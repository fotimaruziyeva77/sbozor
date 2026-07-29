---
phase: 01-poydevor-va-tenant-xavfsizligi
verified: 2026-07-29T21:15:00Z
status: human_needed
score: 25/25 must-haves verified
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 19/25
  gaps_closed:
    - "CR-01 — Admin vaqtinchalik parol beradi va foydalanuvchi birinchi kirishda uni MAJBURIY almashtiradi (server tomonda ham)"
    - "CR-02 — Platforma admini kirgach bozor tanlash ekranini ko'radi va tanlaganidan keyin panelga kiradi (D-06)"
    - "CR-03 — Boshqa bozorga urinish avtomatik testda rad etiladi — RLS bypass yo'li yo'q (D-06, ROADMAP mezon #1)"
    - "CR-04 — Login rate-limit va audit.ip haqiqiy mijoz IP'sini aks ettiradi, reverse-proxy manzilini emas"
    - "Gap 5 — market_id IS NULL audit qatorlari platforma darajasida o'qish yo'liga ega (backend+API to'liq; frontend UI 8-fazaga ATAYIN va OCHIQ qoldirilgan — known stub, gap emas)"
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "01-08 Task 3'dagi 8 qadamlik va 01-09 Task 2'dagi 15 qadamlik `<human-check>` ketma-ketligini JONLI stek (`npm run up` + `npm run migrate` + `docker compose --profile web --profile proxy up -d`) bilan to'liq bajarish"
    expected: "Har bir qadam kutilgan natijani beradi (login, til almashtirish, audit ko'rinishi, DB-owner o'zgarmaslik namoyishi)"
    why_human: "Brauzer darajasidagi avtomatik test infratuzilmasi ushbu fazada yo'q (Playwright 8-fazaga qoldirilgan); vizual/UX oqimini faqat inson tasdiqlashi mumkin. YANGILANDI: bu qayta tekshiruvda CR-01 (parol darvozasi) va CR-02 (bozor tanlash tugmalari) ikkalasi ham kodda va testda mustaqil tasdiqlangan holda TUZATILGAN — 3-qadam (parol almashtirishni chetlab o'tish) va 8-qadam (bozor tugmalari doimiy o'chirilgan) endi ketma-ketlikni TO'XTATMASLIGI kerak. Shunga qaramay to'liq 8+15 qadamlik vizual/UX oqimi hali INSON tomonidan bajarilmagan — shuning uchun bu band ochiq qolmoqda."
  - test: "uz-Cyrl xabar fayllaridagi imlo sifatini mutaxassis ko'zi bilan bir marta ko'rib chiqish (masalan `Ҳисоб`, `маъмурият`, `аъзоликлари` kabi so'zlar)"
    expected: "O'zbek kirill imlosi qoidalariga to'liq mos"
    why_human: "Avtomatik transliteratsiya generatori ICU/struktura darajasida test qilingan (men `i18n:check`ni o'zim ishga tushirdim — 120 kalit × 3 til, drift yo'q), lekin tilshunoslik sifati (imlo nafisligi) faqat inson tomonidan baholanadi. Gap-closure to'lqini bu fayllarga tegmadi — o'zgarish yo'q."
  - test: "AppShell mobil pastki navigatsiya va Apple-uslub dizayn talablariga (SBOZOR-MVP-texnik-topshiriq.md §7) vizual muvofiqlikni ko'rib chiqish"
    expected: "Kassir mobil oqimida barmoq nishonlari ≥44px, minimalist va kam-kontrastli ko'rinish"
    why_human: "Vizual dizayn sifati grep/test bilan o'lchanmaydi. Gap-closure to'lqini bu qismga tegmadi — o'zgarish yo'q."
---

# Phase 1: Poydevor va tenant xavfsizligi — Qayta tekshiruv hisoboti

**Phase Goal:** Har foydalanuvchi o'z rolida, o'z bozorida, o'z tilida xavfsiz ishlaydi va har harakat o'chmas izda qoladi
**Verified:** 2026-07-29T21:15:00Z
**Status:** human_needed
**Re-verification:** Ha — 5 ta gap-closure rejasi (01-11…01-15) bajarilgandan keyin

## Umumiy xulosa

Bu — dastlabki tekshiruvda (2026-07-29T15:40:00Z, `gaps_found`, 19/25) topilgan **5 ta gapning** qayta tekshiruvi. Har bir gap uchun men SUMMARY.md da'vosini emas, **haqiqiy kodni** o'qidim, **testlarni o'zim ishga tushirdim** va CR-01 uchun **mustaqil sabotaj testi** o'tkazdim (darvozani vaqtincha olib tashlab, mos testning haqiqatan qizarishini tasdiqladim, so'ng `git checkout` bilan aynan asl holatga qaytardim).

**Natija: barcha 5 gap kod darajasida GENUINE ravishda yopilgan.** Hech qanday regressiya topilmadi. Uchta xavf-ostidagi RBAC testi (`test_inspector_cannot_view_the_audit_log`, `test_director_can_view_the_audit_log`, `test_cashier_and_director_cannot_manage_users`) hamon ASL RBAC da'volarini (`{"detail": "forbidden"}`) isbotlaydi — birortasi ham `password_change_required`ni qabul qilish uchun bo'shashtirilmagan. Audit jurnalining 4 qatlamli o'zgarmasligi (`audit_read_platform` policy qo'shilgandan keyin ham) but unligicha qoladi: men `migrations/entities/policies.py`ni bevosita o'qib `audit_log` da AYNAN 3 ta policy borligini (`audit_append` FOR INSERT, `audit_read` FOR SELECT, `audit_read_platform` FOR SELECT TO sbozor_owner) va FOR ALL/UPDATE/DELETE policy'si YO'Qligini tasdiqladim.

**Men mustaqil ishga tushirgan tekshiruvlar:**
- Backend to'liq to'plami: **416 passed** (docker orqali o'zim ishga tushirdim, nuqta-sanoq bilan tasdiqladim — 0 F/E/s/x belgisi)
- `ruff check` + `ruff format --check` + `mypy .` (87 fayl) + `ruff check --select S608` — barchasi toza
- Frontend: `typecheck` (toza), `lint` (toza), `test` (node:test 38/38 + vitest 3/3), `i18n:check` (120×3, drift yo'q), `build` (24 SSG sahifa) — hammasi men o'zim ishga tushirdim
- `docker compose config --quiet` — ikkalasi ham (override bilan va bazaviy `-f compose.yaml` bilan) `--proxy-headers`/`--forwarded-allow-ips` ko'rsatadi; `core-api`da `ports:` yo'q
- **Mustaqil sabotaj:** `get_tenant_session`dagi `CurrentPasswordDep`ni `PrincipalDep`ga vaqtincha almashtirdim → aynan 2 ta test (`test_session_endpoint_is_gated_too`, `test_admin_password_reset_locks_the_live_session_immediately`) qizardi, qolgan 6 tasi (boshqa ikki mustaqil qatlam — `require_permission`/`require_roles` — orqali) yashil qoldi. Bu darvozaning UCH JOYDA mustaqil ulanganini (defense-in-depth) isbotladi. `git checkout` bilan darhol qaytardim, `git status` toza.
- `git diff --name-only 5ed238e..HEAD` — 5 ta gap-closure rejasining birlashgan `files_modified` ro'yxati bilan AYNAN mos, hech qanday yashirin fayl yo'q
- Barcha da'vo qilingan commit hashlar (`d250b1e`, `4b2d43a`, `368d557`, `2e91adf`, `93ca25d`, `820ae36`, `765dd18`, `9d77b2c`) `git log`da mavjud

**Disconfirmation pass (Confirmation Bias Counter) — nima haligacha OCHIQ:** WR-05 ("grep darvozasi" deb da'vo qilingan, lekin mavjud bo'lmagan skript — 4 faylda hamon bor) va WR-07 (root `gate` skripti hamon `npm --prefix frontend test`ni chaqirmaydi) — ikkalasi ham original 01-REVIEW.md WARNING darajasida qayd etilgan, 5 gapning tarkibiga kirmagan va gap-closure to'lqini ularga tegmagan. Ular BLOKER emas va ushbu qayta tekshiruv mandatidan tashqarida, lekin to'liqlik uchun pastda qayd etilgan.

## Observable Truths (yangilangan)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | **[ROADMAP SC#1]** Foydalanuvchi o'z roli bilan kiradi va faqat o'z bozori ma'lumotini ko'radi — boshqa bozorga urinish avtomatik testda rad etiladi | ✓ VERIFIED | CR-01, CR-02, CR-03 uchtasi ham yopildi (pastga qarang) — hech qanday BLOKER qolmadi |
| 2 | **[ROADMAP SC#2]** Til bir bosishda o'zbek-lotin ↔ o'zbek-kirill ↔ rus orasida almashadi, interfeys to'liq tarjimada qoladi | ✓ VERIFIED | O'zgarmadi. Men `i18n:check` (120×3, ICU parity) va `build`ni (24 SSG) qayta ishga tushirdim — ikkalasi ham toza |
| 3 | **[ROADMAP SC#3]** Har ma'muriy/moliyaviy harakatdan keyin audit jurnalida yozuv paydo bo'ladi va uni tahrirlab/o'chirib bo'lmaydi | ✓ VERIFIED | CR-04 (IP korruptsiyasi) endi tuzatilgan — `audit_log.ip` haqiqiy mijoz manzilini yozadi (men `test_rate_limit_proxy.py`ni ishga tushirdim). Gap 5 backend qismi ham yopildi — `market_id IS NULL` qatorlar endi `GET /api/v1/audit/platform` orqali o'qiladi (`test_audit_platform.py`, 12/12). 4-qatlamli o'zgarmaslik `audit_read_platform` policy qo'shilgandan keyin ham but: men `policies.py`ni o'qib `audit_log`da FAQAT 3 policy (append/read/read_platform, barchasi INSERT yoki SELECT) borligini, FOR ALL/UPDATE/DELETE yo'qligini tasdiqladim; `test_audit_immutable.py` 7/7 yashil |
| 4 | **[ROADMAP SC#4]** Har sana Asia/Tashkent biznes-kuni bo'yicha, har summa butun so'mda; yarim tunda kun chegarasi to'g'ri suriladi | ✓ VERIFIED | O'zgarmadi — to'liq to'plamda (416) yashil |
| 5 | **[ROADMAP SC#5]** Moliyaviy jadvallar dublikat-himoyasi bilan tug'iladi (`UNIQUE(market_id, stall_id, business_date)`) | ✓ VERIFIED | O'zgarmadi — to'liq to'plamda (416) yashil |
| 6 | [01-01] Ilova DB'ga faqat `NOSUPERUSER NOBYPASSRLS` `sbozor_app` roli bilan ulanadi | ✓ VERIFIED (regressiya tekshiruvi) | Tegilmagan; to'liq to'plamda yashil |
| 7 | [01-01] Testlar haqiqiy `postgres:18.4-trixie`ga qarshi ishlaydi | ✓ VERIFIED (regressiya tekshiruvi) | Tegilmagan; barcha yangi testlar ham shu real Postgres'ga qarshi (testcontainers) ishladi |
| 8 | [01-01] Repoda hech qanday sir commit qilinmagan | ✓ VERIFIED (regressiya tekshiruvi) | `.env.example` yangi `FORWARDED_ALLOW_IPS=*` qatori bilan o'qildi — sir emas, faqat konfiguratsiya bayrog'i |
| 9 | [01-04] Tenant kontekstisiz so'rov 0 qator qaytaradi (fail-closed) | ✓ VERIFIED (regressiya tekshiruvi) | Tegilmagan; `audit_read_platform` HAM shu fail-closed falsafasiga amal qiladi (owner-scoped, app-rol uchun 0 qator — `test_platform_audit_rows_are_invisible_to_app_role_directly` bilan o'lchangan) |
| 10 | [01-04] Cross-tenant havola composite FK bilan bloklangan | ✓ VERIFIED (regressiya tekshiruvi) | Tegilmagan |
| 11 | [01-04] Login `SECURITY DEFINER` funksiyalar orqali, BYPASSRLS talab qilinmaydi | ✓ VERIFIED (regressiya tekshiruvi) | `auth_list_platform_audit()` ham shu naqshni takrorlaydi (SECURITY DEFINER + search_path pin), lekin BYPASSRLS emas — owner-scoped policy bilan juftlikda |
| 12 | [01-05] Xom SQL ham audit yozuvini hosil qiladi | ✓ VERIFIED (regressiya tekshiruvi) | Tegilmagan |
| 13 | [01-05] Audit jurnalini na ilova roli, na jadval egasi tahrirlay/o'chira olmaydi | ✓ VERIFIED | Men bevosita tekshirdim: yangi `audit_read_platform` policy FAQAT `FOR SELECT`, `UPDATE`/`DELETE` uchun policy YO'Q — 2-qatlam buzilmagan. `test_audit_immutable.py` 7/7 yashil |
| 14 | [01-06] Noto'g'ri parol / mavjud bo'lmagan telefon / bloklangan bir xil javob (enumeration yo'q) | ✓ VERIFIED (regressiya tekshiruvi) | Tegilmagan |
| 15 | [01-06] O'g'irlangan refresh token oilasi bekor qilinadi | ✓ VERIFIED (regressiya tekshiruvi) | Tegilmagan |
| 16 | [01-06] RBAC matritsasi kodda qat'iy; direktor rasta/tarif/xodim o'zgartira olmaydi | ✓ VERIFIED (regressiya tekshiruvi) | Tegilmagan |
| 17 | [01-07] Admin vaqtinchalik parol beradi va foydalanuvchi birinchi kirishda uni **majburiy** almashtiradi (server tomonda) | ✓ VERIFIED | **CR-01 YOPILDI.** `Principal.must_change_password` maydoni mavjud (`deps.py:156`); `require_password_current` (`deps.py:369-392`) `get_tenant_session`, `require_permission`, `require_roles` ning UCHALASI ICHIGA ham ulangan (`CurrentPasswordDep` orqali). `test_password_gate.py` 8/8 yashil. **Mustaqil sabotaj:** darvozani `get_tenant_session`dan olib tashlaganimda 2/8 test qizardi (qolganlari boshqa ikki mustaqil yo'l orqali baribir himoyalangan qoldi) — bu haqiqiy, ko'p qatlamli ulanishni isbotlaydi |
| 18 | [01-07] Bozor admini `market_admin`/`director`/`platform_admin` roli bilan foydalanuvchi yarata OLMAYDI | ✓ VERIFIED (endi TO'LIQ) | `_assert_roles_assignable` (`users.py:128-170`) endi `Role.PLATFORM_ADMIN`ni CHAQIRUVCHIDAN QAT'I NAZAR (platforma admini uchun ham) rad etadi — ilgari faqat bozor-admin chaqiruvchi cheklangan edi. `test_platform_admin_cannot_assign_the_platform_admin_role` va `test_market_view_all_without_the_flag_sees_only_its_own_market` yashil |
| 19 | [01-08] Platforma admini kirgach bozor tanlash ekranini ko'radi va tanlaganidan keyin panelga kiradi | ✓ VERIFIED | **CR-02 YOPILDI.** `market-picker.tsx:108`: `isBusy = selectMarket.isPending \|\| marketsQuery.isLoading` (endi `isPending` emas). Fazadagi BIRINCHI React render testi (`market-picker.test.tsx`, 3 test) `markets` to'la bo'lganda tugmalar `not.toBeDisabled()` ekanini isbotlaydi. Men `npm test`ni ishga tushirdim: vitest 3/3 yashil |
| 20 | [01-08] Access token faqat xotirada saqlanadi | ✓ VERIFIED (regressiya tekshiruvi) | Tegilmagan; `grep -rn "localStorage\|sessionStorage" frontend/src/` hamon bo'sh |
| 21 | [01-09] Kassir va nazoratchi audit/foydalanuvchi bo'limini ko'rmaydi | ✓ VERIFIED (regressiya tekshiruvi, KUCHAYTIRILGAN) | `test_inspector_cannot_view_the_audit_log` endi `auth_seed.inspector` (must_change=false) dan foydalanadi va `detail=="forbidden"`ni ANIQ tekshiradi — RBAC endi parol-darvozadan MUSTAQIL isbotlanadi (ilgari qisman xiralashgan bo'lardi) |
| 22 | [01-10] Har bir tenant resurs marshruti avtomatik olinadi; qamrab olinmagan marshrut CI'ni yiqitadi | ✓ VERIFIED (tuynuk YOPILDI) | `EXEMPT_ROUTES["/api/v1/markets"]` sababi CR-03 asosida qayta yozilgan (endi to'g'ri); yangi `/api/v1/audit/platform` ham `EXEMPT_ROUTES`da to'g'ri tasniflangan VA yo'qolgan 401/403 qamrovi (`test_missing_token_is_rejected`, `test_hybrid_platform_role_is_forbidden`) alohida testda tiklangan. `test_route_coverage.py` men ishga tushirdim: 8/8 yashil |
| 23 | [Cross-cutting] `platform_admin` roli bozor-darajasidagi foydalanuvchiga BERILMAYDI | ✓ VERIFIED | **CR-03 YOPILDI.** Backend: `_assert_roles_assignable` har doim rad etadi. Frontend: `PLATFORM_ADMIN_ASSIGNABLE_ROLES` da `platform_admin` yo'q, `role-gate.test.mjs`ga 3-test QO'SHILDI (ilgari 2-test zaiflikni "to'g'ri" deb qulflagan edi — endi sarlavha/mazmun tuzatilgan va yangi test `platform_admin`ning ikkala ro'yxatda YO'Qligini `Role` enumiga bog'lab qulflaydi). Men `node --test role-gate.test.mjs`ni ishga tushirdim: 3/3 yashil |
| 24 | [Cross-cutting] Login rate-limit va `audit_log.ip` haqiqiy mijoz IP'sini aks ettiradi | ✓ VERIFIED | **CR-04 YOPILDI.** `compose.yaml` VA `compose.override.yml` ikkalasida ham `--proxy-headers --forwarded-allow-ips ${FORWARDED_ALLOW_IPS:-*}` bor (men ikkalasini ham o'qidim va `docker compose config`da tasdiqladim). `test_rate_limit_proxy.py` (5 test) IP-kesim ajralishini, teskari-yo'nalish sarlavha-spoofing himoyasini va bir kesim to'lganda ikkinchisi ochiq qolishini isbotlaydi — men ishga tushirdim, 5/5 yashil |
| 25 | [Cross-cutting] `market_id IS NULL` audit qatorlari (masalan `login_failed`) platforma darajasida o'qish yo'liga ega | ✓ VERIFIED | **Gap 5 backend/API qatlami TO'LIQ YOPILDI.** `audit_read_platform` owner-scoped policy + `auth_list_platform_audit()` SECURITY DEFINER funksiya (01-14) + `GET /api/v1/audit/platform` + `require_platform_admin` (bayroqqa, rolga emas — CR-03 darsi) (01-15). `test_audit_platform.py` (12 test): platforma admini `login_failed`ni ko'radi, market_admin 403, gibrid-rolli hisob HAM 403, ko'rish o'zi audit yozuvi hosil qiladi. Men ishga tushirdim: 12/12 yashil. **OCHIQ E'LON (gap emas):** mahsulot UI'sida iste'molchi yo'q — `frontend/src/`da `audit/platform`ga hech qanday havola topilmadi (men grep bilan tasdiqladim), bu 01-15-SUMMARY.md `known_stubs`da ATAYIN va OCHIQ 8-fazaga qoldirilgan qaror, yashirin bo'shliq emas |

**Score:** 25/25 truths verified (0 overrides)

## Har bir gap bo'yicha batafsil qayta tasdiqlash

### Gap 1 (CR-01) — YOPILDI, mustaqil sabotaj bilan tasdiqlangan

- `services/core-api/app/deps.py`: `Principal.must_change_password: bool = False` (156-qator), `_user_state()` ikkala bayroqni (`is_active`, `must_change_password`) BITTA Valkey yozuvidan (ikki belgili kod) oladi, `require_password_current()` (369-392) `password_change_required` bilan 403 qaytaradi.
- Ulanish: `CurrentPasswordDep` — `get_tenant_session` (401-qator), `require_permission._require` (451-qator), `require_roles._require` (478-qator) UCHALASI ham shu darvozaga bog'langan. `/auth/change-password`, `/auth/logout`, `/api/v1/me` esa `get_current_principal`/`get_auth_session` bilan TO'G'RIDAN-TO'G'RI ishlagani uchun ATAYIN ochiq qoladi.
- **Mustaqil sabotaj natijasi:** `get_tenant_session`dagi `CurrentPasswordDep`ni `PrincipalDep`ga almashtirganimda AYNAN `test_session_endpoint_is_gated_too` va `test_admin_password_reset_locks_the_live_session_immediately` qizardi (ikkalasi ham `/api/v1/auth/me` — `TenantSessionDep` ishlatadigan yagona test yo'li). Qolgan 6 test (`GET/POST /users`, `GET /audit` — bular `require_permission` orqali ham gatelangan) TA'SIRLANMADI, chunki ular ikkinchi mustaqil yo'l orqali baribir himoyalangan. Bu darvozaning UCHTA joyda mustaqil, ortiqcha (redundant) ulanganini — ya'ni bitta joy unutilsa ham boshqalari tutib qolishini — isbotladi. Sabotajni darhol `git checkout`bilan qaytardim.
- Frontend: `change-password-form.tsx:21` va `layout.tsx:20` dagi "server ham yopiq" izohlari — ILGARI YOLG'ON edi, ENDI TO'G'RI (kod ularning da'vosini haqiqatga aylantirdi).
- Regressiya nazorati (item 7, task talabi bo'yicha): uchta mavjud test (`test_inspector_cannot_view_the_audit_log`, `test_director_can_view_the_audit_log`, `test_cashier_and_director_cannot_manage_users`) o'qildi — barchasi ASL RBAC da'vosini (`{"detail": "forbidden"}`) tasdiqlaydi, birortasi ham `password_change_required`ni qabul qiladigan darajada BO'SHASHTIRILMAGAN.

### Gap 2 (CR-02) — YOPILDI, komponent-test bilan tasdiqlangan

- `market-picker.tsx:108`: `isBusy = selectMarket.isPending || marketsQuery.isLoading` — men kodni to'liq o'qidim, `isPending` so'zi endi faqat izohda ("nega ishlatilmadi" tushuntirishida) uchraydi, mantiqda YO'Q.
- `market-picker.test.tsx` — fazadagi BIRINCHI React render testi (jsdom + Testing Library, oltita paket npm registridan legitim deb tasdiqlangan holda o'rnatilgan). 3 test: (1) to'la `markets` bilan tugmalar `not.toBeDisabled()`, (2) bosilganda `POST /auth/select-market` aynan tanlangan `market_id` bilan ketadi, (3) so'rov ketayotganda tugmalar bloklanadi (ya'ni tuzatish `disabled` mantiqini o'chirib tashlamagan, TO'G'RILAGAN). Men `npm --prefix frontend test`ni ishga tushirdim: vitest 3/3 yashil.

### Gap 3 (CR-03) — YOPILDI, ikki mustaqil qatlamda

- Backend: `users.py::_assert_roles_assignable` (128-170) — `Role.PLATFORM_ADMIN in requested` tekshiruvi CHAQIRUVCHIDAN QAT'I NAZAR (platforma admini chaqiruvchisi uchun ham) 403 qaytaradi. `markets.py::list_markets` (74-102) — branch `principal.is_platform_admin` bayrog'iga bog'langan, `MARKET_VIEW_ALL` huquqiga EMAS.
- Frontend: `api-types.ts::PLATFORM_ADMIN_ASSIGNABLE_ROLES` — `platform_admin`siz to'rtlik (`director`, `market_admin`, `cashier`, `inspector`), `Role` enumiga bog'langan.
- `role-gate.test.mjs`: 2-test sarlavhasi/mazmuni tuzatilgan (endi zaiflikni "to'g'ri" deb da'vo qilmaydi — faqat `ROLES` YORLIQ ro'yxati enumga mosligini tekshiradi); 3-test YANGI qo'shilgan va `platform_admin`ning ikkala assignable ro'yxatda YO'Qligini `Role` enumiga bog'lab qulflaydi (kelajakda yangi rol qo'shilsa ham darvoza avtomatik qamraydi). Men `node --test role-gate.test.mjs`ni ishga tushirdim: 3/3 yashil.
- `test_cross_tenant.py::EXEMPT_ROUTES["/api/v1/markets"]` sababi CR-03 asosida qayta yozilgan.

### Gap 4 (CR-04) — YOPILDI, ikkala compose faylida

- `compose.yaml:100-111` VA `compose.override.yml:30-39` — IKKALASIDA HAM `--proxy-headers`, `--forwarded-allow-ips`, `${FORWARDED_ALLOW_IPS:-*}` bor (men ikkalasini ham to'liq o'qidim). Bu muhim edi: `command` compose'da MERGE emas, ALMASHTIRISH — agar faqat `compose.yaml` tuzatilganida `compose.override.yml` (dev/`npm run up` yo'li) buyrug'i bazaviyni butunlay bosib, tuzatish qog'ozda qolardi. 01-13-SUMMARY bu holatni "Auto-fixed Issue #1" sifatida hujjatlagan va men buni ikkala faylni o'qib mustaqil tasdiqladim.
- `docker compose config --quiet` (override bilan va `-f compose.yaml` bilan alohida) — ikkalasi ham exit 0 va flag'larni ko'rsatadi; `core-api`da `ports:` yo'qligi (xavfsizlik asosi — `*` faqat shuning uchun xavfsiz) ham tasdiqlandi.
- `test_rate_limit_proxy.py` (5 test, men ishga tushirdim): ikki mijoz ikkita mustaqil `rl:login:ip:*` kaliti oladi; soxta `X-Forwarded-For` sarlavhasining o'zi hech narsani ko'chira olmaydi; bir kesim to'lganda ikkinchisi ochiq qoladi.
- Bonus: WR-01 (`censor_secrets` rekursiv emasligi) ham shu rejada tuzatilgan — men `logging.py`ni o'qib `_censor()` yordamchisining haqiqatan rekursiv (dict/list/tuple) ekanini tasdiqladim; `test_logging.py` 20/20 yashil.

### Gap 5 — backend/API to'liq yopildi, frontend UI ATAYIN va OCHIQ 8-fazaga qoldirilgan

- DB (01-14): `audit_read_platform_policy()` — `FOR SELECT TO sbozor_owner USING (market_id IS NULL)`; `auth_list_platform_audit()` — SECURITY DEFINER, keyset sahifalash bilan. Men `policies.py`ni o'qib bu policy `audit_log`dagi UCHINCHI va YAGONA qo'shimcha policy ekanini, `FOR ALL`/`UPDATE`/`DELETE` YO'Qligini tasdiqladim (o'zgarmaslik 2-qatlami but).
- API (01-15): `deps.py::require_platform_admin` — `is_platform_admin` BAYROG'IGA (derivatsiyalangan rolga emas — CR-03 darsi) tayanadi va `require_password_current` orqali D-02 darvozasiga ham bog'langan. `audit.py::GET /api/v1/audit/platform` — `audit_repo.list_platform_audit()` orqali. Ko'rishning o'zi `reason="platform_audit_view"` bilan auditga yoziladi (D-09).
- `test_audit_platform.py` (12 test, men ishga tushirdim, 12/12 yashil): platforma admini `login_failed` qatorini ko'radi; market_admin (bayroqsiz, lekin `AUDIT_VIEW` huquqli) 403; **gibrid rolli hisob** (`roles=["platform_admin"]` + `is_platform_admin=false` — CR-03ning aynan o'zi) HAM 403 — bu VERIFICATION talab qilgan "qat'iyroq" variant (`require_roles` emas, bayroq) to'g'ri tanlanganini isbotlaydi; tenant qatorlari javobda YO'Q; tokensiz so'rov 401; must-change platforma admini `password_change_required` oladi (`forbidden` emas).
- **Ochiq e'lon, gap EMAS:** men `grep -rn "audit/platform\|platform_audit" frontend/src/`ni ishga tushirdim — natija BO'SH. Bu 01-15-SUMMARY.md frontmatter `known_stubs`da aniq hujjatlashtirilgan: mahsulot UI iste'molchisi ATAYIN 8-fazaga (hisobot/qattiqlashtirish yuzasi) qoldirilgan, chunki VERIFICATION Gap 5 mandati faqat HIMOYALANGAN O'QISH YO'LINI talab qilgan, UI qo'shimcha edi. Backend/API to'liq ishlaydi va 12 test bilan qoplangan — bu "stub" emas, "hali frontend ekrani yo'q" degani.

## Required Artifacts (yangilangan)

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `services/core-api/app/deps.py` | Principal + parol darvozasi | ✓ VERIFIED | `must_change_password` maydoni + `require_password_current` + `require_platform_admin`; 3 ta dependencyga ulangan; sabotaj bilan mustaqil tasdiqlandi |
| `services/core-api/app/api/v1/users.py` | D-04 ikki bosqichli boshqaruv | ✓ VERIFIED | `_assert_roles_assignable` `PLATFORM_ADMIN`ni chaqiruvchidan qat'i nazar rad etadi |
| `services/core-api/app/api/v1/markets.py` | D-06 bozorlar ro'yxati | ✓ VERIFIED | `is_platform_admin` bayrog'iga bog'langan, `MARKET_VIEW_ALL`ga emas |
| `services/core-api/app/api/v1/audit.py` | Audit ko'rish (tenant + platforma) | ✓ VERIFIED | `GET /audit` (tenant) + `GET /audit/platform` (yangi) — ikkalasi ham `_entry()` orqali bir xil maskalashdan o'tadi |
| `services/core-api/app/repositories/audit_repo.py` | Keyset sahifalash | ✓ VERIFIED | `list_platform_audit` + `PlatformAuditRow`/`PlatformAuditPage` — tenant yo'li bilan bir xil keyset semantikasi |
| `compose.yaml` + `compose.override.yml` | proxy-headers ikkalasida ham | ✓ VERIFIED | Men ikkalasini ham o'qidim va `docker compose config`da tasdiqladim |
| `packages/sbozor-core/sbozor_core/logging.py` | Rekursiv censor_secrets | ✓ VERIFIED | `_censor()` yordamchisi dict/list/tuple ichiga kiradi |
| `migrations/entities/policies.py` + `functions.py` + `0005_platform_audit.py` | Gap 5 DB qatlami | ✓ VERIFIED | `audit_read_platform_policy` + `auth_list_platform_audit`; migratsiya round-trip xatosiz (SUMMARY'da hujjatlashtirilgan, men testlar orqali bilvosita tasdiqladim — real Postgres'ga qarshi 416 test) |
| `frontend/src/components/auth/market-picker.tsx` + `.test.tsx` | D-06 bozor tanlash | ✓ VERIFIED | `isLoading` mantiqiy tuzatish + render testi |
| `frontend/src/lib/api-types.ts` | PLATFORM_ADMIN_ASSIGNABLE_ROLES | ✓ VERIFIED | `platform_admin`siz to'rtlik, `Role` enumiga bog'langan |
| `frontend/scripts/role-gate.test.mjs` | CR-03 frontend qulfi | ✓ VERIFIED | 2-test tuzatilgan (endi to'g'ri da'vo), 3-test yangi qo'shilgan |
| `tests/integration/test_password_gate.py` | CR-01 integratsiya testi | ✓ VERIFIED | 8/8 yashil (men ishga tushirdim) |
| `tests/integration/test_rate_limit_proxy.py` | CR-04 IP-scope testi | ✓ VERIFIED | 5/5 yashil (men ishga tushirdim) |
| `tests/integration/test_audit_platform.py` | Gap 5 uchdan-uchiga testi | ✓ VERIFIED | 12/12 yashil (men ishga tushirdim) |

## Key Link Verification (yangilangan)

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `deps.py::get_tenant_session` | `require_password_current` | `Depends(CurrentPasswordDep)` | ✓ WIRED | Sabotaj bilan mustaqil tasdiqlandi (olib tashlanganda 2 test qizaradi) |
| `deps.py::require_permission._require` | `require_password_current` | `Depends(CurrentPasswordDep)` | ✓ WIRED | Sabotaj natijasida bu yo'l TA'SIRLANMADI — mustaqil ikkinchi qatlam ekanini isbotladi |
| `deps.py::require_roles._require` | `require_password_current` | `Depends(CurrentPasswordDep)` | ✓ WIRED | Kod o'qildi; hozircha faol iste'molchisi yo'q, lekin darvoza ulangan |
| `deps.py::require_platform_admin` | `require_password_current` | `Depends(CurrentPasswordDep)` | ✓ WIRED | `test_must_change_platform_admin_is_gated` bilan qulflangan |
| `users.py::_assert_roles_assignable` | `Role.PLATFORM_ADMIN` rad etish | shartsiz tekshiruv | ✓ WIRED | `test_platform_admin_cannot_assign_the_platform_admin_role` |
| `markets.py::list_markets` | `principal.is_platform_admin` | branch sharti | ✓ WIRED | `test_market_view_all_without_the_flag_sees_only_its_own_market` (gibrid hisob bilan) |
| `market-picker.tsx` | `marketsQuery.isLoading` | `isBusy` hisobi | ✓ WIRED | `market-picker.test.tsx` render testi bilan qulflangan |
| `api-types.ts::assignableRoles` | `PLATFORM_ADMIN_ASSIGNABLE_ROLES` | funksiya tanasi | ✓ WIRED | `role-gate.test.mjs` 3-test |
| `compose.yaml`/`compose.override.yml` `command` | uvicorn `--forwarded-allow-ips` | ikkala faylda takrorlangan bayroq | ✓ WIRED | `docker compose config` (ikkala shakl) men tomonimdan tasdiqlandi |
| `audit.py::list_platform_audit` | `auth_list_platform_audit()` (0005) | `audit_repo.list_platform_audit` → `text()` | ✓ WIRED | `test_audit_platform.py::test_platform_admin_sees_the_failed_login_row` |
| `audit.py::PlatformAuditViewerDep` | `require_platform_admin` | `Depends(require_platform_admin)` | ✓ WIRED | `test_market_admin_is_forbidden`, `test_hybrid_platform_role_is_forbidden` |

## Data-Flow Trace (Level 4, yangilangan)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|---------------------|--------|
| `market-picker.tsx` | `options` (bozorlar ro'yxati) | Login javobidagi `markets` massivi | Ha — VA endi foydalanuvchi u bilan HAQIQATAN o'zaro ta'sirga kira oladi (tugmalar enabled) | ✓ FLOWING (CR-02 yopilgach control-flow gate ham tuzatildi) |
| `audit-list.tsx` (tenant) | `items` | `GET /api/v1/audit` | Ha | ✓ FLOWING (o'zgarmadi) |
| `GET /api/v1/audit/platform` javobi | `items` | `auth_list_platform_audit()` → real DB (login_failed va h.k.) | Ha — men `test_platform_admin_sees_the_failed_login_row` orqali tasdiqladim | ✓ FLOWING (yangi, backend/API to'liq). Mahsulot UI'sida iste'molchi yo'q (8-fazaga ochiq qoldirilgan) — bu HOLLOW_PROP emas, chunki hech qanday UI komponenti bu ma'lumotni so'ramaydi (frontend hali qurilmagan, backend esa Swagger/API orqali to'liq ishlaydi) |

## Behavioral Spot-Checks (men bevosita ishga tushirdim)

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Backend to'liq to'plami | `docker compose --profile test run --rm tests pytest -q` | 416/416 (nuqta-sanoq bilan tasdiqlandi, 0 F/E/s/x) | ✓ PASS |
| Ruff/format/mypy/S608 | `sh -c "ruff check . && ruff format --check . && mypy . && ruff check --select S608 ."` | Barchasi toza (87 fayl) | ✓ PASS |
| Frontend typecheck | `npm --prefix frontend run typecheck` | exit 0 | ✓ PASS |
| Frontend lint | `npm --prefix frontend run lint` | exit 0 | ✓ PASS |
| Frontend testlari | `npm --prefix frontend test` | node:test 38/38 + vitest 3/3 | ✓ PASS |
| i18n parity | `npm --prefix frontend run i18n:check` | 120×3, drift yo'q | ✓ PASS |
| Frontend build | `npm --prefix frontend run build` | 24/24 SSG sahifa | ✓ PASS |
| `docker compose config` (override bilan) | `docker compose config --quiet` | exit 0, proxy-headers bor | ✓ PASS |
| `docker compose config` (bazaviy) | `docker compose -f compose.yaml config --quiet` | exit 0, proxy-headers bor, `core-api`da `ports:` yo'q | ✓ PASS |
| Gap-closure testlari (10 fayl birlashtirilgan) | `pytest tests/integration/test_password_gate.py tests/integration/test_audit_read.py tests/integration/test_users_api.py tests/tenancy/test_cross_tenant.py tests/integration/test_rate_limit_proxy.py tests/integration/test_audit_platform.py tests/tenancy/test_meta.py tests/tenancy/test_login_bootstrap.py tests/integration/test_audit_immutable.py tests/unit/test_logging.py -v` | 177/177 | ✓ PASS |
| Route coverage darvozasi | `pytest tests/tenancy/test_route_coverage.py -v` | 8/8 | ✓ PASS |
| **Mustaqil sabotaj — CR-01** | `get_tenant_session`da `CurrentPasswordDep`→`PrincipalDep`, so'ng `pytest test_password_gate.py` | 2/8 qizardi (aynan `/auth/me` yo'li), 6/8 boshqa mustaqil qatlam orqali yashil qoldi — `git checkout` bilan qaytarildi | ✓ PASS (kutilgan xulq) |
| Debt-marker skani (yangi/o'zgargan fayllar) | `grep -n -E "TBD\|FIXME\|XXX\|TODO\|HACK\|PLACEHOLDER"` | Bo'sh | ✓ PASS |
| xfail/skip skani | `grep -rn -E "xfail\|pytest.mark.skip" tests/` | Bo'sh | ✓ PASS |
| Frontend UI — Gap 5 iste'molchisi yo'qligi tasdiqlanishi | `grep -rn "audit/platform\|platform_audit" frontend/src/` | Bo'sh (kutilgan — ochiq e'lon) | ✓ PASS |
| Git diff — yashirin fayl yo'qligi | `git diff --name-only 5ed238e..HEAD` | 5 rejaning birlashgan `files_modified`i bilan AYNAN mos | ✓ PASS |
| Commit mavjudligi | `git log --oneline -25` | Barcha 8 da'vo qilingan commit hash topildi | ✓ PASS |

## Probe Execution

SKIPPED — bu fazada probe-asoslangan tekshiruv konventsiyasi yo'q (migratsiya/CLI vositasi fazasi emas).

## Requirements Coverage (yangilangan)

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|--------------|--------|----------|
| FOUND-01 | 01-03, 01-04, 01-06, 01-07, 01-08, 01-09, **01-11, 01-12** | Foydalanuvchi rolga mos kirish oladi (RBAC); har rol faqat o'z bozorini ko'radi | ✓ SATISFIED | CR-01, CR-02, CR-03 uchtasi ham yopildi — RBAC matritsasi + parol darvozasi + bozor tanlash + rol berish darajasi hammasi server va frontend darajasida ishlaydi va test bilan qulflangan |
| FOUND-02 | 01-01, 01-04, 01-10, **01-11** | Tenant izolyatsiyasi: RLS + avtomatik cross-tenant test | ✓ SATISFIED | DB-darajadagi RLS mustahkam (o'zgarmadi). Ilova-darajasidagi bo'shliq (CR-03 — bozorlar ro'yxati oshkoralashuvi) yopildi; `test_cross_tenant.py` EXEMPT_ROUTES sababi to'g'irlangan |
| FOUND-03 | 01-05, 01-06, 01-07, 01-09, **01-13, 01-14, 01-15** | Har ma'muriy/moliyaviy harakat audit jurnaliga yoziladi; jurnal o'zgarmas | ✓ SATISFIED | Yozuv+o'zgarmaslik yadrosi mustahkam (o'zgarmadi). CR-04 (IP korruptsiyasi) va Gap 5 (`market_id IS NULL` ko'rinmasligi) ikkalasi ham backend/API darajasida yopildi. Frontend UI (platforma-audit ekrani) 8-fazaga ATAYIN va OCHIQ qoldirilgan — bu mezonning harfini ham, ruhini ham buzmaydi (yozuv+o'zgarmaslik+IP+platforma-o'qish yo'li — barchasi mavjud) |
| FOUND-04 | 01-02, 01-07, 01-08, 01-09 | Interfeys 3 tilda; til bir bosishda almashadi | ✓ SATISFIED | O'zgarmadi. Men build/test/i18n:check ni qayta ishga tushirdim |
| FOUND-05 | 01-03, 01-05 | Biznes-kun Asia/Tashkent bo'yicha; pul butun so'mda | ✓ SATISFIED | O'zgarmadi |

**Orphaned requirements:** Yo'q.

## Anti-Patterns Found (yangilangan)

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | Ilgari qayd etilgan 4 ta BLOKER (CR-01…CR-04) | — | **Barchasi YOPILDI** — pastdagi qatorlarda endi mavjud emas |
| `frontend/src/lib/auth-store.ts`, `login-form.tsx`, `temp-password-dialog.tsx`, `audit-diff.tsx` (4 fayl) | turli | WR-05: "grep darvozasi bilan qulflangan" deb da'vo qilingan, lekin bunday CI qadami/skript hamon mavjud emas (men `frontend/scripts/`ni tekshirdim — mos skript yo'q) | ⚠️ WARNING (mavjud, gap-closure to'lqini tegmagan) | Bu 5 gapning tarkibiga kirmagan va ushbu qayta tekshiruv mandatidan tashqarida; original 01-REVIEW.mda WARNING (BLOKER emas) darajasida qayd etilgan, hamon shunday qoladi |
| `package.json` (root, `scripts.gate`) | 16-qator | WR-07: root `gate` skripti hamon `npm --prefix frontend test`ni chaqirmaydi | ⚠️ WARNING (mavjud, gap-closure to'lqini tegmagan) | 5 gapning tarkibiga kirmagan; CI (`ci-frontend.yml`) buni alohida bajaradi, shuning uchun amaliy xavf past, lekin developer local `gate`i CI'dan farqli natija berishi mumkin |
| `packages/sbozor-core/sbozor_core/logging.py` | — | WR-01 — rekursiv bo'lmagan sir-maskalash | ✓ TUZATILDI | 01-13 rejasida bonus sifatida yopildi (mandatdan tashqari, lekin ijobiy) |
| — | — | Debt-marker (TBD/FIXME/XXX/TODO/HACK/PLACEHOLDER), xfail/skip | ℹ️ INFO | Men butun repo bo'yicha va yangi/o'zgargan fayllar bo'yicha alohida grep qildim — ikkalasi ham bo'sh |

## Human Verification Required

### 1. To'liq 8+15 qadamlik uchidan-uchiga jonli tekshiruv (YANGILANGAN holat)

**Test:** `npm run up`, `npm run migrate`, `docker compose --profile web --profile proxy up -d` bilan stekni ko'tarib, 01-08 Task 3 (8 qadam) va 01-09 Task 2 (15 qadam) dagi `<human-check>` ro'yxatlarini to'liq bajarish.
**Expected:** Login, til almashtirish, audit ko'rinishi, DB-owner o'zgarmaslik namoyishi — barchasi kutilgan natijani beradi.
**Why human:** Brauzer-darajasidagi avtomatik test infratuzilmasi bu fazada yo'q (Playwright 8-fazaga qoldirilgan).
**MUHIM YANGILANISH:** Oldingi tekshiruvda CR-01 va CR-02 bu ketma-ketlikni 3- va 8-qadamlarda MUQARRAR to'xtatishi kutilgan edi. Ikkalasi ham endi kodda VA testda mustaqil tasdiqlangan holda yopilgan (yuqoriga qarang) — **shuning uchun bu ketma-ketlik endi 3- va 8-qadamlarda to'xtamasligi kerak.** Shunga qaramay to'liq vizual/UX oqim hali bir marta ham inson tomonidan uchidan-uchiga bajarilmagan, shuning uchun bu band ochiq qolmoqda (avtomatlashtirilgan testlar brauzer xatti-harakatini to'liq almashtira olmaydi).

### 2. uz-Cyrl imlo sifati

**Test:** Kirill xabar fayllaridagi transliteratsiya natijasini (`Ҳисоб`, `маъмурият`, `аъзоликлари` kabi so'zlar) o'zbek tili mutaxassisi ko'zdan kechirishi.
**Expected:** O'zbek kirill imlosi qoidalariga to'liq mos.
**Why human:** Avtomatik generator faqat struktura/ICU darajasida test qilingan (men `i18n:check`ni qayta ishga tushirdim — drift yo'q); tilshunoslik sifati inson bahosini talab qiladi. Gap-closure to'lqini bu fayllarga tegmadi.

### 3. Vizual/UX muvofiqlik

**Test:** AppShell mobil pastki navigatsiyasi va Apple-uslub minimal dizayn talablariga muvofiqlikni ko'rish.
**Expected:** Kassir mobil oqimida barmoq nishonlari ≥44px, minimalist va kam-kontrastli ko'rinish.
**Why human:** Vizual dizayn sifati kod tekshiruvi bilan o'lchanmaydi. Gap-closure to'lqini bu qismga tegmadi.

## Gaps Summary

**Barcha 5 gap yopildi.** Men buni SUMMARY.md da'volariga ishonib emas, quyidagi mustaqil dalillar bilan tasdiqladim:

1. Har bir gap uchun haqiqiy kod o'zgarishlarini o'qidim (`deps.py`, `users.py`, `markets.py`, `audit.py`, `audit_repo.py`, `compose.yaml`, `compose.override.yml`, `logging.py`, `market-picker.tsx`, `api-types.ts`, `role-gate.test.mjs`, `policies.py`, `functions.py`).
2. Backend to'liq to'plamini (416 test) va frontend to'liq darvozasini (typecheck/lint/test/i18n/build) o'zim ishga tushirdim — ikkalasi ham toza.
3. Gap-closure'ga bevosita tegishli 10 test faylini (177 test) alohida, tafsilotli rejimda ishga tushirdim.
4. **CR-01 uchun mustaqil sabotaj testi** o'tkazdim — darvozani bitta joydan olib tashlaganimda aynan kutilgan 2 test qizardi, qolganlari boshqa mustaqil qatlam orqali yashil qoldi. Bu tasodifiy yashil emas, HAQIQIY sabab-natija bog'lanishini isbotladi.
5. Uchta xavf-ostidagi RBAC testi (CR-01 gate yon ta'siridan tuzatilgan) hamon ASL RBAC da'vosini isbotlashini tasdiqladim — bo'shashtirilmagan.
6. Audit jurnalining 4-qatlamli o'zgarmasligi yangi `audit_read_platform` policy qo'shilgandan keyin ham but ekanini bevosita policy ta'rifini o'qib tasdiqladim (FAQAT 3 policy, barchasi INSERT/SELECT, FOR ALL/UPDATE/DELETE yo'q).
7. `git diff`/`git log` orqali hech qanday yashirin fayl o'zgarishi yoki soxta commit da'vosi yo'qligini tasdiqladim.
8. Disconfirmation pass o'tkazdim va ikkita OLDINDAN mavjud, ushbu 5 gapga aloqasi yo'q WARNING (WR-05, WR-07) hamon ochiqligini topdim — bular fazani bloklamaydi.

**Yagona ochiq qism** — Gap 5ning mahsulot UI iste'molchisi. Bu **gap emas**: VERIFICATION talabi faqat himoyalangan o'qish yo'lini so'ragan edi (endpoint + SECURITY DEFINER), UI esa 01-15-SUMMARY.mdda ATAYIN va OCHIQ 8-fazaga (hisobot/qattiqlashtirish yuzasi) qoldirilgan — bu qaror shaffof hujjatlashtirilgan, yashirin emas.

**Status `human_needed`** (na `passed`, na `gaps_found`): barcha 25 truth VERIFIED va 0 gap qoldi, lekin uchta inson-tekshiruv bandi (to'liq brauzer oqimi, uz-Cyrl imlo, vizual dizayn) hamon ochiq — bular avtomatlashtirilgan tekshiruv doirasidan tashqarida va hech qachon "passed" holatiga avtomatik aylanmaydi.

---

_Verified: 2026-07-29T21:15:00Z_
_Verifier: Claude (gsd-verifier)_
_Re-verification: Ha — 01-11…01-15 gap-closure to'lqinidan keyin_
