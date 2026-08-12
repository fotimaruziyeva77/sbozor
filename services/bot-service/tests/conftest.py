"""Test to'plamining YAGONA tayyorgarligi — gettext kataloglarini kompilyatsiya.

=============================================================================
⛔⛔ NEGA BU FAYL UMUMAN KERAK — VA NEGA U `conftest.py` DA.

`aiogram.utils.i18n.I18n.find_locales()` `.po` topib `.mo` topmasa
`RuntimeError` ko'taradi (o'lchandi: `aiogram/utils/i18n/core.py:78` —
«Found locale 'ru' but this language is not compiled!»). Ya'ni katalog
kompilyatsiya qilinmagan bo'lsa handlerlarni import qiladigan HAR BIR
test yig'ilishda yiqiladi.

`Dockerfile` kompilyatsiyani image ichida bajaradi, LEKIN `bot-tests`
repo ildizini `/app` USTIGA mount qiladi (`compose.yaml`): mount
image'dagi katalogni butunlay YASHIRADI va u yerdagi `.mo` fayllari
KO'RINMAY QOLADI. Ya'ni image bosqichi ishlab chiqarish uchun, bu fayl
esa test uchun — ikkalasi ham kerak va ikkalasi ham Babel ning AYNI
funksiyalarini chaqiradi.

`conftest.py` tanlandi, chunki pytest uni test MODULLARINI import
qilishdan OLDIN yuklaydi. Fixture kech bo'lardi: import yig'ish
paytida sodir bo'ladi.

=============================================================================
⛔ HAR YUGURISHDA QAYTA KOMPILYATSIYA — VA BU «ORTIQCHA ISH» EMAS.

`.mo` ni commitga qo'yish `.po` dan JIMGINA eskirish yo'lini ochardi:
matn o'zgargan, darvoza esa eski baytni o'lchagan bo'lardi. Shartsiz
qayta kompilyatsiya bu holatni STRUKTURAVIY ravishda imkonsiz qiladi va
u millisekundlar oladi (uchta kichik katalog). `.mo` `.gitignore` da.
=============================================================================
"""

from __future__ import annotations

from app.i18n import compile_catalogues

compile_catalogues()
"""⛔ MODUL DARAJASIDA — fixture EMAS (yuqoridagi sabab)."""
