"""Ommaviy import uchun o'qish lug'atlari va OMMAVIY yozuv (D-13/D-14/D-15).

=============================================================================
NEGA ALOHIDA REPOZITORIY.

02-09 da o'rnatilgan konvensiya: ROUTERLAR SQL BAJARMAYDI. Import
oqimiga oltita LUG'AT so'rovi va ikkita ommaviy yozuv kerak, ular esa
mavjud repozitoriylarning birortasiga ham tabiiy tushmaydi:

* `ZoneRepository.list_zones()` har zonaga rasta SANOG'ini qo'shadi
  (`LEFT JOIN` + `GROUP BY`) — import uchun bu keraksiz ish;
* `CategoryRepository.list_categories()` BUGUNGI TARIFNI ham hisoblaydi
  va shu sababli `today` argumentini talab qiladi — importda esa tarif
  umuman ishlatilmaydi;
* `StallRepository` / `VendorRepository` — bittalab yozish uchun, ya'ni
  1000 qatorli faylda 1000 ta borish-kelish bo'lardi.

Shuning uchun bu yerda AYNAN import kerak qiladigan shakl: `{nom: id}`
lug'atlari va BITTA `INSERT ... RETURNING`.
=============================================================================

TRANZAKSIYA BU YERDA HAM, ROUTERDA HAM OCHILMAYDI.

`TenantSessionDep` sessiyani ALLAQACHON tranzaksiya ichida beradi
(`app/deps.py::get_tenant_session`), ya'ni har qanday istisno butun
importni orqaga qaytaradi va D-14 (all-or-nothing) TEKIN keladi. Bu
yerda ichki tranzaksiya ochish uni faqat buzardi: ichki blok muvaffaqiyat
bilan yopilgach, undan keyingi xato allaqachon yozilgan qatorlarni
qoldirib ketardi.

RLS ostida konstrayt xatosining `DETAIL` i O'CHIRILADI (Pitfall 4), ya'ni
bu yerdan chiqadigan `IntegrityError` QAYSI qator to'qnashganini AYTMAYDI.
Foydalanuvchi xabarining manbai — `app/services/import_validator.py`, bu
yerdagi konstrayt esa POYGA qo'riqchisi.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog
from sbozor_core.models import (
    MarketProfile,
    Stall,
    StallAssignment,
    StallCategory,
    StallCategoryPeriod,
    Vendor,
    Zone,
)
from sbozor_core.periods import assignment_period
from sbozor_core.tenancy import TenantScopedRepository
from sqlalchemy import insert, select

from app.repositories.stall_repo import MarketProfileMissingError

if TYPE_CHECKING:
    from datetime import date
    from uuid import UUID

    from app.services.import_validator import StallImportRow, VendorImportRow

__all__ = ["ImportRepository"]

log = structlog.get_logger(__name__)


class ImportRepository(TenantScopedRepository):
    """Import oqimining YAGONA DB yuzasi."""

    async def zone_ids_by_name(self) -> dict[str, UUID]:
        """`{zona nomi: id}` — FAQAT joriy bozordan (T-02-94).

        Lug'at tenant sessiyasi ostida o'qilgani uchun boshqa bozorning
        zonasi bu yerga TUSHMAYDI. Natijada A bozoriga B ning zona nomi
        bilan import qilingan qator `zone_not_found` oladi va javob
        o'sha nomning boshqa bozorda MAVJUDLIGINI oshkor qilmaydi.
        """
        result = await self.session.execute(self.scoped(select(Zone.name, Zone.id)))
        return {row.name: row.id for row in result}

    async def category_ids_by_name(self) -> dict[str, UUID]:
        """`{toifa nomi: id}` — FAQAT joriy bozordan."""
        result = await self.session.execute(
            self.scoped(select(StallCategory.name, StallCategory.id))
        )
        return {row.name: row.id for row in result}

    async def stall_ids_by_code(self) -> dict[str, UUID]:
        """`{rasta kodi: id}` — sotuvchi importidagi biriktirish uchun.

        Bu lug'at `existing_stall_codes()` ning O'RNINI BOSMAYDI: u yerda
        savol "kod bandmi?", bu yerda esa "qaysi rasta?". Ikkalasini
        birlashtirish rasta importida keraksiz `id` larni tortardi.
        """
        result = await self.session.execute(self.scoped(select(Stall.code, Stall.id)))
        return {row.code: row.id for row in result}

    async def existing_stall_codes(self) -> set[str]:
        """Joriy bozorda ALLAQACHON mavjud rasta kodlari (D-15).

        ⚠ CHETLANGAN (`stall_code_registry`) kodlar bu yerga TUSHMAYDI va
        bu ATAYIN: chetlangan kod QAYTA ISHLATILMAYDI (D-02), ya'ni uni
        "mavjud" deb jimgina o'tkazib yuborish faylda qolgan eski
        raqamni foydalanuvchiga KO'RSATMASDAN yo'q qilardi. Bunday qator
        `INSERT` ga boradi, `stall_code_claim()` triggeri uni `23505`
        bilan to'xtatadi va router 409 `import_conflict` qaytaradi —
        ya'ni admin "bu raqam qaytarilmaydi" degan haqiqatni KO'RADI.
        """
        result = await self.session.execute(self.scoped(select(Stall.code)))
        return set(result.scalars())

    async def existing_vendor_phones(self) -> set[str]:
        """Joriy bozorda mavjud telefonlar, E.164 shaklida (D-15)."""
        result = await self.session.execute(self.scoped(select(Vendor.phone_e164)))
        return set(result.scalars())

    async def operating_since(self) -> date:
        """`market_profile.operating_since` (A3).

        Raises:
            MarketProfileMissingError: profil qatori yo'q bo'lsa. Router
                uni 409 `market_incomplete` ga aylantiradi — 02-08 dagi
                `StallRepository.create()` bilan AYNAN bir xil qoida.
        """
        result = await self.session.execute(self.scoped(select(MarketProfile.operating_since)))
        value: date | None = result.scalar_one_or_none()
        if value is None:
            raise MarketProfileMissingError(f"market_profile topilmadi: {self.market_id}")
        return value

    async def insert_stalls(self, rows: list[StallImportRow], *, valid_from: date) -> int:
        """Rastalarni va ularning BOSHLANG'ICH toifa davrlarini yozadi.

        `valid_from` — `market_profile.operating_since`, SO'ROV TANASIDAN
        EMAS. Bu 02-08 dagi `StallRepository.create()` bilan AYNAN bir
        xil qoida va u UCHINCHI yozish yo'li (seed, bittalab yaratish,
        import) uchun ham majburiy: 02-11 ning faollashtirish darvozasi
        HAR RASTADA `valid_from <= operating_since` bo'lgan toifa davrini
        TALAB qiladi. Bu yerda `business_today()` yozilsa import qilingan
        rastalar `stalls_without_category` bo'lib sanalardi va bozor
        HECH QACHON faollashmasdi — sabab esa hech qayerda ko'rinmasdi.

        `code_sort` YOZILMAYDI: u DB da hisoblanadigan ustun (`Computed`).
        Ilova tomonda qurilsa ro'yxat va xarita bir kun boshqa-boshqa
        tartibda chiqardi.

        ⚠ `ON CONFLICT DO NOTHING` ATAYIN ISHLATILMAYDI — QARORI O'ZGARMADI,
        SABABI 02-21 DA TO'G'RILANDI (WR-04).

        Bu yerda ilgari "`stall_code_claim()` `BEFORE` triggeri konfliktdan
        OLDIN ishga tushadi va `ON CONFLICT` bandi uni CHETLAB O'TA
        OLMAYDI" deb yozilgan edi. DDL esa
        `AFTER INSERT OR UPDATE OF code` (`0007_market_domain.py:317-321`),
        ya'ni AKSINCHA: konflikt yuzaga kelgan qator uchun trigger UMUMAN
        ishga tushmaydi va `ON CONFLICT DO NOTHING` bemalol ishlagan
        bo'lardi (`triggers.py:215-221`).

        BAND BARIBIR YOZILMAYDI va sabab MAHSULOTDA: u "mavjud kodlar
        jimgina o'tkazib yuborildi" holatini KO'RINMAYDIGAN qilardi.
        Foydalanuvchiga qaytadigan `skipped` soni validatorda, YOZISHDAN
        OLDIN hisoblanadi (D-15) — DB uni sanamaydi. Band qo'shilsa
        `inserted` bilan `skipped` orasidagi farq jimgina yo'qolardi va
        "qayta import hech nima o'zgartirmadi" javobi asossiz qolardi.
        Ayni paytda band chala fayl xatosini ham (kod TASODIFAN
        takrorlangan holat) jimgina yutib yuborardi.
        """
        if not rows:
            return 0

        inserted = await self.session.execute(
            insert(Stall)
            .values(
                [
                    {
                        # `market_id` `self.market_id` DAN — fayldan EMAS
                        # (T-02-54 mass-assignment darvozasi).
                        "market_id": self.market_id,
                        "zone_id": row.zone_id,
                        "code": row.code,
                        "status": row.status,
                        "note": row.note,
                    }
                    for row in rows
                ]
            )
            .returning(Stall.id, Stall.code)
        )
        ids_by_code = {row.code: row.id for row in inserted}

        await self.session.execute(
            insert(StallCategoryPeriod),
            [
                {
                    "market_id": self.market_id,
                    "stall_id": ids_by_code[row.code],
                    "category_id": row.category_id,
                    "valid_from": valid_from,
                }
                for row in rows
            ],
        )
        return len(rows)

    async def insert_vendors(self, rows: list[VendorImportRow]) -> int:
        """Sotuvchilarni va (kodi berilgan qatorlar uchun) biriktirishlarni yozadi.

        Davr `assignment_period()` bilan quriladi — xom `daterange`
        YOZILMAYDI (Pitfall 10). Yuqori chegara `None`: import qilingan
        biriktirish OCHIQ davr, ya'ni "sotuvchi hozir ham shu yerda".

        Qoplanish (`23P01`) va begona havola (`23503`) bu yerdan
        `IntegrityError` bo'lib chiqadi va router uni 409 ga aylantiradi.
        Fayl ICHIDAGI takroriylik esa validatorda, QATOR RAQAMI bilan
        ushlanadi — DB ga faqat POYGA holati qoladi.
        """
        if not rows:
            return 0

        inserted = await self.session.execute(
            insert(Vendor)
            .values(
                [
                    {
                        "market_id": self.market_id,
                        "full_name": row.full_name,
                        "phone_e164": row.phone,
                    }
                    for row in rows
                ]
            )
            .returning(Vendor.id, Vendor.phone_e164)
        )
        ids_by_phone = {row.phone_e164: row.id for row in inserted}

        assignments = [
            {
                "market_id": self.market_id,
                "stall_id": row.stall_id,
                "vendor_id": ids_by_phone[row.phone],
                "period": assignment_period(row.from_date, None),
            }
            for row in rows
            if row.stall_id is not None
        ]
        if assignments:
            await self.session.execute(insert(StallAssignment), assignments)
        return len(rows)
