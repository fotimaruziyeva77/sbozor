"""NVR manzili — ajratish va XUSUSIY TARMOQ darvozasi (SC#5, T-03-23).

=============================================================================
BU MODUL SC#5 NING BIRINCHI DA'VOSINI BAJARADI.

SC#5: *«tunnel o'chirilsa ulanish uziladi va NVR internetdan to'g'ridan-
to'g'ri ochiq emas.»* Bu da'vo yaxlit holda CI'da SINALMAYDI — CI'da
tunnel umuman yo'q, ya'ni «tunnelni o'chir, uzilishini ko'r» testi HAR
DOIM o'tardi va hech nimani isbotlamasdi. Shuning uchun u uchga bo'lingan
(`03-RESEARCH.md` C.11):

  1. NVR manzili XUSUSIY tarmoqda        -> ✅ SHU MODUL, unit test, uskunasiz
  2. `AllowedIPs` da `0.0.0.0/0` YO'Q    -> `ops/wireguard` konfiguratsiya testi
  3. Marshrut haqiqatan tunneldan ketadi -> VPS'dagi deploy smoke-testi (03-07)

1 va 2 aynan REGRESSIYA xavfini tutadi (kimdir keyinroq ommaviy IP
kiritadi yoki `AllowedIPs` ni kengaytiradi); 3 esa bir martalik deploy
tekshiruvi.
=============================================================================

⚠ BU FAQAT KONFIGURATSIYA TEKSHIRUVI EMAS — SSRF CHEGARASI (T-03-23).
`nvr_devices.host` ga yozilgan qiymatga server O'ZI Digest so'rov yuboradi
(03-05). Ommaviy IP qabul qilinsa admin (yoki uning hisobini egallagan
kishi) serverni ixtiyoriy tashqi manzilga so'rov yuborishga majburlay
olardi va NVR ning o'zi internetga ochilgan bo'lardi.

⚠ HOSTNAME QABUL QILINADI — VA BU ATAYIN.
Rad etiladigan yagona narsa — MARSHRUTLANADIGAN OMMAVIY IP. Nomlar
(`.local`, `.internal`, compose tarmog'idagi xizmat nomlari) o'tadi.
Faqat IP qabul qiladigan «qattiqroq» validator konteyner tarmog'idagi
har qanday o'rnatmani sindirardi va keyingi qadam — buni sezgan odam
validatorni butunlay o'chirib qo'yishi — SC#5 ning yagona CI'dagi
da'vosini yo'q qilardi. Nom qanday manzilga yechilishini bu qatlam
BILMAYDI: DNS so'rovi validatorni tarmoqqa bog'lab qo'yardi (sekin,
ishonchsiz va o'zi SSRF vektori). Haqiqiy marshrut kafolati —
WireGuard ning `AllowedIPs` i, ya'ni 2-da'vo.

⚠ BU MODULDA BIRORTA XIZMAT NOMI ATAMA SIFATIDA HAM YOZILMAYDI.
`tests/unit/test_no_sim_branching.py` (03-02) `app/` daraxtida
simulyatorning imzolarini IZLAYDI va izoh bilan kodni AJRATMAYDI — bu
ataylab shunday: «ilova uchun simulyator — bu shunchaki bazadagi bir
qator» qoidasi nom kodga tushishi bilanoq yemirila boshlaydi. Aniq
nomga bog'langan regressiya testi `tests/unit/test_nvr_host_validation.py`
da, ya'ni to'g'ri tomonda turadi.
"""

from __future__ import annotations

import ipaddress
from urllib.parse import urlsplit

__all__ = [
    "DEFAULT_HTTPS_PORT",
    "DEFAULT_HTTP_PORT",
    "NvrAddressError",
    "NvrHostNotPrivateError",
    "assert_private_host",
    "split_address",
]

DEFAULT_HTTP_PORT = 80
DEFAULT_HTTPS_PORT = 443

_MIN_PORT = 1
_MAX_PORT = 65535

_TLS_SCHEMES = frozenset({"https"})
_PLAIN_SCHEMES = frozenset({"http"})
_SUPPORTED_SCHEMES = _TLS_SCHEMES | _PLAIN_SCHEMES
"""ISAPI HTTP(S) USTIDA ishlaydi — boshqa sxema qabul qilinmaydi.

`rtsp://` ni o'tkazish eng ehtimolli chalkashlik bo'lardi: admin RTSP
URL'ini NVR manzili deb kiritib, `use_tls` ni ham noto'g'ri olardi va
kashfiyot sababsiz yiqilardi.
"""


class NvrAddressError(ValueError):
    """Manzilni ajratib bo'lmadi (shakl, sxema yoki port xato).

    `ValueError` dan meros oladi (`phone.py::InvalidPhoneError` bilan bir
    xil qaror): chaqiruvchi uni umumiy validatsiya xatosi sifatida ham
    ushlay oladi va API qatlami 422 ga tarjima qiladi.
    """


class NvrHostNotPrivateError(ValueError):
    """Manzil MARSHRUTLANADIGAN ommaviy IP — rad etiladi (T-03-23).

    `NvrAddressError` dan ALOHIDA sinf va bu ataylab: admin uchun bular
    butunlay boshqa-boshqa muammolar. «Manzilni o'qib bo'lmadi» — terish
    xatosi; «ommaviy IP taqiqlangan» — arxitektura qoidasi, va ikkinchisiga
    javob boshqa manzil sinash EMAS, tunnel ichidagi manzilni topish.
    """


def assert_private_host(host: str) -> None:
    """`host` marshrutlanadigan ommaviy IP EMASLIGINI tekshiradi.

    Uch qadam:

      1. Qiymat IP manzil sifatida o'qishga urinadi;
      2. o'qilsa va u GLOBAL bo'lsa — rad etiladi;
      3. o'qilmasa — bu hostname va u QABUL QILINADI (modul docstringi).

    ⚠ `is_global`, `is_private` EMAS — va bu O'LCHANADIGAN tanlov.
      `not is_private` CGNAT (`100.64.0.0/10`) ni RAD ETARDI, holbuki
      aynan o'sha oraliq bozor tomonidagi operator tarmog'ida uchraydi
      (`03-RESEARCH.md` C.12: «bozor tomoni rozetkaga ulaydi»). Xuddi
      shunday, `is_private` link-local va loopback'ni ham boshqacha
      hisoblaydi. `is_global` esa IANA ning maxsus-maqsadli reyestriga
      tayanadi va savolga TO'G'RIDAN-TO'G'RI javob beradi: «bu manzilga
      internetdan borish mumkinmi?»

    Args:
        host: `nvr_devices.host` ga yoziladigan qiymat.

    Raises:
        NvrHostNotPrivateError: qiymat global (marshrutlanadigan) IP bo'lsa.
    """
    try:
        address = ipaddress.ip_address(host.strip())
    except ValueError:
        # Hostname — IP emas. Qabul qilinadi (modul docstringi).
        return

    if address.is_global:
        raise NvrHostNotPrivateError(
            f"NVR manzili xususiy tarmoqda bo'lishi kerak, ommaviy IP berildi: {host}. "
            "NVR internetga ochilmaydi — WireGuard tunneli ichidagi manzilni kiriting "
            "(masalan 192.168.1.64)."
        )


def split_address(raw: str) -> tuple[str, int, bool]:
    """`host`, `port` va `use_tls` ni bitta manzil satridan ajratadi.

    UI-SPEC §4.1 jadvalining SERVER TOMONIDAGI ZAXIRASI::

        192.168.1.64            -> ("192.168.1.64", 80,   False)
        192.168.1.64:8080       -> ("192.168.1.64", 8080, False)
        http://192.168.1.64     -> ("192.168.1.64", 80,   False)
        https://192.168.1.64    -> ("192.168.1.64", 443,  True)
        https://192.168.1.64:8443 -> ("192.168.1.64", 8443, True)
        nvr.local               -> ("nvr.local",    80,   False)

    ⚠ KLIENTDAGI AJRATISH — QULAYLIK, BU YERDAGI — KONTRAKT.
      Forma `zod .transform()` bilan allaqachon ajratilgan qiymat yuboradi
      (UI-SPEC §4.7), lekin API to'g'ridan-to'g'ri ham chaqirilishi mumkin
      va u holda qoida IKKINCHI joyda bo'lishi shart. Aks holda server
      `192.168.1.64:8080` ni butunlay hostname deb qabul qilardi va
      kashfiyot 80-portga urinardi.

    ⚠ MAXFIYLIK BU YERDA TEKSHIRILMAYDI — u `assert_private_host()` ning
      ishi. Ikkalasini birlashtirish xato xabarini chalkashtirardi
      (`NvrAddressError` va `NvrHostNotPrivateError` docstringlariga
      qarang).

    Args:
        raw: forma maydonining xom qiymati.

    Returns:
        `(host, port, use_tls)`.

    Raises:
        NvrAddressError: qiymat bo'sh, sxema qo'llab-quvvatlanmasa, host
            ajratib bo'lmasa yoki port oraliqdan tashqarida bo'lsa.
    """
    candidate = raw.strip()
    if not candidate:
        raise NvrAddressError("NVR manzili bo'sh bo'lishi mumkin emas")

    use_tls = False
    if "://" in candidate:
        scheme, _, remainder = candidate.partition("://")
        scheme = scheme.lower()
        if scheme not in _SUPPORTED_SCHEMES:
            raise NvrAddressError(
                f"NVR manzilining sxemasi qo'llab-quvvatlanmaydi: {scheme!r}. "
                "ISAPI HTTP(S) ustida ishlaydi — `http://` yoki `https://` kiriting."
            )
        use_tls = scheme in _TLS_SCHEMES
        candidate = remainder

    # Yo'l/so'rov qismini tashlaymiz: `nvr.local:8443/doc/index.html` —
    # brauzerdan ko'chirib qo'yilgan qiymatning odatiy shakli.
    candidate = candidate.split("/", maxsplit=1)[0]
    if not candidate:
        raise NvrAddressError(f"NVR manzilidan host ajratilmadi: {raw!r}")

    # `urlsplit` IPv6 ning kvadrat qavslarini (`[fd00::1]:8080`) to'g'ri
    # ajratadi — qo'lda `rsplit(":")` qilinsa manzilning O'ZI bo'linardi.
    parts = urlsplit(f"//{candidate}")
    try:
        host = parts.hostname
        port = parts.port
    except ValueError as exc:
        # `urlsplit` porti raqam bo'lmasa yoki oraliqdan tashqarida bo'lsa
        # aynan shu yerda yiqiladi.
        raise NvrAddressError(f"NVR manzilining porti noto'g'ri: {raw!r}") from exc

    if not host:
        raise NvrAddressError(f"NVR manzilidan host ajratilmadi: {raw!r}")

    if port is None:
        port = DEFAULT_HTTPS_PORT if use_tls else DEFAULT_HTTP_PORT
    elif not (_MIN_PORT <= port <= _MAX_PORT):
        raise NvrAddressError(
            f"NVR porti {_MIN_PORT}..{_MAX_PORT} oralig'ida bo'lishi kerak, berilgani: {port}"
        )

    return host, port, use_tls
