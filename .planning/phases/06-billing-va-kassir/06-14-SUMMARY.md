---
phase: 06-billing-va-kassir
plan: 14
subsystem: faza-darvozasi
tags: [criteria, sabotage, meta-test, budget, validation, requirements, i18n]
requires:
  - "06-01…06-13 (14 rejaning oldingi 13 tasi merge qilingan)"
  - "tests/fixtures/billing_domain.py (06-05) — ikki variant"
  - "app/jobs/billing_close.py (06-07), app/repositories/billing_repo.py (06-06)"
  - "GET /billing/*, POST /payments, /shifts (06-08/09/10)"
  - "collect-session.test.tsx, payment-bar.test.tsx (06-11) — G-20/G-21"
provides:
  - "tests/integration/test_phase6_criteria.py — SC#1..SC#5 + G-1/G-2/G-3/G-6 + soxtalashtirish taqig'i"
  - "MINIMUM_MATRIX_ROUTES = 80 (o'lchangan: 88)"
  - "collect.recentEmpty / collect.shiftOpened / collect.declaredInvalid — uchala locale, EKRANGA ULANGAN"
  - "06-VALIDATION.md — 42 qatorli Per-Task Verification Map, imzo, human_only_verifications"
  - "REQUIREMENTS.md — to'qqiz talab DALIL bilan Done"
affects:
  - ".planning/ROADMAP.md (06-14 belgisi; faza belgisi TEGILMADI)"
  - "deferred-items.md 6- va 8-bandlar YOPILDI"
tech-stack:
  added: []
  patterns:
    - "Mezon moduli o'z qabul mezonini (matn skani) BUZMASLIGI uchun taqiq reyestri ish vaqtida QURILADI"
    - "D-11 ikki tomondan: bajariladigan nomlarda suzuvchi arifmetika YO'Q + har kasr konstanta [0, 1] da"
    - "Frontend da'vosi konteynerda subprocess bilan emas, DARVOZAGA ULANGANI bilan o'lchanadi"
key-files:
  created:
    - "tests/integration/test_phase6_criteria.py"
  modified:
    - "tests/tenancy/test_route_coverage.py"
    - "frontend/messages/{uz-Latn,uz-Cyrl,ru}.json"
    - "frontend/src/components/collect/{collect-session,shift-open-card,shift-close-form}.tsx"
    - "frontend/src/components/collect/shift-close-form.test.tsx"
    - ".planning/phases/06-billing-va-kassir/{06-VALIDATION.md,deferred-items.md}"
    - ".planning/{REQUIREMENTS.md,ROADMAP.md}"
decisions:
  - "SC#4(b)/SC#5(b) subprocess BILAN EMAS — `tests` konteynerida `node`/`npm` YO'Q (o'lchandi)"
  - "S-1 yashil qoldi -> HOLAT kengaytirildi (test emas), ikkinchi urinishda QIZARDI"
  - "G-3 ning tiplar to'plami rejadagi taxmin emas, O'LCHANGAN qiymat (`boolean` yo'q, `time` bor)"
  - "nyquist_compliant HAMON false — `gate` byudjeti o'lchanmadi va band YASHIRILMADI"
metrics:
  duration: "~4 soat (bir transport uzilishi bilan)"
  completed: 2026-08-11
  tasks: 3
  commits: 5
---

# Phase 6 Plan 14: Faza darvozasi, sabotaj va yakunlash Summary

**Beshala ROADMAP mezoni endi BITTA buyruqda o'lchanadi va uchala meta-darvoza
(mezon boshiga bitta test · ro'yxatni modul introspeksiyasidan hosila qiluvchi
meta-test · soxtalashtirishsiz o'lchov) yashil; beshta sabotajdan to'rttasi
qizardi, bittasi yashil qoldi va u TESTNI emas, HOLATNI kengaytirish bilan
tuzatildi; `gate` byudjeti esa O'LCHANMADI va bu ochiq band sifatida yozildi.**

---

## Koordinator so'ragan uchta javob — birinchi navbatda

**1. Beshala mezon BITTA buyruqda mexanik o'lchanadimi? — ✅ HA.**

```
docker compose --profile test run --rm tests pytest tests/integration/test_phase6_criteria.py -q
```

→ **12 test, hammasi yashil** (oxirgi yugurish sabotajlar qaytarilgandan keyin).
Modul 1949 satr; unda SC#1…SC#5 (har biri AYNAN bitta nomlangan test, docstringida
ROADMAP mezonining so'zma-so'z matni), `test_every_criterion_has_its_own_test`,
`test_criteria_module_uses_no_fakes`, `test_the_fake_registry_names_are_built_correctly`,
`test_g2_…`, `test_g3_…`, `test_g6_…` va bir nazorat testi bor. O'lchov HAQIQIY
`postgres:18.4`, HAQIQIY SeaweedFS va HAQIQIY marshrut grafi ustida — mock YO'Q.

**2. `06-VALIDATION.md` ning `## Manual-Only Verifications` jadvali bo'sh qoldimi?
— ✅ HA, BO'SH.**

Va bu **fazaning natijasi** sifatida yozildi, unutilgan band sifatida emas: D-01
bajarildi, to'qqizala talabning har jumlasi CI'da real artefakt bilan o'lchanadi.
⛔ Shu sababdan **`06-HUMAN-UAT.md` fayli YARATILMADI** (3- va 5-fazadan farqli).
⚠ Frontmatterdagi `human_only_verifications` ro'yxati (4 band) bu bilan
ZIDDIYATLI EMAS: u talab JUMLALARI emas, inson idroki / real qurilma / tashkiliy
shart haqidagi bandlar va ularning har birida `owner` va `trigger` bor.

**3. i18n kalitlar soni: 1106 × 3 → ✅ 1109 × 3.**

```
[i18n:gen --check] drift yo'q
[i18n:check] 1109 kalit × 3 til — kalit va ICU parity to'liq
```

Uchta yangi kalit (`collect.recentEmpty`, `collect.shiftOpened`,
`collect.declaredInvalid`) uchala locale'da va **uchalasi ham o'z ekraniga
ULANGAN** — mavjud, lekin chizilmaydigan kalit hech nimani yopmasdi.

---

## Nima qilindi

### Task 1 — `test_phase6_criteria.py` (commit `15ff931`)

| Mezon | Testi | Nima o'lchanadi |
|---|---|---|
| SC#1 | `test_sc1_immutable_daily_charge_is_written_once` | O'tmishdagi OCHIQ kunda `day_close` → `billing_close`; hisob AYNAN ikki rastada (2 slotli AI + nazoratchi tasdiqlagan), summa `tariffs` qatoridan **o'qib** solishtiriladi; qayta yugurish `charged=0`, qiymatlar va `created_at` o'zgarmaydi. **Ichida ketma-ketlik darvozasi**: materializatsiyasiz `charged==0` **VA** `no_slot_rows>0` |
| SC#2 | `test_sc2_charge_reaches_evidence_and_cannot_be_edited` | Dalil zanjiri **oxirigacha**: `daily_charges` → `charge_evidence` → `occupancy_events.snapshot_id` → `GET /snapshots/{id}/image` **200 + `image/jpeg` + AYNAN o'sha baytlar** (HAQIQIY SeaweedFS, direktor sessiyasi). `UPDATE`/`DELETE` → `RaiseException`; `charge_adjustments` o'tadi va `audit_log` o'sadi |
| SC#3 | `test_sc3_debt_is_computed_and_unassigned_becomes_anomaly` | Qoldiq hisoblanadi; biriktirilmagan band rasta → **0 hisob + 1 anomaliya**; `balance*` ustuni **to'plam tengligi** bilan yo'q; D-24 — `ALLOCATION_RULE` FIFO, `payment_allocations` jadvali va `allocated*` ustuni yo'q |
| SC#4 | `test_sc4_pending_projection_and_three_step_confirmation` | `/billing/pending` kalitlari AYNAN yetti, `charge_id` **yo'q**; summa `resolve_stall_day_money()` va `pending_projection()` dan **ikki chaqiruv, bir natija**; sabab-kodsiz summa → **422** |
| SC#5 | `test_sc5_idempotent_payment_reversal_and_blind_variance` | Bir kalit ikki marta → 1 qator + **200** + o'sha `id`; `UPDATE payments` → `RaiseException`; storno yangi qator, sababsizi `CheckViolation`; `close` javobida `system_*` **yo'q**; variance FAQAT `GET /shifts?day=` da, **−5 000** va **+7 000** |

**Meta-darvozalar.** `test_every_criterion_has_its_own_test` ro'yxatni
`inspect.getmembers` bilan **moduldan hosila** qiladi (o'z nomida `sc<raqam>` yo'q).
`test_criteria_module_uses_no_fakes` ikki mustaqil yo'ldan yuradi (`ast` daraxti +
modul global nomlari va test imzolari) va bu fazaga xos D-11 taqig'ini qo'shadi.

**Qabul mezonlari (grep bilan o'lchandi):** `inspect.getmembers` → 2 ta;
`unittest.mock|MagicMock|monkeypatch|patch\(` → **0**;
`\bfloat\(|Decimal|round\(` → **0**; satr soni **1949** (min 700).

### Task 2 — sabotaj, matritsa, byudjet (commit `553aefc`)

### Task 3 — validatsiya, talablar, ROADMAP (commit `f59c1b0`)

- `06-VALIDATION.md`: 42 qatorli Per-Task Verification Map (14 reja × 3 vazifa,
  har qatorda bo'sh bo'lmagan `Automated Command`), Wave 0 ning o'nala bandi `[x]`,
  `human_only_verifications` (4) + `automated_replacements` (6).
- `REQUIREMENTS.md`: to'qqizala band `Done`, har biri uchun **o'lchagan test
  nomma-nom** va «Nima o'lchanMAGAN» ustuni. `check-requirements-sync.mjs` yashil
  (49 talab; Done 30 · Pending 17 · Blocked 2).
- `ROADMAP.md`: `06-14` `- [x]`; **faza belgisi TEGILMADI**.

### Kechiktirilgan 6- va 8-bandlar (commit `7f63871`)

| Kalit | Ekran | Nega mavjud kalit yaramasdi |
|---|---|---|
| `collect.recentEmpty` | `collect-session.tsx` — bo'lim endi HAR DOIM chiziladi | Ilgari bo'sh ro'yxatda butun bo'lim yo'qolardi: yo'qlik NOSOZLIK bilan bir xil ko'rinardi |
| `collect.shiftOpened` | `shift-open-card.tsx::onSuccess` toasti | `collect.shiftOpen` = «Smenani ochish» — **buyruq**, natija emas |
| `collect.declaredInvalid` | `shift-close-form.tsx`, `aria-describedby` bilan bog'langan | `tariffs.amountInvalid` bu yerda **yolg'on** bo'lardi — §10.2 nolni AYNAN ruxsat etadi |

⚠ `shift-close-form.test.tsx` ning bir asserti yangilandi: u vaqtincha
`collect.declaredLabel` (maydon **nomi**) ni kutardi, testning o'z izohi esa
«bosish SABABNI e'lon qiladi» deydi — endi u sababni o'lchaydi.

---

## Sabotaj — beshtasi, har biriga IKKI SAVOL (D-30)

> (a) sabotaj o'lchanayotgan tizimga **yetib bordimi**?
> (b) umuman biror test bu ikki holatni **ajrata oladimi**?

### S-0 (meta) — `test_sc3_*` nomdan chiqarildi → ⛔ **QIZARDI**

- (a) **Ha** — modul funksiyalari ro'yxati o'zgardi.
- (b) **Ha, AYNAN BITTASI**: `test_every_criterion_has_its_own_test` qizardi,
  qolgan testlar yashil qoldi (SC#3 ning tanasi joyida edi, faqat yig'ilmadi).
  Ya'ni darvoza o'z da'vosidan kengroq narsani ushlamaydi.

### S-1 — `write_charge`: `on_conflict_do_nothing` → `on_conflict_do_update` → ⚠ **YASHIL QOLDI**

- (a) **HA, YETIB BORDI** va bu o'lchandi: `billing_close` `errors` ro'yxatida
  `billing_close_failed:DBAPIError` paydo bo'ldi — `DO UPDATE` `daily_charges`
  ustidagi o'zgarmaslik triggeriga urildi (P0001) va job istisnoni **yutdi**.
- (b) **YO'Q, HECH BIR TEST AJRATA OLMASDI.** Uchala mavjud assert ham ikkala
  shoxda bir xil natija berardi: qator soni o'zgarmasdi (`DO UPDATE` yiqildi),
  `amount_soum` va `created_at` ham o'zgarmasdi. **Bu 05-15 ning S-D sinfining
  aynan takrori.**
- **Tuzatish TESTDA emas, HOLATDA** (majburiy): SC#1 ga ikki assert qo'shildi —
  qayta yugurish `errors` **BO'SH** bo'lishi va `skipped_existing` mavjud
  hisoblarni **TANIGAN** bo'lishi shart. Ma'no farqi: idempotentlik «hech nima
  o'zgarmadi» emas, «job qatorni ALLAQACHON BOR deb tanidi va JIM o'tdi».
- **Ikkinchi urinish → ⛔ QIZARDI** (`assert again.errors == []` yiqildi).

### S-2 — `ALTER TABLE daily_charges DISABLE TRIGGER USER` (o'lchanayotgan bazada) → ⛔ **QIZARDI**

- (a) **Ha** — `Failed: DID NOT RAISE RaiseException`, ya'ni `UPDATE` haqiqatan
  o'tib ketdi. Sabotaj 05-11 darsi bo'yicha **testning o'z sessiyasida**,
  o'lchanayotgan bazada bajarildi.
- (b) **Ha** — SC#2 yolg'iz o'zi ajratadi.

### S-3 — D-28 anomaliya shoxi chetlab o'tildi → ⛔ **QIZARDI**

- (a) **Ha** — `write_charge()` `ValueError: … sotuvchi biriktirilmagan (D-28)`
  bilan yiqildi, ya'ni oqim haqiqatan hisob yo'liga burildi.
- (b) **Ha** — SC#3 ning anomaliya asserti va yugurishning o'zi.
- ⚠ **REJADAGI KUTILGAN QIZIL YETIB BO'LMAYDIGAN EKAN.** Reja «`daily_charges`
  da 1 qator paydo bo'ladi» degan edi; amalda **bu imkonsiz**:
  `daily_charges.vendor_id` — `NOT NULL` va `write_charge()` `INSERT` dan
  **oldin** rad etadi. Ya'ni invariant **ikki joyda** qo'riqlangan (job shoxi +
  repozitoriy guard) va sabotaj buni ko'rsatdi.

### S-4 — `PendingStallResponse` ga `charge_id` qo'shildi → ⛔ **QIZARDI**

- (a) **Ha** — javobda kalit paydo bo'ldi (`extra items: 'charge_id'`).
- (b) **Ha** — SC#4(a) ning **to'plam tengligi**. ⚠ `not in` shakli buni
  ushlardi, lekin `chargeId` ni ushlamasdi — tenglik ikkalasini ham ushlaydi.

### S-5 — `variance()` → `abs(declared − system)` → ⛔ **QIZARDI**

- (a) **Ha** — hisobotda `variance_soum: 5000` (manfiy o'rniga musbat).
- (b) **Ha, LEKIN FAQAT KAMOMAD SHOXI.** Ortiqcha (`+7 000`) sabotajdan **o'tib
  ketdi** — aynan shuning uchun ikki yo'nalish **har xil kattalikda** tanlangan
  (−5 000 va +7 000): teng kattalikda bo'lganda ikkala assert ham yashil qolardi.

**Hamma sabotaj QAYTARILDI.** `git status` da mahsulot kodi toza; oxirgi yugurish
(`test_phase6_criteria.py` + `test_route_coverage.py`) — **20 test yashil**.

---

## `MINIMUM_MATRIX_ROUTES` — o'lchangan son bilan

`len(tenant_resource_routes(app))` = **88** (2026-08-11), ulardan **AYNAN 11 tasi**
6-fazaniki va ular kod izohida nomma-nom sanaladi:

```
GET  /billing/pending · /billing/charges · /billing/charges/{charge_id} · /billing/anomalies   (4)
POST /payments · /payments/{payment_id}/reverse · GET /payments/recent                          (3)
POST /shifts · /shifts/{shift_id}/close · GET /shifts · GET /shifts/open                        (4)
```

Chegara **60 → 80**. ⚠ Farq (20) 11 dan katta va bu ham o'lchangan fakt: konstanta
05-12 dan beri ko'tarilmagan, ya'ni faza oxirida amaldagi sondan **17 ta** orqada
qolgan edi. Yangi qiymat faylning **o'z konventsiyasini** tiklaydi (amaldagi sondan
~8 past — 02-10 dan beri saqlanadigan masofa). Shart `>=` bo'lgani uchun 06-08 uni
ATAYIN ko'tarmagan edi va u haq edi.

---

## ⛔ Byudjet — O'LCHANMADI (ochiq band)

⛔ **Bu bo'limni to'g'ri o'qing: `npm run gate` bu rejada TO'LIQ yugurmadi va uning
vaqti O'LCHANMADI.** «Yashil» degan da'vo BERILMAYDI.

| Qadam (05-15 W0-13 protokoli) | Holat |
|---|---|
| 1. Disk tekshiruvi (`C:` da ≥ 10 GB) | ✅ **15 GB bo'sh / 162 GB, 92 % to'la** — shart bajarildi |
| 2. Tinch xost | ✅ **8 ta begona konteyner to'xtatildi**: `frosty_benz`, `priceless_sammet`, `parnikkpi-{bot,celery_worker,frontend,backend,db,redis}-1`. O'lchovdan keyin **TIKLANADI** (pastdagi bandga qarang) |
| 3. 1-yugurish (sovuq) | ❌ **~33 % da uzildi** (transport xatosi, testlar emas). O'sha nuqtagacha birorta **qizil yo'q** edi |
| 4. 2- va 3-yugurish | ❌ boshlanmadi |
| 5. `gate:fast` nazorat o'lchovi | ❌ olinmadi |
| 6. Tarqoqlik (%) | ❌ hisoblanmadi (o'lchov yo'q) |

**Oqibat va qaror:**

- Byudjet ⛔ **O'ZGARTIRILMADI**: `package.json` dagi `//gate-budget` ham,
  `06-VALIDATION.md` ham hamon **1250 s**. Ikki joyda son **BIR XIL** (grep bilan
  tasdiqlandi), lekin u **05-15 ning** o'lchovi (1009 / 1004 / 983 s), 6-fazaniki
  emas. 6-faza ~6 jadval, ~11 marshrut, ~15 komponent va ~10 test fayli qo'shdi —
  ya'ni 241 s zaxira yetarli ekani **TASDIQLANMAGAN**.
- `06-VALIDATION.md` ning `nyquist_compliant` bayrog'i shu sababdan ⛔ **`false`**
  qoldi. `node scripts/check-validation-signoff.mjs` buni tasdiqlaydi:
  «`nyquist_compliant: false` — hisob-kitob bilan MOS · Per-Task qatorlari: 42 ·
  inson bandlari: 4 · Ochiq qoidalar (1)».
- ⛔ Bandni `human_only_verifications` ga ko'chirish **YOLG'ON** bo'lardi: u
  avtomatlashtirilmaydigan emas — shunchaki **yugurtirilmagan**.

**Yopish yo'li (bir qadam):** tinch xostda `npm run gate` uch marta; oshmasa
byudjet o'zgarmaydi va ikkala band `[x]` bo'ladi; oshsa yangi chegara = eng yomon
o'lchov × 1,20 (50 ga yuqoriga yaxlitlanadi) va u **ikki joyda BIR XIL** yoziladi.

**Bu rejada TO'LIQ yugurgan va YASHIL bo'lgan darvozalar** (byudjet o'lchovidan
alohida):

| Buyruq | Natija |
|---|---|
| `pytest tests/integration/test_phase6_criteria.py -q` | ✅ **12 test** |
| `pytest tests/integration/test_phase6_criteria.py tests/tenancy/test_route_coverage.py -q` | ✅ **20 test** |
| `ruff format --check` + `ruff check` + `mypy` (o'zgargan fayllar) | ✅ toza |
| `npm --prefix frontend test` | ✅ **182 node-test + 717 vitest / 52 fayl** |
| `npm --prefix frontend run typecheck` · `run lint` | ✅ toza |
| `npm --prefix frontend run i18n:check` | ✅ **1109 × 3**, parity to'liq |
| `node scripts/check-requirements-sync.mjs` | ✅ exit 0 |
| `node scripts/check-validation-signoff.mjs` | ✅ bayroq hisob-kitobga MOS |

---

## Deploy

⛔ **`docker compose up -d --force-recreate scheduler`** — 06-07 dan meros va u
**MAJBURIY**: cron jadvali `worker.py` **import paytida** o'qiladi, ya'ni
`BILLING_CLOSE_CRON = "10 4 * * *"` yangi konteynerda ro'yxatga olinadi.
⛔ **Buni hech bir test ushlamaydi.** Yagona mexanik himoya — yurak urishining
yo'qligi: band unutilsa 26 soatdan keyin `billing_close_stale` alerti ochiladi va
`/internal/self-check` javobida `billing_close` `never_seen` ro'yxatida turadi.

---

## Deviatsiyalar

### Avtomatik tuzatilgan

**1. [Rule 3 — bloklovchi] SC#4(b)/SC#5(b) subprocess bilan o'lchab bo'lmaydi**

- **Qayerda:** Task 1.
- **Nima:** Reja «`npm --prefix frontend test -- collect-session` nol kod bilan
  chiqadi» deb talab qilardi. **O'lchandi:**
  `docker compose --profile test run --rm tests sh -c "which npm node"` → **bo'sh**.
  `tests` konteyneri Python image'i; unda `node` ham, `npm` ham **yo'q**. Ikkinchi,
  mustaqil sabab: `frontend` ning `test` skripti
  `node --test scripts/*.test.mjs && vitest run` zanjiri, ya'ni `--` dan keyingi
  argument **birinchi** buyruqqa yopishardi va vitest filtri umuman ishlamasdi.
- **Yechim:** sanoq **qayta yozilmadi** (ikkinchi implementatsiya = ikkinchi
  haqiqat). O'rniga ikki mustaqil da'vo o'lchanadi: (1) sanoq testi **mavjud** va
  matnida chegara **aynan** yozilgan (`toBe(3)`, `toHaveLength(1)`); (2)
  `package.json::gate` zanjiri o'sha to'plamni **haqiqatan yugurtiradi**
  (`npm --prefix frontend test` satri bor). `pytest.skip` yo'li **ATAYIN
  qo'yilmadi**.

**2. [Rule 1 — xato] G-3 ning tiplar to'plami rejada noto'g'ri**

- Reja `{uuid, bigint, date, text, timestamptz, boolean}` deb yozgan edi.
  **O'lchov:** `boolean` oltala jadvalda **umuman yo'q**, `charge_evidence.slot_time`
  esa `time without time zone`. To'plam **o'lchangan qiymat** bilan almashtirildi
  va izohda sabab yozildi. `boolean` ni «har ehtimolga qarshi» qoldirish to'plam
  tengligini **yolg'on** qilardi.

**3. [Rule 1 — xato] SC#5(d) ning stsenariy tartibi**

- Birinchi yozilishda storno tizim summasini **nolga** tushirar, keyin
  `declared < system` holatini ifodalab bo'lmasdi (manfiy deklaratsiyani
  `ck_cashier_shifts_declared_soum_non_negative` rad etadi). Storno va variance
  o'lchovi orasiga **yangi to'lov** qo'shildi.

**4. [Rule 3 — bloklovchi, infratuzilma] `ops/seaweedfs/s3.json` worktree'da yo'q edi**

- Fayl `.gitignore` da (lokal sir). `docker compose` uning o'rniga **katalog**
  yaratdi va `sbozor-storage-1` `fail to load config file … is a directory` bilan
  nosog'lom bo'lib qoldi — bu **umumiy** konteyner.
- **Yechim:** konteyner to'xtatildi, katalog o'chirildi, `s3.json.example` asosida
  compose'ning standart rekvizitlari bilan fayl yozildi, `.env` asosiy
  checkout'dan nusxalandi (ikkalasi ham `git check-ignore` bilan tasdiqlangan —
  commitga tushmaydi). `docker compose up -d storage --wait` → **healthy**.
- ⚠ **Bu asosiy checkout'ning `sbozor` compose loyihasiga TEGDI** (worktree ham,
  asosiy checkout ham `name: sbozor` ostida ishlaydi). Faqat `storage` qayta
  yaratildi; qolgan konteynerlarga tegilmadi.

**5. [Rule 1 — xato] `fastapi_app.routes` bo'sh to'plam berardi**

- Nazorat testi `app.routes` dan marshrut izlardi; v1 yuzasi **alohida ilova**
  sifatida `mount` qilingan, ya'ni ildizda faqat `/healthz`, `/docs` ko'rinadi.
  `app.openapi()["paths"]` ga o'tildi + `>= 40` quyi chegarasi qo'shildi.

### Rejadan ataylab chetlanish

**Mezonlarning kuni — seedning kuni EMAS.** Reja «`billing_domain` seedida
`billing_close(D)`» degan edi; `SEED_BUSINESS_DATE` (2026-09-01) **kelajakda** va
`ck_daily_charges_service_date_not_in_future` u kunga hisob yozishni rad etadi
(06-07 da o'lchangan fakt). Mezonlar `_open_past_day()` bilan **o'tmishdagi ochiq
kunni** tanlaydi va `PastDay` egasi o'sha kunning kadr/hodisa qatlamini yozadi.
`billing_domain_before_day_close` varianti ishlatiladi, `day_close` ni mezonning
o'zi chaqiradi — ya'ni **ketma-ketlik darvozasi saqlanadi**.

### `files_modified` dan tashqarida tegilgan fayllar (koordinator ruxsat bergan)

| Fayl | Sabab |
|---|---|
| `frontend/messages/{uz-Latn,uz-Cyrl,ru}.json` | 6/8-bandlar — uchta kalit |
| `frontend/src/components/collect/{collect-session,shift-open-card,shift-close-form}.tsx` | kalitlarni EKRANGA ulash (ulanmagan kalit hech nimani yopmaydi) |
| `frontend/src/components/collect/shift-close-form.test.tsx` | assert vaqtincha maydon NOMINI kutardi; endi SABABNI o'lchaydi |
| `.planning/phases/06-billing-va-kassir/deferred-items.md` | 6- va 8-bandlar YOPILDI deb belgilandi |

---

## Ochiq bandlar

1. ⛔ **`gate` byudjeti o'lchanmadi** — yuqoridagi «Byudjet» bo'limi. Bu rejaning
   yagona bajarilmagan qabul mezoni.
2. ✅ **YOPILDI — begona konteynerlar TIKLANDI.** O'lchov uchun to'xtatilgan 8 ta
   konteyner (`frosty_benz`, `priceless_sammet`, `parnikkpi-{db,redis,backend,frontend,celery_worker,bot}-1`)
   `docker start` bilan qaytarildi va `docker ps` bilan tasdiqlandi — sakkiztasi
   ham ishlayapti. ⚠ `sbozor-storage-1` esa endi **worktree'ning**
   `ops/seaweedfs/s3.json` fayliga bog'langan (4-deviatsiya): worktree
   o'chirilgach asosiy checkout uni o'z yo'lidan qayta yaratadi
   (`docker compose up -d storage`).
3. **`day_close` yurak urishining ko'rinmasligi** (06-07 dan meros,
   `deferred-items.md` 2-band, 5-faza domeni) — `occupancy.day_close` cron'i
   ro'yxatga olinmasa nosozlik JIMGINA qoladi.
4. **Ochiq buyurtmachi savollari OQ-3/OQ-4/OQ-6/OQ-7** — bular manual verification
   EMAS, `[ASSUMED]` standart qiymat bilan qurilgan **parametr**. Tetigi:
   buyurtmachining javobi; sozlash nuqtalari UI-SPEC §17 (O-01…O-07) jadvalida.
5. **`deferred-items.md` 3-, 7- va 9-bandlar** ochiq (7-band bu rejada qisman
   yopildi — backend darvozasi yugurtirildi; 3 va 9 boshqa fazalarniki).
6. ⚠ **Phase-5 flaky:** `test_blind_audit.py::test_a_different_round_number_draws_a_different_sample`
   to'liq to'plamda ba'zan qizaradi (`deferred-items.md` 1-band). **Bu 6-fazaning
   regressiyasi EMAS** va bu rejaning birorta yugurishida uchramadi.

---

## Self-Check: PASSED

**Fayllar:**

- `tests/integration/test_phase6_criteria.py` — FOUND (1949 satr)
- `.planning/phases/06-billing-va-kassir/06-14-SUMMARY.md` — FOUND
- `.planning/phases/06-billing-va-kassir/06-HUMAN-UAT.md` — ⛔ **YO'Q va bu KUTILGAN**
  (`## Manual-Only Verifications` bo'sh)

**Commitlar:**

- `15ff931` test(06-14): beshta faza mezoni bitta buyruqda, uchta darvoza bilan
- `7f63871` feat(06-14): uchta copy bo'shlig'i yopildi va EKRANGA ULANDI (6/8-band)
- `553aefc` test(06-14): beshta sabotaj, S-1 ning holat kengaytmasi va o'lchangan matritsa chegarasi
- `f59c1b0` docs(06-14): validatsiya imzosi, to'qqiz talab dalil bilan va ROADMAP ro'yxati

---
*Phase: 06-billing-va-kassir · Plan: 14 · 2026-08-11*
