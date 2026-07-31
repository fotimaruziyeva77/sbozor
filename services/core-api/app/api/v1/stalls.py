"""Rasta reestri va plan-xarita (MARKET-02, MARKET-06) — fazaning eng ko'p ishlatiladigan yuzasi.

=============================================================================
MARSHRUT TARTIBI AHAMIYATLI: `GET /map` `GET /{stall_id}` DAN OLDIN.

FastAPI marshrutlarni E'LON TARTIBIDA solishtiradi. Teskari tartibda
`/api/v1/stalls/map` so'rovi `{stall_id}` shabloniga tushardi, `"map"`
esa UUID emas — natijada foydalanuvchi xarita o'rniga 422 olardi va
sabab kodga qarab UMUMAN ko'rinmasdi (ikkala marshrut ham to'g'ri
yozilgan bo'lib turardi).
=============================================================================

O'QISH VA YOZISH HUQUQLARI AJRATILGAN (D-07): `GET` uchun
`MARKET_DATA_VIEW`, yozuv uchun `STALL_MANAGE`. Direktorda ikkinchisi
YO'Q — `test_director_cannot_manage_stalls` shu chegarani qulflaydi va
nazorat holati (`GET` -> 200) bilan birga keladi.

CROSS-TENANT JAVOB — HAR DOIM 404 (T-02-55), 403 EMAS.

`market_id` HECH QACHON SO'ROV TANASIDAN OLINMAYDI (T-02-54): u faqat
`_market_id(principal)` dan keladi va `StallCreateRequest` /
`StallUpdateRequest` da bunday maydon umuman e'lon qilinmagan.

-----------------------------------------------------------------------------
XATO XARITASI — FAQAT `sqlstate` BO'YICHA (`constraint_name` asyncpg
o'ramida `None`, RLS esa `DETAIL` ni o'chiradi — Pitfall 4):

    23505 + xato matnida "stall code"  ->  409 stall_code_retired  (D-02)
    23505 (boshqa)                     ->  409 stall_code_taken    (D-01)
    23505 toifa davri yo'lida          ->  409 category_period_exists
    23503                              ->  404 (begona yoki mavjud bo'lmagan
                                                zone_id / category_id)
    CategoryPeriodPastError            ->  403 category_period_past_locked

403 ATAYIN, 422 EMAS: 02-09 dagi `tariff_past_locked` bilan bir xil
mulohaza — o'tmish hech kimga ochiq emas, bu HUQUQ masalasi.
-----------------------------------------------------------------------------
"""

# =============================================================================
# ⚠ CHECK-KONSTRAYT SQLSTATE'i (23514) BU FAYLDA ATAYIN YO'Q va uni xato
# xaritasiga QO'SHMANG.
#
# `trg_category_period_past_immutable` — `BEFORE UPDATE OR DELETE ON
# stall_category_periods` (02-04:127), bu fayldagi yagona yo'l esa
# `INSERT`. Ya'ni o'sha tarmoq HECH QACHON bajarilmaydigan o'lik kod
# bo'lardi va o'qiyotgan odamni "DB darajasida himoya bor" deb aldardi —
# aynan o'sha yolg'on ishonch tufayli ilova darvozasi keyinchalik
# "ortiqcha" deb olib tashlanishi mumkin edi.
#
# Haqiqiy darvoza — `StallRepository.set_category()` ichidagi ilova
# tekshiruvi (T-02-61a) va u 02-08 Task 3 dagi UCH test bilan qulflangan
# (kelajak -> 201, bugun -> 403, o'tmish -> 403).
#
# Bu izoh ATAYIN `#` bloki (docstring EMAS): qabul mezoni faylni shu
# SQLSTATE bo'yicha grep qiladi va izoh qatorlarini filtrlab tashlaydi,
# ya'ni sabab yozilgan holda ham darvoza o'z-o'ziga qarshi turmaydi.
# =============================================================================

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sbozor_core.enums import StallStatus
from sbozor_core.timeutil import business_today
from sqlalchemy.exc import IntegrityError

from app.deps import Principal, TenantSessionDep, require_permission
from app.repositories.audit_repo import InvalidCursorError
from app.repositories.stall_repo import (
    CategoryPeriodPastError,
    MarketProfileMissingError,
    StallRepository,
    StallRow,
    sqlstate_of,
)
from app.schemas import (
    MapCell,
    MapZone,
    StallCategoryRequest,
    StallCreateRequest,
    StallDetail,
    StallListItem,
    StallListResponse,
    StallMapResponse,
    StallQuery,
    StallUpdateRequest,
)
from app.security.rbac import Permission

# `UUID` ish paytida kerak — FastAPI yo'l parametrlarining annotatsiyasini
# `get_type_hints` bilan o'qiydi (`zones.py` dagi bilan bir xil sabab).
log = structlog.get_logger(__name__)

router = APIRouter(tags=["stalls"])

StallManagerDep = Annotated[Principal, Depends(require_permission(Permission.STALL_MANAGE))]
MarketDataViewerDep = Annotated[Principal, Depends(require_permission(Permission.MARKET_DATA_VIEW))]

_NOT_FOUND = "not_found"
_CODE_TAKEN = "stall_code_taken"
_CODE_RETIRED = "stall_code_retired"
_PERIOD_EXISTS = "category_period_exists"
_PERIOD_PAST_LOCKED = "category_period_past_locked"
_MARKET_INCOMPLETE = "market_incomplete"

UNIQUE_VIOLATION = "23505"
FK_VIOLATION = "23503"

RETIRED_CODE_MARKER = "stall code"
"""`stall_code_claim()` triggerining xato matnidagi belgi (02-04).

Trigger `RAISE EXCEPTION 'stall code % is already retired ...'` yozadi va
`ERRCODE = '23505'` beradi, ya'ni SQLSTATE bo'yicha uni oddiy "kod band"
holatidan AJRATIB BO'LMAYDI. Ikki holat foydalanuvchi uchun butunlay
boshqacha ("bu raqam hozir band" va "bu raqam bir marta ishlatilgan va
qaytarilmaydi"), shuning uchun ajratish xato MATNI bo'yicha bo'ladi —
va aynan shu farq 02-07 sabotaj o'lchovida ko'rindi.

Matn `exc.orig` dan olinadi, `exc` dan EMAS: `str(exc)` SQL operatorini
ham o'z ichiga oladi va u kelajakda tasodifan shu belgini saqlashi
mumkin edi.
"""


def _market_id(principal: Principal) -> UUID:
    """Tanlangan bozor (`zones.py` / `users.py` dagi jufti bilan aynan bir xil)."""
    if principal.market_id is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="market_not_selected",
        )
    return principal.market_id


def _not_found() -> HTTPException:
    """Cross-tenant va mavjud bo'lmagan rasta uchun BIR XIL javob (T-02-55)."""
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_NOT_FOUND)


def _stall_conflict(exc: IntegrityError) -> HTTPException:
    """`stalls` yo'lidagi `IntegrityError` -> aniq `detail` kodi.

    Noma'lum SQLSTATE QAYTA KO'TARILADI (`main.py` global handleri uni
    500 ga aylantiradi): "har ehtimolga qarshi" 409 yangi konstraytni
    jimgina noto'g'ri xabar bilan yashirardi.
    """
    state = sqlstate_of(exc)
    if state == UNIQUE_VIOLATION:
        if RETIRED_CODE_MARKER in str(exc.orig):
            log.info("stall_code_retired", sqlstate=state)
            return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_CODE_RETIRED)
        log.info("stall_code_taken", sqlstate=state)
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_CODE_TAKEN)
    if state == FK_VIOLATION:
        # Begona bozorning `zone_id`/`category_id` si — javob **404**, 403
        # EMAS: 403 o'sha zona MAVJUDLIGINI tasdiqlardi (T-02-56).
        log.info("stall_reference_not_found", sqlstate=state)
        return _not_found()
    raise exc


def _category_period_conflict(exc: IntegrityError) -> HTTPException:
    """`stall_category_periods` yo'lidagi `IntegrityError` -> aniq `detail` kodi.

    `stalls` yo'lidan ALOHIDA: u yerda `23505` "kod band/chetlangan"
    degani, bu yerda esa "shu sanaga davr allaqachon yozilgan"
    (`uq_stall_category_periods_market_id_stall_id_valid_from`). Bitta
    umumiy xaritachi ikkala holatga ham noto'g'ri kod berardi.
    """
    state = sqlstate_of(exc)
    if state == UNIQUE_VIOLATION:
        log.info("category_period_exists", sqlstate=state)
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_PERIOD_EXISTS)
    if state == FK_VIOLATION:
        log.info("category_not_found", sqlstate=state)
        return _not_found()
    raise exc


def _past_locked() -> HTTPException:
    """O'tmishdagi `valid_from` — 403 (T-02-61a)."""
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=_PERIOD_PAST_LOCKED,
    )


def _list_item(row: StallRow) -> StallListItem:
    """Repozitoriy qatorini ro'yxat elementiga o'giradi.

    `StallStatus(row.status)` — ATAYIN aniq konversiya: DB ustuni `text`
    (`STALL_STATUS_CHECK` konstrayti bilan cheklangan), javob esa enum
    ustida. Noma'lum qiymat shu yerda `ValueError` beradi va 500 ga
    aylanadi — bu TO'G'RI xulq: u sxema bilan enum ajralib ketganini
    bildiradi va uni jimgina o'tkazib yuborish xaritada rangsiz katak
    hosil qilardi.
    """
    return StallListItem(
        id=row.id,
        code=row.code,
        zone_id=row.zone_id,
        zone_name=row.zone_name,
        category_id=row.category_id,
        category_name=row.category_name,
        status=StallStatus(row.status),
        vendor_id=row.vendor_id,
        vendor_name=row.vendor_name,
        tariff_soum=row.tariff_soum,
        created_at=row.created_at,
    )


def _detail(row: StallRow) -> StallDetail:
    return StallDetail(
        **_list_item(row).model_dump(),
        phone=row.phone,
        assignment_from=row.assignment_from,
        note=row.note,
    )


async def _detail_or_404(repo: StallRepository, stall_id: UUID) -> StallDetail:
    """Yozuvdan KEYINGI javob — bitta joyda.

    Yozuv endpointlari javobni AYNAN o'qish yo'lidan quradi, ya'ni klient
    `POST`/`PATCH` dan keyin `GET` qilganda boshqa shakl ko'rmaydi.
    """
    row = await repo.detail(stall_id, business_today())
    if row is None:  # pragma: no cover - o'sha tranzaksiyada yo'qolishi mumkin emas
        raise _not_found()
    return _detail(row)


@router.get("", response_model=StallListResponse)
async def list_stalls(
    principal: MarketDataViewerDep,
    session: TenantSessionDep,
    query: Annotated[StallQuery, Query()],
) -> StallListResponse:
    """Filtrlangan keyset sahifa (`MARKET_DATA_VIEW`), UI-SPEC §8.3 filtrlari.

    Tartib — `code_sort` bo'yicha, ya'ni INSON-RAQAMLI (2 < 10 < 100).
    Frontend qayta saralamaydi (UI-SPEC §7.3).
    """
    repo = StallRepository(session, _market_id(principal))
    try:
        page = await repo.list_stalls(query, business_today())
    except InvalidCursorError as exc:
        # `audit.py` bilan AYNAN bir xil javob: buzuq kursor 422, jimgina
        # birinchi sahifaga qaytish EMAS (u sahifalashni cheksiz siklga
        # aylantirardi).
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="invalid_cursor",
        ) from exc

    return StallListResponse(
        items=[_list_item(row) for row in page.rows],
        next_cursor=page.next_cursor,
    )


@router.get("/map", response_model=StallMapResponse)
async def stall_map(
    principal: MarketDataViewerDep,
    session: TenantSessionDep,
) -> StallMapResponse:
    """Zonalar bo'yicha guruhlangan kataklar (MARKET-06, `MARKET_DATA_VIEW`).

    ⚠ BU MARSHRUT `GET /{stall_id}` DAN OLDIN e'lon qilingan — sabab modul
    docstringida.

    Javobda `tone` YO'Q (D-20): API `status` + `has_vendor` xom faktlarini
    beradi, rangni frontend hosil qiladi.
    """
    repo = StallRepository(session, _market_id(principal))
    zones = await repo.map_view(business_today())
    return StallMapResponse(
        zones=[
            MapZone(
                id=zone.id,
                name=zone.name,
                cells=[
                    MapCell(
                        id=cell.id,
                        code=cell.code,
                        status=StallStatus(cell.status),
                        has_vendor=cell.has_vendor,
                    )
                    for cell in zone.cells
                ],
            )
            for zone in zones
        ]
    )


@router.get("/{stall_id}", response_model=StallDetail)
async def get_stall(
    stall_id: UUID,
    principal: MarketDataViewerDep,
    session: TenantSessionDep,
) -> StallDetail:
    """Bitta rasta kartochkasi (`MARKET_DATA_VIEW`).

    Ro'yxat qatoridan uchta maydon bilan farq qiladi: sotuvchi telefoni
    (SHAXSIY MA'LUMOT — shuning uchun ro'yxatda yo'q), biriktirish
    boshlangan sana va izoh.
    """
    row = await StallRepository(session, _market_id(principal)).detail(stall_id, business_today())
    if row is None:
        raise _not_found()
    return _detail(row)


@router.post("", status_code=status.HTTP_201_CREATED, response_model=StallDetail)
async def create_stall(
    payload: StallCreateRequest,
    principal: StallManagerDep,
    session: TenantSessionDep,
) -> StallDetail:
    """Yangi rasta (`STALL_MANAGE`) + uning BOSHLANG'ICH toifa davri.

    Toifa davrining `valid_from` i `market_profile.operating_since` dan
    olinadi va so'rov tanasida bunday maydon UMUMAN yo'q — sabab
    `StallRepository.create()` docstringida (uchta mustaqil dalil).

    409 `stall_code_taken` — raqam hozir band (D-01);
    409 `stall_code_retired` — raqam bir marta ishlatilgan va qaytarilmaydi (D-02);
    404 — `zone_id`/`category_id` begona bozorniki yoki mavjud emas.
    """
    repo = StallRepository(session, _market_id(principal))
    try:
        stall_id = await repo.create(
            code=payload.code,
            zone_id=payload.zone_id,
            category_id=payload.category_id,
            status=str(payload.status),
            note=payload.note,
        )
    except MarketProfileMissingError as exc:
        log.warning("market_profile_missing", market_id=str(_market_id(principal)))
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=_MARKET_INCOMPLETE,
        ) from exc
    except IntegrityError as exc:
        raise _stall_conflict(exc) from exc

    return await _detail_or_404(repo, stall_id)


@router.patch("/{stall_id}", response_model=StallDetail)
async def update_stall(
    stall_id: UUID,
    payload: StallUpdateRequest,
    principal: StallManagerDep,
    session: TenantSessionDep,
) -> StallDetail:
    """Rasta raqami / zonasi / holati / izohini tahrirlaydi (`STALL_MANAGE`).

    `exclude_unset=True` MAJBURIY: usiz har `PATCH` berilmagan maydonlarni
    `null` bilan tozalab ketardi (masalan izohni). Shu bilan "berilmagan"
    va "ataylab bo'shatilgan" holatlari ajraladi.

    `category_id` bu yerda QABUL QILINMAYDI (D-04) — toifa alohida
    endpoint va alohida darvoza ostida o'zgaradi.
    """
    repo = StallRepository(session, _market_id(principal))
    changes: dict[str, Any] = payload.model_dump(exclude_unset=True)
    try:
        updated = await repo.update(stall_id, changes)
    except IntegrityError as exc:
        raise _stall_conflict(exc) from exc
    if updated is None:
        raise _not_found()

    return await _detail_or_404(repo, stall_id)


@router.post(
    "/{stall_id}/category",
    status_code=status.HTTP_201_CREATED,
    response_class=Response,
)
async def set_stall_category(
    stall_id: UUID,
    payload: StallCategoryRequest,
    principal: StallManagerDep,
    session: TenantSessionDep,
) -> Response:
    """Rastaga YANGI toifa davrini yozadi (`STALL_MANAGE`, D-04).

    BITTA RUXSAT ETILGAN TARMOQ: `valid_from` KELAJAKDA bo'lsa -> 201.
    Aks holda (bugun yoki o'tmish) -> **403** `category_period_past_locked`.
    Darvoza ILOVA qatlamida va u DB triggeri bilan almashtirib bo'lmaydi —
    to'liq sabab `StallRepository.set_category()` docstringida.

    JAVOB TANASIZ (201 + bo'sh): yangi davr KELAJAKDA kuchga kiradi, ya'ni
    `StallDetail` (bugungi holat) uni ko'rsatmasdi va klient "yozildimi?"
    degan savolga noto'g'ri javob olardi.

    409 `category_period_exists` — shu sanaga davr allaqachon bor;
    404 — rasta yoki toifa begona bozorniki hamda mavjud emas.
    """
    repo = StallRepository(session, _market_id(principal))
    try:
        written = await repo.set_category(
            stall_id,
            category_id=payload.category_id,
            valid_from=payload.valid_from,
        )
    except CategoryPeriodPastError as exc:
        log.info("category_period_past_locked", valid_from=str(payload.valid_from))
        raise _past_locked() from exc
    except IntegrityError as exc:
        raise _category_period_conflict(exc) from exc

    if not written:
        raise _not_found()
    return Response(status_code=status.HTTP_201_CREATED)
