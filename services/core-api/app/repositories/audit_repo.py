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
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sbozor_core.models import AuditLog
from sbozor_core.tenancy import TenantScopedRepository
from sqlalchemy import BigInteger, DateTime, literal, select, tuple_

if TYPE_CHECKING:
    from app.schemas import AuditQuery

__all__ = [
    "MASKED",
    "SENSITIVE_AUDIT_KEYS",
    "AuditPage",
    "AuditRepository",
    "InvalidCursorError",
    "decode_cursor",
    "encode_cursor",
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
