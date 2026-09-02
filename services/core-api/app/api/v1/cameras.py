"""Kameralar reestri, arxivlash va jonli ko'rish chiptasi (CAM-02, CAM-03).

=============================================================================
`DELETE` MARSHRUTI BU FAYLDA UMUMAN YO'Q — VA U HECH QACHON QO'SHILMAYDI
(D-10).

Sabab tozalik emas, DALIL: `cameras.id` ga 4-fazadagi snapshotlar va
5-fazadagi zona poligonlari bog'lanadi. Qatorni o'chirish o'sha tarixni
BIRGA olib ketardi — «bu rasta o'sha kuni band edimi?» savoli javobsiz
qolardi va aynan shu savolga javob berish mahsulotning butun mazmuni.

Shuning uchun ikkita nomlangan amal bor: `POST /{id}/archive` va
`POST /{id}/restore`. `is_archived` `name_overridden` bilan BIR XIL
qoidaga bo'ysunadi — qayta skan arxivlangan kanalni TIKLAMAYDI
(`nvr_repo.upsert_cameras` docstringidagi 3-qoida).

⚠ FE'L HAM «ARXIVLASH», «O'CHIRISH» EMAS (UI-SPEC §9.1). So'z bir marta
kirsa, u tarjima orqali tarqaladi va D-10 ni jimgina buzadi; matn
darvozasi frontend tomonda (03-08 G-4), lekin nom shu yerda tug'iladi.

Mexanik darvoza: `tests/tenancy/test_camera_route_coverage.py::
test_no_delete_route_exists` `app.routes` ni o'qiydi, bu faylni EMAS.
=============================================================================

=============================================================================
HUQUQ TALABI MARSHRUT DEKORATORIDA (`dependencies=[...]`), IMZO PARAMETRI
SIFATIDA EMAS (§S-4, `stalls.py:28-42`).

FastAPI dekorator darajasidagi bog'liqliklarni imzo parametrlaridan OLDIN
hal qiladi (`fastapi/routing.py` ularni `dependant.dependencies` ning
BOSHIGA qo'yadi). Ya'ni 403 olgan so'rov `audit_read` gacha YETIB
BORMAYDI va jurnalda «kim nimani ko'rdi» degan YOLG'ON DALIL qolmaydi.

Bu qoida bu yerda odatdagidan ham qimmatroq: jonli ko'rish yozuvi
(`reason="live_view"`) nizo paytida «kim ko'rdi» savoliga javob beradi
(RESEARCH E.15). Rad etilgan so'rov o'sha jurnalga tushsa, dalil
ISHONCHSIZ bo'lardi — ko'rmagan odam ko'rgan bo'lib turardi.

⚠ ALIAS QILINMAYDI (`VIEW_GATE = Depends(...)` kabi): har dekoratorda
  huquqning NOMI ochiq turishi kerak (`nvr.py:141-159` da o'rnatilgan
  qoida). Quyidagi `CameraViewerDep`/`CameraManagerDep` — IMZO
  aliaslari (`principal` ni olish uchun), darvoza aliaslari EMAS.
=============================================================================

CROSS-TENANT JAVOB — HAR DOIM 404 (T-03-46), 403 EMAS. Begona bozorning
`camera_id` si va mavjud bo'lmagan `camera_id` bir xil javob oladi.
"""

from __future__ import annotations

import ipaddress
from typing import TYPE_CHECKING, Annotated
from uuid import UUID

import structlog
from cryptography.fernet import InvalidToken
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import SecretStr
from sbozor_core.enums import CameraStatus

from app.deps import Principal, TenantSessionDep, require_permission
from app.repositories.nvr_repo import NvrRepository
from app.schemas import (
    CameraListResponse,
    CameraQuery,
    CameraRead,
    CameraUpdateRequest,
    LiveTokenResponse,
)
from app.security.audit import TABLE_CAMERAS, AuditReadIntent, audit_read
from app.security.rbac import Permission
from app.security.secrets import decrypt_nvr_password
from app.security.tokens import LIVE_TOKEN_MAX_TTL_SECONDS, issue_live_token
from app.services.camagent_live import (
    PREVIEW_DURATION_S,
    STREAM_DURATION_S,
    CamAgentLiveError,
    is_camagent_device,
    open_stream as open_camagent_stream,
)
from app.services.go2rtc import TRANSPORT_HINT, Go2rtcClient, Go2rtcError, live_view_url
from app.services.live_source import authenticated_rtsp_source
from app.services.rtsp import rtsp_url

if TYPE_CHECKING:
    from sbozor_core.models import Camera, NvrDevice

    from app.settings import Settings

log = structlog.get_logger(__name__)

router = APIRouter(tags=["cameras"])

CameraManagerDep = Annotated[Principal, Depends(require_permission(Permission.CAMERA_MANAGE))]
CameraViewerDep = Annotated[Principal, Depends(require_permission(Permission.CAMERA_VIEW))]

CameraReadIntentDep = Annotated[
    AuditReadIntent,
    Depends(audit_read(TABLE_CAMERAS, reason="camera_view")),
]
"""Kameralar REESTRINING o'qilishi — «kim ro'yxatni varaqladi».

`reason` pastdagi `live_view` DAN FARQ QILADI (`stalls.py:137-140` da
o'rnatilgan qoida): jurnalni o'qiyotgan odam «kim kameralar ro'yxatini
ko'rdi» va «kim jonli tasvirni OCHDI» ni ajratishi kerak. Birinchisi —
inventar bo'yicha harakat, ikkinchisi — jonli tasvir (shaxsiy ma'lumot)
ustidagi hodisa; bir xil qiymat bilan bu farq jurnalda umuman
ko'rinmasdi.
"""

LiveViewIntentDep = Annotated[
    AuditReadIntent,
    Depends(audit_read(TABLE_CAMERAS, reason="live_view")),
]
"""Jonli tasvirning OCHILISHI — nizo paytidagi «kim ko'rdi» dalili (RESEARCH E.15).

`resource_type` baribir `cameras`: o'qilgan RESURS kamera. `reason` esa
hodisani ajratadi va `audit_log.new_value.reason` filtri bilan
«kim jonli tasvirni ochdi?» savoli aynan shu qiymat orqali javob oladi.
"""

_NOT_FOUND = "not_found"
_EMPTY_UPDATE = "empty_update"
_OVERRIDE_NEEDS_NAME = "name_overridden_requires_name"


def _market_id(principal: Principal) -> UUID:
    """Tanlangan bozor (`nvr.py:172-179` bilan aynan bir xil)."""
    if principal.market_id is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="market_not_selected",
        )
    return principal.market_id


def _not_found() -> HTTPException:
    """Begona va mavjud bo'lmagan kamera uchun BIR XIL javob (T-03-46)."""
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_NOT_FOUND)


def normalize_source_ip(value: str | None) -> str | None:
    """`inet` qiymatini prefikssiz manzilga keltiradi (03-04 `value-format`).

    PostgreSQL `inet` ustuni `192.168.1.10` ni `192.168.1.10/32` bo'lib
    QAYTARADI. Bu 03-04 da o'lchangan va `test_source_ip_is_stored_as_a_
    host_prefixed_inet` bilan qulflangan fakt; o'sha reja uni ATAYIN
    tuzatmasdan qoldirib, normalizatsiyani serializatsiya chegarasiga —
    ya'ni shu yerga — topshirgan.

    Xom qiymat JSON'ga berilsa UI meta qatorida `192.168.1.10/32`
    ko'rinardi (UI-SPEC §6.1) va admin uchun bu «bu nima?» degan savol
    bo'lardi — meta qator esa aynan diagnostika uchun bor.

    ⚠ SATRNI KESISH (`value.split("/")[0]`) EMAS: IPv6 da qiymat
      `fe80::1/128` bo'ladi va `ipaddress` moduli ikkala oilani ham bir
      xil qoida bilan yechadi. Parse qilib bo'lmaydigan qiymat XOM holda
      o'tadi: bu ustun kashfiyot yozadigan diagnostika va uni
      «tushunmadim» deb yo'qotish admindan aynan kerakli ma'lumotni olib
      qo'yardi.
    """
    if value is None:
        return None
    try:
        return str(ipaddress.ip_interface(value).ip)
    except ValueError:
        return value


def _read(camera: Camera, oxirgi_kadr: UUID | None = None,
          eskirgan: bool = False) -> CameraRead:
    """Qator -> javob modeli.

    ⚠ `stream_name` BU YERDA UMUMAN O'QILMAYDI (`schemas.py` dagi bo'lim
      izohi): u `CameraRead` da yo'q, ya'ni uni javobga qo'shish uchun
      avval sxemani o'zgartirish kerak va bu diffda ko'rinadi.
    """
    return CameraRead(
        id=camera.id,
        nvr_id=camera.nvr_id,
        channel_no=camera.channel_no,
        name=camera.name,
        name_overridden=camera.name_overridden,
        # ⛔ ESKIRGAN ALOQA «ONLAYN» BO'LIB KO'RINMAYDI (260829).
        #   `cameras.status` agent aytgan paytdagi holatda qotib
        #   qoladi; eskirish bayrog'i uni haqiqatga qaytaradi
        #   (`nvr_repo.CAMAGENT_STALE_SECONDS`).
        status=(CameraStatus.OFFLINE if eskirgan
                else CameraStatus(camera.status)),
        is_archived=camera.is_archived,
        has_substream=camera.has_substream,
        source_ip=normalize_source_ip(camera.source_ip),
        source_model=camera.source_model,
        last_seen_at=camera.last_seen_at,
        last_snapshot_id=oxirgi_kadr,
    )


def _describe(query: CameraQuery) -> dict[str, str]:
    """Filtr tavsifi — `audit_log.new_value.filters` uchun.

    FAQAT BERILGAN maydonlar (`stalls.py::_describe` naqshi): standart
    qiymatlarni ham yozish jurnalni «admin holatni tanladi» degan yolg'on
    ma'lumot bilan to'ldirardi.
    """
    described: dict[str, str] = {}
    if query.nvr_id is not None:
        described["nvr_id"] = str(query.nvr_id)
    if query.status is not None:
        described["status"] = str(query.status)
    if query.archived is not None:
        described["archived"] = str(query.archived).lower()
    return described


async def camera_or_404(repo: NvrRepository, camera_id: UUID) -> Camera:
    """Kamerani topadi yoki 404 beradi (arxivlanganlar HAM topiladi).

    ⚠ `include_archived=True` — bu yo'l ARXIVLANGAN kamerani ham
      ko'rishi SHART: `POST /{id}/restore` aynan o'sha qatorga tegadi va
      uni «yo'q» deb hisoblash arxivdan qaytarishni imkonsiz qilardi.
      Jonli ko'rish esa arxiv holatini O'ZI alohida tekshiradi
      (UI-SPEC §8.5).

    Repozitoriyda `get_camera()` YO'Q va u shu rejada QO'SHILMAYDI:
    ro'yxat so'rovi tenant predikatini allaqachon qo'llaydi va bir
    bozorda kameralar soni o'nlab (UI-SPEC §6.1: eng ko'pi 32). Yangi
    metod qo'shish repozitoriyning yuzasini kengaytirardi, foyda esa
    o'lchanmaydigan darajada kichik.
    """
    for row in await repo.list_cameras(include_archived=True):
        if row.id == camera_id:
            return row
    raise _not_found()


# ===========================================================================
# Reestr
# ===========================================================================


@router.get(
    "",
    response_model=CameraListResponse,
    dependencies=[Depends(require_permission(Permission.CAMERA_VIEW))],
)
async def list_cameras(
    principal: CameraViewerDep,
    intent: CameraReadIntentDep,
    session: TenantSessionDep,
    query: Annotated[CameraQuery, Query()],
) -> CameraListResponse:
    """Bozorning kameralari (`CAMERA_VIEW` + o'qish auditi).

    Tartib — `channel_no` bo'yicha o'sish (UI-SPEC §6.1). Standart holda
    ARXIVLANGANLAR KO'RINMAYDI: arxivlangan kanal admin uchun «yo'q»
    degani (`nvr_repo.list_cameras` docstringi).

    ⚠ `next_cursor` HAR DOIM `null` — va maydon baribir kontraktda
      TURADI. Bitta NVR eng ko'pi 32 kanal beradi va bir bozorda
      bir-ikkita NVR bo'ladi (UI-SPEC §6.1), ya'ni kursor mexanikasi
      bugun hech qanday muammoni hal qilmasdi. Maydonni OLIB TASHLASH
      esa chegara oshganda klient kontraktini buzardi —
      `StallListResponse` bilan bir xil shakl saqlanadi.
    """
    repo = NvrRepository(session, _market_id(principal))
    rows = await repo.list_cameras(query.nvr_id, include_archived=bool(query.archived))

    # ⚠ FILTR HISOBLANGAN HOLATGA QARAYDI, ustunga emas: aks holda
    #   «Ulanmagan» filtri agent to'xtagan bozorda BO'SH ro'yxat
    #   qaytarardi — ya'ni operator muammoni aynan uni qidirayotgan
    #   joyda topa olmasdi.
    kontekst = await repo.wall_context()
    javob = [_read(row, *kontekst.get(row.id, (None, False))) for row in rows]
    if query.status is not None:
        javob = [c for c in javob if c.status == query.status]

    intent.filters = _describe(query)
    intent.result_count = len(javob)

    return CameraListResponse(items=javob)


@router.patch(
    "/{camera_id}",
    response_model=CameraRead,
    dependencies=[Depends(require_permission(Permission.CAMERA_MANAGE))],
)
async def update_camera(
    camera_id: UUID,
    payload: CameraUpdateRequest,
    principal: CameraManagerDep,
    session: TenantSessionDep,
) -> CameraRead:
    """Nomni o'zgartiradi yoki NVR nomiga qaytaradi (`CAMERA_MANAGE`, SC#2).

    Ikkita ALOHIDA amal, bitta marshrut (`exclude_unset=True` bilan
    ajratiladi)::

        {"name": "Sabzavot qatori"}   -> nom + `name_overridden = true`
        {"name_overridden": false}    -> keyingi skanda nom NVR'dan olinadi

    ⚠ `name_overridden: true` YOLG'IZ yuborilsa 422: bayroq nomning
      HOSILASI va uni mustaqil qo'yish `rename_camera` ning «ikkala
      ustun BIR operatorda» kafolatini chetlab o'tardi (oradagi skan
      nomni bosib ketardi — aynan SC#2 ning buzilishi).
    """
    fields = payload.model_dump(exclude_unset=True)
    if not fields:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=_EMPTY_UPDATE,
        )

    repo = NvrRepository(session, _market_id(principal))
    await camera_or_404(repo, camera_id)

    name = fields.get("name")
    if name is not None:
        await repo.rename_camera(camera_id, name)
    elif fields.get("name_overridden") is False:
        await repo.reset_camera_name(camera_id)
    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=_OVERRIDE_NEEDS_NAME,
        )

    log.info("camera_updated", camera_id=str(camera_id), fields=sorted(fields))
    return _read(await camera_or_404(repo, camera_id))


@router.post(
    "/{camera_id}/archive",
    response_model=CameraRead,
    dependencies=[Depends(require_permission(Permission.CAMERA_MANAGE))],
)
async def archive_camera(
    camera_id: UUID,
    principal: CameraManagerDep,
    session: TenantSessionDep,
) -> CameraRead:
    """Kamerani ARXIVLAYDI — qator QOLADI (D-10, `CAMERA_MANAGE`).

    `SELECT count(*) FROM cameras` bu chaqiruvdan keyin KAMAYMAYDI va bu
    testda o'lchanadi. Arxivlangan kanal qayta skanda TIKLANMAYDI.
    """
    repo = NvrRepository(session, _market_id(principal))
    await camera_or_404(repo, camera_id)
    await repo.archive_camera(camera_id)
    log.info("camera_archived", camera_id=str(camera_id))
    return _read(await camera_or_404(repo, camera_id))


@router.post(
    "/{camera_id}/restore",
    response_model=CameraRead,
    dependencies=[Depends(require_permission(Permission.CAMERA_MANAGE))],
)
async def restore_camera(
    camera_id: UUID,
    principal: CameraManagerDep,
    session: TenantSessionDep,
) -> CameraRead:
    """Arxivdan qaytaradi (UI-SPEC §9.3 — tasdiqsiz, zararsiz amal).

    Bu YAGONA qaytish yo'li: qayta skan arxivlangan kanalni tiklamaydi.
    Usiz arxivlash amalda qaytarib bo'lmaydigan bo'lardi va o'shanda
    UI-SPEC §9.2 bo'yicha 2-darajali (nom yozib) tasdiq talab qilinardi.
    """
    repo = NvrRepository(session, _market_id(principal))
    await camera_or_404(repo, camera_id)
    await repo.restore_camera(camera_id)
    log.info("camera_restored", camera_id=str(camera_id))
    return _read(await camera_or_404(repo, camera_id))


# ===========================================================================
# Jonli ko'rish chiptasi (SC#6, D-08, D-11)
# ===========================================================================


_DEFAULT_RTSP_PORT = 554
"""Kashfiyot RTSP portini topa olmagan holatdagi zaxira (03-04, A.2).

⚠ TAXMIN QILINGANI QATORDA BELGILANADI (`nvr_devices.rtsp_port_assumed`)
  va u jonli ko'rish yiqilganda BIRINCHI tekshiriladigan gumondor
  (UI-SPEC §4.6). Bu yerda faqat `None` holati yopiladi: portsiz URL
  umuman qurib bo'lmasdi va admin «jonli ko'rish ishlamayapti» degan
  sababsiz xato olardi.
"""

_LIVE_UNAVAILABLE = "live_view_unavailable"


def _live_unavailable() -> HTTPException:
    """**503**, 500 EMAS — jonli ko'rish hozir ishlamayapti (D-02).

    ⚠ REKVIZIT NOSOZLIGI UCHUN YANGI XATO KODI KIRITILMAYDI. Admin uchun
      sabab bir xil («jonli ko'rish hozir ishlamayapti») va UI bir xil
      «Qayta urinish» affordansini beradi. Alohida kod faqat NVR hisobiga
      urinish yuborilganda ma'noli bo'lardi — bu yo'l esa NVR'ga UMUMAN
      chiqmaydi, ya'ni §4.4 qulfi bu yerga qo'llanmaydi (UI-SPEC §8.5).
    """
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=_LIVE_UNAVAILABLE,
    )


async def _ensure_stream(
    state: object,
    camera: Camera,
    device: NvrDevice,
    repo: NvrRepository,
    viewer: str = "",
    duration_s: int = STREAM_DURATION_S,
) -> None:
    """Oqimni go2rtc'da LAZY ro'yxatga oladi — REKVIZIT BILAN (RESEARCH D.13).

    Ro'yxatga olish AYNAN shu yerda — startup'da EMAS. Sabab ikkita:
    startup'da 25 ta so'rov ilovaning ko'tarilishini NVR ning holatiga
    bog'lab qo'yardi, va go2rtc qayta ishga tushganda ro'yxat baribir
    yo'qolardi (`PUT /api/streams` XOTIRAGA yozadi). Lazy yo'lda DB
    YAGONA HAQIQAT MANBAI bo'lib qoladi.

    =======================================================================
    ⚠⚠ `decrypt_nvr_password` NING ILOVADAGI IKKINCHI CHAQIRUV JOYI.

    Birinchisi — `jobs/discovery.py` (ISAPI kashfiyoti). `03-RESEARCH.md`
    D.13 esa aynan shu ikkinchisini talab qiladi: «parol URL'ga hech
    qachon kirmaydi — u alohida, shifrlangan holda turadi va FAQAT go2rtc
    konfiguratsiyasi hosil qilinayotganda ochiladi».

    Ketma-ketlik ATAYIN shu tartibda:

        rtsp_url()                 -> rekvizitSIZ manzil (saqlanadi, jurnalga
                                      tushadi, T-03-24 ostida)
        repo.get_credential()      -> Fernet TOKENI
        decrypt_nvr_password()     -> ochiq matn, FAQAT shu tanada
        authenticated_rtsp_source()-> `SecretStr`, foizli kodlangan
        client.ensure_stream()     -> allow-list + `PUT`

    Ochiq matn parol HECH QAYERGA yozilmaydi va hech qanday oraliq
    strukturaga tushmaydi — u to'g'ridan-to'g'ri sir tashuvchiga o'tadi.
    =======================================================================

    ⚠ `src` FOYDALANUVCHI KIRITMASIDAN QURILMAYDI: u `rtsp_url()` ning
      chiqishi + bazadagi rekvizit. Allow-list (`assert_safe_go2rtc_src`)
      baribir qo'llanadi — u `ensure_stream` ichida, tarmoqqa chiqishdan
      OLDIN, ochilgan qiymat ustida.

    Raises:
        HTTPException: rekvizit qatori yo'q yoki uni joriy kalit bilan
            ochib bo'lmasa — **503** (`_live_unavailable()`).
    """
    settings: Settings = state.settings  # type: ignore[attr-defined]

    if is_camagent_device(device):
        # ⛔ CAMAGENT YO'LI (260829) — sabab `services/camagent_live.py`
        #    boshida. Qisqasi: `device.host` bozorning ICHKI manzili va
        #    serverdan unga yo'l yo'q; oqimni agent O'ZI serverga uzatadi.
        #
        # ⚠ REKVIZIT O'QILMAYDI: parol agentda qoladi va serverga hech
        #   qachon kelmaydi. Quyidagi `get_credential`/`decrypt` zanjiri
        #   bu yo'lda 503 berardi — qator umuman yaratilmaydi.
        try:
            manba, _ = await open_camagent_stream(
                settings.camagent_gateway_url,
                settings.camagent_service_token.get_secret_value(),
                market_id=repo.market_id,
                camera_serial=device.serial_number or "",
                channel_no=camera.channel_no,
                # ⚠ KO'RUVCHI NOMI — `sbozor:{user_id}`. Ikki maqsad:
                #   (1) gateway jurnalida KIM ochgani qoladi (11-bo'lim:
                #       «kim, qachon, qaysi kamerani ochgani yoziladi»);
                #   (2) gateway o'sha odamning eski oqimini yopa oladi —
                #       dialog yopilganini bilmaydi va usiz agentdagi
                #       kanal chegarasi to'lib qolardi.
                viewer=viewer or "sbozor",
                duration_s=duration_s,
            )
        except CamAgentLiveError as exc:
            # `Go2rtcError` ga aylantiramiz: chaqiruvchi uni allaqachon
            # 503 ga o'giradi va UI «Qayta urinish» beradi. Yangi xato
            # turi UI'da yangi holat talab qilardi — sabab esa operator
            # uchun bir xil: «jonli ko'rish hozir ishlamayapti».
            raise Go2rtcError(type(exc).__name__) from exc
        # ⚠ `SecretStr` — `ensure_stream` NING SHARTNOMASI. Bu yo'lda
        #   manzilda parol YO'Q (o'qish MediaMTX'da ochiq), lekin tur
        #   bir xil qolishi kerak: `go2rtc.py` uni `get_secret_value()`
        #   bilan ochadi va boshqa turda ilova 500 beradi.
        async with Go2rtcClient(settings.go2rtc_url) as client:
            await client.ensure_stream(camera.stream_name, SecretStr(manba))
        return

    url = rtsp_url(
        device.host,
        device.rtsp_port if device.rtsp_port is not None else _DEFAULT_RTSP_PORT,
        camera.channel_no,
        # SUB-OQIM AFZAL: jonli ko'rish uchun to'liq HD oqim NVR ning
        # bitreyt byudjetini yeydi (RESEARCH A.5) va ekrandagi kichik
        # oynada farq ko'rinmaydi. `has_substream=False` bo'lgan kanalda
        # asosiy oqimga tushiladi — kashfiyot buni o'lchagan.
        substream=camera.has_substream,
    )

    token = await repo.get_credential(camera.nvr_id)
    if token is None:
        # ⚠ JURNALGA NA TOKEN, NA UNING BO'LAGI TUSHADI (`jobs/discovery.py`
        #   dagi izohning aynan takrori). Xabar operatorga QAYERGA
        #   qarashni aytadi, qiymatni emas.
        log.warning(
            "live_view_credential_missing",
            camera_id=str(camera.id),
            nvr_id=str(camera.nvr_id),
        )
        raise _live_unavailable()

    try:
        password = decrypt_nvr_password(token)
    except InvalidToken:
        log.error(
            "live_view_credential_decrypt_failed",
            camera_id=str(camera.id),
            nvr_id=str(camera.nvr_id),
        )
        # `from None`: `InvalidToken` ning o'zi bo'sh, LEKIN sabab zanjirini
        # ochiq qoldirish keyingi tahrirlovchiga «token bilan birga
        # ko'tarish mumkin» degan namuna berardi.
        raise _live_unavailable() from None

    source = authenticated_rtsp_source(url, device.username, password)

    async with Go2rtcClient(settings.go2rtc_url) as client:
        await client.ensure_stream(camera.stream_name, source)


@router.post(
    "/{camera_id}/live-token",
    response_model=LiveTokenResponse,
    dependencies=[Depends(require_permission(Permission.CAMERA_VIEW))],
)
async def issue_live_token_for_camera(
    camera_id: UUID,
    request: Request,
    principal: CameraViewerDep,
    intent: LiveViewIntentDep,
    session: TenantSessionDep,
    preview: Annotated[bool, Query()] = False,
) -> LiveTokenResponse:
    """Qisqa muddatli ULANISH CHIPTASI (`CAMERA_VIEW` + `live_view` auditi).

    ⚠ HUQUQ DEKORATORDA (fayl boshidagi izoh): 403 olgan so'rov bu
      tanaga YETIB KELMAYDI va jurnalda «ko'rdi» degan YOLG'ON DALIL
      qolmaydi. O'lchov — `test_live_view.py::
      test_forbidden_live_token_is_not_audited`.

    ⚠ ARXIVLANGAN KAMERA UCHUN 404 (UI-SPEC §8.5): arxivlangan kanalning
      oqimi go2rtc'da ro'yxatga olinmaydi (§6.6), ya'ni chipta berish
      ishlamaydigan URL qaytarardi va UI xatoni transport nosozligi deb
      ko'rsatardi. To'g'ri matn — «bu kamera topilmadi, u arxivlangan
      bo'lishi mumkin».

    ⚠ JAVOBDA `stream_name` OCHIQ KO'RINMAYDI (UI-SPEC §8.7) — u faqat
      opaque `url` ning ichida.
    """
    market_id = _market_id(principal)
    repo = NvrRepository(session, market_id)
    camera = await camera_or_404(repo, camera_id)
    if camera.is_archived:
        raise _not_found()

    device = await repo.get_device(camera.nvr_id)
    if device is None:  # pragma: no cover - composite FK buni imkonsiz qiladi
        raise _not_found()

    try:
        # ⛔ KO'RUVCHI NOMIGA KAMERA HAM KIRADI (260829). Devor 16
        #   katakchani BIR VAQTDA ochadi; nom faqat foydalanuvchidan
        #   iborat bo'lsa gateway ularni BIR seans deb hisoblab, har
        #   yangisi oldingisini yopardi va devorda bitta katakcha
        #   jonlanardi.
        #
        # ⚠ Dialog xulqi saqlanadi: AYNI kamerani qayta ochish eski
        #   seansni baribir yopadi — nom o'sha bo'ladi.
        await _ensure_stream(
            request.app.state, camera, device, repo,
            viewer=f"sbozor:{principal.user_id}:{camera_id}",
            # Devor katakchasi 10 soniyadan keyin oxirgi kadrga
            # qaytadi — oqim shundan uzoq yashashi kerak emas.
            duration_s=PREVIEW_DURATION_S if preview else STREAM_DURATION_S,
        )
    except Go2rtcError as exc:
        # ⚠ 503, 500 EMAS: bu bizning kodimizdagi xato emas, TASHQI
        #   servisning holati. UI uni «jonli ko'rish hozir ishlamayapti»
        #   deb ko'rsatadi va «Qayta urinish» affordansini beradi (D-02)
        #   — bu yo'l NVR hisobiga urinish YUBORMAYDI, ya'ni §4.4 qulfi
        #   bu yerga qo'llanmaydi (UI-SPEC §8.5).
        #
        # ⚠⚠ `error=` MAYDONIGA ISTISNO SINFINING NOMI YOZILADI, `str(exc)`
        #   EMAS (T-03-87). `_ensure_stream` endi go2rtc'ga REKVIZITLI
        #   manba yuboradi, ya'ni istisno matni printsipial jihatdan sirni
        #   jurnalga olib chiqadigan kanal. `go2rtc.py::_failure()` matnni
        #   allaqachon tozalaydi — bu esa IKKINCHI qatlam va u
        #   birinchisining kelajakdagi regressiyasidan mustaqil.
        log.warning("go2rtc_unavailable", camera_id=str(camera_id), error=type(exc).__name__)
        raise _live_unavailable() from exc

    settings: Settings = request.app.state.settings
    token = issue_live_token(
        camera_id=camera_id,
        market_id=market_id,
        user_id=principal.user_id,
        settings=settings,
    )

    intent.filters = {"camera_id": str(camera_id)}
    intent.result_count = 1

    log.info("live_token_issued", camera_id=str(camera_id))
    return LiveTokenResponse(
        url=live_view_url(camera.stream_name, token),
        expires_in=LIVE_TOKEN_MAX_TTL_SECONDS,
        transport_hint=TRANSPORT_HINT,
    )
