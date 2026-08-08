"""Litsenziya devori — UCH QATLAM, MANIFESTDAN OLDIN (W0-1, D-03, D-04, T-05-05/T-05-SC).

=============================================================================
NEGA BU FAYL `services/cv-service/pyproject.toml` DAN OLDIN YOZILADI.

`rfdetr` ni o'rnatish `torch` ni ham tortadi — u ekstra EMAS, MAJBURIY
bog'liqlik (D-04, CLAUDE.md «Version Compatibility»). Ya'ni darvoza
manifestdan KEYIN yozilsa, u allaqachon sodir bo'lgan ishni tasdiqlagan
bo'lardi: `uv add rfdetr` `uv.lock` ni qayta hal qilib ~800 MB ni ichkariga
kiritgan bo'lardi va «devor» faqat keyingi safar uchun ishlardi.

Shuning uchun tartib teskari: BU TEST BIRINCHI COMMIT'DA QIZIL TURADI va
`services/cv-service/pyproject.toml` tug'ilgan zahoti yashil bo'ladi. Bu
`schema_contract.py:140-148` dagi «reyestr migratsiyadan OLDIN yoziladi,
meta-test vaqtincha qizil turadi» qarorining aynan takrori.

=============================================================================
NEGA UCH QATLAM VA NEGA HAR BIRI ALOHIDA KERAK.

  (1) MANIFEST   — `services/cv-service/pyproject.toml` NIYATI.
                   `tomllib` bilan o'qiladi, IMPORT QILINMAYDI —
                   `test_runtime_deps.py:3-23` dagi sabab so'zma-so'z
                   amal qiladi: import bu konteynerda har doim
                   muvaffaqiyatli bo'ladi va aynan shu narsa muammoni
                   yashiradi.

  (2) LOCKFILE   — HAQIQATDA hal qilingan graf. Bu qatlam manifestdan
                   KUCHLIROQ: manifest faqat TO'G'RIDAN-TO'G'RI e'lonni
                   ko'radi, lock esa TRANZITIV tortishni ham ko'radi.
                   `rfdetr-plus` (PML 1.0) hech qachon to'g'ridan-to'g'ri
                   yozilmaydi — u `rfdetr[plus]` ekstrasi orqali keladi,
                   ya'ni uni FAQAT shu qatlam ushlaydi.

  (3) METADATA   — RO'YXAT EMAS, PREDIKAT (§S-10). O'rnatilgan har bir
                   distributivning `License-Expression` va
                   `Classifier: License ::` maydonlari o'qiladi;
                   `LicenseRef-` (OSI bo'lmagan) yoki `AGPL` uchrasa test
                   yiqiladi. Kelajakdagi NOMA'LUM proprietar paketni ham
                   ushlaydi — nomlar ro'yxati esa ushlamasdi.

=============================================================================
⚠ (3)-QATLAMNING QAMROVI TOR VA U YASHIRILMAYDI.

Bu fayl ROOT `tests` konteynerida ishlaydi, ya'ni
`importlib.metadata.distributions()` `core-api` ning MUHITINI ko'radi —
`cv-service` nikini EMAS. `cv-service` muhiti uchun javobgar qatlam —
(2), va u kuchliroq (lock butun grafni yozadi).

Soxta qamrov da'vosi qilinmaydi: agar bu fayl «cv-service muhitida PML
yo'q» deb da'vo qilsa, u AYNAN o'sha jimgina yolg'on sinfiga tushardi.
=============================================================================
"""

from __future__ import annotations

import re
import tomllib
from importlib.metadata import Distribution, distributions
from pathlib import Path
from typing import Any, Final

import pytest

# ⚠ NOM NORMALLASHTIRISH NUSXA OLINMAYDI, IMPORT QILINADI.
#   Ikki nusxa ikki xil normallashtirishga ajralib ketardi va o'shanda
#   `taskiq_redis` bir darvozada tutilib, ikkinchisida jimgina o'tib
#   ketardi. Import yo'li `tests/unit/test_snapshot_settings.py:41`
#   (`from unit.test_quality_filter import _SHIPPED`) bilan bir xil.
from unit.test_runtime_deps import _requirement_name

REPO_ROOT: Final = Path(__file__).resolve().parents[2]
CV_SERVICE_PYPROJECT: Final = REPO_ROOT / "services" / "cv-service" / "pyproject.toml"
CV_SERVICE_LOCK: Final = REPO_ROOT / "services" / "cv-service" / "uv.lock"

# Ishlab chiqarish kodidan chaqiriladigan, ya'ni `uv sync --no-dev` bilan
# qurilgan runtime image'da BO'LISHI SHART bo'lgan paketlar. Har biri uchun
# «kim chaqiradi» izohi MAJBURIY — ro'yxat o'sganda sabab code review'da
# ko'rinadi (`test_runtime_deps.py` qoidasi).
REQUIRED_RUNTIME_PACKAGES: Final[frozenset[str]] = frozenset(
    {
        # 05-07: `app/detector/session.py` — ONNX inferensi (CPU EP).
        # `torch` O'RNIGA aynan shu: 15 MB vs ~800 MB (D-04).
        "onnxruntime",
        # 05-07: `app/detector/zones.py` — `sv.PolygonZone` bandlik qarori
        # va `app/detector/annotate.py` — nazoratchi ko'radigan dalil rasm.
        # Nuqta-poligon ichida testi QO'LDA YOZILMAYDI (§4.2).
        "supervision",
        # 05-07/05-08: kadrni dekodlash, o'lchamini o'zgartirish, kesish.
        # ⚠ AYNAN SHU PAKET `core-api` DA IKKALA GURUHDA HAM TAQIQLANGAN
        #   (`test_runtime_deps.py:91-94`) — va bu taqiq O'LCHANGAN qaror.
        #   `cv-service` ning alohida bog'liqlik to'plami bo'lishining
        #   BEVOSITA sababi shu (W0-2).
        "opencv-python-headless",
        # 05-07: xom tenzor arifmetikasi (§4.3) va `sv.Detections` massivlari.
        "numpy",
        # 05-08: dalil rasmini JPEG qilib qayta kodlash (04-04 naqshi).
        "pillow",
        # 05-08: `app/services/storage.py` — SeaweedFS dan kadrni O'QISH.
        # `aioboto3` EMAS (D-17, `test_runtime_deps.py` dagi sabab).
        "aiobotocore",
        # 05-08: `app/worker.py` — aniqlash vazifalarining navbati.
        # `arq` EMAS (D-06): u `redis[hiredis]<6` talab qiladi.
        "taskiq",
        "taskiq-redis",
        # 05-02: minimal FastAPI — health va yurak urishi (D-23).
        "fastapi",
        # 05-08: `occupancy_events` yozuvi va tenant konteksti.
        "sqlalchemy",
        "asyncpg",
        # 05-02: `market_id`/`snapshot_id` bilan bog'langan jurnal.
        "structlog",
        # 05-02: `SENTRY_DSN` berilgan JARAYON `init_sentry()` ni chaqirishi
        # SHART (`test_sentry_processes.py` — hosila darvoza).
        "sentry-sdk",
        # 05-02: `Settings` — model fayli yo'q bo'lsa ISHGA TUSHISHDA yiqiladi.
        "pydantic-settings",
        # `ZoneInfo("Asia/Tashkent")` slim image'da BUSIZ yiqiladi.
        "tzdata",
    }
)

FORBIDDEN_PACKAGES: Final[frozenset[str]] = frozenset(
    {
        # ⚠⚠ `rfdetr` NING O'ZI TAQIQLANGAN — VA BU ENG OSON XATO QILINADIGAN
        # BAND. Paket Apache-2.0 va u «modelimiz» degan taassurot beradi,
        # LEKIN `torch` uning MAJBURIY bog'liqligi (ekstrasi emas, D-04):
        # `uv add rfdetr` ishlab chiqarish image'iga ~800 MB qo'shardi.
        # Ishlab chiqarish yo'li: `onnxruntime` + OLDINDAN eksport qilingan
        # `.onnx` (`ops/models/README.md` retseptni yozadi).
        "rfdetr",
        # PML 1.0 — Apache-2.0 EMAS. 1.9.x da ALOHIDA distributivga ko'chgan
        # va faqat `rfdetr[plus]` ekstrasi orqali keladi (D-03), ya'ni u
        # manifestda HECH QACHON ko'rinmaydi — uni (2)-qatlam ushlaydi.
        "rfdetr-plus",
        # D-04: ishlab chiqarish inferensi uchun kerak emas. `torch` FAQAT
        # ijara GPU'dagi alohida `cv-train` image'ida yashaydi.
        "torch",
        "torchvision",
        # AGPL-3.0 — tijoriy SaaS uchun manba oshkor qilish yoki pullik
        # litsenziya. CLAUDE.md ning QAT'IY taqig'i. `supervision` ning
        # rasmiy «occupancy» misoli aynan shuni import qiladi (§4.2, Tuzoq 3),
        # ya'ni misolni ko'chirib olish uni jimgina ichkariga kiritardi.
        "ultralytics",
        # `aiobotocore[boto3]==2.25.1` ni QATTIQ qadaydi va pinlarni pastga
        # tortadi (D-17, `test_runtime_deps.py` da EMPIRIK tasdiqlangan).
        "aioboto3",
        "boto3",
        # Mijozni BITTA vendorga va ARXIVLANGAN serverga bog'lardi.
        "minio",
    }
)

LOCK_FORBIDDEN_NAMES: Final[tuple[str, ...]] = ("rfdetr", "rfdetr-plus", "torch", "ultralytics")
"""(2)-QATLAM: `uv.lock` da BO'LMASLIGI kerak bo'lgan paket bloklari.

⚠ Bu ro'yxat `FORBIDDEN_PACKAGES` dan QISQAROQ va bu ATAYIN: lock TRANZITIV
  grafni yozadi, ya'ni bu yerdagi har bir nom «hech qanday yo'l bilan
  kirmadi» degan KUCHLIROQ da'vo. `boto3` esa `aiobotocore[boto3]` orqali
  qonuniy ravishda paydo bo'lishi mumkin bo'lgan chegaraviy holat — uni
  manifest qatlami (1) qo'riqlaydi.
"""

LICENSE_REF_PREFIX: Final = "licenseref-"
"""OSI TASDIQLAMAGAN litsenziyaning SPDX belgisi.

⚠ RO'YXAT EMAS, PREDIKAT (§S-10). `LicenseRef-PML-1.0` bugungi holat, lekin
  darvoza uni NOM bilan bilmaydi: SPDX qoidasi bo'yicha `LicenseRef-` bilan
  boshlanadigan HAR QANDAY ifoda — reyestrda yo'q, ya'ni OSI tasdiqlamagan
  shartlar. Kelajakdagi noma'lum proprietar paket ham shu tarzda kelib
  tushadi va aynan shuning uchun predikat nomlar ro'yxatidan kuchliroq.
"""

AGPL_MARKER: Final = "agpl"
"""AGPL ning HAR QANDAY shakli — `AGPL-3.0`, `AGPL-3.0-only`, `AGPL-3.0-or-later`.

Klassifikatorda u «GNU Affero General Public License v3» ko'rinishida ham
yoziladi, shuning uchun quyida IKKALA shakl ham qidiriladi.
"""

AGPL_CLASSIFIER_MARKER: Final = "affero"

LICENSE_EXPRESSION_FIELD: Final = "License-Expression"
LICENSE_FIELD: Final = "License"
CLASSIFIER_FIELD: Final = "Classifier"
LICENSE_CLASSIFIER_PREFIX: Final = "License ::"

_LOCK_PACKAGE_NAME = re.compile(r'^\s*name\s*=\s*"([^"]+)"\s*$', re.MULTILINE)
"""`uv.lock` — TOML, lekin u MATN sifatida o'qiladi.

`test_sentry_processes.py:34-41` qoidasi: `PyYAML` bu loyihaning bog'liqligi
emas. `tomllib` stdlib'da bor, ya'ni bu yerda uni ishlatish MUMKIN edi —
lekin `uv.lock` ning `[[package]]` sxemasi `uv` ning ICHKI formati va u
versiyalar orasida o'zgarishi mumkin. Matn skani esa formatdan mustaqil:
u «bu nomdagi paket lockda umuman uchraydimi?» degan eng qo'pol va eng
ishonchli savolga javob beradi.
"""


def _parse_manifest(path: Path) -> dict[str, Any]:
    """Manifestni o'qiydi; YO'Q bo'lsa xato matni AYNAN yetishmayotgan faylni nomlaydi.

    ⚠ BIRINCHI COMMIT'DA AYNAN SHU YERDA YIQILADI va bu KUTILGAN holat
      (modul docstringining birinchi bloki). Xabar «nima qilish kerak» ni
      aytadi, chunki qizil turgan test ijrochiga yo'l ko'rsatmasa, uni
      o'chirish vasvasasi tug'iladi.
    """
    if not path.is_file():
        pytest.fail(
            f"`{path.relative_to(REPO_ROOT)}` topilmadi.\n"
            "Bu darvoza `cv-service` ning bog'liqlik to'plamidan OLDIN yoziladi "
            "(W0-1): `rfdetr` `torch` ni MAJBURIY tortadi (D-04), ya'ni "
            "manifestdan keyin qo'yilgan devor allaqachon sodir bo'lgan ishni "
            "tasdiqlagan bo'lardi. Manifest 05-02/Task 2 da tug'iladi va shu "
            "test o'shanda yashil bo'ladi — TESTNI O'CHIRMANG."
        )
    data: dict[str, Any] = tomllib.loads(path.read_text(encoding="utf-8"))
    return data


@pytest.fixture(scope="module")
def cv_manifest() -> dict[str, Any]:
    return _parse_manifest(CV_SERVICE_PYPROJECT)


@pytest.fixture(scope="module")
def cv_runtime_packages(cv_manifest: dict[str, Any]) -> set[str]:
    """`uv sync --frozen --no-dev` o'rnatadigan paketlar."""
    return {_requirement_name(spec) for spec in cv_manifest["project"]["dependencies"]}


@pytest.fixture(scope="module")
def cv_dev_packages(cv_manifest: dict[str, Any]) -> set[str]:
    """FAQAT `dev` guruhidagi paketlar — runtime image'ga tushmaydi."""
    return {_requirement_name(spec) for spec in cv_manifest["dependency-groups"]["dev"]}


@pytest.fixture(scope="module")
def lock_package_names() -> set[str]:
    """`uv.lock` dagi HAR BIR paket blokining nomi (PEP 503 normallashtirilgan)."""
    if not CV_SERVICE_LOCK.is_file():
        pytest.fail(
            f"`{CV_SERVICE_LOCK.relative_to(REPO_ROOT)}` topilmadi — "
            "`uv lock --project services/cv-service` bilan hosil qilinadi "
            "(05-02/Task 2). Lock QATLAMI manifestdan KUCHLIROQ: `rfdetr-plus` "
            "manifestda HECH QACHON ko'rinmaydi, u faqat `[plus]` ekstrasi "
            "orqali TRANZITIV keladi (D-03)."
        )
    text = CV_SERVICE_LOCK.read_text(encoding="utf-8")
    return {
        name.lower().replace("_", "-").replace(".", "-")
        for name in _LOCK_PACKAGE_NAME.findall(text)
    }


# --------------------------------------------------------------------------
# (1) MANIFEST QATLAMI
# --------------------------------------------------------------------------


@pytest.mark.parametrize("package", sorted(REQUIRED_RUNTIME_PACKAGES))
def test_production_package_is_a_project_dependency(
    package: str, cv_runtime_packages: set[str]
) -> None:
    """Prod kodidan chaqiriladigan paket `[project] dependencies` da.

    `test_runtime_deps.py::test_production_package_is_a_project_dependency`
    ning aynan takrori va sabab ham aynan o'sha: butun `cv-tests` to'plami
    `dev` target'da ishlaydi, ya'ni `dev` guruhida qolib ketgan modul
    testlarda BOR bo'lib, ishlab chiqarish image'ida YO'Q bo'lardi.
    """
    assert package in cv_runtime_packages, (
        f"`{package}` `services/cv-service/pyproject.toml` ning `[project] "
        "dependencies` bo'limida yo'q — u ishlab chiqarish kodidan "
        "chaqiriladi, ya'ni `uv sync --frozen --no-dev` bilan qurilgan "
        "runtime image'da `ModuleNotFoundError` beradi. Testlar bu xatoni "
        "KO'RMAYDI: ular `dev` target'da ishlaydi."
    )


@pytest.mark.parametrize("package", sorted(FORBIDDEN_PACKAGES))
def test_forbidden_package_is_absent_from_both_groups(
    package: str, cv_runtime_packages: set[str], cv_dev_packages: set[str]
) -> None:
    """Taqiqlangan paket IKKALA guruhda ham yo'q (T-05-05).

    `dev` guruhi ham qamraladi va bu ATAYIN: `uv add --dev rfdetr` ham
    `uv.lock` ni qayta hal qiladi va `torch` ni AYNAN o'sha tarzda ichkariga
    kiritardi. Guruh farqi hech nimani yumshatmaydi — LOCK BITTA.
    """
    assert package not in cv_runtime_packages | cv_dev_packages, (
        f"`{package}` `cv-service` bog'liqliklariga qo'shilgan — u shu "
        "faylning `FORBIDDEN_PACKAGES` ro'yxatida va sabab o'sha yerda "
        "yozilgan. `rfdetr` uchun sabab D-04: `torch` uning ekstrasi emas, "
        "MAJBURIY bog'liqligi."
    )


def test_manifest_actually_parsed(cv_runtime_packages: set[str], cv_dev_packages: set[str]) -> None:
    """QUYI CHEGARA: bo'sh to'plamda yuqoridagi «yo'q» testlari jimgina o'tardi.

    `test_runtime_deps.py:291-302` bilan aynan bir xil qaror. Nazorat
    qiymati — `onnxruntime`: u bu servisning MAVJUD BO'LISH sababi, ya'ni
    parser haqiqatan manifestni o'qiyotganining eng ishonchli belgisi.
    """
    assert len(cv_runtime_packages) >= 15, (
        f"`cv-service` prod bog'liqliklari juda kam: {sorted(cv_runtime_packages)}"
    )
    assert len(cv_dev_packages) >= 4, (
        f"`cv-service` dev bog'liqliklari juda kam: {sorted(cv_dev_packages)}"
    )
    assert "onnxruntime" in cv_runtime_packages


# --------------------------------------------------------------------------
# (2) LOCKFILE QATLAMI — TRANZITIV TORTISHNI HAM KO'RADI
# --------------------------------------------------------------------------


@pytest.mark.parametrize("package", LOCK_FORBIDDEN_NAMES)
def test_forbidden_package_is_absent_from_the_lockfile(
    package: str, lock_package_names: set[str]
) -> None:
    """Hal qilingan grafda paket UMUMAN yo'q (D-03 — litsenziya lockfile invarianti).

    ⚠ BU QATLAM MANIFESTDAN KUCHLIROQ. `rfdetr-plus` manifestda hech qachon
      yozilmaydi: u `rfdetr[plus]` ekstrasi orqali keladi, ya'ni (1)-qatlam
      uni printsipial ravishda ko'ra olmaydi. Lock esa butun grafni yozadi.
    """
    assert package not in lock_package_names, (
        f"`{package}` `services/cv-service/uv.lock` da mavjud — ya'ni u "
        "bog'liqlik grafiga (ehtimol TRANZITIV, ekstra orqali) kirib qolgan. "
        "`rfdetr-plus` — PML 1.0, `ultralytics` — AGPL-3.0, `torch` — ~800 MB "
        "ishlab chiqarish image'ida. Yechim: ekstrani olib tashlash, "
        "keyin `uv lock --project services/cv-service`."
    )


def test_lockfile_actually_scanned(lock_package_names: set[str]) -> None:
    """QUYI CHEGARA: regex mos kelmasa yuqoridagi da'volar bo'sh to'plamda o'tardi.

    `uv.lock` formati o'zgarib `name = "..."` shakli yo'qolsa, skaner BO'SH
    to'plam qaytarardi va «rfdetr-plus yo'q» da'vosi hech nimani
    o'lchamasdi. Chegara QUYI va u INLINE literal — `test_runtime_deps.py::
    test_manifest_actually_parsed` bilan aynan bir xil shakl.
    """
    assert len(lock_package_names) >= 30, (
        f"`uv.lock` dan faqat {len(lock_package_names)} paket nomi o'qildi, "
        "kamida 30 kutilgan — lock skaneri buzilgan va taqiq da'volari "
        "isbotsiz qolardi"
    )
    # Nazorat qiymatlari: ikkalasi ham `cv-service` ning MAVJUD BO'LISH sababi.
    assert {"onnxruntime", "supervision"} <= lock_package_names


# --------------------------------------------------------------------------
# (3) O'RNATILGAN METADATA QATLAMI — RO'YXAT EMAS, PREDIKAT (§S-10)
# --------------------------------------------------------------------------


def _license_tokens(dist: Distribution) -> list[str]:
    """Distributivning litsenziya haqidagi HAMMA e'loni — kichik harfda.

    Uch manba o'qiladi, chunki ekotizim uchalasidan ham foydalanadi:

      `License-Expression`  — PEP 639 (yangi, SPDX ifodasi)
      `License`             — eski erkin matn maydoni
      `Classifier: License ::` — Trove klassifikatorlari

    Faqat bittasini o'qish darvozani jimgina bo'shatardi: `rfdetr-plus`
    o'z shartlarini `license_expression` da e'lon qiladi, `ultralytics` esa
    klassifikatorda.
    """
    metadata = dist.metadata
    tokens: list[str] = []
    for field in (LICENSE_EXPRESSION_FIELD, LICENSE_FIELD):
        tokens.extend(str(value).lower() for value in metadata.get_all(field) or ())
    tokens.extend(
        str(value).lower()
        for value in metadata.get_all(CLASSIFIER_FIELD) or ()
        if str(value).startswith(LICENSE_CLASSIFIER_PREFIX)
    )
    return tokens


@pytest.fixture(scope="module")
def dists() -> list[Distribution]:
    """Shu jarayonning muhitidagi HAMMA distributiv (root `tests` konteyneri)."""
    return list(distributions())


def test_metadata_scan_actually_sees_the_environment(dists: list[Distribution]) -> None:
    """QUYI CHEGARA — BO'SH TO'PLAMDA QUYIDAGI IKKI DARVOZA JIMGINA O'TARDI.

    `importlib.metadata.distributions()` `sys.path` ga tayanadi va noto'g'ri
    muhitda bo'sh iterator qaytarishi mumkin. O'shanda «birorta AGPL paket
    yo'q» da'vosi ROST, lekin MA'NOSIZ bo'lardi.

    Chegara INLINE literal (`test_runtime_deps.py:298` shakli) va u QUYI:
    o'lchangan holat 2026-08-08 da 97 distributiv, ya'ni yangi paket
    qo'shilganda bu son qayta ko'rib chiqilmaydi.
    """
    assert len(dists) >= 30, (
        f"muhitdan faqat {len(dists)} distributiv topildi, kamida 30 "
        "kutilgan — metadata skaneri bo'sh to'plamda ishlayapti"
    )


def test_no_non_osi_licenseref_distribution_is_installed(dists: list[Distribution]) -> None:
    """`LicenseRef-*` — SPDX reyestrida YO'Q, ya'ni OSI tasdiqlamagan shartlar.

    ⚠ NOM RO'YXATI EMAS: darvoza `rfdetr-plus` ni bilmaydi va bilishi ham
      kerak emas (§S-10). Kelajakda kelib tushadigan NOMA'LUM proprietar
      distributiv ham aynan shu prefiks bilan e'lon qiladi.
    """
    offenders = sorted(
        f"{dist.metadata['Name']} ({token})"
        for dist in dists
        for token in _license_tokens(dist)
        if LICENSE_REF_PREFIX in token
    )
    assert not offenders, (
        f"OSI tasdiqlamagan litsenziyali distributiv o'rnatilgan: {offenders}. "
        "`LicenseRef-*` — SPDX reyestrida yo'q ifoda, ya'ni shartlarni "
        "ODAM o'qishi kerak. CLAUDE.md loyiha uchun faqat Apache-2.0/MIT "
        "sinfidagi litsenziyalarga ruxsat beradi (PML 1.0 — TAQIQ)."
    )


def test_no_agpl_distribution_is_installed(dists: list[Distribution]) -> None:
    """AGPL tarmoq xizmatida manba oshkor qilishni talab qiladi — tijoriy SaaS uchun TAQIQ.

    `ultralytics` bu sinfning eng ehtimolli yo'li: `supervision` ning rasmiy
    «occupancy analytics» misoli aynan uni import qiladi (§4.2, Tuzoq 3).

    ⚠ IKKI BELGI QIDIRILADI VA IKKALASI HAM KERAK: SPDX ifodasi `AGPL-3.0`
      deydi, Trove klassifikatori esa «GNU Affero General Public License v3»
      — ya'ni bittasiga tayanish ikkinchi shaklni jimgina o'tkazib yubordi.
    """
    offenders = sorted(
        f"{dist.metadata['Name']} ({token})"
        for dist in dists
        for token in _license_tokens(dist)
        if AGPL_MARKER in token or AGPL_CLASSIFIER_MARKER in token
    )
    assert not offenders, (
        f"AGPL litsenziyali distributiv o'rnatilgan: {offenders}. AGPL-3.0 "
        "tarmoq orqali xizmat ko'rsatishda manba oshkor qilishni yoki pullik "
        "litsenziyani talab qiladi — CLAUDE.md ning QAT'IY taqig'i."
    )
