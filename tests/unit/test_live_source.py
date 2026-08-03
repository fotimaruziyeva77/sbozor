"""Rekvizit bilan boyitilgan RTSP manbai — foizli kodlash DARVOZASI (T-03-88, D-12).

=============================================================================
BU FAYL IKKI XIL DA'VONI O'LCHAYDI VA ULARNI ARALASHTIRMASLIK MUHIM.

  (1) **SIR KO'RINMAYDI** — natija `SecretStr`, ya'ni `repr()` va `str()`
      parolning bo'lagini ham bermaydi. Bu KELISHUV emas, TIP: `03-04`
      sozlama maydonlarini aynan shu sababdan `SecretStr` qilgan
      (`BaseSettings.__repr__` har maydonni chop etadi, Sentry esa lokal
      o'zgaruvchilarni ushlaydi).

  (2) **MANZIL O'ZGARMAYDI** — parolda `@` yoki `/` bo'lsa ham hosil
      bo'lgan URL'ning xosti, porti va yo'li KIRISHDAGI bilan aynan bir
      xil qoladi. Bu «ozodalik» emas, XAVFSIZLIK NAZORATI: bazaga parolni
      ADMIN kiritadi va `pa@evil.example/` shaklidagi qiymat foizli
      kodlash bo'lmasa go2rtc'ni BUTUNLAY BOSHQA xostga ulantirardi —
      ya'ni SSRF (T-03-88).
=============================================================================

⚠ `rtsp_url()` NING IMZOSI BU YERDA O'ZGARMAYDI (T-03-24).

Sirni saqlanadigan/serializatsiya qilinadigan URL'dan chiqarish qarori
TO'G'RI va u `tests/unit/test_rtsp_url.py` da o'z darvozasi bilan turadi.
Shu modul o'sha qarorning MOS KELADIGAN IKKINCHI YARMI: rekvizit
go2rtc'ga faqat SHU YERDA, faqat chiqish paytida qo'shiladi va u
`SecretStr` ichida tashiladi.
"""

from __future__ import annotations

import inspect
from urllib.parse import quote, urlsplit

import pytest
from app.services import live_source
from app.services.go2rtc import assert_safe_go2rtc_src
from app.services.live_source import (
    CREDENTIAL_INJECTION,
    EMPTY_CREDENTIAL,
    NOT_AN_RTSP_SOURCE,
    SOURCE_ALREADY_AUTHENTICATED,
    authenticated_rtsp_source,
)
from pydantic import SecretStr

SOURCE = "rtsp://nvr.invalid:554/Streaming/Channels/102"
"""Mahsulot yo'lidagi HAQIQIY shakl — `rtsp_url()` ning chiqishi."""

USERNAME = "sbozor"
PASSWORD = "Parol12345"

HOST = "nvr.invalid"
PORT = 554
PATH = "/Streaming/Channels/102"


def _parts(secret: SecretStr) -> tuple[str | None, int | None, str]:
    """Natijaning xosti, porti va yo'li — UCHALASI BIRGA.

    ⚠ Uchalasi bitta yordamchidan olinadi va har inyeksiya testida BIRGA
      tekshiriladi. Faqat xostni tekshirish yetarli emas: slesh bo'lgan
      parol xostni saqlab, YO'L chegarasini siljitardi; faqat yo'lni
      tekshirish esa `@` bo'lgan parolning xost almashtirishini
      o'tkazib yuborardi.
    """
    parsed = urlsplit(secret.get_secret_value())
    return parsed.hostname, parsed.port, parsed.path


# ---------------------------------------------------------------------------
# Muvaffaqiyat yo'li
# ---------------------------------------------------------------------------


def test_credentials_are_attached_to_the_source() -> None:
    """Oddiy rekvizit `user:pass@` bo'limiga aylanadi.

    IJOBIY HOLAT MAJBURIY: usiz funksiyani `raise ValueError` bilan
    almashtirib qo'yish mumkin edi va barcha rad etish testlari yashil
    qolardi — jonli ko'rish esa umuman ishlamasdi.
    """
    result = authenticated_rtsp_source(SOURCE, USERNAME, PASSWORD)

    assert isinstance(result, SecretStr)
    assert result.get_secret_value() == f"rtsp://{USERNAME}:{PASSWORD}@{HOST}:{PORT}{PATH}"


def test_result_still_passes_the_go2rtc_allow_list() -> None:
    """Rekvizitli manba HAM `rtsp://` bilan boshlanadi (T-03-92).

    ⚠ ALLOW-LIST BU YERDA QAYTA TASDIQLANADI. `assert_safe_go2rtc_src`
      prefiksni `strip`/`lower` siz solishtiradi, ya'ni rekvizit oyog'i
      sxemadan OLDIN birorta belgi qo'shib qo'ysa (masalan bo'shliq yoki
      `//`) darvoza go2rtc'ga chiqish yo'lida yopilardi va sabab
      «jonli ko'rish ishlamayapti» bo'lib ko'rinardi.
    """
    result = authenticated_rtsp_source(SOURCE, USERNAME, PASSWORD)

    assert_safe_go2rtc_src(result.get_secret_value())


def test_query_and_fragment_survive_untouched() -> None:
    """`?` va `#` bo'lgan manba ham buzilmaydi.

    Bugungi `rtsp_url()` query bermaydi, LEKIN funksiya umumiy URL ustida
    ishlaydi va kelajakdagi `?transport=tcp` shaklidagi qo'shimchani
    jimgina yo'qotmasligi kerak.
    """
    source = f"rtsp://{HOST}:{PORT}{PATH}?transport=tcp#a"

    result = authenticated_rtsp_source(source, USERNAME, PASSWORD)

    parsed = urlsplit(result.get_secret_value())
    assert parsed.query == "transport=tcp"
    assert parsed.fragment == "a"
    assert (parsed.hostname, parsed.port, parsed.path) == (HOST, PORT, PATH)


# ---------------------------------------------------------------------------
# INYEKSIYA — foizli kodlash MAJBURIY (T-03-88)
# ---------------------------------------------------------------------------


def test_password_with_slash_at_and_colon_keeps_the_authority_and_path() -> None:
    """Parolda `@`, `/` va `:` BIRGA bo'lsa ham xost/port/yo'l o'zgarmaydi.

    ⚠ UCHALASI BIR PAROLDA ATAYIN. Ular UCH XIL chegarani siljitadi:
      `@` — avtoritet ajratuvchisi (xost almashadi), `/` — yo'l boshlanishi,
      `:` — port ajratuvchisi. Har birini alohida sinash bittasi
      kodlanmay qolgan holatni o'tkazib yuborardi.

    ⚠ SABOTAJ NISHONI (S1): `quote(password, safe="")` -> `quote(password)`
      qilinganda slesh KODLANMAY qoladi va yo'l chegarasi siljiydi.
    """
    password = "pa@ss/word:9000"  # noqa: S105 - test uskunasi

    result = authenticated_rtsp_source(SOURCE, USERNAME, password)

    assert _parts(result) == (HOST, PORT, PATH)


def test_password_shaped_like_an_authority_cannot_redirect_the_stream() -> None:
    """`pa@evil.example/` PAROLI oqimni boshqa xostga BURA OLMAYDI (SSRF).

    ⚠ BU TESTNING DA'VOSI XAVFSIZLIK, FORMATLASH EMAS. Kodlanmagan holda
      hosil bo'ladigan satr `rtsp://sbozor:pa@evil.example/@nvr.invalid...`
      bo'lardi va uni `urlsplit` `evil.example` xosti deb o'qirdi —
      go2rtc esa hujumchining serveriga ulanib, RTSP rekvizitini o'sha
      yerga TAQDIM ETARDI (T-03-88).
    """
    password = "pa@evil.example/"  # noqa: S105 - test uskunasi

    result = authenticated_rtsp_source(SOURCE, USERNAME, password)

    host, port, path = _parts(result)
    assert host == HOST, "parol xostni qayta yozdi — bu SSRF (T-03-88)"
    assert (port, path) == (PORT, PATH)


def test_percent_sign_in_the_password_is_encoded_too() -> None:
    """`%` ning O'ZI ham kodlanadi — aks holda ikki marta dekodlash tug'ilardi.

    Parol `%40` bo'lsa va `%` kodlanmasa, go2rtc uni `@` deb dekodlab
    yuborardi: ya'ni parol JIMGINA boshqa qiymatga aylanib, ulanish
    401 olardi va sabab «NVR rad etdi» bo'lib ko'rinardi.
    """
    password = "%40%2F"  # noqa: S105 - test uskunasi

    result = authenticated_rtsp_source(SOURCE, USERNAME, password)

    assert "%2540" in result.get_secret_value()
    assert _parts(result) == (HOST, PORT, PATH)


def test_hash_and_question_mark_do_not_open_a_fragment_or_query() -> None:
    """`#` va `?` bo'lgan parol yo'ldan keyingi bo'limlarni ochmaydi."""
    password = "pa#ss?word"  # noqa: S105 - test uskunasi

    result = authenticated_rtsp_source(SOURCE, USERNAME, password)

    parsed = urlsplit(result.get_secret_value())
    assert parsed.query == ""
    assert parsed.fragment == ""
    assert (parsed.hostname, parsed.port, parsed.path) == (HOST, PORT, PATH)


def test_windows_domain_username_is_encoded() -> None:
    """`DOMAIN\\user` shaklidagi hisob ham buzilmaydi.

    Windows domenidagi NVR hisobi aynan shu shaklda keladi va `\\` URL'da
    ajratuvchi emas — LEKIN foydalanuvchi nomi kodlanmasa `@` yoki `/`
    bo'lgan hisob parol bilan bir xil sinf xatoni tug'dirardi.
    """
    result = authenticated_rtsp_source(SOURCE, "DOMAIN\\operator", PASSWORD)

    parsed = urlsplit(result.get_secret_value())
    assert parsed.username == "DOMAIN%5Coperator"
    assert (parsed.hostname, parsed.port, parsed.path) == (HOST, PORT, PATH)


def test_username_with_an_at_sign_is_encoded() -> None:
    """Foydalanuvchi nomidagi `@` ham avtoritetni siljita olmaydi."""
    result = authenticated_rtsp_source(SOURCE, "operator@nvr", PASSWORD)

    assert _parts(result) == (HOST, PORT, PATH)


def test_the_injection_guard_fires_when_encoding_is_bypassed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """DARVOZANING O'ZI o'lchanadi — kodlash chetlab o'tilganda `ValueError`.

    ⚠ BU TEST S1 SABOTAJINING DOIMIY SHAKLI. To'g'ri kodda darvoza HECH
      QACHON ishga tushmaydi, ya'ni «yashil» uning haqiqatan qidirayotganini
      isbotlamaydi (`test_no_sim_branching.py::test_gate_detects_a_planted_
      marker` bilan aynan bir xil mulohaza). Shuning uchun `quote` ayni shu
      modulda vaqtincha o'ziga-o'zi qaytaradigan funksiya bilan
      almashtiriladi va natija QAYTA AJRATIB o'lchanadi.

    Ya'ni darvoza kod o'qishdan emas, NATIJADAN tekshiriladi.
    """
    monkeypatch.setattr(live_source, "quote", lambda value, safe="": value)

    with pytest.raises(ValueError, match=CREDENTIAL_INJECTION):
        authenticated_rtsp_source(SOURCE, USERNAME, "pa@evil.example/")


# ---------------------------------------------------------------------------
# SIR KO'RINMAYDI (D-12)
# ---------------------------------------------------------------------------


def test_neither_repr_nor_str_shows_the_password() -> None:
    """`repr()` va `str()` da parolning OCHIQ MATNI yo'q.

    ⚠ IKKALASI HAM TEKSHIRILADI. `str()` odatiy formatlashda (`f"{value}"`),
      `repr()` esa istisno matnida, `pytest` diffida va Sentry ning lokal
      o'zgaruvchilar suratida chiqadi — ya'ni ikkinchisi birinchisidan
      ko'ra ehtimolli sizish yo'li.
    """
    secret = f"Maxfiy-{PASSWORD}"  # noqa: S105 - test uskunasi

    result = authenticated_rtsp_source(SOURCE, USERNAME, secret)

    assert secret not in repr(result)
    assert secret not in str(result)
    assert secret in result.get_secret_value(), (
        "sir umuman yo'qolgan — maskalanish tekshiruvi bo'sh qiymat ustida ishlagan bo'lardi"
    )


def test_error_messages_never_carry_the_rejected_value() -> None:
    """Rad etish matnida qiymatning O'ZI yo'q (`assert_safe_go2rtc_src` qoidasi).

    Rad etilgan qiymat ta'rifi bo'yicha ishonchsiz kirish va uni istisno
    matniga qo'yish log injection yuzasini ochardi — ustiga u yerdan
    jurnalga va Sentry'ga ketardi.
    """
    secret = "OchiqParol-1234"  # noqa: S105 - test uskunasi

    with pytest.raises(ValueError) as rejected:
        authenticated_rtsp_source("http://nvr.invalid/x", USERNAME, secret)

    assert secret not in str(rejected.value)
    assert "nvr.invalid" not in str(rejected.value)


# ---------------------------------------------------------------------------
# RAD ETISH YO'LLARI — HAR BIRI ALOHIDA (`test_jwt.py` qoidasi)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "source",
    [
        "http://nvr.invalid/snapshot.jpg",
        "exec:whoami",
        "ffmpeg:rtsp://nvr.invalid/x#video=copy",
        "rtsps://nvr.invalid:322/x",
        "",
    ],
)
def test_non_rtsp_source_is_rejected(source: str) -> None:
    """Sxemasi `rtsp` bo'lmagan manba RAD ETILADI.

    Funksiya `assert_safe_go2rtc_src` ning O'RNINI BOSMAYDI (u go2rtc'ga
    chiqishda baribir qo'llanadi), lekin darvoza IKKALA joyda ham bo'lishi
    kerak: bu yerdagi tekshiruv rekvizitning `exec:` satriga yopishtirilib,
    keyin allow-listga «rtsp bilan boshlanadi» bo'lib ko'rinishining oldini
    oladi.
    """
    with pytest.raises(ValueError, match=NOT_AN_RTSP_SOURCE):
        authenticated_rtsp_source(source, USERNAME, PASSWORD)


def test_source_that_already_carries_credentials_is_rejected() -> None:
    """Ikki marta boyitish RAD ETILADI.

    Jimgina o'tkazib yuborilsa natija `rtsp://a:b@c:d@host/...` bo'lardi:
    `urlsplit` oxirgi `@` ni ajratuvchi deb oladi, ya'ni HAQIQIY parol
    xost nomining bir bo'lagiga aylanib qolardi va ulanish tushunarsiz
    sabab bilan yiqilardi.
    """
    with pytest.raises(ValueError, match=SOURCE_ALREADY_AUTHENTICATED):
        authenticated_rtsp_source(f"rtsp://a:b@{HOST}:{PORT}{PATH}", USERNAME, PASSWORD)


def test_source_with_only_a_username_is_rejected_too() -> None:
    """Parolsiz `user@` bo'limi ham «allaqachon boyitilgan» hisoblanadi.

    NAZORAT HOLATI: tekshiruv faqat `password` ni ko'rsa, `rtsp://u@host/...`
    shakli o'tib ketardi va natijada IKKITA foydalanuvchi nomi qolardi.
    """
    with pytest.raises(ValueError, match=SOURCE_ALREADY_AUTHENTICATED):
        authenticated_rtsp_source(f"rtsp://u@{HOST}:{PORT}{PATH}", USERNAME, PASSWORD)


def test_empty_password_is_rejected() -> None:
    """Bo'sh parol RAD ETILADI — rekvizitsiz manba bu funksiyadan CHIQMAYDI.

    Rekvizitsiz yo'l `rtsp_url()` ning O'ZI. Bo'sh qiymatni «mayli, shunday
    yuboraveramiz» deb o'tkazish `rtsp://sbozor:@host/...` beradi va NVR
    401 qaytaradi — sabab esa «kamera ishlamayapti» bo'lib ko'rinardi.
    """
    with pytest.raises(ValueError, match=EMPTY_CREDENTIAL):
        authenticated_rtsp_source(SOURCE, USERNAME, "")


def test_empty_username_is_rejected() -> None:
    """Bo'sh foydalanuvchi nomi ham RAD ETILADI (bo'sh parol bilan juftlik)."""
    with pytest.raises(ValueError, match=EMPTY_CREDENTIAL):
        authenticated_rtsp_source(SOURCE, "", PASSWORD)


# ---------------------------------------------------------------------------
# KONTRAKT — imzo va `__all__`
# ---------------------------------------------------------------------------


def test_return_annotation_is_a_secret_carrier() -> None:
    """Qaytish tipi `SecretStr` — bu KELISHUV emas, IMZO (`03-04` standarti).

    ⚠ `test_rtsp_url.py::test_rtsp_url_signature_has_no_credential_parameter`
      bilan bir xil naqsh va bir xil sabab: kimdir qaytish tipini oddiy
      `str` ga tushirsa, sir birinchi istisnoda `repr` orqali oqib ketardi
      va buni birorta xulq testi sezmasdi.
    """
    signature = inspect.signature(authenticated_rtsp_source)

    assert "SecretStr" in str(signature.return_annotation)


def test_module_exports_exactly_the_documented_contract() -> None:
    """`__all__` — funksiya va uning to'rtta rad etish kodi."""
    assert set(live_source.__all__) == {
        "CREDENTIAL_INJECTION",
        "EMPTY_CREDENTIAL",
        "NOT_AN_RTSP_SOURCE",
        "SOURCE_ALREADY_AUTHENTICATED",
        "authenticated_rtsp_source",
    }


def test_quote_is_called_with_an_empty_safe_set() -> None:
    """`safe=""` MAJBURIY — standart `safe="/"` sleshni qoldirardi.

    ⚠ Bu USULNI qulflaydi, natijani emas: yuqoridagi inyeksiya testlari
      natijani o'lchaydi, bu esa kodlashning O'ZI to'liq ekanini. Ikkalasi
      ham kerak — natija testi darvoza tufayli `ValueError` bilan
      yiqilganda «nima buzildi» savoliga aynan shu qator javob beradi.
    """
    recorded: list[str] = []
    original = quote

    def _spy(value: str, safe: str = "/") -> str:
        recorded.append(safe)
        return original(value, safe=safe)

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(live_source, "quote", _spy)
        authenticated_rtsp_source(SOURCE, USERNAME, PASSWORD)

    assert recorded == ["", ""], f"`quote` `safe` siz chaqirildi: {recorded}"
