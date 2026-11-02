"""Bozor kassalari — Payme va Click (2026-10-30 buyurtmachi qarori).

=============================================================================
⛔ HAR BOZOR — ALOHIDA YURIDIK SHAXS, ALOHIDA KASSA.

Pul bozorning o'z bank hisobiga tushadi, ya'ni har bozor Payme va Click'da
o'z kassasini ochadi. Kassa so'rovida bozor YO'Q — faqat rasta raqami
(`account.rasta` / `merchant_trans_id`). Shuning uchun bozor SO'ROVNING
O'ZIDAN aniqlanadi:

  * Payme — `Authorization: Basic Paycom:<kalit>`: kalit qaysi kassaniki
    bo'lsa, o'sha bozor;
  * Click — `service_id`: kimniki bo'lsa, o'sha bozorning `secret_key` i
    bilan imzo tekshiriladi.

Rasta kodi bozor ichida noyob, bozorlar orasida emas — shu sabab bozor
hech qachon rasta kodidan TAXMIN QILINMAYDI.
=============================================================================
SOZLAMA (sirlar bazada emas, faqat `.env` da):

  PAYME_MERCHANTS=[{"slug": "karmana", "market_id": "<uuid>",
                    "merchant_id": "...", "key": "...",
                    "ikpu": "...", "package_code": "..."}]
  CLICK_MERCHANTS=[{"slug": "karmana", "market_id": "<uuid>",
                    "service_id": "...", "merchant_id": "...",
                    "secret_key": "..."}]
  PAY_DEFAULT_MARKET=karmana   # eski QR manzili /pay/{rasta} qaysi bozorniki

Eski bitta-kassa sozlamalari (`PAYME_KEY` + `PAYME_MARKET_ID`, `CLICK_*`)
hamon o'qiladi — Karmanadagi rastalarga yopishtirilgan QR-kodlar o'zgarmaydi.

⛔ Xato yozuv JIMGINA tashlanmaydi: jurnalga `payment_merchant_invalid`
   yoziladi va u yozuv e'tiborga olinmaydi (fail-closed) — boshqa bozorlar
   ishlayveradi, buzuq yozuvli bozorda esa to'lov 503/xato beradi.
"""

from __future__ import annotations

import hmac
import json
import re
from dataclasses import dataclass, field, replace
from functools import lru_cache
from typing import TYPE_CHECKING, Any
from uuid import UUID

import structlog

if TYPE_CHECKING:
    from app.settings import Settings

__all__ = [
    "ClickMerchant",
    "PaymeMerchant",
    "click_by_service",
    "click_for_market",
    "default_market",
    "market_by_slug",
    "payme_by_key",
    "payme_configured",
    "payme_match",
    "payme_for_market",
]

log = structlog.get_logger(__name__)

_SLUG = re.compile(r"^[a-z][a-z0-9-]{1,31}$")
_FIELD = re.compile(r"^[a-z][a-z0-9_]{1,31}$")
LEGACY_SLUG = "asosiy"


@dataclass(frozen=True, slots=True)
class PaymeMerchant:
    slug: str
    market_id: UUID
    merchant_id: str
    key: str = field(repr=False)
    ikpu: str = ""
    package_code: str = ""
    account_field: str = "rasta"
    # Payme sinov muhiti (test.paycom.uz) shu kassaning SINOV kaliti bilan
    # so'raydi. Bo'sh bo'lsa sinov so'rovlari -32504 oladi. Qaysi manzildan
    # qabul qilinishi `payme.py::_merchant` da tekshiriladi.
    test_key: str = field(default="", repr=False)
    # Fiskal chekdagi QQS foizi (Payme `detail.items[].vat_percent`). Bozor QQS
    # to'lovchi bo'lsa 12, aks holda 0 (261102: Karmana — 12%).
    vat_percent: int = 0


@dataclass(frozen=True, slots=True)
class ClickMerchant:
    slug: str
    market_id: UUID
    service_id: str
    merchant_id: str
    secret_key: str = field(repr=False)


def _items(raw: str, name: str) -> list[dict[str, Any]]:
    if not raw.strip():
        return []
    try:
        data = json.loads(raw)
    except ValueError:
        log.error("payment_merchant_invalid", source=name, reason="json")
        return []
    if not isinstance(data, list):
        log.error("payment_merchant_invalid", source=name, reason="not_a_list")
        return []
    return [item for item in data if isinstance(item, dict)]


def _uuid(value: Any) -> UUID | None:
    try:
        return UUID(str(value))
    except ValueError:
        return None


def _text(item: dict[str, Any], key: str) -> str:
    value = item.get(key)
    return str(value).strip() if value is not None else ""


def _unique[T](merchants: list[T], *keys: str, source: str) -> tuple[T, ...]:
    """Takrorlangan slug/bozor/kalit — IKKALASI ham tashlanadi.

    Birinchisini «yutgan» deb qoldirish pul qaysi bozorga yozilishini fayl
    tartibiga bog'lab qo'yardi; ikkalasini olib tashlash xatoni darhol ko'rsatadi.
    """
    bad: set[int] = set()
    for key in keys:
        seen: dict[str, int] = {}
        for index, merchant in enumerate(merchants):
            value = str(getattr(merchant, key))
            if not value:  # ixtiyoriy maydon (sinov kaliti) — bo'shlar takror emas
                continue
            if value in seen:
                bad |= {index, seen[value]}
                log.error("payment_merchant_invalid", source=source, reason=f"duplicate_{key}")
            seen[value] = index
    return tuple(m for i, m in enumerate(merchants) if i not in bad)


@lru_cache(maxsize=8)
def _vat(value: Any, source: str) -> int:
    """QQS foizi 0..100 butun son; noto'g'ri bo'lsa 0 va jurnalga xato."""
    text = str(value).strip() if value is not None else ""
    if not text:
        return 0
    if text.isdigit() and 0 <= int(text) <= 100:
        return int(text)
    log.error("payment_merchant_invalid", source=source, reason="vat_percent")
    return 0


@lru_cache(maxsize=8)
def _payme(
    raw: str, legacy: tuple[str, str, str, str, str, str, str, str, str]
) -> tuple[PaymeMerchant, ...]:
    out: list[PaymeMerchant] = []
    key, market, merchant_id, ikpu, package_code, slug, field_, test_key, vat = legacy
    field_ = field_ if _FIELD.match(field_) else "rasta"
    if key and market:
        market_id = _uuid(market)
        if market_id is None:
            log.error("payment_merchant_invalid", source="PAYME_MARKET_ID", reason="uuid")
        else:
            out.append(
                PaymeMerchant(
                    slug,
                    market_id,
                    merchant_id,
                    key,
                    ikpu,
                    package_code,
                    field_,
                    test_key,
                    _vat(vat, "PAYME_VAT_PERCENT"),
                )
            )
    for item in _items(raw, "PAYME_MERCHANTS"):
        market_id = _uuid(item.get("market_id"))
        slug_i, key_i = _text(item, "slug"), _text(item, "key")
        if (
            market_id is None
            or not _SLUG.match(slug_i)
            or not key_i
            or not _text(item, "merchant_id")
        ):
            log.error("payment_merchant_invalid", source="PAYME_MERCHANTS", slug=slug_i)
            continue
        out.append(
            PaymeMerchant(
                slug_i,
                market_id,
                _text(item, "merchant_id"),
                key_i,
                _text(item, "ikpu"),
                _text(item, "package_code"),
                field_i if _FIELD.match(field_i := _text(item, "account_field")) else "rasta",
                _text(item, "test_key"),
                _vat(item.get("vat_percent"), "PAYME_MERCHANTS"),
            )
        )
    merchants = _unique(out, "slug", "market_id", "key", "test_key", source="payme")
    # Sinov kaliti boshqa (yoki o'sha) kassaning ASOSIY kaliti bilan bir xil
    # bo'lsa, qaysi biri ekanini bilib bo'lmaydi — sinov kaliti o'chiriladi.
    main_keys = {m.key for m in merchants}
    clean: list[PaymeMerchant] = []
    for m in merchants:
        if m.test_key and m.test_key in main_keys:
            log.error(
                "payment_merchant_invalid", source="payme", slug=m.slug, reason="test_key_is_main"
            )
            m = replace(m, test_key="")
        clean.append(m)
    return tuple(clean)


@lru_cache(maxsize=8)
def _click(raw: str, legacy: tuple[str, str, str, str, str]) -> tuple[ClickMerchant, ...]:
    out: list[ClickMerchant] = []
    secret, service_id, merchant_id, market, slug = legacy
    if secret and service_id and market:
        market_id = _uuid(market)
        if market_id is None:
            log.error("payment_merchant_invalid", source="CLICK_MARKET_ID", reason="uuid")
        else:
            out.append(ClickMerchant(slug, market_id, service_id, merchant_id, secret))
    for item in _items(raw, "CLICK_MERCHANTS"):
        market_id = _uuid(item.get("market_id"))
        slug_i = _text(item, "slug")
        service_i, secret_i = _text(item, "service_id"), _text(item, "secret_key")
        if market_id is None or not _SLUG.match(slug_i) or not service_i or not secret_i:
            log.error("payment_merchant_invalid", source="CLICK_MERCHANTS", slug=slug_i)
            continue
        out.append(
            ClickMerchant(slug_i, market_id, service_i, _text(item, "merchant_id"), secret_i)
        )
    return _unique(out, "slug", "market_id", "service_id", source="click")


def _legacy_slug(settings: Settings) -> str:
    return settings.pay_default_market or LEGACY_SLUG


def payme_merchants(settings: Settings) -> tuple[PaymeMerchant, ...]:
    return _payme(
        settings.payme_merchants.get_secret_value(),
        (
            settings.payme_key.get_secret_value(),
            settings.payme_market_id,
            settings.payme_merchant_id,
            settings.payme_ikpu,
            settings.payme_package_code,
            _legacy_slug(settings),
            settings.payme_account_field,
            settings.payme_test_key.get_secret_value(),
            str(settings.payme_vat_percent),
        ),
    )


def click_merchants(settings: Settings) -> tuple[ClickMerchant, ...]:
    return _click(
        settings.click_merchants.get_secret_value(),
        (
            settings.click_secret_key.get_secret_value(),
            settings.click_service_id,
            settings.click_merchant_id,
            settings.click_market_id,
            _legacy_slug(settings),
        ),
    )


def payme_configured(settings: Settings) -> bool:
    return bool(payme_merchants(settings))


def payme_match(settings: Settings, key: str) -> tuple[PaymeMerchant | None, bool]:
    """Kalit bo'yicha kassa va bu SINOV kalitimi.

    Hamma kassaning hamma kaliti solishtiriladi (vaqt farqi bermaslik uchun).
    Sinov kaliti qaysi manzildan qabul qilinishini chaqiruvchi hal qiladi.
    """
    found: PaymeMerchant | None = None
    is_test = False
    raw = key.encode()
    for merchant in payme_merchants(settings):
        if hmac.compare_digest(merchant.key.encode(), raw):
            found, is_test = merchant, False
        if merchant.test_key and hmac.compare_digest(merchant.test_key.encode(), raw):
            found, is_test = merchant, True
    return found, is_test


def payme_by_key(settings: Settings, key: str) -> PaymeMerchant | None:
    """Faqat ASOSIY kalit bo'yicha kassa (sinov kaliti bu yerda o'tmaydi)."""
    merchant, is_test = payme_match(settings, key)
    return None if is_test else merchant


def payme_for_market(settings: Settings, market_id: UUID) -> PaymeMerchant | None:
    return next((m for m in payme_merchants(settings) if m.market_id == market_id), None)


def click_by_service(settings: Settings, service_id: str) -> ClickMerchant | None:
    return next((m for m in click_merchants(settings) if m.service_id == service_id), None)


def click_for_market(settings: Settings, market_id: UUID) -> ClickMerchant | None:
    return next((m for m in click_merchants(settings) if m.market_id == market_id), None)


def market_by_slug(settings: Settings, slug: str) -> UUID | None:
    """QR manzilidagi bozor nomi -> bozor (Payme yoki Click kassasi bo'lsa)."""
    for payme in payme_merchants(settings):
        if payme.slug == slug:
            return payme.market_id
    for click in click_merchants(settings):
        if click.slug == slug:
            return click.market_id
    return None


def default_market(settings: Settings) -> UUID | None:
    """Eski QR manzili `/pay/{rasta}` — `PAY_DEFAULT_MARKET` bozori."""
    return market_by_slug(settings, _legacy_slug(settings))
