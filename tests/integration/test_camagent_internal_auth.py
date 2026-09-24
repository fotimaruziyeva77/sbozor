"""`/internal/camagent/snapshot` — SERVIS TOKENI VA TENANT CHEGARASI (2026-09-24).

=============================================================================
⛔⛔ NEGA BU FAYL BOR.

Marshrut CamAgent gateway uchun qo'shilgan edi, lekin cross-tenant
matritsasi (`tests/tenancy/test_cross_tenant.py`) uni oddiy foydalanuvchi
marshruti deb oldi va uchala token da'vosida 401 kutdi. Marshrut esa
SERVIS yuzasi: unda foydalanuvchi access tokeni umuman bo'lmaydi va
sozlanmagan token holatida kontrakt 503 — ya'ni matritsa uch marta
qizarib turdi va marshrutning HAQIQIY kontrakti hech qayerda
o'lchanmagan edi.

Endi marshrut matritsadan SABAB bilan chiqarilgan (`EXEMPT_ROUTES`,
`/internal/bot/*` bilan ayni naqsh) va uning o'z kontrakti shu yerda:

  * sozlanmagan token -> 503 (fail-closed, «hammaga ochiq» EMAS);
  * tokensiz va noto'g'ri token -> 401, BAYT-BAYT ayni javob;
  * begona bozorning kamerasi -> 404 — bozor tanadagi `market_id` dan
    keladi va kamera O'SHA bozor ichida qidiriladi (musbat nazorat bilan);
  * yo'l OpenAPI'da YO'Q, router sessiya primitivlarini ishlatmaydi.
=============================================================================
"""

from __future__ import annotations

import ast
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from fixtures.nvr_domain import nvr_rows
from pydantic import SecretStr

if TYPE_CHECKING:
    from collections.abc import Iterator

    import httpx
    from app.settings import Settings
    from fastapi import FastAPI
    from fixtures.nvr_domain import MarketNvrRows, NvrDomainSeed
    from fixtures.two_markets import TwoMarketSeed
    from psycopg import Connection
    from psycopg.rows import TupleRow

pytestmark = pytest.mark.usefixtures("migrated")

SNAPSHOT_URL = "/internal/camagent/snapshot"

SERVICE_TOKEN = "test-camagent-service-token-not-a-real-secret"  # noqa: S105 - test uskunasi

CAMAGENT_ROUTER_SOURCE = (
    Path(__file__).resolve().parents[2]
    / "services"
    / "core-api"
    / "app"
    / "api"
    / "internal"
    / "camagent.py"
)


@pytest.fixture
def camagent_token(api_app: FastAPI, test_settings: Settings) -> Iterator[str]:
    """`camagent_service_token` O'RNATILGAN `Settings` — TESTDAN KEYIN QAYTARILADI.

    ⚠ `test_settings` SESSIYA doirasida: uni joyida o'zgartirish tokenni
      butun to'plamga tarqatardi va «sozlanmagan -> 503» testi jimgina
      ma'nosini yo'qotardi (`test_bot_internal_api.bot_token` bilan ayni sabab).
    """
    original = api_app.state.settings
    api_app.state.settings = test_settings.model_copy(
        update={"camagent_service_token": SecretStr(SERVICE_TOKEN)}
    )
    try:
        yield SERVICE_TOKEN
    finally:
        api_app.state.settings = original


@pytest.fixture
def nvr(
    sync_owner_conn: Connection[TupleRow], two_markets: TwoMarketSeed
) -> Iterator[NvrDomainSeed]:
    with nvr_rows(sync_owner_conn, two_markets) as seed:
        yield seed


def _serial(rows: MarketNvrRows) -> str:
    """Seed NVR'ining seriya raqami — `fixtures/nvr_domain.py` dagi AYNI qoida."""
    return f"SEED{rows.nvr_id.hex[:12].upper()}"


def _payload(*, market_id: str, serial: str, channel: int) -> dict[str, Any]:
    now = datetime.now(tz=UTC).isoformat()
    return {
        "market_id": market_id,
        "camera_serial": serial,
        "channel_no": channel,
        "object_key": "camagent/test/yoq-obyekt.jpg",
        "size_bytes": 1,
        "captured_at": now,
        "scheduled_at": now,
    }


def _any_payload(two_markets: TwoMarketSeed) -> dict[str, Any]:
    return _payload(market_id=str(two_markets.market_a.id), serial="YOQ", channel=1)


async def test_an_unconfigured_token_closes_the_surface_completely(
    api_client: httpx.AsyncClient, two_markets: TwoMarketSeed
) -> None:
    """⛔ FAIL-CLOSED: sozlanmagan token `503` beradi, «hammaga ochiq» EMAS.

    ⚠ `camagent_token` fixture'i ATAYIN SO'RALMAYDI — `test_settings` ning
      standart holati aynan shu: token bo'sh.
    """
    response = await api_client.post(SNAPSHOT_URL, json=_any_payload(two_markets))

    assert response.status_code == 503
    assert response.json() == {"detail": "unavailable"}


async def test_a_missing_and_a_wrong_token_are_rejected_identically(
    api_client: httpx.AsyncClient, camagent_token: str, two_markets: TwoMarketSeed
) -> None:
    """⛔ «Token yo'q» va «token noto'g'ri» — 401 va BAYT-BAYT ayni javob.

    Ajratish hujumchiga «sarlavha shakli to'g'ri edi» degan foydali signal
    berardi.
    """
    assert camagent_token  # token SOZLANGAN — ya'ni 503 emas, 401 o'lchanadi

    missing = await api_client.post(SNAPSHOT_URL, json=_any_payload(two_markets))
    wrong = await api_client.post(
        SNAPSHOT_URL,
        json=_any_payload(two_markets),
        headers={"Authorization": "Bearer butunlay-boshqa-token"},
    )

    assert missing.status_code == wrong.status_code == 401
    assert missing.json() == wrong.json() == {"detail": "unauthorized"}
    assert "set-cookie" not in {name.lower() for name in missing.headers}


async def test_another_markets_camera_is_not_found(
    api_client: httpx.AsyncClient,
    camagent_token: str,
    two_markets: TwoMarketSeed,
    nvr: NvrDomainSeed,
) -> None:
    """⛔ TENANT CHEGARASI: A bozori nomidan B ning kamerasi — 404.

    Bozor tanadagi `market_id` dan keladi va kamera O'SHA bozor ichida
    (RLS + oshkora `market_id` filtri) seriya + kanal bo'yicha qidiriladi.

    ⚠ MUSBAT NAZORAT: AYNI seriya/kanal B bozori nomidan yuborilganda
      kamera TOPILADI va so'rov keyingi qadamga — S3 dan kadrni o'qishga —
      o'tadi (obyekt yo'q -> 502). Usiz 404 «seriya noto'g'ri yozilgan»
      degani ham bo'lishi mumkin edi va test tenant chegarasini emas,
      o'zining xatosini o'lchardi.
    """
    headers = {"Authorization": f"Bearer {camagent_token}"}
    serial = _serial(nvr.market_b)
    channel = nvr.market_b.camera_channels[0]

    foreign = await api_client.post(
        SNAPSHOT_URL,
        json=_payload(market_id=str(two_markets.market_a.id), serial=serial, channel=channel),
        headers=headers,
    )
    own = await api_client.post(
        SNAPSHOT_URL,
        json=_payload(market_id=str(two_markets.market_b.id), serial=serial, channel=channel),
        headers=headers,
    )

    assert foreign.status_code == 404, foreign.text
    assert foreign.json() == {"detail": "camera_not_found"}
    assert own.status_code == 502, own.text
    assert own.json() == {"detail": "object_unreadable"}


def test_the_route_is_not_in_the_public_schema(api_app: FastAPI) -> None:
    """Servis yuzasi OpenAPI'da YO'Q — ommaviy hujjatda kirish nuqtasi ochilmaydi."""
    assert SNAPSHOT_URL not in api_app.openapi()["paths"]


def test_the_router_creates_no_session_primitives() -> None:
    """⛔ GREP DARVOZASI — router foydalanuvchi sessiyasi tug'dirmaydi.

    So'rovchi ODAM emas, SERVIS: `Principal`, token chiqarish yoki cookie
    bu faylda paydo bo'lsa, u ikkinchi sessiya modeli bo'lardi.
    """
    source = CAMAGENT_ROUTER_SOURCE.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(CAMAGENT_ROUTER_SOURCE))
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)} | {
        node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)
    }

    forbidden = names & {
        "create_access_token",
        "encode_access",
        "issue_refresh",
        "issue_live_token",
        "Principal",
        "set_cookie",
        "require_permission",
    }
    assert forbidden == set(), forbidden
