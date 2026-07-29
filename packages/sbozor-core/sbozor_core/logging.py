"""Structured (JSON) logging — tenant konteksti va sir filtri bilan.

Multi-tenant tizimda log satri "nima bo'ldi" dan tashqari "QAYSI BOZORDA,
KIM tomonidan, QAYSI so'rovda" savollariga ham javob berishi kerak — aks
holda nizo paytida hodisani tiklab bo'lmaydi. Shuning uchun `request_id`,
`user_id` va `market_id` `contextvars` orqali bog'lanadi va HAR BIR satrga
avtomatik qo'shiladi (qo'lda uzatish unutiladi).

Ikkinchi vazifa — sir sizishining oldini olish (T-01-16). Loglar Sentry'ga
va fayl/stdout oqimiga ketadi, ya'ni ular ilova chegarasidan CHIQADI.
`censor_secrets` protsessori parol, hash va token qiymatlarini `***` bilan
almashtiradi.
"""

from __future__ import annotations

import logging
import sys
from uuid import UUID

import structlog
from structlog.typing import EventDict, WrappedLogger

__all__ = [
    "CENSORED",
    "SENSITIVE_KEYS",
    "bind_request_context",
    "censor_secrets",
    "clear_request_context",
    "configure_logging",
]

CENSORED = "***"
"""Maskalangan qiymat o'rniga yoziladigan belgi."""

SENSITIVE_KEYS = frozenset(
    {
        # Parol yo'li
        "password",
        "password_hash",
        "old_password",
        "new_password",
        "raw_password",
        # D-02: admin bergan vaqtinchalik parol javobda BIR MARTA ochiq
        # ketadi — u log'ga tushsa, "bir martalik" degan kafolat yo'qoladi
        # va parol jurnalda muddatsiz yashab qolardi.
        "temporary_password",
        # Token va sirlar
        "token",
        "access_token",
        "refresh_token",
        "jwt_secret",
        "secret",
        "api_key",
        # HTTP sarlavhalari (middleware ularni butun bir dict sifatida yozishi mumkin)
        "authorization",
        "cookie",
        "set-cookie",
        # NVR rekvizitlari (spec §5 — RTSP parollari shifrlangan saqlanadi)
        "rtsp_password",
        "nvr_password",
    }
)
"""Log'ga HECH QACHON tushmasligi kerak bo'lgan kalitlar (kichik harfda)."""


def censor_secrets(
    logger: WrappedLogger,
    method_name: str,
    event_dict: EventDict,
) -> EventDict:
    """Sirlarni maskalaydigan structlog protsessori (T-01-16).

    Faqat KALIT nomiga qaraydi — qiymat ichidan sir "topishga" urinmaydi
    (bu yolg'on-musbat va yolg'on-manfiy beradi). Shuning uchun qoida
    oddiy: sirni har doim nomlangan kalit sifatida uzating, `event`
    matnining ichiga qo'shmang.
    """
    for key in list(event_dict):
        if isinstance(key, str) and key.lower() in SENSITIVE_KEYS:
            event_dict[key] = CENSORED
    return event_dict


def configure_logging(level: str = "info") -> None:
    """structlog'ni sozlaydi. Bir marta, `lifespan` boshida chaqiriladi.

    Chiqish — stdout'ga JSON satrlari (12-faktor): konteyner loglarini
    Docker/Sentry/journald yig'adi, faylga yozish yo'q.
    """
    numeric_level = logging.getLevelNamesMapping().get(level.upper(), logging.INFO)

    # Stdlib logging (uvicorn, sqlalchemy) ham bir xil oqim va darajaga tushsin.
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=numeric_level)

    structlog.configure(
        processors=[
            # 1) Avval kontekst qo'shiladi — shunda u ham senzuradan o'tadi.
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            # 2) Senzura — renderergacha, aks holda sir allaqachon satrga aylangan bo'ladi.
            censor_secrets,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(numeric_level),
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )


def bind_request_context(
    request_id: str,
    user_id: UUID | str | None = None,
    market_id: UUID | str | None = None,
) -> None:
    """So'rov kontekstini joriy vazifaga bog'laydi.

    `contextvars` asyncio vazifasi bo'yicha izolyatsiyalanadi, ya'ni parallel
    so'rovlar bir-birining kontekstini ko'rmaydi. Shunga qaramay har so'rov
    boshida `clear_request_context()` chaqirilishi kerak — vazifa qayta
    ishlatilgan holatda eski `market_id` log'da qolib ketmasligi uchun.
    """
    structlog.contextvars.bind_contextvars(
        request_id=request_id,
        user_id=str(user_id) if user_id is not None else None,
        market_id=str(market_id) if market_id is not None else None,
    )


def clear_request_context() -> None:
    """Bog'langan so'rov kontekstini tozalaydi (har so'rov boshida)."""
    structlog.contextvars.clear_contextvars()
