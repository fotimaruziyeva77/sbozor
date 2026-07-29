---
phase: 01-poydevor-va-tenant-xavfsizligi
plan: 15
subsystem: api
tags: [fastapi, audit, rbac, security-definer, keyset-pagination, gap-closure]

# Dependency graph
requires:
  - phase: "01-14"
    provides: "`auth_list_platform_audit(integer, timestamptz, bigint)` SECURITY DEFINER funksiyasi + `audit_read_platform` owner-scoped policy'si (Gap 5 ning DB yarmi)"
  - phase: "01-11"
    provides: "`Principal.must_change_password`, `require_password_current` darvozasi va CR-03 ning `is_platform_admin` bayrog'iga tayanish qoidasi"
  - phase: "01-07"
    provides: "`GET /api/v1/audit` naqshi — `audit_read` niyati, `encode_cursor`/`decode_cursor`, `mask_sensitive`, 422 `invalid_cursor`"
  - phase: "01-06"
    provides: "`login_failed` yozuvi (`market_id=NULL`) — bu endpoint ochadigan qatorlarning manbai"
provides:
  - "`GET /api/v1/audit/platform` — platforma-global (`market_id IS NULL`) audit o'qish endpointi"
  - "`app.deps.require_platform_admin` — `users.is_platform_admin` BAYROG'IGA tayanadigan darvoza (rolga emas)"
  - "`audit_repo.list_platform_audit` + `PlatformAuditRow`/`PlatformAuditPage` — funksiya ustidagi keyset o'rami"
  - "`audit.py::_entry()` — maskalashning ikkala endpoint uchun YAGONA nuqtasi"
  - "12 ta yangi integratsiya testi (`tests/integration/test_audit_platform.py`)"
affects:
  - "8-faza (hisobot/qattiqlashtirish) — platforma-audit UI iste'molchisi aynan shu endpoint ustiga quriladi"
  - "kelajakdagi platforma-darajali endpointlar — `require_platform_admin` tayyor darvoza"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Platforma-darajasidagi darvoza HAR DOIM `is_platform_admin` BAYROG'INI tekshiradi, `platform_admin` ROLINI emas (CR-03)"
    - "Tenant konteksti KERAK BO'LMAGAN o'qish `AuthSessionDep` oladi — `TenantSessionDep` ortiqcha 409 tug'diradi"
    - "Javob shakliga o'girish (va maskalash) BIR funksiyada: nusxa ko'chirilgan maskalash kamroq ko'riladigan yo'lda jimgina eskiradi"
    - "`EXEMPT_ROUTES` ga qo'shilgan marshrut matritsaning 401/403 qamrovini ham YO'QOTADI — u alohida testda QAYTA TIKLANISHI shart"

key-files:
  created:
    - tests/integration/test_audit_platform.py
  modified:
    - services/core-api/app/deps.py
    - services/core-api/app/repositories/audit_repo.py
    - services/core-api/app/api/v1/audit.py
    - tests/tenancy/test_cross_tenant.py

key-decisions:
  - "Darvoza `require_roles(PLATFORM_ADMIN)` EMAS, `principal.is_platform_admin` — VERIFICATION `missing:` bandi ikkalasini ham taklif qilgan edi, qat'iyrog'i tanlandi (CR-03)"
  - "`AuthSessionDep`, `TenantSessionDep` EMAS — bozor tanlamagan platforma admini ham platforma jurnalini o'qiy oladi (409 yo'q)"
  - "`reason='platform_audit_view'` — tenant yo'lidagi `audit_view` dan FARQ QILADI, aks holda D-09 yozuvi ikki xil o'qishni ajratmasdi"
  - "`PlatformAuditRow` frozen dataclass — `AuditPage`/`AuditLog` ORM shakli qayta ishlatilmadi, chunki bu qatorlarga ORM orqali borib bo'lmaydi"
  - "`_entry()` yordamchisi — maskalash ikki endpointda nusxalanmaydi (T-01-52 ning ikkinchi nusxasi bo'lmasin)"
  - "Marshrut `EXEMPT_ROUTES` da (`global` toifasi) — u tenant RESURSI emas; yo'qolgan qamrov integratsiya testida aniq tiklandi"

patterns-established:
  - "Pattern: platforma-darajasidagi endpoint uchta testsiz to'liq emas — bayroqsiz hisob 403, GIBRID rolli hisob 403, tokensiz 401"
  - "Pattern: `EXEMPT_ROUTES` yozuvi qo'shilganda uning docstringida qaysi qamrov YO'QOLGANI va u QAYERDA tiklangani yoziladi"
  - "Pattern: audit dalili qo'lda INSERT qilinmaydi — u mahsulot oqimidan (noto'g'ri parol -> `login_failed`) tug'iladi"

requirements-completed: [FOUND-03]

# Metrics
duration: 25min
completed: 2026-07-29
---

# Phase 1 Plan 15: Platforma-global audit endpointi (Gap 5 — API qatlami) Summary

**`GET /api/v1/audit/platform` — `login_failed` kabi `market_id IS NULL` yozuvlar nihoyat mahsulot yo'lidan o'qiladi; darvoza `users.is_platform_admin` bayrog'ida (derivatsiyalangan `platform_admin` rolida EMAS), ko'rishning o'zi esa `reason='platform_audit_view'` bilan auditga tushadi.**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-07-29T19:56:00Z
- **Completed:** 2026-07-29T20:21:00Z
- **Tasks:** 2/2
- **Files created:** 1 (modifikatsiya: 4)
- **Tests:** 416 yashil (oldin 404; +12)

## Accomplishments

- **Gap 5 uchdan-uchiga yopildi.** 01-14 DB yarmini (policy + `SECURITY DEFINER` funksiya) qurgan edi, lekin funksiya birorta mahsulot kodidan chaqirilmasdi — o'sha SUMMARY buni "ochiq e'tibor nuqtasi" deb qayd etgan. Endi zanjir to'liq: noto'g'ri parol -> `login_failed` (`market_id=NULL`) -> `auth_list_platform_audit()` -> `GET /api/v1/audit/platform` -> platforma admini ekranida. `test_platform_admin_sees_the_failed_login_row` aynan shu zanjirni HTTP chegarasidan o'tkazadi va yozuvni `phone` markeri bo'yicha topadi.

- **Darvoza VERIFICATION taklif qilganidan QAT'IYROQ qilindi.** Gap 5 ning `missing:` bandi ikki variantni berardi: alohida endpoint **yoki** `require_roles(PLATFORM_ADMIN)`. Ikkinchisi tanlanganda CR-03 ning aynan o'zi qaytarilardi — `platform_admin` matni `user_market_roles.roles` massividan ham keladi, ya'ni bayroqsiz gibrid hisob platforma jurnalini ochib qo'yardi. `require_platform_admin` `users.is_platform_admin` ni tekshiradi va bu `test_hybrid_platform_role_is_forbidden` bilan qulflangan: `auth_seed.hybrid_platform_role` da `platform_admin` roli BOR, bayroq esa `false` — javob 403.

- **`EXEMPT_ROUTES` ga qo'shishning YASHIRIN NARXI hujjatlashtirildi va to'landi.** Istisno marshrutni matritsadan TO'LIQ chiqaradi — nafaqat "404 qaytarsin" da'vosidan, balki tokensiz/buzilgan/muddati o'tgan token testlaridan ham. Bu 01-07 dan beri hech qayerda yozilmagan edi. Endi `EXEMPT_ROUTES` docstringida aniq yozilgan va yo'qolgan qamrov `test_audit_platform.py` da nomma-nom tiklangan (401 tokensiz, 403 bayroqsiz, 403 gibrid rolli).

- **Maskalash ikki nusxaga BO'LINMADI.** Ikkinchi endpoint qo'shilishi `mask_sensitive()` chaqiruvini nusxalashning tabiiy joyi edi. Uning o'rniga `_entry()` yordamchisi ajratildi va ikkala yo'l ham undan o'tadi: `SENSITIVE_AUDIT_KEYS` kelajakda kengaysa, kamroq ko'riladigan platforma yo'li ham AVTOMATIK qamrab olinadi (T-01-52).

- **Must-change darvozasi platforma admini uchun ham ishlaydi.** `require_platform_admin` `CurrentPasswordDep` ga bog'langan, ya'ni D-02 tekshiruvi bayroq tekshiruvidan OLDIN hal bo'ladi. `test_must_change_platform_admin_is_gated` buni MAHSULOT OQIMIDAN quradi (bozor admini platforma adminining parolini tiklaydi) va javob AYNAN `password_change_required` ekanini tekshiradi — `forbidden` emas, aks holda foydalanuvchi parol almashtirish ekraniga yo'naltirilmasdi.

## Task Commits

1. **Task 1: `require_platform_admin` + `list_platform_audit` repo o'rami** — `765dd18` (feat)
2. **Task 2: `GET /api/v1/audit/platform` + EXEMPT_ROUTES + integratsiya testi** — `9d77b2c` (feat)

## Files Created/Modified

**Ilova qatlami**

- `services/core-api/app/deps.py` — `require_platform_admin`. Docstringda uch savol javoblangan: nega rol emas bayroq (CR-03 darsi), nega `CurrentPasswordDep` ga bog'langan (D-02), nega tenant sessiyasi talab qilinmaydi. Modul docstringiga "beshinchi mas'uliyat emas, 3 ning maxsus holi" izohi qo'shildi.
- `services/core-api/app/repositories/audit_repo.py` — `list_platform_audit` + `PlatformAuditRow` + `PlatformAuditPage` + tiplangan `_PLATFORM_AUDIT` matni. Bo'lim izohida nega `AuditRepository` KENGAYTIRILMAGANI yozilgan: uning har bir so'rovi `market_id = app.market_id` bilan quriladi, bu qatorlar esa aynan o'shanga mos KELMAYDI — ya'ni ularni tenant repozitoriysiga qo'shish sinfning yagona da'vosini buzardi.
- `services/core-api/app/api/v1/audit.py` — `/platform` endpointi, `PlatformAuditViewerDep`, `PlatformAuditReadIntentDep`, `_entry()`. Modul docstringiga ikki endpointning KESISHMAYDIGAN qatorlar to'plamini ko'rsatuvchi jadval qo'shildi.

**Testlar**

| Test | Nima qulflanadi |
| ---- | --------------- |
| `test_platform_admin_sees_the_failed_login_row` | Gap 5 ning yopilishi — mahsulot yozgan yozuv mahsulot yo'lidan ko'rinadi |
| `test_platform_admin_without_a_selected_market_can_read` | `AuthSessionDep` qarori — bozorsiz admin 409 OLMAYDI |
| `test_tenant_rows_are_never_returned` | Izolyatsiya: A bozorining probe qatori javobda YO'Q (nazorat qatori bilan) |
| `test_market_admin_is_forbidden` | Bayroqsiz, LEKIN `AUDIT_VIEW` huquqli hisob 403 (nazorat: `GET /audit` unga 200) |
| `test_hybrid_platform_role_is_forbidden` | CR-03: `roles=['platform_admin']` + bayroq `false` -> 403 |
| `test_missing_token_is_rejected` | Matritsadan yo'qolgan 401 qamrovi |
| `test_must_change_platform_admin_is_gated` | T-01-92: D-02 darvozasi bayroq tekshiruvidan OLDIN |
| `test_viewing_the_platform_log_writes_a_read_row` | D-09: `reason`, `filters`, `result_count`, aktor |
| `test_rejected_request_writes_no_read_row` | Rad etilgan so'rov jurnalda YOLG'ON dalil qoldirmaydi |
| `test_keyset_pagination_does_not_repeat_the_boundary_row` | Kursor qat'iy `<`, tartib `at DESC, id DESC` |
| `test_malformed_cursor_is_rejected` | 422, jimgina birinchi sahifaga qaytish yo'q |
| `test_limit_above_the_maximum_is_rejected` | `limit=500` -> 422 (T-01-57) |

`tests/tenancy/test_cross_tenant.py` da `EXEMPT_ROUTES` ga bitta yozuv (`global` toifasi) va istisnoning NARXINI tushuntiruvchi docstring paragrafi qo'shildi.

## Decisions Made

- **Darvoza bayroqda, VERIFICATION ikkinchi variantni ham ruxsat bergan bo'lsa-da.** Gap 5 ning `missing:` bandi so'zma-so'z "`require_roles(PLATFORM_ADMIN)` ostidagi bayroq" deb yozilgan — ya'ni rol variantini ham qabul qilardi. Reja (va bu ijro) uni ATAYIN rad etdi: `require_roles` rol NOMIGA qaraydi, rol esa a'zolik qatoridan ham keladi. CR-03 aynan shu chalkashlikdan tug'ilgan edi va uni ikkinchi marta takrorlash gap-closure planining ma'nosini yo'qotardi.

- **`AuthSessionDep` — bu qarorning narxi bor va u ataylab to'landi.** Tenant sessiyasi bo'lganda kod boshqa endpointlarga o'xshab turardi, lekin bozor tanlamagan platforma admini `409 market_not_selected` olardi. U aynan bozorga tegishli BO'LMAGAN hodisalarni ko'rmoqchi — uni "avval biror bozorni tanlang" deb qaytarish ma'nosiz. Funksiya `SECURITY DEFINER` va GUC'ga umuman qaramaydi, ya'ni tenant sessiyasi hech qanday himoya ham bermasdi. Qaror `test_platform_admin_without_a_selected_market_can_read` da qulflangan.

- **`reason` tenant yo'lidan farq qiladi.** `audit_view` o'rniga `platform_audit_view`. Bir xil `reason` bilan jurnalni o'qiyotgan odam "bozor admini o'z jurnalini ochdi" va "platforma admini platforma-global hodisalarni ko'rdi" ni ajrata olmasdi — D-09 yozuvining butun qiymati aynan shu farqda.

- **`PlatformAuditRow` — mavjud `AuditPage`/`AuditLog` qayta ishlatilmadi.** `AuditPage.rows` tipi `list[AuditLog]`, ya'ni ORM obyekti. Bu qatorlarni ORM obyekti sifatida qurish (transient `AuditLog` yasash) tipni qanoatlantirardi-yu, `Identity(always=True)` kaliti bilan yasalgan soxta obyektlarni sessiyaga tushib ketish xavfini tug'dirardi. `auth_repo` dagi `LoginRow`/`MarketRow`/`UserState` naqshi (funksiya chiqishi = frozen dataclass) mavjud, izchil va tipda qulflangan.

- **`_entry()` yordamchisi UNION tipni qabul qiladi.** `AuditLog | PlatformAuditRow` — ikkalasining maydon nomlari mos, chunki funksiyaning `RETURNS TABLE` imzosi 01-14 da jadval ustunlaridan nusxa olingan. Nomlar bir kun ajralib ketsa mypy DARHOL qizaradi, ya'ni bu moslik hujjatda emas, tiplarda saqlanadi.

- **`intent.filters` da `cursor` YO'Q.** Mavjud `_describe()` bilan bir xil qoida: kursor opaque va jurnalni o'qiyotgan odamga hech nima aytmaydi; `limit` esa qoladi, chunki "kim butun jurnalni yuklab oldi" savoliga aynan u javob beradi.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] `EXEMPT_ROUTES` istisnosi yo'qotgan 401/403 qamrovi qayta tiklandi**

- **Found during:** Task 2 (`EXEMPT_ROUTES` yozuvini qo'shishda)
- **Issue:** Reja marshrutni `EXEMPT_ROUTES` ga qo'shishni to'g'ri talab qildi, lekin istisnoning TO'LIQ ta'siri hisobga olinmagan edi: `tenant_resource_routes()` istisno qilingan marshrutni matritsadan BUTUNLAY chiqaradi, ya'ni unga `test_missing_token_is_rejected`, `test_malformed_token_is_rejected` va `test_expired_token_is_rejected` ham qo'llanmaydi. Rejadagi testlar ro'yxatida esa faqat 403 (market_admin) bor edi. Natijada yangi, HIMOYALANGAN bo'lishi kerak bo'lgan marshrut uchun "tokensiz so'rov rad etiladi" degan da'vo hech qayerda tekshirilmasdi — bu autentifikatsiya darvozasidagi sinovsiz teshik.
- **Fix:** `test_missing_token_is_rejected` integratsiya testi qo'shildi; `EXEMPT_ROUTES` docstringiga istisnoning bu narxi va qamrov QAYERDA tiklangani yozildi (keyingi istisno qo'shadigan odam uchun majburiy qadam sifatida).
- **Files modified:** `tests/integration/test_audit_platform.py`, `tests/tenancy/test_cross_tenant.py`
- **Verification:** `test_missing_token_is_rejected` yashil; `pytest tests/tenancy/test_route_coverage.py` ham yashil (istisno to'g'ri tasniflangan)
- **Committed in:** `9d77b2c` (Task 2 commit)

**2. [Rule 2 - Missing Critical] Gibrid `platform_admin` rolli hisob uchun regressiya testi**

- **Found during:** Task 2 (integratsiya testini yozishda)
- **Issue:** Reja `(c)` bandida faqat "market_admin (is_platform_admin=false) -> 403" ni talab qilardi. Lekin rejaning O'Z threat-registri T-01-91 da "gibrid hisob (agar mavjud bo'lsa) ham 403 oladi" deb yozilgan va bu da'vo hech qanday test bilan qoplanmasdi. Market_admin bilan sinash yetarli emas: unda `platform_admin` roli YO'Q, ya'ni darvoza rolga qaytarilgan taqdirda ham u 403 olardi va test YASHIL qolardi — ya'ni test bayroq-vs-rol farqini umuman o'lchamasdi.
- **Fix:** `test_hybrid_platform_role_is_forbidden` qo'shildi (`auth_seed.hybrid_platform_role` — 01-11 da AYNAN shu maqsad uchun seed qilingan foydalanuvchi: `roles=['platform_admin']` + `is_platform_admin=false`).
- **Files modified:** `tests/integration/test_audit_platform.py`
- **Verification:** Test yashil; darvozani `require_roles(Role.PLATFORM_ADMIN)` ga o'zgartirish uni DARHOL qizartiradi (bu aynan qulflanmoqchi bo'lgan regressiya)
- **Committed in:** `9d77b2c` (Task 2 commit)

**3. [Rule 2 - Missing Critical] Must-change platforma admini uchun darvoza testi (T-01-92)**

- **Found during:** Task 2
- **Issue:** T-01-92 threat-registrda `mitigate` dispozitsiyasi bilan turadi, lekin rejadagi test ro'yxatida uni qamraydigan band yo'q edi. `require_password_current` ga bog'lanish KONSTRUKSIYA bo'yicha to'g'ri, lekin uni birov kelajakda `PrincipalDep` ga o'zgartirsa (masalan "409/403 ni soddalashtirish" niyatida) hech nima qizarmasdi.
- **Fix:** `test_must_change_platform_admin_is_gated` — holat mahsulot oqimidan quriladi (bozor admini platforma adminining parolini tiklaydi), javob AYNAN `password_change_required` ekani tekshiriladi.
- **Files modified:** `tests/integration/test_audit_platform.py`
- **Verification:** Test yashil; `detail` tekshiruvi tufayli darvoza olib tashlansa javob `forbidden`/200 ga o'zgaradi va test qizaradi
- **Committed in:** `9d77b2c` (Task 2 commit)

### Kichik moslashtirishlar (xato emas, tanlov)

- **`_entry()` yordamchisi ajratildi** (rejada aniq so'ralmagan): reja "mavjud `GET /audit` naqshi" bilan maskalashni takrorlashni nazarda tutardi. Nusxa o'rniga bitta funksiya — sabab SUMMARY dagi "Decisions" da.
- **Rejada 5 band (a–e) so'ralgan edi, 12 test yozildi.** Bandlarning har biri alohida testga ajratildi (yiqilganda qaysi da'vo buzilgani darhol ko'rinadi), ustiga sahifalash/kursor/limit qulflari qo'shildi — ular tenant yo'lida allaqachon bor va ikki endpoint xulqi ajralib ketmasligi kerak.
- **Dalil `login_failed` dan olinadi, qo'lda INSERT dan emas.** Reja ikkala variantga ruxsat bergan edi. Qo'lda INSERT "funksiya NULL qatorni qaytaradi" ni isbotlardi — u 01-14 da allaqachon isbotlangan. Bu yerdagi savol boshqacha: MAHSULOT yozgan yozuv MAHSULOT o'qish yo'lidan ko'rinadimi.
- **So'rovlarda `limit=200`** (standart 50 emas): `market_id IS NULL` qatorlar butun test sessiyasi davomida to'planadi va ularni boshqa testlar ham yozadi — 50 lik sahifada test sahifa hajmi tufayli (izolyatsiya tufayli emas) yiqilishi mumkin edi.

---

**Total deviations:** 3 auto-fixed (3× Rule 2 — hammasi TEST qamrovi, mahsulot xulqi o'zgarmagan).
**Impact on plan:** Scope creep yo'q. Uchala tuzatish ham rejaning O'Z threat-registridagi dispozitsiyalarni (T-01-91, T-01-92) va `EXEMPT_ROUTES` qarorining yon ta'sirini qoplaydi; birortasi ham yangi mahsulot yuzasi qo'shmadi.

## Issues Encountered

- **`ruff format` uchta chaqiruvni bir satrga yig'ishni talab qildi** — `ruff format` bilan avtomatik tuzatildi, mazmun o'zgarmadi.
- **`ruff` `isort` tartibida `fixtures` UCHINCHI TARAF deb qaraladi** (birinchi taraf emas), ya'ni `TYPE_CHECKING` blokida u `psycopg` bilan BIR guruhda va alfavit bo'yicha undan oldin turadi. Bu mavjud `test_audit_read.py` bilan bir xil — alohida guruhga ajratilgan dastlabki shakl `I001` berdi va tuzatildi.
- **Qo'shni agentlar bilan compose test profilida ziddiyat yo'q** (bu to'lqinda yagona ijrochi).

## Known Stubs

**1. Platforma-audit UI iste'molchisi — ATAYIN 8-fazaga qoldirildi (ochiq e'lon, yashirin bo'shliq EMAS)**

- **stub:** Platforma-audit UI iste'molchisi yo'q — `market_id IS NULL` qatorlar (masalan `login_failed`) mahsulot UI'sida ko'rinmaydi, faqat `GET /api/v1/audit/platform` (API/Swagger) orqali.
- **reason:** VERIFICATION Gap 5 mandati faqat o'qish YO'LI (himoyalangan endpoint + SECURITY DEFINER); UI qo'shimcha va bu backend gap-closure planining doirasidan tashqarida.
- **closes:** 8-faza (hisobot/qattiqlashtirish yuzasi).

Batafsil: mavjud `frontend/src/app/[locale]/(app)/audit/page.tsx` (01-09) TENANT-SCOPED — u `GET /api/v1/audit` ni chaqiradi va faqat `market_id` bo'yicha cheklangan qatorlarni ko'rsatadi. Platforma admini `market_id IS NULL` qatorlarni hozircha faqat API orqali ko'radi.

Bu yozuv endpoint MAVJUDLIGINI INKOR ETMAYDI: backend o'qish yo'li to'liq ishlaydi, himoyalangan va 12 test bilan qoplangan. Bu faqat "mahsulot UI'sida hali ekran yo'q" degani. 01-15 frontend planga KENGAYTIRILMADI, chunki bu wave-2 disjointligini (bu plan faqat backend fayllarga tegadi) va gap-closure doirasini buzardi.

**Boshqa stub yo'q.** Endpoint, repo o'rami, darvoza va 12 testning hammasi to'liq ishlaydi va haqiqiy `postgres:18.4-trixie` ga qarshi tekshirilgan.

## Threat Flags

Yangi, reyestrda qayd etilmagan xavfsizlik yuzasi paydo bo'lmadi. Rejadagi to'rtala dispozitsiya bajarildi:

| Threat | Qanday yopildi | Tekshiruv |
| ------ | -------------- | --------- |
| T-01-91 (Elevation of Privilege — darvoza) | `require_platform_admin` AUTORITATIV `is_platform_admin` bayrog'ini tekshiradi | `test_market_admin_is_forbidden` (bayroqsiz+huquqli), `test_hybrid_platform_role_is_forbidden` (gibrid rol) |
| T-01-92 (Elevation of Privilege — must-change) | `CurrentPasswordDep` orqali D-02 darvozasiga bog'langan | `test_must_change_platform_admin_is_gated` (`detail` bilan) |
| T-01-93 (Repudiation — o'qish yozuvi) | `audit_read(reason='platform_audit_view')` | `test_viewing_the_platform_log_writes_a_read_row`, `test_rejected_request_writes_no_read_row` |
| T-01-94 (Information Disclosure — javob) | Funksiya sharti LITERAL `market_id IS NULL`; javob `_entry()` -> `mask_sensitive()` | `test_tenant_rows_are_never_returned` (nazorat qatori bilan) |

**Qamrovdan tashqarida qolgan kichik nomuvofiqlik (mahsulot xulqiga ta'sirsiz):** `services/core-api/app/api/v1/auth.py::_audit_login_failed` docstringida "platforma admini uchun alohida tor yo'l 01-07 rejasida" deb turibdi — havola eskirgan (yo'l aslida 0005 + shu plan). Fayl bu planning `files_modified` ro'yxatida emas, shuning uchun TEGILMADI; keyingi `auth.py` ga tegadigan planda tuzatilishi kerak.

## User Setup Required

Yo'q — tashqi servis konfiguratsiyasi talab qilinmaydi. Yangi migratsiya ham yo'q (0005 allaqachon 01-14 da qo'llangan):

```
npm test            # docker compose --profile test run --rm tests pytest -q
```

## Next Phase Readiness

**Tayyor:**

- `GET /api/v1/audit/platform` OpenAPI sxemasida (`app.openapi()['paths']` bilan tasdiqlangan), `AuditListResponse` shaklida javob beradi — 8-fazadagi UI uchun kontrakt mavjud tenant audit ekrani bilan AYNAN bir xil (`items` + `next_cursor`), ya'ni komponentni qayta ishlatish mumkin.
- `require_platform_admin` — kelajakdagi har qanday platforma-darajasidagi endpoint uchun tayyor darvoza; uni ishlatgan endpoint avtomatik ravishda D-02 darvozasini ham oladi.
- Kursor formati ikkala endpointda bir xil (`encode_cursor`/`decode_cursor`), ya'ni sahifalash komponenti ham umumiy.

**Ochiq e'tibor nuqtalari:**

- **UI iste'molchisi yo'q** (yuqoridagi "Known Stubs") — 8-faza. Fazani yopishda bu ochiq e'lon sifatida ko'rinishi kerak, bo'shliq sifatida emas.
- **Platforma-audit o'qish yozuvining joyi tanlangan bozorga bog'liq.** Bozor tanlagan admin uchun `read` yozuvi o'sha bozorning jurnaliga tushadi, tanlamagan admin uchun esa `market_id=NULL` bo'ladi va u shu endpointning O'ZIDA ko'rinadi. Bu KUTILGAN (01-14 SUMMARY buni oldindan aytgan edi va bu yerda ataylab tanlandi), lekin 8-fazadagi UI "kim platforma jurnalini ko'rdi" hisobotini qursa, ikkala joyni ham hisobga olishi kerak.
- **`auth.py` dagi eskirgan docstring havolasi** (yuqorida) — kosmetik, keyingi tegishli planda.

## Self-Check: PASSED

- **Fayllar:** da'vo qilingan 5 ta artefaktning (1 yangi + 4 modifikatsiya) hammasi mavjud va git'da kuzatilmoqda; SUMMARY ham joyida.
- **Commitlar:** `765dd18`, `9d77b2c` — ikkalasi ham `git log` da mavjud.
- **O'chirilgan fayl yo'q:** `git diff --diff-filter=D --name-only 1105285..HEAD` bo'sh.
- **Rejadan tashqari faylga tegilmadi:** `git diff --name-only 1105285..HEAD` aynan `files_modified` ro'yxatidagi 5 faylni beradi.
- **Umumiy artefaktlarga tegilmadi:** `STATE.md` / `ROADMAP.md` / `REQUIREMENTS.md` diff'da yo'q (worktree rejimi — ularni orkestrator yangilaydi). Frontend fayllariga ham tegilmadi.
- **Darvozalar:** `ruff check .` + `ruff format --check .` + `mypy .` (strict, 87 fayl) + `pytest -q` (416 test) — hammasi yashil.
- **Marshrut:** `GET /api/v1/audit/platform` `app.openapi()['paths']` da mavjud; `test_exempt_routes_still_exist_in_the_app` va `test_route_walker_matches_openapi` yashil.

---
*Phase: 01-poydevor-va-tenant-xavfsizligi*
*Completed: 2026-07-29*
