"""⛔ G7-4 — bot tokeni istisno MATNI orqali siza olmasligining AST darvozasi.

=============================================================================
QOIDA: `str(<istisno>)`, `repr(<istisno>)` VA `f"...{<istisno>}..."` — NOL.

Telegram Bot API ning shakli:

    POST https://api.telegram.org/bot<SIR>/sendMessage
                                  ^^^^^^^ maxfiy qiymat AYNAN shu yerda

`httpx` istisnosining MATNI to'liq so'rov URL'ini o'z ichiga oladi, ya'ni
bitta interpolyatsiya sirni jurnalga, jurnaldan Sentry'ga va
`notification_outbox.last_error_type` USTUNIGA olib chiqardi — u yerdan esa
`pg_dump` -> restic -> TASHQI BUCKET zanjiriga. Bu 3-fazada `go2rtc.py` da
HAQIQATAN sodir bo'lgan yo'lning aynan takrori, faqat boshqa protokolda.
=============================================================================

=============================================================================
⛔⛔ DARVOZA AST BILAN, GREP BILAN EMAS — VA BU TANLOV EMAS, ZARURAT.

Ikkala skanerlanadigan modul ham taqiqni SO'Z BILAN tushuntiradi:
docstringlarda «istisno matni yozilmaydi» degan jumla bor va u yerda
taqiqning O'ZI misol sifatida keltiriladi. Matn darvozasi izohni koddan
AJRATMAYDI, ya'ni:

    taqiqni tushuntirish -> darvoza qizaradi
    -> yagona «tuzatish» yo'li: darvozaga ISTISNO qo'shish
    -> darvoza sekin-asta teshikka aylanadi

Bu 02-23 va 03-07 da ikki marta o'lchangan dars. AST esa docstringni
`ast.Constant` deb ko'radi va u UMUMAN tekshirilmaydi — ya'ni taqiqni
tushuntirish darvozani KUCHSIZLANTIRMAYDI.

⚠ FARQNING O'ZI HAM O'LCHANADI:
  `test_docstring_mentioning_the_ban_stays_green` — docstringda taqiq
  yozilgan sun'iy manba darvozadan O'TADI. Grepga qaytilsa aynan shu test
  qizaradi.
=============================================================================

UCH QOIDA VA UCHALASI HAM MAJBURIY:

  1. `str(exc)` / `repr(exc)` — istisno o'zgaruvchisi ustida CHAQIRUV;
  2. `f"...{exc}..."` — istisno o'zgaruvchisining INTERPOLYATSIYASI;
  3. `error_type=` kalit argumenti — ⛔ FAQAT `type(exc).__name__`,
     `<Sinf>.__name__` yoki sirsiz tashuvchining `.error_type` maydoni.

⚠ 3-QOIDA IKKINCHI IKKISIDAN FARQ QILADI: u taqiqni emas, TALABNI
  o'lchaydi. Sabab yo'lda: 1- va 2-qoidalar `str(exc)` ni to'sadi, lekin
  `error_type=telegram_url` yoki `error_type=body["description"]` shaklidagi
  qiymatni KO'RMASDI — holbuki ustunga tushadigan narsa aynan o'sha.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

SCANNED_MODULES: tuple[Path, ...] = (
    REPO_ROOT / "services" / "core-api" / "app" / "jobs" / "outbox.py",
    REPO_ROOT / "services" / "core-api" / "app" / "services" / "alerts.py",
)
"""⛔ IKKALA MODUL HAM: sirni QURADIGAN joy (`alerts.py`) va uni USTUNGA
yozadigan joy (`outbox.py`). Bittasini tekshirish ikkinchisini ochiq
qoldirardi."""

MIN_SCANNED_CALLS = 20
"""Har bir modulda kutiladigan eng kam `ast.Call` tugunlari soni.

Quyi chegara MAJBURIY (03-01 qoidasi): yo'l eskirganda yoki fayl bo'sh
bo'lganda `ast.walk()` hech nima topmasdi va «taqiq buzilmagan» da'vosi
JIMGINA yashil bo'lardi.
"""

SUSPECT_NAMES: frozenset[str] = frozenset({"exc", "error", "err", "e", "exception", "cause"})
"""Istisno o'zgaruvchisining ODATIY nomlari.

⚠ RO'YXAT `ExceptHandler.name` LARI BILAN BIRLASHTIRILADI, ularning
  o'rnini bosmaydi: modul `except HTTPError as boom:` deb yozsa `boom`
  ham AVTOMATIK qo'shiladi. Ro'yxatning o'zi esa `except` blokidan
  TASHQARIDA yashaydigan istisnoni (masalan argument sifatida uzatilgan
  `exc`) qoplaydi — `_swallow(result, event, exc, ...)` aynan shunday.
"""

ALLOWED_ERROR_TYPE_ATTRS: frozenset[str] = frozenset({"__name__", "error_type"})
"""`error_type=` ga ruxsat etilgan YAGONA ikki shakl.

  * `type(exc).__name__` / `<Sinf>.__name__` — tur nomi, ta'rifi bo'yicha
    sirsiz: u manba kodidagi identifikator va so'rov haqida hech nima
    bilmaydi;
  * `<tashuvchi>.error_type` — `SendFailure` / `OutboxFailure` ning
    maydoni. U O'Z navbatida `type(exc).__name__` dan yig'iladi va o'sha
    yig'ilish joyi AYNAN SHU QOIDA bilan tekshiriladi, ya'ni zanjir
    yopiq.

⛔ QOLGAN HAMMASI RAD ETILADI, jumladan LITERAL satr: qotirilgan
   `error_type="HTTPStatusError"` sirsiz bo'lardi, lekin u haqiqiy turni
   YASHIRARDI va diagnostikani yolg'onga aylantirardi.
"""


def _exception_names(tree: ast.Module) -> frozenset[str]:
    """`SUSPECT_NAMES` + shu moduldagi HAR BIR `except ... as <nom>`."""
    bound = {
        node.name for node in ast.walk(tree) if isinstance(node, ast.ExceptHandler) and node.name
    }
    return SUSPECT_NAMES | bound


def _is_allowed_error_type(node: ast.expr) -> bool:
    """`error_type=` ning qiymati ruxsat etilgan SHAKLDAMI (3-qoida)."""
    return isinstance(node, ast.Attribute) and node.attr in ALLOWED_ERROR_TYPE_ATTRS


def violations(source: str, label: str) -> list[str]:
    """Uchala qoidaning buzilishlarini AST bo'ylab topadi.

    ⚠ FUNKSIYA OMMAVIY VA SUN'IY MANBADA HAM CHAQIRILADI: nazorat
      testlari aynan SHU predikatni o'lchaydi. Ikkinchi, «test uchun»
      nusxa yozilsa nazorat mahsulot darvozasini emas, o'z nusxasini
      tekshirgan bo'lardi (5-fazaning W-2 darsi).
    """
    tree = ast.parse(source)
    suspects = _exception_names(tree)
    found: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            _check_call(node, suspects=suspects, label=label, found=found)
        elif isinstance(node, ast.JoinedStr):
            _check_fstring(node, suspects=suspects, label=label, found=found)

    return found


def _check_call(node: ast.Call, *, suspects: frozenset[str], label: str, found: list[str]) -> None:
    """1- va 3-qoida: `str(exc)`/`repr(exc)` va `error_type=` ning shakli."""
    if isinstance(node.func, ast.Name) and node.func.id in {"str", "repr"}:
        for argument in node.args:
            if isinstance(argument, ast.Name) and argument.id in suspects:
                found.append(
                    f"{label}:{node.lineno}: `{node.func.id}({argument.id})` — istisno "
                    "MATNI so'rov URL'ini, ya'ni bot tokenini tashiydi (D-04)"
                )

    for keyword in node.keywords:
        if keyword.arg == "error_type" and not _is_allowed_error_type(keyword.value):
            found.append(
                f"{label}:{keyword.value.lineno}: `error_type=` qiymati "
                f"`{ast.dump(keyword.value)[:60]}` — ruxsat etilgani faqat "
                f"{sorted(ALLOWED_ERROR_TYPE_ATTRS)} shakllari"
            )


def _check_fstring(
    node: ast.JoinedStr, *, suspects: frozenset[str], label: str, found: list[str]
) -> None:
    """2-qoida: f-string ichida istisno o'zgaruvchisining O'ZI."""
    for value in node.values:
        if (
            isinstance(value, ast.FormattedValue)
            and isinstance(value.value, ast.Name)
            and value.value.id in suspects
        ):
            found.append(
                f"{label}:{node.lineno}: f-string ichida `{{{value.value.id}}}` — "
                "interpolyatsiya `str()` ning yashirin shakli (D-04)"
            )


def _sources() -> dict[str, str]:
    return {
        path.relative_to(REPO_ROOT).as_posix(): path.read_text(encoding="utf-8")
        for path in SCANNED_MODULES
    }


SOURCES = _sources()


def test_the_scanned_modules_are_actually_parsed() -> None:
    """Quyi chegara: AST bo'sh daraxtda ishlayotgan bo'lsa darvoza YO'Q."""
    for label, source in SOURCES.items():
        tree = ast.parse(source)
        calls = sum(1 for node in ast.walk(tree) if isinstance(node, ast.Call))
        assert calls >= MIN_SCANNED_CALLS, (
            f"`{label}` da faqat {calls} ta chaqiruv topildi (kamida "
            f"{MIN_SCANNED_CALLS} kutilgan) — yo'l eskirgan bo'lsa bu darvoza "
            "BO'SH daraxtda yashil bo'lib turaverardi."
        )


def test_the_handler_names_are_actually_collected() -> None:
    """⛔ NAZORAT: skaner `except ... as <nom>` ni RO'YXATDAN TASHQARI nom uchun topadi.

    =======================================================================
    ⚠ NEGA DA'VO SUN'IY MANBADA, MAHSULOTDA EMAS — VA BU O'LCHANDI.

    Birinchi shaklda bu test mahsulot modullaridan yig'ilgan nomlar
    `SUSPECT_NAMES` dan ORTIQ bo'lishini talab qilardi va u QIZARDI:
    ikkala modul ham istisnoni `exc` deb ataydi, ya'ni nom ALLAQACHON
    ro'yxatda. Ya'ni o'sha da'vo skanerni emas, mahsulotdagi
    O'ZGARUVCHI NOMLARI TANLOVINI o'lchagan bo'lardi — va u kimdir
    `except ... as error:` deb yozgan kuni sababsiz qizarardi.

    Shuning uchun mexanizm AYNAN u kerak bo'ladigan holatda o'lchanadi:
    ro'yxatda YO'Q nom. Mahsulotda `except` blokining MAVJUDLIGI esa
    alohida, sanoq bilan qulflanadi (pastda).
    =======================================================================
    """
    exotic = "\n".join(
        (
            "def f(log):",
            "    try:",
            "        pass",
            "    except Exception as boom:",
            "        log.warning('x', detail=str(boom))",
            "",
        )
    )

    names = _exception_names(ast.parse(exotic))
    assert "boom" in names, (
        f"`except ... as boom:` yig'ilmadi: {sorted(names)}. Usiz ro'yxatdagi "
        "nomlardan boshqacha atalgan istisno tekshiruvdan JIMGINA chetlab o'tardi."
    )
    assert violations(exotic, "exotic.py"), (
        "ro'yxatdan tashqari nomdagi istisnoning `str()` i ushlanmadi — nomlarni "
        "yig'ish ishlayapti, lekin predikat ularni ISHLATMAYAPTI"
    )

    def _handler_count(source: str) -> int:
        return sum(1 for node in ast.walk(ast.parse(source)) if isinstance(node, ast.ExceptHandler))

    handlers = {label: _handler_count(source) for label, source in SOURCES.items()}
    assert all(count > 0 for count in handlers.values()), (
        f"skanerlanadigan modulda birorta `except` bloki topilmadi: {handlers}. "
        "Ikkala modul ham istisno tutadi, ya'ni bu natija yo'l eskirganini "
        "bildiradi."
    )


@pytest.mark.parametrize("label", sorted(SOURCES))
def test_no_exception_text_leaves_the_scanned_modules(label: str) -> None:
    """⛔ G7-4 — uchala qoida ham skanerlanadigan modullarda BUZILMAGAN."""
    found = violations(SOURCES[label], label)

    assert not found, (
        "⛔ ISTISNO MATNI SIZISH YO'LI TOPILDI:\n  "
        + "\n  ".join(found)
        + "\n\nTelegram Bot API ning URL'i BOT TOKENINI tashiydi va `httpx` "
        "istisnosining matni to'liq URL'ni o'z ichiga oladi. Bitta "
        "interpolyatsiya sirni jurnalga, Sentry'ga va `last_error_type` "
        "USTUNIGA — u yerdan esa `pg_dump` -> restic -> TASHQI BUCKET ga "
        "olib chiqardi (D-04)."
    )


def test_the_ast_gate_catches_a_planted_violation() -> None:
    """⛔ NAZORAT — darvoza ATAYIN EKILGAN buzilishda YIQILADI.

    Bu darvoza loyihasi bo'yicha har doim yashil, ya'ni yashil rang uning
    ishlayotganini isbotlamaydi. Nazoratsiz noto'g'ri yozilgan vizitor
    (masalan `ast.walk` o'rniga faqat modul darajasidagi tugunlarni
    ko'radigan sikl) MANGU yashil qolardi.

    ⚠ UCHALA QOIDA HAM ALOHIDA EKILADI — bittasini o'lchash qolgan
      ikkitasi buzuq bo'lgan holatni ham yashil qoldirardi.
    """
    planted = "\n".join(
        (
            "def leak(log, outbox_repo, session):",
            "    try:",
            "        pass",
            "    except Exception as exc:",
            "        log.warning('x', detail=str(exc))",
            "        log.warning('y', detail=f'boom {exc}')",
            "        outbox_repo.mark_failed(session, error_type=repr(exc))",
            "",
        )
    )

    found = violations(planted, "planted.py")

    assert len(found) >= 4, f"ekilgan uchala buzilish ham ushlanmadi: {found}"
    assert any("str(exc)" in line for line in found), f"1-qoida ishlamadi: {found}"
    assert any("f-string" in line for line in found), f"2-qoida ishlamadi: {found}"
    assert any("error_type=" in line for line in found), f"3-qoida ishlamadi: {found}"


def test_docstring_mentioning_the_ban_stays_green() -> None:
    """⛔ IKKINCHI NAZORAT — AST NING GREPDAN FARQI AYNAN SHU YERDA O'LCHANADI.

    Docstringda taqiqning O'ZI misol sifatida yozilgan sun'iy manba
    darvozadan O'TISHI SHART. Grepga qaytilsa bu test QIZARADI va sabab
    darhol ko'rinadi — ya'ni «matn darvozasiga qaytamiz» qarori jimgina
    qabul qilinmaydi.

    ⚠ MAHSULOT KODIDA AYNAN SHU HOLAT BOR: ikkala skanerlanadigan modul
      ham taqiqni docstringda tushuntiradi.
    """
    documented = "\n".join(
        (
            '"""Taqiq: `str(exc)` va `repr(exc)` bu modulda YOZILMAYDI."""',
            "",
            "def safe(log):",
            '    """Ichkarida ham f\'{exc}\' shakli TAQIQLANGAN."""',
            "    try:",
            "        pass",
            "    except Exception as exc:",
            "        log.warning('x', error_type=type(exc).__name__)",
            "",
        )
    )

    found = violations(documented, "documented.py")

    assert found == [], (
        f"docstringdagi taqiq TUSHUNTIRISHI darvozani qizartirdi: {found}. Bu "
        "aynan 02-23/03-07 ning o'lchangan xatosi: matn darvozasi izohni koddan "
        "ajratmaydi va yagona «tuzatish» yo'li darvozaga istisno qo'shish bo'lardi."
    )


def test_the_carrier_field_shape_is_accepted() -> None:
    """`<tashuvchi>.error_type` shakli O'TADI — 3-qoidaning ikkinchi yarmi.

    Usiz `outbox.py` ning HAR BIR holat yozuvi qizarardi va yagona chiqish
    yo'li istisnoni repozitoriygacha OLIB BORISH bo'lardi — ya'ni darvoza
    aynan o'zi to'sishi kerak bo'lgan naqshni MAJBURLAB qo'yardi.
    """
    carrier = "\n".join(
        (
            "def settle(outbox_repo, session, outcome):",
            "    outbox_repo.reschedule(session, error_type=outcome.error_type)",
            "",
        )
    )

    assert violations(carrier, "carrier.py") == []
