"""ISAPI parseri — YOZIB OLINGAN DUMPLAR ustida, `respx` SIZ (Pitfall 2, Pitfall 4).

=============================================================================
NEGA `respx` KERAK EMAS.

Parser — SOF FUNKSIYA: kirish baytlar, chiqish dataclass. Uni HTTP mock
ortiga qo'yish transport qatlamini o'lchashga majbur qilardi, holbuki bu
yerdagi da'vo transport haqida emas. HTTP qatlami `tests/integration/
test_nvr_errors.py` da, HAQIQIY TCP orqali o'lchanadi (`03-RESEARCH.md`
B.6: «respx bilan qurilgan test 'kod XML ni to'g'ri parse qiladi' ni
isbotlaydi, 'kod NVR bilan gaplasha oladi' ni EMAS»).

=============================================================================
KIRISH — 03-02 YARATGAN FIXTURE FAYLLARI, QO'LDA YOZILGAN XML EMAS.

Bu Pitfall 4 (`simulator-confirms-itself`) ga qarshi IKKINCHI QATLAM:
parser ham, simulyator ham AYNAN BIR XIL haqiqiy XML ustida o'lchanadi.
Agar bu yerda qo'lda yozilgan «shunga o'xshash» XML bo'lganda, test faqat
«kod o'z taxminiga mos» ekanini isbotlardi — CI yashil, real qurilma qora.

Fixture'larning O'ZI (kelib chiqishi, namespace'i, manba izohi)
`tests/unit/test_sim_fixtures.py` da qulflangan. Bu fayl ularni QAYTA
tekshirmaydi — u ularni ISHLATADI.
=============================================================================
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from app.services.isapi.errors import NvrError
from app.services.isapi.parser import (
    MAX_RESPONSE_BYTES,
    local_name,
    parse_admin_accesses,
    parse_channel_status,
    parse_device_info,
    parse_input_proxy_channels,
    parse_video_input_channels,
)

if TYPE_CHECKING:
    from collections.abc import Callable

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES_DIR = REPO_ROOT / "services" / "nvr-sim" / "fixtures"

_XMLNS_RE = re.compile(r'\s+xmlns="[^"]*"')


def _fixture(name: str) -> str:
    """Fixture matni — izohi bilan birga (izoh XML uchun ahamiyatsiz)."""
    path = FIXTURES_DIR / name
    assert path.is_file(), f"fixture topilmadi: {path}"
    return path.read_text(encoding="utf-8")


def _strip_namespaces(document: str) -> str:
    """`xmlns="..."` e'lonlarini olib tashlaydi — Pitfall 2 ning NAZORAT holati.

    Bu SUN'IY hujjat va u ataylab sun'iy: real Hikvision har doim
    namespace yuboradi. Uning vazifasi bitta — sabotaj (`local_name` ->
    `lambda tag: tag`) da'volarning QAYSI BIRINI qizartirishini ajratish.
    Namespace'siz variant YASHIL qolishi, namespace'li variant QIZARISHI
    kerak; ikkalasi ham qizarsa test namespace'ni emas, boshqa narsani
    o'lchayotgan bo'lardi.
    """
    return _XMLNS_RE.sub("", document)


# ---------------------------------------------------------------------------
# `local_name` — butun namespace strategiyasining yagona nuqtasi
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("tag", "expected"),
    [
        ("{http://www.hikvision.com/ver20/XMLSchema}deviceType", "deviceType"),
        ("{http://www.isapi.org/ver20/XMLSchema}InputProxyChannelList", "InputProxyChannelList"),
        ("deviceType", "deviceType"),
        ("", ""),
    ],
)
def test_local_name_strips_any_namespace(tag: str, expected: str) -> None:
    """Prefiks bo'lsa ham, bo'lmasa ham natija bir xil qoidadan chiqadi."""
    assert local_name(tag) == expected


# ---------------------------------------------------------------------------
# Pitfall 2 — REJADA NOMMA-NOM TALAB QILINGAN TEST
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("variant", ["namespaced", "stripped"])
def test_namespaced_xml_parses_the_same_as_plain_xml(variant: str) -> None:
    """`deviceType` namespace BILAN ham, namespace'SIZ ham topiladi (Pitfall 2).

    ⚠ ALOMAT: namespace e'tiborsiz qoldirilsa `find("deviceType")` `None`
    qaytaradi, kashfiyot «ulanish muvaffaqiyatli, lekin 0 kanal» deydi va
    HECH QANDAY XATO KO'RINMAYDI. Bu eng ko'p uchraydigan integratsiya
    xatosi.

    ⚠ SABOTAJ CHEGARASI: `local_name` ni `lambda tag: tag` ga
    almashtirganda `[namespaced]` QIZARADI, `[stripped]` esa YASHIL
    qoladi — ya'ni test haqiqatan namespace'ni o'lchayotgani shu bilan
    isbotlanadi.
    """
    document = _fixture("DS-7616NI-K2-deviceInfo.xml")
    if variant == "stripped":
        document = _strip_namespaces(document)
        assert "xmlns=" not in document, "nazorat: namespace olib tashlanmadi"
    else:
        assert 'xmlns="http://www.hikvision.com/ver20/XMLSchema"' in document

    device = parse_device_info(document)

    assert device.model == "DS-7616NI-K2"
    assert device.device_type == "NVR"
    assert device.manufacturer == "hikvision"
    assert device.serial_number == "DS-7616NI-K20000000000CCRRG00000000WCVU"
    assert device.firmware_version == "V4.74.210"


def test_the_second_isapi_namespace_is_also_understood() -> None:
    """`DS-7732NI-M4` `isapi.org` namespace'ida — `hikvision.com` da EMAS.

    03-02 ning topilmasi: reja ham, tadqiqot ham faqat `hikvision.com` ni
    kutgan edi. Bitta namespace'ni qotirib qo'yish ham YETARLI EMAS.
    """
    document = _fixture("DS-7732NI-M4-inputProxyChannels.xml")
    assert 'xmlns="http://www.isapi.org/ver20/XMLSchema"' in document

    rows = parse_input_proxy_channels(document)

    assert [row.channel_no for row in rows] == list(range(1, 19))


# ---------------------------------------------------------------------------
# `@size` — real qurilma o'z atributiga ZID qiymat yuboradi
# ---------------------------------------------------------------------------


def test_channel_count_comes_from_elements_not_from_the_size_attribute() -> None:
    """`size="14"`, elementlar esa 18 ta — ELEMENTLAR yutadi (03-02 topilmasi).

    Bu qo'lda yozilgan XML da HECH QACHON paydo bo'lmasdi: hech kim o'z
    ro'yxatiga zid `size` yozmaydi. Faqat yozib olingan dump buni beradi.
    """
    document = _fixture("DS-7732NI-M4-inputProxyChannels.xml")
    assert 'size="14"' in document, "fixture o'zgargan — `size` atributi yo'qolgan"

    rows = parse_input_proxy_channels(document)

    assert len(rows) == 18, f"`size` atributiga ishonildi: {len(rows)} qator"


def test_input_proxy_rows_carry_the_channel_number_and_the_source_camera() -> None:
    """Har qatorda BUTUN SON kanal raqami va manba kamera IP'si bor (A.1).

    `source_ip` va `source_model` — KUZATILADIGAN atributlar (A.4): kamera
    fizik almashtirilganda ular o'zgaradi va `audit_log` ga tushadi.
    """
    rows = parse_input_proxy_channels(_fixture("DS-7616NI-K2-inputProxyChannels.xml"))

    assert len(rows) == 6
    assert [row.channel_no for row in rows] == [1, 2, 3, 4, 5, 6]
    assert all(isinstance(row.channel_no, int) for row in rows)
    assert all(row.source_ip for row in rows), [row.source_ip for row in rows]
    assert rows[0].name == "tagahoov"
    assert rows[0].source_ip == "1.0.0.208"
    assert rows[0].source_model == "DS-2CD2387G2-LSU/SL"


# ---------------------------------------------------------------------------
# Kanal raqamining normallashuvi
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw_id", "expected"),
    [
        ("1", 1),
        ("6", 6),
        ("101", 1),  # `{kanal}{oqim}` shakli — asosiy oqim
        ("102", 1),  # `{kanal}{oqim}` shakli — sub-oqim
        ("1601", 16),
        ("25", 25),
    ],
)
def test_channel_id_is_normalised_from_both_firmware_shapes(raw_id: str, expected: int) -> None:
    """Ba'zi firmware `1`, ba'zisi `101` yuboradi — ikkalasi ham kanal 1."""
    document = (
        '<InputProxyChannelList version="1.0" xmlns="http://www.hikvision.com/ver20/XMLSchema">'
        f"<InputProxyChannel><id>{raw_id}</id><name>X</name></InputProxyChannel>"
        "</InputProxyChannelList>"
    )
    assert [row.channel_no for row in parse_input_proxy_channels(document)] == [expected]


@pytest.mark.parametrize("raw_id", ["0", "-3", "abc", ""])
def test_unparseable_channel_is_skipped_and_reported_not_hidden(raw_id: str) -> None:
    """Bitta g'alati kanal BUTUN kashfiyotni to'xtatmaydi, lekin JIM ham qolmaydi.

    24 ta sog'lom kamera bittasi tufayli yo'qolishi mumkin emas —
    shuning uchun `NvrError` ko'tarilmaydi. Lekin o'tkazib yuborish
    KO'RINADI: chaqiruvchi `skipped` ro'yxatini beradi va uni jurnalga
    yozadi (`discovery.py`).
    """
    document = (
        '<InputProxyChannelList xmlns="http://www.hikvision.com/ver20/XMLSchema">'
        f"<InputProxyChannel><id>{raw_id}</id><name>Buzuq</name></InputProxyChannel>"
        "<InputProxyChannel><id>2</id><name>Sog'lom</name></InputProxyChannel>"
        "</InputProxyChannelList>"
    )
    skipped: list[str] = []

    rows = parse_input_proxy_channels(document, skipped=skipped)

    assert [row.channel_no for row in rows] == [2], "sog'lom kanal ham yo'qoldi"
    assert len(skipped) == 1, f"o'tkazib yuborish qayd etilmadi: {skipped}"
    assert "InputProxyChannel" in skipped[0]


# ---------------------------------------------------------------------------
# Kanal holati va port kashfiyoti
# ---------------------------------------------------------------------------


def test_channel_status_maps_channel_number_to_online_flag() -> None:
    """`.../channels/status` -> `{3: False, 1: True, ...}` (A.1).

    ⚠ MANBA: bu hujjat yuqori oqim dumplarida YO'Q va uning shakli
    `03-RESEARCH.md` A.1 dan olingan TAXMIN (`services/nvr-sim/sim/
    isapi.py::_input_proxy_status` da ham aynan shunday belgilangan).
    Shuning uchun bu yerdagi XML sim BILAN BIR XIL manbadan keladi va
    ikkalasi birga o'zgaradi.
    """
    document = (
        '<InputProxyChannelStatusList version="1.0" '
        'xmlns="http://www.hikvision.com/ver20/XMLSchema">'
        "<InputProxyChannelStatus><id>1</id><online>true</online></InputProxyChannelStatus>"
        "<InputProxyChannelStatus><id>3</id><online>false</online></InputProxyChannelStatus>"
        "<InputProxyChannelStatus><id>7</id><online>FALSE</online></InputProxyChannelStatus>"
        "</InputProxyChannelStatusList>"
    )

    assert parse_channel_status(document) == {1: True, 3: False, 7: False}


def test_admin_accesses_returns_only_enabled_protocols() -> None:
    """RTSP porti KASHF ETILADI (A.2) va `enabled` bo'lmagan yozuv OLINMAYDI.

    ⚠ Real dumpda `DEV_MANAGE` yozuvida `<enabled>` UMUMAN YO'Q. «Bayroq
    yo'q» ni «yoqilgan» deb hisoblash o'chirilgan protokolni ochiq deb
    ko'rsatardi — bu qo'lda yozilgan fixture'da uchramaydigan holat.
    """
    ports = parse_admin_accesses(_fixture("DS-7616NI-K2-adminAccesses.xml"))

    assert ports == {"HTTP": 80, "RTSP": 554, "HTTPS": 443}
    assert "DEV_MANAGE" not in ports, "`<enabled>` siz yozuv ham olindi"


def test_video_input_channels_parse_the_standalone_camera_dump() -> None:
    """IP-kamera yo'li (A.1 2-qadam-B): bitta kanal, `sourceInputPortDescriptor` YO'Q."""
    rows = parse_video_input_channels(_fixture("DS-2CD2346G2-ISU-videoInputChannels.xml"))

    assert len(rows) == 1
    assert rows[0].channel_no == 1
    assert rows[0].name == "Atelier"
    assert rows[0].source_ip is None


# ---------------------------------------------------------------------------
# T-03-34 — parser HECH QACHON jimgina bo'sh natija bermaydi
# ---------------------------------------------------------------------------

_PARSERS: dict[str, Callable[[str], object]] = {
    "device_info": parse_device_info,
    "input_proxy": parse_input_proxy_channels,
    "channel_status": parse_channel_status,
    "admin_accesses": parse_admin_accesses,
    "video_inputs": parse_video_input_channels,
}


@pytest.mark.parametrize("parser_name", sorted(_PARSERS))
@pytest.mark.parametrize(
    ("payload", "label"),
    [
        ("", "bo'sh javob"),
        ("<InputProxyChannelList>", "yopilmagan teg"),
        ("<html><body>401 Unauthorized</body></html>", "HTML login sahifasi"),
        (
            '<ResponseStatus xmlns="http://www.hikvision.com/ver20/XMLSchema">'
            "<statusCode>6</statusCode></ResponseStatus>",
            "Hikvision xato tanasi",
        ),
    ],
)
def test_broken_or_unexpected_xml_raises_instead_of_returning_empty(
    parser_name: str, payload: str, label: str
) -> None:
    """«0 kanal topildi» HECH QACHON sababsiz bo'lmaydi (T-03-34).

    Bo'sh natija va xato natija ORASIDAGI FARQ yo'qolsa, kashfiyot
    yashil bo'lib turaverardi va admin nima bo'lganini hech qayerdan
    bilmasdi — bu Repudiation, xato emas.
    """
    with pytest.raises(NvrError) as excinfo:
        _PARSERS[parser_name](payload)

    assert excinfo.value.code == "nvr_isapi_unavailable", label
    assert "raw" in excinfo.value.detail, f"{label}: tashxis uchun xom javob saqlanmadi"


def test_oversized_response_is_rejected_before_parsing() -> None:
    """Buzilgan qurilmaning MEGABAYTLI javobi bazaga ham, xotiraga ham tushmaydi."""
    payload = "<DeviceInfo>" + ("x" * (MAX_RESPONSE_BYTES + 1)) + "</DeviceInfo>"

    with pytest.raises(NvrError) as excinfo:
        parse_device_info(payload)

    assert excinfo.value.code == "nvr_isapi_unavailable"


def test_parser_accepts_bytes_as_well_as_text() -> None:
    """`httpx` `response.content` ni BAYT sifatida beradi — o'sha yo'l ham ishlaydi."""
    document = _fixture("DS-7616NI-K2-deviceInfo.xml").encode("utf-8")

    assert parse_device_info(document).model == "DS-7616NI-K2"
