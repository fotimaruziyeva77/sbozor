"""Sifat filtri — bayt → verdikt + `light_mode` (CAM-06, D-12/D-14/D-15).

=============================================================================
NOMLASH QOIDASI `tests/fixtures/frames.py` DAN MEROS: test nomi FIZIK
XUSUSIYAT bilan ataladi, verdikt bilan EMAS.

    test_mean_30_stddev_28_is_ok_because_it_has_structure   ✅
    test_dark_frame_is_rejected                             ❌

Sabab o'sha fixture modulida yozilgan: chegara bilan nomlangan test o'z
farazining aks-sadosiga aylanadi. Bu yerda u yana bir bosqichga ko'tariladi —
har testda chegaralar ANIQ argument sifatida beriladi va `get_settings()`
HECH QACHON chaqirilmaydi. Aks holda test muhitga bog'lanib qolardi va
`.env` dagi bitta son butun to'plamning ma'nosini o'zgartirardi.
=============================================================================

⚠ IKKI CHEGARA TO'PLAMI VA IKKALASI HAM KERAK.

`_RULE` — QOIDANING SHAKLINI o'lchaydi. Uning raqamlari ATAYIN tanlangan:
har shart ALOHIDA hal qiluvchi bo'lsin (pastdagi izohlarga qarang). Shunda
bitta shartni olib tashlash AYNAN bitta testni qizartiradi.

`_SHIPPED` — `Settings` ning YETKAZILGAN standartlari. U qoidaning shaklini
emas, MAHSULOTDAGI xulqni o'lchaydi: `dark` yetkazilgan raqamlarda ham
ERISHILADIGAN bo'lishi va D-14 ning ikkinchi sharti u yerda ham ISHLASHI
shart. Faqat `_RULE` bilan o'lchansa «qoida to'g'ri, lekin mahsulotda
hech qachon ishlamaydi» holati ko'rinmasdan qolardi.
"""

from __future__ import annotations

import io
from typing import Final

import pytest
from PIL import Image, ImageFile

from app.services.quality import (
    LIGHT_DAY,
    LIGHT_IR_NIGHT,
    LIGHT_LOW_LIGHT,
    LIGHT_UNKNOWN,
    QUALITY_THRESHOLDS_VERSION,
    REASON_DECODE_FAILED,
    REASON_NOT_JPEG,
    REASON_SIZE_ABOVE_CEILING,
    REASON_SIZE_BELOW_FLOOR,
    REASON_TRUNCATED,
    VERDICT_BLANK,
    VERDICT_CORRUPT,
    VERDICT_DARK,
    VERDICT_OK,
    QualityThresholds,
    analyze,
)
from fixtures.frames import HTML_ERROR_PAGE, frame_bytes, truncate

_RULE: Final = QualityThresholds(
    min_bytes=2_000,
    max_bytes=8 * 1024 * 1024,
    # 1,0 — `mean=8, stddev=2` kadri (o'lchandi: stddev AYNAN 2,000) `blank`
    # ga tushib ketmasin. `blank` `dark` dan USTUN, ya'ni bu chegara `dark`
    # shoxining ERISHILISHINI belgilaydi: u 2 dan yuqori bo'lsa `dark`
    # umuman sinalmasdan qolardi.
    blank_stddev=1.0,
    # 40 — `mean=30` dan YUQORI. Ataylab: shunda qish-tong kadri `mean`
    # sharti bilan HAL QILINMAYDI va uning `ok` bo'lishi FAQAT ikkinchi
    # shartga bog'liq bo'ladi. 25 (yetkazilgan standart) bilan o'lchansa
    # `mean` yolg'iz o'zi hal qilardi va D-14 ning sabotaji ko'rinmasdi.
    dark_mean=40.0,
    # 20 — `stddev=28` dan PAST, ya'ni ikkinchi shart AYNAN shu kadrda
    # ishlaydi.
    dark_stddev=20.0,
    ir_saturation=0.05,
    night_mean=110.0,
    version=QUALITY_THRESHOLDS_VERSION,
)
"""Qoidaning SHAKLINI o'lchaydigan chegaralar — `Settings` dan MUSTAQIL."""

_SHIPPED: Final = QualityThresholds(
    min_bytes=4_096,
    max_bytes=8 * 1024 * 1024,
    blank_stddev=3.0,
    dark_mean=25.0,
    dark_stddev=12.0,
    ir_saturation=0.05,
    night_mean=110.0,
    version=QUALITY_THRESHOLDS_VERSION,
)
"""`Settings` ning yetkazilgan standartlari — QO'LDA takrorlangan, ATAYIN.

Bu modul `get_settings()` ni chaqirmaydi (yuqoridagi docstring). Nusxa
`tests/unit/test_snapshot_settings.py::test_quality_thresholds_match_the_
shipped_defaults` bilan `Settings` ga BOG'LANGAN — ya'ni standart
o'zgartirilsa o'sha test qizaradi va bu yerdagi nusxa eskirib qola olmaydi.

⚠ `min_bytes=4096` sababli bu to'plam bilan o'lchanadigan kadrlar
  1280x720 da yasaladi: 320x180 sintetik kadr ~2,2–3,8 KB va u
  YETKAZILGAN pol ostida qoladi (o'lchandi 2026-08-04).
"""


def _png_body() -> bytes:
    """Yaroqli PNG — JPEG EMAS, lekin DEKODLANADIGAN tana.

    ⚠ BU MAGIC-BAYT DARVOZASINING YAGONA MUSTAQIL NAZORATI.

    HTML sahifa yoki bo'sh tana magic darvozasisiz ham `corrupt` bo'lardi
    (`Image.open` ularni umuman tanimaydi), ya'ni ular darvozani
    O'LCHAMAYDI — ular faqat natijani takrorlaydi. PNG esa muvaffaqiyatli
    dekodlanadi va statistikasi hisoblanadi: magic darvozasi olib
    tashlansa bu tana `ok` bo'lib chiqadi. Shuning uchun aynan u sabotaj
    o'lchovi bo'ladi.

    1280x720 tanlangan: o'lchandi — 320x180 PNG 643 bayt, ya'ni u
    `min_bytes` polida to'xtardi va yana darvozani o'lchamasdi.
    """
    source = Image.open(io.BytesIO(frame_bytes(mean=140, stddev=45, size=(1280, 720))))
    buffer = io.BytesIO()
    source.save(buffer, "PNG")
    return buffer.getvalue()


# ---------------------------------------------------------------------------
# Qoidaning shakli — `_RULE`
# ---------------------------------------------------------------------------


def test_mean_140_stddev_45_is_ok_and_day() -> None:
    """Yorug', tuzilmali kadr — yaroqli va kunduzgi."""
    report = analyze(frame_bytes(mean=140, stddev=45), _RULE)

    assert report.verdict == VERDICT_OK
    assert report.light_mode == LIGHT_DAY


def test_mean_8_stddev_2_is_dark_when_the_blank_floor_is_below_it() -> None:
    """Ikkala `dark` sharti ham bajarilgan kadr."""
    report = analyze(frame_bytes(mean=8, stddev=2), _RULE)

    assert report.verdict == VERDICT_DARK


def test_mean_30_stddev_28_is_ok_because_it_has_structure() -> None:
    """⛔ D-14 NING BUTUN MAZMUNI — qonuniy qish-tong kadri YAROQLI.

    Qorong'i (`mean=30 < dark_mean=40`), LEKIN tuzilmali
    (`stddev=28 > dark_stddev=20`). Yagona shartli `dark` qoidasi bu
    kadrni rad etardi va nosozlik OYLAB ko'rinmasdi — kunlik hisob
    jimgina yo'qolardi.

    Chegaralar shunday tanlanganki, `mean` sharti YOLG'IZ hal qila
    olmaydi: `30 < 40` rost. Ya'ni bu test faqat IKKINCHI shart borligida
    yashil bo'ladi.
    """
    report = analyze(frame_bytes(mean=30, stddev=28), _RULE)

    assert report.verdict == VERDICT_OK
    assert report.mean is not None
    assert report.stddev is not None
    assert report.mean < _RULE.dark_mean, "birinchi shart BAJARILGAN bo'lishi kerak"
    assert report.stddev > _RULE.dark_stddev, "ya'ni qarorni FAQAT ikkinchi shart beradi"


def test_mean_60_stddev_0_is_blank_regardless_of_brightness() -> None:
    """`blank` FAQAT `stddev` ga qaraydi — yorug'lik normal bo'lsa ham."""
    report = analyze(frame_bytes(mean=60, stddev=0), _RULE)

    assert report.verdict == VERDICT_BLANK
    assert report.mean is not None
    assert report.mean > _RULE.dark_mean, "yorug'lik `dark` chegarasidan YUQORI"


def test_mean_5_stddev_0_is_blank_and_not_dark() -> None:
    """`blank` `dark` dan USTUN: axborot yo'qligi qorong'ilikdan kuchliroq da'vo.

    Bu kadr IKKALA `dark` shartini ham bajaradi (`5 < 40`, `0 < 20`),
    lekin `blank` avval tekshiriladi.
    """
    report = analyze(frame_bytes(mean=5, stddev=0), _RULE)

    assert report.verdict == VERDICT_BLANK


def test_saturation_000_below_the_night_mean_is_ir_night() -> None:
    """Monoxrom (R=G=B) va qorong'i — IR yoritgich yoqilgan."""
    report = analyze(frame_bytes(mean=70, stddev=25, saturation=0.0), _RULE)

    assert report.verdict == VERDICT_OK
    assert report.light_mode == LIGHT_IR_NIGHT


def test_saturation_050_below_the_night_mean_is_low_light() -> None:
    """Rangli, lekin qorong'i — IR ga o'tmagan kamera."""
    report = analyze(frame_bytes(mean=70, stddev=25, saturation=0.5), _RULE)

    assert report.verdict == VERDICT_OK
    assert report.light_mode == LIGHT_LOW_LIGHT


# ---------------------------------------------------------------------------
# `corrupt` ning to'rt yo'li — har biri ALOHIDA sabab bilan
# ---------------------------------------------------------------------------


def test_tail_truncated_jpeg_is_corrupt() -> None:
    """EOI yo'q — kesilgan javob DEKODSIZ tutiladi."""
    report = analyze(truncate(frame_bytes(mean=128, stddev=40, size=(1280, 720))), _RULE)

    assert report.verdict == VERDICT_CORRUPT
    assert report.reason == REASON_TRUNCATED
    assert report.light_mode == LIGHT_UNKNOWN


def test_html_error_page_is_corrupt() -> None:
    """NVR/go2rtc xato sahifasi — `Content-Type` ga UMUMAN qaralmaydi."""
    report = analyze(HTML_ERROR_PAGE, _RULE)

    assert report.verdict == VERDICT_CORRUPT


def test_png_body_is_corrupt_although_it_decodes() -> None:
    """⛔ MAGIC-BAYT DARVOZASINING MUSTAQIL O'LCHOVI.

    Bu tana yaroqli tasvir — u dekodlanadi va statistikasi hisoblanadi.
    Uni FAQAT magic-bayt darvozasi rad etadi. Darvoza olib tashlansa
    verdikt `ok` ga aylanadi (o'lchandi: `mean=140, stddev=45`).
    """
    body = _png_body()
    assert len(body) > _RULE.min_bytes, "nazorat: tana o'lcham polidan YUQORI bo'lishi shart"

    report = analyze(body, _RULE)

    assert report.verdict == VERDICT_CORRUPT
    assert report.reason == REASON_NOT_JPEG


def test_empty_body_is_corrupt() -> None:
    """Bo'sh tana — `200 OK` bilan kelishi mumkin (04-02 `frame_mode=empty`)."""
    report = analyze(b"", _RULE)

    assert report.verdict == VERDICT_CORRUPT
    assert report.reason == REASON_SIZE_BELOW_FLOOR
    assert report.size_bytes == 0


def test_hundred_byte_body_is_corrupt() -> None:
    """O'lcham poli — DEKODSIZ, eng arzon qadam."""
    report = analyze(b"x" * 100, _RULE)

    assert report.verdict == VERDICT_CORRUPT
    assert report.reason == REASON_SIZE_BELOW_FLOOR


def test_body_above_the_size_ceiling_is_corrupt() -> None:
    """T-04-24 — dekompressiya bombasi DEKODDAN OLDIN to'xtatiladi.

    Chegara testda ATAYIN kichraytirilgan (2000 bayt): 8 MiB li tana
    yasash testni sekinlashtirardi va o'lchanadigan da'voni
    o'zgartirmasdi.
    """
    tight = QualityThresholds(
        min_bytes=100,
        max_bytes=2_000,
        blank_stddev=_RULE.blank_stddev,
        dark_mean=_RULE.dark_mean,
        dark_stddev=_RULE.dark_stddev,
        ir_saturation=_RULE.ir_saturation,
        night_mean=_RULE.night_mean,
        version=_RULE.version,
    )
    body = frame_bytes(mean=140, stddev=45)
    assert len(body) > tight.max_bytes, "nazorat: tana shift USTIDA bo'lishi shart"

    report = analyze(body, tight)

    assert report.verdict == VERDICT_CORRUPT
    assert report.reason == REASON_SIZE_ABOVE_CEILING


def test_jpeg_markers_with_garbage_payload_is_corrupt() -> None:
    """SOI va EOI bor, ICHI axlat — dekod bosqichi tutadi."""
    body = b"\xff\xd8\xff" + b"\x00" * 3_000 + b"\xff\xd9"

    report = analyze(body, _RULE)

    assert report.verdict == VERDICT_CORRUPT
    assert report.reason == REASON_DECODE_FAILED


def test_corrupt_report_has_no_measurements() -> None:
    """O'lchab bo'lmagan kadr o'lchov O'RNIGA `None` beradi, NOL emas.

    Nol qiymat bazada «o'lchandi va nol chiqdi» degan MA'NOGA ega
    bo'lardi va D-15 ning butun maqsadini — chegaralarni haqiqiy
    taqsimotdan chiqarishni — buzardi.
    """
    report = analyze(HTML_ERROR_PAGE, _RULE)

    assert report.mean is None
    assert report.stddev is None
    assert report.saturation is None
    assert report.width is None
    assert report.height is None
    assert report.size_bytes == len(HTML_ERROR_PAGE)


# ---------------------------------------------------------------------------
# D-15 — O'LCHOVLARNING O'ZI saqlanadi
# ---------------------------------------------------------------------------


def test_report_carries_the_measurements_not_only_the_verdict() -> None:
    """Chegaralar SQL bilan sozlanadi, qayta kadr olish bilan emas (D-15)."""
    report = analyze(frame_bytes(mean=140, stddev=45), _RULE)

    assert report.mean == pytest.approx(140.0, abs=2.0)
    assert report.stddev == pytest.approx(45.0, abs=1.5)
    assert report.saturation == pytest.approx(0.0, abs=0.05)
    assert (report.width, report.height) == (320, 180)
    assert report.size_bytes == len(frame_bytes(mean=140, stddev=45))


def test_report_carries_the_thresholds_version() -> None:
    """Verdikt QAYSI chegara to'plami bilan qo'yilgani yoziladi (§C.7)."""
    report = analyze(frame_bytes(mean=140, stddev=45), _RULE)

    assert report.thresholds_version == QUALITY_THRESHOLDS_VERSION


def test_analyze_never_raises() -> None:
    """Funksiya kadr olish yo'lining O'RTASIDA turadi — yiqilsa slot yo'qoladi."""
    bodies = [
        b"",
        b"\xff\xd8\xff",
        b"\xff\xd8\xff" + b"\xff" * 5_000 + b"\xff\xd9",
        bytes(range(256)) * 40,
        HTML_ERROR_PAGE,
    ]

    for body in bodies:
        report = analyze(body, _RULE)
        assert report.size_bytes == len(body)


# ---------------------------------------------------------------------------
# Jarayon darajasidagi GLOBAL bayroqlar — ikkala darvoza ham import qatlamida
# ---------------------------------------------------------------------------


def test_truncated_images_flag_is_false() -> None:
    """⛔ `LOAD_TRUNCATED_IMAGES` — GLOBAL bayroq, uni har kim o'zgartira oladi.

    `True` bo'lsa kesilgan JPEG JIMGINA dekodlanadi (qolgani kulrang) va
    buzuq detektori butunlay o'chib qoladi — birorta verdikt testi
    qizarmasdan. Hech qanday erta belgi yo'q, aynan shuning uchun
    darvoza global holatni O'QIYDI.
    """
    assert ImageFile.LOAD_TRUNCATED_IMAGES is False


def test_max_image_pixels_is_bounded() -> None:
    """T-04-24 — dekompressiya bombasi himoyasi O'CHIRILMAGAN."""
    assert Image.MAX_IMAGE_PIXELS is not None


# ---------------------------------------------------------------------------
# YETKAZILGAN standartlar — mahsulotdagi xulq
# ---------------------------------------------------------------------------


def test_mean_24_stddev_24_is_ok_at_shipped_defaults() -> None:
    """⛔ D-14 YETKAZILGAN raqamlarda ham ishlaydi.

    `mean=24 < dark_mean=25` — birinchi shart BAJARILGAN. Kadr faqat
    `stddev=24 > dark_stddev=12` bo'lgani uchun yaroqli. Ya'ni ikkinchi
    shart mahsulotda ham HAQIQATAN qaror qabul qiladi, nafaqat test
    chegaralarida.
    """
    report = analyze(frame_bytes(mean=24, stddev=24, size=(1280, 720)), _SHIPPED)

    assert report.verdict == VERDICT_OK
    assert report.mean is not None
    assert report.mean < _SHIPPED.dark_mean


def test_mean_8_stddev_5_is_dark_at_shipped_defaults() -> None:
    """`dark` yetkazilgan raqamlarda ERISHILADIGAN shox — o'lik enum emas."""
    report = analyze(frame_bytes(mean=8, stddev=5, size=(1280, 720)), _SHIPPED)

    assert report.verdict == VERDICT_DARK
    assert report.light_mode == LIGHT_IR_NIGHT


def test_mean_126_stddev_0_is_blank_at_shipped_defaults() -> None:
    """MediaMTX 9101 yo'lining analogi: yorug'lik normal, tuzilma YO'Q."""
    report = analyze(frame_bytes(mean=126, stddev=0, size=(1280, 720)), _SHIPPED)

    assert report.verdict == VERDICT_BLANK


def test_mean_8_stddev_2_is_blank_at_shipped_defaults() -> None:
    """⚠ CHEGARADAGI HOLAT — ATAYIN yozilgan, tasodifiy emas.

    `stddev=2` yetkazilgan `blank_stddev=3` DAN PAST, ya'ni bu kadr
    mahsulotda `dark` emas, `blank` deb belgilanadi. Ikkala verdikt ham
    `is_billable = false` beradi va ikkalasi ham adminга ko'rinadi —
    farq FAQAT diagnostikada («linza yopiq» va «yorug'lik yo'q»).

    Test shuning uchun bor: bu chegara qiymatining natijasi va u
    D-15 bo'yicha Phase 0 da real kadrlar bilan sozlanadi. Sozlangan
    kuni AYNAN shu test qizaradi va o'zgarish KO'RINADI — jimgina
    siljib ketmaydi.
    """
    report = analyze(frame_bytes(mean=8, stddev=2, size=(1280, 720)), _SHIPPED)

    assert report.verdict == VERDICT_BLANK
    assert report.stddev is not None
    assert report.stddev < _SHIPPED.blank_stddev
