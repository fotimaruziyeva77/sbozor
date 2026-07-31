"""Bozor reestrlari — zona, toifa va rasta so'rovlari (MARKET-02, MARKET-06).

=============================================================================
UCHTA REPOZITORIY, BITTA MODUL — VA BU ATAYIN.

`ZoneRepository`, `CategoryRepository` va `StallRepository` bir-biriga
uzviy bog'langan: rasta ro'yxati zona NOMINI va joriy toifa NOMINI birga
qaytaradi, toifa ro'yxati esa o'sha toifadagi rastalarni sanaydi. Ularni
uch faylga bo'lish har bir so'rovni ikki modulga tarqatardi va "joriy
toifa" ta'rifi (`valid_from <= :today` bo'yicha OXIRGI qator) uch joyda
takrorlanardi — o'sha takror bir kun ajralib ketardi va ro'yxat bilan
xarita boshqa-boshqa toifani ko'rsatardi.
=============================================================================

TENANT FILTRI IKKI QATLAM (RESEARCH Pattern 1): RLS policy'si himoya to'ri,
`scoped()` esa aniq `market_id` predikati. Bu yerda UCHINCHI shakl ham bor —
`text()` bilan yozilgan so'rovlar `market_id` ni NOMLANGAN BIND PARAMETR
sifatida oladi (`audit_repo.py::_PLATFORM_AUDIT` naqshi).

NEGA BA'ZI SO'ROVLAR `text()` BILAN:
`TenantScopedRepository.scoped()` so'rovning BITTA asosiy entity'siga
tayanadi (`column_descriptions[0]`), `LEFT JOIN LATERAL` esa SQLAlchemy'da
`lateral()` + korrelyatsiya bilan quriladi va natijaviy kod xom SQL'dan
sezilarli darajada uzunroq va o'qish qiyinroq bo'lardi. Shuning uchun
LATERAL li so'rovlar `text()` bilan yoziladi va tenant predikati ularda
QO'LDA, ko'rinadigan joyda turadi (`WHERE s.market_id = :market_id`).
Oddiy so'rovlar esa ORM'da qoladi va `scoped()` dan o'tadi.

⚠ `OFFSET` BU MODULDA UMUMAN ISHLATILMAYDI. Sahifalash — keyset kursori
(`audit_repo.py` modul docstringidagi sabab bu yerda ham to'liq kuchda:
1000 rastali bozorda "boshidan n qatorni tashlab yubor" bandi tom ma'noda
o'sha n qatorni o'qib chiqadi).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from sbozor_core.models import Stall, StallCategory, Zone
from sbozor_core.tenancy import TenantScopedRepository
from sqlalchemy import Date, and_, bindparam, delete, func, insert, select, text, update
from sqlalchemy.dialects.postgresql import UUID as PgUuid

if TYPE_CHECKING:
    from datetime import date
    from uuid import UUID

    from sqlalchemy import Select
    from sqlalchemy.exc import IntegrityError

__all__ = [
    "CategoryRepository",
    "CategoryRow",
    "DeleteOutcome",
    "ZoneRepository",
    "ZoneRow",
    "sqlstate_of",
]


def sqlstate_of(exc: IntegrityError) -> str | None:
    """`IntegrityError` ning SQLSTATE kodi (`23505`, `23503`, `23P01`, ...).

    ⚠ `exc.orig.constraint_name` ATAYIN ISHLATILMAYDI: asyncpg o'ramida u
    `None` bo'ladi (02-06 da o'lchangan) va RLS yoqilgan jadvalda Postgres
    xatoning `DETAIL` qatorini ham o'chiradi (Pitfall 4). Ya'ni ilova
    qatlami uchun ISHONCHLI yagona signal — SQLSTATE.

    Ikki xil rad etish bir xil kod berganda (`23505` — kod band / kod
    chetlangan, D-01 va D-02) ajratish xato MATNI bo'yicha bo'ladi va u
    chaqiruvchida, ko'rinadigan joyda yoziladi (`api/v1/stalls.py`).
    """
    return getattr(exc.orig, "sqlstate", None)


class DeleteOutcome(StrEnum):
    """`DELETE` amalining natijasi — HTTP kodiga aylantirish chaqiruvchida.

    Uchta holat ATAYIN ajratilgan: "topilmadi" (404) va "ishlatilmoqda"
    (409) bir xil "muvaffaqiyatsiz" emas. Birinchisi cross-tenant javobi
    ham bo'lishi mumkin (RLS 0 qator beradi), ikkinchisi esa o'z bozoridagi
    haqiqiy bog'liqlik — foydalanuvchi uchun ular butunlay boshqa xabar.
    """

    DELETED = "deleted"
    NOT_FOUND = "not_found"
    IN_USE = "in_use"


@dataclass(frozen=True)
class ZoneRow:
    """Zona + undagi rastalar soni (`user_repo.MarketUser` naqshi)."""

    id: UUID
    name: str
    stall_count: int


@dataclass(frozen=True)
class CategoryRow:
    """Toifa + rastalar soni + BUGUNGI amaldagi narx.

    `current_tariff_soum` `None` — narx hali berilmagan (D-08). `0`
    QAYTARILMAYDI: u "bepul toifa" degan yolg'on ma'no berardi va
    tarifsiz kun anomaliya sifatida hech qachon ko'rinmasdi.
    """

    id: UUID
    name: str
    stall_count: int
    current_tariff_soum: int | None


# ---------------------------------------------------------------------------
# Zonalar (D-03)
# ---------------------------------------------------------------------------


class ZoneRepository(TenantScopedRepository):
    """`zones` ustidagi CRUD — sahifalashsiz (ro'yxat 5–15 element)."""

    def _rows(self) -> Select[Any]:
        """Zona + rasta sanog'i so'rovining YAGONA ta'rifi.

        `list_zones()` va `get()` shu yerdan boshlanadi: sanoq mantiqi ikki
        joyda yozilsa, ro'yxatdagi son bilan tahrirdan keyin qaytariladigan
        son bir kun ajralib ketardi.

        `LEFT JOIN` — rastasi YO'Q zona ham ro'yxatda qoladi (`INNER JOIN`
        bilan u jimgina yo'qolardi va foydalanuvchi endigina yaratgan
        zonasini ko'rmasdi). Birikma sharti `market_id` ni ham o'z ichiga
        oladi: composite kalit bo'yicha birikish tenant invariantining bir
        qismi, `scoped()` esa faqat ASOSIY entity'ga predikat qo'shadi.
        """
        return self.scoped(
            select(Zone.id, Zone.name, func.count(Stall.id).label("stall_count"))
            .outerjoin(
                Stall,
                and_(Stall.market_id == Zone.market_id, Stall.zone_id == Zone.id),
            )
            .group_by(Zone.id, Zone.name)
        )

    async def list_zones(self) -> list[ZoneRow]:
        """Zonalar NOM tartibida + har birida nechta rasta borligi.

        SAHIFALASH YO'Q va bu ataylab: zona soni bozor bo'yicha o'nlab, ya'ni
        kursor mexanikasi hech qanday muammoni hal qilmasdi-yu, klientga
        doimiy "yana bormi?" savolini yuklardi (`ZoneListResponse` docstringi).
        """
        result = await self.session.execute(self._rows().order_by(Zone.name))
        return [ZoneRow(id=row.id, name=row.name, stall_count=row.stall_count) for row in result]

    async def get(self, zone_id: UUID) -> ZoneRow | None:
        """Bitta zona (sanoq bilan); topilmasa yoki begona bozorniki bo'lsa `None`."""
        result = await self.session.execute(self._rows().where(Zone.id == zone_id))
        row = result.one_or_none()
        return (
            None if row is None else ZoneRow(id=row.id, name=row.name, stall_count=row.stall_count)
        )

    async def create(self, name: str) -> UUID:
        """Yangi zona. Takroriy nom `IntegrityError` (`23505`) ko'taradi.

        `market_id` `self.market_id` DAN — so'rov tanasidan EMAS
        (T-02-54, mass-assignment darvozasi).
        """
        result = await self.session.execute(
            insert(Zone).values(market_id=self.market_id, name=name).returning(Zone.id)
        )
        return result.scalar_one()

    async def rename(self, zone_id: UUID, name: str) -> UUID | None:
        """Zona nomini o'zgartiradi; topilmasa (yoki begona bozorniki) `None`.

        `UPDATE ... RETURNING` ikki ishni birga bajaradi: "bor edimi?"
        savoliga javob beradi va yozadi. Avval `SELECT`, keyin `UPDATE`
        qilinsa ikkalasi orasida qator o'chib ketishi mumkin edi va javob
        "o'zgartirildi" bo'lib chiqardi.
        """
        stmt = (
            update(Zone)
            .where(Zone.market_id == self.market_id, Zone.id == zone_id)
            .values(name=name)
            .returning(Zone.id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def delete(self, zone_id: UUID) -> DeleteOutcome:
        """Zonani o'chiradi; rastasi bo'lsa `IN_USE`.

        TEKSHIRUV TARTIBI: avval mavjudlik (404 va 409 ni ajratish uchun),
        keyin bog'liqlik. Teskari tartibda mavjud bo'lmagan zona uchun ham
        "bog'liqlik yo'q" chiqib, javob 204 bo'lardi — ya'ni o'chirilmagan
        narsa uchun muvaffaqiyat qaytarilardi.

        `IntegrityError` (`23503`) HAM ushlanadi: tekshiruv bilan `DELETE`
        orasida boshqa tranzaksiya shu zonaga rasta qo'shishi mumkin.
        DB konstraytisi — yagona atomik qo'riqchi, ilova tekshiruvi esa
        FOYDALANUVCHI XABARI uchun (u konstrayt matnini ko'rmasligi kerak).
        """
        exists = await self.session.execute(self.scoped(select(Zone.id).where(Zone.id == zone_id)))
        if exists.scalar_one_or_none() is None:
            return DeleteOutcome.NOT_FOUND

        used = await self.session.execute(
            self.scoped(select(Stall.id).where(Stall.zone_id == zone_id).limit(1))
        )
        if used.scalar_one_or_none() is not None:
            return DeleteOutcome.IN_USE

        await self.session.execute(
            delete(Zone).where(Zone.market_id == self.market_id, Zone.id == zone_id)
        )
        return DeleteOutcome.DELETED


# ---------------------------------------------------------------------------
# Toifalar (D-05) — tarif kalitining O'ZI
# ---------------------------------------------------------------------------

_LIST_CATEGORIES = text(
    """
    SELECT c.id,
           c.name,
           (
             SELECT count(*)
             FROM stalls s
             JOIN LATERAL (
               SELECT p.category_id
               FROM stall_category_periods p
               WHERE p.market_id = s.market_id
                 AND p.stall_id = s.id
                 AND p.valid_from <= :today
               ORDER BY p.valid_from DESC
               LIMIT 1
             ) cur ON true
             WHERE s.market_id = :market_id AND cur.category_id = c.id
           ) AS stall_count,
           (
             SELECT t.amount_soum
             FROM tariffs t
             WHERE t.market_id = :market_id
               AND t.category_id = c.id
               AND t.valid_from <= :today
             ORDER BY t.valid_from DESC
             LIMIT 1
           ) AS current_tariff_soum
    FROM stall_categories c
    WHERE c.market_id = :market_id
      AND (:category_id IS NULL OR c.id = :category_id)
    ORDER BY c.name
    """
).bindparams(
    bindparam("market_id", type_=PgUuid(as_uuid=True)),
    bindparam("category_id", type_=PgUuid(as_uuid=True)),
    bindparam("today", type_=Date()),
)
"""Toifalar + joriy rasta soni + BUGUNGI amaldagi narx.

`LATERAL` ni ORM bilan qurish o'rniga xom SQL tanlangani modul
docstringida tushuntirilgan. Bind parametrlari `bindparam(type_=...)`
bilan ATAYIN tiplangan: `text()` da SQLAlchemy tipni ustundan chiqara
olmaydi va `uuid`/`date` qiymatlari asyncpg'ga noma'lum tip bilan
ketardi (`audit_repo.py::_PLATFORM_AUDIT` bilan aynan bir xil sabab).

"JORIY TOIFA" TA'RIFI SHU YERDA VA `list_stalls()` DA AYNAN BIR XIL:
`valid_from <= :today` bo'yicha OXIRGI qator (D-04 voris modeli). Ikki
xil ta'rif bo'lganda toifa ro'yxatidagi sanoq rasta ro'yxatidagi filtr
bilan mos kelmasdi va sabab hech qayerda ko'rinmasdi.

`JOIN LATERAL` (`LEFT` EMAS) sanoq ichida ATAYIN: toifa davri BO'LMAGAN
rasta hech qaysi toifaga sanalmasligi kerak.

`:category_id IS NULL` tarmog'i so'rovni IKKI chaqiruvchi uchun umumiy
qiladi (ro'yxat va bitta toifa). Ikki alohida SQL matni bo'lganda
sanoq mantiqi ikki nusxa bo'lardi — `ZoneRepository._rows()` bilan aynan
bir xil sabab.
"""

_CATEGORY_IN_USE = text(
    """
    SELECT 1
    FROM (
      SELECT 1 FROM stall_category_periods
      WHERE market_id = :market_id AND category_id = :category_id
      UNION ALL
      SELECT 1 FROM tariffs
      WHERE market_id = :market_id AND category_id = :category_id
    ) refs
    LIMIT 1
    """
).bindparams(
    bindparam("market_id", type_=PgUuid(as_uuid=True)),
    bindparam("category_id", type_=PgUuid(as_uuid=True)),
)
"""Toifaga havola qiluvchi BIRORTA qator bormi (toifa davri yoki tarif).

IKKALA jadval ham tekshiriladi. Faqat rastalarni tekshirish yetarli
EMAS: rastasi yo'q, lekin tarifi bor toifa "bo'sh" ko'rinardi va uni
o'chirish `DELETE` bosqichida FK bilan yiqilib foydalanuvchiga 500
qaytarardi (409 o'rniga).

`UNION ALL` + `LIMIT 1` — ikkala jadvalni ham to'liq sanash shart emas:
savol "nechta?" emas, "bormi?".
"""


class CategoryRepository(TenantScopedRepository):
    """`stall_categories` ustidagi CRUD — sahifalashsiz."""

    async def list_categories(self, today: date) -> list[CategoryRow]:
        """Toifalar NOM tartibida, sanoq va bugungi narx bilan.

        `today` ARGUMENT sifatida beriladi, funksiya ichida hisoblanmaydi:
        bitta HTTP so'rovi ichida bir necha so'rov bir xil biznes-kunga
        tayanishi kerak va chaqiruvchi uni bir marta oladi.
        """
        return await self._rows(today, category_id=None)

    async def get(self, category_id: UUID, today: date) -> CategoryRow | None:
        """Bitta toifa (sanoq va narx bilan); topilmasa `None`."""
        rows = await self._rows(today, category_id=category_id)
        return rows[0] if rows else None

    async def _rows(self, today: date, *, category_id: UUID | None) -> list[CategoryRow]:
        result = await self.session.execute(
            _LIST_CATEGORIES,
            {"market_id": self.market_id, "category_id": category_id, "today": today},
        )
        return [
            CategoryRow(
                id=row.id,
                name=row.name,
                stall_count=row.stall_count,
                current_tariff_soum=row.current_tariff_soum,
            )
            for row in result
        ]

    async def create(self, name: str) -> UUID:
        """Yangi toifa. Takroriy nom `IntegrityError` (`23505`) ko'taradi."""
        result = await self.session.execute(
            insert(StallCategory)
            .values(market_id=self.market_id, name=name)
            .returning(StallCategory.id)
        )
        return result.scalar_one()

    async def rename(self, category_id: UUID, name: str) -> UUID | None:
        """Toifa nomini o'zgartiradi; topilmasa `None` (`ZoneRepository` naqshi)."""
        stmt = (
            update(StallCategory)
            .where(
                StallCategory.market_id == self.market_id,
                StallCategory.id == category_id,
            )
            .values(name=name)
            .returning(StallCategory.id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def delete(self, category_id: UUID) -> DeleteOutcome:
        """Toifani o'chiradi; unga havola qiluvchi qator bo'lsa `IN_USE`.

        BOG'LIQLIK ZONADAGIDAN KENGROQ: toifaga `stall_category_periods`
        ham, `tariffs` ham havola qiladi. Ikkalasi ham tekshiriladi —
        faqat rastalarni tekshirish narxi bor, lekin rastasi yo'q toifani
        o'chirishga ruxsat berardi va o'sha `DELETE` FK bilan yiqilib
        foydalanuvchiga 500 qaytarardi.
        """
        exists = await self.session.execute(
            self.scoped(select(StallCategory.id).where(StallCategory.id == category_id))
        )
        if exists.scalar_one_or_none() is None:
            return DeleteOutcome.NOT_FOUND

        used = await self.session.execute(
            _CATEGORY_IN_USE, {"market_id": self.market_id, "category_id": category_id}
        )
        if used.scalar_one_or_none() is not None:
            return DeleteOutcome.IN_USE

        await self.session.execute(
            delete(StallCategory).where(
                StallCategory.market_id == self.market_id,
                StallCategory.id == category_id,
            )
        )
        return DeleteOutcome.DELETED
