#!/usr/bin/env bash
# =============================================================================
# SBOZOR — ZAXIRA TSIKLI (FOUND-07, D-13, Pattern 4).
#
# Ishlatilishi: konteynerning ENTRYPOINT'i (`ops/backup/Dockerfile`).
# Argument olmaydi; sozlash faqat muhit o'zgaruvchilari orqali.
#
# Chiqish kodi: ⛔ YO'Q — bu tsikl ATAYIN CHIQMAYDI (pastdagi
# «SOZLANMAGANLIK SHOXI» bandiga qarang).
#
# =============================================================================
# ⛔ NEGA `cron` EMAS.
#
# Host `cron` uch narsani yo'qotardi: (a) u compose'dan TASHQARIDA yashaydi,
# ya'ni `docker compose up` bilan kelmaydi va yangi VPS'da JIMGINA
# o'rnatilmay qolardi; (b) uning holati konteyner ichida ko'rinmaydi;
# (c) konteyner restart bo'lsa o'tkazib yuborilgan kun QAYTA
# urinilmasdi. Bu tsikl esa har 10 daqiqada uyg'onadi va savolni BAZADAN
# so'raydi — ya'ni restart kunni YO'QOTMAYDI va ikkinchi yugurishni ham
# BOSHLAMAYDI (4-faza D-03 naqshi: holat Postgres'da, jarayon xotirasida
# EMAS).
#
# =============================================================================
# ⛔ NIMA O'LCHANMAYDI.
#
# Bu tsikl «zaxira BUGUN olindimi?» degan savolga javob beradi. U
# «zaxiradan tiklanadimi?» ni O'LCHAMAYDI (D-16, `run-backup.sh`
# sarlavhasi) va offsite reponing MAVJUDLIGINI ham oldindan tekshirmaydi:
# bu `restic` ning o'z ishi va nosozlik `backup_failed` bo'lib chiqadi.
# =============================================================================
set -euo pipefail

INTERVAL="${BACKUP_POLL_SECONDS:-600}"

# =============================================================================
# ⛔ 04:40 Asia/Tashkent — TANLOV, STANDART EMAS (R-10, Pitfall 9).
#
# Kunning boshqa fon vazifalari bilan to'qnashuv AYNAN o'lchangan:
#
#   03:20  retention   — kadrlarni AYNAN o'sha S3 kalitida siqib QAYTA
#                        YOZADI. Undan OLDIN olingan arxiv 03:20 da
#                        eskiradi va keyingi zaxira o'sha obyektlarni
#                        qaytadan yozardi (dedup foydasi NOL).
#   03:40  day_close   — kunni yopadi;
#   04:10  billing_close — patta hisobini yopadi.
#
# 04:40 uchalasidan ham KEYIN, ya'ni dump kechagi kunning YOPILGAN
# hisobini o'z ichiga oladi. Kadr olish oynasi (06:00–08:00, 16:00, 18:00)
# esa hali BOSHLANMAGAN — zaxira unga tegmaydi.
# =============================================================================
RUN_AFTER_HOUR="${BACKUP_RUN_AFTER:-04:40}"

WEEKLY_CHECK_AFTER="05:30"

configured() {
    # Uchala sir ham bo'lmasa zaxira TEXNIK JIHATDAN imkonsiz.
    [ -n "${RESTIC_REPOSITORY:-}" ] &&
        [ -n "${RESTIC_PASSWORD:-}" ] &&
        [ -n "${BACKUP_DATABASE_URL:-}" ]
}

already_done_today() {
    # ⛔ HOLAT BAZADA, KONTEYNER XOTIRASIDA EMAS. Xotiradagi bayroq
    #    restartda yo'qolardi va o'sha kuni IKKINCHI to'liq zaxira
    #    boshlanardi (offsite trafik + `forget --prune` ni ikki marta).
    #
    # ⚠ SAVOL Asia/Tashkent KUNIDA beriladi, UTC'da emas: 04:40 mahalliy
    #   vaqt UTC'da 23:40 — ya'ni UTC kuni bilan solishtirilsa chegara
    #   kun HAR KUNI noto'g'ri tomonga tushardi.
    #
    # ⚠ `psql` ning O'ZI yiqilsa (baza ko'tarilmagan) `pipefail` tufayli
    #   funksiya nol bo'lmagan kod qaytaradi va tsikl «bugun olinmagan»
    #   deb hisoblaydi. Bu TO'G'RI: `run-backup.sh` o'sha nosozlikka
    #   borib `backup_failed` bilan OVOZ chiqaradi, jim qolmaydi.
    psql "${BACKUP_DATABASE_URL}" -tAc "
    SELECT 1 FROM system_heartbeats
     WHERE component = 'backup'
       AND (last_seen_at AT TIME ZONE 'Asia/Tashkent')::date
           >= (now() AT TIME ZONE 'Asia/Tashkent')::date" | grep -q 1
}

while true; do
    NOW="$(TZ=Asia/Tashkent date +%H:%M)"

    # =========================================================================
    # ⛔ SOZLANMAGANLIK SHOXI — VA U `exit` CHAQIRMAYDI.
    #
    # Ikkala muqobil ham yomonroq:
    #
    #   * `exit 1` — `restart: unless-stopped` bilan bu CRASH-LOOP bo'lardi.
    #     Dev mashinasida `npm run up` jurnalini ifloslantirardi va odam
    #     uni «shovqin» deb o'chirib qo'yardi;
    #   * jim ishlab, yurak urishini YOZISH — D-15 ning butun ma'nosi
    #     yo'qolardi: sozlanmagan zaxira o'zini «ishlayapti» deb
    #     ko'rsatardi.
    #
    # ⛔ SHUNING UCHUN: nomlangan xabar `stderr` ga, zaxira BOSHLANMAYDI,
    #    yurak urishi YOZILMAYDI — va 26 soatdan keyin `backup_stale`
    #    (CRITICAL) ko'tariladi. Sozlanmagan zaxira uchun bu TO'G'RI
    #    signal (self-service qoidasi 2: dala ishi bloklamaydi, lekin
    #    bajarilmagani KO'RINADI).
    # =========================================================================
    if ! configured; then
        echo "backup_unconfigured: RESTIC_REPOSITORY / RESTIC_PASSWORD /" \
            "BACKUP_DATABASE_URL to'ldirilmagan — zaxira boshlanmadi va" \
            "yurak urishi yozilmadi (26 soatdan keyin backup_stale)" >&2
        sleep "${INTERVAL}"
        continue
    fi

    # `>=` — `>` EMAS: aynan 04:40 da uyg'ongan tsikl ham kunni boshlashi
    # kerak. `HH:MM` nol bilan to'ldirilgan qat'iy kenglikda, ya'ni
    # leksikografik solishtiruv vaqt tartibiga TENG.
    if ! [[ "${NOW}" < "${RUN_AFTER_HOUR}" ]] && ! already_done_today; then
        /opt/backup/run-backup.sh || echo "backup_failed exit=$?" >&2
    fi

    # =========================================================================
    # HAFTALIK BUTUNLIK TEKSHIRUVI (CLAUDE.md § Backups).
    #
    # ⛔ UNING NOSOZLIGI YURAK URISHINI O'CHIRMAYDI — VA BU ONGLI QAROR.
    #
    # `restic check` zaxira OLISHNING emas, REPO BUTUNLIGINING savoli. Uni
    # `backup_stale` ga ulash ikki xil nosozlikni bitta signalga yig'ardi:
    # bugungi zaxira muvaffaqiyatli olingan bo'lsa ham eski snapshotdagi
    # buzilgan blok butun kanalni «zaxira ishlamayapti» deb qichqirardi.
    #
    # ⚠ Alohida signal (`backup_check_stale`) D-25 ning sinfiga tushadi —
    #   yangi alert kaliti `ALERT_TITLE_KEY_COUNT` qulfini qizartirardi va
    #   uch tilli matn talab qilardi. Bu V2; bugun u `stderr` ga chiqadi.
    # =========================================================================
    if [[ "$(TZ=Asia/Tashkent date +%u)" == "7" ]] &&
        [[ "${NOW}" > "${WEEKLY_CHECK_AFTER}" ]]; then
        restic check --read-data-subset=5% ||
            echo "restic_check_failed exit=$?" >&2
    fi

    sleep "${INTERVAL}"
done
