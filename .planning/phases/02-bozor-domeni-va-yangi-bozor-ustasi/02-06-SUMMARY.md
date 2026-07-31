---
phase: 02-bozor-domeni-va-yangi-bozor-ustasi
plan: 06
subsystem: database
tags: [alembic, postgres, rls, exclude-gist, daterange, btree-gist, invoker, seed, autogenerate]

# Dependency graph
requires:
  - phase: 02-bozor-domeni-va-yangi-bozor-ustasi
    provides: "02-05 — `0007`/`0008` migratsiya zanjiri, `PENDING_AUDIT_TRIGGERS`/`PENDING_DOMAIN_TABLES` qarz reyestrlari, `test_market_domain_meta.py` darvoza fayli; 02-04 — `Vendor`/`StallAssignment`/`MarketCalendarException` modellari, `MARKET_CALENDAR_FUNCTIONS`, `sbozor_core.periods.assignment_period()`; 02-01 — `require_extension()` + `ops/db/init/00-extensions.sql` (`btree_gist`)"
  - phase: 01-poydevor-va-tenant-xavfsizligi
    provides: "`enable_tenant_rls()`, `attach_audit_trigger()`, `tenant_policy()`/`owner_bootstrap_policy()`, `fn_audit_row()`, `fixtures/two_markets.py`"
provides:
  - "`migrations/versions/0009_vendors.py` — vendors / stall_assignments + `EXCLUDE USING gist` + RLS + audit"
  - "`migrations/versions/0010_calendar.py` — market_calendar_exceptions + `market_is_open()` + `market_delete_draft()` (2-fazaning OXIRGI migratsiyasi)"
  - "O'nta domen jadvali va beshta bozor funksiyasi bazada; `alembic_version = 0010`"
  - "`tests/fixtures/market_domain.py` — ikki bozorli domen seed'i (`MarketDomainSeed`)"
  - "`market_domain` pytest fixture'i (`two_markets` ustiga qatlanadi)"
  - "`tests/fixtures/market_domain.to_pg_period()` — testlar uchun `[)` yagona manbai"
  - "`test_autogenerate_is_empty` endi ENTITY qatlamini (policy + funksiya) ham qamraydi"
affects: [02-07, 02-08, 02-09, 02-10, 02-11, 02-12, 02-13, 02-14, 02-15, 02-16, 02-17, 06-hisob-kitob]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "`EXCLUDE` konstrayti migratsiyada LITERAL yoziladi va meta-test bilan qulflanadi — Alembic uni na yaratadi, na yo'qolganini sezadi (sabotaj bilan qayta tasdiqlandi)"
    - "Nazorat holati + rad etish JUFTLIGI: qo'shni davrlar qabul qilinadi (yashil qoladi) + qoplanish rad etiladi (qizaradi) — sabotajda ikkalasining farqi ko'rindi"
    - "Seed teardown'i mahsulotning O'Z istisnosiga tayanadi: qoralamaga tushirish (`market_delete_draft()` bilan bir xil mexanizm)"
    - "`PENDING_*` qarz reyestri bo'shaganda darvoza KENGAYADI — filtr olib tashlanadi, yashirish qoldirilmaydi"

key-files:
  created:
    - migrations/versions/0009_vendors.py
    - migrations/versions/0010_calendar.py
    - tests/fixtures/market_domain.py
  modified:
    - tests/conftest.py
    - tests/fixtures/__init__.py
    - tests/tenancy/test_market_domain_meta.py
    - tests/tenancy/test_meta.py

key-decisions:
  - "`PENDING_*` ro'yxatlari IKKI BOSQICHDA bo'shatildi (Task 1 da 2 nom, Task 2 da 1 nom) — 02-05 naqshi, har bir commit o'z-o'zicha yashil bo'lishi uchun"
  - "`cleanup_market_domain()` avval `markets.is_active = false` qiladi — usiz D-07 qulfi tozalashni `23514` bilan yiqitardi (o'lchangan zaruriyat)"
  - "`test_autogenerate_is_empty` dan `_clear_entity_registry()` va `include_object` OLIB TASHLANDI — to'liq solishtiruv 0 diff berishi o'lchandi, ya'ni darvoza kengaydi"
  - "`market_is_open` reyestrdan chetda ekani ALOHIDA test bilan qulflandi (`test_market_is_open_is_absent_from_definer_registry`) — izoh yolg'iz yetarli emas edi"
  - "Seed B bozorida bitta toifani ATAYIN tarifsiz qoldiradi — 02-11 `activate` to'liqlik tekshiruvi uchun manfiy holat"
  - "Seed telefoni A va B bozorida QASDDAN bir xil — global `UNIQUE(phone_e164)` qo'yilsa seed darhol yiqiladi (D-12/T-02-44 ning tirik darvozasi)"

patterns-established:
  - "Pattern: sabotaj tekshiruvi darvozaning KUCHINI ham o'lchaydi — nechta test yiqilgani va QAYSILARI yashil qolgani ikkalasi ham ma'lumot"
  - "Pattern: seed konstantalari (`HANDOVER_DAY`, `GAP_DAY`) testdan EMAS, seed modulidan keladi — downstream testlar sanani qayta yozmaydi"
  - "Pattern: kutilgan tartib QO'LDA yoziladi (`A_STALL_CODES_BY_SORT`), hisoblab chiqarilmaydi — hisoblangan kutilma DB ifodasining mantiqini takrorlardi"

requirements-completed: []

# Metrics
duration: 78min
completed: 2026-07-31
---

# Phase 2 Plan 06: Sotuvchilar, kalendar va domen seed'i Summary

**2-fazaning sxema qurilishi yakunlandi — o'nta domen jadvali, beshta bozor funksiyasi va ikki bozorli domen seed'i `postgres:18.4-trixie` da ishlaydi; Alembic KO'RMAYDIGAN `EXCLUDE USING gist` kafolati sabotaj bilan tekshirildi va o'sha sabotajda `test_autogenerate_is_empty` YASHIL qoldi — ya'ni Pitfall 2 bu kod bazasida qayta o'lchandi va meta-test haqiqatan yagona darvoza ekani isbotlandi.**

## Performance

- **Duration:** ~78 min (transport uzilishi bilan birga)
- **Tasks:** 3/3
- **Files:** 7 (3 yaratildi, 4 o'zgartirildi)
- **Testlar:** 460 → **472** (+12)

## Accomplishments

- **`EXCLUDE` darvozasi SABOTAJ bilan o'lchandi va natija darvozaning kuchini aniq ko'rsatdi.** Konstrayt migratsiyadan olib tashlanganda AYNAN uchta test yiqildi (`..._has_exclusion_constraint`, `..._index_leads_with_market_id`, `..._overlapping_assignment_is_rejected`), **nazorat holati `test_adjacent_assignments_are_accepted` esa YASHIL QOLDI** — ya'ni u haqiqiy nazorat, rad etish testining nusxasi emas. Eng muhimi: **`test_autogenerate_is_empty` ham yashil qoldi**, ya'ni RESEARCH Pitfall 2 ("Alembic EXCLUDE yo'qolganini sezmaydi") bu kod bazasida, bu Alembic versiyasida qayta tasdiqlandi.
- **D-10 almashinuvi DB ichida o'lchandi:** `[2026-08-01, 2026-08-10)` + `[2026-08-10, ∞)` — almashinuv kunida `period @> '2026-08-10'` AYNAN BITTA qator qaytardi va u YANGI sotuvchiniki. Qoplanuvchi uchinchi davr `23P01` bilan rad etildi.
- **D-11 ning ikkala shakli ham seed'da tirik:** bo'shliq kunida (`2026-08-10`, boshqa rasta) `period @> :d` **0 qator**; uchinchi rasta umuman biriktirilmagan. Ikkalasi ham test bilan qulflangan.
- **`market_is_open()` ning uchala qavati va CROSS-TENANT yo'li NAZORAT HOLATI bilan o'lchandi.** A konteksti ostida `market_is_open(B, seshanba)` → `false`; **B kontekstiga o'tilganda AYNI so'rov `true`** — ya'ni `false` javob RLS izolyatsiyasidan keladi, funksiyaning buzuqligidan emas. Bu nazorat holatisiz test hech narsani isbotlamasdi.
- **`market_delete_draft()` to'la qoralamada 11 jadvalning hammasini bo'shatdi** (`{stall_assignments: 0, …, markets: 0}`), faol bozorda esa `false` qaytarib BIRORTA qatorga tegmadi.
- **Qarz to'liq yopildi:** `PENDING_AUDIT_TRIGGERS` va `PENDING_DOMAIN_TABLES` ikkalasi ham BO'SH. Natijada `test_autogenerate_is_empty` `include_object` filtrisiz va reyestr bo'shatishsiz ishlaydi — u endi policy va funksiya qatlamini ham qamraydi (**to'liq diff = 0 element**, o'lchandi).
- **Migratsiyalar uch yo'nalishda ham aylandi:** `downgrade 0009` / `0008` / `0006` → har birida `upgrade head`, hammasi exit 0. Yakuniy holat: `alembic_version = 0010`, `public` sxemada 16 jadval.

## Task Commits

1. **Task 1: `0009_vendors.py` — sotuvchilar va qoplanmaydigan biriktirish davrlari** — `8a94637` (feat)
2. **Task 2: `0010_calendar.py` — ish kunlari istisnolari va qolgan ikki funksiya** — `2675843` (feat)
3. **Task 3: Ikki bozorli domen seed'i va EXCLUDE/`market_is_open` darvozalari** — `b2fe5c6` (test)

## Files Created/Modified

**Yaratildi**

- `migrations/versions/0009_vendors.py` — `vendors` + `stall_assignments` + `EXCLUDE USING gist` + RLS/policy + ikkita audit triggeri. Fayl docstringi `0008` ga QARSHI qo'yiladi: nega u yerda `daterange` xato edi, bu yerda esa to'g'ri (uch nuqta: davr haqiqatan yopiladi / bo'shliq ma'noli / o'tmishni yopish taqiqlanmagan).
- `migrations/versions/0010_calendar.py` — `market_calendar_exceptions` + RLS/policy/audit + `market_is_open()` (INVOKER) + `market_delete_draft()` (DEFINER) + GRANT/REVOKE juftliklari. Docstringda fail-closed'ning NARXI va nega teskari standart (`true`) TANLANMAGANI ochiq yozilgan.
- `tests/fixtures/market_domain.py` — `MarketDomainSeed`/`MarketDomainRows` + `seed_market_domain()` + `cleanup_market_domain()` + `to_pg_period()`. Modul docstringi har bir seed elementini AYNAN bir downstream testga bog'laydi.

**O'zgartirildi**

- `tests/conftest.py` — `market_domain` fixture'i (`two_markets` ustiga qatlanadi; docstringda fixture teardown TARTIBI nega ahamiyatli ekani).
- `tests/fixtures/__init__.py` — seed eksportlari.
- `tests/tenancy/test_market_domain_meta.py` — 10 → **21 test**; `PENDING_DOMAIN_TABLES` bo'shatildi; `test_autogenerate_is_empty` soddalashtirildi va KENGAYTIRILDI.
- `tests/tenancy/test_meta.py` — `PENDING_AUDIT_TRIGGERS` bo'shatildi; `EXPECTED_DEFINER_FUNCTIONS` ga `market_delete_draft`; yangi `test_market_is_open_is_absent_from_definer_registry`.

## Decisions Made

- **`PENDING_*` ro'yxatlari ikki bosqichda bo'shatildi.** Task 1 `vendors`/`stall_assignments` ni, Task 2 `market_calendar_exceptions` ni o'chirdi. Bitta qadamda qilinganda Task 1 commit'i o'z-o'zicha QIZIL bo'lardi (jadvali hali yo'q trigger talab qilinardi). Bu 02-05 dagi aynan o'sha qaror.
- **`test_autogenerate_is_empty` dan reyestr bo'shatish OLIB TASHLANDI.** 02-05 uni "avval o'lchang" deb qarz sifatida qoldirgan edi. O'lchandi: reyestr TO'LIQ holatda (`env.py` dagidek) `compare_metadata()` **0 element** qaytaradi. Filtr ham olib tashlandi — `PENDING_DOMAIN_TABLES` bo'sh bo'lgani uchun u hech nimani chiqarmasdi va faqat "vaqtincha" degan yolg'on taassurot qoldirardi. Docstringda uni QAYTA TIKLASH taqiqlangan va to'g'ri yechim ko'rsatilgan.
- **`market_is_open` reyestrdan chetda ekani ALOHIDA test bilan qulflandi.** 02-05 buni faqat IZOH bilan belgilagan edi. Izoh keyingi ishlovchini to'xtatmaydi: u `EXPECTED_DEFINER_FUNCTIONS` ga nom qo'shsa, `test_security_definer_functions_pin_search_path` uni `SECURITY DEFINER` QILISHNI talab qilib qizarardi va eng tabiiy "tuzatish" aynan T-02-41 ni ochish bo'lardi. Endi test o'sha yo'lni boshidayoq to'sadi.
- **Seed B bozorida bitta toifa TARIFSIZ.** 02-11 dagi `activate` to'liqlik tekshiruvi ("har toifada tarif bor") uchun manfiy holat kerak — aks holda u faqat baxtli yo'lda sinalardi.
- **Seed telefoni A va B da bir xil.** D-12 (unikalik BOZOR ICHIDA) ni seed'ning O'ZIDA ifodalaydi: kimdir `UNIQUE(phone_e164)` ni global qilib qo'ysa seed darhol yiqiladi. Global hisoblagich ATAYIN ishlatilmadi va sabab docstringda (`users.phone_e164` dan farqi).
- **Kutilgan tartib QO'LDA yozildi** (`A_STALL_CODES_BY_SORT = ("2","3","7","10","55","100")`), `sorted(..., key=int)` bilan hisoblanmadi — hisoblangan kutilma `code_sort` ifodasining o'z mantiqini takrorlardi va ikkalasi birga xato bo'lganda test yashil qolardi.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Seed teardown'i D-07 qulfiga urilib yiqilardi**

- **Found during:** Task 3
- **Issue:** Reja seed'ning tarif va toifa davrlari uchun `valid_from = market_profile.operating_since` ni TALAB qiladi va `operating_since` ni "**o'tgan sana** bo'lsin" deb belgilaydi (A3). Ayni paytda seed `two_markets` ustiga qatlanadi, u esa bozorlarni `INSERT INTO markets (id, name)` bilan yaratadi va `markets.is_active` ning server standarti — `true`. Ya'ni seed bozorlari FAOL. `trg_tariff_past_immutable` va `trg_category_period_past_immutable` esa aynan shu juftlikni qulflaydi: faol bozorda `valid_from <= bugun` bo'lgan qatorni **o'chirish** ham `23514` beradi (D-07 `BEFORE UPDATE OR DELETE`). Natijada `cleanup_market_domain()` BIRINCHI `DELETE FROM tariffs` da yiqilardi, har bir test keyingisiga qoldiq qator qoldirardi va cross-tenant testlar o'sha qoldiq ustida jimgina noto'g'ri javob berardi. Rejaning ikki talabi (o'tgan sana + FK tartibida tozalash) bir-birini inkor qiladi.
- **Fix:** `cleanup_market_domain()` o'chirishdan OLDIN `UPDATE markets SET is_active = false` qiladi. Bu mahsulotning O'Z mexanizmi: ikkala qo'riqchi ham qoralama bozorni istisno qiladi va `market_delete_draft()` aynan shunga tayanadi (02-04 deviatsiya #3). Semantik jihatdan halol — qator bir necha satr keyin `cleanup_two_markets()` tomonidan butunlay o'chiriladi.
- **Rad etilgan muqobillar (docstringda yozilgan):** `ALTER TABLE ... DISABLE TRIGGER` — qo'riqchini butunlay o'chiradi va ROSTDAN buzilgan holatni ham yashirardi; kelajakdagi `valid_from` — A3 ni buzardi va 6-faza uchun butun tarixni tarifsiz qoldirardi.
- **Files modified:** `tests/fixtures/market_domain.py`
- **Verification:** `test_market_domain_cleanup_leaves_no_rows` — seed/cleanup TO'G'RIDAN-TO'G'RI chaqiriladi va to'qqizta jadvalning hammasida 0 qator tekshiriladi
- **Committed in:** `b2fe5c6`

**2. [Rule 3 - Blocking] `PENDING_*` ro'yxatlari 1- va 2-vazifalarda bo'shatilishi SHART edi**

- **Found during:** Task 1
- **Issue:** Reja ikkala ro'yxatni ham 3-vazifaga qo'yadi (`files` ro'yxatida ular faqat Task 3 da). Lekin ro'yxatlar IKKI TOMONLAMA (`==` solishtiruvi): jadval tug'ilishi bilanoq `missing` kichrayadi va test QIZARADI. Ya'ni Task 1 commit'i `0009` ni qo'shib ro'yxatlarga tegmasa, o'sha commit o'z-o'zicha QIZIL bo'lardi va "har bir vazifa yashil commit qoldiradi" kafolati buzilardi.
- **Fix:** 02-05 ning O'Z naqshi takrorlandi (u ham `PENDING_AUDIT_TRIGGERS` ni ikki bosqichda qisqartirgan): Task 1 `vendors`/`stall_assignments` ni, Task 2 `market_calendar_exceptions` ni o'chirdi. Rejaning yakuniy holati o'zgarmadi — ikkala ro'yxat ham BO'SH.
- **Files modified:** `tests/tenancy/test_meta.py`, `tests/tenancy/test_market_domain_meta.py`
- **Verification:** Har uchala commit'da `pytest tests/tenancy -q` exit 0
- **Committed in:** `8a94637`, `2675843`

**3. [Rule 2 - Missing Critical] Reyestr izohi keyingi ishlovchini to'xtatmaydi**

- **Found during:** Task 3
- **Issue:** Reja `market_is_open` ni `EXPECTED_DEFINER_FUNCTIONS` ga qo'shMASlikni va "buni izoh bilan qayd etish" ni aytadi (02-05 shunday qilgan). Lekin izoh — passiv himoya. `test_security_definer_functions_pin_search_path` ning da'vosi `found >= EXPECTED_DEFINER_FUNCTIONS`, ya'ni nom qo'shilsa test funksiyani `SECURITY DEFINER` QILISHNI talab qilib qizaradi. Xatoni o'qigan odam uchun eng tabiiy "tuzatish" — migratsiyada funksiyaga `SECURITY DEFINER` qo'shish, ya'ni AYNAN T-02-41 ni ochish (funksiya RLS'dan chiqadi va bir bozor boshqasining bayram jadvalini o'qiy oladi). Izoh o'sha paytda allaqachon "eskirgan qoldiq" ko'rinishida bo'lardi.
- **Fix:** `test_market_is_open_is_absent_from_definer_registry` qo'shildi — REYESTRNING o'zini qulflaydi (`market_is_open` YO'Q, `market_delete_draft` BOR). Test `test_meta.py` da, konstanta yonida joylashtirildi; `test_market_domain_meta.py` dan cross-modul import qilish TANLANMADI, chunki `tests/` da `__init__.py` yo'q va `tests.tenancy.test_meta` / `tenancy.test_meta` ikkita alohida modul obyekti hosil qilardi.
- **Files modified:** `tests/tenancy/test_meta.py`
- **Verification:** Ikkala assertion ham tirik; baza tomonidagi jufti `test_market_is_open_is_not_security_definer`
- **Committed in:** `b2fe5c6`

**4. [Rule 2 - Missing Critical] Qarz yopilgach darvoza KENGAYTIRILMASA, u qisqargan holida qolardi**

- **Found during:** Task 3
- **Issue:** Reja `PENDING_DOMAIN_TABLES` ni bo'shatishni talab qiladi, lekin `test_autogenerate_is_empty` ichidagi `_clear_entity_registry()` blokini va `include_object` filtrini olib tashlashni TALAB QILMAYDI (02-05 uni "avval o'lchang" degan eslatma sifatida qoldirgan). Ular qolganda test ishlashda davom etardi va hech kim sezmasdi — LEKIN policy va funksiya qatlami solishtiruvdan CHETDA qolaverardi, ya'ni 02-05 hujjatlashtirgan qarz "yopilgan" deb ko'rinib aslida ochiq qolardi.
- **Fix:** O'lchandi — reyestr TO'LIQ holatda `compare_metadata()` **0 element** qaytaradi. Ikkala vaqtinchalik konstruksiya ham olib tashlandi, `_clear_entity_registry()` yordamchisi va endi keraksiz uchta import (`register_entities`, `registry`, `PGPolicy`/`PGFunction`, `ALL_ENTITIES`) o'chirildi. Docstringda o'lchov, kengayishning MA'NOSI va "reyestr bo'shatishni QAYTA TIKLAMANG" ogohlantirishi (to'g'ri yechim ko'rsatilgan holda) yozildi.
- **Files modified:** `tests/tenancy/test_market_domain_meta.py`
- **Verification:** To'liq diff = 0 element (alohida probe bilan), so'ng 472 testli to'plamda ham yashil
- **Committed in:** `b2fe5c6`

---

**Total deviations:** 4 auto-fixed (2 blocking, 2 missing-critical). Rule 4 (arxitektura) holati bo'lmadi.
**Impact on plan:** Qamrov kengaytmasi yo'q — birorta yangi jadval, funksiya yoki paket rejadan tashqari qo'shilmadi. #1 rejaning ikki talabi (o'tgan `valid_from` + tozalash) orasidagi HAQIQIY ziddiyat; #2 rejaning vazifa taqsimoti bilan "har commit yashil" qoidasi orasidagi ziddiyat; #3 va #4 darvozalarni passiv izohdan tirik testga ko'chiradi.

## Empirik o'lchovlar (vaqtinchalik probe bilan, commit'dan OLDIN o'chirildi)

To'rtta vaqtinchalik pytest fayli haqiqiy `postgres:18.4-trixie` konteynerida bajarildi va o'lchovdan keyin o'chirildi (02-04/02-05 naqshi).

| O'lchov | Natija |
|---|---|
| `pg_get_constraintdef` | ✅ `EXCLUDE USING gist (market_id WITH =, stall_id WITH =, period WITH &&)` |
| EXCLUDE indeksining birinchi ustuni / access method | ✅ `market_id` / `gist` |
| `stall_assignments` ustunlari | ✅ `market_id, id, stall_id, vendor_id, period, created_at` (`updated_at` va pul ustuni YO'Q) |
| Qo'shni davrlar (`[08-01,08-10)` + `[08-10,∞)`) | ✅ ikkalasi qabul qilindi |
| Qoplanuvchi davr (`[08-05,08-20)`) | ✅ `23P01` |
| EXCLUDE xato matni RLS ostida | ✅ `DETAIL: Key conflicts with existing key.` — qiymatlar YASHIRILGAN (Pitfall 4) |
| Almashinuv kuni (`08-10`) egasi | ✅ AYNAN 1 qator, YANGI sotuvchi |
| Bo'shliq kuni `period @> :d` | ✅ 0 qator |
| Bir bozorda takroriy telefon | ✅ `23505` |
| BOSHQA bozorda bir xil telefon | ✅ qabul qilindi |
| `market_is_open` `prosecdef`/`provolatile`/`proconfig` | ✅ `False` / `'s'` / `['search_path=pg_catalog, public']` |
| `market_is_open` PUBLIC / `sbozor_app` | ✅ `False` / `True` |
| `market_delete_draft` `prosecdef` / PUBLIC / app | ✅ `True` / `False` / `True` |
| A haftalik jadval (dushanba yopiq) | ✅ dushanba `False`, seshanba `True` |
| Istisno `is_open=true` dushanbaga | ✅ `True` (haftalik jadvaldan USTUN) |
| Bayram `is_open=false` seshanbaga | ✅ `False` |
| CROSS-TENANT `market_is_open(B, ...)` A konteksti ostida | ✅ `False` |
| **NAZORAT:** AYNI so'rov B konteksti ostida | ✅ `True` |
| Profilsiz bozor (fail-closed, o'z konteksti) | ✅ `False` |
| `market_calendar_exceptions` audit qatori | ✅ 1 |
| `market_delete_draft(FAOL)` | ✅ `False`, bozor qatori QOLDI |
| `market_delete_draft(QORALAMA)` | ✅ `True`, 11 jadvalda 0 qator |
| To'liq `compare_metadata()` (reyestr TO'LIQ holatda) | ✅ **0 element** |
| `downgrade 0009` / `0008` / `0006` → `upgrade head` | ✅ uchalasi ham exit 0 |
| Yakuniy holat | ✅ `alembic_version = 0010`, `public` da 16 jadval |

**Sabotaj tekshiruvi (`ExcludeConstraint` migratsiyadan olib tashlandi):**

| Test | Sabotajda |
|---|---|
| `test_stall_assignments_has_exclusion_constraint` | ❌ YIQILDI (kutilgan) |
| `test_exclusion_index_leads_with_market_id` | ❌ YIQILDI (kutilgan) |
| `test_overlapping_assignment_is_rejected` | ❌ YIQILDI — `DID NOT RAISE ExclusionViolation` |
| `test_adjacent_assignments_are_accepted` (NAZORAT) | ✅ yashil qoldi — nazorat haqiqiy |
| `test_autogenerate_is_empty` | ✅ **yashil qoldi — Pitfall 2 qayta tasdiqlandi** |

Migratsiya `git checkout` bilan bit-ba-bit tiklandi (`git diff` bo'sh, `ExcludeConstraint` 2 ta ko'rinish).

## Issues Encountered

- **`.env` worktree'da yo'q** (gitignore), ya'ni `npm run migrate` ishlamaydi. Ekvivalent qamrov: `migrated` fixture'i AYNAN `alembic upgrade head` ni `alembic.command` API'si bilan, `sbozor_owner` roli bilan va haqiqiy konteynerda bajaradi — 472 testning har birida. Downgrade aylanalari ham shu yo'l bilan o'lchandi.
- **Probe'da `DATE %s` sintaksis xatosi berdi** (`syntax error at or near "$2"`): `DATE` literal prefiksi bind parametr bilan ishlamaydi, `%s::date` kerak. Bu PROBE xatosi edi, mahsulot xatosi emas — lekin u 02-07 dagi so'rovlarni yozadigan ishlovchi uchun ham amal qiladi.
- **`ruff format` uch marta uzun konstruksiyani qayta formatladi** (bitta `op.create_index`, ikkita parametr tuple'i) va `mypy --strict` bitta `dict` uchun annotatsiya talab qildi. Hammasi qator uzunligi/tip annotatsiyasi darajasida.
- **Cross-modul test importi TANLANMADI:** `tests/` da `__init__.py` yo'q, ya'ni `tests.tenancy.test_meta` va `tenancy.test_meta` ikkita alohida modul obyekti bo'lardi (pytest o'zi ikkinchisi bilan import qiladi). Reyestr testi konstanta yashaydigan faylga qo'yildi.

## Known Stubs

Yo'q. Bu rejadagi barcha DDL bajarildi, seed'ning barcha elementlari yozildi va birorta test `skip`/`xfail` bilan yozilmadi. Rejadagi `PENDING_*` qarzi — 2-fazadagi oxirgi ochiq element edi — **to'liq yopildi**.

**Ataylab ochiq qoldirilgan, ko'rinadigan qarz (stub emas):**

| Qarz | Kim yopadi | Bugungi holati |
|---|---|---|
| `market_calendar_exceptions` seed'da BO'SH | 02-10 (kalendar API'si) | `CLEANUP_ORDER` da ATAYIN bor — kalendar testlari o'z istisnolarini qo'shadi va tozalanadi |
| B bozorining ikkinchi toifasi TARIFSIZ | 02-11 (`activate` to'liqlik tekshiruvi) | ATAYIN nuqson — manfiy holat fixture'i (modul docstringida) |
| Sotuvchini ikki bozorda YAGONA shaxs sifatida birlashtirish | v2 (Deferred Ideas) | T-02-44 `accept`; seed shu holatni bir xil telefon bilan ifodalaydi |

## Threat Flags

Yangi xavfsizlik yuzasi yo'q — yangi endpoint, fayl kirishi yoki tashqi bog'liqlik qo'shilmadi. Rejaning `<threat_model>` idagi dispozitsiyalar:

| Threat ID | Holat |
|-----------|-------|
| T-02-37 | mitigate — `EXCLUDE USING gist`; `23P01` o'lchandi, sabotaj bilan darvoza haqiqatan yopilishi isbotlandi |
| T-02-38 | mitigate — `fk_stall_assignments_market_id_vendor_id_vendors` composite FK; `compare_metadata()` diff 0 uning modeldagidek turganini isbotlaydi |
| T-02-39 | mitigate — `attach_audit_trigger("stall_assignments")`; `PENDING_AUDIT_TRIGGERS` bo'shatildi, ya'ni `test_audited_tables_have_trigger` endi uni TALAB qiladi |
| T-02-40 | mitigate — `market_calendar_exceptions` audit triggeri + `UNIQUE(market_id, exception_date)`; `test_market_calendar_exceptions_is_audited` INSERT/UPDATE/**DELETE** uchalasini ham tekshiradi |
| T-02-41 | mitigate — `market_is_open()` INVOKER (`prosecdef=False` o'lchandi); cross-tenant `false` **nazorat holati bilan**; reyestr ham alohida test bilan qulflangan |
| T-02-42 | mitigate — fail-closed narxi `0010` docstringida ochiq yozilgan; profilsiz bozor `false` o'lchandi; `market_create()` profilni bir tranzaksiyada yaratadi |
| T-02-43 | mitigate — `test_stall_assignments_has_exclusion_constraint`; **sabotaj bilan tasdiqlandi**: konstrayt olib tashlanganda u yiqildi, `test_autogenerate_is_empty` esa yashil qoldi |
| T-02-44 | accept (aniqlangan) — `UNIQUE(market_id, phone_e164)`; seed A va B da bir xil telefon ishlatib qarorni TIRIK darvozaga aylantirdi |
| T-02-45 | mitigate — `market_delete_draft(FAOL)` → `false` va 0 qator o'chdi (o'lchandi); `EXPECTED_DEFINER_FUNCTIONS` ga qo'shildi |
| T-02-45a | mitigate — seed har rastaga toifa davri yozadi; `test_seeded_stalls_have_a_category_period` + `test_seeded_category_periods_use_more_than_one_category` |

## Verification Results

| # | Buyruq | Natija |
|---|--------|--------|
| 1 | `alembic upgrade head` | ✅ nol holatdan `0001` → `0010` (`migrated` fixture'i orqali) |
| 2 | `downgrade 0009` → `upgrade head` | ✅ exit 0 |
| 2b | `downgrade 0008` → `upgrade head` | ✅ exit 0 |
| 2c | `downgrade 0006` → `upgrade head` | ✅ exit 0 |
| 3 | To'liq `compare_metadata()` (entity qatlami bilan) | ✅ **0 element** |
| 4 | `pytest tests/tenancy -q` | ✅ **123 test** (02-05 dagi 111 + 12 yangi) |
| 5 | `pytest tests/tenancy/test_market_domain_meta.py --collect-only` | ✅ **21 test** (talab: ≥15) |
| 6 | `pytest -q` (to'liq) | ✅ **472 passed** (02-05 dagi 460 + 12) |
| 7 | `ruff check . && ruff format --check . && mypy .` | ✅ exit 0 (98 fayl, 97 manba) |

**Task 1 qabul mezonlari (o'lchangan):**

| Mezon | Natija |
|-------|--------|
| `upgrade head` + `downgrade 0008` → `upgrade head` | ✅ ikkalasi ham |
| `pg_get_constraintdef` da to'rtta element | ✅ `EXCLUDE USING gist`, `market_id`, `stall_id`, `&&` |
| `test_tenant_indexes_lead_with_market_id` EXCLUDE indeksini qabul qiladi | ✅ (birinchi ustun `market_id`) |
| Ikkala qo'shni davr qabul qilinadi | ✅ |
| Qoplanuvchi davr `23P01` | ✅ |
| Bo'shliq kunida 0 qator | ✅ |
| Bir bozorda `23505`; boshqa bozorda qabul | ✅ ikkalasi ham |
| `updated_at` va pul ustuni YO'Q | ✅ |
| `CREATE EXTENSION` satri YO'Q, `require_extension` birinchi satr | ✅ |

**Task 2 qabul mezonlari (o'lchangan):**

| Mezon | Natija |
|-------|--------|
| `upgrade head` + `downgrade 0009` → `upgrade head` | ✅ ikkalasi ham |
| `prosecdef` / `provolatile` / `proconfig` | ✅ `false` / `s` / `search_path=pg_catalog, public` |
| Dushanba haftalik jadvalda yo'q → `false` | ✅ |
| Istisno `is_open=true` → `true` | ✅ |
| Bayram `is_open=false` → `false` | ✅ |
| Cross-tenant → `false` (+ nazorat: o'z konteksti `true`) | ✅ ikkalasi ham |
| Profilsiz bozor → `false` | ✅ |
| `market_delete_draft(faol)` → `false`, qator qoldi | ✅ |
| `market_delete_draft(qoralama)` → `true`, qatorlar o'chdi | ✅ |
| `alembic revision --autogenerate` bo'sh diff | ✅ 0 element |

**Task 3 qabul mezonlari (o'lchangan):**

| Mezon | Natija |
|-------|--------|
| `pytest tests/tenancy -q` exit 0 | ✅ 123 test |
| `test_market_domain_meta.py` da ≥15 test | ✅ **21** |
| `market_domain` `two_markets` ga bog'liq, ikkala bozorda qator yaratadi | ✅ |
| Har rastada toifa davri, `valid_from` = `operating_since` | ✅ (A: 6/6, B: 2/2) |
| Toifa davrlari ≥2 xil `category_id` | ✅ (A da 3 xil) |
| `market_domain.py` da xom `daterange(` / `"[)"` YO'Q | ✅ (`grep` bilan, hammasi `to_pg_period()` orqali) |
| Nazorat + rad etish juftligi mavjud va yashil | ✅ (sabotajda farqi ko'rindi) |
| `test_seeded_stalls_have_a_category_period` | ✅ |
| `test_market_is_open_is_not_security_definer` | ✅ |
| `EXPECTED_DEFINER_FUNCTIONS`: `market_delete_draft` BOR, `market_is_open` YO'Q | ✅ (test bilan qulflandi) |
| `ORDER BY code_sort` → `2, 3, 7, 10, 55, 100` | ✅ (+ nazorat: `ORDER BY code` boshqacha) |
| `cleanup_market_domain()` dan keyin 0 qator | ✅ (9 jadval) |
| `pytest -q` (butun to'plam) | ✅ 472 passed |

## User Setup Required

Yo'q — tashqi servis sozlamasi kerak emas.

**⚠ DEPLOY ESLATMASI — BU REJA UNI BIRINCHI MARTA TIRIK QILADI:** `0009_vendors` `btree_gist` kengaytmasini TALAB qiladi va uni O'ZI o'rnata olmaydi (`sbozor_owner` — `permission denied to create extension`). `ops/db/init/00-extensions.sql` faqat BO'SH data katalogida avtomatik ishlaydi. **Mavjud bazada** migratsiya `RuntimeError` bilan to'xtaydi va xato matni to'g'ri buyruqni o'zi ko'rsatadi:

```
psql -U postgres -d <db> -c "CREATE EXTENSION IF NOT EXISTS btree_gist;"
```

Bu 02-01 dan meros eslatma edi; `0007`/`0008` uni talab qilmagan, `0009` esa talab qiladi.

## REQUIREMENTS.md holati — ATAYIN belgilanmadi

Reja frontmatteri `requirements: [MARKET-04, MARKET-05]` deb yozgan, lekin bu reja **sxemani** beradi, foydalanuvchi ko'radigan qobiliyatni emas: sotuvchi reestri va biriktirish UI/API'si (MARKET-04) hamda kalendar boshqaruvi (MARKET-05) 02-07…02-17 rejalarida quriladi. Ularni bu yerda "bajarildi" deb belgilash traceability jadvalini yolg'on qilardi (02-04/02-05 SUMMARY'laridagi bilan bir xil sabab).

Qo'shimcha texnik sabab: bu agent **worktree'da** ishlaydi va `REQUIREMENTS.md` — orkestrator egalik qiladigan umumiy artefakt.

## Next Phase Readiness

**Sxema TUGADI.** 02-07 va keyingi rejalar uchun bazadagi holat: o'nta domen jadvali, beshta bozor funksiyasi, `alembic_version = 0010`.

**02-07+ (API rejalari) uchun kontrakt:**

- **Xatolarni FAQAT `sqlstate` bo'yicha ajrating.** RLS yoqilgan jadvalda `DETAIL` qatori yo'q va `exc.orig.constraint_name` asyncpg o'ramida `None` (ikkalasi ham o'lchangan):
  `23P01` → `409 assignment_period_overlaps` · `23505` → `409` (telefon band / rasta kodi band) · `23514` → `403` (o'tgan sanani tahrirlash).
- **Davr qurish yo'li YAGONA:** `sbozor_core.periods.assignment_period()`. Testlarda — `fixtures.market_domain.to_pg_period()`. Xom `daterange(...)` yozilmaydi.
- **"Bugun kim biriktirilgan"** — `period @> :d` (GiST indeksidan foydalanadi), `period_contains()` EMAS.
- **"Shu sotuvchining rastalari"** — `ix_stall_assignments_market_id_vendor_id` mavjud.
- **Bozor ishlaydimi** — `WHERE market_is_open(:market_id, :business_date)`, bitta shart. U INVOKER, ya'ni tenant konteksti O'RNATILGAN bo'lishi SHART — aks holda fail-closed `false` qaytaradi.
- **`market_delete_draft()` `false` qaytarganda ikki holat bor** (faol yoki topilmadi) — chaqiruvchi ularni ajratishi kerak bo'lsa avval `markets` ni o'qisin.
- **Sana bind parametri:** `%s::date` yozing, `DATE %s` EMAS (sintaksis xatosi beradi).

**02-08 (rasta ro'yxati / xarita) uchun:**

- `market_domain` fixture'i tayyor: A bozorida 6 rasta, har birida toifa davri, uch xil biriktirish holati. `MarketDomainRows.category_by_stall` — `LEFT JOIN LATERAL` natijasini solishtirish uchun kutilma.
- Tartib — `ORDER BY code_sort` (kursor `(code_sort, id)`). Seed kodlari matn tartibidan ATAYIN farq qiladi.

**02-11 (`setup-status` / `activate`) uchun:**

- `stalls_with_category` sanog'i `stall_category_periods` dan o'qiladi — seed har rastaga qator yozadi, ya'ni A bozori to'liq, B bozori esa **bitta toifasi tarifsiz** (manfiy holat tayyor).
- `activate` to'liqlik tekshiruvi `open_weekdays` ni ham talab qilishi SHART (fail-closed narxi).

**6-faza uchun:** almashinuv kunidagi patta YANGI sotuvchiga yoziladi (`[)`, o'lchangan); bo'shliq kuni 0 qator beradi va bu "sotuvchisiz band rasta" anomaliyasi.

## Self-Check: PASSED

- Da'vo qilingan 3 yangi fayl diskda mavjud: `migrations/versions/0009_vendors.py`, `migrations/versions/0010_calendar.py`, `tests/fixtures/market_domain.py`
- Da'vo qilingan 4 o'zgartirilgan fayl `git diff --stat f71aaf3..HEAD` da ko'rinadi: `tests/conftest.py`, `tests/fixtures/__init__.py`, `tests/tenancy/test_market_domain_meta.py`, `tests/tenancy/test_meta.py`
- Uchala vazifa commit'i git tarixida mavjud: `8a94637`, `2675843`, `b2fe5c6`
- Birorta commit'da fayl o'chirilishi yo'q (`git diff --diff-filter=D` uchalasida ham bo'sh)
- To'rtta vaqtinchalik probe fayli commit'dan OLDIN o'chirildi; ishchi daraxtda kuzatilmagan fayl qolmadi
- Sabotaj tekshiruvidan keyin migratsiya bit-ba-bit tiklandi (`git diff` bo'sh)
- `STATE.md`, `ROADMAP.md` va `REQUIREMENTS.md` TEGILMADI (worktree rejimi — orkestrator egalik qiladi)

---
*Phase: 02-bozor-domeni-va-yangi-bozor-ustasi*
*Completed: 2026-07-31*
