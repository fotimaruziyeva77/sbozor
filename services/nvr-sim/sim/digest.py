"""RFC 7616 / RFC 2617 Digest autentifikatsiyasining **SERVER** tomoni.

=============================================================================
BU FAZADAGI YAGONA QO'LDA YOZILADIGAN PROTOKOL.

`03-RESEARCH.md` § `Don't Hand-Roll` shunday deydi: "bu fazada hand-roll
qilinishi kerak bo'lgan YAGONA narsa — Digest challenge'ning SERVER tomoni.
Buning tayyor yechimi yo'q va aynan uning HAQIQIYLIGI butun SC#7 da'vosini
ushlab turadi. Qolgan hamma joyda hand-roll — xato."

KLIENT tomoni esa **hech qachon** yozilmaydi: `httpx.DigestAuth` ishlatiladi.
Agar biz ikkala tomonni ham o'zimiz yozsak, test faqat "bizning
implementatsiyamiz o'zi bilan kelishadi" ni isbotlardi.
=============================================================================

⚠ `verify()` `response` ni **HAQIQATAN HISOBLAYDI**. Bu stub bo'lsa
(masalan har doim `True`), `nvr_bad_credentials` yo'li hech qachon sinalmaydi
va D-03 ning butun retry siyosati o'lchanmasdan qolardi (T-03-09). Aynan shu
sababdan `tests/integration/test_nvr_sim.py` da `verify` ni `True` qaytaradigan
qilish sabotaji bajariladi va u testni qizartirishi SHART.

CHEGARALAR (ataylab, hujjatlashtirilgan):
  * `nonce` bir martalik EMAS — takroriy `nc` rad etilmaydi. Real qurilma ham
    odatda `nc` ni qat'iy kuzatmaydi; bizga kerak bo'lgan xususiyat — parolning
    haqiqatan tekshirilishi.
  * `algorithm` faqat `MD5` (Hikvision aynan shuni ishlatadi). `SHA-256`
    variantini qo'llab-quvvatlash real qurilma bilan mos kelmaslikni bildirardi.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import secrets

REALM = "IP Camera(C1234)"
"""Hikvision qurilmalarining odatdagi `realm` shakli — `WWW-Authenticate` da shu ko'rinadi."""

OPAQUE = "5ccc069c403ebaf9f0171e9517f40e41"
"""Statik `opaque`: RFC bo'yicha klient uni o'zgarishsiz qaytaradi; biz undan foydalanmaymiz."""


def _md5(data: str) -> str:
    """MD5 — bu yerda XAVFSIZLIK PRIMITIVI EMAS, u PROTOKOL TALAB QILGAN hisob.

    RFC 7616 `algorithm=MD5` uchun `response` aynan MD5 bilan hisoblanadi va
    Hikvision qurilmalari aynan shu algoritmni ishlatadi. Uni "kuchliroq"
    narsaga almashtirish xavfsizlikni oshirmaydi — u shunchaki `httpx.DigestAuth`
    bilan (va real NVR bilan) **mos kelmaslikni** bildiradi, ya'ni simulyator
    o'z maqsadini yo'qotardi.

    Shu sababdan `usedforsecurity=False` bayrog'i ISHLATILMAYDI: u "bu MD5
    xavfsizlik uchun emas" deb FIPS rejimida ishlashga ruxsat berardi, lekin
    bayroq ruff `S324` ni baribir yopmaydi va sababni ham yozib qo'ymaydi.
    """
    return hashlib.md5(data.encode("utf-8")).hexdigest()  # noqa: S324 — protokol talabi, yuqoridagi izohga qarang


def make_nonce() -> str:
    """HAQIQIY tasodifiy nonce.

    ⚠ Qotib qolgan satr BO'LMASLIGI kerak: `httpx.DigestAuth` nonce'ni
    eslab qoladi va `nc` (nonce-count) ni oshiradi. Nonce har safar bir xil
    bo'lsa, o'sha mexanika umuman sinalmasdan qolardi va simulyator
    "handshake ishlaydi" degan yolg'on ishonch berardi.
    """
    return secrets.token_hex(16)


def build_challenge(
    realm: str = REALM,
    *,
    nonce: str | None = None,
    stale: bool = False,
    opaque: str = OPAQUE,
) -> str:
    """`WWW-Authenticate: <shu satr>` uchun Digest challenge'ini quradi.

    `stale=true` — nonce eskirgan/rad etilgan degani. A.3 bo'yicha bu deyarli
    har doim **soat farqi** alomati, shuning uchun `mode="digest_stale"` uni
    ataylab qayta tug'diradi.
    """
    parts = [
        f'realm="{realm}"',
        f'nonce="{nonce or make_nonce()}"',
        'qop="auth"',
        f'opaque="{opaque}"',
        "algorithm=MD5",
    ]
    if stale:
        parts.append("stale=true")
    return "Digest " + ", ".join(parts)


def parse_authorization(header: str) -> dict[str, str]:
    """`Authorization: Digest ...` sarlavhasini lug'atga ajratadi.

    Tirnoqlar olib tashlanadi, noma'lum kalitlar e'tiborsiz qoldiriladi
    (RFC klientlarga qo'shimcha parametr yuborishga ruxsat beradi).
    `Digest` sxemasi bo'lmasa bo'sh lug'at qaytadi.
    """
    header = header.strip()
    scheme, _, rest = header.partition(" ")
    if scheme.lower() != "digest" or not rest:
        return {}

    params: dict[str, str] = {}
    # `,` ajratuvchisi — tirnoq ichidagi vergul (masalan `qop="auth,auth-int"`)
    # kamdan-kam uchraydi; shuning uchun oddiy bo'lish yetarli, lekin bo'sh
    # bo'laklar tashlab yuboriladi.
    for chunk in rest.split(","):
        key, sep, value = chunk.partition("=")
        if not sep:
            continue
        params[key.strip().lower()] = value.strip().strip('"')
    return params


def verify(
    params: dict[str, str],
    *,
    method: str,
    username: str,
    password: str,
    realm: str = REALM,
) -> bool:
    """`response` ni HISOBLAB solishtiradi — mana shu funksiya stub bo'lmasligi kerak.

    `HA1 = MD5(user:realm:pass)`
    `HA2 = MD5(method:uri)`
    `qop="auth"`  -> `response = MD5(HA1:nonce:nc:cnonce:qop:HA2)`
    `qop` yo'q     -> `response = MD5(HA1:nonce:HA2)`  (RFC 2069 merosi)

    `uri` KLIENT yuborgan qiymatdan olinadi — RFC aynan shuni talab qiladi.
    Chaqiruvchi (`main.py`) uni so'rovning haqiqiy nishoni bilan alohida
    solishtiradi, aks holda bitta yo'l uchun olingan sarlavhani boshqasiga
    qayta ishlatib bo'lardi.
    """
    supplied = params.get("response", "")
    nonce = params.get("nonce", "")
    uri = params.get("uri", "")
    if not supplied or not nonce or not uri:
        return False
    if params.get("username") != username:
        return False

    ha1 = _md5(f"{username}:{realm}:{password}")
    ha2 = _md5(f"{method.upper()}:{uri}")

    qop = params.get("qop", "")
    if qop:
        nc = params.get("nc", "")
        cnonce = params.get("cnonce", "")
        if not nc or not cnonce:
            return False
        expected = _md5(f"{ha1}:{nonce}:{nc}:{cnonce}:{qop}:{ha2}")
    else:
        expected = _md5(f"{ha1}:{nonce}:{ha2}")

    return secrets.compare_digest(expected, supplied)


def verify_basic(header: str, *, username: str, password: str) -> bool:
    """`Authorization: Basic ...` ni tekshiradi — FAQAT `basic_only` rejimi uchun.

    A.3: ba'zi firmware'da Web-autentifikatsiya rejimi `digest/basic` emas,
    `basic` bo'lib qoladi va Digest **rad etiladi**. Bu holatni sinash uchun
    sim Basic'ni ham tushunishi kerak — lekin faqat o'sha rejimda.
    """
    scheme, _, encoded = header.strip().partition(" ")
    if scheme.lower() != "basic" or not encoded:
        return False
    try:
        decoded = base64.b64decode(encoded, validate=True).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError):
        return False
    supplied_user, sep, supplied_password = decoded.partition(":")
    if not sep:
        return False
    return secrets.compare_digest(supplied_user, username) and secrets.compare_digest(
        supplied_password, password
    )
