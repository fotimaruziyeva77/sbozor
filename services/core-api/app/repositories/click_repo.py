"""`click_transactions` — Click Shop API tranzaksiyalari (0035).

Holatlar: `prepared` (Prepare) -> `completed` (Complete muvaffaqiyatli) yoki
`cancelled` (Complete xato bilan keldi yoki rad etildi). Pul yozuvi `payments`.

⛔ CHAQIRUVCHI TENANT KONTEKSTINI O'RNATGAN BO'LISHI SHART.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sbozor_core.models import ClickTransaction, Stall
from sqlalchemy import insert, select, update

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

__all__ = [
    "STATE_CANCELLED",
    "STATE_COMPLETED",
    "STATE_PREPARED",
    "ClickTx",
    "by_click_trans_id",
    "by_prepare_id",
    "create",
    "set_state",
]

STATE_PREPARED = "prepared"
STATE_COMPLETED = "completed"
STATE_CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class ClickTx:
    """Bitta Click tranzaksiyasi."""

    id: UUID
    prepare_id: int
    click_trans_id: int
    amount_soum: int
    stall_id: UUID
    vendor_id: UUID
    stall_code: str
    state: str
    payment_id: UUID | None


_COLUMNS = (
    ClickTransaction.id,
    ClickTransaction.prepare_id,
    ClickTransaction.click_trans_id,
    ClickTransaction.amount_soum,
    ClickTransaction.stall_id,
    ClickTransaction.vendor_id,
    Stall.code,
    ClickTransaction.state,
    ClickTransaction.payment_id,
)


def _select(market_id: UUID) -> Any:
    return (
        select(*_COLUMNS)
        .join(
            Stall,
            (Stall.market_id == ClickTransaction.market_id)
            & (Stall.id == ClickTransaction.stall_id),
        )
        .where(ClickTransaction.market_id == market_id)
    )


def _tx(row: Any) -> ClickTx:
    return ClickTx(
        id=row[0],
        prepare_id=int(row[1]),
        click_trans_id=int(row[2]),
        amount_soum=int(row[3]),
        stall_id=row[4],
        vendor_id=row[5],
        stall_code=str(row[6]),
        state=str(row[7]),
        payment_id=row[8],
    )


async def by_click_trans_id(
    session: AsyncSession, *, market_id: UUID, click_trans_id: int
) -> ClickTx | None:
    stmt = _select(market_id).where(ClickTransaction.click_trans_id == click_trans_id)
    row = (await session.execute(stmt)).one_or_none()
    return None if row is None else _tx(row)


async def by_prepare_id(
    session: AsyncSession, *, market_id: UUID, prepare_id: int, lock: bool = False
) -> ClickTx | None:
    stmt = _select(market_id).where(ClickTransaction.prepare_id == prepare_id)
    if lock:
        stmt = stmt.with_for_update(of=ClickTransaction)
    row = (await session.execute(stmt)).one_or_none()
    return None if row is None else _tx(row)


async def create(
    session: AsyncSession,
    *,
    market_id: UUID,
    click_trans_id: int,
    click_paydoc_id: int,
    amount_soum: int,
    stall_id: UUID,
    vendor_id: UUID,
) -> ClickTx:
    """Yangi `prepared` tranzaksiya."""
    await session.execute(
        insert(ClickTransaction).values(
            market_id=market_id,
            click_trans_id=click_trans_id,
            click_paydoc_id=click_paydoc_id,
            amount_soum=amount_soum,
            stall_id=stall_id,
            vendor_id=vendor_id,
            state=STATE_PREPARED,
        )
    )
    created = await by_click_trans_id(session, market_id=market_id, click_trans_id=click_trans_id)
    if created is None:  # pragma: no cover - yozilgan qator RLS ostida ko'rinadi
        raise RuntimeError("click_transactions: yozilgan qator topilmadi")
    return created


async def set_state(
    session: AsyncSession,
    *,
    market_id: UUID,
    tx_id: UUID,
    state: str,
    payment_id: UUID | None = None,
) -> None:
    values: dict[str, Any] = {"state": state}
    if state == STATE_COMPLETED:
        values["completed_at"] = datetime.now(UTC)
    if payment_id is not None:
        values["payment_id"] = payment_id
    await session.execute(
        update(ClickTransaction)
        .where(ClickTransaction.market_id == market_id, ClickTransaction.id == tx_id)
        .values(**values)
    )
