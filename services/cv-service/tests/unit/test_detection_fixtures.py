"""`fixtures/detections.py` NING O'ZI uchun darvoza — VA NOMLASH QOIDASINING HUJJATI.

=============================================================================
NOMLASH QOIDASI: GEOMETRIK FAKT, KUTILGAN VERDIKT EMAS.

| ✅ To'g'ri (geometrik fakt)                | ❌ Noto'g'ri (verdikt aks-sadosi)      |
|-------------------------------------------|----------------------------------------|
| `detections_at(boxes=[(0.4,0.5,0.5,0.6)])` | `detections_that_make_zone_occupied()` |
| `polygon_unit_square()`                    | `polygon_that_catches_the_box()`       |
| `box_center_in_polygon(polygon)`           | `box_that_is_detected()`               |

⚠ SABABI TO'G'RIDAN-TO'G'RI: kutilgan natija bilan nomlangan fixture
  testni O'Z FARAZINING AKS-SADOSIGA aylantiradi.
  `detections_that_make_zone_occupied()` degan fixture «zonani band
  qiladigan detektsiya» ni yasash uchun ZONA MANTIG'INI bilishi kerak —
  ya'ni u mantiqni mantiqning O'ZI bilan tekshiradi va mantiq noto'g'ri
  bo'lsa ham YASHIL qoladi. Zona qarori shunda darvoza emas, konventsiya
  bo'lib qolardi (05-VALIDATION: «usiz butun zona mantig'i darvoza emas»).

  Bu 4-fazada o'lchangan naqshning kuchliroq shakldagi qaytishi:
  `frame_bytes(mean=8, stddev=2)` ✅ / `frame_dark()` ❌
  (`tests/fixtures/frames.py:3-29`).

TAQIQLANGAN NOMLAR — `fixtures/detections.py` da na kodda, na izohda:

    occupied · empty · uncertain · verdict · PolygonZone

Uchtasi model VERDIKTI, to'rtinchisi qaror maydonining nomi, beshinchisi
esa tekshirilayotgan MEXANIZM (uni fixture ichiga olib kirish yuqoridagi
aks-sado muammosining eng qisqa yo'li).

⚠ RO'YXAT AYNAN SHU FAYLDA YASHAYDI, SKANERLANADIGAN FAYLDA EMAS. Sabab
  3-fazada o'lchangan (03-07): skanerlanadigan faylning izohida taqiqlangan
  token yozilsa, sodda darvoza O'ZINI O'ZI qizartiradi va yagona
  «tuzatish» yo'li darvozani bo'shatish bo'ladi.

⚠ `np.empty` ISHLATILMAYDI — massivlar `np.array`/`np.zeros` bilan
  quriladi. Sabab geometrik EMAS, LEKSIK: `np.empty` yuqoridagi skanerga
  `empty` bo'lib tushardi va darvoza YOLG'ON-QIZIL berardi. Yolg'on-qizil
  esa darvozani bo'shatish bosimini tug'diradi — ya'ni bu cheklov
  darvozaning O'ZINI himoya qiladi.

=============================================================================
KUTILGAN NATIJALAR QO'LDA HISOBLANADI VA LITERAL YOZILADI.

Tekshirilayotgan funksiya kutilgan qiymatni olish uchun CHAQIRILMAYDI
(`tests/unit/test_periods.py` va `test_rtsp_url.py` bilan bir xil qoida):
aks holda test faqat «funksiya o'zi bilan mos» deganini isbotlardi.
=============================================================================
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

import numpy as np
import pytest
from fixtures.detections import (
    DEFAULT_BOX_SIZE,
    FRAME_SIZE,
    box_center_in_polygon,
    box_center_outside_polygon,
    detections_at,
    polygon_l_shape,
    polygon_self_intersecting,
    polygon_unit_square,
)
from supervision import Detections

FIXTURE_MODULE: Final = Path(__file__).resolve().parents[1] / "fixtures" / "detections.py"

FORBIDDEN_TOKENS: Final[tuple[str, ...]] = (
    "occupied",
    "empty",
    "uncertain",
    "verdict",
    "polygonzone",
)
"""Modul docstringidagi ro'yxatning MASHINA O'QIYDIGAN nusxasi (kichik harfda)."""

MIN_FIXTURE_LINES: Final = 40
"""QUYI CHEGARA: bo'sh yoki topilmagan faylda skan JIMGINA yashil bo'lardi."""


# --------------------------------------------------------------------------
# MAJBURIYAT 1 — modul tozaligi (fayl MATN sifatida o'qiladi)
# --------------------------------------------------------------------------


@pytest.fixture(scope="module")
def fixture_source() -> str:
    assert FIXTURE_MODULE.is_file(), f"`{FIXTURE_MODULE}` topilmadi — yo'l eskirgan"
    source = FIXTURE_MODULE.read_text(encoding="utf-8")
    assert len(source.splitlines()) >= MIN_FIXTURE_LINES, (
        f"`{FIXTURE_MODULE.name}` dan faqat {len(source.splitlines())} qator "
        f"o'qildi, kamida {MIN_FIXTURE_LINES} kutilgan — quyidagi «yo'q» "
        "da'volari bo'sh matn ustida jimgina o'tib ketardi"
    )
    return source


@pytest.mark.parametrize("token", FORBIDDEN_TOKENS)
def test_fixture_module_never_names_a_verdict(token: str, fixture_source: str) -> None:
    """Taqiqlangan token fixture modulida NA KODDA, NA IZOHDA uchramaydi.

    Sabab modul docstringining birinchi blokida. Bu darvoza `np.empty` ni
    ham ushlaydi va bu ATAYIN — o'sha docstringning oxirgi bandiga qarang.
    """
    assert token not in fixture_source.lower(), (
        f"`{FIXTURE_MODULE.name}` da `{token}` uchradi. Fixture GEOMETRIK "
        "FAKT bilan nomlanadi, kutilgan natija bilan emas — sabab shu "
        "faylning modul docstringida. Darvozani bo'shatish O'RNIGA fixture "
        "nomini fakt bilan qayta nomlang."
    )


def test_fixture_module_does_not_import_the_zone_machinery(fixture_source: str) -> None:
    """MAJBURIYAT 3: moduldan faqat `Detections` konteyneri olinadi.

    Zona hisobi — tekshirilayotgan NARSA. Uni fixture ichiga olib kirish
    testni o'z farazining aks-sadosiga aylantirardi.
    """
    supervision_imports = [
        line
        for line in fixture_source.splitlines()
        if line.startswith(("import supervision", "from supervision"))
    ]
    assert supervision_imports == ["from supervision import Detections"], (
        f"`{FIXTURE_MODULE.name}` `supervision` dan boshqa narsa import qilyapti: "
        f"{supervision_imports}. Ruxsat etilgan yagona import — `Detections`."
    )


# --------------------------------------------------------------------------
# MAJBURIYAT 2 — determinizm
# --------------------------------------------------------------------------


def test_same_arguments_produce_byte_identical_arrays() -> None:
    """Bir xil argument -> BAYT-BAYT teng massiv (ishonch qiymatlari ham).

    ⚠ `xyxy` ni tekshirish YETMAYDI: u argumentdan to'g'ridan-to'g'ri
      hisoblanadi va determinizm savoli u yerda umuman tug'ilmaydi. Xavf
      AYNAN standart `confidence` da — qadalmagan urug' bilan u har
      chaqiruvda o'zgarardi va chegara testlari «gohida yiqiladigan»
      bo'lardi.
    """
    boxes = [(0.10, 0.20, 0.30, 0.40), (0.50, 0.50, 0.60, 0.70)]

    first = detections_at(boxes)
    second = detections_at(boxes)

    assert first.xyxy.tobytes() == second.xyxy.tobytes()
    assert first.confidence is not None
    assert second.confidence is not None
    assert first.confidence.tobytes() == second.confidence.tobytes()


def test_seed_is_a_module_level_constant() -> None:
    """`_SEED` MODUL darajasida `Final` konstanta — funksiya ichida emas.

    Funksiya ichidagi literal urug' ikkinchi generator qo'shilgan kuni
    jimgina ajralib ketardi; modul konstantasi esa yagona manba bo'lib
    qoladi (`frames.py:102-103` naqshi).
    """
    from fixtures import detections as module

    assert module._SEED == 20260808
    assert "_SEED: Final" in FIXTURE_MODULE.read_text(encoding="utf-8")


# --------------------------------------------------------------------------
# `detections_at` — shakl va piksel konversiyasi
# --------------------------------------------------------------------------


def test_detections_at_returns_the_expected_container_and_shape() -> None:
    """Chiqish `Detections`, `xyxy` esa `(n, 4)`."""
    boxes = [(0.10, 0.20, 0.30, 0.40), (0.50, 0.50, 0.60, 0.70), (0.00, 0.00, 0.05, 0.05)]

    result = detections_at(boxes)

    assert isinstance(result, Detections)
    assert result.xyxy.shape == (len(boxes), 4)
    assert result.xyxy.dtype == np.float32


def test_detections_at_converts_normalised_boxes_to_pixels() -> None:
    """0..1 -> piksel: kutilgan qiymat QO'LDA hisoblangan.

    `FRAME_SIZE = (1920, 1080)`:
        x1 = 0.25 * 1920 = 480.0     y1 = 0.50 * 1080 = 540.0
        x2 = 0.75 * 1920 = 1440.0    y2 = 1.00 * 1080 = 1080.0
    """
    assert FRAME_SIZE == (1920, 1080)

    result = detections_at([(0.25, 0.50, 0.75, 1.00)])

    assert result.xyxy[0].tolist() == [480.0, 540.0, 1440.0, 1080.0]


def test_detections_at_accepts_an_explicit_frame_size() -> None:
    """Boshqa ruxsat berilganda arifmetika o'zgarmaydi: 0.5 * 640 = 320."""
    result = detections_at([(0.5, 0.5, 1.0, 1.0)], frame_size=(640, 480))

    assert result.xyxy[0].tolist() == [320.0, 240.0, 640.0, 480.0]


def test_detections_at_handles_no_boxes() -> None:
    """Nolta quti — QONUNIY holat va u `(0, 4)` shaklini beradi.

    Bu holat 05-07 da zarur bo'ladi: kadrda hech nima topilmasligi
    xato emas, natijaning bir turi.
    """
    result = detections_at([])

    assert result.xyxy.shape == (0, 4)
    assert len(result) == 0


def test_detections_at_rejects_mismatched_lengths() -> None:
    """Uzunlik mos kelmasa — ISTISNO, jimgina qisqartirish EMAS.

    `zip` ning standart xulqi uch quti berib ikkitasini o'lchash yo'lini
    ochardi va test o'zi so'ragan narsadan kamrog'ini tekshirardi.
    """
    with pytest.raises(ValueError, match="confidences"):
        detections_at([(0.1, 0.1, 0.2, 0.2)], confidences=[0.9, 0.8])

    with pytest.raises(ValueError, match="class_ids"):
        detections_at([(0.1, 0.1, 0.2, 0.2)], class_ids=[0, 1])


# --------------------------------------------------------------------------
# Poligonlar — shakl NOMDA aytilgan va u LITERAL bilan tasdiqlanadi
# --------------------------------------------------------------------------


def test_unit_square_vertices_are_the_hand_written_ones() -> None:
    """`scale`/`offset` bilan siljish — kutilgan tepaliklar LITERAL yozilgan."""
    assert polygon_unit_square().tolist() == [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]]
    assert polygon_unit_square(scale=0.5, offset=(0.25, 0.25)).tolist() == [
        [0.25, 0.25],
        [0.75, 0.25],
        [0.75, 0.75],
        [0.25, 0.75],
    ]


def test_l_shape_has_six_vertices_and_is_not_convex() -> None:
    """Nom shaklni aytadi: olti tepalik va u QAVARIQ EMAS.

    Qavariqlik shu yerda QO'LDA hisoblanadi (fixture'ning `_is_convex` i
    CHAQIRILMAYDI): aks holda test funksiyani o'zi bilan solishtirardi.
    Ichkaridagi burilish `(0.60,0.40) -> (0.30,0.40) -> (0.30,0.80)`
    uchburchagida ishorani almashtiradi.
    """
    polygon = polygon_l_shape()
    assert polygon.shape == (6, 2)

    signs = set()
    for index in range(len(polygon)):
        a, b, c = polygon[index], polygon[(index + 1) % 6], polygon[(index + 2) % 6]
        cross = (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])
        if cross != 0:
            signs.add(cross > 0)
    assert len(signs) == 2, "L shakli qavariq bo'lib qolgan — nom endi shaklni aytmaydi"


def test_self_intersecting_polygon_really_crosses_itself() -> None:
    """Ikki tomon HAQIQATAN kesishadi — tepalar va kesishuv QO'LDA tekshiriladi.

    Tepalar: (0.2,0.2) (0.8,0.2) (0.2,0.8) (0.8,0.8).
    Tomonlar: 1->2, 2->3, 3->4, 4->1. Kesishadigan juftlik — `2->3` va
    `4->1`:

        2->3: (0.8,0.2) -> (0.2,0.8)      diagonal
        4->1: (0.8,0.8) -> (0.2,0.2)      diagonal

    Ikki diagonal (0.5,0.5) da kesishadi — bu QO'LDA hisoblangan nuqta.
    """
    polygon = polygon_self_intersecting()
    assert polygon.tolist() == [[0.2, 0.2], [0.8, 0.2], [0.2, 0.8], [0.8, 0.8]]

    def orientation(p: np.ndarray, q: np.ndarray, r: np.ndarray) -> bool:
        return bool((q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0]) > 0)

    a, b = polygon[1], polygon[2]  # 2->3
    c, d = polygon[3], polygon[0]  # 4->1
    assert orientation(a, b, c) != orientation(a, b, d)
    assert orientation(c, d, a) != orientation(c, d, b)


# --------------------------------------------------------------------------
# Yordamchilar — NOM AYTGAN FAKT arifmetik natija
# --------------------------------------------------------------------------


def test_box_center_in_polygon_is_at_the_hand_computed_centre() -> None:
    """`polygon_unit_square()` uchun markaz QO'LDA hisoblangan: (0.5, 0.5).

    Tepaliklar `(0,0) (1,0) (1,1) (0,1)`, o'rtachasi `(0.5, 0.5)`.
    `DEFAULT_BOX_SIZE = 0.04` -> yarmi `0.02`, ya'ni quti
    `(0.48, 0.48, 0.52, 0.52)`.

    ⚠ Kutilgan qiymat `box_center_in_polygon` ni CHAQIRIB olinmagan.
    """
    assert DEFAULT_BOX_SIZE == 0.04

    box = box_center_in_polygon(polygon_unit_square())

    assert [round(value, 6) for value in box] == [0.48, 0.48, 0.52, 0.52]


def test_box_center_in_polygon_refuses_a_shape_it_cannot_guarantee() -> None:
    """Qavariq bo'lmagan shaklda funksiya YIQILADI — nomi yolg'on bo'lmasligi uchun.

    Kafolat tepaliklar o'rtachasining qavariq kombinatsiya ekanligiga
    tayanadi; L shaklida yoki kesishgan shaklda o'sha nuqta tashqarida
    qolishi mumkin. Jimgina qaytarish nomni YOLG'ON qilardi.
    """
    for polygon in (polygon_l_shape(), polygon_self_intersecting()):
        with pytest.raises(ValueError, match="qavariq"):
            box_center_in_polygon(polygon)


def test_box_center_outside_polygon_is_beyond_the_bounding_box() -> None:
    """Markaz qamrovchi to'rtburchakdan O'NGDA — kutilgan qiymat QO'LDA hisoblangan.

    `polygon_unit_square(scale=0.5)`: x maksimumi `0.5`.
    `gap = size = 0.04`, `half = 0.02` -> markaz `0.5 + 0.04 + 0.02 = 0.56`,
    y markazi tepaliklar o'rtachasi `0.25`.
    Quti: `(0.54, 0.23, 0.58, 0.27)`.
    """
    box = box_center_outside_polygon(polygon_unit_square(scale=0.5))

    assert [round(value, 6) for value in box] == [0.54, 0.23, 0.58, 0.27]


def test_box_center_outside_polygon_falls_back_to_the_left_side() -> None:
    """O'ngda joy qolmasa — chapdan. `x` maksimumi `1.0`, ya'ni o'ng tomon 0..1 dan chiqadi.

    `polygon_unit_square()`: x minimumi `0.0` -> chap markaz
    `0.0 - 0.04 - 0.02 = -0.06`, ya'ni u ham 0..1 dan tashqarida.
    Shuning uchun bu holat ISTISNO beradi — jimgina kadrdan chiqib
    ketmaydi.
    """
    with pytest.raises(ValueError, match="joy qolmadi"):
        box_center_outside_polygon(polygon_unit_square())

    # O'NG CHETGA suringan poligon: x oralig'i 0.68..0.98.
    #   o'ng:  0.98 + 0.04 + 0.02 = 1.04, ustiga yarmi -> 1.06 > 1.0  SIG'MAYDI
    #   chap:  0.68 - 0.04 - 0.02 = 0.62, ayirib yarmi -> 0.60 >= 0.0 SIG'ADI
    # Ya'ni bu AYNAN chap shoxni yuritadi va quti `(0.60, ..., 0.64, ...)`.
    shifted = polygon_unit_square(scale=0.3, offset=(0.68, 0.10))
    box = box_center_outside_polygon(shifted)
    assert [round(value, 6) for value in box[:1]] == [0.60], (
        "poligon o'ng chetda — quti CHAP tomonga qo'yilishi kerak edi"
    )
