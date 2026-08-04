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

import secrets
from collections.abc import AsyncIterator, Iterator
from contextlib import contextmanager
from datetime import date
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import pytest
from app.services import storage
from app.services.storage import SnapshotStorage, StorageError
from app.settings import Settings
from cryptography.fernet import Fernet
from fixtures import MarketScope
from fixtures.admin_api import cleanup_test_users
from fixtures.financial import FinancialProbe, create_financial_probe, drop_financial_probe
from fixtures.nvr_flow import cleanup_api_nvr_rows, record_enqueue
from psycopg import Connection
from psycopg.rows import TupleRow
from pydantic import SecretStr

if TYPE_CHECKING:
    from fastapi import FastAPI
    from fixtures.two_markets import TwoMarketSeed

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


STORAGE_UNAVAILABLE_HINT = (
    "`{bucket}` bucketiga yetib bo'lmadi. Ikkita ehtimol bor va ikkalasining ham "
    "yechimi `ops/seaweedfs/README.md` da: (1) `storage` konteyneri ko'tarilmagan — "
    "`npm run sim:up`; (2) bucket hali yaratilmagan — `printf 's3.bucket.create "
    "-name {bucket}\\n' | docker compose exec -T storage weed shell`."
)
"""Ombor topilmaganda beriladigan ANIQ matn.

⚠ BU YERDA TEST O'TKAZIB YUBORILMAYDI, YIQILADI — VA BU QARORNING SABABI
  `fixtures/nvr_sim.py` DAGIDAN FARQ QILADI.

`nvr-sim` fixture'i dev mashinasida `skip` beradi, chunki `--profile sim`
konteynerlari ixtiyoriy qo'shimcha. `storage` esa PROFILSIZ (04-01, W0-4):
u `npm run up` va `npm run sim:up` ning ikkalasida ham ko'tariladi, ya'ni
"ko'tarilmagan" holati normal ish oqimi emas, KONFIGURATSIYA XATOSI.

Va narxi ham boshqa: o'tkazib yuborilgan test yashil darvozada UMUMAN
KO'RINMAYDI — CAM-07 ning "kadr omborga yoziladi va topiladi" da'vosi
sanoq nolga tushgan holda ham "yashil" bo'lib turaverardi (T-03-10 bilan
bir xil sinf, boshqa yo'ldan).
"""


@pytest.fixture(scope="session")
def s3_settings() -> Settings:
    """Ombor qatlami uchun `Settings` — `S3_*` qiymatlari MUHITDAN keladi.

    ⚠ `get_settings()` CHAQIRILMAYDI (`tests/conftest.py::test_settings` bilan
      bir xil sabab): u `lru_cache` ostida va testda almashtirib bo'lmasdi.

    ⚠ `S3_*` MAYDONLARI BU YERDA QO'LDA BERILMAYDI. `BaseSettings` ularni
      muhitdan o'qiydi va aynan shu — MAHSULOT yo'li: `compose.yaml` ning
      `tests` bloki `S3_ENDPOINT_URL`/`S3_BUCKET`/`S3_ACCESS_KEY`/
      `S3_SECRET_KEY` ni beradi va ular HAQIQIY `storage` konteyneriga
      ishora qiladi. Qiymatlarni bu yerda takrorlash o'sha zanjirni ikkiga
      bo'lardi va test compose sozlamasi buzilganini sezmasdi.

    Qolgan uch maydon (`database_url`, `valkey_url`, `jwt_secret`,
    `nvr_credential_key`) `Settings` ning KONSTRUKTORI uchun majburiy,
    ombor qatlami uchun esa ahamiyatsiz — u faqat `s3_*` maydonlarini
    o'qiydi. Shuning uchun ular bu yerda o'rnini bosuvchi qiymat oladi va
    bu fixture Postgres/Valkey konteynerlariga UMUMAN bog'lanmaydi: ombor
    o'lchovi baza qatlamining ko'tarilishini kutmasligi kerak.
    """
    return Settings(
        database_url="postgresql+asyncpg://storage-testi-bazaga-tegmaydi/none",
        valkey_url="redis://storage-testi-keshga-tegmaydi:6379/0",
        jwt_secret=secrets.token_urlsafe(48),
        nvr_credential_key=SecretStr(Fernet.generate_key().decode()),
    )


@pytest.fixture
async def s3_client(s3_settings: Settings) -> AsyncIterator[SnapshotStorage]:
    """HAQIQIY SeaweedFS konteyneriga ulangan `SnapshotStorage` (04-06, CAM-07).

    ⚠⚠ BU MOCK EMAS VA HECH QACHON MOCK BO'LMAYDI. `S3_ENDPOINT_URL`
      `compose.yaml` dagi `storage` xizmatiga ishora qiladi va har bir
      `put`/`head`/`get`/`list`/`delete` haqiqiy S3 imzosi bilan tarmoq
      orqali ketadi. Sabab 03-14 da o'lchangan: `go2rtc` ning
      `PUT /api/streams` xulqi mock ostida BUTUNLAY yashiringan edi va uni
      faqat birinchi mock'siz o'lchov ochdi. S3 da yashirinadigan qatlam
      undan ham kattaroq — imzolash, endpoint kelishuvi va sahifalash
      semantikasi mock'da UMUMAN bajarilmaydi.

    Bucket mavjudligi fixture ochilishida tekshiriladi: `head()` mavjud
    bo'lmagan kalit uchun `None` qaytaradi, ombor yoki bucket topilmasa esa
    `StorageError` beradi (o'lchandi: qadalgan rekvizit bilan begona bucket
    `403`, yetib bo'lmaydigan manzil `EndpointConnectionError`). Ikkinchi
    holatda test ANIQ matn bilan YIQILADI.
    """
    async with storage.open(s3_settings) as client:
        probe_key = f"bucket-zondi/{uuid4()}.jpg"
        try:
            await client.head(probe_key)
        except StorageError as exc:
            raise AssertionError(
                STORAGE_UNAVAILABLE_HINT.format(bucket=s3_settings.s3_bucket)
            ) from exc
        yield client


@pytest.fixture
async def s3_markets(s3_client: SnapshotStorage) -> AsyncIterator[tuple[UUID, UUID]]:
    """Testga IKKI bozor identifikatori beradi va ularning kalitlarini TOZALAYDI.

    ⚠ BOZOR IDENTIFIKATORI FAQAT SHU FIXTURE'DAN OLINADI. Test o'zi
      `uuid4()` chaqirsa uning yozgan kalitlari tozalanmasdi va arxivda
      abadiy qolib ketardi — 455 kunlik saqlash siyosati bo'lgan omborda
      bu jimgina to'planadigan qarz.

    ⚠ IKKITA, BITTA EMAS: prefiks izolyatsiyasi (§D.9 — bitta rekvizit
      barcha bozorlarni ochadi) faqat IKKI bozorli holatda o'lchanadi.

    Tozalash `list_prefix` + `delete_many` bilan, ya'ni fixture ham AYNAN
    o'sha kontraktdan foydalanadi — testdan tashqarida qolgan yashirin yo'l
    yo'q.
    """
    markets = (uuid4(), uuid4())
    try:
        yield markets
    finally:
        for market_id in markets:
            keys = await s3_client.list_prefix(f"{market_id}/")
            if keys:
                await s3_client.delete_many(keys)


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
def enqueued(api_app: FastAPI) -> Iterator[list[dict[str, Any]]]:
    """Kashfiyot navbatiga qo'yilgan xabarlar (`fixtures.nvr_flow.record_enqueue`).

    ⚠ REYESTRDA, TEST MODULIDA EMAS: zanjirni kesib o'tadigan IKKI modul
      bor (`test_phase3_criteria.py` va `test_live_view_e2e.py`) va
      fixture'ning ikki nusxasi jimgina ajralib ketardi — o'shanda
      mock'siz o'lchov mahsulot zanjirining boshqa variantini kesib
      o'tgan bo'lardi.
    """
    with record_enqueue(api_app) as calls:
        yield calls


@pytest.fixture
def nvr_cleanup(
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
) -> Iterator[None]:
    """API orqali YARATILGAN NVR qatorlarini o'chiradi (FK tartibida).

    Sabab va tartib — `fixtures.nvr_flow.cleanup_api_nvr_rows` docstringida.
    """
    try:
        yield
    finally:
        cleanup_api_nvr_rows(sync_owner_conn, [str(market.id) for market in two_markets.markets])


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
