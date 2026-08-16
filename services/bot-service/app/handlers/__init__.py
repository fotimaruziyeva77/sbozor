"""Handler routerlarining yagona yig'ish nuqtasi.

⚠ TARTIB AHAMIYATLI VA U SHU YERDA, BITTA JOYDA YOZILGAN:

  1. `start`    — `CommandStart()` / `Command("help")`, ya'ni buyruqlar;
  2. `binding`  — `F.contact`, ya'ni kontakt obyekti bo'lgan xabarlar;
  3. `vendor`   — `F.text.in_(...)`, ya'ni menyu tugmalarining MATNI;
  4. `fallback` — ⛔ FILTRSIZ, ya'ni QOLGAN HAMMASI.

Birinchi uchtasining filtrlari o'zaro kesishmaydi (buyruq — matn, lekin
menyu tugmalarining matni buyruq emas), ya'ni ular orasidagi tartib
xulqni O'ZGARTIRMAYDI. Shunga qaramay u determinlashgan holda yozilgan:
kesishuv bir kun paydo bo'lsa, u AYNAN shu ro'yxatda ko'rinadi va
tasodifiy import tartibiga bog'liq bo'lib qolmaydi.

=============================================================================
⛔⛔ TO'RTINCHISI UCHUN ESA TARTIB XULQNING O'ZI — VA U MUZOKARA
   QILINMAYDI (WR-04).

`fallback` routerining filtri YO'Q, ya'ni u KELGAN HAR QANDAY xabarga
mos keladi. aiogram routerlarni RO'YXAT TARTIBIDA sinaydi va birinchi
mos kelgani update'ni ISTE'MOL QILADI. Demak `fallback` ro'yxatning
oxirida BO'LMASA, u `CommandStart()` ni ham, `F.contact` ni ham, uchala
tugma matnini ham USHLAB QOLARDI: bog'lanish, qarz va to'lov tarixi —
uchalasi ham jimgina o'lardi.

⚠ NOSOZLIK SHAKLI ENG YOMON SINFDAN BO'LARDI: bot javob berib turardi
  (zaxira matni bilan), ya'ni «bot tirik» ko'rinardi va HECH QANDAY
  xato chiqmasdi. Aynan shuning uchun tartib
  `tests/unit/test_vendor_handlers.py::test_the_fallback_router_is_the_last_one`
  da MEXANIK o'lchanadi, va o'sha faylda `/start` hamda `F.contact`
  ning o'z handlerlariga yetib borishi ham alohida tekshiriladi.
=============================================================================
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from aiogram import Router
from aiogram.utils.i18n import gettext as _

from app.handlers import binding, start, vendor
from app.handlers.start import main_menu_keyboard

if TYPE_CHECKING:
    from aiogram.types import Message

fallback_router = Router(name="fallback")
"""⛔ FILTRSIZ ROUTER — `build_router()` da ENG OXIRIDA ulanadi."""


@fallback_router.message()
async def on_unknown(message: Message) -> None:
    """Filtrga tushmagan HAR qanday xabar — menyu QAYTA ko'rsatiladi.

    =========================================================================
    ⛔⛔ JAVOB FOYDALANUVCHI TERGAN MATNNI O'QIMAYDI VA TAKRORLAMAYDI.

    D-24 ning taqig'i QO'LDA TERILGAN RAQAMNI O'QISHGA tegishli: bot
    terilgan raqamni hech qachon shaxs da'vosi sifatida qabul qilmaydi,
    chunki uni Telegram TASDIQLAMAGAN. Bu yerdagi handler o'sha taqiqni
    BUZMAYDI — u xabarning MAZMUNIGA umuman qaramaydi: na tahlil qiladi,
    na aks-sado qiladi, na `core-api` ga uzatadi. U faqat MAVJUD
    tugmalarni eslatadi.

    ⛔ SHU SABABDAN BU YERDA `core` ARGUMENTI YO'Q: zaxira hech qanday
       so'rov qilmaydi. Aks holda botga matn yozib turgan begona odam
       HAQIQIY sotuvchining rate-limit sanagichini yeb qo'ya olardi.

    =========================================================================
    ⚠ NEGA UMUMAN JAVOB BERILADI — SABAB `app/main.py` NING O'ZIDA:

        «Botning butun qiymati "sotuvchi yozgan xabar javob oladi"
         degani»

    Bu handlergacha sotuvchining eng tabiiy harakati («qarzim qancha?»
    deb yozish) MUTLAQ SUKUNAT bilan tugardi — hech qanday xato, hech
    qanday jurnal yozuvi, hech qanday belgi.
    """
    await message.answer(_("bot.unknown"), reply_markup=main_menu_keyboard())


def build_router() -> Router:
    """Barcha handler routerlarini bitta routerga yig'adi.

    ⚠ FUNKSIYA, MODUL DARAJASIDAGI OBYEKT EMAS: `Router` ni ikki marta
      `include_router` qilish aiogram'da `RuntimeError` beradi, ya'ni
      modul darajasidagi yagona nusxa testda ikkinchi dispatcher qurish
      yo'lini yopardi.

    ⚠⚠ SHUNGA QARAMAY BU FUNKSIYA IKKI MARTA CHAQIRILMAYDI: `include_router`
      BOLA routerga `parent_router` YOZADI, ya'ni ikkinchi chaqiruv
      «Router is already attached» bilan yiqiladi. Testlar shu sababdan
      `app.main.dp` ning bir marta qurilgan nusxasini o'qiydi.
    """
    router = Router(name="bot")
    router.include_router(start.router)
    router.include_router(binding.router)
    router.include_router(vendor.router)
    # ⛔ OXIRGI — VA BU QATOR YUQORIGA KO'CHIRILMAYDI (modul docstringi).
    router.include_router(fallback_router)
    return router
