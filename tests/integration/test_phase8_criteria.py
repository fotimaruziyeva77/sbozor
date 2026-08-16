"""8-fazaning BESHTA muvaffaqiyat mezoni — ROADMAP matni bilan bog'langan YAGONA fayl.

=============================================================================
BU FAYL MAVJUD TESTLARNI TAKRORLAMAYDI — U ULARNI ZANJIR SIFATIDA BOG'LAYDI.

Har mezonning qismlari allaqachon qamralgan va ular O'Z EGASIDA qoladi:

  * `test_report_repo.py`      (08-04) — davr arifmetikasi va hosila so'rov;
  * `test_reports_api.py`      (08-07/08-12) — huquq, audit, davr, bayt;
  * `test_three_way.py`        (08-14/08-16) — daftar importi va solishtiruv;
  * `test_backup_heartbeat.py` (08-08) — yurak urishi -> alert halqasi;
  * `test_restore_drill.py`    (08-08) — dump -> TOZA server -> ma'lumot;
  * `test_backup_contract.py`  (08-05) — zaxira zanjirining statik shakli;
  * `test_runbook_shape.py`    (08-19) — go-live runbookning shakli;
  * `test_blind_audit.py`      (05-11) — hosila urug' va 70/30 kvota;
  * `test_accuracy_report.py`  (05-12) — ikki xatoning SOF arifmetikasi.

Bu yerdagi savol boshqa va u faqat shu yerda beriladi: **ROADMAP'da
yozilgan jumla bugun rostmi?** Har test docstringi mezon matnini
SO'ZMA-SO'Z olib yuradi, ya'ni ROADMAP tahrirlanganda mos kelmaslik
ko'zga tashlanadi.

=============================================================================
⛔⛔ SOXTALASHTIRISH TAQIQLANADI — VA BU FAZADA TAQIQNING SHAKLI YANA BOSHQA.

5-fazada taqiq ANIQLIK METRIKASI nomlariga, 6-fazada SUZUVCHI
ARIFMETIKAGA, 7-fazada esa JO'NATUVCHINI ALMASHTIRISHGA qo'yilgan edi.
Bu fazaning eng arzon ikki yolg'oni ulardan ham boshqa:

  (1) zaxira zanjiri yugurmasdan turib «zaxira ishladi» degan qatorni
      QO'LDA yozib qo'yish — o'shanda `/internal/self-check` yashil
      bo'lardi, `backup_stale` esa MANGU jim turardi va FOUND-07 ning
      butun kafolati SOXTA bo'lardi;

  (2) `.xlsx` javobini FAQAT `status_code` bilan tasdiqlash — brauzer
      401 javob TANASINI ham `revenue.xlsx` nomi bilan diskka saqlaydi,
      ya'ni «200 + content-type» juftligi «bu haqiqatan hujjatmi?»
      degan savolga UMUMAN javob bermaydi.

Shuning uchun bu modulda TAQIQLANADI:

  1. standart kutubxonaning soxta obyekt vositalari va ularning
     uchinchi tomon qarindoshlari (reyestr: `_FAKE_ROOTS`);
  2. pytest ning tuzatuvchi fixture'i va loyihaning spy fixture'lari
     (reyestr: `_FAKE_FIXTURES`);
  3. ⛔ yurak urishi jadvaliga QO'LDA yozadigan xom SQL — u FAQAT
     mahsulot skriptidan (`ops/backup/heartbeat.sql`) kelishi mumkin;
  4. ⛔ eksport da'vosini BAYTLARSIZ qoldirish — `.xlsx` yo'liga
     tegib, javob KODI haqida da'vo qilgan HAR test mahsulotning O'Z
     o'quvchisini (`read_rows`) ham chaqirishi SHART.

⛔ (3) NING CHEGARASI ANIQ VA U TOR: `DELETE` TAQIQLANMAYDI. Qatorni
   o'chirish «zaxira ishlamadi» degan holatni quradi, ya'ni u
   soxtalashtirishning TESKARISI — o'lchov aynan shu bo'sh holatdan
   boshlanishi kerak. Taqiq faqat FAKTNI YOZADIGAN fe'llarga tegishli.

⛔ (4) SKANERI O'Z FAYLINI ISTE'MOLCHILAR TO'PLAMIDAN CHIQARADI
   (`_SCANNER_TEST`): skanerning o'zi reyestr NOMINI ishlatadi, hujjat
   yo'lini emas, lekin istisno OCHIQ yozilgan — aks holda keyingi
   tahrirchi uni tasodifan o'ziga qarshi qo'yardi.

=============================================================================
⛔⛔ SC#3 NING CHEGARASI — OCHIQ YOZILADI, YASHIRILMAYDI.

Mezonning matni IKKI jumla va ikkinchisi CI'da BAJARILMAYDI:

    «...boshqa lokatsiyaga ketadi va toza serverda tiklash mashqi
     kamida bir marta muvaffaqiyatli o'tkazilgan»

REAL offsite repo (`restic`) ham, REAL toza server (VPS) ham CI'da YO'Q
va ular hech qachon bo'lmaydi. Bu test o'sha bandning O'RNINI BOSMAYDI:
u zanjirning CI'da o'lchanadigan yarmini — yurak urishi halqasini va
mexanizm qatlamining default to'plamda YUGURISHINI — qo'riqlaydi.
Bandning EGASI **Ops**, joyi `08-HUMAN-UAT.md`, tetigi **VPS deploy'i**.

⛔ Mexanika qatlamining yashilligi bilan haqiqat qatlamining yo'qligini
   yopish TAQIQLANADI — bu 3- va 5-fazaning darsi va AI-02 ning
   `Blocked` bo'lish sababi. Shu sababdan **FOUND-07 `Done` QILINMAYDI**.

=============================================================================
⛔⛔ SC#4 NING CHEGARASI HAM LITERAL.

Mezon «...uch tilli interfeys yakuniy tekshiruvdan o'tgan — kassir,
nazoratchi va admin tizimda mashq qilib ko'rgan» deydi. **Odamning
mashqi CI'da o'lchanmaydi** va uni o'lchayotgandek ko'rsatish eng arzon
yolg'on bo'lardi. Bu yerda o'lchanadigan yarim ANIQ: (a) go-live
runbook MAVJUD va shakl darvozasi (`test_runbook_shape.py`) uni
qo'riqlaydi; (b) uch til FOYDALANUVCHI PROFILIDAN chiqib HUJJATGA
yetib boradi. Inson yarmi — `08-HUMAN-UAT.md`, egasi **direktor**.

=============================================================================
⛔ KUN — SEEDNING KUNI EMAS, `business_today() - 1`.

`SEED_BUSINESS_DATE` (2026-09-01) QADALGAN va bugundan KEYIN bo'lishi
mumkin; hisobot marshrutlari esa yuqori chegarani `business_today()`
(Asia/Tashkent) bilan qo'yadi, konteynerlar UTC da yuguradi. Ikki manba
Toshkent yarim tunidan keyingi besh soatda BIR KUN farq qilardi va
nosozlik KODDA emas, SOATDA bo'lardi
(`test_reports_api.py::_last_closed_day()` ning aynan darsi).

⛔ TOZALASH `market_id` BO'YICHA (06-14 qoidasi): mezon qoldirgan
   qatorlar keyingi fayllarning seed'ini FK buzilishi bilan yiqitardi.
=============================================================================
"""

from __future__ import annotations

import ast
import inspect
import io
import sys
import tomllib
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final
from uuid import UUID, uuid4

import httpx
import pytest
import xlsxwriter
from app.api.internal.self_check import EXPECTED_COMPONENTS
from app.jobs.alerting import BACKUP_COMPONENT
from app.jobs.audit_draw import audit_draw, eval_quota
from app.main import app as fastapi_app
from app.services import xlsx_export
from app.services.accuracy_report import MIN_SAMPLE_FOR_PERCENT
from app.services.xlsx_reader import read_rows
from fixtures.admin_api import PROFILE_URL, session_headers
from fixtures.auth_users import AuthSeed
from fixtures.billing_domain import (
    TARIFF_SOUM,
    BillingDomainSeed,
    add_billable_frame,
    add_daily_charge,
    add_payment,
    billing_domain_before_day_close,
)
from fixtures.market_domain import MarketDomainSeed
from fixtures.notification_domain import cleanup_notification_domain, seed_case
from fixtures.nvr_domain import nvr_rows
from fixtures.occupancy_domain import (
    MODEL_VERSION,
    SEED_THRESHOLDS_VERSION,
    SOURCE_HEIGHT,
    SOURCE_WIDTH,
    occupancy_rows,
    square_polygon,
)
from fixtures.snapshot_domain import snapshot_rows
from fixtures.two_markets import SEED_PASSWORD, TwoMarketSeed
from sbozor_core.enums import OccupancyVerdict, ReviewPurpose, ReviewQueueKind
from sbozor_core.models.snapshot import DEFAULT_SNAPSHOT_SLOTS
from sbozor_core.timeutil import business_today

if TYPE_CHECKING:
    from collections.abc import Iterator
    from datetime import time

    from psycopg import Connection
    from psycopg.rows import TupleRow
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

pytestmark = pytest.mark.usefixtures("migrated")

_MODULE_PATH = Path(__file__)
_REPO_ROOT = _MODULE_PATH.resolve().parents[2]


# ===========================================================================
# ⛔ MEZONLAR — ROADMAP § Phase 8 DAN LITERAL KO'CHIRILGAN
#
# ⚠ QISQARTIRILMAYDI VA QAYTA YOZILMAYDI: matn shu yerda o'zgarsa,
#   darvoza ROADMAP bilan JIMGINA ajralib ketardi va «beshala mezon
#   o'lchanadi» da'vosi boshqa beshta jumlaga tegishli bo'lib qolardi.
# ===========================================================================

CRITERIA: Final[tuple[str, ...]] = (
    "Direktor tushum (kunlik/oylik), qarzdorlik reestri va nomuvofiqlik "
    "arxivini ko'radi hamda har birini `.xlsx` qilib yuklab oladi",
    "AI aniqlik hisoboti ko'r audit namunasidan chiqadi va xatolik "
    'turlarini ajratadi: "band deb xato" (nizo xavfi) va "bo\'sh deb xato" '
    "(yo'qotish)",
    "Kunlik avtomatik backup (Postgres + obyekt-ombor) boshqa lokatsiyaga "
    "ketadi va toza serverda tiklash mashqi kamida bir marta muvaffaqiyatli "
    "o'tkazilgan",
    "Go-live runbook tayyor va uch tilli interfeys yakuniy tekshiruvdan "
    "o'tgan — kassir, nazoratchi va admin tizimda mashq qilib ko'rgan",
    "Parallel rejim uchun 3 tomonlama solishtiruv vositasi ishlaydi: daftar "
    "vs tizim vs AI-kutilgan — kunlik chiqariladi va imzolanadi",
)


# ===========================================================================
# MARSHRUTLAR
#
# ⛔⛔ NOMLAR KLIENT KONTRAKTIDAN, REJA MATNIDAN EMAS.
#
# 08-07/08-12 rejalari `/receivables`, `/discrepancies` va `/three-way`
# degan edi, LEKIN 08-03 (TO'LQIN 1) `REPORT_KINDS` ni
# `{revenue, debtors, anomalies, accuracy}` deb TO'PLAM TENGLIGI bilan
# qulflagan va jo'natilgan klient yo'lni AYNAN o'sha a'zodan quradi.
# Server klientni kuzatadi; sabab `app/api/v1/reports.py` modul
# docstringida LITERAL yozilgan.
# ===========================================================================

REVENUE_URL = "/api/v1/reports/revenue"
DEBTORS_URL = "/api/v1/reports/debtors"
ANOMALIES_URL = "/api/v1/reports/anomalies"
COMPARE_URL = "/api/v1/reports/compare"
LEDGER_URL = "/api/v1/reports/compare/ledger"

REVENUE_XLSX_URL = f"{REVENUE_URL}.xlsx"
DEBTORS_XLSX_URL = f"{DEBTORS_URL}.xlsx"
ANOMALIES_XLSX_URL = f"{ANOMALIES_URL}.xlsx"
ACCURACY_XLSX_URL = "/api/v1/reports/accuracy.xlsx"
COMPARE_XLSX_URL = f"{COMPARE_URL}.xlsx"

REPORT_URLS: Final[tuple[str, ...]] = (REVENUE_URL, DEBTORS_URL, ANOMALIES_URL)
REPORT_KINDS: Final[tuple[str, ...]] = ("revenue", "debtors", "anomalies")

EXPORT_URLS: Final[tuple[str, ...]] = (REVENUE_XLSX_URL, DEBTORS_XLSX_URL, ANOMALIES_XLSX_URL)
"""SC#1 ning uchala hujjati — ⛔ UCHALASI HAM BAYT DARAJASIDA o'qiladi."""

SELF_CHECK_URL = "/internal/self-check"
BLIND_NEXT_URL = "/api/v1/review/blind/next"
REVIEW_URL = "/api/v1/review"

XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
"""⚠ NUSXA ONGLI: marshrut modulining ICHKI nomidan import qilish
integratsiya to'plamini o'sha modulga bog'lardi. Ajralib qolish darhol
ko'rinadi — javobning `content-type` i shu satr bilan solishtiriladi.
"""


# ===========================================================================
# HUJJATLARNING SARLAVHASI — MATN KATALOGIDAN HOSILA
# ===========================================================================

_HEADER_KEYS: Final[dict[str, tuple[str, ...]]] = {
    "revenue": ("revenue_date", "revenue_paid", "revenue_charged", "revenue_diff"),
    "debtors": (
        "receivables_vendor",
        "receivables_stalls",
        "receivables_debt",
        "receivables_oldest",
    ),
    "anomalies": (
        "discrepancies_date",
        "discrepancies_kind",
        "discrepancies_stall",
        "discrepancies_status",
        "discrepancies_evidence",
    ),
    "accuracy": ("accuracy_metric", "accuracy_value", "accuracy_lower", "accuracy_upper"),
    "compare": (
        "compare_stall",
        "compare_vendor",
        "compare_ledger",
        "compare_system",
        "compare_ai_expected",
        "compare_diff",
        "compare_class",
    ),
}
"""Hujjat SARLAVHASINING matn KALITLARI — ⛔ satrlar TAKRORLANMAYDI.

Nusxa bir kun ajralib ketardi va o'shanda test hujjatni emas, o'zining
eski nusxasini o'lchardi (`test_reports_api.py::_export_header_row`
naqshi). Ustunlar SONI ham shu yerdan HOSILA — qo'lda yozilgan son
ustun qo'shilganda o'quvchini noto'g'ri katakka qaratardi.
"""

_EXPORT_COLUMNS: Final[dict[str, int]] = {kind: len(keys) for kind, keys in _HEADER_KEYS.items()}


# ===========================================================================
# ⛔⛔ SOXTALASHTIRISH REYESTRLARI — NOMLAR BO'LAKLAB QURILADI
#
# ⛔ NEGA LITERAL YOZILMAYDI VA BU HIYLA EMAS, ZARURAT (05-13 / 06-14 /
#    07-17 darsining takrori): bu modulning uchinchi darvozasi MATN
#    SKANI bilan ishlaydi va reyestrni literal yozish darvozani O'Z
#    izohida topib, uni HECH QACHON yashil bo'lmaydigan qilardi.
#
# ⚠ SHU IZOHNING O'ZI HAM O'SHA QOIDAGA BO'YSUNADI: taqiqlangan nomni
#   «tushuntirish uchun» yozish ham darvozani buzardi.
#
# ⚠ Ish vaqtidagi qiymat AYNAN o'sha nom — pastdagi NAZORAT testi
#   (`test_the_fake_registry_names_are_built_correctly`) buni tekshiradi,
#   ya'ni bo'laklash xatosi jimgina o'tib keta olmaydi.
# ===========================================================================

_UNIT = "unit" + "test"
_MOCK = "mo" + "ck"

_FAKE_ROOTS: Final[frozenset[str]] = frozenset(
    {
        _UNIT,
        _MOCK,
        "moto",
        "botocore",
        "aioresponses",
        "responses",
        "respx",
        "pytest_" + _MOCK,
        "freezegun",
    }
)
"""⛔ BU MODULDA IMPORT QILINMAYDIGAN ildizlar.

⚠ `respx` BU RO'YXATDA BOR va bu 7-fazadan FARQ QILADI. U yerda mezon
  Telegram'ga chiqqan so'rovni o'lchardi, ya'ni tarmoq chegarasini
  tutish ZARUR edi. Bu fazada mezonlarning birortasi ham tashqi tarmoqqa
  chiqmaydi — hammasi Postgres, marshrut grafi va `.xlsx` baytlari
  ustida. Ya'ni bu yerda tarmoqni tutish vositasi HECH NIMANI
  yechmaydi va faqat almashtirish yo'lini ochib qo'yardi.

⚠ `freezegun` ham ro'yxatda: bu fazaning hamma yo'li kunni ARGUMENT
  sifatida oladi (`business_date=`, `?day=`, `?from=&to=`), ya'ni
  soatni siljitish MAHSULOT KONTRAKTINI chetlab o'tish bo'lardi.
"""

_MOCK_SUFFIX = "Mo" + "ck"
"""`from ... import ...` bilan olib kiriladigan SOXTA OBYEKT sinflarining oxiri.

Standart kutubxonaning soxta obyekt sinflari — yalang'ochi ham,
«sehrli» ham, asinxroni ham — HAMMASI shu qo'shimcha bilan tugaydi,
ya'ni ro'yxat SANOQ emas, SHAKL bo'yicha yopiladi.
"""

_PATCH = "pat" + "ch"
_FAKE_IMPORTS: Final[frozenset[str]] = frozenset({_PATCH, _MOCK + "_open", "seal"})

_FAKE_FIXTURES: Final[frozenset[str]] = frozenset(
    {
        "monkey" + _PATCH,
        _MOCK + "er",
        "enqueued",
        "telegram_calls",
        "respx_" + _MOCK,
        "httpx_" + _MOCK,
        "go2rtc_" + _MOCK,
    }
)
"""Test IMZOSIDA uchramasligi shart bo'lgan fixture nomlari.

Import skani soxtalashtirishning FAQAT BIR shaklini ko'radi. Ikkinchisi —
pytest'ning O'Z tuzatuvchi fixture'i yoki loyihaning spy fixture'i —
birorta yangi import TALAB QILMAYDI, ya'ni `ast` daraxti uni UMUMAN
ko'rmasdi.
"""

_HEARTBEAT_TABLE = "system_" + "heartbeats"
_WRITE_VERBS: Final[tuple[str, ...]] = ("insert", "update")
"""⛔ ZAXIRA FAKTINI QO'LDA YOZADIGAN XOM SQL — 3-DARVOZANING NISHONI.

Ikkala bo'lak ham bitta satrda uchrasa, bu «zaxira ishladi» faktini
MAHSULOT ZANJIRISIZ yozish bo'lardi. Reyestr bo'laklab qurilgani uchun
bu docstringning o'zi darvozani qizartirmaydi: har bo'lak ALOHIDA satr.
"""

_READER_CALL = "read_rows"
"""Mahsulotning O'Z `.xlsx` o'quvchisi — 4-darvozaning TALABI."""

_RESPONSE_CLAIM = "status_code"
"""JAVOB HAQIDA DA'VONING mexanik izi — 4-darvozaning TETIGI.

⛔ TETIK «nomni tilga oldi» EMAS, «javob haqida da'vo qildi». Farq ijro
   paytida O'LCHANDI: birinchi shakl marshrut GRAFINI tekshiradigan
   nazorat testini yolg'on-qizil qilgan edi — u hujjat yo'llarini
   `app.openapi()` da izlaydi va birorta so'rov YUBORMAYDI. Ya'ni
   taqiqning nishoni javob kodiga tayangan da'vo bo'lib qoladi va u
   AYNAN shu ustunda ko'rinadi.
"""

_EXPORT_URL_NAMES: Final[frozenset[str]] = frozenset(
    {
        "REVENUE_XLSX_URL",
        "DEBTORS_XLSX_URL",
        "ANOMALIES_XLSX_URL",
        "ACCURACY_XLSX_URL",
        "COMPARE_XLSX_URL",
        "EXPORT_URLS",
    }
)
"""Hujjat yo'lini TASHIYDIGAN modul nomlari — 4-darvozaning KIRISHI.

⚠ RO'YXATDA YAKKA nom ham, TO'PLAM nomi ham bor: testlar uchala
  eksportni siklda aylantiradi va o'shanda yakka nomlar test tanasida
  UMUMAN ko'rinmaydi — skaner esa iste'molchini aynan shu nom bo'yicha
  topadi.

⚠ RO'YXATNING O'ZI NAZORAT TESTI BILAN QULFLANGAN: har nom modul
  globali bo'lishi VA qiymati `.xlsx` tashishi tekshiriladi, ya'ni
  eskirgan reyestr jimgina bo'shab qololmaydi.
"""

_SCANNER_TEST = "test_criteria_module_uses_no_fakes"
"""⛔ SKANERNING O'ZI ISTE'MOLCHILAR TO'PLAMIDAN CHIQARILADI.

Skaner reyestr NOMINI ishlatadi, hujjat yo'lini emas — ya'ni bugun u
o'ziga qarshi tushmaydi. Istisno baribir OCHIQ yozilgan: keyingi
tahrirchi skanerga nazorat namunasi qo'shganda darvoza YOLG'ON-QIZIL
bo'lardi va yagona «tuzatish» yo'li uni BO'SHATISH bo'lardi
(`tests/unit/test_backup_contract.py` ning 2-qoidasi).
"""


# ===========================================================================
# SC#2 NING NAMUNA HAJMI — ⛔ MAHSULOT KONSTANTASIDAN HOSILA
# ===========================================================================

_EVAL_RATIO: Final[float] = 0.70
"""D-14 ning kvotasi — `audit_draw` ga ARGUMENT sifatida beriladi."""

_FRAME_STALLS: Final[int] = 6
_FRAME_SLOTS: Final[int] = 5
_FRAME_SIZE: Final[int] = _FRAME_STALLS * _FRAME_SLOTS
"""Ko'r audit doirasining hajmi — 30 ta zona-hodisa (6 rasta x 5 slot).

⛔ SON «KATTA BO'LSIN» DEB TANLANMAGAN, U CHEGARADAN HOSILA:
   `accuracy_report()` foizlarni FAQAT `n >= MIN_SAMPLE_FOR_PERCENT`
   bo'lganda beradi (bugun 20). `eval` ulushi 70 % ekan, doira kamida
   `ceil(20 / 0,70)` = 29 bo'lishi kerak. 30 tanlangan, chunki u
   D-13 ning KUNLIK byudjeti va u yerda ham AYNAN shu son turibdi.

⛔ TENGSIZLIK TESTNING O'ZIDA, MAHSULOT FUNKSIYASI BILAN o'lchanadi
   (`eval_quota()`), ya'ni chegara yoki kvota o'zgarsa nosozlik SHU
   YERDA, aniq xabar bilan chiqadi — hujjatning bo'sh katagida emas.
"""

_HUMAN_ANSWER: Final[str] = OccupancyVerdict.EMPTY.value
"""⛔ NAZORATCHI BUTUN NAMUNAGA `empty` JAVOB BERADI — VA BU TANLOV.

=============================================================================
⛔⛔ NEGA AYNAN SHU JAVOB VA NEGA U MEZONNI ENG KUCHLI SHAKLDA O'LCHAYDI.

Doiraning hammasi tizim tomonidan `occupied` deb belgilangan, ya'ni
yagona `empty` javobi matritsani AYNAN shunday joylashtiradi:

    tp = 0   fp = eval namunasining HAMMASI
    fn = 0   tn = 0

Shundan KEYIN ikki xatoning maxraji BIR-BIRIDAN AJRALADI va ajralish
HUJJATDA KO'RINADI:

    «band deb xato»  = fp / (tp + fp) -> O'LCHANADI (maxraj > 0)
    «bo'sh deb xato» = fn / (tp + fn) -> O'LCHANMAYDI (maxraj = 0)

Ya'ni bitta varaqda BITTASI son, IKKINCHISI BO'SH katak bo'ladi — bu
esa FAQAT maxrajlar boshqa bo'lganda mumkin. Ikki xato bitta
«xatolik ulushi» ga qo'shilganda yoki umumiy maxraj (`n`) ishlatilganda
ikkala katak ham to'lardi va da'vo darhol qulardi.

⚠ VA BU «yakka nol» EMAS (08-15 ning darsi): o'lchanmagan katak NOL
  emas, BO'SH — `write_optional_number()` ning D-10 kafolati. Nol
  yozilgan varaq «tizim hech qachon bo'sh deb xato qilmaydi» degan
  O'LCHANGAN da'vo bo'lardi.
=============================================================================
"""


# ===========================================================================
# XOM SQL — ⛔ SHU MODULDA, `fixtures/` DA EMAS
# ===========================================================================

_DROP_BACKUP_HEARTBEAT = "DELETE FROM system_heartbeats WHERE component = %s"
"""SC#3 ning BOSHLANG'ICH holati — «zaxira hech qachon ishlamagan».

⛔ BU QATOR 3-DARVOZAGA TUSHMAYDI VA SABAB TA'RIFDA: o'chirish faktni
   YOZMAYDI, u faktni YO'Q QILADI. O'lchov aynan shu bo'sh holatdan
   boshlanadi va `never_seen` ro'yxatida komponentning KO'RINISHI
   birinchi da'vo bo'ladi.
"""

_INSERT_ZONE = (
    "INSERT INTO camera_zones "
    "(id, market_id, camera_id, stall_id, version, polygon, "
    " source_width, source_height, is_active) "
    "VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s)"
)
_INSERT_EVENT = (
    "INSERT INTO occupancy_events "
    "(id, market_id, snapshot_id, camera_zone_id, business_date, slot_time, "
    " verdict, confidence, model_version, thresholds_version, zone_version) "
    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
)
"""⚠ NUSXA ONGLI VA U IKKI FIXTURE'NING CHEGARASIDAN KELIB CHIQADI.

`billing_domain.add_zone_with_event_on()` hukmni QADAB yozadi
(`occupied`), `occupancy_domain.add_zone_with_event()` esa KUNNI qadaydi
(`SEED_BUSINESS_DATE`, kelajakda). SC#2 ga IKKALASI ham yaramaydi:
hisobot davri KECHA bilan tugaydi, doira esa 30 ta hodisani talab
qiladi. Uchinchi variant — fixture imzosini kengaytirish — begona
fayllarni bu rejaning ehtiyojiga bog'lardi (SCOPE BOUNDARY).
"""

_INSERT_SLOT = (
    "INSERT INTO stall_slot_occupancy "
    "(id, market_id, stall_id, business_date, slot_time, verdict, resolution_source) "
    "VALUES (%s, %s, %s, %s, %s, %s, %s)"
)
"""SC#5 ning AI-KUTILGAN ustuni — ⛔ `empty` hukmi G'OLIB HODISASIZ.

`occupied_has_winning_event` konstrayti `occupied` uchun g'olib hodisani
MAJBURIY, qolgan hukmlar uchun esa uni `NULL` qiladi. Ya'ni bu yordamchi
noto'g'ri chaqirilsa seedning O'ZI yiqiladi.
"""

_EVENT_OF_ASSIGNMENT = (
    "SELECT occupancy_event_id, purpose, queue_kind FROM review_assignments WHERE id = %s"  # noqa: E501
)
_SAMPLE_QUEUE_KINDS = (
    "SELECT DISTINCT queue_kind FROM review_assignments WHERE market_id = %s AND purpose = %s"
)
_STALL_CODE = "SELECT code FROM stalls WHERE id = %s"
_DRAFT_MARKET = "UPDATE markets SET is_active = %s WHERE id = %s"


# ===========================================================================
# MUHIT
# ===========================================================================


@dataclass(frozen=True)
class Env:
    """Bir mezonga kerak bo'ladigan hamma narsa — bitta obyektda."""

    billing: BillingDomainSeed
    domain: MarketDomainSeed
    base: TwoMarketSeed
    auth: AuthSeed
    day: date

    @property
    def market_id(self) -> UUID:
        return self.billing.market_a.market_id

    @property
    def market_b_id(self) -> UUID:
        return self.billing.market_b.market_id

    @property
    def vendor_id(self) -> UUID:
        return self.billing.market_a.vendor_id

    @property
    def tariff_id(self) -> UUID:
        return self.billing.market_a.tariff_id

    @property
    def stall_ids(self) -> tuple[UUID, ...]:
        return self.domain.market_a.stall_ids

    @property
    def market_ids(self) -> tuple[UUID, ...]:
        return self.billing.market_ids

    def billed_stall(self, index: int) -> UUID:
        """⛔ BILLING TOIFASI BERILGAN rasta — tarif izlash yo'li uchun.

        `billing_domain._seed_market_a()` toifa davrini FAQAT to'rtta
        rastaga beradi; qolgan ikkitasida `market_domain` ning O'Z toifasi
        va BOSHQA tarifi qoladi (`test_three_way.py::billed_stall` da
        o'lchangan holat). Solishtiruv summani tarifdan oladi, ya'ni u
        AYNAN shu ro'yxatdan rasta olishi kerak.
        """
        return (self.stall_ids[3], self.stall_ids[4], self.stall_ids[0], self.stall_ids[5])[index]


def _report_day() -> date:
    """Davrning eng yuqori RUXSAT ETILGAN kuni — ⛔ KECHA.

    ⛔ `date.today()` YOKI DB `CURRENT_DATE` ISHLATILMAYDI: marshrutlar
       chegarani `sbozor_core.timeutil.business_today()` (Asia/Tashkent)
       bilan qo'yadi, konteynerlar esa UTC da yuguradi.
    """
    return business_today() - timedelta(days=1)


def _period(days: int = 7) -> dict[str, str]:
    """`?from=&to=` — oxiri KECHA, uzunligi `days` kun (ikkala uchi ham kiradi)."""
    to_date = _report_day()
    return {"from": (to_date - timedelta(days=days - 1)).isoformat(), "to": to_date.isoformat()}


@pytest.fixture
def env(
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    auth_seed: AuthSeed,
    market_domain: MarketDomainSeed,
    migrated: None,
) -> Iterator[Env]:
    """Besh qatlamli seed; tozalash TESKARI tartibda (FK zanjiri bo'yicha).

    ⛔ `billing_domain_before_day_close` TANLANDI, `billing_domain` EMAS:
       ikkinchisi `day_close` ni SEED KUNIGA (kelajakda) yugurtiradi va
       hisobot kuniga birorta slot qatori bermasdi. Bu variant
       `stall_slot_occupancy` ni BO'SH qoldiradi, ya'ni SC#5 kerakli
       hukmni O'ZI yozadi va «o'lchanmagan» holati (qator YO'Q) ham
       ifodalanadi.

    ⚠ `auth_seed` `market_domain` DAN OLDIN so'raladi va bu ATAYIN:
      pytest fixture'larni teskari tartibda yopadi, ya'ni nazoratchi
      foydalanuvchisi `zone_reviews` qatorlaridan KEYIN o'chiriladi.
    """
    with (
        nvr_rows(sync_owner_conn, two_markets) as nvr,
        snapshot_rows(sync_owner_conn, nvr) as snaps,
        occupancy_rows(sync_owner_conn, two_markets, market_domain, snaps) as occupancy,
        billing_domain_before_day_close(
            sync_owner_conn, two_markets, market_domain, occupancy
        ) as billing,
    ):
        market_ids = [str(market_id) for market_id in billing.market_ids]
        try:
            yield Env(billing, market_domain, two_markets, auth_seed, _report_day())
        finally:
            # ⛔ TARTIB MAJBURIY: ko'rik qatorlari hodisalarga FK bilan
            #    tayanadi va ular `occupancy_rows` yopilishidan OLDIN
            #    ketishi kerak. `zone_reviews` uchun qoralama-bozor
            #    istisnosi ishlatiladi — javob SHARTSIZ o'zgarmas va
            #    yagona `DELETE` yo'li shu (`test_phase5_criteria.py::
            #    clear_review_state` ning aynan qarori).
            for market in market_ids:
                sync_owner_conn.execute(_DRAFT_MARKET, (False, market))
                sync_owner_conn.execute("DELETE FROM zone_reviews WHERE market_id = %s", (market,))
                sync_owner_conn.execute(_DRAFT_MARKET, (True, market))
            sync_owner_conn.execute(
                "DELETE FROM review_assignments WHERE market_id = ANY(%s::uuid[])", (market_ids,)
            )
            sync_owner_conn.execute(
                "DELETE FROM audit_rounds WHERE market_id = ANY(%s::uuid[])", (market_ids,)
            )
            sync_owner_conn.execute(
                "DELETE FROM ledger_entries WHERE market_id = ANY(%s::uuid[])", (market_ids,)
            )
            sync_owner_conn.execute(
                "DELETE FROM stall_slot_occupancy WHERE market_id = ANY(%s::uuid[])",
                (market_ids,),
            )
            cleanup_notification_domain(sync_owner_conn, market_ids=list(billing.market_ids))


@pytest.fixture
async def director_headers(api_client: httpx.AsyncClient, env: Env) -> dict[str, str]:
    """DIREKTOR sessiyasi — `report_view` VA `vendor_view` BOR (D-07)."""
    return await session_headers(api_client, env.base.market_a.director_phone, SEED_PASSWORD)


@pytest.fixture
async def admin_headers(api_client: httpx.AsyncClient, env: Env) -> dict[str, str]:
    """BOZOR ADMINI sessiyasi — daftar importi `stall_manage` talab qiladi."""
    market_a = env.base.market_a
    return await session_headers(api_client, market_a.admin_phone, market_a.admin_password)


@pytest.fixture
async def inspector_headers(api_client: httpx.AsyncClient, env: Env) -> dict[str, str]:
    """NAZORATCHI sessiyasi — huquqi AYNAN `OCCUPANCY_REVIEW`."""
    return await session_headers(api_client, env.auth.inspector.phone, SEED_PASSWORD)


# ===========================================================================
# YORDAMCHILAR
# ===========================================================================


def _header_row(kind: str, locale: str) -> tuple[str, ...]:
    """Hujjatning SARLAVHA qatori — `xlsx_export` MATN KATALOGIDAN."""
    texts = xlsx_export.report_texts(locale)
    return tuple(texts[key] for key in _HEADER_KEYS[kind])


def _labelled(rows: list[Any]) -> dict[str, tuple[str | None, ...]]:
    """`sarlavha -> qator` — ⛔ NAZORAT: sarlavha TAKRORLANMAYDI.

    Ikki qator bir xil nom bilan qaytsa lug'at JIMGINA qisqarardi va
    «hujjatda ikkala xato turi ham bor» da'vosi bitta qatorni ikki marta
    o'qib ham rost bo'lardi.
    """
    indexed = {str(row.values[0]): tuple(row.values) for row in rows if row.values[0] is not None}
    assert len(indexed) == len([row for row in rows if row.values[0] is not None]), (
        "hujjatda bir xil nomli IKKI qator bor — lug'at ularni jimgina birlashtirardi"
    )
    return indexed


def _seed_zone_event(
    conn: Connection[TupleRow],
    *,
    market_id: UUID,
    camera_id: UUID,
    stall_id: UUID,
    snapshot_id: UUID,
    day: date,
    slot: time,
    verdict: str,
    center: tuple[float, float],
    version: int,
) -> UUID:
    """Zona + bandlik hodisasi — HUKM ham, KUN ham ARGUMENT (sabab yuqorida)."""
    zone_id, event_id = uuid4(), uuid4()
    polygon = square_polygon(*center)
    conn.execute(
        _INSERT_ZONE,
        (
            str(zone_id),
            str(market_id),
            str(camera_id),
            str(stall_id),
            version,
            "[" + ", ".join(f"[{x}, {y}]" for x, y in polygon) + "]",
            SOURCE_WIDTH,
            SOURCE_HEIGHT,
            True,
        ),
    )
    conn.execute(
        _INSERT_EVENT,
        (
            str(event_id),
            str(market_id),
            str(snapshot_id),
            str(zone_id),
            day,
            slot,
            verdict,
            "0.9100",
            MODEL_VERSION,
            SEED_THRESHOLDS_VERSION,
            version,
        ),
    )
    return event_id


def _camera_of(conn: Connection[TupleRow], market_id: UUID) -> tuple[UUID, UUID]:
    """`(nvr_id, camera_id)` — ⛔ `capture_runs` DAN, seed ro'yxatining TARTIBIDAN emas."""
    row = conn.execute(
        "SELECT nvr_id, camera_id FROM capture_runs WHERE market_id = %s ORDER BY nvr_id LIMIT 1",
        (str(market_id),),
    ).fetchone()
    assert row is not None, "nazorat: A bozorida `capture_runs` qatori yo'q"
    return UUID(str(row[0])), UUID(str(row[1]))


def _code_of(conn: Connection[TupleRow], stall_id: UUID) -> str:
    """Rasta kodi — ⛔ BAZADAN, seed ro'yxatining TARTIBIDAN emas."""
    row = conn.execute(_STALL_CODE, (str(stall_id),)).fetchone()
    assert row is not None, f"nazorat: {stall_id} rastasi yo'q"
    return str(row[0])


def _ledger_file(rows: list[tuple[str, int]]) -> bytes:
    """Haqiqiy `.xlsx` daftar — repoda binar fayl SAQLANMAYDI."""
    buffer = io.BytesIO()
    workbook = xlsxwriter.Workbook(buffer, {"in_memory": True})
    worksheet = workbook.add_worksheet("Daftar")
    worksheet.write_row(0, 0, ["rasta kodi", "daftar summasi"])
    for index, (code, amount) in enumerate(rows, start=1):
        worksheet.write_row(index, 0, [code, str(amount)])
    workbook.close()
    return buffer.getvalue()


def _heartbeat_statement() -> str:
    """`ops/backup/heartbeat.sql` ni o'qiydi va `psql` o'zgaruvchisini bog'laydi.

    =======================================================================
    ⛔⛔ SQL QO'LDA YOZILMAYDI — U MAHSULOT FAYLIDAN KELADI.

    Qo'lda yozilgan buyruq mahsulot skriptidan bir kun JIMGINA ajralib
    ketardi va o'shanda bu mezon «zaxira ishladi» degan YOLG'ONNI
    o'lchardi: test yashil bo'lib turardi, mahsulot esa boshqa komponent
    nomi bilan yozardi va `/internal/self-check` uni MANGU `never_seen`
    da ko'rsatardi (`test_backup_heartbeat.py` da o'lchangan nosozlik).

    ⚠ YAGONA MOSLASHTIRISH — `psql` ning qochirilgan satr literalini
      DB-API bog'lamasiga aylantirish. IKKALASI HAM BOG'LANGAN
      parametr, ya'ni T-08-22 ning ma'nosi saqlanadi. Almashtirish
      SONI tekshiriladi: mexanizm o'zgarsa nosozlik SHU YERDA chiqadi,
      jimgina noto'g'ri SQL bajarilmaydi.

    ⚠ TO'LIQ QATORLI izohlar OLIB TASHLANADI: fayl o'z mexanizmini
      izohda ham tushuntiradi va sanoq izoh matnini SQL bilan
      aralashtirib, hech qachon rost bo'lmasdi.
    =======================================================================
    """
    path = _REPO_ROOT / "ops" / "backup" / "heartbeat.sql"
    assert path.is_file(), (
        f"mahsulot skripti topilmadi: {path} — `ops/backup/heartbeat.sql` ko'chirilgan "
        "bo'lsa bu mezon ham yangilanishi SHART"
    )
    body = "\n".join(
        line
        for line in path.read_text(encoding="utf-8").splitlines()
        if not line.lstrip().startswith("--")
    )
    variable = ":'day'"
    found = body.count(variable)
    assert found == 1, (
        f"`heartbeat.sql` ning BAJARILADIGAN qismida {variable} {found} marta uchradi "
        "(kutilgan: 1) — bog'lash mexanizmi o'zgargan"
    )
    return body.replace(variable, "%s::text")


def _module_tests() -> list[tuple[str, Any]]:
    """Modulning test funksiyalari — ⛔ INTROSPEKSIYADAN, qo'lda yozilmaydi."""
    module = sys.modules[__name__]
    return [
        (name, obj)
        for name, obj in inspect.getmembers(module, inspect.isfunction)
        if name.startswith("test_") and obj.__module__ == __name__
    ]


def _string_constants(tree: ast.AST) -> list[str]:
    """Modulning barcha satr konstantalari — izohlar KIRMAYDI.

    ⚠ Docstringlar KIRADI va bu ATAYIN: taqiqlangan SQL ni «izohda
      ko'rsatib qo'yish» ham uni keyingi ijrochiga NUSXA OLINADIGAN
      naqsh qilib qoldirardi.
    """
    return [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    ]


# ===========================================================================
# SC#1
# ===========================================================================


async def test_sc1_director_reads_three_reports_and_downloads_each_as_a_real_xlsx(
    api_client: httpx.AsyncClient,
    sync_owner_conn: Connection[TupleRow],
    director_headers: dict[str, str],
    env: Env,
) -> None:
    """MEZON #1: «Direktor tushum (kunlik/oylik), qarzdorlik reestri va
    nomuvofiqlik arxivini ko'radi hamda har birini `.xlsx` qilib yuklab
    oladi».

    =======================================================================
    ⛔⛔ `200` MEZON EMAS — BAYTLAR QAYTA O'QILADI.

    `report-queries.ts` modul docstringi buni O'LCHANGAN holat sifatida
    yozadi: brauzer 401 javob TANASINI ham `revenue.xlsx` nomi bilan
    diskka saqlaydi. Foydalanuvchi «fayl yuklandi» deb o'ylaydi, Excel
    «fayl buzilgan» deydi va xato HECH QAYERDA ko'rinmaydi. Ya'ni
    «200 + content-type» juftligi «bu haqiqatan hujjatmi?» degan
    savolga javob BERMAYDI.

    Shuning uchun baytlar MAHSULOTNING O'Z o'quvchisidan o'tkaziladi
    (`xlsx_reader.read_rows` — hajm -> ZIP -> parse -> varaq/qator) va
    SARLAVHA QATORI matn katalogi bilan solishtiriladi.

    ⚠ Taqiq MEXANIK: pastdagi 4-darvoza eksport yo'lini ishlatgan HAR
      testda o'quvchining chaqirilishini TALAB qiladi.

    =======================================================================
    ⚠ «KO'RADI» — UCH JSON MARSHRUTI, «YUKLAB OLADI» — UCH HUJJAT.
      Ikkalasi ham o'lchanadi: faqat hujjatni o'lchash ekranni testsiz
      qoldirardi, faqat JSON ni o'lchash esa mezonning ikkinchi
      yarmini.
    """
    day = env.day
    charge_id, _ = add_daily_charge(
        conn=sync_owner_conn,
        market_id=env.market_id,
        stall_id=env.stall_ids[0],
        vendor_id=env.vendor_id,
        tariff_id=env.tariff_id,
        service_date=day,
    )
    seed_case(sync_owner_conn, market_id=env.market_id, service_date=day, charge_id=charge_id)

    # ---- «KO'RADI»: uchala JSON marshruti ham javob beradi va BO'SH EMAS.
    payloads: dict[str, Any] = {}
    for url, kind in zip(REPORT_URLS, REPORT_KINDS, strict=True):
        response = await api_client.get(url, params=_period(), headers=director_headers)
        assert response.status_code == 200, f"{url}: {response.text}"
        payloads[kind] = response.json()

    charged_day = next(
        row for row in payloads["revenue"]["rows"] if row["business_date"] == day.isoformat()
    )
    assert charged_day["charged_soum"] == TARIFF_SOUM, charged_day
    assert payloads["debtors"]["rows"], (
        "qarzdorlik reestri bo'sh — hisob yozilgan, to'lov yo'q holatida u BITTA qator "
        "berishi kerak, aks holda mezon BO'SH-ROST bo'lardi"
    )
    assert payloads["anomalies"]["unpaid_count"] == 1, payloads["anomalies"]

    # ---- «YUKLAB OLADI»: uchala hujjat ham HAQIQIY `.xlsx`.
    locales = ("uz-Latn", "uz-Cyrl", "ru")
    for url, kind in zip(EXPORT_URLS, REPORT_KINDS, strict=True):
        document = await api_client.get(url, params=_period(), headers=director_headers)
        assert document.status_code == 200, f"{url}: {document.text}"
        assert document.headers["content-type"] == XLSX_MEDIA_TYPE, url

        rows = read_rows(document.content, expected_columns=_EXPORT_COLUMNS[kind])
        assert rows, f"{url}: hujjatda birorta qator yo'q — sarlavha ham yozilmagan"
        # ⚠ 1-qator DAVR, ya'ni `read_rows` tashlab yuboradigan qator aynan
        #   o'sha; qaytgan BIRINCHI qator — hujjatning sarlavhasi.
        assert rows[0].values in {_header_row(kind, locale) for locale in locales}, (
            f"{url}: sarlavha qatori matn katalogining birorta tiliga MOS kelmadi: {rows[0].values}"
        )


# ===========================================================================
# SC#2
# ===========================================================================


async def test_sc2_accuracy_report_comes_from_the_blind_sample_and_splits_two_error_kinds(
    api_client: httpx.AsyncClient,
    app_sessionmaker: async_sessionmaker[AsyncSession],
    sync_owner_conn: Connection[TupleRow],
    inspector_headers: dict[str, str],
    director_headers: dict[str, str],
    env: Env,
) -> None:
    """MEZON #2: «AI aniqlik hisoboti ko'r audit namunasidan chiqadi va
    xatolik turlarini ajratadi: "band deb xato" (nizo xavfi) va "bo'sh deb
    xato" (yo'qotish)».

    =======================================================================
    IKKI DA'VO VA ULAR MUSTAQIL — SHUNING UCHUN IKKALASI HAM O'LCHANADI:

      1. **KO'R AUDIT NAMUNASIDAN** — hujjatdagi son namunaning `eval`
         yarmiga TENG, `train` yarmi esa unga TUSHMAYDI. Namuna
         `audit_draw` bilan TORTILADI, qo'lda yozilmaydi: qo'lda yozilgan
         namuna «tasodifiy tanlangan» jumlasini butunlay chetlab
         o'tardi. Manba navbati ham o'lchanadi (`queue_kind`).

      2. **IKKI XATO AJRATILGAN** — ikkalasi hujjatda ALOHIDA qator va
         ⛔ ularning MAXRAJI BOSHQA. Bu ikkinchi da'vo aynan shu
         namunada eng kuchli shaklda o'lchanadi: bittasi O'LCHANADI,
         ikkinchisi esa BO'SH KATAK bo'lib qoladi (sabab
         `_HUMAN_ANSWER` docstringida, matritsa bilan birga).

    ⚠ 05-15 NING DARSI SHU YERDA HAM QO'LLANADI: butun namuna
      javoblanadi — `eval` ham, `train` ham. Faqat bitta bandni
      javoblash filtrning IKKI shartidan bittasini o'lchamay
      qoldirardi.
    =======================================================================
    """
    day = env.day
    nvr_id, camera_id = _camera_of(sync_owner_conn, env.market_id)
    slots = DEFAULT_SNAPSHOT_SLOTS[:_FRAME_SLOTS]

    answers: dict[str, str] = {}
    for slot_index, slot in enumerate(slots):
        _, snapshot_id = add_billable_frame(
            sync_owner_conn,
            market_id=env.market_id,
            nvr_id=nvr_id,
            camera_id=camera_id,
            slot=slot,
            day=day,
            is_market_open=True,
        )
        for stall_index in range(_FRAME_STALLS):
            version = 300 + slot_index * _FRAME_STALLS + stall_index
            event_id = _seed_zone_event(
                sync_owner_conn,
                market_id=env.market_id,
                camera_id=camera_id,
                stall_id=env.stall_ids[stall_index],
                snapshot_id=snapshot_id,
                day=day,
                slot=slot,
                verdict=OccupancyVerdict.OCCUPIED.value,
                center=(0.15 + 0.14 * stall_index, 0.15 + 0.16 * slot_index),
                version=version,
            )
            answers[str(event_id)] = _HUMAN_ANSWER

    assert len(answers) == _FRAME_SIZE, f"doira {len(answers)} ta hodisadan iborat"

    expected_eval = eval_quota(_FRAME_SIZE, _EVAL_RATIO)
    assert expected_eval >= MIN_SAMPLE_FOR_PERCENT, (
        f"doira {_FRAME_SIZE} da `eval` kvotasi {expected_eval} — u foiz chegarasidan "
        f"({MIN_SAMPLE_FOR_PERCENT}) kichik, ya'ni hujjat FOIZSIZ qaytardi va mezonning "
        "ikkinchi yarmi o'lchanmay qolardi"
    )

    drawn = await audit_draw(
        app_sessionmaker, business_date=day, sample_size=_FRAME_SIZE, eval_ratio=_EVAL_RATIO
    )
    assert drawn.drawn == _FRAME_SIZE, f"namuna to'liq tortilmadi: {drawn}"
    assert drawn.eval_count == expected_eval, f"`eval` kvotasi kutilgandan boshqa: {drawn}"
    assert drawn.train_count > 0, (
        f"namunada `train` bandi yo'q: {drawn} — 70/30 kvotasining IKKINCHI yarmi "
        "tug'ilmagan va `purpose` filtri O'LCHANMAY qolardi"
    )

    # ---- BUTUN NAMUNA JAVOBLANADI — `eval` ham, `train` ham.
    purposes: dict[str, int] = {}
    current = await api_client.get(BLIND_NEXT_URL, headers=inspector_headers)
    while current.status_code == 200:
        assignment_id = current.json()["assignment_id"]
        row = sync_owner_conn.execute(_EVENT_OF_ASSIGNMENT, (str(assignment_id),)).fetchone()
        assert row is not None, f"topshiriq {assignment_id} bazada yo'q"
        drawn_event, purpose, queue_kind = str(row[0]), str(row[1]), str(row[2])
        assert queue_kind == ReviewQueueKind.BLIND_AUDIT.value, (
            f"ko'r navbat `{queue_kind}` bandini berdi — hisobotning manbai BOSHQA "
            "navbatga siljigan bo'lardi"
        )
        purposes[purpose] = purposes.get(purpose, 0) + 1

        answered = await api_client.post(
            f"{REVIEW_URL}/blind/{assignment_id}/answer",
            json={"human_verdict": answers[drawn_event]},
            headers=inspector_headers,
        )
        assert answered.status_code == 200, answered.text
        current = await api_client.get(BLIND_NEXT_URL, headers=inspector_headers)

    assert current.status_code == 409, (
        f"ko'r navbat 200/409 dan boshqa kod berdi: {current.status_code}"
    )
    eval_answers = purposes.get(ReviewPurpose.EVAL.value, 0)
    assert eval_answers == expected_eval, f"javoblangan `eval` bandlari: {purposes}"
    assert purposes.get(ReviewPurpose.TRAIN.value, 0) > 0, purposes

    kinds = {
        str(row[0])
        for row in sync_owner_conn.execute(
            _SAMPLE_QUEUE_KINDS, (str(env.market_id), ReviewPurpose.EVAL.value)
        ).fetchall()
    }
    assert kinds == {ReviewQueueKind.BLIND_AUDIT.value}, (
        f"`eval` bandlarining navbat turlari: {sorted(kinds)} — hisobot ko'r auditdan "
        "BOSHQA manbadan ham oziqlanayotgan bo'lardi"
    )

    # ---- HUJJAT: baytlar QAYTA O'QILADI.
    document = await api_client.get(ACCURACY_XLSX_URL, params=_period(), headers=director_headers)
    assert document.status_code == 200, document.text
    assert document.headers["content-type"] == XLSX_MEDIA_TYPE

    rows = read_rows(document.content, expected_columns=_EXPORT_COLUMNS["accuracy"])
    assert rows[0].values in {
        _header_row("accuracy", locale) for locale in ("uz-Latn", "uz-Cyrl", "ru")
    }, rows[0].values

    texts = xlsx_export.report_texts("uz-Latn")
    sheet = _labelled(rows[1:])

    # ---- (1) MANBA: hujjatdagi son AYNAN `eval` javoblariga teng.
    assert sheet[texts["accuracy_n"]][1] == str(eval_answers), (
        f"hujjat {sheet[texts['accuracy_n']][1]} ta javobni sanadi, `eval` esa "
        f"{eval_answers} ta ({purposes}) — hisobot namunaning `train` yarmini ham "
        "o'lchovga qo'shib yuborgan"
    )

    tp = int(str(sheet[texts["accuracy_tp"]][1]))
    fp = int(str(sheet[texts["accuracy_fp"]][1]))
    fn = int(str(sheet[texts["accuracy_fn"]][1]))
    assert (tp, fp, fn) == (0, eval_answers, 0), (
        f"matritsa kutilgandan boshqa joylashdi: tp={tp} fp={fp} fn={fn} — namuna "
        "qurilishi o'zgargan bo'lsa quyidagi ikki da'vo ham ma'nosini yo'qotadi"
    )

    # ---- (2) IKKI XATO — ALOHIDA QATOR VA BOSHQA MAXRAJ.
    false_occupied_label = texts["accuracy_false_occupied"]
    false_empty_label = texts["accuracy_false_empty"]
    assert false_occupied_label != false_empty_label, (
        "ikki xato turi bitta sarlavha bilan yozilgan — ular hujjatda AJRALMAGAN"
    )
    assert false_occupied_label in sheet, f"«band deb xato» qatori yo'q: {sorted(sheet)}"
    assert false_empty_label in sheet, f"«bo'sh deb xato» qatori yo'q: {sorted(sheet)}"

    false_occupied = sheet[false_occupied_label][1]
    false_empty = sheet[false_empty_label][1]

    assert false_occupied is not None and float(false_occupied) == pytest.approx(1.0), (
        f"«band deb xato» ulushi {false_occupied} — maxraj «tizim band dedi» (tp + fp) "
        "bo'lganda u AYNAN 1,0 bo'ladi; boshqa son maxraj almashganini bildiradi"
    )
    assert false_empty is None, (
        f"«bo'sh deb xato» katagida qiymat bor ({false_empty}) — bu namunada uning "
        "maxraji (tp + fn) NOL, ya'ni katak BO'SH qolishi SHART. To'lgan katak ikki "
        "xatoning maxraji BIRLASHTIRILGANINI bildiradi (yoki o'lchanmagan qiymat NOL "
        "bilan almashtirilganini — D-10)"
    )


# ===========================================================================
# SC#3
# ===========================================================================


async def test_sc3_backup_heartbeat_reaches_the_monitor_only_through_the_product_chain(
    api_client: httpx.AsyncClient,
    sync_owner_conn: Connection[TupleRow],
    env: Env,
) -> None:
    """MEZON #3: «Kunlik avtomatik backup (Postgres + obyekt-ombor) boshqa
    lokatsiyaga ketadi va toza serverda tiklash mashqi kamida bir marta
    muvaffaqiyatli o'tkazilgan».

    =======================================================================
    ⛔⛔ CI'DA O'LCHANADIGAN YARIM — VA U MEZONNING O'RNINI BOSMAYDI.

    «Boshqa lokatsiyaga ketadi» REAL offsite `restic` repo'sini talab
    qiladi; «toza serverda tiklash mashqi o'tkazilgan» esa REAL toza
    serverni (VPS). ⛔ IKKALASI HAM CI'DA YO'Q va hech qachon
    bo'lmaydi. Bandning EGASI **Ops**, joyi **`08-HUMAN-UAT.md`**,
    tetigi **VPS deploy'i**.

    Bu yerda o'lchanadigan narsa ANIQ va u uch qismdan iborat:

      (a) zaxira faktining YAGONA yo'li — mahsulot skripti. Yurak
          urishi `ops/backup/heartbeat.sql` bilan yoziladi va u
          `run-backup.sh` ning ENG OXIRGI qadami, ya'ni yiqilgan zanjir
          hech qanday «muvaffaqiyat» qoldirmaydi;
      (b) faktning YO'QLIGI KO'RINADI — komponent kuzatuv reyestrida
          (`EXPECTED_COMPONENTS`) va u yozilmaguncha
          `/internal/self-check` uni `never_seen` da ochiq ko'rsatadi;
      (c) mexanizm qatlami DEFAULT to'plamda yuguradi — `restore`
          markeri `addopts` dan CHIQARILMAGAN, ya'ni
          `test_restore_drill.py` va `test_backup_contract.py`
          `npm run test` / `npm run gate` da ishlaydi.

    ⛔ Mexanika qatlamining yashilligi bilan haqiqat qatlamining
       yo'qligini yopish TAQIQLANADI (3- va 5-fazaning darsi). Shu
       sababdan **FOUND-07 `Done` QILINMAYDI** — u `Blocked` bo'lib
       qoladi va sababi REQUIREMENTS.md da LITERAL yozilgan.
    =======================================================================
    """
    assert BACKUP_COMPONENT in EXPECTED_COMPONENTS, (
        f"`{BACKUP_COMPONENT}` kuzatuv reyestrida yo'q — zaxira umuman ishlamay "
        "qolganda buni HECH KIM ko'rmasdi"
    )

    sync_owner_conn.execute(_DROP_BACKUP_HEARTBEAT, (BACKUP_COMPONENT,))
    try:
        # ---- (b) YO'QLIK KO'RINADI.
        before = await api_client.get(SELF_CHECK_URL)
        assert BACKUP_COMPONENT in before.json()["never_seen"], (
            f"zaxira hech qachon ishlamagan holatda `{BACKUP_COMPONENT}` `never_seen` "
            f"ro'yxatida YO'Q: {before.json()} — kuzatuvchi jim qolardi"
        )

        # ---- (a) FAKT FAQAT MAHSULOT SKRIPTIDAN KELADI.
        sync_owner_conn.execute(_heartbeat_statement(), (env.day.isoformat(),))

        after = await api_client.get(SELF_CHECK_URL)
        body = after.json()
        assert BACKUP_COMPONENT not in body["never_seen"], (
            f"mahsulot skripti bajarilgandan keyin ham `{BACKUP_COMPONENT}` `never_seen` "
            f"da qoldi: {body} — komponent nomi zanjirdan AJRALGAN"
        )
        assert BACKUP_COMPONENT not in body["stale"], body
    finally:
        sync_owner_conn.execute(_DROP_BACKUP_HEARTBEAT, (BACKUP_COMPONENT,))

    # ---- (c) MEXANIZM QATLAMI DEFAULT TO'PLAMDA.
    config = tomllib.loads((_REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    addopts = str(config["tool"]["pytest"]["ini_options"]["addopts"])
    assert "restore" not in addopts, (
        f"`restore` markeri standart `addopts` dan chiqarilgan: {addopts!r} — tiklash "
        "mashqining MEXANIZM qatlami jimgina yugurmay qo'yardi va SC#3 ning CI'da "
        "o'lchanadigan yarmi ham yo'qolardi"
    )
    for name in ("integration/test_restore_drill.py", "unit/test_backup_contract.py"):
        assert (_REPO_ROOT / "tests" / name).is_file(), (
            f"zanjirning bo'g'ini topilmadi: tests/{name} — u ko'chirilgan bo'lsa bu "
            "mezon ham yangilanishi SHART"
        )


# ===========================================================================
# SC#4
# ===========================================================================


async def test_sc4_runbook_exists_and_all_three_locales_reach_the_document(
    api_client: httpx.AsyncClient,
    director_headers: dict[str, str],
    env: Env,
) -> None:
    """MEZON #4: «Go-live runbook tayyor va uch tilli interfeys yakuniy
    tekshiruvdan o'tgan — kassir, nazoratchi va admin tizimda mashq qilib
    ko'rgan».

    =======================================================================
    ⛔⛔ INSON YARMI CI'DA BAJARILMAYDI VA U SHU YERDA LITERAL YOZILADI.

    «Kassir, nazoratchi va admin tizimda mashq qilib ko'rgan» — bu
    ODAMNING harakati. Uni o'lchayotgandek ko'rsatish bu fazadagi eng
    arzon yolg'on bo'lardi: uch rolning sessiyasini ochib «mashq
    bo'ldi» deb yozish MUMKIN, lekin u HECH NIMANI isbotlamasdi.
    Bandning EGASI **direktor**, joyi **`08-HUMAN-UAT.md`**, tetigi
    **pilot tayyorgarligi haftasi**.

    O'lchanadigan yarim IKKI qism:

      (a) **RUNBOOK MAVJUD** — `ops/docs/go-live.md`. Uning SHAKLI
          (har kod blokidan keyin «Kutilgan natija:») `tests/unit/
          test_runbook_shape.py` da o'lchanadi va bu yerda
          TAKRORLANMAYDI; bu yerdagi da'vo faqat mavjudlik va u
          zanjirning bo'g'inini bog'laydi;

      (b) **UCH TIL HUJJATGA YETIB BORADI** — va bu qism aynan shu
          modulda o'lchanishi kerak. Til FOYDALANUVCHI PROFILIDAN
          keladi (D-06), ya'ni uni ekran emas, SERVER tanlaydi.
          Katalogda uch til borligi YETMASDI: ekran uchta tilda
          chizilib, yuklab olingan fayl bitta tilda chiqishi mumkin
          edi va buni faqat FAYLNI ochgan odam ko'rardi.

    ⚠ TIL HAR AYLANISHDA HUJJATDAN O'QILADI, `report_texts` bilan
      SOLISHTIRILADI — ya'ni «boshqa til qaytdi» holati sarlavha
      qatorining O'ZIDA ko'rinadi.
    =======================================================================
    """
    runbook = _REPO_ROOT / "ops" / "docs" / "go-live.md"
    assert runbook.is_file(), (
        f"go-live runbook topilmadi: {runbook} — SC#4 ning birinchi yarmi manbasiz qolardi"
    )
    assert len(runbook.read_text(encoding="utf-8").strip()) > 0, (
        "go-live runbook BO'SH — mavjudlik da'vosi bo'sh fayl ustida ham rost bo'lardi"
    )

    original = (await api_client.get(PROFILE_URL, headers=director_headers)).json()["locale"]
    seen: dict[str, tuple[str | None, ...]] = {}
    try:
        for locale in ("uz-Latn", "uz-Cyrl", "ru"):
            switched = await api_client.patch(
                PROFILE_URL, json={"locale": locale}, headers=director_headers
            )
            assert switched.status_code == 200, switched.text

            document = await api_client.get(
                REVENUE_XLSX_URL, params=_period(), headers=director_headers
            )
            assert document.status_code == 200, document.text

            rows = read_rows(document.content, expected_columns=_EXPORT_COLUMNS["revenue"])
            assert rows, f"{locale}: hujjatda birorta qator yo'q"
            assert rows[0].values == _header_row("revenue", locale), (
                f"{locale} profilida hujjat sarlavhasi BOSHQA tilda qaytdi: {rows[0].values}"
            )
            seen[locale] = rows[0].values
    finally:
        # ⛔ TIKLASH MAJBURIY: profil qatori sessiya davomida yashaydi va
        #    tiklanmagan qiymat keyingi testlarga SIZIB o'tardi.
        await api_client.patch(PROFILE_URL, json={"locale": original}, headers=director_headers)

    assert len(set(seen.values())) == 3, (
        f"uch til hujjatda UCH XIL sarlavha bermadi: {seen} — bir necha til bir xil "
        "matnga tushgan bo'lsa «uch tilli» da'vosi HUJJAT darajasida rost emas"
    )


# ===========================================================================
# SC#5
# ===========================================================================


async def test_sc5_three_way_compare_separates_three_diff_classes_and_is_signed(
    api_client: httpx.AsyncClient,
    sync_owner_conn: Connection[TupleRow],
    admin_headers: dict[str, str],
    director_headers: dict[str, str],
    env: Env,
) -> None:
    """MEZON #5: «Parallel rejim uchun 3 tomonlama solishtiruv vositasi
    ishlaydi: daftar vs tizim vs AI-kutilgan — kunlik chiqariladi va
    imzolanadi».

    =======================================================================
    ZANJIR TO'LIQ: QOG'OZ DAFTAR -> IMPORT MARSHRUTI -> SOLISHTIRUV ->
    IMZOLANADIGAN HUJJAT.

    Daftar TIZIMDA UMUMAN YO'Q — u tashqi qog'ozdan keladigan UCHINCHI
    manba, ya'ni u MAHSULOT MARSHRUTI orqali kiritiladi
    (`POST /reports/compare/ledger`), bazaga to'g'ridan-to'g'ri
    yozilmaydi. Import qadamini chetlab o'tish zanjirning eng uzun
    bo'g'inini o'lchovsiz qoldirardi.

    ⛔ IKKI ROL VA BU HAM MEZONNING BIR QISMI: daftarni **bozor admini**
       yuklaydi (`stall_manage`), hujjatni esa **direktor** oladi
       (`report_view`). Bitta rolda o'lchash haqiqiy oqimni
       soddalashtirardi.

    =======================================================================
    ⛔⛔ UCH FARQ SINFI HECH QACHON QO'SHILMAYDI (D-18).

    Ular uch BOSHQA harakatni talab qiladi: «pulni qidiring»
    (`ledger_over`), «daftarni tuzating» (`system_over`), «detektorni
    tekshiring» (`ai_mismatch`). Shuning uchun seed uchala sinfni ham
    ALOHIDA rastada quradi va to'rtinchi rasta MOS bo'ladi — mos
    qatorsiz maxraj imzolanadigan varaqda ko'rinmasdi.

    ⚠ «Imzolanadi» — ikki BO'SH imzo qatori (§12.6). Ismlar oldindan
      to'ldirilmaydi: tizim KIM imzolashini BILMAYDI va sessiyadagi
      foydalanuvchining ismini yozish nizoda YOLG'ON dalil bo'lardi
      (T-08-74).
    =======================================================================
    """
    day = env.day
    live = env.billing.market_a
    over_ledger, over_system, ai_gap, matched = (env.billed_stall(index) for index in range(4))

    # (1) DAFTAR ORTIQ: qog'ozda 20 000, tizimda 15 000.
    add_daily_charge(
        conn=sync_owner_conn,
        market_id=env.market_id,
        stall_id=over_ledger,
        vendor_id=live.vendor_id,
        tariff_id=live.tariff_id,
        service_date=day,
    )
    add_payment(
        sync_owner_conn,
        market_id=env.market_id,
        stall_id=over_ledger,
        vendor_id=live.vendor_id,
        cashier_id=live.cashier_id,
        shift_id=live.open_shift_id,
        service_date=day,
        amount_soum=TARIFF_SOUM,
        quote_soum=TARIFF_SOUM,
    )

    # (2) TIZIM ORTIQ: qog'ozda umuman yo'q (0), tizimda to'lov bor.
    add_daily_charge(
        conn=sync_owner_conn,
        market_id=env.market_id,
        stall_id=over_system,
        vendor_id=live.vendor_id,
        tariff_id=live.tariff_id,
        service_date=day,
    )
    add_payment(
        sync_owner_conn,
        market_id=env.market_id,
        stall_id=over_system,
        vendor_id=live.vendor_id,
        cashier_id=live.cashier_id,
        shift_id=live.open_shift_id,
        service_date=day,
        amount_soum=TARIFF_SOUM,
        quote_soum=TARIFF_SOUM,
    )

    # (3) BANDLIK FARQI: daftar = tizim, AI esa rastani BO'SH dedi.
    add_daily_charge(
        conn=sync_owner_conn,
        market_id=env.market_id,
        stall_id=ai_gap,
        vendor_id=live.vendor_id,
        tariff_id=live.tariff_id,
        service_date=day,
    )
    add_payment(
        sync_owner_conn,
        market_id=env.market_id,
        stall_id=ai_gap,
        vendor_id=live.vendor_id,
        cashier_id=live.cashier_id,
        shift_id=live.open_shift_id,
        service_date=day,
        amount_soum=TARIFF_SOUM,
        quote_soum=TARIFF_SOUM,
    )
    # (4) MOS: uch manba ham nolda uchrashadi.
    for stall_id in (ai_gap, matched):
        sync_owner_conn.execute(
            _INSERT_SLOT,
            (
                str(uuid4()),
                str(env.market_id),
                str(stall_id),
                day,
                DEFAULT_SNAPSHOT_SLOTS[0],
                OccupancyVerdict.EMPTY.value,
                "ai",
            ),
        )

    codes = {
        name: _code_of(sync_owner_conn, stall)
        for name, stall in (
            ("ledger_over", over_ledger),
            ("system_over", over_system),
            ("ai_mismatch", ai_gap),
            ("match", matched),
        )
    }

    # ---- DAFTAR MAHSULOT MARSHRUTI ORQALI KIRADI.
    imported = await api_client.post(
        LEDGER_URL,
        params={"day": day.isoformat()},
        headers=admin_headers,
        files={
            "file": (
                "daftar.xlsx",
                _ledger_file(
                    [
                        (codes["ledger_over"], TARIFF_SOUM + 5_000),
                        (codes["ai_mismatch"], TARIFF_SOUM),
                        (codes["match"], 0),
                    ]
                ),
                XLSX_MEDIA_TYPE,
            )
        },
    )
    assert imported.status_code == 200, imported.text

    # ---- SOLISHTIRUV: uchala sinf ham ALOHIDA sanaladi.
    report = await api_client.get(
        COMPARE_URL, params={"day": day.isoformat()}, headers=director_headers
    )
    assert report.status_code == 200, report.text
    payload = report.json()
    assert payload["has_ledger"] is True, payload

    by_code = {row["stall_code"]: row for row in payload["rows"]}
    for expected_class, code in codes.items():
        actual = by_code[code]["diff_class"]
        assert actual == (None if expected_class == "match" else expected_class), (
            f"{code} rastasi `{actual}` sinfini oldi, kutilgani `{expected_class}` — "
            "uch sinf bir-biriga qo'shilib ketgan bo'lsa direktor QAYSI harakat "
            "kerakligini bilolmasdi (D-18)"
        )
    assert payload["ledger_over_count"] == 1, payload
    assert payload["system_over_count"] == 1, payload
    assert payload["ai_mismatch_count"] == 1, payload
    assert payload["matched_count"] == 1, payload

    # ---- IMZOLANADIGAN HUJJAT: baytlar QAYTA O'QILADI.
    document = await api_client.get(
        COMPARE_XLSX_URL, params={"day": day.isoformat()}, headers=director_headers
    )
    assert document.status_code == 200, document.text
    assert document.headers["content-type"] == XLSX_MEDIA_TYPE

    assert _EXPORT_COLUMNS["compare"] == xlsx_export.COMPARE_EXPORT_COLUMNS, (
        "solishtiruv hujjatining ustunlar soni mahsulot konstantasidan AJRALDI — "
        "o'quvchi noto'g'ri katakka qarardi"
    )
    rows = read_rows(document.content, expected_columns=_EXPORT_COLUMNS["compare"])
    assert rows[0].values in {
        _header_row("compare", locale) for locale in ("uz-Latn", "uz-Cyrl", "ru")
    }, rows[0].values

    texts = xlsx_export.report_texts("uz-Latn")
    first_column = [row.values[0] for row in rows]
    for signature in (texts["compare_sign_executor"], texts["compare_sign_approver"]):
        assert signature in first_column, (
            f"imzo qatori hujjatda yo'q: {signature!r} — «imzolanadi» jumlasi CHOP "
            "ETILGAN varaqda bajarilishi kerak, ekranda emas (§10.7: raqamli imzo YO'Q)"
        )


# ===========================================================================
# META — MEZONLARDAN BIRORTASI JIMGINA TUSHIB QOLMASIN
# ===========================================================================


def test_every_criterion_has_its_own_test() -> None:
    """Beshala mezon uchun AYNAN BITTA nomlangan test mavjud.

    USIZ MEZONLARDAN BIRI JIMGINA TUSHIB QOLARDI: fayl qayta tashkil
    qilinganda yoki test vaqtincha o'chirilganda darvoza baribir yashil
    bo'lardi va «beshala mezon o'lchanadi» da'vosi isbotsiz qolardi.

    ⚠ META-TESTNING O'Z NOMIDA `sc<raqam>` YO'Q va bu ataylab: darvoza
      `sc[1-5]` naqshini SANAYDI, ya'ni meta-testning o'zi sanoqqa kirib
      ketmasligi kerak.

    ⛔ `CRITERIA` NING UZUNLIGI HAM O'LCHANADI: mezon matni ROADMAP dan
       ko'chiriladi va bittasi tushib qolsa testlar soni bilan mos
       kelmay qolardi.
    """
    names = sorted(name for name, _ in _module_tests())
    assert len(names) >= 8, (
        f"modulda faqat {len(names)} ta test topildi — introspeksiya BO'SH ro'yxatda "
        "ishlayotgan bo'lsa bu darvoza jimgina yashil bo'lardi"
    )

    assert len(CRITERIA) == 5, f"`CRITERIA` da {len(CRITERIA)} ta matn bor, kutilgani 5"

    for number in range(1, 6):
        owned = [name for name in names if name.startswith(f"test_sc{number}_")]
        assert len(owned) == 1, (
            f"SC#{number} uchun {len(owned)} ta test topildi ({owned}) — har mezonning "
            "egasi AYNAN BITTA nomlangan test bo'lishi kerak"
        )

    criteria = [name for name in names if name.startswith("test_sc")]
    assert len(criteria) == len(CRITERIA), f"mezon testlari soni 5 emas: {criteria}"


def test_criteria_module_uses_no_fakes() -> None:
    """SOXTALASHTIRISHSIZ O'LCHOV DARVOZASI — TO'RT MUSTAQIL YO'L.

    =======================================================================
    NEGA TO'RT YO'L VA NEGA BIRORTASI QOLGANINI QOPLAMAYDI.

      1. KUTUBXONA IMPORTI — `ast` daraxtida ko'rinadi. Satr bo'yicha
         qidiruv izohni koddan ajrata olmasdi, shuning uchun daraxt
         o'qiladi.
      2. FIXTURE SO'ROVI — pytest ning O'Z tuzatuvchi fixture'i yoki
         loyihaning spy'i birorta IMPORT talab qilmaydi, ya'ni birinchi
         yo'l uni UMUMAN ko'rmasdi.
      3. ⛔ ZAXIRA FAKTINI QO'LDA YOZADIGAN SQL — u na import, na
         fixture: u SATR KONSTANTASI. Bu fazaning ENG ARZON yolg'oni
         aynan shu bo'lardi — zanjir yugurmasdan «ishladi» deb yozish.
      4. ⛔ EKSPORT DA'VOSINI BAYTLARSIZ QOLDIRISH — u umuman
         QO'SHIMCHA emas, KAMCHILIK: hujjat yo'li ishlatilgan, lekin
         o'quvchi chaqirilmagan. Uchala yuqoridagi skaner ham buni
         KO'RMASDI, chunki hech nima QO'SHILMAGAN.

    ⚠ BESHINCHI DA'VO — DARAXTNING BO'SH BO'LMASLIGI. Skaner nosozlansa
      yoki fayl qayta nomlansa hamma to'plam bo'sh chiqib, darvoza
      TRIVIAL ravishda yashil bo'lardi.

    ⛔ «O'TKAZIB YUBORISH» YO'LI ATAYIN YO'Q: bu yerda `skipif` ham,
       `xfail` ham yo'q. Soxtalashtirilgan mezon — «faza tugadi» degan
       da'voning eng arzon yolg'on shakli.
    =======================================================================
    """
    tree = ast.parse(_MODULE_PATH.read_text(encoding="utf-8"))

    # ---- 1-YO'L: IMPORTLAR.
    roots: set[str] = set()
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots |= {alias.name.split(".")[0] for alias in node.names}
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                roots.add(node.module.split(".")[0])
            imported |= {alias.name for alias in node.names}

    assert len(roots) >= 10, (
        f"faqat {len(roots)} ta import ildizi topildi — `ast` skaneri bo'sh daraxtda "
        "ishlayotgan bo'lsa bu darvoza JIMGINA yashil bo'lardi"
    )
    assert not roots & _FAKE_ROOTS, (
        f"soxtalashtirish kutubxonasi import qilingan: {sorted(roots & _FAKE_ROOTS)} — "
        "bu modul HAQIQIY `postgres:18.4`, HAQIQIY marshrut grafi va HAQIQIY "
        "`.xlsx` baytlari ustida o'lchaydi"
    )
    faked = sorted(
        name for name in imported if name in _FAKE_IMPORTS or name.endswith(_MOCK_SUFFIX)
    )
    assert faked == [], f"soxtalashtirish vositasi import qilingan: {faked}"

    # ---- 2-YO'L: MODUL GLOBALLARI VA TEST IMZOLARI.
    module = sys.modules[__name__]
    globals_seen = set(vars(module))
    assert len(globals_seen) >= 20, (
        f"modul global nomlari faqat {len(globals_seen)} ta — ikkinchi yo'l BO'SH "
        "to'plamda ishlayotgan bo'lsa u ham jimgina yashil bo'lardi"
    )
    assert not globals_seen & _FAKE_FIXTURES, (
        f"soxtalashtiruvchi nom modul darajasida bog'langan: "
        f"{sorted(globals_seen & _FAKE_FIXTURES)}"
    )

    tests = _module_tests()
    assert len(tests) >= 8, (
        f"modulda faqat {len(tests)} ta test topildi — imzo skaneri BO'SH ro'yxatda "
        "ishlayotgan bo'lsa bu darvoza ham jimgina yashil bo'lardi"
    )
    requested = sorted(
        f"{name}({', '.join(sorted(_FAKE_FIXTURES & set(inspect.signature(obj).parameters)))})"
        for name, obj in tests
        if _FAKE_FIXTURES & set(inspect.signature(obj).parameters)
    )
    assert requested == [], (
        f"quyidagi testlar soxtalashtiruvchi fixture so'rayapti: {requested} — mezon "
        "moduli na bazani, na marshrut grafini, na hujjat o'quvchisini almashtiradi"
    )

    # ---- 3-YO'L: ZAXIRA FAKTINI QO'LDA YOZADIGAN SQL.
    hand_written = sorted(
        value
        for value in _string_constants(tree)
        if _HEARTBEAT_TABLE in value.lower() and any(verb in value.lower() for verb in _WRITE_VERBS)
    )
    assert hand_written == [], (
        f"⛔ zaxira fakti QO'LDA yozilyapti: {hand_written}. «Zaxira ishladi» faktining "
        "YAGONA manbai — `ops/backup/heartbeat.sql`, aks holda mezon O'Z SEEDINI "
        "o'lchagan bo'lardi va `backup_stale` MANGU jim turardi"
    )

    # ---- 4-YO'L: EKSPORT DA'VOSI BAYTLARSIZ QOLMAYDI.
    #
    # ⛔ ISTE'MOLCHINING TA'RIFI IJRO PAYTIDA TORAYTIRILDI VA SABAB YOZILADI.
    #    Birinchi shakl «modul nomini ISHLATGAN test» edi va u nazorat
    #    testini (`test_the_module_measures_a_market_that_the_seed_actually
    #    _owns`) YOLG'ON-QIZIL qildi: u yo'llarni marshrut GRAFIDA izlaydi,
    #    hujjat SO'RAMAYDI. Ya'ni skaner «nomni tilga oldi» ni o'lchayotgan
    #    edi, holbuki taqiqning o'zi boshqa narsa haqida: «JAVOB HAQIDA
    #    DA'VO qildi». Da'voning mexanik izi — `status_code` ga murojaat.
    #    Nom bo'yicha istisno ro'yxati yozish darvozani BO'SHATARDI va
    #    keyingi ijrochi unga yangi nom qo'shib qutulardi.
    consumers: list[str] = []
    silent: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.AsyncFunctionDef | ast.FunctionDef):
            continue
        if not node.name.startswith("test_") or node.name == _SCANNER_TEST:
            continue
        used = {inner.id for inner in ast.walk(node) if isinstance(inner, ast.Name)}
        if not used & _EXPORT_URL_NAMES:
            continue
        claims_response = any(
            isinstance(inner, ast.Attribute) and inner.attr == _RESPONSE_CLAIM
            for inner in ast.walk(node)
        )
        if not claims_response:
            continue
        consumers.append(node.name)
        called = {
            inner.func.id
            for inner in ast.walk(node)
            if isinstance(inner, ast.Call) and isinstance(inner.func, ast.Name)
        }
        if _READER_CALL not in called:
            silent.append(node.name)

    assert len(consumers) >= 3, (
        f"hujjat yo'lini ishlatgan faqat {len(consumers)} ta test topildi ({consumers}) — "
        "skaner BO'SH to'plamda ishlayotgan bo'lsa bu darvoza jimgina yashil bo'lardi"
    )
    assert silent == [], (
        f"⛔ quyidagi testlar hujjatni SO'RADI, lekin baytlarini O'QIMADI: {silent}. "
        f"`{_READER_CALL}` chaqirilmagan da'vo faqat javob kodini o'lchaydi — brauzer "
        "esa xato javobning TANASINI ham `.xlsx` nomi bilan saqlaydi"
    )


def test_the_fake_registry_names_are_built_correctly() -> None:
    """NAZORAT — bo'laklab qurilgan reyestr AYNAN kutilgan nomlarni beradi.

    ⛔ USIZ BUTUN SOXTALASHTIRISH DARVOZASI JIMGINA BO'SHAB QOLARDI: bir
       harflik bo'laklash xatosi hech qayerda ko'rinmasdi va yuqoridagi
       to'rt to'plam hech qachon hech nimani ushlamasdi.

    ⚠ KUTILGAN NOMLAR HAM BO'LAKLAB QURILADI va sabab o'sha: bu
      modulning uchinchi darvozasi MATN SKANI bilan ishlaydi.
    """
    assert len(_UNIT) == 8 and _UNIT.startswith("unit"), f"bo'laklash buzilgan: {_UNIT!r}"
    assert _UNIT in _FAKE_ROOTS
    assert len(_MOCK) == 4, f"bo'laklash buzilgan: {_MOCK!r}"
    assert _MOCK in _FAKE_ROOTS
    assert ("pytest_" + _MOCK) in _FAKE_ROOTS

    assert len(_PATCH) == 5, f"bo'laklash buzilgan: {_PATCH!r}"
    assert _PATCH in _FAKE_IMPORTS
    assert ("monkey" + _PATCH) in _FAKE_FIXTURES

    assert _MOCK.capitalize() == _MOCK_SUFFIX, f"qo'shimcha buzilgan: {_MOCK_SUFFIX!r}"
    assert ("Magic" + _MOCK_SUFFIX).endswith(_MOCK_SUFFIX)
    assert not ("Magic" + _MOCK_SUFFIX).endswith(_MOCK_SUFFIX + "s")

    # ⛔ 3-DARVOZANING NISHONI — JADVAL NOMI MAHSULOT REYESTRIDAN.
    assert _DROP_BACKUP_HEARTBEAT.split()[2] == _HEARTBEAT_TABLE, (
        f"jadval nomi reyestrdan ajralib ketgan: {_HEARTBEAT_TABLE!r} — 3-darvoza "
        "hech nimani ushlamasdi"
    )
    assert _WRITE_VERBS and all(verb.islower() for verb in _WRITE_VERBS)

    # ⛔ 4-DARVOZANING KIRISHI — HAR NOM MODUL GLOBALI VA HUJJAT YO'LINI TASHIYDI.
    module = vars(sys.modules[__name__])
    for name in sorted(_EXPORT_URL_NAMES):
        assert name in module, (
            f"`_EXPORT_URL_NAMES` da mavjud bo'lmagan nom bor: {name!r} — reyestr "
            "eskirgan va skaner iste'molchini TOPMASDI"
        )
        value = module[name]
        carried = value if isinstance(value, tuple) else (value,)
        assert all(str(item).endswith(".xlsx") for item in carried), (
            f"{name} hujjat yo'lini tashimayapti: {value!r}"
        )

    assert read_rows.__name__ == _READER_CALL, (
        f"o'quvchining nomi reyestrdan ajralib ketgan: {_READER_CALL!r} != "
        f"{read_rows.__name__!r} — 4-darvoza hamma testni jimgina yashil qilardi"
    )
    # ⚠ MAYDON EKZEMPLYARDA, SINFDA EMAS (`httpx` uni `__init__` da
    #   bog'laydi) — o'lchandi: `hasattr(httpx.Response, ...)` `False`
    #   berardi va nazoratning O'ZI yolg'on-qizil bo'lardi.
    assert hasattr(httpx.Response(200), _RESPONSE_CLAIM), (
        f"javob obyektida `{_RESPONSE_CLAIM}` maydoni yo'q — 4-darvozaning TETIGI "
        "hech qachon yonmasdi va u hamma testni jimgina yashil qilardi"
    )
    assert _SCANNER_TEST in module, (
        f"skanerning nomi o'zgargan: {_SCANNER_TEST!r} topilmadi — istisno endi "
        "boshqa funksiyaga tegishli bo'lib qolardi"
    )


def test_the_module_measures_a_market_that_the_seed_actually_owns(
    sync_owner_conn: Connection[TupleRow], env: Env
) -> None:
    """NAZORAT — seed HAQIQATAN yozilgan va mezonlar bo'sh bazada yugurmayapti.

    ⛔ USIZ BUTUN FAYL «BO'SH TO'PLAM USTIDA YASHIL» BO'LARDI: har
       `assert` ning kirish holati seeddan keladi va seed jimgina
       yiqilganda mezonlar «hech nima yo'q, demak hammasi joyida»
       deganday ko'rinardi (06-14 naqshi).
    """
    stalls = sync_owner_conn.execute(
        "SELECT count(*) FROM stalls WHERE market_id = %s AND status = 'active'",
        (str(env.market_id),),
    ).fetchone()
    assert stalls is not None and stalls[0] >= _FRAME_STALLS, (
        f"A bozorida {stalls} ta faol rasta bor — SC#2 doirasi {_FRAME_STALLS} ta "
        "rastaga tayanadi va kamrog'ida u JIMGINA kichrayardi"
    )

    other = sync_owner_conn.execute(
        "SELECT count(*) FROM stalls WHERE market_id = %s AND status = 'active'",
        (str(env.market_b_id),),
    ).fetchone()
    assert other is not None and other[0] > 0, (
        "B bozorida faol rasta yo'q — tenant chegarasi BO'SH bozor ustida jimgina rost bo'lardi"
    )

    runs = sync_owner_conn.execute(
        "SELECT count(*) FROM capture_runs WHERE market_id = %s",
        (str(env.market_id),),
    ).fetchone()
    assert runs is not None and runs[0] > 0, (
        "A bozorida kadr olish yugurishi yo'q — SC#2 kadrni AYNAN shu qatordan "
        "quradi va seedsiz doira bo'sh bo'lardi"
    )

    # ⚠ MARSHRUTLAR `app.openapi()` DAN, `app.routes` DAN EMAS: v1 yuzasi
    #   ALOHIDA ilova sifatida `mount` qilingan (06-14 da o'lchandi).
    routes = set(fastapi_app.openapi()["paths"])
    assert len(routes) >= 40, (
        f"OpenAPI sxemasida faqat {len(routes)} ta marshrut bor — skaner marshrut "
        "grafining boshqa shaklini ko'ryapti"
    )
    for path in (
        REVENUE_URL,
        DEBTORS_URL,
        ANOMALIES_URL,
        COMPARE_URL,
        LEDGER_URL,
        REVENUE_XLSX_URL,
        DEBTORS_XLSX_URL,
        ANOMALIES_XLSX_URL,
        ACCURACY_XLSX_URL,
        COMPARE_XLSX_URL,
    ):
        assert path in routes, (
            f"{path} marshrut grafida yo'q — mezonlar MAVJUD BO'LMAGAN yuzani o'lchayotgan bo'lardi"
        )
