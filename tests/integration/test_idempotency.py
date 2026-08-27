"""Kun yopilishining IDEMPOTENTLIGI va cross-tenant havola (mezon #5).

=============================================================================
QAYSI NOSOZLIK OLDI OLINADI (T-01-37, BILL-01 ga tayyorgarlik):

Kunlik hisob-kitob job'i qayta ishga tushishi MUQARRAR: konteyner qayta
ishga tushadi, tarmoq uziladi, admin "hisobni qayta hisobla" tugmasini
bosadi. Agar ikkinchi yurish ikkinchi hisobni yaratsa, sotuvchi bir kun
uchun ikki marta patta to'lashi kerak bo'ladi — va buni faqat u sezadi.

Himoya ILOVA MANTIG'IDA emas, SXEMADA:

    UNIQUE (market_id, stall_id, business_date)
    INSERT ... ON CONFLICT (market_id, stall_id, business_date) DO NOTHING

Birinchisi dublikatni STRUKTURAVIY imkonsiz qiladi, ikkinchisi esa qayta
yurishni xatosiz (`INSERT 0`) qiladi. Ikkalasi ham kerak: konstraytsiz
`ON CONFLICT` ning ma'nosi yo'q, `ON CONFLICT` siz esa qayta yurish
istisno bilan yiqiladi va job "muvaffaqiyatsiz" deb belgilanadi.
=============================================================================

Uchinchi tekshiruv — composite FK: A bozorining hisobi B bozorining
rastasiga havola qila OLMAYDI. Bu RLS emas, SXEMA kafolati: RLS "kim
nimani ko'radi" ni hal qiladi, "nima nimaga bog'lanishi mumkin" ni emas.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import psycopg
import pytest
from fixtures.financial import (
    INSERT_CHARGE,
    INSERT_CHARGE_AT,
    INSERT_CHARGE_IDEMPOTENT,
    SELECT_ROWS,
    FinancialProbe,
)

FIRST_AMOUNT = 5000
SECOND_AMOUNT = 7000

# Ikki kunni ATAYIN mahalliy yarim tundan uzoq nuqtada olamiz: bu test
# idempotentlikni sinaydi, chegara arifmetikasini emas (u alohida faylda).
DAY_ONE = datetime(2026, 11, 5, 6, 0, tzinfo=UTC)
DAY_TWO = DAY_ONE + timedelta(days=1)


def test_second_insert_with_on_conflict_is_a_no_op(financial_probe: FinancialProbe) -> None:
    """Kunni QAYTA yopish dublikat yaratmaydi va summani O'ZGARTIRMAYDI.

    `DO NOTHING` ataylab `DO UPDATE` emas: birinchi hisob — haqiqat.
    Qayta yurish uni "yangilashi" kerak emas, chunki u allaqachon
    sotuvchiga ko'rsatilgan va to'lov undan boshlangan bo'lishi mumkin.
    """
    market, stall = financial_probe.market_a, financial_probe.stalls_a[0]

    first = financial_probe.conn.execute(
        INSERT_CHARGE_IDEMPOTENT, (str(market), str(stall), FIRST_AMOUNT)
    )
    assert first.rowcount == 1, "birinchi INSERT o'tmadi — test shartini bajarmadi"

    second = financial_probe.conn.execute(
        INSERT_CHARGE_IDEMPOTENT, (str(market), str(stall), SECOND_AMOUNT)
    )

    assert second.rowcount == 0, (
        f"takroriy INSERT {second.rowcount} qator qo'shdi — kun yopilishi idempotent emas"
    )
    rows = financial_probe.conn.execute(SELECT_ROWS, (str(market), str(stall))).fetchall()
    assert len(rows) == 1, f"bitta hisob kutilgan, {len(rows)} ta topildi"
    assert rows[0][0] == FIRST_AMOUNT, "mavjud hisob summasi o'zgarib ketdi"


def test_second_insert_without_on_conflict_violates_unique(
    financial_probe: FinancialProbe,
) -> None:
    """`ON CONFLICT` SIZ takroriy INSERT unique buzilishi bilan RAD ETILADI.

    Bu — yuqoridagi testning juftligi: u `ON CONFLICT` ning kerakligini
    ko'rsatadi. Konstrayt bo'lmaganida ikkala test ham o'tardi va hech
    qanday himoya bo'lmasdi.
    """
    market, stall = financial_probe.market_a, financial_probe.stalls_a[0]
    financial_probe.conn.execute(INSERT_CHARGE, (str(market), str(stall), FIRST_AMOUNT))

    with pytest.raises(psycopg.errors.UniqueViolation) as excinfo:
        financial_probe.conn.execute(INSERT_CHARGE, (str(market), str(stall), SECOND_AMOUNT))

    assert "business_day" in str(excinfo.value)


def test_next_business_day_is_a_separate_charge(financial_probe: FinancialProbe) -> None:
    """NAZORAT HOLATI: ERTASI kun uchun yangi hisob QABUL QILINADI.

    Busiz yuqoridagi ikki test yolg'on-yashil bo'lardi — unique kalit
    `business_date` siz (`market_id, stall_id`) bo'lganida ular ham
    o'tardi, lekin ikkinchi kun uchun hisob umuman yozilmasdi.
    """
    market, stall = financial_probe.market_a, financial_probe.stalls_a[0]

    financial_probe.conn.execute(INSERT_CHARGE_AT, (str(market), str(stall), FIRST_AMOUNT, DAY_ONE))
    financial_probe.conn.execute(
        INSERT_CHARGE_AT, (str(market), str(stall), SECOND_AMOUNT, DAY_TWO)
    )

    rows = financial_probe.conn.execute(SELECT_ROWS, (str(market), str(stall))).fetchall()
    assert len(rows) == 2, "ikki kunlik hisob bitta kalit ostida qolib ketdi"
    assert [row[0] for row in rows] == [FIRST_AMOUNT, SECOND_AMOUNT]
    assert rows[0][1] != rows[1][1]


def test_cross_tenant_stall_reference_is_rejected(financial_probe: FinancialProbe) -> None:
    """A bozorining hisobi B bozorining rastasiga havola qila OLMAYDI (T-01-26).

    Composite FK `(market_id, stall_id) -> (market_id, id)` juftligini
    talab qiladi, ya'ni `(A, B_rastasi)` juftligi ota-jadvalda umuman
    mavjud emas. Bu SXEMA kafolati: u RLS o'chirilgan taqdirda ham
    kuchda qoladi.
    """
    with pytest.raises(psycopg.errors.ForeignKeyViolation) as excinfo:
        financial_probe.conn.execute(
            INSERT_CHARGE,
            (str(financial_probe.market_a), str(financial_probe.stall_b), FIRST_AMOUNT),
        )

    assert "probe_stalls" in str(excinfo.value)
