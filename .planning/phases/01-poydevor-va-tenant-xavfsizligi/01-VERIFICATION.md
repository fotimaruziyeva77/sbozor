---
phase: 01-poydevor-va-tenant-xavfsizligi
verified: 2026-07-29T15:40:00Z
status: gaps_found
score: 19/25 must-haves verified
overrides_applied: 0
gaps:
  - truth: "Admin vaqtinchalik parol beradi va foydalanuvchi birinchi kirishda uni MAJBURIY almashtiradi (server tomonda ham)"
    status: failed
    reason: "must_change_password bayrog'i DB'dan o'qiladi, javoblarda qaytariladi va frontendda o'qiladi — lekin hech qanday backend dependency yoki endpoint uni TEKSHIRMAYDI. `Principal` dataclass'ida bu maydon umuman yo'q. `services/core-api/app/` bo'yicha `must_change` so'zi faqat o'qish/yozishda uchraydi, bironta ham qiyoslash (`if ... must_change_password`) yo'q. Ikkita frontend fayl serverda ham gate borligini da'vo qiladi — bu da'vo yolg'on."
    artifacts:
      - path: "services/core-api/app/deps.py"
        issue: "`Principal` da `must_change_password` maydoni yo'q; `get_current_principal` (242-292 qator) uni hech qachon tekshirmaydi va hech qaysi dependency (`require_permission`, `get_tenant_session`) ham tekshirmaydi"
      - path: "frontend/src/components/auth/change-password-form.tsx"
        issue: "21-qatordagi izoh: \"server yozuv endpointlarini parol almashtirilmaguncha rad etadi\" — bu kontrol MAVJUD EMAS"
      - path: "frontend/src/app/[locale]/(app)/layout.tsx"
        issue: "20-qatordagi izoh: \"Server tomonda ham yozuv endpointlari yopiq\" — bu ham yolg'on; faqat client-side redirect bor va u brauzersiz (to'g'ridan-to'g'ri API so'rovi bilan) butunlay chetlab o'tiladi"
    missing:
      - "`Principal.must_change_password: bool` maydoni"
      - "`require_password_current` (yoki tengdosh) dependency — `get_tenant_session` va yozuv endpointlarini `must_change_password=true` bo'lganda 403 bilan rad etadigan (faqat `/auth/change-password` va `/auth/logout` ochiq qoladi)"
      - "Integratsiya testi: `must_change_password=true` foydalanuvchi `GET /api/v1/users`, `POST /api/v1/users`, `GET /api/v1/audit` ga so'rov yuborganda 403 `password_change_required` olishi (hozirgi testlar faqat javobdagi bayroq qiymatini tekshiradi, endpoint bloklanishini emas)"

  - truth: "Platforma admini kirgach bozor tanlash ekranini ko'radi va tanlaganidan keyin panelga kiradi (D-06)"
    status: failed
    reason: "TanStack Query v5.101.4'da `enabled: false` bo'lgan so'rov abadiy `status: 'pending'` holatida qoladi (paket hujjatiga ko'ra `isPending` — \"hech qanday keshlangan ma'lumot yo'q va hali birorta urinish tugallanmagan\" degani, `isFetching`dan farqli). Asosiy yo'lda login javobi `markets` massivini to'ldiradi -> `markets.length > 0` -> so'rov `enabled=false` -> `marketsQuery.isPending` DOIM `true` -> `isBusy = selectMarket.isPending || marketsQuery.isPending` DOIM `true` -> HAR BIR bozor tugmasi `disabled`. Platforma admini (yoki 2+ bozorli foydalanuvchi) login qilib shu ekranga tushgach, hech qanday tugmani bosa olmaydi."
    artifacts:
      - path: "frontend/src/components/auth/market-picker.tsx"
        issue: "93-qator: `isBusy = selectMarket.isPending || marketsQuery.isPending` — o'chirilgan so'rovda ikkinchi shart doim true; 127-qator: `disabled={isBusy}` shu holatni tugmaga uzatadi"
    missing:
      - "`isBusy` hisobida `marketsQuery.isPending` o'rniga `marketsQuery.isLoading` (=`isFetching && isPending`) ishlatilishi"
      - "MarketPicker uchun komponent-darajasidagi render testi (hozirgi 37 frontend testining barchasi `node:test` sof-funksiya testlari — React render/interaction testi yo'q, shuning uchun bu sinf xato hech qachon avtomatik ushlanmagan)"

  - truth: "Boshqa bozorga urinish avtomatik testda rad etiladi — RLS bypass yo'li yo'q (D-06, ROADMAP mezon #1)"
    status: failed
    reason: "`POST /api/v1/users` da `_assert_roles_assignable()` faqat `principal.is_platform_admin=False` bo'lgan chaqiruvchini `{cashier, inspector}` bilan cheklaydi; `principal.is_platform_admin=True` bo'lgan chaqiruvchi uchun CHEKLOVSIZ qaytadi — jumladan `Role.PLATFORM_ADMIN` ham ruxsat etiladi. Natijada `user_market_roles.roles` da `'platform_admin'` bor, lekin `users.is_platform_admin=false` bo'lgan GIBRID hisob yaratiladi. Bu hisobning tokeni `roles=[\"platform_admin\"]` oladi -> `permissions_for()` orqali `MARKET_VIEW_ALL` huquqini oladi -> `GET /api/v1/markets` (huquq bo'yicha branch qiladi, `is_platform_admin` bayrog'i bo'yicha EMAS) unga `auth_list_markets_full()` orqali PLATFORMADAGI BARCHA bozorlarni (nom, timezone, holat) qaytaradi — bitta bozorga tegishli hisob uchun. Bu marshrut `tests/tenancy/test_cross_tenant.py` da `EXEMPT_ROUTES` ichida \"faqat platforma admini uchun\" sababi bilan istisno qilingan — bu sabab CR-03 tufayli endi noto'g'ri."
    artifacts:
      - path: "services/core-api/app/api/v1/users.py"
        issue: "`_assert_roles_assignable` (120-136 qator) `Role.PLATFORM_ADMIN` ni hech qachon rad etmaydi — faqat platforma-bo'lmagan chaqiruvchi cheklanadi"
      - path: "services/core-api/app/api/v1/markets.py"
        issue: "`list_markets` (58-82 qator) `Permission.MARKET_VIEW_ALL in principal.permissions` asosida branch qiladi, `principal.is_platform_admin` asosida EMAS"
      - path: "frontend/src/lib/api-types.ts"
        issue: "`assignableRoles(true)` `ROLES` (5 tasi, `platform_admin` bilan) qaytaradi — UI checkbox ro'yxatida platforma admini uchun `platform_admin` varianti ko'rinadi"
      - path: "frontend/scripts/role-gate.test.mjs"
        issue: "Ikkinchi test (\"Rollar ro'yxati sbozor_core.enums.Role bilan mos\") platforma admini BARCHA 5 rolni ko'rishini QULFLAYDI — zaiflik testda \"to'g'ri xulq\" sifatida qattiqlashtirilgan (men bu testni bevosita ishga tushirib tasdiqladim: 37/37 yashil, shu jumladan aynan shu test)"
    missing:
      - "`_assert_roles_assignable` da `Role.PLATFORM_ADMIN` HAR DOIM rad etilishi (u `users.is_platform_admin` bayrog'i orqali beriladi, a'zolik roli emas — `platform_admin` matnini `user_market_roles.roles` ga yozish tuzilmaviy noto'g'ri)"
      - "`GET /api/v1/markets` ni `principal.is_platform_admin` asosida (yoki huquq VA bayroq ikkalasi bilan) branch qilish"
      - "`role-gate.test.mjs`, `rbac.ts`/`api-types.ts` dagi mos yangilanish va `test_cross_tenant.py` EXEMPT_ROUTES izohini qayta ko'rib chiqish"

  - truth: "Login rate-limit va audit.ip haqiqiy mijoz IP'sini aks ettiradi, reverse-proxy manzilini emas"
    status: failed
    reason: "`compose.yaml` dagi `core-api` xizmati `uvicorn`ni `--proxy-headers`/`--forwarded-allow-ips` siz ishga tushiradi. `ops/nginx/nginx.conf` `X-Forwarded-For`ni to'g'ri yuboradi, lekin uvicorn buni ishonchsiz manbadan kelgan deb E'TIBORGA OLMAYDI (standart `--forwarded-allow-ips=127.0.0.1`, nginx esa boshqa konteyner IP'sida). Natijada `request.client.host` DOIM nginx konteynerining IP'siga teng. Oqibat ikki tomonlama: (1) IP-kesimidagi login sanagichi (`rl:login:ip:*`, 50/15daq) BUTUN PLATFORMA uchun BITTA umumiy kalitga aylanadi — tashqi anonim tomon ~51 so'rov bilan HAMMA foydalanuvchini 15 daqiqaga qulflab qo'yishi mumkin (parol tekshiruvidan OLDIN rad etiladi, ya'ni muvaffaqiyatli login bilan ham tozalanmaydi); (2) `audit_log.ip` har doim proxy manzilini yozadi — mahsulotning asosiy qadriyati (\"raqamlar va rasm-dalil bilan\" isbot) uchun \"kimdan\" savoli javobsiz qoladi."
    artifacts:
      - path: "compose.yaml"
        issue: "72-107 qator, `core-api` `command:` da `--proxy-headers` va `--forwarded-allow-ips` YO'Q"
      - path: "services/core-api/app/api/v1/auth.py"
        issue: "`_client_ip()` (116-137 qator) izohida \"ishonch qarori DEPLOY qatlamida\" deyiladi, lekin deploy qatlami (compose.yaml) bu shartni bajarmaydi"
    missing:
      - "`compose.yaml` core-api `command`iga `--proxy-headers --forwarded-allow-ips=<ishonchli tarmoq>` qo'shish (port tashqariga ochilmagani uchun `*` xavfsiz, lekin buni aniq hujjatlashtirish kerak)"
      - "Regressiya testi: turli `client` scope qiymatlari bilan ikkita so'rov ikkita MUSTAQIL `rl:login:ip:*` kalitini hosil qilishini tasdiqlovchi (hozirgi `httpx.ASGITransport` testlari proxyni butunlay chetlab o'tadi)"

  - truth: "market_id IS NULL audit qatorlari (masalan login_failed) platforma darajasida ko'rish yo'liga ega"
    status: failed
    reason: "`GET /api/v1/audit` faqat `TenantSessionDep` (tanlangan bozor GUC'i) bilan ishlaydi; `audit_read` policy'si `market_id = app.market_id` shaklida. `login_failed` kabi platforma-global yozuvlar `market_id=NULL` bilan yoziladi (ataylab — bozor noma'lum bo'lgan holatda uni taxmin qilish yolg'on dalil bo'lardi), shuning uchun ular HECH QANDAY tenant konteksti bilan mos kelmaydi va faqat test-superuser ulanishi bilan o'qiladi. Bu uch marta ketma-ket (01-06, 01-07, 01-09 SUMMARY) ochiq muammo sifatida hujjatlashtirilgan, lekin birorta reja ham uni o'z qamroviga olmagan — chunki har birining `<interfaces>` bo'limi `GET /audit`ni tenant-scoped deb e'lon qilgan."
    artifacts:
      - path: "services/core-api/app/api/v1/audit.py"
        issue: "`GET /audit` faqat `TenantSessionDep` bilan; platforma-global (`market_id IS NULL`) yozuvlarni ochadigan yo'l yo'q"
    missing:
      - "Alohida endpoint (masalan `GET /api/v1/audit/platform`) yoki `require_roles(PLATFORM_ADMIN)` ostidagi bayroq — `market_id IS NULL` yozuvlarni platforma admini uchun ochadigan `SECURITY DEFINER` funksiya orqali"
deferred: []
human_verification:
  - test: "01-08 Task 3'dagi 8 qadamlik va 01-09 Task 2'dagi 15 qadamlik `<human-check>` ketma-ketligini JONLI stek (`npm run up` + `npm run migrate` + `docker compose --profile web --profile proxy up -d`) bilan to'liq bajarish"
    expected: "Har bir qadam kutilgan natijani beradi (login, til almashtirish, audit ko'rinishi, DB-owner o'zgarmaslik namoyishi)"
    why_human: "Brauzer darajasidagi avtomatik test infratuzilmasi ushbu fazada yo'q (Playwright 8-fazaga qoldirilgan); vizual/UX oqimini faqat inson tasdiqlashi mumkin. DIQQAT: yuqoridagi CR-01 va CR-02 gaplari yopilmaguncha bu ketma-ketlik 3- va 8-qadamlarda muqarrar to'xtaydi (parol almashtirishni chetlab o'tish va bozor tanlash tugmalari o'chirilgan) — qayta urinishdan oldin gaplarni yopish tavsiya etiladi."
  - test: "uz-Cyrl xabar fayllaridagi imlo sifatini mutaxassis ko'zi bilan bir marta ko'rib chiqish (masalan `Ҳисоб`, `маъмурият`, `аъзоликлари` kabi so'zlar)"
    expected: "O'zbek kirill imlosi qoidalariga to'liq mos"
    why_human: "Avtomatik transliteratsiya generatori ICU/struktura darajasida test qilingan, lekin tilshunoslik sifati (imlo nafisligi) faqat inson tomonidan baholanadi — 01-02 va 01-08 SUMMARY ham buni tavsiya qilgan"
  - test: "AppShell mobil pastki navigatsiya va Apple-uslub dizayn talablariga (SBOZOR-MVP-texnik-topshiriq.md §7) vizual muvofiqlikni ko'rib chiqish"
    expected: "Kassir mobil oqimida barmoq nishonlari ≥44px, minimalist va kam-kontrastli ko'rinish"
    why_human: "Vizual dizayn sifati grep/test bilan o'lchanmaydi"
---

# Phase 1: Poydevor va tenant xavfsizligi — Verification Report

**Phase Goal:** Har foydalanuvchi o'z rolida, o'z bozorida, o'z tilida xavfsiz ishlaydi va har harakat o'chmas izda qoladi
**Verified:** 2026-07-29T15:40:00Z
**Status:** gaps_found
**Re-verification:** Yo'q — dastlabki tekshiruv

## Goal Achievement

### Umumiy xulosa

Ushbu faza ikki qatlamdan iborat: **DB/RLS qatlami** (Postgres RLS, `SECURITY DEFINER` funksiyalari, audit trigger'lari, moliyaviy konstraytlar) va **ilova qatlami** (FastAPI endpointlari, RBAC, frontend auth oqimi). Men SUMMARY.md da'volarini emas, haqiqiy kodni o'qidim, `docker compose --profile test run --rm tests pytest` (375 test) va to'liq frontend darvozasini (`typecheck`, `lint`, `test` 37/37, `i18n:check`, `build` — 24 SSG sahifa) o'zim ishga tushirdim, hamda 01-REVIEW.md da qayd etilgan 4 ta CRITICAL topilmani (CR-01…CR-04) mustaqil ravishda, kodni bevosita o'qish, `@tanstack/react-query` paketining rasmiy tip hujjatlarini tekshirish va `git log`da tuzatish commiti yo'qligini tasdiqlash orqali qayta tekshirdim.

**Natija: DB qatlami mustahkam va ishonchli isbotlangan — lekin ilova qatlamida 4 ta BLOCKER-darajali kamchilik bor**, ular SUMMARY.md fayllarida qayd etilmagan (chunki ular 01-REVIEW.md orqali, executor SUMMARY'laridan KEYIN topilgan) va hech qanday tuzatish commiti bilan yopilmagan (`git log` dagi eng so'nggi commit — `5495e27 docs(01): add code review report` — bu faqat hisobotning o'zi, kod o'zgarishi yo'q).

### Mustahkam qismlar (mustaqil tasdiqlangan)

- **RLS izolyatsiyasi (DB darajasida):** `NULLIF` fail-closed predikati, `ENABLE`+`FORCE`+policy har bir tenant jadvalida, `sbozor_app`/`sbozor_owner` `NOSUPERUSER NOBYPASSRLS`, composite FK bilan cross-tenant havola strukturaviy bloklangan. Barchasi sabotaj bilan sinalgan (NULLIF olib tashlansa test yiqiladi) — men buni kodni o'qib tasdiqladim, testlar esa mening ishga tushirishimda ham yashil.
- **Audit jurnali 4 qatlamli o'zgarmasligi:** GRANT/REVOKE, RLS policy yo'qligi, `BEFORE UPDATE/DELETE` va `BEFORE TRUNCATE` triggerlari — barchasi holat bo'yicha (exception emas) tekshirilgan va men buni kodda tasdiqladim.
- **JWT qattiqlashtirilishi:** `algorithms=["HS256"]` literal, `alg=none` va boshqa algoritm rad etiladi, tur almashtirish (access↔refresh) bloklangan, minimal kalit uzunligi xato (ogohlantirish emas).
- **375 backend test — men bevosita ishga tushirdim, 375 passed.** `ruff check`, `ruff format --check`, `mypy .` (strict, 83 fayl), `ruff check --select S608 .` — barchasi toza (men ishga tushirdim).
- **Frontend darvozasi — men bevosita ishga tushirdim:** `typecheck` (toza), `lint` (toza), `test` (37/37), `i18n:check` (120 kalit × 3 til), `build` (24 SSG sahifa).
- **Kodda debt-marker yo'q:** `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER`, `xfail`/`pytest.mark.skip` — men butun repo bo'yicha grep qildim, natija bo'sh.

### Aniqlangan BLOCKER'lar (mustaqil tasdiqlangan, tuzatilmagan)

Quyidagi to'rttasi 01-REVIEW.md (CR-01…CR-04) da qayd etilgan va men ularni kodni bevosita o'qib, alohida tekshiruvlar bilan mustaqil tasdiqladim (pastdagi Observable Truths jadvaliga qarang):

1. **CR-01 — D-02 (majburiy parol almashtirish) serverda umuman kuchga kirmaydi.** `Principal`da bu bayroq yo'q, hech qanday dependency uni tekshirmaydi. Vaqtinchalik parol egallagan har kim (masalan uni bergan admin) bu parolni HECH QACHON almashtirmasdan cheksiz foydalanishi mumkin.
2. **CR-02 — Bozor tanlash ekrani asosiy yo'lda ISHLAMAYDI.** TanStack Query v5 semantikasi bo'yicha o'chirilgan so'rov abadiy `isPending=true` qaytaradi; bu holat `isBusy`ga uzatilib, HAR BIR bozor tugmasini `disabled` qiladi. Platforma admini yoki ko'p-bozorli foydalanuvchi login qilgach panelga kira olmaydi.
3. **CR-03 — `platform_admin` bozor-darajasidagi rol sifatida beriladi.** Bu cross-tenant bozorlar ro'yxati oshkoralashuvini va buzuq gibrid hisobni yaratadi — va bu xatti-harakat `role-gate.test.mjs` tomonidan "to'g'ri" deb QULFLANGAN.
4. **CR-04 — Rate-limit va audit IP'si reverse-proxy manziliga bog'lanadi.** ~51 anonim so'rov bilan butun platformaning login imkoniyati 15 daqiqaga blokланishi mumkin; audit yozuvlaridagi IP har doim noto'g'ri.

Bularga qo'shimcha, uchinchi SUMMARY (01-06→01-07→01-09) bo'ylab ochiq qoldirilgan **market_id IS NULL audit qatorlari platformada ko'rinmaydi** muammosi ham bor (planner qaroriga muhtoj, ochiq deb hujjatlashtirilgan).

## Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | **[ROADMAP SC#1]** Foydalanuvchi o'z roli bilan kiradi va faqat o'z bozori ma'lumotini ko'radi — boshqa bozorga urinish avtomatik testda rad etiladi | ✗ FAILED | CR-01, CR-02, CR-03 uchtasi ham shu mezonni buzadi (pastga qarang) |
| 2 | **[ROADMAP SC#2]** Til bir bosishda o'zbek-lotin ↔ o'zbek-kirill ↔ rus orasida almashadi, interfeys to'liq tarjimada qoladi | ✓ VERIFIED | `locale-switcher.tsx` `router.replace` + `PATCH /api/v1/me`ni bitta bosishda bajaradi; men `i18n:check` (120 kalit × 3 til, ICU parity) va `build`ni (24 SSG) o'zim ishga tushirdim — ikkalasi ham toza |
| 3 | **[ROADMAP SC#3]** Har ma'muriy/moliyaviy harakatdan keyin audit jurnalida yozuv paydo bo'ladi va uni tahrirlab/o'chirib bo'lmaydi | ✓ VERIFIED (WARNING bilan) | `audit_log` 4 qatlamli o'zgarmasligi kodda va testda tasdiqlangan (men `test_audit_immutable.py`ni 375 ichida ishga tushirdim). LEKIN: CR-04 tufayli `audit_log.ip` har doim noto'g'ri va `market_id IS NULL` yozuvlar (5-qatorga qarang) hech kimga ko'rinmaydi — bular mezonning harfini buzmaydi (yozuv yaratiladi va o'zgarmas), lekin uning maqsadini (to'liq dalil) qisman zaiflashtiradi |
| 4 | **[ROADMAP SC#4]** Har sana Asia/Tashkent biznes-kuni bo'yicha, har summa butun so'mda; yarim tunda kun chegarasi to'g'ri suriladi | ✓ VERIFIED | `test_business_date.py` (19:30Z→ertangi kun chegara holati) va `test_money_constraints.py` men ishga tushirgan 375 ichida; `assert_safe_soum` `float`/`bool`ni rad etadi (kodda tasdiqlangan) |
| 5 | **[ROADMAP SC#5]** Moliyaviy jadvallar dublikat-himoyasi bilan tug'iladi (`UNIQUE(market_id, stall_id, business_date)`) — 6-fazadan oldin allaqachon o'rnida | ✓ VERIFIED | `financial_guards()` yordamchisi va uning probe-jadval testlari (`test_idempotency.py`) men ishga tushirgan to'plamda yashil; DDL to'rttasini ham chiqarishi kodda tasdiqlangan |
| 6 | [01-01] Ilova DB'ga faqat `NOSUPERUSER NOBYPASSRLS` `sbozor_app` roli bilan ulanadi | ✓ VERIFIED | `ops/db/init/01-roles.sql` o'qildi; `test_app_role_cannot_bypass_rls` 375 ichida yashil |
| 7 | [01-01] Testlar haqiqiy `postgres:18.4-trixie`ga qarshi `sbozor_app` bilan ishlaydi (SQLite emas) | ✓ VERIFIED | `tests/conftest.py` o'qildi — `PostgresContainer`, `sqlite` so'zi yo'q |
| 8 | [01-01] Repoda hech qanday sir commit qilinmagan | ✓ VERIFIED | `.env.example` o'qildi — faqat kalit nomlari, `CHANGEME` platsholderi |
| 9 | [01-04] Tenant kontekstisiz so'rov 0 qator qaytaradi, xato tashlamaydi (fail-closed) | ✓ VERIFIED | `TENANT_PREDICATE` = `NULLIF(current_setting(...), '')::uuid`; `test_rls_predicate.py` 375 ichida |
| 10 | [01-04] Cross-tenant havola composite FK bilan strukturaviy bloklangan | ✓ VERIFIED | `test_composite_fk.py` 375 ichida yashil |
| 11 | [01-04] Foydalanuvchi login RLS ostida `SECURITY DEFINER` funksiyalar orqali topiladi, BYPASSRLS talab qilinmaydi | ✓ VERIFIED | `migrations/entities/functions.py`, `test_login_bootstrap.py` |
| 12 | [01-05] ORM'ni chetlab o'tgan xom SQL ham audit yozuvini hosil qiladi | ✓ VERIFIED | `fn_audit_row()` DB-trigger (ORM hook emas); `test_raw_sql_is_audited` |
| 13 | [01-05] Audit jurnalini na ilova roli, na jadval egasi tahrirlay/o'chira olmaydi (TRUNCATE ham) | ✓ VERIFIED | `test_audit_immutable.py` — holat bo'yicha tekshiruv (`pytest.raises` emas) |
| 14 | [01-06] Noto'g'ri parol / mavjud bo'lmagan telefon / bloklangan foydalanuvchi bir xil javob beradi (enumeration yo'q) | ✓ VERIFIED | `test_login_no_user_enumeration` javob tanasini bayt-bayt taqqoslaydi |
| 15 | [01-06] O'g'irlangan refresh token qayta ishlatilsa butun token oilasi bekor qilinadi | ✓ VERIFIED | `test_refresh_reuse_detection` |
| 16 | [01-06] RBAC matritsasi kodda qat'iy; direktor rasta/tarif/xodim o'zgartira olmaydi (D-07) | ✓ VERIFIED | `rbac.py` o'qildi, `test_rbac_matrix.py` |
| 17 | [01-07] Admin vaqtinchalik parol beradi va foydalanuvchi birinchi kirishda uni **majburiy** almashtiradi (server tomonda) | ✗ FAILED | **CR-01** — batafsil pastda va gaps bo'limida |
| 18 | [01-07] Bozor admini `market_admin`/`director`/`platform_admin` roli bilan foydalanuvchi yarata OLMAYDI | ✓ VERIFIED (tor doirada) | `_assert_roles_assignable` bozor-admin chaqiruvchini `{cashier,inspector}`ga cheklaydi — bu aniq holat ishlaydi. LEKIN platforma-admin chaqiruvchi uchun bu cheklov yo'q (17-qatorga bog'liq emas, alohida — 22-qatorga qarang) |
| 19 | [01-08] Platforma admini kirgach bozor tanlash ekranini ko'radi va tanlaganidan keyin panelga kiradi | ✗ FAILED | **CR-02** — batafsil pastda va gaps bo'limida |
| 20 | [01-08] Access token faqat xotirada saqlanadi — `localStorage`/`sessionStorage` ishlatilmaydi | ✓ VERIFIED | `grep -rn "localStorage\|sessionStorage" frontend/src/` → bo'sh (men o'zim tekshirdim) |
| 21 | [01-09] Kassir va nazoratchi audit/foydalanuvchi bo'limini ko'rmaydi | ✓ VERIFIED | `require_permission(AUDIT_VIEW)`/`USER_VIEW` backend darajasida; `test_cashier_cannot_view_the_audit_log` |
| 22 | [01-10] Har bir tenant resurs marshruti `app.routes`dan avtomatik olinadi; qamrab olinmagan marshrut CI'ni yiqitadi | ✓ VERIFIED (tuynuk bilan) | `test_route_coverage.py` ishlaydi va sabotaj bilan sinalgan. LEKIN `GET /api/v1/markets` `EXEMPT_ROUTES`da — bu istisnoning asosi (23-qatorga qarang) CR-03 tufayli endi noto'g'ri |
| 23 | [Cross-cutting] `platform_admin` roli bozor-darajasidagi foydalanuvchiga BERILMAYDI (D-06 RLS bypass yo'q kafolatining amaliy holati) | ✗ FAILED | **CR-03** — batafsil pastda va gaps bo'limida; `role-gate.test.mjs` buni "to'g'ri" deb qulflagani men o'zim ishga tushirgan 37/37 testda tasdiqlandi |
| 24 | [Cross-cutting] Login rate-limit va `audit_log.ip` haqiqiy mijoz IP'sini aks ettiradi | ✗ FAILED | **CR-04** — batafsil pastda va gaps bo'limida |
| 25 | [Cross-cutting] `market_id IS NULL` audit qatorlari (masalan `login_failed`) platforma darajasida o'qish yo'liga ega | ✗ FAILED | 01-06→01-07→01-09 SUMMARY'larida uch marta ochiq deb qayd etilgan, hech kim yopmagan |

**Score:** 19/25 truths verified

### CR-01…CR-04 — mustaqil tasdiqlash tafsiloti

Men bularni faqat 01-REVIEW.md dan ko'chirmadim — har birini o'zim kod o'qib va/yoki ishga tushirib qayta isbotladim:

- **CR-01:** `grep -rn "must_change" services/core-api/app/` — barcha natijalar o'qish/yozish, bironta ham taqqoslash yo'q. `Principal` dataclass'ida maydon yo'q (`deps.py:110-128`). Mavjud test (`test_created_user_must_change_password_on_first_login`, `tests/integration/test_users_api.py:244`) faqat javobdagi bayroq qiymatini tekshiradi, endpoint bloklanishini emas.
- **CR-02:** `frontend/node_modules/@tanstack/query-core/build/modern/_tsup-dts-rollup.d.ts:1507-1509` — "Will be `pending` if there's no cached data and no query attempt was finished yet" — bu `isFetching`dan mustaqil. `market-picker.tsx:93` da aynan shu maydon `isBusy`ga uzatiladi.
- **CR-03:** `services/core-api/app/api/v1/users.py:120-136` (`_assert_roles_assignable`) va `services/core-api/app/api/v1/markets.py:58-82` (`list_markets`) o'qildi — ikkalasi ham tasdiqlaydi. `frontend/scripts/role-gate.test.mjs`ni men bevosita ishga tushirdim (`npm --prefix frontend run test`) — 37/37 yashil, shu jumladan bu zaiflikni "to'g'ri xulq" sifatida tasdiqlovchi test.
- **CR-04:** `compose.yaml:78-79` (`core-api` command) va `ops/nginx/nginx.conf:23` o'qildi — nginx `X-Forwarded-For` yuboradi, lekin uvicorn buyrug'ida `--proxy-headers`/`--forwarded-allow-ips` yo'q.

Bittasi ham tuzatilmagan: `git log --oneline -20` dagi eng so'nggi commit `5495e27 docs(01): add code review report` — faqat hisobot qo'shilgan, kodga tegilmagan.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `compose.yaml` | db/cache/core-api/frontend/nginx/migrate/tests servislari | ✓ VERIFIED | Mavjud; `docker compose config --quiet` men ishga tushirdim — exit 0. LEKIN `core-api` command'ida `--proxy-headers` yo'q (CR-04) |
| `ops/db/init/01-roles.sql` | `NOBYPASSRLS` ikki rol | ✓ VERIFIED | O'qildi, mavjud |
| `tests/conftest.py` | testcontainers + `sbozor_app` fixture | ✓ VERIFIED | O'qildi, mavjud, 375 test undan foydalanadi |
| `packages/sbozor-core/sbozor_core/security.py` | Argon2id + JWT | ✓ VERIFIED | O'qildi; `algorithms=["HS256"]` literal tasdiqlandi |
| `migrations/versions/0001_identity.py`…`0004_user_admin.py` | 4 migratsiya, RLS+GRANT | ✓ VERIFIED | Mavjud; `alembic upgrade head` orqali qurilgan holat 375 testda ishlatiladi |
| `migrations/entities/triggers.py` | `fn_audit_row`, `audit_immutable` | ✓ VERIFIED | O'qildi, `SECURITY DEFINER` emasligi tasdiqlandi |
| `services/core-api/app/deps.py` | Principal, tenant sessiya, RBAC dependency | ⚠️ ORPHANED MAYDON | Mavjud va ishlaydi, LEKIN `must_change_password` maydoni yo'q (CR-01) |
| `services/core-api/app/security/rbac.py` | ROLE_PERMISSIONS matritsasi | ✓ VERIFIED | O'qildi, D-07 (direktor cheklovi) tasdiqlandi |
| `services/core-api/app/api/v1/users.py` | D-04 ikki bosqichli boshqaruv | ⚠️ STUB-LIKE GAP | Bozor-admin yo'li ishlaydi; platforma-admin yo'lida `platform_admin` roli cheklanmagan (CR-03) |
| `services/core-api/app/api/v1/markets.py` | D-06 bozorlar ro'yxati | ⚠️ WIRING GAP | `MARKET_VIEW_ALL` huquqiga, `is_platform_admin` bayrog'iga emas bog'langan (CR-03 sababi) |
| `services/core-api/app/security/ratelimit.py` | Login rate-limit | ✓ VERIFIED (mustaqil) | Mantiq to'g'ri yozilgan — muammo bu faylda emas, `_client_ip()` manba ma'lumotida (CR-04) |
| `frontend/src/lib/api-client.ts` | apiFetch, single-flight refresh | ✓ VERIFIED | O'qildi, `credentials:'include'` bor |
| `frontend/src/lib/auth-store.ts` | xotira-only sessiya | ✓ VERIFIED | `grep` bilan localStorage/sessionStorage yo'qligi tasdiqlandi |
| `frontend/src/components/auth/market-picker.tsx` | D-06 bozor tanlash | ✗ BROKEN | Mavjud, kompilyatsiya bo'ladi, LEKIN asosiy yo'lda ishlamaydi (CR-02) |
| `frontend/src/components/shell/locale-switcher.tsx` | Bir bosishli til almashtirgich | ✓ VERIFIED | `router.replace` + `PATCH /api/v1/me` ikkalasi ham mavjud |
| `frontend/src/components/users/create-user-dialog.tsx` | D-04/D-05 UI ko'zgusi | ⚠️ WIRING GAP | `assignableRoles()` orqali to'g'ri ulangan, LEKIN backend bilan birga zaiflikni meros qiladi (CR-03) |
| `tests/tenancy/test_cross_tenant.py` | `app.routes`dan avtomatik matritsa | ✓ VERIFIED (tuynuk bilan) | 44 test, ishlaydi; `/markets` EXEMPT_ROUTES asosi endi noto'g'ri |
| `tests/tenancy/test_route_coverage.py` | qamrov darvozasi, xfail/skip yo'q | ✓ VERIFIED | `grep -rn "xfail\|pytest.mark.skip" tests/` → bo'sh |
| `.planning/phases/.../01-VALIDATION.md` | to'liq validatsiya kontrakti | ✓ VERIFIED | O'qildi, `nyquist_compliant: true`, 28 tasklik xarita to'liq |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `compose.yaml` | `ops/db/init/01-roles.sql` | `docker-entrypoint-initdb.d` volume | ✓ WIRED | Kod va test bilan tasdiqlangan |
| `migrations/versions/0001_identity.py` | `migrations/entities/policies.py` | `op.create_entity(tenant_policy(...))` | ✓ WIRED | `alembic revision --autogenerate` bo'sh diff beradi (SUMMARY da'vosi, kod bilan mos) |
| `services/core-api/app/api/v1/auth.py` | `auth_find_login` SECURITY DEFINER | `auth_repo.find_login(phone)` | ✓ WIRED | O'qildi, testlar yashil |
| `services/core-api/app/deps.py` | Valkey `user:state:{id}` keshi | `GET/SET, TTL 30s` | ✓ WIRED | `_is_user_active` orqali tasdiqlandi |
| `frontend/src/lib/queries.ts` | `POST /api/v1/users` | `useCreateUser` | ✓ WIRED | O'qildi |
| `frontend/src/app/[locale]/(app)/audit/page.tsx` | `GET /api/v1/audit` | `useAuditQuery` (keyset cursor) | ✓ WIRED | Tenant-scoped qismi uchun ishlaydi; platforma-global (`market_id IS NULL`) qismi uchun bog'lanish YO'Q (25-qator) |
| `services/core-api/app/api/v1/users.py` | RBAC (D-04 rol darajasi) | `_assert_roles_assignable` | ⚠️ PARTIAL | Bozor-admin yo'li WIRED; platforma-admin yo'li cheklovsiz (CR-03) |
| `frontend/src/components/auth/market-picker.tsx` | `POST /api/v1/auth/select-market` | `selectMutation.mutate` | ⚠️ WIRED, LEKIN ERISHIB BO'LMAYDIGAN | So'rovning o'zi to'g'ri ulangan; UI holati (`isBusy`) uni bosib bo'lmaydigan qiladi (CR-02) |
| `services/core-api/app/api/v1/auth.py` (`_client_ip`) | `request.client.host` | uvicorn `--proxy-headers` (KUTILGAN) | ✗ NOT WIRED | Deploy qatlami (compose.yaml) bu bayroqni bermaydi (CR-04) |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|---------------------|--------|
| `market-picker.tsx` | `options` (bozorlar ro'yxati) | Login javobidagi `markets` massivi (haqiqiy DB ma'lumoti, `auth_memberships`/`auth_list_markets` orqali) | Ha — ma'lumot HAQIQIY va to'g'ri keladi | ⚠️ MAXSUS HOLAT: ma'lumot oqimi TO'G'RI (hollow emas), lekin `isBusy` boshqaruv holati noto'g'ri hisoblangani uchun foydalanuvchi bu haqiqiy ma'lumot bilan HECH QANDAY o'zaro ta'sirga kira olmaydi (tugmalar doim `disabled`). Bu klassik "hollow prop" emas — bu "wired + real data + broken control-flow gate" holati (CR-02) |
| `audit-list.tsx` | `items` (audit yozuvlari) | `GET /api/v1/audit` → `AuditRepository.list_audit()` → RLS ostidagi haqiqiy `audit_log` so'rovi | Ha — real DB so'rovi, statik/bo'sh qaytarish yo'q | ✓ FLOWING (tenant-scoped qism uchun). Platforma-global (`market_id IS NULL`) qatorlar uchun manba yo'q — bu DISCONNECTED emas, chunki hech qanday UI elementi bu ma'lumotni so'ramaydi (backend endpointi yo'q) |
| `user-list.tsx` | `members` | `GET /api/v1/users` → `UserRepository.list_members()` → ikki qatlamli RLS+SECURITY DEFINER so'rov | Ha | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Backend to'liq test to'plami | `docker compose --profile test run --rm tests pytest` | `375 passed in 44.68s` | ✓ PASS |
| Ruff/format/mypy/S608 darvozalari | `docker compose --profile test run --rm tests sh -c "ruff check . && ruff format --check . && mypy . && ruff check --select S608 ."` | Barchasi toza | ✓ PASS |
| Frontend typecheck | `npm --prefix frontend run typecheck` | Xatosiz | ✓ PASS |
| Frontend lint | `npm --prefix frontend run lint` | Xatosiz | ✓ PASS |
| Frontend unit testlari | `npm --prefix frontend run test` | `tests 37, pass 37, fail 0` | ✓ PASS |
| i18n parity/drift darvozasi | `npm --prefix frontend run i18n:check` | `120 kalit × 3 til — kalit va ICU parity to'liq` | ✓ PASS |
| Frontend production build | `npm --prefix frontend run build` | `24` sahifa SSG, muvaffaqiyatli | ✓ PASS |
| `docker compose config` validligi | `docker compose config --quiet` | exit 0 | ✓ PASS |
| CR-01: must_change_password enforcement | `grep -rn "must_change" services/core-api/app/` | Faqat o'qish/yozish, taqqoslash yo'q | ✗ FAIL (gap tasdiqlandi) |
| CR-02: TanStack Query isPending semantikasi | `.d.ts` fayl o'qildi | "pending" holati `isFetching`dan mustaqil | ✗ FAIL (gap tasdiqlandi) |
| CR-03: role-gate test | `npm --prefix frontend run test` (ichida) | Platforma admini 5 rolni ko'rishi "to'g'ri" deb tasdiqlangan | ✗ FAIL (gap tasdiqlandi) |
| CR-04: uvicorn proxy-headers | `compose.yaml` o'qildi | Bayroq yo'q | ✗ FAIL (gap tasdiqlandi) |
| Debt-marker skanı | `grep -rn "TBD\|FIXME\|XXX\|TODO\|HACK\|PLACEHOLDER"` | Bo'sh | ✓ PASS |
| xfail/skip skanı | `grep -rn "xfail\|pytest.mark.skip" tests/` | Bo'sh | ✓ PASS |

### Probe Execution

SKIPPED — bu fazada `scripts/*/tests/probe-*.sh` konventsiyasi yoki PLAN/SUMMARY'da probe-asoslangan tekshiruv e'lon qilinmagan (bu migratsiya/CLI vositasi fazasi emas).

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|--------------|--------|----------|
| FOUND-01 | 01-03, 01-04, 01-06, 01-07, 01-08, 01-09 | Foydalanuvchi rolga mos kirish oladi (RBAC); har rol faqat o'z bozorini ko'radi | ✗ BLOCKED | RBAC matritsasining o'zi mustahkam (16-qator VERIFIED), lekin CR-01 (majburiy parol almashtirish yo'q), CR-02 (bozor tanlash ishlamaydi) va CR-03 (platform_admin roli noto'g'ri berilishi) uchtasi ham FOUND-01ning "xavfsiz kirish" va'dasini buzadi |
| FOUND-02 | 01-01, 01-04, 01-10 | Tenant izolyatsiyasi: RLS + avtomatik cross-tenant test | ✗ BLOCKED (qisman) | DB-darajadagi RLS mukammal isbotlangan (9-11, 22-qatorlar VERIFIED). Ilova-darajasida CR-03 orqali bitta aniq yo'l (bozor ro'yxati) cross-tenant oshkoralashadi va bu `test_cross_tenant.py` tomonidan avtomatik ushlanmaydi (aksincha, boshqa test uni "to'g'ri" deb tasdiqlaydi) |
| FOUND-03 | 01-05, 01-06, 01-07, 01-09 | Har ma'muriy/moliyaviy harakat audit jurnaliga yoziladi; jurnal o'zgarmas | ✓ SATISFIED (WARNING bilan) | Yozuv+o'zgarmaslik yadrosi mustahkam va testlangan. CR-04 (IP korruptsiyasi) va `market_id IS NULL` ko'rinmasligi (25-qator) mezonning harfini buzmaydi, lekin dalil sifatini kamaytiradi |
| FOUND-04 | 01-02, 01-07, 01-08, 01-09 | Interfeys 3 tilda; til bir bosishda almashadi | ✓ SATISFIED | To'liq tekshirilgan, hech qanday BLOCKER topilmadi; men build/test/i18n:check ni o'zim ishga tushirdim |
| FOUND-05 | 01-03, 01-05 | Biznes-kun Asia/Tashkent bo'yicha; pul butun so'mda | ✓ SATISFIED | Keng testlangan (chegara holatlari, konstraytlar); men testlarni ishga tushirdim |

**Orphaned requirements:** Yo'q. REQUIREMENTS.md Phase 1 uchun aynan FOUND-01…FOUND-05ni belgilaydi va barchasi kamida bitta reja frontmatterida `requirements:` sifatida e'lon qilingan.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `services/core-api/app/deps.py` | 110-128, 242-292 | Yetishmayotgan nazorat — `Principal`da `must_change_password` yo'q, hech qanday dependency uni tekshirmaydi | 🛑 BLOCKER | CR-01: majburiy parol almashtirish (D-02) serverda kuchga kirmaydi |
| `frontend/src/components/auth/market-picker.tsx` | 93, 127 | Mantiq xatosi — `isFetching`/`isLoading` o'rniga `isPending` ishlatilgan | 🛑 BLOCKER | CR-02: bozor tanlash tugmalari asosiy yo'lda doimiy `disabled` |
| `services/core-api/app/api/v1/users.py` | 120-136 | Yetishmayotgan validatsiya — `Role.PLATFORM_ADMIN` hech qachon rad etilmaydi | 🛑 BLOCKER | CR-03: cross-tenant bozorlar ro'yxati oshkoralashuvi + buzuq gibrid hisob |
| `compose.yaml` | 78-79 | Yetishmayotgan deploy bayrog'i — `--proxy-headers`/`--forwarded-allow-ips` yo'q | 🛑 BLOCKER | CR-04: rate-limit va audit IP'si reverse-proxy manziliga bog'lanadi |
| `packages/sbozor-core/sbozor_core/logging.py` | 67-82 | Rekursiv bo'lmagan sir-maskalash protsessori | ⚠️ WARNING | Ichma-ich lug'at/ro'yxat ichidagi sirlar (masalan `payload={"password":...}`) stdout/Sentry'ga chiqib ketishi mumkin (WR-01, men kodni o'qib tasdiqladim) |
| 6 ta fayl (`auth-store.ts`, `login-form.tsx`, `temp-password-dialog.tsx`, `audit-diff.tsx`, `locale-switcher.tsx`, `test_route_coverage.py`) | turli | Kod izohlarida "grep darvozasi bilan qulflangan" deb da'vo qilingan, lekin bunday CI qadami/skript mavjud emas | ⚠️ WARNING | Regressiya himoyasi hujjatlashtirilmagan afsona; hozirgi holat to'g'ri (men `grep` bilan tekshirdim — natija bo'sh), lekin bu CI'da mustahkamlanmagan (WR-05) |
| `tests/unit/test_enums.py` | 44 | `pytest.skip` fayl mavjudligiga qarab (jimgina o'tkazib yuboradi) | ℹ️ INFO | `routing.ts` ko'chirilsa/nomlansa, locale-parity darvozasi jimgina yashil bo'lib qoladi (IN-04, men tasdiqladim) |

## Human Verification Required

### 1. To'liq 8+15 qadamlik uchidan-uchiga jonli tekshiruv

**Test:** `npm run up`, `npm run migrate`, `docker compose --profile web --profile proxy up -d` bilan stekni ko'tarib, 01-08 Task 3 (8 qadam) va 01-09 Task 2 (15 qadam) dagi `<human-check>` ro'yxatlarini to'liq bajarish.
**Expected:** Login, til almashtirish, audit ko'rinishi, DB-owner o'zgarmaslik namoyishi — barchasi kutilgan natijani beradi.
**Why human:** Brauzer-darajasidagi avtomatik test infratuzilmasi bu fazada yo'q (Playwright 8-fazaga qoldirilgan). **Muhim eslatma:** yuqoridagi CR-01 va CR-02 gaplari yopilmaguncha bu ketma-ketlik muqarrar ravishda 3- va 8-qadamlarda to'xtaydi — birinchisi parol almashtirishni chetlab o'tish imkoniyati tufayli (aslida "davom etadi", lekin xavfsizlik nazariy jihatdan teshik), ikkinchisi esa bozor tanlash tugmalari butunlay bosilmasligi tufayli (bu holda jarayon LITERALLY to'xtaydi). Gaplarni yopgandan keyin qayta urinish tavsiya etiladi.

### 2. uz-Cyrl imlo sifati

**Test:** Kirill xabar fayllaridagi transliteratsiya natijasini (`Ҳисоб`, `маъмурият`, `аъзоликлари` kabi so'zlar) o'zbek tili mutaxassisi ko'zdan kechirishi.
**Expected:** O'zbek kirill imlosi qoidalariga to'liq mos.
**Why human:** Avtomatik generator faqat struktura/ICU darajasida test qilingan; tilshunoslik sifati inson bahosini talab qiladi.

### 3. Vizual/UX muvofiqlik

**Test:** AppShell mobil pastki navigatsiyasi va Apple-uslub minimal dizayn (SBOZOR-MVP-texnik-topshiriq.md §7) talablariga muvofiqlikni ko'rish.
**Expected:** Kassir mobil oqimida barmoq nishonlari ≥44px, minimalist va kam-kontrastli ko'rinish.
**Why human:** Vizual dizayn sifati kod tekshiruvi bilan o'lchanmaydi.

## Gaps Summary

Ushbu faza **ikki aniq qatlamga** bo'linadi va ular BUTUNLAY boshqacha ishonchlilik darajasiga ega:

**1) DB/RLS/audit-immutability yadrosi (01-01, 01-03, 01-04, 01-05) — MUSTAHKAM.** Men bu qatlamning har bir asosiy da'vosini kodni o'qib va testlarni bevosita ishga tushirib tasdiqladim. Bu yerda hech qanday BLOCKER topilmadi. Bu SBOZORning "band, lekin to'lovsiz" ishonch modelining eng muhim texnik poydevori va u juda yaxshi qurilgan.

**2) Ilova qatlami (01-06, 01-07, 01-08, 01-09) — 4 ta BLOCKER bilan.** Bu qatlamda test qamrovi keng (270+ integratsiya testi), lekin barcha testlar "aytilgan xatti-harakat sodir bo'ladimi" ni tekshiradi, "aytilmagan holat sodir BO'LMAYDIMI" ni emas:

- **CR-01** — hech bir test `must_change_password=true` foydalanuvchining boshqa endpointga kira olish-olmasligini tekshirmagan (faqat javobdagi bayroq qiymatini tekshirgan).
- **CR-02** — React komponent-darajasidagi render/interaction testi umuman yo'q (barcha 37 frontend testi sof `node:test` mantiq testlari); shuning uchun "tugma bosilishi mumkinmi" kabi UI-holat xatosi hech qachon avtomatik ushlanmagan.
- **CR-03** — mavjud test (`role-gate.test.mjs`) aslida MUAMMONI "to'g'ri xulq" sifatida QULFLAGAN — bu eng xavfli holat, chunki test yashil bo'lgani hech narsani isbotlamaydi.
- **CR-04** — testlar `httpx.ASGITransport` orqali proxy'ni butunlay chetlab o'tadi, shuning uchun deploy-darajasidagi (compose.yaml) muammo hech qachon ko'rinmagan.

Bularning barchasi **01-REVIEW.md** da avval topilgan va men ularni mustaqil ravishda, kodni bevosita o'qib va (imkon qadar) ishga tushirib qayta tasdiqladim — birortasi ham noto'g'ri signal (false positive) emas edi.

**3) Ochiq, hujjatlashtirilgan, hali yopilmagan bo'shliq:** `market_id IS NULL` audit qatorlari (`login_failed` va h.k.) platforma darajasida ko'rinmaydi. Bu uch marta (01-06→01-07→01-09) ketma-ket qayd etilgan, lekin hech bir reja o'z qamroviga olmagan, chunki har birining `<interfaces>` bo'limi keyingi rejaga havola qilgan.

**Tavsiya:** Fazani yopishdan oldin kamida CR-01, CR-02 va CR-03 uchun yopish rejasi (`/gsd-plan-phase 1 --gaps`) tuzilishi kerak — bular ROADMAP muvaffaqiyat mezoni #1ni ("boshqa bozorga urinish avtomatik testda rad etiladi") to'g'ridan-to'g'ri buzadigan, ishlab chiqarishga chiqarilsa haqiqiy foydalanuvchilarga ta'sir qiladigan nuqsonlardir. CR-04 va market_id-null bo'shlig'i uchun ham yopish rejasi tavsiya etiladi, garchi ular birinchi uchtadan kamroq shoshilinch bo'lsa-da.

---

_Verified: 2026-07-29T15:40:00Z_
_Verifier: Claude (gsd-verifier)_
