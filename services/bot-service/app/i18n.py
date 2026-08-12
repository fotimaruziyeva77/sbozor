"""Bot matnlarining gettext katalogi — uchala locale MAJBURIY (D-30, D-31).

=============================================================================
⛔⛔ MSGID — SIMVOLIK KALIT, MANBA MATNI EMAS.

`_("bot.binding.neutral")` yoziladi, `_("Bog'lanib bo'lmadi...")` emas.
Sabab `07-UI-SPEC.md` §14.6 da: o'sha jadval matnlarni AYNAN shu kalitlar
bilan nomlaydi va veb tomondagi `messages/*.json` ham kalit bo'yicha
ishlaydi. Ikki manba bir xil nomlash sxemasida bo'lsa D-30 («atamalar
yagona») tekshiriladigan da'voga aylanadi.

⚠⚠ SIMVOLIK MSGID NING NARXI VA UNING DARVOZASI: bo'sh `msgstr` gettext'da
   MSGID NING O'ZINI qaytaradi, ya'ni sotuvchi ekranda «bot.binding.neutral»
   degan matnni ko'rardi va HECH NIMA QIZARMASDI. Aynan shuning uchun
   `tests/unit/test_locale_parity.py::test_no_msgstr_is_empty` MAJBURIY.

=============================================================================
⛔ TIL ANIQLASH TARTIBI — IKKI BOSQICH, UCHINCHISI YO'Q.

  1. foydalanuvchining Telegram `language_code` i;
  2. standart — `uz_Latn`.

`SimpleI18nMiddleware` aynan shuni qiladi: `Locale.parse(language_code)`
ning TIL qismi (`ru`) `available_locales` da bo'lsa u tanlanadi, aks holda
standart qaytadi.

⚠⚠ SHUNING OQIBATI OCHIQ YOZILADI: Telegram klienti «o'zbek kirillcha»
   degan til kodini BERMAYDI (u faqat `uz` ni beradi), ya'ni `uz_Cyrl`
   katalogi bugun `language_code` orqali TANLANMAYDI. Bu katalog o'lik
   emas: uning mazmuni G7-9 (`frontend/scripts/glossary.test.mjs`) va
   parity darvozasi bilan o'lchanadi, iste'molchisi esa til tanlagichi
   bo'ladi. ⛔ Katalogni «ishlatilmayapti» deb o'chirish D-31 ni buzardi.

=============================================================================
⚠⚠ KATALOGLAR KOMPILYATSIYA QILINGAN BO'LISHI SHART — VA BU FAIL-LOUD.

`aiogram.utils.i18n.I18n.find_locales()` `.po` topib `.mo` topmasa
`RuntimeError` ko'taradi (o'lchandi: `aiogram/utils/i18n/core.py`).
Ya'ni kompilyatsiyani unutish JIMGINA emas — servis KO'TARILMAYDI.

Kompilyatsiya ikki joyda va ikkalasi ham ⛔ `pybabel` (Babel) bilan,
⛔ `msgfmt` BILAN EMAS (`07-RESEARCH.md` § Environment Availability:
tashqi gettext binarining mavjudligi tekshirilmagan, Babel esa
`aiogram[i18n]` orqali ALLAQACHON bog'liqlik):

  * `services/bot-service/Dockerfile` — `pybabel compile` (image ichida);
  * `services/bot-service/tests/conftest.py` — Babel ning O'SHA
    funksiyalari bilan (`read_po` + `write_mo`), chunki `bot-tests`
    repo ildizini `/app` ustiga MOUNT qiladi va image'da qurilgan `.mo`
    fayllari mount ostida KO'RINMAY QOLADI.

⛔ `.mo` — build artefakti va u commitga tushmaydi (`.gitignore`).
   Commit qilingan `.mo` `.po` dan JIMGINA eskirardi va darvoza eski
   matnni o'lchardi.
=============================================================================
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Final

from aiogram.utils.i18n import I18n

DOMAIN: Final = "bot"
"""Katalog domeni — `locales/<loc>/LC_MESSAGES/bot.po`."""

LOCALES_PATH: Final = Path(__file__).resolve().parent / "locales"

DEFAULT_LOCALE: Final = "uz_Latn"
"""⛔ Standart — o'zbek LOTIN. Karmana pilotining tili; `ru` ATAYIN
standart emas, aks holda til kodi noma'lum foydalanuvchi rus matnini
ko'rardi."""

SUPPORTED_LOCALES: Final = ("uz_Latn", "uz_Cyrl", "ru")
"""⛔ UCHALASI HAM MAJBURIY (D-31) va tartib DETERMINLASHGAN.

⚠ Bu kortej `frontend/messages/*.json` ning uch tili bilan JUFT: nomlar
  ataylab boshqacha (`uz_Latn` ↔ `uz-Latn`), chunki gettext katalog
  KATALOGI POSIX ajratgichini talab qiladi, `next-intl` esa BCP-47 ni.
  Xarita `frontend/scripts/glossary.test.mjs` da yozilgan va TO'LIQLIGI
  o'sha yerda o'lchanadi — aks holda bir tomonga qo'shilgan til
  ikkinchisida jimgina yo'q bo'lardi.
"""


def compile_catalogues() -> tuple[str, ...]:
    """Uchala katalogni `.po` -> `.mo` ga aylantiradi; nomlarni qaytaradi.

    ⚠⚠ ⛔ `msgfmt` UMUMAN ISHLATILMAYDI (07-RESEARCH § Environment
      Availability: tashqi gettext binarining mavjudligi TEKSHIRILMAGAN).
      Bu yerda `pybabel compile` ning O'ZI chaqiradigan ikki funksiya
      ishlatiladi — natija AYNI, lekin subprocess, `PATH` va chiqish
      kodini tekshirish qatlamlari yo'q.

    ⚠ Import BUZILMASIN uchun `babel` MAHALLIY import qilinadi: u
      `aiogram[i18n]` ning tranzitiv bog'liqligi va ishlab chiqarish
      yo'lida (image ichida allaqachon kompilyatsiya qilingan) bu
      funksiya UMUMAN chaqirilmaydi.

    Returns:
        Kompilyatsiya qilingan locale nomlari.

    Raises:
        FileNotFoundError: `.po` yo'q. ⛔ ATAYIN QO'POL — jimgina
            o'tkazib yuborish D-31 ni («uchala locale majburiy») bo'sh
            da'voga aylantirardi.
    """
    from babel.messages.mofile import write_mo
    from babel.messages.pofile import read_po

    compiled: list[str] = []
    for locale in SUPPORTED_LOCALES:
        po_path = LOCALES_PATH / locale / "LC_MESSAGES" / f"{DOMAIN}.po"
        if not po_path.exists():
            msg = f"katalog yo'q: {po_path}"
            raise FileNotFoundError(msg)
        with po_path.open("rb") as source:
            # ⚠ `locale=None` ATAYIN: ko'plik shakllari `.po` ning O'Z
            #   `Plural-Forms` sarlavhasidan olinadi, CLDR dan emas.
            #   Aks holda sarlavhadagi noto'g'ri e'lon JIMGINA to'g'ri
            #   CLDR qoidasi bilan almashardi va
            #   `test_russian_catalog_declares_three_plural_forms`
            #   hech nimani himoya qilmasdi.
            catalog = read_po(source, locale=None, domain=DOMAIN)
        with po_path.with_suffix(".mo").open("wb") as target:
            write_mo(target, catalog)
        compiled.append(locale)
    return tuple(compiled)


@lru_cache(maxsize=1)
def get_i18n() -> I18n:
    """Yagona `I18n` instansi (`get_settings()` naqshi).

    ⚠⚠ DANGASA, LEKIN JIM EMAS. Konstruktor kataloglarni O'QIYDI va
      kompilyatsiya qilinmagan `.po` da `RuntimeError` beradi —
      ishlab chiqarishda bu `app.main` IMPORT paytida, ya'ni eng erta
      nuqtada chiqadi (`SimpleI18nMiddleware(get_i18n())` modul
      darajasida).

    ⛔ MODUL DARAJASIDAGI OBYEKT ATAYIN QURILMAYDI: u
      `tests/conftest.py` ni ILOJSIZ qilardi. Conftest kompilyatsiyani
      bajaradi, lekin buning uchun shu moduldan `compile_catalogues()`
      ni import qilishi kerak — modul darajasidagi `I18n` esa o'sha
      import paytida, ya'ni KOMPILYATSIYADAN OLDIN yiqilardi.
    """
    return I18n(path=LOCALES_PATH, default_locale=DEFAULT_LOCALE, domain=DOMAIN)
