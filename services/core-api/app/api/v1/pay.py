"""Rastadagi QR-kod sahifasi (0035) — `GET /api/v1/pay/{rasta}`.

Sotuvchi QR-kodni skanerlaydi va shu sahifa ochiladi: rasta raqami, bugungi
summa va sozlangan to'lov tizimlarining tugmalari (Payme, Click). Summa
`online_payment.stall_due()` dan — Payme/Click serverga so'rov yuborganda ham
AYNI son tekshiriladi.

⛔ Sahifada shaxsiy ma'lumot yo'q: faqat rasta raqami va summa.
⛔ Sessiyasiz. Bozor manzildan: `/pay/{bozor}/{rasta}` (har bozor o'z kassasi,
   261030). Eski `/pay/{rasta}` — `PAY_DEFAULT_MARKET` bozori: Karmanadagi
   rastalarga yopishtirilgan QR-kodlar o'zgarmaydi.
"""

from __future__ import annotations

import base64
import html
from typing import TYPE_CHECKING
from urllib.parse import urlencode
from uuid import UUID

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.repositories import binding_repo
from app.services.online_payment import DueUnavailable, StallDue, stall_due
from app.services.payment_merchants import (
    click_for_market,
    default_market,
    market_by_slug,
    payme_for_market,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from app.settings import Settings

__all__ = ["router"]

router = APIRouter(tags=["pay"])

_REASONS = {
    "stall_not_found": "Rasta topilmadi",
    "stall_not_assigned": "Rastaga sotuvchi biriktirilmagan",
    "nothing_due": "Bugun to'lanadigan summa yo'q",
}

_NOT_CONNECTED = "<h1>Onlayn to'lov hozircha ulanmagan</h1><p>Kassirga murojaat qiling.</p>"

_PAGE = """<!doctype html>
<html lang="uz"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SBOZOR — to'lov</title>
<style>
body{{font-family:system-ui,sans-serif;max-width:26rem;margin:2.5rem auto;padding:0 1rem;
color:#1f2937;background:#f8fafc}}
h1{{font-size:1.2rem;margin:0 0 .25rem}}p{{line-height:1.5;margin:.25rem 0}}
.sum{{font-size:2rem;font-weight:700;margin:1rem 0 1.5rem}}
a.btn{{display:block;text-align:center;padding:1rem;border-radius:.75rem;margin:.75rem 0;
font-weight:600;text-decoration:none;color:#fff}}
.payme{{background:#00a0c6}}.click{{background:#0072ff}}
</style></head><body>{body}</body></html>"""


def _payme_url(settings: Settings, market_id: UUID, due: StallDue) -> str | None:
    merchant = payme_for_market(settings, market_id)
    if merchant is None or not merchant.merchant_id:
        return None
    params = (
        f"m={merchant.merchant_id};ac.{merchant.account_field}={due.stall_code};"
        f"a={due.total_soum * 100};l=uz"
    )
    encoded = base64.b64encode(params.encode()).decode()
    return f"{settings.payme_checkout_url.rstrip('/')}/{encoded}"


def _click_url(settings: Settings, market_id: UUID, due: StallDue) -> str | None:
    merchant = click_for_market(settings, market_id)
    if merchant is None or not merchant.merchant_id:
        return None
    query = urlencode(
        {
            "service_id": merchant.service_id,
            "merchant_id": merchant.merchant_id,
            "amount": due.total_soum,
            "transaction_param": due.stall_code,
        }
    )
    return f"{settings.click_pay_url.rstrip('?')}?{query}"


def _page(body: str, status_code: int = 200) -> HTMLResponse:
    return HTMLResponse(_PAGE.format(body=body), status_code=status_code)


@router.get("/{stall_code}", include_in_schema=False)
async def pay_page(stall_code: str, request: Request) -> HTMLResponse:
    """Eski QR-kod (Karmana): bozor `PAY_DEFAULT_MARKET` dan."""
    settings: Settings = request.app.state.settings
    return await _render(request, default_market(settings), stall_code)


@router.get("/{market}/{stall_code}", include_in_schema=False)
async def pay_page_for_market(market: str, stall_code: str, request: Request) -> HTMLResponse:
    """QR-kod sahifasi: `/pay/{bozor}/{rasta}` — summa + o'sha bozor kassasi tugmalari."""
    settings: Settings = request.app.state.settings
    return await _render(request, market_by_slug(settings, market.strip().lower()[:32]), stall_code)


async def _render(request: Request, market_id: UUID | None, stall_code: str) -> HTMLResponse:
    settings: Settings = request.app.state.settings
    if market_id is None:
        return _page(_NOT_CONNECTED, 503)

    sessionmaker: async_sessionmaker[AsyncSession] = request.app.state.sessionmaker
    async with binding_repo.tenant_session(
        sessionmaker, market_id=market_id, request_id="pay:page"
    ) as session:
        try:
            due = await stall_due(session, market_id=market_id, stall_code=stall_code.strip()[:32])
        except DueUnavailable as exc:
            return _page(
                f"<h1>{_REASONS[exc.reason]}</h1><p>Savol bo'lsa, kassirga murojaat qiling.</p>",
                404,
            )

    buttons = []
    payme = _payme_url(settings, market_id, due)
    if payme is not None:
        buttons.append(f'<a class="btn payme" href="{html.escape(payme)}">Payme bilan to\'lash</a>')
    click = _click_url(settings, market_id, due)
    if click is not None:
        buttons.append(f'<a class="btn click" href="{html.escape(click)}">Click bilan to\'lash</a>')
    if not buttons:
        return _page(_NOT_CONNECTED, 503)

    amount = f"{due.total_soum:,}".replace(",", " ")
    body = (
        f"<h1>{html.escape(due.stall_code)}-rasta</h1>"
        "<p>Bugungi to'lov (qarz bilan):</p>"
        f'<p class="sum">{amount} so\'m</p>' + "".join(buttons)
    )
    return _page(body)
