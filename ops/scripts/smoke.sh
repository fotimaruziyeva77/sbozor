#!/usr/bin/env sh
# =============================================================================
# DEPLOYDAN KEYINGI TEKSHIRUV — tashqaridan, brauzer ko'radigan tomondan.
#
# ⛔⛔ NEGA `preflight.sh` YETMAYDI.
#
# `preflight` deploydan OLDIN konfiguratsiyani o'qiydi — u niyatni
# tekshiradi. Bu skript esa NATIJANI o'lchaydi: domen javob beryaptimi,
# HTTPS ishlayaptimi, xavfsizlik taqiqlari HAQIQATAN kuchdami.
#
# ⛔ Farq muhim: `docker compose ps` «yashil» deyishi mumkin, lekin nginx
#    noto'g'ri `server_name` bilan ko'tarilgan bo'lsa yoki sertifikat
#    boshqa domenga tegishli bo'lsa, foydalanuvchi hech narsa ko'rmaydi.
#    Ichkaridan bu KO'RINMAYDI.
#
# Ishlatilishi (istalgan mashinadan — server SHART EMAS):
#   sh ops/scripts/smoke.sh demo.sbozor.uz
#   sh ops/scripts/smoke.sh            # domen `.env` dagi PUBLIC_DOMAIN dan
#
# Chiqish kodi: 0 — hammasi o'tdi, 1 — kamida bitta nuqson.
# =============================================================================
set -eu

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

DOMAIN="${1:-}"
if [ -z "$DOMAIN" ] && [ -f .env ]; then
  DOMAIN="$(sed -n 's/^PUBLIC_DOMAIN=//p' .env | head -n 1)"
fi
if [ -z "$DOMAIN" ]; then
  echo "⛔ Domen berilmadi. Ishlatilishi: sh ops/scripts/smoke.sh demo.sbozor.uz"
  exit 2
fi

FAILED=0

ok()   { printf '  ✓  %s\n' "$1"; }
bad()  { printf '  ⛔ %s\n' "$1"; FAILED=$((FAILED + 1)); }

# HTTP status kodini qaytaradi. ⛔ `--max-time` MAJBURIY: javob bermaydigan
#    domen skriptni abadiy osib qo'yardi va u «tekshirilmadi» emas,
#    «tekshirilyapti» bo'lib ko'rinardi.
# ⛔ `|| echo "000"` YOZILMAYDI: curl nosozlikda `%{http_code}` ni
#    ALLAQACHON `000` deb chiqaradi va zaxira shox uning USTIGA yana
#    `000` qo'shib `000000` berardi — o'shanda hamma shart `*` shoxiga
#    tushib, sabab «kutilmagan javob» bo'lib ko'rinardi (o'lchandi).
code() {
  curl -s -o /dev/null -w '%{http_code}' --max-time 15 "$@" 2>/dev/null || true
}

echo "=============================================================="
echo " SBOZOR — deploydan keyingi tekshiruv: $DOMAIN"
echo "=============================================================="

# --- 1. HTTP -> HTTPS yo'naltirish ------------------------------------------
#
# ⛔ `-L` BERILMAYDI: bu yerda tekshirilayotgan narsa AYNAN yo'naltirishning
#    o'zi. `-L` bilan curl uni jimgina bajarardi va 301 ko'rinmasdi.
echo
echo "1) HTTP -> HTTPS"
http_code="$(code "http://$DOMAIN/")"
case "$http_code" in
  301|302|307|308) ok "HTTP $http_code bilan yo'naltiryapti" ;;
  000)             bad "HTTP javob bermadi — DNS yoki 80-port yopiq" ;;
  200)             bad "HTTP 200 qaytardi — yo'naltirish YO'Q, sayt shifrsiz ochiq" ;;
  *)               bad "HTTP kutilmagan javob: $http_code" ;;
esac

# --- 2. HTTPS ishlayaptimi --------------------------------------------------
echo
echo "2) HTTPS"
https_code="$(code "https://$DOMAIN/")"
if [ "$https_code" = "200" ]; then
  ok "landing 200 qaytardi"
elif [ "$https_code" = "000" ]; then
  bad "HTTPS javob bermadi — sertifikat yoki 443-port muammosi"
else
  bad "HTTPS kutilmagan javob: $https_code"
fi

# --- 3. Uch til -------------------------------------------------------------
#
# ⚠ Uchalasi ALOHIDA tekshiriladi: `next-intl` marshrutlari SSG bo'lib
#   quriladi va bittasi build'dan tushib qolsa qolgani ishlayveradi.
echo
echo "3) Uch til"
for loc in uz uz-cyrl ru; do
  c="$(code "https://$DOMAIN/$loc/login")"
  if [ "$c" = "200" ]; then ok "/$loc/login → 200"; else bad "/$loc/login → $c"; fi
done

# --- 4. API tirikmi ---------------------------------------------------------
echo
echo "4) API"
api_code="$(code "https://$DOMAIN/api/v1/markets")"
# 401 ham SOG'LOM javob: API tirik va himoyalangan. 200 ham bo'lishi mumkin.
case "$api_code" in
  200|401|403) ok "API javob beryapti ($api_code)" ;;
  000)         bad "API javob bermadi" ;;
  502|503|504) bad "API $api_code — core-api ko'tarilmagan yoki yiqilgan" ;;
  *)           bad "API kutilmagan javob: $api_code" ;;
esac

# --- 5. ⛔ XAVFSIZLIK: go2rtc API'si TASHQARIDAN YOPIQmi ---------------------
#
# ⛔⛔ ENG QIMMAT TEKSHIRUV. go2rtc ning `PUT /api/streams?src=exec:...`
#     yuzasi IXTIYORIY BUYRUQ BAJARADI (GHSA-wwww-5h25-jf98, CVSS 9.1).
#     nginx uni ikki qatlamda to'sadi va bu yerda o'sha to'siq
#     TASHQARIDAN o'lchanadi — konfiguratsiyada yozilganiga ishonilmaydi.
echo
echo "5) Xavfsizlik — go2rtc API taqiqi"
for path in "api/streams" "api/config" "api/restart" "live/api/streams"; do
  c="$(code "https://$DOMAIN/$path")"
  if [ "$c" = "403" ] || [ "$c" = "404" ]; then
    ok "/$path → $c (yopiq)"
  elif [ "$c" = "000" ]; then
    # ⛔ JAVOB KELMAGANI «YOPIQ» DEGANI EMAS va «OCHIQ» degani ham EMAS.
    #    Birinchi versiyada bu «OCHIQ QOLGAN» deb yozilardi — ya'ni butun
    #    sayt o'chib qolganda skript XAVFSIZLIK buzilgan deb ayblardi va
    #    haqiqiy sabab ko'rinmasdi.
    bad "/$path → javob kelmadi (sayt umuman ochilmayapti — 2-bandga qarang)"
  else
    bad "/$path → $c — OCHIQ QOLGAN, bu masofadan buyruq bajarish yo'li"
  fi
done

# --- 6. ⛔ 8080 porti tashqaridan yopiqmi ------------------------------------
#
# `compose.prod.yml` da `ports: !override` bor, lekin bu yerda uning
# NATIJASI o'lchanadi: dev porti ochiq qolsa, u TLS'ni, HSTS'ni va
# yo'naltirishni chetlab o'tadigan ikkinchi eshik bo'lardi.
echo
echo "6) 8080 porti"
p8080="$(code "http://$DOMAIN:8080/")"
if [ "$p8080" = "000" ]; then
  ok "8080 tashqaridan yopiq"
else
  bad "8080 javob berdi ($p8080) — TLS'ni chetlab o'tuvchi ikkinchi eshik"
fi

# --- 7. Sertifikat muddati --------------------------------------------------
echo
echo "7) Sertifikat"
if command -v openssl >/dev/null 2>&1; then
  end="$(echo | openssl s_client -servername "$DOMAIN" -connect "$DOMAIN:443" 2>/dev/null \
        | openssl x509 -noout -enddate 2>/dev/null | sed 's/notAfter=//')"
  if [ -n "$end" ]; then
    ok "amal qilish muddati: $end"
  else
    bad "sertifikat o'qilmadi"
  fi
else
  printf '     openssl yo\x27q — muddat tekshirilmadi\n'
fi

# --- Xulosa -----------------------------------------------------------------
echo
echo "=============================================================="
if [ "$FAILED" -gt 0 ]; then
  echo " NATIJA: $FAILED ta nuqson"
  echo "=============================================================="
  exit 1
fi
echo " NATIJA: hammasi o'tdi"
echo "=============================================================="
exit 0
