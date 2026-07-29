"""core-api konfiguratsiyasi — 12-faktor uslubida, muhit o'zgaruvchilaridan.

Sirlar (JWT_SECRET, DB parollari) HECH QACHON kodda yoki repoda saqlanmaydi —
ular faqat muhitdan keladi (`.env` gitignore'da, `.env.example` da faqat
kalit nomlari).
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# PyJWT 2.11+ HS256 uchun kalit uzunligini majburiy tekshiradi
# (RFC 7518 §3.2: kalit >= hash chiqishi = 256 bit = 32 bayt).
MIN_JWT_SECRET_BYTES = 32


class Settings(BaseSettings):
    """core-api ish vaqti sozlamalari."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Ma'lumotlar bazasi ---
    # ILOVA roli (sbozor_app): NOSUPERUSER + NOBYPASSRLS.
    # Bu yerga `postgres` superuseri berilsa tenant izolyatsiyasi butunlay
    # yo'qoladi va hech bir test buni ko'rsatmaydi.
    database_url: str
    # DDL egasi (sbozor_owner) — faqat Alembic `migrate` jobida ishlatiladi.
    migration_database_url: str = ""

    # --- Kesh / navbat ---
    valkey_url: str

    # --- Auth ---
    jwt_secret: str
    jwt_issuer: str = "sbozor"
    jwt_audience: str = "sbozor-api"
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 30
    # Dev'da HTTP -> false; prod'da (TLS ortida) true bo'lishi SHART.
    cookie_secure: bool = False

    # --- Kuzatuv ---
    sentry_dsn: str = ""
    log_level: str = "info"

    @field_validator("jwt_secret")
    @classmethod
    def _validate_jwt_secret(cls, value: str) -> str:
        if len(value.encode("utf-8")) < MIN_JWT_SECRET_BYTES:
            raise ValueError(
                f"JWT_SECRET kamida {MIN_JWT_SECRET_BYTES} bayt bo'lishi kerak. "
                'Hosil qilish: python -c "import secrets;print(secrets.token_urlsafe(48))"'
            )
        return value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Sozlamalarni bir marta o'qiydi va keshlaydi."""
    # mypy majburiy maydonlarni argument sifatida kutadi, lekin pydantic-settings
    # ularni MUHITDAN to'ldiradi (pydantic mypy plagini atayin yoqilmagan).
    # Yetishmayotgan qiymat ish vaqtida `ValidationError` beradi — bu kutilgan xulq.
    return Settings()  # type: ignore[call-arg]
