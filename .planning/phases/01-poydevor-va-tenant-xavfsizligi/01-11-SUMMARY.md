---
phase: 01-poydevor-va-tenant-xavfsizligi
plan: 11
subsystem: auth
tags: [fastapi, rbac, rls, multi-tenant, valkey, pytest, argon2]

# Dependency graph
requires:
  - phase: 01-poydevor-va-tenant-xavfsizligi
    provides: "deps.py Principal + tenant sessiya (01-06), users/markets/audit endpointlari va D-04 rol darvozasi (01-07), cross-tenant marshrut matritsasi (01-10)"
provides:
  - "`require_password_current` — D-02 ni server tomonda kuchga kirituvchi darvoza (`get_tenant_session`, `require_permission`, `require_roles` ostida)"
  - "`Principal.must_change_password` — `is_active` bilan bir manbadan, bitta kesh yozuvidan"
  - "`reset-password` uchun `user:state` kesh invalidatsiyasi (tiklash MAVJUD access tokenga darhol ta'sir qiladi)"
  - "`_assert_roles_assignable` — `platform_admin` a'zolik roli sifatida HECH KIMGA berilmaydi"
  - "`list_markets` — branch `users.is_platform_admin` bayrog'ida, `MARKET_VIEW_ALL` huquqida emas"
  - "`AuthSeed.inspector` va `AuthSeed.hybrid_platform_role` — RBAC va CR-03 regressiya darvozalari uchun seed"
affects: [02-bozor-konfiguratsiyasi, 05-kassir-va-tolovlar, 08-xavfsizlik-va-audit, frontend-auth]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Darvoza dependency ENDPOINTGA emas, boshqa dependency ICHIGA ulanadi — unutib bo'lmaydi"
    - "Ko'p bayroqli holat BITTA kesh yozuvida (ikki belgili kod) — ikkita TTL/invalidatsiya nuqtasi bo'lmasin"
    - "Kesh qiymati tanib bo'lmasa `None` -> DB'dan qayta o'qish (fail-to-source, fail-open EMAS)"
    - "Test-yaxlitligi: yangi darvoza mavjud testning 403 SABABINI o'zgartirsa, test dalil-saqlovchi usulda tuzatiladi (assert bo'shashtirilmaydi)"

key-files:
  created:
    - tests/integration/test_password_gate.py
  modified:
    - services/core-api/app/deps.py
    - services/core-api/app/api/v1/users.py
    - services/core-api/app/api/v1/markets.py
    - tests/fixtures/auth_users.py
    - tests/integration/test_audit_read.py
    - tests/integration/test_users_api.py
    - tests/integration/test_me_locale.py
    - tests/tenancy/test_cross_tenant.py

key-decisions:
  - "must_change_password TOKENGA yozilmaydi — u `auth_user_state()` ning o'sha qatoridan, `is_active` bilan birga keladi; aks holda 15 daqiqalik access token parol almashtirilgandan keyin ham qulf bo'lib turardi"
  - "Darvoza javobi 403 `password_change_required`, 401 EMAS: sessiya yaroqli, rad etish sababi HOLATDA — 401 frontendni cheksiz login siklga tushirardi"
  - "Darvoza `get_tenant_session` + `require_permission` + `require_roles` ICHIGA ulandi, endpointlarga qo'lda emas — yangi endpoint uni chetlab o'ta olmaydi"
  - "`platform_admin` roli platforma adminining O'ZIGA ham berilmaydi: gibrid hisob yaratishning qonuniy holati yo'q"
  - "`list_markets` branchi autoritativ bayroqqa bog'landi; huquq roldan hisoblanadi, rol esa a'zolik orqali qo'lga kiritiladi"
  - "Uch mavjud RBAC testi ONBOARDING (parol almashtirish) bilan tuzatildi, assert bo'shashtirish bilan emas"

patterns-established:
  - "Sabotaj-tekshiruv: har bir yangi nazorat uchun uni olib tashlaganda QIZARADIGAN test ko'rsatiladi"
  - "Gibrid/nomuvofiq holatdagi seed foydalanuvchi — nazorat manbasini (huquq vs bayroq) qulflash usuli"

requirements-completed: [FOUND-01, FOUND-02]

# Metrics
duration: 33min
completed: 2026-07-29
---

# Phase 01 Plan 11: Parol darvozasi va platform_admin rolini rad etish Summary

**`require_password_current` darvozasi D-02 ni serverda kuchga kiritdi va `platform_admin` a'zolik roli butunlay yopildi — bozorlar ro'yxati endi `users.is_platform_admin` bayrog'iga bog'langan, huquqqa emas.**

## Performance

- **Duration:** ~33 min
- **Started:** 2026-07-29T19:15:00Z
- **Completed:** 2026-07-29T19:48:00Z
- **Tasks:** 2
- **Files modified:** 8 (1 yaratilgan, 7 o'zgartirilgan)

## Accomplishments

- **CR-01 yopildi.** `must_change_password = true` foydalanuvchi to'liq yaroqli sessiya olsa-da, `/auth/change-password` va `/auth/logout` dan boshqa HECH QANDAY tenant/yozuv endpointiga kira olmaydi. Darvoza `get_tenant_session`, `require_permission` va `require_roles` ning ICHIDAN chaqiriladi — ya'ni yangi endpoint yozgan odam uni "qo'shishni unutishi" mumkin emas.
- **CR-03 backend qismi yopildi.** `platform_admin` a'zolik roli sifatida HECH KIMGA (platforma adminining o'ziga ham) berilmaydi, `list_markets` esa `principal.is_platform_admin` bayrog'ida branch qiladi. Gibrid hisob orqali cross-tenant bozorlar ro'yxati oshkoralashuvi yo'li ikki mustaqil qatlamda yopildi.
- **Test-yaxlitligi saqlandi.** Darvoza uchta mavjud RBAC testining 403 SABABINI o'zgartirardi. Uchalasi ham dalil-saqlovchi usulda tuzatildi: yangi `must_change=false` nazoratchi seed'i va D-02 ning haqiqiy oqimidan (vaqtinchalik parol -> majburiy almashtirish -> qayta kirish) o'tadigan direktor. Bironta assert `password_change_required` ni qabul qilish uchun BO'SHASHTIRILMADI.
- **Ikkala tuzatish ham sabotaj bilan tasdiqlandi** (pastda, "Verification" bo'limi).
- To'liq backend to'plami: **387 test yashil** (375 bazaviy + 12 yangi), `ruff check` / `ruff format --check` / `mypy .` toza.

## Task Commits

1. **Task 1: must_change_password ni serverda kuchga kiritish (CR-01, D-02)** — `d250b1e` (feat)
2. **Task 2: platform_admin rolini rad etish + bozorlar ro'yxatini bayroqqa bog'lash (CR-03, D-04, D-06)** — `4b2d43a` (fix)

## Files Created/Modified

- `services/core-api/app/deps.py` — `Principal.must_change_password`; `_is_user_active` -> `_user_state()` (ikki bayroq, bitta kesh yozuvi, ikki belgili kod); `require_password_current` + `CurrentPasswordDep`; darvoza `get_tenant_session`, `require_permission`, `require_roles` ostiga ulandi.
- `services/core-api/app/api/v1/users.py` — `_assert_roles_assignable` `Role.PLATFORM_ADMIN` ni chaqiruvchidan qat'i nazar rad etadi; `reset_password` `user:state` keshini bekor qiladi (Rule 2, pastda).
- `services/core-api/app/api/v1/markets.py` — `list_markets` `principal.is_platform_admin` bo'yicha branch qiladi; `Permission` importi olib tashlandi; modul va funksiya docstringlaridagi teskari izoh tuzatildi.
- `tests/integration/test_password_gate.py` *(yangi)* — 8 test: darvozaning yopiqligi (uch endpoint), RBAC dan oldin turishi, `/auth/me` ham yopiqligi, `change-password`/`logout` ochiqligi, o'sha token bilan ochilishi (kesh invalidatsiyasi), yangi sessiya, admin parol tiklaganda jonli sessiyaning darhol qulflanishi.
- `tests/fixtures/auth_users.py` — `AuthSeed.inspector` (`must_change=false`) va `AuthSeed.hybrid_platform_role` (`roles=[platform_admin]` + `is_platform_admin=false`); ikkalasi `extra_user_ids` bilan tozalanadi.
- `tests/integration/test_audit_read.py` — `_director` endi ONBOARD qiladi; `test_inspector_cannot_view_the_audit_log` manbai `inspector` ga o'tdi va `detail == "forbidden"` qo'shildi.
- `tests/integration/test_users_api.py` — `_onboarded_headers` yordamchisi; `test_cashier_and_director_cannot_manage_users` direktori onboard qilinadi; ikkita yangi rad etish testi (`platform_admin` roli, jumladan aralashtirib berish).
- `tests/integration/test_me_locale.py` — `test_markets_list_depends_on_market_view_all` -> `..._depends_on_the_platform_admin_flag` (nom endi haqiqatni aks ettiradi); ikkita yangi test, jumladan CR-03 sabotaj darvozasi.
- `tests/tenancy/test_cross_tenant.py` — `/api/v1/markets` istisnosining SABABI qayta yozildi (`global` prefiksi saqlandi), modul docstringiga asos qo'shildi.

## Decisions Made

- **`must_change_password` tokenga yozilmadi.** U `is_active` bilan AYNAN bir qatordan (`auth_user_state()`) va bitta kesh yozuvidan keladi. Tokenga yozilganda parol almashtirilgandan keyin ham 15 daqiqa "hali almashtirilmagan" deb turardi — foydalanuvchi o'z parolini almashtirib ham qulf ortida qolardi.
- **Kesh formati — ikki belgili kod** (`{faol}{majburiy}`), ikkinchi kalit emas. Ikkita kalit ikkita TTL va ikkita invalidatsiya nuqtasi degani; ulardan biri eskirib qolgan holat jimgina paydo bo'lardi.
- **Tanib bo'lmaydigan kesh qiymati = promax** (fail-to-source). Deploy paytida keshda qolgan eski bir belgili qiymat aks holda `must_change=false` deb talqin qilinib, darvozani 30 soniyaga ochib qo'yardi.
- **Bloklash tekshiruvi darvozadan OLDIN.** Bloklangan hisob "parolingizni almashtiring" javobini olmasligi kerak — u umuman kira olmaydi (401 `account_blocked`).
- **`platform_admin` roli platforma adminining o'ziga ham berilmaydi.** "Faqat platforma admini bera oladi" degan yumshoqroq variant aynan gibrid hisob yaratish yo'lini ochiq qoldirardi — bunday rolni a'zolik sifatida berishning qonuniy holati YO'Q.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] `reset-password` `user:state` keshini bekor qilmasdi**

- **Found during:** Task 1 (darvozani `get_tenant_session` ga ulash)
- **Issue:** `must_change_password` endi KIRISH qarorining bir qismi. `POST /users/{id}/reset-password` bu bayroqni `true` qiladi va barcha refresh tokenlarni bekor qiladi, LEKIN `user:state:{id}` keshiga tegmasdi. Qurbonning ACCESS tokeni yana 15 daqiqa yaroqli — ya'ni "parolim boshqasiga ma'lum" shubhasi bilan tiklangan hisob darvoza ostiga faqat 30 soniyadan (TTL) keyin tushardi. Tiklash aynan eng muhim 30 soniyada kuchga kirmasdi.
- **Fix:** `reset_password` ga `CacheDep` + `BackgroundTasks` qo'shildi va `background.add_task(invalidate_user_state, cache, user_id)` chaqiriladi — `block_user`/`unblock_user` bilan aynan bir xil naqsh va bir xil sabab (COMMIT dan keyin).
- **Files modified:** `services/core-api/app/api/v1/users.py`
- **Verification:** `test_password_gate.py::test_admin_password_reset_locks_the_live_session_immediately` — qurbonning mavjud tokeni bilan `GET /auth/me` tiklashdan oldin 200, keyin darhol 403 `password_change_required`.
- **Committed in:** `d250b1e`

**2. [Rule 2 - Missing Critical] `markets.py` tuzatishini ushlaydigan test yo'q edi**

- **Found during:** Task 2 (rejadagi 4-band testini yozish)
- **Issue:** Reja `test_market_admin_markets_list_returns_only_own_market` ni so'radi, lekin bozor adminida `MARKET_VIEW_ALL` UMUMAN YO'Q — ya'ni bu test tuzatishdan OLDIN ham yashil bo'lardi va `list_markets` branchining manbasi haqida hech nima isbotlamasdi. CR-03 ning haqiqiy hujum yo'li — huquqi BOR, bayrog'i YO'Q gibrid hisob — hech qanday test bilan qoplanmagan bo'lardi.
- **Fix:** `AuthSeed.hybrid_platform_role` seed'i (`roles=["platform_admin"]`, `is_platform_admin=false`, DB'ga to'g'ridan-to'g'ri — API orqali endi yaratib bo'lmaydi) va `test_market_view_all_without_the_flag_sees_only_its_own_market`. Test avval `GET /auth/me` bilan gibrid hisobda `market_view_all` HAQIQATAN borligini tasdiqlaydi (nazorat holati), keyin bozorlar ro'yxati faqat o'z bozorini qaytarishini.
- **Files modified:** `tests/fixtures/auth_users.py`, `tests/integration/test_me_locale.py`
- **Verification:** Sabotaj — branch `Permission.MARKET_VIEW_ALL` ga qaytarilganda test QIZARDI (gibrid hisob ikkala bozorni ko'rdi), tiklangach yashil.
- **Committed in:** `4b2d43a`

**3. [Rule 2 - Missing Critical] `require_roles` darvozasiz qolgan edi**

- **Found during:** Task 1
- **Issue:** Reja darvozani `get_tenant_session` va `require_permission` ga ulashni so'radi. `require_roles` — uchinchi rad etish yo'li (hozircha endpointlarda ishlatilmaydi, lekin eksport qilingan). Darvozasiz qolsa, u birinchi ishlatilgan kunidayoq darvozani chetlab o'tish yo'liga aylanardi.
- **Fix:** `require_roles` ning ichki `_require` si ham `CurrentPasswordDep` ga bog'landi.
- **Files modified:** `services/core-api/app/deps.py`
- **Verification:** `mypy .` toza; xulq o'zgarishi yo'q (hozircha iste'molchisi yo'q). Reja mezoni "kamida `get_tenant_session` va `require_permission`" deb yozilgan — bu uni kengaytiradi, buzmaydi.
- **Committed in:** `d250b1e`

### Rejadan ongli chekinishlar (yaxshilash)

**4. [Rule 1 - Bug] Test nomi yolg'onga aylangan edi**

- **Found during:** Task 2
- **Issue:** `test_markets_list_depends_on_market_view_all` — CR-03 dan keyin branch `MARKET_VIEW_ALL` ga umuman bog'liq emas. Nom hujjat sifatida mavjud bo'lmagan bog'liqlikni tasdiqlardi.
- **Fix:** `test_markets_list_depends_on_the_platform_admin_flag` ga o'zgartirildi; docstringda testning O'ZI CR-03 ni ushlamasligi va uni qaysi test ushlashi aniq yozildi. Reja bunga aniq ruxsat bergan ("...yoki bayroq-asosli branchga moslashtir").
- **Files modified:** `tests/integration/test_me_locale.py`
- **Committed in:** `4b2d43a`

**5. Rejadagi `test_market_admin_cannot_assign_platform_admin_role` yozilmadi (allaqachon mavjud)**

- Reja 3(b) bandida bozor admini uchun ham alohida test so'ragan edi. Bu holat ALLAQACHON ikki test bilan qoplangan: `test_market_admin_cannot_create_platform_admin` (403 `role_not_allowed`) va parametrizatsiyalangan `test_market_admin_cannot_assign_privileged_role_leaves_no_trace[platform_admin]` (qoldiqsizlik). Uchinchi nusxa yozish hech qanday yangi hujumni yopmasdi. Uning o'rniga qoplanmagan yo'l uchun `test_platform_admin_cannot_smuggle_the_platform_admin_role` (aralashtirib berish) qo'shildi.

---

**Total deviations:** 5 (3 Rule 2 — yetishmayotgan kritik nazorat/test, 1 Rule 1 — yolg'on test nomi, 1 rejadagi ortiqcha ishni tushirish)
**Impact on plan:** Uchala Rule 2 tuzatishi ham darvoza/branch tuzatishining O'ZINI to'liq qiladi (biri xavfsizlik teshigi, ikkinchisi tuzatishning isbotsiz qolishi, uchinchisi chetlab o'tish yo'li). Doiradan chiqish yo'q — barcha o'zgarishlar reja `files_modified` ro'yxati ichida.

## Verification

| Da'vo | Buyruq / test | Natija |
| --- | --- | --- |
| To'liq backend to'plami | `docker compose --profile test run --rm tests pytest -q` | **387 passed** (375 bazaviy + 12 yangi) |
| Lint / format / tiplar | `ruff check . && ruff format --check . && mypy .` | toza (84 fayl) |
| must-change 403 `password_change_required` (GET/POST /users, GET /audit) | `test_must_change_user_is_locked_out_of_every_gated_endpoint` | passed |
| Darvoza RBAC dan OLDIN | `test_the_gate_precedes_the_permission_check` | passed |
| `change-password` 204, keyin o'sha token bilan 200/201 | `test_change_password_stays_open`, `test_the_same_token_works_after_the_password_change` | passed |
| Parol tiklash jonli sessiyani darhol qulflaydi | `test_admin_password_reset_locks_the_live_session_immediately` | passed |
| Nazoratchi `GET /audit` 403 **`forbidden`** (darvoza EMAS) | `test_inspector_cannot_view_the_audit_log` | passed |
| Onboarded direktor `GET /audit` 200 | `test_director_can_view_the_audit_log` | passed |
| Onboarded direktor `POST /users` 403 **`forbidden`** | `test_cashier_and_director_cannot_manage_users` | passed |
| Platforma admini `roles=["platform_admin"]` -> 403 + DB'da qoldiq yo'q | `test_platform_admin_cannot_assign_the_platform_admin_role` | passed |
| Gibrid hisob (huquq bor, bayroq yo'q) faqat o'z bozorini ko'radi | `test_market_view_all_without_the_flag_sees_only_its_own_market` | passed |

### Sabotaj tekshiruvlari (nazorat olib tashlanganda test QIZARADIMI)

| Sabotaj | Kutilgan | Natija |
| --- | --- | --- |
| `get_tenant_session` dagi `CurrentPasswordDep` -> `PrincipalDep` | darvoza testlari qizaradi | **FAILED:** `test_session_endpoint_is_gated_too`, `test_admin_password_reset_locks_the_live_session_immediately` — tiklangach ikkalasi ham yashil |
| `list_markets` branchi -> `Permission.MARKET_VIEW_ALL` | gibrid test qizaradi | **FAILED:** `test_market_view_all_without_the_flag_sees_only_its_own_market` (gibrid hisob IKKALA bozorni ko'rdi) — tiklangach yashil |

## Issues Encountered

- `ruff format` ikkita funksiyani bir qatorga siqishni talab qildi (ikkalasi ham aynan 100 belgi). `_encode_state` ni ikki oraliq o'zgaruvchiga bo'lish o'qilishini ham yaxshiladi, `_create_cashier` imzosi esa bir qatorga sig'di. Boshqa hech qanday to'siq bo'lmadi.

## Known Stubs

Yo'q — bu plan mavjud, ishlaydigan kodga xirurgik tuzatish kiritdi; hech qanday joy-egallovchi qiymat yoki ulanmagan komponent qoldirilmadi.

## Threat Flags

Yangi xavfsizlik yuzasi qo'shilmadi (yangi endpoint, yangi tashqi ulanish, yangi sxema o'zgarishi yo'q). Reja `<threat_model>` idagi T-01-80, T-01-81, T-01-82, T-01-83 — to'rttasi ham `mitigate` dispozitsiyasi bilan yopildi va har biri test bilan qulflandi. T-01-WR02 (`409 phone_taken` cross-tenant existence oracle) — `accept` bo'lib qoladi, 8-fazaga qoldirilgan.

## User Setup Required

Yo'q — tashqi servis sozlash talab qilinmaydi.

## Next Phase Readiness

- **Frontend (01-12) uchun tayyor.** Backend endi `403 {"detail": "password_change_required"}` qaytaradi — frontend `api-types.ts` da bu kod ALLAQACHON zaxiralangan. `assignableRoles()` dan `platform_admin` ni olib tashlash va `role-gate.test.mjs` ni yangilash 01-12 doirasida (backend endi bu rolni baribir rad etadi, ya'ni ikkalasi mustaqil).
- **Ochiq qolgan qism:** `/api/v1/me` (PROFIL: telefon, ism, til) darvozadan ATAYIN tashqarida — u `AuthSessionDep` bilan ishlaydi. Ya'ni must-change foydalanuvchi parol almashtirish ekranida o'z tilini o'zgartira oladi. Bu qasddan: aks holda foydalanuvchi tanlash ekranini o'zi tushunmaydigan tilda ko'rardi (D-13).
- **Kelajakdagi eslatma:** `must_change_password` ni o'zgartiradigan HAR QANDAY yangi yo'l `invalidate_user_state()` ni chaqirishi SHART. Hozir uchta joy bor: `auth.py::change_password`, `users.py::reset_password`, `users.py::_set_member_active` (bloklash).

## Self-Check: PASSED

- Barcha da'vo qilingan fayllar diskda mavjud (10/10).
- Ikkala task commiti `git log` da mavjud: `d250b1e`, `4b2d43a`.
- STATE.md va ROADMAP.md O'ZGARTIRILMADI (worktree rejimi — ularni orkestrator yozadi).
- Reja `files_modified` ro'yxatidan tashqarida birorta fayl ham o'zgartirilmadi.

---
*Phase: 01-poydevor-va-tenant-xavfsizligi*
*Completed: 2026-07-29*
