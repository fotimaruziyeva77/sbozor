"""`cv.detect` ni CV navbatiga NASHR QILISH — `core-api` uni HECH QACHON BAJARMAYDI.

=============================================================================
NEGA BU FAYL `app/worker.py` DAN AJRATILGAN (D-06 NING IKKINCHI JOYI).

D-06 navbat kutubxonasini AYNAN BITTA faylda saqlashni talab qiladi va bu
fayl uni IKKINCHIGA chiqaradi. Sabab qat'iy va u qayta ochilmaydi:

    `app/worker.py` ning brokeri `sbozor:jobs` dan O'QIYDI.
    Bu fayl `sbozor:cv` ga FAQAT YOZADI.

`cv.detect` ni o'sha brokerga ro'yxatdan o'tkazish MUMKIN EMAS edi:
`kicker().kiq()` vazifani BROKERNING navbatiga qo'yadi, ya'ni xabar
`sbozor:jobs` ga tushardi va uni `core-api` ning O'Z worker'i tortib
olardi — o'sha jarayonda esa `onnxruntime` ham, `supervision` ham UMUMAN
yo'q. Nosozlik `ModuleNotFoundError` bo'lardi... yo'q, undan ham yomoni:
vazifa tanasi BAJARILARDI va u pastdagi `RuntimeError` ni bergan bo'lardi.

Ya'ni ikkinchi broker TALAB, qulaylik emas — va u KO'RINADIGAN, alohida
faylda turishi kerak.

=============================================================================
⛔ VAZIFA FAQAT NOM BILAN E'LON QILINADI, TANASI ESA YIQILADI.

`taskiq` da xabar yuborish uchun vazifa OBYEKTI kerak, obyekt esa
dekoratorsiz qurilmaydi. Shuning uchun quyida `cv.detect` nomi bilan
vazifa e'lon qilinadi — LEKIN uning tanasi `RuntimeError` tashlaydi.

⚠ BU ATAYIN VA U «HIMOYA» EMAS, SIGNAL. `core-api` bu navbatdan HECH
  QACHON o'qimaydi, ya'ni tananing bajarilishi FAQAT bitta narsani
  bildiradi: kimdir `core-api` worker'ini `sbozor:cv` ga ulab qo'ygan.
  Bo'sh tana (`pass`) o'sha holatni JIMGINA yutardi — vazifa
  «muvaffaqiyatli» bo'lib navbatdan yo'qolardi va kadr HECH QACHON
  aniqlanmasdi. Hech qanday xato, hech qanday alert: faqat bo'sh hisobot.

=============================================================================
⚠ NAVBAT NOMI VA VAZIFA NOMI — KODDA, SOZLAMADA EMAS.

Reja ikkalasini `Settings` ga chiqarishni so'raydi. Bu ATAYIN
BAJARILMADI va sabab bu repoda IKKI MARTA yozilgan:

  * `app/worker.py::JOBS_QUEUE` — «nomni muhit o'zgaruvchisiga chiqarish
    ikki jarayonning jimgina boshqa navbatlarga qarab qolish yo'lini
    ochardi»;
  * `services/cv-service/app/worker.py::CV_QUEUE` (05-02) — AYNAN o'sha
    qaror, aynan o'sha sabab bilan.

Muhit o'zgaruvchisi bu yerda ayniqsa xavfli: qiymat IKKI BOSHQA
KONTEYNERGA beriladi (`core-api` va `cv-service`), ya'ni ularning
ajralib qolishi uchun bitta `.env` satrini unutish yetardi. Nosozlik esa
mutlaqo jim bo'lardi — xabarlar navbatga tushib, hech kim ularni
o'qimasdi.

Buning o'rniga IKKI NUSXA MEXANIK ravishda taqqoslanadi:
`tests/integration/test_capture_enqueues_detect.py` `cv-service` ning
MANBASINI o'qib, quyidagi ikkala satr bilan solishtiradi (§S-10 — darvoza
sanoq emas, MANBADAN hosila).
=============================================================================
"""

from __future__ import annotations

import asyncio
import os
from typing import TYPE_CHECKING, Annotated, Any, Final

import structlog
from taskiq import AsyncBroker, Context, TaskiqDepends
from taskiq_redis import ListQueueBroker

if TYPE_CHECKING:
    from uuid import UUID

__all__ = [
    "CV_DETECT_TASK",
    "CV_ENQUEUE_TIMEOUT_SECONDS",
    "CV_QUEUE_NAME",
    "cv_broker",
    "enqueue_detect",
]

log = structlog.get_logger(__name__)

CV_QUEUE_NAME: Final[str] = "sbozor:cv"
"""`cv-service` ning navbati — `JOBS_QUEUE` («sbozor:jobs») DAN AJRATILGAN.

⚠ NUSXA: asl qiymat `services/cv-service/app/worker.py::CV_QUEUE` da.
  Ikki kod bazasi bir-birini import qila olmaydi (`cv-service` ni
  `core-api` ning runtime'iga olib kirish `onnxruntime`, `supervision` va
  `cv2` ni ham olib kelardi — `tests/unit/test_runtime_deps.py:91-94`
  dagi O'LCHANGAN taqiqni bo'shatgan bo'lardi). Shuning uchun nusxaning
  bir xilligi MANBA MATNI bo'yicha tekshiriladi.
"""

CV_DETECT_TASK: Final[str] = "cv.detect"
"""Vazifa nomi — `cv-service/app/worker.py::DETECT_TASK_NAME` bilan AYNAN BIR XIL.

Nom mos kelmasa `cv-service` xabarni «noma'lum vazifa» deb tashlab
yuborardi — hech qanday xatosiz, faqat jurnal satri bilan. Bu ham
manbadan hosila darvoza bilan qulflangan.
"""

CV_ENQUEUE_TIMEOUT_SECONDS: Final[float] = 5.0
"""`LPUSH` uchun chegara — `worker.py::ENQUEUE_TIMEOUT_SECONDS` bilan bir xil.

⚠ CHEGARA SHU YERDA, PULDA EMAS: broker puli `socket_timeout=None` bilan
  quriladi (usiz `BRPOP` har 5 soniyada yiqilardi — 03-06 da o'lchangan),
  ya'ni chegarasiz `LPUSH` CHEKSIZ kutardi. Osilgan chaqiruv esa kadr
  olish batch'ining ilmog'ini band qilib turardi.
"""


def _broker_url() -> str:
    """Broker manzili — `app/worker.py::_broker_url()` bilan AYNAN bir xil naqsh.

    `Settings` CHAQIRILMAYDI: bu modul `app/jobs/capture.py` dan import
    qilinadi, u esa test to'plamida to'liq muhitsiz ham import qilinadi.
    """
    return os.environ.get("VALKEY_URL") or "redis://cache:6379/0"


cv_broker: AsyncBroker = ListQueueBroker(
    _broker_url(),
    queue_name=CV_QUEUE_NAME,
    # `socket_timeout=None` bu yerda ham beriladi va u `LPUSH` ga
    # ta'sir qilmaydi — sabab `app/worker.py` dagi bloklashda. Nusxa
    # ATAYIN: ikkala broker bir xil sozlangan bo'lishi kerak, aks holda
    # bitta jarayonda ikki xil xulqli pul paydo bo'lardi.
    socket_timeout=None,
    socket_connect_timeout=CV_ENQUEUE_TIMEOUT_SECONDS,
    socket_keepalive=True,
)
"""FAQAT NASHR QILISH uchun broker. `core-api` undan HECH QACHON o'qimaydi.

⚠ `with_result_backend(...)` ATAYIN YO'Q. Natija backend'i «vazifa qanday
  tugadi?» savoliga javob beradi, javobni esa BAJARUVCHI yozadi —
  ya'ni u `cv-service` ning brokeriga tegishli. Bu yerda uni qo'shish
  ikkinchi, hech qachon o'qilmaydigan Valkey ulanishini ochardi.
"""


@cv_broker.task(task_name=CV_DETECT_TASK)
async def cv_detect_task(
    context: Annotated[Context, TaskiqDepends()],
    *,
    market_id: str,
    snapshot_id: str,
) -> None:
    """⛔ BU TANA `core-api` DA HECH QACHON BAJARILMASLIGI KERAK.

    Vazifa faqat NOM va PAYLOAD SHAKLI uchun e'lon qilingan (modul
    docstringi). Uning bajarilishi konfiguratsiya nosozligining
    BELGISIDIR va u jimgina yutilmasligi kerak: aks holda kadr navbatga
    tushar, «bajarilar» va HECH QACHON aniqlanmasdi — hisobot esa
    «bugun birorta band rasta topilmadi» deb ko'rsatardi.

    Haqiqiy amalga oshirilish: `services/cv-service/app/worker.py::detect_task`.

    Raises:
        RuntimeError: har doim.
    """
    del context, market_id, snapshot_id
    raise RuntimeError(
        f"`{CV_DETECT_TASK}` `core-api` jarayonida bajarildi. Bu vazifa "
        f"`{CV_QUEUE_NAME}` navbatiga NASHR QILINADI va uni FAQAT "
        "`cv-service` bajaradi. Bu xabar `core-api` worker'i CV navbatiga "
        "ulanib qolganini bildiradi (`app/services/cv_queue.py` docstringi)."
    )


async def enqueue_detect(
    *,
    market_id: UUID,
    snapshot_id: UUID,
    target: AsyncBroker | None = None,
) -> bool:
    """Kadrni aniqlash navbatiga qo'yadi. XATOSI YUTILADI.

    ⛔ CHAQIRUVCHINI HECH QACHON YIQITMAYDI. CV quvurining nosozligi kadr
      OLISHNI to'xtata olmaydi (`04-PATTERNS.md` §3.3, 4-qadam): kadr
      allaqachon S3 da va `snapshots` da, ya'ni dalil YO'QOLMAGAN. Aniqlash
      esa keyinroq qayta ishga tushirilishi mumkin va u idempotent.

    ⚠ `UUID` LAR MATNGA O'GIRILADI: `taskiq` ning serializatori JSON va
      `json.dumps(UUID(...))` `TypeError` beradi (`enqueue_discovery` bilan
      bir xil qoida, bir xil joyda — CHEGARADA).

    ⚠ `market_id` XABARDA BOR VA U KERAK: `cv-service` RLS ostida
      `snapshots` ni tenant KONTEKSTISIZ o'qiy olmaydi (0 qator). Qiymat
      faqat OYNANI ochadi — yozuvga ketadigan hamma narsa QATORDAN
      o'qiladi (`cv-service/app/jobs/detect.py` docstringi, 4-band).

    Args:
        market_id: kadrning bozori.
        snapshot_id: aniqlanadigan kadr.
        target: brokerni ALMASHTIRISH nuqtasi — FAQAT test uchun
            (`enqueue_discovery` bilan bir xil naqsh).

    Returns:
        `True` — xabar navbatga tushdi; `False` — tushmadi va sabab
        jurnalda. Qaytish qiymati CHAQIRUVCHI uchun MAJBURIY emas: u
        faqat testga va kelajakdagi metrikaga kerak.
    """
    kicker = cv_detect_task.kicker()
    if target is not None:
        kicker = kicker.with_broker(target)

    payload: dict[str, Any] = {
        "market_id": str(market_id),
        "snapshot_id": str(snapshot_id),
    }
    try:
        async with asyncio.timeout(CV_ENQUEUE_TIMEOUT_SECONDS):
            await kicker.kiq(**payload)
    except Exception as exc:  # noqa: BLE001 - kadr olish yiqilmasligi SHART
        # ⚠ `type(exc).__name__` — MATN EMAS. Broker manzili (parol bilan)
        #   `redis-py` ning ba'zi istisnolarida matnda uchraydi va u
        #   jurnalga, u yerdan Sentry'ga chiqardi (T-04-40 bilan bir sinf).
        log.warning("cv_detect_not_enqueued", error=type(exc).__name__, **payload)
        return False

    log.info("cv_detect_enqueued", **payload)
    return True
