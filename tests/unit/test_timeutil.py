"""`sbozor_core.timeutil` — Asia/Tashkent biznes-kuni chegarasi (FOUND-05).

Konteynerlar UTC soatida ishlaydi. Mahalliy 00:00–04:59 oralig'idagi HAR BIR
yozuv naive UTC sanasida OLDINGI kunga tushadi — ya'ni to'lov va hisob turli
kunlarga ajraladi. Bu fayl chegarani raqam bilan qulflaydi; RESEARCH Pattern 7
dagi o'lchangan jadval bu yerda test sifatida takrorlangan.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta, timezone

import pytest
from sbozor_core.timeutil import MARKET_TZ, business_date, now_tz


def test_market_tz_is_asia_tashkent() -> None:
    assert MARKET_TZ.key == "Asia/Tashkent"


def test_market_tz_offset_is_plus_five_without_dst() -> None:
    """O'zbekistonda yozgi vaqt yo'q — yanvarda ham, iyulda ham +05:00."""
    winter = datetime(2026, 1, 15, 12, 0, tzinfo=MARKET_TZ)
    summer = datetime(2026, 7, 15, 12, 0, tzinfo=MARKET_TZ)
    assert winter.utcoffset() == timedelta(hours=5)
    assert summer.utcoffset() == timedelta(hours=5)


def test_now_tz_is_aware_and_in_market_tz() -> None:
    moment = now_tz()
    assert moment.tzinfo is not None
    assert moment.utcoffset() == timedelta(hours=5)


@pytest.mark.parametrize(
    ("moment", "expected"),
    [
        # RESEARCH Pattern 7 chegara jadvali (empirik o'lchangan)
        (datetime(2026, 11, 5, 18, 30, tzinfo=UTC), date(2026, 11, 5)),  # 23:30 Toshkent
        (datetime(2026, 11, 5, 19, 30, tzinfo=UTC), date(2026, 11, 6)),  # 00:30 -> KUN SURILADI
        (datetime(2026, 11, 5, 1, 0, tzinfo=UTC), date(2026, 11, 5)),  # 06:00 Toshkent
        # Yarim tunning ikki tomoni — bir soniya farq bilan
        (datetime(2026, 11, 5, 18, 59, 59, tzinfo=UTC), date(2026, 11, 5)),  # 23:59:59
        (datetime(2026, 11, 5, 19, 0, 0, tzinfo=UTC), date(2026, 11, 6)),  # 00:00:00
        # Yil chegarasi
        (datetime(2026, 12, 31, 18, 59, 59, tzinfo=UTC), date(2026, 12, 31)),
        (datetime(2026, 12, 31, 19, 0, 0, tzinfo=UTC), date(2027, 1, 1)),
    ],
)
def test_business_date_boundary_table(moment: datetime, expected: date) -> None:
    assert business_date(moment) == expected


def test_business_date_differs_from_naive_utc_date_after_local_midnight() -> None:
    """Regressiya qopqoni: `moment.date()` aynan shu holatda XATO javob beradi."""
    moment = datetime(2026, 11, 5, 19, 30, tzinfo=UTC)
    assert moment.date() == date(2026, 11, 5)
    assert business_date(moment) == date(2026, 11, 6)


def test_business_date_accepts_market_local_datetime() -> None:
    local = datetime(2026, 11, 6, 0, 30, tzinfo=MARKET_TZ)
    assert business_date(local) == date(2026, 11, 6)


def test_business_date_normalises_arbitrary_offset() -> None:
    """+07:00 dagi 02:30 = 19:30Z = Toshkentda 00:30 (ertasi kun)."""
    moment = datetime(2026, 11, 6, 2, 30, tzinfo=timezone(timedelta(hours=7)))
    assert business_date(moment) == date(2026, 11, 6)


@pytest.mark.parametrize(
    "naive",
    [
        datetime(2026, 11, 5, 19, 30),
        datetime(2026, 11, 5, 0, 0),
        datetime(2026, 1, 1, 12, 0),
    ],
)
def test_business_date_rejects_naive_datetime(naive: datetime) -> None:
    """Naive datetime TAQIQLANGAN — jimgina noto'g'ri kun beradi."""
    with pytest.raises(ValueError):
        business_date(naive)


def test_business_date_returns_date_not_datetime() -> None:
    result = business_date(datetime(2026, 11, 5, 19, 30, tzinfo=UTC))
    assert isinstance(result, date)
    assert not isinstance(result, datetime)


def test_now_tz_business_date_round_trip() -> None:
    """`business_date(now_tz())` hech qachon xato ko'tarmaydi."""
    assert isinstance(business_date(now_tz()), date)
