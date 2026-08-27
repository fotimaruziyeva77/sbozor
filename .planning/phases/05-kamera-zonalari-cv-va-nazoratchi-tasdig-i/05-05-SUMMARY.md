---
phase: 05-kamera-zonalari-cv-va-nazoratchi-tasdig-i
plan: 05
subsystem: database
tags: [postgres, rls, migrations, immutability-triggers, composite-fk, billing-anchor, blind-audit, sqlalchemy]

requires:
  - phase: 04-snapshot-pipeline
    provides: "`uq_snapshots_billable_anchor` langari (D-21 aynan shunga osiladi), `0014`/`0015` migratsiya juftligining shabloni, `snapshot_domain` seed'i, `AUDIT_IMMUTABLE` shakli"
  - phase: 03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi
    provides: "`cameras (market_id, id)` kompozit FK nishoni, `market_delete_draft()` to'liqlik darvozasi (`pg_catalog` dan), `0012`->`0013` kaskad juftligi"
  - phase: 02-bozor-domeni-va-yangi-bozor-ustasi
    provides: "`stalls (market_id, id)` nishoni, `zones` jadvali (D-06 nom to'qnashuvining MANBAI), `tariff_past_immutable()` ning qoralama-bozor istisnosi (o'lchangan zaruriyat)"
  - phase: 01-poydevor-va-tenant-xavfsizligi
    provides: "tenant meta-darvozalari, `audit_log` o'zgarmasligining to'rt qatlami, `users` jadvali"
provides:
  - "`0018_occupancy_domain` — oltita tenant jadvali, RLS, audit, ikki o'zgarmaslik qo'riqchisi, ikki `SECURITY DEFINER` tik yuzasi"
  - "`0019_market_delete_occupancy` — kaskadning UCHINCHI kengaytmasi (`OCCUPANCY_DELETE_ORDER` bo'yicha, snapshot blokidan OLDIN)"
  - "`models/occupancy.py` — olti model, to'rt enum va ularning `CHECK` ifodalari (05-06…05-12 shulardan import qiladi)"
  - "D-21 langari ISHLATILDI: `occupancy_events` -> `snapshots (id, is_billable)` + `CHECK (snapshot_is_billable)`"
  - "D-17.3 `CHECK` + `queue_kind` LANGARI — «ko'r, lekin ko'rsatilgan» ikki qatlamda imkonsiz"
  - "`uq_snapshots_market_id_id` — 4-fazadagi yetishmayotgan kompozit FK nishoni"
  - "`tests/fixtures/occupancy_domain.py` — ikki bozorli seed (05-06…05-15 shundan foydalanadi)"
  - "`PENDING_AUDIT_TRIGGERS` BO'SHATILDI; `ALL_TENANT_TABLES` kengaytirildi"
affects: [05-06, 05-07, 05-08, 05-09, 05-10, 05-11, 05-12, 05-15]

tech-stack:
  added: []
  patterns:
    - "LANGAR NAQSHI IKKINCHI MARTA: denormalizatsiya qilingan ustun MANBASIGA kompozit FK bilan qadaladi (`zone_reviews.queue_kind` -> `review_assignments (id, queue_kind)`), aynan `snapshots (id, is_billable)` shaklida"
    - "O'ZGARMASLIK — VAQT SHARTISIZ, LEKIN QORALAMA `DELETE` ISTISNOSI BILAN: `UPDATE` har doim rad etiladi, `DELETE` faqat `market_delete_draft()` yo'lida o'tadi (istisno yuzasi `tariffs` nikidan ikki barobar tor)"
    - "`CHECK` nomlari migratsiyada QISQA yoziladi: `ck` konvensiyasida `%(constraint_name)s` tokeni bor, ya'ni to'liq nom IKKI KARRA prefiks beradi va xesh bilan kesiladi"
    - "`CASE WHEN jsonb_typeof(...) = 'array'` — `CHECK` lar aniqlanmagan tartibda baholanadi, ya'ni tip qo'riqchisi UZUNLIK ifodasining ICHIDA bo'lishi kerak"
    - "Seed kadrni SIFAT bo'yicha bazadan ajratadi, qo'shni faylning ro'yxat TARTIBIGA tayanmaydi"

key-files:
  created:
    - packages/sbozor-core/sbozor_core/models/occupancy.py
    - migrations/versions/0018_occupancy_domain.py
    - migrations/versions/0019_market_delete_occupancy.py
    - tests/fixtures/occupancy_domain.py
    - tests/tenancy/test_occupancy_domain_meta.py
    - tests/integration/test_occupancy_immutable.py
    - tests/integration/test_occupancy_billing_fence.py
  modified:
    - packages/sbozor-core/sbozor_core/enums.py
    - packages/sbozor-core/sbozor_core/models/__init__.py
    - packages/sbozor-core/sbozor_core/models/snapshot.py
    - migrations/entities/__init__.py
    - migrations/entities/functions.py
    - migrations/entities/triggers.py
    - tests/tenancy/test_meta.py
    - tests/integration/test_market_delete_guard.py

key-decisions:
  - "O'ZGARMASLIK VAQT SHARTISIZ, LEKIN QORALAMA `DELETE` ISTISNOSI SAQLANDI — butunlay shartsiz shakl `0019` kaskadini HAR QORALAMA uchun `RAISE EXCEPTION` bilan yiqitardi (rejaning ikki qismi bir-birini inkor qilardi). Istisno FAQAT `DELETE` ga berildi, ya'ni `tariff_past_immutable()` nikidan IKKI BAROBAR TOR"
  - "`uq_snapshots_market_id_id` 4-fazaga QO'SHILDI — usiz `0018` `InvalidForeignKeyError` bilan yiqiladi: `snapshots` 4-fazada zanjirning OXIRI edi va unga hech kim tayanmasdi"
  - "`zone_reviews.queue_kind` `review_assignments (id, queue_kind)` ga KOMPOZIT FK bilan qadaldi — usiz D-17.3 ning `CHECK` i o'z nusxasiga ishonardi va nusxani `'uncertain'` deb yozish uni chetlab o'tardi (sabotaj bilan o'lchandi)"
  - "`CHECK (purpose <> 'eval' OR queue_kind = 'blind_audit')` — noaniq navbat TANLANGAN namuna va uning javoblari aniqlik hisobotiga kira olmaydi (D-14 sxemada)"
  - "`stall_slot_occupancy.verdict` — `OccupancyVerdict` NING SUPERSETI (`no_coverage` qo'shiladi), `no_coverage_is_paired` bilan `resolution_source` ga bog'landi (D-22 sxemada)"
  - "`occupancy_day_close_markets()` BARCHA faol bozorlarni qaytaradi, hodisasi borlarini EMAS — «hodisasi bor» filtri qamrovsiz bozorda `no_coverage` materializatsiyasini JIMGINA o'chirardi"
  - "Migratsiyada `CHECK` nomlari QISQA (`ck_` prefiksisiz) — `0014` uslubi ikki karra prefiks va xeshli kesilish berardi (o'lchandi)"

patterns-established:
  - "Statik darvoza kaskad TARTIBINI ko'rmaydi — sabotaj C buni uchinchi marta o'lchadi: matn to'liq, chaqiruv `ForeignKeyViolation`"
  - "Tuzilmaviy (meta) darvoza trigger TANASINI ko'rmaydi — sabotaj A: `BEFORE UPDATE OR DELETE` shakli o'zgarmagani uchun meta-test yashil qoldi, xulq testi qizardi"
  - "Denormalizatsiya qilingan ustunning HALOLLIGI FK langari bilan qulflanadi; usiz `CHECK` o'z nusxasiga ishonadi (sabotaj D)"

requirements-completed: []
requirements-advanced: [AI-01, AI-02, AI-04, AI-05, AI-06]
# ⚠ ATAYIN BO'SH. Bu reja beshala talabning SXEMA qismini yetkazadi, lekin
# hech birini YOPMAYDI: AI-01 poligon muharririni (05-06), AI-02 detektorni
# (05-07/05-08), AI-04/AI-05/AI-06 esa hisobot va kun yopilishini (05-11,
# 05-12) talab qiladi. `05-15` — fazaning yopilish rejasi va u oltala
# talabni DALIL BILAN belgilaydi. Bu 3-fazadagi 03-01 qarorining aynan
# takrori («talablar faza darajasida, dalil bilan belgilanadi»).
#
# ⚠ O'LCHANDI: `requirements mark-complete AI-01 AI-02 AI-04 AI-05 AI-06`
# chaqirildi va DARHOL QAYTARILDI — u beshtasini `Complete` qilib
# belgilagan edi, holbuki 05-06…05-15 hali bajarilmagan. `npm run
# requirements:check` qaytarishdan keyin MOS: Done 16 · Pending 32 ·
# Blocked 1 (o'zgarishsiz).

duration: ~3 soat
completed: 2026-08-09
---

# Phase 5 Plan 05: Bandlik domenining sxemasi, ikki o'zgarmaslik qo'riqchisi va kaskadning uchinchi kengaytmasi — Summary

Oltita tenant jadvali, D-21 billing langari (4-fazadan **uch satr aynan ko'chirildi**), D-17.3 ning ikki qatlamli ko'r-audit `CHECK` i va `market_delete_draft()` kaskadining uchinchi kengaytmasi — fazaning **kafolatlari endi kodda emas, sxemada**; to'rtta sabotaj bilan har biri alohida o'lchandi.

## Bajarilgan ishlar

### Task 1 — To'rt enum va olti model — `1fe35ea`

`enums.py` ga `OccupancyVerdict` / `ReviewQueueKind` / `ReviewPurpose` / `ResolutionSource`.
`models/occupancy.py` (1 028 qator) — `CameraZone`, `OccupancyEvent`, `AuditRound`,
`ReviewAssignment`, `ZoneReview`, `StallSlotOccupancy`. Barcha `CHECK` ifodalari
enum'dan **hosila** (`_quoted()` — loyihada beshinchi marta takrorlangan),
`TimestampMixin` ikkala o'zgarmas jadvalga **qo'yilmadi**.

**O'lchangan qabul mezonlari:** `snapshot_is_billable` `nullable=False` ✅;
`hasattr(OccupancyEvent, "updated_at") is False` ✅;
`hasattr(ZoneReview, "updated_at") is False` ✅;
`hasattr(CameraZone, "updated_at") is True` ✅; `mypy .` toza ✅.

### Task 2 — `0018`, ikki qo'riqchi, ikki tik yuzasi — `5a9b922`

| Element | Holat |
|---|---|
| Oltita jadval + RLS + policy + audit (ikkitasiga) | ✅ |
| `occupancy_event_immutable()` / `zone_review_immutable()` | ✅ `BEFORE UPDATE OR DELETE` |
| `audit_draw_due_markets()` / `occupancy_day_close_markets()` | ✅ `SECURITY DEFINER`, faqat `uuid`+`integer` |
| `ALL_TENANT_TABLES` += `OCCUPANCY_TENANT_TABLES` | ✅ `0018` bilan bir commitda |
| `PENDING_AUDIT_TRIGGERS` | ✅ `frozenset()` — ikki tomonlama qulf yopildi |
| `require_extension()` chaqiruvi | ✅ **0** (`grep -cE "^\s*require_extension\("`) |
| Bazadagi kengaytmalar | ✅ **faqat `plpgsql`, `btree_gist`** (W0-3 xulqiy isboti) |

### Task 3 — `0019` kaskad, seed va uchta xulq darvozasi — `846e4cf`

`MARKET_DELETE_DRAFT` tanasiga oltita `DELETE` **snapshot blokidan OLDIN**;
`0019` `0015` shablonida (`MARKET_DELETE_DRAFT_WITHOUT_OCCUPANCY` muzlatilgan
nusxasi bilan). `audit_log` kaskadga **qo'shilmadi**.

`tests/fixtures/occupancy_domain.py` — ikki bozorli seed; A bozorida eskirgan
zona, ikkita verdikt, javobli ko'r audit va **javobsiz** noaniq navbat
(AI-06 ning kirish holati), ikki xil `resolution_source`.

31 yangi test: `test_occupancy_immutable.py` (8), `test_occupancy_billing_fence.py` (4),
`test_occupancy_domain_meta.py` (10), `test_market_delete_guard.py` (+1).

## Deviations from Plan

### 1. `[Rule 3 - Blocking]` `snapshots` da `UNIQUE (market_id, id)` YO'Q EDI

- **Topildi:** Task 2, birinchi `alembic upgrade head` da
- **Muammo:** `asyncpg.exceptions.InvalidForeignKeyError: there is no unique
  constraint matching given keys for referenced table "snapshots"`.
  `occupancy_events` unga **ikki xil** FK bilan tayanadi va ular ikki xil
  savolga javob beradi — tenant chegarasi (`(market_id, snapshot_id)`) va
  billing chegarasi (`(snapshot_id, snapshot_is_billable)`). 4-fazada
  `snapshots` zanjirning **oxiri** edi, ya'ni birinchisining nishoni umuman
  yaratilmagan edi.
- **Tuzatish:** `Snapshot.__table_args__` ga `uq_snapshots_market_id_id` va
  `0018` ga `op.create_unique_constraint(...)` (+ `downgrade()` da xom SQL
  bilan `DROP`). Birinchi FK'ni tashlab, faqat billing langariga tayanish
  **rad etildi**: u holda A bozorining bandlik dalili B bozorining kadriga
  bog'lana olardi (T-05-20).
- **Fayllar:** `models/snapshot.py`, `migrations/versions/0018_occupancy_domain.py`
- **Commit:** `5a9b922`

### 2. `[Rule 3 - Blocking]` SHARTSIZ o'zgarmaslik `0019` kaskadini yiqitardi

- **Topildi:** Task 2 (loyihalash paytida), `TARIFF_PAST_IMMUTABLE` docstringi bilan solishtirganda
- **Muammo:** Reja qo'riqchi tanasida «faqat `RAISE EXCEPTION`» talab qiladi.
  `market_delete_draft()` esa ikkala jadvaldan ham `DELETE` qiladi (`0019`),
  ya'ni butunlay shartsiz qo'riqchi **har qoralama bozorni o'chirishni**
  `RAISE EXCEPTION` bilan bloklardi — rejaning ikki qismi bir-birini inkor
  qilardi va tashlab ketilgan qoralamalar bazada abadiy to'planardi.
  Bu YANGI muammo emas: `TARIFF_PAST_IMMUTABLE` uni 2-fazada **aynan shu
  shaklda o'lchagan** va `cleanup_market_domain()` / `cleanup_two_markets()`
  o'shandan beri `is_active = false` qadamini bajaradi.
- **Rad etilgan uch muqobil:** `session_replication_role = replica`
  (T-01-33 ning aynan o'zi); `ALTER TABLE ... DISABLE TRIGGER` kaskad ichida
  (`ACCESS EXCLUSIVE` lock, qo'riqchi butun baza uchun o'chadi);
  `current_user = 'sbozor_owner'` sharti (EGANI istisno qilardi, holbuki
  `test_audit_immutable.py` ning butun falsafasi qo'riqchi **egaga qarshi**
  ham ishlashi).
- **Tuzatish:** Istisno **faqat `DELETE`** ga berildi va **faqat qoralama
  bozor** uchun. `UPDATE` har doim, har qanday bozorda rad etiladi — ya'ni
  §S-3 ning «vaqt sharti YO'Q» talabi to'liq bajarildi va istisno yuzasi
  `tariffs` nikidan **ikki barobar tor**. Farq
  `test_draft_market_exception_covers_delete_only` bilan qulflandi.
- **Fayllar:** `migrations/entities/triggers.py`
- **Commit:** `5a9b922`

### 3. `[Rule 1 - Bug]` Migratsiyadagi `CHECK` nomlari IKKI KARRA prefiks olardi

- **Topildi:** Task 2, birinchi `alembic upgrade head` chiqishida
- **Muammo:** `0014` uslubida to'liq nom yozilganda natija
  `ck_occupancy_events_ck_occupancy_events_confidence_in_u_f713` bo'ldi —
  ya'ni SQLAlchemy nom konvensiyasini **allaqachon nomlangan** `CHECK` ga ham
  qo'llaydi (`ck` kalitida `%(constraint_name)s` tokeni bor) va uzun nomlarni
  xesh bilan kesadi.
- **Tuzatish:** `0018` da `CHECK` nomlari **qisqa** yoziladi (modeldagi bilan
  aynan bir xil), qolgan uch kalit (`uq`, `fk`, `ix`) da bu token yo'q va
  ularning to'liq nomlari o'zgarishsiz o'tadi. Natijada bazadagi `CHECK`
  nomlari modeldagilar bilan **teng** va meta-testlar bitta manbadan qidiradi.
  ⚠ `0014` dagi mavjud nomlar **tegilmadi** (qamrov chegarasi).
- **Fayllar:** `migrations/versions/0018_occupancy_domain.py`
- **Commit:** `5a9b922`

### 4. `[Rule 1 - Bug]` `uq_stall_slot_occupancy_...` nomi 63 baytdan uzun edi

- **Topildi:** Task 2, ikkinchi urinishda
- **Muammo:** `sqlalchemy.exc.IdentifierError: Identifier
  'uq_stall_slot_occupancy_market_id_stall_id_business_date_slot_time'
  exceeds maximum length of 63 characters` (66 belgi).
- **Tuzatish:** `uq_stall_slot_occupancy_market_stall_day_slot` (45) —
  model va migratsiyada birdan. Sabab ikkala joyda ham izohda.
- **Fayllar:** `models/occupancy.py`, `0018_occupancy_domain.py`
- **Commit:** `5a9b922`

### 5. `[Rule 2 - Correctness]` `zone_reviews.queue_kind` uchun LANGAR qo'shildi

- **Topildi:** Task 1 (loyihalash), sabotaj D bilan **o'lchandi**
- **Muammo:** Reja D-17.3 ni yolg'iz `CHECK` bilan qo'yadi. `CHECK` esa
  boshqa jadvalni o'qiy olmaydi, ya'ni u `zone_reviews` dagi
  **denormalizatsiya qilingan** `queue_kind` nusxasiga tayanadi. Nusxani
  `'uncertain'` deb yozib `shown_ai_verdict = true` ni bemalol o'tkazish
  mumkin edi — ya'ni kafolat **bitta `INSERT` bilan** chetlab o'tilardi.
- **Tuzatish:** `review_assignments` ga `UNIQUE (id, queue_kind)` langari va
  `zone_reviews` ga `(review_assignment_id, queue_kind)` kompozit FK — aynan
  `snapshots (id, is_billable)` naqshining takrori. `INDEX_EXCEPTIONS` ga
  sabab bilan qo'shildi.
- **Fayllar:** `models/occupancy.py`, `0018_occupancy_domain.py`, `test_meta.py`
- **Commit:** `5a9b922`

### 6. `[Rule 2 - Correctness]` `eval` namunasi FAQAT ko'r auditdan (D-14 sxemada)

- **Muammo:** Reja `purpose` ni faqat `CHECK ... IN (...)` bilan cheklaydi.
  U holda noaniq navbatning javoblari (TANLANGAN, biased namuna) `eval`
  deb belgilanib **aniqlik hisobotiga** kirishi mumkin bo'lardi — kelajakda
  «hamma javoblar hisobga kirsin, ma'lumot isrof bo'lmasin» degan oqilona
  ko'rinuvchi o'zgarish D-14 ni jimgina buzardi.
- **Tuzatish:** `CHECK (purpose <> 'eval' OR queue_kind = 'blind_audit')`.
  D-15 (inson javobi bandlikni ham tuzatadi) buzilmaydi: tuzatish
  `stall_slot_occupancy` orqali boradi va u `purpose` ga umuman qaramaydi.
- **Fayllar:** `models/occupancy.py`, `0018_occupancy_domain.py`
- **Commit:** `5a9b922`

### 7. `[Rule 2 - Correctness]` `no_coverage` ikkala ustunda birdan (D-22 sxemada)

- **Muammo:** `aggregate_stall_slot([])` -> `('no_coverage', 'no_coverage')`
  (05-12). Reja `stall_slot_occupancy.verdict` uchun `CHECK` shaklini
  belgilamaydi. `(verdict='empty', resolution_source='no_coverage')` qatori
  mumkin bo'lardi va u hisobotda **«bo'sh»** hisoblagichiga tushardi — ya'ni
  D-22 konventsiyaga aylanardi.
- **Tuzatish:** `SLOT_VERDICT_VALUES` = `OccupancyVerdict` + `no_coverage`
  (ikkala enum'dan **hosila**) va
  `CHECK ((verdict='no_coverage') = (resolution_source='no_coverage'))`.
- **Fayllar:** `models/occupancy.py`, `0018_occupancy_domain.py`
- **Commit:** `5a9b922`

### 8. `[Rule 2 - Correctness]` `occupancy_day_close_markets()` BARCHA faol bozorlarni qaytaradi

- **Muammo:** «Hodisasi bor bozorlar» filtri tabiiy ko'rinadi va aynan
  JIM YIQILISHNI tug'dirardi: kameralari buzilgan (yoki birorta zona
  chizilmagan) bozor uchun hodisa yo'q -> bozor qaytarilmaydi ->
  `stall_slot_occupancy` ga 0 qator -> hisobot bo'sh -> «hammasi joyida».
  D-22 esa aynan buning teskarisini talab qiladi.
- **Tuzatish:** Shart **atayin yo'q**; `event_count` fan-out o'lchami sifatida
  qaytariladi va `0` qiymat xato emas. Sabab funksiya docstringida
  (`capture_due_markets()` ning ikkinchi disjunkti bilan bir sinf dalil).
- **Fayllar:** `migrations/entities/functions.py`
- **Commit:** `5a9b922`

### 9. `[Rule 2 - Correctness]` `CASE` bilan himoyalangan poligon uzunligi

- **Muammo:** Reja `CHECK (jsonb_array_length(polygon) >= 3)` ni talab
  qiladi. PostgreSQL `CHECK` larni **aniqlanmagan tartibda** baholaydi, ya'ni
  `{"a": 1}` yozilganda `polygon_is_array` dan oldin uzunlik ifodasi
  baholanib `22023 cannot get array length of a non-array` berishi mumkin —
  rad etish `23514` emas, boshqa sinf xato bo'lardi va chaqiruvchi (05-06)
  uni 409 ga aylantira olmasdi.
- **Tuzatish:** `CASE WHEN jsonb_typeof(polygon) = 'array' THEN
  jsonb_array_length(polygon) ELSE -1 END` — har qanday kirish
  `polygon_min_vertices` da toza `23514` beradi.
- **Fayllar:** `models/occupancy.py`
- **Commit:** `1fe35ea`

### 10. `[Rule 3 - Blocking]` `AuditRound` ga `UNIQUE (market_id, id)` qo'shildi

Reja uni `AuditRound` satrida sanamaydi, lekin `ReviewAssignment` uchun
«kompozit FK -> `audit_rounds (market_id, id)`» talab qiladi — nishonsiz
migratsiya yiqilardi. Qo'shildi (`5a9b922`).

## Sabotage o'lchovlari — nima QIZARDI va nima YASHIL QOLDI

Har sabotaj snapshotdan `cp` bilan qaytarildi (`git checkout --` ishlatilmadi).

| # | Sabotaj | Kutilgan | NATIJA |
|---|---|---|---|
| A | `occupancy_event_immutable()` ni `tariff_past_immutable()` ning **shartli** shakliga aylantirish (`business_date < bugun`) | o'zgarmaslik qizil | ✅ `test_occupancy_event_cannot_be_updated_or_deleted` va `test_draft_market_exception_covers_delete_only` qizardi<br>⚠ **`test_immutability_triggers_are_before_update_or_delete` YASHIL QOLDI** — tuzilmaviy darvoza trigger TANASINI ko'rmaydi, faqat SHAKLINI. §S-3 ning butun ogohlantirishi shu haqda. |
| B | `0018` dan `CHECK (snapshot_is_billable)` ni olib tashlash | billing to'sig'i qizil | ✅ `test_billable_flag_cannot_be_written_false` **va** `test_occupancy_events_check_forbids_false` — ikkalasi ham qizardi<br>⚠ `test_invalid_frame_cannot_carry_occupancy_evidence` YASHIL QOLDI va bu TO'G'RI: FK yarmi buzilmagan, ya'ni ikki test ikki xil yarmini o'lchaydi |
| C | Bandlik blokini `market_delete_draft()` da **snapshot blokidan KEYIN**ga surish | tartib qizil | ✅ `test_draft_market_deletion_covers_the_occupancy_domain` qizardi: `ForeignKeyViolation ... "fk_occupancy_events_market_id_snapshot_id_snapshots"`<br>⚠ **`test_cascade_covers_every_table_referencing_markets` YASHIL QOLDI** — statik darvoza TARTIBNI ko'rmaydi (matnda oltala jadval bor). `0015` da yozilgan ogohlantirish uchinchi marta tasdiqlandi. |
| D | `0018` dan `fk_zone_reviews_queue_kind_anchor` ni olib tashlash | langar qizil | ✅ `test_lying_queue_kind_copy_is_rejected` va `test_zone_review_queue_kind_is_anchored_to_its_assignment` qizardi<br>⚠ **`test_blind_audit_row_cannot_show_the_ai_verdict` YASHIL QOLDI** — ya'ni `CHECK` HALOL nusxada ishlaydi, YOLG'ON nusxada esa yo'q. Deviatsiya #5 ning butun qiymati aynan shu ustunda. |

**A, C va D sabotajlarining qiymati «yashil qolgan» ustunida:** uchalasi ham
tuzilmaviy (yoki statik) tekshiruv yolg'iz o'zi yetarli emasligini o'lchab
ko'rsatdi.

## Verification

| Tekshiruv | Natija |
|---|---|
| `alembic upgrade head` — **nol holatdan** | ✅ `0001` -> `0019` |
| `alembic downgrade 0017 && alembic upgrade head` | ✅ |
| `alembic downgrade 0018 && alembic upgrade head` | ✅ |
| `SELECT extname FROM pg_extension` | ✅ **faqat `btree_gist`, `plpgsql`** |
| `pytest -q` (to'liq) | ✅ **1956 o'tdi, 0 nosoz** (bazaviy 1901 + 55) |
| `pytest tests/tenancy` | ✅ **488** (bazaviy 474 + 14) |
| Uchta xulq darvozasi + kaskad testi | ✅ **31** |
| `ruff check . && ruff format --check . && mypy .` | ✅ toza (257 fayl) |
| `npm run gate` | ✅ **exit 0** |
| `grep -cE "^\s*require_extension\(" .../0018_occupancy_domain.py` | ✅ **0** |
| `pg_catalog`: `trg_occupancy_event_immutable`, `trg_zone_review_immutable` | ✅ ikkalasi ham `BEFORE DELETE OR UPDATE` |
| `occupancy_events` da audit trigger | ✅ **yo'q**; `camera_zones`/`zone_reviews` da ✅ **bor** |

## Keyingi rejalar uchun ochiq bandlar

- **`05-06`:** `camera_zones` ustunlari — `polygon` (JSONB massiv, 3–12 uch),
  `source_width`/`source_height`, `version`, `is_active`. Tahrir **yangi
  qator** (`UNIQUE(market_id, camera_id, stall_id, version)`), eskisi
  `is_active = false`.
- **`05-08`:** `occupancy_events` ga yozishda `business_date`/`slot_time`
  `snapshots` dan **nusxalanadi** (generated EMAS); `confidence` `numeric(5,4)`
  va `0..1` oralig'ida; `model_version` kalitning bir qismi.
- **`05-09`/`05-11`:** `review_assignments.purpose` **tortish paytida**
  to'ladi va `eval` FAQAT `queue_kind='blind_audit'` bilan yozilishi mumkin
  (`ck_review_assignments_eval_needs_blind_audit`). `audit_draw_due_markets()`
  tayyor — u faqat `(market_id, frame_size)` qaytaradi.
- **`05-10`:** `zone_reviews.queue_kind` ni server **topshiriqdan o'qib**
  yozishi shart — langar FK yolg'on nusxani rad etadi.
- **`05-12`:** `occupancy_day_close_markets()` BARCHA faol bozorlarni
  qaytaradi (hodisasi bo'lmagani ham) — `no_coverage` materializatsiyasi
  aynan shunga tayanadi. `stall_slot_occupancy.verdict` supersetdan
  (`no_coverage` bor) va u `resolution_source` bilan JUFT.
- **Fixture:** `occupancy_rows(conn, base, domain, snapshots)` — `snapshot_rows`
  NING ICHIDA ochiladi; tozalash bozorni avval qoralamaga tushiradi.

## Known Stubs

Yo'q. Bu reja faqat sxema va uning darvozalarini yetkazadi; birorta ustun,
funksiya yoki test «keyinroq to'ldiriladi» holatida qoldirilmadi.

## Threat Flags

Yangi, rejalashtirilmagan xavfsizlik yuzasi topilmadi. `<threat_model>` ning
oltala bandi rejalashtirilgandek qoplandi:

| Threat | Qoplandi |
|---|---|
| T-05-17 (tampering) | Shartsiz (vaqt shartisiz) qo'riqchilar + `test_occupancy_immutable.py` |
| T-05-18 (yaroqsiz kadrdan hisob) | Kompozit FK + `CHECK` + tranzitiv `stall_slot_occupancy` |
| T-05-19 (`SECURITY DEFINER` yuzasi) | `test_due_markets_functions_expose_only_identifiers` — **qaytish TIPI ham** tekshiriladi |
| T-05-20 (bozorlararo) | RLS oltala jadvalda + ikkita kompozit FK (`cameras` VA `stalls`) + `uq_snapshots_market_id_id` |
| T-05-21 (ulkan poligon) | `polygon_min_vertices` / `polygon_max_vertices` (`CASE` bilan himoyalangan) |
| T-05-22 (nazoratchi qarori) | `zone_reviews` `AUDITED_TABLES` da; rad etilgan `UPDATE` audit qatori qoldirmaydi (o'lchandi) |

⚠ Bitta **yangi** (rejada nomlanmagan) yuza yopildi va u deviatsiya #5 da:
denormalizatsiya qilingan `queue_kind` nusxasi orqali D-17.3 ni chetlab
o'tish yo'li — sabotaj D bilan mavjudligi tasdiqlandi va langar bilan
yopildi.

## Self-Check: PASSED

- Yaratilgan 7 + o'zgartirilgan 8 fayl — **hammasi mavjud** (`git diff --name-only 620c33c..HEAD` bilan tasdiqlandi, 15 fayl)
- `1fe35ea`, `5a9b922`, `846e4cf` — **uchala commit ham git tarixida mavjud**
- To'liq to'plam sabotajlardan keyin qayta yugurtirildi: **0 nosoz**; `npm run gate` **exit 0**
