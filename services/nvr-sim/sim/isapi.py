"""ISAPI yuzasi — real dumpdan olingan fixture'larni `SimState` bo'yicha parametrlaydi.

=============================================================================
NEGA FIXTURE'LAR MATN DARAJASIDA QAYTA ISHLANADI (va `ElementTree` bilan
qayta serializatsiya QILINMAYDI):

Fixture'lar `hikvision_next` ning yozib olingan dumplaridan VERBATIM olingan
(`fixtures/README.md`). `ElementTree` ularni parse qilib qayta yozganda:
  * har `<InputProxyChannel ... xmlns="...">` dagi TAKRORIY namespace e'loni
    yo'qoladi (u ortiqcha, lekin real qurilma aynan shunday yuboradi);
  * atribut tartibi va bo'sh elementlarning shakli o'zgarishi mumkin.
Ya'ni "verbatim" da'vosi jimgina yolg'onga aylanardi.

Shuning uchun: `ElementTree` faqat TEKSHIRISH uchun (fayl yaroqli XML mi),
javob esa fixture MATNIDAN quriladi. Hujjat qat'iy ma'lum va o'zgarmas
(CDATA yo'q, ichma-ich `InputProxyChannel` yo'q), shuning uchun blok
ajratish ishonchli.
=============================================================================

⚠ `@size` atributi fixture'dan **VERBATIM** qoladi va emitilgan kanallar
soniga MOSLANMAYDI. Bu ataylab: yuqori oqimdagi `DS-7732NI-M4` dumpida
`size="14"`, lekin `InputProxyChannel` elementlari **18 ta** — ya'ni real
qurilma bu atributga zid qiymat yuboradi. Kashfiyot kodi elementlarni
SANASHI kerak, `size` ga ishonmasligi. Sim buni qayta tug'diradi.
"""

from __future__ import annotations

import base64
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path

from defusedxml.ElementTree import fromstring as xml_fromstring
from fastapi import Request, Response
from starlette.types import Receive, Scope, Send

from .state import (
    MODEL_DS_7616,
    MODEL_DS_7732,
    MODEL_IPCAMERA,
    STREAM_LIMIT_SILENT,
    SimState,
)

ISAPI_PREFIX = "/ISAPI"
FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"

NVR_MODELS = frozenset({MODEL_DS_7616, MODEL_DS_7732})
"""A.1: `InputProxy` FAQAT NVR/gibrid-DVR da bor; qolganida u 404 beradi."""

SLOT_COUNT = {MODEL_DS_7616: 16, MODEL_DS_7732: 32}
"""Qurilmaning video-kirish SLOTLARI soni — ulangan kameralar soni EMAS (A.1)."""

# 1x1 piksel JPEG (sintetik). CI'da rasm MAZMUNI muhim emas — B.7 #9 bo'yicha
# bu 4-faza uchun ilgak va bu fazada faqat MAVJUDLIGI tekshiriladi. Git'ga
# binar fayl qo'shilmaydi (B.6 "video manbai" jadvali bilan bir xil qoida).
_TINY_JPEG_B64 = (
    "/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRof"
    "Hh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/wAALCAABAAEBAREA/8QAFAAB"
    "AAAAAAAAAAAAAAAAAAAACf/EABQQAQAAAAAAAAAAAAAAAAAAAAD/2gAIAQEAAD8AKp//2Q=="
)
TINY_JPEG = base64.b64decode(_TINY_JPEG_B64)

_COMMENT_RE = re.compile(r"<!--.*?-->\s*", re.DOTALL)
_CHANNEL_RE = re.compile(r"<InputProxyChannel\b.*?</InputProxyChannel>", re.DOTALL)


def _load(name: str) -> str:
    """Fixture matnini o'qiydi, XML sifatida TEKSHIRADI va manba izohini olib tashlaydi.

    Izoh javobga chiqmaydi — real qurilma bizning manba qaydimizni yubormaydi.
    Lekin u FAYLDA qoladi: `tests/unit/test_sim_fixtures.py` aynan shuni izlaydi.
    """
    raw = (FIXTURES_DIR / name).read_text(encoding="utf-8")
    # `defusedxml` — loyiha standarti (`app/services/xlsx_reader.py` bilan bir xil
    # qoida). Bu yerda kirish ishonchli (o'z repomizdagi statik fayl), lekin
    # "ishonchli manba" istisnosini ochish keyingi safar ishonchsiz manbaga
    # ko'chib o'tadigan turdagi qoida. Yangi paket QO'SHILMAYDI: `defusedxml==0.7.1`
    # allaqachon `core-api` ning ishlab chiqarish bog'liqligi.
    xml_fromstring(raw)
    return _COMMENT_RE.sub("", raw, count=1).strip()


def xml_response(
    body: str,
    *,
    status_code: int = 200,
    headers: dict[str, str] | None = None,
) -> Response:
    """Hikvision javoblari `application/xml` bilan keladi."""
    return Response(
        content=body,
        status_code=status_code,
        media_type="application/xml",
        headers=headers,
    )


def hikvision_error_xml(
    *,
    status_code: int,
    status_string: str,
    sub_status: str | None = None,
    detail: str | None = None,
) -> str:
    """`<ResponseStatus>` — Hikvision'ning standart xato tanasi (A.3, B.8).

    ⚠ `statusCode` ≠ 1 = xato. `200 OK` bilan kelgan javob ham `statusCode`
    orqali xato bo'lishi mumkin — shuning uchun kashfiyot kodi faqat HTTP
    kodiga qaramaydi.
    """
    lines = [
        '<ResponseStatus version="1.0" xmlns="http://www.hikvision.com/ver20/XMLSchema">',
        "  <requestURL>/ISAPI</requestURL>",
        f"  <statusCode>{status_code}</statusCode>",
        f"  <statusString>{status_string}</statusString>",
    ]
    if sub_status is not None:
        lines.append(f"  <subStatusCode>{sub_status}</subStatusCode>")
    if detail is not None:
        lines.append(f"  <errorMsg>{detail}</errorMsg>")
    lines.append("</ResponseStatus>")
    return "\n".join(lines)


STREAM_LIMIT_XML = hikvision_error_xml(
    status_code=7,
    status_string="Device Busy",
    sub_status="deviceBusy",
    detail="Maximum number of streams reached",
)
"""A.5 / D-05: chegara `reject` shaklida shunday ko'rinadi.

⚠ `errorMsg` dagi "Maximum number of streams" — Hikvision Web-UI'sida
ko'rinadigan matn. A.5 aynan buni ogohlantiradi: bu matn RTSP javobiga
TARJIMA QILINMASLIGI mumkin, shuning uchun `nvr_stream_limit` — heuristika,
kafolat emas, va `error_detail` da xom javob saqlanadi.
"""


# ---------------------------------------------------------------------------
# Kanal ro'yxati — fixture'dagi elementdan shablon sifatida foydalaniladi.
# ---------------------------------------------------------------------------


def _replace_first(text: str, tag: str, value: str) -> str:
    return re.sub(rf"<{tag}>[^<]*</{tag}>", f"<{tag}>{value}</{tag}>", text, count=1)


def _bump_last_octet(ip: str, delta: int) -> str:
    parts = ip.split(".")
    if len(parts) != 4 or not parts[3].isdigit():
        return ip
    parts[3] = str((int(parts[3]) + delta - 1) % 254 + 1)
    return ".".join(parts)


def _channel_blocks(state: SimState) -> list[str]:
    """`channel_count` ta kanal bloki — imkon qadar fixture'dagi HAQIQIY yozuvlar.

    Fixture'da yetarli kanal bo'lsa ular VERBATIM olinadi (real nom, real
    kamera modeli, real IP). Yetmasa — oxirgisi shablon sifatida ko'paytiriladi
    va `id` / `name` / `ipAddress` o'sadi. Ya'ni "6 kanal" stsenariysi
    (D-09, CI) to'liq real ma'lumot ustida ishlaydi, "25 kanal" (sekin test)
    esa ochiq-oydin sintetik quyruq oladi.
    """
    document = _load(_fixture_for(state.model, "inputProxyChannels"))
    templates = _CHANNEL_RE.findall(document)
    if not templates:  # pragma: no cover - fixture buzilgan bo'lsa
        raise RuntimeError("fixture'da `InputProxyChannel` topilmadi")

    blocks: list[str] = []
    for channel_no in range(1, state.channel_count + 1):
        if channel_no in state.removed_channels:
            # B.8 `channel_removed`: kanal ro'yxatdan BUTUNLAY chiqadi.
            # Kutilgan natija — kamera yozuvi `offline` bo'ladi, O'CHIRILMAYDI (D-10).
            continue
        if channel_no <= len(templates):
            block = templates[channel_no - 1]
        else:
            block = templates[-1]
            block = _replace_first(block, "id", str(channel_no))
            block = _replace_first(block, "name", f"sim_cam_{channel_no:02d}")
            match = re.search(r"<ipAddress>([^<]*)</ipAddress>", block)
            if match:
                shifted = _bump_last_octet(match.group(1), channel_no - len(templates))
                block = _replace_first(block, "ipAddress", shifted)

        if state.mode == "camera_swapped" and state.swapped_channel == channel_no:
            # B.8 `camera_swapped`: kanal o'sha, ORTIDAGI KAMERA boshqa.
            # A.4 bo'yicha bu `camera_source_changed` audit yozuvini tug'diradi
            # va 5-fazada zona poligonlarining yaroqsiz bo'lish signali shundan keladi.
            if state.swapped_ip:
                block = _replace_first(block, "ipAddress", state.swapped_ip)
            if state.swapped_model:
                block = _replace_first(block, "model", state.swapped_model)
        blocks.append(block)
    return blocks


def _fixture_for(model: str, kind: str) -> str:
    """`model` — fixture TANLAGICHI (`state.KNOWN_MODELS`), fayl nomi undan hosil bo'ladi."""
    return f"{model}-{kind}.xml"


def _list_envelope(document: str, tag: str) -> tuple[str, str]:
    """Ro'yxat hujjatining ochilish va yopilish teglarini VERBATIM ajratadi."""
    opening = re.search(rf"<{tag}\b[^>]*>", document)
    if opening is None:  # pragma: no cover - fixture buzilgan bo'lsa
        raise RuntimeError(f"fixture'da `<{tag}>` topilmadi")
    return opening.group(0), f"</{tag}>"


def _input_proxy_channels(state: SimState) -> str:
    document = _load(_fixture_for(state.model, "inputProxyChannels"))
    head, tail = _list_envelope(document, "InputProxyChannelList")
    body = "\n".join(f"  {block}" for block in _channel_blocks(state))
    return f"{head}\n{body}\n{tail}"


def _input_proxy_status(state: SimState) -> str:
    """`.../channels/status` — har kanal uchun `<online>`.

    ⚠ MANBA: bu hujjat yuqori oqim dumplarida YO'Q (ular faqat `channels` ni
    yozib olgan). Shakl `03-RESEARCH.md` A.1 dan olindi: `status` javobi `id`
    bo'yicha ro'yxatga qo'shiladi va `<online>true|false</online>` beradi
    (`eu-evops/homebridge-hikvision` shu naqshni ishlatadi). Bu TAXMIN va u
    shu yerda OCHIQ belgilanadi — yashirin taxmin qabul qilinmaydi (Pitfall 4).
    """
    rows: list[str] = []
    for channel_no in range(1, state.channel_count + 1):
        if channel_no in state.removed_channels:
            continue
        online = "false" if channel_no in state.offline_channels else "true"
        rows.append(
            '  <InputProxyChannelStatus version="1.0" '
            'xmlns="http://www.hikvision.com/ver20/XMLSchema">\n'
            f"    <id>{channel_no}</id>\n"
            f"    <online>{online}</online>\n"
            f"    <streamingProxyChannelIdList>{channel_no}</streamingProxyChannelIdList>\n"
            "  </InputProxyChannelStatus>"
        )
    body = "\n".join(rows)
    return (
        '<InputProxyChannelStatusList version="1.0" '
        'xmlns="http://www.hikvision.com/ver20/XMLSchema">\n'
        f"{body}\n"
        "</InputProxyChannelStatusList>"
    )


def _device_info(state: SimState) -> str:
    document = _load(_fixture_for(state.model, "deviceInfo"))
    if state.mode == "not_hikvision":
        # B.8: Digest O'TADI, lekin qurilma bizniki emas -> `device_not_supported`.
        document = _replace_first(document, "manufacturer", "Acme Video Systems")
        document = _replace_first(document, "model", "AVS-9000")
        document = _replace_first(document, "deviceType", "NetworkVideoRecorder")
    return document


def _admin_accesses(state: SimState) -> str:
    """RTSP porti `state.rtsp_port` dan keladi — 554 QOTIRILMAYDI (A.2, Pitfall 8)."""
    document = _load(_fixture_for(MODEL_DS_7616, "adminAccesses"))

    def _patch(match: re.Match[str]) -> str:
        block = match.group(0)
        if "<protocol>RTSP</protocol>" in block:
            return _replace_first(block, "portNo", str(state.rtsp_port))
        return block

    return re.sub(
        r"<AdminAccessProtocol\b.*?</AdminAccessProtocol>", _patch, document, flags=re.DOTALL
    )


def _video_input_channels(state: SimState) -> Response:
    """A.1 2-qadam-B — standalone kamera yo'li.

    ⚠ NVR rejimida bu **403** qaytaradi. Bu O'YLAB TOPILGAN emas: `DS-7616NI-K2`
    ham, `DS-7732NI-M4` ham yuqori oqim dumpida bu endpoint uchun aynan
    `{"status_code": 403}` yozib olingan. Ya'ni NVR'da kanal ro'yxatining
    yagona ishonchli manbai — `InputProxy` (A.1 "AVTORITETLI" ustuni).
    """
    if state.model in NVR_MODELS:
        return xml_response(
            hikvision_error_xml(status_code=6, status_string="Invalid Operation"),
            status_code=403,
        )
    return xml_response(_load(_fixture_for(MODEL_IPCAMERA, "videoInputChannels")))


def _system_time(state: SimState) -> str:
    """NTP diagnostikasi (B.7 #10, fidelity PAST).

    ⚠ MANBA: dumplarda bu endpoint yo'q; shakl Hikvision ISAPI hujjatidagi
    `<Time>` elementidan olindi va bu TAXMIN sifatida ochiq belgilanadi.
    Qiymat `drift_seconds` bilan siljiydi — ya'ni A.3 dagi ikkinchi, mustaqil
    soat-farqi manbai ham sinaladi.
    """
    device_now = datetime.now(UTC) + timedelta(seconds=state.drift_seconds)
    return (
        '<Time version="1.0" xmlns="http://www.hikvision.com/ver20/XMLSchema">\n'
        "  <timeMode>NTP</timeMode>\n"
        f"  <localTime>{device_now.strftime('%Y-%m-%dT%H:%M:%S+05:00')}</localTime>\n"
        "  <timeZone>CST-5:00:00</timeZone>\n"
        "</Time>"
    )


CAPABILITIES_XML = (
    '<DeviceCap version="1.0" xmlns="http://www.hikvision.com/ver20/XMLSchema">\n'
    "  <SysCap>\n"
    "    <NetworkCap>\n"
    "      <isSupportNtp>true</isSupportNtp>\n"
    "      <isSupportHttps>true</isSupportHttps>\n"
    "    </NetworkCap>\n"
    "  </SysCap>\n"
    "</DeviceCap>"
)
"""B.7 #11 — fidelity PAST, hozircha ishlatilmaydi.

⚠ Bu QISQARTIRILGAN hujjat: to'liq `DeviceCap` yuqori oqim dumplarida bor
(~40 KB), lekin kashfiyot undan foydalanmaydi. Kerak bo'lganda u ham
fixture qilib ajratiladi — bu yerda tuzilma OCHIQ belgilangan qisqartma.
"""


# ---------------------------------------------------------------------------
# Oqim da'volari — D-05 ning IKKALA stsenariysi.
# ---------------------------------------------------------------------------


class SilentDisconnect(Exception):
    """`stream_limit_mode="silent"` — javobsiz uzilish (D-05 ning ikkinchi shakli).

    A.5 chegaraning RTSP javobida qanday ko'rinishini **LOW** ishonch bilan
    belgilaydi: ba'zi firmware `453`/`503` beradi, ba'zisi esa ulanishni
    JIMGINA uzadi va xato kodi UMUMAN bo'lmaydi. Bitta shaklni tanlash
    heuristikani o'z taxminiga moslashtirgan bo'lardi — shuning uchun D-05
    ikkalasini ham modellashtirishni talab qiladi.

    Uni `main.py` dagi ASGI qatlami ushlaydi va javobni TUGATMASDAN ulanishni
    yopadi — klient status kodini ham, xato XML'ini ham OLMAYDI.
    """


class StreamLimitReached(Exception):
    """`stream_limit_mode="reject"` — Hikvision uslubidagi xato XML'i."""


class SilentDropResponse(Response):
    """Javobni ATAYLAB TUGATMAYDI — klient uzilishni ko'radi, status kodini emas.

    ASGI qatlamida soketni to'g'ridan-to'g'ri yopish mumkin emas, shuning uchun
    "jimgina uzilish" ning ASGI'dan erishiladigan eng yaqin analogi ishlatiladi:
    `Content-Length` E'LON QILINADI, tana esa YUBORILMAYDI. `h11` shuni ko'rib
    protokol xatosi beradi va `uvicorn` ulanishni javobni tugatmasdan yopadi.

    Klient tomonda kuzatiladigan xususiyat aynan D-05 talab qilgani:
      * ishlatib bo'ladigan status kodi YO'Q,
      * xato XML'i YO'Q,
      * `httpx` transport darajasidagi istisno beradi.

    ⚠ Bu SHAKL, kafolat emas: A.5 chegaraning wire darajasida qanday
    ko'rinishini **LOW** ishonch bilan belgilaydi. Shuning uchun heuristika
    `error_detail` da xom javobni saqlaydi va xabar "ehtimol" tarzida beriladi.
    """

    def __init__(self) -> None:
        super().__init__(status_code=200, media_type="application/xml")

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        del scope, receive
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [
                    (b"content-type", b"application/xml"),
                    (b"content-length", b"1024"),
                ],
            }
        )
        await send({"type": "http.response.body", "body": b"", "more_body": False})


def _claim_stream(state: SimState) -> None:
    """Oqim da'vo qiladi; chegaradan oshsa rejimga qarab rad etadi.

    ⚠ Sanoq `POST /__sim__/reset` bilan NOLGA qaytadi — busiz testlar
    bir-birining sanog'ini meros qilib olardi.
    """
    if state.stream_claims + 1 > state.stream_limit:
        if state.stream_limit_mode == STREAM_LIMIT_SILENT:
            raise SilentDisconnect
        raise StreamLimitReached
    state.stream_claims += 1


def handle_isapi(state: SimState, path: str, request: Request) -> Response:
    """`/ISAPI/<path>` marshrutlari (B.7 jadvalidagi o'n ikkitasi)."""
    del request  # yuza faqat yo'lga qarab tarmoqlanadi

    if path == "System/deviceInfo":
        return xml_response(_device_info(state))

    if path == "System/capabilities":
        return xml_response(CAPABILITIES_XML)

    if path == "System/time":
        return xml_response(_system_time(state))

    if path == "Security/adminAccesses":
        return xml_response(_admin_accesses(state))

    if path == "System/Video/inputs/channels":
        return _video_input_channels(state)

    if path in {"ContentMgmt/InputProxy/channels", "ContentMgmt/InputProxy/channels/"}:
        if state.model not in NVR_MODELS:
            # A.1: `InputProxy` NVR/gibrid-DVR ga xos; IP-kamerada 404.
            return xml_response(
                hikvision_error_xml(status_code=4, status_string="Invalid Operation"),
                status_code=404,
            )
        return xml_response(_input_proxy_channels(state))

    if path == "ContentMgmt/InputProxy/channels/status":
        return xml_response(_input_proxy_status(state))

    stream = re.fullmatch(r"Streaming/channels/(\d+)(/picture)?", path)
    if stream is not None:
        return _streaming(state, int(stream.group(1)), picture=bool(stream.group(2)))

    # B.7 #12 — noma'lum `/ISAPI/*`: Hikvision uslubidagi XML tanasi bilan 404.
    return xml_response(
        hikvision_error_xml(status_code=4, status_string="Invalid Operation"),
        status_code=404,
    )


def _streaming(state: SimState, stream_id: int, *, picture: bool) -> Response:
    """`{kanal}{oqim}` — `101` = kanal 1 asosiy, `102` = sub (A.2)."""
    channel_no, stream_index = divmod(stream_id, 100)

    if (
        channel_no < 1
        or channel_no > state.channel_count
        or channel_no in state.removed_channels
        or stream_index not in {1, 2}
    ):
        # A.2: sub-oqim mavjudligi KAFOLATLANMAGAN -> `substream_url = NULL` yo'li.
        return xml_response(
            hikvision_error_xml(status_code=4, status_string="Invalid Operation"),
            status_code=404,
        )

    _claim_stream(state)

    if picture:
        return Response(content=TINY_JPEG, media_type="image/jpeg")

    return xml_response(
        '<StreamingChannel version="1.0" xmlns="http://www.hikvision.com/ver20/XMLSchema">\n'
        f"  <id>{stream_id}</id>\n"
        f"  <channelName>{stream_id}</channelName>\n"
        "  <enabled>true</enabled>\n"
        "  <Transport>\n"
        "    <ControlProtocolList>\n"
        "      <ControlProtocol>\n"
        "        <streamingTransport>RTSP</streamingTransport>\n"
        "      </ControlProtocol>\n"
        "    </ControlProtocolList>\n"
        "  </Transport>\n"
        "  <Video>\n"
        "    <enabled>true</enabled>\n"
        f"    <videoInputChannelID>{channel_no}</videoInputChannelID>\n"
        "    <videoCodecType>H.265</videoCodecType>\n"
        f"    <videoResolutionWidth>{3840 if stream_index == 1 else 704}</videoResolutionWidth>\n"
        f"    <videoResolutionHeight>{2160 if stream_index == 1 else 576}</videoResolutionHeight>\n"
        "    <videoQualityControlType>VBR</videoQualityControlType>\n"
        "    <snapShotImageType>JPEG</snapShotImageType>\n"
        "  </Video>\n"
        "</StreamingChannel>"
    )
