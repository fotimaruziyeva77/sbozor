---
phase: 5
slug: kamera-zonalari-cv-va-nazoratchi-tasdig-i
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-05
---

# Phase 5 — Validation Strategy

> **Manba:** `05-RESEARCH.md` § `Validation Architecture`, `05-PATTERNS.md` §5 (Wave 0, 14 band), `05-UI-SPEC.md` darvozalari (G-11…G-19).

---

## Bu fazaning validatsiyasi boshqacha — buni birinchi o'qing

Oldingi to'rt fazada «to'g'ri ishlayaptimi?» savoliga test javob berardi. **Bu fazada bermaydi** (D-01).

Modelning band/bo'sh qarori to'g'riligi — bu haqiqatga qarshi **o'lchov**, va haqiqat (real Karmana kadrlari) hali yo'q. Shuning uchun validatsiya ikki qatlamga bo'linadi va ular aralashtirilmasligi shart:

| Qatlam | Nima isbotlanadi | Bugun mumkinmi |
|---|---|---|
| **Mexanika** | Zona geometriyasi, agregatsiya qoidasi, navbat oqimi, ko'r auditning xolisligi, billing chegarasi, immutabillik | **Ha, to'liq** — seam `sv.Detections` da, undan keyingi hamma narsa sintetik detektsiyalar bilan testlanadi |
| **Aniqlik** | RF-DETR ning verdikti qanchalik to'g'ri | **Yo'q** — oltin to'plam bo'sh; darvoza **uxlab yotadi** |

⚠ **Ikkinchi qatlamning yo'qligini birinchisining yashilligi bilan yopish taqiqlanadi.** Bu loyiha bu shaklni ikki marta rad etgan: 2-fazaning o'zini o'zi tasdiqlovchi shabloni va 3-fazaning «simulyatordan kadr olib tekshiramiz» taklifi.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 (`asyncio_mode=auto`) · vitest (frontend) · `node:test` (skript darvozalari) |
| **Config file** | `pyproject.toml` · `frontend/vitest.config.ts` |
| **Quick run command** | `npm run gate:fast` — chegara **180 s** (o'zgarmaydi) |
| **Full suite command** | `npm run gate` — chegara **W0-13 da qayta belgilanadi** (pastga qarang) |
| **Markerlar** | `tenancy`, `sim`, `hardware`, `slow` + **yangi: `golden`** (W0-10) |

**Bu fazada tug'iladigan infratuzilma:**

| Komponent | Nima uchun | Wave 0 |
|---|---|---|
| `services/cv-service/` — **loyihaning ikkinchi Python bog'liqlik to'plami** | `services/nvr-sim` da `pyproject.toml` ham, `Dockerfile` ham yo'q, ya'ni bu shakl repoda hech qachon qurilmagan | **W0-2**, W0-11, W0-12 |
| `tests/fixtures/detections.py` — `sv.Detections` konstruktori | **Usiz butun zona mantig'i darvoza emas, konventsiya** | **W0-7** |
| `tests/fixtures/golden_set/` + `manifest.jsonl` + `eval-golden-set.py` | Faza mahsuloti — **mashina**, raqam emas | **W0-9** |
| `frontend/src/lib/zone-geometry.ts` | Geometriya sof funksiyalarda — render qatlami almashadi, geometriya emas (D-05) | **W0-8** |

---

## Sampling Rate

- **Har task commitidan keyin:** `npm run gate:fast` (chegara **180 s**, o'zgarmaydi)
- **Har to'lqindan keyin:** `npm run gate`
- **Maksimal kechikish:** W0-13 o'lchoviga qarab

### `gate` byudjeti — 4-fazadan meros ochiq band (D-26)

4-faza chegarani **900 s** ga tushirdi, keyin `04-14` uni **1009 s va 1174 s** bo'lib o'tganini o'lchadi va **chegarani ko'tarmadi**. Sababni `04-VERIFICATION` nomladi: xostda **ikkinchi to'liq Docker steki** ishlab turgan (7 ta `parnikkpi-*` konteyner). Nazorat: `gate:fast` ayni bir xil ish ustida **68 s → 129 s**.

**W0-13 ning talabi:** o'lchov **tinch xostda** va **`cv-service` build'i qo'shilgandan keyin** uch marta olinadi. Chegara = eng yomon + 20 %.

⚠ **Jimgina oshib ketish ham, jimgina bo'sh qoldirish ham qabul qilinmaydi.** Agar tinch xost ta'minlanmasa — buni o'lchov sharti sifatida yozib qo'yish kerak, o'rtachaga aylantirib yashirish emas.

---

## Per-Task Verification Map

*Har PLAN.md taski uchun bitta qator — `gsd-planner` to'ldiradi.*

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| *(rejalashtiruvda to'ldiriladi)* | | | | | | | | | ⬜ pending |

---

## Wave 0 Requirements

`05-PATTERNS.md` §5 o'n to'rt bandni sanaydi. **Uchtasi migratsiyadan oldin hal qilinishi shart** — keyin aniqlash qayta migratsiya demakdir:

- [ ] **W0-1** — `tests/unit/test_license_fence.py`: `rfdetr-plus` / `LicenseRef-*` / AGPL darvozasi. **D-03 — litsenziya endi lockfile invarianti.** Keyin qo'shilsa `uv add rfdetr` allaqachon `torch` ni tortgan bo'lardi.
- [ ] **W0-2** — ⚠ **QAROR:** `cv-service` testlari qayerda yuradi. `tests` konteyneri hozir `core-api` image'ida ishlaydi; qaror ikkala `pyproject.toml` ning shaklini belgilaydi va keyin o'zgartirish qimmat.
- [ ] **W0-3** — ⚠ **QAROR:** ko'r audit urug'i — `sha256(bytea)` / `pgcrypto` / Python. **`05-RESEARCH.md` §C.8.1 ning SQL'i bugun ishlamaydi**: `pgcrypto` o'rnatilmagan, faqat `btree_gist` bor.
- [ ] **W0-4** — `OCCUPANCY_TENANT_TABLES` + `_AUDITED_` + `_DELETE_ORDER` reyestrlari. Reyestr **migratsiyadan oldin** yoziladi va meta-test vaqtincha qizil turadi — bu **kutilgan** (1-fazadagi `FINANCIAL_TABLES` naqshi).
- [ ] **W0-5** — `AUDITED_TABLES` ga `camera_zones`, `zone_reviews`.
- [ ] **W0-6** — 🔇 `market_delete_draft()` kaskadini oltita yangi jadval bilan kengaytirish + `0019`. **`0012`→`0013` va `0014`→`0015` juftligining uchinchi takrori** — kengaytirilmasa `0018` dan keyin bozor o'chirish FK buzilishi bilan yiqiladi.
- [ ] **W0-7** — `tests/fixtures/detections.py`: `sv.Detections` konstruktori, **geometrik fakt bo'yicha** nomlangan (`box_center_in_polygon`), hech qachon kutilgan verdikt bo'yicha emas — aks holda test o'z farazini tasdiqlaydi (4-fazadagi `frame_mean_8_stddev_2` naqshi).
- [ ] **W0-8** — `frontend/src/lib/zone-geometry.ts` + `zone-geometry.**test.tsx**`. ⚠ **`.ts` test fayli `vitest` tomonidan JIMGINA o'tkazib yuboriladi** (`vitest.config.ts:34`) — bu 3-fazada allaqachon boshdan kechirilgan.
- [ ] **W0-9** — `tests/fixtures/golden_set/` skeleti + `manifest.jsonl` sxemasi + `scripts/eval-golden-set.py`. **Uxlab yotadigan darvoza:** `source='karmana'` qatorlari paydo bo'lgan kuni **kodsiz o'zi uyg'onadi**.
- [ ] **W0-10** — `golden` pytest markerini e'lon qilish. `--strict-markers` ostida e'lon qilinmagan marker **yig'ilishda** yiqiladi.
- [ ] **W0-11** — `compose.yaml` ga `cv-service` + `self_check.EXPECTED_COMPONENTS` ga `cv_detect`. `SENTRY_DSN` berilishi bilan `test_sentry_processes.py` **avtomatik** talab qo'yadi (4-fazadagi hosila darvoza).
- [ ] **W0-12** — ONNX artefaktini image'ga `COPY` bilan olib kirish (yuklab olish emas, D-24).
- [ ] **W0-13** — ⚠ `npm run gate` byudjetini **tinch xostda uch marta** o'lchash va 900 s ni qayta belgilash (D-26).
- [ ] **W0-14** — ⚠ `scripts/check-validation-signoff.mjs::DEFAULT_FILE` ni fazadan mustaqil qilish (D-27) — hozir 2-fazaga qadalgan.

🔇 = jimgina yiqiladigan (testlar yashil, ishlab chiqarish buzilgan)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Owner | Trigger |
|----------|-------------|------------|-------|---------|
| **Modelning aniqligi** — RF-DETR ning verdikti qanchalik to'g'ri | AI-02, AI-04 | **Haqiqat yo'q.** Oltin to'plam bo'sh; sintetik detektsiyalar mexanikani isbotlaydi, **modelni emas**. Darvoza uxlab yotadi va real kadrlar kelganda o'zi uyg'onadi | Nazoratchi (yorliqlaydi) + ijrochi (o'lchaydi) | Phase 0 ning real kadrlari kelganda |
| RF-DETR ning COCO sinflari **o'zbek bozori mollarida umuman ishlaydimi** | AI-02 | Fazaning eng katta qoldiq xavfi, hamma joyda LOW confidence. `occupancy_events.model_version` `timm` klassifikatoriga raqobatlashuvchi verdikt yozish imkonini beradi | Nazoratchi | Birinchi real kadrlar to'plamida |
| Ko'r auditning **amaliy** xolisligi | AI-04 | Strukturaviy himoyalar (urug', payloadda yo'qlik, `CHECK`, immutabillik, 70/30) testlanadi; **nazoratchi haqiqatan langarlanmaganini** faqat real ish jarayoni ko'rsatadi | Nazoratchi + direktor | Pilot tayyorgarligi haftasi |
| Poligon chizishning **amalda bajariladiganligi** 300–1000 rasta uchun | AI-01 | UI-SPEC uch yordamchi bilan 2–5 soatni 0.5–1 soatga tushirishni **hisoblab** chiqdi; haqiqiy vaqt faqat real bozor chizmasida o'lchanadi | Bozor admini | Karmana chizmasi kelganda |
| Nazoratchining kunlik 30 bandlik byudjeti realmi | AI-03, AI-04 | Charchash va tezlik — inson o'lchovi | Nazoratchi | Pilotning birinchi haftasi |

> Bu bandlar **fazani bloklamaydi** (self-service direktivasi). `nyquist_compliant` ularning bajarilganini emas, **shaklini** tekshiradigan skript bilan hisoblanadi.

---

## Validation Sign-Off

- [ ] Har taskda `<automated>` verify yoki Wave 0 bog'liqligi bor
- [ ] Namuna uzluksizligi: ketma-ket 3 taskda avtomatik verify yo'qligi holati yo'q
- [ ] Wave 0 ning 14 bandi qoplangan; **W0-2, W0-3 va W0-6 birinchi migratsiyadan oldin**
- [ ] Zona mantig'i sintetik `sv.Detections` bilan **darvoza**, konventsiya emas (W0-7)
- [ ] Oltin to'plam darvozasi mavjud, **uxlab yotadi** va real ma'lumot kelganda kodsiz uyg'onadi (W0-9)
- [ ] Ko'r auditning beshala strukturaviy himoyasi testlangan (D-17)
- [ ] `gate` byudjeti **tinch xostda** uch o'lchov asosida qayta belgilandi (W0-13)
- [ ] `nyquist_compliant: true` skript bilan **hisoblangan**, qo'lda yozilmagan
- [ ] ⚠ **Aniqlik da'vosi hech qayerda o'lchanmagan holda yozilmagan**

**Approval:** pending
