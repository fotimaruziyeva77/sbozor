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

⚠ SAHIFALASH FAQAT KEYSET KURSORI BILAN. "Boshidan n qatorni tashlab
yubor" shaklidagi SQL bandi bu modulda UMUMAN ishlatilmaydi va uni
qo'shish taqiqlanadi — `audit_repo.py` modul docstringidagi sabab bu
yerda ham to'liq kuchda: rejalashtiruvchi o'sha n qatorni tom ma'noda
o'qib chiqadi va 1000 rastali bozorda oxirgi sahifa eng qimmat bo'ladi.
Bu taqiq mexanik darvoza bilan ham qulflangan (02-08 qabul mezoni faylni
o'sha SQL kalit so'zi bo'yicha grep qiladi), shuning uchun so'zning O'ZI
bu faylda hech qayerda — izohda ham — yozilmaydi.
"""

from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sbozor_core.models import MarketProfile, Stall, StallCategory, StallCategoryPeriod, Zone
from sbozor_core.tenancy import TenantScopedRepository
from sbozor_core.timeutil import business_today
from sqlalchemy import (
    Date,
    Integer,
    Text,
    and_,
    bindparam,
    delete,
    func,
    insert,
    select,
    text,
    update,
)
from sqlalchemy.dialects.postgresql import UUID as PgUuid

from app.repositories.audit_repo import InvalidCursorError

if TYPE_CHECKING:
    from datetime import date, datetime

    from sqlalchemy import Select
    from sqlalchemy.exc import IntegrityError

    from app.schemas import StallQuery

__all__ = [
    "CategoryPeriodPastError",
    "CategoryRepository",
    "CategoryRow",
    "DeleteOutcome",
    "MapCellRow",
    "MapZoneRow",
    "MarketProfileMissingError",
    "StallPage",
    "StallRepository",
    "StallRow",
    "ZoneRepository",
    "ZoneRow",
    "decode_stall_cursor",
    "encode_stall_cursor",
    "like_term",
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


# ---------------------------------------------------------------------------
# Rastalar (D-01, D-02, D-03, D-04) — keyset, filtrlar va xarita agregati
# ---------------------------------------------------------------------------


class CategoryPeriodPastError(ValueError):
    """`valid_from` bugun yoki o'tmishda — toifa davri yozilmaydi (T-02-61a).

    Chaqiruvchi buni **403** `category_period_past_locked` ga aylantiradi.
    422 EMAS: so'rovning SHAKLI to'g'ri (`date` maydoni haqiqiy sana), rad
    etishning sababi esa o'tmish hech kimga ochiq emasligi — ya'ni bu
    HUQUQ masalasi (02-09 dagi `tariff_past_locked` bilan bir xil
    mulohaza va bir xil javob kodi).
    """


class MarketProfileMissingError(RuntimeError):
    """Bozorda `market_profile` qatori yo'q — rasta yaratib bo'lmaydi.

    `create()` boshlang'ich toifa davrini `operating_since` bilan yozadi,
    ya'ni profilsiz bozorda u sanani OLADIGAN JOY YO'Q. Bunday holatda
    `business_today()` ga "vaqtincha" tushib qolish EN XAVFLI yechim
    bo'lardi: qator jimgina yozilardi va 02-11 ning faollashtirish
    darvozasi (`valid_from <= operating_since` bo'lgan davrni TALAB
    qiladi) hech qachon o'tmasdi — sabab esa hech qayerda ko'rinmasdi.

    Chaqiruvchi buni 409 `market_incomplete` ga aylantiradi. Amalda bu
    holat `market_create()` orqali tug'ilgan bozorda UCHRAMAYDI (profil
    bozor bilan BIR TRANZAKSIYADA yaratiladi) — u faqat qo'lda yozilgan
    yoki chala migratsiya qilingan ma'lumot uchun.
    """


def encode_stall_cursor(code_sort: str, stall_id: UUID) -> str:
    """`(code_sort, id)` juftligini opaque satrga o'raydi.

    `audit_repo.encode_cursor()` bilan AYNAN bir xil naqsh va bir xil
    kafolat: base64 SIR EMAS, u faqat "ichini o'qimang" degan signal.
    Mijoz kursorni o'zi qurishga urinsa, eng yomoni boshqa sahifani
    oladi — kursor RLS predikatidan KEYIN qo'llanadi, ya'ni u bilan
    begona bozorga o'tib bo'lmaydi (T-02-60).

    ⚠ `at` o'rniga `code_sort` ISHLATILADI, `code` EMAS: tartib DB
    tomonidagi hisoblanadigan ustun bo'yicha (inson-raqamli, 2 < 10 <
    100) va kursor AYNAN o'sha ustunga tayanishi shart. `code` bo'yicha
    kursor matn tartibida solishtirilib, sahifa chegarasida qatorlarni
    o'tkazib yuborardi.
    """
    raw = f"{code_sort}|{stall_id}".encode()
    return base64.urlsafe_b64encode(raw).decode()


def decode_stall_cursor(cursor: str) -> tuple[str, UUID]:
    """`encode_stall_cursor()` jufti.

    ⚠ AJRATGICH O'NGDAN qidiriladi (`rsplit`): `code_sort` ifodasi xom
    `code` ni o'z ichiga oladi (`lpad(...) || code`), ya'ni unda `|`
    belgisi BO'LISHI MUMKIN — rasta raqamini kim qanday yozishini hech
    kim cheklamagan. UUID esa hech qachon `|` saqlamaydi, shuning uchun
    oxirgi ajratgich yagona to'g'ri chegara.

    Raises:
        InvalidCursorError: qiymat buzuq bo'lsa. JIMGINA birinchi
            sahifaga qaytilmaydi — bunday xulq sahifalashni cheksiz
            siklga aylantirardi (`audit_repo.decode_cursor()` bilan bir
            xil qaror va bir xil istisno tipi, ya'ni chaqiruvchi ikkala
            endpointda bitta `except` yozadi).
    """
    try:
        decoded = base64.urlsafe_b64decode(cursor.encode()).decode()
        raw_code, raw_id = decoded.rsplit("|", maxsplit=1)
        return raw_code, UUID(raw_id)
    except (binascii.Error, UnicodeDecodeError, ValueError) as exc:
        raise InvalidCursorError(str(exc)) from exc


@dataclass(frozen=True)
class StallRow:
    """Rasta + JORIY toifa, tarif va sotuvchi (bugungi biznes-kun uchun).

    `code_sort` javobda QAYTARILMAYDI (u `app.schemas.StallListItem` da
    yo'q) — u faqat kursor qurish uchun kerak. Uni tashqariga chiqarish
    klientga "tartibni o'zim hisoblayman" degan yo'lni ochardi, tartib esa
    SERVER qarori (UI-SPEC §7.3).
    """

    id: UUID
    code: str
    code_sort: str
    zone_id: UUID
    zone_name: str
    category_id: UUID | None
    category_name: str | None
    status: str
    note: str | None
    created_at: datetime
    vendor_id: UUID | None
    vendor_name: str | None
    phone: str | None
    assignment_from: date | None
    tariff_soum: int | None


@dataclass(frozen=True)
class StallPage:
    """Bitta sahifa + keyingisining kursori (`None` — oxirgi sahifa)."""

    rows: list[StallRow]
    next_cursor: str | None


@dataclass(frozen=True)
class MapCellRow:
    """Xaritadagi bitta katak — `tone` YO'Q (D-20, sabab `app/schemas.py` da)."""

    id: UUID
    code: str
    status: str
    has_vendor: bool
    # ⛔ `None` — rasta plan-xaritada JOYLASHTIRILMAGAN va u sxematik
    #    rejimda chiziladi. «Joylashtirilmagan» va «(0,0) da» BOSHQA
    #    ikki holat (`0026` migratsiyasi izohi).
    plan_x: int | None
    plan_y: int | None


@dataclass(frozen=True)
class MapZoneRow:
    """Zona bloki; kataklar `code_sort` tartibida keladi (tartib SERVERDA)."""

    id: UUID
    name: str
    cells: tuple[MapCellRow, ...]


_LIKE_SPECIALS = str.maketrans({"\\": "\\\\", "%": "\\%", "_": "\\_"})
"""`ILIKE` naqshidagi maxsus belgilar.

Qochirilmaganda `q=%` so'rovi BUTUN reestrni qaytarardi va `q=_` har
qanday bir belgili kodga mos kelardi — ya'ni filtr jimgina ishlamay
qolardi. PostgreSQL'da `LIKE` uchun standart qochirish belgisi —
teskari chiziq, shuning uchun `ESCAPE` bandi kerak emas.
"""


def like_term(value: str | None) -> str | None:
    """Qidiruv so'zini `ILIKE` uchun xavfsiz holga keltiradi.

    OMMAVIY (`_` prefiksisiz) va bu ataylab: `vendor_repo.py` da ham
    `q` filtri bor va u AYNAN shu qochirishga muhtoj. Nusxa ko'chirilsa
    `_LIKE_SPECIALS` ikkinchi haqiqat manbaiga ega bo'lardi — biri
    yangilanib, ikkinchisi eskirganda esa filtr faqat BITTA yuzada
    jimgina ishlamay qolardi.
    """
    return None if value is None else value.translate(_LIKE_SPECIALS)


_STALL_ROWS = text(
    """
    SELECT s.id,
           s.code,
           s.code_sort,
           s.zone_id,
           z.name         AS zone_name,
           cur.category_id,
           c.name         AS category_name,
           s.status,
           s.note,
           s.created_at,
           v.id           AS vendor_id,
           v.full_name    AS vendor_name,
           v.phone_e164   AS phone,
           lower(a.period) AS assignment_from,
           t.amount_soum  AS tariff_soum
    FROM stalls s
    JOIN zones z
      ON z.market_id = s.market_id AND z.id = s.zone_id
    LEFT JOIN LATERAL (
      SELECT p.category_id
      FROM stall_category_periods p
      WHERE p.market_id = s.market_id
        AND p.stall_id = s.id
        AND p.valid_from <= :today
      ORDER BY p.valid_from DESC
      LIMIT 1
    ) cur ON true
    LEFT JOIN stall_categories c
      ON c.market_id = s.market_id AND c.id = cur.category_id
    LEFT JOIN LATERAL (
      SELECT t.amount_soum
      FROM tariffs t
      WHERE t.market_id = s.market_id
        AND t.category_id = cur.category_id
        AND t.valid_from <= :today
      ORDER BY t.valid_from DESC
      LIMIT 1
    ) t ON true
    LEFT JOIN LATERAL (
      SELECT sa.vendor_id, sa.period
      FROM stall_assignments sa
      WHERE sa.market_id = s.market_id
        AND sa.stall_id = s.id
        AND sa.period @> :today
      LIMIT 1
    ) a ON true
    LEFT JOIN vendors v
      ON v.market_id = s.market_id AND v.id = a.vendor_id
    WHERE s.market_id = :market_id
      AND (:stall_id IS NULL OR s.id = :stall_id)
      AND (:zone_id IS NULL OR s.zone_id = :zone_id)
      AND (:category_id IS NULL OR cur.category_id = :category_id)
      AND (:status IS NULL OR s.status = :status)
      AND (
        :q_prefix IS NULL
        OR s.code ILIKE :q_prefix
        OR v.full_name ILIKE :q_any
      )
      AND (
        :cursor_code IS NULL
        OR (s.code_sort, s.id) > (:cursor_code, :cursor_id)
      )
    ORDER BY s.code_sort, s.id
    LIMIT :limit
    """
).bindparams(
    bindparam("market_id", type_=PgUuid(as_uuid=True)),
    bindparam("stall_id", type_=PgUuid(as_uuid=True)),
    bindparam("zone_id", type_=PgUuid(as_uuid=True)),
    bindparam("category_id", type_=PgUuid(as_uuid=True)),
    bindparam("status", type_=Text()),
    bindparam("q_prefix", type_=Text()),
    bindparam("q_any", type_=Text()),
    bindparam("cursor_code", type_=Text()),
    bindparam("cursor_id", type_=PgUuid(as_uuid=True)),
    bindparam("today", type_=Date()),
    bindparam("limit", type_=Integer()),
)
"""RESEARCH Pattern 3 ning ilova tomonidagi to'liq shakli.

UCHTA `LEFT JOIN LATERAL` va ularning TARTIBI ahamiyatli: joriy toifa
(`cur`) birinchi bo'lishi shart, chunki joriy tarif (`t`) AYNAN o'sha
toifa bo'yicha qidiriladi. Zanjir "D kunidagi toifa -> o'sha toifaning
D kunidagi tarifi" (D-04 + D-05) — 6-fazadagi kunlik hisob ham aynan shu
zanjirdan foydalanadi.

`LEFT` (INNER emas) uchalasida ham: toifasi, tarifi yoki sotuvchisi yo'q
rasta ro'yxatdan TUSHIB QOLMASLIGI kerak — aynan o'shalar anomaliya
alomati (D-08, D-11) va ularni yashirish mahsulotning maqsadini buzardi.

NEGA ORM EMAS: modul docstringida. Tenant predikati SHU YERDA, ko'rinadigan
joyda: `WHERE s.market_id = :market_id`. Har bir birikma sharti ham
`market_id` ni takrorlaydi — composite kalit bo'yicha birikish cross-tenant
aralashuvni STRUKTURA bilan imkonsiz qiladi (02-05 composite FK'lari).

BITTA SO'ROV, UCH CHAQIRUVCHI: ro'yxat (`stall_id IS NULL`), bitta rasta
(`stall_id` berilgan) va yaratish/tahrirdan keyingi javob. Uch nusxa
bo'lganda "joriy toifa" ta'rifi ajralib ketardi va ro'yxatdagi qiymat
kartochkadagi qiymatdan farq qilardi.

Sahifa `(code_sort, id) > (kursor)` predikati bilan olinadi va
`ix_stalls_market_id_code_sort` indeksiga tushadi — qator tashlab
yuboradigan band yo'q (modul docstringi).

Bind parametrlari `bindparam(type_=...)` bilan ATAYIN tiplangan: `text()`
da SQLAlchemy tipni ustundan chiqara olmaydi va filtrlarning KO'PCHILIGI
birinchi sahifada `NULL` bo'ladi — tipsiz `NULL` asyncpg'ga noma'lum tip
bilan ketardi (`audit_repo.py::_PLATFORM_AUDIT` bilan bir xil sabab).
"""


_PLAN_PLACE = text(
    """
    UPDATE stalls s
       SET plan_x = v.x,
           plan_y = v.y,
           updated_at = now()
      FROM unnest(
             CAST(:ids AS uuid[]),
             CAST(:xs  AS integer[]),
             CAST(:ys  AS integer[])
           ) AS v(id, x, y)
     WHERE s.market_id = :market_id
       AND s.id = v.id
    """
)
"""Rastalarni plan-xaritaga joylashtirish — bitta `UPDATE` (260820).

⚠ `s.market_id = :market_id` — IKKINCHI QATLAM, birinchisi emas.
  260820 sabotaji o'lchadi: bu shartni olib tashlaganda ham begona
  bozorning rastasi yangilanmadi — RLS `UPDATE ... FROM unnest(...)`
  yo'lini ham qoplaydi. Shart shunga qaramay qoladi: u xom SQL yoki
  `sbozor_owner` roli ostida ishga tushgan kelajakdagi yo'lni ham
  yopadi va o'qiyotgan odamga chegara BOR ekanini ko'rsatib turadi.
"""

_PLAN_CLEAR = text(
    """
    UPDATE stalls
       SET plan_x = NULL,
           plan_y = NULL,
           updated_at = now()
     WHERE market_id = :market_id
       AND id = ANY(CAST(:ids AS uuid[]))
    """
)
"""Rastani plandan chiqarish — u SXEMATIK rejimga qaytadi, yo'qolmaydi."""


_MAP_ROWS = text(
    """
    SELECT z.id   AS zone_id,
           z.name AS zone_name,
           s.id   AS stall_id,
           s.code,
           s.status,
           s.plan_x,
           s.plan_y,
           (a.stall_id IS NOT NULL) AS has_vendor
    FROM zones z
    LEFT JOIN stalls s
      ON s.market_id = z.market_id AND s.zone_id = z.id
    LEFT JOIN LATERAL (
      SELECT sa.stall_id
      FROM stall_assignments sa
      WHERE sa.market_id = s.market_id
        AND sa.stall_id = s.id
        AND sa.period @> :today
      LIMIT 1
    ) a ON true
    WHERE z.market_id = :market_id
    ORDER BY z.name, s.code_sort, s.id
    """
).bindparams(
    bindparam("market_id", type_=PgUuid(as_uuid=True)),
    bindparam("today", type_=Date()),
)
"""Xarita agregati — zonalar NOM tartibida, kataklar `code_sort` tartibida.

TARTIB SERVERDA HAL QILINADI (UI-SPEC §7.3) va frontend qayta saralamaydi:
klient tomondagi saralash uchala tilda boshqacha natija berardi, DB kontenti
esa bitta tilda (D-16).

`LEFT JOIN stalls` — RASTASI YO'Q ZONA HAM qaytariladi (kataklari bo'sh).
`INNER JOIN` bilan u xaritadan jimgina yo'qolardi va usta 2-qadamda
yaratgan zonasini ko'rmay, uni ikkinchi marta yaratishga urinardi.

"BUGUN SOTUVCHISI BOR" ta'rifi `_STALL_ROWS` dagi bilan AYNAN bir xil
(`period @> :today`, `[)` chegara — D-10 almashinuv kuni YANGI sotuvchiga
tegishli). Ikki xil ta'rif bo'lganda xarita bilan ro'yxat almashinuv
kunida bir-biriga zid rang ko'rsatardi.

`tone` va KOORDINATA qaytarilmaydi (D-19/D-20) — sabab
`app.schemas.MapCell` docstringida.
"""


class StallRepository(TenantScopedRepository):
    """`stalls` ustidagi o'qish va yozish — fazaning eng ko'p ishlatiladigan yo'li."""

    async def list_stalls(self, query: StallQuery, today: date) -> StallPage:
        """Filtrlangan keyset sahifa; `query.limit` — QAYTARILADIGAN qatorlar soni.

        BITTA ORTIQCHA qator so'raladi (`limit + 1`) — "yana bormi?"
        savoliga javob beradigan yagona arzon usul. `count(*)` butun
        natijani qayta hisoblardi va u 1000 rastali bozorda har sahifada
        takrorlanardi (`audit_repo.list_audit()` bilan bir xil hiyla).
        """
        cursor_code: str | None = None
        cursor_id: UUID | None = None
        if query.cursor is not None:
            cursor_code, cursor_id = decode_stall_cursor(query.cursor)

        term = like_term(query.q)
        result = await self.session.execute(
            _STALL_ROWS,
            {
                "market_id": self.market_id,
                "stall_id": None,
                "zone_id": query.zone,
                "category_id": query.category,
                "status": str(query.status) if query.status is not None else None,
                "q_prefix": None if term is None else f"{term}%",
                "q_any": None if term is None else f"%{term}%",
                "cursor_code": cursor_code,
                "cursor_id": cursor_id,
                "today": today,
                "limit": query.limit + 1,
            },
        )
        rows = [_stall_row(row) for row in result]

        if len(rows) > query.limit:
            rows = rows[: query.limit]
            last = rows[-1]
            return StallPage(rows=rows, next_cursor=encode_stall_cursor(last.code_sort, last.id))
        return StallPage(rows=rows, next_cursor=None)

    async def detail(self, stall_id: UUID, today: date) -> StallRow | None:
        """Bitta rasta; topilmasa yoki BEGONA bozorniki bo'lsa `None`.

        Cross-tenant holatida `None` qaytariladi va chaqiruvchi **404**
        beradi — 403 EMAS (T-02-55): 403 javobining o'zi obyekt
        MAVJUDLIGINI tasdiqlardi.
        """
        result = await self.session.execute(
            _STALL_ROWS,
            {
                "market_id": self.market_id,
                "stall_id": stall_id,
                "zone_id": None,
                "category_id": None,
                "status": None,
                "q_prefix": None,
                "q_any": None,
                "cursor_code": None,
                "cursor_id": None,
                "today": today,
                "limit": 1,
            },
        )
        row = result.one_or_none()
        return None if row is None else _stall_row(row)

    async def map_view(self, today: date) -> list[MapZoneRow]:
        """Zonalar bo'yicha guruhlangan kataklar (MARKET-06).

        Guruhlash ILOVADA, `array_agg` bilan EMAS: SQL tomonda yig'ilgan
        massiv har katak uchun `jsonb` qurishni talab qilardi va natija
        tiplanmagan `dict` bo'lib kelardi. Qatorlar allaqachon TO'G'RI
        TARTIBDA keladi (`ORDER BY z.name, s.code_sort, s.id`), ya'ni bu
        yerda bitta ketma-ket o'tish yetarli va hech narsa qayta
        saralanmaydi.
        """
        result = await self.session.execute(
            _MAP_ROWS, {"market_id": self.market_id, "today": today}
        )

        zones: list[MapZoneRow] = []
        cells: list[MapCellRow] = []
        current: tuple[UUID, str] | None = None

        for row in result:
            key = (row.zone_id, row.zone_name)
            if current is not None and key != current:
                zones.append(MapZoneRow(id=current[0], name=current[1], cells=tuple(cells)))
                cells = []
            current = key
            # `stall_id` `NULL` — zonada rasta YO'Q (`LEFT JOIN` natijasi).
            # Bunday qator zonani ro'yxatda qoldiradi, lekin katak bermaydi.
            if row.stall_id is not None:
                cells.append(
                    MapCellRow(
                        id=row.stall_id,
                        code=row.code,
                        status=row.status,
                        has_vendor=row.has_vendor,
                        plan_x=row.plan_x,
                        plan_y=row.plan_y,
                    )
                )

        if current is not None:
            zones.append(MapZoneRow(id=current[0], name=current[1], cells=tuple(cells)))
        return zones

    async def save_plan(
        self,
        *,
        placed: list[tuple[UUID, int, int]],
        cleared: list[UUID],
    ) -> tuple[int, int]:
        """Plan-xarita koordinatalarini BIR TRANZAKSIYADA yozadi (260820).

        =================================================================
        ⛔⛔ IKKI SO'ROV, IKKALASI HAM `market_id` BILAN — RLS ustiga
            NIYAT ham yoziladi (`billing_repo` Pitfall 9 qoidasi).

        ⛔ `unnest` bilan BITTA `UPDATE`: 300 rasta uchun 300 so'rov
           yozish tranzaksiyani cho'zib, muharrirdagi «Saqlash» ni
           sekundlarga aylantirardi.

        ⛔ QAYTGAN SON — HAQIQATAN O'ZGARGAN QATORLAR SONI, klient
           yuborgan ro'yxat uzunligi EMAS. Farq bo'lsa (masalan boshqa
           bozorning rastasi yuborilgan) u JIMGINA yutilmaydi: RLS
           bunday qatorni yangilamaydi va sanoq kichik chiqadi.
        =================================================================
        """
        placed_count = 0
        cleared_count = 0

        if placed:
            result = await self.session.execute(
                _PLAN_PLACE,
                {
                    "market_id": self.market_id,
                    "ids": [item[0] for item in placed],
                    "xs": [item[1] for item in placed],
                    "ys": [item[2] for item in placed],
                },
            )
            placed_count = result.rowcount or 0

        if cleared:
            result = await self.session.execute(
                _PLAN_CLEAR, {"market_id": self.market_id, "ids": cleared}
            )
            cleared_count = result.rowcount or 0

        return placed_count, cleared_count

    async def create(
        self,
        *,
        code: str,
        zone_id: UUID,
        category_id: UUID,
        status: str,
        note: str | None,
    ) -> UUID:
        """Rastani va uning BOSHLANG'ICH toifa davrini BIR TRANZAKSIYADA yozadi.

        =====================================================================
        `valid_from` = `market_profile.operating_since` — SO'ROV TANASIDAN
        EMAS. Uchta mustaqil sabab va uchalasi ham majburiy:

        (a) 02-11 ning faollashtirish darvozasi HAR RASTADA `valid_from <=
            operating_since` bo'lgan toifa davrini TALAB qiladi. Bu yerda
            `business_today()` yozilsa, qoralama bozor (uning
            `operating_since` i o'tmishda) hech qachon faollashmasdi va
            sabab hech qayerda ko'rinmasdi;
        (b) 02-06 seed'i ham, 02-12 import yo'li ham AYNAN `operating_since`
            yozadi — uch yo'l bir xil bo'lishi shart, aks holda "rasta
            qayerdan kelgan" savoli hisob natijasiga ta'sir qilardi;
        (c) sana SERVERDA hisoblangani uchun klient uni tanlay olmaydi va
            bu qator `set_category()` darvozasi uchun YON KANAL bo'la
            olmaydi (T-02-61a). Yangi rastada o'tmishdagi hisob YO'Q — u
            hali mavjud emas edi, ya'ni o'tmishga yozish bu yerda hech
            qanday tarixni surmaydi.
        =====================================================================

        TARTIB: avval `operating_since` o'qiladi, keyin qatorlar yoziladi.
        Teskari tartibda profilsiz bozorda rasta YOZILIB, keyin xato
        chiqardi — tranzaksiya baribir rollback bo'lardi, lekin xato
        `stalls` INSERT'idan keyin kelib, sababni chalkashtirardi.
        """
        operating_since = await self._operating_since()

        inserted = await self.session.execute(
            insert(Stall)
            .values(
                # `market_id` `self.market_id` DAN — so'rov tanasidan EMAS
                # (T-02-54 mass-assignment darvozasi).
                market_id=self.market_id,
                zone_id=zone_id,
                code=code,
                status=status,
                note=note,
            )
            .returning(Stall.id)
        )
        stall_id: UUID = inserted.scalar_one()

        await self.session.execute(
            insert(StallCategoryPeriod).values(
                market_id=self.market_id,
                stall_id=stall_id,
                category_id=category_id,
                valid_from=operating_since,
            )
        )
        return stall_id

    async def update(self, stall_id: UUID, changes: dict[str, Any]) -> UUID | None:
        """Berilgan maydonlarni yozadi; rasta topilmasa `None`.

        `changes` — `model_dump(exclude_unset=True)` natijasi, ya'ni
        "berilmagan" va "ataylab `null` qilingan" holatlar AJRATILGAN.
        Oddiy `model_dump()` bilan `note` har `PATCH` da tozalanib
        ketardi.

        `category_id` bu yerga HECH QACHON kelmaydi — `StallUpdateRequest`
        da bunday maydon yo'q (D-04). Toifa alohida endpoint orqali va
        alohida darvoza ostida o'zgaradi.
        """
        if not changes:
            # Bo'sh `PATCH` — DB'ga tegilmaydi, lekin mavjudlik baribir
            # tekshiriladi: aks holda begona `stall_id` uchun javob 200
            # bo'lib, obyekt MAVJUDLIGINI tasdiqlardi (T-02-55).
            found = await self.session.execute(
                self.scoped(select(Stall.id).where(Stall.id == stall_id))
            )
            return found.scalar_one_or_none()

        result = await self.session.execute(
            update(Stall)
            .where(Stall.market_id == self.market_id, Stall.id == stall_id)
            .values(**changes)
            .returning(Stall.id)
        )
        return result.scalar_one_or_none()

    async def set_category(
        self,
        stall_id: UUID,
        *,
        category_id: UUID,
        valid_from: date,
    ) -> bool:
        """Rastaga YANGI toifa davrini yozadi (D-04 — voris modeli).

        =====================================================================
        O'TMISH DARVOZASI SHU YERDA, ILOVA QATLAMIDA — DB TRIGGERIDA EMAS.

        `trg_category_period_past_immutable` — `BEFORE UPDATE OR DELETE ON
        stall_category_periods` (02-04:127; 02-05 dagi
        `attach_immutability_trigger()` ham AYNAN shu shaklni yozadi). Bu
        metod esa faqat `INSERT` qiladi, toifa davri uchun `PATCH`/`DELETE`
        endpointi esa UMUMAN MAVJUD EMAS — ya'ni trigger bu yo'lda hech
        qachon ishga tushmaydi. U o'z vazifasini bajaradi (yozilgan qatorni
        KEYINCHALIK o'zgartirish/o'chirishni bloklaydi), lekin YOZISHNING
        O'ZINI to'sa olmaydi.

        Darvozasiz nima bo'lardi: o'tgan sanali `valid_from` jimgina 201
        bilan yozilardi. Oqibati D-04 ni BEVOSITA buzadi — rastaning D
        kunidagi amaldagi tarifi "D kunidagi toifa -> o'sha toifaning D
        kunidagi tarifi" zanjiri bilan aniqlanadi (`_STALL_ROWS` dagi
        LATERAL), demak o'tmishga yangi toifa davri qo'yish `tariffs`
        jadvaliga UMUMAN TEGMASDAN tarixiy kunning tarifini almashtirib
        qo'yardi (T-02-61a, SC#3 ga yon kanal).

        CHEGARA AYNAN `>` (`>=` EMAS): bugungi kun uchun 6-fazaning kunlik
        job'i hisob yozib bo'lgan bo'lishi mumkin, ya'ni "bugun" ham
        o'tmish.

        ⚠ QORALAMA BOZOR UCHUN ISTISNO TARMOG'I YO'Q va u ATAYIN
        ochilmagan (02-09 `add_tariff()` dagi `T-02-63a` dan farqli).
        Sababi ikki qavatli: (1) BOSHLANG'ICH davrni `create()` va 02-12
        importi ICHKARIDA, server nazoratidagi `operating_since` bilan
        yozadi — ya'ni bu endpoint orqali o'tishga hech qanday zaruriyat
        yo'q; (2) istisno ochilsa ham u hech qanday yo'lni OCHMASDI:
        `UNIQUE(market_id, stall_id, valid_from)` tufayli `operating_since`
        sanasi allaqachon band va o'sha sanaga ikkinchi INSERT baribir 409
        `category_period_exists` berardi. Ya'ni istisno faqat yon kanalni
        qayta ochardi.
        =====================================================================

        Returns:
            Rasta topilgan va davr yozilgan bo'lsa `True`; rasta topilmasa
            (yoki begona bozorniki bo'lsa) `False` -> chaqiruvchi 404.

        Raises:
            CategoryPeriodPastError: `valid_from` kelajakda emas -> 403.
        """
        if valid_from <= business_today():
            raise CategoryPeriodPastError(
                f"valid_from kelajakda bo'lishi kerak, berilgani: {valid_from}"
            )

        found = await self.session.execute(
            self.scoped(select(Stall.id).where(Stall.id == stall_id))
        )
        if found.scalar_one_or_none() is None:
            return False

        # YANGI QATOR — `UPDATE` YO'Q (D-04 voris modeli): eski davr
        # daxlsiz qoladi va o'tmishdagi hisob qayta baholanmaydi.
        await self.session.execute(
            insert(StallCategoryPeriod).values(
                market_id=self.market_id,
                stall_id=stall_id,
                category_id=category_id,
                valid_from=valid_from,
            )
        )
        return True

    async def _operating_since(self) -> date:
        """Bozorning tizimdagi ish boshlash sanasi (A3).

        Raises:
            MarketProfileMissingError: profil qatori yo'q bo'lsa.
        """
        result = await self.session.execute(self.scoped(select(MarketProfile.operating_since)))
        value: date | None = result.scalar_one_or_none()
        if value is None:
            raise MarketProfileMissingError(f"market_profile topilmadi: {self.market_id}")
        return value


def _stall_row(row: Any) -> StallRow:
    """`_STALL_ROWS` qatorini frozen dataclass'ga o'giradi.

    Modul funksiyasi (metod emas): uni `list_stalls()` va `detail()`
    ikkalasi ham ishlatadi va u repozitoriy holatiga umuman bog'liq emas.
    """
    return StallRow(
        id=row.id,
        code=row.code,
        code_sort=row.code_sort,
        zone_id=row.zone_id,
        zone_name=row.zone_name,
        category_id=row.category_id,
        category_name=row.category_name,
        status=row.status,
        note=row.note,
        created_at=row.created_at,
        vendor_id=row.vendor_id,
        vendor_name=row.vendor_name,
        phone=row.phone,
        assignment_from=row.assignment_from,
        tariff_soum=row.tariff_soum,
    )
