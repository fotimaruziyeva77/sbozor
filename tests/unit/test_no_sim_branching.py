"""Sim ILOVA KODIGA siza olmasligining darvozasi (CAM-09, T-03-07 / B.9).

=============================================================================
QOIDA: ILOVA UCHUN SIM — BU SHUNCHAKI BAZADAGI BIR QATOR.

    `nvr_devices.host = "nvr-sim"` — bu sozlama.
    `if host == "nvr-sim": ...`    — bu YOLG'ON.

CAM-09 ning yakuniy da'vosi shu: real qurilmaga o'tish — **sozlama
o'zgarishi, kod o'zgarishi emas**.

| Nima          | Sim rejimi                | Real rejim              |
|---------------|---------------------------|-------------------------|
| NVR manzili   | `nvr-sim:8080` (bazada)   | `10.10.0.5:80`          |
| Login/parol   | bazada, Fernet bilan      | real rekvizit           |
| RTSP hosti    | `adminAccesses` javobidan | `adminAccesses` javobidan |
| **Kod farqi** | **YO'Q**                  | **YO'Q**                |

Agar sim uchun birorta tarmoqlanish `services/core-api/app/` ga sizib kirsa,
bu jadvalning oxirgi qatori **yolg'onga aylanadi** va buni faqat real
qurilmada, Karmanada, ish paytida bilib olardik.

Naqsh manbai: `tests/integration/test_rate_limit_proxy.py` dagi grep-darvoza —
konfiguratsiya/kod matnini o'qib TAQIQLANGAN satrni izlaydi.
=============================================================================
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
APP_ROOT = REPO_ROOT / "services" / "core-api" / "app"

FORBIDDEN_MARKERS = ("nvr-sim", "__sim__", "SIM_")
"""Sim'ning uchta imzosi: konteyner nomi, control-plane prefiksi, muhit prefiksi.

Uchalasi ham `services/core-api/app/` da UCHRAMASLIGI kerak. Ular
`compose.yaml` da, `tests/` da va `services/nvr-sim/` da bo'lishi — normal.
"""

MIN_SCANNED_FILES = 20
"""Darvozaning QUYI CHEGARASI.

Usiz yo'l noto'g'ri yozilganda (yoki katalog ko'chirilganda) skaner BO'SH
to'plamda ishlab, hamma "yo'q" assert'i jimgina o'tib ketardi va darvoza
o'z mavjudligini yo'qotgan holda yashil bo'lib turaverardi. Bu 03-01 da
o'rnatilgan qoida: har manifest/skaner darvozasining quyi chegarasi majburiy.
"""


def _python_sources() -> list[Path]:
    return sorted(APP_ROOT.rglob("*.py"))


SOURCES = _python_sources()


def test_app_tree_is_actually_scanned() -> None:
    """Quyi chegara: skaner bo'sh to'plamda ishlayotgan bo'lsa darvoza YO'Q."""
    assert APP_ROOT.is_dir(), f"`{APP_ROOT}` katalogi topilmadi — yo'l eskirgan"
    assert len(SOURCES) >= MIN_SCANNED_FILES, (
        f"faqat {len(SOURCES)} ta `.py` topildi (`{APP_ROOT}`), kamida "
        f"{MIN_SCANNED_FILES} kutilgan. Bo'sh to'plamda bu darvoza JIMGINA "
        "yashil bo'lardi."
    )


@pytest.mark.parametrize("marker", FORBIDDEN_MARKERS)
def test_application_code_has_no_simulator_branching(marker: str) -> None:
    """`services/core-api/app/` da sim uchun birorta tarmoqlanish yo'q."""
    hits: list[str] = []
    for source in SOURCES:
        for lineno, line in enumerate(source.read_text(encoding="utf-8").splitlines(), start=1):
            if marker in line:
                relative = source.relative_to(REPO_ROOT).as_posix()
                hits.append(f"{relative}:{lineno}: {line.strip()}")

    assert not hits, (
        f"ilova kodida sim satri {marker!r} topildi:\n  "
        + "\n  ".join(hits)
        + "\n\nIlova uchun sim — bu bazadagi bir qator (`nvr_devices.host`), kodda esa u "
        "umuman mavjud emas. Aks holda «real qurilmaga o'tish — sozlama o'zgarishi» "
        "da'vosi (SC#7) yolg'onga aylanadi."
    )


def test_gate_detects_a_planted_marker(tmp_path: Path) -> None:
    """Darvozaning O'ZI ishlashini isbotlaydi — bugun yashil bo'lgani uchun.

    Bu darvoza loyihasi bo'yicha HAR DOIM yashil bo'lishi kerak, ya'ni
    «yashil» uning haqiqatan qidirayotganini isbotlamaydi. Shuning uchun
    skaner mantig'i ATAYIN EKILGAN satr ustida alohida o'lchanadi.
    """
    planted = tmp_path / "settings.py"
    planted.write_text('SIM_MODE = "ok"\n', encoding="utf-8")

    found = [
        f"{planted.name}:{lineno}"
        for lineno, line in enumerate(planted.read_text(encoding="utf-8").splitlines(), start=1)
        for marker in FORBIDDEN_MARKERS
        if marker in line
    ]
    assert found == ["settings.py:1"], f"skaner ekilgan satrni topmadi: {found}"
