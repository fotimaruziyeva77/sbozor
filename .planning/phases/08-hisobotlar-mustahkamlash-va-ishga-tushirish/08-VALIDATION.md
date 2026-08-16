---
phase: 8
slug: hisobotlar-mustahkamlash-va-ishga-tushirish
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-08-13
updated: 2026-08-16
human_only_verifications:
  - item: REAL toza serverda REAL offsite repodan tiklash mashqi (FOUND-07, SC#3)
    why_not_automatable: CI konteynerida na `restic` binari, na offsite rekvizitlar, na toza VPS bor. `tests/integration/test_restore_drill.py` FAQAT mexanizmni o'lchaydi (pg_dump -> toza postgres:18.4 konteyneri -> pg_restore -> moliyaviy qatorlar, pg_policies va audit_log joyida) va u restic'ga UMUMAN tegmaydi. Ya'ni «offsite repodan tiklandi» da'vosi mexanik qatlamda o'lchanmagan va o'lchanishi ham mumkin emas. Qo'shimcha o'lchangan fakt (08-08): tiklangan bazada sbozor_app uchun 0 GRANT — imzodan OLDIN migratsiya qayta yugurtiriladi
    owner: Ops
    trigger: VPS deploy (pilotdan oldin) — 08-HUMAN-UAT.md #1
  - item: RESTIC_PASSWORD qayerda saqlangani yozilgan va uni IKKI odam biladi
    why_not_automatable: Bu tashkiliy fakt, kod emas. Nosozlik shakli eng yomon sinfdan: parol faqat VPS ning .env ida qolsa hech nima qizarmaydi — zaxira har kuni muvaffaqiyatli olinadi, yurak urishi yoziladi, tizim o'zini sog'lom deb ko'rsatadi — va faqat falokat kuni ma'lum bo'ladi: zaxira BOR, ochib BO'LMAYDI (T-08-85). Bandning bajarilmagani HECH QANDAY signal bermaydi
    owner: Ops
    trigger: Birinchi zaxiradan keyin — 08-HUMAN-UAT.md #2
  - item: Offsite S3 hisobi ochilgan va RESTIC_REPOSITORY to'ldirilgan (boshqa failure domain)
    why_not_automatable: Byudjet va hisob ochish qarori — CI'da bajarilmaydi. Kod hisobsiz ham to'g'ri ishlaydi: kalitlar bo'sh bo'lsa zaxira BOSHLANMAYDI, yurak urishi YOZILMAYDI va 26 soatdan keyin backup_stale (CRITICAL, never_suppressed) chiqadi. ⛔ Bu to'g'ri xulq va alertni o'chirish TAQIQ. D-14: offsite endpoint VPS bilan BOSHQA failure domain bo'lishi shart (Backblaze B2 yoki ikkinchi Contabo regioni) — lokal SeaweedFS kalitlari YARAMAYDI
    owner: Ops / buyurtmachi
    trigger: Byudjet qarori — 08-HUMAN-UAT.md #3
  - item: Uch tilli yakuniy tekshiruv — kassir, nazoratchi va admin tizimda mashq qiladi (SC#4)
    why_not_automatable: Mexanik parity ALLAQACHON darvozada (i18n:check kalit-parity, glossary.test.mjs atama birligi, error-codes.test.mjs reyestr skani) va bu fazada yangi mexanik darvoza yozilmadi (D-23). Ular kalit va matn MAVJUDLIGINI o'lchaydi; o'lchanmagani — o'sha matnning ona tilida to'g'ri ESHITILISHI va uch rolning o'z oqimini uch tilda bajara olishi. Bu lug'at emas, IDROK savoli
    owner: Mahsulot egasi (uch rol egasi bilan)
    trigger: Pilot tayyorgarligi haftasi — 08-HUMAN-UAT.md #4
  - item: "`npm run up` ning dev mashinasida bir marta qo'lda tasdiqlanishi"
    why_not_automatable: Buyruq standart compose loyihasiga (sbozor) tegadi va uni CI'da yugurtirish ijro muhitidagi ishlab turgan stekni qayta yaratardi. Yopilgan yarmi mexanik (tests/unit/test_dev_environment.py — ro'yxatdagi HAR servis compose.yaml da mavjud), ochiq qolgani — buyruqning O'ZI hech qachon uchidan-uchiga yugurtirilmagan
    owner: Ops / dasturchi
    trigger: Birinchi deploydan oldin — 08-HUMAN-UAT.md #5
automated_replacements:
  - was: Hisobotni brauzerda ochib «fayl yuklandimi?» deb ko'z bilan tekshirish
    now: "docker compose --profile test run --rm tests pytest tests/integration/test_phase8_criteria.py -q — beshala eksportning baytlari mahsulotning O'Z o'quvchisidan (xlsx_reader.read_rows) o'tkaziladi va sarlavha qatori matn katalogi bilan solishtiriladi. ⛔ `200` mezon EMAS va taqiq MEXANIK: hujjat yo'liga tegib javob KODI haqida da'vo qilgan HAR test o'quvchini ham chaqirishi shart (AST darvozasi)"
  - was: Uch tilni almashtirib, uchta faylni qo'lda yuklab olib solishtirish
    now: "test_sc4_runbook_exists_and_all_three_locales_reach_the_document — profil tili uchala qiymatga qo'yiladi va HAR safar hujjat sarlavhasi AYNAN o'sha tildan chiqadi; uchala sarlavha bir-biridan farq qilishi ham talab qilinadi"
  - was: Zaxira ishladimi deb `system_heartbeats` jadvaliga qarab qo'yish
    now: "test_sc3_backup_heartbeat_reaches_the_monitor_only_through_the_product_chain — SQL mahsulot faylidan (ops/backup/heartbeat.sql) o'qiladi va bog'lanish soni nazorat asserti bilan tekshiriladi; yozilishidan OLDIN /internal/self-check komponentni never_seen da ko'rsatadi, KEYIN chiqaradi. ⛔ Yurak urishini QO'LDA yozadigan xom SQL AST bilan taqiqlangan"
  - was: Tiklash mashqini eslab qo'lda yugurtirish
    now: "docker compose --profile test run --rm tests pytest tests/integration/test_restore_drill.py -q — pg_dump -> TOZA postgres:18.4 konteyneri -> pg_restore; marker `restore` standart addopts dan CHIQARILMAGAN va mezon buni pyproject.toml ni o'qib tekshiradi"
  - was: Solishtiruv varag'ini chop etib, imzo qatorlari bor-yo'qligini ko'z bilan qidirish
    now: "test_sc5_three_way_compare_separates_three_diff_classes_and_is_signed — daftar MAHSULOT MARSHRUTI orqali yuklanadi (POST /reports/compare/ledger), uch farq sinfi ALOHIDA sanaladi va compare.xlsx bayti qayta o'qilib ikki imzo qatori matn katalogidan topiladi"
  - was: Aniqlik hisobotidagi ikki xato bir xil maxrajdan chiqmaganini qo'lda hisoblab ko'rish
    now: "test_sc2_accuracy_report_comes_from_the_blind_sample_and_splits_two_error_kinds — namuna audit_draw bilan TORTILADI va shunday quriladiki, «band deb xato» O'LCHANADI, «bo'sh deb xato» esa BO'SH KATAK bo'lib qoladi; bu FAQAT maxrajlar boshqa bo'lganda mumkin"
---

# Phase 8 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> **Manba:** `08-RESEARCH.md` va `08-CONTEXT.md` (D-26, D-24) — bu fayl ulardan
> **HOSILA**, qayta yozilmaydi. Ziddiyat bo'lsa — RESEARCH.md ustun.

---

## Bu fazaning validatsiyasi nimasi bilan boshqacha — buni birinchi o'qing

7-fazada chegara birinchi marta **ochilgan** edi: xabar Telegram serverlariga
chiqardi. Bu fazada chegara yana boshqa joyda va u **ikki tomonlama**:

1. ⛔ **HUJJAT TIZIMDAN CHIQIB KETADI.** `.xlsx` fayl brauzerga tushadi,
   pochtaga biriktiriladi, USB'da yuriydi va chop etilib **imzolanadi**.
   Chiqib ketgan baytdan keyin birorta huquq darvozasi ishlamaydi. Shuning
   uchun bu fazaning o'lchovi javob KODIDA tugamaydi — u **baytlarda**
   tugaydi.

2. ⛔ **ZAXIRA — YAGONA QATLAM KI, UNING NOSOZLIGI HECH QANDAY SIGNAL
   BERMAYDI.** Yiqilgan dump, siqilgan oqim yoki `trap` ichida yozilgan
   yurak urishi — uchalasi ham «hammasi joyida» bo'lib ko'rinadi va faqat
   **falokat kuni** ma'lum bo'ladi. Shuning uchun bu yerdagi darvozalar
   xulqni emas, **zanjirning SHAKLINI** ham o'lchaydi.

Ikkala chegara ham «kelishuv» bilan yopilmaydi. Ular **bayt-tasnif**,
**AST** va **statik skan** darvozalari bilan yopiladi va ular reja tuzilganda
tasodifiy test emas, **majburiy band** bo'lgan.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Backend framework** | pytest 9.1.1 + pytest-asyncio 1.4.0 (`asyncio_mode = "auto"`), testcontainers 4.15.0 + **haqiqiy** `postgres:18.4` — ⛔ SQLite TAQIQ (RLS yo'q) |
| **Backend config** | `pyproject.toml` (ildiz) + `tests/conftest.py` — **mavjud** |
| **`bot-service` framework** | pytest + `aiogram.test_utils.mocked_bot.MockedBot`, `bot-tests` konteyneri (07-01) — **mavjud** |
| **Frontend framework** | vitest (`.test.tsx`) + `node --test` (`frontend/scripts/*.test.mjs`) |
| **Quick run command** | `npm run gate:fast` → `npm run test:fast && npm --prefix frontend test` |
| **Full suite command** | `npm run test` + `npm run test:tenancy` + `npm run bot:test` |
| **Faza darvozasi** | `npm run gate` + `tests/integration/test_phase8_criteria.py` (beshta mezon, beshta test + to'rt meta-darvoza) |
| **Yangi konteyner** | ⛔ `test_restore_drill.py` o'z ichida **ikkinchi** `postgres:18.4` konteynerini ko'taradi (`restore_target` fixture) — narx real va u `restore` markerida hujjatlangan |
| **Measured runtime** | `gate` = **1909 / 1842 s** (08-20, tinch xostda **ikki** o'lchov) · `gate:fast` = **155 / 152 s** |

### ⛔ Byudjet — O'LCHANDI (08-20, 2026-08-16) va **O'ZGARMADI**

`gate` **2300 s**, `gate:fast` **200 s** (`06-VALIDATION.md` dan meros,
`07-17` da tasdiqlangan). ⛔ **IKKALASI HAM O'ZGARMAYDI.**

⛔ **O'LCHOV, TAXMIN EMAS** — 05-15 ning W0-13 protokoli bo'yicha: **tinch
xost**, o'lchovlar `exit 0`.

| O'lchov | `gate` | `gate:fast` |
|---------|--------|-------------|
| 1 | **1909 s** (exit 0) | **155 s** (exit 0) |
| 2 | **1842 s** (exit 0) | **152 s** (exit 0) |
| Tarqoqlik | 67 s = eng yomonning **3,5 %** | 3 s = **1,9 %** |
| Byudjet | 2300 s — **zaxira 391 s (17 %)** | 200 s — **zaxira 45 s (23 %)** |

⛔⛔ **HALOLLIK BANDI — UCH EMAS, IKKI O'LCHOV OLINDI.**

05/06/07-fazalarda protokol **uch** o'lchov edi. Bu yerda **ikkitasi**
olindi va sabab texnik emas: **ijro paytida tezlik ustuvor deb
belgilandi** va uchinchi o'lchov (~32 daqiqa) boshlanmadi. Ikki
o'lchovning tarqoqligi **3,5 %** — 07-17 dagi 11,3 % dan ham tor, ya'ni
qiymat barqaror ko'rinadi; lekin ⛔ **«uch marta o'lchandi» degan da'vo
BERILMAYDI.** Agar kelajakda `gate` darvozasi byudjet sababli **yolg'on
qizil** bersa, birinchi shubha **aynan shu yerga** tushadi.

⛔ **TINCH XOST TA'MINLANDI VA U TIKLANDI.** O'lchovdan oldin xostdagi
oltita `parnikkpi-*` konteyner va qayta-qayta yiqilib turgan
`sbozor-bot-service-1` `docker stop` bilan to'xtatildi; o'lchovdan keyin
yettalasi ham `docker start` bilan **tiklandi** (05-15 va 06-14 tartibi).
Disk holati o'lchovdan oldin yozildi: `C:` **84 % to'la, 28 GB bo'sh**
(STATE.md dagi 91 % ogohlantirishidan yaxshiroq; `docker system prune`
KERAK BO'LMADI).

⚠ **O'SISH BOR VA U DEGRADATSIYA EMAS.** 07-17 da eng yomon o'lchov
1424 s edi, bugun 1909 s (**+485 s**). Sabab to'plamning o'sishi:
to'rtta yangi integratsiya fayli (`test_reports_api`, `test_three_way`,
`test_backup_heartbeat`, `test_restore_drill`), uchta yangi unit fayli,
mezon fayli (`test_phase8_criteria.py` — 30 hodisali doira va ikki
`.xlsx` zanjiri), ⛔ `test_restore_drill.py` ning **IKKINCHI postgres
konteyneri** va ikkita yangi SSG marshruti × 3 locale (frontend build).
Eng yomon o'lchov byudjetning **83 %** ini to'ldiradi.

⚠ **CHEGARA KO'TARILMADI VA BU ONGLI:** D-26 «byudjet shunchaki
oshirilmaydi» deydi va bugungi o'lchov chegara ICHIDA. Zaxira 391 s —
keyingi faza uchun tor, ya'ni qayta o'lchov **9-fazaning bandi**.

---

## Sampling Rate

- **After every task commit:** `npm run gate:fast` (byudjet 200 s)
- **After every plan wave:** rejaning O'Z `<automated>` buyruqlari + qo'shni
  to'plam (`npm run test` yoki `npm --prefix frontend test`)
- **Before `/gsd-verify-work`:** `npm run gate` to'liq yashil bo'lishi SHART
- **Max feedback latency:** 200 s (`gate:fast`)

⚠ **UCH KETMA-KET VAZIFA AVTOMATIK VERIFY'SIZ QOLMAGAN** — pastdagi
jadvalning har qatorida buyruq bor va rejalar ichidagi har vazifaning O'Z
`<automated>` bandi mos PLAN.md da hamda SUMMARY.md da yozilgan.

---

## Per-Task Verification Map

> ⚠ **GRANULYARLIK — REJA DARAJASIDA, TASK darajasida EMAS, va bu OCHIQ
> tanlov** (07-VALIDATION.md da o'rnatilgan qoida). 20 reja ~59 taskdan
> iborat va har taskning `<automated>` buyrug'i o'z rejasida hamda
> SUMMARY sida allaqachon yozilgan. Bu yerda ularni ko'chirish **ikkinchi
> haqiqat manbai** bo'lardi va u jimgina eskirardi. Quyidagi jadval har
> rejaning **darvoza buyrug'ini** beradi — ya'ni «bu reja bugun qanday
> o'lchanadi?» savoliga javob.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| P-01 | 08-01 | 1 | RECON-04 | T-08-01/02/03 | Bayt-determinik `.xlsx`: ZIP sanasi muzlatilgan, pul BUTUN so'm, o'lchanmagan son BO'SH katak | unit | `docker compose --profile test run --rm tests pytest tests/unit/test_xlsx_export.py -q` | ✅ | ✅ green |
| P-02 | 08-02 | 1 | RECON-04 | T-08-04/05/06 | `0024`/`0025`: RLS + FORCE + kompozit FK; daftar MOLIYAVIY jadval EMAS; `fn_audit_row()` `id` ustunisiz jadvalda sinmaydi | tenancy | `docker compose --profile test run --rm tests pytest tests/tenancy/test_ledger_domain_meta.py tests/tenancy/test_meta.py -q` | ✅ | ✅ green |
| P-03 | 08-03 | 1 | RECON-04, RECON-05 | T-08-09/10/11 | `REPORT_KINDS` TO'PLAM TENGLIGI bilan qulflangan; uch locale kalit-parity; klientda ikkinchi hisob YO'Q | node:test | `node --test frontend/scripts/report-copy.test.mjs` | ✅ | ✅ green |
| P-04 | 08-04 | 1 | RECON-04 | T-08-13/14/15 | Hosila so'rovlar: nol kunlar `generate_series` dan, storno MINUS, ikki anomaliya sinfi HECH QACHON qo'shilmaydi | integration | `docker compose --profile test run --rm tests pytest tests/integration/test_report_repo.py -q` | ✅ | ✅ green |
| P-05 | 08-05 | 1 | FOUND-07 | T-08-17/18/19 | Zanjirda QUVUR yo'q, `--compress=0` majburiy, yurak urishi ENG OXIRIDA va `trap` ichida EMAS, komponent nomi `alerting.BACKUP_COMPONENT` bilan bir xil | unit + config | `docker compose --profile test run --rm tests pytest tests/unit/test_backup_contract.py -q && docker compose config --quiet` | ✅ | ✅ green |
| P-06 | 08-06 | 1 | RECON-04 | T-08-23/24/25 | «Bir knob» tengligi MAHSULOT yo'lida ham rost; nomzodlar oynasi qarzdorlik reestriga mos | integration | `docker compose --profile test run --rm tests pytest tests/integration/test_bot_internal_api.py -q` | ✅ | ✅ green |
| P-07 | 08-07 | 2 | RECON-04 | T-08-26/27/28 | Uch JSON marshruti: `platform_admin` HAM 403, bitta so'rov = bitta `audit_read`, davr chegarasi uchta ALOHIDA kod, cross-tenant yopiq | integration + tenancy | `docker compose --profile test run --rm tests pytest tests/integration/test_reports_api.py tests/tenancy -q` | ✅ | ✅ green |
| P-08 | 08-08 | 2 | FOUND-07 | T-08-31/32/33 | Yurak urishi -> `/internal/self-check` -> `backup_stale` (CRITICAL); dump -> TOZA server -> moliyaviy qator, `pg_policies` va `audit_log` joyida | integration | `docker compose --profile test run --rm tests pytest tests/integration/test_backup_heartbeat.py tests/integration/test_restore_drill.py -q` | ✅ | ✅ green |
| P-09 | 08-09 | 2 | RECON-04 | T-08-35/36/37 | Davr tanlagichning maksimumi KECHA; eksport YAGONA yo'ldan, xato INLINE ko'rinadi | vitest | `npm --prefix frontend run test:component -- reports` | ✅ | ✅ green |
| P-10 | 08-10 | 2 | RECON-04 | T-08-39/40/41 | Yiqilgan so'rov «0 %» bo'lib CHIZILMAYDI; noma'lum sinf/daraja NOMLANGAN holat oladi; sana ofsetga langarlangan | vitest | `npm --prefix frontend run test:component -- reconciliation` | ✅ | ✅ green |
| P-11 | 08-11 | 2 | RECON-04 | T-08-43/44/45 | Buzuq FSM SUKUNAT bermaydi; sahifada BOZOR ko'rinadi; o'lik `FRONTEND_API_BASE_URL` kaliti OLIB TASHLANDI | bot pytest | `npm run bot:test` | ✅ | ✅ green |
| P-12 | 08-12 | 3 | RECON-04, RECON-05 | T-08-48/49/50 | To'rt `GET` eksport marshruti; ⛔ per-route bayt-tasnif XARITASI (shaxsiy/noshaxsiy); `Content-Disposition` ASCII | integration + tenancy | `docker compose --profile test run --rm tests pytest tests/integration/test_reports_api.py tests/tenancy -q` | ✅ | ✅ green |
| P-13 | 08-13 | 3 | RECON-04 | T-08-54/55/56 | Davr SERVERNIKI; yig'indi YAGONA Display; ism topilmasa BO'SH lekin NOMLANGAN | vitest | `npm --prefix frontend run test:component -- "revenue-report\|debtors-report"` | ✅ | ✅ green |
| P-14 | 08-14 | 4 | RECON-04 | T-08-58/59/60 | Daftar importi ALL-OR-NOTHING (sanoq bilan o'lchanadi), idempotent, ikki qatlamli audit; DIREKTOR ham 403 | integration | `docker compose --profile test run --rm tests pytest tests/integration/test_three_way.py -k ledger -q` | ✅ | ✅ green |
| P-15 | 08-15 | 4 | RECON-04, RECON-05 | T-08-64/65/66 | Ikki anomaliya sinfi ikki ALOHIDA sanoq; dalil kadrsiz; o'lchanmagan foiz NOL bo'lib chizilmaydi | vitest | `npm --prefix frontend run test:component -- "accuracy-block\|anomaly-archive"` | ✅ | ✅ green |
| P-16 | 08-16 | 5 | RECON-04 | T-08-69/70/71 | Uch ustun, uch farq sinfi; `null` va `0` FARQ QILADI; daftarsiz kunda javob BO'SH; imzo qatorlari filtr diapazonidan TASHQARIDA | integration | `docker compose --profile test run --rm tests pytest tests/integration/test_three_way.py -q` | ✅ | ✅ green |
| P-17 | 08-17 | 5 | RECON-04, RECON-05 | T-08-75/76/77 | `/reports` blok to'plami YOPIQ; `components/reports/**` da xom havola 0; nav byudjeti (`MOBILE_PRIMARY_COUNT`) o'zgarmadi | node:test + vitest | `node --test frontend/scripts/report-copy.test.mjs` | ✅ | ✅ green |
| P-18 | 08-18 | 6 | RECON-04 | T-08-79/80/81 | Uch sinf uch badge, «mos» BEZAKSIZ; daftar almashtirishdan OLDIN tasdiq so'raladi; `has_ledger` bo'sh javobda ROST bo'lmaydi | vitest | `npm --prefix frontend run test:component -- "compare"` | ✅ | ✅ green |
| P-19 | 08-19 | 6 | FOUND-07 | T-08-85/86/87 | Runbookning har kod blokidan keyin `**Kutilgan natija:**`; predikat NAZORAT namunasi bilan o'lchanadi | unit | `docker compose --profile test run --rm tests pytest tests/unit/test_runbook_shape.py -q` | ✅ | ✅ green |
| P-20 | 08-20 | 7 | RECON-04, RECON-05, FOUND-07 | T-08-89/90/91/92/93 | Beshala mezon BITTA buyruqda; yurak urishini qo'lda yozish va eksportni baytsiz tasdiqlash AST bilan TAQIQLANGAN; SC#3/SC#4 chegarasi docstringda LITERAL | integration | `docker compose --profile test run --rm tests pytest tests/integration/test_phase8_criteria.py -q` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Bu fazaning Wave 0 i **1-to'lqinning ichida** bajarildi (`08-01`, `08-02`,
`08-03`) va uchalasi ham yopilgan:

- [x] `services/core-api/app/services/xlsx_export.py` + `tests/unit/test_xlsx_export.py` — bayt-determinizmning YAGONA uyi (W0/A)
- [x] `migrations/versions/0024_ledger_entries.py` + `0025_notification_settings_id.py` — daftar reyestri va audit tarixi (W0/B)
- [x] `frontend/src/lib/report-queries.ts` + `frontend/scripts/report-copy.test.mjs` — klient kontrakti va uch locale (W0/C)

⛔ **YANGI FRAMEWORK O'RNATILMADI.** Bu fazada birorta yangi pip/npm paketi
qo'shilmadi (`08-RESEARCH` § Package Legitimacy Audit); yagona tashqi
artefakt — `restic/restic:0.19.1` image'i va u `08-05` Task 1 da
**bloklovchi inson tasdig'idan** o'tgan.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| REAL toza serverda REAL offsite repodan tiklash | FOUND-07 | CI'da na `restic` binari, na offsite rekvizit, na toza VPS bor; `test_restore_drill.py` FAQAT mexanizmni o'lchaydi | `08-HUMAN-UAT.md` #1 — dump olinadi, toza VPS'ga `restic restore` qilinadi, ⛔ migratsiya qayta yugurtirilib GRANT'lar tiklanadi, so'ng ilova ishga tushadi va kunlik hisobot ochiladi |
| `RESTIC_PASSWORD` ning saqlangan joyi va ikkinchi egasi | FOUND-07 | Tashkiliy fakt; bajarilmagani HECH QANDAY signal bermaydi (T-08-85) | `08-HUMAN-UAT.md` #2 — parol menejeriga yoziladi, ikkinchi odam mustaqil ochib ko'rsatadi |
| Offsite S3 hisobi va `RESTIC_REPOSITORY` (boshqa failure domain) | FOUND-07 | Byudjet/hisob qarori. ⛔ Bajarilmaguncha `backup_stale` (CRITICAL) chiqib turadi va uni o'chirish TAQIQ | `08-HUMAN-UAT.md` #3 — B2 yoki ikkinchi Contabo regioni, beshta kalit `.env` ga, birinchi tsikl kuzatiladi |
| Uch tilli yakuniy tekshiruv (kassir · nazoratchi · admin) | (SC#4) | Mexanik parity darvozada; o'lchanmagani — matnning ona tilida to'g'ri ESHITILISHI | `08-HUMAN-UAT.md` #4 — uch rol o'z oqimini uch tilda bajaradi; nuqson KALIT NOMI bilan yoziladi |
| `npm run up` ning dev mashinasida uchidan-uchiga yugurishi | (infra) | Buyruq standart compose loyihasiga tegadi va ijro muhitidagi stekni qayta yaratardi | `08-HUMAN-UAT.md` #5 — toza mashinada bir marta yugurtiriladi, beshala servis `healthy` bo'ladi |

---

## ⚠ Bu fazada takrorlangan NAQSH — sabotaj testning O'ZINI fosh qiladi

⛔ **BU BAND HUJJATLANADI, CHUNKI U BESH MARTA TAKRORLANDI VA HAR SAFAR
BIR XIL SINF EDI:** rejadagi sabotaj mahsulot nuqsonini emas, **testning
o'z ko'r nuqtasini** topdi.

| Reja | Sabotaj nima qildi | Testning yolg'on-yashili |
|------|--------------------|--------------------------|
| `08-13` | Matn da'vosi qizarmadi | `.sr-only` matni `textContent` ga qo'shilib, «ko'rinadigan matn» da'vosi ko'rinmaydigan matnni ham sanardi |
| `08-15` | Foiz da'vosi qizarmadi | «Yakka nol» asserti maxraj almashganda ham yashil qolardi |
| `08-18` | `has_ledger` da'vosi qizarmadi | Bo'sh javobda ham rost bo'lardi |
| `08-18` | `G-42(a)` qizarmadi | Skaner registr sezgir edi |
| `08-20` | 4-darvoza YOLG'ON-QIZIL berdi | Iste'molchining ta'rifi «nomni tilga oldi» edi, kerakligi «javob haqida DA'VO qildi» |

⚠ **XULOSA (05-15 ning S-D darsining beshinchi takrori):** sabotaj
o'lchovining asosiy qiymati mahsulotni emas, **o'lchov asbobini**
tekshirishda. Sabotaj sistemaga yetib borib ham hech nima qizartirmasa —
tuzatish testda emas, ⛔ **HOLATDA** yoki **PREDIKATDA**.

⚠ Reja bu naqsh uchun majburiy meta-band talab qilmagani uchun u
**qo'shilmadi**; kuzatuv `deferred-items.md` №15 da ham yozilgan.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 200s (`gate:fast`)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-08-16 (`08-20`)
