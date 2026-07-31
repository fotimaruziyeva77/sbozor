"""Wave 0 test infratuzilmasi — HAQIQIY Postgres + `sbozor_app` roli.

=============================================================================
DIQQAT — BU FAYLNING ENG MUHIM QOIDASI:
`app_engine` va `sync_app_conn` fixture'lari **`sbozor_app` roli bilan**
ulanadi, **`postgres` superuseri bilan EMAS**. Aks holda RLS testlari
YOLG'ON-YASHIL beradi: `FORCE ROW LEVEL SECURITY` superuser'ni umuman
to'xtatmaydi, shuning uchun superuser bilan ishlaydigan test har qanday
cross-tenant sizishni "muvaffaqiyatli izolyatsiya" deb ko'rsatadi.
=============================================================================

Yengil/embedded fayl-bazalar bu yerda TAQIQLANGAN (CLAUDE.md direktivasi):
Row Level Security FAQAT PostgreSQL'da mavjud, shuning uchun boshqa bazaga
qarshi testlar loyihaning eng xavfli kod yo'lini umuman sinamaydi va yashil
bo'lib turaveradi. Yagona ruxsat etilgan baza — `postgres:18.4-trixie`.

Rol atributlari uchun yagona haqiqat manbai — `ops/db/init/01-roles.sql`,
kengaytmalar uchun esa `ops/db/init/00-extensions.sql`. Ikkala fayl ham shu
yerda VERBATIM o'qib bajariladi va ular prod'dagi tartibda (`00-` -> `01-`)
ishlaydi; DDL testda TAKRORLANMAYDI, shuning uchun prod
(`docker-entrypoint-initdb.d`) va test bir xil DDL'ni oladi.

Qochish yo'li: `TEST_DATABASE_URL` / `TEST_VALKEY_URL` o'rnatilgan bo'lsa
konteyner ishga tushirilmaydi va o'sha URL ishlatiladi (CI/Windows uchun).
"""

from __future__ import annotations

import os
import secrets
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote_plus
from uuid import UUID

import httpx
import psycopg
import pytest
from alembic import command
from alembic.config import Config
from app.settings import Settings
from fastapi import FastAPI
from fixtures import TenantSessionFactory, TokenFactory
from fixtures.admin_api import session_headers
from fixtures.auth_users import AuthSeed, cleanup_auth_users, seed_auth_users
from fixtures.two_markets import TwoMarketSeed, cleanup_two_markets, seed_two_markets
from psycopg import Connection, sql
from psycopg.rows import TupleRow
from redis.asyncio import Redis
from sbozor_core.db import make_sessionmaker
from sbozor_core.enums import ActorKind
from sbozor_core.tenancy import set_tenant_context
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# testcontainers 4.15: `testcontainers.postgres` eskirgan (DeprecationWarning),
# `testcontainers.community.postgres` — amaldagi yo'l. API bir xil.
from testcontainers.community.postgres import PostgresContainer
from testcontainers.core.container import DockerContainer
from testcontainers.core.wait_strategies import LogMessageWaitStrategy

# CLAUDE.md da qulflangan — PG 19 EMAS (hali 19beta2).
POSTGRES_IMAGE = "postgres:18.4-trixie"
VALKEY_IMAGE = "valkey/valkey:9.1.1-alpine"
VALKEY_PORT = 6379

REPO_ROOT = Path(__file__).resolve().parents[1]
EXTENSIONS_SQL_PATH = REPO_ROOT / "ops" / "db" / "init" / "00-extensions.sql"
ROLES_SQL_PATH = REPO_ROOT / "ops" / "db" / "init" / "01-roles.sql"
ALEMBIC_INI_PATH = REPO_ROOT / "alembic.ini"
MIGRATIONS_PATH = REPO_ROOT / "migrations"

# Faqat efemer test konteyneri uchun parollar — bular sir emas.
APP_PASSWORD = "app_pw"  # noqa: S105
OWNER_PASSWORD = "owner_pw"  # noqa: S105


@dataclass(frozen=True)
class PgEndpoint:
    """Ishga tushgan Postgres nusxasining ulanish koordinatalari."""

    host: str
    port: int
    dbname: str
    superuser: str
    superuser_password: str


def _sqlalchemy_url(user: str, password: str, endpoint: PgEndpoint) -> str:
    """SQLAlchemy (asyncpg) URL'i."""
    return (
        f"postgresql+asyncpg://{quote_plus(user)}:{quote_plus(password)}"
        f"@{endpoint.host}:{endpoint.port}/{endpoint.dbname}"
    )


def _psycopg_dsn(user: str, password: str, endpoint: PgEndpoint) -> str:
    """Sinxron psycopg DSN'i (`pg_catalog` meta-so'rovlari uchun)."""
    return (
        f"postgresql://{quote_plus(user)}:{quote_plus(password)}"
        f"@{endpoint.host}:{endpoint.port}/{endpoint.dbname}"
    )


@pytest.fixture(scope="session")
def pg_container() -> Iterator[PgEndpoint]:
    """Haqiqiy `postgres:18.4-trixie`.

    `TEST_DATABASE_URL` o'rnatilgan bo'lsa konteyner ISHGA TUSHIRILMAYDI —
    o'sha nusxa ishlatiladi (CI/Windows uchun qochish yo'li).
    """
    external = os.environ.get("TEST_DATABASE_URL")
    if external:
        url = make_url(external)
        yield PgEndpoint(
            host=url.host or "localhost",
            port=url.port or 5432,
            dbname=url.database or "postgres",
            superuser=url.username or "postgres",
            superuser_password=url.password or "",
        )
        return

    with PostgresContainer(POSTGRES_IMAGE, driver="asyncpg") as container:
        yield PgEndpoint(
            host=container.get_container_host_ip(),
            port=int(container.get_exposed_port(5432)),
            dbname=container.dbname,
            superuser=container.username,
            superuser_password=container.password,
        )


@pytest.fixture(scope="session", autouse=True)
def _bootstrap_extensions(pg_container: PgEndpoint) -> None:
    """`ops/db/init/00-extensions.sql` ni SUPERUSER bilan VERBATIM bajaradi.

    `_bootstrap_roles` bilan AYNAN bir xil naqsh va aynan bir xil sababdan:
    SQL matni testda TAKRORLANMAYDI — prod DDL'ining O'ZI bajariladi. Nusxa
    yozilganda test o'z tasavvurini tekshirgan bo'lardi, prod esa boshqa
    kengaytma bilan ishlab ketardi.

    ULANISH ROLI AHAMIYATLI: bu yerda superuser ATAYIN — `sbozor_owner`
    `CREATE EXTENSION btree_gist` ni bajara olmaydi (`permission denied to
    create extension`, empirik). Aynan shu sababdan kengaytma migratsiyada
    emas, init faylida yashaydi (2-faza Pitfall 1). Agar bu fixture owner
    roliga o'tkazilsa, u prod bilan bir xil xato bilan yiqiladi — ya'ni
    testning o'zi qarorni himoya qiladi.
    """
    extensions_sql = EXTENSIONS_SQL_PATH.read_text(encoding="utf-8")
    dsn = _psycopg_dsn(pg_container.superuser, pg_container.superuser_password, pg_container)

    with psycopg.connect(dsn, autocommit=True) as conn:
        conn.execute(extensions_sql)


@pytest.fixture(scope="session", autouse=True)
def _bootstrap_roles(pg_container: PgEndpoint, _bootstrap_extensions: None) -> None:
    """`ops/db/init/01-roles.sql` ni VERBATIM bajaradi, so'ng parol beradi.

    Rol atributlari (NOSUPERUSER / NOBYPASSRLS) bu yerda QAYTA YOZILMAYDI —
    ular faqat SQL faylida yashaydi. Shu sababli meta-test prod DDL'ini
    tekshiradi, testga xos nusxani emas.

    `_bootstrap_extensions` ga BOG'LIQLIK prod'dagi fayl tartibini
    (`00-` -> `01-`) takrorlaydi: autouse fixture'larning o'zaro tartibi
    kafolatlanmagan, shuning uchun u argument sifatida ATAYIN e'lon
    qilingan. Aks holda kengaytma rollardan keyin yaratilib, tartib
    prod'dan jimgina farq qilardi.
    """
    roles_sql = ROLES_SQL_PATH.read_text(encoding="utf-8")
    dsn = _psycopg_dsn(pg_container.superuser, pg_container.superuser_password, pg_container)

    with psycopg.connect(dsn, autocommit=True) as conn:
        # Parametrsiz `execute` — psycopg oddiy so'rov protokolini ishlatadi,
        # ya'ni ko'p operatorli fayl (DO $$...$$ bloklari bilan) bir marta ketadi.
        conn.execute(roles_sql)
        conn.execute(
            sql.SQL("ALTER ROLE sbozor_owner PASSWORD {}").format(sql.Literal(OWNER_PASSWORD))
        )
        conn.execute(sql.SQL("ALTER ROLE sbozor_app PASSWORD {}").format(sql.Literal(APP_PASSWORD)))


@pytest.fixture(scope="session")
def superuser_url(pg_container: PgEndpoint) -> str:
    """Superuser URL'i — FAQAT rol/DDL bootstrap uchun. Testlarda ishlatilmaydi."""
    return _sqlalchemy_url(pg_container.superuser, pg_container.superuser_password, pg_container)


@pytest.fixture(scope="session")
def owner_url(pg_container: PgEndpoint) -> str:
    """`sbozor_owner` URL'i — Alembic migratsiyalari uchun."""
    return _sqlalchemy_url("sbozor_owner", OWNER_PASSWORD, pg_container)


@pytest.fixture(scope="session")
def app_url(pg_container: PgEndpoint) -> str:
    """`sbozor_app` URL'i — BARCHA RLS testlari uchun MAJBURIY."""
    return _sqlalchemy_url("sbozor_app", APP_PASSWORD, pg_container)


@pytest.fixture(scope="session")
async def app_engine(app_url: str, _bootstrap_roles: None) -> AsyncIterator[AsyncEngine]:
    """Ilova roli (`sbozor_app`) bilan async engine.

    `pool_size=1, max_overflow=0` — bitta ulanish qayta-qayta ishlatiladi,
    ya'ni tranzaksiyalar orasida GUC sizishi (`app.market_id` bo'sh satr bo'lib
    qolishi) maksimal darajada ochib beriladi. Shu holatda o'tgan test prod'da
    ham o'tadi.
    """
    engine = create_async_engine(app_url, pool_size=1, max_overflow=0)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest.fixture
def sync_app_conn(
    app_url: str,
    _bootstrap_roles: None,
) -> Iterator[Connection[TupleRow]]:
    """Sinxron `sbozor_app` ulanishi — `pg_catalog` meta-so'rovlari uchun.

    `postgres` superuseri bilan EMAS: meta-testlar aynan ilova roli ko'radigan
    huquqlarni tekshirishi kerak.
    """
    url = make_url(app_url)
    dsn = (
        f"postgresql://{quote_plus(url.username or '')}:{quote_plus(url.password or '')}"
        f"@{url.host}:{url.port}/{url.database}"
    )
    with psycopg.connect(dsn, autocommit=True) as conn:
        yield conn


@pytest.fixture
def sync_superuser_conn(
    pg_container: PgEndpoint,
    _bootstrap_roles: None,
) -> Iterator[Connection[TupleRow]]:
    """Klaster superuseri — FAQAT `market_id IS NULL` audit qatorlarini o'qish uchun.

    Bunday qatorlar (`login_failed`) `audit_read` policy'si ostida NA
    `sbozor_app`, NA `sbozor_owner` roliga ko'rinadi — bu ataylab
    (`migrations/entities/policies.py` da hujjatlashtirilgan). Ularni
    tekshirishning boshqa yo'li 01-07 dagi tor `SECURITY DEFINER`
    funksiya qo'shilgunga qadar yo'q.

    HECH QANDAY IZOLYATSIYA DA'VOSI bu ulanish bilan tekshirilmaydi:
    superuser RLS'ni umuman chetlab o'tadi, ya'ni u bilan yozilgan
    izolyatsiya testi HAR DOIM yashil bo'lardi (Pitfall 2).
    """
    dsn = _psycopg_dsn(pg_container.superuser, pg_container.superuser_password, pg_container)
    with psycopg.connect(dsn, autocommit=True) as conn:
        yield conn


@pytest.fixture
def sync_owner_conn(
    owner_url: str,
    _bootstrap_roles: None,
) -> Iterator[Connection[TupleRow]]:
    """Sinxron `sbozor_owner` ulanishi — seed va test uchun DDL.

    FAQAT ma'lumot tayyorlash uchun: hech qanday izolyatsiya da'vosi bu
    ulanish bilan tekshirilmaydi. Isbotlar har doim `sbozor_app` bilan
    (`app_engine` / `sync_app_conn`) olinadi, chunki egaga qarshi RLS xulqi
    boshqacha va u ilova ko'radigan haqiqat emas.
    """
    url = make_url(owner_url)
    dsn = (
        f"postgresql://{quote_plus(url.username or '')}:{quote_plus(url.password or '')}"
        f"@{url.host}:{url.port}/{url.database}"
    )
    with psycopg.connect(dsn, autocommit=True) as conn:
        yield conn


@pytest.fixture(scope="session")
def migrated(owner_url: str, _bootstrap_roles: None) -> None:
    """`alembic upgrade head` — `sbozor_owner` roli bilan, DASTURIY ravishda.

    Sxemani testda qo'lda qurish TAQIQLANGAN: u holda testlar migratsiya
    haqiqatan nima yaratganini emas, testning o'z tasavvurini tekshirardi.
    Bu yerda aynan prod'dagi migratsiya bajariladi.

    Rol ham ahamiyatli: `sbozor_owner` superuser EMAS, ya'ni migratsiya
    FORCE ROW LEVEL SECURITY ostida ishlaydi va o'sha yerda buziladigan
    narsa (Pitfall 4) testda ham buziladi, prod'da birinchi marta emas.
    """
    config = Config(str(ALEMBIC_INI_PATH))
    config.set_main_option("script_location", str(MIGRATIONS_PATH))
    os.environ["MIGRATION_DATABASE_URL"] = owner_url
    command.upgrade(config, "head")


@pytest.fixture
def two_markets(sync_owner_conn: Connection[TupleRow], migrated: None) -> Iterator[TwoMarketSeed]:
    """Ikki bozor + beshta foydalanuvchi + oltita a'zolik qatori.

    Har testda YANGI UUID'lar, teardown'da to'liq tozalash — testlar bir
    biriga ta'sir qilmaydi va `auth_list_markets()` kabi global funksiyalar
    flaky bo'lmaydi.
    """
    seed = seed_two_markets(sync_owner_conn)
    try:
        yield seed
    finally:
        cleanup_two_markets(sync_owner_conn, seed)


@pytest.fixture(scope="session")
def app_sessionmaker(app_engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """`sbozor_app` engine ustidagi sessiya fabrikasi (prod bilan bir xil helper)."""
    return make_sessionmaker(app_engine)


@pytest.fixture
def tenant_session(app_sessionmaker: async_sessionmaker[AsyncSession]) -> TenantSessionFactory:
    """Tenant konteksti o'rnatilgan sessiya beruvchi fabrika.

    Sessiya TRANZAKSIYA ICHIDA ochiladi — `set_config(..., is_local=true)`
    autocommit rejimida qiymatni darhol yo'qotadi va kontekst umuman
    o'rnatilmagan bo'lardi (testlar esa jimgina 0 qator olib "izolyatsiya
    ishlayapti" degan yolg'on xulosaga kelardi).
    """

    @asynccontextmanager
    async def _tenant_session(
        market_id: UUID | None,
        actor_id: UUID | None = None,
        *,
        actor_kind: ActorKind = ActorKind.USER,
        request_id: str = "pytest",
    ) -> AsyncIterator[AsyncSession]:
        async with app_sessionmaker() as session, session.begin():
            await set_tenant_context(
                session,
                market_id=market_id,
                actor_id=actor_id,
                request_id=request_id,
                actor_kind=actor_kind,
            )
            yield session

    return _tenant_session


# ===========================================================================
# AUTH API (01-06) — HTTP chegarasidan o'tadigan integratsiya testlari uchun
# ===========================================================================


@pytest.fixture(scope="session")
def valkey_url() -> Iterator[str]:
    """Haqiqiy Valkey — `fakeredis` yoki qo'lda yozilgan qalbaki klient EMAS.

    Bloklash keshi va rate-limit sanagichi `INCR`/`EXPIRE`/TTL semantikasiga
    tayanadi; qalbaki klient bu semantikani TAXMIN qilardi va real Valkey
    bilan farqi faqat prod'da ko'rinardi.

    `TEST_VALKEY_URL` o'rnatilgan bo'lsa konteyner ishga TUSHIRILMAYDI
    (`TEST_DATABASE_URL` bilan bir xil qochish yo'li).
    """
    external = os.environ.get("TEST_VALKEY_URL")
    if external:
        yield external
        return

    container = (
        DockerContainer(VALKEY_IMAGE)
        .with_exposed_ports(VALKEY_PORT)
        # Port ochilishi YETARLI EMAS: Valkey portni tinglashni bosqichma-bosqich
        # boshlaydi va birinchi `PING` "LOADING" bilan qaytishi mumkin.
        .waiting_for(LogMessageWaitStrategy("Ready to accept connections"))
    )
    with container:
        host = container.get_container_host_ip()
        port = container.get_exposed_port(VALKEY_PORT)
        yield f"redis://{host}:{port}/0"


@pytest.fixture
async def valkey_client(valkey_url: str) -> AsyncIterator[Redis]:
    """Har test uchun TOZA Valkey.

    `flushdb()` majburiy: rate-limit sanagichi va bloklash keshi testlar
    orasida saqlanib qolsa, testlar bir-birini yiqitadi va sabab
    "flaky" bo'lib ko'rinadi.
    """
    client: Redis = Redis.from_url(valkey_url)
    await client.flushdb()
    try:
        yield client
    finally:
        await client.aclose()


@pytest.fixture(scope="session")
async def api_engine(app_url: str, _bootstrap_roles: None) -> AsyncIterator[AsyncEngine]:
    """API testlari uchun alohida engine — STANDART pul o'lchami bilan.

    `app_engine` ataylab `pool_size=1` (GUC sizishini ochib berish uchun),
    lekin bitta HTTP so'rovi ba'zan IKKI sessiya ochadi (bloklash keshi
    promahi + tenant sessiyasi). Bitta ulanishli pulda bu deadlock
    berardi — testlar esa timeout bilan yiqilib, sabab tenant izolyatsiyasi
    kabi ko'rinardi.
    """
    engine = create_async_engine(app_url)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest.fixture(scope="session")
def api_sessionmaker(api_engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """API ilovasi ishlatadigan sessiya fabrikasi (prod bilan bir xil helper)."""
    return make_sessionmaker(api_engine)


@pytest.fixture(scope="session")
def test_settings(app_url: str, valkey_url: str) -> Settings:
    """Test uchun `Settings`.

    `get_settings()` CHAQIRILMAYDI: u `lru_cache` bilan muhitdan o'qiydi
    va testda uni almashtirib bo'lmasdi. Ilova sozlamalarni
    `app.state.settings` dan oladi, ya'ni test prod kodining nusxasini
    emas, PROD KODINI ishga tushiradi.

    `cookie_secure=False` — test klienti HTTP orqali ishlaydi va `Secure`
    bayrog'i bilan cookie saqlanmasdi.
    """
    return Settings(
        database_url=app_url,
        valkey_url=valkey_url,
        jwt_secret=secrets.token_urlsafe(48),
        cookie_secure=False,
    )


@pytest.fixture
def api_app(
    test_settings: Settings,
    api_engine: AsyncEngine,
    api_sessionmaker: async_sessionmaker[AsyncSession],
    valkey_client: Redis,
    migrated: None,
) -> FastAPI:
    """HAQIQIY `app.main.app`, faqat `app.state` test resurslari bilan to'ldirilgan.

    `lifespan` ishga tushirilmaydi (`ASGITransport` uni chaqirmaydi) —
    aynan shu sababdan ilova resurslari `app.state` da yashaydi va
    dependency'lar ularni modul darajasidagi globaldan emas,
    `request.app.state` dan oladi.
    """
    from app.main import app

    app.state.settings = test_settings
    app.state.engine = api_engine
    app.state.sessionmaker = api_sessionmaker
    app.state.cache = valkey_client
    return app


@pytest.fixture
async def api_client(api_app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    """ASGI transport orqali to'g'ridan-to'g'ri ilovaga so'rov yuboradi.

    Tarmoq, port va uvicorn YO'Q — lekin middleware'lar, dependency'lar,
    Pydantic validatsiyasi va cookie mexanikasi to'liq ishlaydi.
    """
    transport = httpx.ASGITransport(app=api_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest.fixture
def auth_seed(
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
) -> Iterator[AuthSeed]:
    """`two_markets` ustiga HAQIQIY Argon2 parol + bloklangan/majburiy-almashtirish holatlari."""
    seed = seed_auth_users(sync_owner_conn, two_markets)
    try:
        yield seed
    finally:
        cleanup_auth_users(sync_owner_conn, seed)


@pytest.fixture
def token_for(api_client: httpx.AsyncClient) -> TokenFactory:
    """Berilgan foydalanuvchi/bozor uchun HAQIQIY access token beradi.

    Token MAHSULOT OQIMI orqali olinadi: `POST /auth/login`, keyin —
    agar `market_id` berilgan bo'lsa — `POST /auth/select-market`.
    `encode_access()` bilan to'g'ridan-to'g'ri yasash tezroq bo'lardi,
    lekin o'sha token login oqimidagi har qanday nosozlikni (rate-limit,
    bloklash tekshiruvi, a'zolik qidiruvi, `mid` claim'ining
    joylanishi) YASHIRARDI — cross-tenant matritsasi esa aynan shu
    zanjirning butunligiga tayanadi.

    `market_id` platforma admini uchun MAJBURIY: uning a'zoligi bir
    nechta, ya'ni login bozorni avtomatik tanlamaydi va tokenda `mid`
    bo'lmaydi (01-06). Bunday token bilan har qanday tenant endpointi
    `409 market_not_selected` beradi.
    """

    async def _token_for(phone: str, password: str, market_id: UUID | None = None) -> str:
        headers = await session_headers(api_client, phone, password, market_id=market_id)
        return headers["Authorization"].removeprefix("Bearer ")

    return _token_for
