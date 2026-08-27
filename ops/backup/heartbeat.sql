-- ===========================================================================
-- SBOZOR — ZAXIRA JARAYONINING YURAK URISHI (FOUND-06 -> FOUND-07, D-15).
--
-- Chaqiruvchi: `ops/backup/run-backup.sh` ning ENG OXIRGI qadami.
-- Chaqirilishi:
--     psql "$BACKUP_DATABASE_URL" -v ON_ERROR_STOP=1 \
--          -v day=YYYY-MM-DD -f /opt/backup/heartbeat.sql
--
-- ===========================================================================
-- ⛔ KOMPONENT NOMI BU FAYLDA AYNAN BIR MARTA YOZILADI.
--
-- U `services/core-api/app/jobs/alerting.py` dagi `BACKUP_COMPONENT`
-- konstantasi bilan MATN SIFATIDA bog'langan. Ikkisi ajralib ketsa
-- nosozlik shakli o'ta yomon bo'lardi: zaxira ishlab turardi,
-- `/internal/self-check` esa komponentni MANGU `never_seen` da
-- ko'rsatardi va `alert_sweep` har kuni CRITICAL alert yozardi —
-- ya'ni to'g'ri ishlayotgan tizim o'zini o'zi buzuq deb e'lon qilardi.
--
-- Tenglik `tests/unit/test_backup_contract.py` da o'lchanadi: darvoza
-- qiymatni SHU FAYLDAN o'qiydi va uni MAHSULOT KONSTANTASIDAN import
-- qiladi (literal takrorlanmaydi).
-- ===========================================================================
-- ⛔ SATR BIRLASHTIRISH YO'Q — `:'day'` BOG'LANGAN O'ZGARUVCHI (T-08-22).
--
-- `psql -v` qiymati `:'day'` shaklida QOCHIRILGAN satr sifatida
-- qo'yiladi. Buyruq qatorida SQL yig'ish (`"... '${TODAY}' ..."`) esa
-- inyeksiya yuzasi ochardi va `ON_ERROR_STOP=1` bilan birga u faqat
-- «xato bo'lmasa jim o'tadi» rejimida ishlardi.
--
-- ⚠ `system_heartbeats` — GLOBAL jadval: unda `market_id` YO'Q va u RLS
--   tsikliga kirmaydi (`0014_snapshot_domain.py` §6). Ya'ni bu yozuvda
--   tenant konteksti (`SET LOCAL`) TALAB QILINMAYDI.
--
-- ⚠ `component` — BIRLAMCHI KALITNING O'ZI, surrogat `id` YO'Q. Shuning
--   uchun `ON CONFLICT (component) DO UPDATE` har yugurishda AYNAN BITTA
--   qatorni yangilaydi va ikkinchi qator paydo bo'la olmaydi.
-- ===========================================================================
INSERT INTO system_heartbeats (component, last_seen_at, detail)
VALUES ('backup', now(), jsonb_build_object('business_date', :'day'))
ON CONFLICT (component) DO UPDATE
   SET last_seen_at = now(),
       detail       = EXCLUDED.detail;
