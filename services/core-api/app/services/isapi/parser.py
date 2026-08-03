"""ISAPI XML parseri — NAMESPACE-AGNOSTIK va HECH QACHON JIMGINA BO'SH EMAS.

=============================================================================
PITFALL 2 — ENG KO'P UCHRAYDIGAN INTEGRATSIYA XATOSI VA UNING ALOMATI.

Hikvision javoblari standart namespace bilan keladi:

    <DeviceInfo version="1.0" xmlns="http://www.hikvision.com/ver20/XMLSchema">

`ElementTree` bunda yorliqni `{http://www.hikvision.com/ver20/XMLSchema}
deviceType` deb ko'radi. Ya'ni `element.find("deviceType")` **`None`
qaytaradi** — istisno YO'Q, ogohlantirish YO'Q. Kashfiyot o'tadi,
«ulanish muvaffaqiyatli» deydi va **0 kanal topadi**.

⚠ ALOMAT AYNAN SHU: «ulanish muvaffaqiyatli, lekin 0 kanal». Kim buni
ko'rsa birinchi navbatda shu faylga qarasin.

VA NAMESPACE BITTA EMAS. 03-02 yozib olingan dumplarda O'LCHANDI:

    DS-7616NI-K2  ->  http://www.hikvision.com/ver20/XMLSchema
    DS-7732NI-M4  ->  http://www.isapi.org/ver20/XMLSchema     (!)

Tadqiqot ham, reja ham faqat `hikvision.com` ni kutgan edi. Ya'ni bitta
namespace'ni qotirib qo'yish ham yetarli EMAS — parser prefiksga UMUMAN
tayanmaydi va har `find`/`iter` `local_name()` orqali boradi.
=============================================================================

=============================================================================
`@size` ATRIBUTIGA ISHONIB BO'LMAYDI — O'LCHANGAN FAKT.

`DS-7732NI-M4` dumpida `<InputProxyChannelList size="14">`, elementlar esa
**18 ta**. Real qurilma o'z atributiga ZID qiymat yuboradi. Shuning uchun
bu modulda `size` UMUMAN O'QILMAYDI: kanallar ELEMENTLARDAN sanaladi.
=============================================================================

Sof transform: tarmoqqa chiqmaydi, bazaga tegmaydi, holat saqlamaydi
(`app/services/import_validator.py` va `sbozor_core/periods.py` bilan bir
xil shakl). Kirish — baytlar, chiqish — dataclass yoki `NvrError`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

# `defusedxml` — loyiha standarti (`app/services/xlsx_reader.py` bilan bir
# xil qoida va bir xil sabab). Bu yerda kirish ISHONCHSIZ: XML buzilgan
# yoki soxta NVR'dan keladi va u XML bombasi (billion laughs, quadratic
# blowup) yuborishi mumkin (T-03-30). Yangi paket QO'SHILMAYDI —
# `defusedxml==0.7.1` allaqachon `core-api` ning ishlab chiqarish
# bog'liqligi.
from defusedxml.ElementTree import fromstring as xml_fromstring

from app.services.isapi.errors import NvrError

if TYPE_CHECKING:
    from collections.abc import Iterator
    from xml.etree.ElementTree import Element

__all__ = [
    "MAX_RESPONSE_BYTES",
    "ChannelRow",
    "DeviceInfo",
    "local_name",
    "parse_admin_accesses",
    "parse_channel_status",
    "parse_device_info",
    "parse_input_proxy_channels",
    "parse_video_input_channels",
]


MAX_RESPONSE_BYTES: Final[int] = 2 * 1024 * 1024
"""Javob hajmining yuqori chegarasi — 2 MiB.

Eng katta REAL javob — to'liq `DeviceCap` (~40 KB) va 128 kanalli
`InputProxyChannelList` (~250 KB). 2 MiB ularning ikkalasidan ham ancha
katta, ya'ni haqiqiy qurilmani hech qachon kesmaydi.

Chegara buzilgan yoki soxta qurilma uchun: `defusedxml` XML BOMBASINI
to'xtatadi, lekin oddiy KATTA javobni emas — u shunchaki parse bo'ladi va
xotirani yeydi (T-03-30, ASVS V5.5). Chegara shu ikkinchi yo'l uchun.
"""

_RAW_SNIPPET_CHARS: Final[int] = 500
"""Xatodagi `raw` bo'lagining uzunligi — `MAX_RAW_DETAIL_CHARS` dan KICHIK.

Bu yerdagi maqsad tashxis: «javob umuman XML emas edi» ni ko'rsatish
uchun boshidagi bir necha yuz belgi yetarli. To'liq javobni saqlash
`error_detail` jsonb'ini har diagnostikada shishirardi.
"""

_MIN_TWO_PART_CHANNEL_ID: Final[int] = 100
"""`{kanal}{oqim}` shaklining quyi chegarasi — `101` = kanal 1, asosiy oqim."""

_STREAM_INDEXES: Final[frozenset[int]] = frozenset({1, 2})
"""Asosiy (`1`) va sub (`2`) oqim indekslari — `03-RESEARCH.md` A.2."""


def local_name(tag: str) -> str:
    """`{namespace}yorliq` -> `yorliq`. Namespace'siz yorliq O'ZGARMAYDI.

        local_name("{http://www.hikvision.com/ver20/XMLSchema}deviceType")
        -> "deviceType"
        local_name("deviceType") -> "deviceType"

    `rpartition` ATAYIN, `split`/`strip` emas: u ajratuvchi topilmaganda
    ham uch bo'lakli natija beradi va `[2]` har ikki holatda ham to'g'ri
    javob bo'ladi — ya'ni «namespace bormi?» degan shart umuman yozilmaydi
    va uni unutish mumkin emas.
    """
    return tag.rpartition("}")[2]


@dataclass(frozen=True, slots=True)
class DeviceInfo:
    """`GET /ISAPI/System/deviceInfo` natijasi (`03-RESEARCH.md` A.1).

    `device_type` — KASHFIYOTNING TARMOQLANISH NUQTASI (D-04):
    `NVR`/`DVR`/`HDVR` -> `InputProxy` yo'li; `IPCamera`/`IPDome` ->
    standalone yo'li. Qotib qolgan yo'l yo'q.
    """

    model: str
    serial_number: str
    firmware_version: str
    device_type: str
    manufacturer: str


@dataclass(frozen=True, slots=True)
class ChannelRow:
    """NVR ortidagi BITTA kanal — `DiscoveredChannel` (03-04) ning xom shakli.

    ⚠ Bu `app/repositories/nvr_repo.py::DiscoveredChannel` NING NUSXASI
      EMAS va u bilan almashtirilmaydi. Farq QATLAMDA: bu yerda XML dan
      o'qilgani turadi (status hali noma'lum — u `.../status` javobidan
      keladi), repozitoriy DTO'sida esa YOZISHGA TAYYOR qiymatlar.
      Ikkalasini birlashtirish parserni repozitoriyga bog'lardi.
    """

    channel_no: int
    name: str
    source_ip: str | None = None
    source_model: str | None = None


def _raw_snippet(payload: bytes | str) -> str:
    """Tashxis uchun javobning boshi — `errors.py` yana bir bor kesadi."""
    text = payload.decode("utf-8", errors="replace") if isinstance(payload, bytes) else payload
    return text[:_RAW_SNIPPET_CHARS]


def _unavailable(payload: bytes | str, reason: str) -> NvrError:
    """Parser HECH QACHON jimgina bo'sh natija bermaydi (T-03-34).

    `nvr_isapi_unavailable` — «qurilma ISAPI'ni qo'llamaydi yoki manzil
    noto'g'ri» (A.3). Kutilgan ildiz topilmasa aynan shu holat: biz
    ISAPI'ga so'rov yubordik, javob keldi, lekin u ISAPI javobi emas
    (masalan NVR ning web-porti HTML login sahifasini qaytardi).
    """
    return NvrError("nvr_isapi_unavailable", {"raw": f"{reason}: {_raw_snippet(payload)}"})


def _root(payload: bytes | str, *, expected: str) -> Element:
    """Hujjatni parse qiladi va ILDIZ YORLIG'INI tekshiradi.

    Ildiz tekshiruvi ATAYIN: `200 OK` bilan kelgan javob ham xato bo'lishi
    mumkin — Hikvision `<ResponseStatus><statusCode>6</statusCode>` ni
    `200` bilan ham yuboradi, ya'ni HTTP kodining o'zi yetarli emas.
    Ildizni tekshirmasak `<ResponseStatus>` dan «0 kanal» chiqarardik va
    bu aynan Pitfall 2 ning alomati bo'lardi, sababi esa boshqa.
    """
    raw = payload if isinstance(payload, bytes) else payload.encode("utf-8")
    if len(raw) > MAX_RESPONSE_BYTES:
        raise NvrError(
            "nvr_isapi_unavailable",
            {"raw": f"javob {len(raw)} bayt, chegara {MAX_RESPONSE_BYTES} bayt"},
        )

    try:
        element: Element = xml_fromstring(raw)
    except ValueError as exc:
        # `xml.etree.ElementTree.ParseError` -> `SyntaxError`; `defusedxml`
        # ning `DefusedXmlException` -> `ValueError`. Ikkalasi ham bu yerda
        # ushlanadi (`ParseError` `SyntaxError` orqali `Exception` da, shu
        # sababli u alohida sanaladi).
        raise _unavailable(payload, f"XML parse bo'lmadi ({type(exc).__name__})") from exc
    except SyntaxError as exc:
        raise _unavailable(payload, f"XML parse bo'lmadi ({type(exc).__name__})") from exc

    actual = local_name(element.tag)
    if actual != expected:
        raise _unavailable(payload, f"kutilgan ildiz `<{expected}>`, kelgani `<{actual}>`")
    return element


def _children(element: Element, name: str) -> Iterator[Element]:
    """BEVOSITA bolalar, namespace'dan QAT'I NAZAR.

    `element.iter()` EMAS: u butun daraxtni kezadi va ichma-ich bir xil
    nomli elementni ham qaytarardi (`<InputProxyChannel>` ichidagi `<id>`
    ro'yxat darajasidagi `<id>` bilan aralashib ketardi).
    """
    for child in element:
        if local_name(child.tag) == name:
            yield child


def _text(element: Element, name: str) -> str | None:
    """Bevosita bolaning matni yoki `None` (bo'sh element ham `None`)."""
    for child in _children(element, name):
        value = (child.text or "").strip()
        return value or None
    return None


def _required_text(element: Element, name: str, payload: bytes | str) -> str:
    value = _text(element, name)
    if value is None:
        raise _unavailable(payload, f"`<{name}>` topilmadi yoki bo'sh")
    return value


def parse_device_info(payload: bytes | str) -> DeviceInfo:
    """`<DeviceInfo>` -> model, seriya, firmware, `deviceType`, ishlab chiqaruvchi.

    Namespace BILAN ham, namespace'SIZ ham bir xil natija beradi va bu
    `test_namespaced_xml` bilan alohida qulflangan.
    """
    root = _root(payload, expected="DeviceInfo")
    return DeviceInfo(
        model=_required_text(root, "model", payload),
        serial_number=_text(root, "serialNumber") or "",
        firmware_version=_text(root, "firmwareVersion") or "",
        device_type=_text(root, "deviceType") or "",
        manufacturer=_text(root, "manufacturer") or "",
    )


def _normalise_channel_id(raw_id: str) -> int | None:
    """`<id>` ni kanal raqamiga keltiradi. Noaniq qiymat uchun `None`.

    ⚠ QOIDA VA UNING SABABI:

    Hikvision firmware'lari `InputProxy` da kanal identifikatorini IKKI
    XIL yozadi — `1` (sof kanal) yoki `101` (`{kanal}{oqim}`, A.2 dagi
    RTSP raqamlash bilan bir xil shakl). Normallash:

        id <= 0                          -> None   (yaroqsiz)
        id < 100                         -> id     (sof kanal)
        id >= 100 va (id % 100) in {1,2} -> id//100  (`{kanal}{oqim}`)
        qolgan hollarda                  -> id     (sof kanal, katta NVR)

    ⚠ CHEGARADAGI NOANIQLIK OCHIQ QOLADI: 100 dan ortiq kanalli qurilmada
      `101` ikki ma'noli bo'ladi — «kanal 101» yoki «kanal 1, asosiy
      oqim». Hikvision NVR'lari amalda 128 kanalgacha chiqadi, ya'ni bu
      nazariy jihatdan mumkin. Karmana uchun 25 kanal kutilmoqda, ya'ni
      xavf yo'q. Qaror `{kanal}{oqim}` foydasiga: u REAL uchraydigan
      shakl, 100+ kanalli bitta NVR esa uchramaydi.

    Kanal O'TKAZIB YUBORILADI, `NvrError` KO'TARILMAYDI: bitta g'alati
    kanal butun kashfiyotni to'xtatmasligi kerak — 24 ta sog'lom kamera
    bittasi tufayli yo'qolardi.
    """
    try:
        value = int(raw_id)
    except ValueError:
        return None
    if value <= 0:
        return None
    if value >= _MIN_TWO_PART_CHANNEL_ID and (value % 100) in _STREAM_INDEXES:
        return value // 100
    return value


def parse_input_proxy_channels(
    payload: bytes | str, *, skipped: list[str] | None = None
) -> list[ChannelRow]:
    """`<InputProxyChannelList>` -> kanallar (NVR'da AVTORITETLI manba, A.1).

    ⚠ `size` ATRIBUTI O'QILMAYDI (modul docstringi): kanallar
      ELEMENTLARDAN sanaladi.

    Args:
        payload: xom javob.
        skipped: berilsa, o'tkazib yuborilgan kanallarning tavsifi shu
            ro'yxatga qo'shiladi. ⚠ Reja bu ma'lumotni `detail` ga
            qo'yishni so'raydi, lekin `ERROR_DETAIL_KEYS` (UI-SPEC §7.4)
            da RO'YXAT uchun kalit YO'Q (`channel_no`/`channel_name`
            birlikda). Shuning uchun u chaqiruvchiga alohida beriladi va
            u yerda JURNALGA yoziladi — allowlist zaiflashtirilmaydi.
    """
    root = _root(payload, expected="InputProxyChannelList")
    rows: list[ChannelRow] = []
    for channel in _children(root, "InputProxyChannel"):
        raw_id = _text(channel, "id")
        channel_no = _normalise_channel_id(raw_id) if raw_id is not None else None
        if channel_no is None:
            if skipped is not None:
                skipped.append(f"InputProxyChannel id={raw_id!r}")
            continue

        source_ip: str | None = None
        source_model: str | None = None
        for descriptor in _children(channel, "sourceInputPortDescriptor"):
            source_ip = _text(descriptor, "ipAddress")
            source_model = _text(descriptor, "model")
            break

        rows.append(
            ChannelRow(
                channel_no=channel_no,
                name=_text(channel, "name") or f"Kanal {channel_no:02d}",
                source_ip=source_ip,
                source_model=source_model,
            )
        )
    return rows


def parse_channel_status(payload: bytes | str) -> dict[int, bool]:
    """`<InputProxyChannelStatusList>` -> `{kanal_raqami: onlayn}`.

    `.../channels` bilan `id` bo'yicha juftlanadi (A.1; `homebridge-
    hikvision` ham aynan shu naqshni ishlatadi). Ro'yxatda BOR, lekin
    `online=false` bo'lgan kanal uchun kamera yozuvi BARIBIR yaratiladi
    (SC#2) — shuning uchun bu xarita xato emas, ATRIBUT beradi.
    """
    root = _root(payload, expected="InputProxyChannelStatusList")
    statuses: dict[int, bool] = {}
    for entry in _children(root, "InputProxyChannelStatus"):
        raw_id = _text(entry, "id")
        channel_no = _normalise_channel_id(raw_id) if raw_id is not None else None
        if channel_no is None:
            continue
        statuses[channel_no] = (_text(entry, "online") or "").lower() == "true"
    return statuses


def parse_admin_accesses(payload: bytes | str) -> dict[str, int]:
    """`<AdminAccessProtocolList>` -> `{"RTSP": 554, "HTTP": 80, ...}`.

    ⚠ FAQAT `enabled=true` YOZUVLAR. Real dumpda `DEV_MANAGE` yozuvida
      `<enabled>` UMUMAN YO'Q — ya'ni «bayroq yo'q» ni «yoqilgan» deb
      hisoblash o'chirilgan protokolni ochiq deb ko'rsatardi. Yo'qlik
      `false` bilan bir xil qaraladi.

    Bu funksiya A.2 ning «RTSP portini TAXMIN QILMANG» qoidasining
    manbai: 554 faqat FALLBACK va u ishlatilganda yozuvda
    `rtsp_port_assumed` belgisi qoladi (Pitfall 8).
    """
    root = _root(payload, expected="AdminAccessProtocolList")
    ports: dict[str, int] = {}
    for entry in _children(root, "AdminAccessProtocol"):
        if (_text(entry, "enabled") or "").lower() != "true":
            continue
        protocol = _text(entry, "protocol")
        raw_port = _text(entry, "portNo")
        if protocol is None or raw_port is None:
            continue
        try:
            ports[protocol.upper()] = int(raw_port)
        except ValueError:
            continue
    return ports


def parse_video_input_channels(payload: bytes | str) -> list[ChannelRow]:
    """`<VideoInputChannelList>` -> standalone IP-kamera yo'li (A.1, 2-qadam-B).

    ⚠ NVR'DA BU ENDPOINT AVTORITETLI EMAS va u bu yerda ATAYIN
      ishlatilmaydi: u NVR ning video-kirish SLOTLARINI sanaydi, ya'ni
      bo'sh slot ham «kanal» bo'lib chiqardi. 03-02 yozib olingan ikkala
      NVR dumpida ham bu endpoint uchun **403** qayd etilgan — ya'ni
      «`InputProxy` avtoritetli» xulosasi endi taxmin emas, O'LCHOV.

    `sourceInputPortDescriptor` bu javobda YO'Q: standalone kamerada
    «manba kamera» tushunchasi ham yo'q — qurilmaning o'zi manba.
    """
    root = _root(payload, expected="VideoInputChannelList")
    rows: list[ChannelRow] = []
    for entry in _children(root, "VideoInputChannel"):
        raw_id = _text(entry, "id")
        channel_no = _normalise_channel_id(raw_id) if raw_id is not None else None
        if channel_no is None:
            continue
        rows.append(
            ChannelRow(
                channel_no=channel_no,
                name=_text(entry, "name") or f"Kanal {channel_no:02d}",
            )
        )
    return rows
