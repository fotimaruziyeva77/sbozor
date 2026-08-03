"""`nvr-sim` ASGI ilovasi — simulyatsiya qilingan Hikvision NVR.

=============================================================================
IKKI QATLAM VA ULARNING TARTIBI:

  1. `Date` sarlavhasi middleware'i (ENG TASHQI) — **har** javobga RFC 7231
     formatida `Date` qo'yadi va `state.drift_seconds` ga siljitadi.
     ⚠ U `401` javoblariga ham qo'llanadi, chunki A.3 dagi soat-farqi
     aniqlash aynan **birinchi, autentifikatsiyasiz** javobdan o'qiydi —
     ya'ni drift auth muvaffaqiyatsiz bo'lishidan OLDIN ushlanadi. Bu
     "eng qimmatli bitta hiyla" (A.3) ning yagona sinov vositasi.

  2. Digest darvozasi — faqat `/ISAPI/*` yo'llari uchun. `mode` ga qarab
     tarmoqlanadi va HAR REKVIZIT URINISHIDA `state.auth_attempts` ni
     oshiradi. Bu sanoq D-03 ning **yagona o'lchov vositasi**: 03-05 rejasi
     `401` dan keyin retry BAJARILMAGANINI aynan shu son bilan isbotlaydi.

`/__sim__/*` esa ikkala qatlamdan ham chetda: Digest talab qilmaydi va
`mode="slow"` da HECH QACHON kechiktirilmaydi — u compose healthcheck'ining
nishoni, ya'ni kechiktirilsa konteyner `unhealthy` bo'lib qolardi va
`mode="slow"` testi butun stack'ni yiqitardi.
=============================================================================

NEGA `Date` middleware'i SOF ASGI (Starlette `BaseHTTPMiddleware` EMAS):
`BaseHTTPMiddleware` javobni alohida task'da qayta oqimlaydi, `silent`
rejimidagi ATAYLAB TUGATILMAGAN javob esa aynan oqim darajasida ishlaydi.
Sof ASGI wrapper `http.response.start` xabarini joyida tahrirlaydi va
tananing taqdiriga umuman aralashmaydi.

`app.state` — resurslarning yagona joyi (`core-api/app/main.py` naqshi):
    sim      `SimState`     joriy holat (jarayon xotirasida, bitta ishchi)
"""

from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime, timedelta
from email.utils import format_datetime
from typing import Any

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from .digest import (
    REALM,
    build_challenge,
    make_nonce,
    parse_authorization,
    verify,
    verify_basic,
)
from .isapi import (
    ISAPI_PREFIX,
    STREAM_LIMIT_XML,
    SilentDisconnect,
    SilentDropResponse,
    StreamLimitReached,
    handle_isapi,
    hikvision_error_xml,
    xml_response,
)
from .state import SimState, SimStateError, apply_patch

SIM_USERNAME = os.environ.get("SIM_USERNAME", "admin")
SIM_PASSWORD = os.environ.get("SIM_PASSWORD", "Sim12345")
"""Sim rekvizitlari. Ular SIR EMAS — ular test uskunasining ochiq parametri.

Real rejimga o'tish aynan shu ikki qiymatning bazadagi (Fernet bilan
shifrlangan) boshqa qiymatga almashishi bilan bo'ladi — KOD O'ZGARMAYDI
(`03-RESEARCH.md` B.9 jadvali).
"""

CONTROL_PREFIX = "/__sim__"


def _now(state: SimState) -> datetime:
    """Qurilmaning "o'z" vaqti — server vaqtidan `drift_seconds` ga siljigan."""
    return datetime.now(UTC) + timedelta(seconds=state.drift_seconds)


class DateHeaderMiddleware:
    """Har javobga siljitiladigan `Date` qo'yadi — soat-farqi yo'lining sinov vositasi.

    ⚠ `uvicorn` ning O'Z `Date` sarlavhasi `--no-date-header` bilan
    o'chirilgan (compose.yaml). Aks holda javobda IKKITA `Date` bo'lardi:
    uvicorn o'zinikini ASGI javobidan OLDIN qo'yadi, `httpx` esa bir xil
    nomli sarlavhalarni vergul bilan qo'shib beradi va
    `parsedate_to_datetime` yiqilardi — ya'ni drift o'lchovi jimgina
    ishlamay qolardi.
    """

    def __init__(self, app: ASGIApp, *, state_holder: FastAPI) -> None:
        self.app = app
        self.state_holder = state_holder

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                state: SimState = self.state_holder.state.sim
                MutableHeaders(scope=message)["date"] = format_datetime(_now(state), usegmt=True)
            await send(message)

        await self.app(scope, receive, send_wrapper)


def _unauthorized(*, stale: bool = False, body: str | None = None) -> Response:
    """`401` + Digest challenge. `body` berilsa Hikvision uslubidagi XML tanasi qo'shiladi."""
    headers = {"WWW-Authenticate": build_challenge(nonce=make_nonce(), stale=stale)}
    if body is None:
        return Response(status_code=401, headers=headers)
    return xml_response(body, status_code=401, headers=headers)


ACCOUNT_LOCKED_XML = (
    '<userCheck version="1.0" xmlns="http://www.hikvision.com/ver20/XMLSchema">\n'
    "  <statusValue>401</statusValue>\n"
    "  <statusString>Unauthorized</statusString>\n"
    "  <lockStatus>locked</lockStatus>\n"
    "  <unlockTime>1800</unlockTime>\n"
    "  <retryLoginTime>0</retryLoginTime>\n"
    "</userCheck>"
)
"""B.8: `account_locked` — 401 tanasida qulf holati va qolgan vaqt (soniya).

⚠ Bu javob D-03 ning butun mantiqini ochadi: `401` ni QAYTA URINISH qulf
muddatini **uzaytiradi**, ya'ni retry siyosati odatdagiga TESKARI.
"""

NO_PERMISSION_XML = hikvision_error_xml(
    status_code=6,
    status_string="Invalid Operation",
    sub_status="notSupport",
)


def _authenticate(state: SimState, request: Request) -> Response | None:
    """`/ISAPI/*` uchun darvoza. `None` — o'tdi; `Response` — rad etildi.

    Rejimlar tartibi ATAYLAB shunday:
      * `isapi_404` — auth'dan OLDIN. ISAPI'ni umuman qo'llamaydigan qurilma
        rekvizitni so'ramaydi ham, u shunchaki bunday yo'lni bilmaydi
        (`nvr_isapi_unavailable` rekvizitsiz aniqlanadi).
      * qolganlari — auth ichida.
    """
    if state.mode == "isapi_404":
        return xml_response(
            hikvision_error_xml(status_code=4, status_string="Invalid Operation"),
            status_code=404,
        )

    authorization = request.headers.get("Authorization")

    if state.mode == "basic_only":
        # A.3: `digest/basic` emas, `basic` rejimidagi firmware — Digest RAD ETILADI,
        # Basic esa QABUL QILINADI. Klient `Digest` yuborsa `verify_basic` uni
        # tanimaydi va javob `401` bo'lib qoladi — bu aynan kutilgan alomat.
        basic_challenge = {"WWW-Authenticate": f'Basic realm="{REALM}"'}
        if authorization is None:
            return Response(status_code=401, headers=basic_challenge)
        state.auth_attempts += 1
        if verify_basic(authorization, username=SIM_USERNAME, password=SIM_PASSWORD):
            return None
        return Response(status_code=401, headers=basic_challenge)

    if authorization is None:
        # Birinchi, autentifikatsiyasiz so'rov: challenge beriladi.
        # ⚠ Bu urinish SANALMAYDI — u rekvizit KO'RSATMAYDI. Hikvision'ning
        # qulflash sanagichi ham aynan rekvizit urinishlarini sanaydi, ya'ni
        # `auth_attempts` qurilmaning qulflash sanagichi bilan bir xil narsani
        # o'lchaydi (D-03).
        return _unauthorized(stale=state.mode == "digest_stale")

    state.auth_attempts += 1

    if state.mode == "account_locked":
        return _unauthorized(body=ACCOUNT_LOCKED_XML)

    if state.mode == "digest_stale":
        # Nonce har doim "eskirgan". A.3: `stale=true` ning takrorlanishi
        # deyarli har doim SOAT FARQI alomati.
        return _unauthorized(stale=True)

    params = parse_authorization(authorization)
    if not params:
        return _unauthorized()

    # `realm` BIZNIKI bo'lishi shart. Uni klientdan olish HA1 ni klient tanlagan
    # qiymat ustiga qurardi — parol baribir kerak bo'lardi, lekin sim real
    # qurilmadan farq qilib qolardi (u o'z realm'ini talab qiladi).
    if params.get("realm") != REALM:
        return _unauthorized()

    # RFC: `uri` klient hisobiga kiradi, shuning uchun HA2 uni KLIENTDAN oladi.
    # Lekin u so'rovning haqiqiy nishoni bilan mos kelishi ham SHART — aks holda
    # bitta yo'l uchun olingan `Authorization` sarlavhasini boshqasiga qayta
    # ishlatib bo'lardi.
    target = request.url.path
    if request.url.query:
        target = f"{target}?{request.url.query}"
    if params.get("uri") != target:
        return _unauthorized()

    if state.mode == "bad_password":
        # Rekvizit to'g'ri bo'lsa ham rad etiladi — `nvr_bad_credentials` yo'lini
        # deterministik qayta tug'dirish uchun (parolni bilmasdan ham sinash mumkin).
        return _unauthorized()

    if not verify(
        params,
        method=request.method,
        username=SIM_USERNAME,
        password=SIM_PASSWORD,
        realm=REALM,
    ):
        return _unauthorized()

    if state.mode == "no_permission":
        # A.3: autentifikatsiya O'TDI, lekin foydalanuvchida ISAPI huquqi yo'q.
        return xml_response(NO_PERMISSION_XML, status_code=403)

    return None


def create_app() -> FastAPI:
    app = FastAPI(
        title="SBOZOR nvr-sim (Hikvision ISAPI simulyatori)",
        version="0.1.0",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.state.sim = SimState.from_env()
    app.add_middleware(DateHeaderMiddleware, state_holder=app)

    # ------------------------------------------------------------------
    # Control-plane — Digest YO'Q, kechikish YO'Q.
    # ------------------------------------------------------------------

    @app.get(f"{CONTROL_PREFIX}/state")
    async def get_state() -> dict[str, Any]:
        state: SimState = app.state.sim
        return state.as_dict()

    @app.post(f"{CONTROL_PREFIX}/state")
    async def set_state(patch: dict[str, Any]) -> Response:
        state: SimState = app.state.sim
        try:
            apply_patch(state, patch)
        except (SimStateError, TypeError, ValueError) as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)
        return JSONResponse(state.as_dict())

    @app.post(f"{CONTROL_PREFIX}/reset")
    async def reset_state() -> dict[str, Any]:
        """Muhitdagi standart holatga qaytaradi.

        ⚠ `stream_claims` va `auth_attempts` NOLGA QAYTADI. Busiz testlar
        bir-birining sanog'ini meros qilib olardi: `stream_limit=4` testi
        oldingi testdan qolgan da'volar bilan boshlanib, BIRINCHI so'rovdayoq
        rad etilardi va sabab test mantig'ida emas, tozalanmagan holatda bo'lardi.
        """
        app.state.sim = SimState.from_env()
        state: SimState = app.state.sim
        return state.as_dict()

    @app.get(f"{CONTROL_PREFIX}/attempts")
    async def get_attempts() -> dict[str, int]:
        """Autentifikatsiya urinishlari sanog'i — D-03 ning o'lchov vositasi.

        03-05 rejasi `401` dan keyin retry BAJARILMAGANINI aynan shu son bilan
        isbotlaydi: bitta kashfiyot chaqiruvi = bitta rekvizit urinishi.
        """
        state: SimState = app.state.sim
        return {"auth_attempts": state.auth_attempts}

    # ------------------------------------------------------------------
    # Qurilma yuzasi — barcha `/ISAPI/*` yo'llari bitta darvozadan o'tadi.
    # ------------------------------------------------------------------

    @app.api_route(
        f"{ISAPI_PREFIX}/{{path:path}}",
        methods=["GET", "POST", "PUT", "DELETE"],
    )
    async def isapi(path: str, request: Request) -> Response:
        state: SimState = app.state.sim

        if state.mode == "slow" and state.delay_ms > 0:
            # `taskiq` job byudjeti va `httpx` timeout xulqini sinash uchun.
            await asyncio.sleep(state.delay_ms / 1000.0)

        denied = _authenticate(state, request)
        if denied is not None:
            return denied

        try:
            return handle_isapi(state, path, request)
        except StreamLimitReached:
            # D-05 / A.5 — `reject` shakli: qurilma javob BERADI va sabab XML'da.
            return xml_response(STREAM_LIMIT_XML, status_code=503)
        except SilentDisconnect:
            # D-05 / A.5 — `silent` shakli: javob TUGATILMAYDI, ulanish yopiladi.
            return SilentDropResponse()

    return app


app = create_app()
