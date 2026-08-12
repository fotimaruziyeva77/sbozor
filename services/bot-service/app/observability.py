"""Sentry ilmoqlari va uning O'RNATILISHI — `bot-service` ning kirish nuqtasi uchun.

=============================================================================
NEGA BU MODUL ALOHIDA VA NEGA U NUSXA EMAS.

`services/cv-service/app/observability.py` o'z docstringida bu savolga
allaqachon javob bergan: `core-api` niki `go2rtc` ning
`src=rtsp://user:pass@host` yo'liga sozlangan, `cv-service` niki esa S3 va
Postgres URL lariga. `bot-service` uchalasidan ham BOSHQA sirlarni tashiydi:

    `TELEGRAM_BOT_TOKEN`  — Bot API URL ning YO'L QISMIDA yuradi
                            (`https://api.telegram.org/bot<TOKEN>/getUpdates`),
                            ya'ni u `user:pass@host` NAQSHIGA MOS KELMAYDI
                            va URL maskalash qoidasi uni O'TKAZIB YUBORARDI
    `BOT_SERVICE_TOKEN`   — `Authorization: Bearer …` sarlavhasida (D-10)
    `VALKEY_URL`          — «URL» degan zararsiz nom ostida parol tashiydi

⛔ AYNAN SHU SABABDAN BU YERDA QO'SHIMCHA, TOKENGA MO'LJALLANGAN NAQSH BOR
   (`_BOT_TOKEN_IN_URL`). Uni `core-api`/`cv-service` ga qo'shish MA'NOSIZ
   edi: u yerda Bot API URL i hech qachon qurilmaydi. Umumiy primitivlar
   kerak bo'lgan kuni ular `packages/sbozor-core` ga ko'chadi — bugun
   qoidalar haqiqatan BOSHQA.

=============================================================================
⚠ IKKALA ILMOQ HAM MAJBURIY (`core-api` da o'lchangan, T-04-98).

`before_send` HODISANI, `before_breadcrumb` esa undan OLDIN yig'ilgan
izlarni tozalaydi. Bittasini qoldirish ikkinchisini bir chaqiruvdan narida
qoldirardi — sir hodisa yuz bermasdan turib navbatga tushardi.

=============================================================================
⚠ SDK NING XOM `init()` CHAQIRUVI FAQAT SHU MODULDA UCHRAYDI — pastdagi
  `init_sentry()` ning ichida, AYNAN BIR MARTA. Shunda `before_send`siz
  o'rnatish yo'li UMUMAN ochilmaydi.

  ⛔ Bu darvoza MEXANIK va u LITERAL SANOG'I bilan o'lchanadi (07-01 qabul
    mezoni): shu sababdan xom chaqiruvning matni bu faylda ham, `app/main.py`
    da ham IZOHGA yozilmaydi — aks holda sanoq izohlardan shishib ketardi va
    darvoza ma'nosini yo'qotardi.

  ⚠ `sentry_sdk.capture_exception()` esa `app/main.py` da ATAYIN
    chaqiriladi va bu taqiqni BUZMAYDI: u SOZLAMA emas, XABAR BERISH
    chaqiruvi — o'rnatilmagan SDK ostida u shunchaki no-op. Taqiqning
    predikati «konfiguratsiyani ikkinchi joydan berish», «SDK ni umuman
    ko'rmaslik» EMAS.
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
        "bot_token",
        "telegram_bot_token",
        "bot_service_token",
        "valkey_url",
    }
)
"""Sentry `extra`/`vars` ichida BUTUNLAY maskalanadigan kalitlar.

⚠ `valkey_url` shu ro'yxatda va bu ATAYIN: u «URL» degan zararsiz nom
  ostida PAROL tashiydi (`redis://:PAROL@cache:6379/1`).

⚠ `bot_token` va `bot_service_token` ikkalasi ham bor, chunki ular
  `Settings` maydonlarining NOMI — istisno ko'tarilgan freymning lokal
  o'zgaruvchilari aynan shu nomlar ostida Sentry'ga tushadi.
"""

_URL_USERINFO: Final = re.compile(r"(?i)\b([a-z][a-z0-9+.\-]*://)[^/@\s'\"]+@")
"""HAR QANDAY sxemadagi `scheme://user:pass@host` — userinfo BUTUNLAY kesiladi.

⚠ SXEMA RO'YXATI YOZILMAGAN (§S-10 — ro'yxat emas, predikat): bu servis
  bugun `redis://` va `https://` bilan ishlaydi, ertaga uchinchisi
  qo'shilsa qoida o'zgarmasligi kerak.
"""

_BOT_TOKEN_IN_URL: Final = re.compile(r"(?i)(/bot)\d{5,}:[A-Za-z0-9_-]{20,}")
"""⛔ TELEGRAM TOKENI URL NING YO'L QISMIDA YURADI — VA BU YANGI SINF.

    https://api.telegram.org/bot123456789:AA…/getUpdates
                             ^^^^^^^^^^^^^^^^^^

Yuqoridagi `_URL_USERINFO` bu shaklni KO'RMAYDI: unda `@` yo'q, ya'ni
userinfo naqshiga umuman mos kelmaydi. `aiogram` esa tarmoq xatosida
so'ralgan URL ni istisno matniga qo'shadi — ya'ni token maskalanmasa u
Sentry hodisasiga TO'LIQ tushardi va o'sha token bilan istalgan odam
botning butun yozishmasini o'qiy olardi.

⚠ Naqsh TOKEN SHAKLI bo'yicha yozilgan (`<raqamlar>:<baza64ga o'xshash>`),
  qiymat bo'yicha EMAS: sozlamadagi konkret tokenni izlash rotatsiyadan
  keyin jimgina eskirardi.
"""


def mask_secrets(value: str) -> str:
    """Satrdagi URL rekvizitini va Telegram tokenini maskalaydi — MATN darajasida."""
    masked = _URL_USERINFO.sub(rf"\g<1>{MASKED}@", value)
    return _BOT_TOKEN_IN_URL.sub(rf"\g<1>{MASKED}", masked)


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

    ⚠ CHAQIRUV JOYI AYNAN BITTA: `app/main.py::_on_startup` — aiogram
      `Dispatcher` ning `startup` observeriga ro'yxatga olingan ilmoq.
      `cv-service` da chaqiruv ikkita edi (worker + health yuzasi), bu
      yerda bitta, chunki konteyner bitta JARAYON yuritadi
      (`python -m app.main`).

      Mavjudligi IKKI darvozada tekshiriladi:
        `tests/unit/test_sentry_processes.py`                    (repo ildizi
            — `compose.yaml` dan HOSILA, MANBA darajasida)
        `services/bot-service/tests/unit/test_sentry_entrypoints.py`
            (shu image ichida, `dp.startup` REYESTRI darajasida)

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
    """Shu JARAYONDA `init_sentry()` allaqachon o'rnatib bo'lganmi."""
    return bool(sentry_sdk.is_initialized())
