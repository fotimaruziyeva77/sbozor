"""Sentry ilmoqlari va uning O'RNATILISHI — `cv-service` ning IKKALA kirish nuqtasi uchun.

=============================================================================
NEGA BU MODUL ALOHIDA VA NEGA U `core-api` NIKINING NUSXASI EMAS.

`services/core-api/app/observability.py` — 270 qatorlik modul va uning
maskalash qoidalari `go2rtc` ning `src=rtsp://user:pass@host` yo'liga
sozlangan (T-03-89, 03-13). `cv-service` esa RTSP ga UMUMAN tegmaydi: u
kadrni S3 dan oladi va natijani Postgres'ga yozadi.

Shuning uchun bu yerda o'sha faylning NUSXASI emas, AYNI SINFDAGI, lekin
BU servisning sirlariga sozlangan qisqa moduli turadi:

    Postgres/Valkey/S3 URL larining `user:pass@host` qismi
    `S3_SECRET_KEY`, `DATABASE_URL` kabi kalitlar `extra` da

⚠ NUSXA OLISH ATAYIN RAD ETILDI: ikki nusxa ikki xil qoidaga ajralib
  ketardi va «qaysi biri to'g'ri?» savoli har nosozlikda qaytardi.
  Umumiy primitivlar kerak bo'lgan kuni ular `packages/sbozor-core` ga
  ko'chadi — UCHALA servis uchun bitta manba (bugun bunga ehtiyoj yo'q:
  qoidalar haqiqatan boshqa).

=============================================================================
⚠ IKKALA ILMOQ HAM MAJBURIY (`core-api` da o'lchangan, T-04-98).

`before_send` HODISANI, `before_breadcrumb` esa undan OLDIN yig'ilgan
izlarni tozalaydi. Bittasini qoldirish ikkinchisini bir chaqiruvdan narida
qoldirardi — sir hodisa yuz bermasdan turib navbatga tushardi.

⚠ `sentry_sdk` FAQAT SHU MODULGA import qilinadi. Shunda `before_send`siz
  o'rnatish yo'li UMUMAN ochilmaydi.
=============================================================================
"""

from __future__ import annotations

import re
from typing import Any, Final

import sentry_sdk
from sentry_sdk.types import Breadcrumb, BreadcrumbHint, Event, Hint

__all__ = [
    "MASKED",
    "SENSITIVE_KEYS",
    "init_sentry",
    "mask_secrets",
    "scrub_breadcrumb",
    "scrub_event",
    "sentry_installed",
]

MASKED: Final = "***"
"""Maskalangan qiymatning YAGONA ko'rinishi — testda ham shu satr izlanadi."""

SENSITIVE_KEYS: Final = frozenset(
    {
        "password",
        "secret",
        "token",
        "dsn",
        "sentry_dsn",
        "database_url",
        "valkey_url",
        "s3_access_key",
        "s3_secret_key",
    }
)
"""Sentry `extra`/`vars` ichida BUTUNLAY maskalanadigan kalitlar.

⚠ `database_url` va `valkey_url` shu ro'yxatda va bu ATAYIN: ular
  «URL» degan zararsiz nom ostida PAROL tashiydi
  (`postgresql+asyncpg://sbozor_app:PAROL@db:5432/sbozor`).
"""

_URL_USERINFO: Final = re.compile(r"(?i)\b([a-z][a-z0-9+.\-]*://)[^/@\s'\"]+@")
"""HAR QANDAY sxemadagi `scheme://user:pass@host` — userinfo BUTUNLAY kesiladi.

⚠ SXEMA RO'YXATI YOZILMAGAN (§S-10 — ro'yxat emas, predikat): bu servis
  bugun `postgresql+asyncpg://`, `redis://` va `http://` bilan ishlaydi,
  ertaga to'rtinchisi qo'shilsa qoida o'zgarmasligi kerak.

⚠ URL QAYTA QURILMAYDI (parse -> tahrir -> unparse): maqsad qiymatni
  saqlab qolish emas, sirni CHIQARMASLIK. Qayta qurish kutilmagan shaklda
  istisno berardi va o'sha istisnoning matni yana sirni tashirdi
  (`core-api/app/observability.py` da o'lchangan sabab).
"""


def mask_secrets(value: str) -> str:
    """Satrdagi URL rekvizitini maskalaydi — MATN darajasida."""
    return _URL_USERINFO.sub(rf"\g<1>{MASKED}@", value)


def _mask_deep(node: Any) -> Any:
    """Hodisadagi HAR satr qiymatiga `mask_secrets()` ni, sezgir KALITGA `MASKED` ni qo'llaydi.

    ⚠ NEGA CHUQUR VA NEGA MAYDON RO'YXATI EMAS: sir Sentry hodisasiga
      kamida uch joydan tushadi — istisno matni, stack freymlarning lokal
      o'zgaruvchilari va `extra`. Ro'yxat bilan yurish to'rtinchi joy
      paydo bo'lganda JIMGINA eskirardi.
    """
    if isinstance(node, str):
        return mask_secrets(node)
    if isinstance(node, dict):
        return {
            key: MASKED if str(key).lower() in SENSITIVE_KEYS else _mask_deep(value)
            for key, value in node.items()
        }
    if isinstance(node, list):
        return [_mask_deep(item) for item in node]
    return node


def scrub_event(event: Event, hint: Hint) -> Event | None:
    """`before_send` — hodisa jo'natilishidan OLDIN tozalanadi."""
    del hint
    cleaned: Event = _mask_deep(event)
    return cleaned


def scrub_breadcrumb(crumb: Breadcrumb, hint: BreadcrumbHint) -> Breadcrumb | None:
    """`before_breadcrumb` — iz YIG'ILAYOTGANDA tozalanadi."""
    del hint
    cleaned: Breadcrumb = _mask_deep(crumb)
    return cleaned


def init_sentry(dsn: str) -> bool:
    """Sentry'ni IKKALA ilmoq bilan birga o'rnatadi. Bo'sh DSN — no-op.

    ⚠ CHAQIRUV JOYI IKKITA VA HAR IKKALASI HAM JARAYON, kod kirish nuqtasi
      EMAS (04-12 ning hisobi «ikkita kirish nuqtasi» edi va aynan shu
      shakl uchinchi JARAYONNI ko'rmay qolgan):

        1. `app/worker.py::_open_worker_resources`  — `cv-service` konteyneri
           (`taskiq worker`, `WORKER_STARTUP` ilmog'i)
        2. `app/main.py::lifespan`                  — health yuzasi

      Mavjudligi IKKI darvozada tekshiriladi: `tests/unit/
      test_sentry_processes.py` (root — `compose.yaml` dan HOSILA) va
      `services/cv-service/tests/unit/test_sentry_entrypoints.py`
      (obyekt darajasida, shu image ichida).

    Returns:
        `True` — o'rnatildi; `False` — DSN bo'sh. Qiymat chaqiruvchiga
        JURNALGA yozish uchun beriladi: «Sentry o'chirilgan» holati JIM
        bo'lmasligi kerak, aks holda uni «ishlayapti» deb o'ylash mumkin.
    """
    if not dsn:
        return False
    sentry_sdk.init(
        dsn=dsn,
        before_send=scrub_event,
        before_breadcrumb=scrub_breadcrumb,
        send_default_pii=False,
    )
    return True


def sentry_installed() -> bool:
    """Shu JARAYONDA `sentry_sdk.init()` allaqachon bajarilganmi."""
    return bool(sentry_sdk.is_initialized())
