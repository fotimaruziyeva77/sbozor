"""PLANER JARAYONINING kuzatuvi — `CLIENT_STARTUP` ilmog'i va yutilgan istisno.

=============================================================================
NEGA BU DARVOZA `test_sentry_scrub.py` DAN ALOHIDA.

`test_sentry_scrub.py` ILMOQLAR haqida (`scrub_event`/`scrub_breadcrumb`
to'g'ri tozalaydimi). Bu fayl esa JARAYON haqida: `taskiq scheduler`
konteynerida `init_sentry()` UMUMAN chaqiriladimi va planerning O'Z
istisnosi biror joyda O'QILADIMI.

Ikkisi boshqa da'vo va ular alohida buziladi: ilmoq mukammal bo'lib,
`init()` chaqirilmasa hodisa hech qachon jo'natilmaydi.
=============================================================================
⛔ BU NOSOZLIK `04-VERIFICATION.md` DA O'LCHANGAN, TAXMIN QILINMAGAN.

Zanjir (taskiq 0.12.4 manbasidan, satr raqamlari bilan):

  cli/scheduler/run.py:392   `scheduler.broker.is_scheduler_process = True`
                             — BOSHQA bayroq; `is_worker_process` ni FAQAT
                             cli/worker/run.py:148 o'rnatadi
  cli/scheduler/run.py:406   `await scheduler.startup()`
  scheduler/scheduler.py:34  -> `await self.broker.startup()`
  abc/broker.py:187-191      `event = CLIENT_STARTUP`; u `WORKER_STARTUP` ga
                             FAQAT `is_worker_process` rost bo'lganda almashadi

Ya'ni planer jarayoni `WORKER_STARTUP` ni HECH QACHON olmaydi va 04-12
qo'shgan ilmoq u yerda ishlamaydi. Nosozlik JIM: konteyner `Up`, jurnal
toza, hodisa esa jo'natilmaydi.
=============================================================================
⛔ IKKINCHI DA'VO — `init_sentry()` NING O'ZI YETARLI EMAS.

  cli/scheduler/run.py:157-174  `send()` da `try/except` UMUMAN yo'q
  cli/scheduler/run.py:346-350  `add_done_callback` faqat nomni reyestrdan
                                O'CHIRADI — `.result()` ham, `.exception()`
                                ham chaqirilmaydi

Ya'ni Valkey yetib bo'lmaganda tik navbatga tushmaydi, `alert_sweep` ham
planer boshqaruvida bo'lgani uchun Telegram yo'li ham to'xtaydi, istisno
esa faqat asyncio ning «Task exception was never retrieved» satriga
aylanadi va Sentry'ga BORMAYDI. `ObservedScheduler.on_ready` shu bo'shliqni
yopadi va taskiq semantikasini O'ZGARTIRMAYDI (istisno qayta ko'tariladi).
=============================================================================

⚠ `unittest.mock` ISHLATILMAYDI: `monkeypatch.setattr` va qo'lda yozilgan
  yozib boruvchi manba yetadi (`test_go2rtc_client.py` naqshi).
"""

from __future__ import annotations

import inspect
from typing import TYPE_CHECKING, Final

import pytest
from app import worker
from app.settings import Settings, get_settings
from cryptography.fernet import Fernet
from structlog.testing import capture_logs
from taskiq import ScheduledTask, ScheduleSource, TaskiqEvents, TaskiqScheduler
from taskiq.exceptions import ScheduledTaskCancelledError

if TYPE_CHECKING:
    from collections.abc import Sequence

_BASELINE_ENV: Final[dict[str, str]] = {
    "DATABASE_URL": "postgresql+asyncpg://sbozor_app:x@db:5432/sbozor",
    "VALKEY_URL": "redis://cache:6379/0",
    "JWT_SECRET": "x" * 48,
    "S3_ACCESS_KEY": "test-access-key",
    "S3_SECRET_KEY": "test-secret-key",
}
"""`Settings()` ning shu fayldan TASHQARIDAGI majburiy maydonlari.

`test_snapshot_settings.py::_BASELINE` bilan bir xil ro'yxat va bir xil
sabab. ⚠ `S3_*` MAJBURIY: `settings.py:329` bo'sh kalitni RAD ETADI — va
aynan shu fakt `worker.py` da `get_settings()` NING QO'LLANMASLIGINI
majbur qiladi (pastdagi `test_scheduler_env_names_agree_with_settings`
docstringi).
"""


def _settings(monkeypatch: pytest.MonkeyPatch, **overrides: str) -> Settings:
    """Muhitdan MUSTAQIL `Settings` — `test_snapshot_settings.py::build` naqshi.

    ⚠ `_env_file=None` MAJBURIY: `tests` konteyneri repozitoriyni `/app` ga
      mount qiladi, ya'ni dasturchining `.env` fayli bu testga KO'RINADI va
      «standart qiymat» da'vosi uning mahalliy sozlamasini o'lchab qolardi
      (04-07 da o'lchangan, `test_snapshot_settings.py` da yozilgan).
    """
    for name in (worker.SENTRY_DSN_ENV, worker.LOG_LEVEL_ENV):
        monkeypatch.delenv(name, raising=False)
    for name, value in _BASELINE_ENV.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setenv("NVR_CREDENTIAL_KEY", Fernet.generate_key().decode())
    for name, value in overrides.items():
        monkeypatch.setenv(name, value)
    get_settings.cache_clear()
    return Settings(_env_file=None)  # type: ignore[call-arg]


class _RecordingSource(ScheduleSource):
    """`pre_send` da ATAYIN yiqiladigan (yoki bekor qiladigan) qalbaki manba.

    ⚠ NEGA `pre_send`: `TaskiqScheduler.on_ready` uni BROKERGA murojaat
      qilishdan OLDIN chaqiradi (`scheduler/scheduler.py:36-60`), ya'ni
      test tirik Valkey talab qilmaydi va u AYNAN «broker yo'lida istisno»
      holatini modellaydi.
    """

    def __init__(self, error: BaseException | None = None) -> None:
        self.error = error
        self.seen: list[ScheduledTask] = []

    async def get_schedules(self) -> list[ScheduledTask]:
        return []

    def pre_send(self, task: ScheduledTask) -> None:
        self.seen.append(task)
        if self.error is not None:
            raise self.error


def _task(name: str = "capture.tick") -> ScheduledTask:
    """Planer yuboradigan vazifaning shakli — `TICK_CRON` bilan bir xil."""
    return ScheduledTask(task_name=name, labels={}, args=[], kwargs={}, cron=worker.TICK_CRON)


def _sources_of(handlers: Sequence[object]) -> list[str]:
    return [inspect.getsource(handler) for handler in handlers]  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# 1. Planer jarayoni ateshlaydigan hodisa uchun ilmoq
# ---------------------------------------------------------------------------


def test_client_startup_hook_installs_sentry() -> None:
    """`CLIENT_STARTUP` reyestrida `init_sentry()` ni chaqiradigan ilmoq BOR.

    =======================================================================
    ⛔ 04-13 GACHA REYESTR BO'SH EDI (`04-VERIFICATION.md` da o'lchandi):

        broker.startup() fires: TaskiqEvents.CLIENT_STARTUP
        handlers for it: []
        sentry active: False

    `SENTRY_DSN` konteynerga berilardi, `init()` esa chaqirilmasdi va
    `sentry_sdk` hech qanday xato bermasdi.
    =======================================================================

    ⚠ NAZORAT — `WORKER_STARTUP` ILMOG'I O'Z JOYIDA QOLADI. Usiz «ilmoq
      qo'shildi» da'vosi ilmoqning KO'CHIRILISHI bilan ham bajarilardi va
      o'shanda worker jarayoni jimgina Sentry'siz qolardi.
    """
    client_handlers = worker.broker.event_handlers[TaskiqEvents.CLIENT_STARTUP]
    assert client_handlers, (
        "`CLIENT_STARTUP` reyestri BO'SH — `taskiq scheduler` jarayoni aynan shu "
        "hodisani ateshlaydi (abc/broker.py:187-191), ya'ni planerning istisnolari "
        "Sentry'ga UMUMAN bormaydi"
    )
    assert any("init_sentry(" in source for source in _sources_of(client_handlers)), (
        "`CLIENT_STARTUP` ilmog'i bor, lekin u `init_sentry()` ni chaqirmaydi — "
        "hodisa registratsiyasining o'zi hech nimani o'rnatmaydi"
    )

    worker_handlers = worker.broker.event_handlers[TaskiqEvents.WORKER_STARTUP]
    assert any("init_sentry(" in source for source in _sources_of(worker_handlers)), (
        "`WORKER_STARTUP` ilmog'i Sentry'ni o'rnatmay qo'ydi — ilmoq QO'SHILMAY, "
        "KO'CHIRILGAN bo'lsa worker jarayoni jimgina kuzatuvsiz qolardi (04-12 regressiyasi)"
    )


# ---------------------------------------------------------------------------
# 2. Muhit nomlarining `Settings` bilan mosligi
# ---------------------------------------------------------------------------


def test_scheduler_env_names_agree_with_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """`worker.py` muhitdan O'QIYDIGAN nomlar `Settings` ning AYNAN o'sha maydonlari.

    =======================================================================
    NEGA ILMOQ `get_settings()` NI CHAQIRMAYDI (O'LCHANGAN CHEGARA).

    `settings.py:329` bo'sh `S3_ACCESS_KEY` ni RAD ETADI. Bugun `scheduler`
    jarayoni `Settings` ni umuman qurmaydi (uni faqat `_open_worker_resources`,
    ya'ni WORKER jarayoni quradi), demak planer ombor rekvizitisiz ham
    ko'tariladi. Kuzatuv ilmog'ini `get_settings()` ustiga qurish planerni
    YANGIDAN ombor rekvizitiga bog'lardi — kuzatuv qatlami o'zi kuzatishi
    kerak bo'lgan nosozlikdan yiqilardi.

    Narxi — nusxa xavfi, va bu test aynan o'sha xavfning QULFI:
    `_broker_url()` ning `VALKEY_URL` uchun qilgan kelishuvi shu ikki
    o'zgaruvchi uchun takrorlanadi va nomlar AYRILSA darvoza qizaradi.
    =======================================================================
    """
    sentinel_dsn = "https://public@sentry.invalid/42"
    tuned = _settings(
        monkeypatch,
        **{worker.SENTRY_DSN_ENV: sentinel_dsn, worker.LOG_LEVEL_ENV: "debug"},
    )
    assert tuned.sentry_dsn == sentinel_dsn, (
        f"`{worker.SENTRY_DSN_ENV}` `Settings.sentry_dsn` ga BORMADI — ilmoq muhitdan "
        "boshqa nomni o'qiyapti va ikkala jarayon boshqa DSN bilan ishlardi"
    )
    assert tuned.log_level == "debug", (
        f"`{worker.LOG_LEVEL_ENV}` `Settings.log_level` ga bormadi — jurnal darajasi "
        "jarayonga qarab jimgina ayrilardi"
    )

    default = _settings(monkeypatch)
    assert default.sentry_dsn == "", (
        "`Settings.sentry_dsn` ning standarti bo'sh EMAS — ilmoqning "
        "`os.environ.get(...) or ''` qoidasi bilan mos kelmaydi"
    )
    assert default.log_level == worker.DEFAULT_LOG_LEVEL, (
        f"standart jurnal darajasi ayrildi: `Settings` -> {default.log_level!r}, "
        f"`worker.DEFAULT_LOG_LEVEL` -> {worker.DEFAULT_LOG_LEVEL!r}"
    )


# ---------------------------------------------------------------------------
# 3/4. Planerning yutilgan istisnosi (M-5/M-6)
# ---------------------------------------------------------------------------


async def test_on_ready_reports_the_swallowed_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    """`on_ready` dagi istisno jurnalga VA Sentry'ga chiqadi.

    ⚠ AYNAN O'SHA ISTISNO OBYEKTI talab qilinadi (`is`), turi emas: yangi
      istisno qurish original stack'ni yo'qotardi va Sentry'dagi hodisa
      «qayerda yiqildi?» savoliga javob bermasdi.
    """
    captured: list[BaseException] = []
    monkeypatch.setattr(worker, "capture_exception", captured.append)

    boom = RuntimeError("broker yetib bo'lmaydi")
    source = _RecordingSource(boom)
    task = _task()

    with capture_logs() as logs, pytest.raises(RuntimeError) as excinfo:
        await worker.scheduler.on_ready(source, task)

    assert excinfo.value is boom
    assert captured == [boom], (
        "`capture_exception` chaqirilmadi (yoki boshqa obyekt bilan chaqirildi) — "
        "planerning istisnosi Sentry'ga BORMAYDI (taskiq uni cli/scheduler/run.py:346-350 "
        "da O'QIMAYDI)"
    )

    failures = [entry for entry in logs if entry.get("log_level") == "error"]
    assert failures, "`log.exception` chaqirilmadi — hodisa jurnalda ham qolmadi"
    assert failures[0].get("exc_info"), "`log.error` ishlatilgan — stack yozilmaydi"
    rendered = repr(failures[0])
    assert task.task_name in rendered, "jurnal satrida `task_name` yo'q — qaysi tik yiqildi?"
    assert task.schedule_id in rendered, "jurnal satrida `schedule_id` yo'q"


async def test_on_ready_keeps_taskiq_semantics(monkeypatch: pytest.MonkeyPatch) -> None:
    """NAZORAT: qatlam faqat QO'SHADI — bekor qilingan vazifa jim o'tadi.

    ⚠ BIRINCHI DA'VO — QOBIQNING O'ZI. Usiz bu nazorat BO'SH TO'PLAM
      ustida yashil bo'lardi: o'ralmagan `TaskiqScheduler.on_ready` ham
      `capture_exception` ni chaqirmaydi (u umuman mavjud emas), ya'ni
      test hech nimani o'lchamasdi — bu fazaning O'ZI qidirayotgan sinf.
    """
    scheduler = worker.scheduler
    assert isinstance(scheduler, TaskiqScheduler), "planer taskiq shartnomasidan chiqib ketdi"
    assert type(scheduler).on_ready is not TaskiqScheduler.on_ready, (
        "`on_ready` O'RALMAGAN — quyidagi nazorat hech nimani o'lchamaydi"
    )

    captured: list[BaseException] = []
    monkeypatch.setattr(worker, "capture_exception", captured.append)

    # `ScheduledTaskCancelledError` — taskiq ning O'Z semantikasi: manba
    # vazifani bekor qildi, bu NOSOZLIK emas (`scheduler/scheduler.py:36-60`
    # uni `logger.info` bilan yutadi).
    source = _RecordingSource(ScheduledTaskCancelledError())
    task = _task("alert.sweep")

    await scheduler.on_ready(source, task)

    assert source.seen == [task], "`super().on_ready()` umuman chaqirilmadi"
    assert captured == [], (
        "bekor qilingan vazifa Sentry'ga hodisa sifatida ketdi — qatlam taskiq "
        "semantikasini O'ZGARTIRDI va shovqin qo'shdi"
    )
