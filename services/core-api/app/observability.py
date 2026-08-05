"""Sentry ilmoqlari va uning O'RNATILISHI — UCHALA JARAYON uchun BIR joyda.

=============================================================================
NEGA BU MODUL ALOHIDA (04-12 da tug'ildi va sabab O'LCHANGAN).

Ilmoqlarning o'zi 03-13 dan beri `app/main.py` da yashardi va u yerda
FAQAT API jarayoni uchun o'rnatilardi. `compose.yaml` esa `SENTRY_DSN` ni
UCHALA konteynerga ham beradi (`core-api`, `worker`, `scheduler`) — ya'ni
tashqaridan qaraganda «xatolar Sentry'da» degan da'vo bajarilgandek
ko'rinardi.

⛔ AMALDA U BAJARILMAGAN EDI VA AYNAN ENG MUHIM JOYDA. Kadr olish
   (`capture_batch`), saqlash siyosati (`retention_daily`) va alert
   supurgisi (`alert_sweep`) — uchalasi ham WORKER jarayonida ishlaydi.
   API jarayoni ularning istisnolarini UMUMAN ko'rmaydi, ya'ni FOUND-06
   ning «xatolar Sentry'da» jumlasi 4-fazaning O'Z xatolari uchun yolg'on
   bo'lardi: nosozlik faqat `docker compose logs worker` da qolardi va
   uni o'qiydigan odam yo'q.

   Nosozlik sinfi tanish: `sentry_sdk` DSN ni muhitdan o'zi o'qiydi, lekin
   `init()` ni HECH KIM chaqirmasa ham HECH QANDAY xato bermaydi. Ya'ni
   bu «jimgina yolg'on» sinfi — konteyner sog'lom, jurnal toza, hodisa
   esa hech qachon jo'natilmaydi.

⛔ 04-12 WORKER'NI YOPDI, `scheduler` ESA OCHIQ QOLDI (04-13 da yopildi).
   `04-VERIFICATION.md` uni TAXMIN bilan emas, KONTEYNERDA o'lchab topdi:
   `taskiq scheduler` jarayonida `broker.is_worker_process` `False` bo'lib
   qoladi (CLI `cli/scheduler/run.py:392` da BOSHQA bayroqni —
   `is_scheduler_process` ni — o'rnatadi), ya'ni `AsyncBroker.startup()`
   (`abc/broker.py:187-191`) `WORKER_STARTUP` emas, `CLIENT_STARTUP` ni
   ateshlaydi va reyestrda uning ilmog'i UMUMAN yo'q edi.

   Oqibati kosmetik emas: planer 4-fazaning HAMMA jobini tetiklaydi va
   `alert_sweep` ham uning boshqaruvida, ya'ni planer yiqilsa Telegram
   yo'li ham to'xtaydi. Qolgan yagona detektor — `/internal/self-check`,
   uning tashqi kuzatuvchisi esa D-21 bo'yicha ataylab kod EMAS.
=============================================================================

⚠ NEGA `app/main.py` DAN IMPORT QILINMAYDI. `app/main.py` ning O'ZI
  `app/worker.py` dan `broker` ni import qiladi, ya'ni teskari yo'nalish
  aylanma bog'liqlik bo'lardi. Undan ham qimmatrog'i: `app.main` ni
  import qilish butun FastAPI ilovasini, barcha routerlarni va ularning
  bog'liqliklarini worker jarayoniga tortib kelardi.

⚠ SOZLAMA OBYEKTI ARGUMENT SIFATIDA OLINMAYDI — faqat DSN satri. Shunda
  bu modul `Settings` ga bog'lanmaydi va uni import qilish uchun to'liq
  muhit (`DATABASE_URL`, `JWT_SECRET`, `NVR_CREDENTIAL_KEY`) talab
  qilinmaydi (`app/worker.py` ning broker qurilishi bilan bir xil qoida).
"""

from __future__ import annotations

import re
from typing import Any

import sentry_sdk
from sentry_sdk.types import Breadcrumb, BreadcrumbHint, Event, Hint

__all__ = [
    "MASKED",
    "PII_KEYS",
    "capture_exception",
    "init_sentry",
    "mask_secrets",
    "scrub_breadcrumb",
    "scrub_event",
    "sentry_installed",
]

MASKED = "***"
"""Maskalangan qiymatning YAGONA ko'rinishi — testda ham shu satr izlanadi."""

PII_KEYS = frozenset(
    {"password", "current_password", "new_password", "phone", "token", "src", "source"}
)
"""Sentry `extra` sida maskalanadigan kalitlar.

⚠ `src`/`source` 03-13 da QO'SHILDI: `PUT /api/streams` ning `src` i endi
  REKVIZITLI RTSP manbai (`live_source.authenticated_rtsp_source` ning
  chiqishi), ya'ni u nomi bo'yicha zararsiz ko'ringan holda parol tashiydi.
"""

_SRC_PARAM = re.compile(r"(?i)(\bsrc=)[^&\s'\"]*")
"""Query satridagi `src=<qiymat>` — QIYMAT butunlay maskalanadi.

⚠ QIYMAT PERCENT-ENCODED HOLDA KELADI. `httpx` chiquvchi so'rovda uni
  `src=rtsp%3A%2F%2Fadmin%3APAROL%40nvr...` ko'rinishiga o'giradi, ya'ni
  `rtsp://` naqshi bilan izlash bu shaklni TOPMASDI (o'lchandi). Shuning
  uchun bu yerda butun qiymat `&` gacha kesiladi — shakl ahamiyatsiz.
"""

_RTSP_USERINFO = re.compile(r"(?i)(rtsp://)[^/@\s'\"]+@")
"""XOM `rtsp://user:pass@host` shakli — ZAXIRA qatlam.

⚠ BU QATLAM STACK FRAME'DAGI LOKAL O'ZGARUVCHILAR UCHUN. Sentry
  `include_local_variables` bilan har freymning lokallarini `repr` qilib
  yuboradi, `go2rtc.py::ensure_stream` da esa ochilgan manba lokal
  o'zgaruvchida yotadi. Query naqshi u yerda ishlamasdi: qiymat `src=`
  siz, yalang'och satr sifatida turadi.
"""


def mask_secrets(value: str) -> str:
    """Satrdagi RTSP rekvizitini maskalaydi — MATN darajasida.

    ⚠ URL QAYTA QURILMAYDI (parse -> tahrir -> unparse). Maqsad qiymatni
      SAQLAB QOLISH emas, sirni CHIQARMASLIK: qayta qurish har bir
      kutilmagan shaklda (bo'sh port, ikkinchi `@`, buzilgan kodlash)
      istisno berardi va o'sha istisnoning matni yana sirni tashirdi.
    """
    return _RTSP_USERINFO.sub(rf"\g<1>{MASKED}@", _SRC_PARAM.sub(rf"\g<1>{MASKED}", value))


def _mask_deep(node: Any) -> Any:
    """Hodisadagi HAR satr qiymatiga `mask_secrets()` ni qo'llaydi.

    ⚠ NEGA CHUQUR VA NEGA MAYDON RO'YXATI EMAS: sir Sentry hodisasiga
      KAMIDA UCH xil joydan tushadi — istisno matni (`exception.values[].
      value`), so'rov query satri (`request.query_string`) va stack
      freymlarning lokal o'zgaruvchilari (`stacktrace.frames[].vars`).
      Ro'yxat bilan yurish to'rtinchi joy paydo bo'lganda jimgina
      eskirardi; matn darajasidagi bitta qoida esa hammasini qamraydi.
    """
    if isinstance(node, str):
        return mask_secrets(node)
    if isinstance(node, dict):
        return {key: _mask_deep(value) for key, value in node.items()}
    if isinstance(node, list):
        return [_mask_deep(item) for item in node]
    return node


def scrub_event(event: Event, _hint: Hint) -> Event:
    """Sentry `before_send` — shaxsiy ma'lumot va sirlarni olib tashlaydi (ASVS V14).

    Sentry hodisasi ilova chegarasidan CHIQADI (uchinchi tomon xizmati),
    shuning uchun so'rov tanasi va cookie'lar u yerga umuman bormasligi
    kerak. `structlog` tomonida bir xil vazifani `censor_secrets` bajaradi.

    03-13 dan boshlab BU YERDA IKKINCHI VAZIFA HAM BOR: jonli ko'rish yo'li
    go2rtc'ga REKVIZITLI RTSP manbaini yuboradi (`?src=rtsp://admin:PAROL@...`),
    ya'ni sir istisno matniga, so'rov query satriga va freym lokallariga
    tushishi mumkin. `_mask_deep()` uchalasini ham matn darajasida yopadi.
    """
    request = event.get("request")
    if isinstance(request, dict):
        request.pop("data", None)
        request.pop("cookies", None)
        headers = request.get("headers")
        if isinstance(headers, dict):
            for key in list(headers):
                if key.lower() in {"authorization", "cookie"}:
                    headers[key] = MASKED
    extra = event.get("extra")
    if isinstance(extra, dict):
        for key in list(extra):
            if key.lower() in PII_KEYS:
                extra[key] = MASKED
    masked: Event = _mask_deep(event)
    return masked


def scrub_breadcrumb(crumb: Breadcrumb, _hint: BreadcrumbHint) -> Breadcrumb | None:
    """Sentry `before_breadcrumb` — CHIQUVCHI so'rov URL'ini maskalaydi (T-03-89).

    =========================================================================
    ⚠⚠ BU ALOHIDA ILMOQ KERAK — `before_send` YETMAYDI.

    `sentry-sdk[fastapi]` ning httpx integratsiyasi har CHIQUVCHI so'rovni
    breadcrumb sifatida yozadi va breadcrumb `data` sida TO'LIQ URL, query
    satri bilan turadi. Bizning `PUT /api/streams?name=...&src=rtsp://admin:PAROL@...`
    aynan shunday so'rov — ya'ni parol hodisa YUZ BERMASDAN OLDIN, oddiy
    muvaffaqiyatli chaqiruvda ham navbatga tushardi va keyingi ISTALGAN
    xato bilan Sentry'ga ketardi.

    `before_send` uni ushlamasdi: breadcrumb'lar hodisaga u yerdan
    KEYIN qo'shiladi.
    =========================================================================

    Faqat `http` turidagi breadcrumb qaraladi: qolganlarida URL yo'q va
    ularni ham qayta ishlash har log satrida ikkita regex yurgizardi.
    """
    if crumb.get("type") != "http" and crumb.get("category") != "httplib":
        return crumb

    data = crumb.get("data")
    if isinstance(data, dict):
        for key, value in list(data.items()):
            if isinstance(value, str):
                data[key] = mask_secrets(value)

    message = crumb.get("message")
    if isinstance(message, str):
        crumb["message"] = mask_secrets(message)
    return crumb


def init_sentry(dsn: str) -> bool:
    """Sentry'ni IKKALA ilmoq bilan birga o'rnatadi. Bo'sh DSN — no-op.

    ⚠ IKKALA ILMOQ HAM MAJBURIY (T-03-89): `before_send` hodisani,
      `before_breadcrumb` esa undan OLDIN yig'ilgan chiquvchi so'rovlar
      izini tozalaydi. Bittasini qoldirish ikkinchisini bir chaqiruvdan
      narida qoldirardi — parol hodisa yuz bermasdan turib navbatga
      tushardi.

    ⚠ CHAQIRUV JOYI BITTA EMAS, UCHTA — VA SANOQ KOD KIRISH NUQTASI EMAS,
      JARAYON bo'yicha yuritiladi (04-12 ning hisobi «ikkita kirish
      nuqtasi» edi va aynan shu shakl uchinchi JARAYONNI ko'rmay qolgan):

        1. `app/main.py::lifespan`                    — `core-api` jarayoni
        2. `app/worker.py::_open_worker_resources`    — `worker` jarayoni
           (`WORKER_STARTUP` ilmog'i; kadr olish, saqlash siyosati, alert
           supurgisi)
        3. `app/worker.py::_install_client_observability` — `scheduler`
           jarayoni (`CLIENT_STARTUP` ilmog'i; 04-13 da qo'shildi)

      Uchalasining ham mavjudligi `tests/unit/test_sentry_processes.py` da
      tekshiriladi va u ro'yxatni SANAMAYDI — `compose.yaml` da `SENTRY_DSN`
      oladigan har servisdan HOSILA qiladi, ya'ni to'rtinchi jarayon
      qo'shilganda darvoza jimgina eskirmaydi, u YIQILADI.

    Args:
        dsn: Sentry DSN. Bo'sh satr — o'rnatish O'TKAZIB YUBORILADI va bu
            NORMAL ish oqimi (dev, CI va DSN berilmagan deploy).

    Returns:
        `True` — o'rnatildi; `False` — DSN bo'sh, o'rnatilmadi. Qiymat
        chaqiruvchiga jurnalga yozish uchun beriladi: «Sentry o'chirilgan»
        holati JIM bo'lmasligi kerak, aks holda uni «ishlayapti» deb
        o'ylash mumkin.
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
    """Shu JARAYONDA `sentry_sdk.init()` allaqachon bajarilganmi.

    =========================================================================
    NEGA BU QOBIQ KERAK — IKKI SABAB, IKKALASI HAM STRUKTURAVIY.

    **1. `CLIENT_STARTUP` API jarayonida HAM ateshlanadi.** `app/main.py::
    lifespan` avval `init_sentry()` ni chaqiradi, keyin `broker.startup()`
    ni — va o'sha `startup()` `is_worker_process` `False` bo'lgani uchun
    aynan `CLIENT_STARTUP` ni ateshlaydi (`abc/broker.py:187-191`). Ya'ni
    planer uchun yozilgan ilmoq API jarayonida ham ishga tushadi va u
    yerda ikkinchi marta `init()` qilmasligi kerak.

    **2. `sentry_sdk` `app/worker.py` GA IMPORT QILINMAYDI.** SDK ning
    yagona chaqiruvchisi shu modul bo'lib qolsin — shunda `before_send`/
    `before_breadcrumb` siz o'rnatish yo'li UMUMAN ochilmaydi (T-04-98).
    =========================================================================
    """
    return bool(sentry_sdk.is_initialized())


def capture_exception(exc: BaseException) -> None:
    """Istisnoni Sentry'ga yuboradi — SDK ga yagona tashqi eshik.

    ⚠ `sentry_sdk.capture_exception` NING RE-EKSPORTI EMAS, QOBIG'I: SDK
      hodisa ID sini qaytaradi, chaqiruvchiga esa u kerak emas va uni
      qaytarish chaqiruv joyida «ID bilan nima qilamiz?» savolini
      tug'dirardi. Qaytish tipi `None` — qatlam faqat XABAR BERADI.

    ⚠ `init()` chaqirilmagan jarayonda bu no-op: `sentry_sdk` mijoz
      qurilmagan bo'lsa hodisani jimgina tashlab yuboradi va XATO
      BERMAYDI. Shuning uchun chaqiruv joyida `log.exception` ham bo'lishi
      SHART — jurnal yagona kafolatlangan yo'l.
    """
    sentry_sdk.capture_exception(exc)
