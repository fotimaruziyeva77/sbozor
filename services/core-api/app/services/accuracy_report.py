"""Aniqlik hisoboti — CHALKASHLIK MATRITSASI, Wilson oralig'i va FAQAT `eval` (AI-04).

=============================================================================
⛔⛔ «ANIQLIK» YOLG'IZ KO'RSATKICH SIFATIDA E'LON QILINMAYDI (§C.8.4).

Rastalarning 90% i band bo'lsa, «har doim band» deb javob beradigan
SOXTA model 90% aniqlik oladi. Shuning uchun bu modul birorta funksiyada
yolg'iz «aniqlik» qaytarmaydi: chiqish HAR DOIM chalkashlik matritsasi +
BAZAVIY BANDLIK ULUSHI (`base_rate`) bilan keladi va `base_rate`
maydonining O'ZI majburiy.

⛔ IKKI XATO TENG EMAS VA ULARNING MAXRAJI HAM BOSHQA:

    «Band deb xato»  = fp / (tp + fp)   -> tizim BAND degan rastalarning
                                          qanchasi aslida bo'sh edi
                                          => SOTUVCHI BILAN NIZO xavfi
    «Bo'sh deb xato» = fn / (tp + fn)   -> ROSTDAN band bo'lgan
                                          rastalarning qanchasini tizim
                                          o'tkazib yubordi
                                          => YIG'ILMAGAN PATTA

⚠ MAXRAJLAR ATAYIN BOSHQA VA ULAR O'LCHOV BILAN TANLANGAN, tanlab
  olinmagan: UI-SPEC §11.1 dagi ishlangan misol (tp=401, fp=23, fn=38,
  tn=150) aynan shu ikki maxraj bilan spetsifikatsiyadagi 5,4 % va 8,7 %
  sonlarini beradi. Boshqa har qanday juftlik boshqa son berardi va
  `test_matrix_matches_the_ui_spec_worked_example` uni qizartiradi.

  Sabab mahsulotda ham aynan shunday: birinchi savol «men yozgan
  pattaning qanchasi noto'g'ri?» (maxraj — TIZIM aytgani), ikkinchisi
  «qancha patta yig'ilmay qoldi?» (maxraj — HAQIQATDA band bo'lgani).
=============================================================================

⛔ HISOBOT FAQAT IKKI FILTRDAN O'TGAN QATORLARDAN CHIQADI:

    purpose    = 'eval'          (D-14 — 70/30, TORTISH PAYTIDA belgilangan)
    queue_kind = 'blind_audit'   (SC#4 — o'lchov faqat KO'R namunadan)

⚠⚠ IKKINCHI FILTR BUGUNGI MAHSULOT MA'LUMOTIDA O'LCHANMAYDI VA BU
   OCHIQ AYTILADI. `ck_review_assignments_eval_needs_blind_audit`
   (05-05) `purpose = 'eval'` bo'lgan qator uchun `queue_kind` ni
   ALLAQACHON `'blind_audit'` ga majburlaydi, ya'ni bazadagi ma'lumotda
   ikki filtr AYNAN bir xil to'plamni beradi va ularni ajratadigan
   qator MAVJUD EMAS (bu 05-10 sabotaj D ning aynan sinfi).

   Shuning uchun ikkinchi filtr SOF FUNKSIYA CHEGARASIDA o'lchanadi:
   test sxema RUXSAT BERMAYDIGAN qatorni (eval + uncertain) QO'LDA
   quradi va funksiya uni tashlab yuborishini ko'rsatadi. Bu bugungi
   kafolatning takrori emas — u `CHECK` bo'shatilgan kunga chidamlilik
   va o'sha kun kelganda hisobot JIMGINA shishmaydi.

=============================================================================
⛔ JAVOBSIZ BANDLAR NAMUNADAN CHIQMAYDI (§C.8, 4-dushman).

Ular `unanswered` bo'lib SANALADI va `drawn` maxraji ularni O'Z ICHIGA
OLADI. Ularni jimgina tashlab yuborish QISMAN bajarilgan auditni TOZA
ko'rinadigan ballga aylantirardi: nazoratchi 30 banddan 8 tasiga javob
bersa, «aniqlik» o'sha 8 tadan hisoblanib, u ham xolis bo'lmasdi.

⛔ «ANIQ AYTA OLMAYMAN» JAVOBI MATRITSADAN TASHQARIDA (O-06).
Uni «bo'sh» deb sanash insonning bilmasligini tizimning to'g'riligiga
aylantirardi; «xato» deb sanash esa uni tizimning xatosiga. U — KADR
SIFATI haqidagi ma'lumot va u alohida son bo'lib turadi.

=============================================================================
⛔ `n < MIN_SAMPLE_FOR_PERCENT` DA BIRORTA FOIZ QAYTARILMAYDI.

Kichik namunada oraliq shu qadar kengki, foiz ma'lumot emas, SHOVQIN
uzatadi. `measured = False` va BARCHA nisbat maydonlari `None` bo'ladi —
xom sonlar esa qaytadi. Bu 05-01 ning T-05-04 qoidasi: o'lchanmagan
miqdor KO'RSATILGAN zahoti o'lchangan deb o'qiladi.

⛔ TAXMINIY (normal-approximation / Wald) ORALIQ ISHLATILMAYDI. Kichik
`n` va chetdagi `p` da u ishonchsiz (§C.8.4) — ya'ni ko'rsatilgan
oraliq HAQIQIY bo'lishi shart. `scipy` QO'SHILMAYDI: kerak bo'lgan
narsa bitta formula.

=============================================================================
⚠⚠ NAZORATCHINING ICHKI MOSLIGI (D-16) BU HISOBOTDA YO'Q — NA SON, NA
   MAYDON SIFATIDA.

05-11 o'lchadi va isbotladi: takroriy band (bir hodisani ikkinchi marta
so'rash) bugungi sxemada IFODALAB BO'LMAYDI —
`uq_review_assignments_occupancy_event_id` ikkinchi topshiriqni,
`uq_zone_reviews_review_assignment_id` esa ikkinchi javobni rad etadi.
Mexanizm QURILMAGAN, ya'ni o'lchov ham YO'Q.

Uni `100 %` (yoki `null` o'rniga har qanday son) qilib ko'rsatish
O'LCHANMAGAN miqdorni o'lchangan qilib ko'rsatardi — T-05-04 ning aynan
taqiqi. Maydonning O'ZI ham e'lon qilinmaydi: bo'sh maydon keyingi
ijrochini «bu yerni to'ldirish kerak ekan» degan xulosaga olib kelardi
va u mavjud bo'lmagan mexanizmga son yozardi.
=============================================================================

⚠ MODUL SOF: DB ham, HTTP ham, `Settings` ham import qilinmaydi.
  Chaqiruvchi (`app/api/v1/occupancy.py`) qatorlarni o'qib beradi.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from sbozor_core.enums import OccupancyVerdict, ReviewPurpose, ReviewQueueKind
from sbozor_core.occupancy import effective_verdict

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = [
    "MIN_SAMPLE_FOR_PERCENT",
    "Z_95",
    "AccuracyReport",
    "AccuracyRow",
    "ConfusionMatrix",
    "ProportionInterval",
    "accuracy_lower_wilson_bound",
    "accuracy_report",
    "confusion_matrix",
    "is_fast_decision",
    "wilson_interval",
]


Z_95: Final[float] = 1.96
"""95 % ishonch darajasiga mos standart normal kvantil.

⚠ `frontend/src/lib/wilson.ts` DAGI `Z_95` BILAN AYNAN BIR XIL bo'lishi
  shart: ikkala tomon bir xil oraliqni chizadi va ular ajralib ketsa
  server bilan ekran BOSHQA-BOSHQA son ko'rsatardi. Farq
  `test_accuracy_report.py` da matn darajasida qulflangan.
"""

MIN_SAMPLE_FOR_PERCENT: Final[int] = 20
"""Foiz UMUMAN qaytarilmaydigan quyi chegara (UI-SPEC §8.4 O-4, §11.5).

⚠ Chegara «endi raqam ISHONCHLI» degani EMAS — u «endi raqam
  KO'RSATILADI» degani: `n = 20` da oraliq hamon ~±13 f.p. keng.

Nega aynan 20: birinchi kunning oxirida (30 band/kun, D-13) direktor
NIMADIR ko'rishi kerak, aks holda «tizim ishlamayapti» degan xulosa
chiqarardi.

⚠ `frontend/src/lib/wilson.ts::MIN_SAMPLE_FOR_PERCENT` BILAN BIR XIL
  SON. Ikkalasi ajralganda server foiz qaytarib, ekran uni chizmasdi
  (yoki teskarisi) — nosozlik «ma'lumot yo'q» ko'rinishida bo'lardi.
"""

_FAST_DECISION_MS: Final[int] = 2000
"""«Tez qaror» chegarasi (UI-SPEC §11.6: «2 soniyadan tez»).

⚠ BU MODULDA ATAYIN: chegara hisobot MA'NOSIGA tegishli va u
  nazoratchiga HECH QACHON ko'rsatilmaydi (§7.3) — ko'rsatilsa u
  o'lchovni chetlab o'tishni o'rganardi (sekinroq bosish — real diqqat
  emas, IMITATSIYA).
"""

_OCCUPIED: Final[str] = OccupancyVerdict.OCCUPIED.value
_UNCERTAIN: Final[str] = OccupancyVerdict.UNCERTAIN.value
_EVAL: Final[str] = ReviewPurpose.EVAL.value
_BLIND_AUDIT: Final[str] = ReviewQueueKind.BLIND_AUDIT.value


# ===========================================================================
# TIPLAR
# ===========================================================================


@dataclass(frozen=True, slots=True)
class ProportionInterval:
    """Nisbat va uning ishonch oralig'i — `lib/wilson.ts::ProportionInterval` jufti.

    Namuna bo'sh bo'lganda uchala maydon ham `None`: «hali o'lchanmadi»
    va «nolga teng» BIR XIL ko'rinmasligi uchun.
    """

    point: float | None
    lower: float | None
    upper: float | None


@dataclass(frozen=True, slots=True)
class ConfusionMatrix:
    """2x2 matritsa — «musbat» AYNAN `occupied`.

    ⚠ NOMLAR TIZIM/INSON tartibida o'qiladi: `fp` — TIZIM band dedi,
      INSON bo'sh dedi («band deb xato»).
    """

    tp: int
    fp: int
    fn: int
    tn: int

    @property
    def n(self) -> int:
        """Matritsaga TUSHGAN javoblar soni — javobsizlar va «bilmayman» SIZ."""
        return self.tp + self.fp + self.fn + self.tn


@dataclass(frozen=True, slots=True)
class AccuracyRow:
    """Bitta ko'r audit bandi — javob berilgan yoki BERILMAGAN.

    ⚠ `human_verdict is None` — JAVOBSIZ band. U namunadan CHIQMAYDI:
      `unanswered` bo'lib sanaladi va `drawn` maxrajida qoladi (modul
      docstringi, 4-dushman).
    """

    purpose: str
    queue_kind: str
    system_verdict: str
    human_verdict: str | None


@dataclass(frozen=True, slots=True)
class AccuracyReport:
    """Hisobotning TO'LIQ chiqishi — birorta maydon shartli emas.

    ⛔ `measured is False` bo'lganda NISBAT maydonlari `None` bo'ladi,
       lekin ular JAVOBDAN CHIQIB KETMAYDI: mavjud bo'lmagan maydon
       klientda «eski server» yoki «xato» deb o'qilardi, `null` esa
       «hali o'lchanmagan» deb.
    """

    drawn: int
    """Namunaga TUSHGAN `eval` bandlari — javobsizlar BILAN BIRGA."""
    answered: int
    unanswered: int
    dont_know: int
    """«Aniq ayta olmayman» javoblari — matritsadan TASHQARIDA (O-06)."""
    matrix: ConfusionMatrix
    n: int
    """Matritsaga tushgan javoblar soni — `drawn` DAN KICHIK bo'lishi normal."""
    measured: bool
    base_rate: float | None
    """Bazaviy bandlik ulushi — INSON javoblariga ko'ra («71,7 % i band edi»).

    ⛔ MAJBURIY MAYDON: usiz «90 %» raqami o'qilmaydi (§C.8.4). Qiymat
       `measured is False` bo'lganda `None` — u ham FOIZ.
    """
    correct: ProportionInterval
    false_occupied: ProportionInterval
    """«Band deb xato» — maxraj TIZIM band degan javoblar (nizo xavfi)."""
    false_empty: ProportionInterval
    """«Bo'sh deb xato» — maxraj ROSTDAN band bo'lganlar (yig'ilmagan patta)."""


# ===========================================================================
# ARIFMETIKA
# ===========================================================================


def wilson_interval(successes: int, n: int, z: float = Z_95) -> ProportionInterval:
    """Wilson score oralig'i — `lib/wilson.ts::wilsonInterval` NING AYNAN JUFTI.

    Wilson tanlangan, chunki u KICHIK `n` va CHETDAGI `p` da ham to'g'ri
    qoplama beradi (§C.8.4) — bu loyihada ikkala shart ham NORMAL holat:
    kunlik byudjet 30 band, kutilgan aniqlik esa 0,9 dan yuqori.

    Oraliq nuqta bahoning atrofida SIMMETRIK EMAS va bu uning butun
    foydasi: chegaralar [0, 1] dan chiqmaydi va `p = 1` da ham oraliq
    KENGLIKKA EGA bo'lib qoladi. «Aniqlik 100 %, oraliq 100–100 %» degan
    yolg'on qat'iylik shu bilan STRUKTURA darajasida imkonsiz bo'ladi.

    ⚠ TEKSHIRUVLAR TARTIBI KONTRAKTNING BIR QISMI (TS jufti bilan AYNAN
      bir xil):

        1. shakl (butun, manfiy emas)  -> `ValueError`
        2. `n == 0`                    -> uchala maydon `None`
        3. `successes > n`             -> `ValueError`

      2-qadam 3-dan OLDIN: namuna bo'sh bo'lganda `successes` ning
      qiymati umuman ma'noga ega emas. 3-qadam esa JIMGINA
      TO'G'RILANMAYDI — `successes` ni `n` ga qisish «aniqlik 100 %»
      degan hisobot chiqarardi.
    """
    _reject_non_count(successes, "successes")
    _reject_non_count(n, "n")

    if n == 0:
        return ProportionInterval(None, None, None)

    if successes > n:
        raise ValueError(
            f"wilson_interval(): `successes` ({successes}) `n` ({n}) dan katta bo'lolmaydi"
        )
    if not math.isfinite(z) or z <= 0:
        raise ValueError(f"wilson_interval(): `z` musbat va chekli bo'lishi SHART ({z})")

    p = successes / n
    z2 = z * z
    denominator = 1 + z2 / n

    center = (p + z2 / (2 * n)) / denominator
    half_width = (z * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n))) / denominator

    # Qisish suzuvchi nuqta shovqini uchun (TS jufti bilan bir xil sabab):
    # formula matematik jihatdan [0, 1] dan chiqmaydi, lekin `p = 0` da
    # `center - half_width` amalda -1e-17 beradi.
    return ProportionInterval(
        point=p,
        lower=max(0.0, center - half_width),
        upper=min(1.0, center + half_width),
    )


def accuracy_lower_wilson_bound(correct: int, total: int) -> float:
    """Aniqlikning Wilson QUYI chegarasi — oltin to'plam darvozasining kirishi.

    ⚠ IMZO `scripts/eval-golden-set.py::LOWER_BOUND_ATTR` TOMONIDAN
      BELGILANGAN (`(to'g'ri, jami) -> float`) va u o'sha skript bu
      moduldan matematikani IMPORT QILISHI uchun mavjud. Ikki nusxa
      formula ikki xil raqam berardi va «94 %» qaysi hisobdan chiqqani
      aniqlanmasdi — bu savol esa aynan NIZO paytida so'raladi.

    Raises:
        ValueError: bo'sh namunada. Darvoza uchun `0.0` qaytarish
            «aniqlik nol» degan o'lchangan da'vo bo'lardi, holbuki
            o'lchov UMUMAN bo'lmagan.
    """
    interval = wilson_interval(correct, total)
    if interval.lower is None:
        raise ValueError(
            "accuracy_lower_wilson_bound(): bo'sh namunada quyi chegara YO'Q — "
            "darvoza o'lchanmagan qiymat bilan qurollana olmaydi"
        )
    return interval.lower


def confusion_matrix(pairs: Sequence[tuple[str, str]]) -> ConfusionMatrix:
    """`(tizim javobi, inson javobi)` juftliklaridan 2x2 matritsa.

    =======================================================================
    ⚠⚠ TIZIMNING `uncertain` JAVOBI `empty` GA AYLANTIRILADI — VA U
       `sbozor_core.occupancy.effective_verdict()` BILAN QILINADI.

    Sabab ikkita va ikkalasi ham majburiy:

      1. O'LCHANAYOTGAN NARSA — TIZIM AMALDA QILADIGAN ISH. Nazoratchi
         javob bermaganda `uncertain` kun oxirida `empty` bo'ladi (D-19),
         ya'ni o'sha band uchun patta YOZILMAYDI. Demak «tizim nima
         dedi?» degan savolning javobi AYNAN `empty`.

      2. `uncertain` LARNI MATRITSADAN CHIQARIB TASHLASH ANIQLIKNI SUN'IY
         KO'TARARDI — model IKKILANGAN, ya'ni ENG QIYIN holatlar
         o'lchovdan chiqib ketardi. Bu `audit_draw.FRAME_PREDICATE`
         ATAYIN `verdict` filtri qo'ymagan sababning aynan o'zi
         (§C.8, 2-dushman).

    ⛔ IKKINCHI NUSXA YOZILMAYDI: hosila `effective_verdict(..., None)`
       dan chiqadi, ya'ni kun yopilishi YOZADIGAN qiymat bilan hisobot
       O'LCHAYDIGAN qiymat BIR MANBADAN keladi.
    =======================================================================

    Args:
        pairs: har biri `(system_verdict, human_verdict)`. Inson javobi
            `uncertain` bo'lgan juftliklar chaqiruvchida ALLAQACHON
            ajratilgan bo'lishi kerak (`accuracy_report()` shuni qiladi).

    Raises:
        ValueError: inson javobi `uncertain` bo'lsa — u matritsaga
            TUSHMAYDI va jimgina «bo'sh» deb sanalishi D-16 dan ham
            yomonroq bo'lardi: insonning BILMASLIGI tizimning
            to'g'riligiga aylanardi.
    """
    tp = fp = fn = tn = 0
    for system_verdict, human_verdict in pairs:
        if human_verdict == _UNCERTAIN:
            raise ValueError(
                "confusion_matrix(): «aniq ayta olmayman» javobi matritsaga "
                "TUSHMAYDI — u alohida sanaladi (O-06)"
            )
        system, _ = effective_verdict(system_verdict, None)
        human, _ = effective_verdict(human_verdict, None)

        if system == _OCCUPIED:
            tp, fp = (tp + 1, fp) if human == _OCCUPIED else (tp, fp + 1)
        else:
            fn, tn = (fn + 1, tn) if human == _OCCUPIED else (fn, tn + 1)
    return ConfusionMatrix(tp=tp, fp=fp, fn=fn, tn=tn)


def accuracy_report(rows: Sequence[AccuracyRow]) -> AccuracyReport:
    """Ko'r audit namunasidan aniqlik hisoboti — IKKI FILTR bilan.

    ⛔ FILTRLAR MODUL DOCSTRINGIDA. Bu yerda ular BIRGA yoziladi, lekin
       ular IKKI BOSHQA qarordan keladi (D-14 va SC#4) va ikkisining ham
       O'Z testi bor.

    Args:
        rows: davr ichidagi BARCHA ko'r audit topshiriqlari — javobsizlar
            HAM. Chaqiruvchi ularni oldindan filtrlamaydi: filtrlash shu
            funksiyaning kafolati va u ikki joyda takrorlanmasligi kerak.
    """
    sample = [row for row in rows if row.purpose == _EVAL and row.queue_kind == _BLIND_AUDIT]

    unanswered = sum(1 for row in sample if row.human_verdict is None)
    dont_know = sum(1 for row in sample if row.human_verdict == _UNCERTAIN)
    pairs = [
        (row.system_verdict, row.human_verdict)
        for row in sample
        if row.human_verdict is not None and row.human_verdict != _UNCERTAIN
    ]

    matrix = confusion_matrix(pairs)
    n = matrix.n
    measured = n >= MIN_SAMPLE_FOR_PERCENT

    if not measured:
        # ⛔ XOM SONLAR QAYTADI, FOIZLAR — YO'Q. Ikkalasini birga
        #    yashirish «hisobot yo'q» degan taassurot berardi, holbuki
        #    o'lchov BOSHLANGAN va uning HAJMI ko'rsatilishi kerak.
        return AccuracyReport(
            drawn=len(sample),
            answered=len(sample) - unanswered,
            unanswered=unanswered,
            dont_know=dont_know,
            matrix=matrix,
            n=n,
            measured=False,
            base_rate=None,
            correct=_UNMEASURED,
            false_occupied=_UNMEASURED,
            false_empty=_UNMEASURED,
        )

    truly_occupied = matrix.tp + matrix.fn
    called_occupied = matrix.tp + matrix.fp

    return AccuracyReport(
        drawn=len(sample),
        answered=len(sample) - unanswered,
        unanswered=unanswered,
        dont_know=dont_know,
        matrix=matrix,
        n=n,
        measured=True,
        base_rate=truly_occupied / n,
        correct=wilson_interval(matrix.tp + matrix.tn, n),
        false_occupied=wilson_interval(matrix.fp, called_occupied),
        false_empty=wilson_interval(matrix.fn, truly_occupied),
    )


def is_fast_decision(decision_ms: int | None) -> bool:
    """«Tez qaror» mi — `NULL` HECH QACHON tez emas.

    ⚠⚠ `decision_ms` `NULL` BO'LISHI MUMKIN (Valkey uzilishi, TTL, ko'p
       worker — 05-10 deviatsiya #8). `NULL` ni «tez» deb sanash
       DIAGNOSTIKA nosozligini nazoratchining AYBIGA aylantirardi:
       Valkey bir soat ishlamasa hisobotda «bugun 40 ta shoshib bosilgan
       qaror» chiqardi va u butunlay soxta bo'lardi.

    ⚠ `NULL` «sekin» ham EMAS — u O'LCHANMAGAN. Bu funksiya faqat «tez»
      to'plamini beradi; qolganini «sekin» deb atash chaqiruvchining ishi
      emas va hisobot ham unday demaydi.
    """
    return decision_ms is not None and decision_ms < _FAST_DECISION_MS


_UNMEASURED: Final[ProportionInterval] = ProportionInterval(None, None, None)
"""O'LCHANMAGAN oraliq — uchala maydon `None`.

Bitta umumiy obyekt: `ProportionInterval` `frozen`, ya'ni uni bo'lishish
xavfsiz va «har safar yangi nol» yasash hech nima qo'shmaydi.
"""


def _reject_non_count(value: int, name: str) -> None:
    """Manfiy bo'lmagan BUTUN son — `bool` ALOHIDA rad etiladi.

    `isinstance(True, int)` rost, ya'ni oddiy tekshiruv `True` ni jimgina
    `1` deb qabul qilardi (`money.py::_reject_non_integer` ning aynan
    qoidasi va aynan sababi).
    """
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(
            f"wilson_interval(): `{name}` manfiy bo'lmagan BUTUN son bo'lishi SHART "
            f"(olindi: {value!r})"
        )
