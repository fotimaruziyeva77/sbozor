"""Sentry darvozasi — `cv-service` uchun OBYEKT darajasida, SHU image ichida.

=============================================================================
NEGA BU DARVOZA ROOT `tests/unit/test_sentry_processes.py` DAN TASHQARIDA.

Root darvoza `compose.yaml` dan HOSILA va u to'g'ri ishlaydi — lekin u
`tests` konteynerida, ya'ni `core-api` image'ida yuradi. U yerda
`services/cv-service` `pythonpath` da YO'Q va paket nomi (`app`)
`core-api` niki bilan TO'QNASHADI: `importlib.import_module("app.worker")`
JIMGINA `core-api` ning modulini qaytarardi.

Shuning uchun root darvoza begona kod bazasi uchun MANBA darajasiga
tushadi (fayl bor, atribut bor, ilmoq bor, `init_sentry(` bor), va
OBYEKT darajasidagi to'liq o'lchov — aynan shu fayl. Ikkalasi bir-birining
o'rnini BOSMAYDI:

    root  -> «compose `SENTRY_DSN` bergan HAR jarayon qamralganmi?»
    bu    -> «o'sha jarayonning REYESTRIDA `init_sentry(` haqiqatan bormi?»

=============================================================================
⚠ SERVIS NOMLARI BU YERDA HAM RO'YXAT SIFATIDA YOZILMAGAN (§S-10).

Darvoza `compose.yaml` dan shu image'ga TEGISHLI servislarni
`build.dockerfile` bo'yicha tanlaydi. Ya'ni `cv-service` yoniga ikkinchi
konteyner qo'shilgan kuni (masalan alohida `cv-api`) u AVTOMATIK ravishda
shu talab ostiga tushadi.
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

REPO_ROOT: Final = Path(__file__).resolve().parents[4]
COMPOSE: Final = REPO_ROOT / "compose.yaml"
SERVICE_DOCKERFILE: Final = "services/cv-service/Dockerfile"

SENTRY_ENV_KEY: Final = "SENTRY_DSN"
INIT_MARKER: Final = "init_sentry("
"""`sentry_sdk.init(` EMAS: `init_sentry()` — `before_send`/`before_breadcrumb`
bilan birga o'rnatiladigan YAGONA yo'l (`app/observability.py`)."""

MIN_COMPOSE_SERVICES: Final = 8
"""Parser buzilganda darvoza JIMGINA yashil bo'lardi (`test_storage_config.py` qoidasi)."""

_ENTRYPOINT: Final = re.compile(r"^[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*:[A-Za-z_]\w*$")


class _Service(NamedTuple):
    name: str
    environment: tuple[str, ...]
    command: tuple[str, ...]
    dockerfile: str | None


def _unquote(token: str) -> str:
    token = token.strip()
    if len(token) >= 2 and token[0] == token[-1] and token[0] in {'"', "'"}:
        return token[1:-1]
    return token


def _flow_tokens(value: str) -> tuple[str, ...]:
    inner = value.strip().removeprefix("[").removesuffix("]")
    return tuple(_unquote(part) for part in inner.split(",") if part.strip())


def _compose_services() -> dict[str, _Service]:
    """`compose.yaml` -> servis nomi bo'yicha `environment`, `command`, `build.dockerfile`.

    ⚠ `PyYAML` BU LOYIHANING BOG'LIQLIGI EMAS va u faqat shu test uchun
      qo'shilmaydi (`test_sentry_processes.py:34-41` qoidasi). Fayl matn
      sifatida o'qiladi va parserning o'zi quyi chegara bilan qo'riqlanadi.
    """
    lines = [
        line
        for line in COMPOSE.read_text(encoding="utf-8").splitlines()
        if not line.lstrip().startswith("#")
    ]

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
                services[current] = services[current]._replace(command=_flow_tokens(value))
                section = None
            continue

        if section == "command" and stripped.startswith("- "):
            entry = services[current]
            services[current] = entry._replace(command=(*entry.command, _unquote(stripped[2:])))
            continue

        if section == "build" and indent == 6:
            build_key, _, build_value = stripped.partition(":")
            if build_key.strip() == "dockerfile":
                entry = services[current]
                services[current] = entry._replace(dockerfile=_unquote(build_value))
            continue

        if section == "environment" and indent == 6:
            env_key = stripped.partition(":")[0].strip()
            if env_key:
                entry = services[current]
                services[current] = entry._replace(environment=(*entry.environment, env_key))

    return services


@pytest.fixture(scope="module")
def compose_services() -> dict[str, _Service]:
    assert COMPOSE.is_file(), (
        f"`{COMPOSE}` topilmadi — `cv-tests` konteyneri repo ildizini "
        "`/app` ga mount qiladi, ya'ni yo'l eskirgan bo'lishi mumkin"
    )
    services = _compose_services()
    assert len(services) >= MIN_COMPOSE_SERVICES, (
        f"`compose.yaml` dan faqat {len(services)} servis topildi — parser "
        "bo'sh to'plamda ishlayapti va quyidagi da'volar isbotsiz qolardi"
    )
    return services


@pytest.fixture(scope="module")
def cv_sentry_services(compose_services: dict[str, _Service]) -> tuple[_Service, ...]:
    """SHU image'dan quriladigan va `SENTRY_DSN` oladigan HAR bir servis."""
    return tuple(
        service
        for service in compose_services.values()
        if service.dockerfile == SERVICE_DOCKERFILE and SENTRY_ENV_KEY in service.environment
    )


def test_this_image_is_actually_represented_in_compose(
    compose_services: dict[str, _Service],
) -> None:
    """QUYI CHEGARA: `build.dockerfile` filtri hech nimani tanlamasa darvoza bo'sh bo'lardi.

    Bu servis compose'dan butunlay yo'qolsa (yoki Dockerfile yo'li
    o'zgarsa), quyidagi darvoza `cv_sentry_services` BO'SH bo'lgani uchun
    JIMGINA yashil qolardi — aynan o'sha «bo'sh to'plamdagi da'vo» sinfi.
    """
    from_this_image = [
        service.name
        for service in compose_services.values()
        if service.dockerfile == SERVICE_DOCKERFILE
    ]
    assert len(from_this_image) >= 2, (
        f"`{SERVICE_DOCKERFILE}` dan quriladigan servislar: {from_this_image}. "
        "Kamida ikkitasi kutilgan (`cv-service` va `cv-tests`) — filtr hech "
        "nimani tanlamasa quyidagi darvoza bo'sh to'plamda ishlardi."
    )


def test_test_container_is_not_promised_sentry(compose_services: dict[str, _Service]) -> None:
    """`cv-tests` `SENTRY_DSN` OLMAYDI — test jarayoni ishlab chiqarish kuzatuvi emas.

    Teskari yo'nalish ham qulflanadi: kalit tasodifan qo'yilsa, root
    darvoza test konteyneri uchun ham `init_sentry()` talab qilardi va
    yechim sifatida uni `pytest` ga o'rnatish taklif qilinardi — ya'ni
    CI xatolari mijozning Sentry loyihasiga oqib tushardi.
    """
    tests_service = compose_services.get("cv-tests")
    assert tests_service is not None, "`cv-tests` servisi `compose.yaml` da topilmadi"
    assert SENTRY_ENV_KEY not in tests_service.environment, (
        f"`cv-tests` ga `{SENTRY_ENV_KEY}` berilgan — test jarayonining "
        "istisnolari ishlab chiqarish Sentry loyihasiga tushardi"
    )


def _entrypoint_of(service: _Service) -> tuple[str, str]:
    """`command` tokenlaridan AYNAN BITTA `modul:atribut` chiqariladi."""
    matches = [token for token in service.command if _ENTRYPOINT.match(token)]
    if len(matches) != 1:
        pytest.fail(
            f"`{service.name}` `{SENTRY_ENV_KEY}` ni oladi, lekin uning kirish "
            f"nuqtasi `command` dan chiqarilmadi: {len(matches)} ta mos token "
            f"({matches}), AYNAN BITTA kutilgan.\n  command = {list(service.command)}"
        )
    module_name, _, attribute = matches[0].partition(":")
    return module_name, attribute


def _lifespan_sources(app: FastAPI) -> list[str]:
    """FastAPI ning `lifespan_context` zanjiridagi HAMMA manba matni.

    ⚠ CHUQURLIK CHEGARASI YO'Q — 04-13 da o'lchangan sabab: FastAPI har
      `include_router` da lifespan'ni QO'SHADI (`_merge_lifespan_context`),
      ya'ni bizning funksiyamiz closure hujayralarida yotadi. Takrorlanishni
      `seen` to'plami to'xtatadi (zanjir chekli).
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
            with suppress(OSError, TypeError):
                collected.append(inspect.getsource(candidate))
            for cell in getattr(candidate, "__closure__", None) or ():
                with suppress(ValueError):
                    walk(cell.cell_contents)

    walk(app.router.lifespan_context)
    return collected


def _handler_sources(broker: AsyncBroker, event: TaskiqEvents) -> list[str]:
    return [inspect.getsource(handler) for handler in broker.event_handlers[event]]


def test_every_cv_sentry_process_installs_sentry(cv_sentry_services: tuple[_Service, ...]) -> None:
    """HAR bir `SENTRY_DSN` jarayoni O'Z reyestrida `init_sentry()` ni talab qiladi.

    ⚠ REYESTR OBYEKT TURIGA QARAB TANLANADI, chunki hodisa tanlovi
      taskiq NING O'ZINIKI:

        FastAPI          -> `lifespan_context` zanjiri
        AsyncBroker      -> `event_handlers[WORKER_STARTUP]`  (`taskiq worker`)
        TaskiqScheduler  -> `broker.event_handlers[CLIENT_STARTUP]`

    ⛔ BOSHQA TUR -> `pytest.fail`. «Bilmadim, o'tkazib yuboraman» yo'li
       04-12 ning darvozasini uchinchi jarayonda bo'shatgan edi.
    """
    assert cv_sentry_services, (
        "shu image'dan quriladigan birorta servis `SENTRY_DSN` olmaydi — "
        "ishlab chiqarish jarayoni kuzatuvsiz qolgan bo'lishi mumkin"
    )

    for service in cv_sentry_services:
        module_name, attribute = _entrypoint_of(service)
        module = importlib.import_module(module_name)
        target = getattr(module, attribute)
        label = f"`{service.name}` (`{module_name}:{attribute}`)"

        if isinstance(target, FastAPI):
            sources = _lifespan_sources(target)
            assert sources, f"{label}: `lifespan_context` zanjiridan manba o'qilmadi"
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
                f"{label}: obyektning turi ({type(target).__name__}) darvozaga noma'lum — "
                "yangi tur uchun shox qo'shing, TESTNI O'CHIRMANG"
            )

        assert found, (
            f"{label}: `{SENTRY_ENV_KEY}` konteynerga BERILADI, lekin o'sha "
            f"jarayonning reyestrida `{INIT_MARKER}` chaqiruvi YO'Q — konteyner "
            "sog'lom, jurnal toza, hodisa esa hech qachon jo'natilmaydi"
        )


def test_health_surface_also_installs_sentry() -> None:
    """`app/main.py` — bugun KONTEYNERSIZ, lekin SINALMAGAN kod EMAS.

    ⚠ NEGA ALOHIDA TEST: yuqoridagi darvoza `compose.yaml` dan hosila, ya'ni
      u faqat KONTEYNERGA CHIQARILGAN jarayonni ko'radi. `app/main.py` esa
      bugun birorta konteynerda yuritilmaydi (sabab o'sha faylning
      docstringida: worker uchun soxta healthcheck qo'yilmaydi). Usiz bu
      modul jimgina buzilib turishi mumkin edi va buni faqat uni
      konteynerga chiqargan kun bilinardi.
    """
    from app.main import app as health_app

    sources = _lifespan_sources(health_app)
    assert sources, "`app.main:app` ning `lifespan_context` zanjiridan manba o'qilmadi"
    assert any(INIT_MARKER in source for source in sources), (
        f"`app.main:app` ning `lifespan` ida `{INIT_MARKER}` chaqiruvi yo'q"
    )
