"""Zona reestri (D-03) — YASSI ro'yxat, ierarxiya YO'Q.

=============================================================================
O'QISH VA YOZISH HUQUQLARI ATAYIN AJRATILGAN (D-07).

`GET` — `MARKET_DATA_VIEW`, qolgan hammasi — `STALL_MANAGE`. Direktorda
birinchisi BOR, ikkinchisi YO'Q: u reestrni ko'radi (hisobotlari shunsiz
ma'nosiz), lekin o'zgartira olmaydi. Bitta `STALL_MANAGE` huquqi ikkalasini
ham qamragan bo'lsa, "direktor ko'rsin" so'rovi jimgina "direktor
o'zgartirsin" ga aylanardi.

CROSS-TENANT JAVOB — HAR DOIM 404 (T-02-55). Boshqa bozorning `zone_id` si
bilan kelgan har qanday amal RLS ostida 0 qator topadi va "topilmadi"
javobini oladi. 403 QAYTARILMAYDI: javobning O'ZI "bunday zona bor, lekin
sizniki emas" degan ma'lumotni oshkor qilardi va hujumchi mavjud ID'larni
javob kodi bo'yicha sanab chiqa olardi.
=============================================================================

`market_id` HECH QACHON SO'ROV TANASIDAN OLINMAYDI (T-02-54). U faqat
`_market_id(principal)` dan keladi va `ZoneRequest` da bunday maydon
umuman e'lon qilinmagan (`app/schemas.py` bo'lim izohi).

ZONANI O'CHIRISH IKKI QAVATLI: ilova avval bog'liq rasta borligini
tekshiradi (foydalanuvchi tushunarli 409 olishi uchun), DB esa composite
FK bilan buni ATOMIK kafolatlaydi. Tekshiruv bilan `DELETE` orasidagi
poyga holati ham 409 ga aylanadi — xom konstrayt xatosi javobga chiqmaydi
(T-02-58).
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.exc import IntegrityError

from app.deps import Principal, TenantSessionDep, require_permission
from app.repositories.stall_repo import DeleteOutcome, ZoneRepository, sqlstate_of
from app.schemas import ZoneItem, ZoneListResponse, ZoneRequest
from app.security.rbac import Permission

# `UUID` `if TYPE_CHECKING:` ostiga QO'YILMAYDI: FastAPI yo'l
# parametrlarining annotatsiyasini ISH PAYTIDA o'qiydi (`get_type_hints`),
# ya'ni import faqat tip tekshiruvida bo'lsa marshrut `NameError` bilan
# yiqilardi (`users.py:48` da ham aynan shu sababdan oddiy import).
log = structlog.get_logger(__name__)

router = APIRouter(tags=["zones"])

StallManagerDep = Annotated[Principal, Depends(require_permission(Permission.STALL_MANAGE))]
MarketDataViewerDep = Annotated[Principal, Depends(require_permission(Permission.MARKET_DATA_VIEW))]

_NOT_FOUND = "not_found"
_NAME_TAKEN = "zone_name_taken"
_IN_USE = "zone_in_use"

UNIQUE_VIOLATION = "23505"
"""Takroriy `(market_id, name)` — `uq_zones_market_id_name`."""

FK_VIOLATION = "23503"
"""Zonaga havola qiluvchi rasta bor (o'chirishdagi poyga holati)."""


def _market_id(principal: Principal) -> UUID:
    """Tanlangan bozor.

    `TenantSessionDep` allaqachon 409 qaytargan bo'lardi; bu tekshiruv
    mypy uchun emas, KELAJAK uchun: kimdir endpointni tenant sessiyasisiz
    qayta yozsa, `market_id=None` bilan qator yozilib ketmasin.

    Yordamchi har router faylida TAKRORLANADI (`users.py:113-125` va
    `audit.py:115-122` da ham aynan shunday) — umumiy modulga chiqarish
    uchun u juda kichik va har faylda ko'rinib turishi afzal.
    """
    if principal.market_id is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="market_not_selected",
        )
    return principal.market_id


def _not_found() -> HTTPException:
    """Cross-tenant va mavjud bo'lmagan zona uchun BIR XIL javob (T-02-55)."""
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_NOT_FOUND)


def _conflict(exc: IntegrityError) -> HTTPException:
    """`IntegrityError` ni aniq `detail` kodiga aylantiradi.

    Xom xato matni javobga HECH QACHON tushmaydi (T-02-58, ASVS V7): u
    jadval va konstrayt nomlarini oshkor qilardi. Sabab log'ga to'liq
    yoziladi.

    Noma'lum SQLSTATE QAYTA KO'TARILADI — `main.py` dagi global handler uni
    ko'radi. Uni bu yerda "har ehtimolga qarshi" 409 ga aylantirish yangi
    konstraytni jimgina noto'g'ri xabar bilan yashirardi.
    """
    state = sqlstate_of(exc)
    if state == UNIQUE_VIOLATION:
        log.info("zone_name_taken", sqlstate=state)
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_NAME_TAKEN)
    if state == FK_VIOLATION:
        log.info("zone_in_use", sqlstate=state)
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_IN_USE)
    raise exc


def _item(row_id: UUID, name: str, stall_count: int) -> ZoneItem:
    return ZoneItem(id=row_id, name=name, stall_count=stall_count)


@router.get("", response_model=ZoneListResponse)
async def list_zones(
    principal: MarketDataViewerDep,
    session: TenantSessionDep,
) -> ZoneListResponse:
    """Joriy bozorning zonalari, nom tartibida (`MARKET_DATA_VIEW`).

    Sahifalash YO'Q — sabab `ZoneListResponse` docstringida.
    """
    rows = await ZoneRepository(session, _market_id(principal)).list_zones()
    return ZoneListResponse(items=[_item(row.id, row.name, row.stall_count) for row in rows])


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ZoneItem)
async def create_zone(
    payload: ZoneRequest,
    principal: StallManagerDep,
    session: TenantSessionDep,
) -> ZoneItem:
    """Yangi zona (`STALL_MANAGE`). Takroriy nom -> 409 `zone_name_taken`.

    `stall_count` javobda `0` — bu QAYTA SO'RALMAYDI, chunki endigina
    yaratilgan zonaga rasta bog'lanishining yo'li yo'q. Qo'shimcha
    `SELECT` faqat allaqachon ma'lum javobni takrorlardi.
    """
    repo = ZoneRepository(session, _market_id(principal))
    try:
        zone_id = await repo.create(payload.name)
    except IntegrityError as exc:
        raise _conflict(exc) from exc
    return _item(zone_id, payload.name, 0)


@router.patch("/{zone_id}", response_model=ZoneItem)
async def rename_zone(
    zone_id: UUID,
    payload: ZoneRequest,
    principal: StallManagerDep,
    session: TenantSessionDep,
) -> ZoneItem:
    """Zona nomini o'zgartiradi (`STALL_MANAGE`).

    Rasta RAQAMI o'zgarmaydi (D-01: raqam bozor bo'yicha yagona va zona
    kaliti unga kirmaydi), ya'ni zonani qayta nomlash tarixni buzmaydi.
    """
    repo = ZoneRepository(session, _market_id(principal))
    try:
        renamed = await repo.rename(zone_id, payload.name)
    except IntegrityError as exc:
        raise _conflict(exc) from exc
    if renamed is None:
        raise _not_found()

    row = await repo.get(zone_id)
    if row is None:  # pragma: no cover - o'sha tranzaksiyada o'chib ketishi mumkin emas
        raise _not_found()
    return _item(row.id, row.name, row.stall_count)


@router.delete(
    "/{zone_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def delete_zone(
    zone_id: UUID,
    principal: StallManagerDep,
    session: TenantSessionDep,
) -> Response:
    """Zonani o'chiradi (`STALL_MANAGE`); rastasi bo'lsa 409 `zone_in_use`."""
    repo = ZoneRepository(session, _market_id(principal))
    try:
        outcome = await repo.delete(zone_id)
    except IntegrityError as exc:
        raise _conflict(exc) from exc

    if outcome is DeleteOutcome.NOT_FOUND:
        raise _not_found()
    if outcome is DeleteOutcome.IN_USE:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_IN_USE)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
