"""Sotuvchi tarixidagi bir kunning HOLATI — yagona qoida (261006).

=============================================================================
⛔⛔ NEGA SOF FUNKSIYA VA NEGA TEST SHU YERDA.

    Qoida ikki joyda kerak: serverda (javobdagi `status`) va ekranda
    (belgi rangi va matni). Agar klient uni O'ZI hisoblasa, ekran
    «to'landi» deb, hisobot «qarzdor» deb ko'rsatishi mumkin edi va
    qaysi biri rost ekani aniqlanmasdi. Shuning uchun qoida SERVERDA,
    klient esa faqat tarjima qiladi.

    Funksiya sof — DB ham, HTTP ham kerak emas, ya'ni har bir chekka
    holat arzon o'lchanadi.

⛔⛔ KIRISH — FIFO TAQSIMLASHI, O'SHA KUNGI TO'LOV EMAS (261006 tuzatish).

    Birinchi versiya holatni «o'sha kuni hisob / o'sha kuni to'lov» dan
    chiqarardi va prod'da qarzi nolga tushirilgan bozorda 261 kunni
    «to'lanmagan» ko'rsatdi. Kassir bugungi pattani va eski qarzni BITTA
    to'lov bilan oladi, ya'ni «shu kuni to'lov yo'q» ≠ «shu kun to'lanmagan».
    Endi kirish — `vendor_charge_allocation()` ning shu kunga bergan qismi
    (`covered_soum`) va qolgan qarzi (`unpaid_soum`). Haqiqiy bazadagi
    izchillik `tests/integration/test_vendor_history.py` da o'lchanadi.
=============================================================================
"""

from __future__ import annotations

import inspect

import pytest
from app.repositories.report_repo import vendor_day_status


def _holat(*, covered: int = 0, unpaid: int = 0, waived: int = 0, has_charge: bool = True) -> str:
    return vendor_day_status(
        has_charge=has_charge, covered_soum=covered, unpaid_soum=unpaid, waived_soum=waived
    )


def test_HOLAT_OSHA_KUNGI_TOLOVGA_BOGLANA_OLMAYDI():
    """⛔ TUZILMAVIY QULF: funksiyada o'sha kungi to'lov parametri YO'Q.

    Birinchi versiyaning xatosi aynan shu parametr edi (`paid_soum`). U
    qaytib kelsa, holat yana qarzga zid chiqadi — shuning uchun imzo
    o'zi tekshiriladi, xulq testlari esa yetarli emas.
    """
    parametrlar = set(inspect.signature(vendor_day_status).parameters)
    assert parametrlar == {"has_charge", "covered_soum", "unpaid_soum", "waived_soum"}


class TestToliqYopilgan:
    def test_tolangan(self):
        assert _holat(covered=26_000) == "paid"

    def test_qarzi_qolmagan_kun_kechirimsiz_TOLANDI(self):
        """FIFO kunni boshqa kuni berilgan pul bilan yopgan — u baribir yopilgan."""
        assert _holat(covered=26_000, unpaid=0) == "paid"


class TestKechirilgan:
    def test_PUL_TUSHMAGAN_kechirilgan_deb_belgilanadi(self):
        """⛔ ENG MUHIM AJRATISH.

        2026-10-05 da bozorning qarzi kechirilgan edi. Agar bu kunlar
        «to'landi» deb ko'rsatilsa, hisobotda kassaga TUSHMAGAN pul
        tushgandek ko'rinardi — `debt_settlement` moduli aynan shuni
        («soxta to'lov yozilmaydi») rad etgan.
        """
        assert _holat(waived=26_000) == "waived"

    def test_qisman_tolab_qolgani_kechirilgan_bolsa_ham_KECHIRILGAN(self):
        """⛔ ONGLI O'ZGARISH (261006): avval bu «to'landi» edi.

        FIFO bilan kechirim AYNAN qisman qoplangan eng yangi kunlarga
        tushadi — prod'da: hisob 48 000, qoplangan 8 000, kechirilgan
        40 000. Uni yashil «to'landi» deyish 40 000 so'mni kassaga
        tushgandek ko'rsatardi. Tushgan qism esa qatordagi raqamda
        (`covered_soum`) ko'rinadi, ya'ni u yashirilmaydi.
        """
        assert _holat(covered=8_000, waived=40_000) == "waived"


class TestYopilmagan:
    def test_umuman_tolanmagan(self):
        assert _holat(unpaid=26_000) == "unpaid"

    def test_qisman(self):
        assert _holat(covered=10_000, unpaid=16_000) == "partial"

    @pytest.mark.parametrize("kechirilgan", [1, 25_999])
    def test_qisman_kechirim_ham_QISMAN(self, kechirilgan):
        """Kechirim qarzni to'liq yopmasa — kun hali ochiq."""
        assert _holat(waived=kechirilgan, unpaid=26_000 - kechirilgan) == "partial"


class TestHisobsizKun:
    @pytest.mark.parametrize("covered", [0, 26_000])
    def test_hisobsiz_kun_HAR_DOIM_alohida(self, covered):
        """⚠ `advance` — o'sha kuni pul olingan, hisob yozilmagan.

        «To'landi» deb belgilash uni YOPILGAN patta bilan aralashtirardi;
        pul esa sotuvchining umumiy kreditiga qo'shilib eski qarzni yopgan.
        """
        assert _holat(covered=covered, has_charge=False) == "advance"


def test_QARZ_QOLGAN_KUN_HECH_QACHON_YOPILGAN_DEB_BELGILANMAYDI():
    """⛔ QUYI CHEGARA: usiz yuqoridagi testlar «doim `paid`» qaytaradigan
    buzuq funksiya bilan ham qisman yashil bo'lardi."""
    # Oraliq 25 000 dan OLDIN to'xtaydi: 25 000 + 1 000 kechirim kunni to'liq
    # yopadi va u endi qarzli kun emas.
    for qoplangan in range(0, 25_000, 5_000):
        for kechirilgan in (0, 1_000):
            qolgan = 26_000 - qoplangan - kechirilgan
            holat = _holat(covered=qoplangan, waived=kechirilgan, unpaid=qolgan)
            assert holat in {"unpaid", "partial"}, (
                f"qarz {qolgan} qolgan kun {holat!r} deb belgilandi"
            )
