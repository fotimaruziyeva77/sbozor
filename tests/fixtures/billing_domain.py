"""Ikki bozorli BILLING seed'i — `occupancy_domain` ustiga qatlanadi.

=============================================================================
⛔⛔ BIRINCHI VA ENG QIMMAT QOIDA — `stall_slot_occupancy` QATORLARI
    `day_close` ORQALI YOZILADI, QO'LDA `INSERT` BILAN EMAS.

Sabab **C-3** (`06-VALIDATION.md` § Wave 0 ning birinchi ⚠ bandi):
`stall_slot_occupancy` D kuni uchun faqat **D+1 ning 03:40 da** to'ladi va
`occupancy_repo.materialize()` uning YAGONA yozuvchisi. Agar bu seed
qatorlarni qo'lda yozsa, `billing_close` HECH QACHON «slot qatori yo'q»
holatiga tushmasdi va **Pitfall 2** — «job yuguradi, `errors` bo'sh,
`charged = 0`» — testda KO'RINMASDI. U faqat prodda, birinchi kunlik
hisobot bo'sh chiqqanda ko'rinardi.

Shuning uchun bu modulda o'sha jadvalga XOM `INSERT` ham, uning ORM
klassi orqali yozish ham UMUMAN YO'Q — seed `snapshots` +
`occupancy_events` qatorlarini yozadi va so'ng MAHSULOT YO'LINI
(`app.jobs.day_close.day_close`) CHAQIRADI. Taqiq mexanik: ikkala shakl
ham bu faylda grep bilan qidiriladi va topilishi SHART EMAS.

⛔⛔ IKKINCHI QOIDA — FIXTURE IKKI VARIANTDA BERILADI VA IKKALASI HAM KERAK:

    billing_domain_before_day_close  -> slotlar HALI YO'Q  (0 qator)
    billing_domain                   -> `day_close` chaqirilgan, slotlar BOR

Bittasi bo'lganda «job yugurdi va hech nima yozmadi» holatini «job hali
yugurmagan» holatidan AJRATIB BO'LMASDI: ikkalasida ham `daily_charges`
bo'sh bo'lardi va `billing_close` ning `errors` ro'yxati ham bo'sh
qolardi. `before` varianti aynan shu farqni o'lchanadigan qiladi.
=============================================================================
NOMLASH — FAKT BO'YICHA, VERDIKT AKS-SADOSI BILAN EMAS (§S-9).

`fixtures/occupancy_domain.py:12-33` da o'rnatilgan majburiyat bu yerda
ham to'liq kuchda:

    stall_with_two_occupied_slots            ✅ (nechta slotda band — FAKT)
    stall_with_one_ai_occupied_slot          ✅
    stall_occupied_without_assignment        ✅ (biriktirish bor/yo'q — FAKT)

    stall_that_should_be_billed              ❌
    stall_below_the_billing_threshold        ❌

Ikkinchi ustundagi nomlar fixture'ni TEKSHIRILAYOTGAN QOIDANING
AKS-SADOSIGA aylantirardi: «hisob yoziladigan» rastani yasash uchun
BILL-01 ning chegarasini (nechta slot?) BILISH kerak bo'lardi va chegara
noto'g'ri qo'yilganda ham test YASHIL qolardi.

Shu sababdan bu modul `sbozor_core.models.billing` dagi KONSTRAYT
ifodalarini (`OVERRIDE_IS_PAIRED_CHECK` va h.k.) UMUMAN import qilmaydi —
u faqat enum QIYMATLARINI oladi, chunki ular DB kontenti.
=============================================================================
SEED KONTRAKTI — HAR BIR ELEMENT ANIQ BIR TESTNI OZIQLANTIRADI.

  * **BITTA TOIFA + IKKITA TARIF QATORI.** Birinchisi `valid_from <= D`
    va summasi ANIQ SON (`TARIFF_SOUM`), ikkinchisi `valid_from = D + 1`
    va summasi BOSHQA (`NEXT_DAY_TARIFF_SOUM`). Ikkinchi qator ATAYIN:
    D-09 ning «tarif keyin tahrirlansa yozilgan hisob RETROAKTIV
    o'zgarmasligi» sharti aynan shu bilan o'lchanadi. Bitta tarif bilan
    «D sanadagi narx» qidiruvi noto'g'ri qatorni tanlaganda ham to'g'ri
    javob berardi.

  * **`stall_with_two_occupied_slots`** — IKKI slotda band, ya'ni
    BILL-01 ning kirish holati. Ikkinchi slot uchun seed IKKINCHI
    YAROQLI KADR yozadi (pastdagi ⚠ ga qarang).

  * **`stall_with_one_ai_occupied_slot`** — BITTA slotda band, manba
    `ai`. Yuqoridagining ZID QUTBI: ikkalasi bir xil bo'lganda «nechta
    slot?» sharti umuman sinalmasdi.

  * **`stall_with_one_human_confirmed_occupied_slot`** — bitta slotda
    band, lekin manba `human` (nazoratchi tasdiqlagan). ⛔ Bu rasta
    `occupancy_domain` NING O'ZIDAN keladi (`stall_ids[0]`: `occupied`
    hodisa + ko'r audit javobi) va bu yerda QAYTA QURILMAYDI — ko'r audit
    doirasini ikkinchi marta yasash o'sha mexanizmning NUSXASI bo'lardi.

  * **`stall_with_only_no_coverage_slots`** — birorta zonasi YO'Q
    (`occupancy_domain.stall_without_zone_id`). D-05 ning kirish holati:
    «ko'ra olmadik» ≠ «band» va ≠ «bo'sh». Bu rastaga zona QO'SHILMAYDI.

  * **`stall_occupied_without_assignment`** — band, lekin `stall_
    assignments` da D kunini QAMRAMAYDIGAN bo'shliq bor. Bo'shliq
    `periods.py:24-27` ga ko'ra ATAYIN mumkin va u BILL-04/D-28 ning
    (`unassigned_occupied`) yagona kirish holati. ⚠ Rasta biriktirilgan
    davrga EGA — «hech qachon biriktirilmagan» holat bilan bir xil
    EMAS: bo'shliq shakli `[)` konventsiyasini ham sinaydi.

  * **YOPIQ KUN** — `market_calendar_exceptions` da `CLOSED_BUSINESS_DATE`
    yopiq deb belgilangan va o'sha kunda `stall_occupied_on_a_closed_day`
    band. D-10 ning kirish holati: yopiq kunda hisob yozilmaydi, lekin
    hodisa jimgina yo'qolmaydi (`closed_day_occupied` anomaliyasi).
    ⚠ Kun ATAYIN HAFTA KUNI bo'yicha OCHIQ (`A_OPEN_WEEKDAYS` da bor) —
    aks holda istisno qatori hech nimani ifodalamasdi va test kalendar
    istisnosini emas, haftalik jadvalni o'lchagan bo'lardi.

  * **KASSIR VA UNING OCHIQ SMENASI** — `two_markets` NING mavjud
    kassiri (`market_a.cashier_user_id`, ya'ni `AuthSeed.cashier` bilan
    AYNAN bir xil foydalanuvchi). ⛔ YANGI kassir YARATILMAYDI (Gotcha
    22): ikkinchi `cashier` rolli foydalanuvchi RBAC testlarining
    a'zolik sanog'ini jimgina o'zgartirardi.

  * **IKKINCHI BOZORDA BOSHQA KASSIR VA O'Z TARIF ZANJIRI.** «0 qator
    qaytdi» javobi izolyatsiya ishlaganini ham, jadval bo'shligini ham
    bildirishi mumkin — B bozorida qator BO'LMASA cross-tenant nazorati
    hech nimani o'lchamasdi.
=============================================================================
⚠ NEGA SEED O'ZI KADR YOZADI (`capture_runs` + `snapshots`).

`snapshot_domain.A_RUN_PLAN` A bozoriga IKKI kadr beradi va ulardan
faqat BITTASI yaroqli (`quality_verdict = 'ok'`); ikkinchisi `dark`,
ya'ni unga bandlik hodisasi UMUMAN yozib bo'lmaydi (D-21 langari).
Ya'ni mavjud seed bilan bir rasta ENG KO'PI BILAN bitta slotda band
bo'la olardi va `stall_with_two_occupied_slots` IFODALAB BO'LMASDI —
BILL-01 ning butun sharti («kamida ikki slot») sinalmay qolardi.

Shuning uchun bu modul IKKINCHI kameraga, IKKINCHI slotga yaroqli kadr
yozadi. `A_RUN_PLAN` ga qator qo'shish MUMKIN EMAS: u `snapshot_domain`
ning barcha sanoq testlarini (`statuses`, watchdog, hisobot) jimgina
siljitardi.

⚠ `business_date` QO'LDA YOZILMAYDI — `capture_runs` da u hisoblanadigan
ustun. Seed faqat `scheduled_at` beradi va uni `scheduled_at_for()`
orqali quradi (`snapshot_domain` bilan AYNAN bir manba).

UUID'LAR DETERMINISTIK EMAS — HAR CHAQIRUVDA YANGI (`uuid4`). Quyi
qatlamlar bilan aynan bir xil qaror.

Seed `sbozor_owner` autocommit ulanishi bilan yoziladi: ma'lumot
`day_close` ishlatadigan BOSHQA ulanishga (`sbozor_app` pool'i) DARHOL
ko'rinishi shart.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass
from datetime import date, time, timedelta
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from psycopg import Connection
from psycopg.rows import TupleRow
from sbozor_core.enums import (
    CaptureMethod,
    CaptureRunStatus,
    OccupancyVerdict,
    PaymentKind,
    PaymentMethod,
    ShiftStatus,
    SnapshotLightMode,
    SnapshotQuality,
)
from sbozor_core.models.snapshot import DEFAULT_SNAPSHOT_SLOTS

from fixtures.market_domain import MarketDomainSeed, to_pg_period
from fixtures.occupancy_domain import (
    MODEL_VERSION,
    SEED_THRESHOLDS_VERSION,
    SOURCE_HEIGHT,
    SOURCE_WIDTH,
    OccupancyDomainSeed,
    add_zone_with_event,
    square_polygon,
)
from fixtures.snapshot_domain import (
    DECODED_HEIGHT,
    DECODED_WIDTH,
    SEED_BUSINESS_DATE,
    scheduled_at_for,
)
from fixtures.two_markets import TwoMarketSeed

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

__all__ = [
    "BILLING_CATEGORY_NAME",
    "BILLING_VALID_FROM",
    "CLEANUP_ORDER",
    "CLOSED_BUSINESS_DATE",
    "GAP_RESUMES_AT",
    "HIGH_CONFIDENCE",
    "NEXT_DAY_TARIFF_SOUM",
    "NEXT_TARIFF_VALID_FROM",
    "SEED_BUSINESS_DATE",
    "TARIFF_SOUM",
    "BillingDomainSeed",
    "MarketBillingRows",
    "add_charge_evidence",
    "add_daily_charge",
    "add_payment",
    "billing_domain",
    "billing_domain_before_day_close",
    "cleanup_billing_domain",
    "seed_billing_domain",
    "slot_count",
]

TARIFF_SOUM = 15_000
"""D kunida amal qiladigan tarif — ANIQ SON, testlar summani SHUNGA solishtiradi.

⚠ `market_domain.A_TARIFF_AMOUNTS` (5 000 / 12 000 / 8 000) dan ATAYIN
FARQLI: agar summalar ustma-ust tushsa «hisob QAYSI tarifdan olindi?»
savoliga javob beradigan yagona signal yo'qolardi va noto'g'ri toifaning
narxi olinganda ham test yashil qolardi.
"""

NEXT_DAY_TARIFF_SOUM = 20_000
"""D + 1 dan boshlab amal qiladigan tarif — D-09 ning O'LCHOV nuqtasi.

`TARIFF_SOUM` dan FARQLI bo'lishi SHART: «D sanadagi narx» qidiruvi
noto'g'ri qatorni tanlaganda ikkalasi teng bo'lsa natija BIR XIL chiqardi
va retroaktivlik testi hech nimani o'lchamasdi.
"""

BILLING_VALID_FROM = date(2026, 8, 1)
"""Billing toifasi va birinchi tarifning `valid_from` i — D DAN OLDIN.

⚠ `market_domain.A_OPERATING_SINCE` (2026-01-15) DAN FARQLI va bu
ZARURAT, uslub emas: har rastada `operating_since` sanasida ALLAQACHON
toifa davri bor va `uq_stall_category_periods_market_id_stall_id_
valid_from` ikkinchi qatorni AYNAN o'sha sanada rad etardi.

Sana ikkala bozor uchun ham `operating_since` dan KEYIN
(A: 2026-01-15, B: 2026-02-01), ya'ni bitta konstanta yetadi.
"""

NEXT_TARIFF_VALID_FROM = SEED_BUSINESS_DATE + timedelta(days=1)
"""Ikkinchi tarif qatorining kuni — AYNAN `D + 1`.

Kun D ga TENG bo'lsa `uq_tariffs_market_id_category_id_valid_from`
birinchi qatorni rad etardi; D dan OLDIN bo'lsa u D kunidagi narxni
ALMASHTIRARDI va seed o'z tarifini o'zi buzardi.
"""

CLOSED_BUSINESS_DATE = SEED_BUSINESS_DATE + timedelta(days=2)
"""Kalendar istisnosi bilan YOPIQ deb belgilangan kun (D-10).

⚠ `D + 2` ATAYIN, `D + 1` EMAS: `D + 1` ikkinchi tarifning kuni va ikki
tushunchani bitta sanaga yig'ish testda «qaysi qoida ishladi?» savolini
javobsiz qoldirardi.

⚠ Kun HAFTA KUNI bo'yicha OCHIQ bo'lishi SHART (`A_OPEN_WEEKDAYS` = ISO
2..7, ya'ni faqat dushanba yopiq). 2026-09-03 — payshanba (ISO 4), ya'ni
bu kunni yopiq qiladigan YAGONA narsa `market_calendar_exceptions`
qatoridir. Dushanba tanlansa istisno qatori hech nimaga ta'sir qilmasdi
va D-10 testi haftalik jadvalni o'lchagan bo'lardi.
"""

GAP_RESUMES_AT = SEED_BUSINESS_DATE + timedelta(days=7)
"""`stall_occupied_without_assignment` ning IKKINCHI davri qachon boshlanadi.

Bo'shliq `[BILLING_VALID_FROM, D)` va `[D + 7, ∞)` orasida, ya'ni D
kunida rasta SOTUVCHISIZ. Ikkinchi davr MAJBURIY: faqat yopiq davr
qoldirish «hech qachon biriktirilmagan» holatidan ajralmasdi va D-28
ning ikkala shakli seedda BIR XIL ko'rinardi.
"""

BILLING_CATEGORY_NAME = "Patta (billing seed)"
"""Seed toifasining nomi — `A_CATEGORY_NAMES` / `B_CATEGORY_NAMES` da YO'Q.

`uq_stall_categories_market_id_name` bo'yicha to'qnashmaydi va import
matritsasi testlari (`A_CATEGORY_NAMES` ga tayanadi) tegilmaydi.
"""

HIGH_CONFIDENCE = "0.9400"
"""Seed hodisalarining ishonchi — SON BO'YICHA nomlangan (§S-9).

⛔ `CONFIDENCE_ABOVE_THRESHOLD` deb nomlanmaydi: bunday nom fixture'ni
chegara QIYMATINI biladigan qilib qo'yardi va chegara noto'g'ri
qo'yilganda ham test yashil qolardi.
"""

_SLOT_A: time = DEFAULT_SNAPSHOT_SLOTS[0]
_SLOT_B: time = DEFAULT_SNAPSHOT_SLOTS[1]
"""Kunning ikki sloti — `snapshot_domain.A_RUN_PLAN` AYNAN shularga kadr yozadi.

`_SLOT_B` da mavjud kadr `dark`, ya'ni yaroqsiz. Seed o'sha slotga
IKKINCHI KAMERA orqali yaroqli kadr qo'shadi (modul docstringidagi ⚠) —
`uq_capture_runs_market_id_camera_id_business_date_slot_time` kamera
bo'yicha ajratadi, ya'ni to'qnashuv yo'q.
"""

CLEANUP_ORDER: tuple[str, ...] = (
    "charge_evidence",
    "charge_adjustments",
    "payments",
    "billing_anomalies",
    "daily_charges",
    "cashier_shifts",
)
"""Billing jadvallarining O'CHIRISH TARTIBI — FK bo'yicha bolalardan yuqoriga.

⚠ REYESTRDAN (`migrations.entities.BILLING_DELETE_ORDER`) IMPORT
QILINMAYDI va bu ATAYIN (`occupancy_domain.CLEANUP_ORDER` bilan aynan bir
xil qaror): `tests/fixtures/` `migrations` paketiga bog'lanmaydi, va —
muhimrog'i — reyestrdan olingan ro'yxat reyestrning O'ZI xato bo'lganda
test bilan BIRGA xato bo'lardi.

⚠ `charge_evidence` BIRINCHI: u `daily_charges`, `stall_slot_occupancy`,
`occupancy_events` va `snapshots` ga BIRDAN tayanadi (C-7), ya'ni undan
keyin o'chiriladigan har bir jadval uni yetim qoldirardi.
"""

# ---------------------------------------------------------------------------
# XOM SQL — jadval nomlari LITERAL (`financial.py` da o'rnatilgan qoida)
# ---------------------------------------------------------------------------

_INSERT_CATEGORY = "INSERT INTO stall_categories (id, market_id, name) VALUES (%s, %s, %s)"
_INSERT_TARIFF = (
    "INSERT INTO tariffs (id, market_id, category_id, amount_soum, valid_from) "
    "VALUES (%s, %s, %s, %s, %s)"
)
_INSERT_CATEGORY_PERIOD = (
    "INSERT INTO stall_category_periods (id, market_id, stall_id, category_id, valid_from) "
    "VALUES (%s, %s, %s, %s, %s)"
)
_INSERT_ASSIGNMENT = (
    "INSERT INTO stall_assignments (id, market_id, stall_id, vendor_id, period) "
    "VALUES (%s, %s, %s, %s, %s)"
)
_INSERT_CALENDAR_EXCEPTION = (
    "INSERT INTO market_calendar_exceptions (id, market_id, exception_date, is_open, note) "
    "VALUES (%s, %s, %s, %s, %s)"
)
_INSERT_SHIFT = (
    "INSERT INTO cashier_shifts (id, market_id, cashier_id, status) VALUES (%s, %s, %s, %s)"
)
_INSERT_RUN = (
    "INSERT INTO capture_runs "
    "(id, market_id, camera_id, nvr_id, slot_time, scheduled_at, status, "
    " attempts, capture_method, is_market_open) "
    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
)
_INSERT_SNAPSHOT = (
    "INSERT INTO snapshots "
    "(id, market_id, capture_run_id, camera_id, scheduled_at, captured_at, slot_time, "
    " object_key, size_bytes, quality_verdict, quality_mean, quality_stddev, "
    " quality_thresholds_version, light_mode, capture_method, width, height) "
    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
)
_LINK_SNAPSHOT = "UPDATE capture_runs SET snapshot_id = %s WHERE id = %s"
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
_INSERT_CHARGE = (
    "INSERT INTO daily_charges "
    "(id, market_id, stall_id, vendor_id, service_date, tariff_id, "
    " tariff_amount_soum, amount_soum) "
    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
)
_INSERT_EVIDENCE = (
    "INSERT INTO charge_evidence "
    "(id, market_id, charge_id, stall_slot_occupancy_id, occupancy_event_id, "
    " snapshot_id, slot_time) "
    "VALUES (%s, %s, %s, %s, %s, %s, %s)"
)
_INSERT_PAYMENT = (
    "INSERT INTO payments "
    "(id, market_id, stall_id, vendor_id, service_date, amount_soum, quote_soum, "
    " kind, method, reverses_payment_id, reversal_reason, override_reason, "
    " idempotency_key, request_fingerprint, shift_id, cashier_id) "
    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
)

_SLOT_COUNT = (
    "SELECT count(*) FROM stall_slot_occupancy WHERE market_id = %s AND business_date = %s"
)


@dataclass(frozen=True)
class MarketBillingRows:
    """Bitta bozorning billing qatlami."""

    market_id: UUID
    category_id: UUID
    tariff_id: UUID
    """`valid_from = BILLING_VALID_FROM`, summasi `TARIFF_SOUM`."""
    next_tariff_id: UUID
    """`valid_from = D + 1`, summasi `NEXT_DAY_TARIFF_SOUM` (D-09)."""
    cashier_id: UUID
    """`two_markets` NING kassiri — yangi foydalanuvchi YARATILMAYDI (Gotcha 22)."""
    open_shift_id: UUID
    """Ochiq smena. Ikkinchisini ochish `uq_cashier_shifts_..._open` bilan rad etiladi."""
    vendor_id: UUID
    stall_with_two_occupied_slots: UUID | None
    """IKKI slotda band — BILL-01 ning kirish holati. B bozorida `None`."""
    stall_with_one_ai_occupied_slot: UUID | None
    """BITTA slotda band, manba `ai`. B bozorida `None`."""
    stall_with_one_human_confirmed_occupied_slot: UUID | None
    """BITTA slotda band, manba `human` — `occupancy_domain` DAN keladi."""
    stall_with_only_no_coverage_slots: UUID | None
    """Birorta zonasi YO'Q rasta (D-05). Bu rastaga zona QO'SHILMAYDI."""
    stall_occupied_without_assignment: UUID | None
    """Band, lekin D kuni biriktirish bo'shlig'ida (BILL-04/D-28)."""
    stall_occupied_on_a_closed_day: UUID | None
    """`CLOSED_BUSINESS_DATE` da band (D-10). B bozorida `None`."""
    second_billable_snapshot_id: UUID | None
    """IKKINCHI slotdagi YAROQLI kadr (modul docstringidagi ⚠). B da `None`."""
    closed_day_snapshot_id: UUID | None
    """Yopiq kundagi yaroqli kadr. B bozorida `None`."""
    calendar_exception_id: UUID | None
    """`CLOSED_BUSINESS_DATE` ni yopiq qiladigan qator. B bozorida `None`."""
    zone_ids: tuple[UUID, ...] = ()
    event_ids: tuple[UUID, ...] = ()
    run_ids: tuple[UUID, ...] = ()
    snapshot_ids: tuple[UUID, ...] = ()
    assignment_ids: tuple[UUID, ...] = ()
    category_period_ids: tuple[UUID, ...] = ()


@dataclass(frozen=True)
class BillingDomainSeed:
    """Ikki bozorning billing qatlami."""

    market_a: MarketBillingRows
    market_b: MarketBillingRows

    @property
    def markets(self) -> tuple[MarketBillingRows, MarketBillingRows]:
        return (self.market_a, self.market_b)

    @property
    def market_ids(self) -> tuple[UUID, ...]:
        return (self.market_a.market_id, self.market_b.market_id)


# ===========================================================================
# BAZADAN O'QIYDIGAN YORDAMCHILAR — hech biri qo'shni faylning RO'YXAT
# TARTIBIGA tayanmaydi (`occupancy_domain._camera_of()` da o'rnatilgan qoida)
# ===========================================================================


def _nvr_of(conn: Connection[TupleRow], market_id: UUID) -> UUID:
    """Bozorning NVR'i — `capture_runs` DAN, `nvr_domain` ro'yxatidan EMAS.

    `capture_runs.nvr_id` `NOT NULL`, ya'ni mavjud qator uni ALLAQACHON
    biladi. `nvr_domain` ning ro'yxatidan indeks bo'yicha olish ikkinchi
    haqiqat manbai bo'lardi va u qayta tartiblangan kuni seed boshqa
    qurilmaga bog'lanardi.
    """
    row = conn.execute(
        "SELECT nvr_id FROM capture_runs WHERE market_id = %s ORDER BY nvr_id LIMIT 1",
        (str(market_id),),
    ).fetchone()
    assert row is not None, (
        f"{market_id} da birorta `capture_runs` qatori yo'q — `snapshot_domain` seed'i ishlamagan"
    )
    nvr_id: UUID = row[0]
    return nvr_id


def _cashier_of(conn: Connection[TupleRow], market_id: UUID) -> UUID:
    """Bozorning `cashier` rolli foydalanuvchisi — `user_market_roles` DAN.

    ⛔ YANGI FOYDALANUVCHI YARATILMAYDI (Gotcha 22): `two_markets` har
    bozorga bittadan kassir yozadi va `AuthSeed.cashier` AYNAN o'sha
    qatorni ko'rsatadi (`fixtures/auth_users.py:208-210`). Ikkinchi
    `cashier` rolli hisob a'zolik sanog'iga tayanadigan RBAC testlarini
    jimgina siljitardi.

    ⚠ ROL BO'YICHA IZLANADI, `MarketSeed.cashier_user_id` DAN
      OLINMAYDI: shu funksiya ikkala bozor uchun ham bir xil ishlaydi va
      «B bozorida BOSHQA kassir» talabi seedning o'zida bajariladi.
    """
    row = conn.execute(
        "SELECT user_id FROM user_market_roles "
        "WHERE market_id = %s AND 'cashier' = ANY(roles) "
        "ORDER BY user_id LIMIT 1",
        (str(market_id),),
    ).fetchone()
    assert row is not None, (
        f"{market_id} da `cashier` rolli foydalanuvchi yo'q — `two_markets` seed'i o'zgargan"
    )
    cashier_id: UUID = row[0]
    return cashier_id


def slot_count(conn: Connection[TupleRow], market_id: UUID, day: date) -> int:
    """`stall_slot_occupancy` da shu kunning qatorlari soni.

    ⚠ IKKI VARIANT O'RTASIDAGI FARQNI O'LCHAYDIGAN YAGONA funksiya:
      `billing_domain_before_day_close` dan keyin **0**,
      `billing_domain` dan keyin **> 0**. Testlar bu sanoqni o'zlari
      qurmaydi — ikkita so'rov bir kun jimgina ajralib ketardi.
    """
    row = conn.execute(_SLOT_COUNT, (str(market_id), day)).fetchone()
    assert row is not None
    return int(row[0])


# ===========================================================================
# YOZUVCHILAR
# ===========================================================================


def _add_billable_frame(
    conn: Connection[TupleRow],
    *,
    market_id: UUID,
    nvr_id: UUID,
    camera_id: UUID,
    slot: time,
    day: date,
    is_market_open: bool,
) -> tuple[UUID, UUID]:
    """`capture_runs` + YAROQLI (`quality_verdict = 'ok'`) `snapshots` juftligi.

    Returns:
        `(run_id, snapshot_id)`.

    ⚠ `quality_verdict = 'ok'` MAJBURIY: `snapshots.is_billable`
      `GENERATED ALWAYS AS (quality_verdict = 'ok')` va `occupancy_events`
      AYNAN `(id, true)` juftligiga osiladi (D-21 langari). `dark` kadrga
      hodisa yozish `ForeignKeyViolation` beradi.

    ⚠ `is_market_open` ARGUMENT: yopiq kundagi kadr `false` bilan
      yoziladi. `snapshot_domain` uni HAR DOIM `true` qiladi va o'z
      docstringida «yopiq kun holati kerak bo'lgan test qatorni O'ZI
      yozadi» deb yozgan — bu funksiya aynan o'sha qator.
    """
    scheduled_at = scheduled_at_for(slot, day)
    run_id, snapshot_id = uuid4(), uuid4()
    conn.execute(
        _INSERT_RUN,
        (
            str(run_id),
            str(market_id),
            str(camera_id),
            str(nvr_id),
            slot,
            scheduled_at,
            CaptureRunStatus.SUCCEEDED.value,
            1,
            CaptureMethod.GO2RTC.value,
            is_market_open,
        ),
    )
    conn.execute(
        _INSERT_SNAPSHOT,
        (
            str(snapshot_id),
            str(market_id),
            str(run_id),
            str(camera_id),
            scheduled_at,
            scheduled_at.replace(second=9),
            slot,
            f"{market_id}/{day.isoformat()}/{camera_id}/{slot.strftime('%H%M')}-billing.jpg",
            48_128,
            SnapshotQuality.OK.value,
            "112.40",
            "48.75",
            SEED_THRESHOLDS_VERSION,
            SnapshotLightMode.DAY.value,
            CaptureMethod.GO2RTC.value,
            DECODED_WIDTH,
            DECODED_HEIGHT,
        ),
    )
    conn.execute(_LINK_SNAPSHOT, (str(snapshot_id), str(run_id)))
    return run_id, snapshot_id


def _add_zone_with_event_on(
    conn: Connection[TupleRow],
    *,
    market_id: UUID,
    camera_id: UUID,
    stall_id: UUID,
    snapshot_id: UUID,
    business_date: date,
    slot: time,
    center: tuple[float, float],
    version: int = 1,
) -> tuple[UUID, UUID]:
    """Zona + BANDLIK hodisasi — hodisaning KUNI argument bilan beriladi.

    ⛔ `occupancy_domain.add_zone_with_event()` BU YERDA ISHLATIB
       BO'LMAYDI va sabab mexanik: u `business_date` ga
       `SEED_BUSINESS_DATE` ni QADAB yozadi
       (`fixtures/occupancy_domain.py:850`). Yopiq kun (`CLOSED_BUSINESS_
       DATE`) uchun bu hodisaning kunini KADRNING kunidan ajratib
       yuborardi — ya'ni seedning o'zi «`occupancy_events.business_date`
       `snapshots` ning NUSXASI» invariantini buzardi va nosozlik yarim
       tun bug'i kabi ko'rinardi.

    D kunidagi hodisalar uchun ESA o'sha ommaviy yordamchi ishlatiladi
    (`_seed_market_a_occupancy()`), ya'ni bu funksiya faqat BOSHQA kun
    uchun mavjud.
    """
    zone_id, event_id = uuid4(), uuid4()
    conn.execute(
        _INSERT_ZONE,
        (
            str(zone_id),
            str(market_id),
            str(camera_id),
            str(stall_id),
            version,
            _as_json(square_polygon(*center)),
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
            business_date,
            slot,
            OccupancyVerdict.OCCUPIED.value,
            HIGH_CONFIDENCE,
            MODEL_VERSION,
            SEED_THRESHOLDS_VERSION,
            version,
        ),
    )
    return zone_id, event_id


def _as_json(points: list[list[float]]) -> str:
    """Poligonni `jsonb` parametri uchun matnga aylantiradi."""
    inner = ", ".join(f"[{x}, {y}]" for x, y in points)
    return f"[{inner}]"


def _seed_tariff_chain(
    conn: Connection[TupleRow], *, market_id: UUID, stall_ids: tuple[UUID, ...]
) -> tuple[UUID, UUID, UUID, tuple[UUID, ...]]:
    """Bitta toifa + IKKI tarif qatori + berilgan rastalarning toifa davri.

    Returns:
        `(category_id, tariff_id, next_tariff_id, category_period_ids)`.
    """
    category_id = uuid4()
    conn.execute(_INSERT_CATEGORY, (str(category_id), str(market_id), BILLING_CATEGORY_NAME))

    tariff_id, next_tariff_id = uuid4(), uuid4()
    conn.execute(
        _INSERT_TARIFF,
        (str(tariff_id), str(market_id), str(category_id), TARIFF_SOUM, BILLING_VALID_FROM),
    )
    # ⛔ IKKINCHI QATOR — D-09 ning o'lchov nuqtasi (modul docstringi).
    conn.execute(
        _INSERT_TARIFF,
        (
            str(next_tariff_id),
            str(market_id),
            str(category_id),
            NEXT_DAY_TARIFF_SOUM,
            NEXT_TARIFF_VALID_FROM,
        ),
    )

    period_ids: list[UUID] = []
    for stall_id in stall_ids:
        period_id = uuid4()
        conn.execute(
            _INSERT_CATEGORY_PERIOD,
            (
                str(period_id),
                str(market_id),
                str(stall_id),
                str(category_id),
                BILLING_VALID_FROM,
            ),
        )
        period_ids.append(period_id)

    return category_id, tariff_id, next_tariff_id, tuple(period_ids)


def _seed_market_a(
    conn: Connection[TupleRow],
    *,
    domain: MarketDomainSeed,
    occupancy: OccupancyDomainSeed,
) -> MarketBillingRows:
    """A bozori — TO'LIQ holat qamrovi (oltala rasta stsenariysi)."""
    rows = occupancy.market_a
    market_id = rows.market_id
    stalls = domain.market_a.stall_ids
    vendor_id = domain.market_a.vendor_ids[0]

    primary_camera = rows.camera_id
    second_camera = rows.second_camera_id
    assert second_camera is not None, (
        "A bozorida ikkinchi faol kamera yo'q — `stall_with_two_occupied_slots` "
        "ni ifodalab bo'lmasdi (ikkinchi slotning kadri o'sha kameradan keladi)"
    )
    no_coverage_stall = rows.stall_without_zone_id
    assert no_coverage_stall is not None, (
        "A bozorida zonasiz rasta yo'q — D-05 ning kirish holati yo'qolgan"
    )

    # ⚠ RASTALAR NOMMA-NOM TANLANADI, so'rov bilan TOPILMAYDI. «Zonasi
    #   bo'lmagan rastani top» shaklidagi tanlov seedni `camera_zones`
    #   so'rovining AKS-SADOSIGA aylantirardi (§S-9).
    two_slot_stall = stalls[3]
    one_ai_slot_stall = stalls[4]
    human_slot_stall = stalls[0]
    unassigned_stall = stalls[5]
    closed_day_stall = stalls[1]

    nvr_id = _nvr_of(conn, market_id)

    # ---- Ikkinchi YAROQLI kadr (modul docstringidagi ⚠).
    second_run_id, second_snapshot_id = _add_billable_frame(
        conn,
        market_id=market_id,
        nvr_id=nvr_id,
        camera_id=second_camera,
        slot=_SLOT_B,
        day=SEED_BUSINESS_DATE,
        is_market_open=True,
    )
    # ---- Yopiq kundagi kadr (D-10). `is_market_open = false` — bu DALIL:
    #      kadr yopiq kunda olingan (D-10 yopiq kunda ham kadr olishni
    #      TALAB qiladi, faqat hisob yozilmaydi).
    closed_run_id, closed_snapshot_id = _add_billable_frame(
        conn,
        market_id=market_id,
        nvr_id=nvr_id,
        camera_id=primary_camera,
        slot=_SLOT_A,
        day=CLOSED_BUSINESS_DATE,
        is_market_open=False,
    )

    zone_ids: list[UUID] = []
    event_ids: list[UUID] = []

    # (a) IKKI SLOTDA BAND: birinchi slot asosiy kamerada, ikkinchisi —
    #     ikkinchi kamerada. Bitta kamerada ikki slot yozib BO'LMASDI:
    #     `_SLOT_B` da asosiy kameraning kadri `dark`.
    for camera_id, snapshot_id, center in (
        (primary_camera, rows.snapshot_with_ok_quality, (0.24, 0.66)),
        (second_camera, second_snapshot_id, (0.44, 0.28)),
    ):
        seeded = add_zone_with_event(
            conn,
            market_id=market_id,
            camera_id=camera_id,
            stall_id=two_slot_stall,
            snapshot_id=snapshot_id,
            verdict=OccupancyVerdict.OCCUPIED.value,
            confidence=HIGH_CONFIDENCE,
            center=center,
        )
        zone_ids.append(seeded.zone_id)
        event_ids.append(seeded.event_id)

    # (b) BITTA SLOTDA BAND, manba `ai` — (a) ning ZID QUTBI.
    one_slot = add_zone_with_event(
        conn,
        market_id=market_id,
        camera_id=primary_camera,
        stall_id=one_ai_slot_stall,
        snapshot_id=rows.snapshot_with_ok_quality,
        verdict=OccupancyVerdict.OCCUPIED.value,
        confidence=HIGH_CONFIDENCE,
        center=(0.62, 0.18),
    )
    zone_ids.append(one_slot.zone_id)
    event_ids.append(one_slot.event_id)

    # (e) BAND, LEKIN BIRIKTIRISH BO'SHLIG'IDA (BILL-04/D-28).
    unassigned = add_zone_with_event(
        conn,
        market_id=market_id,
        camera_id=primary_camera,
        stall_id=unassigned_stall,
        snapshot_id=rows.snapshot_with_ok_quality,
        verdict=OccupancyVerdict.OCCUPIED.value,
        confidence=HIGH_CONFIDENCE,
        center=(0.80, 0.80),
    )
    zone_ids.append(unassigned.zone_id)
    event_ids.append(unassigned.event_id)

    # (f) YOPIQ KUNDA BAND (D-10). ⚠ `version = 2`: bu rastada
    #     `occupancy_domain` ning `version = 1` zonasi ALLAQACHON bor
    #     (`uq_camera_zones_..._version`).
    closed_zone_id, closed_event_id = _add_zone_with_event_on(
        conn,
        market_id=market_id,
        camera_id=primary_camera,
        stall_id=closed_day_stall,
        snapshot_id=closed_snapshot_id,
        business_date=CLOSED_BUSINESS_DATE,
        slot=_SLOT_A,
        center=(0.36, 0.52),
        version=2,
    )
    zone_ids.append(closed_zone_id)
    event_ids.append(closed_event_id)

    # ---- Tarif zanjiri: hisob YOZILISHI kutilayotgan rastalar + (e).
    #      (d) (`no_coverage`) ATAYIN QOLDIRILADI: qamrovsizlik anomaliyasi
    #      tarifga umuman tayanmaydi va unga toifa berish «tarif yo'q»
    #      shoxini seedda o'chirib qo'yardi.
    billed_stalls = (two_slot_stall, one_ai_slot_stall, human_slot_stall, unassigned_stall)
    category_id, tariff_id, next_tariff_id, period_ids = _seed_tariff_chain(
        conn, market_id=market_id, stall_ids=billed_stalls
    )

    # ---- Biriktirishlar. (a), (b) ochiq oxirli; (e) — BO'SHLIQ bilan.
    assignment_ids: list[UUID] = []
    for stall_id in (two_slot_stall, one_ai_slot_stall):
        assignment_ids.append(
            _assign(conn, market_id, stall_id, vendor_id, BILLING_VALID_FROM, None)
        )
    # ⛔ BO'SHLIQ: `[BILLING_VALID_FROM, D)` — `[)` konventsiyasida D
    #    yuqori chegara, ya'ni D kuni davrga KIRMAYDI. Ikkinchi davr D + 7
    #    dan boshlanadi, ya'ni bo'shliq IKKI tomondan yopilgan va u
    #    «hech qachon biriktirilmagan» holatdan ajraladi.
    assignment_ids.append(
        _assign(
            conn,
            market_id,
            unassigned_stall,
            vendor_id,
            BILLING_VALID_FROM,
            SEED_BUSINESS_DATE,
        )
    )
    assignment_ids.append(
        _assign(conn, market_id, unassigned_stall, vendor_id, GAP_RESUMES_AT, None)
    )

    # ---- Yopiq kun (D-10).
    calendar_exception_id = uuid4()
    conn.execute(
        _INSERT_CALENDAR_EXCEPTION,
        (
            str(calendar_exception_id),
            str(market_id),
            CLOSED_BUSINESS_DATE,
            False,
            "Billing seed — yopiq kun (D-10)",
        ),
    )

    cashier_id = _cashier_of(conn, market_id)
    open_shift_id = _open_shift(conn, market_id, cashier_id)

    return MarketBillingRows(
        market_id=market_id,
        category_id=category_id,
        tariff_id=tariff_id,
        next_tariff_id=next_tariff_id,
        cashier_id=cashier_id,
        open_shift_id=open_shift_id,
        vendor_id=vendor_id,
        stall_with_two_occupied_slots=two_slot_stall,
        stall_with_one_ai_occupied_slot=one_ai_slot_stall,
        stall_with_one_human_confirmed_occupied_slot=human_slot_stall,
        stall_with_only_no_coverage_slots=no_coverage_stall,
        stall_occupied_without_assignment=unassigned_stall,
        stall_occupied_on_a_closed_day=closed_day_stall,
        second_billable_snapshot_id=second_snapshot_id,
        closed_day_snapshot_id=closed_snapshot_id,
        calendar_exception_id=calendar_exception_id,
        zone_ids=tuple(zone_ids),
        event_ids=tuple(event_ids),
        run_ids=(second_run_id, closed_run_id),
        snapshot_ids=(second_snapshot_id, closed_snapshot_id),
        assignment_ids=tuple(assignment_ids),
        category_period_ids=period_ids,
    )


def _seed_market_b(
    conn: Connection[TupleRow],
    *,
    domain: MarketDomainSeed,
    occupancy: OccupancyDomainSeed,
) -> MarketBillingRows:
    """B bozori — CROSS-TENANT nazorati uchun MINIMAL, lekin BO'SH EMAS.

    B ning yagona vazifasi «A ni ko'raman, B ni ko'rmayman» da'vosini
    o'lchanadigan qilish, ya'ni unga to'liq holat qamrovi kerak emas.
    Lekin qator BO'LISHI shart: bo'sh bozor bilan har qanday izolyatsiya
    asserti JIMGINA rost bo'lardi.

    ⚠ KASSIR BOSHQA: `_cashier_of()` rol bo'yicha izlaydi, ya'ni B
      bozorining o'z kassirini topadi. Ikkala bozorda bir xil kassir
      bo'lganda `uq_cashier_shifts_market_id_cashier_open` ning
      «bir kassirda bitta ochiq smena» sharti bozor bo'yicha ajralganini
      seed umuman ifodalamasdi.
    """
    market_id = occupancy.market_b.market_id
    stall_id = domain.market_b.stall_ids[0]
    vendor_id = domain.market_b.vendor_ids[0]

    category_id, tariff_id, next_tariff_id, period_ids = _seed_tariff_chain(
        conn, market_id=market_id, stall_ids=(stall_id,)
    )
    cashier_id = _cashier_of(conn, market_id)
    open_shift_id = _open_shift(conn, market_id, cashier_id)

    return MarketBillingRows(
        market_id=market_id,
        category_id=category_id,
        tariff_id=tariff_id,
        next_tariff_id=next_tariff_id,
        cashier_id=cashier_id,
        open_shift_id=open_shift_id,
        vendor_id=vendor_id,
        stall_with_two_occupied_slots=None,
        stall_with_one_ai_occupied_slot=None,
        # B bozorining `stall_ids[0]` i `occupancy_domain` da `occupied`
        # hodisaga ega, lekin ko'r audit javobi ham bor -> manba `human`.
        stall_with_one_human_confirmed_occupied_slot=stall_id,
        stall_with_only_no_coverage_slots=None,
        stall_occupied_without_assignment=None,
        stall_occupied_on_a_closed_day=None,
        second_billable_snapshot_id=None,
        closed_day_snapshot_id=None,
        calendar_exception_id=None,
        category_period_ids=period_ids,
    )


def _assign(
    conn: Connection[TupleRow],
    market_id: UUID,
    stall_id: UUID,
    vendor_id: UUID,
    start: date,
    end: date | None,
) -> UUID:
    """`stall_assignments` qatori — chegara harfi `to_pg_period()` DAN.

    ⚠ Xom `daterange(...)` matni bu yerda QURILMAYDI: `[)` konventsiyasi
      `sbozor_core.periods.PERIOD_BOUNDS` da yashaydi va
      `market_domain.to_pg_period()` uni AYNAN o'sha yerdan oladi
      (`fixtures/market_domain.py:334-344`).
    """
    assignment_id = uuid4()
    conn.execute(
        _INSERT_ASSIGNMENT,
        (
            str(assignment_id),
            str(market_id),
            str(stall_id),
            str(vendor_id),
            to_pg_period(start, end),
        ),
    )
    return assignment_id


def _open_shift(conn: Connection[TupleRow], market_id: UUID, cashier_id: UUID) -> UUID:
    """OCHIQ smena — `status` LITERAL emas, `ShiftStatus` DAN.

    ⚠ FAQAT BITTA: ikkinchi ochiq smena `uq_cashier_shifts_market_id_
      cashier_open` bilan rad etiladi (D-27) va aynan shu rad etish
      `test_billing_immutable.py` da O'LCHANADI. Seed ikkinchisini
      yozsa o'sha test seedning o'zida yiqilardi.
    """
    shift_id = uuid4()
    conn.execute(
        _INSERT_SHIFT, (str(shift_id), str(market_id), str(cashier_id), ShiftStatus.OPEN.value)
    )
    return shift_id


def seed_billing_domain(
    conn: Connection[TupleRow],
    base: TwoMarketSeed,
    domain: MarketDomainSeed,
    occupancy: OccupancyDomainSeed,
) -> BillingDomainSeed:
    """`occupancy_domain` ustiga billing qatlamini yozadi — `day_close` SIZ.

    `conn` `sbozor_owner` bilan ochilgan va AUTOCOMMIT rejimida bo'lishi
    kerak: `day_close` BOSHQA ulanishdan (`sbozor_app` pool'i) o'qiydi.

    ⚠ `base` ARGUMENT SIFATIDA OLINADI, lekin bevosita ISHLATILMAYDI va
      bu ATAYIN: kassir rol bo'yicha BAZADAN topiladi (`_cashier_of()`),
      ya'ni seed `MarketSeed` ning maydon nomiga bog'lanmaydi. Argument
      esa fixture zanjirining TARTIBINI e'lon qiladi — `two_markets`
      qatlami bo'lmasa `user_market_roles` bo'sh bo'lardi.
    """
    assert base.market_a.id == occupancy.market_a.market_id, (
        "fixture zanjiri buzilgan: `two_markets` va `occupancy_domain` "
        "boshqa bozorlarni ko'rsatyapti"
    )
    return BillingDomainSeed(
        market_a=_seed_market_a(conn, domain=domain, occupancy=occupancy),
        market_b=_seed_market_b(conn, domain=domain, occupancy=occupancy),
    )


def cleanup_billing_domain(conn: Connection[TupleRow], seed: BillingDomainSeed) -> None:
    """Billing qatlamini FK tartibida o'chiradi.

    =========================================================================
    ⚠ AVVAL BOZORLAR QORALAMAGA QAYTARILADI VA BUSIZ TOZALASH YIQILADI.

    `0020` `daily_charges` va `payments` ga SHARTSIZ (`P0001`),
    `cashier_shifts` ga SHARTLI (`23514`) o'zgarmaslik qo'riqchisini
    qo'yadi; `0018` esa `occupancy_events` ga. `DELETE` uchun yagona
    istisno — QORALAMA bozor, ya'ni `market_delete_draft()` ning yo'li.
    Faol bozorda birinchi `DELETE` darhol yiqilardi.

    Naqsh YANGI EMAS: `cleanup_occupancy_domain()` va
    `cleanup_market_domain()` aynan shu qadamni 02-04 dan beri bajaradi.
    Bayroqni tushirish semantik jihatdan HALOL: qatorlar bir necha satr
    keyin butunlay o'chiriladi va bozorlarni quyi qatlamlar baribir
    o'chiradi.
    =========================================================================

    ⚠ `stall_slot_occupancy` TO'LIQ tozalanadi (`WHERE market_id`), o'z
      qatorlari bo'yicha emas: uni `day_close` yozgan va seed uning
      identifikatorlarini BILMAYDI — bilishi ham kerak emas (modul
      docstringidagi birinchi qoida). `cleanup_occupancy_domain()` keyin
      o'sha jadvalga 0 qator bilan tegadi va bu xavfsiz.
    """
    market_ids = [str(market_id) for market_id in seed.market_ids]
    conn.execute(
        "UPDATE markets SET is_active = false WHERE id = ANY(%s::uuid[])",
        (market_ids,),
    )

    for table in CLEANUP_ORDER:
        # Jadval nomlari shu moduldagi SOBIT `CLEANUP_ORDER` dan keladi —
        # tashqi kirish emas, ya'ni f-string bu yerda xavfsiz
        # (`occupancy_domain.py` dagi jufti bilan bir xil naqsh).
        conn.execute(
            f"DELETE FROM {table} WHERE market_id = ANY(%s::uuid[])",  # noqa: S608
            (market_ids,),
        )

    conn.execute(
        "DELETE FROM stall_slot_occupancy WHERE market_id = ANY(%s::uuid[])",
        (market_ids,),
    )

    # ⚠ TARTIB: hodisa -> zona -> kadr -> yugurish. `occupancy_events`
    #   `camera_zones` GA va `snapshots` GA birdan tayanadi, `snapshots`
    #   esa `capture_runs` ga (`snapshot_domain.CLEANUP_ORDER` bilan bir
    #   xil zanjir).
    for table, ids in (
        ("occupancy_events", _ids(seed, "event_ids")),
        ("camera_zones", _ids(seed, "zone_ids")),
        ("snapshots", _ids(seed, "snapshot_ids")),
        ("capture_runs", _ids(seed, "run_ids")),
        ("stall_assignments", _ids(seed, "assignment_ids")),
        ("stall_category_periods", _ids(seed, "category_period_ids")),
    ):
        if ids:
            conn.execute(
                f"DELETE FROM {table} WHERE id = ANY(%s::uuid[])",  # noqa: S608
                (ids,),
            )

    exception_ids = [
        str(rows.calendar_exception_id)
        for rows in seed.markets
        if rows.calendar_exception_id is not None
    ]
    if exception_ids:
        conn.execute(
            "DELETE FROM market_calendar_exceptions WHERE id = ANY(%s::uuid[])", (exception_ids,)
        )

    tariff_ids = [str(rows.tariff_id) for rows in seed.markets]
    tariff_ids += [str(rows.next_tariff_id) for rows in seed.markets]
    conn.execute("DELETE FROM tariffs WHERE id = ANY(%s::uuid[])", (tariff_ids,))
    conn.execute(
        "DELETE FROM stall_categories WHERE id = ANY(%s::uuid[])",
        ([str(rows.category_id) for rows in seed.markets],),
    )


def _ids(seed: BillingDomainSeed, field: str) -> list[str]:
    """Ikkala bozorning `field` ro'yxatini bitta tekis ro'yxatga yig'adi."""
    return [str(value) for rows in seed.markets for value in getattr(rows, field)]


# ===========================================================================
# IKKI VARIANT — MODUL DOCSTRINGINING IKKINCHI QOIDASI
# ===========================================================================


@contextmanager
def billing_domain_before_day_close(
    conn: Connection[TupleRow],
    base: TwoMarketSeed,
    domain: MarketDomainSeed,
    occupancy: OccupancyDomainSeed,
) -> Iterator[BillingDomainSeed]:
    """Seed YOZILGAN, lekin `stall_slot_occupancy` HALI BO'SH.

    =========================================================================
    ⛔ BU VARIANT PITFALL 2 NI O'LCHASH UCHUN MAJBURIY.

    `billing_close(D)` slot qatorlarisiz yugurganda `errors` bo'sh
    qoladi va `charged = 0` bo'ladi — ya'ni job «muvaffaqiyatli» hisobot
    beradi va HECH NIMA yozmaydi. `billing_domain` (slotlar BOR) bilan
    yozilgan test o'sha holatni HECH QACHON ko'rmasdi.
    =========================================================================

    ⚠ `occupancy_domain` NING IKKI SLOT QATORI OLIB TASHLANADI. Ular
      qo'lda yozilgan (`fixtures/occupancy_domain.py:_INSERT_SLOT`) va bu
      seed uchun ULAR ham «day_close yugurmagan» holatini buzardi:
      «0 qator» da'vosi ikkita qoldiq qator bilan hech qachon rost
      bo'lmasdi. Tozalash NAZORAT ASSERTI bilan keladi —
      `test_day_close.py::clear_slots` da o'rnatilgan qoida.
    """
    seed = seed_billing_domain(conn, base, domain, occupancy)
    market_ids = [str(market_id) for market_id in seed.market_ids]
    conn.execute(
        "DELETE FROM stall_slot_occupancy WHERE market_id = ANY(%s::uuid[])",
        (market_ids,),
    )
    for market_id in seed.market_ids:
        assert slot_count(conn, market_id, SEED_BUSINESS_DATE) == 0, (
            f"{market_id}: slot qatorlari tozalanmadi — «day_close hali yugurmagan» "
            "holati ifodalanmagan va Pitfall 2 ni o'lchab bo'lmasdi"
        )
    try:
        yield seed
    finally:
        cleanup_billing_domain(conn, seed)


@asynccontextmanager
async def billing_domain(
    conn: Connection[TupleRow],
    sessionmaker: async_sessionmaker[AsyncSession],
    base: TwoMarketSeed,
    domain: MarketDomainSeed,
    occupancy: OccupancyDomainSeed,
) -> AsyncIterator[BillingDomainSeed]:
    """Seed + `day_close` — `stall_slot_occupancy` MAHSULOT YO'LIDAN to'ladi.

    =========================================================================
    ⛔ SLOT QATORLARINI YOZADIGAN YAGONA YO'L SHU YERDA VA U MAHSULOT
       KODINING O'ZI (`app.jobs.day_close.day_close`).

    Qo'lda `INSERT` yozish arzonroq bo'lardi va aynan o'sha arzonlik C-3
    sinfidagi xatoni testdan YASHIRARDI (modul docstringining birinchi
    bandi). `occupancy_repo.materialize()` — `stall_slot_occupancy` ning
    YAGONA yozuvchisi va seed uni CHETLAB O'TMAYDI.
    =========================================================================

    ⚠ `day_close` IKKI MARTA chaqiriladi: kunlik D uchun VA yopiq kun
      (`CLOSED_BUSINESS_DATE`) uchun. Job kunni ARGUMENT sifatida oladi
      (`day_close.py:153-157`), ya'ni ikkinchi chaqiruv birinchisining
      natijasini BUZMAYDI — materializatsiya `(market, stall, business_
      date, slot)` bo'yicha idempotent.

    ⚠ `set_tenant_context()` BU YERDA CHAQIRILMAYDI: `day_close` uni
      HAR BOZOR uchun O'ZI o'rnatadi (`day_close.py::_tenant_session`).
      Fixture uni oldindan qo'yishga urinsa job o'z kontekstini o'sha
      sessiyada QAYTA o'rnatardi va test mahsulot yo'lidan chetlangan
      bo'lardi (Pitfall 9).

    ⚠ IMPORT FUNKSIYA ICHIDA. `tests/fixtures/` moduli `app` paketiga
      MODUL DARAJASIDA bog'lanmasin: qolgan fixture'lar `cv-service`
      to'plamida ham import qilinadi va o'sha yerda `app` YO'Q
      (`test_occupancy_domain_meta.py` dagi `migrations.entities` importi
      bilan aynan bir xil qaror).
    """
    from app.jobs.day_close import day_close

    with billing_domain_before_day_close(conn, base, domain, occupancy) as seed:
        await day_close(sessionmaker, business_date=SEED_BUSINESS_DATE)
        await day_close(sessionmaker, business_date=CLOSED_BUSINESS_DATE)

        for market_id in seed.market_ids:
            assert slot_count(conn, market_id, SEED_BUSINESS_DATE) > 0, (
                f"{market_id}: `day_close` birorta slot qatori yozmadi — seed "
                "kadrsiz yoki rastasiz qolgan bo'lishi mumkin va bu holatda "
                "hisob testlari BO'SH bazani o'lchagan bo'lardi"
            )
        yield seed


# ===========================================================================
# QATOR YOZUVCHI YORDAMCHILAR — SEEDNING O'ZIGA QO'SHILMAYDI
#
# ⚠ SABAB `occupancy_domain.py:754-768` DAGI BILAN AYNAN BIR XIL: seed
#   billing job'ining KIRISHINI ta'riflaydi, CHIQISHINI emas. `daily_
#   charges` / `payments` qatorlarini seedga qo'shish `billing_close` ning
#   idempotentlik testini JIMGINA trivial qilardi — job hech nima
#   yozmasa ham jadval bo'sh bo'lmasdi.
#
#   Shuning uchun ular SO'RALGANDA yoziladi va faqat ularni so'ragan
#   testda mavjud bo'ladi (`test_billing_immutable.py` — o'zgarmaslik
#   qo'riqchilarini o'lchash uchun yozilgan qator KERAK).
# ===========================================================================


def _safe_service_date(conn: Connection[TupleRow]) -> date:
    """Hisob/to'lov uchun XAVFSIZ domen sanasi — BAZANING «kechagi kuni».

    =========================================================================
    ⛔ `SEED_BUSINESS_DATE` BU YERDA ISHLATIB BO'LMAYDI VA SABAB SXEMADA.

    `ck_daily_charges_service_date_not_in_future` `service_date <=
    business_date` ni talab qiladi, `business_date` esa `created_at` DAN
    HOSILA, ya'ni HAR DOIM «bugun». `SEED_BUSINESS_DATE` (2026-09-01) esa
    QADALGAN sana va u bugundan keyin bo'lishi mumkin — o'shanda
    `INSERT` `CheckViolation` bilan yiqilardi va sabab «seed noto'g'ri»
    emas, «konstrayt buzuq» kabi ko'rinardi.

    `CURRENT_DATE - 1` shakli 06-04 da o'lchangan (`test_market_delete_
    guard.py:615-620`): `business_date` `Asia/Tashkent` da hisoblanadi,
    ya'ni u UTC `CURRENT_DATE` dan HECH QACHON kichik emas va shart yarim
    tunda ham buzilmaydi.
    =========================================================================
    """
    row = conn.execute("SELECT CURRENT_DATE - 1").fetchone()
    assert row is not None
    service_date: date = row[0]
    return service_date


def add_daily_charge(
    conn: Connection[TupleRow],
    *,
    market_id: UUID,
    stall_id: UUID,
    vendor_id: UUID,
    tariff_id: UUID,
    amount_soum: int = TARIFF_SOUM,
    service_date: date | None = None,
) -> tuple[UUID, date]:
    """Bitta `daily_charges` qatori.

    Returns:
        `(charge_id, service_date)` — sana ham qaytariladi, chunki
        chaqiruvchi uni `payments` bilan MOSLASHTIRISHI kerak va uni
        ikkinchi marta hisoblash ikkinchi manba bo'lardi.
    """
    day = service_date or _safe_service_date(conn)
    charge_id = uuid4()
    conn.execute(
        _INSERT_CHARGE,
        (
            str(charge_id),
            str(market_id),
            str(stall_id),
            str(vendor_id),
            day,
            str(tariff_id),
            TARIFF_SOUM,
            amount_soum,
        ),
    )
    return charge_id, day


def add_charge_evidence(
    conn: Connection[TupleRow], *, market_id: UUID, charge_id: UUID
) -> UUID | None:
    """Hisobning rasm-dalili — ZANJIR BAZADAN olinadi, qayta QURILMAYDI.

    `charge_evidence` `stall_slot_occupancy` (audit havolasi),
    `occupancy_events` (MUZLATILGAN dalil) va `snapshots` (kadrga yo'l)
    ga birdan tayanadi va uchalasi ham BIR XIL bozorga tegishli bo'lishi
    shart — kompozit FK aynan shuni majburlaydi (C-7). Ularni chaqiruvchi
    o'zi qurishga urinsa fixture tekshirilayotgan mexanizmni TAKRORLAGAN
    bo'lardi (§S-9).

    Returns:
        Dalil qatorining `id` si, yoki `None` — bozorda g'olib hodisali
        slot qatori BO'LMASA. `None` — «day_close yugurmagan» holatining
        HALOL javobi va chaqiruvchi undan xulosa chiqarishi kerak.
    """
    row = conn.execute(
        "SELECT s.id, s.slot_time, s.winning_occupancy_event_id, e.snapshot_id "
        "FROM stall_slot_occupancy AS s "
        "JOIN occupancy_events AS e ON e.id = s.winning_occupancy_event_id "
        "WHERE s.market_id = %s "
        "ORDER BY s.id LIMIT 1",
        (str(market_id),),
    ).fetchone()
    if row is None:
        return None

    slot_id, slot_time, event_id, snapshot_id = row
    evidence_id = uuid4()
    conn.execute(
        _INSERT_EVIDENCE,
        (
            str(evidence_id),
            str(market_id),
            str(charge_id),
            str(slot_id),
            str(event_id),
            str(snapshot_id),
            slot_time,
        ),
    )
    return evidence_id


def add_payment(
    conn: Connection[TupleRow],
    *,
    market_id: UUID,
    stall_id: UUID,
    vendor_id: UUID,
    cashier_id: UUID,
    shift_id: UUID | None,
    service_date: date | None = None,
    amount_soum: int = TARIFF_SOUM,
    quote_soum: int = TARIFF_SOUM,
    kind: str = PaymentKind.PAYMENT.value,
    reverses_payment_id: UUID | None = None,
    reversal_reason: str | None = None,
    override_reason: str | None = None,
) -> UUID:
    """Bitta `payments` qatori — STORNO ham shu funksiya orqali yoziladi.

    ⚠ `kind` ARGUMENT va u ATAYIN qattiq yozilmagan: D-23 ning «xato
      yozuv YANGI QATOR bilan qoplanadi» yo'lini o'lchash uchun AYNAN
      shu funksiya `kind='reversal'` bilan ham chaqirilishi kerak.
      Faqat oddiy to'lov yozadigan yordamchi o'sha testni yozib bo'lmas
      qilardi.

    ⚠ `idempotency_key` HAR CHAQIRUVDA YANGI (`uuid4`): `uq_payments_
      market_id_idempotency_key` takroriylikni bloklaydi va sobit kalit
      ikkinchi chaqiruvni seedning o'zida yiqitardi.
    """
    payment_id = uuid4()
    conn.execute(
        _INSERT_PAYMENT,
        (
            str(payment_id),
            str(market_id),
            str(stall_id),
            str(vendor_id),
            service_date or _safe_service_date(conn),
            amount_soum,
            quote_soum,
            kind,
            PaymentMethod.CASH.value,
            None if reverses_payment_id is None else str(reverses_payment_id),
            reversal_reason,
            override_reason,
            f"billing-seed-{payment_id}",
            "billing-seed-fingerprint",
            None if shift_id is None else str(shift_id),
            str(cashier_id),
        ),
    )
    return payment_id
