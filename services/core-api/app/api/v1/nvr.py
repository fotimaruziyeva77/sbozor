"""NVR qurilmalari, ulanish testi va kashfiyot (CAM-01, CAM-08).

=============================================================================
MARSHRUT TARTIBI AHAMIYATLI: `POST /test-connection` `{nvr_id}` SHABLONIDAN
OLDIN E'LON QILINGAN.

FastAPI marshrutlarni E'LON TARTIBIDA solishtiradi. Teskari tartibda
`POST /api/v1/nvr-devices/test-connection` so'rovi `POST /{nvr_id}/...`
shabloniga tushardi, `"test-connection"` esa UUID emas — natijada admin
tekshiruv natijasi o'rniga 422 olardi va sabab kodga qarab UMUMAN
ko'rinmasdi (ikkala marshrut ham to'g'ri yozilgan bo'lib turardi).
`stalls.py:3-11` dagi `GET /map` bilan aynan bir xil holat.
=============================================================================

=============================================================================
KASHFIYOT SO'ROV ICHIDA ISHLAMAYDI — VA BU ARXITEKTURA QARORI, TEZLIK EMAS.

Byudjet (`03-RESEARCH.md` E.16): ~29 ISAPI so'rovi × 2 borish × 300 ms ≈
17 soniya yaxshi holatda, sekin NVR'da 60+. `compose.yaml` da esa
`uvicorn --workers 1` QAT'IY qilib qo'yilgan, ya'ni bitta uzoq so'rov
BUTUN API'ni bloklaydi (T-03-42).

Shuning uchun:

    POST /{id}/discover                    ->  202 + {"run_id": ...}
    GET  /{id}/discovery-runs/{run_id}     ->  poll

«Ulanishni tekshirish» esa ATAYIN INLINE qoladi: u 1–2 ISAPI so'rov ≈ 1
soniya va admin tugma bosgach DARHOL javob kutadi.
=============================================================================

=============================================================================
«ULANISHNI TEKSHIRISH» — IKKI QAT'IY QOIDA.

  1. **U YOZUV YARATMAYDI.** Chaqiruvdan oldin va keyin
     `SELECT count(*) FROM nvr_devices` BIR XIL. Tekshiruv natijasi
     saqlansa admin "sinab ko'rish" bilan "qo'shish" ni ajrata olmasdi va
     har muvaffaqiyatsiz urinish yarim to'ldirilgan qator qoldirardi.

  2. **U RATE-LIMIT OSTIDA.** Chegarasiz endpoint NVR'ga qarshi
     PAROL-BRUTE-FORCE vositasi bo'lardi: u ham parolni topishga
     urinardi, ham mijozning hisobini 30 daqiqaga qulflardi (T-03-37,
     D-03). Chegara qurilmaga BORISHDAN OLDIN tekshiriladi — sabab
     `security/ratelimit.py` docstringida.
=============================================================================

CROSS-TENANT JAVOB — HAR DOIM 404 (T-03-40), 403 EMAS.

`market_id` HECH QACHON SO'ROV TANASIDAN OLINMAYDI (T-03-44): u faqat
`_market_id(principal)` dan keladi va `NvrDeviceCreateRequest` da bunday
maydon umuman e'lon qilinmagan (`schemas.py` dagi bo'lim izohi).

-----------------------------------------------------------------------------
XATO XARITASI — FAQAT `sqlstate` BO'YICHA (`stalls.py:188-207` naqshi):

    23505 `POST ""` yo'lida         ->  409 nvr_host_taken
    23505 `POST /{id}/discover` da  ->  409 discovery_already_running + run_id
    23503                           ->  404 (begona yoki mavjud bo'lmagan nvr_id)

Noma'lum SQLSTATE QAYTA KO'TARILADI: "har ehtimolga qarshi" 409 yangi
konstraytni jimgina noto'g'ri xabar bilan yashirardi.
-----------------------------------------------------------------------------
"""

# =============================================================================
# ⚠ `audit_read` BU FAYLDA ATAYIN ULANMAGAN — VA BU NAZORAT HOLATI.
#
# `stalls.py` dagi qoida: shaxsiy ma'lumot qaytaradigan HAR o'qish
# jurnalga tushadi (D-09). Bu fayldagi ikkala `GET` ham o'sha qoidaga
# TUSHMAYDI:
#
#   `GET ""`                     -> `host`, `model`, `has_password`,
#                                   portlar. Sotuvchi ismi ham, telefoni
#                                   ham, birorta shaxsiy ma'lumot ham yo'q.
#   `GET /discovery-runs/{id}`   -> sonlar va xato kodi. Uni UI HAR IKKI
#                                   SONIYADA chaqiradi (UI-SPEC §5.3),
#                                   ya'ni bitta kashfiyot ~30 ta o'qish
#                                   yozuvi qoldirardi va haqiqiy o'qish
#                                   hodisalari o'sha shovqin ichida
#                                   ko'milardi.
#
# Bu `stalls.py:348-369` dagi `GET /map` nazorat holatining AYNAN jufti:
# darvoza "hamma `GET` ga audit" TALAB QILMASLIGI kerak va u aynan shu
# yerda o'lchanadi (`tests/tenancy/test_personal_data_coverage.py`).
#
# ⚠ QABUL MEZONI BU FAYLNI O'QISH-AUDITI DEPENDENCY'SINING CHAQIRUV
# SHAKLI BO'YICHA GREP QILADI, ya'ni o'sha shakl bu izohda ham LITERAL
# yozilmaydi — aks holda darvoza o'z-o'ziga qarshi turardi. Bu 03-04 va
# 03-05 da `test_no_sim_branching` bilan ikki marta takrorlangan sinf
# xatoning aynan o'zi: grep KODNI IZOHDAN AJRATMAYDI.
# =============================================================================

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sbozor_core.enums import AuditAction, DiscoveryRunStatus
from sqlalchemy.exc import IntegrityError

from app.deps import CacheDep, CurrentPasswordDep, Principal, TenantSessionDep, require_permission
from app.jobs.discovery import JOB_INTERNAL_ERROR
from app.repositories.nvr_repo import NvrRepository
from app.repositories.stall_repo import sqlstate_of
from app.schemas import (
    DiscoveryRunRead,
    DiscoveryStartResponse,
    NvrDeviceCreateRequest,
    NvrDeviceListResponse,
    NvrDeviceRead,
    NvrDeviceUpdateRequest,
    NvrPasswordRequest,
    NvrTestConnectionRequest,
    NvrTestConnectionResponse,
)
from app.security.audit import TABLE_NVR_DEVICES, write_app_audit
from app.security.ratelimit import TooManyAttempts, check_nvr_test_rate
from app.security.rbac import Permission
from app.security.secrets import CURRENT_KEY_VERSION, encrypt_nvr_password
from app.services.isapi.client import IsapiClient
from app.services.isapi.errors import AUTH_LOCKING_CODES
from app.services.nvr_host import (
    NvrAddressError,
    NvrHostNotPrivateError,
    assert_private_host,
    split_address,
)
from app.worker import enqueue_discovery

if TYPE_CHECKING:
    from sbozor_core.models import NvrDevice, NvrDiscoveryRun

    from app.services.isapi.client import ProbeResult

log = structlog.get_logger(__name__)

router = APIRouter(tags=["nvr"])

# =============================================================================
# HUQUQ TALABI MARSHRUT DEKORATORIDA (`dependencies=[...]`), IMZO PARAMETRI
# SIFATIDA EMAS (§S-4).
#
# FastAPI dekorator darajasidagi bog'liqliklarni imzo parametrlaridan OLDIN
# hal qiladi (`fastapi/routing.py` ularni `dependant.dependencies` ning
# BOSHIGA qo'yadi). Ya'ni huquqsiz so'rov endpoint tanasiga — va u bilan
# birga har qanday yon ta'sirga — YETIB BORMAYDI.
#
# ⚠ ALIAS QILINMAYDI (`MANAGE_GATE = Depends(...)` kabi). Har dekoratorda
#   huquqning NOMI ochiq turishi kerak: marshrutni o'qiyotgan odam
#   "bunga kim kira oladi?" savoliga faylning boshqa joyiga qaramasdan
#   javob olsin. Aynan shu sabab bilan qabul mezoni ham nomni HAR
#   marshrutda sanaydi.
#
# Imzodagi `principal` FAQAT `market_id` va `user_id` uchun
# (`CurrentPasswordDep` — vaqtinchalik parol darvozasidan o'tgan
# `Principal`), huquq tekshiruvi uchun EMAS.
# =============================================================================

_NOT_FOUND = "not_found"
_HOST_TAKEN = "nvr_host_taken"
_HOST_PUBLIC_BLOCKED = "nvr_host_public_blocked"
_ADDRESS_INVALID = "nvr_address_invalid"
_ALREADY_RUNNING = "discovery_already_running"
_TOO_MANY_ATTEMPTS = "too_many_attempts"

UNIQUE_VIOLATION = "23505"
FK_VIOLATION = "23503"


def _market_id(principal: Principal) -> UUID:
    """Tanlangan bozor (`stalls.py:173-180` bilan aynan bir xil)."""
    if principal.market_id is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="market_not_selected",
        )
    return principal.market_id


def _not_found() -> HTTPException:
    """Cross-tenant va mavjud bo'lmagan qurilma uchun BIR XIL javob (T-03-40)."""
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_NOT_FOUND)


def _split_or_422(address: str) -> tuple[str, int, bool]:
    """Manzilni ajratadi va xususiylik darvozasidan o'tkazadi (SC#5, T-03-23).

    IKKI XATO SINFI — IKKI XIL KOD va bu ajratish 03-04 ning ochiq
    talabi (`NvrAddressError` / `NvrHostNotPrivateError` docstringlari):
    birinchisiga javob manzilni qayta yozish, ikkinchisiga esa tunnel
    ichidagi manzilni TOPISH.
    """
    try:
        host, port, use_tls = split_address(address)
    except NvrAddressError as exc:
        log.info("nvr_address_invalid")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=_ADDRESS_INVALID,
        ) from exc

    try:
        # ⚠ TEKSHIRUV KIRISH CHEGARASIDA, repozitoriyda EMAS
        #   (`nvr_repo.create_device` docstringi): repozitoriy migratsiya,
        #   seed yoki fon jarayonidan ham chaqirilishi mumkin va o'shanda
        #   darvoza jimgina o'tkazib yuborilardi.
        assert_private_host(host)
    except NvrHostNotPrivateError as exc:
        log.info("nvr_host_public_blocked")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=_HOST_PUBLIC_BLOCKED,
        ) from exc

    return host, port, use_tls


def _device_conflict(exc: IntegrityError) -> HTTPException:
    """`nvr_devices` yo'lidagi `IntegrityError` -> aniq `detail` kodi.

    Noma'lum SQLSTATE QAYTA KO'TARILADI (`main.py` global handleri uni
    500 ga aylantiradi) — `stalls.py::_stall_conflict` bilan aynan bir
    xil qoida va aynan bir xil sabab.
    """
    state = sqlstate_of(exc)
    if state == UNIQUE_VIOLATION:
        log.info("nvr_host_taken", sqlstate=state)
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_HOST_TAKEN)
    if state == FK_VIOLATION:
        log.info("nvr_reference_not_found", sqlstate=state)
        return _not_found()
    raise exc


def _read(device: NvrDevice, *, has_password: bool) -> NvrDeviceRead:
    """Qator -> javob modeli.

    `tunnel_subnet` `CIDR()` ustuni va u Python tomonda `str` bo'lib
    keladi; `source_ip` (03-04 ning `threat_flag: value-format`) bu
    javobda UMUMAN yo'q, ya'ni `/32` artefakti bu yerga tegmaydi.
    """
    return NvrDeviceRead(
        id=device.id,
        host=device.host,
        port=device.port,
        use_tls=device.use_tls,
        username=device.username,
        model=device.model,
        serial_number=device.serial_number,
        firmware_version=device.firmware_version,
        device_type=device.device_type,
        rtsp_port=device.rtsp_port,
        rtsp_port_assumed=device.rtsp_port_assumed,
        tunnel_subnet=None if device.tunnel_subnet is None else str(device.tunnel_subnet),
        last_discovery_at=device.last_discovery_at,
        has_password=has_password,
    )


def _run_read(run: NvrDiscoveryRun) -> DiscoveryRunRead:
    """Yugurish qatori -> poll javobi (UI-SPEC §5.2 ning oltita holati)."""
    return DiscoveryRunRead(
        id=run.id,
        nvr_id=run.nvr_id,
        status=DiscoveryRunStatus(run.status),
        started_at=run.started_at,
        finished_at=run.finished_at,
        channels_found=run.channels_found,
        channels_added=run.channels_added,
        channels_marked_offline=run.channels_marked_offline,
        error_code=run.error_code,
        error_detail=run.error_detail,
    )


async def _device_or_404(repo: NvrRepository, nvr_id: UUID) -> NvrDevice:
    device = await repo.get_device(nvr_id)
    if device is None:
        raise _not_found()
    return device


# ===========================================================================
# Qurilma reestri
# ===========================================================================


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=NvrDeviceRead,
    dependencies=[Depends(require_permission(Permission.CAMERA_MANAGE))],
)
async def create_nvr_device(
    payload: NvrDeviceCreateRequest,
    principal: CurrentPasswordDep,
    session: TenantSessionDep,
) -> NvrDeviceRead:
    """Yangi NVR qurilmasi (`CAMERA_MANAGE`) — D-01 ning butun kirish yuzasi.

    Admin FAQAT manzil + login/parol beradi. Model, seriya raqami,
    kanallar va RTSP porti KASHFIYOT natijasida to'ldiriladi.

    409 `nvr_host_taken` — shu bozorda o'sha `host:port` allaqachon bor;
    422 `nvr_host_public_blocked` — marshrutlanadigan ommaviy IP (T-03-23);
    422 `nvr_address_invalid` — manzilni ajratib bo'lmadi.
    """
    market_id = _market_id(principal)
    host, port, use_tls = _split_or_422(payload.address)

    repo = NvrRepository(session, market_id)
    try:
        nvr_id = await repo.create_device(
            host=host,
            port=port,
            use_tls=use_tls,
            username=payload.username,
        )
        # ⚠ PAROL SHU YERDA SHIFRLANADI. Repozitoriy `bytes` dan boshqa
        #   hech nima ko'rmaydi (`nvr_repo.py` modul docstringi) —
        #   `user_repo` parolni hash holida olgani bilan bir xil chegara.
        await repo.put_credential(
            nvr_id,
            encrypt_nvr_password(payload.password),
            CURRENT_KEY_VERSION,
        )
    except IntegrityError as exc:
        raise _device_conflict(exc) from exc

    device = await _device_or_404(repo, nvr_id)
    log.info("nvr_device_created", host=host, port=port, username=payload.username)
    return _read(device, has_password=True)


@router.get(
    "",
    response_model=NvrDeviceListResponse,
    dependencies=[Depends(require_permission(Permission.CAMERA_VIEW))],
)
async def list_nvr_devices(
    principal: CurrentPasswordDep,
    session: TenantSessionDep,
) -> NvrDeviceListResponse:
    """Bozorning NVR qurilmalari (`CAMERA_VIEW`).

    ⚠ O'QISH AUDITI BU YERDA ATAYIN YO'Q — sabab fayl boshidagi izohda.

    `has_password` HAR QATOR uchun alohida so'rov QILMAYDI: rekvizitlar
    1:1 jadvalda va ular bitta `IN` so'rovi bilan olinadi. Har qurilma
    uchun alohida `get_credential()` chaqirish N+1 hosil qilardi — bir
    bozorda NVR soni kichik bo'lsa ham, naqsh 4-fazaga meros bo'lib
    o'tardi.
    """
    market_id = _market_id(principal)
    repo = NvrRepository(session, market_id)
    devices = await repo.list_devices()
    with_password = await repo.devices_with_credentials()

    return NvrDeviceListResponse(
        items=[_read(device, has_password=device.id in with_password) for device in devices]
    )


# ⚠⚠ SHU MARSHRUT `{nvr_id}` SHABLONIDAN OLDIN TURISHI SHART —
#    sabab modul docstringida. Uni pastga ko'chirish HECH QANDAY
#    testni sintaksis darajasida buzmaydi, faqat 422 beradi.
@router.post(
    "/test-connection",
    response_model=NvrTestConnectionResponse,
    dependencies=[Depends(require_permission(Permission.CAMERA_MANAGE))],
)
async def test_nvr_connection(
    payload: NvrTestConnectionRequest,
    principal: CurrentPasswordDep,
    cache: CacheDep,
) -> NvrTestConnectionResponse:
    """«Ulanishni tekshirish» — YOZUVSIZ, RATE-LIMIT ostida, HAR DOIM 200.

    ⚠ `TenantSessionDep` BU YERDA ATAYIN YO'Q. Endpoint bazaga umuman
      tegmaydi va sessiya so'rash "balki bir kun yozamiz" degan yo'lni
      ochiq qoldirardi — imzoning o'zi qoidani ushlab tursin
      (`rtsp_url()` parol parametrini qabul qilmagani bilan bir xil
      qaror).

    429 — chegara oshdi va so'rov NVR'ga BORMADI.
    200 + `ok=false` — qurilma javob berdi (yoki bermadi), lekin bu
    HTTP xatosi EMAS: UI uni forma ichidagi blok sifatida chizadi va
    unda sabab hamda tuzatish yo'li bo'ladi (D-02).
    """
    market_id = _market_id(principal)
    host, port, use_tls = _split_or_422(payload.address)

    try:
        # ⚠ CHEGARA NVR'GA BORISHDAN OLDIN. Keyin tekshirilsa chegaradan
        #   oshgan so'rov ALLAQACHON qurilmaning qulflash hisoblagichini
        #   oshirgan bo'lardi (T-03-37).
        await check_nvr_test_rate(cache, market_id=str(market_id), host=f"{host}:{port}")
    except TooManyAttempts as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=_TOO_MANY_ATTEMPTS,
        ) from exc

    scheme = "https" if use_tls else "http"
    # ⚠ JURNAL KONTEKSTIGA FAQAT `host`/`port`/`username` TUSHADI (T-03-35).
    log.info("nvr_test_connection", host=host, port=port, username=payload.username)

    base_url = f"{scheme}://{host}:{port}"
    async with IsapiClient(base_url, payload.username, payload.password) as client:
        result: ProbeResult = await client.probe()

    return _probe_response(result)


def _probe_response(result: ProbeResult) -> NvrTestConnectionResponse:
    """`ProbeResult` -> HTTP javobi (UI-SPEC §4.5 ning to'rt majburiy maydoni)."""
    if not result.ok:
        return NvrTestConnectionResponse(
            ok=False,
            error_code=result.error_code,
            error_detail=result.error_detail or None,
            # UI-SPEC §4.4 ning backend tomoni: qayta urinish qurilmadagi
            # qulflash hisoblagichini oshiradigan kodlar shu bayroq bilan
            # belgilanadi va UI "Qayta urinish" ni RENDER QILMAYDI.
            auth_locked=result.error_code in AUTH_LOCKING_CODES,
        )

    device = result.device
    return NvrTestConnectionResponse(
        ok=True,
        model=None if device is None else device.model,
        device_type=None if device is None else device.device_type,
        # ⚠ SERIYA RAQAMI JAVOBDA BOR, LEKIN UI UNI BU BOSQICHDA
        #   KO'RSATMAYDI (UI-SPEC §4.5): u yozuv saqlangandan keyin NVR
        #   kartasida chiqadi. Maydonni backendda saqlash arzon va u
        #   "bu o'sha qurilmami?" savolini keyin javobsiz qoldirmaydi.
        serial_number=None if device is None else device.serial_number,
        channels_preview=result.channels_preview,
        clock_drift_seconds=result.clock_drift_seconds,
        rtsp_port=result.rtsp_port,
        rtsp_port_assumed=result.rtsp_port_assumed,
    )


@router.patch(
    "/{nvr_id}",
    response_model=NvrDeviceRead,
    dependencies=[Depends(require_permission(Permission.CAMERA_MANAGE))],
)
async def update_nvr_device(
    nvr_id: UUID,
    payload: NvrDeviceUpdateRequest,
    principal: CurrentPasswordDep,
    session: TenantSessionDep,
) -> NvrDeviceRead:
    """ISAPI foydalanuvchi nomini yangilaydi (`CAMERA_MANAGE`).

    `exclude_unset=True` MAJBURIY: usiz har `PATCH` berilmagan maydonlarni
    `null` bilan tozalab ketardi (`stalls.py::update_stall` bilan bir xil
    sabab).

    Manzil va tunnel BU YERDA O'ZGARMAYDI — sabab
    `NvrDeviceUpdateRequest` docstringida.
    """
    market_id = _market_id(principal)
    repo = NvrRepository(session, market_id)

    changes: dict[str, Any] = payload.model_dump(exclude_unset=True, exclude_none=True)
    if changes and not await repo.update_device(nvr_id, **changes):
        raise _not_found()

    device = await _device_or_404(repo, nvr_id)
    return _read(device, has_password=await repo.get_credential(nvr_id) is not None)


@router.post(
    "/{nvr_id}/password",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    dependencies=[Depends(require_permission(Permission.CAMERA_MANAGE))],
)
async def update_nvr_password(
    nvr_id: UUID,
    payload: NvrPasswordRequest,
    principal: CurrentPasswordDep,
    session: TenantSessionDep,
) -> Response:
    """NVR parolini almashtiradi (`CAMERA_MANAGE`, SC#4).

    ⚠ AUDIT YOZUVI QIYMATSIZ. `nvr_credentials` jadvali DB triggeridan
      BUTUNLAY chiqarilgan (T-03-13: kalit buzilganda audit TARIXIY
      parollarni ham berardi), shuning uchun izni ILOVA qatlami
      qoldiradi — va u faqat FAKTNI yozadi: "kim, qachon almashtirdi".
      "Parol nima edi" savoliga javob hech qachon bo'lmaydi.

    ⚠ Yozuv `nvr_devices` USTIGA qoldiriladi, `nvr_credentials` ustiga
      emas: `audit_log.row_id` `uuid` va rekvizit jadvalining birlamchi
      kaliti `nvr_id` — ya'ni ular baribir bir xil qiymat, lekin jadval
      nomi jurnalni o'qiyotgan odamni MAVJUD jadvalga yo'naltiradi.

    204 — javob tanasiz. Yangilangan `NvrDeviceRead` ni qaytarish
    "parol saqlandi" faktini qurilma pasporti bilan aralashtirardi.
    """
    market_id = _market_id(principal)
    repo = NvrRepository(session, market_id)
    await _device_or_404(repo, nvr_id)

    await repo.put_credential(
        nvr_id,
        encrypt_nvr_password(payload.password),
        CURRENT_KEY_VERSION,
    )
    await write_app_audit(
        session,
        action=AuditAction.UPDATE,
        table_name=TABLE_NVR_DEVICES,
        row_id=nvr_id,
        new={"credentials_updated": True},
        principal=principal,
        track_changes=False,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ===========================================================================
# Kashfiyot — 202 + poll
# ===========================================================================


@router.post(
    "/{nvr_id}/discover",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=DiscoveryStartResponse,
    dependencies=[Depends(require_permission(Permission.CAMERA_MANAGE))],
)
async def start_discovery(
    nvr_id: UUID,
    request: Request,
    principal: CurrentPasswordDep,
    session: TenantSessionDep,
) -> DiscoveryStartResponse:
    """Kashfiyotni fon navbatiga qo'yadi (`CAMERA_MANAGE`) — **202**.

    ⚠ FAOL YUGURISH OLDINDAN TEKSHIRILMAYDI. `create_run()` `queued`
      qatorini yozadi va `0012` dagi QISMAN UNIQUE indeks ikkinchisini
      `23505` bilan rad etadi. "Tekshir-keyin-yoz" yo'li poyga
      tug'dirardi: ikki so'rov bir vaqtda bo'sh holatni ko'rib,
      ikkalasi ham skan boshlardi — NVR ga ikki barobar yuk va ikki
      barobar `401` urinishi (T-03-16).

    409 javob tanasida MAVJUD yugurishning `run_id` si bo'ladi (UI-SPEC
    §5.6 [TALAB]) — usiz UI ikkinchi so'rov qilishga majbur bo'lardi,
    ya'ni poyga holatining o'zida yana bitta poyga.
    """
    market_id = _market_id(principal)
    repo = NvrRepository(session, market_id)
    await _device_or_404(repo, nvr_id)

    try:
        run_id = await repo.create_run(nvr_id, triggered_by=principal.user_id)
    except IntegrityError as exc:
        raise await _discovery_conflict(repo, nvr_id, exc) from exc

    try:
        await _enqueue(request)(
            market_id=market_id,
            nvr_id=nvr_id,
            run_id=run_id,
            actor_id=principal.user_id,
        )
    except Exception as exc:  # noqa: BLE001 - sabab quyida, yo'l yopilishi SHART
        # ⚠ NAVBATGA TUSHMAGAN YUGURISH `failed` DEB YOPILADI VA BU
        #   MAJBURIY. Aks holda qator MANGU `queued` bo'lib qolardi va
        #   qisman UNIQUE indeks shu NVR uchun HAR QANDAY keyingi
        #   kashfiyotni bloklardi — foydalanuvchi uchun bu "tugma
        #   ishlamay qoldi" bo'lib ko'rinardi va sababi hech qayerda
        #   yozilmasdi.
        log.exception("nvr_discovery_enqueue_failed", nvr_id=str(nvr_id), run_id=str(run_id))
        await repo.finish_run(
            run_id,
            DiscoveryRunStatus.FAILED.value,
            error_code=JOB_INTERNAL_ERROR,
            error_detail={"raw": "kashfiyotni navbatga qo'yib bo'lmadi"},
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=JOB_INTERNAL_ERROR,
        ) from exc

    return DiscoveryStartResponse(run_id=run_id)


async def _discovery_conflict(
    repo: NvrRepository, nvr_id: UUID, exc: IntegrityError
) -> HTTPException:
    """`23505` -> **409 + mavjud `run_id`** (UI-SPEC §5.6 [TALAB]).

    ⚠ SHAKL `main.py:178-197` DAGI GLOBAL HANDLER BILAN MOS: u
      `{"detail": "..."}` yozadi, ya'ni frontendning mavjud
      `detail: string` shartnomasi (`lib/market-errors.ts`) buzilmasligi
      kerak. Shuning uchun `run_id` `detail` ning YONIDA turadi, ICHIDA
      emas — `detail` ni obyektga aylantirish har bir mavjud xato
      ishlovchisini sindirardi.

    `active_run_id()` KONSTRAYT BUZILGANDAN KEYIN o'qiladi: oldindan
    o'qish aynan o'sha poygani qaytarardi.
    """
    state = sqlstate_of(exc)
    if state != UNIQUE_VIOLATION:
        if state == FK_VIOLATION:
            return _not_found()
        raise exc

    active = await repo.active_run_id(nvr_id)
    log.info("discovery_already_running", nvr_id=str(nvr_id), run_id=str(active))
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={"detail": _ALREADY_RUNNING, "run_id": str(active) if active else None},
    )


@router.get(
    "/{nvr_id}/discovery-runs/{run_id}",
    response_model=DiscoveryRunRead,
    dependencies=[Depends(require_permission(Permission.CAMERA_VIEW))],
)
async def get_discovery_run(
    nvr_id: UUID,
    run_id: UUID,
    principal: CurrentPasswordDep,
    session: TenantSessionDep,
) -> DiscoveryRunRead:
    """Kashfiyot holatini qaytaradi (`CAMERA_VIEW`) — UI buni poll qiladi.

    ⚠ O'QISH AUDITI ATAYIN YO'Q — sabab fayl boshidagi izohda (UI har
      ikki soniyada chaqiradi).

    `run.nvr_id != nvr_id` bo'lsa ham **404**: yo'l qurilma ostida
    yashaydi, ya'ni boshqa qurilmaning yugurishini shu yo'l orqali
    o'qish "topilmadi" degani.
    """
    market_id = _market_id(principal)
    repo = NvrRepository(session, market_id)

    run = await repo.get_run(run_id)
    if run is None or run.nvr_id != nvr_id:
        raise _not_found()
    return _run_read(run)


def _enqueue(request: Request) -> Any:
    """Navbatga qo'yuvchi — `app.state` dan, moduldan EMAS (agar u yerda bo'lsa).

    ⚠ NEGA INJEKSIYA NUQTASI KERAK: modul darajasidagi `enqueue_discovery`
      compose tarmog'idagi `cache` ga qarab turadi. Integratsiya testi esa
      o'z Valkey konteynerida ishlaydi (`tests/conftest.py::valkey_url`)
      va u yerda hech qanday worker yo'q — ya'ni test "navbatga
      qo'yildimi?" savolini O'ZI yozib olishi kerak.

      `app.state` — bu loyihada resurs almashtirishning MAVJUD naqshi
      (`sessionmaker`, `cache`, `settings` hammasi shu yerdan keladi va
      `tests/conftest.py::api_app` aynan shu maydonlarni to'ldiradi).
      Yangi mexanizm kiritilmaydi.

    Prod yo'lida qiymatni `main.py::lifespan` qo'yadi; u yo'q bo'lsa
    modul darajasidagi funksiya ishlatiladi — ya'ni unutish XAVFSIZ
    tomonga ishlaydi.
    """
    return getattr(request.app.state, "enqueue_discovery", enqueue_discovery)
