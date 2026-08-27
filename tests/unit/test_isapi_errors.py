"""Xato taksonomiyasi reyestrining SHAKLI (SC#3, D-02, UI-SPEC §7.3-7.5).

=============================================================================
BU YERDA XULQ EMAS, KONTRAKT O'LCHANADI.

Reyestrning uchta iste'molchisi bor va ularning HECH BIRI bu repozitoriyda
emas yoki bu fazada hali yozilmagan:

    nvr_discovery_runs.error_code   -> baza ustuni      (03-06)
    HTTPException(detail=...)       -> HTTP javobi      (03-07)
    cameras.errorCause.<kod>        -> uch tildagi matn (03-08)

Ya'ni kod nomining o'zgarishi bu fazada HECH QAYERDA qizarmaydi va faqat
foydalanuvchi ekranida — «noma'lum xato» bo'lib — ko'rinardi. Shuning
uchun reyestr shakli mexanik ravishda qulflanadi.
=============================================================================
"""

from __future__ import annotations

import inspect

import pytest
from app.services.isapi import errors
from app.services.isapi.errors import (
    AUTH_LOCKING_CODES,
    ERROR_DETAIL_KEYS,
    MAX_RAW_DETAIL_CHARS,
    NVR_ERROR_CODES,
    NvrError,
)

EXPECTED_CODE_COUNT = 12
"""SC#3 ning o'n ikki kodi — `03-VALIDATION.md` ning qamrov jadvali bilan bir xil son."""

EXPECTED_DETAIL_KEYS = frozenset(
    {
        "drift_seconds",
        "device_time",
        "server_time",
        "unlock_at",
        "channel_no",
        "channel_name",
        "model",
        "raw",
    }
)
"""UI-SPEC §7.4 [TALAB] dagi allowlist — TESTDA QAYTA YOZILGAN, import qilinmagan.

Ro'yxatni moduldan import qilib «o'ziga teng» deb tekshirish hech nimani
o'lchamasdi. Bu yerdagi nusxa spetsifikatsiyadan ko'chirilgan, ya'ni
moduldagi ro'yxat o'zgarsa test uni KO'RADI va o'zgartirish ongli qaror
bo'lishga majbur bo'ladi.
"""

EXPECTED_DETAIL_KEY_COUNT = len(EXPECTED_DETAIL_KEYS)

HEDGE_WORDS = ("ehtimol", "возможно", "эҳтимол")
"""D-05 ning hedge so'zlari — ular FRONTEND matnida, backend kodida EMAS."""


def test_registry_has_exactly_twelve_unique_codes() -> None:
    """O'n ikki kod, takrorlanmaydi.

    Takrorlanish `tuple` da JIMGINA o'tib ketardi (`frozenset` da esa
    umuman ko'rinmasdi) va «o'n ikkitasi ham qoplangan» degan qamrov
    jadvali aslida o'n bittani o'lchayotgan bo'lardi.
    """
    assert len(NVR_ERROR_CODES) == EXPECTED_CODE_COUNT, (
        f"reyestrda {len(NVR_ERROR_CODES)} ta kod: {list(NVR_ERROR_CODES)}"
    )
    assert len(set(NVR_ERROR_CODES)) == EXPECTED_CODE_COUNT, (
        f"takrorlangan kod bor: {sorted(NVR_ERROR_CODES)}"
    )


def test_auth_locking_codes_are_a_subset_of_the_registry() -> None:
    """UI-SPEC §4.4: qulflaydigan uchta kod reyestrda BOR bo'lishi shart.

    Aks holda frontend hech qachon kelmaydigan kod uchun «retry tugmasi
    yo'q» qoidasini saqlab yurardi va haqiqiy qulflaydigan kod uchun
    tugmani ko'rsatardi.
    """
    missing = AUTH_LOCKING_CODES - set(NVR_ERROR_CODES)
    assert not missing, f"reyestrda yo'q kod(lar): {sorted(missing)}"
    assert len(AUTH_LOCKING_CODES) == 3, sorted(AUTH_LOCKING_CODES)


def test_error_detail_allowlist_has_exactly_eight_keys() -> None:
    """UI-SPEC §7.4 — sakkiz kalit, ko'p ham emas, kam ham emas."""
    assert len(ERROR_DETAIL_KEYS) == EXPECTED_DETAIL_KEY_COUNT, sorted(ERROR_DETAIL_KEYS)
    assert ERROR_DETAIL_KEYS == EXPECTED_DETAIL_KEYS, (
        f"farq: {sorted(ERROR_DETAIL_KEYS ^ EXPECTED_DETAIL_KEYS)}"
    )


def test_unknown_code_is_rejected_at_construction() -> None:
    """Reyestrda yo'q kod bilan `NvrError` QURIB BO'LMAYDI.

    Usiz «yangi kod o'ylab topaman» yo'li ochiq qolardi va u bazaga ham,
    javobga ham tushardi — frontend esa uni `errors.generic` bilan
    ko'rsatib, sababni butunlay yo'qotardi.
    """
    with pytest.raises(ValueError, match="noma'lum error_code"):
        NvrError("nvr_something_new")


@pytest.mark.parametrize("code", NVR_ERROR_CODES)
def test_every_registered_code_can_be_raised(code: str) -> None:
    """Reyestrdagi HAR KOD haqiqiy istisno bera oladi — «o'lik kod» yo'q."""
    error = NvrError(code)
    assert error.code == code
    assert error.detail == {}


def test_unknown_detail_key_is_rejected_at_construction() -> None:
    """Allowlist HUJJAT EMAS, DARVOZA (UI-SPEC §7.4 [TALAB], T-03-32).

    Faqat hujjatda qolgan ro'yxat jimgina ma'lumot yo'qotishga aylanardi:
    backend kalit yozadi, hech kim xato qilmaganday ko'rinadi,
    foydalanuvchi esa uni HECH QACHON ko'rmaydi.
    """
    with pytest.raises(ValueError, match="ruxsat etilmagan kalit"):
        NvrError("nvr_clock_drift", {"drift_seconds": 420, "internal_trace": "..."})


def test_allowed_detail_keys_pass_through() -> None:
    """Ruxsat etilgan kalitlar O'ZGARMASDAN o'tadi."""
    error = NvrError(
        "nvr_clock_drift",
        {"drift_seconds": 419.5, "device_time": "2026-08-03T10:00:00Z", "server_time": "…"},
    )
    assert error.detail["drift_seconds"] == 419.5
    assert error.detail["device_time"] == "2026-08-03T10:00:00Z"


def test_oversized_raw_is_truncated_before_it_reaches_the_database() -> None:
    """Xom javob CHEKSIZ emas — u `error_detail` jsonb'iga tushadi (T-03-30)."""
    error = NvrError("nvr_stream_limit", {"raw": "x" * (MAX_RAW_DETAIL_CHARS * 3)})
    raw = error.detail["raw"]
    assert isinstance(raw, str)
    assert len(raw) == MAX_RAW_DETAIL_CHARS + 1, f"kesilmadi: {len(raw)}"
    assert raw.endswith("…")


def test_detail_passes_through_the_key_based_mask() -> None:
    """`mask_sensitive` KALIT NOMIGA qaraydi va u shu yerda ham qo'llanadi.

    ⚠ NAZORAT BANDI: `raw` ICHIDAGI matn maskalanMAYDI va bu ochiq
    chegara (`errors.py` izohi). Test ikkala tomonni ham qulflaydi —
    aks holda kimdir «maskalash ishlayapti» deb o'ylab xom javobga
    ishonib qolardi.
    """
    error = NvrError("nvr_stream_limit", {"raw": "password=Sim12345"})
    assert error.detail["raw"] == "password=Sim12345", (
        "xom matn maskalandi — bu kutilmagan; filtr FAQAT kalit nomiga qarashi kerak"
    )


def test_backend_never_writes_the_hedge_word() -> None:
    """D-05 / UI-SPEC §7.5: «ehtimol» — FRONTEND matni, backend kodi emas.

    Backend `nvr_stream_limit` KODINI beradi va xom javobni saqlaydi;
    hedging esa taqdimotda. Agar hedge so'zi backendga tushsa u
    tarjimadan chetda qolardi (uch tilda emas, bir tilda) va G-3
    darvozasi (03-08) uni ko'rmasdi.
    """
    source = inspect.getsource(errors).lower()
    hits = [word for word in HEDGE_WORDS if word in source]
    assert not hits, f"backend kodida hedge so'zi topildi: {hits}"


def test_repr_shows_the_code_and_detail() -> None:
    """Tashxis uchun: istisno o'zini o'zi tushuntiradi."""
    error = NvrError("device_not_supported", {"model": "AVS-9000"})
    assert "device_not_supported" in repr(error)
    assert "AVS-9000" in repr(error)
