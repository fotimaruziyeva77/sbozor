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
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote_plus

import psycopg
import pytest
from psycopg import Connection, sql
from psycopg.rows import TupleRow
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

# testcontainers 4.15: `testcontainers.postgres` eskirgan (DeprecationWarning),
# `testcontainers.community.postgres` — amaldagi yo'l. API bir xil.
from testcontainers.community.postgres import PostgresContainer

# CLAUDE.md da qulflangan — PG 19 EMAS (hali 19beta2).
POSTGRES_IMAGE = "postgres:18.4-trixie"

REPO_ROOT = Path(__file__).resolve().parents[1]
ROLES_SQL_PATH = REPO_ROOT / "ops" / "db" / "init" / "01-roles.sql"

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
