"""Avtoturargoh davr hisoboti — `app.services.parking_report` ning sof hisobi va `.xlsx` i.

Hodisalar DB'SIZ, oddiy obyekt sifatida beriladi (`EventLike` protokoli) —
ya'ni bu to'plam konteynersiz yuguradi. Har `.xlsx` da'vosi HOSIL BO'LGAN
FAYLNI qayta o'qiydi (`test_xlsx_export.py` bilan bir xil sabab:
«funksiya chaqirildi» degan da'vo ikkinchi yozish yo'li ochilganda ham
yashil qolardi).
"""

from __future__ import annotations

import ast
import io
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import openpyxl
import pytest
from app.services import parking_report
from app.services.parking_report import (
    DAY_START_HOUR,
    EVENT_TYPES,
    MAX_PERIOD_DAYS,
    SUMMARY_MAX_PERIOD_DAYS,
    ParkingReport,
    build_parking_report,
    build_parking_report_workbook,
    business_day_of,
    business_day_start,
    parking_report_texts,
)

FROM = date(2026, 10, 1)
TO = date(2026, 10, 2)
SITE = "Test turargoh"


@dataclass(frozen=True, slots=True)
class Event:
    """`edge_repo.EventRow` ning hisobot o'qiydigan to'rt maydoni."""

    type: str
    occurred_at: datetime
    data: dict[str, Any] = field(default_factory=dict)
    correlation_id: UUID | None = None


def utc(month: int, day: int, hour: int, minute: int = 0) -> datetime:
    """UTC lahza. Toshkent = UTC+5: 18:30Z -> 23:30, 19:10Z -> ertasi 00:10."""
    return datetime(2026, month, day, hour, minute, tzinfo=UTC)


A = "0b7c2a52-6a0e-4d43-9a7e-3f1f0c9d2b11"
B = str(uuid4())
C = str(uuid4())
D = str(uuid4())
E = str(uuid4())


def opened(session_id: str, at: datetime, plate: str | None = None) -> Event:
    data: dict[str, Any] = {
        "session_id": session_id,
        "lane_id": "kirish-1",
        "category": "car",
        "reason": "auto" if plate else "no_plate",
    }
    if plate is not None:
        data["plate"] = plate
    return Event("parking.session.opened", at, data)


def closed(session_id: str, at: datetime, *, amount: int, reason: str, **extra: Any) -> Event:
    return Event(
        "parking.session.closed",
        at,
        {"session_id": session_id, "lane_id": "chiqish-1", "amount_soum": amount, "reason": reason}
        | extra,
    )


def payment(
    at: datetime,
    *,
    amount: int,
    method: str,
    subject_id: str | None = None,
    correlation_id: str | None = None,
    subject_kind: str = "parking_session",
) -> Event:
    data: dict[str, Any] = {
        "payment_id": str(uuid4()),
        "amount_soum": amount,
        "method": method,
        "staff_id": "u-17",
        "fiscal_status": "manual",
    }
    if subject_id is not None:
        data["subject"] = {"kind": subject_kind, "id": subject_id}
    return Event(
        "core.payment.cash",
        at,
        data,
        None if correlation_id is None else UUID(correlation_id),
    )


def sample_events() -> list[Event]:
    """Ikki kunlik stsenariy — har seans boshqa bir chekka holatni o'lchaydi.

    * A — 23:30 da kirdi, ertasi 00:10 da chiqdi (ikki kunga bo'linadi),
          naqd to'lov `subject` orqali bog'langan;
    * B — raqamsiz kirish, BEPUL chiqish, `duration_minutes` yo'q (hisoblanadi);
    * C — hali ichkarida (faqat `opened`);
    * D — ikki to'lov (naqd `subject` + terminal `correlation_id`) -> aralash;
    * E — raqami formula bilan boshlanadi (hujum matni), qo'lda chiqarilgan;
    * bog'lanmagan to'lov (rasta uchun) kunlik yig'indiga kiradi, seansga emas;
    * davrdan TASHQARIDAGI to'lov kunlik jadvalga kirmaydi.
    """
    return [
        # Tartib ATAYIN aralash — funksiya o'zi saralashi kerak.
        payment(utc(10, 1, 19, 9), amount=5000, method="cash", subject_id=A),
        closed(A, utc(10, 1, 19, 10), amount=5000, reason="paid", duration_minutes=40),
        opened(A, utc(10, 1, 18, 30), plate="01A123BC"),
        opened(B, utc(10, 2, 3, 0)),
        closed(B, utc(10, 2, 4, 0), amount=0, reason="free"),
        opened(C, utc(10, 2, 5, 0), plate="20B456CD"),
        opened(D, utc(10, 2, 6, 0), plate="30C789EF"),
        closed(D, utc(10, 2, 8, 0), amount=12000, reason="paid"),
        payment(utc(10, 2, 7, 55), amount=5000, method="cash", subject_id=D),
        payment(utc(10, 2, 7, 58), amount=7000, method="terminal", correlation_id=D),
        opened(E, utc(10, 2, 9, 0), plate="=HYPERLINK(1)"),
        closed(E, utc(10, 2, 9, 30), amount=0, reason="manual"),
        payment(
            utc(10, 1, 7, 0), amount=3000, method="cash", subject_id="R-12", subject_kind="stall"
        ),
        payment(utc(9, 30, 10, 0), amount=99_000, method="cash", subject_id=A),
    ]


@pytest.fixture
def report() -> ParkingReport:
    return build_parking_report(sample_events(), from_date=FROM, to_date=TO)


def open_book(raw: bytes) -> openpyxl.Workbook:
    return openpyxl.load_workbook(io.BytesIO(raw))


# ---------------------------------------------------------------------------
# Sof hisob
# ---------------------------------------------------------------------------


def test_days_are_business_days_from_six_and_every_day_of_the_period_is_present(
    report: ParkingReport,
) -> None:
    """A 18:30Z da kirdi (Toshkent 23:30) va 19:10Z da chiqdi (00:10) — ikkalasi ham
    1-ish kuniga: kun 06:00 da almashadi (2026-11-03 qarori)."""
    assert [d.day for d in report.days] == [FROM, TO]

    first, second = report.days
    assert (first.entries, first.exits) == (1, 1)
    # 2-kun: B, C, D, E kirdi; B, D, E chiqdi — C hali ichkarida.
    assert (second.entries, second.exits) == (4, 3)


def test_the_day_turns_over_at_six_in_the_morning() -> None:
    """05:59 dagi chiqish — kechagi kunniki, 06:00 dagi kirish — bugungi."""
    late = closed(B, utc(10, 2, 0, 59), amount=0, reason="free")
    early = opened(C, utc(10, 2, 1, 0), plate="20B456CD")
    built = build_parking_report([late, early], from_date=FROM, to_date=TO)
    first, second = built.days
    assert (first.entries, first.exits) == (0, 1)
    assert (second.entries, second.exits) == (1, 0)
    assert business_day_of(utc(10, 2, 0, 59)) == FROM
    assert business_day_of(utc(10, 2, 1, 0)) == TO
    assert business_day_start(TO) == utc(10, 2, 1, 0)


def test_money_comes_from_payment_events_split_by_method(report: ParkingReport) -> None:
    """Pul `core.payment.cash` dan: bog'lanmagan to'lov ham kunga kiradi,
    davrdan tashqaridagi (99 000) esa KIRMAYDI."""
    first, second = report.days
    # A ning 00:09 dagi to'lovi ham 1-ish kunida (06:00 dan oldin).
    assert (first.cash_soum, first.terminal_soum, first.total_soum) == (8000, 0, 8000)
    assert (second.cash_soum, second.terminal_soum, second.total_soum) == (5000, 7000, 12_000)
    assert (first.free_count, second.free_count) == (0, 1)


def test_total_is_the_column_sum_of_the_days(report: ParkingReport) -> None:
    total = report.total
    assert (total.entries, total.exits) == (5, 4)
    assert (total.cash_soum, total.terminal_soum, total.total_soum) == (13_000, 7000, 20_000)
    assert total.free_count == 1


def test_sessions_are_joined_by_session_id_and_sorted_by_entry(report: ParkingReport) -> None:
    rows = {row.session_id: row for row in report.sessions}
    assert [row.session_id for row in report.sessions] == [A, B, C, D, E]

    a = rows[A]
    assert a.plate == "01A123BC"
    assert a.entered_at == utc(10, 1, 18, 30)
    assert a.exited_at == utc(10, 1, 19, 10)
    assert a.duration_minutes == 40  # `closed.duration_minutes` ustun
    assert (a.amount_soum, a.method, a.reason) == (5000, "cash", "paid")

    b = rows[B]
    assert b.plate is None  # `no_plate` — bo'sh, «—» emas
    assert b.duration_minutes == 60  # hodisada yo'q -> vaqtlardan hisoblandi
    assert (b.amount_soum, b.method, b.reason) == (0, None, "free")

    c = rows[C]
    assert c.exited_at is None and c.duration_minutes is None
    assert (c.amount_soum, c.method, c.reason) == (0, None, None)

    d = rows[D]
    assert d.duration_minutes == 120
    assert (d.amount_soum, d.method) == (12_000, "mixed")  # subject + correlation_id


def test_unlinked_payment_does_not_create_a_session(report: ParkingReport) -> None:
    assert "R-12" not in {row.session_id for row in report.sessions}


def test_closed_without_opened_is_a_session_with_unknown_entry() -> None:
    """Davr boshidan oldin kirgan mashina: `opened` tanlovga tushmagan —
    qator bor, kirgan vaqti va raqami BO'SH (to'qilmaydi)."""
    built = build_parking_report(
        [closed(A, utc(10, 1, 3, 0), amount=4000, reason="paid")], from_date=FROM, to_date=FROM
    )
    (row,) = built.sessions
    assert row.plate is None and row.entered_at is None
    assert row.exited_at == utc(10, 1, 3, 0)
    assert row.duration_minutes is None
    assert row.amount_soum == 4000  # to'lov hodisasi yo'q -> `closed.amount_soum`
    assert built.days[0].exits == 1 and built.days[0].total_soum == 0


def test_out_of_range_events_touch_neither_days_nor_sessions() -> None:
    """Davrdan tashqaridagi to'lov (99 000) A seansining summasiga QO'SHILMAYDI —
    aks holda varaqdagi «Summa» kunlik «Jami» bilan ajralib ketardi."""
    built = build_parking_report(sample_events(), from_date=FROM, to_date=TO)
    a = next(row for row in built.sessions if row.session_id == A)
    assert a.amount_soum == 5000
    assert built.total.total_soum == 20_000


def test_period_without_events_yields_zero_rows_not_an_empty_list() -> None:
    built = build_parking_report([], from_date=FROM, to_date=date(2026, 10, 3))
    assert len(built.days) == 3
    assert all(d.entries == d.exits == d.total_soum == d.free_count == 0 for d in built.days)
    assert built.sessions == ()


def test_inverted_period_is_rejected() -> None:
    with pytest.raises(ValueError, match="from_date"):
        build_parking_report([], from_date=TO, to_date=FROM)


def test_event_types_and_period_limit_are_locked() -> None:
    """Marshrut aynan shu uch turni so'raydi va 92 kundan oshirmaydi."""
    assert set(EVENT_TYPES) == {
        "parking.session.opened",
        "parking.session.closed",
        "core.payment.cash",
    }
    assert MAX_PERIOD_DAYS == 92
    assert SUMMARY_MAX_PERIOD_DAYS == 366
    assert DAY_START_HOUR == 6


# ---------------------------------------------------------------------------
# Panel grafiklari uchun yig'indilar
# ---------------------------------------------------------------------------

FRAME = "ab" * 32


def test_hours_are_tashkent_hours_and_add_up_to_the_totals(report: ParkingReport) -> None:
    """A 23:30 da kirdi va 00:10 da chiqdi — kirish 23-soatga, chiqish 0-soatga."""
    assert [row.hour for row in report.hours] == list(range(24))
    entries = {row.hour: row.entries for row in report.hours if row.entries}
    exits = {row.hour: row.exits for row in report.hours if row.exits}
    assert entries == {8: 1, 10: 1, 11: 1, 14: 1, 23: 1}
    assert exits == {0: 1, 9: 1, 13: 1, 14: 1}
    assert sum(entries.values()) == report.total.entries
    assert sum(exits.values()) == report.total.exits


def test_exit_reasons_follow_a_fixed_order_and_add_up_to_exits(report: ParkingReport) -> None:
    assert [(item.reason, item.count) for item in report.exit_reasons] == [
        ("paid", 2),
        ("online", 0),
        ("free", 1),
        ("exempt", 0),
        ("manual", 1),
    ]
    assert sum(item.count for item in report.exit_reasons) == report.total.exits


def test_unknown_or_missing_exit_reason_is_counted_as_other() -> None:
    """Agentning yangi sababi yoki bo'sh sabab yo'qolmaydi — `other` oxirida."""
    events = [
        closed(A, utc(10, 1, 6, 0), amount=0, reason="towed"),
        Event("parking.session.closed", utc(10, 1, 7, 0), {"session_id": B, "amount_soum": 0}),
    ]
    built = build_parking_report(events, from_date=FROM, to_date=FROM)
    assert built.exit_reasons[-1].reason == "other"
    assert built.exit_reasons[-1].count == 2
    assert sum(item.count for item in built.exit_reasons) == built.total.exits == 2


def test_stay_counts_only_closed_sessions_with_a_known_duration(report: ParkingReport) -> None:
    """A 40 (hodisadan), B 60, D 120, E 30 daqiqa; C hali ichkarida — kirmaydi."""
    stay = report.stay
    assert stay.measured == 4
    assert stay.median_minutes == 40  # [30, 40, 60, 120] — pastki o'rta
    assert [(bucket.key, bucket.count) for bucket in stay.buckets] == [
        ("under_15m", 0),
        ("under_1h", 2),
        ("under_2h", 1),
        ("under_4h", 1),
        ("under_8h", 0),
        ("over_8h", 0),
    ]


def test_session_registered_at_exit_is_flagged_and_left_out_of_stay() -> None:
    """Kirish kamerasi ko'rmagan mashina chiqishda ro'yxatga olinadi: seans
    chiqish yo'lagida ochilib, o'sha zahoti yopiladi. Uning «0 daqiqa» si
    turish vaqti EMAS — taqsimotga kirmaydi, alohida sanaladi.

    Ikki tomonlama yo'lak: bir yo'lakda ochilib SOATLAB keyin yopilgan seans
    haqiqiy turish va belgilanmaydi."""
    at_exit = opened(A, utc(10, 1, 5, 0), plate="85W523OA")
    at_exit.data["lane_id"] = "chiqish-1"
    two_way = opened(B, utc(10, 1, 3, 0), plate="85V230OA")
    two_way.data["lane_id"] = "chiqish-1"
    events = [
        at_exit,
        closed(A, utc(10, 1, 5, 0), amount=4000, reason="paid", duration_minutes=0),
        two_way,
        closed(B, utc(10, 1, 5, 0), amount=8000, reason="paid"),
        opened(C, utc(10, 1, 4, 0), plate="01A123BC"),
        closed(C, utc(10, 1, 4, 30), amount=4000, reason="paid"),
    ]
    built = build_parking_report(events, from_date=FROM, to_date=FROM)
    rows = {row.session_id: row for row in built.sessions}
    assert rows[A].opened_at_exit is True
    assert rows[B].opened_at_exit is False
    assert rows[C].opened_at_exit is False
    assert built.stay.unrecorded_entries == 1
    assert built.stay.measured == 2
    assert built.stay.median_minutes == 30  # [30, 120] — A ning noli kirmadi


def test_regulars_skip_text_without_digits() -> None:
    """Kameraning `UNKNOWN` i raqam emas — doimiy mashinalar ro'yxatiga tushmaydi."""
    events = []
    for hour in (3, 4, 5):
        sid = str(uuid4())
        events += [
            opened(sid, utc(10, 1, hour, 0), plate="UNKNOWN"),
            closed(sid, utc(10, 1, hour, 30), amount=4000, reason="paid"),
        ]
    built = build_parking_report(events, from_date=FROM, to_date=FROM)
    assert built.regulars == ()
    assert [row.plate for row in built.sessions] == ["UNKNOWN"] * 3  # seansda xom qoladi


def test_stay_buckets_are_contiguous_and_open_ended() -> None:
    """Har daqiqa AYNAN bitta guruhga tushadi — oraliq yo'q, ustma-ust tushish yo'q."""
    assert parking_report.STAY_BUCKETS[0][1] == 0
    assert parking_report.STAY_BUCKETS[-1][2] is None
    for (_, _, high), (_, low, _) in zip(
        parking_report.STAY_BUCKETS, parking_report.STAY_BUCKETS[1:], strict=False
    ):
        assert high == low


def test_empty_period_has_no_median_and_no_average_check() -> None:
    built = build_parking_report([], from_date=FROM, to_date=FROM)
    assert built.stay.measured == 0
    assert built.stay.unrecorded_entries == 0
    assert built.stay.median_minutes is None
    assert all(bucket.count == 0 for bucket in built.stay.buckets)
    assert (built.inside, built.paid_sessions, built.average_check_soum) == (0, 0, None)
    assert built.regulars == ()
    assert len(built.hours) == 24


def test_inside_paid_sessions_and_average_check(report: ParkingReport) -> None:
    """C ichkarida; to'langan seanslar A (5 000) va D (12 000) — o'rtacha 8 500."""
    assert report.inside == 1
    assert report.paid_sessions == 2
    assert report.average_check_soum == 8500


def test_average_check_rounds_half_up_to_whole_soum() -> None:
    events = [
        closed(A, utc(10, 1, 6, 0), amount=1000, reason="paid"),
        closed(B, utc(10, 1, 7, 0), amount=2001, reason="paid"),
    ]
    built = build_parking_report(events, from_date=FROM, to_date=FROM)
    assert built.average_check_soum == 1501  # 1500.5 -> 1501


def test_entry_frame_comes_from_opened_and_is_validated() -> None:
    """Kadr — `opened.file_id`; SHA-256 hex bo'lmagan qiymat panelga chiqmaydi."""
    good = opened(A, utc(10, 1, 6, 0), plate="01A123BC")
    good.data["file_id"] = FRAME
    bad = opened(B, utc(10, 1, 6, 5), plate="01B456CD")
    bad.data["file_id"] = "../../etc/passwd"
    built = build_parking_report([good, bad], from_date=FROM, to_date=FROM)
    rows = {row.session_id: row for row in built.sessions}
    assert rows[A].entry_file_id == FRAME
    assert rows[B].entry_file_id is None


def test_regulars_need_two_visits_and_rank_by_visits_then_money() -> None:
    def visit(plate: str, hour: int, amount: int) -> list[Event]:
        sid = str(uuid4())
        return [
            opened(sid, utc(10, 1, hour, 0), plate=plate),
            closed(sid, utc(10, 1, hour, 30), amount=amount, reason="paid" if amount else "free"),
        ]

    events = [
        *visit("01A111AA", 3, 4000),
        *visit("01A111AA", 5, 0),
        *visit("01A111AA", 7, 4000),
        *visit("01B222BB", 4, 8000),
        *visit("01B222BB", 6, 8000),
        *visit("01C333CC", 8, 4000),
        *visit("01C333CC", 9, 0),
        *visit("01D444DD", 10, 99_000),  # bir marta — doimiy emas
    ]
    built = build_parking_report(events, from_date=FROM, to_date=FROM)
    assert [(r.plate, r.visits, r.amount_soum) for r in built.regulars] == [
        ("01A111AA", 3, 8000),
        ("01B222BB", 2, 16_000),
        ("01C333CC", 2, 4000),
    ]
    assert built.regulars[0].last_seen_at == utc(10, 1, 7, 30)


def test_regulars_list_is_capped() -> None:
    events: list[Event] = []
    for n in range(parking_report.REGULARS_LIMIT + 3):
        for hour in (3, 4):
            sid = str(uuid4())
            events.append(opened(sid, utc(10, 1, hour, n), plate=f"01A{n:03d}AA"))
    built = build_parking_report(events, from_date=FROM, to_date=FROM)
    assert len(built.regulars) == parking_report.REGULARS_LIMIT


# ---------------------------------------------------------------------------
# `.xlsx`
# ---------------------------------------------------------------------------


def test_workbook_has_two_sheets_named_in_the_requested_locale(report: ParkingReport) -> None:
    uz = open_book(build_parking_report_workbook(report, locale="uz-Latn", site_name=SITE))
    ru = open_book(build_parking_report_workbook(report, locale="ru", site_name=SITE))
    assert uz.sheetnames == ["Kunlar", "Mashinalar"]
    assert ru.sheetnames == ["Дни", "Машины"]


def test_days_sheet_carries_site_period_bold_header_and_a_total_row(
    report: ParkingReport,
) -> None:
    book = open_book(build_parking_report_workbook(report, locale="uz-Latn", site_name=SITE))
    sheet = book["Kunlar"]

    assert sheet.cell(row=1, column=1).value == f"Avtoturargoh: {SITE}"
    assert sheet.cell(row=2, column=1).value == "Davr: 2026-10-01 — 2026-10-02"

    header = [sheet.cell(row=3, column=c).value for c in range(1, 8)]
    assert header == [
        "Sana",
        "Kirdi",
        "Chiqdi",
        "Naqd (so'm)",
        "Terminal (so'm)",
        "Jami (so'm)",
        "Bepul",
    ]
    assert all(sheet.cell(row=3, column=c).font.bold for c in range(1, 8))

    assert [sheet.cell(row=4, column=c).value for c in range(1, 8)] == [
        "2026-10-01", 1, 1, 8000, 0, 8000, 0
    ]  # fmt: skip
    assert [sheet.cell(row=5, column=c).value for c in range(1, 8)] == [
        "2026-10-02", 4, 3, 5000, 7000, 12_000, 1
    ]  # fmt: skip

    # JAMI — bir qator tashlab (filtr diapazonidan tashqarida), qalin.
    assert sheet.cell(row=6, column=1).value is None
    total = [sheet.cell(row=7, column=c).value for c in range(1, 8)]
    assert total == ["JAMI", 5, 4, 13_000, 7000, 20_000, 1]
    assert sheet.cell(row=7, column=1).font.bold
    assert sheet.cell(row=7, column=6).font.bold

    # Pul SON bo'lib va pul formati bilan yozilgan — matn emas.
    assert sheet.cell(row=5, column=6).number_format == "#,##0"
    assert sheet.freeze_panes == "A4"


def test_sessions_sheet_formats_tashkent_time_and_translates_closed_sets(
    report: ParkingReport,
) -> None:
    book = open_book(build_parking_report_workbook(report, locale="uz-Latn", site_name=SITE))
    sheet = book["Mashinalar"]

    assert [sheet.cell(row=3, column=c).value for c in range(1, 8)] == [
        "Raqam",
        "Kirgan",
        "Chiqqan",
        "Davomiyligi (daq)",
        "Summa (so'm)",
        "To'lov usuli",
        "Holat",
    ]

    a = [sheet.cell(row=4, column=c).value for c in range(1, 8)]
    assert a == ["01A123BC", "01.10.2026 23:30", "02.10.2026 00:10", 40, 5000, "Naqd", "To'langan"]

    b = [sheet.cell(row=5, column=c).value for c in range(1, 8)]
    assert b[0] is None and b[3] == 60 and b[5] is None and b[6] == "Bepul"

    c = [sheet.cell(row=6, column=c).value for c in range(1, 8)]
    assert c[2] is None and c[3] is None and c[6] == "Ichkarida"

    d = [sheet.cell(row=7, column=c).value for c in range(1, 8)]
    assert d[4] == 12_000 and d[5] == "Naqd + terminal"


def test_plate_that_looks_like_a_formula_is_escaped(report: ParkingReport) -> None:
    """Kamera o'qigan raqam TASHQI matn: `=HYPERLINK(...)` direktorning
    Excelida formula bo'lib bajarilmasin (OWASP, `xlsx_export` 3-fakt)."""
    book = open_book(build_parking_report_workbook(report, locale="uz-Latn", site_name=SITE))
    cell = book["Mashinalar"].cell(row=8, column=1)
    assert cell.data_type == "s"
    assert cell.value == "'=HYPERLINK(1)"


def test_site_name_is_escaped_too(report: ParkingReport) -> None:
    book = open_book(
        build_parking_report_workbook(report, locale="uz-Latn", site_name="=cmd|' /C calc'!A0")
    )
    assert book["Kunlar"].cell(row=1, column=1).value == "Avtoturargoh: =cmd|' /C calc'!A0"


def test_workbook_bytes_are_deterministic(report: ParkingReport) -> None:
    first = build_parking_report_workbook(report, locale="ru", site_name=SITE)
    second = build_parking_report_workbook(report, locale="ru", site_name=SITE)
    assert first == second


def test_unknown_locale_falls_back_to_uz_latn(report: ParkingReport) -> None:
    assert build_parking_report_workbook(
        report, locale="tr", site_name=SITE
    ) == build_parking_report_workbook(report, locale="uz-Latn", site_name=SITE)


@pytest.mark.parametrize("locale", ["uz-Latn", "uz-Cyrl", "ru"])
def test_every_locale_translates_every_key(locale: str) -> None:
    """Uch tilning kalit to'plami AYNAN TENG — yarim tarjima bo'sh sarlavha berardi."""
    assert set(parking_report_texts(locale)) == set(parking_report_texts("uz-Latn"))


def test_raw_worksheet_writes_live_only_in_xlsx_export() -> None:
    """Yozish intizomi (`xlsx_export` 2-fakt) BU MODULGA HAM tegishli:
    `worksheet.write*` bu yerda umuman chaqirilmaydi — faqat `xlsx_export`
    yordamchilari (ular `escape_formula` dan o'tadi)."""
    tree = ast.parse(Path(parking_report.__file__).read_text(encoding="utf-8"))
    raw = [
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "worksheet"
    ]
    assert raw == [], f"xom yozish yo'li ochilgan: {raw}"
