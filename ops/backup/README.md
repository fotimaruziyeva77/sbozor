# Kunlik zaxira — Postgres + dalil arxivi, offsite (FOUND-07)

`backup` konteyneri kuniga bir marta ikki narsani offsite `restic`
repo'siga yozadi: **butun Postgres bazasi** va **`seaweed` hajmidagi
dalil kadrlari**. Uchinchi ishi — muvaffaqiyatdan keyin
`system_heartbeats['backup']` qatorini yangilash.

> ⛔ **SAKKIZINCHI KONTEYNER, TO'RTINCHI SERVIS EMAS.** U `db`, `cache`,
> `storage`, `go2rtc`, `nginx` bilan bir toifa — tayyor image ustidagi ops
> skripti, bizning uchinchi mikroservisimiz emas. CLAUDE.md ning «aynan
> 3 ta servis» cheklovi buzilmaydi.

---

## 1. Nima o'lchanadi va nima O'LCHANMAYDI

| Da'vo | Qayerda o'lchanadi |
|-------|--------------------|
| Skript zanjirida quvur yo'q, `-Z0` bor, retention qiymatlari literal | `tests/unit/test_backup_contract.py` (statik) |
| Yurak urishi zanjirning ENG OXIRGI qadami va `trap` ichida emas | `tests/unit/test_backup_contract.py` (statik) |
| Komponent nomi `alerting.BACKUP_COMPONENT` bilan bir xil | `tests/unit/test_backup_contract.py` (import bilan) |
| Compose blokida sir literal emas, `:ro` mount bor | `tests/unit/test_backup_contract.py` (statik) |
| Yurak urishining YO'QLIGI alert beradi (`backup_stale`) | `alerting.py` + `tests/unit/test_heartbeat_registry.py` |
| Dump toza serverga tiklanadi, ma'lumot joyida | `tests/integration/test_restore_drill.py` (08-08) |

> ⛔ **«OFFSITE REPODAN TIKLASH» CI'DA O'LCHANMAYDI VA O'LCHANMAYDI HAM.**
> CI konteynerida offsite rekvizitlar yo'q, `restic` binari `tests`
> image'ida yo'q va sinov tiklashi haqiqiy trafik talab qiladi. Bu band
> **`08-HUMAN-UAT.md`** da, egasi **Ops**, va u go-live checklist'ining
> bloklovchi bandi. CI qatlami faqat «dump → toza server → ma'lumot
> joyida» zanjirini o'lchaydi (D-16).

---

## 2. Besh muhit o'zgaruvchisi

| Kalit | Manba | Izoh |
|-------|-------|------|
| `BACKUP_DATABASE_URL` | `.env` | ⛔ **libpq shakli** — `postgresql://user:pass@db:5432/sbozor` |
| `RESTIC_REPOSITORY` | offsite provayder | `s3:https://<endpoint>/<bucket>/<path>` |
| `RESTIC_PASSWORD` | yangi generatsiya | ⛔ quyidagi §3 ga qarang |
| `BACKUP_S3_ACCESS_KEY` | offsite konsoli → Application keys | konteynerga `AWS_ACCESS_KEY_ID` bo'lib kiradi |
| `BACKUP_S3_SECRET_KEY` | offsite konsoli → Application keys | konteynerga `AWS_SECRET_ACCESS_KEY` bo'lib kiradi |

### ⛔ `DATABASE_URL` ISHLATILMAYDI

`.env` dagi `DATABASE_URL` — `postgresql+asyncpg://…`, ya'ni **SQLAlchemy
dialekti**. `psql` va `pg_dump` uni `invalid URI scheme` bilan **rad
etadi**. `sed` bilan konvertatsiya qilish ham **rad etilgan**: bir joyda
ikki haqiqat manbai bo'lardi va parol o'zgarganda biri jimgina eskirardi.

### ⛔ OFFSITE REKVIZITLAR LOKAL SeaweedFS NIKI EMAS

`S3_ACCESS_KEY` / `S3_SECRET_KEY` — bu **lokal** `storage` konteynerining
kalitlari. Ularni bu yerga qo'yish zaxirani **o'sha VPS'ning o'sha
diskiga** yozardi, ya'ni bitta diskning o'limi ham bazani, ham arxivni,
ham zaxirani birdan olib ketardi. FOUND-07 ning «boshqa lokatsiya»
talabi aynan shuni taqiqlaydi (D-14): offsite **boshqa failure domain**
bo'lishi shart — Backblaze B2 yoki ikkinchi Contabo regioni.

### Ixtiyoriy sozlamalar

| Kalit | Standart | Ma'nosi |
|-------|----------|---------|
| `BACKUP_RUN_AFTER` | `04:40` | Kunlik yugurishning eng erta vaqti (Asia/Tashkent) |
| `BACKUP_POLL_SECONDS` | `600` | Tsikl qadamining uzunligi |

**Nega 04:40:** `retention` (03:20) obyektlarni **joyida qayta yozadi**,
`day_close` (03:40) va `billing_close` (04:10) kunni yopadi. 04:40
uchalasidan keyin, ya'ni dump kechagi kunning **yopilgan** hisobini o'z
ichiga oladi; kadr olish oynasi (06:00–08:00, 16:00, 18:00) esa hali
boshlanmagan.

---

## 3. ⛔⛔ `RESTIC_PASSWORD` — yo'qolsa zaxira BUTUNLAY tiklanmaydi

restic repo'si **har doim shifrlangan** (AES-256 + Poly1305) va uni
ochadigan yagona narsa — shu parol. **Parolni tiklash yo'li YO'Q.**

Ya'ni:

> Parol faqat VPS'ning `.env` ida bo'lsa va VPS o'lsa — **zaxira ham
> o'ladi**. Bu FOUND-07 ni bajarilmagan holatga qaytaradi va buni faqat
> falokat kuni bilib olinadi.

Shuning uchun **majburiy** qoida:

1. Parol **serverdan tashqarida**, **ikki** joyda saqlanadi — parol
   menejeri **va** qog'oz/seyf;
2. Uni **ikki odam** biladi;
3. Ikkala band ham `08-HUMAN-UAT.md` da **imzolanadi** (tekshirish mumkin
   bo'lgan band, «shunday qilamiz» degan niyat emas).

Hosil qilish:

```bash
python -c "import secrets;print(secrets.token_urlsafe(48))"
```

> ⚠ Bu parol `NVR_CREDENTIAL_KEY` bilan **bir toifada**: uni yo'qotish
> ma'lumotni qaytarib bo'lmas qiladi. `JWT_SECRET` esa boshqa toifada —
> uni almashtirsangiz sessiyalar tushadi va hammasi o'z-o'zidan tuzaladi.

---

## 4. Birinchi ishga tushirish

```bash
cp deployment/.env.example deployment/.env          # va besh kalitni to'ldiring
docker compose -f deployment/compose.yaml -f deployment/compose.prod.yml build backup
docker compose -f deployment/compose.yaml -f deployment/compose.prod.yml up -d backup
docker compose -f deployment/compose.yaml -f deployment/compose.prod.yml logs -f backup
```

Repo **avtomatik** yaratiladi: skript `restic cat config` bilan tekshiradi
va faqat topilmasa `restic init` chaqiradi. (`init` ni har safar chaqirish
mavjud repoda **xato** beradi va `set -e` ostida zanjirni birinchi qadamda
o'ldirardi.)

Kunni kutmasdan qo'lda bir marta yugurtirish:

```bash
docker compose -f deployment/compose.yaml -f deployment/compose.prod.yml exec backup /opt/backup/run-backup.sh
```

Natijani tekshirish:

```bash
docker compose -f deployment/compose.yaml -f deployment/compose.prod.yml exec backup restic snapshots
docker compose -f deployment/compose.yaml -f deployment/compose.prod.yml exec db psql -U postgres -d sbozor \
  -c "SELECT component, last_seen_at, detail FROM system_heartbeats WHERE component = 'backup'"
```

---

## 5. Sozlanmagan zaxira JIM QOLMAYDI

Beshta kalit to'ldirilmagan bo'lsa konteyner **chiqmaydi** va
**crash-loop ham qilmaydi** — u har qadamda `stderr` ga
`backup_unconfigured` yozadi, zaxirani **boshlamaydi** va yurak urishini
**yozmaydi**.

Natija: 26 soatdan keyin `alert_sweep` **`backup_stale`** (CRITICAL,
`never_suppressed`) ni ko'taradi va u Telegram'ga chiqadi.

> Bu **to'g'ri xulq**, kamchilik emas: sozlanmagan zaxira — mavjud
> bo'lmagan zaxira, va tizim buni **o'zi** ko'rishi kerak. `exit 1` esa
> `restart: unless-stopped` bilan crash-loop bo'lardi va dev muhitida
> `npm run up` jurnalini ifloslantirardi; jim ishlab «muvaffaqiyat»
> yozish esa D-15 ning butun ma'nosini yo'q qilardi.

---

## 6. Nega baza `postgres:18.4-trixie`, restic esa `COPY --from`

Tabiiy ko'ringan yo'l — `FROM restic/restic` + `apk add
postgresql18-client` — **qurilmaydi**:

| Fakt | Oqibat |
|------|--------|
| `restic/restic` image'i `alpine:latest` ustida | `apk` mavjud, lekin… |
| Alpine `v3.22` da eng yangisi `postgresql17-client` (`postgresql18-client` faqat `edge` da) | `apk add` **`unable to select packages`** beradi |
| `pg_dump` MAJOR versiyasi serverdan kichik bo'lolmaydi | `pg_dump 17` `postgres 18` ni **rad etadi** |

Shuning uchun baza teskari qilingan: **`db` bilan aynan bir xil image** +
restic **static binari** ustiga (`COPY --from=restic/restic:0.19.1`).
Litsenziya: restic — **BSD-2-Clause**, teg **pinlangan** (`latest`
ishlatilmaydi, T-08-SC).

> ⛔ **RUNBOOK BANDI:** Postgres serverini yangilashdan **oldin** shu
> Dockerfile'ning bazasini yangilang. Aks holda birinchi tunggi yugurish
> versiya farqi bilan yiqiladi — ovoz bilan (`backup_stale`), lekin bir
> kunlik zaxira yo'qotib.

---

## 7. Haftalik butunlik tekshiruvi

Yakshanba 05:30 dan keyin tsikl `restic check --read-data-subset=5%` ni
chaqiradi.

> ⛔ **Uning nosozligi yurak urishini O'CHIRMAYDI** va bu ongli qaror: u
> zaxira **olishning** emas, repo **butunligining** nosozligi. Ikkalasini
> bitta signalga yig'ish bugungi muvaffaqiyatli zaxira ustida ham
> «zaxira ishlamayapti» deb qichqirardi. Bugun u `stderr` ga chiqadi va
> Ops ko'radi; alohida alert kaliti — **V2** (yangi kalit
> `ALERT_TITLE_KEY_COUNT` qulfini qizartiradi va uch tilli matn talab
> qiladi).
