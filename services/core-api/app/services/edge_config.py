"""Universal agent sozlamasi: standart hujjat, birlashtirish va tekshiruv (0036).

Kim nimaga egalik qiladi (`docs/protocol-http.md`, agent repozitoriyasi):

  * server (panel): `plugins`, `tariff`, `parking`, `livestock`, `payments`,
    `update`, `schedules`, `thresholds` — `edge_configs.doc` da, versiyalangan;
  * obyekt (agent oynasi): `devices`, `lanes` — `edge_sites.setup` da;
  * hosila: `config_version` (versiya raqami) va `site` (obyekt qatoridan).

Agentga ketadigan hujjat = `doc` + hosila + `setup`. Tekshiruv AYNAN shu
birlashtirilgan hujjat ustida (`config.schema.json`) bajariladi — agent ham
uni shunday tekshiradi.
"""

from __future__ import annotations

import copy
from typing import Any

from app.edge_contract import ContractError, validate_config

__all__ = [
    "DERIVED_KEYS",
    "SITE_TIMEZONE",
    "default_doc",
    "effective_config",
    "strip_derived",
    "validate_doc",
]

SITE_TIMEZONE = "Asia/Tashkent"

DERIVED_KEYS: tuple[str, ...] = ("config_version", "site", "devices", "lanes")
"""`doc` da SAQLANMAYDIGAN kalitlar — ular har yuborishda qayta quriladi."""

_UPDATE: dict[str, Any] = {"channel": "stable", "auto": True, "window": "22:00-05:00"}

_PARKING_TARIFF: dict[str, Any] = {
    "version": 1,
    "rules": [
        {
            "category": "car",
            "title": "Yengil avtomobil",
            "free_minutes": 15,
            "flat_soum": 0,
            "first_hour_soum": 3000,
            "next_hour_soum": 2000,
            "day_max_soum": 20000,
        },
        {
            "category": "truck",
            "title": "Yuk mashinasi",
            "free_minutes": 15,
            "flat_soum": 0,
            "first_hour_soum": 5000,
            "next_hour_soum": 4000,
            "day_max_soum": 40000,
        },
    ],
}

_PARKING: dict[str, Any] = {
    "entry_ticket": False,
    "exit_grace_minutes": 15,
    "staff": [{"id": "kassir-1", "label": "Kassir 1"}],
}

_LIVESTOCK_CATEGORIES: list[dict[str, Any]] = [
    {"code": "qoramol", "title": "Qoramol", "fee_soum": 25000, "camera_class": "large"},
    {"code": "buzoq", "title": "Buzoq", "fee_soum": 15000, "camera_class": "large"},
    {"code": "qoy_echki", "title": "Qo'y-echki", "fee_soum": 14000, "camera_class": "small"},
    {"code": "qozi_uloq", "title": "Qo'zi-uloq", "fee_soum": 10000, "camera_class": "small"},
    {"code": "ot_tuya", "title": "Ot, tuya, toy", "fee_soum": 20000, "camera_class": "large"},
    {"code": "eshak", "title": "Eshak, bo'taloq", "fee_soum": 15000, "camera_class": "large"},
    {"code": "chochqa", "title": "Cho'chqa", "fee_soum": 10000, "camera_class": "none"},
]


def default_doc(kind: str) -> dict[str, Any]:
    """Obyekt turi bo'yicha 1-versiya biznes sozlamasi (yangi nusxa)."""
    if kind == "parking":
        doc: dict[str, Any] = {
            "plugins": ["parking"],
            "tariff": _PARKING_TARIFF,
            "parking": _PARKING,
            "update": _UPDATE,
        }
    elif kind == "livestock":
        # Mol bozorida mashinalar uchun avtoturargoh ham bor (`parking`
        # plagini), ya'ni tarif ham kerak — agentning parking motori
        # tarifsiz seansni narxlay olmaydi.
        doc = {
            "plugins": ["livestock", "parking"],
            "livestock": {"categories": _LIVESTOCK_CATEGORIES},
            "tariff": _PARKING_TARIFF,
            "parking": _PARKING,
            "update": {**_UPDATE, "skip_weekdays": []},
        }
    elif kind == "market":
        doc = {"plugins": ["market"], "update": _UPDATE}
    else:  # pragma: no cover — CHECK konstrayti boshqa turni o'tkazmaydi
        raise ValueError(f"noma'lum obyekt turi: {kind}")
    return copy.deepcopy(doc)


def strip_derived(doc: dict[str, Any]) -> dict[str, Any]:
    """Hosila kalitlarni olib tashlaydi (panel ularni yuborsa ham saqlanmaydi)."""
    return {key: value for key, value in doc.items() if key not in DERIVED_KEYS}


def effective_config(
    *, site_id: str, kind: str, version: int, doc: dict[str, Any], setup: dict[str, Any]
) -> dict[str, Any]:
    """Agentga yuboriladigan TO'LIQ hujjat (desired state)."""
    devices = setup.get("devices")
    lanes = setup.get("lanes")
    return {
        **strip_derived(doc),
        "config_version": version,
        "site": {"id": site_id, "type": kind, "timezone": SITE_TIMEZONE},
        "devices": devices if isinstance(devices, list) else [],
        "lanes": lanes if isinstance(lanes, list) else [],
    }


def validate_doc(
    *, site_id: str, kind: str, doc: dict[str, Any], setup: dict[str, Any]
) -> list[ContractError]:
    """Biznes hujjatini obyekt tuzilmasi bilan birlashtirib tekshiradi."""
    merged = effective_config(site_id=site_id, kind=kind, version=1, doc=doc, setup=setup)
    return validate_config(merged)
