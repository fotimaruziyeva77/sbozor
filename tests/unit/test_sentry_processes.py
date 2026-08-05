"""Sentry darvozasi — SANOQ EMAS, `compose.yaml` DAN HOSILA (04-13, FOUND-06).

=============================================================================
⛔ DARVOZANING O'ZI NOSOZ EDI VA U SHU SABABDAN QAYTA YOZILDI.

04-12 «Sentry ikkala jarayonda ham o'rnatiladi» da'vosini IKKITA **kod
kirish nuqtasi** ro'yxati bilan qulflagan edi:

    tests/unit/test_sentry_scrub.py:176        `(lifespan, _open_worker_resources)`
    tests/integration/test_phase4_criteria.py  `SENTRY_ENTRYPOINTS` — 2 elementli kortej

Ikkalasi ham UCHINCHI **jarayonni** (`scheduler`) struktura jihatidan
ko'ra olmaydi, shuning uchun ular abadiy yashil edi — `04-VERIFICATION.md`
nosozlikni testdan emas, KONTEYNERDAN o'lchab topdi.

⚠ Ro'yxatga uchinchi nomni qo'shish nosozlikni n+1 da QAYTADAN tug'dirardi.
  Shuning uchun bu darvoza «qaysi jarayonlar bizning kodimizni yuritadi?»
  savoliga `compose.yaml` DAN javob oladi: o'sha faylning O'ZI `SENTRY_DSN`
  ni kimga berayotganini biladi. To'rtinchi servis qo'shilgan kuni darvoza
  jimgina eskirmaydi — u YIQILADI.
=============================================================================
DARVOZA UCH BOSQICHDA ISHLAYDI VA HAR UCHALASIDA «TOPILMADI» = YIQILISH:

  (a) JARAYONLARNI TOPISH   — `environment` da `SENTRY_DSN` bo'lgan har servis
  (b) KIRISH NUQTASI        — `command` tokenlari ichidan AYNAN BITTA
                              `modul:atribut` (topilmasa `pytest.fail`)
  (c) O'SHA OBYEKTNING O'Z REYESTRI — obyekt TURIGA qarab mos hodisa
                              reyestrida `init_sentry(` bo'lishi talab
                              qilinadi (noma'lum tur -> `pytest.fail`)

«O'tkazib yuborish» yo'li ATAYIN YO'Q: aynan o'sha yo'l 04-12 ning
darvozasini uchinchi jarayonda jimgina bo'shatgan edi.
=============================================================================
NEGA `compose.yaml` QO'LDA PARSE QILINADI:

`PyYAML` bu loyihaning bog'liqligi EMAS (`test_storage_config.py` ning
modul docstringi). Bu yerda o'sha parser bir pog'ona chuqurlashtiriladi
(servis kalitlari -> `environment` KALITLARI + `command` QIYMATLARI),
lekin qaram bo'lish darajasi o'zgarmaydi. Parserning O'ZI quyi chegaralar
bilan qo'riqlanadi (`test_compose_parser_reads_both_command_shapes`).
=============================================================================
"""

from __future__ import annotations

import importlib
import inspect
import re
from contextlib import suppress
from pathlib import Path
from typing import Final, NamedTuple

import pytest
from fastapi import FastAPI
from taskiq import AsyncBroker, TaskiqEvents, TaskiqScheduler
from taskiq.abc.broker import AsyncBroker as _AsyncBrokerImpl
from taskiq.cli.scheduler.run import run_scheduler

REPO_ROOT: Final = Path(__file__).resolve().parents[2]
COMPOSE: Final = REPO_ROOT / "compose.yaml"

SENTRY_ENV_KEY: Final = "SENTRY_DSN"
"""Jarayonni «kuzatuv va'da qilingan» deb belgilaydigan YAGONA belgi.

⚠ Ro'yxat EMAS, PREDIKAT: darvoza servis NOMLARINI bilmaydi va bilishi
  ham kerak emas. `compose.yaml` bu kalitni kimga bersa, o'sha jarayon
  `init_sentry()` ni chaqirishi SHART.
"""

INIT_MARKER: Final = "init_sentry("
"""Manba matnida izlanadigan chaqiruv.

⚠ `sentry_sdk.init(` EMAS: `init_sentry()` — `before_send`/`before_breadcrumb`
  bilan birga o'rnatiladigan YAGONA yo'l (`app/observability.py`). Xom
  `sentry_sdk.init()` ilmoqlarsiz o'rnatib, sirlarni tozalanmagan holda
  chiqarardi (T-04-98).
"""

MIN_COMPOSE_SERVICES: Final = 8
"""Parser buzilganda darvoza JIMGINA yashil bo'lardi — `test_storage_config.py` qoidasi.

2026-08-05 holati: o'n uch servis. Chegara QUYI, ya'ni yangi servis
qo'shilganda qayta ko'rib chiqilmaydi.
"""

MIN_SENTRY_SERVICES: Final = 3
"""`SENTRY_DSN` oladigan jarayonlarning quyi chegarasi.

2026-08-05 holati: `core-api`, `worker`, `scheduler`. ⚠ Bu QUYI chegara:
to'rtinchi jarayon qo'shilsa test o'zgarmaydi, lekin (b)/(c) bosqichlari
o'sha jarayonni ham TALAB QILADI.

⚠ Servis NOMLARI bu faylda ro'yxat sifatida YOZILMAGAN va bu ataylab —
  aynan nomlar ro'yxati 04-12 ning darvozasini eskirtirgan edi.
"""

MIN_ENV_KEYS: Final = 40
"""Parser `environment` bloklarini haqiqatan o'qiyotganining quyi chegarasi."""

_ENTRYPOINT = re.compile(r"^[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*:[A-Za-z_]\w*$")
"""`modul:atribut` shakli — `app.main:app`, `app.worker:broker`, `app.worker:scheduler`.

⚠ `$` BILAN BOSHLANADIGAN TOKEN TUSHMAYDI: `core-api` ning buyrug'ida
  `${FORWARDED_ALLOW_IPS:-172.16.0.0/12}` bor va u ham ikki nuqta tashiydi.
  Naqsh identifikatordan boshlanishni talab qiladi, ya'ni compose
  o'zgaruvchisi kirish nuqtasi bo'lib ko'rinmaydi (o'lchandi).
"""


class _Service(NamedTuple):
    """`compose.yaml` dagi bitta servisning darvozaga kerak bo'lgan qismi."""

    name: str
    environment: tuple[str, ...]
    command: tuple[str, ...]
    command_style: str | None


def _strip_full_line_comments(text: str) -> list[str]:
    """FAQAT butun-qator izohlar tashlanadi (`test_compose_sim_env.py` qoidasi).

    Qator OXIRIDAGI izoh QOLDIRILADI: uni kesish uchun `#` ni satr ichida
    izlash kerak bo'lardi va u YAML qiymatidagi `#` ni ham kesib yuborardi.
    """
    return [line for line in text.splitlines() if not line.lstrip().startswith("#")]


def _unquote(token: str) -> str:
    token = token.strip()
    if len(token) >= 2 and token[0] == token[-1] and token[0] in {'"', "'"}:
        return token[1:-1]
    return token


def _flow_tokens(value: str) -> tuple[str, ...]:
    """Bir qatorli `["taskiq", "worker", "app.worker:broker"]` -> tokenlar."""
    inner = value.strip()
    if inner.startswith("["):
        inner = inner[1:]
    if inner.endswith("]"):
        inner = inner[:-1]
    return tuple(_unquote(part) for part in inner.split(",") if part.strip())


def _compose_services() -> dict[str, _Service]:
    """`compose.yaml` -> servis nomi bo'yicha `environment` kalitlari va `command` tokenlari.

    IKKALA `command` SHAKLI HAM QO'LLAB-QUVVATLANADI VA IKKALASI HAM
    `compose.yaml` DA MAVJUD:

        core-api            worker / scheduler
        --------            ------------------
        command:            command: ["taskiq", "worker", "app.worker:broker", ...]
          - "uvicorn"
          - "app.main:app"

    ⚠ FAQAT BITTA SHAKLNI QO'LLAB-QUVVATLASH DARVOZANI JIMGINA BO'SHATARDI:
      ikkinchi shakldagi servis uchun `command` bo'sh bo'lib qolardi va (b)
      bosqichi «kirish nuqtasi topilmadi» deb yiqilardi — ya'ni nosozlik
      KO'RINARDI, lekin sababi noto'g'ri bo'lardi. Shuning uchun ikkala
      shakl ham `test_compose_parser_reads_both_command_shapes` da
      alohida o'lchanadi.
    """
    lines = _strip_full_line_comments(COMPOSE.read_text(encoding="utf-8"))

    services: dict[str, _Service] = {}
    current: str | None = None
    section: str | None = None
    in_services = False

    for line in lines:
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        stripped = line.strip()

        if indent == 0:
            in_services = line.startswith("services:")
            current = None
            section = None
            continue
        if not in_services:
            continue

        if indent == 2 and stripped.endswith(":"):
            current = stripped[:-1]
            services[current] = _Service(current, (), (), None)
            section = None
            continue
        if current is None:
            continue

        if indent == 4:
            key, _, value = stripped.partition(":")
            section = key.strip()
            if section == "command" and value.strip():
                services[current] = services[current]._replace(
                    command=_flow_tokens(value), command_style="flow"
                )
                section = None
            continue

        if section == "command" and stripped.startswith("- "):
            entry = services[current]
            services[current] = entry._replace(
                command=(*entry.command, _unquote(stripped[2:])), command_style="block"
            )
            continue

        if section == "environment" and indent == 6:
            env_key = stripped.partition(":")[0].strip()
            if env_key:
                entry = services[current]
                services[current] = entry._replace(environment=(*entry.environment, env_key))

    return services


@pytest.fixture(scope="module")
def compose_services() -> dict[str, _Service]:
    assert COMPOSE.is_file(), f"`{COMPOSE}` topilmadi — yo'l eskirgan"
    return _compose_services()


@pytest.fixture(scope="module")
def sentry_services(compose_services: dict[str, _Service]) -> tuple[_Service, ...]:
    """(a) BOSQICHI — `SENTRY_DSN` va'da qilingan HAR bir jarayon."""
    return tuple(
        service for service in compose_services.values() if SENTRY_ENV_KEY in service.environment
    )


# ---------------------------------------------------------------------------
# Parserning O'ZI — quyi chegaralar va IKKALA `command` shakli
# ---------------------------------------------------------------------------


def test_compose_parser_reads_both_command_shapes(compose_services: dict[str, _Service]) -> None:
    """QUYI CHEGARA: buzilgan parser ustida quyidagi darvozalar hech nimani o'lchamasdi.

    ⚠ NAZORATLAR SERVIS NOMI BO'YICHA EMAS, SHAKL BO'YICHA yozilgan: nom
      ro'yxati aynan shu darvozani 04-12 da eskirtirgan naqsh edi.
    """
    assert len(compose_services) >= MIN_COMPOSE_SERVICES, (
        f"`compose.yaml` dan faqat {len(compose_services)} servis topildi "
        f"({sorted(compose_services)}), kamida {MIN_COMPOSE_SERVICES} kutilgan — "
        "parser bo'sh to'plamda ishlayapti va quyidagi da'volar isbotsiz qolardi"
    )

    styles = {service.command_style for service in compose_services.values()}
    assert "flow" in styles, (
        'bir qatorli (`command: ["..."]`) buyruq UMUMAN parse qilinmadi — '
        "`worker`/`scheduler` shakli ko'rinmayapti"
    )
    assert "block" in styles, (
        'blok ro\'yxatli (`command:` + `- "..."`) buyruq UMUMAN parse qilinmadi — '
        "`core-api` shakli ko'rinmayapti"
    )

    total_env_keys = sum(len(service.environment) for service in compose_services.values())
    assert total_env_keys >= MIN_ENV_KEYS, (
        f"`environment` bloklaridan jami {total_env_keys} kalit topildi, kamida "
        f"{MIN_ENV_KEYS} kutilgan — parser env bloklarini ko'rmayapti, ya'ni "
        f"`{SENTRY_ENV_KEY}` bo'yicha filtr BO'SH to'plam qaytarardi"
    )


# ---------------------------------------------------------------------------
# (a) + (b) + (c) — HOSILA DARVOZA
# ---------------------------------------------------------------------------


def test_every_sentry_process_is_found(sentry_services: tuple[_Service, ...]) -> None:
    """(a) BOSQICHI: `SENTRY_DSN` oladigan jarayonlar topildi va ular kamida uchta."""
    assert len(sentry_services) >= MIN_SENTRY_SERVICES, (
        f"`{SENTRY_ENV_KEY}` faqat {len(sentry_services)} servisga berilyapti "
        f"({[service.name for service in sentry_services]}), kamida "
        f"{MIN_SENTRY_SERVICES} kutilgan. Kuzatuv va'da qilingan jarayon "
        "`compose.yaml` dan yo'qolgan bo'lsa sabab O'SHA faylda"
    )


def _entrypoint_of(service: _Service) -> tuple[str, str]:
    """(b) BOSQICHI: buyruq tokenlaridan AYNAN BITTA `modul:atribut` chiqariladi.

    ⛔ TOPILMASA `pytest.fail` — VA AYNAN SHU YOLG'IZ SATR DARVOZANI
       «HOSILA» QILADI. To'rtinchi jarayon boshqa shakldagi buyruq bilan
       qo'shilsa (masalan `["python", "-m", "app.something"]`) darvoza uni
       JIMGINA o'tkazib yubormaydi — u yiqiladi va sabab xabarda yoziladi.
    """
    matches = [token for token in service.command if _ENTRYPOINT.match(token)]
    if len(matches) != 1:
        pytest.fail(
            f"`{service.name}` servisi `{SENTRY_ENV_KEY}` ni oladi, lekin darvoza uning "
            f"kirish nuqtasini `command` dan chiqara olmadi: `modul:atribut` shaklidagi "
            f"{len(matches)} ta token topildi ({matches}), AYNAN BITTA kutilgan.\n"
            f"  command = {list(service.command)}\n"
            "Bu servis bizning kodimizni boshqa shaklda yuritayotgan bo'lsa, "
            "darvozani (b) bosqichida kengaytiring — TESTNI O'CHIRMANG: aynan "
            "«jimgina o'tkazib yuborish» 04-12 ning darvozasini uchinchi jarayonda "
            "bo'shatgan edi."
        )
    module_name, _, attribute = matches[0].partition(":")
    return module_name, attribute


def _lifespan_sources(app: FastAPI) -> list[str]:
    """FastAPI ning `lifespan_context` zanjiridagi HAMMA manba matni.

    =========================================================================
    ⚠⚠ O'LCHANGAN, TAXMIN QILINMAGAN (04-13, `tests` konteynerida):

        inspect.getsource(app.router.lifespan_context)
            -> fastapi.routing._merge_lifespan_context.<locals>.merged_lifespan
        getattr(ctx, "__wrapped__", ctx)
            -> YANA O'SHA `merged_lifespan` (boshqa nusxa)

    Ikkalasida ham `init_sentry(` YO'Q. Sabab: FastAPI har `include_router`
    da ilovaning `lifespan` ini router lifespan'i bilan QO'SHADI
    (`_merge_lifespan_context`), ya'ni bizning `lifespan` o'nlab qobiq
    ostida, closure hujayralarida yotadi. O'lchov: 8 va 40 chuqurlikda
    topilmadi, closure zanjirini OXIRIGACHA yurganda `app.main.lifespan`
    topildi.

    Shuning uchun bu yerda chuqurlik CHEGARASI YO'Q — takrorlanishni `seen`
    to'plami to'xtatadi (zanjir chekli).
    =========================================================================
    """
    collected: list[str] = []
    seen: set[int] = set()

    def walk(obj: object) -> None:
        if id(obj) in seen or not callable(obj):
            return
        seen.add(id(obj))
        candidates = [obj]
        unwrapped = inspect.unwrap(obj)
        if unwrapped is not obj:
            candidates.append(unwrapped)
        for candidate in candidates:
            # Manbasi yo'q obyekt (C-darajasidagi chaqiriluvchi, `functools.partial`)
            # zanjirning QONUNIY bo'g'ini — u tashlab yuboriladi, yurish davom etadi.
            with suppress(OSError, TypeError):
                collected.append(inspect.getsource(candidate))
            for cell in getattr(candidate, "__closure__", None) or ():
                with suppress(ValueError):  # bo'sh hujayra
                    walk(cell.cell_contents)

    walk(app.router.lifespan_context)
    return collected


def _handler_sources(broker: AsyncBroker, event: TaskiqEvents) -> list[str]:
    return [inspect.getsource(handler) for handler in broker.event_handlers[event]]


def test_every_sentry_process_installs_sentry(sentry_services: tuple[_Service, ...]) -> None:
    """(b) + (c): HAR bir `SENTRY_DSN` jarayoni O'Z reyestrida `init_sentry()` ni talab qiladi.

    ⚠ REYESTR OBYEKT TURIGA QARAB TANLANADI, chunki hodisa tanlovi
      taskiq NING O'ZINIKI (`test_taskiq_still_picks_the_event_by_process`
      uni vendor manbasidan qulflaydi):

        FastAPI          -> `lifespan_context` zanjiri
        AsyncBroker      -> `event_handlers[WORKER_STARTUP]`  (`taskiq worker`)
        TaskiqScheduler  -> `broker.event_handlers[CLIENT_STARTUP]` (`taskiq scheduler`)

    ⛔ BOSHQA TUR -> `pytest.fail`. «Bilmadim, o'tkazib yuboraman» yo'li
       aynan shu darvozaning oldingi nusxasini bo'shatgan edi.
    """
    for service in sentry_services:
        module_name, attribute = _entrypoint_of(service)
        module = importlib.import_module(module_name)
        target = getattr(module, attribute)
        label = f"`{service.name}` (`{module_name}:{attribute}`)"

        if isinstance(target, FastAPI):
            sources = _lifespan_sources(target)
            assert sources, (
                f"{label}: `lifespan_context` zanjiridan birorta manba o'qilmadi — "
                "yuruvchi buzilgan va quyidagi da'vo hech nimani o'lchamasdi"
            )
            found = any(INIT_MARKER in source for source in sources)
        elif isinstance(target, TaskiqScheduler):
            found = any(
                INIT_MARKER in source
                for source in _handler_sources(target.broker, TaskiqEvents.CLIENT_STARTUP)
            )
        elif isinstance(target, AsyncBroker):
            found = any(
                INIT_MARKER in source
                for source in _handler_sources(target, TaskiqEvents.WORKER_STARTUP)
            )
        else:
            pytest.fail(
                f"{label}: obyektning turi ({type(target).__name__}) darvozaga noma'lum, "
                "ya'ni «bu jarayonda Sentry o'rnatiladimi?» savoliga javob berib "
                "bo'lmaydi. Yangi tur uchun (c) bosqichiga shox qo'shing."
            )

        assert found, (
            f"{label}: `{SENTRY_ENV_KEY}` konteynerga BERILADI, lekin o'sha jarayonning "
            f"o'z reyestrida `{INIT_MARKER}` chaqiruvi YO'Q — bu «jimgina yolg'on» "
            "sinfi: konteyner sog'lom, jurnal toza, hodisa esa hech qachon "
            "jo'natilmaydi (04-VERIFICATION.md)"
        )


# ---------------------------------------------------------------------------
# VENDOR QULFI — tur -> hodisa xaritasi taskiq NING tanlovi
# ---------------------------------------------------------------------------


def test_taskiq_still_picks_the_event_by_process() -> None:
    """Yuqoridagi tur->hodisa xaritasi taskiq manbasidan QULFLANADI.

    ⚠ USIZ DARVOZA JIMGINA ESKIRARDI: taskiq bir kun `is_scheduler_process`
      uchun ham `WORKER_STARTUP` ni ateshlay boshlasa (yoki bayroqni birga
      qo'shsa), bizning `CLIENT_STARTUP` ilmog'imiz ikki marta ishlardi
      yoki umuman ishlamasdi — va yuqoridagi test baribir yashil qolardi,
      chunki u faqat REYESTRNI o'qiydi.

    Bu test taskiq o'zgarganda QIZARADI va sabab test nomida yoziladi.
    """
    startup = inspect.getsource(_AsyncBrokerImpl.startup)
    for marker in ("is_worker_process", "CLIENT_STARTUP", "WORKER_STARTUP"):
        assert marker in startup, (
            f"`AsyncBroker.startup` manbasida `{marker}` yo'q — taskiq hodisa tanlash "
            "mexanizmini o'zgartirgan; `app/worker.py` dagi ikki ilmoqning taqsimoti "
            "qayta o'lchanishi SHART"
        )

    assert "is_scheduler_process" in inspect.getsource(run_scheduler), (
        "`taskiq.cli.scheduler.run.run_scheduler` endi `is_scheduler_process` ni "
        "o'rnatmayapti — planer jarayonining bayrog'i o'zgargan, ya'ni qaysi hodisa "
        "ateshlanishi ham o'zgargan bo'lishi mumkin"
    )
