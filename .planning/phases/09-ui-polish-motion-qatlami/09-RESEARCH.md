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

1. **G-motion-5(c) izohlari qanday tug'iladi?**
   - Bilamiz: `globals.css` da bugun **6 ta** nisbat izohda va ularni hech nima tekshirmaydi [M-15]. Kalkulyator ishlaydi va 13/15 da'voni takrorladi.
   - Noaniq: ijrochi izohlarni **qo'lda** yozadimi yoki **generatsiya** qiladimi.
   - **Tavsiya:** `contrast.test.mjs` ga `--print` rejimi qo'shilsin (`node scripts/contrast.test.mjs --print`), chiqishi izohlarga ko'chirilsin. ⛔ Aks holda Tuzoq 2 birinchi kuni yuz beradi.

2. **`success-choreography.tsx` — komponentmi yoki sof funksiyami?**
   - Bilamiz: G-motion-2(d) uning **manbasida** `setTimeout` ichida `setState` yo'qligini **AST bilan** o'lchaydi. Ya'ni fayl **parse qilinadigan** bo'lishi shart.
   - Noaniq: React komponenti (`.tsx`, DOM'ni React boshqaradi) yoki imperativ funksiya (`.ts`, `document.body.appendChild`).
   - **Tavsiya:** ⛔ **Imperativ funksiya** (`.ts`). Sabab: (a) `setState` **umuman bo'lmaydi** → G-motion-2(d) tavtologiya emas, mexanik; (b) klon React daraxtidan tashqarida bo'lsa, u `cleanup()` bilan yo'qolmaydi va test uni `document.body` da **sanay oladi** — G-motion-1(c) ning aynan o'lchovi. ⚠ SPEC §3.4 uni `collect/success-choreography.tsx` deb nomlaydi — ⛔ **nom saqlansin**, ichi imperativ bo'lsin (`.ts` kengaytmasi bilan; agar SPEC nomi qat'iy o'qilsa, `.tsx` da ham eksport sof funksiya bo'lishi mumkin).

3. **`dashboard/page.tsx` bugun `"use client"` — test uni qanday render qiladi?**
   - Bilamiz: sahifa `"use client"` [KOD: `dashboard/page.tsx:1`], `useAuthStore` dan rollarni oladi. `market-status-card.test.tsx` da mavjud naqsh bor.
   - Noaniq: `AuthProvider` + `QueryProvider` + `NextIntlClientProvider` o'ramining aniq shakli.
   - **Tavsiya:** `payment-bar.test.tsx:30-60` naqshini ko'chirish (`setSession()` / `clearSession()` + uchala provayder). ⛔ Yangi test infratuzilmasi **qurilmaydi**.

4. **`@keyframes` soni ≥6 chegarasi bugungi 0 dan qanday to'ladi?**
   - Bilamiz: `globals.css` da bugun `@keyframes` — **0** [O'LCHANDI].
   - Kerakli minimal ro'yxat (6): `draw` (check), `ringpulse`, `landin` (qator), `shimmer`, `breath` (yashil nafas), `attention` (amber halqa). ⛔ Yettinchisi — `shake` (forma xatosi).
   - **Tavsiya:** Reja bu ro'yxatni **nomma-nom** yozsin — G-motion-3(c) nomlarni reyestrdan hosila qiladi.

5. **`text-display` ning ikkinchi joyi `headline-card` da shartli — skeleton ham shartlimi?**
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
