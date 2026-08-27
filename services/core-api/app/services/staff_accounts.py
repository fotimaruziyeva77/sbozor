"""Xodim hisobining ikkita domen qoidasi — ROL DARAJASI va VAQTINCHALIK PAROL.

=============================================================================
NEGA ALOHIDA MODUL VA NEGA U `app/services/` DA.

D-04 rol berish darajasi 01-07 da `app/api/v1/users.py` ichida tug'ilgan
va o'sha paytda u bitta endpointning qoidasi edi. 02-24 unga IKKINCHI
chaqiruvchi qo'shadi (`POST /imports/staff`), ya'ni qoida endi ikki
marshrut orasida bo'linadi. Ikkinchi NUSXA yozish eng qulay, lekin eng
xavfli yo'l bo'lardi: bir kun kimdir `users.py` dagi to'plamga rol
qo'shib, import yo'lini unutardi — va D-04 ning butun ma'nosi jimgina
yo'qolardi.

Shuning uchun to'plam SHU YERDA yashaydi va ikkala chaqiruvchi ham uni
SHU YERDAN oladi. `app/services/` tanlandi, chunki bu modul DB ga ham,
HTTP ga ham tegmaydi — u sof domen qoidasi (`import_validator` bilan
aynan bir xil qatlam).

⚠ Bu modul RAD ETMAYDI. U faqat "kim nimani bera oladi" degan savolga
javob beradi; javobni 403 ga (`users.py::_assert_roles_assignable`) yoki
qator xatosiga (`import_validator.validate_staff_rows`) aylantirish —
chaqiruvchining ishi va u ikkalasida ATAYIN har xil.
=============================================================================

`platform_admin` HAR IKKALA NATIJADA HAM YO'Q (CR-03).

Sabab `users.py::_assert_roles_assignable` dan ko'chiriladi: bu rol
`users.is_platform_admin` BAYROG'I orqali beriladi, a'zolik qatori
orqali EMAS. Ikkalasi mos kelmagan "gibrid" hisob (`roles=
["platform_admin"]` + `is_platform_admin=false`) sessiyada
`MARKET_VIEW_ALL` huquqini olardi (`auth.py::_session_roles` a'zolik va
bayroqni BIRLASHTIRADI), ya'ni bitta bozorga tegishli hisob platformadagi
BARCHA bozorlar ro'yxatini ocha olardi (T-01-81, T-01-82).

Rad etish PLATFORMA ADMINI uchun ham amal qiladi: haqiqiy platforma
admini bayroq bilan tayinlanadi va bu rolni a'zolik sifatida berishning
HECH QANDAY qonuniy holati yo'q.
"""

from __future__ import annotations

import secrets

from sbozor_core.enums import Role

__all__ = [
    "MARKET_ADMIN_ASSIGNABLE_ROLES",
    "PLATFORM_ADMIN_ASSIGNABLE_ROLES",
    "TEMPORARY_PASSWORD_BYTES",
    "assignable_roles",
    "temporary_password",
]

MARKET_ADMIN_ASSIGNABLE_ROLES = frozenset({Role.CASHIER, Role.INSPECTOR})
"""Bozor admini bera oladigan rollar to'plami (D-04 ikkinchi bosqichi).

`frozenset` — ro'yxat ish paytida o'zgartirilishi mumkin bo'lmasligi kerak.
Bu to'plamga yangi rol qo'shish = D-04 ni o'zgartirish, ya'ni u kod
review'dan va `tests/integration/test_users_api.py` dagi uchta rad etish
testidan o'tishi shart.

⚠ Bozor admini o'ziga TENG (`market_admin`) yoki undan YUQORI
(`director`) rol berolmaydi: aks holda u bir so'rov bilan o'zining
nazoratchisini yoki cheksiz sonli teng huquqli adminni tug'dira olardi
(T-01-50, ASVS V8).
"""

PLATFORM_ADMIN_ASSIGNABLE_ROLES = frozenset(
    {Role.MARKET_ADMIN, Role.DIRECTOR, Role.CASHIER, Role.INSPECTOR}
)
"""Platforma admini bera oladigan rollar (D-04 birinchi bosqichi).

`Role` enum'idan `platform_admin` ni CHIQARIB tashlagan holat — ya'ni
"hamma rol" degani EMAS. Yangi rol qo'shilganda bu to'plam AVTOMATIK
kengaymaydi va bu ATAYIN: yangi rolni kim bera olishi alohida qaror.
"""

TEMPORARY_PASSWORD_BYTES = 9
"""Tasodifiy baytlar soni: 9 bayt -> 12 belgili URL-xavfsiz satr.

`MIN_PASSWORD_LENGTH` (10) dan uzun, ya'ni yaratilgan foydalanuvchi bu
parol bilan login qila oladi va uni birinchi kirishda almashtiradi.
Qisqaroq qiymat "vaqtinchalik parol siyosatdan o'tmaydi" degan jimgina
tuzoqni yaratardi.
"""


def assignable_roles(is_platform_admin: bool) -> frozenset[Role]:
    """Chaqiruvchi bera oladigan rollar to'plami (D-04).

    Argument `Principal` EMAS, oddiy bayroq: modul HTTP qatlamiga
    bog'lanmasligi kerak, aks holda uni validator (sof funksiya) ichidan
    chaqirib bo'lmasdi.
    """
    if is_platform_admin:
        return PLATFORM_ADMIN_ASSIGNABLE_ROLES
    return MARKET_ADMIN_ASSIGNABLE_ROLES


def temporary_password() -> str:
    """Bir martalik vaqtinchalik parol (D-02).

    Qaytgan qiymat javobda BIR MARTA ochiq ketadi va boshqa HECH QAYERDA
    saqlanmaydi: bazada faqat Argon2id hash, log'da esa `censor_secrets`
    `temporary_password` kalitini maskalaydi.
    """
    return secrets.token_urlsafe(TEMPORARY_PASSWORD_BYTES)
