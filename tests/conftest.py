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

Rol atributlari uchun yagona haqiqat manbai — `ops/db/init/01-roles.sql`.
Bu fayl shu yerda VERBATIM o'qib bajariladi; rol DDL'i testda TAKRORLANMAYDI,
shuning uchun prod (`docker-entrypoint-initdb.d`) va test bir xil DDL'ni oladi.

Qochish yo'li: `TEST_DATABASE_URL` o'rnatilgan bo'lsa konteyner ishga
tushirilmaydi va o'sha URL ishlatiladi (CI/Windows uchun).
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote_plus
from uuid import UUID

import psycopg
import pytest
from alembic import command
from alembic.config import Config
from fixtures import TenantSessionFactory
from fixtures.two_markets import TwoMarketSeed, cleanup_two_markets, seed_two_markets
from psycopg import Connection, sql
from psycopg.rows import TupleRow
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

# CLAUDE.md da qulflangan — PG 19 EMAS (hali 19beta2).
POSTGRES_IMAGE = "postgres:18.4-trixie"

REPO_ROOT = Path(__file__).resolve().parents[1]
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
def _bootstrap_roles(pg_container: PgEndpoint) -> None:
    """`ops/db/init/01-roles.sql` ni VERBATIM bajaradi, so'ng parol beradi.

    Rol atributlari (NOSUPERUSER / NOBYPASSRLS) bu yerda QAYTA YOZILMAYDI —
    ular faqat SQL faylida yashaydi. Shu sababli meta-test prod DDL'ini
    tekshiradi, testga xos nusxani emas.
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
