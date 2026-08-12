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

import structlog
from asgi_correlation_id import CorrelationIdMiddleware
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from sbozor_core.db import make_engine, make_sessionmaker
from sbozor_core.logging import configure_logging
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncEngine

from app.api.internal.bot import router as bot_internal_router
from app.api.internal.live_authz import router as live_authz_router
from app.api.internal.self_check import router as self_check_router
from app.api.v1.assignments import router as assignments_router
from app.api.v1.assignments import stall_router as stall_assignments_router
from app.api.v1.audit import router as audit_router
from app.api.v1.auth import router as auth_router
from app.api.v1.billing import router as billing_router
from app.api.v1.calendar import router as calendar_router
from app.api.v1.camera_zones import router as camera_zones_router
from app.api.v1.cameras import router as cameras_router
from app.api.v1.categories import router as categories_router
from app.api.v1.imports import router as imports_router
from app.api.v1.markets import router as markets_router
from app.api.v1.me import router as me_router
from app.api.v1.nvr import router as nvr_router
from app.api.v1.occupancy import router as occupancy_router
from app.api.v1.payments import router as payments_router
from app.api.v1.reviews import router as reviews_router
from app.api.v1.schedules import router as schedules_router
from app.api.v1.shifts import router as shifts_router
from app.api.v1.snapshots import alerts_router, capture_runs_router
from app.api.v1.snapshots import router as snapshots_router
from app.api.v1.stalls import router as stalls_router
from app.api.v1.tariffs import router as tariffs_router
from app.api.v1.users import router as users_router
from app.api.v1.vendors import router as vendors_router
from app.api.v1.zones import router as zones_router
from app.observability import init_sentry
from app.settings import Settings, get_settings
from app.worker import broker, enqueue_discovery

log = structlog.get_logger(__name__)

API_V1_PREFIX = "/api/v1"

RLS_VIOLATION_SQLSTATE = "42501"
"""`insufficient_privilege` — RLS `WITH CHECK` buzilishi ham shu kod bilan keladi."""

RLS_VIOLATION_MARKER = "row-level security policy"
"""Postgres xabaridagi belgi: `new row violates row-level security policy for table ...`."""


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    """Ulanish pullarini ilova hayoti davomida bir marta ochadi va yopadi."""
    settings: Settings = get_settings()
    configure_logging(settings.log_level)

    # ⚠ ILMOQLAR VA O'RNATISH `app/observability.py` DA (04-12). Ular shu
    #   faylda yashaganda `worker` jarayoni ularga UMUMAN yeta olmasdi
    #   (`app.main` ni import qilish butun ilovani worker'ga tortib
    #   kelardi), ya'ni kadr olish, saqlash siyosati va alert supurgisining
    #   istisnolari Sentry'ga hech qachon bormasdi — modul docstringiga
    #   qarang.
    log.info("sentry", enabled=init_sentry(settings.sentry_dsn))

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
# --- 05-06: kamera zonalari (AI-01, D-07/D-22) ---
#
# ⚠ ALOHIDA PREFIKS, `cameras/{camera_id}/zones` OSTIDA EMAS — VA SABAB
# `cameras` ning `nvr-devices` ostida turmasligidan FARQ QILADI.
#
# Zona kameraning bolasi, lekin `GET /camera-zones/coverage` BOZORGA
# tegishli: u butun bozorning qamrovini sanaydi va hech qaysi kameraga
# oid emas. `cameras/{camera_id}/zones` ostida u uy topa olmasdi —
# `cameras/coverage` esa `{camera_id}` shabloniga tushib, 422 berardi
# (`stalls.py:3-11` dagi tartib tuzog'ining aynan o'zi).
#
# ⚠ `camera_id` YO'L PARAMETRI EMAS, QUERY parametri — ya'ni u
# cross-tenant matritsasining `PARAM_FILLERS` iga TUSHMAYDI. Uning
# tenant chegarasi shu sababdan `tests/integration/test_camera_zones_
# api.py::test_cross_tenant_camera_returns_404` da ALOHIDA o'lchanadi;
# matritsa esa `camera_zone_id` ni (yo'l parametri) qamraydi va u uchun
# `PARAM_FILLERS` ga B bozorining HAQIQIY zonasi qo'shildi.
app.include_router(camera_zones_router, prefix=f"{API_V1_PREFIX}/camera-zones")
# --- 05-10: nazoratchi navbati (AI-03, D-13/D-18) ---
#
# ⛔ ALOHIDA PREFIKS VA BITTA ROUTER — IKKALA NAVBAT UCHUN.
#
# `/review/uncertain/next` va (05-11 da) `/review/blind/next` BIR router
# ostida yashaydi, chunki ular BITTA mahsulot yuzasining ikki rejimi:
# nazoratchining uyi (`/review`) ikkala kartani ham ko'rsatadi va
# `GET /review/budget` ikkalasining hisoblagichini BIR so'rovda beradi.
#
# ⚠ `POST /review/{review_assignment_id}/answer` — yo'l parametri
# ATAYIN `assignment_id` DEB NOMLANMAGAN: o'sha nom `PATCH /assignments/
# {assignment_id}` (rasta-sotuvchi biriktirishi) bilan to'qnashardi va
# cross-tenant matritsasining `PARAM_FILLERS` i bu marshrutga BEGONA
# obyekt turini berardi — 404 chiqardi-yu, sababi tenant chegarasi
# emas, «bunday topshiriq umuman yo'q» bo'lardi.
#
# ⚠ OMMAVIY (massiv qabul qiladigan) MARSHRUT BU ROUTERDA YO'Q va uning
# yo'qligi `tests/integration/test_uncertain_queue.py::
# test_no_bulk_approve_endpoint` da OpenAPI sxemasidan skanerlanadi
# (D-18 — API qoidasi, UI qoidasi EMAS).
app.include_router(reviews_router, prefix=f"{API_V1_PREFIX}/review")
# --- 05-12: bandlik va aniqlik hisoboti (AI-04/AI-05/AI-06, D-19/D-22) ---
#
# ⛔ ALOHIDA PREFIKS VA `REPORT_VIEW` OSTIDA — `/review` NING QO'SHNISI
#    EMAS, ZIDDI.
#
# `/review` — NAZORATCHINING uyi (`OCCUPANCY_REVIEW`), `/occupancy` esa
# DIREKTORNIKI (`REPORT_VIEW`). Ularni bitta router ostiga qo'yish
# huquqni marshrut darajasida ajratishni talab qilardi va `INSPECTOR_
# ROUTES` matritsasi ikkala yuzani ham bitta sessiya bilan chaqirardi.
#
# ⛔ NAZORATCHIDA `REPORT_VIEW` YO'Q va bu ATAYIN (T-05-58): u o'z
# aniqligini ko'rsa raqamni yaxshilashga urinardi — «tez qaror» sanog'i
# esa aynan shu urinishning izi bo'lib qolardi.
#
# ⛔ «NAMUNANI QAYTA TORTISH» MARSHRUTI YOZILMAGAN (D-17.1) va uning
# yo'qligi 05-11 ning OpenAPI skani bilan o'lchanadi.
app.include_router(occupancy_router, prefix=f"{API_V1_PREFIX}/occupancy")
# --- 06-08: kutilayotgan patta va yozilgan hisob (BILL-02…BILL-05) ---
#
# ⛔ ALOHIDA PREFIKS — `/occupancy` GA QO'SHILMAYDI, VA SABAB
#    STRUKTURAVIY (UI-SPEC §4.3 ning to'rt sababi, qisqacha):
#
#   1. `/occupancy` ning copy'si 05-UI-SPEC §16.1 da OCHIQ VA'DA beradi:
#      «Patta hisobi alohida qoidaga ko'ra yuritiladi»
#      (`occupancy.notBillingYet`). Patta ustunini o'sha yuzaga qo'shish
#      o'sha jumlani YOLG'ONGA aylantirardi;
#   2. BANDLIK ≠ HISOB: `no_coverage` bandlikda KO'RINADI, hisobda YO'Q
#      (D-04/D-05). Bitta jadvalda ikki semantika — «bo'sh katak»
#      sinfidagi jim xato;
#   3. KUN SEMANTIKASI BOSHQA: `/occupancy` `stall_slot_occupancy.
#      business_date` bo'yicha, `/billing` esa `daily_charges.
#      service_date` bo'yicha (C-2). Bir `?day=` ni bo'lishish Pitfall 1
#      ni UI qatlamiga ko'chirardi;
#   4. ALOHIDA KATALOG — DARVOZANING SHARTI: `components/billing/**`
#      ajratilgani uchun G-22 `components/collect/**` da hisob
#      identifikatori YO'QLIGINI skanerlab bera oladi.
#
# ⛔ IKKI HUQUQ, BITTA ROUTER: `/pending` — `BILLING_COLLECT_VIEW`
# (kassir + direktor + bozor admini), qolgan uchtasi — `REPORT_VIEW`
# (kassirda u YO'Q). Ular bitta faylda yashaydi, chunki bitta domen va
# bitta ekranning (`/billing`) ikki bloki; huquq esa IMZO ALIASI bilan
# marshrut darajasida ajratilgan.
#
# ⛔ `require_any_permission()` BU ROUTERDA ISHLATILMAYDI (C-9):
# `test_personal_data_coverage.py:691-706` o'sha darvozaning to'plamini
# AYNAN BITTA marshrutga qulflagan va bu faza unga TEGMAYDI.
#
# Yangi yo'l parametri (`charge_id`) cross-tenant matritsasining
# `PARAM_FILLERS` iga B bozorining HAQIQIY hisobi bilan qo'shildi.
app.include_router(billing_router, prefix=f"{API_V1_PREFIX}/billing")
# --- 06-09: KASSIRNING YOZUV YUZASI (CASH-01…CASH-03) ---
#
# ⛔ ALOHIDA PREFIKS, `/billing` OSTIDA EMAS — VA BU MAHSULOT QARORI,
# fayl uzunligi masalasi emas. `/billing/*` — DIREKTORNING o'qish yuzasi
# (`report_view`), `/payments/*` esa KASSIRNING yozuv yuzasi
# (`payment_create`, u D-07 matritsasida YOLG'IZ kassirda). Ularni bitta
# prefiksga yig'ish ikki ROLNI bitta resurs daraxtiga bog'lardi va
# `/billing` ni «hamma narsa shu yerda» degan chalkash yuzaga aylantirardi.
#
# ⛔ RESURS NOMI KO'PLIKDA VA U KLIENT KONTRAKTIDAN:
# `frontend/src/lib/payment-queries.ts::PAYMENTS_PATH = "/payments"`
# (06-03, allaqachon merge qilingan). Boshqa nom 06-11 ning kassir
# panelini birinchi bosishdayoq 404 ga tushirardi.
#
# ⛔ `PATCH`/`PUT`/`DELETE` BU PREFIKSDA UMUMAN YO'Q (D-23) — `payments`
# append-only va tuzatish FAQAT storno (`POST /{id}/reverse`). OpenAPI
# to'plam tengligi buni `test_payments_api.py` da qulflaydi.
#
# Yangi yo'l parametri (`payment_id`) cross-tenant matritsasining
# `PARAM_FILLERS` iga, ikkala `POST` esa `BODY_FILLERS` VA
# `CASHIER_ROUTES` ga qo'shildi (OP-8/OP-9).
app.include_router(payments_router, prefix=f"{API_V1_PREFIX}/payments")
# --- 06-10: SMENA VA KO'R NAQD DEKLARATSIYASI (CASH-04, D-25, D-26) ---
#
# ⛔ MUSTAQIL PREFIKS, `/collect` OSTIDA EMAS — VA BU IKKI QATLAMNI
# AJRATADIGAN QARORDIR. `/collect/shift` — FRONTEND ning URL ierarxiyasi
# (UI-SPEC §4.2: kassir ekranining bolasi), backend prefiksi esa DOMEN
# bo'yicha quriladi. Ularni tenglashtirish serverni ekran daraxtiga
# bog'lardi: sahifa ko'chirilgan kuni (masalan `/cashier/shift`) API ham
# ko'chishi kerak bo'lardi yoki nom ekrandan JIMGINA ajralib ketardi.
#
# ⛔ RESURS NOMI KO'PLIKDA VA U KLIENT KONTRAKTIDAN:
# `frontend/src/lib/shift-queries.ts::SHIFTS_PATH = "/shifts"` (06-03,
# allaqachon merge qilingan). Boshqa nom 06-12 ning smena ekranini
# birinchi bosishdayoq 404 ga tushirardi.
#
# ⛔ BITTA ROUTER, IKKI HUQUQ: `POST /shifts`, `GET /shifts/open` va
# `POST /shifts/{id}/close` — `SHIFT_MANAGE` (kassir + bozor admini);
# `GET /shifts?day=` — `REPORT_VIEW` (kassirda YO'Q). Variance FAQAT
# oxirgisida qaytariladi (UI-SPEC §10.4) va o'sha ajratma D-25 ning
# ⛔ HUQUQ darajasidagi yarmi.
#
# ⛔ `/billing` GA QO'SHILMADI: `/billing/*` — HISOB va anomaliya yuzasi
# (`service_date` kesimida, C-2), `/shifts` esa KASSA yuzasi
# (`business_date` kesimida). Bir `?day=` ni bo'lishish ikki xil kun
# semantikasini bitta parametrga siqardi.
#
# Yangi yo'l parametri (`shift_id`) cross-tenant matritsasining
# `PARAM_FILLERS` iga B bozorining HAQIQIY smenasi bilan, ikkala `POST`
# esa `BODY_FILLERS` ga qo'shildi. ⛔ `CASHIER_ROUTES` GA TUSHMAYDI —
# `shift_manage` bozor adminida HAM bor (`shifts.py::ShiftManagerDep`).
app.include_router(shifts_router, prefix=f"{API_V1_PREFIX}/shifts")
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
# --- 04-09: kun jurnali, kadr detali, RASM PROXYSI va ogohlantirishlar ---
#
# ⚠ UCHTA ROUTER, UCHTA PREFIKS — VA U ATAYIN. Ular bitta faylda yashaydi
# (`snapshots.py`: bitta mahsulot ekranining uch zonasi), lekin UCH XIL
# resurs. Umumiy prefiks (`/snapshots/capture-runs`) kun jurnalini
# kadrning BOLASI qilib ko'rsatardi — holbuki jurnalning yarmida kadr
# umuman yo'q (`missed`, `failed`, `pending`).
#
# ⛔ `GET /snapshots/{id}/image` — OMBOR YUZASINING YAGONA chiqish nuqtasi.
# Presigned URL BERILMAYDI va uning to'rt sababi `snapshots.py` modul
# docstringida (audit, RLS, manzil oshkorligi, data-rezidentlik).
app.include_router(capture_runs_router, prefix=f"{API_V1_PREFIX}/capture-runs")
app.include_router(snapshots_router, prefix=f"{API_V1_PREFIX}/snapshots")
app.include_router(alerts_router, prefix=f"{API_V1_PREFIX}/alerts")
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
# --- 04-09: o'z-o'zini kuzatish (FOUND-06, D-20) ---
#
# ⚠ `live-authz` BILAN BIR XIL SABABDAN `API_V1_PREFIX` DAN TASHQARIDA:
# uni FOYDALANUVCHI emas, TASHQI KUZATUVCHI chaqiradi va unda
# `Authorization` sarlavhasi umuman bo'lmaydi. Kontrakti ham boshqa —
# 200 yoki 503, hech qachon 401/404 emas.
#
# ⛔ BU MARSHRUT `compose.yaml` DAGI KONTEYNER `healthcheck` IGA
#    ULANMAYDI (Pitfall 14): worker'ning yurak urishi eskirgani uchun
#    SOG'LOM API ni qayta ishga tushirish hech nimani tuzatmasdi.
#    Sabab to'liq `self_check.py` modul docstringida.
app.include_router(self_check_router)
# --- 07-08: `bot-service` -> `core-api` ichki yuzasi (BOT-01/BOT-02, D-10) ---
#
# ⛔ `API_V1_PREFIX` SIZ — `live-authz` / `self-check` bilan bir xil toifa
#    va bir xil sabab: chaqiruvchi FOYDALANUVCHI emas, SERVIS. Uni
#    `/api/v1` ostiga qo'yish uni ommaviy mijoz kontraktining qismiga
#    aylantirardi va cross-tenant matritsasi undan `Authorization: Bearer
#    <access token>` xulqini talab qilardi — bu yerdagi token esa STATIK
#    servis sirri va u bozor tushunchasini umuman ko'tarmaydi.
#
# ⛔ nginx BU PREFIKSNI TASHQARIGA PROXY QILMAYDI (`ops/nginx/nginx.conf`
#    faqat `/api/` va `/`) va core-api porti xostga publish qilinmaydi,
#    ya'ni yuza compose tarmog'idan tashqarida MAVJUD EMAS.
#
# Matritsadan chiqarilishi `tests/tenancy/test_cross_tenant.py::
# EXEMPT_ROUTES` da SABAB bilan yozilgan va qamrovi
# `tests/integration/test_bot_internal_api.py` da TO'LIQ qayta tiklangan
# (tokensiz -> 401; noto'g'ri token -> 401; sozlanmagan token -> 503).
app.include_router(bot_internal_router)


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
