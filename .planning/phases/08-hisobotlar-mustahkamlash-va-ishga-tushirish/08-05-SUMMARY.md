---
phase: 08-hisobotlar-mustahkamlash-va-ishga-tushirish
plan: 05
subsystem: infra
tags: [restic, postgres, pg_dump, seaweedfs, docker-compose, backup, heartbeat, offsite-s3]

# Dependency graph
requires:
  - phase: 04-snapshot-pipeline
    provides: "`system_heartbeats` jadvali (0014), `seaweed` nomlangan volume, `/internal/self-check` dagi `EXPECTED_COMPONENTS`"
  - phase: 07-nomuvofiqlik-bildirishnoma-va-botlar
    provides: "`alerting.BACKUP_COMPONENT`, `HEARTBEAT_STALE_HOURS = 26`, `backup_stale` `ALERT_META` da, `_platform_signals::watched`"
provides:
  - "`backup` konteyneri — kunlik offsite zaxira (Postgres dump + dalil arxivi), profilsiz"
  - "Quvursiz zaxira zanjiri: `restic backup --stdin-from-command -- pg_dump …` (chiqish kodi tekshiriladi)"
  - "Idempotent tsikl, holati BAZADA (`system_heartbeats`) — restart kunni yo'qotmaydi"
  - "`system_heartbeats['backup']` qatorini YOZADIGAN jarayon — 7-fazadan beri kutilayotgan yarim"
  - "`tests/unit/test_backup_contract.py` — shell/SQL/compose ustidagi statik kontrakt darvozasi"
  - "Besh yangi env kaliti va ularning sabablari (`.env.example`, `ops/backup/README.md`)"
affects: [08-08-tiklash-mashqi, 08-19-runbook, 08-HUMAN-UAT, ops-deploy]

# Tech tracking
tech-stack:
  added: ["restic 0.19.1 (BSD-2, Docker image tegi pinlangan)"]
  patterns:
    - "Teskari baza: `FROM postgres:18.4-trixie` + `COPY --from=restic/restic:<teg>` static binar"
    - "Idempotent tsikl, holati Postgres'da (4-faza D-03 naqshining ops qatlamiga ko'chirilishi)"
    - "Yurak urishi — MUVAFFAQIYAT signali: zanjirning eng oxirida, `trap` da EMAS"
    - "Shell/SQL uchun statik kontrakt darvozasi (mantiqiy buyruq yig'uvchi + nazorat namunasi)"

key-files:
  created:
    - ops/backup/Dockerfile
    - ops/backup/run-backup.sh
    - ops/backup/loop.sh
    - ops/backup/heartbeat.sql
    - ops/backup/README.md
    - tests/unit/test_backup_contract.py
  modified:
    - compose.yaml
    - .env.example
    - package.json

key-decisions:
  - "08-05: `restic/restic:0.19.1` legitimligi bloklovchi darvoza bilan tasdiqlandi (Docker Hub tegi 2026-07-05 + GitHub reliz + BSD-2 + digest + `restic version` zondi); tanlangan yo'l `COPY --from`, `ADD`-fallback KERAK BO'LMADI"
  - "08-05: baza TESKARI — `postgres:18.4-trixie` + restic static binari; `FROM restic/restic` + `apk add postgresql18-client` QURILMAYDI (Alpine v3.22 da paket yo'q) va `pg_dump 17` `postgres 18` ni rad etardi"
  - "08-05: `pg_dump` va `restic` orasida QUVUR YO'Q — quvur `pg_dump` chiqish kodini yutadi va yiqilgan dumpni «muvaffaqiyat» deb yozardi; `--stdin-from-command` chiqish kodini tekshiradi"
  - "08-05: `--compress=0` MAJBURIY — siqilgan dump restic dedup'ini o'ldiradi (14 kunlik retention = 14 x to'liq baza)"
  - "08-05: yurak urishi zanjirning ENG OXIRIDA va `trap`/`finally` da EMAS — nosozlikda yozilgan qator tizimni o'zining buzuqligiga ko'r qilardi (D-15)"
  - "08-05: sozlanmagan tsikl `exit` QILMAYDI — `restart: unless-stopped` bilan u crash-loop bo'lardi; u `backup_unconfigured` yozadi, uxlaydi va yurak urishini YOZMAYDI (26 soatdan keyin `backup_stale`)"
  - "08-05: 04:40 Asia/Tashkent — `retention` (03:20), `day_close` (03:40) va `billing_close` (04:10) dan KEYIN, kadr olish oynasidan (06:00) OLDIN"
  - "08-05: `backup` konteyneri root ostida qoladi (`core-api` ning `appuser` qaroridan ATAYIN farq) — `:ro` seaweed hajmi root egaligida va boshqa UID arxivning bir qismini JIMGINA o'tkazib yuborardi"
  - "08-05: komponent nomining IKKINCHI nusxasi (`loop.sh` dagi `already_done_today()`) ham darvozada qulflandi — ajralib ketsa tsikl kunlik yozuvni topmasdi va HAR 10 DAQIQADA to'liq zaxira boshlanardi"
  - "08-05: yangi alert kaliti QO'SHILMADI — `ALERT_TITLE_KEY_COUNT = 15` o'zgarmadi (o'lchandi); `restic check` nosozligi yurak urishini o'chirmaydi va alohida signal V2 ga qoldirildi"

patterns-established:
  - "Statik darvoza uchun MANTIQIY BUYRUQ yig'uvchi: `\\` bilan bo'lingan qatorlar bitta buyruqqa yig'iladi, aks holda «orasida quvur bormi?» savolining o'zi ma'nosiz bo'ladi"
  - "Predikatning O'ZI nazorat namunasi bilan o'lchanadi (ijobiy: quvur ushlanadi; salbiy: `||` ushlanmaydi) — usiz «topilmadi» mangu yashil bo'lardi"
  - "Quyi chegara `autouse` fixture'da: u alohida test emas, HAR o'lchovdan oldin bajariladi"

requirements-completed: [FOUND-07]

# Metrics
duration: 35min
completed: 2026-08-16
---

# Phase 8 Plan 05: Kunlik offsite zaxira va uning yurak urishi — Summary

**`backup` konteyneri (`postgres:18.4-trixie` + restic 0.19.1 static binari) har kuni 04:40 da quvursiz `pg_dump` va dalil arxivini offsite restic repo'siga yozadi va FAQAT to'liq muvaffaqiyatdan keyin `system_heartbeats['backup']` ni yangilaydi — ya'ni 7-fazadan beri kutib turgan `backup_stale` halqasi endi manba bilan ulandi.**

## Performance

- **Duration:** 35 min (Task 2 + Task 3; Task 1 — alohida, bloklovchi checkpoint sessiyasi)
- **Started:** 2026-08-16T05:02:00Z
- **Completed:** 2026-08-16T05:37:00Z
- **Tasks:** 3/3 (Task 1 — inson tasdig'i, kod fayli yo'q)
- **Files modified:** 9 (6 yangi, 3 tahrirlangan)

## Accomplishments

- **FOUND-07 ning yetishmayotgan yarmi qurildi.** Kuzatuv halqasi (`backup_stale`, CRITICAL + `never_suppressed`) 7-fazadan beri tayyor edi, lekin uni oziqlantiradigan jarayon yo'q edi — `system_heartbeats['backup']` qatori UMUMAN mavjud emasdi. Endi u bor va uni faqat TO'LIQ muvaffaqiyat yozadi.
- **Zaxira zanjiridagi eng qimmat jim nosozlik strukturaviy yopildi:** `pg_dump | restic --stdin` quvuri `pg_dump` ning chiqish kodini yutadi va yiqilgan dumpni muvaffaqiyat deb yozardi. `--stdin-from-command` chiqish kodini tekshiradi, va bu endi statik darvoza bilan qulflangan (sabotaj bilan o'lchandi).
- **`shell` va `SQL` birinchi marta mexanik darvoza ostiga tushdi.** `ops/backup/` ga na `ruff`, na `mypy`, na birorta birlik testi qaramasdi — endi yetti o'lchov unga qaraydi va predikatlarning o'zi nazorat namunalari bilan tekshiriladi.
- **Sozlanmagan zaxira endi jim qolmaydi.** Beshala kalit bo'sh bo'lsa tsikl `backup_unconfigured` yozadi, zaxirani boshlamaydi va yurak urishini yozmaydi — 26 soatdan keyin CRITICAL alert chiqadi. Bu empirik o'lchandi (konteyner ishga tushirilib, chiqish kuzatildi).
- **Yangi alert kaliti QO'SHILMADI:** `ALERT_TITLE_KEY_COUNT = 15` o'zgarmadi (`node --test frontend/scripts/snapshot-copy.test.mjs` — 13/13 yashil).

## Task Commits

1. **Task 1: `restic/restic:0.19.1` legitimligi darvozasi** — commit YO'Q (read-only inson tasdig'i; natijasi quyidagi «Paket legitimligi» bo'limida)
2. **Task 2: `ops/backup/` — image, quvursiz skript, tsikl, yurak urishi** — `3690225` (feat)
3. **Task 3: compose xizmati, `.env.example`, `npm run up`, statik darvoza** — `8b37b2c` (feat)

## Files Created/Modified

- `ops/backup/Dockerfile` — `postgres:18.4-trixie` + `COPY --from=restic/restic:0.19.1`; teskari baza tanlovining sababi izohda literal
- `ops/backup/run-backup.sh` — 5 qadam: env darvozalari → `restic cat config || init` → quvursiz dump → arxiv → retention → yurak urishi (ENG OXIRIDA)
- `ops/backup/loop.sh` — 10 daqiqalik idempotent tsikl, holati bazada; `backup_unconfigured` shoxi `exit` qilmaydi; yakshanba `restic check --read-data-subset=5%`
- `ops/backup/heartbeat.sql` — komponent nomi bitta joyda, `:'day'` bog'langan o'zgaruvchi, `ON CONFLICT (component) DO UPDATE`
- `ops/backup/README.md` — nima o'lchanadi / nima O'LCHANMAYDI, besh kalit, `RESTIC_PASSWORD` ning majburiy off-server bandi
- `tests/unit/test_backup_contract.py` — 7 o'lchov + `MIN_SCANNED_FILES` + nazorat namunalari
- `compose.yaml` — `backup:` bloki (profilsiz, `seaweed:/seaweed:ro`, sirlar `${...}` orqali); sarlavhadagi profil ro'yxati to'g'rilandi
- `.env.example` — besh yangi kalit + ikkita ixtiyoriy sozlama, har biriga sabab
- `package.json` — `scripts.up` zanjiriga `backup`, ustida `//up` izohi

## Paket legitimligi (Task 1 — bloklovchi darvoza natijasi)

Uch qatorli majburiy qayd (rejaning `<action>` bandi):

1. **Docker Hub tegi tasdiqlandi:** `restic/restic:0.19.1` mavjud, `tag_last_pushed = 2026-07-05` — 08-RESEARCH § Package Legitimacy Audit bilan MOS. GitHub reliz `v0.19.1` HTTP 200, `LICENSE` = **BSD 2-Clause** (© Alexander Neumann).
2. **`docker pull` MUVAFFAQIYATLI tugadi** (tarmoq bor). Manifest-list digesti `sha256:136600b6ff6843d61d355f7f71f460a166429f35de6fd11b568fece3c9a4d510`, amd64 per-arch digesti `sha256:08916bcda4a4435f9d9828ebb4e91bb7ada3d2c8a53699788930e0ae1bd4fa67` (kutilganga TENG). ⚠ Nuans: `pull` manifest-LIST digestini ko'rsatadi, per-arch digest esa OCI ierarxiyasining boshqa qatlami — bu farq **nomuvofiqlik EMAS**.
3. **Tanlangan yo'l — `COPY --from=restic/restic:0.19.1`**; `ADD …restic_0.19.1_linux_amd64.bz2` fallback'i **KERAK BO'LMADI**.

**A1 farazi (static binar Debian'da ishlaydi) EMPIRIK o'lchandi**, ikki marta — checkpoint sessiyasida zond bilan va bu ijroda haqiqiy image bilan:

```
restic 0.19.1 compiled with go1.26.4 on linux/amd64
pg_dump (PostgreSQL) 18.4 (Debian 18.4-1.pgdg13+1)
psql    (PostgreSQL) 18.4 (Debian 18.4-1.pgdg13+1)
```

`pg_dump` MAJOR versiyasi serverga TENG (18 = 18), ya'ni Pitfall 8a yopilgan.

**Checkpoint qarori:** orkestrator auto-approved (foydalanuvchining doimiy avtonom rejimi), digest tekshiruvi bilan.

## Uch sabotaj — o'lchandi va qaytarildi

| # | Sabotaj | Kutilgan | O'lchangan natija |
|---|---------|----------|-------------------|
| 1 | `--stdin-from-command` o'rniga `pg_dump … \| restic backup --stdin` | (c) qizaradi | ✅ QIZARDI: «`run-backup.sh` da `--stdin-from-command` YO'Q…» |
| 1b | (qo'shimcha) quvur SAQLANDI, lekin `--stdin-from-command` ham qo'yildi | (c) ning IKKINCHI yarmi qizaradi | ✅ QIZARDI: «QUVUR topildi: ['pg_dump … \| restic backup …']» |
| 2 | `heartbeat.sql` da `'backup'` → `'backups'` | (a) qizaradi va IKKALA qiymatni ko'rsatadi | ✅ QIZARDI: «`heartbeat.sql` da 'backups', `alerting.BACKUP_COMPONENT` esa 'backup'» |
| 3 | Yurak urishi `restic forget` dan OLDINGA ko'chirildi | (e) qizaradi | ✅ QIZARDI: «yurak urishidan KEYIN yana zaxira qadami bor: ['restic forget --keep-daily 14 …']» |

Uchalasi ham `git checkout -- <fayl>` bilan qaytarildi va qaytarilgandan keyin `bash -n` hamda to'liq to'plam qayta yashil bo'ldi.

> ⚠ **1b QO'SHIMCHA VA U REJADA YO'Q EDI.** 1-sabotaj (c) ni birinchi
> sub-assert'da (`--stdin-from-command` yo'qligi) to'xtatdi, ya'ni QUVUR
> DETEKTORINING o'zi o'lchanmagan bo'lib qolardi. Ikkinchi variant aynan
> uni o'lchadi. Bu 05-15 darsining takrori: sabotaj sistemaga yetib borsa
> ham, u tekshirmoqchi bo'lgan PREDIKATGA yetib bormasligi mumkin.

## Verification natijalari

| O'lchov | Natija |
|---------|--------|
| `docker compose config --quiet` | EXIT **0** |
| `docker compose build backup` | ✅ `Image sbozor-backup Built` |
| `docker compose --profile test run --rm tests pytest tests/unit/test_backup_contract.py -q` | ✅ **7 passed** |
| `pytest tests/unit -q` (to'liq to'plam) | ✅ **hammasi yashil** (regressiya yo'q) |
| `ruff check . && ruff format --check . && mypy .` | ✅ `All checks passed` / `352 files already formatted` / `no issues found in 341 source files` |
| `node --test frontend/scripts/snapshot-copy.test.mjs` | ✅ **13/13** — `ALERT_TITLE_KEY_COUNT = 15` O'ZGARMADI |
| `grep -c "seaweed:/seaweed:ro" compose.yaml` | **1** |
| `node -e "…scripts.up.includes('backup')…"` | EXIT **0** |
| `grep -c "def test_" tests/unit/test_backup_contract.py` | **7** |
| `bash -n ops/backup/*.sh` | ✅ ikkalasi ham toza |
| Sozlanmaganlik shoxi (jonli) | ✅ konteyner ishga tushirildi: `backup_unconfigured` takror yozildi, jarayon CHIQMADI |

## Decisions Made

Yuqoridagi frontmatter `key-decisions` ro'yxati to'liq. Ikkitasi alohida
diqqat talab qiladi:

- **`backup` konteyneri root ostida qoladi.** Bu `core-api` ning
  `appuser` (T-01-07) qaroridan ATAYIN farq qiladi va sabab o'lchanadigan:
  `seaweed` hajmi `storage` konteyneri tomonidan root egaligida yoziladi.
  Boshqa UID ostida `restic backup /seaweed` arxivning bir qismini
  `permission denied` bilan JIMGINA o'tkazib yuborardi — ya'ni zaxira
  «muvaffaqiyatli» bo'lib, uning yarmi yo'q bo'lardi. Konteynerda tarmoq
  yuzasi yo'q (`ports:` yozilmagan) va kiruvchi so'rov yo'q, ya'ni
  `core-api` dagi hujum yuzasi bu yerda mavjud emas.
- **`restic check` nosozligi yurak urishini o'chirmaydi.** U zaxira
  OLISHNING emas, repo BUTUNLIGINING nosozligi; ikkalasini bitta signalga
  yig'ish bugungi muvaffaqiyatli zaxira ustida ham «zaxira ishlamayapti»
  deb qichqirardi. Alohida kalit — V2 (D-25 sinfi, `ALERT_TITLE_KEY_COUNT`
  qulfi).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Komponent nomining IKKINCHI nusxasi qulflanmagan edi**
- **Found during:** Task 2 (`loop.sh` yozilishi)
- **Issue:** Reja «komponent nomi BITTA joyda» deydi va darvozani faqat `heartbeat.sql` ga qaratadi. Lekin `already_done_today()` o'sha nomni SQL sharti sifatida IKKINCHI marta yozadi (`component = 'backup'`) — busiz «bugun olinganmi?» savolini berib bo'lmaydi. Ikkisi ajralib ketsa tsikl kunlik yozuvni HECH QACHON topmasdi va HAR 10 DAQIQADA to'liq zaxira boshlanardi: offsite trafik va `forget --prune` takror-takror, hech qanday xatosiz.
- **Fix:** (a) o'lchovi kengaytirildi — u endi `heartbeat.sql` NI HAM, `loop.sh` NI HAM `alerting.BACKUP_COMPONENT` dan IMPORT qilingan qiymat bilan solishtiradi.
- **Files modified:** `tests/unit/test_backup_contract.py`
- **Verification:** 2-sabotaj (a) ni qizartirdi; test yashil holatda ikkala faylni ham o'qiydi
- **Committed in:** `8b37b2c`

**2. [Rule 3 - Blocking] `${VAR:?matn}` ichidagi apostrof skriptni SINDIRDI**
- **Found during:** Task 2 (`run-backup.sh` sintaksis tekshiruvi)
- **Issue:** `: "${RESTIC_PASSWORD:?repo paroli MAJBURIY — yo'qolsa …}"` — `${...}` ichidagi yolg'iz `'` bash uchun OCHILGAN qo'shtirnoq bo'lib qoladi (izohdagi apostrofdan farqli). O'lchandi: `bash -n` → `unexpected EOF while looking for matching '`. Skript UMUMAN ishga tushmasdi.
- **Fix:** Xabar apostrofsiz qayta yozildi («parolsiz zaxira BUTUNLAY tiklanmaydi») va sabab kod izohida qoldirildi, ya'ni keyingi tahrir uni qaytarib qo'ymaydi.
- **Files modified:** `ops/backup/run-backup.sh`
- **Verification:** `bash -n ops/backup/run-backup.sh` EXIT 0; konteyner jonli ishga tushirildi
- **Committed in:** `3690225`

**3. [Rule 1 - Bug] Vaqt sharti `>` emas, `>=` bo'lishi kerak edi**
- **Found during:** Task 2 (`loop.sh`)
- **Issue:** 08-RESEARCH ning Code Example 5 i `[[ "${NOW}" > "${RUN_AFTER_HOUR}" ]]` yozadi, reja matni esa «Vaqt ≥ `RUN_AFTER_HOUR`» deydi. Qat'iy `>` bilan AYNAN 04:40 da uyg'ongan tsikl kunni boshlamasdi.
- **Fix:** `! [[ "${NOW}" < "${RUN_AFTER_HOUR}" ]]` (bash'da satrlar uchun `>=` yo'q). Izohda `HH:MM` ning nol bilan to'ldirilgani leksikografik solishtiruvni vaqt tartibiga TENG qilishi yozildi.
- **Files modified:** `ops/backup/loop.sh`
- **Verification:** `bash -n` toza; mantiq izohda nomlangan
- **Committed in:** `3690225`

**4. [Rule 1 - Bug] `compose.yaml` sarlavhasidagi profil ro'yxati eskirgan edi**
- **Found during:** Task 3 (compose tahriri)
- **Issue:** Fayl sarlavhasi profilsiz komponentlarni sanaydi, lekin `bot-service` (07-01 da qo'shilgan) u yerda YO'Q edi. `backup` ni qo'shib, ro'yxatni eskirgan holda qoldirish ikkinchi marta o'sha xatoni takrorlardi.
- **Fix:** Ro'yxat to'ldirildi: `… cv-service, bot-service, go2rtc, backup`.
- **Files modified:** `compose.yaml`
- **Verification:** `docker compose config --quiet` EXIT 0
- **Committed in:** `8b37b2c`

### Ongli shakl farqlari (xato emas, qaror)

**5. Quyi chegara ALOHIDA TEST emas, `autouse` FIXTURE.**
Reja `test_backup_contract.py` da AYNAN 7 ta `def test_` talab qiladi va
AYNI PAYTDA `test_compose_sim_env.py` ning «quyi chegara majburiy»
qoidasini talab qiladi. Alohida chegara testi sanoqni 8 ga chiqarardi.
Yechim kuchliroq chiqdi: chegara `autouse` fixture'da, ya'ni u ETTALA
o'lchovning HAR BIRIDAN oldin bajariladi. Alohida test bo'lganda u yolg'iz
qizarib, qolgan yetti da'vo bo'sh-rost holida yashil bo'lib turardi.

**6. `loop.sh` ning ikki bandi (e) o'lchovi ichida.**
Reja (a)–(g) ni yettita alohida test deb yozadi; `loop.sh` ning
`backup_unconfigured` shoxi esa Task 2 ning qabul mezonida, alohida
o'lchov sifatida emas. U (e) ga qo'shildi, chunki ikkalasi AYNAN BIR XIL
da'voni himoya qiladi: «yurak urishi — MUVAFFAQIYAT signali, tiriklik
signali EMAS». Sanoq shu sababdan yettita bo'lib qoldi.

**7. `ops/seaweedfs/s3.json` lokal yaratildi (repoga tegmaydi).**
Rejaning verify buyrug'i (`docker compose --profile test run --rm tests …`)
`storage` ni ko'taradi, u esa `s3.json` ni bind-mount qiladi. Fayl yo'q
bo'lsa Docker uni KATALOG qilib yaratadi (`ops/seaweedfs/README.md` §2 dagi
o'lchangan tuzoq). Shuning uchun hujjatlangan qadam bajarildi:
`cp ops/seaweedfs/s3.json.example ops/seaweedfs/s3.json`. Fayl
`.gitignore` da, ya'ni commit'ga tushmadi va `git status` toza.

---

**Total deviations:** 4 auto-fixed (1 missing critical, 1 blocking, 2 bug) + 3 ongli shakl farqi
**Impact on plan:** Hech biri qamrovni kengaytirmadi. №1 haqiqiy jim nosozlikni yopdi (10 daqiqada bir marta takrorlanadigan zaxira), №2 skript umuman ishlamas holatini tuzatdi, №3/№4 reja matni bilan kodni moslashtirdi.

## Issues Encountered

- **`git checkout -- <fayl>` bilan sabotaj qaytarish ishonchli chiqdi**, chunki Task 2 sabotajlardan OLDIN commit qilingan edi. Agar tartib teskari bo'lganda qaytarish qo'lda bo'lardi va xato ehtimoli bor edi.
- **Xost diski 92 % to'la (bo'sh 15 GB).** Zond image (`sbozor-backup-probe:08-05`) o'lchovdan keyin O'CHIRILDI; yakuniy `docker compose build backup` esa kesh ustida ishladi va yangi qatlam ~40 MB. Bu 05-15 dan meros xavf va u hamon ochiq.
- **Test konteyneri `depends_on: storage`** — sabotaj tsikllarida `--no-deps` bilan ishlatildi (har o'lchovda SeaweedFS ni qayta ko'tarish narxini oldini olish uchun). Yakuniy o'lchov rejaning AYNAN buyrug'i bilan, `--no-deps` SIZ bajarildi va yashil.

## User Setup Required

**Beshta muhit o'zgaruvchisi TASHQI XIZMATNI talab qiladi** — ular
`.env.example` da e'lon qilingan va `ops/backup/README.md` §2 da
tushuntirilgan:

| Kalit | Manba |
|-------|-------|
| `RESTIC_REPOSITORY` | Backblaze B2 yoki IKKINCHI Contabo region bucket'i (`s3:https://<endpoint>/<bucket>/<yo'l>`) |
| `RESTIC_PASSWORD` | Yangi generatsiya; ⛔ SERVERDAN TASHQARIDA ikki joyda saqlanadi va IKKI ODAM biladi |
| `BACKUP_S3_ACCESS_KEY` | Offsite provayder konsoli → Application keys |
| `BACKUP_S3_SECRET_KEY` | Offsite provayder konsoli → Application keys |
| `BACKUP_DATABASE_URL` | libpq shakli (`postgresql://…`) — ⛔ `DATABASE_URL` YAROQSIZ |

⛔ To'ldirilmaguncha `backup` konteyneri `backup_unconfigured` holatida
turadi va **26 soatdan keyin `backup_stale` (CRITICAL) alerti chiqadi**.
Bu TO'G'RI xulq, kamchilik emas.

## Known Stubs

Yo'q. `ops/backup/` dagi har bir qadam haqiqiy buyruq chaqiradi; hech
qanday joyda qattiq yozilgan bo'sh qiymat, «coming soon» yoki soxta
muvaffaqiyat yo'q. ⚠ CI'da o'lchanmaydigan yagona da'vo — «OFFSITE repodan
tiklash» — SUMMARY da ham, `ops/backup/README.md` §1 da ham, skript
sarlavhasida ham OCHIQ nomlangan va uning egasi Ops (`08-HUMAN-UAT.md`).

## Threat Flags

Yangi yuza REJADAGI `<threat_model>` DAN TASHQARIDA topilmadi. Ikki band
qayd etiladi (ikkalasi ham reja chegaralari ichida, lekin nomlanishi
shart):

| Band | Fayl | Ta'rif |
|------|------|--------|
| Ishonch chegarasi (reja: «VPS → offsite S3») | `compose.yaml`, `ops/backup/run-backup.sh` | Loyihaning shaxsiy ma'lumoti BIRINCHI MARTA VPS chegarasidan chiqadi. Yumshatish: restic repo'si HAR DOIM shifrlangan (AES-256 + Poly1305), `rclone sync` (crypt'siz) R-9 da rad etilgan. |
| Konteyner root ostida (reja bunga TEGMAGAN) | `ops/backup/Dockerfile` | `USER` o'zgartirilmadi va sabab izohda literal: `:ro` seaweed hajmi root egaligida. Kompensatsiya: `ports:` yo'q, kiruvchi yuza yo'q, arxiv `:ro` (T-08-19). |

## Next Phase Readiness

- **08-08 (tiklash mashqi) uchun tayyor:** `run-backup.sh` dagi `pg_dump` bayroqlari (`--format=custom --compress=0 --no-owner --no-privileges`) o'sha testning manba shakli bilan AYNAN bir xil, ya'ni CI qatlami mahsulot bilan bir xil dumpni tiklaydi.
- **08-19 (runbook) uchun tayyor:** `ops/backup/README.md` §3 (parol), §6 (versiya tartibi: serverdan OLDIN backup image'i) va §7 (haftalik `restic check`) — uchalasi runbookning bandlari.
- **`08-HUMAN-UAT.md` ga IKKI band ochiq qoladi:** (1) «`RESTIC_PASSWORD` qayerda saqlangani yozildi va IKKI ODAM biladi»; (2) «offsite repodan tiklash bir marta bajarildi». Ikkalasining egasi Ops va ikkalasi ham CI'da hech qachon o'lchanmaydi.
- **Ochiq band (V2):** `restic check` nosozligi bugun faqat `stderr` ga chiqadi. Alohida signal (`backup_check_stale`) yangi alert kaliti talab qiladi va u `ALERT_TITLE_KEY_COUNT` qulfini qizartiradi — D-25 sinfi.

---
*Phase: 08-hisobotlar-mustahkamlash-va-ishga-tushirish*
*Completed: 2026-08-16*
