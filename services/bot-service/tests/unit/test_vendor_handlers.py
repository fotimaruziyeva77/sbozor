"""BOT-02 — qoldiq va to'lov tarixi; ⛔ D-03 / D-06 / D-07 darvozalari.

=============================================================================
⛔ MANBA SKANLARI SHU YERDA VA ULAR REJANING `grep` MEZONLARINING
   BAJARILADIGAN SHAKLI.

Reja to'rt sanoq talab qiladi (`balance` / `float(`/`round(`/`Decimal` /
`http`/`snapshot`). Ular qo'lda yugurtiriladigan buyruq bo'lib qolsa
birinchi kunidayoq unutilardi — shu sababdan skaner shu faylda va u
`bot:test` bilan HAR SAFAR yuguradi.

⚠ Skaner maydoni QAT'IY: faqat `app/handlers/vendor.py` ning matni.
  Bu faylning O'Z manbasi hech qachon o'qilmaydi — aks holda quyidagi
  taqiq nomlari (ular bu yerda YOZILISHI SHART) darvozani o'z sababi
  bilan qizartirardi (02-23 / 03-07 darsi).
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING, Final

import pytest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage
from fixtures.core_double import (
    MARKET_ID,
    VENDOR_ID,
    CoreDouble,
    failing_double,
    one_market_summary,
)
from fixtures.telegram import make_bot, make_message, sent_texts

from app.core_client import ChargeRow, PaymentsPage, VendorSummary
from app.handlers.vendor import PAGES_KEY, format_soum, on_debt, on_more, on_payments
from app.i18n import get_i18n

if TYPE_CHECKING:
    from collections.abc import Iterator

    from aiogram.utils.i18n import I18n

VENDOR_SOURCE: Final = (
    Path(__file__).resolve().parents[2] / "app" / "handlers" / "vendor.py"
).read_text(encoding="utf-8")

AS_OF: Final = date(2026, 8, 12)


@pytest.fixture
def locale() -> Iterator[I18n]:
    engine = get_i18n()
    with engine.context(), engine.use_locale("uz_Latn"):
        yield engine


def make_state() -> FSMContext:
    """Haqiqiy `FSMContext` — xotira omborida (⛔ Valkey'ga chiqmaydi)."""
    return FSMContext(
        storage=MemoryStorage(),
        key=StorageKey(bot_id=1, chat_id=777, user_id=777),
    )


def _page(*, rows: int, cursor: str | None, start_day: int = 1) -> PaymentsPage:
    return PaymentsPage(
        market_id=MARKET_ID,
        vendor_id=VENDOR_ID,
        rule="FIFO_OLDEST_SERVICE_DATE_FIRST",
        rows=[
            ChargeRow(
                service_date=date(2026, 8, start_day + index),
                stall_code="A-01",
                due_soum=15000,
                paid_soum=15000 if index % 2 == 0 else 0,
                settled=index % 2 == 0,
            )
            for index in range(rows)
        ],
        next_cursor=cursor,
    )


# ---------------------------------------------------------------------------
# ⛔ MANBA SKANLARI (rejaning `grep` mezonlari)
# ---------------------------------------------------------------------------


def test_the_scanned_source_is_not_empty() -> None:
    """QUYI CHEGARA — fayl ko'chirilsa quyidagi to'rtta sanoq JIMGINA 0 bo'lardi."""
    assert len(VENDOR_SOURCE) > 1000
    assert "on_debt" in VENDOR_SOURCE


def test_the_stored_balance_word_never_appears(locale: I18n) -> None:
    """⛔ D-06: saqlangan qoldiq ustuni yo'q — nom darajasida ham tiklanmaydi."""
    assert re.findall(r"\bbalance\b", VENDOR_SOURCE, re.IGNORECASE) == []


def test_no_fractional_money_arithmetic() -> None:
    """⛔ D-07: pul BUTUN sonda — kasr turi va yaxlitlash YO'Q."""
    assert re.findall(r"\bfloat\(|\bround\(|Decimal", VENDOR_SOURCE) == []


def test_no_evidence_frame_or_link_reaches_the_bot() -> None:
    """⛔ D-03: bot faqat MATN yuboradi — kadr ham, havola ham yo'q."""
    assert re.findall(r"https?://|snapshot", VENDOR_SOURCE, re.IGNORECASE) == []


# ---------------------------------------------------------------------------
# Formatlash
# ---------------------------------------------------------------------------


def test_amounts_are_formatted_from_an_integer() -> None:
    """Ajratgich qo'yiladi, qiymat O'ZGARMAYDI."""
    # ⚠ Ajratgich — UZILMAS bo'shliq (U+00A0), oddiy bo'shliq emas.
    assert format_soum(1234567) == "1 234 567"
    assert format_soum(0) == "0"
    assert format_soum(-5000) == "-5 000"


# ---------------------------------------------------------------------------
# «Qarzim»
# ---------------------------------------------------------------------------


async def test_debt_text_shows_the_amount_and_the_stall(locale: I18n) -> None:
    """Qoldiq matni: rasta kodi + butun songa formatlangan summa."""
    bot, session = make_bot()
    core = CoreDouble(summary=one_market_summary(1250000, as_of=AS_OF, codes=("A-01",)))
    message = make_message(text="Qarzim").as_(bot)

    await on_debt(message, core=core)

    (text,) = sent_texts(session)
    assert core.summary_calls == [777]
    assert "A-01" in text
    assert "1 250 000" in text
    assert "qarz" in text.lower()
    # ⛔ D-03 / D-04: matnda havola ham, istisno tafsiloti ham yo'q.
    assert "http" not in text.lower()
    assert "snapshot" not in text.lower()


async def test_debt_for_an_unbound_user_sends_the_neutral_text(locale: I18n) -> None:
    """`404` — HOLAT, xato emas: foydalanuvchi `/start` ga qaytariladi."""
    bot, session = make_bot()
    core = failing_double(404)
    message = make_message(text="Qarzim").as_(bot)

    await on_debt(message, core=core)

    (text,) = sent_texts(session)
    assert text == get_i18n().gettext("bot.notBound", locale="uz_Latn")
    assert text != get_i18n().gettext("bot.error.retry", locale="uz_Latn")


async def test_debt_on_a_server_failure_shows_the_retry_text(locale: I18n) -> None:
    """Nosozlikda «keyinroq urinib ko'ring» — istisno TAFSILOTI yo'q."""
    bot, session = make_bot()
    core = failing_double(500)
    message = make_message(text="Qarzim").as_(bot)

    await on_debt(message, core=core)

    (text,) = sent_texts(session)
    assert text == get_i18n().gettext("bot.error.retry", locale="uz_Latn")
    assert "500" not in text
    assert "HTTPStatusError" not in text


async def test_debt_with_no_stall_codes_does_not_render_an_empty_gap(locale: I18n) -> None:
    """Rasta biriktirilmagan bo'lsa — NOMLANGAN holat, bo'sh joy emas."""
    bot, session = make_bot()
    core = CoreDouble(summary=one_market_summary(0, as_of=AS_OF, codes=()))
    message = make_message(text="Qarzim").as_(bot)

    await on_debt(message, core=core)

    (text,) = sent_texts(session)
    assert get_i18n().gettext("bot.summary.noStalls", locale="uz_Latn") in text


# ---------------------------------------------------------------------------
# «To'lovlarim» va «Ko'proq»
# ---------------------------------------------------------------------------


async def test_payments_renders_a_page_and_stores_the_cursor(locale: I18n) -> None:
    """Birinchi sahifa chiziladi va kursor FSM da NAVBAT sifatida saqlanadi."""
    bot, session = make_bot()
    core = CoreDouble(
        summary=one_market_summary(15000, as_of=AS_OF),
        pages=[_page(rows=10, cursor="2026-08-10|A-01")],
    )
    state = make_state()
    message = make_message(text="To'lovlarim").as_(bot)

    await on_payments(message, core=core, state=state)

    (text,) = sent_texts(session)
    assert "A-01" in text
    assert "15 000" in text
    assert (await state.get_data())[PAGES_KEY] == [[str(MARKET_ID), "2026-08-10|A-01"]]
    # ⛔ Sahifa hajmi — oxirgi 10 qator (`DEFAULT_PAGE_SIZE`).
    assert core.payments_calls[0]["limit"] == 10
    assert core.payments_calls[0]["cursor"] is None


async def test_more_advances_the_queue_and_clears_it_at_the_end(locale: I18n) -> None:
    """«Ko'proq» navbatning BIRINCHISINI suradi; oxirida navbat bo'shaydi."""
    bot, session = make_bot()
    core = CoreDouble(pages=[_page(rows=3, cursor=None, start_day=11)])
    state = make_state()
    await state.update_data({PAGES_KEY: [[str(MARKET_ID), "2026-08-10|A-01"]]})
    message = make_message(text="Ko'proq").as_(bot)

    await on_more(message, core=core, state=state)

    assert core.payments_calls[0]["cursor"] == "2026-08-10|A-01"
    assert (await state.get_data())[PAGES_KEY] == []
    (text,) = sent_texts(session)
    assert "2026-08-11" in text


async def test_more_without_a_stored_cursor_says_there_is_nothing_left(
    locale: I18n,
) -> None:
    """⛔ FSM yo'qolganda ham javob bor — jim qolish «bot buzuq» bo'lardi."""
    bot, session = make_bot()
    core = CoreDouble()
    message = make_message(text="Ko'proq").as_(bot)

    await on_more(message, core=core, state=make_state())

    (text,) = sent_texts(session)
    assert text == get_i18n().gettext("bot.payments.noMore", locale="uz_Latn")
    assert core.payments_calls == []


async def test_payments_for_an_unbound_user_sends_the_neutral_text(locale: I18n) -> None:
    """`404` — `/start` ga qaytaruvchi neytral matn."""
    bot, session = make_bot()
    core = failing_double(404)
    message = make_message(text="To'lovlarim").as_(bot)

    await on_payments(message, core=core, state=make_state())

    (text,) = sent_texts(session)
    assert text == get_i18n().gettext("bot.notBound", locale="uz_Latn")


async def test_payments_with_no_markets_does_not_crash(locale: I18n) -> None:
    """Bozorlar ro'yxati bo'sh bo'lsa ham javob bor (bo'sh xabar EMAS)."""
    bot, session = make_bot()
    core = CoreDouble(summary=VendorSummary(markets=[]))
    message = make_message(text="To'lovlarim").as_(bot)

    await on_payments(message, core=core, state=make_state())

    (text,) = sent_texts(session)
    assert text == get_i18n().gettext("bot.payments.empty", locale="uz_Latn")


# ---------------------------------------------------------------------------
# ⛔ KO'PLIK — `.po` NING `Plural-Forms` I, `if n == 1` EMAS
# ---------------------------------------------------------------------------


def test_the_russian_header_uses_three_distinct_plural_forms() -> None:
    """⛔ 1 / 2 / 5 — ruschada UCH XIL shakl.

    Qo'lda yozilgan `if n == 1` shu yerda buzilardi: u 2 va 5 uchun
    AYNI matnni bergan bo'lardi.
    """
    engine = get_i18n()
    forms = {
        count: engine.gettext(
            "bot.payments.header.one", "bot.payments.header.many", count, locale="ru"
        )
        for count in (1, 2, 5)
    }
    assert len(set(forms.values())) == 3, forms


def test_the_uzbek_header_uses_two_plural_forms() -> None:
    """O'zbekchada son bilan kelishuv yo'q — ikkala shakl ham bir xil matn."""
    engine = get_i18n()
    single = engine.gettext(
        "bot.payments.header.one", "bot.payments.header.many", 1, locale="uz_Latn"
    )
    plural = engine.gettext(
        "bot.payments.header.one", "bot.payments.header.many", 5, locale="uz_Latn"
    )
    assert single == plural
    # Nazorat: matn chizildi, msgid QAYTMADI (bo'sh `msgstr` belgisi).
    assert not single.startswith("bot.payments")
