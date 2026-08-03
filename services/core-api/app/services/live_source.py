"""RTSP manbaiga rekvizit qo'shadigan YAGONA joy (D-12, T-03-88, RESEARCH D.13).

Sof funksiyalar moduli (`rtsp.py` bilan bir xil shakl): tarmoqqa
chiqmaydi, bazaga tegmaydi, holat saqlamaydi.

=============================================================================
NEGA BU `rtsp.py` DA EMAS, ALOHIDA MODULDA.

`rtsp.py` ning kontrakti — «parol parametri UMUMAN yo'q» (T-03-24) va u
IMZO bilan majburlanadi: `rtsp_url()` ning chiqishi saqlanadi, jurnalga
tushadi va `nvr_discovery_runs.error_detail` jsonb'iga ko'chadi, ya'ni
u yerda sir bo'lishi mumkin EMAS.

Bu modul o'sha qarorning MOS KELADIGAN IKKINCHI YARMI: rekvizit go2rtc'ga
kerak, lekin u faqat CHIQISH PAYTIDA, faqat shu yerda qo'shiladi va
natija `SecretStr` ichida tashiladi. Ikkalasini bir faylga yig'ish
`rtsp_url()` ning imzo darvozasini ma'nosiz qilardi — parol o'sha
modulning yuzasiga qaytib kirardi.
=============================================================================

=============================================================================
⚠⚠ FOIZLI KODLASH — XAVFSIZLIK NAZORATI, FORMATLASH EMAS (T-03-88).

Parolni bazaga ADMIN kiritadi. `pa@evil.example/` shaklidagi qiymat
kodlanmasa hosil bo'ladigan satr::

    rtsp://sbozor:pa@evil.example/@nvr.invalid:554/Streaming/Channels/102

va uni har qanday URL ajratuvchi `evil.example` XOSTI deb o'qiydi. Ya'ni
go2rtc hujumchining serveriga ulanib, NVR rekvizitini o'sha yerga TAQDIM
ETARDI — bu SSRF va bir vaqtning o'zida rekvizit o'g'irligi.

Shuning uchun bu yerda IKKI qadam bor va ikkalasi ham majburiy:

  1. `quote(..., safe="")` — `safe` ning STANDART qiymati (`"/"`) sleshni
     KODLAMAYDI va parolda slesh bo'lsa u yo'l chegarasini siljitardi;
  2. natijani QAYTA AJRATIB, xost/port/yo'l/query/fragment kirishdagi
     bilan TENGLIGINI talab qilish.

Ikkinchisi «ehtiyot chorasi» emas: u kodlashning to'g'ri ishlaganini
NATIJADAN o'lchaydi, kod o'qishdan emas. Birinchi qadam kelajakda
jimgina buzilsa (masalan `safe` argumenti tushib qolsa) ikkinchisi
ulanishni butunlay to'xtatadi — fail-closed.
=============================================================================

⚠ XATO MATNLARIGA QIYMAT YOZILMAYDI (`go2rtc.py::assert_safe_go2rtc_src`
  bilan bir xil qoida): rad etilgan qiymat ta'rifi bo'yicha ishonchsiz va
  uni istisno matniga qo'yish log injection yuzasini ochardi — ustiga u
  yerdan jurnalga va Sentry'ga ketardi.

⚠ NATIJA `SecretStr`, ODDIY `str` EMAS. Sabab `03-04` da o'lchangan:
  `repr()` istisno matnida, `pytest` diffida va Sentry ning lokal
  o'zgaruvchilar suratida chiqadi, ya'ni oddiy satr tashuvchi birinchi
  istisnodayoq oqib ketardi. Himoya kelishuv emas, TIP.
"""

from __future__ import annotations

from urllib.parse import quote, urlsplit, urlunsplit

from pydantic import SecretStr

__all__ = [
    "CREDENTIAL_INJECTION",
    "EMPTY_CREDENTIAL",
    "NOT_AN_RTSP_SOURCE",
    "SOURCE_ALREADY_AUTHENTICATED",
    "authenticated_rtsp_source",
]

_RTSP_SCHEME = "rtsp"
"""YAGONA qabul qilinadigan sxema — `rtsps` ham, `http` ham emas.

`assert_safe_go2rtc_src` ning O'RNINI BOSMAYDI (u go2rtc'ga chiqishda
baribir qo'llanadi), lekin darvoza IKKALA joyda ham turishi kerak: bu
yerdagi tekshiruvsiz rekvizit `exec:` satriga yopishtirilib, keyin
allow-listga `rtsp://` bilan boshlanadigan bo'lib ko'rinishi mumkin edi.
"""

NOT_AN_RTSP_SOURCE = "rtsp_source_not_rtsp"
"""Sxema `rtsp` emas yoki avtoritet o'qib bo'lmaydigan shaklda."""

SOURCE_ALREADY_AUTHENTICATED = "rtsp_source_already_authenticated"
"""Kirish URL'ida `user:pass@` ALLAQACHON bor.

Jimgina o'tkazib yuborilsa natija `rtsp://a:b@c:d@host/...` bo'lardi:
ajratuvchilar OXIRGI `@` ni oladi, ya'ni haqiqiy parol xost nomining
bo'lagiga aylanib qolardi va ulanish tushunarsiz sabab bilan yiqilardi.
"""

EMPTY_CREDENTIAL = "rtsp_credential_empty"
"""Foydalanuvchi nomi yoki parol bo'sh.

Rekvizitsiz manba bu funksiyadan CHIQMAYDI — rekvizitsiz yo'l
`rtsp.py::rtsp_url()` ning O'ZI. Bo'sh qiymatni o'tkazish
`rtsp://sbozor:@host/...` berardi va NVR `401` qaytarardi, sabab esa
«kamera ishlamayapti» bo'lib ko'rinardi (Pitfall 8 ning takrori).
"""

CREDENTIAL_INJECTION = "rtsp_credential_injection"
"""Rekvizit manzilning avtoritetini yoki yo'lini O'ZGARTIRDI (T-03-88).

Bu holat to'g'ri kodda HECH QACHON yuz bermaydi — u faqat foizli kodlash
buzilganda chiqadi. Ya'ni bu satr ko'rinishi KODDA xato borligining
belgisi va uni jimgina yutish mumkin emas.
"""

_Authority = tuple[str | None, int | None, str, str, str]
"""`(xost, port, yo'l, query, fragment)` — rekvizitdan TASHQARI hamma narsa."""


def _authority(url: str) -> _Authority | None:
    """URL'ning rekvizitsiz qismini qaytaradi; o'qib bo'lmasa `None`.

    ⚠ `SplitResult.port` YAROQSIZ portda `ValueError` KO'TARADI (masalan
      `admin:pa` shaklidagi netloc'da, ya'ni aynan kodlash buzilgan
      holatda). Uni shu yerda ushlash MAJBURIY: aks holda inyeksiya
      darvozasi o'z `ValueError` i o'rniga `urllib` ning xabari bilan
      yiqilardi va o'sha xabarda netloc — ya'ni PAROLNING bo'lagi —
      turardi (D-12 ning bevosita buzilishi).
    """
    parsed = urlsplit(url)
    try:
        port = parsed.port
    except ValueError:
        return None
    return (parsed.hostname, port, parsed.path, parsed.query, parsed.fragment)


def authenticated_rtsp_source(source: str, username: str, password: str) -> SecretStr:
    """`rtsp://host:port/path` ga rekvizit qo'shadi va natijani sir sifatida qaytaradi.

    Args:
        source: `rtsp.py::rtsp_url()` ning CHIQISHI — rekvizitsiz manzil.
        username: `nvr_devices.username` — ochiq matn, sir emas.
        password: `decrypt_nvr_password()` ning chiqishi — OCHIQ MATN sir.

    Returns:
        `SecretStr`, ochilgan qiymati `rtsp://<user>:<pass>@<host>:<port>/<path>`.
        Ikkala rekvizit ham foizli kodlangan.

    Raises:
        ValueError: `NOT_AN_RTSP_SOURCE`, `SOURCE_ALREADY_AUTHENTICATED`,
            `EMPTY_CREDENTIAL` yoki `CREDENTIAL_INJECTION` matni bilan.
            Xato TURI ataylab oddiy `ValueError` — `assert_safe_go2rtc_src`
            bilan bir xil qaror: bunday qiymat mahsulot yo'lidan kelmaydi
            va u kelishi KODDAGI xatoni bildiradi.
    """
    parsed = urlsplit(source)
    if parsed.scheme != _RTSP_SCHEME:
        raise ValueError(NOT_AN_RTSP_SOURCE)
    if parsed.username is not None or parsed.password is not None:
        raise ValueError(SOURCE_ALREADY_AUTHENTICATED)
    if not username or not password:
        raise ValueError(EMPTY_CREDENTIAL)

    expected = _authority(source)
    if expected is None:
        raise ValueError(NOT_AN_RTSP_SOURCE)

    # ⚠ `safe=""` — MODUL DOCSTRINGIDAGI 1-QADAM. Standart `safe="/"`
    #   sleshni qoldiradi va parolda slesh bo'lsa yo'l chegarasi siljiydi.
    userinfo = f"{quote(username, safe='')}:{quote(password, safe='')}"
    candidate = urlunsplit(
        (
            parsed.scheme,
            f"{userinfo}@{parsed.netloc}",
            parsed.path,
            parsed.query,
            parsed.fragment,
        )
    )

    # ⚠ 2-QADAM — DARVOZA. Kodlash to'g'ri ishlaganini NATIJADAN o'lchaydi.
    if _authority(candidate) != expected:
        raise ValueError(CREDENTIAL_INJECTION)

    return SecretStr(candidate)
