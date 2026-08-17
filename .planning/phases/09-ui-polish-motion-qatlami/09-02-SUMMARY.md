---
phase: 09-ui-polish-motion-qatlami
plan: 02
subsystem: ui
tags: [tailwind4, motion-tokens, reduced-motion, shimmer, node-test, hover-media]
requires:
  - "09-01: motion token reyestri (--motion-fast/base/slow, --ease-out, --default-transition-*)"
  - "09-01: @keyframes reyestri (8 nom) + .motion-shimmer / .motion-shake sinflari"
  - "09-01: globals.css reduced-motion bloki (G-motion-1(a) ning o'lchov nishoni)"
  - "collect-surface.test.mjs darvoza naqshi (reyestr + quyi chegara + hosila skan)"
provides:
  - "ui/button: duration-(--motion-fast) + active:scale-[0.97] motion-reduce juft + default/destructive'da hover:shadow-raised"
  - "ui/card: transition + hover:-translate-y-0.5 hover:shadow-raised (hover-qobiliyatli qurilmadagina)"
  - "ui/dialog: data-[state] scale/fade + starting: kirish holati; overlay bg-black/8 + blur(4px)"
  - "ui/skeleton: motion-shimmer (animate-pulse o'rniga); ui/field: xato paragrafi .motion-shake"
  - "Beshala Loader2 motion-reduce:animate-none bilan juft (capture-cell namunasi, unga tegilmadi)"
  - "scripts/motion-tokens.test.mjs — G-motion-1(a,b,d) + G-motion-3(a,b,c,d) tirik darvoza"
affects:
  - "09-04/09-05 (Y-1 kassir va Y-2 dashboard shu primitivlarni iste'mol qiladi)"
  - "har keyingi ijrochi: duration-<raqam>, transition-[, yangi paket, juftliksiz animate-* endi mexanik qizil"
tech-stack:
  added: []
  patterns:
    - "Tailwind 4 (--var) sintaksisi: duration-(--motion-fast) — davomiylik utilitada, qiymat reyestrda"
    - "starting: (@starting-style) — Radix data-[state=open] mount'ida kirish tranzitsiyasining boshlang'ich holati"
    - "Darvoza to'plam tengligi: dependencies deepEqual 18 nom — son emas, nom-ma-nom"
key-files:
  created:
    - frontend/scripts/motion-tokens.test.mjs
  modified:
    - frontend/src/components/ui/button.tsx
    - frontend/src/components/ui/card.tsx
    - frontend/src/components/ui/dialog.tsx
    - frontend/src/components/ui/skeleton.tsx
    - frontend/src/components/ui/field.tsx
    - frontend/src/components/collect/payment-bar.tsx
    - frontend/src/components/collect/shift-close-form.tsx
    - frontend/src/components/collect/shift-open-card.tsx
    - frontend/src/components/review/decision-bar.tsx
decisions:
  - "globals.css OCHILMADI: Tailwind 4.3.3 hover: variantini @media (hover: hover) ichida kompilyatsiya qilishi postcss-probe bilan O'LCHANDI — sticky-hover fallback keraksiz"
  - "Dialog kirishi starting: varianti bilan (o'lchandi: @starting-style ga kompilyatsiya) — usiz data-[state] tranzitsiyasi umuman o'ynamasdi"
  - "G-motion-1(b) quyi chegarasi 5 — ataylab aynan to'la: bitta spinner yo'qolsa/juftsiz qolsa darvoza qizaradi"
  - "G-motion-3(a) da ruxsat to'plami + ALOHIDA taqiq ro'yxati birga — taqiqlanganlar nomma-nom mustaqil o'lchanadi"
metrics:
  duration: "~40 min"
  completed: "2026-08-17"
  tasks: 3
  commits: 3
  tests_added: 10
requirements: [SC-4, SC-5]
---

# Phase 9 Plan 02: `ui/` primitivlari jilosi + Loader2 juftliklari Summary

**Beshala `ui/` primitivi token-reyestrli motion oldi (press-scale, hover ko'tarilish, dialog scale/fade, shimmer, shake), beshala `Loader2` reduced-motion bilan juftlandi va `motion-tokens.test.mjs` G-motion-1(a,b,d) + G-motion-3(a,b,c,d) ni uch sabotaj isboti bilan qo'riqlaydi — `dependencies` endi 18 nomga to'plam tengligi ostida.**

## Bajarilgan vazifalar

| # | Vazifa | Commit |
|---|--------|--------|
| 1 | `ui/button` (duration token + press-scale + hover soya faqat soyali variantlarda) · `ui/card` (transition + hover ko'tarilish) · `ui/dialog` (data-[state] scale/fade, overlay 8% + blur) · `ui/skeleton` (shimmer) — props kontraktlari O'ZGARMAGAN | `42c236f` |
| 2 | `ui/field` xato paragrafi shartli `.motion-shake` (FieldProps o'zgarmagan) · 4 ta `Loader2` ga `motion-reduce:animate-none` (`capture-cell` namunasi — unga TEGILMADI) | `af5f298` |
| 3 | `scripts/motion-tokens.test.mjs` — 10 test: G-motion-1(a,b,d) + G-motion-3(a,b,c,d) + reyestr/detektor/runaway o'z-o'zini tekshiruvlari; 3 sabotaj har biri IKKI natija bilan | `1b7c56d` |

## O'lchovlar (reja shart qilganlari)

| # | O'lchov | Natija |
|---|---------|--------|
| **T1-hover** | Tailwind 4.3.3 `hover:` varianti kompilyatsiyasi (postcss + `@source inline` probe, haqiqiy `node_modules` bilan) | ⛔ **`.hover\:-translate-y-0\.5` qoidasi `@media (hover: hover)` bloki ICHIDA chiqdi** → telefonda sticky-hover tug'ilmaydi → **`globals.css` fallback'i KERAK EMAS, fayl umuman ochilmadi** (files_modified'dagi shartli band ishlatilmadi; 09-03 bilan to'qnashuv nol) |
| **T1-starting** | `starting:` varianti | `@starting-style { .starting\:...[data-state="open"] }` ga kompilyatsiya bo'ladi — dialog kirishi uchun ishlatildi |
| **T1-token** | `duration-(--motion-fast)` | `transition-duration: var(--motion-fast)` ga kompilyatsiya — sehrli son yo'q |
| **T1-overlay** | `bg-black/8` | Yaroqli utilita sifatida kompilyatsiya bo'ladi (8% qorayish + `backdrop-blur-[4px]`) |
| **T3-b** | Juftlangan `animate-*` soni | **Aynan 5** (payment-bar, shift-close-form, shift-open-card, decision-bar, capture-cell) — chegara ataylab aynan to'la |

## Interface kontrakt holati (keyingi rejalar uchun)

- `ButtonProps` / `CardProps` / `DialogContentProps` / `SkeletonProps` / `FieldProps` — **birortasi o'zgarmagan**; faqat sinf satrlari kengaydi (09-UI-SPEC §3.3).
- `Skeleton` endi `.motion-shimmer` iste'mol qiladi, `Field` xato paragrafi `.motion-shake` — 09-01 reyestrining birinchi ikki jonli iste'molchisi.
- Yangi kod uchun mexanik chegara tirik: `duration-<raqam>` / `transition-[` / komponentda `@keyframes` / juftliksiz `animate-*` / yangi `dependencies` nomi — har biri `gate:fast` da qizil.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Bloklovchi] Task 1 verify buyrug'i bo'sh to'plamda yiqilardi**
- **Topildi:** Task 1 verifikatsiyasida
- **Muammo:** Reja `npx vitest run src/components/ui` deydi, lekin `src/components/ui` da birorta `.test.tsx` yo'q (Glob bilan tasdiqlandi) — vitest «no test files found» bilan xato qaytaradi
- **Tuzatish:** `npx tsc --noEmit` + primitivlarni iste'mol qiluvchi eng og'ir yuzalar (`src/components/collect src/components/review`, 100/100) bilan almashtirildi; reja yakunida to'liq `npx vitest run` (1110/1110) baribir yugurtirildi. «Mavjud `ui/` testlari yashil» sharti bo'sh to'plamda avtomatik rost
- **Fayl:** yo'q (buyruq adaptatsiyasi) · **Commit:** —

**2. [Rule 1 - Niyat va mexanizm farqi] Dialog kirish tranzitsiyasi rejadagi sinflar bilan UMUMAN o'ynamasdi**
- **Topildi:** Task 1, dialog sinflarini yozishda
- **Muammo:** Radix `Content` DOM'ga `data-state="open"` bilan MOUNT bo'ladi — tranzitsiya uchun boshlang'ich holat o'zgarishi yo'q, ya'ni rejadagi `data-[state=open]:scale-100` + `transition` juftligi hech qanday ko'rinadigan kirish animatsiyasi bermasdi (must_have: «Dialog ochilganda scale+fade bilan keladi»)
- **Tuzatish:** `starting:data-[state=open]:scale-[0.96] starting:data-[state=open]:opacity-0` qo'shildi — `@starting-style` kirishning boshlang'ich holatini beradi (kompilyatsiya o'lchandi, sof CSS, props/xulq kontrakti tegilmadi, `@keyframes` ishlatilmadi — G-motion-3(c) buzilmadi)
- **Fayl:** `frontend/src/components/ui/dialog.tsx` · **Commit:** `42c236f`

### Halollik bandlari (tuzatilmagan, sabab bilan)

- **Dialog yopilish animatsiyasi vizual o'ynamaydi:** rejadagi `data-[state=closed]:*` sinflari joyida, LEKIN Radix tranzitsiya tugashini kutmaydi (faqat `animation` ni kutadi) va elementni darhol unmount qiladi. Tuzatish `forceMount`/xulq o'zgarishini talab qilardi — §3.3 «meros qayta qurilmaydi» va «props kontrakti o'zgarmaydi» taqiqiga zid, shuning uchun QILINMADI. Kirish (talab qilingan truth) ishlaydi; yopilish sinflari reja matni bo'yicha qoldirildi.
- **`npm run gate:fast` ning backend yarmi (docker pytest) worktree'da yugurtirilmadi** — 09-01 dagi ayni band: bu reja backend fayllariga tegmagan, worktree'dan ikkinchi compose loyihasini ko'tarish esa image build + disk xavfi. Frontend yarmi TO'LIQ o'lchandi (quyida). To'liq `gate` — faza darvozasida (09-07, W0-13 protokoli).
- **Vitest yakka o'lchovi 164.5 s — BYUDJET o'lchovi EMAS** (sovuq kesh, yangi worktree, tinch bo'lmagan xost). Bu reja vitest'ga 0 test qo'shdi; skript to'plamiga qo'shgani ~1.2 s (316 test jami 2.9 s). Byudjet qayta o'lchovi — 09-07 bandi (05-15 W0-13).
- **Worktree'da `node_modules` yo'q edi** — `npm ci` (lockfile'dan, yangi paket YO'Q) bilan tiklandi; 09-UI-SPEC §16.7 buni zanjir boshida tekshirishni aynan nazarda tutadi.

## Sabotaj jurnali (3/3 — har birida IKKI natija)

| # | Sabotaj | Nishon | Qo'shnilar |
|---|---------|--------|------------|
| S-1 | `ringpulse` keyframes'iga `height: 0 → 100%` (CSS yaroqli qoldi) | **G-motion-3(a) QIZARDI** — `@keyframes ringpulse -> height` nomma-nom | **contrast + collect-surface + bulk-action-surface: 29/29 yashil** |
| S-2 | `package.json` `dependencies` ga `canvas-confetti: "1.9.3"` (FAQAT JSON qatori — `npm install` BAJARILMADI, slopsquatting yuzasi nol) | **G-motion-3(d) QIZARDI** — xabarda «TAQIQLANGAN nom(lar): canvas-confetti» alohida | **29/29 yashil** |
| S-3 | `@media (prefers-reduced-motion)` blokidan `transition-duration` qatori olib tashlandi | **G-motion-1(a) QIZARDI** — aynan yo'qolgan deklaratsiya ko'rsatildi | **29/29 yashil** |

Uchalasida ham fayl parse qilinadigan holda qoldi (08-20 S-5 darsi); uchalasi ham qaytarildi — yakuniy diff bazaga nisbatan `globals.css`/`package.json` uchun NOL.

## TDD Gate Compliance

Task 3 `tdd="true"`: darvoza testlari Tasks 1–2 (implementatsiya, `feat` commitlari `42c236f`/`af5f298`) dan KEYIN yozildi va birinchi yugurishda 10/10 yashil chiqdi — reja buni ochiq bashorat qilgan («Task 2 dan keyin hammasi juft... chegara AYNAN to'ladi»). RED (falsifikatsiya) isboti reja talab qilgan uch sabotaj bilan berildi: har biri o'z bandini qizartirdi va qaytarildi. `test(09-02)` commiti: `1b7c56d`.

## Verifikatsiya natijalari

| Buyruq | Natija |
|--------|--------|
| `node --test scripts/motion-tokens.test.mjs` | **10/10** (1.2 s) |
| `node --test scripts/*.test.mjs` | **316/316, 21 darvoza fayli** (2.9 s) — mavjud 20 tasi REGRESSIYASIZ, birortasi tahrirlangani yo'q |
| `npx vitest run` | **1110/1110** (94 fayl, 164.5 s — sovuq kesh) |
| `npx tsc --noEmit` | yashil |
| `npm run lint` (frontend eslint) | yashil (exit 0) |
| `grep -c motion-reduce:animate-none` (4 nishon fayl) | har birida **1** |
| Baza-diff nazorati | `capture-cell.tsx` · `globals.css` · `package.json` · `STATE.md` · `ROADMAP.md` — **nol diff** |

## Known Stubs

Yo'q — bu reja yangi render yuzasi qo'shmadi, mavjud primitivlarni jiloladi. `.motion-check-draw` / `.motion-ring-pulse` / `.motion-row-land` / `.motion-enter` / `.motion-breath` / `.motion-attention` sinflari hali iste'molchisiz, lekin bu 09-01 belgilagan interface kontrakti (09-04/09-05 uchun), stub emas.

## Self-Check: PASSED

- FOUND: frontend/scripts/motion-tokens.test.mjs
- FOUND: .planning/phases/09-ui-polish-motion-qatlami/09-02-SUMMARY.md
- FOUND: commit 42c236f · af5f298 · 1b7c56d
