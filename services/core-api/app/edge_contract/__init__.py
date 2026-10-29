"""Universal agent protokoli v1 — JSON sxemalar va ularning tekshiruvchisi.

=============================================================================
⛔ SXEMALAR AGENT REPOZITORIYASIDAN SO'ZMA-SO'Z KO'CHIRILGAN
   (`sbozor-agent/contract/schemas/`). Agent o'zi Go'da AYNAN shu fayllarni
   tekshiradi (`contract.Validator`, `santhosh-tekuri/jsonschema`,
   `AssertFormat`). Sxema o'zgarsa — fayllar qayta ko'chiriladi, bu yerda
   tahrirlanmaydi.

Hodisa turlari `events/*.schema.json` ichidagi `$defs` kalitlaridan olinadi
(agentdagi bilan bir xil qoida): kalit `<modul>.<obyekt>.<harakat>` shaklida
bo'lsa — hodisa turi, aks holda yordamchi ta'rif (`file_id`, `plate`, ...).

FORMATLAR: Go validatori `format` ni TEKSHIRADI (`AssertFormat`). Python
`jsonschema` `date-time` ni faqat qo'shimcha paket bilan tekshiradi, shuning
uchun u shu yerda qo'lda (RFC 3339, mintaqa majburiy) ro'yxatdan o'tadi —
aks holda server agent rad etadigan hodisani qabul qilardi.
=============================================================================
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from functools import cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import ValidationError
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

__all__ = [
    "BASE_URL",
    "COMMAND_TYPES",
    "ContractError",
    "event_types",
    "validate_command",
    "validate_config",
    "validate_envelope",
    "validate_event_data",
    "validate_result",
]

BASE_URL = "https://schemas.sbozor.uz/agent/v1/"
_SCHEMA_DIR = Path(__file__).resolve().parent / "schemas"
_EVENT_TYPE_RE = re.compile(r"^(core|market|parking|livestock)\.[a-z][a-z_]*\.[a-z][a-z_]*$")
_RFC3339_RE = re.compile(r"^\d{4}-\d{2}-\d{2}[Tt]\d{2}:\d{2}:\d{2}(\.\d+)?([Zz]|[+-]\d{2}:\d{2})$")

_FORMAT_CHECKER = FormatChecker()


@_FORMAT_CHECKER.checks("date-time", raises=ValueError)  # type: ignore[untyped-decorator]
def _is_date_time(value: object) -> bool:
    """RFC 3339 — mintaqa (`Z` yoki `+05:00`) MAJBURIY, Go'dagi kabi."""
    if not isinstance(value, str):
        return True
    if not _RFC3339_RE.match(value):
        raise ValueError(f"{value!r} RFC 3339 vaqti emas")
    datetime.fromisoformat(value.replace("z", "Z"))
    return True


class ContractError(Exception):
    """Sxemaga mos kelmaslik: xato yo'li va odam o'qiydigan sabab.

    ⚠ `frozen` dataclass EMAS: istisnoga `__traceback__` Python darajasida
      yoziladi (`contextlib`) va muzlatilgan obyekt uni rad etardi.
    """

    def __init__(self, path: str, message: str) -> None:
        super().__init__(f"{path}: {message}" if path else message)
        self.path = path
        self.message = message


@dataclass(frozen=True, slots=True)
class _Contract:
    envelope: Draft202012Validator
    command: Draft202012Validator
    result: Draft202012Validator
    config: Draft202012Validator
    events: dict[str, Draft202012Validator]


def _url(path: Path) -> str:
    return BASE_URL + path.relative_to(_SCHEMA_DIR).as_posix()


@cache
def _contract() -> _Contract:
    resources: list[tuple[str, Resource[Any]]] = []
    event_refs: dict[str, str] = {}
    for path in sorted(_SCHEMA_DIR.rglob("*.schema.json")):
        document = json.loads(path.read_text(encoding="utf-8"))
        url = _url(path)
        resources.append((url, Resource.from_contents(document, default_specification=DRAFT202012)))
        if path.parent.name != "events":
            continue
        for name in document.get("$defs", {}):
            if not _EVENT_TYPE_RE.match(name):
                continue
            if name in event_refs:
                raise RuntimeError(f"hodisa turi ikki marta ta'riflangan: {name}")
            event_refs[name] = f"{url}#/$defs/{name}"

    registry: Registry[Any] = Registry().with_resources(resources)

    def compile_ref(ref: str) -> Draft202012Validator:
        return Draft202012Validator(
            {"$ref": ref}, registry=registry, format_checker=_FORMAT_CHECKER
        )

    return _Contract(
        envelope=compile_ref(BASE_URL + "envelope.schema.json"),
        command=compile_ref(BASE_URL + "command.schema.json"),
        result=compile_ref(BASE_URL + "command_result.schema.json"),
        config=compile_ref(BASE_URL + "config.schema.json"),
        events={name: compile_ref(ref) for name, ref in event_refs.items()},
    )


def event_types() -> list[str]:
    """Ro'yxatdan o'tgan barcha hodisa turlari (tartiblangan)."""
    return sorted(_contract().events)


def _command_types() -> tuple[str, ...]:
    raw = json.loads((_SCHEMA_DIR / "command.schema.json").read_text(encoding="utf-8"))
    return tuple(raw["properties"]["type"]["enum"])


COMMAND_TYPES: tuple[str, ...] = _command_types()
"""`command.schema.json` dagi oq ro'yxat — server faqat shularni yuboradi."""


def _path(error: ValidationError) -> str:
    out = ""
    for part in error.absolute_path:
        if isinstance(part, int):
            out += f"[{part}]"
        else:
            out += f".{part}" if out else str(part)
    return out


def _fmt(values: Any) -> str:
    if isinstance(values, list | tuple):
        return ", ".join(str(v) for v in values)
    return str(values)


_TYPE_NAMES = {
    "object": "obyekt",
    "array": "ro'yxat",
    "string": "matn",
    "integer": "butun son",
    "number": "son",
    "boolean": "ha/yo'q (true/false)",
}


def _uzbek(error: ValidationError) -> str:
    """Validator xatosini oddiy o'zbek tiliga o'giradi (panel uchun)."""
    kind = error.validator
    value = error.validator_value
    if kind == "required":
        missing = [name for name in value if name not in (error.instance or {})]
        return f"majburiy maydon yo'q: {_fmt(missing)}"
    if kind == "additionalProperties":
        extra = sorted(set(error.instance or {}) - set((error.schema or {}).get("properties", {})))
        return f"ruxsat etilmagan maydon: {_fmt(extra)}"
    if kind == "type":
        expected = value if isinstance(value, list) else [value]
        return "turi noto'g'ri — kutilgani: " + _fmt([_TYPE_NAMES.get(t, t) for t in expected])
    if kind == "enum":
        return f"ruxsat etilgan qiymatlardan biri bo'lishi kerak: {_fmt(value)}"
    if kind == "const":
        return f"qiymat aynan «{value}» bo'lishi kerak"
    if kind == "pattern":
        return "format noto'g'ri"
    if kind == "format":
        return f"format noto'g'ri ({value})"
    if kind == "minimum":
        return f"qiymat {value} dan kichik bo'lmasligi kerak"
    if kind == "maximum":
        return f"qiymat {value} dan katta bo'lmasligi kerak"
    if kind == "minLength":
        return "bo'sh bo'lmasligi kerak" if value == 1 else f"kamida {value} belgi bo'lishi kerak"
    if kind == "maxLength":
        return f"ko'pi bilan {value} belgi bo'lishi kerak"
    if kind == "minItems":
        return f"kamida {value} ta element bo'lishi kerak"
    if kind == "uniqueItems":
        return "elementlar takrorlanmasligi kerak"
    return f"sxemaga mos emas ({kind})"


def _errors(validator: Draft202012Validator, instance: Any) -> list[ContractError]:
    found = sorted(
        validator.iter_errors(instance),
        key=lambda e: (list(map(str, e.absolute_path)), str(e.validator)),
    )
    return [ContractError(path=_path(e), message=_uzbek(e)) for e in found]


def _check(validator: Draft202012Validator, instance: Any) -> None:
    errors = _errors(validator, instance)
    if errors:
        raise errors[0]


def validate_envelope(event: Any) -> None:
    """Hodisa konverti + `data` ni shu tur sxemasiga qarab tekshiradi.

    Raises:
        ContractError: birinchi topilgan xato bilan.
    """
    contract = _contract()
    _check(contract.envelope, event)
    validator = contract.events.get(event["type"])
    if validator is None:
        raise ContractError(path="type", message=f"noma'lum hodisa turi: {event['type']}")
    errors = _errors(validator, event["data"])
    if errors:
        first = errors[0]
        raise ContractError(
            path=f"data.{first.path}" if first.path else "data", message=first.message
        )


def validate_event_data(event_type: str, data: Any) -> list[ContractError]:
    """Faqat `data` ni tekshiradi (testlar va diagnostika uchun)."""
    validator = _contract().events.get(event_type)
    if validator is None:
        return [ContractError(path="type", message=f"noma'lum hodisa turi: {event_type}")]
    return _errors(validator, data)


def validate_command(command: Any) -> list[ContractError]:
    """Buyruq konverti (`command.schema.json`)."""
    return _errors(_contract().command, command)


def validate_result(result: Any) -> list[ContractError]:
    """Buyruq natijasi (`command_result.schema.json`)."""
    return _errors(_contract().result, result)


def validate_config(config: Any) -> list[ContractError]:
    """To'liq (agentga yuboriladigan) sozlama — barcha xatolar ro'yxati."""
    return _errors(_contract().config, config)
