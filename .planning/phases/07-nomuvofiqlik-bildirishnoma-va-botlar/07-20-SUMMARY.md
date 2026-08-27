---
phase: 07-nomuvofiqlik-bildirishnoma-va-botlar
plan: 20
subsystem: api
tags: [multi-tenancy, rls, postgres, sqlalchemy, fastapi, pydantic, keyset, cte]

# Dependency graph
requires:
  - phase: 07-nomuvofiqlik-bildirishnoma-va-botlar
    provides: "07-07 case domeni va `transition()`, 07-10 case HTTP yuzasi va DB-trigger auditi, 07-16 yetkazilganlik yuzasi va kursor shakli, 07-18 direktor yozuv yo'li"
  - phase: 01-poydevor
    provides: "`UserRepository.member_roles()` — cross-tenant darvozasi (T-01-51)"
provides:
  - "`PATCH /reconciliation/cases/{id}` `assignee_user_id` ni BAZAGA yetkazadi"
  - "`422 assignee_not_in_market` — begona bozor xodimini biriktirishga qarshi YAGONA to'siq"
  - "`transition(assignee_user_id=..., assignee_explicit=...)` — «mijoz jim» va «mijoz `null` dedi» ajratildi"
  - "«Biriktirilmagan» tanlovi HAQIQIY amal: biriktirish bekor qilinadi"
  - "Holat o'zgarishi mavjud biriktirishni O'G'IRLAMAYDI (COALESCE argumentlari almashdi)"
  - "`open_cases()` ning `born` CTE si — har case tug'ilishida `from_status IS NULL` qatori"
  - "Ikkala kursor dekoderi ham tz-siz qiymatni `422 cursor_invalid` ga aylantiradi"
affects: [07-23, 07-verification, 08-*, reconciliation-ui]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "«Mijoz maydonni yubordimi?» — `payload.model_fields_set` (Pydantic v2); `None` ning ikki ma'nosi ALOHIDA bayroq bilan ajratiladi"
    - "Cross-tenant tekshiruvi yozuvdan OLDIN — rad etish `rollback` ga tayanmaydi"
    - "Tug'ilish hodisasi case bilan AYNI BAYONOTDA (`born` CTE si `inserted` ustida)"
    - "Kursor validatsiyasi ikki bosqichli: shakl (`ValueError`) VA tz-aware ekanligi"

key-files:
  created: []
  modified:
    - services/core-api/app/api/v1/reconciliation.py
    - services/core-api/app/repositories/reconciliation_repo.py
    - tests/integration/test_reconciliation_api.py
    - tests/integration/test_phase7_criteria.py

key-decisions:
  - "`assignee_explicit` ALOHIDA bayroq: `None` ning o'zi «tegmang» va «bekor qiling» degan ikki ma'no tashiydi va ularni bitta qiymat bilan ifodalab bo'lmaydi"
  - "`ELSE COALESCE(assignee_user_id, :actor_user_id)` — argumentlar TARTIBI almashdi: egasi bor case o'z egasida qoladi, egasiz case uni qo'lga olgan odamga tushadi"
  - "Begona/mavjud bo'lmagan mas'ul uchun `422`, `403` EMAS va `404` ham EMAS — javob farqi enumeration signali bo'lardi (T-07-110)"
  - "A'zolik tekshiruvi `transition()` dan OLDIN — keyin qilinsa «case umuman o'zgarmadi» kafolati tranzaksiya xulqiga bog'liq bo'lib qolardi"
  - "AKTIVLIK (`is_active`) TEKSHIRILMAYDI: nofaol xodimni bloklash mavjud biriktirishni qayta yozib bo'lmaydigan qilardi; UI variantlarni allaqachon cheklaydi (07-16)"
  - "`born` CTE si natijasi tashqi `SELECT` da sanaladi — PG ma'lumot o'zgartiruvchi CTE ni baribir bajaradi, sanoq esa INVARIANTNI (`born` == `inserted`) o'qiladigan qiladi"
  - "Naive kursor 422: kursorni SERVER quradi va u HAR DOIM tz-aware, ya'ni naive qiymat qo'lda yasalgan KIRISH xatosi"

patterns-established:
  - "Tenancy da'vosi BEGONA BOZORDA HAQIQATAN MAVJUD odam bilan o'lchanadi — tasodifiy UUID «yo'q foydalanuvchi» ni o'lchardi va darvoza olib tashlanganda ham yashil qolardi"
  - "«Mas'ul yozildi» da'vosi IKKI QISMLI: tanlangan odamga TENG va aktorga TENG EMAS"
  - "Hodisalar sonini oshirishning O'ZI yetmaydi — birinchi qatorning TIZIM ekani alohida o'lchanadi"

requirements-completed: [RECON-02]

# Metrics
duration: 70min
completed: 2026-08-13
---

# Phase 07 Plan 20: Mas'ul, tenancy darvozasi, tug'ilish hodisasi va kursor Summary

**Direktor tanlagan mas'ul endi bazaga yetadi va aktordan ajratiladi; begona bozor xodimini biriktirish `422 assignee_not_in_market` bilan rad etiladi (`user_market_roles` ustidagi ilova qatlami — sxemada FK YO'Q); har case tug'ilganda tarixga `from_status IS NULL` qatori tushadi; tz-siz kursor esa jim bo'sh sahifa o'rniga `422` beradi.**

## Performance

- **Duration:** ~70 min
- **Tasks:** 3 (4 ta atomik commit — TDD RED/GREEN ajratilgan)
- **Files modified:** 4
- **Testlar:** `test_reconciliation_api.py` 22 → 30 test; `test_phase7_criteria.py::test_sc2` kengaytirildi

## Accomplishments

- **B-2 ning server yarmi yopildi.** `payload.assignee_user_id` marshrutda O'QILADI va
  `transition()` ga uzatiladi. Bugungacha u jimgina tashlanardi va SQL har o'tishda
  case'ni HUKM CHIQARGAN odamga biriktirardi — javob esa `200` edi.
- **Tenancy teshigi ochilmadi.** `UserRepository(session, market_id).member_roles()`
  darvozasi `transition()` dan OLDIN turadi. `0023:344-347` tekshiruvni «ilova
  qatlamida» deb yozgan va shu vaqtgacha repoda `user_market_roles` ustidan
  **birorta tekshiruv yo'q edi** — ya'ni maydonni tekshiruvsiz ulash uni tashlab
  yuborishdan YOMONROQ bo'lardi.
- **Uchta xulq nuqsoni birdaniga yopildi:** direktor tanlovi yoziladi, `null`
  biriktirishni HAQIQATAN bekor qiladi, maydonsiz o'tish esa mavjud egani
  o'g'irlamaydi.
- **WR-01:** `from_status IS NULL` yo'li mahsulotda tirildi — sxema, model va API uni
  uch joyda e'lon qilgan bo'lsa ham, undan HECH QACHON qator o'tmagan edi.
- **WR-05:** ikkala kursor dekoderi ham tz-siz qiymatni `422` ga aylantiradi.

## Task Commits

1. **Task 1 (RED): mas'ul va begona-bozor darvozasi** — `dd5b978` (test)
2. **Task 1 (GREEN): mas'ul serverga yetadi va begona bozor rad etiladi** — `3b4d08f` (feat)
3. **Task 2: tug'ilish hodisasi + naive kursor** — `9e2e74c` (feat, test bilan birga)
4. **Task 3: faza darvozasi (`test_sc2`) mas'ulni haqiqatan o'lchaydi** — `7799314` (test)

## Files Created/Modified

- `services/core-api/app/api/v1/reconciliation.py` — `_ASSIGNEE_NOT_IN_MARKET` kodi,
  `model_fields_set` bilan «yuborildimi?» tekshiruvi, `member_roles()` darvozasi,
  ikkala kursor dekoderida `tzinfo is None` shoxi.
- `services/core-api/app/repositories/reconciliation_repo.py` —
  `transition(assignee_user_id=..., assignee_explicit=...)`; `_UPDATE_CASE_STATUS` da
  `CASE WHEN` ikki shoxi; `_OPEN_ANOMALY_CASES` va `_OPEN_UNPAID_CASES` da `born` CTE si.
- `tests/integration/test_reconciliation_api.py` — 8 yangi test (5 mas'ul/tenancy,
  1 tug'ilish, 2 kursor), `_CASE_ROW` / `_MEMBER_ROLES` yordamchilari,
  `_seed_evidenced_anomaly()` (case'siz seed — job uni O'ZI ochsin).
- `tests/integration/test_phase7_criteria.py` — `test_sc2` mas'ulni bazadan o'qiydi,
  hodisalar soni `== 3` ga qulflandi, `_CASE_ASSIGNEE` yordamchisi.

## Decisions Made

Yuqoridagi `key-decisions` ro'yxatiga qarang. Eng qimmat ikkitasi:

1. **`COALESCE` argumentlarining TARTIBI almashdi.** Eski shakl
   (`COALESCE(:actor_user_id, assignee_user_id)`) AKTORNI tanlardi, ya'ni har holat
   o'zgarishi mavjud biriktirishni o'g'irlardi. Yangi shakl
   (`COALESCE(assignee_user_id, :actor_user_id)`) mavjud egani SAQLAYDI, egasiz
   case'ni esa uni qo'lga olgan odamga beradi — ya'ni B-2 ning «jimgina o'g'irlash»
   bandi yopildi, `_UPDATE_CASE_STATUS` docstringidagi mavjud qoida esa (egasiz case
   qo'lga olinadi) buzilmadi.

2. **Aktivlik tekshiruvi ATAYIN qo'shilmadi.** `member_roles()` a'zolikni o'lchaydi,
   faollikni emas. Nofaol xodimni serverda bloklash mavjud biriktirishni ham (u
   nofaol bo'lib qolganda) qayta yozib bo'lmaydigan qilardi — case abadiy o'sha
   odamda qolardi. Sabab marshrut docstringiga yozildi.

## Sabotaj natijalari (majburiy)

Ikkala sabotaj ham KOMPILYATSIYA qildi, NOMLANGAN assertlarni qizartirdi va
`git checkout --` bilan qaytarildi. Qaytarilgandan keyin `git status --porcelain
services/` — **BO'SH**.

| # | Sabotaj | Kutilgan | ⛔ O'LCHANGAN |
|---|---------|----------|---------------|
| **S-1** | `_UPDATE_CASE_STATUS` ni eski `COALESCE(:actor_user_id, assignee_user_id)` xulqiga qaytarish (bind parametrlar saqlangan holda) | «direktor tanlagan mas'ul yoziladi» testi VA `test_sc2` qizaradi | **4 QIZIL** — kutilganidan KENGROQ: `test_the_director_assigns_the_case_to_a_market_member`, `test_an_explicit_null_clears_the_assignment`, `test_a_silent_transition_keeps_the_existing_assignee`, `test_sc2...` (`test_phase7_criteria.py:935` — «direktor TANLAGAN mas'ul bazaga yozilmadi»). Tenancy testlari YASHIL qoldi — ular SQL gacha yetib bormaydi, ya'ni ikki darvoza MUSTAQIL. |
| **S-2** | Marshrutdan `member_roles()` tekshiruvini olib tashlash | begona-bozor testi qizaradi (`200` qaytadi), qolganlari yashil | **AYNAN 2 QIZIL** — `test_a_foreign_market_member_cannot_be_assigned` va `test_an_unknown_user_is_rejected_like_a_foreign_one` (`test_reconciliation_api.py:1050`). Javob tanasida begona `user_id` case'ga **YOZILGAN** holda qaytdi (`assignee_user_id: "9243a618-…"`, `actor_user_id: "87d92b5c-…"`) — teshik jonli ko'rsatildi. Boshqa hamma test yashil, ya'ni darvoza ANIQ. |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - O'lchov tuzatildi] Naive kursorning HAQIQIY xulqi rejadagidan boshqa (va yomonroq) chiqdi**

- **Found during:** Task 2
- **Issue:** Reja `500 internal_error` ni kutgan edi (`asyncpg` tz-siz `datetime` ni
  `timestamptz` ga kodlay olmaydi degan farazda). O'LCHOV boshqasini ko'rsatdi:
  so'rov bazagacha BORADI va **`200`** qaytadi — `rows` BO'SH, hisoblagich esa
  haqiqiy sonda (`new_count: 2`, `pending_count: 2`). Ya'ni nuqson server nosozligi
  emas, ⛔ **JIM YOLG'ON javob** — aynan `_decode_cursor()` ning O'Z docstringi
  taqiqlagan holat («buzilgan qiymat ⛔ 422, jim e'tiborsizlik EMAS»).
- **Fix:** Tuzatish rejadagi bilan AYNI (`tzinfo is None` -> `422`), lekin testlar va
  docstringlar KUTILGAN emas, O'LCHANGAN haqiqatga yozildi. Assertlar ikkalasini ham
  qulfladi (`!= 500` VA `== 422`), ya'ni mexanizm kelajakda o'zgarsa ham da'vo
  o'zgarmaydi.
- **Files modified:** `reconciliation.py`, `test_reconciliation_api.py`
- **Verification:** Ikkala dekoder uchun ham alohida test; nazorat sifatida SERVER
  QURGAN kursor ikkinchi sahifani beradi.
- **Committed in:** `9e2e74c`

**2. [Rule 3 - Bloklovchi] `test_sc2` da «nazoratchi» o'rniga bozor admini**

- **Found during:** Task 3
- **Issue:** Reja mas'ul sifatida «A bozorining **nazoratchisi**» ni, «fixture'da
  mavjud rol» izohi bilan talab qildi. `Role.INSPECTOR` enum'da BOR, lekin
  `tests/fixtures/two_markets.py` har bozorga faqat `market_admin` / `cashier` /
  `director` seed qiladi — **inspector foydalanuvchisi yo'q**.
- **Fix:** `market_a.admin_user_id` ishlatildi — A bozorining HAQIQIY a'zosi va
  direktordan FARQ QILADI. O'lchanadigan da'vo o'zgarmadi: «tanlangan mas'ul
  yoziladi VA u aktorga teng emas».
- **Files modified:** `test_phase7_criteria.py`, `test_reconciliation_api.py`
- **Verification:** `assert assignee_id != director_id` nazorat asserti test ichida —
  seed bir kun ikkalasini bitta odam qilib qo'ysa, test o'zi qizaradi.
- **Committed in:** `7799314` (va `dd5b978`)

**3. [Rule 3 - TDD tartibi] Tenancy testi Task 3 dan Task 1 ga ko'chdi**

- **Found during:** Task 1
- **Issue:** Reja begona-bozor testini Task 3 ga qo'ygan, lekin Task 1 `tdd="true"` —
  ya'ni test tekshiruv YOZILISHIDAN OLDIN qizil bo'lishi kerak.
- **Fix:** Test Task 1 ning RED commitida (`dd5b978`) yozildi. Fayl, assertlar va
  nazoratlar rejadagidek qoldi (jumladan «B bozorida o'sha `user_id` HAQIQATAN
  mavjud» nazorati).
- **Files modified:** `test_reconciliation_api.py`
- **Committed in:** `dd5b978`

---

**Total deviations:** 3 auto-fixed (1 o'lchov tuzatishi, 2 bloklovchi).
**Impact on plan:** Rejaning birorta da'vosi zaiflashmadi — 1-chetlanish da'voni
KUCHAYTIRDI (ikki xil nosozlik shakli ham qulflandi).

## Issues Encountered

- **`ruff format` uzun `assert ... is None` ifodasini qayta terdi** — formatlangan
  shakl qabul qilindi.
- Boshqa muammo yo'q. Muhit gotcha'lari (`.env` va `ops/seaweedfs/s3.json` nusxasi,
  izolyatsiyalangan compose loyihasi, `--no-deps` bilan `storage` ni chetlab o'tish)
  oldindan ma'lum edi va qayta kashf qilinmadi.

## Verification

| # | Tekshiruv | Natija |
|---|-----------|--------|
| 1 | `pytest test_reconciliation_api.py test_reconciliation_repo.py test_phase7_criteria.py test_delivery_surface.py tests/tenancy -q` | ✅ yashil |
| 2 | `ruff check . && ruff format --check . && mypy .` | ✅ `All checks passed` / `347 files already formatted` / `no issues found in 338 source files` |
| 3 | Ikkala sabotaj bajarilgan va jadval bilan hujjatlangan | ✅ yuqoridagi jadval |
| 4 | `git diff --name-only` da `migrations/`, `app/schemas.py`, `pyproject.toml` YO'Q | ✅ aynan 4 fayl, hammasi `files_modified` ichida |
| 5 | `grep -c "assignee_user_id" reconciliation.py` >= 3 | ✅ **8** |
| 6 | `grep -c "member_roles" reconciliation.py` >= 1 | ✅ **3** |
| 7 | `grep -c "cursor_invalid" reconciliation.py` >= 4 | ✅ **5** |

## Ochiq bandlar

1. ⚠ **07-23 uchun (rejada nomma-nom talab qilingan):** `assignee_not_in_market`
   kodining KLIENT xaritasi va uchala locale matni bu rejada YOZILMADI (frontend
   fayllari boshqa egada). Xarita qo'shilmaguncha ekranda xato `errors.generic`
   («Kutilmagan xato») bo'lib chiqadi — ya'ni direktor NIMA noto'g'ri bo'lganini
   bilmaydi.

2. ⚠ **`app/schemas.py::CaseUpdateRequest` docstringi endi ESKIRGAN va u ATAYIN
   tegilmadi.** U hamon shunday deydi: «`None` = «mas'ulni O'ZGARTIRMA», «egasiz
   qoldir» EMAS ... Biriktirishni BEKOR QILISH amali bugun YO'Q va u qo'shilganda
   ALOHIDA argument bilan keladi». Bugundan boshlab bu **YOLG'ON**: `null`
   biriktirishni bekor qiladi va ALOHIDA argument (`assignee_explicit`) ALLAQACHON
   qo'shilgan. Reja `app/schemas.py` ni diffda bo'lishini nomma-nom taqiqlagani
   (tekshiruv #4) uchun tuzatish keyingi rejaga qoldirildi. ⛔ Bu bir qatorlik
   docstring tahriri, lekin u KOD O'QUVCHISINI adashtiradi.

3. ⚠ **`_UPDATE_CASE_STATUS` ning `resolution_note` bandi hamon `COALESCE`** — ya'ni
   yechim MATNINI tozalash amali yo'q. Bu ONGLI (mahsulotda bunday amal yo'q), lekin
   mas'ul bilan yechim matni endi TURLI qoidaga bo'ysunadi va farq faqat docstringda
   yozilgan.

4. ⚠ **`born` CTE si faqat `open_cases()` yo'lini qamraydi.** Qo'lda (fixture
   `seed_case()` bilan yoki kelajakda boshqa yozuvchi orqali) yaratilgan case tarixi
   hamon BO'SH boshlanadi. Bugun `reconciliation_cases` ga mahsulotda yozadigan
   YAGONA yo'l — `open_cases()`, ya'ni bo'shliq nazariy; lekin ikkinchi yozuvchi
   paydo bo'lgan kuni bu qoida u yerda ham TAKRORLANISHI shart.

## Next Phase Readiness

- Mezon #2 ning **server yarmi** yopildi: mas'ul yoziladi, tenancy darvozasi bor va
  sabotaj bilan o'lchangan, case tarixi tug'ilishdan boshlanadi.
- Mezon #2 ning **klient yarmi** 07-21/07-22/07-23 da qoladi (xato xaritasi, navbat
  UI ning uch nuqsoni).
- `07-21` bilan fayl kesishmasi YO'Q (tasdiqlangan); `deferred-items.md` ga
  YOZILMADI.

## Self-Check: PASSED

- Fayllar: 4/4 o'zgartirilgan fayl + SUMMARY diskda MAVJUD.
- Commitlar: `dd5b978`, `3b4d08f`, `9e2e74c`, `7799314` — to'rttasi ham `git log` da.
- Yakuniy to'plam: **805 test yashil** (`test_reconciliation_api.py` +
  `test_reconciliation_repo.py` + `test_phase7_criteria.py` +
  `test_delivery_surface.py` + `tests/tenancy`), exit code `0`.
- `ruff check` / `ruff format --check` / `mypy` — toza.
- `git status --short` sabotajlardan keyin BO'SH; diffda faqat `files_modified`
  ro'yxatidagi 4 fayl.
- ⛔ `STATE.md`, `ROADMAP.md`, `deferred-items.md` — TEGILMADI.

---
*Phase: 07-nomuvofiqlik-bildirishnoma-va-botlar*
*Completed: 2026-08-13*
