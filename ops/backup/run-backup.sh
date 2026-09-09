#!/usr/bin/env bash
# =============================================================================
# SBOZOR — FOUND-07 ning ZAXIRA ZANJIRI: dump + arxiv + retention + yurak
# urishi, AYNAN SHU TARTIBDA.
#
# Ishlatilishi:
#     /opt/backup/run-backup.sh          # `loop.sh` chaqiradi
#     docker compose -f deployment/compose.yaml -f deployment/compose.prod.yml exec backup /opt/backup/run-backup.sh   # qo'lda
#
# Chiqish kodi: 0 — TO'RTALA qadam ham bajarildi VA yurak urishi yozildi;
# nol bo'lmagan kod — zanjir o'sha qadamda TO'XTADI va yurak urishi
# YOZILMADI.
#
# =============================================================================
# ⛔ NIMA O'LCHANMAYDI.
#
# Bu skript «zaxira OLINDI» ni o'lchaydi, «zaxiradan TIKLANADI» ni EMAS.
# Ikkinchisi ikki qatlamda va ikkalasi ham boshqa joyda (D-16):
#
#   (a) CI qatlami   — `tests/integration/test_restore_drill.py`
#                      («dump -> toza server -> ma'lumot joyida»);
#   (b) Ops qatlami  — `08-HUMAN-UAT.md` («OFFSITE repodan tiklandi»),
#                      egasi Ops, CI'da HECH QACHON o'lchanmaydi.
#
# ⛔ `restic check` ham bu yerda EMAS — u `loop.sh` da, haftada bir marta.
#    Uning nosozligi zaxira olishning emas, repo BUTUNLIGINING nosozligi.
# =============================================================================
set -euo pipefail

# =============================================================================
# 0. MAJBURIY ENV DARVOZALARI.
#
# ⛔ `:-` BILAN BO'SH STANDART BERILMAYDI. Bo'sh `RESTIC_REPOSITORY` bilan
#    restic joriy katalogni repo deb qabul qilardi va zaxira KONTEYNER
#    ICHIDA, konteyner bilan birga o'ladigan qatlamda yotardi — ya'ni
#    «boshqa failure domain» talabi (D-14) jimgina buzilardi.
#
# ⛔ `BACKUP_DATABASE_URL` — libpq shakli (`postgresql://…`). `DATABASE_URL`
#    ISHLATILMAYDI: u `postgresql+asyncpg://` (SQLAlchemy dialekti) va
#    `psql`/`pg_dump` uni `invalid URI scheme` bilan rad etadi (Pitfall 8b).
# =============================================================================
: "${BACKUP_DATABASE_URL:?libpq shakli MAJBURIY (postgresql://…) — DATABASE_URL EMAS}"
: "${RESTIC_REPOSITORY:?offsite repo manzili MAJBURIY (D-14: boshqa failure domain)}"
# ⚠ Quyidagi xabarda APOSTROF YO'Q va bu MAJBURIY: `${VAR:?matn}` ichida
#   yolg'iz `'` bash uchun ochilgan qo'shtirnoq bo'lib qoladi va butun
#   skript `unexpected EOF while looking for matching` bilan yiqiladi
#   (o'lchandi: `bash -n` shu qatorda to'xtadi).
: "${RESTIC_PASSWORD:?repo paroli MAJBURIY — parolsiz zaxira BUTUNLAY tiklanmaydi}"

TODAY="$(TZ=Asia/Tashkent date +%F)"

# =============================================================================
# 1. REPO MAVJUDMI.
#
# ⛔ `restic init` ni HAR SAFAR chaqirish mavjud repoda XATO beradi
#    («repository master key and config already initialized») va `set -e`
#    ostida u butun zanjirni birinchi qadamda o'ldirardi (Pitfall 10).
#    Shart shakli: birinchi yugurish avtomatik, keyingilari jim.
# =============================================================================
restic cat config >/dev/null 2>&1 || restic init

# =============================================================================
# 2. POSTGRES — ⛔ QUVUR YO'Q.
#
# (a) `pg_dump | restic backup --stdin` NOSOZLIKNI YUTADI. POSIX quvurida
#     OXIRGI buyruqning chiqish kodi qaytadi, ya'ni `pg_dump` yiqilganda
#     (parol xato, disk to'la, ulanish uzildi) restic BO'SH yoki
#     QISQARTIRILGAN oqimni muvaffaqiyat bilan yozardi, tsikl yurak
#     urishini yozardi va `backup_stale` MANGU jim turardi — FOUND-07
#     ning butun kafolati soxta bo'lardi (Pitfall 5). `--stdin-from-command`
#     esa buyruqning CHIQISH KODINI tekshiradi: rasmiy hujjatning o'z
#     jumlasi — «A non-zero exit code from the command causes restic to
#     cancel the backup».
#
# (b) `--compress=0` MAJBURIY. `--format=custom` standart holatda zlib
#     bilan siqadi; siqilgan oqimda BITTA baytning o'zgarishi undan
#     keyingi BARCHA baytlarni o'zgartiradi, ya'ni restic har kuni butun
#     bazani YANGI ma'lumot deb saqlardi va 14 kunlik retention 14 x to'liq
#     baza bo'lardi (Pitfall 6). Siqishni restic O'ZI qiladi
#     (`--compression auto` — standart qiymat), ya'ni ham dedup, ham siqish.
# =============================================================================
restic backup \
  --stdin-from-command \
  --stdin-filename "sbozor-${TODAY}.dump" \
  --tag postgres --tag "day-${TODAY}" \
  -- pg_dump --format=custom --compress=0 --no-owner --no-privileges \
             --dbname="${BACKUP_DATABASE_URL}"

# =============================================================================
# 3. OBYEKT-OMBOR — `:ro` mount qilingan SeaweedFS hajmi.
#
# Kadr arxivi yo'qolsa «band, lekin to'lovsiz» da'vosining RASM-DALILI
# yo'qoladi, ya'ni mahsulotning asosiy argumenti (`ops/seaweedfs/README.md`
# §5). Shuning uchun baza va arxiv BIR XIL toifada zaxiralanadi.
# =============================================================================
restic backup --tag seaweedfs --tag "day-${TODAY}" /seaweed

# =============================================================================
# 4. RETENTION — qiymatlar CLAUDE.md § Backups va D-12 dan, LITERAL.
#
# ⚠ Ular `tests/unit/test_backup_contract.py` da QULFLANGAN (C-3): siyosat
#   o'zgarsa u ONGLI o'zgarish bo'lishi kerak, yo'l-yo'lakay tahrir emas.
# =============================================================================
restic forget --keep-daily 14 --keep-weekly 8 --keep-monthly 12 --prune

# =============================================================================
# 5. ⛔ YURAK URISHI — ENG OXIRIDA, VA FAQAT SHU YERGACHA YETIB KELINGANDA.
#
# Yuqoridagi `set -e` har qanday nosozlikda skriptni TO'XTATADI, ya'ni
# `system_heartbeats['backup']` qatori YOZILMAYDI va `alert_sweep` 26
# soatdan keyin `backup_stale` (CRITICAL, `never_suppressed`) ni
# ko'taradi (D-15).
#
# ⛔ `trap ... EXIT` YOKI «finally» ICHIDA YOZILMAYDI. O'sha shakl yurak
#    urishini NOSOZLIKDA HAM yozardi — ya'ni tizim o'zining ishlamayotganini
#    «muvaffaqiyat» deb belgilardi va D-15 ning butun ma'nosi yo'qolardi.
#    Taqiq `tests/unit/test_backup_contract.py` da mexanik.
#
# ⛔ SQL SATR BIRLASHTIRISH YO'Q: komponent nomi ham, sana ham FAYLDA
#    (`heartbeat.sql`), sana esa `-v day=` bilan BOG'LANGAN o'zgaruvchi
#    sifatida uzatiladi va `ON_ERROR_STOP=1` jim xatoni imkonsiz qiladi
#    (T-08-22).
# =============================================================================
psql "${BACKUP_DATABASE_URL}" -v ON_ERROR_STOP=1 \
     -v day="${TODAY}" -f /opt/backup/heartbeat.sql
