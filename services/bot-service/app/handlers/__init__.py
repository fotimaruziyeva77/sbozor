"""Handler routerlarining yagona yig'ish nuqtasi.

⚠ TARTIB AHAMIYATLI VA U SHU YERDA, BITTA JOYDA YOZILGAN:

  1. `start`   — `CommandStart()` / `Command("help")`, ya'ni buyruqlar;
  2. `binding` — `F.contact`, ya'ni kontakt obyekti bo'lgan xabarlar;
  3. `vendor`  — `F.text.in_(...)`, ya'ni menyu tugmalarining MATNI.

Uchala filtr ham o'zaro kesishmaydi (buyruq — matn, lekin menyu
tugmalarining matni buyruq emas), ya'ni tartib xulqni O'ZGARTIRMAYDI.
Shunga qaramay u determinlashgan holda yozilgan: kesishuv bir kun paydo
bo'lsa, u AYNAN shu ro'yxatda ko'rinadi va tasodifiy import tartibiga
bog'liq bo'lib qolmaydi.
"""

from __future__ import annotations

from aiogram import Router

from app.handlers import binding, start, vendor


def build_router() -> Router:
    """Barcha handler routerlarini bitta routerga yig'adi.

    ⚠ FUNKSIYA, MODUL DARAJASIDAGI OBYEKT EMAS: `Router` ni ikki marta
      `include_router` qilish aiogram'da `RuntimeError` beradi, ya'ni
      modul darajasidagi yagona nusxa testda ikkinchi dispatcher qurish
      yo'lini yopardi.
    """
    router = Router(name="bot")
    router.include_router(start.router)
    router.include_router(binding.router)
    router.include_router(vendor.router)
    return router
