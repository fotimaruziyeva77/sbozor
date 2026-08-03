"""RTSP URL fabrikasi — `{ch}01` / `{ch}02` raqamlash qoidasi (T-03-24, T-03-25).

=============================================================================
NEGA BU ALOHIDA, SOF FUNKSIYA SIFATIDA O'LCHANADI.

`cameras` da `rtsp_url` USTUNI YO'Q (03-03, `models/nvr.py` docstringi):
URL saqlanmaydi, HAR SAFAR hosil qilinadi. Ya'ni bu funksiya —
kashfiyot bilan jonli ko'rish orasidagi YAGONA manzil manbai, va uning
xatosi «kashfiyot yashil, kadr olish qora» ko'rinishida chiqadi
(`03-RESEARCH.md` Pitfall 8) — ya'ni eng kech sezilagan xato sinfida.

Funksiya tarmoqqa CHIQMAYDI, ya'ni uni ISAPI klientidan (03-05) MUSTAQIL
o'lchash mumkin va shu sababdan u shu rejaga, klientdan oldinga qo'yilgan.
=============================================================================

⚠ ENG MUHIM STRUKTURAVIY DA'VO — PAROL QABUL QILINMAYDI.
`rtsp://user:pass@host/...` shakli ISHLAYDI, lekin u parolni jurnalga,
`error_detail` jsonb'iga va go2rtc konfiguratsiyasiga ko'chirardi (T-03-24).
Himoya «parolni qo'shmang» degan kelishuv EMAS, IMZONING O'ZI: funksiya
parol parametrini umuman qabul qilmaydi, ya'ni uni qo'shish uchun avval
imzoni o'zgartirish kerak bo'ladi — va bu diffda ko'rinadi.
"""

from __future__ import annotations

import inspect

import pytest
from app.services import rtsp
from app.services.rtsp import new_stream_name, rtsp_url, stream_id

# ---------------------------------------------------------------------------
# Kanal raqamlash — `stream_id = channel_no * 100 + oqim`
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("channel_no", "substream", "expected"),
    [
        (1, False, 101),
        (1, True, 102),
        (7, False, 701),
        (7, True, 702),
        (16, False, 1601),
        (16, True, 1602),
        # Ikki xonali kanal chegarasi: 10 -> 1001 (10*100+1), 9 -> 901.
        # Aynan shu yerda "satr birlashtirish" xatosi ko'rinadi: `f"{ch}01"`
        # 10 uchun `1001` beradi va TO'G'RI, lekin `stream_id` arifmetikasi
        # bo'lmasa 100 dan katta kanalda ikkalasi ajralib ketardi.
        (9, False, 901),
        (10, False, 1001),
    ],
)
def test_stream_id_follows_the_channel_stream_rule(
    channel_no: int, substream: bool, expected: int
) -> None:
    """`{kanal}{oqim}`: 1 = asosiy, 2 = sub (`03-RESEARCH.md` A.2)."""
    assert stream_id(channel_no, substream=substream) == expected


@pytest.mark.parametrize(
    ("host", "port", "channel_no", "substream", "expected"),
    [
        ("192.168.1.64", 554, 1, False, "rtsp://192.168.1.64:554/Streaming/Channels/101"),
        ("192.168.1.64", 554, 1, True, "rtsp://192.168.1.64:554/Streaming/Channels/102"),
        # KASHF ETILGAN, standart bo'lmagan port — 554 qotirilgan bo'lsa
        # aynan shu holat qizaradi (`03-RESEARCH.md` A.2: portni TAXMIN
        # QILMANG).
        ("192.168.1.64", 10554, 16, False, "rtsp://192.168.1.64:10554/Streaming/Channels/1601"),
        # Hostname ham qabul qilinadi (sim compose tarmog'ida DNS nomi bilan).
        ("nvr-sim", 554, 3, True, "rtsp://nvr-sim:554/Streaming/Channels/302"),
    ],
)
def test_rtsp_url_is_derived_from_host_port_and_channel(
    host: str, port: int, channel_no: int, substream: bool, expected: str
) -> None:
    """URL uch qiymatdan HOSILA — saqlangan matn emas."""
    assert rtsp_url(host, port, channel_no, substream=substream) == expected


def test_rtsp_path_uses_capitalised_segments() -> None:
    """Yo'l `/Streaming/Channels/` — BOSH HARFLAR bilan.

    ⚠ ISAPI yo'li `/ISAPI/Streaming/channels/` (kichik `c`) va ikkalasi
      bir fazada, bir kod bazasida yashaydi. Ularni almashtirib yuborish
      eng oson va eng jimgina xato: NVR `404` beradi va sabab «kamera
      ishlamayapti» bo'lib ko'rinadi.
    """
    url = rtsp_url("192.168.1.64", 554, 1)

    assert "/Streaming/Channels/" in url
    assert "/ISAPI/" not in url


@pytest.mark.parametrize("channel_no", [0, -1, -100])
def test_non_positive_channel_is_rejected(channel_no: int) -> None:
    """`channel_no <= 0` — `ValueError`.

    `cameras.channel_no > 0` CHECK'i bilan bir xil chegara. Nol kanal
    `001` beradi va u hech qanday kameraga MOS KELMAYDI, lekin URL
    sifatida butunlay to'g'ri ko'rinardi.
    """
    with pytest.raises(ValueError, match="channel_no"):
        rtsp_url("192.168.1.64", 554, channel_no)


def test_stream_id_rejects_non_positive_channel_too() -> None:
    """Chegara IKKALA ommaviy funksiyada ham bor.

    Faqat `rtsp_url` tekshirsa `stream_id` ni to'g'ridan-to'g'ri
    chaqiradigan kod (03-05 dagi sub-oqim tekshiruvi) chegarasiz qolardi.
    """
    with pytest.raises(ValueError, match="channel_no"):
        stream_id(0)


# ---------------------------------------------------------------------------
# T-03-24 — parol strukturaviy ravishda kira olmaydi
# ---------------------------------------------------------------------------


def test_rtsp_url_signature_has_no_credential_parameter() -> None:
    """Imzoda parol/login parametri UMUMAN yo'q (T-03-24).

    ⚠ Bu test kodni emas, KONTRAKTNI qo'riqlaydi. Kimdir «qulaylik uchun»
      `rtsp_url(..., password=...)` qo'shsa u shu yerda qizaradi va diffda
      sababi ko'rinadi.
    """
    parameters = set(inspect.signature(rtsp_url).parameters)

    assert not parameters & {"password", "username", "user", "credentials", "auth"}


def test_generated_url_contains_no_userinfo_section() -> None:
    """Hosil qilingan URL'da `@` (userinfo ajratuvchisi) yo'q — nazorat bandi.

    Imzo testi yolg'iz o'zi kifoya emas: parol `host` argumenti ichida
    (`user:pass@192.168.1.64`) ham o'tib ketishi mumkin edi.
    """
    assert "@" not in rtsp_url("192.168.1.64", 554, 1)


# ---------------------------------------------------------------------------
# T-03-25 — oqim nomi ma'nosiz
# ---------------------------------------------------------------------------


def test_new_stream_name_is_opaque_and_unique() -> None:
    """`cam_<uuid4>`: har chaqiruvda boshqa, hech qanday ma'no yo'q (D.13).

    Nom go2rtc URL'ida KO'RINADI. Ma'noli nom (`karmana_cam_03`) bozor
    nomini, bozorlar sonini va nomlanish sxemasini oshkor qilardi —
    ya'ni URL'ning o'zi razvedka manbai bo'lardi.
    """
    first = new_stream_name()
    second = new_stream_name()

    assert first.startswith("cam_")
    assert first != second
    # `uuid4().hex` — 32 belgi + `cam_` prefiksi.
    assert len(first) == len("cam_") + 32


def test_new_stream_name_takes_no_arguments() -> None:
    """Nom hosil qilish HECH QANDAY kontekst olmaydi.

    Argument bo'lsa (masalan `market_id` yoki `channel_no`) uni nomga
    qo'shish vasvasasi paydo bo'lardi — va aynan shu T-03-25 ning o'zi.
    Imzoning bo'shligi bu vasvasani strukturaviy ravishda yo'q qiladi.
    """
    assert inspect.signature(new_stream_name).parameters == {}


def test_module_exports_exactly_the_documented_contract() -> None:
    """`__all__` — 03-05/03-06 tayanadigan uchta nom."""
    assert set(rtsp.__all__) == {"new_stream_name", "rtsp_url", "stream_id"}
