"""D-24 ning javobi — TASDIQ, PROZA EMAS (G-13/G-14, BILL-03, UI-SPEC §9.4/§9.6).

=============================================================================
BU FAYL BITTA SAVOLNI JADVALGA AYLANTIRADI:

    «Bitta to'lov bir necha kunlik qarzni yopganda — QAYSI KUNNING
     pattasi to'landi?»

Javob ustunda emas, QOIDADA yashaydi: `FIFO_OLDEST_SERVICE_DATE_FIRST`.
`payments.charge_id` IMKONSIZ (C-4: to'lov paytida hisob hali tug'ilmagan,
C-3; va to'lov↔hisob 1:1 emas), `service_date` esa YOLG'IZ YETARLI EMAS
(`[Qarzni ham olish]` da u BUGUN bo'lib qoladi, to'langan kunlar esa ESKI).

=============================================================================
KUTILGAN NATIJA FUNKSIYADAN OLINMAYDI — U LITERAL JADVALDA YOZILGAN.

Uchta MUSTAQIL jadval, hech biri mahsulot kodidan hosil qilinmagan:

  `FIFO_ALLOCATION_TABLE` — har holat uchun KUTILGAN QATORLAR ro'yxati
                            (kun, rasta, to'langan, yopildimi) —
                            ⛔ KUN KESIMI BO'YICHA, jamlar bo'yicha EMAS;
  `EXPECTED_BY_TOTALS`    — o'sha holatlar uchun `(Σ paid, advance, unpaid)`;
  `QUOTE_SET_TABLE`       — `payment_quote_set()` ning kirish -> chiqish.

⛔⛔ NEGA BIRINCHI JADVAL QATOR DARAJASIDA (05-15 ning S-D DARSI).
    `05-15` da sabotaj SISTEMAGA YETIB BORGAN, lekin test tanlagan
    ma'lumot ikkala shoxda ham BIR XIL natija bergani uchun hech nima
    qizarmagan. Bu yerda aynan o'sha tuzoq bor: LIFO ga o'tkazilganda
    JAMLAR (`Σ paid`, `advance`, `unpaid`) UMUMAN O'ZGARMAYDI — faqat
    QAYSI KUN yopilgani o'zgaradi. Ya'ni `EXPECTED_BY_TOTALS` yolg'iz
    o'zi D-24 ni HECH QACHON o'lchamasdi.
=============================================================================
"""

from __future__ import annotations

from datetime import date
from typing import Final

import pytest
from sbozor_core.billing import (
    ALLOCATION_RULE,
    ChargeDue,
    allocate_charge_credit,
    payment_quote_set,
    total_due_soum,
)

D_2: Final[date] = date(2026, 9, 1)
D_1: Final[date] = date(2026, 9, 2)
D: Final[date] = date(2026, 9, 3)

Charges = tuple[tuple[date, str, int], ...]
ExpectedRows = tuple[tuple[date, str, int, bool], ...]


# ===========================================================================
# (A) FIFO_ALLOCATION_TABLE — KUN KESIMI BO'YICHA, LITERAL
# ===========================================================================

FIFO_ALLOCATION_TABLE: Final[tuple[tuple[str, Charges, int, ExpectedRows], ...]] = (
    (
        "bir to'lov N kunga",
        ((D_2, "12a", 15_000), (D_1, "12a", 15_000), (D, "12a", 15_000)),
        45_000,
        (
            (D_2, "12a", 15_000, True),
            (D_1, "12a", 15_000, True),
            (D, "12a", 15_000, True),
        ),
    ),
    (
        "qisman — N kun ustida",
        ((D_2, "12a", 15_000), (D_1, "12a", 15_000), (D, "12a", 15_000)),
        20_000,
        (
            (D_2, "12a", 15_000, True),
            (D_1, "12a", 5_000, False),
            (D, "12a", 0, False),
        ),
    ),
    (
        "qisman — bir kun",
        ((D, "12a", 15_000),),
        7_000,
        ((D, "12a", 7_000, False),),
    ),
    (
        "faqat shu kun",
        ((D, "12a", 15_000),),
        15_000,
        ((D, "12a", 15_000, True),),
    ),
    (
        "avans",
        ((D, "12a", 15_000),),
        20_000,
        ((D, "12a", 15_000, True),),
    ),
    (
        "storno netlashadi",
        ((D_1, "12a", 15_000), (D, "12a", 15_000)),
        15_000 - 15_000,
        ((D_1, "12a", 0, False), (D, "12a", 0, False)),
    ),
    (
        "bir kunda ikki rasta — tenglik uzilishi",
        ((D, "12a", 10_000), (D, "3b", 10_000)),
        10_000,
        ((D, "12a", 10_000, True), (D, "3b", 0, False)),
    ),
    (
        "tuzatish `due` ni oshirdi",
        ((D, "12a", 20_000),),
        15_000,
        ((D, "12a", 15_000, False),),
    ),
    (
        "nol kredit",
        ((D, "12a", 15_000),),
        0,
        ((D, "12a", 0, False),),
    ),
    (
        "bo'sh hisoblar",
        (),
        15_000,
        (),
    ),
    (
        "manfiy kredit",
        ((D, "12a", 15_000),),
        -5_000,
        ((D, "12a", 0, False),),
    ),
)
"""O'n bir holat, har biri QO'LDA yozilgan KUTILGAN QATORLAR bilan.

⚠ «storno netlashadi» qatorida kredit ATAYIN `15_000 - 15_000` shaklida
  yozilgan, `0` deb emas: `payments` append-only va storno O'Z QATORI
  bo'ladi (D-23), ya'ni kredit `CASE WHEN kind = 'reversal' THEN
  -amount_soum ELSE amount_soum END` yig'indisi. Ifoda shaklda qolsa
  jadvalni o'qigan odam netlashning QAYERDA bo'lishini ham ko'radi.

⚠ «manfiy kredit» BO'LMASLIGI KERAK bo'lgan holat (storno hech qachon
  to'lovdan ko'p bo'lmaydi), lekin funksiya undan YIQILMAYDI: `max(credit,
  0)` uni nolga tenglashtiradi. Yiqilish bu yerda yomonroq bo'lardi —
  bitta buzuq qator butun qarzdorlik hisobotini o'chirardi.
"""


# ===========================================================================
# (B) EXPECTED_BY_TOTALS — IKKINCHI, MUSTAQIL JADVAL
# ===========================================================================

EXPECTED_BY_TOTALS: Final[dict[str, tuple[int, int, int]]] = {
    # holat -> (Σ paid, advance_soum, unpaid_soum)
    "bir to'lov N kunga": (45_000, 0, 0),
    "qisman — N kun ustida": (20_000, 0, 25_000),
    "qisman — bir kun": (7_000, 0, 8_000),
    "faqat shu kun": (15_000, 0, 0),
    "avans": (15_000, 5_000, 0),
    "storno netlashadi": (0, 0, 30_000),
    "bir kunda ikki rasta — tenglik uzilishi": (10_000, 0, 10_000),
    "tuzatish `due` ni oshirdi": (15_000, 0, 5_000),
    "nol kredit": (0, 0, 15_000),
    "bo'sh hisoblar": (0, 15_000, 0),
    "manfiy kredit": (0, 0, 15_000),
}
"""Jamlar — QO'LDA yozilgan, `FIFO_ALLOCATION_TABLE` dan HOSILA EMAS.

⛔ G-14 SHU YERDA ARIFMETIK KO'RINADI: `unpaid_soum` ustuni HAR QATORDA
`max(Σ due − max(credit, 0), 0)` ga teng, ya'ni u `vendor_outstanding()`
(BILL-03) hisoblaydigan son BILAN BIR XIL. Hosila taqsimlash
hisoblanadigan qoldiqdan AJRALIB KETA OLMAYDI — ekrandagi qarz bilan
hisobotdagi qarz bir kun farq qilib qolmaydi.

⚠ BU JADVAL YOLG'IZ O'ZI D-24 NI O'LCHAMAYDI (fayl docstringi): LIFO
  sabotajida uchala son ham O'ZGARMAYDI. U faqat 1-jadvalning JUFTI.
"""


# ===========================================================================
# (C) QUOTE_SET_TABLE — `payment_quote_set()` (UI-SPEC §9.4/§9.6)
# ===========================================================================

QUOTE_SET_TABLE: Final[tuple[tuple[int | None, int, tuple[int, ...]], ...]] = (
    # (today_soum, outstanding_soum, kutilgan to'plam — USTUVORLIK tartibida)
    (15_000, 0, (15_000,)),
    (15_000, 45_000, (15_000, 45_000, 60_000)),
    (15_000, 15_000, (15_000, 30_000)),
    (None, 45_000, (45_000,)),
    (None, 0, ()),
    (None, -5_000, ()),
    (15_000, -5_000, (15_000, 10_000)),
    (15_000, -20_000, (15_000,)),
    (0, 45_000, (45_000,)),
)
"""To'qqiz holat, QO'LDA yozilgan.

⛔ `(None, 45_000) -> (45_000,)` — G-15 NING O'ZI: «summa yo'q» qarzni
   undirilmaydigan QILMAYDI. Yopiq kunda (`market_closed`) yoki tarifi
   belgilanmagan rastada (`tariff_missing`) bugungi patta yo'q, LEKIN
   eski qarz baribir olinadi (UI-SPEC §9.4 ning «Faqat `outstanding_soum`»
   ustuni). Eski shart (`amount_soum is None` -> 422) qaytarilsa shu
   qator qizaradi.

⛔ `(None, 0) -> ()` — 06-09 ning YAGONA 422 yo'li. Shart bo'sh
   TO'PLAM, «bugungi summa yo'q» EMAS.

⛔ `(15_000, 45_000) -> (15_000, 45_000, 60_000)` — tartib USTUVORLIK
   bo'yicha va u tasodifan o'sish tartibiga mos tushadi; `(15_000,
   -5_000) -> (15_000, 10_000)` esa numerik saralash BILAN MOS TUSHMAYDI
   (10 000 < 15 000), ya'ni `sorted()` ga o'tkazish AYNAN shu qatorni
   qizartiradi.

⚠ `(15_000, 15_000) -> (15_000, 30_000)` — dublikat emas, ikki bir xil
  qiymat: (1) va (2) TENG, shuning uchun (2) tushib qoladi, (3) esa
  qoladi. `(15_000, 0)` da esa (1) va (3) teng bo'ladi.
"""


def _charges(rows: Charges) -> list[ChargeDue]:
    return [
        ChargeDue(service_date=service_date, stall_code=stall_code, due_soum=due)
        for service_date, stall_code, due in rows
    ]


# ===========================================================================
# (D) QAMROV QO'RIQCHILARI — uchala jadval uchun
# ===========================================================================

REQUIRED_ALLOCATION_CASES: Final[frozenset[str]] = frozenset(
    {
        "bir to'lov N kunga",
        "qisman — N kun ustida",
        "qisman — bir kun",
        "faqat shu kun",
        "avans",
        "storno netlashadi",
        "bir kunda ikki rasta — tenglik uzilishi",
        "tuzatish `due` ni oshirdi",
        "nol kredit",
        "bo'sh hisoblar",
        "manfiy kredit",
    }
)
"""Reja TALAB QILGAN holatlar — jadvaldan MUSTAQIL, ikkinchi manba.

⛔ TO'PLAM TENGLIGI (D-31) bilan solishtiriladi: qator jimgina olib
tashlansa ham, «vaqtincha» qo'shilgan nomsiz holat ham QIZARADI.
"""


def test_the_fifo_allocation_table_covers_every_case() -> None:
    """NAZORAT: 1-jadval to'liq va reja talab qilgan HAR holat bor.

    ⚠ USIZ `parametrize` JIMGINA BO'SHAB QOLARDI
      (`test_aggregate_stall_slot.py:127-133`).
    """
    names = [row[0] for row in FIFO_ALLOCATION_TABLE]
    assert len(names) == len(set(names)), f"takrorlangan holat nomi: {names}"
    assert len(FIFO_ALLOCATION_TABLE) >= 9, (
        f"{len(FIFO_ALLOCATION_TABLE)} holat — reja quyi chegarasi 9"
    )
    assert set(names) == REQUIRED_ALLOCATION_CASES, (
        f"jadvalda ortiqcha: {sorted(set(names) - REQUIRED_ALLOCATION_CASES)}; "
        f"yetishmayapti: {sorted(REQUIRED_ALLOCATION_CASES - set(names))}"
    )


def test_the_totals_table_covers_every_case() -> None:
    """NAZORAT: 2-jadval 1-jadvalning HAR holatiga javob beradi (to'plam tengligi)."""
    names = {row[0] for row in FIFO_ALLOCATION_TABLE}
    assert set(EXPECTED_BY_TOTALS) == names, (
        f"faqat jamlar jadvalida: {sorted(set(EXPECTED_BY_TOTALS) - names)}; "
        f"faqat qatorlar jadvalida: {sorted(names - set(EXPECTED_BY_TOTALS))}"
    )


def test_the_quote_set_table_covers_every_case() -> None:
    """NAZORAT: 3-jadval to'liq va uchala nozik shox ham vakillangan."""
    assert len(QUOTE_SET_TABLE) >= 7, f"{len(QUOTE_SET_TABLE)} holat — quyi chegara 7"

    inputs = [(row[0], row[1]) for row in QUOTE_SET_TABLE]
    assert len(inputs) == len(set(inputs)), f"takrorlangan kirish: {inputs}"

    assert any(row[0] is None and row[1] > 0 for row in QUOTE_SET_TABLE), (
        "«summa yo'q + qarz bor» holati yo'q — G-15 o'lchanmasdi"
    )
    assert any(row[2] == () for row in QUOTE_SET_TABLE), (
        "bo'sh to'plam holati yo'q — 06-09 ning yagona 422 yo'li sinalmasdi"
    )
    assert any(row[1] < 0 for row in QUOTE_SET_TABLE), (
        "manfiy qoldiq (avans) holati yo'q — OQ-4/A4 sinalmasdi"
    )


# ===========================================================================
# 1-JADVAL TESTI — ⛔ KUN KESIMI QATORLAR BO'YICHA
# ===========================================================================


@pytest.mark.parametrize(
    ("case", "charges", "credit", "expected_rows"),
    FIFO_ALLOCATION_TABLE,
    ids=[row[0] for row in FIFO_ALLOCATION_TABLE],
)
def test_allocation_rows_match_the_literal_table(
    case: str, charges: Charges, credit: int, expected_rows: ExpectedRows
) -> None:
    """Har holatning HAR QATORI — QO'LDA yozilgan kutilgan qiymat bilan.

    Solishtiruv `(kun, rasta, to'langan, yopildimi)` KORTEJLARI RO'YXATI
    bo'yicha, ya'ni TARTIB HAM DA'VO. Faqat jamlarni tekshirish LIFO
    sabotajini o'tkazib yuborardi (fayl docstringi).
    """
    allocation = allocate_charge_credit(_charges(charges), credit)

    actual = tuple(
        (row.service_date, row.stall_code, row.paid_soum, row.settled) for row in allocation.rows
    )
    assert actual == expected_rows, f"«{case}»: qatorlar mos kelmadi"
    assert allocation.rule == ALLOCATION_RULE, (
        f"«{case}»: natija qoidaning NOMINI qaytarmadi ({allocation.rule!r})"
    )


@pytest.mark.parametrize(
    ("case", "charges", "credit", "expected_rows"),
    FIFO_ALLOCATION_TABLE,
    ids=[row[0] for row in FIFO_ALLOCATION_TABLE],
)
def test_the_two_invariants_hold_for_every_row(
    case: str, charges: Charges, credit: int, expected_rows: ExpectedRows
) -> None:
    """⛔ (a) kredit yo'qolmaydi · (b) qoldiq `vendor_outstanding()` bilan BIR XIL.

    Invariantlar funksiyaning O'ZIDA ham `assert` bilan majburlangan;
    bu yerda ular MUSTAQIL hisoblanadi — ya'ni ikkala tomon ham bir
    vaqtda buzilishi kerak bo'ladi (funksiya ichidagi assert yolg'iz
    o'zi «o'zini tekshirish» bo'lardi).
    """
    allocation = allocate_charge_credit(_charges(charges), credit)
    credit_applied = max(credit, 0)
    total_due = sum(due for _, _, due in charges)
    paid_total = sum(row.paid_soum for row in allocation.rows)

    assert paid_total + allocation.advance_soum == credit_applied, f"«{case}»: kredit yo'qoldi"
    assert allocation.unpaid_soum == max(total_due - credit_applied, 0), (
        f"«{case}»: hosila taqsimlash hisoblanadigan qoldiqdan ajralib ketdi"
    )
    assert len(allocation.rows) == len(expected_rows)


# ===========================================================================
# 2-JADVAL TESTI — JAMLAR (mustaqil manba)
# ===========================================================================


@pytest.mark.parametrize(
    ("case", "charges", "credit", "expected_rows"),
    FIFO_ALLOCATION_TABLE,
    ids=[row[0] for row in FIFO_ALLOCATION_TABLE],
)
def test_totals_match_the_second_literal_table(
    case: str, charges: Charges, credit: int, expected_rows: ExpectedRows
) -> None:
    """Ikki jadval BIR-BIRINI tekshiradi: qatorlar yig'indisi jamlarga teng."""
    expected_paid, expected_advance, expected_unpaid = EXPECTED_BY_TOTALS[case]
    allocation = allocate_charge_credit(_charges(charges), credit)

    assert sum(row.paid_soum for row in allocation.rows) == expected_paid, f"«{case}»: Σ paid"
    assert allocation.advance_soum == expected_advance, f"«{case}»: advance"
    assert allocation.unpaid_soum == expected_unpaid, f"«{case}»: unpaid"

    # Uchinchi bog'lanish: 1-jadvalning literal qatorlari ham SHU jamni beradi.
    assert sum(paid for _, _, paid, _ in expected_rows) == expected_paid, (
        f"«{case}»: ikki LITERAL jadval bir-biriga zid — qatorlardagi "
        "to'langan summalar yig'indisi jamlar jadvaliga mos emas"
    )


# ===========================================================================
# ⛔ D-24 NING ASOSIY DA'VOSI — «QAYSI KUNNING PATTASI TO'LANDI?»
# ===========================================================================


def test_one_payment_settles_the_oldest_days_first() -> None:
    """⛔ Uch kunlik qarz + BITTA 45 000 to'lov -> yopilgan kunlar AYNAN `[D-2, D-1, D]`.

    ⛔ RO'YXAT, TO'PLAM EMAS: tartib ham da'vo. `set(...)` bilan
       solishtirish LIFO sabotajini o'tkazib yuborardi — uchala kun ham
       yopilgani uchun to'plam BIR XIL bo'lardi.
    """
    charges = _charges(((D_2, "12a", 15_000), (D_1, "12a", 15_000), (D, "12a", 15_000)))
    allocation = allocate_charge_credit(charges, 45_000)

    settled_days = [row.service_date for row in allocation.rows if row.settled]
    assert settled_days == [D_2, D_1, D], (
        f"yopilgan kunlar tartibi: {settled_days}. Kutilgani `[D-2, D-1, D]` — "
        f"{ALLOCATION_RULE} eng QADIMGI kundan boshlaydi."
    )


def test_a_partial_payment_names_the_day_it_stopped_at() -> None:
    """⛔ Qisman to'lov: `D-2` yopildi, `D-1` YARIM, `D` UMUMAN tegilmadi.

    Bu holat LIFO sabotajining IKKINCHI nishoni: jamlar (`20 000` / `0` /
    `25 000`) ikkala tartibda ham BIR XIL, faqat QAYSI KUN yarim to'langani
    o'zgaradi.
    """
    charges = _charges(((D_2, "12a", 15_000), (D_1, "12a", 15_000), (D, "12a", 15_000)))
    allocation = allocate_charge_credit(charges, 20_000)

    by_day = {row.service_date: row for row in allocation.rows}
    assert by_day[D_2].settled is True, "eng qadimgi kun yopilmadi"
    assert by_day[D_1].paid_soum == 5_000, f"`D-1` ga {by_day[D_1].paid_soum} tushdi, 5000 kutilgan"
    assert by_day[D_1].settled is False
    assert by_day[D].paid_soum == 0, f"`D` ga {by_day[D].paid_soum} tushdi, 0 kutilgan"


def test_the_tie_break_is_deterministic_and_input_order_does_not_matter() -> None:
    """⛔ Bir kunda ikki rasta: `12a` yopiladi va KIRISH TARTIBI natijaga TA'SIR QILMAYDI.

    Tenglik `stall_code` bo'yicha uziladi. Determinizm nizoda DALIL
    QIYMATINING sharti (D-02): SQL `ORDER BY` siz qatorlarni ixtiyoriy
    tartibda qaytaradi, ya'ni tartibga tayangan implementatsiya AYNI
    kirish uchun ikki xil javob berardi.
    """
    forward = allocate_charge_credit(_charges(((D, "12a", 10_000), (D, "3b", 10_000))), 10_000)
    reversed_input = allocate_charge_credit(
        _charges(((D, "3b", 10_000), (D, "12a", 10_000))), 10_000
    )

    settled = [row.stall_code for row in forward.rows if row.settled]
    assert settled == ["12a"], f"to'langan rasta: {settled}, kutilgani `['12a']`"

    assert forward == reversed_input, (
        "kirish tartibi teskari berilganda natija O'ZGARDI — tenglik "
        "uzilishi determinlashtirilmagan"
    )


def test_the_rule_name_is_stable() -> None:
    """Qoida NOMI konstanta va u natijada qaytariladi.

    Hisobotlar va keyingi fazalar qoidaga NOM BILAN murojaat qiladi;
    nomni jimgina o'zgartirish ularni ham o'zgartirishga majbur qiladi.
    """
    assert ALLOCATION_RULE == "FIFO_OLDEST_SERVICE_DATE_FIRST"
    assert allocate_charge_credit([], 0).rule == ALLOCATION_RULE


# ===========================================================================
# 3-JADVAL TESTI — `payment_quote_set()` va `total_due_soum()`
# ===========================================================================


@pytest.mark.parametrize(("today", "outstanding", "expected"), QUOTE_SET_TABLE)
def test_quote_set_matches_the_literal_table(
    today: int | None, outstanding: int, expected: tuple[int, ...]
) -> None:
    """Har holat — QO'LDA yozilgan kutilgan KORTEJ bilan (tartib ham da'vo)."""
    assert payment_quote_set(today, outstanding) == expected


def test_quote_set_is_ordered_by_priority_not_by_value() -> None:
    """⛔ Tartib USTUVORLIK bo'yicha — `sorted()` ga o'tkazish QIZARADI.

    `(15 000, -5 000)` da uchinchi taklif (10 000) IKKINCHI o'rinda
    turadi, holbuki u birinchisidan KICHIK. Numerik saralash uni oldinga
    surib, kassirga «avans hisobga olingan jami» ni STANDART tanlov qilib
    ko'rsatardi — UI-SPEC §9.6 esa standart tanlov BUGUNGI PATTA
    bo'lishini talab qiladi.
    """
    quotes = payment_quote_set(15_000, -5_000)
    assert quotes == (15_000, 10_000)
    assert quotes != tuple(sorted(quotes)), "to'plam numerik saralangan — ustuvorlik yo'qolgan"


def test_empty_quote_set_is_the_only_full_rejection_path() -> None:
    """⛔ Bo'sh to'plam MA'NOLI: «bugun asoslangan to'lov yo'q» (06-09 -> 422)."""
    assert payment_quote_set(None, 0) == ()
    assert payment_quote_set(None, -5_000) == ()
    assert payment_quote_set(0, 0) == ()


def test_closed_day_still_collects_the_debt() -> None:
    """⛔ G-15: «summa yo'q» qarzni undirilmaydigan QILMAYDI (UI-SPEC §9.4).

    `market_closed` va `tariff_missing` — ikkalasi ham `today_soum is
    None` bo'lib keladi. Eski shart (`amount_soum is None` -> 422)
    qaytarilsa bu test qizaradi.
    """
    assert payment_quote_set(None, 45_000) == (45_000,)
    assert total_due_soum(None, 45_000) == 45_000


@pytest.mark.parametrize(
    ("today", "outstanding", "expected"),
    [
        (15_000, 0, 15_000),
        (15_000, 45_000, 60_000),
        (None, 45_000, 45_000),
        (None, 0, 0),
        (15_000, -5_000, 10_000),
        (15_000, -20_000, -5_000),
        (0, 0, 0),
    ],
)
def test_total_due_soum_is_the_single_addition(
    today: int | None, outstanding: int, expected: int
) -> None:
    """⛔ SERVERDAGI YAGONA QO'SHISH AMALI (D-16/D-20, UI-SPEC §9.6).

    `pending_projection()` (06-06) va `POST /payments` (06-09) IKKALASI
    ham shu funksiyani chaqiradi. Natija MANFIY ham bo'lishi mumkin
    (avans qarzdan katta) va u istisno KO'TARMAYDI — proyeksiya bu
    holatni `Badge tone="success"` «Avans» bilan ko'rsatadi.
    """
    assert total_due_soum(today, outstanding) == expected


@pytest.mark.parametrize(
    ("today", "outstanding"),
    [(-1, 0), (15_000.5, 0), (True, 0), (15_000, 1.5), (15_000, True)],
)
def test_money_type_rules_are_enforced(today: object, outstanding: object) -> None:
    """D-11: manfiy `today_soum`, kasrli va mantiqiy tiplar RAD ETILADI.

    ⚠ `outstanding_soum` MANFIY bo'lishi mumkin (avans), `today_soum`
      esa YO'Q: u tarif summasi va manfiy tarif ma'noga ega emas.
      Assimetriya ATAYIN va u shu yerda o'lchanadi.
    """
    with pytest.raises((TypeError, ValueError)):
        total_due_soum(today, outstanding)  # type: ignore[arg-type]


def test_negative_due_is_rejected() -> None:
    """Manfiy `due_soum` — chaqiruvchining nosozligi, taqsimlashning savoli emas.

    Hisobdan KATTA `decrease` yozilishi D-07 ning o'z savoli
    (`charge_adjustments` qoidasi); bu funksiya uni jimgina nolga
    aylantirib, qarzdorlik hisobotini buzmasligi kerak.
    """
    with pytest.raises(ValueError, match="manfiy"):
        allocate_charge_credit([ChargeDue(service_date=D, stall_code="12a", due_soum=-1)], 0)
