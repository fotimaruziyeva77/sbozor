"""bot-service konfiguratsiyasi — 12-faktor uslubida, muhit o'zgaruvchilaridan.

`services/core-api/app/settings.py` va `services/cv-service/app/settings.py`
naqshi: bitta `Settings` obyekti, uni kirish nuqtasi TO'LIQ quradi, sirlar
faqat muhitdan keladi va hech qachon standart qiymatga ega bo'lmaydi.

=============================================================================
⚠⚠ BU YERDA BAZA ULANISHI YO'Q — VA BU UNUTILGAN EMAS, QAROR (D-08/1).

`core-api` va `cv-service` ning `Settings` larida `database_url` bor.
Bu servisda u ATAYIN yo'q: bot bazani KO'RMAYDI va uning yagona ma'lumot
manbai `core_api_url` ostidagi ichki API (07-08). Sabab xavfsizlik
chegarasida: Telegram'dan kelgan oqim AUTENTIFIKATSIYA QILINMAGAN va
loyihaning ishonch chegarasidan TASHQARIDA, ya'ni unga baza ulanishini
berish IKKINCHI RLS yuzasini ochardi (T-07-01). Taqiq
`services/bot-service/tests/unit/test_runtime_deps.py` da MEXANIK.
=============================================================================
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_CORE_API_URL = "http://core-api:8000"
"""Compose tarmog'ining ICHIDAGI manzil — `core-api` xost portiga tayanmaydi."""

DEFAULT_VALKEY_URL = "redis://cache:6379/1"
"""⛔ `db 1` — VA BU RAQAM TASODIFIY EMAS.

=============================================================================
`core-api` va `cv-service` `db 0` da ishlaydi (`compose.yaml`:
`VALKEY_URL: ${VALKEY_URL:-redis://cache:6379/0}`). U yerda uchta narsa
yashaydi: login rate-limit sanagichlari (`app/security/ratelimit.py`),
sessiya keshi va `sbozor:jobs` navbati.

aiogram ning FSM kalitlarini O'SHA MAKONGA qo'shish ikki xavf tug'dirardi:

  1. `FLUSHDB` (yoki nomlar to'qnashuvi) xatosi IKKI TIZIMNI BIRDAN
     yiqitardi: bitta noto'g'ri buyruq bot dialoglarini ham, navbat va
     rate-limitni ham o'chirardi.
  2. «Kim bu kalitni yozdi?» savoli har nosozlikda qaytardi — `core-api`
     mi yoki bot? Ajratilgan makonda javob KALIT MAKONINING O'ZIDA.

⚠ `cache` konteyneri `--save "" --appendonly no` bilan ishlaydi, ya'ni
  FSM holati qayta ko'tarilganda YO'QOLADI. Bu qonuniy: FSM — bir necha
  soniyalik dialog bosqichi, biznes holati emas. Biznes holati Postgres'da
  (`vendor_telegram_bindings`) va u bu servisga TEGISHLI EMAS.
=============================================================================
"""


class Settings(BaseSettings):
    """bot-service ning YAGONA sozlama obyekti.

    ⚠ ENTRYPOINT BO'YICHA BO'LINMAYDI (`core-api` ning `compose.yaml`
      izohidagi o'lchangan qaror): ikki model jimgina ajralib ketardi va
      bir entrypoint qo'shgan maydonni ikkinchisi ko'rmay qolardi.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Telegram (DQ-1: long-polling, webhook YO'Q) ---
    #
    # ⛔ MAJBURIY VA STANDARTSIZ. `:-` bilan bo'sh standart berish
    #    `03-04` dagi `NVR_CREDENTIAL_KEY` qarorining teskarisi bo'lardi:
    #    bo'sh token bilan servis muvaffaqiyatli KO'TARILARDI va nosozlik
    #    faqat birinchi `getUpdates` da — hech kim qaramayotgan paytda —
    #    chiqardi. `Bot(token=...)` ni bo'sh satr bilan qurish esa
    #    `TokenValidationError` beradi, ya'ni xato matni «token yaroqsiz»
    #    bo'lib, sababi «token berilmagan» ekani YO'QOLARDI.
    #
    # ⚠⚠ MAYDON NOMI `bot_token` EMAS, `telegram_bot_token` — VA BU
    #    QULAYLIK EMAS, SHART. Loyihada `validation_alias` HECH QAYERDA
    #    ishlatilmaydi (o'lchandi: `core-api/app/settings.py` da nol
    #    uchrash): muhit kaliti maydon nomining KATTA HARFLI shakli va
    #    bu qoidaning O'ZI mexanik kafolat — `compose.yaml` dagi kalitni
    #    o'qigan odam maydonni ham biladi. `bot_token` deb nomlash
    #    `BOT_TOKEN` ni izlardi, `compose.yaml` esa `TELEGRAM_BOT_TOKEN`
    #    beradi (A1: alert supurgisi bilan AYNAN BIR XIL token) —
    #    natijada konteyner «Field required» bilan yiqilardi, token esa
    #    muhitda TURGAN bo'lardi va sabab topilishi qiyin bo'lardi.
    telegram_bot_token: SecretStr

    # --- `core-api` ning ichki API'si (07-08, D-10) ---
    core_api_url: str = DEFAULT_CORE_API_URL

    # ⛔ MAJBURIY: servis-servis tokeni. `hmac.compare_digest` bilan
    #    solishtiriladi va u foydalanuvchi sessiyasini TUG'DIRMAYDI (D-10).
    #    Bo'sh qiymat bilan bot ko'tarilardi va HAR bir ichki chaqiruv
    #    `401` olardi — sotuvchi uchun bu «bot buzuq» bo'lib ko'rinardi.
    bot_service_token: SecretStr

    # --- FSM ombori ---
    valkey_url: str = DEFAULT_VALKEY_URL

    # --- Kuzatuv ---
    sentry_dsn: str = ""
    log_level: str = "info"

    @field_validator("telegram_bot_token")
    @classmethod
    def _validate_bot_token(cls, value: SecretStr) -> SecretStr:
        """Bo'sh bot tokenini ISHGA TUSHISHDA rad etadi (T-07-02).

        Xato matnida KALIT NOMI bor, lekin QIYMAT yo'q — rad etilgan
        qiymat ta'rifi bo'yicha ishonchsiz va u jurnalga tushmasligi kerak.
        """
        if not value.get_secret_value().strip():
            raise ValueError(
                "TELEGRAM_BOT_TOKEN bo'sh bo'lishi mumkin emas. Bot tokensiz "
                "Telegram'ga UMUMAN ulana olmaydi va uni bo'sh standart bilan "
                "ko'tarish nosozlikni birinchi `getUpdates` ga surib qo'yardi. "
                "⚠ Lokal ishlab chiqishda ALOHIDA dev bot tokeni oling: prod "
                "tokeni bilan ikkinchi nusxa prod update'larini O'G'IRLAYDI "
                "(`.env.example` dagi ogohlantirish bandi)."
            )
        return value

    @field_validator("bot_service_token")
    @classmethod
    def _validate_bot_service_token(cls, value: SecretStr) -> SecretStr:
        """Bo'sh servis-servis tokenini ISHGA TUSHISHDA rad etadi (T-07-02)."""
        if not value.get_secret_value().strip():
            raise ValueError(
                "BOT_SERVICE_TOKEN bo'sh bo'lishi mumkin emas. U `core-api` "
                "ning `/internal/bot/*` yuzasiga YAGONA kirish yo'li (D-10) va "
                "busiz har chaqiruv `401` olardi — sotuvchi uchun bu «bot "
                "buzuq» bo'lib ko'rinardi, sabab esa jurnalda qolardi."
            )
        return value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Sozlamalarni bir marta o'qiydi va keshlaydi (`core-api` naqshi)."""
    # mypy majburiy maydonlarni argument sifatida kutadi, lekin
    # pydantic-settings ularni MUHITDAN to'ldiradi.
    return Settings()  # type: ignore[call-arg]
