"""RTSP URL fabrikasi — Hikvision `{kanal}{oqim}` raqamlash qoidasi.

Sof funksiyalar moduli (`sbozor_core/periods.py` shakli): tarmoqqa
chiqmaydi, bazaga tegmaydi, holat saqlamaydi.

=============================================================================
UCHTA NUANCE — UCHALASI HAM ALOHIDA XATO SINFI.

(a) YO'L BOSH HARFLAR BILAN: `/Streaming/Channels/`.
    ISAPI yo'li esa `/ISAPI/Streaming/channels/` — KICHIK `c` bilan.
    Ikkalasi bir fazada, bir kod bazasida yashaydi va ularni almashtirib
    yuborish eng oson xato: NVR `404` beradi, sabab esa «kamera
    ishlamayapti» bo'lib ko'rinadi. RTSP yo'li ISAPI yo'li EMAS.

(b) PAROL URL'GA HECH QACHON KIRMAYDI.
    `rtsp://user:pass@host/...` shakli texnik jihatdan ishlaydi, LEKIN u
    parolni jurnalga, `nvr_discovery_runs.error_detail` jsonb'iga va
    go2rtc konfiguratsiya faylига ko'chirardi (T-03-24). Parol alohida,
    Fernet bilan shifrlangan holda turadi va faqat go2rtc konfiguratsiyasi
    hosil qilinayotganda ochiladi.
    ⚠ Himoya kelishuv emas, STRUKTURA: funksiya parol parametrini UMUMAN
      qabul qilmaydi. Uni qo'shish uchun avval imzoni o'zgartirish kerak
      va bu diffda ko'rinadi (`test_rtsp_url.py` imzoni tekshiradi).

(c) URL SAQLANMAYDI.
    `cameras` da `rtsp_url` ustuni YO'Q (03-03). NVR ning IP'si yoki
    RTSP porti o'zgarganda BITTA qator (`nvr_devices`) yangilanadi, 25 ta
    kamera URL'i emas — va bittasi unutilib qolishi mumkin bo'lgan holat
    umuman tug'ilmaydi.
=============================================================================

⚠ PORT BU YERGA KASHF ETILGAN HOLDA KELADI.
Funksiya `port` ni ARGUMENT sifatida oladi va 554 ni o'zi taxmin
QILMAYDI. Kashfiyot uni `/ISAPI/Security/adminAccesses` javobidan oladi
(`03-RESEARCH.md` A.2); topilmasa chaqiruvchi 554 ni beradi va qatorni
`rtsp_port_assumed = true` bilan belgilaydi. Standart qiymatni shu yerga
qo'yish o'sha bayroqni ma'nosiz qilardi: «taxmin qilindi» fakti
yo'qolardi va nosozlik «kashfiyot yashil, kadr olish qora» ko'rinishida
chiqardi (Pitfall 8).
"""

from __future__ import annotations

from uuid import uuid4

__all__ = ["new_stream_name", "rtsp_url", "stream_id"]

_MAIN_STREAM = 1
"""Asosiy (main) oqimning indeksi — `{ch}01`."""

_SUB_STREAM = 2
"""Sub-oqim indeksi — `{ch}02`.

Har kanalda mavjudligi KAFOLATLANMAGAN: `GET /ISAPI/Streaming/channels/
{ch}02` `404`/`400` bersa sub-oqim yo'q va `cameras.has_substream`
`false` ga tushadi.
"""

_CHANNEL_MULTIPLIER = 100
"""`stream_id = channel_no * 100 + oqim`.

Arifmetika, satr birlashtirish EMAS. `f"{channel_no}0{stream}"` bir xil
natija berardi, lekin 100 dan katta kanalda ikkalasi ajralib ketardi va
xato faqat katta NVR'da (yoki `InputProxy` orqali ulangan kaskadda)
chiqardi.
"""

_STREAM_NAME_PREFIX = "cam_"


def stream_id(channel_no: int, *, substream: bool = False) -> int:
    """Kanal raqamidan Hikvision oqim identifikatorini hisoblaydi.

    `stream_id(1)` -> `101` (kanal 1, asosiy oqim);
    `stream_id(1, substream=True)` -> `102`;
    `stream_id(16)` -> `1601`.

    Args:
        channel_no: NVR dagi kanal raqami (1 dan boshlanadi).
        substream: `True` bo'lsa sub-oqim (`{ch}02`).

    Raises:
        ValueError: `channel_no` musbat bo'lmasa. Chegara `cameras.
            channel_no > 0` CHECK'i bilan bir xil: nol kanal `001` beradi
            va u hech qanday kameraga mos kelmaydi, lekin URL sifatida
            butunlay to'g'ri ko'rinardi.
    """
    if channel_no <= 0:
        raise ValueError(f"channel_no musbat bo'lishi kerak, berilgani: {channel_no}")
    return channel_no * _CHANNEL_MULTIPLIER + (_SUB_STREAM if substream else _MAIN_STREAM)


def rtsp_url(host: str, port: int, channel_no: int, *, substream: bool = False) -> str:
    """Kamera oqimining RTSP manzilini hosil qiladi.

    ⚠ REKVIZIT PARAMETRI ATAYIN YO'Q (modul docstringi, (b) bandi).

    Args:
        host: `nvr_devices.host` — IP yoki hostname.
        port: `nvr_devices.rtsp_port` — KASHF ETILGAN qiymat.
        channel_no: kanal raqami.
        substream: `True` bo'lsa sub-oqim URL'i.

    Returns:
        `rtsp://<host>:<port>/Streaming/Channels/<stream_id>`
    """
    return f"rtsp://{host}:{port}/Streaming/Channels/{stream_id(channel_no, substream=substream)}"


def new_stream_name() -> str:
    """go2rtc uchun MA'NOSIZ oqim nomi: `cam_<uuid4>`.

    ⚠ NOM URL'DA KO'RINADI (`/api/frame.jpeg?src=<nom>`), ya'ni u tashqi
      kuzatuvchiga ko'rinadigan yagona identifikator. Ma'noli nom
      (`karmana_cam_03`) bozor nomini, bozorlar sonini va nomlanish
      sxemasini oshkor qilardi — URL'ning o'zi razvedka manbai bo'lardi
      (T-03-25, D.13).

    Shuning uchun funksiya HECH QANDAY argument olmaydi: kontekst
    berilsa uni nomga qo'shish vasvasasi paydo bo'lardi.

    Nom GLOBAL noyob bo'lishi kerak (`uq_cameras_stream_name` — go2rtc
    bitta jarayon va uning nomlar fazosi barcha bozorlar uchun umumiy),
    shuning uchun `uuid4` — sanagich yoki bozorga bog'liq prefiks emas.
    """
    return f"{_STREAM_NAME_PREFIX}{uuid4().hex}"
