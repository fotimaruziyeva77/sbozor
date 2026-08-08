"""Navbat qatlami — BROKER VA YUPQA QOBIQ. `cv-service` ning ASOSIY jarayoni.

=============================================================================
NEGA ALOHIDA NAVBAT (`sbozor:cv`) VA NEGA `sbozor:jobs` EMAS.

`taskiq worker` BITTA brokerni tinglaydi va broker BITTA ro'yxatdan o'qiydi.
Ikkala servis ham `sbozor:jobs` dan o'qisa, `BRPOP` vazifani TASODIFIY
jarayonga berardi: kadr olish vazifasi `cv-service` ga, aniqlash vazifasi
`core-api` worker'iga tushishi mumkin edi — va o'sha jarayonda kerakli
modul (`onnxruntime` yoki `httpx`) UMUMAN yo'q, ya'ni vazifa
`ModuleNotFoundError` bilan yiqilardi. Nosozlik TASODIFIY va qayta
takrorlanmaydigan bo'lardi — eng qimmat sinf.

⚠ NAVBAT NOMI KODDA YASHAYDI, `compose.yaml` da EMAS — `core-api/app/
  worker.py::JOBS_QUEUE` bilan aynan bir xil qaror va aynan bir xil sabab:
  nomni muhit o'zgaruvchisiga chiqarish ikki jarayonning jimgina boshqa
  navbatlarga qarab qolish yo'lini ochardi.

=============================================================================
BROKER QURILISHI `Settings` NI CHAQIRMAYDI — VA BU ATAYIN.

`broker` MODUL DARAJASIDA quriladi (taskiq CLI `app.worker:broker` ni
IMPORT qiladi, ya'ni boshqa yo'l yo'q). Agar u `get_settings()` dan o'qisa,
`app.worker` ni IMPORT QILISHNING O'ZI to'liq muhitni — shu jumladan
MAVJUD ONNX ARTEFAKTINI — talab qilardi va butun test to'plami modelsiz
yiqilardi.

Shuning uchun bu yerda faqat BITTA o'zgaruvchi (`VALKEY_URL`) to'g'ridan-
to'g'ri o'qiladi. Bu `settings.py` ning nusxasi EMAS: qiymat aynan o'sha
muhit o'zgaruvchisidan va aynan o'sha standart bilan olinadi, farqi faqat
O'QISH PAYTIDA (`core-api/app/worker.py` ning `_broker_url()` i bilan bir
xil naqsh).
=============================================================================
"""

from __future__ import annotations

import os
from typing import Final

import structlog
from sbozor_core.logging import configure_logging
from taskiq import AsyncBroker, TaskiqEvents, TaskiqState
from taskiq_redis import ListQueueBroker, RedisAsyncResultBackend

from app.observability import init_sentry
from app.settings import get_settings

log = structlog.get_logger(__name__)

CV_QUEUE: Final[str] = "sbozor:cv"
"""Aniqlash vazifalarining navbati — `core-api` ning `sbozor:jobs` idan AJRATILGAN.

Sabab modul docstringining birinchi blokida. Prefiks (`sbozor:`) saqlanadi:
bitta Valkey nusxasi rate-limit sanagichlari va sessiya keshini ham
saqlaydi, ya'ni kalit kimga tegishli ekanini AYTISHI kerak.
"""

VALKEY_URL_ENV: Final = "VALKEY_URL"
DEFAULT_VALKEY_URL: Final = "redis://cache:6379/0"
SENTRY_DSN_ENV: Final = "SENTRY_DSN"
LOG_LEVEL_ENV: Final = "LOG_LEVEL"
DEFAULT_LOG_LEVEL: Final = "info"
"""Muhit kalitlari — nomlar `Settings` maydonlari bilan MOS.

⚠ Nomlar `compose.yaml` dagi kalitlar bilan aynan bir xil. Ular
  `Settings` dan MUSTAQIL o'qiladi (yuqoridagi sabab), lekin
  AJRALIB KETMASLIGI kerak.
"""

CONNECT_TIMEOUT_SECONDS: Final[float] = 5.0
"""TCP ulanish chegarasi — `redis-py 8` standarti bilan bir xil.

`socket_timeout` dan FARQ QILADI va u CHEKSIZ QILINMAYDI: ulanish
o'rnatilishi tez amal va uning osilib qolishi normal holat emas.
"""

RESULT_TTL_SECONDS: Final[int] = 7 * 24 * 60 * 60
"""Navbat natijasining Valkey'dagi umri — YETTI KUN (`core-api` bilan bir xil).

HAQIQAT MANBAI BU EMAS: aniqlash natijasi `occupancy_events` da yashaydi
(05-08). Natija backend'i faqat operatsion savol uchun: «kecha qaysi
vazifalar yiqildi?» — bunga bazadagi qator javob bermaydi, chunki navbat
qatlamidagi nosozlik qatorga umuman yetib bormaydi.
"""


def _broker_url() -> str:
    """Broker manzili — modul docstringidagi sabab bo'yicha to'g'ridan-to'g'ri muhitdan."""
    return os.environ.get(VALKEY_URL_ENV) or DEFAULT_VALKEY_URL


broker: AsyncBroker = ListQueueBroker(
    _broker_url(),
    queue_name=CV_QUEUE,
    # ==================================================================
    # ⚠⚠ `socket_timeout=None` MAJBURIY — USIZ WORKER HAR 5 SONIYADA
    #    YIQILADI. Bu 03-06 da O'LCHANGAN fakt, taxmin emas:
    #
    #      redis-py 8.0.1 -> Connection.socket_timeout = 5 (STANDART)
    #      ListQueueBroker.listen() -> `BRPOP <queue>` CHEKSIZ bloklanadi
    #      -> 5 s dan keyin `redis.exceptions.TimeoutError`
    #      -> `listen()` faqat `ConnectionError` ni tutadi
    #      -> prefetcher yiqiladi -> "worker-0 is dead. Scheduling reload."
    #
    #    Bo'sh navbatda bu CHEKSIZ QAYTA ISHGA TUSHISH SIKLI: konteyner
    #    "Up" bo'lib turadi va birorta vazifa hech qachon bajarilmaydi.
    # ==================================================================
    socket_timeout=None,
    socket_connect_timeout=CONNECT_TIMEOUT_SECONDS,
    socket_keepalive=True,
).with_result_backend(
    # Natija backend'i `socket_timeout` ni SAQLAB QOLADI (standart 5 s): u
    # oddiy `SET`/`GET` qiladi va ular hech qachon bloklanmaydi.
    RedisAsyncResultBackend(_broker_url(), result_ex_time=RESULT_TTL_SECONDS),
)
"""`taskiq-redis` ning UCH brokeridan `ListQueueBroker` — `core-api` bilan bir xil tanlov.

`PubSubBroker` fire-and-forget (worker qayta ishga tushayotganda xabar
YO'QOLADI); `RedisStreamBroker` esa vazifani QAYTARADI, ya'ni bitta kadr
ikki marta aniqlanib, `occupancy_events` ga ikkinchi yozuv urinardi.
"""


@broker.on_event(TaskiqEvents.WORKER_STARTUP)
async def _open_worker_resources(state: TaskiqState) -> None:
    """Jurnal va Sentry — jarayon boshida BIR MARTA.

    ⚠ `Settings` AYNAN SHU YERDA quriladi (import paytida emas): ONNX
      artefakti yo'q bo'lsa jarayon SHU YERDA, ishga tushishda yiqiladi va
      sabab `docker compose logs cv-service` da ochiq ko'rinadi. Import
      paytida yiqilish esa butun test to'plamini ham olib ketardi.

    ⚠ SENTRY SHU YERDA VA U «QO'SHIMCHA» EMAS (04-12 ning darsi). Aniqlash
      AYNAN shu jarayonda ishlaydi; boshqa konteynerdagi o'rnatish uning
      istisnolarini UMUMAN ko'rmaydi. Usiz «xatolar Sentry'da» jumlasi
      `cv-service` ning O'Z xatolari uchun yolg'on bo'lardi va nosozlik
      faqat konteyner jurnalida qolardi.

    ⚠ JIM ISHLASH TAQIQLANGAN: «Sentry o'chiq» holati jurnal satrida ochiq
      turishi kerak, aks holda uni «ishlayapti» deb o'ylash mumkin.

    ⚠ OG'IR RESURSLAR (ONNX sessiyasi, ombor puli, `engine`) 05-08 da SHU
      ILMOQQA qo'shiladi — `core-api` ning `_open_worker_resources` i
      bilan aynan bir xil egalik shakli. Bugun ular YO'Q va bu holat
      YASHIRILMAYDI: quvur hali qurilmagan.
    """
    settings = get_settings()
    configure_logging(settings.log_level)
    sentry_enabled = init_sentry(settings.sentry_dsn)

    state.settings = settings
    log.info(
        "cv_worker_started",
        queue=CV_QUEUE,
        sentry=sentry_enabled,
        model=str(settings.cv_model_path),
    )


@broker.on_event(TaskiqEvents.WORKER_SHUTDOWN)
async def _close_worker_resources(state: TaskiqState) -> None:
    """Resurslarni yopadi — `lifespan` ning `finally` bandi bilan bir xil vazifa.

    Bugun yopiladigan resurs YO'Q (yuqoridagi ilmoqning oxirgi bandi).
    Ilmoq baribir mavjud va u JUFTLIKNI o'rnatadi: 05-08 resursni ochgan
    joyda uni yopadigan joy allaqachon turadi va «yopishni unutish» yo'li
    ochilmaydi (`aiobotocore` ning yopilmagan puli `aiohttp` ning
    "Unclosed connector" ogohlantirishi bilan tugardi).
    """
    del state
    log.info("cv_worker_stopped", queue=CV_QUEUE)
