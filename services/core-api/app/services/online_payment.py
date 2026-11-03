"""Onlayn to'lov (Payme, Click — 0035) uchun UMUMIY qism: rastaning bugungi summasi.

⛔ SUMMA BITTA JOYDA: kassir kartasidagi «jami» (`pending_projection().
   total_due_soum` — bugungi patta + eski qarz). Payme ham, Click ham shu
   funksiyani chaqiradi; ikkinchi hisob yozilsa ikki to'lov tizimi bir kun
   ikki xil summa so'rardi.

⛔ QISMAN TO'LOV YO'Q (buyurtmachi, 261028): to'lov tizimi yuborgan summa
   AYNAN shu songa teng bo'lishi shart.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from sbozor_core.timeutil import business_today

from app.repositories import billing_repo

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

__all__ = ["DueUnavailable", "StallDue", "stall_due"]

DueReason = Literal["stall_not_found", "stall_not_assigned", "nothing_due"]


@dataclass(frozen=True, slots=True)
class StallDue:
    """Rastaning bugungi to'lovi: identifikatorlar + to'lanadigan jami summa (so'm).

    `today_soum` / `debt_soum` / `paid_today_soum` — QR sahifasidagi izoh
    qatorlari uchun, kassir kartasidagi AYNI maydonlar (`PendingStall`):
    `amount_soum` (bugungi patta yoki uning qoldig'i, `None` — bugun patta
    yo'q), `outstanding_soum` (oldingi qarz; manfiy — avans). To'lov tizimlari
    faqat `total_soum` ni ishlatadi.
    """

    stall_id: UUID
    vendor_id: UUID
    stall_code: str
    total_soum: int
    today_soum: int | None = None
    debt_soum: int = 0
    paid_today_soum: int = 0


class DueUnavailable(Exception):
    """Bugun bu rasta uchun onlayn to'lov qabul qilinmaydi — sabab bilan."""

    def __init__(self, reason: DueReason) -> None:
        super().__init__(reason)
        self.reason: DueReason = reason


async def stall_due(session: AsyncSession, *, market_id: UUID, stall_code: str) -> StallDue:
    """Rasta kodi (ANIQ moslik) bo'yicha bugungi to'lanadigan summa.

    Raises:
        DueUnavailable: rasta yo'q / sotuvchisiz / to'lanadigan summa yo'q.
    """
    as_of = business_today()
    money = await billing_repo.resolve_stall_day_money(
        session, market_id=market_id, as_of=as_of, stall_code=stall_code
    )
    if not money or money[0].stall_code != stall_code:
        raise DueUnavailable("stall_not_found")
    row = money[0]
    if row.vendor_id is None:
        raise DueUnavailable("stall_not_assigned")
    projection = await billing_repo.pending_projection(
        session, market_id=market_id, as_of=as_of, stall_code=stall_code
    )
    stall = projection.stall
    if stall is None or stall.stall_code != stall_code or stall.total_due_soum <= 0:
        raise DueUnavailable("nothing_due")
    return StallDue(
        row.stall_id,
        row.vendor_id,
        row.stall_code,
        int(stall.total_due_soum),
        today_soum=None if stall.amount_soum is None else int(stall.amount_soum),
        debt_soum=int(stall.outstanding_soum),
        paid_today_soum=int(stall.paid_today_soum),
    )
