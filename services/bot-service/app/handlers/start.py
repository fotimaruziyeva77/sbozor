"""`/start`, `/help` va ikkita klaviatura (BOT-01 ning kirish nuqtasi).

=============================================================================
⛔⛔ `request_contact=True` — VA NEGA AYNAN U.

Telegram `Contact` obyektida `user_id` IXTIYORIY maydon
[core.telegram.org/bots/api#contact]. U SENDER bilan teng bo'lishi
KAFOLATLANADIGAN yagona holat — foydalanuvchi AYNAN SHU tugmani,
AYNAN SHAXSIY chatda bosgani. Boshqa har qanday yo'l (vCard, forward,
qo'lda qo'shilgan kontakt) `user_id` ni yo `bo'sh`, yo BOSHQA odamniki
qilib qoldiradi.

⚠ `request_contact` GURUH CHATIDA UMUMAN ISHLAMAYDI (Bot API cheklovi) —
  ya'ni bu tugma «shaxsiy chat» shartini o'zi ham kuchaytiradi. Lekin u
  `binding.py` dagi uchinchi darvozani ALMASHTIRMAYDI: guruhga `contact`
  boshqa yo'l bilan ham tushishi mumkin va darvoza kirish nuqtasiga emas,
  QABUL nuqtasiga qo'yiladi.

=============================================================================
⛔ MATN RO'YXATGA A'ZOLIK HAQIDA HECH NIMA AYTMAYDI (D-26a).

«Raqamingizni ulashing» — «bozor reyestrida bo'lsangiz raqamingizni
ulashing» EMAS. Ikkinchi shakl botni reyestrni TASHQARIDAN tekshirish
vositasiga aylantirardi. Taqiq `.po` matni ustida o'lchanadi
(`tests/unit/test_locale_parity.py`).

=============================================================================
⛔ QO'LDA TERILGAN RAQAM SO'RALMAYDI VA TAKLIF QILINMAYDI (D-24).

Bu modulda «raqamingizni yozing» ma'nosidagi matn ham, uni o'qiydigan
handler ham YO'Q. Yo'qlik `tests/unit/test_binding.py::
test_typed_phone_number_is_not_handled` da BUTUN dispatcher bo'yicha
o'lchanadi.
=============================================================================
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.i18n import gettext as _

from app.core_client import CoreApiError, NotBoundError

if TYPE_CHECKING:
    from aiogram.types import Message

    from app.core_client import CoreClient

router = Router(name="start")


def share_contact_keyboard() -> ReplyKeyboardMarkup:
    """⛔ YAGONA raqam berish yo'li — `request_contact=True` tugmasi (D-24).

    ⚠ `one_time_keyboard=True`: bog'lanish BIR MARTALIK amal va tugma
      ekranda qolib ketsa sotuvchi uni har kuni ko'rardi.
    """
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=_("bot.shareContact"), request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def main_menu_keyboard(*, with_more: bool = False) -> ReplyKeyboardMarkup:
    """Asosiy menyu — ikki tugma; uchinchisi FAQAT sahifa qolganda.

    Args:
        with_more: «Ko'proq» tugmasi ko'rsatilsinmi. ⛔ U DOIMIY EMAS:
            keyingi sahifa yo'q bo'lganda tugmani qoldirish bo'sh
            javob beradigan amalni taklif qilardi.
    """
    rows = [
        [
            KeyboardButton(text=_("bot.menu.debt")),
            KeyboardButton(text=_("bot.menu.payments")),
        ]
    ]
    if with_more:
        rows.append([KeyboardButton(text=_("bot.menu.more"))])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


@router.message(CommandStart())
async def on_start(message: Message, core: CoreClient) -> None:
    """Bog'langan foydalanuvchiga menyu, qolganiga kontakt tugmasi.

    ⚠ HOLAT SERVERDAN SO'RALADI, botda SAQLANMAYDI. Lokal bayroq
      («bu foydalanuvchi bog'langan») bog'lanish bekor qilinganda
      (D-26c) jimgina eskirardi va sotuvchi menyuni ko'rib turib har
      bosishda xato olardi.

    ⛔ NOSOZLIKDA KONTAKT TUGMASI KO'RSATILMAYDI: u «siz bog'lanmagansiz»
       degan YOLG'ON xulosa bo'lardi. Nosozlik nosozlik bo'lib qoladi.
    """
    if message.from_user is None:
        return
    try:
        await core.vendor_summary(telegram_user_id=message.from_user.id)
    except NotBoundError:
        await message.answer(_("bot.start.greeting"), reply_markup=share_contact_keyboard())
        return
    except CoreApiError:
        await message.answer(_("bot.error.retry"))
        return
    await message.answer(_("bot.start.bound"), reply_markup=main_menu_keyboard())


@router.message(Command("help"))
async def on_help(message: Message) -> None:
    """Atamalar izohi — sotuvchi uchun yagona lug'at yuzasi (D-30).

    ⚠ Matn veb bilan BIR XIL atamalarni ishlatadi va bu G7-9 ning (b)
      bandida o'lchanadi: glossariydagi har atama bot katalogining
      `msgstr` qiymatlarida kamida bir marta uchrashi shart.
    """
    await message.answer(_("bot.help.terms"))
