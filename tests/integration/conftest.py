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
from contextlib import contextmanager
from datetime import date
from uuid import UUID

import pytest
from fixtures import MarketScope
from fixtures.admin_api import cleanup_test_users
from fixtures.financial import FinancialProbe, create_financial_probe, drop_financial_probe
from psycopg import Connection
from psycopg.rows import TupleRow

SET_MARKET_GUC = "SELECT set_config('app.market_id', %s, false)"
"""Sessiya darajasidagi tenant konteksti — `fixtures/two_markets.py` bilan bir xil.

`is_local=false` MAJBURIY: `sync_app_conn` autocommit rejimida ishlaydi va
`is_local=true` qiymati operator tugashi bilan yo'qolardi — ya'ni kontekst
umuman o'rnatilmagan bo'lardi va testlar jimgina 0 qator olib "izolyatsiya
ishlayapti" degan yolg'on xulosaga kelardi.
"""

MARKET_TODAY_SQL = "SELECT (now() AT TIME ZONE 'Asia/Tashkent')::date"
"""Bozorning BUGUNGI sanasi — AYNAN o'zgarmaslik triggeri ishlatadigan ifoda.

`migrations/entities/triggers.py::TARIFF_PAST_IMMUTABLE` shu ifoda bilan
"o'tmish" chegarasini belgilaydi. Test uni QAYTA YOZMAYDI (`date.today()`
UTC bo'lardi va mahalliy 00:00–04:59 oralig'ida bir kun farq qilardi) —
u DB'dan AYNAN o'sha javobni oladi, ya'ni "kelajak" deb yozilgan sana
trigger uchun ham kelajak bo'lishi KAFOLATLANADI.
"""


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


@pytest.fixture
def market_scope(sync_app_conn: Connection[TupleRow]) -> MarketScope:
    """Tenant konteksti o'rnatilgan `sbozor_app` bloki (2-faza sxema testlari).

    Shakli va sabablari — `fixtures/__init__.py::MarketScope` docstringida.
    Bu yerda faqat mexanika: kontekst blok boshida o'rnatiladi va `finally`
    da BO'SHATILADI, ya'ni istisno bilan tugagan test ham keyingisiga
    kontekst qoldirmaydi.

    Ulanish `sbozor_app` — `sbozor_owner` EMAS. Domen qoidalarining
    isbotlari ILOVA ko'radigan haqiqat ustida olinishi kerak; egaga qarshi
    hujum qiladigan testlar `sync_owner_conn` ni ATAYIN va ALOHIDA so'raydi
    (va docstringida buni aytadi).
    """

    @contextmanager
    def _scope(market_id: UUID) -> Iterator[Connection[TupleRow]]:
        sync_app_conn.execute(SET_MARKET_GUC, (str(market_id),))
        try:
            yield sync_app_conn
        finally:
            sync_app_conn.execute(SET_MARKET_GUC, ("",))

    return _scope


@pytest.fixture
def market_today(sync_app_conn: Connection[TupleRow]) -> date:
    """Bozorning bugungi sanasi (Asia/Tashkent) — DB'dan, kod'dan EMAS.

    ⚠ SOBIT SANA YOZMANG. D-07 qulfi "`valid_from <= bugun`" shaklida
    ishlaydi, ya'ni "kelajakdagi qator tahrirlanadi" nazorat holati sana
    QOTIRILGANDA jimgina o'z ma'nosini yo'qotadi: 2026-09-01 bugun kelajak,
    bir oydan keyin esa O'TMISH bo'ladi va nazorat holati `23514` bilan
    yiqiladi. Faza go-live sanasi 2026-10-18 — ya'ni bu rot loyihaning O'Z
    muddati ichida sodir bo'lardi.

    Shuning uchun kelajak/o'tmish sanalar shu qiymatdan HISOBLANADI.
    Seed'ning `operating_since` i (2026-01-15) esa sobit qolaveradi — u
    hech qachon kelajakka aylanmaydi.
    """
    row = sync_app_conn.execute(MARKET_TODAY_SQL).fetchone()
    assert row is not None, "DB bugungi sanani qaytarmadi"
    today: date = row[0]
    return today
