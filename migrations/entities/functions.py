"""Login bootstrap uchun `SECURITY DEFINER` funksiyalari (RESEARCH Pattern 2).

=============================================================================
NEGA BU FUNKSIYALAR BOR (Pitfall 3 — empirik tasdiqlangan):

Login paytida `app.market_id` HALI NOMA'LUM — u aynan login natijasida
aniqlanadi. Agar identifikatsiya ma'lumoti tenant-policy ostida yotsa,
`sbozor_app` uni hech qachon ko'ra olmaydi:

    SET ROLE sbozor_app;
    SELECT count(*) FROM user_market_roles;   ->  0

ya'ni HECH KIM HECH QACHON kira olmaydi. Yechim ikki qismli:

  1. `users` GLOBAL jadval bo'ladi (`market_id` yo'q, RLS yo'q), lekin
     `sbozor_app` ga `REVOKE ALL` qilinadi — ORM orqali oddiy `select()`
     bilan unga borish IMKONSIZ.
  2. Global o'qish yuzasi AYNAN shu to'rt funksiya bilan cheklanadi:
     ular `SECURITY DEFINER` (ega huquqi bilan ishlaydi), `STABLE`
     (yozmaydi) va `PUBLIC` dan `REVOKE ALL` qilingan.

`BYPASSRLS` roli YARATILMAYDI (D-06): platforma admini boshqa bozorni
tanlaganda ham oddiy tenant policy'siga bo'ysunadi, chunki uning ilova
ulanishi baribir `sbozor_app`.
=============================================================================

HAR BIR FUNKSIYADA `SET search_path = pg_catalog, public` MAJBURIY va u
ATAYIN to'rt marta LITERAL yozilgan (umumiy konstantaga chiqarilmagan):
xavfsizlik uchun kritik satr har bir funksiya ta'rifida o'z ko'zi bilan
ko'rinib turishi va `grep` bilan topilishi kerak — 01-03 dagi
`algorithms=["HS256"]` bilan bir xil qoida. Nusxalar orasidagi drift
fail-closed emas, shuning uchun uni pastdagi meta-test qulflaydi.
`SECURITY DEFINER` funksiya chaqiruvchining `search_path` i bilan ishlasa,
chaqiruvchi o'z sxemasida soxta `users` jadvali yaratib funksiyani o'sha
jadvalga qaratishi mumkin — klassik privilege-escalation vektori.
`tests/tenancy/test_meta.py::test_security_definer_functions_pin_search_path`
buni butun baza bo'yicha, kelajakdagi funksiyalar uchun ham tekshiradi.

Funksiya tanasidagi har bir ustun havolasi jadval ALIASI bilan yoziladi
(`u.locale`, `r.market_id`): `RETURNS TABLE (...)` chiqish nomlari SQL
tanasida ko'rinadigan nomlar bo'lib, aliassiz `column reference ... is
ambiguous` xatosini beradi.
"""

from __future__ import annotations

from alembic_utils.pg_function import PGFunction

__all__ = [
    "ALL_FUNCTIONS",
    "AUTH_FIND_LOGIN",
    "AUTH_LIST_MARKETS",
    "AUTH_MEMBERSHIPS",
    "AUTH_USER_STATE",
    "GRANT_SIGNATURES",
]

AUTH_FIND_LOGIN = PGFunction(
    schema="public",
    signature="auth_find_login(p_phone text)",
    definition="""
RETURNS TABLE (
    user_id uuid,
    password_hash text,
    is_active boolean,
    must_change_password boolean,
    locale text,
    is_platform_admin boolean,
    full_name text
)
LANGUAGE sql
SECURITY DEFINER
SET search_path = pg_catalog, public
STABLE
AS $$
    SELECT u.id,
           u.password_hash,
           u.is_active,
           u.must_change_password,
           u.locale,
           u.is_platform_admin,
           u.full_name
    FROM public.users AS u
    WHERE u.phone_e164 = p_phone
$$
""",
)
"""Telefon bo'yicha login qatorini beradi — tenant kontekstisiz.

Mavjud bo'lmagan telefon uchun 0 qator qaytaradi, XATO EMAS: chaqiruvchi
`dummy_verify()` bilan bir xil vaqt sarflab javob beradi (T-01-15), ya'ni
"bu telefon ro'yxatdan o'tganmi" savoli javobsiz qoladi.
"""

AUTH_MEMBERSHIPS = PGFunction(
    schema="public",
    signature="auth_memberships(p_user_id uuid)",
    definition="""
RETURNS TABLE (
    market_id uuid,
    market_name text,
    roles text[]
)
LANGUAGE sql
SECURITY DEFINER
SET search_path = pg_catalog, public
STABLE
AS $$
    SELECT r.market_id,
           m.name,
           r.roles
    FROM public.user_market_roles AS r
    JOIN public.markets AS m ON m.id = r.market_id
    WHERE r.user_id = p_user_id
    ORDER BY m.name
$$
""",
)
"""Foydalanuvchining barcha a'zoliklari — bozor tanlash ekranining manbai (D-05)."""

AUTH_LIST_MARKETS = PGFunction(
    schema="public",
    signature="auth_list_markets()",
    definition="""
RETURNS TABLE (
    market_id uuid,
    market_name text,
    is_active boolean
)
LANGUAGE sql
SECURITY DEFINER
SET search_path = pg_catalog, public
STABLE
AS $$
    SELECT m.id,
           m.name,
           m.is_active
    FROM public.markets AS m
    ORDER BY m.name
$$
""",
)
"""Barcha bozorlar ro'yxati — FAQAT platforma admini oqimida chaqiriladi (D-06).

Huquq tekshiruvi ATAYIN ilova qatlamida: bu funksiya faqat bozor NOMLARI
ro'yxatini ochadi (hech qanday tenant ma'lumoti emas), shuning uchun u
`BYPASSRLS` rolining o'rnini bosadi va bosqichma-bosqich kengaymaydi.
Admin bozorni tanlagach oddiy `app.market_id` konteksti o'rnatiladi va u
ham hamma qatori bilan tenant policy'siga bo'ysunadi — bypass yo'li yo'q.
"""

AUTH_USER_STATE = PGFunction(
    schema="public",
    signature="auth_user_state(p_user_id uuid)",
    definition="""
RETURNS TABLE (
    is_active boolean,
    must_change_password boolean,
    locale text
)
LANGUAGE sql
SECURITY DEFINER
SET search_path = pg_catalog, public
STABLE
AS $$
    SELECT u.is_active,
           u.must_change_password,
           u.locale
    FROM public.users AS u
    WHERE u.id = p_user_id
$$
""",
)
"""Darhol bloklash keshi promahi uchun (D-08).

Valkey'dagi `user:state:{id}` yozuvi bo'lmasa, bu funksiya DB'dan javob
beradi — ya'ni kesh o'chganda tizim fail-open bo'lmaydi.
"""

ALL_FUNCTIONS: list[PGFunction] = [
    AUTH_FIND_LOGIN,
    AUTH_MEMBERSHIPS,
    AUTH_LIST_MARKETS,
    AUTH_USER_STATE,
]

GRANT_SIGNATURES: tuple[str, ...] = (
    "auth_find_login(text)",
    "auth_memberships(uuid)",
    "auth_list_markets()",
    "auth_user_state(uuid)",
)
"""`REVOKE`/`GRANT` uchun imzolar (argument TIPLARI bilan — Postgres shakli).

`ALL_FUNCTIONS` dagi tartib bilan bir xil; ikkalasining mosligi
`tests/tenancy/test_login_bootstrap.py` da tekshiriladi, chunki bu ro'yxat
unutilsa funksiya yaratiladi-yu, `sbozor_app` uni chaqira olmaydi.
"""
