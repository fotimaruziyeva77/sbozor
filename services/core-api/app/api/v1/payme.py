"""Payme Merchant API (0035, 261028) — onlayn to'lov.

=============================================================================
IKKI YO'L:

  POST /api/v1/payme              — Payme serverining JSON-RPC so'rovlari
                                     (CheckPerformTransaction, CreateTransaction,
                                     PerformTransaction, CancelTransaction,
                                     CheckTransaction, GetStatement).
  GET  /api/v1/payme/pay/{rasta}  — rastadagi QR-kod shu manzilga olib keladi:
                                     o'sha kungi summani hisoblab, sotuvchini
                                     Payme to'lov sahifasiga yo'naltiradi.

⛔ SUMMANI TIZIM BELGILAYDI, QISMAN TO'LOV YO'Q (buyurtmachi, 261028).
   Summa = `pending_projection().total_due_soum` — kassir kartasidagi
   «jami» bilan AYNI son (bugungi patta + eski qarz). Payme yuborgan summa
   undan farq qilsa `-31001` bilan rad etiladi.

⛔ KASSIR YO'Q: to'lov `method='payme'`, `cashier_id=NULL`, `shift_id=NULL`
   bilan yoziladi — ya'ni u hech bir kassir smenasining naqd hisobiga
   kirmaydi (smena sanog'i faqat `shift_id` bo'yicha).

⛔ AUTENTIFIKATSIYA: `Authorization: Basic base64("Paycom:<kalit>")`,
   `hmac.compare_digest`. Kalit yoki bozor sozlanmagan bo'lsa — 503
   (fail-closed). Payme protokoli bo'yicha xatolar HTTP 200 + JSON-RPC
   `error` bilan qaytadi.

⛔ BOZOR: kassa BITTA bozorga tegishli (`Settings.payme_market_id`) —
   Payme so'rovida bozor yo'q, faqat `account.rasta`.
=============================================================================
"""

from __future__ import annotations

import base64
import hmac
import time
from typing import TYPE_CHECKING, Any
from uuid import UUID

import structlog
from fastapi import APIRouter, Request, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from sbozor_core.enums import OutboxKind, OutboxRecipientKind, PaymentMethod, ReversalReason
from sbozor_core.timeutil import business_today

from app.jobs.notification_meta import outbox_payload
from app.repositories import billing_repo, binding_repo, outbox_repo, payme_repo, payment_repo

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from app.settings import Settings

log = structlog.get_logger(__name__)

__all__ = ["router"]

router = APIRouter(tags=["payme"])

TIMEOUT_MS = 43_200_000
"""Payme: yaratilganidan 12 soat o'tib bajarilmagan tranzaksiya bekor qilinadi."""

REASON_TIMEOUT = 4
ACCOUNT_FIELD = "rasta"

# --- JSON-RPC / Payme xato kodlari ---
ERR_PARSE = -32700
ERR_INVALID_REQUEST = -32600
ERR_METHOD_NOT_FOUND = -32601
ERR_AUTH = -32504
ERR_AMOUNT = -31001
ERR_TX_NOT_FOUND = -31003
ERR_CANNOT_CANCEL = -31007
ERR_CANNOT_PERFORM = -31008
ERR_STALL_NOT_FOUND = -31050
ERR_STALL_NOT_ASSIGNED = -31051
ERR_NOTHING_DUE = -31052
ERR_STALL_BUSY = -31053

_MESSAGES: dict[int, tuple[str, str, str]] = {
    ERR_PARSE: ("Ошибка разбора запроса", "So'rovni o'qib bo'lmadi", "Parse error"),
    ERR_INVALID_REQUEST: ("Неверный запрос", "Noto'g'ri so'rov", "Invalid request"),
    ERR_METHOD_NOT_FOUND: ("Метод не найден", "Usul topilmadi", "Method not found"),
    ERR_AUTH: ("Недостаточно привилегий", "Ruxsat yo'q", "Insufficient privileges"),
    ERR_AMOUNT: ("Неверная сумма", "Summa noto'g'ri", "Incorrect amount"),
    ERR_TX_NOT_FOUND: ("Транзакция не найдена", "Tranzaksiya topilmadi", "Transaction not found"),
    ERR_CANNOT_CANCEL: (
        "Невозможно отменить транзакцию",
        "Tranzaksiyani bekor qilib bo'lmaydi",
        "Unable to cancel transaction",
    ),
    ERR_CANNOT_PERFORM: (
        "Невозможно выполнить операцию",
        "Amalni bajarib bo'lmaydi",
        "Unable to perform operation",
    ),
    ERR_STALL_NOT_FOUND: ("Место не найдено", "Rasta topilmadi", "Stall not found"),
    ERR_STALL_NOT_ASSIGNED: (
        "За местом не закреплён продавец",
        "Rastaga sotuvchi biriktirilmagan",
        "No vendor is assigned to the stall",
    ),
    ERR_NOTHING_DUE: (
        "Сегодня нечего оплачивать",
        "Bugun to'lanadigan summa yo'q",
        "Nothing to pay today",
    ),
    ERR_STALL_BUSY: (
        "По этому месту уже ожидается другой платёж",
        "Bu rasta bo'yicha boshqa to'lov kutilmoqda",
        "Another payment for this stall is pending",
    ),
}


class PaymeError(Exception):
    """Payme protokoli xatosi — JSON-RPC `error` bo'lib qaytadi."""

    def __init__(self, code: int, *, data: str | None = None) -> None:
        super().__init__(code)
        self.code = code
        self.data = data


def _now_ms() -> int:
    return int(time.time() * 1000)


def _error_body(request_id: Any, code: int, data: str | None = None) -> dict[str, Any]:
    ru, uz, en = _MESSAGES.get(code, ("Системная ошибка", "Tizim xatosi", "System error"))
    error: dict[str, Any] = {"code": code, "message": {"ru": ru, "uz": uz, "en": en}}
    if data is not None:
        error["data"] = data
    return {"jsonrpc": "2.0", "id": request_id, "error": error}


def _authorized(request: Request, key: str) -> bool:
    header = request.headers.get("authorization", "")
    scheme, _, value = header.partition(" ")
    if scheme.lower() != "basic":
        return False
    try:
        decoded = base64.b64decode(value.strip(), validate=True).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return False
    _, _, password = decoded.partition(":")
    return hmac.compare_digest(password.encode(), key.encode())


def _market_id(settings: Settings) -> UUID | None:
    try:
        return UUID(settings.payme_market_id) if settings.payme_market_id else None
    except ValueError:
        return None


# ===========================================================================
# SUMMA — kassir kartasidagi «jami» bilan AYNI manba
# ===========================================================================


class _Due:
    """Rastaning bugungi to'lovi: identifikatorlar + to'lanadigan jami summa."""

    def __init__(self, stall_id: UUID, vendor_id: UUID, stall_code: str, total_soum: int) -> None:
        self.stall_id = stall_id
        self.vendor_id = vendor_id
        self.stall_code = stall_code
        self.total_soum = total_soum


async def _due(session: AsyncSession, *, market_id: UUID, stall_code: str) -> _Due:
    """Raise `PaymeError` — rasta yo'q / sotuvchisiz / to'lanadigan summa yo'q."""
    as_of = business_today()
    money = await billing_repo.resolve_stall_day_money(
        session, market_id=market_id, as_of=as_of, stall_code=stall_code
    )
    if not money or money[0].stall_code != stall_code:
        raise PaymeError(ERR_STALL_NOT_FOUND, data=ACCOUNT_FIELD)
    row = money[0]
    if row.vendor_id is None:
        raise PaymeError(ERR_STALL_NOT_ASSIGNED, data=ACCOUNT_FIELD)
    projection = await billing_repo.pending_projection(
        session, market_id=market_id, as_of=as_of, stall_code=stall_code
    )
    stall = projection.stall
    if stall is None or stall.stall_code != stall_code or stall.total_due_soum <= 0:
        raise PaymeError(ERR_NOTHING_DUE, data=ACCOUNT_FIELD)
    return _Due(row.stall_id, row.vendor_id, row.stall_code, int(stall.total_due_soum))


def _account_code(params: dict[str, Any]) -> str:
    account = params.get("account")
    value = account.get(ACCOUNT_FIELD) if isinstance(account, dict) else None
    if value is None or not str(value).strip():
        raise PaymeError(ERR_STALL_NOT_FOUND, data=ACCOUNT_FIELD)
    return str(value).strip()


def _amount_soum(params: dict[str, Any]) -> int:
    """Payme summasi tiyinda; bizda butun so'm. Kasr so'm — noto'g'ri summa."""
    amount = params.get("amount")
    if not isinstance(amount, int) or isinstance(amount, bool) or amount <= 0 or amount % 100:
        raise PaymeError(ERR_AMOUNT)
    return amount // 100


def _fiscal_detail(settings: Settings, due: _Due) -> dict[str, Any] | None:
    if not settings.payme_ikpu or not settings.payme_package_code:
        return None
    return {
        "receipt_type": 0,
        "items": [
            {
                "title": f"Bozor savdo joyi ijarasi, {due.stall_code}-rasta",
                "price": due.total_soum * 100,
                "count": 1,
                "code": settings.payme_ikpu,
                "package_code": settings.payme_package_code,
                "vat_percent": 0,
            }
        ],
    }


# ===========================================================================
# USULLAR
# ===========================================================================


async def _check_perform(
    session: AsyncSession, settings: Settings, market_id: UUID, params: dict[str, Any]
) -> dict[str, Any]:
    code = _account_code(params)
    due = await _due(session, market_id=market_id, stall_code=code)
    if _amount_soum(params) != due.total_soum:
        raise PaymeError(ERR_AMOUNT)
    pending = await payme_repo.pending_for_stall(
        session, market_id=market_id, stall_id=due.stall_id
    )
    if pending is not None:
        raise PaymeError(ERR_STALL_BUSY, data=ACCOUNT_FIELD)
    result: dict[str, Any] = {"allow": True}
    detail = _fiscal_detail(settings, due)
    if detail is not None:
        result["detail"] = detail
    return result


async def _create(
    session: AsyncSession, settings: Settings, market_id: UUID, params: dict[str, Any]
) -> dict[str, Any]:
    paycom_id = str(params.get("id") or "")
    if not paycom_id:
        raise PaymeError(ERR_INVALID_REQUEST)
    existing = await payme_repo.by_paycom_id(
        session, market_id=market_id, paycom_id=paycom_id, lock=True
    )
    now = _now_ms()
    if existing is not None:
        if existing.state != payme_repo.STATE_CREATED:
            raise PaymeError(ERR_CANNOT_PERFORM)
        if now - existing.create_time > TIMEOUT_MS:
            await payme_repo.set_state(
                session,
                market_id=market_id,
                tx_id=existing.id,
                state=payme_repo.STATE_CANCELLED,
                cancel_time=now,
                reason=REASON_TIMEOUT,
            )
            raise PaymeError(ERR_CANNOT_PERFORM)
        return {
            "create_time": existing.create_time,
            "transaction": str(existing.id),
            "state": existing.state,
        }

    code = _account_code(params)
    due = await _due(session, market_id=market_id, stall_code=code)
    amount = _amount_soum(params)
    if amount != due.total_soum:
        raise PaymeError(ERR_AMOUNT)
    if await payme_repo.pending_for_stall(session, market_id=market_id, stall_id=due.stall_id):
        raise PaymeError(ERR_STALL_BUSY, data=ACCOUNT_FIELD)
    paycom_time = params.get("time")
    tx = await payme_repo.create(
        session,
        market_id=market_id,
        paycom_id=paycom_id,
        paycom_time=int(paycom_time) if isinstance(paycom_time, int) else now,
        amount_soum=amount,
        stall_id=due.stall_id,
        vendor_id=due.vendor_id,
        create_time=now,
    )
    log.info("payme_transaction_created", stall_code=code, amount_soum=amount)
    return {"create_time": tx.create_time, "transaction": str(tx.id), "state": tx.state}


async def _perform(
    session: AsyncSession, settings: Settings, market_id: UUID, params: dict[str, Any]
) -> dict[str, Any]:
    tx = await payme_repo.by_paycom_id(
        session, market_id=market_id, paycom_id=str(params.get("id") or ""), lock=True
    )
    if tx is None:
        raise PaymeError(ERR_TX_NOT_FOUND)
    if tx.state == payme_repo.STATE_PERFORMED:
        return {"transaction": str(tx.id), "perform_time": tx.perform_time, "state": tx.state}
    if tx.state != payme_repo.STATE_CREATED:
        raise PaymeError(ERR_CANNOT_PERFORM)

    now = _now_ms()
    if now - tx.create_time > TIMEOUT_MS:
        await payme_repo.set_state(
            session,
            market_id=market_id,
            tx_id=tx.id,
            state=payme_repo.STATE_CANCELLED,
            cancel_time=now,
            reason=REASON_TIMEOUT,
        )
        raise PaymeError(ERR_CANNOT_PERFORM)

    # ⛔ SUMMA BU YERDA QAYTA TEKSHIRILMAYDI: pul sotuvchidan allaqachon
    #    yechilgan. Orada kassir naqd olgan bo'lsa ham to'lov yoziladi va
    #    ortig'i avans bo'ladi (FIFO) — rad etish pulni jimgina yo'qotardi.
    row, _created = await payment_repo.create_payment(
        session,
        market_id=market_id,
        payload=payment_repo.PaymentWrite(
            idempotency_key=f"payme:{tx.paycom_id}",
            stall_id=tx.stall_id,
            vendor_id=tx.vendor_id,
            service_date=business_today(),
            amount_soum=tx.amount_soum,
            quote_soum=tx.amount_soum,
            method=PaymentMethod.PAYME.value,
            override_reason=None,
            shift_id=None,
            cashier_id=None,
        ),
    )
    await payme_repo.set_state(
        session,
        market_id=market_id,
        tx_id=tx.id,
        state=payme_repo.STATE_PERFORMED,
        perform_time=now,
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
            cashier_name="Payme",
        ),
    )
    log.info("payme_transaction_performed", stall_code=tx.stall_code, amount_soum=tx.amount_soum)
    return {"transaction": str(tx.id), "perform_time": now, "state": payme_repo.STATE_PERFORMED}


async def _cancel(
    session: AsyncSession, settings: Settings, market_id: UUID, params: dict[str, Any]
) -> dict[str, Any]:
    tx = await payme_repo.by_paycom_id(
        session, market_id=market_id, paycom_id=str(params.get("id") or ""), lock=True
    )
    if tx is None:
        raise PaymeError(ERR_TX_NOT_FOUND)
    reason = params.get("reason")
    reason_code = int(reason) if isinstance(reason, int) else None
    now = _now_ms()

    if tx.state == payme_repo.STATE_CREATED:
        await payme_repo.set_state(
            session,
            market_id=market_id,
            tx_id=tx.id,
            state=payme_repo.STATE_CANCELLED,
            cancel_time=now,
            reason=reason_code,
        )
        return {"transaction": str(tx.id), "cancel_time": now, "state": payme_repo.STATE_CANCELLED}

    if tx.state == payme_repo.STATE_PERFORMED:
        if tx.payment_id is None:  # pragma: no cover - holat 2 to'lovsiz bo'lmaydi
            raise PaymeError(ERR_CANNOT_CANCEL)
        try:
            reversal = await payment_repo.reverse_payment(
                session,
                market_id=market_id,
                payment_id=tx.payment_id,
                reason_code=ReversalReason.CUSTOMER_REFUND.value,
                cashier_id=None,
                shift_id=None,
            )
        except payment_repo.PaymentAlreadyReversed as exc:
            raise PaymeError(ERR_CANNOT_CANCEL) from exc
        await payme_repo.set_state(
            session,
            market_id=market_id,
            tx_id=tx.id,
            state=payme_repo.STATE_CANCELLED_AFTER_PERFORM,
            cancel_time=now,
            reason=reason_code,
            reversal_payment_id=reversal.payment_id,
        )
        log.info("payme_transaction_refunded", stall_code=tx.stall_code)
        return {
            "transaction": str(tx.id),
            "cancel_time": now,
            "state": payme_repo.STATE_CANCELLED_AFTER_PERFORM,
        }

    # Allaqachon bekor qilingan — o'sha javob (idempotent).
    return {"transaction": str(tx.id), "cancel_time": tx.cancel_time, "state": tx.state}


async def _check(
    session: AsyncSession, settings: Settings, market_id: UUID, params: dict[str, Any]
) -> dict[str, Any]:
    tx = await payme_repo.by_paycom_id(
        session, market_id=market_id, paycom_id=str(params.get("id") or "")
    )
    if tx is None:
        raise PaymeError(ERR_TX_NOT_FOUND)
    return {
        "create_time": tx.create_time,
        "perform_time": tx.perform_time or 0,
        "cancel_time": tx.cancel_time or 0,
        "transaction": str(tx.id),
        "state": tx.state,
        "reason": tx.reason,
    }


async def _statement(
    session: AsyncSession, settings: Settings, market_id: UUID, params: dict[str, Any]
) -> dict[str, Any]:
    from_ms, to_ms = params.get("from"), params.get("to")
    if not isinstance(from_ms, int) or not isinstance(to_ms, int):
        raise PaymeError(ERR_INVALID_REQUEST)
    rows = await payme_repo.statement(session, market_id=market_id, from_ms=from_ms, to_ms=to_ms)
    return {
        "transactions": [
            {
                "id": tx.paycom_id,
                "time": tx.paycom_time,
                "amount": tx.amount_soum * 100,
                "account": {ACCOUNT_FIELD: tx.stall_code},
                "create_time": tx.create_time,
                "perform_time": tx.perform_time or 0,
                "cancel_time": tx.cancel_time or 0,
                "transaction": str(tx.id),
                "state": tx.state,
                "reason": tx.reason,
            }
            for tx in rows
        ]
    }


_METHODS = {
    "CheckPerformTransaction": _check_perform,
    "CreateTransaction": _create,
    "PerformTransaction": _perform,
    "CancelTransaction": _cancel,
    "CheckTransaction": _check,
    "GetStatement": _statement,
}


@router.post("", include_in_schema=False)
async def payme_merchant_api(request: Request) -> Response:
    """Payme JSON-RPC kirish nuqtasi — xatolar ham HTTP 200 bilan (protokol talabi)."""
    settings: Settings = request.app.state.settings
    key = settings.payme_key.get_secret_value()
    market_id = _market_id(settings)
    if not key or market_id is None:
        log.warning("payme_not_configured")
        return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content={})

    try:
        body = await request.json()
    except ValueError:
        return JSONResponse(_error_body(None, ERR_PARSE))
    request_id = body.get("id") if isinstance(body, dict) else None

    if not _authorized(request, key):
        log.warning("payme_auth_rejected")
        return JSONResponse(_error_body(request_id, ERR_AUTH))
    if not isinstance(body, dict) or not isinstance(body.get("params", {}), dict):
        return JSONResponse(_error_body(request_id, ERR_INVALID_REQUEST))

    handler = _METHODS.get(str(body.get("method")))
    if handler is None:
        return JSONResponse(_error_body(request_id, ERR_METHOD_NOT_FOUND))

    sessionmaker: async_sessionmaker[AsyncSession] = request.app.state.sessionmaker
    try:
        async with binding_repo.tenant_session(
            sessionmaker, market_id=market_id, request_id=f"payme:{body.get('method')}"
        ) as session:
            try:
                result = await handler(session, settings, market_id, body.get("params") or {})
            except PaymeError as exc:
                # ⛔ Xato JAVOBI tranzaksiyani BEKOR QILMAYDI: muddati o'tgan
                #    tranzaksiyaning bekor holati xato bilan birga saqlanishi
                #    kerak (Payme protokoli).
                return JSONResponse(_error_body(request_id, exc.code, exc.data))
    except Exception:
        log.exception("payme_internal_error", method=body.get("method"))
        return JSONResponse(_error_body(request_id, -32400))
    return JSONResponse({"jsonrpc": "2.0", "id": request_id, "result": result})


# ===========================================================================
# QR-KOD -> PAYME TO'LOV SAHIFASI
# ===========================================================================

_PAGE = """<!doctype html>
<html lang="uz"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SBOZOR — to'lov</title>
<style>body{{font-family:system-ui,sans-serif;max-width:28rem;margin:3rem auto;padding:0 1rem;
color:#1f2937}}h1{{font-size:1.25rem}}p{{line-height:1.5}}</style></head>
<body><h1>{title}</h1><p>{body}</p></body></html>"""


def _page(title: str, body: str, code: int = 200) -> HTMLResponse:
    return HTMLResponse(_PAGE.format(title=title, body=body), status_code=code)


@router.get("/pay/{stall_code}", include_in_schema=False)
async def payme_pay(stall_code: str, request: Request) -> Response:
    """Rastadagi QR-kod: bugungi summa bilan Payme to'lov sahifasiga yo'naltiradi."""
    settings: Settings = request.app.state.settings
    market_id = _market_id(settings)
    if market_id is None or not settings.payme_merchant_id:
        return _page("To'lov hozircha ulanmagan", "Iltimos, kassirga murojaat qiling.", 503)

    code = stall_code.strip()[:32]
    sessionmaker: async_sessionmaker[AsyncSession] = request.app.state.sessionmaker
    async with binding_repo.tenant_session(
        sessionmaker, market_id=market_id, request_id="payme:pay"
    ) as session:
        try:
            due = await _due(session, market_id=market_id, stall_code=code)
        except PaymeError as exc:
            _, uz, _ = _MESSAGES[exc.code]
            return _page(uz, "Savol bo'lsa, kassirga murojaat qiling.", 404)

    params = (
        f"m={settings.payme_merchant_id};ac.{ACCOUNT_FIELD}={due.stall_code};"
        f"a={due.total_soum * 100};l=uz"
    )
    encoded = base64.b64encode(params.encode()).decode()
    return RedirectResponse(
        f"{settings.payme_checkout_url.rstrip('/')}/{encoded}",
        status_code=status.HTTP_302_FOUND,
    )
