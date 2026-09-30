"""Tarozi sotuvchiga bir marta — pul yechimining IKKI TOSH DARVOZASI.

=============================================================================
NEGA BU FAYL BOR.

`GET /reconciliation/...` kabi yuzalardan farqli o'laroq bu qoida PULGA
tegadi va uning ikki qismi bor:

  1. «bu rasta tarozini ko'taradimi?» — SQL da yechiladi
     (`_STALL_DAY_MONEY` ning `carrier` CTE'si);
  2. «ko'tarmasa nima bo'ladi?» — `_money_from_row()` da.

Integratsiya testi (`test_service_fee_and_roster.py`) birinchisini HTTP
orqali o'lchaydi. Bu yerda ikkinchisi va ular orasidagi SHARTNOMA
o'lchanadi — bazasiz, ya'ni har commitda tez.
"""

from __future__ import annotations

from uuid import uuid4

from app.repositories.billing_repo import _UNBILLABLE_STATUSES, _money_from_row
from sbozor_core.enums import StallStatus


def _pul(*, status: str = "active", carries_fee: bool = True):
    """Yaroqli kirish — faqat o'lchanayotgan maydon o'zgaradi."""
    return _money_from_row(
        stall_id=uuid4(),
        stall_code="1",
        status=status,
        vendor_id=uuid4(),
        tariff_id=uuid4(),
        tariff_amount_soum=20_000,
        fee_amount_soum=4_000,
        fee_label="Tarozi xizmati",
        market_open=True,
        carries_fee=carries_fee,
    )


def test_unbillable_statuses_match_the_money_rule() -> None:
    """⛔ REYESTR `_money_from_row()` DAN AJRALIB KETA OLMAYDI.

    `_UNBILLABLE_STATUSES` SQL ga kerak: `carrier` CTE'si tarozini
    ko'taradigan rastani tanlashda «bu rasta bugun hisob oladimi?» degan
    savolga javob berishi kerak. Lekin HAQIQIY qaror `_money_from_row()`
    da va u holat bo'yicha shoxlanadi.

    ⚠ Ro'yxatni QO'LDA sanab yozish ikkinchi haqiqat manbai bo'lardi:
      yangi holat qo'shilgan kuni SQL uni «hisob oladi» deb hisoblardi,
      tarozi o'sha rastaga tushardi va PUL HECH QAYERDA yozilmasdi —
      jimgina, chunki hech bir test bu juftlikni o'lchamasdi.

    Shuning uchun bu yerda `StallStatus` NING HAR A'ZOSI haqiqiy funksiya
    orqali o'tkaziladi va natija reyestr bilan solishtiriladi.
    """
    hisobsiz = {
        status.value for status in StallStatus if _pul(status=status.value).amount_soum is None
    }

    assert hisobsiz == set(_UNBILLABLE_STATUSES), (
        "`_UNBILLABLE_STATUSES` reyestri `_money_from_row()` bilan mos emas. "
        f"funksiya hisob yozmaydi: {sorted(hisobsiz)}; "
        f"reyestrda: {sorted(_UNBILLABLE_STATUSES)}. "
        "Yangi holat qo'shilgan bo'lsa uni reyestrga ham qo'shing — aks holda "
        "tarozi hisob olmaydigan rastaga tushib, PUL YO'QOLADI."
    )


def test_a_stall_that_does_not_carry_the_fee_gets_zero_and_no_label() -> None:
    """⛔ KO'TARMAYDIGAN RASTADA TAROZI `0` VA NOMI `None`.

    Ikkinchi shart bezak emas: `fee_label` qolib ketsa kassir ekranida
    «Tarozi xizmati» qatori summasiz turardi va kassir to'lanadigan narsa
    bordek o'ylardi. Buyurtmachining talabi aynan shu edi — ikkinchi
    rastada tarozi UMUMAN chiqmasin.
    """
    kotaruvchi = _pul(carries_fee=True)
    assert kotaruvchi.fee_amount_soum == 4_000
    assert kotaruvchi.fee_label == "Tarozi xizmati"
    assert kotaruvchi.amount_soum == 24_000, "ko'taruvchida rasta puli + tarozi"

    boshqa = _pul(carries_fee=False)
    assert boshqa.fee_amount_soum == 0, "ikkinchi rastada tarozi qayta olindi"
    assert boshqa.fee_label is None, "summasiz «Tarozi» qatori kassirni chalg'itadi"
    assert boshqa.amount_soum == 20_000, "ko'tarmaydiganida faqat rasta puli qolishi kerak"

    # ⛔ RASTA PULI IKKALASIDA HAM BIR XIL: qoida tarozига tegadi, tarifga EMAS.
    assert kotaruvchi.tariff_amount_soum == boshqa.tariff_amount_soum == 20_000
