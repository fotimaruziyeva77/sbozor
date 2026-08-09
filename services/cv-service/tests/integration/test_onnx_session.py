"""HAQIQIY ONNX artefakti bilan sessiya — MOCK'SIZ O'LCHOV (§S-14, `model` marker).

=============================================================================
⚠⚠ BU TESTDA `skipif` YO'Q VA U ATAYIN YO'Q.

Artefakt (`ops/models/rfdetr-large.onnx`) topilmasa bu test **YIQILADI**,
jimgina o'tib ketmaydi. Sabab to'g'ridan-to'g'ri: `skip` «o'lchov
bajarildi» degan YOLG'ON signalni beradi — natija yashil ko'rinadi va
hech kim inference yo'li hech qachon ishga tushmaganini bilmaydi. Bu
03-14 va 04-12 nosozliklarining aynan shakli.

Marker esa fazani BLOKLAMAYDI: `pyproject.toml` da
`addopts = -m "not model"`, ya'ni standart zanjir bu faylni yig'maydi.
Uni ishga tushirish OCHIQ va qo'lda:

    docker compose --profile test run --rm cv-tests pytest -m model

⚠ Bu — `05-HUMAN-UAT` bandi: artefaktni `ops` qo'yadi
  (`ops/models/README.md`), keyin bu buyruq yuritiladi.

=============================================================================
BU TEST NIMANI O'LCHAYDI VA NIMANI O'LCHAMAYDI.

✅ O'LCHAYDI: sessiya HAQIQIY fayldan quriladi; graf kontrakti (kirish
   nomi, chiqishlar soni, statik rezolyutsiya) haqiqatan shunday;
   bir xil kirish -> BAYT-BAYT bir xil chiqish.

❌ O'LCHAMAYDI: modelning ANIQLIGI. Kirish kadri — sintetik tasvir, va
   undan chiqadigan detektsiyalar HECH NIMANI anglatmaydi. Aniqlik
   savoli oltin to'plamga tegishli (W0-9) va u UXLAB YOTADI (D-01).
   ⚠ BU TESTNING YASHILLIGINI «model ishlayapti» deb o'qish TAQIQLANADI.

❌ O'LCHAMAYDI: rezolyutsiyaning AYNIQ SONI to'g'rimi. Quyida
   `test_...resolution...` grafning O'ZI aytgan qiymat bilan bizning
   o'qishimiz mos kelishini tekshiradi — ya'ni «kod grafdan o'qiydimi?»
   degan savolni. «704 to'g'rimi?» degan savol variantga tegishli va
   uning javobi artefakt bilan birga keladi; test uni QATTIQ YOZIB
   qo'ysa, boshqa variantga o'tish darvozani yolg'on-qizil qilardi.
=============================================================================
"""

from __future__ import annotations

import inspect
import os
import sys
from pathlib import Path
from types import ModuleType
from typing import Final

import cv2
import numpy as np
import pytest

from app.detector.session import EXPECTED_OUTPUT_COUNT, INPUT_TENSOR_NAME, DetectorSession
from app.settings import DEFAULT_MODEL_PATH

MODEL_PATH: Final = Path(os.environ.get("CV_MODEL_PATH") or DEFAULT_MODEL_PATH)

INTRA_OP_THREADS: Final = 2
"""O'lchov uchun kifoya. ⚠ Bu tezlik testi EMAS (D-08: kechikish chegara emas)."""

FAKING_PARAMETER_TOKENS: Final[tuple[str, ...]] = (
    "mock",
    "fake",
    "stub",
    "dummy",
    "patch",
)
"""Soxtalashtiruvchi fixture nomining belgilari — RO'YXAT emas, PREDIKAT.

`monkeypatch` ham shu yerga tushadi (`patch` tokeni orqali) va bu ATAYIN:
sessiyaning biror qismini monkeypatch qilish bu faylning butun ma'nosini
yo'q qilardi.
"""


def _this_module() -> ModuleType:
    """SHU modulning o'zi — `import` bilan EMAS, `sys.modules` orqali.

    ⚠ `import tests.integration.test_onnx_session` YOZILMAYDI va sabab
      o'lchangan (2026-08-09): `tests/` paket EMAS, `tests/integration/`
      esa paket — ya'ni bu fayl `integration.test_onnx_session` nomiga
      ega. `tests.` prefiksi bilan import qilish o'sha faylga IKKINCHI
      nom bergan bo'lardi va `mypy` butun tekshiruvni to'xtatardi
      («Source file found twice under different module names») — 05-02
      da `fixtures.detections` uchun aynan shu nosozlik o'lchangan.
    """
    return sys.modules[__name__]


def _synthetic_frame_bytes() -> bytes:
    """Sintetik JPEG — HAQIQIY dekod yo'lini yuritadi, aniqlikni O'LCHAMAYDI.

    Tasvirda gradient bor (bir xil kulrang emas): butunlay tekis kadr
    `resize`/normalizatsiya bosqichlarini ahamiyatsiz qilardi va
    determinizm testi kuchsizroq bo'lardi.
    """
    gradient = np.tile(np.arange(256, dtype=np.uint8), (256, 1))
    image = cv2.merge([gradient, gradient.T, np.full_like(gradient, 128)])
    success, buffer = cv2.imencode(".jpg", image)
    assert success, "sintetik kadrni JPEG ga kodlash muvaffaqiyatsiz"
    return bytes(buffer.tobytes())


@pytest.mark.model
def test_real_onnx_session_is_deterministic_and_reads_its_own_resolution() -> None:
    """HAQIQIY artefakt: kontrakt, rezolyutsiya va BAYT-BAYT determinizm.

    ⚠ BITTA test ichida uchta da'vo — va bu ATAYIN. `model` markerli
      testlar soni AYNAN BITTA bo'lishi §S-14 ning talabi
      (`pytest -m model --collect-only` -> 1). Ularni bo'lish har
      birida qimmat sessiyani qaytadan qurishni ham anglatardi.

    ⛔ SOXTALASHTIRISH YO'Q: sessiya haqiqiy fayldan quriladi, kadr esa
      haqiqiy JPEG dekodidan o'tadi. Buni quyidagi imzo skani o'lchaydi.
    """
    assert MODEL_PATH.is_file(), (
        f"ONNX artefakti topilmadi: `{MODEL_PATH}`. ⚠ BU SKIP EMAS, "
        "YIQILISH: artefaktsiz inference yo'li HECH QACHON o'lchanmagan "
        "bo'ladi. Eksport retsepti — `ops/models/README.md`."
    )

    session = DetectorSession(MODEL_PATH, intra_op_num_threads=INTRA_OP_THREADS)

    # --- Graf kontrakti: nom va chiqishlar soni HAQIQATAN shundaymi ---
    assert session.input_name == INPUT_TENSOR_NAME

    # --- Rezolyutsiya GRAFDAN o'qilganmi (qattiq yozilmaganmi) ---
    graph_height, graph_width = session._session.get_inputs()[0].shape[2:4]
    assert session.input_size == (graph_width, graph_height), (
        f"`input_size` grafning o'z qiymatidan farq qilyapti: "
        f"{session.input_size} != {(graph_width, graph_height)} — ya'ni "
        "rezolyutsiya qattiq yozib qo'yilgan"
    )
    assert graph_width > 0 and graph_height > 0

    # --- Determinizm: bir xil kirish -> BAYT-BAYT bir xil chiqish ---
    tensor = session.preprocess(_synthetic_frame_bytes())
    first_dets, first_labels = session.run(tensor)
    second_dets, second_labels = session.run(tensor)

    assert first_dets.tobytes() == second_dets.tobytes(), (
        "bir xil kirish ikki xil `dets` berdi — CPU EP determinist bo'lishi "
        "SHART, aks holda bir kadr ikki marta aniqlanganda ikki xil "
        "`occupancy_events` qatori tug'ilardi"
    )
    assert first_labels.tobytes() == second_labels.tobytes()

    # --- Chiqishlar soni konstantaga mos ---
    assert len(session._session.get_outputs()) == EXPECTED_OUTPUT_COUNT


# --------------------------------------------------------------------------
# MOCK TAQIG'I — `model` markerisiz, ya'ni STANDART zanjirda YURADI
# --------------------------------------------------------------------------


def test_no_test_in_this_module_requests_a_faking_fixture() -> None:
    """⛔ Bu modulda soxtalashtiruvchi fixture SO'RALMAYDI (§S-14).

    Shakl `test_phase3_criteria.py:1120-1124` dan: `inspect.signature`
    bilan test funksiyalarining parametrlari skanerlanadi.

    ⚠ BU TEST `model` MARKERISIZ va bu ATAYIN: mock taqig'i HAR CI
      yugurishida ishlashi kerak, artefakt bor-yo'qligidan qat'i nazar.
      Marker ostiga qo'yilsa, taqiq aynan artefakt yo'q paytda — ya'ni
      soxtalashtirish bosimi eng yuqori paytda — o'chib qolardi.
    """
    module = _this_module()

    tests = [
        (name, obj)
        for name, obj in inspect.getmembers(module, inspect.isfunction)
        if name.startswith("test_") and obj.__module__ == module.__name__
    ]
    assert tests, "bu modulda birorta `test_` funksiyasi topilmadi — skan bo'sh"

    offenders = {
        name: sorted(
            parameter
            for parameter in inspect.signature(obj).parameters
            if any(token in parameter.lower() for token in FAKING_PARAMETER_TOKENS)
        )
        for name, obj in tests
    }
    named = {name: parameters for name, parameters in offenders.items() if parameters}

    assert named == {}, (
        f"soxtalashtiruvchi fixture so'ralyapti: {named}. Bu faylning YAGONA "
        "ma'nosi — inference yo'lini MOCK'SIZ o'lchash; soxtalashtirish uni "
        "o'z farazining aks-sadosiga aylantirardi."
    )


def test_exactly_one_test_here_carries_the_model_marker() -> None:
    """`model` markerli test AYNAN BITTA (§S-14, mezon boshiga bitta test).

    ⚠ Ikkinchi markerli test qo'shilsa, `pytest -m model` ning natijasi
      «qaysi biri yiqildi?» degan savolga aylanardi va qimmat sessiya ikki
      marta qurilardi. Sanoq shu sababdan darvoza ostida.
    """
    module = _this_module()

    marked = [
        name
        for name, obj in inspect.getmembers(module, inspect.isfunction)
        if name.startswith("test_")
        and obj.__module__ == module.__name__
        and any(mark.name == "model" for mark in getattr(obj, "pytestmark", []))
    ]

    assert marked == ["test_real_onnx_session_is_deterministic_and_reads_its_own_resolution"], (
        f"`model` markerli testlar: {marked} — kutilgani AYNAN BITTA"
    )
