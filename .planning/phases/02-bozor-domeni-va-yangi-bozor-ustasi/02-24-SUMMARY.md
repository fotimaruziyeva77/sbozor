---
phase: 02-bozor-domeni-va-yangi-bozor-ustasi
plan: 24
subsystem: backend+frontend
tags: [import, xlsx, rbac, staff, credentials, audit, multi-tenant, i18n, sabotage, market-07]

# Dependency graph
requires:
  - phase: 02-bozor-domeni-va-yangi-bozor-ustasi
    provides: "02-12 — xavfsiz `.xlsx` o'qish (uch darvoza), `import_validator`, `xlsx_template`, all-or-nothing tranzaksiya va D-15 qayta-import himoyasi"
  - phase: 02-bozor-domeni-va-yangi-bozor-ustasi
    provides: "02-16 — `ImportPanel` ning to'rt holati va `useImportMutation` / `downloadTemplate` kontrakti"
  - phase: 01-poydevor
    provides: "D-04 rol berish darajasi (`users.py`), D-02 vaqtinchalik parol, `auth_create_user` (`SECURITY DEFINER`), `write_app_audit`"
  - phase: 02-bozor-domeni-va-yangi-bozor-ustasi
    provides: "02-22 — `scripts/check-requirements-sync.mjs` va MARKET-07 ning ochiq qolgan bandi"
provides:
  - "`POST /api/v1/imports/staff` — bitta `.xlsx` bilan o'nlab hisob, rollari va bir martalik parollari bilan (MARKET-07)"
  - "`GET /api/v1/imports/template?kind=staff` — uch tilli xodimlar shabloni, rol ro'yxati chaqiruvchining D-04 darajasidan"
  - "`app/services/staff_accounts.py` — D-04 rol berish darajasining va D-02 parolining YAGONA manbai (`POST /users` ham shu yerdan oladi)"
  - "`import_validator.validate_staff_rows` + `phone_taken_issue` — yozishdan OLDIN to'liq tekshiruv, qator-raqamli xatolar"
  - "`UserRepository.create_members` / `existing_member_phones` — ochiq parol kirmaydigan ommaviy yaratish yo'li"
  - "`StaffCredentials` — parollarning bir martalik ro'yxati, KLIENTDA qurilgan `;`+BOM li csv fayl"
  - "`.planning/REQUIREMENTS.md` — MARKET-07 ikkala joyda `Done`; qamrov sanoqlari fayl mazmunidan qayta hisoblangan (46 -> 49)"
affects: [03-nvr, 06-billing]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Ikkinchi chaqiruvchi paydo bo'lganda qoida ENDPOINTDAN servis moduliga ko'chadi, nusxa olinmaydi (`staff_accounts.py`)"
    - "Bitta import mashinasiga uchinchi VARAQ TURI qo'shiladi — parallel quyi tizim ochilmaydi"
    - "Bir xil ko'rinadigan ikki rad etish ATAYIN ikki kod bilan ajratiladi, chunki adminning HARAKATI boshqa (`invalid_role` vs `role_not_allowed`)"
    - "Maxfiy javob alohida DTO oladi, umumiy javobdan MEROS OLMAYDI — meros parol maydonini boshqa javoblarga oqizardi"
    - "Ochiq sir repozitoriy qatlamiga umuman kirmaydi; jurnalga faqat SANOQ uzatiladi (senzura ikkinchi qatlam)"
    - "Fayl mijoz mashinasida quriladi, serverga qaytarilmaydi — server yo'li sirni ikkinchi marta tarmoqqa chiqarardi"
    - "Ommaviy amal auditda IKKI darajada: har obyekt uchun qator + amalning O'ZI uchun `row_id=None` li yig'ma yozuv"

key-files:
  created:
    - services/core-api/app/services/staff_accounts.py
    - tests/unit/test_staff_import_validator.py
    - tests/integration/test_staff_import.py
    - frontend/src/components/import/staff-credentials.tsx
    - frontend/src/components/import/staff-credentials.test.tsx
  modified:
    - services/core-api/app/api/v1/imports.py
    - services/core-api/app/api/v1/users.py
    - services/core-api/app/repositories/user_repo.py
    - services/core-api/app/services/import_validator.py
    - services/core-api/app/services/xlsx_template.py
    - services/core-api/app/schemas.py
    - services/core-api/app/settings.py
    - tests/fixtures/admin_api.py
    - tests/tenancy/test_cross_tenant.py
    - tests/tenancy/test_route_coverage.py
    - tests/unit/test_xlsx_template.py
    - frontend/src/components/import/import-panel.tsx
    - frontend/src/components/import/import-errors.tsx
    - frontend/src/app/[locale]/(app)/users/page.tsx
    - frontend/src/lib/market-queries.ts
    - frontend/src/lib/api-types.ts
    - frontend/src/lib/market-errors.ts
    - frontend/messages/uz-Latn.json
    - frontend/messages/ru.json
    - frontend/messages/uz-Cyrl.json
    - frontend/messages/uz-Cyrl.overrides.json
    - frontend/scripts/role-gate.test.mjs
    - frontend/scripts/gen-cyrillic.test.mjs
    - .planning/REQUIREMENTS.md

key-decisions:
  - "D-04 darajasi `users.py` dan `services/staff_accounts.py` ga KO'CHIRILDI (nusxa olinmadi) — endi ikkita chaqiruvchi bor va ikki nusxa bir kun ajralib ketardi"
  - "Shablonning namunaviy telefoni `+` SIZ yoziladi: `+` — formula prefiksi va qochirish uni O'Z shablonining importidan `invalid_phone` bilan qaytarardi (vendors shabloni ham shu bug bilan yashagan)"
  - "`phone_taken` qator xatosi `imports.py` dan `import_validator.py` ga ko'chdi — aks holda u frontend i18n darvozasidan tashqarida qolib, rus tilidagi admin uz-Latn matnini ko'rardi"
  - "`import_max_staff_rows = 200` — `import_max_rows` (5000) dan ALOHIDA: Argon2id CPU narxi va bir so'rovda telefon sanab chiqish yuzasi (T-02-181)"
  - "`StaffImportResponse` `ImportResultResponse` dan meros OLMAYDI — `credentials` maydoni javobni maxfiy qiladi"
  - "D-15 skip xodimlar uchun XAVFSIZLIK qarori: muqobil (parolni qayta berish) roster faylini ommaviy parol tiklash quroliga aylantirardi"
  - "csv fayli klientda quriladi, `;` ajratgich va UTF-8 BOM bilan — CIS lokalidagi Excel `,` ni ustun chegarasi deb o'qimaydi"
  - "`USERS_QUERY_KEY` (global, doiralanmagan) qayta ixtiro QILINMADI — yangi kalit ro'yxatni ikki kalit ostida bo'lardi; tenant chegarasi `client.clear()` bilan ta'minlanadi (CR-01 naqshi)"

patterns-established:
  - "Pattern: rol/holat kabi enum qiymatlari shablonda TARJIMA QILINMAYDI (D-16) — sarlavha uch tilda, qiymat bitta tilda"
  - "Pattern: matritsaning fayl fillerи GLOBAL jadvalga yozadigan marshrut uchun har chaqiruvda unikal identifikator quradi, aks holda pozitiv darvoza YOLG'ON qizaradi"
  - "Pattern: `.planning/` hujjatidagi sanoq faylning O'Z mazmunidan qayta hisoblanadi, qo'lda taxmin qilinmaydi"

requirements-completed: [MARKET-07]

# Metrics
duration: 195min
completed: 2026-08-03
---

# Phase 2 Plan 24: Xodimlar rosteri importi (MARKET-07)

**Bozor admini endi `/users` sahifasidan uch tilli shablonni oladi va ma'muriyat bergan xodimlar ro'yxatini BITTA fayl bilan hisobga aylantiradi: telefonlar E.164 ga normallanadi, rollar RBAC matritsasidan tekshiriladi, vaqtinchalik parollar bir marta ko'rsatiladi va hech qayerda saqlanmaydi — hammasi mavjud import mashinasining UCHINCHI varaq turi sifatida, parallel quyi tizimsiz.**

## Holat

**Reja to'liq bajarildi.** Uchala task ham yetkazildi. To'rtala sabotaj o'lchandi va har biri AYNAN kutilgan testni qizartirdi (bittasi kutilganidan bitta ko'proq testni qizartirdi — sabab quyida). `npm run gate` yashil: **571 s**, exit 0.

## Nima qurildi

### Task 1 — rol darajasining yagona manbai, validator va shablon

`app/services/staff_accounts.py` yangi modul: `assignable_roles(is_platform_admin)`, `MARKET_ADMIN_ASSIGNABLE_ROLES`, `PLATFORM_ADMIN_ASSIGNABLE_ROLES`, `temporary_password()`, `TEMPORARY_PASSWORD_BYTES`. `Role.PLATFORM_ADMIN` ikkala natijada ham YO'Q (CR-03).

`users.py` shu manbaga ulandi. Refaktoring xulqni o'zgartirmadi: `_assert_roles_assignable()` ning ikki bosqichi, ikkala `log.info` va ikkala 403 saqlandi; o'zgargani faqat ikkinchi bosqichning to'plami endi `assignable_roles(...)` dan olinishi. `tests/integration/test_users_api.py` tegilmasdan yashil qoldi.

`import_validator.py`: `STAFF_COLUMNS = 3`, `StaffImportRow`, `validate_staff_rows(...)`, `phone_taken_issue(...)`. Rol katagi `,` VA `;` bo'yicha bo'linadi, registr farqi va atrofdagi bo'sh joy ahamiyatsiz, katakdagi takroriy rol siqiladi.

`xlsx_template.py`: `TEMPLATE_KINDS` uchtaga kengaydi, `build_template(..., roles=...)` kalit-so'zli argument oldi, `_TEXTS` uchala tiliga uchta yangi kalit qo'shildi, yashirin ma'lumotnoma varag'i `staff` uchun ochildi va `data_validation` C ustuniga bog'landi.

### Task 2 — marshrut, ommaviy yaratish, audit, matritsa

`POST /imports/staff` (`USER_MANAGE`) o'n bosqichli tartibda ishlaydi va tartib docstringda literal yozilgan. `GET /imports/template?kind=staff` ham `USER_MANAGE` ortida (direktorda bu huquq yo'q — D-07).

`UserRepository.create_members()` band telefonda TO'XTAMAYDI — hammasini yig'adi, chunki admin band raqamlarning hammasini bir marta ko'rishi kerak. `existing_member_phones()` yangi so'rov yozmaydi, `list_members()` ning ikki qatlamli naqshini qayta ishlatadi.

Audit ikki darajada: har hisob uchun `INSERT/users/row_id` + ommaviy import uchun `row_id=None` li yig'ma yozuv (`rows`/`created`/`skipped`/`roles`).

### Task 3 — panel, parol ro'yxati, uch til, MARKET-07

`ImportPanel` ga `kind="staff"` tarmog'i qo'shildi (A/B/C1 holatlari tegilmadi). `TEXTS` xaritasi sarlavha, hint va D-15 tushuntirishini tur bo'yicha ajratadi: xodimlar uchun matn parol ham, rol ham tegilmaganini ANIQ aytadi.

`StaffCredentials` — majburiy ogohlantirish (`role="alert"`), har qator uchun nusxa tugmasi, «hammasini nusxalash» va klientda qurilgan csv fayl. `buildCredentialsCsv()` sof funksiya sifatida ajratilgan.

`.planning/REQUIREMENTS.md`: MARKET-07 ikkala joyda belgilandi va qamrov sanoqlari faylning O'Z mazmunidan qayta hisoblandi.

## O'lchangan natijalar

| Darvoza | Buyruq | 02-22 | 02-24 |
|---|---|---|---|
| Backend (to'liq) | `pytest -q` | 916 | **976** |
| Tenancy | `pytest tests/tenancy -q` | 317 | **322** |
| Frontend node | `node --test scripts/*.test.mjs` | 57 | **57** |
| Frontend vitest | `vitest run` | 67 | **73** |
| i18n kalitlari | `npm run i18n:check` | 424 × 3 | **439 × 3** |
| To'liq darvoza | `npm run gate` | 585 s | **571 s**, exit 0 |

Fayl kesimida: `tests/unit/test_staff_import_validator.py` — **27** test (talab ≥ 18); `tests/unit/test_xlsx_template.py` — **44** (02-12 dagi 37 dan katta); `tests/integration/test_staff_import.py` — **21** (talab ≥ 16).

`MINIMUM_MATRIX_ROUTES`: **34 -> 35** (amaldagi marshrutlar soni 43 -> 44).
`MARKET_ERROR_CODES`: **23 -> 24** (`staff_roster_too_large`).

### Mexanik darvozalar

| Tekshiruv | Kutilgan | Natija |
|---|---|---|
| `grep -c "MARKET_ADMIN_ASSIGNABLE_ROLES\s*=\s*frozenset"` `users.py` / `staff_accounts.py` | 0 / 1 | **0 / 1** ✅ |
| `grep -c "secrets.token_urlsafe"` `users.py` / `staff_accounts.py` | 0 / 1 | **0 / 1** ✅ |
| `imports.py` tranzaksiya ochish atamalari | 0 | **0** ✅ |
| `imports.py` dagi `log.*` chaqiruvlari | parol argumenti yo'q | **yo'q** — `staff_import_done` faqat `created`/`skipped`, `staff_roster_too_large` faqat `rows`/`limit` ✅ |
| OpenAPI `imports` marshrutlari | beshta, `staff` bilan | **mos** ✅ |
| `TEMPLATE_KINDS` | `('stalls','vendors','staff')` | **mos** ✅ |
| `xlsx_template.py` to'g'ridan-to'g'ri yozish | faqat `_write_text()` ichida | **484-qator, yagona** ✅ |
| `kind="staff"` `/users/page.tsx` da | 1 | **1** ✅ |
| `console.` `staff-credentials.tsx` da | 0 | **0** ✅ |
| `temporary_password` `api-client.ts` da | 0 | **0** ✅ |
| `check-requirements-sync.mjs` | exit 0 | **exit 0** (49 talab, Done 7) ✅ |
| MARKET-07 ikkala joyda | 1 / 1 | **1 / 1** ✅ |
| `v1 requirements: 46` qoldig'i | 0 | **0** ✅ |
| Boshqa fazalarning bandlari | tegilmagan | **0 diff** ✅ |
| `uv.lock` / `package-lock.json` / `migrations/` | bo'sh | **bo'sh** — yangi paket ham, migratsiya ham yo'q ✅ |

## Sabotaj o'lchovlari

Reja uchtasini talab qilgan; to'rtinchisi Task 3 ning qabul mezonida edi.

### S1 — `phone_taken` rad etishini olib tashlash (band telefonlar jimgina o'tkazib yuboriladi)

**Kutilgan:** `test_phone_taken_by_another_market_is_also_all_or_nothing` qizaradi, qolgani yashil.

**Natija — AYNAN KUTILGANDEK.** Yiqilgan: `test_phone_taken_by_another_market_is_also_all_or_nothing` (200 kutilgan 422 o'rniga). Nazorat guruhi: qolgan **20** test yashil.

Jurnal qatori buzilishning butun mohiyatini ko'rsatdi: `staff_import_done created=2 skipped=1` — ya'ni endpoint uchta qatorli fayldan ikkitasini yozib, uchinchisini JIMGINA yutgan va adminga 200 qaytargan bo'lardi.

### S2 — D-15 skip tarmog'ini olib tashlash (`existing_member_phones` bo'sh uzatiladi)

**Kutilgan:** `test_reimport_does_not_reset_passwords` qizaradi.

**Natija — KUTILGANIDAN BITTA KO'P, VA BU TO'G'RI.** Yiqilganlar: `test_reimport_does_not_reset_passwords` VA `test_reimport_does_not_change_roles`. Ikkinchisi rejada nomlanmagan, chunki u shu rejada QO'SHILGAN ikkinchi D-15 testi (rol tiklanmasligi) — ikkalasi ham AYNAN o'sha tarmoqni o'lchaydi. Nazorat guruhi: qolgan **19** test yashil.

Muhim topilma: skipsiz qayta import 200 emas, **422 `phone_taken`** beradi (`counts={'phone_taken': 1}`). Ya'ni D-15 ning yo'qolishi «parol tiklandi» ga emas, «qayta import umuman ishlamaydi» ga olib borardi — birinchisidan yaxshiroq, lekin baribir buzuq: admin roster faylini ikkinchi marta yuklay olmasdi.

### S3 — matritsa fillerida telefonni qattiq yozilgan raqamga almashtirish

**Kutilgan:** `test_file_routes_actually_execute[POST_/api/v1/imports/staff]` qizaradi.

**Natija — AYNAN KUTILGANDEK.** Yiqilgan: aynan o'sha bitta parametr (422 `phone_taken`). Boshqa ikkita fayl marshruti (`stalls`, `vendors`) va butun tenancy to'plami yashil qoldi.

Bu 02-12 deviatsiya #9 ning davomi: mexanizm (`FILE_FILLERS`) to'g'ri bo'lib, uning YO'QLIGINI ko'rsatadigan pozitiv darvoza bo'lmasa, marshrut matritsada «bor» bo'lib turib jimgina sinovsiz qolardi.

### S4 — `staff-credentials.tsx` dan nusxa tugmasining `writeText` chaqiruvini olib tashlash

**Kutilgan:** nusxa testi qizaradi, qolgan beshtasi yashil.

**Natija — AYNAN KUTILGANDEK.** Yiqilgan: `qator tugmasi buferga AYNAN parolni yozadi`. Nazorat: `1 failed | 72 passed (73)` — ya'ni ayni fayldagi qolgan beshta test ham, boshqa o'nta test fayli ham yashil.

Har sabotajdan keyin `git checkout` bilan tiklandi va `git status --short` (izlanmagan `.docx` fayllardan tashqari) BO'SH ekani tekshirildi.

## Rejadan chetlanishlar

### Avtomatik tuzatilganlar

**1. [Rule 1 - Bug] Shablonning namunaviy telefoni O'Z importidan `invalid_phone` bilan qaytardi**

- **Topildi:** Task 1, `test_staff_template_is_parsed_back_identically_in_every_locale`
- **Muammo:** `_sample_row()` telefonni `+998901234567` deb yozardi. `+` — `FORMULA_PREFIXES` a'zosi, ya'ni `escape_formula()` uni apostrof bilan qochiradi (TO'G'RI xulq, T-02-91) va katakdagi qiymat `'+998901234567` bo'lib qoladi. `normalize_phone()` apostrofni raqam deb qabul qilmaydi.
- **Ta'siri kengroq:** ayni qiymat **`vendors` shablonida ham** turgan edi va u yerda hech qanday aylanma testi yo'q — ya'ni bug 02-12 dan beri jimgina yashab kelgan.
- **Tuzatish:** `_SAMPLE_PHONE = "998901234567"` (`+` siz) — `normalize_phone` qabul qiladigan va admin AMALDA yozadigan shakl; ikkala shablon ham shu konstantani ishlatadi.
- **Fayllar:** `services/core-api/app/services/xlsx_template.py`
- **Commit:** `d9598b4`

**2. [Rule 2 - Missing critical] `phone_taken` qator xatosi frontend i18n darvozasidan tashqarida qolgan edi**

- **Topildi:** Task 3, `error-codes.test.mjs` ni tahlil qilishda
- **Muammo:** `ImportIssue(code="phone_taken")` `imports.py` da qurilardi, darvoza esa `import.errors.*` tarjimalarini AYNAN `import_validator.py` dagi kodlar bilan solishtiradi. Ya'ni tarjima kalitini qo'shishning iloji yo'q edi (darvoza qizarardi) va rus tilidagi admin uz-Latn matnini ko'rardi.
- **Tuzatish:** `import_validator.phone_taken_issue()` yordamchisi — xato validator modulida quriladi, router uni chaqiradi. Uchala tilda tarjima qo'shildi.
- **Fayllar:** `services/core-api/app/services/import_validator.py`, `services/core-api/app/api/v1/imports.py`
- **Commit:** `b0197f0`

**3. [Rule 3 - Blocking] `role-gate.test.mjs` eski Python yo'liga qarab qolgan edi**

- **Topildi:** Task 3, `npm --prefix frontend test`
- **Muammo:** Darvoza `MARKET_ADMIN_ASSIGNABLE_ROLES` ni `services/core-api/app/api/v1/users.py` dan o'qirdi; Task 1 uni `services/staff_accounts.py` ga ko'chirgan edi.
- **Tuzatish:** yo'l yangi manbaga qaratildi va ko'chish sababi darvoza docstringiga yozildi. **Bu darvozaning to'g'ri ishlagani:** u ko'chishni O'ZI ushladi (`MARKET_ADMIN_ASSIGNABLE_ROLES Python faylida topilmadi`), ya'ni «sukut bilan yashil qolish» sinfidan xoli.
- **Fayllar:** `frontend/scripts/role-gate.test.mjs`
- **Commit:** `b0197f0`

**4. [Rule 3 - Blocking] `csv` so'zi kirill transliteratsiya darvozasini qizartirdi**

- **Topildi:** Task 3, `gen-cyrillic.test.mjs`
- **Muammo:** `staffCredentials.download` matnidagi `csv` harfma-harf o'girilib `цсв` bo'lardi.
- **Tuzatish:** `uz-Cyrl.overrides.json` -> `words` ga `csv`/`CSV` qo'shildi (`Excel`/`xlsx` bilan AYNAN bir xil naqsh) va `gen-cyrillic.test.mjs` dagi allowlist ham yangilandi — ikkala ro'yxat JUFT yuritiladi va biri unutilsa test qizaradi.
- **Fayllar:** `frontend/messages/uz-Cyrl.overrides.json`, `frontend/scripts/gen-cyrillic.test.mjs`
- **Commit:** `b0197f0`

### Qabul mezonidan chetlanish (bajarilmadi, sabab bilan)

**`grep -c "temporary_password" services/core-api/app/repositories/user_repo.py` = 0** — bu mezon **ERISHIB BO'LMAYDI** va u noto'g'ri taxminga qurilgan: fayldа 01-07 dan beri `set_temporary_password()` METODI bor (`POST /users/{id}/reset-password` uni chaqiradi) va u ATAMANI o'z nomida saqlaydi.

Amaldagi qiymat — **1** (o'sha mavjud metod nomi). Mezonning MAQSADI esa to'liq bajarildi va u kuchliroq shaklda tekshirildi:

- ochiq parol repozitoriy qatlamiga UMUMAN kirmaydi — uchala yozish yo'lining ham parametri `password_hash`;
- `StaffCreateEntry` da `password_hash` maydoni bor, ochiq maydon YO'Q;
- ochiq qiymat `imports.py` dagi `secrets_by_row` lokal lug'atida qoladi va faqat javob DTO'siga o'tadi.

Metodni qayta nomlash MARKET-07 bilan bog'liq bo'lmagan 01-07 API'sini sababsiz o'zgartirardi. Modul docstringida tekshiriladigan atama ATAYIN yozilmadi (`imports.py` dagi tranzaksiya izohi bilan bir xil qaror — 02-08 deviatsiya #3), ya'ni izohning o'zi darvozani buzmaydi.

## Ijro paytidagi ogohlantirish (jarayon topilmasi)

Task 2 ning sabotaj bosqichida `git checkout -- services/core-api/app/api/v1/imports.py` bilan tiklashga urinildi, holbuki fayl HALI COMMIT QILINMAGAN edi — natijada butun `import_staff` endpointi yo'qoldi va qayta yozildi (~15 daqiqa). Xulosa keyingi rejalar uchun: **sabotaj o'lchovi FAQAT commit qilingan kod ustida bajariladi.** Qolgan uchala sabotaj shu tartibda o'tkazildi va tiklash muammosiz kechdi.

## Xavfsizlik yuzasi (threat register bo'yicha)

| Threat | Qanday yopildi | Dalil |
|---|---|---|
| T-02-175 (rol orqali huquq oshirish) | `assignable_roles()` yagona manba; `platform_admin` ikkala darajada ham yo'q | 4 ta integratsiya testi + 4 ta unit test |
| T-02-176 (parolning jurnalga/keshga tushishi) | repozitoriyga faqat hash; `log.*` faqat sanoq; `Cache-Control: no-store`; `useMutation` | `test_response_is_not_cacheable`, `test_audit_never_contains_a_temporary_password` |
| T-02-177 (csv orqali tarqalish) | fayl klientda, serverga qaytmaydi; majburiy ogohlantirish; nomda parol yo'q | `staff-credentials.test.tsx` (6 test) |
| T-02-178 (qisman yozilgan roster) | tranzaksiya `TenantSessionDep` da; `phone_taken` ham 422 | 3 ta SANOQ assertion'i, S1 sabotaji |
| T-02-179 / T-02-181 (DoS va telefon sanash) | `import_max_staff_rows = 200` | `test_roster_larger_than_the_limit_is_rejected` |
| T-02-180 (ommaviy amalning izsizligi) | har hisob + yig'ma audit yozuvi | `test_audit_records_each_account_and_the_bulk_import` |
| T-02-182 (eski fayl parolni tiklashi) | D-15 skip | `test_reimport_does_not_reset_passwords` + S2 sabotaji |
| T-02-183 (cross-tenant a'zolik) | `market_id` faqat `_market_id(principal)` dan; matritsa filleri | `test_import_into_market_a_leaves_market_b_untouched` + tenancy matritsasi |
| T-02-184 (formula injection) | yagona yozish yo'li `_write_text()` | `test_staff_role_with_a_formula_prefix_is_escaped` |
| T-02-186 (filler yolg'on qizarishi) | har chaqiruvda unikal telefon | S3 sabotaji |
| T-02-SC (paket o'rnatish) | yangi paket yo'q | `git diff` `uv.lock` / `package-lock.json` bo'sh |

## Keyingi qadam uchun eslatmalar

- `POST /users` (bittalab) va `POST /imports/staff` (ommaviy) ikkalasi ham qoladi — birinchisi «yangi kassir ishga keldi», ikkinchisi «bozor ochilyapti» holati uchun.
- Xodim hisobi yaratilgandan keyin unga TELEGRAM orqali xabar berish yo'li YO'Q (7-faza bot mavzusi) — bugun parolni admin qo'lda yetkazadi va bu ROADMAP self-service qoidasiga zid emas (ro'yxatni admin bergan, hisoblarni tizim yaratgan).
- `vendors` shabloni endi to'g'ri namunaviy telefon bilan chiqadi, lekin uning uchidan-uchiga aylanma testi HAMON yo'q (faqat `stalls` va `staff` da bor) — 3-fazada qo'shish arzon.
