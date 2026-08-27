"""`sbozor_core.security` — Argon2id parol primitivlari.

`pwdlib[argon2]`, `passlib` EMAS: passlib oxirgi marta 2020-yilda chiqqan va
Python 3.13'da olib tashlangan `crypt` modulini import qiladi — ya'ni u bu
runtime'da UMUMAN ishga tushmaydi.

Qamralgan tahdidlar:
* T-01-15 — foydalanuvchi sanab chiqish (`dummy_verify` javob vaqtini tekislaydi)
* T-01-18 — hashlash parametrlarining eskirishi (`verify_and_update`)
"""

from __future__ import annotations

import time

from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
from sbozor_core.security import dummy_verify, hash_password, verify_password

PASSWORD = "juda-kuchli-parol-2026"


def test_hash_password_uses_argon2id() -> None:
    """OWASP tavsiya qilgan variant — `argon2i` yoki `argon2d` emas."""
    assert hash_password(PASSWORD).startswith("$argon2id$")


def test_hash_password_is_salted() -> None:
    """Bir xil parol ikki xil hash beradi — rainbow table foydasiz."""
    assert hash_password(PASSWORD) != hash_password(PASSWORD)


def test_verify_password_accepts_correct_password() -> None:
    ok, updated = verify_password(PASSWORD, hash_password(PASSWORD))
    assert ok is True
    assert updated is None, "joriy parametrlar dolzarb — qayta hash kerak emas"


def test_verify_password_rejects_wrong_password() -> None:
    ok, updated = verify_password("noto'g'ri-parol", hash_password(PASSWORD))
    assert ok is False
    assert updated is None


def test_verify_password_handles_non_ascii() -> None:
    """O'zbek/rus harflari va apostrof — parol sifatida odatiy holat."""
    raw = "o'zbek parol — ЎЗБЕК 2026"
    ok, _ = verify_password(raw, hash_password(raw))
    assert ok is True


def test_verify_password_rehashes_outdated_parameters() -> None:
    """T-01-18: eski (zaif) parametrli hash yangisiga ko'chiriladi."""
    weak = PasswordHash((Argon2Hasher(memory_cost=8, time_cost=1, parallelism=1),))
    legacy_hash = weak.hash(PASSWORD)

    ok, updated = verify_password(PASSWORD, legacy_hash)

    assert ok is True
    assert updated is not None, "eskirgan parametrlar uchun yangi hash qaytishi kerak"
    assert updated != legacy_hash
    assert updated.startswith("$argon2id$")


def test_verify_password_does_not_rehash_on_failure() -> None:
    """Noto'g'ri parol hech qachon yangi hash bermaydi."""
    weak = PasswordHash((Argon2Hasher(memory_cost=8, time_cost=1, parallelism=1),))
    ok, updated = verify_password("boshqa-parol", weak.hash(PASSWORD))
    assert ok is False
    assert updated is None


def test_dummy_verify_does_not_raise() -> None:
    dummy_verify()


def test_dummy_verify_costs_measurable_time() -> None:
    """T-01-15: telefon topilmasa ham Argon2 ishi bajariladi.

    Aks holda "raqam bazada bormi?" savoliga javob vaqti bilan bilib olinadi.
    """
    started = time.perf_counter()
    dummy_verify()
    elapsed = time.perf_counter() - started
    assert elapsed > 0.001, f"dummy_verify() juda tez tugadi ({elapsed:.6f}s) — ish bajarilmadi"


def test_dummy_verify_and_real_verify_are_same_order_of_magnitude() -> None:
    """Ikki yo'lning narxi taqqoslanadigan bo'lishi kerak."""
    stored = hash_password(PASSWORD)

    started = time.perf_counter()
    verify_password("noto'g'ri-parol", stored)
    real = time.perf_counter() - started

    started = time.perf_counter()
    dummy_verify()
    dummy = time.perf_counter() - started

    assert 0.2 < dummy / real < 5.0, f"dummy={dummy:.4f}s real={real:.4f}s — vaqt farqi juda katta"
