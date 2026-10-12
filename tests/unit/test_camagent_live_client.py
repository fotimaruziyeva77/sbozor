"""Gateway'ning oqim rad javobini o'qish — «agent aloqada emas» (261011).

=============================================================================
⛔⛔ NEGA BU TEST BOR — PROD'DA O'LCHANGAN.

    Karmanada bozor kompyuteri 11:32 da o'chgan, kechqurun esa «Ko'rish»
    38 marta bosilgan. Gateway endi bunday holatda KUTMASDAN javob beradi:
    `{"agent_offline": true, "last_seen": <epoch>}`. Bu yerda o'sha javob
    `CamAgentLiveError` ning maydonlariga AYNAN o'tishi o'lchanadi — aks
    holda UI yana umumiy «jonli ko'rish ishlamayapti» ni ko'rsatardi.

⚠ `respx` — haqiqiy gateway kerak emas: bu fayl JAVOBNI O'QISHNI o'lchaydi.
=============================================================================
"""

from __future__ import annotations

from uuid import UUID

import httpx
import pytest
import respx
from app.services.camagent_live import CamAgentLiveError, open_stream

_BASE = "http://camagent-gateway:8787"
_MARKET = UUID("01a01f40-69e4-7c73-9096-c3b93c053403")


async def _rad(javob: httpx.Response) -> CamAgentLiveError:
    with respx.mock(assert_all_called=True) as mock:
        mock.post(f"{_BASE}/internal/stream/start").mock(return_value=javob)
        with pytest.raises(CamAgentLiveError) as caught:
            await open_stream(
                _BASE,
                "sir",
                market_id=_MARKET,
                camera_serial="DS-2CD1043G2-I2025",
                channel_no=1,
                viewer="sbozor:u-1",
            )
    return caught.value


async def test_offline_agent_is_flagged_with_its_last_heartbeat() -> None:
    xato = await _rad(
        httpx.Response(
            503,
            json={"error": "agent aloqada emas", "agent_offline": True, "last_seen": 1760160720.0},
        )
    )

    assert xato.agent_offline is True
    assert xato.last_seen == 1760160720.0
    assert xato.agent_reason is None


async def test_a_stream_failure_is_not_mistaken_for_an_offline_agent() -> None:
    """NAZORAT: oddiy oqim xatosi «kompyuter o'chiq» bo'lib ko'rinmasligi kerak."""
    xato = await _rad(
        httpx.Response(
            503,
            json={"error": "oqim hali tayyor emas", "agent_reason": "ffmpeg: Connection refused"},
        )
    )

    assert xato.agent_offline is False
    assert xato.last_seen is None
    assert xato.agent_reason == "ffmpeg: Connection refused"


@pytest.mark.parametrize("vaqt", ["11:32", None, True, [1]])
async def test_a_non_numeric_last_seen_is_unknown_not_guessed(vaqt: object) -> None:
    """Vaqt faqat SON bo'lsa qabul qilinadi — boshqa narsa `None`, taxmin emas.

    ⚠ `True` ham rad etiladi: Python'da `bool` — `int` ning bolasi, ya'ni
      tekshiruvsiz u «1970-01-01 00:00:01» bo'lib ekranga chiqardi.
    """
    xato = await _rad(httpx.Response(503, json={"agent_offline": True, "last_seen": vaqt}))

    assert xato.agent_offline is True
    assert xato.last_seen is None


@pytest.mark.parametrize("epoch", [float("inf"), 1e20])
def test_an_absurd_last_seen_does_not_turn_the_answer_into_a_500(epoch: float) -> None:
    """Gateway yaroqsiz vaqt bersa ham javob «kompyuter o'chiq» bo'lib qoladi."""
    from app.api.v1.cameras import LiveUnavailable

    xato = LiveUnavailable(agent_offline=True, agent_last_seen=epoch)

    assert xato.detail == "live_agent_offline"
    assert xato.agent_last_seen_at is None
