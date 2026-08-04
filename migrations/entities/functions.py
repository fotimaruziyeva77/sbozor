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
from sbozor_core.models.snapshot import DEFAULT_SNAPSHOT_SLOTS

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
    "CAPTURE_DUE_MARKETS",
    "DEFAULT_SCHEDULE_NAME",
    "DEFAULT_SLOT_VALUES",
    "GRANT_SIGNATURES",
    "MARKET_ACTIVATE",
    "MARKET_CALENDAR_FUNCTIONS",
    "MARKET_CALENDAR_GRANT_SIGNATURES",
    "MARKET_CORE_FUNCTIONS",
    "MARKET_CORE_GRANT_SIGNATURES",
    "MARKET_CREATE",
    "MARKET_DELETE_DRAFT",
    "MARKET_DOMAIN_FUNCTIONS",
    "MARKET_DOMAIN_GRANT_SIGNATURES",
    "MARKET_IS_OPEN",
    "MARKET_RENAME",
    "PLATFORM_AUDIT_FUNCTIONS",
    "PLATFORM_AUDIT_GRANT_SIGNATURES",
    "SNAPSHOT_FUNCTIONS",
    "SNAPSHOT_GRANT_SIGNATURES",
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


# ===========================================================================
# 0007_market_domain — BOZOR HAYOT SIKLI (2-faza, MARKET-01…MARKET-05)
# ===========================================================================
#
# NEGA `markets` GA YOZISH YANA `SECURITY DEFINER` ORTIDA (RESEARCH Pattern 6):
#
# `sbozor_app` roliga `markets` da FAQAT `SELECT` grant'i berilgan (0001), va
# policy predikati `id = NULLIF(current_setting('app.market_id', true), '')::uuid`.
# Ya'ni ikki mustaqil to'siq bor va ikkalasi ham yangi bozor yaratishni
# imkonsiz qiladi:
#   1. GRANT yo'q  ->  `INSERT INTO markets` = `permission denied`;
#   2. GRANT berilganda ham yangi bozorning `id` si hali `app.market_id` ga
#      teng emas  ->  `WITH CHECK` rad etadi.
#
# Bu AYNAN `auth_create_user` bilan bir xil naqsh: tor, `search_path` pin
# qilingan, `PUBLIC` dan yopiq funksiya. Muqobil yechim — app-rolga `markets`
# ga `INSERT`/`UPDATE` berish — tenant chegarasini ilova kodining intizomiga
# qoldirardi.
#
# YUZA QASDDAN TOR VA BO'LINGAN: yaratish, faollashtirish, qayta nomlash va
# o'chirish — TO'RTTA alohida funksiya. Bittaga birlashtirilganda ular bitta
# GRANT bilan kelardi va "bozor yaratish huquqi" avtomatik "bozorni
# faollashtirish huquqi" ni ham bergan bo'lardi.
#
# `market_is_open()` esa BU GURUHDA, LEKIN `SECURITY DEFINER` EMAS — sababi
# o'z docstringida.

MARKET_CREATE = PGFunction(
    schema="public",
    signature=(
        "market_create(p_name text, p_timezone text, p_operating_since date, "
        "p_open_weekdays smallint[], p_address text, p_tin text, "
        "p_bank_account text, p_bank_mfo text, p_contact_phone text)"
    ),
    definition="""
RETURNS uuid
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
VOLATILE
AS $$
DECLARE
  v_market_id uuid;
BEGIN
  INSERT INTO public.markets (name, timezone, is_active)
  VALUES (p_name, COALESCE(NULLIF(p_timezone, ''), 'Asia/Tashkent'), false)
  RETURNING id INTO v_market_id;

  INSERT INTO public.market_profile (
      market_id, operating_since, open_weekdays,
      address, tin, bank_account, bank_mfo, contact_phone
  )
  VALUES (
      v_market_id,
      p_operating_since,
      p_open_weekdays,
      NULLIF(p_address, ''),
      NULLIF(p_tin, ''),
      NULLIF(p_bank_account, ''),
      NULLIF(p_bank_mfo, ''),
      NULLIF(p_contact_phone, '')
  );

  RETURN v_market_id;
END $$
""",
)
"""QORALAMA bozor + uning profil qatorini BIR TRANZAKSIYADA yaratadi (usta 1-qadam).

`is_active` LITERAL `false` va `p_is_active` nomli parametr YO'Q. Bu
`auth_create_user` dagi `must_change_password = true` bilan aynan bir xil
sabab: parametr bo'lganda chaqiruvchi uni bir kun `true` bilan berib
`activate` dagi TO'LIQLIK TEKSHIRUVINI butunlay chetlab o'tardi. Bunday
teshikning yagona kafolatlangan yopilishi — uni umuman mavjud qilmaslik.
Faollashtirish alohida funksiya, ya'ni alohida GRANT va alohida audit
hodisasi.

NEGA PROFIL QATORI SHU YERDA, ALOHIDA CHAQIRUVDA EMAS: `market_is_open()`
FAIL-CLOSED — `market_profile` qatori bo'lmasa u HAR KUNI `false` qaytaradi.
Ya'ni profilsiz bozor xato bermaydi, u shunchaki HECH QACHON ishlamaydi va
tushum jimgina nolga tushadi (RESEARCH Pattern 7 ogohlantirishi). Ikki
alohida chaqiruvda ikkinchisi tarmoq uzilishida yo'qolishi mumkin edi;
bitta funksiyada esa ikkalasi bitta tranzaksiyada.

`NULLIF(p_..., '')` MAJBURIY, stil emas: usta bo'sh maydonni odatda `''`
sifatida yuboradi va `''` `ck_market_profile_tin_format` regeksidan
O'TMAYDI. Ya'ni NULLIF'siz "STIR ko'rsatilmagan" holati bozor yaratishni
tushunarsiz CHECK xatosi bilan yiqitardi.

`p_timezone` bo'sh -> `'Asia/Tashkent'`. Bu standart QOLADI: vaqt mintaqasi
tushumga ta'sir qilmaydigan texnik sozlama va uning yagona qo'llanadigan
qiymati ham shu (WR-03).

⚠ `p_open_weekdays` NULL -> USTUNGA HAM NULL YOZILADI, ya'ni "HALI
TANLANMAGAN". Bu 0011 dagi tuzatish (WR-06) va u standart qiymatning
YO'QLIGI — kamchilik emas, tuzatishning O'ZI:

  * ilgari `INSERT` da parametr `COALESCE(...)` ichiga o'ralib
    `ARRAY[1,2,3,4,5,6,7]` standarti bilan yozilardi, ya'ni
    `array_length(open_weekdays,1) > 0` HAR DOIM rost bo'lardi;
  * demak `calendar_configured` har doim `True` va `calendar_missing`
    (step 7) to'sig'i BOZOR YARATADIGAN YAGONA yo'lda hech qachon ishga
    tushmasdi;
  * dushanba yopiladigan bozor "har kuni ochiq" deb faollashardi va
    6-fazadagi kunlik job o'sha kunga patta yozardi — sotuvchi yopiq kun
    uchun hisob olardi. Bu mahsulot oldini olish uchun mavjud bo'lgan
    nizo sinfi.

Endi `NULL` `calendar_missing` to'sig'ini ishga tushiradi va bozor
faollashmaydi; `market_is_open()` esa fail-closed bo'lgani uchun bunday
bozor uchun har kuni `false` beradi (`= ANY(NULL)` -> `NULL` -> uch qavatli
`COALESCE` oxiridagi `false`). Ikkala qatlam BIRGA ishlaydi: to'siq
faollashishga yo'l bermaydi, funksiya esa to'siqdan sirg'alib o'tgan holatda
ham patta yozilishiga yo'l bermaydi.

Ish rejimi ustaning 1-qadamida SO'RALADI (`MarketRequisitesForm`) —
yettala kun oldindan belgilangan holda, lekin QIYMAT SIFATIDA yuboriladi.
Ya'ni DB taxmin qilmaydi, UI esa oqilona taklif qiladi.
"""

DEFAULT_SCHEDULE_NAME = "Standart"
"""Faollashtirishda yoziladigan standart profilning nomi (D-01).

DB KONTENTI va ATAYIN BITTA TILDA (`StallStatus` bilan bir xil qoida): UI
uni tarjima QILMAYDI. Nom shu yerda konstanta, chunki uni ikki joy oladi —
`MARKET_ACTIVATE` ning tanasi va `0015` ning backfill'i — va ikki literal
ajralib ketsa backfill boshqa nomli profil yozardi.
"""

DEFAULT_SLOT_VALUES = ", ".join(f"('{slot.isoformat()}'::time)" for slot in DEFAULT_SNAPSHOT_SLOTS)
"""Standart slotlarning SQL `VALUES` ro'yxati — `DEFAULT_SNAPSHOT_SLOTS` dan HOSILA.

⚠ LITERAL QO'LDA TAKRORLANMAYDI. `PGFunction` ning ta'rifi oddiy Python
satri, ya'ni u QURILADI: yagona manba
`sbozor_core.models.snapshot.DEFAULT_SNAPSHOT_SLOTS` bo'lib qoladi va
ro'yxatni o'zgartirish funksiya tanasini AVTOMATIK o'zgartiradi. Nusxa
yozilganda esa model bilan DB ajralib ketardi va «admin hech nima
kiritmaydi» (D-01) da'vosi bir kuni jimgina boshqa jadval berardi.

Yon ta'siri FOYDALI: tana o'zgargani uchun `alembic check` keyingi safar
`replace_entity` ni O'ZI taklif qiladi — ya'ni ro'yxatni o'zgartirgan odam
migratsiya yozishga majbur bo'ladi.
"""

MARKET_ACTIVATE = PGFunction(
    schema="public",
    signature="market_activate(p_market_id uuid)",
    definition=f"""
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
VOLATILE
AS $$
DECLARE
  v_schedule_id uuid;
BEGIN
  UPDATE public.markets
     SET is_active = true,
         updated_at = now()
   WHERE id = p_market_id;

  INSERT INTO public.snapshot_schedules (market_id, name, period)
  SELECT p_market_id,
         '{DEFAULT_SCHEDULE_NAME}',
         daterange(current_date, NULL, '[)')
  WHERE NOT EXISTS (
      SELECT 1
        FROM public.snapshot_schedules AS existing
       WHERE existing.market_id = p_market_id
  )
  RETURNING id INTO v_schedule_id;

  IF v_schedule_id IS NOT NULL THEN
    INSERT INTO public.snapshot_schedule_slots (market_id, schedule_id, slot_time)
    SELECT p_market_id, v_schedule_id, defaults.slot_time
      FROM (VALUES {DEFAULT_SLOT_VALUES}) AS defaults(slot_time)
    ON CONFLICT DO NOTHING;
  END IF;
END $$
""",  # noqa: S608 -- SQL literallari `DEFAULT_SNAPSHOT_SLOTS` (`tuple[time, ...]`)
    # va `DEFAULT_SCHEDULE_NAME` dan quriladi; ikkalasi ham modul konstantasi,
    # tashqi kirish EMAS. Bu `PGFunction` ta'rifi — bajariladigan so'rov emas.
)
"""Qoralama bozorni JONLI holatga o'tkazadi VA standart kadr jadvalini yozadi.

=============================================================================
D-01 — ADMIN SNAPSHOT JADVALI UCHUN HECH NIMA KIRITMAYDI.

Bozor faollashtirilganda bitta ochiq oxirli profil («Standart») va
`DEFAULT_SNAPSHOT_SLOTS` dan yettita slot AVTOMATIK yoziladi. Admin
ertasi kuniyoq ishlaydigan jadvalga ega bo'ladi va xohlasa uni
tahrirlaydi — self-service qoidasining bevosita natijasi.

⚠ USTAGA YANGI QADAM QO'SHILMAYDI (`04-UI-SPEC.md` §4.9). «Snapshot
jadvali» qadami usta oqimiga qo'shilsa `completedStepCount` ni buzardi va
2-fazaning butun usta holati qayta hisoblanishi kerak bo'lardi. Jadval —
faollashtirishning YON MAHSULOTI, alohida qadam emas.

IDEMPOTENT — `WHERE NOT EXISTS` VA `ON CONFLICT DO NOTHING`:
funksiya ikkinchi marta chaqirilsa (qayta faollashtirish, `0015` ning
backfill'i, testdagi takroriy chaqiruv) IKKINCHI profil YARATILMAYDI. Bu
shunchaki tozalik emas: ikkita profil `ex_snapshot_schedules_no_overlap`
ni buzib, faollashtirishni SQLSTATE `23P01` bilan yiqitardi — ya'ni usta
oxirgi qadamda to'xtab qolardi.

`current_date` dan boshlanadi, `operating_since` dan EMAS: jadval «bugundan
boshlab kadr olamiz» degani, «bozor qachondan beri ishlaydi» degani emas.
Retroaktiv profil o'tmishdagi kunlar uchun reja materializatsiya qilishga
urinardi va ularning hammasi darhol `missed` bo'lardi.
=============================================================================

⚠ `LANGUAGE plpgsql`, `sql` EMAS — VA BU MAJBURIY, USLUB TANLOVI EMAS
   (o'lchangan, 04-03/T3).

`LANGUAGE sql` funksiyaning tanasi `CREATE FUNCTION` PAYTIDA parse va
validatsiya qilinadi (`check_function_bodies` standart `on`). Bu funksiyani
esa `0007_market_domain` yaratadi — `MARKET_CORE_FUNCTIONS` ustidan tsikl
qilib, MODULNING JORIY ta'rifidan. Ya'ni `sql` variantida `0007`
`relation "public.snapshot_schedules" does not exist` bilan yiqilardi va
NOL HOLATDAN qilingan har bir migratsiya to'xtardi (o'lchandi: butun
tenancy va integration to'plami `ERROR at setup` bilan tushdi).

`plpgsql` tanasi esa CREATE paytida tekshirilmaydi, ya'ni `0007` uni
muammosiz yaratadi va `0015` almashtiradi. Bu YANGI nayrang emas —
`MARKET_DELETE_DRAFT` `0010_calendar` dan beri AYNAN shu xususiyatga
tayanadi: uning tanasi `cameras`/`snapshots` ga havola qiladi, o'sha
jadvallar esa `0012`/`0014` da tug'iladi.

NARXI HALOL YOZILADI: `0007` bilan `0015` orasidagi oynada funksiya
tanasi hali mavjud bo'lmagan jadvallarga havola qiladi va CHAQIRILSA
ish paytida yiqilardi. U oynada uni hech kim chaqirmaydi (migratsiya
`head` gacha bitta buyruqda boradi, usta oqimi esa to'liq migratsiyalangan
bazani talab qiladi) — `market_delete_draft()` bilan aynan bir xil holat.

TO'LIQLIK TEKSHIRUVI BU YERDA ATAYIN YO'Q. U ilova qatlamida (02-11),
chunki javob "yo'q" emas, `409` + YETISHMAYOTGAN QADAMLAR RO'YXATI bo'lishi
kerak (`setup-status` bilan bir xil `blocking[]` shakli). DB funksiyasi
faqat "yiqildi" deya olardi va foydalanuvchi qaysi qadamga qaytishni
bilmasdi.

TESKARI YO'L YO'Q: `market_deactivate()` funksiyasi ATAYIN YARATILMAGAN.
Bu shunchaki "kerak emas" emas — u ikkita kafolatning asosi:
  * jonli bozorni `market_delete_draft()` bilan o'chirib bo'lmaydi;
  * o'tmishdagi tarif/toifa daxlsizligining qoralama istisnosi
    (`tariff_past_immutable()`) bir marta faollashgan bozorga hech qachon
    qayta qo'llanmaydi.
Bozorni vaqtincha to'xtatish kerak bo'lsa u kalendar istisnolari bilan
qilinadi (`market_calendar_exceptions`), bayroq bilan emas.
"""

MARKET_RENAME = PGFunction(
    schema="public",
    signature="market_rename(p_market_id uuid, p_name text)",
    definition="""
RETURNS void
LANGUAGE sql
SECURITY DEFINER
SET search_path = pg_catalog, public
VOLATILE
AS $$
    UPDATE public.markets
       SET name = p_name,
           updated_at = now()
     WHERE id = p_market_id
$$
""",
)
"""Bozor nomini o'zgartiradi — `markets` ga yozishning uchinchi (va oxirgi) yo'li.

Alohida funksiya, chunki nom o'zgartirish `MARKET_MANAGE` huquqi bo'lgan
har kimga ochiq bo'lishi mumkin, faollashtirish esa yo'q. Bitta umumiy
`market_update(...)` funksiyasi ikkala amalni bitta GRANT ostiga qo'yardi.
"""

MARKET_DELETE_DRAFT = PGFunction(
    schema="public",
    signature="market_delete_draft(p_market_id uuid)",
    definition="""
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
VOLATILE
AS $$
DECLARE
  v_is_active boolean;
BEGIN
  SELECT m.is_active INTO v_is_active
  FROM public.markets AS m
  WHERE m.id = p_market_id;

  IF v_is_active IS DISTINCT FROM false THEN
    RETURN false;
  END IF;

  -- 4-faza snapshot domeni (0014_snapshot_domain). BLOK NVR BLOKIDAN
  -- OLDIN TURISHI SHART va bu O'LCHANGAN, taxmin emas: `capture_runs`
  -- `cameras` ga kompozit FK `(market_id, camera_id)` bilan tayanadi,
  -- `cameras` esa pastdagi BIRINCHI o'chirish. Blok keyinga qo'yilganda
  -- chaqiruv `ForeignKeyViolation: update or delete on table "cameras"
  -- violates foreign key constraint "fk_capture_runs_market_id_camera_id_
  -- cameras"` bilan yiqiladi — va statik darvoza buni SEZMAYDI (matnda
  -- beshala jadval baribir bor).
  --
  -- Ichki tartib `SNAPSHOT_DELETE_ORDER` dan: `snapshots` ->
  -- `capture_runs` -> slotlar -> profillar -> `alert_events`.
  -- `alert_events` FK zanjirida umuman turmaydi, shuning uchun uning o'rni
  -- ixtiyoriy va u oxirida.
  DELETE FROM public.snapshots                  WHERE market_id = p_market_id;
  DELETE FROM public.capture_runs               WHERE market_id = p_market_id;
  DELETE FROM public.snapshot_schedule_slots    WHERE market_id = p_market_id;
  DELETE FROM public.snapshot_schedules         WHERE market_id = p_market_id;
  DELETE FROM public.alert_events               WHERE market_id = p_market_id;

  -- 3-faza NVR domeni (0012_nvr_domain). TARTIB MAJBURIY va u composite FK
  -- zanjiridan kelib chiqadi: uchala bolasi ham `nvr_devices` ga
  -- `(market_id, nvr_id)` bilan tayanadi, ya'ni ota-ona ULARDAN KEYIN
  -- o'chiriladi. `ON DELETE CASCADE` bu yerda ham ATAYIN ishlatilmadi —
  -- sabab pastdagi docstringda (u 4-fazadagi snapshotlarga ham JIMGINA
  -- tarqalardi va rasm-dalil izini o'chirib yuborardi).
  DELETE FROM public.cameras                    WHERE market_id = p_market_id;
  DELETE FROM public.nvr_discovery_runs         WHERE market_id = p_market_id;
  DELETE FROM public.nvr_credentials            WHERE market_id = p_market_id;
  DELETE FROM public.nvr_devices                WHERE market_id = p_market_id;

  DELETE FROM public.stall_assignments          WHERE market_id = p_market_id;
  DELETE FROM public.stall_category_periods     WHERE market_id = p_market_id;
  DELETE FROM public.tariffs                    WHERE market_id = p_market_id;
  DELETE FROM public.stall_code_registry        WHERE market_id = p_market_id;
  DELETE FROM public.stalls                     WHERE market_id = p_market_id;
  DELETE FROM public.vendors                    WHERE market_id = p_market_id;
  DELETE FROM public.zones                      WHERE market_id = p_market_id;
  DELETE FROM public.stall_categories           WHERE market_id = p_market_id;
  DELETE FROM public.market_calendar_exceptions WHERE market_id = p_market_id;
  DELETE FROM public.market_profile             WHERE market_id = p_market_id;
  DELETE FROM public.user_market_roles          WHERE market_id = p_market_id;
  DELETE FROM public.refresh_tokens             WHERE market_id = p_market_id;
  DELETE FROM public.markets                    WHERE id = p_market_id;

  RETURN true;
END $$
""",
)
"""Tashlab ketilgan QORALAMA bozorni butunlay o'chiradi; `false` = o'chirilmadi.

FAOL BOZORNI O'CHIRISH YO'LI UMUMAN YARATILMAGAN. `is_active = true` bo'lsa
funksiya `false` qaytaradi va BIRORTA qatorga tegmaydi. Bayroq `NULL`
bo'lganda ham (bozor topilmadi) `false` qaytadi — `IS DISTINCT FROM false`
shakli aynan shu ikki holatni birga qamraydi va FAIL-CLOSED bo'ladi.
Chaqiruvchi `false` ni 404 yoki 409 ga aylantiradi (02-11).

`ON DELETE CASCADE` ATAYIN ISHLATILMADI. Kaskad hozir qulay ko'rinardi,
lekin 6-fazada `daily_charges` / `payments` jadvallari tug'ilganda u
ULARGA HAM JIMGINA tarqalardi — ya'ni bitta `DELETE FROM markets` haqiqiy
moliyaviy tarixni o'chirib yuborardi va buni hech kim ko'rmasdi. Bu yerdagi
ANIQ ro'yxat esa yangi jadval qo'shilganda KO'RINADIGAN qarz qoldiradi:
jadval ro'yxatga qo'shilmasa `DELETE FROM markets` FK xatosi bilan yiqiladi
va sabab darhol ma'lum bo'ladi.

TARTIB — FK bo'yicha bolalardan ota-onaga: kameralar -> kashfiyot
yugurishlari -> NVR sirlari -> NVR qurilmalari -> biriktirishlar -> toifa
davrlari -> tariflar -> kod reyestri -> rastalar -> sotuvchilar -> zonalar ->
toifalar -> kalendar -> profil -> a'zoliklar -> tokenlar -> bozor.

⚠ `tariffs` va `stall_category_periods` ustidagi `DELETE` o'zgarmaslik
triggerlarini ishga tushiradi. Ular QORALAMA bozor uchun ataylab o'tkazib
yuboradi — sabab `migrations/entities/triggers.py::TARIFF_PAST_IMMUTABLE`
docstringida. Usiz bu funksiya `operating_since` o'tgan sanada bo'lgan har
qanday qoralama uchun HAR DOIM `23514` bilan yiqilardi.

=============================================================================
RO'YXATNING TO'LIQLIGI ENDI MEXANIK TEKSHIRILADI (3-faza, W0-7 / D-17).

Yuqoridagi "KO'RINADIGAN qarz" aslida ko'rinmas edi: u faqat kimdir
qoralama bozorni o'chirmoqchi bo'lganda, ISH PAYTIDA ko'rinardi.
`tests/integration/test_market_delete_guard.py` uni CI'ga ko'chirdi —
u `pg_catalog` dan `markets` ga chet el kaliti bilan bog'langan
jadvallarni o'qib, shu funksiyaning HAQIQIY tanasi bilan
(`pg_get_functiondef`, Python manbasidan EMAS) solishtiradi.

Ya'ni: yangi tenant jadvali qo'shgan odam bu funksiyani ham yangilashi
shart va uni unutish darhol qizil test beradi, yetishmayotgan jadval nomi
esa xato xabarida turadi.

✅ BAJARILDI (03-03): `0012_nvr_domain` to'rtta jadval olib keldi va
darvoza AYTGANIDEK QIZARDI — xato xabarida to'rtala nom ham turdi
(`['cameras', 'nvr_credentials', 'nvr_devices', 'nvr_discovery_runs']`).
Kaskad `0013_market_delete_guard` da, AYNAN O'SHA REJANING oynasida
kengaytirildi va darvoza qayta yashil bo'ldi. Ya'ni mexanizm o'zi uchun
mo'ljallangan ishni bajardi: qarz to'lqinlar ORASIDA emas, ICHIDA yopildi.

=============================================================================
✅ 4-FAZA QARZI YOPILDI (W0-6, `0015_market_delete_snapshots`, 04-03/T3).

`0014_snapshot_domain` beshta yangi tenant jadvalini olib keldi va yuqoridagi
darvoza AYTGANIDEK QIZARDI — xato xabarida beshala nom ham turdi
(`['alert_events', 'capture_runs', 'snapshot_schedule_slots',
'snapshot_schedules', 'snapshots']`). Kaskad `0015` da, AYNAN O'SHA
REJANING oynasida kengaytirildi va darvoza qayta yashil bo'ldi. Mexanizm
o'zi uchun mo'ljallangan ishni ikkinchi marta bajardi: qarz to'lqinlar
ORASIDA emas, REJA ICHIDA yopildi.

⚠ TARTIB STATIK DARVOZA BILAN O'LCHANMAYDI va bu muhim: matnda beshala
jadval bo'lsa-yu, blok NVR blokidan KEYIN tursa,
`test_cascade_covers_every_table_referencing_markets` YASHIL qolardi,
chaqiruv esa `ForeignKeyViolation` bilan yiqilardi (`capture_runs` ->
`cameras`). Aynan shuning uchun `test_draft_market_deletion_covers_the_
snapshot_domain` funksiyani HAQIQATAN chaqiradi — u ikkinchi, mustaqil
darvoza.

Ichki tartib `migrations/entities/__init__.py::SNAPSHOT_DELETE_ORDER` dan
olingan; reyestr yagona manba bo'lib qoladi va uning o'zi
`test_meta.py::test_snapshot_registries_are_self_consistent` bilan
qulflangan.

=============================================================================
WR-02 — IKKI QATLAM, IKKALASI HAM KERAK (03-03 da yopildi).

Bu funksiya tanasidagi `IS DISTINCT FROM false` sharti FAQAT SHU YO'LNI
qo'riqlaydi. `psql` dan yuborilgan `DELETE FROM markets` uni BUTUNLAY
chetlab o'tardi — ya'ni "faol bozorni o'chirib bo'lmaydi" da'vosi ilova
qatlamining odob-axloqiga tayanardi, sxemaga emas (T-03-17).

Ikkinchi qatlam `0013_market_delete_guard` da: `markets` jadvaliga
`BEFORE DELETE` trigger qo'yiladi (`markets_delete_guard()`), u
`OLD.is_active IS DISTINCT FROM false` bo'lganda `RAISE EXCEPTION` qiladi.
Trigger BU FUNKSIYANI BLOKLAMAYDI: u faqat qoralama bozorga yetib keladi,
ya'ni triggerning sharti hech qachon otilmaydi.
=============================================================================
"""

MARKET_IS_OPEN = PGFunction(
    schema="public",
    signature="market_is_open(p_market_id uuid, p_date date)",
    definition="""
RETURNS boolean
LANGUAGE sql
SET search_path = pg_catalog, public
STABLE
AS $$
    SELECT COALESCE(
        (SELECT e.is_open
           FROM public.market_calendar_exceptions AS e
          WHERE e.market_id = p_market_id
            AND e.exception_date = p_date),
        (SELECT EXTRACT(ISODOW FROM p_date)::smallint = ANY(p.open_weekdays)
           FROM public.market_profile AS p
          WHERE p.market_id = p_market_id),
        false
    )
$$
""",
)
"""Bozor shu kuni ishlaydimi (D-17/D-18). 6-fazaga kontrakt: bitta shart.

⚠ `SECURITY DEFINER` ATAYIN YO'Q — bu shu fayldagi YAGONA shunday funksiya
va farq qasddan. U CHAQIRUVCHI huquqi bilan ishlaydi, ya'ni RLS unga
TO'LIQ qo'llanadi: boshqa bozorning `market_id` si so'ralganda ikkala
subquery ham 0 qator beradi va natija `false` bo'ladi (o'lchangan).
`SECURITY DEFINER` qilish uni RLS'dan chiqarardi va bir bozor
boshqasining kalendarini — ya'ni uning bayram/ish kunlari jadvalini —
o'qiy olardi (T-02-22).

UCH QAVATLI `COALESCE` va tartibi MUHIM:
  1. `market_calendar_exceptions` — istisno HAR DOIM ustun (bayram yoki
     istisno ish kuni, D-18);
  2. `market_profile.open_weekdays` — haftalik jadval (ISO kun raqami);
  3. `false` — FAIL-CLOSED.

FAIL-CLOSED'NING TESKARI TOMONI: sozlamasi yo'q bozor HECH QACHON
ishlamaydi va tushum jimgina nolga tushadi. Aynan shuning uchun
`market_create()` profil qatorini bozor bilan BIR TRANZAKSIYADA yaratadi va
`activate` to'liqlik tekshiruvi `open_weekdays` ni ham talab qiladi.

`EXTRACT(ISODOW ...)` — dushanba=1 … yakshanba=7, ya'ni `open_weekdays`
massivi bilan bir xil asosda; hech qanday konversiya yozilmaydi.
"""

MARKET_CORE_FUNCTIONS: list[PGFunction] = [
    MARKET_CREATE,
    MARKET_ACTIVATE,
    MARKET_RENAME,
]
"""`0007_market_domain` YARATADIGAN to'plam — BU RO'YXAT MUZLATILGAN.

⚠ YANGI FUNKSIYA BU YERGA QO'SHILMAYDI (`AUDIT_TRIGGER_FUNCTIONS` bilan bir
xil qoida): `migrations/versions/0007_market_domain.py` shu ro'yxat ustidan
`upgrade()` da ham, `downgrade()` da ham TSIKL qiladi.

NEGA AYNAN UCHTASI — bu bo'linish TEXNIK ZARURAT, tartib emas.
`market_is_open()` `LANGUAGE sql` bo'lib, uning tanasi `CREATE FUNCTION`
paytida PARSE VA VALIDATSIYA qilinadi (`check_function_bodies` standart
`on`). Tana `market_calendar_exceptions` jadvaliga murojaat qiladi, u esa
`0010_calendar` da tug'iladi — ya'ni funksiyani `0007` da yaratishga urinish
`relation "public.market_calendar_exceptions" does not exist` bilan
YIQILARDI. `market_delete_draft()` esa `stall_assignments` / `vendors` /
`market_calendar_exceptions` dan `DELETE` qiladi; u plpgsql bo'lgani uchun
CREATE paytida tekshirilmaydi, lekin uning YAGONA ma'noli o'rni — barcha
o'sha jadvallar mavjud bo'lgan payt, ya'ni `0010`.
"""

MARKET_CORE_GRANT_SIGNATURES: tuple[str, ...] = (
    "market_create(text, text, date, smallint[], text, text, text, text, text)",
    "market_activate(uuid)",
    "market_rename(uuid, text)",
)
"""`MARKET_CORE_FUNCTIONS` bilan bir xil TARTIBDA (`GRANT`/`REVOKE` imzolari)."""

MARKET_CALENDAR_FUNCTIONS: list[PGFunction] = [
    MARKET_DELETE_DRAFT,
    MARKET_IS_OPEN,
]
"""`0010_calendar` YARATADIGAN to'plam — kalendar jadvali bilan BIRGA.

Ikkalasi ham `market_calendar_exceptions` ga tegadi, ya'ni ular o'sha jadval
tug'ilgan migratsiyada yaratilishi SHART (sabab `MARKET_CORE_FUNCTIONS`
docstringida).
"""

MARKET_CALENDAR_GRANT_SIGNATURES: tuple[str, ...] = (
    "market_delete_draft(uuid)",
    "market_is_open(uuid, date)",
)
"""`MARKET_CALENDAR_FUNCTIONS` bilan bir xil TARTIBDA.

`market_is_open` ham shu ro'yxatda: u `SECURITY DEFINER` emas, lekin
`PUBLIC` dan `REVOKE` va `sbozor_app` ga `GRANT` baribir kerak —
yaratilgandan keyin Postgres unga `EXECUTE TO PUBLIC` ni standart beradi va
usiz bazadagi HAR QANDAY rol uni chaqira olardi. (RLS baribir qatorlarni
yashiradi, lekin funksiyaning MAVJUDLIGI ham keraksiz axborot.)
"""

MARKET_DOMAIN_FUNCTIONS: list[PGFunction] = [
    *MARKET_CORE_FUNCTIONS,
    *MARKET_CALENDAR_FUNCTIONS,
]
"""Bozor hayot siklining BARCHA funksiyalari — autogenerate reyestri uchun.

Faqat KUZATUV ro'yxati (`ALL_ENTITIES` shundan quriladi): `register_entities()`
unga qarab ta'rif o'zgarganda `op.replace_entity(...)` taklif qiladi. Birorta
migratsiya bu aggregat ustidan tsikl QILMAYDI — har bir migratsiya o'z
scope'li ro'yxatini oladi (`ALL_TRIGGER_FUNCTIONS` bilan bir xil naqsh).
"""

MARKET_DOMAIN_GRANT_SIGNATURES: tuple[str, ...] = (
    *MARKET_CORE_GRANT_SIGNATURES,
    *MARKET_CALENDAR_GRANT_SIGNATURES,
)
"""`MARKET_DOMAIN_FUNCTIONS` bilan bir xil TARTIBDA (`GRANT`/`REVOKE` imzolari)."""


# ===========================================================================
# 0015_market_delete_snapshots — SNAPSHOT QUVURINING TIK YUZASI (4-faza)
# ===========================================================================
#
# NEGA TIKKA ALOHIDA `SECURITY DEFINER` FUNKSIYA KERAK (§S-3, A.3):
#
# Bu 3-fazada BO'LMAGAN muammo. Kashfiyot jobi BITTA `market_id` bilan
# chaqirilgan — u navbat xabaridan kelgan. Tik esa HAMMA bozorlar ustida
# ishlashi kerak, `sbozor_app` roli esa tenant kontekstisiz BIRORTA bozorni
# ko'rmaydi (`markets` policy'si `id = app.market_id`).
#
# Loyihada bu muammoning ALLAQACHON yechilgan shakli bor:
# `auth_list_markets_full()` (`services/core-api/app/repositories/
# market_repo.py:111-165`). Quyidagi funksiya uning JUFTI va u AYNAN o'sha
# qoidaga bo'ysunadi: yuza iloji boricha TOR bo'ladi.

CAPTURE_DUE_MARKETS = PGFunction(
    schema="public",
    signature="capture_due_markets()",
    definition="""
RETURNS TABLE (market_id uuid, due_count integer)
LANGUAGE sql
SECURITY DEFINER
SET search_path = pg_catalog, public
STABLE
AS $$
    SELECT m.id,
           COALESCE(due.total, 0)::integer
      FROM public.markets AS m
      LEFT JOIN LATERAL (
          SELECT count(*)::integer AS total
            FROM public.capture_runs AS r
           WHERE r.market_id = m.id
             AND r.status = 'pending'
             AND r.scheduled_at <= now()
      ) AS due ON true
     WHERE m.is_active
       AND (
           COALESCE(due.total, 0) > 0
           OR NOT EXISTS (
               SELECT 1
                 FROM public.capture_runs AS planned
                WHERE planned.market_id = m.id
                  AND planned.business_date = ((now() AT TIME ZONE 'Asia/Tashkent')::date)
           )
       )
$$
""",
)
"""Tik uchun TOR yuza: qaysi bozorda ish bor (FAQAT identifikator va soni).

=============================================================================
YUZANING TORLIGI — BU FUNKSIYANING BUTUN XAVFSIZLIK DA'VOSI (T-04-16).

Funksiya `SECURITY DEFINER`, ya'ni u RLS'ni CHETLAB O'TADI. Qaytaradigan
yuzasi qanchalik keng bo'lsa, chetlab o'tish shunchalik keng — shuning
uchun u AYNAN ikkita ustun beradi: bozor identifikatori va muddati kelgan
slotlar soni. Bozor NOMI ham, kamera ham, sotuvchi ham, kadr ham YO'Q.

Tik keyin HAR BOZOR uchun ALOHIDA tranzaksiya ochadi va unda
`set_tenant_context(market_id=..., actor_kind=ActorKind.SYSTEM)` chaqiradi
(`jobs/discovery.py::_system_transaction()` naqshi) — ya'ni keyingi BARCHA
so'rovlar odatdagidek RLS ostidan o'tadi. Bitta tranzaksiyada ikki bozorni
aralashtirish tenant sizib chiqishining eng qisqa yo'li bo'lardi, chunki
GUC'lar `SET LOCAL` bilan qo'yiladi va `COMMIT` da tozalanadi.

⚠ SQL TANASIDAGI IZOHLARDA BOZOR NOMI YOKI SOTUVCHI HAQIDA YOZMANG:
darvoza `pg_get_functiondef()` chiqishini o'qiydi va u SQL izohlarini HAM
o'z ichiga oladi (bu Python docstringi esa kirmaydi — u xavfsiz).
=============================================================================

IKKINCHI SHART (`NOT EXISTS`) — «REJANING O'ZI YARATILMADI» HOLATI.

Bozor faqat `pending` qatorlari bo'lgani uchun qaytarilsa, BIRINCHI tik
hech qachon reja yaratmasdi: reja yo'q -> `pending` yo'q -> bozor
ko'rinmaydi -> reja yana yaratilmaydi. Bu KLASSIK JIM YIQILISH
(`04-RESEARCH.md` §B.5): hech qanday xato chiqmaydi, hech qanday alert
bo'lmaydi, bozor esa kadrsiz qoladi.

Shuning uchun ikkinchi shart bugungi biznes-kunga rejasi HALI
materializatsiya qilinmagan faol bozorlarni ham qaytaradi. Bugungi kun
`(now() AT TIME ZONE 'Asia/Tashkent')::date` bilan hisoblanadi, ya'ni
`capture_runs.business_date` ning generated ifodasi bilan AYNAN bir xil
mintaqada.

`STABLE` (`VOLATILE` emas): funksiya YOZMAYDI, faqat o'qiydi. `now()` ham
tranzaksiya ichida barqaror.

USTUN HAVOLALARI ALIAS BILAN: `RETURNS TABLE (market_id ...)` chiqish nomi
SQL tanasida ko'rinadigan o'zgaruvchi bo'lib qoladi, ya'ni `r.market_id`
o'rniga `market_id` yozish `column reference is ambiguous` xatosini
berardi (fayl boshidagi umumiy qoida).
"""

SNAPSHOT_FUNCTIONS: list[PGFunction] = [CAPTURE_DUE_MARKETS]
"""`0015_market_delete_snapshots` YARATADIGAN to'plam.

⚠ `ALL_FUNCTIONS` GA QO'SHILMAYDI va bu ATAYIN (o'sha ro'yxatning o'z
docstringi buni taqiqlaydi): `ALL_FUNCTIONS` — `0001_identity` ning
MUZLATILGAN to'plami va `0001` uning ustidan tsikl qiladi. Yangi nomni u
yerga qo'shish nol holatdan qilingan migratsiyani mavjud bo'lmagan
obyektga `GRANT` berishga majburlab yiqitardi.

Naqsh `AUTH_SUPPORT_FUNCTIONS` / `USER_ADMIN_FUNCTIONS` /
`PLATFORM_AUDIT_FUNCTIONS` bilan aynan bir xil: har migratsiya O'Z
scope'li ro'yxatini oladi.
"""

SNAPSHOT_GRANT_SIGNATURES: tuple[str, ...] = ("capture_due_markets()",)
"""`SNAPSHOT_FUNCTIONS` bilan bir xil TARTIBDA (`GRANT`/`REVOKE` imzolari).

`REVOKE ALL ... FROM PUBLIC` MAJBURIY: `CREATE FUNCTION` dan keyin Postgres
yangi funksiyaga `EXECUTE TO PUBLIC` ni STANDART beradi, ya'ni bazadagi HAR
QANDAY rol RLS'ni chetlab o'tadigan bu funksiyani chaqira olardi.
"""
