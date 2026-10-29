"""Universal agent (edge) domeni — `edge_*` jadvallari (0036).

⛔ CHAQIRUVCHI TENANT KONTEKSTINI O'RNATGAN BO'LISHI SHART — ikkita
   istisno: `agent_auth()` va `activation_find()` bozor NOMA'LUM paytda
   `SECURITY DEFINER` funksiya orqali qidiradi (`refresh_tokens.jti`
   naqshi) va faqat identifikator qaytaradi.

Har so'rovda `market_id` predikati ham yoziladi (P9 — ikkinchi qatlam).
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sbozor_core.models import (
    EdgeActivationCode,
    EdgeAgent,
    EdgeCommand,
    EdgeConfig,
    EdgeEvent,
    EdgeFile,
    EdgeSite,
)
from sqlalchemy import and_, func, insert, select, text, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy.ext.asyncio import AsyncSession

__all__ = [
    "ACTIVATION_ALPHABET",
    "ACTIVATION_TTL",
    "ONLINE_WINDOW",
    "ActivationRow",
    "AgentAuth",
    "AgentRow",
    "CommandRow",
    "ConfigRow",
    "EventRow",
    "FileRow",
    "SiteRow",
    "activation_find",
    "agent_auth",
    "claim_code",
    "create_agent",
    "create_code",
    "create_command",
    "create_site",
    "deliver_commands",
    "get_file",
    "get_site",
    "insert_config",
    "insert_events",
    "insert_file",
    "latest_agent",
    "latest_config",
    "latest_versions",
    "list_commands",
    "list_events",
    "list_sites",
    "live_conflict",
    "new_site_id",
    "pending_commands",
    "record_heartbeat",
    "set_results",
    "set_setup",
    "summary_events",
    "touch_agent",
]

ACTIVATION_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
"""Kod alifbosi — chalkashadigan belgilar (0/O, 1/I/L) YO'Q."""

ACTIVATION_TTL = timedelta(days=7)
ONLINE_WINDOW = timedelta(minutes=3)
"""`last_seen_at` shu oyna ichida bo'lsa agent «onlayn»."""

LIVE_CONFLICT_WINDOW = timedelta(minutes=10)
"""Faollashtirishda: boshqa nusxa shu oyna ichida ko'ringan bo'lsa — 409."""


@dataclass(frozen=True, slots=True)
class AgentAuth:
    agent_id: str
    site_id: str
    market_id: UUID
    instance_id: str


@dataclass(frozen=True, slots=True)
class ActivationRow:
    code_id: UUID
    site_id: str
    market_id: UUID
    expires_at: datetime
    used_at: datetime | None


@dataclass(frozen=True, slots=True)
class SiteRow:
    id: str
    kind: str
    name: str
    setup: dict[str, Any]
    created_at: datetime


@dataclass(frozen=True, slots=True)
class AgentRow:
    id: str
    site_id: str
    instance_id: str
    hostname: str
    version: str
    os: str
    last_seen_at: datetime | None
    last_heartbeat: dict[str, Any] | None


@dataclass(frozen=True, slots=True)
class ConfigRow:
    version: int
    doc: dict[str, Any]
    created_at: datetime


@dataclass(frozen=True, slots=True)
class CommandRow:
    id: UUID
    site_id: str
    type: str
    data: dict[str, Any]
    issued_by: str
    issued_at: datetime
    expires_at: datetime
    delivered_at: datetime | None
    result_status: str | None
    result_reason: str | None
    result_at: datetime | None


@dataclass(frozen=True, slots=True)
class EventRow:
    id: UUID
    type: str
    v: int
    seq: int
    occurred_at: datetime
    received_at: datetime
    clock_ok: bool
    correlation_id: UUID | None
    data: dict[str, Any]


@dataclass(frozen=True, slots=True)
class FileRow:
    sha256: str
    size: int
    content_type: str
    storage_key: str


# ---------------------------------------------------------------------------
# Bozor noma'lum paytdagi qidiruv (SECURITY DEFINER)
# ---------------------------------------------------------------------------

_AGENT_AUTH = text(
    "SELECT agent_id, site_id, market_id, instance_id FROM edge_agent_auth(:token_sha256)"
)
_ACTIVATION_FIND = text(
    "SELECT code_id, site_id, market_id, expires_at, used_at FROM edge_activation_find(:code)"
)


async def agent_auth(session: AsyncSession, token_sha256: str) -> AgentAuth | None:
    row = (await session.execute(_AGENT_AUTH, {"token_sha256": token_sha256})).first()
    if row is None:
        return None
    return AgentAuth(
        agent_id=row.agent_id,
        site_id=row.site_id,
        market_id=row.market_id,
        instance_id=row.instance_id,
    )


async def activation_find(session: AsyncSession, code: str) -> ActivationRow | None:
    row = (await session.execute(_ACTIVATION_FIND, {"code": code})).first()
    if row is None:
        return None
    return ActivationRow(
        code_id=row.code_id,
        site_id=row.site_id,
        market_id=row.market_id,
        expires_at=row.expires_at,
        used_at=row.used_at,
    )


# ---------------------------------------------------------------------------
# Obyekt
# ---------------------------------------------------------------------------


def new_site_id(kind: str) -> str:
    """`parking-3fa9c1b2d4` — server yaratadi, erkin matn KIRMAYDI (S3 kaliti)."""
    return f"{kind}-{secrets.token_hex(5)}"


def _site(row: Any) -> SiteRow:
    return SiteRow(
        id=row.id,
        kind=row.kind,
        name=row.name,
        setup=dict(row.setup or {}),
        created_at=row.created_at,
    )


_SITE_COLUMNS = (EdgeSite.id, EdgeSite.kind, EdgeSite.name, EdgeSite.setup, EdgeSite.created_at)


async def create_site(
    session: AsyncSession,
    market_id: UUID,
    *,
    site_id: str,
    kind: str,
    name: str,
    created_by: UUID | None,
) -> SiteRow:
    row = (
        await session.execute(
            insert(EdgeSite)
            .values(market_id=market_id, id=site_id, kind=kind, name=name, created_by=created_by)
            .returning(*_SITE_COLUMNS)
        )
    ).one()
    return _site(row)


async def get_site(session: AsyncSession, market_id: UUID, site_id: str) -> SiteRow | None:
    row = (
        await session.execute(
            select(*_SITE_COLUMNS).where(EdgeSite.market_id == market_id, EdgeSite.id == site_id)
        )
    ).first()
    return None if row is None else _site(row)


async def list_sites(session: AsyncSession, market_id: UUID) -> list[SiteRow]:
    rows = (
        await session.execute(
            select(*_SITE_COLUMNS)
            .where(EdgeSite.market_id == market_id)
            .order_by(EdgeSite.created_at, EdgeSite.id)
        )
    ).all()
    return [_site(row) for row in rows]


async def set_setup(
    session: AsyncSession, market_id: UUID, site_id: str, setup: dict[str, Any]
) -> None:
    await session.execute(
        update(EdgeSite)
        .where(EdgeSite.market_id == market_id, EdgeSite.id == site_id)
        .values(setup=setup)
    )


# ---------------------------------------------------------------------------
# Aktivatsiya kodi
# ---------------------------------------------------------------------------


def _new_code() -> str:
    raw = "".join(secrets.choice(ACTIVATION_ALPHABET) for _ in range(8))
    return f"{raw[:4]}-{raw[4:]}"


async def create_code(
    session: AsyncSession, market_id: UUID, site_id: str, *, created_by: UUID | None
) -> tuple[str, datetime]:
    """Yangi kod (global noyob). To'qnashuv deyarli imkonsiz, lekin qayta urinadi."""
    expires_at = datetime.now(UTC) + ACTIVATION_TTL
    for _ in range(5):
        code = _new_code()
        inserted = (
            await session.execute(
                pg_insert(EdgeActivationCode)
                .values(
                    market_id=market_id,
                    site_id=site_id,
                    code=code,
                    expires_at=expires_at,
                    created_by=created_by,
                )
                .on_conflict_do_nothing(index_elements=["code"])
                .returning(EdgeActivationCode.id)
            )
        ).first()
        if inserted is not None:
            return code, expires_at
    raise RuntimeError("aktivatsiya kodi yaratib bo'lmadi")


async def claim_code(
    session: AsyncSession, market_id: UUID, code_id: UUID, *, agent_id: str
) -> bool:
    """Kodni band qiladi — faqat hali ishlatilmagan va muddati o'tmagan bo'lsa."""
    row = (
        await session.execute(
            update(EdgeActivationCode)
            .where(
                EdgeActivationCode.market_id == market_id,
                EdgeActivationCode.id == code_id,
                EdgeActivationCode.used_at.is_(None),
                EdgeActivationCode.expires_at > func.now(),
            )
            .values(used_at=func.now(), used_by_agent_id=agent_id)
            .returning(EdgeActivationCode.id)
        )
    ).first()
    return row is not None


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------


def _agent(row: Any) -> AgentRow:
    return AgentRow(
        id=row.id,
        site_id=row.site_id,
        instance_id=row.instance_id,
        hostname=row.hostname,
        version=row.version,
        os=row.os,
        last_seen_at=row.last_seen_at,
        last_heartbeat=row.last_heartbeat,
    )


_AGENT_COLUMNS = (
    EdgeAgent.id,
    EdgeAgent.site_id,
    EdgeAgent.instance_id,
    EdgeAgent.hostname,
    EdgeAgent.version,
    EdgeAgent.os,
    EdgeAgent.last_seen_at,
    EdgeAgent.last_heartbeat,
)


async def live_conflict(
    session: AsyncSession, market_id: UUID, site_id: str, instance_id: str
) -> bool:
    """Obyektda BOSHQA nusxa yaqinda (10 daqiqa) ko'ringanmi."""
    row = (
        await session.execute(
            select(EdgeAgent.id).where(
                EdgeAgent.market_id == market_id,
                EdgeAgent.site_id == site_id,
                EdgeAgent.revoked_at.is_(None),
                EdgeAgent.instance_id != instance_id,
                EdgeAgent.last_seen_at > func.now() - LIVE_CONFLICT_WINDOW,
            )
        )
    ).first()
    return row is not None


async def create_agent(
    session: AsyncSession,
    market_id: UUID,
    *,
    agent_id: str,
    site_id: str,
    token_sha256: str,
    instance_id: str,
    hostname: str,
    version: str,
    os: str,
) -> None:
    """Yangi agent; obyektdagi oldingi agentlar bekor qilinadi (bitta obyekt = bitta agent)."""
    await session.execute(
        update(EdgeAgent)
        .where(
            EdgeAgent.market_id == market_id,
            EdgeAgent.site_id == site_id,
            EdgeAgent.revoked_at.is_(None),
        )
        .values(revoked_at=func.now())
    )
    await session.execute(
        insert(EdgeAgent).values(
            market_id=market_id,
            id=agent_id,
            site_id=site_id,
            token_sha256=token_sha256,
            instance_id=instance_id,
            hostname=hostname,
            version=version,
            os=os,
            last_seen_at=func.now(),
        )
    )


async def touch_agent(session: AsyncSession, market_id: UUID, agent_id: str) -> None:
    await session.execute(
        update(EdgeAgent)
        .where(EdgeAgent.market_id == market_id, EdgeAgent.id == agent_id)
        .values(last_seen_at=func.now())
    )


async def record_heartbeat(
    session: AsyncSession, market_id: UUID, agent_id: str, heartbeat: dict[str, Any]
) -> None:
    values: dict[str, Any] = {"last_seen_at": func.now(), "last_heartbeat": heartbeat}
    version = heartbeat.get("version")
    if isinstance(version, str) and version:
        values["version"] = version[:64]
    await session.execute(
        update(EdgeAgent)
        .where(EdgeAgent.market_id == market_id, EdgeAgent.id == agent_id)
        .values(**values)
    )


async def latest_agent(
    session: AsyncSession, market_id: UUID, site_ids: Sequence[str]
) -> dict[str, AgentRow]:
    """Har obyektning amaldagi (bekor qilinmagan, eng yangi) agenti."""
    if not site_ids:
        return {}
    rows = (
        await session.execute(
            select(*_AGENT_COLUMNS)
            .where(
                EdgeAgent.market_id == market_id,
                EdgeAgent.site_id.in_(list(site_ids)),
                EdgeAgent.revoked_at.is_(None),
            )
            .order_by(EdgeAgent.site_id, EdgeAgent.created_at.desc())
        )
    ).all()
    out: dict[str, AgentRow] = {}
    for row in rows:
        out.setdefault(row.site_id, _agent(row))
    return out


# ---------------------------------------------------------------------------
# Sozlama (append-only versiyalar)
# ---------------------------------------------------------------------------


async def latest_config(session: AsyncSession, market_id: UUID, site_id: str) -> ConfigRow | None:
    row = (
        await session.execute(
            select(EdgeConfig.version, EdgeConfig.doc, EdgeConfig.created_at)
            .where(EdgeConfig.market_id == market_id, EdgeConfig.site_id == site_id)
            .order_by(EdgeConfig.version.desc())
            .limit(1)
        )
    ).first()
    if row is None:
        return None
    return ConfigRow(version=row.version, doc=dict(row.doc), created_at=row.created_at)


async def latest_versions(
    session: AsyncSession, market_id: UUID, site_ids: Sequence[str]
) -> dict[str, int]:
    if not site_ids:
        return {}
    rows = (
        await session.execute(
            select(EdgeConfig.site_id, func.max(EdgeConfig.version))
            .where(EdgeConfig.market_id == market_id, EdgeConfig.site_id.in_(list(site_ids)))
            .group_by(EdgeConfig.site_id)
        )
    ).all()
    return {row[0]: int(row[1]) for row in rows}


async def insert_config(
    session: AsyncSession,
    market_id: UUID,
    site_id: str,
    *,
    doc: dict[str, Any],
    created_by: UUID | None,
) -> ConfigRow:
    """Keyingi versiyani yozadi. Parallel yozuvda UNIQUE `IntegrityError` beradi."""
    current = await latest_config(session, market_id, site_id)
    version = 1 if current is None else current.version + 1
    row = (
        await session.execute(
            insert(EdgeConfig)
            .values(
                market_id=market_id,
                site_id=site_id,
                version=version,
                doc=doc,
                created_by=created_by,
            )
            .returning(EdgeConfig.version, EdgeConfig.doc, EdgeConfig.created_at)
        )
    ).one()
    return ConfigRow(version=row.version, doc=dict(row.doc), created_at=row.created_at)


# ---------------------------------------------------------------------------
# Buyruqlar
# ---------------------------------------------------------------------------

_COMMAND_COLUMNS = (
    EdgeCommand.id,
    EdgeCommand.site_id,
    EdgeCommand.type,
    EdgeCommand.data,
    EdgeCommand.issued_by,
    EdgeCommand.issued_at,
    EdgeCommand.expires_at,
    EdgeCommand.delivered_at,
    EdgeCommand.result_status,
    EdgeCommand.result_reason,
    EdgeCommand.result_at,
)


def _command(row: Any) -> CommandRow:
    return CommandRow(
        id=row.id,
        site_id=row.site_id,
        type=row.type,
        data=dict(row.data or {}),
        issued_by=row.issued_by,
        issued_at=row.issued_at,
        expires_at=row.expires_at,
        delivered_at=row.delivered_at,
        result_status=row.result_status,
        result_reason=row.result_reason,
        result_at=row.result_at,
    )


async def create_command(
    session: AsyncSession,
    market_id: UUID,
    site_id: str,
    *,
    type_: str,
    data: dict[str, Any],
    issued_by: str,
    expires_in: timedelta,
) -> CommandRow:
    now = datetime.now(UTC)
    row = (
        await session.execute(
            insert(EdgeCommand)
            .values(
                market_id=market_id,
                site_id=site_id,
                type=type_,
                data=data,
                issued_by=issued_by,
                issued_at=now,
                expires_at=now + expires_in,
            )
            .returning(*_COMMAND_COLUMNS)
        )
    ).one()
    return _command(row)


async def pending_commands(session: AsyncSession, market_id: UUID, site_id: str) -> bool:
    """Yetkazilmagan va muddati o'tmagan buyruq bormi (arzon tekshiruv)."""
    row = (
        await session.execute(
            select(EdgeCommand.id)
            .where(
                EdgeCommand.market_id == market_id,
                EdgeCommand.site_id == site_id,
                EdgeCommand.delivered_at.is_(None),
                EdgeCommand.expires_at > func.now(),
            )
            .limit(1)
        )
    ).first()
    return row is not None


async def deliver_commands(
    session: AsyncSession, market_id: UUID, site_id: str
) -> list[CommandRow]:
    """Yetkazilmagan va muddati o'tmagan buyruqlarni «yetkazildi» deb belgilab qaytaradi.

    Shartli `UPDATE ... WHERE delivered_at IS NULL RETURNING` — ikki parallel
    `poll` bir buyruqni ikki marta olmaydi.
    """
    rows = (
        await session.execute(
            update(EdgeCommand)
            .where(
                EdgeCommand.market_id == market_id,
                EdgeCommand.site_id == site_id,
                EdgeCommand.delivered_at.is_(None),
                EdgeCommand.expires_at > func.now(),
            )
            .values(delivered_at=func.now())
            .returning(*_COMMAND_COLUMNS)
        )
    ).all()
    return sorted((_command(row) for row in rows), key=lambda c: (c.issued_at, str(c.id)))


async def set_results(
    session: AsyncSession,
    market_id: UUID,
    site_id: str,
    results: Sequence[tuple[UUID, str, str | None]],
) -> set[UUID]:
    """Natijalarni yozadi; FAQAT shu obyektning buyruqlari. Topilganlar ID si qaytadi."""
    found: set[UUID] = set()
    for command_id, status, reason in results:
        row = (
            await session.execute(
                update(EdgeCommand)
                .where(
                    EdgeCommand.market_id == market_id,
                    EdgeCommand.site_id == site_id,
                    EdgeCommand.id == command_id,
                )
                .values(result_status=status, result_reason=reason, result_at=func.now())
                .returning(EdgeCommand.id)
            )
        ).first()
        if row is not None:
            found.add(row.id)
    return found


async def list_commands(
    session: AsyncSession, market_id: UUID, site_id: str, *, limit: int = 20
) -> list[CommandRow]:
    rows = (
        await session.execute(
            select(*_COMMAND_COLUMNS)
            .where(EdgeCommand.market_id == market_id, EdgeCommand.site_id == site_id)
            .order_by(EdgeCommand.issued_at.desc(), EdgeCommand.id.desc())
            .limit(limit)
        )
    ).all()
    return [_command(row) for row in rows]


# ---------------------------------------------------------------------------
# Hodisalar
# ---------------------------------------------------------------------------


async def insert_events(
    session: AsyncSession, market_id: UUID, site_id: str, rows: Sequence[dict[str, Any]]
) -> None:
    """`id` bo'yicha idempotent: dublikat jimgina o'tkaziladi (`ON CONFLICT DO NOTHING`)."""
    if not rows:
        return
    await session.execute(
        pg_insert(EdgeEvent)
        .values([{**row, "market_id": market_id, "site_id": site_id} for row in rows])
        .on_conflict_do_nothing(index_elements=["id"])
    )


_EVENT_COLUMNS = (
    EdgeEvent.id,
    EdgeEvent.type,
    EdgeEvent.v,
    EdgeEvent.seq,
    EdgeEvent.occurred_at,
    EdgeEvent.received_at,
    EdgeEvent.clock_ok,
    EdgeEvent.correlation_id,
    EdgeEvent.data,
)


def _event(row: Any) -> EventRow:
    return EventRow(
        id=row.id,
        type=row.type,
        v=row.v,
        seq=row.seq,
        occurred_at=row.occurred_at,
        received_at=row.received_at,
        clock_ok=row.clock_ok,
        correlation_id=row.correlation_id,
        data=dict(row.data or {}),
    )


async def list_events(
    session: AsyncSession,
    market_id: UUID,
    site_id: str,
    *,
    event_type: str | None,
    limit: int,
    offset: int,
) -> list[EventRow]:
    conditions = [EdgeEvent.market_id == market_id, EdgeEvent.site_id == site_id]
    if event_type:
        conditions.append(EdgeEvent.type == event_type)
    rows = (
        await session.execute(
            select(*_EVENT_COLUMNS)
            .where(and_(*conditions))
            .order_by(EdgeEvent.occurred_at.desc(), EdgeEvent.id.desc())
            .limit(limit)
            .offset(offset)
        )
    ).all()
    return [_event(row) for row in rows]


async def summary_events(
    session: AsyncSession,
    market_id: UUID,
    site_id: str,
    *,
    types: Sequence[str],
    start: datetime,
    end: datetime,
) -> list[EventRow]:
    """Kun oralig'idagi berilgan turdagi hodisalar (eskidan yangiga)."""
    rows = (
        await session.execute(
            select(*_EVENT_COLUMNS)
            .where(
                EdgeEvent.market_id == market_id,
                EdgeEvent.site_id == site_id,
                EdgeEvent.type.in_(list(types)),
                EdgeEvent.occurred_at >= start,
                EdgeEvent.occurred_at < end,
            )
            .order_by(EdgeEvent.occurred_at, EdgeEvent.id)
        )
    ).all()
    return [_event(row) for row in rows]


# ---------------------------------------------------------------------------
# Fayllar
# ---------------------------------------------------------------------------


async def get_file(
    session: AsyncSession, market_id: UUID, site_id: str, sha256: str
) -> FileRow | None:
    row = (
        await session.execute(
            select(
                EdgeFile.sha256, EdgeFile.size, EdgeFile.content_type, EdgeFile.storage_key
            ).where(
                EdgeFile.market_id == market_id,
                EdgeFile.site_id == site_id,
                EdgeFile.sha256 == sha256,
            )
        )
    ).first()
    if row is None:
        return None
    return FileRow(
        sha256=row.sha256, size=row.size, content_type=row.content_type, storage_key=row.storage_key
    )


async def insert_file(
    session: AsyncSession,
    market_id: UUID,
    site_id: str,
    *,
    sha256: str,
    size: int,
    content_type: str,
    storage_key: str,
) -> None:
    await session.execute(
        pg_insert(EdgeFile)
        .values(
            market_id=market_id,
            site_id=site_id,
            sha256=sha256,
            size=size,
            content_type=content_type,
            storage_key=storage_key,
        )
        .on_conflict_do_nothing(index_elements=["market_id", "site_id", "sha256"])
    )
