"""`business_date` — biznes-kun chegarasi DB tomonda (FOUND-05, mezon #4).

=============================================================================
NIMA O'LCHANADI VA NEGA (RESEARCH Pattern 7 / Pitfall 6, empirik):

Konteynerlar UTC soatida ishlaydi, Toshkent esa UTC+5 (yozgi vaqt YO'Q).
Ya'ni MAHALLIY 00:00–04:59 oralig'idagi har bir yozuv naive UTC sanasida
OLDINGI kunga tushadi. Bu — mahsulot bartaraf etadigan rekonsiliatsiyaning
o'zi: to'lov qaysi kunga tegishli ekanida kelishmovchilik.

| UTC vaqt            | Toshkent devor-vaqti | `business_date` | naive `::date` |
| ------------------- | -------------------- | --------------- | -------------- |
| 2026-11-05 18:30Z   | 2026-11-05 23:30     | 2026-11-05      | 2026-11-05     |
| 2026-11-05 19:30Z   | 2026-11-06 00:30     | **2026-11-06**  | XATO 2026-11-05|
| 2026-11-05 01:00Z   | 2026-11-05 06:00     | 2026-11-05      | 2026-11-05     |

Uchinchi ustun DB'dan, to'rtinchisi esa XATO NAQSHNING qanday ko'rinishini
ko'rsatadi — u testda ATAYIN o'lchanadi, aks holda "to'g'ri javob" va
"tasodifan mos kelgan javob" farqlanmaydi.
=============================================================================

Ikki qatlam mosligi ham shu yerda qulflanadi: DB natijasi
`sbozor_core.timeutil.business_date()` bilan AYNAN mos bo'lishi shart.
Ular ajralib ketsa hisobot va yozuv boshqa-boshqa kunni ko'rsatadi.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

import psycopg
import pytest
from sbozor_core.timeutil import business_date

from fixtures.financial import CHILD_TABLE, INSERT_CHARGE_AT, FinancialProbe

# RESEARCH Pattern 7 dagi o'lchangan chegara jadvali.
EVENING_UTC = datetime(2026, 11, 5, 18, 30, tzinfo=UTC)
AFTER_MIDNIGHT_UTC = datetime(2026, 11, 5, 19, 30, tzinfo=UTC)
EARLY_MORNING_UTC = datetime(2026, 11, 5, 1, 0, tzinfo=UTC)

EXPECTED = {
    EVENING_UTC: date(2026, 11, 5),
    AFTER_MIDNIGHT_UTC: date(2026, 11, 6),
    EARLY_MORNING_UTC: date(2026, 11, 5),
}

SELECT_DATES = (
    f"SELECT business_date, (created_at)::date FROM {CHILD_TABLE} WHERE stall_id = %s"
)


def _insert_at(probe: FinancialProbe, stall_index: int, moment: datetime) -> tuple[date, date]:
    """Berilgan paytda qator yozadi va `(business_date, naive_date)` qaytaradi."""
    stall = probe.stalls_a[stall_index]
    probe.conn.execute(
        INSERT_CHARGE_AT,
        (str(probe.market_a), str(stall), 5000, moment),
    )
    row = probe.conn.execute(SELECT_DATES, (str(stall),)).fetchone()
    assert row is not None
    return row[0], row[1]


def test_evening_before_local_midnight_stays_on_the_same_day(
    financial_probe: FinancialProbe,
) -> None:
    """18:30Z — Toshkentda 23:30, ya'ni hali o'sha kun."""
    business, _ = _insert_at(financial_probe, 0, EVENING_UTC)
    assert business == EXPECTED[EVENING_UTC]


def test_after_local_midnight_rolls_to_the_next_day(financial_probe: FinancialProbe) -> None:
    """19:30Z — Toshkentda 00:30, ya'ni KUN SURILADI (mezon #4).

    Bu — butun mexanizmning sababi. Kassir mahalliy yarim tundan keyin
    to'lov qabul qilsa, u ERTANGI kunga tushishi kerak, kechagi kunga emas.
    """
    business, _ = _insert_at(financial_probe, 1, AFTER_MIDNIGHT_UTC)
    assert business == EXPECTED[AFTER_MIDNIGHT_UTC], (
        "mahalliy yarim tundan keyingi yozuv oldingi kunda qoldi — "
        "biznes-kun chegarasi noto'g'ri hisoblanmoqda"
    )


def test_early_morning_utc_is_the_same_business_day(financial_probe: FinancialProbe) -> None:
    """01:00Z — Toshkentda 06:00 (bozor ochilishi), o'sha kun."""
    business, _ = _insert_at(financial_probe, 2, EARLY_MORNING_UTC)
    assert business == EXPECTED[EARLY_MORNING_UTC]


def test_naive_date_cast_disagrees_at_the_boundary(financial_probe: FinancialProbe) -> None:
    """XATO NAQSHNING regressiya himoyasi.

    `created_at::date` (mintaqasiz kast) 19:30Z holatida BOSHQA javob
    beradi. Bu farq testda aniq ko'rsatiladi — shunda kimdir generated
    ifodani "soddalashtirib" `(created_at)::date` ga o'zgartirsa, test
    darhol yiqiladi va sabab o'qiladigan bo'ladi.
    """
    business, naive = _insert_at(financial_probe, 1, AFTER_MIDNIGHT_UTC)

    assert business == date(2026, 11, 6)
    assert naive == date(2026, 11, 5)
    assert business != naive, (
        "naive kast bilan mintaqali hisob bir xil javob berdi — bu holat "
        "chegara emas, ya'ni test o'z maqsadini bajarmayapti"
    )


def test_db_matches_code_layer_business_date(financial_probe: FinancialProbe) -> None:
    """DB va `sbozor_core.timeutil.business_date()` uchala holatda AYNAN mos.

    Ikki qatlam ajralib ketsa, yozuv bir kunga tushadi, hisobot esa
    boshqasini ko'rsatadi — va bu faqat nizo paytida ko'rinadi.
    """
    for index, moment in enumerate((EVENING_UTC, AFTER_MIDNIGHT_UTC, EARLY_MORNING_UTC)):
        from_db, _ = _insert_at(financial_probe, index, moment)
        from_code = business_date(moment)

        assert from_db == from_code, (
            f"{moment.isoformat()}: DB `{from_db}`, kod `{from_code}` — "
            "ikki haqiqat manbai ajralib ketdi"
        )
        assert from_db == EXPECTED[moment]


def test_business_date_cannot_be_written_directly(financial_probe: FinancialProbe) -> None:
    """Ilova `business_date` ni O'ZI yoza olmaydi — u GENERATED ALWAYS.

    Busiz kod-qatlami sanani hisoblab yozishi mumkin bo'lardi va ikkinchi
    haqiqat manbai paydo bo'lardi (Anti-Pattern 10). `GENERATED ALWAYS`
    bu yo'lni STRUKTURAVIY yopadi.
    """
    with pytest.raises(psycopg.errors.GeneratedAlways) as excinfo:
        financial_probe.conn.execute(
            f"INSERT INTO {CHILD_TABLE} (market_id, stall_id, amount_soum, business_date) "
            "VALUES (%s, %s, %s, %s)",
            (
                str(financial_probe.market_a),
                str(financial_probe.stalls_a[0]),
                5000,
                date(2000, 1, 1),
            ),
        )

    assert "business_date" in str(excinfo.value)
