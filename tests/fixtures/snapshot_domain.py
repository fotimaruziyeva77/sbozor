"""Ikki bozorli snapshot seed'i — `nvr_domain` ustiga qatlanadi.

`fixtures/two_markets.py` bozor + foydalanuvchi + a'zolik qatlamini,
`fixtures/nvr_domain.py` esa NVR + kameralarni beradi. Bu modul ularning
ustiga 4-fazaning snapshot qatlamini qo'yadi: mavsumiy profil, uning
slotlari, bir kunlik `capture_runs` to'plami, olingan kadrlar va ochiq/yopiq
ogohlantirishlar. Ikki bozor qoidasi shu yerda ham amal qiladi va sabab bir
xil: «0 qator qaytdi» javobi izolyatsiya ishlaganini ham, jadval bo'shligini
ham bildirishi mumkin.

=============================================================================
SEED KONTRAKTI — HAR BIR ELEMENT ANIQ BIR TESTNI OZIQLANTIRADI.

  * **Har bozorda BITTA ochiq oxirli profil + YETTI slot.** Slotlar
    `DEFAULT_SNAPSHOT_SLOTS` dan olinadi, qo'lda TAKRORLANMAYDI: agar
    standart ro'yxat o'zgarsa seed ham u bilan birga o'zgaradi va
    `market_activate()` bilan farq qilib qolmaydi.

  * **`period` OCHIQ OXIRLI (`[SEED_BUSINESS_DATE, None)`).** Yopiq davr
    `EXCLUDE` konstraytini umuman sinamasdi — kesishuv testi ikkinchi
    profilni AYNAN shu davrning ustiga yozadi va u ochiq bo'lishi kerak.

  * **A bozorida OLTALA holat ham bor** (`succeeded`, `failed`, `missed`,
    `pending`, `running`, `skipped`). Sanoq bo'yicha filtrlaydigan har bir
    test (hisobot, watchdog, tick) bitta seed bilan ishlaydi va o'z
    qatorini O'ZI yozishi shart emas. Ikkita `succeeded` bor va bu
    ATAYIN — biriga `quality_verdict='ok'`, ikkinchisiga `'dark'` kadr
    biriktiriladi, ya'ni `is_billable` ning IKKALA qiymati ham seedda
    mavjud. Bittasi bo'lsa D-16 ilgagining manfiy tomoni sinalmasdi.

  * **B bozorida FAQAT ikki qator** (`succeeded` + `pending`). Sonlar
    ATAYIN farqli: «bu bozorning rejasi» testi A ni ko'rib B ni
    ko'rmasligini isbotlashi kerak; ikkalasida bir xil son bo'lsa
    noto'g'ri bozorning qatorlari qaytganda ham sanoq mos kelib qolardi.

  * **Har bozorda BITTA ochiq va BITTA yopilgan alert.** Ochiq alertning
    `subject_id` i `NULL` (butun bozorga tegishli) — aynan shu holat
    `uq_alert_events_market_id_alert_key_open` dagi `COALESCE` ni
    sinaydi. Yopilgani esa kameraga bog'langan, ya'ni qisman indeksning
    predikati («yopilganlar qamralmaydi») ham o'lchanadi.

  * **`market_delete_draft()` KASKADI UCHUN: B bozorida ham BESHALA
    jadvalda qator bor.** Cross-tenant nazorati («A o'chdi, B joyida»)
    B da qator BO'LMASA hech nimani o'lchamaydi.
=============================================================================

⚠ `business_date` QO'LDA YOZILMAYDI — u `capture_runs` da hisoblanadigan
ustun (`GENERATED ... STORED`). Seed faqat `scheduled_at` ni beradi va
uni `SEED_BUSINESS_DATE` + slot vaqtidan Asia/Tashkent mintaqasida quradi
(`sbozor_core.timeutil.MARKET_TZ`). Naive `datetime` bu yerda TAQIQLANGAN:
konteyner UTC'da ishlaydi va mahalliy 00:00–04:59 oralig'idagi qiymat
naive sanada OLDINGI kunga tushardi (Pitfall 6).

⚠ SANA QADALGAN, «bugun» EMAS. `date.today()` ishlatilsa testlar yarim
tunda flaky bo'lardi va `06:00` sloti «muddati kelgan» dan «kelmagan» ga
o'z-o'zidan o'tardi. Qadalgan sana bilan har bir da'vo takrorlanadigan
bo'lib qoladi; «hozir»ga bog'liq test kerak bo'lsa u qatorni O'ZI yozadi
(`nvr_domain.add_discovery_run()` bilan bir xil qoida).

UUID'LAR DETERMINISTIK EMAS — HAR CHAQIRUVDA YANGI (`uuid4`).
`two_markets`/`nvr_domain` bilan aynan bir xil qaror va sabab ham bir xil:
bozor UUID'lari har testda yangi, ya'ni qotib qolgan snapshot UUID'i o'sha
bozorlarga bog'lana olmasdi. `object_key` esa `snapshots.market_id` ichida
noyob bo'lishi shart va u kadr UUID'idan quriladi.

Seed `sbozor_owner` autocommit ulanishi bilan yoziladi (`nvr_domain` bilan
bir xil sabab): ma'lumot boshqa ulanishdagi `sbozor_app` testlariga DARHOL
ko'rinishi kerak, va ega `owner_bootstrap` policy'si ostida tenant
kontekstisiz yoza oladi.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime, time
from uuid import UUID, uuid4

from psycopg import Connection
from psycopg.rows import TupleRow
from sbozor_core.enums import (
    AlertSeverity,
    CaptureMethod,
    CaptureRunStatus,
    SnapshotLightMode,
    SnapshotQuality,
)
from sbozor_core.models.snapshot import DEFAULT_SNAPSHOT_SLOTS
from sbozor_core.timeutil import MARKET_TZ

from fixtures.nvr_domain import NvrDomainSeed

__all__ = [
    "A_RUN_PLAN",
    "B_RUN_PLAN",
    "CLEANUP_ORDER",
    "DECODED_HEIGHT",
    "DECODED_WIDTH",
    "OPEN_ALERT_KEY",
    "RESOLVED_ALERT_KEY",
    "SCHEDULE_NAME",
    "SEED_BUSINESS_DATE",
    "MarketSnapshotRows",
    "RunSpec",
    "SnapshotDomainSeed",
    "cleanup_snapshot_domain",
    "scheduled_at_for",
    "seed_snapshot_domain",
    "snapshot_rows",
]

SEED_BUSINESS_DATE = date(2026, 9, 1)
"""Seed rejasining QADALGAN biznes-kuni (modul docstringidagi ikkinchi ⚠).

`2026-09-01` — dushanba, ya'ni `market_profile.open_weekdays` ning har
qanday oqilona standarti ostida ISH KUNI. Yakshanba tanlansa `market_is_open()`
ga tayanadigan testlar seedning o'zidan `false` olardi va «yopiq kunda ham
kadr olinadi» (D-10) da'vosi bilan aralashib ketardi.
"""

SCHEDULE_NAME = "Standart"
"""Profil nomi — `market_activate()` yozadigan nom bilan AYNAN bir xil.

Farqli nom yozish «faollashtirish standart profil yozdimi?» testini
seedning O'Z qatoriga qaratib, uni ma'nosiz qilardi.
"""

OPEN_ALERT_KEY = "capture_missed"
"""Ochiq alertning kaliti — `subject_id` i `NULL` (butun bozorga tegishli)."""

RESOLVED_ALERT_KEY = "camera_offline"
"""Yopilgan alertning kaliti — `subject_id` i kameraga bog'langan."""


@dataclass(frozen=True)
class RunSpec:
    """Bitta `capture_runs` qatorining REJASI (seed yozishdan oldingi ta'rif).

    Alohida tipda, chunki ro'yxatlar (`A_RUN_PLAN`/`B_RUN_PLAN`) modul
    darajasida ochiq turadi: testlar «seedda nechta `missed` bor?» degan
    kutilmani QAYTA HISOBLAMASDAN shu yerdan oladi. Kutilmani test ichida
    hisoblash filtr mantig'ini takrorlardi va ikkalasi birga xato bo'lganda
    test baribir yashil bo'lardi (`nvr_domain.active_camera_ids` bilan bir
    xil qoida).
    """

    camera_index: int
    slot_time: time
    status: str
    quality: str | None = None
    """`succeeded` qatorga biriktiriladigan kadrning verdikti; `None` = kadr yo'q."""


A_RUN_PLAN: tuple[RunSpec, ...] = (
    RunSpec(0, DEFAULT_SNAPSHOT_SLOTS[0], CaptureRunStatus.SUCCEEDED, SnapshotQuality.OK),
    RunSpec(0, DEFAULT_SNAPSHOT_SLOTS[1], CaptureRunStatus.SUCCEEDED, SnapshotQuality.DARK),
    RunSpec(0, DEFAULT_SNAPSHOT_SLOTS[2], CaptureRunStatus.FAILED),
    RunSpec(1, DEFAULT_SNAPSHOT_SLOTS[3], CaptureRunStatus.PENDING),
    RunSpec(1, DEFAULT_SNAPSHOT_SLOTS[4], CaptureRunStatus.RUNNING),
    RunSpec(1, DEFAULT_SNAPSHOT_SLOTS[5], CaptureRunStatus.MISSED),
    RunSpec(1, DEFAULT_SNAPSHOT_SLOTS[6], CaptureRunStatus.SKIPPED),
)
"""A bozorining kunlik rejasi — OLTALA holat ham qamralgan.

Bitta kamera bir slotda BIR MARTA uchraydi: `uq_capture_runs_market_id_
camera_id_business_date_slot_time` aks holda seedning O'ZINI yiqitardi.
Ikkita `succeeded` ATAYIN — `is_billable` ning ikkala qiymati ham kerak.
"""

B_RUN_PLAN: tuple[RunSpec, ...] = (
    RunSpec(0, DEFAULT_SNAPSHOT_SLOTS[0], CaptureRunStatus.SUCCEEDED, SnapshotQuality.OK),
    RunSpec(0, DEFAULT_SNAPSHOT_SLOTS[1], CaptureRunStatus.PENDING),
)
"""B bozorining rejasi — A dan FARQLI SON (modul docstringi).

B ning yagona vazifasi cross-tenant nazorati, ya'ni unga to'liq holat
qamrovi kerak emas. Lekin `snapshots` da ham qator BO'LISHI shart, aks
holda kaskad testi o'sha jadval bo'yicha hech nimani o'lchamasdi.
"""

CLEANUP_ORDER: tuple[str, ...] = (
    "snapshots",
    "capture_runs",
    "snapshot_schedule_slots",
    "snapshot_schedules",
    "alert_events",
)
"""O'CHIRISH TARTIBI — `migrations.entities.SNAPSHOT_DELETE_ORDER` bilan BIR XIL.

Tasodif emas: ikkalasi ham bir xil FK zanjiridan kelib chiqadi (`snapshots`
-> `capture_runs`, `snapshot_schedule_slots` -> `snapshot_schedules`).
`alert_events` zanjirda umuman turmaydi, shuning uchun uning o'rni
ixtiyoriy va oxirida.

⚠ REYESTRDAN IMPORT QILINMAYDI va bu ATAYIN: `tests/fixtures/` `migrations`
paketiga bog'lanmaydi (fixture'lar servis testlarida ham ishlaydi), va
ikkala ro'yxatning MOSLIGI `test_meta.py::
test_snapshot_registries_are_self_consistent` da emas, kaskad testining
O'ZIDA o'lchanadi: noto'g'ri tartib `DELETE` ni FK buzilishi bilan
yiqitadi.
"""

_INSERT_SCHEDULE = (
    "INSERT INTO snapshot_schedules (id, market_id, name, period) "
    "VALUES (%s, %s, %s, daterange(%s, NULL, '[)'))"
)
_INSERT_SLOT = (
    "INSERT INTO snapshot_schedule_slots (id, market_id, schedule_id, slot_time) "
    "VALUES (%s, %s, %s, %s)"
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
_INSERT_ALERT = (
    "INSERT INTO alert_events "
    "(id, market_id, alert_key, severity, subject_id, occurrences, resolved_at) "
    "VALUES (%s, %s, %s, %s, %s, %s, %s)"
)

# Sifat o'lchovlari — `04-04` ning chegaralari bilan MOS, lekin ULARDAN
# IMPORT QILINMAYDI: seed «qanday kadr yozilgan» ni ta'riflaydi, «qoida
# nima» ni emas. Chegaralar o'zgarsa seed o'zgarmasligi kerak, aks holda
# sifat filtrining O'Z testi o'z kirishini o'zi belgilagan bo'lardi.
_QUALITY_METRICS: dict[str, tuple[str, str, str]] = {
    SnapshotQuality.OK: ("112.40", "48.75", SnapshotLightMode.DAY),
    SnapshotQuality.DARK: ("9.20", "2.10", SnapshotLightMode.IR_NIGHT),
}
_THRESHOLDS_VERSION = 1

DECODED_WIDTH = 480
DECODED_HEIGHT = 270
"""Kadr DEKODLANGANDAGI o'lchami — 16:9, `snapshots.width`/`height` ga yoziladi.

=============================================================================
⚠⚠ BU KADRNING HAQIQIY O'LCHAMI EMAS VA ATAYIN SHUNDAY.

Ishlab chiqarishda bu ikki ustunga `quality.py::analyze()` ning
`draft("RGB", (320, 180))` natijasi yoziladi — DCT darajasida
kichraytirilgan dekod. 1920x1080 kadr uchun Pillow 1/4 masshtabni
tanlaydi va natija 480x270 bo'ladi.

Seed AYNAN SHU SINFDAGI qiymatni yozadi, ya'ni «to'liq o'lcham» (1920x1080)
YOZILMAYDI: ustunlarni haqiqiy kadr o'lchami deb to'ldirish keyingi
o'qiyotgan odamni ular shundaydir deb ishontirardi va u ularni
denormalizatsiya (`denormalize()`) uchun ishlatishga urinardi — natija
har koordinatada TO'RT BAROBAR xato bo'lardi.

⚠ QIYMAT `quality.py` DAN IMPORT QILINMAYDI va `_DRAFT_SIZE` dan
  hisoblanmaydi (§S-9): seed «qanday kadr yozilgan» ni ta'riflaydi,
  «dekoder qanday ishlaydi» ni emas. Import qilinsa `draft()` ning nishon
  o'lchami o'zgargan kuni seed jimgina ergashardi va u tekshirilayotgan
  xususiyatning aks-sadosiga aylanardi.

NISBAT 16:9 va u YAGONA MA'NOLI xususiyat: `camera_zones` ning §6.8
darvozasi (`aspect_ratio_matches`) faqat nisbatni so'raydi — absolyut
o'lcham unga umuman kirmaydi.
=============================================================================
"""

_NEVER_ATTEMPTED: frozenset[str] = frozenset(
    {CaptureRunStatus.PENDING, CaptureRunStatus.MISSED, CaptureRunStatus.SKIPPED}
)
"""HECH QACHON urinilmagan holatlar — `attempts = 0` va `capture_method IS NULL`.

⚠ `missed` bu ro'yxatda, `failed` esa YO'Q va bu farq ATAYIN: `missed` =
«bizning tizimimiz ishlamadi» (urinish umuman bo'lmagan), `failed` = «NVR
javob bermadi» (urinish BO'LGAN). Seed bu farqni ifodalamasa dala
diagnostikasi testlari ikkala holatni ham bir xil ko'rardi.
"""


def scheduled_at_for(slot: time, day: date = SEED_BUSINESS_DATE) -> datetime:
    """Slot vaqtini bozor mintaqasidagi `timestamptz` ga aylantiradi.

    `capture_runs.business_date` AYNAN shu qiymatdan hisoblanadi
    (`GENERATED ALWAYS AS ((scheduled_at AT TIME ZONE 'Asia/Tashkent')::date)`),
    ya'ni funksiya seed va kutilma o'rtasidagi YAGONA aylantirish nuqtasi.
    Testlar ham shu yerdan oladi — qo'lda `datetime(...)` qurish ikkinchi
    manba bo'lardi va u yarim tun atrofida farq qilardi.
    """
    return datetime.combine(day, slot, tzinfo=MARKET_TZ)


@dataclass(frozen=True)
class MarketSnapshotRows:
    """Bitta bozorning snapshot qatorlari."""

    market_id: UUID
    schedule_id: UUID
    slot_ids: tuple[UUID, ...]
    run_ids: tuple[UUID, ...]
    snapshot_ids: tuple[UUID, ...]
    open_alert_id: UUID
    resolved_alert_id: UUID
    plan: tuple[RunSpec, ...] = ()

    @property
    def statuses(self) -> tuple[str, ...]:
        """Rejadagi holatlar — TESTLARNING KUTILMASI, hisoblangan qiymat emas.

        Test «seedda nechta `missed` bor?» degan savolga shu yerdan javob
        oladi. Filtr natijasini test ichida qayta hisoblash tekshirilayotgan
        mantiqning nusxasi bo'lardi.
        """
        return tuple(spec.status for spec in self.plan)


@dataclass(frozen=True)
class SnapshotDomainSeed:
    """Ikki bozorning snapshot qatlami."""

    market_a: MarketSnapshotRows
    market_b: MarketSnapshotRows

    @property
    def markets(self) -> tuple[MarketSnapshotRows, MarketSnapshotRows]:
        return (self.market_a, self.market_b)

    @property
    def market_ids(self) -> tuple[UUID, ...]:
        return (self.market_a.market_id, self.market_b.market_id)


def _seed_market_snapshots(
    conn: Connection[TupleRow],
    *,
    market_id: UUID,
    nvr_id: UUID,
    camera_ids: tuple[UUID, ...],
    plan: tuple[RunSpec, ...],
) -> MarketSnapshotRows:
    """Bitta bozorning snapshot qatlamini yozadi."""
    schedule_id = uuid4()
    conn.execute(
        _INSERT_SCHEDULE,
        (str(schedule_id), str(market_id), SCHEDULE_NAME, SEED_BUSINESS_DATE),
    )

    slot_ids: list[UUID] = []
    for slot in DEFAULT_SNAPSHOT_SLOTS:
        slot_id = uuid4()
        conn.execute(_INSERT_SLOT, (str(slot_id), str(market_id), str(schedule_id), slot))
        slot_ids.append(slot_id)

    run_ids: list[UUID] = []
    snapshot_ids: list[UUID] = []
    for spec in plan:
        run_id = uuid4()
        camera_id = camera_ids[spec.camera_index]
        scheduled_at = scheduled_at_for(spec.slot_time)
        # `attempts` holatga MOS: `pending` hech qachon urinilmagan,
        # `missed` ham (bizning tizimimiz ishlamadi), `skipped` ham. Qolgan
        # uchtasi urinilgan. Bir xil qiymat berish «nechta urinish bo'ldi?»
        # savolini seedning o'zida ma'nosiz qilardi.
        attempts = 0 if spec.status in _NEVER_ATTEMPTED else 1
        # `capture_method` — DALIL: faqat urinilgan qator uni to'ldiradi.
        method = None if spec.status in _NEVER_ATTEMPTED else CaptureMethod.GO2RTC.value
        conn.execute(
            _INSERT_RUN,
            (
                str(run_id),
                str(market_id),
                str(camera_id),
                str(nvr_id),
                spec.slot_time,
                scheduled_at,
                spec.status,
                attempts,
                method,
                # Seed ISH KUNINI ifodalaydi (`SEED_BUSINESS_DATE`
                # docstringiga qarang). Yopiq kun holati kerak bo'lgan test
                # qatorni O'ZI yozadi.
                True,
            ),
        )
        run_ids.append(run_id)

        if spec.quality is None:
            continue
        snapshot_id = uuid4()
        mean, stddev, light_mode = _QUALITY_METRICS[spec.quality]
        conn.execute(
            _INSERT_SNAPSHOT,
            (
                str(snapshot_id),
                str(market_id),
                str(run_id),
                str(camera_id),
                scheduled_at,
                # Kadr slotdan ~9 s keyin olindi — `captured_at` va
                # `scheduled_at` ATAYIN farq qiladi, aks holda «kechikish»
                # ni o'lchaydigan har qanday test nolga qarab yashil bo'lardi.
                scheduled_at.replace(second=9),
                spec.slot_time,
                # DETERMINISTIK kalit shakli (04-04 ning jufti), lekin
                # undan IMPORT QILINMAYDI: seed «qanday kalit yozilgan» ni
                # ta'riflaydi, generatorning o'zini emas.
                f"{market_id}/{SEED_BUSINESS_DATE.isoformat()}/{camera_id}/"
                f"{spec.slot_time.strftime('%H%M')}.jpg",
                48_128,
                spec.quality,
                mean,
                stddev,
                _THRESHOLDS_VERSION,
                light_mode,
                CaptureMethod.GO2RTC.value,
                DECODED_WIDTH,
                DECODED_HEIGHT,
            ),
        )
        conn.execute(_LINK_SNAPSHOT, (str(snapshot_id), str(run_id)))
        snapshot_ids.append(snapshot_id)

    # OCHIQ alert: `subject_id` `NULL` — aynan shu holat qisman UNIQUE
    # indeksdagi `COALESCE` ni sinaydi (usiz ikkita `NULL` qator bir vaqtda
    # yashab ketardi va debounce jimgina ishlamasdi).
    open_alert_id = uuid4()
    conn.execute(
        _INSERT_ALERT,
        (
            str(open_alert_id),
            str(market_id),
            OPEN_ALERT_KEY,
            AlertSeverity.WARNING.value,
            None,
            3,
            None,
        ),
    )
    # YOPILGAN alert: indeksning predikati («yopilganlar qamralmaydi») ham
    # o'lchanishi kerak — aks holda ikkinchi ochiq alert testi qisman emas,
    # to'liq indeks bilan ham yashil bo'lardi.
    resolved_alert_id = uuid4()
    conn.execute(
        _INSERT_ALERT,
        (
            str(resolved_alert_id),
            str(market_id),
            RESOLVED_ALERT_KEY,
            AlertSeverity.INFO.value,
            str(camera_ids[0]),
            1,
            scheduled_at_for(DEFAULT_SNAPSHOT_SLOTS[-1]),
        ),
    )

    return MarketSnapshotRows(
        market_id=market_id,
        schedule_id=schedule_id,
        slot_ids=tuple(slot_ids),
        run_ids=tuple(run_ids),
        snapshot_ids=tuple(snapshot_ids),
        open_alert_id=open_alert_id,
        resolved_alert_id=resolved_alert_id,
        plan=plan,
    )


def seed_snapshot_domain(conn: Connection[TupleRow], nvr: NvrDomainSeed) -> SnapshotDomainSeed:
    """`nvr_domain` ustiga snapshot qatlamini yozadi.

    `conn` `sbozor_owner` bilan ochilgan va AUTOCOMMIT rejimida bo'lishi
    kerak — `nvr_domain` bilan aynan bir xil talab.

    ⚠ A bozorining ARXIVLANGAN kamerasi (`nvr_domain` ning uchinchi kanali)
    rejaga KIRMAYDI: `A_RUN_PLAN` faqat `camera_index` 0 va 1 ni
    ishlatadi. D-10 ning soft-delete'i aynan shuni talab qiladi —
    arxivlangan kanaldan kadr olinmaydi, lekin uning tarixi qoladi.
    """
    market_a = _seed_market_snapshots(
        conn,
        market_id=nvr.market_a.market_id,
        nvr_id=nvr.market_a.nvr_id,
        camera_ids=nvr.market_a.active_camera_ids,
        plan=A_RUN_PLAN,
    )
    market_b = _seed_market_snapshots(
        conn,
        market_id=nvr.market_b.market_id,
        nvr_id=nvr.market_b.nvr_id,
        camera_ids=nvr.market_b.active_camera_ids,
        plan=B_RUN_PLAN,
    )
    return SnapshotDomainSeed(market_a=market_a, market_b=market_b)


def cleanup_snapshot_domain(conn: Connection[TupleRow], seed: SnapshotDomainSeed) -> None:
    """Snapshot qatlamini FK tartibida o'chiradi.

    ⚠ `capture_runs.snapshot_id` FK EMAS, ya'ni u tozalash tartibiga
    ta'sir qilmaydi — `snapshots` birinchi o'chiriladi va qolgan havola
    jimgina osilib turmaydi, chunki qator ham darhol ketadi.
    """
    market_ids = [str(market_id) for market_id in seed.market_ids]

    for table in CLEANUP_ORDER:
        # Jadval nomlari shu moduldagi SOBIT `CLEANUP_ORDER` dan keladi —
        # tashqi kirish emas, ya'ni f-string bu yerda xavfsiz
        # (`nvr_domain.py` dagi jufti bilan bir xil naqsh).
        conn.execute(
            f"DELETE FROM {table} WHERE market_id = ANY(%s::uuid[])",  # noqa: S608
            (market_ids,),
        )


@contextmanager
def snapshot_rows(conn: Connection[TupleRow], nvr: NvrDomainSeed) -> Iterator[SnapshotDomainSeed]:
    """`seed_snapshot_domain()` + kafolatlangan tozalash — `with` bloki uchun.

    ATAYIN pytest fixture EMAS, `contextmanager` (`nvr_domain.nvr_rows()`
    bilan bir xil naqsh va bir xil sabab): fixture `tests/conftest.py` da
    yashashi kerak bo'lardi, o'sha faylni esa boshqa rejalar ham tahrirlaydi.

    ⚠ TOZALASH BLOK O'CHIRILGAN BOZOR USTIDA HAM XAVFSIZ:
    `market_delete_draft()` ni sinaydigan test bozorni butunlay o'chiradi va
    o'shanda `DELETE ... WHERE market_id = ...` shunchaki 0 qatorga tegadi.

    ⚠ TARTIB MUHIM: bu kontekst menejeri `nvr_rows(...)` NING ICHIDA
    ishlatiladi. Teskari joylashuv `nvr_domain` ning tozalashini `cameras`
    ga hali `capture_runs` tayanib turgan paytda ishga tushirardi va u FK
    buzilishi bilan yiqilardi.
    """
    seed = seed_snapshot_domain(conn, nvr)
    try:
        yield seed
    finally:
        cleanup_snapshot_domain(conn, seed)
