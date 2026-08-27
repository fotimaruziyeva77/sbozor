---
phase: 02-bozor-domeni-va-yangi-bozor-ustasi
plan: 02
subsystem: ui
tags: [tailwind4, radix-dialog, wcag, design-tokens, i18n, transliteration, react19]

# Dependency graph
requires:
  - phase: 01-poydevor-va-tenant-xavfsizligi
    provides: "@theme token bloki, ui/button + ui/card + ui/input, Radix Dialog naqshi, gen-cyrillic.mjs transliteratori, i18n darvozalari"
provides:
  - "WCAG AA ga keltirilgan @theme bloki — 6 o'lchangan buzilish yopildi, 5 yangi token"
  - "border-ui / border ajratmasi: boshqaruv elementi chegarasi vs dekorativ chegara"
  - "Yetti ui primitivi: dialog, field, select, badge, skeleton, empty-state, confirm-dialog"
  - "Dialog.Content sheetOnMobile — mobil pastki varaq, faqat CSS"
  - "ConfirmDialog ikki darajali (typeToConfirm + aria-disabled)"
  - "pointer:coarse qoidasi — iOS avtomatik kattalashtirish yo'q, pinch-zoom saqlangan"
  - "Transliteratsiya SIFATI darvozasi (i18n:check qamramaydigan sinf)"
  - "npm run gate endi frontend testlarini ham ishga tushiradi"
affects: [02-13, 02-14, 02-15, 02-16, 02-17, kassir-moduli, hisobotlar]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "ui/ primitivlarida foydalanuvchi matni YO'Q — matn next-intl orqali prop bo'lib keladi"
    - "Field id konvensiyasi: ${id}-error / ${id}-hint; aria-describedby ni chaqiruvchi ulaydi"
    - "Destruktiv tasdiqda aria-disabled, disabled EMAS (fokus oladi va e'lon qilinadi)"
    - "Grep darvozasi bilan qulflangan token izohda literal sifatida yozilmaydi"

key-files:
  created:
    - frontend/src/components/ui/dialog.tsx
    - frontend/src/components/ui/field.tsx
    - frontend/src/components/ui/select.tsx
    - frontend/src/components/ui/badge.tsx
    - frontend/src/components/ui/skeleton.tsx
    - frontend/src/components/ui/empty-state.tsx
    - frontend/src/components/ui/confirm-dialog.tsx
    - frontend/messages/README.md
  modified:
    - frontend/src/app/globals.css
    - frontend/src/components/users/user-list.tsx
    - frontend/src/components/users/create-user-dialog.tsx
    - frontend/src/components/audit/audit-filters.tsx
    - frontend/messages/uz-Cyrl.overrides.json
    - frontend/scripts/gen-cyrillic.test.mjs
    - package.json

key-decisions:
  - "Badge `warning` tone `bg-warning/20 text-text` (15.64:1) — `--color-warning` matn sifatida hech qachon ishlatilmaydi (oq fonda 2.03:1)"
  - "Badge ga `accent` tone qo'shildi — UI-SPEC C-06 (audit manba badge) uchun beshta e'lon qilingan tone ichida uy yo'q edi"
  - "ConfirmDialog ga `confirmVariant` qo'shildi — tiklovchi amal (unblock) qizil bo'lmasligi uchun; standart hamon destructive"
  - "Dialog.Footer `flex-col gap-2 sm:flex-row-reverse` — UI-SPEC §10.6 kontrakti, mobil to'liq kenglikdagi tugmalar saqlanadi"
  - "login-form va change-password-form ham Field ga ko'chirildi — inline nusxa qolmasligi uchun"
  - "Transliteratsiya darvozasi HAQIQIY overrides faylini o'qiydi, sintetik lug'atni emas"

patterns-established:
  - "Ikki chegara tokeni: --color-border (dekorativ, 1.28:1) vs --color-border-ui (boshqaruv, 3.64:1)"
  - "Uch xil semantik rol: --color-X (fon), --color-X-fg (fon ustidagi matn), --color-X-text (tint ustidagi matn)"
  - "Bo'sh holat ikki turga ajraladi; EmptyState farqni bilmaydi — chaqiruvchi title/description/action bilan hal qiladi"
  - "Agglyutinativ o'zbekcha: har qo'shimchali shakl alohida override yozuvi talab qiladi"

requirements-completed: [MARKET-01, MARKET-02, MARKET-06]

# Metrics
duration: 42min
completed: 2026-07-31
---

# Phase 2 Plan 02: Dizayn tizimi tuzatishi Summary

**Oltita o'lchangan WCAG AA buzilishi yopildi (qiymatlar kompilyatsiya qilingan CSS'dan qayta o'lchandi), yetti `ui/` primitivi inline nusxalardan ajratildi va transliteratorning to'rtta jimgina defekti test bilan qulflandi — 2-fazaning to'qqizta ekrani yozilishidan oldin.**

## Performance

- **Duration:** ~42 min
- **Started:** 2026-07-31T15:12Z
- **Completed:** 2026-07-31T15:54Z
- **Tasks:** 3/3
- **Files modified:** 33 (8 yaratildi), +1225 / −406

## Accomplishments

- **Oltita kontrast buzilishi yopildi va MUSTAQIL O'LCHANDI.** Spec'ning raqamlariga ishonilmadi — tokenlar kompilyatsiya qilingan CSS'dan (`#0072de`, `#868686`, `#b7191c`, …) o'qib olinib, sRGB nisbiy yorqinlik orqali qayta hisoblandi va alfa-kompozitsiya (`bg-danger/12` va h.k.) modellashtirildi. Barcha o'n ikki tekshiruv o'tdi; natijalar spec bilan yaxlitlash farqida mos keldi.
- **Yetti primitiv bitta manbaga keldi.** `Dialog.Overlay`/`Dialog.Portal` endi butun kodbazada **umuman yo'q** — xom Radix faqat `ui/dialog.tsx` ichida. Fokus tuzog'i, Esc va `aria-describedby` bir joyda.
- **Mexanik tozalash o'lchov bilan tasdiqlandi:** `font-medium` 22→0, `text-base` 4→0, panjaradan tushgan bo'shliq 21→0, `text-xl` faqat `font-mono` bilan (hujjatlashtirilgan istisno).
- **Transliterator darvozasi haqiqiy ekanligi isbotlandi.** To'rtta defekt avval kodda qayta ishlab chiqarildi, keyin yopildi, keyin overrides olib tashlanib darvoza **qizarishi** tasdiqlandi (44 pass / 4 fail).
- **`npm run gate` endi frontend testlarini ishga tushiradi** — ilgari `stall-map.test.tsx` faza darvozasidan tashqarida qolardi.

## Task Commits

1. **Task 1: Dizayn tokenlarini WCAG AA ga keltirish** — `debbebb` (fix)
2. **Task 2: Yetti `ui/` primitivini ajratish + panjarani tozalash** — `a2eb694` (refactor)
3. **Task 3: Transliterator defektlari + faza darvozasi** — `8f77a4b` (test)
4. **Darvoza gigiyenasi (Task 1–2 ustidan tuzatish)** — `79d9e83` (docs)

## Files Created/Modified

**Yaratildi**
- `frontend/src/components/ui/dialog.tsx` — Radix qobig'i; `Content` Portal+Overlay+Title+Description ni o'z ichiga oladi; `sheetOnMobile` mobil pastki varaq (faqat CSS); `size` sm/md/lg
- `frontend/src/components/ui/field.tsx` — yorliq + boshqaruv + xato + izoh; `${id}-error` / `${id}-hint` konvensiyasi
- `frontend/src/components/ui/select.tsx` — native `<select>` (Radix Select ATAYIN emas — telefonda tizim tanlagichi)
- `frontend/src/components/ui/badge.tsx` — olti tone, hammasi o'lchangan kontrast bilan
- `frontend/src/components/ui/skeleton.tsx` — `motion-reduce:animate-none`, `aria-hidden`
- `frontend/src/components/ui/empty-state.tsx` — sarlavha + tavsif + ixtiyoriy amal
- `frontend/src/components/ui/confirm-dialog.tsx` — ikki daraja, `typeToConfirm`, `aria-disabled`
- `frontend/messages/README.md` — to'rtta copy qoidasi (Excel/apostrof, agglyutinatsiya, DB kontenti, ICU)

**Muhim o'zgarishlar**
- `frontend/src/app/globals.css` — 2 token tuzatildi, 5 qo'shildi, `pointer:coarse` qoidasi, ikki chegara rolining qat'iylashtirilishi
- `frontend/src/components/users/user-list.tsx` — lokal `ConfirmDialog` va `Badge` o'chirildi (−88 qator)
- `frontend/src/components/audit/audit-filters.tsx` — lokal `Field` va `Select` o'chirildi
- `frontend/scripts/gen-cyrillic.test.mjs` — 10 yangi test (T-01…T-04, ICU nazorati, copy qoidasi, yetkazilayotgan fayl skaneri)
- `package.json` — `gate` ga `npm --prefix frontend test`; `fe:test` yorlig'i

## Decisions Made

- **`--color-warning` matn sifatida qat'iy taqiqlangan** (oq fonda o'lchangan 2.03:1). `--color-warning-text` kontrakt sifatida e'lon qilindi, lekin `src/` da ishlatilmaydi — Tailwind uni tree-shake qiladi, bu kutilgan holat.
- **`text-accent` mobil navigatsiyada saqlandi** — token tuzatilgandan keyin oq fonda 4.71:1, ya'ni AA dan o'tadi va UI-SPEC §4.3 uni aniq ruxsat etadi.
- **Tugmalar `border-border` da qoldi.** UI-SPEC migratsiyasi forma boshqaruv elementlarini sanaydi; tugmaning affordansi to'ldirish/shakl/yorliqdan keladi, faqat chegaradan emas. Bu barcha tugmalarni izchil qoldiradi.
- **Ro'yxatlarning yuklanish holati matnli `role="status"` bo'lib qoldi** (§9.1 skeletonni tavsiya qiladi) — reja `Skeleton` ni faqat `(app)/layout.tsx` ga tayinlagan va "xulq o'zgarmasligi shart" degan. Ekran rejalariga qoldirildi.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] CSS izohidagi `*/` ketma-ketligi `@theme` blokini erta yopdi**
- **Found during:** Task 1
- **Issue:** Yozgan izohimda `` `bg-*/12` `` naqshi bor edi; undagi `*/` blok izohini yopdi, qolgan matn CSS sifatida talqin qilindi va apostroflar satr chegarasiga aylandi. `next build` yiqildi: `CssSyntaxError: Unclosed string (122:7)`.
- **Fix:** PostCSS bilan aniq lokalizatsiya qilindi, izoh `bg-danger/12` kabi aniq misollarga qayta yozildi va tuzoq izohda ogohlantirish sifatida qoldirildi.
- **Files modified:** `frontend/src/app/globals.css`
- **Verification:** `postcss.parse` → OK; `next build` → exit 0
- **Committed in:** `debbebb`

**2. [Rule 2 - Missing Critical] Reja sanamagan fayllardagi kontrast buzilishlari**
- **Found during:** Task 1
- **Issue:** Reja `text-danger` migratsiyasi uchun 5 fayl sanagan, lekin uning O'Z qabul mezoni `frontend/src/components` bo'ylab nol talab qiladi. `change-password-form`, `login-form`, `audit-diff`, `audit/page` qamralmagan edi. Bundan tashqari `audit-diff` oq fonda `text-success` ishlatardi — bu o'lchov bo'yicha AA dan o'tmaydi.
- **Fix:** Migratsiya butun `frontend/src` ga yoyildi; `audit-diff` `text-success-text` (6.09:1) va `text-danger-text` (6.63:1) ga o'tdi.
- **Verification:** `text-danger"` → 0; ratio hisoblagichi PASS
- **Committed in:** `debbebb`

**3. [Rule 2 - Missing Critical] `ConfirmDialog` kontrakti matn yorliqlarisiz to'liq emas edi**
- **Found during:** Task 2
- **Issue:** E'lon qilingan interfeys `cancelLabel` ni o'z ichiga olmagan, lekin primitivlarda matn bo'lishi taqiqlangan — bekor qilish tugmasini render qilishning yo'li yo'q edi. 2-darajadagi matn maydonining ham yorlig'i yo'q edi (a11y).
- **Fix:** `cancelLabel`, `typeToConfirmLabel` (2-darajada TS orqali majburiy), `isBusy`, `children` qo'shildi. Diskriminatsiyalangan birlashma 2-daraja proplarini kompilyatsiya vaqtida majburlaydi.
- **Files modified:** `frontend/src/components/ui/confirm-dialog.tsx`
- **Verification:** `tsc --noEmit` exit 0
- **Committed in:** `a2eb694`

**4. [Rule 2 - Missing Critical] `Badge` ga `accent` tone**
- **Found during:** Task 2
- **Issue:** UI-SPEC C-06 buzilishi aynan "audit manba badge" deb nomlangan (`bg-accent/10`), lekin e'lon qilingan beshta tone ichida unga mos keladigani yo'q edi.
- **Fix:** Birlashmaga `accent` qo'shildi (`bg-accent/10 text-accent-text`, o'lchangan 5.29:1). Qo'shimcha a'zo mavjud chaqiruvchilarni buzmaydi.
- **Committed in:** `a2eb694`

**5. [Rule 2 - Missing Critical] `confirmVariant` — refaktoring redizaynga aylanmasligi uchun**
- **Found during:** Task 2
- **Issue:** Reja `ConfirmDialog` ni har doim `destructive` deb belgilaydi, lekin AYNI vazifada "xulq o'zgarmasligi shart" ham deydi. `user-list` da `unblock` — TIKLOVCHI amal va hozir `default` variant. Uni qizil qilish yolg'on xavf signali berardi.
- **Fix:** Ixtiyoriy `confirmVariant` propi, standart qiymati `destructive` (rejaning talabi saqlanadi).
- **Committed in:** `a2eb694`

**6. [Rule 2] `login-form` va `change-password-form` ham `Field` ga ko'chirildi**
- **Found during:** Task 2
- **Issue:** Reja bu ikki faylni chaqiruvchilar ro'yxatiga kiritmagan, lekin ularda aynan o'sha inline maydon razmetkasi bor va ular panjara mezonini (`*-1.5` → 0) buzardi.
- **Fix:** Ikkalasi `Field` ga ko'chdi; `change-password-form` ga yetishmayotgan `aria-describedby` ulanishi qo'shildi.
- **Committed in:** `a2eb694`

**7. [Rule 1 - Bug] Hujjatlashtirilgan taqiqlar o'z grep darvozalarini qizartirdi**
- **Found during:** Yakuniy tekshiruv (Task 1–2 ustidan)
- **Issue:** Izohlarda RAD ETILGAN yondashuv nomma-nom keltirilgani uchun uch mezon yiqildi: `maximum-scale` (`globals.css`), `text-warning` (`ui/badge.tsx`), `Excel'` (`uz-Cyrl.overrides.json`).
- **Fix:** Kodbazaning mavjud konvensiyasi qo'llanildi (`locale-switcher.tsx`, `audit-diff.tsx`, `login-form.tsx` da allaqachon bor): taqiqlangan nom literal sifatida yozilmaydi, sabab to'liq qoladi.
- **Verification:** Uchala grep → 0; build/test/lint exit 0
- **Committed in:** `8f77a4b` (Excel), `79d9e83` (qolgan ikkitasi)

**8. [Rule 2] Ikkita yangi i18n kaliti**
- **Found during:** Task 2
- **Issue:** `EmptyState` majburiy `description` talab qiladi (§9.2 kontrakti), mavjud kalitlar esa faqat sarlavha bergan.
- **Fix:** `users.emptyStateHint` va `audit.emptyStateHint` uz-Latn + ru ga qo'shildi, uz-Cyrl qayta hosil qilindi.
- **Verification:** `i18n:check` — 122 kalit × 3 til, parity to'liq
- **Committed in:** `a2eb694`

---

**Total deviations:** 8 auto-fixed (2 bug, 6 missing-critical). Rule 4 (arxitektura) holati bo'lmadi.
**Impact on plan:** Hech biri qamrov kengaytmasi emas — 2, 3, 4, 6 va 8 rejaning O'Z qabul mezonlari yoki must-have'lari tomonidan talab qilinadi; 1 va 7 mening o'zim kiritgan defektlarim; 5 rejaning ichki ziddiyatini ikkala talabni ham saqlab hal qiladi.

## Issues Encountered

- **Worktree'da `node_modules` yo'q edi.** Commit qilingan `package-lock.json` dan `npm ci` bilan tiklandi (yangi paket o'rnatilmadi — cheklov buzilmadi).
- **`grep -rn "border-border\b"` mezoni `border-border-ui` ni ham tutadi** (`-` regex'da so'z chegarasi). Mezonning niyati bo'yicha tekshirildi: `input.tsx` da yalang'och `border-border` yo'q, faqat `border-border-ui`.
- **`--color-warning-text` kompilyatsiya qilingan CSS'da yo'q** — Tailwind 4 ishlatilmagan tema o'zgaruvchisini tree-shake qiladi. Bu kutilgan: token kontrakt sifatida manbada e'lon qilingan, mezon ham aynan `globals.css` ni tekshiradi.

## Verification Evidence

| Tekshiruv | Natija |
|-----------|--------|
| `npm --prefix frontend run build` | exit 0 |
| `npm --prefix frontend run typecheck` | exit 0 |
| `npm --prefix frontend run lint` | exit 0 |
| `npm --prefix frontend test` | 48 node-test + 3 vitest, 0 fail |
| `npm --prefix frontend run i18n:check` | 122 kalit × 3 til, drift yo'q |
| Qabul mezonlari (avtomatlashtirilgan skript) | 28/28 PASS |
| Kontrast (kompilyatsiya qilingan CSS'dan qayta o'lchandi) | 12/12 PASS |
| Darvoza qizarish sinovi (overrides olib tashlandi) | 4 test yiqildi — darvoza haqiqiy |

O'lchangan kontrast nisbatlari (kompilyatsiya qilingan qiymatlardan):

| # | Tekshiruv | Edi | Bo'ldi | Talab |
|---|-----------|-----|--------|-------|
| C-01 | oq matn `accent` fonida | 4.36 | **4.71** | 4.5 |
| C-02 | `text-muted` / `surface-muted` | 4.31 | **4.77** | 4.5 |
| C-03 | `border-ui` / surface · bg · surface-muted | 1.28 | **3.64 · 3.49 · 3.31** | 3.0 |
| C-04 | `danger-text` / `bg-danger/12` | 3.97 | **5.54** | 4.5 |
| C-05 | `success-text` / `bg-success/12` | 2.87 | **5.35** | 4.5 |
| C-06 | `accent-text` / `bg-accent/10` | 3.82 | **5.29** | 4.5 |

## Known Stubs

Yo'q. Bu reja mavjud ekranlarni refaktoring qiladi — yangi ma'lumot yo'llari yaratmaydi, shuning uchun ulanmagan komponent yoki o'rniga qo'yilgan qiymat yo'q. `--color-warning-text` ishlatilmaydi, lekin bu stub emas: u §4.2 kontraktining bir qismi sifatida ataylab e'lon qilingan.

## Threat Flags

Yo'q — yangi tarmoq nuqtasi, auth yo'li, fayl kirishi yoki sxema o'zgarishi kiritilmadi. Reja `<threat_model>` idagi `mitigate` dispozitsiyalari bajarildi:

| Threat ID | Holat |
|-----------|-------|
| T-02-09 | `--color-danger-text` 5.54:1 + `aria-invalid` + matn — rang yagona signal emas |
| T-02-10 | `ConfirmDialog` 2-darajasi `typeToConfirm` talab qiladi; tugma `aria-disabled` (fokus oladi) |
| T-02-11 | Faqat matn tugunlari; HTML sifatida talqin qiluvchi xossa kiritilmadi |
| T-02-12 | `@media (pointer: coarse)` 16px; kattalashtirishni cheklovchi meta RAD ETILDI |
| T-02-13 | `components.json` yaratilmadi, registr ishlatilmadi, `package.json` ga yangi paket qo'shilmadi |
| T-02-14 | `gen-cyrillic.test.mjs` T-01…T-04 + yetkazilayotgan fayl skaneri; darvoza qizarishi tasdiqlandi |

## Deferred Items

- **Ro'yxatlarning yuklanish holati `Skeleton` ga ko'chmadi** (`user-list`, `audit-list`). UI-SPEC §9.1 ro'yxatlar uchun skeletonni belgilaydi; reja `Skeleton` ni faqat `(app)/layout.tsx` ga tayinlagan va xulqni saqlashni talab qilgan. Ekran rejalari (02-13+) buni o'z ekranlarida qo'llasin.
- **`audit-list` bitta bo'sh holat ishlatadi.** §9.2 "hech narsa yo'q" va "filtr topmadi" ni ajratishni talab qiladi; `useAuditFilters().isEmpty` allaqachon mavjud, lekin §10.4 dagi 9 ta kalit 02-13+ ga tegishli.
- **`npm run gate` ning backend qismi worktree'da ishlamaydi** — `.env` gitignore qilingan, compose sirlar bo'lmasa ishga tushmaydi. Frontend qismi to'liq zanjir sifatida ishga tushirilib exit 0 berdi; backend qismi bu reja tegmagan fayllarga tegishli va asosiy checkout'da ishga tushirilishi kerak.

## User Setup Required

Yo'q — tashqi xizmat sozlamasi talab qilinmaydi.

## Next Phase Readiness

02-13…02-17 uchun tayyor:

- `@theme` bloki barqaror; yangi ekranlar `border-border-ui` va `*-text` tokenlarini ishlatishi kerak (dekorativ `border-border` faqat karta/panel uchun).
- Yetti primitiv `<interfaces>` da e'lon qilingan kontrakt bo'yicha ishlaydi; `Dialog.Content` ning `sheetOnMobile` propi rasta kartasi (§7.6) uchun tayyor.
- `ConfirmDialog` 2-darajasi D-1 (qoralama bozorni o'chirish) va D-2 (rastani yopish) uchun tayyor — ikkalasi ham `typeToConfirm` + `typeToConfirmLabel` beradi.
- ~120 yangi kalit yozilganda `frontend/messages/README.md` Qoida 1 va 2 ga bo'ysunish shart; `npm --prefix frontend test` endi buni darvoza sifatida tekshiradi.

**Ogohlantirish keyingi rejalarga:** UI-SPEC §12.1.1 dagi W0-12 (qoralama bozor ko'rinadigan bo'lishi, 6 bandli zanjir) va X-3 (WR-02/WR-03 — `select-market` avtorizatsiya chetlab o'tishi) bu rejaning qamrovida EMAS edi va hamon ochiq. §12.1.1 ularni "boshqa Wave 0 ishlaridan oldin" turishi kerak deb belgilaydi — usta oqimi shu endpointga tayanadi.

## Self-Check: PASSED

Yaratilgan sakkiz fayl diskda mavjud (`ls` bilan tasdiqlandi); to'rt commit hash `git rev-parse` bilan hal bo'ldi (`debbebb`, `a2eb694`, `8f77a4b`, `79d9e83`). Ishchi daraxt toza, kutilmagan o'chirish yo'q (`git diff --diff-filter=D` har commitdan keyin bo'sh).

---
*Phase: 02-bozor-domeni-va-yangi-bozor-ustasi*
*Completed: 2026-07-31*
