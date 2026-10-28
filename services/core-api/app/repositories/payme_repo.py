"""`payme_transactions` — Payme Merchant API tranzaksiyalari (0035).

Holat mashinasi Payme protokolidan: 1 yaratildi -> 2 bajarildi; 1 -> -1
bekor (bajarilmasdan); 2 -> -2 bekor (bajarilgandan keyin, storno bilan).
Pul yozuvi `payments` da; bu jadval referens va holat.

⛔ CHAQIRUVCHI TENANT KONTEKSTINI O'RNATGAN BO'LISHI SHART (`binding_repo.
   tenant_session`) — so'rovdagi `market_id` NIYAT, RLS esa KAFOLAT.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from sbozor_core.models import PaymeTransaction, Stall
from sqlalchemy import insert, select, update

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

__all__ = [
    "STATE_CANCELLED",
    "STATE_CANCELLED_AFTER_PERFORM",
    "STATE_CREATED",
    "STATE_PERFORMED",
    "PaymeTx",
    "by_paycom_id",
    "create",
    "pending_for_stall",
    "set_state",
    "statement",
]

STATE_CREATED = 1
STATE_PERFORMED = 2
STATE_CANCELLED = -1
STATE_CANCELLED_AFTER_PERFORM = -2


@dataclass(frozen=True, slots=True)
class PaymeTx:
    """Bitta tranzaksiya — Payme javoblari uchun kerakli maydonlar."""

    id: UUID
    paycom_id: str
    paycom_time: int
    amount_soum: int
    stall_id: UUID
    vendor_id: UUID
    stall_code: str
    state: int
    create_time: int
    perform_time: int | None
    cancel_time: int | None
    reason: int | None
    payment_id: UUID | None


_COLUMNS = (
    PaymeTransaction.id,
    PaymeTransaction.paycom_id,
    PaymeTransaction.paycom_time,
    PaymeTransaction.amount_soum,
    PaymeTransaction.stall_id,
    PaymeTransaction.vendor_id,
    Stall.code,
    PaymeTransaction.state,
    PaymeTransaction.create_time,
    PaymeTransaction.perform_time,
    PaymeTransaction.cancel_time,
    PaymeTransaction.reason,
    PaymeTransaction.payment_id,
)


def _select(market_id: UUID) -> Any:
    return (
        select(*_COLUMNS)
        .join(
            Stall,
            (Stall.market_id == PaymeTransaction.market_id)
            & (Stall.id == PaymeTransaction.stall_id),
        )
        .where(PaymeTransaction.market_id == market_id)
    )


def _tx(row: Any) -> PaymeTx:
    return PaymeTx(
        id=row[0],
        paycom_id=str(row[1]),
        paycom_time=int(row[2]),
        amount_soum=int(row[3]),
        stall_id=row[4],
        vendor_id=row[5],
        stall_code=str(row[6]),
        state=int(row[7]),
        create_time=int(row[8]),
        perform_time=None if row[9] is None else int(row[9]),
        cancel_time=None if row[10] is None else int(row[10]),
        reason=None if row[11] is None else int(row[11]),
        payment_id=row[12],
    )


async def by_paycom_id(
    session: AsyncSession, *, market_id: UUID, paycom_id: str, lock: bool = False
) -> PaymeTx | None:
    """Payme `id` si bo'yicha; `lock=True` — holat o'zgartirishdan oldin qator qulfi."""
    stmt = _select(market_id).where(PaymeTransaction.paycom_id == paycom_id)
    if lock:
        stmt = stmt.with_for_update(of=PaymeTransaction)
    row = (await session.execute(stmt)).one_or_none()
    return None if row is None else _tx(row)


async def pending_for_stall(
    session: AsyncSession, *, market_id: UUID, stall_id: UUID
) -> PaymeTx | None:
    """Shu rasta bo'yicha hali bajarilmagan (holat 1) tranzaksiya — bitta bo'lishi mumkin."""
    stmt = _select(market_id).where(
        PaymeTransaction.stall_id == stall_id,
        PaymeTransaction.state == STATE_CREATED,
    )
    row = (await session.execute(stmt.limit(1))).one_or_none()
    return None if row is None else _tx(row)


async def create(
    session: AsyncSession,
    *,
    market_id: UUID,
    paycom_id: str,
    paycom_time: int,
    amount_soum: int,
    stall_id: UUID,
    vendor_id: UUID,
    create_time: int,
) -> PaymeTx:
    """Yangi tranzaksiya (holat 1)."""
    await session.execute(
        insert(PaymeTransaction).values(
            market_id=market_id,
            paycom_id=paycom_id,
            paycom_time=paycom_time,
            amount_soum=amount_soum,
            stall_id=stall_id,
            vendor_id=vendor_id,
            state=STATE_CREATED,
            create_time=create_time,
        )
    )
    created = await by_paycom_id(session, market_id=market_id, paycom_id=paycom_id)
    if created is None:  # pragma: no cover - yozilgan qator RLS ostida ko'rinadi
        raise RuntimeError("payme_transactions: yozilgan qator topilmadi")
    return created


async def set_state(
    session: AsyncSession,
    *,
    market_id: UUID,
    tx_id: UUID,
    state: int,
    perform_time: int | None = None,
    cancel_time: int | None = None,
    reason: int | None = None,
    payment_id: UUID | None = None,
    reversal_payment_id: UUID | None = None,
) -> None:
    """Holatni o'zgartiradi; berilmagan vaqt/havola maydonlari tegilmaydi."""
    values: dict[str, Any] = {"state": state}
    if perform_time is not None:
        values["perform_time"] = perform_time
    if cancel_time is not None:
        values["cancel_time"] = cancel_time
    if reason is not None:
        values["reason"] = reason
    if payment_id is not None:
        values["payment_id"] = payment_id
    if reversal_payment_id is not None:
        values["reversal_payment_id"] = reversal_payment_id
    await session.execute(
        update(PaymeTransaction)
        .where(PaymeTransaction.market_id == market_id, PaymeTransaction.id == tx_id)
        .values(**values)
    )


async def statement(
    session: AsyncSession, *, market_id: UUID, from_ms: int, to_ms: int
) -> list[PaymeTx]:
    """`GetStatement` — Payme vaqti (`paycom_time`) oralig'idagi tranzaksiyalar."""
    stmt = (
        _select(market_id)
        .where(PaymeTransaction.paycom_time >= from_ms, PaymeTransaction.paycom_time <= to_ms)
        .order_by(PaymeTransaction.paycom_time, PaymeTransaction.id)
    )
    return [_tx(row) for row in (await session.execute(stmt)).all()]
