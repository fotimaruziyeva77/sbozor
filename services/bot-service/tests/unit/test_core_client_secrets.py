"""D-04 ning bot tomondagi darvozasi — ISTISNO MATNI HECH QAYERGA YOZILMAYDI.

=============================================================================
⛔⛔ NEGA GREP EMAS, `ast`.

Bu darvoza taqiqlaydigan konstruksiyalarning NOMLARI (str(exc), repr(exc),
f-string ichidagi istisno) taqiqning O'ZINI tushuntirish uchun izohlarda
va docstringlarda YOZILISHI SHART — aks holda keyingi ishlovchi qoidani
`07-RESEARCH.md` dan qidirib yurardi.

Sodda `grep` bu ikkisini AJRATMAYDI: u izohdagi tushuntirishni ham
qizartirardi va yagona «tuzatish» yo'li SABABNI O'CHIRISH bo'lardi. Bu
sinf 02-23 da, so'ng 03-07 va 07-02 da qayta-qayta uchragan.

`ast` esa BAJARILADIGAN kodni ko'radi: docstring `ast.Constant`, izoh
umuman tugun emas. Shuning uchun ikkinchi nazorat testi
(`test_docstring_mentioning_the_ban_stays_green`) MAJBURIY — u aynan shu
farqni o'lchaydi.

=============================================================================
⛔ SKANER MAYDONI: `app/core_client.py` VA `app/handlers/*.py`.

Handlerlar ATAYIN qamralgan: D-04 ning ikkinchi yarmi «istisno matni
FOYDALANUVCHIGA ko'rsatilmaydi» degani. Handler `await message.answer(
str(exc))` yozsa, sir jurnalga emas, TELEGRAM CHATIGA chiqardi — va
undan qaytarib bo'lmasdi.

=============================================================================
UCH TUGUN SINFI O'LCHANADI:

  (a) `ast.Call` — `str(...)` / `repr(...)` ning argumenti ISTISNO;
  (b) `ast.JoinedStr` — f-string ichidagi qiymat ISTISNO;
  (c) `log.*(...)` chaqiruvidagi `error_type=` argumenti AYNAN
      `type(exc).__name__` shaklida.

⚠ (c) IKKI TOMONLAMA: noto'g'ri shakl qizaradi VA to'g'ri shakl kamida
  bir marta UCHRASHI shart (`MIN_ERROR_TYPE_LOGS`). Quyi chegarasiz
  darvoza bo'sh to'plam ustida aylanib jimgina yashil bo'lardi — bu
  loyihada takroran topilgan sinf (§S-10).

=============================================================================
⛔ TO'RTINCHI QATLAM — XULQIY, MANBA EMAS.

Manba skani «token jurnalga yozilmaydi» ni ISBOTLAMAYDI: u faqat
ma'lum bir yozish YO'LINI yopadi. Shuning uchun quyida `httpx.
MockTransport` bilan HAQIQIY so'rov qilinadi va o'lchanadi:

  * token so'rov SARLAVHASIDA bor (ijobiy nazorat — usiz «yo'q»
    da'volari bo'sh to'plam ustida yashil bo'lardi);
  * token so'rov URL ida YO'Q;
  * token ko'tarilgan istisnoning matnida ham, `repr` ida ham YO'Q;
  * token jurnal chiqishida YO'Q.

⚠ Soket OCHILMAYDI: `MockTransport` so'rovni Python funksiyasiga
  yo'naltiradi, ya'ni darvoza tarmoqqa CHIQMAYDI.
=============================================================================
"""

from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import TYPE_CHECKING, Final

import httpx
import pytest
from pydantic import SecretStr

from app.core_client import CoreApiError, CoreClient

if TYPE_CHECKING:
    from collections.abc import Iterator

APP_ROOT: Final = Path(__file__).resolve().parents[2] / "app"
CORE_CLIENT_PATH: Final = APP_ROOT / "core_client.py"
HANDLERS_DIR: Final = APP_ROOT / "handlers"

EXCEPTION_NAMES: Final = frozenset({"exc", "error", "err", "e", "exception"})
"""Istisno o'zgaruvchisining KELISHILGAN nomlari.

⚠ Bu ro'yxat `ExceptHandler.name` bilan TO'LDIRILADI, ya'ni
  `except httpx.HTTPError as boom:` ham qamraladi. Ro'yxat yolg'iz
  qolsa yangi nom bilan yozilgan `str(boom)` darvozadan o'tib ketardi.
"""

STRINGIFIERS: Final = frozenset({"str", "repr", "format", "ascii"})

MIN_ERROR_TYPE_LOGS: Final = 1
"""⛔ QUYI CHEGARA — (c) bandi bo'sh to'plam ustida ishlamasin."""

MIN_SCANNED_FILES: Final = 2
"""`core_client.py` + kamida bitta handler. Skaner maydoni siljisa qizaradi."""

FAKE_TOKEN: Final = "bot-service-token-NOT-REAL-0123456789"
"""⚠ USKUNA, SIR EMAS: bu qiymat hech qanday muhitda haqiqiy emas va u
faqat «shu satr chiqishda uchraydimi?» savolini o'lchash uchun kerak."""


# ---------------------------------------------------------------------------
# Skaner — ⛔ MANBA MATNI USTIDA, FAYL USTIDA EMAS
# ---------------------------------------------------------------------------
#
# Funksiya `str` qabul qiladi va shu sababdan NAZORAT testlari sun'iy
# manbani AYNAN o'sha yo'ldan o'tkaza oladi. Fayl yo'lini qabul qilgan
# skanerni nazorat qilib bo'lmasdi: nazorat uchun diskka fayl yozish
# kerak bo'lardi va u darvozaning o'zidan boshqacha yo'ldan yurardi.


def _exception_names(tree: ast.AST) -> frozenset[str]:
    """Kelishilgan nomlar + shu modulning `except ... as X` nomlari."""
    caught = {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ExceptHandler) and node.name is not None
    }
    return EXCEPTION_NAMES | caught


def _is_exception_ref(node: ast.expr, names: frozenset[str]) -> bool:
    """`exc` va `exc.args` — ikkalasi ham istisnoga MUROJAAT."""
    while isinstance(node, ast.Attribute):
        node = node.value
    return isinstance(node, ast.Name) and node.id in names


def _is_type_name_of_exception(node: ast.expr, names: frozenset[str]) -> bool:
    """Tugun AYNAN `type(<istisno>).__name__` shaklidami?"""
    if not isinstance(node, ast.Attribute) or node.attr != "__name__":
        return False
    call = node.value
    if not isinstance(call, ast.Call) or not isinstance(call.func, ast.Name):
        return False
    if call.func.id != "type" or len(call.args) != 1:
        return False
    return _is_exception_ref(call.args[0], names)


def _is_log_call(node: ast.Call) -> bool:
    """`log.warning(...)` / `logger.error(...)` shaklidagi chaqiruv."""
    func = node.func
    return (
        isinstance(func, ast.Attribute)
        and isinstance(func.value, ast.Name)
        and (func.value.id in {"log", "logger", "logging"})
    )


def scan_source(source: str, *, label: str) -> list[str]:
    """Manbani D-04 bo'yicha skanerlaydi; buzilishlar ro'yxatini qaytaradi.

    ⛔ Bo'sh ro'yxat — «toza». Istisno KO'TARILMAYDI: chaqiruvchi bir
       necha faylning natijasini birlashtira olishi kerak, aks holda
       birinchi buzilish qolganlarini yashirardi.
    """
    tree = ast.parse(source)
    names = _exception_names(tree)
    problems: list[str] = []

    for node in ast.walk(tree):
        # (a) str(exc) / repr(exc) / format(exc) / ascii(exc)
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id in STRINGIFIERS
        ):
            for arg in node.args:
                if _is_exception_ref(arg, names):
                    problems.append(
                        f"{label}:{node.lineno} — `{node.func.id}(...)` argumenti ISTISNO (D-04)"
                    )
        # (b) f-string ichidagi istisno
        if isinstance(node, ast.JoinedStr):
            for value in node.values:
                if isinstance(value, ast.FormattedValue) and _is_exception_ref(value.value, names):
                    problems.append(f"{label}:{node.lineno} — f-string ichida ISTISNO (D-04)")
        # (c) log.*(..., error_type=...) AYNAN `type(exc).__name__`
        if isinstance(node, ast.Call) and _is_log_call(node):
            for keyword in node.keywords:
                if keyword.arg != "error_type":
                    continue
                if not _is_type_name_of_exception(keyword.value, names):
                    problems.append(
                        f"{label}:{node.lineno} — `error_type=` `type(exc).__name__` "
                        "SHAKLIDA EMAS (D-04)"
                    )

    return problems


def count_error_type_logs(source: str) -> int:
    """`log.*(..., error_type=type(exc).__name__)` chaqiruvlari soni."""
    tree = ast.parse(source)
    names = _exception_names(tree)
    total = 0
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and _is_log_call(node)):
            continue
        for keyword in node.keywords:
            if keyword.arg == "error_type" and _is_type_name_of_exception(keyword.value, names):
                total += 1
    return total


def count_secret_reads(source: str) -> int:
    """`.get_secret_value()` chaqiruvlari soni — sirga ochiq borish nuqtalari."""
    return sum(
        1
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "get_secret_value"
    )


def scanned_files() -> list[Path]:
    """`core_client.py` + barcha handlerlar (HOSILA ro'yxat, qo'lda emas).

    ⚠ Yangi handler fayli AVTOMATIK qamraladi — ro'yxatni yangilash
      esdan chiqmaydi (05-15 ning «hosila qamrov» darsi).
    """
    return [CORE_CLIENT_PATH, *sorted(HANDLERS_DIR.glob("*.py"))]


# ---------------------------------------------------------------------------
# QAMROV — hamma qolgan testning SHARTI
# ---------------------------------------------------------------------------


def test_the_scanned_set_is_not_empty() -> None:
    """Skaner maydoni mavjud va u kamida ikki fayldan iborat.

    Usiz quyidagi darvozalar BO'SH ro'yxat ustida aylanib jimgina yashil
    bo'lardi: fayl ko'chirilsa yoki katalog nomi o'zgarsa hech nima
    qizarmasdi.
    """
    files = scanned_files()
    assert len(files) >= MIN_SCANNED_FILES, f"skanerlangan fayllar: {files}"
    for path in files:
        assert path.is_file(), f"yo'q: {path}"


# ---------------------------------------------------------------------------
# ASOSIY DA'VOLAR
# ---------------------------------------------------------------------------


def test_core_client_never_stringifies_an_exception() -> None:
    """`app/core_client.py` da istisno MATNI umuman qurilmaydi (D-04)."""
    problems = scan_source(CORE_CLIENT_PATH.read_text(encoding="utf-8"), label="core_client.py")
    assert problems == [], "\n  ".join(["D-04 buzildi:", *problems])


def test_handlers_never_stringify_an_exception() -> None:
    """Handlerlarda ham istisno matni yo'q — u FOYDALANUVCHIGA chiqardi."""
    problems: list[str] = []
    for path in sorted(HANDLERS_DIR.glob("*.py")):
        problems.extend(scan_source(path.read_text(encoding="utf-8"), label=path.name))
    assert problems == [], "\n  ".join(["D-04 buzildi (handlerlar):", *problems])


def test_error_type_is_logged_as_the_type_name_at_least_once() -> None:
    """⛔ QUYI CHEGARA: (c) bandi haqiqatan bir narsani o'lchayapti."""
    count = count_error_type_logs(CORE_CLIENT_PATH.read_text(encoding="utf-8"))
    assert count >= MIN_ERROR_TYPE_LOGS, (
        "`log.*(..., error_type=type(exc).__name__)` chaqiruvi topilmadi — "
        "(c) bandi bo'sh to'plam ustida ishlayapti"
    )


def test_the_secret_is_read_in_exactly_one_place() -> None:
    """⛔ Sirga ochiq borish — `core_client.py` da AYNAN BIR, handlerda NOL.

    Ikkinchi o'qish nuqtasi paydo bo'lishi «token endi ikki yo'ldan
    chiqadi» degani va ikkinchi yo'l birinchisining darvozalarini
    (`__slots__`, `repr` siz saqlash) MEROS QILMASDI.
    """
    assert count_secret_reads(CORE_CLIENT_PATH.read_text(encoding="utf-8")) == 1
    for path in sorted(HANDLERS_DIR.glob("*.py")):
        assert count_secret_reads(path.read_text(encoding="utf-8")) == 0, path.name


# ---------------------------------------------------------------------------
# ⛔ NAZORAT — DARVOZANING O'ZI O'LCHANADI
# ---------------------------------------------------------------------------


def test_the_ast_gate_catches_a_planted_violation() -> None:
    """Sun'iy manbadagi uchala buzilish ham USHLANADI.

    Usiz yuqoridagi «toza» da'volari darvozaning ishlayotganini emas,
    faqat uning JIM ekanini isbotlardi.
    """
    planted = (
        "import structlog\n"
        "log = structlog.get_logger(__name__)\n"
        "def f() -> None:\n"
        "    try:\n"
        "        pass\n"
        "    except ValueError as exc:\n"
        "        log.warning('x', detail=str(exc))\n"
        "        log.warning('y', error_type=exc)\n"
        "        raise RuntimeError(f'boom: {exc}') from exc\n"
    )
    problems = scan_source(planted, label="planted")

    assert any("`str(...)`" in problem for problem in problems), problems
    assert any("f-string" in problem for problem in problems), problems
    assert any("error_type=" in problem for problem in problems), problems


def test_the_gate_catches_a_violation_under_a_renamed_exception() -> None:
    """`except ... as boom:` ham qamraladi — nomlar ro'yxati YOLG'IZ EMAS."""
    planted = (
        "def f() -> None:\n"
        "    try:\n"
        "        pass\n"
        "    except ValueError as boom:\n"
        "        raise RuntimeError(repr(boom)) from boom\n"
    )
    assert scan_source(planted, label="renamed") != []


def test_docstring_mentioning_the_ban_stays_green() -> None:
    """⛔ TAQIQNI TUSHUNTIRUVCHI DOCSTRING DARVOZADAN O'TADI.

    Bu testning butun mazmuni shu: darvoza `grep` EMAS. Agar u matn
    ustida ishlaganda, quyidagi manba qizarardi va yagona «tuzatish»
    yo'li sababni O'CHIRISH bo'lardi — ya'ni fayl qanchalik yaxshi
    hujjatlangan bo'lsa, shunchalik ko'p yolg'on-qizil bergan bo'lardi.
    """
    documented = (
        '"""Bu modulda `str(exc)` va `repr(exc)` TAQIQLANGAN.\n'
        "\n"
        'f-string ichida `{exc}` yozish ham taqiq — sabab D-04 da."""\n'
        "def f() -> None:\n"
        "    # Bu izohda ham `str(exc)` yozilgan va u ham o'tishi kerak.\n"
        "    return None\n"
    )
    assert scan_source(documented, label="documented") == []


def test_the_correct_shape_is_not_flagged() -> None:
    """SALBIY NAZORAT: to'g'ri yozilgan kod qizarmaydi."""
    correct = (
        "import structlog\n"
        "log = structlog.get_logger(__name__)\n"
        "def f() -> None:\n"
        "    try:\n"
        "        pass\n"
        "    except ValueError as exc:\n"
        "        log.warning('x', error_type=type(exc).__name__, status=None)\n"
    )
    assert scan_source(correct, label="correct") == []


# ---------------------------------------------------------------------------
# ⛔ XULQIY QATLAM — TOKEN SARLAVHADA, BOSHQA HECH QAYERDA
# ---------------------------------------------------------------------------


@pytest.fixture
def captured_requests() -> Iterator[list[httpx.Request]]:
    """Ushlab qolingan so'rovlar — ⛔ SOKET OCHILMAYDI."""
    yield []


async def _failing_client(
    recorded: list[httpx.Request],
    status_code: int,
    *,
    body: dict[str, object] | None = None,
    text: str | None = None,
) -> CoreClient:
    """`MockTransport` ustidagi klient — ⛔ SOKET OCHILMAYDI.

    ⚠ `body` / `text` 07-21 da qo'shildi (WR-01): `404` ning MA'NOSI endi
      javob TANASIDAN keladi, ya'ni darvoza tanani boshqara olishi shart.
      `text` esa JSON BO'LMAGAN javobni (nginx ning HTML `404` sahifasi)
      ifodalaydi.
    """

    def handler(request: httpx.Request) -> httpx.Response:
        recorded.append(request)
        if text is not None:
            return httpx.Response(status_code, text=text)
        return httpx.Response(status_code, json=body if body is not None else {"detail": "nope"})

    return CoreClient(
        base_url="http://core-api.invalid",
        token=SecretStr(FAKE_TOKEN),
        transport=httpx.MockTransport(handler),
    )


async def test_the_token_travels_in_the_header_and_never_in_the_url(
    captured_requests: list[httpx.Request],
) -> None:
    """⛔ IJOBIY + SALBIY nazorat bir testda.

    Faqat «URL da yo'q» ni tekshirish darvozani BO'SH qilardi: token
    umuman yuborilmasa ham u yashil bo'lardi. Shuning uchun avval
    tokenning HAQIQATAN sarlavhada ekani o'lchanadi.
    """
    client = await _failing_client(captured_requests, 500)
    with pytest.raises(CoreApiError):
        await client.vendor_summary(telegram_user_id=42)
    await client.aclose()

    (request,) = captured_requests
    assert request.headers["authorization"] == f"Bearer {FAKE_TOKEN}"
    assert FAKE_TOKEN not in str(request.url)
    assert FAKE_TOKEN not in request.url.query.decode()


async def test_the_token_is_absent_from_the_raised_error_and_the_log(
    captured_requests: list[httpx.Request],
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Token na istisno matnida, na jurnal chiqishida uchraydi (D-04)."""
    client = await _failing_client(captured_requests, 500)
    with pytest.raises(CoreApiError) as excinfo:
        await client.vendor_summary(telegram_user_id=42)
    await client.aclose()

    rendered = str(excinfo.value) + repr(excinfo.value)
    captured = capsys.readouterr()
    stream = captured.out + captured.err

    # Nazorat: jurnal HAQIQATAN yozildi (aks holda «yo'q» da'vosi bo'sh).
    assert "core_api_call_failed" in stream
    assert FAKE_TOKEN not in rendered
    assert FAKE_TOKEN not in stream
    # Uch fakt esa JOYIDA: amal, tur, status.
    assert "vendor_summary" in rendered
    assert "HTTPStatusError" in rendered
    assert "status=500" in rendered


async def test_a_not_bound_response_becomes_its_own_type(
    captured_requests: list[httpx.Request],
) -> None:
    """NOMLANGAN `404` — `NotBoundError`, ya'ni handler uni XATO deb ko'rsatmaydi.

    ⚠ TANA 07-21 da NOMLANDI (WR-01): ilgari bu yerda `{"detail": "nope"}`
      turardi va test HAMON yashil edi — aynan shu narsa nuqsonning O'ZI
      edi (har qanday `404` shu shoxga tushardi).
    """
    from app.core_client import NotBoundError

    client = await _failing_client(captured_requests, 404, body={"detail": "not_bound"})
    with pytest.raises(NotBoundError):
        await client.vendor_summary(telegram_user_id=42)
    await client.aclose()


@pytest.mark.parametrize(
    ("body", "text", "label"),
    [
        ({"detail": "Not Found"}, None, "FastAPI ning standart marshrutsiz javobi"),
        ({}, None, "detali umuman yo'q JSON"),
        (None, "<html><body>404 Not Found</body></html>", "nginx ning HTML sahifasi"),
        (None, "", "bo'sh tana"),
    ],
)
async def test_an_unnamed_404_is_a_plain_error_not_a_not_bound_state(
    captured_requests: list[httpx.Request],
    body: dict[str, object] | None,
    text: str | None,
    label: str,
) -> None:
    """⛔⛔ WR-01 — NOTO'G'RI SOZLANGAN `CORE_API_URL` «BOG'LANMAGANSIZ» BERMAYDI.

    =========================================================================
    ⛔ NUQSONNING OQIBATI FOYDALANUVCHI TOMONIDA O'LCHANADI, KODDA EMAS.

    `start.py:97-98` ochiq taqiqlaydi: sotuvchiga «siz bog'lanmagansiz»
    deyish FAQAT reyestr haqiqatan javob berganda mumkin. Ilgari HAR
    QANDAY `404` shu xulosaga olib borardi, ya'ni:

      * `CORE_API_URL` noto'g'ri sozlangan,
      * `/internal/bot/*` prefiksi o'zgargan,
      * oradagi proxy HTML `404` sahifasi qaytargan

    uchala holatda ham sotuvchi kontakt tugmasini KO'RARDI, raqamini
    QAYTA yuborardi va natija O'ZGARMASDI — infratuzilma nosozligi
    UNING nuqsoni bo'lib ko'rinardi.

    ⛔ `NotBoundError` — `CoreApiError` NING AVLODI, ya'ni «`CoreApiError`
       ko'tarildimi?» degan sodda tekshiruv ikkala shoxda ham yashil
       bo'lardi. Shuning uchun da'vo TURNI AYNIQ solishtiradi
       (`type(...) is CoreApiError`), a'zolik bilan emas.
    =========================================================================
    """
    from app.core_client import NotBoundError

    client = await _failing_client(captured_requests, 404, body=body, text=text)
    with pytest.raises(CoreApiError) as excinfo:
        await client.vendor_summary(telegram_user_id=42)
    await client.aclose()

    assert not isinstance(excinfo.value, NotBoundError), (
        f"{label}: `404` «bog'lanmagansiz» ga aylandi — sotuvchi infratuzilma "
        "nosozligini O'Z nuqsoni deb ko'rardi (WR-01)"
    )
    assert type(excinfo.value) is CoreApiError, f"{label}: kutilmagan tur {type(excinfo.value)}"


async def test_the_response_detail_never_reaches_the_log_or_the_error(
    captured_requests: list[httpx.Request],
    capsys: pytest.CaptureFixture[str],
) -> None:
    """⛔ D-04 — javob tanasidagi `detail` FAQAT TENGLIK uchun o'qiladi.

    ⚠ Manba skani (yuqoridagi `ast` darvozasi) bu da'voni BAJARA
      OLMAYDI: u istisno OBYEKTINI kuzatadi, `detail` esa oddiy satr.
      Shuning uchun bu qatlam XULQIY — javobga o'ziga xos «marker» satr
      qo'yiladi va u jurnal chiqishida ham, istisno matnida ham
      qidiriladi.
    """
    marker = "MARKER-DETAIL-SHOULD-NEVER-BE-ECHOED"
    client = await _failing_client(captured_requests, 404, body={"detail": marker})
    with pytest.raises(CoreApiError) as excinfo:
        await client.vendor_summary(telegram_user_id=42)
    await client.aclose()

    rendered = str(excinfo.value) + repr(excinfo.value)
    stream = capsys.readouterr()
    combined = stream.out + stream.err

    # Nazorat: jurnal HAQIQATAN yozildi (aks holda «yo'q» da'vosi bo'sh).
    assert "core_api_call_failed" in combined
    assert marker not in rendered, "javob detali istisno matniga tushdi (D-04)"
    assert marker not in combined, "javob detali jurnalga tushdi (D-04)"


async def test_the_phone_number_never_reaches_the_url(
    captured_requests: list[httpx.Request],
) -> None:
    """⛔ SHAXSIY MA'LUMOT SO'ROV TANASIDA, URL DA EMAS.

    URL jurnalga, proxy'ga va `httpx` istisno matniga tushadi — telefon
    esa O'zR qonuni ostidagi shaxsiy ma'lumot. Tanada esa u faqat
    `core-api` ga boradi va u yerda ham SAQLANMAYDI (07-08:
    `NO_MATCH` shoxida telefon hech qayerga yozilmaydi).
    """
    phone = "+998901234567"

    def handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        return httpx.Response(200, json={"status": "no_match", "vendor": None})

    client = CoreClient(
        base_url="http://core-api.invalid",
        token=SecretStr(FAKE_TOKEN),
        transport=httpx.MockTransport(handler),
    )
    result = await client.resolve(telegram_user_id=42, raw_phone=phone)
    await client.aclose()

    (request,) = captured_requests
    assert phone not in str(request.url)
    # Nazorat: raqam HAQIQATAN yuborildi — tanada.
    assert json.loads(request.content)["phone"] == phone
    assert result.status == "no_match"
