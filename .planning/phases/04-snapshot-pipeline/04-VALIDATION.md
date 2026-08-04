---
phase: 4
slug: snapshot-pipeline
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-04
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
| **Quick run command** | `npm run gate:fast` — 3-fazada o'lchandi: **32 s**, chegara 180 s |
| **Full suite command** | `npm run gate` — 3-fazada oxirgi toza o'lchov: **538 s** |
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

| Qadam | Kim | Nima |
|---|---|---|
| 1 | Wave 0 rejasi | 3× o'lchov (sovuq / issiq / issiq) **yangi konteynerlar bilan** |
| 2 | Yakuniy reja | Yana 3× o'lchov, chegara = eng yomon + 20 % |
| 3 | — | Agar yangi chegara 1200 s dan past bo'lsa — **tushiriladi**; oshsa — sabab bilan asoslanadi |

⚠ **Jimgina oshib ketish yoki jimgina bo'sh qoldirish — ikkalasi ham qabul qilinmaydi.**

---

## Per-Task Verification Map

*Har PLAN.md taski uchun bitta qator — `gsd-planner` to'ldiradi. `Status` ustunini ijrochi to'ldiradi.*

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| *(rejalashtiruvda to'ldiriladi)* | | | | | | | | | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

`04-PATTERNS.md` §5 o'n bir bandni sanaydi; `04-UI-SPEC.md` bittasini qo'shadi. **Uchtasi jimgina yiqiladigan turdagi** — testlar yashil bo'lgani holda ishlab chiqarish buziladi:

- [ ] **W0-1** — ⚠ **O'LCHOV:** `GENERATED STORED` ustun **kompozit FK nishoni** bo'la oladimi (`postgres:18.4`). `UNIQUE` tomoni allaqachon isbotlangan (`helpers.py:356-362` + `tests/fixtures/financial.py`), **FK-nishon tomoni emas**. Zond shabloni: `tests/fixtures/financial.py:59-145`. Yiqilsa `0014` trigger variantida yoziladi — **migratsiyadan keyin aniqlash qayta migratsiya demakdir** (D-23 / OQ-4).
- [ ] **W0-2** — 🔇 `aiobotocore==3.9.0` va `Pillow==12.3.0` ni `[project] dependencies` ga. **3-fazadagi `httpx` epizodining aynan takrori:** `dev` guruhida qolsa hamma test yashil, deploy'da `ModuleNotFoundError`. `tests/unit/test_runtime_deps.py` kengaytiriladi.
- [ ] **W0-3** — 🔇 `taskiq scheduler` ni `compose.yaml` ga + `npm run up` yorlig'ini yangilash. Planer profil ortida qolsa slotlar **hech qachon** materializatsiya bo'lmasdi **va hech qanday xato chiqmasdi**.
- [ ] **W0-4** — `storage` (SeaweedFS) xizmati + `ops/seaweedfs/s3.json.example`. `anonymous` yozuvining **yo'qligi** grep-darvoza bilan qulflanadi.
- [ ] **W0-5** — `AUDITED_TABLES` ga `snapshot_schedules`, `snapshot_schedule_slots`. Reyestr **migratsiyadan oldin** yoziladi va `test_audited_tables_have_trigger` vaqtincha qizil turadi — bu **kutilgan** (1-fazadagi `FINANCIAL_TABLES` naqshi).
- [ ] **W0-6** — 🔇 `market_delete_draft()` kaskadini beshta yangi jadval bilan kengaytirish + `0015` migratsiyasi. **3-fazadagi `0012`→`0013` juftligining aynan takrori:** kengaytirilmasa `0014` dan keyin bozor o'chirish FK buzilishi bilan yiqiladi. Tartib: `snapshots` → `capture_runs` → `snapshot_schedule_slots` → `snapshot_schedules`.
- [ ] **W0-7** — `tests/tenancy/test_meta.py` ga `markets.timezone = 'Asia/Tashkent'` invarianti. `scheduled_at` `markets.timezone` dan, `business_date` esa **literal**dan hisoblanadi — ikkinchi mintaqa qo'shilgan kuni test qizarsin, biznes-kun **jimgina siljimasin**.
- [ ] **W0-8** — `ix_capture_runs_overdue` uchun `INDEX_EXCEPTIONS` ga **sabab bilan** yozuv. Watchdog barcha bozorlar ustidan yuradi, indeks `market_id` bilan boshlanmaydi.
- [ ] **W0-9** — `tests/fixtures/frames.py`: sintetik JPEG generatori (`mean`/`stddev`/to'yinganlik bo'yicha). Fixture nomlari **fizik xususiyat** bilan (`frame_mean_8_stddev_2`), detektor chegarasi bilan **emas** — aks holda test o'z chegarasini tasdiqlaydi.
- [ ] **W0-10** — `nvr-sim` ga `frame_mode` + `/Streaming/channels/{ch}/picture`; `mediamtx.yml` ga sifat yo'llari. **Buzuq kadrni MediaMTX bera olmaydi** — u yaroqli oqim beradi, ya'ni baytlarni sim boshqarishi shart.
- [ ] **W0-11** — Markerlarni **tasdiqlash** (`tenancy`, `sim`, `hardware`, `slow` yetadi). Yangi marker qo'shilmaydi; `--strict-markers` tufayli e'lon qilinmagan marker yig'ilishda yiqiladi.
- [ ] **W0-F7** — ⚠ **Rejalararo darvoza to'qnashuvi.** 3-fazaning G-3 darvozasi hedge so'zi **aynan bitta** `errorCause.*` kalitida bo'lishini talab qiladi. 4-fazaga u `capture_stream_limit` uchun ham qonuniy kerak (bir xil fizik sabab). Tegilmasa darvoza **birinchi kuniyoq qizaradi**. `HEDGED_KEYS` ikki kalitli allowlist'ga kengaytiriladi (`04-UI-SPEC.md` §11.11 Qoida 4).

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

> Bu bandlar **fazani bloklamaydi** (2026-08-01 self-service direktivasi). `nyquist_compliant` ularning bajarilganini emas, **shaklini** tekshiradigan skript bilan hisoblanadi — 2-fazadagi `scripts/check-validation-signoff.mjs` naqshi.

---

## Validation Sign-Off

- [ ] Har taskda `<automated>` verify yoki Wave 0 bog'liqligi bor
- [ ] Namuna uzluksizligi: ketma-ket 3 taskda avtomatik verify yo'qligi holati yo'q
- [ ] Wave 0 ning 12 bandi (11 + W0-F7) qoplangan; uchala 🔇 bandi **birinchi migratsiyadan oldin**
- [ ] W0-1 o'lchandi va `0014` ning shakli **o'lchov natijasiga qarab** tanlandi
- [ ] Watch-mode bayrog'i yo'q
- [ ] Sifat filtri sintetik kadrlar bilan **darvoza**, konventsiya emas (W0-9 + W0-10)
- [ ] To'lqin chegarasi 6 o'lchov asosida qayta belgilandi (jimgina qoldirilmadi)
- [ ] `nyquist_compliant: true` skript bilan **hisoblangan**, qo'lda yozilmagan

**Approval:** pending
