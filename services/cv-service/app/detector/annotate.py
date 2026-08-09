"""Dalil rasmi — nazoratchi KO'RADIGAN belgilangan kadr (§4.2, T-05-32).

⛔ CHIZISH QO'LDA YOZILMAYDI. `sv.PolygonZoneAnnotator` konturni ham,
yorliqni ham chizadi va u MIT (RESEARCH §B.4).

=============================================================================
⚠⚠ `annotate()` SAHNANI JOYIDA O'ZGARTIRADI — VA BU O'LCHANGAN (2026-08-09).

`supervision` 0.30.0 da:

    out = annotator.annotate(scene=frame, label="...")
    out is frame        ->  True
    frame o'zgardi      ->  True

Ya'ni chaqiruvchi ASL kadr massivini bersa, u O'RNIDA bo'yaladi. O'sha
massiv keyin omborga qayta yozilsa (yoki nazoratchiga «asl kadr» sifatida
ko'rsatilsa), ORIGINAL DALIL YO'QOLGAN bo'lardi — va hech qanday xato
chiqmasdi.

Shuning uchun bu modul HAR DOIM nusxa ustida ishlaydi va bu holat
`tests/unit/test_zone_annotation.py` da o'lchanadi, izohda ishonch bilan
aytilmaydi.

=============================================================================
CHIQISH ALOHIDA PREFIKSGA YOZILADI (T-05-32).

`EVIDENCE_PREFIX` — KOD konstantasi, sozlama EMAS (`worker.CV_QUEUE`
bilan aynan bir xil qaror va sabab): prefiks muhit o'zgaruvchisiga
chiqsa, yozuvchi bilan o'quvchi jimgina boshqa yo'llarga qarab qolardi va
dalil rasmi «yo'q» bo'lib ko'rinardi.

⚠ Yozishning O'ZI 05-08 da. Bu modul FAQAT baytlar hosil qiladi —
  tarmoqqa chiqmaydi, omborni bilmaydi.
=============================================================================
"""

from __future__ import annotations

from typing import Final

import numpy as np
import numpy.typing as npt
from supervision import Color, PolygonZone, PolygonZoneAnnotator, Position

__all__ = [
    "EVIDENCE_PREFIX",
    "ZONE_OUTLINE_COLOR",
    "ZONE_OUTLINE_THICKNESS",
    "annotate_zone",
]

EVIDENCE_PREFIX: Final = "evidence/"
"""Dalil rasmlarining ALOHIDA S3 prefiksi — asl kadr yo'liga TEGMAYDI (T-05-32).

Asl kadr `snapshots` ning o'z yo'lida qoladi va u HECH QACHON qayta
yozilmaydi: nazoratchi bo'yalgan rasmni ko'radi, audit esa asl kadrga
qaytadan murojaat qila oladi. Bitta yo'lda ikkalasini saqlash ko'r
auditning dalil zanjirini uzardi.
"""

ZONE_OUTLINE_COLOR: Final = Color(r=255, g=196, b=0)
"""Kontur rangi — sariq-amber.

Qora-oq va kulrang kadrlarda ham (IR rejim, 06:00 tong) ko'rinadi;
qizil esa go'sht rastalarida fonga singib ketardi.
"""

ZONE_OUTLINE_THICKNESS: Final = 3
"""1920x1080 kadrda ekranga sig'dirilganda ham ko'rinadigan qalinlik."""

_ANNOTATION_ANCHORS: Final[tuple[Position, ...]] = (Position.CENTER,)
"""⚠ CHIZISH uchun ankor — QAROR uchun EMAS.

`PolygonZoneAnnotator` `PolygonZone` obyektini talab qiladi, zona esa
ankorsiz qurilmaydi. Bu yerdagi tanlov faqat annotatorning ichki
hisoblagichiga ta'sir qiladi va u RASMDA ishlatilmaydi — bandlik qarori
`zones.zone_verdict()` da va FAQAT o'sha yerda qabul qilinadi. Ikkala
joyda ikki xil ankor turishi qarama-qarshilik EMAS, aynan shu sababdan.
"""


def annotate_zone(
    frame: npt.NDArray[np.uint8],
    polygon_px: npt.NDArray[np.int64],
    *,
    label: str,
) -> npt.NDArray[np.uint8]:
    """Kadr ustiga zona konturini va yorliqni chizadi.

    Args:
        frame: BGR kadr (`cv2.imdecode` chiqishi). ⚠ O'ZGARTIRILMAYDI —
            modul docstringidagi o'lchovga qarang.
        polygon_px: `zones.polygon_to_pixels()` chiqishi.
        label: konturga yoziladigan matn (rasta raqami, verdikt, ishonch —
            tarkibi 05-08 ning qarori).

    Returns:
        YANGI massiv — kirish kadri o'zgarmagan holda qoladi.
    """
    zone = PolygonZone(polygon=polygon_px, triggering_anchors=_ANNOTATION_ANCHORS)
    annotator = PolygonZoneAnnotator(
        zone=zone,
        color=ZONE_OUTLINE_COLOR,
        thickness=ZONE_OUTLINE_THICKNESS,
        # ⚠ Zona hisoblagichi CHIZILMAYDI: u `trigger()` chaqirilmaganda
        #   `0` bo'lib turadi va rasmda «0» yozuvi nazoratchini
        #   chalg'itardi — u bandlik qarori deb o'qilishi mumkin edi.
        display_in_zone_count=False,
    )

    # ⚠⚠ NUSXA MAJBURIY — `annotate()` sahnani JOYIDA bo'yaydi (o'lchangan).
    canvas: npt.NDArray[np.uint8] = frame.copy()
    annotated: npt.NDArray[np.uint8] = annotator.annotate(scene=canvas, label=label)
    return annotated
