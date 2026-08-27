"""Sentry darvozasi — `bot-service` uchun OBYEKT darajasida, SHU image ichida.

=============================================================================
NEGA BU DARVOZA ROOT `tests/unit/test_sentry_processes.py` DAN TASHQARIDA.

Root darvoza `compose.yaml` dan HOSILA va u to'g'ri ishlaydi — lekin u
`tests` konteynerida, ya'ni `core-api` image'ida yuradi. U yerda
`services/bot-service` `pythonpath` da YO'Q, paket nomi (`app`) esa
`core-api` niki bilan TO'QNASHADI, va eng muhimi: `aiogram` o'sha muhitda
UMUMAN O'RNATILMAGAN (u `core-api` da ATAYIN taqiqlangan —
`tests/unit/test_runtime_deps.py`). Ya'ni root darvoza bu modulni
import qila OLMAYDI.

Shuning uchun root darvoza begona kod bazasi uchun MANBA darajasiga
tushadi (fayl bor, atribut bor, ilmoq bor, `init_sentry(` bor), va
REYESTR darajasidagi to'liq o'lchov — aynan shu fayl. Ikkalasi
bir-birining o'rnini BOSMAYDI:

    root  -> «compose `SENTRY_DSN` bergan HAR jarayon qamralganmi?»
    bu    -> «o'sha jarayonning REYESTRIDA `init_sentry(` haqiqatan bormi?»

⚠ FARQ AMALIY: root darvoza faylda YOZILGANINI ko'radi. `dp.startup.
  register(_on_startup)` satri o'chirilib, funksiya joyida qolsa — root
  darvoza `dp.startup.register` markerini topmay qizarardi, LEKIN agar
  marker boshqa (o'lik) satrda qolsa u YASHIL bo'lardi. Bu fayl esa
  observerning HAQIQIY ro'yxatiga qaraydi.

=============================================================================
⚠ SERVIS NOMLARI BU YERDA HAM RO'YXAT SIFATIDA YOZILMAGAN (§S-10).

Darvoza `compose.yaml` dan shu image'ga TEGISHLI servislarni
`build.dockerfile` bo'yicha tanlaydi.
=============================================================================
"""

from __future__ import annotations

import inspect
import re
from collections.abc import Callable
from pathlib import Path
from typing import Final, NamedTuple

import pytest

REPO_ROOT: Final = Path(__file__).resolve().parents[4]
COMPOSE: Final = REPO_ROOT / "compose.yaml"
SERVICE_DOCKERFILE: Final = "services/bot-service/Dockerfile"

SENTRY_ENV_KEY: Final = "SENTRY_DSN"
INIT_MARKER: Final = "init_sentry("
"""`sentry_sdk.init(` EMAS: `init_sentry()` — `before_send`/`before_breadcrumb`
bilan birga o'rnatiladigan YAGONA yo'l (`app/observability.py`)."""

MODULE_RUN_ATTRIBUTE: Final = "main"
"""`python -m <modul>` shaklidagi jarayonning kutilgan modul atributi.

Root darvozadagi AYNI NOMLI konstanta bilan bir xil qiymat va bir xil
sabab: `aiogram` `modul:atribut` argumentini qabul qilmaydi, ya'ni
`command` dan atribut CHIQARIB BO'LMAYDI va u kelishuv bilan belgilanadi.
"""

MIN_COMPOSE_SERVICES: Final = 8
"""Parser buzilganda darvoza JIMGINA yashil bo'lardi (`test_storage_config.py` qoidasi)."""

_ENTRYPOINT: Final = re.compile(r"^[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*:[A-Za-z_]\w*$")
_MODULE_NAME: Final = re.compile(r"^[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*$")


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
      qo'shilmaydi (`test_sentry_processes.py` qoidasi). Fayl matn
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
        f"`{COMPOSE}` topilmadi — `bot-tests` konteyneri repo ildizini "
        "`/app` ga mount qiladi, ya'ni yo'l eskirgan bo'lishi mumkin"
    )
    services = _compose_services()
    assert len(services) >= MIN_COMPOSE_SERVICES, (
        f"`compose.yaml` dan faqat {len(services)} servis topildi — parser "
        "bo'sh to'plamda ishlayapti va quyidagi da'volar isbotsiz qolardi"
    )
    return services


@pytest.fixture(scope="module")
def bot_sentry_services(compose_services: dict[str, _Service]) -> tuple[_Service, ...]:
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
    o'zgarsa), quyidagi darvoza `bot_sentry_services` BO'SH bo'lgani uchun
    JIMGINA yashil qolardi — aynan o'sha «bo'sh to'plamdagi da'vo» sinfi.
    """
    from_this_image = [
        service.name
        for service in compose_services.values()
        if service.dockerfile == SERVICE_DOCKERFILE
    ]
    assert len(from_this_image) >= 2, (
        f"`{SERVICE_DOCKERFILE}` dan quriladigan servislar: {from_this_image}. "
        "Kamida ikkitasi kutilgan (ishlab chiqarish jarayoni va uning test "
        "konteyneri) — filtr hech nimani tanlamasa quyidagi darvoza bo'sh "
        "to'plamda ishlardi."
    )


def test_test_container_is_not_promised_sentry(compose_services: dict[str, _Service]) -> None:
    """Test konteyneri `SENTRY_DSN` OLMAYDI — test jarayoni ishlab chiqarish kuzatuvi emas.

    Teskari yo'nalish ham qulflanadi: kalit tasodifan qo'yilsa, root
    darvoza test konteyneri uchun ham `init_sentry()` talab qilardi va
    yechim sifatida uni `pytest` ga o'rnatish taklif qilinardi — ya'ni
    CI xatolari mijozning Sentry loyihasiga oqib tushardi.

    ⚠ SERVIS NOMI BO'YICHA EMAS, SHAKL BO'YICHA: shu image'dan quriladigan
      va `dev` targetni ishlatadigan servis TEST konteyneridir.
    """
    offenders = [
        service.name
        for service in compose_services.values()
        if service.dockerfile == SERVICE_DOCKERFILE
        and service.command
        and service.command[0] == "pytest"
        and SENTRY_ENV_KEY in service.environment
    ]
    assert not offenders, (
        f"test konteyneriga `{SENTRY_ENV_KEY}` berilgan: {offenders} — test "
        "jarayonining istisnolari ishlab chiqarish Sentry loyihasiga tushardi"
    )


def _entrypoint_of(service: _Service) -> tuple[str, str]:
    """`command` dan kirish nuqtasi — root darvoza bilan AYNAN BIR XIL ikki shakl."""
    colon_matches = [token for token in service.command if _ENTRYPOINT.match(token)]
    if len(colon_matches) == 1:
        module_name, _, attribute = colon_matches[0].partition(":")
        return module_name, attribute

    module_matches = [
        nxt
        for flag, nxt in zip(service.command, service.command[1:], strict=False)
        if flag == "-m" and _MODULE_NAME.match(nxt)
    ]
    if not colon_matches and len(module_matches) == 1:
        return module_matches[0], MODULE_RUN_ATTRIBUTE

    pytest.fail(
        f"`{service.name}` `{SENTRY_ENV_KEY}` ni oladi, lekin uning kirish nuqtasi "
        f"`command` dan chiqarilmadi: `modul:atribut` {colon_matches}, `-m <modul>` "
        f"{module_matches}.\n  command = {list(service.command)}"
    )


def _startup_callbacks() -> list[Callable[..., object]]:
    """`dp.startup` observeriga RO'YXATGA OLINGAN callback'lar.

    =========================================================================
    ⚠⚠ REYESTR SHAKLI VENDORNIKI VA U O'LCHANGAN (2026-08-12, `bot-tests`):

        dp.startup.handlers
            -> [HandlerObject(callback=<function _on_startup>, awaitable=True, ...)]

    Ya'ni ro'yxatdagi element FUNKSIYANING O'ZI EMAS, uni o'ragan obyekt.
    `inspect.getsource()` ni to'g'ridan-to'g'ri o'ragichga qo'llash aiogram
    ning O'Z manbasini qaytarardi va darvoza BIZNING kodimizni umuman
    ko'rmasdi — u «`init_sentry(` yo'q» deb qizarardi va sabab noto'g'ri
    o'qilardi.

    `getattr(..., "callback", ...)` ATAYIN: aiogram o'ragich sinfini
    o'zgartirsa (yoki olib tashlasa), darvoza ikkala shaklda ham ishlaydi.
    =========================================================================
    """
    from app.main import dp

    callbacks: list[Callable[..., object]] = []
    for handler in dp.startup.handlers:
        candidate = getattr(handler, "callback", handler)
        assert callable(candidate), (
            f"`dp.startup` reyestridagi element chaqiriluvchi emas: {candidate!r} "
            f"({type(candidate).__name__}). aiogram o'ragich sinfini o'zgartirgan "
            "bo'lsa, yuqoridagi `getattr(..., 'callback', ...)` qayta o'lchansin."
        )
        callbacks.append(candidate)
    return callbacks


def test_startup_registry_installs_sentry(bot_sentry_services: tuple[_Service, ...]) -> None:
    """HAR bir `SENTRY_DSN` jarayoni O'Z reyestrida `init_sentry()` ni talab qiladi.

    ⛔ Bu MANBA emas, REYESTR darajasi: ilmoqning haqiqatan ro'yxatga
       tushgani o'lchanadi. Root darvoza faqat matnni ko'radi va bu farq
       IKKALA faylda ham yozilgan.
    """
    assert bot_sentry_services, (
        "shu image'dan quriladigan birorta servis `SENTRY_DSN` olmaydi — "
        "ishlab chiqarish jarayoni kuzatuvsiz qolgan bo'lishi mumkin"
    )

    callbacks = _startup_callbacks()
    assert callbacks, (
        "`dp.startup` reyestri BO'SH — `dp.startup.register(...)` chaqirilmagan "
        "yoki modul darajasidan olib tashlangan. `init_sentry(` chaqiruvi faylda "
        "TURGAN bo'lsa ham u HECH QACHON ishga tushmasdi (aynan «jimgina yolg'on» "
        "sinfi: konteyner sog'lom, jurnal toza, hodisa jo'natilmaydi)."
    )

    sources = [inspect.getsource(callback) for callback in callbacks]
    assert any(INIT_MARKER in source for source in sources), (
        f"`dp.startup` reyestridagi callback'larning BIRORTASIDA `{INIT_MARKER}` "
        f"chaqiruvi yo'q ({[getattr(cb, '__name__', repr(cb)) for cb in callbacks]}). "
        f"`{SENTRY_ENV_KEY}` konteynerga BERILADI, ya'ni kuzatuv VA'DA QILINGAN."
    )


def test_command_names_a_module_level_attribute(
    bot_sentry_services: tuple[_Service, ...],
) -> None:
    """`command` ko'rsatgan atribut MODUL DARAJASIDA mavjud va CHAQIRILUVCHI.

    ⚠ NEGA ALOHIDA TEST: root darvozaning (c) bosqichi bu shartni MANBA
      matnida (`^main\\s*[:=]`) tekshiradi, ya'ni u atribut haqiqatan
      chaqiriluvchi ekanini BILMAYDI. `main = "main"` deb yozilsa root
      darvoza YASHIL qolardi va konteyner ishga tushishda
      `TypeError: 'str' object is not callable` bilan yiqilardi.
    """
    import app.main as entrypoint_module

    for service in bot_sentry_services:
        module_name, attribute = _entrypoint_of(service)
        assert module_name == entrypoint_module.__name__, (
            f"`{service.name}` ning kirish nuqtasi `{module_name}`, bu test esa "
            f"`{entrypoint_module.__name__}` ni import qiladi — ikkisi ajralib "
            "ketgan, ya'ni test BOSHQA modulni o'lchayapti"
        )
        target = getattr(entrypoint_module, attribute, None)
        assert target is not None, (
            f"`{module_name}` da `{attribute}` atributi YO'Q — `python -m` uni "
            "import paytida topa olmasdi va konteyner ishga tushishda yiqilardi"
        )
        assert callable(target), (
            f"`{module_name}:{attribute}` chaqiriluvchi EMAS ({type(target).__name__}) — "
            "`asyncio.run(main())` `TypeError` bilan yiqilardi. Root darvoza buni "
            "KO'RA OLMAYDI: u faqat `^main[:=]` matnini ko'radi."
        )
