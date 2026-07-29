---
phase: 01-poydevor-va-tenant-xavfsizligi
plan: 10
subsystem: testing
tags:
  [
    tenancy,
    rls,
    cross-tenant,
    regression-gate,
    route-matrix,
    fastapi-internals,
    ci,
    validation-contract,
    multi-tenant,
  ]

# Dependency graph
requires:
  - "01-01 (compose `test` profili, pytest+testcontainers, ci-backend.yml, root package.json)"
  - "01-04 (`two_markets` fixture'i, RLS policy'lari, meta-testlar)"
  - "01-06 (login/select-market oqimi, `Principal`, RLS -> 404 handler, `encode_access`)"
  - "01-07 (users/me/markets/audit endpointlari — matritsa qamraydigan yuza)"
provides:
  - "tests/tenancy/test_cross_tenant.py — `app.routes` dan avtomatik quriladigan cross-tenant matritsa (44 test)"
  - "tests/tenancy/test_route_coverage.py — tasniflanmagan marshrutni fail qiladigan qamrov darvozasi (8 test)"
  - "`tenant_resource_routes()` / `EXEMPT_ROUTES` / `PARAM_FILLERS` — keyingi fazalar kengaytiradigan kontrakt"
  - "`two_markets`: har bozorda direktor, haqiqiy Argon2 hash, `admin_password`, `audit_row_id`, `role_ids`, `phones`"
  - "`SEED_PASSWORD` — barcha test seed'lari uchun yagona parol manbai"
  - "conftest `token_for` — mahsulot login oqimi orqali access token"
  - "ci-backend.yml: `SQL injection gate` va `Tenancy gate (FOUND-02)` alohida qadamlar"
  - "package.json: `test:tenancy` va `gate` skriptlari"
  - "01-VALIDATION.md — to'ldirilgan va imzolangan validatsiya kontrakti"
affects:
  - "2–7 fazalar (har yangi endpoint matritsaga AVTOMATIK tushadi; yangi path parametri `PARAM_FILLERS` ga bir satr talab qiladi, aks holda CI yiqiladi)"
  - "faza verifikatori (01-09 ning ikki satri VALIDATION.md da ochiq qoldirilgan — qayta tekshirilishi shart)"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Marshrut ro'yxati QO'LDA yozilmaydi — `app.routes` dan olinadi; unutish xavfsiz tomonga ishlaydi"
    - "Tasnif NEGATIV: istisno bo'lmagan hamma narsa matritsaga tushadi (pozitiv ro'yxat yangi marshrutni jimgina tashqarida qoldirardi)"
    - "Ichki API'ga tayangan yurish OMMAVIY kontrakt (`app.openapi()`) bilan solishtiriladi — jimgina bo'shab qolish ushlanadi"
    - "Har istisno SABAB bilan va uchta ma'lum toifadan biri sifatida yoziladi"
    - "Nazorat holati majburiy: 'B ko'rinmaydi' yoniga 'A ko'rinadi' qo'yiladi, aks holda bo'sh javob ham yashil bo'lardi"
    - "Test seed'i sun'iy qator YARATMAYDI — mavjud mahsulot yo'li qatorining kaliti o'qiladi"

key-files:
  created:
    - tests/tenancy/test_cross_tenant.py
    - tests/tenancy/test_route_coverage.py
  modified:
    - tests/fixtures/two_markets.py
    - tests/fixtures/auth_users.py
    - tests/fixtures/__init__.py
    - tests/conftest.py
    - .github/workflows/ci-backend.yml
    - package.json
    - .planning/phases/01-poydevor-va-tenant-xavfsizligi/01-VALIDATION.md

key-decisions:
  - "FastAPI 0.140 `app.routes` TEKIS EMAS (`_IncludedRouter`) — rekursiv yurish + OpenAPI parite testi majburiy bo'ldi"
  - "Tasnif ikki bosqichli: istisno emasmi -> path parametrlarining fillerи bormi; ikkinchisisiz darvoza soxta marshrutni o'tkazib yuborardi"
  - "Sun'iy audit `probe` qatori RAD ETILDI — u mavjud testni buzardi; o'rniga trigger yozgan haqiqiy qatorning kaliti o'qiladi"
  - "`token_for` imzosi rejadagidan farq qiladi: rollar chaqiruvchidan emas, bazadan keladi"
  - "`audit_log.id` javob matnini skanerlashda MARKER sifatida ishlatilmaydi — butun son yolg'on-qizil berardi"
  - "VALIDATION.md da 01-09 satrlari ✅ EMAS, ⏳ deb belgilandi — u parallel to'lqinda va tekshirilmagan"

patterns-established:
  - "Pattern: avtomatik ro'yxatga tayangan test o'zining BO'SHAB QOLISHIGA qarshi alohida test bilan himoyalanadi"
  - "Pattern: darvoza xato xabari keyingi qadamni AYTADI ('PARAM_FILLERS ga qo'shing'), faqat 'assert False' emas"
  - "Pattern: matritsa qiymatlari haqiqatan begona bozorga tegishli ekani alohida test bilan qulflanadi"

requirements-completed: [FOUND-02]

# Metrics
duration: 45min
completed: 2026-07-29
---

# Phase 1 Plan 10: Cross-tenant matritsa va faza darvozasi Summary

**`app.routes` dan avtomatik quriladigan cross-tenant matritsa: A bozori tokeni + B bozori obyekti har bir tenant marshrutida 404 (va alohida assert bilan 403 EMAS), tasniflanmagan marshrut esa CI'ni marshrut nomi bilan yiqitadi — 52 yangi test, jami 375 yashil; yo'l-yo'lakay FastAPI 0.140 ning `app.routes` ni tekis ro'yxat bo'lishdan to'xtatgani ochildi va matritsaning jimgina bo'shab qolishiga qarshi OpenAPI parite darvozasi qo'yildi.**

## Performance

- **Duration:** ~45 min
- **Tasks:** 2/2
- **Files created:** 2 (modifikatsiya: 7)
- **Tests:** 375 yashil (oldin 323 edi) — 52 yangi; tenancy to'plami 42 -> 94

## Accomplishments

- **Matritsa 01-06 ning rejadan tashqari endpointini o'zi topdi.** Bu avtomatik ro'yxatning qiymatini eng aniq ko'rsatadigan fakt: `GET /api/v1/auth/me` 01-06 rejasida YO'Q edi, u deviatsiya sifatida qo'shilgan. Qo'lda yuritilgan ro'yxatga uni hech kim qo'shmasdi va u tekshiruvdan tashqarida qolardi. Hozir u matritsaning 7 marshrutidan biri va uchala 401 da'vosi hamda sizish skaneri ostida.

- **FastAPI 0.140 `app.routes` ni tekis ro'yxat bo'lishdan to'xtatgan — bu reja yozilganda ma'lum emas edi.** `include_router()` natijasi endi `_IncludedRouter` o'ramiga tushadi: marshrutlar `original_router.routes` da, prefiks esa `include_context.prefix` da. Sodda `for route in app.routes` sikli 15 ta marshrutdan atigi **6 tasini** ko'radi (4 ta hujjat sahifasi + `/healthz` + `/readyz`) va **birorta ham API endpointini** topmaydi — ya'ni matritsa bo'sh bo'lib, `pytest` "hammasi o'tdi" deb tugardi. Rekursiv yurish yozildi.

- **Va aynan shu topilma yangi xavfni ochdi, unga qarshi darvoza qo'yildi.** Yurish FastAPI ning ICHKI tuzilmasiga tayanadi; u yana o'zgarsa, kod **istisno ko'tarmaydi** — u shunchaki kamroq marshrut topadi va butun matritsa jimgina yo'qoladi. `test_route_walker_matches_openapi` yurish natijasini `app.openapi()` (ommaviy kontrakt) bilan solishtiradi: OpenAPI'dagi har bir (yo'l, metod) yurishda BO'LISHI shart. Bu test rejada yo'q edi va usiz butun artefakt bir kun jimgina o'lardi.

- **Qamrov darvozasi sabotaj bilan o'lchandi.** `services/core-api/app/main.py` ga vaqtincha `GET /api/v1/dummy/{id}` qo'shildi. `test_no_unclassified_routes` darhol yiqildi va xabar keyingi qadamni AYTDI: `GET_/api/v1/dummy/{id} -> PARAM_FILLERS da yo'q: id`. `test_all_path_params_have_fillers` ham qizardi (ikkinchi, mustaqil yo'nalish). Soxta marshrut olib tashlandi, `main.py` `git checkout` bilan asl holiga qaytarildi va diffda yo'q.

- **404 da'vosi ikki qatlamda: kod VA javob tanasi.** Har bir cross-tenant testida avval `status != 403` (sabab: 403 obyekt mavjudligini tasdiqlaydi), keyin `== 404`. Bundan tashqari `test_cross_tenant_is_indistinguishable_from_unknown_id` begona bozor ID'si bilan mavjud bo'lmagan ID javoblarini **bayt-bayt** solishtiradi — bir xil 404 ichida turli `detail` matni ham enumeration signali bo'lardi.

- **D-06 ayni bir marshrutda, ayni bir obyektda isbotlandi.** Platforma admini A ni tanlaganda `POST /users/{B kassiri}/reset-password` -> 404; B ni tanlagach AYNAN o'sha chaqiruv -> 200. Farq faqat tanlangan bozorda, ya'ni "platforma admini hamma narsani ko'radi" degan talqinga joy qolmaydi.

- **Audit sizishi beshta filtr ostida va NAZORAT HOLATI bilan.** `GET /audit` filtrsiz, jadval, amal, sana oralig'i va maksimal chegara bilan chaqiriladi; har safar B bozorining audit qatori `id` si javobda yo'qligi tekshiriladi. Yoniga `test_audit_list_shows_the_own_market_probe_row` qo'yilgan: A ning o'z qatori KO'RINADI. Usiz beshtala test endpoint umuman bo'sh qaytargan holatda ham yashil bo'lardi.

- **`two_markets` endi mahsulot login oqimini qo'llab-quvvatlaydi.** Seed `argon2-seed-placeholder` o'rniga haqiqiy Argon2 hash yozadi, parol esa yagona manbadan (`SEED_PASSWORD`) keladi va `auth_users` uni import qiladi. Natijada matritsa tokenni `POST /auth/login` (+ `select-market`) orqali oladi — qo'lda yasalgan token login zanjiridagi nosozlikni yashirardi.

## Task Commits

1. **Task 1: Cross-tenant matritsa va qamrov darvozasi** — `4c2a373` (test)
2. **Task 2: Faza darvozasi, CI gate'lari va validatsiya kontrakti** — `6dae551` (chore)

## Files Created/Modified

**Testlar** — 52 yangi

| Fayl | Testlar | Nima qulflangan |
| ---- | ------- | --------------- |
| `tests/tenancy/test_cross_tenant.py` | 44 | 3 marshrutda 404 + `!= 403`, 3 marshrutda bayt-bayt tenglik, 7 marshrutda sizish skaneri, 7×3 = 21 ta 401 (tokensiz/buzilgan/muddati o'tgan), 5 audit filtri, D-06, filler va sabab invariantlari |
| `tests/tenancy/test_route_coverage.py` | 8 | tasniflanmagan marshrut, eskirgan istisno, sabab toifasi, bo'sh matritsa, obyekt marshrutining yo'qligi, filler to'liqligi, OpenAPI pariteti, to'plamlar kesishmasligi |

**Fixture'lar**

- `two_markets.py` — `MarketSeed` ga `director_*`, `admin_password`, `audit_row_id`; `role_ids`/`phones` xossalari; `SEED_PASSWORD(_HASH)`; `ROLES_PER_MARKET` 3 -> 4
- `auth_users.py` — parol va hash `two_markets` dan olinadi (ikki literal ajralib ketmasin)
- `__init__.py` — `TokenFactory` protokoli
- `conftest.py` — `token_for` fixture'i

**Darvozalar**

- `ci-backend.yml` — `SQL injection gate` (ruff `S608`) va `Tenancy gate (FOUND-02)` alohida qadam
- `package.json` — `test:tenancy`, `gate`
- `01-VALIDATION.md` — o'lchangan runtime'lar, 28 tasklik xarita, Wave 0 ✅, imzo

## Decisions Made

- **Tasnif IKKI bosqichli, bir bosqichli emas.** Dastlabki shakl "istisno bo'lmagan hamma narsa matritsada" edi — bu `test_no_unclassified_routes` ni MA'NOSIZ qilardi: har qanday yangi marshrut avtomatik "tasniflangan" bo'lib chiqardi va soxta `/api/v1/dummy/{id}` darvozani bemalol o'tardi. Endi ikkinchi shart bor: marshrutning har bir path parametri uchun `PARAM_FILLERS` da qiymat bo'lishi kerak. Parametri yo'q yangi endpoint (masalan `GET /reports`) baribir AVTOMATIK qamraladi (sizish skaneri + 401 testlari), parametrlisi esa bir satrlik qo'shimchani talab qiladi va uni unutib bo'lmaydi.

- **Sun'iy audit "probe" qatori rad etildi.** Birinchi amalga oshirish har bozorga `action='update'` bilan qator yozardi. To'liq to'plamda `test_patch_locale_writes_an_audit_row_with_old_and_new` darhol qizardi (`assert 2 == 1`) — u bozordagi `update` qatorlarini SANAYDI. Yechim faqat "boshqa `action` tanlash" emas edi: har qanday sun'iy qator kelajakdagi sanoqli testlar uchun mina bo'lib qolardi. Endi seed HECH NARSA YOZMAYDI — a'zolik INSERT'ining triggeri yozgan haqiqiy qatorning kaliti o'qiladi. Bu ayni paytda kuchliroq da'vo: tekshirilayotgan yozuv mahsulot yo'lidan tug'ilgan.

- **`token_for` imzosi rejadagidan farq qiladi.** Reja `token_for(user_id, market_id, roles)` ni ko'rsatgan. Rollarni ARGUMENT sifatida qabul qilish "kassir tokeni `market_admin` rollari bilan" kabi bazada MAVJUD BO'LMAGAN holatni yasashga imkon berardi va matritsa haqiqiy tizimni emas, o'zi o'ylab topgan tizimni sinardi. Amaldagi imzo — `(phone, password, market_id)`; rollar login javobida bazadan keladi.

- **`audit_log.id` javob matnini skanerlashda marker EMAS.** Sizish skaneri javob tanasida B bozorining identifikatorlarini qidiradi. Butun son (`42` kabi) javobning istalgan joyidagi songa — sanaga, boshqa `id` ga, `result_count` ga — mos kelib YOLG'ON-QIZIL berardi. Shuning uchun markerlar faqat UUID va E.164 telefon; audit kaliti esa STRUKTURA bo'yicha (aynan `item["id"]`) tekshiriladi.

- **Yurish natijasi OpenAPI bilan solishtiriladi.** Ichki API'ga tayanish muqarrar edi (boshqa yo'l yo'q), lekin uning buzilishi JIMGINA bo'lardi. OpenAPI — hujjatlashtirilgan yuza; undagi har bir marshrut yurishda bo'lishi shart. Teskari yo'nalish tekshirilmaydi, chunki `/api/docs`, `/redoc`, `openapi.json` OpenAPI sxemasida ataylab yo'q.

- **VALIDATION.md da 01-09 satrlari ⏳ deb belgilandi, ✅ emas.** Reja "barcha satrlarni ✅ qil" deydi, lekin 01-09 MEN BILAN BIR TO'LQINDA, parallel worktree'da ishlayapti va uning artefaktlari (`frontend/src/components/users/`) mening daraxtimda umuman yo'q. Ularni yashil deb belgilash — validatsiya kontraktiga tekshirilmagan da'vo yozish, ya'ni bu fazaning butun mazmuniga (yolg'on dalil yozmaslik) zid. Ular ⏳ toifasi bilan, sababi va kim tekshirishi kerakligi bilan yozildi.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] FastAPI 0.140 da `app.routes` tekis ro'yxat emas**

- **Found during:** Task 1 (marshrutlarni sanab chiqishga birinchi urinish)
- **Issue:** `include_router()` natijasi `_IncludedRouter` o'ramida; sodda sikl 15 marshrutdan 6 tasini ko'radi va birorta ham API endpointini topmaydi. Reja va RESEARCH "`app.routes` dan avtomatik ro'yxat olinadi" deb yozganda bu tuzilma mavjud emas edi.
- **Fix:** `_walk()` — `original_router.routes` bo'ylab rekursiv yurish, prefikslarni `include_context.prefix` dan to'plash.
- **Verification:** 15 marshrut topiladi; `test_route_walker_matches_openapi` OpenAPI'dagi 15 tasi ham yurishda borligini tasdiqlaydi.
- **Committed in:** `4c2a373`

**2. [Rule 2 - Missing Critical] Yurishning JIMGINA bo'shab qolishiga qarshi himoya yo'q edi**

- **Found during:** Task 1 (#1 ni tuzatgandan keyin)
- **Issue:** Yurish ichki API'ga tayanadi. U yana o'zgarsa, kod xato bermaydi — `parametrize` bo'sh ro'yxat oladi, pytest hech qanday test yaratmaydi va to'plam "o'tdi" deb tugaydi. Ya'ni fazaning eng uzoq yashaydigan artefakti bir kun jimgina o'lardi.
- **Fix:** `test_route_walker_matches_openapi` (rejada yo'q) — `app.openapi()` dagi har bir (yo'l, metod) yurishda bo'lishi shart. Qo'shimcha `test_matrix_is_not_empty` va `test_object_routes_are_covered`.
- **Committed in:** `4c2a373`

**3. [Rule 1 - Bug] Sun'iy audit qatori mavjud testni buzardi**

- **Found during:** Task 1 (to'liq to'plam)
- **Issue:** `MarketSeed.audit_row_id` uchun har bozorga `action='update'` qatori yozilardi. `test_patch_locale_writes_an_audit_row_with_old_and_new` bozordagi `update` qatorlarini sanaydi -> `assert 2 == 1`.
- **Fix:** Seed endi qator YOZMAYDI; a'zolik triggeri yozgan birinchi qatorning kaliti o'qiladi (`_first_audit_row_id`). Tenant konteksti `set_config` bilan o'rnatiladi va `finally` da bo'shatiladi — aks holda `cleanup_two_markets()` faqat bitta bozorni ko'rib, ikkinchisi FK bilan qolib ketardi.
- **Verification:** 375/375 yashil.
- **Committed in:** `4c2a373`

**4. [Rule 1 - Bug] Grep darvozasi o'z izohi bilan yiqilardi (BESHINCHI takror)**

- **Found during:** Task 2 (qabul mezonlarini yakuniy tekshirish)
- **Issue:** Qabul mezoni: `grep -c "xfail\|pytest.mark.skip" tests/tenancy/test_route_coverage.py` -> 0. Mening fayl docstringim aynan shu markerlar ISHLATILMASLIGINI tushuntirish uchun ularni LITERAL yozgandi -> grep 1 qaytardi. Bu 01-01/01-03/01-05/01-06/01-07 dagi bilan AYNAN bir xil sinf xato.
- **Fix:** Izoh ma'nosini saqlagan holda literal markersiz qayta yozildi ("kutilgan nosozlik" va "o'tkazib yuborish" markerlari), va izohning o'ziga bu qoidaning sababi yozildi — keyingi tahrirlovchi oltinchi marta takrorlamasin.
- **Verification:** ikkala yangi faylda ham grep -> 0.
- **Committed in:** `6dae551`

**5. [Rule 2 - Missing Critical] Seed paroli ikki modulda ikki literal edi**

- **Found during:** Task 1 (`MarketSeed.admin_password` ni qo'shishda)
- **Issue:** `two_markets` o'rinbosar hash yozardi, `auth_users` esa o'z `PASSWORD` literali bilan uni qayta yozardi. `admin_password` maydonini shunchaki qo'shish `auth_seed` faol bo'lgan testlarda YOLG'ON qiymat berardi (login 401, sabab fixture'da ko'rinmasdi).
- **Fix:** `SEED_PASSWORD` + `SEED_PASSWORD_HASH` `two_markets` da (quyi qatlam), `auth_users` ularni import qiladi. Hash bir marta hisoblanadi.
- **Committed in:** `4c2a373`

### Kichik moslashtirishlar (xato emas, tanlov)

- **`tests/fixtures/__init__.py` rejaning fayl ro'yxatida yo'q** — `TokenFactory` protokoli `TenantSessionFactory` yonida yashaydi (01-04 da o'rnatilgan naqsh: umumiy fixture tiplari shu yerda).
- **`ROLES_PER_MARKET` 3 -> 4** — direktor qo'shilgani uchun. Konstanta `test_rls_predicate.py` va `test_login_bootstrap.py` dan import qilinadi, ya'ni ikkala test ham o'zgarishsiz yashil qoldi (aynan shuning uchun u konstanta edi).
- **Testlar rejadagi minimumdan ko'p** — matritsa 3 marshrutni emas, 7 tasini qamraydi; 401 da'vosi 3 xil token holatida (tokensiz, buzilgan, muddati o'tgan) sinaladi; audit 5 filtr bilan (reja 3 tani talab qilgan).
- **`EXEMPT_ROUTES` da 13 ta yozuv** — `<interfaces>` dagi 11 tasiga `/docs/oauth2-redirect` va `/redoc` qo'shildi. Ular FastAPI ning standart marshrutlari va `all_routes()` ularni ham ko'radi; ro'yxatga kiritilmasa `test_exempt_routes_still_exist_in_the_app` emas, sizish/401 testlari ma'nosiz qizarardi.
- **`GET /api/v1/auth/me` istisno EMAS** — u tenant ma'lumoti (tanlangan bozor nomi) qaytaradi, ya'ni matritsaning to'la a'zosi.

---

**Total deviations:** 5 auto-fixed — 2× Rule 1 (sun'iy audit qatori, grep darvozasi), 2× Rule 2 (yurish himoyasi, parol manbai), 1× Rule 3 (FastAPI 0.140 tuzilmasi).
**Impact on plan:** Scope creep yo'q — barcha o'zgarishlar rejaning o'z qabul mezonlari va tahdid reyestri doirasida. Bittasi (#1) rejaning asosiy texnik faraziga tegdi: "`app.routes` dan ro'yxat olinadi" endi bir satrlik sikl emas, rekursiv yurish; #2 esa o'sha faktdan kelib chiqqan yangi xavfni yopdi. Rejaning barcha qabul mezonlari o'zgarishsiz bajarildi.

## Verification Evidence

| Tekshiruv | Natija |
| --------- | ------ |
| `pytest tests/tenancy -x -q` | 94 yashil (14.2 s) |
| `pytest -q` (to'liq) | **375 yashil** (42.8 s) |
| `ruff check .` + `ruff format --check .` + `mypy .` (strict, 83 fayl) | toza |
| `ruff check --select S608 .` | toza |
| Soxta `/api/v1/dummy/{id}` | `test_no_unclassified_routes` marshrut nomi bilan yiqildi; `main.py` qaytarildi |
| Grep darvozasi (ikkala yangi fayl) | 0 |
| `ci-backend.yml` YAML parse | 9 qadam, ichida `SQL injection gate` va `Tenancy gate (FOUND-02)` |
| `npm run gate` — backend qismi | `lint` (7 s) -> `test` (47 s) -> `test:tenancy` (20 s), zanjir yashil |
| `npm run gate` — frontend qismi | **mahalliy ishga tushirilmadi** (pastda) |
| `01-VALIDATION.md` platsholder tekshiruvi | `nyquist_compliant: true` bor, shablon platsholderi yo'q |

**`npm run gate` ning frontend qismi haqida aniq gap.** Zanjirning to'rt frontend qadami (`i18n:check`, `typecheck`, `lint`, `build`) **ishga tushirilmadi**. Sabab ikkita va ikkalasi ham qasddan: (1) bu worktree'da `frontend/node_modules` yo'q; (2) `frontend/` ayni paytda 01-09 rejasi tomonidan parallel o'zgartirilmoqda, ya'ni u yerdagi build natijasi mening rejamning holatini emas, boshqa rejaning oraliq holatini o'lchardi. Buning o'rniga `gate` skripti chaqirayotgan to'rtala skript `frontend/package.json` da MAVJUDLIGI dasturiy tekshirildi (`node -e` bilan, hammasi topildi), backend qismi esa to'liq va jonli o'lchandi. Zanjirning frontend qismi 01-09 birlashgandan keyin faza verifikatori tomonidan bir marta ishga tushirilishi kerak.

## Issues Encountered

- **`docker compose run -e PYTHONPATH=...` Windows Git Bash'da yo'l konversiyasiga uchraydi** (`/app/...` -> `C:/Program Files/...`). Faqat qo'lda tekshirishda uchradi; yakuniy kodga ta'sir qilmadi, chunki pytest yo'llarni `pyproject.toml` dagi `pythonpath` dan oladi.
- **Ikki `-q` bayrog'i pytest xulosasini o'chiradi.** `addopts` da allaqachon `-q` bor, buyruqqa yana `-q` qo'shilganda `-qq` bo'lib "375 passed" satri umuman chiqmaydi — test soni "ko'rinmay qolgan" bo'lib tuyulardi. Sonlar `-q` siz chaqiruv bilan olindi.

## Known Stubs

Yo'q. Bu rejadagi har bir test haqiqiy `postgres:18.4-trixie` + `valkey:9.1.1-alpine` ga qarshi ishlaydi va mahsulot login oqimidan o'tadi.

Atayin **boshqa rejalarga** qoldirilgan:

- **`market_id IS NULL` audit qatorlari** (01-06/01-07 dan meros ochiq bo'shliq) — matritsa ularni QAMRAMAYDI va bu to'g'ri: `GET /audit` ataylab tenant-scoped. Bo'shliq 01-07 SUMMARY'sida qayd etilgan va u yerda qoladi.
- **01-09 ning ikki satri VALIDATION.md da ⏳** — parallel to'lqin; faza verifikatori tasdiqlashi shart.

## Threat Flags

Yo'q — bu rejada yangi xavfsizlik yuzasi paydo bo'lmadi (u faqat test va CI konfiguratsiyasiga tegadi). `<threat_model>` dagi 7 dispozitsiyaning hammasi bajarildi:

| Threat | Qanday yopildi | Tekshiruv |
| ------ | -------------- | --------- |
| T-01-75 | Matritsa `app.routes` dan avtomatik quriladi; 7 marshrut qamrovda | `test_cross_tenant_object_returns_404`, `test_no_route_leaks_other_market_identifiers`, `test_audit_list_never_leaks_the_other_market` (5 filtr) |
| T-01-76 | Har testda `status != 403` ALOHIDA assert; javob tanasi mavjud bo'lmagan ID bilan bayt-bayt teng | `test_cross_tenant_object_returns_404`, `test_cross_tenant_is_indistinguishable_from_unknown_id` |
| T-01-77 | A tanlangan platforma admini B obyektiga 404; B tanlangach ayni chaqiruv 200 | `test_platform_admin_cannot_reach_the_unselected_market` |
| T-01-78 | Tasniflanmagan marshrut fail; istisno sababi va toifasi majburiy; OpenAPI pariteti | `test_no_unclassified_routes` (SABOTAJ bilan sinaldi), `test_exempt_routes_have_reason`, `test_route_walker_matches_openapi` |
| T-01-79 | Har bir tenant marshrutida 3 xil token holati -> 401 | `test_missing_token_is_rejected`, `test_malformed_token_is_rejected`, `test_expired_token_is_rejected` (21 test) |
| T-01-80 | CI'da alohida `SQL injection gate` qadami | `ruff check --select S608 .` -> toza; YAML parse bilan qadam nomi tasdiqlandi |
| T-01-81 | `Tenancy gate (FOUND-02)` alohida CI qadami + `npm run gate` mahalliy ekvivalenti | YAML parse; `test:tenancy` va `gate` skriptlari |

## User Setup Required

Yo'q. Testlar `.env` siz ishlaydi (testcontainers Postgres + Valkey ko'taradi):

```
docker compose --profile test run --rm tests pytest -q
```

To'liq faza darvozasi (frontend uchun `npm --prefix frontend ci` kerak):

```
npm run gate
```

## Next Phase Readiness

**Tayyor:**

- **2–7 fazalar:** yangi endpoint qo'shilganda hech narsa yozish shart emas — matritsa uni avtomatik qamraydi (401 × 3, sizish skaneri). Path parametri bo'lgan endpoint uchun `PARAM_FILLERS` ga bir satr kerak va uni unutib bo'lmaydi: CI marshrut nomini aytib yiqiladi.
- **Faza verifikatori:** `npm run gate` bitta buyruq; `tests/tenancy` majburiy yashil; `01-VALIDATION.md` to'ldirilgan va imzolangan.

**Ochiq e'tibor nuqtalari:**

- **01-09 ning ikki satri (`01-09-T1`, `01-09-T2`) VALIDATION.md da ⏳** — parallel to'lqinda bo'lgani uchun 01-10 ularni tekshira olmadi. Faza yopilishidan oldin tasdiqlanishi SHART.
- **`npm run gate` ning frontend qismi bir marta uchdan-uchiga ishga tushirilmagan** (yuqoridagi sababga ko'ra). Birlashuvdan keyingi birinchi to'liq `npm run gate` — verifikatorning ishi.
- **`PARAM_FILLERS` da hozircha bitta parametr turi bor** (`user_id`). 2-fazada `stall_id`, `vendor_id`, `payment_id` paydo bo'ladi; ularning har biri **B bozoriga tegishli** qiymat bo'lishi shart — `test_param_fillers_point_at_the_other_market` buni qulflaydi, aks holda matritsa 404 olib "yashil" bo'lardi-yu, hech nimani isbotlamasdi.
- **Yurish FastAPI ning ichki tuzilmasiga tayanadi.** FastAPI yangilanganda `test_route_walker_matches_openapi` birinchi bo'lib qizaradi — bu kutilgan signal, uni "flaky test" deb o'chirmaslik kerak.

## Self-Check: PASSED

- **Fayllar:** da'vo qilingan 9 ta artefaktning (2 yangi + 7 modifikatsiya) hammasi mavjud va git'da kuzatilmoqda (`git ls-files` bilan tasdiqlandi).
- **Commitlar:** `4c2a373`, `6dae551` — ikkalasi ham `git log` da mavjud.
- **O'chirilgan fayl yo'q:** `git diff --diff-filter=D --name-only 111e225..HEAD` bo'sh.
- **Umumiy artefaktlarga tegilmadi:** `git diff --name-only 111e225..HEAD -- .planning/STATE.md .planning/ROADMAP.md` BO'SH (worktree rejimi — ularni orkestrator yangilaydi).
- **`frontend/` ga tegilmadi:** `git diff --name-only 111e225..HEAD -- frontend` BO'SH (parallel agent egaligida).
- **Sabotaj qaytarildi:** `services/core-api/app/main.py` diffda YO'Q.
- **Ishchi katalog toza:** vaqtinchalik marshrut-zond fayli o'chirildi va commit qilinmadi.
- **Darvozalar:** `ruff check .` + `ruff format --check .` + `mypy .` (strict, 83 fayl) + `ruff check --select S608 .` + `pytest` (375 test) — hammasi yashil.
