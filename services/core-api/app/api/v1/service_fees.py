"""Majburiy xizmat haqi (tarozi) — bozor darajasidagi narx tarixi (0027).

=============================================================================
⛔⛔ NEGA ALOHIDA MARSHRUT OILASI, `/tariffs` ICHIDA EMAS.

Ekranda ular YONMA-YON turadi (ikkalasi ham «Tariflar» sahifasida) va
foydalanuvchi uchun bu bitta mavzu. Lekin RESURS boshqa: tarif
`(category_id, valid_from)` bilan kalitlanadi, xizmat haqi esa
`(market_id, valid_from)` bilan — ya'ni `/tariffs/{id}` ostiga qo'yilgan
xizmat haqi «qaysi toifaning?» degan javobsiz savolni tug'dirardi.

⚠ UI JOYLASHUVI API SHAKLINI BELGILAMAYDI — bu loyihada bir necha marta
  qo'llangan qoida (`/collect/shift` navigatsiyada yo'q, lekin alohida
  marshrut; `camera-zones` kamera ichida ko'rinadi, lekin o'z oilasida).

=============================================================================
⛔ HUQUQ — `TARIFF_MANAGE` (YANGI HUQUQ QO'SHILMAYDI).

Xizmat haqi PUL MIQDORI va uni o'zgartira oladigan odam aynan tarifni
o'zgartira oladigan odam: bozor admini. Yangi huquq (`SERVICE_FEE_MANAGE`)
qo'shish RBAC matritsasini KENGAYTIRARDI va D-07 ning «direktor nima qila
olmaydi» ta'rifini ikki joyda saqlashga majbur qilardi — foyda esa nol,
chunki egalari to'plami AYNAN bir xil.

O'qish `MARKET_DATA_VIEW` ostida — `GET /tariffs` bilan bir xil.

=============================================================================
⚠ KASSIR BU MARSHRUTLARDAN O'TMAYDI. Unga xizmat haqi
  `GET /billing/pending?stall_code=` javobidagi `fee_amount_soum` /
  `fee_label` orqali yetadi (§9.2) — ya'ni u NARX REYESTRINI umuman
  ko'rmaydi va `MARKET_DATA_VIEW` unda YO'Q (C-10).
=============================================================================
"""

from __future__ import annotations

from datetime import date
from typing import Annotated
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sbozor_core.money import assert_safe_soum
from sbozor_core.timeutil import business_today
from sqlalchemy.exc import IntegrityError

from app.deps import Principal, TenantSessionDep, require_permission
from app.repositories.service_fee_repo import ServiceFeeRepository, ServiceFeeRow
from app.repositories.stall_repo import MarketProfileMissingError, sqlstate_of
from app.schemas import (
    ServiceFeeCreateRequest,
    ServiceFeeItem,
    ServiceFeeListResponse,
)
from app.security.rbac import Permission

log = structlog.get_logger(__name__)

__all__ = ["router"]

router = APIRouter(tags=["service-fees"])

FeeManagerDep = Annotated[Principal, Depends(require_permission(Permission.TARIFF_MANAGE))]
FeeViewerDep = Annotated[Principal, Depends(require_permission(Permission.MARKET_DATA_VIEW))]

_NOT_FOUND = "not_found"
_ALREADY_SET = "service_fee_already_set_for_date"
_PAST_LOCKED = "service_fee_past_locked"
_NOT_FUTURE = "valid_from_must_be_future"
_MARKET_INCOMPLETE = "market_incomplete"

UNIQUE_VIOLATION = "23505"
"""Takroriy `valid_from` — `uq_market_service_fees_market_id_valid_from`."""

CHECK_VIOLATION = "23514"
"""`trg_service_fee_past_immutable` NING SQLSTATE'i (D-07).

⚠ Bu jadvalda YANA IKKI `CHECK` bor (`amount_non_negative`,
  `label_not_blank`) va ular ham `23514` beradi. Ikkalasi ham Pydantic
  (`Field(ge=0)`, `min_length=1`) va marshrutdagi `strip()` bilan
  ALLAQACHON to'silgan, ya'ni bu yo'lda `23514` ni ko'rish amalda AYNAN
  o'zgarmaslik triggerini bildiradi — `tariffs.py` dagi bilan bir xil
  mulohaza, lekin bu yerda taxmin KUCHSIZROQ va shuning uchun ochiq
  yozildi.
"""


def _market_id(principal: Principal) -> UUID:
    """Tanlangan bozor (`tariffs.py` dagi jufti bilan aynan bir xil)."""
    if principal.market_id is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="market_not_selected",
        )
    return principal.market_id


def _not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_NOT_FOUND)


def _write_conflict(exc: IntegrityError) -> HTTPException:
    """Noma'lum SQLSTATE QAYTA KO'TARILADI (`tariffs.py` bilan bir xil qaror)."""
    state = sqlstate_of(exc)
    if state == UNIQUE_VIOLATION:
        log.info("service_fee_already_set_for_date", sqlstate=state)
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_ALREADY_SET)
    if state == CHECK_VIOLATION:
        log.info("service_fee_past_locked", sqlstate=state)
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=_PAST_LOCKED)
    raise exc


def _item(row: ServiceFeeRow, today: date) -> ServiceFeeItem:
    """Repozitoriy qatori -> javob elementi.

    `is_past` SHU YERDA hisoblanadi va DB'dan kelmaydi: u qatorning
    xususiyati emas, SO'ROV PAYTIDAGI holat (`tariffs.py::_item()`).
    """
    return ServiceFeeItem(
        id=row.id,
        amount_soum=row.amount_soum,
        label=row.label,
        valid_from=row.valid_from,
        valid_to=row.valid_to,
        is_past=row.valid_from <= today,
    )


@router.get("", response_model=ServiceFeeListResponse)
async def list_service_fees(
    principal: FeeViewerDep,
    session: TenantSessionDep,
) -> ServiceFeeListResponse:
    """Xizmat haqi tarixi + bugungi qiymat (`MARKET_DATA_VIEW`).

    ⛔ `current_amount_soum` RO'YXATDAN HOSILA QILINMAYDI — u alohida
       so'rov (`repo.current()`). Sabab `ServiceFeeListResponse`
       docstringida: ro'yxatning birinchi qatori KELAJAKDAGI narx
       bo'lishi mumkin.

    ⚠ Bozor xizmat haqi belgilamagan bo'lsa `items` BO'SH va
      `current_amount_soum` `null` — bu XATO EMAS, HALOL javob
      («bu bozorda tarozi olinmaydi»).
    """
    market_id = _market_id(principal)
    today = business_today()
    repo = ServiceFeeRepository(session, market_id)

    try:
        window = await repo.window(today)
    except MarketProfileMissingError as exc:
        log.warning("market_profile_missing", market_id=str(market_id), error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=_MARKET_INCOMPLETE
        ) from exc

    rows = await repo.list_rows()
    current = await repo.current(today)

    return ServiceFeeListResponse(
        items=[_item(row, today) for row in rows],
        min_valid_from=window.min_valid_from,
        current_amount_soum=None if current is None else current[0],
        current_label=None if current is None else current[1],
    )


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ServiceFeeItem)
async def create_service_fee(
    payload: ServiceFeeCreateRequest,
    principal: FeeManagerDep,
    session: TenantSessionDep,
) -> ServiceFeeItem:
    """Yangi xizmat haqi qatori (`TARIFF_MANAGE`, D-06 — `UPDATE` YO'Q).

    409 `service_fee_already_set_for_date` — shu sanaga narx bor;
    422 `valid_from_must_be_future` — sana ruxsat etilgan oynadan tashqarida.
    """
    # IKKINCHI QATLAM: Pydantic `ge=0, le=MAX_SAFE_SOUM` ni allaqachon
    # majburlaydi. Chaqiruv baribir qoladi — pul chegarasining ta'rifi
    # `sbozor_core.money` da yashaydi va u DTO cheklovidan mustaqil
    # o'zgarishi mumkin (`tariffs.py` dagi bilan bir xil izoh).
    amount = assert_safe_soum(payload.amount_soum)

    # ⛔ `strip()` MAJBURIY: Pydantic `min_length=1` bo'shliqni qirqmaydi,
    #   ya'ni `"   "` undan o'tib DB'dagi `length(btrim(label)) > 0` ga
    #   urilardi va foydalanuvchi 403/500 ko'rardi. Bu yerda u 422 ga
    #   aylanadi — quyidagi shart.
    label = payload.label.strip()
    if not label:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="service_fee_label_blank",
        )

    market_id = _market_id(principal)
    today = business_today()
    repo = ServiceFeeRepository(session, market_id)

    try:
        window = await repo.window(today)
    except MarketProfileMissingError as exc:
        log.warning("market_profile_missing", market_id=str(market_id), error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=_MARKET_INCOMPLETE
        ) from exc

    if not repo.is_valid_from_allowed(payload.valid_from, window, today):
        log.info("valid_from_rejected", valid_from=str(payload.valid_from))
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=_NOT_FUTURE)

    try:
        fee_id = await repo.add(amount_soum=amount, label=label, valid_from=payload.valid_from)
    except IntegrityError as exc:
        raise _write_conflict(exc) from exc

    row = await repo.get(fee_id)
    if row is None:  # pragma: no cover - o'sha tranzaksiyada yo'qolmaydi
        raise _not_found()
    return _item(row, today)


@router.delete(
    "/{fee_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def delete_service_fee(
    fee_id: UUID,
    principal: FeeManagerDep,
    session: TenantSessionDep,
) -> Response:
    """KELAJAKDAGI qatorni o'chiradi (`TARIFF_MANAGE`, D-07).

    403 `service_fee_past_locked` — sanasi o'tgan qator (DB triggeri);
    404 — qator begona bozorniki yoki mavjud emas.
    """
    repo = ServiceFeeRepository(session, _market_id(principal))
    try:
        removed = await repo.delete_future(fee_id)
    except IntegrityError as exc:
        raise _write_conflict(exc) from exc

    if not removed:
        raise _not_found()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
