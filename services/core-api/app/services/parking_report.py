"""Avtoturargoh davr hisoboti — agent hodisalaridan SOF hisob + `.xlsx`.

Direktorning savoli: «shu sanalar orasida qancha mashina kirdi/chiqdi va
qancha tushum bo'ldi?». Javob `edge_events` jadvalidagi uch turdagi
hodisadan yig'iladi (`parking.session.opened`, `parking.session.closed`,
`core.payment.cash`) va bu modul ularni DB'SIZ, sinxron qayta ishlaydi —
shuning uchun u `tests/unit/` da konteynersiz to'liq o'lchanadi
(`xlsx_export` bilan bir xil joylashuv qarori, `services/__init__.py`).

Uch qoida, keyingi o'quvchi uchun literal:

1. KUN — ISH KUNI, 06:00 DAN 06:00 GACHA (2026-11-03, buyurtmachi: «har
   kun ertalab soat 6:00 dan yangi hisob boshlansin»). Hodisa `occurred_at`
   i UTC'da saqlanadi, `Asia/Tashkent` ga o'giriladi va 06:00 dan oldingi
   lahza OLDINGI kunga tushadi (`business_day_of`). 23:30 da kirgan va
   00:10 da chiqqan mashina BITTA kunga yoziladi; 05:50 da chiqqani ham
   kechagi kunniki. Agent kassasi ham kunni 06:00 da almashtiradi — ikki
   ekran bir kunni bir xil chegarada sanaydi. Soatlar (`hours`) esa soat
   bo'yicha qoladi (0..23), tartibni ekran 06 dan boshlaydi.

2. PUL — `core.payment.cash` HODISASIDAN, `closed.amount_soum` DAN EMAS.
   Kunlik «Naqd/Terminal/Jami» ustunlari aynan to'lov hodisalaridan
   yig'iladi (`edge_sites.parking_summary` bilan AYNI manba — ikki ekran
   bitta sonni ko'rsatsin). Seans varag'idagi «Summa» ham avval to'lovga
   qaraydi; to'lov bo'lmasa (bepul, onlayn) `closed.amount_soum` yoziladi.

3. SEANS — `session_id` BO'YICHA BOG'LANADI. `closed` hodisasida raqam
   (`plate`) YO'Q bo'lishi mumkin — u `opened` dan olinadi. To'lov
   `subject.kind == parking_session` bo'lsa `subject.id` orqali, aks
   holda `correlation_id` orqali seansga biriktiriladi; hech biriga
   tushmagan to'lov kunlik yig'indiga baribir kiradi (pul yo'qolmaydi),
   seans varag'ida esa ko'rinmaydi.

⚠ CHEGARA HAQIDA HALOL: so'rov faqat `[from, to]` oralig'idagi hodisalarni
  oladi. Davr boshidan OLDIN kirib, davr ichida chiqqan mashinaning
  `opened` hodisasi tanlovga tushmaydi — seans varag'ida u raqamsiz va
  «kirgan vaqti» bo'sh qator bo'lib chiqadi. Bu yashirilmaydi: bo'sh
  katak «o'lchanmagan» degani (D-10), to'qilgan vaqt emas.

Panel grafiklari uchun yig'indilar ham SHU YERDA (261102): soatlar
bo'yicha oqim, turish vaqti guruhlari, chiqish turlari, ichkarida qolgan
mashinalar, o'rtacha chek va doimiy mashinalar. Ekran ularni faqat
CHIZADI — klientdagi qayta hisob ikkinchi javob bo'lib chiqardi.
"""

from __future__ import annotations

import io
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from typing import TYPE_CHECKING, Any, Final, Protocol
from uuid import UUID
from zoneinfo import ZoneInfo

from app.services.xlsx_export import (
    COUNT_NUM_FORMAT,
    MONEY_NUM_FORMAT,
    REPORT_DEFAULT_LOCALE,
    ReportPeriod,
    finish,
    layout_sheet,
    money_format,
    new_workbook,
    write_header,
    write_money,
    write_optional_number,
    write_optional_text,
    write_text,
)

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

__all__ = [
    "DAY_START_HOUR",
    "EVENT_TYPES",
    "EXIT_REASONS",
    "MAX_PERIOD_DAYS",
    "REGULARS_LIMIT",
    "STAY_BUCKETS",
    "SUMMARY_MAX_PERIOD_DAYS",
    "ParkingDayRow",
    "ParkingExitReason",
    "ParkingHourRow",
    "ParkingRegular",
    "ParkingReport",
    "ParkingSessionRow",
    "ParkingStay",
    "ParkingStayBucket",
    "ParkingTotals",
    "build_parking_report",
    "build_parking_report_workbook",
    "business_day_of",
    "business_day_start",
    "parking_report_texts",
]

TASHKENT: Final = ZoneInfo("Asia/Tashkent")

DAY_START_HOUR: Final = 6
"""Avtoturargoh ish kuni shu soatda boshlanadi (modul docstringining 1-bandi)."""

MAX_PERIOD_DAYS: Final = 92
"""Davrning eng katta uzunligi — bir chorak.

Avtoturargohda kuniga yuzlab seans bo'ladi; 92 kun × ~500 seans ≈ 46 000
qator — `.xlsx` va JSON uchun hali ko'tariladigan hajm. Yillik so'rov
esa `settings.report_max_rows` ga uriladi va ochiq rad etiladi.
"""

SUMMARY_MAX_PERIOD_DAYS: Final = 366
"""Seanslarsiz yig'indi (`sessions=0`) uchun chegara — direktor panelidagi yillik
tushum grafigi. Seanslar ro'yxati bo'lmagani uchun javob hajmi kunlar soniga
bog'liq, `report_max_rows` ga urilmaydi."""


def business_day_of(moment: datetime) -> date:
    """Lahza qaysi ish kuniga tegishli: 06:00 dan oldingisi — oldingi kunniki."""
    return (moment.astimezone(TASHKENT) - timedelta(hours=DAY_START_HOUR)).date()


def business_day_start(day: date) -> datetime:
    """Ish kunining boshlanishi — o'sha sananing 06:00 i (Toshkent)."""
    return datetime.combine(day, time(DAY_START_HOUR), tzinfo=TASHKENT)


EVENT_TYPES: Final = (
    "parking.session.opened",
    "parking.session.closed",
    "core.payment.cash",
)
"""Hisobot o'qiydigan hodisa turlari — `edge_repo.summary_events` filtri."""

_TYPE_OPENED: Final = "parking.session.opened"
_TYPE_CLOSED: Final = "parking.session.closed"
_TYPE_PAYMENT: Final = "core.payment.cash"

_METHOD_TERMINAL: Final = "terminal"
_METHOD_CASH: Final = "cash"
_METHOD_MIXED: Final = "mixed"
"""Bitta seans ikki xil usulda to'langan (naqd + terminal) — alohida qiymat."""

_FREE_REASONS: Final = frozenset({"free", "exempt"})
"""`closed.reason` ning «pul olinmadi» ma'nosidagi qiymatlari.

`exempt` sxemada hali yo'q, lekin agentning keyingi versiyasi uni
qo'shishi mumkin — ikkalasi ham bepul deb sanaladi, tushumga kirmaydi.
"""

_DATETIME_FORMAT: Final = "%d.%m.%Y %H:%M"
"""Varaqdagi vaqt shakli — Toshkent vaqti, `DD.MM.YYYY HH:MM`."""

STAY_BUCKETS: Final[tuple[tuple[str, int, int | None], ...]] = (
    ("under_15m", 0, 15),
    ("under_1h", 15, 60),
    ("under_2h", 60, 120),
    ("under_4h", 120, 240),
    ("under_8h", 240, 480),
    ("over_8h", 480, None),
)
"""Turish vaqti guruhlari: `(kalit, boshi, oxiri)` daqiqada, oxiri KIRMAYDI.

Chegaralar tarif soatiga qarab tanlangan (soatbay to'lov): birinchi
guruh — bepul vaqt ichida chiqib ketganlar, oxirgisi — tunab qolganlar.
Kalitlar frontend katalogida uch tilga o'giriladi.
"""

EXIT_REASONS: Final = ("paid", "online", "free", "exempt", "manual")
"""`closed.reason` ning ma'lum qiymatlari — chiqish turlari ro'yxatining TARTIBI.

Noma'lum yoki bo'sh sabab `other` bo'lib sanaladi: chiqishlar yig'indisi
`total.exits` bilan har doim teng qolsin.
"""

_REASON_OTHER: Final = "other"

REGULARS_LIMIT: Final = 6
"""«Doimiy mashinalar» ro'yxatining uzunligi — davrda kamida ikki marta kelganlar."""

_REGULAR_MIN_VISITS: Final = 2

_FILE_ID_LENGTH: Final = 64
_HEX_DIGITS: Final = frozenset("0123456789abcdef")


class EventLike(Protocol):
    """`edge_repo.EventRow` ning hisobot o'qiydigan qismi.

    Protokol ATAYIN: unit test oddiy obyekt beradi, marshrut esa
    `EventRow` — ikkalasi ham shu to'rt maydon bilan yetadi va modul
    repozitoriy paketiga bog'lanmaydi.
    """

    @property
    def type(self) -> str: ...

    @property
    def occurred_at(self) -> datetime: ...

    @property
    def correlation_id(self) -> UUID | None: ...

    @property
    def data(self) -> dict[str, Any]: ...


@dataclass(frozen=True, slots=True)
class ParkingTotals:
    """Davr yig'indisi — kunlik qatorlarning ustun bo'yicha summasi."""

    entries: int
    exits: int
    cash_soum: int
    terminal_soum: int
    total_soum: int
    free_count: int


@dataclass(frozen=True, slots=True)
class ParkingDayRow:
    """Bitta Toshkent kuni. Hodisasiz kun ham qator oladi (nol bilan)."""

    day: date
    entries: int
    exits: int
    cash_soum: int
    terminal_soum: int
    total_soum: int
    free_count: int


@dataclass(frozen=True, slots=True)
class ParkingSessionRow:
    """Bitta mashina seansi — `opened` + `closed` + to'lovlar birlashmasi.

    `None` maydon — HODISA KELMAGAN (ochiq seans, raqamsiz kirish, davr
    boshidan oldingi kirish); `0` yoki bo'sh satr bilan ALMASHTIRILMAYDI.
    """

    session_id: str
    plate: str | None
    entered_at: datetime | None
    exited_at: datetime | None
    duration_minutes: int | None
    amount_soum: int
    method: str | None
    reason: str | None
    entry_file_id: str | None
    """Seans ochilgandagi kadr (`opened.file_id`) — panelda mashina surati."""
    opened_at_exit: bool
    """Seans CHIQISH yo'lagida ochilib, o'sha zahoti yopilgan: kirish kamerasi
    mashinani ko'rmagan, kassir uni chiqishda ro'yxatga olgan. Kirgan vaqti
    va turish vaqti NOMA'LUM (nol emas), kadr esa chiqishdagi kadr."""


@dataclass(frozen=True, slots=True)
class ParkingHourRow:
    """Toshkent soati (0–23) — davrning barcha kunlari bo'yicha yig'indi."""

    hour: int
    entries: int
    exits: int


@dataclass(frozen=True, slots=True)
class ParkingStayBucket:
    key: str
    count: int


@dataclass(frozen=True, slots=True)
class ParkingStay:
    """Chiqqan va davomiyligi ma'lum seanslarning turish vaqti.

    `median_minutes` — o'rta qiymat (yarmi undan qisqa turgan); o'rtacha
    arifmetik EMAS: uch kun turib qolgan bitta mashina uni soatlab surardi.
    """

    measured: int
    median_minutes: int | None
    buckets: tuple[ParkingStayBucket, ...]
    unrecorded_entries: int
    """Chiqishda ro'yxatga olingan (kirishi yozilmagan) seanslar — turish
    vaqtiga KIRMAYDI, chunki ularning «0 daqiqa» si o'lchov emas."""


@dataclass(frozen=True, slots=True)
class ParkingExitReason:
    reason: str
    count: int


@dataclass(frozen=True, slots=True)
class ParkingRegular:
    """Davrda kamida ikki marta kelgan raqam."""

    plate: str
    visits: int
    amount_soum: int
    last_seen_at: datetime


@dataclass(frozen=True, slots=True)
class ParkingReport:
    from_date: date
    to_date: date
    days: tuple[ParkingDayRow, ...]
    total: ParkingTotals
    sessions: tuple[ParkingSessionRow, ...]
    hours: tuple[ParkingHourRow, ...]
    stay: ParkingStay
    exit_reasons: tuple[ParkingExitReason, ...]
    inside: int
    """Davrda kirgan, chiqishi esa hali qayd etilmagan seanslar."""
    paid_sessions: int
    average_check_soum: int | None
    """To'langan seanslar summasining o'rtachasi (butun so'm)."""
    regulars: tuple[ParkingRegular, ...]


@dataclass(slots=True)
class _DayCounters:
    entries: int = 0
    exits: int = 0
    cash_soum: int = 0
    terminal_soum: int = 0
    free_count: int = 0


@dataclass(slots=True)
class _SessionState:
    session_id: str
    plate: str | None = None
    entered_at: datetime | None = None
    exited_at: datetime | None = None
    duration_minutes: int | None = None
    closed_amount_soum: int | None = None
    reason: str | None = None
    payments_soum: int = 0
    methods: set[str] = field(default_factory=set)
    entry_file_id: str | None = None
    entry_lane: str | None = None
    exit_lane: str | None = None


def _int_or(value: Any, default: int) -> int:
    """`data` dagi son — agent protokoli `integer` deydi, lekin bu yerda
    ishonilmaydi: noto'g'ri tip hisobotni 500 bilan yiqitmasin."""
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return default


def _str_or_none(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def _file_id_or_none(value: Any) -> str | None:
    """Kadr identifikatori — SHA-256 hex (`edge_sites.site_file` bilan bir xil
    tekshiruv): boshqa shakl panelga yetib bormaydi, u yerda baribir 404 bo'lardi."""
    if not isinstance(value, str) or len(value) != _FILE_ID_LENGTH:
        return None
    return value if set(value) <= _HEX_DIGITS else None


def _payment_session_id(event: EventLike) -> str | None:
    """To'lov qaysi seansga tegishli: `subject.id` (parking_session) yoki
    `correlation_id`."""
    subject = event.data.get("subject")
    if isinstance(subject, dict) and subject.get("kind") == "parking_session":
        linked = _str_or_none(subject.get("id"))
        if linked is not None:
            return linked
    return None if event.correlation_id is None else str(event.correlation_id)


def _session_anchor(state: _SessionState) -> datetime:
    """Saralash kaliti — kirgan vaqti, u bo'lmasa chiqqan vaqti."""
    anchor = state.entered_at or state.exited_at
    # Ikkalasi ham `None` bo'lishi mumkin emas: seans faqat `opened` yoki
    # `closed` hodisasidan tug'iladi. Himoya — tiplash uchun.
    return anchor if anchor is not None else datetime.min.replace(tzinfo=TASHKENT)


def _session_row(state: _SessionState) -> ParkingSessionRow:
    # To'lov hodisasi bor -> u haqiqat; yo'q bo'lsa (bepul/onlayn) `closed` summasi.
    amount = state.payments_soum if state.payments_soum > 0 else (state.closed_amount_soum or 0)

    if not state.methods:
        method: str | None = None
    elif len(state.methods) == 1:
        method = next(iter(state.methods))
    else:
        method = _METHOD_MIXED

    duration = state.duration_minutes
    if duration is None and state.entered_at is not None and state.exited_at is not None:
        duration = max(int((state.exited_at - state.entered_at).total_seconds() // 60), 0)

    # Bir yo'lakda ochilib-yopilgan nol daqiqalik seans — haqiqiy turish emas:
    # mashina chiqishda ro'yxatga olingan (ikki tomonlama yo'lakda ham nol
    # daqiqada kirib-chiqish jismonan bo'lmaydi).
    opened_at_exit = (
        state.entry_lane is not None and state.entry_lane == state.exit_lane and duration == 0
    )

    return ParkingSessionRow(
        session_id=state.session_id,
        plate=state.plate,
        entered_at=state.entered_at,
        exited_at=state.exited_at,
        duration_minutes=duration,
        amount_soum=amount,
        method=method,
        reason=state.reason,
        entry_file_id=state.entry_file_id,
        opened_at_exit=opened_at_exit,
    )


def _stay(rows: Sequence[ParkingSessionRow]) -> ParkingStay:
    """Turish vaqti — faqat CHIQQAN va davomiyligi ma'lum seanslardan.

    Ichkaridagi mashina hisobga kirmaydi: uning «turishi» hali tugamagan
    va kesib olingan qiymat taqsimotni qisqa tomonga surardi. Chiqishda
    ro'yxatga olingan seans ham kirmaydi — uning kirgan vaqti noma'lum.
    """
    minutes = sorted(
        row.duration_minutes
        for row in rows
        if row.exited_at is not None and row.duration_minutes is not None and not row.opened_at_exit
    )
    buckets = tuple(
        ParkingStayBucket(
            key=key,
            count=sum(1 for m in minutes if m >= low and (high is None or m < high)),
        )
        for key, low, high in STAY_BUCKETS
    )
    # Pastki o'rta (juft sonda kichigi) — butun daqiqa, kasr to'qilmaydi.
    median = minutes[(len(minutes) - 1) // 2] if minutes else None
    return ParkingStay(
        measured=len(minutes),
        median_minutes=median,
        buckets=buckets,
        unrecorded_entries=sum(1 for row in rows if row.opened_at_exit),
    )


def _regulars(rows: Sequence[ParkingSessionRow]) -> tuple[ParkingRegular, ...]:
    """Kamida ikki marta kelgan raqamlar: ko'p kelgani, teng bo'lsa ko'p to'lagani oldin.

    Raqamsiz matn (kameraning `UNKNOWN` i va h.k.) mashina emas — agentning
    `NormalizePlate` qoidasi bilan bir xil: raqamda kamida bitta son bor.
    """
    visits: defaultdict[str, list[ParkingSessionRow]] = defaultdict(list)
    for row in rows:
        if row.plate is not None and any(ch.isdigit() for ch in row.plate):
            visits[row.plate].append(row)

    regulars = [
        ParkingRegular(
            plate=plate,
            visits=len(seen),
            amount_soum=sum(row.amount_soum for row in seen),
            last_seen_at=max(_row_anchor(row) for row in seen),
        )
        for plate, seen in visits.items()
        if len(seen) >= _REGULAR_MIN_VISITS
    ]
    regulars.sort(key=lambda r: (-r.visits, -r.amount_soum, r.plate))
    return tuple(regulars[:REGULARS_LIMIT])


def _row_anchor(row: ParkingSessionRow) -> datetime:
    anchor = row.exited_at if row.exited_at is not None else row.entered_at
    return anchor if anchor is not None else datetime.min.replace(tzinfo=TASHKENT)


def build_parking_report(
    events: Iterable[EventLike],
    *,
    from_date: date,
    to_date: date,
) -> ParkingReport:
    """Hodisalardan hisobot — SOF funksiya, DB'ga tegmaydi.

    Args:
        events: `[from, to]` oralig'idagi `EVENT_TYPES` hodisalari
            (tartib ahamiyatsiz — kunlar va seanslar bu yerda saralanadi).
        from_date: davrning birinchi ish kuni (06:00 dan, kiradi).
        to_date: davrning oxirgi ish kuni (kiradi).

    Oraliqdan tashqaridagi kunga tushgan hodisa (chaqiruvchi filtrlamagan
    bo'lsa) BUTUNLAY e'tiborsiz qoldiriladi — kunlik jadvalga ham, seansga
    ham kirmaydi. Aks holda davrdan tashqaridagi to'lov seans summasini
    oshirib, varaqdagi «Summa» ustuni kunlik «Jami» bilan ajralib ketardi.
    """
    if from_date > to_date:
        msg = "from_date to_date dan keyin bo'lmasin"
        raise ValueError(msg)

    counters: defaultdict[date, _DayCounters] = defaultdict(_DayCounters)
    hour_entries = [0] * 24
    hour_exits = [0] * 24
    reasons: defaultdict[str, int] = defaultdict(int)
    sessions: dict[str, _SessionState] = {}

    def state_of(session_id: str) -> _SessionState:
        found = sessions.get(session_id)
        if found is None:
            found = _SessionState(session_id=session_id)
            sessions[session_id] = found
        return found

    for event in events:
        data = event.data
        local = event.occurred_at.astimezone(TASHKENT)
        day = business_day_of(event.occurred_at)
        if not from_date <= day <= to_date:
            continue

        if event.type == _TYPE_OPENED:
            counters[day].entries += 1
            hour_entries[local.hour] += 1
            session_id = _str_or_none(data.get("session_id"))
            if session_id is None:
                continue
            state = state_of(session_id)
            # Birinchi `opened` g'olib: takror yuborilgan hodisa (agent
            # qayta ulanishi) kirgan vaqtni keyinga surmasin.
            if state.entered_at is None or event.occurred_at < state.entered_at:
                state.entered_at = event.occurred_at
            if state.plate is None:
                state.plate = _str_or_none(data.get("plate"))
            if state.entry_file_id is None:
                state.entry_file_id = _file_id_or_none(data.get("file_id"))
            if state.entry_lane is None:
                state.entry_lane = _str_or_none(data.get("lane_id"))

        elif event.type == _TYPE_CLOSED:
            reason = _str_or_none(data.get("reason"))
            counters[day].exits += 1
            hour_exits[local.hour] += 1
            reasons[reason if reason in EXIT_REASONS else _REASON_OTHER] += 1
            if reason in _FREE_REASONS:
                counters[day].free_count += 1
            session_id = _str_or_none(data.get("session_id"))
            if session_id is None:
                continue
            state = state_of(session_id)
            if state.exited_at is None or event.occurred_at > state.exited_at:
                state.exited_at = event.occurred_at
                state.reason = reason
                state.exit_lane = _str_or_none(data.get("lane_id"))
                state.closed_amount_soum = _int_or(data.get("amount_soum"), 0)
                explicit = data.get("duration_minutes")
                state.duration_minutes = None if explicit is None else max(_int_or(explicit, 0), 0)

        elif event.type == _TYPE_PAYMENT:
            amount = max(_int_or(data.get("amount_soum"), 0), 0)
            method = _METHOD_TERMINAL if data.get("method") == _METHOD_TERMINAL else _METHOD_CASH
            if method == _METHOD_TERMINAL:
                counters[day].terminal_soum += amount
            else:
                counters[day].cash_soum += amount
            session_id = _payment_session_id(event)
            if session_id is None:
                continue
            state = state_of(session_id)
            state.payments_soum += amount
            state.methods.add(method)

    days: list[ParkingDayRow] = []
    cursor = from_date
    while cursor <= to_date:
        c = counters.get(cursor, _DayCounters())
        days.append(
            ParkingDayRow(
                day=cursor,
                entries=c.entries,
                exits=c.exits,
                cash_soum=c.cash_soum,
                terminal_soum=c.terminal_soum,
                total_soum=c.cash_soum + c.terminal_soum,
                free_count=c.free_count,
            )
        )
        cursor += timedelta(days=1)

    total = ParkingTotals(
        entries=sum(d.entries for d in days),
        exits=sum(d.exits for d in days),
        cash_soum=sum(d.cash_soum for d in days),
        terminal_soum=sum(d.terminal_soum for d in days),
        total_soum=sum(d.total_soum for d in days),
        free_count=sum(d.free_count for d in days),
    )

    ordered = sorted(sessions.values(), key=lambda s: (_session_anchor(s), s.session_id))
    rows = tuple(_session_row(s) for s in ordered)
    paid = [row.amount_soum for row in rows if row.amount_soum > 0]
    return ParkingReport(
        from_date=from_date,
        to_date=to_date,
        days=tuple(days),
        total=total,
        sessions=rows,
        hours=tuple(
            ParkingHourRow(hour=hour, entries=hour_entries[hour], exits=hour_exits[hour])
            for hour in range(24)
        ),
        stay=_stay(rows),
        # `other` faqat uchragan bo'lsa — ro'yxat oxirida, yig'indi `exits` ga teng.
        exit_reasons=tuple(
            ParkingExitReason(reason=reason, count=reasons[reason])
            for reason in (*EXIT_REASONS, _REASON_OTHER)
            if reason != _REASON_OTHER or reasons[reason] > 0
        ),
        inside=sum(1 for row in rows if row.entered_at is not None and row.exited_at is None),
        paid_sessions=len(paid),
        # Butun so'mga yaxlitlash (yarmi yuqoriga) — kasr tiyin to'qilmaydi.
        average_check_soum=(sum(paid) + len(paid) // 2) // len(paid) if paid else None,
        regulars=_regulars(rows),
    )


# ===========================================================================
# `.xlsx` — ikki varaq: «Kunlar» va «Mashinalar»
# ===========================================================================

_TEXTS: Final[dict[str, dict[str, str]]] = {
    "uz-Latn": {
        "site": "Avtoturargoh",
        "period": "Davr",
        "days_sheet": "Kunlar",
        "day": "Sana",
        "entries": "Kirdi",
        "exits": "Chiqdi",
        "cash": "Naqd (so'm)",
        "terminal": "Terminal (so'm)",
        "total": "Jami (so'm)",
        "free": "Bepul",
        "grand_total": "JAMI",
        "sessions_sheet": "Mashinalar",
        "plate": "Raqam",
        "entered": "Kirgan",
        "exited": "Chiqqan",
        "duration": "Davomiyligi (daq)",
        "amount": "Summa (so'm)",
        "method": "To'lov usuli",
        "status": "Holat",
        "method_cash": "Naqd",
        "method_terminal": "Terminal",
        "method_mixed": "Naqd + terminal",
        "status_open": "Ichkarida",
        "status_paid": "To'langan",
        "status_free": "Bepul",
        "status_manual": "Qo'lda chiqarilgan",
        "status_online": "Onlayn to'langan",
        "status_exempt": "Imtiyozli",
    },
    "uz-Cyrl": {
        "site": "Автотураргоҳ",
        "period": "Давр",
        "days_sheet": "Кунлар",
        "day": "Сана",
        "entries": "Кирди",
        "exits": "Чиқди",
        "cash": "Нақд (сўм)",
        "terminal": "Терминал (сўм)",
        "total": "Жами (сўм)",
        "free": "Бепул",
        "grand_total": "ЖАМИ",
        "sessions_sheet": "Машиналар",
        "plate": "Рақам",
        "entered": "Кирган",
        "exited": "Чиққан",
        "duration": "Давомийлиги (дақ)",
        "amount": "Сумма (сўм)",
        "method": "Тўлов усули",
        "status": "Ҳолат",
        "method_cash": "Нақд",
        "method_terminal": "Терминал",
        "method_mixed": "Нақд + терминал",
        "status_open": "Ичкарида",
        "status_paid": "Тўланган",
        "status_free": "Бепул",
        "status_manual": "Қўлда чиқарилган",
        "status_online": "Онлайн тўланган",
        "status_exempt": "Имтиёзли",
    },
    "ru": {
        "site": "Автостоянка",
        "period": "Период",
        "days_sheet": "Дни",
        "day": "Дата",
        "entries": "Въехало",
        "exits": "Выехало",
        "cash": "Наличные (сум)",
        "terminal": "Терминал (сум)",
        "total": "Итого (сум)",
        "free": "Бесплатно",
        "grand_total": "ИТОГО",
        "sessions_sheet": "Машины",
        "plate": "Номер",
        "entered": "Въезд",
        "exited": "Выезд",
        "duration": "Длительность (мин)",
        "amount": "Сумма (сум)",
        "method": "Способ оплаты",
        "status": "Состояние",
        "method_cash": "Наличные",
        "method_terminal": "Терминал",
        "method_mixed": "Наличные + терминал",
        "status_open": "Внутри",
        "status_paid": "Оплачено",
        "status_free": "Бесплатно",
        "status_manual": "Выпущена вручную",
        "status_online": "Оплачено онлайн",
        "status_exempt": "Льгота",
    },
}
"""Hujjat matnlari — `xlsx_export._REPORT_TEXTS` naqshi, serverda tug'iladi.

⛔ UCH TILNING KALIT TO'PLAMI TENG bo'lishi SHART
  (`test_parking_report.py::test_every_locale_translates_every_key`).
"""

_METHOD_KEYS: Final[dict[str, str]] = {
    _METHOD_CASH: "method_cash",
    _METHOD_TERMINAL: "method_terminal",
    _METHOD_MIXED: "method_mixed",
}

_STATUS_KEYS: Final[dict[str, str]] = {
    "paid": "status_paid",
    "free": "status_free",
    "manual": "status_manual",
    "online": "status_online",
    "exempt": "status_exempt",
}


def parking_report_texts(locale: str) -> dict[str, str]:
    """Til uchun hujjat matnlari; noma'lum til `REPORT_DEFAULT_LOCALE` ga tushadi."""
    return _TEXTS.get(locale, _TEXTS[REPORT_DEFAULT_LOCALE])


def _label(texts: dict[str, str], keys: dict[str, str], value: str) -> str:
    """Yopiq to'plam a'zosining matni; NOMA'LUM qiymat XOM qaytadi (tarjima
    yetishmasligini ko'rsatadi, istisno ko'tarmaydi)."""
    key = keys.get(value)
    return value if key is None else texts[key]


def _stamp(value: datetime | None) -> str | None:
    """Lahza -> `DD.MM.YYYY HH:MM` Toshkent vaqtida; `None` -> bo'sh katak."""
    if value is None:
        return None
    return value.astimezone(TASHKENT).strftime(_DATETIME_FORMAT)


def _banner(worksheet: Any, texts: dict[str, str], site_name: str, label: str, bold: Any) -> None:
    """Ikki sarlavha qatori: obyekt nomi va davr — chop etilgan varaq
    kontekstsiz tarqaladi, davr fayl nomida yetarli emas (§1.2 qoida 2).

    Obyekt nomi DB kontenti (D-16) — tarjima qilinmaydi, lekin `write_text`
    orqali o'tadi: u foydalanuvchi kiritgan matn va `=` bilan boshlanishi
    mumkin.
    """
    write_text(worksheet, 0, 0, f"{texts['site']}: {site_name}", bold)
    write_text(worksheet, 1, 0, f"{texts['period']}: {label}", bold)


def build_parking_report_workbook(
    report: ParkingReport,
    *,
    locale: str,
    site_name: str,
) -> bytes:
    """Ikki varaqli `.xlsx`: kunlar (JAMI qatori bilan) va mashinalar.

    Arifmetika BU YERDA YO'Q (05-14 darsi): yig'indilar `report.total` dan
    ko'chiriladi, Excel formulasi yozilmaydi — fayl va ekran bir sonni
    ko'rsatadi.
    """
    texts = parking_report_texts(locale)
    period = ReportPeriod(from_date=report.from_date, to_date=report.to_date)
    buffer = io.BytesIO()
    workbook = new_workbook(buffer)
    try:
        bold = workbook.add_format({"bold": True})
        header = workbook.add_format({"bold": True, "bg_color": "#F2F2F2"})
        money = money_format(workbook)
        count = workbook.add_format({"num_format": COUNT_NUM_FORMAT})
        money_total = workbook.add_format({"bold": True, "num_format": MONEY_NUM_FORMAT})
        count_total = workbook.add_format({"bold": True, "num_format": COUNT_NUM_FORMAT})

        _write_days_sheet(
            workbook.add_worksheet(texts["days_sheet"]),
            report,
            texts,
            site_name,
            period,
            formats=(bold, header, money, count, money_total, count_total),
        )
        _write_sessions_sheet(
            workbook.add_worksheet(texts["sessions_sheet"]),
            report.sessions,
            texts,
            site_name,
            period,
            formats=(bold, header, money, count),
        )
    except BaseException:
        # `xlsx_export` quruvchilari bilan AYNI sabab: yopilmagan kitob
        # vaqtinchalik fayllarni ushlab qolardi.
        workbook.close()
        raise
    return finish(workbook, buffer)


_DAYS_HEADER_ROW: Final = 2
_DAYS_COLUMNS: Final = 7
_SESSIONS_COLUMNS: Final = 7


def _write_days_sheet(
    worksheet: Any,
    report: ParkingReport,
    texts: dict[str, str],
    site_name: str,
    period: ReportPeriod,
    *,
    formats: tuple[Any, Any, Any, Any, Any, Any],
) -> None:
    bold, header, money, count, money_total, count_total = formats
    _banner(worksheet, texts, site_name, period.label, bold)
    write_header(
        worksheet,
        _DAYS_HEADER_ROW,
        (
            texts["day"],
            texts["entries"],
            texts["exits"],
            texts["cash"],
            texts["terminal"],
            texts["total"],
            texts["free"],
        ),
        header,
    )
    first = _DAYS_HEADER_ROW + 1
    for offset, row in enumerate(report.days, start=first):
        # Sana ISO matn: uch tilda bir xil va Excelda saralanadi.
        write_text(worksheet, offset, 0, row.day.isoformat())
        write_optional_number(worksheet, offset, 1, row.entries, count)
        write_optional_number(worksheet, offset, 2, row.exits, count)
        write_money(worksheet, offset, 3, row.cash_soum, money)
        write_money(worksheet, offset, 4, row.terminal_soum, money)
        write_money(worksheet, offset, 5, row.total_soum, money)
        write_optional_number(worksheet, offset, 6, row.free_count, count)

    # ⚠ JAMI qatori FILTR DIAPAZONIDAN TASHQARIDA (bir qator tashlab):
    #   filtr ichidagi yig'indi saralashda ma'lumot qatori bo'lib
    #   o'rtaga chiqib ketardi (`build_three_way_workbook` imzo bloki
    #   bilan bir xil qoida).
    total_row = first + len(report.days) + 1
    total = report.total
    write_text(worksheet, total_row, 0, texts["grand_total"], bold)
    write_optional_number(worksheet, total_row, 1, total.entries, count_total)
    write_optional_number(worksheet, total_row, 2, total.exits, count_total)
    write_money(worksheet, total_row, 3, total.cash_soum, money_total)
    write_money(worksheet, total_row, 4, total.terminal_soum, money_total)
    write_money(worksheet, total_row, 5, total.total_soum, money_total)
    write_optional_number(worksheet, total_row, 6, total.free_count, count_total)

    layout_sheet(
        worksheet,
        header_row=_DAYS_HEADER_ROW,
        row_count=len(report.days),
        column_count=_DAYS_COLUMNS,
        widths=(14, 10, 10, 16, 16, 16, 10),
    )


def _write_sessions_sheet(
    worksheet: Any,
    sessions: Sequence[ParkingSessionRow],
    texts: dict[str, str],
    site_name: str,
    period: ReportPeriod,
    *,
    formats: tuple[Any, Any, Any, Any],
) -> None:
    bold, header, money, count = formats
    _banner(worksheet, texts, site_name, period.label, bold)
    write_header(
        worksheet,
        _DAYS_HEADER_ROW,
        (
            texts["plate"],
            texts["entered"],
            texts["exited"],
            texts["duration"],
            texts["amount"],
            texts["method"],
            texts["status"],
        ),
        header,
    )
    for offset, row in enumerate(sessions, start=_DAYS_HEADER_ROW + 1):
        # Raqam TASHQI MATN (kamera o'qigan) — `write_optional_text`
        # `escape_formula` dan o'tadi; `None` esa bo'sh katak, «—» emas.
        write_optional_text(worksheet, offset, 0, row.plate)
        write_optional_text(worksheet, offset, 1, _stamp(row.entered_at))
        write_optional_text(worksheet, offset, 2, _stamp(row.exited_at))
        write_optional_number(worksheet, offset, 3, row.duration_minutes, count)
        write_money(worksheet, offset, 4, row.amount_soum, money)
        write_optional_text(
            worksheet,
            offset,
            5,
            None if row.method is None else _label(texts, _METHOD_KEYS, row.method),
        )
        write_text(
            worksheet,
            offset,
            6,
            texts["status_open"] if row.reason is None else _label(texts, _STATUS_KEYS, row.reason),
        )

    layout_sheet(
        worksheet,
        header_row=_DAYS_HEADER_ROW,
        row_count=len(sessions),
        column_count=_SESSIONS_COLUMNS,
        widths=(14, 18, 18, 18, 16, 20, 20),
    )
