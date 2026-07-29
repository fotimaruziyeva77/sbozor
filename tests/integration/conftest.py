"""`tests/integration` uchun fixture reyestri.

Ildizdagi `tests/conftest.py` dagi barcha fixture'lar (`sync_owner_conn`,
`migrated`, `tenant_session`, ...) bu yerda ham mavjud — pytest conftest'larni
kataloglar bo'ylab meros qiladi. Bu fayl faqat SHU paketga tegishli
fixture'ni qo'shadi.

Ma'lumot fabrikasi bu yerda EMAS: DDL va SQL matnlari `tests/fixtures/
financial.py` da yashaydi (01-04 da o'rnatilgan naqsh — conftest fixture'lar
REYESTRI bo'lib qolsin). Bu ayni paytda ikki marta import qilinish
xavfini ham yopadi: conftest moduli pytest tomonidan alohida yuklanadi,
`fixtures.financial` esa oddiy paket sifatida — testlar konstantalarni
ikkinchisidan oladi.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fixtures.financial import FinancialProbe, create_financial_probe, drop_financial_probe
from psycopg import Connection
from psycopg.rows import TupleRow


@pytest.fixture
def financial_probe(
    sync_owner_conn: Connection[TupleRow], migrated: None
) -> Iterator[FinancialProbe]:
    """`financial_guards()` DDL'i qo'llangan haqiqiy moliyaviy jadval.

    `migrated` KERAK: `financial_guard_statements()` ning o'zi migratsiyaga
    bog'liq emas, lekin bu testlar bir xil bazada ishlaydi va sxema
    holatining aniq bo'lishi kerak (`uuidv7()` mavjudligi ham shu yerdan).
    """
    probe = create_financial_probe(sync_owner_conn)
    try:
        yield probe
    finally:
        drop_financial_probe(sync_owner_conn)
