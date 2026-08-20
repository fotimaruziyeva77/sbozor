"""Kutilayotgan patta va yozilgan hisob — KASSIR va DIREKTORNING O'QISH yuzasi.

=============================================================================
⛔⛔ IKKI HUQUQ, IKKI IMZO ALIASI — VA `require_any_permission()`
    ISHLATILMAYDI (C-9).

`tests/tenancy/test_personal_data_coverage.py:691-706` o'sha darvozani
ko'targan marshrutlar to'plamini AYNAN
`("/api/v1/snapshots/{snapshot_id}/image",)` ga TENG bo'lishini talab
qiladi — ya'ni to'plam YOPIQ va bu fayl unga tegmaydi.

Kassir va direktor bitta marshrutni bo'lishishi kerak bo'lganda yechim
BITTA HUQUQNI BIR NECHA ROLGA berish (`billing_collect_view` aynan
shunday: `cashier`, `market_admin`, `director`), «yo P yo Q» EMAS.
Farq ma'noda: `require_permission(P)` — «bu resursni P egasi ko'radi»;
`require_any_permission(P, Q)` — «bu resursni IKKI XIL ish uchun IKKI XIL
odam ko'radi». Ikkinchisi bu yerda YOLG'ON bo'lardi — kassir ham,
direktor ham AYNI savolga («bugun qancha patta kutilyapti?») javob
oladi.

=============================================================================
⛔ HUQUQ IMZODA, DEKORATORDA EMAS — VA `audit_read(...)` YO'Q.

`cameras.py:24-42` / `assignments.py:93-99` dagi dekorator shakli
`audit_read` BOR bo'lganda ishlatiladi. 6-fazada u KERAK EMAS va sabab
o'lchangan: UI-SPEC §5.5 ga ko'ra bu fazaning BIRORTA yangi marshruti
`PERSONAL_FIELDS = {vendor_name, phone, full_name}` dan bittasini ham
qaytarmaydi. Sotuvchi nomi ekranda MAVJUD, AUDIT QILINGAN `GET /vendors`
dan olinib KLIENTDA joinlanadi (§5.5), kassir nomi esa `GET /users` dan.

⛔ DARVOZANI NOM BILAN AYLANIB O'TISH TAQIQLANADI: `vendor_label`,
   `payer`, `who` — hech biri. C-10 buni ochiq aytadi.

=============================================================================
⛔⛔ `charge_id` PROYEKSIYA JAVOBIDA UMUMAN E'LON QILINMAGAN (D-17).

Proyeksiya HISOB EMAS: hisob D+1 04:10 da tug'iladi (C-3). Ya'ni bugungi
kun uchun hisob identifikatori MAVJUD EMAS — u yashirilgan emas. Mexanizm
`app/schemas.py::PendingStallResponse` da va u `BlindItemResponse`
naqshining aynan takrori.

=============================================================================
⚠ HANDLERLAR PUL MANTIG'I YOZMAYDI (D-16).

Har javob `app/repositories/billing_repo.py` dan keladi:
`pending_projection()`, `charge_list()`, `charge_detail()`,
`anomaly_list()`. Summani bu yerda hisoblash «kassir ko'rgan son» bilan
«kechqurun yozilgan son» ni ajratib yuborardi — bu loyihada takroran
topilgan «ikki haqiqat manbai» sinfi.
=============================================================================
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Annotated
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sbozor_core.timeutil import business_today

from app.deps import Principal, TenantSessionDep, require_permission
from app.repositories import billing_repo
from app.schemas import (
    AnomalyListResponse,
    AnomalyRowResponse,
    ChargeAdjustmentRow,
    ChargeDetailResponse,
    ChargeEvidenceRow,
    ChargeListResponse,
    ChargeRowResponse,
    MapDayStatusResponse,
    MapDayStatusRow,
    PendingLookupResponse,
    PendingMarketResponse,
    PendingStallResponse,
)
from app.security.rbac import Permission
from app.services.billing_errors import AMOUNT_UNAVAILABLE, STALL_NOT_FOUND

# ⚠ `date` VA `UUID` ISH VAQTIDA IMPORT QILINADI, `TYPE_CHECKING` OSTIDA
#   EMAS — VA BU O'LCHANGAN ZARURIYAT (`occupancy.py:70-75` va
#   `reviews.py` da ham aynan shunday). `from __future__ import
#   annotations` ostida annotatsiyalar SATR bo'lib qoladi va FastAPI
#   ularni Pydantic uchun YECHA olmaydi: `PydanticUserError: ... is not
#   fully defined`. Nosozlik marshrutda emas, OpenAPI sxemasini quruvchi
#   meta-testda ko'rinadi.

log = structlog.get_logger(__name__)

__all__ = ["router"]

router = APIRouter(tags=["billing"])

CollectViewerDep = Annotated[
    Principal, Depends(require_permission(Permission.BILLING_COLLECT_VIEW))
]
"""⛔ `REPORT_VIEW` EMAS — VA BU FARQ MAHSULOT QARORI.

Kassirda `report_view` YO'Q va berilmaydi (UI-SPEC §5.6): u hisobot
o'qimaydi. Lekin kutilayotgan pattani u HAR KUNI ko'radi — bu uning
ishining O'ZI. Shuning uchun huquq alohida (`billing_collect_view`) va u
UCH ROLGA berilgan: `cashier`, `market_admin`, `director`.

⚠ Direktor ham shu marshrutdan o'tadi (§9.5 bozor kesimi), ya'ni
  matritsada bu marshrut ODATDAGI sessiyadan yuradi va `INSPECTOR_ROUTES`
  sinfidagi alohida ro'yxat KERAK EMAS.
"""

ReportViewerDep = Annotated[Principal, Depends(require_permission(Permission.REPORT_VIEW))]
"""⛔ `BILLING_COLLECT_VIEW` EMAS. Yozilgan hisob, tuzatish va anomaliya —
DIREKTORNING yuzasi; kassir ularni ko'rmaydi (§5.6, `occupancy.py:83-84`
bilan aynan bir xil shakl)."""


_NOT_FOUND = "not_found"
"""Cross-tenant va mavjud bo'lmagan obyekt uchun BIR XIL javob (T-01-76).

⚠ `MARKET_ERROR_CODES` REYESTRIGA QO'SHILMAYDI va bu `assignments.py:149`
  / `reviews.py:211` bilan aynan bir xil qaror: reyestr DOMEN kodlari
  uchun («bu amalni nega bajarib bo'lmadi»), bu esa STRUKTURAVIY javob
  va u hech qanday yo'l ko'rsatmaydi — ko'rsatishi ham mumkin emas.
"""

_DAY_IN_FUTURE = "day_in_future"
"""Kelajak kuni uchun hisobot so'raldi (**422**).

⚠ REYESTRGA QO'SHILMAYDI: `ALL_BILLING_ERROR_CODES` ning soni frontend
  darvozasi (`scripts/error-codes.test.mjs`) tomonidan uchala locale'dagi
  `errorCause`/`errorFix` juftligi bilan SOLISHTIRILADI, ya'ni yangi kod
  matn qo'shilmaguncha o'sha darvozani QIZARTIRARDI. Bu holat esa
  klientda UMUMAN yuz bermaydi: kun tanlagichning maksimumi BUGUN
  (§11.1), ya'ni 422 — sxema chegarasining HTTP jufti, foydalanuvchi
  yo'lidagi holat emas.
"""


def _reject(code: str, http_status: int) -> HTTPException:
    """`detail` ⛔ **SATR**, lug'at EMAS — va bu klient kontrakti.

    =========================================================================
    ⛔⛔ BU YERDA U BIR MARTA O'LCHANGAN NOSOZLIKNING TUZATMASI (CR-04).

    `frontend/src/lib/api-client.ts::detailOf()` `detail` ni AYNAN satr
    deb o'qiydi (`typeof parsed.data.detail === "string"`); lug'at
    yuborilganda u **bo'sh satr** qaytaradi. `/pending` ning 404 i
    lug'at yuborardi, ya'ni:

        `ApiError.detail`                          -> `""`
        `collect-session.tsx::notFound`            -> HAR DOIM `false`
        `collectState()` ning `"not-found"` holati -> O'LIK KOD
        `StallLookup` ning «Rasta topilmadi» shoxi -> HECH QACHON

    va kassir noto'g'ri kod tergan bo'lsa «yuklab bo'lmadi» + [Qayta
    urinish] ko'rardi — har urinish O'SHA 404 ni qaytarardi.

    ⚠ Shakl `payments.py::_reject()` / `shifts.py::_reject()` bilan AYNI
      — uch marshrut oilasida BITTA konvensiya.
    =========================================================================
    """
    return HTTPException(status_code=http_status, detail=code)


_MARKET_NOT_SELECTED = "market_not_selected"
"""Sessiyada bozor tanlanmagan (**403**).

⛔ REYESTRGA QO'SHILMAYDI (`_NOT_FOUND` bilan aynan bir xil sabab):
   `ALL_BILLING_ERROR_CODES` ning soni frontend darvozasi tomonidan
   uchala locale'dagi matn juftligi bilan solishtiriladi. Kod
   `api-types.ts` ning O'Z ro'yxatida ALLAQACHON bor (u 01-fazadan).
"""


def _market_id(principal: Principal) -> UUID:
    """Sessiyadagi bozor — `occupancy.py:100-107` dagi jufti bilan bir xil shakl.

    ⛔ `detail` — **SATR** (`_reject()` docstringi): lug'at shaklida
       `api-client.ts::detailOf()` bo'sh satr qaytaradi va klient kodni
       UMUMAN ko'rmaydi. Bu 01-fazadan meros bo'lgan lug'at shakli edi
       va u «klient yo'lida yuz bermaydi» degan taxminga tayanardi —
       o'sha taxminning ishonchsizligi `/pending` ning 404 ida
       O'LCHANGAN (CR-04).
    """
    market_id = principal.market_id
    if market_id is None:
        raise _reject(_MARKET_NOT_SELECTED, status.HTTP_403_FORBIDDEN)
    return market_id


def _report_day(day: date | None) -> date:
    """Hisobot kunini yechadi — ⛔ STANDARTI KECHA (UI-SPEC §11.1).

    =======================================================================
    ⛔ NEGA BUGUN EMAS.

    C-3 bo'yicha hisob **D+1 04:10** da tug'iladi. Standart kun BUGUN
    bo'lsa sahifa HAR DOIM bo'sh ochilardi va direktor «tizim
    ishlamayapti» degan xulosaga kelardi — ya'ni to'g'ri ishlayotgan
    tizim buzuq bo'lib ko'rinardi. Kecha esa har doim TO'LIQ kun.

    ⛔ KELAJAK KUNI **422**: bu `daily_charges` ning
       `CHECK (service_date <= business_date)` konstraytining HTTP
       qatlamidagi JUFTI. Usiz so'rov bazagacha borib BO'SH ro'yxat
       qaytarardi — ya'ni «kelajakda hisob yo'q» degan MA'NOSIZ javob
       «bu kunda hisob yozilmagan» bilan bir xil ko'rinardi.
    =======================================================================
    """
    today = business_today()
    resolved = today - timedelta(days=1) if day is None else day
    if resolved > today:
        # ⚠ `HTTP_422_UNPROCESSABLE_CONTENT` — RFC 9110 dagi joriy nom
        #   (`audit.py:184-187` da o'rnatilgan qoida). Eski `..._ENTITY`
        #   aliasi Starlette'da DEPRECATED va ogohlantirish beradi.
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=_DAY_IN_FUTURE
        )
    return resolved


@router.get(
    "/pending",
    response_model=PendingStallResponse | PendingLookupResponse | PendingMarketResponse,
)
async def billing_pending(
    principal: CollectViewerDep,
    session: TenantSessionDep,
    stall_code: Annotated[str | None, Query()] = None,
) -> PendingStallResponse | PendingLookupResponse | PendingMarketResponse:
    """Kutilayotgan patta = ⛔ bugungi tarif + eski qarz (BILL-05).

    =======================================================================
    ⛔ UCH SHAKL VA ULAR ARALASHMAYDI:

      `?stall_code=` ANIQ moslik  -> `PendingStallResponse` (tekis, to'qqiz kalit)
      `?stall_code=` KO'P moslik  -> `PendingLookupResponse` (faqat kodlar)
      parametrsiz                 -> `PendingMarketResponse` (bozor kesimi)

    Uchtasini bitta «bo'sh qiymatlar» to'plamiga siqish «summa
    hisoblanmadi» bilan «summa nol» ni ajratmaydigan javob berardi — bu
    esa aynan §9.4 ning oldini olayotgan xatosi.

    ⛔ NOL MOSLIK -> **404 `stall_not_found`**, bo'sh ro'yxat EMAS.
       Bo'sh `matches` bilan 200 qaytarish kassirga «rasta bor, faqat
       ko'rsatilmadi» deb yolg'on aytardi; 06-02 reyestri esa bu holat
       uchun AYNAN shu kodni nomlagan («terish xatosi, yagona to'g'ri
       javob — raqamni qayta kiritish»).
    =======================================================================

    ⛔ SUMMA SERVERDA (D-20 ning kuchli shakli): javobda `tariff_id` ham,
       `category_id` ham, `valid_from` ham YO'Q, ya'ni klientda uni
       qayta hisoblash *taqiqlanmaydi* — IMKONSIZ. `total_due_soum` ham
       shu sababdan serverdan keladi (§9.6).

    ⚠ KUN — `business_today()`, so'rov parametri YO'Q. Proyeksiya
      BUGUNGI patta haqida (BILL-05) va o'tmish kuni uchun «kutilayotgan»
      tushunchasi MA'NOSIZ: o'sha kun uchun yozilgan HISOB bor
      (`GET /billing/charges?day=`), ya'ni ikkinchi yo'l bir savolga ikki
      javob berardi (§9.3 kanal 7).
    """
    market_id = _market_id(principal)
    as_of = business_today()

    projection = await billing_repo.pending_projection(
        session, market_id=market_id, as_of=as_of, stall_code=stall_code
    )

    if stall_code is None:
        market = projection.market
        if market is None:  # pragma: no cover - `pending_projection` kontrakti
            raise _reject(AMOUNT_UNAVAILABLE, status.HTTP_500_INTERNAL_SERVER_ERROR)
        return PendingMarketResponse(
            service_date=as_of,
            market_open=market.market_open,
            pending_amount_soum=market.pending_amount_soum,
            outstanding_soum=market.outstanding_soum,
            pending_stall_count=market.pending_stall_count,
            fetched_at=market.fetched_at,
            row_prefixes=await billing_repo.row_prefixes(
                session, market_id=market_id
            ),
        )

    stall = projection.stall
    if stall is not None:
        return PendingStallResponse(
            stall_code=stall.stall_code,
            service_date=stall.service_date,
            market_open=stall.market_open,
            amount_soum=stall.amount_soum,
            amount_unavailable_reason=stall.amount_unavailable_reason,  # type: ignore[arg-type]
            outstanding_soum=stall.outstanding_soum,
            total_due_soum=stall.total_due_soum,
            stall_status=stall.stall_status,  # type: ignore[arg-type]
            vendor_assigned=stall.vendor_assigned,
        )

    if not projection.matches:
        # ⛔ CR-04: `detail` SATR. Lug'at yuborilganda klientning
        #    `stall_not_found` shoxi UMUMAN ochilmasdi (`_reject()`).
        raise _reject(STALL_NOT_FOUND, status.HTTP_404_NOT_FOUND)

    return PendingLookupResponse(matches=list(projection.matches), stall=None)


@router.get("/map", response_model=MapDayStatusResponse)
async def billing_map_day(
    principal: CollectViewerDep,
    session: TenantSessionDep,
) -> MapDayStatusResponse:
    """Plan-xaritaning BUGUNGI to'lov qatlami — rasta kesimida (MARKET-06).

    =======================================================================
    ⛔⛔ RANG SERVERDA YECHILADI (D-C1) — KLIENT UNI FAQAT CSS SINFIGA
        MAPS QILADI.

    Ustuvorlik qoidasi (`mismatch` > `no_billing` > `free` > `paid` >
    `due`) `billing_repo._map_day_state()` da BITTA sof funksiyada
    yashaydi. Uni klientda takrorlash ikki tilda ikki qoida yaratardi va
    ular BIR KUN ajralib ketardi — o'shanda xaritadagi rang bilan
    hisobotdagi holat farq qilardi, IKKALASI HAM «to'g'ri» bo'lgan holda.

    =======================================================================
    ⛔ HUQUQ — MAVJUD `BILLING_COLLECT_VIEW` (`CollectViewerDep`).

    Egalari: `cashier`, `market_admin`, `director`. Platforma adminida
    YO'Q va bu TO'G'RI: u sozlash roli va unda xarita INVENTAR rejimida
    qoladi. Yolg'on yashil chizishdan ko'ra qatlamni umuman
    ko'rsatmaslik halolroq. ⛔ `ROLE_PERMISSIONS` matritsasiga
    TEGILMAYDI va `require_any_permission()` ISHLATILMAYDI (C-9).

    =======================================================================
    ⛔ `?day=` PARAMETRI YO'Q (D-C5) — VA SABAB `billing_pending` DA
       ALLAQACHON O'LCHANGAN.

    O'tmish kuni uchun YOZILGAN hisob bor (`GET /billing/charges?day=`),
    ya'ni ikkinchi yo'l bir savolga ikki javob berardi. Kun —
    `business_today()`.

    ⚠ ISTISNO: ochiq case'lar KUN BO'YICHA filtrlanmaydi. «Ochiq
      nomuvofiqlik» — BUGUNGI holat, uning `service_date` i esa qatorda
      ALOHIDA qaytadi (`_OPEN_CASE_BY_STALL` docstringi).

    =======================================================================
    ⚠ `audit_read` YOZILMAYDI — `GET /stalls/map` uchun yozilgan
      mulohazaning AYNAN o'zi: javobda shaxsiy ma'lumot yo'q (faqat
      `stall_id` va summalar), har xarita ochilishida esa jurnal shovqin
      bilan to'lardi.
    """
    market_id = _market_id(principal)

    status_rows = await billing_repo.map_day_status(
        session, market_id=market_id, as_of=business_today()
    )

    return MapDayStatusResponse(
        service_date=status_rows.service_date,
        market_active=status_rows.market_active,
        market_open=status_rows.market_open,
        rows=[
            MapDayStatusRow(
                stall_id=row.stall_id,
                state=row.state,
                amount_soum=row.amount_soum,
                unavailable_reason=row.unavailable_reason,  # type: ignore[arg-type]
                paid_soum=row.paid_soum,
                remaining_soum=row.remaining_soum,
                open_case_id=row.open_case_id,
                open_case_service_date=row.open_case_service_date,
            )
            for row in status_rows.rows
        ],
    )


@router.get("/charges", response_model=ChargeListResponse)
async def billing_charges(
    principal: ReportViewerDep,
    session: TenantSessionDep,
    day: Annotated[date | None, Query()] = None,
) -> ChargeListResponse:
    """Kun kesimidagi YOZILGAN hisoblar (BILL-02, BILL-03; `REPORT_VIEW`).

    ⛔ IKKALA HISOBLAGICH HAM HAR DOIM QAYTADI — nol bo'lganda ham. «Bu
       kunda hisob yo'q» bilan «hisoblagich ishlamayapti» bir xil
       ko'rinmasligi kerak (`occupancy.py:122-124` prinsipi).

    ⛔ STANDART KUN — KECHA (`_report_day()` docstringi).

    ⚠ `vendor_id` QAYTADI, ISM EMAS (C-10 + §5.5): sotuvchi nomi
      MAVJUD `GET /vendors` dan klientda joinlanadi. Bu bitta qo'shimcha
      so'rovning ONGLI narxi — agar u og'ir bo'lsa to'g'ri tuzatish
      `/vendors` ni SAHIFALASH, bu javobga ism maydoni qo'shish EMAS.
    """
    market_id = _market_id(principal)
    business_date = _report_day(day)

    rows = await billing_repo.charge_list(session, market_id=market_id, day=business_date)

    return ChargeListResponse(
        day=business_date,
        rows=[
            ChargeRowResponse(
                charge_id=row.charge_id,
                stall_code=row.stall_code,
                vendor_id=row.vendor_id,
                service_date=row.service_date,
                tariff_amount_soum=row.tariff_amount_soum,
                amount_soum=row.amount_soum,
                outstanding_soum=row.outstanding_soum,
            )
            for row in rows
        ],
        charge_count=len(rows),
        charged_soum=sum(row.amount_soum for row in rows),
    )


@router.get("/charges/{charge_id}", response_model=ChargeDetailResponse)
async def billing_charge_detail(
    principal: ReportViewerDep,
    session: TenantSessionDep,
    charge_id: UUID,
) -> ChargeDetailResponse:
    """Bitta hisobning tafsiloti — DL-3 ning besh bo'limi (§11.3, SC#2).

    ⛔ TOPILMAGAN HISOB -> **404**, VA BEGONA BOZORNIKI HAM **404**
       (403 EMAS). RLS ostida o'sha qator boshqa bozor uchun MAVJUD
       EMAS, ya'ni 404 yolg'on emas — aynan haqiqat. 403 javobining O'ZI
       «bunday obyekt bor, lekin sizniki emas» degan ma'lumotni oshkor
       qilardi (T-01-76) va hujumchi ID'larni javob kodi bo'yicha sanab
       chiqa olardi.

    ⛔ `tariff_id` JAVOBDA YO'Q (§11.3, 2-bo'lim): direktorga ham
       ma'nosiz identifikator va uni berish D-20 ning kirish ma'lumotini
       ikkinchi yuzaga ko'chirardi.

    ⚠ DALIL KADRINING O'ZI BU MARSHRUTDAN KELMAYDI — javobda faqat
      `snapshot_id`. Rasm MAVJUD `GET /snapshots/{id}/image` proxysidan
      olinadi va AYNAN o'sha marshrut `audit_read` yozadi (M-8). Yangi
      rasm yuzasi ochilmaydi va `SNAPSHOT_EVIDENCE_FRAME_ROUTES`
      TEGILMAYDI.
    """
    market_id = _market_id(principal)

    detail = await billing_repo.charge_detail(session, market_id=market_id, charge_id=charge_id)
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_NOT_FOUND)

    return ChargeDetailResponse(
        charge_id=detail.charge_id,
        service_date=detail.service_date,
        stall_code=detail.stall_code,
        tariff_amount_soum=detail.tariff_amount_soum,
        amount_soum=detail.amount_soum,
        adjustments=[
            ChargeAdjustmentRow(
                adjustment_id=item.adjustment_id,
                direction=item.direction,  # type: ignore[arg-type]
                amount_soum=item.amount_soum,
                reason_code=item.reason_code,  # type: ignore[arg-type]
                actor_user_id=item.actor_user_id,
                created_at=item.created_at,
            )
            for item in detail.adjustments
        ],
        evidence=[
            ChargeEvidenceRow(snapshot_id=item.snapshot_id, slot_time=item.slot_time)
            for item in detail.evidence
        ],
    )


@router.get("/anomalies", response_model=AnomalyListResponse)
async def billing_anomalies(
    principal: ReportViewerDep,
    session: TenantSessionDep,
    day: Annotated[date | None, Query()] = None,
) -> AnomalyListResponse:
    """Kun kesimidagi anomaliyalar — ⛔ UCH ALOHIDA SANOQ (BILL-04, D-05).

    ⛔ UCHALA SANOQ HAM ALOHIDA VA HECH QACHON QO'SHILMAYDI. «Ko'ra
       olmadik» (`no_coverage_stall`) ≠ «band, lekin biriktirilmagan»
       (`unassigned_occupied`). Ikkisini bitta songa qo'shish KO'R
       NUQTADAN TUSHUM DA'VOSI TO'QISH bo'lardi — hisobot kamerasiz
       rastani ham «yo'qotilgan pul» deb ko'rsatardi.

    ⛔ UCHALASI HAM NOL BO'LGANDA HAM QAYTADI — nol NATIJA.

    ⛔ CASE OQIMI BU YERDA YO'Q (holat, mas'ul, qaror, `[Ko'rildi]`) —
       u 7-fazaniki (§16.1). Bu marshrut faqat YOZUVni ko'rsatadi.

    ⛔ STANDART KUN — KECHA (`_report_day()` docstringi).
    """
    market_id = _market_id(principal)
    business_date = _report_day(day)

    rows, counts = await billing_repo.anomaly_list(session, market_id=market_id, day=business_date)

    return AnomalyListResponse(
        day=business_date,
        rows=[
            AnomalyRowResponse(
                anomaly_id=row.anomaly_id,
                kind=row.kind,  # type: ignore[arg-type]
                stall_code=row.stall_code,
                service_date=row.service_date,
                snapshot_id=row.snapshot_id,
            )
            for row in rows
        ],
        unassigned_count=counts.unassigned,
        closed_day_count=counts.closed_day,
        no_coverage_count=counts.no_coverage,
    )
