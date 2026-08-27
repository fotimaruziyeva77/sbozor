# Phase 8: Hisobotlar, mustahkamlash va ishga tushirish — Research

**Researched:** 2026-08-13
**Domain:** Davr hisobotlari + `.xlsx` eksport · zaxira/tiklash (restic + pg_dump) · 3 tomonlama solishtiruv · go-live runbook · meros qarzlarini yopish
**Confidence:** HIGH (kod bazasi bo'yicha) / MEDIUM (restic konteyner qurilishi bo'yicha — bitta empirik zond talab qiladi)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

> `08-CONTEXT.md` `<decisions>` blokidan **so'zma-so'z**. Planner bularni
> muzokara qilmaydi — ular qulflangan.

#### Hisobot yuzasi va davr modeli (RECON-04)

- **D-01**: **Yangi `/reports` bo'lim** — uch hisobot bitta joyda (tushum,
  qarzdorlik reestri, nomuvofiqlik arxivi). Mavjud `/billing` va
  `/reconciliation` sahifalari **operativ** yuzalar (bugungi ish);
  hisobotlar esa **davr bo'yicha hujjat** — ikkisini aralashtirish
  RECON-04 ning «direktor o'zi chiqarib oladi» talabini operativ ekranga
  yamash qilardi.
- **D-02**: Davr modeli: **kunlik/oylik preset + erkin `[from..to]`
  oraliq**, hammasi Asia/Tashkent **biznes-kuni** bo'yicha
  (`business_date`, 1-faza poydevori). Filtr holati URL bilan
  sinxronlanadi (`nuqs` allaqachon stekda) — hisobot havolasi
  ulashiladigan bo'ladi.
- **D-03**: ⛔ **Hisobot — HOSILA, yangi agregat jadval YO'Q.** Manba —
  mavjud yozuvlar: `daily_charges`/`payments` (tushum),
  `vendor_outstanding()` (qarzdorlik), `reconciliation_cases` +
  `billing_anomalies` (nomuvofiqlik arxivi). «Saqlangan balans/agregat
  ustuni yo'q» qoidasi (6-faza D-07, 7-faza D-06) hisobot uchun ham
  amal qiladi — ikkinchi haqiqat manbai tug'ilmaydi.
- **D-04**: ⛔ **Kassir hisobot yuzasini KO'RMAYDI.** 6-fazaning ko'r
  deklaratsiya kafolati (T-06-53/59): kassir tizim summasini ko'rmasligi
  kerak. Ruxsat direktor + bozor admini (+ platforma admini); huquq
  nomlari planner ixtiyorida, lekin `rbac.py` ↔ `rbac.ts` parity darvozasi
  (G-8) va marshrut qamrovi matritsasi majburiy.

#### Excel eksport mexanikasi (RECON-04)

- **D-05**: **Server tomonda XlsxWriter → `io.BytesIO` →
  `StreamingResponse`** (CLAUDE.md qat'iylashtirgan; openpyxl eksportda
  TAQIQ). Bayt determinizmi uchun `xlsx_template.py` dagi mavjud
  `_freeze_zip` naqshi QAYTA ISHLATILADI (02-23 darsi: ZIP sanasi soatdan
  kelib determinizmni buzadi).
- **D-06**: Eksport tili — **so'rovchining UI locale'i** (uch tilda
  sarlavha/yorliq, Babel/i18n katalogidan; atamalar vebdagi bilan BIR XIL
  — 7-faza D-30 lug'at qoidasi). Summalar **butun so'm** (`BIGINT`),
  sanalar biznes-kun. Fayl nomi deterministik:
  `{market}_{hisobot}_{from}_{to}.xlsx`.
- **D-07**: ⛔ **Sotuvchi ismi qarzdorlik reestrida SERVERDA joinlanadi —
  bu 06 `deferred-items.md` №9 ning yechimi.** Uch rad etilgan yo'l
  (hamma sahifani tortish / `?ids=` ommaviy marshrut / moliyaviy javobga
  `vendor_name` qo'shish) rad etilgancha QOLADI. Hisobot marshruti —
  **yangi, alohida sinf**: u `PERSONAL_ROUTES` reyestriga KIRMAYDI va uni
  O'STIRMAYDI (o'sha reyestr operativ moliyaviy JSON marshrutlari uchun);
  har hisobot so'rovi/eksporti **bitta** `audit_read` yozadi (kim, qaysi
  hisobot, qaysi davr) — sotuvchi boshiga emas. Shu bilan 300–1000
  rastali bozorda jurnal shovqini ham hal.
- **D-08**: Ekran ro'yxatlarining ism bo'shlig'i (07 `deferred-items.md`
  №2 — `/reconciliation` birinchi sahifa bilan cheklangan): tuzatish
  bandda yozilgan shaklda — **ism ma'lumoti hisobot yuzasining auditli
  marshrutidan yoki mavjud marshrutni sahifalab olishdan** keladi; ⛔
  nomuvofiqlik marshrutiga ism maydoni QO'SHILMAYDI (07-10 buni sabotaj
  bilan o'lchagan — to'rt tenancy testi qizaradi). Mexanika tanlovi
  planner'ga; topilmagan ism hamon **bo'sh katak** (to'qilmaydi, 05-14).

#### AI aniqlik hisoboti (RECON-05)

- **D-09**: ⛔ **YANGI hisob-kitob YOZILMAYDI.** Manba — 5-fazada qurilgan
  `services/accuracy_report.py` (Wilson, `ConfusionMatrix`,
  `AccuracyReport`) va uning mavjud API yuzasi. Bu faza faqat: (a)
  direktor `/reports` yuzasiga chiqaradi, (b) `.xlsx` eksport qo'shadi,
  (c) davr tanlovini ulaydi. Ikki xato turi formulasi o'zgarmaydi:
  «band deb xato» = fp/(tp+fp), «bo'sh deb xato» = fn/(tp+fn) — foiz
  KLIENTDA qayta hisoblanmaydi (05-14 qarori).
- **D-10**: ⛔ **O'lchanmagan son chizilmaydi** (05-13/05-14 naqshi):
  ko'r namunasi bo'sh davr uchun «0 %» emas — qator/blok umuman
  chiqmaydi yoki «o'lchov yo'q» holati ochiq aytiladi. 07 ko'rigining
  **WR-05** bandi (yiqilgan so'rov «0 %» bo'lib chiziladi) shu fazada
  AYNAN shu qoida bilan yopiladi.
- **D-11**: Hisobot AI-02 ning Blocked holatini **yashirmaydi**: modelning
  CI'da o'lchangan aniqligi yo'qligi (oltin to'plam bo'sh) hisobot
  sahifasida holat sifatida ko'rinadi — mexanika yashilligi bilan aniqlik
  yo'qligini yopish taqiqlangan (5-faza D-01 merosi).

#### Backup va tiklash mashqi (FOUND-07)

- **D-12**: Vosita: **`pg_dump -Fc` + restic** (CLAUDE.md qat'iy tanlovi),
  obyekt-ombor uchun SeaweedFS hajmining restic/rclone ko'zgusi. Retention:
  `--keep-daily 14 --keep-weekly 8 --keep-monthly 12 --prune`.
- **D-13**: **Alohida compose xizmati** (`backup`) — host cron EMAS.
  Sabab: compose ichida bo'lsa O'zbekiston hostingiga ko'chish (
  data-rezidentlik constraint'i) sozlama ko'chishi bo'ladi; host cron esa
  hujjatlashtirilmagan qo'l ishi. Kunlik jadval konteyner ichida.
- **D-14**: Offsite manzil — **sozlanadigan S3-mos endpoint** (env
  orqali; standart tavsiya: Backblaze B2 yoki ikkinchi Contabo region —
  VPS bilan BOSHQA failure domain). Qiymat `[ASSUMED]` standart bilan
  kodda sabab izohi ostida; hech qanday sir compose fayliga yozilmaydi.
- **D-15**: ⛔ **Muvaffaqiyatning YO'QLIGI alert beradi** (CLAUDE.md:
  «alert on absence of a success signal»). Mexanizm — mavjud
  `system_heartbeats` + `EXPECTED_COMPONENTS` + `alerting::watched`
  naqshi (7-faza D-17 sinfi): `backup` komponenti reyestrga kiradi,
  `ALERT_META` yozuvi va uch locale matni bilan. Backup konteynerining
  heartbeat yozish yo'li (ichki endpoint vs to'g'ridan DB) — planner
  ixtiyorida; talab: ro'yxatga olinmagan/o'lgan backup JIMGINA qolmaydi.
- **D-16**: Tiklash mashqi **IKKI qatlam**: (a) CI-o'lchanadigan mexanizm
  — dump toza Postgres konteyneriga `pg_restore` qilinadi va smoke
  tekshiruv o'tadi (self-service qoidasi 3: tekshiruv simulyator ustida);
  (b) **real toza serverda bir martalik hujjatlashtirilgan mashq** —
  `08-HUMAN-UAT.md` bandi, egasi Ops, tetigi VPS. SC#3 ning «kamida bir
  marta muvaffaqiyatli» da'vosi (b) bilan imzolanadi, (a) esa uni
  regressiyadan qo'riqlaydi.

#### 3 tomonlama solishtiruv vositasi (SC#5)

- **D-17**: Daftar ma'lumotining kirishi — **xlsx import** (2-fazaning
  import infratuzilmasi QAYTA ISHLATILADI: shablon → xavfsiz o'qish →
  validatsiya → all-or-nothing). Kunlik bitta fayl: rasta kodi + daftar
  summasi. Qo'lda forma rad etildi — 300–1000 rasta uchun kunlik forma
  amaliy emas va import yo'li allaqachon o'lchangan.
- **D-18**: Uch ustunning manbalari: **daftar** (import qatori) vs
  **tizim** (`daily_charges` + `payments`) vs **AI-kutilgan** (bandlik
  hosilasi: band rasta × amaldagi tarif). AI-kutilgan **hosila,
  saqlanmaydi** (D-03 sinfi). Farqlar rasta kesimida ko'rinadi.
- **D-19**: Chiqish — kunlik solishtiruv **ekran + `.xlsx`**; «imzolanadi»
  = chop etishga mos eksportning pastida **imzo qatorlari** (bajaruvchi:
  nazoratchi/admin; tasdiqlovchi: direktor). Raqamli imzo YO'Q — bu
  qog'oz jarayon, build emas.
- **D-20**: ⛔ **Bajaruvchi — nazoratchi yoki admin, KASSIR EMAS**
  (ROADMAP Post-Launch bo'limi qat'iy aytadi) — RBAC shunga mos: kassir
  bu yuzani ham ko'rmaydi (D-04 bilan izchil).
- **D-21**: Import jadvali yangi migratsiyada, mavjud naqsh bilan:
  `market_id` + RLS `ENABLE`+`FORCE` + tenant policy + kompozit FK; ⛔
  yangi `SECURITY DEFINER` funksiya YO'Q (`DEFINER_SURFACES = ()` bo'sh
  qoladi, T-06-22).

#### Go-live runbook, 3 til va mustahkamlash qarzlari (SC#4)

- **D-22**: Runbook — `ops/docs/go-live.md` (mavjud `monitoring.md` /
  `nvr-onboarding.md` yoniga). Mazmuni: VPS deploy tartibi, WireGuard/
  CAM-02 yopilishi, birinchi backup + tiklash tasdig'i, `npm run up`
  qo'lda tasdiqlash (07 `deferred-items.md` №5 ning ochiq qismi),
  cutover sanasi qoidasi (2–4 hafta, cho'zilmaydi), rollback yo'li.
  Ochiq HUMAN-UAT bandlari (03/04/05/07) **bitta go-live oldi
  ro'yxatiga** jamlanadi — har biri egasi va tetigi bilan.
- **D-23**: Uch tilli yakuniy tekshiruv: mexanik parity allaqachon
  darvozada (`i18n:check`); bu faza qo'shadigani — **inson o'qishi**
  (kassir/nazoratchi/admin mashqi bilan birga `08-HUMAN-UAT.md` bandi).
  Yangi mexanik darvoza yozilmaydi — mavjudi yetarli.
- **D-24**: **Mustahkamlash qarzlari QAMROVDA** — egasi «8-faza» deb
  yozilgan bandlar rejalarga kiradi:
  - 07 №4: `market_notification_settings` ga `id uuid` ustuni
    (migratsiya) + `AUDITED_TABLES` ga kiritish — yechim shakli
    docstringda allaqachon nomlangan; `fn_audit_row()` O'ZGARMAYDI.
  - 07 №1-qo'shimcha: `alert-list.test.tsx` 07-14 ning to'rt kalitini
    RENDER holida o'lchaydi (G-36 mavjudlikni qo'riqlaydi, chizilishni
    emas).
  - 07 №7a — 13 ta WR (backend WR-04/06/09; frontend WR-02/03/04/05/07/
    11/12/13/14/15): har biri kichik, aniq nomlangan tuzatish; birortasi
    jimgina tashlab yuborilmaydi — kirmasa sababi yoziladi.
  - 07 №7b — Info bandlari (IN-01…IN-08, IN-05 dan tashqari — u 07-22 da
    yopilgan): mustahkamlash to'lqiniga mayda bandlar sifatida.
  - 06 №9 — D-07 orqali yopiladi (hisobot yuzasi).
- **D-25**: **07 №6 (dayjest alert kaliti BITTA) KENGAYTIRILMAYDI** —
  bandning o'z tahlili yetarli deb topdi: operator faktni bitta kalit
  bilan oladi, QAYSI dayjest ekani `/internal/self-check` da nomma-nom.
  Amaliyotda ehtiyoj chiqsa — V2.
- **D-26**: `gate` byudjeti **2300 s / `gate:fast` 200 s** (06-VALIDATION)
  o'zgarmaydi — bu fazaning yangi testlari shu byudjet ichiga sig'ishi
  kerak; sig'masa, chegara ko'tarish faqat TINCH XOSTDAGI uch o'lchov va
  sabab bilan (05/06-faza tartibi).

### Claude's Discretion

Quyidagilar **rejalashtirish va tadqiqotga** qoldiriladi — implementatsiya
tafsiloti, foydalanuvchi qarori emas: hisobot huquq(lar)ining nomi;
jadval/ustun/endpoint nomlari; xlsx ustun tartibi va format tafsiloti;
backup konteynerining bazaviy image'i va heartbeat yozish mexanikasi
(ichki endpoint vs DB); solishtiruv hisobotining sahifalash usuli; 13 WR
ning rejalarga taqsimlanish tartibi; restic vs rclone taqsimoti
(Postgres restic'da — qat'iy; SeaweedFS ko'zgusi uchun tanlov erkin).

### Deferred Ideas (OUT OF SCOPE)

- **Direktor botining buyruq yuzasi** (7-fazadan meros deferred) — V2.
- **Sotuvchi botidan to'lov / da'vo** — V2.
- **07 №6: dayjest alert kalitini ikkiga bo'lish** — amaliy ehtiyoj
  chiqsa V2 (D-25 sababi bilan).
- **To'liq interaktiv plan-xarita (react-konva)** — v2 (ROADMAP qarori).
- **Kassir offline-lite** (`V2-CASH-05`) — V2.
- **AI-02 ning to'liq yopilishi** (real ONNX + oltin to'plam + aniqlik
  o'lchovi) — `05-HUMAN-UAT.md` #1–#3, egasi nazoratchi + Ops; bu faza
  faqat holatni halol KO'RSATADI (D-11).
- **Phase 0 baza varaqalarini solishtiruvga ulash** — ma'lumot kelganda
  operatsion amal; vosita usiz ham to'liq ishlaydi.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description (REQUIREMENTS.md) | Research Support |
|----|-------------------------------|------------------|
| **RECON-04** | Davr bo'yicha hisobotlar: tushum (kunlik/oylik), qarzdorlik reestri, nomuvofiqlik arxivi — har biri Excel (`.xlsx`) yuklab olinadi | § Architecture Patterns — Pattern 1 (hosila davr so'rovi), Pattern 2 (bayt-determinik eksport moduli), Pattern 3 (bayt marshrutning tasnif darvozasi); § Code Examples 1–3; § Common Pitfalls 1, 2, 3, 13, 14 |
| **RECON-05** | AI aniqlik hisoboti: ko'r audit namunasidan, xatolik turlari ajratilgan | § Standard Stack — `accuracy_report.py` + `GET /occupancy/accuracy` MAVJUD; § Don't Hand-Roll qatori 1; § Common Pitfalls 12 (o'lchanmagan son) |
| **FOUND-07** | Kunlik avtomatik backup (Postgres + obyekt-ombor) boshqa lokatsiyaga; tiklash mashqi kamida bir marta o'tkazilgan | § Standard Stack — restic 0.19.1 (verified); § Architecture Patterns Pattern 4–5; § Code Examples 4–6; § Common Pitfalls 5–11; § Validation Architecture (ikki qatlamli tiklash isboti) |

**⚠ Uchala band ham hozir `Pending`.** Fazaning `Done` belgisi — talab
MATNI bo'yicha (REQUIREMENTS.md 188-satrdagi qoida): har jumla o'lchangan
test bilan qoplangan bo'lsa. FOUND-07 ning ikkinchi jumlasi («tiklash
mashqi kamida bir marta o'tkazilgan») **CI'da to'liq bajarilmaydi** —
u D-16(b) bilan `08-HUMAN-UAT.md` ga chiqadi. Bu 3- va 5-fazaning shakli
va u ochiq aytiladi: `Done` faqat mashq HUJJATLASHTIRILGANIDAN keyin.
</phase_requirements>

---

## Summary

Bu faza **yangi mahsulot qurmaydi — mavjudini yuzaga chiqaradi va qulflaydi.**
Tadqiqotning birinchi va eng muhim topilmasi shu: RECON-05 ning butun
arifmetikasi (`accuracy_report.py`, Wilson, ikki xato turi) **allaqachon
yozilgan va API yuzasi ham mavjud** (`GET /occupancy/accuracy`), FOUND-07 ning
kuzatuv yarmi ham **allaqachon qurilgan** (`BACKUP_COMPONENT = "backup"`
`alerting.py:177` da, `backup_stale` `ALERT_META` da, `("backup",
"backup_stale")` `_platform_signals::watched` da, `"backup"`
`EXPECTED_COMPONENTS` da). Ya'ni bugun tizim zaxira **yo'qligini** ko'radi;
yetishmayotgani — zaxiraning O'ZI va uning yurak urishini yozadigan jarayon.

Ikkinchi topilma — **fazaning haqiqiy xavfi kod yozishda emas, mexanik
darvozalarda.** Bu repo yetti faza davomida o'z-o'zini qo'riqlaydigan
darvozalar to'plamini yig'di va ularning **oltitasi** yangi hisobot
marshruti / eksport / migratsiya qo'shilganda **darhol qizaradi**. Ularning
uchtasi «tuzatish» sifatida darvozani bo'shatishga vasvasa qiladi va
o'shanda faza o'zi qo'riqlashi kerak bo'lgan narsani buzadi. Eng o'tkiri:
`.xlsx` eksporti `response_model` bermaydi, ya'ni u `tests/tenancy/
test_personal_data_coverage.py::binary_routes()` ga tushadi, u yerda
`BINARY_PERSONAL_ROUTES` ning **hozirgi assertioni ruxsat etilgan
huquqlarni `{CAMERA_VIEW, OCCUPANCY_REVIEW}` bilan cheklaydi** —
`REPORT_VIEW` u yerga sig'maydi. Darvozani KENGAYTIRISH kerak (per-route
ruxsat xaritasi), BO'SHATISH emas.

Uchinchi topilma — **CONTEXT.md ning bitta texnik da'vosi noto'g'ri**:
D-05 «`xlsx_template.py` dagi mavjud `_freeze_zip`» deydi, aslida
`_freeze_zip` **faqat `tests/fixtures/karmana_seed.py:679`** da yashaydi
va mahsulot eksport yo'lida (`build_template`, `build_error_report`) bayt
determinizmi **umuman yo'q**. Qaror o'zgarmaydi (determinizm kerak), lekin
ish hajmi boshqa: naqsh test fikstursidan **mahsulot moduliga ko'chiriladi**
va ikkala chaqiruvchi (import shabloni + yangi hisobot eksporti) unga
o'tadi.

**Primary recommendation:** `/reports` ni **yangi API moduli + yangi
frontend marshruti** sifatida quring; barcha uch hisobotni MAVJUD
jadvallardan **hosila SQL** bilan oling (yangi agregat jadval yo'q);
`_freeze_zip` ni `app/services/xlsx_export.py` ga ko'chirib ikkala eksport
yo'lini shunga bog'lang; `backup` ni **`postgres:18.4-trixie` bazasidagi
o'z image'i** qilib quring (`pg_dump`/`pg_restore`/`psql` shu yerda,
`restic` binari `restic/restic:0.19.1` dan `COPY --from` bilan olinadi),
kunlik jadvalni **idempotent 10-daqiqalik tsikl** bilan yuriting va uning
holatini **`system_heartbeats['backup']` qatorining O'ZIDAN** o'qing —
shunda «bugun bajarildimi?» va «alert kerakmi?» savollari BITTA haqiqat
manbaidan javob oladi.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Davr agregatsiyasi (tushum · qarzdorlik · nomuvofiqlik) | **API / Backend (SQL)** | — | D-03: hosila; pul arifmetikasi hech qachon klientda (06-faza WR-06 aynan shu buzilish edi) |
| `.xlsx` bayt hosil qilish | **API / Backend** | — | D-05 qat'iy; klient-tomon eksport formula-injection himoyasini (`escape_formula`) yo'qotardi |
| Hisobot filtr holati (`from`/`to`, preset) | **Browser / Client** | Frontend Server (SSG) | D-02: `nuqs` URL sinxroni — havola ulashiladi; SSG uchala locale'da build bo'ladi |
| Aniqlik foizlari va Wilson oraliqlari | **API / Backend** | — | 05-14 qulflagan: klient qayta hisoblasa IKKINCHI JAVOB tug'ilardi (5,4 % vs 3,8 %) |
| Aniqlik hisobotining «o'lchanmagan» holati | **API / Backend** | Browser (chizmaslik) | `measured=False` + `null` maydonlar serverdan; klient faqat CHIZMAYDI (D-10) |
| Ism joini (qarzdorlik reestrida) | **API / Backend (SQL JOIN)** | — | D-07: 06 №9 ning yechimi; klient-joini 50 sahifa chegarasiga qadalgan |
| Zaxira olish (dump + arxiv) | **Yangi `backup` konteyneri** | — | D-13: compose ichida, host cron emas; `pg_dump` core-api image'ida YO'Q |
| Zaxiraning YO'QLIGINI aniqlash | **API / Backend worker (`alert_sweep`)** | `core-api` (`/internal/self-check`) | ⛔ ALLAQACHON QURILGAN — bu faza faqat yurak urishini YOZADI |
| Zaxira jadvalining holati («bugun bo'ldimi?») | **Database (`system_heartbeats`)** | `backup` konteyneri | Konteyner xotirasi restart'da yo'qoladi; bazadagi qator — yagona restart-chidamli holat |
| Tiklash isboti — mexanizm | **CI (testcontainers)** | — | D-16(a); `tests` konteynerida docker soketi bor (`compose.yaml:1025`) |
| Tiklash isboti — haqiqat | **Human / Ops** | — | D-16(b) → `08-HUMAN-UAT.md`; toza server CI'da yo'q |
| Daftar (`.xlsx`) qabul qilish | **API / Backend (import quvuri)** | — | D-17: `_read_bounded` → `xlsx_reader` → validator → all-or-nothing |
| 3 tomonlama farq hisobi | **API / Backend (hosila so'rov)** | — | D-18: AI-kutilgan saqlanmaydi |
| Imzo qatorlari | **Eksport hujjati (xlsx)** | — | D-19: qog'oz jarayon, raqamli imzo YO'Q |
| Go-live runbook | **Docs / Ops** | — | D-22: `ops/docs/go-live.md`, `monitoring.md` naqshida |
| Uch tilli yakuniy tekshiruv | **Human** | CI (`i18n:check` mavjud) | D-23: yangi mexanik darvoza YOZILMAYDI |

---

## Discretion qarorlari (CONTEXT.md «Claude's Discretion» — har biriga BITTA javob)

| # | Discretion bandi | Tavsiya | Sabab (bir jumlada) |
|---|---|---|---|
| **R-1** | Hisobot huquqining nomi | **`REPORT_VIEW` ni QAYTA ISHLATING, yangi huquq YOZMANG** | U allaqachon `director` + `market_admin` da (aynan D-04 ning ikkitasi), `/occupancy`, `/billing`, `/reconciliation` uni ishlatadi va yangi huquq `rbac.py`↔`rbac.ts`↔`role-gate.test.mjs` uchligini uch joyda o'stirardi. ⚠ **Platforma adminida `REPORT_VIEW` YO'Q** — D-04 ning «(+ platforma admini)» qismi ONGLI QAROR talab qiladi (§ Common Pitfalls 11). |
| **R-2** | Marshrut/modul nomlari | `app/api/v1/reports.py`, prefiks `/api/v1/reports`, uchta JSON + uchta eksport: `/revenue`, `/receivables`, `/discrepancies` (+ `.xlsx` variantlari) va `/three-way` (SC#5) | Prefiks bo'yicha yopiq to'plam darvozasi (`test_route_coverage.py::test_the_reconciliation_surface_is_exactly_six_routes` naqshi) shu shaklda yoziladi. |
| **R-3** | Eksport marshrutining metodi | ⛔ **`GET`, `POST` EMAS** — `?format=xlsx` ham EMAS, alohida `.xlsx` yo'l | `POST` bayt-marshrut tasnif darvozasidan (`get_routes()` faqat `GET` ni yuradi) **jimgina chetlab o'tardi** — ya'ni «darvozani chetlash» yechimi bo'lardi. `?format=` esa bitta marshrutda ikki javob turini beradi va `response_model` ni yolg'on qilardi. |
| **R-4** | Jadval/ustun nomlari (daftar importi) | `ledger_entries` (`market_id`, `business_date`, `stall_id`, `amount_soum BIGINT`, `imported_by`, `created_at`) + `UNIQUE(market_id, business_date, stall_id)` | «Daftar» — kunlik, rasta kesimida bitta qiymat (D-17); UNIQUE takroriy importni idempotent qiladi. |
| **R-5** | xlsx ustun tartibi va format | Har hisobot: 1-varaq = ma'lumot, sarlavha `freeze_panes(1,0)` + `autofilter`; pul ustunlari `write_number` + `num_format "#,##0"`; sana `write_string` ISO (`yyyy-mm-dd`) | `build_error_report()` ning mavjud shakli; ISO sana WR-07 ning (uch faylda uch xil sana) takrorlanishini oldini oladi. |
| **R-6** | Backup image bazasi | **`postgres:18.4-trixie` + `COPY --from=restic/restic:0.19.1 /usr/bin/restic`** | `pg_dump` MAJOR versiyasi serverdan kichik bo'lolmaydi; alpine v3.22 da `postgresql18-client` YO'Q (faqat `edge`); restic binari `CGO_ENABLED=0` bilan quriladi (static) — Debian'ga ko'chadi. |
| **R-7** | Heartbeat yozish mexanikasi | **To'g'ridan DB — `psql` bilan `INSERT … ON CONFLICT (component) DO UPDATE`** | `system_heartbeats` da `grant_app_dml` bor (0014-migratsiya:625), jadval GLOBAL (RLS yo'q), ya'ni `sbozor_app` roli yetadi; ichki HTTP endpoint yangi marshrut + yangi autentifikatsiya sirini talab qilardi va `test_route_coverage` matritsasini o'stirardi. |
| **R-8** | Solishtiruv hisobotining sahifalash usuli | ⛔ **Sahifalash YO'Q — bitta kun, bitta javob, qat'iy chegara bilan** (`stalls` soni ≤ `settings.import_max_rows`) | 3 tomonlama solishtiruv KUNLIK va u chop etiladi/imzolanadi (D-19): sahifalangan hujjatni imzolab bo'lmaydi. Chegara `422` bilan rad etadi (import yo'lidagi naqsh). |
| **R-9** | restic vs rclone taqsimoti | **Ikkalasi ham restic**: Postgres `--stdin-from-command` bilan, SeaweedFS hajmi `:ro` mount qilingan katalog sifatida | Ikkinchi vositani qo'shish ikkinchi sir to'plami, ikkinchi retention siyosati va ikkinchi «muvaffaqiyat» ta'rifini tug'dirardi; restic ikkalasini BITTA repoda, BITTA `forget --prune` bilan boshqaradi. ⚠ `rclone` alternativasi va uning aniq foydasi § Alternatives Considered da. |
| **R-10** | Zaxira vaqti | **04:40 Asia/Tashkent** | `billing_close` (04:10) dan KEYIN — dump kechagi kunning YOPILGAN hisobini o'z ichiga oladi; `retention` (03:20) obyektlarni JOYIDA qayta yozadi, ya'ni undan oldin olingan arxiv darhol eskirardi; kadr olish oynasi (06:00–08:00, 16:00, 18:00) tegilmaydi. |
| **R-11** | Daftar import shabloni | ⛔ `TEMPLATE_KINDS` ga **to'rtinchi a'zo qo'shing va `test_template_kinds_are_exactly_three` ni ONGLI ravishda yangilang** (nomi bilan: `..._are_exactly_four`) | Alohida shablon yuzasi qurish ikkinchi `build_template` nusxasini tug'dirardi; darvozani yangilash ONGLI (test nomi sonni aytadi), chetlash esa JIMGINA bo'lardi. |
| **R-12** | 13 WR ning taqsimoti | Uch to'lqin: **(a) backend WR-04/06/09** — hisobot/qarzdorlik ishi bilan bir rejada (WR-09 aynan qarzdorlik yuzasiga tegishli); **(b) frontend WR-05/07/11/12/13/15 + IN-02/03/04/06/08** — bitta «frontend mustahkamlash» rejasi; **(c) bot WR-02/03/04 + IN-01/07** — bitta «bot mustahkamlash» rejasi; **WR-14 + IN-05** — infra/copy, istalgan to'lqinga | Fayl to'plamlari kesishmaydi → parallel to'lqin mumkin; WR-05 aynan D-10 ning qoidasi bilan yopiladi, ya'ni u hisobot ishiga bog'langan. |

---

## Project Constraints (from CLAUDE.md)

| # | Direktiv | Bu fazaga ta'siri |
|---|---|---|
| C-1 | **Aynan 3 servis** (core-api, cv-service, bot-service) | `backup` — **to'rtinchi servis EMAS**: u `db`, `cache`, `storage`, `nginx`, `go2rtc` bilan bir toifada (tayyor image + bizning skript). Bu farq compose izohida LITERAL yozilishi kerak (`storage` blokidagi 63–66-qatorlar naqshi). |
| C-2 | **`XlsxWriter` faqat YOZADI, `openpyxl` faqat O'QIYDI** | Hisobot eksporti — `XlsxWriter`; daftar importi — `xlsx_reader` (u `openpyxl` ustida). Rollar ALMASHTIRILMAYDI. |
| C-3 | **restic 0.19.1 + `pg_dump -Fc`, retention `--keep-daily 14 --keep-weekly 8 --keep-monthly 12 --prune`** | D-12 bilan aynan bir xil; qiymatlar kodda LITERAL va testda qulflanadi. |
| C-4 | **`restic check --read-data-subset` HAFTALIK + tiklash mashqi DELIVERABLE** | Haftalik `check` — `backup` tsiklining ikkinchi shoxi; mashq — `08-HUMAN-UAT.md`. |
| C-5 | **«Alert on ABSENCE of a success signal»** | D-15 bilan aynan; mexanizm mavjud (`_platform_signals` da `last_seen is None` ham eskirish). |
| C-6 | **`float` for money TAQIQ — `BIGINT` so'm ↔ Python `int`** | Hisobot agregatlari `sum(...)::bigint`; xlsx ga `write_number` bilan **butun son** yoziladi. |
| C-7 | **Naive datetime TAQIQ; `TIMESTAMPTZ` + `ZoneInfo` + `tzdata`** | Davr chegaralari `business_date` (DATE) bo'yicha; `backup` konteyneriga `TZ: Asia/Tashkent` majburiy. |
| C-8 | **Data-rezidentlik: O'zbekiston hostingiga ko'chish rejalashtirilgan** | Backup manzili **env orqali sozlanadigan S3** (D-14) — endpoint URL o'zgarishi kod o'zgarishi bo'lmasligi kerak. |
| C-9 | **Multi-tenant: hamma jadvalda `market_id` + RLS** | `ledger_entries` — D-21 naqshi (`enable_tenant_rls` + tenant policy + kompozit FK). |
| C-10 | **Audit jurnali majburiy** | Har hisobot so'rovi/eksporti BITTA `audit_read` (D-07). |
| C-11 | **UI: Apple-uslub minimal, 3 til majburiy** | `/reports`: davr tanlash → ko'rish → bitta bosishda `.xlsx` (≤3 qadam). |

---

## Standard Stack

### Core — ⛔ YANGI PAKET YO'Q

| Library / Image | Version | Purpose | Why Standard |
|---|---|---|---|
| `XlsxWriter` | **3.2.9** (o'rnatilgan) | Uchala hisobot + solishtiruv eksporti | CLAUDE.md qat'iy tanlovi; `app/services/xlsx_template.py` allaqachon ishlatadi (`escape_formula` bilan) |
| `openpyxl` + `defusedxml` | 3.1.5 / 0.7.1 (o'rnatilgan) | Daftar `.xlsx` ni O'QISH (`xlsx_reader` orqali) | O'qish roli faqat unda; XML/ZIP bomba himoyasi `xlsx_reader` da |
| `SQLAlchemy` `text()` + `bindparam` | 2.0.51 (o'rnatilgan) | Hosila davr so'rovlari | `billing_repo` / `reconciliation_repo` ning butun uslubi shu |
| `nuqs` | 2.9.2 (o'rnatilgan) | `/reports` filtr holati URL'da | `cameras/page.tsx`, `map/page.tsx`, `billing/page.tsx` da mavjud naqsh |
| `postgres` image | **18.4-trixie** (xostda MAVJUD) | `pg_dump` · `pg_restore` · `psql` — backup konteynerining bazasi | Server bilan AYNAN bir major; image allaqachon tortilgan (`docker images` tasdiqladi) |
| `restic` | **0.19.1** (2026-07-05) | Shifrlangan, deduplikatsiyalangan offsite zaxira | CLAUDE.md qat'iy tanlovi; Docker Hub API bilan tasdiqlandi: `restic/restic:0.19.1` mavjud, `latest` ham o'sha kuni push qilingan |
| `testcontainers` | 4.15.0 (o'rnatilgan) | D-16(a) tiklash mashqi CI'da | `tests` konteynerida docker soketi bor (docker-outside-of-docker) |

**⚠ `pip install` / `npm install` bandi BU FAZADA YO'Q.** Uchala talab ham
mavjud paketlar bilan bajariladi. Yangi narsa — **bitta Docker image
qatlami** (`ops/backup/Dockerfile`) va **bitta shell skripti**.

### Supporting — mavjud mexanizmlar (qayta ishlatiladi)

| Mexanizm | Fayl | Nima uchun kerak |
|---|---|---|
| `accuracy_report()` · `ConfusionMatrix` · `wilson_interval()` | `app/services/accuracy_report.py` | ⛔ RECON-05 ning YAGONA hisob manbai (D-09). Ikki xato maxraji `test_matrix_matches_the_ui_spec_worked_example` bilan qulflangan |
| `GET /occupancy/accuracy` (`from`/`to` bilan) | `app/api/v1/occupancy.py:162` | Davr parametrlari ALLAQACHON bor va docstring aynan «kelajakdagi eksport uchun» deydi (86–97-qatorlar) |
| `vendor_outstanding(session, market_id, vendor_ids, as_of)` | `app/repositories/billing_repo.py:1023` | Qarzdorlik reestrining arifmetikasi — hisoblanadigan qoldiq, saqlangan balans YO'Q |
| `escape_formula()` + `_write_text()` | `app/services/xlsx_template.py:216, 469` | ⛔ OWASP formula-injection himoyasi — **har yangi eksport shu yordamchidan o'tishi SHART** |
| `_xlsx_response()` (`StreamingResponse` + `Content-Disposition`) | `app/api/v1/imports.py:629` | Eksport javobining tayyor shakli |
| `_read_bounded()` → `xlsx_reader.read_rows()` → validator | `app/api/v1/imports.py:507, 546, 566` | Daftar importining uch darvozasi (D-17) |
| `TenantSessionDep` (tranzaksiya + all-or-nothing) | `app/deps.py` | D-14 (2-faza) tekin keladi — ichki blok OCHILMAYDI |
| `audit_read(TABLE, reason=…)` | `app/security/audit.py` | D-07 ning mexanizmi; `audit_resource` introspektsiya tegi darvozalar tomonidan o'qiladi |
| `BACKUP_COMPONENT` · `backup_stale` · `watched` · `EXPECTED_COMPONENTS` | `app/jobs/alerting.py:177,313,682`; `app/api/internal/self_check.py:112` | ⛔ **HAMMASI ALLAQACHON QURILGAN** — bu faza faqat yurak urishini YOZADI |
| `enable_tenant_rls()` · `grant_app_dml()` · kompozit FK naqshi | `migrations/helpers.py:166,177` | D-21 migratsiyasining tayyor asboblari |
| `_freeze_zip()` | ⚠ `tests/fixtures/karmana_seed.py:679` — **mahsulotda YO'Q** | D-05 ning determinizmi; ko'chirilishi kerak (§ Pitfall 3) |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|---|---|---|
| restic (SeaweedFS uchun) | `rclone sync` S3→S3 | rclone obyekt darajasida ishlaydi, ya'ni tiklash boshqa S3 provayderiga TO'G'RIDAN-TO'G'RI bo'ladi (O'zbekiston migratsiyasi uchun qulay). ⛔ Lekin: shifrlash yo'q (crypt remote qo'shilmasa), versiyalash yo'q, ikkinchi sir to'plami va ikkinchi «muvaffaqiyat» ta'rifi. **restic tavsiya etiladi**; rclone — agar Ops offsite bucketni to'g'ridan-to'g'ri o'qiy olishni talab qilsa |
| `postgres:18.4-trixie` bazasi | `restic/restic:0.19.1` + `apk add postgresql18-client` | ⛔ **Ishlamaydi bugungi tegda**: `postgresql18-client` Alpine `edge` da bor, `v3.22` da YO'Q (pkgs.alpinelinux.org bilan tasdiqlandi). `alpine:latest` qaysi shoxda ekani vaqtga bog'liq — bu tanlov mo'rt |
| `postgres:18.4-trixie` bazasi | `apt-get install restic` (Debian trixie) | Debian repo'sidagi restic CLAUDE.md pinidan (0.19.1) eskiroq va u `--stdin-from-command` ni bermasligi mumkin |
| Konteyner ichida `cron` | `supercronic` (aptible, MIT) | Yangi tashqi bog'liqlik va yangi litsenziya bandi; **tavsiya: bash tsikli + DB holati** (§ Pattern 4) — u restart-chidamli va u YANGI PAKET talab qilmaydi |
| Bash tsikli | Debian `cron -f` | `cron` konteyner restartida «o'tkazib yuborilgan» yugurishni QAYTARMAYDI; bizning tsikl `system_heartbeats` dan «bugun bo'lganmi?» ni o'qiydi, ya'ni 05:00 dagi restart kunni yo'qotmaydi |
| Heartbeat: `psql` | Yangi `POST /internal/heartbeat` | Yangi marshrut + yangi sir + `test_route_coverage` matritsasi + `EXEMPT_ROUTES` yozuvi. `psql` yo'li NOL yangi yuza ochadi |
| `pg_dump -Fc` (standart siqish) | `pg_dump -Fc -Z0` + restic siqishi | ⛔ **`-Z0` MAJBURIY** — siqilgan dump restic'ning deduplikatsiyasini butunlay o'ldiradi (§ Pitfall 6) |

**O'rnatish (yangi paket yo'q — faqat image qatlami):**

```dockerfile
# ops/backup/Dockerfile
FROM postgres:18.4-trixie
# restic 0.19.1 — CGO_ENABLED=0 bilan qurilgan STATIC Go binari
# (build.go:141,165 — cgo faqat `--enable-cgo` bilan yoqiladi),
# ya'ni alpine'da qurilgani Debian'da ham ishlaydi.
COPY --from=restic/restic:0.19.1 /usr/bin/restic /usr/local/bin/restic
COPY ops/backup/ /opt/backup/
RUN chmod +x /opt/backup/*.sh
ENTRYPOINT ["/opt/backup/loop.sh"]
```

⚠ `COPY --from` static-binary da'vosi manbadan o'qildi (`build.go`), lekin
**bitta empirik zond talab qiladi**: `docker run --rm <image> restic version`.
Bu Wave 0 ning bir qatorlik bandi bo'lishi kerak — muqobil yo'l
(`ADD https://github.com/restic/restic/releases/download/v0.19.1/restic_0.19.1_linux_amd64.bz2`)
tayyor tursin.

---

## Package Legitimacy Audit

> Bu fazada **birorta yangi pip/npm paketi o'rnatilmaydi**, shuning uchun
> `slopcheck install` uchun nomzod yo'q. Auditi qilinadigan narsa — **Docker
> image'lar**. Ular registry API'lari bilan to'g'ridan-to'g'ri tekshirildi.

| Artefakt | Registry | Yosh / oxirgi push | Manba repo | Tekshiruv | Disposition |
|---|---|---|---|---|---|
| `restic/restic:0.19.1` | Docker Hub | **2026-07-05** (39 kun) | github.com/restic/restic (BSD-2) | Docker Hub v2 API bilan teg ro'yxati olindi — `0.19.1`, `latest`, `0.19.0`, `0.18.1`… ; GitHub releases sahifasi 0.19.1 = 2026-07-05 deb tasdiqladi | **Approved** |
| `postgres:18.4-trixie` | Docker Hub | mavjud (xostda tortilgan) | postgres official | `docker images` — LOKAL mavjud; `compose.yaml:17` da allaqachon `db` uchun ishlatiladi | **Approved (mavjud)** |
| `rclone/rclone` | Docker Hub | 2026-08-12 (faol) | github.com/rclone/rclone (MIT) | Docker Hub API — faqat `beta`/`master`/`sha-*` teglari oxirgi 6 ta ichida ko'rindi; **versiyali teg ro'yxatga chiqmadi** | **Not used** (R-9 restic tanladi; agar kerak bo'lsa versiyali tegni ALOHIDA tekshiring) |
| `aptible/supercronic` | GitHub releases | — | MIT | ⛔ **TEKSHIRILMADI** — R-9/R-10 uni rad etdi | **Rejected** |

**Packages removed due to slopcheck [SLOP] verdict:** none (nomzod yo'q)
**Packages flagged as suspicious [SUS]:** none

⚠ **`slopcheck` bu sessiyada ISHLATILMADI va bu to'g'ri:** o'rnatiladigan
paket yo'q. Agar planner qaror o'zgartirib **yangi pip yoki npm paketi**
qo'shsa (masalan `supercronic` o'rniga biror python cron kutubxonasi),
Package Legitimacy Gate protokoli o'sha paket uchun QAYTA yurgizilishi va
`checkpoint:human-verify` qo'yilishi SHART.

⚠ **`restic/restic` va `rclone/rclone` xostda LOKAL YO'Q** (`docker images`
tekshiruvi): birinchi build Docker Hub'ga tarmoq talab qiladi. 07-faza
`deferred-items.md` №5 aynan shu holatni («bu muhitda Docker Hub'ga tarmoq
yo'q») qayd etgan — planner buni Wave 0 xavfi sifatida hisobga olsin.

---

## Architecture Patterns

### System Architecture Diagram

```
                         ┌─────────────────────────────────────────────┐
  Direktor / bozor admini│  Brauzer  /{locale}/reports                  │
  (REPORT_VIEW)          │  ┌────────────────────────────────────────┐ │
        │                │  │ Davr tanlagich (nuqs → ?from=&to=&tab=) │ │
        ▼                │  └───────────────┬────────────────────────┘ │
  ┌──────────┐           │                  │ TanStack Query            │
  │  nginx   │──────────▶│  ┌───────────────▼────────────────────────┐ │
  └──────────┘           │  │ 4 ta ko'rinish: tushum · qarzdorlik ·   │ │
                         │  │ nomuvofiqlik arxivi · AI aniqligi       │ │
                         │  │ + [.xlsx] tugmasi (to'g'ridan GET)      │ │
                         │  └────────────────────────────────────────┘ │
                         └──────────────────┬──────────────────────────┘
                                            │ JSON (ko'rish)  /  bytes (eksport)
             ┌──────────────────────────────▼──────────────────────────────┐
             │  core-api  ·  app/api/v1/reports.py                          │
             │  ┌────────────────────────────────────────────────────────┐ │
             │  │ require_permission(REPORT_VIEW)                        │ │
             │  │ + audit_read(TABLE_*, reason="report_*")  ← BITTA yozuv│ │
             │  └───────────────┬──────────────────────┬─────────────────┘ │
             │                  │                      │                    │
             │   ┌──────────────▼──────────┐   ┌───────▼──────────────────┐│
             │   │ report_repo.py (YANGI)  │   │ xlsx_export.py (YANGI)   ││
             │   │ HOSILA SQL — jadval YO'Q│   │ escape_formula + freeze  ││
             │   └──────────────┬──────────┘   └───────┬──────────────────┘│
             └──────────────────┼──────────────────────┼───────────────────┘
                                │                      │ bytes
      ┌─────────────────────────▼──────────────────────┐└──▶ StreamingResponse
      │ PostgreSQL 18.4  (RLS: app.market_id)          │
      │  daily_charges · payments · charge_adjustments │
      │  billing_anomalies · reconciliation_cases      │
      │  vendors · stalls · stall_slot_occupancy       │
      │  review_assignments/zone_reviews (aniqlik)     │
      │  ledger_entries (YANGI — daftar importi)       │
      │  system_heartbeats (GLOBAL, RLS yo'q)          │
      └───────┬──────────────────────────────▲─────────┘
              │ pg_dump -Fc -Z0              │ heartbeat: INSERT … ON CONFLICT
              │ (stdin-from-command)         │ ⛔ FAQAT muvaffaqiyatdan KEYIN
    ┌─────────▼──────────────────────────────┴─────────┐
    │  backup konteyneri  (YANGI compose xizmati)      │
    │  postgres:18.4-trixie + restic 0.19.1            │
    │  loop.sh: har 10 daq → «bugun bo'ldimi?» (DB)    │
    │           ├─ 04:40 dan keyin va bugun bo'lmagan  │
    │           │   → run-backup.sh                    │
    │           └─ yakshanba → restic check 5 %        │
    └───────┬────────────────────────┬─────────────────┘
            │ /seaweed:ro            │ restic → S3
            ▼                        ▼
    ┌───────────────┐        ┌──────────────────────────┐
    │ seaweed volume│        │ OFFSITE S3 (B2 / 2-region│
    │ (dalil kadrlar)│       │  — BOSHQA failure domain)│
    └───────────────┘        └──────────────────────────┘

    ── Kuzatuv halqasi (ALLAQACHON QURILGAN, faza faqat ulanadi) ──
    system_heartbeats['backup'] ──▶ alert_sweep (worker, har 5 daq)
        last_seen is None YOKI >26 soat  ──▶ backup_stale (CRITICAL,
        never_suppressed, platform_scoped) ──▶ Telegram + alert_events
    system_heartbeats['backup'] ──▶ GET /internal/self-check
        ──▶ never_seen[] / stale[]  ──▶ tashqi dead-man's switch
```

### Recommended Project Structure

```
services/core-api/app/
├── api/v1/
│   └── reports.py                 # YANGI — 6+2 marshrut, REPORT_VIEW + audit_read
├── repositories/
│   └── report_repo.py             # YANGI — hosila davr so'rovlari (D-03)
├── services/
│   ├── xlsx_export.py             # YANGI — freeze_zip + umumiy varaq quruvchi
│   └── xlsx_template.py           # MAVJUD — escape_formula shu yerda QOLADI
├── security/rbac.py               # ⚠ TEGILMASLIGI mumkin (R-1)
└── api/internal/self_check.py     # ⚠ TEGILMAYDI — `backup` ALLAQACHON ro'yxatda

migrations/versions/
├── 0024_ledger_entries.py         # YANGI — D-21 naqshi
└── 0025_notification_settings_id.py  # YANGI — 07 №4 (D-24)

ops/
├── backup/
│   ├── Dockerfile                 # postgres:18.4 + restic COPY --from
│   ├── loop.sh                    # idempotent tsikl (10 daq)
│   ├── run-backup.sh              # dump + arxiv + forget + heartbeat
│   └── heartbeat.sql              # ⛔ komponent nomi BITTA joyda
└── docs/
    └── go-live.md                 # YANGI — D-22

frontend/src/
├── app/[locale]/(app)/reports/
│   ├── page.tsx                   # YANGI
│   └── page.test.tsx
├── components/reports/            # YANGI — 4 ko'rinish + davr tanlagich
└── lib/report-queries.ts          # YANGI — zod sxemalari

tests/
├── integration/
│   ├── test_reports_api.py        # YANGI
│   ├── test_restore_drill.py      # YANGI — D-16(a)
│   ├── test_three_way.py          # YANGI — SC#5
│   └── test_phase8_criteria.py    # YANGI — 5 mezon, BITTA buyruq
├── unit/
│   ├── test_xlsx_export.py        # YANGI — determinizm + formula qochirish
│   └── test_backup_contract.py    # YANGI — skript/compose statik darvozalari
└── tenancy/
    └── test_personal_data_coverage.py  # ⚠ KENGAYTIRILADI (§ Pitfall 2)
```

### Pattern 1 — Davr hisoboti = HOSILA so'rov, jadval EMAS (D-03)

**What:** Har hisobot `text()` SQL bilan mavjud jadvallardan yig'iladi;
natija DTO ga aylanadi; `.xlsx` AYNI DTO dan quriladi (ikki hisob yo'li
YO'Q).

**When to use:** Uchala hisobot va 3 tomonlama solishtiruv.

**Nega bu naqsh:** 6-faza D-07 va 7-faza D-06 saqlangan agregatni
TAQIQLAYDI. Agregat jadval qo'shilsa u `daily_charges` bilan drift qiladi
va nizoda «qaysi son to'g'ri?» savoli javobsiz qoladi — bu SBOZOR mavjud
bo'lish sababining aynan teskarisi.

```python
# app/repositories/report_repo.py — TUSHUM (davr kesimida)
#
# ⛔ IKKI SANA IKKI SAVOLGA JAVOB BERADI VA ULAR ARALASHTIRILMAYDI:
#     payments.business_date — PUL QACHON YIG'ILDI (kassa kuni)
#     daily_charges.service_date — QAYSI KUNNING pattasi
#   «Tushum» = YIG'ILGAN PUL, ya'ni maxraj `business_date`.
#   Hisob (charged) esa `service_date` bo'yicha — u BOSHQA ustun.
_REVENUE_BY_DAY = text(
    f"""
    SELECT d.business_date                                        AS business_date,
           COALESCE(p.collected_soum, 0)::bigint                  AS collected_soum,
           COALESCE(p.payment_count, 0)::bigint                   AS payment_count,
           COALESCE(c.charged_soum, 0)::bigint                    AS charged_soum,
           COALESCE(c.charge_count, 0)::bigint                    AS charge_count
      FROM generate_series(:from_date::date, :to_date::date, '1 day') AS d(business_date)
      LEFT JOIN LATERAL (
        SELECT sum({_SIGNED_PAYMENT_EXPR})::bigint AS collected_soum,
               count(*)                            AS payment_count
          FROM payments p
         WHERE p.market_id = :market_id
           AND p.business_date = d.business_date
      ) p ON true
      LEFT JOIN LATERAL (
        SELECT sum(ch.amount_soum + COALESCE(adj.total, 0))::bigint AS charged_soum,
               count(*)                                             AS charge_count
          FROM daily_charges ch
          LEFT JOIN LATERAL (
            SELECT sum({_SIGNED_ADJUSTMENT_EXPR}) AS total
              FROM charge_adjustments a
             WHERE a.market_id = ch.market_id AND a.charge_id = ch.id
          ) adj ON true
         WHERE ch.market_id = :market_id
           AND ch.service_date = d.business_date
      ) c ON true
     ORDER BY d.business_date
    """
)
```

⚠ `_SIGNED_PAYMENT_EXPR` va `_SIGNED_ADJUSTMENT_EXPR` **`billing_repo.py`
dan IMPORT QILINADI**, qayta yozilmaydi: `vendor_outstanding()` bilan
`_VENDOR_CREDIT` orasidagi tenglikni G-14 darvozasi allaqachon o'lchaydi va
uchinchi nusxa o'sha darvozani chetlab o'tardi.

⚠ `generate_series` MAJBURIY: to'lovsiz kun **qator sifatida, 0 bilan**
chiqishi kerak. `GROUP BY` yolg'iz kunni butunlay tushirib qoldirardi va
direktor «o'sha kuni tizim ishlamadi» bilan «o'sha kuni pul yig'ilmadi» ni
ajrata olmasdi (4-fazaning «yo'qlikka alert» prinsipining hisobotdagi
ko'rinishi).

### Pattern 2 — Bayt-determinik eksport moduli (D-05, § Pitfall 3)

**What:** `app/services/xlsx_export.py` — YAGONA eksport quruvchisi.
Ichida: `escape_formula()` (import qilinadi, ko'chirilmaydi),
`freeze_zip()` (fikstursdan KO'CHIRILADI), `set_properties({"created": …})`.

```python
# app/services/xlsx_export.py
FROZEN_ZIP_TIME: Final = (1980, 1, 1, 0, 0, 0)
FROZEN_CREATED: Final = datetime(2026, 8, 1, 0, 0, 0)  # noqa: DTZ001

def freeze_zip(raw: bytes) -> bytes:
    """ZIP a'zolarining sanasini MUZLATADI.

    `XlsxWriter` `ZipFile.writestr()` ni chaqiradi, `zipfile` esa a'zo
    sanasini SOAT'dan oladi — ikki qo'shni chaqiruv baytlari sekund
    chegarasida farq qilardi. `tests/fixtures/karmana_seed.py::_freeze_zip`
    dan KO'CHIRILDI; fikstursdagi nusxa endi shu funksiyani IMPORT qiladi.
    """
```

⛔ **`worksheet.write()` va `write_string()` bu modulda TO'G'RIDAN-TO'G'RI
CHAQIRILMAYDI** — faqat `_write_text()` yordamchisi orqali
(`xlsx_template.py:469` ning qoidasi). Bitta o'tkazib yuborilgan yo'l
butun formula-injection himoyasini bekor qiladi va bu hisobot faylida
ayniqsa xavfli: qarzdorlik reestrida **sotuvchi ismi** bor, ya'ni ismni
`=HYPERLINK(...)` qilib yozgan odam **direktorning mashinasida** kod
bajartirardi.

### Pattern 3 — Bayt marshrutning TASNIF darvozasi (⛔ MAJBURIY, § Pitfall 2)

**What:** Har `.xlsx` `GET` marshruti `tests/tenancy/
test_personal_data_coverage.py` ning YOPIQ to'plamiga kiritiladi. Uchta
eksportdan **ikkitasi shaxsiy** (qarzdorlik reestri — `vendor_name`;
3 tomonlama solishtiruv — rasta+sotuvchi), **ikkitasi shaxsiy emas**
(tushum agregati; AI aniqligi).

**Nega darvozani KENGAYTIRISH kerak, BO'SHATISH emas:** bugungi
`test_binary_personal_routes_declare_read_audit_and_permission` **hamma**
bayt-shaxsiy marshrut uchun `granted <= EVIDENCE_FRAME_ALLOWED`
(`{CAMERA_VIEW, OCCUPANCY_REVIEW}`) ni talab qiladi. Bu 05-15 da AYNAN
BITTA marshrut (dalil-kadr) uchun yozilgan. Hisobot eksporti `REPORT_VIEW`
(+`VENDOR_VIEW`) talab qiladi, ya'ni bugungi assertion QIZARADI.

⛔ **To'g'ri tuzatish — per-route ruxsat XARITASI:**

```python
BINARY_PERSONAL_ROUTES: dict[str, str] = {
    "/api/v1/snapshots/{snapshot_id}/image": "…mavjud sabab…",
    "/api/v1/reports/receivables.xlsx": "qarzdorlik reestrida sotuvchi F.I.Sh. — …",
    "/api/v1/reports/three-way.xlsx": "rasta ↔ sotuvchi bog'lanishi — …",
}
BINARY_PERSONAL_ALLOWED: dict[str, frozenset[Permission]] = {
    "/api/v1/snapshots/{snapshot_id}/image": EVIDENCE_FRAME_ALLOWED,
    "/api/v1/reports/receivables.xlsx": frozenset({Permission.REPORT_VIEW,
                                                   Permission.VENDOR_VIEW}),
    "/api/v1/reports/three-way.xlsx": frozenset({Permission.REPORT_VIEW,
                                                 Permission.VENDOR_VIEW}),
}
```

⚠ **Ikki lug'atning kalitlari AYNAN teng bo'lishi assert qilinsin** — aks
holda yangi marshrut birinchisiga qo'shilib, ikkinchisiga qo'shilmasa
`KeyError` o'rniga jimgina `frozenset()` olardi va `granted <= set()`
har doim yolg'on bo'lib... aslida QIZARARDI. To'g'risi: `.get()` ISHLATMANG,
to'g'ridan-to'g'ri indekslang — `KeyError` baland ovozli nosozlik.

### Pattern 4 — Idempotent zaxira tsikli, holati BAZADA (R-7, R-10)

**What:** `loop.sh` har 10 daqiqada uyg'onadi va **bitta savol** beradi:
«bugungi biznes-kun uchun `system_heartbeats['backup']` yozilganmi?».
Yo'q bo'lsa va soat ≥ 04:40 bo'lsa — zaxirani boshlaydi.

**Nega bu naqsh:** bu 4-fazaning D-03 qarorining (`capture` tikining
idempotentligi) aynan takrori va u uchta nosozlikni birdan yopadi:

| Nosozlik | `cron` bilan | Bu tsikl bilan |
|---|---|---|
| Konteyner 04:30–04:50 orasida restart bo'ldi | Kun **yo'qoladi** | 04:50 da bajariladi |
| Zaxira 40 daqiqa davom etdi, tsikl yana uyg'ondi | Ikkinchi yugurish boshlanardi | «Bugun bo'lgan» → o'tkazib yuboradi |
| Xost soati sakradi | Cron jimgina o'tkazib yuborardi | Keyingi uyg'onishda bajariladi |

⛔ **Yurak urishi FAQAT to'liq muvaffaqiyatdan keyin yoziladi.** Aks holda
D-15 ning butun ma'nosi yo'qoladi: qisman bajarilgan zaxira «muvaffaqiyat
signali» bo'lib qolardi va `backup_stale` MANGU jim turardi.

### Pattern 5 — Tiklash isbotining IKKI qatlami (D-16)

| Qatlam | Nima o'lchanadi | Qayerda | Halol chegara |
|---|---|---|---|
| **(a) Mexanizm** | `pg_dump -Fc` → toza `postgres:18.4-trixie` konteyneriga `pg_restore` → smoke (`markets`, `daily_charges`, `payments` qatorlari va RLS policy'lari mavjud) | `tests/integration/test_restore_drill.py`, testcontainers | ⛔ `restic` bu testda ISHTIROK ETMAYDI (binar `tests` image'ida yo'q) — ya'ni «restic repodan tiklash» o'lchanmaydi |
| **(b) Haqiqat** | Real offsite repodan, REAL toza serverda, hujjatlashtirilgan mashq | `08-HUMAN-UAT.md`, egasi **Ops**, tetigi **VPS deploy** | SC#3 ning imzosi AYNAN shu bilan qo'yiladi |

⚠ **(a) ni «to'liq tiklash isboti» deb atash TAQIQLANADI.** 3- va
5-fazalarning darsi: mexanika qatlamining yashilligi bilan haqiqat
qatlamining yo'qligini yopish — aynan AI-02 ning `Blocked` bo'lish sababi.

### Pattern 6 — Daftar importi: quvurni qayta ishlating, reyestrni O'STIRING ONGLI (D-17, R-11)

```
POST /api/v1/reports/three-way/ledger?day=YYYY-MM-DD   (multipart .xlsx)
  1. _read_bounded()            — bayt chegarasi (oqim to'xtaydi)
  2. xlsx_reader.read_rows()    — ZIP/XML bomba, qator/ustun/varaq
  3. validate_ledger_rows()     — YANGI: rasta kodi mavjudmi, summa BUTUN va ≥0
  4. bitta xato ham bo'lsa → 422 + errors[]  (D-14, hech narsa yozilmaydi)
  5. INSERT … ON CONFLICT (market_id, business_date, stall_id) DO UPDATE
  6. write_app_audit(...)       — BITTA yig'ma yozuv (staff importi naqshi)
```

⚠ **`ON CONFLICT DO UPDATE`, `DO NOTHING` EMAS**: daftar kuni ichida
tuzatilishi mumkin va ikkinchi fayl birinchisini ALMASHTIRISHI kerak.
Lekin bu `daily_charges` ning o'zgarmaslik qoidasini BUZMAYDI —
`ledger_entries` moliyaviy haqiqat emas, **tashqi qog'oz manbaning
nusxasi**. Bu farq jadval docstringida LITERAL yozilsin, aks holda keyingi
ijrochi uni `FINANCIAL_TABLES` ga qo'shishga urinardi (va
`test_financial_tables_have_guards` uni `business_date` generated ustuni
va `CHECK (amount_soum > 0)` bilan majburlardi — daftar esa 0 ni ham
yozishi mumkin).

### Anti-Patterns to Avoid

- **⛔ Agregat jadval / materialized view qo'shish** — D-03 ni buzadi;
  drift nizoga aylanadi.
- **⛔ Eksport marshrutini `POST` qilib bayt-tasnif darvozasidan chetlab
  o'tish** — darvoza bugun jim qoladi va ERTAGA qo'shilgan marshrut ham
  jim qoladi. R-3 buni ochiq rad etadi.
- **⛔ `EVIDENCE_FRAME_ALLOWED` ni `REPORT_VIEW` bilan kengaytirish** —
  bu dalil-kadr marshrutining qo'riqchisini BO'SHATARDI (nazoratchi
  o'rniga endi direktor ham... aslida teskarisi: hisobot huquqi bilan
  dalil kadri ochilardi). Per-route xarita (Pattern 3) — yagona to'g'ri
  shakl.
- **⛔ Nomuvofiqlik JSON marshrutiga `vendor_name` qo'shish** — 07-10
  buni sabotaj bilan o'lchagan: to'rt tenancy testi qizaradi (D-08).
- **⛔ `pg_dump … | restic backup --stdin`** — quvur pg_dump ning chiqish
  kodini yutadi (§ Pitfall 5).
- **⛔ Yurak urishini zaxiradan OLDIN yoki `finally` da yozish** —
  D-15 ni bekor qiladi.
- **⛔ Aniqlik foizini klientda qayta hisoblash** — 05-14 qulflagan.
- **⛔ Bo'sh davr uchun «0 %» chizish** — D-10; WR-05 aynan shu.
- **⛔ Yangi `SECURITY DEFINER` funksiya** — D-21; `DEFINER_SURFACES`
  bo'sh qoladi (T-06-22).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---|---|---|---|
| Aniqlik / Wilson oralig'i / chalkashlik matritsasi | Yangi hisob moduli | `app/services/accuracy_report.py` | D-09; ikki maxraj UI-SPEC ishlangan misolidan O'LCHAB olingan va test bilan qulflangan |
| Excel formula injection himoyasi | O'z `sanitize()` | `xlsx_template.escape_formula()` | `\t` va `\r` prefikslari ham ro'yxatda — «=» tekshiruvi ularni o'tkazib yuborardi |
| `.xlsx` bayt determinizmi | ZIP ni qo'lda qayta qurish | `freeze_zip()` (fikstursdan ko'chiriladi) | 02-23 da o'lchangan: `XlsxWriter` a'zo sanasini SOAT'dan oladi |
| Xavfsiz `.xlsx` o'qish | `openpyxl` ni to'g'ridan chaqirish | `app/services/xlsx_reader.py` | ZIP bomba, XML bomba, qator/ustun/varaq chegaralari |
| All-or-nothing import | Qo'lda `begin()`/`rollback()` | `TenantSessionDep` (blok OCHILMAYDI) | `imports.py` modul docstringi: ichki blok D-14 ni FAQAT buzardi |
| Zaxira jadvali | `cron` konteynerda | Idempotent tsikl + `system_heartbeats` holati | Restart-chidamlilik va ikki marta yugurmaslik BITTA mexanizmdan |
| Zaxira shifri/dedup/retention | `tar`+`gpg`+`find -mtime` | `restic` | `forget --keep-*` + `check --read-data-subset` + repo butunligi tekshiruvi tayyor |
| pg_dump muvaffaqiyatini aniqlash | `PIPESTATUS` / `set -o pipefail` | `restic backup --stdin-from-command` | restic buyruqning chiqish kodini O'ZI tekshiradi va nolga teng bo'lmasa zaxirani BEKOR QILADI (rasmiy hujjat) |
| «Bu marshrut shaxsiy ma'lumot beradimi?» | Kod ko'rigi | `test_personal_data_coverage.py` yopiq to'plami | Model'siz marshrut IKKI ro'yxatdan birida bo'lishi MAJBURIY — «unutish» yo'li yopiq |
| Alert kaliti ↔ uch locale matni | Qo'lda tekshirish | `snapshot-copy.test.mjs` G-36 bloki | Oldinga + teskari + o'lcham qulfi |
| RLS + tenant policy + GRANT | Qo'lda DDL | `migrations/helpers.enable_tenant_rls()` | GRANT'siz policy `permission denied` beradi |

**Key insight:** Bu fazada «hand-rolling» ning eng katta xavfi **yangi kod
yozishda emas — mavjud darvozani chetlab o'tishda**. Har chetlash yo'li
(POST eksport, `?format=`, `PERSONAL_FIELDS` dan tashqaridagi maydon nomi)
bugun ishlaydi va ertaga o'sha darvozani BUTUNLAY foydasiz qiladi.

---

## Runtime State Inventory

> ⚠ Bu faza rename/refactor emas, LEKIN u **go-live** fazasi: D-22 runbook
> aynan «repo yangilangandan keyin qaysi runtime holat eskirgan qoladi?»
> savoliga javob berishi kerak. Shuning uchun inventarizatsiya
> **deploy nuqtai nazaridan** bajarildi.

| Category | Items Found | Action Required |
|---|---|---|
| **Stored data** | `system_heartbeats['backup']` — **qator hozir YO'Q** va bu o'lchanadigan holat (`alerting.py:180`). Birinchi muvaffaqiyatli zaxiradan keyin paydo bo'ladi. `market_notification_settings` — PK `market_id`, `id uuid` ustuni YO'Q (07 №4). `ledger_entries` — hali mavjud emas. | (1) `backup` yurak urishini yozadigan jarayon qurish; (2) `0025` migratsiyasi `id uuid` + `market_id` ga UNIQUE (§ Pitfall 16); (3) `0024` — `ledger_entries` |
| **Live service config** | `scheduler` konteyneri cron jadvalini **import paytida** oladi (`worker.py`, `LabelScheduleSource`) — 07-HUMAN-UAT #5 aynan shu. Bu fazada YANGI cron QO'SHILMAYDI (zaxira o'z konteynerida), ya'ni `scheduler` ni qayta yaratish **shart emas** — LEKIN runbook buni ochiq aytishi kerak. `go2rtc` oqim ro'yxati `:ro` config bilan. | Runbook bandi: `docker compose up -d --build backup` — `scheduler` ga TEGILMAYDI (agar `worker.py` ga tegilmasa) |
| **OS-registered state** | ⛔ **Yo'q — tekshirildi:** loyihada Windows Task Scheduler, systemd unit yoki pm2 saqlangan jarayon nomi ishlatilmaydi; barcha rejalar compose ichida (`ops/scripts/` da faqat ikki tekshiruv skripti: `verify-real-nvr.sh`, `verify-tunnel.sh`). | Yo'q |
| **Secrets / env vars** | **YANGI, hozir MAVJUD EMAS** (`.env.example` da `BACKUP`/`RESTIC`/`OFFSITE` bo'yicha nol moslik): `RESTIC_REPOSITORY`, `RESTIC_PASSWORD`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` (offsite), `BACKUP_DATABASE_URL` (libpq shaklida — § Pitfall 8b). Mavjudlari: `DATABASE_URL` (⚠ `postgresql+asyncpg://` — psql o'qiy olmaydi), `S3_*` (bular LOKAL SeaweedFS niki, offsite EMAS). | `.env.example` ga besh yangi kalit + `ops/backup/README.md`; ⛔ **`RESTIC_PASSWORD` yo'qolsa zaxira BUTUNLAY tiklanmaydi** — runbookda off-server saqlash bandi MAJBURIY |
| **Build artefaktlari** | `sbozor-core-api:*` image'lari (`worker`, `scheduler`, `tests` bir xil Dockerfile'dan). Yangi `backup` image'i **hech qachon qurilmagan** — birinchi build Docker Hub'ga tarmoq talab qiladi (`restic/restic` xostda YO'Q). `frontend` SSG build uchala locale'ni quradi — yangi `/reports` marshruti build vaqtini va `gate` byudjetini oshiradi. | Wave 0: image build zondi; D-26 byudjet kuzatuvi |

---

## Common Pitfalls

### Pitfall 1 — `PERSONAL_ROUTES` REYESTR emas, HOSILA (D-07 ning matni bilan ziddiyat)

**What goes wrong:** D-07 «hisobot marshruti `PERSONAL_ROUTES` reyestriga
KIRMAYDI» deydi. Mexanik haqiqat boshqa: `PERSONAL_ROUTES` — **qo'lda
yozilgan reyestr emas**, u `personal_data_routes(fastapi_app)` funksiyasi
bilan **HOSILA** qilinadi (`test_personal_data_coverage.py:313-323`):
javob modelida `vendor_name` / `phone` / `full_name` bo'lgan HAR `GET`
marshruti unga AVTOMATIK tushadi.

**Why it happens:** D-07 ning niyati — **operativ moliyaviy JSON
marshrutlariga** (`/billing/charges`, `/reconciliation/cases`) ism
qo'shmaslik. Bu niyat to'g'ri va o'zgarmaydi. Lekin qarzdorlik reestrining
EKRAN javobida ism **bo'lishi kerak** (aks holda D-07 ning o'z yechimi —
serverda joinlash — ma'nosiz).

**How to avoid:** Ikkalasini birdan bajaring: (1) mavjud moliyaviy
marshrutlar TEGILMAYDI; (2) yangi `GET /api/v1/reports/receivables`
javobida `vendor_name` BO'LADI, ya'ni u hosila to'plamga qo'shiladi va
`audit_read` + `VENDOR_VIEW` ni **e'lon qilishi SHART**. Bu D-07 ning
«har hisobot so'rovi bitta `audit_read` yozadi» talabi bilan AYNAN mos.
`MINIMUM_PERSONAL_ROUTES = 4` — QUYI chegara, ya'ni to'plamning 5 dan 6 ga
o'sishi hech nimani buzmaydi.

**Warning signs:** `test_every_personal_route_declares_read_audit` qizarsa
— javobga ism qo'shildi, lekin `Depends(audit_read(...))` yozilmadi.

---

### Pitfall 2 — ⛔ ENG XAVFLISI: `.xlsx` eksporti bayt-tasnif darvozasini QIZARTIRADI

**What goes wrong:** `StreamingResponse` qaytaradigan marshrutda
`response_model` YO'Q. `test_every_binary_response_route_is_classified`
har model'siz `GET` ni IKKI ro'yxatdan birida talab qiladi, va
`test_binary_personal_routes_declare_read_audit_and_permission`
**hammasidan** `granted <= EVIDENCE_FRAME_ALLOWED` ni talab qiladi.
`EVIDENCE_FRAME_ALLOWED = {CAMERA_VIEW, OCCUPANCY_REVIEW}` — hisobot
eksporti u yerga **sig'maydi**.

**Why it happens:** Darvoza 05-15 da AYNAN BITTA marshrut (dalil-kadr)
uchun yozilgan; uning docstringi «ro'yxat bitta elementdan iborat va u
SHUNDAY QOLISHI kerak» deydi — bu `SNAPSHOT_EVIDENCE_FRAME_ROUTES` haqida,
lekin `EVIDENCE_FRAME_ALLOWED` global cheklovga aylangan.

**How to avoid:** Pattern 3 — **per-route ruxsat xaritasi**. ⛔ Uch xato
yo'l va nima uchun ular xato:

| Xato yo'l | Nima bo'ladi |
|---|---|
| `EVIDENCE_FRAME_ALLOWED` ga `REPORT_VIEW` qo'shish | Dalil-kadr marshruti `REPORT_VIEW` bilan ham ochilardi — 05-15 ning butun ishi bekor |
| Eksportni `POST` qilish | `get_routes()` faqat `GET` ni yuradi → marshrut darvozadan **jimgina chiqib ketardi** (`POST /imports/errors.xlsx` bugun aynan shunday) |
| Eksportni `NON_PERSONAL_BINARY_ROUTES` ga yozish | Qarzdorlik reestrida ism BOR — bu yolg'on tasnif va u audit talabini o'chirardi |

**Warning signs:** `pytest tests/tenancy -q` da ikkita nomlangan
assertion; xabar marshrut yo'lini nomma-nom ko'rsatadi.

---

### Pitfall 3 — `_freeze_zip` `xlsx_template.py` da EMAS (CONTEXT.md D-05 noto'g'ri joyni ko'rsatadi)

**What goes wrong:** Reja «mavjud naqshni qayta ishlatamiz» deb yozadi,
ijrochi `xlsx_template.py` ni ochadi va u yerda hech nima topmaydi.

**Why it happens:** ⛔ **O'LCHANDI:** `_freeze_zip` **faqat ikki faylda**
uchraydi — `tests/fixtures/karmana_seed.py:679` (ta'rifi) va
`tests/unit/test_karmana_seed.py` (testi). Mahsulot eksport yo'llari
(`build_template`, `build_error_report`) `set_properties()` ni ham
chaqirmaydi, ya'ni ular bugun **bayt-determinik EMAS**.

**How to avoid:** Naqshni **mahsulotga ko'taring** (`app/services/
xlsx_export.py::freeze_zip`) va **fikstursni unga bog'lang** (nusxa
qoldirmang — ikki nusxa `_FROZEN_ZIP_TIME` bir kun ajralib ketardi va
`test_karmana_seed.py` boshqa baytlarni kutardi). Mavjud ikki eksport
yo'lini ham unga o'tkazish — **ONGLI kengaytma**, chunki u mavjud
`test_xlsx_template.py` kutilmalarini siljitishi mumkin (baytlar
o'zgaradi). Buni reja ochiq aytsin.

**Warning signs:** `test_karmana_seed.py` ning determinizm testi ikki
nusxa orasida yashil qoladi, lekin yangi eksport testi flaky bo'ladi.

---

### Pitfall 4 — `TEMPLATE_KINDS` AYNAN UCHTA deb qulflangan

**What goes wrong:** Daftar shabloni uchun to'rtinchi tur qo'shiladi va
`tests/unit/test_xlsx_template.py:843::test_template_kinds_are_exactly_three`
qizaradi (`assert TEMPLATE_KINDS == ("stalls", "vendors", "staff")`).
Bundan tashqari `imports.py:128` dagi `ImportKind = Literal[...]` va
`_TEMPLATE_PERMISSIONS` lug'ati ham QO'LDA sinxron.

**How to avoid:** R-11 — to'rtinchi turni qo'shing va testni **nomi bilan
birga** yangilang (`..._are_exactly_four`). Uch joyni birdan yangilang:
`TEMPLATE_KINDS`, `ImportKind`, `_TEMPLATE_PERMISSIONS`. ⚠ Daftar
shabloni `REPORT_VIEW` emas, **yozuv** huquqi talab qiladi (D-20:
nazoratchi yoki admin) — `_TEMPLATE_PERMISSIONS` ga mos yozuv kerak.

---

### Pitfall 5 — `pg_dump | restic backup --stdin` NOSOZLIKNI YUTADI

**What goes wrong:** POSIX quvurda oxirgi buyruqning chiqish kodi
qaytadi. `pg_dump` yiqilsa (parol xato, disk to'la, ulanish uzildi)
`restic` **bo'sh yoki qisqartirilgan oqimni muvaffaqiyat bilan yozadi**,
tsikl yurak urishini yozadi va `backup_stale` MANGU jim turadi — ya'ni
FOUND-07 ning butun kafolati soxta bo'ladi. restic hujjati buni o'z
misolida ochiq ogohlantiradi.

**How to avoid:** ⛔ `restic backup --stdin-from-command --stdin-filename
<nom> -- pg_dump …`. Rasmiy hujjat: *«Restic uses the command exit code to
determine whether the command succeeded. A non-zero exit code from the
command causes restic to cancel the backup.»*

**Warning signs:** `restic ls latest` dagi dump fayl hajmi kundan kunga
keskin farq qiladi yoki 0 bayt.

---

### Pitfall 6 — `pg_dump -Fc` standart siqishi restic dedup'ini O'LDIRADI

**What goes wrong:** `-Fc` standart holatda zlib bilan siqadi. Siqilgan
oqimda bitta baytning o'zgarishi undan keyingi BARCHA baytlarni
o'zgartiradi, ya'ni restic har kuni **butun dumpni yangi ma'lumot deb**
saqlaydi. 14 kunlik retention 14 × to'liq baza demak — Contabo diskida va
offsite hisobida.

**How to avoid:** `pg_dump -Fc -Z0` (siqishsiz) + restic'ning O'Z siqishi
(`--compression auto` — **standart qiymat**, repo format **versiya 2**
talab qiladi; yangi repolar 0.14 dan beri v2). Shunda restic ham
deduplikatsiya, ham siqish beradi.

**Warning signs:** `restic stats --mode raw-data` ikki kundan keyin
deyarli ikki barobar o'sadi.

---

### Pitfall 7 — restic image'ida `pg_dump` YO'Q; Alpine v3.22 da `postgresql18-client` ham YO'Q

**What goes wrong:** `FROM restic/restic:0.19.1` + `apk add
postgresql18-client` — build vaqtida `ERROR: unable to select packages`.

**Why it happens:** ⛔ O'LCHANDI: restic image'i `alpine:latest` ustida va
faqat `ca-certificates fuse openssh-client tzdata jq` o'rnatadi (rasmiy
Dockerfile). `pkgs.alpinelinux.org` bo'yicha `postgresql18-client`
**faqat `edge`** da; `v3.22` da eng yangisi `postgresql17-client`.

**How to avoid:** R-6 — bazani teskari qiling: `FROM postgres:18.4-trixie`
+ `COPY --from=restic/restic:0.19.1 /usr/bin/restic`. Image xostda
allaqachon bor, ya'ni build tezroq ham.

---

### Pitfall 8 — Ikki xil «URL» va ikki xil «versiya»

**(a) `pg_dump` MAJOR versiyasi serverdan KICHIK bo'lolmaydi.** `pg_dump`
17 `postgres` 18 serverni dump qilishdan **rad etadi** (`server version:
18.x; pg_dump version: 17.x — aborting`). R-6 buni tanlov bilan yopadi
(bir xil image), lekin runbookda yozilishi kerak: **serverni yangilashdan
oldin backup image'ini yangilang.**

**(b) `DATABASE_URL` `psql` uchun YAROQSIZ.** `.env.example:21` da
`postgresql+asyncpg://…` — bu SQLAlchemy dialekti va `psql` uni
`invalid URI scheme` bilan rad etadi. ⛔ **Yangi `BACKUP_DATABASE_URL`
(libpq shakli: `postgresql://…`) kiritilsin**, `sed` bilan konvertatsiya
QILINMASIN: bir joyda ikki haqiqat manbai bo'lardi va parol o'zgarganda
biri eskirardi.

---

### Pitfall 9 — Zaxira oynasi `retention` bilan to'qnashadi

**What goes wrong:** `RETENTION_CRON = "20 3 * * *"` — saqlash siyosati
kadrlarni **AYNAN o'sha kalitda siqib qayta yozadi** (CAM-07, 04-12 da
o'lchangan). 03:00 da olingan arxiv 03:20 da eskiradi va keyingi zaxira
o'sha obyektlarni QAYTADAN yozadi (dedup foydasi yo'q, chunki mazmun
o'zgargan).

**How to avoid:** R-10 — **04:40**. `retention` (03:20) va `day_close`
(03:40) va `billing_close` (04:10) dan KEYIN; kadr olish oynasi (06:00)
dan OLDIN. Qo'shimcha foyda: dump kechagi kunning **yopilgan** hisobini
o'z ichiga oladi.

**Warning signs:** `restic stats` da SeaweedFS qismi kunlik to'liq hajmga
teng o'sadi.

---

### Pitfall 10 — `RESTIC_PASSWORD` yo'qolsa zaxira YO'Q

**What goes wrong:** restic repo'si parol bilan shifrlangan. Parol faqat
VPS'ning `.env` ida bo'lsa va VPS o'lsa — **zaxira ham o'ladi**. Bu
FOUND-07 ni bajarilmagan holatga qaytaradi va buni faqat falokat kuni
bilib olinadi.

**How to avoid:** Runbookda (D-22) MAJBURIY band: parol **serverdan
tashqarida** ikki joyda (parol menejeri + qog'oz/seyf). ⛔ Bu tekshirish
mumkin bo'lgan band: `08-HUMAN-UAT.md` da «parol qayerda saqlangani
yozildi va IKKI ODAM biladi» deb imzolanadi.

⚠ Ikkinchi shakl: `restic init` mavjud repoda xato beradi. Skript
`restic cat config >/dev/null 2>&1 || restic init` qilsin — birinchi
yugurish avtomatik, keyingilar jim.

---

### Pitfall 11 — Platforma adminida `REPORT_VIEW` YO'Q

**What goes wrong:** D-04 «direktor + bozor admini (+ platforma admini)»
deydi. `ROLE_PERMISSIONS[PLATFORM_ADMIN]` da (`rbac.py:211-226`)
`REPORT_VIEW` **YO'Q** — platforma admini `/occupancy`, `/billing`,
`/reconciliation` ni ham bugun ko'ra olmaydi (403).

**How to avoid:** ⛔ Bu **ONGLI QAROR** bo'lishi kerak, yo'l-yo'lakay
tuzatish emas. Ikki yo'l:
- **(A) Tavsiya etiladi — matritsani TEGMANG.** D-04 ning «(+ platforma
  admini)» qismi qavs ichida va u bugungi holatni tasvirlamaydi. Platforma
  admini bozorni SOZLAYDI, hisobotni o'qimaydi — bu D-07 (2-faza) ning
  «direktor NIMA QILA OLMAYDI» falsafasining teskari tomoni.
- **(B)** `REPORT_VIEW` ni `PLATFORM_ADMIN` ga qo'shish — **uch fayl**
  (`rbac.py`, `rbac.ts`, `role-gate.test.mjs` kutilmasi) va u BIR VAQTDA
  `/occupancy` + `/billing` + `/reconciliation` ni ham ochadi, ya'ni
  o'zgarish bu fazadan KENGROQ.

Qaysi tanlansa ham — SUMMARY da nomma-nom yozilsin.

---

### Pitfall 12 — «O'lchanmagan» ni «nol» qilib chizish (WR-05 ning aynan o'zi)

**What goes wrong:** Aniqlik bloki so'rov YIQILGANDA yoki namuna bo'sh
bo'lganda «0 %» chizadi. `AccuracyReport.measured=False` da uchala
nisbat `null` bo'ladi — `null ?? 0` refleksi o'lchanmagan miqdorni
o'lchangan nol qiladi.

**How to avoid:** D-10 — blok **umuman chizilmaydi** yoki «o'lchov yo'q»
holati ochiq aytiladi. `frontend/src/lib/wilson.ts` da
`MIN_SAMPLE_FOR_PERCENT` allaqachon bor va u server bilan bir xil son.
Eksportda ham xuddi shu: **bo'sh katak**, `0` EMAS (`write_blank`).

---

### Pitfall 13 — Chegarasiz davr = xotira va vaqt portlashi

**What goes wrong:** `?from=2020-01-01&to=2030-12-31` + 1000 rasta →
qarzdorlik reestri va solishtiruv millionlab qator beradi. `XlsxWriter`
`{"in_memory": True}` bilan **hammasini xotirada** quradi va uvicorn
ishchisi bloklanadi.

**How to avoid:** Ikki chegara, ikkalasi ham `Settings` da (A7 naqshi:
`import_max_*` bilan bir toifada):
- `report_max_period_days` (tavsiya: **366**) → `422 report_period_too_long`
- `report_max_rows` (tavsiya: `settings.import_max_rows` = 5000 bilan bir
  xil) → `422 report_too_large`

⚠ `constant_memory=True` rejimi **RAD ETILADI**: u qatorlarni tartib
bilan yozishni majburlaydi va `freeze_panes`/`autofilter` ni buzadi.

---

### Pitfall 14 — «Tushum» qaysi sana bo'yicha?

**What goes wrong:** `payments.business_date` (pul QACHON yig'ildi) va
`daily_charges.service_date` (QAYSI kunning pattasi) **bir xil emas**:
kassir bugun kechagi qarzni to'laydi. Bitta ustunni tanlab «tushum» deb
atash direktorga noto'g'ri savolga javob berardi.

**How to avoid:** ⛔ **Ikkalasi ham ko'rsatilsin, alohida ustunlarda**
(6-faza D-05 sinfi: alohida sanoqlar birlashtirilmaydi):
`collected_soum` (`payments.business_date` bo'yicha) va `charged_soum`
(`daily_charges.service_date` bo'yicha). Farq — **yig'ilish darajasi**
va aynan u RECON-04 ning qiymatidir. Ustun sarlavhalari uchala tilda
farqni AYTSIN.

---

### Pitfall 15 — `alert-list.test.tsx` va `ALERT_TITLE_KEY_COUNT = 15` o'lcham qulfi

**What goes wrong:** 07 №1-qo'shimcha bandi (D-24) `alert-list.test.tsx`
ga to'rt kalitni RENDER qilishni talab qiladi. Agar shu ish paytida yangi
alert kaliti qo'shilsa (masalan D-25 ni buzib `digest_morning_stale`),
`snapshot-copy.test.mjs` ning `ALERT_TITLE_KEY_COUNT = 15` qulfi qizaradi.

**How to avoid:** D-25 ni hurmat qiling — **yangi alert kaliti
QO'SHILMAYDI**. `backup_stale` ALLAQACHON reyestrda (`ALERT_META:313`),
ya'ni FOUND-07 hech qanday yangi kalit talab qilmaydi. ⚠ Bu tekshirilsin:
`ALERT_TITLE_KEYS` (frontend) da `backup_stale` matni **borligi** — G-36
uni allaqachon qo'riqlaydi, lekin RENDER holatida o'lchanmagan.

---

### Pitfall 16 — `market_notification_settings` PK migratsiyasi `ON CONFLICT` ni sindirishi mumkin

**What goes wrong:** 07 №4 (D-24) jadvalga `id uuid` qo'shib PK ni
ko'chirishni talab qiladi. `binding_repo._BIND_DIRECTOR_CHAT`
(`binding_repo.py:540-548`) esa **`ON CONFLICT (market_id) DO UPDATE`**
ishlatadi. PK `market_id` dan `id` ga ko'chsa va `market_id` ga UNIQUE
qolmasa → `there is no unique or exclusion constraint matching the
ON CONFLICT specification` va direktor botga ULANA OLMAYDI.

**How to avoid:** Migratsiya `id uuid PRIMARY KEY DEFAULT uuidv7()`
qo'shganda `market_id` ga **`UNIQUE` konstraytini SAQLASIN**
(`UNIQUE(market_id)`). Testi: `bind_director()` ni migratsiyadan keyin
IKKI marta chaqirish (insert + update shoxlari).

**⚠ Ikkinchi topilma — bandning texnik asosi TEKSHIRILISHI kerak.**
`deferred-items.md` №4 va `schema_contract.py` docstringi «`fn_audit_row()`
bunday jadvalda **har DML da YIQILARDI**» deydi. Manbani o'qib ko'rdim
(`migrations/entities/triggers.py:64-110`): funksiya
`COALESCE((v_new ->> 'id')::uuid, (v_old ->> 'id')::uuid)` yozadi va
`audit_log.row_id` **`nullable=True`** (`0002_audit.py:111`). `'id'`
kaliti yo'q bo'lsa `->>` `NULL` qaytaradi, `NULL::uuid` esa **istisno
KO'TARMAYDI**. Ya'ni «yiqilardi» da'vosi kod bo'yicha **tasdiqlanmaydi** —
haqiqiy oqibat: audit qatorlari `row_id = NULL` bilan yozilardi va
«qaysi qator o'zgardi?» savoli javobsiz qolardi.

⛔ **Qaror O'ZGARMAYDI** (`id uuid` qo'shiladi — D-24), lekin reja
«yiqiladi» da'vosiga tayangan test YOZMASIN. To'g'ri o'lchov: migratsiyadan
keyin `AUDITED_TABLES` ga qo'shib, `bind_director()` chaqirilganda
`audit_log` da `row_id IS NOT NULL` bo'lgan qator paydo bo'lishini
talab qilish. **Wave 0 zondi:** hozirgi holatda triggerni qo'lda ulab
bitta DML yuritib ko'ring — u yiqiladimi yoki `NULL` yozadimi.

---

### Pitfall 17 — `gate` byudjeti (D-26) va yangi testlarning narxi

**What goes wrong:** Bu faza kamida to'rt yangi integratsiya fayli
(`test_reports_api`, `test_restore_drill`, `test_three_way`,
`test_phase8_criteria`), ikki unit fayli va yangi frontend marshruti
(uchala locale'da SSG build) qo'shadi. `test_restore_drill` **ikkita
qo'shimcha postgres konteynerini** ko'taradi.

**How to avoid:** (1) `test_restore_drill` ni `@pytest.mark.slow` bilan
belgilang va `gate` ga kirishini ONGLI hal qiling; (2) `gate:fast`
(200 s) ga hech nima qo'shmang; (3) o'lchov TINCH XOSTDA uch marta
(05/06-faza tartibi). ⚠ **`C:` diski 88 % to'la (21 GB bo'sh)** —
Docker VHDX o'sha yerda va ikki qo'shimcha postgres konteyneri +
yangi image qatlami buni yanada toraytiradi (`disk_pressure` chegarasi
85 % — mahsulotning O'Z alerti bu holatni tan oladi).

---

### Pitfall 18 — Yangi frontend marshruti uchta darvozaga ulanadi

**What goes wrong:** `/reports` qo'shilganda uchta narsa jimgina
eskiradi: (1) `app-shell.tsx::NavItem["href"]` — **literal union tipi**
(60-qator), yangi yo'l unga qo'shilmasa `tsc` qizaradi; (2)
`i18n:check` — uchala locale'da yangi kalitlar (uz-Cyrl **hosila**,
`i18n:gen` yugurtirilishi kerak); (3) `glossary.test.mjs` —
taqiqlangan sinonimlar (`yig'im`, `do'kon`) **har locale uchun o'z
tokenlari bilan**.

**How to avoid:** Reja shu uch bandni `files_modified` ga LITERAL
kiritsin. Hisobot atamalari uchun: «patta» (`yig'im` EMAS), «rasta»
(`do'kon` EMAS) — 7-faza D-30 lug'ati.

---

## Code Examples

### 1. Qarzdorlik reestri — ism SERVERDA joinlanadi (D-07, 06 №9 ning yechimi)

```python
# app/repositories/report_repo.py
#
# ⛔ ISM SHU YERDA JOINLANADI VA BU 06 `deferred-items.md` №9 NING YECHIMI.
#   Klient joini (`useVendorsQuery` + `PAGE_SIZE = 50`) 51-chi sotuvchidan
#   boshlab bo'sh katak berardi. Uch rad etilgan yo'l (hamma sahifani
#   tortish / `?ids=` marshruti / moliyaviy javobga `vendor_name`) RAD
#   ETILGANCHA QOLADI — bu marshrut ULARDAN BOSHQA sinf: u operativ emas,
#   HUJJAT va u BITTA `audit_read` yozadi (sotuvchi boshiga emas).
_RECEIVABLES = text(
    """
    SELECT v.id                       AS vendor_id,
           v.full_name                AS vendor_name,
           v.phone                    AS phone,
           o.outstanding_soum         AS outstanding_soum,
           o.oldest_unpaid_date       AS oldest_unpaid_date,
           o.stall_codes              AS stall_codes
      FROM (...) o
      JOIN vendors v ON v.market_id = :market_id AND v.id = o.vendor_id
     WHERE o.outstanding_soum <> 0          -- ⛔ NOL QATOR CHIQMAYDI
     ORDER BY o.outstanding_soum DESC, v.full_name
    """
)
```

```python
# app/api/v1/reports.py
ReportViewerDep = Annotated[Principal, Depends(require_permission(Permission.REPORT_VIEW))]

@router.get(
    "/receivables",
    response_model=ReceivablesResponse,
    dependencies=[
        # ⛔ IKKALASI HAM MAJBURIY VA IKKALASI BOSHQA SAVOLGA JAVOB BERADI:
        #   VENDOR_VIEW — «bu odam shaxsiy ma'lumot ko'rishga haqlimi?»
        #   audit_read  — «kim, qachon, qaysi davrni ko'rdi?»
        # `test_personal_data_coverage.py` ikkalasini ALOHIDA o'lchaydi.
        Depends(require_permission(Permission.VENDOR_VIEW)),
        Depends(audit_read(TABLE_VENDORS, reason="report_receivables")),
    ],
)
async def receivables(
    principal: ReportViewerDep,
    session: TenantSessionDep,
    from_date: Annotated[date, Query(alias="from")],
    to_date: Annotated[date, Query(alias="to")],
) -> ReceivablesResponse: ...
```

### 2. Bayt-determinik eksport javobi (D-05/D-06)

```python
# app/services/xlsx_export.py
def build_receivables_workbook(
    rows: Sequence[ReceivableRow], locale: str, period: tuple[date, date]
) -> bytes:
    buffer = io.BytesIO()
    workbook = xlsxwriter.Workbook(buffer, {"in_memory": True})
    # ⛔ SANA MUZLATILADI (1-qatlam) — `docProps/core.xml` soatdan kelardi.
    workbook.set_properties({"created": FROZEN_CREATED})
    try:
        texts = report_texts(locale)          # D-06: uch tilda, vebdagi lug'at bilan BIR XIL
        sheet = workbook.add_worksheet(texts["receivables_sheet"])
        money = workbook.add_format({"num_format": "#,##0"})
        for column, key in enumerate(_RECEIVABLE_HEADERS):
            _write_text(sheet, 0, column, texts[key], header_format)
        for offset, row in enumerate(rows, start=1):
            _write_text(sheet, offset, 0, row.stall_codes)
            _write_text(sheet, offset, 1, row.vendor_name)     # escape_formula ICHIDA
            # ⛔ PUL — SON, matn EMAS: Excelda saralash va yig'indi ishlashi kerak
            sheet.write_number(offset, 2, row.outstanding_soum, money)
            if row.oldest_unpaid_date is None:
                sheet.write_blank(offset, 3, None)             # ⛔ NOL EMAS — BO'SH (D-10)
            else:
                _write_text(sheet, offset, 3, row.oldest_unpaid_date.isoformat())
        sheet.freeze_panes(1, 0)
        sheet.autofilter(0, 0, max(len(rows), 1), len(_RECEIVABLE_HEADERS) - 1)
    finally:
        workbook.close()
    # ⛔ 2-QATLAM: ZIP a'zolarining sanasi (`zipfile` uni SOAT'dan oladi)
    return freeze_zip(buffer.getvalue())
```

### 3. Solishtiruvning imzo qatorlari (D-19)

```python
# ⛔ RAQAMLI IMZO YO'Q — bu QOG'OZ jarayon (D-19). Eksportning pastida
#   ikki qator: «Bajardi: nazoratchi/admin ____ sana ____» va
#   «Tasdiqladi: direktor ____ sana ____». Ismlar TO'LDIRILMAYDI —
#   fayl imzolanmagan holda chiqadi va uni ODAM imzolaydi.
_SIGNATURE_KEYS: Final = ("signed_by_executor", "signed_by_director")
for offset, key in enumerate(_SIGNATURE_KEYS, start=len(rows) + 3):
    _write_text(sheet, offset, 0, texts[key])
    sheet.write_blank(offset, 1, None, signature_line_format)
```

### 4. Zaxira skripti — quvursiz, chiqish kodi tekshiriladigan (Pitfall 5, 6)

```bash
#!/usr/bin/env bash
# ops/backup/run-backup.sh
set -euo pipefail

: "${BACKUP_DATABASE_URL:?libpq shakli MAJBURIY (postgresql://…) — DATABASE_URL emas}"
: "${RESTIC_REPOSITORY:?}"
: "${RESTIC_PASSWORD:?}"

TODAY="$(TZ=Asia/Tashkent date +%F)"

# 1. Repo mavjudmi — `init` ni har safar chaqirish mavjud repoda XATO beradi.
restic cat config >/dev/null 2>&1 || restic init

# 2. POSTGRES — ⛔ QUVUR YO'Q. `--stdin-from-command` pg_dump ning CHIQISH
#    KODINI tekshiradi; oddiy `pg_dump | restic --stdin` esa yiqilgan
#    dumpni MUVAFFAQIYAT deb yozardi (rasmiy hujjatning o'z ogohlantirishi).
# ⛔ `-Z0` MAJBURIY: siqilgan dump restic'ning deduplikatsiyasini o'ldiradi.
restic backup \
  --stdin-from-command \
  --stdin-filename "sbozor-${TODAY}.dump" \
  --tag postgres --tag "day-${TODAY}" \
  -- pg_dump --format=custom --compress=0 --no-owner --no-privileges \
             --dbname="${BACKUP_DATABASE_URL}"

# 3. OBYEKT-OMBOR — `:ro` mount qilingan SeaweedFS hajmi.
#    04:40 da kadr olish oynasi (06:00–08:00, 16:00, 18:00) ham,
#    retention (03:20) ham TUGAGAN — ya'ni yozuvsiz oyna.
restic backup --tag seaweedfs --tag "day-${TODAY}" /seaweed

# 4. RETENTION — CLAUDE.md va D-12 dagi AYNAN shu qiymatlar.
restic forget --keep-daily 14 --keep-weekly 8 --keep-monthly 12 --prune

# 5. ⛔ YURAK URISHI FAQAT SHU YERGACHA YETIB KELINGANDA. `set -e` yuqoridagi
#    har qanday nosozlikda skriptni to'xtatadi, ya'ni qator YOZILMAYDI va
#    `alert_sweep` 26 soatdan keyin `backup_stale` ni ko'taradi (D-15).
psql "${BACKUP_DATABASE_URL}" -v ON_ERROR_STOP=1 \
     -v day="${TODAY}" -f /opt/backup/heartbeat.sql
```

```sql
-- ops/backup/heartbeat.sql
-- ⛔ KOMPONENT NOMI BITTA JOYDA VA U `alerting.BACKUP_COMPONENT` BILAN
--    MATN SIFATIDA BOG'LANGAN (test darvozasi ikkisini solishtiradi).
--    Nom ayrilsa endpoint `backup` ni MANGU `never_seen` da ko'rsatardi,
--    holbuki zaxira ishlab turardi (`self_check.py` ning o'z ogohlantirishi).
INSERT INTO system_heartbeats (component, last_seen_at, detail)
VALUES ('backup', now(), jsonb_build_object('business_date', :'day'))
ON CONFLICT (component) DO UPDATE
   SET last_seen_at = now(),
       detail       = EXCLUDED.detail;
```

### 5. Idempotent tsikl — holat BAZADA (Pattern 4)

```bash
#!/usr/bin/env bash
# ops/backup/loop.sh — `cron` EMAS va bu ATAYIN (§ Architecture Pattern 4).
set -euo pipefail
INTERVAL="${BACKUP_POLL_SECONDS:-600}"
RUN_AFTER_HOUR="${BACKUP_RUN_AFTER:-04:40}"

already_done_today() {
  # ⛔ HOLAT BAZADA, KONTEYNER XOTIRASIDA EMAS: restart kunni yo'qotmaydi
  #    va ikkinchi yugurishni ham boshlamaydi (04-faza D-03 naqshi).
  psql "${BACKUP_DATABASE_URL}" -tAc "
    SELECT 1 FROM system_heartbeats
     WHERE component = 'backup'
       AND (last_seen_at AT TIME ZONE 'Asia/Tashkent')::date
           >= (now() AT TIME ZONE 'Asia/Tashkent')::date" | grep -q 1
}

while true; do
  NOW="$(TZ=Asia/Tashkent date +%H:%M)"
  if [[ "${NOW}" > "${RUN_AFTER_HOUR}" ]] && ! already_done_today; then
    /opt/backup/run-backup.sh || echo "backup_failed exit=$?" >&2
  fi
  # Haftalik butunlik tekshiruvi (CLAUDE.md § Backups)
  if [[ "$(TZ=Asia/Tashkent date +%u)" == "7" && "${NOW}" > "05:30" ]]; then
    restic check --read-data-subset=5% || echo "restic_check_failed exit=$?" >&2
  fi
  sleep "${INTERVAL}"
done
```

⚠ `restic check` nosozligi **yurak urishini o'chirmaydi** va bu ONGLI:
u zaxira olishning nosozligi emas, repo butunligining nosozligi. Uni
alohida signalga aylantirish (masalan `backup_check_stale`) D-25 ning
sinfiga tushadi — **V2**. Bugun u `stderr` ga chiqadi va Ops ko'radi.

### 6. Compose xizmati (D-13)

```yaml
  backup:
    # KUNLIK ZAXIRA (FOUND-07, D-12/D-13/D-15).
    #
    # ⚠ PROFILSIZ — `worker`, `scheduler`, `storage` bilan bir xil sabab:
    # bu ISHLAB CHIQARISH komponenti. Profil ortida qolsa zaxira HECH
    # QACHON olinmasdi va HECH QANDAY xato chiqmasdi — `docker compose ps`
    # toza, jurnal bo'sh. Farqi shundaki bu holatni tizim O'ZI ko'radi:
    # 26 soatdan keyin `backup_stale` (CRITICAL) ko'tariladi.
    #
    # SAKKIZINCHI KONTEYNER, TO'RTINCHI SERVIS EMAS: `db`, `cache`,
    # `storage`, `go2rtc`, `nginx` bilan bir toifa — tayyor image ustidagi
    # ops skripti, bizning uchinchi mikroservisimiz EMAS (CLAUDE.md
    # «aynan 3 ta servis» cheklovi buzilmaydi).
    build:
      context: .
      dockerfile: ops/backup/Dockerfile
    environment:
      # ⛔ `DATABASE_URL` EMAS: u `postgresql+asyncpg://` (SQLAlchemy
      #    dialekti) va `psql`/`pg_dump` uni rad etadi.
      BACKUP_DATABASE_URL: ${BACKUP_DATABASE_URL}
      RESTIC_REPOSITORY: ${RESTIC_REPOSITORY}
      RESTIC_PASSWORD: ${RESTIC_PASSWORD}
      # Offsite S3 rekvizitlari — LOKAL SeaweedFS niki EMAS (D-14):
      # boshqa failure domain bo'lmasa zaxiraning ma'nosi yo'q.
      AWS_ACCESS_KEY_ID: ${BACKUP_S3_ACCESS_KEY}
      AWS_SECRET_ACCESS_KEY: ${BACKUP_S3_SECRET_KEY}
      TZ: Asia/Tashkent
    volumes:
      # ⚠ `:ro` MAJBURIY — zaxira jarayoni arxivni QAYTA YOZA OLMASLIGI
      #   kerak (`go2rtc.yaml` / `s3.json` bilan bir xil qoida).
      - seaweed:/seaweed:ro
    depends_on:
      db:
        condition: service_healthy
    restart: unless-stopped
```

### 7. Tiklash mashqi — CI qatlami (D-16a)

```python
# tests/integration/test_restore_drill.py
#
# ⚠ HALOL CHEGARA SHU YERDA LITERAL YOZILADI: bu test `restic` ni UMUMAN
#   ISHLATMAYDI (binar `tests` image'ida yo'q). U «dump → toza server →
#   tiklandi → ma'lumot joyida» zanjirini o'lchaydi, «offsite repodan
#   tiklandi» ni EMAS. Ikkinchisi `08-HUMAN-UAT.md` da, egasi Ops.
@pytest.mark.slow
async def test_a_dump_restores_into_a_clean_server_with_data_intact(
    pg_container, seeded_market
) -> None:
    dump = pg_container.exec(
        ["pg_dump", "--format=custom", "--compress=0", "--no-owner",
         "--no-privileges", "--dbname", SOURCE_URL]
    )
    with DockerContainer(POSTGRES_IMAGE) as target:
        ...
        # SMOKE — uch da'vo, uchalasi ham FOUND-07 ning matnidan:
        #   (1) moliyaviy qatorlar joyida
        #   (2) RLS policy'lari tiklandi (tenant izolyatsiyasi dumpda bor)
        #   (3) audit jurnali kesilmagan
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|---|---|---|---|
| `pg_dump … \| restic backup --stdin` | `restic backup --stdin-from-command -- pg_dump …` | restic 0.17 (2024) | Quvur yiqilgan dumpni muvaffaqiyat deb yozardi; endi chiqish kodi tekshiriladi |
| restic repo formati v1 (siqishsiz) | repo **v2** + `--compression auto` (standart) | restic 0.14 (2022) | `pg_dump -Z0` + restic siqishi = dedup **va** siqish |
| `restic check --read-data` (butun repo) | `--read-data-subset=5%` (yoki `n/t`) | uzoq vaqtdan beri | Haftalik tekshiruv trafiksiz va vaqtsiz bo'ladi |
| MinIO (S3 ombori) | SeaweedFS 4.40 | MinIO repo **2026-04-25 da arxivlangan** | CLAUDE.md allaqachon ko'chgan; zaxira SeaweedFS hajmini oladi |
| Alpine'da `postgresql-client` | Alpine `v3.22` da eng yangisi **17** | — | `postgres:18.4-trixie` bazasi yagona ishonchli yo'l (Pitfall 7) |
| `middleware.ts` (Next) | `proxy.ts` | Next 16 | `/reports` marshruti locale routing'ga tegmaydi, lekin runbook bandi |

**Deprecated / eskirgan (bu fazada UCHRAMASIN):**
- `openpyxl` bilan YOZISH — CLAUDE.md taqig'i.
- `arq` — `redis[hiredis]<6` talab qiladi, loyihada `8.0.1` pini
  (`test_runtime_deps.py` bloklaydi).
- `aioboto3` — `aiobotocore[boto3]==2.25.1` pini bilan o'rnatib bo'lmaydi.
- **`_freeze_zip` ning test-fikstursdagi joylashuvi** — bu fazada
  mahsulotga ko'chiriladi (Pitfall 3).

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|---|---|---|
| **A1** | `COPY --from=restic/restic:0.19.1 /usr/bin/restic` Debian image'ida ishlaydi (binar `CGO_ENABLED=0` bilan static) | Standard Stack, R-6 | Backup image qurilmaydi → fallback: GitHub releases dan `restic_0.19.1_linux_amd64.bz2`. **Wave 0 zondi bir buyruq: `docker run --rm <image> restic version`** |
| **A2** | Offsite manzil = Backblaze B2 yoki ikkinchi Contabo region | D-14 (CONTEXT ham `[ASSUMED]` deb belgilagan) | Provayder tanlanmagan bo'lsa `RESTIC_REPOSITORY` bo'sh qoladi va zaxira ishlamaydi → `backup_stale` (to'g'ri xulq). Buyurtmachi qarori |
| **A3** | Zaxira vaqti 04:40 Asia/Tashkent | R-10 | Agar bozor 04:00 dan oldin ochilsa yoki NVR arxivi boshqa oynada bo'lsa siljitiladi. Cron qiymatlari bilan solishtirib chiqarildi, mijoz bilan tasdiqlanmagan |
| **A4** | `report_max_period_days = 366`, `report_max_rows = 5000` | Pitfall 13 | Direktor yillik hisobotni bir faylda so'rasa 422 oladi. Chegara `Settings` da → deploy qayta qurilmasdan kengaytiriladi |
| **A5** | Direktor «tushum» deganda YIG'ILGAN pulni tushunadi (`payments.business_date`) | Pitfall 14 | Ikkala ustun ham chiqariladi, ya'ni xato bo'lsa ham ma'lumot yo'qolmaydi — faqat sarlavha nomi o'zgaradi |
| **A6** | `restic check --read-data-subset=5%` haftalik yetarli | Code Example 5 | CLAUDE.md ning o'z qiymati; katta repoda 5 % kam bo'lishi mumkin |
| **A7** | Platforma adminiga `REPORT_VIEW` **berilmaydi** (Pitfall 11 varianti A) | R-1 | Agar buyurtmachi platforma adminidan hisobot ko'rishni talab qilsa — uch fayllik o'zgarish |
| **A8** | `ledger_entries` da bitta kun × bitta rasta = bitta summa | R-4, D-17 | Agar daftar bir kunda bir rastaga ikki yozuv qilsa (ikki kassir) UNIQUE rad etardi → `ON CONFLICT DO UPDATE` oxirgisini oladi |
| **A9** | `alert-list.test.tsx` da `backup_stale` matni RENDER holida o'lchanmagan | Pitfall 15 | Faqat qo'shimcha ish; xavf yo'q |

---

## Open Questions (RESOLVED)

1. **`fn_audit_row()` `id` ustunisiz jadvalda HAQIQATAN yiqiladimi?**
   - **Bilamiz:** funksiya `(v_new ->> 'id')::uuid` yozadi;
     `audit_log.row_id` — `nullable=True`; `NULL::uuid` istisno
     ko'tarmaydi.
   - **Noaniq:** repo'ning uch joyida (`schema_contract.py:374`,
     `deferred-items.md` №4, `binding_repo.py:606`) «yiqilardi» deb
     yozilgan — bu o'lchangan fakt yoki taxminmi?
   - **Tavsiya:** Wave 0 da bitta zond (triggerni vaqtincha ulab bir DML).
     Natijadan qat'i nazar `id uuid` qo'shiladi (D-24), lekin **testning
     da'vosi** natijaga qarab yoziladi. ⛔ «Yiqiladi» deb test yozmang.

2. **Offsite provayder tanlanganmi?**
   - **Bilamiz:** D-14 sozlanadigan S3 endpoint talab qiladi; `.env` da
     hozir hech nima yo'q.
   - **Noaniq:** hisob ochilganmi, byudjet bormi.
   - **Tavsiya:** kod provayderdan MUSTAQIL yoziladi; hisob yo'q bo'lsa
     `08-HUMAN-UAT.md` bandi (egasi Ops) va `backup_stale` alerti
     holatni halol ko'rsatadi — bu bloklamaydi (self-service qoidasi 2).

3. **3 tomonlama solishtiruvda «AI-kutilgan» qaysi tarifni oladi?**
   - **Bilamiz:** D-18 «band rasta × amaldagi tarif» deydi; tariflar
     tarixiy (MARKET-03).
   - **Noaniq:** «amaldagi» = solishtiruv KUNIDAGI tarif (to'g'ri) yoki
     bugungi tarif (noto'g'ri, tarixni buzardi).
   - **Tavsiya:** ⛔ **o'sha kunning tarifi** — `daily_charges` ning
     `tariff_amount_soum` bilan bir xil manba. Aks holda uch ustundan
     ikkitasi bir xil savolga ikki xil javob berardi.

4. **`/reports` da nomuvofiqlik arxivi qaysi ikki manbani birlashtiradi?**
   - **Bilamiz:** D-03 `reconciliation_cases` **va** `billing_anomalies`
     ni sanaydi.
   - **Noaniq:** ular bitta jadvalga birlashtiriladimi yoki ikki bo'limda
     ko'rsatiladimi.
   - **Tavsiya:** ⛔ **ikki bo'lim, birlashtirilmaydi** — 6-faza D-05
     («alohida sanoqlar birlashtirilmaydi») va `AnomalyCounts` ning uch
     alohida hisoblagichi shu qoidani allaqachon o'rnatgan.

5. **Daftar importi kim tomonidan bajariladi va u qaysi huquqni oladi?**
   - **Bilamiz:** D-20 — nazoratchi yoki admin, KASSIR EMAS.
   - **Noaniq:** `INSPECTOR` da bugun **faqat** `OCCUPANCY_REVIEW` bor;
     unga import huquqini berish uning yuzasini kengaytiradi.
   - **Tavsiya:** import **`MARKET_ADMIN`** (mavjud `STALL_MANAGE` yoki
     yangi huquqsiz) uchun; nazoratchi solishtiruvni **KO'RADI**, lekin
     faylni admin yuklaydi. Bu `INSPECTOR` ning tor yuzasini (05-faza
     qarori) saqlaydi. ⚠ Agar buyurtmachi nazoratchining O'ZI yuklashini
     talab qilsa — bu RBAC o'zgarishi va u SUMMARY da nomlanadi.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|---|---|---|---|---|
| Docker Engine | Butun stek, testcontainers | ✓ | 29.4.2 | — |
| Docker Compose | `backup` xizmati, `gate` | ✓ | v5.1.3 | — |
| `postgres:18.4-trixie` image | `backup` bazasi, `test_restore_drill` | ✓ (lokal) | 18.4 | — |
| `restic/restic:0.19.1` image | Backup image build | ✗ **lokal YO'Q** | — | GitHub releases dan static binar (`ADD`) |
| `rclone/rclone` image | (ishlatilmaydi — R-9) | ✗ | — | — |
| `chrislusf/seaweedfs:4.40` | Zaxira manbai (`:ro` mount) | ✓ (lokal) | 4.40 | — |
| Node.js | Frontend build, `i18n:check` | ✓ | 24.14.1 | — |
| npm | `gate` zanjiri | ✓ | 11.11.0 | — |
| Python (xost) | — (hamma narsa konteynerda) | ✓ | 3.14.3 | — |
| `git` | Commit | ✓ | 2.53.0 | — |
| **Offsite S3 endpoint** | FOUND-07 ning «boshqa lokatsiya» talabi | ✗ **sozlanmagan** | — | ⛔ Fallback YO'Q. `08-HUMAN-UAT.md` bandi (Ops) |
| **Toza server (tiklash mashqi)** | D-16(b), SC#3 ning imzosi | ✗ | — | ⛔ Fallback YO'Q. `08-HUMAN-UAT.md` bandi (Ops) |
| **Docker Hub tarmog'i** | `restic/restic` ni birinchi tortish | ⚠ noaniq | — | 07 `deferred-items.md` №5: «bu muhitda Docker Hub'ga tarmoq yo'q» deb yozilgan |
| Disk (`C:`) | Docker VHDX, testcontainers | ⚠ **88 % to'la** (21 GB bo'sh) | — | `docker system prune` + `docker_data.vhdx` compact (foydalanuvchi retsepti) |

**Fallback'siz yo'qolgan bog'liqliklar:**
- **Offsite S3 endpoint** — kod usiz yoziladi va `backup_stale` alerti
  holatni halol ko'rsatadi; bajarilish `08-HUMAN-UAT.md` da.
- **Toza server** — D-16(b) ning yagona bajarilish joyi; SC#3 ning imzosi
  shu bandsiz QO'YILMAYDI.

**Fallback bilan yo'qolganlar:**
- `restic/restic` image → GitHub releases static binari.
- Disk siqiqligi → prune + compact; ⚠ `test_restore_drill` ikki qo'shimcha
  postgres konteynerini ko'taradi.

---

## Validation Architecture

### Test Framework

| Property | Value |
|---|---|
| Framework (backend) | `pytest 9.1.1` + `pytest-asyncio 1.4.0` (`asyncio_mode = "auto"`), `testcontainers 4.15.0` |
| Framework (frontend) | `vitest 4.1.10` + `@testing-library/react` (jsdom) va `node --test` (`frontend/scripts/*.test.mjs`) |
| Config file | `pyproject.toml` (root), `frontend/vitest.config.*`, `compose.yaml` `tests` bloki |
| Quick run command | `npm run gate:fast` (`test:fast` + `frontend test`) — byudjet **200 s** |
| Full suite command | `npm run gate` — byudjet **2300 s** (D-26, o'zgarmaydi) |

### Phase Requirements → Test Map

| Req / SC | Behavior | Test Type | Automated Command | File Exists? |
|---|---|---|---|---|
| **RECON-04 (1)** | Direktor davr tanlaydi va uchala hisobotni ko'radi | integration | `pytest tests/integration/test_reports_api.py -q` | ❌ Wave 0 |
| **RECON-04 (2)** | Har hisobot `.xlsx` bo'lib yuklab olinadi, baytlari DETERMINIK | unit | `pytest tests/unit/test_xlsx_export.py -q` | ❌ Wave 0 |
| **RECON-04 (3)** | Eksportda formula-injection qochirilgan (ism `=cmd\|…` bo'lsa ham) | unit | `pytest tests/unit/test_xlsx_export.py -k injection -q` | ❌ Wave 0 |
| **RECON-04 (4)** | Kassir uchala marshrutdan ham 403 oladi (D-04) | tenancy | `pytest tests/tenancy/test_cross_tenant.py -q` | ✓ (matritsa avtomatik qamraydi) |
| **RECON-04 (5)** | Shaxsiy eksport `audit_read` + `VENDOR_VIEW` e'lon qiladi | tenancy | `pytest tests/tenancy/test_personal_data_coverage.py -q` | ⚠ MAVJUD, **kengaytiriladi** (Pattern 3) |
| **RECON-05 (1)** | Aniqlik hisoboti `/reports` yuzasida davr bilan chiqadi | integration | `pytest tests/integration/test_reports_api.py -k accuracy -q` | ❌ Wave 0 |
| **RECON-05 (2)** | Ikki xato turi ajratilgan va foiz KLIENTDA hisoblanmaydi | component | `npm --prefix frontend run test:component -- reports` | ❌ Wave 0 |
| **RECON-05 (3)** | ⛔ O'lchanmagan davr «0 %» chizmaydi (D-10, WR-05) | component | `npm --prefix frontend run test:component -- accuracy` | ❌ Wave 0 |
| **FOUND-07 (1)** | Zaxira skripti pg_dump nosozligida yurak urishi YOZMAYDI | unit (statik) | `pytest tests/unit/test_backup_contract.py -q` | ❌ Wave 0 |
| **FOUND-07 (2)** | `heartbeat.sql` dagi komponent nomi `alerting.BACKUP_COMPONENT` bilan AYNAN teng | unit | `pytest tests/unit/test_backup_contract.py -k component -q` | ❌ Wave 0 |
| **FOUND-07 (3)** | Yurak urishi yozilgach `/internal/self-check` `backup` ni `never_seen` dan CHIQARADI | integration | `pytest tests/integration/test_backup_heartbeat.py -q` | ❌ Wave 0 |
| **FOUND-07 (4)** | Yurak urishi eskirsa `backup_stale` ko'tariladi | integration | `pytest tests/integration/test_alerting.py -k backup -q` | ⚠ MAVJUD (tekshirilsin) |
| **FOUND-07 (5)** | Dump toza serverga tiklanadi, ma'lumot va RLS joyida | integration (slow) | `pytest tests/integration/test_restore_drill.py -q` | ❌ Wave 0 |
| **FOUND-07 (6)** | Real offsite repodan real serverga tiklash | ⛔ **manual-only** | — | `08-HUMAN-UAT.md` (egasi **Ops**) |
| **SC#4 (1)** | `ops/docs/go-live.md` mavjud va har bandi «buyruq + kutilgan natija» | unit (statik) | `node --test frontend/scripts/…` yoki `pytest tests/unit/test_runbook_shape.py` | ❌ Wave 0 |
| **SC#4 (2)** | Uch tilli inson tekshiruvi (kassir/nazoratchi/admin mashqi) | ⛔ **manual-only** | — | `08-HUMAN-UAT.md` |
| **SC#5 (1)** | Daftar `.xlsx` importi all-or-nothing va idempotent | integration | `pytest tests/integration/test_three_way.py -k ledger -q` | ❌ Wave 0 |
| **SC#5 (2)** | Uch ustun (daftar/tizim/AI-kutilgan) va farq UCH SINFDA ko'rinadi | integration | `pytest tests/integration/test_three_way.py -k diff -q` | ❌ Wave 0 |
| **SC#5 (3)** | Kassir solishtiruv yuzasini ko'rmaydi (D-20) | tenancy | matritsa | ✓ (avtomatik) |
| **Faza** | Beshala mezon BITTA buyruqda | integration | `pytest tests/integration/test_phase8_criteria.py -q` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `npm run gate:fast` (byudjet 200 s — **oshirilmaydi**)
- **Per wave merge:** `npm run gate` (byudjet 2300 s, D-26)
- **Phase gate:** to'liq `gate` yashil + `test_phase8_criteria.py` beshala
  mezon + `08-HUMAN-UAT.md` ning FOUND-07 bandi imzolangan →
  `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/unit/test_xlsx_export.py` — RECON-04 (determinizm + injection)
- [ ] `tests/unit/test_backup_contract.py` — FOUND-07 (skript shakli,
      komponent nomi tengligi, retention qiymatlari LITERAL)
- [ ] `tests/integration/test_reports_api.py` — RECON-04/05
- [ ] `tests/integration/test_backup_heartbeat.py` — FOUND-07 (self-check)
- [ ] `tests/integration/test_restore_drill.py` — FOUND-07 (`@slow`)
- [ ] `tests/integration/test_three_way.py` — SC#5
- [ ] `tests/integration/test_phase8_criteria.py` — beshala mezon
- [ ] `frontend/src/app/[locale]/(app)/reports/page.test.tsx` — SC#1
- [ ] ⚠ **`tests/tenancy/test_personal_data_coverage.py` KENGAYTMASI** —
      per-route ruxsat xaritasi (Pattern 3). Bu **yangi fayl emas**,
      mavjudning ONGLI o'zgarishi va u SUMMARY da nomlanishi shart
- [ ] ⚠ `tests/unit/test_xlsx_template.py::test_template_kinds_are_exactly_three`
      → `..._four` (R-11)
- [ ] Freymvork o'rnatish: **kerak emas** — hammasi mavjud

---

## Security Domain

### Applicable ASVS Categories (level 1)

| ASVS Category | Applies | Standard Control |
|---|---|---|
| **V2 Authentication** | yes (o'zgarishsiz) | Mavjud JWT + `CurrentPasswordDep`; yangi marshrutlar shu zanjirga ulanadi |
| **V3 Session Management** | yes (o'zgarishsiz) | Refresh token httpOnly cookie; eksport `GET` sessiya cookie'si bilan boradi |
| **V4 Access Control** | ⛔ **yes — bu fazaning eng nozik joyi** | `require_permission(REPORT_VIEW)` + `VENDOR_VIEW` shaxsiy hisobotlarda; `test_personal_data_coverage` + cross-tenant matritsa |
| **V5 Input Validation** | yes | Davr parametrlari Pydantic bilan; daftar `.xlsx` — `xlsx_reader` (ZIP/XML bomba) + `validate_ledger_rows` |
| **V6 Cryptography** | yes | ⛔ Hech narsa qo'lda yozilmaydi: restic AES-256 + Poly1305 ni O'ZI qiladi; `RESTIC_PASSWORD` — sir |
| V7 Error Handling & Logging | yes | ⛔ Xom SQL/konstrayt matni javobga TUSHMAYDI (`imports._conflict` naqshi); zaxira nosozligi `stderr` + `backup_stale` |
| V8 Data Protection | ⛔ **yes** | Zaxira shaxsiy ma'lumotni (F.I.Sh., telefon, dalil kadrlar) **VPS'dan tashqariga** chiqaradi — birinchi marta |
| V12 File & Resources | yes | Eksport hajmi chegarasi (Pitfall 13); import hajmi chegarasi (mavjud) |
| V13 API & Web Service | yes | `GET` eksport, `Content-Disposition: attachment`, ASCII fayl nomi |

### Known Threat Patterns for {FastAPI + XlsxWriter + restic/S3}

| Pattern | STRIDE | Standard Mitigation |
|---|---|---|
| **CSV/Excel formula injection** (sotuvchi ismi `=HYPERLINK(...)`) | Elevation of Privilege (mijoz mashinasida) | ⛔ `escape_formula()` + YAGONA `_write_text()` yo'li; `worksheet.write()` to'g'ridan CHAQIRILMAYDI |
| Cross-tenant hisobot (A bozorining direktori B ni ko'radi) | Information Disclosure | RLS (`app.market_id`) + `TenantSessionDep` + cross-tenant matritsa |
| Auditsiz shaxsiy ma'lumot o'qish | Repudiation | `audit_read` + `test_personal_data_coverage` yopiq to'plami |
| **Zaxira sirlarining oshkor bo'lishi** (`RESTIC_PASSWORD`, offsite kalitlar) | Information Disclosure | ⛔ compose faylida LITERAL YO'Q (`${…}` orqali); `.env` git'da emas; `censor_secrets` jurnal qatlamida |
| **Shifrlanmagan offsite arxiv** | Information Disclosure | restic repo'si **har doim** shifrlangan — `rclone sync` (crypt'siz) shuning uchun R-9 da rad etildi |
| Zaxira jarayoni arxivni qayta yozadi / o'chiradi | Tampering | `seaweed:/seaweed:ro` mount; `forget --prune` faqat restic repo'siga tegadi |
| **Yolg'on «muvaffaqiyat»** (qisman dump) | Tampering / Repudiation | `--stdin-from-command` chiqish kodini tekshiradi; yurak urishi FAQAT oxirida |
| Zaxira o'lganda sukunat | Denial of Service (kechiktirilgan) | ⛔ `backup_stale` CRITICAL + `never_suppressed` + `last_seen is None` ham eskirish |
| Katta davr so'rovi = xotira portlashi | Denial of Service | `report_max_period_days` / `report_max_rows` → 422 |
| Zaxiradan tiklangan bazada RLS yo'qolishi | Elevation of Privilege | Tiklash mashqi smoke tekshiruvi **policy'lar mavjudligini** ham talab qiladi (Code Example 7) |
| `psql` ga URL orqali SQL inyeksiyasi | Tampering | `heartbeat.sql` — FAYL, satr birlashtirish YO'Q; `-v day=` bog'langan o'zgaruvchi; `ON_ERROR_STOP=1` |

⚠ **V8 uchun alohida band:** FOUND-07 loyihaning shaxsiy ma'lumotini
**birinchi marta** VPS chegarasidan tashqariga chiqaradi. CLAUDE.md ning
data-rezidentlik cheklovi («davlat bosqichidan oldin O'zbekiston
hostingiga ko'chish») zaxira manziliga ham tegishli. Runbook (D-22) buni
ochiq yozsin: **offsite bucket ham migratsiya ro'yxatida.**

---

## Sources

### Primary (HIGH confidence)

- **Kod bazasi** (o'qildi, satr raqamlari bilan iqtibos qilindi):
  `app/services/accuracy_report.py`, `app/services/xlsx_template.py`,
  `app/api/v1/imports.py`, `app/api/v1/occupancy.py`,
  `app/api/internal/self_check.py`, `app/jobs/alerting.py`,
  `app/repositories/billing_repo.py`, `app/repositories/binding_repo.py`,
  `app/security/rbac.py`, `migrations/entities/triggers.py`,
  `migrations/versions/0002_audit.py`, `migrations/versions/0014_snapshot_domain.py`,
  `migrations/helpers.py`, `packages/sbozor-core/sbozor_core/schema_contract.py`,
  `tests/tenancy/test_personal_data_coverage.py`,
  `tests/tenancy/test_cross_tenant.py`, `tests/unit/test_heartbeat_registry.py`,
  `tests/unit/test_xlsx_template.py`, `tests/fixtures/karmana_seed.py`,
  `tests/conftest.py`, `compose.yaml`, `package.json`, `frontend/package.json`,
  `frontend/src/components/shell/app-shell.tsx`, `.env.example`
- **Rejalashtirish artefaktlari:** `.planning/phases/08-*/08-CONTEXT.md`,
  `.planning/ROADMAP.md` §Phase 8 + §Post-Launch, `.planning/REQUIREMENTS.md`,
  `.planning/STATE.md`, `06-*/deferred-items.md`, `07-*/deferred-items.md`,
  `07-REVIEW-backend.md`, `07-REVIEW-frontend.md`, `04-HUMAN-UAT.md`,
  `07-VALIDATION.md`, `CLAUDE.md`
- **restic rasmiy hujjati** — `restic.readthedocs.io/en/stable/040_backup.html`
  (`--stdin` ogohlantirishi va `--stdin-from-command` ning chiqish kodi
  semantikasi), `.../045_working_with_repos.html`
  (`check --read-data-subset` formatlari), `.../manual_rest.html`
  (`--compression` = `auto|off|fastest|better|max`, standart `auto`,
  **repo formati v2 talab qiladi**)
- **restic manba kodi** — `github.com/restic/restic/docker/Dockerfile`
  (baza `alpine:latest`, `ca-certificates fuse openssh-client tzdata jq`,
  binar `/usr/bin/restic`), `build.go:141,165` (`CGO_ENABLED=0` standart)
- **Docker Hub v2 API** — `restic/restic` teglari: `0.19.1` (2026-07-05),
  `latest` (2026-07-05), `0.19.0` (2026-06-09), `0.18.1` (2025-09-21)
- **Alpine paket indeksi** (`pkgs.alpinelinux.org`) —
  `postgresql18-client`: `edge` da BOR, `v3.22` da YO'Q
- **Muhit zondlari** — `docker --version` (29.4.2),
  `docker compose version` (v5.1.3), `node` (24.14.1), `npm` (11.11.0),
  `docker images` (postgres:18.4-trixie, seaweedfs:4.40, valkey mavjud;
  restic YO'Q), `df -h /c` (88 % to'la)

### Secondary (MEDIUM confidence)

- **GitHub Releases sahifasi** (WebFetch) — restic 0.19.1 = 2026-07-05,
  0.19.0 = 2026-06-09; Docker Hub API bilan **kesishtirib tasdiqlandi**
- `pg_dump` major-versiya qoidasi (pg_dump ≥ server major) — PostgreSQL
  ning uzoq yillik xulqi; ⚠ bu yerda rasmiy hujjatdan iqtibos
  KELTIRILMADI, R-6 uni baribir strukturaviy ravishda yopadi (bir xil
  image)

### Tertiary (LOW confidence — validatsiya talab qiladi)

- **⛔ Bitta WebSearch natijasi YOLG'ON chiqdi va u yozib qo'yiladi:**
  qidiruv `restic/restic` image'ining eng yangi tegi `0.18.1` va u
  «8 oy oldin push qilingan» dedi. Docker Hub API buni **rad etdi**:
  `0.19.1` mavjud va 2026-07-05 da push qilingan. Xulosa: **registry
  API'lari qidiruv natijasidan ustun** va bu fazaning versiya
  da'volarining hammasi API'dan olingan
- `COPY --from=restic/restic` ning Debian'da ishlashi — manba
  (`build.go`) bo'yicha **kuchli**, lekin **empirik o'lchanmagan** (A1)

---

## Metadata

**Confidence breakdown:**

| Area | Level | Reason |
|---|---|---|
| Mavjud mexanizmlar (aniqlik hisoboti, alert halqasi, import quvuri, xlsx himoyasi) | **HIGH** | Kod o'qildi, satr raqamlari bilan iqtibos qilindi; ikkita da'vo (`_freeze_zip` joylashuvi, `PERSONAL_ROUTES` hosila ekani) CONTEXT.md ni **tuzatadi** |
| Darvozalar ro'yxati va ularning qizarish sabablari | **HIGH** | Har darvozaning manbasi va assertioni bevosita o'qildi |
| restic semantikasi (`--stdin-from-command`, `--compression`, `check`) | **HIGH** | Rasmiy hujjat + manba kodi |
| restic 0.19.1 mavjudligi va sanasi | **HIGH** | Docker Hub v2 API + GitHub releases (ikki manba) |
| Backup image qurilishi (`COPY --from` static binar) | **MEDIUM** | `build.go` `CGO_ENABLED=0` beradi, lekin ishga tushirish **o'lchanmagan** → A1, Wave 0 zondi |
| Alpine paket holati | **MEDIUM-HIGH** | `pkgs.alpinelinux.org` HTML javobi; teskari yo'l (R-6) buni ahamiyatsiz qiladi |
| `fn_audit_row()` ning `id` ustunisiz xulqi | **LOW** | Manba kodi «yiqilmaydi» deyapti, repo hujjatlari «yiqiladi» deyapti — **Open Question 1**, Wave 0 zondi |
| Offsite provayder va tiklash mashqi | **LOW (tashqi)** | Ops qarori; `08-HUMAN-UAT.md` da, bloklamaydi |
| Davr chegaralari va «tushum» semantikasi | **MEDIUM** | Sxemadan hosila; buyurtmachi bilan tasdiqlanmagan (A4, A5) |

**Research date:** 2026-08-13
**Valid until:** **2026-09-12** (30 kun) — kod bazasi bo'yicha topilmalar
faza davomida amal qiladi; restic/Alpine versiyalari uchun 7 kunlik oyna
(tez o'zgaradigan registry ma'lumoti)
