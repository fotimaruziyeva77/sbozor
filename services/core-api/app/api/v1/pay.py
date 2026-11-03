"""Rastadagi QR-kod sahifasi (0035) — `GET /api/v1/pay/{rasta}`.

Sotuvchi QR-kodni skanerlaydi va shu sahifa ochiladi: rasta raqami, bugungi
summa va sozlangan to'lov tizimlarining tugmalari (Payme, Click). Summa
`online_payment.stall_due()` dan — Payme/Click serverga so'rov yuborganda ham
AYNI son tekshiriladi.

⛔ Sahifada shaxsiy ma'lumot yo'q: faqat rasta raqami va summa.
⛔ Sessiyasiz. Bozor manzildan: `/pay/{bozor}/{rasta}` (har bozor o'z kassasi,
   261030). Eski `/pay/{rasta}` — `PAY_DEFAULT_MARKET` bozori: Karmanadagi
   rastalarga yopishtirilgan QR-kodlar o'zgarmaydi.

Ko'rinish (261102) — rastadagi QR stiker bilan bir uslubda:

  * Rasmlar `app/assets/pay/` da va sahifaning O'ZIGA (data URI) qo'yiladi:
    alohida marshrut ochilmaydi, sahifa bitta so'rovda keladi (~60 KB).
    Bozor logosi — `<bozor nomi>.webp`; yo'q bo'lsa sarlavhada bozor nomi.
  * Izoh qatorlari (bugungi patta / oldingi qarz yoki avans) — kassir
    kartasidagi AYNI sonlar. Jami ulardan HISOBLANMAYDI (u `total_soum`):
    qatorlar yig'indisi jamiga teng kelmasa, ular ko'rsatilmaydi.
  * `Cache-Control: no-store` — to'lovdan keyin «orqaga» bosilganda brauzer
    eski summani keshdan ko'rsatmasin.
"""

from __future__ import annotations

import base64
import html
import re
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING, Literal
from urllib.parse import urlencode
from uuid import UUID

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from sbozor_core.timeutil import business_today
from sqlalchemy import text

from app.repositories import binding_repo
from app.services.online_payment import DueUnavailable, StallDue, stall_due
from app.services.payment_merchants import (
    click_for_market,
    default_market,
    default_slug,
    market_by_slug,
    payme_for_market,
)

if TYPE_CHECKING:
    from datetime import date

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from app.settings import Settings

__all__ = ["router"]

router = APIRouter(tags=["pay"])

_ASSETS = Path(__file__).resolve().parents[2] / "assets" / "pay"
_SLUG = re.compile(r"[a-z][a-z0-9-]{1,31}")

_MARKET_NAME = text("SELECT name FROM markets")
"""ATAYIN filtrsiz — `market_repo._CURRENT_MARKET` bilan bir xil qoida: `markets`
policy'si aynan joriy bozorni qaytaradi."""

_MONTHS = (
    "yanvar", "fevral", "mart", "aprel", "may", "iyun",
    "iyul", "avgust", "sentabr", "oktabr", "noyabr", "dekabr",
)  # fmt: skip

_REASONS = {
    "stall_not_found": "Rasta topilmadi",
    "stall_not_assigned": "Rastaga sotuvchi biriktirilmagan",
    "nothing_due": "Bugun to'lanadigan summa yo'q",
}

_HELP = "Savol bo'lsa — bozor kassiriga murojaat qiling."

_SVG = (
    '<svg viewBox="0 0 24 24" width="{s}" height="{s}" fill="none" stroke="currentColor" '
    'stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{d}</svg>'
)
_DOT = '<circle cx="12" cy="{y}" r="1.4" fill="currentColor" stroke="none"/>'
_ICONS = {
    "ok": _SVG.format(s=30, d='<path d="M5 12.5l4.5 4.5L19 7.5"/>'),
    "info": _SVG.format(s=30, d='<path d="M12 11v6.5"/>' + _DOT.format(y=7)),
    "warn": _SVG.format(s=30, d='<path d="M12 6v8"/>' + _DOT.format(y=18)),
}
_ARROW = _SVG.format(s=20, d='<path d="M5 12h13M13 6.5l5.5 5.5-5.5 5.5"/>')

_CSS = """
:root{--kobalt:#012a84;--tun:#001a5c;--fon:#eef1f7;--siyoh:#0e1630;--xira:#59647f;--chiziq:#dce2ec}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;min-height:100vh;background:var(--fon);color:var(--siyoh);
font:16px/1.45 system-ui,-apple-system,"Segoe UI",Roboto,"Noto Sans",Arial,sans-serif}
.top{padding:max(16px,env(safe-area-inset-top)) 16px 58px;text-align:center;
background:radial-gradient(130% 100% at 50% 0,#0b3aa6 0,var(--kobalt) 55%,var(--tun) 100%)}
.logo{display:block;width:min(240px,68vw);height:auto;margin:0 auto}
.mname{margin:10px 0 6px;color:#fff;font:700 24px/1.2 Georgia,"Noto Serif","Times New Roman",serif}
.wrap{max-width:440px;margin:-44px auto 0;padding:0 14px max(28px,env(safe-area-inset-bottom))}
.ticket{position:relative;background:#fff;border-radius:22px;padding:18px 20px 22px;
box-shadow:0 18px 36px -18px rgba(1,42,132,.45),0 1px 2px rgba(14,22,48,.08)}
.head{display:flex;align-items:flex-start;justify-content:space-between;gap:12px}
.head p{margin:0}
.head span,.cap,.choose{display:block;font-size:12px;font-weight:700;letter-spacing:.14em;
text-transform:uppercase;color:var(--xira)}
.rasta b{display:block;margin-top:2px;color:var(--kobalt);overflow-wrap:anywhere;
font:700 50px/.95 Georgia,"Noto Serif","Times New Roman",serif}
.day{text-align:right;font-size:17px;font-weight:700}
.day span{margin-bottom:3px}
.perf{position:relative;margin:14px -20px;border-top:2px dashed var(--chiziq)}
.perf::before,.perf::after{content:"";position:absolute;top:-12px;width:22px;height:22px;
border-radius:50%;background:var(--fon)}
.perf::before{left:-11px}
.perf::after{right:-11px}
.cap{margin:0}
.sum{margin:6px 0 0;white-space:nowrap;font-size:20px;font-weight:700;color:var(--xira)}
.sum b{font-size:46px;line-height:1;font-weight:800;letter-spacing:-.02em;color:var(--siyoh);
font-variant-numeric:tabular-nums}
.hint{margin:8px 0 0;font-size:15px;color:var(--xira)}
.parts{margin:16px 0 0;padding:14px 0 0;border-top:1px solid var(--chiziq);display:grid;gap:8px}
.parts div{display:flex;justify-content:space-between;align-items:baseline;gap:12px}
.parts dt{color:var(--xira)}
.parts dd{margin:0;font-weight:700;white-space:nowrap;font-variant-numeric:tabular-nums}
.choose{margin:22px 4px 10px}
.pay{display:flex;align-items:center;gap:12px;min-height:68px;margin-bottom:12px;
padding:0 14px 0 18px;background:#fff;border:1.5px solid var(--chiziq);border-radius:18px;
color:var(--siyoh);text-decoration:none;font-size:17px;font-weight:700;
box-shadow:0 1px 2px rgba(14,22,48,.06);transition:transform .12s,border-color .12s}
.pay img{display:block;height:30px;width:auto}
.click img{height:34px}
.pay span{flex:1}
.pay i{flex:none;display:grid;place-items:center;width:40px;height:40px;border-radius:50%}
.payme i{background:#dcf5f5;color:#008f93}
.click i{background:#e0f1ff;color:#0a6fd6}
.pay:hover{border-color:#b8c3d6}
.pay:active{transform:scale(.985)}
.pay:focus-visible{outline:3px solid var(--kobalt);outline-offset:3px}
.foot{margin:20px 8px 0;font-size:14px;line-height:1.55;color:var(--xira);text-align:center}
.notice{text-align:center;padding:6px 0 2px}
.ic{display:grid;place-items:center;width:60px;height:60px;margin:0 auto 12px;border-radius:50%}
.notice h1{margin:0;font-size:21px;line-height:1.25}
.notice p{margin:8px 0 0;color:var(--xira)}
.ok .ic{background:#e2f4eb;color:#17794f}
.info .ic{background:#e6ecf8;color:var(--kobalt)}
.warn .ic{background:#fcefd9;color:#a4520b}
@media (max-height:700px){.top{padding-bottom:52px}.logo{width:min(200px,56vw)}
.rasta b{font-size:44px}.sum b{font-size:40px}.choose{margin:16px 4px 8px}
.pay{min-height:62px;margin-bottom:10px}}
@media (prefers-reduced-motion:reduce){.pay{transition:none}}
"""


@cache
def _asset(name: str) -> str | None:
    """`app/assets/pay/<name>` -> data URI (jarayonda bir marta o'qiladi)."""
    path = _ASSETS / name
    if not path.is_file():
        return None
    return "data:image/webp;base64," + base64.b64encode(path.read_bytes()).decode()


def _soum(value: int) -> str:
    return f"{value:,}".replace(",", " ").replace("-", "−")


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


def _header(slug: str | None, market_name: str | None) -> str:
    """Bozor logosi (`<slug>.webp`) yoki — logo yo'q bo'lsa — bozor nomi matn bilan."""
    logo = _asset(f"{slug}.webp") if slug and _SLUG.fullmatch(slug) else None
    if logo is not None:
        alt = html.escape(market_name or "Bozor")
        return (
            f'<header class="top"><img class="logo" src="{logo}" alt="{alt}" '
            'width="240" height="104"></header>'
        )
    name = html.escape(market_name or "Onlayn to'lov")
    return f'<header class="top"><p class="mname">{name}</p></header>'


def _document(*, title: str, header: str, main: str) -> str:
    return (
        '<!doctype html><html lang="uz"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">'
        '<meta name="color-scheme" content="light"><meta name="theme-color" content="#012a84">'
        '<meta name="robots" content="noindex">'
        f"<title>{html.escape(title)}</title><style>{_CSS}</style></head>"
        f'<body>{header}<main class="wrap">{main}</main></body></html>'
    )


def _response(body: str, status_code: int = 200) -> HTMLResponse:
    return HTMLResponse(body, status_code=status_code, headers={"Cache-Control": "no-store"})


def _head(stall_code: str, day: date) -> str:
    """Chipta boshi: rasta raqami (stikerdagi bilan solishtirish uchun) va bugungi sana."""
    return (
        '<div class="head">'
        f'<p class="rasta"><span>Rasta</span><b>{html.escape(stall_code)}</b></p>'
        f'<p class="day"><span>Bugun</span>{day.day}-{_MONTHS[day.month - 1]}</p>'
        '</div><div class="perf" aria-hidden="true"></div>'
    )


def _parts(due: StallDue) -> list[tuple[str, int]]:
    """Izoh qatorlari — yig'indisi jamiga AYNAN teng bo'lsagina, aks holda bo'sh."""
    rows: list[tuple[str, int]] = []
    if due.today_soum:
        label = "Bugungi patta qoldig'i" if due.paid_today_soum > 0 else "Bugungi patta"
        rows.append((label, due.today_soum))
    if due.debt_soum > 0:
        rows.append(("Oldingi kunlardan qarz", due.debt_soum))
    elif due.debt_soum < 0:
        rows.append(("Avans", due.debt_soum))
    if len(rows) < 2 or sum(value for _, value in rows) != due.total_soum:
        return []
    return rows


def _caption(due: StallDue) -> str:
    """Izoh qatorlari bo'lmaganda summa ostidagi bitta jumla."""
    if due.debt_soum == 0 and due.today_soum == due.total_soum:
        return "Bugungi patta qoldig'i" if due.paid_today_soum > 0 else "Bugungi patta"
    if not due.today_soum and due.debt_soum == due.total_soum:
        return "Oldingi kunlardan qarz"
    return "Bugungi patta va qarz bilan"


def _button(kind: Literal["payme", "click"], href: str) -> str:
    name, width, height = ("Payme", 103, 30) if kind == "payme" else ("Click", 82, 34)
    logo = _asset(f"{kind}.webp")
    mark = (
        f'<img src="{logo}" alt="{name}" width="{width}" height="{height}">'
        if logo is not None
        else f"<b>{name}</b>"
    )
    label = html.escape(name + " bilan to'lash")
    return (
        f'<a class="pay {kind}" href="{html.escape(href)}" aria-label="{label}">'
        f"{mark}<span>bilan to'lash</span><i>{_ARROW}</i></a>"
    )


def _due_main(due: StallDue, day: date, buttons: list[str]) -> str:
    rows = _parts(due)
    detail = (
        '<dl class="parts">'
        + "".join(f"<div><dt>{label}</dt><dd>{_soum(v)} so'm</dd></div>" for label, v in rows)
        + "</dl>"
        if rows
        else f'<p class="hint">{_caption(due)}</p>'
    )
    return (
        f'<section class="ticket">{_head(due.stall_code, day)}'
        '<p class="cap">To\'lanadigan summa</p>'
        f'<p class="sum"><b>{_soum(due.total_soum)}</b> so\'m</p>{detail}</section>'
        '<p class="choose">To\'lov usulini tanlang</p>'
        + "".join(buttons)
        + f'<p class="foot">To\'lashdan oldin rasta raqamini tekshiring.<br>{_HELP}</p>'
    )


def _notice(kind: Literal["ok", "info", "warn"], title: str, body: str, head: str = "") -> str:
    return (
        f'<section class="ticket">{head}<div class="notice {kind}">'
        f'<div class="ic">{_ICONS[kind]}</div><h1>{title}</h1><p>{body}</p></div></section>'
        f'<p class="foot">{_HELP}</p>'
    )


def _not_connected(header: str) -> HTMLResponse:
    main = _notice("info", "Onlayn to'lov hozircha ulanmagan", "To'lovni bozor kassiriga qiling.")
    return _response(_document(title="Onlayn to'lov", header=header, main=main), 503)


@router.get("/{stall_code}", include_in_schema=False)
async def pay_page(stall_code: str, request: Request) -> HTMLResponse:
    """Eski QR-kod (Karmana): bozor `PAY_DEFAULT_MARKET` dan."""
    settings: Settings = request.app.state.settings
    return await _render(request, default_market(settings), default_slug(settings), stall_code)


@router.get("/{market}/{stall_code}", include_in_schema=False)
async def pay_page_for_market(market: str, stall_code: str, request: Request) -> HTMLResponse:
    """QR-kod sahifasi: `/pay/{bozor}/{rasta}` — summa + o'sha bozor kassasi tugmalari."""
    settings: Settings = request.app.state.settings
    slug = market.strip().lower()[:32]
    return await _render(request, market_by_slug(settings, slug), slug, stall_code)


async def _render(
    request: Request, market_id: UUID | None, slug: str, stall_code: str
) -> HTMLResponse:
    settings: Settings = request.app.state.settings
    if market_id is None:
        return _not_connected(_header(None, None))

    code = stall_code.strip()[:32]
    sessionmaker: async_sessionmaker[AsyncSession] = request.app.state.sessionmaker
    async with binding_repo.tenant_session(
        sessionmaker, market_id=market_id, request_id="pay:page"
    ) as session:
        market_name = (await session.execute(_MARKET_NAME)).scalar_one_or_none()
        try:
            due: StallDue | DueUnavailable = await stall_due(
                session, market_id=market_id, stall_code=code
            )
        except DueUnavailable as exc:
            due = exc

    header = _header(slug, market_name)
    tail = f" — {market_name}" if market_name else ""
    day = business_today()
    if isinstance(due, DueUnavailable):
        safe = html.escape(code)
        title = _REASONS[due.reason]
        if due.reason == "nothing_due":
            body = "Bugungi patta to'langan yoki oldindan to'lov qilingan."
            main = _notice("ok", title, body, _head(code, day))
        elif due.reason == "stall_not_assigned":
            body = f"{safe}-rasta hozircha hech kimga biriktirilmagan."
            main = _notice("warn", title, body, _head(code, day))
        else:
            body = f"«{safe}» raqamli rasta bu bozorda yo'q — QR kod eskirgan bo'lishi mumkin."
            main = _notice("warn", title, body)
        return _response(_document(title=f"{title}{tail}", header=header, main=main), 404)

    buttons = []
    payme = _payme_url(settings, market_id, due)
    if payme is not None:
        buttons.append(_button("payme", payme))
    click = _click_url(settings, market_id, due)
    if click is not None:
        buttons.append(_button("click", click))
    if not buttons:
        return _not_connected(header)

    title = f"{due.stall_code}-rasta — to'lov{tail}"
    return _response(_document(title=title, header=header, main=_due_main(due, day, buttons)))
