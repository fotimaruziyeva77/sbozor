"""Universal agent (0036) — agent protokoli va panel yuzasi HTTP orqali.

=============================================================================
O'lchanadigan da'volar:

  1. aktivatsiya: kod bir martalik, muddati o'tgani 404, obyektda boshqa
     jonli nusxa — 409; tokenli so'rovda boshqa `X-Instance-Id` — 409;
  2. poll: sozlama faqat yangiroq bo'lsa, buyruq bir marta yetkaziladi,
     muddati o'tgani yuborilmaydi;
  3. hodisalar: yaroqli qabul, dublikat qabul (bitta qator), yaroqsiz —
     sabab bilan rad, boshqa obyekt nomidan — rad;
  4. fayllar: xesh mos kelmasa 400, HEAD 200/404, panel kadrni beradi;
  5. relizlar: manifest so'zma-so'z, yo'l bo'lagi rad, reliz yo'q — 204;
  6. panel RBAC: boshqa bozor admini ko'rmaydi va buyruq bera olmaydi,
     kassir — 403, direktor faqat o'qiydi.
=============================================================================
"""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import time
import uuid
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

import pytest
from fixtures.admin_api import session_headers
from fixtures.edge_domain import edge_rows
from fixtures.two_markets import SEED_PASSWORD

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator
    from pathlib import Path

    import httpx
    from app.services.storage import SnapshotStorage
    from app.settings import Settings
    from fastapi import FastAPI
    from fixtures.edge_domain import EdgeDomainSeed, MarketEdgeRows
    from fixtures.two_markets import TwoMarketSeed
    from psycopg import Connection
    from psycopg.rows import TupleRow

pytestmark = pytest.mark.anyio

EDGE = "/api/v1/edge"
SITES = "/api/v1/edge-sites"


def uuid7() -> str:
    """UUIDv7 (Python 3.13 da `uuid.uuid7` yo'q)."""
    ms = int(time.time() * 1000)
    raw = bytearray(ms.to_bytes(6, "big") + os.urandom(10))
    raw[6] = (raw[6] & 0x0F) | 0x70
    raw[8] = (raw[8] & 0x3F) | 0x80
    return str(uuid.UUID(bytes=bytes(raw)))


def agent_headers(rows: MarketEdgeRows, *, instance: str | None = None) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {rows.token}",
        "X-Instance-Id": rows.instance_id if instance is None else instance,
    }


def event(
    rows: MarketEdgeRows, event_type: str, data: dict[str, Any], **extra: Any
) -> dict[str, Any]:
    body = {
        "id": uuid7(),
        "type": event_type,
        "v": 1,
        "site_id": rows.site_id,
        "agent_id": rows.agent_id,
        "seq": 1,
        "occurred_at": datetime.now(UTC).isoformat(),
        "clock_ok": True,
        "data": data,
    }
    body.update(extra)
    return body


@pytest.fixture
def edge(
    sync_owner_conn: Connection[TupleRow], two_markets: TwoMarketSeed, migrated: None
) -> Iterator[EdgeDomainSeed]:
    with edge_rows(sync_owner_conn, two_markets) as seed:
        yield seed


@pytest.fixture
def releases(api_app: FastAPI, test_settings: Settings, tmp_path: Path) -> Iterator[Path]:
    original = api_app.state.settings
    api_app.state.settings = test_settings.model_copy(update={"edge_releases_dir": str(tmp_path)})
    try:
        yield tmp_path
    finally:
        api_app.state.settings = original


@pytest.fixture
async def edge_keys(s3_client: SnapshotStorage, edge: EdgeDomainSeed) -> AsyncIterator[None]:
    """Test yozgan kadrlarni ombordan tozalaydi."""
    try:
        yield
    finally:
        for rows in (edge.market_a, edge.market_b):
            keys = await s3_client.list_prefix(f"edge/{rows.site_id}/")
            if keys:
                await s3_client.delete_many(keys)


async def admin_a(client: httpx.AsyncClient, two_markets: TwoMarketSeed) -> dict[str, str]:
    market = two_markets.market_a
    return await session_headers(client, market.admin_phone, market.admin_password)


async def admin_b(client: httpx.AsyncClient, two_markets: TwoMarketSeed) -> dict[str, str]:
    market = two_markets.market_b
    return await session_headers(client, market.admin_phone, market.admin_password)


def _add_code(conn: Connection[TupleRow], rows: MarketEdgeRows, *, expires_in: timedelta) -> str:
    code = f"{secrets.token_hex(2).upper()}-{secrets.token_hex(2).upper()}"
    conn.execute(
        "INSERT INTO edge_activation_codes (market_id, site_id, code, expires_at) "
        "VALUES (%s, %s, %s, %s)",
        (str(rows.market_id), rows.site_id, code, datetime.now(UTC) + expires_in),
    )
    return code


def _activation(code: str, instance: str) -> dict[str, str]:
    return {
        "code": code,
        "instance_id": instance,
        "hostname": "KASSA-1",
        "version": "1.0.0",
        "os": "windows/amd64",
    }


# ===========================================================================
# 1. Aktivatsiya va autentifikatsiya
# ===========================================================================


async def test_activation_is_single_use_and_returns_a_working_token(
    api_client: httpx.AsyncClient,
    sync_owner_conn: Connection[TupleRow],
    edge: EdgeDomainSeed,
) -> None:
    rows = edge.market_a
    # Seed agenti «jonli» — boshqa nusxani yangi kod bilan almashtirish uchun
    # avval u oflayn bo'lishi kerak.
    sync_owner_conn.execute(
        "UPDATE edge_agents SET last_seen_at = now() - interval '1 hour' WHERE id = %s",
        (rows.agent_id,),
    )
    code = _add_code(sync_owner_conn, rows, expires_in=timedelta(days=7))

    first = await api_client.post(f"{EDGE}/activate", json=_activation(code.lower(), "pc-new"))
    assert first.status_code == 200, first.text
    body = first.json()
    assert body["site_id"] == rows.site_id
    assert body["agent_id"].startswith("agt-")

    stored = sync_owner_conn.execute(
        "SELECT token_sha256, revoked_at FROM edge_agents WHERE id = %s", (body["agent_id"],)
    ).fetchone()
    assert stored is not None
    assert stored[0] == hashlib.sha256(body["token"].encode()).hexdigest()
    assert body["token"] not in stored[0]

    again = await api_client.post(f"{EDGE}/activate", json=_activation(code, "pc-new"))
    assert again.status_code == 404

    headers = {"Authorization": f"Bearer {body['token']}", "X-Instance-Id": "pc-new"}
    ok = await api_client.post(f"{EDGE}/heartbeat", json={"version": "1.0.1"}, headers=headers)
    assert ok.status_code == 200, ok.text
    assert ok.json()["server_time"].endswith("+05:00")

    # Eski agent bekor qilindi — uning tokeni endi 401.
    old = await api_client.post(f"{EDGE}/heartbeat", json={}, headers=agent_headers(rows))
    assert old.status_code == 401


async def test_expired_or_unknown_code_is_404(
    api_client: httpx.AsyncClient,
    sync_owner_conn: Connection[TupleRow],
    edge: EdgeDomainSeed,
) -> None:
    expired = _add_code(sync_owner_conn, edge.market_a, expires_in=timedelta(seconds=-1))
    response = await api_client.post(f"{EDGE}/activate", json=_activation(expired, "pc-x"))
    assert response.status_code == 404
    unknown = await api_client.post(f"{EDGE}/activate", json=_activation("ZZZZ-ZZZZ", "pc-x"))
    assert unknown.status_code == 404


async def test_activation_while_another_instance_is_live_is_409(
    api_client: httpx.AsyncClient,
    sync_owner_conn: Connection[TupleRow],
    edge: EdgeDomainSeed,
) -> None:
    code = _add_code(sync_owner_conn, edge.market_a, expires_in=timedelta(days=1))
    response = await api_client.post(f"{EDGE}/activate", json=_activation(code, "second-pc"))
    assert response.status_code == 409
    # Kod sarflanmadi.
    row = sync_owner_conn.execute(
        "SELECT used_at FROM edge_activation_codes WHERE code = %s", (code,)
    ).fetchone()
    assert row is not None
    assert row[0] is None


async def test_token_with_another_instance_is_409_and_bad_token_401(
    api_client: httpx.AsyncClient, edge: EdgeDomainSeed
) -> None:
    rows = edge.market_a
    conflict = await api_client.get(
        f"{EDGE}/poll", params={"wait": 0}, headers=agent_headers(rows, instance="other")
    )
    assert conflict.status_code == 409
    bad = await api_client.get(
        f"{EDGE}/poll",
        params={"wait": 0},
        headers={"Authorization": "Bearer nope", "X-Instance-Id": rows.instance_id},
    )
    assert bad.status_code == 401
    missing = await api_client.get(f"{EDGE}/poll", params={"wait": 0})
    assert missing.status_code == 401


# ===========================================================================
# 2. Poll
# ===========================================================================


async def test_poll_returns_config_only_when_newer(
    api_client: httpx.AsyncClient, edge: EdgeDomainSeed
) -> None:
    rows = edge.market_a
    fresh = await api_client.get(
        f"{EDGE}/poll", params={"config_version": 0, "wait": 0}, headers=agent_headers(rows)
    )
    assert fresh.status_code == 200, fresh.text
    config = fresh.json()["config"]
    assert config["config_version"] == 1
    assert config["site"] == {"id": rows.site_id, "type": "parking", "timezone": "Asia/Tashkent"}
    assert config["devices"] == []
    assert config["lanes"] == []

    same = await api_client.get(
        f"{EDGE}/poll", params={"config_version": 1, "wait": 0}, headers=agent_headers(rows)
    )
    assert same.status_code == 200
    assert same.json()["config"] is None
    assert same.json()["commands"] == []


async def test_commands_are_delivered_once_and_expired_ones_skipped(
    api_client: httpx.AsyncClient,
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    edge: EdgeDomainSeed,
) -> None:
    rows = edge.market_a
    headers = await admin_a(api_client, two_markets)
    created = await api_client.post(
        f"{SITES}/{rows.site_id}/commands",
        json={"type": "parking.gate.open", "data": {"lane_id": "kirish-1"}},
        headers=headers,
    )
    assert created.status_code == 201, created.text
    command = created.json()
    ttl = datetime.fromisoformat(command["expires_at"]) - datetime.fromisoformat(
        command["issued_at"]
    )
    assert ttl == timedelta(seconds=60)

    sync_owner_conn.execute(
        "INSERT INTO edge_commands (market_id, site_id, type, issued_by, expires_at) "
        "VALUES (%s, %s, 'core.config.refresh', 'system', now() - interval '1 minute')",
        (str(rows.market_id), rows.site_id),
    )

    first = await api_client.get(
        f"{EDGE}/poll", params={"config_version": 1, "wait": 0}, headers=agent_headers(rows)
    )
    assert first.status_code == 200
    commands = first.json()["commands"]
    assert [c["id"] for c in commands] == [command["id"]]
    assert commands[0]["type"] == "parking.gate.open"
    assert commands[0]["site_id"] == rows.site_id
    assert commands[0]["v"] == 1

    second = await api_client.get(
        f"{EDGE}/poll", params={"config_version": 1, "wait": 0}, headers=agent_headers(rows)
    )
    assert second.json()["commands"] == []

    result = await api_client.post(
        f"{EDGE}/results",
        json={"results": [{"command_id": command["id"], "status": "done"}]},
        headers=agent_headers(rows),
    )
    assert result.status_code == 200
    assert result.json()["accepted"] == [command["id"]]

    listed = await api_client.get(f"{SITES}/{rows.site_id}/commands", headers=headers)
    top = next(c for c in listed.json()["items"] if c["id"] == command["id"])
    assert top["result_status"] == "done"
    assert top["delivered_at"] is not None


async def test_results_cannot_touch_another_sites_command(
    api_client: httpx.AsyncClient, two_markets: TwoMarketSeed, edge: EdgeDomainSeed
) -> None:
    headers = await admin_b(api_client, two_markets)
    created = await api_client.post(
        f"{SITES}/{edge.market_b.site_id}/commands",
        json={"type": "core.config.refresh"},
        headers=headers,
    )
    assert created.status_code == 201
    response = await api_client.post(
        f"{EDGE}/results",
        json={"results": [{"command_id": created.json()["id"], "status": "done"}]},
        headers=agent_headers(edge.market_a),
    )
    assert response.json()["accepted"] == []
    assert response.json()["rejected"][0]["reason"].startswith("command_id")


# ===========================================================================
# 3. Hodisalar
# ===========================================================================


async def test_events_valid_duplicate_invalid_and_foreign_site(
    api_client: httpx.AsyncClient,
    sync_owner_conn: Connection[TupleRow],
    edge: EdgeDomainSeed,
) -> None:
    rows = edge.market_a
    good = event(
        rows,
        "parking.plate.read",
        {"lane_id": "kirish-1", "plate": "01A123BC", "confidence": 90, "direction": "in"},
    )
    invalid = event(
        rows,
        "parking.plate.read",
        {"lane_id": "kirish-1", "plate": "01 a 123", "confidence": 90, "direction": "in"},
    )
    foreign = event(
        rows,
        "core.agent.started",
        {"version": "1.0.0", "plugins": ["parking"]},
        site_id=edge.market_b.site_id,
    )
    response = await api_client.post(
        f"{EDGE}/events",
        json={"events": [good, good, invalid, foreign, "not-an-object"]},
        headers=agent_headers(rows),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["accepted"] == [good["id"], good["id"]]
    reasons = {item["id"]: item["reason"] for item in body["rejected"]}
    assert reasons[invalid["id"]].startswith("data.plate")
    assert reasons[foreign["id"]].startswith("site_id")
    assert len(body["rejected"]) == 3

    again = await api_client.post(
        f"{EDGE}/events", json={"events": [good]}, headers=agent_headers(rows)
    )
    assert again.json()["accepted"] == [good["id"]]

    counts = sync_owner_conn.execute(
        "SELECT market_id, count(*) FROM edge_events WHERE market_id = ANY(%s::uuid[]) "
        "GROUP BY market_id",
        ([str(edge.market_a.market_id), str(edge.market_b.market_id)],),
    ).fetchall()
    assert {str(m): c for m, c in counts} == {str(edge.market_a.market_id): 1}


async def test_more_than_200_events_is_rejected(
    api_client: httpx.AsyncClient, edge: EdgeDomainSeed
) -> None:
    rows = edge.market_a
    batch = [
        event(rows, "core.agent.started", {"version": "1.0.0", "plugins": []}) for _ in range(201)
    ]
    response = await api_client.post(
        f"{EDGE}/events", json={"events": batch}, headers=agent_headers(rows)
    )
    assert response.status_code == 422


async def test_parking_summary_counts_the_day(
    api_client: httpx.AsyncClient, two_markets: TwoMarketSeed, edge: EdgeDomainSeed
) -> None:
    rows = edge.market_a
    session_id = str(uuid.uuid4())
    events = [
        event(
            rows,
            "parking.session.opened",
            {
                "session_id": session_id,
                "lane_id": "kirish-1",
                "category": "car",
                "reason": "auto",
                "plate": "01A123BC",
            },
        ),
        event(
            rows,
            "parking.session.opened",
            {
                "session_id": str(uuid.uuid4()),
                "lane_id": "kirish-1",
                "category": "car",
                "reason": "no_plate",
            },
        ),
        event(
            rows,
            "parking.session.closed",
            {"session_id": session_id, "lane_id": "chiqish-1", "amount_soum": 3000},
        ),
        event(
            rows,
            "core.payment.cash",
            {
                "payment_id": str(uuid.uuid4()),
                "amount_soum": 3000,
                "method": "cash",
                "subject": {"kind": "parking_session", "id": session_id},
                "staff_id": "kassir-1",
                "fiscal_status": "manual",
            },
        ),
        event(
            rows,
            "core.payment.cash",
            {
                "payment_id": str(uuid.uuid4()),
                "amount_soum": 2000,
                "method": "terminal",
                "subject": {"kind": "parking_session", "id": session_id},
                "staff_id": "kassir-1",
                "fiscal_status": "manual",
            },
        ),
        event(
            rows,
            "parking.plate.read",
            {
                "lane_id": "kirish-1",
                "plate": "01A123BC",
                "confidence": 95,
                "direction": "in",
                "file_id": edge.market_a.file_sha256,
            },
        ),
    ]
    posted = await api_client.post(
        f"{EDGE}/events", json={"events": events}, headers=agent_headers(rows)
    )
    assert posted.json()["rejected"] == [], posted.text

    headers = await admin_a(api_client, two_markets)
    summary = await api_client.get(f"{SITES}/{rows.site_id}/parking-summary", headers=headers)
    assert summary.status_code == 200, summary.text
    body = summary.json()
    assert body["entries"] == 2
    assert body["exits"] == 1
    assert body["open_estimate"] == 1
    assert body["cash_total_soum"] == 5000
    assert body["cash_by_method"] == {"cash": 3000, "terminal": 2000}
    assert body["last_plates"][0]["plate"] == "01A123BC"
    assert body["last_plates"][0]["file_id"] == edge.market_a.file_sha256

    listed = await api_client.get(
        f"{SITES}/{rows.site_id}/events",
        params={"type": "parking.plate.read"},
        headers=headers,
    )
    items = listed.json()["items"]
    assert len(items) == 1
    assert items[0]["file_ids"] == [edge.market_a.file_sha256]


# ===========================================================================
# 4. Fayllar
# ===========================================================================


async def test_files_hash_check_head_and_admin_view(
    api_client: httpx.AsyncClient,
    two_markets: TwoMarketSeed,
    edge: EdgeDomainSeed,
    edge_keys: None,
) -> None:
    rows = edge.market_a
    payload = b"\xff\xd8\xff\xe0" + secrets.token_bytes(64)
    sha = hashlib.sha256(payload).hexdigest()

    missing = await api_client.head(f"{EDGE}/files/{sha}", headers=agent_headers(rows))
    assert missing.status_code == 404

    wrong = await api_client.put(
        f"{EDGE}/files/{'0' * 64}",
        content=payload,
        headers={**agent_headers(rows), "Content-Type": "image/jpeg"},
    )
    assert wrong.status_code == 400
    assert wrong.json()["detail"] == "hash_mismatch"

    stored = await api_client.put(
        f"{EDGE}/files/{sha}",
        content=payload,
        headers={**agent_headers(rows), "Content-Type": "image/jpeg"},
    )
    assert stored.status_code == 200, stored.text
    again = await api_client.put(
        f"{EDGE}/files/{sha}",
        content=payload,
        headers={**agent_headers(rows), "Content-Type": "image/jpeg"},
    )
    assert again.status_code == 200

    present = await api_client.head(f"{EDGE}/files/{sha}", headers=agent_headers(rows))
    assert present.status_code == 200
    # B agenti A ning faylini «ko'rmaydi».
    other = await api_client.head(f"{EDGE}/files/{sha}", headers=agent_headers(edge.market_b))
    assert other.status_code == 404

    headers = await admin_a(api_client, two_markets)
    frame = await api_client.get(f"{SITES}/{rows.site_id}/files/{sha}", headers=headers)
    assert frame.status_code == 200
    assert frame.content == payload
    assert frame.headers["content-type"] == "image/jpeg"

    foreign = await api_client.get(
        f"{SITES}/{rows.site_id}/files/{sha}", headers=await admin_b(api_client, two_markets)
    )
    assert foreign.status_code == 404


async def test_too_large_file_is_413(api_client: httpx.AsyncClient, edge: EdgeDomainSeed) -> None:
    payload = b"x" * (5 * 1024 * 1024 + 1)
    response = await api_client.put(
        f"{EDGE}/files/{hashlib.sha256(payload).hexdigest()}",
        content=payload,
        headers=agent_headers(edge.market_a),
    )
    assert response.status_code == 413


# ===========================================================================
# 5. Relizlar
# ===========================================================================


async def test_release_manifest_is_served_verbatim(
    api_client: httpx.AsyncClient, edge: EdgeDomainSeed, releases: Path
) -> None:
    rows = edge.market_a
    none = await api_client.get(
        f"{EDGE}/releases/latest", params={"channel": "stable"}, headers=agent_headers(rows)
    )
    assert none.status_code == 204

    raw = (
        b'{"manifest":{"version":"1.0.1","channel":"stable",'
        b'"url":"/api/v1/edge/releases/binary/1.0.1","sha256":"ab","size":3,"notes":"x"},'
        b'  "signature":"c2ln"}'
    )
    (releases / "stable").mkdir()
    (releases / "stable" / "latest.json").write_bytes(raw)
    (releases / "bin").mkdir()
    (releases / "bin" / "sbozor-agent-1.0.1.exe").write_bytes(b"MZ\x00")
    (releases / "secret.exe").write_bytes(b"nope")

    served = await api_client.get(
        f"{EDGE}/releases/latest", params={"channel": "stable"}, headers=agent_headers(rows)
    )
    assert served.status_code == 200
    assert served.content == raw

    binary = await api_client.get(f"{EDGE}/releases/binary/1.0.1", headers=agent_headers(rows))
    assert binary.status_code == 200
    assert binary.content == b"MZ\x00"

    for bad in ("..%2Fsecret", "1.0.1%2F..%2F..%2Fsecret", "1.0", "1.0.1-..", "..", "1.0.1.exe"):
        response = await api_client.get(
            f"{EDGE}/releases/binary/{bad}", headers=agent_headers(rows)
        )
        assert response.status_code == 404, bad

    unauth = await api_client.get(f"{EDGE}/releases/binary/1.0.1")
    assert unauth.status_code == 401

    download = await api_client.get(f"{EDGE}/download")
    assert download.status_code == 200
    assert download.content == b"MZ\x00"


async def test_download_without_release_is_404(
    api_client: httpx.AsyncClient, releases: Path
) -> None:
    del releases
    response = await api_client.get(f"{EDGE}/download")
    assert response.status_code == 404


# ===========================================================================
# 6. Panel: obyekt, sozlama, RBAC
# ===========================================================================


async def test_admin_creates_site_with_default_config_and_code(
    api_client: httpx.AsyncClient, two_markets: TwoMarketSeed, edge: EdgeDomainSeed
) -> None:
    headers = await admin_a(api_client, two_markets)
    created = await api_client.post(
        SITES, json={"kind": "livestock", "name": "Navoiy mol bozori"}, headers=headers
    )
    assert created.status_code == 201, created.text
    body = created.json()
    site_id = body["site"]["id"]
    assert site_id.startswith("livestock-")
    assert body["site"]["config_version"] == 1
    code = body["activation_code"]["code"]
    assert len(code) == 9
    assert code[4] == "-"
    assert not set(code.replace("-", "")) & set("01ILO")

    config = await api_client.get(f"{SITES}/{site_id}/config", headers=headers)
    doc = config.json()["doc"]
    assert doc["plugins"] == ["livestock", "parking"]
    assert [c["code"] for c in doc["livestock"]["categories"]][0] == "qoramol"
    assert doc["update"]["skip_weekdays"] == []

    bad = await api_client.put(
        f"{SITES}/{site_id}/config",
        json={"doc": {**doc, "update": {"channel": "beta", "auto": True}}},
        headers=headers,
    )
    assert bad.status_code == 422
    detail = bad.json()["detail"]
    assert detail["code"] == "config_invalid"
    assert detail["errors"][0]["path"] == "update.channel"
    assert "ruxsat etilgan" in detail["errors"][0]["message"]

    good = await api_client.put(
        f"{SITES}/{site_id}/config",
        json={"doc": {**doc, "config_version": 99, "devices": [{"id": "x"}]}},
        headers=headers,
    )
    assert good.status_code == 200, good.text
    assert good.json()["version"] == 2
    assert "devices" not in good.json()["doc"]

    listed = await api_client.get(SITES, headers=headers)
    ids = {item["id"] for item in listed.json()["items"]}
    assert {site_id, edge.market_a.site_id} <= ids
    assert edge.market_b.site_id not in ids
    seeded = next(i for i in listed.json()["items"] if i["id"] == edge.market_a.site_id)
    assert seeded["agent"]["online"] is True

    invalid_command = await api_client.post(
        f"{SITES}/{site_id}/commands", json={"type": "core.shell.exec"}, headers=headers
    )
    assert invalid_command.status_code == 422


async def test_other_market_admin_cannot_see_or_act(
    api_client: httpx.AsyncClient, two_markets: TwoMarketSeed, edge: EdgeDomainSeed
) -> None:
    headers = await admin_b(api_client, two_markets)
    site = edge.market_a.site_id
    assert (await api_client.get(f"{SITES}/{site}", headers=headers)).status_code == 404
    assert (await api_client.get(f"{SITES}/{site}/config", headers=headers)).status_code == 404
    command = await api_client.post(
        f"{SITES}/{site}/commands", json={"type": "core.config.refresh"}, headers=headers
    )
    assert command.status_code == 404
    code = await api_client.post(f"{SITES}/{site}/activation-codes", headers=headers)
    assert code.status_code == 404
    listed = await api_client.get(SITES, headers=headers)
    assert site not in json.dumps(listed.json())


async def test_cashier_is_forbidden_and_director_reads_only(
    api_client: httpx.AsyncClient, two_markets: TwoMarketSeed, edge: EdgeDomainSeed
) -> None:
    market = two_markets.market_a
    cashier = await session_headers(api_client, market.cashier_phone, SEED_PASSWORD)
    assert (await api_client.get(SITES, headers=cashier)).status_code == 403

    director = await session_headers(api_client, market.director_phone, SEED_PASSWORD)
    assert (await api_client.get(SITES, headers=director)).status_code == 200
    write = await api_client.post(
        f"{SITES}/{edge.market_a.site_id}/commands",
        json={"type": "core.config.refresh"},
        headers=director,
    )
    assert write.status_code == 403


async def test_site_setup_is_stored_and_passwords_are_rejected(
    api_client: httpx.AsyncClient, two_markets: TwoMarketSeed, edge: EdgeDomainSeed
) -> None:
    rows = edge.market_a
    device = {"id": "cam-kirish", "kind": "anpr_camera", "driver": "hik_isapi", "host": "10.0.0.5"}
    lane = {"id": "kirish-1", "direction": "in", "mode": "auto", "camera": "cam-kirish"}
    rejected = await api_client.put(
        f"{EDGE}/site-setup",
        json={"devices": [{**device, "password": "admin123"}], "lanes": []},
        headers=agent_headers(rows),
    )
    assert rejected.status_code == 422
    assert rejected.json()["detail"]["code"] == "setup_invalid"

    stored = await api_client.put(
        f"{EDGE}/site-setup",
        json={"devices": [device], "lanes": [lane]},
        headers=agent_headers(rows),
    )
    assert stored.status_code == 200, stored.text

    headers = await admin_a(api_client, two_markets)
    site = (await api_client.get(f"{SITES}/{rows.site_id}", headers=headers)).json()
    assert site["setup"] == {"devices": [device], "lanes": [lane]}

    polled = await api_client.get(
        f"{EDGE}/poll", params={"config_version": 0, "wait": 0}, headers=agent_headers(rows)
    )
    assert polled.json()["config"]["lanes"] == [lane]

    beat = await api_client.post(
        f"{EDGE}/heartbeat",
        json={
            "version": "1.0.2",
            "devices": [{"id": "cam-kirish", "status": "offline", "reason": "x"}],
        },
        headers=agent_headers(rows),
    )
    assert beat.status_code == 200
    site = (await api_client.get(f"{SITES}/{rows.site_id}", headers=headers)).json()
    assert site["agent"]["version"] == "1.0.2"
    assert site["agent"]["heartbeat"]["devices"][0]["status"] == "offline"
