"""Ishlab chiqarish bog'liqliklari darvozasi (W0-1 / D-16, T-03-01, T-03-06).

=============================================================================
NEGA BU TEST BOR VA NEGA U BOSHQA HECH QAYERDA ISHLAMAYDI:

Bu sinfdagi xato **FAQAT DEPLOY PAYTIDA** ko'rinadi. `services/core-api/
Dockerfile` ikkita target quradi:

    dev      -> `uv sync --frozen`             (dev guruhi BILAN)
    runtime  -> `uv sync --frozen --no-dev`    (dev guruhi TUSHMAYDI)

Butun test to'plami `dev` target'da ishlaydi. Ya'ni `[dependency-groups]
dev` dagi modul testlarda BOR, prod image'da esa YO'Q — va bu farqni
birorta test ko'rmaydi. 2026-08-03 holatiga `import httpx` yozadigan 24 ta
test fayli bor edi, ya'ni "httpx bor-ku" degan taassurot mustahkam va
YOLG'ON edi: 03-05 ning ISAPI klienti — ishlab chiqarish kodi va prod
image'da u `ModuleNotFoundError: No module named 'httpx'` bilan yiqilardi.
Servis umuman ko'tarilmasdi (T-03-01 — Denial of Service).

Shuning uchun darvoza **manifestning o'zini** o'qiydi, import qilib
ko'rmaydi: import bu konteynerda HAR DOIM muvaffaqiyatli bo'ladi va aynan
shu narsa muammoni yashiradi.
=============================================================================

Ikkinchi vazifa — `redis` pinini qo'riqlash (T-03-06). `arq` legitim paket,
lekin u `redis[hiredis]<6,>=4.2.0` talab qiladi; core-api esa
`redis[hiredis]==8.0.1` ga qadalgan. `uv add arq` `redis` ni 5.x ga
TUSHIRARDI va `app/security/ratelimit.py` bilan sessiya keshi jimgina
eskiroq klientda ishlab qolardi — ya'ni buzilish navbat kodida emas,
BUTUNLAY BOSHQA joyda chiqardi (D-06, 03-RESEARCH Pitfall 1).
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
CORE_API_PYPROJECT = REPO_ROOT / "services" / "core-api" / "pyproject.toml"
ROOT_PYPROJECT = REPO_ROOT / "pyproject.toml"

# 3-faza ishlatadigan pytest markerlari (W0-5). `addopts` da
# `--strict-markers` bor, ya'ni e'lon qilinmagan marker testga qo'yilgan
# zahoti YIG'ILISH xatosi beradi va butun fayl umuman ishga tushmaydi.
# O'lchangan (2026-08-03): e'lon qilinmagan `@pytest.mark.X` ->
# "'X' not found in `markers` configuration option", pytest exit 2.
REQUIRED_MARKERS = {"tenancy", "sim", "hardware", "slow"}

# Prod kodidan chaqiriladigan, ya'ni runtime image'da BO'LISHI SHART bo'lgan
# paketlar. Har biri uchun "kim chaqiradi" izohi majburiy — ro'yxat o'sganda
# sabab code review'da ko'rinadi.
REQUIRED_RUNTIME_PACKAGES = {
    # 03-05: Hikvision ISAPI klienti (`httpx.DigestAuth` — RFC 7616 ni
    # qo'lda yozish taqiqlangan) va go2rtc HTTP chaqiruvlari.
    "httpx",
    # 03-06: kashfiyot job'ining navbati (D-06 — `arq` o'rniga).
    "taskiq",
    "taskiq-redis",
    # 03-05: TARMOQ xatolarida qayta urinish. `401` da HECH QACHON
    # (D-03 — Hikvision hisobni ~5 urinishdan keyin qulflaydi).
    "tenacity",
    # 04-06: `app/services/storage.py` — SeaweedFS ga async S3 yozish/o'qish
    # (D-17). `httpx` bilan AYNAN bir xil sinf: kadr olish zanjiri prod
    # image'da import paytida yiqilardi (T-04-03).
    "aiobotocore",
    # 04-04 + 04-08: `app/services/quality.py` sifat metrikalari
    # (`ImageStat`) va saqlash siyosatining JPEG qayta siqishi (D-13).
    "pillow",
}

# HECH BIR guruhda bo'lmasligi kerak bo'lgan paketlar — har biri uchun
# sabab MUSTAQIL, lekin qaror bir xil. `arq` ham shu sinfda, lekin unga
# alohida test bor (pastda, `redis` pini bilan birga o'lchanadi).
FORBIDDEN_PACKAGES = {
    # D-17: `aiobotocore[boto3]==2.25.1` ni QATTIQ qadaydi, ya'ni
    # `aiobotocore` ni 3.9.0 dan 2.25.1 ga va `boto3` ni pindan pastga
    # tortadi. `arq` epizodining ikkinchi nusxasi, EMPIRIK tasdiqlangan
    # (04-RESEARCH §D.9.2, PyPI 2026-08-04). Oxirgi relizi 2025-10-30.
    "aioboto3",
    # `boto3` ning O'ZI ham kerak emas: `aiobotocore` `botocore` ga
    # to'g'ridan-to'g'ri tayanadi. `boto3` qo'shilishi yuqoridagi
    # pasaytirish zanjirining birinchi belgisi bo'lardi.
    "boto3",
    # CLAUDE.md taqig'i: `minio-py` mijozni BITTA vendorga va ARXIVLANGAN
    # serverga bog'lab qo'yardi. S3 API omborni REFAKTOR emas, SOZLAMA
    # o'zgarishi qilib saqlaydi (SeaweedFS -> Garage -> AWS -> O'zbek buluti).
    "minio",
    # D-13: sifat filtri uchun `Pillow` yetadi. `opencv` — `cv-service`
    # ning bog'liqligi (5-faza) va u runtime image'ga ~70 MB qo'shardi.
    "opencv-python",
    "opencv-python-headless",
    # `aiogram` `pydantic<2.14` va `redis<8` ni qadaydi, core-api esa
    # `pydantic==2.13.4` va `redis==8.0.1` da. U bot-service'ning
    # bog'liqligi va servislar bo'yicha AJRATILGAN qolishi shart
    # (CLAUDE.md Version Compatibility). Telegram alerti `httpx` bilan.
    "aiogram",
}

# Faqat testdan chaqiriladigan, ya'ni prodga TUSHMASLIGI kerak bo'lgan
# paketlar. Bu yo'nalish ham qulflanadi: mock qatlami ishlab chiqarish
# kodiga sizib o'tsa, u shu yerda ko'rinadi.
DEV_ONLY_PACKAGES = {
    "respx",  # `httpx` uchun mock transport
    "pytest",
    "testcontainers",
}


def _parse(path: Path) -> dict[str, Any]:
    assert path.is_file(), f"{path} topilmadi — repo tuzilishi o'zgargan bo'lishi mumkin"
    data: dict[str, Any] = tomllib.loads(path.read_text(encoding="utf-8"))
    return data


def _requirement_name(spec: str) -> str:
    """`redis[hiredis]==8.0.1` -> `redis`; `XlsxWriter==3.2.9` -> `xlsxwriter`.

    Nom PEP 503 bo'yicha normallashtiriladi (kichik harf, `_`/`.` -> `-`),
    aks holda `taskiq_redis` va `taskiq-redis` ikki xil paket bo'lib
    ko'rinardi va darvoza jimgina o'tkazib yuborardi.
    """
    head = spec.split(";", 1)[0].strip()
    for separator in ("==", ">=", "<=", "~=", "!=", ">", "<", "@"):
        head = head.split(separator, 1)[0]
    return head.split("[", 1)[0].strip().lower().replace("_", "-").replace(".", "-")


@pytest.fixture(scope="module")
def core_api_manifest() -> dict[str, Any]:
    return _parse(CORE_API_PYPROJECT)


@pytest.fixture(scope="module")
def runtime_packages(core_api_manifest: dict[str, Any]) -> set[str]:
    """`uv sync --no-dev` o'rnatadigan paketlar."""
    return {_requirement_name(spec) for spec in core_api_manifest["project"]["dependencies"]}


@pytest.fixture(scope="module")
def dev_packages(core_api_manifest: dict[str, Any]) -> set[str]:
    """FAQAT `dev` guruhidagi paketlar (runtime image'ga tushmaydi)."""
    return {_requirement_name(spec) for spec in core_api_manifest["dependency-groups"]["dev"]}


# --------------------------------------------------------------------------
# T-03-01: prod kodi ishlatadigan modul dev guruhida qolib ketmasin
# --------------------------------------------------------------------------


@pytest.mark.parametrize("package", sorted(REQUIRED_RUNTIME_PACKAGES))
def test_production_package_is_a_project_dependency(
    package: str, runtime_packages: set[str]
) -> None:
    """Prod kodidan chaqiriladigan paket `[project] dependencies` da.

    `httpx` uchun bu AYNAN D-16: u 2026-08-03 gacha `dev` da turgan va
    ISAPI klienti unga tayanadi.
    """
    assert package in runtime_packages, (
        f"`{package}` `[project] dependencies` da yo'q — u ishlab chiqarish "
        "kodidan chaqiriladi, ya'ni `uv sync --frozen --no-dev` bilan qurilgan "
        "runtime image'da `ModuleNotFoundError` beradi. Testlar bu xatoni "
        "KO'RMAYDI: ular `dev` target'da ishlaydi."
    )


@pytest.mark.parametrize("package", sorted(REQUIRED_RUNTIME_PACKAGES))
def test_production_package_is_not_dev_only(package: str, dev_packages: set[str]) -> None:
    """Ikki tomonlama e'lon ham xato: `dev` dagi nusxa yolg'on xotirjamlik beradi.

    Paket ikkala guruhda ham turgan bo'lsa, birinchisini o'chirgan odam
    "baribir ikkinchisida bor" deb o'ylardi va prod image jimgina
    bog'liqliksiz qolardi.
    """
    assert package not in dev_packages, (
        f"`{package}` `[dependency-groups] dev` da HAM bor — u prod bog'liqligi, "
        "nusxasi esa faqat chalkashlik beradi"
    )


@pytest.mark.parametrize("package", sorted(DEV_ONLY_PACKAGES))
def test_dev_only_package_stays_out_of_runtime(package: str, runtime_packages: set[str]) -> None:
    """Teskari yo'nalish: mock/test qatlami runtime image'ga sizib o'tmasin.

    `respx` — `httpx` uchun mock transport. U prod bog'liqligiga aylansa,
    ishlab chiqarish kodi undan import qila oladigan bo'lardi va HTTP
    chaqiruvini jimgina soxtalashtirish yo'li ochilardi.
    """
    assert package not in runtime_packages, (
        f"`{package}` `[project] dependencies` ga tushib qolgan — u faqat "
        "testlarda ishlatiladi va runtime image'ni kattalashtiradi"
    )


# --------------------------------------------------------------------------
# T-03-06: `redis` pini — `arq` sinfidagi to'qnashuvning yagona belgisi
# --------------------------------------------------------------------------


def test_redis_pin_is_not_downgraded(core_api_manifest: dict[str, Any]) -> None:
    """`redis[hiredis]` AYNAN `8.0.1` da qoladi (D-06).

    Pasayish `arq` sinfidagi to'qnashuvning YAGONA ogohlantiruvchi belgisi:
    navbat paketi o'rnatilganda `uv` `redis` ni jimgina 5.x ga tushiradi va
    buzilish `app/security/ratelimit.py` da — butunlay boshqa joyda —
    chiqadi. `taskiq-redis 1.2.3` `redis<9,>=8.0.0` talab qiladi, ya'ni bu
    pin bilan AYNAN mos.
    """
    specs = [
        spec
        for spec in core_api_manifest["project"]["dependencies"]
        if _requirement_name(spec) == "redis"
    ]

    assert specs == ["redis[hiredis]==8.0.1"], (
        f"`redis` pini o'zgargan: {specs}. Kutilgan qiymat "
        "`redis[hiredis]==8.0.1` — pasayish `arq` sinfidagi to'qnashuv "
        "sodir bo'lganini bildiradi (D-06, 03-RESEARCH Pitfall 1)."
    )


@pytest.mark.parametrize("package", sorted(FORBIDDEN_PACKAGES))
def test_forbidden_package_is_absent_from_both_groups(
    package: str, runtime_packages: set[str], dev_packages: set[str]
) -> None:
    """Taqiqlangan paket IKKALA guruhda ham yo'q (D-13/D-17, T-04-05).

    `dev` guruhi ham qamraladi va bu ATAYIN: `uv add --dev aioboto3`
    ham `uv.lock` ni qayta hal qiladi, ya'ni `aiobotocore` va `boto3`
    pinlarini AYNAN o'sha tarzda pastga tortardi. Guruh farqi bu
    to'qnashuvni umuman yumshatmaydi — lock bitta.
    """
    assert package not in runtime_packages | dev_packages, (
        f"`{package}` bog'liqliklarga qo'shilgan — u shu faylning "
        "`FORBIDDEN_PACKAGES` ro'yxatida, sababi esa o'sha yerda yozilgan. "
        "Qaror `services/core-api/pyproject.toml` izohida ham takrorlangan."
    )


def test_arq_is_not_installed_anywhere(runtime_packages: set[str], dev_packages: set[str]) -> None:
    """`arq` HECH BIR guruhda yo'q — qaror mexanik qulflangan (D-06).

    Sabab `pyproject.toml` izohida yozilgan, lekin izoh darvoza emas: kimdir
    CLAUDE.md ning eskiroq bo'limini o'qib `uv add arq` qilishi mumkin. Bu
    assert o'sha harakatni CI'da to'xtatadi va sababini aytadi.
    """
    assert "arq" not in runtime_packages | dev_packages, (
        "`arq` bog'liqliklarga qo'shilgan — u `redis[hiredis]<6` talab qiladi "
        "va `redis==8.0.1` pinini buzadi. O'rniga `taskiq` + `taskiq-redis` "
        "ishlatiladi (D-06, empirik tasdiqlangan 2026-08-02)."
    )


# --------------------------------------------------------------------------
# W0-5: `--strict-markers` ostidagi marker e'lonlari
# --------------------------------------------------------------------------


def test_required_pytest_markers_are_declared() -> None:
    """`sim`/`hardware`/`slow` markerlari SIMULYATOR KODIDAN OLDIN e'lon qilingan.

    Tartib muhim: `--strict-markers` ostida e'lon qilinmagan marker testga
    qo'yilgan zahoti YIG'ILISH xatosi beradi (o'lchandi: pytest exit 2,
    "not found in `markers` configuration option"), ya'ni fayl umuman
    ishga tushmaydi va sabab test mantig'ida emas, konfiguratsiyada
    bo'ladi. `slow` — D-09 ning to'g'ridan-to'g'ri talabi (25 kanalli
    stsenariy standart zanjirdan tashqarida turadi).
    """
    ini = _parse(ROOT_PYPROJECT)["tool"]["pytest"]["ini_options"]
    declared = {entry.split(":", 1)[0].strip() for entry in ini["markers"]}

    missing = REQUIRED_MARKERS - declared
    assert not missing, (
        f"e'lon qilinmagan markerlar: {sorted(missing)} — ularni ishlatadigan "
        "har qanday test `--strict-markers` ostida YIG'ILISHDA yiqiladi"
    )
    assert "--strict-markers" in ini["addopts"], (
        "`--strict-markers` `addopts` dan yo'qolgan — endi xato yozilgan marker "
        "JIMGINA e'tiborsiz qoldiriladi va `-m sim` 0 test tanlaydi"
    )


# --------------------------------------------------------------------------
# Nazorat holati: darvozaning o'zi ishlayotganini isbotlash
# --------------------------------------------------------------------------


def test_manifest_actually_parsed(runtime_packages: set[str], dev_packages: set[str]) -> None:
    """Bo'sh to'plamda hamma assert jimgina o'tib ketardi.

    `_parse` yo'li noto'g'ri bo'lsa yoki TOML tuzilishi o'zgarsa,
    yuqoridagi "yo'q" testlari HAMMASI yashil qolardi — chunki bo'sh
    to'plamda hech nima yo'q. Bu quyi chegara shu yolg'on-yashilni yopadi.
    """
    assert len(runtime_packages) >= 20, f"prod bog'liqliklari juda kam: {sorted(runtime_packages)}"
    assert len(dev_packages) >= 5, f"dev bog'liqliklari juda kam: {sorted(dev_packages)}"
    # Nazorat qiymati: 1-fazadan beri o'zgarmagan, ya'ni parser haqiqatan
    # ham manifestni o'qiyapti.
    assert "fastapi" in runtime_packages
