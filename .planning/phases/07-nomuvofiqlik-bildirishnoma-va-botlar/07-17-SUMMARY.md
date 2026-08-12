---
phase: 07-nomuvofiqlik-bildirishnoma-va-botlar
plan: 17
subsystem: faza-darvozasi
tags: [criteria, budget, requirements, uat, i18n-gate]
requires:
  - 07-07 (case domeni + `recon.open`)
  - 07-09 (`outbox_tick`)
  - 07-10 (nomuvofiqlik API)
  - 07-13 (dayjestlar + BOT-03)
  - 07-16 (yetkazilganlik yuzasi)
provides:
  - "tests/integration/test_phase7_criteria.py — beshala mezon BITTA buyruqda"
  - "frontend/scripts/snapshot-copy.test.mjs::G-36 — ALERT_TITLE_KEYS x 3 locale"
  - "o'lchangan `gate` byudjeti (1424/1263/1349 s, chegara 2300 s o'zgarmadi)"
  - ".planning/REQUIREMENTS.md — to'qqizala talab dalil bilan `Done`"
  - "07-HUMAN-UAT.md — yetti band, har birida ega va tetik"
affects:
  - package.json (`//gate-budget` izohi)
  - .planning/phases/07-*/07-VALIDATION.md (sign-off, byudjet, Per-Task xarita)
tech-stack:
  added: []
  patterns:
    - "respx `assert_all_mocked=True` — mahsulot jo'natuvchisi oxirigacha, faqat TARMOQ chegarasi tutiladi"
    - "AST bilan soxtalashtirish taqig'i — TO'RT mustaqil yo'l (import · fixture · sinf vorisi · SQL konstantasi)"
    - "reyestr x 3 locale parity + o'lcham qulfi + zaxira istisnosi (G-17 -> G-36)"
key-files:
  created:
    - tests/integration/test_phase7_criteria.py
    - .planning/phases/07-nomuvofiqlik-bildirishnoma-va-botlar/07-HUMAN-UAT.md
  modified:
    - frontend/scripts/snapshot-copy.test.mjs
    - package.json
    - .planning/REQUIREMENTS.md
    - .planning/phases/07-nomuvofiqlik-bildirishnoma-va-botlar/07-VALIDATION.md
    - .planning/phases/07-nomuvofiqlik-bildirishnoma-va-botlar/deferred-items.md
decisions:
  - "Byudjet 2300 s DA QOLDI: eng yomon o'lchov 1424 s, zaxira 876 s"
  - "Pasayish 7-fazaning yutug'i EMAS — xostdagi cv-service crash-loop to'xtatilgani"
  - "ROADMAP.md va STATE.md TEGILMADI — ular orkestratorniki"
metrics:
  duration: "~4 soat (shundan ~2 soat o'lchov kutish)"
  completed: 2026-08-12
  tasks: 3
  commits: 6
---

# Phase 7 Plan 17: Faza darvozasi Summary

7-fazaning beshala muvaffaqiyat mezoni endi **bitta buyruqda** o'lchanadi va
soxtalashtirish **AST bilan** to'rt yo'ldan taqiqlangan; `gate` byudjeti tinch
xostda **uch marta** o'lchandi va **o'zgarmadi**.

## Nima qilindi

### 1. `tests/integration/test_phase7_criteria.py` (1847 satr, YANGI)

Beshta mezon, beshta test, beshta meta-darvoza. Modul `test_phase6_criteria.py`
ning shaklini takrorlaydi, lekin bu fazaning **o'z yolg'oni** boshqa bo'lgani
uchun taqiqlar ham boshqa.

⛔ **Fazaning markaziy qiyinchiligi va uning yechimi.** SC#3 va SC#5 «Telegramda
oladi» deydi, CI'da esa haqiqiy Telegram **yo'q**. Eng arzon yolg'on —
jo'natuvchini almashtirish yoki navbat qatorini qo'lda `delivered` qilib
«xabar bordi» deb yozish. Yechim: mahsulot jo'natuvchisi (`AlertSender`)
**oxirigacha** yuritiladi va `respx` faqat **tarmoq chegarasini** tutadi,
ya'ni o'lchanadigan narsa **aynan chiqqan HTTP so'rovi va uning tanasi**.

| Mezon | Nima o'lchanadi |
|---|---|
| **SC#1** | `recon.open` chaqiriladi -> `GET /reconciliation/report`: ikkala sinf ham javobda va **ajratilgan**; har qatorda `evidence_snapshot_ids` bo'sh emas va `UUID`; ⛔ tanada `presigned`/`http`/`image` **yo'q**, rekursiv skanda shaxsiy maydon **0** |
| **SC#2** | Job **uchta** case ochadi `(anomaly, unpaid) == (2, 1)`; `new`->`in_review`->`justified` = **ikki** audit qatori, aktor **direktorning identifikatori**; `"other"` -> **422**; hit-rate **0.5**, `open_cases` maxrajga kirmaydi; o'lchovsiz oraliqda **`null`** |
| **SC#3** | (a) ikki dayjest -> `outbox_tick` -> Telegram'ga **aynan 2** so'rov, direktorning chatiga, ikki sifatlovchi **aralashmaydi**, ikki pul qatori **bir xil emas**, matnda sotuvchi ismi **yo'q**; (b) uch rolda **uch xil** `metric`, maydonlar **aynan** `{metric, value}`, kassir qiymati kun summasiga **teng emas** |
| **SC#4** | `/internal/bot/resolve` -> `bound`, `Set-Cookie` yo'q; qoldiq `vendor_outstanding()` bilan **`==`**; tarix `vendor_charge_allocation()` **dan hosila**; ikki bozorda bir xil telefon -> `multiple_matches` va bog'lanish **0** |
| **SC#5** | Kvitansiya **bir marta** (`dedupe_key == receipt:{payment_id}`); quiet oynada kvitansiya **boradi**, eslatma esa navbatdan **umuman olinmaydi**; `overdue_days` ikki bozorda ikki xil -> eslatma faqat **bittasida**; `403` -> `blocked`, `attempt_count == 1`, ikkinchi tikda `respx` sanoqi **o'smaydi**; holat direktor yuzasida **ko'rinadi** |

**Meta-darvozalar:** `test_every_criterion_has_its_own_test` ·
`test_criteria_module_uses_no_fakes` (AST, **to'rt** mustaqil yo'l) ·
`test_the_fake_registry_names_are_built_correctly` ·
`test_respx_is_asserted_to_be_all_mocked` ·
`test_the_module_measures_a_market_that_the_seed_actually_owns`.

⛔ **SC#4 ning chegarasi OCHIQ yozilgan** (T-07-98): `contact` obyektining uch
darvozasi bu modulda **o'lchanmaydi** — `bot-service` paketi `core-api`
image'ida import qilinmaydi (ikkala kod bazasi ham `app` nomiga ega; aiogram
`pydantic<2.14` va `redis<8` ni, core-api esa `redis==8.0.1` ni qadaydi).
Docstring `bot-tests` buyrug'ini **nomma-nom** beradi.

⛔ **`respx` taqiqlangan ildizlar ro'yxatida ATAYIN YO'Q** va bu farq modul
docstringida asoslangan: u mahsulot yo'lini **almashtirmaydi**. `freezegun`
esa ro'yxatda **bor** — bu fazaning hamma jobi vaqtni argument sifatida oladi.

**Sabotaj (bajarildi):** `outbox.py::_classify` da `403` shoxi `RETRY` ga
o'zgartirildi -> SC#5 **QIZARDI** (`403 dan keyin QAYTA URINISH bo'ldi (1 -> 2)`).
Sabotaj qaytarildi.

### 2. G-36 — `deferred-items.md` ning 1-bandi YOPILDI

`frontend/scripts/snapshot-copy.test.mjs` ga to'rt test qo'shildi:
o'lcham qulfi (15) · OLDINGA (tur -> matn, uchala locale) · TESKARI
(matn -> tur, o'lik kalit yo'q) · zaxira yorliq (`errors.generic`) alohida.

**Sabotaj (bajarildi):** 16-a'zo (`sabotage_probe`) matnsiz qo'shilganda
**ikki** darvoza qizardi — o'lcham qulfi (`16 != 15`) va OLDINGA parity
**uchala locale'ni nomma-nom** ko'rsatib. Sabotaj qaytarildi.

### 3. Byudjet — O'LCHANDI, o'zgarmadi

```
npm run gate  ->  1424 s / 1263 s / 1349 s   (uchalasi exit 0)
tarqoqlik     ->  161 s (eng yomonning 11.3 %)
eng yomon     ->  1424 s < 2300 s  =>  BYUDJET O'ZGARMAYDI (zaxira 876 s)
nazorat       ->  gate:fast 80 s (byudjet 200 s)
```

`bot:test` ni `gate` dan ajratish varianti **umuman ko'rilmadi** — ehtiyoj yo'q.
Raqam `package.json::gate-budget` va `07-VALIDATION.md` da **bir xil** (T-07-99,
grep bilan solishtirildi).

**To'plam O'SDI** (pasayish «kamroq test» degani emas): vitest **717 -> 806**
(+89); backend pytest jami **3101** (unit 1218 · integratsiya 1152 · tenancy
731); zanjirga `bot:lint` + `bot:test` qo'shilgan (07-01).

### 4. Talab holatlari va UAT

To'qqizala talab `Done` — har biri **qaysi test** bilan isbotlanganini va
**nima o'lchanmaganini** nomlab. `BOT-01`/`BOT-02` qatorlarida **ikkala**
buyruq ham. `check-requirements-sync.mjs` yashil: **Done 39 · Pending 8 ·
Blocked 2**. `07-HUMAN-UAT.md` — **yetti** band, har birida **ega** va **tetik**.

## ⛔ ENG MUHIM TOPILMA — XOST O'LCHOVI IFLOSLANTIRGAN EDI

Birinchi o'lchov davomida `docker stats` ko'rsatdi: **`sbozor-cv-service-1`
~80 % CPU** yeb turibdi. Sabab jurnalda:

```
CV_MODEL_PATH (/app/models/rfdetr-large.onnx) topilmadi
taskiq.process-manager: worker-0 is dead. Scheduling reload.
```

Ya'ni foydalanuvchining **jonli** steki `cv-service` ni **har ~1 soniyada**
qayta ishga tushirib turgan cheksiz siklda edi. Birinchi o'lchov (1266 s da
to'xtatilgan) shu sababdan **bekor qilindi**, konteyner to'xtatildi va o'lchov
qaytadan olindi — natijada `npm run test` **~2 barobar** tezlashdi
(ifloslangan: 19 daqiqada 46 %; toza: 9 daqiqada 37 %).

⚠ **ONNX artefaktining yo'qligi nuqson emas** — u `ops` yetkazmasi
(`ops/models/README.md`, `05-HUMAN-UAT.md` #3). Qayd etilgani — uning **yon
ta'siri**: artefaktsiz konteyner xostning **har qanday o'lchovini**
ifloslantiradi. Bu 06-14 ning 1899 s raqamiga ham ta'sir qilgan bo'lishi
mumkin, ya'ni ikki o'lchov **to'g'ridan-to'g'ri solishtirilmaydi** — va
byudjet aynan shu noaniqlik uchun ham **pasaytirilmadi**.

Konteyner o'lchovdan keyin **tiklandi** (quyidagi ro'yxat).

## O'lchov qarzi YOPILDI — `tests/tenancy` MERGED MAIN da

| O'lchov | Natija |
|---|---|
| `npm run test:tenancy` (merged main, tinch xost) | **exit 0**, **573 s**, **731 test**, 100 % |
| Uchala `gate` yugurishi ichida (`npm run test` -> `pytest -q`) | **exit 0** (tenancy shu zanjirda) |

⚠ **`-p no:randomly` bilan olingan o'lchov 2062 s bergan** — 3.6 barobar
sekin. Tasodifiy tartibni o'chirish fixture guruhlanishini buzadi, ya'ni u
**boshqa savolni** o'lchaydi. Yakuniy raqam `package.json` dagi **aynan
o'sha buyruq** bilan olindi.

## Tinch xost protokoli — nomma-nom

**To'xtatilgan** (o'lchovdan oldin) va **TIKLANGAN** (o'lchovdan keyin):

| Konteyner | Nima |
|---|---|
| `parnikkpi-backend-1`, `-bot-1`, `-celery_worker-1`, `-db-1`, `-frontend-1`, `-redis-1` | Begona loyihaning steki (05-15 da ham aynan shu) |
| `sbozor-cv-service-1` | ⛔ crash-loop, ~80 % CPU (yuqoridagi topilma) |
| `adoring_agnesi`, `clever_brown`, `focused_proskuriakova`, `nice_burnell` | Oldingi ijrochi agentlarning **yetim** testcontainer'lari (Ryuk o'chirilgan) |

Barchasi `docker start` bilan **tiklandi** va xost boshlang'ich holatiga
qaytdi (17 konteyner). Mening izolyatsiyalangan loyiham
(`sbozor-aa44db23`) `down -v` bilan **butunlay** olib tashlandi.

⚠ **To'rtta yetim testcontainer foydalanuvchi uchun tozalash nomzodi** —
ular 02:06 va 04:27 da yaratilgan va hech kimga xizmat qilmaydi. Men ularni
**o'chirmadim**: bu mening qarorim emas.

## Deviations from Plan

### Rule 1 — Reja aytgan yuza mavjud emas edi

**1. `GET /notifications/deliveries` marshruti YO'Q**
- **Topildi:** Task 1, SC#5 ni yozayotganda
- **Muammo:** reja SC#5 ning oxirgi bandini `GET /notifications/deliveries`
  deb nomlagan; 07-16 esa yuzani `GET /api/v1/reconciliation/delivery`
  sifatida qurgan
- **Tuzatish:** mezon **mavjud** marshrutni chaqiradi; javob shakli ham
  boshqa (`blocked_count`, `counts` emas) va u ham to'g'rilandi
- **Fayl:** `tests/integration/test_phase7_criteria.py`

**2. Rejaning `_criteria_day()` taxminlari mahsulot qoidalariga mos kelmadi**
- **Topildi:** Task 1, birinchi yugurishda
- **Muammo:** uchta mustaqil nomuvofiqlik: (a) `ReconOpenResult` da
  `.opened` maydoni yo'q (`anomaly_cases`/`unpaid_cases` bor); (b) SINF A
  ning case'i `overdue_days` **chegarasidan keyin** ochiladi, ya'ni
  «kechagi» hisob bilan u **umuman** ochilmasdi; (c) hisobot qatorlari
  **case'dan hosila**, ya'ni ikkala sinf bir kunda ko'rinishi uchun job
  **ikki marta** (kun uchun va bugungi kun uchun) chaqirilishi kerak — bu
  mahsulotning **haqiqiy kunlik jadvali**
- **Tuzatish:** SC#1 ikki `recon.open` chaqiruvi bilan yozildi va chegara
  docstringda **ochiq** tushuntirildi
- **Fayl:** `tests/integration/test_phase7_criteria.py`

**3. Seed'ning o'z qoidalari uchta da'voni bo'sh-rost qilib qo'yardi**
- **Topildi:** Task 1, ketma-ket uch yugurishda
- **Muammo:** (a) `market_domain` ning A bozoridagi **birinchi** sotuvchisi
  B bozoriniki bilan **bir xil telefonga** ega (`B_VENDOR_PHONE =
  A_VENDOR_PHONES[0]`, D-12 ni ifodalash uchun ataylab) — ya'ni u bilan
  «bog'lanish» shoxi **hech qachon** ifodalanmasdi; (b) A bozorining
  oltita rastasidan **bugun faqat birinchisi** biriktirilgan (qolganlari
  biriktirish bo'shlig'ida yoki umuman biriktirilmagan) — ikkinchi to'lov
  `409 stall_not_assigned` berardi; (c) kvitansiyaning **sotuvchisi**
  rastaning **bugungi** biriktirilgani, ya'ni billing seed'ining
  sotuvchisi emas — noto'g'ri bog'lanish `unresolved` shoxini berardi va
  «kvitansiya quiet oynada ham boradi» da'vosi **yolg'on sababdan**
  qizarardi
- **Tuzatish:** (a) bog'lanish uchun **ikkinchi** sotuvchi + nazorat
  asserti (`count(*) == 1`), to'qnashuv uchun seedning **o'z** juftligi +
  nazorat (`count(DISTINCT market_id) == 2`); (b) bitta to'lov va sabab
  docstringda; (c) manzil **outbox qatorining o'zidan** o'qiladi
- **Fayl:** `tests/integration/test_phase7_criteria.py`

**4. FIFO taqsimlash test seed'ining o'zini yeb qo'ydi**
- **Topildi:** Task 1, SC#5 ning ikkinchi qadamida
- **Muammo:** kvitansiya **haqiqiy** to'lov va uning krediti
  `FIFO_OLDEST_SERVICE_DATE_FIRST` (D-24) bo'yicha **eng eski** kunga
  tushadi — ya'ni tarifga teng qarz o'sha to'lov bilan **to'liq**
  yopilardi, `overdue_vendors()` bo'sh qaytardi va eslatma **umuman**
  yozilmasdi. ⛔ Nosozlik **mahsulotda emas, seedda** edi va u BOT-03 ni
  o'lchanmagan qoldirardi
- **Tuzatish:** qarz **to'lovdan uch barobar katta** qilindi; sabab kodda
  ochiq yozildi
- **Fayl:** `tests/integration/test_phase7_criteria.py`

### Rule 2 — Ikki da'vo yolg'on yashil bo'lishi mumkin edi

**5. «Quiet oynada ushlab qolindi» ni «manzili topilmadi» dan ajratish**
- **Topildi:** SC#5 ni yozayotganda
- **Muammo:** ikkala shox ham qatorni `pending` da qoldiradi, ya'ni
  **holat ustuni** yolg'on yashil berardi
- **Tuzatish:** `attempt_count == 0` asserti qo'shildi — quiet oyna
  qatorni **umuman oldirmaydi**, manzilsiz qator esa **olinadi**
- **Fayl:** `tests/integration/test_phase7_criteria.py`

**6. Vaqtga bog'liq flakilik (kod emas, soat)**
- **Topildi:** SC#3/SC#5 birinchi yugurishlarida (`route.call_count == 0`)
- **Muammo:** `enqueue()` `next_attempt_at` ni **insert paytidagi**
  `now()` ga qo'yadi, tik esa `next_attempt_at <= :now` bo'lgan qatorlarni
  oladi. «Bugun 22:30 (Toshkent)» = «bugun 17:30 UTC» — test 17:30 UTC dan
  **keyin** yugurganda tik **nol** qator olardi va nosozlik **kuniga besh
  soatgina** ko'rinardi
- **Tuzatish:** `_tick_day(offset)` yordamchisi — tik payti **har doim
  ertaga va keyin**; sabab docstringda to'liq yozildi
- **Fayl:** `tests/integration/test_phase7_criteria.py`

### Rule 3 — Muhit bloklagan bandlar

**7. Izolyatsiyalangan compose loyihasi ikki marta yiqildi**
- **Muammo A:** `cv-tests` ning `db` bog'liqligi xost portini so'raydi
  (`compose.override.yml`), foydalanuvchining jonli steki esa
  `DB_HOST_PORT=55432` ni **band qilgan** -> `port is already allocated`
- **Tuzatish A:** `DB_HOST_PORT`/`CACHE_HOST_PORT`/`API_HOST_PORT`
  izolyatsiyalangan loyiha uchun surildi
- **Muammo B:** `cv:test` **compose `db`** ustida yuguradi (testcontainers
  EMAS — bu `compose.yaml` da ochiq yozilgan) va yangi loyihaning
  **migratsiya qilinmagan** volume'i `relation "occupancy_events" does not
  exist` berardi
- **Tuzatish B:** `npm run migrate` **o'lchov oynasidan tashqarida**
  bajarildi
- ⚠ **Bu ikkalasi ham keyingi agentlar uchun YANGI muhit tuzog'i** —
  ular berilgan ro'yxatda yo'q edi

**8. `grep -c "unittest.mock" -> 0` darvozasi o'z izohida yiqildi**
- **Topildi:** qabul mezonini tekshirayotganda (sanoq `1` chiqdi)
- **Muammo:** taqiqni **tushuntirish uchun** yozilgan izoh taqiqlangan
  nomni **ko'chirma** qilib keltirgan edi — ya'ni darvoza o'zini o'zi
  qizartirardi (06-14 ochiq ogohlantirgan sinf)
- **Tuzatish:** izoh nomni **yozmasdan** ta'riflaydi; sanoq **0**
- **Fayl:** `tests/integration/test_phase7_criteria.py`

## ⛔ ROADMAP.md va STATE.md — ATAYIN TEGILMADI

Reja `files_modified` da `.planning/ROADMAP.md` ni sanaydi, lekin u
**yozilmadi** va bu **ongli qaror**: `ROADMAP.md` hamda `STATE.md`
ning yagona yozuvchisi — **orkestrator**. Ikkalasi ham bu yerdan
yozilsa, hali **merge qilinmagan** worktree ichidan faza «tugadi» deb
belgilanardi va ikki yozuv poygaga tushardi.

⚠ Tekshirildi: ROADMAP ning `**Plans**: 17 plans (8 to'lqin)` bandi va
17 qatorli reja ro'yxati **allaqachon o'rnida** (rejalashtirish
bosqichida yozilgan), ya'ni Task 3 ning o'sha yarmi **bajarilgan**.
Faza belgisi `- [ ]` **holicha** — yopish qarori qayta tekshiruvniki.

`REQUIREMENTS.md` esa **meniki** va u yangilandi.

## i18n — qaysi so'zlar QO'LDA tekshirildi

Bu rejada **yangi `uz_Cyrl` matni yozilmadi** — G-36 mavjud kalitlarni
**bog'laydi**, yangi matn qo'shmaydi. Shunga qaramay 07-05 bashorat
qilgan va 07-16 **jonli topgan** sinf (`kvitansiya` -> `квитанси…`)
bo'yicha `snapshots.alertKey.*` ning uchala locale'dagi 45 satri
ko'zdan kechirildi. Qo'lda tekshirilgan **o'zlashma so'zlar**:

| So'z | `uz-Cyrl` | Holat |
|---|---|---|
| `kvitansiya` | — | Bu guruhda **umuman yo'q** (u `outbox.py` matnida) |
| `anomaliya` | `аномалия` | ✅ to'g'ri (`ns`/`ts` klasteri yo'q) |
| `disk` | `диск` | ✅ |
| `NVR` | `NVR` | ✅ transliteratsiya qilinmagan (akronim) |
| `dayjest` | — | Bu guruhda yo'q; `digestStale` **kaliti**, matni «ҳисобот» |

⚠ Yangi o'zlashma so'z **kiritilmagani** uchun transliterator tuzog'i bu
rejada **tug'ilmadi**. G-36 esa kelajakda uni **qisman** ushlaydi: matn
**yo'qligini** ko'radi, **buzilganini** emas — bu chegara ochiq.

## Verification

| Buyruq | Natija |
|---|---|
| `pytest tests/integration/test_phase7_criteria.py -q` | ✅ **10 passed** |
| `ruff check` + `ruff format --check` + `mypy` (mezon moduli) | ✅ toza |
| `grep -c "unittest.mock" tests/integration/test_phase7_criteria.py` | ✅ **0** |
| `grep -c "bot-tests" tests/integration/test_phase7_criteria.py` | ✅ **1** |
| `node --test frontend/scripts/snapshot-copy.test.mjs` | ✅ **13 passed** |
| `npm --prefix frontend run lint` | ✅ toza |
| `node scripts/check-requirements-sync.mjs` | ✅ Done 39 · Pending 8 · Blocked 2 |
| `node scripts/check-validation-signoff.mjs` | ✅ Per-Task 19 · inson bandlari 7 |
| `npm run gate` × 3 | ✅ **exit 0** (1424 / 1263 / 1349 s) |
| `npm run gate:fast` | ✅ **80 s** (byudjet 200 s) |
| `npm run test:tenancy` (merged main) | ✅ **exit 0**, 731 test, 573 s |
| Sabotaj: `403` -> `RETRY` | ✅ SC#5 **QIZARDI** |
| Sabotaj: 16-chi matnsiz a'zo | ✅ G-36 **QIZARDI** (ikki darvoza) |

## Known Stubs

Yo'q. Bu reja yangi mahsulot yuzasi qurmaydi — u **o'lchov** beradi.

## Ochiq qolgan bandlar (keyingi egasiga)

1. **`alert-list.test.tsx` 07-14 ning to'rt yangi kalitini render qilmaydi**
   (`deferred-items.md` 1-bandining «Qo'shimcha» qismi). G-36 matn
   **mavjudligini** qo'riqlaydi, **chizilishini** emas — boshqa sinf.
2. **`deferred-items.md` 2-bandi** (`/reconciliation` ning ikki qo'shimcha
   so'rovi) — 8-fazaniki, tegilmadi.
3. **To'rtta yetim testcontainer** xostda qoldi (tiklandi, chunki men
   ularni to'xtatgan edim) — foydalanuvchi uchun tozalash nomzodi.
4. **`sbozor-cv-service-1` crash-loop** tiklandi va **davom etadi** —
   yechim ONNX artefaktini `ops/models/` ga qo'yish (`05-HUMAN-UAT.md` #3).
   Har qanday keyingi benchmark buni hisobga olishi shart.

## Self-Check: PASSED

Da'vo qilingan **yettala** fayl diskda mavjud
(`tests/integration/test_phase7_criteria.py`, `07-HUMAN-UAT.md`,
`07-17-SUMMARY.md`, `frontend/scripts/snapshot-copy.test.mjs`,
`package.json`, `.planning/REQUIREMENTS.md`, `07-VALIDATION.md`) va
**beshala** commit git tarixida topildi (`39ea2c7`, `155d51b`,
`46b3512`, `013a4b2`, `1f9a88c`).
