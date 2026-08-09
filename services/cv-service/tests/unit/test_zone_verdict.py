"""`detector/zones.py` darvozasi — ZONA MANTIG'I KONVENTSIYA EMAS (D-09, D-11).

=============================================================================
BU FAYL NIMANI ISBOTLAYDI VA NIMANI ISBOTLAMAYDI.

✅ ISBOTLAYDI: 0..1 <-> piksel konversiyasi va `PolygonZone` verdictining
   MEXANIKASI. Kirish — SINTETIK `sv.Detections` (D-02 ning chokidan
   PASTDA), ya'ni real kadr KERAK EMAS va hech nima taxmin qilinmaydi.

❌ ISBOTLAMAYDI: modelning o'sha zonada haqiqatan mol ko'rgani-ko'rmagani.
   Bu savol chokdan YUQORIDA va u 05-VALIDATION ning «isbotlanmaydi»
   ro'yxatida turadi (D-01).

=============================================================================
FIXTURE'LAR GEOMETRIK FAKT BO'YICHA NOMLANGAN (W0-7, §S-9).

`box_center_in_polygon(polygon)` — «qutining markazi poligon ichida»
degan O'LCHANADIGAN fakt. `box_that_makes_the_zone_busy()` degan nom
esa testni O'Z FARAZINING AKS-SADOSIGA aylantirardi: bunday fixture
zona mantig'ini BILISHI kerak bo'lardi va mantiq noto'g'ri bo'lganda ham
yashil qolardi.

⚠ QAVARIQ BO'LMAGAN shakl uchun fixture ATAYIN yiqiladi (nomi yolg'on
  bo'lmasligi uchun), shuning uchun L-shakl holatlarida qutilar LITERAL
  koordinata bilan beriladi — bu `fixtures/detections.py` ning o'z
  docstringi ko'rsatgan yo'l.

=============================================================================
QO'LDA HISOBLANGAN PIKSEL XARITASI (kadr 1000x500, HAMMA TEST UCHUN BIR XIL)

  polygon_unit_square(scale=0.5)   0..1: (0,0) (0.5,0) (0.5,0.5) (0,0.5)
                                   px:   (0,0) (500,0) (500,250) (0,250)

  polygon_l_shape()                px:   (100,50) (600,50) (600,200)
                                         (300,200) (300,400) (100,400)

  Ishonch qiymatlari ATAYIN `float32` DA AYNIQ ifodalanadigan kasrlar
  (0.125, 0.25, 0.5, 0.75, 0.875): chegara AYNAN tenglikda sinaladi va
  yaxlitlash xatosi testni «gohida yiqiladigan» qilmasligi kerak.
=============================================================================
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

import numpy as np
import pytest
from fixtures.detections import (
    box_center_in_polygon,
    box_center_outside_polygon,
    detections_at,
    polygon_l_shape,
    polygon_unit_square,
)
from sbozor_core.enums import OccupancyVerdict
from supervision import Detections, Position

from app.detector.zones import (
    DEFAULT_REQUIRE_ALL_ANCHORS,
    DEFAULT_TRIGGERING_ANCHORS,
    MIN_POLYGON_POINTS,
    UncertaintyThresholds,
    polygon_to_pixels,
    zone_verdict,
)

MODULE_PATH: Final = Path(__file__).resolve().parents[2] / "app" / "detector" / "zones.py"

MIN_MODULE_LINES: Final = 60
"""QUYI CHEGARA: bo'sh yoki topilmagan faylda «yo'q» da'volari JIMGINA yashil bo'lardi."""

FRAME: Final[tuple[int, int]] = (1000, 500)
"""Barcha testlar uchun BITTA kadr o'lchami — poligon ham, qutilar ham SHU bilan o'giriladi."""

THRESHOLDS: Final = UncertaintyThresholds(uncertain_low=0.25, uncertain_high=0.75)
"""Standart sinov oynasi. ⚠ Bu MAHSULOT qiymati EMAS — chegaralar QATORDAN keladi (D-11)."""

CENTRE_ONLY: Final[tuple[Position, ...]] = (Position.CENTER,)
BOTTOM_ONLY: Final[tuple[Position, ...]] = (Position.BOTTOM_CENTER,)


def _verdict(
    detections: Detections,
    polygon_0_1: np.ndarray,
    *,
    thresholds: UncertaintyThresholds = THRESHOLDS,
    anchors: tuple[Position, ...] = DEFAULT_TRIGGERING_ANCHORS,
    require_all_anchors: bool = DEFAULT_REQUIRE_ALL_ANCHORS,
) -> tuple[OccupancyVerdict, float]:
    """Test yordamchisi — poligonni pikselga o'girib `zone_verdict` ni chaqiradi.

    ⚠ BU YORDAMCHI HECH QANDAY QAROR QABUL QILMAYDI: u faqat ikki
      chaqiruvni bog'laydi. Verdikt mantig'ining bir qismi bu yerga
      tushsa, test tekshirilayotgan koddan boshqa narsani o'lchardi.
    """
    return zone_verdict(
        detections,
        polygon_to_pixels(polygon_0_1, *FRAME),
        thresholds=thresholds,
        anchors=anchors,
        require_all_anchors=require_all_anchors,
    )


# --------------------------------------------------------------------------
# `polygon_to_pixels` — TUZOQ 1 ning mexanizmi
# --------------------------------------------------------------------------


def test_polygon_to_pixels_matches_the_hand_computed_literal() -> None:
    """Rejadagi LITERAL misol: `[(0,0),(1,0),(1,1)]`, `1000x500`.

    (0.0, 0.0) -> (0*1000, 0*500) = (   0,   0)
    (1.0, 0.0) -> (1*1000, 0*500) = (1000,   0)
    (1.0, 1.0) -> (1*1000, 1*500) = (1000, 500)
    """
    polygon = np.array([[0.0, 0.0], [1.0, 0.0], [1.0, 1.0]])

    result = polygon_to_pixels(polygon, 1000, 500)

    assert result.tolist() == [[0, 0], [1000, 0], [1000, 500]]


def test_polygon_to_pixels_returns_int64_because_polygonzone_demands_it() -> None:
    """`PolygonZone` ning kontrakti `npt.NDArray[np.int64]` (TUZOQ 1).

    `float` massiv berilganda kutubxona ichkarida jimgina o'girardi yoki
    umuman boshqacha ishlardi — tur SHU YERDA qulflanadi.
    """
    result = polygon_to_pixels(polygon_unit_square(), 1000, 500)

    assert result.dtype == np.int64


def test_rounding_is_arithmetic_and_not_floor() -> None:
    """Yaxlitlash `round` (yarmi JUFTGA), `floor` EMAS — literal bilan qulflangan.

    Kadr `3x5` ATAYIN tanlangan: ko'paytmalar AYNIQ yarim sonlar bo'ladi
    va uchala qoida uchta boshqa javob beradi.

        x = 0.5 * 3 = 1.5   ->  `floor` 1  |  `round yarmi yuqoriga` 2  |  `rint` 2
        y = 0.5 * 5 = 2.5   ->  `floor` 2  |  `round yarmi yuqoriga` 3  |  `rint` 2

    Kutilgan javob `(2, 2)`, ya'ni bu test `floor` ni HAM,
    «yarmi yuqoriga» ni HAM rad etadi.

    ⚠ `floor` ning zarari sistematik: u HAR koordinatani pastga suradi,
      ya'ni har poligon o'ng va pastki chetidan qisqaradi va kamera
      ruxsati o'zgarganda chegara HAR SAFAR bir tomonga siljiydi.
    """
    polygon = np.array([[0.5, 0.5], [1.0, 0.5], [1.0, 1.0]])

    result = polygon_to_pixels(polygon, 3, 5)

    assert result[0].tolist() == [2, 2]


def test_polygon_with_too_few_points_is_rejected() -> None:
    """Ikki tepalik — kesma, uning ICHKARISI yo'q.

    Jimgina qabul qilinsa `trigger()` abadiy `False` qaytarardi va
    hisobotda «bu rasta hech qachon band bo'lmadi» bo'lib ko'rinardi —
    ya'ni o'lchov yo'qligi yaxshi natijaga o'xshab qolardi.
    """
    assert MIN_POLYGON_POINTS == 3

    with pytest.raises(ValueError, match="tepalik"):
        polygon_to_pixels(np.array([[0.0, 0.0], [1.0, 1.0]]), 1000, 500)


def test_polygon_outside_the_unit_range_is_rejected() -> None:
    """0..1 dan tashqaridagi koordinata — SERVIS CHEGARASIDAGI ikkinchi devor.

    Birinchisi 05-06 da (`POLYGON_OUT_OF_RANGE`, yozish paytida,
    `core-api` da). Bu esa O'QISH paytida, `cv-service` da: normalanmagan
    kontur kamera ruxsati o'zgarganda kadrdan chiqib ketardi (D-07).
    """
    with pytest.raises(ValueError, match="0..1"):
        polygon_to_pixels(np.array([[0.0, 0.0], [1.5, 0.0], [1.0, 1.0]]), 1000, 500)


def test_polygon_with_a_wrong_shape_is_rejected() -> None:
    """`(n, 2)` dan boshqa shakl jimgina qabul qilinmaydi."""
    with pytest.raises(ValueError, match=r"\(n, 2\)"):
        polygon_to_pixels(np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.0, 1.0, 1.0]]), 1000, 500)


# --------------------------------------------------------------------------
# VERDIKT — geometriya
# --------------------------------------------------------------------------


def test_single_high_confidence_box_with_its_centre_inside_is_occupied() -> None:
    """Markazi poligon ichidagi yuqori-ishonchli quti -> `occupied`.

    Qo'lda hisob: `polygon_unit_square(scale=0.5)` tepaliklarining
    o'rtachasi `(0.25, 0.25)`, ya'ni piksel markazi `(250, 125)` va u
    `(0,0)-(500,250)` to'rtburchagi ICHIDA.
    Ishonch `0.875 >= uncertain_high (0.75)`.
    """
    polygon = polygon_unit_square(scale=0.5)
    detections = detections_at(
        [box_center_in_polygon(polygon)], confidences=[0.875], frame_size=FRAME
    )

    verdict, confidence = _verdict(detections, polygon)

    assert verdict == OccupancyVerdict.OCCUPIED
    assert confidence == pytest.approx(0.875)


def test_box_outside_the_polygon_is_empty_however_confident_it_is() -> None:
    """Poligondan tashqaridagi quti -> `empty`, ISHONCH NECHTA BO'LSA HAM.

    ⚠ Ishonch `1.0` — ya'ni model o'sha qutiga MUTLAQO ishonadi. Verdikt
      baribir `empty`, chunki savol «modelga ishonasanmi?» emas, «SHU
      ZONADA mol bormi?». Qaytarilgan ishonch esa `0.0`: zonada
      o'lchanadigan hech nima bo'lmagan.
    """
    polygon = polygon_unit_square(scale=0.5)
    detections = detections_at(
        [box_center_outside_polygon(polygon)], confidences=[1.0], frame_size=FRAME
    )

    verdict, confidence = _verdict(detections, polygon)

    assert verdict == OccupancyVerdict.EMPTY
    assert confidence == 0.0


def test_empty_detections_are_empty_with_zero_confidence() -> None:
    """Nolta detektsiya -> `empty`, `0.0` — YOZILMAGAN QIYMAT YO'Q.

    `None` yoki `nan` qaytarish `occupancy_events.confidence` ning
    `NOT NULL` + `CHECK 0..1` shartlariga urilardi va nosozlik BAZADA,
    aniqlash tugagandan keyin ko'rinardi.
    """
    polygon = polygon_unit_square(scale=0.5)

    verdict, confidence = _verdict(detections_at([], frame_size=FRAME), polygon)

    assert verdict == OccupancyVerdict.EMPTY
    assert confidence == 0.0


def test_box_inside_the_bounding_box_but_outside_the_l_shape_is_empty() -> None:
    """L-shaklning O'YIG'IDAGI quti -> `empty`, garchi u qamrovchi to'rtburchak ichida.

    ⚠⚠ AYNAN SHU HOLAT UCHUN `supervision` ISHLATILADI. Qamrovchi
       to'rtburchak (bounding box) tekshiruvi bu qutini «ichkarida» deb
       hisoblardi — va real rasta qatorlari to'g'ri to'rtburchak EMAS,
       ya'ni bu holat Karmanada TEZ-TEZ uchraydi.

    Qo'lda hisob (kadr 1000x500):
        L px: (100,50) (600,50) (600,200) (300,200) (300,400) (100,400)
        qamrovchi to'rtburchak: x 100..600, y 50..400
        quti markazi (0.50, 0.60) -> px (500, 300)
            -> qamrovchida ICHKARIDA (100<=500<=600, 50<=300<=400)
            -> L ning O'ZIDA TASHQARIDA: y=300 da shakl faqat x 100..300
    """
    polygon = polygon_l_shape()
    detections = detections_at([(0.48, 0.58, 0.52, 0.62)], confidences=[0.875], frame_size=FRAME)

    verdict, confidence = _verdict(detections, polygon)

    assert verdict == OccupancyVerdict.EMPTY
    assert confidence == 0.0


def test_box_inside_the_l_shape_itself_is_occupied() -> None:
    """L-shaklning YUQORI TASMASIDAGI quti -> `occupied` (oldingi testning jufti).

    Qo'lda hisob: quti markazi `(0.20, 0.20)` -> px `(200, 100)`, u esa
    yuqori tasmaning ichida (x 100..600, y 50..200).

    ⚠ Bu juftlik BIRGA ma'noli: yolg'iz oldingi test «hamma narsa
      `empty`» degan buzuq kod ostida ham yashil bo'lardi.
    """
    polygon = polygon_l_shape()
    detections = detections_at([(0.18, 0.18, 0.22, 0.22)], confidences=[0.875], frame_size=FRAME)

    verdict, confidence = _verdict(detections, polygon)

    assert verdict == OccupancyVerdict.OCCUPIED
    assert confidence == pytest.approx(0.875)


def test_the_most_confident_box_inside_the_zone_decides() -> None:
    """Zonada bir necha quti bo'lsa — ENG YUQORI ishonch hal qiladi.

    ⚠ Tashqaridagi quti ishonchi `1.0` bo'lsa ham hisobga OLINMAYDI:
      aks holda qo'shni rastadagi savdo bu rastani band qilib ko'rsatardi.
    """
    polygon = polygon_unit_square(scale=0.5)
    inside = box_center_in_polygon(polygon)
    outside = box_center_outside_polygon(polygon)
    detections = detections_at(
        [inside, outside, (0.24, 0.24, 0.26, 0.26)],
        confidences=[0.25, 1.0, 0.5],
        frame_size=FRAME,
    )

    verdict, confidence = _verdict(detections, polygon)

    # Ichkaridagilar: 0.25 va 0.5 -> eng yuqorisi 0.5, ya'ni `uncertain`.
    # Tashqaridagi 1.0 hisobga olinmadi, aks holda javob `occupied` bo'lardi.
    assert verdict == OccupancyVerdict.UNCERTAIN
    assert confidence == pytest.approx(0.5)


# --------------------------------------------------------------------------
# CHEGARALAR — ARGUMENT, `import` EMAS (D-11)
# --------------------------------------------------------------------------


def test_confidence_between_the_thresholds_is_uncertain() -> None:
    """`low <= ishonch < high` -> `uncertain` — «MODEL BILMAYDI».

    `0.25 <= 0.5 < 0.75`. Bu verdikt zonani nazoratchi navbatiga
    qo'yadi; u «rasta yarim band» degani EMAS.
    """
    polygon = polygon_unit_square(scale=0.5)
    detections = detections_at(
        [box_center_in_polygon(polygon)], confidences=[0.5], frame_size=FRAME
    )

    verdict, confidence = _verdict(detections, polygon)

    assert verdict == OccupancyVerdict.UNCERTAIN
    assert confidence == pytest.approx(0.5)


def test_raising_uncertain_high_turns_occupied_into_uncertain() -> None:
    """AYNI DETEKTSIYALAR, boshqa chegara -> boshqa verdikt (D-11 ning butun ma'nosi).

    Ishonch `0.875` (o'zgarmaydi):
        high = 0.75  ->  0.875 >= 0.75          -> `occupied`
        high = 0.95  ->  0.25 <= 0.875 < 0.95   -> `uncertain`

    ⚠ Agar chegara modul konstantasidan o'qilsa, bu test YOZIB
      BO'LMASDI — «sozlash SQL bilan, migratsiyasiz» va'dasi shu bilan
      isbotlanadi.
    """
    polygon = polygon_unit_square(scale=0.5)
    detections = detections_at(
        [box_center_in_polygon(polygon)], confidences=[0.875], frame_size=FRAME
    )

    occupied, _ = _verdict(detections, polygon, thresholds=UncertaintyThresholds(0.25, 0.75))
    uncertain, _ = _verdict(detections, polygon, thresholds=UncertaintyThresholds(0.25, 0.95))

    assert occupied == OccupancyVerdict.OCCUPIED
    assert uncertain == OccupancyVerdict.UNCERTAIN


def test_confidence_below_uncertain_low_is_empty_but_keeps_its_measurement() -> None:
    """`ishonch < low` -> `empty`, LEKIN o'lchov qaytariladi.

    `0.125 < 0.25`. Qaytarilgan `0.125` — `0.0` EMAS, va farq ma'noli:
    `0.0` «zonada o'lchanadigan hech nima yo'q» degani, `0.125` esa
    «nimadir bor, lekin model unga ishonmaydi». Real kadrlar kelganda
    chegaralar AYNAN shu taqsimotdan (`percentile_cont`) sozlanadi.
    """
    polygon = polygon_unit_square(scale=0.5)
    detections = detections_at(
        [box_center_in_polygon(polygon)], confidences=[0.125], frame_size=FRAME
    )

    verdict, confidence = _verdict(detections, polygon)

    assert verdict == OccupancyVerdict.EMPTY
    assert confidence == pytest.approx(0.125)


@pytest.mark.parametrize(
    ("confidence", "expected"),
    [
        (0.75, OccupancyVerdict.OCCUPIED),
        (0.25, OccupancyVerdict.UNCERTAIN),
    ],
)
def test_threshold_boundaries_are_inclusive(confidence: float, expected: OccupancyVerdict) -> None:
    """AYNAN chegaradagi ishonch YUQORIGI toifaga tegishli.

    `postprocess.raw_to_detections` bilan bir xil qaror va bir xil sabab:
    «chegarada» holati ikki modulda ikki xil o'qilsa, chegarani sozlash
    natijani oldindan aytib bo'lmaydigan qilardi.

    ⚠ Ikkala qiymat ham `float32` da AYNIQ (`0.75 = 3/4`, `0.25 = 1/4`),
      ya'ni bu test yaxlitlash xatosiga tayanmaydi.
    """
    polygon = polygon_unit_square(scale=0.5)
    detections = detections_at(
        [box_center_in_polygon(polygon)], confidences=[confidence], frame_size=FRAME
    )

    verdict, _ = _verdict(detections, polygon)

    assert verdict == expected


def test_inverted_uncertain_window_is_rejected() -> None:
    """`low > high` — ISTISNO, jimgina «ishlash» EMAS.

    Teskari oyna hech qanday xato bermasdan ishlardi: har ishonch yo
    `empty` yo `occupied` bo'lib, `uncertain` navbati BUTUNLAY bo'sh
    qolardi. Nazoratchi hech nima ko'rmasdi va hisobotda bu «hammasi
    aniq» bo'lib ko'rinardi.
    """
    with pytest.raises(ValueError, match="TESKARI"):
        UncertaintyThresholds(uncertain_low=0.9, uncertain_high=0.1)


@pytest.mark.parametrize("bad", [-0.1, 1.1])
def test_thresholds_outside_the_unit_range_are_rejected(bad: float) -> None:
    """Chegara 0..1 dan tashqarida bo'lolmaydi — ishonch shu shkalada."""
    with pytest.raises(ValueError, match="0..1"):
        UncertaintyThresholds(uncertain_low=bad, uncertain_high=bad)


# --------------------------------------------------------------------------
# ANKORLAR — SOZLAMA, VA UNING HAQIQATAN ULANGANI O'LCHANADI (D-09)
# --------------------------------------------------------------------------


def test_switching_the_anchor_changes_the_verdict() -> None:
    """`CENTER` va `BOTTOM_CENTER` BOSHQA javob beradi — sozlama ULANGAN.

    Qo'lda hisob (kadr 1000x500, poligon px `(0,0)-(500,250)`):
        quti 0..1: (0.15, 0.35, 0.35, 0.55)
        px:        (150, 175, 350, 275)
        CENTER        = (250, 225)  ->  225 <= 250   ICHKARIDA
        BOTTOM_CENTER = (250, 275)  ->  275  > 250   TASHQARIDA

    ⚠ Bu test bo'lmasa `anchors` argumenti QABUL QILINIB, e'tiborga
      OLINMASLIGI mumkin edi — va u holda D-09 «bajarilgan» ko'rinardi.
    """
    polygon = polygon_unit_square(scale=0.5)
    detections = detections_at([(0.15, 0.35, 0.35, 0.55)], confidences=[0.875], frame_size=FRAME)

    by_centre, _ = _verdict(detections, polygon, anchors=CENTRE_ONLY)
    by_bottom, _ = _verdict(detections, polygon, anchors=BOTTOM_ONLY)

    assert by_centre == OccupancyVerdict.OCCUPIED
    assert by_bottom == OccupancyVerdict.EMPTY


def test_require_all_anchors_switches_between_and_and_or() -> None:
    """⚠⚠ O'LCHANGAN FAKT: `require_all_anchors` juftlikning MA'NOSINI o'zgartiradi.

    Ayni quti (markazi ichkarida, pastki markazi tashqarida) va ayni
    ankor juftligi bilan:

        require_all_anchors=True   (AND, KUTUBXONA STANDARTI) -> `empty`
        require_all_anchors=False  (OR,  BIZNING STANDART)    -> `occupied`

    ⚠ RESEARCH §B.4 ning imzo sitatasida bu parametr YO'Q edi — u faqat
      haqiqiy `supervision` 0.30.0 imzosini o'lchaganda topildi. AND
      ostida `(CENTER, BOTTOM_CENTER)` juftligi D-09 ning MAQSADIGA ZID
      ishlaydi: juftlik `BOTTOM_CENTER` ning qo'shni zonaga tushish
      xavfini yumshatish uchun tanlangan edi, AND esa uni kuchaytiradi.

    Bu test QIYMATNI emas, MEXANIZMNI qulflaydi: ikkala rejim ham
    argument bilan tanlanadi va ikkalasi ham o'lchangan.
    """
    polygon = polygon_unit_square(scale=0.5)
    detections = detections_at([(0.15, 0.35, 0.35, 0.55)], confidences=[0.875], frame_size=FRAME)
    both = (Position.CENTER, Position.BOTTOM_CENTER)

    conjunction, _ = _verdict(detections, polygon, anchors=both, require_all_anchors=True)
    disjunction, _ = _verdict(detections, polygon, anchors=both, require_all_anchors=False)

    assert conjunction == OccupancyVerdict.EMPTY
    assert disjunction == OccupancyVerdict.OCCUPIED


def test_the_shipped_defaults_are_the_documented_ones() -> None:
    """D-09 ning juftligi va o'lchov bilan tanlangan OR rejimi — konstantalarda.

    ⚠ Standart FUNKSIYADA emas, MODUL KONSTANTASIDA: `zone_verdict()`
      ikkalasini ham argument sifatida TALAB qiladi, ya'ni chaqiruvchi
      tanlovni ko'rmasdan qila olmaydi.
    """
    assert DEFAULT_TRIGGERING_ANCHORS == (Position.CENTER, Position.BOTTOM_CENTER)
    assert DEFAULT_REQUIRE_ALL_ANCHORS is False


# --------------------------------------------------------------------------
# MODUL TOZALIGI — §S-8 chegarasi va «qo'lda yozilmaydi» taqig'i
# --------------------------------------------------------------------------


@pytest.fixture(scope="module")
def module_source() -> str:
    assert MODULE_PATH.is_file(), f"`{MODULE_PATH}` topilmadi — yo'l eskirgan"
    source = MODULE_PATH.read_text(encoding="utf-8")
    assert len(source.splitlines()) >= MIN_MODULE_LINES, (
        f"`{MODULE_PATH.name}` dan faqat {len(source.splitlines())} qator "
        f"o'qildi, kamida {MIN_MODULE_LINES} kutilgan — quyidagi «yo'q» "
        "da'volari bo'sh matn ustida jimgina o'tib ketardi"
    )
    return source


def test_module_uses_the_library_zone_machinery(module_source: str) -> None:
    """`PolygonZone` HAQIQATAN quriladi — mexanizm kutubxonaniki."""
    assert "PolygonZone(" in module_source


def test_module_does_not_hand_roll_point_in_polygon(module_source: str) -> None:
    """Qo'lda yozilgan nuqta-poligon funksiyasi YO'Q (RESEARCH §B.4).

    Bunday funksiya ikki narsani birdan buzardi: kutubxonaning sinovdan
    o'tgan qirra holatlarini qaytadan ixtiro qilardi va test o'sha qo'lda
    yozilgan mantiqni O'ZI bilan solishtirardi.
    """
    offenders = [
        line
        for line in module_source.splitlines()
        if line.lstrip().startswith("def ")
        and "point" in line.lower()
        and "polygon" in line.lower()
    ]
    assert offenders == [], (
        f"`{MODULE_PATH.name}` da qo'lda yozilgan nuqta-poligon funksiyasi: "
        f"{offenders}. Mexanizm `supervision` da bor va u MIT."
    )


def test_module_does_not_read_settings(module_source: str) -> None:
    """Chegaralar ARGUMENT bo'lib kiradi, `import` emas (§S-8, D-11)."""
    offenders = [
        line
        for line in module_source.splitlines()
        if line.startswith(("from app.settings", "import app.settings"))
    ]
    assert offenders == [], (
        f"`{MODULE_PATH.name}` `Settings` ni o'qiyapti: {offenders}. Chegaralar "
        "`occupancy_events.thresholds_version` bilan QATORDA yashaydi (D-11)."
    )


@pytest.mark.parametrize("banned", ["ultralytics", "torch", "rfdetr"])
def test_module_never_imports_a_forbidden_stack(banned: str, module_source: str) -> None:
    """`ultralytics` (AGPL) va trening steki import qilinmaydi.

    ⚠ `ultralytics` ni ALOHIDA qayd etish sababi bor: `PolygonZone` ning
      RASMIY misoli aynan undan boshlanadi (RESEARCH §B.4, Tuzoq 3).
      Misolni ko'chirib olish AGPL paketni tijoriy SaaS ga olib kirardi.
    """
    offenders = [
        line
        for line in module_source.splitlines()
        if line.startswith((f"import {banned}", f"from {banned}"))
    ]
    assert offenders == [], f"`{MODULE_PATH.name}` `{banned}` ni import qilyapti: {offenders}"


def test_module_says_out_loud_that_tiling_is_not_implemented(module_source: str) -> None:
    """D-10 ning sababi KODDA yozilgan, faqat rejada emas.

    «Tiling yo'q» — bu unutilgan ish emas, ONGLI qaror va uning qayta
    ko'rish sharti o'lchanadigan (rasta kadrda <32 px). Sabab kodda
    turmasa, keyingi o'quvchi uni kamchilik deb o'qib, dalilsiz
    qo'shardi.
    """
    lowered = module_source.lower()
    assert "sahi" in lowered or "tiling" in lowered
    assert "32 px" in lowered
