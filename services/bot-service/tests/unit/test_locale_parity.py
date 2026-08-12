"""D-31 — uchala locale majburiy va ular BIR XIL kalit to'plamiga ega.

=============================================================================
⛔⛔ NEGA BO'SH `msgstr` ENG XAVFLI HOLAT.

Bu loyihada msgid — SIMVOLIK KALIT (`app/i18n.py`). Gettext esa tarjimasi
topilmagan msgid uchun ⛔ MSGID NING O'ZINI qaytaradi. Ya'ni bo'sh
`msgstr` bilan rus foydalanuvchi ekranda «bot.binding.neutral» degan
matnni ko'rardi — va NA test, NA lint, NA typecheck qizarardi.

Bu «jimgina yolg'on» sinfining eng toza namunasi va aynan shuning uchun
`test_no_msgstr_is_empty` bu fayldagi eng muhim test.

=============================================================================
⛔ KO'PLIK SHAKLLARI `.po` NING SARLAVHASIDAN, QO'LDA YOZILGAN SHARTDAN EMAS.

Ruschada uchta shakl bor (1 / 2-4 / 5+). `if n == 1` shaklidagi qo'lda
yozilgan mantiq birinchi «2 ta yozuv» da buzilardi va uni hech kim
sezmasdi — matn baribir chizilardi, faqat noto'g'ri shaklda.

⚠ Bu yerda `.po` ning SARLAVHASI o'lchanadi (matn darajasida), xulq esa
  `test_vendor_handlers.py::test_the_russian_header_uses_three_distinct_
  plural_forms` da. Ikkalasi ham kerak: sarlavha to'g'ri bo'lib, matn
  uchta shaklga yozilmagan holat ham mavjud.

=============================================================================
⛔ D-26(a) NING MATN DARVOZASI.

`/start` va bog'lanish matnlari ro'yxatga a'zolik haqida HECH NIMA
aytmasligi kerak: «bu raqam ro'yxatda yo'q» degan javob reyestrni
tashqaridan tekshirish yo'li bo'lardi.

⚠ SKANER MAYDONI QAT'IY: faqat `msgstr` QIYMATLARI. `.po` fayllarning
  IZOHLARI taqiqning SABABINI yozadi va o'sha sababda taqiqlangan
  so'zlar UCHRAYDI — sodda matn qidiruvi ularni buzilish deb o'qirdi
  va yagona «tuzatish» yo'li SABABNI o'chirish bo'lardi (02-23 darsi).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING, Final

from app.i18n import DOMAIN, LOCALES_PATH, SUPPORTED_LOCALES, compile_catalogues

if TYPE_CHECKING:
    from collections.abc import Iterator

MIN_MSGIDS: Final = 15
"""⛔ QUYI CHEGARA (§S-10): katalog bo'shab qolsa quyidagi to'plam
tengliklari JIMGINA yashil bo'lardi (bo'sh == bo'sh)."""

REGISTRY_WORDS: Final = (
    "ro'yxat",
    "reyestr",
    "registry",
    "рўйхат",
    "реестр",
    "список",
)
"""D-26(a): reyestr haqida gapiradigan so'zlar — uchala tilda."""

BINDING_KEY_PREFIXES: Final = ("bot.start.", "bot.binding.", "bot.notBound")
"""Skaner maydoni — bog'lanish oqimidagi matnlar."""

_MSGID_RE: Final = re.compile(r'^msgid(?:_plural)?\s+"(.*)"$')
_MSGSTR_RE: Final = re.compile(r'^msgstr(?:\[\d+\])?\s+"(.*)"$')
_CONT_RE: Final = re.compile(r'^"(.*)"$')


def _po_path(locale: str) -> Path:
    return LOCALES_PATH / locale / "LC_MESSAGES" / f"{DOMAIN}.po"


def _unescape(raw: str) -> str:
    return raw.replace("\\n", "\n").replace("\\t", "\t").replace('\\"', '"').replace("\\\\", "\\")


def _entries(locale: str) -> Iterator[tuple[str, str]]:
    """`(msgid, msgstr)` juftliklari — ⛔ sarlavha bloki (`msgid ""`) SIZ.

    Sarlavhada `Plural-Forms`, `Language` va `Content-Type` yozilgan;
    ular MATN emas, metama'lumot va ularni matn skaniga qo'shish
    quyidagi da'volarni tasodifiy tokenlar bilan «qanoatlantirib»
    qo'yardi.
    """
    current_id = ""
    target: str | None = None
    buffer = ""
    pending: list[tuple[str, str]] = []

    def flush() -> None:
        nonlocal current_id, target, buffer
        if target == "id":
            current_id = buffer
        elif target == "str":
            pending.append((current_id, buffer))
        target = None
        buffer = ""

    for raw_line in _po_path(locale).read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line == "" or line.startswith("#"):
            flush()
            continue
        id_match = _MSGID_RE.match(line)
        if id_match:
            flush()
            if line.startswith("msgid "):
                target = "id"
                buffer = _unescape(id_match.group(1))
            continue
        str_match = _MSGSTR_RE.match(line)
        if str_match:
            flush()
            target = "str"
            buffer = _unescape(str_match.group(1))
            continue
        cont_match = _CONT_RE.match(line)
        if cont_match and target is not None:
            buffer += _unescape(cont_match.group(1))
            continue
        flush()
    flush()

    for msgid, msgstr in pending:
        if msgid != "":
            yield msgid, msgstr


def _msgids(locale: str) -> set[str]:
    return {msgid for msgid, _ in _entries(locale)}


# ---------------------------------------------------------------------------
# QAMROV
# ---------------------------------------------------------------------------


def test_the_catalogues_are_not_empty() -> None:
    """⛔ QUYI CHEGARA — bo'sh katalog ustida tenglik JIMGINA yashil bo'lardi."""
    for locale in SUPPORTED_LOCALES:
        ids = _msgids(locale)
        assert len(ids) >= MIN_MSGIDS, f"{locale}: {len(ids)} msgid (kutilgan >= {MIN_MSGIDS})"


# ---------------------------------------------------------------------------
# D-31 — UCHALA LOCALE, BIR XIL KALIT TO'PLAMI
# ---------------------------------------------------------------------------


def test_every_locale_has_the_same_msgid_set() -> None:
    """⛔ TO'PLAM TENGLIGI — «bor/yo'q» emas, IKKI TOMONLAMA.

    Faqat «referens'dagi hamma kalit bor» tekshiruvi bir tomonlama
    bo'lardi: bir katalogga qo'shilgan ORTIQCHA kalit (masalan
    tuzatilmagan nom) darvozadan o'tib ketardi va u hech qachon
    tarjima qilinmasdi.
    """
    reference, *rest = SUPPORTED_LOCALES
    expected = _msgids(reference)
    for locale in rest:
        assert _msgids(locale) == expected, {
            "yetishmaydi": sorted(expected - _msgids(locale)),
            "ortiqcha": sorted(_msgids(locale) - expected),
        }


def test_no_msgstr_is_empty() -> None:
    """⛔ Bo'sh `msgstr` gettext'da MSGID NING O'ZINI qaytaradi (modul docstringi)."""
    problems = [
        f"{locale}: {msgid}"
        for locale in SUPPORTED_LOCALES
        for msgid, msgstr in _entries(locale)
        if msgstr.strip() == ""
    ]
    assert problems == [], (
        "bo'sh tarjima topildi — rus foydalanuvchi ekranda KALIT NOMINI ko'rardi "
        "va hech nima qizarmasdi:\n  " + "\n  ".join(problems)
    )


def test_no_msgstr_leaks_the_key_name() -> None:
    """Nazorat: tarjima tasodifan msgid ning NUSXASI bo'lib qolmagan.

    Bo'sh `msgstr` dan tashqari ikkinchi shakl ham bor: kimdir kalitni
    `msgstr` ga NUSXALAB qo'yishi mumkin. Natija foydalanuvchi uchun
    AYNI — ekranda `bot.binding.neutral` turadi.
    """
    problems = [
        f"{locale}: {msgid}"
        for locale in SUPPORTED_LOCALES
        for msgid, msgstr in _entries(locale)
        if msgstr.strip() == msgid or msgstr.startswith("bot.")
    ]
    assert problems == [], problems


def test_russian_catalog_declares_three_plural_forms() -> None:
    """⛔ `nplurals=3` — ruschada 1 / 2-4 / 5+."""
    header = _po_path("ru").read_text(encoding="utf-8")
    assert "nplurals=3" in header
    for locale in ("uz_Latn", "uz_Cyrl"):
        assert "nplurals=2" in _po_path(locale).read_text(encoding="utf-8"), locale


def test_compiled_catalog_exists_for_every_locale() -> None:
    """`pybabel` kompilyatsiyasi uchala locale uchun ham `.mo` beradi.

    ⚠ Kompilyatsiya SHU TESTDA qayta bajariladi (idempotent): shunda
      da'vo «kimdir bir marta qurgan artefakt» ni emas, KATALOGNING
      kompilyatsiya qilinishini o'lchaydi — buzilgan `.po` shu yerda
      istisno beradi.
    """
    assert compile_catalogues() == SUPPORTED_LOCALES
    for locale in SUPPORTED_LOCALES:
        mo_path = _po_path(locale).with_suffix(".mo")
        assert mo_path.is_file(), mo_path
        assert mo_path.stat().st_size > 0, mo_path


# ---------------------------------------------------------------------------
# ⛔ D-26(a) — MATN REYESTR HAQIDA GAPIRMAYDI
# ---------------------------------------------------------------------------


def test_the_binding_flow_never_mentions_a_registry() -> None:
    """⛔ `/start` va bog'lanish matnlarida «ro'yxat/reyestr/список» YO'Q.

    «Bozor reyestrida bo'lsangiz raqamingizni ulashing» degan matn
    javobning O'ZINI reyestrni tashqaridan tekshirish yo'liga
    aylantirardi (D-26a).
    """
    scanned = 0
    problems: list[str] = []
    for locale in SUPPORTED_LOCALES:
        for msgid, msgstr in _entries(locale):
            if not msgid.startswith(BINDING_KEY_PREFIXES):
                continue
            scanned += 1
            lowered = msgstr.lower()
            problems.extend(
                f"{locale}: {msgid} -> «{word}»" for word in REGISTRY_WORDS if word in lowered
            )

    # ⛔ QUYI CHEGARA: kalit prefikslari o'zgarsa sikl bo'sh to'plam
    #    ustida aylanib JIMGINA yashil bo'lardi.
    assert scanned >= 9, f"atigi {scanned} matn skanerlandi (3 kalit x 3 locale kutilgan)"
    assert problems == [], "bog'lanish matni reyestr haqida gapiryapti (D-26a):\n  " + "\n  ".join(
        problems
    )


def test_the_registry_word_detector_actually_catches_something() -> None:
    """⛔ NAZORAT: predikat sun'iy ijobiy satrni USHLAYDI.

    Usiz yuqoridagi test detektorning ishlayotganini emas, faqat uning
    JIM ekanini isbotlardi.
    """
    planted = "Bozor ro'yxatida bo'lsangiz raqamingizni ulashing".lower()
    assert [word for word in REGISTRY_WORDS if word in planted] == ["ro'yxat"]
    clean = "Raqamingizni ulashing".lower()
    assert [word for word in REGISTRY_WORDS if word in clean] == []
