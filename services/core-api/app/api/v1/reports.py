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

import re
import unicodedata
from datetime import date, timedelta
from typing import TYPE_CHECKING, Annotated, Final
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from sbozor_core.enums import AuditAction
from sbozor_core.timeutil import business_today
from sqlalchemy.exc import IntegrityError

from app.api.v1.imports import (
    XLSX_SUFFIX,
    _conflict,
    _locale_of,
    _read,
    _read_bounded,
    _reject_if_invalid,
    _xlsx_response,
)
from app.deps import Principal, SettingsDep, TenantSessionDep, require_permission
from app.repositories import report_repo
from app.repositories.import_repo import ImportRepository
from app.repositories.market_repo import MarketRepository
from app.repositories.occupancy_repo import OccupancyRepository
from app.schemas import (
    AnomalyArchiveResponse,
    AnomalyArchiveRowResponse,
    LedgerImportResponse,
    ReceivablesReportResponse,
    ReceivablesReportRow,
    RevenueReportResponse,
    RevenueReportRow,
    ThreeWayReportResponse,
    ThreeWayReportRow,
)
from app.security.audit import (
    TABLE_LEDGER_ENTRIES,
    TABLE_VENDORS,
    AuditReadIntent,
    audit_read,
    write_app_audit,
)
from app.security.rbac import Permission
from app.services import import_validator, xlsx_export
from app.services.accuracy_report import accuracy_report

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy.ext.asyncio import AsyncSession

# ⚠ `StreamingResponse` ISH VAQTIDA IMPORT QILINADI, `TYPE_CHECKING`
#   OSTIDA EMAS — VA BU `date`/`UUID` bilan AYNI SABAB. U
#   `@router.get(..., response_class=StreamingResponse)` da ARGUMENT
#   sifatida, ya'ni dekorator BAJARILAYOTGANDA kerak bo'ladi; annotatsiya
#   esa `from __future__ import annotations` ostida SATR bo'lib qoladi va
#   FastAPI uni javob turini aniqlash uchun YECHISHI kerak.

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

LedgerImporterDep = Annotated[Principal, Depends(require_permission(Permission.STALL_MANAGE))]
"""⛔ DAFTAR IMPORTI — `STALL_MANAGE`, `REPORT_VIEW` EMAS (D-20, 08-14).

`REPORT_VIEW` bu faylning qolgan hamma joyida O'QISH huquqi; daftar
importi esa YOZUV amali va uni bajaruvchi odam bajaruvchi lavozimda
turadi: nazoratchi yoki bozor admini, ⛔ KASSIR EMAS.

⛔ IKKI HUQUQ IKKI TOMONDAN QULFLAYDI VA U BUGUNGI MATRITSADA
   O'LCHANADI: kassirda `report_view` ham, `stall_manage` ham YO'Q;
   direktorda `report_view` BOR, lekin `stall_manage` YO'Q — ya'ni u
   hisobotni o'qiydi, daftarni esa YOZA OLMAYDI. Bu farq
   `test_three_way.py` ning rol matritsasida nom bilan o'lchanadi.

⚠ «Nazoratchi» LAVOZIM sifatida o'qiladi: `ROLE_PERMISSIONS[INSPECTOR]`
  bugun AYNAN `{OCCUPANCY_REVIEW}` (T-05-58) va unga yozuv huquqi berish
  5-fazaning ko'r audit qarorini kengaytirardi. Buyurtmachi
  nazoratchining O'ZI yuklashini talab qilsa, bu RBAC o'zgarishi va u
  ALOHIDA qaror bo'ladi.
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
# QATOR O'GIRUVCHILAR — ⛔ EKRAN VA FAYL AYNAN SHU YERDAN YURADI
#
# ⛔⛔ NEGA UCH FUNKSIYA, NEGA HANDLER ICHIDA EMAS.
#
# Har hisobotning IKKI iste'molchisi bor: JSON marshruti va `.xlsx`
# eksporti. O'girish handler ichida qolsa, u IKKI marta yozilardi va
# `diff_soum` kabi bitta ayirish IKKI JOYDA yashardi — ya'ni ekran bilan
# imzolanadigan varaq bir kun BOSHQA son ko'rsatardi. Nizoda so'raladigan
# savol esa aynan shu: «qaysi raqamni aytdingiz?» (D-03, 05-14 darsi).
#
# ⚠ SAHIFALASH BU YERDA YO'Q: o'giruvchilar BUTUN davrni beradi va kesim
#   JSON handlerida qo'llanadi. Eksport esa umuman kesilmaydi (§8.6).
# ===========================================================================


def _revenue_rows(rows: Sequence[report_repo.RevenueRow]) -> list[RevenueReportRow]:
    """Kunlik tushum qatorlari — ⛔ `diff_soum` NING YAGONA hisoblanish joyi."""
    return [
        RevenueReportRow(
            business_date=row.business_date,
            collected_soum=row.collected_soum,
            charged_soum=row.charged_soum,
            diff_soum=row.collected_soum - row.charged_soum,
        )
        for row in rows
    ]


def _receivable_rows(rows: Sequence[report_repo.ReceivableRow]) -> list[ReceivablesReportRow]:
    """Qarzdorlik qatorlari — ⛔ SATRDAN RO'YXATGA o'girish shu yerda.

    Repo `string_agg` bilan `code_sort` TARTIBIDA yopishtiradi, ya'ni
    bo'linish tartibni SAQLAYDI. `None` -> BO'SH RO'YXAT: «davrda
    biriktirish yo'q» — nol NATIJA, yo'qlik emas.
    """
    return [
        ReceivablesReportRow(
            vendor_id=row.vendor_id,
            vendor_name=row.vendor_name,
            stall_codes=[] if row.stall_codes is None else row.stall_codes.split(", "),
            outstanding_soum=row.outstanding_soum,
            oldest_debt_date=row.oldest_unpaid_date,
        )
        for row in rows
    ]


def _archive_rows(rows: Sequence[report_repo.AnomalyArchiveRow]) -> list[AnomalyArchiveRowResponse]:
    """Arxiv qatorlari — ⛔ MANBA `service_date` (PATTA kuni, Pitfall 14)."""
    return [
        AnomalyArchiveRowResponse(
            business_date=row.service_date,
            kind=row.kind,
            stall_code=row.stall_code,
            snapshot_id=row.evidence_snapshot_id,
            case_status=row.case_status,
        )
        for row in rows
    ]


def _wire_diff_class(diff_class: str | None) -> str | None:
    """`match` -> `None`; qolgan uch sinf O'ZGARMAYDI — ⛔ YAGONA o'girish joyi.

    =======================================================================
    ⛔⛔ NEGA SERVER `"match"` NI SIM USTIGA CHIQARMAYDI.

    `api-types.ts::DIFF_CLASSES` — AYNAN UCH a'zo (`ledger_over`,
    `system_over`, `ai_mismatch`) va `match` unda ATAYIN yo'q; javob
    sxemasi esa `diff_class` ni `z.string().nullable()` deb o'qiydi,
    ya'ni `"match"` PARSE'dan O'TIB KETADI. Klient uni NOMA'LUM sinf
    deb ZAXIRA YORLIQ bilan chizardi — natijada 287 ta mos qator badge
    olardi va 13 ta HAQIQIY farq ular ostida KO'MILIB ketardi (§13.4:
    «Mos qator badge OLMAYDI»).

    ⛔ Nosozlik JIMGINA bo'lardi: status kodi 200, sxema yashil, xato
       jurnalida hech nima — faqat imzolanadigan varaqning ma'nosi
       yo'qolardi.

    ⚠ SERVERDA SINF NOM BILAN QOLADI (`report_repo.DIFF_MATCH`):
      `matched_count` AYNAN shu nomga tayanadi. Repoda ham `None` qilib
      qo'yish uni «AI o'lchanmagan» holati bilan ARALASHTIRARDI — u ham
      `None` va u sanoqqa TUSHMAYDI.
    =======================================================================
    """
    return None if diff_class == report_repo.DIFF_MATCH else diff_class


def _three_way_rows(rows: Sequence[report_repo.ThreeWayRow]) -> list[ThreeWayReportRow]:
    """Solishtiruv qatorlari — ⛔ `vendor_name` JSON GA KO'CHIRILMAYDI.

    Ism `.xlsx` quruvchisiga TO'G'RIDAN-TO'G'RI repo qatoridan boradi,
    ya'ni u bu o'giruvchidan umuman o'tmaydi. Sabab klient kontraktida:
    `threeWayRowSchema` — `strictObject` va ortiqcha maydon butun
    sahifani parse chegarasida yiqitardi (`schemas.ThreeWayReportRow`
    docstringi).
    """
    return [
        ThreeWayReportRow(
            stall_code=row.stall_code,
            ledger_soum=row.ledger_soum,
            system_soum=row.system_soum,
            ai_expected_soum=row.ai_expected_soum,
            diff_class=_wire_diff_class(row.diff_class),
        )
        for row in rows
    ]


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
    rows = _revenue_rows(period.rows)
    visible = rows[_page(len(rows), limit, offset)]

    return RevenueReportResponse(
        from_date=period_from,
        to_date=period_to,
        rows=visible,
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

    found = await report_repo.receivables(
        session, market_id=market_id, from_date=period_from, to_date=period_to
    )
    _guard_row_count(len(found), settings.report_max_rows)
    rows = _receivable_rows(found)
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
        rows=visible,
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
    rows = _archive_rows(archive.rows)
    visible = rows[_page(len(rows), limit, offset)]

    return AnomalyArchiveResponse(
        from_date=period_from,
        to_date=period_to,
        rows=visible,
        unpaid_count=archive.unpaid_count,
        unregistered_count=archive.unregistered_count,
        row_count=len(archive.rows),
        shown_count=len(visible),
    )


# ===========================================================================
# 4. `.xlsx` EKSPORTI — TO'RT `GET` MARSHRUTI (08-12, RECON-04)
#
# =========================================================================
# ⛔⛔ METOD `GET`, `POST` EMAS — VA SABAB DARVOZADA, DID'DA EMAS (R-3).
#
# `tests/tenancy/test_personal_data_coverage.py::get_routes()` FAQAT
# `GET` marshrutlarini yuradi (D-09 O'QISH haqida). Eksport `POST`
# bo'lganda `debtors.xlsx` na `BINARY_PERSONAL_ROUTES` ga, na
# `NON_PERSONAL_BINARY_ROUTES` ga tushardi va YOPIQLIK testi ham uni
# KO'RMASDI — ya'ni «har bayt-marshrut tasniflanadi» kafolati AYNAN eng
# xavfli marshrutda, sotuvchi F.I.Sh. chiqadigan joyda teshilardi. Bu
# «darvozani chetlash» yechimi bo'lardi va u shu rejada ATAYIN rad
# etilgan.
#
# ⛔ `?format=xlsx` HAM EMAS: bitta marshrut ikki javob turini berardi
#    va `response_model` YOLG'ON bo'lardi (bir shox JSON, ikkinchisi
#    bayt). Klient ham buni bilib turadi va ikki yo'l quradi
#    (`report-queries.ts::buildReportDataPath` ↔ `buildReportPath`).
#
# =========================================================================
# ⛔⛔ FAYL NOMINI SERVER QURADI (D-06, UI-SPEC §12.3).
#
# Bozor nomi O'ZBEKCHA MATN: bo'sh joy, apostrof, qo'shtirnoq, kirill.
# U `Content-Disposition` sarlavhasiga tushadi — HTTP protokolining bir
# qismiga. Slug qoidasi ikki tilda IKKI MARTA yozilsa bir kun ajralib
# ketardi (server `karmana_revenue_....xlsx`, klient
# `Karmana-bozori_....xlsx`) va «qaysi biri hujjat?» savoli javobsiz
# qolardi. Klient (`report-queries.ts::filenameFrom()`) nomni faqat
# O'QIYDI.
#
# =========================================================================
# ⛔⛔ TIL PROFILDAN, SO'ROV PARAMETRIDAN EMAS (D-06).
#
# `?locale=` qo'shilsa bitta haqiqat manbai ikkiga bo'linardi va bir
# foydalanuvchi ekranda o'zbekcha, faylda ruscha hisobot olardi.
# `_locale_of()` `imports.py` DAN IMPORT qilinadi — ikkinchi nusxa
# yozilsa profil o'qish qoidasi (topilmasa uz-Latn) ikki joyda yashardi.
# ===========================================================================

_SLUG_FALLBACK: Final = "bozor"
"""Bozor nomi butunlay ASCII'ga o'girilmaganda ishlatiladigan nom.

⛔ BO'SH SLUG TAQIQ: nom `_revenue_2026-08-01_2026-08-07.xlsx` bo'lib
   boshlanardi va ba'zi fayl menejerlari uni yashirin fayl deb
   ko'rsatardi.
"""

_SLUG_MAX_LENGTH: Final = 40
"""Slugning eng katta uzunligi — sarlavha cheksiz o'smasin.

Ba'zi proksilar sarlavha uzunligini cheklaydi va uzun nom butun javobni
rad etardi; bozor nomining birinchi 40 belgisi esa uni ajratish uchun
yetarlidan ham ko'p.
"""

_CYRILLIC_TO_LATIN: Final[dict[str, str]] = {
    "а": "a", "б": "b", "в": "v", "г": "g", "ғ": "g", "д": "d", "е": "e",
    "ё": "yo", "ж": "j", "з": "z", "и": "i", "й": "y", "к": "k", "қ": "q",
    "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r", "с": "s",
    "т": "t", "у": "u", "ў": "o", "ф": "f", "х": "x", "ҳ": "h", "ц": "ts",
    "ч": "ch", "ш": "sh", "щ": "sh", "ъ": "", "ы": "i", "ь": "", "э": "e",
    "ю": "yu", "я": "ya",
}  # fmt: skip
"""Kirill -> lotin jadvali — ⛔ BELGILAR TASHLAB YUBORILMAYDI.

`unicodedata.normalize("NFKD")` kirillni ASCII'ga o'gira OLMAYDI (u
faqat diakritikani ajratadi), ya'ni jadvalsiz «Кармана» butunlay
yo'qolardi va HAR kirill nomli bozor AYNAN BIR XIL fayl nomini olardi:
`bozor_revenue_....xlsx`. O'shanda ikki bozorning hujjatlari bitta
papkada bir-birini ustiga yozardi.

⚠ Jadval O'ZBEK kirillicha alifbosi uchun (`ғ`, `қ`, `ў`, `ҳ` bor).
  Ro'yxatda yo'q belgi keyingi qadamda `-` ga aylanadi, ya'ni nom
  baribir ASCII bo'lib qoladi.
"""


def _ascii_slug(name: str) -> str:
    """Bozor nomini ASCII slug'ga aylantiradi — ⛔ YAGONA joyda (D-06).

    Ketma-ketlik: kichik harf -> kirilldan lotinga -> NFKD (diakritika
    tushadi) -> ASCII'dan tashqarisi tashlanadi -> `[a-z0-9]` dan
    boshqasi `-` ga -> uzunlik cheklanadi.

    ⛔ `'` (apostrof) ALOHIDA e'tibor talab qiladi: o'zbek lotin
       alifbosida u HARFNING QISMI (`o'`, `g'`) va bu yerda `-` ga
       aylanadi — ya'ni «Do'stlik» `do-stlik` bo'ladi. Bu ONGLI: nom
       INSON UCHUN mo'ljallangan yorliq, IDENTIFIKATOR emas
       (identifikator — davr va hisobot turi).
    """
    lowered = name.casefold()
    latin = "".join(_CYRILLIC_TO_LATIN.get(char, char) for char in lowered)
    folded = unicodedata.normalize("NFKD", latin).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", folded).strip("-")
    return slug[:_SLUG_MAX_LENGTH].strip("-") or _SLUG_FALLBACK


def _export_filename(market_name: str, kind: str, period: xlsx_export.ReportPeriod) -> str:
    """`{bozor-slug}_{tur}_{from}_{to}.xlsx` — ⛔ TO'LIQ ASCII.

    Davr NOMDA ham bor: bir nechta hisobot bitta papkaga tushganda ular
    faqat shu bilan ajraladi (UI-SPEC §1.2 qoida 2). Sanalar ISO, ya'ni
    fayl menejerida saralash XRONOLOGIK bo'ladi.
    """
    return (
        f"{_ascii_slug(market_name)}_{kind}"
        f"_{period.from_date.isoformat()}_{period.to_date.isoformat()}{XLSX_SUFFIX}"
    )


async def _export_head(
    session: AsyncSession,
    principal: Principal,
    *,
    kind: str,
    from_date: date,
    to_date: date,
    max_days: int,
) -> tuple[UUID, xlsx_export.ReportPeriod, str, str]:
    """To'rtala eksportning UMUMIY boshi — bozor, davr, til, fayl nomi.

    Returns:
        `(market_id, period, locale, filename)`.

    ⚠ Nusxa YOZILMAYDI: to'rt marshrutda takrorlangan «bozorni ol,
      davrni yech, tilni oq, nomni qur» ketma-ketligi bir kun uchtasida
      yangilanib, to'rtinchisida qolib ketardi.

    ⚠ Bozor qatori topilmasa (`None`) nom `_SLUG_FALLBACK` ga tushadi va
      ISTISNO ko'tarilmaydi: bu holat RLS konteksti bilan ta'minlangan
      so'rovda amalda mumkin emas, lekin u yerda 500 berish hujjatni
      butunlay to'sardi — sababi esa faqat NOMGA tegishli bo'lardi.
    """
    market_id = _market_id(principal)
    period_from, period_to = _report_period(from_date, to_date, max_days)
    period = xlsx_export.ReportPeriod(from_date=period_from, to_date=period_to)

    locale = await _locale_of(session, principal)
    market = await MarketRepository(session).current_market()

    return (
        market_id,
        period,
        locale,
        _export_filename("" if market is None else market.name, kind, period),
    )


ReceivablesExportIntentDep = Annotated[
    AuditReadIntent,
    Depends(audit_read(TABLE_VENDORS, reason="report_receivables_export")),
]
"""⛔ EKSPORTNING `reason` I JSON NIKIDAN FARQ QILADI — VA BU ONGLI.

`report_receivables` — «ekranda ko'rdi», `report_receivables_export` —
«FAYLNI OLDI». Ikkinchisi jiddiyroq hodisa: fayl tizimdan CHIQIB
ketadi va u boshqa odamning pochtasida, USB'sida, chop etilgan
varaqda yashashda davom etadi. Bir xil `reason` bilan jurnalni
o'qiyotgan odam bu farqni ko'rmasdi — `vendors.py:105-113` da
o'rnatilgan qoidaning aynan takrori.

⛔ BITTA SO'ROV = BITTA YOZUV: eksport butun davrni yozadi, ya'ni
   «har sotuvchi uchun bitta yozuv» xatosi bu yerda JSON dagidan ham
   shovqinliroq bo'lardi.
"""


@router.get("/revenue.xlsx", response_class=StreamingResponse)
async def revenue_export(
    principal: ReportViewerDep,
    session: TenantSessionDep,
    settings: SettingsDep,
    from_date: FromDateDep,
    to_date: ToDateDep,
) -> StreamingResponse:
    """Davr tushumi `.xlsx` bo'lib — ⛔ SAHIFALANMAYDI (§8.6).

    `limit`/`offset` parametrlari ATAYIN YO'Q: hujjat BUTUN davrni
    yozadi va chegaraga urilsa `report_too_large` bilan RAD ETILADI.
    Kesilgan faylni jimgina berish TAQIQ — chop etilgan varaqdan
    tushib qolgan qatorlarni hech kim sezmasdi.
    """
    market_id, period, locale, filename = await _export_head(
        session,
        principal,
        kind="revenue",
        from_date=from_date,
        to_date=to_date,
        max_days=settings.report_max_period_days,
    )

    found = await report_repo.revenue_by_day(
        session, market_id=market_id, from_date=period.from_date, to_date=period.to_date
    )
    _guard_row_count(len(found.rows), settings.report_max_rows)

    payload = xlsx_export.build_revenue_workbook(_revenue_rows(found.rows), locale, period)
    return _xlsx_response(payload, filename)


@router.get("/debtors.xlsx", response_class=StreamingResponse)
async def receivables_export(
    principal: ReportViewerDep,
    vendor_guard: VendorFieldGuardDep,
    intent: ReceivablesExportIntentDep,
    session: TenantSessionDep,
    settings: SettingsDep,
    from_date: FromDateDep,
    to_date: ToDateDep,
) -> StreamingResponse:
    """Qarzdorlik reestri `.xlsx` — ⛔ SHAXSIY HUJJAT, AUDIT MAJBURIY.

    =======================================================================
    ⛔⛔ E'LON TARTIBI MAJBURIY VA U BEZAK EMAS (JSON marshrutidagi
        bilan AYNI): huquq -> huquq -> niyat -> ma'lumot. FastAPI
        dependency'larni shu tartibda hal qiladi, ya'ni 403 olgan so'rov
        `audit_read` gacha YETIB KELMAYDI. Teskari tartibda jurnalda
        «kassir qarzdorlik hujjatini yuklab oldi» degan YOLG'ON DALIL
        paydo bo'lardi — hech nima berilmagan bo'lsa ham (T-02-71).

    ⛔ JAVOBNING MODELI YO'Q, ya'ni `PERSONAL_FIELDS` darvozasi bu
       marshrutni HECH QACHON topa olmaydi. Shuning uchun u
       `test_personal_data_coverage.py::BINARY_PERSONAL_ROUTES` ga
       QO'LDA yoziladi va o'sha yerdan `audit_read` + huquq talabi
       MEXANIK ravishda qaytadi.
    =======================================================================
    """
    market_id, period, locale, filename = await _export_head(
        session,
        principal,
        kind="debtors",
        from_date=from_date,
        to_date=to_date,
        max_days=settings.report_max_period_days,
    )

    found = await report_repo.receivables(
        session, market_id=market_id, from_date=period.from_date, to_date=period.to_date
    )
    _guard_row_count(len(found), settings.report_max_rows)

    # ⛔ NIYAT HUJJAT QURILISHIDAN OLDIN TO'LDIRILADI (JSON marshrutidagi
    #    bilan AYNI sabab): bo'sh niyat jurnalda «kimdir nimadir o'qidi»
    #    degan foydasiz qator qoldirardi.
    intent.filters = {
        "from_date": period.from_date.isoformat(),
        "to_date": period.to_date.isoformat(),
        "format": "xlsx",
    }
    intent.result_count = len(found)

    payload = xlsx_export.build_receivables_workbook(_receivable_rows(found), locale, period)
    return _xlsx_response(payload, filename)


@router.get("/anomalies.xlsx", response_class=StreamingResponse)
async def anomaly_archive_export(
    principal: ReportViewerDep,
    session: TenantSessionDep,
    settings: SettingsDep,
    from_date: FromDateDep,
    to_date: ToDateDep,
) -> StreamingResponse:
    """Nomuvofiqlik arxivi `.xlsx` — ⛔ DALIL IDENTIFIKATOR, KADR EMAS.

    ⛔ `audit_read` BU MARSHRUTDA YO'Q va bu ONGLI (JSON juftidagi bilan
       AYNI sabab): javobda shaxsiy maydon yo'q — rasta KODI, sana,
       sinf nomi, case holati va kadr IDENTIFIKATORI.

    ⛔ KADR BAYTI, OMBOR KALITI VA IMZOLANGAN HAVOLA FAYLGA TUSHMAYDI
       (07 D-03, T-06-81): u yerda birorta huquq darvozasi ishlamaydi.
    """
    market_id, period, locale, filename = await _export_head(
        session,
        principal,
        kind="anomalies",
        from_date=from_date,
        to_date=to_date,
        max_days=settings.report_max_period_days,
    )

    archive = await report_repo.anomaly_archive(
        session, market_id=market_id, from_date=period.from_date, to_date=period.to_date
    )
    _guard_row_count(len(archive.rows), settings.report_max_rows)

    payload = xlsx_export.build_discrepancies_workbook(_archive_rows(archive.rows), locale, period)
    return _xlsx_response(payload, filename)


@router.get("/accuracy.xlsx", response_class=StreamingResponse)
async def accuracy_export(
    principal: ReportViewerDep,
    session: TenantSessionDep,
    settings: SettingsDep,
    from_date: FromDateDep,
    to_date: ToDateDep,
) -> StreamingResponse:
    """AI aniqlik hisoboti `.xlsx` — ⛔ MAVJUD XIZMATDAN, YANGI HISOBSIZ.

    =======================================================================
    ⛔⛔ D-09: BU YERDA HISOB-KITOB YOZILMAYDI.

    Manba — `accuracy_report()`, ya'ni `GET /occupancy/accuracy` (05-12)
    ishlatadigan AYNI sof funksiya va AYNI repozitoriy so'rovi. Ikkinchi
    hisob arifmetik jihatdan to'g'ri bo'lib turib BOSHQA savolga javob
    berardi (05-14 darsi) va «5,4 % mi, 3,8 % mi?» savoli aynan nizo
    paytida so'ralardi.

    ⚠ IKKI FILTR (`purpose='eval'`, `queue_kind='blind_audit'`) SHU
      YERDA YOZILMAYDI — ular `accuracy_report()` ning ichida
      (`occupancy.py::occupancy_accuracy()` bilan AYNI qaror).
    =======================================================================

    ⛔ `/reports/accuracy` (JSON) MARSHRUTI QO'SHILMAYDI: aniqlikning
       JSON yuzasi ALLAQACHON `GET /occupancy/accuracy` da yashaydi va
       ikkinchisi ikkinchi haqiqat manbai bo'lardi. Klient ham shuni
       biladi — `report-queries.ts` `accuracy` uchun `occupancy-queries`
       kalitini ishlatadi.

    ⚠ DAVR PARAMETRLARI MAJBURIY va `_report_period()` qoidasida —
      `/occupancy/accuracy` dagi IXTIYORIY `from`/`to` dan FARQLI.
      Standart davrli hujjat imzolanadigan varaqda «qaysi davr?»
      savolini javobsiz qoldirardi.
    """
    market_id, period, locale, filename = await _export_head(
        session,
        principal,
        kind="accuracy",
        from_date=from_date,
        to_date=to_date,
        max_days=settings.report_max_period_days,
    )

    repo = OccupancyRepository(session, market_id)
    report = accuracy_report(await repo.accuracy_rows(period.from_date, period.to_date))

    payload = xlsx_export.build_accuracy_workbook(report, locale, period)
    return _xlsx_response(payload, filename)


# ===========================================================================
# 5. QOG'OZ DAFTAR IMPORTI — `POST /compare/ledger?day=` (D-17, 08-14)
#
# =========================================================================
# ⛔⛔ YO'L KLIENT KONTRAKTIDAN: `/compare/ledger`, reja aytgan
#     `/three-way/ledger` EMAS.
#
# `report-queries.ts::uploadLedger()` AYNAN `${REPORTS_PATH}/compare/
# ledger?day=` ga boradi va u 08-03 (TO'LQIN 1) da yozilib, allaqachon
# jo'natilgan. Bu modul docstringining 2-bandidagi qarorning aynan
# takrori: SERVER KLIENTNI KUZATADI. Boshqa nom tanlansa nosozlik
# JIMGINA bo'lardi — komponent testlari mock bilan yashil qolardi va
# 404 faqat jonli ekranda ko'rinardi.
#
# =========================================================================
# ⛔⛔ BU PREFIKSDAGI YAGONA YOZUV MARSHRUTI — VA U HISOBOTNI
#     «TUZATMAYDI».
#
# `main.py` ning 08-07 blokidagi «bu prefiksda POST YO'Q» qoidasining
# sababi hisobotning HOSILA ekani edi (D-03): hisobotni tahrirlash uni
# ikkinchi haqiqat manbaiga aylantirardi. Daftar esa hisobot EMAS —
# u TIZIMDA UMUMAN YO'Q, tashqi qog'ozdan keladigan UCHINCHI manba, ya'ni
# uning yozuv yo'li o'sha taqiqning ostiga tushmaydi. Marshrut baribir
# yopiq to'plam testida NOM bilan ko'rinadi.
#
# =========================================================================
# ⛔⛔ UCH DARVOZA `imports.py` DAN IMPORT QILINADI, KO'CHIRILMAYDI.
#
#   `_read_bounded()` -> bayt chegarasi (fayl xotiraga TO'LIQ olinmasdan)
#   `_read()`         -> ZIP/XML bomba, qator/ustun/varaq chegaralari
#   `validate_ledger_rows()` -> mazmun
#
# TARTIB MAJBURIY: birinchisi ikkinchisining O'RNINI BOSMAYDI —
# `read_rows()` `len(raw)` ni tekshirganda baytlar ALLAQACHON xotirada
# bo'lardi (T-02-89 / T-08-58). Ikkinchi nusxa yozilsa chegaralar ikki
# joyda yashardi va biri sozlamadan, ikkinchisi modul standartidan
# yurardi.
# ===========================================================================

DayDep = Annotated[date, Query(alias="day")]
"""⛔ MAJBURIY — standart qiymat YO'Q (`FromDateDep`/`ToDateDep` qoidasi).

Daftar qatori QAYSI kunga yozilishi `business_date` ustuniga tushadi va
u DOMEN sanasi (`sbozor_core.models.ledger`): import kechikib, ertasi kuni
bajarilishi MUMKIN. Standart qiymat («bugun») o'shanda faylni JIMGINA
noto'g'ri kunga yozardi va xato faqat solishtiruvda, boshqa raqamlar
bilan aralashib ko'rinardi.

⚠ Klient uni HAR DOIM yuboradi (`uploadLedger(day, file)`), ya'ni
  majburiylik hech kimni to'smaydi — u faqat parametrsiz so'rovni
  ochiqchasiga rad etadi.
"""


@router.post("/compare/ledger", response_model=LedgerImportResponse)
async def ledger_import(
    principal: LedgerImporterDep,
    session: TenantSessionDep,
    settings: SettingsDep,
    day: DayDep,
    file: Annotated[UploadFile, File()],
) -> LedgerImportResponse:
    """Kunlik qog'oz daftarni `.xlsx` dan yozadi (`STALL_MANAGE`, D-17).

    Ustunlar (UI-SPEC §10.3): `rasta kodi, daftar summasi` — AYNAN IKKITA
    va POZITSIYA bo'yicha (O-05).

    =======================================================================
    ⛔⛔ ALL-OR-NOTHING TEKIN KELADI — VA SHU SABABDAN BU YERDA HECH
        QANDAY QO'SHIMCHA BLOK OCHILMAYDI.

    `TenantSessionDep` sessiyani ALLAQACHON tranzaksiya ichida beradi
    (`app/api/v1/imports.py` modul docstringi, 1-band): endpointdan
    chiqqan HAR QANDAY istisno butun importni orqaga qaytaradi. Ichki
    blok ochish uni faqat BUZARDI — ichki qism muvaffaqiyat bilan
    yopilgach, undan keyingi xato allaqachon yozilgan qatorlarni
    qoldirib ketardi.

    ⚠ Bu qoida MEXANIK darvoza bilan qulflangan: qabul mezoni faylni
      tranzaksiya ochish atamalari bo'yicha grep qiladi va natija NOL
      bo'lishi shart — shuning uchun o'sha atamalar bu izohda ham
      LITERAL yozilmagan (02-08 deviatsiya #3 dagi bilan aynan bir xil
      sabab).

    =======================================================================
    ⛔ IKKINCHI FAYL BIRINCHISINI ALMASHTIRADI, IKKINCHI QATOR
       YARATMAYDI (Pattern 6). Kafolat DB da:
       `UNIQUE (market_id, business_date, stall_id)` +
       `ON CONFLICT DO UPDATE` (`report_repo._LEDGER_UPSERT`). Ilova
       qatlamidagi «avval tekshir, keyin yoz» ikki parallel importda
       IKKITA qator yozardi.

    ⛔ BITTA IMPORT = BITTA YIG'MA AUDIT YOZUVI (T-02-180). Jadvalning
       O'Z DB triggeri (`0024`) har qator uchun yozuv qoldiradi va
       ularning hammasi to'g'ri — lekin ulardan «bular BITTA ommaviy
       amaldan» degan faktni CHIQARIB BO'LMAYDI. Nizoda aynan shu
       so'raladi, shuning uchun ilova bitta QO'SHIMCHA qator yozadi.

    ⚠ `imported_by` SESSIYADAN keladi, fayldan EMAS; `market_id` ham
      (T-02-54 / T-08-60) — shablonda bunday ustun umuman yo'q.
    """
    market_id = _market_id(principal)

    rows = _read(await _read_bounded(file, settings), import_validator.LEDGER_COLUMNS, settings)

    repo = ImportRepository(session, market_id)
    accepted, issues = import_validator.validate_ledger_rows(
        rows,
        # Lug'at TENANT sessiyasi ostida o'qiladi, ya'ni begona bozorning
        # rasta kodi bu yerga TUSHMAYDI va u `ledger_stall_unknown` oladi —
        # javob esa o'sha kodning boshqa bozorda MAVJUDLIGINI oshkor
        # qilmaydi (`ImportRepository.zone_ids_by_name()` ning qoidasi).
        stalls_by_code=await repo.stall_ids_by_code(),
    )
    _reject_if_invalid(issues)

    try:
        replaced = await report_repo.ledger_upsert(
            session,
            market_id=market_id,
            business_date=day,
            rows=accepted,
            imported_by=principal.user_id,
        )
    except IntegrityError as exc:
        # Bu yerga faqat POYGA holati yetib keladi: mazmun xatolari
        # validatorda, YOZISHDAN OLDIN ushlangan (`imports.py::_conflict`
        # docstringi). 409 D-14 ni BUZMAYDI — istisno tranzaksiyani
        # butunlay orqaga qaytaradi.
        raise _conflict(exc) from exc

    await write_app_audit(
        session,
        action=AuditAction.INSERT,
        table_name=TABLE_LEDGER_ENTRIES,
        row_id=None,
        principal=principal,
        # ⚠ `replaced` BU YERDA SON, javobda esa MANTIQIY qiymat va bu
        #   FARQ ONGLI: jurnal «nima o'zgardi» ga javob beradi (nechta
        #   qator ustiga yozildi), ekran esa «almashtirildimi?» degan
        #   BITTA savolga (§14.8 tasdiq dialogining natijasi).
        new={
            "import": "ledger",
            "day": day.isoformat(),
            "rows": len(accepted),
            "replaced": replaced,
        },
        track_changes=False,
    )

    log.info("ledger_import_done", day=day.isoformat(), rows=len(accepted), replaced=replaced)

    return LedgerImportResponse(day=day, rows=len(accepted), replaced=replaced > 0)


# ===========================================================================
# 6. UCH TOMONLAMA SOLISHTIRUV — `GET /compare` va `/compare.xlsx` (08-16)
#
# =========================================================================
# ⛔⛔ YO'LLAR KLIENT KONTRAKTIDAN: `/compare` va `/compare.xlsx`, reja
#     aytgan `/three-way` va `/three-way.xlsx` EMAS.
#
# `report-queries.ts` (08-03, TO'LQIN 1) AYNAN shu ikkisiga boradi:
# `${REPORTS_PATH}/compare?day=` (:253) va `${REPORTS_PATH}/compare.xlsx
# ?day=` (:383). Bu modul docstringining 2-bandidagi qarorning
# TO'RTINCHI takrori (`/debtors`, `/anomalies`, `/compare/ledger` dan
# keyin): SERVER KLIENTNI KUZATADI.
#
# =========================================================================
# ⛔⛔ IKKI YUZA, IKKI SHAXSIY-MA'LUMOT QARORI VA ULAR ZID EMAS.
#
#   `GET /compare`      -> javobda ISM YO'Q  -> `REPORT_VIEW` yetadi
#   `GET /compare.xlsx` -> hujjatda ISM BOR  -> `VENDOR_VIEW` + `audit_read`
#
# Sabab foydalanishda: ekrandagi jadval rasta kesimida ishlaydi va unga
# ism KERAK EMAS; imzolanadigan hujjatda esa «kimdan so'raladi?» savoli
# QOG'OZDA javob olishi kerak. JSON ga ism qo'shish ikki narsani birdan
# buzardi — klientning `strictObject` ini VA jurnalni (har hisobot
# ochilishida `audit_read` yozilardi, ya'ni HAQIQIY o'qish hodisasi
# shovqin ichida ko'milardi).
#
# ⛔ EKSPORT SHU SABABDAN `BINARY_PERSONAL_ROUTES` VA
#    `BINARY_PERSONAL_ALLOWED` NING IKKALASIGA ham yoziladi (08-12
#    qarori): javobi BAYT bo'lgan marshrutni `PERSONAL_FIELDS` darvozasi
#    HECH QACHON topa olmaydi.
#
# =========================================================================
# ⛔⛔ SAHIFALASH YO'Q (R-8) — VA BU QULAYLIK EMAS, HUJJATNING SHAKLI.
#
# Solishtiruv KUNLIK va u chop etilib IMZOLANADI. Sahifalangan hujjatni
# imzolab bo'lmaydi: ikkinchi sahifadagi farq imzo chekilgan varaqda
# UMUMAN bo'lmasdi. Chegara `settings.report_max_rows` va u oshsa javob
# `422 report_too_large` — ⛔ JIMGINA KESISH TAQIQ (T-08-73).
# ===========================================================================


def _compare_day(day: date) -> date:
    """Solishtiruv kunini yechadi — ⛔ YUQORI CHEGARA **KECHA** (UI-SPEC §10.2).

    =======================================================================
    ⛔⛔ NEGA «BUGUN» RAD ETILADI.

    Bugungi tizim summasi HALI YOPILMAGAN: `daily_charges` D+1 **04:10**
    da tug'iladi (`BILLING_CLOSE_CRON`, C-3). Qog'oz daftar ham kun
    OXIRIDA yig'iladi va odatda ertasi kuni kiritiladi. Ya'ni «bugun»
    ni solishtirish HAR DOIM farq ko'rsatardi va uchala sinf ham
    SOXTA bo'lardi — «Daftar ortiq» belgisi bilan chiqqan rasta aslida
    shunchaki hali yopilmagan kun bo'lardi.

    ⛔ Va u EKRANDA QOLMASDI: aynan shu javob `.xlsx` bo'lib yuklab
       olinadi va IMZOLANADI. Soxta farq bilan imzolangan varaq
       sotuvchiga qarshi «dalil» bo'lib ishlatilardi — mahsulot aynan
       shu nosozlikni yo'q qilish uchun bor (D-02).

    ⚠ `_report_period()` DAN AYRIM funksiya va bu ATAYIN: u ikki
      chegarali DAVR bilan ishlaydi va uning uch xato kodidan ikkitasi
      (`report_period_invalid`, `report_period_too_long`) bir kunlik
      so'rovda MA'NOSIZ. Bitta kunga uch shartli funksiyani cho'zish
      «qaysi shart ishladi?» savolini javobsiz qoldirardi.
    =======================================================================

    Returns:
        Tekshirilgan kun — ⛔ SILJITILMAGAN holda. Server kunni JIMGINA
        kechaga ko'chirmaydi: so'ralmagan kunning hisoboti «men bugunni
        so'radim, bugun keldi» degan YOLG'ON tasdiq berardi va u faylga
        tushib TARQALARDI (§8.7 ning kunlik shakli).
    """
    if day > business_today() - timedelta(days=1):
        raise _reject(_PERIOD_FUTURE, status.HTTP_422_UNPROCESSABLE_CONTENT)
    return day


ThreeWayExportIntentDep = Annotated[
    AuditReadIntent,
    Depends(audit_read(TABLE_VENDORS, reason="report_three_way_export")),
]
"""⛔ SOLISHTIRUV HUJJATINING O'Z `reason` I — `report_receivables_export` EMAS.

`vendors.py:105-113` da o'rnatilgan qoida: jurnalni o'qiyotgan odam
«kim QARZDORLIK hujjatini oldi» bilan «kim SOLISHTIRUV hujjatini oldi»
ni ajrata olishi kerak. Ikkinchisi boshqa savolga javob beradi va
boshqa jarayonda (imzolash) ishlatiladi — bir xil `reason` bilan o'sha
farq yo'qolardi.

⛔ BITTA SO'ROV = BITTA YOZUV, RASTA BOSHIGA EMAS: 1000 rastali bozorda
   «qator boshiga bitta yozuv» jurnalni bir so'rovda 1000 qator bilan
   to'ldirardi va HAQIQIY o'qish hodisasi ko'milib ketardi (06 №9 da
   rad etilgan (a) yo'lining aynan oqibati).
"""


def _compare_filename(market_name: str, day: date) -> str:
    """`{bozor-slug}_compare_{kun}.xlsx` — ⛔ TO'LIQ ASCII, SERVERDA.

    ⛔ `_export_filename()` ISHLATILMAYDI va sabab TURDA: u davrni IKKI
       sana bilan yozadi (`_{from}_{to}`), bir kunlik hujjatda esa u
       `..._2026-08-15_2026-08-15.xlsx` berardi — ya'ni chop etilgan
       varaqning nomi «bir kunlik oraliq» degan savolni tug'dirardi.
       Slug qoidasining O'ZI esa `_ascii_slug()` da, YAGONA joyda
       qoladi (D-06).

    ⚠ Nom klientning zaxira nomi bilan BIR OILADA:
      `report-queries.ts:391` sarlavha o'qilmasa `sbozor-compare-{day}.
      xlsx` yozadi — ikkalasida ham `compare` va AYNAN BITTA sana bor.
    """
    return f"{_ascii_slug(market_name)}_compare_{day.isoformat()}{XLSX_SUFFIX}"


async def _compare_report(
    session: AsyncSession,
    principal: Principal,
    *,
    day: date,
    max_rows: int,
) -> tuple[UUID, report_repo.ThreeWayReport]:
    """Ikkala marshrutning UMUMIY yadrosi — bozor, kun, chegara, hisobot.

    ⚠ Nusxa YOZILMAYDI: JSON va `.xlsx` da takrorlangan «bozorni ol,
      kunni yech, hisobotni qur, chegarani tekshir» ketma-ketligi bir
      kun bittasida yangilanib, ikkinchisida qolib ketardi — va aynan
      o'sha ikkinchisi IMZOLANADIGAN hujjat bo'lardi.

    ⛔ CHEGARA HISOBOTDAN KEYIN TEKSHIRILADI, oldin emas: `row_count`
       ni ikkinchi `count(*)` so'rovi bilan olish ikki so'rov orasida
       yozilgan yangi qatorni ro'yxatdan ajratardi (`_page()` da
       o'lchangan aynan o'sha sinf).
    """
    market_id = _market_id(principal)
    report = await report_repo.three_way(
        session, market_id=market_id, business_date=_compare_day(day)
    )
    _guard_row_count(len(report.rows), max_rows)
    return market_id, report


@router.get("/compare", response_model=ThreeWayReportResponse)
async def three_way_report(
    principal: ReportViewerDep,
    session: TenantSessionDep,
    settings: SettingsDep,
    day: DayDep,
) -> ThreeWayReportResponse:
    """Kunning uch tomonlama solishtiruvi — daftar · tizim · AI-kutilgan (SC#5).

    =======================================================================
    ⛔⛔ `VENDOR_VIEW` VA `audit_read` BU MARSHRUTDA YO'Q — VA BU ONGLI,
        «UNUTILGAN» EMAS.

    Javobda shaxsiy maydon YO'Q: rasta KODI va uch summa
    (`schemas.ThreeWayReportRow` — klient `strictObject` ining aynan
    nusxasi). Ism FAQAT `.xlsx` hujjatiga chiqadi va o'sha marshrut
    ikkala darvozani ham ko'taradi.

    ⛔ Bu yerga audit qo'yish jurnalni har hisobot ochilishida shovqin
       bilan to'ldirardi va HAQIQIY o'qish hodisasi (`/debtors`,
       `/compare.xlsx`) ko'milib ketardi — `audit.py` da ATAYIN rad
       etilgan «blanket middleware» holatining aynan sinfi
       (`anomaly_archive_report()` bilan AYNI qaror).
    =======================================================================

    ⛔ TO'RT SANOQ ALOHIDA VA ULARNING YIG'INDISI JAVOBDA YO'Q (D-18):
       uch sinf uch TURLI harakatni talab qiladi va bitta songa siqilgan
       hisobot qaysi sinf o'sganini yashirardi.

    ⛔ `has_ledger is False` bo'lgan kun uchun `rows` BO'SH keladi
       (§10.6): daftarsiz kunda «hamma farq 0» jadvali MUVAFFAQIYATLI
       solishtiruv bo'lib ko'rinardi va imzolanardi.
    """
    _, report = await _compare_report(
        session, principal, day=day, max_rows=settings.report_max_rows
    )

    return ThreeWayReportResponse(
        day=report.day,
        has_ledger=report.has_ledger,
        rows=_three_way_rows(report.rows),
        ledger_over_count=report.ledger_over_count,
        system_over_count=report.system_over_count,
        ai_mismatch_count=report.ai_mismatch_count,
        matched_count=report.matched_count,
    )


@router.get("/compare.xlsx", response_class=StreamingResponse)
async def three_way_export(
    principal: ReportViewerDep,
    vendor_guard: VendorFieldGuardDep,
    intent: ThreeWayExportIntentDep,
    session: TenantSessionDep,
    settings: SettingsDep,
    day: DayDep,
) -> StreamingResponse:
    """Solishtiruvning IMZOLANADIGAN `.xlsx` hujjati (D-19, §12.6).

    =======================================================================
    ⛔⛔ E'LON TARTIBI MAJBURIY VA U BEZAK EMAS (`receivables_export()`
        bilan AYNI): huquq -> huquq -> niyat -> ma'lumot. FastAPI
        dependency'larni shu tartibda hal qiladi, ya'ni 403 olgan so'rov
        `audit_read` gacha YETIB KELMAYDI. Teskari tartibda jurnalda
        «kassir solishtiruv hujjatini yuklab oldi» degan YOLG'ON DALIL
        paydo bo'lardi — hech nima berilmagan bo'lsa ham (T-02-71).

    ⛔ JAVOBNING MODELI YO'Q (javob — BAYT), ya'ni `PERSONAL_FIELDS`
       darvozasi bu marshrutni HECH QACHON topa olmaydi. Shuning uchun u
       `BINARY_PERSONAL_ROUTES` va `BINARY_PERSONAL_ALLOWED` ga QO'LDA
       yoziladi va o'sha yerdan `audit_read` + huquq talabi MEXANIK
       ravishda qaytadi (08-12 qarori).
    =======================================================================

    ⛔ IMZO QATORLARI FAYLDA, ISMLAR BO'SH: tizim kim imzolashini
       BILMAYDI (D-19 — bu QOG'OZ jarayon). Raqamli imzo yo'q va
       ekranda `[Imzolash]` tugmasi ham qurilmaydi (§10.7).
    """
    market_id, report = await _compare_report(
        session, principal, day=day, max_rows=settings.report_max_rows
    )

    locale = await _locale_of(session, principal)
    market = await MarketRepository(session).current_market()

    # ⛔ NIYAT HUJJAT QURILISHIDAN OLDIN TO'LDIRILADI (`receivables_export()`
    #    dagi bilan AYNI sabab): bo'sh niyat jurnalda «kimdir nimadir
    #    o'qidi» degan foydasiz qator qoldirardi. `result_count` — hujjatga
    #    tushgan RASTALAR soni, ya'ni «bu odam necha rastaning sotuvchisini
    #    ko'rdi» degan savolga javob.
    intent.filters = {"day": report.day.isoformat(), "format": "xlsx"}
    intent.result_count = len(report.rows)

    payload = xlsx_export.build_three_way_workbook(report.rows, locale, report.day)
    return _xlsx_response(payload, _compare_filename("" if market is None else market.name, day))
