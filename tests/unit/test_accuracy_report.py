"""Aniqlik hisoboti — KUTILGAN QIYMATLAR QO'LDA HISOBLANGAN VA LITERAL.

=============================================================================
BU FAYL FORMULANI TAKRORLAMAYDI (`test_money.py` uslubi).

Har bir nazorat qiymati QO'LDA hisoblangan va hisobning O'ZI test
docstringida turadi. Formulani testda qayta yozish testni kodning
aks-sadosiga aylantirardi: ikkalasi birga xato bo'lganda natija yashil
qolardi.

⚠ NAZORAT QIYMATLARINING ENG QIMMATI — UI-SPEC §11.1 DAGI ISHLANGAN
  MISOL (tp=401, fp=23, fn=38, tn=150). U spetsifikatsiyada foizlari
  bilan birga yozilgan, ya'ni u MUSTAQIL manba: kod ham, test ham undan
  chiqmaydi, ikkalasi ham unga QARSHI o'lchanadi. Aynan shu misol ikki
  xato nisbatining MAXRAJINI ham qulflaydi.

⚠ TOLERANS AYNAN `1e-3` — `frontend/src/lib/wilson.test.tsx` bilan bir
  xil son va bir xil sabab: `pytest.approx(x, abs=5e-4)` (ya'ni uch
  xonaga «yaxlitlash») qo'lda yozilgan `0,825` ni YIQITARDI (haqiqiy
  qiymat 0,825633, farq 6,3e-4) va keyingi ijrochi «literalni aniqroq
  yozib qo'yaman» deb o'lchovni yashirardi.
=============================================================================
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Final

import pytest
from app.services.accuracy_report import (
    MIN_SAMPLE_FOR_PERCENT,
    Z_95,
    AccuracyRow,
    ConfusionMatrix,
    accuracy_lower_wilson_bound,
    accuracy_report,
    confusion_matrix,
    is_fast_decision,
    wilson_interval,
)

TOLERANCE: Final = 1e-3

OCCUPIED: Final = "occupied"
EMPTY: Final = "empty"
UNCERTAIN: Final = "uncertain"
EVAL: Final = "eval"
TRAIN: Final = "train"
BLIND: Final = "blind_audit"
UNCERTAIN_QUEUE: Final = "uncertain"

REPO_ROOT: Final = Path(__file__).resolve().parents[2]
WILSON_TS: Final = REPO_ROOT / "frontend" / "src" / "lib" / "wilson.ts"


def near(actual: float | None, expected: float) -> None:
    assert actual is not None, "qiymat `None` — o'lchov umuman qaytmadi"
    assert abs(actual - expected) <= TOLERANCE, f"{actual} != {expected} (tolerans {TOLERANCE})"


def rows(
    *,
    tp: int = 0,
    fp: int = 0,
    fn: int = 0,
    tn: int = 0,
    purpose: str = EVAL,
    queue_kind: str = BLIND,
) -> list[AccuracyRow]:
    """Matritsaning to'rt katagini TO'G'RIDAN-TO'G'RI beradigan qatorlar.

    ⚠ Yordamchi VERDIKT juftliklarini yozadi, matritsani EMAS: agar u
      `ConfusionMatrix` ni qursa, test `confusion_matrix()` ni umuman
      chetlab o'tardi va uning xatosini KO'RMASDI.
    """
    made: list[AccuracyRow] = []
    for system, human, count in (
        (OCCUPIED, OCCUPIED, tp),
        (OCCUPIED, EMPTY, fp),
        (EMPTY, OCCUPIED, fn),
        (EMPTY, EMPTY, tn),
    ):
        made.extend(
            AccuracyRow(
                purpose=purpose,
                queue_kind=queue_kind,
                system_verdict=system,
                human_verdict=human,
            )
            for _ in range(count)
        )
    return made


# ===========================================================================
# 1. WILSON — QO'LDA HISOBLANGAN NAZORAT
# ===========================================================================


def test_wilson_matches_hand_computed() -> None:
    """`wilson_interval(90, 100)` -> 0,825 / 0,945.

    QO'LDA HISOB (z = 1,96; z² = 3,8416):
        maxraj = 1 + z²/n = 1 + 0,038416           = 1,038416
        markaz = (0,9 + 0,019208) / 1,038416       = 0,885202
        ildiz  = √(0,9·0,1/100 + 3,8416/40000)
               = √(0,0009 + 0,00009604) = √0,00099604 = 0,0315601
        yarim  = 1,96 · 0,0315601 / 1,038416       = 0,0595694
        quyi   = 0,885202 − 0,059569               = 0,825633
        yuqori = 0,885202 + 0,059569               = 0,944771
    """
    result = wilson_interval(90, 100)

    near(result.point, 0.9)
    near(result.lower, 0.825)
    near(result.upper, 0.945)


def test_the_two_wilson_implementations_agree_on_the_same_literal() -> None:
    """⚠ SERVER VA EKRAN AYNAN BIR XIL NAZORAT QIYMATIGA qarshi o'lchanadi.

    `frontend/src/lib/wilson.test.tsx` da `wilsonInterval(90, 100)`
    uchun `0.825` va `0.945` LITERAL yozilgan. Bu yerda ham AYNAN
    o'shalar. Ikki tomon bir xil formulani yozgani import bilan
    isbotlanmaydi (ular ikki xil tilda), lekin bir xil NAZORAT QIYMATIGA
    yaqinlashishi ularni bir gapga bog'laydi.

    ⛔ TS FAYLI O'QILADI VA UNDAGI LITERAL QIDIRILADI: qo'shni tilda
       qiymat o'zgartirilsa bu test qizaradi va ajralish JIMGINA sodir
       bo'lmaydi.
    """
    ts_test = (WILSON_TS.parent / "wilson.test.tsx").read_text(encoding="utf-8")

    assert "expectNear(result.lower, 0.825);" in ts_test, (
        "klient tomondagi nazorat qiymati o'zgargan — ikki implementatsiya ajralib ketdi"
    )
    assert "expectNear(result.upper, 0.945);" in ts_test


def test_the_shared_constants_match_the_client() -> None:
    """`Z_95` va `MIN_SAMPLE_FOR_PERCENT` — ikkala tilda BIR XIL son.

    ⛔ IKKALASI HAM MANBA MATNIDAN o'qiladi (§S-10): import mumkin emas,
       ya'ni yagona mexanik bog' — matn. Chegara ajralganda server foiz
       qaytarib, ekran uni chizmasdi va nosozlik «ma'lumot yo'q»
       ko'rinishida bo'lardi.
    """
    source = WILSON_TS.read_text(encoding="utf-8")

    z_match = re.search(r"^const Z_95 = ([0-9.]+);", source, re.MULTILINE)
    min_match = re.search(r"^export const MIN_SAMPLE_FOR_PERCENT = (\d+);", source, re.MULTILINE)

    assert z_match is not None, "`wilson.ts` da `Z_95` topilmadi — bog' uzilgan"
    assert min_match is not None, "`wilson.ts` da `MIN_SAMPLE_FOR_PERCENT` topilmadi"
    assert float(z_match.group(1)) == Z_95
    assert int(min_match.group(1)) == MIN_SAMPLE_FOR_PERCENT


def test_an_empty_sample_has_no_interval_rather_than_a_zero_one() -> None:
    """`n = 0` -> uchala maydon `None`, `0.0` EMAS.

    Nol oraliq «o'lchadim va nol chiqdi» degani bo'lardi; `None` esa
    «o'lchov umuman bo'lmadi».
    """
    result = wilson_interval(0, 0)

    assert (result.point, result.lower, result.upper) == (None, None, None)


def test_a_perfect_score_still_has_width() -> None:
    """`p = 1` da ham oraliq KENGLIKKA ega — «100 % (100–100)» imkonsiz."""
    result = wilson_interval(25, 25)

    assert result.point == 1.0
    assert result.upper == 1.0
    assert result.lower is not None
    assert result.lower < 1.0, "mukammal natijada oraliq nuqtaga siqilib qoldi"


def test_more_successes_than_trials_is_rejected() -> None:
    """⛔ JIMGINA TO'G'RILANMAYDI: qisish «aniqlik 100 %» hisobotini chiqarardi."""
    with pytest.raises(ValueError, match="katta bo'lolmaydi"):
        wilson_interval(11, 10)


@pytest.mark.parametrize("bad", [-1, True])
def test_non_counts_are_rejected(bad: int) -> None:
    """`bool` ALOHIDA rad etiladi — `isinstance(True, int)` rost."""
    with pytest.raises(ValueError, match="BUTUN son"):
        wilson_interval(bad, 10)


def test_the_golden_gate_bound_refuses_an_empty_sample() -> None:
    """Oltin darvoza uchun bo'sh namunada `0.0` QAYTARILMAYDI.

    `0.0` «aniqlik nol» degan O'LCHANGAN da'vo bo'lardi va darvoza
    o'sha yolg'on bilan YIQILARDI — sabab esa ma'lumotning yo'qligi
    bo'lardi.
    """
    near(accuracy_lower_wilson_bound(90, 100), 0.825)

    with pytest.raises(ValueError, match="quyi chegara YO'Q"):
        accuracy_lower_wilson_bound(0, 0)


# ===========================================================================
# 2. MATRITSA — UI-SPEC NING ISHLANGAN MISOLI
# ===========================================================================


def test_matrix_matches_hand_computed() -> None:
    """To'rt katak — kirish juftliklaridan QO'LDA sanalgan.

    Kirish: 2 x (band, band), 1 x (band, bo'sh), 3 x (bo'sh, band),
            4 x (bo'sh, bo'sh)  ->  tp=2, fp=1, fn=3, tn=4, n=10
    """
    matrix = confusion_matrix(
        [
            (OCCUPIED, OCCUPIED),
            (OCCUPIED, OCCUPIED),
            (OCCUPIED, EMPTY),
            (EMPTY, OCCUPIED),
            (EMPTY, OCCUPIED),
            (EMPTY, OCCUPIED),
            (EMPTY, EMPTY),
            (EMPTY, EMPTY),
            (EMPTY, EMPTY),
            (EMPTY, EMPTY),
        ]
    )

    assert matrix == ConfusionMatrix(tp=2, fp=1, fn=3, tn=4)
    assert matrix.n == 10


def test_matrix_matches_the_ui_spec_worked_example() -> None:
    """⚠⚠ SPETSIFIKATSIYANING O'Z MISOLI — MUSTAQIL NAZORAT MANBAI.

    UI-SPEC §11.1: tp=401, fp=23, fn=38, tn=150 (n=612) va u yerda
    foizlari ham yozilgan:

        To'g'ri:        90,0 %  (87,4 – 92,2)   -> (401+150)/612
        Band deb xato:   5,4 %  (3,6 – 8,0)     -> 23 / (401+23)   = 23/424
        Bo'sh deb xato:  8,7 %  (6,4 – 11,7)    -> 38 / (401+38)   = 38/439
        Bazaviy ulush:  71,7 %                  -> (401+38)/612

    ⛔ AYNAN SHU TEST IKKI XATONING MAXRAJINI QULFLAYDI. Ikkala nisbat
       ham `n = 612` ga bo'linsa 3,8 % va 6,2 % chiqardi — ya'ni
       spetsifikatsiyaning sonlaridan FARQ QILARDI, lekin hech qanday
       xato bermasdi va hisobot jimgina boshqa savolga javob berardi.
    """
    report = accuracy_report(rows(tp=401, fp=23, fn=38, tn=150))

    assert report.matrix == ConfusionMatrix(tp=401, fp=23, fn=38, tn=150)
    assert report.n == 612
    assert report.measured is True

    near(report.base_rate, 0.717)
    near(report.correct.point, 0.900)
    near(report.correct.lower, 0.874)
    near(report.correct.upper, 0.922)
    near(report.false_occupied.point, 0.054)
    near(report.false_occupied.lower, 0.036)
    near(report.false_occupied.upper, 0.080)
    near(report.false_empty.point, 0.087)
    near(report.false_empty.lower, 0.064)
    near(report.false_empty.upper, 0.117)


def test_two_error_kinds_are_reported_separately() -> None:
    """Ikki xato ALOHIDA maydonda va ular TENG EMAS.

    Kirish ATAYIN nosimmetrik: `fp = 1`, `fn = 9`. Bitta «aniqlik»
    raqami ikkalasini ham 0,80 ga yig'ib yuborardi va direktor
    «yig'ilmagan patta» muammosini KO'RMASDI.
    """
    report = accuracy_report(rows(tp=20, fp=1, fn=9, tn=20))

    assert report.false_occupied.point != report.false_empty.point
    near(report.false_occupied.point, 1 / 21)
    near(report.false_empty.point, 9 / 29)
    near(report.correct.point, 40 / 50)


def test_base_rate_is_reported() -> None:
    """⛔ `base_rate` MAJBURIY — usiz «90 %» raqami o'qilmaydi.

    Kirish ATAYIN og'ir tomonlama: 45 band, 5 bo'sh. «Har doim band»
    deydigan soxta model bu namunada 90 % aniqlik olardi va aynan
    `base_rate` uni fosh qiladi.
    """
    report = accuracy_report(rows(tp=45, fp=5, fn=0, tn=0))

    near(report.base_rate, 45 / 50)
    near(report.correct.point, 45 / 50)


def test_a_matrix_never_receives_a_dont_know_answer() -> None:
    """«Aniq ayta olmayman» matritsaga TUSHSA — OCHIQ xato."""
    with pytest.raises(ValueError, match="matritsaga"):
        confusion_matrix([(OCCUPIED, UNCERTAIN)])


def test_system_uncertain_counts_as_the_empty_it_would_become() -> None:
    """⚠⚠ TIZIMNING `uncertain` JAVOBI `empty` DEB SANALADI (D-19 bilan bir manba).

    Ikki da'vo birdan:

      1. `uncertain` MATRITSADAN CHIQARIB TASHLANMAYDI — chiqarilsa
         model IKKILANGAN, ya'ni eng qiyin holatlar o'lchovdan ketardi
         va aniqlik SUN'IY ko'tarilardi (§C.8, 2-dushman);
      2. u AYNAN `empty` bo'lib sanaladi, chunki kun oxirida shu hukm
         yoziladi va o'sha rastadan patta YIG'ILMAYDI — ya'ni haqiqat
         «band» bo'lsa bu `fn` («bo'sh deb xato»).

    NAZORAT: ikkinchi juftlik `(empty, occupied)` ham `fn` beradi, ya'ni
    ikkalasi BIR XIL katakka tushishi kerak.
    """
    matrix = confusion_matrix([(UNCERTAIN, OCCUPIED), (EMPTY, OCCUPIED)])

    assert matrix == ConfusionMatrix(tp=0, fp=0, fn=2, tn=0)


# ===========================================================================
# 3. IKKI FILTR — VA ULARNING TESTLARI ALOHIDA
# ===========================================================================


def test_train_rows_excluded() -> None:
    """⛔ `purpose = 'train'` qatorlar hisobotga KIRMAYDI (D-14).

    Qo'shilgan `train` qatorlar ATAYIN «mukammal» (hammasi to'g'ri):
    kirsalar `correct` ko'tarilardi. Hisobot raqamlari O'ZGARMASLIGI —
    o'lchanadigan da'vo.
    """
    base = accuracy_report(rows(tp=15, fp=5, fn=5, tn=15))
    polluted = accuracy_report(
        [*rows(tp=15, fp=5, fn=5, tn=15), *rows(tp=100, tn=100, purpose=TRAIN)]
    )

    assert polluted == base, "trening qatorlari aniqlik raqamini o'zgartirdi (D-14 buzilgan)"


def test_uncertain_queue_rows_excluded() -> None:
    """⛔ BOSHQA NAVBAT qatorlari hisobotga KIRMAYDI (SC#4).

    =======================================================================
    ⚠⚠ BU KIRISH SXEMADA MAVJUD BO'LA OLMAYDI VA TEST SHUNI BILADI.

    `ck_review_assignments_eval_needs_blind_audit` (05-05) `eval` +
    `uncertain` juftligini RAD ETADI, ya'ni bazadagi ma'lumotda ikki
    filtr AYNAN bir xil to'plamni beradi va ularni ajratadigan qator
    YO'Q — bu 05-10 sabotaj D ning aynan sinfi («`WHERE` sharti ikki
    ifodani teng qilib qo'yadi»).

    Shuning uchun o'lchov SOF FUNKSIYA CHEGARASIDA qilinadi: qator
    QO'LDA quriladi. Da'vo shunga mos ravishda TOR: «funksiya ikkinchi
    filtrni O'ZI bajaradi va sxemaga tayanmaydi» — bu bugungi
    kafolatning takrori emas, `CHECK` bo'shatilgan kunga chidamlilik.
    =======================================================================
    """
    base = accuracy_report(rows(tp=15, fp=5, fn=5, tn=15))
    polluted = accuracy_report(
        [
            *rows(tp=15, fp=5, fn=5, tn=15),
            *rows(tp=100, tn=100, purpose=EVAL, queue_kind=UNCERTAIN_QUEUE),
        ]
    )

    assert polluted == base, "noaniq navbat javoblari hisobotga kirdi (SC#4 buzilgan)"


def test_the_two_filters_are_independent() -> None:
    """NAZORAT: ikki filtrning HAR BIRI YOLG'IZ ham qatorni chiqarib tashlaydi.

    ⚠ USIZ YUQORIDAGI IKKI TEST BITTA FILTR BILAN HAM YASHIL QOLARDI:
      `train` + `uncertain` qatori IKKALA shartni ham buzadi, ya'ni uni
      bitta filtr ham ushlaydi. Bu yerda har bir kirish AYNAN BITTA
      shartni buzadi.
    """
    empty_report = accuracy_report(
        [
            AccuracyRow(TRAIN, BLIND, OCCUPIED, OCCUPIED),
            AccuracyRow(EVAL, UNCERTAIN_QUEUE, OCCUPIED, OCCUPIED),
        ]
    )

    assert empty_report.drawn == 0
    assert empty_report.n == 0


# ===========================================================================
# 4. JAVOBSIZ BANDLAR VA `n < 20`
# ===========================================================================


def test_unanswered_items_stay_in_the_sample() -> None:
    """⛔ JAVOBSIZ BAND NAMUNADAN CHIQMAYDI — u SANALADI (§C.8, 4-dushman).

    Uch alohida da'vo va ular bir-birini almashtirmaydi:
      `drawn`      — tortilgan bandlar (javobsizlar BILAN);
      `unanswered` — javobsizlar soni AYNAN ko'rinadi;
      `n`          — matritsaga tushganlar (javobsizlarSIZ).

    `drawn == n` bo'lsa qisman bajarilgan audit TO'LIQ ko'rinardi.
    """
    sample = [
        *rows(tp=10, fp=2, fn=3, tn=10),
        *[AccuracyRow(EVAL, BLIND, OCCUPIED, None) for _ in range(7)],
    ]

    report = accuracy_report(sample)

    assert report.drawn == 32
    assert report.answered == 25
    assert report.unanswered == 7
    assert report.n == 25
    assert report.drawn != report.n, "javobsizlar namunadan jimgina chiqib ketdi"


def test_dont_know_answers_are_outside_the_matrix() -> None:
    """«Aniq ayta olmadi» ALOHIDA sanaladi va matritsani o'zgartirmaydi (O-06)."""
    base = accuracy_report(rows(tp=10, fp=5, fn=5, tn=10))
    with_dont_know = accuracy_report(
        [
            *rows(tp=10, fp=5, fn=5, tn=10),
            *[AccuracyRow(EVAL, BLIND, OCCUPIED, UNCERTAIN) for _ in range(4)],
        ]
    )

    assert with_dont_know.matrix == base.matrix
    assert with_dont_know.n == base.n
    assert with_dont_know.dont_know == 4
    assert base.dont_know == 0, "nol bo'lganda ham maydon qaytadi"
    assert with_dont_know.drawn == base.drawn + 4


def test_small_n_reports_no_percentage() -> None:
    """⛔ `n = 19` -> `measured is False` VA BIRORTA foiz maydoni `None`.

    Foiz maydonlari JAVOBDAN CHIQIB KETMAYDI — ular `None` bo'ladi.
    Maydonning yo'qligi klientda «eski server» deb o'qilardi, `null`
    esa «hali o'lchanmagan» deb.
    """
    report = accuracy_report(rows(tp=10, fp=3, fn=3, tn=3))

    assert report.n == 19
    assert report.measured is False
    assert report.base_rate is None
    for interval in (report.correct, report.false_occupied, report.false_empty):
        assert (interval.point, interval.lower, interval.upper) == (None, None, None)

    # ⚠ XOM SONLAR BARIBIR QAYTADI: «hisobot yo'q» va «hali o'lchanmadi»
    #   bir xil ko'rinmasligi kerak.
    assert report.matrix == ConfusionMatrix(tp=10, fp=3, fn=3, tn=3)
    assert report.drawn == 19


def test_twenty_answers_switch_the_report_on() -> None:
    """`n = 20` -> `measured is True` va foizlar chiqadi. Chegara AYNAN 20."""
    report = accuracy_report(rows(tp=10, fp=3, fn=3, tn=4))

    assert report.n == MIN_SAMPLE_FOR_PERCENT
    assert report.measured is True
    assert report.base_rate is not None
    assert report.correct.point is not None


def test_an_empty_period_still_returns_every_field() -> None:
    """Bo'sh davr — barcha maydonlar bor, foizlar `None`, sonlar nol."""
    report = accuracy_report([])

    assert (report.drawn, report.answered, report.unanswered, report.dont_know, report.n) == (
        0,
        0,
        0,
        0,
        0,
    )
    assert report.measured is False
    assert report.matrix == ConfusionMatrix(tp=0, fp=0, fn=0, tn=0)


# ===========================================================================
# 5. D-16 — HISOBOTDA MAYDON HAM YO'Q
# ===========================================================================


def test_the_report_declares_no_reviewer_self_consistency() -> None:
    """⛔⛔ NAZORATCHINING ICHKI MOSLIGI (D-16) MAYDON SIFATIDA HAM YO'Q.

    05-11 o'lchadi: takroriy band bugungi sxemada IFODALAB BO'LMAYDI
    (ikki `UNIQUE` uni rad etadi), ya'ni MEXANIZM QURILMAGAN. Bo'sh
    maydon qo'yish keyingi ijrochini «bu yerni to'ldirish kerak» degan
    xulosaga olib kelardi va u mavjud bo'lmagan o'lchovga son yozardi;
    `100 %` yozish esa o'lchanmagan miqdorni o'lchangan qilib
    ko'rsatardi (T-05-04).

    ⚠ DA'VO NOMLAR RO'YXATI BILAN emas, MAYDON TO'PLAMI bilan yopiladi:
      hisobot maydonlari AYNAN sanab chiqiladi, ya'ni bu testni
      chetlab o'tish uchun ro'yxatni ATAYIN o'zgartirish kerak bo'ladi.
    """
    report = accuracy_report(rows(tp=10, tn=10))
    declared = set(type(report).__dataclass_fields__)

    assert declared == {
        "drawn",
        "answered",
        "unanswered",
        "dont_know",
        "matrix",
        "n",
        "measured",
        "base_rate",
        "correct",
        "false_occupied",
        "false_empty",
    }, f"hisobot maydonlari o'zgargan: {sorted(declared)}"

    for forbidden in ("self_consistency", "consistency", "repeat", "agreement"):
        assert not any(forbidden in name for name in declared), (
            f"hisobotda `{forbidden}` ma'nosidagi maydon paydo bo'ldi — "
            "D-16 mexanizmi QURILMAGAN, ya'ni bu son o'lchanmagan bo'lardi"
        )


# ===========================================================================
# 6. «TEZ QAROR» — `NULL` HECH QACHON TEZ EMAS
# ===========================================================================


@pytest.mark.parametrize(
    ("decision_ms", "expected"),
    [(None, False), (0, True), (1999, True), (2000, False), (9000, False)],
)
def test_fast_decision_never_counts_a_missing_measurement(
    decision_ms: int | None, expected: bool
) -> None:
    """⛔ `None` «tez» EMAS — u O'LCHANMAGAN (05-10 ochiq bandi #7).

    Valkey bir soat ishlamasa `decision_ms` `NULL` bo'lib yozilardi va
    ularni «tez» deb sanash hisobotda «bugun 40 ta shoshib bosilgan
    qaror» degan BUTUNLAY SOXTA son chiqarardi — ya'ni diagnostika
    nosozligi nazoratchining aybiga aylanardi.
    """
    assert is_fast_decision(decision_ms) is expected
