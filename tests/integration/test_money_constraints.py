"""Pul — musbat `bigint` so'm, DB darajasida qulflangan (T-01-36).

=============================================================================
NEGA `float` EMAS (CLAUDE.md hard constraint):

Kasrli tip kunlik patta agregatlarida yaxlitlanish drifti beradi va bu
sotuvchi bilan nizoga olib keladi — ya'ni AYNAN mahsulot bartaraf etadigan
nosozlikni mahsulotning o'zi ishlab chiqaradi. Shuning uchun pul har doim
butun `bigint` so'm (spec §6).

NEGA `CHECK (amount_soum > 0)` DB'da, ilovada emas:
Ilova validatsiyasi faqat ORM yo'lini qamraydi. Xom SQL, migratsiya va
bulk import undan chetlab o'tadi — aynan `fn_audit_row()` uchun aytilgan
sabab (Pitfall 5). Konstrayt esa yozuv yo'lidan qat'i nazar ishlaydi.

Manfiy summa chegirma EMAS: chegirma `charge_adjustments` jadvalida alohida
yozuv sifatida saqlanadi, shunda "asl hisob qancha edi" savoli javobsiz
qolmaydi.
=============================================================================
"""

from __future__ import annotations

import psycopg
import pytest
from sbozor_core.money import MAX_SAFE_SOUM

from fixtures.financial import CHILD_TABLE, INSERT_CHARGE, FinancialProbe

SELECT_AMOUNT = f"SELECT amount_soum FROM {CHILD_TABLE} WHERE stall_id = %s"

AMOUNT_TYPE = (
    "SELECT data_type FROM information_schema.columns "
    "WHERE table_schema = 'public' AND table_name = %s AND column_name = 'amount_soum'"
)


def _insert_amount(probe: FinancialProbe, stall_index: int, amount: int) -> None:
    probe.conn.execute(
        INSERT_CHARGE,
        (str(probe.market_a), str(probe.stalls_a[stall_index]), amount),
    )


def test_zero_amount_is_rejected(financial_probe: FinancialProbe) -> None:
    """Nol so'mlik hisob — hisob emas, xato (`CHECK (amount_soum > 0)`)."""
    with pytest.raises(psycopg.errors.CheckViolation) as excinfo:
        _insert_amount(financial_probe, 0, 0)

    assert "amount_soum_positive" in str(excinfo.value)


def test_negative_amount_is_rejected(financial_probe: FinancialProbe) -> None:
    """Manfiy summa ham rad etiladi — chegirma boshqa jadvalning ishi."""
    with pytest.raises(psycopg.errors.CheckViolation) as excinfo:
        _insert_amount(financial_probe, 0, -1)

    assert "amount_soum_positive" in str(excinfo.value)


def test_positive_amount_is_accepted(financial_probe: FinancialProbe) -> None:
    """NAZORAT HOLATI: oddiy patta summasi muammosiz yoziladi.

    Busiz yuqoridagi ikki test yolg'on-yashil bo'lardi — konstrayt HAMMA
    narsani rad etayotgan bo'lsa ham "0 va -1 bloklandi" deb ko'rinardi.
    """
    _insert_amount(financial_probe, 0, 5000)

    row = financial_probe.conn.execute(
        SELECT_AMOUNT, (str(financial_probe.stalls_a[0]),)
    ).fetchone()
    assert row is not None
    assert row[0] == 5000
    assert isinstance(row[0], int)


def test_max_safe_soum_round_trips_exactly(financial_probe: FinancialProbe) -> None:
    """`MAX_SAFE_SOUM` yaxlitlanishsiz saqlanadi va aynan qaytadi (Pitfall 7).

    `bigint` maksimumi ~9.2x10^18, JS `Number.MAX_SAFE_INTEGER` esa
    9.007x10^15. Kod-qatlami aynan ikkinchisini chegara qilib oladi
    (`sbozor_core.money`), chunki summa JSON orqali frontendga o'tadi.
    Bu test o'sha chegaraviy qiymat DB'da ham buzilmasligini isbotlaydi —
    `numeric`/`double precision` tipida u JIMGINA yaxlitlanardi.
    """
    _insert_amount(financial_probe, 1, MAX_SAFE_SOUM)

    row = financial_probe.conn.execute(
        SELECT_AMOUNT, (str(financial_probe.stalls_a[1]),)
    ).fetchone()
    assert row is not None
    assert row[0] == MAX_SAFE_SOUM, "chegaraviy qiymat o'zgarib qaytdi — tip kasrli bo'lishi mumkin"


def test_amount_column_type_is_bigint(financial_probe: FinancialProbe) -> None:
    """Ustun tipi AYNAN `bigint` — `numeric` ham, `double precision` ham emas.

    Yuqoridagi round-trip testi `numeric` da ham o'tardi (u aniq, lekin
    sekin va `float` ga jimgina keltirilishi mumkin). Shuning uchun tip
    alohida va aniq tekshiriladi.
    """
    row = financial_probe.conn.execute(AMOUNT_TYPE, (CHILD_TABLE,)).fetchone()
    assert row is not None
    assert row[0] == "bigint", f"`amount_soum` tipi `{row[0]}` — `bigint` bo'lishi SHART"
