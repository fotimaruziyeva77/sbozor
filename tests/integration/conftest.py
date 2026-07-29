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
from fixtures.admin_api import cleanup_test_users
from fixtures.financial import FinancialProbe, create_financial_probe, drop_financial_probe
from psycopg import Connection
from psycopg.rows import TupleRow


@pytest.fixture(autouse=True)
def _cleanup_api_created_users(sync_owner_conn: Connection[TupleRow]) -> Iterator[None]:
    """API orqali YARATILGAN foydalanuvchilarni har testdan keyin o'chiradi.

    `two_markets`/`auth_seed` teardown'lari faqat O'Z seed'ini biladi, ya'ni
    `POST /users` yaratgan qator bazada qolib ketardi va uning telefoni
    keyingi testda kutilmagan `409 phone_taken` berardi. Telefon diapazoni
    (`fixtures.admin_api.TEST_PHONE_PREFIX`) seed diapazonlaridan ajratilgan,
    shuning uchun tozalash boshqa hech nimaga tegmaydi.
    """
    yield
    cleanup_test_users(sync_owner_conn)


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
