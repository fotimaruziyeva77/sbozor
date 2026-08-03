"""Navbat qatlami — BROKER VA YUPQA QOBIQ. Kutubxona FAQAT shu faylda (D-06).

=============================================================================
D-06 NING QAT'IY SHARTI VA UNING NARXI.

Navbat kutubxonasi (`taskiq` + `taskiq-redis`) bu loyihada FAQAT SHU
FAYLDA ko'rinadi. `app/jobs/` daraxtida u import qilinmaydi va
`app/api/` ham unga to'g'ridan-to'g'ri bog'lanmaydi — API `lifespan` da
`app.state` ga qo'yilgan chaqiruvchini oladi.

Sabab 4-fazaga tegishli: ROADMAP orkestratsiya mexanizmini ochiq savol
deb belgilagan (`taskiq` vs Postgres `SELECT ... FOR UPDATE SKIP LOCKED`).
Mexanizm o'zgarsa ko'chirish narxi SHU FAYL bo'lishi kerak — kashfiyot
mantig'i emas. Va **ikki mexanizm bir vaqtda saqlanmaydi**: ikkitasi
turganda "bu job qaysi yo'ldan ketdi?" savoli har nosozlikda qaytadan
so'ralardi.

`arq` NEGA RAD ETILDI (CLAUDE.md ning navbat yozuvi 2026-08-02 da shu
sababdan qayta yozilgan): u `redis[hiredis]<6,>=4.2.0` talab qiladi,
`services/core-api/pyproject.toml` esa `redis[hiredis]==8.0.1` ga qadalgan.
`pip install arq` `redis` ni 5.3.1 ga TUSHIRADI — bu EMPIRIK kuzatilgan,
taxmin emas. `taskiq-redis 1.2.3` esa `redis<9,>=8.0.0` talab qiladi,
ya'ni mavjud pin bilan AYNAN mos.
=============================================================================

=============================================================================
BROKER QURILISHI `Settings` NI CHAQIRMAYDI — VA BU ATAYIN.

`broker` MODUL DARAJASIDA quriladi (taskiq CLI `app.worker:broker` ni
import qiladi, ya'ni boshqa yo'l yo'q). Agar u `get_settings()` dan
o'qisa, `app.worker` ni IMPORT QILISHNING O'ZI to'liq muhitni talab
qilardi — va `app/main.py` uni import qiladi, ya'ni butun test to'plami
`NVR_CREDENTIAL_KEY` siz yiqilardi.

Shuning uchun bu yerda faqat BITTA o'zgaruvchi (`VALKEY_URL`) to'g'ridan-
to'g'ri o'qiladi. Bu `settings.py` ning nusxasi EMAS: qiymat aynan o'sha
muhit o'zgaruvchisidan va aynan o'sha standart bilan olinadi (`compose.yaml`
`VALKEY_URL: ${VALKEY_URL:-redis://cache:6379/0}`), farqi faqat O'QISH
PAYTIDA. `Settings` ning qolgan maydonlari WORKER STARTUP ilgagida —
ya'ni jarayon haqiqatan ishga tushayotganda — o'qiladi va u yerda
yiqilish TO'G'RI xulq.

⚠ `ListQueueBroker(...)` QURILISHI ULANMAYDI: `redis-py` puli yalqov.
  Ulanish `startup()` da bo'ladi.
=============================================================================

RESURS EGALIGI `app/main.py:96-117` (`lifespan`) SHAKLI BILAN BIR XIL:
`engine` bir marta ochiladi, `shutdown` ilgagida yopiladi. Farq —
saqlanadigan joy: worker jarayonida `app.state` YO'Q, uning o'rniga
`TaskiqState` (`03-PATTERNS.md` §3.8).
"""

from __future__ import annotations

import asyncio
import os
from typing import TYPE_CHECKING, Annotated, Any, Final
from uuid import UUID

import structlog
from sbozor_core.db import make_engine, make_sessionmaker
from sbozor_core.logging import configure_logging
from taskiq import Context, TaskiqDepends, TaskiqEvents, TaskiqState
from taskiq_redis import ListQueueBroker, RedisAsyncResultBackend

from app.jobs.discovery import discover_nvr
from app.settings import get_settings

if TYPE_CHECKING:
    from taskiq import AsyncBroker

log = structlog.get_logger(__name__)

__all__ = ["DISCOVERY_QUEUE", "broker", "discover_nvr_task", "enqueue_discovery"]


VALKEY_URL_ENV: Final[str] = "VALKEY_URL"
DEFAULT_VALKEY_URL: Final[str] = "redis://cache:6379/0"
"""`compose.yaml` dagi `${VALKEY_URL:-redis://cache:6379/0}` bilan BIR XIL standart."""

DISCOVERY_QUEUE: Final[str] = "sbozor:discovery"
"""Navbat ro'yxatining nomi.

`taskiq` ning standart nomi (`taskiq`) ATAYIN ishlatilmaydi: bitta Valkey
nusxasi rate-limit sanagichlari va sessiya keshini ham saqlaydi (`db 0`),
ya'ni kalitlar prefiksi kimga tegishli ekanini AYTISHI kerak. `rl:login:*`
bilan bir xil qoida.
"""

CONNECT_TIMEOUT_SECONDS: Final[float] = 5.0
"""TCP ulanish chegarasi — `redis-py 8` ning standarti bilan bir xil.

Bu qiymat `socket_timeout` dan FARQ QILADI va u CHEKSIZ QILINMAYDI:
ulanish o'rnatilishi tez amal va uning osilib qolishi hech qachon normal
holat emas.
"""

ENQUEUE_TIMEOUT_SECONDS: Final[float] = 5.0
"""`enqueue_discovery()` ning yuqori chegarasi — SO'ROV ICHIDAGI yo'l uchun.

⚠ NEGA ALOHIDA CHEGARA KERAK: broker puli `socket_timeout=None` bilan
  quriladi (pastdagi izoh — `BRPOP` cheksiz bloklanadi), ya'ni Valkey
  osilib qolganda `LPUSH` ham cheksiz kutardi. Worker uchun bu to'g'ri
  xulq, `POST /discover` uchun esa YO'Q: admin brauzeri osilib qolardi va
  `uvicorn --workers 1` ostida u butun API'ni bloklardi (T-03-42 ning
  aynan o'zi, boshqa yo'ldan).
"""

RESULT_TTL_SECONDS: Final[int] = 7 * 24 * 60 * 60
"""Navbat natijasining Valkey'dagi umri — YETTI KUN.

⚠ HAQIQAT MANBAI BU EMAS. Kashfiyotning holati `nvr_discovery_runs`
  jadvalida yashaydi va UI aynan o'sha qatorni poll qiladi. Natija
  backend'i FAQAT operatsion savol uchun: "kecha qaysi vazifalar
  bajarildi va qaysilari yiqildi?" — bunga bazadagi qator javob bermaydi,
  chunki navbat qatlamidagi nosozlik (serializatsiya, worker yiqilishi)
  qatorga umuman yetib bormaydi.

  TTL CHEKSIZ EMAS: natijalar o'chmasa Valkey (davomiyliksiz kesh —
  `compose.yaml` da `--save "" --appendonly no`) asta-sekin to'lib borardi.
"""


def _broker_url() -> str:
    """Broker manzili — modul docstringidagi sabab bo'yicha to'g'ridan-to'g'ri muhitdan."""
    return os.environ.get(VALKEY_URL_ENV) or DEFAULT_VALKEY_URL


broker: AsyncBroker = ListQueueBroker(
    _broker_url(),
    queue_name=DISCOVERY_QUEUE,
    # ==================================================================
    # ⚠⚠ `socket_timeout=None` MAJBURIY VA U "QULAYLIK" EMAS — USIZ
    #    WORKER HAR 5 SONIYADA YIQILADI. Bu O'LCHANGAN fakt:
    #
    #      redis-py 8.0.1 -> Connection.socket_timeout = 5 (STANDART)
    #      ListQueueBroker.listen() -> `BRPOP <queue>` CHEKSIZ bloklanadi
    #      -> 5 s dan keyin `redis.exceptions.TimeoutError`
    #      -> `listen()` faqat `ConnectionError` ni tutadi
    #      -> prefetcher yiqiladi -> "worker-0 is dead. Scheduling reload."
    #
    #    Bo'sh navbatda bu CHEKSIZ QAYTA ISHGA TUSHISH SIKLI: konteyner
    #    "Up" bo'lib turadi, `docker compose ps` sog'lom ko'rsatadi va
    #    birorta vazifa hech qachon bajarilmaydi.
    #
    #    `socket_timeout` — javob KUTISH chegarasi; bloklanuvchi navbat
    #    o'quvchisi uchun uning ta'rifi bo'yicha chegara bo'lishi mumkin
    #    emas. Uning o'rnini `socket_connect_timeout` (ulanish) va
    #    `socket_keepalive` (o'lik peer'ni OS darajasida aniqlash) egallaydi.
    # ==================================================================
    socket_timeout=None,
    socket_connect_timeout=CONNECT_TIMEOUT_SECONDS,
    socket_keepalive=True,
).with_result_backend(
    # ⚠ NATIJA BACKEND'I `socket_timeout` NI SAQLAB QOLADI (standart 5 s):
    #   u oddiy `SET`/`GET` qiladi va ular hech qachon bloklanmaydi, ya'ni
    #   u yerda chegara TO'G'RI va foydali.
    RedisAsyncResultBackend(_broker_url(), result_ex_time=RESULT_TTL_SECONDS),
)
"""`taskiq-redis 1.2.3` ning UCH brokeridan BIRI — tanlov sabab bilan.

| Broker             | Semantika                          | Verdikt |
|--------------------|------------------------------------|---------|
| `ListQueueBroker`  | Redis `LIST` + `BRPOP`             | ✅ TANLANDI |
| `PubSubBroker`     | `PUB/SUB` — obunachi yo'q bo'lsa xabar YO'QOLADI | ❌ |
| `RedisStreamBroker`| `XADD` + iste'molchi guruhlari     | ⚠ keyingi qadam |

`PubSubBroker` RAD ETILDI, chunki u fire-and-forget: worker qayta ishga
tushayotgan paytdagi `POST /discover` jimgina yo'qolardi va admin
tugmani bosgan holda hech qanday natija ko'rmasdi.

`RedisStreamBroker` KUCHLIROQ (`ack` bilan, ya'ni worker o'rtada yiqilsa
vazifa qaytadi), lekin aynan shu xususiyat BU YERDA ZARARLI: qaytgan
vazifa NVR ga ikkinchi marta borardi va D-03 ning qulflash arifmetikasini
ishga tushirardi. `start_run()` ning `status = 'queued'` sharti buni
to'sadi, lekin ikkinchi himoya qatlamiga tayanmaslik afzal. Yuk oshsa
(4-faza: kunlik snapshot pipeline) qayta ko'rib chiqilsin.
"""


@broker.on_event(TaskiqEvents.WORKER_STARTUP)
async def _open_worker_resources(state: TaskiqState) -> None:
    """`engine` va `sessionmaker` — jarayon boshida BIR MARTA.

    `app/main.py::lifespan` bilan aynan bir xil egalik shakli; farqi
    saqlanadigan joyda (`app.state` -> `TaskiqState`) va bu farq
    strukturaviy: worker jarayonida `FastAPI` obyekti umuman yo'q.

    ⚠ `Settings` AYNAN SHU YERDA quriladi (import paytida emas): shifr
      kaliti berilmagan bo'lsa jarayon SHU YERDA, ishga tushishda
      yiqiladi va `docker compose logs worker` da sabab ochiq ko'rinadi.
      Import paytida yiqilish esa `app.main` ni ham olib ketardi.
    """
    settings = get_settings()
    configure_logging(settings.log_level)

    engine = make_engine(settings.database_url)
    state.engine = engine
    state.sessionmaker = make_sessionmaker(engine)
    log.info("worker_started", queue=DISCOVERY_QUEUE)


@broker.on_event(TaskiqEvents.WORKER_SHUTDOWN)
async def _close_worker_resources(state: TaskiqState) -> None:
    """Pulni yopadi — `lifespan` ning `finally` bandi bilan bir xil vazifa."""
    await state.engine.dispose()
    log.info("worker_stopped", queue=DISCOVERY_QUEUE)


@broker.task(task_name="nvr.discover")
async def discover_nvr_task(
    context: Annotated[Context, TaskiqDepends()],
    *,
    market_id: str,
    nvr_id: str,
    run_id: str,
    actor_id: str | None = None,
) -> None:
    """YUPQA QOBIQ — boshqa hech nima qilmaydi (D-06).

    Ikki ish bajaradi va ikkalasi ham CHEGARA ishi:

      1. `str` -> `UUID`. Navbat xabari JSON, ya'ni `UUID` u yerdan
         MATN bo'lib qaytadi. Konversiya shu yerda, jobda EMAS: job
         funksiyasi tiplangan qiymatlar bilan ishlaydi va u navbat
         formatidan umuman bexabar qoladi.
      2. `sessionmaker` ni `TaskiqState` dan olib beradi — job resursni
         O'ZI QURMAYDI (`app/jobs/discovery.py` argument sifatida oladi).

    Mantiq shu funksiyada YO'Q va bo'lmasligi kerak: mexanizm
    almashtirilganda ko'chiriladigan yagona qism aynan shu.
    """
    await discover_nvr(
        context.state.sessionmaker,
        market_id=UUID(market_id),
        nvr_id=UUID(nvr_id),
        run_id=UUID(run_id),
        actor_id=UUID(actor_id) if actor_id is not None else None,
    )


async def enqueue_discovery(
    *,
    market_id: UUID,
    nvr_id: UUID,
    run_id: UUID,
    actor_id: UUID | None = None,
    target: AsyncBroker | None = None,
) -> None:
    """Kashfiyotni navbatga qo'yadi — API qatlami chaqiradigan YAGONA funksiya.

    ⚠ `UUID` LAR MATNGA O'GIRILADI. `taskiq` ning standart serializatori —
      JSON, `json.dumps(UUID(...))` esa `TypeError` beradi. Konversiya
      SHU YERDA va u yagona joyda: chaqiruvchi tiplangan `UUID` beradi va
      navbat formati haqida hech nima bilmaydi.

    Args:
        target: brokerni ALMASHTIRISH nuqtasi — FAQAT test uchun. Modul
            darajasidagi `broker` compose tarmog'idagi `cache` ga
            qarab turadi; test esa o'z Valkey konteyneriga yozadi
            (`tests/conftest.py::valkey_url`). Prod yo'lida bu argument
            berilmaydi va `None` bo'lib qoladi.
    """
    kicker = discover_nvr_task.kicker()
    if target is not None:
        kicker = kicker.with_broker(target)

    payload: dict[str, Any] = {
        "market_id": str(market_id),
        "nvr_id": str(nvr_id),
        "run_id": str(run_id),
        "actor_id": None if actor_id is None else str(actor_id),
    }
    # Chegara SHU YERDA, pulda emas — sabab `ENQUEUE_TIMEOUT_SECONDS`
    # docstringida. `TimeoutError` chaqiruvchiga KO'TARILADI: API qatlami
    # navbatga tushmagan yugurishni `failed` deb yopishi SHART, aks holda
    # qator MANGU `queued` bo'lib qolardi va qisman UNIQUE indeks shu NVR
    # uchun har qanday keyingi kashfiyotni bloklardi.
    async with asyncio.timeout(ENQUEUE_TIMEOUT_SECONDS):
        await kicker.kiq(**payload)
    log.info("nvr_discovery_enqueued", **payload)
