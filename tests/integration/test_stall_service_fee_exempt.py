"""Rastaning «tarozi olinmaydi» belgisi (0032) — API va sxema xulqi.

=============================================================================
NEGA BU FAYL BOR (foydalanuvchi talabi, 261022).

Karmanadagi 5-rastada ko'kat sotiladi va undan tarozi puli olinmaydi.
Rastaga `service_fee_exempt` belgisi qo'shildi; uning PULDAGI ta'siri
(tarozini kim ko'taradi) `test_service_fee_and_roster.py` ning 5-bo'limida
o'lchanadi. Bu yerda — belgining o'zi:

  1. standart `false` — mavjud rastalarda tarozi avvalgidek olinadi;
  2. yaratish/tahrir/o'qish yo'llaridan TO'LIQ o'tadi;
  3. `PATCH` semantikasi — berilmasa tegilmaydi, `null` 422 (ustun `NOT NULL`);
  4. belgi TARIFGA tegmaydi.
=============================================================================
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from fixtures.admin_api import STALLS_URL, session_headers

if TYPE_CHECKING:
    import httpx
    from fixtures import MarketDomainSeed
    from fixtures.two_markets import TwoMarketSeed

NEW_CODE = "9102"
"""Seed'da uchramaydigan rasta raqami (`test_stall_product_area.NEW_CODE` dan farqli)."""


@pytest.fixture
async def admin_headers(
    api_client: httpx.AsyncClient,
    two_markets: TwoMarketSeed,
    market_domain: MarketDomainSeed,
) -> dict[str, str]:
    """A bozori adminining sessiyasi (`STALL_MANAGE`)."""
    market_a = two_markets.market_a
    return await session_headers(api_client, market_a.admin_phone, market_a.admin_password)


def _create_payload(domain: MarketDomainSeed, **extra: Any) -> dict[str, Any]:
    market_a = domain.market_a
    return {
        "code": NEW_CODE,
        "zone_id": str(market_a.zone_ids[0]),
        "category_id": str(market_a.category_ids[0]),
        **extra,
    }


async def test_existing_stall_still_pays_the_fee_by_default(
    api_client: httpx.AsyncClient,
    market_domain: MarketDomainSeed,
    admin_headers: dict[str, str],
) -> None:
    """Migratsiya hech bir rastaning pulini o'zgartirmaydi — standart `false`."""
    stall_id = market_domain.market_a.unassigned_stall_id
    response = await api_client.get(f"{STALLS_URL}/{stall_id}", headers=admin_headers)
    assert response.status_code == 200, response.text
    assert response.json()["service_fee_exempt"] is False


async def test_new_stall_keeps_the_flag_in_detail_and_list(
    api_client: httpx.AsyncClient,
    market_domain: MarketDomainSeed,
    admin_headers: dict[str, str],
) -> None:
    """Yaratishda berilgan belgi kartochkada ham, ro'yxatda ham qaytadi."""
    created = await api_client.post(
        STALLS_URL,
        json=_create_payload(market_domain, product_type="greens", service_fee_exempt=True),
        headers=admin_headers,
    )
    assert created.status_code == 201, created.text
    assert created.json()["service_fee_exempt"] is True

    listed = await api_client.get(STALLS_URL, params={"q": NEW_CODE}, headers=admin_headers)
    assert listed.status_code == 200, listed.text
    [item] = [row for row in listed.json()["items"] if row["code"] == NEW_CODE]
    assert item["service_fee_exempt"] is True


async def test_patch_sets_and_clears_the_flag_without_touching_the_rest(
    api_client: httpx.AsyncClient,
    market_domain: MarketDomainSeed,
    admin_headers: dict[str, str],
) -> None:
    """Belgi qo'yiladi va olinadi; boshqa `PATCH` uni tozalamaydi; tarif o'zgarmaydi."""
    stall_id = market_domain.market_a.unassigned_stall_id
    url = f"{STALLS_URL}/{stall_id}"
    before = (await api_client.get(url, headers=admin_headers)).json()

    on = await api_client.patch(url, json={"service_fee_exempt": True}, headers=admin_headers)
    assert on.status_code == 200, on.text
    assert on.json()["service_fee_exempt"] is True
    assert on.json()["tariff_soum"] == before["tariff_soum"], "belgi tarifga tegdi"

    # Belgi berilmagan PATCH uni o'chirib yubormaydi (`exclude_unset`).
    other = await api_client.patch(url, json={"note": "ko'kat"}, headers=admin_headers)
    assert other.status_code == 200, other.text
    assert other.json()["service_fee_exempt"] is True

    off = await api_client.patch(url, json={"service_fee_exempt": False}, headers=admin_headers)
    assert off.status_code == 200, off.text
    assert off.json()["service_fee_exempt"] is False


@pytest.mark.parametrize("value", [None, "maybe"], ids=["null", "not-a-bool"])
async def test_invalid_flag_returns_422(
    api_client: httpx.AsyncClient,
    market_domain: MarketDomainSeed,
    admin_headers: dict[str, str],
    value: object,
) -> None:
    """`null` 422 — 500 EMAS: ustun `NOT NULL` va xato chegarada to'xtashi kerak."""
    stall_id = market_domain.market_a.unassigned_stall_id
    response = await api_client.patch(
        f"{STALLS_URL}/{stall_id}", json={"service_fee_exempt": value}, headers=admin_headers
    )
    assert response.status_code == 422, response.text
