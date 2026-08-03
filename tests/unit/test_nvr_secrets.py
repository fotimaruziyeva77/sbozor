"""NVR parolining Fernet shifri va kalit ROTATSIYASI (SC#4, T-03-20..22).

=============================================================================
BU FAYL LOYIHADAGI BIRINCHI SHIFRLASH TESTI.

`03-PATTERNS.md` §4.1 o'lchagan: `cryptography` bu repozitoriyda hech qayerda
import qilinmagan (`grep -rn "from cryptography" --include=*.py .` -> 0
natija), garchi paket `services/core-api/pyproject.toml:17` da e'lon
qilingan bo'lsa ham. Ya'ni bu yerda ko'chiriladigan uy naqshi YO'Q va
testning o'zi kontraktni birinchi marta yozadi.

Eng yaqin qo'shni — `tests/unit/test_password.py` — BIR TOMONLAMA sirni
(Argon2id hash) sinaydi, ya'ni unda rotatsiya tushunchasi umuman yo'q. Shu
sababdan bu yerdagi eng muhim ikkita test aynan rotatsiyaning IKKI
YO'NALISHI haqida.
=============================================================================

ROTATSIYA NEGA IKKI YO'NALISHDA O'LCHANADI:

  1. Eski kalit bilan yozilgan token yangi konfiguratsiyada O'QILADI
     (`retired` ro'yxati ishlayapti);
  2. Yangi kalit bilan yozilgan token faqat eski kalit qolgan
     konfiguratsiyada O'QILMAYDI.

Faqat birinchisi o'lchansa test "ikkita kalit ham ishlaydi" ni isbotlardi,
"rotatsiya" ni emas — ikkinchi band yo'nalishning BIR TOMONLAMA ekanini
qulflaydi va aynan u `build_cipher` dagi kalit TARTIBINI himoya qiladi
(`MultiFernet`: birinchi kalit yozadi, hammasi o'qiydi).

KALITLAR TESTDA HOSIL QILINADI (`Fernet.generate_key()`) — fayldan ham,
muhitdan ham OLINMAYDI. Qotirilgan test kaliti repozitoriyga tushgan sir
bo'lardi va uni bir kun kimdir prod'da ishlatishi mumkin edi.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from app.security.secrets import (
    CURRENT_KEY_VERSION,
    build_cipher,
    decrypt_nvr_password,
    encrypt_nvr_password,
    split_retired_keys,
)
from app.settings import Settings, get_settings
from cryptography.fernet import Fernet, InvalidToken
from pydantic import SecretStr, ValidationError
from sbozor_core.logging import CENSORED, censor_secrets

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator, Sequence

PASSWORD = "Sim12345"
"""`03-RESEARCH.md` A.1 dagi simulyator paroli — ATAYIN o'sha qiymat.

Sim'ning parolini ishlatish testni haqiqiy oqimga bog'laydi: aynan shu satr
03-05 da ISAPI klientiga uzatiladi. Tasodifiy satr ham o'tardi, lekin u
hujjatlangan qiymat bilan bog'liqlikni yo'qotardi.
"""

MALFORMED_KEY = "not-a-fernet-key"
"""Fernet formatiga MOS KELMAYDIGAN qiymat — ataylab base64 ham emas."""

_REQUIRED_ENV = {
    "DATABASE_URL": "postgresql+asyncpg://sbozor_app:x@db:5432/sbozor",
    "VALKEY_URL": "redis://cache:6379/0",
    "JWT_SECRET": "x" * 48,
}
"""`Settings` ning NVR bilan bog'liq bo'lmagan MAJBURIY maydonlari.

Ular shu yerda beriladi, chunki test HAQIQIY `get_settings()` yo'lidan
boradi — soxta sozlama obyektidan emas. Aks holda test `settings.py` bilan
`secrets.py` orasidagi ULANISHNI (`key_links`) umuman o'lchamasdi va
maydon nomi o'zgarganda yashil qolaverardi.
"""


@pytest.fixture
def configure_keys(monkeypatch: pytest.MonkeyPatch) -> Iterator[Callable[..., None]]:
    """Kalitlarni muhitga qo'yadi va IKKALA keshni ham tozalaydi.

    `get_settings()` va shifr instansi `lru_cache` ostida (prod'da bu
    to'g'ri: sozlama bir marta o'qiladi). Testda esa kesh tozalanmasa
    ikkinchi holat birinchisining kalitini ko'rardi va rotatsiya testi
    hech nimani o'lchamasdi.

    Tozalash `monkeypatch` bekor qilingandan KEYIN ham kerak, shuning
    uchun u `yield` ning ikkala tomonida ham bajariladi — aks holda bu
    fayldagi oxirgi kalit boshqa test modullariga sizib o'tardi.
    """

    def _configure(primary: str, retired: Sequence[str] = ()) -> None:
        for name, value in _REQUIRED_ENV.items():
            monkeypatch.setenv(name, value)
        monkeypatch.setenv("NVR_CREDENTIAL_KEY", primary)
        monkeypatch.setenv("NVR_CREDENTIAL_KEYS_RETIRED", ",".join(retired))
        get_settings.cache_clear()
        _clear_cipher_cache()

    _clear_cipher_cache()
    get_settings.cache_clear()
    yield _configure
    get_settings.cache_clear()
    _clear_cipher_cache()


def _clear_cipher_cache() -> None:
    """Modul darajasidagi shifr instansini bo'shatadi."""
    from app.security import secrets as secrets_module

    secrets_module.nvr_cipher.cache_clear()


def _new_key() -> str:
    return Fernet.generate_key().decode()


# ---------------------------------------------------------------------------
# Aylanma
# ---------------------------------------------------------------------------


def test_round_trip_returns_the_original_password(configure_keys: Callable[..., None]) -> None:
    """Shifrlab, deshifrlab — o'sha satr qaytadi."""
    configure_keys(_new_key())

    token = encrypt_nvr_password(PASSWORD)

    assert decrypt_nvr_password(token) == PASSWORD


def test_ciphertext_does_not_contain_the_plaintext(configure_keys: Callable[..., None]) -> None:
    """Token ichida ochiq matn UCHRAMAYDI (nazorat bandi).

    Aylanma testi yolg'iz o'zi "shifrlash" ni "hech nima qilmaslik" dan
    ajratmaydi: `encrypt` parolni shunchaki qaytarsa ham aylanma yashil
    bo'lardi.
    """
    configure_keys(_new_key())

    token = encrypt_nvr_password(PASSWORD)

    assert PASSWORD.encode() not in token


def test_same_password_encrypts_to_different_tokens(configure_keys: Callable[..., None]) -> None:
    """Bir xil parol IKKI XIL token beradi (Fernet IV + vaqt tamg'asi).

    Determinstik shifr `password_encrypted` ustunini lug'at hujumiga ochiq
    qilardi: bir xil parolli ikki NVR bir xil baytga ega bo'lardi va
    bazani ko'rgan odam buni parolsiz ham sezardi.
    """
    configure_keys(_new_key())

    first = encrypt_nvr_password(PASSWORD)
    second = encrypt_nvr_password(PASSWORD)

    assert first != second
    assert decrypt_nvr_password(first) == decrypt_nvr_password(second) == PASSWORD


# ---------------------------------------------------------------------------
# Rotatsiya — IKKI YO'NALISH (modul docstringi)
# ---------------------------------------------------------------------------


def test_token_written_with_the_retired_key_is_still_readable(
    configure_keys: Callable[..., None],
) -> None:
    """1-YO'NALISH: eski kalit bilan yozilgani yangi konfiguratsiyada o'qiladi.

    Bu bandsiz kalit almashtirish MA'LUMOT YO'QOTISH amaliyoti bo'lardi
    (T-03-21): barcha mavjud `nvr_credentials` qatorlari bir zumda
    o'qib bo'lmas holga kelardi va sabab faqat birinchi ulanish
    urinishida ko'rinardi.
    """
    old_key = _new_key()
    new_key = _new_key()

    configure_keys(old_key)
    legacy_token = encrypt_nvr_password(PASSWORD)

    # Rotatsiya: yangi kalit BIRINCHI, eskisi `retired` ga ko'chdi.
    configure_keys(new_key, retired=(old_key,))

    assert decrypt_nvr_password(legacy_token) == PASSWORD


def test_token_written_with_the_new_key_is_unreadable_by_the_old_key_alone(
    configure_keys: Callable[..., None],
) -> None:
    """2-YO'NALISH: yangi kalit bilan yozilgani ESKI konfiguratsiyada o'qilmaydi.

    Yo'nalish BIR TOMONLAMA ekanini qulflaydi. Usiz birinchi test
    shunchaki "ikkita kalit ham ishlaydi" ni isbotlardi va `build_cipher`
    dagi kalit TARTIBI (kim yozadi) umuman o'lchanmasdi.
    """
    old_key = _new_key()
    new_key = _new_key()

    configure_keys(new_key, retired=(old_key,))
    fresh_token = encrypt_nvr_password(PASSWORD)

    configure_keys(old_key)

    with pytest.raises(InvalidToken):
        decrypt_nvr_password(fresh_token)


def test_build_cipher_writes_with_the_first_key() -> None:
    """`MultiFernet` semantikasi: BIRINCHI kalit yozadi, hammasi o'qiydi.

    `build_cipher` ni sozlamalardan MUSTAQIL o'lchaydi — bu funksiya
    03-06 dagi rotatsiya yugurishida ham to'g'ridan-to'g'ri chaqiriladi.
    """
    primary = _new_key()
    retired = _new_key()

    token = build_cipher(primary, (retired,)).encrypt(PASSWORD.encode())

    # Faqat birlamchi kalit bilan qurilgan shifr uni O'QIY OLADI...
    assert Fernet(primary.encode()).decrypt(token) == PASSWORD.encode()
    # ...iste'foga chiqqan kalit esa YO'Q.
    with pytest.raises(InvalidToken):
        Fernet(retired.encode()).decrypt(token)


# ---------------------------------------------------------------------------
# Sozlama — noto'g'ri kalit ISHGA TUSHISHDA yiqiladi
# ---------------------------------------------------------------------------


def test_malformed_key_fails_at_settings_construction() -> None:
    """Noto'g'ri kalit `Settings` QURILISHIDA yiqiladi (T-03-22).

    ⚠ Da'vo AYNAN shu: yiqilish ILOVA KO'TARILAYOTGANDA bo'ladi, birinchi
    kamera qo'shilganda emas. Shuning uchun test `Settings(...)` ni
    QURADI — modulni import qilish validatorni umuman ishga tushirmasdi.
    """
    with pytest.raises(ValidationError) as excinfo:
        Settings(
            database_url=_REQUIRED_ENV["DATABASE_URL"],
            valkey_url=_REQUIRED_ENV["VALKEY_URL"],
            jwt_secret=_REQUIRED_ENV["JWT_SECRET"],
            nvr_credential_key=SecretStr(MALFORMED_KEY),
        )

    message = str(excinfo.value)
    # Xato matni FOYDALI bo'lishi shart: format talabi + hosil qilish buyrug'i.
    assert "Fernet" in message
    assert "generate_key" in message


def test_our_validator_message_does_not_repeat_the_key() -> None:
    """BIZNING matnimiz rad etilgan qiymatni takrorlamaydi.

    ⚠ Da'vo ATAYIN TOR va u shunday bo'lishi kerak. Butun
      `str(ValidationError)` tekshirilsa test QIZIL bo'lardi: pydantic
      ning O'ZI xabarga `input_value=...` ni qo'shadi va buni to'sib
      bo'lmaydi (`SecretStr` ham, `mode="after"` model validatori ham
      empirik sinaldi — ikkalasi ham xom kiritmani chop etadi).

      Shuning uchun bu yerda AYNAN o'zimiz yozgan xabar o'lchanadi, xato
      obyektining butun matni emas. Kengroq da'vo qo'yish testni
      pydantic ning ichki xulqiga bog'lab qo'yardi va uni "to'g'irlash"
      uchun kimdir foydali xato matnini olib tashlashi mumkin edi.

    Kengroq yo'l — muvaffaqiyatli ko'tarilgan ilovadagi `repr(settings)`
    — quyidagi test bilan yopilgan.
    """
    with pytest.raises(ValidationError) as excinfo:
        Settings(
            database_url=_REQUIRED_ENV["DATABASE_URL"],
            valkey_url=_REQUIRED_ENV["VALKEY_URL"],
            jwt_secret=_REQUIRED_ENV["JWT_SECRET"],
            nvr_credential_key=SecretStr(MALFORMED_KEY),
        )

    (error,) = excinfo.value.errors()
    assert MALFORMED_KEY not in error["msg"]


def test_settings_repr_masks_the_credential_keys(configure_keys: Callable[..., None]) -> None:
    """`repr(settings)` shifr kalitini OSHKOR QILMAYDI.

    ⚠ BU TESTNING MA'NOSI SENTRY: `sentry-sdk` istisno paytida LOKAL
      o'zgaruvchilarni yig'adi, `settings` esa `main.py::lifespan` da aynan
      lokal o'zgaruvchi. Oddiy `str` maydon bilan ilova ishga tushgandan
      keyingi HAR QANDAY istisno butun shifr kalitini Sentry'ga yuborardi
      — va kalit oshkor bo'lsa BARCHA NVR parollari, o'tmishdagilari ham,
      ochiladi.

    Nazorat bandi: kalitning haqiqiy qiymati testda ma'lum, ya'ni "yo'q"
    da'vosi bo'sh natijadan emas, aniq satrdan kelib chiqadi.
    """
    key = _new_key()
    retired = _new_key()
    configure_keys(key, retired=(retired,))

    rendered = repr(get_settings())

    assert key not in rendered
    assert retired not in rendered
    assert "**********" in rendered


def test_missing_key_fails_at_settings_construction() -> None:
    """Kalit UMUMAN berilmasa ham ilova ko'tarilmaydi.

    Maydon ATAYIN standart qiymatsiz. Bo'sh standart berilsa ilova
    shifrlashsiz ko'tarilardi va birinchi rekvizit yozuvida yiqilardi —
    aynan yuqoridagi testda rad etilgan xulq.
    """
    with pytest.raises(ValidationError) as excinfo:
        Settings(  # type: ignore[call-arg]
            database_url=_REQUIRED_ENV["DATABASE_URL"],
            valkey_url=_REQUIRED_ENV["VALKEY_URL"],
            jwt_secret=_REQUIRED_ENV["JWT_SECRET"],
        )

    (error,) = excinfo.value.errors()
    assert error["loc"] == ("nvr_credential_key",)
    assert error["type"] == "missing"


def test_empty_retired_keys_is_accepted(configure_keys: Callable[..., None]) -> None:
    """`NVR_CREDENTIAL_KEYS_RETIRED` bo'sh satr bo'lsa ham sozlama quriladi.

    Bu STANDART holat: rotatsiya hali bo'lmagan o'rnatmada iste'foga
    chiqqan kalit yo'q. Maydon majburiy bo'lsa har bir yangi o'rnatma
    soxta qiymat yozishga majbur bo'lardi.
    """
    configure_keys(_new_key())

    settings = get_settings()

    assert settings.nvr_credential_keys_retired.get_secret_value() == ""
    assert split_retired_keys(settings.nvr_credential_keys_retired.get_secret_value()) == ()
    # Va shifrlash baribir ishlaydi.
    assert decrypt_nvr_password(encrypt_nvr_password(PASSWORD)) == PASSWORD


@pytest.mark.parametrize(
    ("raw", "expected_count"),
    [
        ("", 0),
        ("   ", 0),
        ("a-key", 1),
        ("a-key,b-key", 2),
        (" a-key , b-key ", 2),
        ("a-key,,b-key", 2),
    ],
)
def test_split_retired_keys_tolerates_operator_typing(raw: str, expected_count: int) -> None:
    """Vergul bilan ajratilgan ro'yxat bo'sh va ortiqcha bo'shliqlarga chidamli.

    Kalitlar muhit o'zgaruvchisiga QO'LDA yoziladi (rotatsiya kuni,
    ehtimol shoshilinch). Ortiqcha bo'sh joy yoki qo'shaloq vergul
    `Fernet("")` ni chaqirib butun ilovani yiqitardi.
    """
    assert len(split_retired_keys(raw)) == expected_count


def test_current_key_version_is_a_positive_integer() -> None:
    """`nvr_credentials.key_version > 0` CHECK'i bilan MOS.

    Konstanta o'sha ustunga yoziladi; nol yoki manfiy qiymat qatorni
    `23514` bilan rad ettirardi va sabab shifrlash kodida ko'rinmasdi.
    """
    assert isinstance(CURRENT_KEY_VERSION, int)
    assert CURRENT_KEY_VERSION > 0


# ---------------------------------------------------------------------------
# D-12 — sir jurnalga tushmaydi
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("key", ["nvr_password", "rtsp_password", "NVR_PASSWORD"])
def test_password_is_censored_in_logs_under_the_nvr_keys(
    configure_keys: Callable[..., None], key: str
) -> None:
    """Parol (va uning shifrmatni) `SENSITIVE_KEYS` ostida maskalanadi.

    ⚠ Bu testning MA'NOSI: 1-faza `logging.py:59-61` da `nvr_password` va
    `rtsp_password` ni oldindan ro'yxatga olgan, LEKIN o'sha da'vo bu
    fazaning O'Z maydon nomlari bilan hech qachon o'lchanmagan. Filtr
    FAQAT kalit nomiga qaraydi, ya'ni "allaqachon qamralgan" degan
    taxmin nomlar mos kelmasa jimgina yolg'on bo'lardi.
    """
    configure_keys(_new_key())
    token = encrypt_nvr_password(PASSWORD)

    result = censor_secrets(None, "info", {"event": "nvr.credential.saved", key: token})

    assert result[key] == CENSORED


def test_password_is_censored_inside_nested_error_detail(
    configure_keys: Callable[..., None],
) -> None:
    """Ichma-ich `error_detail` ham qamraladi (§S-7, T-03-28).

    `nvr_discovery_runs.error_detail` — XOM ISAPI javobi tushadigan jsonb.
    Yuqori daraja tekshirilib, ichkarisi tekshirilmasa u yerdagi rekvizit
    bazaga o'tirib qolardi.
    """
    configure_keys(_new_key())

    result = censor_secrets(
        None,
        "info",
        {"event": "nvr.discovery.failed", "error_detail": {"request": {"nvr_password": PASSWORD}}},
    )

    assert result["error_detail"] == {"request": {"nvr_password": CENSORED}}
