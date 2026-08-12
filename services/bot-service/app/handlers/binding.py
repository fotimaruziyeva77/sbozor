"""BOT-01 — sotuvchi o'zini tanitadi (D-24, D-26, Pitfall 8).

=============================================================================
⛔⛔ D-24 NING BUTUN MAZMUNI BITTA JUMLADA.

Terilgan raqam — foydalanuvchining DA'VOSI; `contact` esa Telegram O'ZI
KAFOLATLAGAN yagona narsa. Terilgan raqamni qabul qilish begona
sotuvchining qarzini ko'rish yo'lini OCHARDI: sotuvchining raqami maxfiy
emas (u bozorda hammaga ma'lum), ya'ni «raqamni bilish» hech qanday
autentifikatsiya bermaydi.

=============================================================================
⛔⛔ QO'LDA TERILGAN RAQAMNI O'QIYDIGAN HANDLER BU MODULDA YO'Q — VA BU
   YO'QLIK STRUKTURA, KELISHUV EMAS.

Bu yerda `F.text` bo'yicha telefon o'qiydigan handler UMUMAN yozilmagan.
Yo'qlik `tests/unit/test_binding.py::test_typed_phone_number_is_not_
handled` da BUTUN dispatcher bo'yicha o'lchanadi: `F.contact` filtrisiz
birorta handler manbasida «phone» so'zi uchramasligi shart.

⛔ «Foydalanuvchi tugmani topa olmasa raqamni yozsin» degan qulaylik
   qo'shish TAQIQ: u aynan yuqoridagi yo'lni qaytarardi.

=============================================================================
⛔⛔ UCH DARVOZA — VA UCHALASI HAM MAJBURIY (Pitfall 8).

Telegram `Contact` obyektida `user_id` — IXTIYORIY maydon
[core.telegram.org/bots/api#contact]. Ya'ni:

  1. `contact.user_id is None` -> vCard yoki qo'lda qo'shilgan kontakt;
     Telegram uni HECH KIM bilan bog'lamagan va raqam hech kimniki
     ekani tasdiqlanmagan;
  2. `contact.user_id != message.from_user.id` -> foydalanuvchi BOSHQA
     odamning kontaktini ulashdi. Telegram klientida bu ODDIY AMAL
     (skrepka -> «Kontakt» -> istalgan odam) va bu D-24 aynan yopmoqchi
     bo'lgan yo'l;
  3. `message.chat.type != private` -> guruhdan yuborilgan; guruhda
     kimning nomidan yuborilgani va kim o'qishi nazorat qilinmaydi.

Faqat `request_contact=True` tugmasi SHAXSIY chatda bosilganda `user_id`
sender bilan TENG bo'ladi — aynan o'shanda raqam Telegram tomonidan
KAFOLATLANADI.

=============================================================================
⛔⛔ D-26(a): «MOS KELMADI» VA «BIR NECHTA MOSLIK» AYNAN BIR XIL MATN.

«Bu raqam ro'yxatda yo'q» degan javob botni reyestrni TASHQARIDAN
tekshirish vositasiga aylantirardi: begona odam raqamlarni ketma-ket
sinab, kim sotuvchi ekanini aniqlay olardi.

⛔ TENGLIK TESTGA EMAS, STRUKTURAGA TAYANADI: bu modulda faqat BITTA
   nomlangan holat bor (`BOUND_STATUS`) va qolgan hamma narsa bitta
   `else` shoxiga tushadi. Ya'ni ikkinchi matnni yozish uchun avval
   ikkinchi shoxni tug'dirish kerak bo'ladi.

=============================================================================
⛔⛔ DIREKTOR SHOXI D-26(a) NING NEYTRALLIGINI BUZMAYDI (07-18).

Kontakt sotuvchi reyestriga mos kelmasa, handler IKKINCHI so'rov yuboradi
va «bu odam biror bozorning direktormi?» deb so'raydi. Uch fakt bu
shoxni neytral qoldiradi:

  1. IKKALA RAD ETISH HAM AYNI MATN: sotuvchi ham, direktor ham
     topilmasa `NEUTRAL_KEY` chiziladi — ya'ni «raqamingiz qaysi
     reyestrda yo'q?» degan savolga bot javob BERMAYDI;
  2. FARQ FAQAT MUVAFFAQIYAT SHOXIDA KO'RINADI, unga esa raqamning
     EGASI yetadi (D-24 ning uch qo'riqchisi shoxdan OLDIN ishlaydi va
     ular O'ZGARMAGAN) — begona odam boshqa birovning rolini
     bilib ololmaydi;
  3. IKKI SO'ROV BITTA RATE-LIMIT SANAGICHINI yeydi (`core-api`
     `/director/resolve` docstringidagi arifmetika), ya'ni ikkinchi
     shox urinishlar byudjetini kengaytirmaydi.
=============================================================================
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from aiogram import F, Router
from aiogram.enums import ChatType
from aiogram.utils.i18n import gettext as _

from app.core_client import BOUND_STATUS, CoreApiError
from app.handlers.start import main_menu_keyboard

if TYPE_CHECKING:
    from aiogram.types import Message

    from app.core_client import CoreClient

router = Router(name="binding")

NEUTRAL_KEY = "bot.binding.neutral"
"""⛔ UCHALA RAD ETISH SHOXINING YAGONA MATNI (D-26a).

Konstanta ATAYIN bitta: uchta joyda uchta literal yozilsa, kimdir
bittasini «aniqroq qilish» uchun tahrirlab, qolgan ikkitasini
unutardi — va o'sha farqning o'zi oracle bo'lardi.
"""


@router.message(F.contact)
async def on_contact(message: Message, core: CoreClient) -> None:
    """Kontaktni qabul qiladi — ⛔ uch darvozadan keyin (modul docstringi).

    ⚠ DARVOZALAR BITTA SHARTDA VA ULAR `or` BILAN BOG'LANGAN: har biri
      alohida `if` bo'lsa, biriga qo'shilgan «lekin agar ...» istisnosi
      qolgan ikkitasini chetlab o'tish yo'lini ochardi. Bitta shart —
      bitta chiqish nuqtasi.

    ⛔ RAD ETILGANDA `core.resolve` UMUMAN CHAQIRILMAYDI. Bu shunchaki
       tejamkorlik emas: chaqiruv `core-api` da rate-limit sanagichini
       oshirardi va begona kontakt bilan yuborilgan oqim HAQIQIY
       sotuvchini o'z akkauntidan bloklab qo'ya olardi.
    """
    contact = message.contact
    if (
        message.chat.type != ChatType.PRIVATE
        or contact is None
        or contact.user_id is None
        or message.from_user is None
        or contact.user_id != message.from_user.id
    ):
        await message.answer(_(NEUTRAL_KEY))
        return

    try:
        outcome = await core.resolve(
            telegram_user_id=contact.user_id,
            raw_phone=contact.phone_number,
        )
    except CoreApiError:
        # ⛔ ISTISNO NA MATNI, NA TURI FOYDALANUVCHIGA CHIQADI (D-04).
        #    Jurnal `core_client._failure()` da allaqachon yozilgan;
        #    bu yerda ikkinchi yozuv faqat shovqin qo'shardi.
        await message.answer(_("bot.error.retry"))
        return

    if outcome.status == BOUND_STATUS and outcome.vendor is not None:
        await message.answer(_("bot.binding.ok"), reply_markup=main_menu_keyboard())
        return

    try:
        director = await core.resolve_director(
            telegram_user_id=contact.user_id,
            raw_phone=contact.phone_number,
        )
    except CoreApiError:
        await message.answer(_("bot.error.retry"))
        return

    if director.status == BOUND_STATUS:
        # ⛔ ASOSIY MENYU KLAVIATURASI BERILMAYDI VA BU QAROR: uning ikkala
        #    tugmasi ham («Qarzim», «To'lovlarim») SOTUVCHINING savoli va
        #    ular direktor uchun `not_bound` javobini qaytarardi — ya'ni
        #    menyu ishlamaydigan tugmalar bilan chiqardi.
        #
        # ⚠ `ReplyKeyboardRemove()` ATAYIN YUBORILMAYDI: kontakt tugmasi
        #   `/start` da ONE-TIME klaviatura sifatida ko'rsatiladi va uni
        #   Telegram O'ZI yopadi. Ortiqcha olib tashlash so'rovi
        #   direktorning chatida ikkinchi xabar tug'dirardi.
        await message.answer(_("bot.binding.director"))
        return

    # ⛔ `no_match`, `multiple_matches` VA «direktor ham emas» — SHU BITTA
    #    SHOX. Farq faqat serverda yoziladi (07-08: ikkinchisi
    #    `alert_events` ga qator qo'yadi), foydalanuvchi esa reyestr
    #    nuqsonini ham, reyestr A'ZOLIGINI ham bilishi SHART EMAS.
    await message.answer(_(NEUTRAL_KEY))
