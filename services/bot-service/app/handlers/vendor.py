"""BOT-02 — sotuvchi o'z qarzini va to'lov tarixini ko'radi (D-03, D-06, D-07).

=============================================================================
⛔⛔ 1-TAQIQ — «BALANS» MA'NOSIDAGI SO'Z NA MATNDA, NA KODDA (D-06).

Loyihada saqlangan qoldiq USTUNI yo'q: son har chaqiruvda
`billing_repo.vendor_outstanding()` ning hisoblanadigan ko'rinishidan
keladi. Nom darajasida ham uni tiklamaslik kerak — «qoldiq» degan
o'zgaruvchi ertaga «shu yerda saqlansa tezroq bo'lardi» degan fikrni
tug'dirardi va o'sha kundan boshlab ikkita haqiqat manbai bo'lardi:
bot bir sonni, qarzdorlik reestri boshqasini ko'rsatardi va ikkalasi
ham «to'g'ri» bo'lardi. Bu aynan SBOZOR mavjud bo'lish sababining
(D-02) teskarisi.

=============================================================================
⛔⛔ 2-TAQIQ — PUL BUTUN SONDA (D-07).

`int` so'm ichkariga ham, tashqariga ham shundayligicha o'tadi:
kasr turlari, yaxlitlash va o'nlik arifmetikasi bu modulda YO'Q. Kunlik
patta yig'indisidagi bir tiyinlik siljish sotuvchi bilan nizoga
aylanardi — ya'ni mahsulot oldini olish uchun mavjud bo'lgan nosozlik
sinfining o'zi.

Formatlash faqat AJRATGICH qo'yadi (`{:,}` -> uzilmas bo'shliq) va
qiymatni O'ZGARTIRMAYDI.

=============================================================================
⛔⛔ 3-TAQIQ — KADR, HAVOLA VA OBYEKT KALITI YO'Q (D-03).

Bot faqat MATN yuboradi. Dalil kadri Telegram'ga chiqsa u chatda
abadiy qoladi, forward qilinadi va uni qaytarib olib bo'lmaydi —
holbuki kadrda boshqa sotuvchilar ham bor. Havola ham qo'shilmaydi:
sotuvchida veb yuzasiga huquq yo'q va havola faqat «kirish rad etildi»
ekraniga olib borardi.

=============================================================================
⚠⚠ SAHIFA KURSORI FSM DA — VA SAHIFALAR NAVBATI, BITTA KURSOR EMAS.

Bir Telegram akkaunti IKKI bozorda faol bo'lishi qonuniy (07-08). Ya'ni
«oxirgi kursor» degan yagona qiymat ikki bozorning tarixini
ARALASHTIRARDI. Shuning uchun FSM da (bozor, kursor) juftliklari
NAVBATI saqlanadi va «Ko'proq» navbatning BIRINCHISINI oldinga suradi.

⚠ Navbat bo'shasa tugma ham YO'QOLADI: bo'sh javob beradigan amalni
  taklif qilish foydalanuvchini «bot buzuq» xulosasiga olib kelardi.
=============================================================================
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final
from uuid import UUID

from aiogram import F, Router
from aiogram.utils.i18n import gettext as _
from aiogram.utils.i18n import ngettext as _n

from app.core_client import CoreApiError, NotBoundError
from app.handlers.start import main_menu_keyboard, share_contact_keyboard
from app.i18n import SUPPORTED_LOCALES, get_i18n

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext
    from aiogram.types import Message

    from app.core_client import CoreClient, PaymentsPage

router = Router(name="vendor")

PAGES_KEY: Final = "payment_pages"
"""FSM kaliti — (bozor, kursor) juftliklari navbati (modul docstringi)."""

THOUSANDS_SEPARATOR: Final = " "
"""Uzilmas bo'shliq: son satr oxirida IKKIGA BO'LINMASIN.

⚠ `frontend` da bu ishni `Intl.NumberFormat` qiladi va u ham aynan shu
  belgini qo'yadi — ya'ni ikki yuza bir xil ko'rinadi.
"""


def _labels(key: str) -> frozenset[str]:
    """Tugma matnining UCHALA tildagi shakli.

    ⛔ FILTR BITTA TILGA BOG'LANMAYDI: foydalanuvchi tugmani bosganda
       Telegram uning MATNINI yuboradi, matn esa o'sha paytdagi
       til bilan chizilgan. Agar keyin til o'zgarsa (yoki klaviatura
       eski xabarda qolsa), bitta tilga bog'langan filtr bosishni
       JIMGINA e'tiborsiz qoldirardi.
    """
    i18n = get_i18n()
    return frozenset(i18n.gettext(key, locale=locale) for locale in SUPPORTED_LOCALES)


DEBT_LABELS: Final = _labels("bot.menu.debt")
PAYMENTS_LABELS: Final = _labels("bot.menu.payments")
MORE_LABELS: Final = _labels("bot.menu.more")


def format_soum(value: int) -> str:
    """Butun so'mni ajratgich bilan chizadi — ⛔ qiymat O'ZGARMAYDI.

    ⚠ Kirish `int` va chiqish `str`: oraliqda kasr turi umuman
      tug'ilmaydi (D-07).
    """
    return f"{value:,}".replace(",", THOUSANDS_SEPARATOR)


def _render_page(page: PaymentsPage) -> str:
    """Bitta sahifani MATNGA aylantiradi (D-03: faqat matn).

    ⛔ KO'PLIK `.po` NING `Plural-Forms` I BILAN: ruschada uchta shakl
       bor va qo'lda yozilgan `if n == 1` birinchi «2 ta yozuv» da
       buzilardi.
    """
    if not page.rows:
        return _("bot.payments.empty")

    count = len(page.rows)
    lines = [_n("bot.payments.header.one", "bot.payments.header.many", count).format(count=count)]
    for row in page.rows:
        lines.append(
            _("bot.payments.row").format(
                date=row.service_date.isoformat(),
                stall=row.stall_code,
                due=format_soum(row.due_soum),
                paid=format_soum(row.paid_soum),
                state=_("bot.payments.settled") if row.settled else _("bot.payments.unsettled"),
            )
        )
    return "\n".join(lines)


async def _answer_not_bound(message: Message) -> None:
    """Bog'lanmagan foydalanuvchini `/start` ga qaytaradi — NEYTRAL matn.

    ⛔ Matn «sizning raqamingiz topilmadi» DEMAYDI: bu javob
       bog'lanmagan HAR KIMGA bir xil bo'lishi kerak (D-26a).
    """
    await message.answer(_("bot.notBound"), reply_markup=share_contact_keyboard())


@router.message(F.text.in_(DEBT_LABELS))
async def on_debt(message: Message, core: CoreClient) -> None:
    """«Qarzim» — har bozor uchun alohida qator.

    ⛔ SON `core-api` DAN KELADI VA BU YERDA QAYTA HISOBLANMAYDI: ikkinchi
       arifmetika ikkinchi haqiqat manbai bo'lardi.
    """
    if message.from_user is None:
        return
    try:
        summary = await core.vendor_summary(telegram_user_id=message.from_user.id)
    except NotBoundError:
        await _answer_not_bound(message)
        return
    except CoreApiError:
        await message.answer(_("bot.error.retry"))
        return

    lines = [_("bot.summary.header")]
    for market in summary.markets:
        stalls = ", ".join(market.stall_codes) if market.stall_codes else _("bot.summary.noStalls")
        lines.append(
            _("bot.summary.market").format(
                stalls=stalls,
                amount=format_soum(market.outstanding_soum),
            )
        )
    await message.answer("\n".join(lines), reply_markup=main_menu_keyboard())


@router.message(F.text.in_(PAYMENTS_LABELS))
async def on_payments(message: Message, core: CoreClient, state: FSMContext) -> None:
    """«To'lovlarim» — har bozorning BIRINCHI sahifasi + navbatni tiklash."""
    if message.from_user is None:
        return
    try:
        summary = await core.vendor_summary(telegram_user_id=message.from_user.id)
        pending: list[list[str]] = []
        chunks: list[str] = []
        for market in summary.markets:
            page = await core.vendor_payments(
                telegram_user_id=message.from_user.id,
                market_id=market.market_id,
            )
            chunks.append(_render_page(page))
            if page.next_cursor is not None:
                pending.append([str(market.market_id), page.next_cursor])
    except NotBoundError:
        await _answer_not_bound(message)
        return
    except CoreApiError:
        await message.answer(_("bot.error.retry"))
        return

    await state.update_data({PAGES_KEY: pending})
    await message.answer(
        "\n\n".join(chunks) if chunks else _("bot.payments.empty"),
        reply_markup=main_menu_keyboard(with_more=bool(pending)),
    )


@router.message(F.text.in_(MORE_LABELS))
async def on_more(message: Message, core: CoreClient, state: FSMContext) -> None:
    """«Ko'proq» — navbatning BIRINCHI bozorini bir sahifa oldinga suradi.

    ⚠ FSM YO'QOLSA (`cache` qayta ko'tarilsa) navbat bo'sh bo'ladi va
      foydalanuvchi «boshqa yozuv qolmadi» matnini oladi. Bu QONUNIY:
      FSM — bir necha daqiqalik dialog bosqichi, biznes holati emas
      (`app/settings.py::DEFAULT_VALKEY_URL`).
    """
    if message.from_user is None:
        return
    data = await state.get_data()
    pages: list[list[str]] = list(data.get(PAGES_KEY) or [])
    if not pages:
        await message.answer(_("bot.payments.noMore"), reply_markup=main_menu_keyboard())
        return

    market_id_raw, cursor = pages[0]
    try:
        page = await core.vendor_payments(
            telegram_user_id=message.from_user.id,
            market_id=UUID(market_id_raw),
            cursor=cursor,
        )
    except NotBoundError:
        await _answer_not_bound(message)
        return
    except CoreApiError:
        await message.answer(_("bot.error.retry"))
        return

    rest = pages[1:]
    if page.next_cursor is not None:
        rest.append([market_id_raw, page.next_cursor])
    await state.update_data({PAGES_KEY: rest})
    await message.answer(
        _render_page(page),
        reply_markup=main_menu_keyboard(with_more=bool(rest)),
    )
