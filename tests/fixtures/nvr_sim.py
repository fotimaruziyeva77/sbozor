"""`nvr-sim` ga yo'naltiruvchi fixture'lar (CAM-09).

=============================================================================
`pytest.skip` — O'YLAB QILINGAN XAVF, VA U SHU YERDA CHEKLANADI.

`skip` testni JIMGINA o'tkazib yuboradi. Agar sim testlari CI'da skip
bo'lsa, SC#7 ning «CI'da o'lchanadi» da'vosi isbotsiz qoladi va hech kim
buni sezmaydi: chiqish yashil, sanoq esa nolga tushib ketgan bo'ladi
(T-03-10, Repudiation).

Shuning uchun qoida:
    CI YO'Q   -> `skip`  (dev mashinasida `--profile sim` ko'tarilmagan
                          bo'lishi mumkin; bu normal ish oqimi)
    CI BOR    -> `fail`  (CI'da sim KO'TARILGAN bo'lishi SHART)

⚠ Ikkinchi, nozikroq holat: `NVR_SIM_BASE_URL` compose tomonidan HAR DOIM
beriladi (`tests` konteyneri muhitida), ya'ni "o'zgaruvchi yo'q" holati
amalda deyarli uchramaydi. Haqiqiy xavf — o'zgaruvchi BOR, konteyner esa
ko'tarilmagan. Shuning uchun fixture manzilni shunchaki o'qimaydi, balki
uni ZONDLAYDI va bir xil skip/fail qoidasini qo'llaydi.
=============================================================================

`ASGITransport` bu qatlamda ISHLATILMAYDI. `tests/conftest.py` dagi
`api_client` ilovaning O'ZIGA to'g'ridan-to'g'ri boradi va tarmoqni chetlab
o'tadi — bu boshqa maqsad uchun to'g'ri vosita, lekin Digest handshake
umuman bajarilmaydi. Sim testlari HAQIQIY TCP talab qiladi.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from typing import Any

import httpx
import pytest

DEFAULT_TIMEOUT = httpx.Timeout(10.0, connect=5.0)
"""`None` (cheksiz) HECH QACHON — osilib qolgan test butun to'plamni bloklaydi (A.3)."""

_PROBE_TIMEOUT = httpx.Timeout(3.0, connect=2.0)

SIM_MISSING_HINT = (
    "nvr-sim ishlamayapti. Ishga tushirish: "
    "`docker compose --profile sim up -d nvr-sim go2rtc-sim --wait` "
    "yoki to'liq zanjir bilan `npm run test:sim`."
)


def _unavailable(reason: str) -> None:
    """CI'da `fail`, dev'da `skip` — T-03-10 ning yagona mexanizmi."""
    message = f"{reason} {SIM_MISSING_HINT}"
    if os.environ.get("CI"):
        pytest.fail(
            f"{message} CI'da sim testlari SKIP BO'LA OLMAYDI: "
            "aks holda SC#7 ning «CI'da o'lchanadi» da'vosi isbotsiz qolardi."
        )
    pytest.skip(message)


@pytest.fixture(scope="session")
def sim_url() -> str:
    """Sim'ning bazaviy manzili — zondlangan, shunchaki muhitdan o'qilgan emas."""
    url = os.environ.get("NVR_SIM_BASE_URL")
    if not url:
        _unavailable("`NVR_SIM_BASE_URL` o'rnatilmagan.")
        raise AssertionError("unreachable")  # pragma: no cover - `_unavailable` chiqadi

    url = url.rstrip("/")
    try:
        with httpx.Client(timeout=_PROBE_TIMEOUT) as client:
            response = client.get(f"{url}/__sim__/state")
        response.raise_for_status()
    except httpx.HTTPError as exc:
        _unavailable(f"`{url}` ga yetib bo'lmadi ({type(exc).__name__}).")
        raise AssertionError("unreachable") from exc  # pragma: no cover

    return url


@pytest.fixture(scope="session")
def sim_credentials() -> tuple[str, str]:
    """Sim rekvizitlari — `nvr-sim` konteyneri bilan BIR XIL muhitdan.

    Ular sir emas: sim test uskunasi. Real rejimga o'tish aynan shu ikki
    qiymatning bazadagi (Fernet bilan shifrlangan) boshqa qiymatga almashishi
    bilan bo'ladi — KOD O'ZGARMAYDI.
    """
    return os.environ.get("SIM_USERNAME", "admin"), os.environ.get("SIM_PASSWORD", "Sim12345")


def sim_state(url: str) -> dict[str, Any]:
    """`GET /__sim__/state` — joriy holat."""
    with httpx.Client(timeout=DEFAULT_TIMEOUT) as client:
        response = client.get(f"{url}/__sim__/state")
    response.raise_for_status()
    data: dict[str, Any] = response.json()
    return data


def sim_patch(url: str, **fields: Any) -> dict[str, Any]:
    """`POST /__sim__/state` — QISMAN yangilash.

    Noma'lum maydon yoki rejim `400` beradi va bu yerda istisnoga aylanadi:
    "rejimni o'rnatdim deb o'ylab, aslida hech nima o'zgarmagan" holati
    testda KO'RINISHI kerak.
    """
    with httpx.Client(timeout=DEFAULT_TIMEOUT) as client:
        response = client.post(f"{url}/__sim__/state", json=fields)
    response.raise_for_status()
    data: dict[str, Any] = response.json()
    return data


def sim_mode(url: str, mode: str, **fields: Any) -> dict[str, Any]:
    """`sim_mode(url, "clock_drift", drift_seconds=420)` — B.8 rejimlarini o'rnatadi."""
    return sim_patch(url, mode=mode, **fields)


def sim_reset(url: str) -> dict[str, Any]:
    """`POST /__sim__/reset` — standart holat + sanagichlar NOLGA.

    ⚠ Sanagichlarni nollash — bu fixture'ning eng muhim ishi. Usiz
    `stream_claims` va `auth_attempts` testlar orasida meros bo'lib qolardi va
    `stream_limit=4` testi oldingi testdan qolgan da'volar bilan boshlanardi.
    """
    with httpx.Client(timeout=DEFAULT_TIMEOUT) as client:
        response = client.post(f"{url}/__sim__/reset")
    response.raise_for_status()
    data: dict[str, Any] = response.json()
    return data


def sim_attempts(url: str) -> int:
    """`GET /__sim__/attempts` — D-03 ning o'lchov vositasi (`401` da retry YO'Q)."""
    with httpx.Client(timeout=DEFAULT_TIMEOUT) as client:
        response = client.get(f"{url}/__sim__/attempts")
    response.raise_for_status()
    count: int = response.json()["auth_attempts"]
    return count


@pytest.fixture
def sim(sim_url: str) -> Iterator[str]:
    """Toza holatdagi sim: test OLDIDAN ham, KEYIN ham `reset`.

    Ikki tomonlama: oldingi test yiqilib tozalamagan bo'lsa ham bu test toza
    holatdan boshlaydi, va bu test yiqilsa ham keyingisi toza holat oladi.
    """
    sim_reset(sim_url)
    try:
        yield sim_url
    finally:
        sim_reset(sim_url)
