"""Billing domeni: kunlik hisob, tuzatish, dalil, to'lov, smena va anomaliya.

=============================================================================
BU FAYLDA OLTITA QAROR YASHAYDI VA HAMMASI KODDA EMAS, SXEMADA.
Ular "qulaylik uchun" buzilishi oson, shuning uchun sabablari shu yerda.

1. NOM `daily_charges`, `charges` EMAS (C-1). Nom 1-fazadan QULFLANGAN:
   `sbozor_core.schema_contract.FINANCIAL_TABLES` da u AYNAN shu nom bilan
   yozilgan va `tests/tenancy/test_meta.py::test_financial_tables_have_guards`
   bazada AYNAN shu nomni izlaydi. `charges` deb nomlash darvozani
   «jadval yo'q» holatida jimgina yashil qoldirardi — ya'ni uchala moliyaviy
   qo'riqchi ham hech qachon tekshirilmasdi. D-06 va D-07 ning MA'NOSI
   o'zgarmaydi, faqat nom.

2. `service_date` VA `business_date` — IKKI XIL SAVOL (C-2, D-06).

       service_date  — hisob QAYSI KUN uchun yozildi (DOMEN sanasi)
       business_date — qator QAYSI KUNDA yozildi   (AUDIT fakti)

   Ikkalasi ATAYIN ajratilgan. `business_date` `created_at` dan HOSILA
   (`BILLING_BUSINESS_DATE_EXPR`), ya'ni unga aniq qiymat yozib bo'lmaydi —
   `tests/integration/test_business_date.py:134-145` uni RAD ETADI. Shuning
   uchun D-06 ning idempotentlik kaliti `UNIQUE (market_id, stall_id,
   service_date)`: kalit HISOBLANAYOTGAN kunda, YOZILGAN kunda emas.
   Kun 04:10 da yopiladi (C-3), ya'ni normal holatda ikkalasi FARQ QILADI
   va backfill ham aynan shu farq bilan ajraladi.

   ⚠ 06-01 ning A2 zondi ikkinchi variantni (`business_date GENERATED
   ALWAYS AS (service_date) STORED`) HAQIQIY `postgres:18.4` da o'lchagan:
   u ISHLAYDI (`GENERATED_FROM_COLUMN_SUPPORTED = True`). Baribir Variant A
   tanlandi — Variant B «qator qachon yozilgan» AUDIT FAKTINI butunlay
   yo'qotardi va D-02 ning nizo modeli aynan shunga tayanadi.

3. TO'LOV — SOTUVCHI DARAJASIDAGI KREDIT, `charge_id` YO'Q (C-4/D-24).
   Sabab MEXANIK: kassir kun davomida yig'adi, hisob esa ERTASI KUNI
   04:10 da tug'iladi — ya'ni to'lov paytida `charge_id` MAVJUD EMAS.
   Ustiga bitta to'lov bir necha kunlik qarzni yopishi mumkin (§9.6),
   ya'ni bog'lanish 1:1 emas. Kun kesimi HOSILA qoida bilan olinadi:
   `sbozor_core.billing.allocate_charge_credit()`,
   `FIFO_OLDEST_SERVICE_DATE_FIRST` (06-01).

4. MANFIY SUMMA YOZILMAYDI (C-5/D-23). Har joyda MUSBAT KATTALIK +
   `kind` / `direction`. `test_meta.py:1341-1347` har moliyaviy jadvaldan
   `CHECK (amount_soum > 0)` talab qiladi va `money.py:78-79` manfiyni rad
   etadi. D-23 ning «belgili summalar yig'indisi» iborasi — HISOBLASH
   USULI, ustun tipi emas.

5. MUZLATILGAN DALIL — `occupancy_event_id` (C-7/D-08/D-29).
   `stall_slot_occupancy` MUTABLE (`_MATERIALIZE_SLOT` `DO UPDATE`
   ishlatadi), ya'ni uning `id` si «muzlatilgan dalil» EMAS: kun qayta
   hisoblanganda o'sha qator boshqa hukmni ko'rsatishi mumkin.
   `occupancy_events` esa `0018` bilan SHARTSIZ o'zgarmas — shuning uchun
   `charge_evidence.occupancy_event_id` `NOT NULL` va u dalil zanjirining
   langari. `stall_slot_occupancy_id` FAQAT audit havolasi.

6. ANOMALIYA JUFTLANGAN (C-12). `CHECK ((kind = 'no_coverage_stall') =
   (occupancy_event_id IS NULL))` — `models/occupancy.py:333-344` dagi
   `NO_COVERAGE_IS_PAIRED_CHECK` ning aynan takrori va bir xil sababdan:
   DALILSIZ ANOMALIYA ham, DALILLI QAMROVSIZLIK ham IFODALAB BO'LMAYDI.
   Birinchisi «band, lekin to'lovsiz» da'vosini dalilsiz qoldirardi;
   ikkinchisi esa «ko'ra olmadik» ni «ko'rdik» ga aylantirardi.
=============================================================================

OLTALA JADVAL HAM TENANT JADVALI (`06-PATTERNS.md` §2 R-1): `market_id` +
RLS `ENABLE` va `FORCE` + tenant policy + `market_id` bilan boshlanuvchi
domen konstraytlari + kompozit FK. `market_id` ustunida inline `ForeignKey`
YOZILMAYDI — sabab `models/base.py::market_fk_column()` docstringida.

⚠ PG `ENUM` TIPI ISHLATILMAYDI. Ustunlar `text` + enum'dan HOSILA `CHECK`
ifodasi (`models/occupancy.py:60-64` naqshi). Sabab ikkita: (a) PG enum
tipiga qiymat qo'shish tranzaksiya ichida bajarilmaydi; (b) loyihada
`stalls.status`, `cameras.status` va `occupancy_events.verdict` allaqachon
`text`+`CHECK` — yangi shakl IKKINCHI konventsiya yaratardi.

⚠ PUL — `bigint` SO'M (D-11). Kasrli tip HECH QAYERDA ishlatilmaydi:
yaxlitlanish drifti aynan mahsulot bartaraf etadigan nizoni tug'diradi.

⚠ SAQLANGAN QOLDIQ USTUNI HECH QAYERDA YO'Q (BILL-03). Qarz — HAR DOIM
hisoblanadigan ko'rinish (`total_due_soum()` / `vendor_outstanding()`).
Saqlangan ustun ikkinchi haqiqat manbai bo'lardi va u birinchisidan
jimgina ajralib ketardi — ya'ni «qancha qarzdor?» savoli ikki xil javob
berardi va nizoda ikkalasi ham dalil bo'la olmasdi.

⚠ `TimestampMixin` OLTALA JADVALGA HAM QO'YILMAYDI. `updated_at` «bu
qatorni tahrirlash mumkin» degan YOLG'ON VA'DA berardi, holbuki `0020`
ning uch qo'riqchisi uni DB darajasida imkonsiz qiladi (D-07/D-23/D-25).
`created_at` esa har jadvalda ALOHIDA e'lon qilinadi — u `business_date`
ning YAGONA manbai (`models/occupancy.py:643-645` naqshi).
"""

from __future__ import annotations

from datetime import date, datetime, time
from typing import Final
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Computed,
    Date,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Text,
    Time,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PgUuid
from sqlalchemy.orm import Mapped, mapped_column

from sbozor_core.enums import (
    AdjustmentDirection,
    AdjustmentReason,
    AnomalyKind,
    PaymentKind,
    PaymentMethod,
    ReversalReason,
    ShiftStatus,
)
from sbozor_core.models.base import Base, TenantMixin, uuid_pk
from sbozor_core.models.market import TARIFF_BUSINESS_DATE_EXPR

__all__ = [
    "ADJUSTMENT_DIRECTION_CHECK",
    "ADJUSTMENT_DIRECTION_VALUES",
    "ADJUSTMENT_REASON_CHECK",
    "ADJUSTMENT_REASON_VALUES",
    "ANOMALY_EVIDENCE_IS_PAIRED_CHECK",
    "ANOMALY_KIND_CHECK",
    "ANOMALY_KIND_VALUES",
    "BILLING_ANOMALY_INDEX",
    "BILLING_BUSINESS_DATE_EXPR",
    "CHARGE_ADJUSTMENT_INDEX",
    "CHARGE_EVIDENCE_INDEX",
    "DAILY_CHARGE_DAY_INDEX",
    "DAILY_CHARGE_VENDOR_INDEX",
    "LATE_REVIEW_ADJUSTMENT_INDEX",
    "LATE_REVIEW_ADJUSTMENT_PREDICATE",
    "NO_COVERAGE_ANOMALY_IS_PAIRED_CHECK",
    "OVERRIDE_IS_PAIRED_CHECK",
    "OVERRIDE_REASON_CHECK",
    "PAYMENT_KIND_CHECK",
    "PAYMENT_KIND_VALUES",
    "PAYMENT_METHOD_CHECK",
    "PAYMENT_METHOD_VALUES",
    "PAYMENT_STALL_INDEX",
    "PAYMENT_VENDOR_INDEX",
    "REVERSAL_HAS_NO_OVERRIDE_CHECK",
    "REVERSAL_IS_PAIRED_CHECK",
    "REVERSAL_REASON_CHECK",
    "REVERSAL_REASON_IS_PAIRED_CHECK",
    "REVERSAL_REASON_VALUES",
    "SERVICE_DATE_NOT_IN_FUTURE_CHECK",
    "SHIFT_CLOSED_HAS_DECLARATION_CHECK",
    "SHIFT_CLOSED_HAS_SYSTEM_TOTAL_CHECK",
    "SHIFT_CLOSED_IS_PAIRED_CHECK",
    "SHIFT_OPEN_INDEX",
    "SHIFT_OPEN_PREDICATE",
    "SHIFT_STATUS_CHECK",
    "SHIFT_STATUS_VALUES",
    "BillingAnomaly",
    "CashierShift",
    "ChargeAdjustment",
    "ChargeEvidence",
    "DailyCharge",
    "Payment",
]

BILLING_BUSINESS_DATE_EXPR: Final = TARIFF_BUSINESS_DATE_EXPR
"""`business_date` generated ustunining ifodasi — TO'RTINCHI NUSXA YOZILMAYDI.

⛔ IFODA BU YERDA QAYTA YOZILMAYDI va bu qat'iy talab:
`06-04-PLAN.md` «ifoda `migrations.helpers` dan IMPORT qilinadi» deydi,
lekin `sbozor_core` `migrations.helpers` ni IMPORT QILA OLMAYDI — o'sha
modul `alembic.op` ni import qiladi, `sbozor-core` ning
`pyproject.toml` ida esa `alembic` UMUMAN YO'Q. Ya'ni bunday import
`cv-service` va `bot-service` da `ModuleNotFoundError` bilan yiqilardi
(bog'liqlik yo'nalishi `models/market.py:188-196` da yozilgan).

Shuning uchun mavjud nusxa QAYTA ISHLATILADI: `TARIFF_BUSINESS_DATE_EXPR`
(`models/market.py:185`) — u `migrations.helpers.BUSINESS_DATE_EXPR` ning
oyna nusxasi va uning `AYNAN bir xil bo'lishi SHART` talabi o'sha yerda
yozilgan. Bu yerda YANGI literal yozish TO'RTINCHI nusxa bo'lardi va
mintaqa arifmetikasi undan ajralib ketardi.

⚠ MIGRATSIYA BOSHQACHA QILADI: `0020_billing_domain.py` ifodani
`migrations.helpers.BUSINESS_DATE_EXPR` DAN import qiladi
(`0008_temporal.py:196-206` naqshi). Ya'ni DDL tomonida ham, model
tomonida ham literal QAYTA YOZILMAYDI.

⚠ IFODANING MINTAQA SHAKLI (ikki argumentli — IMMUTABLE, bitta
argumentlisi STABLE va generated ustunda umuman ruxsat etilmaydi) shu
faylda TAKRORLANMAYDI ham, tushuntirilmaydi ham: u
`migrations/helpers.py::BUSINESS_DATE_EXPR` va
`models/market.py::TARIFF_BUSINESS_DATE_EXPR` docstringlarida yozilgan.
Uni bu yerda qayta yozish o'sha ifodaning UCHINCHI tushuntirishi bo'lardi
va tushuntirishlar ham nusxa kabi ajralib ketadi.
"""

SHIFT_STATUS_VALUES: tuple[str, ...] = tuple(s.value for s in ShiftStatus)
PAYMENT_KIND_VALUES: tuple[str, ...] = tuple(k.value for k in PaymentKind)
PAYMENT_METHOD_VALUES: tuple[str, ...] = tuple(m.value for m in PaymentMethod)
ADJUSTMENT_DIRECTION_VALUES: tuple[str, ...] = tuple(d.value for d in AdjustmentDirection)
ADJUSTMENT_REASON_VALUES: tuple[str, ...] = tuple(r.value for r in AdjustmentReason)
REVERSAL_REASON_VALUES: tuple[str, ...] = tuple(r.value for r in ReversalReason)
ANOMALY_KIND_VALUES: tuple[str, ...] = tuple(k.value for k in AnomalyKind)


def _quoted(values: tuple[str, ...]) -> str:
    """SQL literal ro'yxati. Qiymatlar `StrEnum` a'zolari — tashqi kirish emas.

    `market.py`, `identity.py`, `nvr.py`, `snapshot.py` va `occupancy.py`
    dagi jufti bilan bir xil ikki qatorli funksiya va u ATAYIN OLTINCHI
    marta takrorlanadi: umumiy modulga chiqarish `models/base.py` ning
    ommaviy yuzasini kengaytirardi, har bir chaqiruvchi esa baribir O'Z
    enum'i bilan qulflangan.
    """
    return ", ".join(f"'{value}'" for value in values)


_CLOSED: Final = ShiftStatus.CLOSED.value
_REVERSAL: Final = PaymentKind.REVERSAL.value
_NO_COVERAGE: Final = AnomalyKind.NO_COVERAGE_STALL.value
"""Uch a'zo qiymati QISQA nom ostida — ifodalar 100 belgilik chegaraga sig'sin.

Alias ATAYIN: to'liq `{AnomalyKind.NO_COVERAGE_STALL.value}` yozilgan
ifoda 100 belgidan oshib, ko'p qatorli ifodaga bo'linardi. Qiymat baribir
ENUM'DAN HOSILA — literal qo'lda yozilmaydi va a'zo qiymati o'zgarsa
uchala `CHECK` ham O'ZI yangilanadi.
"""

SHIFT_STATUS_CHECK = f"status IN ({_quoted(SHIFT_STATUS_VALUES)})"
"""`cashier_shifts.status` — `ShiftStatus` DAN HOSILA (D-27)."""

PAYMENT_KIND_CHECK = f"kind IN ({_quoted(PAYMENT_KIND_VALUES)})"
"""`payments.kind` — `PaymentKind` DAN HOSILA (D-23)."""

PAYMENT_METHOD_CHECK = f"method IN ({_quoted(PAYMENT_METHOD_VALUES)})"
"""`payments.method` — `PaymentMethod` DAN HOSILA (CASH-01).

⛔ UCHINCHI TUR (`transfer`) YO'Q va bu enum'ning O'Z docstringida
sabablangan: referenssiz «o'tkazma» nizoda hech qanday dalil
qoldirmaydigan to'lov turi bo'lardi.
"""

ADJUSTMENT_DIRECTION_CHECK = f"direction IN ({_quoted(ADJUSTMENT_DIRECTION_VALUES)})"
"""`charge_adjustments.direction` — `AdjustmentDirection` DAN HOSILA (C-5)."""

ADJUSTMENT_REASON_CHECK = f"reason_code IN ({_quoted(ADJUSTMENT_REASON_VALUES)})"
"""`charge_adjustments.reason_code` — `AdjustmentReason` DAN HOSILA (D-19).

⛔ `other` A'ZOSI YO'Q va bu ro'yxatning butun qiymati (sabab
`enums.py::AdjustmentReason` docstringida): bitta bo'sh maydon har qanday
summa o'zgartirishini oqlab yuborardi va hisobotda «boshqa» AMALDA eng
katta guruh bo'lib qolardi.
"""

REVERSAL_REASON_CHECK = f"reversal_reason IN ({_quoted(REVERSAL_REASON_VALUES)})"
"""`payments.reversal_reason` — `ReversalReason` DAN HOSILA (D-19/D-23).

⚠ Ustun NULLABLE va bu `CHECK` uni MAJBURLAMAYDI: `NULL IN (...)` `NULL`
beradi, `CHECK` esa `NULL` ni O'TKAZADI. Majburiyat AYRIM konstraytda —
`REVERSAL_REASON_IS_PAIRED_CHECK` (ikki tomonlama tenglik).
"""

OVERRIDE_REASON_CHECK = f"override_reason IN ({_quoted(ADJUSTMENT_REASON_VALUES)})"
"""`payments.override_reason` — `AdjustmentReason` DAN HOSILA (D-19).

⚠ ATAYIN `AdjustmentReason`, YANGI ENUM EMAS: «nega server bergan summadan
chetlandik?» va «nega hisob tuzatildi?» — BIR XIL sabablar to'plami
(`late_review`, `partial_day`, `director_waiver` va h.k.). Ikkinchi enum
ikki ro'yxatni ajralib ketadigan qilardi va hisobotda bitta sabab ikki
xil kalit bilan chiqardi.
"""

ANOMALY_KIND_CHECK = f"kind IN ({_quoted(ANOMALY_KIND_VALUES)})"
"""`billing_anomalies.kind` — `AnomalyKind` DAN HOSILA (C-12)."""

SHIFT_CLOSED_IS_PAIRED_CHECK = f"(status = '{_CLOSED}') = (closed_at IS NOT NULL)"
"""Smena YOPILGAN bo'lsa yopilish vaqti BOR, aks holda YO'Q (D-25).

Ikki tomonlama tenglik (`=`, `->` EMAS) IKKALA nosozlikni ham yopadi:
`closed`, lekin `closed_at IS NULL` -> smena qachon yopilgani noma'lum;
`open`, lekin `closed_at` to'ldirilgan -> «yopilgan, lekin hamon ochiq»
qatori variance hisobotini ikki xil javobga bo'lardi.
"""

SHIFT_CLOSED_HAS_DECLARATION_CHECK = f"(status = '{_CLOSED}') = (declared_soum IS NOT NULL)"
"""KO'R DEKLARATSIYA — smena yopilishining SHARTI (D-25, CASH-04).

Deklaratsiyasiz yopilgan smena variance ni umuman hisoblab bo'lmaydigan
qilardi: `variance()` ikki sonni talab qiladi va biri yo'q bo'lsa natija
«nomuvofiqlik yo'q» bilan BIR XIL ko'rinardi — ya'ni nazoratning yo'qligi
yaxshi natijaga aylanardi.
"""

SHIFT_CLOSED_HAS_SYSTEM_TOTAL_CHECK = f"(status = '{_CLOSED}') = (system_soum IS NOT NULL)"
"""Tizim summasi ham yopilish paytida MUZLATILADI (D-25).

⚠ Saqlanishining sababi: `payments` keyin ham o'zgaradi (storno YANGI
qator), ya'ni «smena yopilganda tizim qancha ko'rsatgan edi?» savoliga
javob keyin qayta hisoblansa BOSHQA son berardi va ko'r deklaratsiya
bilan solishtiruv ma'nosini yo'qotardi.
"""

REVERSAL_IS_PAIRED_CHECK = f"(kind = '{_REVERSAL}') = (reverses_payment_id IS NOT NULL)"
"""Storno ASL QATORNI ko'rsatadi, oddiy to'lov esa KO'RSATMAYDI (D-23).

Ikki tomonlama: «storno, lekin nimani bekor qilgani noma'lum» ham,
«oddiy to'lov, lekin nimanidir bekor qilyapti» ham IFODALAB BO'LMAYDI.
"""

REVERSAL_REASON_IS_PAIRED_CHECK = f"(kind = '{_REVERSAL}') = (reversal_reason IS NOT NULL)"
"""Storno SABAB-KOD talab qiladi, oddiy to'lov uni KO'TARMAYDI (D-19/D-23).

Nizoda ikkala yozuv ham ko'rinadi — «to'ladi» va «bekor qilindi, sababi
shu» (D-02). Sababsiz storno esa «pul kelmagan» da'vosini hech narsa
bilan izohlamasdi.
"""

REVERSAL_HAS_NO_OVERRIDE_CHECK = f"kind <> '{_REVERSAL}' OR override_reason IS NULL"
"""Storno qatorida `override_reason` BO'LMAYDI.

Storno asl to'lovning KATTALIGINI qaytaradi, ya'ni «server bergan
summadan chetlanish» tushunchasi unga umuman tegishli emas. Ikkala sabab
maydonining bir qatorda bo'lishi «qaysi biri hisobotga tushadi?» savolini
javobsiz qoldirardi.
"""

NO_COVERAGE_ANOMALY_IS_PAIRED_CHECK = f"(kind = '{_NO_COVERAGE}') = (occupancy_event_id IS NULL)"
"""C-12 — DALILSIZ ANOMALIYA HAM, DALILLI QAMROVSIZLIK HAM YO'Q.

`models/occupancy.py::NO_COVERAGE_IS_PAIRED_CHECK` ning aynan takrori va
bir xil sinf da'vo. Ikki tomonlama tenglik ikki nosozlikni yopadi:

  * `unassigned_occupied`, lekin hodisa YO'Q -> «band, lekin to'lovsiz»
    da'vosi RASM-DALILSIZ qolardi va u aynan mahsulotning yagona
    qiymati (`PROJECT.md` Core Value);
  * `no_coverage_stall`, lekin hodisa BOR -> «ko'ra olmadik» degan
    da'vo ko'rilgan kadr bilan birga kelardi, ya'ni u YOLG'ON bo'lardi.
"""

OVERRIDE_IS_PAIRED_CHECK = "(amount_soum = quote_soum) = (override_reason IS NULL)"
"""D-19 / CASH-02 — SERVER BERGAN SUMMADAN HAR QANDAY CHETLANISH SABAB TALAB QILADI.

⛔ BU KONSTRAYT D-19 NI ILOVA QATLAMIDAN SXEMAGA KO'CHIRADI va bu
o'lchov: «422 `reason_required`» tekshiruvi FAQAT HTTP yo'lini
qo'riqlaydi, xom SQL (migratsiya, import skripti, `psql`) esa uni
BUTUNLAY chetlab o'tardi — `migrations/entities/triggers.py:4-20` da
o'lchangan sinf.

Ikki tomonlama tenglik ikkala nosozlikni ham yopadi: SABABSIZ
o'zgartirish ham, O'ZGARISHSIZ sabab ham IFODALAB BO'LMAYDI.

⚠ QISMAN TO'LOV BU BILAN TAQIQLANMAYDI (OQ-4): kassir kichik summa
kiritsa qator `override_reason` bilan keladi, ya'ni sabab YOZILADI.
⛔ `CHECK (amount_soum = tariff_amount_soum)` shaklidagi shart YOZILMAYDI —
u qisman to'lovni umuman imkonsiz qilardi.
"""

ANOMALY_EVIDENCE_IS_PAIRED_CHECK = "(occupancy_event_id IS NULL) = (snapshot_id IS NULL)"
"""Hodisa va kadr JUFTLIKDA keladi (D-29).

Hodisasiz kadr «qaysi zona?» savolini javobsiz qoldirardi; kadrsiz hodisa
esa nazoratchiga KO'RSATADIGAN rasm bermasdi — ikkalasi ham dalil
zanjirining yarmi.
"""

SERVICE_DATE_NOT_IN_FUTURE_CHECK = "service_date <= business_date"
"""KELAJAK KUNI UCHUN HISOB YOZIB BO'LMAYDI (D-06).

`business_date` `created_at` dan hosila, ya'ni u HAR DOIM «bugun». Shart
`service_date` ni o'tmish va bugun bilan cheklaydi: kelajakka yozilgan
hisob qarz hisobotida bugundan boshlab ko'rinardi va sotuvchi hali
bo'lmagan kun uchun qarzdor bo'lib qolardi.
"""


# ===========================================================================
# INDEKS NOMLARI VA PREDIKATLAR — MODEL VA MIGRATSIYA UCHUN YAGONA MANBA
# ===========================================================================
#
# ⚠ NEGA INDEKSLAR MODELDA HAM E'LON QILINADI (o'lchangan, 03-03 va
# `models/occupancy.py:350-358`): `op.create_index(...)` yolg'iz o'zi
# yetarli EMAS. Alembic autogenerate model metadata'sini baza bilan
# solishtiradi va modelda e'lon qilinmagan indeksni "o'chirilgan" deb
# hisoblaydi — `test_autogenerate_is_empty` `remove_index` bilan QIZARADI
# (OP-10).
#
# ⚠ HAMMASI `market_id` BILAN BOSHLANADI, ya'ni `test_meta.py::
# INDEX_EXCEPTIONS` ga HECH NIMA qo'shilmaydi. Har bir so'rov HAR DOIM
# bitta bozor konteksti ostida bajariladi (P9).

DAILY_CHARGE_VENDOR_INDEX = "ix_daily_charges_market_vendor_service_date"
"""«Bu sotuvchining qarzi» — qarzdorlik reestrining issiq yo'li (BILL-03)."""

DAILY_CHARGE_DAY_INDEX = "ix_daily_charges_market_service_date_stall"
"""«Bu kunning hisoblari» — kunlik hisobot va `billing_close` idempotentligi."""

PAYMENT_VENDOR_INDEX = "ix_payments_market_vendor_service_date"
"""FIFO taqsimlashning kirishi: sotuvchining to'lovlari KUN bo'yicha (D-24)."""

PAYMENT_STALL_INDEX = "ix_payments_market_stall_service_date"
"""«Bu rastaga bugun to'landimi?» — kassirning ≤3 bosishli oqimi (CASH-01)."""

CHARGE_ADJUSTMENT_INDEX = "ix_charge_adjustments_market_charge"
"""Hisob kartochkasidagi tuzatishlar ro'yxati (UI-SPEC §11.3)."""

LATE_REVIEW_ADJUSTMENT_INDEX = "uq_charge_adjustments_market_charge_late_review"
"""BIR HISOBGA BITTA `late_review` TUZATISHI — qisman UNIQUE indeks (0022).

=============================================================================
⛔⛔ POYGA DB'GA TOPSHIRILADI, `SHIFT_OPEN_INDEX` bilan AYNAN bir xil sabab.

`late_review` tuzatishini INSON emas, `billing_close` job'i yozadi
(`app/jobs/billing_close.py`): nazoratchi D+1 kunduzida «bo'sh» degach,
job qayta yugurganda o'zgarmas hisobni BEKOR QILA OLMAYDI (D-07) va
o'rniga `direction = 'decrease'` tuzatishi yoziladi.

⚠ Job KONVERGENT, ya'ni u AYNAN o'sha kun uchun QAYTA-QAYTA yugurishi
  NORMAL holat. Idempotentlik ilova qatlamida («avval tekshir, keyin
  yoz») qilinganda ikkita parallel yugurish ikkita TO'LIQ SUMMALI
  kamaytirish yozardi va hisobning netto summasi MANFIY bo'lib qolardi —
  ya'ni himoyaning yo'qligi jimgina PUL XATOSIGA aylanardi.

⚠ QOLGAN sabab kodlari uchun bu indeks HECH NIMANI cheklamaydi va bu
  ATAYIN: `CHARGE_ADJUSTMENT_INDEX` docstringidagi «bir hisobga bir necha
  tuzatish MUTLAQO qonuniy» qoidasi kuchida qoladi — qisman indeks faqat
  TIZIM yozadigan yagona sabab kodini qamraydi.
"""

LATE_REVIEW_ADJUSTMENT_PREDICATE = f"reason_code = '{AdjustmentReason.LATE_REVIEW.value}'"
"""Qisman indeksning predikati — `AdjustmentReason` DAN HOSILA.

`SHIFT_OPEN_PREDICATE` bilan bir xil qoida: qo'lda ko'chirilgan literal
enum bilan ajralib ketganda indeks JIMGINA hech nimani qamramay qolardi
va idempotentlik konventsiyaga aylanardi.
"""

BILLING_ANOMALY_INDEX = "ix_billing_anomalies_market_service_date_kind"
"""Kunlik anomaliya hisoboti — uchala `kind` ALOHIDA sanaladi (C-12)."""

CHARGE_EVIDENCE_INDEX = "ix_charge_evidence_market_charge"
"""«Bu hisobning dalili» — rasm-dalil ko'rsatishning yagona yo'li (BILL-02)."""

SHIFT_OPEN_INDEX = "uq_cashier_shifts_market_id_cashier_open"
"""BIR KASSIRDA BIR OCHIQ SMENA — qisman UNIQUE indeks (D-27).

`models/snapshot.py::ALERT_OPEN_INDEX` naqshi va bir xil sabab:
poyga DB'GA topshiriladi, ilova qatlamida «avval tekshir, keyin yoz»
QILINMAYDI. Ikki oynadan bir vaqtda ochilgan smena aynan shu poyga
holati va uni faqat sxema to'xtata oladi.

⚠ `NULL` SENTINEL KERAK EMAS (`ALERT_OPEN_EXPR` dan FARQI): `cashier_id`
`NOT NULL`, ya'ni `COALESCE` bilan niqoblanadigan `NULL` yo'q.
"""

SHIFT_OPEN_PREDICATE = f"status = '{ShiftStatus.OPEN.value}'"
"""Ochiq smena indeksining predikati — `ShiftStatus` DAN HOSILA.

`OCCUPANCY_UNCERTAIN_PREDICATE` va `CAPTURE_DUE_PREDICATE` bilan bir xil
qoida va bir xil sabab: qo'lda ko'chirilgan literal enum bilan ajralib
ketganda indeks JIMGINA hech nimani qamramay qolardi — ya'ni ikkinchi
ochiq smena bloklanmasdi va D-27 konventsiyaga aylanardi.
"""


class CashierShift(Base, TenantMixin):
    """Kassir smenasi — ko'r deklaratsiya va tizim summasining uchrashuv nuqtasi.

    =========================================================================
    BIR KASSIRDA BIR VAQTDA AYNAN BITTA OCHIQ SMENA (D-27).

    Majburiyat QISMAN UNIQUE indeks bilan (`SHIFT_OPEN_INDEX`), ilova
    mantig'i bilan EMAS: ikki oynadan bir vaqtda ochilgan smena poyga
    holati va «avval tekshir, keyin yoz» ikkalasiga ham bo'sh holatni
    ko'rsatardi. O'shanda kassir to'lovlarni ikki smenaga bo'lib yozardi
    va variance HAR IKKALASIDA ham kichik ko'rinardi — ya'ni nomuvofiqlik
    ikkiga bo'linib YO'QOLARDI.

    DEKLARATSIYA YOZILGACH O'ZGARMAS (D-25). `0020` bu jadvalga SHARTLI
    o'zgarmaslik qo'riqchisini ulaydi (`shift_declaration_immutable()`):
    `open` -> `closed` o'tishi RUXSAT (aks holda smenani yopib bo'lmasdi),
    lekin `declared_soum`/`system_soum` bir marta yozilgach QAYTA
    YOZILMAYDI. «Qayta ochish» yo'li smenani tizim summasiga
    MOSLASHTIRISH imkonini berardi va ko'r deklaratsiya ma'nosini
    butunlay yo'qotardi.
    =========================================================================

    IKKI VAQT USTUNI VA IKKALASI HAM KERAK — C-2 NING AYNAN TAKRORI:

        opened_at   — smena QACHON OCHILDI      (DOMEN fakti)
        created_at  — qator QACHON YOZILDI      (AUDIT fakti)

    Bugun ular odatda ustma-ust tushadi, lekin direktor smenani KEYIN
    kiritsa (yoki backfill qilinsa) ular AJRALADI — va aynan shu farq
    `business_date` ni halol qiladi. `business_date` `created_at` dan
    hosila, chunki u `BILLING_BUSINESS_DATE_EXPR` ning yagona kirishi:
    ikkinchi ifoda yozish mintaqa arifmetikasining ikkinchi nusxasini
    tug'dirardi (`models/market.py:188-196`).

    JADVAL AUDIT OSTIDA (`AUDITED_TABLES`): smena ochilishi va yopilishi —
    INSONNING moliyaviy oqibatli qarori va deklaratsiya raqami nizoda
    dalil bo'ladi.

    `declared_soum = 0` RUXSAT ETILADI va bu ATAYIN: butun smena terminal
    orqali o'tgan kun REAL holat (UI-SPEC §10.2). `> 0` sharti kassirni
    soxta naqd summa yozishga majburlardi.
    """

    __tablename__ = "cashier_shifts"
    __table_args__ = (
        ForeignKeyConstraint(
            ["market_id"], ["markets.id"], name="fk_cashier_shifts_market_id_markets"
        ),
        # ⚠ `users` GA FK BOR va u `zone_reviews.reviewer_id` bilan bir xil
        #   naqsh. ⛔ `ondelete` YO'Q (NO ACTION): smenasi bor kassirni
        #   o'chirish RAD ETILADI. `CASCADE` bo'lganda bitta `DELETE FROM
        #   users` butun kassa tarixini o'chirib yuborardi.
        ForeignKeyConstraint(
            ["cashier_id"], ["users.id"], name="fk_cashier_shifts_cashier_id_users"
        ),
        # KOMPOZIT FK NISHONI: `payments.shift_id` `(market_id, shift_id)`
        # ga havola qiladi.
        UniqueConstraint("market_id", "id", name="uq_cashier_shifts_market_id_id"),
        CheckConstraint(SHIFT_STATUS_CHECK, name="status_allowed"),
        CheckConstraint(SHIFT_CLOSED_IS_PAIRED_CHECK, name="closed_is_paired"),
        CheckConstraint(SHIFT_CLOSED_HAS_DECLARATION_CHECK, name="closed_has_declaration"),
        CheckConstraint(SHIFT_CLOSED_HAS_SYSTEM_TOTAL_CHECK, name="closed_has_system_total"),
        # ⚠ `>= 0`, `> 0` EMAS — klass docstringidagi oxirgi band.
        CheckConstraint(
            "declared_soum IS NULL OR declared_soum >= 0", name="declared_soum_non_negative"
        ),
        CheckConstraint("system_soum IS NULL OR system_soum >= 0", name="system_soum_non_negative"),
        # ⚠⚠ D-27 NING BUTUN MAJBURIYATI — QISMAN UNIQUE INDEKS.
        Index(
            SHIFT_OPEN_INDEX,
            "market_id",
            "cashier_id",
            unique=True,
            postgresql_where=text(SHIFT_OPEN_PREDICATE),
        ),
    )

    id: Mapped[UUID] = uuid_pk()
    cashier_id: Mapped[UUID] = mapped_column(PgUuid(as_uuid=True), nullable=False)
    # `sbozor_core.enums.ShiftStatus` — `open` yoki `closed`.
    status: Mapped[str] = mapped_column(
        Text(), nullable=False, server_default=text(f"'{ShiftStatus.OPEN.value}'")
    )
    # DOMEN vaqti: smena qachon ochildi (klass docstringi).
    opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    # `NULL` = smena hamon ochiq (`closed_is_paired` uni MAJBURLAYDI).
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # KO'R DEKLARATSIYA (CASH-04): kassir kassadagi naqd summani tizim
    # summasini KO'RMASDAN kiritadi. Ustun `NULL` bo'lgani — smena hali
    # ochiq degani, «kassir kiritmadi» degani EMAS.
    declared_soum: Mapped[int | None] = mapped_column(BigInteger(), nullable=True)
    # Tizim hisoblagan naqd summa — yopilish paytida MUZLATILADI
    # (`SHIFT_CLOSED_HAS_SYSTEM_TOTAL_CHECK` docstringi).
    system_soum: Mapped[int | None] = mapped_column(BigInteger(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    # AUDIT sanasi — qator QAYSI biznes-kunda yozildi (klass docstringi).
    business_date: Mapped[date] = mapped_column(
        Date(), Computed(BILLING_BUSINESS_DATE_EXPR, persisted=True), nullable=False
    )


class DailyCharge(Base, TenantMixin):
    """Kunlik patta hisobi — «band, lekin to'lovsiz» da'vosining PUL tomoni.

    =========================================================================
    IKKINCHI HISOB YOZIB BO'LMAYDI: `UNIQUE (market_id, stall_id, service_date)`.

    ⛔ KALIT `service_date` USTIDA, `business_date` USTIDA EMAS (C-2/D-06).
    Kun 04:10 da yopiladi, ya'ni hisob HISOBLANAYOTGAN kundan KEYINGI
    kunda yoziladi. Kalit `business_date` ustida bo'lsa kunni QAYTA yopish
    (yoki backfill) IKKINCHI hisob yaratardi va sotuvchi bir kun uchun ikki
    marta qarzdor bo'lardi. `financial_guards()` aynan shunday kalit beradi
    — shuning uchun u BU YERDA CHAQIRILMAYDI va uchala qo'riqchi QO'LDA
    yoziladi (`0008_temporal.py:164-182` presedenti, `tariffs` aynan shu
    muammoni shunday hal qilgan).

    QATOR YOZILGACH O'ZGARMAS (D-07). `0020` unga SHARTSIZ `BEFORE UPDATE
    OR DELETE` qo'riqchisini (`charge_immutable()`) ulaydi: tahrir ham,
    o'chirish ham RAD ETILADI. Tuzatish YANGI QATOR bo'ladi
    (`charge_adjustments`), ya'ni asl summa nizoda ko'rinib qoladi (D-02).
    =========================================================================

    `vendor_id` `NOT NULL` VA U MUZLATILGAN NUSXA (D-28). Sotuvchisiz
    rastaga hisob YOZILMAYDI — u `billing_anomalies.unassigned_occupied`
    bo'ladi. `vendor_id NULL` bilan hisob yozish «kimdir qarzdor, lekin kim
    ekani noma'lum» yozuvini tug'dirardi va qarz hisoboti uni HECH KIMGA
    biriktira olmasdi. Biriktirish davri keyin ko'chsa ham bu qator o'z
    sotuvchisini ESLAB QOLADI.

    `tariff_id` HAM, SUMMA HAM SAQLANADI (D-09). Faqat `tariff_id` yozish
    yetarli emas: `tariffs` tahrirlansa (yoki yangi `valid_from` qo'shilsa)
    o'tmishdagi hisob RETROAKTIV o'zgarardi. Faqat summani yozish ham
    yetarli emas: «qaysi tarif bo'yicha?» savoli javobsiz qolardi.
    `tariff_amount_soum` — tarif BERGAN summa, `amount_soum` esa AMALDA
    yozilgan summa; ikkalasi `charge_adjustments` gacha teng bo'ladi.

    JADVAL AUDIT TRIGGERIDAN CHIQARILGAN — ikki mustaqil sabab:
      (a) O'ZGARMASLIK: qator shartsiz o'zgarmas, ya'ni audit faqat
          `INSERT` ni ko'rardi va bu o'sha ma'lumotning IKKINCHI NUSXASI
          bo'lardi (`occupancy_events` bilan aynan bir xil dalil);
      (b) HAJM: ~300–1000 rasta/kun/bozor — `audit_log` append-only.
    Iz yo'qolmaydi: tuzatishlar `charge_adjustments` da va U auditda.
    """

    __tablename__ = "daily_charges"
    __table_args__ = (
        ForeignKeyConstraint(
            ["market_id"], ["markets.id"], name="fk_daily_charges_market_id_markets"
        ),
        ForeignKeyConstraint(
            ["market_id", "stall_id"],
            ["stalls.market_id", "stalls.id"],
            name="fk_daily_charges_market_id_stall_id_stalls",
        ),
        ForeignKeyConstraint(
            ["market_id", "vendor_id"],
            ["vendors.market_id", "vendors.id"],
            name="fk_daily_charges_market_id_vendor_id_vendors",
        ),
        ForeignKeyConstraint(
            ["market_id", "tariff_id"],
            ["tariffs.market_id", "tariffs.id"],
            name="fk_daily_charges_market_id_tariff_id_tariffs",
        ),
        # ⚠⚠ D-06 NING IDEMPOTENTLIK KALITI (klass docstringidagi birinchi
        #   blok). Nom `test_meta.py::test_financial_tables_have_guards`
        #   ning uchinchi shartini ham bajaradi: `conkey[1] = market_id`.
        UniqueConstraint(
            "market_id",
            "stall_id",
            "service_date",
            name="uq_daily_charges_market_id_stall_id_service_date",
        ),
        # KOMPOZIT FK NISHONI: `charge_adjustments` va `charge_evidence`
        # `(market_id, charge_id)` ga havola qiladi.
        UniqueConstraint("market_id", "id", name="uq_daily_charges_market_id_id"),
        # ⛔ USTUN NOMI AYNAN `amount_soum` — `test_meta.py:1341-1347`
        #   regeksi (`amount_soum\\s*>\\s*0`) SHU nomni izlaydi. `delta_soum`
        #   yoki `total_soum` darvozani qizartirardi.
        CheckConstraint("amount_soum > 0", name="amount_soum_positive"),
        CheckConstraint("tariff_amount_soum > 0", name="tariff_amount_soum_positive"),
        CheckConstraint(SERVICE_DATE_NOT_IN_FUTURE_CHECK, name="service_date_not_in_future"),
        Index(DAILY_CHARGE_VENDOR_INDEX, "market_id", "vendor_id", "service_date"),
        Index(DAILY_CHARGE_DAY_INDEX, "market_id", "service_date", "stall_id"),
    )

    id: Mapped[UUID] = uuid_pk()
    stall_id: Mapped[UUID] = mapped_column(PgUuid(as_uuid=True), nullable=False)
    # MUZLATILGAN NUSXA (D-28) — klass docstringi.
    vendor_id: Mapped[UUID] = mapped_column(PgUuid(as_uuid=True), nullable=False)
    # DOMEN sanasi: hisob QAYSI KUN uchun yozildi. `business_date` bilan
    # ARALASHTIRILMAYDI — ikkalasi ikki xil savolga javob beradi (C-2).
    service_date: Mapped[date] = mapped_column(Date(), nullable=False)
    tariff_id: Mapped[UUID] = mapped_column(PgUuid(as_uuid=True), nullable=False)
    # Tarif BERGAN summa — retroaktiv o'zgarishdan himoya (D-09).
    tariff_amount_soum: Mapped[int] = mapped_column(BigInteger(), nullable=False)
    # AMALDA yozilgan summa. `bigint` so'm; kasrli tip TAQIQLANGAN (D-11).
    amount_soum: Mapped[int] = mapped_column(BigInteger(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    # AUDIT sanasi — qator QAYSI biznes-kunda yozildi (C-2).
    business_date: Mapped[date] = mapped_column(
        Date(), Computed(BILLING_BUSINESS_DATE_EXPR, persisted=True), nullable=False
    )


class ChargeAdjustment(Base, TenantMixin):
    """Hisob tuzatishi — ALOHIDA QATOR, `daily_charges` ning TAHRIRI EMAS (D-07).

    =========================================================================
    NEGA `INSERT`, NEGA `UPDATE` EMAS.

    Yozilgan hisobni joyida tahrirlash asl summani O'CHIRARDI — ya'ni
    nizoda «qancha talab qilingan edi?» savoliga javob beradigan yagona
    ma'lumot yo'qolardi. Yakuniy summa esa HISOBLANADIGAN KO'RINISH:
    `amount_soum + Σ(increase) - Σ(decrease)` (2-fazadagi «qoldiq har doim
    hisoblanadigan ko'rinish» qoidasining takrori).

    ⛔ MANFIY SUMMA YOZILMAYDI (C-5): `amount_soum` MUSBAT KATTALIK,
    yo'nalish esa ALOHIDA ustunda. Belgili `bigint` da «-15000» ni yozgan
    odam «15000 qaytarildi» ni ham, «15000 kamaytirildi» ni ham nazarda
    tutgan bo'lishi mumkin va hisobot ikkalasini bir guruhga qo'shardi.
    =========================================================================

    JADVAL AUDIT OSTIDA (`AUDITED_TABLES`): tuzatish — INSONNING moliyaviy
    oqibatli qarori va u `tariffs` / `zone_reviews` bilan BIR OILADA.
    Aynan shuning uchun `AuditAction` ga `charge_adjust` a'zosi
    QO'SHILMAYDI: DB-trigger qatorni O'ZI yozadi va app darajasidagi audit
    DUBLIKAT bo'lardi (`enums.py::AuditAction` docstringi).

    `reason_code` YOPIQ RO'YXATDAN (D-19) va unda `other` YO'Q — sabab
    `enums.py::AdjustmentReason` docstringida.
    """

    __tablename__ = "charge_adjustments"
    __table_args__ = (
        ForeignKeyConstraint(
            ["market_id"], ["markets.id"], name="fk_charge_adjustments_market_id_markets"
        ),
        ForeignKeyConstraint(
            ["market_id", "charge_id"],
            ["daily_charges.market_id", "daily_charges.id"],
            name="fk_charge_adjustments_charge",
        ),
        # ⛔ `ondelete` YO'Q — `CashierShift.cashier_id` bilan bir xil sabab.
        ForeignKeyConstraint(
            ["actor_user_id"], ["users.id"], name="fk_charge_adjustments_actor_user_id_users"
        ),
        # ⚠ `test_financial_tables_have_guards` ning uchinchi sharti
        #   (`conkey[1] = market_id`) AYNAN shu konstrayt bilan bajariladi:
        #   bu jadval `FINANCIAL_TABLES` da (1-fazadan) va unda tabiiy
        #   idempotentlik kaliti YO'Q — bir hisobga bir necha tuzatish
        #   yozilishi MUTLAQO qonuniy.
        UniqueConstraint("market_id", "id", name="uq_charge_adjustments_market_id_id"),
        CheckConstraint(ADJUSTMENT_DIRECTION_CHECK, name="direction_allowed"),
        CheckConstraint(ADJUSTMENT_REASON_CHECK, name="reason_code_allowed"),
        CheckConstraint("amount_soum > 0", name="amount_soum_positive"),
        Index(CHARGE_ADJUSTMENT_INDEX, "market_id", "charge_id"),
        # ⚠⚠ TIZIM YOZADIGAN YAGONA SABAB KODI UCHUN QISMAN UNIQUE INDEKS
        #   (`LATE_REVIEW_ADJUSTMENT_INDEX` docstringi). Qolgan sabab
        #   kodlari uchun bir hisobga bir necha tuzatish qonuniy bo'lib
        #   QOLADI — indeks ularni umuman qamramaydi.
        Index(
            LATE_REVIEW_ADJUSTMENT_INDEX,
            "market_id",
            "charge_id",
            unique=True,
            postgresql_where=text(LATE_REVIEW_ADJUSTMENT_PREDICATE),
        ),
    )

    id: Mapped[UUID] = uuid_pk()
    charge_id: Mapped[UUID] = mapped_column(PgUuid(as_uuid=True), nullable=False)
    # `sbozor_core.enums.AdjustmentDirection` — `increase` / `decrease`.
    direction: Mapped[str] = mapped_column(Text(), nullable=False)
    # `sbozor_core.enums.AdjustmentReason` — YOPIQ ro'yxat (D-19).
    reason_code: Mapped[str] = mapped_column(Text(), nullable=False)
    # MUSBAT KATTALIK (C-5). `bigint` so'm.
    amount_soum: Mapped[int] = mapped_column(BigInteger(), nullable=False)
    # Kim tuzatdi — nizoda «kim qaror qildi?» savolining javobi (D-02).
    #
    # ⛔ `NULL` = TIZIM, va u YO'Q JAVOB EMAS (0022 da NOT NULL bo'shatildi).
    #   `late_review` tuzatishini `billing_close` job'i yozadi: nazoratchi
    #   kechikkan javobi hisobni o'zgarmas qoldiradi (D-07) va kamaytirish
    #   ALOHIDA qator bo'lib tug'iladi. O'sha qatorga birorta odamning
    #   `user_id` sini yozish YOLG'ON bo'lardi — «kim qaror qildi?»
    #   savoliga noto'g'ri odamni ko'rsatgan javob javobning YO'QLIGIDAN
    #   yomonroq (nizoda u aynan dalil sifatida o'qiladi).
    #
    # ⚠ NAQSH `ops.py::AuditLog.actor_user_id` DAN: u ham `nullable` va
    #   sabab AYNAN bir xil — fon jobi `actor_kind = 'system'` bilan
    #   ishlaydi va uning `app.actor_id` GUC'i bo'sh.
    actor_user_id: Mapped[UUID | None] = mapped_column(PgUuid(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    business_date: Mapped[date] = mapped_column(
        Date(), Computed(BILLING_BUSINESS_DATE_EXPR, persisted=True), nullable=False
    )


class ChargeEvidence(Base, TenantMixin):
    """Hisobning RASM-DALILI — mahsulotning yagona qiymatining tayanchi (BILL-02).

    =========================================================================
    MUZLATILGAN POINTER — `occupancy_event_id`, `stall_slot_occupancy_id` EMAS (C-7).

    `stall_slot_occupancy` MUTABLE: kunlik job uni `ON CONFLICT DO UPDATE`
    bilan qayta hisoblaydi (`occupancy_repo.py:341-361`). Ya'ni o'sha
    qatorning `id` si BUGUN «band» ni, ERTAGA esa «bo'sh» ni ko'rsatishi
    mumkin — bunday havola nizoda DALIL bo'la olmaydi.

    `occupancy_events` esa `0018` bilan SHARTSIZ o'zgarmas
    (`occupancy_event_immutable()`), ya'ni u YAGONA halol langar. Zanjir
    to'liq:

        charge_evidence -> occupancy_events -> snapshots (id, is_billable)

    va uning oxirgi halqasi D-21 ning billing langari, ya'ni YAROQSIZ
    kadr bu zanjirga umuman kira olmaydi.

    `stall_slot_occupancy_id` BARIBIR SAQLANADI va u AUDIT HAVOLASI:
    «kun yopilishida qaysi agregat qator hisobga sabab bo'ldi». U dalil
    EMAS va hech qachon dalil sifatida ishlatilmaydi.

    `snapshot_id` — KADRGA YO'L. U `occupancy_events` dan hosila bo'lishi
    mumkin edi, lekin nusxa ATAYIN: rasm-dalilni ko'rsatish uchun bitta
    `JOIN` kamayadi va dalil qatori kadrni NOMMA-NOM biladi.
    =========================================================================

    `business_date` USTUNI YO'Q va bu ATAYIN. Dalil qatori KUNNI
    `daily_charges` dan meros qiladi (`charge_id`), ikkinchi hosila sana
    esa yarim tunda bir kun farq qilishi mumkin bo'lardi (Pitfall 3) —
    o'shanda o'sha hisobning dalili hisobotda «yo'q» bo'lib qolardi.
    `slot_time` esa `stall_slot_occupancy` DAN NUSXALANADI, mustaqil
    hisoblanmaydi — u qaysi slot hisobga sabab bo'lganini aytadi.

    JADVAL AUDIT TRIGGERIDAN CHIQARILGAN: u `daily_charges` ning
    muzlatilgan nusxasi va o'zi ham hech qachon tahrirlanmaydi.
    """

    __tablename__ = "charge_evidence"
    __table_args__ = (
        ForeignKeyConstraint(
            ["market_id"], ["markets.id"], name="fk_charge_evidence_market_id_markets"
        ),
        ForeignKeyConstraint(
            ["market_id", "charge_id"],
            ["daily_charges.market_id", "daily_charges.id"],
            name="fk_charge_evidence_charge",
        ),
        # ⚠ NOM QISQARTIRILGAN va bu O'LCHANGAN zaruriyat: konvensiya nomi
        #   (`fk_charge_evidence_market_id_stall_slot_occupancy_id_stall_
        #   slot_occupancy`) 73 baytdan oshardi, PostgreSQL esa
        #   identifikatorni 63 baytga JIMGINA kesadi — SQLAlchemy buni
        #   `IdentifierError` bilan OLDINDAN to'xtatadi
        #   (`models/occupancy.py:997-1002` dagi holat).
        #
        #   ⛔ NISHON `0020` NING BIRINCHI QADAMIDA TUG'ILADI (OP-11):
        #   `stall_slot_occupancy` da `UNIQUE (market_id, id)` BUGUNGACHA
        #   YO'Q edi va usiz bu FK `InvalidForeignKeyError` berardi.
        ForeignKeyConstraint(
            ["market_id", "stall_slot_occupancy_id"],
            ["stall_slot_occupancy.market_id", "stall_slot_occupancy.id"],
            name="fk_charge_evidence_stall_slot_occupancy",
        ),
        # ⚠⚠ MUZLATILGAN DALIL (klass docstringi).
        ForeignKeyConstraint(
            ["market_id", "occupancy_event_id"],
            ["occupancy_events.market_id", "occupancy_events.id"],
            name="fk_charge_evidence_occupancy_event",
        ),
        ForeignKeyConstraint(
            ["market_id", "snapshot_id"],
            ["snapshots.market_id", "snapshots.id"],
            name="fk_charge_evidence_snapshot",
        ),
        # BIR HISOBGA BIR SLOTDAN BITTA DALIL. Dublikat qator hisobotda
        # bitta kadrni ikki marta ko'rsatardi va «nechta slotda band edi?»
        # sanog'ini shishirardi.
        # ⚠ NOM QISQARTIRILGAN (yuqoridagi 63-bayt sababi).
        UniqueConstraint(
            "market_id",
            "charge_id",
            "stall_slot_occupancy_id",
            name="uq_charge_evidence_market_charge_slot",
        ),
        UniqueConstraint("market_id", "id", name="uq_charge_evidence_market_id_id"),
        Index(CHARGE_EVIDENCE_INDEX, "market_id", "charge_id"),
    )

    id: Mapped[UUID] = uuid_pk()
    charge_id: Mapped[UUID] = mapped_column(PgUuid(as_uuid=True), nullable=False)
    # AUDIT HAVOLASI — dalil EMAS (klass docstringi).
    stall_slot_occupancy_id: Mapped[UUID] = mapped_column(PgUuid(as_uuid=True), nullable=False)
    # ⚠⚠ MUZLATILGAN DALIL: `occupancy_events` SHARTSIZ o'zgarmas (C-7).
    occupancy_event_id: Mapped[UUID] = mapped_column(PgUuid(as_uuid=True), nullable=False)
    # KADRGA YO'L — rasm-dalilni ko'rsatishning yagona manzili (BILL-02).
    snapshot_id: Mapped[UUID] = mapped_column(PgUuid(as_uuid=True), nullable=False)
    # `stall_slot_occupancy` DAN NUSXALANADI — mustaqil hisoblanmaydi.
    slot_time: Mapped[time] = mapped_column(Time(timezone=False), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Payment(Base, TenantMixin):
    """Kassir yozgan to'lov — APPEND-ONLY, SOTUVCHI DARAJASIDAGI KREDIT.

    =========================================================================
    ⛔ D-24 — TO'LOV `charge_id` GA BOG'LANMAYDI (C-3: hisob to'lovdan
    keyin tug'iladi; §9.6: bir to'lov N kunni yopadi). Kun kesimi hosila
    qoida bilan olinadi — `sbozor_core.billing.allocate_charge_credit()`,
    `FIFO_OLDEST_SERVICE_DATE_FIRST`. ⛔ Taqsimlash SAQLANMAYDI:
    `payment_allocations` jadvali ham, `allocated_*` ustuni ham YO'Q —
    D-07 va BILL-03 buni taqiqlaydi.
    =========================================================================

    QATOR YOZILGACH O'ZGARMAS (D-23). `0020` unga SHARTSIZ `BEFORE UPDATE
    OR DELETE` qo'riqchisini (`payment_immutable()`) ulaydi. Xato yozuv
    STORNO qatori bilan qoplanadi va u `reverses_payment_id` orqali asl
    qatorga bog'lanadi. Nizoda IKKALA yozuv ham ko'rinadi — «to'ladi» va
    «bekor qilindi, sababi shu» (D-02). To'lovni o'chirish esa «pul
    kelmagan» da'vosini IZSIZ qoldirardi (T-06-16).

    ⛔ EKRANDA «STORNO» SO'ZI ISHLATILMAYDI (§13.1): kassir qilayotgan
    ishning nomi «bekor qilish». Kod nomi `reversal` bo'lib QOLADI —
    atama ajralishi ATAYIN va u reyestrga olingan.

    `quote_soum` — SERVER BERGAN SUMMA (D-20) va u D-19 ni STRUKTURAVIY
    qiladi. Sabab O'LCHOV sifatida: D-19 ni ilova qatlamida («422
    `reason_required`») qoldirish `CHECK` bilan qulflashdan KUCHSIZ — xom
    SQL yo'li ilova validatsiyasini butunlay chetlab o'tadi
    (`migrations/entities/triggers.py:4-20`). `quote_soum` server bergan
    summani QATORDA saqlaydi, `OVERRIDE_IS_PAIRED_CHECK` esa har qanday
    chetlanishdan sabab-kod TALAB QILADI.

    `shift_id` NULLABLE va bu ATAYIN (OQ-6/A5): direktor smenasiz to'lov
    kiritishi mumkin (masalan kassir kasal bo'lgan kun). `NOT NULL` qilish
    o'sha holatda soxta smena ochishga majburlardi va variance hisoboti
    hech qachon yopilmaydigan qator bilan ifloslanardi.

    JADVAL AUDIT TRIGGERIDAN CHIQARILGAN — ikki mustaqil sabab:
      (a) jadval APPEND-ONLY, ya'ni audit faqat `INSERT` ni ko'rardi va bu
          o'sha ma'lumotning IKKINCHI NUSXASI bo'lardi;
      (b) HAJM: ~300–1000 qator/kun/bozor.
    ⛔ IZ YO'QOLMAYDI va bu shu qarorning SHARTI: u `payments` ning
    O'ZIDA yashaydi (`kind`, `reverses_payment_id`, `reversal_reason`,
    `override_reason`, `cashier_id`). Ilova darajasidagi audit esa
    `AuditAction.PAYMENT_OVERRIDE` / `PAYMENT_REVERSE` bilan yoziladi
    (06-09) — aynan shuning uchun `enums.py` o'sha ikki a'zoni qo'shgan.
    """

    __tablename__ = "payments"
    __table_args__ = (
        ForeignKeyConstraint(["market_id"], ["markets.id"], name="fk_payments_market_id_markets"),
        ForeignKeyConstraint(
            ["market_id", "stall_id"],
            ["stalls.market_id", "stalls.id"],
            name="fk_payments_market_id_stall_id_stalls",
        ),
        # MUZLATILGAN NUSXA — `daily_charges.vendor_id` bilan bir xil qaror
        # (D-28): biriktirish davri keyin ko'chsa ham to'lov o'z
        # sotuvchisini eslab qoladi.
        ForeignKeyConstraint(
            ["market_id", "vendor_id"],
            ["vendors.market_id", "vendors.id"],
            name="fk_payments_market_id_vendor_id_vendors",
        ),
        # O'ZIGA HAVOLA: storno asl to'lovni ko'rsatadi (D-23).
        ForeignKeyConstraint(
            ["market_id", "reverses_payment_id"],
            ["payments.market_id", "payments.id"],
            name="fk_payments_reverses_payment",
        ),
        ForeignKeyConstraint(
            ["market_id", "shift_id"],
            ["cashier_shifts.market_id", "cashier_shifts.id"],
            name="fk_payments_cashier_shift",
        ),
        # ⛔ `ondelete` YO'Q — kassiri bor to'lovni yetim qoldirib bo'lmaydi.
        ForeignKeyConstraint(["cashier_id"], ["users.id"], name="fk_payments_cashier_id_users"),
        # ⚠⚠ D-21 NING IDEMPOTENTLIK KALITI. Takror so'rov (tarmoq uzildi,
        #   kassir ikki marta bosdi) IKKINCHI to'lov yaratmaydi — u O'SHA
        #   qatorni qaytaradi. Poyga DB'GA topshirilgan va shakl 06-01 ning
        #   A1 zondi bilan HAQIQIY `postgres:18.4` da o'lchangan
        #   (`IDEMPOTENT_GET_OR_CREATE_SUPPORTED = True`).
        UniqueConstraint(
            "market_id", "idempotency_key", name="uq_payments_market_id_idempotency_key"
        ),
        UniqueConstraint("market_id", "id", name="uq_payments_market_id_id"),
        CheckConstraint(PAYMENT_KIND_CHECK, name="kind_allowed"),
        CheckConstraint(PAYMENT_METHOD_CHECK, name="method_allowed"),
        CheckConstraint(REVERSAL_REASON_CHECK, name="reversal_reason_allowed"),
        CheckConstraint(OVERRIDE_REASON_CHECK, name="override_reason_allowed"),
        # ⛔ USTUN NOMI AYNAN `amount_soum` (`DailyCharge` dagi bilan bir
        #   xil sabab: `test_meta.py:1341-1347` regeksi).
        CheckConstraint("amount_soum > 0", name="amount_soum_positive"),
        CheckConstraint("quote_soum > 0", name="quote_soum_positive"),
        CheckConstraint(REVERSAL_IS_PAIRED_CHECK, name="reversal_is_paired"),
        CheckConstraint(REVERSAL_REASON_IS_PAIRED_CHECK, name="reversal_reason_is_paired"),
        CheckConstraint(OVERRIDE_IS_PAIRED_CHECK, name="override_is_paired"),
        CheckConstraint(REVERSAL_HAS_NO_OVERRIDE_CHECK, name="reversal_has_no_override"),
        Index(PAYMENT_VENDOR_INDEX, "market_id", "vendor_id", "service_date"),
        Index(PAYMENT_STALL_INDEX, "market_id", "stall_id", "service_date"),
    )

    id: Mapped[UUID] = uuid_pk()
    stall_id: Mapped[UUID] = mapped_column(PgUuid(as_uuid=True), nullable=False)
    vendor_id: Mapped[UUID] = mapped_column(PgUuid(as_uuid=True), nullable=False)
    # ⚠ USTUNNING O'Z CHEGARASI: u «to'lov QAYSI KUN UCHUN kiritildi» ni
    #   yozadi, «qaysi kunning pattasi YOPILDI» ni EMAS. Ikkinchisi
    #   `allocate_charge_credit()` qoidasidan chiqadi va HECH QAYERDA
    #   saqlanmaydi (D-24) — `[Qarzni ham olish]` (§9.6) da bitta to'lov
    #   bugungi tarifni VA eski qarzni yopadi, `service_date` esa BUGUN
    #   bo'lib qoladi.
    service_date: Mapped[date] = mapped_column(Date(), nullable=False)
    # AMALDA olingan summa. `bigint` so'm; kasrli tip TAQIQLANGAN (D-11).
    amount_soum: Mapped[int] = mapped_column(BigInteger(), nullable=False)
    # SERVER BERGAN summa (D-20) — klass docstringi.
    quote_soum: Mapped[int] = mapped_column(BigInteger(), nullable=False)
    # `sbozor_core.enums.PaymentKind` — `payment` / `reversal`.
    kind: Mapped[str] = mapped_column(
        Text(), nullable=False, server_default=text(f"'{PaymentKind.PAYMENT.value}'")
    )
    # `sbozor_core.enums.PaymentMethod` — `cash` / `terminal`.
    method: Mapped[str] = mapped_column(Text(), nullable=False)
    # `NULL` = oddiy to'lov (`reversal_is_paired` MAJBURLAYDI).
    reverses_payment_id: Mapped[UUID | None] = mapped_column(PgUuid(as_uuid=True), nullable=True)
    # `sbozor_core.enums.ReversalReason` — FAQAT storno qatorida.
    reversal_reason: Mapped[str | None] = mapped_column(Text(), nullable=True)
    # `sbozor_core.enums.AdjustmentReason` — server summasidan chetlanish
    # sababi (D-19). `override_is_paired` uni ikki tomonlama majburlaydi.
    override_reason: Mapped[str | None] = mapped_column(Text(), nullable=True)
    # Klient bergan takroriylik kaliti (D-21).
    idempotency_key: Mapped[str] = mapped_column(Text(), nullable=False)
    # ⚠ SO'ROV TANASINING BARMOQ IZI — Pitfall 4. Bir xil kalit BOSHQA
    #   summa bilan kelsa 409 beriladi (06-09). Usiz D-21 ning «o'sha
    #   to'lovni qaytaradi» va'dasi BOSHQA to'lovni qaytarardi.
    request_fingerprint: Mapped[str] = mapped_column(Text(), nullable=False)
    # `NULL` RUXSAT — direktor smenasiz kiritishi mumkin (OQ-6/A5).
    shift_id: Mapped[UUID | None] = mapped_column(PgUuid(as_uuid=True), nullable=True)
    cashier_id: Mapped[UUID] = mapped_column(PgUuid(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    business_date: Mapped[date] = mapped_column(
        Date(), Computed(BILLING_BUSINESS_DATE_EXPR, persisted=True), nullable=False
    )


class BillingAnomaly(Base, TenantMixin):
    """Hisob YOZILMAGAN, lekin e'tibor talab qiladigan holat (C-12, D-05/D-10/D-28).

    =========================================================================
    UCHALA `kind` UCH BOSHQA QARORDAN CHIQADI VA ULAR HECH QACHON BITTA
    HISOBLAGICHGA QO'SHILMAYDI (`enums.py::AnomalyKind` docstringi):

      `unassigned_occupied` — rasta band, sotuvchi biriktirilmagan (D-28);
      `closed_day_occupied` — yopiq kunda savdo ko'rindi (D-10);
      `no_coverage_stall`   — rastani birorta kamera zonasi qamramaydi
                              (D-05). ⛔ BU «BAND, LEKIN TO'LOVSIZ» EMAS:
                              «ko'ra olmadik» ≠ «band».

    JUFTLANGAN `CHECK` (`NO_COVERAGE_ANOMALY_IS_PAIRED_CHECK`) uchinchisini
    birinchi ikkitasidan STRUKTURAVIY ajratadi: qamrovsizlikda hodisa
    BO'LMAYDI, qolgan ikkitasida esa BO'LISHI SHART. Aks holda ko'r
    nuqtadan tushum da'vosi to'qish mumkin bo'lardi.
    =========================================================================

    `UNIQUE (market_id, stall_id, service_date, kind)` — JOB QAYTA
    YUGURISHI uchun idempotentlik. `billing_close` kun davomida bir necha
    marta ishga tushishi mumkin (qayta urinish, qo'lda chaqiruv) va har
    safar o'sha anomaliyani QAYTA yozardi — kunlik hisobotda bitta rasta
    o'nlab qator bo'lib ko'rinardi.

    JADVAL AUDIT TRIGGERIDAN CHIQARILGAN: u HODISA JURNALI — odam
    tahrirlamaydi, job yozadi. Audit unga o'sha ma'lumotning ikkinchi
    nusxasini yozardi (`capture_runs` / `alert_events` bilan bir sinfda).

    `business_date` USTUNI BOR va u `service_date` DAN AJRALADI: anomaliya
    ham kun yopilishida (ertasi kuni 04:10) tug'iladi.
    """

    __tablename__ = "billing_anomalies"
    __table_args__ = (
        ForeignKeyConstraint(
            ["market_id"], ["markets.id"], name="fk_billing_anomalies_market_id_markets"
        ),
        ForeignKeyConstraint(
            ["market_id", "stall_id"],
            ["stalls.market_id", "stalls.id"],
            name="fk_billing_anomalies_market_id_stall_id_stalls",
        ),
        # ⚠ NULLABLE FK: `no_coverage_stall` da hodisa YO'Q va
        #   `NO_COVERAGE_ANOMALY_IS_PAIRED_CHECK` buni MAJBURLAYDI.
        ForeignKeyConstraint(
            ["market_id", "occupancy_event_id"],
            ["occupancy_events.market_id", "occupancy_events.id"],
            name="fk_billing_anomalies_occupancy_event",
        ),
        ForeignKeyConstraint(
            ["market_id", "snapshot_id"],
            ["snapshots.market_id", "snapshots.id"],
            name="fk_billing_anomalies_snapshot",
        ),
        # JOB QAYTA YUGURISHI UCHUN IDEMPOTENTLIK (klass docstringi).
        UniqueConstraint(
            "market_id",
            "stall_id",
            "service_date",
            "kind",
            name="uq_billing_anomalies_market_stall_service_date_kind",
        ),
        UniqueConstraint("market_id", "id", name="uq_billing_anomalies_market_id_id"),
        CheckConstraint(ANOMALY_KIND_CHECK, name="kind_allowed"),
        CheckConstraint(NO_COVERAGE_ANOMALY_IS_PAIRED_CHECK, name="no_coverage_is_paired"),
        CheckConstraint(ANOMALY_EVIDENCE_IS_PAIRED_CHECK, name="evidence_is_paired"),
        Index(BILLING_ANOMALY_INDEX, "market_id", "service_date", "kind"),
    )

    id: Mapped[UUID] = uuid_pk()
    # `sbozor_core.enums.AnomalyKind` — uchta a'zo, uchta boshqa qaror.
    kind: Mapped[str] = mapped_column(Text(), nullable=False)
    stall_id: Mapped[UUID] = mapped_column(PgUuid(as_uuid=True), nullable=False)
    # DOMEN sanasi — anomaliya QAYSI KUN uchun aniqlandi (`service_date`
    # `daily_charges` dagi bilan AYNAN bir xil ma'noga ega).
    service_date: Mapped[date] = mapped_column(Date(), nullable=False)
    # `no_coverage_stall` da `NULL` (C-12). Qolgan ikkisida MAJBURIY.
    occupancy_event_id: Mapped[UUID | None] = mapped_column(PgUuid(as_uuid=True), nullable=True)
    # Hodisa bilan JUFTLIKDA (`evidence_is_paired`).
    snapshot_id: Mapped[UUID | None] = mapped_column(PgUuid(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    business_date: Mapped[date] = mapped_column(
        Date(), Computed(BILLING_BUSINESS_DATE_EXPR, persisted=True), nullable=False
    )
