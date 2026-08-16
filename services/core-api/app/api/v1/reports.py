"""Davr hisobotlarining JSON yuzasi — DIREKTOR va BOZOR ADMINIniki (RECON-04).

=============================================================================
⛔⛔ 1. YANGI HUQUQ YOZILMAGAN VA `ROLE_PERMISSIONS` TEGILMAGAN (R-1, M-6).

`Permission.REPORT_VIEW` ALLAQACHON mavjud va u AYNAN `director` +
`market_admin` da. Ya'ni D-04 («kassir hisobot yuzasini ko'rmaydi») va
D-20 bugungi matritsada ALLAQACHON rost — yangi a'zo qo'shish o'sha
haqiqatni takrorlab, `rbac.py` ↔ `rbac.ts` juftligini va
`role-gate.test.mjs` darvozasini SABABSIZ qo'zg'atardi.

⛔ `platform_admin` GA `REPORT_VIEW` BERILMAGAN — VA BU ONGLI QAROR
   (Pitfall 11 varianti A, UI-SPEC O-07).

Platforma admini BOZORLARARO rol: u har bozorni ko'ra oladi. Unga
hisobot yuzasini ochish HAR BOZORNING qarzdorlari ismini bitta
sessiyaga to'plardi — ya'ni bitta akkaunt butun platformaning shaxsiy
ma'lumot xaritasiga aylanardi. Uning ishi bozorni QURISH (wizard) va
platforma auditini o'qish, bozorning pulini KO'RISH emas. Bu taqiq
`test_reports_api.py` da NOM BILAN o'lchanadi.

=============================================================================
⛔⛔ 2. MARSHRUT NOMLARI KLIENT KONTRAKTIDAN: `/revenue`, `/debtors`,
    `/anomalies` — reja aytgan `/receivables`, `/discrepancies` EMAS.

08-03 (TO'LQIN 1) `REPORT_KINDS` ni ⛔ `{revenue, debtors, anomalies,
accuracy}` deb to'plam TENGLIGI bilan qulflagan (UI-SPEC §12.1, G-43a)
va `report-queries.ts::buildReportDataPath()` yo'lni AYNAN o'sha
a'zodan quradi: `/api/v1/reports/{kind}`. Ya'ni jo'natilgan klient
`/debtors` va `/anomalies` ga boradi.

⛔ SERVER KLIENTNI KUZATADI, AKSINCHA EMAS — bu 08-03 SUMMARY da
   YOZILGAN to'lqin qarori. Boshqa nom tanlansa nosozlik JIMGINA
   bo'lardi: komponent testlari mock bilan yashil qolardi va 404
   faqat jonli ekranda ko'rinardi.

⚠ 08-12 (`.xlsx`) SHU NOMLARDAN yuradi: `/revenue.xlsx`,
  `/debtors.xlsx`, `/anomalies.xlsx`, `/accuracy.xlsx` — chunki
  `buildReportPath()` ham AYNI reyestrdan quriladi.

=============================================================================
⛔⛔ 3. HUQUQ IMZODA, VA «YO P YO Q» DARVOZASI BU YERDA YO'Q (C-9).

`test_personal_data_coverage.py::
test_the_any_permission_gate_exists_nowhere_else_in_the_app` o'sha
darvozani ko'targan marshrutlar to'plamini AYNAN dalil-kadr yo'liga
TENG deb qulflagan. `/debtors` ikki huquq talab qiladi va ular
«yo P yo Q» EMAS, **VA** bilan: `REPORT_VIEW` — «bu odam hisobot
o'qiydimi?», `VENDOR_VIEW` — «bu odam SHAXSIY ma'lumot ko'rishga
haqlimi?». Ikkalasi ham majburiy.

⚠ TAQIQLANGAN FABRIKA NOMI BU FAYLDA LITERAL YOZILMAYDI — na kodda,
  na izohda (`test_route_coverage.py` modul docstringidagi «taqiqlangan
  marker nomlari izohda ham literal yozilmaydi» qoidasining aynan
  takrori). Qabul mezoni `grep` bilan o'lchanadi va izohdagi nusxa uni
  YOLG'ON-QIZIL qilardi.

=============================================================================
⛔ 4. XATO KODLARI `ALL_BILLING_ERROR_CODES` REYESTRIGA QO'SHILMAYDI.

Sabab `billing.py:124-134` da literal yozilgan: reyestrning SONI
frontend darvozasi (`scripts/error-codes.test.mjs`) tomonidan uchala
locale'dagi `errorCause`/`errorFix` juftligi bilan solishtiriladi, ya'ni
yangi kod matn qo'shilmaguncha o'sha darvozani QIZARTIRARDI. Hisobot
kodlarining O'Z reyestri bor va u FRONTENDDA langar:
`frontend/src/lib/report-errors.ts::REPORT_ERROR_CODES` (08-03) —
`report_period_invalid`, `report_period_future`, `report_period_too_long`,
`report_too_large` shu yerdagi satrlar bilan AYNAN bir xil yozilgan.

=============================================================================
⚠ 5. HANDLERLAR ARIFMETIKA YOZMAYDI (D-16 ning hisobotdagi shakli).

Uchala javob ham `app/repositories/report_repo.py` dan keladi. Yig'indi
ham SERVERDAN: `revenue_by_day()` uni `sum(...) OVER ()` bilan AYNI
so'rovda beradi. Bu qatlam faqat DTO ga o'giradi va sahifalaydi.
=============================================================================
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Annotated, Final
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sbozor_core.timeutil import business_today

from app.deps import Principal, SettingsDep, TenantSessionDep, require_permission
from app.repositories import report_repo
from app.schemas import (
    AnomalyArchiveResponse,
    AnomalyArchiveRowResponse,
    ReceivablesReportResponse,
    ReceivablesReportRow,
    RevenueReportResponse,
    RevenueReportRow,
)
from app.security.audit import TABLE_VENDORS, AuditReadIntent, audit_read
from app.security.rbac import Permission

# ⚠ `date` VA `UUID` ISH VAQTIDA IMPORT QILINADI, `TYPE_CHECKING` OSTIDA
#   EMAS — VA BU O'LCHANGAN ZARURIYAT (`billing.py:82-88` va
#   `occupancy.py:70-75` da ham aynan shunday). `from __future__ import
#   annotations` ostida annotatsiyalar SATR bo'lib qoladi va FastAPI
#   ularni Pydantic uchun YECHA olmaydi: `PydanticUserError: ... is not
#   fully defined`. Nosozlik marshrutda emas, OpenAPI sxemasini quruvchi
#   meta-testda ko'rinadi.

log = structlog.get_logger(__name__)

__all__ = ["REPORT_PAGE_SIZE", "router"]

router = APIRouter(tags=["reports"])

ReportViewerDep = Annotated[Principal, Depends(require_permission(Permission.REPORT_VIEW))]
"""⛔ `BILLING_COLLECT_VIEW` EMAS (`billing.py:111-114` bilan AYNI shakl).

Kassirda `report_view` YO'Q va berilmaydi (UI-SPEC §5.6): u pul YIG'ADI,
hisobot O'QIMAYDI. Nazoratchida ham yo'q — `ROLE_PERMISSIONS[INSPECTOR]`
AYNAN `{OCCUPANCY_REVIEW}` (T-05-58).
"""

VendorFieldGuardDep = Annotated[Principal, Depends(require_permission(Permission.VENDOR_VIEW))]
"""⛔ FAQAT `/debtors` DA — VA U `ReportViewerDep` NING O'RNINI BOSMAYDI.

Ikki darvoza IKKI BOSHQA savolga javob beradi va shuning uchun ikkalasi
ham e'lon qilinadi:

    `REPORT_VIEW`  -> «bu odam hisobot yuzasini ochadimi?»
    `VENDOR_VIEW`  -> «bu odam SHAXSIY ma'lumot (F.I.Sh.) ko'rishga haqlimi?»

`test_personal_data_coverage.py::test_personal_data_routes_require_vendor_view`
javob MODELIDAN yuradi (`vendor_name` maydonini ko'radi) va shu
marshrutdan `VENDOR_VIEW` ni AYNAN talab qiladi — ya'ni bu qator
kelajakdagi «faqat ko'rsin» rolini himoya qiladi: bunday rol
`REPORT_VIEW` olganda shaxsiy ma'lumotni JIMGINA meros qilib olmaydi.

⚠ Bugungi matritsada ikkala huquq ham `director` va `market_admin` da
  BIRGA turadi, ya'ni bu qator hech kimning kirishini TORAYTIRMAYDI.
"""

ReceivablesReadIntentDep = Annotated[
    AuditReadIntent,
    Depends(audit_read(TABLE_VENDORS, reason="report_receivables")),
]
"""D-09: shaxsiy ma'lumotning HAR BIR o'qilishi jurnalga tushadi.

⛔ `reason` YANGI VA NOMLANGAN (`vendors.py:105-113` dagi qoida):
   jurnalni o'qiyotgan odam «kim sotuvchilar reestrini varaqladi»
   (`vendor_view`) bilan «kim QARZDORLIK HUJJATINI oldi»
   (`report_receivables`) ni ajrata olishi kerak. Bir xil `reason`
   bilan o'sha farq yo'qolardi.

⛔ BITTA SO'ROV = BITTA YOZUV, SOTUVCHI BOSHIGA EMAS. `audit_read`
   dependency si so'rov boshida BITTA `AuditReadIntent` quradi va
   javob yuborilgandan keyin BITTA qator yozadi — 200 qarzdorli
   hisobot ham, 3 qarzdorli ham AYNI bitta izni qoldiradi. Muqobil
   («har sotuvchi uchun bitta yozuv») jurnalni shovqinga to'ldirib,
   HAQIQIY o'qish hodisasini ko'mib yuborardi (06 №9 da rad etilgan
   (a) yo'lining aynan sababi). Bu `test_reports_api.py` da IKKI
   hajmda (3 va 200 sotuvchi) o'lchanadi.
"""

REPORT_PAGE_SIZE: Final[int] = 500
"""Bir sahifadagi eng ko'p hisobot qatori (§8.6, `CASE_PAGE_SIZE` naqshi).

=============================================================================
⛔ NEGA 500, VA NEGA «CHEGARASIZ» EMAS.

Tushum hisoboti KUN kesimida, davr esa `report_max_period_days = 366`
bilan chegaralangan — ya'ni u 500 ga HECH QACHON yetmaydi va HAR DOIM
to'liq ko'rinadi. Qarzdorlik (≤ sotuvchi soni) va arxiv (1000 rasta ×
30 kun ≈ 30 000 qator) esa yetadi.

⛔ KESISH JIM QOLMAYDI: `row_count` BUTUN DAVRNIKI, `shown_count` esa
   ko'rinayotgan sahifaniki va ikkalasi ham javobda MAJBURIY. Ekran
   «{shown} qatordan {total} tasi ko'rsatilmoqda» jumlasini shulardan
   chizadi (§8.6) — usiz direktor ekrandagi qatorlarni BUTUN DAVR deb
   o'qirdi va bu shu fazadagi eng qimmat nosozlik sinfi (§1.2).

⚠ EKSPORT SAHIFALANMAYDI (§8.6): `.xlsx` butun davrni yozadi va
  chegaraga urilsa `report_too_large` bilan RAD ETILADI — kesilgan
  faylni jimgina berish TAQIQ. Shuning uchun bu konstanta EKRAN
  sahifasi, hujjatning chegarasi emas.
"""


def _reject(code: str, http_status: int) -> HTTPException:
    """`detail` ⛔ **SATR**, lug'at EMAS — va bu KLIENT KONTRAKTI (CR-04).

    `frontend/src/lib/api-client.ts::detailOf()` `detail` ni AYNAN satr
    deb o'qiydi (`typeof parsed.data.detail === "string"`); lug'at
    yuborilganda u **bo'sh satr** qaytaradi va klientning xato shoxi
    UMUMAN ochilmaydi. Bu yerda oqibat aniq: `report-errors.ts::
    reportErrorView()` `null` qaytarardi, ekran esa `errors.generic`
    ga tushib «davrni qisqartiring» degan YAGONA foydali maslahatni
    ayta olmasdi.

    ⚠ Shakl `billing.py::_reject()` / `payments.py` / `shifts.py` bilan
      AYNI — endi to'rt marshrut oilasida BITTA konvensiya.
    """
    return HTTPException(status_code=http_status, detail=code)


_MARKET_NOT_SELECTED = "market_not_selected"
"""Sessiyada bozor tanlanmagan (**403**) — `billing.py:165-172` bilan AYNI kod."""

_PERIOD_FUTURE = "report_period_future"
_PERIOD_INVALID = "report_period_invalid"
_PERIOD_TOO_LONG = "report_period_too_long"
_TOO_LARGE = "report_too_large"
"""To'rt kod — ⛔ `frontend/src/lib/report-errors.ts::REPORT_ERROR_CODES` NING JUFTI.

⛔ REYESTR FRONTENDDA LANGAR (modul docstringining 4-bandi), bu yerda
   esa faqat SATRLAR. Ular o'sha fayldagi a'zolar bilan HARFMA-HARF bir
   xil yozilgan; `SERVER_CODE_MAP` orqali tarjima KERAK EMAS, chunki
   `isReportErrorCode()` ularni to'g'ridan-to'g'ri taniydi.
"""


def _market_id(principal: Principal) -> UUID:
    """Sessiyadagi bozor — `billing.py:175-188` dagi jufti bilan AYNI shakl."""
    market_id = principal.market_id
    if market_id is None:
        raise _reject(_MARKET_NOT_SELECTED, status.HTTP_403_FORBIDDEN)
    return market_id


def _report_period(from_date: date, to_date: date, max_days: int) -> tuple[date, date]:
    """Davrni yechadi — ⛔ YUQORI CHEGARA **KECHA**, BUGUN EMAS.

    =======================================================================
    ⛔⛔ NEGA BUGUN QAMRALMAYDI.

    `daily_charges` D+1 **04:10** da tug'iladi (`BILLING_CLOSE_CRON`,
    C-3). Ya'ni bugunni qamragan hisobot bugungi PATTANI ko'rsatmasdi,
    lekin bugungi TO'LOVNI ko'rsatardi — natija KAM KO'RSATILGAN
    `charged_soum` va sun'iy musbat `diff_soum` bo'lardi.

    ⛔ Va u EKRANDA QOLMASDI: aynan shu javob `.xlsx` bo'lib yuklab
       olinadi va imzolanadigan varaqqa tushadi (UI-SPEC §1.2 qoida 1).
       Ekranda tuzatiladigan xato faylda TARQALADI — shuning uchun
       chegara so'rov qatlamida, MAJBURLAB qo'yiladi.

    ⚠ `billing.py::_report_day()` STANDART kunni kecha qiladi; bu yerda
      standart YO'Q (ikkala parametr ham majburiy), shuning uchun bu
      MAJBURLASH — 422 bilan.
    =======================================================================

    ⛔ UCH XATO UCH ALOHIDA KOD BILAN, bittaga yig'ilmaydi: ekranda
       «Boshlanish sanasi tugash sanasidan keyin bo'lmasin» degan
       YOLG'ON sabab ko'rsatilsa, foydalanuvchi sanalarni joyini
       almashtirib ko'rardi, xato takrorlanardi va u tizimni buzuq deb
       xulosa qilardi (`report-errors.ts` ning sakkizinchi kod izohi).

    Args:
        from_date: davrning BIRINCHI kuni (kiradi).
        to_date: davrning OXIRGI kuni (kiradi).
        max_days: `settings.report_max_period_days`.

    Returns:
        Tekshirilgan `(from_date, to_date)` — ⛔ QISQARTIRILMAGAN holda.
        Server davrni JIMGINA kesmaydi; sig'masa RAD ETADI.
    """
    latest = business_today() - timedelta(days=1)
    if to_date > latest:
        # ⚠ `HTTP_422_UNPROCESSABLE_CONTENT` — RFC 9110 dagi joriy nom
        #   (`billing.py:212-214` da o'rnatilgan qoida). Eski
        #   `..._ENTITY` aliasi Starlette'da DEPRECATED.
        raise _reject(_PERIOD_FUTURE, status.HTTP_422_UNPROCESSABLE_CONTENT)
    if from_date > to_date:
        raise _reject(_PERIOD_INVALID, status.HTTP_422_UNPROCESSABLE_CONTENT)
    if (to_date - from_date).days + 1 > max_days:
        raise _reject(_PERIOD_TOO_LONG, status.HTTP_422_UNPROCESSABLE_CONTENT)
    return from_date, to_date


def _guard_row_count(row_count: int, max_rows: int) -> None:
    """`row_count` chegaradan oshsa **422 `report_too_large`** (T-08-16).

    ⛔ JIMGINA KESISH TAQIQ (UI-SPEC §8.6, O-04): kesilgan javob
       ekranda ham, faylda ham TO'LIQ ko'rinardi va direktor
       yetishmayotgan qatorlarni HECH QACHON sezmasdi. Rad javobi esa
       to'g'ri harakatni aytadi — «davrni qisqartiring».

    ⚠ Chegara `settings.report_max_rows` (50 000, `[ASSUMED]`) va u
      `Settings` da: qiymatni o'zgartirish deploy qayta qurishni talab
      qilmaydi. Tetigi 08-01 da yozilgan.
    """
    if row_count > max_rows:
        raise _reject(_TOO_LARGE, status.HTTP_422_UNPROCESSABLE_CONTENT)


def _page(total: int, limit: int, offset: int) -> slice:
    """Ko'rinadigan kesim — ⛔ SANOQ ALOHIDA, KESIM ALOHIDA.

    ⚠ Sahifalash BU QATLAMDA, SQL da EMAS va bu ONGLI: `row_count`
      BUTUN DAVRNIKI bo'lishi shart (§8.6), ya'ni so'rov baribir hamma
      qatorni qaytarishi kerak. `LIMIT`/`OFFSET` ni SQL ga tushirish
      maxrajni IKKINCHI `count(*)` so'rovi bilan olishni talab qilardi
      va ikki so'rov orasida yozilgan yangi qator ro'yxat bilan sanoqni
      ajratardi (`anomaly_list()` da o'lchangan sinf).

    ⚠ Narx chegaralangan: `row_count > report_max_rows` bo'lgan javob
      allaqachon RAD ETILGAN (`_guard_row_count()`), ya'ni bu yerda
      ro'yxat hech qachon chegaradan katta bo'lmaydi.
    """
    start = min(offset, total)
    return slice(start, min(start + limit, total))


FromDateDep = Annotated[date, Query(alias="from")]
ToDateDep = Annotated[date, Query(alias="to")]
"""⛔ IKKALASI HAM MAJBURIY — standart qiymat YO'Q (`occupancy.py:166-167` dan FARQ).

Aniqlik hisobotida `from`/`to` IXTIYORIY va standarti serverda
(`ACCURACY_WINDOW_DAYS`), chunki u BITTA ekranning yagona blokida
yashaydi. Bu yerda esa davr foydalanuvchi TANLAYDIGAN o'lchov (§4.4
davr tanlagichi) va u javobga ham, `.xlsx` sarlavhasiga ham chiqadi.
Standart qiymat berilsa parametrsiz so'rov JIM ravishda boshqa davrni
qaytarardi va imzolanadigan varaqda «qaysi davr?» savoli javobsiz
qolardi (UI-SPEC §1.2 qoida 2).
"""

LimitDep = Annotated[int, Query(ge=1, le=REPORT_PAGE_SIZE)]
OffsetDep = Annotated[int, Query(ge=0)]
"""⛔ `limit` YUQORI CHEGARASI SXEMADA — «kattaroq so'rasam ko'proq beradi» yo'li YOPIQ.

`Query(le=REPORT_PAGE_SIZE)` chegarani OpenAPI kontraktiga ham
chiqaradi, ya'ni klient uni GENERATSIYA paytida ko'radi. Qiymatni
handler ichida `min()` bilan qisqartirish (`reconciliation_repo`
naqshi) bu yerda TANLANMADI: u so'ralgan sahifadan KICHIK sahifa
qaytarardi va `shown_count` sababsiz farq qilardi.
"""


# ===========================================================================
# 1. TUSHUM — `GET /revenue`
# ===========================================================================


@router.get("/revenue", response_model=RevenueReportResponse)
async def revenue_report(
    principal: ReportViewerDep,
    session: TenantSessionDep,
    settings: SettingsDep,
    from_date: FromDateDep,
    to_date: ToDateDep,
    limit: LimitDep = REPORT_PAGE_SIZE,
    offset: OffsetDep = 0,
) -> RevenueReportResponse:
    """Davr tushumi — kunlik qatorlar, ikki ustun, ikki yig'indi (§8.2).

    =======================================================================
    ⛔ NOL KUN QATOR SIFATIDA CHIQADI (`report_repo._REVENUE_BY_DAY`).

    `generate_series` davrning HAR kunini beradi, ya'ni «o'sha kuni tizim
    ishlamadi» bilan «o'sha kuni pul yig'ilmadi» ekranda AJRALADI. Bu
    4-fazaning «YO'QLIKKA ALERT» prinsipining hisobotdagi shakli.
    =======================================================================

    ⛔ `diff_soum` SHU YERDA HISOBLANADI VA U KLIENTGA BERILMAYDI (D-03).
       Ayirish SERVERDA bir joyda bajariladi; klientda takrorlanganda u
       xato bo'lib emas, IKKINCHI JAVOB bo'lib chiqardi.

    ⚠ YIG'INDI REPODAN, PYTHON `sum()` IDAN EMAS: `revenue_by_day()` uni
      `sum(...) OVER ()` bilan AYNI so'rovda beradi va u sahifadan
      MUSTAQIL — ikkinchi joyda yozilgan qo'shish amali bir kun ajralib
      ketardi (`total_due_soum()` ning darsi).
    """
    market_id = _market_id(principal)
    period_from, period_to = _report_period(from_date, to_date, settings.report_max_period_days)

    period = await report_repo.revenue_by_day(
        session, market_id=market_id, from_date=period_from, to_date=period_to
    )
    _guard_row_count(len(period.rows), settings.report_max_rows)
    visible = period.rows[_page(len(period.rows), limit, offset)]

    return RevenueReportResponse(
        from_date=period_from,
        to_date=period_to,
        rows=[
            RevenueReportRow(
                business_date=row.business_date,
                collected_soum=row.collected_soum,
                charged_soum=row.charged_soum,
                diff_soum=row.collected_soum - row.charged_soum,
            )
            for row in visible
        ],
        total_collected_soum=period.total_collected_soum,
        total_charged_soum=period.total_charged_soum,
        row_count=len(period.rows),
        shown_count=len(visible),
    )


# ===========================================================================
# 2. QARZDORLIK REESTRI — `GET /debtors`
#
# ⛔⛔ E'LON TARTIBI MAJBURIY VA U BEZAK EMAS (`vendors.py:4-22`):
#
#     principal: ReportViewerDep            # 1) HUQUQ — hisobot
#     vendor_guard: VendorFieldGuardDep     # 2) HUQUQ — shaxsiy ma'lumot
#     intent: ReceivablesReadIntentDep      # 3) O'QISH NIYATI
#     session: TenantSessionDep             # 4) MA'LUMOT
#
# FastAPI dependency'larni AYNAN shu tartibda hal qiladi va birinchi
# `HTTPException` qolganlarini umuman chaqirmaydi. Ya'ni 403 olgan so'rov
# `audit_read` gacha YETIB KELMAYDI va jurnalga yozuv qurilmaydi.
#
# Teskari tartibda jurnalda «kassir qarzdorlar ro'yxatini o'qidi» degan
# YOLG'ON DALIL paydo bo'lardi — hech narsa o'qilmagan bo'lsa ham. Nizoni
# hal qilishda aynan shu yozuvga tayanadigan odam chalg'itilardi va bu
# jurnalning BO'SH qolishidan ham yomonroq (T-02-71).
# ===========================================================================


@router.get("/debtors", response_model=ReceivablesReportResponse)
async def receivables_report(
    principal: ReportViewerDep,
    vendor_guard: VendorFieldGuardDep,
    intent: ReceivablesReadIntentDep,
    session: TenantSessionDep,
    settings: SettingsDep,
    from_date: FromDateDep,
    to_date: ToDateDep,
    limit: LimitDep = REPORT_PAGE_SIZE,
    offset: OffsetDep = 0,
) -> ReceivablesReportResponse:
    """Qarzdorlik reestri — ⛔ ISM SERVERDA JOINLANGAN HUJJAT (D-07).

    =======================================================================
    ⛔ PITFALL 1 OCHIQ YOZILADI — D-07 NING NIYATI VA MEXANIKASI FARQ QILADI.

    D-07 «hisobot marshruti `PERSONAL_ROUTES` reyestriga kirmaydi» deydi.
    Mexanik haqiqat esa boshqa: `PERSONAL_ROUTES` — ⛔ **HOSILA**
    (`personal_data_routes(fastapi_app)` javob modelida `vendor_name` /
    `phone` / `full_name` bo'lgan HAR `GET` ni AVTOMATIK oladi, ichma-ich
    rekursiya bilan). Bu javobda ism BOR, ya'ni marshrut o'sha to'plamga
    ⛔ **O'ZI** tushadi.

    ⛔ VA BU D-07 NING NIYATIGA MOS: taqiq **OPERATIV MOLIYAVIY JSON**
       marshrutlariga (`/billing/charges`, `/reconciliation/cases`) ism
       qo'shmaslikka tegishli — ular ekranda ishlatiladi va ism
       `GET /vendors` dan KLIENTDA joinlanadi (C-10, §5.5). Ular bu
       reja bilan ⛔ TEGILMAYDI.

    Bu esa BOSHQA SINF: HUJJAT. Uning butun mavjud bo'lish sababi
    «kimdan undirish kerak?» savoliga qog'ozda javob berish, va u shuning
    uchun BITTA `audit_read` yozadi (06 №9 da rad etilgan (a) yo'li —
    klientda hamma sahifani tortish — jurnalni HAR sahifada bittadan
    yozuv bilan to'ldirardi).

    ⚠ `MINIMUM_PERSONAL_ROUTES` — QUYI chegara (`>=`), ya'ni to'plamning
      o'sishi hech qanday darvozani buzmaydi.
    =======================================================================

    ⛔ `phone` JAVOBDA YO'Q (UI-SPEC O-03): telefon — ALOQA ma'lumoti va
       u eksportga tushib fayl bo'lib tarqalardi. Qarz undirish oqimi
       ALLAQACHON bot eslatmasi (BOT-03).

    ⚠ YIG'INDI BUTUN DAVRNIKI, sahifaniki EMAS (§8.6): u kesimdan OLDIN,
      to'liq ro'yxatdan hisoblanadi. Repo bu yerda envelope BERMAYDI
      (`receivables()` yalang'och ro'yxat qaytaradi), ya'ni qo'shish
      SERVERNING shu qatlamida bajariladi — klientda EMAS.
    """
    market_id = _market_id(principal)
    period_from, period_to = _report_period(from_date, to_date, settings.report_max_period_days)

    rows = await report_repo.receivables(
        session, market_id=market_id, from_date=period_from, to_date=period_to
    )
    _guard_row_count(len(rows), settings.report_max_rows)
    visible = rows[_page(len(rows), limit, offset)]

    # ⛔ NIYAT JAVOB QURILISHIDAN OLDIN TO'LDIRILADI: fon vazifasi
    #    `intent` obyektini KO'RADI va u yerda «qaysi davr, nechta qator»
    #    yozilgan bo'lishi kerak. Bo'sh niyat jurnalda «kimdir nimadir
    #    o'qidi» degan foydasiz qator qoldirardi (D-09 ning butun
    #    mazmuni — «kim, qachon, QAYSI DAVRNI ko'rdi»).
    #
    # ⚠ `result_count` — BUTUN DAVRNIKI, ko'rinayotgan sahifaniki EMAS:
    #   jurnal «bu odam necha qarzdorning ismini ko'rdi» degan savolga
    #   javob beradi va sahifa soni o'sha savolga javob bermasdi.
    intent.filters = {
        "from_date": period_from.isoformat(),
        "to_date": period_to.isoformat(),
    }
    intent.result_count = len(rows)

    return ReceivablesReportResponse(
        from_date=period_from,
        to_date=period_to,
        rows=[
            ReceivablesReportRow(
                vendor_id=row.vendor_id,
                vendor_name=row.vendor_name,
                # ⛔ SATRDAN RO'YXATGA SHU YERDA: repo `string_agg` bilan
                #    `code_sort` TARTIBIDA yopishtiradi, ya'ni bo'linish
                #    tartibni SAQLAYDI. `None` -> BO'SH RO'YXAT: «davrda
                #    biriktirish yo'q» — nol NATIJA, yo'qlik emas.
                stall_codes=[] if row.stall_codes is None else row.stall_codes.split(", "),
                outstanding_soum=row.outstanding_soum,
                oldest_debt_date=row.oldest_unpaid_date,
            )
            for row in visible
        ],
        total_outstanding_soum=sum(row.outstanding_soum for row in rows),
        row_count=len(rows),
        shown_count=len(visible),
    )


# ===========================================================================
# 3. NOMUVOFIQLIK ARXIVI — `GET /anomalies`
# ===========================================================================


@router.get("/anomalies", response_model=AnomalyArchiveResponse)
async def anomaly_archive_report(
    principal: ReportViewerDep,
    session: TenantSessionDep,
    settings: SettingsDep,
    from_date: FromDateDep,
    to_date: ToDateDep,
    limit: LimitDep = REPORT_PAGE_SIZE,
    offset: OffsetDep = 0,
) -> AnomalyArchiveResponse:
    """Davr arxivi — ikki sinf bitta xronologiyada, ikki sanoq alohida (§8.5).

    ⛔ `audit_read` BU MARSHRUTDA YO'Q — VA BU ONGLI, «UNUTILGAN» EMAS.
       Javobda shaxsiy maydon yo'q: rasta KODI, sana, sinf nomi, case
       holati va kadr IDENTIFIKATORI. Bu yerga audit qo'yish jurnalni
       har hisobot ochilishida shovqin bilan to'ldirardi va HAQIQIY
       o'qish hodisasi (`/debtors`) ko'milib ketardi
       (`audit.py` da ATAYIN rad etilgan «blanket middleware» holati).

    ⛔ IKKI SANOQ REPODAN va ular sahifadan MUSTAQIL: `unpaid_count` va
       `unregistered_count` BUTUN DAVRNIKI. Ularni ko'rinayotgan
       qatorlardan qayta hisoblash sahifa almashganda sonlarni
       o'zgartirardi — ya'ni «bu davrda 12 ta nomuvofiqlik» degan gap
       skroll bilan yolg'onga aylanardi.

    ⛔ UCHINCHI, «yig'indi» SANOG'I YO'Q (D-05): «band, lekin to'lovsiz»
       UNDIRISHNI, «ro'yxatga olinmagan savdo» esa RO'YXATGA OLISHNI
       talab qiladi. Bitta songa siqilgan hisobot qaysi sinf o'sganini
       yashirardi.
    """
    market_id = _market_id(principal)
    period_from, period_to = _report_period(from_date, to_date, settings.report_max_period_days)

    archive = await report_repo.anomaly_archive(
        session, market_id=market_id, from_date=period_from, to_date=period_to
    )
    _guard_row_count(len(archive.rows), settings.report_max_rows)
    visible = archive.rows[_page(len(archive.rows), limit, offset)]

    return AnomalyArchiveResponse(
        from_date=period_from,
        to_date=period_to,
        rows=[
            AnomalyArchiveRowResponse(
                # ⛔ MANBA `service_date` — PATTA kuni. Nom klient
                #    kontraktidan (`anomalyArchiveRowSchema.business_date`),
                #    ma'no esa repodaniki va u `payments.business_date`
                #    bilan ARALASHTIRILMAYDI (Pitfall 14).
                business_date=row.service_date,
                kind=row.kind,
                stall_code=row.stall_code,
                snapshot_id=row.evidence_snapshot_id,
                case_status=row.case_status,
            )
            for row in visible
        ],
        unpaid_count=archive.unpaid_count,
        unregistered_count=archive.unregistered_count,
        row_count=len(archive.rows),
        shown_count=len(visible),
    )
