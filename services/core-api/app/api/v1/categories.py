"""Mahsulot toifalari reestri (D-05) — toifa TARIF KALITINING O'ZI.

=============================================================================
TOIFA ODDIY LUG'AT EMAS — U NARX MODELINING O'QI.

`tariffs` jadvalining kaliti aynan `(market_id, category_id, valid_from)`
(D-05): zona, rasta o'lchami, hafta kuni yoki mavsum bo'yicha farq YO'Q.
Yangi narx kesimi kerak bo'lsa u YANGI TOIFA sifatida ifodalanadi — shunda
6-fazadagi narx qidiruvi bitta shaklda qoladi.

Shuning uchun toifani o'chirish tarif tarixini ham, rastaning toifa
tarixini ham yo'q qilardi. `DELETE` ikkala bog'liqlikni ham tekshiradi va
409 `category_in_use` qaytaradi (`stall_repo._CATEGORY_IN_USE`).
=============================================================================

`GET` javobidagi `current_tariff_soum` `null` bo'lishi MA'NOLI holat
(D-08), nuqson emas: toifa yaratilgan, lekin narx hali berilmagan. Usta
4-qadami aynan shu holatdan boshlanadi va 02-11 faollashtirish darvozasi
"har toifada tarif bor" shartini shu ustundan tekshiradi.

Qolgan hamma narsa `zones.py` bilan bir xil: `GET` uchun
`MARKET_DATA_VIEW`, yozuv uchun `STALL_MANAGE` (D-07), cross-tenant javob
har doim 404 (T-02-55), `market_id` faqat `principal` dan (T-02-54).
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sbozor_core.timeutil import business_today
from sqlalchemy.exc import IntegrityError

from app.deps import Principal, TenantSessionDep, require_permission
from app.repositories.stall_repo import CategoryRepository, DeleteOutcome, sqlstate_of
from app.schemas import CategoryItem, CategoryListResponse, CategoryRequest
from app.security.rbac import Permission

# `UUID` ish paytida kerak — sabab `zones.py` dagi bilan bir xil.
log = structlog.get_logger(__name__)

router = APIRouter(tags=["categories"])

StallManagerDep = Annotated[Principal, Depends(require_permission(Permission.STALL_MANAGE))]
MarketDataViewerDep = Annotated[Principal, Depends(require_permission(Permission.MARKET_DATA_VIEW))]

_NOT_FOUND = "not_found"
_NAME_TAKEN = "category_name_taken"
_IN_USE = "category_in_use"

UNIQUE_VIOLATION = "23505"
"""Takroriy `(market_id, name)` — `uq_stall_categories_market_id_name`."""

FK_VIOLATION = "23503"
"""Toifaga havola qiluvchi tarif yoki toifa davri bor (poyga holati)."""


def _market_id(principal: Principal) -> UUID:
    """Tanlangan bozor (`zones.py` dagi jufti bilan aynan bir xil)."""
    if principal.market_id is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="market_not_selected",
        )
    return principal.market_id


def _not_found() -> HTTPException:
    """Cross-tenant va mavjud bo'lmagan toifa uchun BIR XIL javob (T-02-55)."""
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_NOT_FOUND)


def _conflict(exc: IntegrityError) -> HTTPException:
    """`IntegrityError` -> aniq `detail` kodi; xom matn javobga chiqmaydi (T-02-58)."""
    state = sqlstate_of(exc)
    if state == UNIQUE_VIOLATION:
        log.info("category_name_taken", sqlstate=state)
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_NAME_TAKEN)
    if state == FK_VIOLATION:
        log.info("category_in_use", sqlstate=state)
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_IN_USE)
    raise exc


@router.get("", response_model=CategoryListResponse)
async def list_categories(
    principal: MarketDataViewerDep,
    session: TenantSessionDep,
) -> CategoryListResponse:
    """Toifalar nom tartibida + rasta sanog'i + BUGUNGI narx (`MARKET_DATA_VIEW`).

    Biznes-kun `business_today()` dan olinadi (`date.today()` EMAS):
    konteyner UTC'da ishlaydi va mahalliy 00:00–04:59 oralig'ida
    `date.today()` OLDINGI kunni berardi — o'sha besh soat ichida bugun
    kuchga kirgan narx ro'yxatda ko'rinmasdi.
    """
    repo = CategoryRepository(session, _market_id(principal))
    rows = await repo.list_categories(business_today())
    return CategoryListResponse(
        items=[
            CategoryItem(
                id=row.id,
                name=row.name,
                stall_count=row.stall_count,
                current_tariff_soum=row.current_tariff_soum,
            )
            for row in rows
        ]
    )


@router.post("", status_code=status.HTTP_201_CREATED, response_model=CategoryItem)
async def create_category(
    payload: CategoryRequest,
    principal: StallManagerDep,
    session: TenantSessionDep,
) -> CategoryItem:
    """Yangi toifa (`STALL_MANAGE`). Takroriy nom -> 409 `category_name_taken`.

    Javobdagi `stall_count` `0` va `current_tariff_soum` `null` — ikkalasi
    ham endigina yaratilgan toifa uchun YAGONA mumkin bo'lgan qiymat,
    shuning uchun qayta so'ralmaydi.
    """
    repo = CategoryRepository(session, _market_id(principal))
    try:
        category_id = await repo.create(payload.name)
    except IntegrityError as exc:
        raise _conflict(exc) from exc
    return CategoryItem(id=category_id, name=payload.name, stall_count=0, current_tariff_soum=None)


@router.patch("/{category_id}", response_model=CategoryItem)
async def rename_category(
    category_id: UUID,
    payload: CategoryRequest,
    principal: StallManagerDep,
    session: TenantSessionDep,
) -> CategoryItem:
    """Toifa nomini o'zgartiradi (`STALL_MANAGE`).

    NARX TARIXIGA TEGMAYDI: tarif `category_id` ga bog'langan, nomga emas
    — ya'ni qayta nomlash o'tmishdagi hisobni o'zgartirmaydi.
    """
    repo = CategoryRepository(session, _market_id(principal))
    try:
        renamed = await repo.rename(category_id, payload.name)
    except IntegrityError as exc:
        raise _conflict(exc) from exc
    if renamed is None:
        raise _not_found()

    row = await repo.get(category_id, business_today())
    if row is None:  # pragma: no cover - o'sha tranzaksiyada o'chib ketishi mumkin emas
        raise _not_found()
    return CategoryItem(
        id=row.id,
        name=row.name,
        stall_count=row.stall_count,
        current_tariff_soum=row.current_tariff_soum,
    )


@router.delete(
    "/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def delete_category(
    category_id: UUID,
    principal: StallManagerDep,
    session: TenantSessionDep,
) -> Response:
    """Toifani o'chiradi; tarifi yoki toifa davri bo'lsa 409 `category_in_use`."""
    repo = CategoryRepository(session, _market_id(principal))
    try:
        outcome = await repo.delete(category_id)
    except IntegrityError as exc:
        raise _conflict(exc) from exc

    if outcome is DeleteOutcome.NOT_FOUND:
        raise _not_found()
    if outcome is DeleteOutcome.IN_USE:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_IN_USE)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
