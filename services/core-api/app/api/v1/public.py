"""Anonim demo so'rovi — landing formasining backend yarmi (LAND-03).

=============================================================================
UCH QOIDA — LITERAL, chunki bu marshrut butun kodbazaning istisnosi:

1. BU KODBAZADAGI YAGONA ANONIM YOZUV MARSHRUTI. Boshqa 26 modulning
   birortasi ham autentifikatsiyasiz so'rov qabul qilmaydi; bu yerda esa
   token ham, sessiya ham, cookie ham YO'Q — landing sahifasidagi
   tashrifchi to'g'ridan-to'g'ri yuboradi.

2. U `market_id` SO'RAMAYDI VA RLS KONTEKSTIGA KIRMAYDI — 1-fazadagi
   ko'p-ijarali qoidaning ONGLI istisnosi. So'rovda bozor tushunchasining
   o'zi yo'q (bozor hali MIJOZ EMAS, u demo so'rayapti), ya'ni tenant
   konteksti PRINSIPIAL ravishda mavjud emas. Shu sababdan javobga ham
   bozor identifikatori/nomi/topologiyasi tushmaydi (T-10-02).

3. SO'ROV MA'LUMOTI DB'GA YOZILMAYDI. Ism va telefon Telegram xabari
   sifatida adminga yetadi va tizimda SAQLANMAYDI (T-10-06) — maxfiylik
   sahifasi (10-04) aynan shu faktni e'lon qiladi. DB yozuvi paydo
   bo'lishi `tests/integration/test_demo_request.py` dagi hosila qator
   sanog'i bilan bloklangan.
=============================================================================

XATO SHARTNOMASI — `DEMO_ERROR_CODES` (schemas.py) bilan bitta-satr:
429 `rate_limited` · 422 `invalid_phone` · 502 `delivery_failed`.
Pydantic chegaralari esa FastAPI'ning standart 422 shakli bilan keladi va
frontend uni `validation_error` ga xaritalaydi.

⛔ QADAMLAR TARTIBI MUHIM: honeypot tekshiruvi telefon
   normalizatsiyasidan OLDIN — bot yuborgan buzuq telefon 422 olsa,
   honeypot mavjudligi javob kodidan o'qilardi (T-10-01).

⛔ ISTISNO MATNI JAVOBGA HAM, JURNALGA HAM INTERPOLYATSIYA QILINMAYDI
   (T-10-05): bot tokeni Telegram URL'ining qismi va `AlertSender.
   _failure()` allaqachon sirsiz uchlikni (amal/xato-turi/status) beradi.
"""

from __future__ import annotations

import html

import structlog
from fastapi import APIRouter, HTTPException, Request, status
from sbozor_core.phone import InvalidPhoneError, normalize_phone

from app.api.v1.auth import _client_ip
from app.deps import CacheDep, SenderDep, SettingsDep
from app.schemas import DemoRequestPayload, DemoRequestResponse
from app.security.ratelimit import TooManyAttempts, check_demo_request_rate

log = structlog.get_logger(__name__)

router = APIRouter(tags=["public"])


@router.post("/demo-requests", response_model=DemoRequestResponse)
async def create_demo_request(
    payload: DemoRequestPayload,
    request: Request,
    settings: SettingsDep,
    cache: CacheDep,
    sender: SenderDep,
) -> DemoRequestResponse:
    """Demo so'rovini admin Telegram chatiga SINXRON yetkazadi (SC#3).

    Sinxron + `200` — RESEARCH B-5 qarori: `202 Accepted` paytida
    `delivered` NOMA'LUM bo'lardi va SPEC §12.5 ning «yubordik deb yolg'on
    aytilmaydi» sharti bajarilmasdi. Narxi — so'rov Telegram javobini
    kutadi (`AlertSender` da timeout 5s + tarmoq sinfiga retry bor) va bu
    qabul qilinadi: forma yuborish foydalanuvchi KUTAYOTGAN amal.
    """
    # 1. IP — `auth._client_ip` QAYTA YOZILMAYDI (RESEARCH Don't
    #    Hand-Roll): `X-Forwarded-For` ishonchi DEPLOY qatlamida (uvicorn
    #    `--proxy-headers` + nginx `$remote_addr`), kodda emas.
    ip = _client_ip(request)

    # 2. IP chegarasi — `ip` yo'q bo'lsa qadam o'tkaziladi (login yo'li
    #    bilan bir xil qaror: `inet` ga tushmagan manba sanalmaydi).
    if ip is not None:
        try:
            await check_demo_request_rate(cache, ip=ip)
        except TooManyAttempts as exc:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="rate_limited",
            ) from exc

    # 3. ⛔ HONEYPOT — NORMALIZATSIYADAN OLDIN. Ko'rinmas maydon
    #    to'ldirilgan bo'lsa bu bot: JIMGINA «muvaffaqiyat» qaytariladi va
    #    Telegram'ga BIRORTA chaqiruv ketmaydi. Tartib muhim: bot yuborgan
    #    buzuq telefon 422 bersa, honeypot mavjudligi javob kodidan
    #    o'qilardi.
    if payload.website.strip():
        log.info("demo_request_honeypot")
        return DemoRequestResponse(delivered=True)

    # 4. Telefon — YAGONA haqiqat manbai serverda (T-10-11): klient qattiq
    #    regeks yozmaydi, `phonenumbers` esa CLDR qoidalari bilan o'qiydi.
    try:
        phone = normalize_phone(payload.phone)
    except InvalidPhoneError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="invalid_phone",
        ) from exc

    # 5. ⛔⛔ T-10-04: `AlertSender` `parse_mode: "HTML"` bilan yuboradi
    #    (`services/alerts.py`), ya'ni anonim foydalanuvchi boshqaradigan
    #    `name` va `market_name` — HTML IN'YEKSIYA YUZASI. Har foydalanuvchi
    #    maydoni `html.escape(..., quote=False)` dan o'tadi va FAQAT shundan
    #    keyin matnga qo'shiladi. `phone` normalizatsiyadan o'tgan E.164
    #    (faqat `+` va raqamlar), `stall_count` — `int`, `locale` —
    #    `Literal`; ular kirisha olmaydi. ⛔ Rasm/fayl/havola qo'shilmaydi
    #    (`alerts.py` 1-taqig'i) — faqat MATN.
    lines = [
        "Yangi demo so'rovi — SBOZOR landing",
        f"Ism: {html.escape(payload.name, quote=False)}",
        f"Telefon: {phone}",
        f"Bozor: {html.escape(payload.market_name, quote=False)}",
    ]
    if payload.stall_count is not None:
        lines.append(f"Rastalar soni: {payload.stall_count}")
    lines.append(f"Til: {payload.locale}")
    text = "\n".join(lines)

    # 6. SINXRON yuborish. `demo_request_chat_id` bo'sh bo'lsa `None`
    #    beriladi va `AlertSender` konstruktordagi STANDART manzilga
    #    (`telegram_chat_id`, ops kanali) tushadi — kanal ajratish
    #    KONFIGURATSIYA qarori (RESEARCH A7).
    delivered = await sender.send_message(text, chat_id=settings.demo_request_chat_id or None)
    if not delivered:
        # 7. ⛔ «Yubordik» deb yolg'on aytilmaydi (SPEC §12.5). Istisno
        #    tafsiloti bu yerga YETMAYDI ham — `send_message` `bool`
        #    qaytaradi va sirsiz diagnostikani `AlertSender` o'zi yozadi.
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="delivery_failed",
        )

    return DemoRequestResponse(delivered=True)
