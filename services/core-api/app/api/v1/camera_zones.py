"""Kamera zonalari (AI-01) — kameralarning DAVOMI, yangi resurs sinfi EMAS.

=============================================================================
O'QISH VA YOZISH HUQUQLARI ATAYIN AJRATILGAN (D-07).

`GET` — `CAMERA_VIEW`, yozuv — `CAMERA_MANAGE`. Direktorda birinchisi BOR,
ikkinchisi YO'Q: u zonalarni ko'radi (bandlik hisobotining rasm-dalili
zonalarsiz ma'nosiz), lekin ularni o'zgartira olmaydi. Bitta huquq
ikkalasini ham qamragan bo'lsa, «direktor zonalarni ko'rsin» so'rovi
jimgina «direktor bandlik o'lchanadigan maydonni qayta chizsin» ga
aylanardi — ya'ni hisobotni o'qiydigan odam hisobot RAQAMINI o'zgartira
olardi.

⛔ YANGI `Permission` QO'SHILMAYDI VA BU O'YLANGAN QAROR.

`camera_zones` — kameraning ustiga chizilgan kontur; u kamerasiz mavjud
emas va kamera bilan birga o'chadi (kompozit FK). Alohida
`ZONE_VIEW`/`ZONE_MANAGE` juftligi RBAC matritsasiga ikki qator
qo'shardi, `frontend/src/lib/rbac.ts` ko'zgusini QO'LDA sinxronlashni
talab qilardi va birorta yangi mahsulot qarorini ifodalamasdi: hech
qanday rol «kamerani boshqaradi, lekin zonalarini emas» holatida
bo'lishi kutilmaydi.
=============================================================================

CROSS-TENANT JAVOB — HAR DOIM 404 (T-05-25), 403 EMAS.

Boshqa bozorning `camera_id` yoki `camera_zone_id` si bilan kelgan har
qanday amal RLS ostida 0 qator topadi va «topilmadi» javobini oladi. 403
QAYTARILMAYDI: javobning O'ZI «bunday zona bor, lekin sizniki emas»
degan ma'lumotni oshkor qilardi va hujumchi mavjud identifikatorlarni
javob kodi bo'yicha sanab chiqa olardi.

⚠ BO'SH RO'YXAT 404 NING O'RNINI BOSA OLMAYDI. Begona `camera_id` uchun
  zonalar so'rovi tabiiy ravishda 0 qator beradi va u «zonasi yo'q
  kamera» dan farq qilmaydi — ya'ni admin o'z kamerasini zonasiz deb
  o'ylab, qaytadan chizishga tushardi. Shuning uchun kamera mavjudligi
  ALOHIDA tekshiriladi (`camera_exists()`).

-----------------------------------------------------------------------------
`market_id` HECH QACHON SO'ROV TANASIDAN OLINMAYDI (T-05-24). U faqat
`_market_id(principal)` dan keladi va `CameraZoneRequest` /
`CameraZoneWrite` da bunday maydon UMUMAN e'lon qilinmagan
(`app/schemas.py` bo'lim izohi). E'lon qilinmagan maydon uchun
«e'tiborsiz qoldirish» kodi ham kerak emas — filtrni unutish mumkin,
mavjud bo'lmagan maydonni esa yo'q.
-----------------------------------------------------------------------------
⚠ O'QISH AUDITI E'LON QILINMAYDI va bu `stalls.py:348-369` (`GET /map`)
  bilan AYNAN bir xil qaror. `camera_zones` da shaxsiy ma'lumot YO'Q:
  javobda faqat identifikatorlar, rasta raqami va koordinatalar bor —
  na sotuvchi ismi, na telefoni. Zona muharriri har surish-tortishda
  ro'yxatni qayta so'raydi, ya'ni auditni bu yerga yopishtirish jurnalni
  SHOVQIN bilan to'ldirib, haqiqiy o'qish hodisalarini ko'mib yuborardi
  (`security/audit.py:240-245` da rad etilgan «blanket middleware»
  mulohazasining aynan o'zi).

  Jadvalning O'ZGARISHI esa auditda: `camera_zones` `AUDITED_TABLES` da
  va DB-trigger har `INSERT`/`UPDATE` ni yozadi. Ya'ni «kim poligonni
  siljitdi?» savoli javobsiz qolmaydi — o'zgarish audit qilinadi,
  o'qish esa yo'q.

  ⚠ BU DA'VO XULQ BILAN O'LCHANADI:
    `test_camera_zones_api.py::test_get_writes_no_read_audit_row`.
-----------------------------------------------------------------------------

MARSHRUT TARTIBI: `GET /coverage` `DELETE /{camera_zone_id}` DAN OLDIN.

Bugungi holatda ular metod bo'yicha ajraladi, ya'ni to'qnashuv YO'Q.
Tartib shunga qaramay `stalls.py:3-11` qoidasiga muvofiq saqlanadi:
`/coverage` uchun `DELETE` yoki `PATCH` qo'shilgan kuni statik segment
`{camera_zone_id}` shablonidan KEYIN turgan bo'lsa, so'rov shablonga
tushardi, `"coverage"` esa UUID emas — natijada foydalanuvchi 422 olardi
va ikkala marshrut ham to'g'ri yozilgan bo'lib turardi.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.exc import IntegrityError

from app.deps import Principal, SettingsDep, TenantSessionDep, require_permission
from app.repositories.camera_zone_repo import (
    CameraZoneRepository,
    CameraZoneRow,
    ZoneWrite,
    zones_needing_review,
)
from app.repositories.stall_repo import sqlstate_of
from app.schemas import (
    CameraZoneItem,
    CameraZoneListResponse,
    CameraZoneRequest,
    ZoneCoverageResponse,
)
from app.security.rbac import Permission
from app.services.occupancy_errors import ZONE_LIMIT_REACHED, ZONE_STALL_ALREADY_COVERED
from app.services.zone_geometry import validate_polygon

# `UUID` `if TYPE_CHECKING:` ostiga QO'YILMAYDI: FastAPI yo'l
# parametrlarining annotatsiyasini ISH PAYTIDA o'qiydi (`get_type_hints`),
# ya'ni import faqat tip tekshiruvida bo'lsa marshrut `NameError` bilan
# yiqilardi (`zones.py:44-47` dagi bilan aynan bir xil sabab).
log = structlog.get_logger(__name__)

router = APIRouter(tags=["camera-zones"])

CameraViewerDep = Annotated[Principal, Depends(require_permission(Permission.CAMERA_VIEW))]
CameraManagerDep = Annotated[Principal, Depends(require_permission(Permission.CAMERA_MANAGE))]

CameraIdDep = Annotated[UUID, Query(description="Zonalar qaysi kameraga tegishli")]
"""`camera_id` — QUERY parametri, tananing maydoni EMAS.

U RESURSNI aniqlaydi, ya'ni yo'lning ma'nosiy qismi. Tanada bo'lganda
bitta `PUT` ikki xil kameraga yozish niyatini ifodalay olardi (query'da
bittasi, tanada boshqasi) va qaysi biri ustun ekani kodni o'qimasdan
ko'rinmasdi.
"""

_NOT_FOUND = "not_found"

UNIQUE_VIOLATION = "23505"
"""Bir vaqtda ikkinchi saqlash — `uq_camera_zones_market_id_camera_id_stall_id_version`.

Poyga DB'ga TOPSHIRILADI: «avval tekshir, keyin yoz» ikki so'rovni bir
xil bo'sh holatni ko'rgan holda o'tkazib yuborardi va ikkalasi ham bir
xil `version` yozardi (`camera_zone_repo` modul docstringi).
"""

FK_VIOLATION = "23503"
"""Begona (yoki mavjud bo'lmagan) `stall_id` — kompozit FK rad etadi.

Javob **404**, 403 EMAS: 403 o'sha rastaning MAVJUDLIGINI tasdiqlardi
(`stalls.py::_stall_conflict()` bilan bir xil qaror).
"""

CHECK_VIOLATION = "23514"
"""DB `CHECK` i ilova darvozasidan o'tib ketgan poligonni rad etdi.

⚠ BU TARMOQ TO'G'RI KODDA HECH QACHON BAJARILMAYDI: `validate_polygon()`
  DB `CHECK` laridan QAT'IYROQ (u kesishuvni ham, nol uzunlikdagi
  qirrani ham ko'radi) va `zone_max_vertices` `POLYGON_MAX_VERTICES`
  bilan chegaralangan. Ya'ni bu satrning bajarilishi KODDA xato
  borligining belgisi (`live_source.py::CREDENTIAL_INJECTION` bilan bir
  xil sinf) va uni jimgina 500 ga aylantirish sababni yo'qotardi.
"""


def _market_id(principal: Principal) -> UUID:
    """Tanlangan bozor (`zones.py` / `stalls.py` dagi jufti bilan aynan bir xil)."""
    if principal.market_id is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="market_not_selected",
        )
    return principal.market_id


def _not_found() -> HTTPException:
    """Cross-tenant va mavjud bo'lmagan obyekt uchun BIR XIL javob (T-05-25)."""
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_NOT_FOUND)


def _conflict(code: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=code)


def _unprocessable(code: str) -> HTTPException:
    """Poligon qoidasi buzildi — 422 + NOMLANGAN kod.

    ⚠ 422 NI PYDANTIC GA QOLDIRIB BO'LMASDI. Chegaralarni sxemada
      e'lon qilish (`min_length=3`) ham 422 berardi, lekin uning
      `detail` i Pydantic ning ichki tuzilmasi bo'lardi — frontend
      `zone_polygon_too_few_points` matnini KO'RSATA OLMASDI va admin
      «Kutilmagan xato» ni o'qirdi. Kod `app/schemas.py::ERROR_CODES`
      allowlist'ida, ya'ni u uch tilda matnga aylanadi.
    """
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=code)


def _integrity(exc: IntegrityError) -> HTTPException:
    """`IntegrityError` -> aniq `detail` kodi.

    Xom xato matni javobga HECH QACHON tushmaydi (ASVS V7): u jadval va
    konstrayt nomlarini oshkor qilardi.

    Noma'lum SQLSTATE QAYTA KO'TARILADI — `main.py` dagi global handler
    uni ko'radi. Uni «har ehtimolga qarshi» 409 ga aylantirish yangi
    konstraytni jimgina noto'g'ri xabar bilan yashirardi
    (`zones.py::_conflict()` da o'rnatilgan qoida).
    """
    state = sqlstate_of(exc)
    if state == UNIQUE_VIOLATION:
        log.info("camera_zone_version_conflict", sqlstate=state)
        return _conflict(ZONE_STALL_ALREADY_COVERED)
    if state == FK_VIOLATION:
        log.info("camera_zone_reference_not_found", sqlstate=state)
        return _not_found()
    if state == CHECK_VIOLATION:
        # Ilova darvozasi DB nikidan qat'iyroq bo'lishi kerak edi —
        # bu yerga yetib kelish KODDAGI xato (konstanta docstringi).
        log.error("camera_zone_check_violation", sqlstate=state)
        return _unprocessable("zone_polygon_out_of_range")
    raise exc


def _item(row: CameraZoneRow, *, needs_review: bool) -> CameraZoneItem:
    return CameraZoneItem(
        id=row.id,
        camera_id=row.camera_id,
        stall_id=row.stall_id,
        stall_code=row.stall_code,
        version=row.version,
        polygon=[(float(x), float(y)) for x, y in row.polygon],
        source_width=row.source_width,
        source_height=row.source_height,
        needs_review=needs_review,
    )


@router.get("/coverage", response_model=ZoneCoverageResponse)
async def zone_coverage(
    principal: CameraViewerDep,
    session: TenantSessionDep,
) -> ZoneCoverageResponse:
    """Qamrov uchligi — D-22 (`CAMERA_VIEW`).

    ⚠ BU MARSHRUT `DELETE /{camera_zone_id}` DAN OLDIN e'lon qilingan —
      sabab modul docstringida.

    Uchala son ham HAR DOIM qaytadi, nol bo'lganda ham: birorta zona
    chizilmagan bozorda karta UMUMAN chiqmasligi «hammasi joyida»
    degan yolg'on xulosa berardi (UI-SPEC §6.9).
    """
    coverage = await CameraZoneRepository(session, _market_id(principal)).coverage()
    return ZoneCoverageResponse(
        covered=coverage.covered,
        uncovered=coverage.uncovered,
        cameras_without_zones=coverage.cameras_without_zones,
    )


@router.get("", response_model=CameraZoneListResponse)
async def list_camera_zones(
    camera_id: CameraIdDep,
    principal: CameraViewerDep,
    session: TenantSessionDep,
    settings: SettingsDep,
) -> CameraZoneListResponse:
    """Kameraning FAOL zonalari + joriy kadr o'lchami (`CAMERA_VIEW`).

    Eskirgan versiyalar javobda YO'Q (D-07: ular jadvalda qoladi, lekin
    muharrir faqat amaldagi konturni chizadi).

    `needs_review` — HOSILA: zonaning `source_width`/`source_height` i
    joriy kadrnikidan farq qilsa `true` (§6.8). Kamerada hali yaroqli
    kadr bo'lmasa BARCHA zonada `false` — solishtiradigan narsa yo'q,
    ya'ni «farq qiladi» degan da'vo asossiz bo'lardi.

    ⛔ AVTOMATIK TO'G'RILASH QILINMAYDI: javob faqat FAKTNI beradi.
    """
    repo = CameraZoneRepository(session, _market_id(principal))
    if not await repo.camera_exists(camera_id):
        raise _not_found()

    rows = await repo.list_for_camera(camera_id)
    frame = await repo.latest_frame_size(camera_id)

    flagged = (
        zones_needing_review(rows, frame[0], frame[1], tolerance=settings.zone_aspect_tolerance)
        if frame is not None
        else frozenset()
    )

    return CameraZoneListResponse(
        items=[_item(row, needs_review=row.id in flagged) for row in rows],
        frame_width=None if frame is None else frame[0],
        frame_height=None if frame is None else frame[1],
    )


@router.put("", response_model=CameraZoneListResponse)
async def replace_camera_zones(
    payload: CameraZoneRequest,
    camera_id: CameraIdDep,
    principal: CameraManagerDep,
    session: TenantSessionDep,
    settings: SettingsDep,
) -> CameraZoneListResponse:
    """Kameraning zonalarini ATOMAR almashtiradi (`CAMERA_MANAGE`, D-07).

    Tekshiruvlar ARZONDAN QIMMATGA va ular so'rovni BUTUNLAY rad etadi —
    qisman saqlash YO'Q (UI-SPEC §6.6):

        1. kamera shu bozornikimi          -> 404
        2. zonalar soni chegarada          -> 409 `zone_limit_reached`
        3. bitta rasta ikki marta          -> 409 `zone_stall_already_covered`
        4. har poligon V5 qoidalarida      -> 422 + geometriya kodi

    ⚠ UCHINCHI TEKSHIRUV DB KONSTRAYTI BILAN ALMASHTIRIB BO'LMAYDI.
      `uq_camera_zones_market_id_camera_id_stall_id_version` bir xil
      rastaning ikki yozuvini RAD ETMASDI: ikkalasi ham YANGI qator
      bo'lib, ikkinchisi birinchisidan keyingi `version` ni olardi — ya'ni
      bir rasta bitta kamerada IKKI faol konturga ega bo'lardi va ular
      bir kadrga ikki qarama-qarshi verdikt berardi. Qaysi biri hisobga
      kirishini esa aniqlab bo'lmasdi.

      ⛔ Bu taqiq FAQAT BIR KAMERA ICHIDA. Bir rasta bir necha KAMERADA
         bo'lishi NORMAL va u D-20 ning butun asosi («birortasi band desa —
         rasta band»).

    Javob `GET` bilan AYNAN bir xil shaklda: klient saqlashdan keyin
    qayta so'rov yubormaydi va ikki yo'l bir xil natijani beradi
    (`stalls.py::_detail_or_404()` da o'rnatilgan qoida).
    """
    repo = CameraZoneRepository(session, _market_id(principal))
    if not await repo.camera_exists(camera_id):
        raise _not_found()

    if len(payload.zones) > settings.zone_max_per_camera:
        log.info(
            "zone_limit_reached",
            requested=len(payload.zones),
            limit=settings.zone_max_per_camera,
        )
        raise _conflict(ZONE_LIMIT_REACHED)

    seen: set[UUID] = set()
    writes: list[ZoneWrite] = []
    for zone in payload.zones:
        if zone.stall_id in seen:
            raise _conflict(ZONE_STALL_ALREADY_COVERED)
        seen.add(zone.stall_id)

        error = validate_polygon(
            zone.polygon,
            min_vertices=3,
            max_vertices=settings.zone_max_vertices,
        )
        if error is not None:
            log.info("zone_polygon_rejected", error_code=error, stall_id=str(zone.stall_id))
            raise _unprocessable(error)

        writes.append(
            ZoneWrite(
                stall_id=zone.stall_id,
                polygon=[list(point) for point in zone.polygon],
                source_width=zone.source_width,
                source_height=zone.source_height,
            )
        )

    try:
        outcome = await repo.replace_for_camera(camera_id, writes)
    except IntegrityError as exc:
        raise _integrity(exc) from exc

    log.info(
        "camera_zones_replaced",
        camera_id=str(camera_id),
        created=outcome.created,
        versioned=outcome.versioned,
        deactivated=outcome.deactivated,
        unchanged=outcome.unchanged,
    )
    return await list_camera_zones(
        camera_id=camera_id, principal=principal, session=session, settings=settings
    )


@router.delete(
    "/{camera_zone_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def delete_camera_zone(
    camera_zone_id: UUID,
    principal: CameraManagerDep,
    session: TenantSessionDep,
) -> Response:
    """Zonani ESKIRGAN deb belgilaydi (`CAMERA_MANAGE`).

    ⛔ QATTIQ `DELETE` YO'Q: `occupancy_events` `(market_id,
       camera_zone_id)` ga kompozit FK bilan tayanadi, ya'ni qatorni
       o'chirish o'tmishdagi BUTUN dalil zanjirini uzardi — «bu rasta
       band edi» hukmining qaysi kontur bo'yicha o'lchangani javobsiz
       qolardi. `cameras.is_archived` (D-10) bilan aynan bir xil qaror.

    Begona bozorning zonasi ham, mavjud bo'lmagan `id` ham, ALLAQACHON
    eskirgan zona ham BIR XIL 404 oladi. Uchalasini ajratish javob kodi
    orqali identifikator sanab chiqish yo'lini ochardi (T-05-25).
    """
    deleted = await CameraZoneRepository(session, _market_id(principal)).deactivate(camera_zone_id)
    if not deleted:
        raise _not_found()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
