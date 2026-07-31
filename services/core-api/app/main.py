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

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import sentry_sdk
import structlog
from asgi_correlation_id import CorrelationIdMiddleware
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from sbozor_core.db import make_engine, make_sessionmaker
from sbozor_core.logging import configure_logging
from sentry_sdk.types import Event, Hint
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncEngine

from app.api.v1.assignments import router as assignments_router
from app.api.v1.assignments import stall_router as stall_assignments_router
from app.api.v1.audit import router as audit_router
from app.api.v1.auth import router as auth_router
from app.api.v1.calendar import router as calendar_router
from app.api.v1.categories import router as categories_router
from app.api.v1.imports import router as imports_router
from app.api.v1.markets import router as markets_router
from app.api.v1.me import router as me_router
from app.api.v1.stalls import router as stalls_router
from app.api.v1.tariffs import router as tariffs_router
from app.api.v1.users import router as users_router
from app.api.v1.vendors import router as vendors_router
from app.api.v1.zones import router as zones_router
from app.settings import Settings, get_settings

log = structlog.get_logger(__name__)

API_V1_PREFIX = "/api/v1"

RLS_VIOLATION_SQLSTATE = "42501"
"""`insufficient_privilege` — RLS `WITH CHECK` buzilishi ham shu kod bilan keladi."""

RLS_VIOLATION_MARKER = "row-level security policy"
"""Postgres xabaridagi belgi: `new row violates row-level security policy for table ...`."""

_PII_KEYS = frozenset({"password", "current_password", "new_password", "phone", "token"})


def _scrub_event(event: Event, _hint: Hint) -> Event:
    """Sentry `before_send` — shaxsiy ma'lumot va sirlarni olib tashlaydi (ASVS V14).

    Sentry hodisasi ilova chegarasidan CHIQADI (uchinchi tomon xizmati),
    shuning uchun so'rov tanasi va cookie'lar u yerga umuman bormasligi
    kerak. `structlog` tomonida bir xil vazifani `censor_secrets` bajaradi.
    """
    request = event.get("request")
    if isinstance(request, dict):
        request.pop("data", None)
        request.pop("cookies", None)
        headers = request.get("headers")
        if isinstance(headers, dict):
            for key in list(headers):
                if key.lower() in {"authorization", "cookie"}:
                    headers[key] = "***"
    extra = event.get("extra")
    if isinstance(extra, dict):
        for key in list(extra):
            if key.lower() in _PII_KEYS:
                extra[key] = "***"
    return event


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    """Ulanish pullarini ilova hayoti davomida bir marta ochadi va yopadi."""
    settings: Settings = get_settings()
    configure_logging(settings.log_level)

    if settings.sentry_dsn:
        sentry_sdk.init(dsn=settings.sentry_dsn, before_send=_scrub_event, send_default_pii=False)

    engine: AsyncEngine = make_engine(settings.database_url)
    cache: Redis = Redis.from_url(settings.valkey_url)

    application.state.settings = settings
    application.state.engine = engine
    application.state.sessionmaker = make_sessionmaker(engine)
    application.state.cache = cache
    try:
        yield
    finally:
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
