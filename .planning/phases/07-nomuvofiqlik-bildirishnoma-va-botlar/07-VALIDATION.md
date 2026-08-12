---
phase: 7
slug: nomuvofiqlik-bildirishnoma-va-botlar
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-08-11
updated: 2026-08-12
human_only_verifications:
  - item: Haqiqiy Telegram yetkazishi — jonli token bilan
    why_not_automatable: CI'da bot tokeni YO'Q va bo'lmaydi ham (07-RESEARCH Environment Availability). Mezon moduli mahsulot jo'natuvchisini oxirigacha yuritadi va respx faqat TARMOQ CHEGARASINI tutadi (assert_all_mocked=True — tashqariga chiqish IMKONSIZ, T-07-97). Ya'ni «so'rov to'g'ri shakllandi» o'lchangan, «Telegram uni qabul qildi» esa o'lchanmagan
    owner: Ops
    trigger: Birinchi deploy (pilotdan oldin), test bozori va test chatida
  - item: «Yetkazildi» so'zining sotuvchi uchun MA'NOSI
    why_not_automatable: Telegram Bot API yetkazilganlik kvitansiyasini BERMAYDI — sendMessage faqat Message qaytaradi (Key Finding 4). delivered = «Telegram 200 qaytardi», «o'qildi» EMAS. Semantika kodda uch joyda bir xil va test uni o'lchaydi; o'lchanmagani — nizoda direktor va sotuvchi bu farqni tushunadimi
    owner: Direktor (mahsulot egasi kuzatadi)
    trigger: Pilotning birinchi «xabar kelmadi» nizosi
  - item: Bot matnlarining sotuvchi uchun TUSHUNARLILIGI
    why_not_automatable: Glossariy parity MEXANIK o'lchangan (G7-9 — atama ikkala manbada bir xil, taqiqlangan sinonim nol, uchala locale kalit-parity). O'lchanmagani — o'qish savodxonligi past sotuvchi «qoldiq», «patta» va «kvitansiya» so'zlarini ajrata oladimi. Bu lug'at emas, IDROK savoli
    owner: Mahsulot egasi (bozor adminining yordami bilan)
    trigger: Karmanadagi birinchi dala tashrifi — 5 sotuvchiga ko'rsatiladi
  - item: request_contact tugmasining HAQIQIY klientlardagi xulqi
    why_not_automatable: bot-tests MockedBot bilan ishlaydi, ya'ni Contact obyektini TEST O'ZI yasaydi. D-24 ning uch qo'riqchisi to'liq o'lchangan, lekin ular TAXMINGA tayanadi — haqiqiy klient Contact.user_id ni sender bilan teng qilib yuboradi. Tadqiqot buni MEDIUM-HIGH ishonch bilan yozgan
    owner: Ops
    trigger: Birinchi deploy — iOS, Android va Desktop klientlarida bittadan
  - item: Deploy bandi — cron jadvali IMPORT PAYTIDA olinadi
    why_not_automatable: Bu jarayon holati, kod emas. 07-14 jadvalni worker.py da import paytida o'qiydi, ya'ni qayta ishga tushirilmagan planer yangi vazifalarni UMUMAN ko'rmaydi va HECH QANDAY XATO CHIQMAYDI — jurnal toza, navbat mangu bo'sh
    owner: Ops
    trigger: Har deploy (checklist bandi) — beshala komponent last_seen_at ni yangilashi kuzatiladi
  - item: Bir tokenga bitta poller
    why_not_automatable: Nosozlik IKKI MASHINA ORASIDA tug'iladi va bitta muhitda ifodalanmaydi. Telegram getUpdates ni bitta token uchun bitta klientga beradi — dev nusxa prod botni JIM qiladi va jurnal TOZA qoladi (Pitfall 5)
    owner: Ops (jamoa qoidasi sifatida)
    trigger: Birinchi deploydan oldin — token taqsimoti belgilanganda
  - item: Quiet hours va overdue_days STANDARTLARI
    why_not_automatable: Ikkalasi ham [ASSUMED] qaror (A2 21:00-08:00, A3 overdue_days=3) va buyurtmachi bilan TASDIQLANMAGAN. Mexanika to'liq o'lchangan — oyna bozor kesimida, kvitansiya undan ozod, eslatma unga bo'ysunadi — lekin RAQAMLARNING O'ZI taxmin
    owner: Mahsulot egasi (bozor ma'muriyati bilan)
    trigger: Pilotning birinchi haftasi — javob market_notification_settings ga yoziladi, kod o'zgarmaydi
automated_replacements:
  - was: Kechqurun telefonga qarab dayjest keldimi deb kutish
    now: docker compose --profile test run --rm tests pytest tests/integration/test_phase7_criteria.py -q — digest_evening + digest_morning chaqiriladi, outbox_tick respx bilan yuritiladi va CHIQQAN so'rov o'lchanadi (AYNAN 2, direktorning chatiga, ikki sifatlovchi aralashmaydi)
  - was: Ikki dayjestning raqamini qo'lda solishtirish
    now: test_sc3_... — ikki matnning pul qatori BIR XIL EMAS (D-15/D-16 manba farqi); manba farqining o'zi test_notifications.py::test_evening_reads_projection_and_morning_reads_ledger da
  - was: Botni bloklab ko'rib navbat to'xtaganini kuzatish
    now: test_sc5_... — 403 -> blocked, attempt_count == 1 va IKKINCHI tikda respx chaqiruvlari soni O'SMAYDI. Sabotaj bilan o'lchangan: 403 shoxi RETRY ga o'zgartirilganda test QIZARADI
  - was: Quiet oynada xabar kelmasligini tunda kutib tekshirish
    now: test_sc5_... — 22:30 da kvitansiya BORADI, eslatma esa navbatdan UMUMAN OLINMAYDI (attempt_count == 0 — «ushlab qolindi» ni «manzili topilmadi» dan ajratadi)
  - was: Ikki bozorda bir xil telefonli sotuvchini qo'lda izlab topish
    now: test_sc4_... — market_domain seed'ining O'Z to'qnashuvi (B_VENDOR_PHONE = A_VENDOR_PHONES[0]) ustida: multiple_matches va vendor_telegram_bindings da 0 qator
  - was: Yangi ogohlantirish turiga matn yozishni eslab yurish
    now: node --test frontend/scripts/snapshot-copy.test.mjs — G-36: ALERT_TITLE_KEYS reyestri x 3 locale, oldinga va teskari, o'lcham qulfi bilan (07-17 da qo'shildi, deferred-items 1-bandi)
---

# Phase 7 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> **Manba:** `07-RESEARCH.md` § `Validation Architecture` (1234-satr) — bu fayl undan
> **HOSILA**, qayta yozilmaydi. Ziddiyat bo'lsa — RESEARCH.md ustun.

---

## Bu fazaning validatsiyasi nimasi bilan boshqacha — buni birinchi o'qing

6-fazada butun tizim **ishonch chegarasi ichida** edi: har bir bayt VPS'da qolardi va
har bir foydalanuvchi autentifikatsiya qilingan xodim edi. Test qilinadigan narsa
«hisob to'g'ri yozildimi» edi.

**Bu fazada chegara birinchi marta OCHILADI** (CONTEXT.md D-01): sotuvchi — xodim
emas — tizimga kiradi, va har bir xabar **Telegram serverlariga**, ya'ni
data-rezidentlik chegarasidan **tashqariga** chiqadi. Shuning uchun bu fazaning
validatsiyasi ikki mustaqil savolga javob berishi kerak:

1. **Funksional:** raqam to'g'rimi, xabar bordimi, case yuritildimi.
2. ⛔ **Strukturaviy:** chegaradan **chiqmasligi kerak bo'lgan** narsa chiqmadimi —
   dalil-kadr bayti (D-03) va bot tokeni (D-04).

Ikkinchi savolga **kelishuv bilan** javob berib bo'lmaydi. Uni faqat **to'plam
tengligi** va **AST** darvozalari o'lchaydi — G7-1 … G7-9 (`07-RESEARCH.md:1287-1310`).
Bu darvozalar reja tuzilganda **tasodifiy test emas, majburiy band** bo'lishi kerak.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Backend framework** | pytest 9.1.1 + pytest-asyncio 1.4.0 (`asyncio_mode = "auto"`), testcontainers 4.15.0 + **haqiqiy** `postgres:18.4` — ⛔ SQLite TAQIQ (RLS yo'q) |
| **Backend config** | `pyproject.toml` (ildiz) + `tests/conftest.py` — **mavjud** |
| **`bot-service` framework** | pytest + `aiogram.test_utils.mocked_bot.MockedBot` — ⛔ **Wave 0 da quriladi** (`services/bot-service/pyproject.toml` + `bot-tests` konteyneri). Testlar **haqiqiy Telegram'ga chiqmaydi** |
| **Frontend framework** | vitest (`.test.tsx`) + `node --test` (`frontend/scripts/*.test.mjs`) |
| **Quick run command** | `npm run gate:fast` → `npm run test:fast && npm --prefix frontend test` |
| **Full suite command** | `npm run test` + `npm run test:tenancy` + **`npm run bot:test`** (yangi) |
| **Faza darvozasi** | `npm run gate` + `tests/integration/test_phase7_criteria.py` (beshta mezon, beshta test) |
| **Estimated runtime** | `gate` ≈ **2124 s** (1899 s bugungi + ≈225 s bu faza) |

### ⛔ Byudjet — o'zgartirilmaydi

`gate` **2300 s**, `gate:fast` **200 s** (`06-VALIDATION.md` dan meros). Oxirgi
o'lchov `gate` = **1899 s** → **401 s zaxira**.

| Manba | Taxminiy narx |
|-------|---------------|
| `bot-service` testlari (`bot:test`, `MockedBot`) | ~25 s |
| Backend integratsiya (~60 test) | ~120 s |
| `bot-service` lint/typecheck (ruff + mypy) | ~20 s |
| vitest (+~60 test) + 1 yangi SSG marshruti (`/reconciliation` × 3 locale) | ~60 s |
| **Jami** | **≈ 225 s** — zaxira ichida |

⚠ Agar o'lchov 2300 s dan oshsa — ⛔ **byudjet «shunchaki oshirilmaydi»**: avval
`bot:test` ni `gate:fast` dan **tashqarida** qoldirish tekshiriladi (u mustaqil kod
bazasi), keyin 05-15 W0-13 protokoli yuritiladi (tinch xost, uch o'lchov, eng yomon × 1,20).

---

## Sampling Rate

- **Har task commitida:** `npm run gate:fast` — byudjet **200 s**
- **Har to'lqin (wave) merge'ida:** `npm run test` + `npm run test:tenancy` + `npm run bot:test`
- **`/gsd-verify-work` dan oldin:** to'liq `npm run gate` yashil **va**
  `tests/integration/test_phase7_criteria.py` beshala mezonni **bitta buyruqda** beradi
- **Max feedback latency:** **200 s**

---

## Per-Task Verification Map

> ⚠ **GRANULYARLIK — REJA DARAJASIDA, TASK darajasida EMAS, va bu OCHIQ
> tanlov.** 17 reja ~60 taskdan iborat va har taskning `<automated>` buyrug'i
> o'z rejasida hamda SUMMARY sida allaqachon yozilgan. Bu yerda ularni
> ko'chirish **ikkinchi haqiqat manbai** bo'lardi va u jimgina eskirardi.
> Quyidagi jadval har rejaning **darvoza buyrug'ini** beradi — ya'ni «bu
> reja bugun qanday o'lchanadi?» savoliga javob. Sampling continuity
> shartini bu qanoatlantiradi: uchta ketma-ket reja avtomatik verify'siz
> qolmagan (har qatorda buyruq bor).

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| P-01 | 07-01 | 1 | (infra) | T-07-01 | `bot-service` Sentry ilmog'i bilan tug'iladi; test konteyneri `core-api` to'plamini ifloslantirmaydi | unit | `docker compose --profile test run --rm tests pytest tests/unit/test_sentry_processes.py tests/unit/test_runtime_deps.py -q` | ✅ | ✅ green |
| P-02 | 07-02 | 1 | (domen) | T-07-02 | `0023`: RLS + FORCE + kompozit FK + XOR CHECK; ⛔ `notification_outbox` da kadr ustuni YO'Q (G7-2) | tenancy | `docker compose --profile test run --rm tests pytest tests/tenancy/test_notification_domain_meta.py -q` | ✅ | ✅ green |
| P-03 | 07-03 | 1 | RECON-06 | T-07-15 | Javobda AYNAN bitta son; kassir qiymati kunlik summaga TENG EMAS | integration | `docker compose --profile test run --rm tests pytest tests/integration/test_headline.py -q` | ✅ | ✅ green |
| P-04 | 07-04 | 2 | (fixture) | T-07-07/08 | Strukturaviy meta darvozalar + `TwoMarketSeed` (D-26b ning YAGONA ifodasi) | tenancy | `docker compose --profile test run --rm tests pytest tests/tenancy -q` | ✅ | ✅ green |
| P-05 | 07-05 | 2 | RECON-06 | T-07-15 | Bosh ekran bitta sonni chizadi; rol serverda hal qilinadi | vitest | `npm --prefix frontend test -- headline-card` | ✅ | ✅ green |
| P-06 | 07-06 | 3 | BOT-04 | T-07-49/51 | `AlertSender` yuzasi O'ZGARMADI (G7-1); istisno matni hech qayerga yozilmaydi (G7-4) | unit | `docker compose --profile test run --rm tests pytest tests/unit/test_outbox_surface.py tests/unit/test_outbox_secrets.py -q` | ✅ | ✅ green |
| P-07 | 07-07 | 3 | RECON-02 | T-07-60 | Case holati 4 a'zoli YOPIQ to'plam; hit-rate HOSILA, saqlanmaydi | integration | `docker compose --profile test run --rm tests pytest tests/integration/test_reconciliation_repo.py tests/unit/test_reconciliation_enums.py -q` | ✅ | ✅ green |
| P-08 | 07-08 | 3 | BOT-01, BOT-02 | T-07-38/39/40 | Servis tokeni fail-closed (`503`), tokensiz/noto'g'ri token BAYT-BAYT ayni `401`, sessiya tug'ilmaydi | integration | `docker compose --profile test run --rm tests pytest tests/integration/test_bot_internal_api.py -q` | ✅ | ✅ green |
| P-09 | 07-09 | 4 | BOT-04 | T-07-52/54 | `403` -> `blocked` qayta urinishsiz; token jurnalga sizmaydi (G7-5); yurak urishi detalida faqat SANOQ | integration | `docker compose --profile test run --rm tests pytest tests/integration/test_outbox.py tests/integration/test_outbox_repo.py -q` | ✅ | ✅ green |
| P-10 | 07-10 | 4 | RECON-01, RECON-02 | T-07-61 | Hisobotda dalil IDENTIFIKATORI, kadr BAYTI yo'q; `PERSONAL_ROUTES` o'smadi (G7-6) | integration | `docker compose --profile test run --rm tests pytest tests/integration/test_reconciliation_api.py tests/tenancy/test_personal_data_coverage.py -q` | ✅ | ✅ green |
| P-11 | 07-11 | 4 | BOT-01, BOT-02 | T-07-24 | `contact` ning uch rad javobi (D-24); uchala locale kalit-parity (G7-9) | unit (bot) | `docker compose --profile test run --rm bot-tests pytest -q` | ✅ | ✅ green |
| P-12 | 07-12 | 4 | CASH-05 | T-07-23 | Kvitansiya niyati to'lov TRANZAKSIYASIDA; takror `POST` ikkinchi qator bermaydi | integration | `docker compose --profile test run --rm tests pytest tests/integration/test_receipt_outbox.py -q` | ✅ | ✅ green |
| P-13 | 07-13 | 4 | RECON-03, BOT-03 | T-07-53 | Kechki PROYEKSIYADAN, ertalabki YOZILGAN hisobdan; sotuvchi ismi xabarga tushmaydi | integration | `docker compose --profile test run --rm tests pytest tests/integration/test_notifications.py tests/unit/test_digest_qualifiers.py -q` | ✅ | ✅ green |
| P-14 | 07-14 | 5 | RECON-03 | T-07-55 | Beshala vazifa reyestrda VA `alert_sweep::watched` da (D-17); G-35 matn darvozasi | unit | `docker compose --profile test run --rm tests pytest tests/unit/test_heartbeat_registry.py tests/unit/test_digest_qualifiers.py -q` | ✅ | ✅ green |
| P-15 | 07-15 | 6 | RECON-01 | T-07-81 | `components/reconciliation/**` da `<img>` YO'Q — dalil faqat HAVOLA (G7-3) | vitest + node | `npm --prefix frontend test` | ✅ | ✅ green |
| P-16 | 07-16 | 7 | BOT-04 | T-07-62 | Yetkazilganlik holati direktor yuzasida; besh hisoblagich NOL bo'lsa ham qaytadi | integration + vitest | `docker compose --profile test run --rm tests pytest tests/integration/test_delivery_surface.py -q` va `npm --prefix frontend test -- delivery-list` | ✅ | ✅ green |
| P-17a | 07-17 | 8 | (beshala mezon) | T-07-96/97/98 | Mezon SOXTALASHTIRILMAYDI (AST, to'rt yo'l); `respx` `assert_all_mocked`; SC#4 chegarasi OCHIQ | integration | `docker compose --profile test run --rm tests pytest tests/integration/test_phase7_criteria.py -q` | ✅ | ✅ green |
| P-17b | 07-17 | 8 | (deferred #1) | — | `ALERT_TITLE_KEYS` reyestri x 3 locale MEXANIK bog'landi (G-36), o'lcham qulfi bilan | node --test | `node --test frontend/scripts/snapshot-copy.test.mjs` | ✅ | ✅ green |
| P-17c | 07-17 | 8 | (byudjet) | T-07-99 | Byudjet raqami `package.json` va shu faylda BIR XIL; o'lchov tinch xostda, uch marta | ops | `npm run gate` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

⚠ **`File Exists` ustuni «fayl bor» degani, «to'liq» degani EMAS.** Har
qator o'z rejasining SUMMARY sida batafsil ochilgan; bu jadval ularning
**indeksi**, o'rnini bosuvchi emas.

---

## Phase Requirements → Test Map (RESEARCH.md:1268 dan hosila)

| Req | Xulq | Turi | Avtomatik buyruq | Fayl bormi? |
|-----|------|------|------------------|-------------|
| RECON-01 | Hisobotda ikkala sinf va dalil **havolasi** ko'rinadi; ⛔ javobda kadr **bayti** yo'q | integration | `pytest tests/integration/test_phase7_criteria.py::test_sc1_report_shows_both_classes_with_evidence_links -x` | ❌ W0 |
| RECON-02 | Case holati 4 a'zoli yopiq to'plam; o'zgarish **audit qatori**; hit-rate hosila | integration | `pytest tests/integration/test_reconciliation_api.py -x` | ❌ W0 |
| RECON-02 | ⛔ `other` a'zosi **yo'q** — to'plam tengligi | unit | `pytest tests/unit/test_reconciliation_enums.py -x` | ❌ W0 |
| RECON-03 | 20:45 xabari `pending_projection()` dan; 08:00 xabari `daily_charges` dan; **ikki son har xil** | integration | `pytest tests/integration/test_notifications.py::test_evening_reads_projection_and_morning_reads_ledger -x` | ❌ W0 |
| RECON-03 | Uchala yangi komponent `EXPECTED_COMPONENTS` da **va** `alert_sweep::watched` da (D-17) | unit | `pytest tests/unit/test_heartbeat_registry.py -x` | ❌ W0 |
| RECON-06 | Javobda **aynan bitta son**; ⛔ kassir qiymati kunlik summaga **teng emas** | integration | `pytest tests/integration/test_headline.py -x` | ❌ W0 |
| CASH-05 | To'lov → outbox qatori **o'sha tranzaksiyada**; takror `POST` **ikkinchi qator bermaydi** | integration | `pytest tests/integration/test_outbox.py::test_receipt_is_enqueued_once_per_payment -x` | ❌ W0 |
| CASH-05 | Quiet hours kvitansiyani **ushlab qolmaydi** (D-18) | unit | `pytest tests/unit/test_outbox_policy.py -x` | ❌ W0 |
| BOT-01 | `user_id is None` / `user_id != from_user.id` / guruh chati — **uch** rad | unit (bot) | `docker compose --profile test run --rm bot-tests pytest tests/unit/test_binding.py -x` | ❌ W0 |
| BOT-01 | ⛔ Ikki bozorda bir xil telefon → bog'lanish **yo'q** + alert (D-26b) | integration | `pytest tests/integration/test_bot_internal_api.py::test_two_markets_same_phone_refuses_binding -x` | ❌ W0 |
| BOT-02 | Qoldiq `vendor_outstanding()` bilan **teng**; tarix `vendor_charge_allocation()` dan | integration | `pytest tests/integration/test_bot_internal_api.py -x` | ❌ W0 |
| BOT-03 | `overdue_days` bozor kesimida; quiet hours ga **bo'ysunadi** | integration | `pytest tests/integration/test_notifications.py::test_overdue_reminder_respects_market_settings -x` | ❌ W0 |
| BOT-04 | `403` → `blocked`, qayta urinish **yo'q**; `429` → `retry_after`; 5 urinishdan keyin `failed` | integration | `pytest tests/integration/test_outbox.py -x` | ❌ W0 |
| BOT-04 | ⛔ Jo'natuvchi **bloklamaydi**: Telegram yiqilganda to'lov yozuvi o'tadi (D-23) | integration | `pytest tests/integration/test_outbox.py::test_telegram_failure_does_not_block_payment -x` | ❌ W0 |

---

## ⛔ Strukturaviy darvozalar — G7-1 … G7-9 (kelishuv EMAS)

To'liq shakli: `07-RESEARCH.md:1287-1310`. Reja **har birini** nomlangan task
sifatida ko'tarishi shart — ular «yaxshi bo'lardi» emas, **fazaning shartlari**.

| Darvoza | Qaysi qarorni himoya qiladi | Nima o'lchanadi |
|---|---|---|
| **G7-1** | D-03 (kadr Telegram'ga chiqmaydi) | `AlertSender` ommaviy metodlari to'plami **o'zgarmadi**; `sendPhoto\|sendDocument\|sendMediaGroup\|photo=\|InputFile` → **0** |
| **G7-2** | D-03 (sxema darajasida) | `notification_outbox` da `snapshot_id`/`image`/`object_key`/`url` ustuni **YO'Q** — `information_schema` to'plam tengligi |
| **G7-3** | D-03 (frontend jufti, 04-UI-SPEC G-3) | `components/reconciliation/**` alert bloklarida `<img>` **yo'q**; dalil faqat **havola** |
| **G7-4** | D-04 (token istisno matnida) | `str(exc)`/`{exc}`/`repr(exc)` → **0** (AST bilan); `last_error` ga faqat `type(exc).__name__` |
| **G7-5** | D-04 (xulqiy tasdiq) | Soxta token bilan jo'natuvchi yiqilganda `caplog` matnida token satri **yo'q** |
| **G7-6** | D-05 | `PERSONAL_ROUTES` **o'smadi** — yangi marshrutlar `vendor_name`/`phone`/`full_name` qaytarmaydi |
| **G7-7** | T-06-22 | `DEFINER_SURFACES == ()` — yangi `SECURITY DEFINER` **0** |
| **G7-8** | D-06 / D-07 | `balance`/`balance_soum` ustuni **0**; `float(`/`Decimal`/`round(` **0** |
| **G7-9** | D-30 / D-31 | Glossariy atamalari **ikkala** manbada bir xil + **taqiqlangan sinonimlar 0** + uchala locale kalit-parity |

⚠ **G7-9 ning uchinchi bandi majburiy.** Usiz darvoza «ikkalasida ham bor» ni
tasdiqlaydi, lekin **ikkinchi so'z paydo bo'lishini** to'smaydi.

⚠ **D-26(b) testi `TwoMarketSeed` siz hech nimani o'lchamaydi** —
`uq_vendors_market_id_phone_e164` sababli «ko'p moslik» faqat **bozorlar aro** yuz
beradi (`07-RESEARCH.md` Key Finding 5).

---

## Wave 0 Requirements

- [ ] `services/bot-service/` butun skeleti — `pyproject.toml`, `uv.lock`, `Dockerfile`,
      `app/main.py` (⛔ `init_sentry()` bilan), `app/observability.py`
- [ ] `compose.yaml` ga `bot-service` **va** `bot-tests` yozuvlari
- [ ] `package.json` ga `bot:test` / `bot:lint`; `gate` zanjiriga ulash
- [ ] ⛔ `tests/unit/test_sentry_processes.py::FOREIGN_HOOK_MARKERS` ni aiogram ilmog'i
      bilan kengaytirish — **birinchi** migratsiyadan oldin (bu test yangi servis
      qo'shilganda **ataylab** yiqiladi)
- [ ] `tests/tenancy/test_notification_domain_meta.py` — RLS/FORCE/kompozit FK/⛔ nomlar (G7-2, G7-8)
- [ ] `tests/unit/test_outbox_surface.py` + `tests/unit/test_outbox_secrets.py` (G7-1, G7-4)
- [ ] `ops/i18n/glossary.json` + `frontend/scripts/glossary.test.mjs` (G7-9)
- [ ] `tests/fixtures/notification_domain.py` — outbox/case/binding seed'lari
      (⛔ `TwoMarketSeed` ni **o'z ichiga oladi** — D-26(b) uchun)
- [ ] `services/bot-service/tests/unit/test_sentry_entrypoints.py` (`cv-service` juftining nusxasi)
- [ ] `tests/integration/test_phase7_criteria.py` skeleti — **beshta** mezon, **beshta**
      test, meta-test bilan

---

## Manual-Only Verifications

> 6-fazadagi kabi, bu bo'limga qo'shilgan **har bir qator sabab bilan asoslanishi** va
> egasi hamda tetigi bo'lishi shart. «Hozir o'lchab bo'lmaydi» — dizayn xatosining
> belgisi, tabiiy chegara emas.

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| ⚠ **«Yetkazildi» so'zining sotuvchi uchun MA'NOSI** | BOT-04 | ⛔ Telegram Bot API yetkazilganlik kvitansiyasi **BERMAYDI** — `sendMessage` faqat `Message` qaytaradi (`07-RESEARCH.md` Key Finding 4). `delivered` = «Telegram 200 qaytardi», **«o'qildi» EMAS**. Kod buni to'g'ri yozadi va test o'lchaydi; o'lchanmagani — **nizoda direktor va sotuvchi bu farqni tushunadimi** | Pilotning birinchi «xabar kelmadi» nizosida: direktor yuzadagi holat matnini o'qib, sotuvchiga tushuntira oladimi |
| **Bot matnlarining sotuvchi uchun TUSHUNARLILIGI** | BOT-01, BOT-02 | Glossariy parity **mexanik** o'lchangan (G7-9): atama ikkala manbada bir xil, taqiqlangan sinonim nol. O'lchanmagani — **o'qish savodxonligi past sotuvchi** «qoldiq» va «patta» so'zlarini ajrata oladimi | Karmanada 5 sotuvchiga bot ekrani ko'rsatiladi; qaysi so'z tushunilmagani yoziladi |

*Boshqa barcha faza xulqlari avtomatik verifikatsiyaga ega.*

---

## Validation Sign-Off

- [x] Har task `<automated>` verify yoki Wave 0 bog'liqligiga ega
- [x] Sampling continuity: uchta ketma-ket task avtomatik verify'siz qolmagan
- [x] Wave 0 barcha MISSING havolalarni qoplaydi
- [x] ⛔ G7-1 … G7-9 **to'qqizala** darvoza rejada nomlangan task sifatida bor
- [x] Watch-mode bayrog'i yo'q
- [x] Feedback latency < **200 s**; `gate` byudjeti ⛔ **o'lchangan** (taxmin emas) — raqam va uch o'lchov yuqoridagi «Byudjet» bo'limida
- [x] `nyquist_compliant: true` frontmatterda o'rnatilgan

⛔ **`nyquist_compliant: true` NIMAGA TAYANADI — VA U «hammasi
avtomatlashtirilgan» DEGANI EMAS.** Frontmatterda **yettita** inson
bandi ochiq sanalgan va har birida **ega** hamda **tetik** bor; ular
`07-HUMAN-UAT.md` bilan bir xil to'plam. Bayroq shuni bildiradi:
fazaning har **avtomatlashtiriladigan** xulqi darvoza bilan qoplangan va
qolgan bandlar **tashqi xizmat**, **haqiqiy klient** yoki **inson
idroki** — ya'ni ular dizayn xatosi emas, tabiiy chegara.

⚠ **FAZANI YOPISH QARORI BU FAYLNIKI EMAS.** Bu yerdagi belgilar
**o'lchov** natijasi; yopish qarori qayta tekshiruvniki
(`/gsd-verify-work`) va `ROADMAP.md` dagi faza belgisi shu sababdan
`- [ ]` **holicha qoldirildi** (4- va 5-fazalarda ham aynan shunday).

**Approval:** o'lchandi (07-17, 2026-08-12) — yopish qarori qayta tekshiruvda
