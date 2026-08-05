---
phase: 4
slug: snapshot-pipeline
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-08-04
measured: 2026-08-05
updated: 2026-08-05
human_only_verifications:
  - item: Sifat chegaralarini real Karmana kadrida sozlash
    why_not_automatable: Chegaralar hozir LOW confidence — real kadr yo'q. Sintetik JPEG generatori MEXANIZMNI isbotlaydi, QIYMATNI emas; chegara bilan nomlangan fixture testni o'z farazining aks-sadosiga aylantirardi
    owner: Nazoratchi (baholaydi) + ijrochi (SQL yozadi)
    trigger: Phase 0 ning real kadrlari kelganda — 06:00 va 18:00 slotlari majburiy
  - item: 90 kunlik saqlash siyosatining kalendar bo'yicha ishlashi
    why_not_automatable: Vaqtni kutib bo'lmaydi. Test chegarani sozlama (full_days=0), vaqtni argument (today=) qilib mexanizmni isbotlaydi; 90 kalendar kunni faqat vaqtning o'zi isbotlaydi
    owner: Ops
    trigger: go-live + 90 kun (birinchi full -> compressed to'lqini); +455 kun (birinchi purged)
  - item: Tiklash mashqi (restore drill)
    why_not_automatable: Zaxirani tiklash real ombor, real ma'lumot va toza server talab qiladi. Zaxira olindi bilan zaxiradan tiklandi ikki boshqa da'vo
    owner: Ops
    trigger: go-live'dan oldin, 8-fazada (FOUND-07)
  - item: Telegram alertining haqiqatan yetib borishi
    why_not_automatable: Bot tokeni, chat ID va tarmoq CI'da yo'q. respx HTTP kontraktini o'lchaydi; haqiqiy Bot API ga borish testni tashqi xizmatga bog'lardi va soxta yashil test alert ishlayapti degan yolg'on ishonch berardi (Pitfall 10)
    owner: Ops
    trigger: bot sozlanganda — .env ga TELEGRAM_BOT_TOKEN va TELEGRAM_CHAT_ID yozilgan kun
  - item: Tashqi dead-man's switch (D-21)
    why_not_automatable: v1 da bu qatlam uchun kod yozilmaydi — u bitta URL sozlash. O'lchanadigan hodisa VPS butunlay o'lishi, ya'ni ichkaridagi hech bir kod alert yubora olmaydigan holat
    owner: Ops
    trigger: VPS deploy'idan keyin, domen va TLS ishlagan kun
  - item: Real NVR'da sessiya chegarasining kadr olishga ta'siri
    why_not_automatable: Simulyator RTSP sessiya limitini umuman modellamaydi (3-faza tekshiruvida ochiq yozilgan). Chegara firmware va bitreytga bog'liq va sonning o'zi faqat qurilmada o'lchanadi
    owner: Ops
    trigger: real NVR ulanganda — WireGuard tunneli ko'tarilgach
  - item: Planer istisnosi haqiqiy Sentry loyihasida ko'rinadi
    why_not_automatable: Darvoza sentry_sdk.init() ning chaqirilishini va yutilgan on_ready istisnosining capture_exception ga borishini o'lchaydi — hodisaning haqiqiy Sentry loyihasiga YETIB BORISHINI emas. CI'da DSN yo'q; uchinchi tomon xizmatiga boradigan test soxta yashil ishonch berardi (Telegram bandi bilan aynan bir xil sabab, Pitfall 10)
    owner: Ops
    trigger: .env ga haqiqiy SENTRY_DSN yozilgan kun — Sentry loyihasi ochilib DSN olingandan keyin
automated_replacements:
  - was: 90 kunni kutish (saqlash siyosati amalda ishlaydimi)
    now: pytest tests/integration/test_retention.py tests/integration/test_phase4_criteria.py -k sc4 -q — RetentionPolicy(full_days=0) + retention_daily(today=<sana>), haqiqiy SeaweedFS ustida
  - was: Telegram yetkazilishini kutish (xabar keldimi)
    now: pytest tests/integration/test_alerting.py tests/integration/test_phase4_criteria.py -k sc5 -q — respx bilan HTTP kontrakti — nechta so'rov, qaysi yo'lga, tanasida nima yo'q
  - was: Real buzuq kadrni kutish (NVR yaroqsiz kadr bersa)
    now: pytest tests/integration/test_snapshot_quality.py -q — nvr-sim ning frame_mode boshqaruvi + tests/fixtures/frames.py sintetik JPEG generatori
  - was: Yarim tunda gate ni ishga tushirib flaky testni kutish
    now: pytest tests/tenancy/test_snapshot_domain_meta.py -q — _anchor_today() bugungi kunga qat'iy bog'langan qator yozadi, ya'ni soat holatiga bog'liqlik yo'q
  - was: Deploy'da yangi jarayon kuzatuvsiz qolganini payqashni kutish
    now: pytest tests/unit/test_sentry_processes.py -q — darvoza SANAMAYDI: compose.yaml da SENTRY_DSN oladigan HAR servis uchun kirish nuqtasini command dan chiqaradi va o'sha obyektning hodisa reyestrida init_sentry( bo'lishini talab qiladi; topilmagan har bosqich pytest.fail
  - was: Deploy'da planer istisnosining Sentry'ga borishini kutish
    now: pytest tests/integration/test_phase4_criteria.py -k sc5 tests/unit/test_scheduler_observability.py -q — subprocess zondi planer jarayonida SENTRY_ACTIVE=True beradi (nazorat yugurishi DSN'siz False) va ObservedScheduler.on_ready yutilgan istisnoni capture_exception ga uzatib qayta ko'taradi
---

# Phase 4 — Validation Strategy

> Fazani ijro qilish davomida teskari aloqa namunasini olish uchun validatsiya kontrakti.
> **Manba:** `04-RESEARCH.md` § `Validation Architecture`, `04-PATTERNS.md` §5 (Wave 0, 11 band), `04-UI-SPEC.md` darvozalari (G-1…G-7 + W0-F7).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 (`asyncio_mode=auto`) · vitest (frontend) · `node:test` (skript darvozalari) |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`) · `frontend/vitest.config.ts` |
| **Quick run command** | `npm run gate:fast` — 4-fazada o'lchandi: **68 s**, chegara **180 s (O'ZGARMADI)** |
| **Full suite command** | `npm run gate` — 4-fazada eng yomon o'lchov: **745 s**, yangi chegara **900 s** (`04-12` da qayta belgilandi) |
| **Slow lane** | `npm run test:sim:slow` (`-m "sim and slow"`) — `gate` dan ataylab tashqarida |
| **Markerlar** | `tenancy`, `sim`, `hardware`, `slow` — **yangi marker kerak emas** (W0-11 buni tasdiqlaydi, qo'shmaydi) |

**Bu fazada tug'iladigan infratuzilma:**

| Komponent | Nima uchun | Wave 0 bandi |
|---|---|---|
| `taskiq scheduler` konteyneri | D-02 — holatsiz 1-daqiqalik tik | **W0-3** |
| `storage` (SeaweedFS) xizmati | CAM-07 — S3-mos arxiv | **W0-4** |
| `tests/fixtures/frames.py` — sintetik JPEG generatori | **Usiz sifat filtri darvoza emas, konventsiya** | **W0-9** |
| `nvr-sim` ning `frame_mode` boshqaruvi | Buzuq kadrni MediaMTX **bera olmaydi** — u yaroqli oqim beradi, ya'ni baytlarni sim boshqarishi shart | **W0-10** |

---

## Sampling Rate

- **Har task commitidan keyin:** `npm run gate:fast`
- **Har to'lqindan keyin:** `npm run gate`
- **`/gsd-verify-work` dan oldin:** to'liq to'plam yashil
- **Task darajasidagi chegara:** **180 s** — o'zgarmaydi (3-fazada 32 s o'lchangan, 5.6× zaxira sog'lom)

### 3-fazadan meros qolgan band: to'lqin chegarasi

3-faza qayta bajarish qismini yopdi (`gate` 1000 s → **538 s**, qamrov kamaymadi: 1520 ⊃ 412 ⊃ 76), lekin chegarani **1200 s da qoldirdi** va buni ochiq band sifatida shu fazaga topshirdi. Sabab yozib qo'yilgan: 538 s ga 2.2× zaxira — **signal bo'shashgan**, ya'ni sekinlashuv chegaraga urilguncha uzoq sezilmaydi.

**Bu fazaning qarori:** chegara **bir necha yugurish o'lchovi** asosida qayta belgilanadi, bitta o'lchov bilan emas. Bu faza `storage` va `scheduler` konteynerlarini qo'shadi, ya'ni bazaviy vaqt o'sadi — shuning uchun:

| Qadam | Kim | Nima | Holat |
|---|---|---|---|
| 1 | Wave 0 rejasi | 3× o'lchov (sovuq / issiq / issiq) **yangi konteynerlar bilan** | ✅ **BAJARILDI (04-01)** — pastdagi jadval |
| 2 | Yakuniy reja | Yana 3× o'lchov, chegara = eng yomon + 20 % | ✅ **BAJARILDI (04-12)** — pastdagi jadval |
| 3 | — | Agar yangi chegara 1200 s dan past bo'lsa — **tushiriladi**; oshsa — sabab bilan asoslanadi | ✅ **TUSHIRILDI: 1200 s -> 900 s** |

⚠ **Jimgina oshib ketish yoki jimgina bo'sh qoldirish — ikkalasi ham qabul qilinmaydi.**

### 1-qadam o'lchovlari (04-01, 2026-08-04) — `storage` + `scheduler` bilan

| # | Holat | `npm run gate` | Chiqish kodi |
|---|---|---|---|
| 1 | **sovuq** (`frontend/.next` yo'q, `node_modules` yangi o'rnatilgan) | **490 s** | 0 |
| 2 | issiq | **466 s** | 0 |
| 3 | issiq | **461 s** | 0 |

`npm run gate:fast` — **49 s** (chegara **180 s**, o'zgarmadi; 3.7× zaxira).

**O'lchov sharti:** `sim:up` endi `storage` ni ham ko'taradi (SeaweedFS 4.40) va
`compose` da `scheduler` ta'rifi bor, lekin u `gate` zanjirida ishga
**tushirilmaydi** (planer obyekti `04-07` da tug'iladi), ya'ni bu qiymatlar
`storage` ning narxini o'z ichiga oladi, `scheduler` ning narxini **emas**.
`04-12` ning uchta o'lchovi to'liq zanjirda olinadi va farq shu bandda ko'rinadi.

**Kuzatuv:** uchala qiymat ham 3-fazaning 538 s bazasidan **past** (461–490 s),
ya'ni ikkita yangi konteyner qo'shilgani bilan zanjir sekinlashmadi. Sabab
o'lchanmagan (ehtimol docker qatlamlarining issiqligi va xost holati), shuning
uchun chegara **bu rejada o'zgartirilmaydi** — bitta seriya bir seansda
olingan va u chegarani qayta belgilash uchun yetarli emas. Qaror `04-12` da,
olti o'lchov asosida.

### 2-qadam o'lchovlari (04-12, 2026-08-05) — TO'LIQ zanjir

| # | Holat | `npm run gate` | Chiqish kodi |
|---|---|---|---|
| 4 | **sovuq** (`docker compose down -v`, `frontend/.next` o'chirilgan, hamma konteyner olib tashlangan) | **745 s** | 0 |
| 5 | issiq | **691 s** | 0 |
| 6 | issiq | **695 s** | 0 |

`npm run gate:fast` — **68 s** (chegara **180 s**, O'ZGARMADI; **2.6×** zaxira).

**O'lchov sharti va uning `04-01` dan FARQI — bu farq qaror uchun muhim:**

1. **«Sovuq» ning ta'rifi qattiqroq.** `04-01` da sovuq = `frontend/.next`
   yo'q. Bu yerda sovuq = `docker compose down -v` (BARCHA konteynerlar
   olib tashlangan, `pgdata` va `seaweed` **volume**lari o'chirilgan) **+**
   `frontend/.next` o'chirilgan. Ya'ni 745 s — yangi mashinadagi birinchi
   yugurishga eng yaqin qiymat.
   ⚠ Volume o'chirilgani uchun S3 bucket ham yo'qoldi va u o'lchovdan
   **OLDIN** qayta yaratildi (`weed shell` bilan, `ops/seaweedfs/README.md`
   §3). Bu bir martalik ta'minot qadami, ya'ni u `04-01` ning `npm install`
   qadami bilan bir toifa va o'lchov oynasidan tashqarida.
2. **To'plam kattalashdi.** `04-01` o'lchagan paytda `04-02`…`04-11` ning
   testlari hali YO'Q edi. Bugungi sanoq: pytest **1 875**, tenancy **481**,
   vitest **338**, node **115**, i18n **777 × 3**. Ya'ni 461 s va 745 s ni
   solishtirish ikki xil to'plamni solishtirishdir — va aynan shuning uchun
   chegara **eng yomoni** bo'yicha, o'rtacha bo'yicha emas.
3. **`scheduler` endi zanjirda emas, lekin `storage` HAR pytest yugurishida
   ko'tariladi** (`04-12` da `tests` xizmatiga `depends_on: storage`
   qo'shildi). Planer obyekti mavjud, lekin `gate` uni ishga tushirmaydi —
   uning narxi bu sonlarga KIRMAYDI va bu ochiq aytiladi.

### ⛔ CHEGARA QARORI — olti o'lchov asosida

| Manba | Qiymatlar |
|---|---|
| `04-01` (2026-08-04) | 490 · 466 · 461 |
| `04-12` (2026-08-05) | **745** · 691 · 695 |
| **Eng yomoni** | **745 s** |
| Hisob | 745 × 1.20 = 894 |
| **Yangi chegara** | **900 s** (894 yuqoriga yaxlitlandi) |

**Qaror: 1200 s -> 900 s (TUSHIRILDI).** Sabab 3-fazadan meros qolgan
bandning o'zi: 1200 s bugungi eng yomon qiymatga **1.61×** zaxira berardi
va u «bo'shashgan signal» — sekinlashuv chegaraga urilguncha uzoq
sezilmasdi. 900 s esa **1.21×**, ya'ni bitta issiq yugurishning ~30 %
sekinlashuvi darhol ko'rinadi.

⚠ **NEGA O'RTACHA EMAS, ENG YOMONI.** O'rtacha (591 s) chegarani 710 s ga
tushirardi va u sovuq yugurishni (745 s) HAR SAFAR qizartirardi — ya'ni
darvoza «shovqin» bo'lib, birinchi haftadayoq e'tibordan chiqardi.
Chegaraning vazifasi — REGRESSIYANI ushlash, holat farqini emas.

⚠ **`gate:fast` 180 s da QOLADI va u o'zgartirilmadi.** Joriy o'lchov 68 s
(2.6× zaxira). 3-fazadagi 32 s dan ikki barobar o'sdi — sabab o'lchandi:
`gate:fast` endi vitest to'plamini ham 283 -> **338** test bilan yuritadi
va `tests` konteyneri `storage` ni kutadi. 2.6× hali ham sog'lom va
chegarani qisqartirish flakiga olib kelardi (xost yuki bu zanjirga
kuchliroq ta'sir qiladi — u qisqa).

### ⛔ 3-qadam o'lchovlari (04-14, 2026-08-05) — CHEGARADAN OSHDI

**Bu bo'lim yomon xabarni yozadi va uni yumshatmaydi.**

| # | Holat | `npm run gate` | Chiqish kodi |
|---|---|---|---|
| 7 | issiq, seansning O'RTASIDA (oldidan to'liq `pytest`, `tenancy`, `vitest`, `node`, `i18n` va `gate:fast` yugurgan) | **1 009 s** | 0 |
| 8 | issiq, 7-yugurishdan darhol keyin, **AYNAN o'sha kod ustida** | **1 174 s** | 0 |

**Ikkalasi ham 900 s chegarasidan YUQORI (+12 % va +30 %).**

⚠ **CHEGARA KO'TARILMAYDI.** 900 s qarori olti o'lchovga tayanadi
(yuqoridagi jadval) va uni bitta ifloslangan seans bilan qayta belgilash
darvozani mazmunsiz qilardi — aynan «bo'shashgan signal» muammosining
qaytishi bo'lardi.

#### Nega bu REGRESSIYA DEB YOZILADI, lekin sabab BU FAZANING KODIDA EMAS

7- va 8-yugurishlar orasida **kod umuman o'zgarmagan** (`git status` faqat
bitta hujjat qatorini ko'rsatgan), shunga qaramay **zanjirning HAR bosqichi
sekinlashdi** — shu jumladan bu fazaga umuman aloqasi yo'q bosqichlar:

| Bosqich | 7-yugurish | 8-yugurish | Farq |
|---|---|---|---|
| `vitest` umumiy davomiyligi | 58.47 s | 79.55 s | **+36 %** |
| `vitest` `environment` (jsdom) | 225.94 s | 282.90 s | **+25 %** |
| `next build` — `Compiled successfully` | 10.9 s | 13.5 s | **+24 %** |
| `next build` — `Finished TypeScript` | 18.7 s | 20.9 s | **+12 %** |
| 51 statik sahifa generatsiyasi | 1 894 ms | 2 500 ms | **+32 %** |

**Hal qiluvchi nazorat o'lchovi** — `gate:fast`, AYNAN bir xil ish hajmi
ustida (uchala yangi unit test ikkala o'lchovda ham mavjud edi):

| Qachon | `gate:fast` |
|---|---|
| Seans BOSHIDA (ikkala `gate` dan OLDIN) | **68 s** — `04-12` bazasi bilan AYNAN teng |
| Seans OXIRIDA (ikkala `gate` dan KEYIN) | **129 s** — **+90 %** |

Ya'ni o'zgarmagan ish hajmi bir seans ichida ikki barobarga sekinlashdi.
Bu **xost tomonidagi PROGRESSIV degradatsiya** (Windows ustidagi Docker
Desktop uzluksiz og'ir IO ostida) va u o'lchovni ifloslantiradi.

#### Bundan kelib chiqadigan halol xulosa

1. ✅ **Darvozaning O'ZI yashil:** `npm run gate` ikki marta ham **exit 0**;
   to'plam mazmuni bo'yicha regressiya YO'Q (sonlar pastdagi bazaviy
   jadvalda).
2. ⛔ **Davomiylik bo'yicha «regressiya yo'q» degan da'vo BU SEANSDA
   BERIB BO'LMAYDI** — o'lchov vositasining o'zi ishonchsiz ekani
   o'lchandi. Buni «yashil» deb yozish `04-12` ning olti o'lchovli
   qaroriga yolg'on ustun qo'shish bo'lardi.
3. 📌 **Ochiq band (egasi: 5-fazaning validatsiya rejasi):** chegara
   TINCH xostda, seansning boshida, kamida uch o'lchov bilan qayta
   tekshirilsin. Agar tinch xostda ham 900 s dan oshsa — sabab qidiriladi;
   oshmasa — chegara o'z joyida qoladi va bu bo'lim tarix bo'lib qoladi.
   ⚠ Chegarani ko'tarish faqat SHU o'lchovdan keyin muhokama qilinadi.
4. ⚠ **Amaliy ogohlantirish:** xost shu holatda qolsa `npm run gate`
   dasturchining mashinasida ham chegaraga urilishi mumkin. Bu darvozaning
   nosozligi emas — u aynan shu narsani ko'rsatish uchun qo'yilgan.

---

## Per-Task Verification Map

*Har PLAN.md taski uchun bitta qator — `gsd-planner` to'ldiradi. `Status` ustunini ijrochi to'ldiradi.*

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 04-01/T1 | 04-01 | 1 | CAM-07 | T-04-01…05, T-04-SC | Prod bog'liqliklari to'g'ri guruhda; `storage`/`scheduler` profilsiz; `s3.json` da `anonymous` yo'q; ombor porti publish qilinmagan | unit | `pytest tests/unit/test_runtime_deps.py tests/unit/test_storage_config.py -q` | yangi | ✅ green |
| 04-01/T2 | 04-01 | 1 | CAM-06 | T-04-17 | `GENERATED STORED` ustun kompozit FK nishoni bo'la oladimi — haqiqiy `postgres:18.4` da o'lchanadi (D-23) | tenancy | `pytest tests/tenancy/test_billable_anchor_probe.py -q` | yangi | ✅ green — **`BILLABLE_ANCHOR_SUPPORTED = true`** |
| 04-01/T3 | 04-01 | 1 | CAM-05 | T-04-06, T-04-07, T-04-08 | Besh jadval reyestrlari va kaskad tartibi migratsiyadan oldin; `PENDING_AUDIT_TRIGGERS` ikki tomonlama qulfi (darvoza **yashil** qoladi); `markets.timezone` invarianti; `ix_capture_runs_overdue` istisnosi | tenancy | `pytest tests/tenancy/test_meta.py tests/integration/test_market_delete_guard.py -q` | mavjud (kengaytiriladi) | ✅ green |
| 04-02/T1 | 04-02 | 1 | CAM-06 | T-04-09 | Sintetik kadr fizik xususiyat bilan yasaladi (`mean`/`stddev`/to'yinganlik), determinstik va JPEG tolerans kodda | unit | `pytest tests/unit/test_frame_fixtures.py -q` | yangi | ✅ green |
| 04-02/T2 | 04-02 | 1 | CAM-06 | T-04-10, T-04-13 | Sim buzuq/kesilgan/bo'sh/HTML javobni buyurtma bilan beradi; noma'lum `frame_mode` rad etiladi; yangi rekvizit qo'shilmaydi | integration (`sim`) + unit | `pytest tests/integration/test_nvr_sim.py tests/unit/test_compose_sim_env.py -q` | mavjud (kengaytiriladi) | ✅ green |
| 04-02/T3 | 04-02 | 1 | CAM-04, FOUND-06 | T-04-11, T-04-12, T-04-14, T-04-15 | G-1…G-4, G-10 darvozalari; `IR`/`Telegram` override; `ъ` ning ikki ma'nosi; hedging ikkala reyestrda | node gate | `node --test frontend/scripts/snapshot-copy.test.mjs frontend/scripts/gen-cyrillic.test.mjs frontend/scripts/error-codes.test.mjs frontend/scripts/nvr-copy.test.mjs` | yangi + mavjud | ✅ green |
| 04-03/T1 | 04-03 | 2 | CAM-04, CAM-05, CAM-06 | T-04-17, T-04-18 | Beshta model, kompozit FK va `UNIQUE (id, is_billable)`; `business_date` `scheduled_at` dan; indeks nomlari enum'dan hosila | unit (metadata) | `pytest tests/unit/test_enums.py -q` + `mypy packages` | yangi | ✅ green |
| 04-03/T2 | 04-03 | 2 | CAM-04, CAM-05, CAM-06, CAM-07 | T-04-18, T-04-19, T-04-21, T-04-22 | RLS+policy beshta jadvalda; audit trigger faqat ikkitasida va `PENDING_AUDIT_TRIGGERS` dan ikkala nom **o'chiriladi**; `EXCLUDE` va qisman indekslar; `downgrade()` ishlaydi | tenancy + migration | `npm run migrate && pytest tests/tenancy/test_meta.py -q` | yangi | ✅ green |
| 04-03/T3 | 04-03 | 2 | CAM-04, CAM-05, FOUND-06 | T-04-16, T-04-20 | Kaskad besh jadvalni qamraydi; `capture_due_markets()` faqat identifikator beradi; standart 7 slotli profil avtomatik | tenancy + integration | `pytest tests/tenancy/test_snapshot_domain_meta.py tests/integration/test_market_delete_guard.py -q` | yangi | ✅ green |
| 04-04/T1 | 04-04 | 2 | CAM-07, FOUND-06 | T-04-28, T-04-29 | Sirlar `SecretStr`; bo'sh S3 kaliti ishga tushishda yiqitadi; `.env.example` ↔ `Settings` parity | unit | `pytest tests/unit/test_snapshot_settings.py -q` | yangi | ✅ green |
| 04-04/T2 | 04-04 | 2 | CAM-06 | T-04-24, T-04-25, T-04-26, T-04-31 | `dark` ikki shartli; kesilgan va HTML javob dekodsiz tutiladi; `LOAD_TRUNCATED_IMAGES is False`; `MAX_IMAGE_PIXELS` chegaralangan | unit | `pytest tests/unit/test_quality_filter.py -q` | yangi | ✅ green |
| 04-04/T3 | 04-04 | 2 | CAM-05, CAM-07 | T-04-27, T-04-30 | Kalit faqat UUID+ISO sana+`HHMM` dan (yo'l chiqishi mumkin emas); xato reyestri 11 kod, hosila to'plamlar metadan | unit | `pytest tests/unit/test_object_key.py tests/unit/test_capture_errors.py -q` | yangi | ✅ green |
| 04-05/T1 | 04-05 | 3 | CAM-05 | T-04-32, T-04-33, T-04-34, T-04-35, T-04-38 | `ensure_plan` idempotent; `SKIP LOCKED` parallelda kesishmaydi; lease qaytaradi; `grace` dan chiqqan `missed`; auth-locking darhol `failed` | integration | `pytest tests/integration/test_capture_repo.py -q` | yangi | ✅ green |
| 04-05/T2 | 04-05 | 3 | CAM-04 | T-04-19, T-04-32 | Davr bo'lish semantikasi; `bugun`/`ertaga` bitta so'rovda; qoplanmagan kunlar SQL'da; server chegarasi majburlanadi | integration | `pytest tests/integration/test_schedule_repo.py -q` | yangi | ✅ green |
| 04-05/T3 | 04-05 | 3 | CAM-06, CAM-07 | T-04-36, T-04-37 | `delete` metodi umuman yo'q; retention holat o'tishi bir yo'nalishli; sof modul ↔ enum pariteti | unit | `pytest tests/unit/test_quality_enum_parity.py -q` | yangi | ✅ green |
| 04-06/T1 | 04-06 | 3 | CAM-07 | T-04-40, T-04-41, T-04-42, T-04-44 | `StorageError` endpoint/imzo tashimaydi; `from None`; `create_bucket` yo'q; qo'lda SigV4 yo'q | static + type | `ruff check services/core-api && mypy services/core-api` | yangi | ✅ green |
| 04-06/T2 | 04-06 | 3 | CAM-07 | T-04-43, T-04-45, T-04-47 | Kalit tartibi, ustiga yozish idempotentligi va prefiks izolyatsiyasi HAQIQIY SeaweedFS da; mock yo'q | integration (`sim`) | `npm run sim:up && pytest tests/integration/test_storage_layout.py -m sim -q` | yangi | ✅ green |
| 04-06/T3 | 04-06 | 3 | CAM-07 | T-04-46 | `orphan_keys` faqat kun prefiksini qabul qiladi; erkin prefiks `ValueError` | integration (`sim`) | `npm run sim:up && pytest tests/integration/test_storage_layout.py -m sim -q` | yangi | ✅ green |
| 04-07/T1 | 04-07 | 4 | CAM-05 | T-04-49, T-04-52, T-04-53, T-04-56 | Uch usul bitta protokol ortida; `cache` va `remove_stream` yo'q; natijadan o'lchash; sir oqmaydi | unit (`respx`) | `pytest tests/unit/test_frame_source.py -q` | yangi | ✅ green |
| 04-07/T2 | 04-07 | 4 | CAM-05, CAM-06 | T-04-48, T-04-50, T-04-51, T-04-54, T-04-55 | Tik tenant kontekstini o'zi o'rnatadi; tartib kadr→sifat→S3→baza; auth-locking batchni to'xtatadi; job yiqilmaydi | static + type | `ruff check services/core-api && mypy services/core-api && grep -c -e '^import taskiq' -e '^from taskiq' services/core-api/app/jobs/capture.py` | yangi | ✅ green |
| 04-07/T3 | 04-07 | 4 | CAM-05, CAM-06, CAM-07 | T-04-48, T-04-54, T-04-57 | Planer holatsiz; kontekstsiz tik 0 qator; dublikat yo'q; lease qaytaradi; buzuq kadr `is_billable=false` va FK rad etadi | integration (+`sim`) | `npm run sim:up && pytest tests/integration/test_capture_tick.py tests/integration/test_snapshot_quality.py -q` | yangi | ✅ green |
| 04-08/T1 | 04-08 | 5 | CAM-07 | T-04-64, T-04-66 | Siqish 90 kunni kutmasdan isbotlanadi; o'lchamlar saqlanadi; qator o'chirilmaydi; ikki marta siqish mumkin emas | integration (`sim`) | `npm run sim:up && pytest tests/integration/test_retention.py -m sim -q` | yangi | ✅ green |
| 04-08/T2 | 04-08 | 5 | FOUND-06 | T-04-58, T-04-59, T-04-60 | `sendPhoto` funksiyasi umuman yo'q; token xato matnida yo'q; `send_message` istisno ko'tarmaydi | static + type | `ruff check . && mypy . && pytest tests/unit/test_logging.py -q` | yangi | ✅ green |
| 04-08/T3 | 04-08 | 5 | FOUND-06 | T-04-61, T-04-62, T-04-63, T-04-65 | 22 kameralik yiqilish bitta xabar; debounce va eskalatsiya `alert_events` da; bostirilmaydiganlar metadan; Telegram yiqilsa kadr olish davom etadi | integration (`respx`) | `pytest tests/integration/test_alerting.py -q` | yangi | ✅ green |
| 04-09/T1 | 04-09 | 5 | CAM-04 | T-04-70, T-04-75 | Huquq dekoratorda; `/today` bitta so'rovda; kesishuv 409; `object_key` DTO'da yo'q | integration | `pytest tests/integration/test_capture_schedule.py -q` | yangi | ✅ green |
| 04-09/T2 | 04-09 | 5 | CAM-06, CAM-07 | T-04-67, T-04-68, T-04-69, T-04-73, T-04-74 | Rasm faqat proxy orqali; presigned URL yo'q; `audit_read` yozuvi; `purged` da 410; alert yopish marshruti yo'q | integration (`sim`) | `npm run sim:up && pytest tests/integration/test_snapshot_api.py -q` | yangi | ✅ green |
| 04-09/T3 | 04-09 | 5 | FOUND-06 | T-04-71, T-04-72 | `/internal/self-check` boshqa jarayondan heartbeat holatini beradi; javob yuzasi tor; konteyner healthcheck'i tegilmagan | integration + tenancy | `pytest tests/integration/test_capture_schedule.py -k self_check tests/tenancy/test_route_coverage.py -q` | yangi | ✅ green |
| 04-10/T1 | 04-10 | 6 | CAM-04 | T-04-79, T-04-80, T-04-81 | Kesh kalitlari `marketId` bilan doiralangan; global kalit yo'q; 11 kod uchun sabab↔tuzatish↔`actor` parity | node gate + i18n | `npm --prefix frontend run i18n:check && node --test frontend/scripts/error-codes.test.mjs frontend/scripts/snapshot-copy.test.mjs` | yangi | ✅ green |
| 04-10/T2 | 04-10 | 6 | CAM-04 | T-04-76, T-04-77 | «Ertaga» qatori doim; farq izohi `bg-warning/20`; `camera_manage` yo'q rolda tugmalar render bo'lmaydi; qoplanmagan kun ko'rinadi | component (vitest) | `npm --prefix frontend run test:component -- schedule-card` | yangi | ✅ green |
| 04-10/T3 | 04-10 | 6 | CAM-04 | T-04-78 | 12 lik chegara `aria-disabled` bilan; dublikat rad etiladi; oraliq to'ldirish qisman emas | component (vitest) | `npm --prefix frontend run test:component -- slot-editor` | yangi | ✅ green |
| 04-11/T1 | 04-11 | 7 | CAM-05 | T-04-89 | Oltala hisoblagich nol bilan birga (G-8); `planned === 0` da «0/0» chiqmaydi; foiz yo'q | component (vitest) | `npm --prefix frontend run test:component -- day-summary` | yangi | ✅ green |
| 04-11/T2 | 04-11 | 7 | CAM-05, CAM-06 | T-04-83, T-04-88 | `missed` hujayrasi bo'sh emas (G-7); `CircleSlash` ≠ `XCircle`; `role=grid` yo'q; bitta tab to'xtashi | component (vitest) + node gate | `npm --prefix frontend run test:component -- capture-cell capture-grid && node --test frontend/scripts/snapshot-copy.test.mjs` | yangi | ✅ green |
| 04-11/T3 | 04-11 | 7 | CAM-06, CAM-07, FOUND-06 | T-04-82, T-04-84, T-04-85, T-04-86, T-04-87 | `dark`+`ir_night` ≠ `dark`+`day`; `purged` halol ko'rsatiladi; ogohlantirishda rasm yo'q (G-3); `notified_at` yashirilmaydi | component (vitest) + node gate | `npm --prefix frontend run test:component -- snapshot-dialog alert-list && node --test frontend/scripts/snapshot-copy.test.mjs` | yangi | ✅ green |
| 04-12/T1 | 04-12 | 8 | CAM-04, CAM-05, CAM-06, CAM-07, FOUND-06 | T-04-90, T-04-91, T-04-95 | Beshala mezon bitta buyruqda; meta-test mezon yo'qolishini tutadi; S3 mock'i to'silgan | integration (`sim`) | `npm run sim:up && pytest tests/integration/test_phase4_criteria.py -q` | yangi | ✅ green |
| 04-12/T2 | 04-12 | 8 | CAM-06, CAM-07, FOUND-06 | T-04-92, T-04-94 | Chegara olti o'lchov asosida; `nyquist_compliant` hisoblangan; qo'lda bandlar ega va tetik bilan | script gate | `node scripts/check-validation-signoff.mjs .planning/phases/04-snapshot-pipeline/04-VALIDATION.md` | yangi | ✅ green |
| 04-12/T3 | 04-12 | 8 | CAM-04, CAM-05, CAM-06, CAM-07, FOUND-06 | T-04-93 | Talab holatlari dalil bilan; ro'yxat ↔ Traceability parity; ROADMAP yakunlangan | script gate | `npm run requirements:check` | yangi | ✅ green |
| 04-13/T1 | 04-13 | BW1 | FOUND-06 | T-04-96, T-04-97, T-04-98 | `taskiq scheduler` `CLIENT_STARTUP` ni ateshlaydi, ya'ni `init_sentry()` u yerda ilmoq bilan chaqiriladi; `ObservedScheduler.on_ready` taskiq yutib yuboradigan istisnoni jurnal + Sentry'ga chiqarib QAYTA KO'TARADI; ilmoq `Settings` ga BOG'LANMAYDI | unit | `pytest tests/unit/test_scheduler_observability.py -q` | yangi | ✅ green |
| 04-13/T2 | 04-13 | BW1 | FOUND-06 | T-04-98, T-04-99, T-04-100 | Darvoza jarayonlarni SANAMAYDI — `compose.yaml` da `SENTRY_DSN` oladigan har servisdan HOSILA qiladi; noma'lum `command` shakli va topilmagan kirish nuqtasi YIQILADI; vendor xulqi manbadan qulflangan | unit | `pytest tests/unit/test_sentry_processes.py -q` | yangi | ✅ green |
| 04-13/T3 | 04-13 | BW1 | CAM-04, CAM-05, CAM-06, CAM-07, FOUND-06 | T-04-96, T-04-SC | SC#5 ning Sentry yarmi manba matnidan emas, HAQIQIY subprocess'dan o'lchanadi (nazorat yugurishi DSN'siz `False`); mezonlar soni o'zgarmaydi va meta-test buni talab qiladi | integration (`sim`) | `pytest tests/integration/test_phase4_criteria.py -q` | mavjud (kengaytirildi) | ✅ green |
| 04-14/T1 | 04-14 | BW2 | CAM-07 | T-04-101 | `.env.example` ↔ `s3.json.example` AYNAN teng va bo'sh emas; da'vo TENGLIK (yo'qlik emas); darvoza dasturchining `.env` ini O'QIMAYDI; `compose.yaml` ning `:-` siz qarori tegilmaydi | unit | `pytest tests/unit/test_storage_config.py tests/unit/test_snapshot_settings.py -q` | mavjud (kengaytirildi) | ✅ green |
| 04-14/T2 | 04-14 | BW2 | CAM-07, FOUND-06 | T-04-102, T-04-103 | FOUND-06 dalili sanoq emas, hosila darvozaga tayanadi; ro'yxat ↔ Traceability parity; `human_only_verifications` ↔ `04-HUMAN-UAT.md` bir xil to'plam va tartib; `Automated Command` katagida quvur belgisi yo'q | script gate | `node scripts/check-requirements-sync.mjs && node scripts/check-validation-signoff.mjs .planning/phases/04-snapshot-pipeline/04-VALIDATION.md` | mavjud (kengaytirildi) | ✅ green |
| 04-14/T3 | 04-14 | BW2 | CAM-04, CAM-05, CAM-06, CAM-07, FOUND-06 | T-04-101, T-04-104, T-04-SC | S4 sabotaji juftlik darvozasini AYNAN BITTA testda qizartiradi; to'liq zanjir yashil va to'plam sonlari bazadan past emas; yangi paket yo'q | full gate | `npm run gate` | mavjud | ✅ green — ⚠ **exit 0, LEKIN 1 009 s / 1 174 s — 900 s chegarasidan YUQORI.** Sabab bu faza kodida EMAS (yuqoridagi 3-qadam o'lchovlari: o'zgarmagan kod ustida har bosqich 12–36 % sekinlashdi, `gate:fast` 68 s -> 129 s). Chegara KO'TARILMADI |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

**Wave 0 bandlari → reja xaritasi** (`04-12` ularni `[x]` bilan belgilaydi):

| Band | Reja / task | Band | Reja / task |
|---|---|---|---|
| W0-1 | `04-01` / T2 | W0-7 | `04-01` / T3 |
| W0-2 | `04-01` / T1 | W0-8 | `04-01` / T3 |
| W0-3 | `04-01` / T1 | W0-9 | `04-02` / T1 |
| W0-4 | `04-01` / T1 | W0-10 | `04-02` / T2 |
| W0-5 | `04-01` / T3 | W0-11 | `04-01` / T1 (tasdiqlash) |
| W0-6 | `04-01` / T3 (muddat) + `04-03` / T3 (`0015`) | W0-F1…F7 | `04-02` / T2, T3 |

---

## Wave 0 Requirements

`04-PATTERNS.md` §5 o'n bir bandni sanaydi; `04-UI-SPEC.md` bittasini qo'shadi. **Uchtasi jimgina yiqiladigan turdagi** — testlar yashil bo'lgani holda ishlab chiqarish buziladi:

- [x] **W0-1** *(yopildi: `04-01`/T2 — `BILLABLE_ANCHOR_SUPPORTED = true`, `0014` FK variantida yozildi)* — ⚠ **O'LCHOV:** `GENERATED STORED` ustun **kompozit FK nishoni** bo'la oladimi (`postgres:18.4`). `UNIQUE` tomoni allaqachon isbotlangan (`helpers.py:356-362` + `tests/fixtures/financial.py`), **FK-nishon tomoni emas**. Zond shabloni: `tests/fixtures/financial.py:59-145`. Yiqilsa `0014` trigger variantida yoziladi — **migratsiyadan keyin aniqlash qayta migratsiya demakdir** (D-23 / OQ-4).
- [x] **W0-2** *(yopildi: `04-01`/T1)* — 🔇 `aiobotocore==3.9.0` va `Pillow==12.3.0` ni `[project] dependencies` ga. **3-fazadagi `httpx` epizodining aynan takrori:** `dev` guruhida qolsa hamma test yashil, deploy'da `ModuleNotFoundError`. `tests/unit/test_runtime_deps.py` kengaytiriladi.
- [x] **W0-3** *(yopildi: `04-01`/T1)* — 🔇 `taskiq scheduler` ni `compose.yaml` ga + `npm run up` yorlig'ini yangilash. Planer profil ortida qolsa slotlar **hech qachon** materializatsiya bo'lmasdi **va hech qanday xato chiqmasdi**.
- [x] **W0-4** *(yopildi: `04-01`/T1)* — `storage` (SeaweedFS) xizmati + `ops/seaweedfs/s3.json.example`. `anonymous` yozuvining **yo'qligi** grep-darvoza bilan qulflanadi.
- [x] **W0-5** *(yopildi: `04-01`/T3 (reyestr), `04-03`/T2 (ikkala nom o'chirildi))* — `AUDITED_TABLES` ga `snapshot_schedules`, `snapshot_schedule_slots`. Reyestr **migratsiyadan oldin** yoziladi. ⚠ **TUZATILDI (04-01):** bu bandning avvalgi matni «`test_audited_tables_have_trigger` vaqtincha qizil turadi — bu kutilgan» degan edi va u **NOTO'G'RI**. `test_meta.py:794-832` `not missing` ni emas, **ikki tomonlama tenglikni** tekshiradi (`missing == PENDING_AUDIT_TRIGGERS`), ya'ni ikkala nom `PENDING_AUDIT_TRIGGERS` ga ham qo'shilganda darvoza **YASHIL** qoladi. `test_meta.py:127-131` buni so'zma-so'z talab qiladi: «Buzilgan darvoza — darvoza emas». Amalda: darvoza `04-01` dan `04-03` gacha yashil; `04-03`/T2 `0014` bilan bir oynada ikkala nomni ro'yxatdan o'chiradi.
- [x] **W0-6** *(yopildi: `04-01`/T3 (tartib) + `04-03`/T3 (`0015`))* — 🔇 `market_delete_draft()` kaskadini beshta yangi jadval bilan kengaytirish + `0015` migratsiyasi. **3-fazadagi `0012`→`0013` juftligining aynan takrori:** kengaytirilmasa `0014` dan keyin bozor o'chirish FK buzilishi bilan yiqiladi. ⚠ **TUZATILDI (04-01):** avvalgi matn «beshta jadval» deb yozib, tartibda **to'rttasini** sanagan edi. To'liq tartib — `migrations/entities/__init__.py::SNAPSHOT_DELETE_ORDER`: `snapshots` → `capture_runs` → `snapshot_schedule_slots` → `snapshot_schedules` → **`alert_events`**, va butun blok mavjud NVR blokidan **OLDIN** turishi shart (`capture_runs` `cameras` ga kompozit FK bilan tayanadi, `cameras` esa funksiyaning birinchi `DELETE` i).
- [x] **W0-7** *(yopildi: `04-01`/T3)* — `tests/tenancy/test_meta.py` ga `markets.timezone = 'Asia/Tashkent'` invarianti. `scheduled_at` `markets.timezone` dan, `business_date` esa **literal**dan hisoblanadi — ikkinchi mintaqa qo'shilgan kuni test qizarsin, biznes-kun **jimgina siljimasin**.
- [x] **W0-8** *(yopildi: `04-01`/T3)* — `ix_capture_runs_overdue` uchun `INDEX_EXCEPTIONS` ga **sabab bilan** yozuv. Watchdog barcha bozorlar ustidan yuradi, indeks `market_id` bilan boshlanmaydi.
- [x] **W0-9** *(yopildi: `04-02`/T1)* — `tests/fixtures/frames.py`: sintetik JPEG generatori (`mean`/`stddev`/to'yinganlik bo'yicha). Fixture nomlari **fizik xususiyat** bilan (`frame_mean_8_stddev_2`), detektor chegarasi bilan **emas** — aks holda test o'z chegarasini tasdiqlaydi.
- [x] **W0-10** *(yopildi: `04-02`/T2)* — `nvr-sim` ga `frame_mode` + `/Streaming/channels/{ch}/picture`; `mediamtx.yml` ga sifat yo'llari. **Buzuq kadrni MediaMTX bera olmaydi** — u yaroqli oqim beradi, ya'ni baytlarni sim boshqarishi shart.
- [x] **W0-11** *(yopildi: `04-01`/T1 — tasdiqlandi, yangi marker qo'shilmadi)* — Markerlarni **tasdiqlash** (`tenancy`, `sim`, `hardware`, `slow` yetadi). Yangi marker qo'shilmaydi; `--strict-markers` tufayli e'lon qilinmagan marker yig'ilishda yiqiladi.
- [x] **W0-F7** *(yopildi: `04-02`/T3 — `HEDGED_KEYS` ikki kalitli allowlist)* — ⚠ **Rejalararo darvoza to'qnashuvi.** 3-fazaning G-3 darvozasi hedge so'zi **aynan bitta** `errorCause.*` kalitida bo'lishini talab qiladi. 4-fazaga u `capture_stream_limit` uchun ham qonuniy kerak (bir xil fizik sabab). Tegilmasa darvoza **birinchi kuniyoq qizaradi**. `HEDGED_KEYS` ikki kalitli allowlist'ga kengaytiriladi (`04-UI-SPEC.md` §11.11 Qoida 4).

🔇 = jimgina yiqiladigan (testlar yashil, ishlab chiqarish buzilgan)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Owner | Trigger |
|----------|-------------|------------|-------|---------|
| Sifat chegaralarini real Karmana kadrida sozlash | CAM-06 | Chegaralar hozir **LOW confidence** — real kadr yo'q. Sintetik JPEG generatori mexanizmni isbotlaydi, **qiymatni emas**. D-15 bo'yicha o'lchovlarning o'zi saqlanadi, ya'ni sozlash SQL bilan bo'ladi, qayta kadr olish bilan emas | Nazoratchi + ijrochi | Phase 0 real kadrlari kelganda |
| 90 kunlik saqlash siyosatining amalda ishlashi | CAM-07 | **Vaqtni kutib bo'lmaydi.** Test soatni siljitib mexanizmni isbotlaydi; siyosatning 90 kun davomida haqiqatan ishlashi faqat kalendar bilan tasdiqlanadi | Ops | Go-live + 90 kun |
| Tiklash mashqi (restore drill) | FOUND-07 (8-faza) | Backup'ni tiklash real ombor va real ma'lumot talab qiladi | Ops | Go-live'dan oldin, 8-fazada |
| Telegram alertining haqiqatan yetib borishi | FOUND-06 | Bot tokeni, chat id va tarmoq — CI'da yo'q. Soxta yashil test alert ishlayapti deb yolg'on ishonch berardi | Ops | Bot sozlanganda |
| Tashqi dead-man's switch | FOUND-06 / D-21 | v1 da **kod yozilmaydi** — URL sozlash yo'riqnomasi va ops bandi | Ops | VPS deploy'idan keyin |
| Real NVR'da sessiya chegarasining kadr olishga ta'siri | CAM-05 | Simulyator sessiya chegarasini modellashtirmaydi (3-faza tekshiruvida ochiq yozilgan). `max_concurrent=1` uni **bloklovchi emas**, faqat kechikish masalasi qiladi | Ops | Real NVR ulanganda |
| Planer istisnosi haqiqiy Sentry loyihasida ko'rinadi | FOUND-06 | Darvoza `init()` ning chaqirilishini va yutilgan `on_ready` istisnosining `capture_exception` ga borishini o'lchaydi — hodisaning **yetib borishini emas**. CI'da DSN yo'q; haqiqiy Sentry'ga boradigan test soxta yashil ishonch berardi | Ops | `.env` ga haqiqiy `SENTRY_DSN` yozilgan kun |

> Bu bandlar **fazani bloklamaydi** (2026-08-01 self-service direktivasi). `nyquist_compliant` ularning bajarilganini emas, **shaklini** tekshiradigan skript bilan hisoblanadi — 2-fazadagi `scripts/check-validation-signoff.mjs` naqshi.

---

## Validation Sign-Off

- [x] Har taskda `<automated>` verify yoki Wave 0 bog'liqligi bor — 42/42 qatorda `Automated Command` to'ldirilgan (skript majburlaydi; bo'shliq yopish to'lqini `04-13` va `04-14` ning uch-uchtadan qatorini qo'shdi)
- [x] Namuna uzluksizligi: ketma-ket 3 taskda avtomatik verify yo'qligi holati yo'q
- [x] Wave 0 ning 12 bandi (11 + W0-F7) qoplangan; uchala 🔇 bandi **birinchi migratsiyadan oldin** (`04-01`/`04-02`, `0014` dan oldin)
- [x] W0-1 o'lchandi (`BILLABLE_ANCHOR_SUPPORTED = true`) va `0014` FK variantida yozildi — trigger variantiga ehtiyoj bo'lmadi
- [x] Watch-mode bayrog'i yo'q
- [x] Sifat filtri sintetik kadrlar bilan **darvoza**, konventsiya emas (W0-9 + W0-10) — `test_quality_filter.py` + `test_snapshot_quality.py` + `test_sc3_...`
- [x] To'lqin chegarasi 6 o'lchov asosida qayta belgilandi: **1200 s -> 900 s** (eng yomon 745 s + 20 %); `gate:fast` 180 s da qoldi, joriy o'lchov 68 s
- [x] `nyquist_compliant: true` skript bilan **hisoblangan**: `node scripts/check-validation-signoff.mjs .planning/phases/04-snapshot-pipeline/04-VALIDATION.md` exit 0 (42 qator · 7 inson bandi). Hisob IKKI YO'NALISHDA tekshirildi — bayroq `false` ga o'zgartirilganda skript exit 1 berdi (`04-14`), ya'ni u qiymatni O'QIMAYDI, HISOBLAYDI. ⚠ Argumentsiz `npm run validation:check` **2-faza** fayliga ishora qiladi (`DEFAULT_FILE` qadalgan) va bu faylni QAMRAMAYDI
- [ ] ⛔ **`npm run gate` DAVOMIYLIGI CHEGARADAN OSHDI:** 1 009 s va 1 174 s (chegara 900 s). Ikkalasi ham **exit 0** va to'plam mazmuni bo'yicha regressiya yo'q, lekin davomiylik bo'yicha «regressiya yo'q» degan da'vo bu seansda BERILMAYDI — o'lchov vositasining o'zi ifloslangani o'lchandi (yuqoridagi «3-qadam o'lchovlari»). **Chegara ko'tarilmadi.** Egasi: 5-fazaning validatsiya rejasi; tetigi: tinch xostda uch o'lchov
- [x] Bo'shliq yopish to'lqini yozildi: `04-VERIFICATION.md` ning YAGONA bo'shlig'i (`scheduler` jarayonida Sentry) `04-13` da uch mustaqil qatlamda yopildi; `04-14` uning atrofidagi ochiq bandlarni (`deferred-items.md` #2/#3) yopdi va regressiyasiz ekanini o'lchadi
- [x] Yettinchi inson bandi qo'shildi (`04-HUMAN-UAT.md` #7 — hodisaning haqiqiy Sentry loyihasiga yetib borishi, egasi Ops). ⚠ **90 kunlik saqlash bandi (#2) O'ZGARMADI va YOPILMADI** — vaqtni kutib bo'lmaydi; mexanizm dalili siyosat dalili sifatida ko'rsatilmaydi

**Approval:** ✅ **2026-08-05, `04-14`** — beshala faza mezoni
`tests/integration/test_phase4_criteria.py` bilan BITTA buyruqda
o'lchanadi; `nyquist_compliant` skript bilan hisoblangan; chegara olti
o'lchov asosida qayta belgilangan; `04-VERIFICATION.md` ning bo'shlig'i
yopilgan va uning regressiyasizligi o'lchangan.

*Oldingi imzo: 2026-08-05, `04-12` — o'sha payt 36 qator · 6 inson bandi.*

⚠ **IMZO NIMANI ANGLATMAYDI.** U «hamma narsa tekshirildi» degani emas —
u «tekshirilgan narsa NOMLANGAN, tekshirilmagani ham NOMLANGAN» degani.
Tekshirilmaganlar yuqoridagi `human_only_verifications` blokida va
`04-HUMAN-UAT.md` da, ega hamda tetigi bilan; ular fazani bloklamaydi
(2026-08-01 self-service direktivasi), lekin ularning natijasi hech
qayerda da'vo qilinmagan.
