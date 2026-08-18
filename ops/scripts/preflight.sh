#!/usr/bin/env sh
# =============================================================================
# DEPLOY OLDI TEKSHIRUVI — «qo'ydik, keyin bilib qoldik» ni to'sadi.
#
# ⛔⛔ NEGA BU SKRIPT BOR (260818).
#
# Deploy'ning nosozlik shakli o'lchangan va u har doim bir xil: stack
# ko'tariladi, `docker compose ps` YASHIL ko'rinadi, lekin bitta-ikkita
# konteyner jimgina restart halqasida aylanadi. Misol — `cv-service`:
# ONNX artefakti bo'lmasa u har ~1 s da qayta ishga tushadi va ~80 % CPU
# yeydi (bu xostda O'LCHANGAN). Sabab faqat `docker compose logs` da
# qoladi va odam u yerga faqat nimadir ishlamaganda qaraydi.
#
# ⛔ Shuning uchun tekshiruv DEPLOYDAN OLDIN va u NO-GO bera oladi.
#
# ⚠ Bu skript HECH NIMANI o'zgartirmaydi va hech nima ishga tushirmaydi —
#   faqat o'qiydi va xulosa aytadi.
#
# Ishlatilishi (repo ildizidan, serverda):
#   sh ops/scripts/preflight.sh
#
# Chiqish kodi: 0 — GO, 1 — NO-GO (kamida bitta blokerli band).
# =============================================================================
set -eu

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

BLOCKERS=0
WARNINGS=0

red()  { printf '  ⛔ %s\n' "$1"; BLOCKERS=$((BLOCKERS + 1)); }
warn() { printf '  ⚠  %s\n' "$1"; WARNINGS=$((WARNINGS + 1)); }
ok()   { printf '  ✓  %s\n' "$1"; }

# Tafsilot qatori — ⛔ U BLOKER SANALMAYDI. Aks holda bitta nuqson uchta
# bo'lib ko'rinardi va yakundagi «N ta bloker» soni YOLG'ON bo'lardi.
detail() { printf '     %s\n' "$1"; }

# `.env` dan qiymat o'qiydi. ⛔ QIYMATNING O'ZI hech qachon chop etilmaydi —
#    bu fayl sirlar bilan to'la va preflight chiqishi jurnалga tushishi mumkin.
envval() {
  [ -f .env ] || return 0
  sed -n "s/^$1=//p" .env | head -n 1
}

# Bo'sh emasligini tekshiradi; ikkinchi argument — nima uchun kerakligi.
need() {
  key="$1"; why="$2"
  val="$(envval "$key")"
  if [ -z "$val" ]; then
    red "$key bo'sh — $why"
  else
    ok "$key to'ldirilgan"
  fi
}

want() {
  key="$1"; why="$2"
  val="$(envval "$key")"
  if [ -z "$val" ]; then
    warn "$key bo'sh — $why"
  else
    ok "$key to'ldirilgan"
  fi
}

echo "=============================================================="
echo " SBOZOR — deploy oldi tekshiruvi"
echo "=============================================================="

# --- 1. `.env` ning o'zi ---------------------------------------------------
echo
echo "1) Konfiguratsiya fayli"
if [ -f .env ]; then
  ok ".env mavjud"
else
  red ".env yo'q — 'cp .env.example .env' qilib to'ldiring"
fi

# --- 1.1. `.env` NAMUNADAN ORQADA QOLMAGANMI --------------------------------
#
# ⛔⛔ NEGA BU BAND BOR (260818, jonli chalkashlikdan keyin).
#
# `.env` odatda BIR MARTA `.env.example` dan nusxa olinadi va keyin
# qo'lda tahrirlanadi. Namunaga yangi kalit qo'shilsa, mavjud `.env` da u
# PAYDO BO'LMAYDI — va yo'q kalit `docker compose` da atigi bitta sariq
# ogohlantirish beradi, uni esa hech kim o'qimaydi.
#
# Aynan shu bo'ldi: `.env` da `TELEGRAM_BOT_TOKEN` qatorining O'ZI yo'q
# edi, foydalanuvchi esa tokenni boshqa kalitning ustiga yozib qo'ydi.
#
# ⚠ Bu OGOHLANTIRISH, bloker EMAS: yetishmayotgan kalitlarning ko'pi
#   standart qiymatga ega va ularsiz ilova ishlaydi. Blokerlilari
#   2-bandda alohida tekshiriladi.
echo
echo "1.1) .env namunadan orqada qolmaganmi"
if [ -f .env ] && [ -f .env.example ]; then
  missing="$(
    awk -F= '/^[A-Z0-9_]+=/ {print $1}' .env.example | sort -u > /tmp/_pf_ex
    awk -F= '/^[A-Z0-9_]+=/ {print $1}' .env         | sort -u > /tmp/_pf_cur
    comm -23 /tmp/_pf_ex /tmp/_pf_cur
  )"
  count="$(printf '%s' "$missing" | grep -c . || true)"
  if [ "$count" = "0" ]; then
    ok ".env namunadagi hamma kalitni o'z ichiga oladi"
  else
    warn "$count ta kalit .env da YO'Q (namunada bor) — qatorning o'zi yo'q, bo'sh emas"
    printf '%s\n' "$missing" | head -n 8 | while read -r k; do
      [ -n "$k" ] && detail "$k"
    done
    [ "$count" -gt 8 ] && detail "... va yana $((count - 8)) ta"
  fi
  rm -f /tmp/_pf_ex /tmp/_pf_cur
fi

# --- 2. Ilova ishga tushishi uchun MAJBURIY qiymatlar -----------------------
#
# Ro'yxat taxmin EMAS: bu maydonlar `Settings` da standart qiymatsiz
# e'lon qilingan, ya'ni bo'sh bo'lsa servis ISHGA TUSHISHDA yiqiladi.
echo
echo "2) Servislar ishga tushishi uchun majburiy"
need DATABASE_URL          "core-api va cv-service ko'tarilmaydi"
need VALKEY_URL            "core-api ko'tarilmaydi (navbat va kesh)"
need JWT_SECRET            "core-api ko'tarilmaydi (sessiyalar)"
need NVR_CREDENTIAL_KEY    "core-api ko'tarilmaydi (RTSP parollari shifri)"
need S3_ACCESS_KEY         "cv-service va worker ko'tarilmaydi (snapshot arxivi)"
need S3_SECRET_KEY         "cv-service va worker ko'tarilmaydi"

# --- 2.1. NAMUNADAN QOLGAN O'RIN TO'LDIRUVCHILAR ----------------------------
#
# ⛔⛔ TO'LDIRILGANDEK KO'RINADI, LEKIN ISHLAMAYDI — eng yomon shakl.
#
# Bo'sh qiymat kamida ovoz chiqaradi (servis ishga tushishda yiqiladi yoki
# yuqoridagi bandlar uni ushlaydi). `CHANGEME` esa BOR: tekshiruvlardan
# o'tadi, konteyner ko'tariladi va nosozlik faqat o'sha qiymat HAQIQATAN
# ishlatilganda — masalan birinchi zaxira nusxasida — chiqadi.
echo
echo "2.1) Namunadan qolgan o'rin to'ldiruvchilar"
if [ -f .env ]; then
  # ⚠ Faqat KALIT nomi chop etiladi, qiymat EMAS.
  stale="$(grep -nE '^[A-Z0-9_]+=.*(CHANGEME|TODO|REPLACE_ME|xxxxx)' .env | cut -d= -f1 | cut -d: -f2 || true)"
  if [ -z "$stale" ]; then
    ok "o'rin to'ldiruvchi qolmagan"
  else
    printf '%s\n' "$stale" | while read -r k; do
      [ -n "$k" ] && printf '  ⛔ %s da namuna qiymati (CHANGEME) qolgan\n' "$k"
    done
    # `while` quyi qobiqda ishlaydi, ya'ni BLOCKERS u yerda oshsa
    # YO'QOLARDI — shuning uchun sanoq bu yerda, tashqarida oshiriladi.
    BLOCKERS=$((BLOCKERS + $(printf '%s\n' "$stale" | grep -c .)))
  fi
fi

# --- 3. Production'ga XOS majburiy qiymatlar --------------------------------
echo
echo "3) Production uchun majburiy"
need PUBLIC_DOMAIN "nginx shabloni envsubst da yiqiladi va TLS sertifikati topilmaydi"

# --- 4. ONNX artefakti — CV yarmi ------------------------------------------
#
# ⛔ Bu ALOHIDA band va u bloker, chunki uning yo'qligi JIM emas, QIMMAT:
#    konteyner restart halqasida protsessorni yeydi.
echo
echo "4) CV artefakti"
MODEL="ops/models/rfdetr-large.onnx"
if [ -f "$MODEL" ]; then
  ok "$MODEL mavjud"
elif [ "${ALLOW_NO_CV:-0}" = "1" ]; then
  warn "$MODEL YO'Q, lekin ALLOW_NO_CV=1 berilgan — cv-service SIZ ishga tushirmaysiz"
  detail "⛔ Bandlik o'lchanmaydi: «band, lekin to'lovsiz» hisoboti DOIM NOL bo'ladi"
  detail "Ko'tarmaslik uchun: docker compose ... up -d --scale cv-service=0"
else
  red "$MODEL yo'q — cv-service restart halqasiga tushadi (~80% CPU, o'lchangan)"
  detail "Eksport retsepti: ops/models/README.md"
  detail "CV'siz ONGLI chiqish: ALLOW_NO_CV=1 sh ops/scripts/preflight.sh"
fi

# --- 5. TLS sertifikati -----------------------------------------------------
echo
echo "5) TLS"
DOMAIN="$(envval PUBLIC_DOMAIN)"
if [ -n "$DOMAIN" ] && [ -d "ops/certbot/conf/live/$DOMAIN" ]; then
  ok "sertifikat mavjud ($DOMAIN)"
else
  # ⚠ Bu OGOHLANTIRISH, bloker emas: birinchi deployda sertifikat
  #   bo'lmasligi NORMAL — uni `first-cert.sh` oladi. Bloker qilinsa,
  #   birinchi deploy hech qachon boshlanmasdi.
  warn "sertifikat yo'q — avval: PUBLIC_DOMAIN=... CERT_EMAIL=... sh ops/scripts/first-cert.sh"
fi

# --- 6. Zaxira nusxa --------------------------------------------------------
#
# ⚠ Bu ATAYIN bloker EMAS, lekin ATAYIN ovoz chiqaradi: zaxirasiz chiqish
#   mumkin, faqat u ONGLI qaror bo'lsin. Bu eng jim yo'qotish turi —
#   hamma narsa ishlab turadi va nosozlik faqat baza yo'qolganda bilinadi.
echo
echo "6) Zaxira nusxa"
want RESTIC_REPOSITORY "offsite zaxira YO'Q — birinchi kundan tiklash imkoni bo'lmaydi"
want RESTIC_PASSWORD   "zaxira shifri sozlanmagan"

# --- 7. Kuzatuv -------------------------------------------------------------
echo
echo "7) Kuzatuv"
want SENTRY_DSN          "xatolar hech qayerga bormaydi"
want TELEGRAM_BOT_TOKEN  "botlar ishlamaydi va alertlar yuborilmaydi"
want TELEGRAM_CHAT_ID    "alertlar boradigan chat ko'rsatilmagan"

# --- 8. Compose konfiguratsiyasi haqiqatan yig'iladimi ----------------------
echo
echo "8) Compose"
if [ -n "$DOMAIN" ]; then
  if PUBLIC_DOMAIN="$DOMAIN" docker compose -f compose.yaml -f compose.prod.yml \
       --profile proxy config >/dev/null 2>&1; then
    ok "prod konfiguratsiyasi yig'iladi"

    # ⛔ 8080 PORTI TEKSHIRUVI — `ports: !override` ishlayotganini
    #    HAQIQIY chiqishdan o'lchaydi, yozilganiga ishonmaydi.
    published="$(PUBLIC_DOMAIN="$DOMAIN" docker compose -f compose.yaml -f compose.prod.yml \
       --profile proxy config 2>/dev/null | grep -c 'published: "8080"' || true)"
    if [ "$published" = "0" ]; then
      ok "8080 porti prod'da OCHILMAYDI"
    else
      red "8080 porti prod'da ochiq qolyapti — TLS'ni chetlab o'tuvchi ikkinchi eshik"
    fi
  else
    red "prod konfiguratsiyasi yig'ilmadi — buyruqni qo'lda yurgizib xatoni o'qing"
  fi
else
  warn "PUBLIC_DOMAIN bo'sh — compose tekshiruvi o'tkazilmadi"
fi

# --- Xulosa -----------------------------------------------------------------
echo
echo "=============================================================="
if [ "$BLOCKERS" -gt 0 ]; then
  echo " NATIJA: NO-GO — $BLOCKERS ta bloker, $WARNINGS ta ogohlantirish"
  echo "=============================================================="
  exit 1
fi
echo " NATIJA: GO — $WARNINGS ta ogohlantirish"
echo "=============================================================="
exit 0
