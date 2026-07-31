"""Rasta ↔ sotuvchi biriktirish davrlari (MARKET-04) — 6-fazadagi qarz egaligining manbai.

=============================================================================
IKKITA ROUTER, IKKITA PREFIKS — VA BU ATAYIN.

    router        ->  {API_V1_PREFIX}/assignments   POST "", PATCH "/{id}"
    stall_router  ->  {API_V1_PREFIX}                GET "/stalls/{id}/assignments"

`GET /api/v1/stalls/{stall_id}/assignments` marshruti RESURS jihatidan
biriktirish domeniga tegishli (u `AssignmentItem` qaytaradi va shu
fayldagi xato semantikasini baham ko'radi), lekin YO'LI rasta ostida
yashaydi. Uni bitta routerga qo'shib bo'lmaydi: `router` `/assignments`
prefiksi bilan ulanadi va o'sha prefiks ostida `/stalls/...` yo'li
`/api/v1/assignments/stalls/...` bo'lib chiqardi.

Uni `stalls_router` ga qo'yish ham noto'g'ri bo'lardi: o'shanda rasta
reestri biriktirish repozitoriysiga va shu fayldagi xato xaritasiga
bog'lanib qolardi, ya'ni ikki domen bitta modulda qorishardi.

Shuning uchun IKKINCHI router `{API_V1_PREFIX}` ga (prefikssiz) ulanadi
va yo'lni to'liq o'zi e'lon qiladi. `stalls_router` bilan TO'QNASHUV
YO'Q: `/api/v1/stalls/{stall_id}` va `/api/v1/stalls/{stall_id}/
assignments` turli segment sonига ega.
=============================================================================

ALMASHINUV OQIMI IKKI CHAQIRUVDAN IBORAT VA QULAYLIK ENDPOINTI
ATAYIN QILINMADI:

    1. PATCH /assignments/{eski}   {"to_date": "2026-08-10"}
    2. POST  /assignments          {"from_date": "2026-08-10", ...}

`[)` chegarasi tufayli almashinuv KUNI YANGI sotuvchiga tegishli bo'ladi
va o'sha kunning pattasi unga yoziladi (D-10). Eski sotuvchining
o'tmishdagi qarzi esa JOYIDA qoladi — davrni yopish hech qanday
`daily_charges` qatoriga tegmaydi.

`POST /assignments/{id}/handover` shaklidagi bitta-chaqiruvli qulaylik
endpointi ATAYIN yo'q: u ikki alohida audit yozuvini bittaga siqib,
"kim qachon nima qildi" javobini xiralashtirardi (T-02-72). Ikki
chaqiruv — ikki iz, va nizoda aynan shu ikki iz kerak bo'ladi.

BO'SHLIQ XATO EMAS (D-11). Davrlar uzluksizligi HECH QAYERDA
majburlanmaydi: `GET /stalls/{id}/assignments` sotuvchisiz rasta uchun
bo'sh ro'yxat qaytaradi va bu 6-faza topadigan "band, lekin sotuvchisiz"
anomaliyasining boshlanish nuqtasi. "Noma'lum sotuvchi" texnik hisobi
YARATILMAYDI (D-11).

O'QISH VA YOZISH HUQUQLARI AJRATILGAN (D-07): yozuv uchun
`VENDOR_MANAGE`, o'qish uchun `MARKET_DATA_VIEW`. Direktorda birinchisi
YO'Q — u kim qayerda savdo qilayotganini KO'RADI (hisobotlari shunsiz
ma'nosiz), lekin biriktirishni surib qarz egaligini o'zgartira olmaydi
(T-02-76).

CROSS-TENANT JAVOB — HAR DOIM 404 (T-02-74), 403 EMAS.

-----------------------------------------------------------------------------
XATO XARITASI — FAQAT `sqlstate` BO'YICHA (`constraint_name` asyncpg
o'ramida `None`, RLS esa `DETAIL` ni o'chiradi — Pitfall 4):

    23P01 (EXCLUDE)          ->  409 assignment_period_overlaps
    23503 (composite FK)     ->  404 (begona bozorning stall_id/vendor_id)
    23514 (lower_bound_...)  ->  422 invalid_period
    ValueError (period)      ->  422 invalid_period
    yopilgan davrni yopish   ->  409 assignment_not_open

⚠ 409 JAVOBIDA "QAYSI DAVR BILAN KESISHDI" YO'Q VA UNI QO'SHIB BO'LMAYDI.
RLS yoqilgan jadvalda PostgreSQL konstrayt buzilishining `DETAIL`
qatorini BUTUNLAY o'chiradi (empirik, Pitfall 4) — ya'ni to'qnashgan
davrni DB xatosidan olib bo'lmaydi. UI aniqroq xabar xohlasa, u
`GET /stalls/{id}/assignments` bilan mavjud davrlarni O'ZI ko'rsatadi;
server esa xom xato matnini javobga HECH QACHON qo'ymaydi (T-02-75).
-----------------------------------------------------------------------------

AUDIT BU YERDA YOZILMAYDI: `stall_assignments` `AUDITED_TABLES` da va
`fn_audit_row()` triggeri ostida (02-06). Davr o'zgarishi `old`/`new`
farqida `period` kaliti bilan ko'rinadi — aynan shu yozuv "qarzni kim
boshqa sotuvchiga o'tkazdi" savoliga javob beradi (T-02-72). App-qatlam
yozuvi qo'shilsa har amal uchun IKKITA qator paydo bo'lardi.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.deps import Principal, TenantSessionDep, require_permission
from app.repositories.stall_repo import sqlstate_of
from app.repositories.vendor_repo import AssignmentRepository, AssignmentRow
from app.schemas import (
    AssignmentCloseRequest,
    AssignmentCreateRequest,
    AssignmentItem,
    AssignmentListResponse,
)
from app.security.rbac import Permission

# `UUID` ish paytida kerak — FastAPI yo'l parametrlarining annotatsiyasini
# `get_type_hints` bilan o'qiydi (`zones.py` dagi bilan bir xil sabab).
log = structlog.get_logger(__name__)

router = APIRouter(tags=["assignments"])
stall_router = APIRouter(tags=["assignments"])
"""Rasta ostidagi biriktirish yo'li — sabab modul docstringida (prefiks farqi)."""

VendorManagerDep = Annotated[Principal, Depends(require_permission(Permission.VENDOR_MANAGE))]
MarketDataViewerDep = Annotated[Principal, Depends(require_permission(Permission.MARKET_DATA_VIEW))]

_NOT_FOUND = "not_found"
_OVERLAPS = "assignment_period_overlaps"
_NOT_OPEN = "assignment_not_open"
_INVALID_PERIOD = "invalid_period"

EXCLUSION_VIOLATION = "23P01"
"""`ex_stall_assignments_no_overlap` — bir rastada davrlar kesishdi (D-09).

Bu SQLSTATE bu yo'lda BOSHQA hech qanday ma'no bermaydi: jadvalda yagona
`EXCLUDE` konstrayti shu. Ya'ni uni ko'rish AYNAN "shu rastada bu
kunlarda boshqa sotuvchi bor" degani.
"""

FK_VIOLATION = "23503"
"""Begona bozorning (yoki mavjud bo'lmagan) `stall_id` / `vendor_id` si.

Composite FK (`(market_id, stall_id)`, `(market_id, vendor_id)`)
cross-tenant biriktirishni STRUKTURA bilan imkonsiz qiladi — ilova
tekshiruvi bu yerda ikkinchi qatlam, birinchisi emas (T-02-74).
"""

CHECK_VIOLATION = "23514"
"""`lower_bound_required` — quyi chegarasiz davr.

⚠ Bu tarmoq amalda ERISHIB BO'LMAYDIGAN: `assignment_period(start: date,
...)` sanani MAJBURIY oladi, ya'ni quyi chegarasiz davr bu yo'ldan
umuman chiqmaydi. Xarita baribir yozilgan, chunki konstrayt xom SQL
yo'lini ham qamraydi va kelajakda boshqa chaqiruvchi paydo bo'lsa javob
500 emas, tushunarli 422 bo'lishi kerak.
"""


def _market_id(principal: Principal) -> UUID:
    """Tanlangan bozor (`zones.py` / `tariffs.py` dagi jufti bilan aynan bir xil)."""
    if principal.market_id is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="market_not_selected",
        )
    return principal.market_id


def _not_found() -> HTTPException:
    """Cross-tenant va mavjud bo'lmagan obyekt uchun BIR XIL javob (T-02-74)."""
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_NOT_FOUND)


def _invalid_period(exc: ValueError) -> HTTPException:
    """Davr chegaralari mantiqsiz (`to_date <= from_date`) -> 422.

    403 EMAS: mavjud qatorga huquq masalasi umuman qo'yilmayapti — rad
    etilayotgani so'rovning O'Z shakli (`tariffs.py::_not_future()` bilan
    bir xil mulohaza).

    Xato MATNI javobga chiqmaydi, faqat log'ga: `assignment_period()`
    xabari ichki konvensiyani (`[)`) tushuntiradi va u foydalanuvchiga
    emas, dasturchiga qaratilgan.
    """
    log.info("assignment_invalid_period", error=str(exc))
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail=_INVALID_PERIOD,
    )


def _write_conflict(exc: IntegrityError) -> HTTPException:
    """`stall_assignments` yo'lidagi `IntegrityError` -> aniq `detail` kodi.

    Noma'lum SQLSTATE QAYTA KO'TARILADI (`main.py` global handleri uni 500
    ga aylantiradi): "har ehtimolga qarshi" 409 yangi konstraytni jimgina
    noto'g'ri xabar bilan yashirardi (`stalls.py` / `tariffs.py` bilan bir
    xil qaror).
    """
    state = sqlstate_of(exc)
    if state == EXCLUSION_VIOLATION:
        log.info("assignment_period_overlaps", sqlstate=state)
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_OVERLAPS)
    if state == FK_VIOLATION:
        log.info("assignment_reference_not_found", sqlstate=state)
        return _not_found()
    if state == CHECK_VIOLATION:
        log.info("assignment_invalid_period", sqlstate=state)
        return HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=_INVALID_PERIOD,
        )
    raise exc


def _item(row: AssignmentRow) -> AssignmentItem:
    """Repozitoriy qatorini javob elementiga o'giradi."""
    return AssignmentItem(
        id=row.id,
        stall_id=row.stall_id,
        stall_code=row.stall_code,
        vendor_id=row.vendor_id,
        vendor_name=row.vendor_name,
        from_date=row.from_date,
        to_date=row.to_date,
    )


async def _row_or_404(repo: AssignmentRepository, assignment_id: UUID) -> AssignmentItem:
    """Yozuvdan KEYINGI javob — bitta joyda.

    Javob AYNAN o'qish yo'lidan quriladi, ya'ni klient `POST`/`PATCH` dan
    keyin `GET /stalls/{id}/assignments` qilganda boshqa shakl ko'rmaydi
    (`tariffs.py::_row_or_404()` bilan bir xil qoida). `stall_code` va
    `vendor_name` ham shu tufayli javobda bor — ular yozuv paytida
    so'rov tanasida yo'q edi.
    """
    row = await repo.get(assignment_id)
    if row is None:  # pragma: no cover - o'sha tranzaksiyada yo'qolishi mumkin emas
        raise _not_found()
    return _item(row)


@router.post("", status_code=status.HTTP_201_CREATED, response_model=AssignmentItem)
async def create_assignment(
    payload: AssignmentCreateRequest,
    principal: VendorManagerDep,
    session: TenantSessionDep,
) -> AssignmentItem:
    """Rastaga sotuvchi biriktiradi (`VENDOR_MANAGE`, D-09).

    `to_date` berilmasa davr OCHIQ qoladi — bu odatiy holat: sotuvchi
    qachongacha ishlashini oldindan hech kim bilmaydi.

    409 `assignment_period_overlaps` — shu rastada bu kunlarda boshqa
    davr bor (DB `EXCLUDE`); QAYSI davr ekani javobda YO'Q va sabab modul
    docstringida.
    404 — `stall_id` yoki `vendor_id` begona bozorniki yoxud mavjud emas.
    422 `invalid_period` — `to_date` `from_date` dan keyin kelmadi.
    """
    repo = AssignmentRepository(session, _market_id(principal))
    try:
        assignment_id = await repo.create(
            stall_id=payload.stall_id,
            vendor_id=payload.vendor_id,
            from_date=payload.from_date,
            to_date=payload.to_date,
        )
    except ValueError as exc:
        raise _invalid_period(exc) from exc
    except IntegrityError as exc:
        raise _write_conflict(exc) from exc

    return await _row_or_404(repo, assignment_id)


@router.patch("/{assignment_id}", response_model=AssignmentItem)
async def close_assignment(
    assignment_id: UUID,
    payload: AssignmentCloseRequest,
    principal: VendorManagerDep,
    session: TenantSessionDep,
) -> AssignmentItem:
    """OCHIQ davrni yopadi (`VENDOR_MANAGE`, D-10 — almashinuvning 1-qadami).

    =========================================================================
    YOPILGAN DAVRNI QAYTA OCHISH YO'LI YO'Q va u ATAYIN qo'yilmagan.

    Yopilgan davr — o'tmish: uning kunlariga 6-faza allaqachon patta
    yozgan bo'lishi mumkin. Yuqori chegarani orqaga surish o'sha kunlarni
    JIMGINA boshqa sotuvchiga o'tkazardi va qarzdorlik reestri sababsiz
    o'zgarardi (T-02-72). Xato bilan yopilgan davrni tuzatishning yagona
    ko'rinadigan yo'li — yangi davr ochish, ya'ni ikkinchi audit izi.
    =========================================================================

    409 `assignment_not_open` — davr allaqachon yopiq;
    404 — davr mavjud emas yoki begona bozorniki;
    422 `invalid_period` — `to_date` davr boshidan keyin kelmadi
    (`[)` konvensiyasida bir kunlik biriktirish uchun `to_date` ERTASI
    kuni bo'ladi).
    """
    repo = AssignmentRepository(session, _market_id(principal))

    # AVVAL O'QISH, KEYIN YOZISH: "topilmadi" (404) va "yopiq" (409)
    # ikki xil javob, bitta shartli `UPDATE` esa ikkalasini ham "0 qator"
    # bo'lib qaytarardi.
    period = await repo.period_of(assignment_id)
    if period is None:
        raise _not_found()
    if period.upper is not None:
        log.info("assignment_not_open", assignment_id=str(assignment_id))
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_NOT_OPEN)

    # `lower` `None` bo'la olmaydi — `lower_bound_required` konstrayti
    # (02-06) buni DB darajasida imkonsiz qiladi; tekshiruv mypy uchun.
    from_date = period.lower
    if from_date is None:  # pragma: no cover - konstrayt buni yozdirmaydi
        raise _invalid_period(ValueError("davrning quyi chegarasi yo'q"))

    try:
        closed = await repo.close(assignment_id, from_date=from_date, to_date=payload.to_date)
    except ValueError as exc:
        raise _invalid_period(exc) from exc
    except IntegrityError as exc:
        raise _write_conflict(exc) from exc

    if not closed:  # pragma: no cover - o'sha tranzaksiyada yo'qolishi mumkin emas
        raise _not_found()
    return await _row_or_404(repo, assignment_id)


@stall_router.get("/stalls/{stall_id}/assignments", response_model=AssignmentListResponse)
async def list_stall_assignments(
    stall_id: UUID,
    principal: MarketDataViewerDep,
    session: TenantSessionDep,
) -> AssignmentListResponse:
    """Rastaning biriktirish TARIXI (`MARKET_DATA_VIEW`, eng yangisi birinchi).

    ⚠ RASTA MAVJUDLIGI ALOHIDA TEKSHIRILADI. Usiz begona bozorning
    rastasi uchun ham bo'sh 200 qaytardi (RLS natijani baribir bo'shatadi)
    va cross-tenant da'vosi (404, T-02-74) shu marshrutda JIMGINA
    bajarilmasdi — matritsa esa hech nima sezmasdi, chunki javob
    strukturaviy jihatdan to'g'ri ko'rinardi.

    BO'SH RO'YXAT — NORMAL HOLAT (D-11): rasta hech qachon
    biriktirilmagan bo'lishi ham, davrlar orasida bo'shliq bo'lishi ham
    mumkin. Bu 404 EMAS: rasta MAVJUD, faqat sotuvchisi yo'q.
    """
    repo = AssignmentRepository(session, _market_id(principal))
    if not await repo.stall_exists(stall_id):
        raise _not_found()

    rows = await repo.list_for_stall(stall_id)
    return AssignmentListResponse(items=[_item(row) for row in rows])
