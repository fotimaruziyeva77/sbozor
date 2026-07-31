"""Tarif tarixi — FAQAT QO'SHADIGAN repozitoriy (D-05/D-06/D-07, MARKET-03).

=============================================================================
BU MODULDA `add_tariff()` ICHIDA HECH QANDAY `UPDATE` YO'Q VA BO'LMAYDI.

D-06: yangi narx — YANGI QATOR. Eski qatorga tegilmaydi, ya'ni o'tmishdagi
hisob hech qachon qayta baholanmaydi. `daterange` bilan qurilgan modelda
yangi narx kiritish eski qatorning yuqori chegarasini YOPISHNI talab
qilardi — D-07 esa aynan o'sha amalni taqiqlaydi (ikki qoida bir-birini
inkor qilardi). Voris modelida narx qo'shish bitta `INSERT`
(`sbozor_core.models.market` modul docstringi).

Amal qilish OXIRI (`valid_to`) SAQLANMAYDI — u keyingi qatordan
`LEAD(valid_from)` bilan HISOBLANADI (Pitfall 9). `tariffs` da bunday
ustunning YO'QLIGI `tests/integration/test_tariff_history.py` da tirik
darvoza bilan qulflangan.
=============================================================================

`valid_from` DARVOZASI IKKI TARMOQLI VA IKKALASI HAM SHU MODULDA:

  1. `valid_from > today`  -> ruxsat (asosiy yo'l, D-06);
  2. `valid_from == market_profile.operating_since` VA bozor QORALAMA
     (`markets.is_active = false`) -> ruxsat (boshlang'ich narx, A3 + D-13);
  3. qolgan hamma holat -> `ValidFromNotAllowedError` -> 422.

Ikkala shart ham `_tariff_window()` dan o'qiladi va boshqa hech qayerda
takrorlanmaydi: `min_valid_from` javob maydoni ham AYNAN o'sha
yordamchidan keladi. Shartni ikki joyda yozish server bilan klient
o'rtasida jimgina ajralib ketadigan ikkinchi haqiqat manbai bo'lardi.

TENANT FILTRI IKKI QATLAM (RESEARCH Pattern 1): RLS policy'si himoya to'ri,
`scoped()` esa aniq predikat. `text()` bilan yozilgan so'rovlarda predikat
QO'LDA, ko'rinadigan joyda turadi (`WHERE t.market_id = :market_id`) —
`stall_repo.py` va `audit_repo.py::_PLATFORM_AUDIT` bilan bir xil naqsh.

SAHIFALASH YO'Q: bozorda toifa soni 5–15 ta, har toifada esa yiliga bir
necha narx. Kursor mexanikasi hech qanday muammoni hal qilmasdi-yu,
"qaysi narx qachon amal qilgan" savolining javobini kesib qo'yardi
(`app.schemas.TariffListResponse` docstringi).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sbozor_core.models import Tariff
from sbozor_core.tenancy import TenantScopedRepository
from sqlalchemy import bindparam, delete, insert, select, text, update
from sqlalchemy.dialects.postgresql import UUID as PgUuid

from app.repositories.stall_repo import MarketProfileMissingError

if TYPE_CHECKING:
    from datetime import date

__all__ = [
    "TariffRepository",
    "TariffRow",
    "TariffWindow",
    "ValidFromNotAllowedError",
]


class ValidFromNotAllowedError(ValueError):
    """`valid_from` ikkala ruxsat etilgan tarmoqqa ham tushmadi.

    Chaqiruvchi buni **422** `valid_from_must_be_future` ga aylantiradi.
    403 EMAS (`tariff_past_locked` dan farqli): bu yerda mavjud qatorga
    umuman tegilmayapti — rad etilayotgani YANGI qatorning sanasi, ya'ni
    savol "shakl to'g'rimi" darajasida hal bo'ladi.
    """


@dataclass(frozen=True)
class TariffWindow:
    """Bozorning tarif oynasi — IKKALA darvoza ham shu obyektdan o'qiladi.

    `min_valid_from` — klient tanlashi mumkin bo'lgan eng erta sana
    (sana maydonining `min` atributi, 02-15). ⚠ BU DARVOZA EMAS: qoralama
    bozorda `operating_since` bilan bugun orasidagi sanalar `min` dan
    katta bo'lsa ham server ularni 422 bilan rad etadi (istisno AYNAN
    tenglik bo'yicha tor). Haqiqiy tekshiruv — `add_tariff()` da va u
    DevTools bilan olib tashlanmaydi.
    """

    operating_since: date
    is_draft: bool
    min_valid_from: date


@dataclass(frozen=True)
class TariffRow:
    """Tarif tarixining bitta qatori — `valid_to` HISOBLANGAN holda.

    `valid_to` `None` — bu toifadagi OXIRGI qator, ya'ni narx hozircha
    muddatsiz. DB'da bunday ustun YO'Q (modul docstringi).
    """

    id: UUID
    category_id: UUID
    category_name: str
    amount_soum: int
    valid_from: date
    valid_to: date | None


_TARIFF_ROWS = text(
    """
    SELECT rows.id,
           rows.category_id,
           rows.category_name,
           rows.amount_soum,
           rows.valid_from,
           rows.valid_to
    FROM (
      SELECT t.id,
             t.category_id,
             c.name         AS category_name,
             t.amount_soum,
             t.valid_from,
             lead(t.valid_from) OVER (
               PARTITION BY t.market_id, t.category_id
               ORDER BY t.valid_from
             )              AS valid_to
      FROM tariffs t
      JOIN stall_categories c
        ON (c.market_id, c.id) = (t.market_id, t.category_id)
      WHERE t.market_id = :market_id
    ) rows
    WHERE (:tariff_id IS NULL OR rows.id = :tariff_id)
      AND (:category_id IS NULL OR rows.category_id = :category_id)
    ORDER BY rows.category_name, rows.valid_from DESC
    """
).bindparams(
    bindparam("market_id", type_=PgUuid(as_uuid=True)),
    bindparam("tariff_id", type_=PgUuid(as_uuid=True)),
    bindparam("category_id", type_=PgUuid(as_uuid=True)),
)
"""Tarif tarixi + hisoblangan amal qilish oxiri.

⚠ FILTRLAR OYNA FUNKSIYASIDAN KEYIN QO'LLANADI VA BU MAJBURIY.

`lead(...)` ni ichki so'rovda qoldirib, `id`/`category_id` filtrini
TASHQARIDA bajarish yagona to'g'ri tartib: `WHERE rows.id = :tariff_id`
ichkariga tushirilsa oyna FAQAT o'sha bitta qatorni ko'rardi va
`valid_to` HAR DOIM `NULL` bo'lib chiqardi — ya'ni `POST`/`PATCH` javobi
"bu narx muddatsiz" deb yolg'on aytardi, `GET` esa aynan o'sha qator
uchun to'g'ri sanani qaytarardi. Ikki javob bir-biriga zid bo'lardi va
sabab kodga qarab umuman ko'rinmasdi.

BITTA SQL MATNI UCH CHAQIRUVCHIGA XIZMAT QILADI (`:tariff_id IS NULL`
tarmog'i): ro'yxat, bitta qator va yozuvdan keyingi javob. Uch nusxa
bo'lganda `valid_to` ta'rifi ajralib ketardi — `stall_repo._STALL_ROWS`
bilan aynan bir xil sabab.

TARTIB: toifa NOMI bo'yicha, ichida esa `valid_from` KAMAYISH tartibida —
UI eng yangi narxni birinchi ko'rsatadi (UI-SPEC §9).

Bind parametrlari `bindparam(type_=...)` bilan ATAYIN tiplangan: `text()`
da SQLAlchemy tipni ustundan chiqara olmaydi va ikkala filtr ham
ko'pincha `NULL` bo'ladi — tipsiz `NULL` asyncpg'ga noma'lum tip bilan
ketardi.
"""

_TARIFF_WINDOW = text(
    """
    SELECT p.operating_since,
           NOT m.is_active AS is_draft
    FROM markets m
    JOIN market_profile p ON p.market_id = m.id
    WHERE m.id = :market_id
    """
).bindparams(bindparam("market_id", type_=PgUuid(as_uuid=True)))
"""Bozorning `operating_since` sanasi va QORALAMA holati — BITTA so'rovda.

Ikkala qiymat ham bitta darvozaning ikki sharti (`T-02-63a`), shuning
uchun ular bitta o'qishda olinadi: ikki alohida so'rov orasida bozor
faollashtirilishi mumkin edi va o'shanda darvoza yarim eski, yarim yangi
holat ustida qaror qabul qilardi.

`markets` bu yerda `scoped()` dan O'TMAYDI va o'ta olmaydi ham: unda
`market_id` ustuni yo'q (tenant chegarasining O'ZI, policy'si `id = ...`).
Shuning uchun predikat qo'lda va ko'rinadigan joyda — `WHERE m.id =
:market_id`. RLS baribir ikkinchi qatlam bo'lib qoladi.
"""


class TariffRepository(TenantScopedRepository):
    """`tariffs` ustidagi o'qish va FAQAT QO'SHADIGAN yozuv yo'li."""

    async def list_tariffs(self, category_id: UUID | None) -> list[TariffRow]:
        """Toifa bo'yicha (yoki hammasi) tarif tarixi, `valid_to` bilan."""
        return await self._rows(tariff_id=None, category_id=category_id)

    async def get(self, tariff_id: UUID) -> TariffRow | None:
        """Bitta qator; topilmasa yoki BEGONA bozorniki bo'lsa `None`.

        Cross-tenant holatida `None` qaytariladi va chaqiruvchi **404**
        beradi — 403 EMAS (T-02-67): 403 javobining o'zi qator
        MAVJUDLIGINI tasdiqlardi.
        """
        rows = await self._rows(tariff_id=tariff_id, category_id=None)
        return rows[0] if rows else None

    async def _rows(self, *, tariff_id: UUID | None, category_id: UUID | None) -> list[TariffRow]:
        result = await self.session.execute(
            _TARIFF_ROWS,
            {
                "market_id": self.market_id,
                "tariff_id": tariff_id,
                "category_id": category_id,
            },
        )
        return [
            TariffRow(
                id=row.id,
                category_id=row.category_id,
                category_name=row.category_name,
                amount_soum=row.amount_soum,
                valid_from=row.valid_from,
                valid_to=row.valid_to,
            )
            for row in result
        ]

    async def tariff_window(self, today: date) -> TariffWindow:
        """`operating_since` + qoralama holati + ruxsat etilgan eng erta sana.

        `today` ARGUMENT sifatida beriladi, funksiya ichida hisoblanmaydi:
        bitta HTTP so'rovi ichidagi bir necha so'rov AYNAN bir xil
        biznes-kunga tayanishi kerak, aks holda yarim tun atrofida yozuv
        va javob boshqa-boshqa kunga tushardi (02-08 qarori).

        Raises:
            MarketProfileMissingError: profil qatori yo'q bo'lsa ->
                router 409 `market_incomplete`. `business_today()` ga
                "vaqtincha" tushib qolish EN XAVFLI yechim bo'lardi:
                qoralama bozorda boshlang'ich narx yo'li JIMGINA yopilib,
                02-11 faollashtirishi hech qachon o'tmasdi.
        """
        result = await self.session.execute(_TARIFF_WINDOW, {"market_id": self.market_id})
        row = result.one_or_none()
        if row is None:
            raise MarketProfileMissingError(f"market_profile topilmadi: {self.market_id}")

        is_draft = bool(row.is_draft)
        operating_since: date = row.operating_since
        return TariffWindow(
            operating_since=operating_since,
            is_draft=is_draft,
            # Qoralama bozorda usta 4-qadami `operating_since` dan
            # boshlanadi; faol bozorda esa eng erta ruxsat etilgan sana —
            # ERTAGA (bugun ham o'tmish: 6-fazaning kunlik job'i bugungi
            # hisobni allaqachon yozgan bo'lishi mumkin).
            min_valid_from=operating_since if is_draft else today + timedelta(days=1),
        )

    def is_valid_from_allowed(self, valid_from: date, window: TariffWindow, today: date) -> bool:
        """`valid_from` ikkala ruxsat etilgan tarmoqdan biriga tushadimi.

        =====================================================================
        2-TARMOQ (BOSHLANG'ICH NARX) ATAYIN OCHILGAN — VA SABABI SHU YERDA.

        Karmana bozori yillar davomida ishlab kelgan, ya'ni uning
        `operating_since` sanasi O'TMISHDA. 02-11 dagi faollashtirish
        darvozasi esa har toifada `valid_from <= operating_since` bo'lgan
        tarifni TALAB qiladi. Istisnosiz usta 4-qadamda boshi berk
        ko'chaga tushardi (D-13) va MARKET-01 API orqali umuman
        bajarilmas edi.

        Istisno XAVFSIZ, chunki u faqat QORALAMA bozorda ochiq: bunday
        bozorda birorta `daily_charges` qatori mavjud emas (6-faza
        `WHERE m.is_active` kontrakti), ya'ni qayta yoziladigan hisobning
        O'ZI yo'q. Faollashtirishdan keyin bu tarmoq BUTUNLAY yopiladi va
        o'sha qator endi "o'tmish" bo'lib `trg_tariff_past_immutable`
        ostiga tushadi (D-07).

        ⚠ TENGLIK AYNAN `==` BO'LISHI SHART. `<=` yozilsa qoralama
        bozorda `operating_since` dan ham OLDINGI ixtiyoriy sanaga narx
        yozib bo'lardi va tor istisno "har qanday o'tmish" ga aylanardi.

        ⚠ BU TEKSHIRUVNI "ortiqcha" deb OLIB TASHLAMANG: uni DB triggeri
        BILAN ALMASHTIRIB BO'LMAYDI. `trg_tariff_past_immutable` —
        `BEFORE UPDATE OR DELETE ON tariffs`, ya'ni `INSERT` yo'lida u
        umuman ishga tushmaydi (02-08 da `set_category()` uchun aynan shu
        fakt sabotaj bilan o'lchangan).
        =====================================================================
        """
        if valid_from > today:
            return True
        return valid_from == window.operating_since and window.is_draft

    async def add_tariff(
        self,
        *,
        category_id: UUID,
        amount_soum: int,
        valid_from: date,
        today: date,
    ) -> UUID:
        """YANGI tarif qatorini yozadi (D-06 — hech qanday qator o'zgarmaydi).

        Raises:
            MarketProfileMissingError: profil qatori yo'q -> 409.
            ValidFromNotAllowedError: sana ikkala tarmoqqa ham tushmadi -> 422.
        """
        window = await self.tariff_window(today)
        if not self.is_valid_from_allowed(valid_from, window, today):
            raise ValidFromNotAllowedError(
                f"valid_from ruxsat etilmagan sanada: {valid_from} "
                f"(eng erta: {window.min_valid_from}, qoralama: {window.is_draft})"
            )

        result = await self.session.execute(
            insert(Tariff)
            .values(
                # `market_id` `self.market_id` DAN — so'rov tanasidan EMAS
                # (T-02-54 mass-assignment darvozasi).
                market_id=self.market_id,
                category_id=category_id,
                amount_soum=amount_soum,
                valid_from=valid_from,
            )
            .returning(Tariff.id)
        )
        return result.scalar_one()

    async def update_future(
        self,
        tariff_id: UUID,
        changes: dict[str, Any],
        today: date,
    ) -> UUID | None:
        """Berilgan maydonlarni yozadi; qator topilmasa `None` (-> 404).

        =====================================================================
        O'TMISHDAGI qatorni qulflash mantig'i BU YERDA TAKRORLANMAYDI —
        u `trg_tariff_past_immutable` da (`OLD.valid_from <= bugun` ->
        `23514`). Trigger `UPDATE` da ROSTDAN ishga tushadi va xom SQL
        yo'lini ham qamraydi, ya'ni ilova tekshiruvi faqat ikkinchi nusxa
        bo'lardi.

        LEKIN YANGI QIYMAT TRIGGER KO'RMAYDIGAN YO'L OCHADI va u shu
        yerda yopiladi: trigger faqat `OLD` ni tekshiradi. Ya'ni
        darvozasiz kimdir avval KELAJAKDAGI tarif yozib (ruxsat etilgan),
        so'ng uning `valid_from` ini O'TMISHGA surib qo'ya olardi — va
        `POST` darvozasi (T-02-63) butunlay chetlab o'tilardi. Shuning
        uchun `valid_from` O'ZGARTIRILAYOTGAN bo'lsa YANGI qiymat AYNAN
        `add_tariff()` dagi ikki tarmoqli shartdan o'tadi.
        =====================================================================

        Raises:
            MarketProfileMissingError: profil qatori yo'q -> 409.
            ValidFromNotAllowedError: yangi sana ruxsat etilmagan -> 422.
        """
        new_valid_from: date | None = changes.get("valid_from")
        if new_valid_from is not None:
            window = await self.tariff_window(today)
            if not self.is_valid_from_allowed(new_valid_from, window, today):
                raise ValidFromNotAllowedError(
                    f"valid_from ruxsat etilmagan sanaga ko'chirilmoqda: {new_valid_from}"
                )

        if not changes:
            # Bo'sh `PATCH` — DB'ga tegilmaydi, lekin mavjudlik BARIBIR
            # tekshiriladi: aks holda begona `tariff_id` uchun javob 200
            # bo'lib, qator MAVJUDLIGINI tasdiqlardi (T-02-67).
            found = await self.session.execute(
                self.scoped(select(Tariff.id).where(Tariff.id == tariff_id))
            )
            return found.scalar_one_or_none()

        result = await self.session.execute(
            update(Tariff)
            .where(Tariff.market_id == self.market_id, Tariff.id == tariff_id)
            .values(**changes)
            .returning(Tariff.id)
        )
        return result.scalar_one_or_none()

    async def delete_future(self, tariff_id: UUID) -> bool:
        """Qatorni o'chiradi; topilmasa `False` (-> 404).

        O'tmishdagi qator uchun `trg_tariff_past_immutable` `23514`
        ko'taradi va chaqiruvchi uni 403 ga aylantiradi — `update_future`
        bilan aynan bir xil yo'l va aynan bir xil sabab.
        """
        result = await self.session.execute(
            delete(Tariff)
            .where(Tariff.market_id == self.market_id, Tariff.id == tariff_id)
            .returning(Tariff.id)
        )
        return result.scalar_one_or_none() is not None

    async def current_amount(self, category_id: UUID, day: date) -> int | None:
        """`day` sanasida AMALDAGI narx; tarif topilmasa `None` (D-08).

        `0` HECH QACHON qaytarilmaydi: u "bepul toifa" degan yolg'on ma'no
        berardi va tarifsiz kun anomaliya sifatida umuman ko'rinmasdi
        (02-07 `test_before_first_tariff_is_fail_closed`). Tip ham shuni
        majburlaydi — `int | None`, `int` emas.

        6-fazaning kunlik job'i va `categories.py` AYNAN shu shakldan
        foydalanadi (`valid_from <= :day` bo'yicha OXIRGI qator).
        """
        result = await self.session.execute(
            self.scoped(
                select(Tariff.amount_soum)
                .where(Tariff.category_id == category_id, Tariff.valid_from <= day)
                .order_by(Tariff.valid_from.desc())
                .limit(1)
            )
        )
        amount: int | None = result.scalar_one_or_none()
        return amount
