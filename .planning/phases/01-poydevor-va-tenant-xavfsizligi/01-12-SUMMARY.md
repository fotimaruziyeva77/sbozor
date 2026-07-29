---
phase: 01-poydevor-va-tenant-xavfsizligi
plan: 12
subsystem: ui
gap_closure: true
tags:
  [
    react,
    vitest,
    jsdom,
    testing-library,
    react-query,
    rbac,
    market-picker,
    component-test,
    CR-02,
    CR-03,
  ]

# Dependency graph
requires:
  - "01-08 (`market-picker.tsx`, `api-types.ts`, `auth-store.ts`, `api-client.ts` — tuzatilayotgan kod shu rejada yozilgan)"
  - "01-09 (`role-gate.test.mjs`, `create-user-dialog.tsx` — mustahkamlanayotgan test va uni iste'mol qiluvchi forma)"
provides:
  - "`frontend/vitest.config.ts` + `frontend/vitest.setup.ts` — jsdom komponent-test infratuzilmasi (fazadagi BIRINCHI)"
  - "`frontend/src/components/auth/market-picker.test.tsx` — fazadagi BIRINCHI React render/interaction testi"
  - "`PLATFORM_ADMIN_ASSIGNABLE_ROLES` — platforma admini bera oladigan to'rt rol (`platform_admin` siz)"
  - "`npm --prefix frontend test` endi node:test (38) VA vitest (3) ni ketma-ket bajaradi"
  - "`npm --prefix frontend run test:component` / `test:unit` — yugurtgichlarni alohida chaqirish"
affects:
  - "01-11 (backend CR-03 yarmi: `users.py::_assert_roles_assignable` — bu reja UI ko'zgusini o'sha darvozaga moslashtirdi)"
  - "Barcha keyingi frontend rejalari — komponent testi endi `src/**/*.test.tsx` naqshi bilan yoziladi, alohida infra qurish shart emas"
  - "08 (Playwright E2E — bu reja uni ATAYIN qurmadi, jsdom bilan proporsional yechim berildi)"

# Tech tracking
tech-stack:
  added:
    - "vitest 4.1.10 (MIT) — komponent-test yugurtgichi"
    - "@vitejs/plugin-react 6.0.4 (MIT) — JSX transformi"
    - "jsdom 30.0.1 (MIT) — DOM muhiti"
    - "@testing-library/react 16.3.2 (MIT) — React 19 render API"
    - "@testing-library/dom 10.4.1 (MIT) — so'rov (query) qatlami"
    - "@testing-library/jest-dom 7.0.0 (MIT) — `toBeDisabled()` va boshqa DOM matcher'lari"
  patterns:
    - "TanStack Query v5: `disabled` so'rovda `isPending` ABADIY true — tugma bloklash uchun DOIM `isLoading` ishlatiladi"
    - "Ikki test yugurtgichi ATAYIN yonma-yon: sof funksiyalar `node --test`, React komponentlari vitest+jsdom; `include` naqshlari kesishmaydi"
    - "Modul mock'lari `vi.hoisted` + `vi.mock`; holat har testda aniq `vi.resetAllMocks()` bilan tozalanadi (`restoreMocks` `vi.fn()` tarixini tozalamaydi)"
    - "Rol ro'yxatlari testda qattiq yozilgan qiymat emas, QOIDA sifatida qulflanadi (`enum minus platform_admin`)"

key-files:
  created:
    - frontend/vitest.config.ts
    - frontend/vitest.setup.ts
    - frontend/src/components/auth/market-picker.test.tsx
  modified:
    - frontend/src/components/auth/market-picker.tsx
    - frontend/src/lib/api-types.ts
    - frontend/scripts/role-gate.test.mjs
    - frontend/package.json
    - frontend/package-lock.json

decisions:
  - "`@testing-library/user-event` QO'SHILMADI — u tasdiqlangan olti paket ro'yxatiga kirmaydi; bosish `fireEvent` bilan qilinadi"
  - "`restoreMocks: true` konfiguratsiyadan OLIB TASHLANDI — u `vi.fn()` modul mock'larining chaqiruv tarixini tozalamaydi va testlararo sizishga sabab bo'lgan edi"
  - "`PLATFORM_ADMIN_ASSIGNABLE_ROLES` `Role` enum'iga bog'landi (enum minus `platform_admin`), qattiq yozilgan to'rtlik takrorlanmadi"
  - "`test` skripti `&&` bilan ketma-ket — node:test qizarsa vitest umuman ishga tushmaydi (tez fail)"

metrics:
  duration_min: 16
  tasks_completed: 3
  files_created: 3
  files_modified: 5
  tests_before: 37
  tests_after: 41
  completed: 2026-07-29
---

# Phase 01 Plan 12: Frontend gap-closure (CR-02 + CR-03) Summary

TanStack Query v5 ning `isPending` semantikasi tufayli ishlamay qolgan bozor
tanlash ekrani tuzatildi va fazadagi birinchi React render testi bilan
qulflandi; `platform_admin` foydalanuvchi yaratish formasidan olib tashlandi.

## Nima qilindi

### Task 1 — test-infra paketlari legitimligi (checkpoint, blocking-human)

Bu checkpoint SPAWN'dan OLDIN orkestrator tomonidan jonli npm registry va
downloads API'siga qarab bajarilgan (2026-07-29). Natija:

| Paket | Versiya | Litsenziya | Haftalik yuklab olish | Maintainerlar | Repo |
|---|---|---|---|---|---|
| vitest | 4.1.10 | MIT | 84 959 096 | ariperkkio, antfu | github.com/vitest-dev/vitest |
| @vitejs/plugin-react | 6.0.4 | MIT | 69 073 545 | yyx990803 (Evan You), vitebot | github.com/vitejs/vite-plugin-react |
| jsdom | 30.0.1 | MIT | 89 087 369 | domenic, timothygu | github.com/jsdom/jsdom |
| @testing-library/react | 16.3.2 | MIT | 50 776 271 | testing-library-bot, kentcdodds | github.com/testing-library/react-testing-library |
| @testing-library/dom | 10.4.1 | MIT | 58 105 823 | testing-library-bot, kentcdodds | github.com/testing-library/dom-testing-library |
| @testing-library/jest-dom | 7.0.0 | MIT | 57 354 917 | testing-library-bot, kentcdodds | github.com/testing-library/jest-dom |

Oltalasi ham kanonik, MIT, faol saqlanadigan paketlar; hech birida
[SLOP]/[SUS] signali yo'q. React 19 mosligi TASDIQLANDI —
`@testing-library/react@16.3.2` ning `peerDependencies` i
`react: '^18.0.0 || ^19.0.0'` ni o'z ichiga oladi (reja v16+ talab qilgan),
o'rnatilgan React esa 19.2.8. Barchasi `--save-exact` bilan qadaldi va
`devDependencies` ga tushdi (`dependencies` ga EMAS).

Versiya fallback'i (vitest 3.x) KERAK BO'LMADI — vitest 4.1.10 +
@vitejs/plugin-react 6.0.4 Next 16 / React 19.2.8 muhitida birinchi
urinishdayoq ishladi.

### Task 2 — CR-02: bozor tanlash tugmalari (D-06)

`market-picker.tsx` da `isBusy` endi `marketsQuery.isLoading` ni o'qiydi:

```ts
const isBusy = selectMarket.isPending || marketsQuery.isLoading;

if (marketsQuery.isLoading) {
```

Xatoning ildizi: `marketsQuery` asosiy yo'lda O'CHIQ
(`enabled: accessToken !== null && markets.length === 0`, login javobi
`markets` ni to'ldirgani uchun shart `false`). TanStack Query v5 da
`isPending` "keshda ma'lumot yo'q" degani, "so'rov ketyapti" degani emas —
o'chirilgan so'rovga hech qachon javob kelmagani uchun u ABADIY `true`
bo'lib qoladi. Natijada 95-qatordagi skelet return'i o'tib ketardi
(`markets.length === 0` yolg'on), ro'yxat esa `isBusy === true` bilan
render bo'lardi va HAR BIR bozor tugmasi `disabled` chiqardi. `isLoading`
= `isPending && isFetching`, ya'ni o'chirilgan so'rovda `false`.

Skelet sharti ham `markets.length === 0` qo'shimchasidan xalos bo'ldi —
`isLoading` allaqachon aynan "hozir yuklanyaptimi" degan savolga javob
beradi.

Yangi test (`market-picker.test.tsx`, 3 ta holat):
1. `markets` to'la bo'lganda ikkala tugma ham `not.toBeDisabled()` —
   CR-02 ning to'g'ridan-to'g'ri regressiya qulfi; ayni paytda
   `GET /markets` UMUMAN chaqirilmasligi ham tasdiqlanadi.
2. Tugma bosilganda `POST /auth/select-market` aynan tanlangan
   `market_id` bilan ketadi va muvaffaqiyatdan keyin `/dashboard` ga
   o'tiladi.
3. So'rov ketayotganda tugmalar bloklanadi — bu tuzatish `disabled`
   mantiqini shunchaki O'CHIRIB tashlamaganini isbotlaydi.

### Task 3 — CR-03 frontend yarmi: `platform_admin` (D-04)

`api-types.ts` ga `PLATFORM_ADMIN_ASSIGNABLE_ROLES`
(`director`, `market_admin`, `cashier`, `inspector`) qo'shildi va
`assignableRoles()` endi `ROLES` (beshta) o'rniga shu to'rtlikni
qaytaradi. Ishlatilmay qolgan `ROLES` importi olib tashlandi.

`create-user-dialog.tsx` O'ZGARTIRILMADI va kerak ham emas edi: u
katakchalarni to'g'ridan-to'g'ri `assignableRoles()` natijasidan quradi
(qattiq yozilgan rol nomlari yo'q), shuning uchun ro'yxatdan chiqarish
katakchani avtomatik yo'qotadi.

`role-gate.test.mjs` ikki joyda o'zgardi:
- 2-testning sarlavhasidagi "(platforma admini beshalasini ko'radi)"
  ma'nosi olib tashlandi. VERIFICATION aynan shuni "zaiflikni to'g'ri deb
  qulflagan" deb belgilagan edi. Test endi faqat haqiqiy da'voni
  tekshiradi: `rbac.ts::ROLES` — bu YORLIQ ro'yxati va u
  `sbozor_core.enums.Role` bilan mos.
- Yangi 3-test: `platform_admin` IKKALA assignable ro'yxatda ham yo'q va
  platforma ro'yxati `Role` enum'i minus `platform_admin` ga teng.
  Oxirgi assert testni zaiflashtirmaydi — backend'ga yangi rol qo'shilsa
  u qizaradi, ya'ni qoida qulflanadi, qattiq yozilgan to'rtlik emas.

1-test (frontend/backend `MARKET_ADMIN_ASSIGNABLE_ROLES` bog'lanishi)
ATAYIN o'zgarmadi — u haqiqiy kontrakt qulfi va saqlanishi shart edi.

## Sabotaj tekshiruvlari

Ikkala test ham HAQIQATAN xatoni ushlashi qo'lda isbotlandi:

| Sabotaj | Natija |
|---|---|
| `market-picker.tsx`: `isLoading` -> `isPending` | UCHALA komponent testi ham QIZARDI. 1-test: tugmalar `disabled`. 2 va 3-testlar: tugma bloklangani uchun bosish umuman ishlamaydi, `apiFetch` "called 0 times". |
| `api-types.ts`: `PLATFORM_ADMIN_ASSIGNABLE_ROLES` ga `platform_admin` qo'shish | FAQAT yangi 3-test qizardi (`tests 3 / pass 2 / fail 1`), qolgan ikkitasi yashil qoldi — ya'ni nishon aniq. |

Ikkala holatda ham sabotaj bekor qilinib, yakuniy holat qayta tekshirildi.

## Darvozalar (yakuniy holat)

```
npm --prefix frontend run i18n:gen      -> uz-Cyrl.json qayta hosil qilindi
npm --prefix frontend run i18n:check    -> drift yo'q; 120 kalit × 3 til, ICU parity to'liq
npm --prefix frontend run typecheck     -> exit 0
npm --prefix frontend run lint          -> exit 0
npm --prefix frontend test              -> node:test 38/38 + vitest 3/3
npm --prefix frontend run build         -> Compiled successfully; 24/24 SSG sahifa
```

Test soni: 37 -> 41 (node:test 37 -> 38 CR-03 testi bilan; vitest 0 -> 3).
Mavjud 37 testning hech biri o'zgartirilmadi yoki o'chirilmadi.

CI o'zgartirishi SHART EMAS: `.github/workflows/ci-frontend.yml` allaqachon
`npm --prefix frontend test` ni chaqiradi, ya'ni yangi vitest to'plami
avtomatik CI'ga ulandi.

## Rejadan chetlanishlar

### 1. [Rule 3 - Blocking] `restoreMocks: true` testlararo sizish berdi

- **Qachon:** Task 2, komponent testini birinchi ishga tushirishda.
- **Muammo:** Rejada mock tozalash usuli ko'rsatilmagan edi. `restoreMocks`
  vitest 4 da `vi.spyOn` josuslarini tiklaydi, lekin `vi.fn()` bilan
  qurilgan modul mock'larining chaqiruv TARIXINI tozalamaydi. Natijada
  2-testdagi bitta `apiFetch` chaqiruvi 3-testning sanog'iga qo'shilib
  ketdi ("expected 1 times, but got 2 times").
- **Yechim:** `restoreMocks` konfiguratsiyadan olib tashlandi (sababi izohda
  yozildi) va test faylida aniq `vi.resetAllMocks()` `beforeEach` ga
  qo'yildi — u ham tarixni, ham implementatsiyani tozalaydi.
- **Fayllar:** `frontend/vitest.config.ts`, `frontend/src/components/auth/market-picker.test.tsx`
- **Commit:** b7b4e6a

### 2. [Rejadan og'ish - paket] `@testing-library/user-event` ishlatilmadi

- **Qachon:** Task 2, testni yozishda.
- **Muammo:** Bosishni modellashtirishning odatiy yo'li `user-event`, lekin
  u Task 1 da tasdiqlangan OLTI paket ro'yxatiga kirmaydi. Tasdiqdan
  o'tmagan paketni jimgina qo'shish paket-legitimlik darvozasini
  chetlab o'tish bo'lardi.
- **Yechim:** `fireEvent` (`@testing-library/react` tarkibida, tasdiqlangan)
  ishlatildi — bu test uchun to'liq yetarli. Sabab test faylining
  sarlavha izohida qayd etilgan.
- **Commit:** b7b4e6a

### 3. [Rule 3 - Blocking] `ROLES` importi ishlatilmay qoldi

- **Qachon:** Task 3.
- **Muammo:** `assignableRoles()` `ROLES` dan foydalanishni to'xtatgach,
  `api-types.ts:3` dagi import ishlatilmay qoldi va lint/typecheck
  darvozasini buzardi.
- **Yechim:** Import `import type { Role } from "@/lib/rbac";` ga
  qisqartirildi.
- **Commit:** 01eb2a7

## Kechiktirilgan masalalar (bu rejadan TASHQARI)

- **`npm audit`: 12 ta high-severity zaiflik.** Tekshirildi — hammasi
  MAVJUD bog'liqliklardan keladi, yangi olti paketdan EMAS: `eslint` /
  `eslint-config-next` (`minimatch` -> `brace-expansion` DoS) va `next`
  (`postcss` XSS, `sharp` -> libvips CVE-2026-333xx). Ular bu rejaning
  doirasidan tashqarida (SCOPE BOUNDARY) va tuzatilmadi.
- **`jsdom@30.0.1` engine ogohlantirishi.** `EBADENGINE`: jsdom
  `node ^22.22.2 || ^24.15.0 || >=26.0.0` so'raydi, mahalliy host esa
  v24.14.1. Ogohlantirish maslahat xarakterida — jsdom amalda ishlashi
  tekshirildi (import + DOM so'rovi) va 3 test yashil. CI `node-version: 24`
  ishlatadi, ya'ni u eng so'nggi 24.x ni oladi va talabni qondiradi.
  Mahalliy Node'ni 24.15+ ga ko'tarish tavsiya etiladi.

## Nima ishlanmadi (ATAYIN)

- **Playwright E2E qurilmadi** — OQ-2 bo'yicha 8-fazaga qoldirilgan.
  Bu reja jsdom + Testing Library bilan proporsional yechim berdi.
- **Backend CR-03 yarmi tegilmadi** — `services/core-api/app/api/v1/users.py`
  dagi `_assert_roles_assignable()` va `markets.py` dagi
  `MARKET_VIEW_ALL` -> `is_platform_admin` tuzatishi 01-11 rejasining
  (parallel agent) zimmasida. Bu reja faqat UI ko'zgusini moslashtirdi.
  HAQIQIY xavfsizlik chegarasi baribir serverda qoladi.
- **`create-user-dialog.tsx` o'zgartirilmadi** — kerak emas edi (yuqoriga
  qarang).

## Threat Flags

Yangi xavfsizlik yuzasi qo'shilmadi. `<threat_model>` dagi uchala yozuv
ham `mitigate` holatida yopildi:

| Threat ID | Holat |
|---|---|
| T-01-SC (npm test-infra tampering) | Yopildi — install'dan oldin blocking-human tasdiq, oltala paket MIT/kanonik, `--save-exact` bilan qadaldi |
| T-01-83 (assignableRoles EoP ko'zgusi) | Yopildi — `platform_admin` chiqarildi, `role-gate.test.mjs` qulfladi; haqiqiy darvoza 01-11 da |
| T-01-84 (market-picker DoS/usability) | Yopildi — `isLoading` semantikasi, render testi enabled holatni tasdiqlaydi |

## Commitlar

| Task | Commit | Tavsif |
|---|---|---|
| 2 | `b7b4e6a` | `fix(01-12): market-picker isPending -> isLoading + component test infra (CR-02)` |
| 3 | `01eb2a7` | `fix(01-12): platform_admin ni beriladigan rollardan chiqarish (CR-03, D-04)` |

## Known Stubs

Yo'q. Bu reja mavjud, ishlaydigan kodga jarrohlik tuzatish kiritdi va
hech qanday placeholder/stub qoldirmadi.

## Self-Check: PASSED

Fayllar (7/7 topildi):
`frontend/vitest.config.ts`, `frontend/vitest.setup.ts`,
`frontend/src/components/auth/market-picker.test.tsx`,
`frontend/src/components/auth/market-picker.tsx`,
`frontend/src/lib/api-types.ts`, `frontend/scripts/role-gate.test.mjs`,
`.planning/phases/01-poydevor-va-tenant-xavfsizligi/01-12-SUMMARY.md`

Commitlar (2/2 topildi): `b7b4e6a`, `01eb2a7`

Doira: `frontend/` va shu SUMMARY dan tashqari HECH QANDAY fayl
o'zgartirilmadi. `STATE.md` va `ROADMAP.md` ga TEGILMADI (worktree rejimi —
ular orkestrator zimmasida).
