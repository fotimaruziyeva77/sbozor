"""Nomuvofiqlik hisoboti va case navbati — DIREKTORNING yuzasi (RECON-01, RECON-02).

=============================================================================
⛔⛔ DALIL — HAVOLA, BAYT EMAS. VA YANGI TASVIR MARSHRUTI OCHILMAYDI.

RECON-01 «rasm-dalil **havolalari** bilan» deydi va bu so'z D-03 ning
frontendga qaragan yarmi: javobda **identifikator** bo'ladi, klient uni
⛔ **MAVJUD** `GET /api/v1/snapshots/{snapshot_id}/image` marshrutiga
beradi va o'sha marshrut har ochilishda `audit_read` yozadi (04-11).

⛔ Bu fayl BIRORTA yangi tasvir marshruti ochmaydi. 5-fazada dalil-kadr
   yuzasi ATAYIN bitta marshrutda qulflangan (T-06-81) va yopiqlik
   `tests/tenancy/test_personal_data_coverage.py::
   test_the_snapshot_surface_is_a_closed_set` bilan o'lchanadi — u bu
   faza davomida ⛔ **O'ZGARMASDAN** yashil qoladi.

=============================================================================
⛔⛔ `read_audit` E'LON QILINMAYDI — VA BU UNUTISH EMAS, QAROR.

`tests/tenancy/test_personal_data_coverage.py` ning D-09 darvozasi
`PERSONAL_FIELDS = {vendor_name, phone, full_name}` maydonlarini
qaytaradigan `GET` larni qamraydi. Bu fayldagi ⛔ **BIRORTA** javob
modelida ular YO'Q (`app/schemas.py` ning 07-10 bo'limidagi (a) taqig'i),
ya'ni marshrutlar darvozaga TUSHMAYDI va `audit_read` talabi ularga
qo'llanmaydi. `billing.py` ning modul docstringi bu qarorni 6-fazada
aynan shu shaklda yozgan.

⛔ DARVOZANI NOM BILAN AYLANIB O'TISH TAQIQLANADI: `vendor_label`,
   `payer`, `who` — hech biri. Sotuvchi nomi klientda MAVJUD va AUDIT
   QILINGAN `GET /vendors` bilan joinlanadi (C-10 + §5.5).

⛔ `chat_id` / `telegram_user_id` / `telegram_username` ham YO'Q. Ular
   `PERSONAL_FIELDS` da bo'lmagani uchun darvoza ularni USHLAMAYDI,
   lekin ular odamni TASHQI tizimda aniqlaydi (D-01); §5.5 bo'shliqni
   frontend tomonda **G-36** bilan yopadi.

=============================================================================
⛔⛔ HUQUQ MATRITSASI TEGILMAYDI (`app/security/rbac.py` O'ZGARMAGAN).

O'qish — `REPORT_VIEW` (direktor, bozor admini, platforma admini);
holat o'zgartirish — `DISPUTE_DECIDE` (⛔ FAQAT direktor). Ikkalasi ham
**MAVJUD** `Permission` a'zolari va ular D-07 matritsasidan OLINADI,
u yerga yozilmaydi. Kassirda ham, nazoratchida ham `REPORT_VIEW` YO'Q —
ya'ni beshala marshrut ham ular uchun **403** (T-07-58).

=============================================================================
⚠ ARIFMETIKA BU YERDA YOZILMAYDI (07-07 ning `reconciliation_repo` i va
  6-fazaning `billing_repo` i YAGONA manba). Bu fayl faqat SHAKL beradi:
  kunni yechadi, huquqni talab qiladi, natijani envelope'ga soladi va
  xatolarni HTTP kodiga aylantiradi. Summani bu yerda hisoblash
  «direktor ko'rgan son» bilan «bot yuborgan son» ni ajratib yuborardi —
  bu loyihada takroran topilgan «ikki haqiqat manbai» sinfi.
=============================================================================
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING, Annotated
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sbozor_core.enums import AuditAction, ReconciliationCaseStatus, ReconciliationSubjectKind
from sbozor_core.timeutil import business_today

from app.deps import Principal, TenantSessionDep, require_permission
from app.repositories import billing_repo, reconciliation_repo
from app.schemas import (
    CaseDetailResponse,
    CaseEventRow,
    CaseListResponse,
    CaseRowResponse,
    CaseUpdateRequest,
    HitRateResponse,
    ReconciliationReportResponse,
    ReconciliationReportRow,
)
from app.security.audit import write_app_audit
from app.security.rbac import Permission

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

# ⚠ `date` VA `UUID` ISH VAQTIDA IMPORT QILINADI, `TYPE_CHECKING` OSTIDA
#   EMAS — VA BU O'LCHANGAN ZARURIYAT (`billing.py:80-86`, va 07-08 uni
#   `bot.py` da IKKINCHI marta to'lagan). `from __future__ import
#   annotations` ostida annotatsiyalar SATR bo'lib qoladi va FastAPI
#   ularni Pydantic uchun YECHA olmaydi: `PydanticUserError: ... is not
#   fully defined` — nosozlik ish vaqtida, birinchi so'rovda chiqadi va
#   `mypy` uni KO'RMAYDI.

log = structlog.get_logger(__name__)

__all__ = ["router"]

router = APIRouter(tags=["reconciliation"])

ReportViewerDep = Annotated[Principal, Depends(require_permission(Permission.REPORT_VIEW))]
"""Hisobot va navbatni O'QISH huquqi — direktor, bozor admini, platforma admini.

⛔ Kassirda va nazoratchida bu huquq YO'Q va berilmaydi (UI-SPEC §5.6).
   Kassir hisobot o'qimaydi; nazoratchi esa BANDLIK verdiktini beradi va
   uning natijasini (aniqligini) o'zi ko'rmaydi — T-05-58 ning aynan
   davomi. Ikkalasi ham bu yerda **403** oladi.
"""

DisputeDeciderDep = Annotated[Principal, Depends(require_permission(Permission.DISPUTE_DECIDE))]
"""Case holatini O'ZGARTIRISH huquqi — ⛔ FAQAT DIREKTOR (D-07 matritsasi).

⛔ `REPORT_VIEW` EMAS va farq MAHSULOT qarori: bozor admini navbatni
   KO'RADI («bugun 12 ta nomuvofiqlik bor»), lekin «asosli / asossiz»
   HUKMINI direktor chiqaradi — u nizoda (D-02) sotuvchi oldida javob
   beradigan odam. Ikkalasini bitta huquqqa qo'shish hukmni kim
   chiqarganini jurnalda ham, mahsulotda ham noaniq qoldirardi.

⛔ `require_any_permission(REPORT_VIEW, DISPUTE_DECIDE)` ISHLATILMAYDI:
   `test_the_any_permission_gate_exists_nowhere_else_in_the_app` o'sha
   darvozani ko'targan marshrutlar to'plamini AYNAN dalil-kadr yo'liga
   TENG deb talab qiladi (05-15 qarori) — ya'ni bu yerda u darvozani
   qizartirardi. Bu texnik to'siq emas, o'sha qarорning himoyasi.
"""


_NOT_FOUND = "not_found"
"""Cross-tenant va mavjud bo'lmagan case uchun ⛔ BIR XIL javob (T-07-59).

⛔ 403 EMAS: javobning O'ZI «bunday case bor, lekin sizniki emas» degan
   ma'lumotni oshkor qilardi va hujumchi identifikatorlarni javob kodi
   bo'yicha sanab chiqa olardi. RLS `FORCE` begona bozorning qatorini
   ⛔ **0 QATOR** qiladi, ya'ni 404 yolg'on emas — aynan haqiqat.

⚠ `MARKET_ERROR_CODES` REYESTRIGA QO'SHILMAYDI (`billing.py:115-122`
  bilan aynan bir xil qaror): reyestr DOMEN kodlari uchun, bu esa
  STRUKTURAVIY javob va u hech qanday yo'l ko'rsatmaydi.
"""

_MARKET_NOT_SELECTED = "market_not_selected"
"""Sessiyada bozor tanlanmagan (**403**) — `billing.py` bilan bir xil kod."""

_DAY_IN_FUTURE = "day_in_future"
"""Kelajak kuni uchun hisobot so'raldi (**422**)."""

_RANGE_INVALID = "range_invalid"
"""`from` > `to` (**422**) — oraliqning O'ZI ifodalab bo'lmaydigan."""

_RANGE_TOO_WIDE = "range_too_wide"
"""Oraliq `HIT_RATE_MAX_DAYS` dan uzun (**422**) — T-07-60."""

_STATUS_UNCHANGED = "status_unchanged"
"""Case allaqachon so'ralgan holatda (**409**) — D-14 ning nol o'tishi."""

HIT_RATE_MAX_DAYS = 92
"""Hit-rate oralig'ining maksimal uzunligi, KUNLARDA (T-07-60).

⛔ ORALIQ MAJBURIY VA CHEGARALANGAN: chegarasiz so'rov
   `reconciliation_cases` ni BUTUNLAY skanerlardi va bitta so'rov bilan
   bozorning butun tarixini tortib olish yo'li ochiq qolardi.

⚠ 92 — chorakning eng uzun shakli (31+31+30). Direktor «shu chorak»
   savolini bir so'rov bilan berishi kerak, «shu yil» esa hisobot
   emas, EKSPORT (u alohida yuza va u bu fazada YO'Q).
"""

REPORT_PAGE_BUDGET = 100
"""Hisobot yig'adigan keyset sahifalarining CHEGARASI — ⛔ NOSOZLIK DETEKTORI.

=============================================================================
⛔ BU TRUNKATSIYA CHEGARASI EMAS. Hisobot kunning HAMMA nomuvofiqligini
   ko'rsatishi shart (RECON-01 — «raqamlar bilan»), ya'ni jim qisqartirish
   direktorga KAM son ko'rsatardi va u buni SEZMASDI ham.

Chegara STRUKTURAVIY jihatdan erishib bo'lmaydigan qilib tanlangan: bir
kunda bitta rastada ko'pi bilan bitta hisob (`daily_charges` ning
`(market_id, stall_id, service_date)` unikaligi) va bitta anomaliya
bo'ladi, ya'ni case'lar soni `2 × rasta_soni` dan oshmaydi. MVP
konvertida (Karmana — ~300–1000 rasta) bu ≤ 2000, `CASE_PAGE_SIZE = 50`
da esa ≤ 40 sahifa.

Ya'ni budjetning tugashi — MA'LUMOT hajmi emas, KURSORNING AYLANIB
QOLISHI, ya'ni kod nuqsoni. Shuning uchun u `RuntimeError` bilan
yiqiladi (500), jim qisqarish bilan EMAS: yashirin qisqargan hisobot
«bugun nomuvofiqlik kam» degan YOLG'ON xulosa berardi.
=============================================================================
"""


def _reject(code: str, http_status: int) -> HTTPException:
    """`detail` ⛔ **SATR**, lug'at EMAS — va bu KLIENT KONTRAKTI (CR-04).

    `frontend/src/lib/api-client.ts::detailOf()` `detail` ni AYNAN satr
    deb o'qiydi (`typeof parsed.data.detail === "string"`); lug'at
    yuborilganda u **bo'sh satr** qaytaradi va kod klientga UMUMAN yetib
    bormaydi — o'shanda `errors.generic` («Kutilmagan xato») chiziladi.
    Nosozlik 6-fazada bir marta O'LCHANGAN (`/billing/pending` ning 404 i)
    va shakl `billing.py` / `payments.py` / `shifts.py` da bir xil.
    """
    return HTTPException(status_code=http_status, detail=code)


def _market_id(principal: Principal) -> UUID:
    """Sessiyadagi bozor — `billing.py::_market_id()` bilan AYNI shakl."""
    market_id = principal.market_id
    if market_id is None:
        raise _reject(_MARKET_NOT_SELECTED, status.HTTP_403_FORBIDDEN)
    return market_id


def _report_day(day: date | None) -> date:
    """Hisobot kunini yechadi — ⛔ STANDARTI KECHA (UI-SPEC §11.1).

    ⛔ NEGA BUGUN EMAS: hisob D+1 04:10 da tug'iladi (C-3) va `recon.open`
       KECHAGI kunni bugun tekshiradi. Standart kun BUGUN bo'lsa sahifa
       HAR DOIM bo'sh ochilardi va direktor «tizim ishlamayapti» degan
       xulosaga kelardi — ya'ni to'g'ri ishlayotgan tizim buzuq bo'lib
       ko'rinardi.

    ⛔ KELAJAK KUNI **422**: `daily_charges` ning `CHECK (service_date <=
       business_date)` konstraytining HTTP qatlamidagi jufti. Usiz so'rov
       bazagacha borib BO'SH ro'yxat qaytarardi va «kelajakda nomuvofiqlik
       yo'q» degan MA'NOSIZ javob «bu kunda nomuvofiqlik topilmadi» bilan
       bir xil ko'rinardi.
    """
    today = business_today()
    resolved = today - timedelta(days=1) if day is None else day
    if resolved > today:
        raise _reject(_DAY_IN_FUTURE, status.HTTP_422_UNPROCESSABLE_CONTENT)
    return resolved


def _encode_cursor(cursor: reconciliation_repo.CaseCursor | None) -> str | None:
    """Keyset kursorini ⛔ UNUMSIZ SATRGA aylantiradi.

    ⚠ SHAKL (`<ISO timestamp>|<uuid>`) KLIENT KONTRAKTI EMAS: klient uni
      PARSE QILMAYDI, o'zgarmasdan qaytaradi. Ichki shaklni ochish
      sahifalash qoidasini serverdan klientga ko'chirardi va ikki tomonda
      ajralib ketardi (`CaseListPage.next_cursor` docstringidagi qaror).
    """
    if cursor is None:
        return None
    return f"{cursor.created_at.isoformat()}|{cursor.case_id}"


def _decode_cursor(raw: str | None) -> reconciliation_repo.CaseCursor | None:
    """Kursor satrini yechadi — buzilgan qiymat ⛔ **422**, jim e'tiborsizlik EMAS.

    ⛔ JIM TASHLAB YUBORISH TAQIQLANADI: nazoratchi «Yana» tugmasini
       bosganda BIRINCHI sahifani qayta ko'rardi va navbat cheksiz
       aylanardi — u buni sezmasdi ham, chunki qatorlar haqiqiy.
    """
    if raw is None:
        return None
    head, _, tail = raw.partition("|")
    try:
        created_at = datetime.fromisoformat(head)
        case_id = UUID(tail)
    except ValueError as exc:
        raise _reject("cursor_invalid", status.HTTP_422_UNPROCESSABLE_CONTENT) from exc
    return reconciliation_repo.CaseCursor(created_at=created_at, case_id=case_id)


@router.get("/report", response_model=ReconciliationReportResponse)
async def reconciliation_report(
    principal: ReportViewerDep,
    session: TenantSessionDep,
    day: Annotated[date | None, Query()] = None,
) -> ReconciliationReportResponse:
    """Kunlik nomuvofiqlik hisoboti — ⛔ IKKALA SINF HAM (RECON-01, §8.1).

    =======================================================================
    ⛔⛔ IKKI SINF VA ULAR BIR JADVALDAN KELMAYDI (Pattern 4).

      `occupied_unpaid` — «band, lekin to'lovsiz»: hisob YOZILGAN, to'lov
                          yetmagan. Manba — `daily_charges` − `payments`
                          HOSILASI.
      `anomaly`         — «ro'yxatga olinmagan savdo»: hisob UMUMAN
                          yozilmagan. Manba — `billing_anomalies` ning
                          O'ZGARMAS qatori.

    Ikkalasi ham `reconciliation_cases` navbatiga tushadi va hisobot
    ularni BIRGA ko'rsatadi — chunki direktorning savoli bitta: «bugun
    qancha patta yo'qoldi?». Ammo hisoblagichlar ⛔ ALOHIDA va HECH
    QACHON qo'shilmaydi (`ReconciliationReportResponse` docstringi).
    =======================================================================

    ⛔ `read_audit` E'LON QILINMAYDI va bu qaror, unutish emas — modul
       docstringining ikkinchi bo'limi. Javobda shaxsiy maydon YO'Q,
       ya'ni D-09 darvozasining talabi bu marshrutga qo'llanmaydi.

    ⛔ DALIL — `snapshot_id` LARNING RO'YXATI. Bayt ham, imzolangan
       havola ham YO'Q va yangi tasvir marshruti OCHILMAYDI (D-03).

    ⚠ NARXI OCHIQ YOZILADI: har case uchun `case_evidence()` chaqiriladi
      (N+1). Yagona muqobil — dalil so'rovini hisobot so'roviga
      qo'shib yozish, ya'ni `_CASE_EVIDENCE` ning IKKINCHI nusxasi;
      07-07 aynan shu vasvasani `vendor_charge_allocation()` uchun
      nomma-nom rad etgan. Hisobot kuniga bir necha marta ochiladi va
      qatorlar soni rasta soni bilan chegaralangan.
    """
    market_id = _market_id(principal)
    business_date = _report_day(day)

    cases = await _all_cases_of_day(session, market_id=market_id, day=business_date)

    charges = {
        row.charge_id: row
        for row in await billing_repo.charge_list(session, market_id=market_id, day=business_date)
    }
    anomalies = {
        row.anomaly_id: row
        for row in (
            await billing_repo.anomaly_list(session, market_id=market_id, day=business_date)
        )[0]
    }

    # ⚠ TAQSIMLASH SOTUVCHI BO'YICHA KESHLANADI, CASE BO'YICHA EMAS: bir
    #   sotuvchining bir necha rastasi bo'lishi NORMAL va har biriga
    #   alohida chaqiruv AYNI natijani qayta hisoblardi. Kesh SO'ROV
    #   ichida yashaydi — `allocate_charge_credit()` ning docstringi
    #   natijani JADVALGA yozishni ham, UZOQ MUDDATLI keshlashni ham
    #   nomma-nom taqiqlaydi (D-07/BILL-03).
    allocations: dict[UUID, dict[tuple[date, str], int]] = {}

    rows: list[ReconciliationReportRow] = []
    for case in cases:
        charge = None if case.charge_id is None else charges.get(case.charge_id)
        anomaly = None if case.anomaly_id is None else anomalies.get(case.anomaly_id)

        stall_code = charge.stall_code if charge is not None else None
        if stall_code is None and anomaly is not None:
            stall_code = anomaly.stall_code
        if stall_code is None:
            # ⚠ HISOB YOKI ANOMALIYA O'SHA KUNDA TOPILMADI. Bu STRUKTURAVIY
            #   jihatdan kutilmaydi (case nishonga kompozit FK bilan
            #   bog'langan va `service_date` ikkalasida ham bir xil),
            #   lekin `stall_code` ni «—» bilan to'ldirish TO'QILGAN
            #   qiymat bo'lardi (05-14 darsi). Qator TUSHIRILMAYDI ham:
            #   u hisoblagichda BOR va yo'qolishi sonlarni ajratardi.
            log.warning(
                "reconciliation_report_row_without_target",
                case_id=str(case.case_id),
                subject_kind=case.subject_kind,
            )
            continue

        vendor_id = charge.vendor_id if charge is not None else None
        paid_soum: int | None = None
        if charge is not None:
            if vendor_id is not None and vendor_id not in allocations:
                allocation = await billing_repo.vendor_charge_allocation(
                    session, market_id=market_id, vendor_id=vendor_id
                )
                allocations[vendor_id] = {
                    (item.service_date, item.stall_code): item.paid_soum for item in allocation.rows
                }
            if vendor_id is not None:
                paid_soum = allocations[vendor_id].get((charge.service_date, charge.stall_code))

        evidence = await reconciliation_repo.case_evidence(
            session, market_id=market_id, case_id=case.case_id
        )
        rows.append(
            ReconciliationReportRow(
                subject_kind=ReconciliationSubjectKind(case.subject_kind),
                case_id=case.case_id,
                status=ReconciliationCaseStatus(case.status),
                service_date=case.service_date,
                stall_code=stall_code,
                vendor_id=vendor_id,
                expected_soum=None if charge is None else charge.amount_soum,
                paid_soum=paid_soum,
                evidence_snapshot_ids=list(evidence.snapshot_ids),
            )
        )

    unpaid = [row for row in rows if row.subject_kind is ReconciliationSubjectKind.OCCUPIED_UNPAID]
    return ReconciliationReportResponse(
        day=business_date,
        rows=rows,
        unpaid_count=len(unpaid),
        unregistered_count=len(rows) - len(unpaid),
        unpaid_expected_soum=sum(row.expected_soum or 0 for row in unpaid),
    )


async def _all_cases_of_day(
    session: AsyncSession, *, market_id: UUID, day: date
) -> list[reconciliation_repo.CaseRow]:
    """Kunning HAMMA case'i — keyset bo'ylab yurib yig'iladi.

    ⛔ `list_cases()` NING `limit` INI KO'TARISH BILAN ALMASHTIRIB
       BO'LMAYDI: funksiya qiymatni `CASE_PAGE_SIZE` GACHA QISQARTIRADI
       («klient bir so'rov bilan butun navbatni tortib ololmasligi
       kerak») va chegarani ko'tarish o'sha qarorni butun tizim uchun
       bo'shatardi. Hisobot esa navbat EMAS — u kunning YAKUNI va u
       to'liq bo'lishi shart.

    Raises:
        RuntimeError: sahifa budjeti tugaganda — `REPORT_PAGE_BUDGET`
            docstringi (jim qisqarish o'rniga BALAND ovozdagi nosozlik).
    """
    collected: list[reconciliation_repo.CaseRow] = []
    cursor: reconciliation_repo.CaseCursor | None = None
    for _ in range(REPORT_PAGE_BUDGET):
        page = await reconciliation_repo.list_cases(
            session, market_id=market_id, day=day, cursor=cursor
        )
        collected.extend(page.rows)
        if page.next_cursor is None:
            return collected
        cursor = page.next_cursor
    raise RuntimeError(
        f"hisobot {REPORT_PAGE_BUDGET} sahifadan oshdi (kun={day}, bozor={market_id}). "
        "Bu ma'lumot hajmi emas, KURSORNING AYLANIB QOLISHI — "
        "`REPORT_PAGE_BUDGET` docstringiga qarang."
    )


@router.get("/cases", response_model=CaseListResponse)
async def reconciliation_cases(
    principal: ReportViewerDep,
    session: TenantSessionDep,
    day: Annotated[date | None, Query()] = None,
    case_status: Annotated[ReconciliationCaseStatus | None, Query(alias="status")] = None,
    cursor: Annotated[str | None, Query()] = None,
) -> CaseListResponse:
    """Kun kesimidagi case navbati — keyset bilan sahifalangan (RECON-02, DQ-4).

    ⛔ `status` FILTRI ⛔ **YOPIQ ENUMDAN**: noma'lum qiymat FastAPI ning
       validatsiyasida **422** oladi va so'rov bazagacha umuman yetib
       bormaydi. Erkin satr qabul qilish `ReconciliationCaseStatus` ning
       yopiqligini (D-12) HTTP chegarasida bo'shatardi — o'shanda
       `?status=other` bilan kelgan so'rov BO'SH ro'yxat qaytarib,
       «bunday holatdagi case yo'q» degan MA'NOSIZ javob berardi.

    ⛔ TO'RTALA HISOBLAGICH HAM ⛔ FILTRDAN MUSTAQIL (kun bo'yicha) va
       bu `reconciliation_repo._CASE_COUNTS` ning qarori — bu yerda
       TAKRORLANMAYDI.

    ⚠ `alias="status"` ATAYIN: `status` nomi bu modulda FastAPI ning
      `status` moduli bilan to'qnashardi (`status.HTTP_404_NOT_FOUND`),
      ya'ni parametr nomi KLIENT kontraktida `status`, Python imzosida
      esa `case_status`.
    """
    market_id = _market_id(principal)
    business_date = _report_day(day)

    page = await reconciliation_repo.list_cases(
        session,
        market_id=market_id,
        day=business_date,
        status=None if case_status is None else case_status.value,
        cursor=_decode_cursor(cursor),
    )

    return CaseListResponse(
        day=page.day,
        rows=[_case_row(row) for row in page.rows],
        new_count=page.new_count,
        in_review_count=page.in_review_count,
        justified_count=page.justified_count,
        unjustified_count=page.unjustified_count,
        next_cursor=_encode_cursor(page.next_cursor),
    )


def _case_row(row: reconciliation_repo.CaseRow) -> CaseRowResponse:
    """Repo qatorini HTTP shakliga o'tkazadi — ⛔ FAQAT SHAKL, hisob YO'Q."""
    return CaseRowResponse(
        case_id=row.case_id,
        subject_kind=ReconciliationSubjectKind(row.subject_kind),
        anomaly_id=row.anomaly_id,
        charge_id=row.charge_id,
        service_date=row.service_date,
        status=ReconciliationCaseStatus(row.status),
        assignee_user_id=row.assignee_user_id,
        created_at=row.created_at,
    )


@router.get("/cases/{case_id}", response_model=CaseDetailResponse)
async def reconciliation_case_detail(
    principal: ReportViewerDep,
    session: TenantSessionDep,
    case_id: UUID,
) -> CaseDetailResponse:
    """Bitta case: holat + TO'LIQ tarix + dalil identifikatorlari (D-14, D-03).

    ⛔ BEGONA BOZORNING `case_id` I -> **404**, ⛔ **403 EMAS** (T-07-59).
       RLS `FORCE` uni **0 QATOR** qiladi va marshrut buni 404 ga
       aylantiradi. 403 javobining O'ZI «bunday case bor, lekin sizniki
       emas» deb tasdiqlardi va hujumchi identifikatorlarni javob kodi
       bo'yicha sanab chiqa olardi. Mavjud bo'lmagan `case_id` ham
       AYNAN o'sha javobni oladi — ikkalasi farq qilsa javobning o'zi
       enumeration signali bo'lardi.

    ⛔ TARIX SAHIFALANMAYDI: u nazoratchining QO'L harakatlaridan o'sadi
       va nizo hujjatida aynan TO'LIQLIK muhim (`_CASE_EVENTS`
       docstringi).
    """
    return await _case_detail_response(session, market_id=_market_id(principal), case_id=case_id)


async def _case_detail_response(
    session: AsyncSession, *, market_id: UUID, case_id: UUID
) -> CaseDetailResponse:
    """Case tafsiloti — ⛔ IKKI MARSHRUT UCHUN BITTA SHAKL.

    `GET` va `PATCH` AYNI javobni qaytaradi (PATCH dan keyin klient
    ikkinchi so'rov yubormasligi kerak — nazoratchi oqimi 07-16 da
    optimistik yozuv bilan quriladi). Ikki joyda qurish ularni bir kun
    AJRATIB yuborardi: bittasiga maydon qo'shilib, ikkinchisiga
    qo'shilmasdi va klient sxemasi `z.strictObject` ostida FAQAT bitta
    yo'lda yiqilardi.

    ⛔ MARSHRUT FUNKSIYASINI TO'G'RIDAN-TO'G'RI CHAQIRISH BILAN
       ALMASHTIRILMAYDI: u `Principal` ni argument sifatida talab
       qilardi va `PATCH` ning `DISPUTE_DECIDE` egasini `REPORT_VIEW`
       imzosiga uzatish huquq talabini KOD DARAJASIDA chalkashtirardi.
    """
    detail = await reconciliation_repo.case_detail(session, market_id=market_id, case_id=case_id)
    if detail is None:
        raise _reject(_NOT_FOUND, status.HTTP_404_NOT_FOUND)

    evidence = await reconciliation_repo.case_evidence(
        session, market_id=market_id, case_id=case_id
    )
    case = detail.case

    return CaseDetailResponse(
        case_id=case.case_id,
        subject_kind=ReconciliationSubjectKind(case.subject_kind),
        anomaly_id=case.anomaly_id,
        charge_id=case.charge_id,
        service_date=case.service_date,
        status=ReconciliationCaseStatus(case.status),
        assignee_user_id=case.assignee_user_id,
        created_at=case.created_at,
        resolution_note=case.resolution_note,
        events=[
            CaseEventRow(
                from_status=(
                    None
                    if event.from_status is None
                    else ReconciliationCaseStatus(event.from_status)
                ),
                to_status=ReconciliationCaseStatus(event.to_status),
                actor_user_id=event.actor_user_id,
                note=event.note,
                created_at=event.created_at,
            )
            for event in detail.events
        ],
        evidence_snapshot_ids=list(evidence.snapshot_ids),
    )


@router.patch("/cases/{case_id}", response_model=CaseDetailResponse)
async def reconciliation_case_update(
    principal: DisputeDeciderDep,
    session: TenantSessionDep,
    case_id: UUID,
    payload: CaseUpdateRequest,
) -> CaseDetailResponse:
    """Case holatini o'zgartiradi — ⛔ IKKI JURNAL, IKKI MAQSAD (D-14, T-07-61).

    =======================================================================
    ⛔⛔ NEGA IKKI YOZUV VA NEGA ULARDAN BIRORTASI ORTIQCHA EMAS.

      `reconciliation_case_events` — ⛔ **MAHSULOT** tarixi. Uni DIREKTOR
          o'qiydi: «bu case qaysi yo'ldan o'tdi, kim nima dedi?». U
          nizo hujjatining (D-02) qismi va u foydalanuvchi yuzasida
          KO'RINADI (`GET /reconciliation/cases/{id}` javobidagi
          `events`).

      `audit_log` — ⛔ **XAVFSIZLIK** jurnali. Uni AUDITOR o'qiydi:
          «tizimda kim nimani o'zgartirdi?». U `GET /audit` yuzasida
          yashaydi va uning qamrovi butun ilova bo'ylab BIR XIL
          bo'lishi shart — case'ni istisno qilish «qaysi jadvallar
          kuzatiladi?» degan savolga «hammasi, bittasidan tashqari»
          degan javob berardi.

    ⛔ BIRINCHISINI IKKINCHISI BILAN ALMASHTIRIB BO'LMAYDI: `audit_log`
       da `market_id` bo'yicha filtr va `changed_keys` bor, lekin unda
       `from_status` -> `to_status` KETMA-KETLIGI YO'Q. Ikkinchisini
       birinchisi bilan ham: `reconciliation_case_events` FAQAT case
       domenini biladi.

    ⚠ TARIX QATORINI ⛔ **REPO YOZADI** (`transition()` bitta
      tranzaksiyada ikkala yozuvni ham bajaradi), marshrut esa faqat
      `audit_log` qatorini qo'shadi. Tarix yozuvini bu yerga ko'chirish
      uni tranzaksiyadan CHIQARIB yuborardi.
    =======================================================================

    ⛔ BIR XIL HOLATGA O'TISH -> **409**. Repo `ValueError` beradi
       (`transition()` docstringi: nol o'tish tarixni shovqin bilan
       to'ldirardi va «case necha marta qo'ldan qo'lga o'tdi?» savoli
       noto'g'ri javob berardi), marshrut uni KODGA aylantiradi.

    ⛔ HOLAT — YOPIQ RO'YXAT: `CaseUpdateRequest.status` `Reconciliation
       CaseStatus` tipida, ya'ni `"other"` HTTP chegarasida **422** oladi
       va u yechim MATNI bo'lib ham kira olmaydi (D-12).
    """
    market_id = _market_id(principal)

    before = await reconciliation_repo.case_detail(session, market_id=market_id, case_id=case_id)
    if before is None:
        raise _reject(_NOT_FOUND, status.HTTP_404_NOT_FOUND)

    try:
        await reconciliation_repo.transition(
            session,
            market_id=market_id,
            case_id=case_id,
            to_status=payload.status.value,
            actor_user_id=principal.user_id,
            note=payload.resolution_note,
        )
    except LookupError as exc:  # pragma: no cover — yuqoridagi o'qish uni oldindan tutadi
        raise _reject(_NOT_FOUND, status.HTTP_404_NOT_FOUND) from exc
    except ValueError as exc:
        raise _reject(_STATUS_UNCHANGED, status.HTTP_409_CONFLICT) from exc

    await write_app_audit(
        session,
        action=AuditAction.UPDATE,
        table_name="reconciliation_cases",
        row_id=case_id,
        principal=principal,
        old={"status": before.case.status, "resolution_note": before.case.resolution_note},
        new={"status": payload.status.value, "resolution_note": payload.resolution_note},
    )
    await session.commit()

    return await _case_detail_response(session, market_id=market_id, case_id=case_id)


@router.get("/hit-rate", response_model=HitRateResponse)
async def reconciliation_hit_rate(
    principal: ReportViewerDep,
    session: TenantSessionDep,
    date_from: Annotated[date, Query(alias="from")],
    date_to: Annotated[date, Query(alias="to")],
) -> HitRateResponse:
    """Navbatning aniqligi — ⛔ HOSILA, saqlangan ustun EMAS (D-13).

    ⛔ ORALIQ ⛔ **MAJBURIY** (standart qiymat YO'Q) VA MAKSIMAL
       `HIT_RATE_MAX_DAYS` KUN (T-07-60). Chegarasiz so'rov
       `reconciliation_cases` ni butunlay skanerlardi; standart oraliq
       esa «qaysi davr o'lchandi?» savolini javobsiz qoldirardi va
       ko'rsatkich hisobotga MANBASIZ ko'chib o'tardi.

    ⛔ `hit_rate` `null` BO'LISHI MUMKIN VA BU JAVOB, XATO EMAS:
       maxraj (`justified + unjustified`) nol bo'lganda «hali o'lchov
       yo'q» degani va u `0.0` («nol aniqlik») bilan
       ALMASHTIRILMAYDI. Arifmetika `reconciliation_repo.hit_rate()`
       da va bu yerda TAKRORLANMAYDI.

    ⚠ `open_cases` (`new` + `in_review`) maxrajga KIRMAYDI, lekin
      javobda BOR: usiz «100 %» ikki xil dunyoni bir xil ko'rsatardi.
    """
    market_id = _market_id(principal)

    if date_from > date_to:
        raise _reject(_RANGE_INVALID, status.HTTP_422_UNPROCESSABLE_CONTENT)
    # ⚠ INKLYUZIV ORALIQ: `from == to` — BIR KUN, ya'ni uzunlik
    #   `(to - from) + 1`. `repo.hit_rate()` chegaralarni `BETWEEN` bilan
    #   qo'llaydi va bu hisob o'sha semantikaning AYNAN jufti.
    if (date_to - date_from).days + 1 > HIT_RATE_MAX_DAYS:
        raise _reject(_RANGE_TOO_WIDE, status.HTTP_422_UNPROCESSABLE_CONTENT)

    measured = await reconciliation_repo.hit_rate(
        session, market_id=market_id, date_from=date_from, date_to=date_to
    )

    return HitRateResponse(
        date_from=date_from,
        date_to=date_to,
        justified=measured.justified,
        unjustified=measured.unjustified,
        open_cases=measured.pending,
        hit_rate=measured.rate,
    )
