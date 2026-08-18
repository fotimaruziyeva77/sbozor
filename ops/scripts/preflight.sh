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
