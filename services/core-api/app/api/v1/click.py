"""Click Shop API (0035, 261029) — onlayn to'lov.

=============================================================================
  POST /api/v1/click/prepare   — Click: «shu to'lovni qabul qilasizmi?»
  POST /api/v1/click/complete  — Click: to'lov natijasi

So'rov `application/x-www-form-urlencoded`, javob JSON. Imzo:
  prepare:  md5(click_trans_id + service_id + SECRET + merchant_trans_id
                + amount + action + sign_time)
  complete: md5(click_trans_id + service_id + SECRET + merchant_trans_id
                + merchant_prepare_id + amount + action + sign_time)

`merchant_trans_id` — RASTA RAQAMI. Summa — `online_payment.stall_due()`
(Payme bilan AYNI son), qisman to'lov yo'q. Kalit yoki bozor sozlanmagan
bo'lsa — 503 (fail-closed).

⛔ COMPLETE'DA SUMMA QAYTA TEKSHIRILADI: Prepare bilan Complete orasida
   rasta boshqa yo'l bilan to'langan bo'lsa (kassir, Payme), Click'ga
   `-4` qaytadi va u to'lovni bekor qiladi — ikki marta to'lov bo'lmaydi.
=============================================================================
"""

from __future__ import annotations

import hashlib
import hmac
from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING, Any
from urllib.parse import parse_qs
from uuid import UUID

import structlog
from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse, Response
from sbozor_core.enums import OutboxKind, OutboxRecipientKind, PaymentMethod
from sbozor_core.timeutil import business_today

from app.jobs.notification_meta import outbox_payload
from app.repositories import binding_repo, click_repo, outbox_repo, payment_repo
from app.services.online_payment import DueUnavailable, stall_due
from app.services.payment_merchants import ClickMerchant, click_by_service, click_merchants

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from app.settings import Settings

log = structlog.get_logger(__name__)

__all__ = ["router"]

router = APIRouter(tags=["click"])

OK = 0
ERR_SIGN = -1
ERR_AMOUNT = -2
ERR_ACTION = -3
ERR_ALREADY_PAID = -4
ERR_USER = -5
ERR_TX_NOT_FOUND = -6
ERR_REQUEST = -8
ERR_CANCELLED = -9

_NOTES = {
    OK: "Success",
    ERR_SIGN: "SIGN CHECK FAILED!",
    ERR_AMOUNT: "Incorrect parameter amount",
    ERR_ACTION: "Action not found",
    ERR_ALREADY_PAID: "Already paid",
    ERR_USER: "User does not exist",
    ERR_TX_NOT_FOUND: "Transaction does not exist",
    ERR_REQUEST: "Error in request from click",
    ERR_CANCELLED: "Transaction cancelled",
}

_REQUIRED = (
    "click_trans_id",
    "service_id",
    "merchant_trans_id",
    "amount",
    "action",
    "sign_time",
    "sign_string",
)


async def _form(request: Request) -> dict[str, str]:
    raw = (await request.body()).decode("utf-8", errors="replace")
    return {key: values[0] for key, values in parse_qs(raw, keep_blank_values=True).items()}


def _sign_ok(form: dict[str, str], secret: str, *, complete: bool) -> bool:
    parts = [form["click_trans_id"], form["service_id"], secret, form["merchant_trans_id"]]
    if complete:
        parts.append(form.get("merchant_prepare_id", ""))
    parts += [form["amount"], form["action"], form["sign_time"]]
    expected = hashlib.md5("".join(parts).encode(), usedforsecurity=False).hexdigest()
    return hmac.compare_digest(expected, form["sign_string"].lower())


def _amount(form: dict[str, str]) -> Decimal | None:
    try:
        value = Decimal(form["amount"])
    except (InvalidOperation, KeyError):
        return None
    return value if value.is_finite() else None


def _reply(form: dict[str, str], error: int, **ids: int | None) -> JSONResponse:
    body: dict[str, Any] = {
        "click_trans_id": form.get("click_trans_id"),
        "merchant_trans_id": form.get("merchant_trans_id"),
        "error": error,
        "error_note": _NOTES.get(error, "Error"),
    }
    body.update({key: value for key, value in ids.items() if value is not None})
    return JSONResponse(body)


def _ints(form: dict[str, str], *names: str) -> dict[str, int] | None:
    out: dict[str, int] = {}
    for name in names:
        try:
            out[name] = int(form[name])
        except (KeyError, ValueError):
            return None
    return out


async def _validated(
    request: Request, *, complete: bool
) -> tuple[ClickMerchant, dict[str, str], dict[str, int]] | Response:
    settings: Settings = request.app.state.settings
    if not click_merchants(settings):
        log.warning("click_not_configured")
        return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content={})
    form = await _form(request)
    names: tuple[str, ...] = ("click_trans_id", "service_id", "action", "error")
    if complete:
        names = (*names, "merchant_prepare_id")
    numbers = _ints(form, *names) if all(key in form for key in _REQUIRED) else None
    if numbers is None:
        return _reply(form, ERR_REQUEST)
    # ⛔ Bozor `service_id` dan: har bozorning o'z kassasi va o'z kaliti.
    config = click_by_service(settings, form["service_id"])
    if config is None:
        log.warning("click_unknown_service")
        return _reply(form, ERR_REQUEST)
    if not _sign_ok(form, config.secret_key, complete=complete):
        log.warning("click_sign_rejected")
        return _reply(form, ERR_SIGN)
    if numbers["action"] != (1 if complete else 0):
        return _reply(form, ERR_ACTION)
    return config, form, numbers


def _session(request: Request, market_id: UUID, action: str) -> Any:
    sessionmaker: async_sessionmaker[AsyncSession] = request.app.state.sessionmaker
    return binding_repo.tenant_session(
        sessionmaker, market_id=market_id, request_id=f"click:{action}"
    )


@router.post("/prepare", include_in_schema=False)
async def click_prepare(request: Request) -> Response:
    checked = await _validated(request, complete=False)
    if isinstance(checked, Response):
        return checked
    config, form, numbers = checked
    market_id = config.market_id
    amount = _amount(form)
    code = form["merchant_trans_id"].strip()

    async with _session(request, market_id, "prepare") as session:
        existing = await click_repo.by_click_trans_id(
            session, market_id=market_id, click_trans_id=numbers["click_trans_id"]
        )
        if existing is not None:
            if existing.state == click_repo.STATE_CANCELLED:
                return _reply(form, ERR_CANCELLED)
            return _reply(form, OK, merchant_prepare_id=existing.prepare_id)
        try:
            due = await stall_due(session, market_id=market_id, stall_code=code)
        except DueUnavailable as exc:
            error = ERR_ALREADY_PAID if exc.reason == "nothing_due" else ERR_USER
            return _reply(form, error)
        if amount is None or amount != due.total_soum:
            return _reply(form, ERR_AMOUNT)
        tx = await click_repo.create(
            session,
            market_id=market_id,
            click_trans_id=numbers["click_trans_id"],
            click_paydoc_id=int(form.get("click_paydoc_id") or 0),
            amount_soum=due.total_soum,
            stall_id=due.stall_id,
            vendor_id=due.vendor_id,
        )
    log.info("click_prepared", stall_code=code, amount_soum=due.total_soum)
    return _reply(form, OK, merchant_prepare_id=tx.prepare_id)


@router.post("/complete", include_in_schema=False)
async def click_complete(request: Request) -> Response:
    checked = await _validated(request, complete=True)
    if isinstance(checked, Response):
        return checked
    config, form, numbers = checked
    market_id = config.market_id
    amount = _amount(form)

    async with _session(request, market_id, "complete") as session:
        tx = await click_repo.by_prepare_id(
            session, market_id=market_id, prepare_id=numbers["merchant_prepare_id"], lock=True
        )
        if tx is None or tx.click_trans_id != numbers["click_trans_id"]:
            return _reply(form, ERR_TX_NOT_FOUND)
        if tx.state == click_repo.STATE_COMPLETED:
            return _reply(form, ERR_ALREADY_PAID, merchant_confirm_id=tx.prepare_id)
        if tx.state == click_repo.STATE_CANCELLED:
            return _reply(form, ERR_CANCELLED)
        if amount is None or amount != tx.amount_soum:
            return _reply(form, ERR_AMOUNT)

        async def cancel(error: int) -> JSONResponse:
            await click_repo.set_state(
                session, market_id=market_id, tx_id=tx.id, state=click_repo.STATE_CANCELLED
            )
            return _reply(form, error)

        if numbers["error"] < 0:
            # Click to'lovni amalga oshira olmadi (masalan mablag' yetmadi).
            return await cancel(ERR_CANCELLED)
        try:
            due = await stall_due(session, market_id=market_id, stall_code=tx.stall_code)
        except DueUnavailable:
            return await cancel(ERR_ALREADY_PAID)
        if due.total_soum != tx.amount_soum:
            return await cancel(ERR_AMOUNT)

        row, _created = await payment_repo.create_payment(
            session,
            market_id=market_id,
            payload=payment_repo.PaymentWrite(
                idempotency_key=f"click:{tx.click_trans_id}",
                stall_id=tx.stall_id,
                vendor_id=tx.vendor_id,
                service_date=business_today(),
                amount_soum=tx.amount_soum,
                quote_soum=tx.amount_soum,
                method=PaymentMethod.CLICK.value,
                override_reason=None,
                shift_id=None,
                cashier_id=None,
            ),
        )
        await click_repo.set_state(
            session,
            market_id=market_id,
            tx_id=tx.id,
            state=click_repo.STATE_COMPLETED,
            payment_id=row.payment_id,
        )
        await outbox_repo.enqueue(
            session,
            market_id=market_id,
            kind=OutboxKind.PAYMENT_RECEIPT.value,
            recipient_kind=OutboxRecipientKind.VENDOR.value,
            vendor_id=tx.vendor_id,
            dedupe_key=f"receipt:{row.payment_id}",
            payload=outbox_payload(
                OutboxKind.PAYMENT_RECEIPT.value,
                amount_soum=row.amount_soum,
                stall_code=tx.stall_code,
                paid_at=row.created_at.isoformat(),
                cashier_name="Click",
            ),
        )
    log.info("click_completed", stall_code=tx.stall_code, amount_soum=tx.amount_soum)
    return _reply(form, OK, merchant_confirm_id=tx.prepare_id)
