"""Audit jurnalini o'qish — filtrlar, KEYSET sahifalash va maskalash (D-12).

=============================================================================
SAHIFALASH — KURSOR BILAN, SAHIFA RAQAMI BILAN EMAS:

"Boshidan n ta qatorni tashlab yubor" shaklidagi bandni SQL rejalashtiruvchi
tom ma'noda bajaradi — u avval o'sha n qatorni topadi, keyin ularni
tashlaydi. Ya'ni 10 000-sahifa 10 000 qatorni o'qib chiqadi. Audit jurnali
FAQAT o'sadi (append-only, o'chirish yo'li umuman yo'q), shuning uchun bu
sekinlashuv vaqt o'tgani sari yomonlashadi va aynan eng ko'p ma'lumot
to'plangan bozorda eng og'riqli bo'ladi.

Kursor esa `(at, id) < (chegara)` predikati bilan
`ix_audit_log_market_id_at` indeksiga to'g'ridan-to'g'ri tushadi va sahifa
raqamidan qat'i nazar bir xil narx turadi.

Ikkinchi (va nozikroq) sabab: jurnal so'rovlar ORASIDA o'sib boradi — har
`GET /audit` ning O'ZI yangi `read` qatorini qo'shadi (D-09). Raqamli
sahifalashda bu qatorlar sahifalarni SURIB YUBORARDI: foydalanuvchi
2-sahifaga o'tganda 1-sahifadagi yozuvni yana ko'rardi. Kursor esa qat'iy
yuqori chegara, ya'ni undan keyin qo'shilgan qatorlar natijaga umuman
tushmaydi.

`(at, id)` JUFTLIGI kerak, `at` yolg'iz emas: bir tranzaksiyada yozilgan
bir necha qator AYNAN bir xil `at` ga ega bo'lishi mumkin va o'shanda
`at <` predikati ularning bir qismini o'tkazib yuborardi.
=============================================================================

BIZNES-KUN FILTRI `business_date` USTUNI BO'YICHA. Vaqt tamg'asini so'rov
ichida kunga yaxlitlovchi ifoda ISHLATILMAYDI: (a) u indeksdan
foydalanmaydi, (b) u UTC kunini beradi, biznes-kun esa `Asia/Tashkent`
bo'yicha yopiladi — mahalliy yarim tundan keyingi besh soat UTC'da OLDINGI
kunga tushadi (Pitfall 6). `business_date` generated column bu farqni DB
tomonda bir marta hal qilgan (01-05) va uni ilova qatlamida takrorlash
ikkinchi haqiqat manbaini yaratardi.
"""

from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass
from datetime import date, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sbozor_core.models import AuditLog
from sbozor_core.tenancy import TenantScopedRepository
from sqlalchemy import BigInteger, DateTime, Integer, bindparam, literal, select, text, tuple_

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.schemas import AuditQuery

__all__ = [
    "MASKED",
    "SENSITIVE_AUDIT_KEYS",
    "AuditPage",
    "AuditRepository",
    "InvalidCursorError",
    "PlatformAuditPage",
    "PlatformAuditRow",
    "decode_cursor",
    "encode_cursor",
    "list_platform_audit",
    "mask_sensitive",
]

MASKED = "***"

SENSITIVE_AUDIT_KEYS = frozenset(
    {
        "password",
        "password_hash",
        "temporary_password",
        "new_password",
        "current_password",
        "token",
        "access_token",
        "refresh_token",
        "secret",
        "api_key",
        "rtsp_password",
        "nvr_password",
    }
)
"""Javobda `"***"` bilan almashtiriladigan kalitlar (T-01-52).

Mahsulot kodi bunday kalitni auditga HECH QACHON yozmaydi, ya'ni bu ro'yxat
ikkinchi qatlam: u kelajakda kimdir yangi jadvalga audit triggerini ulaganda
va o'sha jadvalda sirli ustun bo'lganda ishga tushadi. `to_jsonb(NEW)`
BUTUN qatorni yozadi, ya'ni bunday ustun jurnalga O'ZIDAN tushadi va uni
jurnalni ko'rish huquqi bor har bir odam o'qiy olardi.

Ro'yxat `sbozor_core.logging.SENSITIVE_KEYS` bilan bir xil MANTIQDA, lekin
alohida: u log satrlari uchun (HTTP sarlavhalari ham bor), bu esa DB
ustunlari uchun.
"""


class InvalidCursorError(ValueError):
    """Kursorni o'qib bo'lmadi — chaqiruvchi uni 422 ga aylantiradi."""


def mask_sensitive(value: Any) -> Any:
    """JSONB qiymatidagi sezgir kalitlarni REKURSIV maskalaydi.

    Ichma-ich obyekt ham qamraladi: faqat yuqori daraja tekshirilganda
    `{"credentials": {"password": ...}}` shaklidagi yozuv ochiq qolardi.
    Massiv elementlari ham ko'riladi — `to_jsonb()` massiv ichida obyekt
    qaytarishi mumkin.
    """
    if isinstance(value, dict):
        return {
            key: MASKED if str(key).lower() in SENSITIVE_AUDIT_KEYS else mask_sensitive(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [mask_sensitive(item) for item in value]
    return value


def encode_cursor(at: datetime, row_id: int) -> str:
    """`(at, id)` juftligini opaque satrga o'raydi.

    Base64 — SIR EMAS, u faqat "bu qiymatning ichini o'qimang" degan
    signal. Mijoz uni o'zi qurishga urinsa (masalan `at` ni surib), eng
    yomoni boshqa sahifani oladi: kursor RLS predikatidan KEYIN
    qo'llanadi, ya'ni u bilan begona bozorga o'tib bo'lmaydi.
    """
    raw = f"{at.isoformat()}|{row_id}".encode()
    return base64.urlsafe_b64encode(raw).decode()


def decode_cursor(cursor: str) -> tuple[datetime, int]:
    """`encode_cursor()` jufti.

    Raises:
        InvalidCursorError: qiymat buzuq bo'lsa. JIMGINA birinchi
            sahifaga qaytilmaydi — bunday xulq sahifalashni cheksiz
            siklga aylantirardi va sabab mijoz tomonda ko'rinmasdi.
    """
    try:
        decoded = base64.urlsafe_b64decode(cursor.encode()).decode()
        raw_at, raw_id = decoded.split("|", maxsplit=1)
        return datetime.fromisoformat(raw_at), int(raw_id)
    except (binascii.Error, UnicodeDecodeError, ValueError) as exc:
        raise InvalidCursorError(str(exc)) from exc


@dataclass(frozen=True)
class AuditPage:
    """Bitta sahifa + keyingisining kursori (`None` — oxirgi sahifa)."""

    rows: list[AuditLog]
    next_cursor: str | None


class AuditRepository(TenantScopedRepository):
    """`audit_log` ustidagi o'qish — IKKI QATLAMLI tenant filtri bilan.

    `audit_read` policy'si (01-05) allaqachon `market_id = app.market_id`
    ni majburlaydi; `scoped()` esa o'sha predikatni so'rovning O'ZIGA
    qo'shadi. Ikkilanish ataylab (RESEARCH Pattern 1): RLS bir kun
    noto'g'ri migratsiya bilan o'chib qolsa, ilova baribir to'g'ri
    ishlaydi — va predikat rejalashtiruvchiga `(market_id, at DESC)`
    indeksini ishlatish imkonini beradi.
    """

    async def list_audit(self, query: AuditQuery) -> AuditPage:
        """Filtrlangan sahifa. `query.limit` — QAYTARILADIGAN qatorlar soni."""
        stmt = self.scoped(select(AuditLog))

        if query.date_from is not None:
            stmt = stmt.where(AuditLog.business_date >= query.date_from)
        if query.date_to is not None:
            stmt = stmt.where(AuditLog.business_date <= query.date_to)
        if query.actor_user_id is not None:
            stmt = stmt.where(AuditLog.actor_user_id == query.actor_user_id)
        if query.action is not None:
            stmt = stmt.where(AuditLog.action == query.action)
        if query.table_name is not None:
            stmt = stmt.where(AuditLog.table_name == query.table_name)
        if query.cursor is not None:
            at, row_id = decode_cursor(query.cursor)
            # Qiymatlar `literal(..., type_)` bilan ATAYIN tiplangan:
            # `tuple_()` xom Python qiymatidan tipni chiqara olmaydi va
            # `at` ni mintaqasiz `timestamp` ga aylantirib qo'yardi —
            # o'shanda kursor Toshkent yarim tuni atrofida bir necha
            # qatorni o'tkazib yuborardi.
            boundary = tuple_(
                literal(at, DateTime(timezone=True)),
                literal(row_id, BigInteger()),
            )
            stmt = stmt.where(tuple_(AuditLog.at, AuditLog.id) < boundary)

        # BITTA ORTIQCHA qator so'raladi: "yana bormi?" savoliga javob
        # beradigan yagona arzon usul. `count(*)` butun natijani qayta
        # hisoblardi va u aynan katta jurnalda qimmat.
        stmt = stmt.order_by(AuditLog.at.desc(), AuditLog.id.desc()).limit(query.limit + 1)

        result = await self.session.execute(stmt)
        rows = list(result.scalars().all())

        if len(rows) > query.limit:
            rows = rows[: query.limit]
            last = rows[-1]
            return AuditPage(rows=rows, next_cursor=encode_cursor(last.at, last.id))
        return AuditPage(rows=rows, next_cursor=None)


# ===========================================================================
# PLATFORMA-GLOBAL O'QISH (Gap 5) — `market_id IS NULL` qatorlar
# ===========================================================================
#
# NEGA BU YERDA ORM YO'Q VA `AuditRepository` KENGAYTIRILMAGAN:
#
# `AuditRepository` — `TenantScopedRepository`, ya'ni uning har bir so'rovi
# `market_id = app.market_id` predikati bilan quriladi. Platforma-global
# qatorlar esa AYNAN o'sha predikatga mos kelmaydigan qatorlar
# (`market_id IS NULL`), ya'ni ularni tenant repozitoriysiga qo'shish
# sinfning yagona da'vosini buzardi.
#
# Undan ham muhimi: bu qatorlarga ORM orqali umuman BORIB BO'LMAYDI.
# `audit_log` da RLS ENABLE+FORCE va `audit_read` policy'si tenant-scoped,
# `sbozor_app` esa `audit_read_platform` (`TO sbozor_owner`) policy'sidan
# foydalana olmaydi — xom `select(AuditLog).where(market_id.is_(None))`
# HAR DOIM 0 qator beradi (`tests/tenancy/test_login_bootstrap.py` da
# o'lchangan). Yagona yo'l — `auth_list_platform_audit()` SECURITY DEFINER
# funksiyasi (0005), ya'ni `auth_repo` dagi bilan bir xil naqsh: `text()`
# + nomlangan, TIPLANGAN bind parametrlari.
#
# HUQUQ TEKSHIRUVI BU YERDA EMAS (D-07): funksiyaga `EXECUTE` berilgani
# "ilova chaqira oladi" degani, "har kim ko'ra oladi" degani EMAS. Darvoza
# — `app.deps.require_platform_admin` (`is_platform_admin` bayrog'i).

_PLATFORM_AUDIT = text(
    "SELECT id, at, business_date, actor_user_id, actor_label, action, table_name, "
    "row_id, old_value, new_value, changed_keys, request_id, source "
    "FROM auth_list_platform_audit(:limit, :before_at, :before_id)"
).bindparams(
    bindparam("limit", type_=Integer()),
    bindparam("before_at", type_=DateTime(timezone=True)),
    bindparam("before_id", type_=BigInteger()),
)
"""Bind parametrlari ATAYIN TIPLANGAN.

`text()` da SQLAlchemy tipni ustundan chiqara olmaydi, kursorning ikkala
qismi esa birinchi sahifada `None` bo'ladi — tipsiz `NULL` asyncpg'ga
noma'lum tip bilan ketardi va Postgres funksiya imzosini bir ma'noli tanlay
olmasdi. `at` uchun `timezone=True` alohida muhim: mintaqasiz `timestamp`
ga tushgan kursor Toshkent yarim tuni atrofida bir necha qatorni o'tkazib
yuborardi (`AuditRepository.list_audit` dagi `literal(..., type_)` bilan
AYNAN bir xil sabab).
"""


@dataclass(frozen=True)
class PlatformAuditRow:
    """`auth_list_platform_audit()` ning bitta qatori — ORM obyekti EMAS.

    Maydonlar funksiyaning 13 ustunli `RETURNS TABLE` imzosini AYNAN
    takrorlaydi (`migrations/entities/functions.py`), ya'ni DB kontrakti
    ilovada bir marta va ko'rinadigan joyda yozilgan: imzo o'zgarsa bu
    dataclass ham o'zgarishi kerak va nomuvofiqlik mypy/testda darhol
    chiqadi.

    `ip` ustuni YO'Q — u funksiyada ham, `app.schemas.AuditEntry` da ham
    yo'q (D-12). Platforma yo'li mavjud tenant o'qishidan KENGROQ ma'lumot
    bermaydi.

    `market_id` ham YO'Q va bu ataylab: funksiya sharti LITERAL
    `market_id IS NULL`, ya'ni ustunning yagona mumkin bo'lgan qiymati
    `NULL`. Uni qaytarish javobga hech nima qo'shmasdi.
    """

    id: int
    at: datetime
    business_date: date
    actor_user_id: UUID | None
    actor_label: str | None
    action: str
    table_name: str
    row_id: UUID | None
    old_value: dict[str, Any] | None
    new_value: dict[str, Any] | None
    changed_keys: list[str] | None
    request_id: str | None
    source: str


@dataclass(frozen=True)
class PlatformAuditPage:
    """Bitta sahifa + keyingisining kursori (`AuditPage` bilan bir xil shakl)."""

    rows: list[PlatformAuditRow]
    next_cursor: str | None


async def list_platform_audit(
    session: AsyncSession,
    *,
    limit: int,
    cursor: str | None = None,
) -> PlatformAuditPage:
    """Platforma-global audit sahifasi — `AuditRepository.list_audit` NAQSHIDA.

    Keyset semantikasi tenant yo'li bilan AYNAN BIR XIL: `(at, id)`
    juftligi, `at DESC, id DESC` tartibi, "yana bormi?" savoliga BITTA
    ortiqcha qator javob beradi. Kursor formati ham o'sha
    (`encode_cursor`/`decode_cursor`), ya'ni mijoz uchun ikkala endpoint
    bir xil xulq ko'rsatadi va kursorni bir joydan ikkinchisiga uzatish
    kabi chalkashlik tug'ilmaydi.

    `limit` HECH QACHON `None` BO'LMASLIGI KERAK va tip shuni majburlaydi.
    Funksiyada `LIMIT COALESCE(p_limit, 0)` turibdi (01-14), ya'ni `None`
    XATO emas, 0 QATOR beradi — jimgina bo'sh sahifa. Yagona haqiqiy
    chegara chaqiruvchida: endpoint `Query(ge=1, le=AUDIT_PAGE_SIZE_MAX)`
    bilan validatsiya qiladi.

    Raises:
        InvalidCursorError: kursor buzuq bo'lsa. Yuqoriga TARQALADI —
            endpoint uni 422 ga aylantiradi, xuddi tenant yo'lidagi kabi.
            Jimgina birinchi sahifaga qaytish sahifalashni cheksiz siklga
            aylantirardi.
    """
    before_at: datetime | None = None
    before_id: int | None = None
    if cursor is not None:
        before_at, before_id = decode_cursor(cursor)

    result = await session.execute(
        _PLATFORM_AUDIT,
        # `limit + 1` — `AuditRepository.list_audit` bilan bir xil hiyla:
        # bitta ortiqcha qator "yana bormi?" savoliga `count(*)` siz javob
        # beradi (append-only jadvalda `count(*)` vaqt o'tgani sari qimmatlashadi).
        {"limit": limit + 1, "before_at": before_at, "before_id": before_id},
    )
    rows = [
        PlatformAuditRow(
            id=row.id,
            at=row.at,
            business_date=row.business_date,
            actor_user_id=row.actor_user_id,
            actor_label=row.actor_label,
            action=row.action,
            table_name=row.table_name,
            row_id=row.row_id,
            old_value=row.old_value,
            new_value=row.new_value,
            changed_keys=row.changed_keys,
            request_id=row.request_id,
            source=row.source,
        )
        for row in result
    ]

    if len(rows) > limit:
        rows = rows[:limit]
        last = rows[-1]
        return PlatformAuditPage(rows=rows, next_cursor=encode_cursor(last.at, last.id))
    return PlatformAuditPage(rows=rows, next_cursor=None)
