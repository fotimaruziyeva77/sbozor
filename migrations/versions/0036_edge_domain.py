"""edge — universal agent: obyekt, aktivatsiya kodi, agent, sozlama, buyruq, hodisa, fayl

Revision ID: 0036
Revises: 0035
Create Date: 2026-10-30

=============================================================================
⛔⛔ NEGA BU MIGRATSIYA BOR (foydalanuvchi talabi, 2026-10-30).

Bozor, avtoturargoh va mol bozoriga o'rnatiladigan universal Windows agenti
(`sbozor-agent`) serverga O'ZI ulanadi: `/api/v1/edge/*` (long-poll,
hodisalar, fayllar, natijalar). Protokol — agent repozitoriyasidagi
`docs/protocol-http.md`.

  1. Yetti tenant jadvali (`EDGE_TENANT_TABLES`): RLS ENABLE+FORCE,
     `tenant_isolation` + `owner_bootstrap`. Audit triggeri YO'Q — sabab
     `migrations/entities/__init__.py::EDGE_TENANT_TABLES` docstringida.
  2. Ikki GLOBAL unique indeks (`token_sha256`, `code`) — tenant noma'lum
     paytdagi qidiruv kaliti (`INDEX_EXCEPTIONS` da sabab bilan).
  3. Ikki tor `SECURITY DEFINER` funksiya: `edge_agent_auth(text)`,
     `edge_activation_find(text)` — `REVOKE PUBLIC` + `GRANT sbozor_app`.
  4. `market_delete_draft()` kaskadiga yetti `DELETE`.
=============================================================================
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from alembic import op
from alembic_utils.pg_function import PGFunction
from sbozor_core.models.edge import (
    EDGE_ACTIVATION_SITE_INDEX,
    EDGE_AGENT_SITE_INDEX,
    EDGE_COMMAND_PENDING_INDEX,
    EDGE_COMMAND_RESULT_CHECK,
    EDGE_EVENT_SITE_TIME_INDEX,
    EDGE_EVENT_SITE_TYPE_INDEX,
    EDGE_SITE_KIND_CHECK,
)
from sqlalchemy.dialects import postgresql as pg

from migrations.entities import EDGE_TENANT_TABLES
from migrations.entities.functions import (
    EDGE_FUNCTIONS,
    EDGE_GRANT_SIGNATURES,
    MARKET_DELETE_DRAFT,
)
from migrations.entities.policies import owner_bootstrap_policy, tenant_policy
from migrations.helpers import (
    APP_ROLE,
    create_entity,
    drop_entity,
    enable_tenant_rls,
    replace_entity,
)

# revision identifiers, used by Alembic.
revision: str = "0036"
down_revision: str | Sequence[str] | None = "0035"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_EDGE_DELETE_BLOCK = (
    "  -- 0036 — universal agent (edge) domeni. Boshqa domendan hech kim\n"
    "  -- tayanmaydi; ichki tartib — bolalar `edge_sites` dan OLDIN.\n"
    "  DELETE FROM public.edge_events              WHERE market_id = p_market_id;\n"
    "  DELETE FROM public.edge_files               WHERE market_id = p_market_id;\n"
    "  DELETE FROM public.edge_commands            WHERE market_id = p_market_id;\n"
    "  DELETE FROM public.edge_configs             WHERE market_id = p_market_id;\n"
    "  DELETE FROM public.edge_agents              WHERE market_id = p_market_id;\n"
    "  DELETE FROM public.edge_activation_codes    WHERE market_id = p_market_id;\n"
    "  DELETE FROM public.edge_sites               WHERE market_id = p_market_id;\n"
    "\n"
)

MARKET_DELETE_DRAFT_WITHOUT_EDGE = PGFunction(
    schema="public",
    signature=MARKET_DELETE_DRAFT.signature,
    definition=MARKET_DELETE_DRAFT.definition.replace(_EDGE_DELETE_BLOCK, ""),
)
"""0035 holatidagi funksiya — downgrade uchun (joriy ta'rifdan edge bloki olinadi)."""


def _created_at() -> sa.Column[Any]:
    return sa.Column(
        "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
    )


def _market_fk(table: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        ["market_id"], ["markets.id"], name=f"fk_{table}_market_id_markets"
    )


def _site_fk(table: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        ["market_id", "site_id"],
        ["edge_sites.market_id", "edge_sites.id"],
        name=f"fk_{table}_site",
    )


def _regrant(signature: str) -> None:
    """`REVOKE PUBLIC` + `GRANT sbozor_app` — `0015` naqshi."""
    op.execute(f"REVOKE ALL ON FUNCTION {signature} FROM PUBLIC")
    op.execute(f"GRANT EXECUTE ON FUNCTION {signature} TO {APP_ROLE}")


def upgrade() -> None:
    """Upgrade schema."""
    if _EDGE_DELETE_BLOCK not in MARKET_DELETE_DRAFT.definition:
        raise RuntimeError("market_delete_draft() da edge bloki yo'q")

    op.create_table(
        "edge_sites",
        sa.Column("market_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("setup", pg.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_by", pg.UUID(as_uuid=True), nullable=True),
        _created_at(),
        sa.PrimaryKeyConstraint("id", name="pk_edge_sites"),
        _market_fk("edge_sites"),
        sa.UniqueConstraint("market_id", "id", name="uq_edge_sites_market_id_id"),
        sa.CheckConstraint(EDGE_SITE_KIND_CHECK, name="kind_allowed"),
    )

    op.create_table(
        "edge_activation_codes",
        sa.Column("market_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("id", pg.UUID(as_uuid=True), server_default=sa.text("uuidv7()"), nullable=False),
        sa.Column("site_id", sa.Text(), nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("used_by_agent_id", sa.Text(), nullable=True),
        sa.Column("created_by", pg.UUID(as_uuid=True), nullable=True),
        _created_at(),
        sa.PrimaryKeyConstraint("id", name="pk_edge_activation_codes"),
        _market_fk("edge_activation_codes"),
        _site_fk("edge_activation_codes"),
        sa.UniqueConstraint("market_id", "id", name="uq_edge_activation_codes_market_id_id"),
        sa.UniqueConstraint("code", name="uq_edge_activation_codes_code"),
    )
    op.create_index(EDGE_ACTIVATION_SITE_INDEX, "edge_activation_codes", ["market_id", "site_id"])

    op.create_table(
        "edge_agents",
        sa.Column("market_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("site_id", sa.Text(), nullable=False),
        sa.Column("token_sha256", sa.Text(), nullable=False),
        sa.Column("instance_id", sa.Text(), nullable=False),
        sa.Column("hostname", sa.Text(), nullable=False),
        sa.Column("version", sa.Text(), nullable=False),
        sa.Column("os", sa.Text(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_heartbeat", pg.JSONB(), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        _created_at(),
        sa.PrimaryKeyConstraint("id", name="pk_edge_agents"),
        _market_fk("edge_agents"),
        _site_fk("edge_agents"),
        sa.UniqueConstraint("market_id", "id", name="uq_edge_agents_market_id_id"),
        sa.UniqueConstraint("token_sha256", name="uq_edge_agents_token_sha256"),
    )
    op.create_index(EDGE_AGENT_SITE_INDEX, "edge_agents", ["market_id", "site_id"])

    op.create_table(
        "edge_configs",
        sa.Column("market_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("id", pg.UUID(as_uuid=True), server_default=sa.text("uuidv7()"), nullable=False),
        sa.Column("site_id", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("doc", pg.JSONB(), nullable=False),
        sa.Column("created_by", pg.UUID(as_uuid=True), nullable=True),
        _created_at(),
        sa.PrimaryKeyConstraint("id", name="pk_edge_configs"),
        _market_fk("edge_configs"),
        _site_fk("edge_configs"),
        sa.UniqueConstraint("market_id", "id", name="uq_edge_configs_market_id_id"),
        sa.UniqueConstraint(
            "market_id", "site_id", "version", name="uq_edge_configs_market_id_site_id_version"
        ),
        sa.CheckConstraint("version >= 1", name="version_positive"),
    )

    op.create_table(
        "edge_commands",
        sa.Column("market_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("id", pg.UUID(as_uuid=True), server_default=sa.text("uuidv7()"), nullable=False),
        sa.Column("site_id", sa.Text(), nullable=False),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("data", pg.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("issued_by", sa.Text(), nullable=False),
        sa.Column(
            "issued_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("result_status", sa.Text(), nullable=True),
        sa.Column("result_reason", sa.Text(), nullable=True),
        sa.Column("result_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_edge_commands"),
        _market_fk("edge_commands"),
        _site_fk("edge_commands"),
        sa.UniqueConstraint("market_id", "id", name="uq_edge_commands_market_id_id"),
        sa.CheckConstraint(EDGE_COMMAND_RESULT_CHECK, name="result_status_allowed"),
    )
    op.create_index(
        EDGE_COMMAND_PENDING_INDEX, "edge_commands", ["market_id", "site_id", "delivered_at"]
    )

    op.create_table(
        "edge_events",
        sa.Column("market_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("site_id", sa.Text(), nullable=False),
        sa.Column("agent_id", sa.Text(), nullable=False),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("v", sa.Integer(), nullable=False),
        sa.Column("seq", sa.BigInteger(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("clock_ok", sa.Boolean(), nullable=False),
        sa.Column("correlation_id", pg.UUID(as_uuid=True), nullable=True),
        sa.Column("data", pg.JSONB(), nullable=False),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_edge_events"),
        _market_fk("edge_events"),
        _site_fk("edge_events"),
        sa.UniqueConstraint("market_id", "id", name="uq_edge_events_market_id_id"),
    )
    op.create_index(
        EDGE_EVENT_SITE_TIME_INDEX, "edge_events", ["market_id", "site_id", "occurred_at"]
    )
    op.create_index(
        EDGE_EVENT_SITE_TYPE_INDEX,
        "edge_events",
        ["market_id", "site_id", "type", "occurred_at"],
    )

    op.create_table(
        "edge_files",
        sa.Column("market_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("id", pg.UUID(as_uuid=True), server_default=sa.text("uuidv7()"), nullable=False),
        sa.Column("site_id", sa.Text(), nullable=False),
        sa.Column("sha256", sa.Text(), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column("content_type", sa.Text(), nullable=False),
        sa.Column("storage_key", sa.Text(), nullable=False),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_edge_files"),
        _market_fk("edge_files"),
        _site_fk("edge_files"),
        sa.UniqueConstraint("market_id", "id", name="uq_edge_files_market_id_id"),
        sa.UniqueConstraint(
            "market_id", "site_id", "sha256", name="uq_edge_files_market_id_site_id_sha256"
        ),
        sa.CheckConstraint("size > 0", name="size_positive"),
    )

    for table in EDGE_TENANT_TABLES:
        enable_tenant_rls(table)
        create_entity(tenant_policy(table))
        create_entity(owner_bootstrap_policy(table))

    for function in EDGE_FUNCTIONS:
        create_entity(function)
    for signature in EDGE_GRANT_SIGNATURES:
        _regrant(signature)

    replace_entity(MARKET_DELETE_DRAFT)


def downgrade() -> None:
    """Downgrade schema — edge jadvallari va funksiyalari o'chiriladi."""
    replace_entity(MARKET_DELETE_DRAFT_WITHOUT_EDGE)

    for function in reversed(EDGE_FUNCTIONS):
        drop_entity(function)

    for table in reversed(EDGE_TENANT_TABLES):
        drop_entity(owner_bootstrap_policy(table))
        drop_entity(tenant_policy(table))

    op.drop_table("edge_files")
    op.drop_index(EDGE_EVENT_SITE_TYPE_INDEX, table_name="edge_events")
    op.drop_index(EDGE_EVENT_SITE_TIME_INDEX, table_name="edge_events")
    op.drop_table("edge_events")
    op.drop_index(EDGE_COMMAND_PENDING_INDEX, table_name="edge_commands")
    op.drop_table("edge_commands")
    op.drop_table("edge_configs")
    op.drop_index(EDGE_AGENT_SITE_INDEX, table_name="edge_agents")
    op.drop_table("edge_agents")
    op.drop_index(EDGE_ACTIVATION_SITE_INDEX, table_name="edge_activation_codes")
    op.drop_table("edge_activation_codes")
    op.drop_table("edge_sites")
