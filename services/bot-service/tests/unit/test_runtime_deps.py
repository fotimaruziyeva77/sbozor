"""D-08/1 ning MEXANIK darvozasi — bot bazani, navbatni va `sbozor-core` ni KO'RMAYDI.

=============================================================================
NEGA BU TEST BOR VA NEGA IZOH YETMAYDI.

`services/bot-service/pyproject.toml` taqiq ro'yxatini SABAB bilan yozgan.
Lekin izoh darvoza EMAS: keyingi rejaning ijrochisi «sotuvchi ismini
olish uchun bitta `SELECT` yozsam bo'ladi» deb `uv add sqlalchemy asyncpg`
qilishi mumkin va o'sha commit code review'dan o'tib ketishi mumkin —
chunki u ISHLAYDI.

Buzilish esa DARHOL ko'rinmaydi: u loyihaning tenant izolyatsiyasi
kafolatiga tegadi. `core-api` da RLS bir marta o'lchangan (`tests/tenancy`),
ikkinchi baza yuzasi esa uni IKKINCHI MARTA isbotlashni talab qilardi — va
bu yuza Telegram'dan kelgan AUTENTIFIKATSIYA QILINMAGAN oqim ostida
turadi (T-07-01, birinchi marta loyihada).

=============================================================================
⚠⚠ DARVOZA IKKI QATLAMLI VA IKKALASI HAM KERAK.

  (1) METADATA  — `importlib.metadata.distribution(...)`. Bu qatlam
                  paket O'RNATILGANINI ko'radi, hatto uni hech kim
                  import qilmasa ham. `uv add` ning oqibati aynan shu
                  yerda ko'rinadi.

  (2) XULQ      — haqiqiy `import`. Bu qatlam (1) ni DUBLIKAT qilmaydi:
                  distributiv nomi (`sqlalchemy`) va modul nomi har doim
                  ham bir xil bo'lmaydi, va tranzitiv tarzda kelgan paket
                  metadatada boshqa nom ostida turishi mumkin.

`tests/unit/test_runtime_deps.py` (repo ildizi) MANIFESTNI o'qiydi va
sabab o'sha faylda yozilgan: import u yerda har doim muvaffaqiyatli
bo'ladi. BU YERDA teskari: biz aynan SHU KONTEYNERNING muhitini
o'lchayapmiz, ya'ni `uv.lock` haqiqatda nima o'rnatganini.
=============================================================================
"""

from __future__ import annotations

import importlib
import importlib.metadata as md
from typing import Final

import pytest

FORBIDDEN_DISTRIBUTIONS: Final[tuple[str, ...]] = (
    # D-08/1: baza ulanishi IKKINCHI RLS yuzasini ochardi (T-07-01).
    "sqlalchemy",
    "asyncpg",
    # Bot JOB BAJARMAYDI — u faqat KIRUVCHI oqimni qabul qiladi.
    # Jo'natish `worker` ning `notify.outbox_tick` ida qoladi (DQ-2);
    # ikkinchi orkestratsiya mexanizmi tug'ilmaydi.
    "taskiq",
    "taskiq-redis",
    # ⛔ E.164 normalizatsiyasi `core-api` DA (D-25). Ikki joyda
    # normallashtirish ikki xil natija bergan kunda bog'lanish JIMGINA
    # buzilardi: bot bir shaklni yozardi, server boshqasini izlardi.
    "phonenumbers",
    # ⚠ VASVASA ENG KATTA BAND: unda enumlar va pul turi bor. Lekin u
    # `models/` orqali SQLAlchemy'ni TORTADI va yuqoridagi ikki taqiqni
    # BILVOSITA buzardi.
    "sbozor-core",
    # AGPL-3.0 — CLAUDE.md ning QAT'IY taqig'i. Bu servisda CV kodi yo'q,
    # lekin taqiq UCHALA muhitda ham bir xil bo'lishi kerak.
    "ultralytics",
)

FORBIDDEN_MODULES: Final[tuple[str, ...]] = ("sqlalchemy", "asyncpg", "taskiq", "phonenumbers")
"""(2)-QATLAM: haqiqiy `import` bilan o'lchanadigan modullar.

⚠ Ro'yxat `FORBIDDEN_DISTRIBUTIONS` dan QISQAROQ va bu ATAYIN: `sbozor-core`
  ning modul nomi `sbozor_core`, `taskiq-redis` niki `taskiq_redis` — ya'ni
  distributiv nomi bilan modul nomi HAR DOIM ham bir xil emas. Bu yerga
  faqat ikkalasi bir xil bo'lgan (yoki bosh paket) nomlar kiradi; qolganini
  (1)-qatlam qamraydi.
"""

EXPECTED_PINS: Final[dict[str, str]] = {
    # ⛔ `redis` MAJORI `7.` — VA BU DARVOZANING ENG QIMMAT SATRI.
    #    `core-api` `redis[hiredis]==8.0.1` ga qadalgan, `aiogram 3.30` esa
    #    `<8` talab qiladi. `8.` ga «yangilash» bu servisni ISHLAMAY
    #    qo'yardi yoki (battari) `core-api` ning pinini pastga tortardi —
    #    bu `arq` darsining aynan takrori (D-06, T-07-05).
    "redis": "7.",
    "aiogram": "3.30.0",
    "pydantic": "2.13.4",
}

LICENSE_REF_PREFIX: Final = "licenseref-"
AGPL_MARKERS: Final[tuple[str, ...]] = ("agpl", "affero")

LICENSE_FIELDS: Final[tuple[str, ...]] = ("License-Expression", "License")
CLASSIFIER_FIELD: Final = "Classifier"
LICENSE_CLASSIFIER_PREFIX: Final = "License ::"
MAX_IDENTIFIER_LENGTH: Final = 100
"""Eski `License` maydoni FAQAT shu uzunlikkacha IDENTIFIKATOR deb o'qiladi.

Sabab `tests/unit/test_license_fence.py` da O'LCHANGAN (2026-08-08): ba'zi
paketlar bu maydonga BUTUN LITSENZIYA MATNINI yozadi va matn ichida boshqa
litsenziyalarning nomi uchrashi normal — uni identifikator deb o'qish
YOLG'ON-QIZIL berardi, yolg'on-qizil esa darvozani o'chirish bosimini.
"""

MIN_INSTALLED_DISTRIBUTIONS: Final = 20
"""QUYI CHEGARA: bo'sh muhitda quyidagi «yo'q» da'volari jimgina o'tardi."""


@pytest.mark.parametrize("distribution", FORBIDDEN_DISTRIBUTIONS)
def test_forbidden_distribution_is_not_installed(distribution: str) -> None:
    """(1)-QATLAM: taqiqlangan paket bu muhitda UMUMAN o'rnatilmagan."""
    with pytest.raises(md.PackageNotFoundError):
        md.distribution(distribution)


@pytest.mark.parametrize("module_name", FORBIDDEN_MODULES)
def test_forbidden_module_cannot_be_imported(module_name: str) -> None:
    """(2)-QATLAM: XULQIY o'lchov — modul haqiqatan import qilinmaydi.

    ⚠ Bu (1) ning dublikati EMAS: paket tranzitiv tarzda boshqa
      distributiv nomi ostida kelib, moduli baribir import qilinadigan
      bo'lishi mumkin edi.
    """
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module(module_name)


@pytest.mark.parametrize(("distribution", "expected_prefix"), sorted(EXPECTED_PINS.items()))
def test_pin_did_not_drift(distribution: str, expected_prefix: str) -> None:
    """Pinlar `pyproject.toml` da yozilgan qiymatda QOLGAN.

    ⛔ `redis` uchun bu «tartib» emas, TO'QNASHUV DARVOZASI: `8.` ga
       ko'tarilish `aiogram` ning `<8` shiftini buzadi va servis ishga
       tushishda emas, BIRINCHI FSM yozuvida yiqilardi.
    """
    installed = md.version(distribution)
    assert installed.startswith(expected_prefix), (
        f"`{distribution}` versiyasi `{installed}` — kutilgan boshlanish "
        f"`{expected_prefix}`. Pin siljigan bo'lsa sabab `uv.lock` ni qayta hal "
        "qilgan buyruqda; `redis` uchun bu `core-api` bilan TO'QNASHUV belgisi "
        "(D-06/T-07-05, `pyproject.toml` izohi)."
    )


def _license_tokens(dist: md.Distribution) -> list[str]:
    """Distributivning litsenziya haqidagi HAMMA e'loni — kichik harfda."""
    metadata = dist.metadata
    tokens: list[str] = []
    for field in LICENSE_FIELDS:
        tokens.extend(
            str(value).lower()
            for value in metadata.get_all(field) or ()
            if len(str(value)) <= MAX_IDENTIFIER_LENGTH and "\n" not in str(value)
        )
    tokens.extend(
        str(value).lower()
        for value in metadata.get_all(CLASSIFIER_FIELD) or ()
        if str(value).startswith(LICENSE_CLASSIFIER_PREFIX)
    )
    return tokens


@pytest.fixture(scope="module")
def installed_distributions() -> list[md.Distribution]:
    return list(md.distributions())


def test_metadata_scan_actually_sees_the_environment(
    installed_distributions: list[md.Distribution],
) -> None:
    """QUYI CHEGARA — BO'SH TO'PLAMDA QUYIDAGI IKKI DARVOZA JIMGINA O'TARDI."""
    assert len(installed_distributions) >= MIN_INSTALLED_DISTRIBUTIONS, (
        f"muhitdan faqat {len(installed_distributions)} distributiv topildi, kamida "
        f"{MIN_INSTALLED_DISTRIBUTIONS} kutilgan — skaner bo'sh to'plamda ishlayapti"
    )


def test_no_non_osi_licenseref_distribution_is_installed(
    installed_distributions: list[md.Distribution],
) -> None:
    """`LicenseRef-*` — SPDX reyestrida YO'Q, ya'ni OSI tasdiqlamagan shartlar.

    ⚠ NOM RO'YXATI EMAS, PREDIKAT (§S-10): darvoza kelajakdagi NOMA'LUM
      proprietar distributivni ham ushlaydi.
    """
    offenders = sorted(
        f"{dist.metadata['Name']} ({token})"
        for dist in installed_distributions
        for token in _license_tokens(dist)
        if LICENSE_REF_PREFIX in token
    )
    assert not offenders, (
        f"OSI tasdiqlamagan litsenziyali distributiv o'rnatilgan: {offenders}. "
        "CLAUDE.md loyiha uchun faqat Apache-2.0/MIT sinfidagi litsenziyalarga "
        "ruxsat beradi."
    )


def test_no_agpl_distribution_is_installed(
    installed_distributions: list[md.Distribution],
) -> None:
    """AGPL tarmoq xizmatida manba oshkor qilishni talab qiladi — tijoriy SaaS uchun TAQIQ.

    ⚠ IKKI BELGI QIDIRILADI VA IKKALASI HAM KERAK: SPDX ifodasi `AGPL-3.0`
      deydi, Trove klassifikatori esa «GNU Affero General Public License v3».
    """
    offenders = sorted(
        f"{dist.metadata['Name']} ({token})"
        for dist in installed_distributions
        for token in _license_tokens(dist)
        if any(marker in token for marker in AGPL_MARKERS)
    )
    assert not offenders, (
        f"AGPL litsenziyali distributiv o'rnatilgan: {offenders}. AGPL-3.0 tarmoq "
        "orqali xizmat ko'rsatishda manba oshkor qilishni yoki pullik litsenziyani "
        "talab qiladi — CLAUDE.md ning QAT'IY taqig'i."
    )
