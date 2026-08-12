"""G-35 — IKKI RAQAMNING MATN KONTRAKTI, UCHALA LOCALE (`07-UI-SPEC.md` §12).

=============================================================================
⛔⛔ NEGA BU FAYL 07-14 DA TUG'ILDI VA NEGA U 07-13 DA TUG'ILMAGAN EDI.

07-13 G-35 ning ⛔ SHAKL yarmini bajardi (`payload` kalitlari ustidagi
to'plam tengligi), lekin ⛔ MATN yarmini O'LCHAY OLMADI: matn quruvchisi
`app/jobs/outbox.py::_build_text` o'sha paytda 07-09 ning worktree'sida
edi va bu faylga KO'RINMASDI. 07-13 noma'lum shaxsiy API ga qarshi
SPEKULYATIV test yozishni ATAYIN rad etdi — imzo taxmin qilinganda test
merge'dan keyin `TypeError` bilan yiqilardi.

Ikkala fayl ham endi merge qilingan `main` da, ya'ni darvoza NIHOYAT
yoziladigan bo'ldi. Bu — o'sha ochiq bandning YOPILISHI, yangi da'vo
emas.
=============================================================================

=============================================================================
⛔⛔ NEGA TO'PLAM TENGLIGI, «BORMI?» EMAS (§12.3, D-31).

    QUALIFIER_VOCAB = {expected, recorded}
    EXPECTED = { evening: {expected},  morning: {recorded} }
    har (kalit × 3 locale): found == EXPECTED[kalit]     <- AYNAN bittasi

Oddiy «kutilayotgan bormi?» tekshiruvi kechki xabarga ⛔ «yozilgan» HAM
qo'shilganda YASHIL qolardi — va aynan o'sha ARALASHUV direktorni
chalkashtiradi (§12.1 ssenariysi: kechqurun 4 200 000, ertalab
3 950 000, sabab topilmaydi, uchinchi kuni ikkala xabar ham o'qilmaydi).
=============================================================================

⛔ KUTILGAN SO'ZLAR SHU YERDA QAYTA YOZILGAN, MAHSULOTDAN IMPORT
   QILINMAYDI (05-13 / 07-13 darsi): `_QUALIFIER_WORDS` ni import qilish
   darvozani o'zi tekshirayotgan qiymatga bog'lardi va so'z jimgina
   o'zgartirilganda test YASHIL qolardi. Manba — `07-UI-SPEC.md` §12.2
   jadvali, kod emas.

⚠ BAZA KERAK EMAS: `_build_text()` — SOF funksiya. `payload` esa
  `notification_meta.outbox_payload()` allowlisti bilan bir xil
  kalitlardan iborat.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Final

import pytest
from app.jobs import outbox
from sbozor_core.enums import Locale, OutboxKind

if TYPE_CHECKING:
    from collections.abc import Iterable

MORNING: Final = OutboxKind.DIGEST_MORNING.value
EVENING: Final = OutboxKind.DIGEST_EVENING.value

LOCALES: Final[tuple[str, ...]] = (Locale.UZ_LATN.value, Locale.UZ_CYRL.value, Locale.RU.value)
"""Uchala til MAJBURIY (D-31) — ro'yxat `Locale` enumidan, qo'lda emas."""

QUALIFIER_WORDS: Final[dict[str, dict[str, str]]] = {
    Locale.UZ_LATN.value: {"expected": "kutilayotgan", "recorded": "yozilgan"},
    Locale.UZ_CYRL.value: {"expected": "кутилаётган", "recorded": "ёзилган"},
    Locale.RU.value: {"expected": "ожидаемый", "recorded": "записанный"},
}
"""`07-UI-SPEC.md` §12.2 jadvalining TESTDAGI nusxasi — mahsulotdan MUSTAQIL."""

EXPECTED_QUALIFIERS: Final[dict[str, set[str]]] = {
    EVENING: {"expected"},
    MORNING: {"recorded"},
}
"""Har xabarda AYNAN BITTA sifatlovchi — §12.3 ning `deepEqual` i."""

_MORNING_PAYLOAD: Final[dict[str, Any]] = {
    "business_date": "2026-08-11",
    "charged_soum": 3_950_000,
    "collected_soum": 3_700_000,
    "occupancy_pct": 87,
    "top_debtor_count": 10,
    "case_new_count": 4,
}
_EVENING_PAYLOAD: Final[dict[str, Any]] = {
    "business_date": "2026-08-12",
    "expected_soum": 4_200_000,
    "collected_soum": 3_100_000,
    "unpaid_stall_count": 26,
    "anomaly_count": 3,
}
PAYLOADS: Final[dict[str, dict[str, Any]]] = {MORNING: _MORNING_PAYLOAD, EVENING: _EVENING_PAYLOAD}
"""⚠ SONLAR §12.1 NING SSENARIYSIDAN: kechqurun 4 200 000 (proyeksiya),
ertalab 3 950 000 (yozilgan hisob). Ular ATAYIN TENG EMAS — teng sonlar
bilan «ikki manba» da'vosi o'lchanmay qolardi."""


def _found(text: str, locale: str) -> set[str]:
    """Matnda UCHRAGAN sifatlovchilar to'plami — §12.3 ning `found` i.

    ⚠ `casefold()` IKKALA TOMONDA: yorliq jumla boshida bosh harf bilan
      turishi mumkin (`Записанный вчера патта`), lug'at esa kichik harfda.
      Registrga sezgir taqqoslash rus tilida darvozani JIMGINA bo'sh
      qilardi.
    """
    haystack = text.casefold()
    return {name for name, word in QUALIFIER_WORDS[locale].items() if word.casefold() in haystack}


def _build(kind: str, locale: str) -> str:
    return outbox._build_text(kind, PAYLOADS[kind], locale=locale)  # noqa: SLF001


def _cases() -> Iterable[tuple[str, str]]:
    return [(kind, locale) for kind in (MORNING, EVENING) for locale in LOCALES]


# ---------------------------------------------------------------------------
# 1. G-35 — to'plam tengligi, har xabar x har locale
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(("kind", "locale"), _cases())
def test_each_digest_names_exactly_one_qualifier(kind: str, locale: str) -> None:
    """⛔ Topilgan sifatlovchilar to'plami AYNAN BITTAGA teng (§12.3).

    Ikki yo'nalish ham shu bitta assertda: kerakli so'z BOR va ikkinchisi
    YO'Q. `in` bilan yozilgan variant ikkinchisining qo'shilishini
    ko'rmasdi.
    """
    text = _build(kind, locale)
    assert _found(text, locale) == EXPECTED_QUALIFIERS[kind], (
        f"{kind} / {locale}: topilgan sifatlovchilar {sorted(_found(text, locale))}, "
        f"kutilgani {sorted(EXPECTED_QUALIFIERS[kind])}. Matn:\n{text}"
    )


@pytest.mark.parametrize(("kind", "locale"), _cases())
def test_the_qualifier_shares_the_line_with_the_number(kind: str, locale: str) -> None:
    """⛔ SIFATLOVCHI RAQAM BILAN BIR QATORDA, ALOHIDA SARLAVHADA EMAS (§12.2).

    =========================================================================
    ⛔ SABAB MEXANIK: Telegram bildirishnomasining QISQARTIRILGAN
       ko'rinishida sarlavha KESILIB qoladi va foydalanuvchi faqat raqamni
       ko'radi. Ya'ni sifatlovchi sarlavhada tursa, kontrakt matnda BOR
       bo'lib turib, ekranda YO'Q bo'lardi.
    =========================================================================

    ⚠ «RAQAM» — `format_soum()` chizgan summa, ya'ni qator ichida kamida
      bitta RAQAM belgisi bo'lishi shart. Faqat sifatlovchi turgan qator
      (masalan «Kutilayotgan:» + keyingi qatorda son) bu shartni
      BAJARMAYDI.
    """
    word = QUALIFIER_WORDS[locale][next(iter(EXPECTED_QUALIFIERS[kind]))]
    carriers = [
        line for line in _build(kind, locale).splitlines() if word.casefold() in line.casefold()
    ]
    assert len(carriers) == 1, (
        f"{kind} / {locale}: sifatlovchi {len(carriers)} qatorda uchradi — u AYNAN "
        f"bitta qatorda, raqam bilan birga turishi kerak: {carriers}"
    )
    assert any(char.isdigit() for char in carriers[0]), (
        f"{kind} / {locale}: sifatlovchi qatorida RAQAM yo'q — u sarlavhaga "
        f"ko'chib ketgan va bildirishnomaning qisqa ko'rinishida KESILARDI: "
        f"{carriers[0]!r}"
    )


# ---------------------------------------------------------------------------
# 2. Uchala locale HAQIQATAN boshqa matn beradi
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("kind", [MORNING, EVENING])
def test_the_three_locales_render_three_different_texts(kind: str) -> None:
    """⛔ NAZORAT: `locale` argumenti matnga HAQIQATAN ta'sir qiladi.

    Usiz yuqoridagi da'volar bo'sh-rost bo'lardi: `locale` ni umuman
    o'qimaydigan quruvchi ham uchala parametrda BIR XIL (lotincha) matn
    qaytarardi va lotincha holat yashil bo'lgani uchun qolgan ikkitasi ham
    «tasodifan» o'tib ketardi — yo'q, aslida ular qizarardi, lekin
    SABABI noto'g'ri o'qilardi («tarjima yo'q» emas, «sifatlovchi
    noto'g'ri»). Bu test sababni AJRATADI.
    """
    rendered = {locale: _build(kind, locale) for locale in LOCALES}
    assert len(set(rendered.values())) == len(LOCALES), (
        "uchala locale bir xil matn berdi — `locale` argumenti matn "
        f"quruvchisiga umuman yetib bormayapti: {rendered}"
    )


def test_an_unknown_locale_falls_back_instead_of_raising() -> None:
    """Noma'lum til xabarni YIQITMAYDI — u standart tilga tushadi.

    ⚠ `KeyError` bu yo'lda QIMMAT: `_deliver()` matn qurilmaganda qatorni
      `failed` ga tushiradi, ya'ni bitta noto'g'ri til qiymati
      KVITANSIYANI butunlay yo'qotardi. Til — KO'RINISH tanlovi, ma'lumot
      emas.
    """
    fallback = _build(EVENING, "kl-KL")
    assert fallback == _build(EVENING, Locale.UZ_LATN.value)


# ---------------------------------------------------------------------------
# 3. NAZORAT — predikat aralashuvni HAQIQATAN ushlaydi
# ---------------------------------------------------------------------------


def test_the_gate_catches_a_mixed_qualifier() -> None:
    """⛔ NAZORAT BANDI: IKKALA sifatlovchi ham bor matn darvozadan O'TMASLIGI shart.

    =========================================================================
    ⛔ USIZ 1-BO'LIM BO'SH-ROST BO'LARDI.

    `found` ni noto'g'ri yozgan (masalan har doim bitta elementli to'plam
    qaytaradigan) yig'uvchi bilan hamma narsa yashil qolardi. Bu test
    aralashtirilgan MATN yasaydi va predikat uni KO'RISHINI talab qiladi —
    ya'ni o'lchanadigan narsa mahsulot emas, DARVOZANING O'ZI.
    =========================================================================
    """
    for locale in LOCALES:
        words = QUALIFIER_WORDS[locale]
        mixed = f"Bugun {words['expected']} va kecha {words['recorded']} patta: 1 000"
        assert _found(mixed, locale) == {"expected", "recorded"}, (
            f"{locale}: predikat ARALASHUVNI ko'rmadi — G-35 ning butun ma'nosi "
            "aynan shu holatni ushlashda"
        )
        assert _found(mixed, locale) != EXPECTED_QUALIFIERS[EVENING], (
            f"{locale}: aralashtirilgan matn kechki xabar kutilmasiga MOS keldi — "
            "to'plam tengligi `in` ga aylanib qolgan"
        )

    # Teskari nazorat: sifatlovchisiz matn BO'SH to'plam beradi, ya'ni
    # predikat «har doim topadigan» funksiya emas.
    assert _found("Kun: 2026-08-12", Locale.UZ_LATN.value) == set()


def test_the_vocabulary_is_closed_and_matches_the_spec() -> None:
    """Lug'at YOPIQ: aynan ikki sifatlovchi, uchala locale'da to'liq.

    ⚠ MAHSULOTNING `QUALIFIER_VOCAB` I BILAN SOLISHTIRILADI, lekin
      SO'ZLAR emas — nomlar. Nomlar API kontrakti (`recon.qualifier.*`
      kalitlari), so'zlar esa copy: birinchisi kod bilan bog'langan,
      ikkinchisi §12.2 jadvali bilan (yuqoridagi `QUALIFIER_WORDS`).
    """
    assert set(outbox.QUALIFIER_VOCAB) == {"expected", "recorded"}
    for locale in LOCALES:
        assert set(QUALIFIER_WORDS[locale]) == set(outbox.QUALIFIER_VOCAB), (
            f"{locale}: sifatlovchilar to'plami spetsifikatsiyadan farq qiladi"
        )
    assert len({word for words in QUALIFIER_WORDS.values() for word in words.values()}) == 6, (
        "olti so'zning ikkitasi bir xil chiqdi — locale jadvali nusxalanган"
    )
