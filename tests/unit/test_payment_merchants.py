"""Ko'p bozorli kassalar (261030): har bozor o'z Payme/Click kassasi.

Bozor so'rovning o'zidan aniqlanadi — Payme kalitidan, Click `service_id`
sidan. Bu yerdagi xato puldan boshqa bozorning hisobiga yozilishiga olib
keladi, shuning uchun har shox alohida tekshiriladi.
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from uuid import uuid4

from app.services import payment_merchants as pm
from pydantic import SecretStr

A, B, C = uuid4(), uuid4(), uuid4()


def _settings(
    payme: list[dict[str, str]] | str = "", click: list[dict[str, str]] | str = "", **legacy: str
) -> SimpleNamespace:
    def raw(value: list[dict[str, str]] | str) -> SecretStr:
        return SecretStr(value if isinstance(value, str) else json.dumps(value))

    return SimpleNamespace(
        payme_merchants=raw(payme),
        click_merchants=raw(click),
        payme_key=SecretStr(legacy.get("payme_key", "")),
        payme_market_id=legacy.get("payme_market_id", ""),
        payme_merchant_id=legacy.get("payme_merchant_id", ""),
        payme_ikpu="",
        payme_package_code="",
        payme_account_field=legacy.get("payme_account_field", "rasta"),
        click_secret_key=SecretStr(legacy.get("click_secret_key", "")),
        click_service_id=legacy.get("click_service_id", ""),
        click_merchant_id=legacy.get("click_merchant_id", ""),
        click_market_id=legacy.get("click_market_id", ""),
        pay_default_market=legacy.get("pay_default_market", ""),
    )


def _payme(slug: str, market: object, key: str) -> dict[str, str]:
    return {"slug": slug, "market_id": str(market), "merchant_id": f"m-{slug}", "key": key}


def _click(slug: str, market: object, service: str) -> dict[str, str]:
    return {
        "slug": slug,
        "market_id": str(market),
        "service_id": service,
        "merchant_id": f"cm-{slug}",
        "secret_key": f"s-{slug}",
    }


def test_payme_key_selects_its_own_market() -> None:
    s = _settings([_payme("karmana", A, "ka"), _payme("navoiy", B, "nv")])
    assert pm.payme_by_key(s, "ka").market_id == A  # type: ignore[union-attr, arg-type]
    assert pm.payme_by_key(s, "nv").market_id == B  # type: ignore[union-attr, arg-type]
    assert pm.payme_by_key(s, "xato") is None  # type: ignore[arg-type]
    assert pm.payme_by_key(s, "") is None  # type: ignore[arg-type]


def test_click_service_selects_its_own_market_and_secret() -> None:
    s = _settings(click=[_click("karmana", A, "100"), _click("navoiy", B, "200")])
    found = pm.click_by_service(s, "200")  # type: ignore[arg-type]
    assert found is not None and found.market_id == B and found.secret_key == "s-navoiy"
    assert pm.click_by_service(s, "300") is None  # type: ignore[arg-type]


def test_legacy_single_kassa_keeps_working_as_default_market() -> None:
    """Karmanadagi rastalarga yopishtirilgan eski QR `/pay/{rasta}` o'zgarmaydi."""
    s = _settings(
        [_payme("navoiy", B, "nv")],
        payme_key="old",
        payme_market_id=str(A),
        payme_merchant_id="m-old",
        pay_default_market="karmana",
    )
    assert pm.payme_by_key(s, "old").market_id == A  # type: ignore[union-attr, arg-type]
    assert pm.default_market(s) == A  # type: ignore[arg-type]
    assert pm.market_by_slug(s, "karmana") == A  # type: ignore[arg-type]
    assert pm.market_by_slug(s, "navoiy") == B  # type: ignore[arg-type]
    assert pm.market_by_slug(s, "yoq") is None  # type: ignore[arg-type]


def test_duplicates_disable_both_entries_instead_of_guessing() -> None:
    """Bir kalit ikki bozorda — pul qaysi bozorga yozilishi fayl tartibiga bog'lanmasin."""
    s = _settings(
        [_payme("karmana", A, "same"), _payme("navoiy", B, "same"), _payme("qiziltepa", C, "qz")]
    )
    assert pm.payme_by_key(s, "same") is None  # type: ignore[arg-type]
    assert pm.payme_by_key(s, "qz").market_id == C  # type: ignore[union-attr, arg-type]


def test_invalid_entries_are_skipped_others_keep_working() -> None:
    bad = [
        {"slug": "Katta Harf", "market_id": str(A), "merchant_id": "m", "key": "k1"},
        {"slug": "noid", "market_id": "uuid-emas", "merchant_id": "m", "key": "k2"},
        {"slug": "nokey", "market_id": str(B), "merchant_id": "m", "key": ""},
        _payme("ok", C, "k3"),
    ]
    s = _settings(bad)
    assert [m.slug for m in pm.payme_merchants(s)] == ["ok"]  # type: ignore[arg-type]
    assert pm.payme_merchants(_settings("{buzuq json")) == ()  # type: ignore[arg-type]
    assert pm.payme_configured(_settings()) is False  # type: ignore[arg-type]


def test_secrets_do_not_leak_into_repr() -> None:
    s = _settings([_payme("karmana", A, "juda-maxfiy")], [_click("karmana", A, "100")])
    text = repr(pm.payme_merchants(s)) + repr(pm.click_merchants(s))  # type: ignore[arg-type]
    assert "juda-maxfiy" not in text and "s-karmana" not in text


def test_account_field_follows_the_kassa_setting() -> None:
    """Karmana kassasida maydon `rasta_id` (261030) — QR havolasi shu nomni oladi."""
    s = _settings(
        payme_key="old",
        payme_market_id=str(A),
        payme_merchant_id="m",
        payme_account_field="rasta_id",
    )
    assert pm.payme_by_key(s, "old").account_field == "rasta_id"  # type: ignore[union-attr, arg-type]
    bad = _settings([{**_payme("navoiy", B, "nv"), "account_field": "Yomon Nom!"}])
    assert pm.payme_by_key(bad, "nv").account_field == "rasta"  # type: ignore[union-attr, arg-type]
