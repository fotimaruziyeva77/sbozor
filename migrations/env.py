"""Alembic muhiti — async engine + `alembic-utils` entity reyestri.

`connection.run_sync(do_run_migrations)` naqshi ishlatiladi: Alembic'ning
sinxron API'si async ulanish ustida bajariladi, ya'ni **asyncpg URL yetarli**
va alohida `psycopg` URL SHART EMAS (RESEARCH Pattern 11).

Ulanish satri faqat `MIGRATION_DATABASE_URL` muhit o'zgaruvchisidan olinadi
(`alembic.ini` dagi `sqlalchemy.url` ATAYIN bo'sh). Sabab: migratsiya
`sbozor_owner` roli bilan ishlashi kerak, ilova roli yoki superuser bilan
emas — va sir hech qachon repoda yotmasligi kerak.
"""

from __future__ import annotations

import asyncio
import os
from logging.config import fileConfig

from alembic import context
from alembic_utils.pg_function import PGFunction
from alembic_utils.pg_policy import PGPolicy
from alembic_utils.replaceable_entity import register_entities
from sbozor_core.models import Base
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from migrations.entities import ALL_ENTITIES

MIGRATION_URL_ENV = "MIGRATION_DATABASE_URL"

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Modellar `sbozor_core.models.__init__` da import qilinadi — shu sababli
# bu yerda faqat `Base` kerak.
target_metadata = Base.metadata

# Policy'lar va `SECURITY DEFINER` funksiyalari autogenerate nazorati ostiga
# olinadi. ENABLE/FORCE bayroqlari BUNGA KIRMAYDI (Pitfall 10) — ular
# `migrations/helpers.py` orqali xom DDL bilan qo'yiladi.
#
# `entity_types` MAJBURIY (A9 tekshiruvida o'lchandi): busiz `alembic-utils`
# `PGGrantTable` ni ham taqqoslaydi va bazadagi HAR BIR mavjud GRANT uchun
# `op.drop_entity(...)` chiqaradi — ya'ni "bo'sh" autogenerate migratsiyasi
# aslida `sbozor_owner` va `sbozor_app` ning barcha huquqlarini bekor
# qiladigan 40 qatorli DDL bo'lib chiqadi. Huquqlar bu loyihada
# `migrations/helpers.py` orqali ATAYIN aniq boshqariladi, shuning uchun
# autogenerate ularga umuman tegmasligi kerak.
register_entities(ALL_ENTITIES, entity_types=[PGPolicy, PGFunction])


def _database_url() -> str:
    """Migratsiya URL'i — yo'q bo'lsa aniq xato bilan to'xtaydi."""
    url = os.environ.get(MIGRATION_URL_ENV, "").strip()
    if not url:
        raise RuntimeError(
            f"{MIGRATION_URL_ENV} o'rnatilmagan. Migratsiyalar `sbozor_owner` "
            "roli bilan bajariladi, masalan: "
            f"{MIGRATION_URL_ENV}=postgresql+asyncpg://sbozor_owner:***@db:5432/sbozor"
        )
    return url


def run_migrations_offline() -> None:
    """`--sql` rejimi: ulanmasdan DDL matnini chiqaradi."""
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        include_schemas=False,
        version_table_schema=None,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Sinxron Alembic yadrosi — `run_sync` ichida bajariladi."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        include_schemas=False,
        version_table_schema=None,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Async engine ochadi va sinxron migratsiyani uning ustida ishga tushiradi."""
    section = config.get_section(config.config_ini_section, {}) or {}
    section["sqlalchemy.url"] = _database_url()

    connectable = async_engine_from_config(
        section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Odatiy rejim."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
