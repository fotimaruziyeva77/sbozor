"""App-qatlam audit yozuvi — `source='app'` (D-09, FOUND-03).

=============================================================================
IKKI XIL AUDIT YOZUVI BOR VA ULAR ARALASHTIRILMAYDI:

* `source='db_trigger'` — `fn_audit_row()` DB-triggeri yozadi. Qamrov:
  moliyaviy va huquq-o'zgartiruvchi JADVALLAR (D-10). Xom SQL bilan
  qilingan o'zgarish ham qamraladi, ya'ni ilova kodini chetlab o'tib
  bo'lmaydi.
* `source='app'` — SHU MODUL yozadi. Qamrov: DB o'zgarishi BO'LMAGAN
  hodisalar — `login`, `login_failed`, `logout`, `market_selected`,
  `refresh_reuse_detected`, `password_changed` va (01-07 da) shaxsiy
  ma'lumot O'QISHLARI.

Ya'ni bu modul triggerning O'RNINI BOSMAYDI; u trigger ko'ra olmaydigan
hodisalarni yozadi. Login DB'da hech nimani o'zgartirmaydi — trigger uchun
u umuman sodir bo'lmagan hodisa.
=============================================================================

`audit_append` policy'si `WITH CHECK (true)`, ya'ni jurnalga yozish
TENANT KONTEKSTIDAN QAT'I NAZAR ishlaydi — bu ataylab: `login_failed`
yozuvi bozor hali aniqlanmagan paytda ham qoldirilishi kerak.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sbozor_core.enums import ActorKind, AuditAction, AuditSource
from sbozor_core.models.ops import AuditLog
from sqlalchemy import insert

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.deps import Principal

__all__ = [
    "TABLE_MARKETS",
    "TABLE_REFRESH_TOKENS",
    "TABLE_USERS",
    "platform_admin_label",
    "write_app_audit",
]

TABLE_USERS = "users"
"""`login`, `login_failed`, `password_changed` — hodisa foydalanuvchiga tegishli."""

TABLE_MARKETS = "markets"
"""`market_selected` — hodisa bozor konteksti tanlanishiga tegishli (D-06)."""

TABLE_REFRESH_TOKENS = "refresh_tokens"  # noqa: S105 — jadval nomi, sir emas
"""`logout`, `refresh_reuse_detected` — hodisa sessiyaga tegishli."""


def platform_admin_label(phone: str | None, market_name: str | None) -> str:
    """D-06: "platforma admini X bozorida" — auditda o'qiladigan aktor tavsifi.

    `actor_user_id` va `market_id` ustunlari baribir yoziladi; bu matn
    jurnalni O'QIYOTGAN odam uchun: u ID'larni jadvalga bog'lamasdan
    "bu harakat platforma admini tomonidan, X bozori kontekstida qilingan"
    degan xulosaga kelishi kerak.
    """
    who = phone or "noma'lum"
    where = market_name or "bozor tanlanmagan"
    return f"platforma admini {who} — {where} bozorida"


async def write_app_audit(
    session: AsyncSession,
    *,
    action: AuditAction,
    table_name: str,
    row_id: UUID | None = None,
    old: dict[str, Any] | None = None,
    new: dict[str, Any] | None = None,
    principal: Principal | None = None,
    actor_label: str | None = None,
    actor_user_id: UUID | None = None,
    market_id: UUID | None = None,
    request_id: str | None = None,
    ip: str | None = None,
    actor_kind: ActorKind = ActorKind.USER,
) -> None:
    """`audit_log` ga bitta app-qatlam yozuvi qo'shadi.

    `principal` berilsa, undan `actor_user_id` / `market_id` / `request_id` /
    `actor_label` STANDART QIYMAT sifatida olinadi; aniq argument har doim
    ustun turadi. Bu ikki chaqiruvchi uchun kerak:

    * himoyalangan endpointlar — `Principal` mavjud, hech nima uzatilmaydi;
    * `/auth/login` — `Principal` HALI YO'Q (u aynan shu so'rov natijasida
      tug'iladi), shuning uchun maydonlar aniq uzatiladi. `login_failed`
      holatida `market_id` `None` bo'lib qoladi: kim urinayotgani noma'lum,
      ya'ni bozorni "taxmin qilib" yozish yolg'on dalil bo'lardi.

    DIQQAT: chaqiruvchi tranzaksiyani O'ZI yopadi (`session.commit()`).
    Rad etish yo'llarida audit qatori commit qilinib, KEYIN `HTTPException`
    ko'tariladi — aks holda rollback jurnalni ham o'chirib yuborardi va
    aynan muvaffaqiyatsiz urinishlar izsiz qolardi.
    """
    resolved_actor = actor_user_id if actor_user_id is not None else _principal_user(principal)
    resolved_market = market_id if market_id is not None else _principal_market(principal)
    resolved_request = request_id if request_id is not None else _principal_request(principal)
    resolved_label = actor_label if actor_label is not None else _principal_label(principal)

    await session.execute(
        insert(AuditLog).values(
            market_id=resolved_market,
            actor_user_id=resolved_actor,
            actor_kind=str(actor_kind),
            actor_label=resolved_label,
            action=str(action),
            table_name=table_name,
            row_id=row_id,
            old_value=old,
            new_value=new,
            changed_keys=sorted(new) if new else None,
            request_id=resolved_request,
            ip=ip,
            source=str(AuditSource.APP),
        )
    )


def _principal_user(principal: Principal | None) -> UUID | None:
    return principal.user_id if principal is not None else None


def _principal_market(principal: Principal | None) -> UUID | None:
    return principal.market_id if principal is not None else None


def _principal_request(principal: Principal | None) -> str | None:
    return principal.request_id if principal is not None else None


def _principal_label(principal: Principal | None) -> str | None:
    return principal.actor_label if principal is not None else None
