---
phase: 09-ui-polish-motion-qatlami
plan: 06
subsystem: ui
tags: [locale-switcher, table-hover, starting-style, cls, typography-gate, node-test]
requires:
  - "09-01: .motion-attention sinfi, --motion-slow/--ease-out/--default-transition-* tokenlari, @keyframes yopiq reyestri (8 nom)"
  - "09-02: motion-tokens darvozasi + ui/dialog `starting:` presedenti (Tailwind 4.3.3 @starting-style kompilyatsiyasi O'LCHANGAN)"
  - "09-04: pending-card text-display + skeleton h-11 (G-motion-7(c) juftligining birinchi yarmi)"
  - "09-05: headline-card shartli text-display + skeleton h-11 (juftlikning ikkinchi yarmi)"
provides:
  - "shell/locale-switcher: sirg'aluvchi faol indikator — bitta absolut element, translateX(calc(var(--idx) * (100% + 0.25rem))), w-20 umumiy kenglik (BUTTON_WIDTH_CLASS), transition-transform"
  - "Jadval qator hover foni 10/12 faylda (transition-colors + hover:bg-surface-muted); 2 istisno sabab bilan"
  - "case-list: §10.5 kirish (starting:-translate-x-2 + duration-(--motion-slow), 400ms token) + amber .motion-attention halqasi faqat status=new, bir marta"
  - "scripts/typography.test.mjs — G-motion-7(a,c,d,e): Display-XL yopiq qamrovi (deepEqual, aynan 2 fayl), geometriya juftligi bitta reyestrdan, deviatsiya chegaralari 7/4/0/0/21 qulflangan"
affects:
  - "09-07 (faza darvozasi: to'liq gate + byudjet qayta o'lchovi)"
tech-stack:
  added: []
  patterns:
    - "Kirish tranzitsiyasi yopiq keyframes reyestriga tegmasdan: `starting:` variant + transition-transform + duration-(--var) — dialog presedentining qator shakli"
    - "Bir elementda ikki davomiylik kerak bo'lsa: qatorda transform-oila (400ms), kataklarda group-hover + transition-colors (150ms standart) — ikki savolga bitta duration berilmaydi"
    - "Teng-kenglik indikator o'lchovsiz: kenglik sinfi bitta konstantada, siljish 100% + gap calc'ida — getBoundingClientRect jsdom'da 0 bergani uchun taqiq"
key-files:
  created:
    - frontend/src/components/shell/locale-switcher.test.tsx
    - frontend/scripts/typography.test.mjs
  modified:
    - frontend/src/components/shell/locale-switcher.tsx
    - frontend/src/components/billing/charge-list.tsx
    - frontend/src/components/billing/variance-list.tsx
    - frontend/src/components/reconciliation/case-list.tsx
    - frontend/src/components/reconciliation/delivery-list.tsx
    - frontend/src/components/reconciliation/unpaid-list.tsx
    - frontend/src/components/reconciliation/unregistered-list.tsx
    - frontend/src/components/reports/anomaly-archive.tsx
    - frontend/src/components/reports/compare-table.tsx
    - frontend/src/components/reports/debtors-report.tsx
    - frontend/src/components/reports/revenue-report.tsx
decisions:
  - "LocaleSwitcher yorliqlari ENDONIM bo'lib qoldi (01-08 kontrakti yutdi; reja «UZ/ЎЗ/RU» degan edi) — teng kenglik w-20 eng uzun endonimga yetadi"
  - "Case kirishi yangi @keyframes bilan EMAS — @starting-style tranzitsiya bilan: reyestr yopiq (8 nom) va globals.css 09-01 egaligida; 09-05 sparkline qarori bilan ayni sinf"
  - "Case qatorida hover group-hover orqali KATAKLARDA: qatorning transition-transform'i (400ms) fon rangiga tegmaydi, hover 150ms standart tokenda qoladi"
  - "Amber halqa <tr> ustida emas, birinchi katak ichidagi absolut span'da: border-collapse jadvalda qator box-shadow'i brauyzerlararo ishonchsiz"
  - "G-motion-7(c) «isPending shoxi» butun-fayl skani bilan (AST'siz): reyestr fayllarida Skeleton faqat pending shoxida yashaydi; AST typescript importini olib kelardi"
metrics:
  duration: "~42 min"
  completed: "2026-08-17"
  tasks: 4
  commits: 6
  tests_added: 15
requirements: [SC-5]
---

# Phase 9 Plan 06: Qolgan jilo — locale indikatori, jadval hover, G-motion-7 Summary

**Til almashtirgichning faol foni endi sakramaydigan bitta sirg'aluvchi indikator (`translateX(calc(var(--idx) * (100% + 0.25rem)))`, o'lchovsiz), 12 jadval faylining har biri uchun alohida hover hukmi (10 qo'shildi / 2 istisno — sabab va o'lchov bilan), §10.5 case kirishi `@starting-style` + `--motion-slow` bilan (yopiq keyframes reyestriga tegmasdan) va `typography.test.mjs` — Display-XL ning deepEqual yopiq qamrovi hamda CLS'ning yagona mexanik o'lchovi ikki REAL sabotaj isboti bilan jonli.**

## Bajarilgan vazifalar

| # | Vazifa | Commit |
|---|--------|--------|
| 1 (RED) | `locale-switcher.test.tsx` — 9 test: teng kenglik, `--idx`/translateX inline, transform-only, a11y, oqim; 5 failed \| 4 passed (mavjud xulq qo'riqchisi) | `b002947` |
| 1 (GREEN) | Indikator: absolut span, `w-20` (bitta konstanta), `transition-transform`, aria-hidden; `change()` oqimi tegilmagan; 30/30 | `8b7b1d9` |
| 2 | A guruh hover (5 qo'shildi, 1 istisno, 1 group-shakl) + case kirishi (`starting:-translate-x-2`, 400ms token) + amber `.motion-attention` halqasi | `1325a5e` |
| 3 | B guruh hover (4 qo'shildi, 1 istisno o'lchov bilan); report-copy 44/44, snapshot-copy 13/13 tegilmagan | `009c7f3` |
| 4 | `typography.test.mjs` — G-motion-7(a,c,d,e), 6/6; ikki sabotaj ikki natija bilan | `887c578` |

## Jadval hover — 12 faylning HAR BIRI uchun hukm (§12.8)

**Hosila skan qayta yugurtirildi (ijro boshida):** `grep -rl "<tbody" frontend/src --include=*.tsx` (testlar chiqarilgan) → **12 fayl — reja e'loni bilan aynan mos, drift YO'Q.**

### A guruh (Task 2)

| # | Fayl | Hukm | Sabab |
|---|------|------|-------|
| 1 | `billing/charge-list.tsx` | **qo'shildi** | Qatorlar yalang'och (`border-b` xolos) — `transition-colors hover:bg-surface-muted` |
| 2 | `billing/variance-list.tsx` | **qo'shildi** | Qator foni yo'q; `VarianceCell` pilli — INLINE element, o'z fonini hover USTIDA saqlaydi, semantik signal bosilmaydi |
| 3 | `occupancy/confusion-matrix.tsx` | **istisno** | 2×2 STATIK matritsa: kataklar semantik tint tashiydi (`bg-danger/12` false_occupied, `bg-warning/20` false_empty); 2 qatorli jadvalda hover'ning skanlash qiymati nol va tint chetlari bilan aralashib «tanlangan qator» degan yolg'on signal berardi |
| 4 | `reconciliation/case-list.tsx` | **qo'shildi** (group shakli) | Hover `group-hover:bg-surface-muted` bilan BESH KATAKDA: qator o'zi `transition-transform duration-(--motion-slow)` tashiydi (kirish) va qator darajasidagi hover foni 400ms'ga tushib qolardi — kataklardagi `transition-colors` 150ms standart tokenda |
| 5 | `reconciliation/delivery-list.tsx` | **qo'shildi** | Qatorlar yalang'och; `DeliveryBadge` inline — bosilmaydi |
| 6 | `reconciliation/unpaid-list.tsx` | **qo'shildi** | Qatorlar yalang'och; `CaseStatusBadge`/`EvidenceLink` inline |
| 7 | `reconciliation/unregistered-list.tsx` | **qo'shildi** | Qatorlar yalang'och |

### B guruh (Task 3)

| # | Fayl | Hukm | Sabab |
|---|------|------|-------|
| 8 | `reports/anomaly-archive.tsx` | **qo'shildi** | Qatorlar yalang'och |
| 9 | `reports/compare-table.tsx` | **qo'shildi** | `DiffCell` badge'i inline — farq signali (uch kanal) hover ostida to'liq ko'rinadi |
| 10 | `reports/debtors-report.tsx` | **qo'shildi** | `text-danger-text` — MATN rangi, fon emas; hover bg bilan to'qnashmaydi |
| 11 | `reports/revenue-report.tsx` | **qo'shildi** | `diffClass` matn rangi; kontrast juftliklari G-motion-5 reyestrida o'lchangan |
| 12 | `snapshots/capture-grid.tsx` | **istisno** (o'lchov bilan) | `capture-cell.tsx` tint reyestri o'lchandi: **9/9 holat tinti `bg-*` tashiydi** (`bg-success/12` ×1, `bg-warning/20` ×3, `bg-danger/12` ×2, `bg-surface-muted` ×3); sticky qator-sarlavha `<th>` ochiq `bg-surface` bilan; jadval `border-separate border-spacing-1` — qator hover foni faqat 4px oraliqlarni bo'yab to'qqiz holat rangini ifloslantirardi va sticky ustun foni bilan to'qnashardi |

## Interface kontrakt holati (keyingi rejalar uchun)

- `LocaleSwitcher`: `role="group"` + `aria-label` + `aria-current` + endonim yorliqlar + `change()` oqimi (useTransition, `router.replace(pathname, {locale})`, sessiyada `PATCH /me`, jim catch) — O'ZGARMAGAN. Yangi: `BUTTON_WIDTH_CLASS = "w-20"` (tugma va indikatorning bitta kenglik manbai), indikator `data-active-index` atributi bilan topiladi.
- `typography.test.mjs` reyestrlari: `DISPLAY_REGISTRY` (aynan 2, tenglik — chegara emas), `GEOMETRY_PAIRS` (`text-display→h-11`, `text-2xl→h-8`, kattadan-kichikka), chegara qulflari `7/4/0/0/21` (ko'tarish TAQIQ — tuzatish yangi komponentda).
- Case qatori: `starting:` faqat BIRINCHI renderda ishlaydi — sahifalash/saralashda qayta o'ynamaydi (FLIP taqiqi o'z-o'zidan hurmat qilinadi).

## Deviations from Plan

### Reja ↔ mavjud kontrakt ziddiyatlari (KONTRAKT yutdi — reja bandi bo'yicha yoziladi)

**1. LocaleSwitcher yorliqlari «UZ / ЎЗ / RU» EMAS — endonimlar**
- Reja Task 1: «matnlar `UZ` / `ЎЗ` / `RU` — qisqa va yaqin» deb taxmin qilgan. Mavjud kontrakt: `api-types.ts::LOCALE_LABELS` — «O'zbekcha» / «Ўзбекча» / «Русский», 01-08 qarori bilan qulflangan (til nomi har doim o'z tilida; «Русский»ni o'girish tanlovni o'qib bo'lmas qilardi).
- KONTRAKT yutdi: yorliqlar tegilmadi. Teng-kenglik mexanizmi endonimlarga ham qo'llanadi — `w-20` (80px) eng uzun endonim (~55px @ text-xs semibold) uchun yetarli, sabab komponент izohida.

**2. §12.9 `--motion-base` ≠ rejaning `--default-transition-*` ko'rsatmasi — reja (ijro shartnomasi) yutdi**
- SPEC §12.9 indikatorga `--motion-base` (250ms) yozgan; reja Task 1 esa ochiq buyurdi: «Yumshoqlik `transition` utilitasi va `--default-transition-*` (09-01) orqali keladi» va `duration-<raqam>`/`transition-[` taqiqladi.
- Ijro: `transition-transform` yolg'iz — davomiylik `--default-transition-duration` (=`--motion-fast`, 150ms), ease `--ease-out`. Indikator 80px masofani bosadi — 150ms bu masshtabda to'g'ri his; 250ms xohlansa 09-07 da `duration-(--motion-base)` bir sinf qo'shiladi.

**3. §10.5 «`.motion-enter` naqshi» yangi keyframe bilan EMAS — `@starting-style` tranzitsiya bilan**
- `.motion-enter` keyframe'i `translateY(8px)` + `--motion-base` (09-01 da qulflangan); §10.5 esa `translateX` + **400ms** talab qiladi. `@keyframes` reyestri YOPIQ (8 nom, «FAQAT globals.css») va `globals.css` bu rejaning fayl ro'yxatidan TASHQARIDA.
- Yechim: `starting:-translate-x-2` + `transition-transform` + `duration-(--motion-slow)` — 400ms TOKEN bilan (sehrli son yo'q), `translate` xossasi transform oilasida (build CSS'da o'lchandi: `transition-property: transform, translate, scale, rotate`). Presedent: `ui/dialog.tsx` (09-02 T1 o'lchovi) va 09-05 ning «globals.css parallel egalikda — inline transition» qarori.
- Farq: kirishda opacity fade YO'Q (sof sirg'alish) — §10.5 literal faqat `translateX` deydi; `transition-transform` opacity'ni qamramaydi va bu hover-davomiylik ajratishning narxi emas, spec'ning o'z shakli.

**4. Amber halqa `<tr>` ustida emas — birinchi katak ichidagi absolut `span`da**
- `case-list` jadvali `border-collapse`: qator `box-shadow`'i bu rejimda brauzerlararo ishonchsiz chiziladi. Halqa `relative` katakdagi `absolute inset-1` aria-hidden span'da — `.motion-attention` (09-01: amber `oklch(0.78 0.15 85)`, 0→10px shaffof, `--motion-slow`, iteration 1). Qayta pulsatsiya yo'q; holatni `CaseStatusBadge` MATN bilan aytadi (rang yolg'iz signal emas).

### Auto-fixed Issues

**5. [Rule 3 - Bloklovchi muhit] Worktree'da `frontend/node_modules` yo'q edi**
- SPEC §16.7 ogohlantirishi bo'yicha zanjir boshida tekshirildi; `npm ci --no-audit` (lockfile'dan, YANGI paket yo'q). Commit yo'q — faqat lokal muhit.

**6. [Rule 1 - Test qobig'i] `useAuthStore()` provayder talab qiladi**
- RED birinchi yugurishda 9/9 failed — `AuthProvider` o'rami yo'q edi. Qobiq `app-shell.test.tsx` naqshi bilan tuzatildi (kontrakt emas, harness). Commit: `b002947` ichida.

## Sabotaj jurnali (2/2 — har birida IKKI natija, fayllar yig'iladigan holda)

| # | Sabotaj (REAL manba ustida) | Nishon | Qo'shnilar |
|---|------------------------------|--------|------------|
| S1 | `billing/pending-summary.tsx` dagi `text-sm` → `text-display` (uchinchi mahsulot fayli) | **G-motion-7(a) QIZARDI** — deepEqual farqi faylni nomma-nom ko'rsatdi (1 failed \| 5 passed) | **motion-tokens + contrast + theme-tokens + collect-surface: 50/50 yashil** |
| S2 | `collect/pending-card.tsx` skeletoni `h-11` → `h-9` (09-04 dan OLDINGI holatga qaytarish) | **G-motion-7(c) QIZARDI** — «qiymat skeletoni h-9, eng katta shox text-display (juftligi h-11)» (1 failed \| 5 passed) | **50/50 yashil** |

Ikkalasi ham qaytarildi; yakuniy `git status` toza, typography 6/6.

## TDD Gate Compliance

- **Task 1** (`tdd="true"`): RED→GREEN commit darajasida — `test(09-06)` `b002947` (5 failed: indikator mexanikasi yo'q | 4 passed: mavjud xulq qo'riqchisi — 09-04 presedenti bilan ochiq yozildi) → `feat(09-06)` `8b7b1d9` (30/30).
- **Task 4** (`tdd="true"`, darvoza-fayl): `test(09-06)` `887c578`. RED bosqichi sog'lom bazada YASHIL chiqdi va bu KUTILGAN — o'lchanadigan holat (text-display 2 fayl, h-11 juftligi, chegaralar 7/4/0/0/21) 09-04/09-05 da allaqachon qurilgan; darvozaning falsifikatsiya qatlamini REJA TALAB QILGAN ikki sabotaj berdi (S1→(a) qizil, S2→(c) qizil — har biri qo'shni 50/50 yashil bilan). `feat` commiti yo'q, chunki tuzatiladigan mahsulot nuqsoni topilmadi.

## Verifikatsiya natijalari

| Buyruq | Natija |
|--------|--------|
| `node --test scripts/typography.test.mjs` | **6/6** |
| `node --test scripts/*.test.mjs` | **341/341** (22 skript-darvoza; 09-01 dagi «24 (20+4)» bahosi emas — bugungi haqiqiy son 21 mavjud + 1 yangi; mavjud 21 tasi REGRESSIYASIZ va TAHRIRLANMAGAN) |
| `npx vitest run` (to'liq) | **1170/1170** (99 fayl; +9 yangi locale-switcher testi) |
| `npx vitest run src/components/reconciliation src/components/billing src/components/occupancy` | 194/194 |
| `npx vitest run src/components/reports src/components/snapshots` | 147/147 |
| `node --test scripts/report-copy.test.mjs` / `snapshot-copy` / `motion-tokens` | 44/44 · 13/13 · 10/10 |
| `npm run i18n:check` | 1373 kalit × 3 til parity (yangi kalit QO'SHILMADI) |
| `npx tsc --noEmit` · `npm run lint` | yashil (exit 0) |
| `npm run build` | exit 0 — SSG 3 locale; build CSS'da o'lchandi: `@starting-style{.starting\:-translate-x-2…}`, `transition-duration:var(--motion-slow)`, `.motion-attention` |
| Baza-diff nazorati | `STATE.md` · `ROADMAP.md` · `package.json` · `package-lock.json` · `globals.css` — **nol diff** |

### Verifikatsiya chetlanishlari (halollik bandi)

- **`npm run gate:fast` ning backend yarmi (docker pytest) yugurtirilmadi** — 09-01/09-04/09-05 dagi ayni band: bu reja backend fayllariga TEGMAGAN (faqat `frontend/` + `.planning/`), backend testlari baza commitdagi bilan bit-aynan; worktree'dan ikkinchi compose loyihasi disk xavfi. **Frontend yarmi TO'LIQ va VAQT bilan: 169 s** (scripts 341/341 + vitest 1170/1170; byudjet 200 s, nominal zaxira 31 s) — LEKIN bu BYUDJET O'LCHOVI EMAS (worktree, tinch bo'lmagan xost, W0-13). Rasmiy qayta o'lchov — 09-07 faza darvozasida (A3 riski o'sha yerda yopiladi).

## Known Stubs

Yo'q — indikator, hover va halqa to'liq ulangan; `typography.test.mjs` jonli darvoza. Ikki istisno (confusion-matrix, capture-grid) stub emas — sabab va o'lchov bilan yozilgan dizayn hukmlari.

## Threat Flags

Yo'q — yangi endpoint, kiritma, sir yoki paket yo'q. Reja `<threat_model>` mitigatsiyalari bajarildi: T-09-18 (geometriya juftligi bitta reyestrdan — G-motion-7(c) jonli, S2 isboti), T-09-19 (to'plam tengligi + chegara qulflari — S1 isboti; chegara ko'tarish testning o'zida taqiqlangan), T-09-20 (fon rangi bor qatorlar istisno — 2/12 nomma-nom; rang yolg'iz signal emas — halqa aria-hidden, holat badge MATNI bilan).

## Self-Check: PASSED

- FOUND: frontend/scripts/typography.test.mjs (`text-display` ✓)
- FOUND: frontend/src/components/shell/locale-switcher.test.tsx
- FOUND: locale-switcher.tsx `translate` ✓ (translateX calc)
- FOUND: commit b002947 · 8b7b1d9 · 1325a5e · 009c7f3 · 887c578
