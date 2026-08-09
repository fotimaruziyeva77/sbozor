"""Kadr olish -> CV navbati: cross-servis kontrakt va sifat filtri (05-08/T3).

=============================================================================
BU FAYL UCH XIL SAVOLGA JAVOB BERADI VA UCHALASI HAM BOSHQA MEXANIZM.

  1. NAVBATNING O'ZI — haqiqiy Valkey ustida: xabar `LIST` ga tushdimi,
     ichida nima bor, `task_name` to'g'rimi.
  2. QUVUR SHARTLARI — `_capture_one` chaqiruvi TRANZAKSIYADAN KEYIN va
     FAQAT `quality_verdict='ok'` uchun bo'ladimi.
  3. IKKI KOD BAZASINING KONTRAKTI — navbat nomi va vazifa nomi
     `core-api` da va `cv-service` da BIR XILMI.

Uchinchisi eng nozik va u §S-10 ning naqshi bilan yechiladi: darvoza
SANOQ emas, MANBADAN HOSILA. `cv-service` ni import qilib bo'lmaydi
(uning `app` paketi nomdosh va `onnxruntime`/`supervision`/`cv2` bu
image'da ATAYIN yo'q — `tests/unit/test_runtime_deps.py:91-94`), shuning
uchun uning MANBA MATNI o'qiladi.

⚠ MATN O'QISH — IMPORT DAN KUCHSIZROQ VA BU YASHIRILMAYDI. U «ikkala
  faylda bir xil satr yozilgan» ni tasdiqlaydi, «ikkala JARAYON bir xil
  navbatga qaradi» ni EMAS. Ikkinchisi faqat to'liq compose yugurishida
  ko'rinadi va u `05-15` ning bandi. Lekin matn darvozasi ENG EHTIMOLLI
  nosozlikni — bittasini o'zgartirib, ikkinchisini unutishni — to'liq
  yopadi.
=============================================================================
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import TYPE_CHECKING, Final, cast
from uuid import uuid4

import pytest
from app.services.cv_queue import (
    CV_DETECT_TASK,
    CV_ENQUEUE_TIMEOUT_SECONDS,
    CV_QUEUE_NAME,
    cv_detect_task,
    enqueue_detect,
)
from app.worker import ENQUEUE_TIMEOUT_SECONDS, JOBS_QUEUE
from taskiq_redis import ListQueueBroker

if TYPE_CHECKING:
    from redis.asyncio import Redis
    from taskiq import Context

REPO_ROOT: Final = Path(__file__).resolve().parents[2]
CV_WORKER_SOURCE: Final = REPO_ROOT / "services" / "cv-service" / "app" / "worker.py"
"""`cv-service` ning navbat qatlami — MANBA sifatida o'qiladi, import qilinmaydi."""


def _constant(source: str, name: str) -> str:
    """`NAME: Final[str] = "qiymat"` dan qiymatni ajratadi.

    ⚠ REGEX `Final` NI TALAB QILADI: oddiy tayinlash (`NAME = "x"`)
      keyinroq qayta yozilishi mumkin va u konstanta bo'lmasdi. Ya'ni
      darvoza faqat QIYMATNI emas, e'lonning SHAKLINI ham qulflaydi.
    """
    match = re.search(rf'^{name}:\s*Final\[str\]\s*=\s*"([^"]+)"', source, re.MULTILINE)
    assert match is not None, (
        f"`{name}` `cv-service/app/worker.py` da `Final[str]` konstanta "
        "sifatida topilmadi. Nom yoki e'lon shakli o'zgargan bo'lsa bu "
        "darvoza SHU YERDA yangilanishi kerak — jimgina o'tkazib "
        "yuborilmasin."
    )
    return match.group(1)


# ===========================================================================
# 1. IKKI KOD BAZASINING KONTRAKTI
# ===========================================================================


def test_the_cv_queue_name_matches_the_cv_service_source() -> None:
    """Navbat nomi ikkala kod bazasida AYNAN BIR XIL.

    Ajralib ketsa xabarlar `sbozor:cv` ga tushar, `cv-service` esa boshqa
    ro'yxatni tinglardi. HECH QANDAY XATO chiqmasdi: `LPUSH` muvaffaqiyatli,
    `BRPOP` esa abadiy kutar edi. Nosozlik faqat «hisobot bo'sh» bo'lib
    ko'rinardi.
    """
    source = CV_WORKER_SOURCE.read_text(encoding="utf-8")
    assert _constant(source, "CV_QUEUE") == CV_QUEUE_NAME


def test_the_detect_task_name_matches_the_cv_service_source() -> None:
    """Vazifa nomi ikkala kod bazasida AYNAN BIR XIL.

    Nom mos kelmasa `cv-service` xabarni «noma'lum vazifa» deb tashlab
    yuborardi — jurnal satri bilan, lekin hech qanday alertsiz.
    """
    source = CV_WORKER_SOURCE.read_text(encoding="utf-8")
    assert _constant(source, "DETECT_TASK_NAME") == CV_DETECT_TASK


def test_cv_queue_name_differs_from_core_queue() -> None:
    """⛔ IKKI NAVBAT AJRATILGAN — RUNTIME DA tasdiqlanadi.

    Bir xil bo'lsa `BRPOP` vazifani TASODIFIY jarayonga berardi: aniqlash
    vazifasi `core-api` worker'iga tushishi mumkin edi va u yerda
    `onnxruntime` UMUMAN yo'q. Nosozlik tasodifiy va qayta
    takrorlanmaydigan bo'lardi — eng qimmat sinf.
    """
    assert CV_QUEUE_NAME != JOBS_QUEUE


def test_the_two_enqueue_timeouts_agree() -> None:
    """Ikki nashr yo'lining chegarasi bir xil — «qaysi biri sekinroq?» savoli yo'q."""
    assert CV_ENQUEUE_TIMEOUT_SECONDS == ENQUEUE_TIMEOUT_SECONDS


def test_the_capture_job_never_imports_the_queue_library() -> None:
    """D-06: `app/jobs/` da navbat kutubxonasi IMPORT QILINMAYDI.

    `capture.py` `cv_queue.enqueue_detect` ni chaqiradi, `taskiq` ni EMAS.
    Mexanizm almashtirilganda ko'chiriladigan yagona fayl —
    `app/services/cv_queue.py`.
    """
    source = (REPO_ROOT / "services" / "core-api" / "app" / "jobs" / "capture.py").read_text(
        encoding="utf-8"
    )
    matches = re.findall(r"^\s*(?:import|from)\s+taskiq", source, re.MULTILINE)
    assert matches == [], f"`app/jobs/capture.py` `taskiq` ni import qilmoqda: {matches}"


# ===========================================================================
# 2. NASHR QILISH — HAQIQIY VALKEY USTIDA
# ===========================================================================


async def test_ok_frame_is_enqueued_once(valkey_url: str, valkey_client: Redis) -> None:
    """Navbatda AYNAN BITTA xabar va uning `task_name` i `cv.detect`.

    HAQIQIY Valkey, mock EMAS — `tests/conftest.py::valkey_client` dagi
    sabab: qalbaki klient semantikani TAXMIN qiladi va farqi faqat
    prod'da ko'rinardi.
    """
    market_id, snapshot_id = uuid4(), uuid4()
    target = ListQueueBroker(valkey_url, queue_name=CV_QUEUE_NAME)
    await target.startup()
    try:
        assert await enqueue_detect(market_id=market_id, snapshot_id=snapshot_id, target=target)
    finally:
        await target.shutdown()

    assert await valkey_client.llen(CV_QUEUE_NAME) == 1
    raw = await valkey_client.lpop(CV_QUEUE_NAME)
    assert isinstance(raw, bytes), f"navbatga hech nima tushmadi: {raw!r}"
    payload = raw.decode()

    assert f'"market_id": "{market_id}"' in payload
    assert f'"snapshot_id": "{snapshot_id}"' in payload
    assert CV_DETECT_TASK in payload


async def test_the_message_carries_no_frame_bytes(valkey_url: str, valkey_client: Redis) -> None:
    """⛔ XABARDA KADR BAYTLARI YO'Q — FAQAT IDENTIFIKATORLAR (RESEARCH §E.13).

    Ikki mustaqil sabab:
      * hajm — ~500 KB x 175 kadr/kun/bozor brokerni bo'g'ardi;
      * bardoshlilik — 4-fazaning Valkey'i `--save "" --appendonly no`
        bilan ishlaydi, ya'ni unga hech qanday MUHIM ma'lumot ishonib
        topshirilmaydi. Kadr S3 da, qator Postgres'da.
    """
    target = ListQueueBroker(valkey_url, queue_name=CV_QUEUE_NAME)
    await target.startup()
    try:
        await enqueue_detect(market_id=uuid4(), snapshot_id=uuid4(), target=target)
    finally:
        await target.shutdown()

    raw = await valkey_client.lpop(CV_QUEUE_NAME)
    assert isinstance(raw, bytes)
    # Xabar UZUNLIGI ham darvoza: identifikatorlardan iborat payload
    # kilobaytlarga yetmaydi.
    assert len(raw) < 1024, f"navbat xabari kutilganidan katta: {len(raw)} bayt"


async def test_enqueue_failure_does_not_raise() -> None:
    """Broker yiqilganda `enqueue_detect` `False` qaytaradi, ISTISNO EMAS.

    ⚠ XULQIY TEST: `pytest.raises` YO'Q. Bu chaqiruv `_capture_one` ning
      OXIRIDA turadi va u yerda ko'tarilgan istisno kadr olishni
      «yiqilgan» deb belgilardi — holbuki kadr S3 da va `snapshots` da
      allaqachon bor.
    """
    unreachable = ListQueueBroker(
        "redis://cv-queue-yoq.invalid:6379/0",
        queue_name=CV_QUEUE_NAME,
        socket_connect_timeout=0.2,
    )
    assert not await enqueue_detect(market_id=uuid4(), snapshot_id=uuid4(), target=unreachable)


# ===========================================================================
# 3. QUVURDAGI O'RNI — AST BILAN, VA QAMROV CHEGARASI OCHIQ
# ===========================================================================
#
# ⚠⚠ QUYIDAGI IKKI TEST STRUKTURAVIY, XULQIY EMAS — VA BU YASHIRILMAYDI.
#
#    Ular `_capture_one` ning MANBASINI `ast` bilan o'qib, `enqueue_detect`
#    chaqiruvi QAYERDA turganini o'lchaydi. Xulqiy o'lchov `capture_batch`
#    ni to'liq yuritishni talab qiladi va u `-m sim` to'plamining ishi
#    (`test_snapshot_quality.py` — haqiqiy NVR simulyatori, haqiqiy
#    SeaweedFS). Bu yerda takrorlash quvurni ikkinchi marta qurardi.
#
#    NIMANI QO'RIQLAYDI: eng ehtimolli regressiyani — chaqiruvni
#    tranzaksiya ICHIGA ko'chirish yoki `if` shartini olib tashlash.
#    NIMANI QO'RIQLAMAYDI: chaqiruv ISHLAYDIMI degan savolni. Unga
#    `enqueue_detect` ning O'Z testlari (yuqorida, haqiqiy Valkey ustida)
#    va `-m sim` e2e javob beradi.
#
#    ⚠ MATN EMAS, AST: `grep` izohdagi «enqueue_detect» so'zini ham
#      topardi va darvoza O'Z docstringini o'qib yashil bo'lardi (05-07
#      ning `test_detector_has_no_stub.py` da o'rnatgan qoidasi).


def _capture_one_body() -> ast.AsyncFunctionDef:
    source = (REPO_ROOT / "services" / "core-api" / "app" / "jobs" / "capture.py").read_text(
        encoding="utf-8"
    )
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "_capture_one":
            return node
    pytest.fail(
        "`_capture_one` topilmadi. Funksiya qayta nomlangan bo'lsa quyidagi "
        "ikki darvoza HECH NIMANI o'lchamaydi — ular yangilanishi SHART."
    )


def _enqueue_calls(tree: ast.AST) -> list[ast.Call]:
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "enqueue_detect"
    ]


def test_dark_frame_is_not_enqueued() -> None:
    """`enqueue_detect` FAQAT `report.verdict == VERDICT_OK` sharti ostida turadi.

    Shartsiz chaqiruv yaroqsiz kadr uchun ham task qo'yardi va natija HAR
    DOIM `ForeignKeyViolation` bo'lardi (D-21): navbat, worker vaqti va S3
    o'qishi sarflanib, hech qanday hodisa yozilmasdi. «Oldindan filtrlash
    mumkin bo'lgan xatoni IMKONSIZ xatoga aylantirish» — aynan shu.
    """
    function = _capture_one_body()
    guarded = [
        node
        for node in ast.walk(function)
        if isinstance(node, ast.If)
        and _enqueue_calls(node)
        and isinstance(node.test, ast.Compare)
        and isinstance(node.test.left, ast.Attribute)
        and node.test.left.attr == "verdict"
        and any(isinstance(c, ast.Name) and c.id == "VERDICT_OK" for c in node.test.comparators)
    ]
    assert len(guarded) == 1, (
        "`enqueue_detect` `report.verdict == VERDICT_OK` sharti ostida "
        f"AYNAN BIR MARTA turishi kerak, topilgani: {len(guarded)}."
    )
    assert len(_enqueue_calls(function)) == 1, (
        "`_capture_one` da `enqueue_detect` ning IKKINCHI chaqiruvi bor — "
        "biri shartsiz bo'lishi mumkin."
    )


def test_enqueue_happens_after_commit() -> None:
    """Chaqiruv HECH QANDAY `async with` blokining ICHIDA emas.

    `_system_transaction()` — `async with` bilan ochiladigan tranzaksiya
    chegarasi. Chaqiruv uning ichida bo'lsa IKKI nosozlik birdan
    tug'ilardi:

      1. Valkey uzilganda `COMMIT` yiqilardi va KADR OLISH ham yiqilardi
         (holbuki obyekt allaqachon S3 da);
      2. xabar `COMMIT` dan OLDIN chiqsa `cv-service` hali MAVJUD
         BO'LMAGAN `snapshots` qatorini izlab, «ko'rinmadi» deb chiqib
         ketardi — va bu SUKUNAT bilan tugardi.

    ⚠ Predikat `async with` NING BARCHA turini rad etadi, faqat
      `_system_transaction` ni emas: kelajakda boshqa nom bilan ochilgan
      tranzaksiya ham xuddi shu xavfni olib kelardi.
    """
    function = _capture_one_body()
    inside_async_with = [
        call
        for node in ast.walk(function)
        if isinstance(node, ast.AsyncWith)
        for call in _enqueue_calls(node)
    ]
    assert inside_async_with == [], (
        "`enqueue_detect` `async with` blokining ICHIDA turibdi — ya'ni "
        "tranzaksiya hali YOPILMAGAN paytda chaqiriladi."
    )
    assert _enqueue_calls(function), "`_capture_one` da `enqueue_detect` UMUMAN yo'q."


async def test_the_core_api_body_of_the_task_refuses_to_run() -> None:
    """⛔ `cv.detect` TANASI `core-api` da BAJARILSA — `RuntimeError`.

    Bo'sh tana (`pass`) bu holatni JIMGINA yutardi: vazifa
    «muvaffaqiyatli» bo'lib navbatdan yo'qolardi va kadr HECH QACHON
    aniqlanmasdi. Hech qanday xato, hech qanday alert — faqat bo'sh
    hisobot.
    """
    with pytest.raises(RuntimeError, match=CV_DETECT_TASK):
        # `Context` in'ektsiyasi dekorator ostida bo'ladi va tana uni
        # UMUMAN ishlatmaydi (`del context, ...`) — to'liq `Context`
        # qurish tekshirilayotgan da'voga hech nima qo'shmasdi.
        await cv_detect_task.original_func(
            cast("Context", None), market_id=str(uuid4()), snapshot_id=str(uuid4())
        )
