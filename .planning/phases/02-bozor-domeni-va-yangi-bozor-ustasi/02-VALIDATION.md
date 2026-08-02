---
phase: 2
slug: bozor-domeni-va-yangi-bozor-ustasi
status: automated-green-human-items-scheduled
nyquist_compliant: true
wave_0_complete: true
created: 2026-07-30
measured: 2026-08-03
human_only_verifications:
  - item: "Ma'muriyatning qog'oz reestri bilan raqamlarni solishtirish (README §7 ning yettala raqami)"
    why_not_automatable: "Taqqoslanadigan ikkinchi tomon — ma'muriyatning qog'oz daftari — tizimdan TASHQARIDA. Mashina uni o'qiy olmaydi; tizimning O'ZI bilan mosligi esa allaqachon avtomatlashtirilgan."
    owner: "Bozor ma'muriyati (hisobchi) + platforma admini"
    trigger: "Ma'muriyat fayllari kelgan va `ops/data/karmana/README.md` §2 tartibi bajarilgan kun"
  - item: "Ustaning kod yozmasdan yakunlanishi — foydalanuvchanlik kuzatuvi"
    why_not_automatable: "«Kod yozilmaydi» — FOYDALANUVCHANLIK da'vosi, manba tekshiruvi emas. Odam qayerda to'xtashini faqat kuzatish ko'rsatadi; mashinaviy yarmi (zanjir uzilmaydimi) `test_phase2_criteria.py::test_sc1_...` bilan qamralgan."
    owner: "Platforma admini (kuzatuvchi) + mahsulot egasi (yozib boruvchi)"
    trigger: "Pilot tayyorgarligi haftasi — 02-18 uchala to'siqni yopgani uchun kuzatuv endi BAJARILADIGAN holatda"
  - item: "Sxematik xaritaning maqsadli qurilmada O'QILISHI (shrift, kontrast, skroll masofasi)"
    why_not_automatable: "Perseptual baho. jsdom shrift o'lchamini, kontrastni va skroll masofasini o'lchay olmaydi; «birorta rasta tushib qolmaydi» degan MEXANIK yarmi esa avtomatlashtirilgan."
    owner: "Bozor admini (o'z ish kompyuteri va telefonida) + frontend egasi"
    trigger: "Pilot tayyorgarligi haftasi, real zona/rasta soni yuklangandan keyin"
  - item: "Rekvizit formatlarini (STIR, bank hisob raqami, MFO) buyurtmachi bilan tasdiqlash"
    why_not_automatable: "Rasmiy hujjatning talabi tashqi manba (A1/A2 taxminlari, LOW confidence). Uni faqat buyurtmachi tasdiqlaydi."
    owner: "Mahsulot egasi + buyurtmachi (bozor direktori/hisobchisi)"
    trigger: "Formani qotirishdan OLDIN; bugungi holat xavfsiz tomonga qiya (server rekvizitlarni ATAYIN formatlamaydi), ya'ni kechiktirish zarar keltirmaydi"
automated_replacements:
  - was: "Real ma'lumot ~300–1000 miqyosda yuklanadi va raqamlar mos keladi (MEXANIK yarmi)"
    now: "docker compose --profile test run --rm tests pytest tests/integration/test_karmana_scale_import.py -q"
  - was: "Generator quvurning O'ZIDAN mustaqilligi (o'z-o'ziga qaytish xavfi)"
    now: "docker compose --profile test run --rm tests pytest tests/unit/test_karmana_seed.py -q"
  - was: "Xarita real miqyosda birorta rastani tushirib qoldirmasligi (MEXANIK yarmi)"
    now: "npm --prefix frontend test"
  - was: "Ustaga yetib borish yo'lining mavjudligi (foydalanuvchanlik kuzatuvining to'sig'i)"
    now: "npm --prefix frontend run test:unit"
  - was: "`nyquist_compliant` bayrog'ining qo'lda, kelishuv bilan qo'yilishi"
    now: "node scripts/check-validation-signoff.mjs"
open_items:
  - "KECHIKISH BYUDJETI (egasi: 3-FAZA). To'lqin darajasi hamon byudjetdan tashqarida va u 02-23 da YANA o'sdi: 02-17 da 225 s (890 test) -> 02-22 da o'lchangan `npm run gate` 585 s -> 02-24 da ~571 s -> 02-23 da **464 s** (`npm run gate`, 992 backend + 322 tenancy testi). ⚠ Darvozaning DEVOR-SOATI 02-22 dagidan KAM chiqdi (585 s -> 464 s) va bu tezlashtirish EMAS: raqam Docker keshi va `next build` ning holatiga qattiq bog'liq, ya'ni u trend o'lchovi sifatida ishonchsiz. Ishonchli o'lchov — ajratilgan fayl narxi (pastga qarang). Maqsad ≤180 s (to'lqin). Sabab strukturaviy: har integratsiya testi `two_markets` + `market_domain` seed'ini QAYTA yozadi (function-scope fixture). Tuzatish fixture doirasiga tegadi va u bu fazaning eng qimmat kafolati — shuning uchun 3-fazaga o'tkaziladi (`pytest-xdist` yoki tranzaksiyaga o'ralgan seed)."
  - "MIQYOS KONSTANTASINING IKKI JOYDA YASHASHI (egasi: 3-FAZA, past ustuvorlik). `KARMANA_ZONE_COUNT`/`KARMANA_STALL_COUNT` Python fixture'ida, `stall-map.test.tsx` da esa QO'LDA takrorlangan — Python konstantasini vitest'ga import qilib bo'lmaydi. Ajralib ketsa frontend testi eski miqyosni o'lchab yashil qolardi."
  - "REAL KARMANA MA'LUMOTI hali yuklanmagan va bu FAZA DARVOZASI EMAS (ROADMAP self-service qoidasi, 2026-08-01). U `human_only_verifications` ning 1-bandi sifatida, egasi va ishga tushish sharti bilan yuritiladi."
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Derived from `02-RESEARCH.md` § Validation Architecture (lines 1243–1313).
> The **Per-Task Verification Map** below is a stub — the planner fills it from `02-01-PLAN.md` … `02-NN-PLAN.md`.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 + pytest-asyncio 1.4.0 (`asyncio_mode = "auto"`) + testcontainers 4.15.0 — **all present from Phase 1, no framework install needed** |
| **Config file** | `pyproject.toml` (repo root, `[tool.pytest.ini_options]`, `pythonpath = [".", "tests", "services/core-api"]`, marker: `tenancy`) |
| **Database** | **`postgres:18.4-trixie`, connected as `sbozor_app`** — `tests/conftest.py` |
| **Frontend** | vitest 4.1.10 + jsdom 30.0.1 + Testing Library; `node --test` for scripts |
| **Quick run command** | `docker compose --profile test run --rm tests pytest tests/unit -x -q` |
| **Tenancy gate command** | `npm run test:tenancy` |
| **Full suite command** | `npm run test` → `docker compose --profile test run --rm tests pytest -q` |
| **Frontend suite command** | `npm --prefix frontend test` |
| **Phase gate command** | `npm run gate` (lint + mypy + backend + tenancy + i18n + typecheck + eslint + build) |
| **Estimated runtime** | **ESKI RAQAMLAR O'CHIRILMAYDI — o'sish byudjet muhokamasi uchun kerak.**<br>**2026-08-01 (02-17):** task darajasi (`pytest tests/unit -x -q`) **11 s** ✅ (maqsad ≤30 s) · to'lqin darajasi (`npm run test:tenancy`, 309 test) **99 s** · to'liq backend (`npm run test`, **890** test) **225 s** ❌ (maqsad ≤180 s) · frontend (54 node + 40 vitest) **12 s** · to'liq darvoza (`npm run gate`) **403 s**.<br>**2026-08-02 (02-22):** `npm run gate` **585 s**; **(02-24):** `npm run gate` **~571 s**.<br>**2026-08-03 (02-23):** to'liq darvoza (`npm run gate`, **992** backend + **322** tenancy testi) **464 s** (⚠ devor-soati Docker keshiga bog'liq — trend o'lchovi sifatida ishonchsiz) · frontend to'plami (57 node + 74 vitest) **14 s** · yangi miqyos fayli YOLG'IZ (`test_karmana_scale_import.py`) **14 s** (konteyner ko'tarilishi bilan; testning O'ZI ~5 s) · generator birlik fayli (`test_karmana_seed.py`) to'liq `tests/unit` ichida, task byudjeti ichida.<br>Har bir raqam konteyner ko'tarilishini O'Z ICHIGA OLADI (xostda `time` bilan). 1-faza: quick 8 s / full 47 s / tenancy 20 s |

**Forbidden:** SQLite (RLS does not exist there). The test engine MUST connect as `sbozor_app`, never as a superuser — `FORCE ROW LEVEL SECURITY` does not constrain superusers, so a superuser fixture makes every RLS test falsely green.

**New infrastructure prerequisite (Pitfall 1):** `btree_gist` must exist before the first Phase 2 migration runs. `sbozor_owner` is `NOCREATEDB` and returns `permission denied to create extension` — the extension must be created by a superuser init step (`ops/db/init/00-extensions.sql`) and read by `tests/conftest.py`.

---

## Sampling Rate

- **After every task commit:** `docker compose --profile test run --rm tests pytest tests/unit -x -q` + the integration file for the changed module
- **After every plan wave:** `npm run test` + `npm run test:tenancy` + `npm --prefix frontend test`
- **Before `/gsd-verify-work`:** `npm run gate` fully green
- **Max feedback latency:** target ≤30 s at task level, ≤180 s at wave level (Phase 1 budgets; confirm by measurement)
- **O'LCHOV NATIJASI (2026-08-01):** task darajasi **11 s** ✅; to'lqin darajasi **225 s** ❌ — byudjet **45 s ga oshib ketdi**. Sabab strukturaviy va u yashirilmasligi kerak: har integratsiya testi `two_markets` + `market_domain` seed'ini QAYTA yozadi (function-scope fixture), ya'ni 890 testning taxminan yarmi har safar ikki bozorlik domen qatlamini quradi. Bu 2-fazada TUZATILMADI — tuzatish fixture doirasini o'zgartirishni talab qiladi va u testlar orasidagi izolyatsiyaga (bu fazaning eng qimmat kafolati) tegadi. 3-fazaga o'tkaziladi va u yerda `pytest-xdist` yoki tranzaksiyaga o'ralgan seed sifatida ko'rib chiqiladi.
- **QAYTA O'LCHOV (2026-08-03, 02-23):** to'liq darvoza **599 s** (1000 backend testi). 02-23 ning o'z hissasi o'lchandi va u **yashirilmaydi**: miqyos fayli yolg'iz `14 s` (konteyner ko'tarilishi bilan), ya'ni sof qo'shimcha **~5 s**. Bu byudjetni buzgan sabab EMAS — buzilish 02-17 dayoq strukturaviy edi va egasi 3-faza. Yangi fayl uni **atigi ~1% ga** kattalashtirdi, buning evaziga esa `02-VERIFICATION.md` ning 2-bo'shlig'i yopildi.

---

## Per-Task Verification Map

> **Filled by the planner (2026-07-31).** 17 plans / 51 tasks. Every task carries an `<automated>` verify command; three tasks additionally carry `<human-check>` steps (real Karmana data, usability walkthrough, perceptual map check) which are recorded under **Manual-Only Verifications** below.
>
> Wave 0 work is **not** a separate wave here — it is plans `02-01` (backend gates) and `02-02` (frontend design-system gates), both in wave 1, plus the mandatory ordering chain in `02-03`. Every later plan depends on them transitively.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 1 | MARKET-01,MARKET-02,MARKET-03,MARKET-04 | T-02-01 | Sxema reyestrlari va RBAC matritsasini 2-faza uchun to'g'rilash | unit | `npm run test:unit` | ✅ | ✅ green |
| 02-01-02 | 01 | 1 | MARKET-01,MARKET-02,MARKET-03,MARKET-04 | T-02-02 | `btree_gist` superuser init qadami, conftest ulanishi va `require_extension()` yordamchisi | tenancy | `npm run test:tenancy` | ✅ | ✅ green |
| 02-01-03 | 01 | 1 | MARKET-01,MARKET-02,MARKET-03,MARKET-04 | T-02-03 | WR-02/WR-03 — `select-market` ni parol darvozasi ostiga olish va `is_platform_admin` ni DB'dan qayta o'qish | integration | `docker compose --profile test run --rm tests pytest tests/integration/tes…` | ✅ | ✅ green |
| 02-02-01 | 02 | 1 | MARKET-01,MARKET-02,MARKET-06 | T-02-09 | Dizayn tokenlarini WCAG AA ga keltirish va boshqaruv elementlarini yangi tokenlarga ko'chirish | component | `npm --prefix frontend run typecheck && npm --prefix frontend run lint && …` | ✅ | ✅ green |
| 02-02-02 | 02 | 1 | MARKET-01,MARKET-02,MARKET-06 | T-02-10 | Yetti `ui/` primitivini ajratish + tipografiya va bo'shliq panjarasini mexanik tozalash | component | `npm --prefix frontend run test:component && npm --prefix frontend run typ…` | ✅ | ✅ green |
| 02-02-03 | 02 | 1 | MARKET-01,MARKET-02,MARKET-06 | T-02-11 | Transliterator defektlarini yopish va frontend testlarini faza darvozasiga ulash | component | `npm --prefix frontend test && npm --prefix frontend run i18n:check` | ✅ | ✅ green |
| 02-03-01 | 03 | 2 | MARKET-01 | T-02-15 | Zanjir 1–2-bandlari — `auth_memberships()` qaytish tipi va `Membership.is_active` | gate | `docker compose --profile migrate run --rm migrate alembic upgrade head &&…` | ✅ | ✅ green |
| 02-03-02 | 03 | 2 | MARKET-01 | T-02-16 | Zanjir 3–4-bandlari — `MarketRef.is_active` va serverdagi filtrni olib tashlash | integration | `docker compose --profile test run --rm tests pytest tests/integration/tes…` | ✅ | ✅ green |
| 02-03-03 | 03 | 2 | MARKET-01 | T-02-17 | Zanjir 5–6-bandlari — zod kontrakti, `Qoralama` belgisi va uzilgan ustaga qaytish | component | `npm --prefix frontend run test:component && npm --prefix frontend run i18…` | ✅ | ✅ green |
| 02-04-01 | 04 | 3 | MARKET-02,MARKET-03,MARKET-04,MARKET-05 | T-02-20 | `StallStatus` enum'i va `[)` davr yordamchisi | unit | `npm run test:unit` | ✅ | ✅ green |
| 02-04-02 | 04 | 3 | MARKET-02,MARKET-03,MARKET-04,MARKET-05 | T-02-21 | O'nta domen modeli (`models/market.py`) va barrel importi | gate | `docker compose --profile test run --rm tests sh -c "python -c 'from sbozo…` | ✅ | ✅ green |
| 02-04-03 | 04 | 3 | MARKET-02,MARKET-03,MARKET-04,MARKET-05 | T-02-22 | DB funksiyalari, trigger funksiyalari va entity reyestrlari | gate | `docker compose --profile test run --rm tests sh -c "python -c 'from migra…` | ✅ | ✅ green |
| 02-05-01 | 05 | 4 | MARKET-01,MARKET-02,MARKET-03 | T-02-29 | `0007_market_domain.py` — yadro jadvallar, RLS, audit va rasta-kod kafolati | gate | `docker compose --profile migrate run --rm migrate alembic upgrade head &&…` | ✅ | ✅ green |
| 02-05-02 | 05 | 4 | MARKET-01,MARKET-02,MARKET-03 | T-02-30 | `0008_temporal.py` — tarif va toifa tarixi + o'zgarmaslik triggerlari | gate | `docker compose --profile migrate run --rm migrate alembic upgrade head &&…` | ✅ | ✅ green |
| 02-05-03 | 05 | 4 | MARKET-01,MARKET-02,MARKET-03 | T-02-31 | Alembic ko'rmaydigan narsalar uchun meta-test darvozasi + bo'sh autogenerate diff | tenancy | `docker compose --profile test run --rm tests pytest tests/tenancy/test_ma…` | ✅ | ✅ green |
| 02-06-01 | 06 | 5 | MARKET-04,MARKET-05 | T-02-37 | `0009_vendors.py` — sotuvchilar va qoplanmaydigan biriktirish davrlari | gate | `docker compose --profile migrate run --rm migrate alembic upgrade head &&…` | ✅ | ✅ green |
| 02-06-02 | 06 | 5 | MARKET-04,MARKET-05 | T-02-38 | `0010_calendar.py` — ish kunlari istisnolari, `market_is_open()` va `market_delete_draft()` | gate | `docker compose --profile migrate run --rm migrate alembic upgrade head &&…` | ✅ | ✅ green |
| 02-06-03 | 06 | 5 | MARKET-04,MARKET-05 | T-02-39 | Ikki bozorli domen seed'i va EXCLUDE/`market_is_open` darvozalari | tenancy | `docker compose --profile test run --rm tests pytest tests/tenancy -x -q` | ✅ | ✅ green |
| 02-07-01 | 07 | 6 | MARKET-02,MARKET-03,MARKET-04,MARKET-05 | T-02-46 | Tarif va toifa tarixi — SC#3 ning to'liq isboti | integration | `docker compose --profile test run --rm tests pytest tests/integration/tes…` | ✅ | ✅ green |
| 02-07-02 | 07 | 6 | MARKET-02,MARKET-03,MARKET-04,MARKET-05 | T-02-47 | Sotuvchi biriktirish — D-09/D-10/D-11/D-12 isboti | integration | `docker compose --profile test run --rm tests pytest tests/integration/tes…` | ✅ | ✅ green |
| 02-07-03 | 07 | 6 | MARKET-02,MARKET-03,MARKET-04,MARKET-05 | T-02-48 | Ish kunlari kalendari (SC#4) va rasta raqamining qayta ishlatilmasligi (SC#2/D-02) | integration | `docker compose --profile test run --rm tests pytest tests/integration/tes…` | ✅ | ✅ green |
| 02-08-01 | 08 | 7 | MARKET-02,MARKET-06 | T-02-54 | Domen DTO'lari, xato kodlari va oddiy reestrlar (zonalar, toifalar) | gate | `docker compose --profile test run --rm tests sh -c "ruff check . && mypy …` | ✅ | ✅ green |
| 02-08-02 | 08 | 7 | MARKET-02,MARKET-06 | T-02-55 | `stall_repo.py` va `stalls.py` — reestr, keyset, filtrlar va xarita agregati | gate | `docker compose --profile test run --rm tests sh -c "ruff check . && mypy …` | ✅ | ✅ green |
| 02-08-03 | 08 | 7 | MARKET-02,MARKET-06 | T-02-56 | Marshrutlarni ulash, cross-tenant matritsasiga qo'shish va SC#2 ning API isboti | integration | `docker compose --profile test run --rm tests pytest tests/integration/tes…` | ✅ | ✅ green |
| 02-09-01 | 09 | 8 | MARKET-03,MARKET-05 | T-02-62 | `tariff_repo.py` va `tariffs.py` — faqat qo'shadigan tarif API'si | gate | `docker compose --profile test run --rm tests sh -c "ruff check . && mypy …` | ✅ | ✅ green |
| 02-09-02 | 09 | 8 | MARKET-03,MARKET-05 | T-02-63 | `calendar.py` — haftalik jadval va istisno kunlar | integration | `docker compose --profile test run --rm tests pytest tests/integration/tes…` | ✅ | ✅ green |
| 02-09-03 | 09 | 8 | MARKET-03,MARKET-05 | T-02-64 | Tarif va kalendar API'sining integratsiya testlari | integration | `docker compose --profile test run --rm tests pytest tests/integration/tes…` | ✅ | ✅ green |
| 02-10-01 | 10 | 9 | MARKET-04 | T-02-70 | `vendor_repo.py` va `vendors.py` — reestr va shaxsiy ma'lumot o'qish auditi | gate | `docker compose --profile test run --rm tests sh -c "ruff check . && mypy …` | ✅ | ✅ green |
| 02-10-02 | 10 | 9 | MARKET-04 | T-02-71 | `assignments.py` — biriktirish davrlari va almashinuv oqimi | integration | `docker compose --profile test run --rm tests pytest tests/integration/tes…` | ✅ | ✅ green |
| 02-10-03 | 10 | 9 | MARKET-04 | T-02-72 | Sotuvchi va biriktirish API'sining integratsiya testlari | integration | `docker compose --profile test run --rm tests pytest tests/integration/tes…` | ✅ | ✅ green |
| 02-11-01 | 11 | 10 | MARKET-01 | T-02-79 | `market_repo.py` va qoralama bozor yaratish / o'chirish | gate | `docker compose --profile test run --rm tests sh -c "ruff check . && mypy …` | ✅ | ✅ green |
| 02-11-02 | 11 | 10 | MARKET-01 | T-02-80 | `setup-status` agregati va faollashtirish darvozasi | integration | `docker compose --profile test run --rm tests pytest tests/integration/tes…` | ✅ | ✅ green |
| 02-11-03 | 11 | 10 | MARKET-01 | T-02-81 | SC#1 ning uchidan-uchiga testi va RBAC darvozasi | integration | `docker compose --profile test run --rm tests pytest tests/integration/tes…` | ✅ | ✅ green |
| 02-12-01 | 12 | 11 | MARKET-02,MARKET-04 | T-02-87 | Xavfsiz `.xlsx` o'qish qatlami va uning hujum testlari | unit | `docker compose --profile test run --rm tests pytest tests/unit/test_xlsx_…` | ✅ | ✅ green |
| 02-12-02 | 12 | 11 | MARKET-02,MARKET-04 | T-02-88 | Validator (yozishdan oldin) va shablon/xato-hisoboti generatori | unit | `docker compose --profile test run --rm tests pytest tests/unit/test_xlsx_…` | ✅ | ✅ green |
| 02-12-03 | 12 | 11 | MARKET-02,MARKET-04 | T-02-89 | `imports.py` routeri va all-or-nothing / idempotentlik testlari | integration | `docker compose --profile test run --rm tests pytest tests/integration/tes…` | ✅ | ✅ green |
| 02-13-01 | 13 | 12 | MARKET-01,MARKET-02,MARKET-03,MARKET-04,MARKET-05,MARKET-06 | T-02-98 | Zod kontraktlari va xato-kod xaritasi | component | `npm --prefix frontend run typecheck && npm --prefix frontend run lint` | ✅ | ✅ green |
| 02-13-02 | 13 | 12 | MARKET-01,MARKET-02,MARKET-03,MARKET-04,MARKET-05,MARKET-06 | T-02-99 | TanStack Query hooklari va navigatsiya kengaytmasi | component | `npm --prefix frontend run typecheck && npm --prefix frontend run lint && …` | ✅ | ✅ green |
| 02-13-03 | 13 | 12 | MARKET-01,MARKET-02,MARKET-03,MARKET-04,MARKET-05,MARKET-06 | T-02-100 | To'qqizta namespace uchun uch tilli matnlar | component | `npm --prefix frontend run i18n:check && npm --prefix frontend test` | ✅ | ✅ green |
| 02-14-01 | 14 | 13 | MARKET-02,MARKET-06 | T-02-105 | Rastalar reestri sahifasi — ro'yxat, filtrlar va tahrir dialoglari | component | `npm --prefix frontend run typecheck && npm --prefix frontend run lint && …` | ✅ | ✅ green |
| 02-14-02 | 14 | 13 | MARKET-02,MARKET-06 | T-02-106 | Sxematik plan-xarita — grid, katak, tone kontrakti va legenda | component | `npm --prefix frontend run typecheck && npm --prefix frontend run lint && …` | ✅ | ✅ green |
| 02-14-03 | 14 | 13 | MARKET-02,MARKET-06 | T-02-107 | Rasta kartasi dialogi va xarita darvozasi (vitest) | component | `npm --prefix frontend run test:component && npm --prefix frontend run typ…` | ✅ | ✅ green |
| 02-15-01 | 15 | 13 | MARKET-03,MARKET-04,MARKET-05 | T-02-112 | Sotuvchilar reestri va biriktirish oqimi | component | `npm --prefix frontend run test:component && npm --prefix frontend run typ…` | ✅ | ✅ green |
| 02-15-02 | 15 | 13 | MARKET-03,MARKET-04,MARKET-05 | T-02-113 | Tarif tarixi, zona va toifa ro'yxatlari | component | `npm --prefix frontend run typecheck && npm --prefix frontend run lint && …` | ✅ | ✅ green |
| 02-15-03 | 15 | 13 | MARKET-03,MARKET-04,MARKET-05 | T-02-114 | Ish kunlari kalendari | component | `npm --prefix frontend run typecheck && npm --prefix frontend run lint && …` | ✅ | ✅ green |
| 02-16-01 | 16 | 14 | MARKET-01,MARKET-02,MARKET-04 | T-02-120 | Usta qobig'i, qadam relsi va marshrutlar | component | `npm --prefix frontend run test:component && npm --prefix frontend run typ…` | ✅ | ✅ green |
| 02-16-02 | 16 | 14 | MARKET-01,MARKET-02,MARKET-04 | T-02-121 | Rekvizitlar formasi va faollashtirish paneli | component | `npm --prefix frontend run typecheck && npm --prefix frontend run lint && …` | ✅ | ✅ green |
| 02-16-03 | 16 | 14 | MARKET-01,MARKET-02,MARKET-04 | T-02-122 | Excel import paneli va xato ro'yxati | component | `npm --prefix frontend run test:component && npm --prefix frontend run typ…` | ✅ | ✅ green |
| 02-17-01 | 17 | 15 | MARKET-01,MARKET-02,MARKET-03,MARKET-04,MARKET-05,MARKET-06 | T-02-128 | Real ma'lumot yo'riqnomasi va takrorlanadigan import skripti | gate | `node scripts/karmana-import.mjs --help && node -e "const fs=require('node…` | ✅ | ✅ green |
| 02-17-02 | 17 | 15 | MARKET-01,MARKET-02,MARKET-03,MARKET-04,MARKET-05,MARKET-06 | T-02-129 | Beshta faza mezonining uchidan-uchiga avtomatik tekshiruvi | integration | `docker compose --profile test run --rm tests pytest tests/integration/tes…` | ✅ | ✅ green |
| 02-17-03 | 17 | 15 | MARKET-01,MARKET-02,MARKET-03,MARKET-04,MARKET-05,MARKET-06 | T-02-130 | Real ma'lumotni yuklash, solishtirish va faza darvozasi | gate + human-check | `npm run gate` | ✅ | ✅ green |
| 02-18-01 | 18 | 16 | MARKET-01 | T-02-140 | `/markets/new` uchun marshrut istisnosi — PREFIKS emas, TENGLIK (huquq oshirish yuzasi ochilmaydi) | component | `npm --prefix frontend run test:component && npm --prefix frontend run i18…` | ✅ | ✅ green |
| 02-18-02 | 18 | 16 | MARKET-01 | T-02-143 | Bo'sh bozor ro'yxatidan ustaga havola va WR-09 (403 `password_change_required`) boshi berk ko'chasi | component | `npm --prefix frontend run test:component && npm --prefix frontend run i18…` | ✅ | ✅ green |
| 02-18-03 | 18 | 16 | MARKET-01 | T-02-144 | Uchala to'siqni alohida qulflaydigan manba darvozasi (`wizard-reachability.test.mjs`) | gate | `npm --prefix frontend run test:unit && npm run gate` | ✅ | ✅ green |
| 02-19-01 | 19 | 16 | MARKET-04,MARKET-02 | T-02-145 | `GET /stalls` va `GET /stalls/{id}` — shaxsiy ma'lumot o'qishining auditi (D-09) | gate | `docker compose --profile test run --rm tests sh -c "ruff check services/c…` | ✅ | ✅ green |
| 02-19-02 | 19 | 16 | MARKET-04,MARKET-02 | T-02-146 | `assignments.py` marshruti + `VENDOR_VIEW` chegarasi dekoratorda va introspektsiya teglari | unit | `docker compose --profile test run --rm tests sh -c "ruff check . && mypy …` | ✅ | ✅ green |
| 02-19-03 | 19 | 16 | MARKET-04,MARKET-02 | T-02-149 | Butun `GET` yuzasini supuruvchi darvoza — marshrut GRAFI o'qiladi, manba matni emas | integration | `docker compose --profile test run --rm tests pytest tests/integration/tes…` | ✅ | ✅ green |
| 02-20-01 | 20 | 16 | MARKET-02,MARKET-04 | T-02-150 | Har bir domen kalitini `market_id` bilan doiralash (global konstantalar butunlay olib tashlangan) | component | `npm --prefix frontend run typecheck && npm --prefix frontend run lint && …` | ✅ | ✅ green |
| 02-20-02 | 20 | 16 | MARKET-02,MARKET-04 | T-02-151 | Sessiya identifikatori o'zgarganda keshni to'liq tozalash (`subscribeSessionReset` -> `clear()`) | component | `npm --prefix frontend run typecheck && npm --prefix frontend run lint` | ✅ | ✅ green |
| 02-20-03 | 20 | 16 | MARKET-02,MARKET-04 | T-02-154 | Ikki himoya qatlamining MUSTAQILLIGI — har test bitta yarimni o'lchaydi | component | `npm --prefix frontend test` | ✅ | ✅ green |
| 02-21-01 | 21 | 17 | MARKET-05 | T-02-155 | `0011` — `open_weekdays` ning jimgina «har kuni ochiq» standartini IKKALA yo'ldan olib tashlash | gate | `docker compose --profile migrate run --rm migrate alembic upgrade head &&…` | ✅ | ✅ green |
| 02-21-02 | 21 | 17 | MARKET-05 | T-02-157 | Usta 1-qadamida haftalik ish rejimi tanlovi — `NULL` / `'{}'` / to'ldirilgan uch holat | component | `npm --prefix frontend run typecheck && npm --prefix frontend run lint && …` | ✅ | ✅ green |
| 02-21-03 | 21 | 17 | MARKET-05 | T-02-158 | WR-05: registr farqli takroriy rasta kodi QATOR RAQAMI bilan rad etiladi | integration | `docker compose --profile test run --rm tests pytest tests/unit/test_impor…` | ✅ | ✅ green |
| 02-22-01 | 22 | 18 | MARKET-01,MARKET-02,MARKET-03,MARKET-04,MARKET-05,MARKET-06 | T-02-160 | Yopilgan bo'shliqlarning nomlangan buyruq + o'lchangan test soni bilan dalili | gate | `npm run gate` | ✅ | ✅ green |
| 02-22-02 | 22 | 18 | MARKET-01,MARKET-02,MARKET-03,MARKET-04,MARKET-05,MARKET-06 | T-02-161 | Ro'yxat ↔ Traceability jadvalining ikki yo'nalishli mexanik solishtiruvi | gate | `node scripts/check-requirements-sync.mjs` | ✅ | ✅ green |
| 02-24-01 | 24 | 19 | MARKET-07 | T-02-175 | Rol berish darajasining YAGONA manbai — `platform_admin` ikkala darajada ham to'plamda yo'q | unit | `docker compose --profile test run --rm tests sh -c "ruff check . && ruff …` | ✅ | ✅ green |
| 02-24-02 | 24 | 19 | MARKET-07 | T-02-178 | `POST /imports/staff` — qisman yozilmaydigan roster; test SANOQNI o'lchaydi, status kodini emas | integration | `docker compose --profile test run --rm tests sh -c "ruff check . && mypy …` | ✅ | ✅ green |
| 02-24-03 | 24 | 19 | MARKET-07 | T-02-176 | Bir martalik parollar: repozitoriy qatlamiga kirmaydi, keshlanmaydi, jurnalga faqat SANOQ tushadi | component | `npm --prefix frontend run typecheck && npm --prefix frontend run lint && …` | ✅ | ✅ green |
| 02-23-01 | 23 | 20 | MARKET-01,MARKET-02,MARKET-03,MARKET-04,MARKET-05,MARKET-06 | T-02-165 | Generator quvurning shablon yo'lidan MUSTAQIL (`ast` darvozasi; o'z-o'ziga qaytish yopilgan) | unit | `docker compose --profile test run --rm tests pytest tests/unit/test_karma…` | ✅ | ✅ green |
| 02-23-02 | 23 | 20 | MARKET-01,MARKET-02,MARKET-03,MARKET-04,MARKET-05,MARKET-06 | T-02-167 | Karmana miqyosida (600/480) uchidan-uchiga import; rad etish yo'llarida SANOQ o'zgarmaydi | integration | `docker compose --profile test run --rm tests pytest tests/integration/tes…` | ✅ | ✅ green |
| 02-23-03 | 23 | 20 | MARKET-01,MARKET-02,MARKET-03,MARKET-04,MARKET-05,MARKET-06 | T-02-169 | `nyquist_compliant` bayrog'ining mexanik darvozasi — bayroq yolg'on gapira olmaydi | gate | `node scripts/check-validation-signoff.mjs` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

> **`Status` ustuni FAQAT `Automated Command` ustunini bildiradi** va u
> 2026-08-03 da `npm run gate` ning to'liq yashil o'tishi bilan tasdiqlangan
> (992 backend + 322 tenancy + 57 node + 74 vitest testi,
> lint/mypy/typecheck/eslint/build; exit 0).
> 2026-08-01 dagi o'lchov (890 backend + 54 node + 40 vitest) tarixiy yozuv
> sifatida SAQLANADI — o'sishni ko'rsatish byudjet muhokamasi uchun kerak.
>
> ⚠ **Bu jadvaldagi to'liq yashil ustun «faza mezonlari isbotlangan» degani
> EMAS — u «kod darvozalari yashil» degani.** Insonni talab qiladigan
> to'rtta band quyidagi «Verification triage» jadvalida ALOHIDA yuritiladi
> va ularning har birida egasi (`owner`) hamda ishga tushish sharti
> (`trigger`) bor. Ular fazaning darvozasidan tashqarida, LEKIN nomlangan.

**Coverage anchors the planner must not drop** (each already has a named command in RESEARCH.md):

| Requirement | Anchor behavior | Test file |
|-------------|-----------------|-----------|
| MARKET-01 / SC#1 | Wizard end-to-end reaches `is_active=true`; incomplete market → 409 with missing-step list | `tests/integration/test_wizard_flow.py` |
| MARKET-02 / SC#2 | Stall status transitions audited **including raw SQL**; closed stall code cannot be reused | `tests/integration/test_stall_registry.py`, `test_stall_code_reuse.py` |
| MARKET-03 / SC#3 | Past date keeps old price; effective day uses new price; past tariff immutable via raw SQL; existing row never touched | `tests/integration/test_tariff_history.py` |
| MARKET-04 | Overlapping assignment → 23P01; handover day boundary; vacancy gap → 0 rows; phone unique per market; vendor read audited | `tests/integration/test_stall_assignments.py`, `test_vendors.py` |
| MARKET-05 / SC#4 | Weekly closure + holiday + exception-open all resolve through `market_is_open()`; fail-closed on missing config | `tests/integration/test_market_calendar.py` |
| MARKET-06 / SC#5 | Map renders zone blocks in code order; stall click opens card; 1000 cells render without full re-render on select | `frontend/src/components/stalls/stall-map.test.tsx` |
| Import (D-13/D-14/D-15) | All-or-nothing with per-row line numbers; re-import idempotent; billion-laughs + zip-bomb rejected; formula injection escaped | `tests/integration/test_stall_import.py`, `tests/unit/test_xlsx_reader.py`, `test_xlsx_template.py` |
| FOUND-02 (regression) | All 9 new tables carry `market_id` + RLS ENABLE+FORCE + tenant policy + `market_id`-leading indexes | `tests/tenancy/test_meta.py` (**existing, automatic**) |
| Cross-tenant (regression) | Every new endpoint returns **404** for another tenant's object; uncovered routes fail CI | `tests/tenancy/test_cross_tenant.py`, `test_route_coverage.py` (**existing, automatic**) |

---

## Wave 0 Requirements

Two of these are **inherited landmines from Phase 1** and must land before the first Phase 2 migration — otherwise the existing meta-tests go red on the first table created.

- [x] `packages/sbozor-core/sbozor_core/schema_contract.py` — remove `stall_assignments` from `FINANCIAL_TABLES` (with a reason comment); extend `AUDITED_TABLES` to the 6 domain tables — **Pitfall 3**
- [x] `services/core-api/app/security/rbac.py` — grant `PLATFORM_ADMIN` the `STALL_MANAGE` / `TARIFF_MANAGE` / `VENDOR_MANAGE` permissions; add the two new `Permission` members — **Pitfall 6** (without this, the person running the wizard cannot enter stalls or tariffs into the market they are building)
- [x] `ops/db/init/00-extensions.sql` + read it from `tests/conftest.py` — `btree_gist` — **Pitfall 1**
- [x] `tests/fixtures/market_domain.py` — two-market seed (zone / category / stall / tariff / vendor / assignment), layered on the existing `two_markets.py`
- [x] `tests/tenancy/test_market_domain_meta.py` — asserts the EXCLUDE constraint exists, `tariff_past_immutable` trigger exists, `stall_code_claim` trigger exists, and `market_is_open` is **NOT** `SECURITY DEFINER` — **Pitfall 2** (Alembic cannot see `ExcludeConstraint` drift in either direction; this meta-test is the only guard)
- [x] `tests/integration/test_{tariff_history,stall_assignments,market_calendar,stall_import,wizard_flow,stall_registry,stall_code_reuse,vendors}.py` — stubs *(hammasi endi to'liq test, stub emas; `vendors` fayli `test_vendors_api.py` nomi bilan)*
- [x] `tests/unit/test_{xlsx_reader,xlsx_template}.py` — parser limits, billion-laughs smoke test, formula injection
- [x] `frontend/src/components/stalls/stall-map.test.tsx` — vitest + jsdom (infrastructure ready from Phase 1)
- [x] `tests/tenancy/test_route_coverage.py` — register the new routes (CI goes red until done — **this is deliberate**)

**Framework install:** not required — every tool is present from Phase 1.

**To'qqizta band diskda TEKSHIRILDI (2026-08-01, 02-17):** to'qqizala fayl mavjud
(`ls` bilan), `FINANCIAL_TABLES` da `stall_assignments` YO'Q (sabab izohi bilan),
`AUDITED_TABLES` da yettita domen jadvali bor, `PLATFORM_ADMIN` uchala `*_MANAGE`
huquqiga ega, `conftest.py::_bootstrap_extensions` `00-extensions.sql` ni
VERBATIM bajaradi va `MINIMUM_MATRIX_ROUTES = 34` (matritsada 43 marshrut).

⚠ **Bu bandlarning bajarilishi ularning KUCHINI o'lchamaydi.** Kuchi 02-17 dagi
olti sabotaj bilan alohida o'lchandi (`02-17-SUMMARY.md`), shu jumladan
`PLATFORM_ADMIN` dan `STALL_MANAGE` ni olib tashlash — 2-bandning aynan
o'zi — va u `test_phase2_criteria.py::test_sc1_...` ni AYNAN qizartirdi.

---

## Verification triage (2026-08-03 da qayta o'tkazildi)

Ilgari bu bo'lim «Manual-Only Verifications» deb atalar va to'rtala bandi
ham ochiq-qizil belgi bilan turardi (o'sha belgi — `check-validation-
signoff.mjs` ning 2-qoidasi taqiqlaydigan so'z; uni bu yerda LITERAL
yozib bo'lmaydi, aks holda darvoza o'z hujjatiga qarshi ishlardi va
bayroq abadiy `false` bo'lib qolardi). Bu holat ikki xil narsani ARALASHTIRIB
yuborgan edi: **avtomatlashtirish MUMKIN, lekin qilinmagan** ish bilan
**avtomatlashtirib BO'LMAYDIGAN** ish. Birinchisi qarz, ikkinchisi esa
mahsulotning tabiati. Ular birga turganda ikkalasi ham bir xil ko'rinadi
va ikkalasi ham e'tibordan qoladi.

Shuning uchun har bir band endi AYNAN bitta toifaga tushadi:
**AVTOMATLASHTIRILDI** yoki **INSON**.

| # | Band | Talab | Toifa | Nima bo'ldi |
|---|------|-------|-------|-------------|
| 1a | Import ~300–1000 miqyosda ishlaydi; D-14/D-15 semantikasi, README §7 ning yettala raqami, telefon normallashtirishi, xaritaning to'liqligi | MARKET-01…06 | **AVTOMATLASHTIRILDI** | `tests/integration/test_karmana_scale_import.py` — 8 zona / 605 rasta / 480 sotuvchi. Buyruq: `docker compose --profile test run --rm tests pytest tests/integration/test_karmana_scale_import.py -q`. Yuk `tests/fixtures/karmana_seed.py` dan keladi va quvurning shablon yo'lidan MUSTAQIL (`ast` darvozasi, T-02-165) |
| 1b | Ma'muriyatning **qog'oz reestri** bilan solishtirish | MARKET-01, MARKET-02 | **INSON** | Taqqoslanadigan ikkinchi tomon tizimdan tashqarida. Egasi: bozor ma'muriyati (hisobchi) + platforma admini. Shart: ma'muriyat fayllari kelganda. Tartib: `ops/data/karmana/README.md` §2 → §7 |
| 2 | Ustaning kod yozmasdan yakunlanishi — **foydalanuvchanlik kuzatuvi** | MARKET-01 / SC#1 | **INSON** (rejalashtirilgan) | Mashinaviy yarmi qamralgan: `test_phase2_criteria.py::test_sc1_...` butun zanjirni FAQAT HTTP orqali bajaradi; 02-18 esa yetib borish yo'lini `wizard-reachability.test.mjs` bilan qulfladi. ⚠ 02-18 dan OLDIN bu band «bajarib bo'lmaydi» edi (ikki to'siq); endi u **rejalashtirilgan**. Egasi: platforma admini + mahsulot egasi. Shart: pilot tayyorgarligi haftasi |
| 3a | Xarita real miqyosda **birorta rastani tushirmaydi** | MARKET-06 / SC#5 | **AVTOMATLASHTIRILDI** | «Real miqyos» endi TA'RIFLANGAN (generator konstantalari: 8 zona × 600 rasta). `stall-map.test.tsx` DOM'da aynan 600 katak va 8 zona bloki topadi hamda kodlar to'plamini serverdagi bilan solishtiradi. Buyruq: `npm --prefix frontend test` |
| 3b | Xaritaning maqsadli qurilmada **O'QILISHI** | MARKET-06 / SC#5 | **INSON** | Perseptual: jsdom shrift, kontrast va skroll masofasini o'lchay olmaydi. Egasi: bozor admini + frontend egasi. Shart: pilot tayyorgarligi haftasi |
| 4 | Rekvizit formatlari (STIR, bank, MFO) buyurtmachi bilan tasdiqlanishi | MARKET-01 | **INSON** | Bugungi holat xavfsiz tomonga qiya: server rekvizitlarni ATAYIN formatlamaydi (02-16 qarori), klientdagi MFO qoidasi QULAYLIK bo'lib yozilgan va uni olib tashlash ko'rsatmasi kodda turibdi — ya'ni forma QOTIRILMAGAN va kechiktirish zarar keltirmaydi. Egasi: mahsulot egasi + buyurtmachi. Shart: formani qotirishdan oldin |

**Natija: 2 ta band avtomatlashtirildi (1a, 3a), 4 ta band inson bandi
sifatida NOMLANDI (1b, 2, 3b, 4).** To'rttasining ham egasi va ishga
tushish sharti frontmatter'dagi `human_only_verifications` da yozilgan va
ularning to'liqligini `scripts/check-validation-signoff.mjs` MAJBURLAYDI:
`owner` yoki `trigger` tushib qolsa skript exit 1 beradi va bandni nomi
bilan ko'rsatadi (T-02-170).

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies — 71/71 satrda `Automated Command` bor (51 + 02-18…02-24 + 02-23)
- [x] Sampling continuity: no 3 consecutive tasks without automated verify — har taskda buyruq bor, ya'ni ketma-ketlik uzilmaydi
- [x] Wave 0 covers all MISSING references (9 items above) — to'qqizala band diskda tekshirildi
- [x] No watch-mode flags — `grep -rn "\-\-watch" package.json frontend/package.json` da darvoza skriptlarida yo'q (`vitest run`, `node --test`)
- [x] Feedback latency measured and recorded (do not carry Phase 1 numbers forward) — o'lchandi va yozildi; **to'lqin byudjeti hamon BUZILGAN** va u `open_items` da 3-faza egasi bilan yuritiladi
- [x] `nyquist_compliant: true` set in frontmatter — **SKRIPT HISOBLADI, ODAM E'LON QILMADI** (`node scripts/check-validation-signoff.mjs`)

**Approval:** ✅ **BERILDI — namuna olish qamrovi bo'yicha.**

### Nega `true` «isbotlanmagan narsani isbotlangan deb e'lon qilish» EMAS

Keyingi o'quvchi bu bayroqni aynan shu savol bilan o'qiydi, shuning uchun
javob shu yerda turadi.

`nyquist_compliant` — **namuna olish (sampling) qamrovi** haqidagi da'vo:
«har bir taskning avtomatik tekshiruv buyrug'i bor, u yashil, va
avtomatlashtirib bo'lmaydigan bandlar egasi hamda sharti bilan
NOMLANGAN». U «faza mukammal» yoki «hech narsa qolmadi» degani EMAS.

To'rtta inson bandi (1b, 2, 3b, 4) **yo'qolmaydi**: ular yuqoridagi
jadvalda va frontmatter'da, har birida `owner` va `trigger` bilan
yashaydi. Ular fazaning **darvozasidan tashqarida** yuritiladi — chunki
ROADMAP ning 2026-08-01 dagi self-service qoidasi buni qat'iy qilib
qo'ygan:

> *«Tashqi bog'liqlik hech qachon `Blocks:` bo'lmaydi.»*

Ilgari bayroq `false` edi va sababi to'g'ri edi: fazaning maqsad jumlasi
«Karmananing real ma'lumoti tizimda yashaydi» degan ikkinchi qismni ham
o'z ichiga olardi. **O'sha jumla 2026-08-01 da ROADMAP'ning o'zida qayta
ta'riflandi** (milestone egasining ochiq qarori):

> *«fazaning yetkazib berish mahsuloti — import qobiliyati, ma'lum bir
> fayl emas: yo'l (shablon → validatsiya → all-or-nothing yuklash → D-15
> takroriy import himoyasi) qurilgan, hujjatlashtirilgan va o'lchangan
> bo'lsa, faza yopiladi»*

02-23 aynan «o'lchangan» qismini bajardi: qobiliyat Karmana miqyosida,
quvur o'zi ishlab chiqarmagan iflos ma'lumot bilan uchidan-uchiga
o'lchandi va o'lchov CI'da takrorlanadi. Ya'ni bayroqning o'zgarishi
kelishuv emas — **shartning o'zgarishi va uning bajarilishi**.

⚠ Va bayroq endi qo'lda ham yozilmaydi: uni
`scripts/check-validation-signoff.mjs` hisoblaydi. Ochiq band belgisi
bilan `true` birga turolmaydi; egasiz inson bandi ham turolmaydi. Sabotaj
bilan o'lchandi (`02-23-SUMMARY.md`).

**Fazadan TASHQARIDA yuritiladigan bandlar (egasi bilan):**

| # | Band | Egasi | Ishga tushish sharti |
|---|------|-------|----------------------|
| 1 | Ma'muriyat fayllarini olish va §2 tartibi bo'yicha import (tarif qadami faollashtirishdan OLDIN) | Bozor ma'muriyati + platforma admini | Fayllar topshirilgan kun |
| 2 | README §7 ni qog'oz reestr bilan solishtirish va farqlarni yozish | Hisobchi + platforma admini | 1-band bajarilgandan keyin |
| 3 | Ustaning foydalanuvchanlik kuzatuvi | Platforma admini + mahsulot egasi | Pilot tayyorgarligi haftasi |
| 4 | Rekvizitlar formasini buyurtmachiga ko'rsatish (A1/A2) | Mahsulot egasi + buyurtmachi | Formani qotirishdan oldin |
| 5 | Xaritani maqsadli qurilmada real miqyosda ochish | Bozor admini + frontend egasi | Pilot tayyorgarligi haftasi |
| 6 | To'lqin darajasidagi kechikish byudjeti (`pytest-xdist` yoki tranzaksiyaga o'ralgan seed) | 3-faza | 3-faza rejalashtirilganda |

**Oltala eski «yopish uchun kerak bo'lgan band» ning holati:**

| Eski band | Holat | Kim yopdi |
|-----------|-------|-----------|
| 1. Ma'muriyatdan beshta hujjat va import | **Inson bandiga aylantirildi** (mexanik yarmi avtomatlashtirildi) | 02-23 (ROADMAP self-service qoidasi asosida) |
| 2. README §7 ni qog'oz reestr bilan solishtirish | **BO'LINDI**: mexanik yarmi avtomatlashtirildi, qog'oz yarmi inson bandi | 02-23 |
| 3. Ustaga navigatsiya havolasi va «bozorsiz admin» boshi berk ko'chasi | **BAJARILDI** | 02-18 (uchala to'siq, `wizard-reachability.test.mjs` bilan qulflangan) |
| 4. Rekvizitlar formasini buyurtmachiga ko'rsatish | **Inson bandi** (egasi va sharti bilan) | 02-23 (triaj) |
| 5. Xaritani maqsadli qurilmada ochish | **BO'LINDI**: to'liqlik avtomatlashtirildi, o'qilish inson bandi | 02-23 |
| 6. Kechikish byudjeti | **3-FAZAGA O'TKAZILDI** (egasi nomlangan, `open_items` da) | 02-22 → 02-23 (o'sish qayta o'lchandi) |
