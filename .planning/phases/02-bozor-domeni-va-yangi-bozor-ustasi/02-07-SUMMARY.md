---
phase: 02-bozor-domeni-va-yangi-bozor-ustasi
plan: 07
subsystem: testing
tags: [integration, postgres, trigger, rls, daterange, audit, fail-closed, sabotage]

# Dependency graph
requires:
  - phase: 02-bozor-domeni-va-yangi-bozor-ustasi
    provides: "02-06 — `market_domain` fixture'i (ikki bozorli domen seed'i), `to_pg_period()`, `0009`/`0010` migratsiyalari, `alembic_version = 0010`; 02-05 — `trg_tariff_past_immutable`/`trg_category_period_past_immutable`, `trg_stall_code_claim`; 02-04 — `sbozor_core.periods.PERIOD_BOUNDS`/`assignment_period()`, `StallStatus`, `market_is_open()` INVOKER qarori"
  - phase: 01-poydevor-va-tenant-xavfsizligi
    provides: "`sync_app_conn`/`sync_owner_conn`/`migrated` fixture'lari, `fn_audit_row()`, `audit_read` policy'si, `two_markets` seed'i"
provides:
  - "`tests/integration/test_tariff_history.py` — SC#3 ning to'liq isboti (9 test)"
  - "`tests/integration/test_category_history.py` — D-04 ning jufti + `stalls.category_id` yo'qligi darvozasi (6 test)"
  - "`tests/integration/test_stall_assignments.py` — D-09/D-10/D-11/D-12 (11 test / 14 holat)"
  - "`tests/integration/test_market_calendar.py` — SC#4, uch qavat + ikki tarmoqli fail-closed (9 test)"
  - "`tests/integration/test_stall_code_reuse.py` — SC#2 ning DB tomoni (7 test)"
  - "`market_scope` fixture'i — sinxron `sbozor_app` tenant bloki (kontekst `finally` da bo'shatiladi)"
  - "`market_today` fixture'i — DB'ning Asia/Tashkent sanasi, trigger ishlatadigan AYNAN o'sha ifoda"
  - "`fixtures.MarketScope` protokoli — `TenantSessionFactory` ning sinxron jufti"
affects: [02-08, 02-09, 02-10, 02-11, 02-12, 02-15, 02-17, 06-hisob-kitob]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Kelajakdagi sanalar DB'ning `(now() AT TIME ZONE 'Asia/Tashkent')::date` idan HISOBLANADI — sobit sana D-07 nazorat holatlarini go-live'dan oldin jimgina o'ldirardi"
    - "Ikki xil rad etish bir xil `sqlstate` bergan joyda test ularni xato MATNI bo'yicha ajratadi (`stall code` vs `uq_stalls_market_id_code`)"
    - "Nazorat holati JUFTIDAN nom bilan havola qilinadi (`Usiz yuqoridagi test ...`) — qo'shni turish yolg'iz yetarli emas"
    - "Sabotaj o'lchovi «nechta test yiqildi» dan tashqari «QAYSILARI yashil qoldi» ni ham qayd etadi — nazoratning haqiqiyligi shu bilan isbotlanadi"

key-files:
  created:
    - tests/integration/test_tariff_history.py
    - tests/integration/test_category_history.py
    - tests/integration/test_stall_assignments.py
    - tests/integration/test_market_calendar.py
    - tests/integration/test_stall_code_reuse.py
  modified:
    - tests/integration/conftest.py
    - tests/fixtures/__init__.py
    - tests/fixtures/market_domain.py

key-decisions:
  - "Kelajak sanalari `market_today` fixture'idan hisoblanadi — rejadagi sobit `2026-09-01` bir oydan keyin O'TMISHGA aylanib nazorat holatlarini yiqitardi (go-live 2026-10-18)"
  - "Yangi tarif summasi `15 000` — rejadagi `12 000` seed'da allaqachon mavjud va `category_id` filtri yo'qolganda test YASHIL qolardi"
  - "`market_scope` fixture'i qo'shildi (4 faylda takrorlanadigan `set_config` try/finally o'rniga) va uning protokoli `fixtures/__init__.py` da — `TenantSessionFactory` ning aynan naqshi"
  - "`test_lower_bound_is_required` `PgRange(None, ...)` ni QO'LDA quradi, lekin chegara harfini `PERIOD_BOUNDS` dan oladi — `assignment_period()` bu holatni struktura bilan imkonsiz qiladi"
  - "`test_tariff_history_shows_computed_valid_to` avval `valid_to` USTUNI yo'qligini tekshiradi, keyin `LEAD()` ni — grep konvensiyasi o'rniga tirik darvoza"
  - "Nazorat holatlari rejadagi vazifa matnidagi TARTIBDA qoldirildi (Task 2 dagi majburiy juftlikdan tashqari); har biri juftiga nom bilan havola qiladi"

patterns-established:
  - "Pattern: sana-bog'liq testlarda «kelajak» DB'dan olinadi — kod tomonidagi `date.today()` UTC bo'lib mahalliy 00:00–04:59 oralig'ida bir kun farq qiladi"
  - "Pattern: fail-closed testi IKKI TARMOQLI bo'ladi (sozlama yo'q + cross-tenant) va cross-tenant tarmog'i O'Z-KONTEKSTI nazorati bilan keladi"
  - "Pattern: struktura darvozasi (`information_schema.columns`) xulq darvozasi bilan JUFTLIKDA — xulq testi ustun qo'shilganda ham yashil qolardi"

requirements-completed: []

# Metrics
duration: 42min
completed: 2026-07-31
---

# Phase 2 Plan 07: Tarif, biriktirish va kalendar shartnomasi Summary

**2-fazaning uchta muvaffaqiyat mezoni (SC#2 audit, SC#3 tarif tarixi, SC#4 ish kunlari) va MARKET-04 ning qarz-egaligi semantikasi jonli `postgres:18.4-trixie` da 45 ta integratsiya testi bilan qulflandi — API yozilishidan OLDIN, va uchta alohida sabotaj o'lchovi har bir darvozaning AYNAN bitta testni yiqitishini hamda nazorat holatlarining YASHIL qolishini ko'rsatdi.**

## Performance

- **Duration:** ~42 min
- **Tasks:** 3/3
- **Files:** 8 (5 yaratildi, 3 o'zgartirildi)
- **Testlar:** 472 → **517** (+45)

## Accomplishments

- **Uchta sabotaj o'lchovi darvozalarning KUCHINI aniq ko'rsatdi va uchalasida ham nazorat holatlari yashil qoldi:**

  | Sabotaj | Yiqilgan test | Nazorat holati |
  |---|---|---|
  | `trg_tariff_past_immutable` olib tashlandi | AYNAN 1: `test_past_tariff_is_immutable_even_via_raw_sql` (`DID NOT RAISE CheckViolation`) | `test_future_tariff_is_editable` ✅ yashil; **`test_past_category_period_is_immutable_even_via_raw_sql` ham ✅ yashil** — ikki qo'riqchi MUSTAQIL ekani isbotlandi |
  | `ex_stall_assignments_no_overlap` olib tashlandi | AYNAN 1: `test_overlapping_period_is_rejected` | `test_adjacent_periods_are_accepted` ✅ yashil; `test_handover_day_boundary` ning to'rttasi ham ✅ (ular `[)` semantikasiga tayanadi, konstraytga emas) |
  | `market_is_open()` → `SECURITY DEFINER` | AYNAN 1: `test_calendar_is_fail_closed`, cross-tenant tarmog'i (`assert True is False`) | `test_weekly_closed_day_is_closed` va `test_open_weekday_is_open` ✅ yashil — huquq rejimi FAQAT cross-tenant yo'lida ko'rinadi |
  | `trg_stall_code_claim` olib tashlandi | AYNAN 1: `test_retired_code_cannot_be_reused_by_a_new_stall` (`DID NOT RAISE UniqueViolation`) | `test_stall_can_reclaim_its_own_code`, `test_code_is_unique_within_market`, `test_same_code_in_another_market_is_accepted` ✅ uchalasi ham yashil |

  Har to'rttasidan keyin migratsiya `git checkout` bilan **bit-ba-bit** tiklandi (`git status` toza).

- **D-07 EGA roliga qarshi ikkala amalda ham o'lchandi.** `sbozor_owner` bilan o'tgan sanali tarif `UPDATE` **va** `DELETE` ikkalasi ham `23514`; qator keyin qayta o'qilib summasi o'zgarmagani tasdiqlandi (istisno chiqib, amal qisman o'tib ketgan holat yopildi). Toifa davri uchun ham aynan shu juftlik.

- **D-08 fail-closed'ning eng qimmat xatosi testda ATAYIN nomlangan:** `test_before_first_tariff_is_fail_closed` natijani `None` deb kutadi va docstringda `0` qaytarishning nima uchun eng xavfli javob ekani (tarifsiz kun "bepul kun" bo'lib ko'rinadi, anomaliya hech qachon chiqmaydi) yozilgan. Yordamchi funksiyaning o'zi ham `int | None` qaytaradi — tip darajasida `0` bilan aralashib ketmaydi.

- **D-10 chegarasi to'rtta sana bo'yicha parametrizatsiya qilindi va sanalar `HANDOVER_DAY` dan HISOBLANADI** (`-2, -1, 0, +1`), testda qayta yozilmaydi. Har bir sana uchun qator SONI ham tekshiriladi: `[]` konventsiyasida almashinuv kuni ikkala davrga tushib patta ikki marta yozilardi.

- **`market_is_open()` ning fail-closed'i IKKI TARMOQLI sinaldi va ikkinchi tarmoq NAZORAT bilan keladi:** profilsiz bozor → `false`; A konteksti ostida B → `false`; **B konteksti ostida AYNI so'rov → `true`**. Uchinchi assertion'siz test har doim `false` qaytaradigan buzuq funksiyadan ham o'tib ketardi.

- **Ikki xil rad etish xato MATNI bo'yicha AJRATILDI.** `23505` ni ham `uq_stalls_market_id_code` (kod hozir band, D-01), ham `trg_stall_code_claim` (kod chetlangan, D-02) beradi. Testlar `"stall code" in str(exc)` va `"uq_stalls_market_id_code" in str(exc)` bilan qaysi qatlam ishlaganini talab qiladi — aks holda D-02 mexanizmi umuman yo'q bo'lganda ham reyestr testi yashil qolardi (sabotajda aynan shu farq ko'rindi).

- **Audit qamrovi uch xil yo'lda tasdiqlandi:** ORM'siz app-rol yo'li (`stall_assignments.period`, `market_profile.open_weekdays`, `stalls.code`), `sbozor_owner` xom SQL yo'li (`stalls.status`) va `DELETE` yo'li (`market_calendar_exceptions`). Har birida `old`/`new` farqi va `changed_keys` tekshiriladi.

## Task Commits

1. **Task 1: Tarif va toifa tarixi — SC#3 ning to'liq isboti** — `9c41863` (test)
2. **Task 2: Sotuvchi biriktirish — D-09/D-10/D-11/D-12 isboti** — `303649b` (test)
3. **Task 3: Ish kunlari kalendari (SC#4) va rasta raqami/holati (SC#2)** — `49c48c3` (test)

## Files Created/Modified

**Yaratildi**

- `tests/integration/test_tariff_history.py` (9 test) — modul docstringi «nega bu testlar API'dan OLDIN va nega ular API'ni sinamaydi» savoliga javob beradi va 02-09 uchun xato xaritasini (`23514 → 403`, `23505 → 409`, 0 qator → anomaliya) oldindan yozadi.
- `tests/integration/test_category_history.py` (6 test) — D-04 ning tarif bilan AYNAN bir xil mexanizmi + `stalls.category_id` yo'qligining strukturaviy darvozasi + 6-fazaning `LEFT JOIN LATERAL` so'rovi (tarifli va tarifsiz rasta bir testda).
- `tests/integration/test_stall_assignments.py` (11 test, 14 holat) — `tests/tenancy/test_market_domain_meta.py` bilan munosabati docstringda ochiq yozilgan (u yerda konstraytning MAVJUDLIGI, bu yerda XULQI va ilovaga beriladigan shartnoma).
- `tests/integration/test_market_calendar.py` (9 test) — uch qavat, ikki yo'nalishli istisno, ikki tarmoqli fail-closed va D-18 ning strukturaviy darvozasi.
- `tests/integration/test_stall_code_reuse.py` (7 test) — SC#2 ning ikkala yarmi (kod qayta ishlatilmaydi + holat o'zgarishlari auditda, xom SQL yo'lida ham).

**O'zgartirildi**

- `tests/integration/conftest.py` — `market_scope` va `market_today` fixture'lari + `SET_MARKET_GUC`/`MARKET_TODAY_SQL` konstantalari. Har ikkalasining docstringi «nega bu shaklda» ni yozadi (kontekst sizishi va sobit sana rot'i).
- `tests/fixtures/__init__.py` — `MarketScope` protokoli, `TenantSessionFactory` yonida va aynan uning naqshida.
- `tests/fixtures/market_domain.py` — `A_TARIFF_AMOUNTS` va `B_TARIFF_AMOUNT` `__all__` ga qo'shildi (testlar kutilmani seed'dan oladi, o'z nusxasini yozmaydi).

## Decisions Made

- **Kelajakdagi sanalar `market_today` fixture'idan HISOBLANADI.** Deviatsiya #1 — batafsil pastda. Qisqasi: reja `valid_from = 2026-09-01` ni «kelajak» deb belgilaydi, bugun 2026-07-31, faza go-live sanasi esa **2026-10-18**. Ya'ni `test_future_tariff_is_editable` va `test_future_category_period_is_editable` nazorat holatlari loyihaning O'Z muddati ichida `23514` bilan yiqilardi.
- **Yangi tarif summasi `15 000`, rejadagi `12 000` emas.** Deviatsiya #2. `12 000` seed'da A bozorining IKKINCHI toifasiga allaqachon berilgan, ya'ni so'rov `category_id` filtrini yo'qotganda ham «to'g'ri» javob qaytarardi.
- **`market_scope` fixture'i qo'shildi.** Mavjud naqsh (`test_market_domain_meta.py`) har testda `set_config` + `try/finally` ni takrorlaydi; to'rtta yangi faylda bu ~40 satr shovqin bo'lardi va bitta unutilgan `finally` keyingi testga kontekst sizdirardi. Protokol `fixtures/__init__.py` da — o'sha fayl allaqachon `TenantSessionFactory` va `TokenFactory` protokollarining uyi.
- **`test_lower_bound_is_required` `PgRange` ni QO'LDA quradi.** `assignment_period()` `start: date` talab qiladi, ya'ni quyi chegarasiz davrni STRUKTURA bilan imkonsiz qiladi — bu uning maqsadi. Test DB darajasidagi qo'riqchini sinashi kerak, shuning uchun yordamchini chetlab o'tadi, LEKIN chegara harfini baribir `PERIOD_BOUNDS` dan oladi: faylda `'[)'` literali ham, xom `daterange(` matni ham yo'q (`grep` bilan tasdiqlandi — yagona uchrash modul docstringidagi «bu yerda YO'Q» izohi).
- **`valid_to` darvozasi grep konvensiyasidan TIRIK testga ko'chirildi.** Reja «testlarda `valid_to` ustuniga murojaat bo'lmasin» deydi — bu code-review bandi va u faqat ko'z bilan tekshiriladi. `test_tariff_history_shows_computed_valid_to` avval `information_schema.columns` dan ustunning YO'QLIGINI talab qiladi, keyin `LEAD()` bilan hisoblaydi. Ustun qo'shilsa test darhol qizaradi, hech kimning grep qilishini kutmasdan.
- **Nazorat holatlari rejadagi vazifa matnidagi tartibda qoldirildi.** Rejaning `<verification>` bandi #5 «nazorat juftidan OLDIN» deydi, vazifa matnlari esa aksincha tartibda sanaydi va nazorat testlarini «Usiz OLDINGI test...» deb ta'riflaydi (ya'ni juft o'zi keyin turishini nazarda tutadi). Aniq talab qilingan yagona joy — Task 2 ning qabul mezoni (`test_adjacent_periods_are_accepted` `test_overlapping_period_is_rejected` dan oldin) — bajarildi. Qolganlarida nazorat juftidan KEYIN turadi, lekin **har biri juftiga nom bilan havola qiladi** (`«Usiz yuqoridagi test ... bemalol o'tardi»`), ya'ni o'quvchi uchun bog'liqlik ko'rinadi.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Rejadagi sobit «kelajak» sanasi go-live'dan OLDIN o'tmishga aylanardi**

- **Found during:** Task 1
- **Issue:** Reja `test_effective_day_uses_new_price` uchun `valid_from = 2026-09-01` ni, `test_past_date_keeps_old_price` uchun esa `2026-08-31` ni LITERAL belgilaydi. Bugun — 2026-07-31, ya'ni bugun bu sanalar kelajak. Lekin `test_future_tariff_is_editable` va `test_future_category_period_is_editable` **nazorat holatlari** aynan shu sana KELAJAK bo'lishiga tayanadi: `tariff_past_immutable()` sharti `OLD.valid_from <= (now() AT TIME ZONE 'Asia/Tashkent')::date`. 2026-09-01 kelganda o'sha qator o'tmishga aylanadi va nazorat testlari `23514` bilan yiqiladi. Bu «bir kun kelib» emas — **32 kundan keyin**, va fazaning go-live sanasi (2026-10-18) undan ham kech. Ya'ni reja o'zi qurayotgan darvozani o'z muddati ichida o'ldiradigan testlar yozishni buyuradi.
- **Fix:** `tests/integration/conftest.py` ga `market_today` fixture'i qo'shildi — u `SELECT (now() AT TIME ZONE 'Asia/Tashkent')::date` ni bajaradi, ya'ni triggerning O'ZI ishlatadigan AYNAN o'sha ifodani. Kelajakdagi sanalar `market_today + timedelta(days=DAYS_AHEAD)` shaklida. `date.today()` ATAYIN ishlatilmadi: konteyner UTC'da ishlaydi va mahalliy 00:00–04:59 oralig'ida bir kun farq qilardi — ya'ni test «kelajak» deb yozgan sana trigger uchun o'tmish bo'lib chiqishi mumkin edi.
- **Nima o'zgarmadi:** o'tmish sanalari SOBIT qoldi — seed'ning `operating_since` i (2026-01-15) hech qachon kelajakka aylanmaydi, `HANDOVER_DAY`/`GAP_DAY` esa triggerga umuman bog'liq emas (biriktirishlarda o'zgarmaslik qo'riqchisi yo'q).
- **Files modified:** `tests/integration/conftest.py`, `tests/integration/test_tariff_history.py`, `tests/integration/test_category_history.py`
- **Verification:** `test_future_tariff_is_editable` va `test_future_category_period_is_editable` ikkalasi ham yashil; sabotaj o'lchovida ikkalasi ham nazorat sifatida yashil QOLDI
- **Committed in:** `9c41863`

**2. [Rule 1 - Bug] Rejadagi `12 000` yangi narxi testni YOLG'ON-YASHIL qilardi**

- **Found during:** Task 1
- **Issue:** Reja «`valid_from = operating_since` bilan 8 000 so'm tarif bor; `valid_from = 2026-09-01` bilan **12 000** qo'shiladi» deydi. Lekin `12 000` — seed'ning `A_TARIFF_AMOUNTS = (5_000, 12_000, 8_000)` dagi IKKINCHI toifasining narxi. Seed moduli o'z docstringida narxlar har xil ekanini ATAYIN ta'kidlaydi («"D sanadagi tarif" qidiruvi qaysi qatorni topganini ajrata olishi uchun»). Rejaning tanlovi bu himoyani buzardi: agar so'rov `category_id` filtrini yo'qotib qo'ysa va boshqa toifaning tarifini topsa, `test_effective_day_uses_new_price` baribir `12 000` ko'rib YASHIL qolardi.
- **Fix:** `NEW_AMOUNT = 15_000` — seed'ning uchala summasidan ham farqli qiymat; sabab konstanta docstringida yozilgan. `SEEDED_AMOUNT` esa literal emas, `A_TARIFF_AMOUNTS[SEEDED_CATEGORY_INDEX]` dan olinadi (seed narxni o'zgartirsa test ergashadi, 02-06 naqshi).
- **Files modified:** `tests/integration/test_tariff_history.py`
- **Verification:** `test_effective_day_uses_new_price` yashil; kutilma seed'da UMUMAN uchramaydigan qiymat
- **Committed in:** `9c41863`

**3. [Rule 2 - Missing Critical] `valid_to` bandi code-review qoidasi edi, tirik darvoza emas**

- **Found during:** Task 1
- **Issue:** Reja qabul mezoni sifatida «Testlarning birortasida `valid_to` ustuniga murojaat YO'Q» ni beradi. Bu — inson bajaradigan tekshiruv va u faqat kimdir grep qilganda ishlaydi. Ayni paytda Pitfall 9 ning haqiqiy xavfi testlarda emas, SXEMADA: kimdir «UI uchun qulay bo'lsin» deb `tariffs` ga `valid_to` ustuni qo'shsa, mavjud testlarning HAMMASI yashil qolardi (ular `valid_from` bilan ishlaydi) va ikkinchi haqiqat manbai jimgina paydo bo'lardi.
- **Fix:** `test_tariff_history_shows_computed_valid_to` ikki qismli qilindi: avval `information_schema.columns` dan `valid_to` ning YO'QLIGI talab qilinadi, keyin `LEAD(valid_from) OVER (...)` bilan hisoblanadi va oxirgi qator uchun `NULL` berishi tekshiriladi. Endi ustun qo'shilishi darhol qizaradi.
- **Files modified:** `tests/integration/test_tariff_history.py`
- **Verification:** Test ikkala assertion bilan ham yashil
- **Committed in:** `9c41863`

**4. [Rule 3 - Blocking] Rejaning ikki bandi nazorat tartibida bir-biriga zid**

- **Found during:** Task 1
- **Issue:** `<verification>` bandi #5 «har bir nazorat holati juftidan OLDIN e'lon qilingan» deydi. Vazifa matnlari esa nazorat testlarini juftidan KEYIN sanaydi va ularni «Usiz **oldingi** test ... yashil bo'lardi» deb ta'riflaydi — ya'ni ular juftning keyin turishini nazarda tutadi. Ikkala talabni bir vaqtda bajarib bo'lmaydi.
- **Fix:** Aniq talab qilingan yagona joy — Task 2 ning qabul mezoni — bajarildi (`test_adjacent_periods_are_accepted` `test_overlapping_period_is_rejected` dan OLDIN). Qolgan beshta juftlikda vazifa matnining tartibi saqlandi, LEKIN har bir nazorat testi juftiga NOM yoki «yuqoridagi test» iborasi bilan havola qiladi va nima uchun kerakligini o'z docstringida yozadi. Bog'liqlik o'quvchiga tartibdan emas, matndan ko'rinadi.
- **Files modified:** beshta test faylining hammasi (docstringlar)
- **Verification:** Sabotaj o'lchovlarida nazoratlarning HAMMASI yashil qoldi — ya'ni ular haqiqiy nazorat, rad etish testining nusxasi emas
- **Committed in:** `9c41863`, `303649b`, `49c48c3`

**5. [Rule 2 - Missing Critical] `market_scope`/`MarketScope` reja fayl ro'yxatidan tashqarida**

- **Found during:** Task 1
- **Issue:** Reja `files_modified` da faqat `tests/integration/conftest.py` ni sanaydi va u ham «kerak bo'lsa» shartli. Lekin to'rtta test fayli ham tenant kontekstini o'rnatishi kerak va mavjud naqsh (`test_market_domain_meta.py`) har testda `set_config` + `try/finally` ni QO'LDA takrorlaydi. To'rtta faylda bu ~40 satr takror bo'lardi va bitta unutilgan `finally` kontekstni keyingi testga sizdirardi — o'sha test esa jimgina noto'g'ri bozorni o'qib YASHIL qolardi (`fixtures/two_markets.py::_first_audit_row_id` da aynan shu xato sinfi hujjatlashtirilgan).
- **Fix:** `market_scope` fixture'i `tests/integration/conftest.py` ga, uning protokoli (`MarketScope`) esa `tests/fixtures/__init__.py` ga qo'shildi — `TenantSessionFactory` va `TokenFactory` yashaydigan AYNAN o'sha fayl va aynan o'sha naqsh (`Protocol` + `__call__`). Cross-modul import muammosi ham shu bilan yopiladi: test modullari conftest'dan import qilmaydi (02-06 SUMMARY o'sha yo'lni ATAYIN rad etgan).
- **Files modified:** `tests/integration/conftest.py`, `tests/fixtures/__init__.py`
- **Verification:** `mypy --strict` 102 faylda toza; barcha 45 test yashil
- **Committed in:** `9c41863`

---

**Total deviations:** 5 auto-fixed (2 bug, 1 blocking, 2 missing-critical). Rule 4 (arxitektura) holati bo'lmadi.
**Impact on plan:** Qamrov kengaytmasi yo'q — birorta yangi jadval, migratsiya, funksiya yoki paket qo'shilmadi va MAHSULOT kodiga umuman tegilmadi. #1 va #2 rejaning O'Z konstantalaridagi haqiqiy xatolar (biri vaqt bo'yicha rot, ikkinchisi yolg'on-yashil); #3 va #4 rejaning bandlarini passiv qoidadan tirik darvozaga ko'chiradi; #5 fixture takrorini yopadi.

## Empirik o'lchovlar

Barcha o'lchovlar haqiqiy `postgres:18.4-trixie` konteynerida, `sbozor_app` (isbotlar) va `sbozor_owner` (hujumlar) rollari bilan.

| O'lchov | Natija |
|---|---|
| O'tgan sanadagi narx yangi tarif qo'shilgandan KEYIN | ✅ o'zgarmadi (8 000) |
| Kuchga kirish KUNINING O'ZI | ✅ 15 000 (chegara inklyuziv) |
| `operating_since - 1` kun uchun so'rov | ✅ **0 qator** (`None`, `0` emas) |
| O'tgan tarif `UPDATE` — `sbozor_owner` | ✅ `23514`, summa o'zgarmadi |
| O'tgan tarif `DELETE` — `sbozor_owner` | ✅ `23514`, qator qoldi |
| Kelajakdagi tarif `UPDATE` + `DELETE` | ✅ ikkalasi ham o'tdi (nazorat) |
| Mavjud tarif qatori `(amount, valid_from, created_at)` | ✅ bayt-baytga teng |
| Bir kunda ikkita kelajak tarifi | ✅ `(1 biznes-kun, 2 qator)` |
| Takroriy `(category_id, valid_from)` | ✅ `23505` |
| `tariffs` da `valid_to` ustuni | ✅ YO'Q; `LEAD()` oxirgi qatorga `NULL` |
| O'tgan toifa davri `UPDATE`/`DELETE` — ega | ✅ `23514` (ikkalasi) |
| `stalls` da `category_id` ustuni | ✅ YO'Q |
| `LEFT JOIN LATERAL` (B bozori) | ✅ 2 rasta; tarifli → 7 000, TARIFSIZ → `NULL` |
| Qo'shni davrlar | ✅ ikkalasi qabul (2 qator) |
| Qoplanuvchi davr | ✅ `23P01` |
| Almashinuv chegarasi (`-2/-1/0/+1`) | ✅ `eski/eski/YANGI/yangi`, har birida AYNAN 1 qator |
| Bo'shliq kuni / biriktirilmagan rasta | ✅ 0 qator (ikkalasi) |
| Ochiq oxirli davr round-trip | ✅ `lower` saqlandi, `upper is None`, `bounds == '[)'` |
| Quyi chegarasiz davr | ✅ `CheckViolation` (`lower_bound_required`) |
| Cross-tenant biriktirish | ✅ `ForeignKeyViolation` (`fk_stall_assignments_market_id_vendor_id_vendors`) |
| Davr o'zgarishi auditi | ✅ 1 `update` qatori, `changed_keys` da `period`, `old != new` |
| A da takroriy telefon / B da AYNI telefon | ✅ `23505` / qabul qilindi |
| Dushanba (jadvalda yo'q) / seshanba | ✅ `false` / `true` |
| `is_open=true` dushanbaga / `is_open=false` seshanbaga | ✅ `true` / `false` |
| Profilsiz bozor (fail-closed) | ✅ `false` |
| A konteksti ostida B → **nazorat:** B konteksti ostida B | ✅ `false` → **`true`** |
| Takroriy istisno sanasi | ✅ `23505` |
| Istisno `insert` + `delete` auditi | ✅ `['insert', 'delete']`, `note` va eski `is_open` saqlangan |
| `open_weekdays` o'zgarishi auditi | ✅ `changed_keys` da `open_weekdays`, `old` = `[2..7]`, `new` = `[1..7]` |
| `market_calendar_exceptions` da `zone_id`/`stall_id` | ✅ YO'Q |
| Kod tahriri + auditi | ✅ `12 → 99`, `changed_keys` da `code` |
| Chetlangan kodni yangi rastaga berish | ✅ `23505` + xabarda `stall code` (REYESTR triggeri) |
| O'z kodini qaytarib olish | ✅ ruxsat (nazorat) |
| Band kod (bir vaqtda) | ✅ `23505` + xabarda `uq_stalls_market_id_code` (BOSHQA qatlam) |
| B bozorida AYNI kod | ✅ qabul qilindi (nazorat) |
| `sbozor_owner` xom `UPDATE stalls SET status` | ✅ audit qatori, `changed_keys == ['status']` |
| `active → maintenance → closed` | ✅ `['insert', 'update', 'update']`, har o'tishda `status` farqi |

## Issues Encountered

- **`.env` worktree'da yo'q** (gitignore), ya'ni `npm run migrate` ishlamaydi. Ekvivalent qamrov o'zgarmadi: `migrated` fixture'i AYNAN `alembic upgrade head` ni `alembic.command` API'si bilan, `sbozor_owner` roli bilan va haqiqiy konteynerda bajaradi — 517 testning har birida. Sabotaj o'lchovlari ham shu yo'l bilan (migratsiya o'zgartirilib, sxema noldan qayta qurilib) bajarildi.
- **`ruff format` uch marta uzun konstruksiyani qayta formatladi** (bitta `execute` chaqiruvi, bitta fixture imzosi, bitta test imzosi) va `ruff check` ikkita `SIM117` (ichma-ich `with`) berdi — ikkalasi ham `with (A as x, pytest.raises(...) as y):` shakliga o'tkazildi. Hammasi qator uzunligi/stil darajasida.
- **`test_period_change_is_audited` seed davrini DB'dan o'qib suradi**, konstantadan emas: `GAP_REOPENED_AT` seed modulining `__all__` ida yo'q va uni eksport qilish o'rniga mavjud qatorning `period.lower` i olinadi. Yon foyda — test seed sanasi o'zgarganda ham to'g'ri qoladi.
- **`_free_stall()` har uchala faylda BIR XIL rastani (`unassigned_stall_id`) tanlaydi**, chunki `handover_stall`/`gap_stall` ustida yangi davr yozish D-10/D-11 testlarining boshlang'ich holatini buzardi. Har testda seed yangi bo'lgani uchun fayllararo ta'sir yo'q.

## Known Stubs

Yo'q. Birorta test `skip`/`xfail` bilan yozilmagan, birorta assertion izohga o'ralmagan va rejadagi barcha test nomlari (VALIDATION.md dagi nomlar bilan) yozildi. Bu reja mahsulot kodiga umuman tegmaydi — u mavjud sxema ustidagi shartnomani qulflaydi.

**Ataylab ochiq qoldirilgan, ko'rinadigan qarz (stub emas):**

| Qarz | Kim yopadi | Bugungi holati |
|---|---|---|
| `23514`/`23505`/`23P01` → HTTP kod xaritasi ilova qatlamida yo'q | 02-09 (tarif), 02-10 (biriktirish) | Kutilgan `sqlstate` lar shu testlarda qulflandi — endpoint ularga qarshi quriladi |
| Sotuvchi ma'lumotini O'QISH auditi (D-09, Pattern 10) | 02-10 | Bu reja YOZISH auditini qamraydi; o'qish auditi endpoint dekoratori bilan keladi |
| `market_is_open()` ni kunlik job'da ishlatish | 6-faza | Kontrakt («bitta shart») shu testlarda tasdiqlandi |

## Threat Flags

Yangi xavfsizlik yuzasi yo'q — yangi endpoint, fayl kirishi, tashqi bog'liqlik yoki sxema o'zgarishi qo'shilmadi. Bu reja FAQAT test yozadi. Rejaning `<threat_model>` idagi dispozitsiyalar:

| Threat ID | Holat |
|-----------|-------|
| T-02-46 | mitigate — `test_past_tariff_is_immutable_even_via_raw_sql` `sbozor_owner` bilan hujum qiladi, `UPDATE` va `DELETE` ikkalasida ham `23514`; **sabotaj bilan tasdiqlandi**, nazorat holati yashil qoldi |
| T-02-47 | mitigate — `test_past_category_period_is_immutable_even_via_raw_sql`; tarif sabotajida u YASHIL qoldi, ya'ni ikki qo'riqchi mustaqil |
| T-02-48 | mitigate — `test_raw_sql_update_is_audited` (`sbozor_owner`, ORM'siz) + `test_status_transition_is_audited` (uch bosqichli zanjir) |
| T-02-49 | mitigate — `test_retired_code_cannot_be_reused_by_a_new_stall` (xato MATNI reyestr triggeridan ekanini talab qiladi) + uchta nazorat holati; **sabotaj bilan tasdiqlandi** |
| T-02-50 | mitigate — `test_exception_change_is_audited` (`insert` + `delete`) va `test_weekday_change_is_audited` (`old → new`) |
| T-02-51 | mitigate — `test_calendar_is_fail_closed` cross-tenant tarmog'i O'Z-KONTEKSTI nazorati bilan; **sabotaj bilan tasdiqlandi** (`SECURITY DEFINER` da AYNAN shu test yiqildi) |
| T-02-52 | mitigate — `test_cross_tenant_vendor_assignment_is_rejected`, konstrayt NOMI bilan (rasta FK'sidan ajratiladi) |
| T-02-53 | mitigate — `test_period_change_is_audited`, `changed_keys` da `period` va `old != new` |

## Verification Results

| # | Buyruq | Natija |
|---|--------|--------|
| 1 | `pytest tests/integration -q` | ✅ (to'liq to'plam ichida) |
| 2 | `npm run test` (`pytest -q`) | ✅ **517 passed** (02-06 dagi 472 + 45) |
| 3 | `npm run test:tenancy` | ✅ **123 passed** |
| 4 | `npm run lint` (ruff + format + mypy strict) | ✅ exit 0 (103 fayl, 102 manba) |
| 5 | Nazorat holatlari — kod ko'rigi | ✅ har biri juftiga havola qiladi (deviatsiya #4) |

**Task 1 qabul mezonlari (o'lchangan):**

| Mezon | Natija |
|-------|--------|
| `test_tariff_history.py` ≥8 test | ✅ **9** |
| `test_category_history.py` ≥6 test | ✅ **6** |
| `test_before_first_tariff_is_fail_closed` `None` kutadi | ✅ (yordamchi ham `int \| None` qaytaradi) |
| `test_past_tariff_is_immutable_even_via_raw_sql` `sync_owner_conn` + `23514` | ✅ `UPDATE` va `DELETE` |
| `test_future_tariff_is_editable` mavjud va yashil | ✅ |
| `test_stall_has_no_category_column` yashil | ✅ |
| Triggerni o'chirib test yiqiladimi | ✅ AYNAN 1 test yiqildi, migratsiya tiklandi |
| `valid_to` ustuniga murojaat | ✅ YO'Q — va ustunning YO'QLIGI endi test bilan talab qilinadi |

**Task 2 qabul mezonlari (o'lchangan):**

| Mezon | Natija |
|-------|--------|
| `test_stall_assignments.py` ≥11 test | ✅ 11 funksiya / **14 holat** |
| Nazorat rad etishdan OLDIN e'lon qilingan | ✅ |
| `sqlstate == "23P01"` (konstrayt nomiga tayanmaydi) | ✅ |
| `test_handover_day_boundary` 4 sana, `2026-08-10` → yangi | ✅ (sanalar `HANDOVER_DAY` dan hisoblanadi) |
| `test_vacancy_gap_returns_no_vendor` 0 qator, istisnosiz | ✅ |
| `test_same_phone_in_another_market_is_accepted` yashil | ✅ |
| Xom `daterange(` / `"[)"` literali | ✅ YO'Q (`grep`; yagona uchrash — docstringdagi «bu yerda YO'Q» izohi) |
| EXCLUDE konstraytini o'chirib test yiqiladimi | ✅ AYNAN 1 test yiqildi, nazorat yashil qoldi |

**Task 3 qabul mezonlari (o'lchangan):**

| Mezon | Natija |
|-------|--------|
| `test_market_calendar.py` ≥9 test | ✅ **9** |
| `test_stall_code_reuse.py` ≥7 test | ✅ **7** |
| `test_calendar_is_fail_closed` ikkala tarmoq | ✅ + uchinchi assertion (o'z-konteksti nazorati) |
| `test_open_weekday_is_open` va `test_stall_can_reclaim_its_own_code` yashil | ✅ |
| `test_raw_sql_update_is_audited` `sync_owner_conn` bilan (ORM emas) | ✅ |
| `test_calendar_is_market_level_only` yashil | ✅ |
| `market_is_open` → `SECURITY DEFINER` da cross-tenant tarmog'i yiqiladimi | ✅ AYNAN shu test va AYNAN shu assertion yiqildi |
| `npm run test` exit 0 | ✅ 517 passed |

## User Setup Required

Yo'q — tashqi servis sozlamasi ham, deploy qadami ham kerak emas. Bu reja migratsiya yozmaydi va sxemaga tegmaydi.

## REQUIREMENTS.md holati — ATAYIN belgilanmadi

Reja frontmatteri `requirements: [MARKET-02, MARKET-03, MARKET-04, MARKET-05]` deb yozgan, lekin bu reja **shartnomani qulflaydi**, foydalanuvchi ko'radigan qobiliyatni bermaydi: rasta reestri (MARKET-02), tarif boshqaruvi (MARKET-03), sotuvchi/biriktirish UI'si (MARKET-04) va kalendar boshqaruvi (MARKET-05) 02-08…02-17 rejalarida quriladi. Ularni bu yerda «bajarildi» deb belgilash traceability jadvalini yolg'on qilardi (02-04/02-05/02-06 SUMMARY'laridagi bilan bir xil sabab).

Qo'shimcha texnik sabab: bu agent **worktree'da** ishlaydi va `REQUIREMENTS.md` — orkestrator egalik qiladigan umumiy artefakt.

## Next Phase Readiness

**02-08…02-11 (API rejalari) uchun endi QULFLANGAN shartnoma:**

- **Xato xaritasi** (testlar bilan tasdiqlangan, faqat `sqlstate` bo'yicha ajratiladi):
  `23514` → `403` (o'tgan tarif/toifa davrini tahrirlash) · `23P01` → `409 assignment_period_overlaps` · `23505` → `409` (telefon band / rasta kodi band / chetlangan kod / takroriy istisno sanasi / takroriy `valid_from`).
- **«Tarif topilmadi» — 0 QATOR**, `0` so'm emas. Endpoint uni `null` yoki alohida holat sifatida qaytarishi shart; `0` yozish D-08 ni buzadi.
- **Almashinuv kuni YANGI sotuvchiniki** — `period @> :d` bitta qator beradi. Ilova bu so'rovni AYNAN shu shaklda yozadi (GiST indeksi).
- **`market_is_open()` tenant konteksti O'RNATILGAN bo'lishini talab qiladi** — u INVOKER, kontekstsiz `false` qaytaradi (fail-closed) va bu sabotaj bilan tasdiqlangan xulq.
- **Ikki xil `23505` bir xil yo'lda `409` ga aylanadi** (kod band / kod chetlangan) — ikkita alohida tarmoq yozish shart emas, lekin foydalanuvchi xabari farq qilishi kerak bo'lsa ilova xato MATNIDAN ajratishi mumkin (`stall code` vs `uq_stalls_...`).
- **RLS `DETAIL` ni o'chiradi** — foydalanuvchi xabari DB xatosidan OLINMAYDI (02-12 import validatsiyasi uchun kritik).

**Yangi test infratuzilmasi (02-08+ uchun tayyor):**

- `market_scope(market_id)` — sinxron `sbozor_app` bloki, kontekst avtomatik bo'shatiladi.
- `market_today` — DB'ning Asia/Tashkent sanasi; **kelajak/o'tmish sanalarni SHU qiymatdan hisoblang**, `date.today()` dan emas va literal yozmang.
- `fixtures.MarketScope` — protokol, `TenantSessionFactory` yonida.

**6-faza uchun:** bu fayllar hisob-kitobning butun kirish shartnomasini o'z ichiga oladi — tarif qidiruvi, toifa qidiruvi, `LEFT JOIN LATERAL` birikmasi, biriktirish egaligi va `market_is_open()`. Kunlik job yozilganda ularning HAMMASI allaqachon o'lchangan holatda turadi.

## Self-Check: PASSED

- Da'vo qilingan 5 yangi fayl diskda mavjud: `tests/integration/test_tariff_history.py`, `test_category_history.py`, `test_stall_assignments.py`, `test_market_calendar.py`, `test_stall_code_reuse.py`
- Da'vo qilingan 3 o'zgartirilgan fayl `git diff --stat dfcb4b0..HEAD` da ko'rinadi: `tests/integration/conftest.py`, `tests/fixtures/__init__.py`, `tests/fixtures/market_domain.py`
- Uchala vazifa commit'i git tarixida mavjud: `9c41863`, `303649b`, `49c48c3`
- Birorta commit'da fayl o'chirilishi yo'q (`git diff --diff-filter=D dfcb4b0..HEAD` bo'sh)
- To'rtta sabotajdan keyin uchala migratsiya ham `git checkout` bilan bit-ba-bit tiklandi; ishchi daraxtda kuzatilmagan fayl qolmadi
- `STATE.md`, `ROADMAP.md` va `REQUIREMENTS.md` TEGILMADI (worktree rejimi — orkestrator egalik qiladi)

---
*Phase: 02-bozor-domeni-va-yangi-bozor-ustasi*
*Completed: 2026-07-31*
