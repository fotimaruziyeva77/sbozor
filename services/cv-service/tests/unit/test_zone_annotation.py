"""`detector/annotate.py` darvozasi — DALIL ZANJIRINING BUTUNLIGI (T-05-32).

=============================================================================
BU FAYL REJANING FAYL RO'YXATIDA YO'Q EDI — VA U ONGLI QO'SHIMCHA.

Sabab tahdid reyestrida yozilgan: T-05-32 «annotator chiqishi ALOHIDA
prefiksga yoziladi; ASL KADR QAYTA YOZILMAYDI» dispozitsiyasi
`mitigate`. `mitigate` — bu o'lchanadigan da'vo, izoh emas.

O'lchov esa xavfni TASDIQLADI (2026-08-09): `supervision` 0.30.0 ning
`PolygonZoneAnnotator.annotate()` sahnani JOYIDA bo'yaydi va AYNAN
o'sha obyektni qaytaradi. Ya'ni himoyasiz kodda asl kadr massivi
o'rnida bo'yalardi va hech qanday xato chiqmasdi.

=============================================================================
⚠ BU YERDA HAQIQIY KADR KERAK EMAS.

«Kadr» — sintetik `np.zeros((h, w, 3), np.uint8)` massivi. Chizish
mexanikasi (nusxa olinganmi, kontur chizilganmi) piksellarning O'ZIDAN
o'lchanadi, ya'ni bu test D-02 ning chokidan PASTDA turadi va real
Karmana kadriga BOG'LIQ EMAS.

❌ ISBOTLAMAYDI: rasm nazoratchi uchun TUSHUNARLI ekanini. Bu inson
   o'lchovi va u `05-HUMAN-UAT` ning bandi.
=============================================================================
"""

from __future__ import annotations

from typing import Final

import numpy as np

from app.detector.annotate import (
    EVIDENCE_PREFIX,
    ZONE_OUTLINE_COLOR,
    annotate_zone,
)

FRAME_SHAPE: Final[tuple[int, int, int]] = (200, 300, 3)
"""`(balandlik, kenglik, kanal)` — kichik, lekin konturga joy beradigan kadr."""

POLYGON: Final = np.array([[50, 40], [250, 40], [250, 160], [50, 160]], dtype=np.int64)


def _blank_frame() -> np.ndarray:
    """Butunlay qora sintetik kadr — har qanday chizilgan piksel KO'RINADI."""
    return np.zeros(FRAME_SHAPE, dtype=np.uint8)


def test_the_original_frame_is_not_modified() -> None:
    """⚠⚠ ASL KADR O'ZGARMAYDI — T-05-32 ning butun ma'nosi.

    `annotate()` sahnani JOYIDA bo'yashi o'lchangan fakt. Nusxa
    olinmasa, chaqiruvchining massivi bo'yalardi va u massiv omborga
    qayta yozilsa (yoki nazoratchiga «asl kadr» deb ko'rsatilsa) ORIGINAL
    DALIL YO'QOLARDI — jimgina, hech qanday xatosiz.

    Ko'r auditning dalil zanjiri aynan shu farqqa tayanadi: nazoratchi
    bo'yalgan rasmni ko'radi, audit esa asl kadrga qayta murojaat qila
    olishi SHART.
    """
    frame = _blank_frame()
    untouched = frame.copy()

    annotate_zone(frame, POLYGON, label="R-12")

    assert np.array_equal(frame, untouched), (
        "asl kadr o'zgardi — `annotate()` sahnani joyida bo'yadi va nusxa "
        "olinmagan. Dalil zanjiri uzilardi (T-05-32)."
    )


def test_the_returned_image_is_a_different_object() -> None:
    """Qaytgan massiv — BOSHQA obyekt, kirishning o'zi emas."""
    frame = _blank_frame()

    result = annotate_zone(frame, POLYGON, label="R-12")

    assert result is not frame


def test_something_is_actually_drawn() -> None:
    """Kontur HAQIQATAN chiziladi — «nusxa qaytardim» yolg'on-yashilini yopadi.

    ⚠ Bu testsiz `annotate_zone` shunchaki `frame.copy()` qaytarsa ham
      yuqoridagi ikkala test YASHIL bo'lardi: nusxa asl kadrni
      o'zgartirmaydi va boshqa obyekt bo'ladi. Ya'ni bu uchlik BIRGA
      ma'noli.

    Kadr butunlay qora (`0`), shuning uchun nolga teng bo'lmagan har
    qanday piksel — chizilgan narsa.
    """
    frame = _blank_frame()

    result = annotate_zone(frame, POLYGON, label="R-12")

    assert result.shape == FRAME_SHAPE
    assert result.any(), "birorta piksel chizilmadi — kontur umuman qo'yilmagan"


def test_the_outline_uses_the_declared_colour() -> None:
    """Chizilgan piksellar orasida e'lon qilingan rang BOR.

    `cv2` BGR tartibida ishlaydi, `sv.Color` esa RGB da e'lon qilinadi —
    bu test ikkisining orasidagi moslikni ham qulflaydi.
    """
    frame = _blank_frame()

    result = annotate_zone(frame, POLYGON, label="R-12")

    expected_bgr = (ZONE_OUTLINE_COLOR.b, ZONE_OUTLINE_COLOR.g, ZONE_OUTLINE_COLOR.r)
    matches = np.all(result == np.array(expected_bgr, dtype=np.uint8), axis=-1)
    assert matches.any(), (
        f"kutilgan BGR rang {expected_bgr} rasmda topilmadi — kontur rangi "
        "e'lon qilinganidan boshqa"
    )


def test_evidence_prefix_is_separate_from_the_snapshot_path() -> None:
    """Dalil rasmi ALOHIDA prefiksda va u KOD konstantasi (T-05-32).

    Prefiks sozlamaga chiqarilsa, yozuvchi (05-08) bilan o'quvchi
    (`core-api` proxysi) jimgina boshqa yo'llarga qarab qolardi va dalil
    rasmi «yo'q» bo'lib ko'rinardi — `worker.CV_QUEUE` bilan aynan bir
    xil qaror va bir xil sabab.
    """
    assert EVIDENCE_PREFIX
    assert EVIDENCE_PREFIX.endswith("/"), (
        "prefiks `/` bilan tugashi kerak — aks holda u qo'shni kalitlarning "
        "boshiga yopishib ketardi"
    )
    assert "snapshot" not in EVIDENCE_PREFIX, (
        "dalil rasmi kadrlarning yo'liga yozilmaydi — asl kadr qayta yozilmasligi SHART (T-05-32)"
    )
