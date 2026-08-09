"""`detector/postprocess.py` darvozasi — ARIFMETIKA, MODEL EMAS (§4.3).

=============================================================================
BU FAYL NIMANI ISBOTLAYDI VA NIMANI ISBOTLAMAYDI.

✅ ISBOTLAYDI: xom tenzordan qutiga o'tish arifmetikasi qo'lda hisoblangan
   javobga TENG. Kirish `np.array(...)` bilan qo'lda yoziladi, kutilgan
   chiqish esa qo'lda hisoblanadi va LITERAL yoziladi.

❌ ISBOTLAMAYDI: modelning band/bo'sh qarori TO'G'RIMI. Bu savol real
   Karmana kadrini talab qiladi va u 05-VALIDATION ning «isbotlanmaydi»
   ro'yxatida ochiq turadi (D-01). ⚠ BU FAYLNING YASHILLIGI O'SHA
   SAVOLGA JAVOB EMAS.

=============================================================================
KUTILGAN QIYMAT TEKSHIRILAYOTGAN KOD BILAN HISOBLANMAYDI.

`sigmoid()` kutilgan ishonchni olish uchun CHAQIRILMAYDI — barcha
ehtimolliklar qo'lda hisoblangan o'nlik literal sifatida yozilgan
(`test_periods.py`, `test_rtsp_url.py` va `test_detection_fixtures.py`
bilan bir xil qoida). Aks holda test faqat «funksiya o'zi bilan mos»
deganini isbotlardi.

Qo'lda hisoblangan sigmoid qiymatlari (`1 / (1 + e^-x)`):

    x = -10   ->  0.0000453978687
    x =  -5   ->  0.0066928509243
    x =  -4   ->  0.0179862099621
    x =  -3   ->  0.0474258731776
    x =  -2   ->  0.1192029220221
    x =  -1   ->  0.2689414213700
    x =   0   ->  0.5              <- AYNIQ, yaxlitlashsiz
    x = 0.5   ->  0.6224593312019
    x =   1   ->  0.7310585786300
    x =   2   ->  0.8807970779779
    x =   3   ->  0.9525741268224
    x =   5   ->  0.9933071490757

=============================================================================
⚠ SABOTAJ NISHONI: `BACKGROUND_CLASS_INDEX` ni `0` dan `1` ga o'zgartirish
  KAMIDA UCHTA testni qizartirishi SHART
  (`..._keeps_the_original_label_index`, `..._maps_every_query_to_its_hand_
  written_class`, `..._threshold_is_inclusive`). Agar u qizarmasa —
  darvoza background ustunini umuman o'lchamayotgan bo'ladi.
=============================================================================
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

import numpy as np
import pytest
from supervision import Detections

from app.detector.postprocess import (
    BACKGROUND_CLASS_INDEX,
    MIN_CLASS_COLUMNS,
    raw_to_detections,
    sigmoid,
)

MODULE_PATH: Final = Path(__file__).resolve().parents[2] / "app" / "detector" / "postprocess.py"

MIN_MODULE_LINES: Final = 60
"""QUYI CHEGARA: bo'sh yoki topilmagan faylda «yo'q» da'volari JIMGINA yashil bo'lardi."""

# Qo'lda hisoblangan sigmoid qiymatlari — modul docstringidagi jadvaldan.
SIGMOID_MINUS_ONE: Final = 0.2689414213700
SIGMOID_ZERO: Final = 0.5
SIGMOID_HALF: Final = 0.6224593312019
SIGMOID_ONE: Final = 0.7310585786300
SIGMOID_TWO: Final = 0.8807970779779
SIGMOID_THREE: Final = 0.9525741268224
SIGMOID_FIVE: Final = 0.9933071490757

FLOAT32_TOLERANCE: Final = 1e-6
"""`confidence` `float32` ga o'giriladi — uning aniqligi ~1e-7.

⚠ `SIGMOID_ZERO` bundan ISTISNO: `0.5` `float32` da ham, `float64` da ham
  AYNIQ ifodalanadi, ya'ni u AYNIQ tenglik bilan tekshiriladi va u tekshiruv
  chegara inklyuzivligining butun asosi.
"""


# --------------------------------------------------------------------------
# `sigmoid` — sof funksiya, alohida o'lchanadi
# --------------------------------------------------------------------------


def test_sigmoid_of_zero_is_exactly_one_half() -> None:
    """`sigmoid(0) == 0.5` — AYNIQ, `approx` siz.

    Qiymat ikkala shoxda ham `1 / (1 + 1)` ga tushadi va `0.5` ikkilik
    kasrda AYNIQ ifodalanadi. Bu tenglikni `approx` bilan yumshatish
    chegara inklyuzivligi testining ma'nosini yo'qotardi: o'sha test
    AYNAN `confidence == threshold` holatiga tayanadi.
    """
    assert sigmoid(np.array([0.0]))[0] == 0.5


def test_sigmoid_matches_the_hand_computed_table() -> None:
    """Jadvaldagi olti nuqta — literal, `sigmoid` ni chaqirmasdan yozilgan."""
    values = np.array([-1.0, 0.0, 0.5, 1.0, 2.0, 3.0])

    result = sigmoid(values)

    assert result.tolist() == pytest.approx(
        [
            SIGMOID_MINUS_ONE,
            SIGMOID_ZERO,
            SIGMOID_HALF,
            SIGMOID_ONE,
            SIGMOID_TWO,
            SIGMOID_THREE,
        ],
        abs=1e-12,
    )


def test_sigmoid_does_not_overflow_on_large_magnitudes() -> None:
    """Katta logitda `nan`/`inf` CHIQMAYDI — sonli barqaror shoxlanish.

    ⚠ Sodda `1 / (1 + exp(-x))` bu yerda `exp(1000)` = `inf` beradi va
      natija `nan` bo'lardi. `nan` esa `>=` solishtirishida JIMGINA
      `False` qaytaradi — quti sababsiz tushib qolardi va hech qayerda
      xato KO'RINMASDI. Aynan shu jim yo'l uchun test bor.
    """
    result = sigmoid(np.array([-1000.0, 1000.0]))

    assert not np.isnan(result).any()
    assert result[0] == 0.0
    assert result[1] == 1.0


# --------------------------------------------------------------------------
# BACKGROUND USTUNI — modulning eng xavfli qadami
# --------------------------------------------------------------------------


def test_background_removal_keeps_the_original_label_index() -> None:
    """Ustun olib tashlangandan keyin `class_id` ASL fazoda qoladi.

    ⚠⚠ SABOTAJ NISHONI. Qo'lda hisob:

        logitlar        [ 5.0,  -1.0,   3.0,   0.5]
        ehtimolliklar   [0.99331, 0.26894, 0.95257, 0.62246]

        background = ustun 0 -> qoladi: ustunlar 1, 2, 3
        kesilgandagi ballar  [0.26894, 0.95257, 0.62246]
        eng kattasi          -> kesilgan pozitsiya 1
        ASL indeks           -> 2          <- SURILMAGAN javob
        (agar pozitsiya to'g'ridan-to'g'ri yozilsa -> 1, ya'ni SURILGAN)

    Ya'ni `1` javobi «bittaga surilgan» nosozlikning AYNAN o'zi, va shu
    sababdan bu test uni ushlaydi.
    """
    dets = np.array([[0.5, 0.5, 0.2, 0.4]])
    labels = np.array([[5.0, -1.0, 3.0, 0.5]])

    result = raw_to_detections(dets, labels, frame_size=(1000, 500), confidence_threshold=0.0)

    assert result.class_id is not None
    assert result.class_id.tolist() == [2], (
        "background ustuni olib tashlangandan keyin klass indeksi SURILDI — "
        "RESEARCH §B.2 ogohlantirgan JIMGINA noto'g'ri javob"
    )
    assert result.confidence is not None
    assert result.confidence[0] == pytest.approx(SIGMOID_THREE, abs=FLOAT32_TOLERANCE)


def test_background_removal_maps_every_query_to_its_hand_written_class() -> None:
    """Uch so'rov — har birining ASL indeksi QO'LDA yozilgan.

    Qo'lda hisob (background = ustun 0, ya'ni qolgan ustunlar 1, 2, 3):

        qator 0  [ 5.0, -1.0,  3.0,  0.5]  -> ballar [0.269, 0.953, 0.622]
                 eng kattasi pozitsiya 1   -> ASL 2
        qator 1  [-4.0,  2.0,  0.0, -3.0]  -> ballar [0.881, 0.500, 0.047]
                 eng kattasi pozitsiya 0   -> ASL 1
        qator 2  [ 0.0, -2.0, -5.0,  1.0]  -> ballar [0.119, 0.007, 0.731]
                 eng kattasi pozitsiya 2   -> ASL 3

    ⚠ KUTILGAN JAVOB `[2, 1, 3]`, kesilgan pozitsiyalar esa `[1, 0, 2]` —
      UCHALASI HAM bittaga farq qiladi. Bu ATAYIN tanlangan: surilish
      nosozligi shu holatda HAR QATORDA ko'rinadi.
    """
    dets = np.array(
        [
            [0.5, 0.5, 0.2, 0.4],
            [0.2, 0.2, 0.1, 0.1],
            [0.8, 0.8, 0.1, 0.1],
        ]
    )
    labels = np.array(
        [
            [5.0, -1.0, 3.0, 0.5],
            [-4.0, 2.0, 0.0, -3.0],
            [0.0, -2.0, -5.0, 1.0],
        ]
    )

    result = raw_to_detections(dets, labels, frame_size=(1000, 500), confidence_threshold=0.0)

    assert result.class_id is not None
    assert result.class_id.tolist() == [2, 1, 3]
    assert result.confidence is not None
    assert result.confidence.tolist() == pytest.approx(
        [SIGMOID_THREE, SIGMOID_TWO, SIGMOID_ONE], abs=FLOAT32_TOLERANCE
    )


def test_background_class_index_is_a_module_constant_with_an_open_caveat() -> None:
    """Indeks MODUL konstantasi va uning TAXMIN ekani docstringda OCHIQ.

    ⚠ Bu qiymat o'lchangan fakt EMAS (`[LOW confidence]`): rasmiy hujjat
      «background ustunini olib tashlang» deydi, lekin indeksni AYTMAYDI.
      Uni haqiqiy artefakt bilan tekshirish `model` markerli testning
      vazifasi. Konstantaning O'ZI va uning ogohlantirishi shu sababdan
      darvoza ostida: izohsiz qattiq raqam keyingi o'quvchiga uni
      o'lchangan fakt bo'lib ko'rinardi.
    """
    assert BACKGROUND_CLASS_INDEX == 0

    source = MODULE_PATH.read_text(encoding="utf-8")
    assert "BACKGROUND_CLASS_INDEX: Final = 0" in source
    assert "LOW confidence" in source, (
        "konstantaning TAXMIN ekani modulda ochiq yozilmagan — keyingi "
        "o'quvchi uni o'lchangan fakt deb o'qirdi"
    )


# --------------------------------------------------------------------------
# `cxcywh` (normalangan) -> `xyxy` (piksel)
# --------------------------------------------------------------------------


def test_box_conversion_matches_the_hand_computed_pixels() -> None:
    """Rejadagi LITERAL misol — qo'lda hisoblangan.

    cx=0.5, cy=0.5, w=0.2, h=0.4   kadr 1000x500

    x1 = (0.5 - 0.2/2) * 1000 = 0.4 * 1000 = 400
    y1 = (0.5 - 0.4/2) *  500 = 0.3 *  500 = 150
    x2 = (0.5 + 0.2/2) * 1000 = 0.6 * 1000 = 600
    y2 = (0.5 + 0.4/2) *  500 = 0.7 *  500 = 350
    """
    dets = np.array([[0.5, 0.5, 0.2, 0.4]])
    labels = np.array([[-10.0, 0.0]])

    result = raw_to_detections(dets, labels, frame_size=(1000, 500), confidence_threshold=0.5)

    assert result.xyxy.tolist() == [[400.0, 150.0, 600.0, 350.0]]


def test_box_conversion_follows_the_frame_size_argument() -> None:
    """Boshqa kadr o'lchamida arifmetika o'zgarmaydi — faqat ko'paytuvchi.

    cx=0.5, cy=0.5, w=0.5, h=0.5   kadr 640x480
    x1 = 0.25 * 640 = 160     y1 = 0.25 * 480 = 120
    x2 = 0.75 * 640 = 480     y2 = 0.75 * 480 = 360
    """
    dets = np.array([[0.5, 0.5, 0.5, 0.5]])
    labels = np.array([[-10.0, 0.0]])

    result = raw_to_detections(dets, labels, frame_size=(640, 480), confidence_threshold=0.0)

    assert result.xyxy.tolist() == [[160.0, 120.0, 480.0, 360.0]]


def test_box_outside_the_frame_is_not_clipped() -> None:
    """Kadrdan chiqqan quti QIRQILMAYDI — markaz siljimaydi.

        cx=0.05, cy=0.05, w=0.2, h=0.2   kadr 1000x500
        x1 = (0.05 - 0.1) * 1000 = -50      <- MANFIY va shunday qoladi
        y1 = (0.05 - 0.1) *  500 = -25
        x2 = (0.05 + 0.1) * 1000 = 150
        y2 = (0.05 + 0.1) *  500 =  75

    ⚠ Chegaraga yopishtirish (`clip`) markazni `(50, 25)` dan `(75, 37.5)`
      ga SILJITARDI — ya'ni zona qarori kadr chetida jimgina o'zgarardi.
    """
    dets = np.array([[0.05, 0.05, 0.2, 0.2]])
    labels = np.array([[-10.0, 0.0]])

    result = raw_to_detections(dets, labels, frame_size=(1000, 500), confidence_threshold=0.0)

    assert result.xyxy.tolist() == [[-50.0, -25.0, 150.0, 75.0]]


# --------------------------------------------------------------------------
# CHEGARA — INKLYUZIV
# --------------------------------------------------------------------------


def test_confidence_threshold_is_inclusive() -> None:
    """`confidence == threshold` bo'lgan quti QOLADI, pastdagisi TUSHADI.

    Uch so'rov, chegara `0.5`:

        qator 0  logit  0.0  -> 0.5      AYNAN chegarada  -> QOLADI
        qator 1  logit -1.0  -> 0.26894  pastda           -> TUSHADI
        qator 2  logit  3.0  -> 0.95257  yuqorida         -> QOLADI

    Qo'lda hisoblangan omon qolgan qutilar (kadr 1000x500):

        qator 0  cx=0.5 cy=0.5 w=0.2 h=0.4 -> (400, 150, 600, 350)
        qator 2  cx=0.9 cy=0.9 w=0.2 h=0.2 -> (800, 400, 1000, 500)

    ⚠ Chegara EKSKLYUZIV bo'lganda qator 0 tushib qolardi va natija bir
      qutili bo'lardi — test aynan shu farqni o'lchaydi.
    """
    dets = np.array(
        [
            [0.5, 0.5, 0.2, 0.4],
            [0.1, 0.1, 0.02, 0.04],
            [0.9, 0.9, 0.2, 0.2],
        ]
    )
    labels = np.array([[-10.0, 0.0], [-10.0, -1.0], [-10.0, 3.0]])

    result = raw_to_detections(dets, labels, frame_size=(1000, 500), confidence_threshold=0.5)

    assert len(result) == 2
    assert result.xyxy.tolist() == [
        [400.0, 150.0, 600.0, 350.0],
        [800.0, 400.0, 1000.0, 500.0],
    ]
    assert result.confidence is not None
    # AYNIQ tenglik: chegaradagi qiymat `0.5` va u `float32` da ham aniq.
    assert result.confidence[0] == 0.5
    assert result.confidence[1] == pytest.approx(SIGMOID_THREE, abs=FLOAT32_TOLERANCE)


def test_threshold_above_every_score_yields_an_empty_result() -> None:
    """Hech biri chegaradan o'tmasa — BO'SH natija, ISTISNO EMAS.

    «Kadrda hech nima topilmadi» — nosozlik emas, natijaning bir turi
    (`fixtures/detections.py` ning `detections_at([])` qarori bilan bir
    xil). Istisno tashlash chaqiruvchini har kadrda `try` yozishga
    majburlardi va o'sha `try` haqiqiy xatolarni ham yutardi.
    """
    dets = np.array([[0.5, 0.5, 0.2, 0.4], [0.1, 0.1, 0.1, 0.1]])
    labels = np.array([[-10.0, 0.0], [-10.0, -1.0]])

    result = raw_to_detections(dets, labels, frame_size=(1000, 500), confidence_threshold=0.99)

    assert isinstance(result, Detections)
    assert len(result) == 0
    assert result.xyxy.shape == (0, 4)


# --------------------------------------------------------------------------
# BO'SH KIRISH va SHAKL TEKSHIRUVLARI
# --------------------------------------------------------------------------


def test_empty_input_yields_empty_detections() -> None:
    """Nolta so'rov — QONUNIY kirish va u bo'sh `Detections` beradi."""
    result = raw_to_detections(
        np.zeros((0, 4)),
        np.zeros((0, 3)),
        frame_size=(1000, 500),
        confidence_threshold=0.5,
    )

    assert isinstance(result, Detections)
    assert len(result) == 0
    assert result.xyxy.shape == (0, 4)


def test_leading_batch_axis_is_accepted_and_gives_the_same_answer() -> None:
    """`(1, n, k)` va `(n, k)` — AYNAN bir xil natija.

    Eksport `batch_size=1` bilan qilinadi (RESEARCH §B.2), ya'ni graf
    odatda yetakchi partiya o'qi bilan qaytaradi. Ikkala shakl ham qabul
    qilinishi kerak, aks holda chaqiruvchi har joyda `[0]` yozardi va
    o'sha indeks bir kuni unutilardi.
    """
    dets = np.array([[0.5, 0.5, 0.2, 0.4]])
    labels = np.array([[5.0, -1.0, 3.0, 0.5]])

    flat = raw_to_detections(dets, labels, frame_size=(1000, 500), confidence_threshold=0.0)
    batched = raw_to_detections(
        dets[np.newaxis, :, :],
        labels[np.newaxis, :, :],
        frame_size=(1000, 500),
        confidence_threshold=0.0,
    )

    assert batched.xyxy.tolist() == flat.xyxy.tolist()
    assert batched.class_id is not None
    assert flat.class_id is not None
    assert batched.class_id.tolist() == flat.class_id.tolist()


def test_real_batch_is_rejected_instead_of_being_truncated() -> None:
    """`(2, n, k)` — jimgina birinchi kadrga QISQARTIRILMAYDI.

    Qisqartirish ikkinchi kadrni butunlay yo'qotardi va natija «kamroq
    aniqlandi» bo'lib ko'rinardi — ya'ni nosozlik model sifatiga
    yozilardi.
    """
    dets = np.zeros((2, 1, 4))
    labels = np.zeros((2, 1, 3))

    with pytest.raises(ValueError, match="partiya"):
        raw_to_detections(dets, labels, frame_size=(100, 100), confidence_threshold=0.0)


def test_mismatched_query_counts_are_rejected() -> None:
    """`dets` va `labels` uzunliklari mos kelmasa — ISTISNO.

    `zip` ning jim qisqartirishi uch quti berib ikkitasini o'lchash
    yo'lini ochardi (`fixtures/detections.py` ning aynan o'sha qarori).
    """
    with pytest.raises(ValueError, match="mos emas"):
        raw_to_detections(
            np.zeros((3, 4)),
            np.zeros((2, 3)),
            frame_size=(100, 100),
            confidence_threshold=0.0,
        )


def test_label_tensor_without_a_real_class_column_is_rejected() -> None:
    """Faqat background ustuni bo'lgan tenzor — ochiq xabar bilan rad etiladi.

    Ustun olib tashlangandan keyin hech nima qolmasdi va `argmax` bo'sh
    o'q ustida yiqilardi — sabab chaqiruvchiga umuman tushunarsiz
    bo'lardi.
    """
    assert MIN_CLASS_COLUMNS == 2

    with pytest.raises(ValueError, match="kamida"):
        raw_to_detections(
            np.zeros((1, 4)),
            np.zeros((1, 1)),
            frame_size=(100, 100),
            confidence_threshold=0.0,
        )


def test_box_tensor_must_have_four_columns() -> None:
    """`cxcywh` — aynan to'rtta ustun; boshqasi jimgina qabul qilinmaydi."""
    with pytest.raises(ValueError, match="cxcywh"):
        raw_to_detections(
            np.zeros((1, 5)),
            np.zeros((1, 3)),
            frame_size=(100, 100),
            confidence_threshold=0.0,
        )


# --------------------------------------------------------------------------
# MODUL TOZALIGI — sof funksiya moduli chegarasi (§S-8)
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


@pytest.mark.parametrize("banned", ["torch", "rfdetr"])
def test_module_never_imports_the_training_stack(banned: str, module_source: str) -> None:
    """`torch`/`rfdetr` import qilinmaydi — D-04 ning kod darajasidagi yarmi.

    ⚠ Bu darvoza `test_license_fence.py` NING O'RNINI BOSMAYDI: u paket
      o'rnatilganini ushlaydi, bu esa import yozilganini. Ikkalasi ham
      kerak — paketsiz import `ImportError` beradi (shovqinli), lekin
      paket kimdir tomonidan qo'shilgan kuni import JIMGINA ishlab
      ketardi va ishlab chiqarish image'i ~800 MB o'sardi.
    """
    offenders = [
        line
        for line in module_source.splitlines()
        if line.startswith((f"import {banned}", f"from {banned}"))
    ]
    assert offenders == [], (
        f"`{MODULE_PATH.name}` `{banned}` ni import qilyapti: {offenders}. "
        "Ishlab chiqarish image'ida bu paket YO'Q (D-04) va u hech qachon "
        "qo'shilmaydi — post-processing SHU MODULDA qo'lda hisoblanadi."
    )


def test_module_does_not_read_settings(module_source: str) -> None:
    """Chegaralar ARGUMENT bo'lib kiradi, `import` emas (§S-8, D-11).

    `Settings` dan o'qilgan chegara «sozlash SQL bilan, migratsiyasiz»
    va'dasini buzardi: chegara `occupancy_events.thresholds_version` bilan
    QATORDA yashaydi va o'tmishdagi hukmlar o'z to'plamini eslab qoladi.
    """
    offenders = [
        line
        for line in module_source.splitlines()
        if line.startswith(("from app.settings", "import app.settings"))
    ]
    assert offenders == [], (
        f"`{MODULE_PATH.name}` `Settings` ni o'qiyapti: {offenders}. Sof "
        "funksiya moduli chegaralarni ARGUMENT sifatida oladi."
    )
