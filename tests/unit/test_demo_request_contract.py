"""Demo-so'rov kontrakti — DTO, xato reyestri va IP chegarasi (LAND-03).

Bu kodbazadagi BIRINCHI autentifikatsiyasiz yozuv yo'lining kontrakt
yarmi: `DemoRequestPayload` chegarasi (T-10-03 payload chegaralari),
`DEMO_ERROR_CODES` reyestri va `check_demo_request_rate` (T-10-01).

⛔ `phone` MAYDONIDA `field_validator` YO'QLIGI ATAYIN: `LoginRequest`
   naqshi FastAPI'ning standart 422 shakli (`{"detail":[{...}]}`) bilan
   yiqiladi, LAND-03 esa BITTA `"invalid_phone"` satrini talab qiladi.
   Normalizatsiya marshrutda (`api/v1/public.py`), `HTTPException(422,
   detail="invalid_phone")` bilan — `validate_password_strength` bilan
   bir xil qaror va bir xil sabab.

Rate-limit soxta Redis bilan o'lchanadi: `_bump` faqat `pipeline()` ->
`incr`/`expire`/`execute` yuzasini ishlatadi va bu yuzani taqlid qilish
haqiqiy Valkey'siz sanagich arifmetikasini o'lchash imkonini beradi.
Fail-open xulqi (RedisError -> jim o'tish) esa mavjud uchala chaqiruv
(`check_login_rate`, `check_nvr_test_rate`, `check_bot_resolve_rate`)
bilan bir xil qaror — kesh o'chgani uchun demo formani BUTUNLAY
o'ldirish mavjud xizmatni yo'q qilardi.
"""

from __future__ import annotations

from typing import Any

import pytest
from app.schemas import DEMO_ERROR_CODES, DemoRequestPayload, DemoRequestResponse
from app.security.ratelimit import (
    DEMO_REQUEST_LIMIT,
    TooManyAttempts,
    check_demo_request_rate,
)
from pydantic import ValidationError
from redis.exceptions import RedisError

IP = "203.0.113.10"
"""RFC 5737 hujjat diapazoni — hech qachon haqiqiy marshrutlanmaydi."""


def _payload(**overrides: Any) -> dict[str, Any]:
    """Yaroqli tana; har test faqat O'ZI buzadigan maydonni almashtiradi."""
    body: dict[str, Any] = {
        "name": "Alisher Navoiy",
        "phone": "+998901234567",
        "market_name": "Karmana dehqon bozori",
        "locale": "uz-Latn",
    }
    body.update(overrides)
    return body


# ---------------------------------------------------------------------------
# DemoRequestPayload — chegara qoidalari (T-10-03)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("bad_name", ["", "A"])
def test_payload_rejects_empty_or_too_short_name(bad_name: str) -> None:
    """`name` kamida 2 belgi — bo'sh satr forma spami uchun ochiq eshik."""
    with pytest.raises(ValidationError):
        DemoRequestPayload(**_payload(name=bad_name))


def test_payload_rejects_market_name_longer_than_the_limit() -> None:
    """200 belgilik `market_name` rad etiladi (T-10-03 payload chegarasi)."""
    with pytest.raises(ValidationError):
        DemoRequestPayload(**_payload(market_name="x" * 200))


@pytest.mark.parametrize("good_locale", ["uz-Latn", "uz-Cyrl", "ru"])
def test_payload_accepts_the_three_product_locales(good_locale: str) -> None:
    assert DemoRequestPayload(**_payload(locale=good_locale)).locale == good_locale


@pytest.mark.parametrize("bad_locale", ["en", "uz", "UZ-LATN", ""])
def test_payload_rejects_unknown_locale(bad_locale: str) -> None:
    """`locale` uchta mahsulot qiymatidan tashqarisini olmaydi."""
    with pytest.raises(ValidationError):
        DemoRequestPayload(**_payload(locale=bad_locale))


@pytest.mark.parametrize("bad_count", [0, 100_001])
def test_payload_rejects_stall_count_outside_bounds(bad_count: int) -> None:
    """`stall_count` 1..100000 oralig'idan chiqmaydi (T-10-03)."""
    with pytest.raises(ValidationError):
        DemoRequestPayload(**_payload(stall_count=bad_count))


def test_payload_accepts_missing_stall_count() -> None:
    """Rastalar soni IXTIYORIY — `None` yaroqli qiymat."""
    assert DemoRequestPayload(**_payload()).stall_count is None
    assert DemoRequestPayload(**_payload(stall_count=300)).stall_count == 300


def test_honeypot_defaults_to_empty_and_that_is_the_normal_mode() -> None:
    """`website` (honeypot) standarti — BO'SH satr, ya'ni odam rejimi.

    Maydon HTML'da ko'rinmas bo'ladi; to'ldirilgani bot belgisi va marshrut
    uni JIMGINA muvaffaqiyat bilan tashlab yuboradi (Task 2 xulqi).
    """
    payload = DemoRequestPayload(**_payload())
    assert payload.website == ""


def test_payload_has_no_phone_field_validator() -> None:
    """⛔ `phone` Pydantic ichida NORMALIZATSIYA QILINMAYDI (modul docstringi).

    Buzuq telefon modeldan O'TADI — 422 `invalid_phone` qarori marshrutda
    yashaydi. Aks holda FastAPI standart 422 shakli bilan javob berardi va
    LAND-03 ning bitta-satr kontrakti buzilardi.
    """
    raw = "bu telefon emas"
    assert DemoRequestPayload(**_payload(phone=raw)).phone == raw


# ---------------------------------------------------------------------------
# DemoRequestResponse — T-10-02 ning mexanik shakli
# ---------------------------------------------------------------------------


def test_response_model_carries_exactly_one_field() -> None:
    """Javob modeli YAGONA `delivered` maydonini tashiydi.

    Tenant izi (bozor identifikatori/nomi/topologiyasi) javobga tushmasligi
    T-10-02 ning mexanik shakli — maydon QO'SHILGAN zahoti bu test qizaradi.
    """
    assert set(DemoRequestResponse.model_fields) == {"delivered"}


# ---------------------------------------------------------------------------
# DEMO_ERROR_CODES — reyestr (frontend ko'zgu darvozasi 10-08 da ulanadi)
# ---------------------------------------------------------------------------


def test_error_code_registry_is_exactly_four_codes() -> None:
    assert DEMO_ERROR_CODES == frozenset(
        {"rate_limited", "invalid_phone", "validation_error", "delivery_failed"}
    )


# ---------------------------------------------------------------------------
# check_demo_request_rate — IP kesimi (T-10-01)
# ---------------------------------------------------------------------------


class _FakePipeline:
    """`_bump` ishlatadigan yuzaning taqlidi: `incr` + `expire` + `execute`."""

    def __init__(self, store: dict[str, int], *, fail: bool) -> None:
        self._store = store
        self._fail = fail
        self._ops: list[tuple[str, str]] = []

    async def __aenter__(self) -> _FakePipeline:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        return None

    def incr(self, key: str) -> None:
        self._ops.append(("incr", key))

    def expire(self, key: str, window: int, *, nx: bool = False) -> None:
        self._ops.append(("expire", key))

    async def execute(self) -> list[int | bool]:
        if self._fail:
            raise RedisError("connection refused")
        results: list[int | bool] = []
        for op, key in self._ops:
            if op == "incr":
                self._store[key] = self._store.get(key, 0) + 1
                results.append(self._store[key])
            else:
                results.append(True)
        return results


class _FakeRedis:
    """Sanagich arifmetikasi uchun yetarli minimal Valkey taqlidi."""

    def __init__(self, *, fail: bool = False) -> None:
        self.store: dict[str, int] = {}
        self._fail = fail

    def pipeline(self, *, transaction: bool = True) -> _FakePipeline:
        return _FakePipeline(self.store, fail=self._fail)


async def test_demo_request_rate_is_silent_up_to_the_limit() -> None:
    """5-chaqiruvgacha (chegara) hech qanday istisno yo'q."""
    cache = _FakeRedis()
    for _ in range(DEMO_REQUEST_LIMIT):
        await check_demo_request_rate(cache, ip=IP)  # type: ignore[arg-type]


async def test_the_sixth_call_raises_too_many_attempts() -> None:
    """6-chaqiruv `TooManyAttempts` — 429 `rate_limited` ning manbai."""
    cache = _FakeRedis()
    for _ in range(DEMO_REQUEST_LIMIT):
        await check_demo_request_rate(cache, ip=IP)  # type: ignore[arg-type]

    with pytest.raises(TooManyAttempts) as excinfo:
        await check_demo_request_rate(cache, ip=IP)  # type: ignore[arg-type]
    assert excinfo.value.scope == "demo_request"


async def test_the_counter_key_is_cut_by_ip_only() -> None:
    """⛔ Kalit kesimi FAQAT IP — telefon Valkey'ga YOZILMAYDI (T-07-41).

    `_BOT_RESOLVE_KEY` docstringidagi qoidaning ayni o'zi: mos kelmagan
    (yoki umuman anonim) telefon raqami hech qayerga saqlanmasligi kerak,
    kalit esa Valkey'dan xotira dumpiga tushishi mumkin bo'lgan joy.
    """
    cache = _FakeRedis()
    await check_demo_request_rate(cache, ip=IP)  # type: ignore[arg-type]

    assert set(cache.store) == {f"rl:demo_request:{IP}"}


async def test_redis_error_fails_open() -> None:
    """`RedisError` JIM o'tadi — kesh o'limi demo formani O'LDIRMAYDI.

    Mavjud uchala chaqiruv bilan bir xil qaror (fail-open): teskarisi
    Valkey uzilishida butun marketing yuzasini 500 ga tushirardi.
    """
    cache = _FakeRedis(fail=True)
    for _ in range(DEMO_REQUEST_LIMIT + 3):
        await check_demo_request_rate(cache, ip=IP)  # type: ignore[arg-type]
