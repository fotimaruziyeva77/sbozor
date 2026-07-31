---
phase: 2
slug: bozor-domeni-va-yangi-bozor-ustasi
status: approved
shadcn_initialized: false
preset: none
design_system: manual (1-fazadan meros, Tailwind 4 CSS-first + Radix primitivlari)
created: 2026-07-31
reviewed_at: 2026-07-31
reviewed_by: gsd-ui-checker
review_result: 6/6 dimension PASS
---

# Phase 2 — UI Design Contract

> Uch yuza uchun vizual va o'zaro ta'sir kontrakti: (1) "Yangi bozor" ustasi, (2) sxematik plan-xarita + rasta kartasi, (3) rasta/sotuvchi reestrlari + Excel import.
> Yaratdi: `gsd-ui-researcher`. Tekshiradi: `gsd-ui-checker`. Iste'mol qiladi: `gsd-planner`, `gsd-executor`.

---

## 0. Dalil holati — taxmin va faktni ajratish

Bu hujjatdagi har bir raqam quyidagi uch toifadan biriga tegishli. Hech bir qiymat "yaxshi ko'rinadi" asosida qo'yilmagan.

| Belgi | Ma'nosi |
|-------|---------|
| **[O'LCHANDI]** | Shu sessiyada kodbazada yoki hisob-kitobda o'lchandi — natija keltirilgan |
| **[KOD]** | Kodbazadan o'qildi — aniq `fayl:qator` keltirilgan |
| **[MEROS]** | 1-faza yoki 2-faza upstream artefaktidan olindi (CONTEXT / RESEARCH / ROADMAP) |
| **[QAROR]** | Bu hujjatda qabul qilindi — sabab yozilgan, muqobil rad etilgan |
| **[OCHIQ]** | Javob yo'q — §15 Open Questions'da |

Bu sessiyada bajarilgan o'lchovlar:

1. **WCAG kontrast hisobi** — `globals.css` dagi 14 ta OKLCH tokeni sRGB'ga o'girilib, nisbiy yorqinlik va kontrast nisbatlari hisoblandi (17 juftlik + 7 ta alfa-kompozitsiya). Natija: **6 ta o'lchangan WCAG AA buzilishi** (§4.2).
2. **i18n uzunlik o'lchovi** — 120 ta mavjud kalit uch tilda o'lchandi. Natija: prompt'dagi "kirill +10–15%, rus +20–30%" taxmini **noto'g'ri** (§5.1).
3. **Transliterator sinovi** — 46 ta nomzod matn `frontend/scripts/gen-cyrillic.mjs` orqali o'tkazildi. Natija: **4 ta jimgina buziladigan defekt** (§5.2).
4. **Kodbaza inventarizatsiyasi** — tipografik og'irlik/o'lcham va spacing sanog'i (§2, §3).

---

## 1. Design System — aniqlangan holat

### 1.1 Mavjud va QAYTA ISHLATILADI (yangidan qurilmaydi)

| Nima | Fayl | Holat |
|------|------|-------|
| Tailwind 4 CSS-first `@theme` bloki | `frontend/src/app/globals.css:12-54` | 14 rang, 3 radius, 2 soya, 2 shrift steki. `tailwind.config.js` **YO'Q** va yaratilmaydi |
| Global `:focus-visible` halqasi | `frontend/src/app/globals.css:70-73` | `outline: 2px solid var(--color-accent); outline-offset: 2px` |
| `Button` (cva) | `frontend/src/components/ui/button.tsx` | 4 variant (`default`/`secondary`/`ghost`/`destructive`), 3 o'lcham (`sm` h-9, `md` h-10, `lg` min-h-11 = 44px) |
| `Card` / `CardHeader` / `CardContent` | `frontend/src/components/ui/card.tsx` | Jadval emas — karta naqshi (topshiriq §7) |
| `Input` (+ `aria-invalid` uslubi) | `frontend/src/components/ui/input.tsx` | `aria-[invalid=true]` bitta atribut bilan vizual + skrinrider |
| `cn()` (clsx + tailwind-merge) | `frontend/src/lib/cn.ts` | — |
| Radix Dialog naqshi (modal + fokus tuzog'i + Esc) | `frontend/src/components/users/create-user-dialog.tsx:145-258`, `user-list.tsx:293-342` | **Ichki (inline)** — `ui/dialog.tsx` mavjud emas |
| Radix DropdownMenu (qator amallari) | `frontend/src/components/users/user-list.tsx:215-251` | — |
| `sonner` Toaster | `frontend/src/app/[locale]/layout.tsx:82` | `position="top-center" richColors` — o'rnatilgan, ishlatishga tayyor |
| nuqs URL holati | `frontend/src/components/audit/audit-filters.tsx:35-73` | `useQueryStates` + `parseAsString.withDefault("")`; `NuqsAdapter` ildiz layout'da |
| Keyset paginatsiya UI | `frontend/src/components/audit/audit-list.tsx:100-112`, `queries.ts:201-208` | `useInfiniteQuery` + `next_cursor` + "Ko'proq yuklash" tugmasi. **Sahifa raqamlari yo'q** |
| RBAC UI ko'zgusi | `frontend/src/lib/rbac.ts` + `user-list.tsx:60` | Huquq yo'q → tugma **render qilinmaydi** (yashirilmaydi) |
| next-intl 3 til + darvozalar | `messages/{uz-Latn,ru,uz-Cyrl,uz-Cyrl.overrides}.json`, `scripts/{gen-cyrillic,check-messages}.mjs` | `npm run i18n:check` — kalit-parity **va** ICU-argument parity |
| vitest + jsdom komponent testi | `frontend/src/components/auth/market-picker.test.tsx`, `vitest.config.ts` | Naqsh tayyor |

**Kalit nomlash konventsiyasi [KOD: `messages/uz-Latn.json`]:** ikki daraja — `namespace.camelCaseKey` (`users.emptyState`, `audit.filterFrom`). Uchinchi daraja **faqat** enum xaritalari uchun (`audit.actions.insert`, `audit.tables.markets`). 2-faza shu qoidaga bo'ysunadi: `stalls.*`, `vendors.*`, `zones.*`, `categories.*`, `tariffs.*`, `calendar.*`, `map.*`, `wizard.*`, `import.*` + `stalls.status.*`, `import.errors.*` enum xaritalari.

### 1.2 YETISHMAYDI — Wave 0 da yaratiladi

Quyidagilar hozir **3 joyda nusxalangan** holda yashaydi. 2-faza ~9 ta yangi ekran qo'shadi — nusxa 9 taga chiqishidan **oldin** ajratilishi shart.

| Primitiv | Hozir qayerda nusxalangan | Nega Wave 0 |
|----------|---------------------------|-------------|
| `ui/dialog.tsx` (Root/Overlay/Content/Title/Description/Footer) | `create-user-dialog.tsx:145-258`, `user-list.tsx:293-342`, `temp-password-dialog.tsx` — 3 ta bir xil overlay+content class satri | 2-fazada +5 dialog (rasta kartasi, rasta tahriri, sotuvchi, biriktirish, tasdiq) |
| `ui/field.tsx` (label + control + xato + hint) | `audit-filters.tsx:173-190`, `create-user-dialog.tsx:161-177` | Ustada ~30 maydon |
| `ui/select.tsx` (native `<select>` + fokus uslubi) | `audit-filters.tsx:192-213`, `create-user-dialog.tsx:217-227` — bir xil class satri | Zona/toifa/holat tanlovlari |
| `ui/badge.tsx` (`tone` propi bilan) | `user-list.tsx:345-364` — lokal funksiya | Rasta holati, import natijasi, qadam holati |
| `ui/skeleton.tsx` | `app/[locale]/(app)/layout.tsx:95-96` — ichki `animate-pulse` | §9 yuklanish kontrakti |
| `ui/empty-state.tsx` (sarlavha + tavsif + amal) | Yo'q — hozir yalang'och `<p>` (`user-list.tsx:99`) | 9 ta bo'sh holat (§10.4) |
| `ui/confirm-dialog.tsx` (2 daraja: oddiy / matn yozib tasdiqlash) | `user-list.tsx:260-343` — faqat oddiy daraja | 5 ta destruktiv amal (§10.6) |
| Stepper (usta qadam relsi) | Yo'q | §6 |
| Fayl tanlash zonasi (`import/import-dropzone.tsx`) | Yo'q | §8.4 |

**QILINMAYDI:** `<table>` primitivi, virtualizatsiya kutubxonasi, drag-drop, chart kutubxonasi. Sabablar §12 da.

### 1.3 shadcn darvozasi — natija

**`components.json` topilmadi** [O'LCHANDI: `find /e/bozor -maxdepth 3 -name components.json` → 0 natija].

**Qaror: `Tool: none`. shadcn init BAJARILMAYDI.** [QAROR]

Sabablar (uchalasi ham qat'iy cheklov, did masalasi emas):

1. **Yangi bog'liqlik taqiqi.** `02-RESEARCH.md` §Standard Stack: *"Frontendga yangi paket QO'SHILMAYDI."* `shadcn init` `tw-animate-css` va `components.json` keltiradi va `package.json` ni o'zgartiradi.
2. **`@theme` bloki ustidan yozilardi.** `shadcn init` Tailwind 4 rejimida `globals.css` ga **o'z token nomlarini** (`--background`, `--foreground`, `--primary`, `--muted`…) yozadi. 1-faza esa `--color-bg`, `--color-surface`, `--color-text`, `--color-accent` nomlarini o'rnatgan va **70 ta joyda** ishlatgan. Ikki token to'plami yonma-yon yashab, dizayn tizimi ikkiga bo'linardi.
3. **Foydalanuvchidan so'rab bo'lmaydi.** Bu subagent kontekstida interaktiv savol vositasi yo'q; darvoza "so'rab, N javobini olish" o'rniga hujjatlashtirilgan qaror bilan yopiladi.

**Oqibat:** `Registry Safety` darvozasi **qo'llanmaydi** — uchinchi tomon registri yo'q, `npx shadcn add` bu fazada ishlatilmaydi (§13).

**Qachon qayta ko'riladi:** agar loyiha keyinchalik shadcn'ga o'tsa, o'tish `@theme` nomlarini shadcn konvensiyasiga ko'chirish migratsiyasi sifatida alohida rejalashtiriladi — faza o'rtasida emas.

### 1.4 Yangi bog'liqlik so'rovi

**YO'Q.** Bu fazaning uchala yuzasi ham mavjud paketlar bilan quriladi:

| Ehtiyoj | Mavjud yechim | Nega yangi paket kerak emas |
|---------|---------------|------------------------------|
| Usta qadam holati | `nuqs@2.9.2` (URL) + `@tanstack/react-query@5.101.4` (server holati) | Holat serverda (RESEARCH Pattern 5) — klient store kerak emas |
| Forma + validatsiya | `react-hook-form@7.83.0` + `zod@4.4.3` + `@hookform/resolvers@5.5.7` | — |
| Rasta kartasi / tasdiq | `@radix-ui/react-dialog@1.1.15` | Fokus tuzog'i, Esc, `aria-modal` tayyor |
| Plan-xarita (1000 katak) | CSS Grid + `React.memo` | RESEARCH Pattern 11: react-konva **RAD ETILDI** (SSR yo'q, a11y yo'q, drag kerak emas) |
| Jadval virtualizatsiyasi | Kerak emas — keyset + 50 qatorli sahifa | 1000 statik tugma virtualizatsiyani talab qilmaydi (Pattern 11) |
| Xabar / toast | `sonner@2.0.7` | O'rnatilgan |
| Ikonkalar | `lucide-react@1.27.0` | — |

> **`react-leaflet` TAQIQLANGAN** (Hippocratic-2.1, CLAUDE.md) — bu fazada baribir kerak emas, xarita geografik emas, sxematik.

---

## 2. Spacing Scale

E'lon qilingan qiymatlar (barchasi 4 ning karrali):

| Token | Qiymat | Tailwind | Ishlatilishi |
|-------|--------|----------|--------------|
| `xs` | 4px | `1` | Ikonka–matn oralig'i, badge ichki `y` |
| `sm` | 8px | `2` | Yorliq↔maydon, xarita kataklari orasi, badge ichki `x` |
| `md` | 12px | `3` | Ro'yxat elementlari orasi, tugma ichki `x` |
| `lg` | 16px | `4` | Karta ichki, forma maydonlari orasi |
| `xl` | 24px | `6` | Bo'lim oralig'i, sahifa `y` |
| `2xl` | 32px | `8` | Katta bo'lim uzilishi (usta qadamlari orasi) |
| `3xl` | 48px | `12` | Sahifa darajasidagi oraliq |

**Hujjatlashtirilgan istisnolar** (qat'iy sabab bilan, boshqasi yo'q):

| Qiymat | Qayerda | Sabab |
|--------|---------|-------|
| **44px** (`min-h-11` / `min-w-11`) | Barcha barmoq nishonlari: `Button size="lg"`, xarita katagi, mobil nav elementi, checkbox yorlig'i | WCAG 2.5.5 (AAA) va Apple HIG minimal nishon. `Button lg` va `RoleCheckbox` da allaqachon [KOD: `button.tsx:32`, `create-user-dialog.tsx:275`] |
| **56px** (`min-h-14`) | Mobil pastki navigatsiya | Mavjud [KOD: `app-shell.tsx:104`] |
| **20px** (`5`) | `CardHeader`/`CardContent` ichki `x` | Mavjud [KOD: `card.tsx:26,33`]; 4 ning karrali, saqlanadi |

**Chiqarib tashlanadi (Wave 0, mexanik):** [O'LCHANDI: 21 ta hodisa]

| Qiymat | Hodisa | Almashtiriladi |
|--------|--------|----------------|
| `gap-1.5` / `py-1.5` (6px) | 10 ta | `gap-2` (8px) |
| `gap-2.5` / `px-2.5` (10px) | 3 ta | `gap-2` / `px-2` (8px) |
| `gap-0.5` / `p-0.5` / `py-0.5` / `mt-0.5` (2px) | 4 ta | `gap-1` / `p-1` / `py-1` (4px) |

Sabab: 6px va 10px 4-panjaraga tushmaydi va ular hech qanday o'lchangan ehtiyojni qondirmaydi — ular "biroz torroq" degan bir martalik qarorlar. 2-faza spacing qarorlari sonini ~3× oshiradi; panjarani hozir tozalash keyingi 9 ekranda takrorlanishini oldini oladi.

---

## 3. Typography

**Shrift steki o'zgarmaydi** [KOD: `globals.css:14-18`] — `ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", Inter, …`. Tizim shrifti uchala yozuvni (lotin, kirill, rus) ham qamraydi va tarmoqdan yuklanmaydi (Karmana internet sifati). `--font-mono` kod ko'rsatkichi uchun.

### 3.1 E'lon qilingan shkala — 4 o'lcham, 2 og'irlik

| Rol | O'lcham | Og'irlik | Line-height | Tailwind |
|-----|---------|----------|-------------|----------|
| **Display** — sahifa sarlavhasi (`<h1>`) | 24px | 600 semibold | 1.25 | `text-2xl font-semibold tracking-tight leading-tight` |
| **Heading** — bo'lim / dialog / karta sarlavhasi | 18px | 600 semibold | 1.375 | `text-lg font-semibold leading-snug` |
| **Body** — barcha matn, yorliq, boshqaruv elementi | 14px | 400 regular | 1.5 | `text-sm leading-normal` |
| **Meta** — badge, yordamchi matn, vaqt belgisi | 12px | 400 regular | 1.33 | `text-xs` |

**Urg'u** Body/Meta ichida: **o'lcham o'zgarmaydi, faqat og'irlik 600 ga chiqadi.** Rang bilan urg'u berilmaydi (§4.3).

**Hujjatlashtirilgan istisno:** `font-mono text-xl` (20px) — **faqat** ko'chiriladigan kod ko'rsatkichi uchun: vaqtinchalik parol [KOD: `temp-password-dialog.tsx:73`] va rasta kartasidagi rasta raqami (§7.6). Sabab: bu qiymatlar o'qib aytiladi yoki nusxa olinadi, ular tipografik ierarxiyaning bir qismi emas.

### 3.2 Retire qilinadi (Wave 0, mexanik) [O'LCHANDI: kodbaza sanog'i]

| Nima | Hodisa | Nega | Almashtiriladi |
|------|--------|------|----------------|
| `font-medium` (500) | **22** | 500 va 600 14px'da amalda farqlanmaydi — ikkitasi ham "urg'u" degan ma'noni beradi, ya'ni har safar tanlash kerak bo'ladi va tanlov tasodifiy chiqadi | `font-semibold` |
| `text-base` (16px) | **4** | 14px va 16px orasidagi farq ierarxiya bermaydi; 4 ta hodisa (`Button lg`, 2 ta karta sarlavhasi) | `text-sm` (`Button lg` da) / `text-lg` (karta sarlavhasida) |

`text-xl` (1 hodisa) **saqlanadi** — u yuqoridagi `font-mono` istisnosi.

### 3.3 iOS avtomatik kattalashtirish — o'lchangan defekt va tuzatish

**Muammo:** iOS Safari fokusdagi forma elementining shrifti 16px'dan kichik bo'lsa sahifani **avtomatik kattalashtiradi**. `Input` `text-sm` = 14px [KOD: `input.tsx:19`], `<select>` ham `text-sm` [KOD: `audit-filters.tsx:205`]. Loyiha telefon-birinchi (bozor admini va kassir telefonda ishlaydi — PROJECT.md).

**RAD ETILGAN tuzatish:** `<meta viewport maximum-scale=1>` — WCAG 1.4.4 (Resize Text) ni buzadi va pinch-zoom'ni o'ldiradi. Loyihada `viewport` eksporti yo'q [O'LCHANDI], ya'ni Next 16 standarti (`initial-scale=1`, `maximum-scale` yo'q) amal qiladi — bu to'g'ri va shunday qoladi.

**QABUL QILINGAN tuzatish** — `globals.css` `@layer base` ga bitta qoida:

```css
/* iOS Safari 16px'dan kichik forma elementiga fokuslanganda sahifani
   kattalashtiradi. Pinch-zoom'ni o'ldirmasdan (WCAG 1.4.4) faqat
   barmoq bilan boshqariladigan qurilmalarda shriftni 16px qilamiz. */
@media (pointer: coarse) {
  input, select, textarea { font-size: 1rem; }
}
```

Narxi: nol churn, nol bog'liqlik, desktopdagi 14px zichligi saqlanadi.

---

## 4. Color

### 4.1 60/30/10 taqsimoti

| Rol | Token | Qiymat | O'lchangan sRGB | Ishlatilishi |
|-----|-------|--------|------------------|--------------|
| **Dominant (60%)** | `--color-bg` | `oklch(0.985 0 0)` | `#fafafa` | Sahifa foni |
| **Ikkilamchi (30%)** | `--color-surface` | `oklch(1 0 0)` | `#ffffff` | Kartalar, dialog, header, yon panel, xarita katagi |
| | `--color-surface-muted` | `oklch(0.968 0 0)` | `#f4f4f4` | Bosilgan/faol nav, ta'mirdagi rasta, skeleton |
| **Aksent (10%)** | `--color-accent` | **`oklch(0.56 0.19 255)`** ⚠ o'zgaradi | `#0071e0` | §4.3 ro'yxati |
| **Destruktiv** | `--color-danger` | `oklch(0.58 0.21 27)` | `#db2c2b` | **Faqat** destruktiv amal tugmasi foni |

Neytral shkala butunlay xromasiz (`C = 0`) — bu ataylab: Apple-uslub minimalizmda ierarxiya **bo'sh joy va tipografiya** bilan beriladi, rang esa faqat harakat va xavf uchun saqlanadi.

### 4.2 O'LCHANGAN WCAG AA buzilishlari va MAJBURIY token tuzatishlari

Bu sessiyada 1-faza tokenlarining kontrast nisbatlari OKLCH → sRGB → nisbiy yorqinlik yo'li bilan hisoblandi. **Oltita buzilish topildi.** Ular 2-fazada tuzatilishi shart, chunki 2-faza aynan shu tokenlarni ishlatadigan yuzani ~3× kengaytiradi.

| # | Nima | Hozirgi qiymat | **O'lchangan** | Talab | Tuzatish | **Tuzatishdan keyin** |
|---|------|----------------|----------------|-------|----------|------------------------|
| **C-01** | Oq matn `--color-accent` fonida (birlamchi tugma, `text-sm`) | `oklch(0.58 0.19 255)` | **4.36:1** ❌ | 4.5:1 (AA, 14px normal) | `--color-accent: oklch(0.56 0.19 255)` | **4.72:1** ✅ |
| **C-02** | `--color-text-muted` `--color-surface-muted` fonida | `oklch(0.556 0 0)` | **4.31:1** ❌ | 4.5:1 | `--color-text-muted: oklch(0.53 0 0)` | **4.81:1** ✅ |
| **C-03** | `--color-border` boshqaruv elementi chegarasi sifatida (Input, Select, xarita katagi) | `oklch(0.916 0 0)` | **1.28:1** ❌ | 3:1 (WCAG 2.2 SC 1.4.11 Non-text Contrast) | **yangi** `--color-border-ui: oklch(0.62 0 0)` | **3.64:1** (surface), **3.49:1** (bg), **3.32:1** (surface-muted) ✅ |
| **C-04** | `text-danger` `bg-danger/12` fonida (xato bloki, badge) | `oklch(0.58 0.21 27)` | **3.97:1** ❌ | 4.5:1 | **yangi** `--color-danger-text: oklch(0.50 0.19 27)` | **5.52:1** ✅ |
| **C-05** | `text-success` `bg-success/12` fonida (badge) | `oklch(0.63 0.16 150)` | **2.87:1** ❌ | 4.5:1 | **yangi** `--color-success-text: oklch(0.48 0.14 150)` | **5.34:1** ✅ |
| **C-06** | `text-accent` `bg-accent/10` fonida (audit manba badge) | `oklch(0.58 0.19 255)` | **3.82:1** ❌ | 4.5:1 | **yangi** `--color-accent-text: oklch(0.50 0.18 255)` | **5.31:1** ✅ |

Qo'shimcha: `--color-warning` (`oklch(0.78 0.15 85)`) matn sifatida oq fonda **2.02:1** — falokat. Hozir u faqat fon sifatida ishlatiladi (`bg-warning/20 text-text` = **15.63:1** ✅). Kontrakt: **`--color-warning` hech qachon matn rangi bo'lmaydi**; kerak bo'lsa **yangi** `--color-warning-text: oklch(0.50 0.11 85)` (`bg-warning/20` fonida **5.28:1** ✅).

**`globals.css` `@theme` bloki uchun aniq diff (Wave 0, BLOKLOVCHI):**

```css
  /* ---- Neytral kulrang shkala ----------------------------------------- */
  --color-border: oklch(0.916 0 0);          /* dekorativ ajratkich — o'zgarmaydi */
  --color-border-ui: oklch(0.62 0 0);        /* YANGI: interaktiv element chegarasi (WCAG 1.4.11, 3.64:1) */
  --color-text-muted: oklch(0.53 0 0);       /* 0.556 -> 0.53  (surface-muted da 4.31 -> 4.81) */

  /* ---- Bitta aksent rang ---------------------------------------------- */
  --color-accent: oklch(0.56 0.19 255);      /* 0.58 -> 0.56  (oq matn 4.36 -> 4.72) */
  --color-accent-text: oklch(0.50 0.18 255); /* YANGI: aksent MATNI tint fonida (5.31:1) */

  /* ---- Semantik holat ranglari ---------------------------------------- */
  --color-success-text: oklch(0.48 0.14 150); /* YANGI (5.34:1) */
  --color-warning-text: oklch(0.50 0.11 85);  /* YANGI (5.28:1) */
  --color-danger-text:  oklch(0.50 0.19 27);  /* YANGI (5.52:1) */
```

**`--color-border` vs `--color-border-ui` ajratmasining qoidasi:**
- `--color-border` (1.28:1) — **faqat dekorativ**: karta konturi, ajratkich chiziq, panel chegarasi. WCAG 1.4.11 dekorativ chegaraga qo'llanmaydi.
- `--color-border-ui` (3.64:1) — **majburiy**: `Input`, `<select>`, `textarea`, xarita katagi, checkbox, tanlanadigan qator, ya'ni chegarasi elementni "boshqaruv elementi" sifatida tanitadigan har narsa.

Migratsiya: `input.tsx:19`, `audit-filters.tsx:205`, `create-user-dialog.tsx:218,275` — `border-border` → `border-border-ui` (≈6 hodisa).

### 4.3 Aksent nima uchun saqlangan (aniq ro'yxat)

Aksent rang **faqat** quyidagilarda ishlatiladi. "Barcha interaktiv elementlar" — **YO'Q**.

1. **Birlamchi tugma foni** — sahifada **eng ko'pi bilan bitta** (`Button variant="default"`). Ustada bu "Keyingi qadam", oxirgi qadamda "Bozorni faollashtirish".
2. **Fokus halqasi** (`:focus-visible outline`) — barcha interaktiv elementlar uchun. [KOD: `globals.css:70-73`]
3. **Faol maydon chegarasi va halqasi** (`focus-visible:border-accent`, `ring-accent/25`). [KOD: `input.tsx:21`]
4. **Joriy navigatsiya elementi** — faqat mobil pastki panelda (`text-accent`). [KOD: `app-shell.tsx:105`] Desktop yon panelda faol element `bg-surface-muted` bilan belgilanadi, rang bilan emas.
5. **Ustadagi joriy qadam ko'rsatkichi** — qadam raqami doirasi (`bg-accent text-accent-fg`).
6. **Checkbox/radio `accent-color`**. [KOD: `create-user-dialog.tsx:280`]

**Aksent ishlatilMAYDIGAN joylar (aniq taqiq):** havolalar (ular `underline` bilan belgilanadi), badge matni (agar `--color-accent-text` bilan bo'lmasa), xarita kataklari (§7.4), jadval sarlavhalari, ikonkalar (agar tugma ichida bo'lmasa).

### 4.4 Rang hech qachon YAGONA signal emas

WCAG 1.4.1 (Use of Colour). Bu fazada rangdan tashqari kanal **majburiy** bo'lgan joylar:

| Holat | Rang kanali | Qo'shimcha kanal 1 | Qo'shimcha kanal 2 |
|-------|-------------|--------------------|--------------------|
| Rasta: faol | to'ldirish `surface` | **uzluksiz** chegara | matn og'irligi 600 |
| Rasta: sotuvchisiz | to'ldirish `surface` | **uzuq-uzuq (dashed)** chegara | `aria-label` da "sotuvchisiz" |
| Rasta: ta'mirda | to'ldirish `surface-muted` | `Wrench` ikonkasi (12px) | matn `text-muted` |
| Rasta: yopiq | to'ldirish `surface-muted` | `Ban` ikonkasi (12px) | matn `line-through` |
| Usta qadami: bajarilgan | — | `Check` ikonkasi | `aria-label` da "bajarilgan" |
| Usta qadami: bloklangan | — | `Lock` ikonkasi | `aria-disabled="true"` + sabab matni |
| Maydon xatosi | `text-danger-text` | `aria-invalid="true"` | Maydon ostidagi matn |
| Import: xato / muvaffaqiyat | tint fon | `AlertCircle` / `CheckCircle2` | Sarlavha matni raqam bilan |

---

## 5. Uch tilli matn kontrakti (uz-Latn / uz-Cyrl / ru)

### 5.1 O'LCHANGAN uzunlik — prompt taxminining tuzatilishi

Prompt "kirill lotindan ~10–15% uzunroq, rus ~20–30% uzunroq" deb taxmin qilgan. **Mavjud 120 ta kalitda o'lchandi — bu noto'g'ri:**

| Juftlik | **O'lchangan nisbat** | Izoh |
|---------|------------------------|------|
| uz-Cyrl / uz-Latn | **0.948** (≈5% **QISQAROQ**) | O'zbek lotini digraf ishlatadi (`sh`→ш, `ch`→ч, `o'`→ў, `g'`→ғ) — kirillcha har digrafni bitta harfga siqadi |
| ru / uz-Latn | **0.985** (≈1.5% qisqaroq) | O'rtacha bo'yicha teng |

**Lekin o'rtacha yolg'on tinchlantiradi — ayrim kalitlar 2× ga cho'ziladi:**

| Kalit | uz-Latn | uz-Cyrl | ru | ru/uz |
|-------|---------|---------|-----|-------|
| `audit.sourceApp` | "Ilova" (5) | (5) | "Приложение" (10) | **2.00×** |
| `users.statusActive` | "Faol" (4) | (4) | "Активен" (7) | **1.75×** |
| `users.block` | "Bloklash" (8) | (7) | "Заблокировать" (13) | **1.63×** |
| `roles.marketAdmin` | "Bozor admini" (12) | (12) | "Администратор рынка" (19) | **1.58×** |

**Kontrakt [QAROR]:**

1. **Hech qanday matn saqlovchi konteynerda qat'iy kenglik yo'q.** Tugma — `whitespace-nowrap` + tabiiy kenglik (mavjud [KOD: `button.tsx:12`]); qator — `flex-wrap`; ustun — `minmax(0,1fr)`, `w-*` emas.
2. **Qisqa yorliqlar eng ko'p 2× o'sishga chidashi kerak.** Amaliy tekshiruv: rus tilida ekran ochilganda birorta tugma yorlig'i ikki qatorga tushmasligi va birorta badge kesilmasligi kerak. Bu **UAT bandiga** aylanadi, taxminga emas.
3. **Badge va status yorliqlari `truncate` QILINMAYDI** — ular ma'no tashiydi. Ular o'rniga konteyner o'sadi.
4. **Faqat DB kontenti `truncate` bo'ladi** (bozor nomi, sotuvchi ismi, zona nomi) va u doim `title` atributi bilan birga. Mavjud naqsh [KOD: `user-list.tsx:158`, `app-shell.tsx:61`].
5. **Ikonka + matn tugmalari** ikonkani hech qachon yo'qotmaydi — rus tilida matn uzun bo'lsa tugma o'sadi, ikonka olib tashlanmaydi.

### 5.2 O'LCHANGAN transliterator defektlari — MAJBURIY overrides

`uz-Cyrl.json` **avtomatik hosil qilinadi** [MEROS: 1-faza D-14]. Yagona qo'lda tahrirlanadigan kirill fayli — `messages/uz-Cyrl.overrides.json`. 46 ta nomzod matn transliteratordan o'tkazildi. **To'rtta jimgina buziladigan defekt topildi:**

| # | Kirish | **Chiqish (buzuq)** | Muammo |
|---|--------|---------------------|--------|
| **T-01** | `Excel'dan yuklash` | `Эхcэлъдан юклаш` | "Excel" so'zma-so'z transliteratsiya bo'ladi **va ichida lotin `c` qoladi** (aralash yozuv); apostrof `ъ` ga aylanadi |
| **T-02** | `.xlsx fayl` | `.хлсх файл` | Fayl kengaytmasi transliteratsiya bo'ladi — ma'nosiz |
| **T-03** | `Filtrga mos rasta topilmadi` | `Филтрга…` | Mavjud override faqat `filtr/filtrlar/filtrlarni/filtrlash` shakllarini qamragan; o'zbekcha agglyutinativ — har qo'shimchali shakl alohida yozuv talab qiladi. To'g'risi `Фильтрга` |
| **T-04** | `Excel qilib yuklab olish` | `Эхcэл қилиб…` | T-01 bilan bir xil |

**Tuzatish 1 — `uz-Cyrl.overrides.json` `words` ga qo'shiladi** (Wave 0):

```json
"Excel": "Excel",
"xlsx": "xlsx",
"filtrga": "фильтрга",
"filtrni": "фильтрни",
"filtrdan": "фильтрдан"
```

**Tuzatish 2 — copy qoidasi (override yetarli emas!):** `Excel` overridedan keyin ham `Excel'dan` **buzuq qoladi** — [O'LCHANDI: override bilan ham `Эхcэлъдан`], chunki apostrofli shakl boshqa token. Shuning uchun:

> **QOIDA: `Excel` so'zi hech qachon apostrofli qo'shimcha bilan yozilmaydi.**
> ❌ `Excel'dan yuklash` → ✅ **`Excel fayldan yuklash`** [O'LCHANDI: → `Excel файлдан юклаш` ✅]
> ❌ `.xlsx fayl` → ✅ **`xlsx fayl`** [O'LCHANDI: → `xlsx файл` ✅]

**Tekshiruv darvozasi:** `npm run i18n:check` kalit-parity **va** ICU-argument parity'ni tekshiradi, lekin **transliteratsiya sifatini tekshirmaydi**. Shu sababli 2-faza `frontend/scripts/gen-cyrillic.test.mjs` ga yuqoridagi 4 ta holat uchun assertion qo'shadi — aks holda defekt keyingi fazada jimgina qaytadi.

**Ijobiy tasdiq:** ICU platsholderlar transliteratsiyadan **buzilmasdan** o'tadi [O'LCHANDI: `{count, plural, one {# ta xato} other {# ta xato}}` → `{count, plural, one {# та хато} other {# та хато}}`].

### 5.3 Til bo'yicha mas'uliyat taqsimoti

| Fayl | Kim yozadi | 2-fazada |
|------|-----------|----------|
| `messages/uz-Latn.json` | **Qo'lda — manba** | ~120 yangi kalit |
| `messages/ru.json` | **Qo'lda** | ~120 yangi kalit (§10 da berilgan) |
| `messages/uz-Cyrl.json` | **Avtomatik** (`npm run i18n:gen`) | Qo'l tegizilmaydi |
| `messages/uz-Cyrl.overrides.json` | **Qo'lda** | §5.2 dagi 5 ta yangi so'z |

**DB kontenti tarjima QILINMAYDI** [MEROS: 1-faza D-16]: zona nomi, toifa nomi, sotuvchi F.I.Sh., bozor nomi, rasta izohi. Ular `dir`/`lang` atributisiz, qanday kiritilgan bo'lsa shunday ko'rinadi. Har bunday joyda kod izohi majburiy — mavjud naqsh [KOD: `user-list.tsx:157`].

---

## 6. Yuza 1 — "Yangi bozor" ustasi (MARKET-01, SC#1)

### 6.1 Arxitektura kontrakti [MEROS: RESEARCH Pattern 5]

**Usta holatsiz.** Klientda katta forma holati **saqlanmaydi**. Haqiqat manbai — DB'dagi qoralama bozor (`markets.is_active = false`) va hisoblanadigan `GET /api/v1/markets/{id}/setup-status`.

| Nima | Qayerda yashaydi |
|------|------------------|
| Bajarilgan qadamlar | Server — `setup-status` javobi (hisoblanadi, saqlanmaydi) |
| Joriy qadam raqami | URL — `?step=N` (`nuqs`), **faqat ko'rinish** |
| Qadam formasining vaqtinchalik qiymatlari | `react-hook-form` — **faqat o'sha qadam ochiq bo'lgan vaqtda** |
| Qoralama bozor identifikatori | Access token (`mid`) — `POST /auth/select-market` dan keyin |

**Marshrutlar [QAROR]:**

| Marshrut | Vazifa |
|----------|--------|
| `/[locale]/(app)/markets/new` | **Faqat 1-qadam.** Hali `market_id` yo'q, ya'ni `?step` ham yo'q |
| `/[locale]/(app)/markets/setup?step=N` | 2–7-qadamlar. Bozor tokendan olinadi |

Nega ikkita marshrut: 1-qadamgacha tenant konteksti mavjud emas (`app.market_id` bo'sh). `POST /markets` → `POST /auth/select-market` → `router.replace('/markets/setup?step=2')`. Bitta marshrutga sig'dirish "market_id bormi?" degan shartni har render'da takrorlashni talab qilardi.

### 6.2 Qadamlar va ularning bog'liqlik tartibi

| # | Qadam | uz-Latn / ru | Bloklovchi shart | Shakl |
|---|-------|--------------|------------------|-------|
| 1 | Rekvizitlar | Rekvizitlar / Реквизиты | — | Forma |
| 2 | Zonalar | Zonalar / Зоны | 1-qadam | Ro'yxat + inline qo'shish |
| 3 | Toifalar | Toifalar / Категории | 1-qadam | Ro'yxat + inline qo'shish |
| 4 | Tariflar | Tariflar / Тарифы | **3-qadam ≥1 toifa** | Ro'yxat (toifa × sana × summa) |
| 5 | Rastalar | Rastalar / Торговые места | **2 va 3-qadam** | Import + ro'yxat |
| 6 | Sotuvchilar *(ixtiyoriy)* | Sotuvchilar / Продавцы | **5-qadam ≥1 rasta** | Import + ro'yxat |
| 7 | Ish kunlari va faollashtirish | Ish kunlari / Рабочие дни | 1-qadam | Forma + istisno ro'yxati + faollashtirish paneli |
| — | Kamera *(keyinroq)* | Kamera (keyinroq) / Камеры (позже) | **Doim `aria-disabled`** | Yo'q — §6.7 |

**Tartib did emas, bog'liqlik:** toifa tarifdan oldin (FK `tariffs → stall_categories`), zona+toifa rastadan oldin (import ularni **nom bo'yicha** qidiradi), rasta sotuvchidan oldin (`stall_assignments` FK). Stepper buni ko'rsatishi shart, aks holda admin 4-qadamda "nega bo'sh?" deb qoladi.

**6-qadam IXTIYORIY** — `activate` to'liqlik tekshiruvi sotuvchi talab qilmaydi [MEROS: RESEARCH Pattern 5; D-11 sotuvchisiz rastani anomaliya deb belgilaydi, taqiq emas]. Stepper'da u "ixtiyoriy" yorlig'i bilan ko'rsatiladi va `blocking[]` ga hech qachon tushmaydi. Bu **majburiy**: aks holda admin o'zini bloklangan deb o'ylaydi.

### 6.3 Stepper — to'rt holat, uch kanal

Uchta emas, **to'rtta** holat kerak (prompt uchtasini nomlagan, lekin "ochiq-lekin-bo'sh" alohida ma'no):

| Holat | Vizual | Ikonka | ARIA | Havolami? |
|-------|--------|--------|------|-----------|
| **Bajarilgan** | `bg-surface` + `border-border-ui`, raqam o'rnida ikonka | `Check` | `aria-label="{n}-qadam: {nom} — bajarilgan"` | ✅ `<Link>` |
| **Joriy** | `bg-accent text-accent-fg` doira | raqam | `aria-current="step"` | ❌ (o'zi) |
| **To'ldirilmagan** | `bg-surface` + `border-border-ui`, raqam `text-muted` | raqam | `aria-label="{n}-qadam: {nom} — to'ldirilmagan"` | ✅ `<Link>` |
| **Bloklangan** | `bg-surface-muted`, raqam o'rnida ikonka | `Lock` | `aria-disabled="true"` + `aria-describedby` → sabab | ❌ `<span>` |

**Bloklangan qadam sababi ko'rinadi, yashirilmaydi.** Stepper elementi ostida (desktop) yoki bosilganda (mobil) `text-xs text-text-muted`: "Avval toifa qo'shing" / "Сначала добавьте категорию". Sababsiz bloklangan qadam — foydalanuvchini boshi berk ko'chaga olib boradi.

**Joylashuv:**
- Desktop (`md:`) — chap tomonda vertikal rels (`w-56`), asosiy kontent yonida. `sticky top-20`.
- Mobil — gorizontal, `overflow-x-auto snap-x`, joriy qadam markazga `scrollIntoView({block:'nearest', inline:'center'})` bilan keladi. Har element `min-w-11 min-h-11`.

**Progress e'lon qilinadi:** stepper ustida `role="status"` bilan bitta qator — "7 qadamdan {done} tasi bajarilgan" / "Выполнено {done} из 7 шагов". Skrinrider foydalanuvchisi 7 ta elementni sanab chiqmasligi kerak.

### 6.4 Orqaga qaytish va uzilishdan tiklanish

**Orqaga qaytish erkin.** Har bir bajarilgan/to'ldirilmagan qadam haqiqiy `<Link href="?step=N">`. Ogohlantirish dialogi **YO'Q** — holat serverda, ya'ni qaytishda yo'qoladigan narsa yo'q. (Yagona istisno: forma ichida saqlanmagan o'zgarish bo'lsa — §6.5.)

**Uzilishdan tiklanish [QAROR]:**

1. Foydalanuvchi qaytib kelganda **bozor tanlash ekranini** ko'radi.
2. Qoralama bozorlar u yerda **`Qoralama` badge**i bilan ko'rinadi.
3. Bosilganda: `select-market` → `setup-status` → `router.replace('/markets/setup?step=' + firstIncompleteStep)`.
4. **`firstIncompleteStep` = `blocking[]` dagi eng kichik qadam raqami**, "oxirgi ochilgan qadam" emas. Klientda hech qanday xotira yo'q — bu Pattern 5 ning to'g'ridan-to'g'ri natijasi.

> ⚠ **O'LCHANGAN to'siq — bu oqim BUGUN ishlamaydi va tuzatish 6 fayldan iborat zanjir.**
>
> Qoralama bozor bozor tanlash ekraniga **umuman yetib bormaydi**: u serverda kesiladi va `is_active` maydoni javob sxemasida **umuman yo'q**. Ya'ni faqat frontend filtrini olib tashlash **hech narsani o'zgartirmaydi** — vazifa "bajarildi" deb yopiladi, oqim esa hamon ishlamaydi va UAT'da qaytadan chiqadi.
>
> To'liq zanjir — §12.1.1 (6 band, tartib majburiy: DB → backend → tip → UI). Xavfsizlik ta'siri — §12.1.1 dagi X-1…X-4.

### 6.5 Saqlash va fikr-mulohaza (feedback)

**Ikki xil qadam shakli:**

| Shakl | Qadamlar | Saqlash | Fikr-mulohaza |
|-------|----------|---------|---------------|
| **Forma qadami** | 1, 7 | Aniq "Saqlash va davom etish" tugmasi | Tugma `disabled` + matni "Saqlanmoqda"; muvaffaqiyatda **keyingi qadamga o'tish** (toast **YO'Q** — navigatsiyaning o'zi tasdiq) |
| **Ro'yxat qadami** | 2, 3, 4, 5, 6 | Har element qo'shilganda darhol | `sonner` toast: "Zona qo'shildi" + ro'yxat darhol yangilanadi (optimistik emas — server javobidan) |

**Avtomatik saqlash (autosave) YO'Q** [QAROR]. Sabab: 1-qadam `market_create()` chaqiradi va **qoralama bozor tug'diradi**. Autosave har terilgan harfda tashlab ketilgan qoralama yaratardi. Ro'yxat qadamlarida esa har element allaqachon atomik — autosave qo'shadigan narsa yo'q.

**Saqlanmagan o'zgarish himoyasi:** faqat **forma qadamlarida** (1, 7) va faqat `formState.isDirty` bo'lsa — qadamdan chiqishda `ui/confirm-dialog` 1-daraja: "Saqlanmagan o'zgarishlar bor. Chiqilsinmi?" / "Есть несохранённые изменения. Выйти?".

### 6.6 Faollashtirish — 409 xato emas, yo'l ko'rsatkichi

**Bu fazaning eng muhim UX qarori.** [QAROR]

Yakuniy panel (7-qadam) doimo **ikkita** narsani ko'rsatadi:

```
┌─ Bozorni ishga tayyorlash ──────────────────────────────┐
│                                                          │
│  ✓  Zonalar                                    4 ta      │
│  ✓  Toifalar                                   6 ta      │
│  ✓  Tariflar                          6 toifadan 6 ta    │
│  ✓  Rastalar                                 512 ta      │
│  ✗  Rasta toifalari              512 dan 498 tasi  →     │   ← havola, 5-qadamga
│  ✓  Ish kunlari                          Belgilangan     │
│  ·  Sotuvchilar (ixtiyoriy)                  380 ta      │
│  ·  Kamera (keyinroq ulanadi)                   —        │
│                                                          │
│  [ Bozorni faollashtirish ]                              │
└──────────────────────────────────────────────────────────┘
```

**Kontrakt:**

1. **Ro'yxat DOIM ko'rinadi** — `can_activate === true` bo'lganda ham. U "nima qoldi" emas, "bozor nimadan iborat" degan ma'noni beradi va faollashtirishdan oldin oxirgi ko'z yugurtirish imkonini beradi.
2. **Tugma `disabled` QILINMAYDI.** `can_activate === false` bo'lganda `aria-disabled="true"` + `variant="secondary"` bo'ladi. Sabab: `disabled` tugma fokus olmaydi, skrinrider uni o'qimaydi va "nega?" savoliga javob beradigan joy qolmaydi. `aria-disabled` esa fokuslanadi va e'lon qilinadi.
3. **Bosilganda** (`can_activate === false`): so'rov yuborilmaydi; fokus ro'yxatdagi **birinchi bajarilmagan** bandga ko'chadi va `role="status" aria-live="polite"` konteyner uni e'lon qiladi.
4. **Har bajarilmagan band — havola** o'sha qadamga. Bu "409 → yo'l ko'rsatkichi" tamoyilining amaliy shakli.
5. **Server 409 qaytarsa** (poyga holati: kimdir zonani o'chirdi) — javob tanasidagi `blocking[]` **shu ro'yxatni almashtiradi**, fokus birinchi bajarilmaganga ko'chadi. **Alohida xato UI'si yo'q** — bir xil render yo'li. Toast ham yo'q.
6. **Muvaffaqiyatda:** `sonner` toast "Bozor faollashtirildi" + `router.replace('/dashboard')`.

**Nima QILINMAYDI:** qizil xato bloki, `AlertTriangle` ikonkasi, "Xato: 409". Bozorning chala bo'lishi — normal ish jarayoni holati, nosozlik emas.

### 6.7 Kamera bo'limi (D-16) — "keyinroq", "chala" emas

D-16 aniq: usta kamerasiz yakunlanadi va **doimiy ogohlantirish banneri qo'yilmaydi**. Ayni paytda kamera bo'limi "ixtiyoriy bo'lim bo'lib turadi".

**Kontrakt [QAROR] — ikkita ko'rinish, ikkalasi ham neytral:**

1. **Stepper relsida 8-element:** `Kamera (keyinroq)` — `aria-disabled="true"`, `Camera` ikonkasi `text-text-muted`, havola emas. Bu tizim kameralarni "biladi" degan xabarni beradi va admin ularni izlab yurmaydi.
2. **Yakuniy panelda bitta neytral qator** (yuqoridagi chizmada `·` bilan).
3. **Yakuniy paneldan keyin bitta jumla** — oddiy `<p className="text-sm text-text-muted">`, **ramkasiz, fonsiz, ikonkasiz**.

**QAT'IY TAQIQ:** `AlertTriangle` / `AlertCircle` ikonkasi, `bg-warning/*` yoki `bg-danger/*` fon, `role="alert"`, "chala"/"tugallanmagan"/"e'tibor bering" so'zlari, sariq/qizil chegara. Ularning har biri D-16 ni buzadi.

**Matn (§10.2 da to'liq):**
> uz-Latn: «Kamera bo'limi keyinroq ulanadi. Bozor hozirdan to'liq ishlaydi: rasta, tarif va kunlik patta hisobi kamerasiz yuritiladi.»
> ru: «Камеры будут подключены позже. Рынок уже полностью работает: торговые места, тарифы и ежедневный учёт сбора ведутся без камер.»

### 6.8 Validatsiya xatolari qayerda ko'rinadi

Mavjud naqshni davom ettiradi [KOD: `create-user-dialog.tsx:174-176, 230-237`]:

| Xato turi | Joyi | ARIA | Misol |
|-----------|------|------|-------|
| **Maydon xatosi** (zod, klient) | Maydon **ostida**, `text-sm text-danger-text` | Maydonda `aria-invalid="true"` + `aria-describedby` | "Telefon raqami noto'g'ri kiritilgan" |
| **Forma xatosi** (server 4xx) | Forma **tepasida**, `role="alert"`, `bg-danger/10` + `text-danger-text` | `role="alert"` | "Bu telefon raqami shu bozorda allaqachon ro'yxatda" |
| **Faollashtirish to'siqlari** (409) | Yakuniy panel ro'yxati | `role="status"` (alert **emas**) | §6.6 |
| **Import xatolari** (422, ko'p) | Alohida panel | §8.5 | §8.5 |

**Yuborishdan keyingi fokus:** validatsiya yiqilsa fokus **birinchi noto'g'ri maydonga** ko'chadi (`setFocus` — react-hook-form). Server xatosi bo'lsa fokus forma tepasidagi `role="alert"` blokiga ko'chadi. Aks holda klaviatura foydalanuvchisi xatoni umuman topa olmaydi.

### 6.9 "≤3 bosish" qoidasi bu fazada qayerda qo'llanadi

CLAUDE.md "kassir oqimi ≤3 bosish" deydi — kassir oqimi 6-fazada. **2-fazaning majburiyati — uning poydevorini qo'yish** (D-01 rasta raqami bozor bo'yicha yagona, aynan shu maqsadda):

**Kontrakt:** rasta raqami bo'yicha topish **≤2 ta o'zaro ta'sirda** bo'lishi shart.

1. `/stalls` sahifasi ochilganda qidiruv maydoni **avtomatik fokusda** (`autoFocus`), `inputMode="numeric"`, `enterKeyHint="search"`.
2. Raqam terilib `Enter` bosilsa — **aynan bitta** natija bo'lsa rasta kartasi darhol ochiladi (ro'yxat oralig'i yo'q).
3. Xaritada ham xuddi shu: xarita tepasidagi qidiruv maydoni raqam bo'yicha katakni topadi, unga `scrollIntoView` qiladi va fokus beradi.

Bu bitta o'lchanadigan mezon: **kod terish + Enter = karta ochiq**. 6-fazaning "≤3 bosish"i shundan bitta bosishni oladi.

---

## 7. Yuza 2 — Sxematik plan-xarita va rasta kartasi (MARKET-06, SC#5)

### 7.1 Renderer texnologiyasi [MEROS: RESEARCH Pattern 11]

**CSS Grid + memoizatsiyalangan `<button>`. `react-konva` o'rnatilMAYDI.** Sabab RESEARCH da o'lchov bilan berilgan: statik render, drag yo'q, 1000 element bir martalik ~21 ms; Konva evaziga SSR, a11y va klaviatura yo'qolardi.

**Majburiy amalga oshirish qoidalari** (Pattern 11 dan, o'zgarishsiz):

1. Katak — **haqiqiy `<button type="button">`**.
2. Katak `React.memo` bilan; `onSelect` — `useCallback`.
3. **Tanlangan rasta katakning propiga TUSHMAYDI** — u sahifa holatida (`selectedStallId`) yashaydi va faqat `<Dialog>` uni o'qiydi. Aks holda har bosishda 1000 katak qayta render bo'ladi.
4. `key={stall.id}` — hech qachon `key={index}`.
5. Koordinata saqlanmaydi (D-19) — joylashuv hosila.

> **Qo'shimcha foyda (3-qoidadan):** tanlash katakni qayta render qilmagani uchun Radix Dialog yopilganda **fokus aynan bosilgan katakka qaytadi** (trigger DOM'da qolgan). Agar tanlangan ID katak propi bo'lganida, katak qayta render bo'lib fokus yo'qolardi.

### 7.2 Ma'lumot kontrakti va `tone` tipi (D-20 kengaytirilishi)

```ts
// frontend/src/components/stalls/stall-map-types.ts

/**
 * 2-fazada FAQAT birinchi uchtasi hosil qilinadi (D-20).
 * Qolgan uchtasi 6–7 fazalarda YONADI — tip hozir e'lon qilinadi,
 * uslub hozir YOZILMAYDI (Scope Fence).
 */
export type StallTone =
  | "neutral"    // faol, sotuvchisi bor
  | "muted"      // ta'mirda
  | "off"        // yopiq
  | "paid"       // 6-faza — to'langan
  | "debt"       // 6-faza — qarzdor
  | "mismatch";  // 7-faza — nomuvofiqlik

export type StallCell = {
  id: string;
  code: string;
  tone: StallTone;
  hasVendor: boolean;
};

export type ZoneBlock = {
  id: string;
  name: string;      // DB kontenti — TARJIMA QILINMAYDI (1-faza D-16)
  cells: StallCell[]; // inson-raqamli tartibda (§7.3)
};
```

**`tone` ni API hisoblamaydi — frontend `status` + `hasVendor` dan hosil qiladi** [MEROS: Pattern 11 qoida 4]:

```ts
// frontend/src/components/stalls/stall-tone.ts
export function toneOf(stall: { status: StallStatus }): StallTone {
  switch (stall.status) {
    case "active":      return "neutral";
    case "maintenance": return "muted";
    case "closed":      return "off";
  }
}
```

**Uslub xaritasi to'liq (exhaustive) `Record` bo'lishi SHART:**

```ts
const TONE_STYLES: Record<StallTone, string> = {
  neutral:  "...",
  muted:    "...",
  off:      "...",
  // 6–7 fazalar to'ldiradi. Hozircha neutral bilan bir xil —
  // ular hech qachon hosil qilinmaydi, lekin Record to'liqligi
  // 6-fazada kalit unutilsa TypeScript xatosini kafolatlaydi.
  paid:     "...",  // = neutral
  debt:     "...",  // = neutral
  mismatch: "...",  // = neutral
};
```

Sabab: `Record<StallTone, string>` kalit tushib qolsa **kompilyatsiya xatosi** beradi. `Partial<Record<...>>` yoki `switch` + `default` bo'lsa 6-faza `debt` uslubini yozishni unutib, jimgina `neutral` chizardi — bu esa qarzdor rastani "hammasi joyida" ko'rsatardi.

### 7.3 Tartib

| Nima | Tartib | Qayerda hal qilinadi |
|------|--------|----------------------|
| Zona bloklari | Zona nomi bo'yicha (`ORDER BY name`) | **Server.** Frontend qayta saralamaydi — server tartibi uchala UI tilida bir xil bo'lishi kerak, DB kontenti esa bitta tilda (1-faza D-16) |
| Katak (rasta) | **Inson-raqamli** (`2` < `10` < `100`) | **Server.** `code` — `text` ustuni, oddiy `ORDER BY code` "1, 10, 100, 11, 2" beradi |

> ⚠ Bu **jimgina buziladigan** narsa: raqamli tartib buzilsa xarita "ishlayotgandek" ko'rinadi, lekin rasta topib bo'lmaydi. Shuning uchun `stall-map.test.tsx` da majburiy assertion: `["2","10"]` tartibi saqlanadi.

### 7.4 Katak — o'lcham, matn sig'imi, holat kanallari

| Xususiyat | Qiymat | Sabab |
|-----------|--------|-------|
| Minimal o'lcham | **44 × 44 px** (`min-h-11 min-w-11`, `aspect-square`) | WCAG 2.5.5 + §2 istisnosi; `Button lg` bilan bir xil |
| Grid | `grid-template-columns: repeat(auto-fill, minmax(2.75rem, 1fr))` | D-19: koordinata yo'q, joylashuv hosila |
| Oraliq | `gap-2` (8px) | Fokus halqasi uchun joy (§7.5) |
| Radius | `--radius-sm` (8px) | Mavjud token |
| Matn | `text-sm tabular-nums` | Raqamlar tik ustunda tursin |

**Matn sig'imi qoidasi (uzun rasta raqami):**

| `code.length` | Uslub | Natija |
|---------------|-------|--------|
| 1–4 | `text-sm` (14px) | 44px ichiga sig'adi (~34px) |
| 5–6 | `text-xs` (12px) | ~40px — sig'adi |
| >6 | `text-xs truncate` + `title={code}` | Vizual kesiladi |

**`aria-label` HECH QACHON kesilmaydi** — u to'liq kodni o'z ichiga oladi. Karmanada kodlar 1–1000 (≤4 belgi), ya'ni >6 — degenerativ holat, lekin u jimgina buzilmasligi kerak.

**Holat kanallari (§4.4 ning amalga oshirilishi) — rang yagona signal emas:**

| Holat | Fon | Chegara | Ikonka | Matn |
|-------|-----|---------|--------|------|
| Faol + sotuvchi bor | `bg-surface` | `border border-border-ui` **uzluksiz** | — | `text-text font-semibold` |
| Faol + **sotuvchisiz** | `bg-surface` | `border border-dashed border-border-ui` | — | `text-text font-semibold` |
| Ta'mirda | `bg-surface-muted` | `border border-border-ui` | `Wrench` 12px, yuqori-o'ng | `text-text-muted` |
| Yopiq | `bg-surface-muted` | `border border-border-ui` | `Ban` 12px, yuqori-o'ng | `text-text-muted line-through` |

Rang (hue) **umuman ishlatilmaydi** — D-20 "faol (neytral), ta'mirda (kulrang), yopiq (o'chgan)" ni aynan shunday talqin qiladi va 6–7 fazalar uchun butun hue maydonini bo'sh qoldiradi.

**Legenda MAJBURIY.** Xarita ustida `<ul>` — har tone uchun namuna katak + yorliq. Aks holda "uzuq-uzuq chegara = sotuvchisiz" qoidasini hech kim topa olmaydi. Legenda mobil'da ham ko'rinadi (yig'ilmaydi).

**`aria-label` formati:**
```
"{code}-rasta, {holat}, {toifa}, {sotuvchi yoki 'sotuvchi biriktirilmagan'}"
→ "12-rasta, faol, Sabzavot, Karimov A."
→ "37-rasta, ta'mirda, Go'sht, sotuvchi biriktirilmagan"
```
Toifa va sotuvchi — DB kontenti, tarjima qilinmaydi.

### 7.5 Fokus, hover, active

| Holat | Uslub | Sabab |
|-------|-------|-------|
| `:focus-visible` | `outline: 2px solid var(--color-accent); outline-offset: 1px; z-index: 10` | Global qoida `offset: 2px` beradi; 8px oraliqda 2+2 = 4px ikki tomondan → halqalar tegib ketardi. **Katak uchun `offset-1`** → 3px, 2px zaxira. `z-10` halqa qo'shni katak ostida qolmasligi uchun |
| `:hover` | `border-color: var(--color-text-muted)` (4.81:1) | To'rtala tone'da ham ishlaydi — `hover:bg-surface-muted` "ta'mirda"/"yopiq" kataklarida ko'rinmasdi (ular allaqachon shu fonda) |
| `:active` | `scale-[0.97]` + `motion-reduce:scale-100` | Barmoq bilan bosishda tasdiq |
| Tanlangan (dialog ochiq) | `ring-2 ring-accent ring-offset-1` | Dialog yopilgach qaysi katak ochilgani ko'rinib turadi |

### 7.6 Rasta kartasi — Radix Dialog [QAROR]

**Tanlov: bitta modal `<Dialog>`, tanlangan ID sahifa holatida.**

Rad etilgan muqobillar va sabablari:

| Muqobil | Nega rad etildi |
|---------|------------------|
| Har katakka `<Popover>` | 1000 ta Radix portali (RESEARCH Anti-Patterns bandi). Zich gridda pozitsiyalash doim ekran chekkasiga urilardi |
| Yon panel (drawer) | Yangi layout primitivi kerak; ≤768px da gridni siqib qo'yardi |
| Sahifa ichida kengayadigan qator | Grid oqimini buzadi, `auto-fill` tartibini yorib yuboradi |
| Alohida marshrut `/stalls/{id}` | Xaritadagi o'rin yo'qoladi; qaytishda skroll pozitsiyasi tiklanmaydi |

Radix Dialog tanlanishi tekin: allaqachon bog'liqlik, allaqachon ikki joyda ishlatilgan, fokus tuzog'i / Esc / `aria-modal` / fokus qaytishi tayyor.

**Mobil variant:** `<640px` da bir xil Radix Dialog **pastki varaq** ko'rinishida — `items-end`, `w-full`, `rounded-t-lg rounded-b-none`, `max-h-[85vh]`. Faqat CSS, yangi komponent emas.

**Karta mazmuni:**

```
┌──────────────────────────────────────────┐
│  12                          [Faol]      │   ← font-mono text-xl + Badge
│  Sabzavot rastasi · A zonasi             │   ← text-sm text-muted (DB kontenti)
├──────────────────────────────────────────┤
│  Toifa           Sabzavot                │
│  Bugungi tarif   8 000 so'm              │   ← yoki "Tarif belgilanmagan" (D-08)
│  Sotuvchi        Karimov A.              │   ← yoki "Sotuvchi biriktirilmagan"
│  Telefon         +998 90 123 45 67       │
│  Holat           Faol                    │
├──────────────────────────────────────────┤
│  {children}                              │   ← 6–7 fazalar: dalil-rasm
├──────────────────────────────────────────┤
│  [ Tahrirlash ]  [ Sotuvchi biriktirish ]│   ← faqat `stall_manage` bo'lsa
└──────────────────────────────────────────┘
```

**Kelajak ilgagi (Scope Fence, arzon):**

```tsx
export type StallCardProps = {
  stallId: string | null;
  onClose: () => void;
  /** 6–7 fazalar: dalil-rasm galereyasi shu yerga tushadi. 2-fazada `undefined`. */
  children?: React.ReactNode;
};
```

Bitta prop. Rasm galereyasi, uning yuklanishi, lightbox — hech biri bu fazada **qurilmaydi**.

**Muhim: "Tarif belgilanmagan" majburiy ko'rinadi.** D-08 fail-closed — tarifsiz rasta hisobga tushmaydi va anomaliyaga aylanadi. Kartada bu `text-danger-text` + `AlertCircle` bilan ko'rsatiladi, chunki bu **haqiqiy nosozlik** (kamera bo'limidan farqli).

### 7.7 Klaviatura navigatsiyasi — 1000 tab-stop muammosi

**Muammo:** 1000 ta `<button>` = 1000 ta tab-stop. Klaviatura foydalanuvchisi xaritadan o'tib keta olmaydi.

**Yechim [QAROR] — roving tabindex + chiziqli o'qlar:**

1. Har zona `<section role="group" aria-label="{zona nomi} zonasi">`.
2. Zona ichida **aynan bitta** katak `tabIndex={0}`, qolganlari `tabIndex={-1}`. Tab bilan **zonaga bitta stop**.
3. Zona ichida:

| Klavish | Amal |
|---------|------|
| `←` / `→` (va `↑` / `↓`) | Oldingi / keyingi katak (**chiziqli**, kod tartibida) |
| `Home` / `End` | Zonadagi birinchi / oxirgi katak |
| `Enter` / `Space` | Kartani ochish |
| `Esc` (karta ochiq) | Yopish, fokus katakka qaytadi (Radix bajaradi) |

4. Fokus ko'chganda `scrollIntoView({ block: "nearest" })`.
5. Xaritadan **oldin** "Xaritani o'tkazib yuborish" havolasi (`sr-only focus:not-sr-only`) — 20 zona = 20 stop ham ko'p.

**Nega ikki o'lchovli `role="grid"` EMAS** — sabab hujjatlashtiriladi: joylashuv `auto-fill` bilan hosil bo'ladi, ya'ni "qator"ning **hech qanday ma'nosi yo'q** (D-19: koordinata saqlanmaydi, tartib faqat kod bo'yicha). `↑`/`↓` ni "ustundagi keyingi" deb talqin qilish foydalanuvchiga yolg'on model beradi va oyna kengligi o'zgarganda javob o'zgaradi. Chiziqli harakat halol. Bu §15-O-03 da a11y ko'rigiga chiqariladi.

### 7.8 Mobil va katta hajm

360px kenglikda: `floor((360 − 32) / 52) = 6` ustun. 1000 katak = ~167 qator × 52px = **~8700px skroll**.

**Kontrakt:**

1. **Zona sakrash chiplari** — `<768px` da xarita tepasida `sticky` gorizontal chiplar qatori; bosilganda `scrollIntoView` bilan zonaga o'tadi. Har chip `min-h-11`.
2. **Zonalar `<details>` ichida** (`<768px`): faqat **birinchi zona** ochiq (`open`), qolganlari yopiq. `<summary>` da zona nomi + rasta soni.
3. **`content-visibility: auto` + `contain-intrinsic-size`** har zona `<section>` ida (barcha o'lchamlarda):

```css
.zone-block {
  content-visibility: auto;
  contain-intrinsic-size: auto 400px;
}
```

Brauzer ekrandan tashqaridagi zonalarni render qilmaydi; `contain-intrinsic-size` skroll balandligini barqaror ushlaydi. **Nol bog'liqlik, nol JS** — virtualizatsiya kutubxonasiga alternativa.

4. `≥768px` da `<details>` doim ochiq (`open` atributi shartli).

**Yuklanish holati:** xarita `Skeleton` bilan — zona sarlavhasi + 24 ta katak shakli. Bu 1000 katak kelganda layout sakrashini (CLS) oldini oladi.

---

## 8. Yuza 3 — Reestrlar va Excel import (MARKET-02, MARKET-04)

### 8.1 Jadval emas — zich karta qatori [QAROR]

1-faza `<table>` ni ataylab rad etgan [KOD: `user-list.tsx:25-27` izohi: *"jadval telefon ekranida gorizontal skroll talab qilardi"*]. 2-faza bu qarorni **saqlaydi**, lekin miqyos boshqa (10 foydalanuvchi ↔ 1000 rasta), shuning uchun karta **zichlashtiriladi**:

- `<ul>` → `<li>` → `<Card className="px-4 py-3">` (hozirgi `px-5 pt-5 pb-3` o'rniga)
- `<640px`: 3 qatorli tik joylashuv
- `≥640px`: bitta qator — `grid grid-cols-[auto_1fr_auto_auto] items-center gap-4`

`<table>` rad etilishining sababi (yangilangan): yangi primitiv + gorizontal skroll + `role="table"` a11y ishi — hammasi karta qatori bermaydigan hech narsani bermaydi, chunki ustunlar soni 5 tadan oshmaydi.

### 8.2 Ustun ustuvorligi — nima qachon yo'qoladi

**Rastalar reestri:**

| Maydon | <640px | 640–1024px | >1024px | Uslub |
|--------|--------|------------|---------|-------|
| **Rasta raqami** | ✅ 1-qator, chapda | ✅ | ✅ | `font-mono text-sm font-semibold tabular-nums` |
| **Holat** (badge + ikonka) | ✅ 1-qator, o'ngda | ✅ | ✅ | `ui/badge` |
| Zona | ✅ 2-qator | ✅ | ✅ | `text-xs text-text-muted` |
| Toifa | ✅ 2-qator | ✅ | ✅ | `text-xs text-text-muted` |
| Sotuvchi | ✅ 3-qator | ✅ | ✅ | `text-sm` |
| **Bugungi tarif** | ❌ | ❌ | ✅ | `text-sm tabular-nums` |
| Amallar (`⋯`) | ✅ | ✅ | ✅ | `min-h-11 min-w-11` |

**Faqat bitta maydon yo'qoladi — bugungi tarif.** Sabab: u toifadan hosil bo'ladi va kartada baribir ko'rinadi. Rasta raqami, holati va sotuvchisi — hech qachon yo'qolmaydi, chunki ular reestrning maqsadi.

**Sotuvchilar reestri:**

| Maydon | <640px | ≥640px |
|--------|--------|--------|
| F.I.Sh. | ✅ | ✅ |
| Telefon | ✅ (`tel:` havola) | ✅ |
| Rastalar soni | ✅ badge (`3 ta rasta`) | ✅ badge + kodlar ro'yxati |
| Amallar | ✅ | ✅ |

### 8.3 Paginatsiya, filtr, qidiruv

**Keyset — "Ko'proq yuklash", sahifa raqamlari YO'Q** [MEROS: RESEARCH; KOD: `audit-list.tsx:100-112`].

| Element | Kontrakt |
|---------|----------|
| Sahifa hajmi | 50 |
| Yuklash | `useInfiniteQuery` + `next_cursor`; tugma `variant="secondary"`, matni "Ko'proq yuklash" |
| **"Oldingi" tugmasi** | **YO'Q.** `useInfiniteQuery` sahifalarni **qo'shib boradi** — oldingi natijalar ekranda qoladi, "oldingi" = yuqoriga skroll. Ikkinchi paginatsiya modeli kiritilmaydi |
| Natija soni | Ro'yxat tepasida `role="status"`: "{count} yozuv ko'rsatilmoqda" [KOD: `audit-list.tsx:81-83`] |
| Yangi sahifa e'loni | `aria-live="polite"` — yangi elementlar sonini e'lon qiladi, aks holda skrinrider "hech narsa o'zgarmadi" deb o'ylaydi |

**Filtrlar — `nuqs` bilan URL'da** [KOD: `audit-filters.tsx:35-73` naqshi]:

| Ekran | Parametrlar |
|-------|-------------|
| `/stalls` | `q` (kod yoki sotuvchi), `zone`, `category`, `status` |
| `/vendors` | `q` (ism yoki telefon) |
| `/tariffs` | `category` |
| `/map` | `q` (kodni topish va fokuslash) |

**Qidiruv debounce [QAROR]:** `q` parametri `parseAsString.withDefault("").withOptions({ throttleMs: 300 })` — nuqs'ning **o'z** mexanizmi. Maxsus `useDebounce` hooki yozilmaydi (yangi kod, yangi test yuzasi), lodash qo'shilmaydi (yangi bog'liqlik). Qolgan parametrlar throttle'siz (ular tanlov, terish emas).

**Filtrlarni tozalash** tugmasi — mavjud naqsh [KOD: `audit-filters.tsx:158-168`], `disabled` bo'sh holatda.

### 8.4 Inline tahrir emas — modal [QAROR]

**Tanlov: Radix Dialog + `react-hook-form` + `zod`** (mavjud naqsh: `create-user-dialog.tsx`).

Inline tahrir rad etilishining uchta sababi:

1. **Audit chegarasi.** Har rasta/sotuvchi o'zgarishi `fn_audit_row()` triggeri bilan yoziladi (D-10). Inline `onBlur` saqlash ikkilanish paytida tasodifiy audit yozuvlari hosil qiladi; aniq "Saqlash" tugmasi esa niyat chegarasini beradi.
2. **Rad etiladigan o'zgarish.** Rasta kodini tahrirlash **DB tomonidan rad etilishi mumkin** (D-02, `stall_code_claim()` → `23505`). Inline maydonda 409 tushuntirishini qo'yadigan joy yo'q; modalda `role="alert"` bloki bor.
3. **Bir vaqtda bir necha maydon.** Kod + zona + toifa + holatni birga o'zgartirish bitta tranzaksiya bo'lishi kerak.

### 8.5 Excel import oqimi (D-13 / D-14 / D-15)

**Joylashuv [QAROR]:** import — **sahifa ichidagi panel**, dialog emas. Sabab: xato ro'yxati uzun bo'lishi mumkin, o'z sarlavha ierarxiyasiga muhtoj va yuklab olish havolasi bilan birga yashaydi. Dialog ichida bularning hammasi ikki qavatli skrollga aylanardi.

**To'rt holat:**

**A — Tanlash**
```
┌─ Excel fayldan yuklash ─────────────────────────────┐
│                                                      │
│   [ Faylni tanlang yoki bu yerga tashlang ]         │
│                                                      │
│   Faqat xlsx fayl · 5 MB gacha · 5000 qatorgacha    │
│                                                      │
│   ↓ Shablonni yuklab olish                          │
└──────────────────────────────────────────────────────┘
```
- Drop zonasi — `<label>` + yashirin `<input type="file" accept=".xlsx">`. **Klaviatura bilan ishlaydi** (drag-drop yagona yo'l emas — WCAG 2.1.1).
- `min-h-11`; `dragover` da `border-accent`.
- "Shablonni yuklab olish" — birlamchi emas, `variant="ghost"` + `Download` ikonkasi. Lekin **birinchi importda ko'rinarli**: rastalar ro'yxati bo'sh bo'lsa bu havola bo'sh holat ichida ham takrorlanadi.

**B — Tekshirilmoqda**
- Fayl nomi + `Skeleton` qatorlar. Tugmalar `disabled`.
- **Progress bar YO'Q** — 1000 qator = 9 ms serverda (RESEARCH o'lchovi) + tarmoq. Soxta progress yolg'on.

**C1 — Xato (422)**

Bu — fazaning eng nozik ekrani. **300 xato muammosi** shunday hal qilinadi:

```
┌─ ⛔ Fayl qabul qilinmadi — 300 ta xato ──────────────┐
│                                                       │
│  Hech narsa saqlanmadi. Faylni tuzatib qayta yuklang. │  ← MAJBURIY
│                                                       │
│  Zona topilmadi                              210 ta   │  ← guruhlash
│  Raqam takrorlangan                           78 ta   │
│  Telefon raqami noto'g'ri                     12 ta   │
│                                                       │
│  14-qator: 'Sabzavot' zonasi topilmadi                │
│  15-qator: 'Sabzavot' zonasi topilmadi                │
│  … (birinchi 50 ta)                                   │
│                                                       │
│  Yana 250 ta xato                                     │
│  ↓ Xatolar ro'yxatini yuklab olish (xlsx)             │
└───────────────────────────────────────────────────────┘
```

**Kontrakt:**

| Qoida | Sabab |
|-------|-------|
| **"Hech narsa saqlanmadi" — birinchi jumla, doim** | D-14 all-or-nothing. Busiz admin qisman yozuvdan qo'rqadi va bazani qo'lda tekshira boshlaydi |
| **Xato KODI bo'yicha guruhlash — ro'yxatdan YUQORIDA** | 300 ta qator o'qib bo'lmaydi; 3 ta jumla o'qiladi va harakatga aylanadi. Bu ekranning eng qimmatli qismi |
| **Faqat birinchi 50 ta qator ko'rsatiladi** | 300 ta DOM elementi + skrinrider uchun foydasiz |
| **Qolganlari `.xlsx` bo'lib yuklab olinadi** | 300 xatoni brauzerda emas, Excelda tuzatiladi. `XlsxWriter` shu fazada allaqachon stekda |
| **Format aynan `{row}-qator: {message}`** | D-14 va CONTEXT `<specifics>` da so'zma-so'z talab qilingan |
| **`role="alert"` — FAQAT sarlavhada** | 50 ta elementga qo'yilsa skrinrider 50 marta uziladi |
| Xato ro'yxati — `<ol>` | Tartib ma'noli (qator raqami o'sib boradi) |
| Fokus | Javob kelganda sarlavhaga ko'chadi |

**C2 — Muvaffaqiyat (D-15 idempotentligi ko'rinadigan bo'lishi kerak):**

```
┌─ ✓ Yuklash yakunlandi ───────────────────────────────┐
│  512 ta rasta qo'shildi                               │
│  38 ta rasta allaqachon mavjud edi — ular             │
│  o'zgartirilmadi                                      │  ← MAJBURIY
│  [ Rastalar ro'yxatiga o'tish ]                       │
└───────────────────────────────────────────────────────┘
```

`skipped > 0` bo'lganda tushuntirish **majburiy** — aks holda admin "nega 38 tasi yo'qoldi?" deb o'ylaydi. D-15 bu xulqni ataylab tanlagan, UI buni ataylab deb ko'rsatishi kerak.

### 8.6 Sotuvchi shaxsiy ma'lumoti — foydalanuvchiga aytiladimi? [QAROR]

**Savol:** D-09 bo'yicha `GET /vendors` har chaqiruvi auditga yoziladi. Foydalanuvchi bundan xabardor qilinadimi?

**QAROR: HA — passiv, ekran boshida bir marta. Modal emas, qator-bo'yicha emas, tasdiq emas.**

Amalga oshirish — sotuvchilar sahifasi sarlavhasi ostida bitta qator:

```tsx
<p className="flex items-center gap-2 text-xs text-text-muted">
  <Info aria-hidden="true" className="size-3.5 shrink-0" />
  {t("vendors.auditNotice")}
</p>
```
> uz-Latn: «Sotuvchi ma'lumotlarini ko'rish audit jurnaliga yoziladi.»
> ru: «Просмотр данных продавцов фиксируется в журнале аудита.»

**Sabablar:**

1. **To'siq ko'rinmasa, to'sadigan narsa yo'q.** Audit'ning maqsadi — shaxsiy ma'lumotni sababsiz varaqlashni **oldini olish** (D-09, ASVS V8). Ko'rinmaydigan jurnal hech kimni to'xtatmaydi; u faqat keyin ayblaydi.
2. **Huquqiy holat.** O'zR shaxsiy ma'lumotlar qonuni + loyihaning "davlat bosqichiga tayyor" maqsadi. Ishlov berish haqida xabar berish bu yerda arzon.
3. **Nega tasdiq dialogi EMAS:** bozor admini bu ekranni kuniga o'nlab marta ochadi. Har safar tasdiq refleks bilan bosiladigan bo'lib qoladi (warning fatigue) va har oqimga bitta bosish qo'shadi — bu loyihaning "≤3 bosish" tamoyiliga bevosita zid.
4. **Nega qator-bo'yicha belgi EMAS:** audit **ro'yxat o'qishini** yozadi, har qatorni emas. Qator-bo'yicha belgi mexanizmni noto'g'ri tasvirlardi.
5. **Nega telefon MASKALANMAYDI:** server raqamni allaqachon yuborgan; uni klientda yulduzcha bilan yopish — xavfsizlik teatri. Bundan tashqari telefon operatsion jihatdan zarur (admin sotuvchiga qo'ng'iroq qiladi). Maskalash foydani emas, faqat ishqalanishni qo'shardi.

**Rad etilgan muqobil:** "Ko'rsatish" tugmasi ostidagi maskalangan raqam — 4-sabab bo'yicha rad etildi (allaqachon uzatilgan ma'lumotni yashirish).

**Bu bildirish qayerda takrorlanadi:** rasta kartasida sotuvchi telefoni ko'rinadi — u yerda **takrorlanmaydi** (karta sotuvchilar ro'yxatidan kelmaydi, u bitta rasta konteksti). Takroriy bildirish shovqinga aylanadi.

---

## 9. Umumiy holat kontrakti — yuklanish / bo'sh / xato

### 9.1 Yuklanish — BITTA naqsh tanlanadi

Hozir kodbazada **ikkita** naqsh bor: matnli `role="status"` [KOD: `user-list.tsx:80-86`] va `animate-pulse` bloklari [KOD: `(app)/layout.tsx:95-96`]. Uchinchisi qo'shilmaydi — mavjudlaridan bittasi tanlanadi.

**QAROR: Skeleton — kontent uchun; matnli `role="status"` — faqat amal holatlari uchun.**

| Vaziyat | Naqsh |
|---------|-------|
| Ro'yxat, xarita, karta yuklanmoqda | **`Skeleton`** — haqiqiy shaklga mos (5 qator / zona + 24 katak / karta shakli) |
| Tugma bosildi, so'rov ketdi | Tugma matni "Saqlanmoqda" + `disabled` (mavjud naqsh) |
| Sessiya tiklanmoqda (app layout) | Mavjud gibrid saqlanadi |

Sabab: 1000 katakli sahifada yalang'och "Yuklanmoqda" matni layoutni yig'ib, keyin 1000 katak bilan yoyadi — kuchli CLS. Skeleton balandlikni ushlab turadi. Bundan tashqari `(app)/layout.tsx` allaqachon skeleton ishlatadi — bu tanlov kodbazani **birlashtiradi**, uchinchi naqsh qo'shmaydi.

**Majburiy:**
- Skeleton konteyneri: `role="status" aria-busy="true"` + `<span className="sr-only">{t("common.loading")}</span>`. Skrinrider bir marta eshitadi, 20 marta emas.
- `motion-reduce:animate-none` — `prefers-reduced-motion` hurmat qilinadi.
- Skeleton bloki `bg-surface-muted` + `rounded-md`.

### 9.2 Bo'sh holat — "hech narsa yo'q" ≠ "filtr topmadi"

`ui/empty-state.tsx`: sarlavha (Heading 18px) + tavsif (Body 14px `text-muted`) + ixtiyoriy amal tugmasi. Markazlashtirilgan, `py-12`, ikonka **ixtiyoriy va neytral** (`text-text-muted`).

**Ikki xil bo'sh holat har doim ajratiladi** — ularning keyingi qadami boshqa:

| Vaziyat | Keyingi qadam |
|---------|---------------|
| Hech narsa yo'q | **Yaratish/import** — amal tugmasi bilan |
| Filtr hech narsa topmadi | **Filtrni tozalash** — amal tugmasi bilan |

To'liq matnlar §10.4 da (9 ta bo'sh holat).

### 9.3 Xato holati

Mavjud naqsh [KOD: `user-list.tsx:89-94`] saqlanadi, **ikkita tuzatish bilan**:

1. **Rang:** `text-danger` → `text-danger-text` (C-04: 3.97:1 → 5.52:1).
2. **Matn:** har xato **keyingi qadamni** aytishi shart. Hozirgi "Kutilmagan xato yuz berdi" [KOD: `messages/uz-Latn.json:136`] foydalanuvchini boshi berk ko'chada qoldiradi.

```tsx
<div role="alert" className="rounded-sm bg-danger/10 px-3 py-2 text-sm text-danger-text">
  <p className="font-semibold">{t("errors.loadFailedTitle")}</p>
  <p>{t("errors.loadFailedBody")}</p>
  <Button size="sm" variant="secondary" onClick={retry}>{t("common.retry")}</Button>
</div>
```

Xom `detail` foydalanuvchiga **hech qachon** ko'rsatilmaydi [MEROS: 1-faza naqshi] — xato → tarjima kaliti xaritasi (`adminErrorMessageKey`) kengaytiriladi.

---

## 10. Copywriting Contract

> `uz-Cyrl` ustuni **avtomatik hosil qilinadi** (`npm run i18n:gen`) — jadvalda faqat tasdiqlash uchun ko'rsatilgan. Qo'lda yoziladigan tillar: **uz-Latn** (manba) va **ru**.
> ✱ belgisi — §5.2 override talab qiladigan matn.

### 10.1 Birlamchi CTA va asosiy amallar

| Kalit | uz-Latn | uz-Cyrl (hosila) | ru |
|-------|---------|-------------------|-----|
| **`wizard.activate`** | **Bozorni faollashtirish** | Бозорни фаоллаштириш | **Активировать рынок** |
| `wizard.saveAndNext` | Saqlash va davom etish | Сақлаш ва давом этиш | Сохранить и продолжить |
| `markets.create` | Bozor qo'shish | Бозор қўшиш | Добавить рынок |
| `stalls.create` | Rasta qo'shish | Раста қўшиш | Добавить торговое место |
| `vendors.create` | Sotuvchi qo'shish | Сотувчи қўшиш | Добавить продавца |
| `zones.create` | Zona qo'shish | Зона қўшиш | Добавить зону |
| `categories.create` | Toifa qo'shish | Тоифа қўшиш | Добавить категорию |
| `tariffs.create` | Tarif qo'shish | Тариф қўшиш | Добавить тариф |
| `calendar.createException` | Istisno kun qo'shish | Истисно кун қўшиш | Добавить исключение |
| `stalls.assignVendor` | Sotuvchi biriktirish | Сотувчи бириктириш | Назначить продавца |
| `import.open` ✱ | Excel fayldan yuklash | Excel файлдан юклаш | Загрузить из файла Excel |
| `import.template` | Shablonni yuklab olish | Шаблонни юклаб олиш | Скачать шаблон |

**Birlamchi CTA qoidasi:** sahifada `variant="default"` bilan **eng ko'pi bilan bitta** tugma. Usta qadamlarida bu "Saqlash va davom etish", 7-qadamda "Bozorni faollashtirish", reestrlarda "… qo'shish".

### 10.2 Usta

| Kalit | uz-Latn | ru |
|-------|---------|-----|
| `wizard.title` | Yangi bozor | Новый рынок |
| `wizard.progress` | 7 qadamdan {done} tasi bajarilgan | Выполнено {done} из 7 шагов |
| `wizard.step1` | Rekvizitlar | Реквизиты |
| `wizard.step2` | Zonalar | Зоны |
| `wizard.step3` | Toifalar | Категории |
| `wizard.step4` | Tariflar | Тарифы |
| `wizard.step5` | Rastalar | Торговые места |
| `wizard.step6` | Sotuvchilar | Продавцы |
| `wizard.step7` | Ish kunlari | Рабочие дни |
| `wizard.stepCamera` | Kamera (keyinroq) | Камеры (позже) |
| `wizard.optional` | ixtiyoriy | необязательно |
| `wizard.stateDone` | bajarilgan | выполнено |
| `wizard.stateEmpty` | to'ldirilmagan | не заполнено |
| `wizard.stateBlocked` | hozircha ochilmaydi | пока недоступно |
| `wizard.reviewTitle` | Bozorni ishga tayyorlash | Готовность рынка |
| **`wizard.cameraNote`** | Kamera bo'limi keyinroq ulanadi. Bozor hozirdan to'liq ishlaydi: rasta, tarif va kunlik patta hisobi kamerasiz yuritiladi. | Камеры будут подключены позже. Рынок уже полностью работает: торговые места, тарифы и ежедневный учёт сбора ведутся без камер. |
| `wizard.activated` | Bozor faollashtirildi | Рынок активирован |
| `wizard.draftBadge` | Qoralama | Черновик |
| `wizard.resumeHint` | Bu bozor hali faollashtirilmagan — davom ettirishingiz mumkin | Этот рынок ещё не активирован — можно продолжить |

**Bloklovchi bandlar** (`setup-status.blocking[]` → tarjima kaliti):

| Kod | uz-Latn | ru |
|-----|---------|-----|
| `blocking.zones` | Kamida bitta zona qo'shing | Добавьте хотя бы одну зону |
| `blocking.categories` | Kamida bitta toifa qo'shing | Добавьте хотя бы одну категорию |
| `blocking.tariffs` | Har toifaga tarif belgilang | Укажите тариф для каждой категории |
| `blocking.stalls` | Kamida bitta rasta qo'shing | Добавьте хотя бы одно торговое место |
| `blocking.stallCategories` | Har rastaga toifa belgilang | Укажите категорию для каждого торгового места |
| `blocking.calendar` | Ish kunlarini belgilang | Укажите рабочие дни |

**Bloklangan qadam sabablari:**

| Kalit | uz-Latn | ru |
|-------|---------|-----|
| `wizard.needCategories` | Avval toifa qo'shing | Сначала добавьте категорию |
| `wizard.needZonesAndCategories` | Avval zona va toifa qo'shing | Сначала добавьте зоны и категории |
| `wizard.needStalls` | Avval rasta qo'shing | Сначала добавьте торговые места |

### 10.3 Xarita va rasta kartasi

| Kalit | uz-Latn | ru |
|-------|---------|-----|
| `map.title` | Plan-xarita | Схема рынка |
| `map.skip` | Xaritani o'tkazib yuborish | Пропустить схему |
| `map.legend` | Belgilar | Обозначения |
| `map.searchLabel` | Rasta raqami bo'yicha topish | Найти по номеру места |
| `map.zoneStalls` | {count} ta rasta | Мест: {count} |
| `stalls.status.active` | Faol | Действует |
| `stalls.status.maintenance` | Ta'mirda | На ремонте |
| `stalls.status.closed` | Yopiq | Закрыто |
| `stalls.noVendor` | Sotuvchi biriktirilmagan | Продавец не назначен |
| `stalls.noVendorShort` | Sotuvchisiz | Без продавца |
| `stalls.noTariff` | Tarif belgilanmagan | Тариф не задан |
| `stalls.noTariffHint` | Tarifsiz kunlik patta hisoblanmaydi | Без тарифа ежедневный сбор не начисляется |
| `stalls.cellLabel` | {code}-rasta, {status}, {category}, {vendor} | Место {code}, {status}, {category}, {vendor} |
| `stalls.todayTariff` | Bugungi tarif | Тариф на сегодня |
| `stalls.zone` | Zona | Зона |
| `stalls.category` | Toifa | Категория |
| `stalls.vendor` | Sotuvchi | Продавец |
| `stalls.edit` | Tahrirlash | Редактировать |

### 10.4 Bo'sh holatlar (9 ta) — sarlavha + tavsif

| Kalit | uz-Latn sarlavha / tavsif | ru sarlavha / tavsif |
|-------|---------------------------|----------------------|
| `stalls.empty` ✱ | **Bu bozorda hali rasta yo'q** / Excel fayldan yuklang yoki birinchi rastani qo'lda qo'shing. | **На этом рынке пока нет торговых мест** / Загрузите из файла Excel или добавьте первое место вручную. |
| `stalls.emptyFiltered` ✱ | **Filtrga mos rasta topilmadi** / Raqamni tekshiring yoki filtrlarni tozalang. | **Торговых мест по фильтру не найдено** / Проверьте номер или сбросьте фильтры. |
| `vendors.empty` | **Bu bozorda hali sotuvchi yo'q** / Sotuvchisiz ham davom etishingiz mumkin — ularni keyinroq qo'shasiz. | **На этом рынке пока нет продавцов** / Можно продолжить без продавцов — добавите их позже. |
| `vendors.emptyFiltered` ✱ | **Sotuvchi topilmadi** / Ism yoki telefon raqamini tekshiring. | **Продавец не найден** / Проверьте имя или номер телефона. |
| `zones.empty` | **Zona qo'shilmagan** / Har rasta bitta zonaga tegishli bo'ladi. Birinchi zonani qo'shing. | **Зоны не добавлены** / Каждое место относится к одной зоне. Добавьте первую зону. |
| `categories.empty` | **Toifa qo'shilmagan** / Kunlik patta summasi mahsulot toifasi bo'yicha belgilanadi. | **Категории не добавлены** / Сумма ежедневного сбора задаётся по категории товара. |
| `tariffs.empty` | **Tarif belgilanmagan** / Tarifsiz kunlik patta hisoblanmaydi. Har toifaga narx qo'shing. | **Тарифы не заданы** / Без тарифа ежедневный сбор не начисляется. Укажите цену для каждой категории. |
| `calendar.empty` | **Istisno kun belgilanmagan** / Haftalik jadval amal qiladi. Bayram yoki qo'shimcha ish kunini shu yerda qo'shasiz. | **Исключения не заданы** / Действует недельное расписание. Праздники и дополнительные рабочие дни добавляются здесь. |
| `map.empty` | **Xarita bo'sh** / Rasta qo'shilgach xarita avtomatik chiziladi. | **Схема пуста** / Схема появится автоматически после добавления мест. |

### 10.5 Xato holatlari — muammo + keyingi qadam

| Kalit | uz-Latn | ru |
|-------|---------|-----|
| `errors.loadFailedTitle` | Ma'lumot yuklanmadi | Не удалось загрузить данные |
| `errors.loadFailedBody` | Qayta urinib ko'ring. Xato takrorlansa bozor ma'muriyatiga xabar bering. | Повторите попытку. Если ошибка повторяется, сообщите администрации рынка. |
| `errors.forbidden` | Bu amal uchun ruxsat yo'q. Bozor admini bilan bog'laning. | Нет прав на это действие. Обратитесь к администратору рынка. |
| `errors.notFound` | Bu yozuv topilmadi yoki u boshqa bozorga tegishli. | Запись не найдена или относится к другому рынку. |
| `stalls.codeRetired` | Bu raqam ilgari ishlatilgan va boshqa rastaga berilmaydi. Boshqa raqam kiriting. | Этот номер уже использовался и не может быть присвоен другому месту. Введите другой номер. |
| `stalls.codeTaken` | Bu raqamli rasta allaqachon mavjud. | Место с таким номером уже существует. |
| `vendors.phoneTaken` | Bu telefon raqami shu bozorda allaqachon ro'yxatda. | Этот номер телефона уже зарегистрирован на этом рынке. |
| `assignments.overlap` | Bu davrda rastaga boshqa sotuvchi biriktirilgan. Avvalgi davrni yoping yoki boshqa sana tanlang. | В этот период место занято другим продавцом. Закройте предыдущий период или выберите другую дату. |
| `tariffs.pastLocked` | O'tgan sanadagi tarif o'zgartirilmaydi. Yangi sanadan yangi tarif qo'shing. | Тариф за прошедшую дату изменить нельзя. Добавьте новый тариф с будущей даты. |
| `wizard.activateBlocked` | Bozor hali faollashtirilmaydi — quyidagilar to'ldirilishi kerak: | Рынок пока нельзя активировать — необходимо заполнить: |

**Import xatolari** (D-14 formati: `{row}-qator: {message}`):

| Kalit | uz-Latn | ru |
|-------|---------|-----|
| `import.errorLine` | {row}-qator: {message} | Строка {row}: {message} |
| `import.errors.zoneNotFound` | '{name}' zonasi topilmadi | Зона «{name}» не найдена |
| `import.errors.categoryNotFound` | '{name}' toifasi topilmadi | Категория «{name}» не найдена |
| `import.errors.duplicateCode` | {code} raqami takrorlangan | Номер {code} повторяется |
| `import.errors.emptyCode` | Rasta raqami ko'rsatilmagan | Номер места не указан |
| `import.errors.invalidPhone` | Telefon raqami noto'g'ri | Неверный номер телефона |
| `import.errors.stallNotFound` | {code} raqamli rasta topilmadi | Место с номером {code} не найдено |

**Import paneli:**

| Kalit | uz-Latn | ru |
|-------|---------|-----|
| `import.dropHint` | Faylni tanlang yoki bu yerga tashlang | Выберите файл или перетащите сюда |
| `import.limits` ✱ | Faqat xlsx fayl · 5 MB gacha · 5000 qatorgacha | Только файл xlsx · до 5 МБ · до 5000 строк |
| `import.rejectedTitle` | Fayl qabul qilinmadi — {count} ta xato | Файл не принят — ошибок: {count} |
| **`import.nothingSaved`** | **Hech narsa saqlanmadi. Faylni tuzatib qayta yuklang.** | **Ничего не сохранено. Исправьте файл и загрузите заново.** |
| `import.moreErrors` | Yana {count} ta xato | Ещё ошибок: {count} |
| `import.downloadErrors` | Xatolar ro'yxatini yuklab olish | Скачать список ошибок |
| `import.doneTitle` | Yuklash yakunlandi | Загрузка завершена |
| `import.inserted` | {count} ta rasta qo'shildi | Добавлено мест: {count} |
| **`import.skipped`** | {count} ta rasta allaqachon mavjud edi — ular o'zgartirilmadi | {count} мест уже существовали — они не изменены |
| `import.goToList` | Rastalar ro'yxatiga o'tish | Перейти к списку мест |

### 10.6 Destruktiv amallar — beshta, ikki daraja

| # | Amal | Daraja | Tasdiq matni (uz-Latn / ru) |
|---|------|--------|------------------------------|
| **D-1** | **Qoralama bozorni o'chirish** | **2 — nom yozib tasdiqlash** | «Bu qoralama bozor butunlay o'chiriladi: zonalari, rastalari va tariflari ham yo'qoladi. Tasdiqlash uchun bozor nomini yozing.» / «Черновик рынка будет удалён полностью: зоны, места и тарифы также исчезнут. Для подтверждения введите название рынка.» |
| **D-2** | **Rastani yopish** (`status → closed`) | **2 — raqam yozib tasdiqlash** | «Bu rasta yopiladi va uning {code} raqami boshqa hech qachon ishlatilmaydi. Tasdiqlash uchun raqamni yozing.» / «Место будет закрыто, а его номер {code} больше никогда не будет использован. Для подтверждения введите номер.» |
| **D-3** | Kelajakdagi tarifni o'chirish | 1 — oddiy tasdiq | «Bu tarif hali kuchga kirmagan. O'chirilsinmi?» / «Этот тариф ещё не вступил в силу. Удалить?» |
| **D-4** | Sotuvchi biriktirishini yopish | 1 — oddiy tasdiq | «{vendor} bu rastadan {date} dan boshlab ajratiladi. Undagi qarz o'ziga qoladi.» / «{vendor} будет откреплён от места с {date}. Его задолженность остаётся за ним.» |
| **D-5** | Kunni yopiq deb belgilash | 1 — oddiy tasdiq | «{date} kuni bozor yopiq bo'ladi va o'sha kunga patta hisoblanmaydi.» / «{date} рынок будет закрыт, и сбор за этот день не начисляется.» |

**Tasdiq tugmasining MATNI — generic "Tasdiqlash" EMAS.**

Mavjud naqsh tasdiq tugmasiga generic `t("users.confirm")` = **"Tasdiqlash"** qo'yadi [KOD: `user-list.tsx:331`]. 2-faza bu naqshni **meros qilmaydi**: qaytarib bo'lmaydigan amalda tugma o'z fe'lini takrorlashi shart — foydalanuvchi ko'pincha dialog matnini o'qimasdan tugmaga qarab qaror qiladi, "Tasdiqlash" esa nimani tasdiqlayotganini aytmaydi.

| # | Kalit | uz-Latn | uz-Cyrl (hosila, tekshirildi) | ru |
|---|-------|---------|-------------------------------|-----|
| D-1 | `markets.deleteDraftAction` | **Bozorni o'chirish** | Бозорни ўчириш | **Удалить рынок** |
| D-2 | `stalls.closeAction` | **Rastani yopish** | Растани ёпиш | **Закрыть место** |
| D-3 | `tariffs.deleteAction` | **Tarifni o'chirish** | Тарифни ўчириш | **Удалить тариф** |
| D-4 | `assignments.closeAction` | **Biriktirishni yopish** | Бириктиришни ёпиш | **Закрыть назначение** |
| D-5 | `calendar.closeDayAction` | **Yopiq deb belgilash** | Ёпиқ деб белгилаш | **Отметить нерабочим** |
| — | `common.cancel` (mavjud) | Bekor qilish | Бекор қилиш | Отмена |

**Transliteratsiya tekshirildi** [O'LCHANDI: beshtasi ham `gen-cyrillic.mjs` orqali o'tkazildi] — birortasida §5.2 dagi defektlar yo'q: lotin so'zi ham, apostrofli qo'shimcha ham yo'q; `o'chirish` → `ўчириш` digrafi to'g'ri ko'chadi. **Qo'shimcha override kerak emas.**

**Nega buyruq fe'li emas, harakat nomi** ("O'chir" emas, "O'chirish"): mavjud katalog butunlay harakat nomidan iborat (`Saqlash`, `Bloklash`, `Tasdiqlash`) — aralashtirish uslubni buzardi; rus tilida ham `Удалить` infinitiv shakl.

**2-daraja nima uchun faqat D-1 va D-2 da:** ikkalasi ham **UI'dan qaytarib bo'lmaydi**. D-1 kaskad o'chirish; D-2 esa D-02 qarori bo'yicha rasta raqamini **abadiy iste'moldan chiqaradi** (`stall_code_registry`) — "bekor qilish" tugmasi bo'lishi mumkin emas. Yozib tasdiqlash arzon: bozor nomi va rasta raqami ekranda ko'rinib turadi va 1–4 belgidan iborat.

**D-4 matni D-10 ni ataylab takrorlaydi** ("qarz o'ziga qoladi") — bu admin uchun eng ehtimolli noto'g'ri tushuncha va uni aynan shu daqiqada tuzatish kerak.

**Barcha tasdiq dialoglarida:**
- Tasdiq tugmasi `variant="destructive"`, **o'ngda**; bekor qilish `variant="secondary"`, chapda [KOD: `user-list.tsx:324` — `flex-col gap-2 sm:flex-row-reverse`]
- Dialog ochilganda fokus **bekor qilishda** (D-3/D-4/D-5) yoki **matn maydonida** (D-1/D-2) — hech qachon destruktiv tugmada
- `Esc` = bekor qilish

---

## 11. Accessibility Contract

| Talab | Kontrakt | Tekshiruv |
|-------|----------|-----------|
| **Kontrast — matn** | AA 4.5:1. §4.2 dagi 6 ta buzilish tuzatiladi | Tokenlar bo'yicha hisoblangan — §4.2 jadvali |
| **Kontrast — boshqaruv elementi** | WCAG 2.2 SC 1.4.11 ≥3:1. `--color-border-ui` (3.64:1) | §4.2 C-03 |
| **Fokus ko'rinishi** | Har interaktiv element. Xarita katagida `outline-offset: 1px` + `z-10` (§7.5) | Klaviatura o'tishi UAT |
| **Rang yagona signal emas** | §4.4 jadvali — har holatga ≥2 qo'shimcha kanal | `stall-map.test.tsx`: ikonka/`line-through`/`dashed` mavjudligi |
| **Nishon o'lchami** | ≥44×44px barcha bosiladigan elementda | §2 istisnosi |
| **Klaviatura — usta** | Qadamlar `<Link>`; bloklangan qadam `<span aria-disabled>`; forma xatosida fokus birinchi noto'g'ri maydonga | §6.3, §6.8 |
| **Klaviatura — xarita** | Roving tabindex: zonaga 1 stop; `←→↑↓`, `Home`/`End`, `Enter`/`Space`; "o'tkazib yuborish" havolasi | §7.7 |
| **Klaviatura — dialog** | Radix: fokus tuzog'i, `Esc`, fokus triggerga qaytadi | §7.6 |
| **Klaviatura — import** | Drop zonasi `<label>` + `<input type="file">` — drag yagona yo'l emas (WCAG 2.1.1) | §8.5 |
| **Jonli hududlar** | `role="alert"` — xato; `role="status"` — progress, natija soni, faollashtirish to'siqlari. Xato ro'yxatida **faqat sarlavha** alert | §8.5, §6.6 |
| **Rasm/ikonka** | Bezak ikonkalari `aria-hidden="true"` (mavjud naqsh); ma'no tashuvchi ikonka `aria-label` bilan | — |
| **Til atributi** | `<html lang>` locale bo'yicha; DB kontenti `lang` bilan belgilanMAYDI (1-faza D-16 — kontent bir tilda) | — |
| **Harakat** | `prefers-reduced-motion`: skeleton pulsi va `active:scale` o'chadi | §7.5, §9.1 |
| **Matn kattalashtirish** | 200% zoom'da layout buzilmaydi (`maximum-scale` qo'yilmaydi) | §3.3 |
| **Forma yorliqlari** | Har boshqaruv elementida `<label htmlFor>`; placeholder yorliq o'rnini bosMAYDI | Mavjud naqsh |

---

## 12. Component Inventory

### 12.1 Wave 0 — dizayn tizimi tuzatishi (yangi ekranlardan OLDIN)

**BLOKLOVCHI (o'lchangan a11y buzilishi):**

| # | Ish | Fayl |
|---|-----|------|
| W0-1 | 6 ta token tuzatish + 4 ta yangi token (§4.2 diff) | `frontend/src/app/globals.css` |
| W0-2 | `border-border` → `border-border-ui` boshqaruv elementlarida (≈6 hodisa) | `ui/input.tsx`, `audit-filters.tsx`, `create-user-dialog.tsx` |
| W0-3 | `text-danger` → `text-danger-text` xato bloklarida (≈6 hodisa) | `user-list.tsx`, `audit-list.tsx`, `market-picker.tsx`, `create-user-dialog.tsx`, `users/page.tsx` |
| W0-4 | Badge tone'lari `*-text` tokenlariga o'tadi | `ui/badge.tsx` (yangi) |
| W0-5 | `@media (pointer: coarse)` forma shrifti qoidasi | `globals.css` |

**MAJBURIY (yangi ekranlardan oldin — arzon hozir, qimmat keyin):**

| # | Ish | Hajmi |
|---|-----|-------|
| W0-6 | `font-medium` → `font-semibold` | 22 hodisa, mexanik |
| W0-7 | `text-base` → `text-sm`/`text-lg`; `text-xl` faqat `font-mono` da qoladi | 4 hodisa |
| W0-8 | Off-grid spacing (`*-0.5`, `*-1.5`, `*-2.5`) → 4-panjara | 21 hodisa |
| W0-9 | `ui/` primitivlarini ajratish: `dialog`, `field`, `select`, `badge`, `skeleton`, `empty-state`, `confirm-dialog` | §1.2 |
| W0-10 | `uz-Cyrl.overrides.json` — 5 ta yangi so'z (§5.2) | 5 qator |
| W0-11 | `gen-cyrillic.test.mjs` — T-01…T-04 uchun assertionlar | 4 test |
| W0-12 | **Qoralama bozor ko'rinadigan bo'ladi** — 6 bandli zanjir | §12.1.1 |

#### 12.1.1 W0-12 to'liq zanjiri — qoralama bozor ko'rinadigan bo'lishi

§6.4 dagi "chala ustaga qaytish" oqimi **oltita fayl birga o'zgargandagina** ishlaydi. Zanjir kod bo'yicha oxirigacha kuzatildi — har band `fayl:qator` bilan tasdiqlangan.

**Nega bitta bandning o'zi yetarli emas:** bozor tanlash ekranining **asosiy** manbai — `POST /auth/login` javobidagi `markets` ro'yxati, va u serverda allaqachon kesilgan. `market-picker.tsx:61` dagi `.filter(...)` esa faqat **zaxira** yo'lga (`GET /markets`) tegishli. Bundan tashqari zaxira yo'l bu ekranda **umuman ishlay olmaydi**: `GET /markets` `TenantSessionDep` talab qiladi va bozor tanlanmagan sessiya u yerda **409** oladi — bu ataylab qilingan [KOD: `services/core-api/app/api/v1/markets.py` docstring: *"Bozor tanlanmagan sessiya `TenantSessionDep` da 409 oladi. Bu ataylab..."*].

| # | Fayl:qator | Hozir | O'zgarish |
|---|------------|-------|-----------|
| **1** | `migrations/` — `auth_memberships()` SQL funksiyasi | `SELECT market_id, market_name, roles` [KOD: `auth_repo.py:124`] | Qaytish to'plamiga `is_active` qo'shiladi. ⚠ Postgres'da funksiya qaytish tipini o'zgartirish uchun `DROP FUNCTION` + qayta yaratish kerak — "ustun qo'shish" tekin emas, alohida migratsiya bandi |
| **2** | `services/core-api/app/repositories/auth_repo.py:76-81` | `class Membership` da `market_id`, `market_name`, `roles` — **`is_active` YO'Q** | `is_active: bool` qo'shiladi; `memberships()` uni o'qiydi (`auth_repo.py:200-210`) |
| **3** | `services/core-api/app/schemas.py:73-77` | `class MarketRef(BaseModel)` da **faqat `id` va `name`** | `is_active: bool` qo'shiladi |
| **4** | `services/core-api/app/api/v1/auth.py:384-390` | `_visible_markets()` platforma admini uchun `if market.is_active` bilan **serverda kesadi** va `is_active` ni uzatmaydi ham | Filtr **olib tashlanadi**, `is_active=...` uzatiladi. ⚠ `MarketRef` **8 joyda** quriladi (`auth.py:235, 238, 353, 386, 390, 451, 519, 796`) — majburiy maydon qo'shilgani uchun **hammasi** o'zgaradi |
| **5** | `frontend/src/lib/api-types.ts:48-52` | `marketRefSchema` / `MarketSummary` da faqat `id`/`name` | `is_active: z.boolean()` qo'shiladi. `marketListItemSchema` allaqachon uni `.extend()` qiladi (`api-types.ts:55-58`) — endi takrorlanmaydi |
| **6** | `frontend/src/components/auth/market-picker.tsx:57-62` | `.filter((market) => market.is_active)` (o'lik zaxira yo'lida) | Filtr olib tashlanadi; `is_active === false` → `Qoralama` badge + `?step=` ga marshrutlash (§6.4) |

**Tartib majburiy:** 1 → 2 → 3 → 4 → 5 → 6. 3-band 4-banddan oldin bajarilmasa `MarketRef` qurilishi yiqiladi; 5-band 4-banddan oldin bajarilsa zod sxemasi hali kelmagan maydonni talab qiladi va **butun login oqimi** chegarada yiqiladi.

**Test ta'siri:** `MarketRef` — uchta javob modelining bir qismi (`schemas.py:116-117, 137, 164`: `LoginResponse.market`, `LoginResponse.markets`, `SessionResponse.market`). Majburiy maydon qo'shish **login / select-market / refresh** javob shakllarini o'zgartiradi — shu uchala oqimning mavjud testlari yangilanadi.

##### Xavfsizlik ta'siri — to'rt topilma; ikkitasi kutilganidan kichik, bittasi katta

**X-1 — Yangi vakolat berilMAYDI, faqat topiladigan bo'ladi.** Platforma admini qoralama bozorni **allaqachon tanlay oladi**: `POST /auth/select-market` a'zoligi bo'lmagan bozorni tanlashga ruxsat beradi (`_platform_admin_market()`) [MEROS: RESEARCH Pattern 5, 2-qadam]. Ya'ni qoralama bozor bugun ham **yetib boriladigan**, faqat **ko'rinmaydigan**. O'zgarish yangi kirish sinfini ochmaydi — u mavjud vakolatni topiladigan qiladi.

**X-2 — Hozirgi xulq assimetrik: a'zolar qoralamani ALLAQACHON ko'radi.** `_visible_markets()` da `if market.is_active` **faqat `is_platform_admin` tarmog'ida** [KOD: `auth.py:384-389`]. A'zolik tarmog'ida (`auth.py:390`) hech qanday filtr **yo'q**. Ya'ni D-04 bo'yicha qoralama bozorga tayinlangan bozor admini uni **bugun ham ro'yxatda ko'radi va ichiga kiradi**, uni yaratgan platforma admini esa ko'rmaydi. Tuzatish bu assimetriyani yopadi, kengaytirmaydi. Zanjirning 2-bandi aynan shuning uchun kerak: `is_active` ni faqat platforma admini tarmog'ida uzatib, a'zolik tarmog'ida `True` deb standart qo'yish qoralamani "faol" deb **yolg'on yorliqlagan** bo'lardi.

**X-3 — WR-03 shu fazada JONLI bo'ladi. Bu ilgak emas, ogohlantirish.** 1-faza ko'rigi `POST /auth/select-market` ning `is_platform_admin` ni DB'dan qayta o'qimay, **chaqiruvchi tokenidan qayta imzolashini** qayd etgan va so'zma-so'z shunday yozgan [KOD: `.planning/phases/01-poydevor-va-tenant-xavfsizligi/01-REVIEW-GAPS.md:307-311`]:

> *"There is no revocation API in phase 1, which is the only reason this is not already exploitable; **the moment one is added (market wizard / platform admin management) this becomes a live authorization bypass.**"*

2-faza — **aynan o'sha market wizard**, va uning 2-qadami `POST /auth/select-market` ni ishlatadi [MEROS: RESEARCH Pattern 5]. Ya'ni 1-faza nomma-nom ko'rsatgan shart bu fazada bajariladi. WR-02 ham shu endpointga tegishli (`select-market` `require_password_current` dan tashqarida).

**Kontrakt:** WR-02 va WR-03 Wave 0 da yopiladi, keyingi fazaga qoldirilmaydi va ular §12.1 dagi boshqa Wave 0 ishlaridan **oldin** turadi. Bu UI qarori emas — lekin UI-SPEC uni **jimgina o'tkazib yubormaydi**, chunki ustaning butun oqimi aynan shu endpointga tayanadi.

**X-4 — Qoralama mahsulot oqimlariga sizib chiqmasligi.** `is_active` ni javobga chiqarish — aynan **filtrni mumkin qiladigan** narsa [MEROS: RESEARCH Pitfall 7]. Kontrakt: `is_active` ochilgandan keyin har bir iste'molchi **aniq** filtrlaydi (6-faza billing job `WHERE m.is_active`), "ro'yxat allaqachon toza" degan taxminga tayanmaydi. Bozor tanlash ekrani — qoralama **ataylab ko'rinadigan** yagona joy.

### 12.2 Yangi komponentlar

| Yo'l | Vazifa | Client? |
|------|--------|---------|
| `components/wizard/wizard-stepper.tsx` | Qadam relsi, 4 holat | ✅ |
| `components/wizard/wizard-shell.tsx` | Layout: rels + kontent + `setup-status` so'rovi | ✅ |
| `components/wizard/activation-panel.tsx` | To'liqlik ro'yxati + faollashtirish (§6.6) | ✅ |
| `components/stalls/stall-map.tsx` | Zona bloklari + CSS Grid + roving tabindex | ✅ |
| `components/stalls/stall-cell.tsx` | `React.memo` katak | ✅ |
| `components/stalls/stall-tone.ts` | `toneOf()` + `TONE_STYLES` (§7.2) | — |
| `components/stalls/stall-map-legend.tsx` | Legenda | — |
| `components/stalls/stall-card-dialog.tsx` | Rasta kartasi + `children` sloti | ✅ |
| `components/stalls/stall-list.tsx` | Reestr (zich karta qatori) | ✅ |
| `components/stalls/stall-dialog.tsx` | Yaratish/tahrirlash formasi | ✅ |
| `components/stalls/stall-filters.tsx` | nuqs filtrlari | ✅ |
| `components/vendors/{vendor-list,vendor-dialog,assignment-dialog}.tsx` | Sotuvchi reestri | ✅ |
| `components/tariffs/{tariff-list,tariff-dialog}.tsx` | Tarif tarixi | ✅ |
| `components/calendar/{weekday-picker,exception-list,exception-dialog}.tsx` | Ish kunlari | ✅ |
| `components/zones/zone-list.tsx`, `components/categories/category-list.tsx` | Oddiy ro'yxat + inline qo'shish | ✅ |
| `components/import/import-panel.tsx` | 4 holatli import (§8.5) | ✅ |
| `components/import/import-errors.tsx` | Guruhlash + 50 qator + yuklab olish | — |

### 12.3 Navigatsiya kengaytmasi

2-faza 5 ta yangi bo'lim qo'shadi (jami 8). Mobil pastki panel [KOD: `app-shell.tsx:93-115`] 8 ta elementni ko'tara olmaydi (360px'da har biri ~45px).

**Kontrakt:**
- **Desktop (`md:`)** — yon panel, 3 guruh: *(guruhsiz)* Boshqaruv paneli · **Bozor**: Xarita, Rastalar, Sotuvchilar, Tariflar, Ish kunlari · **Tizim**: Foydalanuvchilar, Audit jurnali. Guruh sarlavhasi `text-xs font-semibold text-text-muted` (5.06:1 tuzatishdan keyin).
- **Mobil** — pastki panelda **eng ko'pi 5 element**: 4 ta eng ko'p ishlatiladigan + `Ko'proq`. `Ko'proq` mavjud Radix Dialog'ni pastki varaq sifatida ochadi (yangi bog'liqlik yo'q).
- Har element `permission` bo'yicha filtrlanadi — mavjud naqsh [KOD: `app-shell.tsx:50-52`]. Kassir/nazoratchida 2-fazada `MARKET_DATA_VIEW` yo'q [MEROS: RESEARCH A8] → ular faqat Boshqaruv panelini ko'radi.

---

## 13. Registry Safety

| Registry | Ishlatilgan bloklar | Safety Gate |
|----------|---------------------|-------------|
| shadcn (rasmiy) | — | **Qo'llanmaydi** — `components.json` yo'q, shadcn init bajarilmadi (§1.3) |
| Uchinchi tomon registrlari | **YO'Q** | **Qo'llanmaydi** — birorta uchinchi tomon registri e'lon qilinmadi |

**`npx shadcn add` bu fazada ishlatilmaydi.** Barcha komponentlar mavjud bog'liqliklar (`@radix-ui/*`, `lucide-react`, `class-variance-authority`) ustida qo'lda yoziladi va kod-ko'rikdan o'tadi.

**Yangi npm paketi qo'shilmaydi** (§1.4). Agar reja bajarilishida biror paket zarur bo'lib chiqsa, u **UI-SPEC ga qaytariladi** va §1.4 ostida sabab + rad etilgan muqobil bilan yoziladi — jimgina `npm install` qilinmaydi.

---

## 14. Scope Fence — UI ilgaklari (to'liq dizayn EMAS)

[MEROS: RESEARCH §Scope Fence]

| Kelajak imkoniyati | Faza | 2-fazada aynan nima qilinadi | Nima QILINMAYDI |
|--------------------|------|-------------------------------|------------------|
| Kamera qo'shish, ulanish testi | 3 | Stepper'da `aria-disabled` element + bitta neytral jumla (§6.7) | Kamera formasi, RTSP maydonlari, ogohlantirish banneri |
| Snapshot jadvali | 4 | Hech narsa | — |
| Kamera-zona poligonlari | 5 | Hech narsa (`stalls.id` barqarorligi allaqachon) | Poligon muharriri, canvas |
| Xarita ranglari (to'langan/qarzdor/nomuvofiq) | 6–7 | `StallTone` tipida 3 ta qiymat **e'lon qilinadi**; `TONE_STYLES` `Record` to'liq (§7.2) | Rang mantiqi, hue tanlovi, legendaga qator |
| Rasta kartasida dalil-rasm | 6–7 | `children?: React.ReactNode` — **bitta prop** (§7.6) | Galereya, lightbox, rasm yuklash |
| Sotuvchi qarzi / to'lov tarixi | 6–7 | Hech narsa | Balans ustuni, qarz badge'i |
| Kassir ≤3 bosish oqimi | 6 | Faqat **poydevor**: raqam bo'yicha qidiruv ≤2 o'zaro ta'sirda (§6.9) | Kassir ekrani, to'lov formasi |
| Telegram bot ulanishi | 7 | Hech narsa (`vendors.phone` allaqachon) | — |
| Excel hisobot eksporti | 8 | `XlsxWriter` shu fazada import shabloni va xato ro'yxati uchun keladi | Hisobot ekranlari |
| To'liq interaktiv xarita | v2 | Renderer kontrakti ajratilgan (§7.2) — Konva'ga o'tish faqat `stall-map.tsx` ni almashtiradi | react-konva |
| Ko'p tilli DB kontenti | — | Qurilmaydi (1-faza D-16) | — |

**Erta optimizatsiya deb baholangan va QILINMAYDIGAN "ilgaklar":** virtualizatsiya kutubxonasi, dark mode tokenlari, chart kutubxonasi, umumiy `<DataTable>` abstraktsiyasi, dizayn-token generatori, Storybook.

---

## 15. Open Questions

Bu subagent kontekstida foydalanuvchiga savol berish vositasi yo'q. Quyidagilar **taxmin qilinib jimgina qulflanmadi** — ular ochiq qoldiriladi va reja/UAT bosqichida hal qilinadi.

| # | Savol | Bilamiz | Noaniq | Tavsiya (agar javob kelmasa) |
|---|-------|---------|--------|------------------------------|
| **O-01** | Usta **7 qadammi yoki 8**? | Prompt "7 qadam" deydi va 6 ta strelka sanaydi; RESEARCH Pattern 5 esa 8 ta nuqta beradi (rekvizit + 6 domen + faollashtirish) | "Ish kunlari" alohida qadammi yoki 1-qadam rekvizitlari ichidami | §6.2 dagi 7 qadamli tuzilish (ish kunlari 7-qadam, faollashtirish paneli o'sha qadam ichida). Agar buyurtmachi 8 ni xohlasa — faqat stepper massivi o'zgaradi |
| **O-02** | Bozor **rekvizitlari to'plami** | RESEARCH A1: nom, manzil, STIR, bank hisobi, MFO, aloqa telefoni. A2: STIR 9 raqam — **rasmiy hujjatdan tasdiqlanmagan** | Kvitansiya/hisobot uchun majburiy maydon yetishmaydimi | Phase 0 ning buyurtmachi savollari bilan tasdiqlansin. UI 1-qadamni **ikki bo'limga** bo'ladi: «Asosiy» (nom, manzil, ish boshlangan sana) + «Rasmiy rekvizitlar» (STIR, bank) — ikkinchisi kengaytiriladigan (`<details>`), ya'ni maydon qo'shilishi layoutni buzmaydi |
| **O-03** | Xaritada **ikki o'lchovli klaviatura navigatsiyasi** kerakmi | §7.7 chiziqli harakat tanladi; sabab — `auto-fill` qatorining ma'nosi yo'q (D-19) | Skrinrider foydalanuvchilari 2D `role="grid"` kutadimi | Chiziqli bilan boshlanadi; a11y ko'rigida (8-faza uchidan-uchiga tekshiruvi) qayta baholanadi. O'tish narxi — faqat `stall-map.tsx` |
| **O-04** | **Rasta holatlari o'rtasidagi o'tish qoidalari** | RESEARCH A4: `active`/`maintenance`/`closed`; yopiq va ta'mirdagi rastaga hisob yozilmaydi | `closed` → `active` ga **qaytish** mumkinmi? Agar yo'q bo'lsa D-2 tasdig'i "abadiy" deb yozilishi kerak; agar ha bo'lsa matn yumshaydi | Hozircha D-2 matni "boshqa hech qachon ishlatilmaydi" deb rasta **raqami** haqida gapiradi (bu D-02 dan aniq), rasta holati haqida emas. Qaytish qoidasi aniqlangach matn qayta ko'riladi |
| **O-05** | **Import shabloni ustun nomlari** qaysi tilda | RESEARCH A6: `kod, zona, toifa, holat, izoh` | Shablon uchala tilda beriladimi yoki faqat foydalanuvchi tilida? Karmananing mavjud ro'yxati qaysi ustunlarda? | Shablon **foydalanuvchi tilida** hosil qilinadi (`XlsxWriter`), lekin parser ustunni **pozitsiya bo'yicha** o'qiydi — shunda tilni almashtirish importni buzmaydi. Bu reja qarori sifatida tasdiqlansin |
| **O-06** | **Kim ish kunlarini o'zgartiradi** | MARKET-05 "Bozor admini"; RESEARCH Open Question 4 direktor tasdig'ini so'ragan | Maker-checker kerakmi | MVP: bozor admini + majburiy audit. UI'da D-5 tasdig'i (§10.6) bu amalning og'irligini ko'rsatadi |
| **O-07** | `ru.json` matnlarini **kim tasdiqlaydi** | §10 dagi ru matnlar bu hujjatda taklif qilindi | Ona tilida so'zlashuvchi ko'rigi bo'ladimi (ayniqsa "торговое место" atamasi Karmana kontekstida to'g'rimi) | Go-live'gacha ona tilida so'zlashuvchi ko'rigi — 8-faza «uch tilli interfeys yakuniy tekshiruvi» mezoniga kiritilsin |

---

## Checker Sign-Off

- [x] Dimension 1 Copywriting: PASS
- [x] Dimension 2 Visuals: PASS
- [x] Dimension 3 Color: PASS
- [x] Dimension 4 Typography: PASS
- [x] Dimension 5 Spacing: PASS
- [x] Dimension 6 Registry Safety: PASS

**Approval:** approved 2026-07-31 — `gsd-ui-checker`, 6/6 dimension PASS.
Checker 11 ta WCAG kontrast da'vosini mustaqil qayta hisoblab, 2 xonagacha tasdiqladi.
Tasdiqdan keyin ikkita tavsiya kiritildi:
§12.1.1 (W0-12 ning to'liq 6 bandli zanjiri + X-1…X-4 xavfsizlik ta'siri) va
§10.6 (destruktiv amal tugmalarining o'z matni, uch tilda).

---

*Phase: 02-bozor-domeni-va-yangi-bozor-ustasi*
*UI-SPEC yaratildi: 2026-07-31 — `gsd-ui-researcher`*
*Upstream: 02-CONTEXT.md (D-01…D-20), 02-RESEARCH.md (Pattern 5, 11 + Scope Fence), 01-CONTEXT.md (D-14, D-16), ROADMAP Phase 2, CLAUDE.md*
