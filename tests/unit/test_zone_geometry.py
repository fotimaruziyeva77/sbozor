"""Poligon geometriyasining SERVER TOMONDAGI darvozasi (AI-01, ASVS V5).

=============================================================================
BU FAYL «FRONTEND ALLAQACHON TEKSHIRADI» DEGAN E'TIROZGA QARSHI YOZILGAN.

`frontend/src/lib/zone-geometry.ts` (05-03) aynan shu qoidalarni klientda
tekshiradi va u yerdagi izoh buni ochiq aytadi: «BU YERDAGI TEKSHIRUV —
QULAYLIK, XAVFSIZLIK CHEGARASI EMAS. Ishonch manbai SERVERDA (05-06).»

Klient tekshiruvi `curl` bilan chetlab o'tiladi. O'zi bilan kesishgan
poligon esa zona kutubxonasida (`supervision`, `cv2.pointPolygonTest`)
ANIQLANMAGAN natija beradi — ya'ni xato xabari YO'Q, poligon ekranda
KO'RINADI, lekin bandlik boshqa maydondan o'lchanadi va u bevosita
billing chegarasiga o'tadi. Shuning uchun darvoza SAQLASH paytida,
serverda turadi.
=============================================================================

AYLANMA TESTI — SANAB CHIQILADI, TANLAB OLINMAYDI (05-03 ning o'lchovi).

05-03 da `denormalize` dan yaxlitlash BUTUNLAY olib tashlanganda aylanma
testi YASHIL qolgan: qo'lda tanlangan beshta piksel IEEE754 da tasodifan
aniq aylanardi. O'lchov: 1279 kenglikda 1280 ta butun pikseldan 183 tasi
qo'pol arifmetikada yo'qotadi, lekin tanlangan qiymatlar ular orasida
emas edi — ya'ni test o'z farazini tasdiqlab, himoya qilishi kerak
bo'lgan xususiyatni UMUMAN o'lchamagan.

Bu yerda o'sha xato TAKRORLANMAYDI. Ikki qadam:
  (a) FIXTURE HAQIQIYLIGI alohida assert bilan o'lchanadi — rad etilgan
      arifmetika (yaxlitlashsiz) HAQIQATAN yo'qotishi isbotlanadi;
  (b) chekli domen (kadr kengligi) TO'LIQ sanab chiqiladi, ya'ni «omadli
      fixture» yo'li butunlay yopiladi.

=============================================================================
KUTILGAN NATIJALAR QO'LDA HISOBLANGAN VA LITERAL (`test_rtsp_url.py` naqshi).

Birorta kutilgan qiymat tekshirilayotgan funksiyaning O'ZI bilan
hisoblanmaydi — aks holda test funksiyaning bugungi xulqini tasdiqlab,
uning TO'G'RILIGINI umuman o'lchamasdi.
"""

from __future__ import annotations

import math
from pathlib import Path

import pytest
from app.services.occupancy_errors import OCCUPANCY_ERROR_CODES
from app.services.zone_geometry import (
    ASPECT_RATIO_MISMATCH,
    POLYGON_DEGENERATE_EDGE,
    POLYGON_OUT_OF_RANGE,
    POLYGON_SELF_INTERSECTING,
    POLYGON_TOO_FEW_POINTS,
    POLYGON_TOO_MANY_POINTS,
    ZONE_GEOMETRY_ERROR_CODES,
    aspect_ratio_matches,
    denormalize,
    normalize,
    validate_polygon,
)

# ---------------------------------------------------------------------------
# Chegaralar TESTDA e'lon qilinadi, `Settings` dan OLINMAYDI
#
# ⚠ Modul `Settings` ni bilmaydi (§S-8) va test ham bilmasligi kerak: agar
#   test chegarani sozlamadan olsa, sozlamani o'zgartirish testni JIMGINA
#   boshqa qiymat ustida ishlatardi va «12 tepa chegarasi ishlaydi» da'vosi
#   bugun 12, ertaga 60 haqida bo'lardi.
# ---------------------------------------------------------------------------

MIN_VERTICES = 3
MAX_VERTICES = 12

# Poligon chizilgan odatiy kadr o'lchamlari (`cameras.capture_stream`).
HD_WIDTH, HD_HEIGHT = 1280, 720
FHD_WIDTH, FHD_HEIGHT = 1920, 1080
VGA_WIDTH, VGA_HEIGHT = 640, 480

ASPECT_TOLERANCE = 0.01
"""Nisbat farqining ruxsat etilgan chegarasi — LITERAL, sozlamadan emas.

16:9 = 1,7778 va 4:3 = 1,3333, ya'ni farq 0,4444 — chegaradan qirq
barobar katta. Ya'ni bu test tolerans qiymatining ANIQ tanloviga
sezgir emas va u shu sababdan barqaror.
"""


def square(x0: float, y0: float, x1: float, y1: float) -> list[tuple[float, float]]:
    """Ikki burchakdan to'rtburchak — GEOMETRIK FAKT bo'yicha nomlangan (§S-9).

    Funksiya `validate_polygon()` ni ham, uning chegaralarini ham
    BILMAYDI: u faqat «shu ikki burchak orasidagi to'rtburchak» ni
    qaytaradi. «Yaroqli poligon» deb nomlangan yordamchi testni
    darvozaning aks-sadosiga aylantirardi.
    """
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def regular_polygon(n: int) -> list[tuple[float, float]]:
    """Markazi (0,5; 0,5), radiusi 0,4 bo'lgan MUNTAZAM `n`-burchak.

    Muntazam ko'pburchak ta'rifi bo'yicha qavariq, ya'ni u hech qachon
    o'zi bilan kesishmaydi va ketma-ket tepalari hech qachon ustma-ust
    tushmaydi (`n >= 3` da). Bu — tepa SONI chegaralarining sof
    nazorati: shakl hech qanday boshqa qoidani qo'zg'atmaydi.
    """
    return [
        (
            round(0.5 + 0.4 * math.cos(2 * math.pi * k / n), 6),
            round(0.5 + 0.4 * math.sin(2 * math.pi * k / n), 6),
        )
        for k in range(n)
    ]


def check(points: list[tuple[float, float]]) -> str | None:
    """`validate_polygon` ni testdagi chegaralar bilan chaqiradi."""
    return validate_polygon(points, min_vertices=MIN_VERTICES, max_vertices=MAX_VERTICES)


# ===========================================================================
# 1. Reyestr — YANGI KOD O'YLAB TOPILMAGAN (§S-5)
# ===========================================================================


def test_every_geometry_code_lives_in_the_occupancy_registry() -> None:
    """Oltala kod `OCCUPANCY_ERROR_CODES` NING ICHIDA.

    ⛔ NEGA BU MUHIM: `app/schemas.py::ERROR_CODES` allowlist'i AYNAN shu
       reyestrdan quriladi. Reyestrda yo'q kod bilan `HTTPException`
       ko'tarilsa, javob HTTP chegarasidan o'tadi-yu, frontend uni
       tanimay `errors.generic` ga tushirardi — admin poligonning QAYSI
       qoidasini buzganini BILMASDI va xato «kutilmagan nosozlik» bo'lib
       ko'rinardi.

    Bugungi holatda kodlar reyestrdan IMPORT qilinadi, ya'ni bu tekshiruv
    o'z-o'zidan bajariladi. U shunga qaramay yozilgan: kimdir aliasni
    literal satr bilan almashtirsa (eng tabiiy «soddalashtirish»),
    darvoza AYNAN shu yerda qizaradi.
    """
    assert set(ZONE_GEOMETRY_ERROR_CODES) <= OCCUPANCY_ERROR_CODES

    # Nazorat: reyestr bo'shab qolmagan. Bo'sh to'plam yuqoridagi
    # `<=` ni HAR DOIM qanoatlantirardi.
    assert len(ZONE_GEOMETRY_ERROR_CODES) == 6


def test_geometry_module_does_not_import_settings() -> None:
    """Modul `Settings` ni BILMAYDI — chegaralar argument sifatida kiradi (§S-8).

    ⛔ GREP EMAS, TEST: qabul mezoni buni `grep` bilan tekshiradi, lekin
       grep faqat ijro paytida qo'lda chaqiriladi. Bu yerda u CI'ning
       doimiy qismi.

    Import qaytadan paydo bo'lsa nima buziladi: chegaralar modul ichida
    o'qilardi, ya'ni ularni testda argument bilan berish imkonsiz bo'lardi
    va butun to'plam muhitga (`.env`) bog'lanib qolardi. Bu D-11 ning
    bevosita talabi (`quality.py::QualityThresholds` docstringi).
    """
    source = Path(__file__).resolve().parents[2] / (
        "services/core-api/app/services/zone_geometry.py"
    )
    code_lines = [
        line
        for line in source.read_text(encoding="utf-8").splitlines()
        if line.lstrip().startswith(("from ", "import "))
    ]
    offenders = [line for line in code_lines if "app.settings" in line]

    assert not offenders, f"`Settings` importi qaytib keldi: {offenders}"


# ===========================================================================
# 2. Tepa soni — IJOBIY va SALBIY
# ===========================================================================


def test_two_vertices_are_rejected_as_too_few() -> None:
    """Ikki tepa FIGURA emas, CHIZIQ — yuzasi nol."""
    assert check([(0.1, 0.1), (0.9, 0.9)]) == POLYGON_TOO_FEW_POINTS


def test_three_vertices_are_accepted() -> None:
    """SALBIY NAZORAT: `min_vertices` ning O'ZI yaroqli (chegara INKLYUZIV).

    Usiz yuqoridagi test «hamma poligon rad etiladi» holatida ham yashil
    bo'lardi.
    """
    assert check([(0.1, 0.1), (0.9, 0.1), (0.5, 0.9)]) is None


def test_thirteen_vertices_are_rejected_as_too_many() -> None:
    """`max_vertices + 1` tepa rad etiladi (T-05-21, resurs chegarasi)."""
    assert check(regular_polygon(MAX_VERTICES + 1)) == POLYGON_TOO_MANY_POINTS


def test_twelve_vertices_are_accepted() -> None:
    """SALBIY NAZORAT: `max_vertices` ning O'ZI yaroqli (chegara INKLYUZIV)."""
    assert check(regular_polygon(MAX_VERTICES)) is None


def test_vertex_limits_are_arguments_not_constants() -> None:
    """Chegara CHAQIRUVDAN keladi — modulda qadalgan son YO'Q.

    Bir xil poligon ikki xil chegara bilan ikki xil javob oladi. Agar
    modul o'z konstantasiga tayansa, bu test qizarardi va aynan shu
    `Settings` ga qaytishning birinchi qadami bo'lardi.
    """
    pentagon = regular_polygon(5)

    assert validate_polygon(pentagon, min_vertices=3, max_vertices=12) is None
    assert validate_polygon(pentagon, min_vertices=3, max_vertices=4) == POLYGON_TOO_MANY_POINTS
    assert validate_polygon(pentagon, min_vertices=6, max_vertices=12) == POLYGON_TOO_FEW_POINTS


# ===========================================================================
# 3. 0..1 oralig'i — CHEGARA INKLYUZIV
# ===========================================================================


@pytest.mark.parametrize(
    ("label", "point"),
    [
        ("x biroz katta", (1.0000001, 0.5)),
        ("y biroz katta", (0.5, 1.0000001)),
        ("x biroz manfiy", (-0.0000001, 0.5)),
        ("y biroz manfiy", (0.5, -0.0000001)),
        ("piksel koordinatasi", (640.0, 360.0)),
    ],
)
def test_coordinate_outside_the_unit_square_is_rejected(
    label: str, point: tuple[float, float]
) -> None:
    """Oraliqdan tashqaridagi koordinata rad etiladi (D-07 normalash shartnomasi).

    ⚠ «piksel koordinatasi» holati ATAYIN ro'yxatda: eng ehtimoliy
      haqiqiy xato — klient normalashni unutib, xom pikselni yuborishi.
      Chegarasiz bunday poligon SAQLANARDI va denormalashdan keyin kadr
      chetidan ancha uzoqqa tushardi — ya'ni zona ko'rinmas bo'lib
      qolardi, lekin rasta baribir «qamrovda» deb sanalardi va D-22
      jimgina yolg'onga aylanardi.
    """
    assert check([point, (0.2, 0.2), (0.3, 0.4)]) == POLYGON_OUT_OF_RANGE, label


def test_exact_zero_and_one_are_valid() -> None:
    """SALBIY NAZORAT: 0,0 va 1,0 — YAROQLI (chegara INKLYUZIV).

    ⛔ Bu bo'sh formallik emas: kadrning chekkasidagi rasta (devor
       yonidagi qator) aynan 0,0 yoki 1,0 ga tegadi. Eksklyuziv chegara
       bunday zonalarni rad etib, admin nima qilishni bilmay qolardi —
       poligonni «biroz ichkariga» surish esa o'lchanadigan maydonni
       jimgina kichraytirardi.
    """
    assert check([(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]) is None


def test_nan_coordinate_is_rejected() -> None:
    """`NaN` — oraliqdan tashqarida (Pydantic `float` uni O'TKAZADI).

    ⚠ Pydantic 2 standart holatda `float` uchun `NaN` va `Infinity` ni
      QABUL QILADI (`allow_inf_nan` standarti `True`), ya'ni bu qiymat
      HTTP chegarasidan o'tib shu funksiyaga yetib keladi. `NaN` bilan
      har qanday solishtirish `False` beradi — ya'ni «kichikmi?» ham,
      «kattami?» ham yo'q — va u nuqta-poligon testida aniqlanmagan
      natija berardi.

    Solishtirishga TAYANGAN oraliq tekshiruvi (`0.0 <= v <= 1.0`) uni
    O'ZI rad etadi; `abs(v) > 1` shaklidagi tekshiruv esa `NaN` ni
    JIMGINA o'tkazib yuborardi.
    """
    assert check([(math.nan, 0.5), (0.2, 0.2), (0.3, 0.4)]) == POLYGON_OUT_OF_RANGE
    assert check([(math.inf, 0.5), (0.2, 0.2), (0.3, 0.4)]) == POLYGON_OUT_OF_RANGE


# ===========================================================================
# 4. O'Z-O'ZI BILAN KESISHISH — klient jufti bilan BIR XIL javob
# ===========================================================================


def test_bowtie_is_rejected() -> None:
    """«Kapalak» — ikki qarama-qarshi qirra kesishadi (T-05-27)."""
    bowtie = [(0.1, 0.1), (0.9, 0.9), (0.9, 0.1), (0.1, 0.9)]

    assert check(bowtie) == POLYGON_SELF_INTERSECTING


@pytest.mark.parametrize(
    ("label", "points"),
    [
        ("soat mili bo'yicha", [(0.1, 0.1), (0.1, 0.9), (0.9, 0.9), (0.9, 0.1)]),
        ("soat miliga qarshi", [(0.1, 0.1), (0.9, 0.1), (0.9, 0.9), (0.1, 0.9)]),
    ],
)
def test_simple_quadrilateral_is_accepted_in_both_windings(
    label: str, points: list[tuple[float, float]]
) -> None:
    """SALBIY NAZORAT: oddiy to'rtburchak IKKALA aylanish yo'nalishida ham yaroqli.

    Aylanish yo'nalishi — admin poligonni qaysi tomonga chizganining
    natijasi va u hech qanday ma'no tashimaydi. Bir yo'nalishni rad
    etadigan algoritm zonalarning yarmini sababsiz bloklardi.
    """
    assert check(points) is None, label


def test_spike_along_an_existing_edge_is_rejected() -> None:
    """«Nina» — qo'shni qirra birinchisining USTIDAN qaytib o'tadi.

    Umumiy tepani baham ko'rgan ikki qirra kollinear bo'lib, ikkalasi ham
    o'sha tepadan BIR TOMONGA ketsa, poligon nol kenglikdagi tilim bilan
    qoladi. Oddiy kesma-kesishuv testi buni TOPA OLMAYDI (qo'shni qirralar
    ta'rifi bo'yicha bitta nuqtani baham ko'radi va ular istisno
    qilinadi), shuning uchun u ALOHIDA shart.

    Bu yerda tepa (0,5; 0,1) dan (0,9; 0,1) ga, so'ng (0,3; 0,1) ga
    boradi — ikkinchi qirra birinchisining ustidan qaytadi.
    """
    spike = [(0.1, 0.1), (0.5, 0.1), (0.9, 0.1), (0.3, 0.1), (0.5, 0.9)]

    assert check(spike) == POLYGON_SELF_INTERSECTING


def test_collinear_vertex_on_a_straight_edge_is_accepted() -> None:
    """SALBIY NAZORAT: qirra USTIDAGI oraliq tepa — YAROQLI, «nina» EMAS.

    ⛔ Bu farq «nina» testining butun qiymati. `insertMidpoint`
       (05-03) aynan shunday tepa qo'yadi — qirraning o'rtasiga — va u
       muharrirda eng ko'p ishlatiladigan amal. Kollinearlikning O'ZINI
       rad etadigan algoritm har qo'shilgan o'rta nuqtani xato deb
       e'lon qilardi va zona muharriri ishlatib bo'lmas holga kelardi.

    Farq YO'NALISHDA: bu yerda uchala tepa BIR TOMONGA ketadi (0,1 -> 0,5
    -> 0,9), «nina» da esa ikkinchi qirra ORQAGA qaytadi.
    """
    with_midpoint = [(0.1, 0.1), (0.5, 0.1), (0.9, 0.1), (0.9, 0.9), (0.1, 0.9)]

    assert check(with_midpoint) is None


def test_vertex_touching_a_non_adjacent_edge_is_rejected() -> None:
    """TEGIB O'TISH HAM KESISHISH (klient jufti bilan bir xil qaror).

    Qirraning ustida turgan tepa `cv2.pointPolygonTest` uchun aynan
    kesishgan poligon kabi aniqlanmagan holat: nuqta «ichkarida» ham,
    «tashqarida» ham emas va javob algoritmga qarab o'zgaradi.

    Bu yerda (0,5; 0,1) tepasi (0,1; 0,1)–(0,9; 0,1) qirrasi ustida
    turibdi, lekin u o'sha qirraga QO'SHNI EMAS.
    """
    touching = [(0.1, 0.1), (0.9, 0.1), (0.9, 0.9), (0.5, 0.1), (0.1, 0.9)]

    assert check(touching) == POLYGON_SELF_INTERSECTING


# ===========================================================================
# 5. NOL UZUNLIKDAGI QIRRA — klient buni TOPA OLMAYDI
# ===========================================================================


def test_duplicate_consecutive_vertex_is_rejected() -> None:
    """Ketma-ket ikki AYNAN bir xil tepa — qirraning uzunligi nol."""
    duplicated = [(0.1, 0.1), (0.9, 0.1), (0.9, 0.1), (0.9, 0.9), (0.1, 0.9)]

    assert check(duplicated) == POLYGON_DEGENERATE_EDGE


def test_duplicate_across_the_closing_edge_is_rejected() -> None:
    """OXIRGI va BIRINCHI tepa ustma-ust — YOPILUVCHI qirra nol uzunlikda.

    ⚠ Yopiluvchi qirra eng oson unutiladigan holat: `zip(points,
      points[1:])` shaklidagi tabiiy yozuv uni UMUMAN ko'rmaydi va
      poligonning oxiri bilan boshi ustma-ust tushishi jimgina
      o'tkazilardi.
    """
    closed_on_itself = [(0.1, 0.1), (0.9, 0.1), (0.9, 0.9), (0.1, 0.1)]

    assert check(closed_on_itself) == POLYGON_DEGENERATE_EDGE


def test_vertices_separated_below_float_noise_are_rejected() -> None:
    """1e-15 ga ajralgan juft ham NOL UZUNLIKDAGI qirra.

    Chegara — orientatsiya testida ishlatiladigan AYNAN O'SHA `EPS`.
    Ikki qoida bir xil «nol» tushunchasiga tayanadi: orientatsiya
    determinanti ajrata olmaydigan farq qirra uzunligi uchun ham nol.
    Boshqa chegara qo'yilsa ikki qoida orasida yoriq paydo bo'lardi —
    u yerda tushgan poligon na kesishgan, na degenerat deb hisoblanib,
    zona kutubxonasiga aniqlanmagan holda yetib borardi.
    """
    almost_identical = [(0.1, 0.1), (0.9, 0.1), (0.9 + 1e-15, 0.1), (0.9, 0.9), (0.1, 0.9)]

    assert check(almost_identical) == POLYGON_DEGENERATE_EDGE


def test_vertices_one_pixel_apart_are_accepted() -> None:
    """SALBIY NAZORAT: HAQIQIY piksel to'ridagi qo'shni tepa YAROQLI.

    1920 kenglikda bitta piksel 1/1920 ≈ 5,2e-4, ya'ni `EPS` (1e-12) dan
    to'qqiz tartib katta. Chegarani piksel o'lchamiga yaqinlashtirish
    admin ataylab qo'ygan tor zonani rad etardi.
    """
    one_pixel = 1.0 / FHD_WIDTH
    narrow = [(0.5, 0.5), (0.5 + one_pixel, 0.5), (0.5 + one_pixel, 0.6), (0.5, 0.6)]

    assert check(narrow) is None


def test_degenerate_edge_is_reported_before_self_intersection() -> None:
    """TARTIB QULFLANGAN: takrorlangan tepa «kesishgan» deb ATALMAYDI.

    ⛔ Sabab foydalanuvchida: «zona o'zi bilan kesishgan» xabarini olgan
       admin kesishmani QIDIRADI va topa olmaydi — takrorlangan tepa
       ekranda bitta nuqta bo'lib ko'rinadi. Ikki kod ikki xil tuzatish
       yo'lini ko'rsatadi va aynan shu farq uchun ular ajratilgan.

    Bu poligonda IKKALA nuqson ham bor: (0,9; 0,1) ikki marta va
    qarama-qarshi qirralar kesishadi.
    """
    both = [(0.1, 0.1), (0.9, 0.9), (0.9, 0.1), (0.9, 0.1), (0.1, 0.9)]

    assert check(both) == POLYGON_DEGENERATE_EDGE


def test_client_geometry_cannot_see_a_duplicate_vertex() -> None:
    """FIXTURE HAQIQIYLIGI: klient darvozasi bu poligonni O'TKAZADI.

    =======================================================================
    ⛔ BU TEST YUQORIDAGI UCHTASINING SABABINI O'LCHAYDI.

    `POLYGON_DEGENERATE_EDGE` reyestrga QO'SHILDI va qo'shishning yagona
    oqlanishi — bu holatni boshqa hech qaysi darvoza ushlamasligi.
    Da'voni yozib qo'yish yetarli emas: u KO'RSATILISHI kerak.

    Bu yerda klientning `isSelfIntersecting` algoritmi AYNAN takrorlanadi
    (uning o'zi TypeScript'da va bu jarayondan chaqirib bo'lmaydi) va
    natija `False` ekani o'lchanadi. Ya'ni takrorlangan tepali poligon
    klient tekshiruvidan BEMALOL o'tadi va uni FAQAT server ushlaydi.

    Nusxa ajralib ketsa nima bo'ladi: bu test yashil qoladi-yu, da'vosi
    yolg'on bo'lardi. Shuning uchun nusxa MINIMAL — faqat qaror beradigan
    ikki shart (orientatsiya nolga teng, `dot` musbat emas) va ular
    `zone-geometry.ts:143-210` dan aynan ko'chirilgan.
    =======================================================================
    """
    eps = 1e-12
    shared = (0.9, 0.1)
    duplicate = (0.9, 0.1)
    neighbour = (0.9, 0.9)

    def cross(o: tuple[float, float], a: tuple[float, float], b: tuple[float, float]) -> float:
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    # `isSpike` ning ikki sharti — ikkalasi ham BAJARILMAYDI.
    assert abs(cross(shared, duplicate, neighbour)) < eps, "orientatsiya nolga teng"
    dot = (duplicate[0] - shared[0]) * (neighbour[0] - shared[0]) + (duplicate[1] - shared[1]) * (
        neighbour[1] - shared[1]
    )
    assert dot == 0.0, "nol vektorning skalyar ko'paytmasi nol"
    assert not dot > eps, "ya'ni `isSpike` `False` qaytaradi — klient buni KO'RMAYDI"


# ===========================================================================
# 6. KADR NISBATI — avtomatik to'g'rilash YO'Q, faqat FAKT
# ===========================================================================


def test_hd_and_full_hd_have_the_same_aspect_ratio() -> None:
    """1280x720 va 1920x1080 — ikkalasi ham 16:9, ya'ni poligon omon qoladi.

    Bu asosiy oqim <-> sub-oqim almashuvining eng ko'p uchraydigan
    holati (`cameras.capture_stream`). Nisbat saqlangani uchun 0..1
    koordinatalar AYNAN o'sha joyni ko'rsatadi va `needs_review`
    ko'tarilmasligi SHART — aks holda har oqim almashuvida butun bozor
    zonalari «tekshirish kerak» bo'lib qolardi va bayroq ma'nosini
    yo'qotardi.
    """
    assert aspect_ratio_matches(
        HD_WIDTH, HD_HEIGHT, FHD_WIDTH, FHD_HEIGHT, tolerance=ASPECT_TOLERANCE
    )


def test_sixteen_to_nine_and_four_to_three_do_not_match() -> None:
    """1280x720 va 640x480 — 16:9 va 4:3, ya'ni koordinatalar SILJIYDI."""
    assert not aspect_ratio_matches(
        HD_WIDTH, HD_HEIGHT, VGA_WIDTH, VGA_HEIGHT, tolerance=ASPECT_TOLERANCE
    )


def test_aspect_comparison_is_symmetric() -> None:
    """Tartib ahamiyatsiz: `(a, b)` va `(b, a)` bir xil javob beradi.

    Chaqiruvchi (05-06 routeri) qaysi juftni oldin qo'yishi tasodifiy va
    assimetrik funksiya `needs_review` ni kameraning qaysi tomonidan
    qaralganiga bog'lab qo'yardi.
    """
    for tolerance in (0.01, 0.5):
        assert aspect_ratio_matches(
            VGA_WIDTH, VGA_HEIGHT, HD_WIDTH, HD_HEIGHT, tolerance=tolerance
        ) == aspect_ratio_matches(HD_WIDTH, HD_HEIGHT, VGA_WIDTH, VGA_HEIGHT, tolerance=tolerance)


def test_non_positive_extent_never_matches() -> None:
    """Nol yoki manfiy o'lcham — MOS EMAS (fail-closed).

    ⛔ Nolga bo'lish bu yerda ISTISNO KO'TARMASLIGI kerak: funksiya
       `GET /camera-zones` yo'lida, ya'ni istisno butun ro'yxatni 500 ga
       aylantirardi. `True` qaytarish esa undan ham yomon — nisbatni
       solishtirib bo'lmagan holda «hammasi joyida» deyish D-07 ning
       to'g'ridan-to'g'ri buzilishi.

    Xavfsiz yo'nalish — `False`, ya'ni zona `needs_review` bo'ladi va
    ODAM qaraydi (§6.8).
    """
    assert not aspect_ratio_matches(HD_WIDTH, 0, FHD_WIDTH, FHD_HEIGHT, tolerance=0.5)
    assert not aspect_ratio_matches(HD_WIDTH, HD_HEIGHT, 0, FHD_HEIGHT, tolerance=0.5)
    assert not aspect_ratio_matches(-HD_WIDTH, HD_HEIGHT, FHD_WIDTH, FHD_HEIGHT, tolerance=0.5)


def test_aspect_mismatch_code_is_not_produced_by_validate_polygon() -> None:
    """`ASPECT_RATIO_MISMATCH` — poligon QOIDASI EMAS, kadr fakti.

    Ikkalasi bitta modulda yashaydi, lekin ikki xil savolga javob beradi:
    `validate_polygon()` «bu shakl yaroqlimi?» deydi, nisbat esa «bu
    shakl HALIYAM o'sha joyni ko'rsatyaptimi?». Nisbat farqi poligonni
    RAD ETMAYDI — u saqlanadi va `needs_review` bilan belgilanadi.
    """
    assert check(square(0.1, 0.1, 0.9, 0.9)) != ASPECT_RATIO_MISMATCH
    assert ASPECT_RATIO_MISMATCH in ZONE_GEOMETRY_ERROR_CODES


# ===========================================================================
# 7. AYLANMA — CHEKLI DOMEN TO'LIQ SANAB CHIQILADI (05-03 ning o'lchovi)
# ===========================================================================


@pytest.mark.parametrize("width", [VGA_WIDTH, HD_WIDTH, 1279, FHD_WIDTH])
def test_round_trip_is_lossless_for_every_integer_pixel(width: int) -> None:
    """`denormalize(normalize(px)) == px` — 0 dan `width` gacha HAR piksel.

    =======================================================================
    ⛔ SANAB CHIQILADI, TANLAB OLINMAYDI — 05-03 DA O'LCHANGAN SABAB.

    O'sha rejada bu da'vo beshta qo'lda tanlangan piksel bilan
    tekshirilgan va `denormalize` dan yaxlitlashni BUTUNLAY olib tashlash
    HECH NIMANI qizartirmagan: tanlangan qiymatlar IEEE754 da tasodifan
    aniq aylanardi. 1279 kenglikda 1280 pikseldan 183 tasi qo'pol
    arifmetikada yo'qotadi — ya'ni tanlash yo'li bilan yozilgan test
    o'zining 14% ehtimolli omadiga tayanardi.
    =======================================================================

    1279 ro'yxatda ATAYIN: u toq va ikkining darajasi emas, ya'ni
    bo'linish natijalari ikkilik kasrda deyarli hech qachon aniq
    ifodalanmaydi.
    """
    for px in range(width + 1):
        normalized = normalize((float(px), 0.0), width, HD_HEIGHT)
        restored = denormalize(normalized, width, HD_HEIGHT)

        assert restored[0] == px, f"{px}/{width} aylanmada yo'qotdi: {restored[0]}"


def test_rounding_is_what_makes_the_round_trip_lossless() -> None:
    """FIXTURE HAQIQIYLIGI: RAD ETILGAN arifmetika HAQIQATAN yo'qotadi.

    =======================================================================
    Yuqoridagi test yaxlitlashsiz ham o'tib ketishi MUMKIN edi, agar
    tanlangan kenglikda bo'linish tasodifan aniq bo'lsa. Bu test aynan
    o'sha farazni o'lchaydi: yaxlitlashsiz (`px / w * w`) NECHTA piksel
    yo'qotishini SANAYDI va sonning noldan katta ekanini talab qiladi.

    Ya'ni «yaxlitlash kerak» degan da'vo bu yerda ISBOTLANADI, boshqa
    joyda esa faqat ISHLATILADI. Yaxlitlash bezak emas — usiz poligon
    har ochilib-saqlanganda joyidan siljib, bir necha tahrirdan keyin
    rastadan «sirg'alib» chiqardi, hech qanday xato xabarisiz.
    =======================================================================
    """
    width = 1279
    lossy = [px for px in range(width + 1) if (px / width) * width != float(px)]

    assert len(lossy) > 0, (
        f"{width} kengligida qo'pol arifmetika hech nimani yo'qotmadi — "
        "bu fixture yaxlitlash haqidagi da'voni UMUMAN o'lchamaydi"
    )
    # 05-03 klient tomonida AYNAN shu sonni o'lchagan.
    assert len(lossy) == 183


def test_denormalize_rounds_halves_upward_like_the_client() -> None:
    """Yarim qiymat YUQORIGA yaxlitlanadi — `Math.round` bilan AYNAN bir xil.

    =======================================================================
    ⛔ PYTHON NING `round()` I BU YERDA ISHLATILMAYDI.

    O'rnatilgan `round()` — BANKIR YAXLITLASHI (yarimni JUFT songa):
    `round(640.5) == 640`, lekin `round(641.5) == 642`. JavaScript ning
    `Math.round` esa yarimni HAR DOIM yuqoriga oladi. Ya'ni ikki tomon
    aynan chegara qiymatida BIR PIKSELGA ajralardi va farq faqat
    ba'zi koordinatalarda, ba'zi kadr kengliklarida ko'rinardi — ya'ni
    «zona bir piksel siljidi» degan, takrorlab bo'lmaydigan nosozlik.

    Nazorat: `round()` ning O'ZI bu yerda BOSHQA javob berishi
    o'lchanadi — aks holda test har qanday amalga mos kelib, hech nimani
    qulflamasdi.
    =======================================================================
    """
    # 0,5 * 1281 = 640,5 — aniq yarim (1281 toq son).
    assert denormalize((0.5, 0.5), 1281, 1283) == (641, 642)

    # Rad etilgan muqobil AYNAN shu joyda boshqa javob beradi.
    assert round(0.5 * 1281) == 640
    assert round(0.5 * 1283) == 642


def test_normalize_rejects_a_non_positive_frame() -> None:
    """Nol kenglik — ISTISNO, jimgina `Infinity` EMAS.

    Nolga bo'lish Pythonda `ZeroDivisionError` beradi, ya'ni bu yerda
    «jimgina» xavfi kichik. Lekin manfiy kenglik JIMGINA manfiy
    koordinata yasardi va u keyingi qadamda `POLYGON_OUT_OF_RANGE` bo'lib
    chiqib, sabab butunlay boshqa joyda ko'rinardi.
    """
    for width, height in ((0, HD_HEIGHT), (HD_WIDTH, 0), (-HD_WIDTH, HD_HEIGHT)):
        with pytest.raises(ValueError, match="musbat"):
            normalize((1.0, 1.0), width, height)
        with pytest.raises(ValueError, match="musbat"):
            denormalize((0.5, 0.5), width, height)
