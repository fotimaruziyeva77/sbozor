#!/usr/bin/env sh
# =============================================================================
# BIRINCHI SERTIFIKATNI OLISH — faqat BIR MARTA, deploy'ning eng boshida.
#
# ⛔ MUAMMO: production nginx konfiguratsiyasi `ssl_certificate` ga ishora
#    qiladi. Sertifikat hali yo'q bo'lsa nginx UMUMAN ko'tarilmaydi, ya'ni
#    ACME tekshiruvini o'tkazadigan server ham yo'q — tovuq va tuxum.
#
# ⛔ YECHIM: bu skript vaqtinchalik, TLS'siz nginx ko'taradi (faqat ACME
#    yo'li), certbot'ni ishga tushiradi, so'ng o'zini o'chiradi. Shundan
#    keyin to'liq stack normal ko'tariladi.
#
# Ishlatilishi (repo ildizidan, serverda):
#   PUBLIC_DOMAIN=demo.sbozor.uz CERT_EMAIL=siz@example.com sh ops/scripts/first-cert.sh
# =============================================================================
set -eu

: "${PUBLIC_DOMAIN:?PUBLIC_DOMAIN kerak — masalan demo.sbozor.uz}"
: "${CERT_EMAIL:?CERT_EMAIL kerak — Let's Encrypt ogohlantirishlari uchun}"

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
mkdir -p "$ROOT/ops/certbot/www" "$ROOT/ops/certbot/conf"

# ⛔ Sertifikat allaqachon bor bo'lsa — HECH NIMA qilinmaydi. Let's Encrypt
#    haftasiga 5 marta bir xil domen uchun so'rovni bloklaydi; takroriy
#    ishga tushirish shu limitni yeb qo'yardi.
if [ -d "$ROOT/ops/certbot/conf/live/$PUBLIC_DOMAIN" ]; then
  echo "Sertifikat allaqachon bor: $PUBLIC_DOMAIN — hech nima qilinmadi."
  exit 0
fi

echo "1/3 · ACME uchun vaqtinchalik nginx ko'tarilmoqda…"
docker run --rm -d --name sbozor-acme \
  -p 80:80 \
  -v "$ROOT/ops/certbot/www:/var/www/certbot:ro" \
  -v "$ROOT/ops/nginx/acme-only.conf:/etc/nginx/conf.d/default.conf:ro" \
  nginx:1.30.4-alpine

# Konteyner yiqilsa ham porti bo'shashi uchun.
trap 'docker rm -f sbozor-acme >/dev/null 2>&1 || true' EXIT

echo "2/3 · Sertifikat so'ralmoqda ($PUBLIC_DOMAIN)…"
docker run --rm \
  -v "$ROOT/ops/certbot/conf:/etc/letsencrypt" \
  -v "$ROOT/ops/certbot/www:/var/www/certbot" \
  certbot/certbot:latest certonly \
  --webroot -w /var/www/certbot \
  -d "$PUBLIC_DOMAIN" \
  --email "$CERT_EMAIL" \
  --agree-tos --no-eff-email --non-interactive

echo "3/3 · Vaqtinchalik nginx to'xtatilmoqda…"
docker rm -f sbozor-acme >/dev/null

echo "Tayyor. Endi:"
echo "  docker compose -f compose.yaml -f compose.prod.yml --profile proxy up -d"
