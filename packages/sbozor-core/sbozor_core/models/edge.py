"""Universal agent (edge) domeni — 0036.

Bozor, avtoturargoh va mol bozoriga o'rnatiladigan Windows agenti
(`sbozor-agent`) serverga O'ZI ulanadi (HTTPS long-poll). Protokol —
agent repozitoriyasidagi `docs/protocol-http.md`; JSON sxemalar
`services/core-api/app/edge_contract/schemas/` ga ko'chirilgan.

=============================================================================
1. HAMMA JADVAL TENANT (`market_id` + RLS). Obyekt (`edge_sites`) bitta
   bozorga tegishli; agent tokeni bozorni topish uchun `SECURITY DEFINER`
   funksiya orqali qidiriladi (`edge_agent_auth()`), keyingi har so'rov
   odatdagidek RLS ostida — `refresh_tokens.jti` naqshi.
2. IKKI GLOBAL UNIQUE INDEKS (`token_sha256`, `code`) — tenant hali
   noma'lum paytdagi qidiruv kaliti. Sabab `tests/tenancy/test_meta.py::
   INDEX_EXCEPTIONS` da yozilgan.
3. TOKEN OCHIQ SAQLANMAYDI — faqat SHA-256 xeshi.
4. SHAXSIY MA'LUMOT YO'Q: ism/telefon ustuni yo'q; `issued_by` — foydalanuvchi
   ID si yoki `system`.
5. PUL MANTIG'I YO'Q: `edge_events` — agent hodisalarining jurnali,
   `payments` ga hech narsa yozilmaydi.
=============================================================================
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUuid
from sqlalchemy.orm import Mapped, mapped_column

from sbozor_core.models.base import Base, TenantMixin, uuid_pk

__all__ = [
    "EDGE_ACTIVATION_SITE_INDEX",
    "EDGE_AGENT_SITE_INDEX",
    "EDGE_COMMAND_PENDING_INDEX",
    "EDGE_COMMAND_RESULT_CHECK",
    "EDGE_COMMAND_RESULT_VALUES",
    "EDGE_EVENT_SITE_TIME_INDEX",
    "EDGE_EVENT_SITE_TYPE_INDEX",
    "EDGE_SITE_KIND_CHECK",
    "EDGE_SITE_KIND_VALUES",
    "EdgeActivationCode",
    "EdgeAgent",
    "EdgeCommand",
    "EdgeConfig",
    "EdgeEvent",
    "EdgeFile",
    "EdgeSite",
]

EDGE_SITE_KIND_VALUES: tuple[str, ...] = ("parking", "market", "livestock")
EDGE_SITE_KIND_CHECK = "kind IN ('parking', 'market', 'livestock')"

EDGE_COMMAND_RESULT_VALUES: tuple[str, ...] = ("done", "rejected", "failed", "expired")
EDGE_COMMAND_RESULT_CHECK = (
    "result_status IS NULL OR result_status IN ('done', 'rejected', 'failed', 'expired')"
)

EDGE_ACTIVATION_SITE_INDEX = "ix_edge_activation_codes_market_id_site_id"
EDGE_AGENT_SITE_INDEX = "ix_edge_agents_market_id_site_id"
EDGE_COMMAND_PENDING_INDEX = "ix_edge_commands_market_id_site_id_delivered_at"
EDGE_EVENT_SITE_TIME_INDEX = "ix_edge_events_market_id_site_id_occurred_at"
EDGE_EVENT_SITE_TYPE_INDEX = "ix_edge_events_market_id_site_id_type_occurred_at"


def _site_fk(table: str) -> ForeignKeyConstraint:
    return ForeignKeyConstraint(
        ["market_id", "site_id"],
        ["edge_sites.market_id", "edge_sites.id"],
        name=f"fk_{table}_site",
    )


def _market_fk(table: str) -> ForeignKeyConstraint:
    return ForeignKeyConstraint(["market_id"], ["markets.id"], name=f"fk_{table}_market_id_markets")


def _created_at() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class EdgeSite(Base, TenantMixin):
    """Obyekt — agent o'rnatilgan joy (avtoturargoh, bozor, mol bozori).

    `setup` — obyektda o'rnatuvchi kiritgan jismoniy tuzilma (`devices`,
    `lanes`); uni agent `PUT /api/v1/edge/site-setup` bilan yuboradi. Biznes
    sozlamasi bu yerda EMAS — `edge_configs` da, versiyalangan.
    """

    __tablename__ = "edge_sites"
    __table_args__ = (
        _market_fk("edge_sites"),
        UniqueConstraint("market_id", "id", name="uq_edge_sites_market_id_id"),
        CheckConstraint(EDGE_SITE_KIND_CHECK, name="kind_allowed"),
    )

    id: Mapped[str] = mapped_column(Text(), primary_key=True)
    kind: Mapped[str] = mapped_column(Text(), nullable=False)
    name: Mapped[str] = mapped_column(Text(), nullable=False)
    setup: Mapped[dict[str, Any]] = mapped_column(
        JSONB(), nullable=False, server_default=text("'{}'::jsonb")
    )
    created_by: Mapped[UUID | None] = mapped_column(PgUuid(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = _created_at()


class EdgeActivationCode(Base, TenantMixin):
    """Bir martalik aktivatsiya kodi (`XXXX-XXXX`, 7 kun)."""

    __tablename__ = "edge_activation_codes"
    __table_args__ = (
        _market_fk("edge_activation_codes"),
        _site_fk("edge_activation_codes"),
        UniqueConstraint("market_id", "id", name="uq_edge_activation_codes_market_id_id"),
        UniqueConstraint("code", name="uq_edge_activation_codes_code"),
        Index(EDGE_ACTIVATION_SITE_INDEX, "market_id", "site_id"),
    )

    id: Mapped[UUID] = uuid_pk()
    site_id: Mapped[str] = mapped_column(Text(), nullable=False)
    code: Mapped[str] = mapped_column(Text(), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    used_by_agent_id: Mapped[str | None] = mapped_column(Text(), nullable=True)
    created_by: Mapped[UUID | None] = mapped_column(PgUuid(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = _created_at()


class EdgeAgent(Base, TenantMixin):
    """Faollashtirilgan agent nusxasi — bitta token = bitta `instance_id`."""

    __tablename__ = "edge_agents"
    __table_args__ = (
        _market_fk("edge_agents"),
        _site_fk("edge_agents"),
        UniqueConstraint("market_id", "id", name="uq_edge_agents_market_id_id"),
        UniqueConstraint("token_sha256", name="uq_edge_agents_token_sha256"),
        Index(EDGE_AGENT_SITE_INDEX, "market_id", "site_id"),
    )

    id: Mapped[str] = mapped_column(Text(), primary_key=True)
    site_id: Mapped[str] = mapped_column(Text(), nullable=False)
    token_sha256: Mapped[str] = mapped_column(Text(), nullable=False)
    instance_id: Mapped[str] = mapped_column(Text(), nullable=False)
    hostname: Mapped[str] = mapped_column(Text(), nullable=False)
    version: Mapped[str] = mapped_column(Text(), nullable=False)
    os: Mapped[str] = mapped_column(Text(), nullable=False)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_heartbeat: Mapped[dict[str, Any] | None] = mapped_column(JSONB(), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = _created_at()


class EdgeConfig(Base, TenantMixin):
    """Biznes sozlamasining versiyasi (append-only; `devices`/`lanes` YO'Q)."""

    __tablename__ = "edge_configs"
    __table_args__ = (
        _market_fk("edge_configs"),
        _site_fk("edge_configs"),
        UniqueConstraint("market_id", "id", name="uq_edge_configs_market_id_id"),
        UniqueConstraint(
            "market_id", "site_id", "version", name="uq_edge_configs_market_id_site_id_version"
        ),
        CheckConstraint("version >= 1", name="version_positive"),
    )

    id: Mapped[UUID] = uuid_pk()
    site_id: Mapped[str] = mapped_column(Text(), nullable=False)
    version: Mapped[int] = mapped_column(Integer(), nullable=False)
    doc: Mapped[dict[str, Any]] = mapped_column(JSONB(), nullable=False)
    created_by: Mapped[UUID | None] = mapped_column(PgUuid(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = _created_at()


class EdgeCommand(Base, TenantMixin):
    """Server -> agent buyrug'i (`command.schema.json`)."""

    __tablename__ = "edge_commands"
    __table_args__ = (
        _market_fk("edge_commands"),
        _site_fk("edge_commands"),
        UniqueConstraint("market_id", "id", name="uq_edge_commands_market_id_id"),
        CheckConstraint(EDGE_COMMAND_RESULT_CHECK, name="result_status_allowed"),
        Index(EDGE_COMMAND_PENDING_INDEX, "market_id", "site_id", "delivered_at"),
    )

    id: Mapped[UUID] = uuid_pk()
    site_id: Mapped[str] = mapped_column(Text(), nullable=False)
    type: Mapped[str] = mapped_column(Text(), nullable=False)
    data: Mapped[dict[str, Any]] = mapped_column(
        JSONB(), nullable=False, server_default=text("'{}'::jsonb")
    )
    issued_by: Mapped[str] = mapped_column(Text(), nullable=False)
    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    result_status: Mapped[str | None] = mapped_column(Text(), nullable=True)
    result_reason: Mapped[str | None] = mapped_column(Text(), nullable=True)
    result_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class EdgeEvent(Base, TenantMixin):
    """Agent hodisasi (`envelope.schema.json`) — append-only, `id` bo'yicha idempotent."""

    __tablename__ = "edge_events"
    __table_args__ = (
        _market_fk("edge_events"),
        _site_fk("edge_events"),
        UniqueConstraint("market_id", "id", name="uq_edge_events_market_id_id"),
        Index(EDGE_EVENT_SITE_TIME_INDEX, "market_id", "site_id", "occurred_at"),
        Index(EDGE_EVENT_SITE_TYPE_INDEX, "market_id", "site_id", "type", "occurred_at"),
    )

    id: Mapped[UUID] = mapped_column(PgUuid(as_uuid=True), primary_key=True)
    site_id: Mapped[str] = mapped_column(Text(), nullable=False)
    agent_id: Mapped[str] = mapped_column(Text(), nullable=False)
    type: Mapped[str] = mapped_column(Text(), nullable=False)
    v: Mapped[int] = mapped_column(Integer(), nullable=False)
    seq: Mapped[int] = mapped_column(BigInteger(), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    clock_ok: Mapped[bool] = mapped_column(Boolean(), nullable=False)
    correlation_id: Mapped[UUID | None] = mapped_column(PgUuid(as_uuid=True), nullable=True)
    data: Mapped[dict[str, Any]] = mapped_column(JSONB(), nullable=False)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class EdgeFile(Base, TenantMixin):
    """Agent yuklagan fayl (kadr) — baytlar obyekt omborida `edge/{site_id}/`."""

    __tablename__ = "edge_files"
    __table_args__ = (
        _market_fk("edge_files"),
        _site_fk("edge_files"),
        UniqueConstraint("market_id", "id", name="uq_edge_files_market_id_id"),
        UniqueConstraint(
            "market_id", "site_id", "sha256", name="uq_edge_files_market_id_site_id_sha256"
        ),
        CheckConstraint("size > 0", name="size_positive"),
    )

    id: Mapped[UUID] = uuid_pk()
    site_id: Mapped[str] = mapped_column(Text(), nullable=False)
    sha256: Mapped[str] = mapped_column(Text(), nullable=False)
    size: Mapped[int] = mapped_column(Integer(), nullable=False)
    content_type: Mapped[str] = mapped_column(Text(), nullable=False)
    storage_key: Mapped[str] = mapped_column(Text(), nullable=False)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
