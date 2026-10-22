"""Rastaning mahsulot turi va maydoni (0031) — API va sxema xulqi.

=============================================================================
NEGA BU FAYL BOR (foydalanuvchi talabi, 261022).

Navoiy viloyati hokimining 131-5-0-Q/25-son qarori joy haqini mahsulot turi
va joy o'lchami bo'yicha belgilaydi. Rasta reestriga ikki IXTIYORIY maydon
qo'shildi: `product_type` (qaror 1-ilovasining mahsulot qatorlari) va
`area_m2` (m², ikki kasr xonasi bilan).

Uch narsa qulflanadi:
  1. maydonlar yaratish/tahrir/o'qish yo'llaridan TO'LIQ o'tadi;
  2. `PATCH` semantikasi — berilmagan maydon tegilmaydi, `null` tozalaydi;
  3. noto'g'ri qiymat chegarada (422) VA sxemada (CHECK) rad etiladi —
     xom SQL yo'li ham qamralgan.

⚠ PULGA TA'SIR YO'Q: tarif hamon toifa → tarif zanjiridan keladi. Shuning
  uchun bu yerda `tariff_soum` o'zgarmasligi ham tekshiriladi.
=============================================================================
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import psycopg.errors
import pytest
from fixtures.admin_api import STALLS_URL, session_headers

if TYPE_CHECKING:
    import httpx
    from fixtures import MarketDomainSeed, MarketScope
    from fixtures.two_markets import TwoMarketSeed

NEW_CODE = "9101"
"""Seed'da uchramaydigan rasta raqami (`test_stall_registry.NEW_CODE` dan farqli)."""


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


async def test_new_stall_keeps_product_type_and_area(
    api_client: httpx.AsyncClient,
    market_domain: MarketDomainSeed,
    admin_headers: dict[str, str],
) -> None:
    """Yaratishda berilgan tur va maydon kartochkada ham, ro'yxatda ham qaytadi."""
    created = await api_client.post(
        STALLS_URL,
        json=_create_payload(market_domain, product_type="vegetables", area_m2=3.6),
        headers=admin_headers,
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["product_type"] == "vegetables"
    assert body["area_m2"] == 3.6

    listed = await api_client.get(STALLS_URL, params={"q": NEW_CODE}, headers=admin_headers)
    assert listed.status_code == 200, listed.text
    [item] = [row for row in listed.json()["items"] if row["code"] == NEW_CODE]
    assert item["product_type"] == "vegetables"
    assert item["area_m2"] == 3.6


async def test_stall_without_product_type_and_area_reports_null(
    api_client: httpx.AsyncClient,
    market_domain: MarketDomainSeed,
    admin_headers: dict[str, str],
) -> None:
    """Kiritilmagan — `null`, `0` yoki bo'sh satr EMAS (mavjud rastalar shu holatda)."""
    stall_id = market_domain.market_a.unassigned_stall_id
    response = await api_client.get(f"{STALLS_URL}/{stall_id}", headers=admin_headers)
    assert response.status_code == 200, response.text
    assert response.json()["product_type"] is None
    assert response.json()["area_m2"] is None


async def test_patch_sets_then_clears_only_what_was_sent(
    api_client: httpx.AsyncClient,
    market_domain: MarketDomainSeed,
    admin_headers: dict[str, str],
) -> None:
    """`PATCH` — berilmagan maydon TEGILMAYDI, `null` esa aynan o'shani tozalaydi.

    Tarif o'zgarmaydi: mahsulot turi pul emas, solishtirish uchun ma'lumot.
    """
    stall_id = market_domain.market_a.unassigned_stall_id
    url = f"{STALLS_URL}/{stall_id}"
    before = (await api_client.get(url, headers=admin_headers)).json()

    set_both = await api_client.patch(
        url, json={"product_type": "imported_fruit", "area_m2": 12.5}, headers=admin_headers
    )
    assert set_both.status_code == 200, set_both.text
    assert set_both.json()["product_type"] == "imported_fruit"
    assert set_both.json()["area_m2"] == 12.5
    assert set_both.json()["tariff_soum"] == before["tariff_soum"]

    clear_area = await api_client.patch(url, json={"area_m2": None}, headers=admin_headers)
    assert clear_area.status_code == 200, clear_area.text
    assert clear_area.json()["area_m2"] is None
    assert clear_area.json()["product_type"] == "imported_fruit"


@pytest.mark.parametrize(
    "payload",
    [
        {"product_type": "bananas"},
        {"area_m2": 0},
        {"area_m2": -1},
        {"area_m2": 3.666},
        {"area_m2": 10000},
    ],
    ids=["unknown-type", "zero-area", "negative-area", "three-decimals", "too-large"],
)
async def test_invalid_product_type_or_area_returns_422(
    api_client: httpx.AsyncClient,
    market_domain: MarketDomainSeed,
    admin_headers: dict[str, str],
    payload: dict[str, Any],
) -> None:
    """Chegarada rad etiladi — DB'da jimgina yaxlitlanmaydi va CHECK'gacha yetmaydi."""
    stall_id = market_domain.market_a.unassigned_stall_id
    response = await api_client.patch(
        f"{STALLS_URL}/{stall_id}", json=payload, headers=admin_headers
    )
    assert response.status_code == 422, response.text


@pytest.mark.parametrize(
    ("column", "value", "error"),
    [
        ("product_type", "bananas", psycopg.errors.CheckViolation),
        ("area_m2", 0, psycopg.errors.CheckViolation),
        # ⚠ 10 000 CHECK'gacha yetmaydi: `NUMERIC(6,2)` ning o'zi uni sig'dirmaydi.
        ("area_m2", 10000, psycopg.errors.NumericValueOutOfRange),
    ],
)
async def test_db_rejects_bad_values_on_raw_sql(
    two_markets: TwoMarketSeed,
    market_domain: MarketDomainSeed,
    market_scope: MarketScope,
    column: str,
    value: object,
    error: type[Exception],
) -> None:
    """Xom SQL yo'li ham qamralgan: ilova validatsiyasini chetlab o'tgan yozuv
    `ck_stalls_product_type_allowed` / `ck_stalls_area_m2_range` yoki ustun
    turining o'zida to'xtaydi."""
    stall_id = market_domain.market_a.unassigned_stall_id
    with (
        market_scope(two_markets.market_a.id) as conn,
        pytest.raises(error),
    ):
        conn.execute(
            f"UPDATE stalls SET {column} = %s WHERE id = %s",  # noqa: S608 - ustun nomi parametrdan, ro'yxat yuqorida qotirilgan
            (value, str(stall_id)),
        )
