# syntax=docker/dockerfile:1

# SBOZOR — KUNLIK ZAXIRA KONTEYNERI (FOUND-07, D-12/D-13).
#
# =============================================================================
# ⛔ BAZA TESKARI TANLANGAN VA BU YAGONA ISHONCHLI YO'L (R-6, Pitfall 7, 8a).
#
# Tabiiy ko'ringan yo'l — `FROM restic/restic:0.19.1` + `apk add
# postgresql18-client` — QURILMAYDI. O'lchangan sabablar:
#
#   * `restic/restic` image'i `alpine:latest` ustida va faqat
#     `ca-certificates fuse openssh-client tzdata jq` o'rnatadi;
#   * `pkgs.alpinelinux.org` bo'yicha `postgresql18-client` FAQAT `edge` da;
#     `v3.22` da eng yangisi `postgresql17-client`;
#   * `pg_dump` ning MAJOR versiyasi serverdan KICHIK bo'lolmaydi —
#     `pg_dump 17` `postgres 18` serverni dump qilishdan RAD ETADI
#     («server version: 18.x; pg_dump version: 17.x — aborting»).
#
# Shuning uchun baza — `db` xizmati bilan AYNAN BIR XIL image, restic esa
# uning ustiga static binar sifatida ko'chiriladi.
#
# ⚠ RUNBOOK BANDI (D-22): Postgres serverini yangilashdan OLDIN shu
#   Dockerfile'ning bazasi yangilanadi. Aks holda birinchi zaxira
#   yugurishi versiya farqi bilan yiqiladi va yurak urishi YOZILMAYDI —
#   ya'ni 26 soatdan keyin `backup_stale` (CRITICAL) ko'tariladi. Bu
#   TO'G'RI xulq: nosozlik jimgina emas, ovoz bilan chiqadi.
# =============================================================================
FROM postgres:18.4-trixie

# =============================================================================
# ⛔ TEG PINLANGAN — `latest` ISHLATILMAYDI (T-08-SC).
#
# Ta'minot zanjiri tekshiruvi (bloklovchi inson tasdig'i, 08-05 Task 1):
#   * Docker Hub tegi `restic/restic:0.19.1` mavjud, `tag_last_pushed`
#     2026-07-05 — 08-RESEARCH § Package Legitimacy Audit bilan mos;
#   * GitHub reliz `v0.19.1` mavjud, litsenziya BSD-2-Clause;
#   * `docker pull` bajarildi, manifest-list digesti
#     `sha256:136600b6ff6843d61d355f7f71f460a166429f35de6fd11b568fece3c9a4d510`,
#     amd64 per-arch digesti
#     `sha256:08916bcda4a4435f9d9828ebb4e91bb7ada3d2c8a53699788930e0ae1bd4fa67`;
#   * `restic version` zondi: `restic 0.19.1 compiled with go1.26.4 on
#     linux/amd64`.
#
# ⚠ A1 FARAZI EMPIRIK O'LCHANDI: `COPY --from` bilan olingan STATIC binar
#   Debian (glibc) bazasida ishlaydi — restic Go bilan statik linklanadi,
#   ya'ni musl↔glibc farqi unga tegmaydi. Farazni tekshirmasdan qoldirish
#   nosozlikni birinchi tunggi yugurishga surib qo'yardi.
#
# ⚠ `ADD https://.../restic_0.19.1_linux_amd64.bz2` FALLBACK'I KERAK
#   BO'LMADI (Task 1): bu muhitda Docker Hub'ga tarmoq bor va image
#   allaqachon lokal mavjud. Fallback'ning o'zi ham yomonroq bo'lardi —
#   `ADD` masofaviy URL uchun digestni tekshirmaydi.
# =============================================================================
COPY --from=restic/restic:0.19.1 /usr/bin/restic /usr/local/bin/restic

COPY ops/backup/ /opt/backup/
RUN chmod +x /opt/backup/*.sh

# =============================================================================
# ⚠ `USER` O'ZGARTIRILMAYDI (root qoladi) — VA BU `core-api` NING
#   `appuser` QARORIDAN (T-01-07) ATAYIN FARQ QILADI.
#
# Sabab bitta va u o'lchanadigan: `seaweed` hajmi `storage` konteyneri
# tomonidan root egaligida yoziladi va bu yerda u `:ro` mount qilinadi.
# Boshqa UID ostida `restic backup /seaweed` dalil kadrlarining bir
# qismini `permission denied` bilan JIMGINA o'tkazib yuborardi — ya'ni
# zaxira «muvaffaqiyatli» bo'lib, arxivning yarmi yo'q bo'lardi.
#
# Konteynerda tarmoq yuzasi YO'Q (`ports:` yozilmagan), kiruvchi so'rov
# yo'q va u faqat compose tarmog'idan chiqadi — ya'ni `core-api` dagi
# hujum yuzasi bu yerda mavjud emas.
# =============================================================================

# ⛔ `CMD` EMAS, `ENTRYPOINT`: `postgres` image'ining O'Z entrypointi
#   (`docker-entrypoint.sh`) initdb/`gosu` mantiqini yuritadi va u shu
#   konteynerda BUTUNLAY o'rinsiz. Uni almashtirmasdan `command:` berish
#   entrypointni «postgres serverini ko'tarish» yo'liga qo'yardi.
ENTRYPOINT ["/opt/backup/loop.sh"]
