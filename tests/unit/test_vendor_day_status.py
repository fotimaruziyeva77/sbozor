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
=============================================================================
"""

from __future__ import annotations

import pytest
from app.repositories.report_repo import vendor_day_status


class TestToliqYopilgan:
    def test_tolangan(self):
        assert vendor_day_status(charged_soum=26_000, paid_soum=26_000, waived_soum=0) == "paid"

    def test_ortiqcha_tolov_ham_tolangan(self):
        """Sotuvchi ko'proq to'lagan — kun baribir yopilgan."""
        assert vendor_day_status(charged_soum=26_000, paid_soum=30_000, waived_soum=0) == "paid"


class TestKechirilgan:
    def test_PUL_TUSHMAGAN_kechirilgan_deb_belgilanadi(self):
        """⛔ ENG MUHIM AJRATISH.

        2026-10-05 da bozorning 1 176 000 so'm qarzi kechirilgan edi.
        Agar bu kunlar «to'landi» deb ko'rsatilsa, hisobotda kassaga
        TUSHMAGAN pul tushgandek ko'rinardi — `debt_settlement` moduli
        aynan shuni («soxta to'lov yozilmaydi») rad etgan.
        """
        assert vendor_day_status(charged_soum=26_000, paid_soum=0, waived_soum=26_000) == "waived"

    def test_qisman_tolab_qolgani_kechirilgan_bolsa_TOLANDI(self):
        """Pul TUSHGAN, qolgani kechirilgan — bu «to'landi».

        «Kechirilgan» deb belgilash tushgan pulni ko'rinmas qilardi.
        """
        assert vendor_day_status(charged_soum=26_000, paid_soum=20_000, waived_soum=6_000) == "paid"


class TestYopilmagan:
    def test_umuman_tolanmagan(self):
        assert vendor_day_status(charged_soum=26_000, paid_soum=0, waived_soum=0) == "unpaid"

    def test_qisman(self):
        assert vendor_day_status(charged_soum=26_000, paid_soum=10_000, waived_soum=0) == "partial"

    @pytest.mark.parametrize("kechirilgan", [1, 25_999])
    def test_qisman_kechirim_ham_QISMAN(self, kechirilgan):
        """Kechirim qarzni to'liq yopmasa — kun hali ochiq."""
        assert vendor_day_status(
            charged_soum=26_000, paid_soum=0, waived_soum=kechirilgan
        ) == "partial"


class TestHisobsizKun:
    def test_hisobsiz_TOLOV_avans(self):
        """⚠ `advance` — hisobsiz to'lov: oldindan to'lagan yoki hisob
        keyinroq o'chirilgan. «To'landi» deb belgilash uni YOPILGAN patta
        bilan aralashtirardi va kun qarzdor emasdek ko'rinardi."""
        assert vendor_day_status(charged_soum=0, paid_soum=26_000, waived_soum=0) == "advance"

    def test_hisob_ham_tolov_ham_yoq(self):
        assert vendor_day_status(charged_soum=0, paid_soum=0, waived_soum=0) == "paid"


def test_QARZ_HECH_QACHON_tolandi_deb_belgilanmaydi():
    """⛔ QUYI CHEGARA: usiz yuqoridagi testlar «doim `paid`» qaytaradigan
    buzuq funksiya bilan ham qisman yashil bo'lardi."""
    for tolov in range(0, 26_000, 5_000):
        holat = vendor_day_status(charged_soum=26_000, paid_soum=tolov, waived_soum=0)
        assert holat != "paid", f"to'lov {tolov} da qarz 'to'landi' deb belgilandi"
