"""Kameralararo agregatsiya — TO'LIQ SANAB CHIQILGAN JADVAL (AI-05, D-20/D-22).

=============================================================================
KUTILGAN NATIJA FUNKSIYADAN OLINMAYDI — U LITERAL JADVALDA YOZILGAN.

`aggregate_stall_slot(...)` ni chaqirib natijani «kutilgan» deb saqlash
testni funksiyaning O'Z aksiga aylantirardi: qoida qanday buzilsa ham
ikkala tomon birga o'zgarardi va test yashil qolardi. Shuning uchun
bu faylda IKKI literal manba bor va ularning HECH BIRI mahsulot kodidan
hosil qilinmagan:

  `ONE_AND_TWO_CAMERA_TABLE` — 1 va 2 kamerali BARCHA holat (3 + 9 = 12),
                               har biri alohida qatorda, qo'lda yozilgan;
  `EXPECTED_BY_VERDICT_SET`  — yettita bo'sh bo'lmagan kichik to'plam
                               uchun kutilgan verdikt (qo'lda yozilgan).

Ikkinchisi 1–4 kamerali BARCHA kombinatsiyani (3+9+27+81 = 120) qoplaydi
va shu bilan BIRGA o'lchanadigan qo'shimcha DA'VO ham qo'yadi: natija
faqat verdiktlar TO'PLAMIGA bog'liq — tartibga ham, takrorlanish soniga
ham EMAS. Bu da'vo tekin emas: usiz kirish tartibiga bog'liq bo'lgan
implementatsiya (masalan «birinchi uchragan zona yutadi») 120 holatning
hammasida ham yashil qolishi mumkin edi.

⚠ IKKI JADVAL BIR-BIRINI TEKSHIRADI: 1–2 kamerali 12 holat ikkalasida
  ham bor va `test_the_two_literal_tables_agree` ularni solishtiradi.
  Bittasini «tuzatib» ikkinchisini unutish darhol qizil beradi.
=============================================================================
"""

from __future__ import annotations

import itertools
from pathlib import Path
from typing import Final

import pytest
from sbozor_core import occupancy as occupancy_module
from sbozor_core.occupancy import aggregate_stall_slot, effective_verdict

OCCUPIED: Final = "occupied"
UNCERTAIN: Final = "uncertain"
EMPTY: Final = "empty"
NO_COVERAGE: Final = "no_coverage"

AI: Final = "ai"
HUMAN: Final = "human"
DEFAULT_EMPTY: Final = "default_empty"

VERDICTS: Final[tuple[str, ...]] = (OCCUPIED, UNCERTAIN, EMPTY)
"""Zona darajasidagi UCHALA verdikt — `no_coverage` bu yerda ATAYIN yo'q.

`no_coverage` zona verdikti EMAS, u zonalarning YO'QLIGI, ya'ni uni
kombinatsiyalarga qo'shish ifodalab bo'lmaydigan holat yasardi.
"""


# ===========================================================================
# 1-JADVAL — 1 va 2 kamerali BARCHA holat, har biri alohida qatorda
# ===========================================================================

ONE_AND_TWO_CAMERA_TABLE: Final[tuple[tuple[tuple[str, ...], str], ...]] = (
    # --- bitta kamera: javob o'sha zonaning javobi ---
    ((OCCUPIED,), OCCUPIED),
    ((UNCERTAIN,), UNCERTAIN),
    ((EMPTY,), EMPTY),
    # --- ikki kamera: «birortasi band desa band» (D-20) ---
    ((OCCUPIED, OCCUPIED), OCCUPIED),
    ((OCCUPIED, UNCERTAIN), OCCUPIED),
    ((OCCUPIED, EMPTY), OCCUPIED),
    ((UNCERTAIN, OCCUPIED), OCCUPIED),
    ((UNCERTAIN, UNCERTAIN), UNCERTAIN),
    ((UNCERTAIN, EMPTY), UNCERTAIN),
    ((EMPTY, OCCUPIED), OCCUPIED),
    ((EMPTY, UNCERTAIN), UNCERTAIN),
    ((EMPTY, EMPTY), EMPTY),
)
"""3 + 9 = 12 holat, QO'LDA yozilgan.

⚠ `(OCCUPIED, EMPTY)` va `(EMPTY, OCCUPIED)` IKKALASI HAM bor va bu
  ataylab: ular AYNI natijani berishi kerak, ya'ni tartib ahamiyatsiz.
  Faqat bittasini yozish «birinchi kamera yutadi» degan
  implementatsiyani ham o'tkazib yuborardi.
"""


# ===========================================================================
# 2-JADVAL — verdiktlar TO'PLAMI bo'yicha, 1–4 kamerani qoplaydi
# ===========================================================================

EXPECTED_BY_VERDICT_SET: Final[dict[frozenset[str], str]] = {
    frozenset({OCCUPIED}): OCCUPIED,
    frozenset({UNCERTAIN}): UNCERTAIN,
    frozenset({EMPTY}): EMPTY,
    frozenset({OCCUPIED, UNCERTAIN}): OCCUPIED,
    frozenset({OCCUPIED, EMPTY}): OCCUPIED,
    frozenset({UNCERTAIN, EMPTY}): UNCERTAIN,
    frozenset({OCCUPIED, UNCERTAIN, EMPTY}): OCCUPIED,
}
"""Yettita bo'sh bo'lmagan kichik to'plam — qo'lda yozilgan.

`{occupied, empty}` -> `occupied` qatori AI-05 ning aynan matni;
`{uncertain, empty}` -> `uncertain` qatori esa ustuvorlikning talabdan
UZUNROQ qismi: «bir kamera ikkilandi, ikkinchisi bo'sh dedi» holatida
javob HAMON ochiq va u kun oxirida §C.10 bo'yicha hal bo'ladi.
"""

CAMERA_COUNTS: Final[tuple[int, ...]] = (1, 2, 3, 4)

ALL_COMBINATIONS: Final[tuple[tuple[str, ...], ...]] = tuple(
    combination
    for size in CAMERA_COUNTS
    for combination in itertools.product(VERDICTS, repeat=size)
)
"""3 + 9 + 27 + 81 = 120 kombinatsiya (rejaning quyi chegarasi 40)."""


def _pairs(verdicts: tuple[str, ...], source: str = AI) -> list[tuple[str, str]]:
    """Verdiktlar ketma-ketligini `(verdict, source)` juftlariga aylantiradi."""
    return [(verdict, source) for verdict in verdicts]


# ===========================================================================
# Jadval testlari
# ===========================================================================


def test_the_combination_table_covers_every_case() -> None:
    """NAZORAT: 120 kombinatsiya haqiqatan yig'ilgan va hammasi noyob.

    ⚠ USIZ QUYIDAGI `parametrize` JIMGINA BO'SHAB QOLISHI MUMKIN EDI:
      bo'sh ro'yxatda pytest birorta test yaratmaydi va to'plam
      «hammasi o'tdi» deb tugaydi.
    """
    assert len(ALL_COMBINATIONS) == 120, (
        f"{len(ALL_COMBINATIONS)} kombinatsiya yig'ildi, 120 kutilgan — "
        "`VERDICTS` yoki kamera sonlari o'zgargan"
    )
    assert len(set(ALL_COMBINATIONS)) == len(ALL_COMBINATIONS)
    assert len(EXPECTED_BY_VERDICT_SET) == 7, (
        "yettita bo'sh bo'lmagan kichik to'plam kutilgan — jadval to'liq emas"
    )


@pytest.mark.parametrize(("verdicts", "expected"), ONE_AND_TWO_CAMERA_TABLE)
def test_one_and_two_camera_cases_match_the_literal_table(
    verdicts: tuple[str, ...], expected: str
) -> None:
    """12 holatning har biri — QO'LDA yozilgan kutilgan qiymat bilan."""
    verdict, _ = aggregate_stall_slot(_pairs(verdicts))

    assert verdict == expected, (
        f"{verdicts} -> {verdict!r}, kutilgani {expected!r} "
        "(ustuvorlik: occupied > uncertain > empty)"
    )


@pytest.mark.parametrize("verdicts", ALL_COMBINATIONS)
def test_every_combination_of_one_to_four_cameras(verdicts: tuple[str, ...]) -> None:
    """1–4 kamera x 3 verdikt: BARCHA 120 kombinatsiya.

    Kutilgan qiymat verdiktlar TO'PLAMIDAN olinadi, ya'ni test bir vaqtda
    ikki narsani o'lchaydi: natijaning to'g'riligini VA uning kirish
    tartibi hamda takrorlanish sonidan MUSTAQILLIGINI.
    """
    expected = EXPECTED_BY_VERDICT_SET[frozenset(verdicts)]

    verdict, _ = aggregate_stall_slot(_pairs(verdicts))

    assert verdict == expected, f"{verdicts} -> {verdict!r}, kutilgani {expected!r}"


def test_the_two_literal_tables_agree() -> None:
    """Ikki qo'lda yozilgan jadval bir-birini tasdiqlaydi.

    Ular UMUMIY 12 holatni qoplaydi. Biri tahrirlanib ikkinchisi
    unutilsa — bu test qizaradi va sabab AYNAN qaysi qatorda ekanini
    ko'rsatadi.
    """
    for verdicts, expected in ONE_AND_TWO_CAMERA_TABLE:
        by_set = EXPECTED_BY_VERDICT_SET[frozenset(verdicts)]
        assert by_set == expected, (
            f"{verdicts}: birinchi jadval {expected!r}, ikkinchisi {by_set!r} deydi"
        )


# ===========================================================================
# `no_coverage` — D-22
# ===========================================================================


def test_no_zone_gives_no_coverage_and_never_empty() -> None:
    """⛔ Bo'sh kirish `no_coverage` beradi — `empty` EMAS (D-22).

    Ikkinchi assert ATAYIN alohida va u AYNAN `empty` ga qarshi yozilgan:
    faqat `== ('no_coverage', 'no_coverage')` bo'lganda kimdir qiymatni
    `empty` ga o'zgartirsa xato xabari «kutilgan qiymat boshqa» deb
    chiqardi va SABAB (o'lchovning yo'qligi yaxshi natijaga aylanmasin)
    ko'rinmasdi.
    """
    result = aggregate_stall_slot([])

    assert result[0] != EMPTY, (
        "qamrovsiz rasta «bo'sh» deb belgilandi — D-22 ning aynan taqiqi: "
        "rasta haqida MA'LUMOT YO'Q degani «rasta bo'sh» degani emas"
    )
    assert result == (NO_COVERAGE, NO_COVERAGE), (
        f"bo'sh kirish {result!r} berdi; verdikt va manba JUFT bo'lishi shart "
        "(`no_coverage_is_paired` konstraytining kod tomondagi jufti)"
    )


def test_an_empty_tuple_and_an_empty_list_agree() -> None:
    """Kirish TIPI natijani o'zgartirmaydi — chaqiruvchi ro'yxat ham, kortej ham beradi."""
    assert aggregate_stall_slot(()) == aggregate_stall_slot([])


# ===========================================================================
# Manba (`resolution_source`) — g'olib zonaniki
# ===========================================================================


def test_a_default_empty_zone_takes_part_as_empty() -> None:
    """`default_empty` zona `empty` sifatida qatnashadi va manbasi SAQLANADI."""
    assert aggregate_stall_slot([(EMPTY, DEFAULT_EMPTY)]) == (EMPTY, DEFAULT_EMPTY)


def test_an_occupied_zone_beats_a_default_empty_one() -> None:
    """Ko'rilmagan zona bilan birga BAND zona bo'lsa — rasta band (D-20).

    ⚠ MANBA HAM O'ZGARADI: g'olib `occupied` zonaning manbai chiqadi,
      ya'ni rasta «ko'rilmagani uchun bo'sh» hisoblagichiga TUSHMAYDI.
    """
    assert aggregate_stall_slot([(EMPTY, DEFAULT_EMPTY), (OCCUPIED, AI)]) == (OCCUPIED, AI)


def test_evidence_beats_the_absence_of_evidence_inside_the_same_verdict() -> None:
    """⚠ Tenglikni ENG KUCHLI DALIL buzadi (`_SOURCE_STRENGTH`).

    Ikkala yo'nalish ham o'lchanadi, ya'ni da'vo kirish TARTIBIDAN
    mustaqil: `default_empty` birinchi kelganda ham, oxirida kelganda ham
    natija bir xil.
    """
    assert aggregate_stall_slot([(EMPTY, DEFAULT_EMPTY), (EMPTY, AI)]) == (EMPTY, AI)
    assert aggregate_stall_slot([(EMPTY, AI), (EMPTY, DEFAULT_EMPTY)]) == (EMPTY, AI)
    assert aggregate_stall_slot([(EMPTY, AI), (EMPTY, HUMAN)]) == (EMPTY, HUMAN)
    assert aggregate_stall_slot([(EMPTY, HUMAN), (EMPTY, DEFAULT_EMPTY)]) == (EMPTY, HUMAN)


def test_default_empty_survives_only_when_no_zone_had_evidence() -> None:
    """«Ko'rilmagani uchun bo'sh» AYNAN nazoratchining yo'qligi hal qilgan holat.

    Bu hisoblagichning MA'NOSI (§C.10): «bu raqam katta bo'lsa nazoratchi
    navbatga ulgurmayapti». Bir kamera ISHONCH bilan bo'sh degan rastani
    ham shu sanoqqa qo'shish raqamni bajarib bo'lmaydigan qilardi.
    """
    assert aggregate_stall_slot([(EMPTY, DEFAULT_EMPTY), (EMPTY, DEFAULT_EMPTY)]) == (
        EMPTY,
        DEFAULT_EMPTY,
    )


def test_the_losing_verdicts_source_is_not_carried() -> None:
    """Manba G'OLIB verdikt ichidan tanlanadi, butun kirishdan EMAS.

    ⚠ NAZORAT HOLATI: `human` bu yerda YUTQAZGAN verdiktda turibdi.
      «Eng kuchli manbani butun kirishdan ol» degan implementatsiya
      `('occupied', 'human')` qaytarardi — ya'ni tizim «nazoratchi bu
      rastani band deb tasdiqladi» deb YOLG'ON gapirardi, holbuki
      nazoratchi aynan BO'SH degan edi.
    """
    assert aggregate_stall_slot([(OCCUPIED, AI), (EMPTY, HUMAN)]) == (OCCUPIED, AI)


# ===========================================================================
# `effective_verdict` — uchala shox
# ===========================================================================


def test_effective_verdict_takes_the_human_answer_when_one_exists() -> None:
    """1-shox: javob bor -> `(review, 'human')`, AI javobidan qat'i nazar."""
    assert effective_verdict(OCCUPIED, EMPTY) == (EMPTY, HUMAN)
    assert effective_verdict(EMPTY, OCCUPIED) == (OCCUPIED, HUMAN)
    assert effective_verdict(UNCERTAIN, OCCUPIED) == (OCCUPIED, HUMAN)


def test_effective_verdict_defaults_an_unreviewed_uncertain_to_empty() -> None:
    """2-shox: tasdiqlanmagan `uncertain` -> `('empty', 'default_empty')` (AI-06).

    ⛔ MANBA `human` EMAS va bu D-19 ning butun mazmuni: `zone_reviews` ga
       soxta qator yozilmagani kabi, hosila ham «nazoratchi tasdiqladi»
       demaydi.
    """
    assert effective_verdict(UNCERTAIN, None) == (EMPTY, DEFAULT_EMPTY)


def test_effective_verdict_passes_the_model_answer_through() -> None:
    """3-shox: javob yo'q va AI ikkilanmagan -> `(event, 'ai')`."""
    assert effective_verdict(OCCUPIED, None) == (OCCUPIED, AI)
    assert effective_verdict(EMPTY, None) == (EMPTY, AI)


def test_a_human_who_cannot_tell_stays_uncertain() -> None:
    """«Aniq ayta olmayman» JIMGINA «bo'sh» ga aylanmaydi.

    Farq o'lchanadigan: `default_empty` — «hech kim qaramadi»,
    `('uncertain', 'human')` — «QARADI va ayta olmadi». Ikkalasini bir
    joyga yig'ish nazoratchining ishini uning yo'qligi bilan
    tenglashtirardi.
    """
    assert effective_verdict(OCCUPIED, UNCERTAIN) == (UNCERTAIN, HUMAN)
    assert effective_verdict(UNCERTAIN, UNCERTAIN) == (UNCERTAIN, HUMAN)


@pytest.mark.parametrize("bad", ["no_coverage", "OCCUPIED", "", "band"])
def test_unknown_verdicts_are_rejected_loudly(bad: str) -> None:
    """Noma'lum verdikt JIMGINA ishlamaydi — `ValueError` beradi.

    ⚠ `no_coverage` ham RAD ETILADI: u ZONA verdikti emas. Zona
      darajasida uni qabul qilish «qamrovsiz zona» degan ifodalab
      bo'lmaydigan holatni qonuniylashtirardi.
    """
    with pytest.raises(ValueError, match="noma'lum"):
        effective_verdict(bad, None)
    with pytest.raises(ValueError, match="noma'lum"):
        aggregate_stall_slot([(bad, AI)])


def test_an_incoherent_pair_is_rejected() -> None:
    """`default_empty` FAQAT `empty` bilan keladi — boshqasi chaqiruvchi nosozligi."""
    with pytest.raises(ValueError, match="default_empty"):
        aggregate_stall_slot([(OCCUPIED, DEFAULT_EMPTY)])


def test_an_unknown_resolution_source_is_rejected() -> None:
    """`no_coverage` manbasi ZONA darajasida ham rad etiladi."""
    with pytest.raises(ValueError, match="noma'lum"):
        aggregate_stall_slot([(EMPTY, NO_COVERAGE)])


# ===========================================================================
# EKSPORT YUZASINING CHEGARASI — 2-daraja agregatsiyasi bu yerda YO'Q
# ===========================================================================


def test_the_export_surface_is_exactly_two_functions() -> None:
    """⛔ `__all__` AYNAN ikki nom — slotlararo agregatsiya EKSPORT QILINMAGAN.

    Ikkinchi daraja («kamida 2 slotda band») — BILL-01, 6-faza. Uni bu
    yerga qo'shish 5-fazani billing qoidasini yozgan holatga tushirardi
    va 6-faza uni ikkinchi marta yozardi.
    """
    assert occupancy_module.__all__ == ("aggregate_stall_slot", "effective_verdict"), (
        f"eksport yuzasi o'zgargan: {occupancy_module.__all__!r}"
    )


def test_the_export_surface_cannot_be_extended_at_runtime() -> None:
    """`__all__` KORTEJ — unga `.append()` bilan nom qo'shib bo'lmaydi.

    Ro'yxat bo'lganda chegarani kengaytirish bir satrlik, ko'rinmas
    o'zgarish bo'lardi.
    """
    assert isinstance(occupancy_module.__all__, tuple)


def test_the_module_has_no_database_dependency() -> None:
    """⛔ `sqlalchemy` MANBA MATNIDA umuman uchramaydi (reja mezoni).

    Modul `sbozor-core` da yashaydi, ya'ni uni `cv-service` ham import
    qila oladi — o'sha image'da esa `sqlalchemy` bo'lsa ham, ORM ga
    bog'langan domen funksiyasi testda haqiqiy baza talab qilardi va
    «jadval testi» degan butun usul yo'qolardi.
    """
    source = Path(occupancy_module.__file__ or "").read_text(encoding="utf-8")

    assert "sqlalchemy" not in source, "domen funksiyasi ORM ga bog'lanib qolgan"
    for forbidden in ("fastapi", "httpx", "taskiq"):
        assert forbidden not in source, f"`{forbidden}` sof domen modulida uchramasligi shart"
