"""Sintetik `Detections` konstruktori — kirish GEOMETRIK FAKT bo'yicha yasaladi (W0-7).

=============================================================================
MAJBURIYAT 1 — NOMLASH: GEOMETRIK FAKT, MODEL NATIJASI EMAS.

Bu modulning funksiyalari FAQAT o'lchanadigan geometrik fakt bilan
ataladi: `box_center_in_polygon(polygon)` — «qutining markazi poligon
ichida». Nom fakt aytadi va u chaqiruvchining KUTGAN NATIJASINI aytmaydi.

Qoidaning to'liq bayoni, taqiqlangan nomlar ro'yxati va ularning sababi
`tests/unit/test_detection_fixtures.py` ning MODUL DOCSTRINGIDA yashaydi —
bu faylda EMAS, va bu ataylab. Sabab 3-fazada o'lchangan: skanerlanadigan
faylning izohida taqiqlangan token yozilsa, sodda darvoza o'zini o'zi
qizartiradi va yagona «tuzatish» yo'li darvozani bo'shatish bo'ladi.

=============================================================================
MAJBURIYAT 2 — DETERMINIZM: BIR XIL ARGUMENT -> BIR XIL BAYTLAR.

Ishonch qiymatlari `random` GLOBAL modulidan OLINMAYDI. Qadalgan urug'li
mustaqil generator (`random.Random(_SEED)`) ishlatiladi va u HAR
CHAQIRUVDA YANGIDAN quriladi — modul darajasida umumiy holat yo'q
(`tests/fixtures/frames.py` va `karmana_seed.py` bilan aynan bir xil
qaror).

⚠ Usiz keyingi rejalarning chegara testlari «gohida yiqiladigan» turdagi
  bo'lardi: ishonch qiymati har chaqiruvda o'zgarib, chegara atrofida
  sakrab turardi va sabab test mantig'ida emas, generatorda bo'lardi.

=============================================================================
MAJBURIYAT 3 — MODUL `supervision` NING ZONA MANTIG'INI IMPORT QILMAYDI.

Bu yerdan faqat `Detections` konteyneri va `numpy` olinadi. Zona hisobi
tekshirilayotgan NARSA, ya'ni uni fixture ichiga olib kirish testni o'z
farazining aks-sadosiga aylantirardi. Chegara `test_detection_fixtures.py`
da matn skani bilan tasdiqlanadi.

=============================================================================
KOORDINATA TIZIMI — IKKITA VA ULAR ARALASHTIRILMAYDI.

    poligonlar   0..1        (bazada AYNAN shunday saqlanadi — D-07)
    `xyxy`       PIKSEL      (`Detections` ning kontrakti)

`detections_at()` — aynan shu ikkisi orasidagi ko'prik va u YAGONA joyda
turadi: konversiya har testda takrorlansa, ular sekin-asta ajralib
ketardi.
=============================================================================
"""

from __future__ import annotations

import random
from typing import Final

import numpy as np
from supervision import Detections

__all__ = [
    "DEFAULT_BOX_SIZE",
    "FRAME_SIZE",
    "box_center_in_polygon",
    "box_center_outside_polygon",
    "detections_at",
    "polygon_l_shape",
    "polygon_self_intersecting",
    "polygon_unit_square",
]

type Box = tuple[float, float, float, float]
"""Normalangan `(x1, y1, x2, y2)` — 0..1 oralig'ida."""

type Point = tuple[float, float]

_SEED: Final = 20260808
"""Qadalgan urug'. Qiymatning O'ZI ahamiyatsiz — QADALGANLIGI ahamiyatli."""

FRAME_SIZE: Final[tuple[int, int]] = (1920, 1080)
"""Standart kadr o'lchami (kenglik, balandlik) — piksel konversiyasi uchun.

⚠ SON ERKIN TANLANMAGAN, LEKIN U TALAB HAM EMAS: 1920x1080 — Hikvision
  asosiy oqimining eng keng tarqalgan ruxsati (03-faza kashfiyoti). Har
  qanday boshqa o'lcham `frame_size=` bilan beriladi va konversiya
  arifmetikasi o'zgarmaydi.
"""

DEFAULT_BOX_SIZE: Final = 0.04
"""Yordamchilar quradigan kvadratning normalangan tomoni.

Kichik, lekin nolga teng emas: nol o'lchamli quti `Detections` uchun
qonuniy bo'lsa ham, markaz hisobini degeneratsiyaga olib borardi.
"""

_MIN_CONFIDENCE: Final = 0.30
_MAX_CONFIDENCE: Final = 0.95
"""Standart ishonch oralig'i.

⚠ BU ORALIQ HECH QANDAY CHEGARANI IFODALAMAYDI va uni chegara sifatida
  o'qish XATO. Aniq qiymat kerak bo'lgan test uni `confidences=` bilan
  O'ZI beradi; bu yerdagi qiymat faqat «maydon to'ldirilgan» degani.
"""


def detections_at(
    boxes: list[Box],
    *,
    confidences: list[float] | None = None,
    class_ids: list[int] | None = None,
    frame_size: tuple[int, int] = FRAME_SIZE,
) -> Detections:
    """Normalangan qutilardan `Detections` quradi (pikselga o'girib).

    Args:
        boxes: normalangan `(x1, y1, x2, y2)` kortejlari, 0..1.
        confidences: berilmasa — QADALGAN urug'li generator (MAJBURIYAT 2).
        class_ids: berilmasa — hammasi `0`.
        frame_size: `(kenglik, balandlik)` piksellarda.

    Raises:
        ValueError: uzunliklar mos kelmasa. Jimgina qisqartirish
            (`zip` ning standart xulqi) testni JIMGINA kuchsizlantirardi:
            uch quti berib ikkitasini o'lchash mumkin bo'lardi.
    """
    width, height = frame_size
    if confidences is not None and len(confidences) != len(boxes):
        raise ValueError(f"confidences={len(confidences)} != boxes={len(boxes)}")
    if class_ids is not None and len(class_ids) != len(boxes):
        raise ValueError(f"class_ids={len(class_ids)} != boxes={len(boxes)}")

    # ⚠ `np.zeros(...)` — `np.array(...)` bilan birga YAGONA ruxsat etilgan
    #   qurish yo'llari. Sabab `test_detection_fixtures.py` da yozilgan va
    #   u geometriyaga umuman aloqador emas.
    xyxy = np.zeros((len(boxes), 4), dtype=np.float32)
    for index, (x1, y1, x2, y2) in enumerate(boxes):
        xyxy[index] = (x1 * width, y1 * height, x2 * width, y2 * height)

    if confidences is None:
        generator = random.Random(_SEED)  # noqa: S311 - fixture, kriptografiya emas
        confidences = [
            generator.uniform(_MIN_CONFIDENCE, _MAX_CONFIDENCE) for _ in range(len(boxes))
        ]

    return Detections(
        xyxy=xyxy,
        confidence=np.array(confidences, dtype=np.float32),
        class_id=np.array(class_ids if class_ids is not None else [0] * len(boxes), dtype=int),
    )


def polygon_unit_square(scale: float = 1.0, offset: Point = (0.0, 0.0)) -> np.ndarray:
    """0..1 dagi to'rtburchak: `(0,0)`-`(scale,scale)`, `offset` ga siljitilgan."""
    dx, dy = offset
    return np.array(
        [
            [0.0 + dx, 0.0 + dy],
            [scale + dx, 0.0 + dy],
            [scale + dx, scale + dy],
            [0.0 + dx, scale + dy],
        ],
        dtype=np.float64,
    )


def polygon_l_shape() -> np.ndarray:
    """L harfi shaklidagi olti tepalik — SODDA, lekin QAVARIQ EMAS.

    Real rasta qatorlari to'g'ri to'rtburchak bo'lmaydi; bu shakl
    «qavariq emas» holatini eng arzon ko'rinishda beradi.
    """
    return np.array(
        [
            [0.10, 0.10],
            [0.60, 0.10],
            [0.60, 0.40],
            [0.30, 0.40],
            [0.30, 0.80],
            [0.10, 0.80],
        ],
        dtype=np.float64,
    )


def polygon_self_intersecting() -> np.ndarray:
    """O'zi bilan KESISHGAN to'rt tepalik («kapalak»).

    Tepalar tartibi 1-2-4-3: `(0.2,0.2) -> (0.8,0.2)` va
    `(0.2,0.8) -> (0.8,0.8)` tomonlari emas, ULARNI BOG'LAYDIGAN ikki
    tomon kesishadi. Bunday shakl uchun «ichkarida» tushunchasi
    ANIQLANMAGAN, ya'ni uni SAQLASH PAYTIDA rad etish kerak (05-06).
    """
    return np.array(
        [
            [0.20, 0.20],
            [0.80, 0.20],
            [0.20, 0.80],
            [0.80, 0.80],
        ],
        dtype=np.float64,
    )


def _is_convex(polygon: np.ndarray) -> bool:
    """Ketma-ket tomonlarning ko'paytmasi BIR XIL ishorada-mi.

    ⚠ BU NUQTA-POLIGON TESTI EMAS va u shunday bo'lib ko'rinmasligi kerak:
      quyidagi ikki yordamchining KAFOLATI shu tekshiruvga tayanadi,
      chunki qavariq shaklda tepaliklarning o'rtachasi HAR DOIM ichkarida
      (u tepaliklarning qavariq kombinatsiyasi).
    """
    signs: set[bool] = set()
    count = len(polygon)
    for index in range(count):
        a = polygon[index]
        b = polygon[(index + 1) % count]
        c = polygon[(index + 2) % count]
        cross = (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])
        if cross != 0:
            signs.add(cross > 0)
    return len(signs) <= 1


def box_center_in_polygon(polygon: np.ndarray, *, size: float = DEFAULT_BOX_SIZE) -> Box:
    """Markazi poligon ICHIDA bo'lgan normalangan quti.

    Markaz — tepaliklarning O'RTACHASI. Qavariq shaklda bu nuqta har doim
    ichkarida (tepaliklarning qavariq kombinatsiyasi), ya'ni funksiya
    nomidagi FAKT arifmetik natija — taxmin emas.

    Raises:
        ValueError: poligon qavariq bo'lmasa. ⚠ BU KAFOLATNING O'ZI:
            qavariq bo'lmagan shaklda o'rtacha nuqta tashqarida qolishi
            mumkin va o'shanda funksiya nomi YOLG'ON bo'lardi. Yolg'on
            nomli fixture esa testni jimgina bo'shatadi.
    """
    if not _is_convex(polygon):
        raise ValueError(
            "box_center_in_polygon faqat qavariq poligon uchun kafolat bera "
            "oladi; boshqa shakl uchun qutini `detections_at()` ga LITERAL "
            "koordinata bilan bering."
        )
    center_x = float(np.mean(polygon[:, 0]))
    center_y = float(np.mean(polygon[:, 1]))
    half = size / 2
    return (center_x - half, center_y - half, center_x + half, center_y + half)


def box_center_outside_polygon(polygon: np.ndarray, *, size: float = DEFAULT_BOX_SIZE) -> Box:
    """Markazi poligonning QAMROVCHI TO'RTBURCHAGIDAN tashqarida bo'lgan quti.

    Poligon o'z qamrovchi to'rtburchagining ichida yotadi, ya'ni undan
    tashqaridagi nuqta poligondan ham tashqarida — shakl qavariqmi yoki
    yo'qmi, ahamiyatsiz. Kafolat yana arifmetik.

    Markaz o'ngdan qo'yiladi; 0..1 ga sig'masa — chapdan.

    Raises:
        ValueError: ikkala tomonda ham joy qolmasa (poligon deyarli butun
            kadrni egallagan). Jimgina 0..1 dan chiqib ketish esa keyingi
            piksel konversiyasida kadrdan tashqaridagi quti berardi.
    """
    half = size / 2
    gap = size
    right = float(np.max(polygon[:, 0])) + gap + half
    left = float(np.min(polygon[:, 0])) - gap - half
    center_y = float(np.mean(polygon[:, 1]))

    if right + half <= 1.0:
        center_x = right
    elif left - half >= 0.0:
        center_x = left
    else:
        raise ValueError(
            "poligon kadrning deyarli butun kengligini egallagan — undan "
            "tashqarida 0..1 ichida joy qolmadi"
        )
    return (center_x - half, center_y - half, center_x + half, center_y + half)
