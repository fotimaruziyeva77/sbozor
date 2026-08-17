# Phase 9: UI-polish — motion qatlami — Tadqiqot

**Tadqiqot sanasi:** 2026-08-17
**Domen:** CSS-only motion qatlami · Tailwind 4 token-scope temalar · jsdom'da animatsiya darvozalari
**Ishonch:** HIGH (asosiy topilmalar shu sessiyada mashina bilan o'lchandi)
**Til:** uz-Latn

---

## Xulosa

09-UI-SPEC **NIMA** qurilishini to'liq qulflagan (7 ta `G-motion-*` darvozasi, 34 kod-o'lchov, 10 ta [QULF] qaror). Bu tadqiqot faqat **QANDAY** qurilishiga javob beradi va u uchta savolga tayanadi: (1) jsdom bu animatsiyalarni umuman o'lchay oladimi, (2) Tailwind 4 token-scope temasi kaskadda haqiqatan g'alaba qiladimi, (3) UI-SPEC'ning raqamlari bugungi kodbazaga mosmi.

Uchala savolga ham **o'lchov bilan** javob berildi. Ikkitasi yashil, bittasi **uchta aniq nomuvofiqlik** ochdi va ular tuzatilmasa uchta darvoza **birinchi kunidayoq yolg'on qizil** beradi: `dependencies` soni **18**, SPEC esa 20 deydi; dark rejimning uchta xromatik tokeni SPEC keltirgan nisbatdan **+0.10** farq qiladi, G-motion-5(c) esa **±0.01** talab qiladi; va `--ease-out` ni qayta ta'riflash bugungi **30 ta** `transition-colors` ga **umuman ta'sir qilmaydi**, chunki ular boshqa tokendan (`--default-transition-timing-function`) oziqlanadi.

Eng qimmat texnik topilma — **jsdom animatsiya haqida hech nima bilmaydi**: `matchMedia` yo'q, `Element.animate` yo'q, `getAnimations()` yo'q, `getBoundingClientRect()` nol qaytaradi, Tailwind sinflari hech qanday hisoblangan uslub bermaydi. Bu G-motion-1(c) va G-motion-2(c) ning yozilish shaklini **majburlaydi**: tasdiqlar `matchMedia` stubi + **inline uslub** ustida o'lchanishi shart, sinf nomi yoki hisoblangan CSS ustida emas.

**Asosiy tavsiya:** `globals.css` ni **birinchi** wave'da yopish (motion tokenlari + `--default-transition-*` qayta bog'lash + global reduced-motion bloki + uchta tema scope), so'ng **kontrast kalkulyatorini** yozib, uning chiqishini `globals.css` izohlariga **generatsiya** qilish (SPEC raqamlarini KO'CHIRMASDAN), keyin komponent qatlamiga o'tish. Sabab §Pitfall 2 va §Pitfall 6 da.

---

<user_constraints>
## Foydalanuvchi cheklovlari

⛔ `09-CONTEXT.md` **mavjud emas** (`has_context: false`). Cheklovlarning manbai — **09-UI-SPEC.md** (`status: approved`) va `sketch-findings-bozor` skill'i. Ikkalasidagi qarorlar foydalanuvchi tomonidan **2026-08-16 da tasdiqlangan** (sketch 001-B / 002-B g'oliblari) va bu tadqiqot ularni **QULFLANGAN** deb oladi — qayta ochilmaydi, muqobili tadqiq qilinmaydi.

### Qulflangan qarorlar (09-UI-SPEC §2, so'zma-so'z)

| # | Qulflangan qaror | Manba |
|---|------------------|-------|
| **L-1** | Iliq fon `#FAFAF9` — light temaning yangi bazasi; dark **token-scope** bilan | sketch 002-B |
| **L-2** | `--motion-fast:150ms` · `--motion-base:250ms` · `--motion-slow:400ms`; `--ease-out: cubic-bezier(0.22,1,0.36,1)`; `--ease-spring: cubic-bezier(0.34,1.56,0.64,1)` | sketch 001-B |
| **L-3** | To'lov muvaffaqiyati — **6-qadam** xoreografiya, aniq timinglar, jami ~700ms, ⛔ **BLOKLAMAYDI** | sketch 001-B |
| **L-4** | Konfetti ⛔ **FAQAT** kunlik plan bajarilganda; sessiyada **bir marta**; **12 zarra**, **600ms** | sketch 001-B |
| **L-5** | Dashboard: shimmer **1.5s** (⛔ spinner TAQIQ) → stagger **60ms** → count-up **600ms** + tick `scale(1.03)` → sparkline/donut **600ms**; case amber ⛔ **BIR marta** diqqat-halqa | sketch 002-B |
| **L-6** | Yangi to'lov real-vaqt: **400ms** yumshoq count + **bir marta** yashil «nafas» | sketch 002-B |
| **L-7** | **G-motion-1** (`prefers-reduced-motion`) va **G-motion-2** (kassir ≤150ms) — ikkalasi ham **testda o'lchanadi** | ROADMAP SC#4 |
| **L-8** | Faqat `transform`/`opacity`; motion kutubxonasi ⛔ **FAQAT** vau/layout uchun, **+35KB gzip MAX**; qolgani **sof CSS** | masterplan §8 |
| **L-9** | Pul: **Display-XL (40px)** faqat summalar; `tabular-nums` **hamma raqamda** | masterplan §2 |
| **L-10** | Landing ⛔ **bu SPEC'ga kirmaydi** — Phase 10 niki | Topshiriq |

### Claude ixtiyori (SPEC §18 da standart tanlangan, tetigi bilan)

O-01…O-07 — konfetti tetigi (**qurilmaydi**), standart tema (**`light`**), ikki kartaning huquqi (**`report_view`**), sparkline davri (**7 kun**), 4-qadamning desktopda ishlashi (**ha**), `success-fg` ni quyuqlashtirish (**shu fazada**), shimmer 1.5s (**saqlanadi**). ⛔ Bu tadqiqot ularning **birortasini qayta ochmaydi** — faqat ijro yo'lini o'lchaydi.

### Qamrovdan tashqarida (SPEC §17)

Landing · konfetti **ijrosi** · «Bugun yig'ildi» hisoblagichi · masterplan §6.3 ning to'liq 2-ustunli grid'i · View Transitions API · 12 ta bo'sh-holat illustratsiyasi · plan-xarita zoom inersiyasi · kamera thumbnail'lari · smena «muhri» · usta/NVR animatsiyalari · terse validatsiyalar copy auditi · Storybook · skrinshot-solishtiruv.
</user_constraints>

---

<phase_requirements>
## Faza talablari

⛔ Topshiriqda: *«TBD — plan bosqichida aniqlanadi (UI-polish mavjud talablarning sifat qatlami)»*. `.planning/REQUIREMENTS.md` da **UX kategoriyasi yo'q** [O'LCHANDI: `grep "^### " REQUIREMENTS.md` → FOUND · MARKET · CAM · AI · BILL · CASH · RECON · BOT, hammasi]. Ya'ni 9-faza **yangi talab yaratmaydi**, uchta mavjud talabning **sifat qatlamini** yopadi:

| ID | Bugungi holat | 9-faza nima qo'shadi | Tadqiqotdagi tayanchi |
|----|---------------|----------------------|------------------------|
| **CASH-01** (`Done`) | «≤3 bosishda tasdiqlaydi» — mexanik bajarilgan | ⛔ **Takrorlanuvchanlik sifati**: 6-qadam xoreografiya to'lovning yozilganini KO'RSATADI va `≤150ms` da keyingi mijozga tayyorlik **o'lchanadi** (G-motion-2). ⛔ Bu talabni kengaytirmaydi — uni **buzilishdan qo'riqlaydi** | §Pitfall 1, §Naqsh 3, §Kod namunalari 2 |
| **RECON-06** (`Done`) | Har rol bosh ekranida bitta ko'rsatkich (`HeadlineCard`) | ⛔ **Ikkita karta qo'shiladi** (`report_view` ostida) va bosh ekran «bo'shlik» dan «javob» ga aylanadi. ⛔ Kassir uchun ekran **o'zgarmaydi** — u ikkala kartani ham ko'rmaydi | §Naqsh 5, §Pitfall 3 |
| **FOUND-04** (`Pending`) | 3 til, bir bosishda almashadi | ⛔ **11 yangi kalit** uchala tilda; ⛔ transliteratsiya **0 defekt** [M-31]; `i18n:check` darvozasi o'zgarmaydi | §Copy mexanikasi |

⛔ **Yangi talab ID qo'shish TAVSIYA ETILMAYDI.** `scripts/check-requirements-sync.mjs` ro'yxat va Traceability jadvalining mosligini mexanik qulflagan [O'LCHANDI: `package.json::requirements:check`]; UI sifat qatlami uchun `UX-01` ochish 9 ta fazaning traceability tarixiga **retroaktiv** savol qo'shardi («oldingi fazalarda UX-01 qayerda edi?»). ⛔ To'g'ri yo'l — ROADMAP Phase 9 ning **SC#1…SC#5** i talab o'rniga ishlaydi, aynan `G-motion-*` darvozalari orqali (SPEC §1.3 shu bog'lanishni allaqachon yozgan).
</phase_requirements>

---

## Loyiha cheklovlari (CLAUDE.md dan)

Rejalashtiruvchi bu bandlarni **qulflangan qaror** darajasida hurmat qiladi:

| # | Direktiv | Manba | 9-fazadagi ta'siri |
|---|----------|-------|--------------------|
| **C-1** | GSD workflow tashqarisida to'g'ridan-to'g'ri repo tahriri **yo'q** | CLAUDE.md § GSD Workflow Enforcement | Barcha o'zgarish `/gsd-execute-phase` orqali |
| **C-2** | `tailwind.config.js` / `.ts` ⛔ **YARATILMAYDI** — Tailwind 4 CSS-first | CLAUDE.md stack + `globals.css:6-7` izohi | Barcha token `@theme` blokida; motion tokenlari ham |
| **C-3** | Next.js 16: `middleware.ts` ⛔ **YO'Q**, `proxy.ts` | CLAUDE.md «What NOT to Use» | ⛔ Tema qatlami `proxy.ts` ga **tegmaydi** (SPEC §17.1) — u `localStorage`, cookie emas |
| **C-4** | TypeScript **5.9.3**, 7.0.2 EMAS | CLAUDE.md | `next.config.ts` da `experimental.useTypeScriptCli` yozilmaydi [KOD tasdiqladi] |
| **C-5** | `react-leaflet` — Hippocratic-2.1, **TAQIQ**; diagramma paketi kerak bo'lsa `recharts` | CLAUDE.md | ⛔ 9-fazada **umuman qo'llanmaydi** — sparkline/donut sof SVG |
| **C-6** | Boshqa paket zarur bo'lsa — UI-SPEC ga **qaytariladi**, jimgina `npm install` **yo'q** | 08-UI-SPEC §3.5 | G-motion-3(d) buni mexanik qiladi |
| **C-7** | Pul `float` emas — butun so'm; `tabular-nums` | CLAUDE.md «What NOT to Use» | Count-up oraliq kadrlari `Math.round()`, `toFixed`/`parseFloat` **yo'q** |
| **C-8** | Javob tili — **uz-Latn** | MEMORY.md | Barcha izoh, xato matni va reja matni uz-Latn'da |

---

## Arxitektura mas'uliyat xaritasi

| Imkoniyat | Birlamchi qatlam | Ikkilamchi qatlam | Sabab |
|-----------|------------------|-------------------|-------|
| Motion token reyestri (`--motion-*`, `--ease-*`) | **CDN/Statik** (`globals.css`, build-time) | — | Tailwind 4 `@theme` build paytida `:root` ga kompilyatsiya qilinadi; runtime qatlami yo'q |
| Global `prefers-reduced-motion` hurmati | **Brauzer/Klient** (CSS `@media`) | — | ⛔ JS qatlamiga chiqarilmaydi: `!important` CSS bloki React yuklanishidan **oldin** kuchga kiradi |
| Tema tanlash va saqlash | **Brauzer/Klient** (`localStorage` + inline skript) | — | ⛔ **Server EMAS** (SPEC §11.2): tema — qurilma xossasi. `proxy.ts` ham, cookie ham, profil maydoni ham **yo'q** |
| Tema token qiymatlari | **CDN/Statik** (`[data-theme]` scope) | — | Sof CSS; komponent kodi bilmaydi |
| 6-qadam xoreografiya (1–5) | **Brauzer/Klient** (DOM + CSS `@keyframes`) | — | `getBoundingClientRect` va DOM manipulyatsiyasi — faqat brauzer |
| 6-qadam, 6-qadam (fokus + tozalash) | **Brauzer/Klient** — ⛔ **ALLAQACHON BOR** [M-9] | — | `collect-session.tsx:281-288`, **TEGILMAYDI** |
| Count-up animatsiyasi | **Brauzer/Klient** (`requestAnimationFrame`) | — | Oxirgi kadr `format.number()` — `next-intl` klient konteksti |
| Sparkline / donut geometriyasi | **Brauzer/Klient** (SVG `stroke-dashoffset`) | **API/Backend** (`GET /reports/revenue`, `GET /occupancy`) | ⛔ Nuqta qiymatlari **serverdan**; klient faqat chizadi. Foiz/yig'indi klientda **hisoblanmaydi** [MEROS: D-03] |
| Ikki dashboard kartasining **huquq darvozasi** | **Brauzer/Klient** (sahifa darajasida shart) | ⛔ **API/Backend** (`require_permission(REPORT_VIEW)`) | ⛔ Klient darvozasi **ko'rinish** uchun; haqiqiy nazorat serverda [MEROS: `rbac.ts` sarlavhasi] |
| `market_day_cleared` bayrog'i (kelajak) | **API/Backend** (`POST /payments` javobi) | Brauzer (konfetti) | ⛔ Klient hosila qila **olmaydi** — SPEC §9.2 uch yo'lni ham yopgan |
| Kontrast o'lchovi | **Build/CI** (`scripts/contrast.test.mjs`) | — | Runtime'da o'lchanmaydi; CSS parse + sof matematika |

---

## Standart stek

### Yadro — ⛔ **YANGI PAKET NOL**

⛔ `frontend/package.json` ning `dependencies` bo'limi **o'zgarmaydi** (SPEC §3.2, G-motion-3(d)). Quyidagi jadval — **mavjud** paketlarning 9-fazadagi roli, tavsiya emas.

| Kutubxona | Versiya | 9-fazadagi roli | Manba |
|-----------|---------|------------------|-------|
| `tailwindcss` + `@tailwindcss/postcss` | **4.3.3** | `@theme` motion/text tokenlari, `[data-theme]` scope, `@keyframes` uyi | [VERIFIED: `package.json` devDependencies] |
| `next` | **16.2.12** | `<html suppressHydrationWarning>` + `<head>` inline tema skripti | [VERIFIED: `package.json`] |
| `react` / `react-dom` | **19.2.8** | `useSyncExternalStore` — tema hook'i uchun (§Naqsh 4) | [VERIFIED: `package.json`] |
| `next-intl` | **4.13.4** | `useFormatter().number()` — count-up ning **oxirgi kadri** | [VERIFIED: `package.json`] |
| `@radix-ui/react-dialog` | **1.1.15** | `data-[state=open]` atributi — dialog scale/fade ilgagi | [VERIFIED: `package.json`] |
| `lucide-react` | **1.27.0** | `Loader2` (5 joyda) — ⛔ **yangi ikonka kerak emas** | [VERIFIED: `package.json`] |
| `@tanstack/react-query` | **5.101.4** | Real-vaqt yangilanish invalidatsiyadan; ⛔ **yangi poll yo'q** | [VERIFIED: `package.json`] |
| `vitest` + `jsdom` + `@testing-library/*` | **4.1.10** / **30.0.1** | G-motion-1(c), G-motion-2, G-motion-6(b), G-motion-7(b) | [VERIFIED: `package.json` devDependencies] |
| `node:test` (o'rnatilgan) | Node 24 | `scripts/*.test.mjs` — CSS/matn parse darvozalari, **nol bog'liqlik** | [VERIFIED: `package.json::test`] |

### ⛔ RAD ETILGAN paketlar — sabab bilan

| Paket | Nega YO'Q | Dalil |
|-------|-----------|-------|
| `motion` / `framer-motion` | Qulflangan 10 ta animatsiyaning **hech biri** uni talab qilmaydi; Lighthouse ≥90 byudjetiga o'lchanadigan zarar | SPEC §3.2 jadvali; [M-14] sketch fayllarida `cdn`/`<script src` — 0 |
| `canvas-confetti` | Konfetti **qurilmaydi**; qurilganda ham 12 ta `<span>` paket talab qilmaydi | SPEC §9.2 |
| `recharts` | Sparkline/donut — sof SVG `stroke-dashoffset`; `recharts` `package.json` da **yo'q** | [O'LCHANDI: `dependencies` ro'yxati] |
| `next-themes` | Uchta tema + `sun` uning ikki holatli modeliga sig'maydi; 20 qatorlik hook kamroq yuza | SPEC §17.2 |
| `culori` / `colorjs.io` (kontrast uchun) | ⛔ **Kerak emas** — oklch→WCAG ~30 qator sof matematika, **shu sessiyada ishlab tekshirildi** (§Kod namunalari 5) | [O'LCHANDI — 13/15 SPEC da'vosi aynan takrorlandi] |
| `postcss` API testda | ⛔ Kerak emas — `@keyframes` va `[data-theme]` bloklarini parse qilish uchun oddiy matn skani yetadi va u **tez** (`gate:fast` byudjeti) | [MEROS: `collect-surface.test.mjs` naqshi] |

**O'rnatish:**
```bash
# ⛔ HECH NARSA. Bu fazada `npm install` BAJARILMAYDI.
# G-motion-3(d) buni mexanik ravishda majburlaydi.
```

---

## Paket qonuniyligi auditi

⛔ **QO'LLANMAYDI — va bu holat mexanik darvoza bilan qulflangan.**

Bu faza **birorta tashqi paket o'rnatmaydi** (SPEC §3.2, [QAROR]; G-motion-3(d) `dependencies` to'plam tengligini talab qiladi). Ya'ni slopsquatting yuzasi **nol**: yangi paket nomi na tadqiqotda, na rejada, na ijroda paydo bo'lmaydi.

| Paket | Registry | Holat | Disposition |
|-------|----------|-------|-------------|
| — | — | Bu fazada yangi paket **yo'q** | N/A |

⛔⛔ **LEKIN darvozaning o'zi bugun noto'g'ri songa tayanadi — bu tadqiqotning eng qimmat topilmasi.**

| Da'vo | O'lchov | Farq |
|-------|---------|------|
| SPEC G-motion-3(d): *«`dependencies` … bugungi **20 paket** ro'yxatiga TENG»* | ⛔ **18 paket** [O'LCHANDI: `node -e "Object.keys(pkg.dependencies).length"` → **18**] | ⛔ **−2** |

To'liq ro'yxat (18): `@hookform/resolvers`, `@radix-ui/react-dialog`, `@radix-ui/react-dropdown-menu`, `@radix-ui/react-select`, `@tanstack/react-query`, `class-variance-authority`, `clsx`, `date-fns`, `lucide-react`, `next`, `next-intl`, `nuqs`, `react`, `react-dom`, `react-hook-form`, `sonner`, `tailwind-merge`, `zod`.

**Tavsiya (rejaga bevosita kiradi):** G-motion-3(d) **sonni qotirmasin** — u `package.json` dan to'plamni **o'qib**, `assert.deepEqual(actual, EXPECTED_SET)` qilsin va `EXPECTED_SET` test faylida **nomma-nom** yozilsin (18 nom). Son (`length === 20`) shakli ikki tomondan yomon: (a) bugun **yolg'on qizil**; (b) paket almashtirilganda (biri chiqib, biri kirganda) **yolg'on yashil** qolardi — bu aynan SPEC §16.2 taqiqlagan «to'plam tengligi emas» shakli.

---

## Arxitektura naqshlari

### Tizim oqim diagrammasi

```
                          ┌──────────────────────────────────────────┐
   BRAUZER HTML PARSE     │  <head> inline skript (bloklovchi)       │
   (React'dan OLDIN)      │  localStorage["sbozor-theme"] → oqiladi  │
                          │  documentElement.dataset.theme = qiymat  │
                          └───────────────────┬──────────────────────┘
                                              │  ⛔ birinchi bo'yashdan OLDIN
                                              ▼
   CSS KASKAD             ┌──────────────────────────────────────────┐
   (build-time)           │ @layer theme { :root { --color-*, ... } } │  ← @theme
                          │ @layer base  { @media reduced-motion {}}  │  ← G-motion-1(a)
                          │ @layer components { @keyframes ... }      │  ← G-motion-3(a,c)
                          │ ⛔ QATLAMSIZ: [data-theme="dark"|"sun"]   │  ← G-motion-4(c)
                          └───────────────────┬──────────────────────┘
                                              │ qatlamsiz > qatlamli (O'LCHANDI)
                                              ▼
   REACT GIDRATATSIYA     ┌──────────────────────────────────────────┐
                          │ <html suppressHydrationWarning>          │
                          │ useTheme(): DOM'dan O'QIYDI, yaratmaydi  │
                          └───────────────────┬──────────────────────┘
                                              │
                ┌─────────────────────────────┼─────────────────────────────┐
                ▼                             ▼                             ▼
   ┌────────────────────────┐  ┌────────────────────────┐  ┌────────────────────────┐
   │  Y-1 KASSIR (eng       │  │  Y-2 DASHBOARD         │  │  Y-4 KOMPONENT JILOSI  │
   │  yuqori ustuvorlik)    │  │                        │  │                        │
   │                        │  │  useRevenueReport(7k)  │  │  Button: active:scale  │
   │  POST /payments        │  │  useOccupancyDay(...)  │  │  Card: hover (desktop) │
   │        │ 2xx           │  │      │ report_view     │  │  Dialog: data-[state]  │
   │        ▼               │  │      ▼  SHART SAHIFADA │  │  Skeleton: shimmer     │
   │  onWritten()           │  │  Skeleton (shimmer)    │  │  LocaleSwitcher: slide │
   │   1. kesh tozalash     │  │      ▼ stagger 60ms    │  │  Forma xatosi: shake   │
   │   2. maydon bo'sh      │  │  count-up (rAF, 600ms) │  └────────────────────────┘
   │   3. method = null     │  │      ▼                 │
   │   4. ⛔ focus()  ◄─────┼──┤  SVG dashoffset 600ms  │
   │   5. toast             │  │      ▼                 │
   │   ══ SHU YERDAN ══     │  │  amber case slide-in   │
   │   6. xoreografiya      │  └────────────────────────┘
   │      (await QILINMAYDI)│
   │      try/catch ichida  │           ⛔ HAR UCHALASI USTIDA:
   │      1..5 qadam        │        @media (prefers-reduced-motion: reduce)
   │      setTimeout →      │        *, ::before, ::after { *-duration: 0.01ms !important }
   │        FAQAT removeChild│       → natija AYNI, faqat yo'l boshqa
   └────────────────────────┘
```

⛔ Diagrammaning yagona muzokarasiz o'qi — **`focus()` va xoreografiya orasidagi chegara**. 1–5-qadamlar `focus()` dan **keyin** boshlanadi va `await` **qilinmaydi**; shu bitta tartib G-motion-2 ning butun ma'nosini ushlab turadi.

### Tavsiya etilgan fayl tuzilishi

```
frontend/src/
├── app/globals.css                         # ⛔ Wave 0 da YOPILADI (§Wave tartibi)
├── app/[locale]/layout.tsx                 # + <head> inline skript, suppressHydrationWarning
├── lib/
│   ├── theme.ts                            # YANGI: reyestr + o'qish/yozish (sof funksiya + hook)
│   ├── use-count-up.ts                     # YANGI: rAF + kubik ease, ~30 qator
│   └── motion.ts                           # YANGI: prefersReducedMotion() — matchMedia GUARD bilan
├── components/
│   ├── shell/theme-toggle.tsx              # YANGI: LocaleSwitcher naqshining aynan nusxasi
│   ├── shell/app-shell.tsx                 # + <ThemeToggle /> LocaleSwitcher YONIDA
│   ├── collect/success-choreography.tsx    # YANGI: 4-qadam FLIP klon, ~90 qator
│   ├── collect/payment-bar.tsx             # 2-qadam: Loader2 → check-draw SVG
│   ├── collect/pending-card.tsx            # 3-qadam halqa; skeleton h-9 → h-11; text-display
│   ├── collect/payment-row.tsx             # 5-qadam: birinchi renderda qo'nish
│   ├── dashboard/revenue-card.tsx          # YANGI: sparkline (sof SVG)
│   ├── dashboard/occupancy-donut.tsx       # YANGI: donut (sof SVG)
│   ├── headline/headline-card.tsx          # text-display SHARTLI (unit==="soum"); skeleton h-11
│   └── ui/{button,card,dialog,skeleton}.tsx
└── ...
frontend/scripts/
├── motion-tokens.test.mjs                  # YANGI — G-motion-1(a,b,d) + G-motion-3
├── theme-tokens.test.mjs                   # YANGI — G-motion-4
├── contrast.test.mjs                       # YANGI — G-motion-5
├── typography.test.mjs                     # YANGI — G-motion-7(a,d,e)
└── collect-surface.test.mjs                # ⛔ MAVJUD — G-motion-6(a): O'ZGARMAYDI
```

⛔ `lib/motion.ts`, `lib/use-count-up.ts`, `lib/theme.ts` — ⛔ **`components/ui/` ga chiqarilmaydi** (SPEC §3.4). `lib/` — `zone-geometry.ts` / `wilson.ts` bilan bir xil naqsh: sof funksiya + tor hook.

---

### Naqsh 1: Tema token-scope — kaskad tartibi ISBOTLANDI

**Nima:** `@theme` `:root` ga yozadi, `[data-theme="…"]` uni **qatlamsiz** bo'lib bosadi.
**Qachon:** Uchala tema uchun; komponent kodi umuman o'zgarmaydi.

⛔⛔ **Bu fazaning eng katta jimgina-nosozlik xavfi edi va u o'lchov bilan yopildi.** `@theme` va `[data-theme]` ikkalasining ham spetsifikligi `(0,1,0)` — ya'ni g'olib **kaskad tartibi** bilan aniqlanadi. Shu sessiyada `@tailwindcss/postcss@4.3.3` bilan haqiqiy kompilyatsiya qilindi:

```css
/* KOMPILYATSIYA CHIQISHI — [O'LCHANDI, 2026-08-17] */
@layer theme, base, components, utilities;
@layer theme {
  :root, :host {
    --ease-out: cubic-bezier(0.22, 1, 0.36, 1);   /* ⛔ Tailwind standarti ALMASHTIRILDI */
    --color-bg: oklch(0.985 0 0);
    --text-display: 2.5rem;
    --text-display--line-height: 1.1;
  }
}
@layer utilities { .bg-bg { background-color: var(--color-bg); } }

[data-theme="dark"] { --color-bg: oklch(0.17 0.005 260); }   /* ⛔ QATLAMSIZ — G'OLIB */
[data-theme="sun"]  { --color-bg: oklch(1 0 0); --font-weight-normal: 500; }
```

⛔ Natija: **qatlamsiz CSS har doim qatlamli CSS'dan ustun** — ya'ni `[data-theme]` bloki `globals.css` da **`@layer` ichiga o'ralmasa**, override kafolatli. ⛔ **Reja bandiga aylanadi:** `[data-theme]` bloklari `@layer base`/`@layer components` **ICHIGA yozilmaydi**.

⛔ **`--font-weight-normal: 500` ham ishlaydi** — o'lchandi: `.font-normal { font-weight: var(--font-weight-normal); }`, ya'ni quyosh rejimining og'irlik ko'tarilishi **komponent kodiga tegmasdan** amalga oshadi (SPEC §11.4 tasdiqlandi).

---

### Naqsh 2: ⛔⛔ `--ease-out` qayta ta'rifi 30 ta mavjud `transition-colors` ga TA'SIR QILMAYDI

**Nima:** Tailwind 4'da bare `transition-*` utilitasi `--ease-out` dan EMAS, `--default-transition-timing-function` dan oziqlanadi.
**Qachon:** Har doim — bu SPEC §4.2 ning yagona to'ldiriladigan bo'shlig'i.

⛔ **[O'LCHANDI]** — kompilyatsiya chiqishi:

```css
:root { --default-transition-duration: 150ms;
        --default-transition-timing-function: cubic-bezier(0.4, 0, 0.2, 1); }  /* ⛔ ESKI EGRI */

.transition-colors {
  transition-timing-function: var(--tw-ease, var(--default-transition-timing-function));
  transition-duration:        var(--tw-duration, var(--default-transition-duration));
}
```

SPEC §4.2 shunday deydi: *«"yumshoq tormoz" butun ilovada **bitta joydan** boshqariladi»*. ⛔ Bu **bugungi shaklda rost emas**: kodbazadagi **30 ta** `transition-colors` [O'LCHANDI] ning birortasida ham `ease-*` utilitasi yo'q [M-3: `ease-*` — 0 marta], ya'ni ular hammasi **eski** `cubic-bezier(0.4, 0, 0.2, 1)` da qoladi.

⛔ **Tuzatish bir qator va u ham o'lchandi:**

```css
@theme {
  --ease-out: cubic-bezier(0.22, 1, 0.36, 1);
  --motion-fast: 150ms;
  /* ⛔ SHU IKKI QATOR — usiz 30 ta `transition-colors` ESKI egrida qoladi. */
  --default-transition-timing-function: var(--ease-out);
  --default-transition-duration: var(--motion-fast);
}
```

⛔ **[O'LCHANDI]** — kompilyatsiya `:root` ga `--default-transition-timing-function: var(--ease-out)` ni **o'zgarishsiz** chiqardi va `.transition-colors` uni oladi. Ya'ni bitta qo'shimcha token e'loni **30 ta faylni** yumshoq egriga o'tkazadi, **birorta komponent tahriri qilmasdan**.

⚠ `--default-transition-duration` **allaqachon 150ms** — ya'ni `--motion-fast` ga bog'lash pikselni o'zgartirmaydi, lekin ikkinchi haqiqat manbaini yo'q qiladi.

---

### Naqsh 3: Bloklamaydigan xoreografiya — `onWritten` ning kengaytmasi

**Nima:** 1–5-qadamlar `onWritten` ning **oxirida**, `focus()` dan keyin, `await`siz, `try/catch` ichida ishga tushadi.
**Qachon:** `POST /payments` 2xx qaytarganda.

⛔ Ulanish nuqtasi aniq va u **allaqachon mavjud**: `collect-session.tsx:265-295` dagi `onWritten` [KOD]. Bugungi tartib — `setWrote` → `dropPendingAfterPayment` → 4 ta `setState` → **`inputRef.current?.focus()`** → `toast.success`. ⛔ Xoreografiya **`toast.success` dan keyin** qo'shiladi.

**Nega aynan oxirida:** SPEC §8.3 sababi mexanik va u tasdiqlandi — `position: fixed` klon `focus()` dan **oldin** DOM'ga qo'shilsa, brauzer scroll-anchoring hisobini qayta qiladi va telefonda fokuslangan input ekrandan chiqib ketishi mumkin.

**Anti-naqsh (⛔ TAQIQ):**
```tsx
// ⛔ NOTO'G'RI — G-motion-2(a)/(b) ni QIZARTIRADI
await runChoreography(...);          // bayram fokusni ushlab turadi
setBusy(true); setTimeout(() => setBusy(false), 700);  // holat animatsiyaga bog'landi
<input disabled={celebrating} />     // klaviatura kirishi yo'qoladi
```

---

### Naqsh 4: Tema hook'i — DOM haqiqat manbai, React nusxa emas

**Nima:** Hook `document.documentElement.dataset.theme` ni **o'qiydi** va `useSyncExternalStore` bilan obuna bo'ladi; o'z `useState` nusxasini **yaratmaydi**.
**Qachon:** `ThemeToggle` va `data-theme` ga qaraydigan har qanday joy (bugun — faqat toggle).

⛔ Sabab SPEC §11.2 da: React holati atributdan ajralib ketsa, tugma «yoqilgan» ko'rinib, ekran o'zgarmasdi. `useSyncExternalStore` ning `getServerSnapshot` i **`"light"`** qaytaradi — SSR'da `document` yo'q va bu HTML'dagi `data-theme="light"` standarti bilan **aynan mos** (gidratatsiya nomuvofiqligi tug'ilmaydi).

⚠ **Muqobil (rad etildi):** `useState(() => localStorage.getItem(...))` — Next.js hujjatining «lazy initializer» naqshi [CITED: `next/dist/docs/01-app/02-guides/preventing-flash-before-hydration.md`]. ⛔ Rad sababi: u **ikkinchi haqiqat manbai** (localStorage) yaratadi va `data-theme` atributi qo'lda o'zgartirilsa (DevTools, kelajakdagi ikkinchi iste'molchi) React bilmay qoladi. DOM'ni yagona manba qilish 08-fazaning «ikkinchi haqiqat manbai» darsiga mos.

---

### Naqsh 5: Ikki dashboard kartasi — huquq sahifada, komponentda EMAS

**Nima:** `hasPermission(roles, "report_view") && <RevenueCard />` — shart **sahifada**; komponent manbasida `hasPermission(` **0 marta**.
**Qachon:** `/dashboard` ga qo'shiladigan ikkala karta.

⛔ Naqshning uyi allaqachon shu faylda: `dashboard/page.tsx:105` `hasPermission(roles, "market_manage") && principal?.marketId ? <MarketStatusCard/> : null` [KOD]. ⛔ Yangi kartalar **aynan shu shaklda** qo'shiladi — ixtiro yo'q.

⛔⛔ **Server tomoni tasdiqlandi:** `GET /occupancy` **ham** `Permission.REPORT_VIEW` ostida [VERIFIED: `services/core-api/app/api/v1/occupancy.py:83,114`], `GET /reports/revenue` ham [VERIFIED: `reports.py:156`]. Ya'ni **bitta** huquq ikkala kartani ham qamraydi va O-03 ning standarti (`report_view`, yangi huquq yo'q) **mexanik ravishda to'g'ri**.

⛔ Kassirda `report_view` **yo'q** [VERIFIED: `rbac.ts` — `billing_collect_view`, `shift_manage` bor; `report_view` alohida] → G-motion-6(b) ning ikkala qatlami (DOM'da yo'q **va** so'rov yuborilmagan) `enabled:` prop'i orqali tabiiy bajariladi.

**Anti-naqsh:**
```tsx
// ⛔ NOTO'G'RI — hidden karta so'rovni BARIBIR yuboradi, summa tarmoq panelida ko'rinadi
<div className={canView ? "" : "hidden"}><RevenueCard /></div>
// ⛔ NOTO'G'RI — shart komponent ICHIDA (G-motion-6(c) qizaradi)
function RevenueCard() { if (!hasPermission(...)) return null; ... }
```

---

### Naqsh 6: Count-up — rAF, oxirgi kadr `format.number()`

**Nima:** `requestAnimationFrame` + kubik ease (`1-(1-p)³`); oraliq kadrlar `Math.round()`; oxirgi kadr **aynan** `format.number(value)`.
**Qachon:** Bosh ko'rsatkich, tushum, bandlik %, qarzdorlik.

⛔ `requestAnimationFrame` jsdom'da **mavjud** [O'LCHANDI: vitest+jsdom probasi → `typeof rAF === "function"`] va `vi.useFakeTimers()` uni **patch qiladi** [O'LCHANDI: `advanceTimersByTime(20)` rAF callback'ini ishga tushirdi]. Ya'ni count-up **testda deterministik o'lchanadi**.

⛔ `value === null` bo'lsa count-up **umuman boshlanmaydi** [MEROS: T-05-04 — «o'lchanmagan son chizilmaydi»]. ⛔ `aria-live` **qo'yilmaydi**; `aria-label` da yakuniy qiymat **darhol** to'liq turadi.

---

### Qochiladigan anti-naqshlar

- **`@theme inline`:** ⛔ **TAQIQ.** `inline` utilitani `var()` o'rniga **qiymatga** kompilyatsiya qiladi va `[data-theme]` override **umuman ishlamaydi**. Bitta so'z butun tema qatlamini jimgina o'ldiradi (G-motion-4(b)).
- **`dark:` Tailwind varianti:** ⛔ 0 marta. `@custom-variant dark` ham **yozilmaydi** — u variantni qonuniylashtirardi.
- **`width`/`height`/`top`/`left` animatsiyasi:** ⛔ Arzon Androidda har kadrda layout hisobi (G-motion-3(a)).
- **`setTimeout` ichida `setState`:** ⛔ Holatni animatsiyaga bog'laydi (G-motion-2(d)). `setTimeout` **faqat** `removeChild` uchun.
- **Sinf nomi orqali `pointer-events` tasdig'i:** ⛔ jsdom'da Tailwind CSS **yuklanmaydi** — `className="pointer-events-none"` bergan elementning `getComputedStyle(...).pointerEvents` qiymati **`"auto"`** [O'LCHANDI]. Klonga **inline uslub** berilishi shart.
- **`prefers-color-scheme` avtomatik ergashish:** ⛔ D-15 falsafasi — qurilma taxminlari jimgina noto'g'ri natija beradi.
- **Jadval saralashda FLIP:** ⛔ 1000 qatorda byudjetni yeydi, foyda nol.

---

## Qo'lda yozilmasin (Don't Hand-Roll)

| Muammo | Qurmang | O'rniga | Sabab |
|--------|---------|---------|-------|
| Reduced-motion har komponentda | `useReducedMotion()` hook'ini har joyga tarqatish | ⛔ **Global CSS `@media` bloki** (`globals.css`) | Bitta manba; React yuklanishidan **oldin** kuchga kiradi; G-motion-1(a) uni parse qiladi |
| Tema o'tishi FOUC | `useEffect` + `setTheme` | ⛔ **`<head>` inline bloklovchi skript** | `useEffect` bo'yashdan **keyin** ishlaydi → miltillash ko'rinadi [CITED: Next.js 16 hujjati] |
| Tema saqlash/o'qish infratuzilmasi | `next-themes` (14 KB) | ⛔ **~20 qatorlik `lib/theme.ts`** | 3 tema + `sun` uning ikki holatli modeliga sig'maydi (SPEC §17.2) |
| Sanoq animatsiyasi | `react-countup` / `motion` | ⛔ **~30 qatorlik `use-count-up.ts`** (rAF) | Oxirgi kadr `next-intl` formatteri bo'lishi **shart** — kutubxona buni bilmaydi |
| Diagramma | `recharts` (~90 KB) | ⛔ **Sof SVG `stroke-dashoffset`** | 7 nuqtali sparkline va 2 sektorli donut uchun grafik kutubxonasi — byudjet isrofi (C-5, C-6) |
| Rang kontrasti matematikasi | `culori` / `colorjs.io` | ⛔ **~30 qatorlik sof funksiya** | **O'LCHANDI**: SPEC ning 15 ta da'vosidan **13 tasi aynan** takrorlandi; §Kod namunalari 5 da tayyor |
| Polygon/geometriya | — | ⛔ Kerak emas | Bu fazada geometriya yo'q |
| CSS parse darvozalarda | `postcss` API'ni testga import qilish | ⛔ **Oddiy matn skani** (`readFileSync` + regex/holat mashinasi) | `gate:fast` byudjeti 200 s; mavjud 18 ta `scripts/*.test.mjs` ning **hech biri** tashqi paketga bog'liq emas |

**Asosiy tushuncha:** Bu fazada har bir «kutubxona kerak» tuyg'usi aslida **10–40 qatorlik sof funksiya**ga aylanadi, va sof funksiya **testda o'lchanadi**, kutubxona esa faqat **ishonch** talab qiladi. Byudjet (Lighthouse ≥90, arzon Android) buni intizom emas, **arifmetika** qiladi.

---

## Umumiy tuzoqlar

### Tuzoq 1: ⛔⛔ jsdom animatsiya haqida HECH NIMA bilmaydi

**Nima buziladi:** G-motion-1(c) va G-motion-2(c) «matchMedia mock'i bilan» yozilib, birinchi ishga tushirishda `TypeError: window.matchMedia is not a function` beradi — yoki yomoni, komponent ichidagi himoyasiz `window.matchMedia(...)` chaqiruvi **butun testni** yiqitadi va sabab «animatsiya» deb o'qiladi.

**Nega:** [O'LCHANDI — vitest 4.1.10 + jsdom 30.0.1, 2026-08-17]

| API | jsdom'da holati | Oqibati |
|-----|------------------|---------|
| `window.matchMedia` | ⛔ **`undefined`** | Komponent GUARD qilishi + test STUB qo'yishi shart |
| `Element.animate()` (WAAPI) | ⛔ **`undefined`** | ⛔ JS-boshqaruvli animatsiya **umuman** yozilmaydi — faqat CSS sinf/`@keyframes` |
| `document.getAnimations()` | ⛔ **`undefined`** | Animatsiya holatini WAAPI orqali tasdiqlab **bo'lmaydi** |
| `getBoundingClientRect()` | ⛔ Hammasi **0** | FLIP masofasi testda 0 — ⛔ **bo'lish** qilinmasin (`NaN` xavfi) |
| Tailwind sinfidan `getComputedStyle` | ⛔ **`"auto"`** (CSS yuklanmaydi) | Tasdiq **inline uslub** yoki **className satri** ustida |
| **inline uslubdan** `getComputedStyle` | ✅ **To'g'ri qaytaradi** (`"none"`) | ⛔ **Bu yagona ishonchli yo'l** |
| `requestAnimationFrame` | ✅ **Mavjud**, `useFakeTimers` uni patch qiladi | Count-up deterministik o'lchanadi |

**Qanday qochish:**
1. `lib/motion.ts` da guard **majburiy** — `stall-map.tsx:46,56` naqshining aynan nusxasi:
   ```ts
   export function prefersReducedMotion(): boolean {
     if (typeof window === "undefined") return false;
     if (typeof window.matchMedia !== "function") return false;   // ⛔ jsdom
     return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
   }
   ```
2. Testda `vi.stubGlobal("matchMedia", …)` [O'LCHANDI — ishladi].
3. Uchayotgan klonga `el.style.pointerEvents = "none"` **inline** beriladi (sinf emas) — shunda G-motion-2(c) o'lchanadi.

**Ogohlantiruvchi belgi:** Test `Cannot read properties of undefined` yoki tasdiq `expected "auto" to be "none"` bersa — sabab animatsiyada emas, **muhitda**.

---

### Tuzoq 2: ⛔⛔ SPEC raqamlarini izohga KO'CHIRISH — G-motion-5(c) ni birinchi kuni qizartiradi

**Nima buziladi:** Ijrochi `globals.css` izohlariga SPEC §5.3 jadvalining raqamlarini ko'chiradi, `contrast.test.mjs` ularni qayta hisoblaydi va **±0.01** talabida uchtasi qizaradi.

**Nega:** [O'LCHANDI — mustaqil kalkulyator, 2026-08-17] SPEC ning 15 ta nisbat da'vosidan **13 tasi aynan** takrorlandi. Ikkitasi farq qildi va sababi topildi:

| Da'vo | SPEC | Hisoblandi (`surface` 0.22 fonida) | Hisoblandi (`surface-muted` 0.26 fonida) |
|-------|------|-------------------------------------|-------------------------------------------|
| dark `success-text` | 5.05 | **5.05** ✅ | 4.53 |
| dark `danger-text` | 5.04 | **5.05** (Δ0.01) | 4.53 |
| dark `text-muted` | 6.98 | **6.98** ✅ | 6.26 |
| ⛔ dark `accent` | 5.02 | **5.12** (Δ**0.10**) | 4.60 |
| ⛔ dark `accent-text` | 5.03 | **5.13** (Δ**0.10**) | 4.60 |
| ⛔ dark `warning-text` | 5.02 | **5.12** (Δ**0.10**) | 4.59 |

⛔ **Ikkita xulosa:**
- **(a)** SPEC §5.3 ning *«Har bir qiymat `surface-muted` da ham ≥4.50:1»* da'vosi **ROST** — lekin marja **0.03–0.10** (4.53…4.60). ⛔ Tokenlarni «bir oz» sozlash bu marjani yo'qotadi.
- **(b)** Uchta xromatik token **+0.10** sistematik farq beradi. Ikkalasi ham AA dan o'tadi, ya'ni **hukm o'zgarmaydi** — lekin **±0.01** solishtiruvi qizil beradi.

**Qanday qochish:** ⛔⛔ **Izohdagi raqam kalkulyatorning CHIQISHI bo'lsin, SPEC ning ko'chirmasi EMAS.** Tartib: (1) `contrast.test.mjs` ning kalkulyatorini yoz, (2) uni bir marta `--print` rejimida yugurt, (3) chiqishini `globals.css` izohlariga qo'y. Shunda G-motion-5(c) **CSS qiymatlari ↔ izohlar** izchilligini o'lchaydi — aynan u nima uchun mavjud bo'lsa.

⚠ **Ikkinchi qatlam:** `--color-accent` (`oklch(0.56 0.19 255)`) va bugungi `--color-accent-text` (`oklch(0.50 0.18 255)`) **sRGB gamutdan tashqarida** [O'LCHANDI: gamma sRGB `-0.05` va `-0.107`]. Gamut xaritalash siyosati **e'lon qilinishi shart**, aks holda ikki implementatsiya ikki xil son beradi. ⛔ **Tanlangan siyosat: gamma fazoda `[0,1]` ga kesish** — u M-19 ning ikkala da'vosini (**1.28** va **4.72**) **aynan** takrorladi.

---

### Tuzoq 3: ⛔ Bandlik donuti bugungi kunda BO'SH bo'ladi

**Nima buziladi:** «Bandlik halqasi» kartasi `useOccupancyDay(bugun)` ni chaqiradi, javob keladi, lekin barcha hisoblagichlar **0** — direktor bo'sh halqani ko'radi va «tizim ishlamayapti» deb xulosa qiladi.

**Nega:** [VERIFIED: `occupancy.py:114` docstring so'zma-so'z] — *«`day` BERILMASA BUGUNGI KUN. Bugungi kunning materializatsiyasi ERTASI kuni 03:40 da bo'ladi (`worker.py::DAY_CLOSE_CRON`), ya'ni bugungi javob odatda BO'SH bo'ladi va bu KUTILGAN»*.

**Qanday qochish:** Karta **oxirgi yopilgan kun** ni so'rasin (kecha) va sarlavhasida kunni **ko'rsatsin**; yoki bo'sh javobda `dashboard.occupancyEmpty` (`Bandlik hali o'lchanmagan`) chizsin — bu kalit SPEC §14.1 da **allaqachon** e'lon qilingan. ⛔ Nol bilan halqa chizish **TAQIQ** [MEROS: T-05-04 — o'lchanmagan son chizilmaydi].

**Ogohlantiruvchi belgi:** Halqa doim to'liq bo'sh; `occupancy.noFutureDays` matni yodga tushadi.

---

### Tuzoq 4: ⛔ `useOccupancyDay` avtomatik poll'ni O'ZI BILAN OLIB KELADI

**Nima buziladi:** Dashboard'ga `useOccupancyDay` ulanadi va u SPEC §10.6 ning *«Avtomatik poll QO'SHILMAYDI»* qoidasini **jimgina** buzadi.

**Nega:** [KOD: `occupancy-queries.ts:117-122,151`] `refetchInterval: () => occupancyPollInterval({ day, todayIso })` — `day === todayIso` bo'lsa poll **yoqiladi**.

**Qanday qochish:** Karta **kecha**ni so'rasa poll o'zi o'chadi (`occupancyPollInterval` `false` qaytaradi) — ya'ni Tuzoq 3 ning yechimi bu tuzoqni ham yopadi. ⛔ Muqobil («`refetchInterval: false` ni prop bilan majburlash») — rad etiladi: u mavjud hook'ning kontraktini kengaytirardi.

⚠ **Uchinchi ta'sir:** `occupancyDaySchema.items` — **butun rastalar ro'yxati** (1000 gacha element) [KOD: `api-types.ts:1895`]. Ikki sonli donut uchun bu og'ir yuk. ⛔ Yangi endpoint **qo'shilmaydi** (SPEC §14.3: «yangi so'rov qo'shilmaydi»); to'g'ri qaror — mavjud javobni ishlatish va uni `select:` bilan ikki songa **qisqartirish** (react-query `select` keshga tegmaydi, faqat komponentga beriladigan shaklni toraytiradi).

---

### Tuzoq 5: ⛔ `dependencies` sanog'i — 18, SPEC 20 deydi

Yuqorida §Paket qonuniyligi auditida to'liq. **Reja bandiga aylanadi:** G-motion-3(d) **to'plam tengligi** bilan yozilsin, son bilan emas.

---

### Tuzoq 6: `dark:` skanini `grep` bilan yozish — 2 ta yolg'on-ijobiy

**Nima buziladi:** G-motion-4(a) `grep "dark:"` bilan yoziladi va **bugundan** qizil bo'ladi.

**Nega:** [O'LCHANDI] `dark:` naqshi mahsulot fayllarida **2 marta** uchraydi va ikkalasi ham **obyekt kaliti**, Tailwind varianti emas:
- `components/snapshots/capture-cell.tsx:106` → `dark: {` (`light_mode` gistogrammasi)
- `lib/api-types.ts:1400` → `dark: z.number().int()`

**Qanday qochish:** Skan `className=` / `cn(` argumentlari bilan **chegaralansin** — SPEC §16.4 G-motion-4(a) buni allaqachon talab qiladi va yolg'on-ijobiy manbasini **nomma-nom** yozgan. ⛔ Bu bandning rejaga so'zma-so'z ko'chirilishi shart.

---

### Tuzoq 7: ⛔⛔ Sabotaj modulni YIG'ILMAYDIGAN qilib qo'yish

**Nima buziladi:** Sabotaj (masalan `@keyframes` ga `height: 0 → 100%` qo'shish) faylni sintaksis xatosi bilan buzadi, test qizaradi va ijrochi «sabotaj ushlandi» deb yozadi — holbuki qizargani **yig'ilish**, mezon emas.

**Nega:** [MEROS: STATE.md `08-20` S-5 darsi, so'zma-so'z] — *«Sabotaj modulni IMPORT QILINADIGAN holda qoldirishi shart, aks holda "qo'shnilari yashil qoladimi?" degan yarim o'lchanmay qoladi»*.

**Qanday qochish:** Har sabotajdan keyin **ikki** o'lchov: (a) nishon test **qizardi**, (b) qo'shni testlar **yashil qoldi**. ⛔ (b) yozilmagan sabotaj — **bajarilmagan** sabotaj.

---

### Tuzoq 8: ⛔ Reja matni ↔ klient kontrakti ziddiyati — kontrakt yutadi

**Nima buziladi:** Reja «serverga `market_day_cleared` maydonini qo'sh» deydi, server qo'shadi, klient **parse'da yiqiladi**.

**Nega:** [VERIFIED: `payment-queries.ts:119`] `paymentResponseSchema = z.strictObject({...})` — **8 kalit**, qat'iy. Loyihada `strictObject` **20 marta** ishlatiladi [O'LCHANDI]. ⛔ Ya'ni har qanday javob maydoni **ikki tomonlama, kelishilgan** o'zgarish; server yolg'iz qo'sha olmaydi.

**Qanday qochish:** SPEC §9 ni hurmat qilib, `market_day_cleared` **shu fazada qurilmaydi**. ⛔ Agar keyingi faza uni ochsa — server va klient **bitta commitda** o'zgaradi.

⛔ **Bonus topilma (rejaga foydali):** tetikning ma'lumot manbai **allaqachon mavjud** — `billing_repo.PendingMarket.pending_stall_count` [VERIFIED: `billing_repo.py:1340`], `billing.py:277` da chiqariladi. Ya'ni `market_day_cleared` **migratsiya talab qilmaydi** (hosila qiymat, saqlanadigan ustun emas); u `create_payment` ichida `pending_projection(...)` ni bir marta chaqirish bilan hisoblanadi. ⛔ **Audit ta'siri: nol** — mantiqiy hosila qiymat yozuv emas, `audit_log` ga tushmaydi. Bu **kelajak fazasi uchun** yozib qo'yildi.

---

### Tuzoq 9: `motion-reduce:animate-none` TRANZISIYANI to'xtatmaydi

**Nima buziladi:** Ijrochi `motion-reduce:animate-none` ni yetarli deb hisoblaydi va `transition` bilan qurilgan effektlar reduced-motion'da **ishlashda davom etadi**.

**Nega:** [O'LCHANDI — kompilyatsiya chiqishi]
```css
@media (prefers-reduced-motion: reduce) { .motion-reduce\:animate-none { animation: none; } }
```
⛔ `transition-duration` ga **tegmaydi**.

**Qanday qochish:** Global `@media` bloki (G-motion-1(a)) **ikkalasini ham** `!important` bilan `0.01ms` ga tushiradi. ⛔ `!important` deklaratsiyalari qatlam tartibidan **qat'i nazar** oddiy deklaratsiyalardan ustun — ya'ni blok `@layer base` ichida bo'lsa ham ishlaydi. `motion-reduce:` utilitalari esa **ikkinchi** qatlam (SPEC G-motion-1(b) ularning qamrovini alohida o'lchaydi).

---

### Tuzoq 10: `text-display` skeleton geometriyasi — CLS ning yagona mexanik o'lchovi

**Nima buziladi:** `text-2xl` (30px qator qutisi) `text-display` (44px) ga almashadi, skeleton esa `h-8`/`h-9` da qoladi → **8–12px CLS**.

**Nega:** [KOD tasdiqladi] `headline-card.tsx:110` `<Skeleton className="h-8 w-28" />`; `pending-card.tsx:183` `<Skeleton className="h-9 w-40" />`. Ikkalasi ham `h-11` (44px) bo'lishi kerak — `headline-card` da ⛔ **faqat `unit === "soum"` shoxida**.

**Ogohlantiruvchi belgi:** Skeleton kontentga almashganda karta balandligi «sakraydi».

---

## Kod namunalari

### 1. Motion + tema tokenlari (`globals.css` — Wave 0)

```css
/* Manba: sketch 001-B/002-B [QULF]; kompilyatsiya O'LCHANDI 2026-08-17 */
@theme {
  /* ---- Harakat davomiyligi — YOPIQ REYESTR (3 qiymat) --------------- */
  --motion-fast: 150ms;
  --motion-base: 250ms;
  --motion-slow: 400ms;

  /* ---- Ease egri chiziqlari ---------------------------------------- */
  --ease-out: cubic-bezier(0.22, 1, 0.36, 1);
  --ease-spring: cubic-bezier(0.34, 1.56, 0.64, 1);

  /* ⛔⛔ USIZ 30 TA MAVJUD `transition-colors` ESKI EGRIDA QOLADI.
   * Tailwind 4 bare `transition-*` ni `--default-transition-*` dan
   * oziqlantiradi, `--ease-out` dan EMAS [O'LCHANDI: 09-RESEARCH Naqsh 2]. */
  --default-transition-timing-function: var(--ease-out);
  --default-transition-duration: var(--motion-fast);

  /* ---- Pul roli ----------------------------------------------------- */
  --text-display: 2.5rem;
  --text-display--line-height: 1.1;
}

@layer base {
  /* ⛔ G-motion-1(a). `!important` qatlam tartibidan QAT'I NAZAR ustun. */
  @media (prefers-reduced-motion: reduce) {
    *, *::before, *::after {
      animation-duration: 0.01ms !important;
      animation-iteration-count: 1 !important;
      transition-duration: 0.01ms !important;
      scroll-behavior: auto !important;
    }
  }
  :where(table, .money, [data-numeric]) { font-variant-numeric: tabular-nums; }
}

/* ⛔⛔ QATLAMSIZ — `@layer` ICHIGA YOZILMAYDI.
 * Qatlamsiz CSS qatlamli CSS'dan ustun; @theme esa `@layer theme` da
 * [O'LCHANDI: @tailwindcss/postcss@4.3.3 kompilyatsiyasi]. */
[data-theme="dark"] { /* §5.3 ning TO'LIQ ro'yxati — `*-text` oilasi HAM */ }
[data-theme="sun"]  { --font-weight-normal: 500; --font-weight-semibold: 700; /* … */ }
```

### 2. Bloklamaydigan xoreografiya ulanishi (`collect-session.tsx`)

```tsx
// Manba: mavjud `onWritten` [KOD: collect-session.tsx:265-295] ning kengaytmasi
const onWritten = useCallback((record: PaymentRecord) => {
  setWrote(record);
  dropPendingAfterPayment(client, marketId);
  setSubmittedCode(""); setDraft(""); setMethod(null);
  setExtraAmount(null); setOverride(null);

  inputRef.current?.focus();                         // ⛔ 6-QADAM — BIRINCHI
  toast.success(`${t("collect.written")} · …`);

  // ⛔⛔ 1–5-QADAM SHU YERDAN. `await` YO'Q. `try/catch` MAJBURIY:
  //     bayram yiqilsa ham to'lov qatori va fokus JOYIDA qoladi (G-motion-2(e)).
  try {
    flyAmountToList({ from: amountRef.current, to: listRef.current });
  } catch { /* bayram — bezak; oqimni to'xtatmaydi */ }
}, [client, marketId, money, t]);
```

### 3. FLIP klon — jsdom'da o'lchanadigan shaklda

```tsx
// ⛔ `pointer-events` INLINE beriladi: jsdom Tailwind sinfini KO'RMAYDI
//    [O'LCHANDI: class-only computed pointerEvents === "auto"]
export function flyAmountToList(opts: { from: HTMLElement | null; to: HTMLElement | null }) {
  if (prefersReducedMotion()) return;                    // ⛔ klon YARATILMAYDI
  const { from, to } = opts;
  if (from === null || to === null) return;

  const a = from.getBoundingClientRect();
  const b = to.getBoundingClientRect();

  const clone = from.cloneNode(true) as HTMLElement;
  clone.setAttribute("aria-hidden", "true");             // ⛔ G-motion-2(c)
  clone.style.pointerEvents = "none";                    // ⛔ G-motion-2(c)
  clone.style.position = "fixed";                        // ⛔ oqimdan tashqarida
  clone.style.left = `${a.left}px`;
  clone.style.top = `${a.top}px`;
  clone.style.willChange = "transform";
  clone.style.transition =
    "transform var(--motion-slow) var(--ease-out), opacity var(--motion-slow) var(--ease-out)";
  document.body.appendChild(clone);

  requestAnimationFrame(() => {
    clone.style.transform = `translate(${b.left - a.left}px, ${b.top - a.top}px) scale(0.85)`;
    clone.style.opacity = "0";
  });

  // ⛔ `setTimeout` FAQAT TOZALASH — `setState` YO'Q (G-motion-2(d), AST bilan o'lchanadi)
  window.setTimeout(() => clone.remove(), 450);
}
```

### 4. Reduced-motion guard (`lib/motion.ts`)

```ts
// ⛔ jsdom'da `window.matchMedia` UMUMAN YO'Q [O'LCHANDI: jsdom 30.0.1]
// Naqsh manbai: `components/stalls/stall-map.tsx:46,56` — ixtiro emas.
export function prefersReducedMotion(): boolean {
  if (typeof window === "undefined") return false;
  if (typeof window.matchMedia !== "function") return false;
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}
```

Testda:
```ts
vi.stubGlobal("matchMedia", (q: string) => ({
  matches: q.includes("reduce"), media: q,
  addEventListener() {}, removeEventListener() {},
  addListener() {}, removeListener() {},
  onchange: null, dispatchEvent: () => false,
}));                                        // [O'LCHANDI: ishladi]
```

### 5. ⛔ Kontrast kalkulyatori — TEKSHIRILGAN, nol bog'liqlik

```js
/* OKLCH → WCAG 2.x kontrast nisbati. Bog'liqlik YO'Q.
 * [O'LCHANDI 2026-08-17]: 09-UI-SPEC ning 15 ta da'vosidan 13 tasi AYNAN
 * takrorlandi (M-16 ning to'rttasi, M-17 ning uchtasi, M-19/M-20 ning
 * to'rttasi, M-18 ning ikkitasi). Qolgan uchtasi — dark rejimning
 * xromatik tokenlari — +0.10 farq beradi; sabab 09-RESEARCH Tuzoq 2 da. */
function oklchToLinear(L, C, Hdeg) {
  const h = (Hdeg * Math.PI) / 180, a = C * Math.cos(h), b = C * Math.sin(h);
  const l = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3;
  const m = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3;
  const s = (L - 0.0894841775 * a - 1.2914855480 * b) ** 3;
  return [ 4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
          -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
          -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s ];
}
const enc = (v) => (v <= 0.0031308 ? 12.92 * v : 1.055 * Math.pow(v, 1 / 2.4) - 0.055);
const dec = (v) => (v <= 0.04045 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4));

/* ⛔ GAMUT SIYOSATI E'LON QILINADI: gamma fazoda [0,1] ga kesiladi.
 *   `--color-accent` (0.56 0.19 255) sRGB gamutdan TASHQARIDA [O'LCHANDI],
 *   ya'ni siyosatsiz ikki implementatsiya ikki xil son berardi.
 *   Bu siyosat M-19 ning 1.28 va 4.72 ni AYNAN qaytardi. */
function relativeLuminance(c) {
  const lin = oklchToLinear(...c).map(enc).map((v) => Math.min(1, Math.max(0, v))).map(dec);
  return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2];
}
export function contrastRatio(fg, bg) {
  const a = relativeLuminance(fg), b = relativeLuminance(bg);
  const hi = Math.max(a, b), lo = Math.min(a, b);
  return (hi + 0.05) / (lo + 0.05);
}
```

O'lchov natijasi (SPEC da'vosi ↔ hisoblangan):

| Juftlik | SPEC | Hisoblandi | Holat |
|---------|------|------------|-------|
| `text-muted`/`surface-muted` | 4.81 | **4.81** | ✅ |
| `border-ui`/`surface` · `/bg` · `/surface-muted` | 3.64 · 3.49 · 3.32 | **3.64 · 3.49 · 3.32** | ✅ |
| `text-muted`/iliq `bg` | 5.06 | **5.06** | ✅ |
| `text`/iliq `bg` | 17.15 | **17.16** | ✅ (Δ0.01) |
| `text-muted`/iliq `surface-muted` | 4.84 | **4.84** | ✅ |
| ⛔ `accent-text`/`accent` (M-19 NUQSON) | 1.28 | **1.28** | ✅ |
| `accent-fg`/`accent` (M-19 tuzatish) | 4.72 | **4.72** | ✅ |
| `success-fg` oq/`success` (M-20) | 3.27 | **3.27** | ✅ |
| `success-fg` quyuq/`success` | 5.48 | **5.48** | ✅ |
| dark `text`/`surface` | 14.96 | **14.96** | ✅ |
| sun `text`/`bg` | 21.00 | **21.00** | ✅ |
| ⛔ dark `accent`/`accent-text`/`warning-text` | 5.02/5.03/5.02 | **5.12/5.13/5.12** | ⚠ Δ0.10 |

### 6. Tema — inline skript + `<html>` (Next.js 16 rasmiy naqshi)

```tsx
// Manba: next/dist/docs/01-app/02-guides/preventing-flash-before-hydration.md
// ⛔ CSP tekshirildi: loyihada CSP sarlavhasi YO'Q [O'LCHANDI] → `unsafe-inline` muammosi yo'q.
<html lang={locale} className="h-full" data-theme="light" suppressHydrationWarning>
  <head>
    <script
      dangerouslySetInnerHTML={{
        __html: `(function(){try{var t=localStorage.getItem("sbozor-theme");` +
                `if(t==="dark"||t==="sun"||t==="light")` +
                `document.documentElement.setAttribute("data-theme",t)}catch(e){}})()`,
      }}
    />
  </head>
  <body className="flex min-h-full flex-col">…</body>
</html>
```

⛔ Skript **reyestr bilan tekshiradi** (`"dark"|"sun"|"light"`) — `localStorage` dagi ixtiyoriy satr `data-theme` ga to'g'ridan-to'g'ri o'tmaydi. ⛔ `try/catch` — `localStorage` bloklangan brauzerlar uchun (hujjat shuni talab qiladi).

---

## Runtime holat inventarizatsiyasi

> Bu **rename/refactor fazasi emas**, lekin faza **yangi runtime holat** kiritadi — shuning uchun qisqartirilgan shaklda.

| Kategoriya | Topilgan | Kerakli amal |
|------------|----------|--------------|
| Saqlangan ma'lumot | ⛔ **`localStorage["sbozor-theme"]`** — YANGI kalit, uchta qiymat (`light`/`dark`/`sun`) | Kod: reyestr bilan validatsiya (§Kod namunalari 6). ⛔ **Migratsiya YO'Q** — kalit hali mavjud emas |
| Jonli servis konfiguratsiyasi | **Yo'q** — bu faza server konfiguratsiyasiga tegmaydi (yangi endpoint yo'q, SPEC §14.3) | Yo'q |
| OS-ro'yxatdagi holat | **Yo'q** — verified: faza faqat `frontend/` ga tegadi | Yo'q |
| Sirlar / env o'zgaruvchilari | **Yo'q** — tema `localStorage` da, serverda emas (SPEC §11.2); yangi env kaliti yo'q | Yo'q |
| Build artefaktlari | ⛔ **`messages/uz-Cyrl.json`** — 11 yangi kalitdan **generatsiya** qilinadi | `npm --prefix frontend run i18n:gen`, so'ng `i18n:check`. ⛔ Qo'lda tahrirlanmaydi; `uz-Cyrl.overrides.json` **tegilmaydi** [M-31: 0 defekt] |
| Server profili | ⛔ **Ataylab TEGILMAYDI** — tema qurilma xossasi, til esa profilda (D-15) | Yo'q |

---

## Copy mexanikasi (i18n darvozasi)

| Mexanizm | Holat | 9-fazada |
|----------|-------|-----------|
| `messages/uz-Latn.json` | Manba, **1362 kalit** [M-30] | +11 kalit (`theme.*` 4 ta, `dashboard.*` 7 ta) |
| `messages/uz-Cyrl.json` | ⛔ **Generatsiya** (`gen-cyrillic.mjs`) | Avtomatik; qo'l tegmaydi |
| `messages/uz-Cyrl.overrides.json` | Yagona qo'lda tahrirlanadigan kirill fayli | ⛔ **TEGILMAYDI** [M-31: 17 nomzoddan 0 defekt] |
| `messages/ru.json` | Qo'lda | +11 kalit (SPEC §14.1 da tayyor) |
| `i18n:check` | Kalit-parity + ICU-parity | ⛔ O'zgarmaydi; yangi kalitlar undan **o'tadi** |

⚠ **`gen-cyrillic.test.mjs` `[A-Za-z]+[0-9]` naqshini `messages/*.json` da UMUMAN taqiqlaydi** [KOD: `uz-Cyrl.overrides.json::_comment_alphanumeric`]. SPEC §14.1 ning 11 kalitida bunday token **yo'q** (`So'nggi 7 kun` — `7` alohida token) ✅. ⛔ Yangi copy yozilsa (masalan `7 kunlik`) — bu taqiq esga olinsin.

---

## Zamonaviy holat

| Eski yondashuv | Joriy yondashuv | Qachon o'zgardi | Ma'nosi |
|----------------|------------------|------------------|---------|
| `tailwind.config.js` `theme.extend` | ⛔ **CSS-first `@theme`** | Tailwind 4.0 (2025) | Motion tokenlari `globals.css` da; config fayli **taqiq** (C-2) |
| `.dark` class + `dark:` variant | ⛔ **`[data-theme]` token-scope** | Bu faza — 3 tema, 2 emas | `dark:` **0 marta**; komponent kodi bilmaydi |
| `duration-150` (sehrli son) | ⛔ **`duration-(--motion-fast)`** | Tailwind 4 `(--var)` sintaksisi | [O'LCHANDI: kompilyatsiya qiladi] |
| `middleware.ts` | ⛔ **`proxy.ts`** (Node runtime) | Next.js 16 | ⛔ 9-faza unga **tegmaydi** — tema `localStorage` da |
| `useEffect` + `setTheme` (FOUC) | ⛔ **`<head>` inline bloklovchi skript** | Next.js rasmiy tavsiyasi | Birinchi bo'yashdan **oldin** |
| Grafik kutubxonasi (`recharts`) | ⛔ **Sof SVG `stroke-dashoffset`** | Bu faza | 0 KB o'sish |
| WAAPI (`Element.animate`) | ⛔ **CSS `@keyframes` + sinf** | — | jsdom WAAPI'ni **bermaydi** [O'LCHANDI] → testda o'lchab bo'lmaydi |

**Eskirgan / ishlatilmaydi:**
- `next-themes` — 3 tema modeliga sig'maydi
- `animate-pulse` (skeleton) → **shimmer** (`background-position`)
- `passlib`/`python-jose` naqshidagi «tutorialda bor» yechimlar — bu fazada ekvivalent: `motion` kutubxonasi «hamma ishlatadi» degani uchun qo'shilmaydi

---

## Muhit mavjudligi

| Bog'liqlik | Talab qiladi | Mavjud | Versiya | Zaxira |
|------------|--------------|--------|---------|--------|
| Node.js | `next build`, `node --test`, `vitest` | ✓ | ≥20.9 (`engines`); CLAUDE.md 24.18 LTS | — |
| `frontend/node_modules` | Butun frontend zanjiri | ✓ | `vitest 4.1.10`, `jsdom 30.0.1`, `tailwindcss 4.3.3` tasdiqlandi | ⛔ **Zanjir boshida `npm ci` tekshiruvi** [MEROS: STATE.md — 8-fazada bo'shligi **29-daqiqada** ko'ringan] |
| `@tailwindcss/postcss` | `globals.css` kompilyatsiyasi | ✓ | 4.3.3 — shu sessiyada **haqiqiy kompilyatsiya** bajarildi | — |
| Docker Compose (backend) | `npm run gate` ning backend yarmi | ✓ | Loyiha bo'ylab ishlatiladi | 9-faza backend'ga **tegmaydi** → `gate:fast` yetarli |
| Headless Chrome / Lighthouse | Performance ≥90 o'lchovi | ✗ | — | ⛔ **09-HUMAN-UAT.md** (SPEC §16.6) — egasi ijrochi, natija **son bilan** |
| Real qurilma (arzon Android) | 60fps, CLS <0.05 | ✗ | — | ⛔ **09-HUMAN-UAT.md**; mexanik proksi — G-motion-3(a) va G-motion-7(c) |
| `slopcheck` | Paket qonuniyligi | — | Kerak emas: **0 yangi paket** | — |

**Zaxirasiz yetishmovchilik:** yo'q — ikkala yetishmayotgan bog'liqlik ham HUMAN-UAT ga o'tadi va SPEC §16.6 ularni **ochiq** qayd etgan.

---

## Validatsiya arxitekturasi

### Test freymvorki

| Xossa | Qiymat |
|-------|--------|
| Freymvork (komponent) | **vitest 4.1.10** + jsdom 30.0.1 + Testing Library |
| Freymvork (sof funksiya / matn-CSS skani) | **`node --test`** (Node o'rnatilgan) — ⛔ **nol bog'liqlik** |
| Konfiguratsiya | `frontend/vitest.config.ts` (`include: ["src/**/*.test.tsx"]`), `frontend/vitest.setup.ts` |
| Tez ishga tushirish | `npm run gate:fast` → `npm run test:fast && npm --prefix frontend test` — byudjet **200 s** (oxirgi o'lchov 155/152 s) |
| To'liq to'plam | `npm run gate` — byudjet **2300 s** (oxirgi o'lchov 1909/1842 s) |
| Bugungi hajm | **94** ta `*.test.tsx` fayli · **18** ta `scripts/*.test.mjs` · vitest ~**1110** test [MEROS: STATE.md 08-20] |

### Faza talablari → test xaritasi

| Mezon | Xulq | Test turi | Avtomatik buyruq | Fayl bormi? |
|-------|------|-----------|-------------------|-------------|
| **SC#1** / G-motion-2 | Kassir inputi 150ms da tayyor; klon `pointer-events:none` + `aria-hidden`; `setTimeout` da `setState` yo'q; xoreografiya yiqilsa ham qator+fokus joyida | komponent + AST | `npx vitest run src/components/collect/success-choreography.test.tsx src/components/collect/collect-session.test.tsx` | ❌ Wave 0 |
| **SC#1** / xoreografiya ijrosi | 1–5-qadam ulanish nuqtalari | komponent | `npx vitest run src/components/collect/` | ⚠ qisman (`payment-bar.test.tsx`, `pending-card.test.tsx`, `collect-session.test.tsx` **bor**) |
| **SC#2** | Dashboard skeleton→stagger→count-up; sparkline/donut; kassirda **yo'q** | komponent | `npx vitest run src/app/**/dashboard src/components/dashboard/` | ❌ Wave 0 |
| **SC#3** / G-motion-4 | `dark:` 0; `@theme inline` 0; uchala scope token to'plami teng; `suppressHydrationWarning` + inline skript bor | matn/CSS skani | `node --test scripts/theme-tokens.test.mjs` | ❌ Wave 0 |
| **SC#4** / G-motion-1 | Global `@media` bloki `animation-duration` **va** `transition-duration` ni ≤0.01ms qiladi; `animate-*` ↔ `motion-reduce:` juftligi ≥5; reduced'da klon **yaratilmaydi**; `confetti` 0 | CSS skani + komponent | `node --test scripts/motion-tokens.test.mjs` + `npx vitest run src/components/collect/success-choreography.test.tsx` | ❌ Wave 0 |
| **SC#5** / G-motion-3 | `@keyframes` xossalari to'plam tengligi (≥6 blok); `duration-<raqam>` 0; `dependencies` **to'plam tengligi** (18 nom) | CSS/JSON skani | `node --test scripts/motion-tokens.test.mjs` | ❌ Wave 0 |
| **SC#3** / G-motion-5 | `oklch` parse + WCAG hisob, ≥12 juftlik × 3 tema; izohdagi son ±0.01; `bg-accent`+`text-accent-text` 0 | CSS skani | `node --test scripts/contrast.test.mjs` | ❌ Wave 0 |
| **Chegara** / G-motion-6 | Kassir yuzasida yig'indi yo'q (**mavjud**); dashboard kassir sessiyasida **so'rov yubormaydi**; bayram copy'si 0 | matn skani + komponent | `node --test scripts/collect-surface.test.mjs` (**mavjud, O'ZGARMAYDI**) + `npx vitest run src/app/**/dashboard` | ⚠ yarmi bor |
| **L-9** / G-motion-7 | `text-display` ≤2 faylda; `headline-card` da **shartli**; skeleton `h-N` ↔ kontent qutisi; `text-base ≤7`, `text-xl ≤4`, `font-medium ≤21` | matn skani + komponent | `node --test scripts/typography.test.mjs` + `npx vitest run src/components/headline/` | ❌ Wave 0 |

### Namuna olish darajasi

- **Har task commiti:** `npm run gate:fast` — byudjet **200 s** (bugungi 155 s, zaxira 45 s)
- **Har wave merge:** `npm --prefix frontend test` (`node --test scripts/*.test.mjs && vitest run`) + `npm --prefix frontend run i18n:check`
- **Faza darvozasi:** `npm run gate` — byudjet **2300 s**, `/gsd-verify-work` dan oldin yashil

⚠ **Byudjet risk baholovi:** SPEC §16.7 taxmini — vitest **+~55 test**, 4 yangi `scripts/*.test.mjs` (sof matn/CSS parse) → **~40–60 s**. `gate:fast` zaxirasi **45 s** [MEROS: 08-20 o'lchovi]. ⛔ **Ya'ni zaxira taxmin bilan deyarli teng.** Reja bandiga aylanadi: 4 ta yangi `scripts/*.test.mjs` **sof matn skani** bo'lsin (`postcss` import qilmasin — u ~1 s qo'shardi), va faza oxirida byudjet **qayta o'lchansin** (05-15 W0-13 protokoli: tinch xost, uch o'lchov, eng yomon × 1,20).

### Wave 0 bo'shliqlari

- [ ] `frontend/scripts/motion-tokens.test.mjs` — G-motion-1(a,b,d) + G-motion-3(a,b,c,d)
- [ ] `frontend/scripts/theme-tokens.test.mjs` — G-motion-4(a–e)
- [ ] `frontend/scripts/contrast.test.mjs` — G-motion-5(a–d) + `--print` rejimi (izohlarni generatsiya qilish uchun)
- [ ] `frontend/scripts/typography.test.mjs` — G-motion-7(a,d,e)
- [ ] `src/components/collect/success-choreography.test.tsx` — G-motion-1(c) + G-motion-2(a–e)
- [ ] `src/app/[locale]/(app)/dashboard/page.test.tsx` — G-motion-6(b)
- [ ] ⛔ **`vitest.setup.ts` ga `matchMedia` stubi QO'SHILMAYDI** — u global bo'lsa har test «reduced-motion o'chirilgan» deb ishlaydi va G-motion-1(c) ning teskari shoxi **o'lchanmay qolardi**. Stub **har testda alohida**
- [ ] Freymvork o'rnatish: ⛔ **kerak emas** — vitest, jsdom, Testing Library, `node --test` hammasi mavjud

---

## Validation Architecture

> ⛔ Bu bo'lim `09-VALIDATION.md` ning **manbai** (`scripts/check-validation-signoff.mjs`
> shartlari bo'yicha). Yuqoridagi «Validatsiya arxitekturasi» bo'limi bilan **bir xil
> faktlarga** tayanadi; farq — bu yerda `human_only_verifications` va
> `automated_replacements` **shakl to'liqligi** bilan beriladi.
> ⚠ Ziddiyat bo'lsa — **09-UI-SPEC.md §16 ustun** (u `approved`).

### Test Framework

| Property | Value |
|----------|-------|
| **Framework (birlamchi)** | **vitest 4.1.10** + jsdom 30.0.1 + `@testing-library/react` 16.3.2 — React komponent qatlami (`src/**/*.test.tsx`) |
| **Framework (ikkilamchi)** | **`node --test`** (Node o'rnatilgan, ⛔ **nol bog'liqlik**) — CSS/JSON/matn skan darvozalari (`frontend/scripts/*.test.mjs`) |
| **Framework (uchlamchi)** | **pytest 9.1.1** (`docker compose --profile test run --rm tests`) — ⛔ **bu fazada ISHLATILMAYDI**: yangi endpoint yo'q (SPEC §14.3). Zaxirada `market_day_cleared` **kelajak** fazasi uchun turadi (§Tuzoq 8) |
| Config — komponent | `frontend/vitest.config.ts` (`environment: "jsdom"`, `include: ["src/**/*.test.tsx"]`, alias `@` → `./src`) |
| Config — global setup | `frontend/vitest.setup.ts` (`@testing-library/jest-dom/vitest` + `afterEach(cleanup)`) — ⛔ **`matchMedia` stubi bu yerga QO'YILMAYDI** (sabab: Wave 0 bo'shliqlari) |
| Config — skript darvozalari | Config **yo'q va kerak emas** — `node --test scripts/*.test.mjs` fayl nomidan ishlaydi |
| Tez buyruq (task commit) | `npm run gate:fast` → `npm run test:fast && npm --prefix frontend test` |
| Frontend-only tez buyruq | `npm --prefix frontend test` → `node --test scripts/*.test.mjs && vitest run` |
| To'liq to'plam (faza darvozasi) | `npm run gate` (sim:up → backend lint/test → cv → bot → i18n:check → frontend test/typecheck/lint/build) |
| **Taxminiy vaqt — `gate:fast`** | **155 s / 152 s** [O'LCHANDI: 08-20, tinch xost, ikkala o'lchov exit 0] · byudjet **200 s** · zaxira **45 s (23 %)** |
| **Taxminiy vaqt — `gate`** | **1909 s / 1842 s** [O'LCHANDI: 08-20] · byudjet **2300 s** · zaxira **391 s (17 %)** |
| Bugungi hajm | vitest ~**1110** test (94 fayl) · `scripts/` **18** fayl |
| ⚠ Kutilayotgan o'sish | vitest **+~55** test · **+4** skript fayli (sof matn skani) → **~40–60 s** (SPEC §16.7). ⛔ `gate:fast` zaxirasi **45 s** — taxmin bilan deyarli teng, §A3 ga qarang |

⛔ **Zanjir boshida majburiy nazorat:** `npm ci --prefix frontend` mavjudligi tekshirilsin.
[MEROS: STATE.md `deferred-items.md` №13] — 8-fazada `frontend/node_modules` **bo'sh** edi va
nosozlik faqat **29-daqiqada** ko'rindi.

### Sampling Rate

| Daraja | Buyruq | Nima kafolatlaydi | Byudjet |
|--------|--------|--------------------|---------|
| **Har task commit** | `npm run gate:fast` | Frontend'ning **butun** to'plami (skript darvozalari + vitest) + backend unit — ya'ni 9-fazada bu **to'liq qamrov** | **200 s** |
| **Har to'lqin (wave) merge** | `npm --prefix frontend test` + `npm --prefix frontend run i18n:check` + `npm --prefix frontend run typecheck` | Kalit-parity, ICU-parity, transliteratsiya drifti va tip xatolari to'lqin ichida qolsin | ~180 s |
| **Wave 1 dan keyin qo'shimcha** | `npm --prefix frontend run build` | ⛔ Tema qatlami `layout.tsx` + `<head>` skriptiga tegadi — SSG marshrutlari (3 locale × ~27 sahifa) **build paytida** yiqilishi mumkin va uni `vitest` ko'rmaydi | ~120 s |
| **`/gsd-verify-work` dan oldin** | `npm run gate` — ⛔ **to'liq yashil** | Faza darvozasi | **2300 s** |
| **Faza yopilishida** | `gate` va `gate:fast` ni **qayta o'lchash** (05-15 W0-13 protokoli: tinch xost, uch o'lchov, eng yomon × 1,20, sabab yozilgan) | §A3 — zaxira 45 s va o'sish taxmini 40–60 s | — |

⛔ **9-fazada `npm run test:tenancy` va `cv:test`/`bot:test` alohida chaqirilmaydi** — faza
`frontend/` dan tashqariga chiqmaydi. Ular `gate` zanjirida qoladi (regressiya nazorati sifatida),
lekin to'lqin darajasida **namuna olinmaydi**: ular bu fazaning kodini umuman qamramaydi.

### Mezon → O'lchov xaritasi

⛔ Oxirgi ustun — bu fazaning **eng katta test-yozish xavfi** (§Tuzoq 1). U har qatorda
**nomma-nom** yozilgan, chunki uni unutish testni «yashil, lekin hech nimani o'lchamaydigan»
holga keltiradi.

| Mezon / Darvoza | O'lchanadigan xulq | Turi | Avtomatik buyruq | ⛔ jsdom cheklovi qanday hisobga olinadi |
|-----------------|--------------------|------|-------------------|------------------------------------------|
| **SC#1** (xoreografiya ishlaydi) | 1–5-qadamning ulanish nuqtalari DOM'da; 6-qadam **tegilmagan** | komponent | `npx vitest run src/components/collect/` | `Element.animate` **yo'q** → animatsiya **CSS sinf/`@keyframes`** bilan; test **sinf qo'shilganini** o'lchaydi, harakatni emas |
| **SC#1** / ⛔ **G-motion-2** (≤150ms, bloklamaydi) | (a) 150ms da input `activeElement` + `value===""` + `disabled===false` + `readOnly===false`; (b) 150ms da yozilgan belgi **to'liq** turadi; (c) klon `pointer-events==="none"` + `aria-hidden==="true"`; (d) `setTimeout` ichida `set[A-Z]` **0** (AST); (e) xoreografiya istisno otsa ham qator+fokus joyida | komponent + AST | `npx vitest run src/components/collect/success-choreography.test.tsx src/components/collect/collect-session.test.tsx` | ⛔ **(b) uchun `vi.useFakeTimers({ shouldAdvanceTime: true })`** — `userEvent` soxta taymer bilan aks holda osiladi [naqsh: `discovery-panel.test.tsx:245`]. ⛔ **(c) `el.style.pointerEvents` (inline)** — sinfdan `getComputedStyle` **`"auto"`** qaytaradi [O'LCHANDI]. ⛔ FLIP masofasi testda **0** (`getBoundingClientRect`) — bo'lish qilinmaydi |
| **SC#2** (dashboard jonlanishi) | Skeleton → stagger → count-up → sparkline/donut; `null` qiymatda count-up **boshlanmaydi** | komponent | `npx vitest run src/components/dashboard/ src/components/headline/` | ⛔ `requestAnimationFrame` **mavjud** va `useFakeTimers` uni **patch qiladi** [O'LCHANDI] → `advanceTimersByTime` bilan oxirgi kadr deterministik; `vi.advanceTimersToNextFrame()` ham mavjud |
| **SC#3** / ⛔ **G-motion-4** (tema token-scope) | (a) `className`/`cn(` ichida `dark:` **0**; (b) `@theme inline` **0**; (c) `[data-theme="dark"]` va `["sun"]` token to'plamlari **teng** va `--color-*-text` oilasi **ikkalasida ham**; (d) `data-theme` reyestri **aynan 3** + `theme.*` uchala locale'da; (e) `suppressHydrationWarning` + `<head>` skripti **bor** | skript (matn skani) | `node --test scripts/theme-tokens.test.mjs` | ⛔ jsdom **umuman ishtirok etmaydi** — sof fayl skani. ⛔ (a) `grep "dark:"` **2 yolg'on-ijobiy** beradi [O'LCHANDI: `capture-cell.tsx:106`, `api-types.ts:1400`] → skan `className=`/`cn(` argumentlari bilan **chegaralanadi** |
| **SC#3** / ⛔ **G-motion-5** (kontrast) | (a) `oklch()` **parse**; (b) ≥12 juftlik × 3 tema (matn ≥4.5, chegara ≥3.0); (c) izohdagi `N.NN:1` ↔ hisoblangan **±0.01**, ≥4 da'vo; (d) `bg-accent` + `text-accent-text` bir `className` da **0** | skript (CSS parse + matematika) | `node --test scripts/contrast.test.mjs` | ⛔ jsdom ishtirok etmaydi. ⛔ **Gamut siyosati e'lon qilinadi** (gamma fazoda kesish) — usiz ikki implementatsiya ikki xil son beradi [O'LCHANDI: `--color-accent` gamutdan tashqarida]. ⛔ (c) izohlari kalkulyator `--print` chiqishidan **generatsiya** qilinadi (§Tuzoq 2) |
| **SC#4** / ⛔ **G-motion-1** (reduced-motion) | (a) `globals.css` da `@media (prefers-reduced-motion: reduce)` bloki bor va `animation-duration` **va** `transition-duration` ni `!important` bilan ≤0.01ms qiladi (**parse**, grep emas); (b) `animate-*` ↔ `motion-reduce:` juftligi, qamrov `components/**` dan hosila, chegara **≥5**; (c) reduced mock'da klon **yaratilmaydi** (`document.body` bolalari o'zgarmaydi), halqa yo'q, **LEKIN** to'lov qatori bor va fokus inputda; (d) `confetti`/`burst`/`particle` ta'rifi **0** | skript + komponent | `node --test scripts/motion-tokens.test.mjs` && `npx vitest run src/components/collect/success-choreography.test.tsx` | ⛔ **(c) `vi.stubGlobal("matchMedia", …)` MAJBURIY** — jsdom'da `window.matchMedia` **`undefined`** [O'LCHANDI], ya'ni stubsiz `TypeError`. ⛔ Stub **har testda alohida**, `vitest.setup.ts` da **emas**: global bo'lsa teskari shox (reduced **o'chirilgan**) hech qachon o'lchanmasdi. ⛔ Komponent tomonda guard majburiy (`typeof window.matchMedia !== "function"`) |
| **SC#5** / ⛔ **G-motion-3** (GPU + byudjet) | (a) har `@keyframes` xossalari **to'plam tengligi** bilan ruxsat etilgan to'plamda; `width/height/top/left/margin*/padding*` — har biri **0**; chegara **≥6 blok**; (b) `components/**` da `duration-<raqam>` **0**, `transition-[` va inline `animation:` **0**; (c) `@keyframes` **faqat** `globals.css` da; (d) `dependencies` **to'plam tengligi** | skript (CSS/JSON skani) | `node --test scripts/motion-tokens.test.mjs` | ⛔ jsdom ishtirok etmaydi. ⛔⛔ **(d) SON bilan yozilmasin** — bugungi holat **18 paket**, SPEC 20 deydi [O'LCHANDI] → `length === 20` **birinchi kuni qizil**; `deepEqual(actual, EXPECTED_18_NAMES)` esa paket **almashtirilganda** ham ushlaydi |
| **Chegara** / ⛔ **G-motion-6** (ko'r deklaratsiya) | (a) mavjud `BLIND_DECLARATION_TOKENS` va `MIN_*` **o'zgarmaydi**; (b) `cashier` sessiyasida tushum kartasi DOM'da **yo'q** **va** so'rov **0** chaqiruv; `director` da **bor**; (c) `components/dashboard/**` da `hasPermission(` **0**; (d) bayram copy'si (`Ajoyib`/`Zo'r`/`Tabrik`/`Отлично`/`Поздравля`) **0**, uchala locale, chegara ≥5 token; (e) `components/collect/**` da `confetti`/`burst`/`particle` **0** | skript + komponent | `node --test scripts/collect-surface.test.mjs` (⛔ **MAVJUD, O'ZGARMAYDI**) && `npx vitest run "src/app/[locale]/(app)/dashboard"` | ⛔ **(b) ikki qatlam MAJBURIY**: `hidden` bilan yashirilgan karta so'rovni **baribir** yuborardi va summa tarmoq panelida ko'rinardi. So'rov qatlami `apiFetch` mock'ining **chaqiruvlar soni** bilan o'lchanadi [naqsh: `payment-bar.test.tsx`]. ⚠ Sessiya `setSession()`/`clearSession()` bilan quriladi |
| **L-9** / ⛔ **G-motion-7** (CLS + Display-XL) | (a) `text-display` **≤2** mahsulot faylida va reyestrga **teng**; (b) `headline-card` da **shartli** — `unit==="soum"` da bor, `"count"` da **yo'q**, ikkalasi **bitta testda**; (c) `isPending` shoxidagi `Skeleton` ning `h-N` kontent qator qutisiga **teng** (reyestr **jadvaldan** o'qiladi); (d) `text-base ≤7`, `text-xl ≤4`, `text-3xl 0`, `text-[ 0`; (e) `font-medium ≤21` | skript + komponent | `node --test scripts/typography.test.mjs` && `npx vitest run src/components/headline/` | ⛔ (c) **sinf satri** ustida o'lchanadi (`className` ni o'qish), hisoblangan balandlik ustida **emas** — jsdom layout **qilmaydi** (`getBoundingClientRect` **0**). ⛔ Bu **CLS ning yagona mexanik proksisi**; haqiqiy CLS — HUMAN-UAT |
| **FOUND-04** (3 til) | 11 yangi kalit uchala locale'da; ICU argumentlari teng; transliteratsiya drifti yo'q | skript | `npm --prefix frontend run i18n:check` (⛔ **MAVJUD, O'ZGARMAYDI**) | jsdom ishtirok etmaydi. ⚠ `gen-cyrillic.test.mjs` `[A-Za-z]+[0-9]` naqshini **taqiqlaydi** — yangi copy shuni hisobga olsin |

⛔ **Sabotaj majburiyati (SPEC §16.3, MEROS 08-20 S-5):** yuqoridagi **har** darvoza uchun reja
sabotaj o'lchovini yozadi va **ikki** natijani qayd etadi: (a) nishon test **qizardi**, (b) qo'shni
testlar **yashil qoldi**. ⛔ Sabotaj modulni **import qilinadigan** holda qoldirishi shart — aks
holda u mezonni emas, **yig'ilishni** o'lchaydi.

### `human_only_verifications` (09-VALIDATION.md frontmatter'i uchun)

⛔ To'rtala kalit har bandda to'ldirilgan — `check-validation-signoff.mjs` qoida (3) shuni talab
qiladi. «Avtomatlashtirib bo'lmaydi» da'vosi **hech qachon bepul emas**: u ism va shart talab qiladi.

⛔⛔ **QIYMATLAR BIR QATORDA — va bu uslub emas, MEXANIKA [O'LCHANDI].**
`scripts/check-validation-signoff.mjs` ataylab **tor YAML qism to'plamini** o'qiydi
(`parseFrontmatter`/`parseList`, `node:` dan boshqa bog'liqlik yo'q). Uning yagona qabul
qiladigan shakli — `key: value` **bitta qatorda**. ⛔ Agar qiymat `>-` (folded) yoki `|`
(literal) bilan yozilsa, parser `PAIR_RE` orqali qiymatni **literal `">-"`** deb o'qiydi,
davomi qatorlarni esa **tashlab yuboradi** — va `filled(">-")` **`true`** qaytaradi.
Ya'ni darvoza **yashil** bo'ladi, sabab matni esa `">-"` — bu aynan loyiha kurashadigan
**bo'sh-yashil** sinfi. `08-VALIDATION.md` ham shu sababdan uzun bir qatorli qiymatlardan
foydalanadi.

```yaml
human_only_verifications:
  - item: 60fps arzon Android qurilmada — 6-qadam xoreografiya va dashboard stagger jank bermaydi (ROADMAP SC#5)
    why_not_automatable: jsdom layout ham, kompozitsiya ham QILMAYDI — `getBoundingClientRect()` nol qaytaradi, `Element.animate` va `document.getAnimations()` UMUMAN yo'q [O'LCHANDI: jsdom 30.0.1 + vitest 4.1.10]. Ya'ni «kadr tushdimi?» savoliga test qatlamida javob beradigan sirt YO'Q. Mexanik proksi G-motion-3(a) — u `@keyframes` xossalari to'plamini `transform`/`opacity` bilan qulflaydi va `width`/`height`/`top`/`left` ni nolga tushiradi, ya'ni layout-thrash SABABINI yo'q qiladi. Lekin sabab yo'qligi natija borligini isbotlamaydi: to'g'ri xossalar bilan ham juda ko'p bir vaqtli animatsiya arzon GPU'ni to'ldiradi. Bu — o'lchov, kod emas
    owner: Ijrochi (dala qurilmasi bilan)
    trigger: Wave 3 yakuni — 09-HUMAN-UAT.md #1; natija KADR/SONIYA raqami bilan yoziladi
  - item: Lighthouse Performance >= 90 va CLS < 0.05 (arzon Android profili, ROADMAP SC#5)
    why_not_automatable: Lighthouse CI'da YO'Q va bu fazada QO'SHILMAYDI (09-UI-SPEC §16.6, [QAROR]) — u headless Chrome + yangi ishlab chiqish bog'liqligini talab qiladi va `gate` byudjetiga daqiqalar qo'shardi. Bundan ham muhimi: mexanik qatlamning yashilligi bilan o'lchov qatlamining yo'qligini yopish TAQIQLANADI [MEROS: D-01, FOUND-07 va AI-02 darsi]. CLS uchun mexanik proksi bor va u TOR: G-motion-7(c) skeleton `h-N` sinfini kontent qator qutisiga tenglaydi — bu CLS ning AYNAN sababi [M-25: bugun 8–12px farq], lekin YAGONA sababi emas (shrift yuklanishi, kech kelgan karta va rasm ham siljitadi)
    owner: Ijrochi
    trigger: Wave 3 yakuni — 09-HUMAN-UAT.md #2; ⛔ natija SON bilan yopiladi, «ko'rinishi yaxshi» bilan EMAS
  - item: Iliq fon (rang 2.0), tungi va quyosh rejimlarining VIZUAL idroki — uch rol, real ekranlarda
    why_not_automatable: G-motion-5 kontrast NISBATINI o'lchaydi va u matematik jihatdan to'liq (12+ juftlik × 3 tema, izohlar ±0.01 da qulflangan). O'lchanMAGANI — o'sha nisbatlarning ODAM KO'ZIDA ishlashi: `text-muted` iliq fonda 5.06:1 (AA dan o'tadi), lekin ierarxiya hamon o'qiladimi; dark rejimda `border-ui` 3.57:1 chegarani ushlaydi, lekin karta konturi quyuq fonda KO'RINADIMI; quyosh rejimida soya `none` qilingandan keyin karta yuzadan AJRALADIMI. Bu lug'at emas, IDROK savoli va u ekran yorqinligiga, burchagiga va foydalanuvchi yoshiga bog'liq — kassir ochiq havoda, direktor ofisda ishlaydi
    owner: Mahsulot egasi (kassir va direktor bilan)
    trigger: Pilot tayyorgarligi haftasi — 09-HUMAN-UAT.md #3
  - item: "Bayram BLOKLAMAGANINING dala tasdig'i: kassir 20 ketma-ket to'lov yozadi va bironta rasta kodi yo'qolmaydi"
    why_not_automatable: G-motion-2 buni SINTETIK ravishda o'lchaydi va o'lchovi halol — 150ms nuqtasida `userEvent.type` bilan yozilgan belgi input qiymatida to'liq turadi. Lekin u BITTA to'lovni, BITTA soxta taymer bilan, jsdom'da o'lchaydi. Dala sharoiti boshqacha: navbat turadi, kassir kodni YODDAN teradi, telefon issiq, tarmoq sekin va xoreografiya HAR to'lovda qayta ishga tushadi. Nosozlik shakli ham boshqacha — u «input bloklandi» emas, «kassir ikkilanib to'xtadi» bo'lib ko'rinadi va uni faqat kuzatish ko'radi. Bu fazaning eng qimmat nuqsoni aynan shu (09-UI-SPEC §1.2) va u sintetik testdan qochib qutula oladi
    owner: Mahsulot egasi (kassir bilan)
    trigger: Pilot tayyorgarligi haftasi — 09-HUMAN-UAT.md #4
  - item: Vestibulyar sezgir foydalanuvchi tasdig'i — OS darajasida reduced-motion yoqilganda ilova to'liq harakatsiz
    why_not_automatable: G-motion-1 `matchMedia` MOCK'i bilan o'lchaydi, ya'ni u «kod shoxi to'g'rimi?» degan savolga javob beradi. O'lchanMAGANI — brauzerning HAQIQIY `prefers-reduced-motion` signali bilan CSS `@media` blokining birgalikda ishlashi va uchinchi tomon xulqi (Radix dialog, `sonner` toast) o'sha rejimda TINCH qolishi. jsdom'da CSS umuman yuklanmaydi [O'LCHANDI: Tailwind sinfidan `getComputedStyle` «auto» qaytaradi], ya'ni `@media` blokining kuchga kirishi test qatlamida PRINSIPIAL ravishda ko'rinmaydi
    owner: Ijrochi (OS sozlamasi yoqilgan holda)
    trigger: Wave 3 yakuni — 09-HUMAN-UAT.md #5
```

### `automated_replacements` (09-VALIDATION.md frontmatter'i uchun)

⛔ Qoida (4): har bandda `was` va **ishlaydigan** `now` buyrug'i. ⛔ Bu yerda ham qiymatlar
**bir qatorda** — sabab yuqorida.

```yaml
automated_replacements:
  - was: Brauzerda tugmani bosib «animatsiya ishladimi?» deb ko'z bilan qarash
    now: "npx vitest run src/components/collect/success-choreography.test.tsx — klonning `pointer-events` INLINE qiymati «none», `aria-hidden` «true», 150ms nuqtasida input `activeElement` va yozilgan belgi to'liq turadi. ⛔ Sinf nomi YETARLI EMAS: jsdom Tailwind CSS ni yuklamaydi va `pointer-events-none` sinfidan `getComputedStyle` «auto» qaytaradi [O'LCHANDI]"
  - was: Tema tugmasini bosib uchala rejimni ko'z bilan aylantirib chiqish
    now: "node --test scripts/theme-tokens.test.mjs — `[data-theme=dark]` va `[data-theme=sun]` bloklaridagi o'zgaruvchi to'plamlari TENG va `--color-*-text` oilasi ikkalasida ham bor (M-18 ning besh AA buzilishi AYNAN shu tenglik bilan ushlanadi); `@theme inline` 0 marta; `dark:` varianti `className`/`cn(` argumentlari ichida 0 marta"
  - was: DevTools da rangni tanlab kontrast nisbatini qo'lda tekshirish
    now: "node --test scripts/contrast.test.mjs — `globals.css` dan `oklch()` qiymatlari PARSE qilinadi va WCAG 2.x nisbati hisoblanadi (12+ juftlik × 3 tema); izohdagi har `N.NN:1` da'vosi hisoblangan qiymat bilan ±0.01 da solishtiriladi. ⛔ Bog'liqlik YO'Q — ~30 qatorlik sof matematika, u 09-UI-SPEC ning 15 da'vosidan 13 tasini AYNAN takrorladi"
  - was: "`prefers-reduced-motion` ni OS da yoqib, sahifani qo'lda aylanib chiqish"
    now: "node --test scripts/motion-tokens.test.mjs — global `@media` bloki PARSE qilinadi (grep emas) va `animation-duration` HAM, `transition-duration` HAM `!important` bilan <=0.01ms ekani tekshiriladi; `animate-*` va `motion-reduce:` juftligi qamrovdan HOSILA. Klon shoxi esa `vi.stubGlobal(matchMedia, ...)` bilan komponent testida"
  - was: Kassir hisobi bilan kirib dashboard'da tushum kartasi ko'rinmasligini ko'z bilan tekshirish
    now: "npx vitest run src/app --dir src/app — `cashier` sessiyasida tushum kartasi DOM'da YO'Q VA `apiFetch` mock'ining chaqiruvlar soni 0; `director` sessiyasida BOR. ⛔ Ikki qatlam ataylab: `hidden` bilan yashirilgan karta so'rovni baribir yuborardi va summa tarmoq panelida ko'rinardi"
  - was: Yangi og'ir paket qo'shilmaganini `package.json` ga qarab eslab qolish
    now: "node --test scripts/motion-tokens.test.mjs — `dependencies` kalitlari TO'PLAM TENGLIGI bilan 18 ta nomdan iborat reyestrga solishtiriladi. ⛔ SON bilan emas: `length === N` shakli paket almashtirilganda (biri chiqib, biri kirganda) yolg'on yashil qolardi"
  - was: Skeleton kontentga almashganda karta «sakraydimi?» deb ko'z bilan kuzatish
    now: "node --test scripts/typography.test.mjs && npx vitest run src/components/headline/ — `isPending` shoxidagi `Skeleton` ning `h-N` sinfi kontent shoxining qator qutisiga TENG (reyestr jadvaldan o'qiladi, testda qayta yozilmaydi); `text-display` <=2 mahsulot faylida va `headline-card` da `unit === soum` shartiga bog'liq"
```

### Nyquist xulosasi

| Savol | Javob |
|-------|-------|
| Har mezon uchun avtomatik buyruq bormi | ⛔ **Ha** — 5 ta SC va 7 ta `G-motion-*` ning har biri yuqoridagi xaritada buyruq bilan |
| Namuna olish tezligi nuqsonni qanchada ushlaydi | **Bir task commit** — `gate:fast` frontend'ning **butun** to'plamini yugurtiradi, ya'ni 9-fazada namuna **to'liq qamrov** bilan teng |
| Qo'lda qolgan bandlar egasi va tetigi bilanmi | ⛔ **Ha** — 5 band, har birida `why_not_automatable` + `owner` + `trigger` |
| `nyquist_compliant` qachon `true` bo'ladi | ⛔ Wave 0 dagi **7** ta test fayli tug'ilgach va 5 ta qo'lda band `09-HUMAN-UAT.md` ga **ko'chirilgach**. ⛔ Undan **oldin** `false` |

---

## Xavfsizlik domeni

`security_enforcement: true`, `security_asvs_level: 1`.

### Qo'llaniladigan ASVS kategoriyalari

| ASVS kategoriya | Qo'llanadimi | Standart nazorat |
|-----------------|--------------|------------------|
| V2 Autentifikatsiya | **yo'q** | Faza autentifikatsiyaga tegmaydi |
| V3 Sessiya boshqaruvi | **yo'q** | Yangi sessiya yuzasi yo'q |
| V4 Kirish nazorati | ⛔ **HA** | Ikki dashboard kartasi `report_view` ostida; ⛔ **haqiqiy nazorat serverda** (`require_permission(REPORT_VIEW)` [VERIFIED]) — klient darvozasi faqat ko'rinish uchun |
| V5 Kirish validatsiyasi | ⛔ **HA (kichik)** | `localStorage["sbozor-theme"]` — **ishonchsiz kirish**. Inline skript uni `data-theme` ga qo'yishdan **oldin** reyestr bilan tekshiradi (§Kod namunalari 6) |
| V6 Kriptografiya | **yo'q** | Faza sir yoki shifrlashga tegmaydi |
| V7 Xatolar / jurnal | **yo'q** | Yangi xato kodi yo'q (SPEC §14.3) |
| V12 Fayllar | **yo'q** | Fayl yuklash yo'q |
| V14 Konfiguratsiya | ⛔ **HA** | `dangerouslySetInnerHTML` — statik, foydalanuvchi kiritmasi **yo'q**, satr build paytida qotirilgan |

### Ma'lum tahdid naqshlari (Next.js 16 + Tailwind 4 + localStorage)

| Naqsh | STRIDE | Standart mitigatsiya |
|-------|--------|-----------------------|
| `localStorage` orqali `data-theme` ga ixtiyoriy satr → CSS selektor injeksiyasi | Tampering | ⛔ **Reyestr validatsiyasi** inline skript ichida (`t==="dark"\|\|t==="sun"\|\|t==="light"`) — G-motion-4(d) uchta qiymatni to'plam tengligi bilan qulflaydi |
| `dangerouslySetInnerHTML` — XSS vektori | Tampering | ⛔ Satr **statik va build paytida qotirilgan**; foydalanuvchi ma'lumoti interpolatsiya **qilinmaydi**. CSP loyihada yo'q [O'LCHANDI] — kelajakda qo'shilsa `nonce` kerak bo'ladi [CITED: Next.js hujjati] |
| ⛔⛔ Dashboard tushum kartasi kassirga ko'rinib qolishi | Information Disclosure | ⛔ **Ikki qatlam**: (a) sahifada shart → so'rov ham ketmaydi (G-motion-6(b)); (b) serverda `require_permission(REPORT_VIEW)` — kassirda yo'q [VERIFIED: `rbac.ts`, `occupancy.py:83`, `reports.py:156`] |
| Ko'r deklaratsiyaning arifmetika bilan buzilishi | Information Disclosure | ⛔ `collect-surface.test.mjs` **o'zgarmaydi** (`MIN_FORBIDDEN_NAMES=14`, `MIN_BLIND_DECLARATION_TOKENS=7`) |
| Uchayotgan klon bosishni ushlashi (UI redressing tusi) | Tampering | ⛔ `pointer-events:none` + `aria-hidden` — G-motion-2(c) da o'lchanadi |
| ⛔ `occupied_slots` (taqiqlangan nom) kassir yuzasiga sizishi | Information Disclosure | ⚠ **Yangi xavf:** `occupancyStallItemSchema` da `occupied_slots` bor va u `FORBIDDEN_NAMES` ro'yxatida [KOD: `collect-surface.test.mjs:106`]. ⛔ Bandlik tipini `components/collect/**` ga import qilish darvozani **qizartiradi** — bu **to'g'ri xulq**, lekin ijrochi buni oldindan bilishi kerak |

⛔ **Yangi hujum yuzasi qo'shilmaydi:** yangi endpoint yo'q, yangi paket yo'q, yangi sir yo'q, yangi fayl yuklash yo'q.

---

## Taxminlar jurnali

| # | Taxmin | Bo'lim | Xato bo'lsa ta'siri |
|---|--------|--------|----------------------|
| **A1** | Dark rejimning uchta xromatik tokenidagi **+0.10** farq gamut xaritalash siyosati farqidan — SPEC muallifi boshqa kesish usulini ishlatgan | Tuzoq 2 | ⛔ **Past**: ikkala qiymat ham AA dan o'tadi. ⛔ **Lekin izohlar generatsiya qilinmasa** G-motion-5(c) qizil |
| **A2** | «Bandlik halqasi» kartasi **kecha**ni so'raydi (bugungi javob bo'sh bo'lgani uchun) | Tuzoq 3 | O'rta: bugun so'ralsa direktor doim bo'sh halqa ko'radi va SC#2 amalda bajarilmaydi |
| **A3** | 4 ta yangi `scripts/*.test.mjs` + ~55 vitest testi `gate:fast` ga **40–60 s** qo'shadi (SPEC §16.7 taxmini) | Validatsiya | O'rta: 45 s zaxira bilan deyarli teng. ⛔ Oshsa 05-15 W0-13 qayta o'lchov protokoli |
| **A4** | `dashboard.revenueTrend*` kartasi `useRevenueReport` ni **7 kunlik davr** bilan chaqiradi va server bu davrni qisqartirmaydi | Naqsh 5 | Past: `from_date`/`to_date` **serverniki** [KOD] — karta serverdan kelgan davrni ko'rsatsa xavf yo'q |
| **A5** | `useSyncExternalStore` + `MutationObserver` tema hook'i uchun yetarli (React 19.2.8) | Naqsh 4 | Past: muqobil — oddiy `useState` + custom event; ikkalasi ham ishlaydi |
| **A6** | Sparkline `<path>` ning `stroke-dasharray: 220` qiymati 7 nuqtali chiziq uzunligiga yetadi | Kod namunalari | Past: `getTotalLength()` bilan aniq hisoblash mumkin, lekin u jsdom'da **yo'q** — qotirilgan qiymat kifoya (kesilsa chiziq to'liq chizilmaydi, ko'z bilan sozlanadi) |
| **A7** | 9-faza yangi `REQUIREMENTS.md` ID yaratmaydi; SC#1–SC#5 talab o'rniga ishlaydi | Faza talablari | O'rta: `requirements:check` skripti qizarmaydi (ro'yxat o'zgarmaydi), lekin traceability'da 9-faza **ko'rinmaydi** — ⛔ bu **ataylab**, sabab yozilgan |

---

## Ochiq savollar

> ⛔ **HOLAT (2026-08-17, rejalashtirishdan keyin): beshalasi ham YOPILDI.** Har savolning **Tavsiya** bandi tegishli rejaga so'zma-so'z singdirildi va qaysi rejaga tushgani sarlavhada `(RESOLVED — 09-0N da)` bilan belgilandi. Savollarning matni **o'chirilmaydi**: tanlovning muqobillari va sabablari shu yerda qoladi, aks holda keyingi o'quvchi qarorni «shunchaki shunday qilingan» deb o'qirdi.

1. **G-motion-5(c) izohlari qanday tug'iladi?** ⛔ **(RESOLVED — 09-01 da)**
   - Bilamiz: `globals.css` da bugun **6 ta** nisbat izohda va ularni hech nima tekshirmaydi [M-15]. Kalkulyator ishlaydi va 13/15 da'voni takrorladi.
   - Noaniq: ijrochi izohlarni **qo'lda** yozadimi yoki **generatsiya** qiladimi.
   - **Tavsiya:** `contrast.test.mjs` ga `--print` rejimi qo'shilsin (`node scripts/contrast.test.mjs --print`), chiqishi izohlarga ko'chirilsin. ⛔ Aks holda Tuzoq 2 birinchi kuni yuz beradi.

2. **`success-choreography.tsx` — komponentmi yoki sof funksiyami?** ⛔ **(RESOLVED — 09-04 da)**
   - Bilamiz: G-motion-2(d) uning **manbasida** `setTimeout` ichida `setState` yo'qligini **AST bilan** o'lchaydi. Ya'ni fayl **parse qilinadigan** bo'lishi shart.
   - Noaniq: React komponenti (`.tsx`, DOM'ni React boshqaradi) yoki imperativ funksiya (`.ts`, `document.body.appendChild`).
   - **Tavsiya:** ⛔ **Imperativ funksiya** (`.ts`). Sabab: (a) `setState` **umuman bo'lmaydi** → G-motion-2(d) tavtologiya emas, mexanik; (b) klon React daraxtidan tashqarida bo'lsa, u `cleanup()` bilan yo'qolmaydi va test uni `document.body` da **sanay oladi** — G-motion-1(c) ning aynan o'lchovi. ⚠ SPEC §3.4 uni `collect/success-choreography.tsx` deb nomlaydi — ⛔ **nom saqlansin**, ichi imperativ bo'lsin (`.ts` kengaytmasi bilan; agar SPEC nomi qat'iy o'qilsa, `.tsx` da ham eksport sof funksiya bo'lishi mumkin).

3. **`dashboard/page.tsx` bugun `"use client"` — test uni qanday render qiladi?** ⛔ **(RESOLVED — 09-05 da)**
   - Bilamiz: sahifa `"use client"` [KOD: `dashboard/page.tsx:1`], `useAuthStore` dan rollarni oladi. `market-status-card.test.tsx` da mavjud naqsh bor.
   - Noaniq: `AuthProvider` + `QueryProvider` + `NextIntlClientProvider` o'ramining aniq shakli.
   - **Tavsiya:** `payment-bar.test.tsx:30-60` naqshini ko'chirish (`setSession()` / `clearSession()` + uchala provayder). ⛔ Yangi test infratuzilmasi **qurilmaydi**.

4. **`@keyframes` soni ≥6 chegarasi bugungi 0 dan qanday to'ladi?** ⛔ **(RESOLVED — 09-01 da)**
   - Bilamiz: `globals.css` da bugun `@keyframes` — **0** [O'LCHANDI].
   - Kerakli minimal ro'yxat (6): `draw` (check), `ringpulse`, `landin` (qator), `shimmer`, `breath` (yashil nafas), `attention` (amber halqa). ⛔ Yettinchisi — `shake` (forma xatosi).
   - **Tavsiya:** Reja bu ro'yxatni **nomma-nom** yozsin — G-motion-3(c) nomlarni reyestrdan hosila qiladi.

5. **`text-display` ning ikkinchi joyi `headline-card` da shartli — skeleton ham shartlimi?** ⛔ **(RESOLVED — 09-05 da; reyestr darvozasi 09-06 da)**
   - Bilamiz: G-motion-7(c) skeleton `h-N` ni kontent qator qutisi bilan **teng** talab qiladi; `headline-card` da `text-display` faqat `unit === "soum"` da.
   - Noaniq: `isPending` shoxida `unit` **hali ma'lum emas** (javob kelmagan).
   - **Tavsiya:** ⛔ Skeleton **`h-11`** bo'lsin (eng katta shox). Sabab: `h-8` dan `h-11` ga sakrash CLS beradi; `h-11` dan `h-8` ga qisqarish esa **layout siljishi emas, bo'shliq** — va u ko'zga sezilmaydi. ⛔ G-motion-7(c) reyestri buni **jadvaldan** o'qisin, testda qayta yozmasin.

---

## Wave tartibi (rejalashtiruvchiga tavsiya)

⛔ Bu bo'lim reja emas — bog'liqlik tartibi. U ikki tuzoqdan (§Tuzoq 2, §Tuzoq 5) kelib chiqadi.

| Wave | Nima | Nega bu tartibda |
|------|------|-------------------|
| **0** | `globals.css` ni **to'liq** yopish: motion tokenlari + `--default-transition-*` + global reduced-motion + `@keyframes` (7 ta) + uchta `[data-theme]` scope + M-19/M-20 token tuzatishlari | ⛔ Har uchala CSS darvozasi (`motion-tokens`, `theme-tokens`, `contrast`) **shu bitta faylni** o'qiydi. Uni bo'lib qurish har wave'da yarim-yashil darvoza qoldirardi |
| **0** | `contrast.test.mjs` + `--print`, so'ng izohlarni **generatsiya** qilish | ⛔ Tuzoq 2 — izohlar tokenlar bilan **bir vaqtda** tug'ilishi shart |
| **0** | 4 ta `scripts/*.test.mjs` skeleti + `dependencies` to'plami (18 nom) | Tuzoq 5; darvozalar komponentlardan **oldin** tirik bo'lsin |
| **1** | Tema qatlami: `lib/theme.ts` + `layout.tsx` (`<head>` skript, `suppressHydrationWarning`) + `shell/theme-toggle.tsx` + 11 copy kaliti + `i18n:gen` | SC#3; komponent qatlamiga **bog'liq emas** |
| **1** | `ui/` jilosi: `button` (press-scale + `duration-(--motion-fast)`), `card` (hover), `dialog` (`data-[state]`), `skeleton` (shimmer) | ⛔ Y-1 va Y-2 ikkalasi ham shu primitivlarni ishlatadi |
| **2** | Y-1: `lib/motion.ts` → `success-choreography` → `payment-bar` (check-draw) → `pending-card` (halqa + `text-display` + `h-11`) → `payment-row` (qo'nish) → `collect-session` (ulanish) | ⛔ **ENG YUQORI ustuvorlik** (SPEC §1.2); 6-qadamga **tegilmaydi** |
| **2** | Y-2: `lib/use-count-up.ts` → `headline-card` (`text-display` shartli + `h-11`) → `dashboard/revenue-card` → `dashboard/occupancy-donut` → `dashboard/page.tsx` (huquq sharti) | Y-1 dan mustaqil → **parallel** yurishi mumkin |
| **3** | Qolgan jilo: `locale-switcher` sirg'alishi, forma shake, jadval qator hover, 5 ta `Loader2` ga `motion-reduce:` | Kichik, tarqoq; oxirida |
| **3** | `09-HUMAN-UAT.md` (Lighthouse ≥90, CLS, 60fps — **son bilan**) + `gate` byudjetini qayta o'lchash | SPEC §16.6; A3 |

---

## Manbalar

### Birlamchi (HIGH ishonch — shu sessiyada o'lchandi)

- ⛔ **Kodbaza o'lchovlari** (`E:\bozor\frontend`) — `dependencies` sanog'i (**18**), `dark:` uchrashlari (**2, ikkalasi ham yolg'on-ijobiy**), tipografiya sanoqlari (13 tokendan 9 tasi SPEC bilan aynan), `@keyframes` (**0**), `prefers-reduced-motion` (**0**), `animate-spin` (**5 joy, 1 tasida `motion-reduce`**), `text-display` (**0**)
- ⛔ **jsdom/vitest muhit probasi** — `matchMedia: undefined`, `Element.animate: undefined`, `getAnimations: undefined`, `getBoundingClientRect: {0,0,0,0}`, `rAF: function`, inline uslub `getComputedStyle` da **ko'rinadi**, Tailwind sinfi **ko'rinmaydi**, `vi.stubGlobal("matchMedia")` **ishlaydi**, `useFakeTimers` rAF ni **patch qiladi**
- ⛔ **Tailwind 4.3.3 haqiqiy kompilyatsiyasi** (`@tailwindcss/postcss` + `postcss`) — `@theme` → `@layer theme{:root}`, `[data-theme]` **qatlamsiz va g'olib**, `--ease-out` **almashtiriladi**, `--default-transition-timing-function` **alohida token**, `duration-(--var)`/`ease-(--var)` **kompilyatsiya qiladi**, `--font-weight-normal` scope'da **ishlaydi**, `motion-reduce:animate-none` faqat `animation` ga tegadi
- ⛔ **Mustaqil kontrast kalkulyatori** — 09-UI-SPEC ning **15** ta nisbat da'vosidan **13 tasi aynan** takrorlandi; gamut siyosati aniqlandi
- ⛔ **Darvoza ijrosi** — `node --test scripts/bulk-action-surface.test.mjs` → **8/8 pass** (09-UI-SPEC mavjudligida G-18 e'lon darvozasi yashil, M-33 tasdiqlandi)
- `services/core-api/app/api/v1/occupancy.py:83,114` · `reports.py:156` — ikkala dashboard endpointi ham `Permission.REPORT_VIEW`
- `services/core-api/app/repositories/billing_repo.py:1338-1341` · `api/v1/billing.py:275-278` — `pending_stall_count` mavjud → `market_day_cleared` migratsiyasiz
- `frontend/src/lib/payment-queries.ts:119` — `paymentResponseSchema = z.strictObject` (8 kalit)

### Birlamchi (HIGH — rasmiy hujjat)

- [CITED] `frontend/node_modules/next/dist/docs/01-app/02-guides/preventing-flash-before-hydration.md` — tema uchun `<head>` inline skript + `suppressHydrationWarning`, `useEffect`/`useLayoutEffect` nega yaramaydi, CSP ogohlantirishi
- [CITED] `.planning/phases/09-ui-polish-motion-qatlami/09-UI-SPEC.md` (`status: approved`) — barcha [QULF] qarorlar, 7 darvoza, 34 o'lchov
- [CITED] `.claude/skills/sketch-findings-bozor/` — SKILL.md + `motion-tizimi-va-kassir.md` + `dashboard-jonlanishi.md` (foydalanuvchi tasdiqlagan CSS naqshlari)
- [CITED] `./CLAUDE.md` — stek qulflari, «What NOT to Use», Tailwind 4 CSS-first
- [CITED] `.planning/ROADMAP.md` Phase 9 — Goal, SC#1–SC#5, Chegaralar
- [CITED] `.planning/STATE.md` — `gate`/`gate:fast` byudjetlari va oxirgi o'lchovlari, 08-20 sabotaj darsi (S-5), `npm ci` darsi
- [CITED] `UI-UX-MASTERPLAN.md` §7 — mikro-UX bandlari (SPEC §13 ularning holatini yopgan)

### Ikkilamchi (MEDIUM)

- `frontend/scripts/collect-surface.test.mjs` · `bulk-action-surface.test.mjs` · `report-copy.test.mjs` · `role-gate.test.mjs` — darvoza mexanikasi naqshlari va **skan chegaralari** (dashboard uchalasidan ham **tashqarida**)
- `frontend/src/components/cameras/discovery-panel.test.tsx:245` — `vi.useFakeTimers({ shouldAdvanceTime: true })` naqshi (userEvent bilan mos)
- `frontend/messages/uz-Cyrl.overrides.json` — `[A-Za-z]+[0-9]` taqig'i va transliteratsiya qoidalari

### Uchlamchi (LOW — tasdiqlanmagan)

- Yo'q. ⛔ Bu tadqiqotda WebSearch **ishlatilmadi** — barcha da'volar kodbaza o'lchovi, rasmiy hujjat yoki tasdiqlangan upstream artefaktdan.

---

## Metadata

**Ishonch taqsimoti:**

| Soha | Daraja | Sabab |
|------|--------|-------|
| Standart stek | **HIGH** | 0 yangi paket; mavjudlari `package.json` dan o'qildi va versiyalari tasdiqlandi |
| Tailwind 4 tema mexanikasi | **HIGH** | Haqiqiy kompilyatsiya bajarildi — taxmin emas, chiqish o'qildi |
| jsdom test qobiliyati | **HIGH** | To'g'ridan-to'g'ri proba, vitest ostida |
| Kontrast matematikasi | **HIGH** | 13/15 mustaqil takrorlandi; 2 ta farq **tushuntirildi** (fon va gamut siyosati) |
| Backend ulanish nuqtalari | **HIGH** | Marshrut + huquq + repo dataclass'i o'qildi |
| Darvoza chegaralari (skan maydonlari) | **HIGH** | Uchta mavjud darvozaning manbasi o'qildi; G-18 haqiqatan ishga tushirildi |
| Byudjet ta'siri (A3) | **MEDIUM** | SPEC taxminiga tayanadi; 45 s zaxira **o'lchangan**, qo'shimcha esa **taxmin** |
| Dark rejim +0.10 farqining sababi (A1) | **MEDIUM** | Gamut siyosati farqi eng ehtimolli izoh; SPEC muallifining aniq usuli noma'lum |
| Sparkline `stroke-dasharray` qiymati (A6) | **LOW** | Ko'z bilan sozlanadi; jsdom `getTotalLength()` bermaydi |

**Tadqiqot sanasi:** 2026-08-17
**Amal muddati:** **7 kun** — Tailwind/Next/vitest versiyalari qulflangan, lekin kodbaza sanoqlari (`dependencies`, tipografiya, `motion-reduce`) **har commitda o'zgaradi**; darvozalarning quyi/yuqori chegaralari rejalashtirish paytida **qayta o'lchansin**.

---

*Faza: 09-ui-polish-motion-qatlami*
*Tadqiqot yakunlandi: 2026-08-17 — `gsd-phase-researcher`*
*Upstream: 09-UI-SPEC.md (approved), `sketch-findings-bozor` skill (001-B/002-B, foydalanuvchi tasdiqlagan 2026-08-16), ROADMAP Phase 9, REQUIREMENTS.md, STATE.md, UI-UX-MASTERPLAN.md, CLAUDE.md*
