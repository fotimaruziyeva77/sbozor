"""core-api ASGI ilovasi.

`lifespan=` ishlatiladi — `@app.on_event` FastAPI 0.93+ da eskirgan.

Ikkita sog'liq endpointi ajratilgan:
  * `/healthz` — liveness: tashqi bog'liqliklarga TEGMAYDI, har doim 200.
                 Compose healthcheck va orkestrator shundan foydalanadi.
  * `/readyz`  — readiness: DB va Valkey ping; biri yiqilsa 503.

=============================================================================
`app.state` — ILOVA RESURSLARINING YAGONA JOYI:

    settings      `Settings`                     (12-faktor, muhitdan)
    engine        `AsyncEngine`                  (`sbozor_app` roli bilan)
    sessionmaker  `async_sessionmaker`           dependency'lar shundan oladi
    cache         `Redis`                        Valkey klienti

Dependency'lar bu qiymatlarni `request.app.state` dan oladi, modul
darajasidagi globaldan EMAS. Sabab: integratsiya testi aynan shu
ilovaning o'zini ishlatadi va faqat `app.state` ni almashtiradi — ya'ni
test prod kodining nusxasini emas, PROD KODINI ishga tushiradi.
=============================================================================
"""

from __future__ import annotations

import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import sentry_sdk
import structlog
from asgi_correlation_id import CorrelationIdMiddleware
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from sbozor_core.db import make_engine, make_sessionmaker
from sbozor_core.logging import configure_logging
from sentry_sdk.types import Breadcrumb, BreadcrumbHint, Event, Hint
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncEngine

from app.api.internal.live_authz import router as live_authz_router
from app.api.v1.assignments import router as assignments_router
from app.api.v1.assignments import stall_router as stall_assignments_router
from app.api.v1.audit import router as audit_router
from app.api.v1.auth import router as auth_router
from app.api.v1.calendar import router as calendar_router
from app.api.v1.cameras import router as cameras_router
from app.api.v1.categories import router as categories_router
from app.api.v1.imports import router as imports_router
from app.api.v1.markets import router as markets_router
from app.api.v1.me import router as me_router
from app.api.v1.nvr import router as nvr_router
from app.api.v1.schedules import router as schedules_router
from app.api.v1.stalls import router as stalls_router
from app.api.v1.tariffs import router as tariffs_router
from app.api.v1.users import router as users_router
from app.api.v1.vendors import router as vendors_router
from app.api.v1.zones import router as zones_router
from app.settings import Settings, get_settings
from app.worker import broker, enqueue_discovery

log = structlog.get_logger(__name__)

API_V1_PREFIX = "/api/v1"

RLS_VIOLATION_SQLSTATE = "42501"
"""`insufficient_privilege` — RLS `WITH CHECK` buzilishi ham shu kod bilan keladi."""

RLS_VIOLATION_MARKER = "row-level security policy"
"""Postgres xabaridagi belgi: `new row violates row-level security policy for table ...`."""

MASKED = "***"
"""Maskalangan qiymatning YAGONA ko'rinishi — testda ham shu satr izlanadi."""

_PII_KEYS = frozenset(
    {"password", "current_password", "new_password", "phone", "token", "src", "source"}
)
"""Sentry `extra` sida maskalanadigan kalitlar.

⚠ `src`/`source` 03-13 da QO'SHILDI: `PUT /api/streams` ning `src` i endi
  REKVIZITLI RTSP manbai (`live_source.authenticated_rtsp_source` ning
  chiqishi), ya'ni u nomi bo'yicha zararsiz ko'ringan holda parol tashiydi.
"""

_SRC_PARAM = re.compile(r"(?i)(\bsrc=)[^&\s'\"]*")
"""Query satridagi `src=<qiymat>` — QIYMAT butunlay maskalanadi.

⚠ QIYMAT PERCENT-ENCODED HOLDA KELADI. `httpx` chiquvchi so'rovda uni
  `src=rtsp%3A%2F%2Fadmin%3APAROL%40nvr...` ko'rinishiga o'giradi, ya'ni
  `rtsp://` naqshi bilan izlash bu shaklni TOPMASDI (o'lchandi). Shuning
  uchun bu yerda butun qiymat `&` gacha kesiladi — shakl ahamiyatsiz.
"""

_RTSP_USERINFO = re.compile(r"(?i)(rtsp://)[^/@\s'\"]+@")
"""XOM `rtsp://user:pass@host` shakli — ZAXIRA qatlam.

⚠ BU QATLAM STACK FRAME'DAGI LOKAL O'ZGARUVCHILAR UCHUN. Sentry
  `include_local_variables` bilan har freymning lokallarini `repr` qilib
  yuboradi, `go2rtc.py::ensure_stream` da esa ochilgan manba lokal
  o'zgaruvchida yotadi. Query naqshi u yerda ishlamasdi: qiymat `src=`
  siz, yalang'och satr sifatida turadi.
"""


def _mask_secrets(value: str) -> str:
    """Satrdagi RTSP rekvizitini maskalaydi — MATN darajasida.

    ⚠ URL QAYTA QURILMAYDI (parse -> tahrir -> unparse). Maqsad qiymatni
      SAQLAB QOLISH emas, sirni CHIQARMASLIK: qayta qurish har bir
      kutilmagan shaklda (bo'sh port, ikkinchi `@`, buzilgan kodlash)
      istisno berardi va o'sha istisnoning matni yana sirni tashirdi.
    """
    return _RTSP_USERINFO.sub(rf"\g<1>{MASKED}@", _SRC_PARAM.sub(rf"\g<1>{MASKED}", value))


def _mask_deep(node: Any) -> Any:
    """Hodisadagi HAR satr qiymatiga `_mask_secrets()` ni qo'llaydi.

    ⚠ NEGA CHUQUR VA NEGA MAYDON RO'YXATI EMAS: sir Sentry hodisasiga
      KAMIDA UCH xil joydan tushadi — istisno matni (`exception.values[].
      value`), so'rov query satri (`request.query_string`) va stack
      freymlarning lokal o'zgaruvchilari (`stacktrace.frames[].vars`).
      Ro'yxat bilan yurish to'rtinchi joy paydo bo'lganda jimgina
      eskirardi; matn darajasidagi bitta qoida esa hammasini qamraydi.
    """
    if isinstance(node, str):
        return _mask_secrets(node)
    if isinstance(node, dict):
        return {key: _mask_deep(value) for key, value in node.items()}
    if isinstance(node, list):
        return [_mask_deep(item) for item in node]
    return node


def _scrub_event(event: Event, _hint: Hint) -> Event:
    """Sentry `before_send` — shaxsiy ma'lumot va sirlarni olib tashlaydi (ASVS V14).

    Sentry hodisasi ilova chegarasidan CHIQADI (uchinchi tomon xizmati),
    shuning uchun so'rov tanasi va cookie'lar u yerga umuman bormasligi
    kerak. `structlog` tomonida bir xil vazifani `censor_secrets` bajaradi.

    03-13 dan boshlab BU YERDA IKKINCHI VAZIFA HAM BOR: jonli ko'rish yo'li
    go2rtc'ga REKVIZITLI RTSP manbaini yuboradi (`?src=rtsp://admin:PAROL@...`),
    ya'ni sir istisno matniga, so'rov query satriga va freym lokallariga
    tushishi mumkin. `_mask_deep()` uchalasini ham matn darajasida yopadi.
    """
    request = event.get("request")
    if isinstance(request, dict):
        request.pop("data", None)
        request.pop("cookies", None)
        headers = request.get("headers")
        if isinstance(headers, dict):
            for key in list(headers):
                if key.lower() in {"authorization", "cookie"}:
                    headers[key] = MASKED
    extra = event.get("extra")
    if isinstance(extra, dict):
        for key in list(extra):
            if key.lower() in _PII_KEYS:
                extra[key] = MASKED
    masked: Event = _mask_deep(event)
    return masked


def _scrub_breadcrumb(crumb: Breadcrumb, _hint: BreadcrumbHint) -> Breadcrumb | None:
    """Sentry `before_breadcrumb` — CHIQUVCHI so'rov URL'ini maskalaydi (T-03-89).

    =========================================================================
    ⚠⚠ BU ALOHIDA ILMOQ KERAK — `before_send` YETMAYDI.

    `sentry-sdk[fastapi]` ning httpx integratsiyasi har CHIQUVCHI so'rovni
    breadcrumb sifatida yozadi va breadcrumb `data` sida TO'LIQ URL, query
    satri bilan turadi. Bizning `PUT /api/streams?name=...&src=rtsp://admin:PAROL@...`
    aynan shunday so'rov — ya'ni parol hodisa YUZ BERMASDAN OLDIN, oddiy
    muvaffaqiyatli chaqiruvda ham navbatga tushardi va keyingi ISTALGAN
    xato bilan Sentry'ga ketardi.

    `before_send` uni ushlamasdi: breadcrumb'lar hodisaga u yerdan
    KEYIN qo'shiladi.
    =========================================================================

    Faqat `http` turidagi breadcrumb qaraladi: qolganlarida URL yo'q va
    ularni ham qayta ishlash har log satrida ikkita regex yurgizardi.
    """
    if crumb.get("type") != "http" and crumb.get("category") != "httplib":
        return crumb

    data = crumb.get("data")
    if isinstance(data, dict):
        for key, value in list(data.items()):
            if isinstance(value, str):
                data[key] = _mask_secrets(value)

    message = crumb.get("message")
    if isinstance(message, str):
        crumb["message"] = _mask_secrets(message)
    return crumb


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    """Ulanish pullarini ilova hayoti davomida bir marta ochadi va yopadi."""
    settings: Settings = get_settings()
    configure_logging(settings.log_level)

    if settings.sentry_dsn:
        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            before_send=_scrub_event,
            # ⚠ IKKALASI HAM MAJBURIY (T-03-89): `before_send` hodisani,
            #   `before_breadcrumb` esa undan OLDIN yig'ilgan chiquvchi
            #   so'rovlar izini tozalaydi. Bittasini qoldirish ikkinchisini
            #   bir chaqiruvdan narida qoldirardi.
            before_breadcrumb=_scrub_breadcrumb,
            send_default_pii=False,
        )

    engine: AsyncEngine = make_engine(settings.database_url)
    cache: Redis = Redis.from_url(settings.valkey_url)

    # 3-faza: navbatning KLIENT tomoni (`app/worker.py`). API job'ni
    # bajarmaydi — u faqat navbatga qo'yadi, ya'ni bu yerda `startup()`
    # ulanish pulini ochadi va boshqa hech nima qilmaydi.
    #
    # ⚠ EGALIK SHAKLI `engine`/`cache` BILAN AYNAN BIR XIL: bir marta
    #   ochiladi, `finally` da yopiladi. Broker'ni har so'rovda ochish
    #   `LPUSH` ga TCP qo'l siqishini qo'shardi.
    await broker.startup()

    application.state.settings = settings
    application.state.engine = engine
    application.state.sessionmaker = make_sessionmaker(engine)
    application.state.cache = cache
    # Marshrut qatlami navbatga SHU maydon orqali boradi, moduldan
    # to'g'ridan-to'g'ri emas — sabab `api/v1/nvr.py::_enqueue` da
    # (`sessionmaker`/`cache` bilan bir xil almashtirish nuqtasi).
    application.state.enqueue_discovery = enqueue_discovery
    try:
        yield
    finally:
        await broker.shutdown()
        await cache.aclose()
        await engine.dispose()


app = FastAPI(
    title="SBOZOR core-api",
    version="0.1.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# So'rov identifikatori: `X-Request-ID` sarlavhasidan olinadi yoki hosil
# qilinadi, `contextvars` orqali barcha log satrlariga va `audit_log.
# request_id` ustuniga tushadi — nizoni tiklashda uchala servis (core-api,
# cv-service, bot-service) yozuvlarini bitta ipga bog'laydi.
app.add_middleware(CorrelationIdMiddleware)

app.include_router(auth_router, prefix=f"{API_V1_PREFIX}/auth")
app.include_router(users_router, prefix=f"{API_V1_PREFIX}/users")
app.include_router(me_router, prefix=f"{API_V1_PREFIX}/me")
app.include_router(markets_router, prefix=f"{API_V1_PREFIX}/markets")
app.include_router(audit_router, prefix=f"{API_V1_PREFIX}/audit")
# --- 2-faza: bozor domeni reestrlari ---
#
# Yangi marshrutlar `tests/tenancy/test_cross_tenant.py` matritsasiga
# AVTOMATIK tushadi (u ro'yxatni `app.routes` dan oladi), ya'ni bu yerga
# qo'shish o'sha faylda qo'lda ro'yxat yuritishni TALAB QILMAYDI. IKKI
# qo'lda qadam bor: yangi yo'l parametri uchun `PARAM_FILLERS` ga B bozori
# qiymatini, TANA talab qiladigan marshrut uchun esa `BODY_FILLERS` ga
# yaroqli tanani qo'shish. Birinchisi unutilsa `test_no_unclassified_routes`,
# ikkinchisi unutilsa `test_cross_tenant_object_returns_404` qizaradi
# (tanasiz so'rov 422 da to'xtab, 404 da'vosini sinamay qo'yardi).
app.include_router(zones_router, prefix=f"{API_V1_PREFIX}/zones")
app.include_router(categories_router, prefix=f"{API_V1_PREFIX}/categories")
app.include_router(stalls_router, prefix=f"{API_V1_PREFIX}/stalls")
app.include_router(tariffs_router, prefix=f"{API_V1_PREFIX}/tariffs")
app.include_router(calendar_router, prefix=f"{API_V1_PREFIX}/calendar")
app.include_router(vendors_router, prefix=f"{API_V1_PREFIX}/vendors")
app.include_router(assignments_router, prefix=f"{API_V1_PREFIX}/assignments")
# ⚠ IKKINCHI ROUTER, PREFIKSSIZ — `GET /api/v1/stalls/{stall_id}/assignments`.
#
# Marshrut BIRIKTIRISH domeniga tegishli (`AssignmentItem` qaytaradi va
# `assignments.py` dagi xato semantikasini baham ko'radi), lekin yo'li
# rasta ostida yashaydi. `assignments_router` ichida qoldirilsa yo'l
# `/api/v1/assignments/stalls/...` bo'lib ketardi, `stalls_router` ga
# ko'chirilsa esa rasta reestri biriktirish repozitoriysiga bog'lanib
# qolardi. Shuning uchun u alohida router va u `{API_V1_PREFIX}` ga
# ulanadi. `stalls_router` bilan to'qnashuv YO'Q — yo'llarning segment
# soni har xil (sabab `api/v1/assignments.py` modul docstringida).
app.include_router(stall_assignments_router, prefix=API_V1_PREFIX)
# --- 02-12: Excel import (D-13/D-14/D-15) ---
#
# Marshrutlarning UCHTASI tana talab qiladi, LEKIN ikkitasi `multipart/
# form-data` (fayl) va faqat bittasi JSON. Cross-tenant matritsasi
# `BODY_FILLERS` orqali FAQAT JSON yubora oladi, shuning uchun fayl
# marshrutlari uchun `FILE_FILLERS` qo'shildi — usiz ular 422 da
# to'xtab, "javobda B bozorining izi yo'q" da'vosini SINAMASDAN
# o'tkazib yuborardi (02-08 dagi `BODY_FILLERS` bilan aynan bir xil
# sinf xato).
app.include_router(imports_router, prefix=f"{API_V1_PREFIX}/imports")
# --- 3-faza: NVR qurilmalari va kashfiyot (CAM-01/CAM-08) ---
#
# Yettita marshrut ham yuqoridagi 2-faza izohidagi IKKI QO'LDA QADAMga
# tushadi: `PARAM_FILLERS` ga `nvr_id` va `run_id`, `BODY_FILLERS` ga esa
# `POST ""`, `PATCH /{nvr_id}`, `POST /{nvr_id}/password` va
# `POST /test-connection` uchun namuna tana. Ikkalasini ham 03-06
# qo'shdi; unutilganda `test_no_unclassified_routes` va
# `test_cross_tenant_object_returns_404` qizaradi.
app.include_router(nvr_router, prefix=f"{API_V1_PREFIX}/nvr-devices")
# --- 03-07: kameralar reestri va jonli ko'rish (CAM-02/CAM-03) ---
#
# ⚠ ALOHIDA PREFIKS, `nvr-devices` OSTIDA EMAS. Kamera NVR ning bolasi
# bo'lsa ham, u MUSTAQIL resurs: 4-fazadagi snapshotlar va 5-fazadagi
# zonalar aynan `cameras.id` ga bog'lanadi va ular NVR ni umuman
# bilmaydi. Yo'lni `/nvr-devices/{nvr_id}/cameras/...` qilish har bir
# kamera amalini NVR identifikatorini bilishga majburlardi — UI esa
# ro'yxatdan to'g'ridan-to'g'ri kamera ustida ishlaydi (UI-SPEC §6.1).
#
# Yangi yo'l parametri (`camera_id`) cross-tenant matritsasining
# `PARAM_FILLERS` iga, `PATCH` esa `BODY_FILLERS` ga qo'shildi — usiz
# `test_no_unclassified_routes` va `test_cross_tenant_object_returns_404`
# qizaradi (yuqoridagi 2-faza izohidagi IKKI QO'LDA QADAM).
app.include_router(cameras_router, prefix=f"{API_V1_PREFIX}/cameras")
# --- 04-09: snapshot jadvali (CAM-04, D-05) ---
#
# ⚠ ALOHIDA PREFIKS, `cameras` OSTIDA EMAS — `cameras` ning `nvr-devices`
# ostida turmasligi bilan AYNAN bir xil mulohaza. Jadval BOZORGA
# tegishli (bitta profil butun bozorning barcha kameralariga amal
# qiladi), ya'ni uni `/cameras/{camera_id}/schedule` ostiga qo'yish
# resursni noto'g'ri joyga bog'lardi va «qaysi kameraning jadvali?»
# degan ma'nosiz savolni tug'dirardi.
#
# Yangi yo'l parametri (`schedule_id`) cross-tenant matritsasining
# `PARAM_FILLERS` iga, `POST`/`PATCH` esa `BODY_FILLERS` ga qo'shildi.
app.include_router(schedules_router, prefix=f"{API_V1_PREFIX}/snapshot-schedules")
# --- 03-07: nginx `auth_request` nishoni (SC#6, D-11) ---
#
# ⚠ PREFIKSSIZ VA `API_V1_PREFIX` DAN TASHQARIDA — `/healthz` bilan bir
# xil naqsh va bir xil sabab: bu marshrut MAHSULOT kontrakti emas, u
# INFRASTRUKTURA (nginx) chaqiradigan ichki yuza. `/api/v1` ostiga
# qo'yilsa u avtomatik ravishda cross-tenant matritsasidan 401/404
# xulqini talab qilib qolardi, uning kontrakti esa 204/403.
#
# `include_in_schema=False` (router darajasida): OpenAPI mijozlar uchun
# yoziladi va bu yerda mijoz YO'Q. `test_route_walker_matches_openapi`
# faqat `documented <= walked` ni talab qiladi, ya'ni sxemadan
# chiqarish darvozani buzmaydi.
#
# Matritsadan chiqarilishi `tests/tenancy/test_cross_tenant.py::
# EXEMPT_ROUTES` da SABAB bilan yozilgan va qamrovi
# `tests/integration/test_live_view.py` da TO'LIQ qayta tiklangan.
app.include_router(live_authz_router)


@app.exception_handler(DBAPIError)
async def rls_violation_handler(request: Request, exc: DBAPIError) -> JSONResponse:
    """RLS buzilishini **404** ga tarjima qiladi (T-01-47).

    NEGA 403 EMAS: cross-tenant so'rovda 403 javobning O'ZI "bunday obyekt
    bor, lekin sizniki emas" degan ma'lumotni oshkor qiladi. 404 esa
    "bunday obyekt yo'q" deydi va bu boshqa bozor uchun AYNI HAQIQAT —
    RLS ostida o'sha qator uning uchun mavjud emas.

    Ichki tafsilot (jadval nomi, policy nomi) javobga CHIQMAYDI; u
    to'liqligicha log'ga yoziladi.
    """
    sqlstate = getattr(exc.orig, "sqlstate", None)
    message = str(exc.orig)
    if sqlstate == RLS_VIOLATION_SQLSTATE and RLS_VIOLATION_MARKER in message:
        log.warning("rls_violation", path=request.url.path, error=message)
        return JSONResponse(status_code=404, content={"detail": "not_found"})

    log.error("database_error", path=request.url.path, error=message)
    return JSONResponse(status_code=500, content={"detail": "internal_error"})


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    """Liveness — jarayon javob berayotganini bildiradi, boshqa hech narsani emas."""
    return {"status": "ok"}


@app.get("/readyz")
async def readyz(request: Request) -> JSONResponse:
    """Readiness — DB va Valkey haqiqatan javob berayotganini tekshiradi."""
    checks: dict[str, str] = {}
    ready = True

    engine: AsyncEngine = request.app.state.engine
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001 - har qanday nosozlik = tayyor emas
        ready = False
        checks["database"] = f"error: {type(exc).__name__}"
    else:
        checks["database"] = "ok"

    cache: Redis = request.app.state.cache
    try:
        await cache.ping()
    except Exception as exc:  # noqa: BLE001 - har qanday nosozlik = tayyor emas
        ready = False
        checks["cache"] = f"error: {type(exc).__name__}"
    else:
        checks["cache"] = "ok"

    return JSONResponse(
        status_code=200 if ready else 503,
        content={"status": "ok" if ready else "degraded", "checks": checks},
    )
