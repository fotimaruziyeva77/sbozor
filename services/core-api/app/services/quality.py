"""Kadr sifati — bayt oqimidan verdikt va `light_mode` (CAM-06, D-12/D-13/D-14/D-15).

Sof funksiyalar moduli (`rtsp.py`, `live_source.py` bilan bir xil shakl):
tarmoqqa chiqmaydi, bazaga tegmaydi, holat saqlamaydi va `Settings` ni
BILMAYDI — chegaralar unga argument sifatida kiradi.

=============================================================================
UCH MAJBURIYAT — UCHALASI HAM JIM NOSOZLIKKA QARSHI.

⛔ 1. `ImageFile.LOAD_TRUNCATED_IMAGES` `False` BO'LIB QOLISHI SHART.

   Bu JARAYON DARAJASIDAGI global bayroq va uni istalgan bog'liqlik
   o'rnatishi mumkin. `True` bo'lsa kesilgan JPEG JIMGINA dekodlanadi —
   yetib kelmagan qismi kulrang bo'lib to'ldiriladi — va buzuq detektori
   BUTUNLAY o'chib qoladi. Hech qanday istisno chiqmaydi, hech qanday
   verdikt testi qizarmaydi: kadr «yaroqli» bo'lib bazaga tushadi va
   billing uni qabul qiladi.

   Aynan shuning uchun himoya kod ichida emas, GLOBAL HOLATNI O'QIYDIGAN
   darvozada: `test_quality_filter.py::test_truncated_images_flag_is_false`.

⛔ 2. `dark` IKKI SHARTLI (D-14).

   `dark := mean < DARK_MEAN VA stddev < DARK_STDDEV`. Yagona shartli
   qoida TAQIQLANGAN va sabab mahsulotda: qishki 06:00 tong kadri
   qonuniy ravishda qorong'i bo'ladi (`mean≈30`), lekin unda TUZILMA bor
   (`stddev>25`) — u YAROQLI dalil. Faqat `mean` ga tayangan filtr bunday
   kadrlarni OYLAB rad etardi va nosozlik faqat tushum tahlilida, oylar
   keyin ko'rinardi. Bu — kunlik hisobning jimgina yo'qolishi.

   `live_source.py:100-106` uslubida: bu satrning kodda ikkala shart
   bilan turishi darvoza ostida (`test_mean_30_stddev_28_is_ok_because_
   it_has_structure` va uning yetkazilgan chegaralardagi juftligi).

⛔ 3. VERDIKT YOZISH PAYTIDA QO'YILADI, HISOBLANMAYDI.

   `QUALITY_THRESHOLDS_VERSION` verdikt QAYSI chegara to'plami bilan
   qo'yilganini yozadi. Agar verdikt chegaralardan hisoblanadigan
   bo'lganda, chegarani o'zgartirish O'TMISHDAGI kadrlarning billing
   yaroqliligini RETROAKTIV o'zgartirardi — allaqachon yozilgan hisoblar
   asossiz bo'lib qolardi (§C.7, BILL-02/AI-02 o'zgarmaslik falsafasi).
=============================================================================

⚠ O'LCHOVLARNING O'ZI QAYTARILADI, faqat verdikt emas (D-15). `mean`,
  `stddev`, `saturation`, `width`, `height`, `size_bytes` — hammasi
  `snapshots` ga yoziladi, ya'ni real Karmana kadrlari kelganda chegaralar
  SQL SO'ROVI bilan sozlanadi, QAYTA KADR OLISH bilan emas. Chegara
  raqamlari shu sababdan ATAYIN LOW confidence: qoidaning SHAKLI
  ma'lumotsiz ham himoyalanadi, raqamlar esa taqsimotdan chiqariladi.

⚠ `opencv` BU FAZADA YO'Q (D-13). `Pillow` uchala hodisani ham beradi va u
  allaqachon retention siqishi uchun kerak — ya'ni yangi bog'liqlik nolga
  teng. `opencv-python-headless` cv-service ning (5-faza) bog'liqligi va
  uni bir faza oldin ochish ~70 MB image o'sishi demakdir.
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Final

import structlog
from PIL import Image, ImageFile, ImageStat, UnidentifiedImageError

__all__ = [
    "LIGHT_DAY",
    "LIGHT_IR_NIGHT",
    "LIGHT_LOW_LIGHT",
    "LIGHT_MODES",
    "LIGHT_UNKNOWN",
    "QUALITY_THRESHOLDS_VERSION",
    "QUALITY_VERDICTS",
    "REASON_BLANK",
    "REASON_DARK",
    "REASON_DECODE_FAILED",
    "REASON_NOT_JPEG",
    "REASON_OK",
    "REASON_SIZE_ABOVE_CEILING",
    "REASON_SIZE_BELOW_FLOOR",
    "REASON_TRUNCATED",
    "VERDICT_BLANK",
    "VERDICT_CORRUPT",
    "VERDICT_DARK",
    "VERDICT_OK",
    "QualityReport",
    "QualityThresholds",
    "analyze",
]

log = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# GLOBAL Pillow holati — ATAYIN aniq o'rnatiladi, standartga TAYANILMAYDI
# ---------------------------------------------------------------------------

MAX_IMAGE_PIXELS: Final[int] = 50_000_000
"""Dekompressiya bombasi shifti (T-04-24, ASVS V12.1).

Buzilgan yoki soxta NVR sarlavhasida ulkan o'lcham e'lon qilingan JPEG
yuborishi mumkin: 8 MiB li tana 100 000 x 100 000 piksel deb e'lon qilinsa
Pillow uni ochishga urinib butun konteynerning xotirasini yeb qo'yardi.

50 MP — 4K kadrdan (8,3 MP) olti barobar keng va 12 MP li kameradan ham
yuqori, ya'ni haqiqiy kadr hech qachon bu chegaraga urilmaydi. Pillow ning
o'z standarti 89 478 485 (89 MP) — biz uni PASAYTIRAMIZ, hech qachon
ko'tarmaymiz.

⚠ QIYMAT ANIQ O'RNATILADI, standartga TAYANILMAYDI: standart Pillow
  versiyasi bilan o'zgarishi mumkin va `None` ga tushishi himoyani
  BUTUNLAY o'chirardi. Darvoza — `test_max_image_pixels_is_bounded`.
"""

Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS

# ⚠ `ImageFile.LOAD_TRUNCATED_IMAGES` BU YERDA O'RNATILMAYDI — u Pillow ning
#   standarti bo'yicha allaqachon `False` (o'lchandi 2026-08-04, Pillow
#   12.3.0). Uni bu yerda `False` ga «o'rnatish» himoyani KUCHSIZLANTIRARDI:
#   import tartibi tasodifiy, ya'ni bizdan KEYIN yuklangan bog'liqlik uni
#   baribir `True` qilib qo'yardi va biz «o'rnatdik» degan yolg'on
#   ishonchda qolardik. Yagona ishonchli himoya — HOLATNI O'QIYDIGAN test.


# ---------------------------------------------------------------------------
# Verdikt va yorug'lik rejimi konstantalari
# ---------------------------------------------------------------------------

VERDICT_OK: Final[str] = "ok"
"""Kadr yaroqli — dalil zanjiriga kiradi va `is_billable = true` bo'ladi."""

VERDICT_DARK: Final[str] = "dark"
"""Qorong'i VA tuzilmasiz — yorug'lik yetishmaydi (IR yoritgich o'chgan).

⚠ IKKI SHARTLI (D-14, modul docstringi 2-majburiyat).
"""

VERDICT_BLANK: Final[str] = "blank"
"""Axborot yo'q — linza yopilgan, signal yo'qolgan, muzlagan kulrang kadr.

`mean` dan QAT'I NAZAR: yorug'lik normal bo'lgan bir xil rangli kadr ham
`blank` (MediaMTX 9101 yo'li — `YAVG 126, YLOW=YHIGH=126`).
"""

VERDICT_CORRUPT: Final[str] = "corrupt"
"""O'lchab bo'lmadi — tana JPEG emas, kesilgan yoki chegaradan tashqarida."""

QUALITY_VERDICTS: Final[tuple[str, ...]] = (
    VERDICT_OK,
    VERDICT_DARK,
    VERDICT_BLANK,
    VERDICT_CORRUPT,
)
"""Reyestr TARTIBLANGAN (`isapi/errors.py::NVR_ERROR_CODES` bilan bir xil qaror).

Qiymatlar `sbozor_core.enums::SnapshotQuality` bilan AYNAN mos bo'lishi
kerak. Moslik BU YERDA tekshirilmaydi va bu ataylab: `04-03` (enum va
migratsiya) shu reja bilan BIR TO'LQINDA ishlaydi, ya'ni bugun import
qilish to'lqin ichida bog'liqlik yaratardi. Moslik `04-05` da (repozitoriy
qatlamida) bitta test bilan qulflanadi.
"""

LIGHT_DAY: Final[str] = "day"
LIGHT_LOW_LIGHT: Final[str] = "low_light"
LIGHT_IR_NIGHT: Final[str] = "ir_night"
LIGHT_UNKNOWN: Final[str] = "unknown"

LIGHT_MODES: Final[tuple[str, ...]] = (
    LIGHT_DAY,
    LIGHT_LOW_LIGHT,
    LIGHT_IR_NIGHT,
    LIGHT_UNKNOWN,
)
"""`light_mode` — SUPERSET, `quality_verdict` ning dublikati EMAS (D-12).

U kameraning YORUG'LIK REJIMINI yozadi va BILLING QARORIGA KIRMAYDI: IR
tundagi kadr to'liq yaroqli dalil. Qiymati 5-fazada (dataset `light_mode`
bo'yicha muvozanatlanadi) va 8-fazada (aniqlik hisoboti kesimi) ochiladi.
Aks holda tizim tunda yig'ilgan pattani asossiz rad etardi.
"""


# ---------------------------------------------------------------------------
# Rad etish sababi — verdiktdan ALOHIDA o'lcham
# ---------------------------------------------------------------------------

REASON_OK: Final[str] = "ok"
REASON_SIZE_BELOW_FLOOR: Final[str] = "size_below_floor"
REASON_SIZE_ABOVE_CEILING: Final[str] = "size_above_ceiling"
REASON_NOT_JPEG: Final[str] = "not_a_jpeg"
REASON_TRUNCATED: Final[str] = "missing_end_of_image"
REASON_DECODE_FAILED: Final[str] = "decode_failed"
REASON_BLANK: Final[str] = "no_structure"
REASON_DARK: Final[str] = "low_light_and_no_structure"
"""QAYSI darvoza qaror qabul qilgani — `verdict` dan ALOHIDA maydon.

IKKI mustaqil sabab:

1. **Operator diagnostikasi.** «corrupt» yolg'iz o'zi hech nima aytmaydi.
   `not_a_jpeg` — go2rtc/NVR xato sahifasi qaytaryapti (sozlama muammosi);
   `missing_end_of_image` — tarmoq uzilyapti (tunnel muammosi);
   `size_below_floor` — javob umuman bo'sh. Uchtasining yechimi UCH XIL
   joyda va ularni bitta verdiktga yig'ish adminni noto'g'ri joyni
   qidirishga majbur qilardi (`discovery.py:112-121` bilan bir xil
   mulohaza).

2. **Darvozalarning MUSTAQIL o'lchanishi.** Faqat verdikt qaytarilganda
   magic-bayt qadamini olib tashlash HECH QANDAY testni qizartirmasdi:
   JPEG bo'lmagan tana keyingi qadamda baribir `corrupt` bo'lardi, faqat
   BOSHQA sabab bilan. Ya'ni darvoza «bor» deb hisoblanardi, aslida esa
   uni o'chirib qo'yish mumkin edi. Sabab maydoni har qadamni alohida
   o'lchanadigan qiladi.
"""


QUALITY_THRESHOLDS_VERSION: Final[int] = 1
"""Chegara to'plamining versiyasi — har kadrga YOZILADI (§C.7).

Chegaralar D-15 bo'yicha real ma'lumot kelganda o'zgaradi. O'sha kuni bu
son OSHIRILADI, shunda «bu kadr qaysi qoida bilan baholangan?» savoliga
javob bazadan olinadi. Usiz chegarani o'zgartirish o'tmishni jimgina
qayta yozardi.
"""


@dataclass(frozen=True, slots=True)
class QualityThresholds:
    """Filtrning barcha raqamlari — BITTA obyektda, STANDART QIYMATSIZ.

    ⚠ STANDART QIYMAT ATAYIN YO'Q. Ular `Settings` dan keladi (D-15), ya'ni
      bu modul chegaralarni BILMAYDI. Standart berilsa `Settings` dagi
      qiymat jimgina eskirib qolishi va ikki manba ajralib ketishi mumkin
      edi — `xlsx_reader.py` da aynan shu xavf uchun alohida darvoza bor.

    ⚠ IMPORT YO'NALISHI: `settings.py` -> `services/quality.py`. Aksincha
      EMAS. Shunda sof modul sozlamaga bog'lanmaydi va uni testda argument
      bilan chaqirish mumkin bo'ladi.
    """

    min_bytes: int
    max_bytes: int
    blank_stddev: float
    dark_mean: float
    dark_stddev: float
    ir_saturation: float
    night_mean: float
    version: int


@dataclass(frozen=True, slots=True)
class QualityReport:
    """Bitta kadrning to'liq baholanishi — verdikt VA o'lchovlar (D-15).

    Attributes:
        verdict: `QUALITY_VERDICTS` dan biri.
        light_mode: `LIGHT_MODES` dan biri. `corrupt` da har doim `unknown`.
        reason: qaysi darvoza qaror qabul qilgani.
        mean: kul rang o'rtachasi `[0; 255]`; o'lchab bo'lmasa `None`.
        stddev: kul rang standart og'ishi; o'lchab bo'lmasa `None`.
        saturation: HSV to'yinganligi `[0,0; 1,0]`; o'lchab bo'lmasa `None`.
        width: dekodlangan kenglik; o'lchab bo'lmasa `None`.
        height: dekodlangan balandlik; o'lchab bo'lmasa `None`.
        size_bytes: XOM tananing hajmi — HAR DOIM ma'lum.
        thresholds_version: `QualityThresholds.version` ning nusxasi.

    ⚠ O'LCHAB BO'LMAGAN QIYMAT `None`, NOL EMAS. Nol bazada «o'lchandi va
      nol chiqdi» degan MA'NOGA ega bo'lardi va D-15 ning maqsadini —
      chegaralarni haqiqiy taqsimotdan chiqarishni — buzardi: `corrupt`
      kadrlarning soxta nollari `percentile_cont` ni pastga tortardi.

    ⚠ `width`/`height` DEKODLANGAN o'lcham, kadrning haqiqiy o'lchami emas:
      `draft()` DCT darajasida kichraytiradi (pastga qarang). Ular sifat
      metrikasi qaysi tasvirdan olinganini yozadi.
    """

    verdict: str
    light_mode: str
    reason: str
    mean: float | None
    stddev: float | None
    saturation: float | None
    width: int | None
    height: int | None
    size_bytes: int
    thresholds_version: int


_SOI: Final[bytes] = b"\xff\xd8\xff"
"""JPEG boshlanishi (Start Of Image + birinchi marker bayti)."""

_EOI: Final[bytes] = b"\xff\xd9"
"""JPEG tugashi (End Of Image). Yo'qligi — javob YARIM yetkazilgan degani."""

_DRAFT_SIZE: Final[tuple[int, int]] = (320, 180)
"""`draft()` ning nishon o'lchami — DCT darajasidagi kichraytirilgan dekod.

Bu `Pillow` ning JPEG'ga xos xususiyati: dekoder to'liq tasvirni qurmasdan,
DCT koeffitsiyentlarining bir qismidan kichraytirilgan tasvir chiqaradi.
To'liq dekoddan bir necha barobar tez va sifat metrikalari uchun 320x180
yetarli.

O'LCHANDI (2026-08-04): 1280x720 kadr `draft("RGB", (320,180))` bilan
o'qilganda `mean`/`stddev`/`saturation` AYNAN o'zgarmadi (24,000/24,000 va
0,5081 ga qarshi 0,5114) — chunki sintetik kadrning polosalari DCT to'riga
tushadi. Ya'ni kichraytirish o'lchovni buzmaydi.

⚠ REJIM `"RGB"`, `"L"` EMAS. `draft("L", ...)` dekoderni KUL RANG rejimiga
  o'tkazadi va o'shanda to'yinganlik HAR DOIM 0,0 chiqardi — ya'ni
  `ir_night` va `low_light` shoxlari BIR-BIRIDAN AJRALMAY qolardi va D-12
  ning butun mazmuni jimgina yo'qolardi.
"""

_SATURATION_SIZE: Final[tuple[int, int]] = (64, 64)
"""To'yinganlik o'lchanadigan eng katta o'lcham.

IR aniqlash uchun piksel aniqligi kerak emas — kerak bo'lgani o'rtacha
rang to'yinganligi. 64x64 gacha kichraytirish uni ~14 barobar arzon
qiladi va natijani o'zgartirmaydi.
"""

_HSV_MAX: Final[float] = 255.0
"""`ImageStat` HSV kanallarini `[0; 255]` da beradi, `[0,0; 1,0]` da emas."""


def _saturation_of(image: Image.Image) -> float:
    """O'rtacha HSV to'yinganligi `[0,0; 1,0]`.

    ⚠ MANBA KUL RANG BO'LSA NATIJA 0,0 va bu TO'G'RI, sun'iy emas: IR
      yoritgich bitta to'lqin uzunligida ishlaydi, sensor esa monoxrom
      kadr beradi (R=G=B). Ya'ni «to'yinganlik yo'q» IR rejimining FIZIK
      xususiyati — `ir_night` shoxi aynan shunga tayanadi (D-12).
    """
    if image.mode == "L":
        return 0.0

    small = image.convert("RGB")
    small.thumbnail(_SATURATION_SIZE)
    return float(ImageStat.Stat(small.convert("HSV")).mean[1]) / _HSV_MAX


def _light_mode_for(mean: float, saturation: float, thresholds: QualityThresholds) -> str:
    """§C.8 formulasi — `mean` va to'yinganlikdan yorug'lik rejimi."""
    if mean >= thresholds.night_mean:
        return LIGHT_DAY
    if saturation < thresholds.ir_saturation:
        return LIGHT_IR_NIGHT
    return LIGHT_LOW_LIGHT


def _corrupt(reason: str, size_bytes: int, thresholds: QualityThresholds) -> QualityReport:
    """O'lchovsiz hisobot — barcha metrikalar `None`."""
    return QualityReport(
        verdict=VERDICT_CORRUPT,
        light_mode=LIGHT_UNKNOWN,
        reason=reason,
        mean=None,
        stddev=None,
        saturation=None,
        width=None,
        height=None,
        size_bytes=size_bytes,
        thresholds_version=thresholds.version,
    )


def analyze(data: bytes, thresholds: QualityThresholds) -> QualityReport:
    """Kadr baytlaridan verdikt, `light_mode` va o'lchovlarni chiqaradi.

    Zanjir ARZONDAN QIMMATGA (§C.7) va tartib ma'noli — har qadam o'zidan
    keyingisining narxini to'laydigan holatlarni oldindan kesadi:

        1. Hajm chegaralari                       -> DEKOD YO'Q
        2. SOI/EOI magic baytlari                  -> DEKOD YO'Q
        3. `Image.open` + `draft("RGB")` + `load()`
        4. `ImageStat` — `mean`, `stddev`
        5. To'yinganlik (kichraytirilgan HSV)
        6. Qaror: blank -> dark -> ok

    Args:
        data: HTTP javobining XOM tanasi (go2rtc `/api/frame.jpeg`,
            ISAPI `/picture` yoki ffmpeg chiqishi).
        thresholds: `Settings.quality_thresholds()` ning natijasi.

    Returns:
        `QualityReport` — HAR YO'LDA. Bu funksiya HECH QACHON istisno
        ko'tarmaydi (pastdagi izohga qarang).
    """
    size_bytes = len(data)

    # --- 1-QADAM: hajm. DEKODSIZ va eng arzon. -----------------------------
    #
    # Bu qadam bo'sh javobni (`200 OK` + bo'sh tana — 04-02 ning
    # `frame_mode=empty` i) va dekompressiya bombasini (T-04-24) BIR
    # BAYT ham dekodlamasdan tutadi.
    if size_bytes < thresholds.min_bytes:
        return _corrupt(REASON_SIZE_BELOW_FLOOR, size_bytes, thresholds)
    if size_bytes > thresholds.max_bytes:
        return _corrupt(REASON_SIZE_ABOVE_CEILING, size_bytes, thresholds)

    # --- 2-QADAM: magic baytlar. DEKODSIZ. ---------------------------------
    #
    # ⚠ BU QADAM `Content-Type` SARLAVHASIGA UMUMAN QARAMAYDI va aynan
    #   shuning uchun kerak. NVR yoki go2rtc xato holatida HTML sahifa
    #   qaytaradi; ba'zi proxy va firmware esa sarlavhani `image/jpeg`
    #   qoldirib yuboradi (T-04-25). Sarlavhaga ishonadigan filtr o'sha
    #   sahifani YAROQLI KADR deb qabul qilardi.
    #
    # ⚠ EOI ning yo'qligi — «javob YARIM yetkazilgan» ning shakli: TCP
    #   uzilishi, NVR buferining to'lishi yoki proxy timeout'i JPEG ni
    #   o'rtasida uzadi. Sarlavha va birinchi skanerlash qatorlari yaroqli
    #   bo'lgani uchun `Image.open()` MUVAFFAQIYATLI bo'lardi.
    if data[:3] != _SOI:
        return _corrupt(REASON_NOT_JPEG, size_bytes, thresholds)
    if data[-2:] != _EOI:
        return _corrupt(REASON_TRUNCATED, size_bytes, thresholds)

    # --- 3-QADAM: dekod. ---------------------------------------------------
    try:
        image = Image.open(io.BytesIO(data))
        image.draft("RGB", _DRAFT_SIZE)
        image.load()
    except (OSError, UnidentifiedImageError, Image.DecompressionBombError):
        # `OSError` — kesilgan skanerlash ma'lumoti (`LOAD_TRUNCATED_IMAGES`
        # `False` bo'lgani uchun); `UnidentifiedImageError` — format
        # tanilmadi; `DecompressionBombError` — e'lon qilingan o'lcham
        # `MAX_IMAGE_PIXELS` dan katta.
        return _corrupt(REASON_DECODE_FAILED, size_bytes, thresholds)
    except Exception:
        # ⚠ KENG `except` — ATAYIN, VA U OXIRGI. Bu funksiya kadr olish
        #   yo'lining O'RTASIDA turadi: uning yiqilishi butun slotni
        #   yo'qotardi va yo'qotilgan slot QAYTARILMAYDI (04-UI-SPEC
        #   §11.8, `capture_slot_missed`). Pillow ning har bir plagini o'z
        #   istisnosini ko'tarishi mumkin va ularning ro'yxati Pillow
        #   versiyasi bilan o'zgaradi.
        #
        #   Xato YUTILMAYDI — `log.exception` bilan to'liq iz jurnalga va
        #   Sentry'ga boradi. Yutilgan bo'lsa nosozlik faqat statistikada,
        #   oylar keyin ko'rinardi.
        log.exception("quality.decode_unexpected_error", size_bytes=size_bytes)
        return _corrupt(REASON_DECODE_FAILED, size_bytes, thresholds)

    # --- 4 va 5-QADAM: o'lchovlar. -----------------------------------------
    grey = ImageStat.Stat(image.convert("L"))
    mean = float(grey.mean[0])
    stddev = float(grey.stddev[0])
    saturation = _saturation_of(image)
    width, height = image.size

    # --- 6-QADAM: qaror. TARTIB MA'NOLI. -----------------------------------
    #
    # `blank` `dark` DAN OLDIN: axborot yo'qligi qorong'ilikdan KUCHLIROQ
    # da'vo. Yorug'lik normal bo'lgan bir xil rangli kadr ham `blank`
    # (MediaMTX 9101 yo'li: `YAVG 126, YLOW=YHIGH=126`), ya'ni `blank`
    # `mean` ga UMUMAN qaramaydi.
    if stddev < thresholds.blank_stddev:
        verdict, reason = VERDICT_BLANK, REASON_BLANK
    elif mean < thresholds.dark_mean and stddev < thresholds.dark_stddev:
        # ⛔ IKKI SHART — D-14. `and stddev < thresholds.dark_stddev` qismini
        #   olib tashlash qonuniy qish-tong kadrlarini OYLAB rad etardi
        #   (modul docstringi, 2-majburiyat). Bu qator yagona shartli
        #   holatga qaytarilmaydi.
        verdict, reason = VERDICT_DARK, REASON_DARK
    else:
        verdict, reason = VERDICT_OK, REASON_OK

    return QualityReport(
        verdict=verdict,
        light_mode=_light_mode_for(mean, saturation, thresholds),
        reason=reason,
        mean=mean,
        stddev=stddev,
        saturation=saturation,
        width=width,
        height=height,
        size_bytes=size_bytes,
        thresholds_version=thresholds.version,
    )


# `ImageFile` import qatlamida ISHLATILADI — `test_truncated_images_flag_is_
# false` uni `PIL.ImageFile` dan o'qiydi, lekin bu modul uni ATAYIN import
# qiladi: shunda bayroqning mavjudligi va nomi kompilyatsiya paytida
# tekshiriladi va Pillow uni qayta nomlaganda import xatosi DARHOL chiqadi,
# darvoza esa jimgina «yo'q bayroqni» tekshirib yashil qolmaydi.
_TRUNCATED_FLAG_IS_REFERENCED: Final[bool] = ImageFile.LOAD_TRUNCATED_IMAGES
