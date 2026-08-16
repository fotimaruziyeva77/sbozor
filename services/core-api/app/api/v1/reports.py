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

from app.deps import Principal, require_permission
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


def _page(rows: list[object], limit: int, offset: int) -> tuple[int, int]:
    """`(start, stop)` — ro'yxat kesimining chegaralari.

    ⚠ Sahifalash BU QATLAMDA, SQL da EMAS va bu ONGLI: `row_count`
      BUTUN DAVRNIKI bo'lishi shart (§8.6), ya'ni so'rov baribir hamma
      qatorni qaytarishi kerak. `LIMIT`/`OFFSET` ni SQL ga tushirish
      maxrajni IKKINCHI `count(*)` so'rovi bilan olishni talab qilardi
      va ikki so'rov orasida yozilgan yangi qator ro'yxat bilan sanoqni
      ajratardi (`anomaly_list()` da o'lchangan sinf).

    ⚠ Narx chegaralangan: `row_count > report_max_rows` bo'lgan javob
      allaqachon RAD ETILGAN (`_guard_row_count()`).
    """
    start = min(offset, len(rows))
    return start, min(start + limit, len(rows))


LimitDep = Annotated[int, Query(ge=1, le=REPORT_PAGE_SIZE)]
OffsetDep = Annotated[int, Query(ge=0)]
"""⛔ `limit` YUQORI CHEGARASI SXEMADA — «kattaroq so'rasam ko'proq beradi» yo'li YOPIQ.

`Query(le=REPORT_PAGE_SIZE)` chegarani OpenAPI kontraktiga ham
chiqaradi, ya'ni klient uni GENERATSIYA paytida ko'radi. Qiymatni
handler ichida `min()` bilan qisqartirish (`reconciliation_repo`
naqshi) bu yerda TANLANMADI: u so'ralgan sahifadan KICHIK sahifa
qaytarardi va `shown_count` sababsiz farq qilardi.
"""
