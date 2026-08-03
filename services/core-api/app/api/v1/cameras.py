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
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sbozor_core.enums import CameraStatus

from app.deps import Principal, TenantSessionDep, require_permission
from app.repositories.nvr_repo import NvrRepository
from app.schemas import CameraListResponse, CameraQuery, CameraRead, CameraUpdateRequest
from app.security.audit import TABLE_CAMERAS, AuditReadIntent, audit_read
from app.security.rbac import Permission

if TYPE_CHECKING:
    from sbozor_core.models import Camera

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


def _read(camera: Camera) -> CameraRead:
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
        status=CameraStatus(camera.status),
        is_archived=camera.is_archived,
        has_substream=camera.has_substream,
        source_ip=normalize_source_ip(camera.source_ip),
        source_model=camera.source_model,
        last_seen_at=camera.last_seen_at,
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
    if query.status is not None:
        rows = [row for row in rows if row.status == str(query.status)]

    intent.filters = _describe(query)
    intent.result_count = len(rows)

    return CameraListResponse(items=[_read(row) for row in rows])


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
