"""Rastadagi QR sahifasining ko'rinishi (261102): logolar, izoh qatorlari, xavfsiz chiqish.

Summa va tugma havolalari integratsiya testlarida (`test_click.py`,
`test_payme.py`); bu yerda faqat sahifani yig'uvchi sof funksiyalar.
Eng muhim shart — izoh qatorlari: ular jamiga teng kelmasa ko'rsatilmaydi,
aks holda sotuvchi ekranda bir-biriga qo'shilmaydigan sonlarni ko'rardi.
"""

from __future__ import annotations

from datetime import date
from uuid import uuid4

import pytest
from app.api.v1 import pay
from app.services.online_payment import StallDue


def _due(total: int, today: int | None, debt: int, paid: int = 0) -> StallDue:
    return StallDue(uuid4(), uuid4(), "27", total, today_soum=today, debt_soum=debt,
                    paid_today_soum=paid)  # fmt: skip


def test_parts_show_today_and_debt_when_they_add_up() -> None:
    assert pay._parts(_due(45000, 22000, 23000)) == [
        ("Bugungi patta", 22000),
        ("Oldingi kunlardan qarz", 23000),
    ]


def test_parts_show_advance_as_negative_row() -> None:
    assert pay._parts(_due(23000, 33000, -10000)) == [("Bugungi patta", 33000), ("Avans", -10000)]


def test_parts_say_remainder_when_part_of_today_is_paid() -> None:
    assert pay._parts(_due(30000, 7000, 23000, paid=15000))[0] == ("Bugungi patta qoldig'i", 7000)


@pytest.mark.parametrize(
    ("due", "caption"),
    [
        (_due(22000, 22000, 0), "Bugungi patta"),
        (_due(23000, None, 23000), "Oldingi kunlardan qarz"),
        (_due(23000, 0, 23000), "Oldingi kunlardan qarz"),
    ],
)
def test_single_component_is_a_caption_not_rows(due: StallDue, caption: str) -> None:
    assert pay._parts(due) == []
    assert pay._caption(due) == caption


def test_rows_that_do_not_add_up_to_the_total_are_not_shown() -> None:
    due = _due(45000, 22000, 20000)
    assert pay._parts(due) == []
    assert pay._caption(due) == "Bugungi patta va qarz bilan"


def test_amounts_use_spaces_and_a_real_minus_sign() -> None:
    assert pay._soum(1234567) == "1 234 567"
    assert pay._soum(-10000) == "−10 000"


def test_logos_ship_with_the_service() -> None:
    for name in ("payme.webp", "click.webp", "karmana.webp"):
        uri = pay._asset(name)
        assert uri is not None and uri.startswith("data:image/webp;base64,"), name


def test_header_uses_market_logo_or_falls_back_to_escaped_name() -> None:
    assert 'alt="Karmana bozor"' in pay._header("karmana", "Karmana bozor")
    plain = pay._header("logosiz", "Bozor <b>1</b>")
    assert "<img" not in plain and "Bozor &lt;b&gt;1&lt;/b&gt;" in plain
    assert "<img" not in pay._header("../../settings", None), "slug fayl yo'liga aylanmasin"


def test_button_escapes_link_and_names_the_provider() -> None:
    html = pay._button("click", "https://my.click.uz/services/pay?service_id=1&amount=2")
    assert 'href="https://my.click.uz/services/pay?service_id=1&amp;amount=2"' in html
    assert 'aria-label="Click bilan to&#x27;lash"' in html


def test_stall_code_is_escaped_in_the_ticket_head() -> None:
    head = pay._head("<script>", date(2026, 11, 2))
    assert "2-noyabr" in head
    assert "<script>" not in head and "&lt;script&gt;" in head
