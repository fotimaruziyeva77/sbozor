---
phase: 05-kamera-zonalari-cv-va-nazoratchi-tasdig-i
verified: 2026-08-10T04:20:00Z
status: human_needed
score: 5/5 must-haves verified
overrides_applied: 0
re_verification: null
deferred:
  - truth: "DL-5 rasta-slot qatorlari (vaqt · kamera · natija · manba)"
    addressed_in: "Phase 8"
    evidence: "Phase 8 goal: «Direktor raqamlarni o'zi chiqarib oladi» — hisobot detali; `deferred-items.md` #3 da egasi 8-faza deb yozilgan va UI-SPEC §11.7 tuzatilgan"
  - truth: "`fast_decision_ms` chegarasining javobda maydon sifatida bo'lishi"
    addressed_in: "Phase 8"
    evidence: "`deferred-items.md` #4 — egasi 8-faza; UI-SPEC §12.6 tuzatilgan, chegara `accuracy_report.is_fast_decision()` da yashaydi"
  - truth: "`occupancy_day_close_markets()` va `audit_draw_due_markets()` chaqiruvchisiz qolishi"
    addressed_in: "Phase 6"
    evidence: "Phase 6 goal: «Band rasta kun oxirida ... pattaga aylanadi» — billing tiki; `deferred-items.md` #2 da qaror yozilgan"
human_verification:
  - test: "Detektorning aniqligi — real Karmana kadrlarida verdikt qanchalik to'g'ri"
    expected: "Oltin to'plamda `source='karmana'` qatorlari paydo bo'lishi va `-m golden` darvozasining uyg'onishi"
    why_human: "Haqiqat yo'q — oltin to'plamda 0 ta `karmana` qatori (o'lchandi). Sintetik `sv.Detections` zona mantig'ini isbotlaydi, modelni emas (D-01)"
  - test: "RF-DETR ning COCO sinflari o'zbek bozori mollarida ishlaydimi"
    expected: "Birinchi real kadrlar to'plamida sinflarning mazmunli ishlashi"
    why_human: "Fazaning eng katta qoldiq xavfi; sintetik detektsiya bu savolni umuman bermaydi"
  - test: "ONNX artefaktini eksport qilib `ops/models/` ga qo'yish"
    expected: "`pytest -m model` bandi (aynan bitta) yashil bo'lishi"
    why_human: "Ops ishi — GPU ijarasi va eksport retsepti; artefakt repoda yo'q (o'lchandi)"
  - test: "Ko'r auditning amaliy xolisligi"
    expected: "Nazoratchi haqiqatan langarlanmasligi"
    why_human: "Strukturaviy himoyalar o'lchangan; odamning o'zini birorta test o'lchay olmaydi"
  - test: "Poligon chizishning amalda bajariladiganligi (300–1000 rasta)"
    expected: "Uch yordamchi bilan 0.5–1 soat"
    why_human: "Vaqt faqat real bozor chizmasida va real admin bilan o'lchanadi"
  - test: "Nazoratchining kunlik 30 bandlik byudjeti realmi"
    expected: "Charchashsiz bajariladigan hajm"
    why_human: "Byudjetning MEXANIZMI o'lchangan (409 `review_budget_exhausted`), QIYMATNING o'zi emas"
  - test: "D-05 chiqish yo'li: 60 poligonli kamerada `pointermove` > 16 ms mi"
    expected: "Sudrash 16 ms ichida"
    why_human: "Real brauzerdagi render o'lchovi — jsdom buni bermaydi"
  - test: "«Ko'rmasdan tekshirish» atamasining ona tilida ko'rigi (O-01)"
    expected: "Atama nazoratchiga tushunarli"
    why_human: "Til sifati — ona tilida so'zlashuvchi bahosi"
---

# Phase 5: Kamera zonalari, CV va nazoratchi tasdig'i — Verification Report

**Phase Goal:** Tizim har rastaning band/bo'shligini kadrdan aniqlaydi va bu javobning aniqligi halol — noaniq navbatidan emas, ko'r namunadan — o'lchanadi
**Verified:** 2026-08-10T04:20:00Z
**Status:** human_needed
**Re-verification:** Yo'q — birinchi tekshiruv

---

## Bu tekshiruvning qoidasi

`05-VALIDATION.md` ning **ikki qatlam** qoidasi bog'lovchi: mexanika bugun
isbotlanadi, **aniqlik esa isbotlanmaydi** (oltin to'plam bo'sh). Shuning
uchun bu hisobot ikki savolni ALOHIDA beradi:

1. Mexanika haqiqatan ishlaydimi — **kod bilan**, SUMMARY da'vosi bilan emas;
2. Aniqlikning o'lchanmaganligi hamma joyda **ochiq turibdimi** — biror
   summary, test nomi, ekran yoki talab qatori uni o'lchangandek
   ko'rsatmayaptimi.

Ikkinchi savolga javob: **hech qayerda ko'rsatmayapti.** Skan quyida.

---

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Admin kamera kadrida rasta zonalarini poligon qilib chizadi; koordinatalar normalangan (0..1), poligon versiyalangan, bitta rasta bir necha kameraga bog'lanadi | ✓ VERIFIED | `test_phase5_criteria.py::test_sc1_*` — **9 passed** (o'zim yugurtirdim, exit 0). `camera_zones.py` da 4 marshrut (`GET /coverage`, `GET ""`, `PUT ""`, `DELETE`); `zone-editor.tsx` **820 qator**, `zone-canvas.tsx` **432 qator** — stub emas |
| 2 | Har zona band/bo'sh/noaniq bahosini confidence bilan oladi; AI javobi hech qachon tahrirlanmaydi — nazoratchi qarori alohida yozuv | ✓ VERIFIED | `test_sc2_*` yashil. `0018:197` — `trg_occupancy_event_immutable` triggeri; nazoratchi qarori `zone_reviews` da alohida jadval. `detector/` **957 qator** (`session.py` da haqiqiy `ort.InferenceSession`) |
| 3 | Byudjet doirasidagi ustuvorlashtirilgan noaniq navbat; «hammasini tasdiqlash» tugmasi yo'q; javoblar dataset sifatida yig'iladi | ✓ VERIFIED | `test_sc3_*` yashil; `test_uncertain_queue.py::test_no_bulk_approve_endpoint` OpenAPI **sxemasini** skanerlaydi (nom ro'yxatini emas). Klient tomonda `submittedRef` qulfi **ikkala** sessiyada — uchinchi yo'l yo'q (pastga qarang) |
| 4 | Nazoratchi ko'r audit navbatida AI javobini ko'rmasdan baholaydi — aniqlik hisoboti faqat shu namunadan | ✓ VERIFIED | `test_sc4_*` yashil; `test_blind_audit.py` + 3 boshqa fayl birga **91 passed**, exit 0. `accuracy_report.py:396` da IKKI shartli filtr (`purpose == eval AND queue_kind == blind_audit`) va kuchaytirilgan test uni ajratadi |
| 5 | Birortasi «band» desa rasta band; tasdiqlanmagan «noaniq» kun oxirida «bo'sh» va hisobotda alohida belgilanadi | ✓ VERIFIED | `test_sc5_*` yashil; `sbozor_core/occupancy.py` — `occupied > uncertain > empty > no_coverage`; `OccupancyDayResponse` da `default_empty` **alohida hisoblagich** va u `empty` ga qo'shilmaydi (D-19) |

**Score: 5/5 truths verified**

---

### Ikkinchi qatlam — ATAYIN ISBOTLANMAGAN va bu to'g'ri

| Miqdor | Holat | Tekshirildimi |
|---|---|---|
| RF-DETR verdiktining aniqligi | ⛔ **O'LCHANMAGAN** | ✓ Oltin to'plamda `karmana` qatorlari **aynan 0** (`grep -c karmana manifest.jsonl` → 0); `.onnx` artefakti repoda **yo'q** |
| Aniqlik darvozasi | 😴 **UXLAB YOTIBDI** | ✓ `test_golden_harness.py::test_the_accuracy_gate_is_asleep_today` — bu **skip emas**, bugungi holatni **fakt sifatida** qayd etadi |
| Real artefakt yo'li | 😴 **UXLAB YOTIBDI** | ✓ `pytest -m model` aynan **1 ta** test (§S-14 talabi) va u artefaktsiz **YIQILADI**, `skip` qilmaydi. `addopts = -m "not model"` standart zanjirdan chiqaradi |

⚠ **Birinchi qatlamning yashilligi ikkinchisini yopmaydi va bu hech
qayerda buzilmagan** — pastdagi halollik skaniga qarang.

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `tests/integration/test_phase5_criteria.py` | 5 mezon + meta-darvozalar | ✓ VERIFIED | **1287 qator**, 5 SC testi + 4 meta/nazorat; o'zim yugurtirdim → **9 passed** |
| `services/core-api/app/jobs/audit_draw.py` | Hosila urug', muzlatilgan doira, 70/30 | ✓ VERIFIED | `sha256((ev.id::text \|\| seed.value)::bytea)` bo'yicha ORDER BY; `random()` **yo'q**; `purpose` uchun IKKINCHI mustaqil tartib (`\|\|'\|purpose'`) |
| `services/core-api/app/schemas.py::BlindItemResponse` | 8 AI maydonining **e'lon qilinmasligi** | ✓ VERIFIED | Sakkiztasining birortasi ham sinfda yo'q; `None` bilan yuborish emas — kalitning O'ZI yo'q |
| `migrations/versions/0018_occupancy_domain.py` | `CHECK` + kompozit FK langari | ✓ VERIFIED | `blind_audit_not_shown`, `eval_needs_blind_audit`, `blind_audit_needs_round` + `fk_zone_reviews_queue_kind_anchor` |
| `services/cv-service/app/detector/` | Haqiqiy ONNX yo'li, stub emas | ✓ VERIFIED | 957 qator; `test_detector_has_no_stub.py` da 5 ta struktura testi; `cv-tests` → **130 passed**, exit 0 |
| `frontend/src/components/camera-zones/` | Y-1 zona muharriri | ✓ VERIFIED | 7 komponent, 2551 qator (test'siz) |
| `frontend/src/components/{review,blind-audit,occupancy}/` | Y-2/Y-3/Y-4 yuzalari | ✓ VERIFIED | Barchasi substantiv; `review/blind/` da **dinamik segment yo'q** (G-14a) |
| `packages/sbozor-core/sbozor_core/occupancy.py` | Agregatsiya sof funksiyasi | ✓ VERIFIED | `aggregate_stall_slot()` + `effective_verdict()`; bo'sh kirish `no_coverage` beradi, `empty` **emas** (D-22) |
| `.planning/phases/.../05-HUMAN-UAT.md` | Ochiq bandlar ega va tetik bilan | ✓ VERIFIED | 8 band, har birida egasi |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `GET /snapshots/{id}/image` | `require_any_permission` | `EVIDENCE_FRAME_PERMISSIONS` | ✓ WIRED | `snapshots.py:479` dekorator + `:483` imza aliasi |
| `capture_day` / `snapshot_detail` / `list_alerts` | `require_permission(CAMERA_VIEW)` | `SnapshotViewerDep` | ✓ WIRED (kengaymagan) | 3 marshrut hamon **qat'iy** `CAMERA_VIEW` ostida — `:391`, `:450`, `:574` |
| `decision-bar.tsx` (bosish **va** klaviatura) | `submit()` | `onAnswer` | ✓ WIRED | IKKALA yo'l ham bitta `submit` ga boradi; `submittedRef` qulfi + `event.repeat` qo'riqchisi |
| `blind-session.tsx` | `DecisionBar` | `onAnswer={submit}` | ✓ WIRED | O'z `submittedRef` i bor (mustaqil implementatsiya) |
| `accuracy_report()` | ko'r namuna | `purpose == eval AND queue_kind == blind_audit` | ✓ WIRED | IKKI shart; kuchaytirilgan SC#4 ularni ajratadi |
| `day_close` | `stall_slot_occupancy` | `effective_verdict` + `aggregate_stall_slot` | ✓ WIRED | `resolution_source` to'rt manbani ajratadi |

---

## Topshiriqda so'ralgan maxsus tekshiruvlar

### 1. Huquq kengaytmasi AYNAN BITTA marshrutdami — ✓ HA

```
grep -rn "require_any_permission" --include="*.py" services/
→ snapshots.py:126 (import), :236 (alias), :479 (dekorator)   ← boshqa joy YO'Q
```

Qolgan uchta marshrut (`capture-runs`, kadr detali, `alerts`) hamon
`SnapshotViewerDep` = qat'iy `CAMERA_VIEW`.

**Struktura skanerlari hamon rost gapiradi** — bu eng muhim qismi va u
o'lchandi:

- `required_permissions()` «yo P yo Q» darvozasini ro'yxatiga **qo'shmaydi**
  (`test_personal_data_coverage.py:280-293`), ya'ni «bu marshrut
  `CAMERA_VIEW` TALAB QILADI» degan ma'no buzilmagan;
- `required_any_permissions()` — **alohida** o'quvchi;
- `test_camera_route_coverage.py` ning `CAMERA_SURFACE_PREFIXES` i
  `("/api/v1/cameras", "/api/v1/nvr-devices")` — `snapshots` yuzasi u
  darvozaning qamrovida **hech qachon bo'lmagan**, ya'ni kengaytma
  uchun **istisno qo'shilmagan** (jimgina siljish shakli YO'Q edi);
- `EVIDENCE_FRAME_ALLOWED` darvozada **ikkinchi marta** yozilgan,
  mahsulotdan import qilinmagan.

### 2. Ko'r auditning himoyalari haqiqatan turibdimi — ✓ HA (barchasi)

| Himoya | Mexanizm | Kodda tekshirildi |
|---|---|---|
| Hosila urug' | `ORDER BY sha256((ev.id \|\| seed)::bytea)` | ✓ `audit_draw.py:254` — `random()` yo'q |
| Muzlatilgan doira | `frame_size` + `frame_predicate_hash` + `drawn_at` bitta tranzaksiyada | ✓ `audit_draw.py:589-608`; `FRAME_PREDICATE_HASH` shart **matnidan** hosila |
| Payloadda maydonning UMUMAN yo'qligi | `BlindItemResponse` 8 maydonni e'lon qilmaydi | ✓ `schemas.py:2521+`; klient tomonda G-12 katalog skani **yashil** |
| Javobning qulflanishi | `CHECK blind_audit_not_shown` + kompozit FK | ✓ `0018:615` + `0018:602-606` |
| 70/30 kvota **tortish paytida** | IKKINCHI mustaqil `sha256` tartibi + `ceil` kvota | ✓ `audit_draw.py:261-274` |

**`05-05` topgan chetlab o'tish yo'li YOPILGAN va men uni ko'rdim:**
`zone_reviews.queue_kind` denormalizatsiya nusxasi `fk_zone_reviews_queue_kind_anchor`
bilan `review_assignments (id, queue_kind)` ga qadalgan
(`uq_review_assignments_queue_anchor` bilan qo'llab-quvvatlanadi), ya'ni
nusxani `'uncertain'` deb yozib `CHECK` ni aldab bo'lmaydi.

### 3. D-16 ning yo'qligi izchilmi — ✓ HA, BEShALA QATLAMDA

| Qatlam | Holat | Buyruq / dalil |
|---|---|---|
| Sozlama | `BLIND_AUDIT_REPEAT_RATIO` **yozilmagan** | `grep -r "REPEAT_RATIO" services/` → **0** |
| Sxema | Takroriy band ustuni yo'q | `grep -r "is_repeat\|repeat_of" migrations/ services/` → **0** |
| Payload | `/occupancy/round` da maydon yo'q | `grep -n "self_consistency" services/core-api/app/schemas.py` → **0** |
| Hisobot | `accuracy_report.py` da son ham, maydon ham yo'q | `grep -n "consistency\|repeat"` → **0** |
| Ekran | Placeholder ham qo'yilmagan; klient sxemasi maydonni **RAD ETADI** | `occupancy-queries.test.tsx:271-315` — ikkala sxema uchun `.toThrow()` **va SALBIY NAZORAT** («toza javob o'tadi») |
| i18n | Kalit yozilmagan | `grep -r "consistency" frontend/messages/` → **0** |
| Spetsifikatsiya | UI-SPEC §11.6 qatori **olib tashlangan**, sabab qoldirilgan | `05-UI-SPEC.md:1136-1160` |

⚠ Klient testi «so'z topilmadi» bilan emas, **sxemaning rad etishi**
bilan o'lchaydi va salbiy nazorat holati ham bor — ya'ni bu test ikki
holatni haqiqatan ajrata oladi.

### 4. D-18 ning uchinchi yo'li bormi — ✗ YO'Q

- **API:** `test_no_bulk_approve_endpoint` OpenAPI **sxemasini** skanerlaydi
  (`bulk_on_review_surface` + `bulk_answers_anywhere`), quyi chegara bilan;
- **Klient — bosish:** `decision-bar.tsx:139` → `onAnswer` → `submit` → `submittedRef`;
- **Klient — klaviatura:** `decision-bar.tsx:99-126` → **o'sha** `onAnswer`; ustiga
  `event.repeat` darhol qaytaradi va `blocked` holatida hech nima yubormaydi;
- **Ko'r sessiya:** `components/review/decision-bar` ni **qayta ishlatadi** va
  o'z `submittedRef` i bor;
- `input[type="checkbox"]` ikkala katalogda ham **yo'q** (o'zim skanerladim).

### 5. Halollik skani — aniqlik raqami hech qayerda da'vo qilinmaganmi — ✓ TOZA

```
grep -rniE "(aniqlik|accuracy|precision|recall|mAP|F1)[^.]{0,40}[0-9]{2,3}\s*%" 05-*-SUMMARY.md
→ 1 ta uchrash: 05-14-SUMMARY.md:479 — «T-05-68 («aniqlik 94 %» yolg'iz)»
```

Bu **da'vo emas**, threat-model qatorining nomi (aynan shu yolg'on
shaklga qarshi chora). Boshqa uchrash yo'q. Frontend tomonda foiz
**faqat** `report.measured` rost bo'lganda chiziladi va qaror
SERVERNIKI (`confusion-matrix.tsx:156`, `min_sample` ham serverdan).

---

### Behavioral Spot-Checks (o'zim yugurtirdim, SUMMARY dan olmadim)

| Behavior | Command | Result | Status |
|---|---|---|---|
| Beshala mezon | `docker compose --profile test run --rm tests pytest tests/integration/test_phase5_criteria.py -q` | **9 passed**, exit 0 | ✓ PASS |
| Ko'r audit + huquq + navbat | `... pytest tests/integration/test_blind_audit.py tests/tenancy/test_personal_data_coverage.py tests/integration/test_snapshot_api.py tests/integration/test_uncertain_queue.py -q` | **91 passed**, exit 0 | ✓ PASS |
| cv-service | `docker compose --profile test run --rm cv-tests pytest -q` | **130 passed**, exit 0 | ✓ PASS |
| Frontend | `npm --prefix frontend test` | vitest **620** (43 fayl) + `node --test` **144**, exit 0 | ✓ PASS |
| Ko'r payload darvozasi | `node --test frontend/scripts/blind-payload.test.mjs` | **8 pass**, 0 fail | ✓ PASS |
| Copy darvozalari (G-11/15/16/18a) | `node --test frontend/scripts/zone-copy.test.mjs` | **25 pass** (jami), 0 fail | ✓ PASS |
| Validatsiya imzosi | `npm run validation:check` | `nyquist_compliant: true` — MOS (45 qator, 5 inson bandi); **fayl yo'li chop etildi va u 5-faza** (D-27/W0-14 tasdig'i) | ✓ PASS |
| Talablar sinxroni | `npm run requirements:check` | **49 talab MOS** — Done 21 · Pending 26 · Blocked 2 | ✓ PASS |
| Litsenziya devori | `grep -c "rfdetr-plus\|ultralytics\|LicenseRef-PML" */uv.lock` | **0** ikkala lockda; `torch`/`rfdetr` cv-service lockida **yo'q** | ✓ PASS |
| `gate` byudjeti izchilligi | `grep "gate-budget" package.json` | **1250 s** — `05-VALIDATION.md` bilan bir xil; zanjirda `cv:lint` + `cv:test` bor | ✓ PASS |
| `npm run gate` to'liq | — | ? SKIP — ~17 daqiqa; xostda hozir **ikkinchi stek ishlab turibdi** (6 ta `parnikkpi-*`), ya'ni o'lchov ifloslangan bo'lardi. Tarkibiy bosqichlarning hammasi alohida yashil | ? SKIP |

---

### Requirements Coverage

| Requirement | Status | Verdict | Evidence |
|---|---|---|---|
| **AI-01** | `Done` | ✓ SATISFIED | `test_sc1_*`; piksel koordinatasi **422 bilan rad etiladi** (normalanish darvoza); `version=3` yaratiladi, eskisi `is_active=false` |
| **AI-02** | `Blocked` | ✓ TO'G'RI TASNIFLANGAN | Ikkinchi jumla (o'zgarmaslik + confidence + alohida yozuv) **to'liq o'lchangan**; birinchi jumla (real ONNX) CI'da bajarilmaydi — `.onnx` yo'q, `-m model` chetda, oltin to'plam bo'sh. Egasi/tetigi/bandlari yozilgan |
| **AI-03** | `Done` | ✓ SATISFIED | `test_sc3_*`; 409 `review_budget_exhausted` «navbat bo'sh» dan boshqa kod; dalil-kadr bo'shlig'i `05-15` da yopilgan |
| **AI-04** | `Done` | ✓ SATISFIED | `test_sc4_*`; hisobot AYNAN `eval` lar sonini beradi; D-16 ning qurilmagani talab qatorida **ochiq yozilgan** |
| **AI-05** | `Done` | ✓ SATISFIED | `test_sc5_*` + `test_aggregate_stall_slot.py` (120 holat) + tenglik uchun **atayin yozilgan** `test_the_losing_verdicts_source_is_not_carried` |
| **AI-06** | `Done` | ✓ SATISFIED | `default_empty` alohida hisoblagich; `zone_reviews` ga soxta qator **yozilmaydi** |

**Vocabulary:** ✓ `Done` / `Pending` / `Blocked` — yaroqsiz `Complete`
qiymati **yo'q**; `npm run requirements:check` mexanik tasdiqladi.
`- [ ] AI-02` katakchasi `Blocked` bilan **izchil**.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | `TBD` / `FIXME` / `XXX` | — | **TOPILMADI** — 149 ta o'zgargan `.py`/`.ts`/`.tsx`/`.mjs` fayl skanerlandi |
| — | — | `TODO` / `HACK` / `PLACEHOLDER` | — | **TOPILMADI** |
| — | — | Stub / bo'sh ekran | — | **TOPILMADI** — barcha komponentlar substantiv |

---

## Ogohlantirishlar — bloklamaydi, lekin yozib qo'yiladi

### ⚠ W-1: `05-VALIDATION.md:260` «beshala» so'zi ikki xil ro'yxatga ishora qiladi

Imzo qatori: *«Ko'r auditning **beshala** strukturaviy himoyasi
testlangan (D-17)»* va beshtasini sanaydi (urug', muzlatilgan doira,
payloadda yo'qlik, javobning qulflanishi, 70/30).

`05-11-SUMMARY.md:96` esa: *«beshala himoyaning **to'rttasi** kodda va
sxemada o'lchandi, **beshinchisi (D-16)** ... qurilmadi»*.

Sabab — repoda D-17 ning **ikki xil sanog'i** bor:

| Manba | Ro'yxat | Natija |
|---|---|---|
| `05-CONTEXT.md:49` | urug' · payloadda yo'qlik · `CHECK` · o'zgarmaslik · 70/30 | 5/5 qurilgan |
| `05-11-PLAN.md:57-64` | 5 ta **dushman**, 5-chorasi = D-16 | 4/5 qurilgan |

**Nima bloklamaydi:** imzo sanagan beshala mexanizm **haqiqatan bor va
men har birini ko'rdim**; o'sha faylning `automated_replacements` bloki
(40–41-qatorlar) D-16 ning **O'RNI BOSILMAGANINI OCHIQ AYTADI**. Ya'ni
hujjat yolg'on gapirmaydi.

**Nima xavfli:** faqat imzo qatorini o'qigan kishi «ko'r auditning
himoya to'plami to'liq» degan xulosaga keladi, holbuki fazaning o'z
qabul qilingan ramkasida u **4/5**. Bitta aniqlashtiruvchi jumla buni
yopadi.

✅ **YOPILDI (05-16, `b6c90f1`)** — «bitta jumla» dan kengroq: ildiz
`05-UI-SPEC §7.6` da topildi (pastdagi yopilish bo'limiga qarang).

### ⚠ W-2: G-18(b) skani UI-SPEC e'lon qilganidan **tor**

UI-SPEC §15: *«(b) `components/review/**` **va** `components/blind-audit/**`
da `type="checkbox"` ... yo'q»*.

Amalda: `review-session.test.tsx:452-459` faqat **Y-2 sessiyasini**
render qiladi. `blind-session.test.tsx` da checkbox skani **yo'q**
(`grep` → 0).

**Bugun zarari yo'q:** ikkala sessiya ham bitta `DecisionBar` ni
ishlatadi, ya'ni bugungi kod qamralgan. **Ertangi xavf:** to'g'ridan-to'g'ri
`blind-session.tsx` ga qo'shilgan checkbox birorta darvozani
qizartirmaydi.

✅ **YOPILDI (05-16, `7f18d7d`)** — «ertangi xavf» sabotaj bilan
**bugun o'lchandi va tasdiqlandi**: checkbox qo'yilganda mavjud 40 test
yashil qolgan. Qamrov endi §15 dan hosila.

### ⚠ W-3: `SNAPSHOT_CAMERA_ONLY_ROUTES` **yopiq to'plam emas**

`test_the_evidence_frame_widening_stops_at_the_image_route` uchta
marshrutni nom bilan tekshiradi va eskirishni ushlaydi (`route is None`
→ yiqiladi). Lekin `snapshots.py` ga **yangi** marshrut qo'shilib unga
«yo P yo Q» darvozasi berilsa, birorta test qizarmaydi.

Taqqoslash: o'sha faylning `BINARY_PERSONAL_ROUTES` i uchun
**yopiqlik testi bor** (`found - classified` va `classified - found`
ikkalasi ham tekshiriladi). Bu asimmetriya — o'sha naqshni bu ro'yxatga
ham qo'llash bir necha qatorlik ish.

✅ **YOPILDI (05-16, `795a63b`)** — naqsh qo'llandi va sabotaj bilan
tasdiqlandi: `any` darvozali yangi marshrutda **eski test yashil
qolgan**, yangisi qizargan.

---

## Human Verification Required

Fazani bloklamaydi (self-service direktivasi), lekin ularsiz
**«detektor to'g'ri ishlaydi» degan da'vo berilmagan bo'lib qoladi**.
To'liq matn `05-HUMAN-UAT.md` da; sakkiztasi ham ega va tetik bilan.

### 1. Detektorning aniqligi
**Test:** Real Karmana kadrlarini yorliqlab `manifest.jsonl` ga `source='karmana'` qatorlarini qo'shish, so'ng `pytest -m golden`
**Expected:** Uxlab yotgan darvoza **kodsiz uyg'onadi** va birinchi haqiqiy aniqlik raqamini beradi
**Why human:** Haqiqat yo'q — bugun `karmana` qatorlari aynan 0

### 2. COCO sinflari o'zbek bozori mollarida
**Test:** Birinchi real kadrlar to'plamida verdiktlarni ko'zdan kechirish
**Expected:** Sinflar mazmunli ishlaydi (yoki `timm` ikkinchi bosqichi kerakligi ma'lum bo'ladi)
**Why human:** Sintetik detektsiya bu savolni umuman bermaydi

### 3. ONNX artefaktini eksport qilish
**Test:** `rfdetr[train,onnx]` bilan eksport → `ops/models/rfdetr-large.onnx` → `pytest -m model`
**Expected:** Aynan bitta model-markerli test yashil
**Why human:** Ops ishi + GPU ijarasi

### 4. Ko'r auditning amaliy xolisligi
**Test:** Nazoratchi bilan pilot haftasida ishlash
**Expected:** Nazoratchi tizim javobini taxmin qilishga urinmaydi
**Why human:** Strukturaviy himoyalar o'lchangan; odamning o'zini test o'lchamaydi

### 5. Poligon chizishning amalda bajariladiganligi
**Test:** Real Karmana chizmasida 300–1000 rastani chizish, vaqtni o'lchash
**Expected:** Uch yordamchi bilan 0.5–1 soat
**Why human:** Vaqt faqat real admin bilan o'lchanadi

### 6. Kunlik 30 bandlik byudjet realmi
**Test:** Nazoratchi bir hafta davomida navbatni yuritadi
**Expected:** Charchashsiz bajariladi
**Why human:** MEXANIZM o'lchangan, QIYMAT emas

### 7. D-05 chiqish yo'li — 60 poligonli kamerada sudrash
**Test:** Real brauzerda `pointermove` kechikishini o'lchash
**Expected:** ≤16 ms
**Why human:** jsdom render vaqtini bermaydi

### 8. «Ko'rmasdan tekshirish» atamasining ona tilida ko'rigi (O-01)
**Test:** Ona tilida so'zlashuvchi + direktor atamani ko'rib chiqadi
**Expected:** Nazoratchi uchun tushunarli
**Why human:** Til sifati

---

## Gaps Summary

**Bloklovchi bo'shliq TOPILMADI.** Beshala ROADMAP mezoni kodda
bajarilgan va men har birini SUMMARY da'vosidan emas, **o'z
buyruqlarim bilan** tasdiqladim (9 + 91 + 130 + 620 + 144 + 8 + 25
test, hammasi exit 0).

4-fazada topilgan shakl — «konteyner sozlamani oladi, lekin funksiya
o'sha jarayonda chaqirilmaydi» — bu yerda **maxsus qidirildi va
topilmadi**: huquq kengaytmasi aynan bitta marshrutda, struktura
skanerlari kengaytmadan keyin ham rost gapiradi, hisobot filtri ikki
shartli va kuchaytirilgan test ularni ajratadi, D-16 esa yettita
qatlamda izchil ravishda **yo'q**.

Uchta ogohlantirish (W-1, W-2, W-3) **testlarning kelajakdagi
sezgirligi** haqida, bugungi xulq haqida emas. Ularni yopish uchun:

- **W-1:** `05-VALIDATION.md:260` ga aniqlashtiruvchi jumla —
  «D-17 ning mexanizmlari 5/5; `05-11-PLAN` sanagan 5 dushmandan
  5-chorasi (D-16) qurilmagan, sabab 40–41-qatorlarda».
- **W-2:** `blind-session.test.tsx` ga `input[type="checkbox"]`
  skanini qo'shish (Y-2 dagi shaklning nusxasi).
- **W-3:** `SNAPSHOT_CAMERA_ONLY_ROUTES` ni `BINARY_PERSONAL_ROUTES`
  naqshi bo'yicha **yopiq to'plamga** aylantirish.

⚠ **Ikkinchi qatlam hamon MAVJUD EMAS va bu kutilgan holat.** Aniqlik
o'lchanmagan, oltin to'plam bo'sh, artefakt yo'q — va bu hech qayerda
yashirilmagan. AI-02 ning `Blocked` maqomi, uxlab yotgan ikki darvoza
va `05-HUMAN-UAT.md` ning 8 bandi buni ochiq ushlab turadi.

---

*Verified: 2026-08-10T04:20:00Z*
*Verifier: Claude (gsd-verifier)*

---

## Ogohlantirishlarning yopilishi (05-16)

**Sana:** 2026-08-10 · **Qamrov:** faqat W-1, W-2, W-3. **Mahsulot
xulqi o'zgarmadi** — birorta marshrut huquqi, birorta ekran tegilmadi.

| # | Nima qilindi | Commit |
|---|---|---|
| **W-1** | Ikki «beshlik» o'z uyida **nomlandi**: mexanizmlar `D-17.1`…`D-17.5`, dushmanlar `§C.8-1`…`§C.8-5`. Imzo qatori endi qaysi ro'yxatni sanashini va D-16 ning yo'qligini aytadi | `b6c90f1` |
| **W-2** | G-18(b) qamrovi UI-SPEC §15 ning G-18 **qatoridan hosila** qilinadi (`bulk-action-surface.test.mjs`) | `7f18d7d` |
| **W-3** | Snapshots yuzasi **yopiq to'plam** (`__module__` dan hosila) + «yo P yo Q» darvozasi butun ilova bo'ylab yopildi | `795a63b` |

### W-1 ning ildizi ogohlantirishda yozilganidan CHUQURROQ edi

Ogohlantirish ikki manbani ko'rsatgan edi (`05-CONTEXT:49` va
`05-11-PLAN:57–64`). Ular haqiqatan ikki xil ro'yxat, lekin **ularni
bir yorliq ostida ushlab turgan uchinchi qator** bor edi:

> `05-UI-SPEC §7.6`: *«05-RESEARCH §C.8 beshta strukturaviy **himoyani**
> sanaydi»* — holbuki §C.8 beshta **DUSHMANNI** sanaydi.

Ya'ni spetsifikatsiya dushmanlar bo'limini himoyalar bo'limi deb
atagan va shundan keyin har ikkala «beshlik» bir-biriga o'tib ketardi.
Faqat imzo qatorini yumshatish bu qatorni joyida qoldirardi.

⚠ **Ikki ro'yxat 1:1 EMAS** — bu endi uchala faylda yozilgan:
§C.8-3 ning chorasi (`UNIQUE`) D-17 beshligida yo'q; D-17.5 (70/30)
dushman qatori emas; §C.8-4 ga D-17.1 va D-17.4 birgalikda javob
beradi. Ikkalasining ham beshta a'zoli bo'lishi — **tasodif**, va aynan
shu tasodif ogohlantirishni tug'dirgan.

### Sabotajlar — nima qizardi va sabotaj nishonga YETDIMI

| Sabotaj | Nishonga yetdimi | Nima qizardi | Nimani ISBOTLADI |
|---|---|---|---|
| **W-3:** `alerts_router` ga `require_any_permission` li `/summary` marshruti | ✓ ha — marshrut grafida `/api/v1/alerts/summary` paydo bo'ldi | Yangi ikkala test; xabar aybdor yo'lni **nom bilan** chiqardi | ⛔ **Eski `test_the_evidence_frame_widening_stops_at_the_image_route` YASHIL QOLDI.** Ya'ni W-3 nazariy emas edi: eski darvoza ikki holatni **ajrata olmasdi** |
| **W-2/A:** `<input type="checkbox">` → `blind-session.tsx` | ✓ ha — checkbox haqiqatan render qilindi | Faqat yangi hosila darvoza | ⛔ **Mavjud 40 test (`review-session` + `blind-session`) YASHIL QOLDI** — e'lon qilingan kafolat mexanizmidan keng ekanining o'lchovi |
| **W-2/B:** e'londan `components/blind-audit/**` naqshi olib tashlandi (A joyida turib) | ✓ ha | «kamida ikki katalog» **va** fayl soni quyi chegarasi | Skan checkbox ni **emas**, «atigi 4 ta fayl» ni qizartirdi — ya'ni qamrov **haqiqatan e'londan** kelmoqda, qattiq yozilgan emas. Qattiq yozilgan bo'lsa, checkbox hamon topilardi |

Uchala sabotaj ham `cp` bilan qaytarildi (`git checkout --` ishlatilmadi).

⚠ **W-1 da sabotaj yo'q va bu ataylab:** u hujjat ambiguitetsi — uni
o'lchaydigan test yo'q. Uning o'rniga **ildiz izlandi** va yuqoridagi
uchinchi manba shu izlanishda topildi.

### Darvoza bosqichlari — hammasi yashil

`npm run gate` ning **wall-clock** i o'lchanmadi: xostda hamon
begona stek ishlab turibdi (6 ta `parnikkpi-*`), ya'ni raqam
ifloslangan bo'lardi (W0-13 protokoli «tinch xost» talab qiladi).
Buning o'rniga **tarkibiy bosqichlar alohida** yugurtirildi:

| Bosqich | Natija |
|---|---|
| `npm run lint` (ruff + format + mypy) | ✓ 289 fayl formatli, **279 manbada mypy toza** |
| `npm run test` (to'liq pytest) | ✓ **2374 test**, exit 0 |
| `npm run cv:lint` / `npm run cv:test` | ✓ 33/32 toza · **130 passed** |
| `npm --prefix frontend run i18n:check` | ✓ **980 kalit × 3 til**, drift yo'q |
| `npm --prefix frontend test` | ✓ `node --test` **152** + vitest **620** (43 fayl) |
| `typecheck` · `lint` · `build` | ✓ uchalasi toza |
| `validation:check` · `requirements:check` | ✓ `nyquist_compliant: true` · 49 talab MOS |

**Baza bilan farq — aynan qo'shilgani:**
`node --test` 144 → **152** (+8, yangi darvoza);
tenancy 549 → **551** (+2, yopiqlik testlari);
vitest **620 o'zgarmadi** (yangi testlar vitest emas).

⚠ Topshiriqdagi tenancy bazasi **548** deb berilgan edi; `HEAD` da
o'lchanganda **549** chiqdi (`--collect-only`, o'zgarishlarim
qo'yilmasdan oldin). Ya'ni farq mening qo'shganimdan emas —
bazaning o'zi bir birlikka eskirgan edi.

### Nima YOPILMADI

Uchala ogohlantirish ham **testlarning kelajakdagi sezgirligi**
haqida edi va shu qatlamda yopildi. **Ikkinchi qatlam — aniqlik —
hamon o'lchanmagan** va bu holat o'zgarmadi: oltin to'plamda `karmana`
qatorlari 0, `.onnx` artefakti yo'q, `pytest -m golden` va `-m model`
uxlab yotibdi. `05-HUMAN-UAT.md` ning 8 bandi kuchda qoladi.

*Closed: 2026-08-10 · gsd-executor (05-16 gap closure)*
