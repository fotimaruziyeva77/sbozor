"""«To'lov bor, hisob yo'q» alertining sof qismlari — bazasiz (2026-09-24).

Prod'da 28 kun davomida patta hisobi yozilmadi va buni hech nima aytmadi:
`billing_close` har kecha ishladi (yurak urishi yangi), natijasi esa 0 edi.
Bu fayl alertning ikki qaror nuqtasini o'lchaydi — QAYSI kun tekshiriladi
va QACHON signal chiqadi. Haqiqiy SQL `tests/integration/test_alerting.py`
da o'lchanadi.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest
from app.jobs.alerting import (
    ALERT_META,
    BILLING_SILENCE_FROM_HOUR,
    NEVER_SUPPRESSED_ALERT_KEYS,
    PLATFORM_SCOPED_ALERT_KEYS,
    billing_silence_signals,
    last_closed_day,
)
from sbozor_core.enums import AlertSeverity
from sbozor_core.timeutil import MARKET_TZ

KEY = "billing_no_charges"


@pytest.mark.parametrize(
    ("moment", "expected"),
    [
        # Chegaradan oldin — kechaning hisobi hali QONUNIY yo'q (04:10 cron).
        (
            datetime(2026, 9, 24, BILLING_SILENCE_FROM_HOUR - 1, 59, tzinfo=MARKET_TZ),
            date(2026, 9, 22),
        ),
        # Chegaraning o'zi — kecha tekshiriladi (`>=`).
        (datetime(2026, 9, 24, BILLING_SILENCE_FROM_HOUR, 0, tzinfo=MARKET_TZ), date(2026, 9, 23)),
        (datetime(2026, 9, 24, 23, 59, tzinfo=MARKET_TZ), date(2026, 9, 23)),
        # UTC payt Toshkentga o'giriladi: 00:30 UTC = 05:30 Toshkent.
        (datetime(2026, 9, 24, 0, 30, tzinfo=UTC), date(2026, 9, 22)),
        # 20:00 UTC — Toshkentda ERTASI kun 01:00, ya'ni biznes-kun 25-sentabr.
        (datetime(2026, 9, 24, 20, 0, tzinfo=UTC), date(2026, 9, 23)),
    ],
)
def test_the_checked_day_never_jumps_at_midnight(moment: datetime, expected: date) -> None:
    """⛔ Oyna yarim tunda kechaga ko'chmaydi — aks holda ochiq alert har kecha
    «tiklanib» ertalab qayta tug'ilardi (konstanta docstringi)."""
    assert last_closed_day(moment) == expected


def test_payments_without_charges_on_an_open_day_raise_one_signal() -> None:
    signals = billing_silence_signals(market_open=True, payment_count=37, charge_count=0)

    assert [signal.key for signal in signals] == [KEY]
    assert signals[0].subject_id is None, "signal butun bozorga tegishli, bitta rastaga emas"
    assert signals[0].detail == {}


@pytest.mark.parametrize(
    ("market_open", "payment_count", "charge_count", "why"),
    [
        (False, 12, 0, "yopiq kunda hisob QONUNIY yo'q (D-10) — eski qarz undirilishi mumkin"),
        (True, 0, 0, "to'lovsiz ochiq kun — bo'sh bozor, uzilish emas (bayram)"),
        (True, 40, 1, "bitta hisob ham bo'lsa job natija bergan"),
        (True, 40, 42, "normal kun"),
    ],
)
def test_the_signal_stays_silent_outside_the_outage(
    market_open: bool, payment_count: int, charge_count: int, why: str
) -> None:
    signals = billing_silence_signals(
        market_open=market_open, payment_count=payment_count, charge_count=charge_count
    )
    assert signals == [], why


def test_the_alert_is_a_debounced_market_level_warning() -> None:
    meta = ALERT_META[KEY]

    assert meta.severity == AlertSeverity.WARNING.value, (
        "`critical` bo'lib tug'ilsa eskalatsiya o'tkinchi holatni qotgan uzilishdan ajratmasdi"
    )
    assert KEY not in NEVER_SUPPRESSED_ALERT_KEYS, (
        "shart butun kun rost turadi — debounce'siz supurgi har 5 daqiqada xabar yuborardi"
    )
    assert KEY not in PLATFORM_SCOPED_ALERT_KEYS, "har bozor direktori O'Z holatini ko'rishi kerak"
    assert meta.storable
