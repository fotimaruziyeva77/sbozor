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
from contextlib import AsyncExitStack
from typing import Annotated, Final
from uuid import UUID

import structlog
from sbozor_core.logging import configure_logging
from taskiq import AsyncBroker, Context, TaskiqDepends, TaskiqEvents, TaskiqState
from taskiq_redis import ListQueueBroker, RedisAsyncResultBackend

from app.db import open_sessionmaker
from app.detector.session import DetectorSession
from app.jobs.detect import assert_model_version_matches, detect, session_detector
from app.observability import init_sentry
from app.services import storage as storage_module
from app.settings import get_settings

log = structlog.get_logger(__name__)

CV_QUEUE: Final[str] = "sbozor:cv"
"""Aniqlash vazifalarining navbati — `core-api` ning `sbozor:jobs` idan AJRATILGAN.

Sabab modul docstringining birinchi blokida. Prefiks (`sbozor:`) saqlanadi:
bitta Valkey nusxasi rate-limit sanagichlari va sessiya keshini ham
saqlaydi, ya'ni kalit kimga tegishli ekanini AYTISHI kerak.
"""

DETECT_TASK_NAME: Final[str] = "cv.detect"
"""Aniqlash vazifasining nomi — IKKI KOD BAZASI ORASIDAGI KONTRAKT.

`core-api` bu vazifani BAJARMAYDI, faqat NASHR QILADI
(`app/services/cv_queue.py`), ya'ni nom ikkala tarafda ham yozilishi
SHART: `taskiq` xabarni nom bilan yo'naltiradi va nom mos kelmasa
`cv-service` uni «noma'lum vazifa» deb tashlab yuborardi — hech qanday
xatosiz, faqat jurnal satri bilan.

⚠ NOM `CV_QUEUE` BILAN BIR XIL SABABDAN KODDA YASHAYDI, sozlamada
  EMAS: muhit o'zgaruvchisiga chiqarilsa ikki servis jimgina boshqa
  nomlarga qarab qolardi. Ikki nusxaning AJRALIB KETMASLIGI
  `tests/integration/test_capture_enqueues_detect.py` da MANBA
  DARAJASIDA tekshiriladi (§S-10: darvoza sanoq emas, MANBADAN hosila).
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

    ⚠⚠ OG'IR RESURSLAR SHU YERDA OCHILADI (05-08) — `core-api/app/worker.py`
       ning `_open_worker_resources` i bilan AYNAN bir xil egalik shakli:

         `engine`         — ulanish puli, `WORKER_SHUTDOWN` da `dispose()`
         ombor klienti    — `aiobotocore` sessiyasi, `async with` ichida
         `DetectorSession`— ONNX grafi, JARAYON-LOKAL

       Uchalasi ham `AsyncExitStack` ga yopishtiriladi, ya'ni «ochdim,
       yopishni unutdim» yo'li YO'Q: yopish tartibi ochish tartibining
       teskarisi va u QO'LDA yozilmaydi.

    ⚠ `DetectorSession` NI HAR VAZIFADA QURISH TAQIQ: ONNX grafi ~model
      hajmi RAM oladi va uni 175 marta/kun qayta yuklash butun byudjetni
      yeb qo'yardi. Sessiya jarayon-lokal, ya'ni yopiladigan TARMOQ
      resursi yo'q — u `AsyncExitStack` da faqat egalikni ko'rsatish
      uchun turadi.
    """
    settings = get_settings()
    configure_logging(settings.log_level)
    sentry_enabled = init_sentry(settings.sentry_dsn)

    # ⚠ ARTEFAKT BILAN `MODEL_VERSION` NING MOSLIGI — ISHGA TUSHISHDA.
    #   `Settings._validate_model_file` faylning MAVJUDLIGINI tekshiradi,
    #   bu esa uning QAYSI ekanini: `occupancy_events.model_version`
    #   kalitning bir qismi va u artefakt bilan birga o'zgarishi shart.
    assert_model_version_matches(settings.cv_model_path)

    stack = AsyncExitStack()
    state.stack = stack
    state.settings = settings
    state.sessionmaker = await stack.enter_async_context(open_sessionmaker(settings))
    state.storage = await stack.enter_async_context(storage_module.open(settings))
    state.detect_frame = session_detector(
        DetectorSession(settings.cv_model_path, intra_op_num_threads=settings.cv_intra_op_threads)
    )

    log.info(
        "cv_worker_started",
        queue=CV_QUEUE,
        sentry=sentry_enabled,
        model=str(settings.cv_model_path),
    )


@broker.on_event(TaskiqEvents.WORKER_SHUTDOWN)
async def _close_worker_resources(state: TaskiqState) -> None:
    """Resurslarni yopadi — `lifespan` ning `finally` bandi bilan bir xil vazifa.

    ⚠ `AsyncExitStack.aclose()` — BITTA chaqiruv, uchala resurs uchun.
      Qo'lda yozilgan yopish zanjiri birinchi istisnoda to'xtardi va
      qolgan resurslar ochiq qolardi (`aiobotocore` ning yopilmagan puli
      `aiohttp` ning "Unclosed connector" ogohlantirishi bilan tugardi —
      ya'ni resurs oqishi FAQAT jurnalda ko'rinadigan shaklda qolardi).
    """
    stack: AsyncExitStack | None = getattr(state, "stack", None)
    if stack is not None:
        await stack.aclose()
    log.info("cv_worker_stopped", queue=CV_QUEUE)


@broker.task(task_name=DETECT_TASK_NAME)
async def detect_task(
    context: Annotated[Context, TaskiqDepends()],
    *,
    market_id: str,
    snapshot_id: str,
) -> None:
    """YUPQA QOBIQ — `core-api/app/worker.py::capture_batch_task` bilan bir xil shakl (D-06).

    Ikki ish bajaradi va ikkalasi ham CHEGARA ishi:

      1. `str` -> `UUID`. Navbat xabari JSON, ya'ni `UUID` u yerdan MATN
         bo'lib qaytadi. Konversiya shu yerda, jobda EMAS.
      2. Resurslarni `TaskiqState` dan olib beradi — job ularni O'ZI
         QURMAYDI (`jobs/detect.py` hammasini argument sifatida oladi).

    ⚠ VAZIFA NOMI (`cv.detect`) — IKKI SERVIS ORASIDAGI KONTRAKT. Uni
      `core-api/app/services/cv_queue.py` ham AYNAN shu satr bilan e'lon
      qiladi va ikkalasining mos kelishi darvoza bilan tekshiriladi
      (`tests/integration/test_capture_enqueues_detect.py`).

    Mantiq bu funksiyada YO'Q va bo'lmasligi kerak: mexanizm
    almashtirilganda ko'chiriladigan yagona qism aynan shu.
    """
    state = context.state
    await detect(
        state.sessionmaker,
        state.storage,
        state.detect_frame,
        market_id=UUID(market_id),
        snapshot_id=UUID(snapshot_id),
    )
