---
phase: 05-kamera-zonalari-cv-va-nazoratchi-tasdig-i
plan: 01
subsystem: infra
tags: [registries, rls, audit-triggers, pytest-markers, postgres, sha256, blind-audit, golden-set, wilson]

requires:
  - phase: 04-snapshot-pipeline
    provides: "`SNAPSHOT_*` reyestr uchligining shabloni, `PENDING_AUDIT_TRIGGERS` ikki tomonlama qulfining ochilib-yopilish sikli (`04-01`→`04-03`), `tests/fixtures/billable_probe.py` zond shabloni, `uq_snapshots_billable_anchor` langari (D-21 shu langarga osiladi)"
  - phase: 03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi
    provides: "`--strict-markers` ostida markerni KODDAN OLDIN e'lon qilish naqshi (`sim`/`slow`), `cameras` jadvali (`camera_zones` uchun kompozit FK nishoni)"
  - phase: 02-bozor-domeni-va-yangi-bozor-ustasi
    provides: "`AUDITED_TABLES` reyestri, `zones` jadvali (D-06 nom to'qnashuvining MANBAI), `stalls` (`camera_zones` uchun ikkinchi FK nishoni)"
  - phase: 01-poydevor-va-tenant-xavfsizligi
    provides: "tenancy meta-darvozalari, `FINANCIAL_TABLES` ning «reyestr bugun bo'sh, darvoza kelajakda yopiladi» falsafasi (oltin to'plamning AYNAN mexanizmi)"
provides:
  - "`OCCUPANCY_TENANT_TABLES` / `OCCUPANCY_AUDITED_TABLES` / `OCCUPANCY_DELETE_ORDER` reyestrlari — migratsiyadan OLDIN (W0-4, W0-6 reyestr qismi)"
  - "`AUDITED_TABLES` + `PENDING_AUDIT_TRIGGERS` ikki tomonlama qulfi `camera_zones`/`zone_reviews` uchun ochildi (W0-5) — `0018` uni yopadi"
  - "W0-3 O'LCHOVI: `AUDIT_SEED_SHA256_SUPPORTED = true`, `PGCRYPTO_ABSENT = true` — `0018` da `require_extension()` CHAQIRILMAYDI"
  - "`golden` va `model` pytest markerlari + `addopts` filtri `-m \"not hardware and not model\"` (W0-10)"
  - "`tests/fixtures/audit_seed_probe.py` — hosila urug' + hash tartibining zondi va `sample_ids()` yordamchisi"
  - "`tests/fixtures/golden_set/` + `scripts/eval-golden-set.py` — UXLAB YOTGAN aniqlik darvozasi (W0-9)"
  - "`MIN_N = 73` va `THRESHOLD = 0.85` — hisoblangan (Wilson n=73/p=0.95 -> 0.8738), tanlanmagan"
  - "`app.services.accuracy_report` import nuqtasi — 05-12 statistikani AYNAN shu yerga ulaydi"
affects: [05-05, 05-07, 05-11, 05-12, 05-15]

tech-stack:
  added: []
  patterns:
    - "Reyestr LITERAL, hosila EMAS — va bu MANBA MATNIDAN o'lchanadi, chunki import qilingan qiymat `tuple(reversed(...))` bilan literalni ajrata olmaydi"
    - "Uxlab yotgan darvoza: uyg'onish sharti bugun yoziladi, `source='karmana'` qatorlar kelganda KOD O'ZGARMASDAN qurollanadi"
    - "Zondda taqiqlangan funksiya nomi BIR JOYDA (`_PGCRYPTO_PROBE_SQL`); qarorning sababi BOSHQA faylda — skanerlanadigan fayl o'zini o'zi qizartirmasin"
    - "Marker `skip` emas, OCHIQ FILTR: artefakt yo'qligida test YIQILADI, jimgina o'tmaydi"

key-files:
  created:
    - tests/fixtures/audit_seed_probe.py
    - tests/tenancy/test_audit_seed_probe.py
    - tests/fixtures/golden_set/manifest.jsonl
    - tests/fixtures/golden_set/README.md
    - scripts/eval-golden-set.py
    - tests/unit/test_golden_harness.py
  modified:
    - migrations/entities/__init__.py
    - packages/sbozor-core/sbozor_core/schema_contract.py
    - tests/tenancy/test_meta.py
    - pyproject.toml

key-decisions:
  - "W0-3 O'LCHANDI: yadro `sha256(bytea)` kengaytmasiz ishlaydi va `pgcrypto` bazada YO'Q (`PostgreSQL 18.4 (Debian 18.4-1.pgdg13+1)`) -> A yo'li qulflandi, `00-extensions.sql` ga satr QO'SHILMAYDI"
  - "`OCCUPANCY_TENANT_TABLES` `ALL_TENANT_TABLES` ga BU REJADA qo'shilmadi — `04-01` da o'lchangan `UndefinedTable` sababi amal qiladi; qo'shish `0018` bilan bir oynada (05-05/T2), tetigi mexanik"
  - "Rejaning `OCCUPANCY_DELETE_ORDER != tuple(reversed(...))` mezoni O'LCHOV BILAN RAD ETILDI (u rejaning o'z ma'lumotida yolg'on) va MUSTAQILLIK darvozasi bilan almashtirildi — kuchliroq da'vo"
  - "`MIN_N = 73` `05-RESEARCH.md` §C.8.4 jadvalidan; `THRESHOLD = 0.85` hisoblangan — 0.90 qo'yilsa HAQIQATAN 95% aniq model minimal namunada o'ta olmasdi va yagona yo'l chegarani keyin TUSHIRISH bo'lardi"
  - "`golden` marker `addopts` filtriga QO'SHILMADI (standart to'plamda yuradi), `model` esa QO'SHILDI — birinchisi repodagi ma'lumot bilan ishlaydi, ikkinchisi repoda saqlanmaydigan artefaktni talab qiladi"
  - "Aniqlik foizi darvoza uxlagan holatda UMUMAN chop etilmaydi (T-05-04) — o'lchanmagan raqam ko'rilgan zahoti o'lchangan deb o'qilardi"

patterns-established:
  - "Ikki savolni bitta assertga yuklash xato XABARINI yolg'on qiladi — sabotaj buni ochib berdi va shart ikkiga bo'lindi"
  - "Sintetik yorliq FAQAT `geometry` dan; `karmana` yorlig'i esa HECH QACHON `geometry` dan emas — ikki yo'nalish ham qulflangan"
  - "Manifestni test o'z parallel o'quvchisi bilan emas, skriptning O'Z validatori bilan o'qiydi (aks holda ikkalasi birga xato bo'lganda yashil qolardi)"

metrics:
  duration: "~2.5 soat"
  completed: 2026-08-09
  tasks: 3
  commits: 3
  tests-added: 12
---

# Phase 5 Plan 01: Bandlik reyestrlari, ko'r audit urug'ining zondi va uxlab yotgan oltin to'plam — Summary

Bandlik domenining uchta reyestri, `PENDING_AUDIT_TRIGGERS` ikki tomonlama qulfi va `golden`/`model` markerlari **birinchi migratsiyadan oldin** joyiga qo'yildi; ko'r audit urug'ining SQL yo'li HAQIQIY `postgres:18.4` da o'lchandi (`sha256(bytea)` kengaytmasiz ishlaydi); oltin to'plam mashinasi **uxlab yotgan** holatda qurildi va `source='karmana'` qatorlar kelganda kodsiz uyg'onishi sabotaj bilan tasdiqlandi.

## Bajarilgan ishlar

### Task 1 — Reyestrlar, audit qulfi va ikki marker (W0-4/W0-5/W0-6/W0-10) — `2876449`

`migrations/entities/__init__.py` ga `SNAPSHOT_*` uchligining **aynan shaklida** uchta reyestr qo'shildi: `OCCUPANCY_TENANT_TABLES` (6), `OCCUPANCY_AUDITED_TABLES` (2), `OCCUPANCY_DELETE_ORDER` (6). `ALL_TENANT_TABLES` ga **ATAYIN qo'shilmadi** — `04-01` da o'lchangan `UndefinedTable` sababi izoh bilan yozildi va qarz `test_occupancy_registries_are_self_consistent` ning bazaga bog'langan sharti bilan mexanik ushlab turiladi.

`schema_contract.py::AUDITED_TABLES` ga `camera_zones` va `zone_reviews`, **ayni commitda** `test_meta.py::PENDING_AUDIT_TRIGGERS` ga ikkala nom qo'shildi. Natijada `test_audited_tables_have_trigger` `05-01` dan `05-05` gacha **uzluksiz yashil** turadi.

`pyproject.toml` ga `golden` va `model` markerlari; `addopts` `-m "not hardware and not model"` ga kengaytirildi.

### Task 2 — W0-3 zondi (`sha256(bytea)`, kengaytmasiz) — `379d217`

To'rt fakt HAQIQIY bazada alohida SQL bilan o'lchandi:

| Fakt | Natija |
|---|---|
| `AUDIT_SEED_SHA256_SUPPORTED` | **true** |
| `PGCRYPTO_ABSENT` | **true** |
| Bir xil urug' → ikki sessiyada AYNI namuna | **ha** (tartib ham teng) |
| Boshqa `round_no` → boshqa namuna | **ha** (kesishuvsiz) |

**Server:** `PostgreSQL 18.4 (Debian 18.4-1.pgdg13+1) on x86_64-pc-linux-gnu`.

Ya'ni `0018` da `require_extension()` **chaqirilmaydi** va `ops/db/init/00-extensions.sql` **o'zgarmaydi**. Zond ID larni `uuidv7()` bilan emas, **qadalgan** qiymatlar bilan yaratadi — aks holda 3- va 4-faktlar har yugurishda boshqa ma'lumot ustida o'lchanardi.

Qarorning sababi (nega `ORDER BY random()` va `setseed()` rad etilgan) **test faylining docstringida**, zondda emas — skanerlanadigan fayl o'zini o'zi qizartirmasligi uchun.

### Task 3 — Uxlab yotgan oltin to'plam darvozasi (W0-9) — `c3dcd9e`

`manifest.jsonl` — 8 sintetik yozuv (4 `occupied`, 4 `empty`), ular orasida **botiq (concave) poligon** holati ham bor: `(0.70, 0.70)` nuqtasi L-shaklning tishida, ya'ni sodda chegara-quti tekshiruvi uni xato aniqlagan bo'lardi. **Sakkizala yorliq mustaqil ray-casting bilan qayta hisoblab tekshirildi** — hech biri qo'lda «to'g'ri ko'rinadi» deb qabul qilinmadi.

`scripts/eval-golden-set.py` — sxema validatori (noma'lum kalit/yetishmagan maydon → `SystemExit`), `VerdictProvider` interfeysi (D-02 choki, amalga oshirilishsiz) va uxlab yotgan darvoza. Statistika **import qilinadi** (`app.services.accuracy_report`, 05-12), takrorlanmaydi.

## Deviations from Plan

### 1. `[Rule 1 - Bug]` Rejaning `!=` qabul mezoni o'z ma'lumotida YOLG'ON

- **Topildi:** Task 1
- **Muammo:** Reja `OCCUPANCY_DELETE_ORDER != tuple(reversed(OCCUPANCY_TENANT_TABLES))` ni «testda literal tasdiqlanadi» deb talab qildi. Rejaning O'ZI bergan ikki ro'yxat esa aynan bir-birining teskarisi. **O'lchandi:** `OCCUPANCY_DELETE_ORDER == tuple(reversed(OCCUPANCY_TENANT_TABLES))` → `True`. 4-fazada mezon ROST edi, chunki `alert_events` FK zanjirida turmasdi; bu domenda zanjirdan chetdagi jadval yo'q, ya'ni ustma-ustlik **tasodif**.
- **Tuzatish:** Mezonni «qondirish»ning yagona yo'li ro'yxatlardan birini ataylab noto'g'ri tartibda yozish bo'lardi — o'shanda `0019` kaskadi o'z chet el kalitiga urilardi. Mezonning NIYATI esa §S-2 ning «ALOHIDA RO'YXAT, hosila emas» qoidasi. Shuning uchun `test_occupancy_delete_order_is_declared_not_derived` **tengsizlikni emas, MUSTAQILLIKNI** o'lchaydi: MANBA MATNIDAN `OCCUPANCY_DELETE_ORDER = tuple(...)` shaklini qidiradi. Bu **kuchliroq** da'vo — ustma-ustlik tasodifan yo'qolganda ham kuchda qoladi, `!=` esa o'sha kundan boshlab hech nima demay qo'yardi.
- **Fayllar:** `tests/tenancy/test_meta.py`, `migrations/entities/__init__.py`
- **Commit:** `2876449`

### 2. `[Rule 2 - Correctness]` Darvozada `assert` o'rniga `SystemExit`

- **Topildi:** Task 3
- **Muammo:** Reja darvozani `assert accuracy_lower_wilson_bound >= THRESHOLD` shaklida yozgan. `scripts/` `tests/**` emas, ya'ni ruff `S101` uni rad etadi — lekin asosiy sabab boshqa: **`python -O` ostida `assert` butunlay o'chiriladi**, ya'ni darvoza bitta bayroq bilan jimgina yo'qolardi.
- **Tuzatish:** `_fail()` → `SystemExit`, va CLI chiqish kodi. Sabab funksiya docstringida yozildi.
- **Fayllar:** `scripts/eval-golden-set.py`
- **Commit:** `c3dcd9e`

### 3. `[Rule 1 - Bug]` Skript yuklovchisi `sys.modules` siz yiqilardi

- **Topildi:** Task 3 (birinchi yugurishda)
- **Muammo:** `spec_from_file_location` + `exec_module` bilan yuklangan modulda `@dataclass` `AttributeError: 'NoneType' object has no attribute '__dict__'` berdi — skriptda `from __future__ import annotations` bor, ya'ni `@dataclass` annotatsiyalarni yechish uchun `sys.modules[cls.__module__]` ga murojaat qiladi.
- **Tuzatish:** `sys.modules[spec.name] = module` — `exec_module` dan OLDIN, sababi izohda.
- **Fayllar:** `tests/unit/test_golden_harness.py`
- **Commit:** `c3dcd9e`

### 4. `[Rule 1 - Bug]` Ikkita assert uyg'ongan holatda YOLG'ON xabar berardi

- **Topildi:** Task 3, **sabotaj paytida** (quyida)
- **Muammo:** (a) `labeled_by == "geometry"` da'vosi BUTUN manifestga qo'yilgan edi — `karmana` qatori qo'shilgan zahoti u «o'zini-o'zi tasdiqlash tuzog'i» deb qizarardi, holbuki nazoratchi yorliqlagan qator aynan KUTILGAN narsa; (b) `len(synthetic) == len(rows)` sharti «noma'lum manba bor: ['karmana', 'synthetic']» deb qizarardi, ya'ni RUXSAT ETILGAN manbani noma'lum deb atardi.
- **Tuzatish:** (a) da'vo sintetik qatorlarga cheklandi va teskari yo'nalish qo'shildi (`karmana` yorlig'i HECH QACHON `geometry` dan emas); (b) shart ikkiga bo'lindi — «noma'lum manba» va «darvoza uxlayapti» alohida. Natijada uyg'ongan holatda **aynan bitta** test qizaradi va xabari uchta keyingi qadamni nomlaydi.
- **Fayllar:** `tests/unit/test_golden_harness.py`
- **Commit:** `c3dcd9e`

### 5. `[Rule 3 - Blocking]` Worktree'da gitignore qilingan lokal konfiglar yo'q edi

- **Topildi:** Boshlanishda
- **Muammo:** `docker compose --profile test` `storage` konteyneri `fail to read /etc/seaweedfs/s3.json: is a directory` bilan yiqildi. `ops/seaweedfs/s3.json` va `.env` — gitignore qilingan LOKAL fayllar; worktree'da ular yo'q edi va Docker bind-mount manbasi topilmagach o'rniga **katalog** yaratdi.
- **Tuzatish:** Katalog o'chirildi, ikkala fayl asosiy repodan nusxalandi. **Birorta kuzatiladigan fayl o'zgarmadi** (`git status` bo'sh).
- **Fayllar:** yo'q (gitignore qilingan lokal fayllar)

## Sabotage o'lchovlari — nima QIZARDI va nima YASHIL QOLDI

Har sabotaj snapshotdan `cp` bilan qaytarildi (`git checkout --` ishlatilmadi).

| # | Sabotaj | Kutilgan | NATIJA |
|---|---|---|---|
| A | `camera_zones` ni `PENDING_AUDIT_TRIGGERS` dan olib tashlash | `regressed` bilan qizil | ✅ `test_audited_tables_have_trigger` qizardi: «`AUDITED_TABLES` da bor, lekin audit triggeri YO'Q: ['camera_zones']» |
| B | `OCCUPANCY_DELETE_ORDER = tuple(reversed(...))` | manba-matn darvozasi qizil | ✅ `test_occupancy_delete_order_is_declared_not_derived` qizardi<br>⚠ **`test_occupancy_registries_are_self_consistent` YASHIL QOLDI** — tuzilmaviy tekshiruvlar buni ushlay OLMAYDI, chunki hosila qiymat bugun aynan bir xil mazmun beradi. Deviatsiya #1 ning butun sababi shu. |
| C | `ORDER BY` dan urug'ni olib tashlash | 4-fakt qizil | ✅ `test_a_different_round_number_draws_a_different_sample` qizardi<br>⚠ **3-fakt («ikki sessiyada bir xil») YASHIL QOLDI** — ya'ni nazorat holatisiz «qayta chiqariladi» degan xulosa aslida «urug' umuman ishlamaydi» degani bo'lardi |
| D | Manifestga `source="karmana"` qatori qo'shish | darvoza «uyg'ondi» deb qizil | ✅ qizardi — lekin **avval UCHTA test qizardi va ikkitasining xabari YOLG'ON edi** (deviatsiya #4). Tuzatishdan keyin: aynan bitta test, aniq xabar. |

**Sabotaj B va C ning qiymati aynan «yashil qolgan» ustunida:** ikkalasi ham tuzilmaviy tekshiruv yolg'iz o'zi yetarli emasligini o'lchab ko'rsatdi.

## Verification

| Tekshiruv | Natija |
|---|---|
| `pytest -q` (to'liq, `sim:up` bilan) | ✅ **1901 yig'ildi, 0 nosoz** (bazaviy 1889 + 12 yangi) |
| `pytest tests/tenancy -q` | ✅ **474** (bazaviy 472 + 2) |
| `pytest tests/tenancy/test_audit_seed_probe.py -q` | ✅ 4 |
| `pytest tests/unit/test_golden_harness.py -m golden -q` | ✅ 6 |
| `pytest --collect-only -m golden` / `-m model` | ✅ yig'ilish xatosisiz (`--strict-markers`) |
| `ruff check . && ruff format --check . && mypy .` | ✅ toza (248 fayl) |
| `python scripts/eval-golden-set.py` | ✅ «darvoza UXLAYAPTI — 0/73», foiz chop etilmadi |

**Qabul mezonlari (grep bilan o'lchangan):**

| Mezon | Kutilgan | O'lchandi |
|---|---|---|
| `grep -cE "setseed\|random\(\)" tests/fixtures/audit_seed_probe.py` | 0 | **0** |
| `grep -c "digest(" tests/fixtures/audit_seed_probe.py` | 1 | **1** |
| `wc -l tests/fixtures/golden_set/manifest.jsonl` | ≥6 | **8** |
| `grep -c 'karmana' scripts/eval-golden-set.py` | ≥1 | **14** |
| `grep -cE '\bMIN_N\b\|\bTHRESHOLD\b' scripts/eval-golden-set.py` | ≥2 | **6** |
| `grep -cE "^\s*def (wilson\|confusion)" scripts/eval-golden-set.py` | 0 | **0** |
| `karmana` yozuvlari soni | 0 | **0** |

⚠ **To'liq to'plamning birinchi yugurishida 4 test yiqildi va sabab MENING O'ZGARISHLARIM EMAS:** `test_alerting.py` (2) va `test_live_view_e2e.py` (2) `httpx.ConnectError: Name or service not known` berdi, chunki buyruq `npm run sim:up` siz ishga tushirilgan edi — `nvr-sim` `profiles: ["sim"]` ostida va `--profile test` uni ko'tarmaydi. `npm run gate` zanjiri `sim:up` ni BIRINCHI bajaradi. Sim ko'tarilgandan keyin to'plam **to'liq yashil**. Ikkala fayl ham men o'zgartirgan birorta belgini import qilmaydi (grep bilan tasdiqlandi).

## Keyingi rejalar uchun ochiq bandlar

- **`05-05` (0018/0019):** (a) `OCCUPANCY_TENANT_TABLES` ni `ALL_TENANT_TABLES` ga `0018` BILAN BIR COMMITDA qo'shish; (b) `camera_zones`/`zone_reviews` ni `PENDING_AUDIT_TRIGGERS` dan O'CHIRISH; (c) `audit_rounds` docstringiga W0-3 natijasini `AUDIT_SEED_SHA256_SUPPORTED` / `PGCRYPTO_ABSENT` nomlari bilan ko'chirish; (d) `require_extension()` ni **chaqirmaslik**; (e) `0019` da `OCCUPANCY_DELETE_ORDER` ni kaskadga **snapshot blokidan OLDIN** qo'shish.
- **`05-12`:** `app/services/accuracy_report.py` da `accuracy_lower_wilson_bound(correct, total) -> float` ni e'lon qilish (skript aynan shu nomni kutadi) va `VerdictProvider` ni ONNX + `PolygonZone` bilan ulash.
- **`05-11`:** `sample_ids()` ning SQL yo'li (`_SAMPLE_SQL`) — `jobs/audit_draw.py` uchun tayyor shakl.
- **Real ma'lumot kelganda:** `MIN_N`/`THRESHOLD` ATAYIN tasdiqlanadi; `test_the_accuracy_gate_is_asleep_today` qizaradi va uyg'ongan holatga moslanadi.

## Known Stubs

`scripts/eval-golden-set.py::VerdictProvider` — **ataylab amalga oshirilmagan interfeys** (Protocol). Reja uni aynan shunday talab qiladi: haqiqiy provayder 05-12 da ulanadi, interfeys esa bugun turadi, chunki D-02 seam'ni shu joyda belgilaydi. Darvoza uyg'onib provayder topilmasa skript **baland ovozda yiqiladi** (`SystemExit`), jimgina o'tmaydi — ya'ni stub yashil natija bera olmaydi.

`app.services.accuracy_report` — bu rejada mavjud EMAS; import `importlib` bilan kechiktirilgan va faqat darvoza qurollanganda bajariladi. 05-12 uni yozadi.

## Threat Flags

Yangi xavfsizlik yuzasi topilmadi: bu reja tarmoq endpointi, autentifikatsiya yo'li, fayl kirish naqshi yoki ishonch chegarasidagi sxema o'zgarishini kiritmaydi. `<threat_model>` ning to'rtala bandi rejalashtirilgandek qoplandi (T-05-01 → Task 2 grep darvozalari; T-05-02 → Task 1 ikki tomonlama qulf; T-05-03 → `golden_set/README.md` ning operatsion tartibi; T-05-04 → uxlagan darvoza foiz chop etmaydi).

## Self-Check: PASSED

- Yaratilgan/o'zgartirilgan 10 fayl + SUMMARY — **hammasi mavjud** (`ls` bilan tasdiqlandi)
- `2876449`, `379d217`, `c3dcd9e` — **uchala commit ham git tarixida mavjud**
- To'liq to'plam `sim:up` bilan qayta yugurtirildi: **0 nosoz**
