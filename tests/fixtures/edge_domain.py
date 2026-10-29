"""Ikki bozorli universal agent (edge) seed'i — `two_markets` ustiga qatlanadi (0036).

Har bozorda: bitta obyekt (`parking`), 1-versiya sozlama, bitta agent
(token xeshi bilan) va bitta fayl qatori. B bozorining qatorlari cross-tenant
matritsasining `site_id` / `file_id` fillerlari (HAQIQIY B obyekti).

⚠ TOZALASH BOZOR BO'YICHA (`market_id`), seed ID'lari bo'yicha EMAS: test
  davomida API orqali yaratilgan obyekt/kod/buyruq/hodisalar ham qoladi va
  ular `two_markets` ning `DELETE FROM markets` ini FK bilan yiqitardi.
"""

from __future__ import annotations

import hashlib
import json
import secrets
from contextlib import contextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator
    from uuid import UUID

    from psycopg import Connection
    from psycopg.rows import TupleRow

    from fixtures.two_markets import TwoMarketSeed

EDGE_TABLES_DELETE_ORDER = (
    "edge_events",
    "edge_files",
    "edge_commands",
    "edge_configs",
    "edge_agents",
    "edge_activation_codes",
    "edge_sites",
)

SEED_CONFIG = {
    "plugins": ["parking"],
    "update": {"channel": "stable", "auto": True},
}


@dataclass(frozen=True)
class MarketEdgeRows:
    market_id: UUID
    site_id: str
    agent_id: str
    token: str
    instance_id: str
    file_sha256: str


@dataclass(frozen=True)
class EdgeDomainSeed:
    market_a: MarketEdgeRows
    market_b: MarketEdgeRows


def _seed_market(conn: Connection[TupleRow], market_id: UUID, label: str) -> MarketEdgeRows:
    site_id = f"parking-{label}{secrets.token_hex(4)}"
    agent_id = f"agt-{secrets.token_hex(8)}"
    token = secrets.token_urlsafe(32)
    instance_id = f"inst-{secrets.token_hex(6)}"
    file_sha = hashlib.sha256(secrets.token_bytes(16)).hexdigest()
    conn.execute(
        "INSERT INTO edge_sites (market_id, id, kind, name) VALUES (%s, %s, 'parking', %s)",
        (str(market_id), site_id, f"Seed obyekt {label}"),
    )
    conn.execute(
        "INSERT INTO edge_configs (market_id, site_id, version, doc) VALUES (%s, %s, 1, %s::jsonb)",
        (str(market_id), site_id, json.dumps(SEED_CONFIG)),
    )
    conn.execute(
        "INSERT INTO edge_agents (market_id, id, site_id, token_sha256, instance_id, hostname, "
        "version, os, last_seen_at) VALUES (%s, %s, %s, %s, %s, 'SEED-PC', '1.0.0', "
        "'windows/amd64', now())",
        (
            str(market_id),
            agent_id,
            site_id,
            hashlib.sha256(token.encode()).hexdigest(),
            instance_id,
        ),
    )
    conn.execute(
        "INSERT INTO edge_files (market_id, site_id, sha256, size, content_type, storage_key) "
        "VALUES (%s, %s, %s, 3, 'image/jpeg', %s)",
        (str(market_id), site_id, file_sha, f"edge/{site_id}/{file_sha}"),
    )
    return MarketEdgeRows(
        market_id=market_id,
        site_id=site_id,
        agent_id=agent_id,
        token=token,
        instance_id=instance_id,
        file_sha256=file_sha,
    )


def cleanup_edge(conn: Connection[TupleRow], market_ids: list[UUID]) -> None:
    ids = [str(market_id) for market_id in market_ids]
    for table in EDGE_TABLES_DELETE_ORDER:
        conn.execute(f"DELETE FROM {table} WHERE market_id = ANY(%s::uuid[])", (ids,))  # noqa: S608


@contextmanager
def edge_rows(conn: Connection[TupleRow], base: TwoMarketSeed) -> Iterator[EdgeDomainSeed]:
    """Seed + bozor bo'yicha tozalash (kontekst menejeri)."""
    seed = EdgeDomainSeed(
        market_a=_seed_market(conn, base.market_a.id, "a"),
        market_b=_seed_market(conn, base.market_b.id, "b"),
    )
    try:
        yield seed
    finally:
        cleanup_edge(conn, [base.market_a.id, base.market_b.id])
