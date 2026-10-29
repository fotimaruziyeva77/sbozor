"""Click Shop API (0035) va QR-kod sahifasi — to'liq yo'l HTTP orqali.

1. Prepare -> Complete -> `payments` (`method='click'`, kassirsiz) + kvitansiya;
   takror Complete `-4` (Click protokoli);
2. imzo xato `-1`, summa xato `-2` (qisman to'lov yo'q), rasta yo'q `-5`,
   kalit sozlanmagan — 503;
3. Click xato bilan Complete yuborsa — `-9`, tranzaksiya bekor;
4. Prepare va Complete orasida rasta boshqa yo'l bilan to'langan bo'lsa —
   `-4`, ikkinchi to'lov yozilmaydi;
5. QR-kod sahifasi summa va ikkala tugmani ko'rsatadi.
"""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING, Any

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
    from uuid import UUID

    import httpx
    from app.settings import Settings
    from fastapi import FastAPI
    from psycopg import Connection
    from psycopg.rows import TupleRow

pytestmark = pytest.mark.anyio

SECRET = "test-click-secret"
SERVICE_ID = "45678"
MERCHANT_ID = "12345"
SIGN_TIME = "2026-10-29 12:00:00"


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
            market_id = str(two_markets.market_a.id)
            sync_owner_conn.execute(
                "UPDATE markets SET is_active = false WHERE id = %s", (market_id,)
            )
            sync_owner_conn.execute(
                "DELETE FROM notification_outbox WHERE market_id = %s", (market_id,)
            )
            sync_owner_conn.execute(
                "DELETE FROM click_transactions WHERE market_id = %s", (market_id,)
            )
            sync_owner_conn.execute(
                "DELETE FROM payme_transactions WHERE market_id = %s", (market_id,)
            )
            sync_owner_conn.execute("DELETE FROM payments WHERE market_id = %s", (market_id,))
            sync_owner_conn.execute(
                "UPDATE markets SET is_active = true WHERE id = %s", (market_id,)
            )


@pytest.fixture
def click(api_app: FastAPI, test_settings: Settings, two_markets: TwoMarketSeed) -> Iterator[None]:
    original = api_app.state.settings
    api_app.state.settings = test_settings.model_copy(
        update={
            "click_secret_key": SecretStr(SECRET),
            "click_service_id": SERVICE_ID,
            "click_merchant_id": MERCHANT_ID,
            "click_market_id": str(two_markets.market_a.id),
            "payme_key": SecretStr("payme-key"),
            "payme_merchant_id": "65f0a0b1c2d3e4f5a6b7c8d9",
            "payme_market_id": str(two_markets.market_a.id),
        }
    )
    try:
        yield
    finally:
        api_app.state.settings = original


def _form(
    trans_id: int,
    code: str,
    amount: str,
    *,
    action: int,
    prepare_id: int | None = None,
    error: int = 0,
    secret: str = SECRET,
) -> dict[str, str]:
    parts = [str(trans_id), SERVICE_ID, secret, code]
    if prepare_id is not None:
        parts.append(str(prepare_id))
    parts += [amount, str(action), SIGN_TIME]
    form = {
        "click_trans_id": str(trans_id),
        "service_id": SERVICE_ID,
        "click_paydoc_id": str(trans_id + 1000),
        "merchant_trans_id": code,
        "amount": amount,
        "action": str(action),
        "error": str(error),
        "error_note": "Success" if error == 0 else "Error",
        "sign_time": SIGN_TIME,
        "sign_string": hashlib.md5("".join(parts).encode(), usedforsecurity=False).hexdigest(),
    }
    if prepare_id is not None:
        form["merchant_prepare_id"] = str(prepare_id)
    return form


async def _post(client: httpx.AsyncClient, step: str, form: dict[str, str]) -> dict[str, Any]:
    response = await client.post(f"/api/v1/click/{step}", data=form)
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


def _stall_code(conn: Connection[TupleRow], stall_id: UUID) -> str:
    row = conn.execute("SELECT code FROM stalls WHERE id = %s", (str(stall_id),)).fetchone()
    assert row is not None
    return str(row[0])


async def _due(client: httpx.AsyncClient, two_markets: TwoMarketSeed, code: str) -> int:
    headers = await session_headers(client, two_markets.market_a.cashier_phone, SEED_PASSWORD)
    response = await client.get(
        "/api/v1/billing/pending", params={"stall_code": code}, headers=headers
    )
    assert response.status_code == 200, response.text
    total = int(response.json()["total_due_soum"])
    assert total > 0, "nazorat: seed rastasida bugun to'lanadigan summa yo'q"
    return total


async def test_prepare_then_complete_writes_a_cashierless_click_payment(
    api_client: httpx.AsyncClient,
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    env: Any,
    click: None,
) -> None:
    code = _stall_code(sync_owner_conn, env.market_a.stall_with_two_occupied_slots)
    total = await _due(api_client, two_markets, code)
    amount = f"{total}.00"

    prepared = await _post(api_client, "prepare", _form(111, code, amount, action=0))
    assert prepared["error"] == 0, prepared
    prepare_id = prepared["merchant_prepare_id"]
    assert isinstance(prepare_id, int)

    again = await _post(api_client, "prepare", _form(111, code, amount, action=0))
    assert again["merchant_prepare_id"] == prepare_id, "takror Prepare o'sha ID ni qaytarsin"

    completed = await _post(
        api_client, "complete", _form(111, code, amount, action=1, prepare_id=prepare_id)
    )
    assert completed["error"] == 0, completed
    assert completed["merchant_confirm_id"] == prepare_id

    rows = sync_owner_conn.execute(
        "SELECT amount_soum, method, cashier_id, shift_id FROM payments "
        "WHERE market_id = %s AND idempotency_key = %s",
        (str(two_markets.market_a.id), "click:111"),
    ).fetchall()
    assert rows == [(total, "click", None, None)]

    receipts = sync_owner_conn.execute(
        "SELECT count(*) FROM notification_outbox "
        "WHERE market_id = %s AND kind = 'payment_receipt'",
        (str(two_markets.market_a.id),),
    ).fetchone()
    assert receipts is not None and receipts[0] == 1

    repeat = await _post(
        api_client, "complete", _form(111, code, amount, action=1, prepare_id=prepare_id)
    )
    assert repeat["error"] == -4, "takror Complete ikkinchi to'lov yozmasin"


async def test_sign_amount_stall_and_configuration_are_checked(
    api_client: httpx.AsyncClient,
    api_app: FastAPI,
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    env: Any,
    click: None,
) -> None:
    code = _stall_code(sync_owner_conn, env.market_a.stall_with_two_occupied_slots)
    total = await _due(api_client, two_markets, code)

    bad_sign = await _post(
        api_client, "prepare", _form(201, code, str(total), action=0, secret="wrong")
    )
    assert bad_sign["error"] == -1

    partial = await _post(api_client, "prepare", _form(202, code, str(total - 1000), action=0))
    assert partial["error"] == -2, "qisman to'lov rad etilishi kerak"

    unknown = await _post(api_client, "prepare", _form(203, "no-such", "1000", action=0))
    assert unknown["error"] == -5

    configured = api_app.state.settings
    api_app.state.settings = configured.model_copy(update={"click_secret_key": SecretStr("")})
    try:
        response = await api_client.post(
            "/api/v1/click/prepare", data=_form(204, code, str(total), action=0)
        )
        assert response.status_code == 503
    finally:
        api_app.state.settings = configured


async def test_click_error_on_complete_cancels_the_transaction(
    api_client: httpx.AsyncClient,
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    env: Any,
    click: None,
) -> None:
    code = _stall_code(sync_owner_conn, env.market_a.stall_with_two_occupied_slots)
    total = str(await _due(api_client, two_markets, code))
    prepare_id = (await _post(api_client, "prepare", _form(301, code, total, action=0)))[
        "merchant_prepare_id"
    ]

    failed = await _post(
        api_client,
        "complete",
        _form(301, code, total, action=1, prepare_id=prepare_id, error=-5017),
    )
    assert failed["error"] == -9

    again = await _post(
        api_client, "complete", _form(301, code, total, action=1, prepare_id=prepare_id)
    )
    assert again["error"] == -9
    count = sync_owner_conn.execute(
        "SELECT count(*) FROM payments WHERE market_id = %s", (str(two_markets.market_a.id),)
    ).fetchone()
    assert count is not None and count[0] == 0


async def test_stall_paid_between_prepare_and_complete_is_not_paid_twice(
    api_client: httpx.AsyncClient,
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    env: Any,
    click: None,
) -> None:
    code = _stall_code(sync_owner_conn, env.market_a.stall_with_two_occupied_slots)
    total = str(await _due(api_client, two_markets, code))
    first = (await _post(api_client, "prepare", _form(401, code, total, action=0)))[
        "merchant_prepare_id"
    ]
    second = (await _post(api_client, "prepare", _form(402, code, total, action=0)))[
        "merchant_prepare_id"
    ]

    ok = await _post(api_client, "complete", _form(401, code, total, action=1, prepare_id=first))
    assert ok["error"] == 0
    late = await _post(api_client, "complete", _form(402, code, total, action=1, prepare_id=second))
    assert late["error"] == -4, "rasta allaqachon to'langan — ikkinchi to'lov yozilmasin"

    count = sync_owner_conn.execute(
        "SELECT count(*) FROM payments WHERE market_id = %s", (str(two_markets.market_a.id),)
    ).fetchone()
    assert count is not None and count[0] == 1


async def test_qr_page_shows_the_amount_and_both_buttons(
    api_client: httpx.AsyncClient,
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    env: Any,
    click: None,
) -> None:
    code = _stall_code(sync_owner_conn, env.market_a.stall_with_two_occupied_slots)
    total = await _due(api_client, two_markets, code)

    page = await api_client.get(f"/api/v1/pay/{code}")
    assert page.status_code == 200, page.text
    assert f"{total:,}".replace(",", " ") in page.text
    assert "Payme bilan to&#x27;lash" in page.text or "Payme bilan to'lash" in page.text
    assert f"service_id={SERVICE_ID}" in page.text
    assert f"transaction_param={code}" in page.text

    missing = await api_client.get("/api/v1/pay/no-such")
    assert missing.status_code == 404
    assert "Rasta topilmadi" in missing.text
