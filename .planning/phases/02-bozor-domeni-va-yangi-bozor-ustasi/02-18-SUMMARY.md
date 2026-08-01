---
phase: 02-bozor-domeni-va-yangi-bozor-ustasi
plan: 18
subsystem: ui
tags: [routing, navigation, rbac, empty-state, i18n, wizard, gap-closure, sabotage, gate]

# Dependency graph
requires:
  - phase: 02-bozor-domeni-va-yangi-bozor-ustasi
    provides: "02-16 — usta ekranlari (`markets/new/page.tsx`, `WizardShell`, `wizard-steps.ts::WIZARD_SETUP_PATH`) va ularning o'z `market_manage` + `isPlatformAdmin` darvozasi; 02-11 — `POST /markets`, `setup-status`, `PLATFORM_ADMIN_ROUTES`; 02-02 — `app-shell.tsx` uch guruhli navigatsiya va `NavMoreSheet`"
  - phase: 01-poydevor-va-tenant-xavfsizligi
    provides: "`(app)/layout.tsx` uch qoidali darvozasi (D-03/D-02/D-06), `auth-store.ts::updatePrincipal`, `api-client.ts::apiRequest`/`errorMessageKey`, `rbac.ts::hasPermission`, `market-picker.tsx` (D-06), vitest komponent yugurtgichi va `scripts/*.test.mjs` manba darvozasi naqshi"
provides:
  - "`(app)/layout.tsx` — `/markets/new` uchun marshrut istisnosi (`needsMarket`), IKKALA joyda: redirect effekti va `ready` ifodasi"
  - "`app-shell.tsx` — `market_manage` bilan himoyalangan «Yangi bozor» navigatsiya yozuvi (`system` guruhi, ro'yxat oxirida)"
  - "`market-picker.tsx` — bo'sh bozor ro'yxatida «Birinchi bozorni yaratish» birlamchi amali (UI-SPEC §9.2), «Chiqish» saqlangan holda"
  - "`api-client.ts` — 403 `password_change_required` javobida store'ni server verdikti bilan moslash (WR-09) + `auth.passwordChangeRequired` xato kaliti"
  - "`frontend/scripts/wizard-reachability.test.mjs` — uchala to'siqni alohida-alohida qulflaydigan manba darvozasi (izoh-filtrli)"
  - "3 ta yangi i18n kaliti × 3 til: `nav.newMarket`, `wizard.createFirstMarket`, `auth.passwordChangeRequired`"
affects: [02-23, 03-kamera, 06-hisob-kitob]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Marshrut istisnosi PREFIKS emas, TENGLIK bilan yoziladi — `startsWith` butun himoyalangan daraxtga huquq oshirish yuzasi ochadi"
    - "Bitta shart IKKI joyda ishlatilsa (effekt + `ready`) bu takror emas: biri redirectni, ikkinchisi ekranning ochilishini boshqaradi va yarim tuzatish 'abadiy skelet' beradi"
    - "Server 403 ni ATAYIN tanlagan bo'lsa klient `clearSession()` qilmaydi — store server verdikti bilan MOSLANADI va mavjud layout qoidasi yo'naltirishni o'zi bajaradi"
    - "Manba darvozasi izoh qatorlarini filtrlaydi, aks holda fayl DOCSTRINGI darvozani o'z-o'ziga qarshi qo'yadi"
    - "Manba darvozasi identifikator NOMINI emas, MEXANIZMNI qulflaydi: qo'riqchi nomi regexdan olinadi va uning kelib chiqishi (pathname'dan) tekshiriladi — qayta nomlash darvozani buzmaydi"
    - "`buttonVariants` bilan stillangan `<Link>` — ko'rinish dizayn tizimidan, semantika havoladan"

key-files:
  created:
    - frontend/src/app/[locale]/(app)/layout.test.tsx
    - frontend/src/components/shell/app-shell.test.tsx
    - frontend/scripts/wizard-reachability.test.mjs
  modified:
    - frontend/src/app/[locale]/(app)/layout.tsx
    - frontend/src/components/shell/app-shell.tsx
    - frontend/src/components/auth/market-picker.tsx
    - frontend/src/components/auth/market-picker.test.tsx
    - frontend/src/lib/api-client.ts
    - frontend/messages/uz-Latn.json
    - frontend/messages/ru.json
    - frontend/messages/uz-Cyrl.json

key-decisions:
  - "Istisno AYNAN bitta literal marshrutga (`pathname !== WIZARD_NEW_PATH`) bog'landi — prefiks emas (T-02-140); `layout.test.tsx` da `/markets/new-anything` nazorat holati bilan qulflandi"
  - "`needsMarket` ikkala joyda ham qo'llandi (effekt + `ready`) — yarim tuzatish 'redirect yo'q, lekin ekran ham yo'q' holatini bergan bo'lardi"
  - "WR-09 da `clearSession()` EMAS, `updatePrincipal({mustChangePassword:true})` — server 401 ni ataylab rad etgan (`deps.py:389-412`) va sessiyani tozalash o'sha rad etilgan redirect siklini orqa eshikdan qaytarardi; yangi redirect mantiqi UMUMAN yozilmadi"
  - "Navigatsiya yozuvi `NAV_ITEMS` OXIRIDA va `system` guruhida — mobil pastki panelning 'eng ko'pi 5 element' kontrakti (UI-SPEC §12.3) shu tanlov bilan saqlanadi"
  - "Bo'sh holatdagi «Chiqish» tugmasi SAQLANDI — `market_manage` siz foydalanuvchi uchun u yagona chiqish yo'li; havola bir boshi berk ko'chani ikkinchisiga almashtirmasligi kerak"
  - "Manba darvozasi konstanta NOMLARINI qattiq yozmaydi — qo'riqchi identifikatori regexdan olinadi va uning kelib chiqishi tekshiriladi"
  - "`MOBILE_MAX_PRIMARY = 4` testda import qilinmay, qo'lda yozildi — import qilinsa test implementatsiyani o'ziga o'zi tasdiqlatardi"

patterns-established:
  - "Pattern: marshrut darvozasi testi `usePathname` ni mock obyektining MAYDONI orqali beradi va har test o'z yo'lini o'rnatadi"
  - "Pattern: layout testida `AppShell` mock qilinadi — marshrut qarori va qobiq da'volari ikki faylda alohida o'lchanadi"
  - "Pattern: `apiRequest` ning xato tarmog'i `vi.stubGlobal('fetch', ...)` bilan, HAQIQIY kod ustida sinaladi (`importOriginal` faqat `apiFetch` ni almashtiradi)"
  - "Pattern: manba darvozasi har assertda 'qaysi TO'SIQ qaytdi' degan sabab matnini beradi"

requirements-completed: []

# Metrics
duration: 100min
completed: 2026-08-01
---

# Phase 2 Plan 18: Ustaga yetib borish yo'li (CR-03) Summary

**«Yangi bozor» ustasi uchala to'siqdan ozod qilindi — marshrut istisnosi, `market_manage` bilan himoyalangan menyu yozuvi va bo'sh ro'yxatdagi «Birinchi bozorni yaratish» havolasi; yo'l 12 ta vitest + 3 ta manba darvozasi testi bilan qulflandi va 5 ta sabotaj bilan o'lchandi.**

## Holat

**Rejaning avtomatik qamrovi — TUGALLANGAN.** Uchala task ham yetkazildi va commit qilindi, shu jumladan 3-taskning artefakti (`frontend/scripts/wizard-reachability.test.mjs`). `npm run gate` yashil (exit 0).

**CR-03 ning KOD bo'shlig'i yopildi va mustaqil tekshiriladi.** Bu da'vo `npm run gate` bilan isbotlanadi va uni har kim qayta yugurtira oladi.

**CR-03 ning FOYDALANUVCHANLIK tasdig'i esa OCHIQ va u `02-23` ga o'tkazildi** (pastdagi bo'limga qarang). Ikkala da'vo ATAYIN ajratilgan va birlashtirilmaydi: «yo'l bor» — o'lchangan; «yo'l topiladi» — hali o'lchanmagan.

## Performance

- **Duration:** ~100 min
- **Started:** 2026-08-01T06:38:00Z
- **Completed:** 2026-08-01T07:20:00Z
- **Tasks:** 3/3 (avtomatik qamrov to'liq; Manual-Only #2 `02-23` ga o'tkazildi)
- **Files modified:** 11 (3 yangi, 8 tahrir)

## Accomplishments

- **1-to'siq (marshrut).** `(app)/layout.tsx` endi `/markets/new` ni `marketId` talabidan ozod qiladi. Tuzatish IKKI joyda: redirect effektida va `ready` ifodasida — chunki faqat effekt tuzatilsa ekran abadiy skelet bo'lib qolardi, faqat `ready` tuzatilsa effekt sahifani ochilishi bilanoq surib yuborardi.
- **2-to'siq (topilishi).** `app-shell.tsx` ga `market_manage` bilan himoyalangan «Yangi bozor» yozuvi qo'shildi. Yozuv `NAV_ITEMS` oxirida va `system` guruhida — mobil pastki panelning "eng ko'pi 5 element" kontrakti buzilmadi (o'lchandi: panelda hamon 4 havola + «Ko'proq»).
- **3-to'siq (bootstrap).** `market-picker.tsx` ning bo'sh ro'yxat tarmog'i UI-SPEC §9.2 shakliga keltirildi: «Birinchi bozorni yaratish» birlamchi amali + saqlangan «Chiqish». Toza platformada birinchi bozorni yaratish yo'li endi mahsulotning o'zidan o'tadi.
- **WR-09.** Sessiya o'rtasida `password_change_required` olgan foydalanuvchi endi boshi berk ko'chada qolmaydi: `api-client.ts` store'ni server verdikti bilan moslaydi va mavjud layout qoidasi keyingi renderda `/change-password` ga olib boradi. **Yangi redirect mantiqi yozilmadi.**
- **Darvoza.** `wizard-reachability.test.mjs` uchala to'siqni alohida-alohida qulflaydi va `npm run test:unit` (ya'ni `npm run gate`) ichida avtomatik ishlaydi — `package.json` ga tegilmadi.

## Task Commits

1. **Task 1: Marshrut istisnosi va navigatsiya yozuvi** — `6468af4` (feat)
2. **Task 2: Bo'sh ro'yxat havolasi va WR-09** — `30a6659` (feat)
3. **Task 3: Yetib borish darvozasi** — `1cbca80` (test)

_TDD tsikli fayl ichida bajarildi: har taskda avval test yozilib QIZARTIRILDI (o'lchangan), keyin kod yozildi. RED holatlar quyida «Sabotaj o'lchovlari» bo'limida qayd etilgan._

## Files Created/Modified

**Yangi:**
- `frontend/src/app/[locale]/(app)/layout.test.tsx` — marshrut darvozasining 5 ta testi (istisno, `/stalls` nazorati, parol ustunligi, T-02-140 prefiks nazorati, bozorli admin)
- `frontend/src/components/shell/app-shell.test.tsx` — navigatsiya yozuvining 4 ta testi (ko'rinadi, huquqsizda ko'rinmaydi, mobil panel kontrakti, «Tizim» guruhi)
- `frontend/scripts/wizard-reachability.test.mjs` — uchala to'siqning manba darvozasi (3 test, izoh-filtrli)

**Tahrir:**
- `frontend/src/app/[locale]/(app)/layout.tsx` — `usePathname` + `WIZARD_NEW_PATH` + `needsMarket`; docstringga istisno bandi
- `frontend/src/components/shell/app-shell.tsx` — `NavItem` unionlariga `/markets/new` va `newMarket`; `NAV_ITEMS` oxiriga yozuv
- `frontend/src/components/auth/market-picker.tsx` — `canCreate` + bo'sh holatdagi `<Link>`; modul docstringiga bo'sh holat bandi
- `frontend/src/components/auth/market-picker.test.tsx` — +6 test (3 bo'sh holat, 3 WR-09), `Link` mock'i
- `frontend/src/lib/api-client.ts` — 403 `password_change_required` tarmog'i + `ErrorMessageKey` kengaytmasi
- `frontend/messages/{uz-Latn,ru,uz-Cyrl}.json` — 3 kalit × 3 til (418 → 421)

## Test hisobi

| To'plam | Oldin | Keyin | Farq |
|---------|-------|-------|------|
| `test:unit` (`node --test scripts/*.test.mjs`) | 54 | **57** | +3 (manba darvozasi) |
| `test:component` (vitest) | 40 | **55** | +15 (5 layout + 4 app-shell + 6 market-picker) |
| **Frontend jami** | **94** | **112** | **+18** |

Birorta mavjud test qizarmadi.

## Sabotaj o'lchovlari (5 ta)

Har biri qo'lda kiritildi, o'lchandi va bayt-baytga qaytarildi (`git diff --stat` bo'sh).

| # | Sabotaj | Kutilgan | O'lchangan natija |
|---|---------|----------|--------------------|
| 1 | `layout.tsx` dan `needsMarket &&` olib tashlandi | faqat «`/markets/new` da redirect yo'q» qizaradi | **1 failed / 49** — aynan o'sha test; qolgan 48 yashil |
| 2 | `NAV_ITEMS` yozuvining `permission` i `null` ga o'zgartirildi | faqat «huquqsiz rolda ko'rinmaydi» qizaradi | **1 failed / 49** — aynan o'sha nazorat testi |
| 3 | `market-picker.tsx` da `canCreate` `false` ga qotirildi | faqat «havola ko'rinadi» qizaradi | **1 failed / 55** — aynan o'sha test |
| 4 | `apiRequest` dan `updatePrincipal({mustChangePassword:true})` olib tashlandi | faqat WR-09 testi qizaradi | **1 failed / 55** — aynan o'sha test; nazorat (`role_not_allowed`) yashil qoldi |
| 5 | `NAV_ITEMS` dagi yangi yozuv butunlay o'chirildi | manba darvozasining AYNAN 2-testi qizaradi | **1 failed / 3** — 2-test qizardi, 1- va 3-testlar yashil qoldi |

**5-sabotaj alohida qiymat berdi:** yozuv o'chirilganda uning ustidagi izoh bloki (unda `/markets/new` ham, `market_manage` ham MATN sifatida bor) faylda **qoldi** va darvoza baribir qizardi. Bu — izoh filtrining ishlayotganining to'g'ridan-to'g'ri empirik isboti, taxmin emas.

RED bosqichlari ham o'lchandi: 1-taskda 3 ta yangi test (1 layout + 2 app-shell) kod yozilishidan oldin aynan kutilgan sabab bilan qizardi; 2-taskda 3 ta test (1 havola + 2 WR-09) shunday qizardi. Har ikkala holatda ham nazorat testlari **boshidanoq yashil** edi, ya'ni ular yangi xulqni emas, mavjudini qo'riqlaydi.

## Decisions Made

- **Prefiks emas, tenglik (T-02-140).** `startsWith` bo'lsa `/markets/new-anything` ham bozorsiz ochilib, butun `(app)` daraxtiga huquq oshirish yuzasi paydo bo'lardi. `layout.test.tsx` da alohida nazorat holati bor va manba darvozasi ham buni tekshiradi.
- **WR-09 da sessiya tozalanmaydi.** Server 403 ni ATAYIN tanlagan (401 sessiyani uzib redirect siklini tug'dirardi). To'g'ri javob — store'ni server bilan moslash; yo'naltirishni mavjud layout qoidasi bajaradi. Yangi redirect mantiqi yozilmagani uchun yangi sikl xavfi ham tug'ilmadi.
- **⚠ REJADAN TASHQARI, LEKIN HAL QILUVCHI TEKSHIRUV — `canCreate` gati bootstrap holatida haqiqatan ishlaydimi?** Reja buni talab qilmagan, lekin javob «yo'q» bo'lganda **butun tuzatish bekor bo'lardi va buni birorta test ushlamasdi**: agar bozorsiz platforma admini `roles: []` bilan kelsa, `hasPermission(roles, "market_manage")` `false` qaytarib, «Birinchi bozorni yaratish» havolasi AYNAN o'zi uchun yaratilgan holatda ko'rinmasdi — ya'ni 3-to'siq qog'ozda yopilib, amalda ochiq qolardi. `services/core-api/app/api/v1/auth.py::_session_roles` o'qildi: u `is_platform_admin` bo'lsa a'zolik qatorisiz ham `platform_admin` rolini qo'shadi (`login` yo'lida `auto_select is None` bo'lsa ham), ya'ni bozorsiz login javobi `roles: ["platform_admin"]` beradi va gat ishlaydi. Test seed'i shu O'LCHANGAN haqiqatga moslandi (`seedSessionWithoutMarkets`); mavjud `seedSessionWithMarkets` dagi bo'sh `roles: []` — 1-fazadan qolgan soddalashtirish va u ATAYIN takrorlanmadi, aks holda test o'zi tekshirmoqchi bo'lgan huquqni yo'q qilib qo'yardi.
- **Manba darvozasi nomlarni emas, mexanizmni qulflaydi.** Qo'riqchi identifikatori regexdan olinadi, keyin uning `pathname !== <const>` dan kelib chiqishi va konstantaning qiymati tekshiriladi. Qayta nomlash darvozani buzmaydi; mantiqni yo'q qilish buzadi.
- **`MOBILE_MAX_PRIMARY` testda qo'lda yozildi.** `MOBILE_PRIMARY_COUNT` ni import qilish testni implementatsiyaga tasdiqlatib qo'yardi (konstanta 8 ga o'zgarsa test ham 8 ni kutib, jimgina yashil qolardi). Test WCAG 2.5.8 dan kelib chiqadigan SONNI qo'riqlaydi.
- **v2 qarori saqlandi.** `market-picker.tsx` dagi «DEFERRED (v2): bozorni ALMASHTIRISH UI'si ATAYIN yo'q» bandiga tegilmadi — yangi bozor YARATISH bozorni ALMASHTIRISH emas.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Worktree'da frontend bog'liqliklari o'rnatilmagan edi**
- **Found during:** Task 1 (birinchi RED yugurtish)
- **Issue:** Parallel worktree toza checkout — `frontend/node_modules` yo'q, `vitest` ishga tushmadi (`Cannot find module '@vitejs/plugin-react'`).
- **Fix:** `npm ci` (frontend). Bu YANGI paket o'rnatish EMAS — `package-lock.json` dagi qulflangan daraxtni tiklash, ya'ni slopsquatting darvozasi qo'llanmaydi.
- **Files modified:** hech biri (`package.json` va `package-lock.json` o'zgarmadi — `git diff --exit-code frontend/package.json package.json` yashil)
- **Verification:** `npm run test:component` ishga tushdi; T-02-SC qabul mezoni bajarildi.
- **Committed in:** — (fayl o'zgarishi yo'q)

**2. [Rule 1 - Bug] Manba darvozasining birinchi versiyasi noto'g'ri satrni qo'riqlagan edi**
- **Found during:** Task 3 (darvozaning birinchi yugurtishi)
- **Issue:** `principal.marketId === null` fayl bo'ylab IKKI marta uchraydi — redirect effektida va profil to'ldirish effektida (`if (principal.marketId === null || enrichStarted.current) return;`). Darvoza "sharti bitta joyda" deb assert qilib, to'g'ri kod ustida qizardi.
- **Fix:** Darvoza endi satrlarni emas, aynan `router.replace("/select-market")` bayonotining OLDIDAGI shartni tekshiradi. Profil effekti (reja bo'yicha tegilmaydigan va to'g'ri) darvoza ko'rish maydonidan chiqdi.
- **Files modified:** `frontend/scripts/wizard-reachability.test.mjs`
- **Verification:** 3/3 test yashil; 5-sabotaj bilan darvozaning hamon sezuvchan ekani o'lchandi.
- **Committed in:** `1cbca80`

**3. [Rule 1 - Bug] `layout.test.tsx` teardown'da butun faylni yiqitardi**
- **Found during:** Task 1 (RED bosqichi)
- **Issue:** `afterEach(clearSession)` sessiyani bo'shatganda komponent hali montajda turadi, `hasSession` `false` bo'ladi va tiklash effekti qayta ishga tushadi. Qiymatsiz `vi.fn()` `undefined` qaytarib, `undefined.then` bilan 5 ta «Uncaught Exception» berdi.
- **Fix:** `beforeEach` da `restoreSession.mockResolvedValue(false)` — mock HAR DOIM promise qaytaradi.
- **Files modified:** `frontend/src/app/[locale]/(app)/layout.test.tsx`
- **Verification:** 5/5 test toza yashil, birorta uncaught exception yo'q.
- **Committed in:** `6468af4`

---

**Total deviations:** 3 auto-fixed (1 blocking, 2 bug)
**Impact on plan:** Hech biri qamrovni kengaytirmadi. 1-si muhit tiklash, 2- va 3-si o'z artefaktlarimizdagi defektlar. Reja `files_modified` ro'yxatidan tashqariga BIRORTA fayl chiqmadi.

## Issues Encountered

- **`docker compose` ogohlantirishlari bo'yicha xato xulosa chiqarildi va u TUZATILDI.** `docker compose ps` `POSTGRES_PASSWORD`/`JWT_SECRET` va boshqalarni "not set, defaulting to blank string" deb ogohlantiradi (`.env` `.gitignore` da va u na worktree'da, na asosiy repoda bor). Bundan "backend darvozasi bu muhitda ishga tushmaydi" degan xulosa chiqarilgan edi va u SUMMARY'ga **yozilib ham qo'yilgandi**. Xulosa **noto'g'ri**: `npm run test` mustaqil qayta yugurtirildi va **890 ta backend testi to'liq o'tdi (exit 0)** — ogohlantirishlar `tests` profili uchun kosmetik. Da'vo taxmin ustiga emas, o'lchov ustiga qayta qurildi.
- **Colocated test fayli marshrutga aylanmadi.** `layout.test.tsx` `app/` daraxti ichida turadi; `next build` chiqishida u marshrutlar ro'yxatida YO'Q (faqat `page.tsx`/`layout.tsx` kabi maxsus nomlar marshrut bo'ladi). Bu ataylab tekshirildi, chunki teskarisi ishlab chiqarish build'iga test kodini olib kirardi.
- **`git stash` ishlatilmadi.** Beshta sabotaj `Edit` bilan kiritilib, `Edit` bilan qaytarildi va har safar `git diff --stat` bo'shligi bilan tasdiqlandi (worktree'da `stash` global `refs/stash` ga tegadi).

## Verification

| Qadam | Buyruq | Natija |
|-------|--------|--------|
| To'liq darvoza | `npm run gate` | **exit 0** |
| Backend testlari | `npm run test` (mustaqil qayta yugurtirildi) | **890 passed**, exit 0 |
| Tenant izolyatsiyasi | `npm run test:tenancy` (gate ichida) | ✓ |
| i18n pariteti | `npm --prefix frontend run i18n:check` | 421 kalit × 3 til, drift yo'q |
| Frontend testlari | `npm --prefix frontend test` | **112 passed** (57 unit + 55 komponent) |
| Tiplar | `npm --prefix frontend run typecheck` | exit 0 |
| Lint | `npm --prefix frontend run lint` | exit 0 |
| Build | `npm --prefix frontend run build` | exit 0; `/[locale]/markets/new` uchala locale uchun prerender |
| Bog'liqlik drifti | `git diff --exit-code frontend/package.json package.json` | o'zgarish yo'q (T-02-SC) |

## Known Stubs

Yo'q. Bu rejada qattiq yozilgan bo'sh qiymat, «coming soon» matni yoki manbaga ulanmagan komponent qo'shilmadi. Uchala to'siq ham haqiqiy holatga (`principal.marketId`, `principal.roles`, `options.length`) ulangan.

## Threat Flags

Yo'q — yangi tarmoq endpointi, auth yo'li, fayl kirish naqshi yoki sxema o'zgarishi kiritilmadi. Reja `<threat_model>` idagi `mitigate` dispozitsiyalari (T-02-140, T-02-142, T-02-143, T-02-144) bajarildi va har biri test bilan qulflandi; T-02-141 rejadagidek `accept (qatlamlangan)` bo'lib qoldi.

## ⏭ O'TKAZILGAN BAND — foydalanuvchanlik kuzatuvi (02-VALIDATION.md Manual-Only #2)

**Holat: O'TKAZILMAGAN va bu rejada BAJARILMAYDI. Egasi — `02-23`.**

Bu **kutilayotgan tasdiq emas, egasi bor o'tkazma**. `02-23` `02-VALIDATION.md` faylini va TO'RTALA Manual-Only bandini birga olib boradi (#1 real ma'lumot solishtiruvi, **#2 foydalanuvchanlik kuzatuvi**, #3 haqiqiy qurilmada idrok tekshiruvi, #4 rekvizit formatini mijoz bilan tasdiqlash), shuningdek `nyquist_compliant` bayrog'ini oxirida o'zi qaytaradi. Shu sababli #2 shu yerda yopilmaydi — u qolgan uchtasi bilan BIR O'TISHDA, odam haqiqatan mavjud bo'lganda imzolanadi.

- **Kim:** — (`02-23` da belgilanadi)
- **Qachon:** — (`02-23` da belgilanadi)
- **To'xtalish nuqtalari soni:** o'lchanmagan

**Nega bu yerda emas:** kuzatuvning hal qiluvchi sharti — **dasturchi bo'lmagan odam**, va u avtonom ijrochi uchun mavjud emas. (Stek cheklov EMAS: `npm run gate` shu muhitda to'liq o'tdi, ya'ni `docker compose` ishlaydi va bozorsiz platforma admini seed'i texnik jihatdan yaratilishi mumkin.) Kuzatuvni ijrochining o'zi "o'ynab chiqishi" esa uni **butunlay ma'nosiz** qilardi: rejani yozgan va kodni yozgan agent yo'lni tabiiy ravishda topadi — o'lchanayotgan narsa aynan shu emas. «Bajarildi» deb belgilash esa aynan `02-VALIDATION.md` ga — vazifasi nima tekshirilgan va nima tekshirilmaganini halol saqlash bo'lgan yagona artefaktga — yolg'on yozuv kiritardi.

**Nima uchun buni manba tekshiruvi BILAN ALMASHTIRIB BO'LMAYDI:** SC#1 ning da'vosi «kod yozilmaydi», ya'ni u odamning yo'lni O'ZI topishi haqida. Avtomatik darvozalar «yo'l bor» ni isbotlaydi, «yo'l topiladi» ni emas.

**Quyidagi 7 band — kuzatuvni o'tkazadigan odam uchun YO'RIQNOMA** (u shu holicha `02-23` ga ko'chiriladi):

1. Toza stek ko'tariladi va bozori bo'lmagan platforma admini yaratiladi.
2. Dasturchi bo'lmagan odam `/uz` ga kirib login qiladi; kuzatuvchi **yordam bermaydi**.
3. Kutilgan yo'l: login → bo'sh bozor tanlash ekrani → «Birinchi bozorni yaratish» → usta 1-qadam → … → 7-qadam → faollashtirish.
4. Har to'xtalish nuqtasi yoziladi: qaysi ekran, nima kutilgan, nima ko'rilgan.
5. Ikkinchi o'tish: **bozori bor** admin bilan kirib, yon paneldagi «Yangi bozor» topiladimi va ikkinchi bozor yaratiladimi?
6. 360px kenglikda pastki panel ≤5 element ko'rsatayotgani va «Yangi bozor» «Ko'proq» varag'ida ekani (UI-SPEC §12.3).
7. `/ru` da menyu yorlig'i («Новый рынок») va bo'sh holat havolasi («Создать первый рынок») ikki qatorga tushmayotgani (§5.1).

**6- va 7-bandlar uchun avtomatik/o'lchangan dalil ALLAQACHON bor** (odam tasdig'ining o'rnini bosmaydi, lekin xavfni kamaytiradi):
- 6-band: `app-shell.test.tsx` mobil panelda ≤4 havola + 1 «Ko'proq» tugmasini o'lchaydi va «Yangi bozor» u yerda YO'Qligini tasdiqlaydi.
- 7-band: `nav.newMarket` = «Новый рынок» (13 belgi, uz-Latn'dagi «Yangi bozor» — 12); `wizard.createFirstMarket` = «Создать первый рынок» (22 belgi, uz-Latn — 26). Ikkala juftlik ham §5.1 ning «2× o'sishga chidash» chegarasidan ancha pastda va tugmalarda qat'iy kenglik yo'q (`buttonVariants` → `whitespace-nowrap` + tabiiy kenglik). Ya'ni ikki qatorga tushish xavfi past, lekin **brauzerda o'lchanmagan**.

➡ **Demak `02-23` uchun qoladigan HAQIQIY odam ishi — 1–5-bandlar.** 6- va 7-bandlar tasdiqlovchi ko'z bilan bir daqiqada yopiladi.

**Bu band `02-VALIDATION.md` ga BU REJADA ko'chirilmadi** — u fayl `02-23` ning zimmasida va bir faylni ikki reja tahrirlamaydi. `STATE.md` va `ROADMAP.md` ham bu rejada o'zgartirilmadi (orkestrator zimmasida).

## User Setup Required

Yo'q — tashqi servis sozlamasi talab qilinmaydi. `02-23` dagi foydalanuvchanlik kuzatuvi uchun lokal stek, bitta bozorsiz platforma admini hisobi va **dasturchi bo'lmagan kuzatiluvchi** kerak (yuqoriga qarang).

## Next Phase Readiness

**Yopildi (o'lchangan):**
- 02-VERIFICATION.md 1-bo'shlig'ining **kod qismi** to'liq: uchala artefakt ham `contains: "/markets/new"` talabini bajaradi, uchala `key_link` ham NOT_WIRED → **WIRED**.
- 02-REVIEW.md **WR-09** yopildi.
- `npm run gate` **yashil** (exit 0): 890 backend + tenant izolyatsiyasi + 112 frontend + typecheck + lint + build. Yashil darvoza regressiya QILMADI.

**Boshqa rejalarga o'tkazildi (ataylab, egasi bilan):**
- **Manual-Only #2 (foydalanuvchanlik kuzatuvi) → `02-23`.** U `02-VALIDATION.md` ni va to'rtala Manual-Only bandini birga yopadi hamda `nyquist_compliant` bayrog'ini qaytaradi. Qolgan odam ishi — yuqoridagi yo'riqnomaning 1–5-bandlari.
- **MARKET-01 katakchasini belgilash → `02-22`.** Bu rejada `requirements-completed: []` ATAYIN bo'sh: 02-VERIFICATION.md ning traceability qaroriga ko'ra oltala MARKET-ID ham CR-01/CR-02 yopilib, real Karmana ma'lumoti kelgunicha `Pending` qoladi. `02-22` faqat yopilishi HAQIQATAN yuz bergan IDlarni belgilaydi.

**Bu reja SC#1 ni YAKKA O'ZI yopa olmaydi** va bunga da'vo ham qilmaydi: SC#1 uchun (a) shu yerdagi kod qismi — bajarildi, (b) foydalanuvchanlik tasdig'i — `02-23`, (c) 02-VERIFICATION.md ning 2-bo'shlig'i (real Karmana ma'lumoti) — hamon ochiq va u bozor ma'muriyatining beshta hujjatiga bog'liq.

## Self-Check: PASSED

- 3 ta yangi fayl diskda mavjud (`layout.test.tsx`, `app-shell.test.tsx`, `wizard-reachability.test.mjs`).
- 5 ta tahrir qilingan manba fayli diskda mavjud.
- 3 ta commit hash `git log` da tasdiqlandi: `6468af4`, `30a6659`, `1cbca80`.
- **TEGILMAGAN fayllar** (egasi boshqa reja yoki orkestrator): `02-VALIDATION.md` (`02-23`), `REQUIREMENTS.md` (`02-22`), `STATE.md` va `ROADMAP.md` (orkestrator).
- `files_modified` ro'yxatidan tashqariga birorta fayl chiqmadi.
- Bu tahrir **hujjat aniqligi uchun**: birorta kod fayli o'zgarmadi va birorta o'lchov qayta yugurtirilmadi — yuqoridagi barcha raqamlar asl ijro paytida olingan.

---
*Phase: 02-bozor-domeni-va-yangi-bozor-ustasi*
*Completed: 2026-08-01*
