"""Sotuvchilar reestri (MARKET-04, D-12) — shaxsiy ma'lumotning o'qish yo'li.

=============================================================================
SOTUVCHI — SHAXSIY MA'LUMOT (F.I.Sh. + telefon).

Bu modul o'qish AUDITINI o'zi YOZMAYDI: u endpoint darajasida
`Depends(audit_read(...))` bilan e'lon qilinadi (`app/api/v1/vendors.py`).
Sabab e'lon TARTIBIDA: audit yozuvi huquq tekshiruvidan KEYIN tug'ilishi
kerak va bu faqat dependency zanjirida ifodalanadi. Repozitoriy chaqirilgan
paytga kelib huquq allaqachon tekshirilgan bo'ladi, lekin u "kim so'radi"
ni bilmaydi — ya'ni yozuvni bu yerda qilish `principal` ni repozitoriyga
sudrab kelishni talab qilardi va rad etilgan so'rov yo'lini ham
o'zgartirmasdi.
=============================================================================

TENANT FILTRI IKKI QATLAM (RESEARCH Pattern 1): RLS policy'si himoya to'ri,
`scoped()` esa aniq `market_id` predikati. `LATERAL` li so'rov `text()`
bilan yoziladi va tenant predikati unda QO'LDA, ko'rinadigan joyda turadi
(`WHERE v.market_id = :market_id`) — `stall_repo.py` bilan bir xil naqsh va
bir xil sabab (`scoped()` so'rovning BITTA asosiy entity'siga tayanadi).

⚠ SAHIFALASH FAQAT KEYSET KURSORI BILAN — `stall_repo.py` modul
docstringidagi taqiq bu yerda ham to'liq kuchda va u yerdagi kabi mexanik
darvoza bilan qulflangan, shuning uchun taqiqlangan SQL bandining nomi bu
faylda hech qayerda — izohda ham — yozilmaydi.
"""

from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sbozor_core.models import Vendor
from sbozor_core.tenancy import TenantScopedRepository
from sqlalchemy import Date, Integer, Text, bindparam, insert, select, text, update
from sqlalchemy.dialects.postgresql import UUID as PgUuid

from app.repositories.audit_repo import InvalidCursorError
from app.repositories.stall_repo import like_term

if TYPE_CHECKING:
    from datetime import date, datetime

    from app.schemas import VendorQuery

__all__ = [
    "VendorPage",
    "VendorRepository",
    "VendorRow",
    "decode_vendor_cursor",
    "encode_vendor_cursor",
]


def encode_vendor_cursor(full_name: str, vendor_id: UUID) -> str:
    """`(full_name, id)` juftligini opaque satrga o'raydi.

    `encode_stall_cursor()` bilan AYNAN bir xil naqsh va bir xil kafolat:
    base64 SIR EMAS, u faqat "ichini o'qimang" degan signal. Mijoz
    kursorni o'zi qurishga urinsa, eng yomoni boshqa sahifani oladi —
    kursor RLS predikatidan KEYIN qo'llanadi, ya'ni u bilan begona
    bozorga o'tib bo'lmaydi (T-02-60 bilan bir xil mulohaza).

    ⚠ TARTIB USTUNI `full_name` — ro'yxat aynan shu ustun bo'yicha
    saralanadi (`ORDER BY v.full_name, v.id`) va kursor undan CHETGA
    CHIQMASLIGI shart: boshqa ustun bo'yicha kursor sahifa chegarasida
    qatorlarni jimgina o'tkazib yuborardi.
    """
    raw = f"{full_name}|{vendor_id}".encode()
    return base64.urlsafe_b64encode(raw).decode()


def decode_vendor_cursor(cursor: str) -> tuple[str, UUID]:
    """`encode_vendor_cursor()` jufti.

    ⚠ AJRATGICH O'NGDAN qidiriladi (`rsplit`): F.I.Sh. ixtiyoriy matn va
    unda `|` belgisi BO'LISHI MUMKIN (hech kim buni cheklamagan). UUID esa
    hech qachon `|` saqlamaydi, shuning uchun oxirgi ajratgich yagona
    to'g'ri chegara.

    Raises:
        InvalidCursorError: qiymat buzuq bo'lsa. JIMGINA birinchi sahifaga
            qaytilmaydi — bunday xulq sahifalashni cheksiz siklga
            aylantirardi (`decode_stall_cursor()` bilan bir xil qaror va
            bir xil istisno tipi, ya'ni chaqiruvchi bitta `except`
            yozadi).
    """
    try:
        decoded = base64.urlsafe_b64decode(cursor.encode()).decode()
        raw_name, raw_id = decoded.rsplit("|", maxsplit=1)
        return raw_name, UUID(raw_id)
    except (binascii.Error, UnicodeDecodeError, ValueError) as exc:
        raise InvalidCursorError(str(exc)) from exc


@dataclass(frozen=True)
class VendorRow:
    """Sotuvchi + BUGUN unga biriktirilgan rastalar.

    `stall_codes` `stall_count` dan QISQAROQ bo'lishi mumkin
    (`VENDOR_STALL_CODES_MAX`) va bu ataylab: kodlar UI badge'i uchun,
    sanoq esa haqiqat. Faqat kodlar qaytarilsa "yigirmatadan ortiq rasta"
    holati javobda umuman ko'rinmasdi.
    """

    id: UUID
    full_name: str
    phone: str
    stall_count: int
    stall_codes: tuple[str, ...]
    created_at: datetime


@dataclass(frozen=True)
class VendorPage:
    """Bitta sahifa + keyingisining kursori (`None` — oxirgi sahifa)."""

    rows: list[VendorRow]
    next_cursor: str | None


_VENDOR_ROWS = text(
    """
    SELECT v.id,
           v.full_name,
           v.phone_e164 AS phone,
           v.created_at,
           cnt.stall_count,
           coalesce(codes.stall_codes, ARRAY[]::text[]) AS stall_codes
    FROM vendors v
    LEFT JOIN LATERAL (
      SELECT count(*) AS stall_count
      FROM stall_assignments sa
      WHERE sa.market_id = v.market_id
        AND sa.vendor_id = v.id
        AND sa.period @> :today
    ) cnt ON true
    LEFT JOIN LATERAL (
      SELECT array_agg(picked.code ORDER BY picked.code_sort) AS stall_codes
      FROM (
        SELECT s.code, s.code_sort
        FROM stall_assignments sa
        JOIN stalls s
          ON s.market_id = sa.market_id AND s.id = sa.stall_id
        WHERE sa.market_id = v.market_id
          AND sa.vendor_id = v.id
          AND sa.period @> :today
        ORDER BY s.code_sort
        LIMIT :codes_limit
      ) picked
    ) codes ON true
    WHERE v.market_id = :market_id
      AND (:vendor_id IS NULL OR v.id = :vendor_id)
      AND (
        :q_prefix IS NULL
        OR v.full_name ILIKE :q_prefix
        OR v.phone_e164 ILIKE :q_any
      )
      AND (
        :cursor_name IS NULL
        OR (v.full_name, v.id) > (:cursor_name, :cursor_id)
      )
    ORDER BY v.full_name, v.id
    LIMIT :limit
    """
).bindparams(
    bindparam("market_id", type_=PgUuid(as_uuid=True)),
    bindparam("vendor_id", type_=PgUuid(as_uuid=True)),
    bindparam("q_prefix", type_=Text()),
    bindparam("q_any", type_=Text()),
    bindparam("cursor_name", type_=Text()),
    bindparam("cursor_id", type_=PgUuid(as_uuid=True)),
    bindparam("today", type_=Date()),
    bindparam("codes_limit", type_=Integer()),
    bindparam("limit", type_=Integer()),
)
"""Sotuvchilar + BUGUNGI biriktirishlar agregati.

IKKI ALOHIDA `LATERAL` VA BU MAJBURIY: sanoq CHEGARASIZ (`count(*)` butun
to'plam ustida), kodlar esa `LIMIT :codes_limit` bilan kesiladi. Bitta
`LATERAL` da ikkalasini olishga urinilsa agregat KESILGAN to'plam ustida
hisoblanardi va `stall_count` yolg'on — "yigirmata" — bo'lib qolardi,
ya'ni T-02-78 chegarasi javobga sizib chiqardi.

`array_agg(... ORDER BY picked.code_sort)` — ichki so'rov allaqachon
tartiblangan bo'lsa ham tartib agregatda QAYTA e'lon qilinadi: SQL ichki
so'rovning tartibini agregatga o'tkazishni KAFOLATLAMAYDI va kodlar
ro'yxati rejalashtiruvchi qaroriga qarab aralashib ketardi. Tartib
`code_sort` bo'yicha, ya'ni INSON-RAQAMLI (2 < 10 < 100) —
`stall_repo._STALL_ROWS` bilan bir xil.

"BUGUN BIRIKTIRILGAN" TA'RIFI `stall_repo._STALL_ROWS` DAGI BILAN AYNAN
BIR XIL (`period @> :today`). Ikki xil ta'rif bo'lganda sotuvchi
kartochkasidagi rastalar ro'yxati rasta reestridagi sotuvchi bilan
ALMASHINUV KUNIDA bir-biriga zid bo'lardi (D-10).

BITTA SQL MATNI IKKI CHAQIRUVCHIGA XIZMAT QILADI (`:vendor_id IS NULL`
tarmog'i): ro'yxat va bitta sotuvchi. Ikki nusxa bo'lganda agregat
ta'rifi ajralib ketardi — `stall_repo` va `tariff_repo` dagi bilan bir xil
sabab.

Bind parametrlari `bindparam(type_=...)` bilan ATAYIN tiplangan: `text()`
da SQLAlchemy tipni ustundan chiqara olmaydi va filtrlarning KO'PCHILIGI
birinchi sahifada `NULL` bo'ladi — tipsiz `NULL` asyncpg'ga noma'lum tip
bilan ketardi.
"""

_PHONE_FIELD = "phone"
_PHONE_COLUMN = "phone_e164"
"""DTO maydoni -> ustun nomi. Ular ATAYIN har xil.

Javobda `phone` (klient uchun qisqa), ustunda esa `phone_e164` — nomning
O'ZI saqlangan qiymat E.164 ekanini aytadi (`users.phone_e164` bilan bir
xil qaror). `PATCH` yo'li shu ikkisini BITTA joyda bog'laydi; mapping
router ichida qilinsa, u yerda bir kun "`phone` ustuni yo'q" xatosi
paydo bo'lardi.
"""


class VendorRepository(TenantScopedRepository):
    """`vendors` ustidagi o'qish va yozish (MARKET-04)."""

    async def list_vendors(
        self,
        query: VendorQuery,
        today: date,
        *,
        codes_limit: int,
    ) -> VendorPage:
        """Filtrlangan keyset sahifa; `query.limit` — QAYTARILADIGAN qatorlar soni.

        BITTA ORTIQCHA qator so'raladi (`limit + 1`) — "yana bormi?"
        savoliga javob beradigan yagona arzon usul. `count(*)` butun
        natijani qayta hisoblardi va u har sahifada takrorlanardi
        (`list_stalls()` va `audit_repo.list_audit()` bilan bir xil hiyla).

        `today` va `codes_limit` ARGUMENT sifatida beriladi, funksiya
        ichida hisoblanmaydi: bitta HTTP so'rovi ichidagi bir necha so'rov
        AYNAN bir xil biznes-kunga tayanishi kerak (02-08 qarori).

        Raises:
            InvalidCursorError: `query.cursor` buzuq bo'lsa -> 422.
        """
        cursor_name: str | None = None
        cursor_id: UUID | None = None
        if query.cursor is not None:
            cursor_name, cursor_id = decode_vendor_cursor(query.cursor)

        term = like_term(query.q)
        rows = await self._rows(
            vendor_id=None,
            today=today,
            codes_limit=codes_limit,
            q_prefix=None if term is None else f"{term}%",
            q_any=None if term is None else f"%{term}%",
            cursor_name=cursor_name,
            cursor_id=cursor_id,
            limit=query.limit + 1,
        )

        if len(rows) > query.limit:
            rows = rows[: query.limit]
            last = rows[-1]
            return VendorPage(rows=rows, next_cursor=encode_vendor_cursor(last.full_name, last.id))
        return VendorPage(rows=rows, next_cursor=None)

    async def get_vendor(
        self,
        vendor_id: UUID,
        today: date,
        *,
        codes_limit: int,
    ) -> VendorRow | None:
        """Bitta sotuvchi; topilmasa yoki BEGONA bozorniki bo'lsa `None`.

        Cross-tenant holatida `None` qaytariladi va chaqiruvchi **404**
        beradi — 403 EMAS (T-02-67 bilan bir xil mulohaza): 403 javobining
        o'zi qator MAVJUDLIGINI tasdiqlardi.
        """
        rows = await self._rows(
            vendor_id=vendor_id,
            today=today,
            codes_limit=codes_limit,
            q_prefix=None,
            q_any=None,
            cursor_name=None,
            cursor_id=None,
            limit=1,
        )
        return rows[0] if rows else None

    async def _rows(
        self,
        *,
        vendor_id: UUID | None,
        today: date,
        codes_limit: int,
        q_prefix: str | None,
        q_any: str | None,
        cursor_name: str | None,
        cursor_id: UUID | None,
        limit: int,
    ) -> list[VendorRow]:
        result = await self.session.execute(
            _VENDOR_ROWS,
            {
                "market_id": self.market_id,
                "vendor_id": vendor_id,
                "today": today,
                "codes_limit": codes_limit,
                "q_prefix": q_prefix,
                "q_any": q_any,
                "cursor_name": cursor_name,
                "cursor_id": cursor_id,
                "limit": limit,
            },
        )
        return [
            VendorRow(
                id=row.id,
                full_name=row.full_name,
                phone=row.phone,
                stall_count=row.stall_count,
                stall_codes=tuple(row.stall_codes),
                created_at=row.created_at,
            )
            for row in result
        ]

    async def create_vendor(self, *, full_name: str, phone: str) -> UUID:
        """Yangi sotuvchi. Takroriy telefon `IntegrityError` (`23505`) ko'taradi.

        `market_id` `self.market_id` DAN — so'rov tanasidan EMAS (T-02-54
        mass-assignment darvozasi).

        Telefon BU YERDA normallashtirilmaydi: u chegarada
        (`VendorRequest._normalize`) allaqachon E.164 ga keltirilgan.
        Ikkinchi normalizatsiya "qaysi biri haqiqat?" savolini tug'dirardi
        va ikkala shakl bir kun ajralib ketardi (`schemas.py` modul
        docstringidagi qoida).
        """
        result = await self.session.execute(
            insert(Vendor)
            .values(market_id=self.market_id, full_name=full_name, phone_e164=phone)
            .returning(Vendor.id)
        )
        return result.scalar_one()

    async def update_vendor(self, vendor_id: UUID, changes: dict[str, Any]) -> UUID | None:
        """Berilgan maydonlarni yozadi; sotuvchi topilmasa `None` (-> 404).

        `changes` — `model_dump(exclude_unset=True)` natijasi, ya'ni
        "berilmagan" va "yuborilgan" holatlar ajratilgan. Oddiy
        `model_dump()` bilan har `PATCH` ikkala ustunni ham qayta yozardi
        va ismni tuzatmoqchi bo'lgan so'rov telefonni `NULL` bilan
        almashtirib, `NOT NULL` konstraytiga urilardi.
        """
        values = {
            (_PHONE_COLUMN if field == _PHONE_FIELD else field): value
            for field, value in changes.items()
        }

        if not values:
            # Bo'sh `PATCH` — DB'ga tegilmaydi, lekin mavjudlik BARIBIR
            # tekshiriladi: aks holda begona `vendor_id` uchun javob 200
            # bo'lib, qator MAVJUDLIGINI tasdiqlardi (T-02-67).
            found = await self.session.execute(
                self.scoped(select(Vendor.id).where(Vendor.id == vendor_id))
            )
            return found.scalar_one_or_none()

        result = await self.session.execute(
            update(Vendor)
            .where(Vendor.market_id == self.market_id, Vendor.id == vendor_id)
            .values(**values)
            .returning(Vendor.id)
        )
        return result.scalar_one_or_none()
