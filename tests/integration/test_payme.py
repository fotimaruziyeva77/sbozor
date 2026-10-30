"""Payme Merchant API (0035) — to'liq yo'l HTTP orqali.

=============================================================================
O'lchanadigan da'volar:

  1. to'lov yo'li: Check -> Create -> Perform -> `payments` qatori
     (`method='payme'`, kassirsiz, smenasiz) + sotuvchiga kvitansiya niyati;
     takror Perform o'sha javobni beradi; Check/GetStatement holatni ko'rsatadi;
  2. summa — kassir kartasidagi «jami» bilan AYNI son; boshqa summa `-31001`;
  3. noto'g'ri kalit `-32504`, kalit sozlanmagan — 503 (fail-closed);
  4. bajarilgandan keyin bekor qilish — storno (`customer_refund`), holat -2;
  5. bir rasta bo'yicha ikkinchi kutilayotgan to'lov rad etiladi;
  6. QR-kod sahifasi Payme'ga to'g'ri summa bilan 302 qiladi.
=============================================================================
"""

from __future__ import annotations

import base64
import json
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from fixtures.admin_api import session_headers
from fixtures.billing_domain import billing_domain_before_day_close
from fixtures.market_domain import MarketDomainSeed
from fixtures.nvr_domain import nvr_rows
from fixtures.occupancy_domain import occupancy_rows
from fixtures.snapshot_domain import snapshot_rows
from fixtures.two_markets import SEED_PASSWORD, TwoMarketSeed
from pydantic import SecretStr

if TYPE_CHECKING:
    from collections.abc import Iterator

    import httpx
    from app.settings import Settings
    from fastapi import FastAPI
    from psycopg import Connection
    from psycopg.rows import TupleRow

pytestmark = pytest.mark.anyio

URL = "/api/v1/payme"
KEY = "test-payme-key"
MERCHANT = "65f0a0b1c2d3e4f5a6b7c8d9"
CHECKOUT = "https://test.paycom.uz"


@pytest.fixture
def env(
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    market_domain: MarketDomainSeed,
    migrated: None,
) -> Iterator[Any]:
    with (
        nvr_rows(sync_owner_conn, two_markets) as nvr,
        snapshot_rows(sync_owner_conn, nvr) as snaps,
        occupancy_rows(sync_owner_conn, two_markets, market_domain, snaps) as occupancy,
        billing_domain_before_day_close(
            sync_owner_conn, two_markets, market_domain, occupancy
        ) as billing,
    ):
        try:
            yield billing
        finally:
            # ⛔ To'lovlar o'zgarmas — o'chirish faqat qoralama (nofaol) bozorda.
            market_id = str(two_markets.market_a.id)
            sync_owner_conn.execute(
                "UPDATE markets SET is_active = false WHERE id = %s", (market_id,)
            )
            sync_owner_conn.execute(
                "DELETE FROM notification_outbox WHERE market_id = %s", (market_id,)
            )
            sync_owner_conn.execute(
                "DELETE FROM payme_transactions WHERE market_id = %s", (market_id,)
            )
            sync_owner_conn.execute("DELETE FROM payments WHERE market_id = %s", (market_id,))
            sync_owner_conn.execute(
                "UPDATE markets SET is_active = true WHERE id = %s", (market_id,)
            )


@pytest.fixture
def payme(api_app: FastAPI, test_settings: Settings, two_markets: TwoMarketSeed) -> Iterator[None]:
    """Payme sozlangan `Settings` — testdan keyin qaytariladi (sessiya sozlamasi tegilmaydi)."""
    original = api_app.state.settings
    api_app.state.settings = test_settings.model_copy(
        update={
            "payme_key": SecretStr(KEY),
            "payme_merchant_id": MERCHANT,
            "payme_market_id": str(two_markets.market_a.id),
            "payme_checkout_url": CHECKOUT,
        }
    )
    try:
        yield
    finally:
        api_app.state.settings = original


def _auth(key: str = KEY) -> dict[str, str]:
    token = base64.b64encode(f"Paycom:{key}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


async def _rpc(
    client: httpx.AsyncClient, method: str, params: dict[str, Any], key: str = KEY
) -> dict[str, Any]:
    response = await client.post(
        URL,
        json={"jsonrpc": "2.0", "id": 7, "method": method, "params": params},
        headers=_auth(key),
    )
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    assert body["id"] == 7
    return body


def _stall_code(conn: Connection[TupleRow], stall_id: UUID) -> str:
    row = conn.execute("SELECT code FROM stalls WHERE id = %s", (str(stall_id),)).fetchone()
    assert row is not None
    return str(row[0])


async def _due(client: httpx.AsyncClient, two_markets: TwoMarketSeed, code: str) -> int:
    """Kassir kartasidagi «jami» — Payme summasining YAGONA manbai."""
    headers = await session_headers(client, two_markets.market_a.cashier_phone, SEED_PASSWORD)
    response = await client.get(
        "/api/v1/billing/pending", params={"stall_code": code}, headers=headers
    )
    assert response.status_code == 200, response.text
    total = int(response.json()["total_due_soum"])
    assert total > 0, "nazorat: seed rastasida bugun to'lanadigan summa yo'q"
    return total


async def test_full_payment_flow_writes_a_cashierless_payment_and_a_receipt(
    api_client: httpx.AsyncClient,
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    env: Any,
    payme: None,
) -> None:
    code = _stall_code(sync_owner_conn, env.market_a.stall_with_two_occupied_slots)
    total = await _due(api_client, two_markets, code)
    params = {"amount": total * 100, "account": {"rasta": code}}

    check = await _rpc(api_client, "CheckPerformTransaction", params)
    assert check["result"]["allow"] is True

    created = await _rpc(
        api_client, "CreateTransaction", {**params, "id": "pay-1", "time": 1_700_000_000_000}
    )
    assert created["result"]["state"] == 1
    again = await _rpc(
        api_client, "CreateTransaction", {**params, "id": "pay-1", "time": 1_700_000_000_000}
    )
    assert again["result"] == created["result"], (
        "takror Create o'sha tranzaksiyani qaytarishi kerak"
    )

    performed = await _rpc(api_client, "PerformTransaction", {"id": "pay-1"})
    assert performed["result"]["state"] == 2
    repeat = await _rpc(api_client, "PerformTransaction", {"id": "pay-1"})
    assert repeat["result"] == performed["result"], "takror Perform ikkinchi to'lov yozmasin"

    rows = sync_owner_conn.execute(
        "SELECT amount_soum, method, cashier_id, shift_id, kind FROM payments "
        "WHERE market_id = %s AND idempotency_key = %s",
        (str(two_markets.market_a.id), "payme:pay-1"),
    ).fetchall()
    assert rows == [(total, "payme", None, None, "payment")]

    receipts = sync_owner_conn.execute(
        "SELECT count(*) FROM notification_outbox "
        "WHERE market_id = %s AND kind = 'payment_receipt'",
        (str(two_markets.market_a.id),),
    ).fetchone()
    assert receipts is not None and receipts[0] == 1, "sotuvchiga kvitansiya niyati yozilmadi"

    status_ = await _rpc(api_client, "CheckTransaction", {"id": "pay-1"})
    assert status_["result"]["state"] == 2
    assert status_["result"]["perform_time"] == performed["result"]["perform_time"]

    statement = await _rpc(
        api_client, "GetStatement", {"from": 1_699_999_999_000, "to": 1_700_000_001_000}
    )
    [item] = statement["result"]["transactions"]
    assert item["id"] == "pay-1"
    assert item["amount"] == total * 100
    assert item["account"] == {"rasta": code}

    # To'lovdan keyin shu summa endi qarz emas — yana Check rad etiladi.
    after = await _rpc(api_client, "CheckPerformTransaction", params)
    assert "error" in after


async def test_wrong_amount_and_unknown_stall_are_rejected(
    api_client: httpx.AsyncClient,
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    env: Any,
    payme: None,
) -> None:
    code = _stall_code(sync_owner_conn, env.market_a.stall_with_two_occupied_slots)
    total = await _due(api_client, two_markets, code)

    partial = await _rpc(
        api_client,
        "CheckPerformTransaction",
        {"amount": (total - 1_000) * 100, "account": {"rasta": code}},
    )
    assert partial["error"]["code"] == -31001, "qisman to'lov rad etilishi kerak"

    unknown = await _rpc(
        api_client, "CheckPerformTransaction", {"amount": 100_000, "account": {"rasta": "no-such"}}
    )
    assert unknown["error"]["code"] == -31050
    assert unknown["error"]["data"] == "rasta"


async def test_wrong_key_is_rejected_and_missing_key_closes_the_surface(
    api_client: httpx.AsyncClient,
    api_app: FastAPI,
    env: Any,
    payme: None,
) -> None:
    rejected = await _rpc(api_client, "CheckTransaction", {"id": "x"}, key="not-the-key")
    assert rejected["error"]["code"] == -32504

    configured = api_app.state.settings
    api_app.state.settings = configured.model_copy(update={"payme_key": SecretStr("")})
    try:
        response = await api_client.post(
            URL, json={"id": 1, "method": "CheckTransaction", "params": {}}, headers=_auth()
        )
        assert response.status_code == 503
    finally:
        api_app.state.settings = configured


async def test_cancel_after_perform_writes_a_reversal(
    api_client: httpx.AsyncClient,
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    env: Any,
    payme: None,
) -> None:
    code = _stall_code(sync_owner_conn, env.market_a.stall_with_two_occupied_slots)
    total = await _due(api_client, two_markets, code)
    params = {"amount": total * 100, "account": {"rasta": code}}
    await _rpc(api_client, "CreateTransaction", {**params, "id": "pay-2", "time": 1})
    await _rpc(api_client, "PerformTransaction", {"id": "pay-2"})

    cancelled = await _rpc(api_client, "CancelTransaction", {"id": "pay-2", "reason": 5})
    assert cancelled["result"]["state"] == -2

    kinds = sync_owner_conn.execute(
        "SELECT kind, reversal_reason, method FROM payments "
        "WHERE market_id = %s ORDER BY created_at",
        (str(two_markets.market_a.id),),
    ).fetchall()
    assert kinds == [("payment", None, "payme"), ("reversal", "customer_refund", "payme")]

    again = await _rpc(api_client, "CancelTransaction", {"id": "pay-2", "reason": 5})
    assert again["result"] == cancelled["result"], "takror bekor qilish ikkinchi storno yozmasin"


async def test_a_second_pending_payment_for_the_same_stall_is_refused(
    api_client: httpx.AsyncClient,
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    env: Any,
    payme: None,
) -> None:
    code = _stall_code(sync_owner_conn, env.market_a.stall_with_two_occupied_slots)
    total = await _due(api_client, two_markets, code)
    params = {"amount": total * 100, "account": {"rasta": code}}
    await _rpc(api_client, "CreateTransaction", {**params, "id": "pay-3", "time": 1})

    second = await _rpc(api_client, "CreateTransaction", {**params, "id": "pay-4", "time": 2})
    assert second["error"]["code"] == -31053

    # Birinchisi bekor qilinsa, rasta yana bo'shaydi.
    await _rpc(api_client, "CancelTransaction", {"id": "pay-3", "reason": 3})
    freed = await _rpc(api_client, "CheckPerformTransaction", params)
    assert freed["result"]["allow"] is True


async def test_qr_page_redirects_to_payme_with_the_due_amount(
    api_client: httpx.AsyncClient,
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    env: Any,
    payme: None,
) -> None:
    code = _stall_code(sync_owner_conn, env.market_a.stall_with_two_occupied_slots)
    total = await _due(api_client, two_markets, code)

    response = await api_client.get(f"{URL}/pay/{code}")
    assert response.status_code == 302, response.text
    location = response.headers["location"]
    assert location.startswith(f"{CHECKOUT}/")
    decoded = base64.b64decode(location.rsplit("/", 1)[1]).decode()
    assert decoded == f"m={MERCHANT};ac.rasta={code};a={total * 100};l=uz"

    missing = await api_client.get(f"{URL}/pay/no-such")
    assert missing.status_code == 404
    assert "Rasta topilmadi" in missing.text


async def test_each_market_kassa_resolves_its_own_market(
    api_app: FastAPI,
    api_client: httpx.AsyncClient,
    test_settings: Settings,
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    env: Any,
) -> None:
    """261030: har bozor alohida yuridik shaxs — bozor KALITDAN aniqlanadi.

    A bozorining rastasi B kassasining kaliti bilan so'ralsa, B bozorida
    qidiriladi va topilmaydi: pul hech qachon boshqa bozor hisobiga ketmaydi.
    """
    code = _stall_code(sync_owner_conn, env.market_a.stall_with_two_occupied_slots)
    in_b = sync_owner_conn.execute(
        "SELECT count(*) FROM stalls WHERE market_id = %s AND code = %s",
        (str(two_markets.market_b.id), code),
    ).fetchone()
    assert in_b is not None and in_b[0] == 0, "nazorat: rasta kodi B bozorida bo'lmasin"
    total = await _due(api_client, two_markets, code)

    original = api_app.state.settings
    api_app.state.settings = test_settings.model_copy(
        update={
            "payme_merchants": SecretStr(
                json.dumps(
                    [
                        {
                            "slug": "bozor-a",
                            "market_id": str(two_markets.market_a.id),
                            "merchant_id": MERCHANT,
                            "key": "key-a",
                        },
                        {
                            "slug": "bozor-b",
                            "market_id": str(two_markets.market_b.id),
                            "merchant_id": "m-b",
                            "key": "key-b",
                        },
                    ]
                )
            ),
            "payme_checkout_url": CHECKOUT,
        }
    )
    try:
        params = {"amount": total * 100, "account": {"rasta": code}}
        own = await _rpc(api_client, "CheckPerformTransaction", params, key="key-a")
        assert own["result"]["allow"] is True
        # Kassada maydon `rasta_id` deb nomlangan bo'lsa ham (Karmana, 261030).
        by_id = {"amount": total * 100, "account": {"rasta_id": code}}
        assert (await _rpc(api_client, "CheckPerformTransaction", by_id, key="key-a"))["result"][
            "allow"
        ] is True
        foreign = await _rpc(api_client, "CheckPerformTransaction", params, key="key-b")
        assert foreign["error"]["code"] == -31050, foreign
        assert foreign["error"]["data"] == "rasta", "xato maydon nomi kassaning maydonidan"
        unknown = await _rpc(api_client, "CheckPerformTransaction", params, key="key-x")
        assert unknown["error"]["code"] == -32504

        page = await api_client.get(f"/api/v1/pay/bozor-a/{code}")
        assert page.status_code == 200, page.text
        assert f"{total:,}".replace(",", " ") in page.text
        assert (await api_client.get(f"/api/v1/pay/bozor-b/{code}")).status_code == 404
        assert (await api_client.get(f"/api/v1/pay/yoq-bozor/{code}")).status_code == 503
    finally:
        api_app.state.settings = original
