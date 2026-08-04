"""Obyekt kaliti — deterministik, tartibi muzokara qilinmaydi, foydalanuvchi matnisiz.

Sof funksiya testlarining shakli `test_rtsp_url.py` dan meros: kirish
argumentlardan, chiqish satrdan iborat va hech qanday I/O yo'q.
"""

from __future__ import annotations

from datetime import date, time
from uuid import UUID

import pytest
from app.services.object_key import KEY_PREFIX_FOR_DAY, object_key

_MARKET = UUID("1f0c0000-0000-4000-8000-000000000001")
_CAMERA = UUID("9a2b0000-0000-4000-8000-000000000002")
_DAY = date(2026, 9, 1)
_SLOT = time(6, 30)


def test_key_has_the_documented_shape() -> None:
    """`{market}/{sana}/{kamera}/{HHMM}.jpg` — §D.9 ning aynan shakli."""
    key = object_key(market_id=_MARKET, business_date=_DAY, camera_id=_CAMERA, slot_time=_SLOT)

    assert key == f"{_MARKET}/2026-09-01/{_CAMERA}/0630.jpg"


def test_identical_arguments_produce_an_identical_key() -> None:
    """Determinizm — tasodifiy komponent YO'Q (§B.4).

    ⚠ Bu shunchaki qulaylik emas: siqilgan versiya AYNAN o'sha kalitni
      ustiga yozadi, ya'ni 6-fazadagi dalil havolalari hech qachon
      buzilmasligi kerak. Tasodifiy komponent siqishdan keyin ikkinchi
      obyekt hosil qilardi va eskisi yetim bo'lib qolardi.
    """
    first = object_key(market_id=_MARKET, business_date=_DAY, camera_id=_CAMERA, slot_time=_SLOT)
    second = object_key(market_id=_MARKET, business_date=_DAY, camera_id=_CAMERA, slot_time=_SLOT)

    assert first == second


@pytest.mark.parametrize(
    "slot,expected",
    [
        (time(0, 0), "0000.jpg"),
        (time(6, 30), "0630.jpg"),
        (time(9, 5), "0905.jpg"),
        (time(18, 0), "1800.jpg"),
        (time(23, 59), "2359.jpg"),
    ],
)
def test_slot_time_is_zero_padded_to_four_digits(slot: time, expected: str) -> None:
    """`HHMM` — HAR DOIM to'rt raqam.

    ⚠ To'ldirilmagan shakl (`630.jpg`) leksikografik tartibni buzardi va
      retention'ning prefiks skani kunni NOTO'G'RI tartibda o'qirdi.
    """
    key = object_key(market_id=_MARKET, business_date=_DAY, camera_id=_CAMERA, slot_time=slot)

    assert key.endswith(f"/{expected}")


def test_seconds_and_microseconds_never_reach_the_key() -> None:
    """Slot DAQIQA aniqligida — sekund kalitni idempotentlikdan ayirardi.

    Bir xil slot ikki marta olinsa (retry) kalit BIR XIL bo'lishi shart,
    aks holda ikkinchi urinish ikkinchi obyekt yaratardi va
    `(market, camera, slot, business_date)` idempotentlik kaliti (§B.4)
    ombor darajasida buzilardi.
    """
    key = object_key(
        market_id=_MARKET,
        business_date=_DAY,
        camera_id=_CAMERA,
        slot_time=time(6, 30, 45, 123456),
    )

    assert key.endswith("/0630.jpg")


def test_key_cannot_express_a_path_escape() -> None:
    """⛔ T-04-27 / ASVS V12.3 — yo'l chiqishi STRUKTURAVIY mumkin emas.

    Kalit FAQAT `UUID`, ISO sana va `HHMM` dan quriladi. Foydalanuvchi
    matni (kamera nomi, bozor nomi, fayl nomi) UMUMAN kirmaydi, ya'ni
    `../` yozib bo'ladigan joy YO'Q.

    Bu «tozalash» (sanitizatsiya) emas: tozalash chetlab o'tilishi mumkin,
    struktura esa yo'q — imzoni o'zgartirmasdan foydalanuvchi matnini
    kalitga qo'shib bo'lmaydi va imzo o'zgarishi diffda ko'rinadi
    (`rtsp.py` ning parol parametri bilan bir xil qaror).
    """
    key = object_key(market_id=_MARKET, business_date=_DAY, camera_id=_CAMERA, slot_time=_SLOT)

    assert ".." not in key
    assert "//" not in key
    assert not key.startswith("/")
    assert "\\" not in key
    assert "\x00" not in key
    assert all(segment for segment in key.split("/")), "bo'sh segment YO'Q"


def test_the_key_uses_only_url_safe_characters() -> None:
    """Kalit S3 ning yo'l qismiga foizli kodlashsiz tushadi."""
    key = object_key(market_id=_MARKET, business_date=_DAY, camera_id=_CAMERA, slot_time=_SLOT)

    allowed = set("abcdefghijklmnopqrstuvwxyz0123456789-./")
    assert set(key) <= allowed, f"kutilmagan belgilar: {sorted(set(key) - allowed)}"


def test_market_comes_before_the_date_and_the_date_before_the_camera() -> None:
    """⛔ TARTIB MUZOKARA QILINMAYDI (§D.9).

    Eng katta ommaviy amal — retention: u KUNLIK va barcha kameralar
    ustidan yuradi. `market/sana/kamera` da bu BITTA prefiks skani;
    `market/kamera/sana` da esa N ta skan (har kamera uchun bittadan).
    """
    key = object_key(market_id=_MARKET, business_date=_DAY, camera_id=_CAMERA, slot_time=_SLOT)
    segments = key.split("/")

    assert segments[0] == str(_MARKET)
    assert segments[1] == "2026-09-01"
    assert segments[2] == str(_CAMERA)


def test_day_prefix_is_a_prefix_of_every_key_of_that_day() -> None:
    """Retention `ListObjectsV2` prefiksi — kalit bilan BOG'LANGAN.

    Ikkalasi mustaqil qurilsa prefiks bir kun kalitdan ajralib ketardi va
    retention JIMGINA hech nima topmasdi — ya'ni eski kadrlar muddatsiz
    saqlanib qolardi va nosozlik faqat disk to'lganda ko'rinardi.
    """
    prefix = KEY_PREFIX_FOR_DAY(market_id=_MARKET, business_date=_DAY)

    for slot in (time(6, 0), time(6, 30), time(18, 0)):
        key = object_key(market_id=_MARKET, business_date=_DAY, camera_id=_CAMERA, slot_time=slot)
        assert key.startswith(prefix)


def test_day_prefix_ends_with_a_separator() -> None:
    """Ajratuvchisiz prefiks `2026-09-1` bilan `2026-09-10` ni ARALASHTIRARDI."""
    prefix = KEY_PREFIX_FOR_DAY(market_id=_MARKET, business_date=_DAY)

    assert prefix.endswith("/")
    assert prefix == f"{_MARKET}/2026-09-01/"


def test_day_prefix_does_not_match_a_neighbouring_day() -> None:
    """Nazorat holati — prefiks HAQIQATAN kunni ajratadi."""
    prefix = KEY_PREFIX_FOR_DAY(market_id=_MARKET, business_date=_DAY)
    other = object_key(
        market_id=_MARKET,
        business_date=date(2026, 9, 10),
        camera_id=_CAMERA,
        slot_time=_SLOT,
    )

    assert not other.startswith(prefix)


def test_different_markets_never_share_a_prefix() -> None:
    """Bitta bucket, `market_id` — BIRINCHI prefiks (§D.9)."""
    other_market = UUID("1f0c0000-0000-4000-8000-000000000099")

    mine = object_key(market_id=_MARKET, business_date=_DAY, camera_id=_CAMERA, slot_time=_SLOT)
    theirs = object_key(
        market_id=other_market, business_date=_DAY, camera_id=_CAMERA, slot_time=_SLOT
    )

    assert not mine.startswith(KEY_PREFIX_FOR_DAY(market_id=other_market, business_date=_DAY))
    assert not theirs.startswith(KEY_PREFIX_FOR_DAY(market_id=_MARKET, business_date=_DAY))


def test_arguments_are_keyword_only() -> None:
    """Pozitsion chaqiruv ikki `UUID` ni ALMASHTIRIB yuborishi mumkin edi.

    `market_id` va `camera_id` bir xil tipda, ya'ni ularni joyini
    almashtirish tip xatosi BERMASDI — kalit «to'g'ri ko'rinishda»
    qurilardi va kadrlar boshqa bozorning prefiksiga tushardi.
    """
    with pytest.raises(TypeError):
        object_key(_MARKET, _DAY, _CAMERA, _SLOT)  # type: ignore[misc]
