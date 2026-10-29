"""Universal agent protokoli (0036) — server tekshiruvchisi agentniki bilan bir xil.

`tests/fixtures/edge_contract/{valid,invalid}` — agent repozitoriyasidagi
`contract/testdata` ning nusxasi: Go validatori aynan shu fayllarni qabul
qiladi/rad etadi, Python tekshiruvchisi ham AYNAN shunday qilishi shart.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from app.edge_contract import (
    COMMAND_TYPES,
    ContractError,
    event_types,
    validate_command,
    validate_config,
    validate_envelope,
    validate_result,
)
from app.services.edge_config import default_doc, effective_config, validate_doc

TESTDATA = Path(__file__).resolve().parents[1] / "fixtures" / "edge_contract"


def _errors(name: str, doc: Any) -> list[ContractError]:
    if name.startswith("event"):
        try:
            validate_envelope(doc)
        except ContractError as exc:
            return [exc]
        return []
    if name.startswith("command"):
        return validate_command(doc)
    if name.startswith("config"):
        return validate_config(doc)
    if name.startswith("result"):
        return validate_result(doc)
    raise AssertionError(f"noma'lum namuna: {name}")


def _files(kind: str) -> list[Path]:
    files = sorted((TESTDATA / kind).glob("*.json"))
    assert files, f"{kind} namunalari topilmadi"
    return files


@pytest.mark.parametrize("path", _files("valid"), ids=lambda p: p.name)
def test_valid_samples_pass(path: Path) -> None:
    assert _errors(path.name, json.loads(path.read_text(encoding="utf-8"))) == []


@pytest.mark.parametrize("path", _files("invalid"), ids=lambda p: p.name)
def test_invalid_samples_fail(path: Path) -> None:
    assert _errors(path.name, json.loads(path.read_text(encoding="utf-8"))), path.name


def test_registries_are_not_empty() -> None:
    assert "parking.plate.read" in event_types()
    assert "core.payment.cash" in event_types()
    assert "parking.gate.open" in COMMAND_TYPES
    assert "file_id" not in event_types()


@pytest.mark.parametrize("kind", ["parking", "market", "livestock"])
def test_default_configs_validate_with_empty_setup(kind: str) -> None:
    doc = default_doc(kind)
    assert validate_doc(site_id="s-1", kind=kind, doc=doc, setup={}) == []
    merged = effective_config(site_id="s-1", kind=kind, version=1, doc=doc, setup={})
    assert merged["devices"] == []
    assert merged["lanes"] == []
    assert merged["site"]["timezone"] == "Asia/Tashkent"


def test_errors_are_plain_uzbek_with_paths() -> None:
    doc = default_doc("parking")
    doc["tariff"]["rules"][0]["first_hour_soum"] = -1
    errors = validate_doc(site_id="s-1", kind="parking", doc=doc, setup={})
    assert errors[0].path == "tariff.rules[0].first_hour_soum"
    assert errors[0].message == "qiymat 0 dan kichik bo'lmasligi kerak"
