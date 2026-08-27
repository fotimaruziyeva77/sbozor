"""DEV MUHITINING VA'DASI — `npm run up` VA `bot-tests` TOKENLARI (07-21).

=============================================================================
⛔⛔ BU FAYL IKKI NUQSONNI QULFLAYDI VA IKKALASI HAM «HUJJAT BOR, XULQ
   YO'Q» SINFIDAN.

  B-8 — `compose.yaml:601-605` OCHIQ DA'VO QILADI: «`bot-service`
        PROFILSIZ ... `npm run up` uni ham ko'taradi». `package.json` ning
        `scripts.up` satrida esa `bot-service` UMUMAN YO'Q edi. Ya'ni
        hujjatlashtirilgan buyruq fazaning MAHSULOTINI ishga tushirmasdi
        va bu HECH QANDAY xato bermasdi: sotuvchi botga yozardi, javob
        esa hech qachon kelmasdi.

  B-9 — o'sha faylning 706-719-qatorlaridagi izoh «QIYMAT SIR EMAS,
        USKUNA» deydi, lekin qiymat `${TELEGRAM_BOT_TOKEN:-...}` shaklida
        yozilgan edi. `:-` STANDART emas, MAJBURLASH: u faqat
        o'zgaruvchi BO'SH bo'lganda ishlaydi, ya'ni ishlaydigan har
        qanday `.env` da test konteyneriga PROD tokeni oqib o'tardi.

=============================================================================
⛔ NAZORAT BANDI (3-test) USIZ 2-TEST BO'SH-ROST BO'LARDI.

«`bot-tests` da `${` yo'q» da'vosi butun compose faylida indirektsiya
o'chirilganda ham yashil bo'lardi — va o'shanda mahsulot bloki tokenni
muhitdan OLMAY qo'yardi, ya'ni bot umuman ishlamasdi. Shuning uchun
darvoza AYNAN AJRATILGANLIKNI o'lchaydi: test blokida `${` YO'Q, prod
blokida esa BOR.

=============================================================================
⚠ DOCKER TALAB QILINMAYDI: fayl `compose.yaml` va `package.json` ni
  MATN sifatida o'qiydi (`test_compose_sim_env.py` da o'rnatilgan naqsh).
  Konteyner ko'tarmaydigan darvoza har commitda yugurishi mumkin.

⚠ `yaml` YANGI BOG'LIQLIK EMAS: u `uvicorn[standard]` orqali
  `uv.lock` da ALLAQACHON qulflangan (`pyyaml 6.0.3`), ya'ni T-07-SC
  buzilmaydi — `pyproject.toml` diffda YO'Q. Uning YO'QOLISHI esa bu
  modulni `ImportError` bilan yiqitadi, ya'ni darvoza JIMGINA emas,
  BALAND o'ladi.
=============================================================================
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Final

# ⛔ `type: ignore` KODLI VA U SIR EMAS: `types-PyYAML` stublari
#   o'rnatilmagan va ularni qo'shish `pyproject.toml` ni diffga
#   olib kirardi — T-07-SC esa buni ATAYIN taqiqlaydi («yangi paket
#   YO'Q»). Ignore FAQAT stubning yo'qligini yopadi: quyidagi
#   `_compose()` natijani `isinstance(..., dict)` bilan TORAYTIRADI,
#   ya'ni `Any` chaqiruvchilarga tarqalmaydi.
import yaml  # type: ignore[import-untyped]

REPO_ROOT: Final = Path(__file__).resolve().parents[2]
COMPOSE: Final = REPO_ROOT / "compose.yaml"
PACKAGE_JSON: Final = REPO_ROOT / "package.json"

TOKEN_KEYS: Final[tuple[str, ...]] = ("TELEGRAM_BOT_TOKEN", "BOT_SERVICE_TOKEN")
"""Ikkala token ham bir xil qoidaga bo'ysunadi — biri yetmaydi.

`BOT_SERVICE_TOKEN` `TELEGRAM_BOT_TOKEN` dan KAM emas: u
`hmac.compare_digest` bilan solishtiriladigan servis-servis siri va u
bilan `/internal/bot/*` yuzasining HAMMASI ochiladi.
"""

INTERPOLATION: Final = "${"
"""Compose ning muhit-interpolyatsiyasi izi — `${X}` ham, `${X:-y}` ham."""

MIN_UP_SERVICES: Final = 5
"""`scripts.up` da kutiladigan eng kam servis — QUYI CHEGARA.

⚠ ANIQ SON EMAS: yangi servis qo'shilganda bu fayl TEGILMAYDI. Chegara
  faqat parser BUZILGANDA (masalan buyruq shakli o'zgarganda) qizaradi —
  usiz 1- va 4-testlar bo'sh ro'yxat ustida jimgina yashil bo'lardi.
"""

_FLAG_RE: Final = re.compile(r"^-")


def _compose() -> dict[str, Any]:
    """`compose.yaml` ning tahlil qilingan ko'rinishi.

    ⛔ `compose.override.yml` QO'SHILMAYDI: bu darvoza BAZA faylining
       mazmunini o'lchaydi va override faqat dev qulayligi (port
       bog'lash) uchun. Override ni ham birlashtirish `docker compose
       config` ni takrorlash bo'lardi — u esa Docker talab qilardi.
    """
    parsed = yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))
    assert isinstance(parsed, dict), "`compose.yaml` lug'at emas — parser buzilgan"
    return parsed


def _service_env(name: str) -> dict[str, Any]:
    services = _compose().get("services")
    assert isinstance(services, dict), "`services` bloki topilmadi"
    assert name in services, f"`{name}` servisi `compose.yaml` da yo'q: {sorted(services)}"
    env = services[name].get("environment")
    assert isinstance(env, dict), f"`{name}.environment` lug'at emas: {type(env)}"
    return env


def _up_services() -> list[str]:
    """`scripts.up` buyrug'idagi servis nomlari — bayroqlarsiz.

    `docker compose up -d <servislar...> --wait` shaklidan `-` bilan
    boshlanadigan bayroqlar va `docker`/`compose`/`up` so'zlari
    tashlanadi.
    """
    scripts = json.loads(PACKAGE_JSON.read_text(encoding="utf-8"))["scripts"]
    words = scripts["up"].split()
    skip = {"docker", "compose", "up"}
    return [word for word in words if word not in skip and not _FLAG_RE.match(word)]


# ---------------------------------------------------------------------------
# 1. `npm run up` fazaning mahsulotini ko'taradi (B-8)
# ---------------------------------------------------------------------------


def test_the_up_script_starts_the_bot_service() -> None:
    """⛔ B-8 — `compose.yaml` ning da'vosi endi ROST.

    O'sha blok ochiq yozadi: «PROFILSIZ ... `npm run up` uni ham
    ko'taradi». Profil ortiga yashirilgan (yoki ro'yxatdan tushib qolgan)
    bot HECH QANDAY xato bermasdi — sotuvchi yozardi, javob kelmasdi.

    ⚠ `--wait` `bot-service` uchun faqat «konteyner ishga tushdi» ni
      kutadi: `healthcheck` ATAYIN yo'q (long-poller HTTP yuzasi
      bermaydi) va bu KUTILGAN xulq, nuqson emas.
    """
    services = _up_services()
    assert len(services) >= MIN_UP_SERVICES, (
        f"`scripts.up` dan atigi {len(services)} servis o'qildi ({services}) — "
        "parser buzilgan va quyidagi da'volar bo'sh-rost bo'lib qolardi"
    )
    assert "bot-service" in services, (
        f"`npm run up` `bot-service` ni ko'tarmaydi: {services}. `compose.yaml` "
        "esa teskarisini DA'VO QILADI — hujjat bilan xulq ajralgan (B-8)"
    )


def test_every_service_named_by_the_up_script_exists_in_compose() -> None:
    """⛔ NOM O'ZGARSA DARVOZA QIZARADI — 1-testni bo'sh-rostdan saqlaydi.

    Usiz `scripts.up` ga xato yozilgan nom («bot_service») ham 1-testdan
    o'tib ketardi va `docker compose up` ishga tushishda «no such
    service» bilan yiqilardi — ya'ni nuqson CI'da emas, DEV MASHINASIDA
    ko'rinardi.
    """
    compose_services = _compose().get("services")
    assert isinstance(compose_services, dict)
    missing = sorted(set(_up_services()) - set(compose_services))
    assert missing == [], f"`scripts.up` `compose.yaml` da yo'q servis(lar)ni nomlaydi: {missing}"


# ---------------------------------------------------------------------------
# 2. `bot-tests` prod tokenini MEROS OLMAYDI (B-9)
# ---------------------------------------------------------------------------


def test_the_bot_test_container_cannot_inherit_a_production_token() -> None:
    """⛔⛔ B-9 — TEST KONTEYNERINING TOKENLARI MUHITDAN KELMAYDI.

    =========================================================================
    ⛔ `${X:-standart}` STANDART EMAS, MAJBURLASH: u faqat `X` BO'SH
       bo'lganda ishlaydi. Ishlaydigan dev mashinasida `.env` to'ldirilgan,
       ya'ni test konteyneri PROD Telegram tokenini va PROD servis
       tokenini olardi.

    Oqibat ikki tomonlama:
      * `app/main.py` `Bot(token=...)` ni MODUL DARAJASIDA quradi, ya'ni
        token `import app.main` bilan yuklanadi va tasodifiy tarmoq
        chaqirig'i prod botni `409 Conflict` bilan JIM qoldirishi mumkin
        edi (DQ-1);
      * CI chiqishida yoki xato izida ko'ringan qiymat PROD siri bo'lardi.

    ⚠ QIYMAT SHAKLI HAMON MUHIM: aiogram ning `validate_token()`
      `<raqamlar>:<sir>` shaklini talab qiladi va yaroqsiz standart bilan
      `import app.main` yozadigan HAR test yig'ilishda yiqilardi. Shuning
      uchun quyida shakl ham o'lchanadi.
    =========================================================================
    """
    env = _service_env("bot-tests")
    for key in TOKEN_KEYS:
        assert key in env, f"`bot-tests.environment` da `{key}` yo'q"
        value = str(env[key])
        assert INTERPOLATION not in value, (
            f"`bot-tests.{key}` muhitdan o'qiladi ({value!r}) — ishlaydigan `.env` "
            "da unga PROD tokeni tushardi (B-9)"
        )

    assert re.fullmatch(r"\d+:\S+", str(env["TELEGRAM_BOT_TOKEN"])), (
        "test tokeni aiogram ning `validate_token()` shakliga mos emas — "
        "`Bot(...)` konstruktori MODUL DARAJASIDA yiqilardi"
    )


def test_the_production_bot_block_still_reads_its_tokens_from_the_environment() -> None:
    """⛔⛔ NAZORAT BANDI — USIZ YUQORIDAGI TEST BO'SH-ROST BO'LARDI.

    «`${` yo'q» da'vosi butun compose faylida interpolyatsiya
    o'chirilganda ham yashil bo'lardi — va o'shanda `bot-service` tokenni
    muhitdan OLMAY qo'yardi, ya'ni mahsulot butunlay ishlamasdi va
    darvoza buni KO'RMASDI.

    Ya'ni bu juftlik «hamma joyda literal» ni emas, AYNAN test
    konteynerining AJRATILGANINI o'lchaydi.
    """
    env = _service_env("bot-service")
    for key in TOKEN_KEYS:
        assert key in env, f"`bot-service.environment` da `{key}` yo'q"
        assert INTERPOLATION in str(env[key]), (
            f"`bot-service.{key}` endi muhitdan o'qilmaydi ({env[key]!r}) — "
            "mahsulot bloki literal qiymat bilan qolgan va bot Telegram'ga "
            "umuman ulana olmasdi"
        )
