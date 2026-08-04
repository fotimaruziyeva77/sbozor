"""Snapshot quvuri: mavsumiy jadval, kunlik reja, kadr va ogohlantirish.

=============================================================================
BU FAYLDA UCHTA KAFOLAT YASHAYDI VA UCHALASI HAM KODDA EMAS, SXEMADA.
Ular "qulaylik uchun" buzilishi oson, shuning uchun sabablari shu yerda.

1. `UNIQUE (market_id, camera_id, business_date, slot_time)` — CAM-05 ning
   IDEMPOTENTLIGI. Ilova qatlami bunga TAYANADI, uni TAKRORLAMAYDI: tick
   `ON CONFLICT DO NOTHING` bilan yozadi va poygani DB'ga topshiradi.
   "Avval tekshir, keyin yoz" naqshi ikki parallel tikda ikkalasini ham
   o'tkazib yuborardi (T-04-18).

2. `EXCLUDE USING gist (market_id WITH =, period WITH &&)` — «bir kunga
   AYNAN bitta profil». Ikki kesishuvchi profil bir kunga ikki xil slot
   to'plamini berardi va «ertasi kuni aynan o'sha slotlarda» (SC#1)
   da'vosi ma'nosini yo'qotardi (T-04-19).

3. `UNIQUE (id, is_billable)` — 5-FAZA UCHUN ILGAK (D-16). Bu jadvaldagi
   YAGONA konstrayt bo'lib, u BOSHQA FAZA uchun mavjud: `occupancy_events`
   `(snapshot_id, snapshot_is_billable)` juftligiga kompozit FK qo'yadi va
   `CHECK (snapshot_is_billable)` bilan birga yaroqsiz kadrga bandlik
   dalilini bog'lashni IMKONSIZ qiladi. Kafolat KELISHUV emas, DB RAD
   ETISHI (T-04-17).
=============================================================================

BESHALA JADVAL HAM TENANT JADVALI (`04-PATTERNS.md` §S-1): `market_id` +
RLS `ENABLE` va `FORCE` + tenant policy + `market_id` bilan boshlanuvchi
domen konstraytlari + kompozit FK. `market_id` ustunida inline `ForeignKey`
YOZILMAYDI — sabab `models/base.py::market_fk_column()` docstringida.

⚠ PG `ENUM` TIPI ISHLATILMAYDI. Ustunlar `text` + enum'dan HOSILA `CHECK`
ifodasi (`models/nvr.py:104-117` naqshi). Sabab ikkita va ikkalasi ham
amaliy: (a) PG enum tipiga qiymat qo'shish tranzaksiya ichida bajarilmaydi
va har safar alohida migratsiya nayrangini talab qiladi; (b) loyihada
`cameras.status`, `nvr_discovery_runs.status` va `stalls.status`
uchalasi ham allaqachon `text`+`CHECK` — yangi shakl kiritish IKKINCHI
konventsiya yaratardi. `04-RESEARCH.md` §A.2/§B.4 dagi sxema eskizlari PG
tipini ko'rsatadi, lekin loyiha konventsiyasi ustun.

AUDIT ASSIMETRIYASI (`schema_contract.AUDITED_TABLES`): trigger FAQAT
`snapshot_schedules` va `snapshot_schedule_slots` ga ulanadi. `capture_runs`,
`snapshots` va `alert_events` — HODISA JURNALLARI: ular faqat qo'shiladi va
o'z ustunlarida tarixga ega, ya'ni audit ularning ikkinchi nusxasini
yozardi (kuniga ~525 qator BITTA bozordan).
"""

from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Computed,
    Date,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    Text,
    Time,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import DATERANGE, JSONB, ExcludeConstraint, Range
from sqlalchemy.dialects.postgresql import UUID as PgUuid
from sqlalchemy.orm import Mapped, mapped_column

from sbozor_core.enums import (
    AlertSeverity,
    CaptureMethod,
    CaptureRunStatus,
    SnapshotLightMode,
    SnapshotQuality,
    SnapshotTier,
)
from sbozor_core.models.base import Base, TenantMixin, TimestampMixin, uuid_pk

__all__ = [
    "ALERT_OPEN_INDEX",
    "ALERT_OPEN_PREDICATE",
    "ALERT_SEVERITY_CHECK",
    "ALERT_SEVERITY_VALUES",
    "CAPTURE_BUSINESS_DATE_EXPR",
    "CAPTURE_DUE_INDEX",
    "CAPTURE_DUE_PREDICATE",
    "CAPTURE_METHOD_CHECK",
    "CAPTURE_METHOD_VALUES",
    "CAPTURE_OVERDUE_INDEX",
    "CAPTURE_OVERDUE_PREDICATE",
    "CAPTURE_RUN_ACTIVE_STATUSES",
    "CAPTURE_RUN_STATUS_CHECK",
    "CAPTURE_RUN_STATUS_VALUES",
    "DEFAULT_SNAPSHOT_SLOTS",
    "SNAPSHOT_BUSINESS_DATE_EXPR",
    "SNAPSHOT_LIGHT_MODE_CHECK",
    "SNAPSHOT_LIGHT_MODE_VALUES",
    "SNAPSHOT_QUALITY_CHECK",
    "SNAPSHOT_QUALITY_VALUES",
    "SNAPSHOT_TIER_CHECK",
    "SNAPSHOT_TIER_VALUES",
    "AlertEvent",
    "CaptureRun",
    "Snapshot",
    "SnapshotSchedule",
    "SnapshotScheduleSlot",
]

CAPTURE_RUN_STATUS_VALUES: tuple[str, ...] = tuple(status.value for status in CaptureRunStatus)
SNAPSHOT_QUALITY_VALUES: tuple[str, ...] = tuple(verdict.value for verdict in SnapshotQuality)
SNAPSHOT_LIGHT_MODE_VALUES: tuple[str, ...] = tuple(mode.value for mode in SnapshotLightMode)
SNAPSHOT_TIER_VALUES: tuple[str, ...] = tuple(tier.value for tier in SnapshotTier)
ALERT_SEVERITY_VALUES: tuple[str, ...] = tuple(level.value for level in AlertSeverity)
CAPTURE_METHOD_VALUES: tuple[str, ...] = tuple(method.value for method in CaptureMethod)

CAPTURE_RUN_ACTIVE_STATUSES: tuple[str, ...] = (
    CaptureRunStatus.PENDING.value,
    CaptureRunStatus.RUNNING.value,
)
"""Watchdog «osilib qolgan» deb hisoblaydigan holatlar to'plami (FOUND-06).

`0014_snapshot_domain` dagi `ix_capture_runs_overdue` indeksining predikati
AYNAN shu ro'yxatdan hosil qilinadi, qo'lda ko'chirilmaydi — bu
`DISCOVERY_RUN_ACTIVE_STATUSES` (`models/nvr.py:83-93`) bilan bir xil qoida
va bir xil sabab: ikki nusxa ajralib ketganda indeks jimgina KAM holatni
qamrar, watchdog esa o'sha holatdagi qatorlarni umuman ko'rmasdi.

Bu yerda narxi 3-fazadagidan ham qimmat: ko'rinmagan `running` qator
`missed` ham, `failed` ham bo'lmaydi — u MANGU `running` bo'lib qoladi va
o'sha slot uchun na kadr, na alert, na hisobot qatori bo'ladi. Ya'ni
nosozlik JIMGINA (D-20 aynan shuni taqiqlaydi).
"""


def _quoted(values: tuple[str, ...]) -> str:
    """SQL literal ro'yxati. Qiymatlar `StrEnum` a'zolari — tashqi kirish emas.

    `market.py`, `identity.py` va `nvr.py` dagi jufti bilan bir xil ikki
    qatorli funksiya va u ATAYIN to'rtinchi marta takrorlanadi: umumiy
    modulga chiqarish `models/base.py` ning ommaviy yuzasini kengaytirardi,
    har bir chaqiruvchi esa baribir O'Z enum'i bilan qulflangan.
    """
    return ", ".join(f"'{value}'" for value in values)


CAPTURE_RUN_STATUS_CHECK = f"status IN ({_quoted(CAPTURE_RUN_STATUS_VALUES)})"
"""`capture_runs.status` faqat ma'lum holatlardan biri (ifoda enum'dan HOSILA)."""

SNAPSHOT_QUALITY_CHECK = f"quality_verdict IN ({_quoted(SNAPSHOT_QUALITY_VALUES)})"
"""`snapshots.quality_verdict` faqat ma'lum verdiktlardan biri (enum'dan HOSILA)."""

SNAPSHOT_LIGHT_MODE_CHECK = f"light_mode IN ({_quoted(SNAPSHOT_LIGHT_MODE_VALUES)})"
"""`snapshots.light_mode` faqat ma'lum rejimlardan biri (enum'dan HOSILA)."""

SNAPSHOT_TIER_CHECK = f"storage_tier IN ({_quoted(SNAPSHOT_TIER_VALUES)})"
"""`snapshots.storage_tier` faqat ma'lum qatlamlardan biri (enum'dan HOSILA)."""

ALERT_SEVERITY_CHECK = f"severity IN ({_quoted(ALERT_SEVERITY_VALUES)})"
"""`alert_events.severity` faqat ma'lum darajalardan biri (enum'dan HOSILA)."""

CAPTURE_METHOD_CHECK = f"capture_method IN ({_quoted(CAPTURE_METHOD_VALUES)})"
"""Kadr olish yo'li — UCH JADVALDA bir xil ifoda (enum'dan HOSILA).

`nvr_devices.capture_method` (SOZLAMA), `capture_runs.capture_method` va
`snapshots.capture_method` (DALIL) — uchalasi ham shu konstantadan oladi.

⚠ NULLABLE USTUNDA HAM SHU AYNAN IFODA ISHLAYDI va bunga alohida
`IS NULL OR ...` shoxi KERAK EMAS: Postgres'da `NULL IN (...)` natijasi
`NULL` bo'ladi, `CHECK` esa `FALSE` da rad etadi, `NULL` da EMAS. Ya'ni
`capture_runs.capture_method` hali noma'lum bo'lganda (`pending` qator)
konstrayt jimgina o'tkazadi. `cameras.status` da ham aynan shu shakl
ishlatilgan (u yerda ustun `NOT NULL`).
"""

CAPTURE_DUE_PREDICATE = f"status = '{CaptureRunStatus.PENDING.value}'"
"""«Muddati kelgan ish» indeksining predikati — enum a'zosidan HOSILA."""

CAPTURE_OVERDUE_PREDICATE = f"status IN ({_quoted(CAPTURE_RUN_ACTIVE_STATUSES)})"
"""Watchdog indeksining predikati — `CAPTURE_RUN_ACTIVE_STATUSES` dan HOSILA."""

ALERT_OPEN_PREDICATE = "resolved_at IS NULL"
"""«Ochiq alert» — yopilmagan ish. Yopilganlar debounce indeksiga tushmaydi."""


# ===========================================================================
# QISMAN INDEKS NOMLARI — MODEL VA MIGRATSIYA UCHUN YAGONA MANBA
# ===========================================================================
#
# ⚠ NEGA INDEKSLAR MODELDA HAM E'LON QILINADI (o'lchangan, 03-03):
# `op.create_index(...)` yolg'iz o'zi yetarli EMAS. Alembic autogenerate
# model metadata'sini baza bilan solishtiradi va modelda e'lon qilinmagan
# indeksni "o'chirilgan" deb hisoblaydi — `test_autogenerate_is_empty`
# uchta `remove_index` bilan QIZARDI. Ya'ni migratsiyada indeks yaratish
# uni sxemaga qo'shadi, LEKIN keyingi `alembic revision --autogenerate`
# uni O'CHIRISHNI taklif qilardi va kimdir buni "tozalash" deb qabul
# qilishi mumkin edi.
#
# Nomlar va predikatlar shu yerda, ikkala tomon (model `Index(...)` va
# `0014_snapshot_domain`) SHU KONSTANTALARDAN oladi — literal takrorlanmaydi.

CAPTURE_DUE_INDEX = "ix_capture_runs_market_id_scheduled_at_due"
CAPTURE_OVERDUE_INDEX = "ix_capture_runs_overdue"
ALERT_OPEN_INDEX = "uq_alert_events_market_id_alert_key_open"

ALERT_OPEN_EXPR = "COALESCE(subject_id, '00000000-0000-0000-0000-000000000000'::uuid)"
"""Ochiq alert indeksining UCHINCHI kalit ifodasi — `COALESCE` MAJBURIY.

⚠ SABAB: UNIQUE indeksda `NULL` O'ZIGA TENG EMAS. `subject_id` butun
bozorga tegishli alertlar uchun `NULL` bo'ladi («kadr olish umuman
ishlamadi»), va `COALESCE` siz bir xil `(market_id, alert_key)` juftligi
uchun ISTALGANCHA ochiq qator yashab ketardi — ya'ni debounce (D-22)
jimgina ishlamasdi va operator har daqiqada bir xil xabarni olardi.

Nol UUID sentinel sifatida ishlatiladi: u `uuidv7()` dan hech qachon
chiqmaydi, ya'ni haqiqiy `subject_id` bilan to'qnashmaydi.
"""


CAPTURE_BUSINESS_DATE_EXPR = "((scheduled_at AT TIME ZONE 'Asia/Tashkent')::date)"
"""`capture_runs.business_date` generated column ifodasi.

UCH FAKT, UCHALASI HAM MAJBURIY:

**(a) `migrations/helpers.py::BUSINESS_DATE_EXPR` bilan SHAKL jihatidan
bir xil, USTUNI esa BOSHQA.** Nusxa bo'lishining sababi bog'liqlik
yo'nalishi: `migrations.helpers` `alembic.op` ni import qiladi,
`sbozor_core` esa migratsiya vositalariga bog'lanmaydi (u uchala servisda
ishlaydi) — `models/market.py::TARIFF_BUSINESS_DATE_EXPR` bilan bir xil
qaror.

**(b) `created_at` EMAS, `scheduled_at`.** Reja qatori o'zi tegishli
bo'lgan kundan OLDIN yaratiladi (kunning birinchi tikida, ya'ni 00:00–00:05
oynasida). `created_at` ga tayanish o'sha oynada yozilgan qatorni OLDINGI
kunga tushirardi va 06:00 sloti kechagi hisobotga tushib qolardi. Bu
1-fazadagi moliyaviy shakldan ATAYIN farq qiladi: u yerda qator hodisa
sodir bo'lgan payt yoziladi, bu yerda esa qator hodisadan OLDIN yoziladi.

**(c) Mintaqa LITERAL, `markets.timezone` EMAS.** `GENERATED ... STORED`
ifodasi `IMMUTABLE` bo'lishi shart va boshqa jadvaldan o'qiy olmaydi
(`migrations/helpers.py::financial_guards()` da hujjatlashtirilgan
cheklov). Natijada assimetriya paydo bo'ladi — `scheduled_at` bozorning
O'Z mintaqasidan hisoblanadi, `business_date` esa literaldan — va u
`tests/tenancy/test_meta.py::test_markets_all_use_tashkent_timezone`
bilan QO'RIQLANADI: ikkinchi mintaqadagi bozor qo'shilgan kuni test
qizaradi va qaror ATAYIN qabul qilinadi.

IKKI ARGUMENTLI `AT TIME ZONE` shakli MAJBURIY: u IMMUTABLE, bitta
argumentli varianti esa STABLE va generated column'da umuman ruxsat
etilmaydi.
"""

SNAPSHOT_BUSINESS_DATE_EXPR = CAPTURE_BUSINESS_DATE_EXPR
"""`snapshots.business_date` — `capture_runs` niki bilan AYNAN BIR XIL ifoda.

⚠ ALIAS, NUSXA EMAS — VA BU ATAYIN. Ikki mustaqil literal yozilsa ular
ajralib ketishi mumkin edi, va nosozlik shakli o'ta yomon bo'lardi: yarim
tunga yaqin olingan kadr `capture_runs` da bir kunga, `snapshots` da esa
BOSHQA kunga tushardi. 6-faza dalilni `business_date` bo'yicha izlaydi,
ya'ni o'sha kadr hisobda «yo'q» bo'lib qolardi (Pitfall 3).

Kafolatning ikkinchi yarmi ma'lumot tomonida: `snapshots.scheduled_at`
`capture_runs.scheduled_at` dan NUSXALANADI, mustaqil hisoblanmaydi. Bir
xil ifoda + bir xil kirish = bir xil natija. Uchinchi yarmi esa
`tests/tenancy/test_snapshot_domain_meta.py` da: ikkala ifoda
`pg_get_expr()` dan o'qilib TENGLIKKA solishtiriladi.
"""


DEFAULT_SNAPSHOT_SLOTS: tuple[time, ...] = (
    time(6, 0),
    time(6, 30),
    time(7, 0),
    time(7, 30),
    time(8, 0),
    time(16, 0),
    time(18, 0),
)
"""Standart profilning YETTI sloti (D-01) — YAGONA manba.

⚠ ADMIN HECH NIMA KIRITMAYDI. Bozor faollashtirilganda `market_activate()`
bitta ochiq oxirli profil («Standart») va AYNAN shu yetti slotni yozadi;
`0015_market_delete_snapshots` esa mavjud FAOL bozorlarga backfill qiladi.
Bu self-service qoidasining bevosita natijasi: usta oqimiga yangi qadam
QO'SHILMAYDI (`04-UI-SPEC.md` §4.9 — u `completedStepCount` ni buzardi).

⚠ RO'YXAT ORALIQ SIFATIDA SAQLANMAYDI. «06:00–08:00 har 30 daqiqada»
ko'rinishidagi oraliq + yakka vaqtlar (`16:00`, `18:00`) ikkita shakl
bo'lardi va sxemada ikkita kod yo'lini tug'dirardi. Oraliqni UI
kengaytiradi (generator tugmasi), baza esa FAQAT tekis ro'yxatni ko'radi
(`04-RESEARCH.md` §A.1).

`market_activate()` ning SQL tanasi shu tuple'dan QURILADI (`PGFunction`
ta'rifi Python satri), ya'ni literal qo'lda takrorlanmaydi va ro'yxatni
o'zgartirish ikkala tomonni birdan yangilaydi.
"""


class SnapshotSchedule(Base, TenantMixin, TimestampMixin):
    """Mavsumiy kadr-olish profili — «bir kunga AYNAN bitta» (CAM-04).

    =========================================================================
    `EXCLUDE USING gist` — BU JADVALNING BUTUN MAZMUNI (T-04-19).

    Ilova qatlamidagi «avval kesishuvni tekshir, keyin yoz» IKKI PARALLEL
    so'rovda ikkalasini ham o'tkazib yuborardi (ikkalasi ham bo'sh holatni
    ko'radi) va bir kunga IKKI XIL slot to'plami paydo bo'lardi.
    Materializatsiya esa qaysi biriga tayanishni tasodifga qoldirardi —
    ya'ni «ertasi kuni AYNAN o'sha slotlarda» (SC#1) da'vosi tekshirib
    bo'lmaydigan holga kelardi. `EXCLUDE` atomik va xom SQL yo'lini ham
    qamraydi; buzilganda SQLSTATE `23P01`.

    ⚠ ALEMBIC `ExcludeConstraint` NI KO'RMAYDI — IKKI TOMONLAMA (empirik,
    `0009_vendors.py:29-40`): model va DB bir xil bo'lganda diff bo'sh,
    LEKIN konstrayt modeldan OLIB TASHLANGANDA HAM diff bo'sh. Ya'ni bu
    e'lon migratsiyaga O'ZI ko'chmaydi va uning YO'QOLGANI ham sezilmaydi.
    Shuning uchun u `0014` da LITERAL yoziladi va mavjudligi
    `tests/tenancy/test_snapshot_domain_meta.py` bilan alohida qulflanadi.
    `btree_gist` kengaytmasi shart (`uuid` ning GiST tenglik operator
    klassi aynan undan keladi) — migratsiya `require_extension(...)` bilan
    boshlanadi.
    =========================================================================

    MAVSUMIYLIK AMALDA: `EXCLUDE` kesishishni taqiqlagani uchun «qishki
    profil qo'shish» — 2-fazadagi tarif qo'shish bilan BIR XIL amal:
    mavjud ochiq oxirli profil BO'LINADI. Bo'shliq (qoplanmagan kun) ATAYIN
    mumkin — o'sha kunga umuman slot yo'q, ya'ni kadr olinmaydi. Bu xato
    emas (mavsumiy yopiladigan bozor), lekin u UI'da KO'RINISHI shart
    («keyingi 90 kunda 12 kun qoplanmagan»), aks holda bu jim ma'lumot
    yo'qotish bo'lardi.

    JADVAL AUDIT OSTIDA (`AUDITED_TABLES`): slotni olib tashlash — nazoratni
    JIMGINA o'chirishning eng arzon yo'li. O'sha vaqtdagi «band, lekin
    to'lovsiz» dalili UMUMAN tug'ilmaydi va hisobot kamaygani bilinmaydi.
    """

    __tablename__ = "snapshot_schedules"
    __table_args__ = (
        ForeignKeyConstraint(
            ["market_id"], ["markets.id"], name="fk_snapshot_schedules_market_id_markets"
        ),
        # Kompozit FK NISHONI: `snapshot_schedule_slots` `(market_id,
        # schedule_id)` ga havola qiladi, ya'ni A bozorining sloti B
        # bozorining profiliga bog'lana OLMAYDI — bu RLS emas, SXEMA
        # darajasidagi kafolat.
        UniqueConstraint("market_id", "id", name="uq_snapshot_schedules_market_id_id"),
        ExcludeConstraint(
            ("market_id", "="),
            ("period", "&&"),
            name="ex_snapshot_schedules_no_overlap",
            using="gist",
        ),
        # BO'SH davr (`[a, a)`) `&&` bilan HECH NIMA bilan kesishmaydi, ya'ni
        # `EXCLUDE` uni to'xtatmaydi va jadvalda «mavjud, lekin hech qaysi
        # kunda amal qilmaydigan» fantom profil paydo bo'lardi — admin uni
        # ko'rardi, materializatsiya esa hech qachon ishlatmasdi.
        CheckConstraint("NOT isempty(period)", name="period_not_empty"),
        # Nomsiz profil jadval sahifasida «qaysi mavsum?» savoliga javob
        # bermaydi va ikkita profilni ajratib bo'lmaydi (`zones.name_not_blank`
        # bilan bir xil sabab).
        CheckConstraint("length(btrim(name)) > 0", name="name_not_blank"),
    )

    id: Mapped[UUID] = uuid_pk()
    # Admin yozadi: «Standart», «Yozgi», «Qishki». Standart profilning nomi
    # `market_activate()` da qadalgan va u DB KONTENTI — UI uni tarjima
    # QILMAYDI (`StallStatus` bilan bir xil qoida).
    name: Mapped[str] = mapped_column(Text(), nullable=False)
    # HAR DOIM `[)` chegarasi (`sbozor_core.periods.PERIOD_BOUNDS`) —
    # loyihadagi YAGONA konventsiya. Yuqori chegara `NULL` bo'lishi mumkin
    # («hozircha amaldagi profil»), quyi chegara esa `NOT NULL` bo'lishi
    # `isempty` CHECK'i bilan bevosita majburlanmaydi, lekin ochiq quyi
    # chegara «abadiy o'tmishdan beri» degani bo'lardi va uni admin
    # kiritolmaydi (API `starts_on` ni majburiy qiladi).
    period: Mapped[Range[date]] = mapped_column(DATERANGE(), nullable=False)


class SnapshotScheduleSlot(Base, TenantMixin):
    """Profilning aniq vaqti — `06:00`, `06:30`, … (CAM-04).

    `time`, `timetz` EMAS va bu ATAYIN: slot — MAHALLIY DEVOR-SOATI.
    «06:00» har bozorda o'zining mahalliy soati bo'lishi kerak va
    materializatsiya uni `((:business_date + slot_time) AT TIME ZONE
    m.timezone)` bilan `timestamptz` ga aylantiradi. `timetz` esa vaqtga
    QADALGAN ofset biriktiradi — PostgreSQL hujjatining o'zi bu tipni
    «kamdan-kam foydali» deb belgilagan va u mintaqa o'zgarganda noto'g'ri
    natija berardi.

    `TimestampMixin` YO'Q: slot — profilning tarkibiy qismi, mustaqil hayot
    sikliga ega emas. «Qachon o'zgartirildi» savoliga audit jurnali javob
    beradi (jadval `AUDITED_TABLES` da), ikkinchi vaqt juftligi esa faqat
    chalkashlik qo'shardi (`StallAssignment` bilan bir xil qoida).

    `ON DELETE CASCADE` FAQAT SHU YERDA: profil o'chirilsa slotlari ketadi.
    ⚠ `capture_runs` ga kaskad YO'Q va bo'lmasligi ham kerak — o'tmishdagi
    dalil jadval o'zgarishidan OMON QOLISHI shart (`04-RESEARCH.md` §A.1).
    """

    __tablename__ = "snapshot_schedule_slots"
    __table_args__ = (
        ForeignKeyConstraint(
            ["market_id"], ["markets.id"], name="fk_snapshot_schedule_slots_market_id_markets"
        ),
        # ⚠ NOM QO'LDA BERILGAN, konvensiyadan HOSILA EMAS. Konvensiya
        #   (`fk_%(table_name)s_%(column_0_N_name)s_%(referred_table_name)s`)
        #   67 belgilik nom berardi, PostgreSQL esa identifikatorni 63
        #   baytga JIMGINA kesadi — natijada model metadata'sidagi nom va
        #   bazadagi nom farq qilib, `alembic check` har safar soxta diff
        #   berardi.
        ForeignKeyConstraint(
            ["market_id", "schedule_id"],
            ["snapshot_schedules.market_id", "snapshot_schedules.id"],
            name="fk_snapshot_schedule_slots_schedule",
            ondelete="CASCADE",
        ),
        UniqueConstraint("market_id", "id", name="uq_snapshot_schedule_slots_market_id_id"),
        # Bir profilda bir vaqt IKKI MARTA bo'lolmaydi: dublikat slot o'sha
        # kamera uchun ikkita `capture_runs` qatorini talab qilardi va
        # `uq_capture_runs_...` ni buzardi — ya'ni materializatsiya butun
        # bozor uchun yiqilardi. `market_id` bilan BOSHLANADI (tenant
        # invarianti #5).
        UniqueConstraint(
            "market_id",
            "schedule_id",
            "slot_time",
            name="uq_snapshot_schedule_slots_market_id_schedule_id_slot_time",
        ),
    )

    id: Mapped[UUID] = uuid_pk()
    schedule_id: Mapped[UUID] = mapped_column(PgUuid(as_uuid=True), nullable=False)
    slot_time: Mapped[time] = mapped_column(Time(timezone=False), nullable=False)


class CaptureRun(Base, TenantMixin):
    """Kunlik rejaning BITTA sloti — «yo'qlik» ni ko'rinadigan qiladigan qator.

    =========================================================================
    MATERIALIZATSIYA MAJBURIY VA BU FAZANING MARKAZIY QARORI (D-20).

    Yo'qlik HODISA QOLDIRMAYDI. «Ishladi va yiqildi» oson aniqlanadi —
    `status='failed'` va `error_code` bor. «Umuman ishlamadi» esa FAQAT
    kutilgan qator OLDINDAN yozilgan bo'lsa aniqlanadi. Shuning uchun kun
    boshida 25 kamera × 7 slot = 175 qator `pending` holatida YOZILADI va
    watchdog «muddati o'tgan, hamon `pending`» qatorlarni `missed` qiladi.

    Bu «alert-on-absence» ni «alert-on-state» ga aylantiradigan YAGONA
    qadam. Usiz planer o'lik bo'lgan daqiqadagi slot hech qayerda iz
    qoldirmasdi: navbatda ish yo'q, jurnalda yozuv yo'q, alert yo'q.
    =========================================================================

    JADVAL AUDIT TRIGGERIDAN CHIQARILGAN — IKKI MUSTAQIL SABAB:
      (a) u HODISA JURNALI va faqat qo'shiladi; holat o'tishlari ustunlarning
          O'ZIDA (`status`, `attempts`, `error_code`, vaqt tamg'alari);
      (b) HAJM: har holat o'tishi audit qatori berardi — 175 qator × 3 o'tish
          ≈ kuniga 525 qator BITTA bozordan, o'nta bozorda yiliga ~1.9 mln.
          `audit_log` append-only, ya'ni u hech qachon kichraymaydi.

    ⚠ `nvr_id` — DENORMALIZATSIYA, IDENTIFIKATSIYA EMAS. U idempotentlik
    kalitida ATAYIN YO'Q (`04-RESEARCH.md` §B.4): kamera boshqa NVR'ga
    ko'chirilsa (kanal ko'chirildi, qurilma almashtirildi) tarixdagi
    slotlarning identifikatori O'ZGARMASLIGI kerak — aks holda o'sha kun
    uchun IKKINCHI qator tug'ilib, bitta slot ikki marta hisoblanardi.
    Ustunning o'z vazifasi boshqa: fan-out `nvr_id` bo'yicha GURUHLANADI,
    chunki konkurentlik chegarasi NVR ga tegishli (D-04/D-08).
    `models/nvr.py::NvrDevice.serial_number` bilan bir xil qaror sinfi.

    ⚠ `snapshot_id` DA FK YO'Q va bu ATAYIN: `snapshots` bu jadvalga
    kompozit FK bilan tayanadi, teskari FK esa TSIKL yaratardi va ikkala
    jadvalni ham bir tranzaksiyada yozishga majburlardi. Bog'lanish YAGONA
    yo'nalishda qulflangan (`uq_snapshots_market_id_capture_run_id`), bu
    ustun esa faqat tez havola.
    """

    __tablename__ = "capture_runs"
    __table_args__ = (
        ForeignKeyConstraint(
            ["market_id"], ["markets.id"], name="fk_capture_runs_market_id_markets"
        ),
        ForeignKeyConstraint(
            ["market_id", "camera_id"],
            ["cameras.market_id", "cameras.id"],
            name="fk_capture_runs_market_id_camera_id_cameras",
        ),
        ForeignKeyConstraint(
            ["market_id", "nvr_id"],
            ["nvr_devices.market_id", "nvr_devices.id"],
            name="fk_capture_runs_market_id_nvr_id_nvr_devices",
        ),
        # ⚠ CAM-05 NING YAGONA DB KAFOLATI (T-04-18).
        #
        #   Ilova qatlami bunga TAYANADI, uni TAKRORLAMAYDI: tick
        #   `ON CONFLICT DO NOTHING` bilan yozadi. Ikki parallel tik
        #   («planer qayta ko'tarildi va tickni takrorladi» — taskiq'ning
        #   hujjatlashtirilgan yiqilish rejimi) «avval tekshir, keyin yoz»
        #   naqshida ikkalasi ham bo'sh holatni ko'rardi va bitta slot
        #   uchun IKKITA qator tug'ilardi. 6-fazada bu bitta kunni ikki
        #   marta hisoblash degani.
        #
        #   `business_date` KALITGA KIRADI, `scheduled_at` esa KIRMAYDI:
        #   ikkinchisi `timestamptz` va u yarim tun atrofida bir xil
        #   biznes-kunning ikki xil qiymati bo'lishi mumkin edi.
        #
        #   `market_id` BIRINCHI — tenant invarianti #5.
        #   Buzilganda SQLSTATE `23505`.
        UniqueConstraint(
            "market_id",
            "camera_id",
            "business_date",
            "slot_time",
            name="uq_capture_runs_market_id_camera_id_business_date_slot_time",
        ),
        # Kompozit FK NISHONI: `snapshots` `(market_id, capture_run_id)` ga
        # havola qiladi.
        UniqueConstraint("market_id", "id", name="uq_capture_runs_market_id_id"),
        CheckConstraint(CAPTURE_RUN_STATUS_CHECK, name="status_allowed"),
        CheckConstraint(CAPTURE_METHOD_CHECK, name="capture_method_allowed"),
        CheckConstraint("attempts >= 0", name="attempts_non_negative"),
        # Manfiy davomiylik SC#3 dagi «sekin NVR» o'lchovini ma'nosiz
        # qilardi (`nvr_discovery_runs.finished_after_started` bilan bir xil).
        CheckConstraint(
            "finished_at IS NULL OR started_at IS NULL OR finished_at >= started_at",
            name="finished_after_started",
        ),
        # ⚠ TICK NING ISSIQ YO'LI. `market_id` bilan boshlanadi, chunki tick
        #   HAR BOZOR uchun ALOHIDA tranzaksiyada, tenant konteksti ostida
        #   ishlaydi (§S-3) — ya'ni so'rovda `market_id = ...` predikati
        #   HAR DOIM bor. Qisman: yakunlangan qatorlar (kunlarning katta
        #   qismi) indeksga umuman tushmaydi, ya'ni indeks kichik qoladi.
        Index(
            CAPTURE_DUE_INDEX,
            "market_id",
            "scheduled_at",
            postgresql_where=text(CAPTURE_DUE_PREDICATE),
        ),
        # ⚠ BU INDEKS `market_id` BILAN BOSHLANMAYDI VA BU ATAYIN.
        #   Watchdog BARCHA BOZORLAR ustidan yuradi: savol «qaysi bozorda?»
        #   emas, «umuman nimadir osilib qoldimi?». `market_id` bilan
        #   boshlash uni o'sha so'rov uchun BUTUNLAY foydasiz qilardi
        #   (rejalashtiruvchi birinchi ustunsiz undan foydalana olmaydi) va
        #   watchdog bozorlar soni o'sgani sari to'liq skanga o'tardi.
        #
        #   Nom `tests/tenancy/test_meta.py::INDEX_EXCEPTIONS` ga 04-01 da
        #   SABAB bilan qo'shilgan. Istisno xavfsizlik da'vosini
        #   SUSAYTIRMAYDI: watchdog faqat identifikatorlarni oladi va har
        #   qanday keyingi o'qish odatdagidek RLS ostidan o'tadi.
        Index(
            CAPTURE_OVERDUE_INDEX,
            "scheduled_at",
            postgresql_where=text(CAPTURE_OVERDUE_PREDICATE),
        ),
    )

    id: Mapped[UUID] = uuid_pk()
    camera_id: Mapped[UUID] = mapped_column(PgUuid(as_uuid=True), nullable=False)
    # DENORMALIZATSIYA — klass docstringidagi uchinchi bandga qarang.
    nvr_id: Mapped[UUID] = mapped_column(PgUuid(as_uuid=True), nullable=False)
    # Profil slotidan NUSXALANADI. Jadval keyinroq tahrirlansa BUGUNGI reja
    # o'zgarmaydi (D-05) — ya'ni bu ustun rejaning MUZLATILGAN nusxasi.
    slot_time: Mapped[time] = mapped_column(Time(timezone=False), nullable=False)
    # `((business_date + slot_time) AT TIME ZONE markets.timezone)` — ya'ni
    # bozorning O'Z mintaqasidan. `business_date` esa literaldan (pastga
    # qarang) va bu assimetriya meta-test bilan qo'riqlanadi.
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    business_date: Mapped[date] = mapped_column(
        Date(),
        Computed(CAPTURE_BUSINESS_DATE_EXPR, persisted=True),
        nullable=False,
    )
    # `sbozor_core.enums.CaptureRunStatus`. Boshlang'ich `pending` — qator
    # rejadan tug'iladi, hodisadan emas.
    status: Mapped[str] = mapped_column(Text(), nullable=False, server_default=text("'pending'"))
    attempts: Mapped[int] = mapped_column(SmallInteger(), nullable=False, server_default=text("0"))
    # IJARA (lease). `SELECT ... FOR UPDATE SKIP LOCKED` bilan olinadi va
    # `locked_until` o'tgach qator qaytariladi — ya'ni yiqilgan worker'ning
    # ishi mangu qulflanib qolmaydi.
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Worker identifikatori — FAQAT diagnostika uchun. Qulflash qarori
    # `locked_until` ga tayanadi, bu ustunga EMAS: nom bo'yicha qulflash
    # worker qayta nomlanganda jimgina buzilardi.
    locked_by: Mapped[str | None] = mapped_column(Text(), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # KOD, MATN EMAS (`models/nvr.py::NvrDiscoveryRun.error_code` bilan bir
    # xil qaror): frontend uni uch tilga tarjima qiladi. Matn saqlansa u
    # bitta tilda muzlab qolardi (CLAUDE.md «3 til majburiy»).
    error_code: Mapped[str | None] = mapped_column(Text(), nullable=True)
    # ⚠ YOZISHDAN OLDIN `mask_sensitive` DAN O'TADI (`03-PATTERNS.md` §S-7):
    #   filtr faqat KALIT nomiga qaraydi, ya'ni parol bu yerga NOMLANGAN
    #   kalit sifatida tushishi shart, formatlangan matn ichida hech qachon.
    error_detail: Mapped[dict[str, Any] | None] = mapped_column(JSONB(), nullable=True)
    # QAYSI yo'l HAQIQATAN ishladi (`nvr_devices.capture_method` — SOZLAMA).
    # `NULL` = hali urinilmagan; fallback ishga tushganda ikkalasi FARQ
    # qiladi va aynan shu farq dala diagnostikasining birinchi savoli.
    capture_method: Mapped[str | None] = mapped_column(Text(), nullable=True)
    # `market_is_open()` dan (D-10). Yopiq kunda ham kadr olinadi, chunki
    # yopiq kundagi band rasta — aynan mahsulot izlaydigan anomaliya; 6-faza
    # bunday qatorlarni BILLING'dan chiqaradi, HISOBOTDAN esa chiqarmaydi.
    # Bayroq qator yozilgan PAYTDAGI holatni muzlatadi: kalendar keyinroq
    # tahrirlansa o'tmishdagi dalil qayta talqin qilinmaydi.
    is_market_open: Mapped[bool] = mapped_column(Boolean(), nullable=False)
    # FK ATAYIN YO'Q — klass docstringidagi oxirgi bandga qarang.
    snapshot_id: Mapped[UUID | None] = mapped_column(PgUuid(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Snapshot(Base, TenantMixin):
    """Olingan kadrning METAMA'LUMOTI — dalil zanjirining birinchi halqasi (CAM-06).

    =========================================================================
    IKKI QAT'IY TAQIQ.

    **(a) KADR BAYTLARI BU JADVALDA YO'Q.** Faqat `object_key`,
    `size_bytes`, `etag`. `bytea` ustuni «qulaylik uchun» QO'SHILMAYDI —
    bu `cameras` da `rtsp_url` ustuni yo'qligining aynan bir oilasidagi
    qaror (`0012_nvr_domain.py:26-31`). Sabablari: JPEG'lar Postgres'ning
    TOAST'iga tushib `pg_dump` ni ~175 MB/kun/bozorga o'stirardi va
    backup/restore mashqi (spec §5) bajarib bo'lmas holga kelardi; S3
    abstraksiyasi esa omborni SOZLAMA o'zgarishi qilib saqlaydi
    (SeaweedFS -> Uzbekiston hostingiga ko'chish).

    **(b) `quality_verdict` YOZISH PAYTIDA QO'YILADI, HISOBLANMAYDI**
    (T-04-23). U oddiy ustun va hech qachon qayta baholanmaydi;
    `quality_thresholds_version` esa QAYSI chegara to'plami bilan
    qo'yilganini yozadi. Aks holda chegarani sozlash (D-15: Phase 0 real
    kadrlarda sozlaydi) o'tmishdagi kadrlarning billing yaroqliligini
    RETROAKTIV o'zgartirardi — ya'ni bir yil oldin yozilgan hisob bugun
    o'z-o'zidan bekor bo'lardi. Qayta tasniflash kerak bo'lsa u ATAYIN
    qilinadigan migratsiya bo'ladi, jimgina hisoblanadigan ifoda emas.
    =========================================================================

    `is_billable` — `GENERATED ALWAYS AS (quality_verdict = 'ok') STORED`.
    Shakl W0-1 zondi bilan HAQIQIY `postgres:18.4` da O'LCHANGAN
    (2026-08-04, `tests/fixtures/billable_probe.py`): `GENERATED ... STORED`
    ustun ustidagi `UNIQUE` kompozit FK NISHONI bo'la OLADI
    (`BILLABLE_ANCHOR_SUPPORTED = true`). Shuning uchun `BEFORE
    INSERT/UPDATE` trigger varianti KERAK EMAS va D-16 ning kafolati
    TUZILMAVIY bo'ladi. Zond kafolatning IKKALA yo'nalishini ham o'lchadi:
    `'dark'` qatorga havola `ForeignKeyViolation` beradi, VA mavjud `'ok'`
    qatorni `'dark'` ga `UPDATE` qilish ham rad etiladi — ya'ni kafolat
    faqat `INSERT` paytida emas, hukm o'zgarganda ham ishlaydi.

    `TimestampMixin` YO'Q: kadr o'zgarmaydi. Yagona «yangilanish» —
    retention (`storage_tier`, `object_deleted_at`) va u o'z ustunlari
    bilan o'lchanadi; `updated_at` «bu qatorni tahrirlash mumkin» degan
    yolg'on va'da berardi.
    """

    __tablename__ = "snapshots"
    __table_args__ = (
        ForeignKeyConstraint(["market_id"], ["markets.id"], name="fk_snapshots_market_id_markets"),
        ForeignKeyConstraint(
            ["market_id", "capture_run_id"],
            ["capture_runs.market_id", "capture_runs.id"],
            name="fk_snapshots_market_id_capture_run_id_capture_runs",
        ),
        # `camera_id` DENORMALIZATSIYA, lekin kompozit FK baribir qo'yiladi:
        # `capture_runs.nvr_id` bilan bir xil qoida — denormalizatsiya
        # tenant chegarasini bo'shatish uchun bahona emas (T-03-14 sinfi).
        ForeignKeyConstraint(
            ["market_id", "camera_id"],
            ["cameras.market_id", "cameras.id"],
            name="fk_snapshots_market_id_camera_id_cameras",
        ),
        # Bitta slotga bitta kadr. Ikkinchi kadr «qaysi biri dalil?»
        # savolini javobsiz qoldirardi va 5-faza tasodifiy birini tanlardi.
        UniqueConstraint(
            "market_id", "capture_run_id", name="uq_snapshots_market_id_capture_run_id"
        ),
        # Obyekt kaliti DETERMINISTIK (04-04) — ikkita qator bir obyektga
        # ishora qilsa retention ulardan birini o'chirib, ikkinchisini
        # «mavjud» deb qoldirardi.
        UniqueConstraint("market_id", "object_key", name="uq_snapshots_market_id_object_key"),
        # ⚠⚠ D-16 NING YAGONA ILGAGI — BU KONSTRAYT BOSHQA FAZA UCHUN BOR.
        #
        #   5-fazada `occupancy_events` shunday quriladi:
        #
        #       snapshot_is_billable boolean NOT NULL DEFAULT true
        #       CHECK  (snapshot_is_billable)
        #       FOREIGN KEY (snapshot_id, snapshot_is_billable)
        #           REFERENCES snapshots (id, is_billable)
        #
        #   Ya'ni `quality_verdict <> 'ok'` bo'lgan kadrga bandlik dalilini
        #   bog'lash uchun kerak bo'lgan `(id, true)` juftligi JADVALDA
        #   UMUMAN MAVJUD BO'LMAYDI va FK rad etadi. «Yaroqsiz kadr
        #   billing'ga ta'sir qilmaydi» da'vosi kelishuv emas, DB xatosi.
        #
        #   ⚠ NOMI KONVENSIYADAN HOSILA EMAS (`uq_snapshots_id_is_billable`
        #     bo'lardi): `billable_anchor` nomi 5-faza va meta-test uchun
        #     QIDIRILADIGAN belgidir — u tasodifiy UNIQUE emas, ATAYIN
        #     qo'yilgan langar ekanini nomning o'zi aytadi.
        UniqueConstraint("id", "is_billable", name="uq_snapshots_billable_anchor"),
        CheckConstraint(SNAPSHOT_QUALITY_CHECK, name="quality_verdict_allowed"),
        CheckConstraint(SNAPSHOT_LIGHT_MODE_CHECK, name="light_mode_allowed"),
        CheckConstraint(SNAPSHOT_TIER_CHECK, name="storage_tier_allowed"),
        CheckConstraint(CAPTURE_METHOD_CHECK, name="capture_method_allowed"),
        CheckConstraint("size_bytes > 0", name="size_bytes_positive"),
        CheckConstraint("length(btrim(object_key)) > 0", name="object_key_not_blank"),
        # `purged` qator obyekt QACHON o'chirilganini aytishi SHART, aks
        # holda «kadr mavjud edi, arxivdan chiqarildi» da'vosi sanasiz
        # qolardi va operator uni «yo'qolgan kadr» dan ajrata olmasdi.
        CheckConstraint(
            "(storage_tier = 'purged') = (object_deleted_at IS NOT NULL)",
            name="purged_has_deletion_time",
        ),
    )

    id: Mapped[UUID] = uuid_pk()
    capture_run_id: Mapped[UUID] = mapped_column(PgUuid(as_uuid=True), nullable=False)
    # DENORMALIZATSIYA: 5/6-faza so'rovlari «shu kameraning shu kundagi
    # kadrlari» ni `capture_runs` ga `JOIN` qilmasdan olishi kerak.
    camera_id: Mapped[UUID] = mapped_column(PgUuid(as_uuid=True), nullable=False)
    # ⚠ `capture_runs.scheduled_at` DAN NUSXALANADI, MUSTAQIL HISOBLANMAYDI.
    #   Ikki mustaqil hisoblash manbai yarim tunda bir kun farq qilardi
    #   (Pitfall 3) — `SNAPSHOT_BUSINESS_DATE_EXPR` docstringiga qarang.
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # FORENZIKA uchun: kadr HAQIQATAN qachon olindi. `scheduled_at` bilan
    # farqi kechikishni beradi va u grace oynasi qarorining dalili.
    # ⚠ `business_date` bu ustundan HISOBLANMAYDI: 06:00 sloti 06:09 da
    #   olingan bo'lsa ham u 06:00 slotining dalili bo'lib qolishi kerak.
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    slot_time: Mapped[time] = mapped_column(Time(timezone=False), nullable=False)
    business_date: Mapped[date] = mapped_column(
        Date(),
        Computed(SNAPSHOT_BUSINESS_DATE_EXPR, persisted=True),
        nullable=False,
    )
    # S3 kaliti — DETERMINISTIK (04-04). Siqilgan versiya AYNAN shu kalitni
    # ustiga yozadi, ya'ni 6-fazadagi dalil havolalari hech qachon
    # buzilmaydi.
    object_key: Mapped[str] = mapped_column(Text(), nullable=False)
    # `sbozor_core.enums.SnapshotTier` — BIR YO'NALISHLI o'tish.
    storage_tier: Mapped[str] = mapped_column(Text(), nullable=False, server_default=text("'full'"))
    # 455 kundan keyin obyekt o'chiriladi, QATOR QOLADI (D-18).
    object_deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    size_bytes: Mapped[int] = mapped_column(Integer(), nullable=False)
    # S3 javobidan. Yuklashning HAQIQATAN yakunlanganini tasdiqlaydi —
    # `PUT` ning status kodi emas, natijaning o'zi (03-14 metodikasi).
    etag: Mapped[str | None] = mapped_column(Text(), nullable=True)
    width: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    height: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    # `sbozor_core.enums.SnapshotQuality` — `is_billable` ning YAGONA kirishi.
    quality_verdict: Mapped[str] = mapped_column(Text(), nullable=False)
    # ⚠ O'LCHOVLARNING O'ZI SAQLANADI, FAQAT HUKM EMAS (D-15). Shunda
    #   Phase 0 ning real Karmana kadrlari chegaralarni SQL bilan sozlaydi,
    #   qayta kadr olish bilan emas — chegaralar bugun LOW confidence,
    #   chunki real kadr hali yo'q.
    quality_mean: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    quality_stddev: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    # IR aniqlash uchun — deyarli monoxrom kadrda to'yinganlik nolga yaqin.
    # `NULL` = o'lchanmadi (kadr buzuq yoki bir kanalli).
    quality_saturation: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    # Verdikt QAYSI chegara to'plami bilan qo'yilgani — klass docstringidagi
    # (b) bandining bajarilish mexanizmi.
    quality_thresholds_version: Mapped[int] = mapped_column(SmallInteger(), nullable=False)
    # `sbozor_core.enums.SnapshotLightMode` — `quality_verdict` ning
    # DUBLIKATI EMAS (D-12: superset). Ikki savol boshqa: «ishlatsa
    # bo'ladimi?» va «qanday yorug'likda olingan?».
    light_mode: Mapped[str] = mapped_column(Text(), nullable=False)
    # QAYSI yo'l HAQIQATAN ishladi (`sbozor_core.enums.CaptureMethod`).
    capture_method: Mapped[str] = mapped_column(Text(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    # ⚠ HOSILA USTUN — ILOVA UNGA YOZA OLMAYDI (`GENERATED ALWAYS`).
    #   Shakl 2026-08-04 da `postgres:18.4` da o'lchangan (klass
    #   docstringiga qarang): trigger varianti kerak emas.
    is_billable: Mapped[bool] = mapped_column(
        Boolean(),
        Computed("quality_verdict = 'ok'", persisted=True),
        nullable=False,
    )


class AlertEvent(Base, TenantMixin):
    """Ochiq ogohlantirish — debounce va eskalatsiyaning holat yozuvi (D-22).

    TENANT jadvali (`market_id NOT NULL`), `GLOBAL_TABLES` da EMAS:
    ogohlantirish HAR DOIM aniq bir bozorning kamerasiga yoki NVR'iga
    tegishli va UI uni BOZOR sahifasida ko'rsatadi. (`04-RESEARCH.md` §E.13
    uni «global» deb atagan, lekin o'sha yerdayoq unga `market_id` bergan —
    ikkisi bir vaqtda to'g'ri bo'la olmaydi; `GLOBAL_TABLES` ning ta'rifi
    «`market_id` ustuni BO'LMASLIGI kutilgan jadvallar».)

    ⚠ ALERTGA KADR RASMI HECH QACHON BIRIKTIRILMAYDI (D-19) — shuning uchun
    bu jadvalda `snapshot_id` ustuni ham YO'Q. Dalil-kadrlar bozor
    tashrifchilarining shaxsiy ma'lumoti, Telegram serverlari esa loyiha
    zimmasiga olgan O'zR data-rezidentlik chegarasidan tashqarida. `detail`
    ga faqat matn va sonlar tushadi.

    HODISA JURNALI, ya'ni audit triggeridan chiqarilgan (`capture_runs` va
    `snapshots` bilan bir xil sabab): u faqat qo'shiladi/yangilanadi va
    `occurrences`/`first_seen_at`/`last_seen_at` bilan o'z tarixiga ega.

    `TimestampMixin` YO'Q: `created_at` o'rniga `first_seen_at`,
    `updated_at` o'rniga `last_seen_at` — ikkinchi vaqt juftligi faqat
    chalkashlik qo'shardi (`NvrDiscoveryRun` bilan bir xil qoida).
    """

    __tablename__ = "alert_events"
    __table_args__ = (
        ForeignKeyConstraint(
            ["market_id"], ["markets.id"], name="fk_alert_events_market_id_markets"
        ),
        UniqueConstraint("market_id", "id", name="uq_alert_events_market_id_id"),
        CheckConstraint(ALERT_SEVERITY_CHECK, name="severity_allowed"),
        CheckConstraint("occurrences > 0", name="occurrences_positive"),
        CheckConstraint("length(btrim(alert_key)) > 0", name="alert_key_not_blank"),
        CheckConstraint("last_seen_at >= first_seen_at", name="last_seen_after_first"),
        # ⚠ DEBOUNCE NING YAGONA DB KAFOLATI: bitta `(bozor, kalit, subyekt)`
        #   uchun AYNAN BITTA ochiq alert. Qisman (`resolved_at IS NULL`),
        #   ya'ni yopilgan alertlar tarixi cheksiz to'planaveradi va faqat
        #   OCHIQ qator qulflanadi — `nvr_discovery_runs` ning «bir vaqtda
        #   ikki skan yo'q» indeksi bilan aynan bir xil naqsh.
        #
        #   Uchinchi kalit — IFODA (`ALERT_OPEN_EXPR`) va sabab o'sha
        #   konstantaning yonida: `NULL` UNIQUE indeksda o'ziga teng emas.
        Index(
            ALERT_OPEN_INDEX,
            "market_id",
            "alert_key",
            text(ALERT_OPEN_EXPR),
            unique=True,
            postgresql_where=text(ALERT_OPEN_PREDICATE),
        ),
    )

    id: Mapped[UUID] = uuid_pk()
    # `capture_missed`, `camera_offline`, `backup_stale` — i18n KALITI,
    # matn emas (`capture_runs.error_code` bilan bir xil qaror).
    alert_key: Mapped[str] = mapped_column(Text(), nullable=False)
    # `sbozor_core.enums.AlertSeverity`. Muammo davom etsa CHASTOTA emas,
    # DARAJA oshadi — eskalatsiya, spam emas.
    severity: Mapped[str] = mapped_column(Text(), nullable=False)
    # Kamera yoki NVR identifikatori. FK ATAYIN YO'Q: subyekt IKKI XIL
    # jadvaldan bo'lishi mumkin (polimorf havola) va bitta ustunga ikkita
    # FK qo'yib bo'lmaydi. `NULL` = butun bozorga tegishli alert.
    subject_id: Mapped[UUID | None] = mapped_column(PgUuid(as_uuid=True), nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    # Bo'g'ilgan takrorlar shu yerda sanaladi va keyingi xabarda «(so'nggi
    # soatda yana 47 marta)» bo'lib chiqadi — ya'ni bo'g'ish ma'lumot
    # yo'qotmaydi.
    occurrences: Mapped[int] = mapped_column(Integer(), nullable=False, server_default=text("1"))
    # Oxirgi Telegram xabari. `NULL` = hali yuborilmagan (debounce oynasi
    # ichida yoki `TELEGRAM_BOT_TOKEN` bo'sh — D-19).
    notified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Yopilmagan alert — OCHIQ ISH. Uni yopadigan yagona narsa — tiklanish
    # xabari («kadr olish tiklandi»).
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # FAQAT matn va sonlar (D-19). Kadr, obyekt kaliti yoki shaxsiy
    # ma'lumot bu yerga tushmaydi.
    detail: Mapped[dict[str, Any] | None] = mapped_column(JSONB(), nullable=True)
