---
phase: 7
slug: nomuvofiqlik-bildirishnoma-va-botlar
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-11
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

> Bu jadvalni **gsd-planner** to'ldiradi. Har task `<automated>` verify buyrug'iga
> yoki Wave 0 bandiga ega bo'lishi shart. Uchta ketma-ket task avtomatik verify'siz
> qolmaydi (sampling continuity).

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| _(planner to'ldiradi)_ | | | | | | | | | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

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

- [ ] Har task `<automated>` verify yoki Wave 0 bog'liqligiga ega
- [ ] Sampling continuity: uchta ketma-ket task avtomatik verify'siz qolmagan
- [ ] Wave 0 barcha MISSING havolalarni qoplaydi
- [ ] ⛔ G7-1 … G7-9 **to'qqizala** darvoza rejada nomlangan task sifatida bor
- [ ] Watch-mode bayrog'i yo'q
- [ ] Feedback latency < **200 s**; `gate` < **2300 s** (o'lchangan, taxmin emas)
- [ ] `nyquist_compliant: true` frontmatterda o'rnatilgan

**Approval:** pending
