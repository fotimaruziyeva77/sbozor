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

=============================================================================
PLANER JARAYONI BOSHQA HODISANI ATESHLAYDI (04-13, FOUND-06).

`taskiq worker` va `taskiq scheduler` — IKKI BOSHQA JARAYON va ular
BOSHQA hodisani ateshlaydi. Bu taskiq ning tanlovi, bizniki emas, va u
`04-VERIFICATION.md` da KONTEYNERDA o'lchangan:

    cli/scheduler/run.py:392   `scheduler.broker.is_scheduler_process = True`
    cli/worker/run.py:148      `broker.is_worker_process = True`  <- BOSHQA bayroq
    abc/broker.py:187-191      `is_worker_process` yolg'on -> CLIENT_STARTUP

Ya'ni `WORKER_STARTUP` ilmog'i (`_open_worker_resources`) planer
jarayonida HECH QACHON ishlamaydi. Shuning uchun bu faylda IKKI ilmoq
bor va ularning vazifasi ham har xil:

    WORKER_STARTUP  -> og'ir resurslar (engine, ombor, kadr manbalari)
    CLIENT_STARTUP  -> FAQAT kuzatuv (jurnal + Sentry), resurs YO'Q

⚠ IKKINCHI ILMOQ RESURS OCHMAYDI VA BU ATAYIN: planer hech qanday jobni
  O'ZI bajarmaydi — u faqat navbatga qo'yadi (D-02). Unga engine ham,
  ombor ham, kadr manbai ham kerak emas.
=============================================================================
"""

from __future__ import annotations

import asyncio
import os
from contextlib import AsyncExitStack
from datetime import timedelta
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
from app.jobs.audit_draw import QueueTickPolicy, daily_queue_tick
from app.jobs.billing_close import billing_close
from app.jobs.capture import BatchRequest, CapturePolicy, capture_batch, capture_tick
from app.jobs.day_close import day_close
from app.jobs.discovery import discover_nvr
from app.jobs.retention import RetentionPolicy, retention_daily
from app.observability import capture_exception, init_sentry, sentry_installed
from app.services import storage as storage_module
from app.services.alerts import AlertSender
from app.services.frame_source import FrameSourcePool
from app.settings import get_settings

if TYPE_CHECKING:
    from taskiq import AsyncBroker, ScheduledTask, ScheduleSource

    from app.settings import Settings

log = structlog.get_logger(__name__)

__all__ = [
    "BILLING_CLOSE_CRON",
    "DAY_CLOSE_CRON",
    "DEFAULT_LOG_LEVEL",
    "DIGEST_CRON",
    "DISCOVERY_QUEUE",
    "JOBS_QUEUE",
    "LOG_LEVEL_ENV",
    "MARKET_CRON_OFFSET",
    "QUEUE_TICK_CRON",
    "RETENTION_CRON",
    "SENTRY_DSN_ENV",
    "SWEEP_CRON",
    "TICK_CRON",
    "ObservedScheduler",
    "alert_sweep_task",
    "billing_close_task",
    "broker",
    "capture_batch_task",
    "capture_tick_task",
    "daily_digest_task",
    "day_close_task",
    "daily_queue_tick_task",
    "discover_nvr_task",
    "enqueue_discovery",
    "retention_daily_task",
    "scheduler",
]


VALKEY_URL_ENV: Final[str] = "VALKEY_URL"
DEFAULT_VALKEY_URL: Final[str] = "redis://cache:6379/0"
"""`compose.yaml` dagi `${VALKEY_URL:-redis://cache:6379/0}` bilan BIR XIL standart."""

SENTRY_DSN_ENV: Final[str] = "SENTRY_DSN"
LOG_LEVEL_ENV: Final[str] = "LOG_LEVEL"
DEFAULT_LOG_LEVEL: Final[str] = "info"
"""Kuzatuv sozlamalari — muhitdan TO'G'RIDAN-TO'G'RI, `VALKEY_URL` bilan bir xil qoida.

=============================================================================
IKKI SABAB, VA IKKINCHISI PLANERGA XOS.

**(a) `_broker_url()` BILAN BIR XIL QOIDA.** Bu `settings.py` ning NUSXASI
emas: qiymat AYNAN o'sha muhit o'zgaruvchisidan va AYNAN o'sha standart
bilan olinadi (`compose.yaml`: `SENTRY_DSN: ${SENTRY_DSN:-}`,
`LOG_LEVEL: ${LOG_LEVEL:-info}`), farqi faqat O'QISH PAYTIDA. Nomlarning
`Settings` bilan mosligi `tests/unit/test_scheduler_observability.py::
test_scheduler_env_names_agree_with_settings` da QULFLANADI — nom ayrilsa
darvoza qizaradi.

**(b) `Settings` PLANERNI OMBOR REKVIZITIGA BOG'LAB QO'YARDI.**
`settings.py:329` bo'sh `S3_ACCESS_KEY` ni RAD ETADI, `scheduler`
jarayoni esa bugun `get_settings()` ni UMUMAN chaqirmaydi (u faqat
`_open_worker_resources` da, ya'ni WORKER jarayonida chaqiriladi). Ilmoqni
`get_settings()` ustiga qurish planerni YANGIDAN ombor rekvizitiga
bog'lardi va kuzatuv qatlami o'zi kuzatishi kerak bo'lgan nosozlikdan
yiqilardi — «ombor sozlamasi buzildi» hodisasi hech qachon Sentry'ga
yetib bormasdi.
=============================================================================
"""

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

QUEUE_TICK_CRON: Final[str] = "30 19 * * *"
"""Nazoratchi navbatlari — 19:30 (Toshkent), oxirgi slotdan (18:00) KEYIN.

=============================================================================
⛔⛔ VAQT — XOLISLIK QARORI, QULAYLIK EMAS (05-RESEARCH §C.8, 2-dushman).

Ko'r audit doirasi kunning BARCHA slotlarini qamrashi shart. Kun
o'rtasida tortilgan namuna faqat ertalabki slotlardan iborat bo'lardi va
kunning ikkinchi yarmi (16:00, 18:00) o'lchovga UMUMAN kirmasdi — ya'ni
«tasodifiy namuna» degan da'vo jimgina «ertalabki namuna» ga aylanardi.

⛔ SHU SABABDAN NOANIQ NAVBAT HAM SHU YERDA, SOAT SAYIN EMAS.

   Noaniq navbatni tez-tez qurish o'z-o'zicha oqilona ko'rinadi (bandlar
   kun bo'yi qo'shiladi). Lekin o'shanda kun oxiriga borib BARCHA
   `uncertain` hodisalar allaqachon noaniq navbatda bo'lardi va ko'r
   audit namunasi ularni `ON CONFLICT DO NOTHING` bilan JIMGINA
   yo'qotardi — cron JADVALI 2-dushmanni qaytadan ochardi.

   Chaqiruv TARTIBINI kod majburlaydi (`daily_queue_tick`), CADENCE ni
   esa BITTA vazifa. Ikkalasi ham kerak.

⚠ 19:30 = 18:00 + grace + aniqlash quyruq vaqti; dayjestdan (20:00)
  OLDIN, ya'ni kunlik xabar navbat qurilgandan keyin chiqadi.

⚠ NAZORATCHI KECHAGI NAVBATNI BUGUN KO'RADI va bu KUTILGAN xulq:
  byudjet `zone_reviews.decided_at` bo'yicha sanaladi (05-10), ya'ni
  kechagi qoldiq BUGUNGI diqqat byudjetini yeydi.
"""

DAY_CLOSE_CRON: Final[str] = "40 3 * * *"
"""Kun yopilishi — KECHASI 03:40 (Toshkent) va u KECHAGI kunni yopadi.

=============================================================================
⛔⛔ VAQT «SHU KUNNING OXIRI» EMAS, «KEYINGI KUNNING ERTALABI» — VA BU
    AI-06 NING TALABI.

D-19: «kun oxirigacha tasdiqlanmagan `uncertain` -> bo'sh». Namuna va
noaniq navbat 19:30 da quriladi (`QUEUE_TICK_CRON`), nazoratchi esa
ularni ERTASI KUNI ko'radi (o'sha docstringning oxirgi bandi). Ya'ni
kun 19:30 da yopilsa nazoratchining butun ish oynasi kesib tashlanardi:
har bir band «ko'rilmagani uchun bo'sh» bo'lib qolardi va D-19 ning
hisoblagichi HAR KUNI to'liq bo'lardi — signal doimiy shovqinga
aylanardi.

⚠ KECHAGI KUN YOPILADI (`business_today() - 1`), bugungisi EMAS: bugungi
  kun 03:40 da hali BOSHLANMAGAN ham (birinchi slot 06:00).

⚠ QAYTA HISOBLASH XATO EMAS. Nazoratchi kechagi bandga bugun javob
  yozsa, o'sha kunning materializatsiyasi eskiradi — va u
  `day_close(business_date=...)` ni qayta chaqirish bilan tuzatiladi
  (`ON CONFLICT DO UPDATE`, `occupancy_repo._MATERIALIZE_SLOT`). Job
  KONVERGENT, ya'ni o'tkazib yuborilgan yugurish yo'qotish EMAS.

⚠ 03:40 — `RETENTION_CRON` (03:20) DAN KEYIN va u ataylab: ikkalasi ham
  kechasi ishlaydi, lekin retention arxiv bo'ylab I/O qiladi. Bir
  daqiqada boshlansalar disk uchun raqobat qilardilar; 20 daqiqa farq
  ularni ajratadi. Kadr olish oynasi (06:00–18:00) ikkalasidan ham
  uzoqda.
=============================================================================
"""

BILLING_CLOSE_CRON: Final[str] = "10 4 * * *"
"""Kunlik patta hisobi — KECHASI 04:10 (Toshkent) va u KECHAGI kunni yopadi.

=============================================================================
⛔⛔ (a) `DAY_CLOSE_CRON` (03:40) DAN KEYIN — VA BU O'LCHANGAN, TANLOV EMAS.

`stall_slot_occupancy` ning YAGONA yozuvchisi `occupancy_repo.
materialize()` va uni faqat `day_close` chaqiradi, ya'ni D kunining
slot qatorlari D + 1 ning 03:40 da TUG'ILADI. `billing_close` esa
`billable_stalls()` orqali FAQAT materializatsiya qilingan qatorlarni
o'qiydi (D-03).

Vazifa 03:40 dan OLDIN (masalan o'sha kunning 20:30 ida) yugurganda slot
jadvalida o'sha kun uchun ⛔ NOL qator bo'lardi: job hech nima yozmasdi
va ⛔ XATO HAM BERMASDI — «hammasi joyida» bilan bir xil ko'rinadigan
sukunat. 30 daqiqalik oraliq `day_close` ning uzoq bozorlarda cho'zilishi
uchun zaxira.

⛔ (b) ORALIQ `RETENTION_CRON`(03:20) -> `DAY_CLOSE_CRON`(03:40) FARQI
   BILAN BIR XIL MULOHAZA: ketma-ket ishlaydigan kechki vazifalar bir
   daqiqada boshlanmasligi kerak. Bu yerda raqobat disk uchun emas,
   BAZA uchun: `day_close` 1000 rastaga 7000 qator yozadi.

⛔ (c) TARTIB KAFOLATI BU SATRGA TAYANMAYDI (D-13 ning MAZMUNI).
   `billing_close` bandlikka faqat O'QISH uchun tegadi va IDEMPOTENT
   (`ON CONFLICT DO NOTHING`), ya'ni noto'g'ri tartibda yugursa ham
   QAYTA YUGURISH tuzatadi. Cron satri faqat NARXNI kamaytiradi —
   kafolatni `daily_charges` ning idempotentlik kaliti beradi.

=============================================================================
⛔⛔ DEPLOY BANDI — MEXANIK RAVISHDA USHLANMAYDI, SHU YERGA YOZILADI.

Cron jadvali `import` PAYTIDA olinadi (`LabelScheduleSource`, fayl
boshidagi planer bo'limi), ya'ni YANGI VAZIFA `scheduler` KONTEYNERI
QAYTA ISHGA TUSHIRILMAGUNCHA RO'YXATGA OLINMAYDI:

    docker compose up -d --force-recreate scheduler

⛔ BUNI BIRORTA TEST USHLAMAYDI: testlar `broker.task` reyestrini
   jarayonning O'ZIDA o'qiydi, prodda esa eski jarayon eski jadval bilan
   ishlab turaveradi — vazifa hech qachon ishlamaydi va xato ham
   chiqmaydi.

⚠ YAGONA MEXANIK HIMOYA — YURAK URISHINING YO'QLIGI: `billing_close`
  `self_check.EXPECTED_COMPONENTS` va `alerting._platform_signals`
  ning `watched` ro'yxatiga qo'shilgan, ikkinchisida esa `None` HAM
  eskirish. Ya'ni band unutilsa `billing_close_stale` alerti ochiladi.

=============================================================================
⚠ IKKINCHI CRON QO'SHILMAYDI (A8) va bu ONGLI rad etish. «Kechqurun yana
  bir ko'r» varianti kuniga IKKI chaqiruv berardi va u ikki narsani
  buzardi: (1) kechki yugurish hali materializatsiya qilinmagan kunni
  ko'rib `no_slot_rows` ni shishirardi; (2) «qaysi yugurish yozdi?»
  savoli har nosozlikda qaytadan so'ralardi — ikki haqiqat manbai.
  Kech kelgan tasdiqlar `charge_adjustments` yo'li bilan hal bo'ladi
  (`billing_close.py` docstringining 5-bandi).
=============================================================================
"""


class ObservedScheduler(TaskiqScheduler):
    """`on_ready` ni o'rab oladigan planer — YUTILGAN ISTISNONI E'LON QILADI.

    =========================================================================
    ⛔ NIMA UCHUN KERAK — O'LCHANGAN VENDOR XULQI (taskiq 0.12.4).

      cli/scheduler/run.py:157-174  `send()` da `try/except` UMUMAN yo'q:
                                    u to'g'ridan-to'g'ri
                                    `await scheduler.on_ready(...)` qiladi
      cli/scheduler/run.py:346-350  `send_task.add_done_callback(...)` faqat
                                    nomni reyestrdan O'CHIRADI — `.result()`
                                    ham, `.exception()` ham chaqirilmaydi

    Ya'ni Valkey yetib bo'lmaganda:

      * tik navbatga TUSHMAYDI -> kadr olinmaydi;
      * `alert_sweep` ham planer boshqaruvida -> TELEGRAM YO'LI HAM
        TO'XTAYDI, ya'ni nosozlikni aytadigan kanalning o'zi o'chadi;
      * istisno faqat asyncio ning «Task exception was never retrieved»
        satriga aylanadi va Sentry'ga HECH QACHON bormaydi.

    Qolgan yagona detektor — `/internal/self-check`, uning tashqi
    kuzatuvchisi esa D-21 bo'yicha ataylab kod EMAS (hujjat + ops bandi).
    =========================================================================

    ⚠ ISTISNO QAYTA KO'TARILADI VA BU ATAYIN: taskiq semantikasi
      O'ZGARMAYDI (M-6 bo'yicha uni `send()` ushlamaydi va bu bizning
      ishimiz emas). Bu qatlam faqat QO'SHADI — jurnal va Sentry.

    ⚠ `sentry_sdk` BU FAYLGA IMPORT QILINMAYDI: `app/observability.py`
      SDK ning yagona uyi bo'lib qoladi, ya'ni `before_send`/
      `before_breadcrumb` siz o'rnatish yo'li umuman ochilmaydi (T-04-98).

    ⚠ MONKEY-PATCH TALAB QILINMAYDI: `TaskiqScheduler.on_ready` — oddiy
      `async def` metod (`scheduler/scheduler.py:36-60`), ya'ni meros
      olib override qilish YETADI va uni taskiq ning o'zi hujjatlaydi.
    """

    async def on_ready(self, source: ScheduleSource, task: ScheduledTask) -> None:
        """Vazifani navbatga qo'yadi; yiqilsa — jurnal + Sentry, keyin QAYTA KO'TARADI."""
        try:
            await super().on_ready(source, task)
        except Exception as exc:
            log.exception(
                "scheduler_send_failed",
                task_name=task.task_name,
                schedule_id=task.schedule_id,
                source=type(source).__name__,
            )
            capture_exception(exc)
            raise


scheduler: TaskiqScheduler = ObservedScheduler(broker=broker, sources=[LabelScheduleSource(broker)])
"""`taskiq scheduler app.worker:scheduler` IMPORT QILADIGAN obyekt.

⚠ QURILISH `get_settings()` GA BOG'LANMAYDI — `broker` bilan aynan bir xil
  sabab (modul docstringi): planerni import qilishning O'ZI to'liq muhitni
  talab qilardi va `app.main` ni ham olib ketardi.

⚠ `LabelScheduleSource` — jadval KODDAN, Redis'dan EMAS. Sabab modul
  docstringining planer bo'limida: Valkey `--save "" --appendonly no`
  bilan ishlaydi va `RedisScheduleSource` bilan kesh qayta ko'tarilganda
  jadval JIMGINA yo'qolardi.

⚠ TUR `ObservedScheduler`, LEKIN SHARTNOMA O'ZGARMAYDI: taskiq CLI
  `isinstance(scheduler, TaskiqScheduler)` ni tekshiradi
  (`cli/scheduler/run.py:386-391`) va meros bu shartni saqlaydi.
"""


# ==========================================================================
# ⚠⚠ NEGA AYNAN `CLIENT_STARTUP` — ZANJIR SATR RAQAMLARI BILAN (04-13).
#
#   cli/scheduler/run.py:392   `scheduler.broker.is_scheduler_process = True`
#   cli/worker/run.py:148      `broker.is_worker_process = True` <- BOSHQA bayroq
#   cli/scheduler/run.py:406   `await scheduler.startup()`
#   scheduler/scheduler.py:34  -> `await self.broker.startup()`
#   abc/broker.py:187-191      `event = CLIENT_STARTUP`; u `WORKER_STARTUP`
#                              ga FAQAT `is_worker_process` rost bo'lganda
#                              almashadi
#
# Ya'ni planer jarayonida `is_worker_process` `False` bo'lib qoladi va
# `WORKER_STARTUP` ilmog'i HECH QACHON ishlamaydi.
#
# ⚠ `_open_worker_resources` GA TEGILMAYDI — u TO'G'RI jarayonda TO'G'RI
#   ishlayapti. Bu ilmoq uni almashtirmaydi, YONIGA qo'shiladi.
# ==========================================================================
@broker.on_event(TaskiqEvents.CLIENT_STARTUP)
async def _install_client_observability(state: TaskiqState) -> None:
    """Planer jarayonining kuzatuvi — jurnal + Sentry, RESURS YO'Q.

    ⚠ API JARAYONIDA HAM ATESHLANADI VA U YERDA NO-OP: `app/main.py::
      lifespan` avval `init_sentry()` ni chaqiradi, keyin `broker.startup()`
      ni — o'sha `startup()` esa `is_worker_process` yolg'on bo'lgani uchun
      aynan shu hodisani ateshlaydi. `sentry_installed()` ikkinchi
      `sentry_sdk.init()` ni to'sadi (`app/observability.py` docstringi).

    ⚠ `get_settings()` CHAQIRILMAYDI: sabab `SENTRY_DSN_ENV` konstantasi
      docstringining (b) bandida — `Settings` bo'sh `S3_ACCESS_KEY` ni rad
      etadi va planer bugun ombor rekvizitisiz ham ko'tariladi.

    ⚠ JIM ISHLASH TAQIQLANGAN — `_open_worker_resources` ning
      `worker_started` satri bilan AYNAN bir xil qoida: «Sentry o'chiq»
      holati jurnal satrida ochiq turishi kerak, aks holda uni
      «ishlayapti» deb o'ylash mumkin.
    """
    del state  # planer holatsiz (D-02): bu ilmoq `TaskiqState` ga hech nima yozmaydi

    if sentry_installed():
        log.info("client_observability_skipped", queue=JOBS_QUEUE, reason="already_installed")
        return

    configure_logging(os.environ.get(LOG_LEVEL_ENV) or DEFAULT_LOG_LEVEL)
    installed = init_sentry(os.environ.get(SENTRY_DSN_ENV) or "")
    log.info("scheduler_started", queue=JOBS_QUEUE, sentry=installed)


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

    ⚠ SENTRY HAM SHU YERDA (04-12) VA U «QO'SHIMCHA» EMAS. Kadr olish,
      saqlash siyosati va alert supurgisi AYNAN shu jarayonda ishlaydi;
      API jarayonidagi o'rnatish ularning istisnolarini UMUMAN ko'rmaydi.
      Usiz FOUND-06 ning «xatolar Sentry'da» jumlasi 4-fazaning O'Z
      xatolari uchun yolg'on bo'lardi va nosozlik faqat konteyner
      jurnalida qolardi (`app/observability.py` docstringi).
    """
    settings = get_settings()
    configure_logging(settings.log_level)
    sentry_enabled = init_sentry(settings.sentry_dsn)

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
    state.queue_tick = _queue_tick_policy(settings)

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

    log.info(
        "worker_started",
        queue=JOBS_QUEUE,
        alerts=settings.alerts_enabled,
        sentry=sentry_enabled,
    )


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


def _queue_tick_policy(settings: Settings) -> QueueTickPolicy:
    """`Settings` -> `QueueTickPolicy` — `_retention_policy` bilan bir xil qaror.

    ⛔ `sample_size` `review_blind_daily_budget` DAN OLINADI va ikkinchi
       sozlama YOZILMAGAN: D-13 bitta son beradi («kuniga 30 band»), ikki
       sozlama esa ajralib ketardi va ajralishning ikkala yo'nalishi ham
       JIM nosozlik (`settings.py` dagi bo'lim izohi).
    """
    return QueueTickPolicy(
        sample_size=settings.review_blind_daily_budget,
        eval_ratio=settings.review_blind_eval_ratio,
        uncertain_limit=settings.review_uncertain_daily_budget,
        midpoint=settings.review_uncertain_midpoint,
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


@broker.task(
    task_name="review.queue_tick",
    schedule=[{"cron": QUEUE_TICK_CRON, "cron_offset": MARKET_CRON_OFFSET}],
)
async def daily_queue_tick_task(context: Annotated[Context, TaskiqDepends()]) -> None:
    """YUPQA QOBIQ — ko'r audit namunasi VA noaniq navbat (05-11, AI-03/AI-04).

    ⛔ IKKI QADAM BITTA VAZIFADA VA TARTIBI KODDA (`daily_queue_tick`):
       avval ko'r audit tortiladi, keyin noaniq navbat quriladi. Ikkita
       alohida vazifa yozilsa planer ularni MUSTAQIL jadval bilan
       chaqirardi va tartib kafolati cron satrlariga ko'chib ketardi —
       ya'ni xolislik kafolati kod tekshiruvidan CHIQIB ketardi
       (`QUEUE_TICK_CRON` docstringi).

    ⚠ BIZNES-KUN QOBIQDA HISOBLANADI, jobda EMAS (`daily_digest_task`
      bilan bir xil qoida): job uni ARGUMENT sifatida oladi va shu bilan
      «qaysi kun?» savoli testda bitta qiymatga aylanadi.
    """
    state = context.state
    await daily_queue_tick(
        state.sessionmaker,
        business_date=business_today(),
        policy=state.queue_tick,
    )


@broker.task(
    task_name="occupancy.day_close",
    schedule=[{"cron": DAY_CLOSE_CRON, "cron_offset": MARKET_CRON_OFFSET}],
)
async def day_close_task(context: Annotated[Context, TaskiqDepends()]) -> None:
    """YUPQA QOBIQ — kun yopilishi va rasta-slot materializatsiyasi (05-12, AI-05/AI-06).

    ⛔ KECHAGI KUN YOPILADI, BUGUNGISI EMAS (`DAY_CLOSE_CRON` docstringi):
       tik 03:40 da ishlaydi, bugungi kunning birinchi sloti esa 06:00 da.
       `business_today()` berilsa job HAR KUNI BO'SH kunni yopardi va
       kechagi kun HECH QACHON materializatsiya qilinmasdi — hisobot
       doim bo'sh bo'lardi va birorta xato chiqmasdi.

    ⚠ BIZNES-KUN QOBIQDA HISOBLANADI, jobda EMAS (`daily_digest_task`
      bilan bir xil qoida): job uni ARGUMENT sifatida oladi va shu bilan
      «qaysi kun?» savoli testda bitta qiymatga aylanadi.
    """
    state = context.state
    await day_close(state.sessionmaker, business_date=business_today() - timedelta(days=1))


@broker.task(
    task_name="billing.close",
    schedule=[{"cron": BILLING_CLOSE_CRON, "cron_offset": MARKET_CRON_OFFSET}],
)
async def billing_close_task(context: Annotated[Context, TaskiqDepends()]) -> None:
    """YUPQA QOBIQ — kunlik patta hisobi (06-07, BILL-01/BILL-02/BILL-04).

    ⛔ KECHAGI KUN YOPILADI, BUGUNGISI EMAS (`BILLING_CLOSE_CRON`
       docstringi): tik 04:10 da ishlaydi va bugungi kunning birinchi
       sloti 06:00 da. `business_today()` berilsa job HAR KUNI hali
       boshlanmagan kunni «yopardi» — hisob YOZILMASDI, `no_slot_rows`
       esa har kuni butun bozor bo'lib turardi, kechagi kun esa HECH
       QACHON hisoblanmasdi. Xato chiqmasdi.

    ⚠ BIZNES-KUN QOBIQDA HISOBLANADI, jobda EMAS (`day_close_task` bilan
      aynan bir xil qoida): job uni ARGUMENT sifatida oladi va shu bilan
      «qaysi kun?» savoli testda bitta qiymatga aylanadi.

    ⚠ IKKINCHI JADVAL YO'Q (A8) — sabab cron konstantasining oxirgi
      bandida: kuniga BITTA chaqiruv, kech tasdiqlar esa
      `charge_adjustments` yo'lidan hal bo'ladi.
    """
    state = context.state
    await billing_close(state.sessionmaker, business_date=business_today() - timedelta(days=1))


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
