"""Zona bandligi — 0..1 <-> piksel va `PolygonZone` verdicti (§4.2, D-09/D-11).

Sof funksiyalar moduli (`core-api/app/services/quality.py` bilan bir xil
shakl): tarmoqqa chiqmaydi, bazaga tegmaydi, holat saqlamaydi va
`Settings` ni BILMAYDI — chegaralar unga ARGUMENT sifatida kiradi (D-11).

=============================================================================
⛔ NUQTA-POLIGON ICHIDA TESTI QO'LDA YOZILMAYDI.

Zona hisoblagichi ham, annotator ham `supervision` da bor va u MIT
(RESEARCH §B.4). Qo'lda yozilgan `point_in_polygon` ikki narsani birdan
buzardi: (1) kutubxonaning sinovdan o'tgan qirra holatlarini qaytadan
ixtiro qilardi, (2) test o'sha qo'lda yozilgan mantiqni O'ZI bilan
solishtirardi.

⛔ RASMIY MISOL `ultralytics` ISHLATADI — u AGPL va bu loyihada TAQIQ.
`sv.Detections` xom ONNX chiqishidan `postprocess.py` da QO'LDA quriladi.

=============================================================================
TUZOQ 1 — `PolygonZone` PIKSEL KUTADI, BIZ 0..1 SAQLAYMIZ.

`PolygonZone(polygon: npt.NDArray[np.int64], ...)`, AI-01/D-07 esa
normalangan 0..1 saqlashni talab qiladi. Bu qarama-qarshilik emas,
CHEGARA — va `polygon_to_pixels()` aynan o'sha chegaraning mexanizmi:
u §A.2 dagi «kamera rezolyutsiyasi o'zgarsa zona OMON QOLADI»
kafolatining o'zi.

=============================================================================
⚠⚠ TUZOQ 4 — RESEARCH DA YO'Q VA U O'LCHOV BILAN TOPILDI (2026-08-09).

`supervision` 0.30.0 ning haqiqiy imzosida UCHINCHI parametr bor va
RESEARCH §B.4 dagi sitata uni KO'RSATMAGAN:

    PolygonZone(polygon, triggering_anchors=(BOTTOM_CENTER,),
                require_all_anchors: bool = True)

`require_all_anchors=True` — ya'ni KUTUBXONA STANDARTI — bir nechta
ankor berilganda ularni **VA** (AND) bilan birlashtiradi. Markazi
ichkarida, pastki markazi tashqarida bo'lgan quti ustida o'lchandi:

    (CENTER,)                    -> True
    (BOTTOM_CENTER,)             -> False
    (CENTER, BOTTOM_CENTER) AND  -> False      <- standart
    (CENTER, BOTTOM_CENTER) OR   -> True

⚠ BU D-09 NING SABABINI TESKARISIGA O'GIRADI. RESEARCH §B.4 juftlikni
  aynan «`BOTTOM_CENTER` qo'shni zonaga tushib qolishi mumkin» degan
  xavfni YUMSHATISH uchun tavsiya qilgan. AND ostida juftlik bu xavfni
  yumshatmaydi — aksincha, u HAR IKKALA ankorni talab qilib, yagona
  ankordan QAT'IYROQ bo'lib qoladi va aynan o'sha savat-qo'shni-zona
  holatida detektsiyani YO'QOTADI.

Shuning uchun bu modul `require_all_anchors` ni YASHIRMAYDI: u ochiq
argument va uning standarti `DEFAULT_REQUIRE_ALL_ANCHORS` da. To'g'ri
qiymatni faqat REAL KADR aytadi — mexanizm quriladi va o'lchanadi,
QIYMAT keyin sozlanadi (4-fazadagi `light_mode` naqshi).

=============================================================================
⛔ TILING / SAHI YOZILMAYDI (D-10).

Byudjet bor (175 kadr/kun/bozor, eng og'ir ssenariy ~47 daqiqa CPU/kun),
lekin murakkablik ANIQLIK DALILISIZ qo'shilmaydi. Qayta ko'rish sharti
ochiq va o'lchanadigan: rasta kadrda <32 px bo'lsa.
=============================================================================
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

import numpy as np
import numpy.typing as npt
from sbozor_core.enums import OccupancyVerdict
from supervision import Detections, PolygonZone, Position

__all__ = [
    "DEFAULT_REQUIRE_ALL_ANCHORS",
    "DEFAULT_TRIGGERING_ANCHORS",
    "MIN_POLYGON_POINTS",
    "UncertaintyThresholds",
    "polygon_to_pixels",
    "zone_verdict",
]

DEFAULT_TRIGGERING_ANCHORS: Final[tuple[Position, ...]] = (
    Position.CENTER,
    Position.BOTTOM_CENTER,
)
"""D-09 ning standarti — LEKIN U SOZLAMA, QAT'IY QIYMAT EMAS.

`BOTTOM_CENTER` odam uchun mantiqiy (oyoq yerda turadi). «Rastada mol
bormi?» savolida esa aniqlangan obyekt stol ustidagi savat bo'lishi
mumkin va uning bottom-center'i QO'SHNI zonaga tushishi mumkin — o'shanda
rasta band bo'la turib «bo'sh» deb yozilardi.

⚠ Standart FUNKSIYADA emas, CHAQIRUVCHIDA: `zone_verdict()` ankorlarni
  ARGUMENT sifatida oladi. Aks holda «sozlama» so'zi yolg'on bo'lardi.

⚠ Yuqoridagi TUZOQ 4 ni O'QING: bu juftlikning ma'nosi
  `require_all_anchors` ga BOG'LIQ va standart kutubxona qiymati (AND)
  D-09 ning niyatiga ZID.
"""

DEFAULT_REQUIRE_ALL_ANCHORS: Final = False
"""Ankorlar **YOKI** (OR) bilan birlashtiriladi — kutubxona standarti EMAS.

⚠⚠ BU KUTUBXONA STANDARTIDAN ONGLI CHEKINISH VA SABAB MODUL
   DOCSTRINGIDAGI «TUZOQ 4» DA O'LCHANGAN.

`supervision` ning o'z standarti `True` (AND). D-09 esa juftlikni
`BOTTOM_CENTER` ning qo'shni zonaga tushish xavfini YUMSHATISH uchun
tanlagan, va AND ostida juftlik o'sha xavfni yumshatmaydi — kuchaytiradi.
Ya'ni kutubxona standartini jimgina qabul qilish D-09 ni bajarilgan
ko'rsatib, uning MAQSADINI buzardi.

⚠ QIYMATNING O'ZI HAM `[LOW confidence]`: OR ostida yolg'on-musbat
  (qo'shni zonaning savati) ko'payishi mumkin. To'g'ri javobni faqat real
  Karmana kadri aytadi — bu `05-HUMAN-UAT` bandi. Bu yerda qulflangan
  narsa QIYMAT emas, MEXANIZM: ikkala rejim ham argument bilan
  tanlanadi va ikkalasi ham test bilan o'lchangan.
"""

MIN_POLYGON_POINTS: Final = 3
"""Poligonda kamida uchta tepalik.

Ikki nuqtali «poligon» — kesma; uning ichkarisi YO'Q, ya'ni `trigger()`
har doim `False` qaytarardi va zona JIMGINA abadiy bo'sh bo'lib qolardi.
Nosozlik hisobotda «bu rasta hech qachon band bo'lmadi» bo'lib
ko'rinardi — ya'ni ma'lumot yo'qligi yaxshi natijaga o'xshab qolardi.
"""

_POINT_COLUMNS: Final = 2
"""`(x, y)` — aynan ikkita ustun."""


@dataclass(frozen=True, slots=True)
class UncertaintyThresholds:
    """`uncertain` oynasining ikki cheti — QATORDAN keladi, `import` dan EMAS (D-11).

    Bu qiymatlar `occupancy_events.thresholds_version` bilan BIR QATORDA
    yashaydi: ularni sozlash `UPDATE`, migratsiya EMAS, va o'tmishdagi
    hukmlar o'z chegara to'plamini eslab qoladi. Shu sababdan bu klass
    modul konstantasi sifatida standart qiymat TAKLIF QILMAYDI —
    chaqiruvchi ularni qatordan o'qib beradi (05-08).

    Attributes:
        uncertain_low: undan PAST ishonch — `empty`.
        uncertain_high: undan yuqori yoki TENG ishonch — `occupied`.
            Ikkisining orasi — `uncertain`, ya'ni «model bilmaydi» va
            zona nazoratchi navbatiga tushadi.

    Raises:
        ValueError: oraliq 0..1 dan tashqarida yoki `low > high` bo'lsa.
            ⚠ Teskari oyna (`low > high`) ISTISNO TASHLAMASDAN «ishlardi»:
            har bir ishonch yo `empty` yo `occupied` bo'lib, `uncertain`
            navbati BUTUNLAY bo'sh qolardi — ya'ni nazoratchi hech qachon
            hech nima ko'rmasdi va bu holat hisobotda «hammasi aniq»
            bo'lib ko'rinardi.
    """

    uncertain_low: float
    uncertain_high: float

    def __post_init__(self) -> None:
        for name, value in (
            ("uncertain_low", self.uncertain_low),
            ("uncertain_high", self.uncertain_high),
        ):
            if not 0.0 <= value <= 1.0:
                raise ValueError(
                    f"{name}={value} 0..1 oralig'idan tashqarida. Ishonch shu "
                    "shkalada o'lchanadi (`occupancy_events.confidence` "
                    "`CHECK confidence >= 0 AND confidence <= 1`)."
                )
        if self.uncertain_low > self.uncertain_high:
            raise ValueError(
                f"uncertain_low={self.uncertain_low} > "
                f"uncertain_high={self.uncertain_high}: `uncertain` oynasi "
                "TESKARI. Bunday to'plam istisnosiz ishlab, noaniq navbatni "
                "butunlay bo'sh qoldirardi — nazoratchi hech nima ko'rmasdi."
            )


def polygon_to_pixels(
    polygon: npt.NDArray[np.float64], width: int, height: int
) -> npt.NDArray[np.int64]:
    """Normalangan 0..1 poligonni piksel koordinatalariga o'giradi.

    Qo'lda hisoblanadigan misol (birlik testida AYNAN shu literal):
        `[(0,0), (1,0), (1,1)]`, kadr `1000x500`
        -> `[[0, 0], [1000, 0], [1000, 500]]`

    ⚠⚠ YAXLITLASH QOIDASI — `round`, `floor` EMAS, VA SABAB SISTEMATIK.

    `floor` HAR koordinatani pastga suradi (0..1 px), ya'ni har poligon
    o'zining o'ng va pastki chetidan QISQARADI. Xato tasodifiy emas,
    BIR TOMONLAMA: kamera ruxsati o'zgarib zona qayta hisoblanganda
    chegara har safar bir xil yo'nalishda siljiydi va rasta chetidagi
    savdo sekin-asta zonadan chiqib ketardi. `round` esa nosimmetrik
    emas — o'rtacha siljish nol.

    ⚠ ARIFMETIK YAXLITLASH (`np.rint`) — YARMI JUFTGA. `1.5 -> 2`,
      `2.5 -> 2`. Bu `numpy` ning standarti va u SHU YERDA qulflangan
      (literal test bilan): keyingi o'quvchi «yarmi yuqoriga» deb
      o'ylab, sabab bilan tanlangan xulqni jimgina o'zgartirmasligi
      uchun. Yarim piksel farqi zona qarori uchun ahamiyatsiz —
      ahamiyatli bo'lgani BIR TOMONLAMA siljishning YO'QLIGI.

    Args:
        polygon: `(n, 2)` shaklidagi normalangan tepaliklar, 0..1.
        width: kadr kengligi piksellarda.
        height: kadr balandligi piksellarda.

    Returns:
        `npt.NDArray[np.int64]` — `PolygonZone` ning kontrakti AYNAN shu
        turni talab qiladi.

    Raises:
        ValueError: shakl noto'g'ri, tepaliklar uchtadan kam yoki
            koordinata 0..1 dan tashqarida bo'lsa.
            ⚠ Oxirgi shart 05-06 ning `POLYGON_OUT_OF_RANGE` validatsiyasi
            bilan IKKI KARRA: baza yozish paytida rad etadi, bu modul esa
            O'QISH paytida. Ikkinchi devor arzon va u SERVIS CHEGARASIDA
            turadi — `camera_zones` ni `core-api` yozadi, bu yerda esa
            `cv-service` o'qiydi.
    """
    if polygon.ndim != _POINT_COLUMNS or polygon.shape[1] != _POINT_COLUMNS:
        raise ValueError(f"poligon shakli `(n, 2)` bo'lishi kerak, olingani {polygon.shape}")
    if polygon.shape[0] < MIN_POLYGON_POINTS:
        raise ValueError(
            f"poligonda {polygon.shape[0]} tepalik bor, kamida "
            f"{MIN_POLYGON_POINTS} kerak — kamrog'ining ICHKARISI yo'q va "
            "zona jimgina abadiy bo'sh bo'lib qolardi"
        )
    if polygon.min() < 0.0 or polygon.max() > 1.0:
        raise ValueError(
            "poligon koordinatalari 0..1 dan tashqarida. Zonalar NORMALANGAN "
            "saqlanadi (D-07) — aks holda kamera ruxsati o'zgarganda kontur "
            "kadrdan chiqib ketardi."
        )

    scale = np.array([width, height], dtype=np.float64)
    pixels: npt.NDArray[np.int64] = np.rint(polygon * scale).astype(np.int64)
    return pixels


def zone_verdict(
    detections: Detections,
    polygon_px: npt.NDArray[np.int64],
    *,
    thresholds: UncertaintyThresholds,
    anchors: tuple[Position, ...],
    require_all_anchors: bool,
) -> tuple[OccupancyVerdict, float]:
    """Zonadagi detektsiyalardan bandlik verdictini hosil qiladi.

    ⚠ NUQTA-POLIGON HISOBI `supervision` DA — bu funksiya faqat
      `PolygonZone` ni SOZLAYDI va uning natijasidan verdikt yasaydi.

    Qoida (chegaralar INKLYUZIV, `postprocess.raw_to_detections` bilan bir
    xil qaror va bir xil sabab — «chegarada» holati ikki xil o'qilsa,
    chegarani sozlash natijani oldindan aytib bo'lmaydigan qilardi):

        zonada birorta detektsiya yo'q      -> `empty`,     ishonch 0.0
        eng yuqori ishonch >= high          -> `occupied`
        low <= eng yuqori ishonch <  high   -> `uncertain`
        eng yuqori ishonch <  low           -> `empty`

    ⚠ O'LCHOVNING O'ZI QAYTARILADI, FAQAT VERDIKT EMAS (`quality.py` ning
      aynan o'sha qarori): `empty` verdikti ham o'zining o'lchangan
      ishonchini olib keladi. Shunda real Karmana kadrlari kelganda
      chegaralar SQL SO'ROVI bilan (`percentile_cont`) sozlanadi, qayta
      aniqlash bilan emas. `0.0` esa AYNAN BITTA narsani anglatadi:
      zonada o'lchanadigan hech nima BO'LMAGAN.

    Args:
        detections: `postprocess.raw_to_detections()` chiqishi — `xyxy`
            PIKSELDA va `polygon_px` bilan BIR XIL kadr o'lchamida.
        polygon_px: `polygon_to_pixels()` chiqishi.
        thresholds: `uncertain` oynasi — QATORDAN keladi (D-11).
        anchors: `Position` ankorlari. Standart uchun
            `DEFAULT_TRIGGERING_ANCHORS`, lekin u CHAQIRUVCHIDA (D-09).
        require_all_anchors: `True` -> AND, `False` -> OR. Standart uchun
            `DEFAULT_REQUIRE_ALL_ANCHORS`; sabab modul docstringidagi
            «TUZOQ 4» da O'LCHANGAN.

    Returns:
        `(verdikt, ishonch)` — ishonch HAR DOIM 0..1.
    """
    zone = PolygonZone(
        polygon=polygon_px,
        triggering_anchors=anchors,
        require_all_anchors=require_all_anchors,
    )
    inside = zone.trigger(detections)

    confidences = detections.confidence
    if confidences is None or len(inside) == 0 or not bool(np.any(inside)):
        return OccupancyVerdict.EMPTY, 0.0

    best = float(np.max(confidences[inside]))

    if best >= thresholds.uncertain_high:
        return OccupancyVerdict.OCCUPIED, best
    if best >= thresholds.uncertain_low:
        return OccupancyVerdict.UNCERTAIN, best
    return OccupancyVerdict.EMPTY, best
