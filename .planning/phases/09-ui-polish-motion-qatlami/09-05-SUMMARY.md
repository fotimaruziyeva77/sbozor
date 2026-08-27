---
phase: 09-ui-polish-motion-qatlami
plan: 05
subsystem: ui
tags: [count-up, raf, sparkline, donut, svg, rbac, blind-declaration, jsdom]
requires:
  - "09-01: .motion-enter/.motion-breath/.motion-shimmer sinflari, --motion-*/--ease-*/--text-display tokenlari"
  - "09-02: ui/skeleton shimmer, ui/button duration-(--motion-fast) presedenti"
  - "09-03: dashboard.revenueTrend*/occupancy* 7 kaliti (3 til)"
  - "useRevenueReport / useOccupancyDay / rbac.ts report_view matritsasi (o'zgarmagan holda)"
provides:
  - "lib/use-count-up.ts: rAF + kubik ease; null'da halqa yo'q; oxirgi kadr qiymatning o'zi; reduced-motion'da hosila oxirgi holat; davomiylik tanlovi hook ichida (birinchi 600, yangilanish updateDurationMs)"
  - "headline-card: text-display SHARTLI (faqat soum), skeleton h-11, sr-only yakuniy qiymat + aria-hidden count, tick bir marta (settledFor, transition-transform)"
  - "dashboard/revenue-card.tsx: 7 kunlik sparkline (sof SVG, stroke-dashoffset 220->0), server from_date/to_date, motion-breath faqat yangilanishda"
  - "dashboard/occupancy-donut.tsx: KECHAgi kun halqasi (226->hisoblangan), stalls=0 da occupancyEmpty, poll o'zi o'chadi"
  - "dashboard/page.tsx: ikki karta report_view sharti ostida (shart SAHIFADA)"
  - "collect-surface.test.mjs: G-motion-6(a) chegara qulflari + (c)(d)(e) yangi skanlar sun'iy-ijobiy nazorat bilan"
affects:
  - "09-07 (faza darvozasi: to'liq gate + byudjet qayta o'lchovi)"
  - "09-06 (verifikatsiya: G-motion-6 va G-motion-7(b,c) endi mexanik)"
tech-stack:
  added: []
  patterns:
    - "Count-up yakuniy qiymati AT uchun sr-only MATN TUGUNI (aria-label emas) — G-33(a) skaneri bilan mos yagona shakl"
    - "Kompozit SVG chizilish davomiyliklari (600ms/250ms) inline transition'da, ease TOKENDAN — @keyframes reyestri parallel wave egaligida"
    - "jsdom'da React onAnimationEnd YETIB BORMAYDI [O'LCHANDI: proba] — native addEventListener('animationend') ikkala muhitda ishlaydi"
key-files:
  created:
    - frontend/src/lib/use-count-up.ts
    - frontend/src/components/dashboard/revenue-card.tsx
    - frontend/src/components/dashboard/revenue-card.test.tsx
    - frontend/src/components/dashboard/occupancy-donut.tsx
    - frontend/src/components/dashboard/occupancy-donut.test.tsx
  modified:
    - frontend/src/components/headline/headline-card.tsx
    - frontend/src/components/headline/headline-card.test.tsx
    - frontend/src/app/[locale]/(app)/dashboard/page.tsx
    - frontend/src/app/[locale]/(app)/dashboard/page.test.tsx
    - frontend/scripts/collect-surface.test.mjs
decisions:
  - "Yakuniy qiymat sr-only matn tuguni sifatida (reja 'aria-label' degan edi) — G-33(a) numericTextNodes skaneri aria-hidden tugunlarni sanamaydi; mavjud darvoza yutdi, a11y natija ayni"
  - "select: ISHLATILMADI — useOccupancyDay imzosi select olmaydi va 'hook ichiga hech narsa qo'shilmaydi' sharti ustun (KONTRAKT yutdi); kun yopiq, poll yo'q — select amalda hech narsa bermasdi"
  - "Sparkline/donut chizilishi inline transition bilan (600ms/250ms literal + izoh) — globals.css @keyframes reyestri bu rejaning fayl ro'yxatidan tashqarida; G-motion-3 darvozalari yashil (duration-<raqam> utilitasi emas)"
  - "Davomiylik tanlovi (600/400) hook ICHIDA — react-hooks/refs 'renderda ref o'qish' taqiqi komponentdagi hadValueRef shaklini rad etdi"
  - "Donut yoy rangi success (band = success — day-breakdown.tsx reyestri), iz — border; aksent byudjeti ochilmadi"
metrics:
  duration: "~85 min"
  completed: "2026-08-17"
  tasks: 3
  commits: 7
  tests_added: 28
---

# Phase 9 Plan 05: Y-2 direktor jonlanishi — count-up, sparkline, donut Summary

**`/dashboard` «bo'shlik»dan «javob»ga aylandi: rAF count-up (600ms, oxirgi kadr formatterniki), 7 kunlik sof-SVG sparkline va KECHAgi kun bandlik halqasi — ikkalasi `report_view` sharti ostida SAHIFADA darvozalangan; kassir sessiyasida karta DOM'da ham yo'q, so'rov ham ketmaydi va bu ikki qatlam sabotaj bilan isbotlandi.**

## Bajarilgan vazifalar

| # | Vazifa | Commit |
|---|--------|--------|
| 1 | TDD RED: useCountUp kontrakti (null/butun kadrlar/oxirgi kadr/reduced-motion/manba skani) + HeadlineCard G-motion-7(b,c) va a11y | `1db4cc7` |
| 1 | TDD GREEN: `lib/use-count-up.ts` + headline-card (text-display SHARTLI, skeleton h-11, sr-only+aria-hidden, tick) | `ea0c1db` |
| 2 | TDD RED: revenue-card (7 kun davri, EmptyState, server sanalari, nafas) + occupancy-donut (KECHA, poll 0, stalls=0, 226→72) | `9356faa` |
| 2 | TDD GREEN: ikki sof-SVG karta; motion-enter + `--i` stagger; native animationend | `b49d4e3` |
| 3 | TDD RED: page.test G-motion-6(b) ikki qatlam (kassir DOM + SO'ROV alohida testlar; direktor bor) + collect-surface (a)(c)(d)(e) | `7afcad1` |
| 3 | TDD GREEN: page.tsx'da ikki karta `hasPermission(roles, "report_view") && principal?.marketId` sharti bilan | `474b55b` |
| 3 | FIX: react-hooks compiler lint (set-state-in-effect, refs-in-render) — hook/tick/davomiylik qayta loyihalandi | `ffd0845` |

## Interface kontrakt holati (keyingi rejalar uchun)

- `useCountUp(value: number | null, durationMs = 600, updateDurationMs?)` → `number | null`. `null`da halqa boshlanmaydi; oraliq kadrlar `Math.round`; oxirgi kadr — qiymatning O'ZI; reduced-motion'da render `value`ni to'g'ridan-to'g'ri qaytaradi (halqasiz). Birinchi animatsiya (0 dan) `durationMs`, keyingilari `updateDurationMs ?? durationMs`.
- `RevenueCard` / `OccupancyDonut` — propssiz; marketId'ni hook o'zi auth-store'dan oladi; sahifa sharti marketId mavjudligini kafolatlaydi. Xatoda ikkalasi ham `null` qaytaradi (headline §10.2 naqshi).
- `collect-surface.test.mjs` yangi reyestrlari: `PERMISSION_CALL_TOKENS` (1), `CELEBRATION_TOKENS` (9, quyi chegara 5), `CONFETTI_TOKENS` (3), `MIN_DASHBOARD_FILES = 3`, `LOCKED_MIN_*` qulflari (14/7).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Bloklovchi muammo] Worktree'da `frontend/node_modules` yo'q edi**
- **Topildi:** Zanjir boshida (SPEC §16.7 ogohlantirishi bo'yicha tekshirildi)
- **Tuzatish:** `npm ci --no-audit` — mavjud `package-lock.json`dan deterministik; YANGI paket qo'shilmadi
- **Commit:** yo'q (faqat lokal muhit)

**2. [Rule 1 - Reja-darvoza to'qnashuvi] Yakuniy qiymat `aria-label` emas — `sr-only` MATN TUGUNI**
- **Topildi:** Task 1, mavjud `headline-card.test.tsx` (G-33 darvozasi) o'qilganda
- **Muammo:** Reja «aria-label'da yakuniy qiymat» degan; G-33(a) ning `numericTextNodes` skaneri esa aria-hidden bo'lmagan MATN tugunlarini sanaydi va «AYNAN 1 raqamli tugun = formatlangan yakuniy qiymat» talab qiladi — aria-label atribut, tugun emas: darvoza qizarardi
- **Tuzatish:** yakuniy qiymat `sr-only` span (haqiqiy matn tuguni, skrinriderga darhol to'liq), sanayotgan span `aria-hidden` — G-33 TEGILMASDAN yashil, a11y natija ayni (`aria-live` baribir yo'q)
- **Fayl:** `headline-card.tsx` · **Commit:** `ea0c1db`

**3. [Rule 3 - Bloklovchi lint] react-hooks compiler qoidalari uch joyni rad etdi**
- **Topildi:** Task 3 verifikatsiyasida (`npm run lint`)
- **Muammo:** (a) `use-count-up` effektida sinxron `setShown` (reduced-motion/from===to shoxlari); (b) headline'da effektda `setSettled(false)`; (c) revenue'da renderda `hadValueRef.current` o'qish
- **Tuzatish:** (a) reduced-motion renderda HOSILA bo'ldi (`if (prefersReducedMotion()) return value`), from===to da setState umuman kerak emas; (b) tick hodisa-asosli `settledFor` (transitionEnd qaysi qiymat uchun tugaganini eslab qoladi — effektsiz qayta qurollanadi); (c) davomiylik tanlovi hook ICHIGA ko'chdi (`useCountUp(total, 600, 400)` — birinchi animatsiya bazaviy, keyingilari update)
- **Fayllar:** `use-count-up.ts`, `headline-card.tsx`, `revenue-card.tsx`, `revenue-card.test.tsx` · **Commit:** `ffd0845`

**4. [Rule 1 - jsdom topilmasi] React `onAnimationEnd` jsdom'da ishlamaydi**
- **Topildi:** Task 2 GREEN o'lchovida (nafas sinfi olib tashlanmadi)
- **Muammo:** Proba bilan o'lchandi: `fireEvent.animationEnd` ham, native dispatch ham React sintetik `onAnimationEnd`ga yetib bormaydi (`AnimationEvent` jsdom'da yo'q); `onTransitionEnd` esa ishlaydi
- **Tuzatish:** nafas tugashi native `addEventListener("animationend")` bilan (ref + effekt) — jsdom'da ham, brauzerda ham ishlaydi
- **Fayl:** `revenue-card.tsx` · **Commit:** `b49d4e3`

**5. [Rule 2 - SPEC §4.4 qoida 5] Count-up'ga reduced-motion himoyasi qo'shildi**
- **Sabab:** Global CSS `@media` bloki FAQAT CSS animatsiyalarini o'chiradi — rAF halqasi JS va o'zini o'zi to'xtatishi shart («hamma harakat 0.01ms, faqat oxirgi holat»); sanayotgan raqam ham harakat
- **Shakl:** jsdom-xavfsiz `matchMedia` guard (stall-map naqshi) `lib/motion.ts`siz INLINE — u parallel 09-04 ning fayli va bu worktree'da mavjud emas
- **Fayl:** `use-count-up.ts` · **Commit:** `ea0c1db` (+ `ffd0845` hosila shaklga)

### Reja-kontrakt farqlari (reja o'zi belgilagan qoida bo'yicha)

- **`select:` ISHLATILMADI** — reja «useQuery select bilan ikki songa qisqartiriladi» degan, LEKIN `useOccupancyDay(day, todayIso, {enabled?})` imzosi `select` olmaydi va rejaning o'z sharti («hook'lar ICHIGA hech narsa qo'shilmaydi» + «kontrakt yutadi») ustun. Amaliy narx nol: kun YOPIQ (poll yo'q, bitta fetch) — `items[]` keshda turadi, komponent faqat 3 hisoblagichni o'qiydi, DOM'ga tushmaydi.
- **Sparkline/donut chizilish davomiyliklari (600ms, 250ms) inline `transition`da** — reja `stroke-dashoffset 220→0, 600ms` dedi, mexanizmni ochiq qoldirdi; `@keyframes` esa FAQAT `globals.css`da bo'lishi shart (G-motion-3(c)) va u fayl bu rejaning ro'yxatidan TASHQARIDA (parallel wave egaligi). Tanlangan shakl — FLIP-klon presedenti (09-RESEARCH Kod namunalari 3): inline `transition`, ease TOKENDAN, reduced-motion global blok bilan o'chadi. G-motion-3(a,b,c) darvozalari yashil o'lchandi (`duration-<raqam>` utilitasi ham, inline `animation:` ham yo'q). Tick esa токенда: `transition-transform duration-(--motion-fast)`.
- **`stroke-dasharray: 220` — [ASSUMED]** (reja o'zi belgilagan): `getTotalLength()` jsdom'da yo'q; jonli ko'rikda chiziq to'liq chizilmasa qiymat ko'z bilan sozlanadi (09-HUMAN-UAT yuzasi).

### Verifikatsiya chetlanishlari (halollik bandi)

- **`npm run gate:fast` ning backend yarmi (docker pytest) yugurtirilmadi** — 09-01/09-03 protokoli: bu reja backend fayllariga TEGMAGAN (faqat `frontend/` + `.planning/`), backend testlari baza commitdagi bilan bit-aynan; worktree'dan ikkinchi compose loyihasi disk xavfi. Frontend yarmi TO'LIQ: skriptlar **335/335**, vitest **1145/1145**, `tsc --noEmit`, `npm run lint` — hammasi yashil. To'liq `gate` — faza darvozasida (09-07, W0-13 protokoli).
- **`npm run build` yugurtirilmadi** — reja verifikatsiya bloki talab qilmagan; yagona yangi utility-sintaksis (`duration-(--motion-fast)`) 09-02 da `ui/button.tsx`da build bilan tasdiqlangan presedent. To'liq build — faza darvozasida.

## Sabotaj jurnali (2 sabotaj, reja talabi bo'yicha har biri IKKI natija bilan)

| # | Sabotaj | Nishon | Qo'shnilar |
|---|---------|--------|------------|
| S1a | `page.tsx` sharti `report_view` → `market_manage` (kassirga yopiq, LEKIN direktorga ham) | **Direktor testi QIZARDI** (ikkala karta topilmadi) | **5/6 yashil** — kassirning ikkala qatlami va H6/H7 tinch |
| S1b | Shart butunlay olib tashlandi (kartalar shartsiz) | **Kassirning IKKALA qatlami QIZARDI** — DOM testi ham, SO'ROV testi ham (alohida ikki test) | **4/6 yashil** — H6/H7 va direktor tinch |
| S2 | `uz-Latn.json` `collect`ga `"cheer": "Ajoyib!"` | **G-motion-6(d) QIZARDI** — aynan `uz-Latn.json: collect.cheer -> Ajoyib` | **15/16 yashil** collect-surface ichida; sabotaj ostida `role-gate` **6/6**, `forbidden-notice` **3/3** |

Uchala holatda ham fayllar parse/yig'iladigan holda qoldi; uchalasi ham qaytarildi. Yakuniy holat: page testlari **6/6**, collect-surface **16/16**, `i18n:check` **1373 kalit × 3 til** parity.

## Verifikatsiya natijalari

| Buyruq | Natija |
|--------|--------|
| `npx vitest run` | **1145/1145** (97 fayl; +23 yangi test) |
| `node --test scripts/*.test.mjs` | **335/335** (collect-surface 11→16: (a) qulf, (c), (d), (e), sun'iy-ijobiy nazorat) |
| `node --test scripts/motion-tokens.test.mjs` | 10/10 — yangi kartalar G-motion-3 ni buzmaydi |
| `node --test scripts/report-copy.test.mjs` | 44/44 — sparkline `/reports`ga qo'yilmagan, G-42 tinch |
| `npm run i18n:check` | drift yo'q; 1373 kalit parity (yangi kalit QO'SHILMADI) |
| `npx tsc --noEmit` | yashil |
| `npm run lint` | yashil (3 ta react-hooks xatosi topilib, `ffd0845` da yechildi) |

## Known Stubs

Yo'q — ikkala karta ham MAVJUD endpointlarga to'liq ulangan (`GET /reports/revenue`, `GET /occupancy?day=kecha`), EmptyState shoxlari o'lchangan holatlarga mos («7 kundan kam», «kun hali yopilmagan»). `SPARKLINE_DASH = 220` — [ASSUMED] vizual kalibr qiymati, stub emas (09-HUMAN-UAT bandi).

## Threat Flags

Yo'q — yangi endpoint, sxema maydoni yoki huquq yo'q. Reja `<threat_model>` dagi mitigatsiyalar bajarildi: T-09-03 (ikki qatlam: sahifa sharti + server REPORT_VIEW), T-09-16 (komponentlarda `hasPermission(` 0 — mexanik skan), T-09-04 (bayram copy 0, konfetti identifikatorlari 0), T-09-14 (`occupied_slots` `collect/**`ga olib borilmadi — bandlik tipi faqat `dashboard/**`da), T-09-17 (oxirgi kadr formatterniki, `null`da count yo'q, kasr yo'llari manba skani bilan 0).

## Self-Check: PASSED

- FOUND: frontend/src/lib/use-count-up.ts (requestAnimationFrame ✓)
- FOUND: frontend/src/components/dashboard/revenue-card.tsx (stroke-dashoffset ✓)
- FOUND: frontend/src/components/dashboard/occupancy-donut.tsx (role="img" ✓)
- FOUND: frontend/src/components/dashboard/revenue-card.test.tsx · occupancy-donut.test.tsx
- FOUND: commit 1db4cc7 · ea0c1db · 9356faa · b49d4e3 · 7afcad1 · 474b55b · ffd0845
