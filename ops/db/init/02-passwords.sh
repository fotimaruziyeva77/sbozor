#!/bin/sh
# SBOZOR — rol parollarini muhit o'zgaruvchilaridan o'rnatadi.
#
# Parollar HECH QACHON repoda saqlanmaydi — ular faqat `.env` orqali keladi.
# `01-roles.sql` rollarni parolsiz yaratadi; bu skript ularga parol beradi.
#
# psql `-v` + `:'var'` — qiymat SQL literali sifatida to'g'ri qochiriladi
# (parolga qo'shtirnoq tushsa ham injection bo'lmaydi).

set -e

if [ -z "${SBOZOR_OWNER_PASSWORD}" ]; then
    echo "XATO: SBOZOR_OWNER_PASSWORD o'rnatilmagan. \`cp .env.example .env\` qiling va qiymat bering." >&2
    exit 1
fi

if [ -z "${SBOZOR_APP_PASSWORD}" ]; then
    echo "XATO: SBOZOR_APP_PASSWORD o'rnatilmagan. \`cp .env.example .env\` qiling va qiymat bering." >&2
    exit 1
fi

psql -v ON_ERROR_STOP=1 \
     --username "${POSTGRES_USER}" \
     --dbname "${POSTGRES_DB}" \
     -v owner_pw="${SBOZOR_OWNER_PASSWORD}" \
     -v app_pw="${SBOZOR_APP_PASSWORD}" <<'EOSQL'
ALTER ROLE sbozor_owner PASSWORD :'owner_pw';
ALTER ROLE sbozor_app   PASSWORD :'app_pw';
EOSQL
