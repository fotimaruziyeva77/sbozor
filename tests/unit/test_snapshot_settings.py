"""4-fazaning sozlamalari — `Settings` va `.env.example` PARITETI (D-15, D-18).

=============================================================================
NEGA PARITET MEXANIK DARVOZA BO'LISHI SHART.

`Settings.model_config` da `extra="ignore"` turadi. Ya'ni `.env` ga
`RETENTION_PURGE_DAYS=1000` yozilsa pydantic uni JIMGINA TASHLAB YUBORADI:
xato yo'q, ogohlantirish yo'q, jurnalda hech nima yo'q. Operator sozlamani
«o'zgartirdim» deb hisoblaydi, tizim esa eski qiymat bilan ishlaydi.

Bu nosozlikning eng yomon shakli, chunki u HECH QANDAY signal bermaydi.
Yagona himoya — hujjat (`.env.example`) va kod (`Settings`) o'rtasidagi
ikki tomonlama tenglikni MASHINA tekshirishi.

Darvoza IKKI YO'NALISHDA ham ishlaydi:

  `.env.example` -> `Settings`  : hujjatda bor, kodda yo'q -> JIM NO-OP
  `Settings` -> `.env.example`  : kodda bor, hujjatda yo'q -> operator
                                  sozlamaning MAVJUDLIGINI bilmaydi

Ikkinchi yo'nalish bugun to'liq yopilmagan va bu ATAYIN NOMLANGAN:
`_ENV_EXAMPLE_TODO` reyestriga qarang.
=============================================================================
"""

from __future__ import annotations

import os
import re
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Final

import pytest
from app.services.quality import QUALITY_THRESHOLDS_VERSION, QualityThresholds
from app.settings import Settings, get_settings
from cryptography.fernet import Fernet
from pydantic import SecretStr, ValidationError
from sbozor_core.logging import CENSORED, censor_secrets

from unit.test_quality_filter import _SHIPPED

type BuildSettings = Callable[..., Settings]
"""`build` fixture'ining tipi — har testda takrorlanmasin."""

_ENV_EXAMPLE: Final = Path(__file__).resolve().parents[2] / ".env.example"

PHASE4_PREFIXES: Final[tuple[str, ...]] = (
    "S3_",
    "CAPTURE_",
    "RETENTION_",
    "QUALITY_",
    "SNAPSHOT_",
    "TELEGRAM_",
)
"""4-faza kiritgan kalitlarning prefikslari.

⚠ Prefiks bo'yicha filtrlash ATAYIN: `DATABASE_URL` yoki `JWT_SECRET` bu
  rejaning ishi emas va ularni paritetga qo'shish darvozani 1–3 fazalarning
  qarzlariga bog'lab qo'yardi.
"""

MIN_PHASE4_KEYS: Final[int] = 18
"""Topilishi SHART bo'lgan eng kam kalit soni — PARSERNING O'ZI uchun nazorat.

⚠ Usiz regex buzilganda (masalan `.env.example` formati o'zgarsa) parser
  BO'SH to'plam qaytarardi va «hamma kalit mos» degan tenglik JIMGINA rost
  bo'lardi. Bo'sh to'plamlar ustidagi tenglik — darvoza emas.
"""

_ENV_LINE = re.compile(r"^([A-Z][A-Z0-9_]*)=(.*)$")

_BASELINE: Final[dict[str, str]] = {
    "DATABASE_URL": "postgresql+asyncpg://sbozor_app:x@db:5432/sbozor",
    "VALKEY_URL": "redis://cache:6379/0",
    "JWT_SECRET": "x" * 48,
    "S3_ACCESS_KEY": "test-access-key",
    "S3_SECRET_KEY": "test-secret-key",
}
"""`Settings()` ning 4-fazadan TASHQARIDAGI majburiy maydonlari.

`NVR_CREDENTIAL_KEY` alohida beriladi — u Fernet formatida bo'lishi shart
va har chaqiruvda yangi hosil qilinadi (`test_nvr_secrets.py` bilan bir xil
qaror: qotirilgan kalit repozitoriyga tushgan sir bo'lardi).
"""

_ENV_EXAMPLE_TODO: Final[dict[str, str]] = {
    "S3_REGION": (
        "botocore `region_name` ni TALAB qiladi (SeaweedFS uni e'tiborsiz "
        "qoldiradi). Ombor klienti — 04-06 ning ishi va `.env.example` "
        "qatorini o'sha reja qo'shadi."
    ),
    "CAPTURE_LEASE_SECONDS": (
        "`capture_runs` ijarasining muddati — tik va worker orkestratsiyasi "
        "04-07 da tug'iladi; qator o'sha reja bilan birga yoziladi."
    ),
    "CAPTURE_BATCH_SIZE": ("Bitta tikda olinadigan qator soni — o'sha 04-07 ning o'lchami."),
    "QUALITY_MAX_BYTES": (
        "T-04-24 shifti. `04-01` `.env.example` ga faqat POLNI "
        "(`QUALITY_MIN_BYTES`) yozgan; shift dekompressiya bombasiga "
        "qarshi va u ham sozlanadigan bo'lishi kerak."
    ),
    "QUALITY_IR_SATURATION": (
        "`light_mode` ning IR chegarasi (§C.8). `04-01` `.env.example` ga "
        "faqat `quality_verdict` chegaralarini yozgan, `light_mode` "
        "chegaralarini emas."
    ),
    "QUALITY_NIGHT_MEAN": (
        "`light_mode` ning kunduz/tun chegarasi (§C.8) — yuqoridagi bilan bir juft."
    ),
}
"""`Settings` da BOR, lekin `.env.example` da HALI YO'Q kalitlar.

⚠ BU REYESTR — «TEGILMAGAN» DEGANI EMAS, «NOMLANGAN» DEGANI.

`.env.example` bu rejaning `files_modified` ida YO'Q (u `04-01` ning
fayli), ya'ni qatorlarni bu yerda qo'shib bo'lmaydi. Muqobil — kalitlarni
`Settings` ga umuman kiritmaslik — ancha yomon bo'lardi: o'shanda
04-06/04-07 sozlamani O'Z fayllariga sochib yuborardi va «fazaning barcha
sozlamalari bitta joyda» qoidasi buzilardi.

Reyestr IKKI TOMONLAMA qulflangan (`PENDING_AUDIT_TRIGGERS` naqshi):

  * ro'yxatdan TASHQARI yangi kalit qo'shilsa -> darvoza qizaradi;
  * ro'yxatdagi kalit `.env.example` ga YOZILSA -> darvoza yana qizaradi
    va reyestrni tozalashga majbur qiladi.

Ya'ni qarz na jimgina o'sadi, na jimgina qoladi.
"""


def _phase4(name: str) -> bool:
    return name.startswith(PHASE4_PREFIXES)


def _env_example_keys() -> dict[str, str]:
    """`.env.example` dagi 4-faza kalitlari va ularning XOM qiymatlari."""
    found: dict[str, str] = {}
    for line in _ENV_EXAMPLE.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        match = _ENV_LINE.match(stripped)
        if match and _phase4(match.group(1)):
            found[match.group(1)] = match.group(2)
    return found


def _settings_keys() -> set[str]:
    """`Settings` ning 4-faza maydonlari — YUQORI registrda."""
    return {name.upper() for name in Settings.model_fields if _phase4(name.upper())}


@pytest.fixture
def build(monkeypatch: pytest.MonkeyPatch) -> Iterator[BuildSettings]:
    """4-faza kalitlarini TOZALAB `Settings` quradi.

    ⚠ TOZALASH MAJBURIY: `tests` konteyneri `compose.yaml` dan bir necha
      `S3_*` qiymatini oladi (`compose.yaml:637-640`). Ular tozalanmasa
      «standart qiymat» testlari konteyner muhitini o'lchardi va xost
      sozlamasi o'zgarganda sabab topilmasdi.

    ⚠⚠ `_env_file=None` — VA U TOZALASHNING IKKINCHI YARMI (04-07 da
       qo'shildi, O'LCHANGAN sabab bilan). `Settings.model_config` da
       `env_file=".env"` turadi va `tests` konteyneri repozitoriyni
       `/app` ga mount qiladi, ya'ni DASTURCHINING `.env` FAYLI bu
       testlarga KO'RINADI.

       Muhit o'zgaruvchisi fayldan ustun turgani uchun `monkeypatch.setenv`
       bilan berilgan qiymatlar himoyalangan — LEKIN «o'zgaruvchi UMUMAN
       yo'q» yo'lida fayl yagona manba bo'lib qoladi. O'lchandi: `.env` ga
       haqiqiy `S3_ACCESS_KEY` yozilgan dasturchida (bu `worker` va
       `scheduler` konteynerlari uchun MAJBURIY —
       `compose.yaml` ularga `${S3_ACCESS_KEY}` ni standartsiz beradi)
       `test_a_missing_empty_s3_key_env_var_fails_the_same_way` QIZARARDI.

       Ya'ni darvoza kodni emas, dasturchining mahalliy faylini o'lchardi.
       `_env_file=None` bilan u AYNAN maydonning STANDARTINI o'lchaydi va
       muhitdan mustaqil bo'ladi.
    """

    def _build(**overrides: str) -> Settings:
        for name in list(os.environ):
            if _phase4(name):
                monkeypatch.delenv(name, raising=False)
        for name, value in _BASELINE.items():
            monkeypatch.setenv(name, value)
        monkeypatch.setenv("NVR_CREDENTIAL_KEY", Fernet.generate_key().decode())
        for name, value in overrides.items():
            monkeypatch.setenv(name, value)
        get_settings.cache_clear()
        return Settings(_env_file=None)  # type: ignore[call-arg]

    get_settings.cache_clear()
    yield _build
    get_settings.cache_clear()


# ---------------------------------------------------------------------------
# `.env.example` <-> `Settings` pariteti
# ---------------------------------------------------------------------------


def test_env_example_parser_finds_the_phase_four_keys() -> None:
    """Parserning O'ZI uchun nazorat — bo'sh to'plam ustidagi tenglik yolg'on."""
    keys = _env_example_keys()

    assert len(keys) >= MIN_PHASE4_KEYS, (
        f"`.env.example` da {MIN_PHASE4_KEYS} dan kam 4-faza kaliti topildi "
        f"({sorted(keys)}). Bu deyarli har doim PARSER buzilganini bildiradi, "
        "kalitlar o'chirilganini emas."
    )


def test_every_env_example_key_has_a_settings_field() -> None:
    """⛔ JIM NO-OP DARVOZASI — hujjatda bor, kodda yo'q.

    `extra="ignore"` sababli bunday kalit hech qanday signal bermasdan
    tashlab yuboriladi (modul docstringi).
    """
    missing = set(_env_example_keys()) - _settings_keys()

    assert not missing, (
        f"`.env.example` da bor, `Settings` da YO'Q: {sorted(missing)}. "
        '`extra="ignore"` bu kalitlarni JIMGINA tashlab yuboradi — operator '
        "sozlamani o'zgartirdim deb o'ylaydi, tizim esa eski qiymat bilan "
        "ishlaydi. Maydon qo'shing yoki kalitni `.env.example` dan olib tashlang."
    )


def test_every_settings_field_is_documented_or_registered() -> None:
    """Teskari yo'nalish — kodda bor, hujjatda yo'q.

    Bu yo'nalish jim no-op emas (maydon standart qiymat bilan ishlaydi),
    lekin operator sozlamaning MAVJUDLIGINI bilmaydi. Shuning uchun har
    bunday maydon `_ENV_EXAMPLE_TODO` da SABAB bilan nomlanishi shart.
    """
    undocumented = _settings_keys() - set(_env_example_keys())

    assert undocumented == set(_ENV_EXAMPLE_TODO), (
        "`Settings` da bor, `.env.example` da yo'q maydonlar reyestrga MOS "
        f"kelmadi.\n  hujjatlanmagan: {sorted(undocumented)}\n"
        f"  reyestrda:      {sorted(_ENV_EXAMPLE_TODO)}\n"
        "Yangi maydon qo'shildimi — uni `_ENV_EXAMPLE_TODO` ga sabab bilan "
        "yozing. `.env.example` ga qator qo'shildimi — uni reyestrdan OLIB "
        "TASHLANG (qarz yopildi)."
    )


def test_registered_gaps_carry_a_reason() -> None:
    """Reyestr yozuvi SABABSIZ bo'lmasligi kerak — aks holda u shunchaki ro'yxat."""
    for key, reason in _ENV_EXAMPLE_TODO.items():
        assert len(reason) > 40, f"{key} — sabab juda qisqa: {reason!r}"


def test_env_example_values_equal_the_settings_defaults(build: BuildSettings) -> None:
    """⛔ QIYMATLAR HAM MOS BO'LISHI SHART, faqat kalit nomlari emas.

    `xlsx_reader.py` dan meros naqsh: «standart qiymat ikki joyda yozilgan
    bo'lsa, ular BIRGA o'zgarishi kerak». Aks holda `.env` ni
    `.env.example` dan nusxalagan operator KODDAGI standartdan BOSHQA
    xulq oladi va ikkalasi ham «to'g'ri» ko'rinadi.

    ⚠ `S3_ACCESS_KEY`/`S3_SECRET_KEY` chetlab o'tiladi: ular SIR va
      `Settings` da ma'noli standart qiymatga EGA EMAS (maydon standarti
      `""` — u faqat validator uchun mavjud), ya'ni «kod standarti ==
      `.env.example` qiymati» tengligi ular uchun ma'nosiz bo'lardi.

      ⚠ ULAR ENDI BO'SH EMAS (`04-14`): `.env.example` da
      `ops/seaweedfs/s3.json.example` bilan AYNAN bir xil
      `NAMUNA-ALMASHTIRING-*` juftligi turadi, chunki bo'sh qiymat
      `cp .env.example .env` qilgan yangi klonda `worker`/`scheduler` ni
      ISHGA TUSHISHDA yiqitardi (`deferred-items.md` #2).

      Ularning O'Z darvozalari IKKITA va ular boshqa narsani o'lchaydi:
        * `test_empty_s3_key_fails_at_startup` — bo'sh qiymat rad etiladi;
        * `tests/unit/test_storage_config.py::test_env_example_matches_the_s3_config_example`
          — ikki namuna fayl AYNAN teng (juftlik).
    """
    raw = _env_example_keys()
    secrets_without_default = {"S3_ACCESS_KEY", "S3_SECRET_KEY"}
    overrides = {key: value for key, value in raw.items() if key not in secrets_without_default}

    defaults = build()
    from_example = build(**overrides)

    mismatched = {
        name: (getattr(defaults, name), getattr(from_example, name))
        for name in Settings.model_fields
        if _phase4(name.upper())
        and name.upper() not in secrets_without_default
        and getattr(defaults, name) != getattr(from_example, name)
    }

    assert not mismatched, (
        f"`.env.example` va `Settings` standartlari AJRALIB KETDI: {mismatched}. "
        "(chapda — kod standarti, o'ngda — `.env.example` dan o'qilgani)"
    )


# ---------------------------------------------------------------------------
# Sirlar
# ---------------------------------------------------------------------------


def test_empty_s3_key_fails_at_startup(build: BuildSettings) -> None:
    """⛔ BO'SH S3 KALITI ISHGA TUSHISHDA YIQITADI, birinchi kadrda emas.

    Aks holda konteyner muvaffaqiyatli ko'tarilardi va nosozlik ertalab
    06:00 da, birinchi yuklashda `SignatureDoesNotMatch` bo'lib chiqardi —
    ya'ni butun kunlik reja yo'qolgandan KEYIN (T-04-29).

    ⚠ Test muhitni `monkeypatch` bilan bo'shatadi va `pytest.raises` bilan
      o'lchaydi — qobiqdagi `-e` bayrog'iga tayanadigan tekshiruvdan
      ishonchliroq: u yerda noto'g'ri yozilgan buyruq ham «o'tdi» ko'rinardi.
    """

    with pytest.raises(ValidationError, match="S3_ACCESS_KEY"):
        build(S3_ACCESS_KEY="")

    with pytest.raises(ValidationError, match="S3_SECRET_KEY"):
        build(S3_SECRET_KEY="   ")


def test_a_missing_empty_s3_key_env_var_fails_the_same_way(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """⛔ KALIT UMUMAN BERILMAGAN yo'l ham AYNAN shu darvozaga tushadi.

    Maydonlarning standarti `""` (sabab `settings.py` da: standartsiz
    shakl bu rejaning fayllari BO'LMAGAN `Settings(...)` chaqiruvlarini
    mypy darajasida buzardi). Standart qo'shilishi bilan YANGI yo'l
    ochildi — «o'zgaruvchi umuman yo'q» — va u ALOHIDA o'lchanishi kerak:
    aks holda validator faqat BO'SH SATRNI tekshirib, yetishmayotgan
    o'zgaruvchini jimgina o'tkazib yuborishi mumkin edi.

    ⚠ `_env_file=None` — `build` fixture'idagi bilan AYNAN bir xil sabab va
      u AYNAN SHU TESTDA hal qiluvchi: «o'zgaruvchi umuman yo'q» yo'lida
      dasturchining `.env` fayli yagona qolgan manba bo'lardi va darvoza
      kodni emas, o'sha faylni o'lchardi.
    """
    for name in ("S3_ACCESS_KEY", "S3_SECRET_KEY"):
        monkeypatch.delenv(name, raising=False)
    for name, value in _BASELINE.items():
        if name.startswith("S3_"):
            continue
        monkeypatch.setenv(name, value)
    monkeypatch.setenv("NVR_CREDENTIAL_KEY", Fernet.generate_key().decode())
    get_settings.cache_clear()

    with pytest.raises(ValidationError, match="S3_ACCESS_KEY"):
        Settings(_env_file=None)  # type: ignore[call-arg]

    get_settings.cache_clear()


def test_secrets_are_secret_str_and_do_not_appear_in_repr(build: BuildSettings) -> None:
    """`BaseSettings.__repr__` BARCHA maydonlarni chop etadi (03-04 o'lchovi).

    `lifespan` da `settings` lokal o'zgaruvchi, Sentry esa istisno paytida
    lokal o'zgaruvchilarni yig'adi — ya'ni oddiy `str` birinchi
    istisnodayoq oqib ketardi. Himoya kelishuv emas, TIP.
    """
    s3_secret = "s3-secret-canary-8f2b1d"
    telegram = "telegram-token-canary-4c7a9e"

    settings = build(S3_SECRET_KEY=s3_secret, TELEGRAM_BOT_TOKEN=telegram)
    rendered = repr(settings)

    assert isinstance(settings.s3_secret_key, SecretStr)
    assert isinstance(settings.telegram_bot_token, SecretStr)
    assert s3_secret not in rendered
    assert telegram not in rendered
    assert settings.s3_secret_key.get_secret_value() == s3_secret
    assert settings.telegram_bot_token.get_secret_value() == telegram


def test_log_filter_covers_the_phase_four_secret_names() -> None:
    """`censor_secrets` fazaning uchala sirini MASKALAYDI (T-04-28, T-04-59).

    =====================================================================
    BU TEST `04-04` DA TESKARI DA'VO BILAN TUG'ILGAN VA `04-08` DA AG'DARILDI.

    `04-04` o'lchagan edi: `SENSITIVE_KEYS` — ANIQ NOMLAR ro'yxati, naqsh
    emas (`_is_sensitive`: `str(key).lower() in SENSITIVE_KEYS`), ya'ni
    `*_key` / `*_token` / `*_secret` shakli avtomatik QAMRAB OLINMAYDI va
    uchala nom ham senzuradan O'TIB KETARDI (`covered == set()`).
    `logging.py` esa o'sha rejaning `files_modified` ida YO'Q edi.

    Shuning uchun `04-04` bu yerga O'ZINI BEKOR QILADIGAN test qoldirgan:
    u hozirgi holatni qulflardi va QAMROV PAYDO BO'LGANDA QIZARARDI.
    `04-08` — Telegram tokenini ISHLATADIGAN birinchi reja — bandni yopdi
    va shu bilan birga bu testni AG'DARDI: endi u qamrovning MAVJUDLIGINI
    talab qiladi.

    ⚠ Endi test TESKARI yo'nalishda qo'riqlaydi: `SENSITIVE_KEYS` dan
      uchala nomdan biri olib tashlansa (yoki yangi sozlama nomi bilan
      almashtirilsa) darvoza QIZARADI.
    =====================================================================

    ⚠ `SecretStr` BU YO'LNI YOPMAYDI va u yuqoridagi testning o'rnini
      bosmaydi: `SecretStr` `repr(settings)` ni yopadi, structlog
      kalitini emas. Ikki himoya IKKI XIL yo'lni to'sadi va ikkalasi ham
      kerak.
    """
    candidates = ("s3_access_key", "s3_secret_key", "telegram_bot_token")

    censored = censor_secrets(None, "info", dict.fromkeys(candidates, "leak-me"))
    uncovered = sorted(name for name in candidates if censored[name] != CENSORED)

    assert uncovered == [], (
        f"`censor_secrets` {uncovered} ni MASKALAMADI — ya'ni bu nom(lar) "
        "`SENSITIVE_KEYS` dan tushib qolgan. `log.info(..., <nom>=...)` "
        "shaklidagi har qanday chaqiruv sirni stdout'ga va Sentry'ga "
        "yuboradi. Ro'yxat: `packages/sbozor-core/sbozor_core/logging.py`."
    )


def test_the_secret_filter_still_ignores_non_secret_key_shaped_names() -> None:
    """NAZORAT HOLATI: `*_key` shakli O'Z-O'ZIDAN sir emas.

    ⚠ BU TEST YUQORIDAGISINING JUFTI VA U YOLG'ON-MUSBAT SENZURANI
      TO'SADI. `SENSITIVE_KEYS` ni naqshga («har qanday `*_key`»)
      aylantirish vasvasasi tabiiy, lekin u `object_key` ni ham
      maskalardi — retention, dalil zanjiri va ombor diagnostikasining
      HAMMASI o'sha kalitga tayanadi va ular jurnalda `***` bo'lib
      qolardi.

    Ya'ni bu yerda o'lchanadigan narsa — ro'yxat naqshga AYLANMAGANI.
    """
    benign = ("object_key", "alert_key", "idempotency_key")

    censored = censor_secrets(None, "info", dict.fromkeys(benign, "ko'rinishi-shart"))
    masked = sorted(name for name in benign if censored[name] == CENSORED)

    assert masked == [], (
        f"{masked} sababsiz maskalandi — `SENSITIVE_KEYS` naqshga "
        "aylantirilgan bo'lsa kerak. Yolg'on-musbat senzura nosozlikni "
        "topib bo'lmaydigan qiladi."
    )


def test_empty_telegram_token_does_not_fail_and_disables_alerts(build: BuildSettings) -> None:
    """Bo'sh token — QONUNIY holat (D-19), S3 kalitlaridan TESKARI.

    Alertsiz kadr — alertli kadrsizlikdan yaxshiroq: bo'sh token ustida
    yiqilish butun kadr olish quvurini to'xtatardi.
    """

    settings = build()

    assert settings.telegram_bot_token.get_secret_value() == ""
    assert settings.telegram_chat_id == ""
    assert settings.alerts_enabled is False


def test_alerts_need_both_the_token_and_the_chat_id(build: BuildSettings) -> None:
    """Yarim sozlangan alert — «alert bor» degan YOLG'ON ishonchning manbai."""

    assert build(TELEGRAM_BOT_TOKEN="t").alerts_enabled is False
    assert build(TELEGRAM_CHAT_ID="-100123").alerts_enabled is False
    assert build(TELEGRAM_BOT_TOKEN="t", TELEGRAM_CHAT_ID="-100123").alerts_enabled is True


# ---------------------------------------------------------------------------
# Chegaralar va standart qiymatlar
# ---------------------------------------------------------------------------


def test_retention_full_days_zero_is_legal_but_negative_is_not(build: BuildSettings) -> None:
    """`0` — «to'liq sifatda umuman saqlanmasin» degan QONUNIY siyosat (D-18)."""

    assert build(RETENTION_FULL_DAYS="0").retention_full_days == 0

    with pytest.raises(ValidationError):
        build(RETENTION_FULL_DAYS="-1")


def test_snapshot_max_times_per_day_rejects_zero_and_two_hundred(build: BuildSettings) -> None:
    """Server tomonidagi QATTIQ chegara — mijoz tekshiruvi darvoza emas.

    `04-UI-SPEC.md` §4.6: UI 12 tani ko'rsatadi va server AYNAN shu sonni
    MAJBURLAYDI. `0` rejani ma'nosiz qilardi, `200` esa «har 5 daqiqada»
    patologiyasini ochardi (4 225 kadr/kun).
    """

    assert build().snapshot_max_times_per_day == 12

    with pytest.raises(ValidationError):
        build(SNAPSHOT_MAX_TIMES_PER_DAY="0")

    with pytest.raises(ValidationError):
        build(SNAPSHOT_MAX_TIMES_PER_DAY="200")


def test_shipped_defaults_are_the_documented_numbers(build: BuildSettings) -> None:
    """D-18 va D-08 ning raqamlari — bitta joyda, o'qilib tekshiriladi."""
    settings = build()

    assert settings.retention_full_days == 90
    assert settings.retention_compressed_days == 365
    assert settings.snapshot_max_times_per_day == 12
    assert settings.capture_grace_seconds == 600
    assert settings.capture_global_concurrency == 1


def test_quality_thresholds_returns_a_versioned_frozen_object(build: BuildSettings) -> None:
    """Chegaralar `QualityThresholds` bo'lib chiqadi — sof modul uchun argument."""

    thresholds = build().quality_thresholds()

    assert isinstance(thresholds, QualityThresholds)
    assert thresholds.version == QUALITY_THRESHOLDS_VERSION


def test_quality_thresholds_match_the_shipped_defaults(build: BuildSettings) -> None:
    """⛔ `test_quality_filter.py::_SHIPPED` NUSXASINI `Settings` GA BOG'LAYDI.

    Sifat filtrining testi `get_settings()` ni ATAYIN chaqirmaydi (u
    muhitga bog'lanib qolardi), ya'ni u yetkazilgan raqamlarni QO'LDA
    takrorlaydi. Bu test o'sha nusxani manbaga bog'laydi: standart
    o'zgartirilsa AYNAN shu yerda qizaradi va nusxa eskirib qola olmaydi.
    """
    assert build().quality_thresholds() == _SHIPPED
