-- SBOZOR — DB rollari. ROL ATRIBUTLARI UCHUN YAGONA HAQIQAT MANBAI.
--
-- Bu fayl IKKI joyda bajariladi:
--   1) `db` konteyneri birinchi ishga tushganda — docker-entrypoint-initdb.d orqali
--   2) `tests/conftest.py` tomonidan testcontainer ustida — VERBATIM o'qib bajariladi
--
-- Shuning uchun bu yerda psql o'zgaruvchilari (:'var') yoki env interpolatsiyasi
-- ISHLATILMAYDI va hech qanday parol literali YO'Q (parollar 02-passwords.sh da).
--
-- NEGA (FOUND-02 / T-01-01):
--   `FORCE ROW LEVEL SECURITY` faqat jadval EGASINI policy'ga bo'ysundiradi.
--   Superuser va BYPASSRLS atributli rollar RLS'ni HAR DOIM chetlab o'tadi.
--   Ya'ni NOSUPERUSER + NOBYPASSRLS — tenant izolyatsiyasining yagona haqiqiy
--   nazorati. Ilova (va testlar) hech qachon `postgres` bilan ulanmaydi.
--
-- Rollar:
--   sbozor_owner — DDL/migratsiya egasi (Alembic)
--   sbozor_app   — ilova DML roli (core-api va BARCHA RLS testlari)

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'sbozor_owner') THEN
        CREATE ROLE sbozor_owner
            LOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE NOINHERIT;
    END IF;
END
$$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'sbozor_app') THEN
        CREATE ROLE sbozor_app
            LOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE NOINHERIT;
    END IF;
END
$$;

-- Idempotentlik: rol allaqachon mavjud bo'lsa ham atributlar qat'iy qayta qo'yiladi.
-- (Fayl testlarda takror bajarilishi mumkin.)
ALTER ROLE sbozor_owner LOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE NOINHERIT;
ALTER ROLE sbozor_app   LOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE NOINHERIT;

-- `public` sxema egasi — migratsiya roli.
ALTER SCHEMA public OWNER TO sbozor_owner;

-- Hech kim (jumladan sbozor_app) `public` da obyekt yarata olmaydi (T-01-06).
REVOKE CREATE ON SCHEMA public FROM PUBLIC;

GRANT USAGE ON SCHEMA public TO sbozor_owner;
GRANT USAGE ON SCHEMA public TO sbozor_app;
