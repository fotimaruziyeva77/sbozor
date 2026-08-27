---
phase: 09-ui-polish-motion-qatlami
plan: 04
subsystem: ui
tags: [flip, reduced-motion, choreography, jsdom, ast, vitest]
requires:
  - "09-01: @keyframes reyestri (draw/ringpulse/landin) + .motion-* sinflari + --motion-slow/--ease-out tokenlari"
  - "09-02: motion-tokens darvozasi (duration-<raqam> / transition-[ / inline animation: taqiqi)"
  - "M-9: collect-session.tsx onWritten 6-qadami (bugungi tartib — TEGILMADI)"
provides:
  - "lib/motion.ts — prefersReducedMotion() bir martalik guard (standart false: API yo'q = cheklov yo'q)"
  - "collect/success-choreography.tsx — imperativ FLIP flyAmountToList (React'siz, useState'siz, JSX'siz)"
  - "onWritten ulanishi: focus() -> toast -> try { flyAmountToList } catch — await'siz"
  - "2/3/5-qadam iste'molchilari: .motion-check-draw (payment-bar) / .motion-ring-pulse (pending-card) / .motion-row-land (payment-row)"
  - "PendingCard.amountRef — ixtiyoriy Ref<HTMLParagraphElement>, 4-qadam FLIP manbai ilgagi"
  - "pending-card: text-display (Display-XL, L-9) + skeleton h-11 (G-motion-7(c) juftligi)"
  - "G-motion-1(c) ikkala shoxi + G-motion-2(a,b,c,d,e) beshala qismi jonli testlarda"
affects:
  - "09-07 (faza darvozasi: to'liq gate + byudjet qayta o'lchovi)"
  - "kelajak konfetti rejasi (market_day_cleared) — ulanish nuqtasi onWritten oxirida tayyor"
tech-stack:
  added: []
  patterns:
    - "Imperativ DOM bezagi React daraxtidan TASHQARIDA — unmount'dan omon qoladi, holatga tegmaydi, testda document.body'da sanaladi"
    - "AST darvoza (typescript.createSourceFile) — setTimeout callback ichida set[A-Z] chaqiruvi 0, sun'iy-ijobiy nazorat bilan"
    - "Nazoratli modul-o'rami mock: standartda ASL funksiya ishlaydi, impl bilan istisno modellashtiriladi, activeAtCall bilan tartib o'lchanadi"
key-files:
  created:
    - frontend/src/lib/motion.ts
    - frontend/src/components/collect/success-choreography.tsx
    - frontend/src/components/collect/success-choreography.test.tsx
  modified:
    - frontend/src/components/collect/payment-bar.tsx
    - frontend/src/components/collect/pending-card.tsx
    - frontend/src/components/collect/payment-row.tsx
    - frontend/src/components/collect/collect-session.tsx
    - frontend/src/components/collect/collect-session.test.tsx
decisions:
  - "motion.ts standarti stall-map'ga ATAYLAB teskari: fail-open emas, false — mavjud bo'lmagan media-API foydalanuvchi afzalligi emas"
  - "Halqa «muvaffaqiyat lahzasi» = matched proyeksiya mounti — to'lov lahzasida karta M-9 tufayli ayni flush'da unmount bo'ladi (kontrakt yutdi, quyida)"
  - "S1 sabotaj «await bayram» ning JONLI shakli bilan modellashtirildi (700ms kutish) — literal await sync funksiyada mikrotask-no-op bo'lib, darvozani o'lchamasdi"
  - "(b) o'lchovi fireEvent + activeElement tasdig'i bilan — user-event lockfile'da yo'q, yangi paket TAQIQ (G-motion-3(d))"
metrics:
  duration: "~35 min"
  completed: "2026-08-17"
  tasks: 3
  commits: 5
  tests_added: 16
requirements: [SC-1, SC-4, CASH-01]
---

# Phase 9 Plan 04: Y-1 kassir to'lov xoreografiyasi (1–5-qadam) Summary

**Kassir vau-oqimining 1–5-qadami bloklamaydigan MEXANIKA bilan ulandi: imperativ FLIP klon (React daraxtidan tashqarida, inline uslub bilan o'lchanadigan), check-draw/halqa/qator-qo'nish iste'molchilari va `onWritten` da `focus()`dan KEYIN, `await`siz, `try/catch` ichidagi chaqiruv — G-motion-2 beshala qismi va G-motion-1(c) ikkala shoxi uch REAL sabotaj isboti bilan jonli.**

## Bajarilgan vazifalar

| # | Vazifa | Commit |
|---|--------|--------|
| 1 (RED) | `success-choreography.test.tsx` — G-motion-1(c) ikkala shox, G-motion-2(c) inline uslub, G-motion-2(d) AST + sun'iy-ijobiy nazorat, G-motion-2(e) istisno modeli; modul yo'qligida 1 failed | `c6df23f` |
| 1 (GREEN) | `lib/motion.ts` (guard, standart false) + `success-choreography.tsx` (imperativ FLIP, RESEARCH «Kod namunalari 3» dan); 12/12 · sabotaj o'lchandi | `26cbfeb` |
| 2 | `payment-bar` check-draw (`pay.isSuccess`da, `Loader2` saqlanib) · `pending-card` halqa + `text-display` + skeleton `h-11` + izoh yangilandi + `amountRef` ilgagi · `payment-row` `.motion-row-land` shartsiz | `6958403` |
| 3 (RED) | `collect-session.test.tsx` — G-motion-2(a,b,e) + tartib o'lchovi (`activeAtCall`); ulanishsiz 2 failed | `13b0835` |
| 3 (GREEN) | `onWritten` ulanishi: `amountRef`/`listRef`, `focus()`/`toast`dan keyin, `await`siz, `try/catch`; 11/11 | `9ed03da` |

## Interface kontrakt holati (keyingi rejalar uchun)

- `flyAmountToList({ from, to })` — sof imperativ, istisnoni YUTMAYDI (himoya faqat chaqiruvchida); reduced-motion'da klon UMUMAN yaratilmaydi; `setTimeout` faqat `clone.remove()`.
- `PendingCardProps.amountRef?: Ref<HTMLParagraphElement>` — YANGI ixtiyoriy prop (sabab quyida); qolgan props kontraktlari (`PaymentBarProps`, `PaymentRowProps`) O'ZGARMAGAN.
- `onWritten` tartibi (M-9) TEGILMADI: `setWrote` → `dropPendingAfterPayment` → 5 `setState` → `focus()` → `toast.success` → **[YANGI]** `try { flyAmountToList } catch`. `useCallback` deplari o'zgarmagan (`[client, marketId, money, t]`).
- ≤3 bosish sanog'i (G-20) REGRESSIYASIZ: yettala mavjud test yashil, ikkinchi takror ham 3.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Bloklovchi] `userEvent.type` o'rniga `fireEvent` + fokus-egasi tasdig'i**
- **Topildi:** Task 3, (b) testini yozishda
- **Muammo:** Reja (b) uchun `userEvent.type` deydi, lekin `@testing-library/user-event` lockfile'da YO'Q (grep: 0 natija) va yangi paket o'rnatish TAQIQ (G-motion-3(d), L-8 0 KB; parallel ijro sharti «yangi paket TAQIQ»)
- **Tuzatish:** (b) `document.activeElement === input` AVVAL tasdiqlanadi (fokus qaytgan — terish fokusdagi maydonga boradi), so'ng `fireEvent.change`, so'ng bayram oynasi (700ms) o'tgach qiymat TO'LIQ turgani o'lchanadi — kechikkan `setDraft("")` anti-naqshini S1 sabotaji isbotlaganidek ushlaydi
- **Fayl:** `frontend/src/components/collect/collect-session.test.tsx` · **Commit:** `13b0835`

**2. [Rule 3 - Bloklovchi] `import.meta.url` vitest transformida `file:` sxemasida emas**
- **Topildi:** Task 1 RED yugurishida (`TypeError: The URL must be of scheme file`)
- **Tuzatish:** AST testi manba faylni `process.cwd()` dan o'qiydi (vitest har doim `frontend/` ildizidan yuguradi — `vitest.config.ts` shu yerda); izoh testda
- **Fayl:** `success-choreography.test.tsx` · **Commit:** `26cbfeb`

### Reja ↔ mavjud kontrakt ziddiyatlari (KONTRAKT yutdi — reja bandi bo'yicha yoziladi)

**3. Halqaning (3-qadam) «muvaffaqiyat lahzasi» — proyeksiya `matched` mounti, to'lov lahzasi EMAS**
- M-9 sharti: to'lov 2xx kelgan flush'da `submittedCode=""` → `PendingCard` (va `PaymentBar`) AYNI commit'da unmount bo'ladi — React oraliq holatni CHIZMAYDI, ya'ni «to'lov muvaffaqiyati»da halqani bu daraxt jismonan ko'rsata olmaydi. 6-qadamni kechiktirish TAQIQ (M-9 «TEGILMAYDI»).
- Mavjud ma'lumot ichida komponentning yagona jonli muvaffaqiyat lahzasi — server proyeksiyani tasdiqlagan payt (`matched` false→true). Halqa shu mountda BIR marta o'ynaydi (`both`, cheksiz pulsatsiya yo'q, `aria-hidden` + `pointer-events-none`).
- Jonli to'lov bayramini 4-qadam (klon — React daraxtidan TASHQARIDA, unmount'dan omon qoladi) va 5-qadam (yangi qator qo'nishi) tashiydi — bu rejaning o'z arxitekturasi.

**4. Check-draw (2-qadam) jonli oqimda sub-frame umrli — halollik bandi**
- Reja aytganidek `pay.isSuccess` (busy'ni hosil qiluvchi mutatsiya obyektining MAVJUD bayrog'i) ga ulandi, yangi holat yo'q. LEKIN M-9 unmount'i tufayli jonli oqimda tugma javob flush'ida yo'qoladi — check to'liq 250ms ni faqat bar mounted qolgan holatlarda o'ynaydi. Izoh komponentda ochiq yozildi; ulanish nuqtasi §8.1 shartnomasi bo'yicha joyida.

**5. `PendingCard` prop kontrakti `amountRef` bilan kengaydi (reja ruxsati bilan, sabab shu yerda)**
- 4-qadam FLIP manbai («Kutilayotgan patta» summasi) `PendingCard` ICHIDA yashaydi; sessiya unga DOM so'rovisiz (`querySelector` — mo'rt) yetishi kerak. Ixtiyoriy `Ref` — xulqsiz sof ilgak; berilmasa hech nima o'zgarmaydi.

### Rejalashtirilgan tasdiqlar (reja «SUMMARY'da tasdiqla» degan bandlar)

- **G-motion-3(b) tegilmadi:** klonning davomiyligi inline `transition: "transform var(--motion-slow) var(--ease-out), …"` satrida — bu Tailwind `transition-[` utilitasi EMAS va `duration-<raqam>` ham emas; `motion-tokens.test.mjs` 10/10 yashil (o'lchandi).
- **Konfetti/burst/particle yozilmadi** — G-motion-1(d) ta'rif skani yashil; sabab `deferred-items.md` da (09-01 dan).
- **S1 sabotajning shakli:** rejadagi so'zma-so'z «`await flyAmountToList(...)`» sinxron funksiyada MIKROTASK-NO-OP bo'lib chiqdi (xoreografiya `focus()`dan keyin turgani uchun hech narsani kechiktirmaydi — bu aynan dizayn yutug'i). Darvoza BLOKLASHNI o'lchashi uchun anti-naqshning jonli shakli modellashtirildi: bayram OLDINGA olinib to'liq davomiyligi (700ms) `await` qilindi — reja anti-naqsh blokidagi «`await runChoreography(...)`» ning ayni o'zi.

### Halollik bandlari (tuzatilmagan, sabab bilan)

- **`npm run gate:fast` ning backend yarmi (docker pytest) worktree'da yugurtirilmadi** — 09-01/09-02 dagi ayni band: bu reja backend fayllariga TEGMAGAN (faqat `frontend/` + `.planning/`), worktree'dan ikkinchi compose loyihasini ko'tarish image build + disk xavfi. Frontend yarmi TO'LIQ o'lchandi (quyida). To'liq `gate` — faza darvozasida (09-07, W0-13 protokoli).
- **Vitest yakka o'lchovi 172 s — BYUDJET o'lchovI EMAS** (worktree, tinch bo'lmagan xost, parallel 09-05 ijrochisi ishlayapti). Byudjet qayta o'lchovi — 09-07 bandi.
- **Worktree'da `node_modules` yo'q edi** — `npm ci` (lockfile'dan, yangi paket YO'Q) bilan tiklandi.

## Sabotaj jurnali (3/3 — har birida IKKI natija, modul har doim import qilinadigan holda)

| # | Sabotaj (REAL manba ustida) | Nishon | Qo'shnilar |
|---|------------------------------|--------|------------|
| S0 (Task 1, majburiy) | `success-choreography.tsx` da `if (prefersReducedMotion()) return;` izohga olindi | **G-motion-1(c) `reduce: true` shoxi QIZARDI** — body bolalar soni o'zgardi (1 failed \| 11 passed) | **payment-bar + pending-card 32/32 · collect-surface 11/0 yashil** |
| S1 (Task 3) | `onWritten` async qilinib bayram OLDINGA olindi va 700ms davomiyligi `await` qilindi (`await runChoreography` anti-naqshining jonli modeli) | **(a) va (b) QIZARDI** (+tartib va (e) ham — tartib buzilgani uchun; 4 failed \| 7 passed, G-20 yettalasi yashil) | **payment-bar + pending-card + success-choreography 44/44 · collect-surface 11/0 yashil** |
| S2 (Task 3) | `success-choreography.tsx` dan `clone.style.pointerEvents = "none"` qatori olib tashlandi | **G-motion-2(c) QIZARDI** (1 failed \| 11 passed) | **collect-session + payment-bar + pending-card 43/43 · collect-surface 11/0 yashil** |

Uchalasida ham modul import qilinadigan holda qoldi (08-20 S-5 darsi); uchalasi ham qaytarildi — yakuniy `git status` toza, yakuniy to'plam to'liq yashil.

## TDD Gate Compliance

Task 1 va Task 3 `tdd="true"`: ikkalasida ham RED→GREEN ketma-ketligi commit darajasida bajarildi — `test(09-04)` `c6df23f` (import xatosi bilan 1 failed) → `feat(09-04)` `26cbfeb` (12/12); `test(09-04)` `13b0835` (ulanishsiz 2 failed: chaqiruv + (e)) → `feat(09-04)` `9ed03da` (11/11). (a)/(b) RED bosqichida yashil edi — bu KUTILGAN va rejada ochiq: 6-qadam (M-9) bugundan ishlaydi, ularning qiymati anti-naqshni ushlashda (S1 isbotladi). Falsifikatsiya qatlamini uch sabotaj berdi.

## Verifikatsiya natijalari

| Buyruq | Natija |
|--------|--------|
| `npx vitest run src/components/collect` | **94/94** (Task 2 nuqtasida 90/90, Task 3 dan keyin 94/94) |
| `npx vitest run` (to'liq) | **1138/1138** (96 fayl, 172 s — worktree) |
| `node --test scripts/*.test.mjs` | **330/330** — `collect-surface` (MIN_* tegilmagan) · `motion-tokens` · `contrast` · `theme-tokens` · `submit-gate` · `role-gate` · `bulk-action-surface` · `report-copy` — hammasi REGRESSIYASIZ, birortasi tahrirlanmagan |
| `npx tsc --noEmit` | yashil |
| `npm run lint` (eslint) | yashil (exit 0) |
| `npm test` (frontend gate:fast yarmi) | exit 0 (~175 s) |
| Baza-diff nazorati | `STATE.md` · `ROADMAP.md` · `package.json` · `globals.css` — **nol diff** (tegilmagan) |

## Known Stubs

Yo'q. Ikki halollik bandi stub EMAS, hujjatlangan mexanika chegarasi: (1) check-draw jonli oqimda M-9 unmount'i tufayli sub-frame umrli (Deviatsiya 4); (2) halqa to'lov lahzasida emas, proyeksiya-matched mountida o'ynaydi (Deviatsiya 3). Ikkalasining ulanish nuqtasi, darvozasi va reduced-motion shoxi jonli; jonli to'lov bayramini 1/4/5/6-qadamlar tashiydi.

## Self-Check: PASSED

- FOUND: frontend/src/lib/motion.ts
- FOUND: frontend/src/components/collect/success-choreography.tsx
- FOUND: frontend/src/components/collect/success-choreography.test.tsx
- FOUND: commit c6df23f · 26cbfeb · 6958403 · 13b0835 · 9ed03da
