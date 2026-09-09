# Go-live runbook — deploy, birinchi zaxira, cutover va rollback (FOUND-07, D-12..D-16, D-22, SC#3, SC#4)

> ⛔ **Bu hujjat darvoza EMAS.** U operatsion **tartib**: qaysi buyruq
> qaysi navbatda yuguradi va har birining **kutilgan natijasi** nima.
> Kodning darvozalari boshqa joyda va ular bu faylni **o'qimaydi**:
>
> | Darvoza | Nimani qulflaydi |
> |---------|------------------|
> | `tests/unit/test_backup_contract.py` | Zaxira skriptining shakli: quvursiz zanjir, `-Z0`, retention qiymatlari, yurak urishining o'rni |
> | `tests/integration/test_backup_heartbeat.py` | Yurak urishi -> `/internal/self-check` -> `backup_stale` zanjiri |
> | `tests/integration/test_restore_drill.py` | Dump -> toza `postgres:18.4-trixie` -> ma'lumot joyida (D-16a) |
> | `tests/unit/test_runbook_shape.py` | ⚠ SHU FAYLNING SHAKLI: har buyruq bloki kutilgan natija bilan juft |
>
> ⚠ **Shakl qoidasi bitta va u mexanik:** har bir buyruq bloki ostida
> darhol `**Kutilgan natija:**` qatori turadi. Natijasiz buyruq bandi bu
> faylga **kirmaydi** — uni `test_runbook_shape.py` qaytarib yuboradi.

---

## 0. Bir jumlada

**Deploy — kod yangilash emas, TARTIB:** migratsiya ilova ishga
tushishidan **oldin**, planer koddan **keyin** qayta yaratiladi, zaxira
esa birinchi tunni **kutmasdan** bir marta qo'lda yugurtiriladi — chunki
uch nosozlikning uchalasi ham **jim**: eski jadval bilan yuguruvchi
planer xato bermaydi, sozlanmagan zaxira xato bermaydi, tiklanmaydigan
repo esa faqat **falokat kuni** ovoz beradi.

⛔ **Ushbu runbookdagi hech bir band «keyin bajaramiz» ga
qoldirilmaydi.** Go-live oldi ro'yxati (§9) — imzolanadigan hujjat;
imzosiz band **bajarilmagan** band.

---

## 1. VPS deploy tartibi (D-13)

### 1.1 Kodni yangilash

```bash
cd /opt/sbozor
git pull --ff-only origin main
```

**Kutilgan natija:** `Fast-forward` yoki `Already up to date.`
⛔ `--ff-only` MAJBURIY: merge commiti serverda tug'ilsa keyingi
`git pull` konfliktga tushadi va deploy yarim holatda qoladi. Xato
`Not possible to fast-forward` bo'lsa — serverda lokal commit bor,
uni §8 dagi rollback tartibi bilan hal qiling.

### 1.2 Image'larni qurish

```bash
docker compose -f deployment/compose.yaml -f deployment/compose.prod.yml build core-api worker scheduler cv-service bot-service backup
docker compose -f deployment/compose.yaml -f deployment/compose.prod.yml --profile web build frontend
```

**Kutilgan natija:** har bir servis uchun `Built` qatori; xatosiz exit 0.
⚠ `frontend` va `nginx` **profil ortida** (`web` / `proxy`), ya'ni
profilsiz `docker compose build` ularni **qurmaydi** — shuning uchun
ikkinchi qator alohida.

### 1.3 Migratsiya — ilovadan OLDIN

```bash
npm run migrate
```

**Kutilgan natija:** `Running upgrade <eski> -> <yangi>` qatorlari va
exit 0. Buyruq `docker compose --profile migrate run --rm migrate
alembic upgrade head` ga yoyiladi — ya'ni bir martalik ish, ilova
startupida Alembic **yugurmaydi**.
⛔ Migratsiya yiqilsa keyingi qadamga **o'tilmaydi**: eski kod yangi
sxemada, yoki yangi kod eski sxemada ishlashi hech qayerda o'lchanmagan.

### 1.4 ⛔ `npm run up` — QO'LDA TASDIQLANADIGAN BAND

Bu band 07-fazaning `deferred-items.md` №5 ining **ochiq qolgan**
qismidir: `scripts.up` ro'yxati to'g'rilangan va uning har bir servisi
`compose.yaml` da mavjudligi `tests/unit/test_dev_environment.py` bilan
qulflangan, lekin buyruqning **O'ZI** hech qachon uchidan-uchiga
yugurtirilmagan.

```bash
npm run up
```

**Kutilgan natija:** exit 0 va `--wait` tufayli buyruq faqat konteynerlar
sog'lom bo'lgandan keyin qaytadi.

```bash
docker compose -f deployment/compose.yaml -f deployment/compose.prod.yml ps --format 'table {{.Service}}\t{{.State}}\t{{.Status}}'
```

**Kutilgan natija:** ⛔ **o'nta** qator `running` holatida —
`db`, `cache`, `storage`, `core-api`, `worker`, `scheduler`,
`cv-service`, `bot-service`, `go2rtc`, `backup`. Kamroq qator chiqsa
`scripts.up` ro'yxati mahsulot to'plamidan **ajralgan** va bu
`deferred-items.md` №5 ning aynan takroridir.

### 1.5 Yuza qatlam (profil ortidagi ikkitasi)

```bash
docker compose -f deployment/compose.yaml -f deployment/compose.prod.yml --profile web --profile proxy up -d frontend nginx --wait
```

**Kutilgan natija:** `frontend` va `nginx` `running`; `curl -sS -o
/dev/null -w '%{http_code}' https://<domen>/uz` **200** qaytaradi.

> ⛔ **HALOL CHEGARA (§1).** Bu bo'lim jarayonlarning **ko'tarilganini**
> beradi, «tizim to'g'ri ishlayapti» ni **EMAS**. Birinchisi
> `docker compose ps` bilan o'lchanadi; ikkinchisining yagona manbai —
> `system_heartbeats` va `/internal/self-check` (§2.2), hamda go-live
> oldi ro'yxatidagi inson bandlari (§9).

---

## 2. Qaysi konteyner qayta yaratiladi

### 2.1 ⛔ Cron jadvali IMPORT paytida olinadi

`scheduler` konteyneri jadvalni `LabelScheduleSource` orqali
`app/worker.py` ning **import paytida** o'qiydi. Ya'ni `worker.py` ga
tegilgan har qanday deploy'da planer **qayta yaratilishi SHART** —
aks holda u eski jadval bilan yuguradi va ⛔ **hech qanday xato
chiqmaydi**: jurnal toza, navbat esa yangi vazifa uchun mangu bo'sh.

```bash
docker compose -f deployment/compose.yaml -f deployment/compose.prod.yml up -d --force-recreate scheduler worker
```

**Kutilgan natija:** ikkala konteyner ham `Recreated` va keyin `running`;
`docker compose logs scheduler --tail 20` da `scheduler_started` qatori
va uning `"sentry": true|false` maydoni.

### 2.2 Jadval haqiqatan yangilanganini o'lchash

```bash
docker compose -f deployment/compose.yaml -f deployment/compose.prod.yml exec db psql -U postgres -d sbozor \
  -c "SELECT component, last_seen_at FROM system_heartbeats ORDER BY component"
```

**Kutilgan natija:** deploy vaqtidan **keyingi** `last_seen_at` qiymatlari
o'z tsikliga mos komponentlarda (`capture_tick` — daqiqalarda,
`outbox_tick` — daqiqalarda, `alert_sweep` — 5 daqiqada). Yangilanmagan
qator planerning eski jadval bilan yugurayotganini bildiradi.

### 2.3 Bu fazada yangi cron QO'SHILMADI

⚠ Zaxira **o'z konteynerida** (`backup`), taskiq jadvalida emas —
ya'ni 8-faza `scheduler` ning jadvaliga **yangi yozuv qo'shmadi**. Band
shu yerda ochiq yozilgan, chunki «yangi cron yo'q» degan **fakt** ham
deploy qarori: `scheduler` ni qayta yaratish zarurati bu fazada
`worker.py` ga tegilgan-tegilmaganidan kelib chiqadi, zaxiradan emas.

> ⛔ **HALOL CHEGARA (§2).** `system_heartbeats` ning yangilanishi
> «vazifa **yugurdi**» ni isbotlaydi, «vazifa **to'g'ri natija** berdi»
> ni emas. Ikkinchisi mahsulot testlarining ishi.

---

## 3. WireGuard tunneli va CAM-02 ning yopilishi (SC#5 ning 3-da'vosi)

CI konteynerida `wg0` interfeysi **yo'q**, ya'ni marshrutning tunneldan
ketishi mexanik darvozaga **kirmaydi** va kira olmaydi ham. Uning
o'rnini shu band egallaydi.

```bash
ops/scripts/verify-tunnel.sh 192.168.1.64 wg0
```

**Kutilgan natija:** `OK: 192.168.1.64 -> wg0 (tunnel)` va **chiqish
kodi 0**. Chiqish kodi 1 — marshrut tunneldan ketmayapti yoki tunnel
umuman ko'tarilmagan; ⛔ nol bo'lmagan kod deploy'ni **TO'XTATADI**.

```bash
sudo wg show wg0 allowed-ips
```

**Kutilgan natija:** faqat NVR subneti (masalan `192.168.1.0/24`).
⛔ `0.0.0.0/0` chiqsa — bu **to'liq tunnel**: VPS ning butun chiquvchi
trafigi bozorning DSL kanaliga burilib, Telegram, Let's Encrypt va
foydalanuvchilar bilan birga o'ladi. Tuzatilmaguncha go-live
boshlanmaydi.

> ⛔ **HALOL CHEGARA (§3).** Skript **marshrutni** o'lchaydi, NVR ning
> **javob berishini** emas. NVR ning haqiqiy firmware xulqi
> (`03-HUMAN-UAT.md` bandlari 3 va 4) alohida va u go-live oldi
> ro'yxatida (§9) turadi.

---

## 4. Birinchi zaxira va tiklash tasdig'i (FOUND-07, D-12..D-16)

⚠ Bu bo'lim `ops/backup/README.md` ni **takrorlamaydi**. Kalitlarning
ma'nosi, jadval sababi (04:40) va haftalik butunlik tsikli o'sha faylda;
bu yerda faqat **deploy kunidagi tartib**.

### 4.1 Kalitlarni to'ldirish

Besh kalit `.env` da: `BACKUP_DATABASE_URL`, `RESTIC_REPOSITORY`,
`RESTIC_PASSWORD`, `BACKUP_S3_ACCESS_KEY`, `BACKUP_S3_SECRET_KEY`
(izohlari — `ops/backup/README.md` §2).

```bash
docker compose -f deployment/compose.yaml -f deployment/compose.prod.yml logs backup --tail 20
```

**Kutilgan natija:** `backup_unconfigured` qatori **YO'Q**. U chiqayotgan
bo'lsa — kalitlar bo'sh; bu holat **to'g'ri xulq** (konteyner jim
ishlab «muvaffaqiyat» yozmaydi) va 26 soatdan keyin `backup_stale`
(CRITICAL) alerti keladi.

### 4.2 Birinchi zaxirani tunni kutmasdan olish

```bash
docker compose -f deployment/compose.yaml -f deployment/compose.prod.yml exec backup /opt/backup/run-backup.sh
```

**Kutilgan natija:** ikkita `restic` xulosasi (biri `postgres` tegi
bilan, ikkinchisi `seaweedfs`), keyin `restic forget` ning retention
xulosasi, exit **0**. Nol bo'lmagan kod — zanjir o'sha qadamda
**to'xtadi** va yurak urishi **yozilmadi**.

```bash
docker compose -f deployment/compose.yaml -f deployment/compose.prod.yml exec backup restic snapshots --compact
```

**Kutilgan natija:** kamida ikki snapshot: `sbozor-<sana>.dump`
(`postgres` tegi) va `/seaweed` (`seaweedfs` tegi), ikkalasi ham
bugungi sana bilan.

```bash
docker compose -f deployment/compose.yaml -f deployment/compose.prod.yml exec db psql -U postgres -d sbozor \
  -c "SELECT component, last_seen_at, detail FROM system_heartbeats WHERE component = 'backup'"
```

**Kutilgan natija:** aynan bitta qator, `last_seen_at` — hozirgi payt.
⛔ Bu **yagona** ishonchli signal: konteynerning `Up` bo'lishi zaxira
olinganini bildirmaydi (`backup` blokida `healthcheck` ATAYIN yo'q).

### 4.3 ⛔⛔ `RESTIC_PASSWORD` — SERVERDAN TASHQARIDA, IKKI JOYDA

restic repo'si har doim shifrlangan va uni ochadigan yagona narsa —
shu parol. **Parolni tiklash yo'li YO'Q.** Parol faqat VPS ning `.env`
ida bo'lsa va VPS o'lsa — **zaxira ham o'ladi**, ya'ni FOUND-07 qog'ozda
bajarilgan, amalda esa bajarilmagan holatga qaytadi va buni **faqat
falokat kuni** bilib olinadi.

Majburiy va imzolanadigan uch band (`ops/backup/README.md` §3 ning
operatsion yuzasi):

| # | Band | Imzo joyi |
|---|------|-----------|
| 1 | Parol **serverdan tashqarida** saqlangan — parol menejeri **va** qog'oz/seyf, ya'ni **ikki joyda** | `08-HUMAN-UAT.md` bandi 2 |
| 2 | Parolni **ikki odam** biladi | `08-HUMAN-UAT.md` bandi 2 |
| 3 | Saqlash joylari **nomma-nom yozilgan** (qaysi menejer, qaysi seyf) | `08-HUMAN-UAT.md` bandi 2 |

```bash
python -c "import secrets;print(secrets.token_urlsafe(48))"
```

**Kutilgan natija:** 64 belgilik tasodifiy satr. ⛔ U jurnalga,
chatga yoki tiketga **yozilmaydi** — to'g'ridan-to'g'ri `.env` ga va
yuqoridagi ikki saqlash joyiga ko'chiriladi.

### 4.4 Tiklash tartibi — ⛔ GRANT QADAMI BILAN

`pg_dump` `--no-owner --no-privileges` bilan yuguradi (08-05 ning ongli
qarori, `test_backup_contract.py` da qulflangan). O'lchangan oqibat
(08-08): manba `44 jadval / 83 policy / 163 GRANT`, tiklangan baza
`44 jadval / 83 policy / **0 GRANT**`. Ya'ni RLS policy'lari
**saqlanadi**, `sbozor_app` ning huquqlari esa **yo'q** — tiklangan
platformada ilova har so'rovda `permission denied for table` olardi.

Tiklash **to'rt** qadam, aynan shu tartibda:

```bash
docker compose -f deployment/compose.yaml -f deployment/compose.prod.yml exec backup restic restore latest --tag postgres --target /tmp/restore
```

**Kutilgan natija:** `restored` xulosasi va `/tmp/restore` ichida
`sbozor-<sana>.dump` fayli.

```bash
docker compose -f deployment/compose.yaml -f deployment/compose.prod.yml exec backup psql "${BACKUP_DATABASE_URL}" -c "SELECT version()"
```

**Kutilgan natija:** `PostgreSQL 18.x` — ⛔ tiklanadigan serverning
majori manbaning majoriga **teng** bo'lishi shart.

```bash
docker compose -f deployment/compose.yaml -f deployment/compose.prod.yml exec backup pg_restore --no-owner --no-privileges \
  --dbname="${BACKUP_DATABASE_URL}" /tmp/restore/sbozor-<sana>.dump
```

**Kutilgan natija:** exit 0; ⚠ `--no-owner` sababli bir nechta
`WARNING` chiqishi normal, `ERROR` esa emas.

```bash
npm run migrate
```

**Kutilgan natija:** `alembic upgrade head` no-op sifatida o'tadi
(sxema allaqachon `head` da), lekin GRANT'lar **qayta chiqadi** —
ular `migrations/helpers.py::enable_tenant_rls` da yashaydi.
⚠ ⛔ **BU QADAMNING O'ZI O'LCHANMAGAN:** CI qatlami (D-16a) tiklashni
GRANT'siz o'lchaydi, ya'ni «ilova tiklangan bazada ishlay oladi» da'vosi
faqat §9 ning 1-bandi bilan imzolanadi. Qadam bajarilmasa tiklash
«muvaffaqiyatli» ko'rinadi va ilova baribir ishlamaydi.

### 4.5 `BACKUP_DATABASE_URL` superuser roliga ishora qiladi

`pg_dump` ishini `row_security = off` bilan boshlaydi; uni o'rnatish
SUPERUSER yoki `BYPASSRLS` talab qiladi, `sbozor_app` va `sbozor_owner`
esa ATAYIN `NOSUPERUSER NOBYPASSRLS`.

```bash
docker compose -f deployment/compose.yaml -f deployment/compose.prod.yml exec db psql -U postgres -d sbozor \
  -c "SELECT rolname, rolsuper, rolbypassrls FROM pg_roles WHERE rolname IN ('postgres','sbozor_owner','sbozor_app')"
```

**Kutilgan natija:** `BACKUP_DATABASE_URL` da nomlangan rol uchun
`rolsuper = t` **yoki** `rolbypassrls = t`. Aks holda birinchi tunggi
zaxira `pg_dump` bosqichida yiqiladi — ⚠ bu **to'g'ri** xulq (jim
qisman dumpdan yaxshiroq), lekin sababi faqat shu yerda yozilgan.

> ⛔ **HALOL CHEGARA (§4).** CI hech qachon **offsite repodan**
> tiklamaydi: sinov konteynerida offsite rekvizitlar ham, `restic`
> binari ham yo'q. Ya'ni SC#3 ning «kamida bir marta muvaffaqiyatli
> tiklash mashqi» da'vosi **faqat** §9 ning 1-bandi bilan imzolanadi;
> `test_restore_drill.py` uni regressiyadan qo'riqlaydi, **o'rnini
> bosmaydi**.

---

## 5. Offsite bucket — data-rezidentlik va migratsiya ro'yxati

⛔ **FOUND-07 loyihaning shaxsiy ma'lumotini BIRINCHI MARTA VPS
chegarasidan tashqariga chiqaradi.** Bugungacha har bayt bitta
mashinada edi; offsite repo esa boshqa provayder, ko'pincha boshqa
yurisdiksiya.

CLAUDE.md ning data-rezidentlik cheklovi (davlat bosqichidan oldin
O'zbekiston hostingiga ko'chish) shu sababdan **offsite bucketga ham**
tegishli:

| Nima | Qayerda |
|------|---------|
| Postgres dump + dalil arxivi | offsite restic repo (`RESTIC_REPOSITORY`) |
| Shifrlash | restic ning o'zi — AES-256 + Poly1305, repo **har doim** shifrlangan |
| Migratsiya ro'yxatidagi o'rni | ⛔ **VPS bilan BIR QATORDA**: hosting ko'chganda repo ham ko'chadi |

```bash
docker compose -f deployment/compose.yaml -f deployment/compose.prod.yml exec backup sh -c 'echo "${RESTIC_REPOSITORY%%/*}"'
```

**Kutilgan natija:** offsite endpoint sxemasi (`s3:https:` bilan
boshlanadi) — ya'ni repo **lokal** SeaweedFS ga emas, boshqa failure
domenga ishora qiladi (D-14). Lokal endpoint chiqsa bitta diskning
o'limi bazani ham, arxivni ham, zaxirani ham birdan olib ketardi.

> ⛔ **HALOL CHEGARA (§5).** Provayderning **jismoniy joylashuvi** kodda
> o'lchanmaydi va o'lchanishi ham mumkin emas — bu shartnoma bandi.
> Uning egasi Ops/buyurtmachi va u §9 ning 3-bandida turadi.

---

## 6. Versiya tartibi — backup image serverdan OLDIN

`pg_dump` ning MAJOR versiyasi serverdan **kichik bo'lolmaydi**:
`pg_dump 17` `postgres 18` ni **rad etadi**. `backup` konteyneri
shuning uchun `db` bilan aynan bir xil image ustida quriladi
(`ops/backup/README.md` §6).

```bash
docker compose -f deployment/compose.yaml -f deployment/compose.prod.yml exec backup pg_dump --version
docker compose -f deployment/compose.yaml -f deployment/compose.prod.yml exec db postgres --version
```

**Kutilgan natija:** ikkala qatorning ham MAJOR raqami **teng**
(masalan `18.4` va `18.4`).

⛔ **Yangilash tartibi — teskari emas:**

| # | Qadam | Sabab |
|---|-------|-------|
| 1 | `ops/backup/Dockerfile` bazasini yangilash va `docker compose build backup` | `pg_dump` majori serverdan katta bo'lishi **mumkin** |
| 2 | `db` image tegini yangilash va `docker compose up -d db` | Server majori endi backup majoridan katta emas |

```bash
docker compose -f deployment/compose.yaml -f deployment/compose.prod.yml exec backup /opt/backup/run-backup.sh
```

**Kutilgan natija:** exit 0 — yangilashdan **keyin** zaxira zanjiri
uchidan-uchiga bir marta yugurtiriladi. Teskari tartibda birinchi
tunggi yugurish versiya farqi bilan yiqilardi: ovoz bilan
(`backup_stale`), lekin bir kunlik zaxira yo'qotib.

> ⛔ **HALOL CHEGARA (§6).** Versiya tengligi **deploy kunida**
> o'lchanadi; ikkala image mustaqil yangilanib ketishini hech qanday
> mexanizm to'smaydi. Yagona himoya — shu tartibning bajarilishi.

---

## 7. Cutover sanasi qoidasi (Post-Launch, D-19/D-20)

Parallel rejim — qog'oz daftar va tizim **birga** yuritiladigan davr.
U ⛔ **2–4 hafta** va ⛔ **CHO'ZILMAYDI**: sana **oldindan e'lon
qilinadi** va o'zgartirilmaydi. Cho'zilgan parallel rejim ikki xarajat
tug'diradi — ikki karra ish va «qaysi raqam haqiqiy?» degan doimiy
ikkilanish.

| Band | Qoida |
|------|-------|
| Davomiyligi | 2–4 hafta, e'lon qilingan sana bilan tugaydi |
| Kunlik solishtiruvni **kim** bajaradi | ⛔ **nazoratchi yoki admin** |
| Kim bajarmaydi | ⛔ **KASSIR EMAS** — u o'zi kiritgan ma'lumotni o'zi tasdiqlardi |
| Chiqish shakli | Ekran + `.xlsx`, pastida imzo qatorlari (bajaruvchi + direktor) |

```bash
curl -sS -o karmana-solishtiruv.xlsx -w '%{http_code}\n' \
  -H "Authorization: Bearer <admin-token>" \
  'https://<domen>/api/v1/reports/three-way.xlsx?date=<sana>'
```

**Kutilgan natija:** `200` va yuklab olingan `.xlsx` faylning pastida
ikki imzo qatori. ⛔ Kassir roli bilan o'sha so'rov **403** qaytaradi —
bu RBAC ning to'g'ri xulqi, nuqson emas.

> ⛔ **HALOL CHEGARA (§7).** Cutover sanasining **bajarilishi**
> tashkiliy qaror; kod uni majburlamaydi. Runbook faqat qoidani
> qayd etadi va uning egasini nomlaydi.

---

## 8. Rollback yo'li

⛔ **Rollback — «oldingi commitga qaytish» EMAS.** Kod orqaga qaytadi,
ma'lumot esa qaytmaydi. Shuning uchun qadamlar **ikki toifaga**
ajratilgan.

### 8.1 Xavfsiz qadamlar (ma'lumot yo'qolmaydi)

```bash
git log --oneline -n 10
git checkout <oxirgi-ishlaydigan-teg>
docker compose -f deployment/compose.yaml -f deployment/compose.prod.yml build core-api worker scheduler cv-service bot-service backup
docker compose -f deployment/compose.yaml -f deployment/compose.prod.yml up -d --force-recreate core-api worker scheduler cv-service bot-service
```

**Kutilgan natija:** konteynerlar eski image bilan `running`;
`docker compose ps` da o'nta servis (§1.4 dagi ro'yxat).
⚠ Bu yo'l faqat **sxema o'zgarmagan** deploy uchun: yangi kod eski
sxemani o'qiy oladi, teskarisi esa har doim ham emas.

### 8.2 ⛔ MA'LUMOT YO'QOLISHI MUMKIN BO'LGAN QADAMLAR — NOMMA-NOM

| # | Qadam | Nima yo'qoladi |
|---|-------|----------------|
| 1 | `alembic downgrade <revizyon>` — ustun **tashlaydigan** migratsiya | O'sha ustunning **butun mazmuni**, qaytarib bo'lmaydi |
| 2 | `alembic downgrade` — jadval **tashlaydigan** migratsiya | Jadvalning barcha qatorlari |
| 3 | `docker compose down -v` | ⛔ **`pgdata` va `seaweed` hajmlari** — baza ham, dalil arxivi ham |
| 4 | `pg_restore` ni **mavjud** bazaga `--clean` bilan yugurtirish | Zaxira olingan paytdan **keyingi** hamma yozuv |

```bash
npm run migrate
```

**Kutilgan natija:** `alembic upgrade head` — ⛔ downgrade'dan **oldin**
joriy revizyon nomi yozib olinadi, aks holda qaytish nuqtasi
yo'qoladi. Downgrade zaruriyati tug'ilsa avval §4.2 ning zaxirasi
**qo'lda** olinadi.

### 8.3 Rollback qarorining chegarasi

```bash
docker compose -f deployment/compose.yaml -f deployment/compose.prod.yml exec db psql -U postgres -d sbozor \
  -c "SELECT version_num FROM alembic_version"
```

**Kutilgan natija:** bitta qator — joriy revizyon. ⛔ Agar u
`git checkout` qilingan tegning `head` idan **oldinda** bo'lsa, kod
rollback qilingan, sxema esa **qilinmagan**: shu holatda ilovani
ko'tarish o'rniga §4.4 ning tiklash tartibi ishlatiladi.

> ⛔ **HALOL CHEGARA (§8).** Bu yerda hech qanday avtomatik rollback
> yo'q va ATAYIN yo'q: avtomatik downgrade yuqoridagi 8.2 jadvalining
> 1- va 2-qatorini **odam qaroridan tashqarida** bajarardi.

---

## 9. Go-live oldi ro'yxati

⛔ Ro'yxat **bu faylda takrorlanmaydi** — u bitta joyda:

**`.planning/phases/08-hisobotlar-mustahkamlash-va-ishga-tushirish/08-HUMAN-UAT.md`**

O'sha faylda har band **egasi**, **tetigi** va **imzosi** bilan turadi,
oldingi besh fazaning yopilmagan bandlari esa **havola** bilan
kiritilgan (matn ko'chirilmagan — ikki nusxa bir kun ajralib ketardi).

```bash
grep -c '^### ' .planning/phases/08-hisobotlar-mustahkamlash-va-ishga-tushirish/08-HUMAN-UAT.md
```

**Kutilgan natija:** **6** yoki undan katta son — go-live oldi
ro'yxatining bandlari soni. Nol yoki fayl topilmasa: go-live
boshlanmaydi, chunki SC#3 va SC#4 ning imzo joyi **mavjud emas**.

> ⛔ **HALOL CHEGARA (§9).** Ro'yxatning **mavjudligi va shakli**
> mexanik o'lchanadi (`tests/unit/test_runbook_shape.py`), **mazmuni**
> esa inson qaroriga tayanadi. Imzolanmagan band — bajarilmagan band,
> va uni hech qanday test yashil qila olmaydi.

---

*Aloqador hujjatlar: `ops/backup/README.md` (zaxiraning kalitlari va
haftalik butunlik tsikli), `ops/docs/monitoring.md` (alertlar va
kunlik operatsion tartib), `ops/docs/nvr-onboarding.md` (NVR ulash).*
