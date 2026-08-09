"""Xom tenzor -> `sv.Detections` — ARIFMETIKA, MODEL EMAS (§4.3, RESEARCH §B.2).

Sof funksiyalar moduli (`core-api/app/services/quality.py` bilan bir xil
shakl): tarmoqqa chiqmaydi, bazaga tegmaydi, holat saqlamaydi va
`Settings` ni BILMAYDI — chegaralar unga argument sifatida kiradi.

=============================================================================
BU MODUL «MODEL TO'G'RIMI?» DEGAN SAVOLGA JAVOB BERMAYDI.

U «ARIFMETIKA TO'G'RIMI?» degan savolga javob beradi, va u savol real
kadrsiz TO'LIQ isbotlanadi: kirishi qo'lda yasalgan tenzor, kutilgan
chiqishi qo'lda hisoblangan quti (D-01/D-02).

=============================================================================
⚠⚠ ENG XAVFLI QADAM — BACKGROUND USTUNI, VA U ISTISNO TASHLAMAYDI.

Rasmiy hujjat (RESEARCH §B.2 dan sitata):

    «The model returns raw tensors: `dets` (normalized `cxcywh` boxes) and
     `labels` (unnormalized logits). You must apply sigmoid activation,
     remove the background class column, and convert box coordinates
     yourself.»

Ustunni NOTO'G'RI olib tashlash BARCHA klass ID'larini bittaga suradi va
JIMGINA noto'g'ri javob beradi: hech qanday istisno chiqmaydi, faqat
«odam» o'rniga «boshqa narsa» chiqadi. Nosozlikning bu sinfi faqat
qo'lda hisoblangan kutilgan qiymat bilan ushlanadi.

Shuning uchun ustun olib tashlangandan keyin `class_id` MODELNING ASL
YORLIQ FAZOSIDA qoladi — quyidagi `_foreground_scores()` ga qarang.

=============================================================================
KOORDINATA TIZIMLARI — IKKITA VA ULAR ARALASHTIRILMAYDI.

    kirish `dets`   NORMALANGAN `cxcywh`   (0..1, grafning kontrakti)
    chiqish `xyxy`  PIKSEL                 (`sv.Detections` ning kontrakti)

Konversiya AYNAN shu modulda va YAGONA joyda turadi.
=============================================================================
"""

from __future__ import annotations

from typing import Final

import numpy as np
import numpy.typing as npt
from supervision import Detections

__all__ = [
    "BACKGROUND_CLASS_INDEX",
    "MIN_CLASS_COLUMNS",
    "raw_to_detections",
    "sigmoid",
]

BACKGROUND_CLASS_INDEX: Final = 0
"""Yorliq tenzoridagi background ustunining indeksi.

⚠⚠ BU QIYMAT TAXMIN VA U SHUNDAY DEB O'QILISHI KERAK — `[LOW confidence]`.

RESEARCH §B.2 dagi rasmiy sitata «remove the background class column»
deydi, LEKIN INDEKSNI AYTMAYDI. Ya'ni `0` bu yerda o'lchangan fakt emas,
konvensiyaga (DETR oilasida background odatda birinchi ustun) asoslangan
tanlov.

QANDAY TEKSHIRILADI: haqiqiy artefakt bilan, `model` markerli test orqali
(`tests/integration/test_onnx_session.py`) — chiqish ustunlari soni va
ma'lum bir kadrdagi yorliqlar taqsimoti bo'yicha. Bu tekshiruv real
`.onnx` fayl talab qiladi, ya'ni u CI zanjirida YURMAYDI va bu holat
`05-HUMAN-UAT` bandi sifatida ochiq qayd etiladi.

⚠ Quyidagi arifmetika bu qiymatdan MUSTAQIL to'g'ri: ustun qaysi bo'lsa
  ham, u olib tashlangandan keyin qolgan ustunlar O'Z ASL INDEKSLARINI
  saqlaydi. Birlik testi aynan SHU kafolatni o'lchaydi, `0` ning
  to'g'riligini emas.
"""

MIN_CLASS_COLUMNS: Final = 2
"""Yorliq tenzorida kamida shuncha ustun bo'lishi SHART.

Background + kamida bitta haqiqiy klass. Bittalik tenzorda background
olib tashlangandan keyin HECH NIMA qolmasdi va `argmax` bo'sh o'q ustida
`ValueError` bilan yiqilardi — sabab esa chaqiruvchiga umuman
tushunarsiz bo'lardi. Shuning uchun shart SHU YERDA, ochiq xabar bilan
tekshiriladi.
"""

_BOX_COLUMNS: Final = 4
"""`cxcywh` — aynan to'rtta ustun."""


def sigmoid(values: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:
    """Logitlarni 0..1 ehtimolliklariga o'giradi.

    ⚠ SONLI BARQAROR SHAKL, sodda `1 / (1 + exp(-x))` EMAS: manfiy katta
      logitda `exp(-x)` toshib ketadi (`RuntimeWarning: overflow`) va
      natija `nan` bo'lardi. `nan` esa chegara solishtirishida JIMGINA
      `False` beradi — ya'ni quti sababsiz tushib qolardi va hech qayerda
      xato ko'rinmasdi.

    Kafolat: `sigmoid(0) == 0.5` AYNIQ (ikkala shoxda ham `1/(1+1)`).
    """
    positive = values >= 0
    result = np.empty_like(values, dtype=np.float64)
    # x >= 0 shoxi: exp(-x) <= 1, toshish yo'q.
    result[positive] = 1.0 / (1.0 + np.exp(-values[positive]))
    # x < 0 shoxi: exp(x) < 1, toshish yo'q.
    exponent = np.exp(values[~positive])
    result[~positive] = exponent / (1.0 + exponent)
    return result


def _drop_batch_axis(tensor: npt.NDArray[np.float64], name: str) -> npt.NDArray[np.float64]:
    """`(1, n, k)` -> `(n, k)`; `(n, k)` o'zgarmaydi.

    Eksport `batch_size=1` bilan qilinadi (RESEARCH §B.2), ya'ni graf
    ODATDA yetakchi partiya o'qi bilan qaytaradi. Ikkala shakl ham qabul
    qilinadi, lekin `(2, n, k)` — ya'ni haqiqiy partiya — ATAYIN rad
    etiladi: uni jimgina birinchi elementga qisqartirish qolgan
    kadrlarni yo'qotardi va natija «kamroq aniqlandi» bo'lib ko'rinardi.
    """
    if tensor.ndim == 3:
        if tensor.shape[0] != 1:
            raise ValueError(
                f"{name}: partiya o'lchami {tensor.shape[0]}, kutilgani 1. "
                "Eksport `batch_size=1` bilan qilinadi (`ops/models/README.md`); "
                "haqiqiy partiyani jimgina qisqartirish kadrlarni yo'qotardi."
            )
        single: npt.NDArray[np.float64] = tensor[0]
        return single
    if tensor.ndim != 2:
        raise ValueError(
            f"{name}: kutilgan shakl `(n, k)` yoki `(1, n, k)`, olingani {tensor.shape}"
        )
    return tensor


def _foreground_scores(
    probabilities: npt.NDArray[np.float64],
) -> tuple[npt.NDArray[np.float64], npt.NDArray[np.int64]]:
    """Background ustunini olib tashlaydi va ASL yorliq indeksini QAYTARADI.

    ⚠⚠ MODULNING BUTUN MA'NOSI SHU FUNKSIYADA.

    `np.delete(probabilities, BG, axis=1)` dan keyin ustunlar QAYTA
    RAQAMLANADI: kesilgan massivdagi `argmax` `j` ni bersa, u ASL
    fazodagi `j` EMAS. O'sha `j` ni to'g'ridan-to'g'ri `class_id` qilib
    yozish — bu aynan RESEARCH §B.2 ogohlantirgan JIMGINA SURILISH.

    Shuning uchun ustun indekslari massivi (`class_axis`) AYNAN o'sha
    `np.delete` bilan kesiladi va u kesilgan pozitsiyani asl indeksga
    QAYTA o'giradi. Kafolat `BACKGROUND_CLASS_INDEX` ning qiymatidan
    mustaqil: konstanta o'zgarsa, ikkala kesish ham BIRGA o'zgaradi.

    Returns:
        `(confidence, class_id)` — eng yuqori ballli NOBACKGROUND klass
        va uning ASL yorliq fazosidagi indeksi.
    """
    original_indices = np.arange(probabilities.shape[1], dtype=np.int64)
    class_axis = np.delete(original_indices, BACKGROUND_CLASS_INDEX)
    foreground = np.delete(probabilities, BACKGROUND_CLASS_INDEX, axis=1)

    best_position = np.argmax(foreground, axis=1)
    rows = np.arange(foreground.shape[0])

    confidence: npt.NDArray[np.float64] = foreground[rows, best_position]
    class_id: npt.NDArray[np.int64] = class_axis[best_position]
    return confidence, class_id


def _cxcywh_to_xyxy_pixels(
    boxes: npt.NDArray[np.float64], width: int, height: int
) -> npt.NDArray[np.float64]:
    """Normalangan `cxcywh` -> piksel `xyxy`.

    Qo'lda hisoblanadigan misol (birlik testida AYNAN shu literal):
        `cx=0.5, cy=0.5, w=0.2, h=0.4`, kadr `1000x500`
        x1 = (0.5 - 0.1) * 1000 = 400      y1 = (0.5 - 0.2) * 500 = 150
        x2 = (0.5 + 0.1) * 1000 = 600      y2 = (0.5 + 0.2) * 500 = 350

    ⚠ QIRQISH (`clip`) QILINMAYDI. Kadr chetidan chiqib ketgan quti —
      detektorning qonuniy chiqishi (obyektning bir qismi kadrdan
      tashqarida) va uni chegaraga yopishtirish markazni SILJITARDI, ya'ni
      zona qarorini o'zgartirardi. `PolygonZone` kadrdan tashqaridagi
      ankorni baribir «ichkarida emas» deb hisoblaydi.
    """
    centre_x = boxes[:, 0]
    centre_y = boxes[:, 1]
    half_width = boxes[:, 2] / 2.0
    half_height = boxes[:, 3] / 2.0

    return np.stack(
        [
            (centre_x - half_width) * width,
            (centre_y - half_height) * height,
            (centre_x + half_width) * width,
            (centre_y + half_height) * height,
        ],
        axis=1,
    )


def raw_to_detections(
    dets: npt.NDArray[np.float64],
    labels: npt.NDArray[np.float64],
    *,
    frame_size: tuple[int, int],
    confidence_threshold: float,
) -> Detections:
    """Eksport qilingan grafning xom chiqishidan `sv.Detections` quradi.

    Args:
        dets: normalangan `cxcywh` qutilar — `(n, 4)` yoki `(1, n, 4)`.
        labels: NORMALLANMAGAN logitlar — `(n, c)` yoki `(1, n, c)`.
            `c` background ustunini HAM o'z ichiga oladi.
        frame_size: `(kenglik, balandlik)` piksellarda — chiqish shu
            shkalada bo'ladi.
        confidence_threshold: undan PAST qutilar tushib qoladi.
            ⚠ CHEGARA INKLYUZIV: `confidence == threshold` bo'lgan quti
            QOLADI. Sabab `snapshots` sifat filtri bilan bir xil
            (`quality.py`): «chegarada» holati ikki xil o'qilsa,
            chegarani sozlash natijani oldindan aytib bo'lmaydigan
            qilardi.

    Returns:
        `sv.Detections` — `xyxy` PIKSELDA, `confidence` 0..1,
        `class_id` MODELNING ASL yorliq fazosida.

    Raises:
        ValueError: shakllar mos kelmasa. ⚠ Jimgina qisqartirish
            (`zip` ning standart xulqi) ATAYIN qilinmaydi: u yuz quti
            berib o'ntasini o'lchash yo'lini ochardi va test o'zi
            so'ragandan kamrog'ini tekshirardi
            (`fixtures/detections.py` ning aynan o'sha qarori).
    """
    boxes = _drop_batch_axis(np.asarray(dets, dtype=np.float64), "dets")
    logits = _drop_batch_axis(np.asarray(labels, dtype=np.float64), "labels")

    if boxes.shape[1] != _BOX_COLUMNS:
        raise ValueError(f"dets: kutilgan {_BOX_COLUMNS} ustun (cxcywh), olingani {boxes.shape[1]}")
    if logits.shape[1] < MIN_CLASS_COLUMNS:
        raise ValueError(
            f"labels: kamida {MIN_CLASS_COLUMNS} ustun kutilgan (background + "
            f"kamida bitta klass), olingani {logits.shape[1]}"
        )
    if boxes.shape[0] != logits.shape[0]:
        raise ValueError(
            f"dets={boxes.shape[0]} va labels={logits.shape[0]} so'rovlar soni "
            "mos emas — jimgina qisqartirish qutilarni yo'qotardi"
        )

    width, height = frame_size

    # 1. Logitlar -> ehtimolliklar.
    probabilities = sigmoid(logits)
    # 2. Background ustuni — VA ASL INDEKSNING SAQLANISHI.
    confidence, class_id = _foreground_scores(probabilities)
    # 3. Normalangan `cxcywh` -> piksel `xyxy`.
    xyxy = _cxcywh_to_xyxy_pixels(boxes, width, height)
    # 4. Chegara — INKLYUZIV (docstringdagi sabab).
    keep = confidence >= confidence_threshold

    return Detections(
        xyxy=xyxy[keep].astype(np.float32).reshape(-1, _BOX_COLUMNS),
        confidence=confidence[keep].astype(np.float32),
        class_id=class_id[keep].astype(int),
    )
