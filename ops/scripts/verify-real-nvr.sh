#!/usr/bin/env bash
# =============================================================================
# SBOZOR — REAL Hikvision qurilmasining DALA ZONDI.
#
# ⚠⚠ BU SKRIPT MAHSULOTNI EMAS, **SIMULYATORNING HAQIQIYLIGINI** O'LCHAYDI.
#
# 3-fazaning hamma narsasi `services/nvr-sim` ustida tekshirilgan. Bu esa
# Pitfall 4 ni ochiq qoldiradi: `simulator-confirms-itself` — sim'ning
# fixture'lari real qurilmaning shaklidan chetga chiqqan bo'lsa, butun CI
# yashil bo'lib turadi va tizim BIRINCHI marta Karmanada yiqiladi.
#
# Yagona yopish yo'li — real qurilmadan XOM javoblarni olib, ularni
# `services/nvr-sim/fixtures/` bilan SOLISHTIRISH. Shuning uchun bu
# skriptning chiqishi **JSON**: uni saqlash, `jq` bilan kesish va fixture
# bilan `diff` qilish mumkin.
#
# Farq topilsa — bu **SIM'NING NUQSONI**, mahsulotning emas. Tuzatish yo'li:
# fixture'ni real dump bilan yangilash (`ops/docs/nvr-onboarding.md` §4).
# =============================================================================
#
# Ishlatilishi:
#     ops/scripts/verify-real-nvr.sh http://192.168.1.64 sbozor 'parol'
#     ops/scripts/verify-real-nvr.sh http://192.168.1.64 sbozor 'parol' > karmana.json
#
# Talab qilinadi: `curl` (Digest bilan), `date`. `jq` — IXTIYORIY (faqat
# chiqishni chiroyli ko'rsatish uchun; skript o'zi JSON'ni QO'LDA quradi).
#
# Chiqish kodi: 0 — zond bajarildi (natija JSON'da, "ok" maydonlari bilan);
#               1 — argument yetishmadi yoki `curl` topilmadi.
#
# ⚠ ZOND QURILMANI O'ZGARTIRMAYDI: faqat `GET` so'rovlari yuboriladi.
#   Hech qanday sozlama yozilmaydi, hech qanday oqim yozib olinmaydi.

set -uo pipefail

BASE_URL="${1:-}"
USERNAME="${2:-}"
PASSWORD="${3:-}"
MAX_CHANNEL_FRAMES="${MAX_CHANNEL_FRAMES:-32}"
CONCURRENT_STREAMS="${CONCURRENT_STREAMS:-3}"
TIMEOUT="${TIMEOUT:-10}"

if [ -z "$BASE_URL" ] || [ -z "$USERNAME" ] || [ -z "$PASSWORD" ]; then
    echo "ISHLATILISHI: $0 <base-url> <login> <parol>" >&2
    echo "Masalan:      $0 http://192.168.1.64 sbozor 'Parol123'" >&2
    exit 1
fi

if ! command -v curl >/dev/null 2>&1; then
    echo "XATO: \`curl\` topilmadi." >&2
    exit 1
fi

BASE_URL="${BASE_URL%/}"
WORKDIR="$(mktemp -d)"
# shellcheck disable=SC2064  # `$WORKDIR` ATAYIN hozir kengaytiriladi
trap "rm -rf '$WORKDIR'" EXIT

# -----------------------------------------------------------------------
# `--digest` MAJBURIY, `--basic` EMAS.
#
# Hikvision ISAPI standart holatda faqat Digest (RFC 7616) ni qabul
# qiladi va `--basic` bilan yuborilgan parol `401` oladi. Bundan ham
# yomoni: `--basic` parolni base64 da OCHIQ yuboradi va u tunneldan
# tashqarida ushlanishi mumkin. `--digest` esa parolni HECH QACHON
# simda yubormaydi.
#
# `--anyauth` ATAYIN ISHLATILMAYDI: u qurilma taklif qilgan ISTALGAN
# sxemaga tushadi, ya'ni firmware Basic taklif qilsa parol ochiq ketardi.
# -----------------------------------------------------------------------
fetch() {
    local path="$1" out="$2"
    curl --silent --show-error \
        --digest --user "$USERNAME:$PASSWORD" \
        --max-time "$TIMEOUT" \
        --insecure \
        --write-out '%{http_code}' \
        --output "$out" \
        "$BASE_URL/ISAPI/$path" 2>"$WORKDIR/err" || echo "000"
}

json_escape() {
    # Backslash -> tirnoq -> boshqaruv belgilari. `sed` ning tartibi
    # AHAMIYATLI: backslash birinchi bo'lmasa qochirilgan tirnoqlar
    # qayta qochiriladi.
    printf '%s' "$1" \
        | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g' \
        | tr -d '\000-\037'
}

probe_endpoint() {
    local name="$1" path="$2"
    local out="$WORKDIR/$name.raw"
    local started ended code bytes
    started="$(date +%s%3N 2>/dev/null || date +%s)"
    code="$(fetch "$path" "$out")"
    ended="$(date +%s%3N 2>/dev/null || date +%s)"
    bytes="$(wc -c <"$out" 2>/dev/null | tr -d ' ')"

    printf '    {\n'
    printf '      "name": "%s",\n' "$(json_escape "$name")"
    printf '      "path": "/ISAPI/%s",\n' "$(json_escape "$path")"
    printf '      "http_code": %s,\n' "${code:-0}"
    printf '      "bytes": %s,\n' "${bytes:-0}"
    printf '      "elapsed_ms": %s,\n' "$((ended - started))"
    printf '      "ok": %s,\n' "$([ "$code" = "200" ] && echo true || echo false)"
    printf '      "saved_as": "%s"\n' "$(json_escape "$out")"
    printf '    }'
}

# -----------------------------------------------------------------------
# Kanal raqamlari `<id>` elementlaridan olinadi.
#
# ⚠ `<InputProxyChannelList size="N">` ATRIBUTIGA ISHONILMAYDI: 03-02
#   `DS-7732NI-M4` dumpida `size="14"` bo'lib, elementlar 18 ta ekanini
#   o'lchagan. Shuning uchun bu yerda ham ELEMENTLAR sanaladi.
# -----------------------------------------------------------------------
channel_ids() {
    local file="$1"
    grep -o '<id>[0-9]\{1,\}</id>' "$file" 2>/dev/null \
        | sed -e 's/<id>//' -e 's|</id>||' \
        | sort -n | uniq
}

printf '{\n'
printf '  "probe": "sbozor/verify-real-nvr",\n'
printf '  "generated_at": "%s",\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
printf '  "base_url": "%s",\n' "$(json_escape "$BASE_URL")"
printf '  "username": "%s",\n' "$(json_escape "$USERNAME")"
printf '  "note": "parol bu faylga YOZILMAYDI; xom javoblar %s da",\n' "$(json_escape "$WORKDIR")"
printf '  "endpoints": [\n'

probe_endpoint "deviceInfo" "System/deviceInfo"
printf ',\n'
probe_endpoint "inputProxyChannels" "ContentMgmt/InputProxy/channels"
printf ',\n'
probe_endpoint "videoInputChannels" "System/Video/inputs/channels"
printf ',\n'
probe_endpoint "adminAccesses" "Security/adminAccesses"
printf ',\n'
probe_endpoint "systemTime" "System/time"
printf '\n  ],\n'

# --- Qurilma pasporti: fixture bilan SOLISHTIRILADIGAN maydonlar ---
DEVICE_FILE="$WORKDIR/deviceInfo.raw"
field() {
    grep -o "<$1>[^<]*</$1>" "$DEVICE_FILE" 2>/dev/null | head -n 1 \
        | sed -e "s/<$1>//" -e "s|</$1>||"
}
printf '  "device": {\n'
printf '    "model": "%s",\n' "$(json_escape "$(field model)")"
printf '    "deviceType": "%s",\n' "$(json_escape "$(field deviceType)")"
printf '    "serialNumber": "%s",\n' "$(json_escape "$(field serialNumber)")"
printf '    "firmwareVersion": "%s",\n' "$(json_escape "$(field firmwareVersion)")"
# ⚠ `manufacturer` ALOHIDA: 03-05 o'lchagan `DS-7732NI-M4` dumpida bu
#   maydon UMUMAN YO'Q va `device_not_supported` sharti aynan shunga
#   tayanadi («maydon BOR va Hikvision emas»). Bo'sh qiymat — TOPILMA.
printf '    "manufacturer": "%s",\n' "$(json_escape "$(field manufacturer)")"
printf '    "manufacturer_present": %s\n' \
    "$([ -n "$(field manufacturer)" ] && echo true || echo false)"
printf '  },\n'

# --- Kanallar ---
CHANNEL_SOURCE="$WORKDIR/inputProxyChannels.raw"
if [ ! -s "$CHANNEL_SOURCE" ]; then
    CHANNEL_SOURCE="$WORKDIR/videoInputChannels.raw"
fi
CHANNELS="$(channel_ids "$CHANNEL_SOURCE" | tr '\n' ' ')"
CHANNEL_COUNT="$(printf '%s' "$CHANNELS" | wc -w | tr -d ' ')"
DECLARED_SIZE="$(grep -o 'size="[0-9]\{1,\}"' "$CHANNEL_SOURCE" 2>/dev/null | head -n 1 \
    | sed -e 's/size="//' -e 's/"//')"

printf '  "channels": {\n'
printf '    "source": "%s",\n' "$(json_escape "$(basename "$CHANNEL_SOURCE" .raw)")"
printf '    "counted": %s,\n' "${CHANNEL_COUNT:-0}"
printf '    "declared_size_attribute": "%s",\n' "$(json_escape "${DECLARED_SIZE:-}")"
# ⚠ MOS KELMASLIK — TOPILMA, XATO EMAS. 03-02 aynan shuni o'lchagan
#   (`size="14"`, elementlar 18 ta) va kashfiyot ELEMENTLARNI sanaydi.
#   Bu maydon farqni JSON'da KO'RINADIGAN qiladi.
printf '    "size_attribute_matches_count": %s,\n' \
    "$([ "${DECLARED_SIZE:-x}" = "${CHANNEL_COUNT:-y}" ] && echo true || echo false)"
printf '    "ids": [%s]\n' "$(printf '%s' "$CHANNELS" | tr ' ' ',' | sed 's/,$//')"
printf '  },\n'

# -----------------------------------------------------------------------
# RTSP porti `adminAccesses` dagi `<protocol>RTSP</protocol>` BLOKIDAN
# olinadi — birinchi uchragan `<portNo>` dan EMAS.
#
# ⚠ Ro'yxatda kamida to'rtta blok bor (HTTP 80, RTSP 554, HTTPS 443,
#   SDK 8000) va ular ixtiyoriy tartibda kelishi mumkin. Birinchi
#   `<portNo>` ni olish `80` ni qaytarardi va zond «RTSP porti 80»
#   deb yozib qo'yardi — mahsulot esa bu qiymatni jonli ko'rish URL'iga
#   qo'yardi.
# -----------------------------------------------------------------------
RTSP_PORT="$(tr -d '\n' <"$WORKDIR/adminAccesses.raw" 2>/dev/null \
    | grep -o '<protocol>RTSP</protocol>[^<]*<portNo>[0-9]\{1,\}</portNo>' \
    | head -n 1 \
    | grep -o '<portNo>[0-9]\{1,\}</portNo>' \
    | sed -e 's/<portNo>//' -e 's|</portNo>||')"
printf '  "rtsp": {\n'
printf '    "port": %s,\n' "${RTSP_PORT:-null}"
printf '    "discovered": %s,\n' "$([ -n "$RTSP_PORT" ] && echo true || echo false)"

# --- Uchta bir vaqtdagi oqim ---
#
# ⚠ TO'LIQ RTSP KLIENTI YOZILMAYDI: `OPTIONS` so'rovi sessiya ochish uchun
#   yetarli va qurilmaning ulanish hisoblagichini aynan shunday oshiradi.
#   `curl` RTSP ni qo'llasa u ishlatiladi; qo'llamasa band `null` bo'ladi va
#   bu HALOL natija — «o'lchanmadi» «ishlamaydi» dan BOSHQA narsa.
#
# ⚠⚠ HAR PID ALOHIDA KUTILADI, ARGUMENTSIZ `wait` BILAN EMAS.
#    POSIX bo'yicha argumentsiz `wait` HAR DOIM `0` qaytaradi — ya'ni
#    `if wait; then OK=true` yozuvi bolalar YIQILGANDA ham `true`
#    berardi. O'LCHANDI: simulyatorda (u 554-portni umuman tinglamaydi)
#    birinchi variant `concurrent_options_ok: true` yozdi, holbuki uchala
#    ulanish ham rad etilgan edi — aynan YOLG'ON-YASHIL.
CONCURRENT_OK="null"
CONCURRENT_FAILED=0
if [ -n "$RTSP_PORT" ] && curl --version 2>/dev/null | grep -q 'rtsp'; then
    RTSP_HOST="${BASE_URL#*://}"
    RTSP_HOST="${RTSP_HOST%%/*}"
    RTSP_HOST="${RTSP_HOST%%:*}"
    pids=""
    index=1
    while [ "$index" -le "$CONCURRENT_STREAMS" ]; do
        curl --silent --output /dev/null --max-time "$TIMEOUT" \
            --request OPTIONS "rtsp://$RTSP_HOST:$RTSP_PORT" \
            >"$WORKDIR/rtsp.$index" 2>&1 &
        pids="$pids $!"
        index=$((index + 1))
    done
    for pid in $pids; do
        wait "$pid" || CONCURRENT_FAILED=$((CONCURRENT_FAILED + 1))
    done
    if [ "$CONCURRENT_FAILED" -eq 0 ]; then CONCURRENT_OK=true; else CONCURRENT_OK=false; fi
fi
printf '    "concurrent_options_ok": %s,\n' "$CONCURRENT_OK"
printf '    "concurrent_failed": %s,\n' "$CONCURRENT_FAILED"
printf '    "concurrent_attempted": %s\n' "$CONCURRENT_STREAMS"
printf '  },\n'

# --- Har kanaldan bitta kadr ---
#
# `image/jpeg` SARLAVHASIGA ISHONILMAYDI — sehrli baytlar tekshiriladi:
# Hikvision xato holatida ham `image/jpeg` bilan XML qaytarishi mumkin.
printf '  "frames": [\n'
first=1
for channel in $CHANNELS; do
    if [ "$first" -eq 0 ]; then printf ',\n'; fi
    first=0
    stream="$((channel * 100 + 1))"
    out="$WORKDIR/frame.$channel.jpg"
    code="$(fetch "Streaming/channels/$stream/picture" "$out")"
    bytes="$(wc -c <"$out" 2>/dev/null | tr -d ' ')"
    magic="$(head -c 3 "$out" 2>/dev/null | od -An -tx1 | tr -d ' \n')"
    printf '    {"channel": %s, "stream_id": %s, "http_code": %s, "bytes": %s, "is_jpeg": %s}' \
        "$channel" "$stream" "${code:-0}" "${bytes:-0}" \
        "$([ "$magic" = "ffd8ff" ] && echo true || echo false)"
    if [ "$channel" -ge "$MAX_CHANNEL_FRAMES" ]; then break; fi
done
printf '\n  ],\n'

printf '  "next_step": "Chiqishni `services/nvr-sim/fixtures/` bilan solishtiring — '
printf 'tartib `ops/docs/nvr-onboarding.md` §4 da. Farq SIM/NING nuqsoni."\n'
printf '}\n'
