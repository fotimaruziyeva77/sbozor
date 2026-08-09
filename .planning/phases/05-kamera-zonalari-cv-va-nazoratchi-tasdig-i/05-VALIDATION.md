---
phase: 5
slug: kamera-zonalari-cv-va-nazoratchi-tasdig-i
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-08-05
measured: 2026-08-10
updated: 2026-08-10
human_only_verifications:
  - item: Detektorning aniqligi — verdikt qanchalik to'g'ri
    why_not_automatable: Haqiqat yo'q. Oltin to'plam bo'sh, real Karmana kadri olinmagan. Sintetik sv.Detections geometrik fakt bo'yicha yasaladi va kutilayotgan verdiktni umuman bilmaydi — u zona mantig'ini isbotlaydi, modelni emas. Darvoza qurilgan va uxlab yotadi (W0-9)
    owner: Nazoratchi (yorliqlaydi) + ijrochi (o'lchaydi)
    trigger: Phase 0 ning real kadrlari kelganda — 06:00 va 18:00 slotlari majburiy
  - item: RF-DETR ning COCO sinflari o'zbek bozori mollarida umuman ishlaydimi
    why_not_automatable: Fazaning eng katta qoldiq xavfi. Sintetik detektsiya bu savolni umuman bermaydi — u sinf nomini tanlab beradi. Javob faqat real kadrlarda ko'rinadi
    owner: Nazoratchi
    trigger: Birinchi real kadrlar to'plamida
  - item: Ko'r auditning amaliy xolisligi
    why_not_automatable: Strukturaviy himoyalar (hosila urug', payloadda maydonning umuman yo'qligi, CHECK, o'zgarmaslik, 70/30 kvota) testlangan; nazoratchining haqiqatan langarlanmaganini faqat real ish jarayoni ko'rsatadi va buni birorta test o'lchay olmaydi
    owner: Nazoratchi + direktor
    trigger: Pilot tayyorgarligi haftasi
  - item: Poligon chizishning amalda bajariladiganligi 300-1000 rasta uchun
    why_not_automatable: UI-SPEC uch yordamchi bilan 2-5 soatni 0.5-1 soatga tushirishni hisoblab chiqdi; haqiqiy vaqt faqat real bozor chizmasida, real kadrda va real admin bilan o'lchanadi
    owner: Bozor admini
    trigger: Karmana chizmasi kelganda
  - item: Nazoratchining kunlik 30 bandlik byudjeti realmi
    why_not_automatable: Charchash va tezlik — inson o'lchovi. Byudjetning MEXANIZMI o'lchangan (409 review_budget_exhausted, navbat bo'shligidan ajratilgan kod), o'lchanmagani — QIYMATNING o'zi
    owner: Nazoratchi
    trigger: Pilotning birinchi haftasi
automated_replacements:
  - was: Real ONNX artefakti bilan detektorni ishga tushirib zona verdiktini kutish
    now: docker compose --profile test run --rm cv-tests pytest -q — xom tenzor arifmetikasi (test_rfdetr_postprocess.py) va 0..1 <-> piksel zona verdicti (test_zone_verdict.py) sintetik sv.Detections ustida, GEOMETRIK FAKT bo'yicha nomlangan fixture bilan (W0-7)
  - was: Nazoratchi ekranini brauzerda ochib ko'r payloadda AI javobi yo'qligini ko'rish
    now: docker compose --profile test run --rm tests pytest tests/integration/test_blind_audit.py -q && node --test frontend/scripts/blind-payload.test.mjs — server tomonda maydonning UMUMAN e'lon qilinmagani, klient tomonda z.strictObject va katalog skani (G-12/G-13/G-14)
  - was: Kunni haqiqatan tugatib javobsiz noaniqning bo'shga aylanishini kutish
    now: docker compose --profile test run --rm tests pytest tests/integration/test_day_close.py -q — day_close(business_date=...) argument sifatida vaqtni oladi, ya'ni kun soat holatiga bog'liq emas
  - was: Bir rastani ikki kamerada band qilib qo'yib agregatsiyani ko'zdan kechirish
    now: docker compose --profile test run --rm tests pytest tests/unit/test_aggregate_stall_slot.py -q — 120 holatli jadval sof funksiya ustida; uchidan-uchiga versiyasi test_phase5_criteria.py::test_sc5_ da haqiqiy Postgres bilan
  - was: Bir yil kutib nazoratchining o'zi bilan mosligini kuzatish (D-16)
    now: O'RNI BOSILMADI VA BU OCHIQ AYTILADI — D-16 bugungi sxemada strukturaviy ravishda ifodalab bo'lmaydi (audit_draw har hodisani eng ko'pi bilan bir marta tortadi). Qator UI-SPEC 11.6 dan OLIB TASHLANDI va i18n kaliti YOZILMADI
  - was: Ko'r audit tortishida odam qaysi bandni tanlaganini tekshirish
    now: docker compose --profile test run --rm tests pytest tests/integration/test_blind_audit.py -q — namuna Python da MUSTAQIL qayta hisoblanadi va bazadagi to'plamga teng bo'lishi talab qilinadi; mahsulot kodidan formula import QILINMAYDI
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
| **Quick run command** | `npm run gate:fast` — chegara **180 s** (o'zgarmadi), joriy o'lchov **87 s** |
| **Full suite command** | `npm run gate` — chegara **1250 s** (W0-13 da qayta belgilandi, 900 s dan **KO'TARILDI**; pastga qarang) |
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
- **Maksimal kechikish:** bir to'lqin (`gate` 1250 s chegarasi ichida)

### `gate` byudjeti — 4-fazadan meros ochiq band (D-26) — ✅ **YOPILDI 2026-08-10 (`05-15`)**

4-faza chegarani **900 s** ga tushirdi, keyin `04-14` uni **1009 s va 1174 s** bo'lib o'tganini o'lchadi va **chegarani ko'tarmadi**. Sababni `04-VERIFICATION` nomladi: xostda **ikkinchi to'liq Docker steki** ishlab turgan (7 ta `parnikkpi-*` konteyner). Nazorat: `gate:fast` ayni bir xil ish ustida **68 s → 129 s**.

**W0-13 ning talabi:** o'lchov **tinch xostda** va **`cv-service` build'i qo'shilgandan keyin** uch marta olinadi. Chegara = eng yomon + 20 %.

#### O'LCHOV SHARTI — u natijaning bir qismi va shuning uchun BIRINCHI yoziladi

| Shart | Holat (2026-08-10, o'lchovdan OLDIN) |
|---|---|
| Boshqa Docker steki | ⚠ **BOR EDI: 6 ta `parnikkpi-*` konteyner** (`bot`, `celery_worker`, `frontend`, `backend`, `db`, `redis`) — aynan `04-14` ni ifloslantirgan stek, 19 soatdan beri ishlab turgan |
| Ko'rilgan chora | ✅ **`docker stop` bilan TO'XTATILDI**, o'lchovdan keyin `docker start` bilan **tiklandi**. Ular `restart=unless-stopped` bilan ishlaydi, ya'ni qo'lda to'xtatish ularni to'xtoq holatda ushlab turadi va tiklash izsiz |
| ⇒ **Tinch xost** | ✅ **TA'MINLANDI.** Uchala o'lchov ham `docker ps` da faqat `sbozor-*` (5 ta) ko'rinib turgan holatda olindi |
| Docker disk holati | `Images 12.35 GB` (17 ta, 13 faol) · `Build Cache 4.48 GB` · `Local Volumes 875 MB`. **Sovuq/issiq farqi shu bilan izohlanadi** |
| Xost diski | ⚠ **`C:` 91 % to'la (147/162 GB, bo'sh 15 GB)** — Docker Desktop VHDX aynan shu diskda. Bu loyihada ilgari 1.85× sekinlashuv aynan shundan kelib chiqqan; bugungi o'lchovlar bir-biriga juda yaqin chiqqani (tarqoqlik 2.6 %) shu holatning **barqaror** ekanini ko'rsatadi, LEKIN u kelajakdagi o'lchovlar uchun xavf bo'lib qoladi. `E:` da 115 GB bo'sh |

#### UCH O'LCHOV — o'rtachaga AYLANTIRILMAGAN, uchalasi ham alohida

| # | Yugurish | `real` | Soniya | Natija |
|---|---|---|---|---|
| 1 | `npm run gate` — **sovuq** (birinchi) | `16m48.9s` | **1009 s** | exit 0 |
| 2 | `npm run gate` — issiq | `16m44.2s` | **1004 s** | exit 0 |
| 3 | `npm run gate` — issiq | `16m22.8s` | **983 s** | exit 0 |

**Eng yomoni: 1009 s. Eng yaxshisi: 983 s. Tarqoqlik: 26 s** — eng yomonning **2,6 %** i.

⚠ **Sovuq/issiq farqi deyarli YO'Q (1009 → 983, −2,6 %)** va bu ma'noli: zanjirning og'irligi Docker build'ida emas, **testlarning O'ZIDA**. Ya'ni byudjetni tushirishning yagona yo'li — testlarni tezlashtirish yoki ularni bo'lish; kesh isitish yordam bermaydi.

#### NAZORAT O'LCHOVI — `gate:fast`, o'zgarmagan ish hajmi

| Qachon | `gate:fast` | Izoh |
|---|---|---|
| 4-fazaning TOZA bazasi (`04-12`) | **68 s** | — |
| 4-fazaning IFLOSLANGAN seansi (`04-14` oxiri) | **129 s** | ⚠ ish hajmi O'ZGARMAGAN — degradatsiya xostdan |
| **Bugun, tinch xostda (`05-15`)** | **87 s** | ✅ chegara **180 s** — 48 % zaxira |

⚠ **87 s ni 129 s bilan ADASHTIRMASLIK KERAK va farq mexanik.** 129 s **o'zgarmagan** ish hajmida olingan edi, 87 s esa **o'sgan** ish hajmida: `gate:fast` = `test:fast` (unit testlar) + `frontend test` (vitest **494 → 620** + `node --test` 144). Ya'ni bugungi 87 s ifloslanish emas, **to'plamning o'sishi**.

#### YANGI CHEGARA

**1009 s (eng yomon) × 1,20 = 1210,7 s → 50 ga yuqoriga yaxlitlandi → `gate` byudjeti = 1250 s.**

⚠ Yaxlitlash qoidasi 4-fazanikining **aynan o'zi** (o'sha yerda 745 × 1,20 = 894 → **900**), ya'ni qoida bu yerda **o'ylab topilmadi**, qayta ishlatildi.

⛔ **CHEGARA KO'TARILDI — 900 s → 1250 s — VA BU JIMGINA QILINMADI.** 4-faza uni ko'tarmagan edi, chunki o'lchov ifloslangan edi va ifloslangan o'lchov bilan chegara bo'shatilsa darvoza mazmunsiz bo'lardi. Bugun sabab **boshqa va u o'lchangan**: zanjirga `cv-service` ning **ikkita yangi bosqichi** (`cv:lint` + `cv:test`) qo'shildi (05-02, W0-2) va `tests` to'plami bu fazada sezilarli o'sdi. Ya'ni +39 % **ish hajmining o'sishi**, xost degradatsiyasi emas — va buni tinch xostdagi uch o'lchovning bir-biriga yaqinligi tasdiqlaydi.

⚠ **Chegara `package.json` da ham yozilgan** (`"//gate-budget"` kaliti, `gate` yorlig'ining YONIDA) va ikkala joydagi son **bir xil: 1250 s**. `"//"` bilan boshlanadigan kalit — npm ning izoh konventsiyasi: u ishga tushirilmaydi va zanjirga kirmaydi.

⚠ **`gate:fast` chegarasi 180 s da QOLDI.**

#### TO'RTINCHI YUGURISH — chegara asosiga KIRMAYDI, lekin yozib qo'yiladi

Faza yopilishining yakuniy tekshiruvi `parnikkpi` steki **TIKLANGANDAN
KEYIN** bajarildi (ya'ni xost yana ikki steklik): `npm run gate` →
**exit 0, 1015 s** (`16m54.7s`).

⚠ **Bu son chegarani BELGILAMAYDI** — chegara ATAYIN faqat tinch
xostdagi uch o'lchovdan chiqadi. U bu yerda BOSHQA savolga javob
beradi va javob qiziq: ikkinchi stek tiklangach farq **+0,6 %**
(1009 → 1015), holbuki `04-14` da ayni shu stek **+30 %** bergan edi.
Ya'ni 4-fazadagi degradatsiya stekning MAVJUDLIGIDAN emas, o'sha
seansdagi **progressiv** holatdan kelib chiqqan (`gate:fast` ning
68 → 129 s bo'lishi ham shu shaklda edi). Bu farq keyingi o'lchovchi
uchun yozib qo'yiladi: «boshqa stek bor» yolg'iz o'zi hali
ifloslanish DEMAKMAS — nazorat o'lchovi (`gate:fast`) shart.

---

## Per-Task Verification Map

*Har PLAN.md taski uchun bitta qator. **15 reja × 3 task = 45 qator.** `Threat Ref` — o'sha rejaning `<threat_model>` bloki (to'liq ro'yxat reja faylida).*

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 05-01/T1 | 05-01 | 1 | AI-02, AI-04 | T-05-01/02/04 | Reyestrlar, `PENDING_AUDIT_TRIGGERS` qulfi va ikki yangi ma… | avtomatik | `docker compose --profile test run --rm tests pytest tests/tenancy/test_meta.py tests/unit -q` | mavjud | ✅ green |
| 05-01/T2 | 05-01 | 1 | AI-02, AI-04 | T-05-01/02/04 | W0-3 — ko'r audit urug'ining zondi (`sha256(bytea)`, kengay… | avtomatik | `docker compose --profile test run --rm tests pytest tests/tenancy/test_audit_seed_probe.py -q` | mavjud | ✅ green |
| 05-01/T3 | 05-01 | 1 | AI-02, AI-04 | T-05-01/02/04 | W0-9 — oltin to'plam skeleti va UXLAB YOTADIGAN aniqlik dar… | avtomatik | `docker compose --profile test run --rm tests pytest tests/unit/test_golden_harness.py -m golden -q` | mavjud | ✅ green |
| 05-02/T1 | 05-02 | 1 | AI-02 | T-05-SC/05/06/07 | Litsenziya devori — uch qatlam, manifestdan OLDIN (W0-1, D-… | avtomatik | `docker compose --profile test run --rm tests pytest tests/unit/test_license_fence.py -q` | mavjud | ✅ green |
| 05-02/T2 | 05-02 | 1 | AI-02 | T-05-SC/05/06/07 | `cv-service` — ikkinchi bog'liqlik to'plami, image va minim… | avtomatik | `docker compose --profile test run --rm tests pytest tests/unit/test_license_fence.py tests/unit/test_sentry…` | mavjud | ✅ green |
| 05-02/T3 | 05-02 | 1 | AI-02 | T-05-SC/05/06/07 | W0-7 — `sv.Detections` konstruktori, GEOMETRIK FAKT bo'yich… | avtomatik | `docker compose --profile test run --rm cv-tests pytest tests/unit/test_detection_fixtures.py -q` | mavjud | ✅ green |
| 05-03/T1 | 05-03 | 1 | AI-01, AI-04 | T-05-09/10/11 | `lib/zone-geometry.ts` — 11 sof funksiya + G-19 darvozasi (… | avtomatik | `npm --prefix frontend run test:component` | mavjud | ✅ green |
| 05-03/T2 | 05-03 | 1 | AI-01, AI-04 | T-05-09/10/11 | `lib/wilson.ts` — Wilson score oralig'i (W0-F3) | avtomatik | `npm --prefix frontend run test:component` | mavjud | ✅ green |
| 05-03/T3 | 05-03 | 1 | AI-01, AI-04 | T-05-09/10/11 | `blind-payload.test.mjs` — G-12 va G-14 (W0-F4, D-17.2/3/4) | avtomatik | `npm --prefix frontend run test:unit` | mavjud | ✅ green |
| 05-04/T1 | 05-04 | 1 | AI-01, AI-03, AI-04, AI-06 | T-05-13/14/15 | Oltinchi xato reyestri — backend, frontend ko'zgusi va uch til | avtomatik | `docker compose --profile test run --rm tests pytest tests/unit -q && npm --prefix frontend run i18n:check` | mavjud | ✅ green |
| 05-04/T2 | 05-04 | 1 | AI-01, AI-03, AI-04, AI-06 | T-05-13/14/15 | Navigatsiya — ikkita yozuv va RBAC tasdig'i (W0-F1, W0-F5) | avtomatik | `npm --prefix frontend run test:component && npm --prefix frontend run typecheck` | mavjud | ✅ green |
| 05-04/T3 | 05-04 | 1 | AI-01, AI-03, AI-04, AI-06 | T-05-13/14/15 | Uch copy darvozasi + parity kengaytmasi + D-27 (G-11, G-15,… | avtomatik | `npm --prefix frontend run test:unit && node scripts/check-validation-signoff.mjs .planning/phases/05-kamera…` | mavjud | ✅ green |
| 05-05/T1 | 05-05 | 2 | AI-01, AI-02, AI-04, AI-05, AI-06 | T-05-17/18/19/20 | Enumlar va olti model (`models/occupancy.py`) | avtomatik | `docker compose --profile test run --rm tests pytest tests/unit/test_enums.py -q && docker compose --profile…` | mavjud | ✅ green |
| 05-05/T2 | 05-05 | 2 | AI-01, AI-02, AI-04, AI-05, AI-06 | T-05-17/18/19/20 | Ikki o'zgarmaslik qo'riqchisi va `0018_occupancy_domain` | avtomatik | `docker compose --profile migrate run --rm migrate alembic upgrade head && docker compose --profile test run…` | mavjud | ✅ green |
| 05-05/T3 | 05-05 | 2 | AI-01, AI-02, AI-04, AI-05, AI-06 | T-05-17/18/19/20 | `0019` kaskad, seed fixture va uchta xulq darvozasi | avtomatik | `docker compose --profile test run --rm tests pytest tests/integration/test_occupancy_immutable.py tests/int…` | mavjud | ✅ green |
| 05-06/T1 | 05-06 | 3 | AI-01 | T-05-23/24/25 | `app/services/zone_geometry.py` — V5 validatsiyasi sof funk… | avtomatik | `docker compose --profile test run --rm tests pytest tests/unit/test_zone_geometry.py -q` | mavjud | ✅ green |
| 05-06/T2 | 05-06 | 3 | AI-01 | T-05-23/24/25 | `camera_zone_repo.py` — versiyalash va qamrov (D-07, D-22) | avtomatik | `docker compose --profile test run --rm tests pytest tests/integration/test_camera_zones_api.py -q` | mavjud | ✅ green |
| 05-06/T3 | 05-06 | 3 | AI-01 | T-05-23/24/25 | `app/api/v1/camera_zones.py` — marshrutlar, RBAC va darvoza | avtomatik | `docker compose --profile test run --rm tests pytest tests/integration/test_camera_zones_api.py tests/tenanc…` | mavjud | ✅ green |
| 05-07/T1 | 05-07 | 3 | AI-02 | T-05-28/29/31 | `detector/postprocess.py` — xom tenzor arifmetikasi (§4.3) | avtomatik | `docker compose --profile test run --rm cv-tests pytest tests/unit/test_rfdetr_postprocess.py -q` | mavjud | ✅ green |
| 05-07/T2 | 05-07 | 3 | AI-02 | T-05-28/29/31 | `detector/zones.py` — 0..1 ↔ piksel va zona verdicti (D-09,… | avtomatik | `docker compose --profile test run --rm cv-tests pytest tests/unit/test_zone_verdict.py -q` | mavjud | ✅ green |
| 05-07/T3 | 05-07 | 3 | AI-02 | T-05-28/29/31 | `detector/session.py` + `annotate.py` — ONNX sessiya va dal… | avtomatik | `docker compose --profile test run --rm cv-tests pytest tests/unit/test_detector_has_no_stub.py -q` | mavjud | ✅ green |
| 05-08/T1 | 05-08 | 4 | AI-02 | T-05-33/34/35 | Tor ombor klienti va tenant kontekstli sessiya | avtomatik | `docker compose --profile test run --rm cv-tests pytest tests/unit/test_storage_surface.py -q` | mavjud | ✅ green |
| 05-08/T2 | 05-08 | 4 | AI-02 | T-05-33/34/35 | `jobs/detect.py` — orkestratsiya, idempotentlik va yurak ur… | avtomatik | `docker compose --profile test run --rm cv-tests pytest tests/integration/test_detect_job.py -q` | mavjud | ✅ green |
| 05-08/T3 | 05-08 | 4 | AI-02 | T-05-33/34/35 | Cross-servis enqueue va sifat filtri | avtomatik | `docker compose --profile test run --rm tests pytest tests/integration/test_capture_enqueues_detect.py -q` | mavjud | ✅ green |
| 05-09/T1 | 05-09 | 4 | AI-01 | T-05-39/40/41 | Kesh kalitlari, sxemalar, sahifa qobig'i va qamrov kartasi | avtomatik | `npm --prefix frontend run test:component && npm --prefix frontend run i18n:check && npm --prefix frontend r…` | mavjud | ✅ green |
| 05-09/T2 | 05-09 | 4 | AI-01 | T-05-39/40/41 | SVG yuzasi va RO'YXAT yuzasi — chizish, sudrash va klaviatura | avtomatik | `npm --prefix frontend run test:component` | mavjud | ✅ green |
| 05-09/T3 | 05-09 | 4 | AI-01 | T-05-39/40/41 | Asboblar, DL-1/DL-2 dialoglari va 300–1000 rasta uchun yord… | avtomatik + qo'lda | `npm --prefix frontend run test:component && node --test frontend/scripts/zone-copy.test.mjs` | mavjud | ✅ green |
| 05-10/T1 | 05-10 | 5 | AI-03 | T-05-43/44/45 | `review_repo.py` — qulflab olish, byudjet va ustuvorlik | avtomatik | `docker compose --profile test run --rm tests pytest tests/integration/test_uncertain_queue.py -q` | mavjud | ✅ green |
| 05-10/T2 | 05-10 | 5 | AI-03 | T-05-43/44/45 | `app/api/v1/reviews.py` — bitta so'rov = bitta qaror (D-18) | avtomatik | `docker compose --profile test run --rm tests pytest tests/integration/test_uncertain_queue.py tests/tenancy…` | mavjud | ✅ green |
| 05-10/T3 | 05-10 | 5 | AI-03 | T-05-43/44/45 | SC#3 darvozalari — OpenAPI skani, byudjet va ustuvorlik | avtomatik | `docker compose --profile test run --rm tests pytest tests/integration/test_uncertain_queue.py -q` | mavjud | ✅ green |
| 05-11/T1 | 05-11 | 6 | AI-04 | T-05-49/50/51 | `jobs/audit_draw.py` — hosila urug', muzlatilgan doira, 70/… | avtomatik | `docker compose --profile test run --rm tests pytest tests/integration/test_blind_audit.py -q` | mavjud | ✅ green |
| 05-11/T2 | 05-11 | 6 | AI-04 | T-05-49/50/51 | Ko'r serializer — maydonning UMUMAN yo'qligi (D-17.2) | avtomatik | `docker compose --profile test run --rm tests pytest tests/integration/test_blind_audit.py -q` | mavjud | ✅ green |
| 05-11/T3 | 05-11 | 6 | AI-04 | T-05-49/50/51 | SC#4 darvozasi — oltita invariant | avtomatik | `docker compose --profile test run --rm tests pytest tests/integration/test_blind_audit.py -q` | mavjud | ✅ green |
| 05-12/T1 | 05-12 | 7 | AI-04, AI-05, AI-06 | T-05-55/56/57 | `sbozor_core/occupancy.py` — kameralararo agregatsiya (AI-0… | avtomatik | `docker compose --profile test run --rm tests pytest tests/unit/test_aggregate_stall_slot.py -q` | mavjud | ✅ green |
| 05-12/T2 | 05-12 | 7 | AI-04, AI-05, AI-06 | T-05-55/56/57 | `jobs/day_close.py` — materializatsiya va `default_empty` (… | avtomatik | `docker compose --profile test run --rm tests pytest tests/integration/test_day_close.py -q` | mavjud | ✅ green |
| 05-12/T3 | 05-12 | 7 | AI-04, AI-05, AI-06 | T-05-55/56/57 | Aniqlik hisoboti, `/occupancy` API va oltin to'plamning ula… | avtomatik | `docker compose --profile test run --rm tests pytest tests/unit/test_accuracy_report.py -q && docker compose…` | mavjud | ✅ green |
| 05-13/T1 | 05-13 | 7 | AI-03, AI-04 | T-05-61/62/63 | Ikki ALOHIDA so'rov moduli, `z.strictObject` sxemasi va `/r… | avtomatik | `npm --prefix frontend run test:component && node --test frontend/scripts/blind-payload.test.mjs && npm --pr…` | mavjud | ✅ green |
| 05-13/T2 | 05-13 | 7 | AI-03, AI-04 | T-05-61/62/63 | Y-2 sessiyasi — bitta band, dalil darvozasi, byudjet hisobl… | avtomatik | `npm --prefix frontend run test:component` | mavjud | ✅ green |
| 05-13/T3 | 05-13 | 7 | AI-03, AI-04 | T-05-61/62/63 | Y-3 ko'r sessiya — uch kanal, oshkor paneli va G-13/G-14 | avtomatik + qo'lda | `npm --prefix frontend run test:component && node --test frontend/scripts/blind-payload.test.mjs` | mavjud | ✅ green |
| 05-14/T1 | 05-14 | 8 | AI-04, AI-05, AI-06 | T-05-67/68/69 | So'rovlar, sahifa qobig'i va BESH hisoblagich | avtomatik | `npm --prefix frontend run test:component && node --test frontend/scripts/zone-copy.test.mjs` | mavjud | ✅ green |
| 05-14/T2 | 05-14 | 8 | AI-04, AI-05, AI-06 | T-05-67/68/69 | Chalkashlik matritsasi va namuna holati | avtomatik | `npm --prefix frontend run test:component` | mavjud | ✅ green |
| 05-14/T3 | 05-14 | 8 | AI-04, AI-05, AI-06 | T-05-67/68/69 | Rastalar ro'yxati, DL-5 va matn | avtomatik + qo'lda | `npm --prefix frontend test && npm --prefix frontend run i18n:check && npm --prefix frontend run build` | mavjud | ✅ green |
| 05-15/T1 | 05-15 | 9 | AI-01, AI-02, AI-03, AI-04, AI-05, AI-06 | T-05-73/74/75 | `test_phase5_criteria.py` — beshta mezon, meta-test va soxt… | avtomatik | `docker compose --profile test run --rm tests pytest tests/integration/test_phase5_criteria.py -q` | mavjud | ✅ green |
| 05-15/T2 | 05-15 | 9 | AI-01, AI-02, AI-03, AI-04, AI-05, AI-06 | T-05-73/74/75 | W0-13 — `gate` byudjetini TINCH XOSTDA uch marta o'lchash (… | avtomatik + qo'lda | `node -e "const p=require('./package.json'); if(!/cv:test/.test(p.scripts.gate)) { console.error('gate zanji…` | mavjud | ✅ green |
| 05-15/T3 | 05-15 | 9 | AI-01, AI-02, AI-03, AI-04, AI-05, AI-06 | T-05-73/74/75 | `05-HUMAN-UAT.md`, validatsiya imzosi va talablarni belgilash | avtomatik + qo'lda | `npm run validation:check && npm run requirements:check` | mavjud | ✅ green |

---

## Wave 0 Requirements

`05-PATTERNS.md` §5 o'n to'rt bandni sanaydi. **Uchtasi migratsiyadan oldin hal qilinishi shart** — keyin aniqlash qayta migratsiya demakdir:

- [x] **W0-1** (05-02/T1) — `tests/unit/test_license_fence.py`: `rfdetr-plus` / `LicenseRef-*` / AGPL darvozasi. **D-03 — litsenziya endi lockfile invarianti.** Keyin qo'shilsa `uv add rfdetr` allaqachon `torch` ni tortgan bo'lardi.
- [x] **W0-2** — ⚠ **QAROR QULFLANDI (05-02/T2):** `cv-service` **o'z `pyproject.toml` + `uv.lock` + `Dockerfile`** i bilan keladi; testlari `services/cv-service/tests/` da va **yangi `cv-tests` konteynerida** yuradi (`cv-service` Dockerfile'ining `dev` target'i qayta ishlatiladi — `tests` ↔ `core-api` naqshining aynan takrori). Rad etilgan muqobil: CV kutubxonalarini `core-api` dev guruhiga olib kirish — `test_runtime_deps.py:91-94` `opencv-python-headless` ni **ikkala guruhda ham** taqiqlaydi va bu o'lchangan darvoza.
- [x] **W0-3** — ⚠ **QAROR QULFLANDI (05-01/T2):** yadro **`sha256(bytea)`** — yangi kengaytma **YO'Q**, `require_extension()` chaqirilmaydi. Qaror fikr emas, **o'lchov**: `tests/fixtures/audit_seed_probe.py` + `tests/tenancy/test_audit_seed_probe.py` uni HAQIQIY `postgres:18.4` da o'lchaydi (`billable_probe.py` naqshi) va `0018` ning migratsiyasi `pgcrypto`siz bazada o'tishi bilan **xulqiy** tasdiqlanadi.
- [x] **W0-4** (05-01/T1) — `OCCUPANCY_TENANT_TABLES` + `_AUDITED_` + `_DELETE_ORDER` reyestrlari. Reyestr **migratsiyadan oldin** yoziladi va meta-test vaqtincha qizil turadi — bu **kutilgan** (1-fazadagi `FINANCIAL_TABLES` naqshi).
- [x] **W0-5** (05-01/T1) — `AUDITED_TABLES` ga `camera_zones`, `zone_reviews`.
- [x] **W0-6** — 🔇 `market_delete_draft()` kaskadi. **IKKI BOSQICH va bu ataylab:** reyestr (`OCCUPANCY_DELETE_ORDER`) **05-01/T1** da — ya'ni migratsiyadan OLDIN, `SNAPSHOT_DELETE_ORDER` naqshi bo'yicha; funksiya tanasi + `0019` esa **05-05/T3** da, `0018` bilan **bir to'lqinda** (04-03 ning `0014`+`0015` juftligi shakli). `pg_catalog` to'liqlik darvozasi `0018` dan keyin qizaradi va `0019` uni yopadi.
- [x] **W0-7** (05-02/T3) — `tests/fixtures/detections.py`: `sv.Detections` konstruktori, **geometrik fakt bo'yicha** nomlangan (`box_center_in_polygon`), hech qachon kutilgan verdikt bo'yicha emas — aks holda test o'z farazini tasdiqlaydi (4-fazadagi `frame_mean_8_stddev_2` naqshi).
- [x] **W0-8** — `frontend/src/lib/zone-geometry.ts` + `zone-geometry.**test.tsx**` (**05-03/T1**). ⚠ **`.ts` test fayli `vitest` tomonidan JIMGINA o'tkazib yuboriladi** (`vitest.config.ts:34`). ⚠ UI-SPEC va RESEARCH `scripts/zone-geometry.test.mjs` ni taklif qiladi — u **bajarilmaydi** (M-3: `node --test` TS import qila olmaydi); §S-13 ning **A yo'li** tanlandi.
- [x] **W0-9** (05-01/T3) — `tests/fixtures/golden_set/` skeleti + `manifest.jsonl` sxemasi + `scripts/eval-golden-set.py`. **Uxlab yotadigan darvoza:** `source='karmana'` qatorlari paydo bo'lgan kuni **kodsiz o'zi uyg'onadi**.
- [x] **W0-10** (05-01/T1) — `golden` pytest markerini e'lon qilish. `--strict-markers` ostida e'lon qilinmagan marker **yig'ilishda** yiqiladi.
- [x] **W0-11** — `compose.yaml` ga `cv-service` **va** `cv-tests` + `self_check.EXPECTED_COMPONENTS` ga `cv_detect` (**05-02/T2**). `SENTRY_DSN` berilishi bilan `test_sentry_processes.py` **avtomatik** talab qo'yadi, shuning uchun minimal `app/main.py` + `app/worker.py` (`init_sentry`) **o'sha taskda** tug'iladi. `cv_detect` bugun `never_seen` bo'ladi va `/internal/self-check` ni **buzmaydi** (`healthy = not stale and bool(seen)` — `backup` bilan aynan bir xil holat).
- [x] **W0-12** (05-02/T1+T2) — ONNX artefaktini image'ga `COPY` bilan olib kirish (yuklab olish emas, D-24).
- [x] **W0-13** — ⚠ `npm run gate` byudjetini **tinch xostda uch marta** o'lchash va 900 s ni qayta belgilash (D-26). ⚠ **YAGONA WAVE-0 BANDI KI OXIRIDA BAJARILADI (05-15/T2) va sabab ordinal:** o'lchovning sharti — zanjirda `cv-service` build'ining **mavjudligi**, u esa Wave 0 ning O'ZIDA (05-02) tug'iladi. Ya'ni bandni Wave 0 da bajarish shartni buzardi. Protokol (tinch xost tekshiruvi, uch o'lchov + `gate:fast` nazorati, chegara = eng yomon + 20 %) shu yerda va 05-15 da yozilgan.
- [x] **W0-14** — ⚠ `scripts/check-validation-signoff.mjs::DEFAULT_FILE` ni fazadan mustaqil qilish (D-27, **05-04/T3**) — hozir 2-fazaga qadalgan. Topilmasa `exit 1`; tanlangan fayl yo'li **chop etiladi**.

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

- [x] Har taskda `<automated>` verify yoki Wave 0 bog'liqligi bor — 45/45 qatorda buyruq bor (`node scripts/check-validation-signoff.mjs` mexanik tekshiradi)
- [x] Namuna uzluksizligi: ketma-ket 3 taskda avtomatik verify yo'qligi holati yo'q
- [x] Wave 0 ning **14 bandi** qoplangan; **W0-2, W0-3 va W0-6 birinchi migratsiyadan oldin** (05-01/05-02, `0018` esa 05-05 da). ⚠ **W0-13 — YAGONA oxirida bajarilgan band va sabab ORDINAL:** uning sharti zanjirda `cv-service` build'ining MAVJUDLIGI, u esa Wave 0 ning O'ZIDA (05-02) tug'iladi
- [x] Zona mantig'i sintetik `sv.Detections` bilan **darvoza**, konventsiya emas (W0-7) — `cv-tests::test_detection_fixtures.py`, fixture'lar GEOMETRIK FAKT bo'yicha nomlangan
- [x] Oltin to'plam darvozasi mavjud, **uxlab yotadi** va real ma'lumot kelganda kodsiz uyg'onadi (W0-9) — `tests/unit/test_golden_harness.py -m golden`
- [x] Ko'r auditning beshala strukturaviy himoyasi testlangan (D-17) — hosila urug', muzlatilgan doira, payloadda maydonning UMUMAN yo'qligi, javobning qulflanishi, 70/30 kvota tortish paytida (`test_blind_audit.py`, `test_phase5_criteria.py::test_sc4_*`)
- [x] `gate` byudjeti **tinch xostda** uch o'lchov asosida qayta belgilandi (W0-13) — 900 s → **1250 s**, o'lchov sharti yuqorida
- [x] `nyquist_compliant: true` skript bilan **hisoblangan**, qo'lda yozilmagan — `node scripts/check-validation-signoff.mjs` → «hisob-kitob bilan MOS»
- [x] ⚠ **Aniqlik da'vosi hech qayerda o'lchanmagan holda yozilmagan** — qo'lda halollik ko'rigi bajarildi (natija `05-15-SUMMARY.md` da) va u endi MEXANIK darvoza bilan ham qo'llab-quvvatlanadi: `test_phase5_criteria.py::test_the_criteria_module_claims_no_accuracy_number` mezon modulida `precision`/`recall`/`f1`/`map` nomlarini `ast` daraxtidan taqiqlaydi

⛔ **BU IMZO FAZANI YOPMAYDI.** `ROADMAP.md` dagi Phase 5 belgisi hamon
`- [ ]` va uni belgilash **qayta tekshiruvning** (`/gsd-verify-work`)
qarori — ijrochiniki emas. Bu farq 4-fazada ataylab saqlangan va bu
yerda ham saqlanadi.

⚠ **Bu imzo NIMANI ANGLATMAYDI:** «detektor to'g'ri ishlaydi». Mexanika
qatlami to'liq yashil, **aniqlik qatlami esa MAVJUD EMAS** — oltin
to'plam bo'sh. Ikkalasini aralashtirish bu fazaning bosh taqig'i (D-01)
va u uch marta rad etilgan. Ochiq bandlar `05-HUMAN-UAT.md` da, ega va
tetigi bilan.

**Approval:** ✅ **imzolandi 2026-08-10 (`05-15`)** — 15 reja, 9 to'lqin,
45 task; beshala mezon `tests/integration/test_phase5_criteria.py` da
BITTA buyruq bilan yashil; `npm run gate` exit 0 (983–1009 s, yangi
chegara 1250 s). Rejalashtirish 2026-08-08 da yakunlangan edi.
