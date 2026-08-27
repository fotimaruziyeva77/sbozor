"""identity: markets, users, user_market_roles, refresh_tokens + RLS + login funksiyalari

Revision ID: 0001
Revises:
Create Date: 2026-07-29

Bu migratsiya uch narsani BIRGA o'rnatadi va ular ajralmas:

  1. Sxema — to'rt jadval, composite-FK maqsadli `UNIQUE(market_id, id)`
     konstraytlari va `market_id` bilan boshlanadigan indekslar (P9).
  2. Izolyatsiya — `ENABLE` + `FORCE ROW LEVEL SECURITY` + policy. Uchtasidan
     bittasi tushib qolsa jadval jimgina ochiq qoladi, shuning uchun
     `tests/tenancy/test_meta.py` uchalasini ham `pg_catalog` dan tekshiradi.
  3. Login yo'li — `users` app-rolga BUTUNLAY yopiq, o'qish faqat to'rt
     `SECURITY DEFINER` funksiya orqali (Pattern 2 / Pitfall 3).
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

import sqlalchemy as sa
from alembic import op
from sbozor_core.models.identity import LOCALE_CHECK, ROLES_SUBSET_CHECK
from sqlalchemy.dialects import postgresql as pg

from migrations.entities.functions import ALL_FUNCTIONS, GRANT_SIGNATURES
from migrations.entities.policies import (
    markets_policy,
    owner_bootstrap_policy,
    tenant_policy,
)
from migrations.helpers import (
    create_entity,
    drop_entity,
    enable_rls,
    enable_tenant_rls,
    grant_app_dml,
)

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

APP_ROLE = "sbozor_app"

TENANT_TABLES = ("user_market_roles", "refresh_tokens")
RLS_TABLES = ("markets", *TENANT_TABLES)


def _uuid_pk() -> sa.Column[UUID]:
    """PG18 native `uuidv7()` — vaqt-tartiblangan, B-tree do'st."""
    return sa.Column(
        "id",
        pg.UUID(as_uuid=True),
        server_default=sa.text("uuidv7()"),
        nullable=False,
    )


def _created_at() -> sa.Column[datetime]:
    return sa.Column(
        "created_at",
        sa.DateTime(timezone=True),
        server_default=sa.text("now()"),
        nullable=False,
    )


def _updated_at() -> sa.Column[datetime]:
    return sa.Column(
        "updated_at",
        sa.DateTime(timezone=True),
        server_default=sa.text("now()"),
        nullable=False,
    )


def upgrade() -> None:
    """Upgrade schema."""
    # ------------------------------------------------------------------
    # 1. markets — tenant chegarasining O'ZI (maxsus holat)
    # ------------------------------------------------------------------
    op.create_table(
        "markets",
        _uuid_pk(),
        sa.Column("name", sa.Text(), nullable=False),
        # Pitfall 6: ustun 1-fazadayoq sxemada. 2-fazadagi `business_date`
        # generated column IMMUTABLE ifoda talab qiladi, shuning uchun u
        # hozircha literal 'Asia/Tashkent' ni ishlatadi — lekin bozorga xos
        # mintaqa keyin qo'shilganda migratsiya emas, faqat ifoda o'zgaradi.
        sa.Column("timezone", sa.Text(), server_default=sa.text("'Asia/Tashkent'"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        _created_at(),
        _updated_at(),
        sa.PrimaryKeyConstraint("id", name="pk_markets"),
    )
    # `markets` da `market_id` ustuni YO'Q — policy `id` bo'yicha solishtiradi,
    # shuning uchun `enable_tenant_rls` emas, `enable_rls` + tor GRANT.
    # Yozish `sbozor_owner` va 2-fazadagi bozor ustasi orqali.
    enable_rls("markets")
    grant_app_dml("markets", ops="SELECT")

    # ------------------------------------------------------------------
    # 2. users — GLOBAL. `market_id` YO'Q, RLS YO'Q, app-rolga GRANT YO'Q.
    # ------------------------------------------------------------------
    op.create_table(
        "users",
        _uuid_pk(),
        sa.Column("phone_e164", sa.Text(), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("full_name", sa.Text(), nullable=True),
        sa.Column("locale", sa.Text(), server_default=sa.text("'uz-Latn'"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "must_change_password", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column(
            "is_platform_admin", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        _created_at(),
        _updated_at(),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("phone_e164", name="uq_users_phone_e164"),
        # `ck` konvensiyasi prefiksni O'ZI qo'shadi (`ck_<table>_<name>`),
        # shuning uchun bu yerga faqat qisqa mantiqiy nom beriladi.
        sa.CheckConstraint(LOCALE_CHECK, name="locale_allowed"),
    )
    # Bu satr ATAYIN literal yozilgan (yordamchi `revoke_app_all()` mavjud
    # bo'lsa ham): xavfsizlik uchun eng kritik DDL o'qiganda ham, `grep`
    # qilganda ham ko'rinib turishi shart. `sbozor_app` `users` ni ORM
    # orqali umuman o'qiy olmaydi — login faqat SECURITY DEFINER
    # funksiyalari orqali (Pattern 2, T-01-25).
    op.execute("REVOKE ALL ON TABLE users FROM sbozor_app")

    # ------------------------------------------------------------------
    # 3. user_market_roles — TENANT
    # ------------------------------------------------------------------
    op.create_table(
        "user_market_roles",
        sa.Column("market_id", pg.UUID(as_uuid=True), nullable=False),
        _uuid_pk(),
        sa.Column("user_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("roles", pg.ARRAY(sa.Text()), nullable=False),
        _created_at(),
        _updated_at(),
        sa.PrimaryKeyConstraint("id", name="pk_user_market_roles"),
        sa.ForeignKeyConstraint(
            ["market_id"], ["markets.id"], name="fk_user_market_roles_market_id_markets"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_user_market_roles_user_id_users",
            ondelete="CASCADE",
        ),
        # Bu konstrayt AYNI PAYTDA `(market_id, user_id)` indeksining o'zi —
        # alohida `CREATE INDEX` keraksiz dublikat bo'lardi.
        sa.UniqueConstraint("market_id", "user_id", name="uq_user_market_roles_market_id_user_id"),
        # Composite FK maqsadi (T-01-26): keyingi fazalar `(market_id, id)`
        # ga havola qilib cross-tenant bog'lanishni strukturaviy yopadi.
        sa.UniqueConstraint("market_id", "id", name="uq_user_market_roles_market_id_id"),
        sa.CheckConstraint(ROLES_SUBSET_CHECK, name="roles_allowed"),
        sa.CheckConstraint("cardinality(roles) > 0", name="roles_not_empty"),
    )
    enable_tenant_rls("user_market_roles")

    # ------------------------------------------------------------------
    # 4. refresh_tokens — TENANT
    # ------------------------------------------------------------------
    op.create_table(
        "refresh_tokens",
        sa.Column("market_id", pg.UUID(as_uuid=True), nullable=False),
        _uuid_pk(),
        sa.Column("user_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("jti", sa.Text(), nullable=False),
        sa.Column("family_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replaced_by_jti", sa.Text(), nullable=True),
        _created_at(),
        sa.PrimaryKeyConstraint("id", name="pk_refresh_tokens"),
        sa.ForeignKeyConstraint(
            ["market_id"], ["markets.id"], name="fk_refresh_tokens_market_id_markets"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_refresh_tokens_user_id_users",
            ondelete="CASCADE",
        ),
        # `jti` GLOBAL qidiruv kaliti: refresh cookie kelganda bozor hali
        # noma'lum. Bu — `market_id` bilan boshlanmaydigan YAGONA indeks va
        # meta-testda aniq istisno sifatida qayd etilgan.
        sa.UniqueConstraint("jti", name="uq_refresh_tokens_jti"),
        sa.UniqueConstraint("market_id", "id", name="uq_refresh_tokens_market_id_id"),
    )
    op.create_index(
        "ix_refresh_tokens_market_id_user_id_expires_at",
        "refresh_tokens",
        ["market_id", "user_id", "expires_at"],
    )
    enable_tenant_rls("refresh_tokens")

    # ------------------------------------------------------------------
    # 5. Policy'lar. TARTIB MUHIM: ENABLE/FORCE (yuqorida) -> policy.
    #    `alembic-utils` bayroqlarni BILMAYDI (Pitfall 10), ularsiz policy
    #    hech qanday ta'sir ko'rsatmaydi.
    # ------------------------------------------------------------------
    create_entity(markets_policy())
    for table in TENANT_TABLES:
        create_entity(tenant_policy(table))
    for table in RLS_TABLES:
        create_entity(owner_bootstrap_policy(table))

    # ------------------------------------------------------------------
    # 6. SECURITY DEFINER login funksiyalari.
    #    Funksiyalar `sbozor_owner` egaligida bo'ladi (migratsiya shu rol
    #    bilan ishlaydi), shuning uchun ular `users` ni o'qiy oladi —
    #    `sbozor_app` esa o'qiy olmaydi.
    # ------------------------------------------------------------------
    for function in ALL_FUNCTIONS:
        create_entity(function)

    for signature in GRANT_SIGNATURES:
        # PUBLIC dan avval olib tashlanadi: Postgres yangi funksiyaga
        # `EXECUTE TO PUBLIC` ni STANDART beradi, ya'ni REVOKE'siz global
        # o'qish yuzasi hammaga ochiq bo'lib qolardi.
        op.execute(f"REVOKE ALL ON FUNCTION {signature} FROM PUBLIC")
        op.execute(f"GRANT EXECUTE ON FUNCTION {signature} TO {APP_ROLE}")


def downgrade() -> None:
    """Downgrade schema."""
    for function in reversed(ALL_FUNCTIONS):
        drop_entity(function)

    for table in reversed(RLS_TABLES):
        drop_entity(owner_bootstrap_policy(table))
    for table in reversed(TENANT_TABLES):
        drop_entity(tenant_policy(table))
    drop_entity(markets_policy())

    op.drop_index("ix_refresh_tokens_market_id_user_id_expires_at", table_name="refresh_tokens")
    op.drop_table("refresh_tokens")
    op.drop_table("user_market_roles")
    op.drop_table("users")
    op.drop_table("markets")
