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
from uuid import UUID

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
from fixtures.telegram import make_bot, make_contact, make_message, sent_texts

from app.core_client import (
    ChargeRow,
    MarketSummary,
    PaymentsPage,
    ResolveResult,
    VendorRef,
    VendorSummary,
)
from app.handlers.vendor import PAGES_KEY, format_soum, on_debt, on_more, on_payments
from app.i18n import get_i18n

if TYPE_CHECKING:
    from collections.abc import Iterator

    from aiogram import Bot
    from aiogram.types import Message
    from aiogram.utils.i18n import I18n

VENDOR_SOURCE: Final = (
    Path(__file__).resolve().parents[2] / "app" / "handlers" / "vendor.py"
).read_text(encoding="utf-8")

AS_OF: Final = date(2026, 8, 12)

SECOND_MARKET_ID: Final = UUID("33333333-3333-4333-8333-333333333333")
"""IKKINCHI bozor — WR-03 ning butun mavzusi.

Bir Telegram akkaunti ikki bozorda faol bo'lishi QONUNIY (07-08), ya'ni
`fixtures/core_double.py` ning bitta bozorli yordamchisi bu sinfni
o'lchay olmaydi: u bilan «qaysi blok qaysi bozorniki» degan savolning
O'ZI tug'ilmasdi.
"""


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
    # ⚠ NAVBAT ELEMENTI UCH A'ZOLI: (bozor, kursor, RASTA KODLARI). Uchinchi
    #   a'zo WR-03 uchun kerak — «Ko'proq» dan kelgan sahifa ham qaysi
    #   bozorniki ekanini AYTISHI shart, ikkinchi so'rov OCHMASDAN.
    assert (await state.get_data())[PAGES_KEY] == [[str(MARKET_ID), "2026-08-10|A-01", "A-01"]]
    # ⛔ Sahifa hajmi — oxirgi 10 qator (`DEFAULT_PAGE_SIZE`).
    assert core.payments_calls[0]["limit"] == 10
    assert core.payments_calls[0]["cursor"] is None


async def test_more_advances_the_queue_and_clears_it_at_the_end(locale: I18n) -> None:
    """«Ko'proq» navbatning BIRINCHISINI suradi; oxirida navbat bo'shaydi."""
    bot, session = make_bot()
    core = CoreDouble(pages=[_page(rows=3, cursor=None, start_day=11)])
    state = make_state()
    await state.update_data({PAGES_KEY: [[str(MARKET_ID), "2026-08-10|A-01", "A-01"]]})
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
# ⛔⛔ WR-02 — BUZUQ FSM SUKUNAT BERMAYDI
#
# FSM `db 1` da, `--save "" --appendonly no` bilan yashaydi va u SXEMA
# VERSIYASINI tashimaydi. Navbat elementi bu rejada IKKI a'zolidan UCH
# a'zoliga o'tdi (WR-03), ya'ni tirik Valkey'da qolgan ESKI kalitlar
# aynan shu yo'ldan o'tadi — bu farazi emas, shu commitning FAKTI.
#
# Ilgari `market_id_raw, cursor = pages[0]` `try` dan TASHQARIDA edi:
# istisno aiogram jurnaliga tushardi, foydalanuvchi esa HECH QANDAY
# javob olmasdi.
# ---------------------------------------------------------------------------


def stale_text() -> str:
    return get_i18n().gettext("bot.payments.stale", locale="uz_Latn")


async def test_more_with_a_legacy_two_element_entry_answers_instead_of_raising(
    locale: I18n,
) -> None:
    """⛔ ESKI IKKI A'ZOLI YOZUV — `ValueError` emas, NOMLANGAN javob."""
    bot, session = make_bot()
    core = CoreDouble()
    state = make_state()
    # Aynan shu shakl 08-11 dan OLDIN yozilgan va u Valkey'da qolgan.
    await state.update_data({PAGES_KEY: [[str(MARKET_ID), "2026-08-10|A-01"]]})
    message = make_message(text="Ko'proq").as_(bot)

    await on_more(message, core=core, state=state)

    (text,) = sent_texts(session)
    assert text == stale_text()
    # ⛔ «Boshqa yozuv qolmadi» EMAS: u O'LCHANGAN FAKT da'vosi bo'lardi,
    #    holbuki haqiqat — «saqlangan holat buzuq». Ikkisi boshqa gap.
    assert text != get_i18n().gettext("bot.payments.noMore", locale="uz_Latn")
    # Buzuq navbat TOZALANADI — aks holda har bosish o'sha yo'lga tushardi.
    assert (await state.get_data())[PAGES_KEY] == []
    assert core.payments_calls == []


async def test_more_with_a_non_uuid_market_id_answers_instead_of_raising(
    locale: I18n,
) -> None:
    """⛔ `UUID("...")` ning `ValueError` i ham JAVOBGA aylanadi."""
    bot, session = make_bot()
    core = CoreDouble()
    state = make_state()
    await state.update_data({PAGES_KEY: [["bozor-emas", "2026-08-10|A-01", "A-01"]]})
    message = make_message(text="Ko'proq").as_(bot)

    await on_more(message, core=core, state=state)

    (text,) = sent_texts(session)
    assert text == stale_text()
    assert (await state.get_data())[PAGES_KEY] == []
    # ⛔ Yaroqsiz identifikator `core-api` ga UMUMAN yuborilmaydi.
    assert core.payments_calls == []


# ---------------------------------------------------------------------------
# ⛔⛔ WR-03 — HAR BLOK QAYSI BOZORNIKI EKANINI AYTADI
#
# `core_client.py` ning o'z asosi: «serverda "birinchisini tanlash"
# sotuvchiga BOSHQA bozorning tarixini ko'rsatardi». Server tanlamaydi,
# lekin klient ikkalasini AJRATMASDAN yopishtirsa natija o'sha bo'lardi.
# ---------------------------------------------------------------------------


def market_header(stalls: str) -> str:
    return get_i18n().gettext("bot.payments.marketHeader", locale="uz_Latn").format(stalls=stalls)


def market_fallback(market: str) -> str:
    return get_i18n().gettext("bot.payments.marketFallback", locale="uz_Latn").format(market=market)


def _two_market_summary() -> VendorSummary:
    """Ikki bozorda faol sotuvchi — 07-08 ga ko'ra QONUNIY holat."""
    return VendorSummary(
        markets=[
            MarketSummary(
                market_id=MARKET_ID,
                vendor_id=VENDOR_ID,
                outstanding_soum=15000,
                as_of=AS_OF,
                stall_codes=["A-01"],
            ),
            MarketSummary(
                market_id=SECOND_MARKET_ID,
                vendor_id=VENDOR_ID,
                outstanding_soum=5000,
                as_of=AS_OF,
                stall_codes=["B-07"],
            ),
        ]
    )


async def test_payments_labels_every_block_with_its_own_market(locale: I18n) -> None:
    """⛔ IKKI BOZORLI SOTUVCHI QAYSI BLOK KIMNIKI EKANINI KO'RADI."""
    bot, session = make_bot()
    core = CoreDouble(
        summary=_two_market_summary(),
        pages=[
            _page(rows=2, cursor=None),
            _page(rows=2, cursor=None, start_day=20),
        ],
    )
    message = make_message(text="To'lovlarim").as_(bot)

    await on_payments(message, core=core, state=make_state())

    (text,) = sent_texts(session)
    assert market_header("A-01") in text
    assert market_header("B-07") in text
    # ⛔ IKKINCHI SO'ROV OCHILMAYDI: yorliq `vendor_summary` javobidan
    #    keladi, ya'ni bozor nomi uchun alohida chaqiruv YO'Q.
    assert core.summary_calls == [777]
    assert len(core.payments_calls) == 2


async def test_more_says_which_market_the_next_page_belongs_to(locale: I18n) -> None:
    """⛔ «Ko'proq» bozorlarni AYLANTIRADI — sahifa o'zini tanishtirishi shart."""
    bot, session = make_bot()
    core = CoreDouble(pages=[_page(rows=3, cursor=None, start_day=11)])
    state = make_state()
    await state.update_data({PAGES_KEY: [[str(SECOND_MARKET_ID), "2026-08-10|B-07", "B-07"]]})
    message = make_message(text="Ko'proq").as_(bot)

    await on_more(message, core=core, state=state)

    (text,) = sent_texts(session)
    assert market_header("B-07") in text
    assert core.payments_calls[0]["market_id"] == SECOND_MARKET_ID


async def test_a_market_without_stall_codes_is_named_by_its_identifier(
    locale: I18n,
) -> None:
    """⛔ RASTA KODI YO'Q BO'LSA SARLAVHA BO'SH QOLMAYDI.

    Bo'sh yorliq ikki bozorli sotuvchida ikkala blokni ham
    AJRATIB BO'LMAS qilardi. To'qilgan nom ham yozilmaydi — bozorning
    identifikatori qisqartirilgan shaklda ko'rsatiladi.
    """
    bot, session = make_bot()
    core = CoreDouble(
        summary=one_market_summary(0, as_of=AS_OF, codes=()),
        pages=[_page(rows=1, cursor=None)],
    )
    message = make_message(text="To'lovlarim").as_(bot)

    await on_payments(message, core=core, state=make_state())

    (text,) = sent_texts(session)
    assert market_fallback(str(MARKET_ID)[:8]) in text
    # Nazorat: sarlavha HAQIQATAN identifikatorni tashiydi.
    assert str(MARKET_ID)[:8] in text


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


# ---------------------------------------------------------------------------
# ⛔⛔ WR-04 — ZAXIRA HANDLER: FILTRGA TUSHMAGAN XABAR HAM JAVOB OLADI
#
# ⚠ BU YERDA HANDLER TO'G'RIDAN-TO'G'RI CHAQIRILMAYDI — ROUTER DARAXTI
#   O'LCHANADI, VA BU FARQ BUTUN MAVZUNING O'ZI. `on_unknown` ni qo'lda
#   chaqirish «u javob qaytaradimi?» degan SAVOLGA javob berardi, holbuki
#   WR-04 ning savoli boshqa: «filtrga tushmagan xabar UNGACHA yetib
#   boradimi, va u boshqa oqimlarni USHLAB QOLMAYDIMI?». Ikkinchi savol
#   faqat haqiqiy `propagate_event` bilan o'lchanadi.
#
# ⚠ `build_router()` BU YERDA CHAQIRILMAYDI: `include_router` bolaga
#   `parent_router` YOZADI va ikkinchi chaqiruv «Router is already
#   attached» bilan yiqilardi. `app.main.dp` esa import paytida BIR
#   MARTA quriladi — `test_binding.py` ham aynan shu nusxani o'qiydi.
# ---------------------------------------------------------------------------


async def _route(message: Message, bot: Bot, core: CoreDouble) -> None:
    """Xabarni HAQIQIY router daraxti bo'ylab yuboradi (filtrlar bilan).

    ⚠ `bot=` va `state=` QO'LDA uzatiladi: ularni odatda `Dispatcher`
      ning `update` observeridagi outer middleware'lari qo'yadi, bu yerda
      esa `message` observeri to'g'ridan-to'g'ri qo'zg'atiladi. `Command`
      filtri `bot` ni TALAB qiladi va usiz `/start` darvozasi umuman
      hal bo'lmasdi.
    """
    from app.main import dp

    await dp.propagate_event("message", message, bot=bot, core=core, state=make_state())


def test_the_fallback_router_is_the_last_one() -> None:
    """⛔ TARTIB MAJBURIY — zaxira router ro'yxatning OXIRIDA.

    Filtrsiz router boshda (yoki o'rtada) tursa u `CommandStart()`,
    `F.contact` va uchala tugma matnini USHLAB QOLARDI: mavjud oqimlar
    jimgina o'lardi va HECH NIMA qizarmasdi — chunki bot baribir javob
    qaytarardi, faqat NOTO'G'RI javobni.
    """
    from app.main import dp

    (bot_router,) = dp.sub_routers
    names = [sub_router.name for sub_router in bot_router.sub_routers]

    # ⛔ QUYI CHEGARA: ro'yxat qisqarib qolsa quyidagi tenglik ham
    #    (bitta router qolganda) JIMGINA yashil bo'lardi.
    assert len(names) >= 4, names
    assert names[-1] == "fallback", (
        f"zaxira router ro'yxatning OXIRIDA emas: {names}. Bu tartibda u "
        "mavjud filtrlarni ushlab qolardi (WR-04 ning tuzatishi o'z "
        "oqimlarini o'ldirardi)"
    )


async def test_an_unrecognised_text_still_gets_an_answer(locale: I18n) -> None:
    """⛔ WR-04: sotuvchi yozgan HAR xabar javob oladi — mutlaq sukunat yo'q.

    Bugungi holat `app/main.py:130-136` ning o'z asosiga zid edi:
    «Botning butun qiymati — sotuvchi yozgan xabar javob oladi».
    """
    bot, session = make_bot()
    core = CoreDouble()
    message = make_message(text="qarzim qancha?").as_(bot)

    await _route(message, bot, core)

    (text,) = sent_texts(session)
    assert text == get_i18n().gettext("bot.unknown", locale="uz_Latn")
    # ⛔ D-24: javob foydalanuvchi TERGAN matnni O'QIMAYDI va uni
    #    TAKRORLAMAYDI — u faqat mavjud tugmalarni eslatadi.
    assert "qarzim qancha?" not in text.lower()
    # ⛔ ZAXIRA `core-api` GA CHIQMAYDI: filtrga tushmagan har xabar
    #    so'rov tug'dirsa, begona odam botga matn yozib turib HAQIQIY
    #    sotuvchining rate-limit sanagichini yeb qo'ya olardi.
    assert core.summary_calls == []
    assert core.payments_calls == []


async def test_the_start_command_still_reaches_its_own_handler(locale: I18n) -> None:
    """⛔ Zaxira `/start` ni USHLAB QOLMAYDI (tartibning birinchi isboti)."""
    bot, session = make_bot()
    core = CoreDouble(summary=one_market_summary(0, as_of=AS_OF))
    message = make_message(text="/start").as_(bot)

    await _route(message, bot, core)

    (text,) = sent_texts(session)
    assert text == get_i18n().gettext("bot.start.bound", locale="uz_Latn")
    assert text != get_i18n().gettext("bot.unknown", locale="uz_Latn")
    # Ijobiy nazorat: `/start` HAQIQATAN o'z handleriga tushdi — u
    # `core.vendor_summary` ni chaqiradi, zaxira esa chaqirmaydi.
    assert core.summary_calls == [777]


async def test_a_shared_contact_still_reaches_its_own_handler(locale: I18n) -> None:
    """⛔ Zaxira `F.contact` ni USHLAB QOLMAYDI (tartibning ikkinchi isboti).

    ⚠ Bu darvoza D-24 uchun ham muhim: kontakt oqimi zaxira ortida
      qolsa bog'lanishning YAGONA qonuniy yo'li yopilardi.
    """
    bot, session = make_bot()
    core = CoreDouble(
        resolve_result=ResolveResult(
            status="bound",
            vendor=VendorRef(market_id=MARKET_ID, vendor_id=VENDOR_ID),
        )
    )
    message = make_message(contact=make_contact(user_id=777)).as_(bot)

    await _route(message, bot, core)

    (text,) = sent_texts(session)
    assert text == get_i18n().gettext("bot.binding.ok", locale="uz_Latn")
    assert text != get_i18n().gettext("bot.unknown", locale="uz_Latn")
    assert len(core.resolve_calls) == 1


def test_the_fallback_text_exists_in_every_locale() -> None:
    """⛔ D-31: `bot.unknown` UCHALA katalogda ham BOR va BO'SH EMAS.

    ⚠ `test_locale_parity.py` to'plam TENGLIGINI o'lchaydi, ya'ni kalit
      uchala katalogdan BIRDAN tushib qolganda u yashil qolardi. Bu test
      esa kalitni NOMMA-NOM talab qiladi.
    """
    engine = get_i18n()
    rendered = {
        locale: engine.gettext("bot.unknown", locale=locale)
        for locale in ("uz_Latn", "uz_Cyrl", "ru")
    }

    for locale, text in rendered.items():
        assert text and text != "bot.unknown", f"{locale}: tarjima yo'q ({text!r})"
    assert len(set(rendered.values())) == 3, (
        f"kamida ikki locale bir xil matn berdi — tarjima nusxalangan: {rendered}"
    )
