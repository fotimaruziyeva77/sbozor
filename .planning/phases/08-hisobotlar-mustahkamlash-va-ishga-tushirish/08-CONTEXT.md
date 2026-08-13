# Phase 8: Hisobotlar, mustahkamlash va ishga tushirish - Context

**Gathered:** 2026-08-13
**Status:** Ready for planning

> ⚙ **`--auto` rejimida yig'ildi.** Foydalanuvchining doimiy ko'rsatmasi
> (`no-questions-autonomous-mode`, 2026-08-01): savol berilmaydi, **tavsiya
> etilgan variant** tanlanadi va zanjir davom etadi. Har kulrang soha uchun
> tanlangan variant va **sababi** quyida ochiq yozilgan — ular qaror sifatida
> qulflanadi, taxmin sifatida emas.

<domain>
## Phase Boundary

Bu faza **yangi funksiya fazasi EMAS — mustahkamlash haftasi** (ROADMAP:
«hafta 12 — yangi funksiya emas, mustahkamlash haftasi»). U to'rt narsani
yetkazadi:

1. **Direktor raqamlarni O'ZI chiqarib oladi** (RECON-04): tushum
   (kunlik/oylik), qarzdorlik reestri, nomuvofiqlik arxivi — har biri
   `.xlsx` bo'lib yuklab olinadi.
2. **AI aniqlik hisoboti direktor yuzasiga chiqadi** (RECON-05): ko'r audit
   namunasidan, «band deb xato» (nizo xavfi) va «bo'sh deb xato»
   (yo'qotish) ajratilgan — 5-fazada QURILGAN hisob qayta ishlatiladi.
3. **Tizim tiklanishi ISBOTLANADI** (FOUND-07): kunlik avtomatik backup
   (Postgres + obyekt-ombor) boshqa lokatsiyaga + toza serverda tiklash
   mashqi.
4. **Go-live tayyorgarligi**: runbook, 3 tomonlama solishtiruv vositasi
   (daftar vs tizim vs AI-kutilgan), uch tilli yakuniy tekshiruv, va
   6/7-fazalardan **egasi «8-faza» deb yozilgan** mustahkamlash qarzlari.

**Qamrovda:** RECON-04, RECON-05, FOUND-07; SC#4 (runbook + 3 til + mashq);
SC#5 (3 tomonlama solishtiruv); `deferred-items.md` bandlari — 06 №9,
07 №1-qo'shimcha, №2, №4, №5-ochiq-qismi, №7a (13 WR), №7b (Info bandlari).

**⛔ Qamrovdan TASHQARIDA:**
- **Yangi qobiliyat emas** — direktor botining buyruq yuzasi, sotuvchi
  botidan to'lov, to'liq interaktiv xarita, kassir offline-lite (V2).
- **AI-02 ni yopish** — real ONNX artefakti va oltin to'plam bu fazaning
  ishi emas (`05-HUMAN-UAT.md` #1–#3, egasi nazoratchi + Ops). Aniqlik
  hisoboti faqat MAVJUD ko'r-audit ma'lumotidan chiqadi.
- **Parallel rejimning O'ZI** (hafta 13–16) — bu faza faqat VOSITANI
  quradi; kunlik solishtiruv operatsion tartib, build emas.
- **Phase 0 baza varaqalari** — solishtiruv vositasi ularga
  BOG'LANMAYDI (self-service qoidasi 2: tashqi bog'liqlik hech qachon
  bloklamaydi); baza kelsa, taqqoslash nuqtasi sifatida keyin ulanadi.

</domain>

<decisions>
## Implementation Decisions

### Hisobot yuzasi va davr modeli (RECON-04)

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

### Excel eksport mexanikasi (RECON-04)

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

### AI aniqlik hisoboti (RECON-05)

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

### Backup va tiklash mashqi (FOUND-07)

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

### 3 tomonlama solishtiruv vositasi (SC#5)

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

### Go-live runbook, 3 til va mustahkamlash qarzlari (SC#4)

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

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Faza doirasi va talablar
- `.planning/ROADMAP.md` §«Phase 8» (503–518-qatorlar) — maqsad, 5 mezon,
  timeline; §«Post-Launch: Parallel rejim» (520–526) — solishtiruv
  tartibining qat'iy qoidalari (kassir emas, qat'iy cutover).
- `.planning/REQUIREMENTS.md` — FOUND-07 (18-qator), RECON-04/05
  (72–73-qatorlar).
- `.planning/STATE.md` §Blockers — Phase 0 tushum bazasi (8-fazaning
  taqqoslash nuqtasi, LEKIN bloklamaydi), AI-02 holati.

### ⛔ Meros qarz reyestrlari (BIRINCHI O'QILADI — bu fazaning ish ro'yxati)
- `.planning/phases/06-billing-va-kassir/deferred-items.md` **№9** — ism
  joini 50 sahifa chegarasi: uch RAD ETILGAN yo'l va «tabiiy egasi —
  8-fazaning hisobot yuzasi» qarori (D-07 ning manbasi).
- `.planning/phases/07-nomuvofiqlik-bildirishnoma-va-botlar/deferred-items.md`
  — №1-qo'shimcha (alert-list render), №2 (recon ism sahifalash), №4
  (`market_notification_settings` audit migratsiyasi, yechim shakli
  docstringda), №5-ochiq-qismi (`npm run up` qo'lda tasdiqlash), №6
  (dayjest kaliti — KENGAYTIRILMAYDI, D-25), №7a (13 WR jadvali), №7b
  (Info bandlari).
- `.planning/phases/03-*/03-HUMAN-UAT.md`, `04-*/04-HUMAN-UAT.md`,
  `05-*/05-HUMAN-UAT.md`, `07-*/07-HUMAN-UAT.md` — go-live oldi
  ro'yxatining manbalari (D-22).

### Mavjud mexanizmlar (qayta ishlatiladi, takrorlanmaydi)
- `services/core-api/app/services/accuracy_report.py` — Wilson,
  `ConfusionMatrix`, `AccuracyReport`; RECON-05 ning YAGONA hisob manbai
  (D-09).
- `services/core-api/app/api/v1/occupancy.py` +
  `app/repositories/occupancy_repo.py` — aniqlik hisobotining mavjud API
  yuzasi.
- `services/core-api/app/services/xlsx_template.py` — `_freeze_zip`
  determinizm naqshi (D-05) va xavfsiz xlsx o'qish/yozish intizomi.
- `services/core-api/app/api/v1/imports.py` — all-or-nothing import
  naqshi (D-17 shu infratuzilmani qayta ishlatadi).
- `services/core-api/app/jobs/alerting.py` — `ALERT_META`,
  `EXPECTED_COMPONENTS`, `alert_sweep`, heartbeat naqshi (D-15).
- `services/core-api/app/worker.py` — cron reyestri; yangi komponentlar
  ro'yxatga kiradi (7-faza D-17 qoidasi).
- `services/core-api/app/repositories/billing_repo.py` —
  `vendor_outstanding()`, `pending_projection()` (qarzdorlik reestri va
  solishtiruvning arifmetika manbai).
- `CLAUDE.md` §Backups — restic/pg_dump/retention/restore-drill qat'iy
  tanlovlari; §Supporting Libraries — XlsxWriter (openpyxl eksportda
  taqiq).

### Meros qilib olinadigan qarorlar
- `.planning/phases/06-billing-va-kassir/06-CONTEXT.md` — D-07
  (o'zgarmaslik), D-11 (pul turi), saqlangan agregat taqiqi (D-03/D-07
  ning manbasi).
- `.planning/phases/07-nomuvofiqlik-bildirishnoma-va-botlar/07-CONTEXT.md`
  — D-03 (dalil-kadr chegaradan chiqmaydi — hisobot eksportiga RASM
  KIRMAYDI, faqat havola/identifikator), D-17 (cron reyestri), D-30
  (atamalar lug'ati).
- `.planning/phases/06-billing-va-kassir/06-VALIDATION.md` — `gate`
  2300 s / `gate:fast` 200 s byudjeti (D-26).
- `.planning/phases/05-*/05-UI-SPEC.md` §11 — aniqlik hisoboti
  formulalari va «o'lchanmagan son chizilmaydi» qoidasi (D-09/D-10).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`accuracy_report.py`** — RECON-05 ning hisobi TAYYOR; faza faqat yuzani
  va eksportni qo'shadi.
- **`xlsx_template.py::_freeze_zip`** — bayt-determinik xlsx; eksport
  modullari shu naqshda yoziladi.
- **Import infratuzilmasi** (`imports.py`, shablon, all-or-nothing) — daftar
  importi (D-17) uchun tayyor poydevor.
- **`system_heartbeats` + `EXPECTED_COMPONENTS` + `ALERT_META`** — backup
  kuzatuvining (D-15) mavjud uyi.
- **`vendor_outstanding()` / `daily_charges` / `payments` /
  `reconciliation_cases`** — uch hisobotning arifmetika manbalari; yangi
  hisob yo'li ochilmaydi.
- **`nuqs`** (stekda) — hisobot filtrlarining URL sinxroni (D-02).

### Established Patterns
- **Hosila, saqlanmaydi** — balans, hit-rate, endi hisobot agregatlari va
  AI-kutilgan ustun ham (D-03, D-18).
- **O'lchanmagan son chizilmaydi** (05-13/05-14) — aniqlik hisoboti va
  WR-05 tuzatishining qoidasi (D-10).
- **Muvaffaqiyat yo'qligi = alert** (CLAUDE.md, 7-faza D-17) — backup
  komponenti (D-15).
- **Yopiq reyestr + parity darvoza** — huquqlar (rbac.py↔rbac.ts),
  atamalar (D-06), alert kalitlari.
- **Har eksport/o'qish auditda** — shaxsiy ma'lumotli hisobot bitta
  `audit_read` yozadi (D-07; 02-19 naqshi).

### Integration Points
- **Yangi `/reports` marshruti** frontendda (`src/app/[locale]/(app)/reports`)
  va yangi hisobot API moduli (`api/v1/`) — marshrut qamrovi matritsasi va
  cross-tenant testlarga ULANADI (mavjud darvozalar avtomatik talab qiladi).
- **Yangi compose xizmati `backup`** — `compose.yaml` + `EXPECTED_COMPONENTS`
  + `ALERT_META` + uch locale alert matni (D-15); deploy bandi: `scheduler`
  singari qayta yaratish talab qilinadi.
- **Yangi migratsiya(lar)**: daftar import jadvali (D-21) va
  `market_notification_settings.id uuid` (D-24/07-№4) — `0024+`.
- **13 WR + Info bandlari** frontend/backend bo'ylab tarqoq mayda
  tuzatishlar — mustahkamlash to'lqini sifatida rejalashtiriladi.

</code_context>

<specifics>
## Specific Ideas

- **Hisobot «hujjat» sifatida his qilinishi kerak**: davr tanlandi →
  ekranda ko'rildi → bitta bosishda `.xlsx` — direktor uchun ≤3 qadam
  (Apple-uslub minimallik constraint'i shu yuzada ham amal qiladi).
- **Solishtiruv hisobotida farq uch sinfda ko'rinadi**: daftar > tizim
  (yo'qotish shubhasi), tizim > daftar (daftar kamchiligi/xato),
  AI-kutilgan ≠ tizim (bandlik-billing farqi) — har sinf o'z qatorida,
  bitta «farq bor» yig'indisiga siqilmaydi (6-faza D-05 sinfi: alohida
  sanoqlar birlashtirilmaydi).
- **Go-live runbook o'qib bajariladigan bo'lishi kerak** — har band
  «buyruq + kutilgan natija» shaklida; «tekshiring» kabi fe'lsiz band
  qabul qilinmaydi (mavjud `verify-real-nvr.sh` / `verify-tunnel.sh`
  skriptlari namuna).

</specifics>

<deferred>
## Deferred Ideas

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

</deferred>

---

*Phase: 8-Hisobotlar, mustahkamlash va ishga tushirish*
*Context gathered: 2026-08-13*
