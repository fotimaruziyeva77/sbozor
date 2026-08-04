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

=============================================================================
PLANER HAM SHU FAYLDA VA U HOLATSIZ (D-02/D-03, 04-07).

`taskiq scheduler app.worker:scheduler` obyektni IMPORT QILADI, ya'ni
uning qurilishi ham `get_settings()` ga bog'lanmasligi shart (yuqoridagi
bo'lim bilan aynan bir xil sabab).

⚠ PLANERNING HOLATIGA ISHONILMAYDI. `SchedulerLoop.cron_tasks_last_run` —
  jarayon XOTIRASIDAGI oddiy `dict` va taqsimlangan qulf YO'Q. Shuning
  uchun bu yerda AYNAN BITTA jadval bor va u eng arzon narsani qiladi:
  har daqiqada holatsiz `capture.tick` ni navbatga qo'yadi. Reja, ijara,
  idempotentlik va yo'qlik yozuvi Postgres'da (`capture_runs`).

  Natijada taskiq'ning UCHALA nosozlik rejimi ham zararsiz bo'ladi:
  o'tkazib yuborilgan tik keyingi daqiqada qoplanadi, takroriy tik
  `ON CONFLICT DO NOTHING` + `SKIP LOCKED` ga uriladi, ikkita planer esa
  bir xil natija beradi. «Aynan bitta planer» operatsion talabi YO'Q.

⚠ `RedisScheduleSource` YAROQSIZ: u jadvalni Valkey'da saqlaydi, Valkey
  esa `--save "" --appendonly no` bilan ishlaydi — kesh qayta ko'tarilganda
  HAMMA bozorning jadvali jimgina yo'q bo'lardi va hech qanday xato
  chiqmasdi. `LabelScheduleSource` jadvalni KODDAN oladi, ya'ni u
  konteyner bilan birga keladi.
=============================================================================
"""

from __future__ import annotations

import asyncio
import os
from contextlib import AsyncExitStack
from typing import TYPE_CHECKING, Annotated, Any, Final
from uuid import UUID

import structlog
from sbozor_core.db import make_engine, make_sessionmaker
from sbozor_core.logging import configure_logging
from sbozor_core.timeutil import business_today
from taskiq import Context, TaskiqDepends, TaskiqEvents, TaskiqScheduler, TaskiqState
from taskiq.schedule_sources import LabelScheduleSource
from taskiq_redis import ListQueueBroker, RedisAsyncResultBackend

from app.jobs.alerting import alert_sweep, daily_digest
from app.jobs.capture import BatchRequest, CapturePolicy, capture_batch, capture_tick
from app.jobs.discovery import discover_nvr
from app.jobs.retention import RetentionPolicy, retention_daily
from app.services import storage as storage_module
from app.services.alerts import AlertSender
from app.services.frame_source import FrameSourcePool
from app.settings import get_settings

if TYPE_CHECKING:
    from taskiq import AsyncBroker

    from app.settings import Settings

log = structlog.get_logger(__name__)

__all__ = [
    "DIGEST_CRON",
    "DISCOVERY_QUEUE",
    "JOBS_QUEUE",
    "MARKET_CRON_OFFSET",
    "RETENTION_CRON",
    "SWEEP_CRON",
    "TICK_CRON",
    "alert_sweep_task",
    "broker",
    "capture_batch_task",
    "capture_tick_task",
    "daily_digest_task",
    "discover_nvr_task",
    "enqueue_discovery",
    "retention_daily_task",
    "scheduler",
]


VALKEY_URL_ENV: Final[str] = "VALKEY_URL"
DEFAULT_VALKEY_URL: Final[str] = "redis://cache:6379/0"
"""`compose.yaml` dagi `${VALKEY_URL:-redis://cache:6379/0}` bilan BIR XIL standart."""

JOBS_QUEUE: Final[str] = "sbozor:jobs"
"""Navbat ro'yxatining nomi — BITTA navbat, TO'RT TURDAGI vazifa.

`taskiq` ning standart nomi (`taskiq`) ATAYIN ishlatilmaydi: bitta Valkey
nusxasi rate-limit sanagichlari va sessiya keshini ham saqlaydi (`db 0`),
ya'ni kalitlar prefiksi kimga tegishli ekanini AYTISHI kerak. `rl:login:*`
bilan bir xil qoida.

=============================================================================
NOM `sbozor:discovery` DAN QAYTA NOMLANDI (04-07) — VA QAROR SHU YERDA.

3-fazada navbatda BITTA vazifa turi bor edi (`nvr.discover`) va nom uni
aniq ta'riflardi. 4-faza uchtasini qo'shadi (`capture.tick`,
`capture.batch` va 04-08 dagi supurgi), ya'ni eski nom navbatning
mazmunidan ARZONROQ ma'lumot beradigan bo'lib qoldi.

⚠ IKKINCHI NAVBAT OCHILMADI va bu ATAYIN. Ikkinchi navbat ikkinchi
  BROKER obyektini va ikkinchi WORKER KONTEYNERINI talab qilardi
  (`taskiq worker` bitta brokerni tinglaydi). Kunlik ~175 vazifa uchun bu
  ajratish keraksiz: prioritet muammosi yo'q, chunki tik 1 sekunddan
  qisqa va batch'lar semafor bilan allaqachon cheklangan
  (`04-PATTERNS.md` §3.10).

⚠ QAYTA NOMLASH `compose.yaml` GA TEGMAYDI: navbat nomi KODDA yashaydi,
  konteyner ta'rifida emas. Deploy paytida eski navbatda qolgan vazifalar
  YO'QOLADI — bu qabul qilinadigan xavf, chunki kashfiyot yugurishi
  bazada `queued` bo'lib qoladi va uni admin qayta bosadi; kadr olish esa
  keyingi tikda (<=60 s) qaytadan navbatga tushadi.
=============================================================================
"""

DISCOVERY_QUEUE: Final[str] = JOBS_QUEUE
"""ESKI NOM — `JOBS_QUEUE` ning aliasi (deprecated, 04-07).

Mavjud testlar va 3-fazadagi chaqiruvchilar shu nomni import qiladi.
Alias BITTA relizga mo'ljallangan: yangi kod `JOBS_QUEUE` ni ishlatadi.
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
    queue_name=JOBS_QUEUE,
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


TICK_CRON: Final[str] = "* * * * *"
"""Planerning YAGONA jadvali — har daqiqada bir marta (D-02).

⚠ LITERAL KONSTANTA, SOZLAMA EMAS. `LabelScheduleSource` jadvalni KOD
  dekoratoridan oladi, ya'ni u bozorga qarab o'zgara olmaydi — va bu
  ATAYIN: bozorga xos jadval `snapshot_schedules` jadvalida yashaydi va
  tik uni HAR DAQIQADA o'qiydi. Cron satrini sozlanadigan qilish ikkinchi
  haqiqat manbaini tug'dirardi.

⚠ SATR AYNAN BITTA MARTA UCHRAYDI (dekoratorda) va buni matn darvozasi
  sanaydi: ikkinchi daqiqalik cron ikkinchi tik oqimini ochib, D-03 ning
  «bitta planer talab qilinmaydi» da'vosini shubha ostiga qo'yardi.
"""

MARKET_CRON_OFFSET: Final[str] = "Asia/Tashkent"
"""⚠⚠ HAR BIR JADVALDA MAJBURIY (Pitfall 12) — VA U «QULAYLIK» EMAS.

`taskiq` cronni **UTC'da** baholaydi (`is_cron_task_now()` ->
`now.astimezone(ZoneInfo(offset))`). Ya'ni `cron_offset` siz yozilgan
`"20 3 * * *"` Toshkentda **08:20** da ishga tushardi — ertalabki kadr
olish cho'qqisining O'RTASIDA. Retention esa arxiv bo'ylab o'qish va
yozish qiladi, ya'ni u aynan o'sha daqiqalarda disk I/O si uchun
`capture_batch` bilan raqobat qilardi.

⚠ `TICK_CRON` DA U ATAYIN YO'Q va bu ziddiyat emas: daqiqalik cron
  mintaqadan MUSTAQIL — «har daqiqada» har qanday mintaqada bir xil
  ma'noga ega. Qolgan uchtasi esa SOATGA bog'langan.

Darvoza: `worker.py` da `cron_offset` literali kamida uch marta uchraydi.
"""

RETENTION_CRON: Final[str] = "20 3 * * *"
"""Saqlash siyosati — kechasi 03:20 (Toshkent).

Kadr olish oynasi 06:00-18:00, ya'ni 03:20 undan ANIQ tashqarida va
arxiv bo'ylab yuriladigan I/O hech kimga xalaqit bermaydi.
"""

SWEEP_CRON: Final[str] = "*/5 * * * *"
"""Alert supurgisi — har 5 daqiqada.

⚠ HAR DAQIQADA EMAS: supurgi har yugurishda har bozor uchun bir necha
  so'rov qiladi va uning tezligi hech nimani yaxshilamaydi — debounce
  oynasi baribir 60 daqiqa. Besh daqiqa «nosozlikni sezish» va «bazani
  bekorga bandi qilish» orasidagi muvozanat.
"""

DIGEST_CRON: Final[str] = "0 20 * * *"
"""Kunlik dayjest — 20:00 (Toshkent), oxirgi slotdan (18:00) KEYIN.

⚠ VAQT TASODIFIY EMAS: dayjest kunning TO'LIQ xulosasini berishi kerak,
  ya'ni u oxirgi slotning grace oynasi yopilgandan keyin ishlashi shart.
  18:00 + 10 daqiqa grace + zaxira = 20:00.
"""

scheduler: TaskiqScheduler = TaskiqScheduler(broker=broker, sources=[LabelScheduleSource(broker)])
"""`taskiq scheduler app.worker:scheduler` IMPORT QILADIGAN obyekt.

⚠ QURILISH `get_settings()` GA BOG'LANMAYDI — `broker` bilan aynan bir xil
  sabab (modul docstringi): planerni import qilishning O'ZI to'liq muhitni
  talab qilardi va `app.main` ni ham olib ketardi.

⚠ `LabelScheduleSource` — jadval KODDAN, Redis'dan EMAS. Sabab modul
  docstringining planer bo'limida: Valkey `--save "" --appendonly no`
  bilan ishlaydi va `RedisScheduleSource` bilan kesh qayta ko'tarilganda
  jadval JIMGINA yo'qolardi.
"""


@broker.on_event(TaskiqEvents.WORKER_STARTUP)
async def _open_worker_resources(state: TaskiqState) -> None:
    """`engine`, ombor va kadr-manba puli — jarayon boshida BIR MARTA.

    `app/main.py::lifespan` bilan aynan bir xil egalik shakli; farqi
    saqlanadigan joyda (`app.state` -> `TaskiqState`) va bu farq
    strukturaviy: worker jarayonida `FastAPI` obyekti umuman yo'q.

    ⚠ `Settings` AYNAN SHU YERDA quriladi (import paytida emas): shifr
      kaliti berilmagan bo'lsa jarayon SHU YERDA, ishga tushishda
      yiqiladi va `docker compose logs worker` da sabab ochiq ko'rinadi.
      Import paytida yiqilish esa `app.main` ni ham olib ketardi.

    ⚠ OMBOR VA KADR MANBALARI HAM SHU YERDA (04-07). `storage.open()` —
      `@asynccontextmanager`, ya'ni uni ushlab turish uchun
      `AsyncExitStack` kerak; `aiobotocore` ning puli jimgina yopilmaydi va
      yopilmagan pul `aiohttp` ning "Unclosed connector" ogohlantirishi
      bilan tugardi. Kadr manbalari esa har chaqiruvda qayta ochilsa har
      kadrga yangi TCP ulanishi va yangi Digest handshake narxini
      qo'shardi (`frame_source.py` ning 2-majburiyati).
    """
    settings = get_settings()
    configure_logging(settings.log_level)

    engine = make_engine(settings.database_url)
    state.engine = engine
    state.sessionmaker = make_sessionmaker(engine)

    resources = AsyncExitStack()
    state.resources = resources
    state.storage = await resources.enter_async_context(storage_module.open(settings))
    sources = FrameSourcePool(go2rtc_url=settings.go2rtc_url)
    resources.push_async_callback(sources.aclose)
    state.sources = sources
    state.policy = _capture_policy(settings)
    state.retention = _retention_policy(settings)

    # ⚠ ALERT JO'NATUVCHISI HAM SHU YERDA (04-08). `alert_sweep` har 5
    #   daqiqada ishlaydi, ya'ni har safar yangi TLS qo'l siqishi narxini
    #   to'lash keraksiz. Bo'sh token bilan qurilganda klient UMUMAN
    #   ochilmaydi va konstruktor bir marta `log.warning("alerts_disabled")`
    #   yozadi — jim ishlash aynan «alert bor deb o'ylash» yolg'onidir.
    sender = AlertSender(
        token=settings.telegram_bot_token,
        chat_id=settings.telegram_chat_id,
        enabled=settings.alerts_enabled,
    )
    resources.push_async_callback(sender.aclose)
    state.sender = sender

    log.info("worker_started", queue=JOBS_QUEUE, alerts=settings.alerts_enabled)


def _capture_policy(settings: Settings) -> CapturePolicy:
    """`Settings` -> `CapturePolicy` — TARJIMA SHU YERDA, jobda EMAS.

    Job sozlamalar obyektining butun yuzasini ko'rmasligi kerak
    (`CapturePolicy` docstringi): shunda uni testda qurish uchun
    `DATABASE_URL`/`JWT_SECRET`/`NVR_CREDENTIAL_KEY` kerak bo'lmaydi.
    """
    return CapturePolicy(
        grace_seconds=settings.capture_grace_seconds,
        lease_seconds=settings.capture_lease_seconds,
        max_attempts=settings.capture_max_attempts,
        batch_size=settings.capture_batch_size,
        global_concurrency=settings.capture_global_concurrency,
        quality=settings.quality_thresholds(),
    )


def _retention_policy(settings: Settings) -> RetentionPolicy:
    """`Settings` -> `RetentionPolicy` — TARJIMA SHU YERDA, jobda EMAS.

    `_capture_policy` bilan aynan bir xil qaror va bir xil sabab: job
    sozlamalar obyektining butun yuzasini ko'rmasligi kerak, shunda uni
    testda `full_days=0` bilan qurish BITTA qatorga tushadi va u
    `DATABASE_URL`/`JWT_SECRET` talab qilmaydi.
    """
    return RetentionPolicy(
        full_days=settings.retention_full_days,
        compressed_days=settings.retention_compressed_days,
        jpeg_quality=settings.retention_jpeg_quality,
        batch_size=settings.retention_batch_size,
    )


@broker.on_event(TaskiqEvents.WORKER_SHUTDOWN)
async def _close_worker_resources(state: TaskiqState) -> None:
    """Barcha resurslarni yopadi — `lifespan` ning `finally` bandi bilan bir xil vazifa."""
    await state.resources.aclose()
    await state.engine.dispose()
    log.info("worker_stopped", queue=JOBS_QUEUE)


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


@broker.task(task_name="capture.batch")
async def capture_batch_task(
    context: Annotated[Context, TaskiqDepends()],
    *,
    market_id: str,
    nvr_id: str,
    run_ids: list[str],
) -> None:
    """YUPQA QOBIQ — `discover_nvr_task` bilan aynan bir xil shakl (S-4).

    `str` -> `UUID` konversiyasi CHEGARADA; resurslar (`sessionmaker`,
    `storage`, `sources`, `policy`) `TaskiqState` dan. Mantiq YO'Q.
    """
    state = context.state
    await capture_batch(
        state.sessionmaker,
        state.storage,
        state.sources,
        policy=state.policy,
        market_id=UUID(market_id),
        nvr_id=UUID(nvr_id),
        run_ids=[UUID(run_id) for run_id in run_ids],
    )


async def _enqueue_batch(batch: BatchRequest) -> None:
    """`capture.batch` ni navbatga qo'yadi — tikning 4-qadami.

    ⚠ CHAQIRUV TIKGA ARGUMENT SIFATIDA BERILADI (`capture_tick(...,
      enqueue=...)`), ya'ni `app/jobs/capture.py` navbat kutubxonasini
      umuman ko'rmaydi (S-4). Bu funksiya — o'sha chegaraning yagona
      o'tish nuqtasi.

    ⚠ `UUID` LAR MATNGA O'GIRILADI: `taskiq` ning serializatori JSON va
      `json.dumps(UUID(...))` `TypeError` beradi (`enqueue_discovery`
      bilan bir xil qoida).
    """
    payload: dict[str, Any] = {
        "market_id": str(batch.market_id),
        "nvr_id": str(batch.nvr_id),
        "run_ids": [str(run_id) for run_id in batch.run_ids],
    }
    # ⚠ `kicker()` — `enqueue_discovery` bilan bir xil yo'l: u `Context`
    #   in'ektsiyasini chetlab o'tadi (dekorator uni ijro paytida beradi)
    #   va chegara `asyncio.timeout` bilan qo'yiladi. Chegarasiz `LPUSH`
    #   broker pulining `socket_timeout=None` i tufayli CHEKSIZ kutardi va
    #   osilgan tik keyingi daqiqadagi tikni ham to'sardi.
    async with asyncio.timeout(ENQUEUE_TIMEOUT_SECONDS):
        await capture_batch_task.kicker().kiq(**payload)


@broker.task(task_name="capture.tick", schedule=[{"cron": TICK_CRON}])
async def capture_tick_task(context: Annotated[Context, TaskiqDepends()]) -> None:
    """YUPQA QOBIQ — planer har daqiqada AYNAN shuni navbatga qo'yadi (D-02).

    ⚠ ARGUMENT YO'Q VA BU ATAYIN: tik HOLATSIZ. Unga «qaysi bozor» yoki
      «qaysi slot» berilsa planer holatiga ishonish boshlanardi va D-02
      ning butun mazmuni (o'tkazib yuborilgan slot IZ QOLDIRADI) yo'qolardi.

    ⚠ `now` HAM BERILMAYDI: mahsulot yo'lida u `now_tz()` ga tushadi.
      Argument test uchun mavjud (`capture_tick(..., now=...)`), ya'ni
      qobiq ham, job ham bir xil funksiyani chaqiradi.
    """
    state = context.state
    await capture_tick(state.sessionmaker, policy=state.policy, enqueue=_enqueue_batch)


@broker.task(
    task_name="retention.daily",
    schedule=[{"cron": RETENTION_CRON, "cron_offset": MARKET_CRON_OFFSET}],
)
async def retention_daily_task(context: Annotated[Context, TaskiqDepends()]) -> None:
    """YUPQA QOBIQ — saqlash siyosati (04-08, CAM-07).

    ⚠ `today` BERILMAYDI: mahsulot yo'lida u `business_today()` ga
      tushadi. Argument FAQAT test uchun mavjud, ya'ni qobiq ham, job ham
      AYNAN bir xil funksiyani chaqiradi.

    ⚠ RETENTION KONVERGENT VAZIFA (`retention.py` ning cron bo'limi):
      o'tkazib yuborilgan yugurish ertaga o'zi tutib olinadi, ya'ni
      planerning xotiradagi cron holati bu yerda AHAMIYATSIZ.
    """
    state = context.state
    await retention_daily(state.sessionmaker, state.storage, policy=state.retention)


@broker.task(
    task_name="alert.sweep",
    schedule=[{"cron": SWEEP_CRON, "cron_offset": MARKET_CRON_OFFSET}],
)
async def alert_sweep_task(context: Annotated[Context, TaskiqDepends()]) -> None:
    """YUPQA QOBIQ — alert supurgisi (04-08, FOUND-06).

    ⛔ SUPURGI `capture.tick` NING TRANZAKSIYASIDAN TASHQARIDA VA ALOHIDA
       VAZIFADA. Aks holda Telegram uzilishi kadr olishni to'xtatardi —
       kuzatuv vositasi kuzatilayotgan tizimni yiqitardi (`alerting.py`
       ning 3-qoidasi).
    """
    state = context.state
    await alert_sweep(state.sessionmaker, state.sender)


@broker.task(
    task_name="alert.digest",
    schedule=[{"cron": DIGEST_CRON, "cron_offset": MARKET_CRON_OFFSET}],
)
async def daily_digest_task(context: Annotated[Context, TaskiqDepends()]) -> None:
    """YUPQA QOBIQ — kunlik dayjest (04-08, FOUND-06).

    ⚠ BIZNES-KUN QOBIQDA HISOBLANADI, jobda emas: job uni ARGUMENT
      sifatida oladi va shu bilan «qaysi kun?» savoli testda bitta
      qiymatga aylanadi (`retention_daily` bilan bir xil qoida).
    """
    state = context.state
    await daily_digest(state.sessionmaker, state.sender, business_date=business_today())


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
