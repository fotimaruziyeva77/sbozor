"""Kadr olish xato taksonomiyasi — o'n bir kod, IKKI iste'molchi, BITTA reyestr.

Darvozalarning shakli `test_isapi_errors.py` dan meros: SANOQ darvozasi
reyestrning kutilmaganda o'sishini/qisqarishini tutadi, HOSILA darvozasi
esa qism-to'plamlarning qo'lda ikkinchi marta yozilmaganini.
"""

from __future__ import annotations

from typing import Final

import pytest
from app.services.capture_errors import (
    CAPTURE_AUTH_LOCKING_CODES,
    CAPTURE_DEFER_CODES,
    CAPTURE_ERROR_CODES,
    CAPTURE_ERROR_META,
    CAPTURE_JOB_ERROR_CODES,
    MAX_DETAIL_CHARS,
    CaptureError,
)

EXPECTED_CODE_COUNT: Final[int] = 11
"""`04-UI-SPEC.md` §11.8 da AYNAN o'n bitta kod uchun matn yozilgan.

⚠ Sanoq darvozasi «kod qo'shildi, uch tildagi matn esa qo'shilmadi»
  holatini tutadi. Matnsiz kod foydalanuvchiga `errors.generic` bo'lib
  ko'rinardi va sabab yo'qolardi.
"""

VALID_ACTORS: Final[frozenset[str]] = frozenset({"admin", "platform", "none"})


def test_registry_has_exactly_eleven_unique_codes() -> None:
    """SANOQ darvozasi — reyestr `04-UI-SPEC.md` §11.8 bilan bir xil hajmda."""
    assert len(CAPTURE_ERROR_CODES) == EXPECTED_CODE_COUNT
    assert len(set(CAPTURE_ERROR_CODES)) == EXPECTED_CODE_COUNT


def test_every_code_has_metadata_and_vice_versa() -> None:
    """Reyestr va metadata BIR XIL to'plam — ikkinchi haqiqat manbai yo'q."""
    assert set(CAPTURE_ERROR_META) == set(CAPTURE_ERROR_CODES)


def test_every_code_names_an_actor_from_the_contract() -> None:
    """`04-UI-SPEC.md` §5.3 — «KIM tuzatadi» xato matnining uchinchi qismi.

    Aktorsiz xato foydalanuvchini «men nima qilishim kerak?» degan savol
    bilan qoldiradi va admin platforma jamoasining ishini kutib o'tiradi
    (yoki teskarisi).
    """
    for code, meta in CAPTURE_ERROR_META.items():
        assert meta.actor in VALID_ACTORS, f"{code}: {meta.actor!r}"


def test_every_meta_knows_its_own_code() -> None:
    """Metadata kalitdan AJRALIB ketmaydi — nusxa-ko'chirish xatosining tuzog'i."""
    for code, meta in CAPTURE_ERROR_META.items():
        assert meta.code == code


def test_codes_are_namespaced_to_capture() -> None:
    """`capture_` prefiksi — kod QAYSI taksonomiyadan kelganini aytadi.

    3-fazaning `nvr_*` kodlari bilan bir bazada, bir `error_code` ustunida
    yashaydi (`nvr_discovery_runs` va `capture_runs`), ya'ni prefiks
    ularni aralashtirib yuborishning oldini oladi.
    """
    for code in CAPTURE_ERROR_CODES:
        assert code.startswith("capture_"), code


# ---------------------------------------------------------------------------
# Hosila to'plamlar — METADAN, qo'lda emas
# ---------------------------------------------------------------------------


def test_auth_locking_codes_are_derived_from_the_metadata() -> None:
    """⛔ HOSILA DARVOZASI — to'plam qo'lda IKKINCHI marta yozilmagan.

    Qo'lda yozilgan nusxa jadval bilan bir kun ajralib ketardi va qoida
    BITTA yuzada qolardi (`nvr-errors.ts:139` bilan aynan bir xil sabab).
    """
    expected = {code for code, meta in CAPTURE_ERROR_META.items() if meta.locks_account}

    assert expected == CAPTURE_AUTH_LOCKING_CODES
    assert set(CAPTURE_ERROR_CODES) >= CAPTURE_AUTH_LOCKING_CODES


def test_defer_codes_are_derived_from_the_metadata() -> None:
    """Xuddi shu qoida `defer` o'lchami uchun ham."""
    expected = {code for code, meta in CAPTURE_ERROR_META.items() if meta.defer}

    assert expected == CAPTURE_DEFER_CODES


def test_bad_credentials_locks_the_account_and_is_not_retried() -> None:
    """D-03 dan meros TESKARI retry siyosati — 4-fazadagi YANGI ma'nosi bilan.

    Hikvision hisobni ~5 xato urinishdan keyin 30 daqiqaga qulflaydi. Tik
    har daqiqada ishlaydi, ya'ni retry taqiqlanmasa 25 kamera x 10 tik =
    250 muvaffaqiyatsiz urinish bo'lib, BUTUN BOZORNING hisobi qulflanardi
    va undan keyin TO'G'RI PAROL HAM ishlamasdi.
    """
    meta = CAPTURE_ERROR_META["capture_bad_credentials"]

    assert meta.locks_account is True
    assert meta.retry_safe is False
    assert "capture_bad_credentials" in CAPTURE_AUTH_LOCKING_CODES


def test_stream_limit_is_deferred_but_never_locking() -> None:
    """⛔ KECHIKTIRISH ≠ QULFLASH — ikki O'LCHOV, bitta emas.

    `capture_stream_limit` da hisob qulflanmaydi: NVR shunchaki band. Uni
    `AUTH_LOCKING_CODES` ga qo'shish slotni BUTUNLAY tashlab yuborardi,
    holbuki oqim bo'shagach kadr olish MUVAFFAQIYATLI bo'ladi. Shuning
    uchun u `locked_until` ni qayta ishlatadi (kechiktirish), qatorni
    `failed` qilmaydi.
    """
    meta = CAPTURE_ERROR_META["capture_stream_limit"]

    assert meta.defer is True
    assert meta.locks_account is False
    assert "capture_stream_limit" in CAPTURE_DEFER_CODES
    assert "capture_stream_limit" not in CAPTURE_AUTH_LOCKING_CODES


def test_locking_codes_are_never_retry_safe() -> None:
    """Invariant: qulflaydigan kod qayta urinishga XAVFSIZ bo'la olmaydi.

    Ikkalasi mustaqil bayroq, lekin ularning `locks_account=True` va
    `retry_safe=True` kombinatsiyasi MA'NOSIZ — u «qayta urinish xavfsiz,
    lekin u hisobni qulflaydi» degan bo'lardi.
    """
    for code in CAPTURE_AUTH_LOCKING_CODES:
        assert CAPTURE_ERROR_META[code].retry_safe is False, code


def test_job_error_codes_is_the_whole_registry() -> None:
    """`app/schemas.py` bu to'plamni IMPORT qiladi (04-07), qayta yozmaydi.

    Ikki nusxa bo'lganda job bazaga kod yozib, API uni tanimasdi va
    frontend `errors.generic` ko'rsatib sababni yo'qotardi (§S-5/§S-7).
    """
    assert frozenset(CAPTURE_ERROR_CODES) == CAPTURE_JOB_ERROR_CODES


def test_platform_owns_the_codes_the_admin_cannot_fix() -> None:
    """Aktor taqsimoti `04-UI-SPEC.md` §11.8 bilan mos.

    ⚠ `capture_credential_unreadable` ATAYIN `platform`: u «bizning SHIFR
      KALITIMIZ mos kelmayapti» degani va admin parolni qayta kiritish
      bilan uni HECH QACHON tuzata olmaydi (`discovery.py:112-121` ning
      aynan takrori).
    """
    assert CAPTURE_ERROR_META["capture_credential_unreadable"].actor == "platform"
    assert CAPTURE_ERROR_META["capture_storage_unavailable"].actor == "platform"
    assert CAPTURE_ERROR_META["capture_slot_missed"].actor == "platform"
    assert CAPTURE_ERROR_META["capture_worker_lost"].actor == "platform"
    assert CAPTURE_ERROR_META["capture_plan_created_late"].actor == "none"
    assert CAPTURE_ERROR_META["capture_bad_credentials"].actor == "admin"


def test_the_no_action_actor_belongs_only_to_the_late_plan_code() -> None:
    """«Harakat talab qilinmaydi» — YAGONA holat, aks holda u bahonaga aylanardi."""
    none_actors = {code for code, meta in CAPTURE_ERROR_META.items() if meta.actor == "none"}

    assert none_actors == {"capture_plan_created_late"}


# ---------------------------------------------------------------------------
# `CaptureError`
# ---------------------------------------------------------------------------


def test_capture_error_rejects_an_unknown_code() -> None:
    """Allowlist KONSTRUKTORDA — reyestrdan tashqari kod bazaga TUSHMAYDI."""
    with pytest.raises(ValueError, match="capture_errors.py"):
        CaptureError("capture_made_up_code")


def test_capture_error_keeps_the_code_and_detail() -> None:
    """Kod O'ZGARTIRILMASDAN uzatiladi — u ustun qiymati VA HTTP `detail`."""
    error = CaptureError("capture_timeout", detail="NVR 10 s ichida javob bermadi")

    assert error.code == "capture_timeout"
    assert error.detail == "NVR 10 s ichida javob bermadi"
    assert str(error) == "capture_timeout"


def test_capture_error_truncates_a_long_detail() -> None:
    """Buzilgan NVR megabaytlab javob yuborishi mumkin (T-03-30 naqshi).

    Chegarasiz matn `capture_runs.error_detail` ga cheksiz o'sardi.
    """
    error = CaptureError("capture_invalid_response", detail="x" * (MAX_DETAIL_CHARS + 500))

    assert len(error.detail) == MAX_DETAIL_CHARS + 1, "kesilgan + ellipsis"
    assert error.detail.endswith("…")


def test_capture_error_detail_defaults_to_empty() -> None:
    """`detail` IXTIYORIY — ko'p kodlar uchun kodning o'zi yetarli."""
    error = CaptureError("capture_camera_offline")

    assert error.detail == ""


def test_capture_error_exposes_its_metadata() -> None:
    """Chaqiruvchi retry siyosatini istisnoning O'ZIDAN o'qiy oladi.

    Aks holda har `except` bloki reyestrga qaytib murojaat qilardi va
    ulardan bittasi buni unutardi.
    """
    error = CaptureError("capture_bad_credentials")

    assert error.meta.locks_account is True
    assert error.meta.retry_safe is False
