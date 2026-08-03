"""Sim NVR'ning RTSP oyog'i REKVIZIT TALAB QILADI (CAM-09, CAM-03, T-03-84).

=============================================================================
BU FAYLDAGI DA'VO NIMA — VA NEGA U ENG MUHIM O'LCHOV.

Da'vo: `nvr-sim` KASHFIYOT E'LON QILGAN PORTDA rostdan RTSP xizmat qiladi,
va o'sha server **rekvizitsiz ulanishni RAD ETADI**.

Ikkinchi yarim birinchisidan muhimroq. Agar manba anonim o'qishga ruxsat
bersa:
  * `03-13` ning rekvizit uzatish oyog'i UMUMAN o'lchanmasdan qolardi —
    go2rtc parol yubormasa ham tasvir kelaverardi;
  * `03-14` ning uchidan-uchiga testi rekvizit BUTUNLAY tashlab yuborilgan
    holatda ham YASHIL bo'lardi.
Ya'ni "parol shifrlangan holda saqlanadi va faqat go2rtc konfiguratsiyasi
hosil qilinayotganda ochiladi" degan butun hikoya isbotsiz qolardi.

=============================================================================
NEGA XOM TCP, `ffmpeg`/`httpx` EMAS.

`DESCRIBE` ga qaytadigan `401` ni kutubxona odatda O'ZI yutadi va rekvizit
bilan qayta so'raydi — ya'ni "birinchi javob 401 edimi?" savoli
kutubxonaning ichida qolib ketardi. Xom soket bu qatlamni olib tashlaydi:
biz AYNAN birinchi javob satrini va sarlavhalarini ko'ramiz.

Autentifikatsiya SXEMASI (`Basic` yoki `Digest`) ATAYIN tekshirilmaydi —
u server versiyasiga bog'liq, da'vo esa «rekvizit talab qilinadi», «qaysi
sxema bilan» emas.

⚠ PORT TESTGA QOTIRILMAYDI. U `GET /__sim__/state` dan so'raladi, ya'ni
  `adminAccesses` e'lon qiladigan qiymat bilan BITTA manbadan keladi.
  Qotirilgan son ikkinchi haqiqat manbai bo'lardi va port o'zgarganda test
  «hammasi joyida» deb turaverardi.
=============================================================================
"""

from __future__ import annotations

import asyncio
from urllib.parse import urlsplit

import pytest
from fixtures.nvr_sim import sim_state

pytestmark = pytest.mark.sim

RTSP_TIMEOUT_SECONDS = 10.0
"""ANIQ taymaut — `None` (cheksiz) HECH QACHON.

Osilgan soket CI'ni butunlay to'xtatib qo'yardi va sabab "test sekin"
bo'lib ko'rinardi. 10 s — `fixtures/nvr_sim.py` dagi HTTP taymauti bilan
bir xil tartib.
"""

MAIN_STREAM_PATH = "/Streaming/Channels/101"
"""Kanal 1, ASOSIY oqim — `services/core-api/app/services/rtsp.py` ning shakli.

`{kanal}{oqim}`: `101` = kanal 1 + oqim 01. Bu satr mahsulot kodidagi
`rtsp_url()` hosil qiladigan yo'lning AYNAN o'zi — sim boshqa shaklni
qabul qilsa, mahsulot yo'li sinovdan o'tmagan bo'lib qolardi.
"""

UNKNOWN_STREAM_PATH = "/Streaming/Channels/9901"
"""Kanal 99 — CI'dagi 6 kanaldan TASHQARIDA (`SIM_CHANNEL_COUNT=6`)."""


async def _rtsp_request(host: str, port: int, path: str) -> tuple[str, dict[str, list[str]]]:
    """REKVIZITSIZ `DESCRIBE` yuboradi va (holat satri, sarlavhalar) qaytaradi.

    `Authorization` sarlavhasi ATAYIN YO'Q — testning butun ma'nosi shu.
    """
    request = (
        f"DESCRIBE rtsp://{host}:{port}{path} RTSP/1.0\r\n"
        "CSeq: 1\r\n"
        "Accept: application/sdp\r\n"
        f"User-Agent: {__name__}\r\n"
        "\r\n"
    )

    async with asyncio.timeout(RTSP_TIMEOUT_SECONDS):
        reader, writer = await asyncio.open_connection(host, port)
        try:
            writer.write(request.encode("ascii"))
            await writer.drain()
            # Sarlavhalar bloki bo'sh qator bilan tugaydi. Tanani o'qimaymiz:
            # `401` javobida u yo'q, `readuntil` esa uni kutib osilib qolardi.
            raw = await reader.readuntil(b"\r\n\r\n")
        finally:
            writer.close()
            await writer.wait_closed()

    head = raw.decode("utf-8", errors="replace").split("\r\n")
    status_line = head[0]

    headers: dict[str, list[str]] = {}
    for line in head[1:]:
        if not line:
            continue
        name, _, value = line.partition(":")
        # RTSP bir sarlavhani BIR NECHA marta yuborishi mumkin
        # (`WWW-Authenticate` aynan shunday: Basic + Digest).
        headers.setdefault(name.strip().lower(), []).append(value.strip())

    return status_line, headers


def _rtsp_endpoint(sim: str) -> tuple[str, int]:
    """Sim'ning RTSP manzili — XOST ISAPI xosti bilan BIR XIL, port sim'dan.

    Xostning bir xilligi bu fazaning markaziy qarori: real NVR'da ISAPI ham,
    RTSP ham bitta manzilda yashaydi va kashfiyot hosil qiladigan URL'ning
    xosti `nvr_devices.host` dan keladi.
    """
    host = urlsplit(sim).hostname
    assert host, f"`{sim}` dan xost ajratib bo'lmadi"

    state = sim_state(sim)
    port = int(state["rtsp_port"])
    assert port > 0, f"sim e'lon qilgan `rtsp_port` yaroqsiz: {state}"

    return host, port


async def test_rtsp_source_listens_on_the_advertised_port(sim: str) -> None:
    """`adminAccesses` e'lon qilgan portda HAQIQATAN javob beradigan server bor.

    Bu test eng birinchi turadi: qolganlarining yiqilish sababini bir
    qarashda ajratib beradi. Yiqilsa — `nvr-sim-rtsp` ko'tarilmagan
    (`npm run sim:up`), «kod buzilgan» degani EMAS.
    """
    host, port = _rtsp_endpoint(sim)

    status_line, _ = await _rtsp_request(host, port, MAIN_STREAM_PATH)

    assert status_line.startswith("RTSP/1.0"), (
        f"`{host}:{port}` RTSP javobi emas, boshqa protokol qaytardi: {status_line!r}"
    )


async def test_anonymous_describe_is_rejected(sim: str) -> None:
    """REKVIZITSIZ `DESCRIBE` -> `401` + `WWW-Authenticate`.

    Bu faylning ASOSIY o'lchovi (T-03-84). Yiqilishi «manba anonim o'qishga
    ruxsat berdi» degani, ya'ni `03-13` va `03-14` ning rekvizit hikoyasi
    o'lchanmasdan qolgan.
    """
    host, port = _rtsp_endpoint(sim)

    status_line, headers = await _rtsp_request(host, port, MAIN_STREAM_PATH)

    assert "401" in status_line.split(), (
        f"rekvizitsiz `DESCRIBE` `401` OLMADI: {status_line!r}. Manba anonim "
        "o'qishga ruxsat berayotgan bo'lsa, rekvizit uzatish oyog'i "
        "(03-13) umuman o'lchanmaydi va uni tashlab yuborish HECH BIR "
        "testni qizartirmaydi."
    )
    assert "www-authenticate" in headers, (
        f"`401` keldi, lekin `WWW-Authenticate` sarlavhasi yo'q: {headers}. "
        "Usiz mijoz qaysi sxema bilan qayta urinishni bilmaydi — real "
        "qurilma bu sarlavhani HAR DOIM yuboradi."
    )


async def test_unknown_channel_also_requires_credentials(sim: str) -> None:
    """NOMA'LUM yo'l ham `401` oladi — mavjudlik AUTENTIFIKATSIYADAN OLDIN oshkor bo'lmaydi.

    Server `404` bersa, rekvizitsiz mijoz qaysi kanallar bor va qaysilari
    yo'qligini sanab chiqa olardi: bu ro'yxat NVR topologiyasini va bozor
    hajmini oshkor qiladi (`new_stream_name` ning ma'nosiz nom tanlashi
    bilan bir xil sabab, T-03-25).
    """
    host, port = _rtsp_endpoint(sim)

    status_line, headers = await _rtsp_request(host, port, UNKNOWN_STREAM_PATH)

    assert "401" in status_line.split(), (
        f"noma'lum yo'l uchun javob `401` EMAS: {status_line!r} — server yo'lning "
        "mavjudligini rekvizitdan OLDIN oshkor qilyapti"
    )
    assert "www-authenticate" in headers, f"`401` da `WWW-Authenticate` yo'q: {headers}"
