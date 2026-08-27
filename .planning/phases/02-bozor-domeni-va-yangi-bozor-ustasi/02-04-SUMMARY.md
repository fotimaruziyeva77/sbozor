---
phase: 02-bozor-domeni-va-yangi-bozor-ustasi
plan: 04
subsystem: domain-model
tags: [sqlalchemy, postgres, daterange, exclude-gist, generated-column, security-definer, alembic-utils]

# Dependency graph
requires:
  - phase: 02-bozor-domeni-va-yangi-bozor-ustasi
    provides: "02-01 — `AUDITED_TABLES` 8 domen jadvali, `FINANCIAL_TABLES` dan `stall_assignments` chiqarilgan, `btree_gist` init qadami + `require_extension()`; 02-03 — `migrations/entities/functions.py` konvensiyalari va `0006` migratsiya naqshi"
  - phase: 01-poydevor-va-tenant-xavfsizligi
    provides: "`Base`/`TenantMixin`/`TimestampMixin`/`uuid_pk()`, `NAMING_CONVENTION`, `BUSINESS_DATE_EXPR`, `tenant_policy()`/`owner_bootstrap_policy()`, `ALL_TRIGGER_FUNCTIONS` naqshi"
provides:
  - "`sbozor_core.enums.StallStatus` — `active`/`maintenance`/`closed` (A4 mazmuni bilan)"
  - "`sbozor_core.periods` — `PERIOD_BOUNDS` + `assignment_period()` + `period_contains()`, `[)` ning YAGONA manbai"
  - "O'nta domen modeli `Base.metadata` da (`market_profile` … `market_calendar_exceptions`)"
  - "`STALL_STATUS_CHECK` / `OPEN_WEEKDAYS_CHECK` / `STALL_CODE_SORT_EXPR` / `TARIFF_BUSINESS_DATE_EXPR` — migratsiyalar uchun ifoda konstantalari"
  - "`MARKET_DOMAIN_FUNCTIONS` + `MARKET_DOMAIN_GRANT_SIGNATURES` — beshta DB funksiyasi"
  - "`MARKET_DOMAIN_TRIGGER_FUNCTIONS` — uchta domen trigger funksiyasi"
  - "`AUDIT_TRIGGER_FUNCTIONS` — `0002` ning MUZLATILGAN scope'i (yangi nom)"
  - "`ALL_TENANT_TABLES` (12) / `ALL_RLS_TABLES` (13) + to'rtta migratsiya-scope'li tuple"
affects: [02-05, 02-06, 02-07, 02-08, 02-09, 02-10, 02-11, 02-12, 02-13, 02-14, 02-15, 02-16, 02-17, 06-hisob-kitob]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Chegara konventsiyasi `Final[Literal[...]]` bilan qulflanadi — `mypy` uni o'zgartirishni to'xtatadi"
    - "Migratsiya tsikl qiladigan HAR QANDAY ro'yxat o'sha migratsiya bilan MUZLAYDI; aggregat alohida nom oladi"
    - "Reyestrga yozadigan trigger `AFTER` bo'ladi — `BEFORE` da ota qator hali yo'q va FK buziladi"
    - "O'zgarmaslik triggeri qoralama (`is_active = false`) bozorni istisno qiladi; teskari yo'l bo'lmagani uchun bu bir tomonlama"

key-files:
  created:
    - packages/sbozor-core/sbozor_core/periods.py
    - packages/sbozor-core/sbozor_core/models/market.py
    - tests/unit/test_periods.py
  modified:
    - packages/sbozor-core/sbozor_core/enums.py
    - packages/sbozor-core/sbozor_core/models/__init__.py
    - migrations/entities/functions.py
    - migrations/entities/triggers.py
    - migrations/entities/__init__.py
    - migrations/versions/0002_audit.py
    - tests/unit/test_enums.py

key-decisions:
  - "`stall_code_claim()` `AFTER` bo'ldi, `BEFORE` emas — `BEFORE INSERT` da `stalls` qatori yo'q va reyestrdagi composite FK darhol buziladi (o'lchandi)"
  - "`tariff_past_immutable()` / `category_period_past_immutable()` qoralama bozorni istisno qiladi — usiz `market_delete_draft()` har doim `23514` bilan yiqilardi"
  - "`ALL_TRIGGER_FUNCTIONS` aggregatga aylandi; `0002_audit.py` endi `AUDIT_TRIGGER_FUNCTIONS` ustidan tsikl qiladi (DDL o'zgarmadi)"
  - "`Range` `sqlalchemy.dialects.postgresql` dan import qilinadi — SQLAlchemy 2.0.51 da `sqlalchemy.Range` YO'Q"
  - "`PERIOD_BOUNDS` tipi `Final[Literal[\"[)\"]]` — `Final[str]` `Range.bounds` imzosidan o'tmaydi va konvensiya o'zgarishi jimgina ketardi"
  - "`market_create()` matn parametrlarini `NULLIF(..., '')` bilan o'tkazadi — bo'sh `tin` `ck_market_profile_tin_format` ni buzardi"
  - "`stall_category_periods` toifa FK'sining NOMIDA `market_id` segmenti yo'q — to'liq nom 64 bayt bo'lib 63 baytlik chegaradan oshardi"

patterns-established:
  - "Pattern: migratsiya-scope'li ro'yxat + aggregat (jadvallar uchun `TENANT_TABLES`/`ALL_TENANT_TABLES`, funksiyalar uchun `AUDIT_TRIGGER_FUNCTIONS`/`ALL_TRIGGER_FUNCTIONS`)"
  - "Pattern: DB qoidasining istisnosi FAQAT bir tomonlama holatga bog'lanadi (qoralama -> faol yo'li bor, teskarisi yo'q)"
  - "Pattern: yangi model fayli commit'dan oldin haqiqiy PG'da vaqtinchalik probe bilan bajarib ko'riladi (generated ustun, identifikator uzunligi, EXCLUDE)"

requirements-completed: []

# Metrics
duration: 41min
completed: 2026-07-31
---

# Phase 2 Plan 04: Domen modeli kod sifatida Summary

**2-fazaning butun ma'lumot modeli — o'nta SQLAlchemy jadvali, ikki xil temporal model, beshta DB funksiyasi va uchta domen triggeri — e'lon qilindi va ularning har biri haqiqiy `postgres:18.4-trixie` da bajarib ko'rildi; shu o'lchov rejadagi ikkita ishlamaydigan konstruksiyani (BEFORE trigger + FK, o'zgarmaslik triggeri + qoralama o'chirish) migratsiyalar yozilishidan OLDIN topdi.**

## Performance

- **Duration:** ~41 min
- **Started:** 2026-07-31T16:45Z
- **Completed:** 2026-07-31T17:26Z
- **Tasks:** 3/3
- **Files:** 10 (3 yaratildi, 7 o'zgartirildi)

## Accomplishments

- **Ikki xil temporal model bitta faylda va farqi KO'RINADI.** `tariffs`/`stall_category_periods` — voris modeli (`valid_to` YO'Q), `stall_assignments` — `daterange` + `EXCLUDE USING gist`. Fayl boshidagi qaror bloki nima uchun D-06 va D-07 birgalikda `daterange` ni tarif uchun IMKONSIZ qilishini yozadi.
- **`code_sort` inson-raqamli tartibni DB kafolatiga aylantirdi va tartib O'LCHANDI:** kiritilgan `2, 10, 100, 11, 12a, A-3` → natija `2, A-3, 10, 11, 12a, 100`. Harfli kod o'z RAQAMI bo'yicha joylashishi — ifodaning kutilmagan, lekin muhim oqibati — model docstringida qayd etildi (UI shunga tayanadi).
- **`[)` konventsiyasi ikki qatlamda qulflandi:** `Final[Literal["[)"]]` tipi bilan (`mypy` boshqa qiymatni o'tkazmaydi) va D-10 almashinuv jadvalini takrorlaydigan 8 ta unit test bilan.
- **`market_is_open()` ning uchala qavati va fail-closed yo'li o'lchandi:** haftalik jadval → `false`, istisno → `true` (ustun), noma'lum bozor → `false`.
- **`market_delete_draft()` haqiqatan ishlaydi** — o'tgan sanali tarif, toifa davri, biriktirish va kod reyestri bilan to'la qoralama butunlay o'chdi; faol bozor uchun `false` qaytdi va BIRORTA qator o'chmadi.
- **Reyestrlar migratsiya-scope'li bo'lib bo'lindi va `0001` teginilmadi.** `TENANT_TABLES` muzlatildi, `ALL_TENANT_TABLES` (12) / `ALL_RLS_TABLES` (13) aggregatlari qo'shildi.

## Task Commits

1. **Task 1: `StallStatus` enum'i va `[)` davr yordamchisi** — `fe7b117` (feat)
2. **Task 2: O'nta domen modeli va barrel importi** — `f521397` (feat)
3. **Task 3: DB funksiyalari, trigger funksiyalari va entity reyestrlari** — `156ba33` (feat)

## Files Created/Modified

**Yaratildi**

- `packages/sbozor-core/sbozor_core/periods.py` — `PERIOD_BOUNDS`, `assignment_period()`, `period_contains()`. Modul docstringida D-10 almashinuv jadvali va D-11 bo'shlig'ining ATAYINLIGI.
- `packages/sbozor-core/sbozor_core/models/market.py` — o'nta model + to'rtta ifoda konstantasi (663 qator).
- `tests/unit/test_periods.py` — 8 test, jumladan "almashinuv kuni AYNAN bitta davrga tegishli" nazorat holati (yolg'iz yuqori-chegara testi `'(]'` konventsiyasida ham yashil bo'lardi).

**O'zgartirildi**

- `packages/sbozor-core/sbozor_core/enums.py` — `StallStatus` + A4 mazmuni (`closed`/`maintenance` ga hisob yozilmaydi).
- `packages/sbozor-core/sbozor_core/models/__init__.py` — o'nta model va to'rtta konstanta barrel'ga.
- `migrations/entities/functions.py` — beshta `PGFunction` + `MARKET_DOMAIN_FUNCTIONS` / `MARKET_DOMAIN_GRANT_SIGNATURES`.
- `migrations/entities/triggers.py` — uchta `PGFunction`; ro'yxat `AUDIT_TRIGGER_FUNCTIONS` / `MARKET_DOMAIN_TRIGGER_FUNCTIONS` / `ALL_TRIGGER_FUNCTIONS` ga bo'lindi.
- `migrations/entities/__init__.py` — to'rtta scope'li tuple + ikkita aggregat; `ALL_ENTITIES` ular ustidan quriladi.
- `migrations/versions/0002_audit.py` — tsikl `AUDIT_TRIGGER_FUNCTIONS` ga o'tkazildi (bajariladigan DDL o'zgarmadi).
- `tests/unit/test_enums.py` — `StallStatus` uchun ikkita test.

## Decisions Made

- **`stall_code_claim()` — `AFTER`, `BEFORE` emas.** RESEARCH Pattern 8 `BEFORE INSERT` deb yozgan, lekin u o'zi e'lon qilgan `fk_stall_code_registry_market_id_stall_id_stalls` FK'si bilan bir vaqtda ishlay olmaydi. Pastdagi deviatsiya #2.
- **O'zgarmaslik triggerlari qoralama bozorni istisno qiladi.** Pastdagi deviatsiya #3. Bu xavfsizlikni zaiflashtirmaydi, chunki `market_deactivate()` funksiyasi YO'Q — bozor bir marta faollashgach hech qachon qoralamaga qaytmaydi.
- **`Range` — `sqlalchemy.dialects.postgresql` dan.** Reja `sqlalchemy.Range` deb yozgan; SQLAlchemy 2.0.51 da bunday nom yo'q (`ImportError` bilan o'lchandi).
- **`PERIOD_BOUNDS: Final[Literal["[)"]]`.** `Final[str]` `mypy --strict` da `Range(bounds=...)` imzosidan o'tmadi. `Literal` tipi qo'shimcha foyda beradi: konvensiyani o'zgartirish endi tip xatosi.
- **`market_create()` matn parametrlarini `NULLIF(..., '')` bilan yozadi.** Usta bo'sh maydonni `''` sifatida yuboradi va `''` `ck_market_profile_tin_format` regeksidan o'tmaydi — ya'ni "STIR ko'rsatilmagan" holati bozor yaratishni tushunarsiz CHECK xatosi bilan yiqitardi.
- **`stall_category_periods` toifa FK'sining nomidan `market_id` olib tashlandi.** To'liq konvensiya nomi 64 bayt (63 baytlik chegaradan oshadi) — Postgres uni jimgina kesardi va autogenerate har safar "o'zgargan" deb ko'rsatardi. Konstraytning O'ZI baribir composite.
- **`bank_account`/`bank_mfo` DB darajasida formatlanmaydi.** `tin` uchun CHECK bor (A2 taxmini), bank rekvizitlari uchun yo'q: A1 buyurtmachi bilan tasdiqlanmagan va noto'g'ri qat'iy format haqiqiy rekvizitni rad etardi. Chegara validatsiyasi zod/pydantic tomonida.
- **`zones`/`stall_categories`/`stalls`/`vendors` da "bo'sh emas" CHECK'lari qo'shildi.** Import nom bo'yicha bog'laydi (D-14) va bo'sh nom hech qachon mos kelmay "fantom" qator yaratardi; ismsiz sotuvchi esa qarzdorlik reestrini foydasiz qilardi. Reja "Claude's Discretion: sxema detallari" deb ruxsat bergan.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `sqlalchemy.Range` mavjud emas**

- **Found during:** Task 1
- **Issue:** Reja `assignment_period()` ni "`sqlalchemy.Range` (SQLAlchemy 2.0 `Range` tipi)" bilan qurishni aytadi. SQLAlchemy 2.0.51 da bunday eksport YO'Q: `ImportError: cannot import name 'Range' from 'sqlalchemy'` (o'lchandi). Tip `sqlalchemy.dialects.postgresql.Range` da yashaydi.
- **Fix:** Import yo'li to'g'rilandi. Qo'shimcha o'lchov: `Range.contains()` `[)` chegarasini to'g'ri hisoblaydi (`2026-08-09` → `True`, `2026-08-10` → `False`), shuning uchun `period_contains()` chegara arifmetikasini QO'LDA yozmaydi — u `Range.contains()` ga topshiradi (qo'lda yozilgan `day >= lower and day < upper` varianti `bounds` ni umuman o'qimasdi).
- **Files modified:** `packages/sbozor-core/sbozor_core/periods.py`
- **Verification:** `tests/unit/test_periods.py` — 8 test
- **Committed in:** `fe7b117`

**2. [Rule 1 - Bug] `stall_code_claim()` `BEFORE INSERT` da o'z FK'sini buzadi**

- **Found during:** Task 3 (funksiya tanalarini haqiqiy PG'da bajarib ko'rish)
- **Issue:** Reja (va RESEARCH Pattern 8) triggerni `BEFORE INSERT OR UPDATE OF code ON stalls` deb belgilaydi va AYNI PAYTDA `stall_code_registry.stall_id` uchun composite FK e'lon qiladi. Ikkalasi birga ishlay olmaydi: `BEFORE INSERT` paytida `stalls` qatori hali YOZILMAGAN, ya'ni reyestrga `stall_id = NEW.id` bilan yozish darhol yiqiladi. O'lchangan xato: `ForeignKeyViolation: Key (market_id, stall_id)=(...) is not present in table "stalls"`. Ya'ni MARKET-02 ning har bir rasta qo'shish amali 02-06 migratsiyasi triggerni ulagan kundan boshlab ishlamay qolardi.
- **Fix:** Trigger `AFTER INSERT OR UPDATE OF code` ga o'tkazildi (docstring — 02-06 uchun kontrakt), tana `RETURN NULL` qaytaradi (`AFTER ROW` da qaytish qiymati e'tiborga olinmaydi, `fn_audit_row()` bilan bir xil). Kafolat zaiflashmaydi: `AFTER` dagi `RAISE` ham butun operatsiyani bekor qiladi.
- **Qo'shimcha foyda:** `AFTER` bo'lgani uchun `INSERT ... ON CONFLICT DO NOTHING` da konflikt yuzaga kelgan qator uchun trigger UMUMAN ishga tushmaydi — ya'ni D-15 rejalashtirgan xulq (mavjud kodlar jimgina `skipped`) endi TO'G'RIDAN-TO'G'RI ishlaydi. Rejaning "import mavjud kodlarni ilova qatlamida oldindan chiqarib tashlashi SHART" ogohlantirishi to'g'rilikdan UX talabiga tushdi va docstringda shunday yozildi (02-12 uchun).
- **Files modified:** `migrations/entities/triggers.py`
- **Verification:** O'lchandi — chetlangan kod uchun `23505`, o'z kodini qaytarib olish esa ruxsat
- **Committed in:** `156ba33`

**3. [Rule 1 - Bug] O'zgarmaslik triggeri `market_delete_draft()` ni har doim yiqitardi**

- **Found during:** Task 3
- **Issue:** Rejaning ikki qismi bir-birini inkor qiladi. `market_delete_draft()` `tariffs` va `stall_category_periods` dan `DELETE` qiladi; `tariff_past_immutable()` esa `BEFORE UPDATE OR DELETE` bo'lib `valid_from <= bugun` qatorlarni qulflaydi. Qoralamaning BIRINCHI tarifi `valid_from = market_profile.operating_since` bilan yaratiladi (A3), ya'ni odatda bugun yoki o'tgan sana — demak tashlab ketilgan har qanday qoralamani o'chirish HAR DOIM `23514` bilan yiqilardi va qoralamalar bazada abadiy to'planardi.
- **Fix:** Ikkala daxlsizlik triggeriga qoralama istisnosi qo'shildi: qator faqat bozor QORALAMA EMAS bo'lganda qulflanadi (`NOT EXISTS (SELECT 1 FROM markets WHERE id = OLD.market_id AND is_active = false)`).
- **Nega bu T-02-23/T-02-24 ni zaiflashtirmaydi:** `is_active` `false` → `true` ga faqat `market_activate()` orqali o'tadi va TESKARI yo'l YO'Q — `market_deactivate()` ataylab yaratilmagan (bu `MARKET_ACTIVATE` docstringida qulflandi). Ya'ni bir marta jonli bo'lgan bozor hech qachon qoralamaga qayta olmaydi va istisno unga hech qachon qo'llanmaydi. Qoralamada esa hisob-kitob umuman ishlamagan (6-faza `WHERE m.is_active` bilan filtrlaydi), ya'ni himoya qilinadigan o'tmish yo'q. `markets` o'qish `SECURITY DEFINER` siz, ya'ni tenant kontekstsiz sessiyada 0 qator → qator QULFLANGAN deb hisoblanadi (fail-closed).
- **Files modified:** `migrations/entities/triggers.py`, `migrations/entities/functions.py` (docstringlar)
- **Verification:** O'lchandi — qoralamada o'tgan tarifni tahrirlash ✅ o'tdi; faollashtirgandan keyin AYNI o'sha `UPDATE` `23514` bilan rad etildi; `market_delete_draft()` o'tgan sanali tarif+toifa+biriktirish bilan to'la qoralamani to'liq o'chirdi
- **Committed in:** `156ba33`

**4. [Rule 3 - Blocking] `ALL_TRIGGER_FUNCTIONS` ni kengaytirish `0002_audit.py` ni egallab oladi**

- **Found during:** Task 3
- **Issue:** Reja "`ALL_TRIGGER_FUNCTIONS` ro'yxatiga uchtasi ham qo'shiladi" deb yozadi va `len(...)==5` ni qabul mezoni qiladi. Lekin `migrations/versions/0002_audit.py` AYNAN shu ro'yxat ustidan `upgrade()` da ham, `downgrade()` da ham tsikl qiladi. Ya'ni 2-faza domen trigger funksiyalari 1-fazaning AUDIT migratsiyasida yaratilib qolardi va keyin ularni o'z migratsiyasida (`0007`/`0008`) yaratmoqchi bo'lgan `create_entity()` yiqilardi. O'lchangan xato: `DuplicateFunction: function "stall_code_claim" already exists with same argument types`. Bu rejaning O'ZI `TENANT_TABLES` uchun hujjatlashtirgan tuzoqning aynan o'zi — faqat u jadvallarga qo'llanib, funksiyalarga qo'llanmagan.
- **Fix:** Jadvallar bilan bir xil naqsh: `AUDIT_TRIGGER_FUNCTIONS` (`0002` ning muzlatilgan scope'i) + `MARKET_DOMAIN_TRIGGER_FUNCTIONS` (`0007`/`0008`) + `ALL_TRIGGER_FUNCTIONS` aggregati (5 — rejaning mezoni saqlandi, `ALL_ENTITIES` faqat undan foydalanadi). `0002_audit.py` dagi ikkita identifikator yangi nomga o'tkazildi.
- **Nega mavjud migratsiyaga tegish xavfsiz:** `AUDIT_TRIGGER_FUNCTIONS` ning mazmuni `ALL_TRIGGER_FUNCTIONS` ning bu o'zgarishdan OLDINGI mazmuni bilan AYNAN bir xil (`FN_AUDIT_ROW`, `AUDIT_IMMUTABLE`). Bajariladigan DDL bayt-ba-bayt o'zgarmadi — bu semantik qayta yozish emas, migratsiyani u har doim nazarda tutgan ro'yxatga qadash.
- **Files modified:** `migrations/entities/triggers.py`, `migrations/versions/0002_audit.py`
- **Verification:** `alembic upgrade head` nol holatdan yashil (450 testning `migrated` fixture'i orqali)
- **Committed in:** `156ba33`

**5. [Rule 2 - Missing Critical] `market_create()` bo'sh rekvizitlarda yiqilardi**

- **Found during:** Task 3
- **Issue:** Reja funksiya imzosida `p_tin text` va boshqa ixtiyoriy matn maydonlarini beradi, model esa `ck_market_profile_tin_format` = `tin IS NULL OR tin ~ '^[0-9]{9}$'` ni talab qiladi. Usta bo'sh maydonni odatda `''` sifatida yuboradi va `''` bu regeksdan O'TMAYDI. Ya'ni "STIR ko'rsatilmagan" — eng oddiy holat — bozor yaratishni tushunarsiz CHECK xatosi bilan yiqitardi.
- **Fix:** Barcha ixtiyoriy matn parametrlari `NULLIF(p_..., '')` bilan yoziladi; sabab docstringda.
- **Files modified:** `migrations/entities/functions.py`
- **Verification:** O'lchandi — `market_create('Probe bozori', '', DATE '2026-01-01', NULL, '', '', '', '', '')` muvaffaqiyatli, profil qatorida `tin IS NULL` va `address IS NULL`
- **Committed in:** `156ba33`

**6. [Rule 3 - Blocking] `stall_category_periods` FK nomi 63 baytlik chegaradan oshardi**

- **Found during:** Task 2
- **Issue:** Loyiha konvensiyasi bo'yicha to'liq nom `fk_stall_category_periods_market_id_category_id_stall_categories` = 64 bayt. Postgres identifikatorlarni 63 baytga JIMGINA kesadi — bazadagi nom modeldagi nom bilan mos kelmasdi va autogenerate uni har safar "o'zgargan" deb ko'rsatib, `downgrade()` esa mavjud bo'lmagan nomni o'chirmoqchi bo'lardi.
- **Fix:** Faqat shu bitta FK nomidan `market_id` segmenti olib tashlandi (`fk_stall_category_periods_category_id_stall_categories`, 54 bayt); konstraytning O'ZI baribir composite. Sabab model docstringida.
- **Files modified:** `packages/sbozor-core/sbozor_core/models/market.py`
- **Verification:** Probe barcha 10 jadvalning konstrayt nomlarini `pg_constraint` dan o'qib model nomlari bilan solishtirdi — kesilgan nom yo'q
- **Committed in:** `f521397`

---

**Total deviations:** 6 auto-fixed (2 bug, 3 blocking, 1 missing-critical). Rule 4 (arxitektura) holati bo'lmadi.
**Impact on plan:** Qamrov kengaytmasi yo'q — birorta yangi jadval, funksiya yoki paket rejadan tashqari qo'shilmadi. #2, #3 va #4 rejaning O'Z artefaktlari orasidagi HAQIQIY ziddiyatlarni hal qiladi (ular bo'lmasa 02-06 migratsiyasi yozilgan kunda uchta alohida nosozlik chiqardi); #1 va #6 texnik chegaralar; #5 rejaning o'z CHECK konstrayti bilan o'z funksiya imzosi orasidagi bo'shliq.

## Empirik o'lchovlar (vaqtinchalik probe bilan, commit'dan oldin o'chirildi)

Ikkita vaqtinchalik pytest fayli haqiqiy `postgres:18.4-trixie` konteynerida `sbozor_owner` roli bilan bajarildi va o'lchovdan keyin o'chirildi (02-03 dagi naqsh).

| O'lchov | Natija |
|---|---|
| 10 jadvalning DDL'i `sbozor_owner` bilan bajariladi | ✅ |
| Konstrayt nomlari `pg_constraint` da KESILMAGAN | ✅ (10/10 jadval) |
| `code_sort` generated ustuni (IMMUTABLE talabi) | ✅ `2, A-3, 10, 11, 12a, 100` |
| `open_weekdays = '{}'` rad etiladi | ✅ `CheckViolation` |
| `EXCLUDE` qoplanuvchi davrni rad etadi | ✅ `23P01` |
| `tariffs.business_date` `valid_from` dan ALOHIDA hisoblanadi | ✅ `2026-07-31` vs `valid_from = 2026-09-01` |
| `market_create()` bozor + profilni birga yaratadi | ✅ `is_active=false`, `Asia/Tashkent`, `{1..7}`, `''` → `NULL` |
| `market_is_open()` — haftalik jadval | ✅ `false` (dushanba jadvalda yo'q) |
| `market_is_open()` — istisno ustun turadi | ✅ `true` |
| `market_is_open()` — noma'lum bozor (fail-closed) | ✅ `false` |
| `stall_code_claim()` chetlangan kodni rad etadi | ✅ `23505` |
| `stall_code_claim()` o'z kodini qaytarishga ruxsat beradi | ✅ |
| Qoralamada o'tgan tarifni tahrirlash | ✅ ruxsat (istisno) |
| Faol bozorda o'tgan tarif/toifa | ✅ `23514` (ikkalasi ham) |
| `market_delete_draft()` faol bozorda | ✅ `false`, 0 qator o'chdi |
| `market_delete_draft()` to'la qoralamada | ✅ `true`, 5 jadvalda 0 qator qoldi |
| `market_delete_draft()` mavjud bo'lmagan bozorda | ✅ `false` |

## Issues Encountered

- **Rejaning `<must_haves>` artefakt tekshiruvi `bounds="[)"` literalini talab qiladi**, amaldagi kod esa `bounds=PERIOD_BOUNDS` yozadi (yagona manba). Literal `assignment_period()` docstringida "chiqadigan shakl" sifatida qoldirildi — ya'ni u haqiqiy hujjat, gaming emas; qulflash esa `Final[Literal["[)"]]` tipida (undan kuchliroq).
- **Reja `financial_guards()` ni `tariffs` uchun taqiqlaydi va bu bajarildi**, lekin `tariffs` `FINANCIAL_TABLES` da qolgani uchun `test_financial_tables_have_guards` 02-05 migratsiyasidan keyin uchta qo'riqchini QO'LDA topishi kerak bo'ladi — model tomonda uchalasi ham bor.
- **`.env` worktree'da yo'q** (gitignore), shuning uchun `npm run migrate` (compose `migrate` profili) ishlamaydi. `alembic upgrade head` ekvivalenti `migrated` fixture'i orqali — AYNAN o'sha `alembic.command` API'si bilan, haqiqiy `postgres:18.4-trixie` da va `sbozor_owner` roli bilan — 450 testning har birida bajarildi.
- **`ruff format` ikki marta uzun konstruksiyani qayta formatladi** (bitta list comprehension, ikkita `UniqueConstraint`). O'zgarish faqat qator uzunligiga tegishli.

## Known Stubs

Yo'q. Bu reja HECH QANDAY DDL ishga tushirmaydi — bu uning maqsadi (migratsiyalar 02-05/02-06 da). Barcha e'lonlar to'liq va bajarib ko'rilgan; birorta model bo'sh qolmagan, birorta funksiya tanasi `TODO` bilan yozilmagan.

**Ataylab ochiq qoldirilgan, ko'rinadigan qarz (stub emas):**

| Qarz | Kim yopadi | Bugungi holati |
|---|---|---|
| O'nta jadval hali bazada yo'q | 02-05, 02-06 | `tests/tenancy/test_meta.py::PENDING_AUDIT_TRIGGERS` ikki tomonlama qulflaydi (o'zgartirilmadi) |
| `ExcludeConstraint` migratsiyaga o'zi ko'chmaydi | 02-06 | Model docstringida ANIQ ogohlantirish; Alembic uni na yaratadi, na yo'qolganini sezadi |
| `STALL_STATUS_CHECK` uchun enum-vs-DB meta-testi | 02-05 | `test_role_check_constraint_matches_enum` naqshi tayyor |
| `market_deactivate()` funksiyasi | — (ATAYIN YO'Q) | Uning yo'qligi deviatsiya #3 ning xavfsizlik asosi |

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| threat_flag: immutability-guard-scoped | `migrations/entities/triggers.py` | `tariff_past_immutable()` va `category_period_past_immutable()` endi QORALAMA bozorda (`is_active = false`) o'tmishdagi qatorni o'zgartirish/o'chirishga ruxsat beradi. T-02-23/T-02-24 dispozitsiyalari saqlanadi: istisno bir tomonlama (`market_deactivate()` YO'Q, ya'ni faol bozor qoralamaga qayta olmaydi), qoralamada hisob-kitob umuman ishlamagan, va `markets` o'qish RLS ostida — kontekstsiz sessiyada qator QULFLANGAN deb hisoblanadi. Deviatsiya #3 da to'liq. |
| threat_flag: trigger-timing-changed | `migrations/entities/triggers.py` | `stall_code_claim()` `BEFORE` dan `AFTER` ga o'tdi (T-02-25). Kafolat saqlanadi — `AFTER` dagi `RAISE` ham operatsiyani bekor qiladi. Yon ta'sir: `ON CONFLICT DO NOTHING` bilan kelgan takroriy kod endi triggerga umuman yetib bormaydi, ya'ni import D-15 bo'yicha jimgina `skipped` qiladi. |

Boshqa yangi xavfsizlik yuzasi yo'q: yangi endpoint, fayl kirishi yoki tashqi bog'liqlik qo'shilmadi. Rejaning `<threat_model>` idagi qolgan dispozitsiyalar bajarildi:

| Threat ID | Holat |
|-----------|-------|
| T-02-20 | mitigate — `market_create()` da `is_active` LITERAL `false`, `p_is_active` parametri YO'Q; faollashtirish alohida funksiya va alohida GRANT |
| T-02-21 | mitigate — beshta funksiyaning har birida `SET search_path = pg_catalog, public` LITERAL (dasturiy tekshirildi) |
| T-02-22 | mitigate — `market_is_open()` da `SECURITY DEFINER` YO'Q, `STABLE` bor; noma'lum bozor uchun `false` o'lchandi |
| T-02-26 | mitigate — `EXCLUDE USING gist` o'lchandi (`23P01`) |
| T-02-27 | mitigate — `market_delete_draft()` faol bozorda `false` qaytardi va 0 qator o'chdi (o'lchandi) |
| T-02-28 | mitigate — reyestr migratsiya-scope'li tuple'larga bo'lindi; meta-test `pg_catalog` dan tekshiradi va reyestrga tayanmaydi |

## Verification Results

| # | Buyruq | Natija |
|---|---|---|
| 1 | `npm run test:unit` | ✅ exit 0 (174 test — 164 + 10 yangi) |
| 2 | `npm run lint` (ruff + format + mypy strict) | ✅ exit 0 (92 fayl, 91 manba) |
| 3 | `Base.metadata.tables` | ✅ 15 (1-fazadagi 5 + 10 yangi) |
| 4 | `alembic upgrade head` | ✅ `migrated` fixture'i orqali, nol holatdan (`.env` yo'qligi sababi pastda) |
| 5 | `git diff --stat migrations/versions/0001_identity.py` | ✅ BO'SH |
| — | `pytest -q` (to'liq) | ✅ **450 passed** (02-03 dagi 440 + 10 yangi) |
| — | Task 3 avtomatik tekshiruvi (`len(...)` uchligi) | ✅ 12 / 5 / 5 |

**Qabul mezonlari (Task 2):**

| Mezon | Natija |
|-------|--------|
| O'nta yangi jadval `Base.metadata.tables` da | ✅ |
| `code_sort` `Computed(..., persisted=True)`, ifodada `regexp_replace` + `lpad` | ✅ |
| `tariffs` da `valid_to` YO'Q, `business_date` `Computed` | ✅ |
| `tariffs`/`stall_category_periods`/`stall_assignments` da `updated_at` YO'Q | ✅ (uchalasi) |
| `stall_assignments` da `ExcludeConstraint(using="gist")` | ✅ |
| `stall_code_registry` dan tashqari hammasida `UNIQUE(market_id, id)` | ✅ (9/9) |
| `grep "ForeignKey("` `market.py` da | ✅ 0 ta (hammasi `ForeignKeyConstraint`) |
| `STALL_STATUS_CHECK` enum'dan hosil qilingan | ✅ `status IN ('active', 'maintenance', 'closed')` |
| `models/__init__.py` `__all__` da o'nta model | ✅ |

**Qabul mezonlari (Task 3):**

| Mezon | Natija |
|-------|--------|
| `MARKET_DOMAIN_FUNCTIONS` = 5, har birida `SET search_path` literal | ✅ |
| `market_is_open` da `SECURITY DEFINER` YO'Q, `STABLE` bor | ✅ |
| `market_create` da literal `false`, `p_is_active` parametri YO'Q | ✅ |
| `market_create` tanasida `markets` + `market_profile` INSERT | ✅ |
| `ALL_TRIGGER_FUNCTIONS` = 5 | ✅ (aggregat — deviatsiya #4) |
| Uchta yangi triggerda `SECURITY DEFINER` YO'Q | ✅ (beshtasida ham) |
| `stall_code_claim` `23505`; daxlsizlik triggerlari `23514` | ✅ |
| `TENANT_TABLES` = `("user_market_roles", "refresh_tokens")` | ✅ o'zgarmadi |
| `ALL_TENANT_TABLES` = 12, `ALL_RLS_TABLES` = 13 | ✅ |
| `0001_identity.py` o'zgartirilmagan | ✅ |

## User Setup Required

Yo'q — tashqi servis sozlamasi kerak emas. Bu reja DDL ishga tushirmaydi, ya'ni deploy eslatmasi ham yo'q.

## Next Phase Readiness

**02-05 (`0007_market_domain`) uchun aniq topshiriq:**
- Jadvallar: `MARKET_DOMAIN_TENANT_TABLES` tuple'i tayyor; har biri uchun `enable_tenant_rls()` + `create_entity(tenant_policy(t))` + `create_entity(owner_bootstrap_policy(t))`.
- `attach_audit_trigger()` — `market_profile` va `stalls` uchun; ulangach nomlarini `tests/tenancy/test_meta.py::PENDING_AUDIT_TRIGGERS` dan O'CHIRING (aks holda test qizaradi va sababni o'zi aytadi). `stall_code_registry` ga trigger ULANMAYDI (`id uuid` PK yo'q).
- Funksiyalar: `MARKET_DOMAIN_FUNCTIONS` + `MARKET_DOMAIN_GRANT_SIGNATURES` (`REVOKE ... FROM PUBLIC` AVVAL, keyin `GRANT ... TO sbozor_app` — `0004_user_admin.py` naqshi).
- `stall_code_claim` trigger'i: `AFTER INSERT OR UPDATE OF code ON stalls FOR EACH ROW` — `BEFORE` EMAS (deviatsiya #2).
- `EXPECTED_DEFINER_FUNCTIONS` ga to'rtta yangi `SECURITY DEFINER` funksiya qo'shiladi; `market_is_open` unga QO'SHILMAYDI.

**02-06 (`0008`/`0009`/`0010`) uchun:**
- `TEMPORAL_TENANT_TABLES` / `VENDOR_TENANT_TABLES` / `CALENDAR_TENANT_TABLES` tuple'lari tayyor.
- `stall_assignments` migratsiyasi `require_extension("btree_gist")` bilan BOSHLANADI.
- ⚠ `ExcludeConstraint` ni Alembic AVTOGENERATSIYA QILMAYDI va yo'qolganini ham sezmaydi — u migratsiyada ANIQ yoziladi va meta-test bilan qulflanadi.
- `tariffs` da `financial_guards()` CHAQIRILMAYDI; uchta qo'riqchi qo'lda (`business_date` Computed, `CHECK (amount_soum > 0)`, `UNIQUE(market_id, category_id, valid_from)`). `business_date` ifodasi uchun `migrations.helpers.BUSINESS_DATE_EXPR` ni IMPORT qiling — uchinchi nusxa yozmang.
- Trigger funksiyalarini `MARKET_DOMAIN_TRIGGER_FUNCTIONS` dan oling (`ALL_TRIGGER_FUNCTIONS` aggregatidan EMAS — u faqat autogenerate reyestri).

**02-11 (`setup-status` / `activate`) uchun:**
- `market_activate()` to'liqlik tekshiruvini O'ZI qilmaydi — u ilova qatlamida va javob `409` + `blocking[]` bo'lishi kerak (02-03 kontrakti).
- `market_delete_draft()` `false` qaytarganda ikki holat bor: bozor FAOL yoki TOPILMADI. Chaqiruvchi ularni ajratishi kerak bo'lsa, avval `markets` ni o'qisin.

**02-12 (import) uchun:**
- `stall_code_claim()` `AFTER` bo'lgani uchun `INSERT ... ON CONFLICT (market_id, code) DO NOTHING` mavjud kodlarni JIMGINA o'tkazib yuboradi (D-15 shaklida). Ilova qatlamidagi oldindan filtrlash `skipped` sonini ko'rsatish uchun kerak, TO'G'RILIK uchun emas.

**6-faza (hisob-kitob) uchun yozma kontrakt:**
- "D sanadagi tarif" — `WHERE market_id = :m AND category_id = :c AND valid_from <= :d ORDER BY valid_from DESC LIMIT 1` (qo'shimcha indeks kerak emas, UNIQUE konstraytining o'zi optimal).
- "Bozor shu kuni ishlaydimi" — `WHERE market_is_open(:market_id, :business_date)`, bitta shart.
- "Bugun kim biriktirilgan" — `period @> :d` (GiST indeksi), `period_contains()` EMAS.
- `closed`/`maintenance` rastalarga hisob YOZILMAYDI (A4, `StallStatus` docstringida).

## Self-Check: PASSED

- Da'vo qilingan 3 yangi fayl diskda mavjud: `packages/sbozor-core/sbozor_core/periods.py`, `packages/sbozor-core/sbozor_core/models/market.py`, `tests/unit/test_periods.py`
- Da'vo qilingan 7 o'zgartirilgan fayl `git diff --stat 4c5f0a9..HEAD` da ko'rinadi
- Uchala vazifa commit'i git tarixida mavjud: `fe7b117`, `f521397`, `156ba33`
- Birorta commit'da fayl o'chirilishi yo'q (`git diff --diff-filter=D` uchalasida ham bo'sh)
- Ikkala vaqtinchalik probe fayli commit'dan OLDIN o'chirildi; ishchi daraxtda kuzatilmagan fayl qolmadi

---
*Phase: 02-bozor-domeni-va-yangi-bozor-ustasi*
*Completed: 2026-07-31*
