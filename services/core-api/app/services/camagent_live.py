"""CamAgent obyektlarida jonli ko'rish — oqim SERVERGA KELADI.

⛔⛔ NEGA ALOHIDA MODUL VA NEGA UMUMAN KERAK.

    Odatdagi yo'lda go2rtc kameraga o'zi ulanadi:
    `rtsp://user:pass@192.168.1.113:554/...`. CamAgent obyektida bu
    manzil BOZORNING ICHKI tarmog'ida va serverdan unga yo'l YO'Q —
    CamAgent 1-prinsipi modemda port ochishni, oq IP olishni va NVR'ni
    internetga chiqarishni TAQIQLAYDI (`CLAUDE.md` §2).

    Ya'ni «Ko'rish» tugmasi bunday obyektlarda hech qachon ishlamasdi
    va xato «go2rtc javob bermadi» deb ko'rinardi — operator esa
    kamerani yoki tarmoqni ayblardi.

    Bu modul zanjirni TESKARI yo'nalishda quradi:

        sbozor -> CamAgent gateway -> agent (WS buyruq)
        agent  -> ffmpeg -> MediaMTX (RTSP publish, TASHQARIGA)
        go2rtc -> MediaMTX (server ICHIDA o'qish)

    Bozor tarmog'iga hech kim kirmaydi va hech qanday port ochilmaydi.

⚠ QAYSI KAMERA SHU YO'LDAN KETADI: `nvr_devices.username == 'camagent'`.
  Bu qiymatni `agent_gateway/sbozor_sync.py` yozadi va u LOGIN emas —
  belgi: CamAgent qurilmasiga sbozor hech qachon o'zi ulanmaydi, ya'ni
  bu ustunda haqiqiy foydalanuvchi nomi turishining ma'nosi yo'q.

⚠ REKVIZIT BU YO'LDA UMUMAN ISHLATILMAYDI. Parol agentda (DPAPI bilan
  shifrlangan) va u serverga hech qachon kelmaydi. `nvr_credentials`
  qatorining yo'qligi shuning uchun XATO EMAS — odatdagi yo'lda esa u
  503 beradi.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

import httpx
import structlog

log = structlog.get_logger(__name__)

CAMAGENT_USERNAME = "camagent"
"""`nvr_devices.username` dagi belgi. `sbozor_sync.py` bilan bir xil."""

_TIMEOUT_SECONDS = 10.0
"""Gateway agentga WS orqali buyruq yuboradi va javob kutmaydi, ya'ni
javob tez keladi. Uzun timeout bu yerda faqat foydalanuvchini kutishga
majbur qilardi."""

# Agentga beriladigan oqim muddati. sbozor tokeni 5 daqiqada
# yangilanadi (`LIVE_SESSION_MAX_MS`), ya'ni oqim ham shuncha kerak;
# marja yangilanish kechikishini yopadi.
STREAM_DURATION_S = 360

# Devor katakchasi uchun — QISQA (260829). Devor 16 kamerani BIR VAQTDA
# ochadi va har biri bozorning uplink'idan yeydi (o'lchangan 10.7
# Mbit/s). Katakcha 10 soniya jonli ko'rsatib oxirgi kadrga qaytadi,
# ya'ni oqim shundan uzoq yashashi kerak emas. Marja — ffmpeg ko'tarilish
# vaqti va tarmoq kechikishi uchun.
PREVIEW_DURATION_S = 20


class CamAgentLiveError(RuntimeError):
    """Gateway oqim bera olmadi.

    ⚠ MATNGA GATEWAY JAVOBI YOZILMAYDI: u tashqi servisning matni va
      chaqiruvchi uni jurnalga chiqaradi. Sinf nomining o'zi yetarli
      (`cameras.py` da `type(exc).__name__` yoziladi).
    """


def is_camagent_device(device: Any) -> bool:
    """Qurilma CamAgent orqali keladimi."""
    return (getattr(device, "username", "") or "") == CAMAGENT_USERNAME


async def open_stream(
    base_url: str,
    token: str,
    *,
    market_id: UUID,
    camera_serial: str,
    channel_no: int,
    viewer: str,
    duration_s: int = STREAM_DURATION_S,
) -> tuple[str, str]:
    """Gateway'dan oqim so'raydi.

    Returns:
        `(rtsp_url, session_id)` — birinchisi go2rtc uchun manba,
        ikkinchisi ijara kaliti.

    Raises:
        CamAgentLiveError: gateway sozlanmagan, javob bermadi yoki
            kamerani topa olmadi.
    """
    if not base_url or not token:
        raise CamAgentLiveError("gateway sozlanmagan")
    if not camera_serial:
        # Seriyasiz kamerani gateway topa olmaydi. Bu holat sinxronizatsiya
        # buzilganini bildiradi — jonli ko'rish emas, u tuzatilishi kerak.
        raise CamAgentLiveError("kamera seriyasi yo'q")

    tana = {
        "market_id": str(market_id),
        "camera_serial": camera_serial,
        "channel_no": int(channel_no),
        "viewer": viewer,
        "duration_s": int(duration_s),
    }
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
            javob = await client.post(
                f"{base_url.rstrip('/')}/internal/stream/start",
                json=tana,
                headers={"Authorization": f"Bearer {token}"},
            )
    except httpx.HTTPError as exc:
        raise CamAgentLiveError("gateway javob bermadi") from exc

    if javob.status_code != 200:
        log.warning(
            "camagent_stream_rejected",
            status=javob.status_code,
            camera_serial=camera_serial,
        )
        raise CamAgentLiveError("gateway rad etdi")

    natija = javob.json()
    rtsp = str(natija.get("rtsp_url") or "")
    session_id = str(natija.get("session_id") or "")
    if not rtsp:
        raise CamAgentLiveError("gateway manzil bermadi")
    return rtsp, session_id
