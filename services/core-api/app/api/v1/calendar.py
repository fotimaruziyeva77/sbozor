"""Ish kunlari kalendari (MARKET-05) — SC#4 ning admin boshqaradigan yuzasi.

=============================================================================
BU YERDA "BOZOR OCHIQMI?" SAVOLI HISOBLANMAYDI.

SC#4 ning butun qarori `market_is_open(market_id, date)` DB funksiyasida
va 6-fazaning kunlik job'i unga BITTA shart sifatida murojaat qiladi::

    WHERE market_is_open(:market_id, :business_date)

Bu router faqat o'sha funksiya O'QIYDIGAN ikkita manbani boshqaradi:
`market_profile.open_weekdays` (haftalik jadval, D-17) va
`market_calendar_exceptions` (alohida kunlar, D-18). Javob semantikasi
funksiyaga MOS bo'lishi shart, lekin takrorlanmaydi — ikkinchi nusxa bir
kun ajralib ketardi va ekran "ochiq" deb turgan kunga hisob yozilmasdi.

`test_holiday_exception_closes_the_day` aynan shu bog'lanishni o'lchaydi:
u API orqali YOZADI va `market_is_open()` orqali O'QIYDI.
=============================================================================

KIM O'ZGARTIRADI — `STALL_MANAGE` (A5/A6, RESEARCH Open Question 4).

Kalendar bozor ma'muriyatining kundalik ishi (bayram e'lon qilish, maxsus
savdo kuni), ya'ni u alohida huquq talab qilmaydi. Maker-checker (ikkinchi
tasdiqlovchi) v2 ga qoldirildi va uning o'rniga MAJBURIY audit qo'yildi:
yopiq kun belgilash o'sha kunning BUTUN yig'imini hisobdan chiqaradi va bu
jadvalda pul ustuni yo'q, ya'ni moliyaviy audit uni umuman qamramaydi.

O'QISH esa `MARKET_DATA_VIEW`: direktor kalendarni KO'RADI (hisobotlarida
"nega bu kun bo'sh?" savoli aynan shundan javob oladi), lekin
o'zgartira olmaydi (D-07). `test_director_cannot_change_calendar` shu
chegarani nazorat holati bilan qulflaydi.

CROSS-TENANT JAVOB — HAR DOIM 404 (T-02-67), 403 EMAS.

-----------------------------------------------------------------------------
AUDIT BU YERDA YOZILMAYDI VA BU ATAYIN.

`market_profile` ham, `market_calendar_exceptions` ham `AUDITED_TABLES` da
va DB-trigger ostida (02-05/02-06). Ya'ni oddiy `UPDATE`/`INSERT`/`DELETE`
o'zi audit qatorini tug'diradi. App-qatlam yozuvi qo'shilsa har
o'zgarish uchun IKKITA qator paydo bo'lardi va jurnalni o'qiyotgan odam
"nima ikki marta sodir bo'ldi?" degan savol bilan qolardi.

Trigger `old`/`new` farqini O'ZI hisoblaydi va `changed_keys` ga
`open_weekdays` ni qo'yadi, ya'ni "eski qiymatni yozuvdan OLDIN o'qish"
qoidasi ham bu yerda emas — u faqat app-qatlam yozuvlariga tegishli
(`users.py`).
-----------------------------------------------------------------------------

XATO XARITASI:

    MarketProfileMissingError   ->  409 market_incomplete
    23505                       ->  409 calendar_exception_exists
    topilmadi / begona bozor    ->  404 not_found
"""

from __future__ import annotations

from datetime import date
from typing import Annotated
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sbozor_core.timeutil import business_today
from sqlalchemy.exc import IntegrityError

from app.deps import Principal, TenantSessionDep, require_permission
from app.repositories.calendar_repo import CalendarExceptionRow, CalendarRepository
from app.repositories.stall_repo import MarketProfileMissingError, sqlstate_of
from app.schemas import (
    CalendarException,
    CalendarExceptionRequest,
    CalendarResponse,
    WeekdaysRequest,
)
from app.security.rbac import Permission

# `UUID` va `date` ish paytida kerak: FastAPI yo'l/query parametrlarining
# annotatsiyasini `get_type_hints` bilan o'qiydi (`zones.py` dagi sabab).
log = structlog.get_logger(__name__)

router = APIRouter(tags=["calendar"])

StallManagerDep = Annotated[Principal, Depends(require_permission(Permission.STALL_MANAGE))]
MarketDataViewerDep = Annotated[Principal, Depends(require_permission(Permission.MARKET_DATA_VIEW))]

_NOT_FOUND = "not_found"
_EXCEPTION_EXISTS = "calendar_exception_exists"
_MARKET_INCOMPLETE = "market_incomplete"

UNIQUE_VIOLATION = "23505"
"""Bir sanaga ikkinchi istisno — `uq_market_calendar_exceptions_market_id_exception_date`.

Bu unikalik `market_is_open()` ning ISHLASH SHARTI, shunchaki tozalik
emas: ikkita qator bo'lsa funksiyaning skalyar subquery'si "more than one
row returned by a subquery" bilan yiqilardi va BUTUN kunlik hisob-kitob
bitta takroriy qator sababli to'xtardi (02-07 da o'lchangan).
"""

CALENDAR_LIMIT_DEFAULT = 200
CALENDAR_LIMIT_MAX = 500
"""`GET /calendar?limit=` chegaralari (T-02-68).

Chegarasiz so'rov yildan-yilga o'sadigan butun istisno tarixini bitta
JSON'ga aylantirardi. Ro'yxat baribir JORIY YILDAN boshlab kesiladi
(`CalendarRepository.list_exceptions()`), ya'ni standart 200 amaliy
holatda hech qachon to'lmaydi — u yuqori chegara, sahifa o'lchami emas.
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
    """Cross-tenant va mavjud bo'lmagan istisno uchun BIR XIL javob (T-02-67)."""
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_NOT_FOUND)


def _incomplete(exc: Exception, market_id: UUID) -> HTTPException:
    """`market_profile` qatori yo'q -> 409 `market_incomplete`.

    Bu holat 02-11 dan KEYIN yaratilgan bozorda uchramaydi:
    `market_create()` profilni bozor bilan BIR TRANZAKSIYADA yozadi. U
    faqat qo'lda kiritilgan yoki chala ko'chirilgan ma'lumot uchun.
    """
    log.warning("market_profile_missing", market_id=str(market_id), error=str(exc))
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_MARKET_INCOMPLETE)


def _conflict(exc: IntegrityError) -> HTTPException:
    """`IntegrityError` -> aniq `detail` kodi.

    Noma'lum SQLSTATE QAYTA KO'TARILADI (`main.py` global handleri uni 500
    ga aylantiradi) — `zones.py` / `stalls.py` bilan bir xil qaror: "har
    ehtimolga qarshi" 409 yangi konstraytni jimgina noto'g'ri xabar bilan
    yashirardi.
    """
    state = sqlstate_of(exc)
    if state == UNIQUE_VIOLATION:
        log.info("calendar_exception_exists", sqlstate=state)
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_EXCEPTION_EXISTS)
    raise exc


def _exception(row: CalendarExceptionRow) -> CalendarException:
    return CalendarException(
        id=row.id,
        exception_date=row.exception_date,
        is_open=row.is_open,
        note=row.note,
    )


def _year_start() -> date:
    """Istisnolar ro'yxatining quyi chegarasi — JORIY yilning 1-yanvari.

    Yil `business_today()` dan olinadi, `date.today()` dan EMAS:
    konteynerlar UTC soatida ishlaydi va mahalliy 00:00–04:59 oralig'ida
    `date.today()` OLDINGI kunni beradi — 1-yanvar tunida esa bu OLDINGI
    YIL degani, ya'ni chegara bir yilga surilib ketardi.

    Bu qiymat DARVOZA emas, ekranni eskirgan tarix bilan to'ldirmaslik
    uchun filtr. Yuqori chegara YO'Q — kelajakdagi bayramlar (jumladan
    keyingi yilning yanvari) ro'yxatda qoladi.
    """
    return date(business_today().year, 1, 1)


@router.get("", response_model=CalendarResponse)
async def get_calendar(
    principal: MarketDataViewerDep,
    session: TenantSessionDep,
    limit: Annotated[int, Query(ge=1, le=CALENDAR_LIMIT_MAX)] = CALENDAR_LIMIT_DEFAULT,
) -> CalendarResponse:
    """Haftalik jadval + istisno kunlar (`MARKET_DATA_VIEW`, D-17/D-18).

    Profil QATORI yo'q bo'lsa 409 `market_incomplete`: yozadigan joy ham
    yo'q, ya'ni bo'sh javob foydalanuvchini ishlamaydigan ekranga qamab
    qo'yardi.

    Profil bor, LEKIN jadval hali tanlanmagan bo'lsa (`open_weekdays`
    ustuni `NULL` — 0011 dan keyingi normal holat) javob `[]` bo'ladi va
    bu 409 EMAS. Bo'sh ro'yxat NOANIQ emas: `'{}'` DB darajasida
    taqiqlangan, ya'ni `[]` faqat "hali tanlanmagan" degani. 7-qadamdagi
    `WeekdayPicker` shu holatda belgisiz katakchalar bilan ochiladi va
    foydalanuvchi tanlovni AYNAN shu ekranda yozadi.
    """
    market_id = _market_id(principal)
    repo = CalendarRepository(session, market_id)
    try:
        profile = await repo.profile()
    except MarketProfileMissingError as exc:
        raise _incomplete(exc, market_id) from exc

    rows = await repo.list_exceptions(since=_year_start(), limit=limit)
    return CalendarResponse(
        open_weekdays=profile.open_weekdays,
        exceptions=[_exception(row) for row in rows],
    )


@router.put("/weekdays", response_model=CalendarResponse)
async def set_weekdays(
    payload: WeekdaysRequest,
    principal: StallManagerDep,
    session: TenantSessionDep,
) -> CalendarResponse:
    """Haftalik ish jadvalini yozadi (`STALL_MANAGE`, D-17).

    Qiymat `WeekdaysRequest` da tekshiriladi va u UCH holatni rad etadi
    (hammasi 422): bo'sh massiv, `1..7` dan tashqari raqam va TAKRORIY
    kun. Uchalasi ham DB'dagi `open_weekdays_valid` konstraytining jufti,
    lekin ilova chegarasida ham kerak — konstrayt buzilganda javob 500
    bo'lardi va foydalanuvchi nima noto'g'ri ekanini bilmasdi.

    Javob TO'LIQ kalendar (`CalendarResponse`): klient `PUT` dan keyin
    `GET` qilmasdan ekranni yangilaydi va istisnolar ro'yxati ham
    o'zgarmagani ko'rinadi.
    """
    market_id = _market_id(principal)
    repo = CalendarRepository(session, market_id)
    updated = await repo.set_weekdays(payload.open_weekdays)
    if updated is None:
        raise _incomplete(
            MarketProfileMissingError(f"market_profile topilmadi: {market_id}"),
            market_id,
        )

    rows = await repo.list_exceptions(since=_year_start(), limit=CALENDAR_LIMIT_DEFAULT)
    return CalendarResponse(
        open_weekdays=payload.open_weekdays,
        exceptions=[_exception(row) for row in rows],
    )


@router.post("/exceptions", status_code=status.HTTP_201_CREATED, response_model=CalendarException)
async def add_exception(
    payload: CalendarExceptionRequest,
    principal: StallManagerDep,
    session: TenantSessionDep,
) -> CalendarException:
    """Alohida kunni ochiq yoki yopiq deb belgilaydi (`STALL_MANAGE`, D-18).

    Istisno haftalik jadvaldan HAR DOIM ustun turadi va ikkala yo'nalish
    ham ma'noli: `is_open=false` — bayram, `is_open=true` — dam olish
    kunidagi maxsus savdo.

    Javobda `id` QAYTARILADI — usiz klient endigina qo'shgan istisnoni
    o'chirish uchun butun ro'yxatni qayta so'rashga majbur bo'lardi.

    409 `calendar_exception_exists` — o'sha sanaga istisno allaqachon bor.
    """
    repo = CalendarRepository(session, _market_id(principal))
    try:
        exception_id = await repo.add_exception(
            exception_date=payload.exception_date,
            is_open=payload.is_open,
            note=payload.note,
        )
    except IntegrityError as exc:
        raise _conflict(exc) from exc

    return CalendarException(
        id=exception_id,
        exception_date=payload.exception_date,
        is_open=payload.is_open,
        note=payload.note,
    )


@router.delete(
    "/exceptions/{exception_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def delete_exception(
    exception_id: UUID,
    principal: StallManagerDep,
    session: TenantSessionDep,
) -> Response:
    """Istisnoni bekor qiladi — kun HAFTALIK QOIDAGA qaytadi (`STALL_MANAGE`).

    O'chirish `audit_log` da iz qoldiradi (`DELETE` ham trigger ostida,
    T-02-40): istisnoni qo'yib, kun o'tgach uni o'chirib tashlash izni
    yo'qotishning eng oddiy usuli bo'lardi.
    """
    repo = CalendarRepository(session, _market_id(principal))
    if not await repo.delete_exception(exception_id):
        raise _not_found()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
