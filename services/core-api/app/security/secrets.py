"""NVR rekvizitlarining shifri — Fernet + kalit rotatsiyasi (SC#4).

=============================================================================
BU LOYIHADAGI BIRINCHI SHIFRLASH MODULI — KO'CHIRILADIGAN UY NAQSHI YO'Q.

`03-PATTERNS.md` §4.1 o'lchagan: `cryptography` (`pyproject.toml:17` da
e'lon qilingan) repozitoriyda hech qayerda import qilinmagan edi. Eng yaqin
strukturaviy qo'shni — `sbozor_core/security.py` dagi parol hashlash —
BIR TOMONLAMA, ya'ni unda kalit rotatsiyasi muammosi umuman yo'q. Shuning
uchun bu yerdagi qarorlar (kalit manbai, rotatsiyaning shakli, deshifrlash
xatosining taqdiri) ATAYIN ochiq yozilgan: ulardan biri keyin jimgina
o'zgartirilsa mavjud qatorlar o'qib bo'lmas holga kelardi.

NIMA ATAYIN QILINMAYDI:

  * AES/IV/HMAC QO'LDA yozilmaydi. Fernet — tayyor, tekshirilgan
    konstruksiya (AES-128-CBC + HMAC-SHA256, IV va vaqt tamg'asi bilan).
    Uni "soddalashtirish" bu yerdagi eng qimmat xato bo'lardi.
  * Kalit HECH QACHON bazada saqlanmaydi. `pgcrypto` aynan shu sababdan
    rad etilgan (`03-RESEARCH.md` C.10): kalit DB'da bo'lsa "bazaga kirgan
    odam ochiq matn parol ko'rmaydi" degan SC#4 butunlay ma'nosiz bo'ladi.
  * Kalit `JWT_SECRET` DAN ALOHIDA — ikki xil xavf modeli. JWT kaliti
    almashtirilsa sessiyalar tushadi (arzon, o'z-o'zidan tuzaladi); shifr
    kaliti almashtirilsa MA'LUMOT YO'QOLADI (qimmat, tuzalmaydi).
  * Ochiq matn parol `repr` ga, jurnalga yoki auditga TUSHMAYDI. Modul
    faqat ikkita tor funksiya beradi va parolni obyektda SAQLAMAYDI —
    saqlanmagan qiymat sizib chiqa olmaydi. `nvr_credentials` jadvali esa
    audit triggeridan butunlay chiqarilgan (03-03, T-03-13).
  * `MultiFernet` HAND-ROLL QILINMAYDI. "Bir nechta kalitni sinab ko'rish"
    siklini o'zimiz yozish vaqt bo'yicha oshkor solishtiruvga va noto'g'ri
    xato semantikasiga olib kelardi; `cryptography` bu API'ni o'zi beradi.
=============================================================================

KALIT ROTATSIYASI — QANDAY BAJARILADI (operator uchun):

  1. Yangi kalit hosil qiling:
     ``python -c "from cryptography.fernet import Fernet;print(Fernet.generate_key().decode())"``
  2. ESKI `NVR_CREDENTIAL_KEY` qiymatini `NVR_CREDENTIAL_KEYS_RETIRED` ga
     ko'chiring (vergul bilan; eng yangisi oldinda).
  3. Yangi kalitni `NVR_CREDENTIAL_KEY` ga qo'ying va ilovani qayta
     ishga tushiring — mavjud qatorlar SHU ZAHOTI o'qilaveradi.
  4. Qatorlarni bo'sh vaqtda qayta shifrlang (`MultiFernet.rotate()`) va
     `nvr_credentials.key_version` ni `CURRENT_KEY_VERSION` ga ko'taring.
  5. Ish ro'yxati tugagach (`WHERE key_version < CURRENT_KEY_VERSION` bo'sh)
     eski kalitni `NVR_CREDENTIAL_KEYS_RETIRED` dan olib tashlang.

⚠ 3-qadamdan KEYIN yozilgan token eski kalit bilan O'QILMAYDI — yo'nalish
  bir tomonlama. Orqaga qaytish kerak bo'lsa eski kalit BIRINCHI o'ringa
  qaytarilishi shart, aks holda yangi qatorlar yo'qoladi.
"""

from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

from cryptography.fernet import Fernet, InvalidToken, MultiFernet

from app.settings import get_settings

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = [
    "CURRENT_KEY_VERSION",
    "InvalidToken",
    "build_cipher",
    "decrypt_nvr_password",
    "encrypt_nvr_password",
    "nvr_cipher",
    "split_retired_keys",
]

CURRENT_KEY_VERSION = 1
"""`nvr_credentials.key_version` ga yoziladigan qiymat.

MAQSADI — ROTATSIYANING ISH RO'YXATINI SO'ROV BILAN TOPISH:

    SELECT nvr_id FROM nvr_credentials WHERE key_version < <CURRENT_KEY_VERSION>

Usiz rotatsiya "hammasini qayta shifrlab ko'ramiz" ga aylanardi: qaysi
qator qaysi kalit bilan yozilganini aytadigan hech nima qolmasdi va
uzilgan rotatsiyani davom ettirish imkonsiz bo'lardi.

⚠ Bu qiymat kalit ALMASHTIRILGANDA qo'lda oshiriladi (kod o'zgarishi bilan,
  migratsiya bilan emas — u ilova sozlamasining versiyasi, sxemaniki emas).
"""

_KEY_SEPARATOR = ","
"""`NVR_CREDENTIAL_KEYS_RETIRED` ning ajratuvchisi.

Vergul, chunki Fernet kaliti — base64url alifbosi (`A-Za-z0-9_-=`) va unda
vergul UCHRAMAYDI, ya'ni ajratuvchi qiymat ichiga tushib qololmaydi.
"""


def split_retired_keys(raw: str) -> tuple[str, ...]:
    """Vergul bilan ajratilgan kalitlar ro'yxatini tozalab ajratadi.

    Bo'sh bo'laklar va ortiqcha bo'shliqlar TASHLAB YUBORILADI. Bu
    "qulaylik uchun" emas: qiymat muhit o'zgaruvchisiga QO'LDA, ehtimol
    rotatsiya kuni shoshilinch yoziladi. Qo'shaloq vergul yoki oxiridagi
    bo'shliq `Fernet("")` chaqiruvini keltirib chiqarardi va butun ilova
    ko'tarilmasdan qolardi — ya'ni terish xatosi ishlab chiqarishni
    to'xtatardi.

    Args:
        raw: `NVR_CREDENTIAL_KEYS_RETIRED` ning xom qiymati.

    Returns:
        Kalitlar berilgan TARTIBDA (tartib muhim — pastga qarang).
    """
    return tuple(part.strip() for part in raw.split(_KEY_SEPARATOR) if part.strip())


def build_cipher(primary: str, retired: Sequence[str] = ()) -> MultiFernet:
    """`MultiFernet` quradi: BIRINCHI kalit YOZADI, HAMMASI O'QIYDI.

    Bu `MultiFernet` ning rasmiy semantikasi va u shu yerda ATAYIN
    takrorlanmaydi — kalitlar shunchaki to'g'ri TARTIBDA uzatiladi.
    Tartibning o'zi kontrakt: `primary` birinchi bo'lmasa yangi yozuvlar
    iste'foga chiqqan kalit bilan shifrlanardi va rotatsiya teskari
    yo'nalishda ketardi.

    ⚠ `retired` ni tashlab ketish — mavjud qatorlarni o'qib bo'lmas holga
      keltirish demak (T-03-21). Aynan shu xatoni `tests/unit/
      test_nvr_secrets.py::test_token_written_with_the_retired_key_is_
      still_readable` tutadi.

    Args:
        primary: joriy kalit (`NVR_CREDENTIAL_KEY`) — YOZISH shu bilan.
        retired: iste'foga chiqqan kalitlar — faqat O'QISH uchun.

    Raises:
        ValueError: kalitlardan biri Fernet formatida bo'lmasa. Amalda bu
            yerga yetib kelmaydi: format `Settings` da, ishga tushishda
            tekshiriladi (T-03-22).
    """
    return MultiFernet([Fernet(key.encode()) for key in (primary, *retired)])


@lru_cache(maxsize=1)
def nvr_cipher() -> MultiFernet:
    """Modul darajasidagi YAGONA shifr instansi.

    `sbozor_core/security.py:44-63` dagi `_hasher` naqshi: har chaqiruvda
    qayta qurish keraksiz ish va sozlamaning ikki joyda ajralib ketishiga
    yo'l ochadi. Keshlash usuli `get_settings()` niki bilan AYNAN bir xil
    (`lru_cache(maxsize=1)`) — ikkinchi mexanizm kiritilmaydi.

    Instans YALQOV quriladi (import paytida emas): `settings.py` ni import
    qilishning o'zi hali muhit to'ldirilmagan jarayonda ham xavfsiz
    bo'lishi kerak, ya'ni yiqilish nuqtasi `Settings` ning O'ZI bo'ladi.
    """
    settings = get_settings()
    # `.get_secret_value()` SHU IKKI JOYDA va boshqa hech qayerda: maydonlar
    # `SecretStr` (settings.py dagi sabab) va ochiq qiymatga borish
    # ATAYIN ko'rinadigan, grep bilan topiladigan qadam.
    return build_cipher(
        settings.nvr_credential_key.get_secret_value(),
        split_retired_keys(settings.nvr_credential_keys_retired.get_secret_value()),
    )


def encrypt_nvr_password(plain: str) -> bytes:
    """Ochiq matn parolni `nvr_credentials.password_encrypted` uchun tokenga o'giradi.

    Natija HAR CHAQIRUVDA BOSHQA (Fernet IV va vaqt tamg'asi qo'shadi) —
    bu shart, aks holda bir xil parolli ikki NVR bir xil baytga ega
    bo'lardi va bazani ko'rgan odam buni parolni bilmasdan ham sezardi.

    ⚠ Qaytariladigan qiymat `bytes`, `str` EMAS: repozitoriy chegarasi
      faqat `bytes` ni ko'radi (`nvr_repo.py` modul docstringi) va matnga
      o'girilgan token beixtiyor formatlangan xabarga qo'shilib ketardi.
    """
    return nvr_cipher().encrypt(plain.encode("utf-8"))


def decrypt_nvr_password(token: bytes) -> str:
    """Tokendan ochiq matn parolni tiklaydi.

    ⚠ XATO YUTILMAYDI. Buzilgan yoki begona kalit bilan yozilgan token
      `InvalidToken` ko'taradi va u SHU YERDA ushlanmaydi — chaqiruvchi
      uni ISAPI ning `401` idan farqlashi SHART (SC#3 taksonomiyasi).
      `None` qaytarish ikkalasini bir xil "ulanib bo'lmadi" holatiga
      qo'shib yuborardi va operator noto'g'ri joyni — parolni, kalit
      o'rniga — qidirardi.

    ⚠ Natija HECH QAYERDA saqlanmaydi va jurnalga tushmaydi: chaqiruvchi
      uni faqat chiquvchi so'rovga (ISAPI Digest yoki go2rtc konfiguratsiyasi)
      beradi va darhol unutadi.
    """
    return nvr_cipher().decrypt(token).decode("utf-8")
