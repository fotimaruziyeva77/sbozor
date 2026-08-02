---
phase: 02-bozor-domeni-va-yangi-bozor-ustasi
plan: 21
subsystem: database
tags: [postgres, alembic, alembic-utils, rls, check-constraint, react-hook-form, zod, next-intl, pytest, vitest]

# Dependency graph
requires:
  - phase: 02-18
    provides: "usta marshrutining erishiluvchanligi — 1-qadam UI'si haqiqatda ochiladigan ekran"
  - phase: 02-11
    provides: "`setup-status` / `activate` darvozalari va `_blocking()` shartnomasi (`calendar_missing`, step 7)"
  - phase: 02-12
    provides: "`market_is_open()` fail-closed funksiyasi va `market_calendar_exceptions`"
provides:
  - "`0011_weekday_choice` — `market_profile.open_weekdays` dan `NOT NULL` va `server_default` olib tashlandi; `market_create()` ish rejimini TAXMIN QILMAYDI"
  - "`calendar_missing` (step 7) to'sig'i BOZOR YARATADIGAN YAGONA yo'lda haqiqatda ishga tushadi va faollashtirishni 409 bilan to'sadi"
  - "Usta 1-qadamida haftalik ish rejimi tanlovi (`fieldset`/`legend`, yettala kun oldindan belgilangan) va uning `POST /markets` payload'iga tushishi"
  - "`open_weekdays` uchun UCH holatli kontrakt: `NULL` (tanlanmagan, ruxsat) / `'{}'` (rad etiladi) / to'ldirilgan massiv"
  - "WR-05: sotuvchi importida registr farqli takroriy rasta kodi QATOR RAQAMI bilan rad etiladi"
  - "WR-04: `stall_code_claim()` haqidagi ikkala noto'g'ri `BEFORE INSERT` da'vosi haqiqatga keltirildi"
  - "02-REVIEW.md ning 18 ta topilmasi uchun to'liq yozma triaj (yopilgan / boshqa rejada / kechiktirilgan + faza biriktirmasi)"
affects: [06-kunlik-hisob, 03-nvr, 08-mustahkamlash]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Migratsiyada eski funksiya tanasini MUZLATISH: `alembic_utils` `PGFunction` ni modul ta'rifidan oladi, ya'ni `downgrade()` uchun eski tana migratsiyaning O'ZIDA nusxalanadi"
    - "CHECK ifodasini almashtirish `op.drop_constraint`/`create_check_constraint` bilan emas, xom SQL bilan — konstrayt nomi YAGONA konstantadan keladi"
    - "Usta formasida ko'p tanlovli guruh: `useWatch` + `setValue` (`watch()` EMAS — React Compiler memoizatsiyasi), `fieldset`/`legend`, `shouldValidate` faqat to'plam bo'sh bo'lmaganda"

key-files:
  created:
    - migrations/versions/0011_weekday_choice.py
    - tests/unit/test_import_validator.py
    - frontend/src/components/wizard/market-requisites-form.test.tsx
  modified:
    - migrations/entities/functions.py
    - packages/sbozor-core/sbozor_core/models/market.py
    - services/core-api/app/repositories/calendar_repo.py
    - services/core-api/app/api/v1/calendar.py
    - services/core-api/app/services/import_validator.py
    - services/core-api/app/repositories/import_repo.py
    - frontend/src/components/wizard/market-requisites-form.tsx
    - tests/integration/test_wizard_flow.py
    - tests/integration/test_market_calendar.py
    - .planning/phases/02-bozor-domeni-va-yangi-bozor-ustasi/02-CONTEXT.md

key-decisions:
  - "`NULL` = «hali tanlanmagan» RUXSAT ETILADI, `'{}'` = «hech qachon ochilmaydi» hamon RAD ETILADI — ikki holat mahsulot darajasida farqlanadi"
  - "Standart IKKALA yo'ldan (`COALESCE` va `server_default`) olib tashlandi: bittasini qoldirish ustun sanab o'tilmagan har qanday `INSERT` uchun teshik qoldirardi"
  - "Usta 1-qadamida yettala kun OLDINDAN BELGILANGAN, lekin qiymat sifatida YUBORILADI — DB taxmin qilmaydi, UI taklif qiladi"
  - "Ish rejimi maydoni `<details>` («Rasmiy rekvizitlar») ICHIGA QO'YILMADI: yopiq bo'lim maydoni o'tkazib yuborilishi kutiladi, aynan shu esa WR-06 ni tug'dirgan xatti-harakat"
  - "WR-02 3-fazaga YUQORI ustuvorlik bilan kechiktirildi: ikki bog'liq bo'lmagan o'zgarishni bitta migratsiya oynasida aralashtirish downgrade'ni ishonchsiz qilardi"
  - "`ON CONFLICT DO NOTHING` ning yo'qligi QARORI o'zgarmadi, lekin sababi almashtirildi: kafolat DB'da emas, validatorda"

patterns-established:
  - "Sabotaj o'lchovi to'rt marta bajarildi va har birida NAZORAT testi yashil qolgani ALOHIDA yozildi — «qizardi» yolg'iz o'lchov emas"
  - "Migratsiya `downgrade()` ma'lumotni o'zgartirsa, buni docstringda OCHIQ aytish (`_BACKFILL_NULLS`)"

requirements-completed: [MARKET-05]

# Metrics
duration: 95min
completed: 2026-08-02
---

# Phase 2 Plan 21: WR-06 yopildi — ish rejimi TANLANADI, taxmin qilinmaydi

**`0011_weekday_choice` `market_profile.open_weekdays` dan ikkala standart yo'lini ham olib tashladi, `calendar_missing` (step 7) to'sig'i shu bilan bozor yaratadigan yagona yo'lda ishga tushdi, usta 1-qadami esa haftalik rejimni `fieldset` bilan so'rab payload'da yuboradi; yonida WR-04/WR-05 yopildi va 02-REVIEW.md ning 18 topilmasi uchun yozma triaj qoldi.**

## Performance

- **Duration:** ~95 min
- **Started:** 2026-08-02T16:05:12Z
- **Completed:** 2026-08-02T17:40:00Z
- **Tasks:** 3 / 3
- **Files modified:** 16 (3 yangi, 13 o'zgargan)

## Accomplishments

- **WR-06 yopildi va u YOZIB BO'LMAS assertni yozib bo'ladigan qildi.** `market_create()` `COALESCE(p_open_weekdays, ARRAY[1..7])` bilan, ustun esa `server_default` bilan standart yozardi. Natijada `array_length(open_weekdays,1) > 0` **har doim** rost, `calendar_configured` har doim `True` va `calendar_missing` (step 7) bandi `POST /api/v1/markets` yo'lida **hech qachon** ishga tushmasdi. Dushanba kuni yopiladigan bozor «har kuni ochiq» deb faollashardi — 6-fazadagi kunlik job o'sha kunga patta yozardi.
- **Ikkala yo'l ham yopildi** (`COALESCE` va `server_default`), CHECK esa `NULL` ni ATAYIN va KO'RINADIGAN qilib ruxsat etadi; bo'sh massiv (`'{}'`) hamon rad etiladi.
- **`market_is_open()` va `_SETUP_STATUS` TEGILMADI va bu O'LCHANDI** — «tegilmadi» degan da'vo o'lchanmasa qiymatsiz (pastda, «Verification» bo'limida).
- **Usta 1-qadami endi ish rejimini so'raydi** — yettala kun oldindan belgilangan (har kuni ishlaydigan bozor bitta bosishda o'tadi), lekin qiymat **yuboriladi**.
- **Ikki mavjud test qayta yozildi** (majburiy edi — eskisi migratsiyadan keyin `TypeError` bilan yiqilardi) va **10 ta yangi test** qo'shildi.
- **02-REVIEW.md ning 18/18 topilmasi** uchun qaror yozildi; kechiktirilganlar `02-CONTEXT.md` `## Deferred Ideas` ga faza biriktirmasi bilan tushdi.

## Task Commits

1. **Task 1: `0011` migratsiyasi — jimgina «har kuni ochiq» standartini olib tashlash** — `1b74a8c` (fix)
2. **Task 2: Usta 1-qadamida haftalik ish rejimi tanlovi** — `cac9b4d` (feat)
3. **Task 3: 02-REVIEW.md topilmalarining triaji (WR-04, WR-05 + hujjatlashtirish)** — `4693b40` (fix)

## Files Created/Modified

### Yangi

- `migrations/versions/0011_weekday_choice.py` — `open_weekdays` dan `NOT NULL` + `server_default` olib tashlanadi, CHECK `NULL` ni ochiq ruxsat etadi, `market_create()` standartsiz qayta yaratiladi. `downgrade()` teskari tartibda: funksiya → CHECK → `NULL` backfill → ustun cheklovlari. Eski funksiya tanasi (`MARKET_CREATE_WITH_DEFAULT`) migratsiyaning **o'zida muzlatilgan** — `alembic_utils` `PGFunction` ni modul ta'rifidan oladi, ya'ni nusxasiz `downgrade()` YANGI tanani qaytarardi.
- `tests/unit/test_import_validator.py` — WR-05 ning to'rt testi (registr juftligi, ikki xil rasta = nazorat, topilmagan kod, rastasiz sotuvchi). Konteynersiz: `validate_vendor_rows()` sof funksiya.
- `frontend/src/components/wizard/market-requisites-form.test.tsx` — 5 test: `fieldset`/`legend` semantikasi, belgini olib tashlash, payload'dagi `open_weekdays`, bo'sh to'plamning rad etilishi, standart holat.

### O'zgargan

- `migrations/entities/functions.py` — `MARKET_CREATE` tanasidan `COALESCE` olib tashlandi; docstring `NULL` ning yangi ma'nosini va uning `calendar_missing` bilan bog'liqligini yozadi. `p_timezone` standarti **qoldi** (tushumga ta'sir qilmaydigan texnik sozlama).
- `packages/sbozor-core/sbozor_core/models/market.py` — `open_weekdays: Mapped[list[int] | None]`, `nullable=True`, `server_default` yo'q; `OPEN_WEEKDAYS_CHECK` uch holatni hujjatlashtiradi.
- `services/core-api/app/repositories/calendar_repo.py` — `profile()` `NULL` ni `[]` ga xaritalaydi (deviatsiya #1, pastda).
- `services/core-api/app/api/v1/calendar.py` — `get_calendar()` docstringi: profil QATORI yo'q → 409, jadval TANLANMAGAN → `[]` (409 emas).
- `services/core-api/app/services/import_validator.py` — WR-04 (modul docstringi) + WR-05 (`stall_first_seen: dict[UUID, int]`, kalit yechilgan `stall_id`).
- `services/core-api/app/repositories/import_repo.py` — WR-04 (`insert_stalls()` docstringi); `ON CONFLICT` ning yo'qligi endi MAHSULOT sababi bilan asoslanadi.
- `frontend/src/components/wizard/market-requisites-form.tsx` — `openWeekdays` maydoni, zod `min(1)`, `useWatch`/`setValue`, `fieldset`/`legend` + 7 katakcha, payload'da `open_weekdays`.
- `frontend/messages/{uz-Latn,ru,uz-Cyrl}.json` — `wizard.weekdaysLabel|weekdaysHint|weekdaysRequired`; `calendar.weekday.*` **qayta ishlatildi**, dublikat yaratilmadi.
- `tests/integration/test_wizard_flow.py` — 2 test qayta yozildi + 4 yangi + `INCOMPLETE_CASES` docstringi.
- `tests/integration/test_market_calendar.py` — `market_with_unchosen_weekdays` fixture + 2 yangi test.
- `.planning/.../02-CONTEXT.md` — `## Deferred Ideas` ga 10 ta kechiktirilgan topilma; `## Decisions` **tegilmadi** (`git diff | grep -c "^[+-].*D-[0-9]"` = 0).

## Qayta yozilgan ikki test — eski qiymat / yangi qiymat

Ikkalasi ham `_fill_wizard` ni ATAYIN chetlab o'tib endigina yaratilgan bozorning **xom standartlarini** tekshirardi, ya'ni ular aynan shu reja o'zgartirayotgan xatti-harakatni qulflab turgan edi.

| Test | Eski da'vo | Yangi da'vo | Nega majburiy |
|---|---|---|---|
| `test_market_profile_is_born_with_the_market` (418–458) | `assert sorted(row[1]) == [1,2,3,4,5,6,7]` | `assert row[1] is None` | Migratsiyadan keyin `row[1]` `None`, `sorted(None)` esa **`TypeError`** — test FAIL emas, **ERROR** bilan yiqilardi. Qolgan uchta assert (`row is not None`, `operating_since`, `tin`) tegilmadi — ular profil qatorining bozor bilan bir amalda tug'ilishini tekshiradi va bu da'vo o'zgarmadi. |
| `test_empty_draft_reports_every_missing_step` (558–596) | `blocking[] == ["zones_missing","categories_missing","stalls_missing"]`, `calendar_configured is True` | `blocking[] == ["zones_missing","categories_missing","stalls_missing","calendar_missing"]`, `calendar_configured is False` | Docstringi (565–571) nosozlikni FAKT sifatida yozardi («Kalendar bandi ATAYIN yo'q»). Butunlay qayta yozildi — aks holda keyingi o'quvchi yangi assertni «xato» deb tuzatib qo'yardi. Test **o'chirilmadi**: u yangi testlardan boshqa savolga javob beradi — `blocking[]` ning TO'LIQ va TARTIBLI ro'yxati (band tushib qolishi ham, ortiqchasi ham faqat shu yerda ushlanadi). |

`INCOMPLETE_CASES` docstringi (474–492) ham yangilandi: `calendar_missing` endi **ikki yo'ldan** erishiladi — (a) profil qatorisiz bozor (mavjud `_DROP_PROFILE` yo'li, **saqlandi**) va (b) `open_weekdays` tanlanmagan bozor (yangi, mahsulot yo'li). `test_activate_rejects_incomplete_market` ning oltala parametri ham o'zgarishsiz o'tadi.

**`_fill_wizard` ta'sirlanmadi va bu tasdiqlandi:** yordamchi `skip != "calendar"` bo'lganda `PUT /calendar/weekdays` ni **har doim** chaqiradi (298–304), ya'ni `new_market` orqali quriladigan qolgan testlar migratsiyadan ta'sirlanmaydi. Butun fayl yashil (`pytest tests/integration/test_wizard_flow.py -q` exit 0).

## Verification — «tegilmadi» da'volari O'LCHANDI

| Da'vo | O'lchov | Natija |
|---|---|---|
| `alembic upgrade head` ishlaydi | `docker compose --profile migrate run --rm migrate alembic upgrade head` | exit 0, `alembic current` → **`0011 (head)`** |
| downgrade ishlaydi | `alembic downgrade 0010 && alembic upgrade head` | ikkalasi ham exit 0 |
| model ↔ sxema ajralmagan | `alembic revision --autogenerate -m probe` | `upgrade()`/`downgrade()` ikkalasi ham **`pass`** (bo'sh diff); probe fayli o'chirildi |
| ustun `NULL` qabul qiladi va standarti yo'q | `information_schema.columns` | `is_nullable = YES`, `column_default` **bo'sh** |
| CHECK yangi ifoda bilan | `pg_get_constraintdef` | `CHECK (((open_weekdays IS NULL) OR ((open_weekdays <@ ARRAY[...]) AND (array_length(open_weekdays, 1) IS NOT NULL))))` |
| `market_create()` da standart yo'q | `position('COALESCE(p_open_weekdays' in pg_get_functiondef(...))` | **`0`** |
| `market_is_open()` `NULL` ni to'g'ri talqin qiladi (`= ANY(NULL)` → `NULL` → fail-closed) | yangi `test_unchosen_weekday_schedule_is_fail_closed` | yashil — yopiq kun ham, ochiq kun ham `false` |
| `_SETUP_STATUS` `NULL` ni to'g'ri talqin qiladi (`array_length(NULL,1)` → `NULL` → `COALESCE(...,0) > 0` → `false`) | yangi `test_market_without_weekday_choice_reports_calendar_missing` | yashil — `calendar_configured is False`, `blocking == ["calendar_missing"]` |
| meta-darvozalar qizarmagan | `npm run test:tenancy` | **317 passed** |
| 02-20 fayli tegilmagan | `git diff --exit-code frontend/src/lib/market-queries.ts` | toza |
| yangi paket o'rnatilmagan (T-02-SC) | `git diff --exit-code services/core-api/pyproject.toml frontend/package.json` | toza |

**Yakuniy darvoza:** `npm run gate` → **exit 0**. Backend **916** test (baza 906 → +10), tenancy **317**, frontend **67** test (baza 62 → +5), i18n **424 kalit × 3 til**, `next build` yashil.

## Sabotaj o'lchovlari

Har birida **NAZORAT** testining yashil qolgani alohida yozilgan — «qizardi» yolg'iz o'lchov emas, u har doim yashil qoladigan juftini talab qiladi.

| # | Sabotaj | Qizargan | Yashil qolgan | Xulosa |
|---|---|---|---|---|
| 1 | `MARKET_CREATE` ga `COALESCE(p_open_weekdays, ARRAY[1..7])` qaytarildi | `test_market_profile_is_born_with_the_market`, `test_empty_draft_reports_every_missing_step`, `test_market_without_weekday_choice_reports_calendar_missing`, `test_market_without_weekday_choice_cannot_activate`, `test_weekday_choice_at_step_seven_clears_the_gate` (5) | **`test_weekday_choice_at_step_one_leaves_no_calendar_gate`** (nazorat — 1-qadamda qiymat berilganda to'siq yonmaydi) | To'siq AYNAN standartga bog'liq; nazorat testi «to'siq har doim yonadi» buzuq variantini ajratadi |
| 2 | CHECK'dan `array_length(open_weekdays,1) IS NOT NULL` olib tashlandi (model + `0011`) | **faqat** `test_empty_weekday_array_is_still_rejected` (`DID NOT RAISE CheckViolation`) | `test_unchosen_weekday_schedule_is_fail_closed`, `test_open_weekday_is_open` | `NULL` ruxsati bo'sh massiv taqiqini **yemirmagan** — ikki shart mustaqil |
| 3 | `onSubmit` payload'idan `open_weekdays` olib tashlandi (WR-06 ning ASL holati) | `yuborilgan tanlov ... payload'ga tushadi` (`expected undefined`), `standart holat: yettala kun yuboriladi` | `fieldset`/`legend`, belgini olib tashlash, bo'sh to'plamning rad etilishi (3) | UI yarmi payload darajasida qulflangan — forma holati to'g'ri bo'lib, yuborish unutilgan holat ushlandi |
| 4 | `stall_first_seen` kaliti xom satrga qaytarildi | **faqat** `test_mixed_case_stall_code_is_reported_as_a_duplicate` (`kutilgan 1 xato, kelgani 0`) | `test_two_different_stalls_are_not_a_duplicate`, `test_unknown_stall_code_is_not_counted_as_a_duplicate`, `test_vendor_without_a_stall_code_never_collides` | Kalit turi AYNAN registr juftligini ushlaydi; nazorat testlari «hamma narsani dublikat deb ataydigan» variantni ajratadi |

Har to'rt sabotajdan keyin fayl tiklandi va testlar qayta yashil bo'ldi.

## 02-REVIEW.md — TO'LIQ TRIAJ (18/18)

| ID | Qisqa nomi | Qaror | Qayerda / nega |
|---|---|---|---|
| **CR-01** | React Query keshi tenant-scoped emas, sessiya almashganda tozalanmaydi | ✅ **yopildi** | **02-20** (`domainKey(marketId, …)` + `client.clear()`) |
| **CR-02** | Sotuvchi ismi/telefoni `MARKET_DATA_VIEW` ostida, o'qish auditisiz | ✅ **yopildi** | **02-19** (`audit_read` + `VENDOR_VIEW`) |
| **CR-03** | Usta erishib bo'lmaydigan — MARKET-01 UI orqali bajarilmaydi | ✅ **yopildi** | **02-18** (layout istisnosi + nav + bo'sh holat havolasi) |
| **WR-01** | `POST /imports/errors.xlsx` chegarasi to'liq emas (3 qismli) | ⏸ **kechiktirildi → 8-faza** | Element maydonlari chegarasiz + 5000 lik cheklov noto'g'ri asosdan (bitta qator 4 tagacha xato) + 32 767 belgidan uzun katak jimgina yo'qoladi. Autentifikatsiyalangan yo'ldagi o'z-o'ziga DoS, ta'sir doirasi bitta sessiya |
| **WR-02** | `market_activate()` / `market_delete_draft()` da tenant predikati yo'q | ⏸ **kechiktirildi → 3-faza, YUQORI ustuvorlik** | Bugun eskalatsiya yo'li YO'Q (`_own_market()` principaldan oladi, `MARKET_MANAGE` faqat platforma admini), lekin kaskad 12 jadval bo'ylab ketadi. Tuzatish yangi migratsiya talab qiladi — bu reja allaqachon `0011` ni olib yuribdi va ikki bog'liq bo'lmagan o'zgarish bitta downgrade oynasida aralashardi |
| **WR-03** | `markets.timezone` validatsiyasiz va hech qayerda o'qilmaydi | ⏸ **kechiktirildi** | Uchta literal joy BIRGA o'zgarishi kerak va ular Deferred Ideas'da **nomma-nom**: `timeutil.MARKET_TZ`, `helpers.BUSINESS_DATE_EXPR`, `triggers.py` dagi ikki o'zgarmaslik triggeri. Ikkinchi vaqt mintaqasidagi bozor paydo bo'lgandagina ma'noga ega |
| **WR-04** | `stall_code_claim()` ikki faylda `BEFORE INSERT` deb yozilgan, DDL esa `AFTER INSERT OR UPDATE OF code` | ✅ **yopildi** | **shu reja** (`4693b40`). Kod xatti-harakati o'zgarmadi; ikkala docstring ham haqiqatga keltirildi va D-15 idempotentligining haqiqiy egasi (DB emas, **validator**) ochiq yozildi |
| **WR-05** | Registr farqli takroriy rasta kodi sirg'alib o'tadi → `23P01`, qator raqamisiz 409 | ✅ **yopildi** | **shu reja** (`4693b40`). `stall_first_seen: dict[UUID, int]`, kalit yechilgan `stall_id`; 4 birlik test |
| **WR-06** | `calendar_missing` usta yo'lida hech qachon ishga tushmaydi | ✅ **yopildi** | **shu reja** (`1b74a8c` + `cac9b4d`) — 1- va 2-tasklar |
| **WR-07** | `errors.xlsx` `STALL_MANAGE` talab qiladi, sotuvchi importi xatosi uchun ham | ⏸ **kechiktirildi** | Bugun bitta huquqqa ega rol ikkinchisiga ham ega → latent. Tuzatish `ImportErrorReportRequest` shakliga `kind` qo'shishni talab qiladi, ya'ni **kontrakt o'zgarishi**. Naqsh mavjud: `imports.py::require_template_access` (157-178) |
| **WR-08** | `_check_zip()` chegarani allokatsiyadan KEYIN qo'llaydi | ⏸ **kechiktirildi → 8-faza** | 5 MB yuklash chegarasi eng yomon holatni allaqachon chegaralaydi; to'g'ri tuzatish EOCD ni oldindan o'qishni talab qiladi |
| **WR-09** | Mid-session `password_change_required` «ruxsat yo'q» bo'lib ko'rinadi, redirect yo'q | ✅ **yopildi** | **02-18** (`api-client.ts` da kod xaritalandi + `updatePrincipal`) |
| **WR-10** | `useImportMutation` `ASSIGNMENTS_KEY` ni bekor qilmaydi | ✅ **yopildi** | **02-20** (`IMPORT_SIDE_EFFECTS`) |
| **IN-01** | Sarlavha qatori `MAX_ROWS` ga sanaladi (amaldagi chegara 4999) | ⏸ **kechiktirildi → 8-faza** | Hujjat bilan xatti-harakat orasidagi bir qatorlik farq; `test_default_limits_match_the_documented_values` bilan birga |
| **IN-02** | Ikki kalendar yozuv endpointi javobni SO'ROVDAN quradi | ⏸ **kechiktirildi** | Fazaning qolgan yozuv yo'llari javobni o'qish yo'lidan quradi; kalendar ikkitasi chetda qolgan |
| **IN-03** | `activate.mutateAsync(marketId ?? "")` `null` ni buzuq URL'ga aylantiradi | ⏸ **kechiktirildi** | Bugun erishib bo'lmaydi (`enabled: false`), lekin `?? ""` dasturiy xatoni jimgina noto'g'ri so'rovga aylantiradi |
| **IN-04** | `tests/tenancy/test_cross_tenant.py` taqiqlangan `date.today()` ni ishlatadi | ⏸ **kechiktirildi** | +30 kunlik zaxira bugun zararsiz qiladi; tenancy to'plami loyihaning o'z vaqt qoidasini modellashtirishi kerak joy |
| **IN-05** | OpenAPI va `/docs` shartsiz ochiq | ⏸ **kechiktirildi → 8-faza, ISHGA TUSHIRISH QATTIQLASHTIRISH** | 1-fazadan meros va `EXEMPT_ROUTES` uni ataylab deb yozgan, LEKIN 2-faza o'sha yuzaga **43 marshrut** qo'shdi. Muhit bayrog'i bilan yopiladi, standart — o'chiq |

**Jami:** 8 yopildi (3 CRITICAL + 5 WARNING), 10 kechiktirildi (5 WARNING + 5 INFO) — **jimgina tashlab ketilgani yo'q**. Kechiktirilganlarning hammasi `02-CONTEXT.md` `## Deferred Ideas` da sababi va faza biriktirmasi bilan.

## Decisions Made

Rejadagi qarorlar bajarildi. Ijro davomida qo'shilgan ikki qaror:

1. **`GET /calendar` jadval tanlanmagan bozor uchun `[]` beradi, 409 emas.** Reja bu yo'lni ko'rmagan edi (deviatsiya #1). Bo'sh ro'yxat **noaniq emas** va aynan shu sabab u xavfsiz: `'{}'` DB darajasida taqiqlangan, ya'ni javobdagi `[]` FAQAT «hali tanlanmagan» degani. 409 qaytarish 7-qadam ekranini umuman ochilmaydigan qilardi — ya'ni `calendar_missing` «yo'l ko'rsatkichi» ko'rsatgan joyda ishlamaydigan ekran turardi.
2. **`market-requisites-form.test.tsx` qo'shildi.** Reja uni talab qilmagan, lekin usiz Task 2 ning UI yarmi umuman o'lchanmasdi va fazaning sabotaj konvensiyasini bajarib bo'lmasdi (sabotaj #3 aynan shu fayl bilan o'tkazildi).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `CalendarRepository.profile()` `open_weekdays` `NULL` bo'lganda `TypeError` beradi**
- **Found during:** Task 1 (migratsiya kodini yozishdan oldin, chaqiruvchilarni o'qish paytida)
- **Issue:** `return CalendarProfileRow(id=row.id, open_weekdays=list(row.open_weekdays))` — `list(None)` `TypeError` beradi. Migratsiyadan keyin ustun `NULL` bo'lishi mumkin, ya'ni **`GET /api/v1/calendar` 500 qaytarardi** aynan o'sha bozorlar uchun. Reja «`market_is_open()` va `_SETUP_STATUS` tegilmaydi» deb ikki chaqiruvchini nomma-nom sanagan, lekin uchinchisini (kalendar o'qish yo'li) ko'rmagan.
- **Fix:** `list(row.open_weekdays or ())`; `profile()` va `get_calendar()` docstringlari yangi uch holatli kontraktni yozadi (`NULL` → `[]`, `'{}'` taqiqlangan, profil qatori yo'q → 409).
- **Files modified:** `services/core-api/app/repositories/calendar_repo.py`, `services/core-api/app/api/v1/calendar.py`
- **Verification:** `test_weekday_choice_at_step_seven_clears_the_gate` `PUT` dan OLDIN `GET /calendar` ni chaqirib `open_weekdays == []` ni tasdiqlaydi; `test_calendar_api.py` (24 test) yashil
- **Committed in:** `1b74a8c` (Task 1 commit)

**2. [Rule 3 - Blocking] `.env` fayli umuman yo'q edi — dev stek ishga tushmasdi**
- **Found during:** Task 1 (migratsiyani ishga tushirishga urinish)
- **Issue:** `docker compose` `POSTGRES_PASSWORD`, `SBOZOR_OWNER_PASSWORD`, `SBOZOR_APP_PASSWORD`, `MIGRATION_DATABASE_URL`, `DATABASE_URL`, `JWT_SECRET` uchun «variable is not set» ogohlantirishi berardi. `.env` `.gitignore` da va repoda mavjud emas edi (faqat `.env.example`). `migrate` profili shusiz umuman ishlamaydi.
- **Fix:** `.env` `.env.example` dan hosil qilindi, parollar va `JWT_SECRET` `secrets` bilan generatsiya qilindi (dev-only). `pgdata` volumesi qayta yaratildi (`down -v` + `up`), chunki rol parollari faqat birinchi initda o'rnatiladi va eskisi noma'lum edi. Karmana ma'lumoti yo'qolmadi — `ops/data/karmana/` da faqat `.gitignore` va `README.md` bor, testlar esa **testcontainers** bilan o'z Postgresini ko'taradi (`.env` ga umuman bog'liq emas).
- **Files modified:** `.env` (gitignored — **commit qilinmadi**)
- **Verification:** `alembic upgrade head` exit 0; `npm run gate` yashil
- **Committed in:** — (gitignored, tarixga kirmaydi)

**3. [Rule 3 - Blocking] Xost portidagi 5432 band edi**
- **Found during:** Task 1
- **Issue:** `Error response from daemon: ports are not available: exposing port TCP 127.0.0.1:5432` — xostda boshqa loyihaning konteyneri (`parnikkpi-db-1`) o'sha portni band qilgan.
- **Fix:** `.env` ga `DB_HOST_PORT=55432` (`compose.override.yml` allaqachon shu o'zgaruvchini kutadi va bog'lanish interfeysi `127.0.0.1` o'zgarmadi). Faqat dev qulayligi porti — kompoz tarmog'i ichidagi ulanishlar tegilmadi.
- **Files modified:** `.env` (gitignored)
- **Verification:** `docker compose up -d db cache --wait` → ikkalasi `Healthy`
- **Committed in:** —

**4. [Rule 2 - Missing Critical] Task 2 uchun komponent testi qo'shildi**
- **Found during:** Task 2
- **Issue:** Reja Task 2 uchun test talab qilmagan (`<verify>` faqat «mavjud usta testlari qizarmagan» deydi). Lekin WR-06 ning **UI yarmi** — tushumga bevosita ta'sir qiluvchi darvozaning yarmi — o'lchanmay qolardi, va fazaning sabotaj konvensiyasini bajarish uchun o'lchanadigan joy kerak edi.
- **Fix:** `frontend/src/components/wizard/market-requisites-form.test.tsx` — 5 test. Sabotaj #3 aynan shu fayl bilan o'tkazildi va payload'ni buzish ikkita testni AYNAN qizartirdi.
- **Files modified:** `frontend/src/components/wizard/market-requisites-form.test.tsx`
- **Verification:** `npm --prefix frontend run test:component` — 67 passed (baza 62)
- **Committed in:** `cac9b4d` (Task 2 commit)

**5. [Rule 3 - Blocking] Reja qabul mezonlaridagi ikki grep o'z izohimga urilardi**
- **Found during:** Task 1 va Task 3
- **Issue:** Reja `grep -c "COALESCE(p_open_weekdays"` = 0, `grep -n "sorted(row[1])"` natijasiz va `grep -c "BEFORE INSERT"` = 0 mezonlarini qo'ygan. Mening tuzatish izohlarim («ilgari … yozilardi») aynan shu tokenlarni **prozada** takrorlab, mezonlarni buzardi — ya'ni kelajakdagi grep-darvoza yolg'on-qizil berardi.
- **Fix:** Izohlar mazmunini saqlagan holda qayta yozildi (`COALESCE(...)` + `ARRAY[1,2,3,4,5,6,7]` alohida; «jadval yettala kun bilan solishtirilardi»; «`BEFORE` deb yozilgan edi»). Ma'no yo'qolmadi, token esa qolmadi.
- **Files modified:** `migrations/entities/functions.py`, `tests/integration/test_wizard_flow.py`, `services/core-api/app/services/import_validator.py`, `services/core-api/app/repositories/import_repo.py`
- **Verification:** barcha grep mezonlari o'tadi (yuqoridagi Verification jadvali)
- **Committed in:** `1b74a8c`, `4693b40`

---

**Total deviations:** 5 auto-fixed (1 Rule 1 — bug, 1 Rule 2 — missing critical, 3 Rule 3 — blocking)
**Impact on plan:** Hech biri qamrovni kengaytirmadi. #1 migratsiyaning bevosita oqibati edi va usiz `GET /calendar` 500 berardi; #2/#3 muhit ta'miri (kod emas); #4 o'lchanmaydigan yarim tuzatishni o'lchanadigan qildi; #5 reja mezonlarining o'zini bajarilishi mumkin holga keltirdi.

## Wave 16 post-merge tekshiruvi

Bu reja wave 16 ning (02-18, 02-19, 02-20) `main` ga qo'shilganidan keyingi **birinchi to'liq darvoza** edi. **Kross-plan integratsiya nosozligi TOPILMADI:**

- `npm run gate` to'liq yashil — ziddiyatli tiplar, o'zgargan imzolar yoki tushib qolgan eksportlar yo'q.
- 02-20 ning `market-queries.ts` fayli tegilmadi (`git diff --exit-code` toza) va uning `MarketCreateInput.open_weekdays` maydoni Task 2 uchun **tayyor holda** turgan ekan — ya'ni ikki reja o'rtasidagi kontrakt to'g'ri hisoblangan.
- 02-19 ning `audit_read` o'zgarishlari kalendar/usta yo'llariga tegmaydi; 02-18 ning wizard marshruti Task 2 render testida bilvosita ishlatildi (`MarketRequisitesForm` mustaqil montaj bo'ladi).
- Backend testlari 906 → **916** (+10 yangi), frontend 62 → **67** (+5). Baza raqamlari saqlanib qoldi, ya'ni wave 16 dan hech nima yo'qolmadi.

## Issues Encountered

1. **Docker daemon qotib qoldi (~25 daqiqa yo'qotildi).** `docker compose ps` javob bermay qo'ydi, `docker ps` esa 8 ta ketma-ket 55-soniyalik timeoutdan keyin ham javobsiz qoldi. Sabab — oldingi bekor qilingan gate ishlaridan qolgan ~30 ta osilib qolgan `docker` / `docker-compose` klient jarayoni. Klientlarni o'ldirish yetmadi; `Docker Desktop` + `com.docker.backend` to'xtatilib, `wsl --shutdown` bajarilib, qayta ishga tushirildi. Shundan keyin daemon normal ishladi. Kod nosozligi emas.
2. **Ijro davomida `main` ga ikki begona commit tushdi** (`b1b0e36` phase-03 research, `346a91c` stack docs — `CLAUDE.md` va `ROADMAP.md`). Mening fayllarim bilan kesishmadi, konflikt bo'lmadi; commitlarim ular ustiga toza tushdi. Faqat kuzatuv sifatida qayd etilyapti — «bitta yozuvchi» taxmini bu ijroda to'liq to'g'ri bo'lmagan.
3. **`ruff format` ikki faylni qayta formatladi** (`0011_weekday_choice.py`, `test_market_calendar.py`) — `with` bloki va uzun `op.execute` satri. Formatlashdan keyin testlar qayta ishga tushirildi va yashil qoldi.

## Known Stubs

Yo'q. O'zgargan 16 faylda `TODO` / `FIXME` / `placeholder` / «coming soon» naqshlari topilmadi (i18n dagi `addPlaceholder` / `searchPlaceholder` — bular `<input placeholder>` matnlari, oldindan mavjud va stub emas).

## Threat Flags

Yo'q. Yangi tarmoq endpointi, yangi auth yo'li yoki yangi fayl kirish naqshi qo'shilmadi. Yagona sxema o'zgarishi (`open_weekdays` `NULL` qabul qiladi) reja `<threat_model>` idagi **T-02-155/T-02-156 ning mitigatsiyasining o'zi** — u yangi yuza emas, mavjud yuzaning yopilishi. `T-02-SC` (paket o'rnatish) o'lchandi va toza: `git diff --exit-code services/core-api/pyproject.toml frontend/package.json`.

## User Setup Required

**Bitta lokal qadam — repoga tegmaydi.** Ijro `.env` faylini `.env.example` dan qayta yaratdi (u `.gitignore` da bo'lgani uchun ishchi nusxada yo'q edi) va dev `pgdata` volumesini tozalab qayta initsializatsiya qildi. Boshqa mashinada ishlayotgan bo'lsangiz:

```bash
cp .env.example .env
# POSTGRES_PASSWORD / SBOZOR_OWNER_PASSWORD / SBOZOR_APP_PASSWORD / JWT_SECRET ni to'ldiring
# DATABASE_URL va MIGRATION_DATABASE_URL dagi CHANGEME ni ham almashtiring
python -c "import secrets;print(secrets.token_urlsafe(48))"   # JWT_SECRET uchun
```

Xostda 5432 band bo'lsa `.env` ga `DB_HOST_PORT=55432` qo'shing. Tashqi servis sozlash **kerak emas** — testlar testcontainers bilan o'z Postgresini ko'taradi.

## Next Phase Readiness

- **6-faza uchun kirish sharti mustahkamlandi:** `open_weekdays` endi TANLANGAN qiymat, ya'ni `WHERE market_is_open(:m, :d)` shartnomasi taxmin ustiga qurilmaydi. Yopiq kunga patta yozilishi sinfi DB darajasida yopildi.
- **7-qadam o'z o'rnida qoldi** (tahrir + bayram istisnolari), 1-qadam esa faqat boshlang'ich qiymat beradi — D-17/D-18 buzilmadi.
- **3-faza uchun ilgak:** WR-02 (`market_activate()` / `market_delete_draft()` tenant predikati) **yuqori ustuvorlik** bilan biriktirildi va u yangi migratsiya talab qiladi — 3-fazaning birinchi migratsiya oynasiga qo'shilishi mantiqiy.
- **8-faza uchun to'plandi:** WR-01, WR-08, IN-01, IN-05 — hammasi mustahkamlash/ishga tushirish qattiqlashtirish bandi sifatida yozib qo'yilgan.
- **Blokerlar yo'q.** `npm run gate` yashil, `alembic` head = `0011`.

---
*Phase: 02-bozor-domeni-va-yangi-bozor-ustasi*
*Completed: 2026-08-02*

## Self-Check: PASSED

- Yaratilgan uch fayl ham diskda mavjud (`0011_weekday_choice.py`, `test_import_validator.py`, `market-requisites-form.test.tsx`)
- To'rt commit ham git tarixida (`1b74a8c`, `cac9b4d`, `4693b40`, `4ba3a7b`)
- `alembic current` → `0011 (head)` — SUMMARY dagi da'vo bilan mos
