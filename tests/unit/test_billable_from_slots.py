"""Slotlararo hisob sharti — TO'LIQ SANAB CHIQILGAN JADVAL (BILL-01, D-04/D-05, C-6).

=============================================================================
KUTILGAN NATIJA FUNKSIYADAN OLINMAYDI — U LITERAL JADVALDA YOZILGAN.

`billable_from_slots(...)` ni chaqirib natijani «kutilgan» deb saqlash
testni funksiyaning O'Z AKSIGA aylantirardi: qoida qanday buzilsa ham
ikkala tomon birga o'zgarardi va test yashil qolardi
(`test_aggregate_stall_slot.py:1-27` da o'rnatilgan qoida). Shuning uchun
bu faylda IKKI literal manba bor va ularning HECH BIRI mahsulot kodidan
hosil qilinmagan:

  `SLOT_COMBINATION_TABLE` — 1, 2 va 3 slotli holatlar, har biri alohida
                             qatorda, kutilgan `billable` va
                             `no_coverage_only` QO'LDA yozilgan;
  `EXPECTED_BY_SLOT_SET`   — slotlar TO'PLAMI bo'yicha kutilgan qaror
                             (qo'lda yozilgan, mustaqil manba).

⚠ IKKINCHI JADVAL QO'SHIMCHA DA'VO QO'YADI: takrorlanmagan juftliklarda
  natija faqat TO'PLAMGA bog'liq — SLOT TARTIBIGA emas. Da'vo tekin emas:
  usiz «birinchi slot yutadi» yoki «oxirgi slot yutadi» kabi
  implementatsiya butun 1-jadvalda yashil qolishi mumkin edi.

⛔ TAKRORLANGAN JUFTLIKLI QATORLAR 2-JADVALDAN ATAYIN CHIQARILADI.
  `((occupied, ai), (occupied, ai))` va `((occupied, ai),)` ning
  TO'PLAMI bir xil, JAVOBI esa boshqa (D-04 SANOQQA tayanadi). Ya'ni
  to'plam kaliti faqat takrorsiz kombinatsiyalar uchun ma'noli va
  kesishma `test_the_combination_table_covers_every_case` da
  TO'PLAM TENGLIGI bilan qulflangan (D-31: inkor tasdiq emas).
=============================================================================
"""

from __future__ import annotations

import itertools
from typing import Final

import pytest
from sbozor_core.billing import BillableDecision, billable_from_slots

OCCUPIED: Final = "occupied"
EMPTY: Final = "empty"
UNCERTAIN: Final = "uncertain"
NO_COVERAGE: Final = "no_coverage"

AI: Final = "ai"
HUMAN: Final = "human"
DEFAULT_EMPTY: Final = "default_empty"

Slot = tuple[str, str]
Combination = tuple[Slot, ...]


# ===========================================================================
# 1-JADVAL — 1, 2 va 3 slotli holatlar, har biri alohida qatorda
# ===========================================================================

SLOT_COMBINATION_TABLE: Final[tuple[tuple[Combination, bool, bool], ...]] = (
    # --- bitta slot: D-04 bo'yicha AI yolg'iz o'zi YETMAYDI ---
    (((OCCUPIED, AI),), False, False),
    (((OCCUPIED, HUMAN),), True, False),
    (((EMPTY, AI),), False, False),
    (((EMPTY, HUMAN),), False, False),
    (((UNCERTAIN, AI),), False, False),
    (((EMPTY, DEFAULT_EMPTY),), False, False),
    (((NO_COVERAGE, NO_COVERAGE),), False, True),
    (((EMPTY, NO_COVERAGE),), False, True),
    # --- ikki slot ---
    (((OCCUPIED, AI), (OCCUPIED, AI)), True, False),
    # ⛔ C-6 NING O'ZI: nazoratchi BOSHQA slotda «bo'sh» dedi.
    (((OCCUPIED, AI), (EMPTY, HUMAN)), False, False),
    (((OCCUPIED, AI), (OCCUPIED, HUMAN)), True, False),
    (((OCCUPIED, HUMAN), (EMPTY, AI)), True, False),
    (((OCCUPIED, AI), (EMPTY, AI)), False, False),
    (((OCCUPIED, AI), (NO_COVERAGE, NO_COVERAGE)), False, False),
    (((EMPTY, DEFAULT_EMPTY), (EMPTY, DEFAULT_EMPTY)), False, False),
    (((NO_COVERAGE, NO_COVERAGE), (NO_COVERAGE, NO_COVERAGE)), False, True),
    (((EMPTY, NO_COVERAGE), (EMPTY, NO_COVERAGE)), False, True),
    # --- uch slot ---
    (((OCCUPIED, AI), (OCCUPIED, AI), (EMPTY, AI)), True, False),
    (((OCCUPIED, AI), (EMPTY, HUMAN), (EMPTY, HUMAN)), False, False),
    (((OCCUPIED, HUMAN), (NO_COVERAGE, NO_COVERAGE), (EMPTY, AI)), True, False),
    (((UNCERTAIN, AI), (UNCERTAIN, AI), (UNCERTAIN, AI)), False, False),
    (
        (
            (NO_COVERAGE, NO_COVERAGE),
            (NO_COVERAGE, NO_COVERAGE),
            (NO_COVERAGE, NO_COVERAGE),
        ),
        False,
        True,
    ),
)
"""22 holat, QO'LDA yozilgan: `(slotlar, kutilgan billable, kutilgan no_coverage_only)`.

⚠ `((occupied, ai), (empty, human))` VA `((occupied, human), (empty, ai))`
  IKKALASI HAM bor va bu ataylab: ular AYNAN TESKARI javob berishi kerak.
  Faqat bittasini yozish C-6 sabotajini o'tkazib yuborardi — «nazoratchi
  qatnashdi» degan predikat ikkalasida ham `true` bo'lardi.

⚠ `(empty, no_coverage)` JUFTLIGI SXEMADA UCHRAMAYDI (`stall_slot_occupancy`
  ning `CHECK` i juftlikni majburlaydi), lekin funksiya uni RAD ETMASLIGI
  kerak: qamrov savoliga `resolution_source` javob beradi va invariantni
  ikkinchi marta shu yerda majburlash sxemadan ajralib ketardigan nusxa
  bo'lardi (modul docstringida yozilgan).
"""


# ===========================================================================
# 2-JADVAL — slotlar TO'PLAMI bo'yicha (mustaqil manba)
# ===========================================================================

EXPECTED_BY_SLOT_SET: Final[dict[frozenset[Slot], tuple[bool, bool]]] = {
    frozenset({(OCCUPIED, AI)}): (False, False),
    frozenset({(OCCUPIED, HUMAN)}): (True, False),
    frozenset({(EMPTY, AI)}): (False, False),
    frozenset({(EMPTY, HUMAN)}): (False, False),
    frozenset({(UNCERTAIN, AI)}): (False, False),
    frozenset({(EMPTY, DEFAULT_EMPTY)}): (False, False),
    frozenset({(NO_COVERAGE, NO_COVERAGE)}): (False, True),
    frozenset({(EMPTY, NO_COVERAGE)}): (False, True),
    frozenset({(OCCUPIED, AI), (EMPTY, HUMAN)}): (False, False),
    frozenset({(OCCUPIED, AI), (OCCUPIED, HUMAN)}): (True, False),
    frozenset({(OCCUPIED, HUMAN), (EMPTY, AI)}): (True, False),
    frozenset({(OCCUPIED, AI), (EMPTY, AI)}): (False, False),
    frozenset({(OCCUPIED, AI), (NO_COVERAGE, NO_COVERAGE)}): (False, False),
    frozenset({(OCCUPIED, HUMAN), (NO_COVERAGE, NO_COVERAGE), (EMPTY, AI)}): (True, False),
}
"""To'plam -> `(billable, no_coverage_only)`, QO'LDA yozilgan.

`{(occupied, ai), (occupied, human)}` -> `billable` qatori D-04 ning
ikkinchi shoxi: ikkita `occupied` slot BOR, ya'ni birinchi shox ham
yetardi — lekin `{(occupied, human), (empty, ai)}` -> `billable` qatori
FAQAT ikkinchi shox bilan tushuntiriladi va u C-6 ning to'g'ri shakli:
tasdiq AYNAN band slotda.
"""


def _distinct_rows() -> tuple[tuple[Combination, bool, bool], ...]:
    """1-jadvalning takrorsiz juftlikli qatorlari — 2-jadval bilan kesishma."""
    return tuple(row for row in SLOT_COMBINATION_TABLE if len(set(row[0])) == len(row[0]))


# ===========================================================================
# Qamrov qo'riqchisi
# ===========================================================================


def test_the_combination_table_covers_every_case() -> None:
    """NAZORAT: ikkala jadval ham to'liq va ular BIR-BIRINI qoplaydi.

    ⚠ USIZ QUYIDAGI `parametrize` JIMGINA BO'SHAB QOLISHI MUMKIN EDI:
      bo'sh ro'yxatda pytest birorta test yaratmaydi va to'plam
      «hammasi o'tdi» deb tugaydi (`test_aggregate_stall_slot.py:127-133`).
    """
    assert len(SLOT_COMBINATION_TABLE) == 22, (
        f"1-jadvalda {len(SLOT_COMBINATION_TABLE)} qator, 22 kutilgan — "
        "qator jimgina olib tashlangan yoki qo'shilgan"
    )
    assert len({row[0] for row in SLOT_COMBINATION_TABLE}) == len(SLOT_COMBINATION_TABLE), (
        "1-jadvalda takrorlangan kombinatsiya bor"
    )
    assert len(EXPECTED_BY_SLOT_SET) == 14, (
        f"2-jadvalda {len(EXPECTED_BY_SLOT_SET)} kalit, 14 kutilgan"
    )

    # ⛔ TO'PLAM TENGLIGI (D-31), `not in` EMAS: 2-jadvalga hech qachon
    #    tekshirilmaydigan kalit qo'shib qo'yish ham, 1-jadvaldan qatorni
    #    olib tashlab kesishmani kambag'allashtirish ham QIZARADI.
    covered = {frozenset(row[0]) for row in _distinct_rows()}
    assert covered == set(EXPECTED_BY_SLOT_SET), (
        "ikki jadvalning kesishmasi buzildi.\n"
        f"faqat 1-jadvalda: {sorted(map(sorted, covered - set(EXPECTED_BY_SLOT_SET)))}\n"
        f"faqat 2-jadvalda: {sorted(map(sorted, set(EXPECTED_BY_SLOT_SET) - covered))}"
    )


# ===========================================================================
# 1-jadval testi
# ===========================================================================


@pytest.mark.parametrize(
    ("slots", "expected_billable", "expected_no_coverage_only"), SLOT_COMBINATION_TABLE
)
def test_slot_combinations_match_the_literal_table(
    slots: Combination, expected_billable: bool, expected_no_coverage_only: bool
) -> None:
    """22 holatning har biri — QO'LDA yozilgan kutilgan qiymat bilan."""
    decision = billable_from_slots(list(slots))

    assert decision.billable is expected_billable, (
        f"{slots} -> billable={decision.billable}, kutilgani "
        f"{expected_billable} (occupied={decision.occupied_slots}, "
        f"human_confirmed_occupied={decision.human_confirmed_occupied})"
    )
    assert decision.no_coverage_only is expected_no_coverage_only, (
        f"{slots} -> no_coverage_only={decision.no_coverage_only}, kutilgani "
        f"{expected_no_coverage_only} (no_coverage_slots={decision.no_coverage_slots})"
    )
    assert decision.slots == len(slots)


# ===========================================================================
# 2-jadval testi — TARTIBDAN MUSTAQILLIK
# ===========================================================================


@pytest.mark.parametrize("slot_set", list(EXPECTED_BY_SLOT_SET))
def test_the_answer_depends_on_the_slot_set_not_on_the_order(
    slot_set: frozenset[Slot],
) -> None:
    """Takrorsiz juftliklarda javob TARTIBGA bog'liq EMAS.

    Har to'plamning BARCHA o'rin almashtirishlari sinaladi. «Birinchi
    slot yutadi» yoki «oxirgi slot yutadi» sinfidagi implementatsiya
    1-jadvalda yashil qolib, aynan shu yerda qizarardi.
    """
    expected_billable, expected_no_coverage_only = EXPECTED_BY_SLOT_SET[slot_set]

    for permutation in itertools.permutations(sorted(slot_set)):
        decision = billable_from_slots(list(permutation))
        assert decision.billable is expected_billable, (
            f"{permutation} tartibida javob o'zgardi: {decision.billable}"
        )
        assert decision.no_coverage_only is expected_no_coverage_only, (
            f"{permutation} tartibida `no_coverage_only` o'zgardi: {decision.no_coverage_only}"
        )


# ===========================================================================
# ⛔ G-6 — UCH HOLAT, UCHTA NOMLANGAN TEST
# ===========================================================================


def test_two_ai_occupied_slots_are_billable() -> None:
    """G-6 (1): ikki AI-`occupied` -> hisob. D-04 ning BIRINCHI shoxi."""
    decision = billable_from_slots([(OCCUPIED, AI), (OCCUPIED, AI)])
    assert decision.billable is True
    assert decision.occupied_slots == 2
    assert decision.human_confirmed_occupied is False, (
        "nazoratchi qatnashmagan — bu shox INSON tasdig'iga tayanmaydi"
    )


def test_human_empty_on_another_slot_does_not_make_it_billable() -> None:
    """⛔⛔ G-6 (2) / C-6 — SABOTAJ AYNAN SHU TESTNI QIZARTIRISHI KERAK.

    Bitta AI-`occupied` slot BOR, nazoratchi esa BOSHQA slotda «BO'SH»
    degan. `occupancy_repo.py:369` ning `human_confirmed` ustuni bu
    holatda `true` beradi (u `verdict` bilan bog'lanmagan), ya'ni o'sha
    ustunni D-04 predikatiga ulash JIM NOTO'G'RI HISOB yozardi:
    sotuvchi hech kim tasdiqlamagan patta uchun qarzdor bo'lardi (D-02).

    ⛔ TEST NOMI REJADA QATTIQ YOZILGAN — u sabotajning nishoni.
    """
    decision = billable_from_slots([(OCCUPIED, AI), (EMPTY, HUMAN)])

    assert decision.billable is False, (
        "«boshqa slotda nazoratchi BO'SH dedi» holati hisob berdi — C-6 "
        "sabotaji ishladi: predikat `verdict` bilan bog'lanmagan"
    )
    assert decision.occupied_slots == 1
    assert decision.human_confirmed_occupied is False, (
        "`human_confirmed_occupied` `true` bo'ldi — ikki shart ALOHIDA "
        "hisoblangan (`any(verdict==occupied)` va `any(source==human)`), "
        "holbuki ular AYNI slotda bajarilishi shart"
    )


def test_single_human_confirmed_occupied_slot_is_billable() -> None:
    """G-6 (3): bitta `(occupied, human)` -> hisob. D-04 ning IKKINCHI shoxi."""
    decision = billable_from_slots([(OCCUPIED, HUMAN)])
    assert decision.billable is True
    assert decision.occupied_slots == 1
    assert decision.human_confirmed_occupied is True


# ===========================================================================
# D-05 va `no_slot_rows` — IKKI HOLAT, BIR BAYROQQA SIQILMAYDI
# ===========================================================================


def test_no_coverage_only_is_not_the_same_as_no_slot_rows() -> None:
    """⛔ BO'SH KIRISH `no_coverage_only` BERMAYDI — u UCHINCHI holat.

    `slots == 0` degani «bu kunda materializatsiya qilingan qator UMUMAN
    yo'q» (C-3: `stall_slot_occupancy` bugungi kun uchun bo'sh va u
    kechqurun `day_close` da to'ladi). `no_coverage_only` esa «qatorlar
    BOR, lekin hech biri qamramagan».

    Ikkisini bir bayroqqa siqish `billing_close` ni hali yopilmagan kun
    ustida yugurtirganda «hamma rasta qamrovsiz» degan YOLG'ON hisobot
    berardi — ya'ni nosozlik o'lchovga o'xshab ko'rinardi.
    """
    empty_input = billable_from_slots([])
    assert empty_input == BillableDecision(
        slots=0,
        occupied_slots=0,
        human_confirmed_occupied=False,
        no_coverage_slots=0,
        billable=False,
        no_coverage_only=False,
    )

    all_uncovered = billable_from_slots([(NO_COVERAGE, NO_COVERAGE), (NO_COVERAGE, NO_COVERAGE)])
    assert all_uncovered.no_coverage_only is True
    assert all_uncovered.slots == 2
    assert all_uncovered.no_coverage_slots == 2


def test_no_coverage_slots_do_not_count_as_occupied_or_empty() -> None:
    """D-05: qamrovsiz slot NA `occupied` sanog'iga, NA hisobga ta'sir qiladi.

    Ikki AI-`occupied` slotga qancha qamrovsiz slot qo'shilsa ham javob
    O'ZGARMAYDI — ya'ni qamrovsizlik hisobni na yaratadi, na yo'q qiladi.
    """
    base = billable_from_slots([(OCCUPIED, AI), (OCCUPIED, AI)])
    padded = billable_from_slots(
        [
            (OCCUPIED, AI),
            (NO_COVERAGE, NO_COVERAGE),
            (OCCUPIED, AI),
            (NO_COVERAGE, NO_COVERAGE),
        ]
    )

    assert padded.billable is base.billable is True
    assert padded.occupied_slots == base.occupied_slots == 2
    assert padded.no_coverage_slots == 2
    assert padded.no_coverage_only is False, (
        "qamrovsiz slotlar BOR, lekin hammasi emas — bayroq `false` bo'lishi kerak"
    )


# ===========================================================================
# Noma'lum qiymat — JIMGINA ishlamaydi
# ===========================================================================


@pytest.mark.parametrize(
    ("slot", "fragment"),
    [
        ((("busy"), AI), "slot verdikti"),
        ((OCCUPIED, "guess"), "slot manbai"),
    ],
)
def test_unknown_values_are_rejected(slot: Slot, fragment: str) -> None:
    """Noma'lum verdikt/manba `ValueError` beradi (`occupancy.py::_rank` qoidasi).

    Jimgina ishlash eng yomon variant: funksiya shartni tasodifiy hal
    qilib, patta hisobini buzardi va nosozlik faqat nizoda ko'rinardi.
    """
    with pytest.raises(ValueError, match=fragment):
        billable_from_slots([slot])
