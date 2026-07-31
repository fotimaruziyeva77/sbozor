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

QAYTISH TIPINI O'ZGARTIRISH `CREATE OR REPLACE` BILAN IMKONSIZ: Postgres
mavjud funksiyaning `RETURNS TABLE (...)` ro'yxatini almashtirishga yo'l
bermaydi (`cannot change return type of existing function`). Bu yerdagi
ta'rifga ustun qo'shish "tekin" emas — u alohida migratsiya bandini talab
qiladi: `DROP FUNCTION` + qayta yaratish + `REVOKE`/`GRANT` ni QAYTADAN
qo'yish (`DROP` dan keyin Postgres yangi funksiyaga `EXECUTE TO PUBLIC` ni
standart beradi). Namuna — `migrations/versions/0006_membership_active.py`.
"""

from __future__ import annotations

from alembic_utils.pg_function import PGFunction

__all__ = [
    "ALL_FUNCTIONS",
    "AUTH_CREATE_USER",
    "AUTH_FIND_LOGIN",
    "AUTH_FIND_LOGIN_BY_ID",
    "AUTH_LIST_MARKETS",
    "AUTH_LIST_MARKETS_FULL",
    "AUTH_LIST_PLATFORM_AUDIT",
    "AUTH_LIST_USERS",
    "AUTH_MEMBERSHIPS",
    "AUTH_REFRESH_FIND",
    "AUTH_REFRESH_ISSUE",
    "AUTH_REFRESH_REVOKE_FAMILY",
    "AUTH_REFRESH_REVOKE_USER",
    "AUTH_REFRESH_ROTATE",
    "AUTH_SET_ACTIVE",
    "AUTH_SET_LOCALE",
    "AUTH_SUPPORT_FUNCTIONS",
    "AUTH_SUPPORT_GRANT_SIGNATURES",
    "AUTH_UPDATE_PASSWORD_HASH",
    "AUTH_USER_STATE",
    "GRANT_SIGNATURES",
    "PLATFORM_AUDIT_FUNCTIONS",
    "PLATFORM_AUDIT_GRANT_SIGNATURES",
    "USER_ADMIN_FUNCTIONS",
    "USER_ADMIN_GRANT_SIGNATURES",
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
    roles text[],
    is_active boolean
)
LANGUAGE sql
SECURITY DEFINER
SET search_path = pg_catalog, public
STABLE
AS $$
    SELECT r.market_id,
           m.name,
           r.roles,
           m.is_active
    FROM public.user_market_roles AS r
    JOIN public.markets AS m ON m.id = r.market_id
    WHERE r.user_id = p_user_id
    ORDER BY m.name
$$
""",
)
"""Foydalanuvchining barcha a'zoliklari — bozor tanlash ekranining manbai (D-05).

`is_active` — BOZOR faolligi (`markets.is_active`), foydalanuvchi faolligi
EMAS. U qoralama bozorni (usta tugallanmagan, `false`) bozor tanlash
ekranida ajratish uchun kerak: a'zolik tarmog'ida bozor avval ham
ko'rinardi, lekin javob shaklida bu maydon umuman yo'q edi va UI uni
jimgina "faol" deb yorliqlardi (UI-SPEC §12.1.1 X-2).

`m.is_active` jadval ALIASI bilan yozilgan: `RETURNS TABLE` chiqish nomi
ham `is_active` va aliassiz `column reference "is_active" is ambiguous`
xatosi chiqadi.

⚠ Bu ta'rif `0001` da yaratiladi, LEKIN qaytish tipi `0006` da o'zgardi.
Mavjud bazada `CREATE OR REPLACE` yetmaydi — `0006_membership_active.py`
`DROP` + qayta yaratish + `GRANT` tiklashni bajaradi.
"""

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
"""`0001_identity` migratsiyasi yaratadigan LOGIN BOOTSTRAP to'plami.

Keyingi migratsiyalarda qo'shilgan funksiyalar bu ro'yxatga TUSHMAYDI —
aks holda `0001` mavjud bo'lmagan obyektga `GRANT` berishga urinardi.
Ular `AUTH_SUPPORT_FUNCTIONS` da (pastda).
"""

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


# ===========================================================================
# 0003_auth_support — SESSIYA VA PAROL YOZISH YO'LI
# ===========================================================================
#
# NEGA `refresh_tokens` HAM `SECURITY DEFINER` ORTIDA (01-06 da aniqlangan):
#
# `refresh_tokens` tenant-scoped (RLS ENABLE + FORCE). Refresh cookie
# kelganda esa bozor HALI NOMA'LUM: `mid` claim'i refresh tokenga ATAYIN
# yozilmaydi (01-03 — huquqlar har `/refresh` da DB'dan qayta o'qiladi,
# aks holda bloklangan foydalanuvchi 30 kun eski huquqlari bilan yashardi).
# Ya'ni qatorni `jti` bo'yicha topish tenant kontekstisiz bajarilishi kerak,
# RLS esa uni 0 qatorga tushiradi -> `/refresh` HECH QACHON ishlamasdi.
#
# Bu Pitfall 3 ning AYNAN o'sha mexanizmi (login RLS ostida imkonsiz), faqat
# `users` emas, `refresh_tokens` ustida — shuning uchun yechim ham bir xil:
# tor, `search_path` pin qilingan, `PUBLIC` dan yopiq `SECURITY DEFINER`
# funksiyalar. Jadval sxemasi (`uq_refresh_tokens_jti` GLOBAL unique indeksi)
# 01-04 da aynan shu global qidiruvni ko'zlab qurilgan edi.
#
# YUZA QASDDAN TOR: har bir funksiya BITTA operatsiyani bajaradi va
# `jti` / `family_id` / `user_id` bo'yicha aniq filtrlanadi. Hech biri
# ixtiyoriy `WHERE` qabul qilmaydi, ya'ni ular "RLS'siz refresh_tokens
# ustida ishlash" imkonini bermaydi.

AUTH_FIND_LOGIN_BY_ID = PGFunction(
    schema="public",
    signature="auth_find_login_by_id(p_user_id uuid)",
    definition="""
RETURNS TABLE (
    user_id uuid,
    phone_e164 text,
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
           u.phone_e164,
           u.password_hash,
           u.is_active,
           u.must_change_password,
           u.locale,
           u.is_platform_admin,
           u.full_name
    FROM public.users AS u
    WHERE u.id = p_user_id
$$
""",
)
"""`user_id` bo'yicha login qatori — parol almashtirish oqimi uchun (D-02).

Access tokenda telefon YO'Q (u shaxsiy ma'lumot va tokenga kerak emas),
`change-password` esa joriy parol hash'ini talab qiladi. Telefon shu
funksiyadan olinadi va D-06 `actor_label` matnida ishlatiladi.
"""

AUTH_UPDATE_PASSWORD_HASH = PGFunction(
    schema="public",
    signature="auth_update_password_hash(p_user_id uuid, p_hash text, p_must_change boolean)",
    definition="""
RETURNS void
LANGUAGE sql
SECURITY DEFINER
SET search_path = pg_catalog, public
VOLATILE
AS $$
    UPDATE public.users
       SET password_hash = p_hash,
           must_change_password = COALESCE(p_must_change, must_change_password),
           updated_at = now()
     WHERE id = p_user_id
$$
""",
)
"""Parol hash'ini yangilaydi. `p_must_change IS NULL` -> bayroq TEGILMAYDI.

Ikki chaqiruvchisi bor va ular boshqacha xulq kutadi:
  * `change-password` -> `false` (D-02: majburiy almashtirish bajarildi);
  * login paytidagi `verify_and_update` (T-01-18: Argon2 parametrlari
    eskirgan) -> `NULL`, chunki bu foydalanuvchi uchun ko'rinmas texnik
    yangilanish va u majburiy almashtirish holatini o'zgartirmasligi kerak.

`DEFAULT` ATAYIN ISHLATILMAGAN: `alembic-utils` imzoni matn sifatida
solishtiradi va standart qiymatli argument autogenerate'da keraksiz
`replace_entity` chiqarishi mumkin.
"""

AUTH_SET_ACTIVE = PGFunction(
    schema="public",
    signature="auth_set_active(p_user_id uuid, p_is_active boolean)",
    definition="""
RETURNS void
LANGUAGE sql
SECURITY DEFINER
SET search_path = pg_catalog, public
VOLATILE
AS $$
    UPDATE public.users
       SET is_active = p_is_active,
           updated_at = now()
     WHERE id = p_user_id
$$
""",
)
"""Foydalanuvchini bloklaydi/tiklaydi (D-08).

Bloklash DARHOL kuchga kirishi uchun chaqiruvchi shu funksiyadan KEYIN
`app.deps.invalidate_user_state()` ni ishga tushiradi. Boshqaruv UI'si
01-07 rejasida; funksiya bu yerda yaratiladi, chunki uning yagona
alternativasi `users` ga to'g'ridan-to'g'ri GRANT berish bo'lardi va bu
Pattern 2 ni butunlay buzardi.
"""

AUTH_REFRESH_ISSUE = PGFunction(
    schema="public",
    signature=(
        "auth_refresh_issue(p_market_id uuid, p_user_id uuid, p_jti text, "
        "p_family_id uuid, p_expires_at timestamptz)"
    ),
    definition="""
RETURNS void
LANGUAGE sql
SECURITY DEFINER
SET search_path = pg_catalog, public
VOLATILE
AS $$
    INSERT INTO public.refresh_tokens (market_id, user_id, jti, family_id, expires_at)
    VALUES (p_market_id, p_user_id, p_jti, p_family_id, p_expires_at)
$$
""",
)
"""Yangi refresh token qatorini yozadi (login yoki bozor tanlashdan keyin)."""

AUTH_REFRESH_FIND = PGFunction(
    schema="public",
    signature="auth_refresh_find(p_jti text)",
    definition="""
RETURNS TABLE (
    market_id uuid,
    user_id uuid,
    family_id uuid,
    expires_at timestamptz,
    revoked_at timestamptz,
    replaced_by_jti text
)
LANGUAGE sql
SECURITY DEFINER
SET search_path = pg_catalog, public
STABLE
AS $$
    SELECT t.market_id,
           t.user_id,
           t.family_id,
           t.expires_at,
           t.revoked_at,
           t.replaced_by_jti
    FROM public.refresh_tokens AS t
    WHERE t.jti = p_jti
$$
""",
)
"""`jti` bo'yicha global qidiruv — cookie kelganda bozor noma'lum.

Topilmasa 0 qator (xato emas): chaqiruvchi buni `401 invalid_refresh` ga
aylantiradi. `revoked_at` to'ldirilgan qator ham QAYTARILADI — reuse
aniqlash aynan shu qatorga tayanadi (o'chirilgan qator hech nima aytmagan
bo'lardi).
"""

AUTH_REFRESH_ROTATE = PGFunction(
    schema="public",
    signature="auth_refresh_rotate(p_old_jti text, p_new_jti text)",
    definition="""
RETURNS integer
LANGUAGE sql
SECURITY DEFINER
SET search_path = pg_catalog, public
VOLATILE
AS $$
    WITH rotated AS (
        UPDATE public.refresh_tokens
           SET revoked_at = now(),
               replaced_by_jti = p_new_jti
         WHERE jti = p_old_jti
           AND revoked_at IS NULL
        RETURNING 1
    )
    SELECT count(*)::integer FROM rotated
$$
""",
)
"""Eski qatorni bekor qilib yangisiga bog'laydi; TEGILGAN QATORLAR SONI qaytadi.

`0` qaytishi — reuse signali. Tekshiruv `UPDATE ... WHERE revoked_at IS
NULL` ICHIDA bajariladi: avval `SELECT` qilib keyin `UPDATE` qilish ikki
parallel `/refresh` so'roviga bir xil tokenni rotatsiya qilish imkonini
berardi (poyga oynasi), bu yerda esa faqat BITTASI g'olib chiqadi.
"""

AUTH_REFRESH_REVOKE_FAMILY = PGFunction(
    schema="public",
    signature="auth_refresh_revoke_family(p_family_id uuid)",
    definition="""
RETURNS integer
LANGUAGE sql
SECURITY DEFINER
SET search_path = pg_catalog, public
VOLATILE
AS $$
    WITH revoked AS (
        UPDATE public.refresh_tokens
           SET revoked_at = now()
         WHERE family_id = p_family_id
           AND revoked_at IS NULL
        RETURNING 1
    )
    SELECT count(*)::integer FROM revoked
$$
""",
)
"""BUTUN token oilasini bekor qiladi (reuse aniqlanganda va logout'da, T-01-41)."""

AUTH_REFRESH_REVOKE_USER = PGFunction(
    schema="public",
    signature="auth_refresh_revoke_user(p_user_id uuid)",
    definition="""
RETURNS integer
LANGUAGE sql
SECURITY DEFINER
SET search_path = pg_catalog, public
VOLATILE
AS $$
    WITH revoked AS (
        UPDATE public.refresh_tokens
           SET revoked_at = now()
         WHERE user_id = p_user_id
           AND revoked_at IS NULL
        RETURNING 1
    )
    SELECT count(*)::integer FROM revoked
$$
""",
)
"""Foydalanuvchining BARCHA sessiyalarini bekor qiladi.

Parol almashtirilganda majburiy (ASVS V7): eski parolni bilgan hujumchining
mavjud sessiyasi parol almashtirilgandan keyin ham yashab qolmasligi kerak.
"""

AUTH_SUPPORT_FUNCTIONS: list[PGFunction] = [
    AUTH_FIND_LOGIN_BY_ID,
    AUTH_UPDATE_PASSWORD_HASH,
    AUTH_SET_ACTIVE,
    AUTH_REFRESH_ISSUE,
    AUTH_REFRESH_FIND,
    AUTH_REFRESH_ROTATE,
    AUTH_REFRESH_REVOKE_FAMILY,
    AUTH_REFRESH_REVOKE_USER,
]
"""`0003_auth_support` migratsiyasi yaratadigan to'plam."""

AUTH_SUPPORT_GRANT_SIGNATURES: tuple[str, ...] = (
    "auth_find_login_by_id(uuid)",
    "auth_update_password_hash(uuid, text, boolean)",
    "auth_set_active(uuid, boolean)",
    "auth_refresh_issue(uuid, uuid, text, uuid, timestamptz)",
    "auth_refresh_find(text)",
    "auth_refresh_rotate(text, text)",
    "auth_refresh_revoke_family(uuid)",
    "auth_refresh_revoke_user(uuid)",
)
"""`AUTH_SUPPORT_FUNCTIONS` bilan bir xil TARTIBDA.

Mosligi `tests/tenancy/test_login_bootstrap.py` da tekshiriladi: ro'yxat
ajralib qolsa funksiya yaratiladi-yu, `sbozor_app` uni chaqira olmaydi va
sessiya oqimi `permission denied` bilan yiqiladi.
"""


# ===========================================================================
# 0004_user_admin — FOYDALANUVCHI BOSHQARUVI VA PROFIL
# ===========================================================================
#
# `users` jadvali app-rolga BUTUNLAY yopiq (Pattern 2), ya'ni foydalanuvchi
# YARATISH, PROFIL O'QISH va TIL SAQLASH ham xuddi login yo'li kabi tor
# `SECURITY DEFINER` funksiyalari orqali o'tadi. Muqobil yechim — `users`
# ga `INSERT`/`UPDATE`/`SELECT` GRANT berish — butun naqshni bekor qilardi:
# o'shanda ORM orqali tasodifan global `select(User)` yozish yana mumkin
# bo'lardi va tenant chegarasi ilova kodining intizomiga qolardi.
#
# YUZA QASDDAN TOR: `auth_list_users` ixtiyoriy `WHERE` qabul qilmaydi —
# u faqat ANIQ ID RO'YXATI bo'yicha ishlaydi. ID'lar esa chaqiruvchida
# `user_market_roles` dan RLS OSTIDA olinadi, ya'ni funksiya global o'qish
# yuzasini kengaytirmaydi: boshqa bozor a'zosining ID'si birinchi qadamda
# umuman qaytmaydi. "Barcha foydalanuvchilarni bering" degan so'rov shakli
# bu yerda ATAYIN yo'q.

AUTH_CREATE_USER = PGFunction(
    schema="public",
    signature=(
        "auth_create_user(p_phone text, p_hash text, p_full_name text, "
        "p_locale text, p_is_platform_admin boolean)"
    ),
    definition="""
RETURNS uuid
LANGUAGE sql
SECURITY DEFINER
SET search_path = pg_catalog, public
VOLATILE
AS $$
    INSERT INTO public.users (
        phone_e164, password_hash, full_name, locale, is_platform_admin, must_change_password
    )
    VALUES (p_phone, p_hash, p_full_name, p_locale, p_is_platform_admin, true)
    ON CONFLICT (phone_e164) DO NOTHING
    RETURNING id
$$
""",
)
"""Yangi foydalanuvchi yaratadi; telefon BAND bo'lsa `NULL` qaytaradi (D-04).

`must_change_password` ATAYIN LITERAL `true` — parametr emas. D-02 bo'yicha
admin bergan parol HAR DOIM vaqtinchalik: uni birinchi kirishda almashtirish
majburiy. Parametr bo'lganida chaqiruvchi uni bir kun `false` bilan chaqirib
qo'yardi va vaqtinchalik parol doimiy parolga aylanardi — bunday teshikning
yagona kafolatlangan yopilishi uni UMUMAN mavjud qilmaslik.

`ON CONFLICT DO NOTHING` istisno o'rniga 0 qator beradi, ya'ni funksiya
`NULL` qaytaradi va chaqiruvchi uni `409 phone_taken` ga aylantiradi. Xom
`unique_violation` istisnosi tranzaksiyani ABORT qilardi va o'sha
tranzaksiyada yozilishi kerak bo'lgan audit qatori ham yo'qolardi.
"""

AUTH_SET_LOCALE = PGFunction(
    schema="public",
    signature="auth_set_locale(p_user_id uuid, p_locale text)",
    definition="""
RETURNS boolean
LANGUAGE sql
SECURITY DEFINER
SET search_path = pg_catalog, public
VOLATILE
AS $$
    WITH updated AS (
        UPDATE public.users
           SET locale = p_locale,
               updated_at = now()
         WHERE id = p_user_id
        RETURNING 1
    )
    SELECT count(*) > 0 FROM updated
$$
""",
)
"""Foydalanuvchi tilini profilda saqlaydi (D-13) — DB yagona haqiqat manbai.

`boolean` qaytaradi: qator topilmasa `false`. Chaqiruvchi buni 404 ga
aylantiradi, aks holda `PATCH /me` o'chirilgan foydalanuvchi uchun ham
"muvaffaqiyatli" javob berardi.

Qiymat `users_locale_allowed` CHECK konstrayti bilan cheklangan
(`sbozor_core.enums.Locale` dan hosil qilinadi), ya'ni bu funksiya orqali
ham noma'lum til yozib bo'lmaydi.
"""

AUTH_LIST_USERS = PGFunction(
    schema="public",
    signature="auth_list_users(p_user_ids uuid[])",
    definition="""
RETURNS TABLE (
    user_id uuid,
    phone_e164 text,
    full_name text,
    locale text,
    is_active boolean,
    must_change_password boolean,
    is_platform_admin boolean,
    created_at timestamptz
)
LANGUAGE sql
SECURITY DEFINER
SET search_path = pg_catalog, public
STABLE
AS $$
    SELECT u.id,
           u.phone_e164,
           u.full_name,
           u.locale,
           u.is_active,
           u.must_change_password,
           u.is_platform_admin,
           u.created_at
    FROM public.users AS u
    WHERE u.id = ANY(p_user_ids)
    ORDER BY u.created_at, u.id
$$
""",
)
"""ANIQ ID ro'yxati bo'yicha profil ma'lumoti (foydalanuvchilar ro'yxati, `/me`).

`password_hash` ATAYIN QAYTARILMAYDI: bu funksiyaning chaqiruvchilari
(ro'yxat ekrani, profil) parolga umuman tegmaydi, `auth_find_login*` esa
alohida mavjud. Hash'ni "har ehtimolga qarshi" qo'shish uni ro'yxat
javobiga tasodifan chiqarish yo'lini ochardi.
"""

AUTH_LIST_MARKETS_FULL = PGFunction(
    schema="public",
    signature="auth_list_markets_full()",
    definition="""
RETURNS TABLE (
    market_id uuid,
    market_name text,
    market_timezone text,
    is_active boolean
)
LANGUAGE sql
SECURITY DEFINER
SET search_path = pg_catalog, public
STABLE
AS $$
    SELECT m.id,
           m.name,
           m.timezone,
           m.is_active
    FROM public.markets AS m
    ORDER BY m.name
$$
""",
)
"""`GET /api/v1/markets` uchun bozor qatori — `timezone` bilan (D-06).

NEGA `auth_list_markets()` KENGAYTIRILMADI: u `0001` migratsiyasi yaratgan
obyekt va uning `RETURNS TABLE` imzosini o'zgartirish `CREATE OR REPLACE`
bilan MUMKIN EMAS (Postgres qaytish tipini almashtirishga yo'l bermaydi) —
ya'ni allaqachon qo'llangan migratsiyani qayta yozish kerak bo'lardi.
Additiv funksiya bu tarixni tegmasdan qoldiradi va `downgrade()` ham toza.

Ikkalasining vazifasi ham boshqacha: `auth_list_markets()` — LOGIN
oqimidagi bozor tanlash ro'yxati (faqat nom), bu esa boshqaruv panelining
bozor ro'yxati. Ikkalasi ham faqat bozor KONFIGURATSIYASINI ochadi, hech
qanday tenant ma'lumotini emas, shuning uchun `BYPASSRLS` roli baribir
kerak emas (D-06).
"""

USER_ADMIN_FUNCTIONS: list[PGFunction] = [
    AUTH_CREATE_USER,
    AUTH_SET_LOCALE,
    AUTH_LIST_USERS,
    AUTH_LIST_MARKETS_FULL,
]
"""`0004_user_admin` migratsiyasi yaratadigan to'plam."""

USER_ADMIN_GRANT_SIGNATURES: tuple[str, ...] = (
    "auth_create_user(text, text, text, text, boolean)",
    "auth_set_locale(uuid, text)",
    "auth_list_users(uuid[])",
    "auth_list_markets_full()",
)
"""`USER_ADMIN_FUNCTIONS` bilan bir xil TARTIBDA (`GRANT`/`REVOKE` imzolari)."""


# ===========================================================================
# 0005_platform_audit — PLATFORMA-GLOBAL AUDIT QATORLARINI O'QISH (Gap 5)
# ===========================================================================
#
# `login_failed` kabi yozuvlar ataylab `market_id = NULL` bilan yoziladi:
# rad etilgan login urinishida bozor NOMA'LUM va uni taxmin qilish jurnalga
# YOLG'ON dalil yozish bo'lardi. `audit_read` policy'si esa
# `market_id = app.market_id` shaklida, ya'ni bu qatorlar HECH QANDAY tenant
# konteksti bilan mos kelmaydi va mahsulot yo'lida HECH KIMGA ko'rinmaydi —
# ular faqat test-superuseri bilan o'qilardi (01-06, 01-07, 01-09 SUMMARY'da
# uch marta ochiq qayd etilgan bo'shliq).
#
# BU YERDA NAQSH BOSHQACHA VA SABABI MUHIM. Yuqoridagi funksiyalar `users` /
# `refresh_tokens` ustida ishlaydi: `users` da RLS UMUMAN YO'Q, ya'ni ega
# huquqi o'z-o'zidan yetarli. `audit_log` da esa RLS ENABLE+FORCE va
# `sbozor_owner` `NOSUPERUSER NOBYPASSRLS` — FORCE tufayli EGA HAM policy'ga
# bo'ysunadi. Shuning uchun `SECURITY DEFINER` YOLG'IZ YETMAYDI: u ega
# nomidan ishlab ham 0 qator qaytarardi. Funksiya AYNAN `audit_read_platform`
# policy'si (`FOR SELECT TO sbozor_owner USING (market_id IS NULL)`) bilan
# JUFTLIKDA ishlaydi — biri ikkinchisisiz ma'nosiz.
#
# YUZA QASDDAN TOR: funksiya ixtiyoriy `WHERE` qabul qilmaydi — sharti
# LITERAL `market_id IS NULL`. Ya'ni uni "RLS'siz butun audit jurnalini
# o'qish" vositasiga aylantirib bo'lmaydi: tenant qatorlari (`market_id`
# to'ldirilgan) bu funksiyadan HECH QACHON qaytmaydi.

AUTH_LIST_PLATFORM_AUDIT = PGFunction(
    schema="public",
    signature=(
        "auth_list_platform_audit(p_limit integer, p_before_at timestamptz, p_before_id bigint)"
    ),
    definition="""
RETURNS TABLE (
    id bigint,
    at timestamptz,
    business_date date,
    actor_user_id uuid,
    actor_label text,
    action text,
    table_name text,
    row_id uuid,
    old_value jsonb,
    new_value jsonb,
    changed_keys text[],
    request_id text,
    source text
)
LANGUAGE sql
SECURITY DEFINER
SET search_path = pg_catalog, public
STABLE
AS $$
    SELECT a.id,
           a.at,
           a.business_date,
           a.actor_user_id,
           a.actor_label,
           a.action,
           a.table_name,
           a.row_id,
           a.old_value,
           a.new_value,
           a.changed_keys,
           a.request_id,
           a.source
    FROM public.audit_log AS a
    WHERE a.market_id IS NULL
      AND (p_before_at IS NULL OR (a.at, a.id) < (p_before_at, p_before_id))
    ORDER BY a.at DESC, a.id DESC
    LIMIT COALESCE(p_limit, 0)
$$
""",
)
"""Platforma-global (`market_id IS NULL`) audit qatorlari — KEYSET sahifalash bilan.

`ip` ustuni ATAYIN QAYTARILMAYDI: `app.api.v1.audit.AuditEntry` uni ham
qaytarmaydi (D-12 maskalash qarori), ya'ni bu funksiya mavjud o'qish
shaklidan kengroq ma'lumot bermaydi.

KEYSET SEMANTIKASI `app.repositories.audit_repo.AuditRepository.list_audit`
BILAN AYNAN BIR XIL: `(at, id)` juftligi chegara juftligidan KICHIK,
`ORDER BY at DESC, id DESC`. Juftlik kerak, `at` yolg'iz emas — bir
tranzaksiyada yozilgan qatorlar aynan bir xil `at` ga ega bo'lishi mumkin va
`at <` predikati ularning bir qismini o'tkazib yuborardi. Chaqiruvchi
`p_limit` ga `limit + 1` beradi va "yana bormi?" savoliga shu ortiqcha qator
bilan javob topadi.

`p_before_at IS NULL` — birinchi sahifa (chegara yo'q). `p_before_at`
berilib `p_before_id` NULL qolsa juftlik solishtiruvi NULL beradi va natija
0 qator bo'ladi — FAIL-CLOSED, ya'ni yarim kursor jimgina butun sahifani
qaytarib yubormaydi.

`LIMIT COALESCE(p_limit, 0)`: xom `LIMIT p_limit` da `p_limit IS NULL`
Postgres uchun "CHEKLOVSIZ" degani, ya'ni chaqiruvchidagi bitta `None`
butun platforma-global jurnalni bir so'rovda tortib olardi. `COALESCE(...,
0)` uni fail-closed qiladi: kursor `NULLIF` naqshi bilan bir xil qoida —
noto'g'ri kirish XATO emas, 0 QATOR beradi.

INDEKS: `ix_audit_log_market_id_at` (`market_id`, `at DESC`) bu so'rovni
to'liq qamraydi — btree NULL'larni ham indekslaydi, shuning uchun
`market_id IS NULL` indeks bo'yicha qidiruv (`IS NULL` btree uchun
qidiriladigan shart) va `at DESC` tartibi bepul keladi.

XAVFSIZLIK: `audit_read_platform` policy'siz bu funksiya 0 qator qaytaradi
(`audit_log` da FORCE RLS, ega ham policy'ga bo'ysunadi) — juftlik
`tests/tenancy/test_login_bootstrap.py` da sabotaj bilan sinaladi.
`sbozor_app` esa o'sha policy'ni UMUMAN ishlata olmaydi, ya'ni funksiya
NULL qatorlarga yagona yo'l bo'lib qoladi.
"""

PLATFORM_AUDIT_FUNCTIONS: list[PGFunction] = [AUTH_LIST_PLATFORM_AUDIT]
"""`0005_platform_audit` migratsiyasi yaratadigan to'plam."""

PLATFORM_AUDIT_GRANT_SIGNATURES: tuple[str, ...] = (
    "auth_list_platform_audit(integer, timestamptz, bigint)",
)
"""`PLATFORM_AUDIT_FUNCTIONS` bilan bir xil TARTIBDA (`GRANT`/`REVOKE` imzolari)."""
