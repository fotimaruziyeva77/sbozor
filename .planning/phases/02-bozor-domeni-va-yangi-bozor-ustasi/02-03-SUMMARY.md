---
phase: 02-bozor-domeni-va-yangi-bozor-ustasi
plan: 03
subsystem: auth
tags: [postgres, alembic, pydantic, zod, next-intl, rbac, wcag, security-definer]

# Dependency graph
requires:
  - phase: 02-bozor-domeni-va-yangi-bozor-ustasi
    provides: "02-01 — `select-market` parol darvozasi + `is_platform_admin` ni DB'dan qayta o'qish (WR-02/WR-03); 02-02 — `ui/badge.tsx` va `frontend/messages/README.md` copy qoidalari"
  - phase: 01-poydevor-va-tenant-xavfsizligi
    provides: "`auth_memberships()` SECURITY DEFINER funksiyasi, `MarketRef` javob shakli, `market-picker.tsx`, `migrations/helpers.py`, tenancy meta-testlari"
provides:
  - "`auth_memberships(uuid)` qaytish to'plamida `is_active boolean` — a'zolik tarmog'ida bozor faolligi"
  - "`auth_repo.Membership.is_active` — BOZOR faolligi (foydalanuvchi faolligi emas)"
  - "`MarketRef.is_active` — MAJBURIY, standart qiymatsiz javob maydoni (login / select-market / refresh / auth-me)"
  - "`_visible_markets()` serverdagi filtrsiz — qoralama bozor ikkala tarmoqda ham ro'yxatga chiqadi"
  - "`_platform_admin_market()` qoralama bozorni ham qaytaradi — usta oqimi uchun tenant konteksti ochiladi"
  - "`marketRefSchema.is_active` + `setupStatusSchema` — 02-11 endpointi uchun kengayishga chidamli zod shakli"
  - "`auth.marketDraft` uchala tilda + `Qoralama` badge'i bozor tanlash ekranida"
  - "`tests/fixtures/auth_api.py::draft_market` — qoralama bozor seed'i (kelgusi rejalar uchun)"
  - "`0006_membership_active` — qaytish tipini o'zgartiruvchi migratsiya NAQSHI (DROP + GRANT tiklash)"
affects: [02-11, 02-16, 02-04, 02-05, 06-hisob-kitob]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Funksiya qaytish tipini o'zgartirish = xom `DROP` + `create_entity` + GRANT/REVOKE ni QAYTADAN qo'yish"
    - "Javob maydonining standart qiymati yo'qligi — manbani kengaytirishga majburlovchi vosita"
    - "Marshrut qarori server javobidan olinadi, bosilgan ro'yxat elementidan emas (ro'yxat eskirgan bo'lishi mumkin)"
    - "Kelgusi endpoint uchun MINIMAL zod sxemasi: faqat ishlatiladigan maydon majburiy, qolgani jimgina tashlanadi"

key-files:
  created:
    - migrations/versions/0006_membership_active.py
  modified:
    - migrations/entities/functions.py
    - services/core-api/app/repositories/auth_repo.py
    - services/core-api/app/schemas.py
    - services/core-api/app/api/v1/auth.py
    - frontend/src/lib/api-types.ts
    - frontend/src/components/auth/market-picker.tsx
    - frontend/src/components/auth/market-picker.test.tsx
    - frontend/messages/uz-Latn.json
    - frontend/messages/ru.json
    - frontend/messages/uz-Cyrl.json
    - tests/fixtures/auth_api.py
    - tests/integration/test_auth_login.py
    - tests/integration/test_auth_refresh.py
    - tests/tenancy/test_meta.py

key-decisions:
  - "`_platform_admin_market()` dagi faollik sharti OLIB TASHLANDI — usiz ko'rinadigan qoralama bosilganda 403 berardi va usta oqimi tenant kontekstini umuman ocholmasdi (sabotaj bilan o'lchandi)"
  - "`MarketRef.is_active` standart qiymatsiz — `= True` unutilgan chaqiruvchida qoralamani jimgina 'faol' deb yorliqlagan bo'lardi"
  - "`/auth/me` so'rovi `is_active` ustunini ham o'qiydi — usta ichidagi sessiya o'zini faol bozor deb ko'rsatmasin"
  - "Marshrut qarori `session.market.is_active` dan, ro'yxat elementidan emas"
  - "Badge oldiga LITERAL bo'shliq (`{\" \"}`) qo'yildi — accname algoritmi inline elementlar orasiga bo'shliq qo'shmaydi"
  - "`setupStatusSchema` da faqat `step` majburiy — 02-11 javob shaklini kengaytirganda bu fayl o'zgarmaydi"

patterns-established:
  - "Pattern: qaytish tipi o'zgargan funksiya uchun `drop_entity` EMAS, xom `DROP` — imzo bir xil bo'lgani uchun `replaceable_entity` eski/yangi ta'rifni ajrata olmaydi"
  - "Pattern: imzo o'zgarmagan, faqat qaytish tipi o'zgargan funksiya `pg_get_function_result()` bilan alohida qulflanadi — mavjud darvozalarning BIRORTASI uni ko'rmaydi"
  - "Pattern: fail-safe navigatsiya (`?step=1`) — xavfsizlik chegarasi bo'lmagan joyda fail-closed EMAS"

requirements-completed: []

# Metrics
duration: 37min
completed: 2026-07-31
---

# Phase 2 Plan 03: Qoralama bozorni topiladigan qilish Summary

**`auth_memberships()` SQL funksiyasidan `market-picker.tsx` gacha bo'lgan olti bandli zanjir bajarildi: qoralama bozor endi bozor tanlash ekranida `Qoralama` belgisi bilan ko'rinadi, tanlanadi va uzilgan ustaning birinchi tugallanmagan qadamiga olib boradi.**

## Performance

- **Duration:** ~37 min
- **Started:** 2026-07-31T11:05Z
- **Completed:** 2026-07-31T11:42Z
- **Tasks:** 3/3
- **Files:** 15 (1 yaratildi, 14 o'zgartirildi), +791 / −46

## Accomplishments

- **Zanjirning oltala bandi birga bajarildi va tartib buzilmadi.** UI-SPEC §12.1.1 aniq ogohlantirgan edi: faqat frontend filtrini olib tashlash **hech narsani o'zgartirmaydi** — vazifa "bajarildi" deb yopiladi, oqim esa hamon ishlamaydi. Shuning uchun DB → repozitoriy → sxema → endpoint → zod → UI ketma-ketligi saqlandi.
- **Assimetriya yopildi.** Ilgari qoralama bozorni **a'zosi ko'rardi, uni yaratgan platforma admini esa yo'q** (`_visible_markets()` da filtr faqat bitta tarmoqda edi). Endi ikkala tarmoq ham bayroqni DB'dan uzatadi va hech bir joyda literal `True` yozilmaydi.
- **Ko'rinadigan, lekin o'lik element qolmadi.** `_platform_admin_market()` dagi faollik sharti aniqlandi va olib tashlandi — usiz reja o'zining `<done>` mezonini ("bosilganda ustaga olib boradi") bajara olmasdi. Nosozlik **o'lchandi**: shart qaytarilganda `test_platform_admin_can_select_a_draft_market` 403 bilan qizardi.
- **Migratsiya ikki tomonlama tekshirildi.** `alembic downgrade 0005 && alembic upgrade head` haqiqiy `postgres:18.4` konteynerida bajarildi; har qadamda qaytish tipi VA grant holati o'lchandi (`sbozor_app` → `EXECUTE true`, `PUBLIC` → `false`).
- **Nazorat holatlari har bir yangi da'vo uchun yozildi** — faol bozor `/dashboard` da qoladi, `setup-status` umuman chaqirilmaydi, a'zoligi bo'lmagan bozor admini qoralamani tanlay olmaydi (403).

## Task Commits

1. **Task 1: `auth_memberships()` qaytish tipi va `Membership.is_active`** — `eef6d6e` (feat)
2. **Task 2: `MarketRef.is_active` va serverdagi filtrni olib tashlash** — `54bb193` (feat)
3. **Task 3: zod kontrakti, `Qoralama` belgisi va ustaga qaytish** — `2b9405a` (feat)

## Files Created/Modified

**Yaratildi**
- `migrations/versions/0006_membership_active.py` — xom `DROP` + `create_entity(AUTH_MEMBERSHIPS)` + GRANT/REVOKE tiklash; `downgrade()` eski uch ustunli ta'rifni LITERAL tiklaydi. Docstringda `cannot change return type of existing function` xatosi va `drop_entity` nega ishlatilmagani yozilgan.

**Muhim o'zgarishlar**
- `migrations/entities/functions.py` — `AUTH_MEMBERSHIPS` ga `is_active boolean` + `m.is_active`; fayl docstringiga qaytish tipini o'zgartirish qoidasi.
- `services/core-api/app/repositories/auth_repo.py` — `Membership.is_active`; `memberships()` filtrlamaydi va sababi yozilgan.
- `services/core-api/app/schemas.py` — `MarketRef.is_active` majburiy, standart qiymatsiz (sababi docstringda).
- `services/core-api/app/api/v1/auth.py` — 8 ta `MarketRef` qurilish joyi manbadan bayroq oladi; `_visible_markets()` filtrsiz; `_platform_admin_market()` qoralamani ham qaytaradi; `/auth/me` so'rovi `is_active` ustunini o'qiydi.
- `frontend/src/lib/api-types.ts` — `marketRefSchema.is_active`; `marketListItemSchema` dagi takror olib tashlandi; `setupStatusSchema` qo'shildi.
- `frontend/src/components/auth/market-picker.tsx` — o'lik zaxira filtri olib tashlandi; `Badge tone="muted"`; `firstIncompleteStep()` (eng kichik `blocking[].step`, xatoda 1).
- `tests/fixtures/auth_api.py` — `draft_market()` context-manager seed'i (FK tartibida teardown).
- `tests/tenancy/test_meta.py` — `test_auth_memberships_returns_is_active`.

## Decisions Made

- **`_platform_admin_market()` sharti olib tashlandi (rejadan tashqari, pastda deviatsiya #1).** UI-SPEC X-1 "platforma admini qoralamani ALLAQACHON tanlay oladi" deb yozgan; kod esa buni qilmasdi. Ikki variant bor edi: kodни da'voga moslashtirish yoki da'voni tuzatib oqimni buzuq qoldirish. Birinchisi tanlandi — chunki ustaning 2–7-qadamlari tenant-scoped jadvallarga yozadi, ya'ni `app.market_id` ni qoralama bozorga o'rnatishning boshqa yo'li YO'Q.
- **`/auth/me` ham `is_active` ni qaytaradi.** Reja `:796` ni "markets qatoridan" deb belgilagan, lekin so'rovda ustun yo'q edi. Uni `True` deb taxmin qilish usta ichidagi sessiyani "faol bozor" deb ko'rsatardi.
- **Marshrut qarori server javobidan.** `session.market.is_active` ishlatiladi, bosilgan ro'yxat elementi emas: ro'yxat login paytida olingan va bozor shu orada faollashtirilgan bo'lsa foydalanuvchi tugallangan ustaga qaytib tushardi.
- **Badge oldiga literal bo'shliq.** `gap-2` faqat VIZUAL; accname algoritmi qo'shni inline elementlar orasiga bo'shliq qo'shmaydi va nom `"<nom><belgi>"` bo'lib qo'shilib ketardi (o'lchandi — test aynan shundan qizardi).
- **`setupStatusSchema` da faqat `step` majburiy.** To'liq javob shaklini oldindan qotirish 02-11 ni shu faylga bog'lab qo'yardi; zod noma'lum kalitlarni jimgina tashlaydi.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] `_platform_admin_market()` qoralama bozorni rad etardi — ko'rinadigan element bosilganda 403**

- **Found during:** Task 2 (`MarketRef` qurilish joylarini aylanib chiqishda)
- **Issue:** Reja va uning `<threat_model>` i X-1 ga tayanadi: *"platforma admini qoralama bozorni **allaqachon tanlay oladi** (`_platform_admin_market()`); o'zgarish faqat topiladigan qiladi"*. Kod bunga ZID edi — `auth.py:568` da `if market.market_id == market_id and market.is_active:` turardi. Reja qabul mezoni `grep "if market.is_active"` ni tekshiradi va bu satr unga TUSHMAYDI (`and market.is_active`), ya'ni mezon uni o'tkazib yuborardi. Natija rejaning O'Z `<done>` mezonini buzardi: qoralama ro'yxatda paydo bo'lardi-yu, bosilganda 403 `market_forbidden` berardi — o'zgarishdan OLDINGI holatdan (ko'rinmaydi) ham yomonroq. Bundan tashqari ustaning 2–7-qadamlari tenant-scoped jadvallarga yozadi va `app.market_id` ni qoralama bozorga o'rnatishning yagona yo'li aynan shu funksiya, ya'ni MARKET-01 texnik jihatdan bajarilmas bo'lib qolardi.
- **Fix:** Faollik sharti olib tashlandi; docstringga sabab, X-1 havolasi va "yangi vakolat berilmaydi" chegarasi yozildi. **Vakolat kengaymadi:** `is_platform_admin` darvozasi (02-01 da `CurrentPasswordDep` + DB'dan qayta o'qish bilan mustahkamlangan) o'z joyida, RLS teginilmadi, qoralama bozor tanlangandan keyin ham oddiy tenant sifatida yashaydi.
- **Files modified:** `services/core-api/app/api/v1/auth.py`, `tests/integration/test_auth_login.py`
- **Verification:** SABOTAJ bilan o'lchandi — shart qaytarilganda `test_platform_admin_can_select_a_draft_market` `403 != 200` bilan qizardi; olib tashlanganda yashil. Nazorat: `test_member_cannot_select_a_foreign_draft_market` → 403 (darvoza hammaga ochilmadi).
- **Committed in:** `54bb193`

**2. [Rule 1 - Bug] `/auth/me` bozor faolligini taxmin qilardi**

- **Found during:** Task 2
- **Issue:** Reja `:796` ni "`markets` qatoridan → `row.is_active`" deb belgilagan, lekin endpointdagi so'rov `SELECT id, name FROM markets` edi — ustun umuman o'qilmasdi. Yagona ishlaydigan variant `is_active=True` literalini yozish bo'lardi va bu rejaning O'Z taqig'ini buzardi ("hech bir joyda `True` literal yozilmaydi"). Oqibati: usta ichida ochilgan sessiya `/auth/me` da o'zini faol bozor deb ko'rsatardi va ekran usta relsini emas, oddiy boshqaruv panelini chizardi.
- **Fix:** So'rovga `is_active` ustuni qo'shildi; docstringda ATAYIN filtrsiz so'rov qoidasi saqlandi.
- **Files modified:** `services/core-api/app/api/v1/auth.py`
- **Verification:** `test_platform_admin_can_select_a_draft_market` ning ikkinchi yarmi — `/auth/me` qoralama bozor uchun `is_active: false` qaytaradi
- **Committed in:** `54bb193`

**3. [Rule 1 - Bug] Badge tugmaning hisoblangan nomiga bo'shliqsiz qo'shilardi**

- **Found during:** Task 3 (komponent testi)
- **Issue:** `<span>{nom}</span><Badge>Qoralama</Badge>` ikki qo'shni inline element; accname algoritmi ular orasiga bo'shliq QO'SHMAYDI, ya'ni hisoblangan nom `"Nurota yangi bozoriQoralama"` bo'lardi. `gap-2` faqat vizual bo'shliq beradi. Skrinrider foydalanuvchisi holatni bitta qo'shilib ketgan so'z sifatida eshitardi — badge'ning butun maqsadi (rang yagona signal emas, WCAG 1.4.1) yarim yo'qolardi.
- **Fix:** Badge oldiga literal `{" "}` matn tuguni; izohda "bu `gap-2` ning takrori emas" deb sababi yozildi.
- **Files modified:** `frontend/src/components/auth/market-picker.tsx`
- **Verification:** `getByRole("button", { name: "Nurota yangi bozori Qoralama" })` — nom aniq satr bilan taqqoslanadi
- **Committed in:** `2b9405a`

**4. [Rule 2 - Missing Critical] `setup-status` fail-safe yo'li testsiz qolgandi**

- **Found during:** Task 3
- **Issue:** Reja `<threat_model>` ida T-02-19 (`setup-status` yiqilsa foydalanuvchi ustaga umuman kira olmasligi) dispozitsiyasi **mitigate** va mitigatsiya matni aniq: "chaqiruv `try/catch` ichida va xatoda `?step=1` ga tushadi". Reja uchta test sanaydi va ularning birortasi bu yo'lni bosmaydi — ya'ni `catch` bloki o'chirilsa yoki `FIRST_STEP` noto'g'ri bo'lsa hech narsa qizarmasdi. Bu ayniqsa muhim, chunki **endpoint 02-11 gacha umuman mavjud emas**, ya'ni bugungi YAGONA ishlaydigan yo'l aynan shu.
- **Fix:** To'rtinchi test — `setup-status` rad etilganda `router.replace("/markets/setup?step=1")`.
- **Files modified:** `frontend/src/components/auth/market-picker.test.tsx`
- **Verification:** `npm --prefix frontend run test:component` — 7 test
- **Committed in:** `2b9405a`

**5. [Rule 3 - Blocking] Qoralama bozor seed'i uchun yordamchi yo'q edi**

- **Found during:** Task 2
- **Issue:** Reja ikkita yangi integratsiya testini talab qiladi va ikkalasi ham `is_active=false` bozorni talab qiladi, lekin mavjud seed'lar (`two_markets`, `auth_users`) faqat faol bozor yaratadi va reja seed yo'lini ko'rsatmagan. Har testda inline `INSERT`/`DELETE` yozish teardown'ni to'rt joyda takrorlardi (FK tartibi: refresh → a'zolik → bozor) va bittasi unutilsa keyingi testlar flaky bo'lardi (`auth_list_markets()` global funksiya).
- **Fix:** `tests/fixtures/auth_api.py::draft_market()` — `contextmanager`, `sbozor_owner` bilan yozadi (`two_markets` bilan bir xil sabab), FK tartibida tozalaydi, ixtiyoriy a'zolik beradi.
- **Files modified:** `tests/fixtures/auth_api.py`
- **Verification:** To'rtta yangi test undan foydalanadi; `pytest tests/integration -q` 100% yashil, qoldiq qator yo'q
- **Committed in:** `54bb193`

**6. [Rule 2 - Missing Critical] Nazorat holatlari rejadagidan kengroq**

- **Found during:** Task 2 va 3
- **Issue:** Reja Task 3 uchun nazorat holatini aniq talab qiladi ("usiz birinchi ikki test 'hamma narsa ustaga ketyapti' holatida ham yashil ko'rinardi"), lekin AYNAN o'sha mantiq backend tomonida ham amal qiladi: `_platform_admin_market()` dagi shart olib tashlangach "endi har kim har qanday bozorni tanlay oladi" holatini hech narsa rad etmasdi.
- **Fix:** `test_member_cannot_select_a_foreign_draft_market` (403 — vakolat bozor faolligiga emas, bayroqqa bog'liq); frontend nazorat testiga ikkinchi da'vo (`setup-status` UMUMAN chaqirilmaydi); `test_login_reports_draft_market_as_inactive` ga faol bozor da'vosi (bayroq har doim `false` deb qattiq yozilmagan).
- **Files modified:** `tests/integration/test_auth_login.py`, `frontend/src/components/auth/market-picker.test.tsx`
- **Committed in:** `54bb193`, `2b9405a`

---

**Total deviations:** 6 auto-fixed (2 bug, 3 missing-critical, 1 blocking). Rule 4 (arxitektura) holati bo'lmadi.
**Impact on plan:** Qamrov kengaytmasi yo'q — birorta yangi funksiya, endpoint yoki paket qo'shilmadi. #1 va #2 rejaning O'Z `<done>` mezonini bajarish uchun zarur edi; #3 mening o'zim kiritgan defektim; #4 va #6 rejaning `<threat_model>` idagi `mitigate` dispozitsiyalari va o'z nazorat-holat qoidasidan kelib chiqadi; #5 — testlarni yozish uchun yo'l.

## Issues Encountered

- **Reja qabul mezoni `_platform_admin_market()` dagi shartni ushlamasdi.** `grep "if market.is_active"` naqshi `and market.is_active` shaklidagi ikkinchi filtrni ko'rmaydi. Mezonlar bajarildi, lekin ular yolg'iz o'zi yetarli bo'lmasdi — deviatsiya #1 aynan shu bo'shliqda edi.
- **Izohlarda taqiqlangan naqshni literal yozish o'z darvozasini qizartiradi.** `if market.is_active` va `is_active=True` ni docstringda tushuntirish uchun yozgandim va ikkala grep mezoni ham yiqildi. 02-02 da o'rnatilgan konvensiya qo'llanildi: taqiqlangan shakl literal yozilmaydi, sabab to'liq qoladi.
- **`.env` worktree'da yo'q** (gitignore), lekin `compose` standart qiymatlari bilan `test` profili ishlaydi — `POSTGRES_PASSWORD` ogohlantirishlari zararsiz. `migrate` profili esa ishlamaydi, shuning uchun `alembic downgrade/upgrade` mezoni **dasturiy ravishda**, `migrated` fixture'i ishlatadigan AYNAN o'sha `alembic.command` API'si orqali va haqiqiy `postgres:18.4` konteynerida o'lchandi (vaqtinchalik test fayli, o'lchovdan keyin o'chirilgan).
- **`ruff format` bitta testni qayta formatladi** (uzun `login(...)` chaqiruvi). O'zgarish faqat qator uzunligiga tegishli.

## Known Stubs

Bu reja **oldinga havola qiladigan ikkita marshrut** yaratadi va ikkalasi ham ataylab — rejaning `<interfaces>` bo'limi ularni nomma-nom kontrakt sifatida e'lon qiladi:

| Havola | Holati | Kim yopadi | Bugungi xulq |
|--------|--------|-----------|--------------|
| `GET /api/v1/markets/{id}/setup-status` | endpoint hali YO'Q | **02-11** | `try/catch` → `?step=1` (test bilan qoplangan) |
| `/markets/setup` sahifasi | marshrut hali YO'Q | **02-16** | qoralama bosilganda 404 sahifasiga tushiladi |

**Bu stub emas, ketma-ketlik.** Reja qamrovi §12.1.1 dagi 6 bandli zanjir bilan cheklangan va u to'liq bajarildi — `is_active` DB'dan UI'gacha uzluksiz oqadi. Usta sahifasining O'ZI 02-11/02-16 rejalarida quriladi va bu reja ularga tayyor kontrakt (`?step=` + `blocking[]` semantikasi) qoldiradi.

**02-16 uchun aniq topshiriq:** `/markets/setup` marshruti tug'ilgan kuni `market-picker.test.tsx` dagi to'rtta test hech qanday o'zgarishsiz ishlashda davom etadi — ular marshrut SATRINI tekshiradi, sahifaning mavjudligini emas.

Boshqa stub yo'q: hech bir komponent bo'sh massiv/`null` bilan qattiq to'ldirilmagan, o'rniga qo'yilgan matn yozilmagan.

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| threat_flag: authz-predicate-widened | `services/core-api/app/api/v1/auth.py` | `_platform_admin_market()` endi qoralama bozorni ham qaytaradi (avval `and market.is_active` bilan kesardi). Reja `<threat_model>` idagi T-02-15 (accept) va X-1 aynan shu xulqni MAVJUD deb hisoblagan — o'zgarish kodni e'lon qilingan modelga moslashtiradi. Vakolat darvozasi (`is_platform_admin`, 02-01 da DB'dan qayta o'qiladi) va RLS teginilmagan; nazorat testi a'zoligi bo'lmagan foydalanuvchi uchun 403 ni qulflaydi. |

Boshqa yangi xavfsizlik yuzasi yo'q: yangi endpoint, fayl kirishi yoki sxema o'zgarishi kiritilmadi (`0006` faqat funksiya qaytish tipini kengaytiradi).

Reja `<threat_model>` idagi dispozitsiyalar bajarildi:

| Threat ID | Holat |
|-----------|-------|
| T-02-15 | accept — X-1 kodda ham to'g'ri bo'ldi (yuqoridagi flag) |
| T-02-16 | mitigate — `memberships()`/`_visible_markets()` docstringlarida "filtrlash iste'molchida" kontrakti yozildi; 6-faza uchun `WHERE m.is_active` nomma-nom qayd etilgan |
| T-02-17 | mitigate — `test_member_cannot_select_a_foreign_draft_market` 403 ni qulflaydi; ro'yxat faqat ko'rinish |
| T-02-18 | mitigate — qoralama oddiy tenant: alohida "wizard" yo'li yaratilmadi, `select-market` audit qatori o'zgarmadi (`test_select_market_audit_carries_platform_admin_label` yashil) |
| T-02-19 | mitigate — `try/catch` → `?step=1`, alohida test bilan qoplangan (deviatsiya #4) |

## Verification Results

| # | Buyruq | Natija |
|---|--------|--------|
| 1 | `alembic upgrade head` | ✅ `0005 -> 0006` bajarildi; `pg_get_function_result` → `TABLE(market_id uuid, market_name text, roles text[], is_active boolean)` |
| 2 | `alembic downgrade 0005 && alembic upgrade head` | ✅ downgrade → 3 ustun, upgrade → 4 ustun; har ikkalasidan keyin `sbozor_app` EXECUTE=`true`, `PUBLIC` EXECUTE=`false` |
| 3 | `npm run test:tenancy` | ✅ exit 0 (101 test) |
| 4 | `pytest tests/integration -q` | ✅ exit 0 (175 test) |
| — | `pytest` (to'liq) | ✅ **440 passed** (02-01 dagi 435 + 5 yangi) |
| 5 | `npm --prefix frontend test` | ✅ 48 node-test + 7 vitest |
| 5 | `npm --prefix frontend run i18n:check` | ✅ 123 kalit × 3 til, drift yo'q |
| — | `npm --prefix frontend run typecheck` / `lint` / `build` | ✅ exit 0 |
| 6 | `npm run gate` | ✅ **exit 0** (to'liq zanjir) |

**Sabotaj o'lchovlari (darvozalar haqiqiyligini isbotlash):**

| Sabotaj | Kutilgan | Natija |
|---------|----------|--------|
| `_platform_admin_market()` ga faollik sharti qaytarildi | qizil | ✅ `AssertionError: {"detail":"market_forbidden"} assert 403 == 200` |
| Badge oldidagi bo'shliq yo'q | qizil | ✅ `Unable to find accessible element ... name "Nurota yangi bozori Qoralama"` |

## Qabul mezonlari

| Mezon | Natija |
|-------|--------|
| `grep -n "if market.is_active" auth.py` | 0 |
| `grep -n "is_active=True" auth.py` | 0 |
| `grep -c "MarketRef(" auth.py` | 8 — har birida `is_active=` |
| `MarketRef.is_active` standart qiymatsiz | ✅ |
| `0006` `down_revision = "0005"` | ✅ |
| `auth_repo.Membership.is_active` | ✅ |
| `marketRefSchema` da `is_active: z.boolean()` | ✅ |
| `marketListItemSchema` da takror yo'q | ✅ |
| `grep "filter((market) => market.is_active)"` | 0 |
| `auth.marketDraft` = `Qoralama` / `Черновик` / `Қоралама` | ✅ |
| `router.replace` qoralamada `"/markets/setup?step="` bilan boshlanadi | ✅ (`?step=3` — eng kichik blocking) |
| Faol bozorda `/markets/setup` YO'Q | ✅ (nazorat testi) |

## User Setup Required

Yo'q — tashqi servis sozlamasi kerak emas.

**DEPLOY ESLATMASI:** `0006` mavjud bazada `auth_memberships(uuid)` ni **DROP qilib qayta yaratadi**. Migratsiya davomida (millisekundlar) o'sha funksiyaga kelgan login/refresh so'rovi xato olishi mumkin. MVP miqyosida ahamiyatsiz, lekin jonli deploy'da migratsiya ilova qayta ishga tushishi bilan bir oynada bajarilsin. GRANT'lar migratsiya ichida tiklanadi — qo'lda hech narsa qilinmaydi.

## Next Phase Readiness

- **02-11 (`setup-status` / `activate`) uchun kontrakt tayyor:** javob tanasida `blocking[]` bo'lishi va har bandda `step` (1 dan boshlanadigan butun son) bo'lishi SHART — `frontend/src/lib/api-types.ts::setupStatusSchema` aynan shunga tayanadi. Qo'shimcha maydonlar (`code`, `count`) frontendni buzmaydi.
- **02-11 uchun MAJBURIY darvoza:** faollashtirish (`activate`) to'liqlikni O'ZI tekshirishi kerak — bozor tanlash endi qoralamani kesmaydi (T-02-16 kontrakti).
- **02-16 (usta qobig'i) uchun:** `/markets/setup?step=N` marshruti kutilmoqda; `market-picker` unga allaqachon yo'naltiradi va `?step=1` fail-safe yo'li ishlaydi.
- **6-faza (hisob-kitob) uchun yozma kontrakt:** qoralama bozor endi javob shakllarida ko'rinadi, ya'ni **har bir mahsulot oqimi `WHERE m.is_active` ni O'ZI yozishi shart** — "ro'yxat allaqachon toza" degan taxmin bugundan boshlab noto'g'ri (RESEARCH Pitfall 7, `auth_repo.memberships()` va `_visible_markets()` docstringlarida qayd etilgan).
- **Kelgusi rejalar uchun asbob:** `tests/fixtures/auth_api.py::draft_market()` — qoralama bozor seed'i, 02-11 va 02-16 testlari uni to'g'ridan-to'g'ri ishlatishi mumkin.

## Self-Check: PASSED

- Da'vo qilingan 15 fayl (1 yaratilgan + 14 o'zgartirilgan) diskda mavjud va `git diff --stat cdf1b45..HEAD` bilan tasdiqlandi
- Uchala vazifa commit'i git tarixida mavjud: `eef6d6e`, `54bb193`, `2b9405a`
- Birorta commit'da kutilmagan fayl o'chirilishi yo'q (`git diff --diff-filter=D` har uchtasida bo'sh)
- Ishchi daraxtda kuzatilmagan (untracked) fayl qolmadi; vaqtinchalik verifikatsiya fayli commit'dan OLDIN o'chirildi

---
*Phase: 02-bozor-domeni-va-yangi-bozor-ustasi*
*Completed: 2026-07-31*
