"""GENERATORNING O'ZINI o'lchaydi — sifat filtrining EMASINI (W0-9).

=============================================================================
BU FAYL NIMANI ISBOTLAYDI VA NIMANI ISBOTLAMAYDI.

ISBOTLAYDI: `fixtures.frames.frame_bytes` so'ralgan FIZIK XUSUSIYATNI
  haqiqatan beradi — `mean=8, stddev=2` so'ralsa, qaytgan JPEG'dan
  `PIL.ImageStat` aynan shuni o'qiydi.

ISBOTLAMAYDI: chegaralar to'g'ri qo'yilganini. Sifat filtri bu yerda
  UMUMAN import qilinmaydi; uning testi `04-04` da yoziladi va u shu
  generatorni ISTE'MOL qiladi.

⚠ Ikkalasini bitta faylda aralashtirish aynan taqiqlangan antinaqshni
  qaytarardi: fixture chegaraga qarab yasalsa, test chegarani chegaraning
  o'zi bilan tekshirardi. Shuning uchun bu yerdagi HAR test nomi FIZIK
  XUSUSIYAT bilan atalgan va birortasida `dark`, `blank`, `rejected` degan
  verdikt so'zi YO'Q.
=============================================================================

TOLERANS MANBAI — `fixtures.frames` MODULI (`MEAN_TOLERANCE` va h.k.), test
emas. Test uni faqat o'qiydi: tolerans generatorning E'LON QILINGAN va'dasi,
testning qulayligi emas. Ikkinchi nusxa bo'lsa, ular ajralib ketardi va
"generator kontraktni bajaradi" da'vosi testning o'z sonlariga aylanardi.
"""

from __future__ import annotations

import io

import pytest
from fixtures.frames import (
    HTML_ERROR_PAGE,
    MEAN_TOLERANCE,
    SATURATION_TOLERANCE,
    STDDEV_TOLERANCE,
    frame_bytes,
    truncate,
)
from PIL import Image, ImageFile, ImageStat

JPEG_SOI = b"\xff\xd8\xff"
JPEG_EOI = b"\xff\xd9"


def _luma(data: bytes) -> ImageStat.Stat:
    """Kul rang kanalining statistikasi — D-14 ning `mean`/`stddev` juftligi."""
    return ImageStat.Stat(Image.open(io.BytesIO(data)).convert("L"))


def _hsv_saturation(data: bytes) -> float:
    """HSV `S` kanalining o'rtachasi, [0,0; 1,0] ga normallashtirilgan."""
    return ImageStat.Stat(Image.open(io.BytesIO(data)).convert("HSV")).mean[1] / 255.0


def _channel_means(data: bytes) -> tuple[float, float, float]:
    red, green, blue = ImageStat.Stat(Image.open(io.BytesIO(data))).mean
    return red, green, blue


# ---------------------------------------------------------------------------
# 1-2. Nishonga tushish — ikki uchi (juda qorong'i va o'rtacha yorug').
# ---------------------------------------------------------------------------


def test_mean_8_stddev_2_reads_back_within_tolerance() -> None:
    stat = _luma(frame_bytes(mean=8, stddev=2))

    assert abs(stat.mean[0] - 8) <= MEAN_TOLERANCE, (
        f"o'rtacha nishondan chetda: {stat.mean[0]:.2f} (nishon 8 ± {MEAN_TOLERANCE})"
    )
    assert abs(stat.stddev[0] - 2) <= STDDEV_TOLERANCE, (
        f"og'ish nishondan chetda: {stat.stddev[0]:.2f} (nishon 2 ± {STDDEV_TOLERANCE})"
    )


def test_mean_140_stddev_45_reads_back_within_tolerance() -> None:
    stat = _luma(frame_bytes(mean=140, stddev=45))

    assert abs(stat.mean[0] - 140) <= MEAN_TOLERANCE, (
        f"o'rtacha nishondan chetda: {stat.mean[0]:.2f} (nishon 140 ± {MEAN_TOLERANCE})"
    )
    assert abs(stat.stddev[0] - 45) <= STDDEV_TOLERANCE, (
        f"og'ish nishondan chetda: {stat.stddev[0]:.2f} (nishon 45 ± {STDDEV_TOLERANCE})"
    )


# ---------------------------------------------------------------------------
# 3. `stddev=0` — bir xil rangli kadr.
#
# ⚠ D-14 aynan shu holat uchun IKKI SHARTLI qoidani talab qiladi: past
#   `mean` YOKI past `stddev` yakka o'zi yetarli emas. Generator ikkala
#   o'lchamni MUSTAQIL beradi, ya'ni `mean=60` (past emas) + `stddev=0`
#   (juda past) kombinatsiyasini ham yasay oladi — bu qish-tong kadrining
#   analogi va uni faqat o'rtachaga qaragan qoida jimgina tashlab yuborardi.
# ---------------------------------------------------------------------------


def test_stddev_0_produces_a_single_level_frame() -> None:
    stat = _luma(frame_bytes(mean=60, stddev=0))

    assert stat.stddev[0] < 1.0, (
        f"bir xil rangli kadrda og'ish {stat.stddev[0]:.2f} — 1,0 dan kichik kutilgan"
    )
    assert abs(stat.mean[0] - 60) <= MEAN_TOLERANCE


# ---------------------------------------------------------------------------
# 4. To'yinganlik — IR (monoxrom) va kunduzgi (rangli) kadrning FARQI.
# ---------------------------------------------------------------------------


def test_saturation_0_keeps_all_three_channels_equal() -> None:
    red, green, blue = _channel_means(frame_bytes(mean=140, stddev=45, saturation=0.0))

    assert abs(red - green) <= 1.0 and abs(green - blue) <= 1.0, (
        f"monoxrom kutilgan, o'lchangani R={red:.1f} G={green:.1f} B={blue:.1f}"
    )
    assert _hsv_saturation(frame_bytes(mean=140, stddev=45, saturation=0.0)) < 0.02


def test_saturation_050_reads_back_above_030() -> None:
    data = frame_bytes(mean=140, stddev=45, saturation=0.5)

    assert _hsv_saturation(data) >= 0.30, (
        f"HSV to'yinganligi {_hsv_saturation(data):.3f} — 0,30 dan katta kutilgan"
    )
    # Yorug'lik to'yinganlik bilan BIRGA SUZIB KETMAYDI: ikki fizik xususiyat
    # mustaqil boshqariladi (`_rgb_for` docstringi).
    assert abs(_luma(data).mean[0] - 140) <= MEAN_TOLERANCE
    assert abs(_hsv_saturation(data) - 0.5) <= SATURATION_TOLERANCE


# ---------------------------------------------------------------------------
# 5. DETERMINIZM — MAJBURIY va ALOHIDA.
# ---------------------------------------------------------------------------


def test_identical_arguments_produce_identical_bytes() -> None:
    """Usiz keyingi rejalarning chegara testlari "gohida" yiqilardi.

    ⚠ Bu test tolerans testlaridan MUSTAQIL bo'lishi SHART: urug' global
      `random` moduliga o'tkazilsa polosalarning TARTIBI har chaqiruvda
      o'zgaradi, lekin TO'PLAM o'sha bo'lgani uchun `mean` va `stddev`
      nishonda qoladi — ya'ni yuqoridagi to'rtta test YASHIL qolib,
      faqat SHU test qizaradi. Determinizm shu sababdan alohida
      o'lchanadi.
    """
    first = frame_bytes(mean=8, stddev=2)
    second = frame_bytes(mean=8, stddev=2)

    assert first == second, "bir xil argumentlar har xil baytlar berdi — urug' qadalmagan"
    assert first.startswith(JPEG_SOI), "SOI markeri yo'q — bu JPEG emas"
    assert first.endswith(JPEG_EOI), "EOI markeri yo'q — oqim to'liq emas"


def test_different_arguments_produce_different_bytes() -> None:
    """Nazorat: determinizm testi konstanta qaytaradigan generatorda ham yashil bo'lardi."""
    assert frame_bytes(mean=8, stddev=2) != frame_bytes(mean=140, stddev=45)
    assert frame_bytes(mean=140, stddev=45) != frame_bytes(mean=140, stddev=45, saturation=0.5)


# ---------------------------------------------------------------------------
# 6. Kesilgan oqim — `open()` o'tadi, `load()` yiqiladi.
# ---------------------------------------------------------------------------


def test_truncate_removes_the_end_of_image_marker() -> None:
    data = truncate(frame_bytes(mean=140, stddev=45))

    assert not data.endswith(JPEG_EOI), "EOI hamon joyida — oqim kesilmagan"
    assert data.startswith(JPEG_SOI), "sarlavha ham yo'qolgan — bu kesish emas, buzish"


def test_truncated_stream_opens_but_fails_on_load() -> None:
    """⚠ Sifat filtri `open()` bilan cheklanib qolsa, kesilgan kadr YAROQLI ko'rinardi."""
    assert ImageFile.LOAD_TRUNCATED_IMAGES is False, (
        "`LOAD_TRUNCATED_IMAGES` global bayroq va u YOQILGAN — kimdir uni "
        "boshqa modulda o'zgartirgan bo'lsa kesilgan kadr JIMGINA yuklanadi "
        "va bu darvoza ma'nosini yo'qotadi (D-13)"
    )

    data = truncate(frame_bytes(mean=140, stddev=45))
    image = Image.open(io.BytesIO(data))  # `open()` MUVAFFAQIYATLI — sarlavha yaroqli

    with pytest.raises(OSError):
        image.load()


# ---------------------------------------------------------------------------
# 7. HTML xato sahifasi — JPEG EMAS.
# ---------------------------------------------------------------------------


def test_html_error_page_does_not_start_with_jpeg_magic() -> None:
    assert not HTML_ERROR_PAGE.startswith(JPEG_SOI), "HTML sahifa JPEG magic bayti bilan boshlandi"
    assert b"<html>" in HTML_ERROR_PAGE
    assert b"401" in HTML_ERROR_PAGE


# ---------------------------------------------------------------------------
# Kontrakt chegaralari — nishonga tushib bo'lmasa RAD ETILADI, QISILMAYDI.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("kwargs", "reason"),
    [
        ({"mean": 8, "stddev": 20}, "oraliq 0 dan pastga tushadi"),
        ({"mean": 250, "stddev": 20}, "oraliq 255 dan oshadi"),
        ({"mean": 140, "stddev": 45, "size": (321, 180)}, "kenglik 8 ga karrali emas"),
        ({"mean": 200, "stddev": 30, "saturation": 0.5}, "eng yorug' kanal 255 dan oshadi"),
        ({"mean": 140, "stddev": 45, "saturation": 1.5}, "to'yinganlik oralig'i buzilgan"),
    ],
)
def test_unreachable_targets_are_rejected(kwargs: dict[str, object], reason: str) -> None:
    """Jimgina qisish (`clamp`) chaqiruvchiga SO'RALMAGAN kadrni berardi."""
    with pytest.raises(ValueError):
        frame_bytes(**kwargs)  # type: ignore[arg-type]
