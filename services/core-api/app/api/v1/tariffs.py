"""Tarif boshqaruvi (MARKET-03) — narx tarixining HTTP yuzasi.

=============================================================================
BU YUZA FAQAT QO'SHADI. `POST` yangi qator yozadi, `PATCH`/`DELETE` esa
faqat KELAJAKDAGI qatorga ta'sir qila oladi.

Moliyaviy yaxlitlikning KAFOLATI bu faylda EMAS — u DB triggerida
(`trg_tariff_past_immutable`, 02-05). Bu faylning vazifasi o'sha kafolatni
foydalanuvchi TUSHUNADIGAN xatoga aylantirish: aniq HTTP kodi va aniq
`detail`. Ilova tekshiruvi triggerning o'rnini bosmaydi va bosishi ham
kerak emas — xom SQL yo'lini faqat trigger qamraydi (1-faza D-10
falsafasi).
=============================================================================

O'QISH VA YOZISH HUQUQLARI AJRATILGAN (D-07): `GET` uchun
`MARKET_DATA_VIEW`, yozuv uchun `TARIFF_MANAGE`. Direktorda ikkinchisi
YO'Q — u narx tarixini KO'RADI (hisobotlari shunsiz ma'nosiz), lekin
o'zgartira olmaydi. `test_director_cannot_manage_tariffs` shu chegarani
nazorat holati (`GET` -> 200) bilan birga qulflaydi.

CROSS-TENANT JAVOB — HAR DOIM 404 (T-02-67), 403 EMAS.

`market_id` HECH QACHON SO'ROV TANASIDAN OLINMAYDI (T-02-54):
`TariffCreateRequest` va `TariffUpdateRequest` da bunday maydon umuman
e'lon qilinmagan.

-----------------------------------------------------------------------------
XATO XARITASI — FAQAT `sqlstate` BO'YICHA (`constraint_name` asyncpg
o'ramida `None`, RLS esa `DETAIL` ni o'chiradi — Pitfall 4):

    ValidFromNotAllowedError    ->  422 valid_from_must_be_future
    MarketProfileMissingError   ->  409 market_incomplete
    23505                       ->  409 tariff_already_set_for_date
    23503                       ->  404 (begona yoki mavjud bo'lmagan category_id)
    23514 (trigger)             ->  403 tariff_past_locked

`23514` uchun javob **403**, 409 EMAS va bu ataylab: o'tmish HECH KIMGA
ochiq emas, ya'ni bu HUQUQ masalasi — bir vaqtning o'zida ikki tomon bir
xil resursni o'zgartirmoqchi bo'lgan KONFLIKT emas. Aynan shu mulohaza
02-08 dagi `category_period_past_locked` uchun ham ishlatilgan.

`valid_from` uchun esa 422 (403 emas): u yerda mavjud qatorga umuman
tegilmayapti — rad etilayotgani YANGI qatorning sanasi.
-----------------------------------------------------------------------------

AUDIT BU YERDA YOZILMAYDI: `tariffs` `AUDITED_TABLES` da va DB-trigger
ostida (02-05). App-qatlam yozuvi qo'shilsa har `INSERT` uchun IKKITA
audit qatori paydo bo'lardi va jurnalni o'qiyotgan odam "nima ikki marta
sodir bo'ldi?" degan savol bilan qolardi (`app/security/audit.py` dagi
2-faza bo'limi bilan bir xil qoida).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sbozor_core.money import assert_safe_soum
from sbozor_core.timeutil import business_today
from sqlalchemy.exc import IntegrityError

from app.deps import Principal, TenantSessionDep, require_permission
from app.repositories.stall_repo import MarketProfileMissingError, sqlstate_of
from app.repositories.tariff_repo import (
    TariffRepository,
    TariffRow,
    ValidFromNotAllowedError,
)
from app.schemas import (
    TariffCreateRequest,
    TariffItem,
    TariffListResponse,
    TariffUpdateRequest,
)
from app.security.rbac import Permission

if TYPE_CHECKING:
    from datetime import date

# `UUID` `if TYPE_CHECKING:` ostiga QO'YILMAYDI: FastAPI yo'l
# parametrlarining annotatsiyasini ISH PAYTIDA o'qiydi (`zones.py` /
# `stalls.py` dagi bilan bir xil sabab). `date` esa faqat yordamchi
# funksiyalar imzosida uchraydi va u marshrut annotatsiyasi emas.
log = structlog.get_logger(__name__)

router = APIRouter(tags=["tariffs"])

TariffManagerDep = Annotated[Principal, Depends(require_permission(Permission.TARIFF_MANAGE))]
MarketDataViewerDep = Annotated[Principal, Depends(require_permission(Permission.MARKET_DATA_VIEW))]

_NOT_FOUND = "not_found"
_ALREADY_SET = "tariff_already_set_for_date"
_PAST_LOCKED = "tariff_past_locked"
_NOT_FUTURE = "valid_from_must_be_future"
_MARKET_INCOMPLETE = "market_incomplete"

UNIQUE_VIOLATION = "23505"
"""Takroriy `(category_id, valid_from)` — `uq_tariffs_market_id_category_id_valid_from`."""

FK_VIOLATION = "23503"
"""Begona bozorning (yoki mavjud bo'lmagan) `category_id` si."""

CHECK_VIOLATION = "23514"
"""`trg_tariff_past_immutable` ning SQLSTATE'i (D-07).

Trigger `RAISE EXCEPTION ... USING ERRCODE = '23514'` yozadi, ya'ni u
oddiy `CHECK` konstrayti bilan bir xil kod beradi. `tariffs` dagi yagona
boshqa `CHECK` — `amount_soum > 0` va u Pydantic (`Field(gt=0)`)
tomonidan allaqachon to'silgan, shuning uchun bu yo'lda `23514` ni ko'rish
AYNAN o'zgarmaslik triggerini bildiradi.
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
    """Cross-tenant va mavjud bo'lmagan tarif uchun BIR XIL javob (T-02-67)."""
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_NOT_FOUND)


def _past_locked() -> HTTPException:
    """O'tmishdagi qatorni tahrirlash/o'chirish — **403** (T-02-62)."""
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=_PAST_LOCKED)


def _incomplete(exc: Exception, market_id: UUID) -> HTTPException:
    """`market_profile` qatori yo'q -> 409 `market_incomplete` (02-08 naqshi)."""
    log.warning("market_profile_missing", market_id=str(market_id), error=str(exc))
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_MARKET_INCOMPLETE)


def _not_future(exc: ValidFromNotAllowedError) -> HTTPException:
    """Ruxsat etilmagan `valid_from` -> 422."""
    log.info("valid_from_rejected", error=str(exc))
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail=_NOT_FUTURE,
    )


def _write_conflict(exc: IntegrityError) -> HTTPException:
    """`tariffs` yo'lidagi `IntegrityError` -> aniq `detail` kodi.

    Noma'lum SQLSTATE QAYTA KO'TARILADI (`main.py` global handleri uni 500
    ga aylantiradi): "har ehtimolga qarshi" 409 yangi konstraytni jimgina
    noto'g'ri xabar bilan yashirardi (`stalls.py` bilan bir xil qaror).
    """
    state = sqlstate_of(exc)
    if state == UNIQUE_VIOLATION:
        log.info("tariff_already_set_for_date", sqlstate=state)
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_ALREADY_SET)
    if state == FK_VIOLATION:
        # Begona bozorning `category_id` si — javob **404**, 403 EMAS:
        # 403 o'sha toifa MAVJUDLIGINI tasdiqlardi (T-02-67).
        log.info("tariff_category_not_found", sqlstate=state)
        return _not_found()
    if state == CHECK_VIOLATION:
        log.info("tariff_past_locked", sqlstate=state)
        return _past_locked()
    raise exc


def _item(row: TariffRow, today: date) -> TariffItem:
    """Repozitoriy qatorini javob elementiga o'giradi.

    `is_past` SHU YERDA hisoblanadi va DB'dan kelmaydi: u qatorning
    xususiyati emas, SO'ROV PAYTIDAGI holat. Ustun sifatida saqlansa
    ertaga yolg'onga aylanardi.
    """
    return TariffItem(
        id=row.id,
        category_id=row.category_id,
        category_name=row.category_name,
        amount_soum=row.amount_soum,
        valid_from=row.valid_from,
        valid_to=row.valid_to,
        is_past=row.valid_from <= today,
    )


async def _row_or_404(repo: TariffRepository, tariff_id: UUID, today: date) -> TariffItem:
    """Yozuvdan KEYINGI javob — bitta joyda.

    Javob AYNAN o'qish yo'lidan quriladi, ya'ni klient `POST`/`PATCH` dan
    keyin `GET` qilganda boshqa shakl ko'rmaydi. `valid_to` ham shu
    tufayli to'g'ri chiqadi: u oyna funksiyasi bilan BUTUN toifa tarixi
    ustida hisoblanadi (`tariff_repo._TARIFF_ROWS`).
    """
    row = await repo.get(tariff_id)
    if row is None:  # pragma: no cover - o'sha tranzaksiyada yo'qolishi mumkin emas
        raise _not_found()
    return _item(row, today)


@router.get("", response_model=TariffListResponse)
async def list_tariffs(
    principal: MarketDataViewerDep,
    session: TenantSessionDep,
    category: Annotated[UUID | None, Query()] = None,
) -> TariffListResponse:
    """Tarif tarixi + ruxsat etilgan eng erta sana (`MARKET_DATA_VIEW`).

    `min_valid_from` HAR DOIM to'ldiriladi — ro'yxat BO'SH bo'lganda ham.
    Usta 4-qadami aynan bo'sh ro'yxatdan boshlanadi va o'sha ekranda sana
    maydonining chegarasi allaqachon kerak bo'ladi (02-15).

    ⚠ `min_valid_from` KLIENT QULAYLIGI, darvoza EMAS: haqiqiy tekshiruv
    `TariffRepository.add_tariff()` da va u DevTools bilan olib
    tashlanmaydi.

    Sahifalash YO'Q — sabab `TariffListResponse` docstringida.
    """
    market_id = _market_id(principal)
    today = business_today()
    repo = TariffRepository(session, market_id)
    try:
        window = await repo.tariff_window(today)
    except MarketProfileMissingError as exc:
        raise _incomplete(exc, market_id) from exc

    rows = await repo.list_tariffs(category)
    return TariffListResponse(
        items=[_item(row, today) for row in rows],
        min_valid_from=window.min_valid_from,
    )


@router.post("", status_code=status.HTTP_201_CREATED, response_model=TariffItem)
async def create_tariff(
    payload: TariffCreateRequest,
    principal: TariffManagerDep,
    session: TenantSessionDep,
) -> TariffItem:
    """Yangi narx qatori (`TARIFF_MANAGE`, D-06 — `UPDATE` YO'Q).

    422 `valid_from_must_be_future` — sana ikkala ruxsat etilgan tarmoqqa
    ham tushmadi (`TariffRepository.is_valid_from_allowed()` docstringi);
    409 `tariff_already_set_for_date` — shu toifaga shu sanada narx bor;
    404 — `category_id` begona bozorniki yoki mavjud emas.
    """
    # IKKINCHI QATLAM: Pydantic allaqachon `gt=0, le=MAX_SAFE_SOUM` ni
    # majburlaydi, ya'ni bu yerda istisno amalda chiqmaydi. Chaqiruv
    # baribir qoladi — pul chegarasining ta'rifi `sbozor_core.money` da
    # yashaydi va u DTO cheklovidan mustaqil o'zgarishi mumkin.
    amount = assert_safe_soum(payload.amount_soum)

    market_id = _market_id(principal)
    today = business_today()
    repo = TariffRepository(session, market_id)
    try:
        tariff_id = await repo.add_tariff(
            category_id=payload.category_id,
            amount_soum=amount,
            valid_from=payload.valid_from,
            today=today,
        )
    except MarketProfileMissingError as exc:
        raise _incomplete(exc, market_id) from exc
    except ValidFromNotAllowedError as exc:
        raise _not_future(exc) from exc
    except IntegrityError as exc:
        raise _write_conflict(exc) from exc

    return await _row_or_404(repo, tariff_id, today)


@router.patch("/{tariff_id}", response_model=TariffItem)
async def update_tariff(
    tariff_id: UUID,
    payload: TariffUpdateRequest,
    principal: TariffManagerDep,
    session: TenantSessionDep,
) -> TariffItem:
    """KELAJAKDAGI narx qatorini tahrirlaydi (`TARIFF_MANAGE`, D-07).

    `exclude_unset=True` MAJBURIY: usiz har `PATCH` berilmagan maydonni
    ham yozardi va `amount_soum` ni o'zgartirmoqchi bo'lgan so'rov
    `valid_from` ni ham "yangi" qiymat bilan qayta yozib, trigger
    darvozasini keraksiz yerda ishga tushirardi.

    403 `tariff_past_locked` — qatorning sanasi o'tgan (DB triggeri);
    422 `valid_from_must_be_future` — YANGI sana ruxsat etilmagan;
    409 `tariff_already_set_for_date` — o'sha toifada o'sha sana band;
    404 — qator begona bozorniki yoki mavjud emas.
    """
    market_id = _market_id(principal)
    today = business_today()
    repo = TariffRepository(session, market_id)
    changes: dict[str, Any] = payload.model_dump(exclude_unset=True)
    try:
        updated = await repo.update_future(tariff_id, changes, today)
    except MarketProfileMissingError as exc:
        raise _incomplete(exc, market_id) from exc
    except ValidFromNotAllowedError as exc:
        raise _not_future(exc) from exc
    except IntegrityError as exc:
        raise _write_conflict(exc) from exc

    if updated is None:
        raise _not_found()
    return await _row_or_404(repo, tariff_id, today)


@router.delete(
    "/{tariff_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def delete_tariff(
    tariff_id: UUID,
    principal: TariffManagerDep,
    session: TenantSessionDep,
) -> Response:
    """KELAJAKDAGI narx qatorini o'chiradi (`TARIFF_MANAGE`, D-07).

    403 `tariff_past_locked` — sanasi o'tgan qator (DB triggeri, `23514`);
    404 — qator begona bozorniki yoki mavjud emas.
    """
    repo = TariffRepository(session, _market_id(principal))
    try:
        removed = await repo.delete_future(tariff_id)
    except IntegrityError as exc:
        raise _write_conflict(exc) from exc

    if not removed:
        raise _not_found()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
