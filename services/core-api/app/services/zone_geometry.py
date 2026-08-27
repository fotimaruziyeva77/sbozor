"""Kamera zonasi poligonining ISHONCH MANBAI (AI-01, ASVS V5 Input Validation).

Sof funksiyalar moduli (`quality.py`, `rtsp.py`, `live_source.py` bilan bir
xil shakl): tarmoqqa chiqmaydi, bazaga tegmaydi, holat saqlamaydi va
`Settings` ni BILMAYDI — chegaralar unga argument sifatida kiradi.

=============================================================================
NEGA BU TEKSHIRUV SERVERDA HAM BOR: FRONTEND TEKSHIRUVI TAKROR, ISHONCH EMAS.

`frontend/src/lib/zone-geometry.ts` (05-03) aynan shu qoidalarni klientda
tekshiradi va o'sha faylning O'ZI buni ochiq yozadi: «BU YERDAGI TEKSHIRUV —
QULAYLIK, XAVFSIZLIK CHEGARASI EMAS. Ishonch manbai SERVERDA (05-06).»

Sabab ikkita va ikkalasi ham mustaqil:

  1. **Klient chetlab o'tiladi.** `PUT /camera-zones` — oddiy JSON
     endpointi; `curl` bilan yuborilgan har qanday poligon brauzerdagi
     birorta tekshiruvni ko'rmaydi.

  2. **Rad etilgan poligon JIM NOSOZLIK beradi, xato emas.** O'zi bilan
     kesishgan yoki nol uzunlikdagi qirrasi bor figurada «ichkarida»
     tushunchasi ANIQLANMAGAN: `supervision.PolygonZone` ostidagi
     `cv2.pointPolygonTest` bunday shaklda algoritmga qarab TURLI javob
     beradi. Ya'ni xato xabari YO'Q, poligon ekranda KO'RINADI, lekin
     bandlik BOSHQA maydondan o'lchanadi — va u bevosita billing
     chegarasiga o'tadi (T-05-27).

⚠ SERVER KLIENTDAN QAT'IYROQ BO'LISHI MUMKIN VA BU TO'G'RI YO'NALISH.
  `POLYGON_DEGENERATE_EDGE` aynan shunday: klientning `isSelfIntersecting`
  algoritmi takrorlangan tepani TOPA OLMAYDI (nol uzunlikdagi kesmada
  orientatsiya determinanti har doim nol, ya'ni na «nina», na umumiy
  kesishuv sharti bajariladi — bu `tests/unit/test_zone_geometry.py::
  test_client_geometry_cannot_see_a_duplicate_vertex` da O'LCHANGAN).
  Teskarisi — server klientdan YUMSHOQROQ bo'lishi — TAQIQLANGAN: u
  darvozani butunlay brauzerga ko'chirardi.
=============================================================================

⚠ XATO KODLARI REYESTRDAN OLINADI, BU YERDA QAYTA YOZILMAYDI (§S-5).
  Literal nusxa `occupancy_errors.py` bilan bir kun ajralib ketardi va
  o'shanda router ko'targan kod `app/schemas.py::ERROR_CODES` allowlist'iga
  TUSHMASDI — javob HTTP chegarasidan o'tardi-yu, frontend uni tanimay
  `errors.generic` ga tushirardi. Admin poligonning QAYSI qoidasini
  buzganini bilmasdi.

  Quyidagi konstantalar — ALIAS. Ularning docstringi kodning MA'NOSINI
  takrorlamaydi (u reyestrda), balki uni QAYSI GEOMETRIK PREDIKAT
  tug'dirishini yozadi.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Final

from app.services.occupancy_errors import (
    ZONE_ASPECT_MISMATCH,
    ZONE_POLYGON_DEGENERATE_EDGE,
    ZONE_POLYGON_OUT_OF_RANGE,
    ZONE_POLYGON_SELF_INTERSECTING,
    ZONE_POLYGON_TOO_FEW_POINTS,
    ZONE_POLYGON_TOO_MANY_POINTS,
)

__all__ = [
    "ASPECT_RATIO_MISMATCH",
    "POLYGON_DEGENERATE_EDGE",
    "POLYGON_OUT_OF_RANGE",
    "POLYGON_SELF_INTERSECTING",
    "POLYGON_TOO_FEW_POINTS",
    "POLYGON_TOO_MANY_POINTS",
    "ZONE_GEOMETRY_ERROR_CODES",
    "Point",
    "aspect_ratio_matches",
    "denormalize",
    "normalize",
    "validate_polygon",
]

Point = tuple[float, float]
"""Normalangan tepa — ikkala komponent ham 0..1 (`zone-geometry.ts::Pt`)."""


# ---------------------------------------------------------------------------
# Xato kodlari — ALIAS, har biri O'Z PREDIKATI bilan
# ---------------------------------------------------------------------------

POLYGON_TOO_FEW_POINTS: Final[str] = ZONE_POLYGON_TOO_FEW_POINTS
"""Tepalar soni `min_vertices` dan kam.

Predikat SANOQ, geometriya emas: `len(points) < min_vertices`. Chegara
INKLYUZIV — `min_vertices` ning O'ZI yaroqli.

⚠ Bu tekshiruv ENG BIRINCHI turadi va tartib ma'noli: ikki tepali
  «poligon» uchun kesishuv testi baribir `False` qaytarardi (kesma o'zi
  bilan kesishmaydi), ya'ni figura QABUL QILINARDI. Sanoq shartisiz
  geometriya darvozasi bu holatni umuman ko'rmaydi.
"""

POLYGON_TOO_MANY_POINTS: Final[str] = ZONE_POLYGON_TOO_MANY_POINTS
"""Tepalar soni `max_vertices` dan ko'p.

Predikat: `len(points) > max_vertices`. Chegara INKLYUZIV.

⚠ Bu RESURS chegarasi (T-05-21), did emas: har tepa `jsonb` da
  saqlanadi, HAR KADRDA qayta o'qiladi va `supervision.PolygonZone` ga
  uzatiladi. Chegarasiz bitta noto'g'ri klient ming tepali poligon
  yuborib, butun bozorning kunlik bandlik hisobini sekinlashtirardi.
"""

POLYGON_OUT_OF_RANGE: Final[str] = ZONE_POLYGON_OUT_OF_RANGE
"""Biror koordinata `0.0 <= v <= 1.0` shartini BUZDI.

⚠ SHART SOLISHTIRISHGA TAYANADI va bu ataylab: `NaN` bilan har qanday
  solishtirish `False` beradi, ya'ni `0.0 <= nan <= 1.0` ham `False` va
  qiymat RAD ETILADI. `abs(v) > 1.0` shaklidagi teskari yozuv esa `NaN`
  ni JIMGINA o'tkazib yuborardi — Pydantic `float` uchun `allow_inf_nan`
  ni standart holatda YOQIQ qoldiradi, ya'ni `NaN` HTTP chegarasidan
  bemalol o'tadi.

Chegara INKLYUZIV: 0,0 va 1,0 yaroqli. Kadrning chekkasidagi rasta
(devor yonidagi qator) aynan shu qiymatlarga tegadi va uni «biroz
ichkariga» surish o'lchanadigan maydonni jimgina kichraytirardi.
"""

POLYGON_SELF_INTERSECTING: Final[str] = ZONE_POLYGON_SELF_INTERSECTING
"""Qo'shni BO'LMAGAN ikki qirra kesishdi, YOKI qo'shni juft «nina» yasadi.

Ikki predikat, bitta kod:

  * **Umumiy holat** — qo'shni bo'lmagan `(i, i+1)` va `(j, j+1)`
    qirralari kesishadi. TEGIB O'TISH HAM kesishish deb sanaladi:
    qirraning ustida turgan tepa nuqta-poligon testi uchun aynan
    kesishgan poligon kabi aniqlanmagan holat.

  * **«Nina»** — umumiy tepani baham ko'rgan ikki qirra kollinear va
    ikkalasi ham o'sha tepadan BIR TOMONGA ketadi, ya'ni ikkinchisi
    birinchisining ustidan qaytib o'tadi. Umumiy kesishuv testi buni
    TOPA OLMAYDI: qo'shni qirralar ta'rifi bo'yicha bitta nuqtani baham
    ko'radi va shu sababdan istisno qilinadi.

⚠ KOLLINEARLIKNING O'ZI RAD ETILMAYDI. Qirraning O'RTASIDAGI oraliq
  tepa — `insertMidpoint` (05-03) ning natijasi va muharrirdagi eng
  ko'p ishlatiladigan amal. Farq YO'NALISHDA: oraliq tepada uchala nuqta
  bir tomonga ketadi (`dot > 0` bajarilmaydi), «nina» da esa qaytadi.
"""

POLYGON_DEGENERATE_EDGE: Final[str] = ZONE_POLYGON_DEGENERATE_EDGE
"""Ketma-ket ikki tepa orasidagi masofa `_EPS` dan kichik — qirra NOL uzunlikda.

Yopiluvchi qirra (oxirgi -> birinchi) HAM tekshiriladi: `zip(points,
points[1:])` shaklidagi tabiiy yozuv uni umuman ko'rmaydi va poligonning
oxiri bilan boshi ustma-ust tushishi jimgina o'tib ketardi.

⚠ CHEGARA — ORIENTATSIYA TESTIDAGI AYNAN O'SHA `_EPS`, yangi son emas.
  Ikki qoida bir xil «nol» tushunchasiga tayanishi SHART: orientatsiya
  determinanti ajrata olmaydigan farq qirra uzunligi uchun ham nol.
  Boshqa chegara qo'yilsa ikki qoida orasida YORIQ paydo bo'lardi —
  u yerga tushgan poligon na kesishgan, na degenerat deb hisoblanib,
  zona kutubxonasiga aniqlanmagan holda yetib borardi.

⚠ TEKSHIRUV KESISHUVDAN OLDIN va tartib FOYDALANUVCHI uchun ma'noli:
  «zona o'zi bilan kesishgan» xabarini olgan admin kesishmani QIDIRADI
  va topa olmaydi — takrorlangan tepa ekranda bitta nuqta bo'lib
  ko'rinadi. Ikki kod ikki xil tuzatish yo'lini ko'rsatadi.
"""

ASPECT_RATIO_MISMATCH: Final[str] = ZONE_ASPECT_MISMATCH
"""Joriy kadr nisbati poligon chizilgandagidan farq qiladi.

⚠ BU `validate_polygon()` NING NATIJASI EMAS va u yerda hech qachon
  qaytarilmaydi. Poligon nisbat farqi tufayli RAD ETILMAYDI — u
  saqlanadi va `needs_review` bayrog'i bilan belgilanadi (§6.8).
  Predikat `aspect_ratio_matches()` da va u `bool` qaytaradi.

⛔ AVTOMATIK TO'G'RILASH QILINMAYDI. Kadr cho'zilganmi yoki kesilganmi —
   `source_width`/`source_height` dan bilib bo'lmaydi va noto'g'ri
   tuzatish xatoni «tuzatilgan» qilib ko'rsatib, uni o'lchanmas holga
   keltirardi. To'g'ri xulq — ODAMDAN so'rash.
"""

ZONE_GEOMETRY_ERROR_CODES: Final[frozenset[str]] = frozenset(
    {
        POLYGON_TOO_FEW_POINTS,
        POLYGON_TOO_MANY_POINTS,
        POLYGON_OUT_OF_RANGE,
        POLYGON_SELF_INTERSECTING,
        POLYGON_DEGENERATE_EDGE,
        ASPECT_RATIO_MISMATCH,
    }
)
"""Bu modul TUG'DIRADIGAN kodlar — `ZONE_ERROR_CODES` ning QISM to'plami.

Reyestrdagi qolgan uch kod (`zone_limit_reached`,
`zone_stall_already_covered`, `zone_camera_has_no_frame`) geometriya
EMAS: ular sanoq, unikalik va kadr mavjudligi haqida, ya'ni ularni
faqat BAZANI ko'rgan qatlam ayta oladi. Sof funksiya ularni bilmasligi
kerak.
"""


# ---------------------------------------------------------------------------
# Geometrik yordamchilar — `zone-geometry.ts:112-210` ning AYNAN porti
# ---------------------------------------------------------------------------

_EPS: Final[float] = 1e-12
"""Nolga tenglik chegarasi — klient jufti bilan AYNAN BIR XIL QIYMAT.

Koordinatalar 0..1 da, ya'ni tipik kesma-kesishuv determinanti 1e-3
atrofida. 1e-12 — «haqiqiy nol» va «suzuvchi nuqta shovqini» orasidagi
xavfsiz oraliq: undan kichigi kollinear tepalarni o'tkazib yuborardi,
kattasi esa yonma-yon rastalarni kesishgan deb e'lon qilardi.

⚠ QIYMAT KLIENTNIKI BILAN TENG BO'LISHI SHART (`zone-geometry.ts:112`).
  Ajralganda admin brauzerda yashil ko'rgan poligon serverda rad
  etilardi (yoki teskarisi) va sabab EKRANDA ko'rinmasdi.
"""


def _cross(o: Point, a: Point, b: Point) -> float:
    """`o -> a` va `o -> b` vektorlarining ko'paytmasi (ishorasi burilish tomoni)."""
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def _orientation(o: Point, a: Point, b: Point) -> int:
    """Burilish ishorasi: -1, 0 yoki 1 (`_EPS` bilan)."""
    value = _cross(o, a, b)
    if abs(value) < _EPS:
        return 0
    return 1 if value > 0 else -1


def _on_segment(p: Point, q: Point, r: Point) -> bool:
    """`q` kollinear `p`–`r` kesmasining ICHIDA (yoki uchida) turibdimi."""
    return (
        q[0] <= max(p[0], r[0]) + _EPS
        and q[0] >= min(p[0], r[0]) - _EPS
        and q[1] <= max(p[1], r[1]) + _EPS
        and q[1] >= min(p[1], r[1]) - _EPS
    )


def _segments_intersect(p1: Point, q1: Point, p2: Point, q2: Point) -> bool:
    """Ikki kesma kesishadimi — TEGIB O'TISH HAM kesishish deb sanaladi.

    ⚠ Bu faqat QO'SHNI BO'LMAGAN qirralarga qo'llanadi. Qo'shni qirralar
      ta'rifi bo'yicha bitta tepani baham ko'radi, ya'ni bu yerda ular
      HAR DOIM «kesishgan» chiqardi.
    """
    o1 = _orientation(p1, q1, p2)
    o2 = _orientation(p1, q1, q2)
    o3 = _orientation(p2, q2, p1)
    o4 = _orientation(p2, q2, q1)

    # Umumiy holat — haqiqiy kesib o'tish.
    if o1 != o2 and o3 != o4:
        return True

    # Kollinear holatlar: tepa boshqa qirraning USTIDA turibdi.
    return bool(
        (o1 == 0 and _on_segment(p1, p2, q1))
        or (o2 == 0 and _on_segment(p1, q2, q1))
        or (o3 == 0 and _on_segment(p2, p1, q2))
        or (o4 == 0 and _on_segment(p2, q1, q2))
    )


def _is_spike(shared: Point, a: Point, b: Point) -> bool:
    """Bitta tepani baham ko'radigan ikki qirra USTMA-UST TUSHGANMI.

    `shared` — umumiy tepa, `a` va `b` — qolgan uchlari. Uchalasi
    kollinear bo'lsa VA `a` bilan `b` `shared` dan BIR TOMONGA ketsa,
    ikkinchi qirra birinchisining ustidan qaytib o'tadi («nina»).
    """
    if _orientation(shared, a, b) != 0:
        return False
    dot = (a[0] - shared[0]) * (b[0] - shared[0]) + (a[1] - shared[1]) * (b[1] - shared[1])
    return dot > _EPS


def _is_self_intersecting(polygon: Sequence[Point]) -> bool:
    """Poligon o'zi bilan kesishadimi (`zone-geometry.ts::isSelfIntersecting`).

    Uchdan kam tepa bu yerda «kesishmagan» deb qaytariladi va bu ataylab:
    sanoq holatini `POLYGON_TOO_FEW_POINTS` hal qiladi va uni bu yerda
    «kesishgan» deb e'lon qilish xato SABABINI yashirardi.
    """
    n = len(polygon)
    if n < 3:
        return False

    for i in range(n):
        a1 = polygon[i]
        a2 = polygon[(i + 1) % n]

        for j in range(i + 1, n):
            b1 = polygon[j]
            b2 = polygon[(j + 1) % n]

            adjacent = j == i + 1 or (i == 0 and j == n - 1)

            if adjacent:
                # Umumiy tepa: `i+1` juftida `a2`, yopiluvchi juftda `a1`.
                shared = a2 if j == i + 1 else a1
                other1 = a1 if j == i + 1 else a2
                other2 = b2 if j == i + 1 else b1
                if _is_spike(shared, other1, other2):
                    return True
                continue

            if _segments_intersect(a1, a2, b1, b2):
                return True

    return False


def _has_degenerate_edge(polygon: Sequence[Point]) -> bool:
    """Ketma-ket ikki tepa `_EPS` dan yaqinmi (YOPILUVCHI qirra ham).

    ⚠ `range(n)` va `(i + 1) % n` — yopiluvchi qirrani ham qamraydi.
      `zip(polygon, polygon[1:])` ni ishlatish oxirgi va birinchi tepa
      ustma-ust tushgan holatni umuman ko'rmasdi.
    """
    n = len(polygon)
    for i in range(n):
        current = polygon[i]
        following = polygon[(i + 1) % n]
        if abs(current[0] - following[0]) < _EPS and abs(current[1] - following[1]) < _EPS:
            return True
    return False


# ---------------------------------------------------------------------------
# Ommaviy yuza
# ---------------------------------------------------------------------------


def validate_polygon(
    points: Sequence[Point],
    *,
    min_vertices: int,
    max_vertices: int,
) -> str | None:
    """Poligonni V5 qoidalari bo'yicha tekshiradi; yaroqli bo'lsa `None`.

    Zanjir ARZONDAN QIMMATGA va tartib MA'NOLI (`quality.py::analyze()`
    bilan bir xil qaror):

        1. Tepalar soni        -> O(1),  geometriyaga umuman kirmaydi
        2. 0..1 oralig'i       -> O(n),  har koordinata bo'yicha bir marta
        3. Nol uzunlikdagi qirra -> O(n)
        4. O'z-o'zi bilan kesishish -> O(n²)

    ⚠ TARTIB FAQAT TEZLIK MASALASI EMAS. Har qadam o'zidan keyingisini
      MA'NOLI qiladi:

        * sanoqsiz ikki tepali «poligon» kesishuv testidan BEMALOL
          o'tardi (kesma o'zi bilan kesishmaydi) va qabul qilinardi;
        * oraliq tekshiruvisiz `NaN` koordinata orientatsiya
          determinantini `NaN` qilardi va u `abs(value) < _EPS` da
          `False` berib, kesishuv testini JIMGINA o'chirardi;
        * nol uzunlikdagi qirra kesishuv testi uchun aniqlanmagan
          kirish — u yerda hech qanday javob ishonchli emas.

    Args:
        points: normalangan tepalar (`[[x, y], ...]`, har biri 0..1).
        min_vertices: eng kam tepa soni; chegara INKLYUZIV.
        max_vertices: eng ko'p tepa soni; chegara INKLYUZIV.

    Returns:
        `ZONE_GEOMETRY_ERROR_CODES` dan xato kodi, yoki yaroqli poligon
        uchun `None`. Chaqiruvchi (05-06 routeri) kodni HTTP `detail`
        ga aylantiradi va matnni frontend uch tilda chizadi (D-02).
    """
    if len(points) < min_vertices:
        return POLYGON_TOO_FEW_POINTS
    if len(points) > max_vertices:
        return POLYGON_TOO_MANY_POINTS

    for x, y in points:
        # ⚠ Solishtirish shakli `NaN` uchun MUHIM — konstanta docstringiga
        #   qarang. Bu satrni `abs(...) > 1.0` ga aylantirmang.
        if not (0.0 <= x <= 1.0) or not (0.0 <= y <= 1.0):
            return POLYGON_OUT_OF_RANGE

    if _has_degenerate_edge(points):
        return POLYGON_DEGENERATE_EDGE

    if _is_self_intersecting(points):
        return POLYGON_SELF_INTERSECTING

    return None


def aspect_ratio_matches(
    source_width: int,
    source_height: int,
    current_width: int,
    current_height: int,
    *,
    tolerance: float,
) -> bool:
    """Joriy kadr nisbati poligon chizilgandagi bilan MOSMI.

    Poligon 0..1 da saqlanadi, ya'ni asosiy oqim <-> sub-oqim almashuvi
    NISBAT SAQLANGANDA butunlay zararsiz: 1280x720 va 1920x1080 uchun
    bir xil normalangan koordinata AYNAN o'sha joyni ko'rsatadi. Nisbat
    o'zgarganda (16:9 -> 4:3) esa koordinatalar JIMGINA siljiydi.

    ⚠ KO'PAYTIRISH BILAN SOLISHTIRILADI, BO'LISH BILAN EMAS:
      `|w1*h2 - w2*h1| <= tolerance * h1 * h2`. Ikki bo'linish natijasini
      ayirish qo'shimcha yaxlitlash xatosi kiritardi va tolerans aynan
      chegara atrofida barqarorligini yo'qotardi.

    ⚠ NOL YOKI MANFIY O'LCHAM -> `False` (fail-closed). Istisno ko'tarish
      `GET /camera-zones` ni 500 ga aylantirardi; `True` qaytarish esa
      undan ham yomon — nisbatni solishtirib bo'lmagan holda «hammasi
      joyida» deyish D-07 ning to'g'ridan-to'g'ri buzilishi bo'lardi.
      Xavfsiz yo'nalish — zonani `needs_review` qilib, ODAMDAN so'rash.

    Args:
        source_width: `camera_zones.source_width`.
        source_height: `camera_zones.source_height`.
        current_width: bugungi kadrning kengligi.
        current_height: bugungi kadrning balandligi.
        tolerance: nisbat farqining ruxsat etilgan yuqori chegarasi.

    Returns:
        Nisbatlar mos bo'lsa `True`. Mos bo'lmasa `False` — bu POLIGONNI
        RAD ETMAYDI, u faqat `needs_review` bayrog'ini ko'taradi (§6.8).
    """
    if source_width <= 0 or source_height <= 0 or current_width <= 0 or current_height <= 0:
        return False

    difference = abs(source_width * current_height - current_width * source_height)
    return difference <= tolerance * source_height * current_height


def _require_positive_extent(width: int, height: int) -> None:
    """Kadr o'lchami musbatligini talab qiladi (`assertPositiveExtent` jufti)."""
    if width <= 0 or height <= 0:
        raise ValueError(
            f"zone_geometry: kadr o'lchami musbat bo'lishi SHART (olindi: {width}x{height}). "
            "Nol kenglik jimgina cheksiz koordinata yasab, poligonni butunlay yo'qotardi; "
            "manfiy kenglik esa manfiy koordinata berib, sabab boshqa darvozada ko'rinardi."
        )


def normalize(point: Sequence[float], width: int, height: int) -> Point:
    """Piksel -> 0..1.

    Qisish YO'Q va bu ataylab (`zone-geometry.ts::normalize` bilan bir xil
    qaror): bu SOF konversiya. Kadr tashqarisidagi nuqtani qisish
    `validate_polygon()` ning ishi emas — u bunday nuqtani RAD ETADI,
    chunki «qisib to'g'rilash» admin chizgan shaklni jimgina o'zgartirardi.
    """
    _require_positive_extent(width, height)
    return (point[0] / width, point[1] / height)


def denormalize(point: Sequence[float], width: int, height: int) -> tuple[int, int]:
    """0..1 -> piksel, BUTUN songa yaxlitlangan.

    ⚠ YAXLITLASH — AYLANMA YO'QOTISHSIZLIGINING SHARTI, bezak emas:
      `denormalize(normalize(p, w, h), w, h) == p` faqat shunda HAR
      BUTUN pikselda bajariladi. Yaxlitlashsiz poligon har ochilib
      saqlanganda joyidan bir oz siljib, bir necha tahrirdan keyin
      rastadan «sirg'alib» chiqardi — hech qanday xato xabarisiz.
      1279 kenglikda 1280 pikseldan 183 tasi qo'pol arifmetikada
      yo'qotadi (05-03 da o'lchangan va bu yerda qayta o'lchanadi).
    """
    _require_positive_extent(width, height)
    return (_round_half_up(point[0] * width), _round_half_up(point[1] * height))


def _round_half_up(value: float) -> int:
    """Eng yaqin butun son; YARIM qiymat YUQORIGA (`Math.round` bilan bir xil).

    =========================================================================
    ⛔ O'RNATILGAN `round()` BU YERDA ISHLATILMAYDI.

    Python ning `round()` i — BANKIR YAXLITLASHI (yarimni JUFT songa):
    `round(640.5) == 640`, lekin `round(641.5) == 642`. JavaScript ning
    `Math.round` esa yarimni HAR DOIM yuqoriga oladi. Ya'ni klient va
    server aynan chegara qiymatida BIR PIKSELGA ajralardi va farq faqat
    ba'zi koordinatalarda, ba'zi kadr kengliklarida ko'rinardi — ya'ni
    takrorlab bo'lmaydigan «zona bir piksel siljidi» nosozligi.

    `math.floor(value + 0.5)` HAM ISHLATILMAYDI: qo'shishning O'ZI
    suzuvchi nuqtada yaxlitlash xatosi kiritadi (`0.49999999999999994 +
    0.5` aynan `1.0` beradi). Kasr qismini AYIRISH bilan olish esa aniq.
    =========================================================================
    """
    floor_value = math.floor(value)
    return floor_value + 1 if value - floor_value >= 0.5 else floor_value
