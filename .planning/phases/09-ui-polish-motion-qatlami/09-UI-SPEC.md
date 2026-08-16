---
phase: 09-ui-polish-motion-qatlami
status: approved
reviewed_at: 2026-08-17
shadcn_initialized: false
preset: none
design_system: shadcn-pattern (manual, CVA + Radix — 1/2-faza tokenlari)
response_language: uz-Latn
inherits: .planning/phases/08-hisobotlar-mustahkamlash-va-ishga-tushirish/08-UI-SPEC.md
created: 2026-08-17
---

# Phase 9 — UI-polish, motion qatlami: UI dizayn kontrakti

> Bitta va'daning vizual kontrakti: **ilova javob beradi — va javobi ko'rinadi.**
> 8-fazaning UI'si «raqamni faylga o'tkazish» edi. Bu fazaniki — **raqam va holat o'zgarganini foydalanuvchi KO'ZI bilan tasdiqlashi.** Farq shundaki, bu yerda nuqson hech qanday raqamni buzmaydi: u **ishonchni** buzadi. Kassir 300–1000 marta tugma bosadi va har safar «yozildimi?» deb ikkilanadi; direktor panelni ochadi va bo'shlikka qaraydi. Ikkalasi ham «tizim sekin» deb ataladi, holbuki server 40 ms da javob bergan.
> ⛔ Bu faza dizayn tizimini **meros qilib oladi va jilo qo'shadi** — **REDESIGN EMAS**. ROADMAP Chegaralari so'zma-so'z: «redesign EMAS — mavjud dizayn-tizim ustiga». Yangi bo'shliq shkalasi, yangi komponent kutubxonasi, yangi tipografiya roli (Display-XL dan **tashqari**, u qulflangan) yoki mavjud `G-*` darvozalarini yumshatish — **o'zi nuqson** bo'lardi.
> ⛔⛔ Bu fazaning barcha dizayn qarorlari **foydalanuvchi tomonidan 2026-08-16 da tasdiqlangan** (sketch 001/002 g'oliblari). Ular bu hujjatda **qayta ochilmaydi** — shartnoma sifatida yoziladi.
> Yaratdi: `gsd-ui-researcher`. Tekshiradi: `gsd-ui-checker`. Iste'mol qiladi: `gsd-planner`, `gsd-executor`.

---

## 0. Dalil holati va shu sessiyada bajarilgan o'lchovlar

| Belgi | Ma'nosi |
|-------|---------|
| **[O'LCHANDI]** | Shu sessiyada kodbazada yoki skript bilan o'lchandi — natija keltirilgan |
| **[KOD]** | Kodbazadan o'qildi — aniq `fayl:qator` keltirilgan |
| **[QULF]** | Foydalanuvchi tasdiqlagan qaror (sketch 001/002, 2026-08-16) — **qayta ochilmaydi** |
| **[MEROS]** | Upstream artefaktdan (ROADMAP Phase 9, masterplan, 08/07/06/05-UI-SPEC, CLAUDE.md) |
| **[QAROR]** | Shu hujjatda qabul qilindi — sabab yozilgan, muqobil rad etilgan |
| **[TALAB]** | UI backend'dan talab qiladigan narsa — rejaga bevosita kiradi |
| **[ASSUMED]** | Dalilsiz tanlangan qiymat — sabab va tetigi yozilgan |

### 0.1 O'lchovlar

| # | O'lchov | Natija |
|---|---------|--------|
| **M-1** | **shadcn darvozasi** — `find . -maxdepth 3 -name components.json` | **0 natija** → `Tool: none` (§3.1). 2–8-faza qarori davom etadi |
| **M-2** | **`ui/` primitivlari** — `ls frontend/src/components/ui/` | **10 primitiv** (`badge, button, card, confirm-dialog, dialog, empty-state, field, input, select, skeleton`). ⛔ 9-fazada **yangi `ui/` primitivi qurilmaydi** (§3.3) |
| **M-3** | ⛔⛔ **`ease-*` utilitasi kodbazada** — `grep "ease-out\|ease-in\|ease-linear\|ease-\["` | ⛔ **0 marta.** Ya'ni `--ease-out` ni `@theme` da **qayta ta'riflash bugungi kodga 0 ta'sir qiladi** — u faqat kelajakdagi ishlatishga qo'llanadi. **Bu §4.2 ning butun asosi** |
| **M-4** | **`duration-*` utilitasi** [KOD: `ui/button.tsx:14`] | ⛔ **Aynan 1 marta**: `transition-colors duration-150`. Ya'ni token reyestrini yopish uchun **bitta** qatorni ko'chirish yetarli (§4.3) |
| **M-5** | **`transition*` utilitalari** | **30 marta**, ⛔ **hammasi `transition-colors`** — ya'ni bugungi ilovada **birorta geometrik animatsiya YO'Q** va yangi qatlam bo'sh maydonga tushadi |
| **M-6** | ⛔ **`motion-reduce:` qamrovi** | **3 ta mahsulot joyi**: `ui/skeleton.tsx:31`, `snapshots/capture-cell.tsx:273`, `stalls/stall-cell.tsx:127`. ⛔ **`@media (prefers-reduced-motion)` globals.css da UMUMAN YO'Q** — G-motion-1 aynan shu bo'shliqni yopadi |
| **M-7** | ⛔ **`animate-spin` (aylanuvchi spinner)** | **5 joy**: `collect/payment-bar.tsx:293`, `collect/shift-close-form.tsx:280`, `collect/shift-open-card.tsx:154`, `review/decision-bar.tsx:150`, `snapshots/capture-cell.tsx:273`. ⛔ **Beshtadan FAQAT bittasida** `motion-reduce:animate-none` bor — qolgan 4 tasi **o'lchangan nuqson** (§12.2) |
| **M-8** | ⛔ **`active:scale` presedenti** [KOD: `stalls/stall-cell.tsx:127`] | `"active:scale-[0.97] motion-reduce:scale-100"` — ⛔ **bosish-masshtabi naqshi ALLAQACHON mavjud va reduced-motion bilan JUFT**. §12.1 uni `ui/button.tsx` ga ko'taradi, ixtiro qilmaydi |
| **M-9** | ⛔⛔ **Xoreografiyaning 6-qadami ALLAQACHON YASHIL** [KOD: `collect/collect-session.tsx:281-288`] | `setDraft("")` + `setMethod(null)` + `inputRef.current?.focus()` — ⛔ «qidiruv tozalanadi + fokus» **bugundan ishlaydi**. 9-faza 1–5-qadamlarni qo'shadi va ⛔ **6-qadamga TEGMAYDI** (§8.3) |
| **M-10** | ⛔⛔ **`daily_plan` / `target` KONSEPSIYASI UMUMAN YO'Q** — `services/core-api/app/**` va `frontend/src/lib/**` skani | **0 natija** (topilganlar — `zone-geometry` va `use-nvr-auth-lock` dagi begona `target` o'zgaruvchilari). ⛔ **Konfetti tetigining haqiqat manbai MAVJUD EMAS** (§9) |
| **M-11** | ⛔⛔ **Ko'r deklaratsiya darvozasi TIRIK** [KOD: `scripts/collect-surface.test.mjs:117,142`] | `MIN_FORBIDDEN_NAMES = 14`, `BLIND_DECLARATION_TOKENS` ichida `payment_count`, `system_total_soum`, `variance`. ⛔ Masterplan §6.2 dagi «**Bugun yig'ildi**» mini-hisoblagichi **shu darvozani buzadi** (§9.2) |
| **M-12** | ⛔ **`useMarketPending` iste'molchilari** | ⛔ **Aynan 1**: `components/billing/pending-summary.tsx:72` — ya'ni bozor kesimidagi `pending_amount_soum` **kassir yuzasiga hech qachon yetmagan** va yetmasligi kerak |
| **M-13** | **Direktor «paneli» bugun nima** [KOD: `app/[locale]/(app)/dashboard/page.tsx`] | Sarlavha + rol yorliqlari + **`HeadlineCard` (BITTA ko'rsatkich)** + `MarketStatusCard` (faqat `platform_admin`) + 2 ta navigatsiya kartasi. ⛔ **Masterplan §6.3 ning 2-ustunli grid'i (sparkline · donut · qarzdorlik · lenta) QURILMAGAN** (§10.1) |
| **M-14** | **Diagramma bog'liqligi** | `recharts` `package.json` da **yo'q**; ⛔ sketch 001/002/003 fayllarida `cdn`/`unpkg`/`<script src` — **0 marta**, ya'ni butun xoreografiya **sof CSS/JS bilan isbotlangan** (§3.2) |
| **M-15** | ⛔⛔ **KONTRAST DARVOZASI YO'Q** — `grep -l "contrast\|wcag" frontend/scripts/*` | **0 natija.** `globals.css` dagi **6 ta o'lchangan nisbat** (4.81 · 3.64 · 3.49 · 3.32 · 4.72 · 5.31) — ⛔ **qo'lda yozilgan da'volar**, mexanik qo'riqchisiz. Bu faza fonni o'zgartiradi, ya'ni **hammasi qayta o'lchanadi** (§5.5, G-motion-5) |
| **M-16** | ⛔ **Kontrast matematikasi TASDIQLANDI** — mustaqil skript `globals.css` da yozilgan nisbatlarni qayta hisobladi | ⛔ **To'rttasi ham AYNAN mos**: `text-muted/surface-muted` **4.81**, `border-ui/surface` **3.64**, `border-ui/bg` **3.49**, `border-ui/surface-muted` **3.32**. Ya'ni G-motion-5 ni **shu matematika ustiga** qurish mumkin |
| **M-17** | ⛔⛔ **ILIQ FON MAVJUD MATN TOKENLARINI BUZMAYDI** [O'LCHANDI] | `#FAFAF9` fonida: `text` **17.15:1** · `text-muted` **5.06:1** · `border-ui` **3.49:1**; iliq `surface-muted` (`#F5F5F4`) fonida: `text-muted` **4.84:1** · `border-ui` **3.34:1**. ⛔ **Hammasi AA dan o'tadi** → matn tokenlari **TEGILMAYDI** (§5.2) |
| **M-18** | ⛔⛔ **DARK REJIM SKETCH TOKENLARI BILAN AA'DAN O'TMAYDI** [O'LCHANDI] | Sketch `.dark-scope` faqat `bg/surface/border/text` ni almashtiradi. Natija: `success-text` **2.82:1** · `danger-text` **2.61:1** · `warning-text` **2.86:1** · `accent-text` **2.83:1** · `accent` **3.65:1** — ⛔ **beshtasi ham buzilish.** Dark scope **semantik matn tokenlarini HAM** qayta ta'riflashi SHART (§5.3) |
| **M-19** | ⛔⛔ **REAL, BUGUN RENDER BO'LAYOTGAN NUQSON** [KOD: `review/page.tsx:217`, `blind-audit/blind-session.tsx:212`] | `"bg-accent … text-accent-text"` → o'lchandi: **1.28:1**. ⛔ Matn deyarli **ko'rinmaydi**. To'g'ri token — `text-accent-fg` (**4.72:1**). Bu **bir so'zlik** tuzatish va u shu fazaga kiradi (§5.6) |
| **M-20** | **Latent token xavfi** [O'LCHANDI] | `success-fg` (oq) `bg-success` ustida — **3.27:1** (AA buzilishi). ⛔ **LEKIN bu juftlik kodda HECH QAYERDA yo'q** (`bg-success` + `text-success-fg` — 0 marta). Latent qoladi va G-motion-5 uni **e'lon qilingan juftlik** sifatida ushlaydi (§5.6) |
| **M-21** | **Tipografiya sanog'i** — `text-*` uchrashlari | `text-sm` **435** · `text-xs` **175** · `text-lg` **49** · `text-2xl` **35** · ⚠ `text-base` **7** · ⚠ `text-xl` **4** · `text-3xl` **0** · `text-[` **0**. ⛔ 9-faza oxirgi ikki deviatsiyaga **tegmaydi va yangisini qo'shmaydi** (§7.1) |
| **M-22** | **Og'irliklar** | `font-semibold` **222** · `font-normal` **45** · ⚠ `font-medium` **21** · `font-bold` **0**. ⛔ 2 og'irlik e'loni (400/600) kuchda; `font-medium` — meros deviatsiya, **o'smaydi** (§7.2) |
| **M-23** | **`tabular-nums` qamrovi** | **94 marta**. ⛔ Qamrov keng, lekin **e'lon qilinmagan** — §7.3 uni token darajasida majburlaydi |
| **M-24** | **Skeleton qamrovi** | **54 fayl** `Skeleton` ni import qiladi/ishlatadi. ⛔ Ya'ni «skeleton qatlami» **allaqachon qurilgan** — 9-faza unga **shimmer** va **geometriya juftligi** qo'shadi (§10.2, §12.5) |
| **M-25** | ⛔ **Skeleton geometriyasi bugun MOS EMAS** [KOD: `headline/headline-card.tsx` `h-8`, `collect/pending-card.tsx:183` `h-9 w-40`] | Kontent `text-2xl leading-tight` ≈ **30px**, skeleton **32/36px**. Display-XL (44px qator qutisi) qo'shilsa farq **8–12px** ga chiqadi → ⛔ **CLS** (§12.5, G-motion-7) |
| **M-26** | **`dark:` Tailwind varianti** | ⛔ **0 marta.** (6 ta `dark` uchrashi — `snapshots` javobidagi **maydon nomi**, variant emas.) Ya'ni «komponent kodi o'zgarmaydi» qoidasi **bugundan yashil** va G-motion-4 uni shunday saqlaydi |
| **M-27** | **`prefers-color-scheme` / `data-theme`** | ⛔ **0 marta.** Tema infratuzilmasi **umuman yo'q** — §11 uni noldan quradi |
| **M-28** | **`<html>` elementi** [KOD: `app/[locale]/layout.tsx:66`] | `<html lang={locale} className="h-full">` — ⛔ `suppressHydrationWarning` **yo'q**, ya'ni §11.2 ning inline skripti uni **qo'shishi shart** |
| **M-29** | **Aksent byudjeti** — `bg-accent` (test fayllarsiz) | **9 uchrash**, shundan **to'yingan fon** sifatida **5** joy: `ui/button.tsx:21` (birlamchi tugma), `shell/locale-switcher.tsx:93`, `wizard/wizard-stepper.tsx:152`, `markets/setup/page.tsx:241`, va ⛔ **2 ta nuqsonli** (M-19). §5.4 reyestri shu o'lchovdan |
| **M-30** | **Matn katalogi hajmi** | **1362 / 1362 / 1362** (uz-Latn / uz-Cyrl / ru) — parity bugundan yashil |
| **M-31** | ⛔ **Transliteratsiya sinovi** — 17 ta nomzod satr `gen-cyrillic.mjs::transliterate()` dan o'tkazildi | ⛔ **0 defekt.** `Ko'rinish`→`Кўриниш`, `Yorug'`→`Ёруғ`, `Tungi`→`Тунги`, `Quyosh ostida`→`Қуёш остида`, `Kunlik plan bajarildi`→`Кунлик план бажарилди`, `So'nggi 7 kun`→`Сўнгги 7 кун`. ⛔ `uz-Cyrl.overrides.json` **tegilmaydi** (§14.4) |
| **M-32** | **Frontend darvoza raqamlari** | Eng katta band ID — **`G-43`** (08-UI-SPEC). ⛔ **LEKIN bu faza `G-44` dan boshlamaydi** — sabab §16.1 |
| **M-33** | ⛔⛔ **`G-18` e'lon darvozasi** [KOD: `bulk-action-surface.test.mjs:98,112-125`] | Regeks `` /^\|\s*\*\*G-18\*\*\s*\|/ `` **barcha** `*-UI-SPEC.md` fayllarini skanerlaydi va `SPEC_FILES.length === 1` talab qiladi. ⛔ **Oqibat: BU FAYL ham shunday qator YOZMAYDI.** `G-motion-*` nomlari regeksga tushmaydi — xavf yo'q (§16.1) |
| **M-34** | **Yo'q narsalar** | `components/dashboard/revenue-card.tsx`, `…/occupancy-donut.tsx`, `lib/use-theme.ts`, `lib/use-count-up.ts`, `lib/motion.ts`, `scripts/contrast.test.mjs` — **hech biri yo'q**. Barchasi shu fazada tug'iladi |

### 0.2 M-10 + M-11 ning oqibati — bu fazaning eng qimmat tuzog'i

```
collect-surface.test.mjs:130   BLIND_DECLARATION_TOKENS = [
                                 "system_soum", "system_total_soum", "expected_soum",
                                 "variance", …, "payment_count", "cash_count", … ]
payment-row.tsx:16            ⛔⛔ JAMI / YIG'INDI — HECH QANDAY SHAKLDA YO'Q.
```

Masterplan §6.2 kassir header'iga «**Bugun yig'ildi**» mini-hisoblagichini so'raydi, §4.1 esa konfettini «**kunlik plan bajarilganda**» yoqishni. ⛔ **Ikkalasi ham kassirdan YIG'INDI bilishni talab qiladi** — 6-fazaning ko'r naqd deklaratsiyasi esa aynan shuni **mexanik ravishda** taqiqlaydi: kassir o'z smenasining tizim summasini **deklaratsiyadan OLDIN** bilsa, ko'r deklaratsiya **arifmetika bilan buziladi** va nomuvofiqlik topish mexanizmi jimgina qadrsizlanadi.

> ⛔ Bu «intizom masalasi» emas: `MIN_FORBIDDEN_NAMES = 14` va `MIN_BLIND_DECLARATION_TOKENS = 7` chegaralari bilan darvoza **bugun tirik** va hisoblagich qo'shilgan zahoti **qizaradi**. Ya'ni masterplan §6.2 ning bu bandi — **kechroq yozilgan hujjatning eskirgan bandi**, mahsulot talabi emas.

**Tanlangan yo'l** (§9): xoreografiya **6 qadam bilan to'liq yetkaziladi**; konfetti **shartnoma sifatida to'liq yoziladi, LEKIN qurilmaydi** — chunki uning yagona halol tetigi (server bergan **mantiqiy bayroq**) bugun mavjud emas, klientdagi har qanday hosila esa ko'rlikni buzadi.

**Rad etilgan muqobillar:**

| Muqobil | Nega rad etildi |
|---------|------------------|
| Klientda `recent payments` ni qo'shib «bugun yig'ildi» chiqarish | ⛔ `payment-row.tsx` izohi so'zma-so'z: server oynasi **atayin 5 ta** va yig'uvchi amal **umuman yozilmaydi**. Bu G-7 ning to'g'ridan-to'g'ri buzilishi |
| `useMarketPending()` ni kassir yuzasiga ulash | ⛔ [M-12] u **bozor kesimidagi** `pending_amount_soum` ni beradi — kassirga **butun bozorning** qolgan summasini ochardi |
| «Kunlik plan» ni bozor sozlamasiga qo'shish | ⛔ Yangi migratsiya + API + usta maydoni + 3 tilli copy — **UI-polish fazasida mahsulot funksiyasi**. Va u kassir oldiga **plan raqamini** qo'yardi: bu boshqaruv qarori, dizayn qarori emas |
| Konfettini har to'lovda yoqish | ⛔ [QULF] — foydalanuvchi C variantini aynan shu sababdan rad etgan («sirk») |

---

## 1. Ko'lam

### 1.1 To'rtta yuza — ular teng og'ir emas

| # | Yuza | Nimaga javob beradi | Foydalanuvchi | Ustuvorlik |
|---|------|---------------------|---------------|------------|
| **Y-1** | ⛔ **Kassir vau-oqimi** — to'lov muvaffaqiyatining 6-qadam xoreografiyasi | «Yozildimi? Keyingi mijozga o'tsam bo'ladimi?» | Kassir | ⛔ **ENG YUQORI** |
| **Y-2** | **Direktor jonlanishi** — skeleton → stagger → count-up → sparkline/donut | «Bugun qanday ketyapti?» | Direktor, bozor admini | Yuqori |
| **Y-3** | ⛔ **Tema qatlami** — iliq baza · tungi · quyosh ostida | «Ekranni o'qiy olyapmanmi?» | Hamma rollar | Yuqori — ⛔ **va u a11y masalasi, did emas** |
| **Y-4** | **Komponent jilosi** — tugma, karta, dialog, forma, jadval, til almashtirgich | «Ilova javob beryaptimi?» | Hamma rollar | O'rta — ⛔ **lekin tarqoq** |

⛔ **Landing (`sbozor.uz`) BU FAZAGA KIRMAYDI** — u **Phase 10** niki [MEROS: topshiriq bandi 10 + ROADMAP]. `sketch-findings-bozor/references/landing-sehri.md` shu hujjatda **manba sifatida ishlatilmaydi**.

### 1.2 Y-1 nima uchun eng yuqori — va UI uni QANDAY jimgina buzadi

ROADMAP Phase 9 SC#1: *«…6-qadam xoreografiya ishlaydi va input ~150ms ichida keyingi mijozga tayyor — bayram bloklamaydi.»*

> Kassir tugmani bosadi. Ekran 700 ms davomida chiroyli bayram qiladi: check chiziladi, halqa uriladi, summa uchadi. Kassir esa **shu vaqtda** keyingi rasta kodini terishni boshlagan — chunki uning oldida navbat turibdi. ⛔ Agar bayram fokusni **ushlab tursa** yoki inputni **bloklasa**, birinchi 2–3 belgi yo'qoladi. Kassir kodni qayta teradi. **Har to'lovga +1 xato, +2 soniya.** Kunlik 400 to'lovda bu **13 daqiqa** va — muhimrog'i — kassir «tizim sekin» degan xulosaga keladi, holbuki server 40 ms da javob bergan.
> ⛔⛔ Ya'ni bu fazada **eng qimmat nuqson — bayramning o'zi**.

Beshta qoida **muzokarasiz** va §16 da darvozaga aylanadi:

| # | Qoida | Nega UI qatlamida ham kerak |
|---|-------|------------------------------|
| **1** | ⛔ **Bayram BLOKLAMAYDI** — u fokusni ham, inputni ham, klaviaturani ham ushlamaydi | [QULF] «Jami ~700ms, lekin bloklamaydi — input ~150ms ichida yana tayyor» (**G-motion-2**) |
| **2** | ⛔ **`prefers-reduced-motion` da HAMMASI o'chadi** — natija **ayni**, faqat harakatsiz | Vestibulyar buzilish — a11y talabi, sozlama emas (**G-motion-1**) |
| **3** | ⛔ **Faqat `transform` va `opacity`** — `width`/`height`/`top`/`left` animatsiya QILINMAYDI | Arzon Androidda layout-thrash 60fps ni o'ldiradi (**G-motion-3**) |
| **4** | ⛔ **Kassir HECH QACHON yig'indi ko'rmaydi** — bayram ham bundan istisno emas | §0.2 — ko'r deklaratsiya (**G-motion-6**) |
| **5** | ⛔ **Skeleton kontent bilan BIR O'LCHAMDA** | Aks holda count-up CLS ni tug'diradi va Lighthouse byudjeti yiqiladi (**G-motion-7**) |

### 1.3 ROADMAP mezonlarining qamrovi

| SC | UI'da qanday ko'rinadi |
|----|------------------------|
| **SC#1** | Y-1 — §8 ning 6 qadami, har biri **aniq timing** va **aniq ulanish nuqtasi** bilan |
| **SC#2** | Y-2 — §10; ⛔ «direktor paneli» **`/dashboard`** deb aniq ta'riflanadi (§10.1) va sparkline/donut **mavjud endpointlardan** quriladi |
| **SC#3** | Y-3 — §11; uchala tema **token-scope**, `dark:` varianti **0** |
| **SC#4** | **G-motion-1** va **G-motion-2** — §16.4, ikkalasi ham **sabotaj bilan** |
| **SC#5** | **G-motion-3** — GPU xossalari + ⛔ **yangi paket 0 KB** (§3.2) |

### 1.4 Bu faza UI'si NIMA QILMAYDI (to'lig'i §17)

Landing · konfettining o'zi (shartnoma bor, ijro yo'q) · masterplan §6.3 ning 2-ustunli dashboard qayta qurilishi · View Transitions API · plan-xarita zoom inersiyasi · kamera thumbnail'lari · 12 ta bo'sh-holat illustratsiyasi · Storybook · skrinshot-solishtiruv avtomatikasi.

---

## 2. Qulflangan qarorlar — shartnoma sifatida

⛔ Quyidagi o'nta band **foydalanuvchi tomonidan tasdiqlangan** (2026-08-16, sketch 001/002 g'oliblari). Ular **qayta so'ralmaydi va qayta ochilmaydi**.

| # | Qulflangan qaror | Manba | Bu hujjatdagi joyi |
|---|------------------|-------|--------------------|
| **L-1** | Iliq fon `#FAFAF9` — light temaning yangi bazasi; dark **token-scope** bilan | sketch 002-B | §5.2, §5.3, §11 |
| **L-2** | `--motion-fast:150ms` · `--motion-base:250ms` · `--motion-slow:400ms`; `--ease-out: cubic-bezier(0.22,1,0.36,1)`; `--ease-spring: cubic-bezier(0.34,1.56,0.64,1)` | sketch 001-B | §4 |
| **L-3** | To'lov muvaffaqiyati — **6-qadam** xoreografiya, aniq timinglar, jami ~700ms, ⛔ **BLOKLAMAYDI** | sketch 001-B | §8 |
| **L-4** | Konfetti ⛔ **FAQAT** kunlik plan bajarilganda; sessiyada **bir marta**; **12 zarra**, **600ms** | sketch 001-B | §9 |
| **L-5** | Dashboard: shimmer **1.5s** (⛔ spinner TAQIQ) → stagger **60ms** → count-up **600ms** + tick `scale(1.03)` → sparkline/donut **600ms**; case amber ⛔ **BIR marta** diqqat-halqa | sketch 002-B | §10 |
| **L-6** | Yangi to'lov real-vaqt: **400ms** yumshoq count + **bir marta** yashil «nafas» | sketch 002-B | §10.6 |
| **L-7** | **G-motion-1** (`prefers-reduced-motion`) va **G-motion-2** (kassir ≤150ms) — ikkalasi ham **testda o'lchanadi** | ROADMAP SC#4 | §16.4 |
| **L-8** | Faqat `transform`/`opacity`; motion kutubxonasi ⛔ **FAQAT** vau/layout uchun, **+35KB gzip MAX**; qolgani **sof CSS** | masterplan §8 | §3.2 — ⛔ **0 KB tanlandi** |
| **L-9** | Pul: **Display-XL (40px)** faqat summalar; `tabular-nums` **hamma raqamda** | masterplan §2 | §7.1, §7.3 |
| **L-10** | Landing ⛔ **bu SPEC'ga kirmaydi** — Phase 10 niki | Topshiriq | §1.1 |

⛔ **L-8 ning o'qilishi — bu hujjatning yagona «kengaytiruvchi» talqini va u ochiq yoziladi:** «+35KB gzip **MAX**» — **shift**, majburiyat emas. §3.2 o'lchov bilan ko'rsatadiki bu fazadagi **har bir** qulflangan animatsiya sof CSS + ~40 qator vanilla JS bilan bajariladi, ya'ni kutubxona **0 ta noyob imkoniyat** beradi. **0 KB ⊂ ≤35KB**, demak L-8 **buzilmaydi, eng qattiq shaklda bajariladi**.

---

## 3. Dizayn tizimi holati

### 3.1 shadcn darvozasi — natija [M-1]

**`components.json` topilmadi** → **`Tool: none`. `shadcn init` BAJARILMAYDI.** [QAROR — 2–8-faza qarorini davom ettiradi]

Sabablar: (1) `shadcn init` Tailwind 4 rejimida `globals.css` ga **o'z token nomlarini** yozadi va `--color-bg`/`--color-surface`/`--color-accent` yonida **ikkinchi dizayn tizimi** paydo bo'lardi — ⛔ **bu faza aynan token qatlamini qayta yozadi**, ya'ni to'qnashuv eng qimmat lahzada bo'lardi; (2) `shadcn` ning `dark` konvensiyasi `.dark` **class** ga tayanadi, bu faza esa `data-theme` **atributi** + **uch** tema (§11.1) — ⛔ ikki mexanizm bir faylda; (3) bu subagent kontekstida interaktiv savol vositasi yo'q.

**Oqibat:** `Registry Safety` darvozasi shadcn uchun **qo'llanmaydi** (§15, §19). Uchinchi tomon registry **yo'q**, vendored blok **yo'q**.

### 3.2 ⛔⛔ Yangi npm paketi — **YO'Q**, jumladan `motion` HAM

**[QAROR]** Bu fazada `package.json` ning `dependencies` bo'limi **o'zgarmaydi**.

| Qulflangan animatsiya | Kerakli mexanizm | Kutubxona kerakmi |
|---|---|---|
| 1-qadam: bosish `scale(0.97)` | CSS `:active` + `transform` [M-8 presedenti] | ⛔ Yo'q |
| 2-qadam: check-draw | SVG `stroke-dasharray/offset` + `@keyframes` | ⛔ Yo'q |
| 3-qadam: halqa pulsi | absolut element + `@keyframes` `scale`+`opacity` | ⛔ Yo'q |
| 4-qadam: summa uchishi | `getBoundingClientRect()` A→B + `transform` (FLIP) — **~40 qator** | ⛔ Yo'q |
| 5-qadam: qator qo'nishi | `@keyframes` `background`+`translateY` | ⛔ Yo'q |
| Count-up 400/600ms | `requestAnimationFrame` + kubik ease — **~25 qator** | ⛔ Yo'q |
| Skeleton shimmer 1.5s | `@keyframes` `background-position` | ⛔ Yo'q |
| Stagger 60ms | CSS `animation-delay` (indeks bo'yicha inline `--i`) | ⛔ Yo'q |
| Sparkline / donut chizilishi | SVG `stroke-dashoffset` + `transition` | ⛔ Yo'q |
| Dialog scale+fade | Radix `data-[state]` + CSS | ⛔ Yo'q |

⛔ **Dalil:** [M-14] sketch 001/002 fayllarida `cdn`/`unpkg`/`jsdelivr`/`<script src` — **0 marta**. Ya'ni foydalanuvchi tasdiqlagan xoreografiyaning **o'zi** kutubxonasiz qurilgan va tasdiqlangan.

**Nega bu shunchaki tejash emas:** Lighthouse Performance **≥90** *arzon Android profilida* — bu byudjetda 35 KB gzip (parse'dan keyin ~110 KB JS) **o'lchanadigan** yo'qotish; va 08-UI-SPEC §3.5 ning qoidasi kuchda: *«boshqa paket zarur bo'lsa, u UI-SPEC ga qaytariladi — jimgina `npm install` qilinmaydi»*.

**Qayta ko'rish tetigi:** agar reja bajarilishida 4-qadamning FLIP'i yoki dialog layout-animatsiyasi **o'lchangan** ravishda sof CSS bilan chiqmasa — `motion` **UI-SPEC ga qaytariladi**, byudjet **35 KB gzip**, va u **faqat** o'sha bitta joyda ishlatiladi.

### 3.3 Meros — o'zgarmaydi va qayta qurilmaydi

| Nima | Fayl | 9-fazada |
|------|------|----------|
| Tailwind 4 CSS-first `@theme` | `globals.css` | ⛔ **Kengayadi** (motion + text-display + tema), lekin ⛔ **`@theme inline` ISHLATILMAYDI** (§11.3) |
| `Button` (4 variant; `sm` 36 · `md` 40 · `lg` min 44px) | `ui/button.tsx` | Press-scale + `duration-(--motion-fast)` (§12.1) |
| `Card` | `ui/card.tsx` | Hover ko'tarilishi **faqat** `@media (hover:hover)` (§12.3) |
| `Skeleton` (`motion-reduce:animate-none`) | `ui/skeleton.tsx` | ⛔ `animate-pulse` → **shimmer** (§12.5) |
| `Dialog` (`sm/md/lg` + `sheetOnMobile`) | `ui/dialog.tsx` | Radix `data-[state]` + scale/fade (§12.4) |
| `EmptyState`, `Field`, `Input`, `Select`, `Badge`, `ConfirmDialog` | `ui/*` | ⛔ **Tegilmaydi** |
| `sonner` Toaster (`top-center richColors`) | `layout.tsx:82` | ⛔ **Sozlamasi TEGILMAYDI** (§12.6) |
| `nuqs`, `next-intl`, `react-query`, `rbac.ts` | — | ⛔ **Tegilmaydi** |
| `formatBusinessDay()` — sana | `lib/format-day.ts` | ⛔ **Yagona yo'l**, kengaymaydi (§13.1) |
| Pul: `useFormatter().number()` + `*.amountUnit` | `pending-summary.tsx:155` naqshi | ⛔ **Yagona yo'l** (§13.2) |
| Ko'r deklaratsiya darvozasi | `scripts/collect-surface.test.mjs` | ⛔ **Kuchayadi**, yumshamaydi (§16.4) |

### 3.4 Yangi `ui/` primitivi — YO'Q [M-2]

Uchta chegaraviy holat **ataylab** `ui/` ga ko'tarilmaydi:

| Komponent | Nega `ui/` emas |
|-----------|------------------|
| `collect/success-choreography.tsx` | Uning kontrakti — **domen qoidasi**: 6 qadam, aniq timinglar, **bloklamaslik** majburiyati. `ui/` dagi «muvaffaqiyat animatsiyasi» ertaga `blocking` propini olardi |
| `dashboard/count-up.tsx` | ⛔ U **son formatlash** bilan juft ishlaydi (`useFormatter`, `tabular-nums`, butun so'm). `ui/` ga chiqarish uni «har qanday son» quroliga aylantirib, foizni ham sanashga taklif qilardi |
| `shell/theme-toggle.tsx` | Uchta tema — **mahsulot reyestri** (§11.1), umumiy «tema tugmasi» emas |

---

## 4. Motion token reyestri — YOPIQ

### 4.1 `@theme` ga qo'shiladigan qiymatlar [L-2]

```css
@theme {
  /* ---- Harakat davomiyligi — YOPIQ REYESTR (3 qiymat) --------------- */
  --motion-fast: 150ms;   /* bosish javoblari, hover, chiqish */
  --motion-base: 250ms;   /* dialog, sahifa elementlari, kirish */
  --motion-slow: 400ms;   /* sahna almashinuvi, bayram, uchish */

  /* ---- Ease egri chiziqlari — Tailwind `--ease-*` NAMESPACE'i ------- */
  --ease-out: cubic-bezier(0.22, 1, 0.36, 1);      /* standart tormoz */
  --ease-spring: cubic-bezier(0.34, 1.56, 0.64, 1); /* vau-lahzalar */

  /* ---- Pul roli (§7.1) --------------------------------------------- */
  --text-display: 2.5rem;              /* 40px */
  --text-display--line-height: 1.1;    /* 44px qator qutisi */
}
```

| Token | Qiymat | ⛔ Ishlatiladigan YAGONA joy |
|-------|--------|------------------------------|
| `--motion-fast` | 150ms | Tugma press/hover, chiqish animatsiyalari, badge crossfade |
| `--motion-base` | 250ms | Kirish (8px pastdan + fade), dialog, check-draw, karta hover |
| `--motion-slow` | 400ms | Summa uchishi, case sirg'alishi, real-vaqt count |
| `--ease-out` | `cubic-bezier(0.22,1,0.36,1)` | ⛔ **Standart** — boshqa egri chiziq **ko'rsatilmasa shu** |
| `--ease-spring` | `cubic-bezier(0.34,1.56,0.64,1)` | ⛔ **AYNAN 2 joy**: toast kirishi, rasta yon panelining ochilishi |
| `--text-display` | 40px / 1.1 | ⛔ **AYNAN 2 joy** — §7.1 |

⛔ **Reyestrdan tashqari davomiylik YOZILMAYDI.** 800ms (5-qadam, qator qo'nishi), 600ms (count-up, sparkline), 1.5s (shimmer), 300ms (halqa) — bular **kompozit** qiymatlar va ular **`@keyframes` ta'rifining ichida**, utilita sifatida emas (§4.3).

### 4.2 ⛔ `--ease-out` — Tailwind'ning O'RNATILGAN qiymatini QAYTA TA'RIFLAYDI [QAROR]

Tailwind 4 standarti: `--ease-out: cubic-bezier(0, 0, 0.2, 1)`. Bizniki — `cubic-bezier(0.22, 1, 0.36, 1)`.

⛔ **Bu ataylab va u XAVFSIZ, chunki O'LCHANDI [M-3]: kodbazada `ease-*` utilitasi — 0 marta.** Ya'ni qayta ta'rif **bugungi birorta pikselni** o'zgartirmaydi; u faqat 9-fazadan keyingi ishlatishga qo'llanadi va «yumshoq tormoz» butun ilovada **bitta joydan** boshqariladi.

**Rad etilgan muqobil:** `--ease-out-soft` deb **yangi nom** olish. ⛔ Rad sababi: shunda ikki egri chiziq yonma-yon yashaydi va ijrochi `ease-out` (Tailwind'niki) yozganda **jimgina noto'g'ri** natija oladi — nom to'qnashuvi **xatoni ko'rinmas** qilardi. Bitta nom, bitta ma'no.

### 4.3 ⛔ Sehrli son taqiqi — `duration-<raqam>` YOZILMAYDI

| Bugun | 9-fazadan keyin |
|-------|------------------|
| `duration-150` [M-4, `ui/button.tsx:14`] | `duration-(--motion-fast)` |
| — | ⛔ `duration-` + raqam **0 marta** (**G-motion-3(b)**) |

Tailwind 4 ning `(--var)` sintaksisi (`duration-(--motion-base)`, `ease-(--ease-spring)`) tokenni **utilitaning o'zida** manba qiladi. `@keyframes` ichida esa `var(--motion-*)` to'g'ridan-to'g'ri ishlatiladi.

⛔ **Istisno — `@keyframes` ta'riflari:** 800ms/600ms/300ms/1.5s qiymatlari `globals.css` ning `@layer components` blokidagi **nomlangan** animatsiyalarda yashaydi (`--animate-*` orqali emas: ular komponentga xos, utilita emas). Har biri yonida **izoh bilan sababi** yoziladi. ⛔ Ular **komponent faylida** takrorlanmaydi (**G-motion-3(c)**).

### 4.4 Xoreografiya qoidalari [MEROS: masterplan §3.2]

| # | Qoida |
|---|-------|
| 1 | **Kirish:** `translateY(8px)` + `opacity 0→1`, `--motion-base`, `--ease-out`; ro'yxatlarda stagger **60ms** |
| 2 | **Chiqish:** kirishdan **2× tez** (`--motion-fast`) — ketayotgan narsa ushlab turmaydi |
| 3 | **Dialog:** trigger'dan `scale(0.96)` + fade; fon **8%** qorayadi + `blur(4px)` |
| 4 | ⛔ **HECH QACHON:** cheksiz pulsatsiya · foydalanuvchi boshlamagan avtomatik harakat · kontent yuklanishida **aylanuvchi spinner** |
| 5 | ⛔ **`prefers-reduced-motion`:** hamma harakat **0.01ms** ga tushadi, faqat oxirgi holat qoladi |

---

## 5. Rang 2.0 — uchta tema, bitta token lug'ati

### 5.1 60/30/10 — o'zgarmaydi

| Rol | Token | Ulush |
|-----|-------|-------|
| Dominant (60%) | `--color-bg` | Sahifa foni |
| Ikkilamchi (30%) | `--color-surface` + `--color-surface-muted` | Kartalar, panel, header |
| Aksent (10%) | `--color-accent` | §5.4 reyestri |
| Destruktiv | `--color-danger` | Faqat destruktiv amal |

### 5.2 ⛔ Light tema — ILIQ BAZA [L-1]. O'zgaradigan AYNAN 3 token

⛔ **Bu fazaning eng ehtiyotkor qarori.** `globals.css` dagi matn/chegara tokenlari **o'lchangan WCAG izohlari** bilan keladi (07/08-fazalarda sozlangan). Fonni iliqlashtirish ularning **hammasini qayta ochadi** — shuning uchun **[O'LCHANDI, M-17]** va **eng kichik** o'zgarish tanlandi:

| Token | Bugun | ⛔ 9-fazada | Manba |
|-------|-------|-------------|-------|
| `--color-bg` | `oklch(0.985 0 0)` | **`oklch(0.985 0.001 106)`** | `#FAFAF9` (stone-50) |
| `--color-surface-muted` | `oklch(0.968 0 0)` | **`oklch(0.970 0.001 106)`** | `#F5F5F4` (stone-100) |
| `--color-border` | `oklch(0.916 0 0)` | **`oklch(0.923 0.003 49)`** | `#E7E5E4` (stone-200) |
| `--color-surface` | `oklch(1 0 0)` | ⛔ **O'ZGARMAYDI** | warm.css ham `#FFFFFF` deydi |
| `--color-text` | `oklch(0.205 0 0)` | ⛔ **O'ZGARMAYDI** | §5.2.1 |
| `--color-text-muted` | `oklch(0.53 0 0)` | ⛔ **O'ZGARMAYDI** | §5.2.1 |
| `--color-border-ui` | `oklch(0.62 0 0)` | ⛔ **O'ZGARMAYDI** | §5.2.1 |
| Semantik tokenlar (`success`/`warning`/`danger`/`accent` + `-text`/`-fg`) | — | ⛔ **O'ZGARMAYDI** | §5.2.1 |

#### 5.2.1 ⛔ Nega matn tokenlari TEGILMAYDI — o'lchov bilan [M-17]

| Juftlik | Iliq fonda o'lchandi | AA chegarasi | Holat |
|---------|----------------------|--------------|-------|
| `text` / iliq `bg` | **17.15:1** | 4.5 | ✅ (bugun 17.16) |
| `text-muted` / iliq `bg` | **5.06:1** | 4.5 | ✅ |
| `text-muted` / iliq `surface-muted` | **4.84:1** | 4.5 | ✅ (bugun 4.81) |
| `border-ui` / iliq `bg` | **3.49:1** | 3.0 | ✅ (bugun 3.49) |
| `border-ui` / iliq `surface-muted` | **3.34:1** | 3.0 | ✅ (bugun 3.32) |
| `accent-text` / `accent/10` iliq | **5.11:1** | 4.5 | ✅ |
| `success-text` / `success/12` iliq | **5.17:1** | 4.5 | ✅ |
| `warning-text` / `warning/20` iliq | **5.10:1** | 4.5 | ✅ |
| `danger-text` / `danger/12` iliq | **5.30:1** | 4.5 | ✅ |

**Rad etilgan muqobil:** `warm.css` ning matn qiymatlarini ham olish (`#1C1917` va `#57534E`). ⛔ Rad sababi ikki qavat: (a) `#57534E` `text-muted` ni **7.30:1** ga chiqaradi — bu **ierarxiyani yassilaydi** (muted matn asosiy matnga yaqinlashadi) va u dizayn niyati emas; (b) 0.006 xromali «iliq» matn **ko'z bilan farqlanmaydi**, lekin **uchta yopilgan o'lchovni qayta ochadi**. ⛔ Iliqlik **yuzalardan** keladi, matndan emas.

### 5.3 ⛔⛔ Dark tema — sketch tokenlari YETARLI EMAS [M-18]

Sketch `.dark-scope` **oltita** o'zgaruvchini almashtiradi. O'lchov ko'rsatdi: shu holicha jo'natilsa, **beshta semantik matn tokeni AA dan o'tmaydi**. Shuning uchun dark scope **to'liq** yoziladi:

| Token | Dark qiymat | O'lchandi (`surface` fonida) |
|-------|-------------|------------------------------|
| `--color-bg` | `oklch(0.17 0.005 260)` | — |
| `--color-surface` | `oklch(0.22 0.006 260)` | — |
| `--color-surface-muted` | `oklch(0.26 0.006 260)` | — |
| `--color-border` | `oklch(0.32 0.008 260)` | — |
| `--color-border-ui` | `oklch(0.55 0.008 260)` | ⛔ chegara ≥3:1 |
| `--color-text` | `oklch(0.95 0 0)` | **14.96:1** ✅ |
| `--color-text-muted` | `oklch(0.72 0 0)` | **6.98:1** ✅ |
| ⛔ `--color-accent` | **`oklch(0.64 0.15 255)`** | **5.02:1** (sketch qiymatida **3.65** ❌) |
| ⛔ `--color-accent-text` | **`oklch(0.64 0.14 255)`** | **5.03:1** (bugungi qiymat **2.83** ❌) |
| ⛔ `--color-success-text` | **`oklch(0.62 0.14 150)`** | **5.05:1** (bugungi **2.82** ❌) |
| ⛔ `--color-warning-text` | **`oklch(0.64 0.10 85)`** | **5.02:1** (bugungi **2.86** ❌) |
| ⛔ `--color-danger-text` | **`oklch(0.65 0.13 27)`** | **5.04:1** (bugungi **2.61** ❌) |
| `--shadow-card` / `--shadow-raised` | ⛔ **quyuqroq** (`oklch(0 0 0 / 0.5)`) | Qorong'i fonda oq soya ishlamaydi |

⛔ Har bir qiymat **`surface-muted`** (eng yorug' fon, 0.26) da ham ≥**4.50:1** bo'lishi uchun yechildi — ya'ni **eng yomon holat** o'lchandi.

### 5.4 Aksent byudjeti — reyestr [M-29]

⛔ Aksent **to'yingan fon** sifatida **aynan beshta** joyda:

| # | Joy | Fayl |
|---|-----|------|
| 1 | Birlamchi tugma (`variant="default"`) | `ui/button.tsx:21` |
| 2 | Faol til tugmasi | `shell/locale-switcher.tsx:93` |
| 3 | Usta joriy qadami | `wizard/wizard-stepper.tsx:152` |
| 4 | Usta yakuniy CTA | `markets/setup/page.tsx:241` |
| 5 | ⛔ Kassir «To'lovni tasdiqlash» — `Button` orqali | `collect/payment-bar.tsx` |

Bulardan tashqari aksent: **fokus halqasi** · **faol maydon chegarasi** · **joriy mobil nav elementi** · `Badge tone="accent"` (`bg-accent/10`, **tint**). ⛔ Yangi aksentli yuza **qo'shilmaydi** — jumladan sparkline ham: u `accent` **chizig'i** + `accent/0.08` **maydoni** (tint), to'yingan fon emas.

### 5.5 ⛔ Kontrast — endi DA'VO emas, O'LCHOV [M-15, M-16]

⛔ **Bu fazaning eng uzoq ta'sirli hissasi.** Bugun `globals.css` da **oltita** nisbat izohda yozilgan va ularni **hech nima tekshirmaydi**. Shu sessiyada mustaqil skript ularni qayta hisobladi va **to'rttasi baytma-bayt mos tushdi** — ya'ni matematika ishonchli va uni darvozaga aylantirish mumkin.

`scripts/contrast.test.mjs` (**G-motion-5**) `globals.css` dan **tokenlarni parse qiladi**, e'lon qilingan **juftliklar reyestri** bo'yicha nisbatni hisoblaydi va uchala temada tekshiradi. ⛔ Izohdagi son bilan hisoblangan son **farq qilsa — qizaradi** (izohlar endi **mashina o'qiydigan da'vo**).

### 5.6 O'lchangan ikki nuqson — biri tuzatiladi, biri qo'riqlanadi

| # | Nuqson | Holat |
|---|--------|-------|
| **M-19** | `"bg-accent … text-accent-text"` → **1.28:1** [KOD: `review/page.tsx:217`, `blind-audit/blind-session.tsx:212`] | ⛔ **TUZATILADI** — `text-accent-text` → `text-accent-fg` (**4.72:1**). Ikki fayl, ikki so'z; redesign emas, **token xatosi** |
| **M-20** | `success-fg` (oq) `bg-success` ustida → **3.27:1** | ⛔ **Kodda ishlatilmaydi.** G-motion-5 uni **e'lon qilingan juftlik** sifatida ushlaydi va `--color-success-fg` **quyuq** qiymatga (`oklch(0.205 0 0)`, **5.48:1**) o'tkaziladi — ⛔ **hech qanday piksel o'zgarmaydi**, latent tuzoq esa yopiladi |

---

## 6. Bo'shliq — o'zgarmaydi

4-panjara: **4 · 8 · 12 · 16 · 24 · 32 · 48**. **Istisnolar:** 44px barmoq nishoni · 56px mobil panel/tasdiq tugmasi · 20px karta ichki `x`.

⛔ **Yangi istisno YO'Q.** Motion `transform` bilan ishlaydi — u **bo'shliq so'ramaydi**. Xoreografiyaning yagona geometrik qiymati — kirish `translateY(**8px**)`, u **panjara a'zosi**.

---

## 7. Tipografiya

### 7.1 ⛔ Beshinchi rol — Display-XL, YOPIQ QAMROV bilan [L-9]

| Rol | O'lcham | Og'irlik | Satr balandligi | Utilita |
|-----|---------|----------|-----------------|---------|
| ⛔ **Display-XL** | **40px** | 600 | **1.1** | `text-display` |
| Heading | 24px | 600 | 1.2 | `text-2xl` |
| Subheading | 18px | 600 | 1.3 | `text-lg` |
| Body | 14px | 400 | 1.5 | `text-sm` |
| Caption | 12px | 400 | 1.4 | `text-xs` |

⛔⛔ **`text-display` — AYNAN IKKI joy va bu MEXANIK reyestr:**

| # | Joy | Shart |
|---|-----|-------|
| 1 | Kassir «Kutilayotgan patta» summasi [KOD: `collect/pending-card.tsx:273`] | Shartsiz |
| 2 | Direktor bosh ko'rsatkichi [KOD: `headline/headline-card.tsx`] | ⛔ **FAQAT `unit === "soum"`** — sanoq ko'rsatkichi `text-2xl` da qoladi |

**Nega shart:** `HeadlineCard` metrikasini **server** tanlaydi va u pul ham, **rasta soni** ham bo'lishi mumkin. «Pul — bosh qahramon» qoidasi **sanoqqa qo'llanmaydi**; 40px li «34» direktorga *«34 million»* bo'lib o'qilardi.

**Checker uchun izoh:** e'lon **5 o'lchamli** ko'rinadi, lekin **matn rollari — 4 ta** (24/18/14/12, [M-21] bilan tasdiqlangan); beshinchi — **raqamli display roli**, `text-display` **yopiq reyestr** bilan qulflangan (**G-motion-7(b)**: `text-display` ⛔ **≤2 mahsulot faylida**). Shkala tarqalishi mexanik ravishda **imkonsiz**.

### 7.2 Og'irliklar — 2 ta [M-22]

**400** (`font-normal`) + **600** (`font-semibold`). ⚠ `font-medium` (500) — **21 marta** meros deviatsiya; ⛔ 9-faza unga **tegmaydi va yangisini qo'shmaydi**.

⛔ **Quyosh rejimida og'irlik TOKEN orqali ko'tariladi** (§11.4) — komponent kodi o'zgarmaydi.

### 7.3 ⛔ `tabular-nums` — endi TASODIF emas [L-9]

Bugun **94 marta** qo'lda yozilgan [M-23]. 9-fazada:

```css
@layer base {
  /* Raqam ustunlari «sakramasin» — masterplan §2. */
  :where(table, .money, [data-numeric]) { font-variant-numeric: tabular-nums; }
}
```

⛔ Mavjud **94** ta qo'lda yozilgan sinf **olib tashlanmaydi** (ular zararsiz va ularni supurish 40+ faylga tegardi — bu faza uchun **shovqin**). Yangi kod `tabular-nums` ni **qo'lda yozmaydi**.

---

## 8. Y-1 — Kassir vau-oqimi: 6 qadam [L-3]

### 8.1 Xoreografiya — ijro shartnomasi

| # | Qadam | Davomiylik | Texnika | Ulanish nuqtasi |
|---|-------|-----------|---------|------------------|
| **1** | Tugma bosilishi | **100ms** | `:active` → `transform: scale(0.97)` | `ui/button.tsx` (§12.1) — ⛔ **barcha tugmalarga**, kassirga xos emas |
| **2** | Check-mark chiziladi | **250ms** (`--motion-base`) | SVG `stroke-dasharray:30; stroke-dashoffset:30→0` | `collect/payment-bar.tsx` — tugma **ichida**, `Loader2` o'rnida |
| **3** | Karta yashil halqa pulsi | **300ms** | absolut `.ring`, `scale(0.98→1.06)` + `opacity 0.9→0` | `collect/pending-card.tsx` o'ramida |
| **4** | Summa ro'yxatga uchadi | **400ms** (`--motion-slow`) | `position:fixed` klon, `getBoundingClientRect()` A→B, ⛔ **faqat `transform`+`opacity`** | `collect/success-choreography.tsx` (yangi) |
| **5** | Yangi qator qo'nadi | **800ms** | `background: success/0.18 → transparent`, `translateY(-4px→0)` | `collect/payment-row.tsx` — ⛔ **birinchi** render'da |
| **6** | Qidiruv tozalanadi + fokus | ⛔ **darhol** | `setDraft(""); inputRef.current?.focus()` | ⛔ **[M-9] ALLAQACHON BOR** — `collect-session.tsx:281-288`, **TEGILMAYDI** |

### 8.2 ⛔⛔ «Bloklamaydi» — bu niyat emas, MEXANIKA

| Talab | Mexanizm |
|-------|----------|
| Fokus 6-qadamda **darhol** qaytadi | 1–5-qadamlar `onWritten` **ichidan keyin** boshlanadi va ⛔ **hech biri `await` qilinmaydi** |
| Uchayotgan klon bosishni yutmaydi | ⛔ `pointer-events: none` **majburiy** (**G-motion-2(c)**) |
| Klon layoutni siljitmaydi | ⛔ `position: fixed` + `will-change: transform` — u **oqim ichida emas** |
| Animatsiya tugashini kutadigan holat yo'q | ⛔ `setTimeout` **faqat tozalash** uchun (`removeChild`), holat o'zgartirish uchun **emas** (**G-motion-2(d)**) |
| Klaviatura kirishi yo'qolmaydi | ⛔ Input `disabled` ham, `readOnly` ham **QILINMAYDI** — 3-fazadan beri o'rnatilgan `aria-disabled` naqshi |

### 8.3 ⛔ 6-qadamga tegmaslik — nega alohida yozilgan

[M-9] `onWritten` bugun **beshta** ishni bajaradi: kesh tozalash · maydon bo'shatish · to'lov turini nolga qaytarish · **fokusni qaytarish** · toast. ⛔ Xoreografiya bu ketma-ketlikka **oldindan** ham, **orasiga** ham qo'shilmaydi — u **oxirida**, `focus()` dan **keyin** boshlanadi.

> Sabab mexanik: `focus()` dan **oldin** DOM'ga `position:fixed` klon qo'shilsa, brauzer scroll-anchoring hisobini qayta qiladi va telefonda ⛔ **fokus qilingan input ekrandan chiqib ketishi** mumkin. Tartib — **shartnoma**, uslub emas.

### 8.4 Reduced-motion shoxi

| Qadam | `prefers-reduced-motion: reduce` da |
|-------|-------------------------------------|
| 1 | `scale` yo'q — `:active` da faqat fon quyuqlashadi |
| 2 | Check-mark ⛔ **darhol to'liq** ko'rinadi (chizilmaydi) |
| 3 | Halqa ⛔ **umuman chizilmaydi** |
| 4 | Klon ⛔ **umuman yaratilmaydi** |
| 5 | Qator fon rangisiz, **darhol** joyida |
| 6 | ⛔ **O'zgarmaydi** — u harakat emas, u **oqim** |

⛔ **Natija AYNI**: to'lov yozildi, ro'yxatda qator bor, fokus qidiruvda. Farq faqat **yo'lda**.

---

## 9. ⛔⛔ Konfetti — to'liq shartnoma, ijrosiz [L-4 + M-10]

### 9.1 Shartnoma (o'zgarishsiz saqlanadi)

| Xossa | Qiymat |
|-------|--------|
| Tetik | ⛔ **FAQAT** kunlik plan bajarilganda |
| Chastota | ⛔ Sessiyada **bir marta** |
| Zarralar | **12** |
| Davomiylik | **600ms** |
| Reduced-motion | ⛔ **Umuman chizilmaydi** |
| Texnika | 12 ta absolut `<span>`, `transform`+`opacity`, `pointer-events:none` |

### 9.2 ⛔ Nega bu fazada QURILMAYDI [QAROR]

[M-10] `daily_plan` · `daily_target` · `plan_soum` — ⛔ **backend'da ham, frontend'da ham 0 natija**. Tetikning **haqiqat manbai mavjud emas**.

Va uni klientda hosila qilishning **har bir** yo'li §0.2 ning ko'r deklaratsiya taqig'iga uriladi:

| Hosila yo'l | Nega imkonsiz |
|-------------|----------------|
| Kassirning oxirgi to'lovlarini qo'shish | ⛔ Server oynasi **atayin 5 ta**; `payment-row.tsx` da yig'uvchi amal **taqiqlangan** |
| `useMarketPending()` ni ulash | ⛔ [M-12] u **bozor kesimidagi** summani ochardi |
| «Yig'ilgan / hisoblangan» foizini olish | ⛔ `system_total_soum` — `BLIND_DECLARATION_TOKENS` ro'yxatida |

⛔ **Soxta tetik bilan yoqish** (masalan «har 50-to'lov») — ⛔ **TAQIQ**: u foydalanuvchi rad etgan C variantining («har to'lovda bayram») niqoblangan shakli bo'lardi va bayram **ma'nosini** yo'qotardi.

### 9.3 [TALAB] — bir qatorli yoqish sharti

> **Server `POST /payments` javobiga mantiqiy maydon qo'shadi:** `market_day_cleared: boolean` — *«shu to'lov bilan bugungi hisoblangan patta to'liq yig'ildi»* (ya'ni `pending_stall_count` **0** ga tushdi).
> ⛔ **Son emas, foiz emas, sanoq emas — MANTIQIY qiymat.** Kassir hech qanday summa olmaydi, ya'ni ko'rlik saqlanadi.
> ⚠ `paymentResponseSchema` — `z.strictObject`, ya'ni bu **kelishilgan, ikki tomonlama** o'zgarish; server yolg'iz qo'sha olmaydi (klient parse'da yiqiladi).

⛔ **Tetik kelgan kunda** ijro: `if (record.market_day_cleared && !firedThisSession && !reducedMotion) burst()`. Boshqa hech nima o'zgarmaydi. **Shartnoma shu hujjatda tayyor turadi.**

### 9.4 ⛔ Masterplan §6.2 ning «Bugun yig'ildi» hisoblagichi — RAD ETILADI

⛔ Sabab §0.2 da mexanik: `collect-surface.test.mjs` uni **qizartiradi**. ⛔ Bu **eskirgan hujjat bandi** (masterplan 2026-08-15, ko'r deklaratsiya 6-fazada 2026-08-11 da qulflangan). ⛔ **Motivatsiya** ehtiyoji rad etilmaydi — u **smena yopilgandan keyin** (deklaratsiya yozilgach) ko'rsatilishi mumkin; bu **v2 mahsulot savoli**, 9-fazaning UI qatlami emas (§17.1).

---

## 10. Y-2 — Direktor jonlanishi [L-5, L-6]

### 10.1 ⛔ «Direktor paneli» — bu hujjatda AYNAN NIMA [QAROR]

[M-13] Bugun `/dashboard` da: sarlavha · rol yorliqlari · **`HeadlineCard`** · `MarketStatusCard` (faqat `platform_admin`) · 2 navigatsiya kartasi. ⛔ Masterplan §6.3 ning **2-ustunli grid'i qurilmagan**.

**[QAROR] Ko'lam:** `/dashboard` ga ⛔ **AYNAN IKKI karta** qo'shiladi va ular **mavjud endpointlardan** oziqlanadi:

| Karta | Manba | Huquq |
|-------|-------|-------|
| **Tushum trendi** — 7 kunlik sparkline + davr yig'indisi | `GET /reports/revenue?from&to` (8-fazadan) | ⛔ `report_view` |
| **Bandlik halqasi** — donut (band / bo'sh) | Mavjud bandlik xulosasi (5-fazadan) | ⛔ `report_view` |

⛔⛔ **HUQUQ SHARTI MUZOKARASIZ:** `/dashboard` — **hamma rol** kiradigan sahifa va kassir navigatsiyasi aynan `/dashboard` + `/collect` [MEROS: 08 M-5]. ⛔ Agar tushum kartasi darvozasiz qo'yilsa — **kassir bozorning kunlik tushumini ko'radi** va ko'r deklaratsiya **butunlay** qulaydi. Shart komponentdan **tashqarida** bo'ladi (`cameras/page.tsx` naqshi): huquqsiz sessiyada **so'rov ham ketmaydi** (**G-motion-6(b)**).

⛔ **Nega sparkline `/reports` ga QO'YILMAYDI:** 08-UI-SPEC §17.2 diagrammani u yerda **uch sabab** bilan rad etgan; ikkitasi **hamon kuchda** — (a) diagramma `.xlsx` ga tushmaydi, ya'ni **ekran bilan hujjat ajralardi**; (b) trend **davrlararo** solishtiruvni taklif qiladi va u yerda javobsiz qolardi. ⛔ Uchinchi sabab (`recharts` yo'q) esa **yo'qoldi**: sparkline — **sof SVG** (§3.2). Dashboard esa **hujjat emas** — undan hech nima eksport qilinmaydi, shuning uchun (a) va (b) u yerda **qo'llanmaydi**. ⛔ **Ziddiyat yo'q: chegara «diagramma» emas, «hujjat yuzasi».**

### 10.2 Yuklanish → kontent

| Bosqich | Shakl |
|---------|-------|
| Skeleton | ⛔ **Shimmer 1.5s** (`background-position`, gradient `surface-muted → border → surface-muted`) |
| ⛔ Spinner | ⛔ **TAQIQ** — kontent yuklanishida aylanuvchi spinner **yo'q** (§12.2 istisnosi bilan) |
| Kontent kelishi | Crossfade; kartalar **stagger 60ms** bilan, `translateY(8px)` + fade, `--motion-base` |

### 10.3 Count-up [L-5]

| Ko'rsatkich | Davomiylik | Tick |
|-------------|-----------|------|
| Bosh ko'rsatkich / tushum | **600ms**, `ease-out` kubik (`1-(1-p)³`) | ⛔ **Ha** — oxirida `scale(1.03)`, 150ms |
| Bandlik %, qarzdorlik | **600ms** | ⛔ **Yo'q** |
| Real-vaqt yangilanish | **400ms** [L-6] | ⛔ Yo'q — o'rniga «nafas» (§10.6) |

⛔ **Count-up SONNI O'ZGARTIRMAYDI:** oxirgi kadr — ⛔ **aynan** `format.number(value)` natijasi. Oraliq kadrlar `Math.round()` bilan chiziladi va ⛔ **hech qachon** `toFixed`/`parseFloat` ishlatmaydi [MEROS: 08 D-03]. ⛔ `value === null` bo'lsa count-up **umuman boshlanmaydi** — nol sanalmaydi [MEROS: T-05-04].

⛔ **A11y:** sanayotgan raqam `aria-live` ga ⛔ **qo'yilmaydi** (skrinrider 600ms davomida 20 marta gapirardi). Yakuniy qiymat `aria-label` da **darhol** to'liq turadi (§15).

### 10.4 Sparkline va donut — sof SVG

| Element | Texnika | Davomiylik |
|---------|---------|-----------|
| Sparkline | `<path>` + `stroke-dasharray:220; stroke-dashoffset:220→0`; ostida `accent/0.08` maydon | **600ms**, **250ms** kechikish |
| Donut | `<circle>` + `stroke-dashoffset: 226 → hisoblangan`; `rotate(-90deg)` | **600ms** |

⛔ **Ikkalasi ham `<title>` va matnli yig'indiga EGA** — rang/shakl **yolg'iz signal emas** (§15). ⛔ Ma'lumot yetarli bo'lmasa (7 kundan kam nuqta) — chiziq **chizilmaydi**, `EmptyState` chiqadi [MEROS: 08 D-10 «o'lchanmagan son chizilmaydi»].

### 10.5 Nomuvofiqlik case'i [L-5]

Yangi amber case **chetdan sirg'alib kiradi** (`translateX`, **400ms**) + ⛔ **BIR marta** diqqat-halqa (`box-shadow 0 → 10px transparent`). ⛔ **Qayta pulsatsiya YO'Q** — ogohlantirish charchatmasin.

### 10.6 Real-vaqt yangilanish [L-6]

Yangi to'lov kelganda: raqam **400ms** yumshoq o'sadi + karta ⛔ **bir marta** «yashil nafas» (`box-shadow` `success/0.25` → `--shadow-card`, **800ms**).

⛔ **Avtomatik poll QO'SHILMAYDI** — yangilanish mavjud `react-query` invalidatsiyasidan keladi. [MEROS: `billing-pending-queries.ts` §9.5 — *«avtomatik taymer rad etiladi… «men boshqa raqam ko'rgandim» nizosining manbai jimgina o'zgaradigan raqam edi»*.]

---

## 11. Y-3 — Tema qatlami [L-1]

### 11.1 Uchta tema — YOPIQ reyestr

| `data-theme` | Nomi (uz-Latn) | Kim uchun |
|--------------|----------------|-----------|
| `light` | Yorug' | Standart (iliq baza, §5.2) |
| `dark` | Tungi | 06:00 smenalar, kechki hisobot (§5.3) |
| `sun` | Quyosh ostida | ⛔ Kassir — ochiq havoda telefon (§11.4) |

⛔ **To'rtinchi tema yo'q.** ⛔ «Tizim bo'yicha» (`auto`) ⛔ **YO'Q** — sabab §11.2.

### 11.2 Tanlash va saqlash mexanikasi

| Savol | Qaror |
|-------|-------|
| Qayerda saqlanadi | ⛔ **`localStorage`** (kalit: `sbozor-theme`) — server profilida **emas** |
| Nega serverda emas | Tema — **qurilma** xossasi, foydalanuvchiniki emas: bitta kassir kunduzi telefonda, kechqurun ofis kompyuterida ishlaydi. Server profilida saqlash ⛔ ikkalasini **bir-biriga majburlardi**. ⚠ Til esa **teskari** — u profilda (D-15) va bu ziddiyat emas: til **odamning** xossasi |
| Standart qiymat | ⛔ **`light`** — ⛔ `prefers-color-scheme` **so'ralmaydi** |
| Nega `auto` yo'q | (a) Uchta tema + `auto` = **to'rt holat**, tugma esa **bir bosishli** bo'lishi kerak; (b) `sun` rejimi **hech qanday** tizim signaliga bog'lanmaydi; (c) ⛔ **eng muhimi** — [MEROS: D-15] loyihada **brauzer tili hech qachon so'ralmaydi** degan qaror bor va u aynan shu falsafadan: qurilma taxminlari **jimgina** noto'g'ri natija beradi |
| Qayerda turadi | `shell/app-shell.tsx:480` — ⛔ `LocaleSwitcher` **yonida** |
| Shakli | ⛔ 3 tugmali `role="group"` — `LocaleSwitcher` ning **aynan naqshi** (yangi ixtiro yo'q) |

⛔⛔ **FOUC va gidratatsiya — ikkalasi ham MAJBURIY hal qilinadi:**

| Muammo | Yechim |
|--------|--------|
| Birinchi bo'yashda oq miltillash | ⛔ `<head>` da **inline, bloklovchi** skript: `localStorage` dan o'qiydi va `document.documentElement.dataset.theme` ni **React'dan oldin** qo'yadi |
| React gidratatsiya nomuvofiqligi | ⛔ `<html>` ga **`suppressHydrationWarning`** [M-28 — bugun yo'q] |
| React holati atributdan ajralib ketishi | ⛔ Hook **DOM'dan o'qiydi** (`documentElement.dataset.theme`), o'z nusxasini **yaratmaydi** |
| SSG marshrutlar | Skript **statik** — locale'ga ham, sessiyaga ham bog'liq emas |

### 11.3 ⛔⛔ Token-scope — «komponent kodi o'zgarmaydi» ning MEXANIKASI

```css
[data-theme="dark"] { --color-bg: …; --color-surface: …; /* §5.3 to'liq ro'yxati */ }
[data-theme="sun"]  { --color-bg: …; --font-weight-normal: 500; /* §11.4 */ }
```

| Qoida | Sabab |
|-------|-------|
| ⛔ `dark:` Tailwind varianti — **0 marta** | [M-26] bugun 0; token-scope uni **keraksiz** qiladi (**G-motion-4(a)**) |
| ⛔ `@theme inline` — **TAQIQ** | ⛔ **Mexanik**: `inline` utilitani `var()` o'rniga **qiymatga** kompilyatsiya qiladi va scope override ⛔ **umuman ishlamaydi** [Tailwind hujjati: *«use the inline option to ensure utility classes resolve to the variable value rather than a reference»*]. Bu bitta so'z butun tema qatlamini **jimgina o'ldirardi** (**G-motion-4(b)**) |
| ⛔ Uchala temada token **TO'PLAMI TENG** | Bir temada yetishmagan token **standartga tushib**, jimgina noto'g'ri rang berardi (**G-motion-4(c)**) |
| ⛔ `@custom-variant dark` — **yozilmaydi** | U `dark:` variantini **qonuniylashtirardi**; bizda dark — **token**, variant emas |

### 11.4 Quyosh rejimi [MEROS: masterplan §1.4]

| Xossa | Qiymat | O'lchandi |
|-------|--------|-----------|
| `--color-bg` / `--color-surface` | `oklch(1 0 0)` (sof oq) | — |
| `--color-text` | `oklch(0 0 0)` (sof qora) | **21.00:1** |
| `--color-text-muted` | `oklch(0.35 0 0)` | **11.31:1** |
| `--color-border` | `oklch(0.62 0 0)` | **3.64:1** |
| `--color-border-ui` | `oklch(0.45 0 0)` | **7.44:1** |
| `--color-*-text` (4 ta) | `L ≈ 0.40–0.42` | **8.42–8.79:1** |
| ⛔ `--shadow-card` / `--shadow-raised` | ⛔ **`none`** | Quyoshda soya **shovqin** |
| ⛔ `--font-weight-normal` | ⛔ **500** (`--font-weight-semibold` → **700**) | Tailwind `--font-weight-*` namespace'i — ⛔ **komponent kodi o'zgarmaydi** |

⛔ **Iliq baza quyosh rejimida YO'Q** — iliqlik ko'z qulayligi uchun, quyosh rejimi esa **maksimal kontrast** uchun; ikkalasi qarama-qarshi maqsad.

---

## 12. Y-4 — Komponent jilosi

| # | Komponent | Bugun | ⛔ 9-fazada |
|---|-----------|-------|-------------|
| **12.1** | `ui/button.tsx` | `transition-colors duration-150` | `active:scale-[0.97] motion-reduce:scale-100` [M-8 naqshi] + `duration-(--motion-fast)`; ⛔ hover'da soya `--shadow-card` → `--shadow-raised` |
| **12.2** | Tugma ichidagi `Loader2` | 5 joy, **4 tasida** `motion-reduce` yo'q [M-7] | ⛔ **Beshalasiga** `motion-reduce:animate-none` qo'shiladi. ⛔ **Bu «spinner taqig'i» ga zid emas**: taqiq **kontent yuklanishiga** qo'llanadi (u yerda skeleton bor); tugma ichidagi ≤16px indikator — foydalanuvchi **o'zi bosgan** amalning javobi va uni skeleton **almashtira olmaydi** |
| **12.3** | `ui/card.tsx` | statik | ⛔ **Faqat** `@media (hover:hover)`: `translateY(-2px)` + soya chuqurlashishi, `--motion-base`. ⛔ Telefonda **umuman yo'q** (sticky-hover nuqsoni) |
| **12.4** | `ui/dialog.tsx` | shunchaki paydo | Radix `data-[state=open]` → `scale(0.96)→1` + fade, `--motion-base`; yopilish `--motion-fast`; fon **8%** + `blur(4px)` |
| **12.5** | `ui/skeleton.tsx` | `animate-pulse` | ⛔ **Shimmer 1.5s** + ⛔⛔ **GEOMETRIYA JUFTLIGI**: `pending-card.tsx:183` `h-9 w-40` → **`h-11`** (Display-XL ning 44px qutisi), `headline-card` `h-8` → **`h-11`** (faqat `soum` shoxida) [M-25] |
| **12.6** | `sonner` Toast | `top-center richColors` | ⛔ **Sozlamasi TEGILMAYDI.** ⛔ Masterplan §5 ning «muvaffaqiyat toastida mini check-draw» bandi ⛔ **RAD ETILADI**: 2-qadam tugmada **allaqachon** check chizadi va bir lahzada **ikki bir xil signal** ma'noni suyultirardi |
| **12.7** | Formalar | xato matni | Xato maydoni ⛔ **`translateX` shake** (2px, 200ms, `--ease-out`) + xabar `translateY` bilan; ⛔ reduced-motion'da **faqat matn**. ⛔ Login kartasi shake ⛔ **QILMAYDI** [MEROS: masterplan §6.1] |
| **12.8** | Jadval | statik | Qator hover fon; yangi qator kirish animatsiyasi (5-qadam naqshi). ⛔ Saralashda **qayta-tartib animatsiyasi YO'Q** — u FLIP'ni har qatorga qo'llardi va 1000 qatorli jadvalda **budjetni yeb qo'yardi** |
| **12.9** | `LocaleSwitcher` | `bg-accent` sakraydi | Faol indikator ⛔ **sirg'aladi**: `transform: translateX()` + kenglik `--w`, `--motion-base`. ⛔ `width`/`left` animatsiya **QILINMAYDI** |
| **12.10** | Bo'sh holatlar | matn (yaxshi) | ⛔ **TEGILMAYDI.** Masterplan §5 ning «12 ta SVG illustratsiya» bandi — §17.1 |

---

## 13. Mikro-UX §7 qoldiqlari — holat tekshiruvi

⛔ Topshiriq: *«masterplan §7 bandlaridan 8-fazada yopilmaganlari shu fazaga kiradi»*. O'lchov natijasi:

| # | Band | Holat | Dalil |
|---|------|-------|-------|
| **№1** | Sana formati — yagona util | ⛔ **YOPILGAN** | [KOD: `lib/format-day.ts` `formatBusinessDay()`, WR-07] — 11 faylda ishlatiladi. ⚠ **Ochiq quyruq:** `format.dateTime(` xom chaqiruvi **36 marta** — ular **lahza** (`timestamp`) formatlari, kalendar kuni emas; ⛔ 9-faza ularga **tegmaydi** |
| **№3** | Pul formati — yagona util | ⛔ **YOPILGAN** (boshqa shaklda) | `useFormatter().number()` + `*.amountUnit` naqshi — 18 faylda. ⛔ `formatMoney()` **yozilmaydi**: u `next-intl` ning locale kontekstini **ikkinchi marta** o'rardi |
| **№5** | Nisbiy vaqt | ⚠ **QISMAN** | `format.relativeTime()` **2 joyda** (`camera-row.tsx:113`, `alert-row.tsx:328`). ⛔ **9-faza uni KENGAYTIRMAYDI**: nisbiy vaqtning o'z yuzasi bor (kameralar, alertlar) va uni **to'lov/hisobot** yuzalariga yoyish ⛔ **aniq vaqtni yashirardi** — nizo hujjatida «3 soat oldin» **yaroqsiz** |
| **№4** | Terse validatsiyalar to'liq gapga | ⛔ **QAMROVDAN TASHQARIDA** | Bu **copy** ishi, motion emas; 1362 kalitni qayta o'qish — alohida topshiriq (§17.1) |
| **№5b** | Desktop max-width + direktor 2 ustun | ⚠ **QISMAN** — §10.1 ikki karta qo'shadi | To'liq 2-ustunli grid — §17.1 |
| **№6** | Breadcrumb emas, bozor konteksti | ⛔ **YOPILGAN** | [KOD: `app-shell.tsx` `shell.marketLabel`] |

⛔ **Xulosa: §7 dan 9-fazaga TUSHADIGAN yangi band YO'Q.** Uchtasi yopilgan, ikkitasi ataylab kengaytirilmaydi, bittasi qamrovdan tashqarida. ⛔ Bu **topilma** va u shu yerda yozilgani muhim — aks holda reja «6 ta mikro-UX tuzatish» degan **bo'sh to'lqin** ochardi.

---

## 14. Copy kontrakti

### 14.1 Yangi kalitlar — YOPIQ reyestr (yangi `theme` fazoviy nomi)

| Kalit | uz-Latn | ru |
|-------|---------|-----|
| `theme.label` | Ko'rinish | Оформление |
| `theme.light` | Yorug' | Светлое |
| `theme.dark` | Tungi | Тёмное |
| `theme.sun` | Quyosh ostida | На солнце |

`dashboard` fazoviy nomiga:

| Kalit | uz-Latn | ru |
|-------|---------|-----|
| `dashboard.revenueTrendTitle` | Tushum trendi | Динамика выручки |
| `dashboard.revenueTrendPeriod` | So'nggi 7 kun | Последние 7 дней |
| `dashboard.revenueTrendEmpty` | Trend uchun ma'lumot yetarli emas | Недостаточно данных для графика |
| `dashboard.revenueTrendEmptyHint` | Kamida 7 yopilgan kun kerak — hisobotlar bo'limida to'liq davrni ko'rish mumkin. | Нужно минимум 7 закрытых дней — полный период доступен в отчётах. |
| `dashboard.occupancyTitle` | Bandlik | Занятость |
| `dashboard.occupancySummary` | {occupied} band · {empty} bo'sh | {occupied} занято · {empty} свободно |
| `dashboard.occupancyEmpty` | Bandlik hali o'lchanmagan | Занятость ещё не измерена |

⛔ **Boshqa yangi kalit YO'Q.** ⛔ Xoreografiya, konfetti, tema animatsiyasi va count-up ⛔ **birorta yangi matn chiqarmaydi** — ular **mavjud** matnni harakat bilan yetkazadi. ⛔ «Muvaffaqiyat!», «Ajoyib!», «Zo'r ish!» kabi bayram matnlari ⛔ **YOZILMAYDI**: mavjud `collect.written` toasti **faktni** aytadi va u yetarli (**G-motion-6(d)**).

### 14.2 Transliteratsiya [M-31]

⛔ 17 nomzod satrdan **0 defekt**. `uz-Cyrl.json` ⛔ **`npm --prefix frontend run i18n:gen`** bilan quriladi, qo'lda tahrirlanmaydi; `uz-Cyrl.overrides.json` ⛔ **tegilmaydi**.

### 14.3 Glossariy va xato kontrakti

⛔ `ops/i18n/glossary.json` ⛔ **kengaytirilmaydi** — 9-faza domen atamasi kiritmaydi. ⛔ **Yangi xato kodi YO'Q**: bu fazada serverga yangi so'rov qo'shilmaydi (§10.1 dagi ikki karta **mavjud** endpointlarni ishlatadi va ularning xato kontrakti 08/05-fazalarda yopilgan).

---

## 15. Qulaylik (a11y)

| Talab | Shakl |
|-------|-------|
| ⛔ `prefers-reduced-motion` | ⛔ **GLOBAL** `@media` bloki `globals.css` da — barcha `animation-duration` va `transition-duration` **0.01ms** (**G-motion-1**) |
| ⛔ Sanayotgan raqam | ⛔ `aria-live` ga **QO'YILMAYDI**; `aria-label` da **yakuniy** qiymat darhol to'liq (§10.3) |
| Yuklanish holati | Skeleton konteynerida `aria-busy="true"` + `role="status"` + `sr-only` matn — ⛔ **mavjud naqsh** [KOD: `headline-card.tsx`] |
| ⛔ Uchayotgan klon | ⛔ `aria-hidden="true"` **va** `pointer-events:none` — u **bezak**, ma'lumot emas |
| ⛔ Konfetti (kelgusida) | ⛔ `aria-hidden="true"`; skrinriderga **hech nima** e'lon qilinmaydi |
| Sparkline / donut | ⛔ `<title>` + `role="img"` + yonida **matnli** yig'indi — rang yolg'iz signal **emas** |
| Tema tugmasi | `role="group"` + `aria-label` + `aria-current="true"` — ⛔ `LocaleSwitcher` naqshi |
| ⛔ Tema o'zgarishi | ⛔ Toast **chiqmaydi** — natija **ekranning o'zida** ko'rinadi |
| Fokus halqasi | ⛔ **HAR temada** `:focus-visible` aksent outline — dark va sun'da **qayta o'lchanadi** (§5.3, §11.4) |
| Barmoq nishoni | ≥44px — tema tugmalari `min-h-11` |
| ⛔ Animatsiya fokusni o'g'irlamaydi | ⛔ Xoreografiya davomida `focus()` **faqat 6-qadamda** va u **birinchi** bajariladi (§8.3) |

---

## 16. Darvozalar

### 16.1 ⛔ Raqamlash — TO'RTINCHI ketma-ketlik ochiladi va sabab MEXANIK

| Ketma-ketlik | Diapazon | Uyi |
|--------------|----------|-----|
| Frontend darvozalari | `G-1`…**`G-43` band** [M-32] | `frontend/scripts/*.test.mjs`, `*.test.tsx` |
| Backend/faza darvozalari | `G-1`…`G-16` band | `tests/**` |
| 7-fazaning taqiq darvozalari | `G7-1`…`G7-9` band | 07-RESEARCH |
| ⛔ **Motion darvozalari** | ⛔ **`G-motion-1`…`G-motion-7`** | `frontend/scripts/*.test.mjs`, `*.test.tsx` |

⛔⛔ **Nega `G-44` emas:** ROADMAP Phase 9 SC#4 ikkita darvozani ⛔ **NOM BILAN** talab qiladi — *«(G-motion-1 darvozasi)… (G-motion-2 darvozasi)»*; masterplan §9 ham shunday. Ularni `G-44`/`G-45` deb qayta nomlash ⛔ **ROADMAP mezonini nomi bo'yicha o'lchab bo'lmas** qilardi. ⛔ Nom — **mezonning bir qismi**.

**Qoidalar:**

1. Yangi darvozalar ⛔ **`G-motion-1` dan `G-motion-7` gacha**; `G-44` ⛔ **band qilinmaydi** (keyingi faza uchun ochiq).
2. Kod izohlarida ID **manba bilan**: `G-motion-3 (09-UI-SPEC)`.
3. ⛔⛔ **Bu hujjat `| **G-18** |` bilan boshlanadigan jadval qatori YOZMAYDI** [M-33] — `bulk-action-surface.test.mjs` UI-SPEC sonini **aynan 1** talab qiladi. `G-motion-*` nomlari uning regeksiga **tushmaydi**.

### 16.2 Har darvozaning ikki muzokarasiz xossasi [MEROS: 06/07/08-UI-SPEC]

| Xossa | Ma'nosi |
|-------|---------|
| ⛔ **HOSILA qamrov** | Darvoza katalogni **o'qiydi**, reyestrdan **iteratsiya qiladi**. Qo'lda yozilgan ro'yxat **yo'q** |
| ⛔ **TO'PLAM TENGLIGI** | `deepEqual`/`Set`. ⛔ `not.toContain(...)` **ishlatilmaydi** |

Har darvozada **quyi chegara** (`MIN_*`): skanerlanadigan fayl/token soni kamaysa darvoza **qizaradi**.

### 16.3 ⛔ Sabotaj majburiyati [MEROS: 05-15 va 08-20 darslari]

Har darvoza uchun reja **sabotaj o'lchovini** yozadi. ⛔ **Sabotaj modulni IMPORT QILINADIGAN holda qoldirishi SHART** [MEROS: 08-20 S-5 darsi] — aks holda u mezonni emas, **yig'ilishni** o'lchaydi. ⛔ Sabotaj sistemaga yetib borib ham hech nima qizarmasa, tuzatish **testda emas — HOLATDA**.

### 16.4 Yangi darvozalar

| # | Darvoza | Fayl | Mexanik ravishda NIMANI o'qiydi | Nima uchun mavjud |
|---|---------|------|----------------------------------|-------------------|
| **G-motion-1** | ⛔⛔ **`prefers-reduced-motion` HURMATI** (ROADMAP SC#4) | `scripts/motion-tokens.test.mjs` + `collect/success-choreography.test.tsx` | **(a)** `globals.css` da `@media (prefers-reduced-motion: reduce)` bloki **bor** va u `animation-duration` **va** `transition-duration` ni `!important` bilan **≤0.01ms** ga tushiradi (parse, `grep` emas). **(b)** ⛔ `animate-` bilan boshlanadigan **har** utilita yonida `motion-reduce:` juftligi **bor** — qamrov `components/**` dan **hosila**; ⛔ quyi chegara **≥5 uchrash** [M-7]. **(c)** `matchMedia("(prefers-reduced-motion: reduce)")` **true** mock'ida: xoreografiya ⛔ **klon YARATMAYDI** (`document.body` bolalar soni **o'zgarmaydi**), halqa elementi **yo'q**, ⛔ **LEKIN** to'lov qatori DOM'da **bor** va fokus inputda. **(d)** ⛔ Konfetti moduli **umuman yo'q** (§9) — `confetti`/`konfetti`/`burst` ta'rifi `components/**` da **0**. ⛔ **SABOTAJ:** `@media` blokidan `transition-duration` qatori olib tashlanadi — **(a) qizarishi SHART**; `matchMedia` shoxidagi `if` teskari qilinadi — **(c) qizarishi SHART** | ⛔ **ROADMAP SC#4 ning birinchi yarmi.** [M-6] bugun global blok **yo'q** va `motion-reduce:` **3 joyda** — ya'ni bu qatlam **noldan** quriladi. Vestibulyar buzilishi bo'lgan foydalanuvchi uchun 700ms uchuvchi element — **jismoniy noqulaylik**, did emas |
| **G-motion-2** | ⛔⛔ **KASSIR INTERAKTIV ≤150ms VA BAYRAM BLOKLAMAYDI** (ROADMAP SC#4) | `collect/collect-session.test.tsx` + `collect/success-choreography.test.tsx` | **(a)** ⛔ **O'LCHOV, da'vo emas:** `POST` javobidan **keyin** soxta taymer bilan **150ms** o'tkaziladi → input `document.activeElement` **va** `value === ""` **va** `disabled === false` **va** `readOnly === false`. **(b)** ⛔ 150ms nuqtasida yozilgan belgi (`userEvent.type`) input qiymatida **to'liq** turadi — ⛔ **bu «bloklamaydi» ning yagona halol o'lchovi**. **(c)** ⛔ Uchayotgan klonning `pointer-events` **`none`** va `aria-hidden` **`true`**. **(d)** ⛔ `setTimeout` chaqiruvlari **faqat** DOM tozalash uchun: `success-choreography.tsx` manbasida `setTimeout` ichida `setState`/`set[A-Z]` **0 marta** (AST, `grep` emas). **(e)** ⛔ Xoreografiya **tashlansa ham** (istisno otilsa) to'lov qatori va fokus **joyida** — `try/catch` bilan o'ralgani **o'lchanadi**. ⛔ **SABOTAJ:** 4-qadam `await` bilan kutiladigan qilinadi — **(a)/(b) qizarishi SHART**; `pointer-events:none` olib tashlanadi — **(c) qizarishi SHART** | ⛔ **§1.2 — bu fazaning eng qimmat nuqsoni.** Kunlik 400 to'lovda har biriga +2s **13 daqiqa** va «tizim sekin» xulosasi. (b) eng nozigi: fokus **qaytgan** bo'lishi mumkin, lekin klon ustida turib bosishni **yutayotgan** bo'ladi — birinchi shakl buni **o'tkazib yuborardi** |
| **G-motion-3** | ⛔⛔ **FAQAT GPU XOSSALARI · TOKEN REYESTRI YOPIQ · YANGI PAKET 0** (ROADMAP SC#5) | `scripts/motion-tokens.test.mjs` | **(a)** ⛔ `globals.css` ning **har** `@keyframes` bloki parse qilinadi: ruxsat etilgan xossalar ⛔ **to'plam tengligi** bilan `{transform, opacity, background, background-color, background-position, box-shadow, stroke-dashoffset, stroke-dasharray}`; ⛔ `width`, `height`, `top`, `left`, `right`, `bottom`, `margin*`, `padding*` — **har biri 0**; quyi chegara **≥6 `@keyframes`**. **(b)** ⛔ `components/**` da `duration-` + **raqam** — **0 marta** [M-4 ko'chiriladi]; `transition-\[` va `animation:` inline uslubda — **0**. **(c)** ⛔ `@keyframes` **nomlari** reyestrdan hosila va ular **faqat** `globals.css` da ta'riflanadi — komponent faylida `@keyframes` **0**. **(d)** ⛔⛔ `package.json` `dependencies` ⛔ **to'plam tengligi** bilan bugungi **20 paket** ro'yxatiga TENG — ⛔ `motion`, `framer-motion`, `recharts`, `gsap`, `lottie-*`, `canvas-confetti`, `react-spring` **nomma-nom** yo'q. ⛔ **SABOTAJ:** bitta `@keyframes` ga `height: 0 → 100%` qo'shiladi — **(a) qizarishi SHART**; `package.json` ga `canvas-confetti` qo'shiladi — **(d) qizarishi SHART** | ⛔ **ROADMAP SC#5 + L-8.** (a) arzon Androidda `height` animatsiyasi har kadrda **layout** hisobini qo'zg'aydi — 60fps **imkonsiz** bo'ladi. (d) ⛔ **to'plam tengligi** ataylab: «taqiqlangan nom yo'q» tekshiruvi **yangi** og'ir paketni o'tkazib yuborardi, byudjet esa **umumiy** |
| **G-motion-4** | ⛔⛔ **TEMA — TOKEN-SCOPE, KOMPONENT KODI O'ZGARMAYDI** (ROADMAP SC#3) | `scripts/theme-tokens.test.mjs` | **(a)** ⛔ `components/**` va `app/**` da `className` **satrlari ichida** `dark:` — **0 marta**; ⛔ **yolg'on-ijobiy manbai NOMMA-NOM yozilgan**: `snapshots` javobidagi `dark` **maydoni** (6 uchrash, [M-26]) — skan `className=`/`cn(` argumentlari bilan **chegaralangan**. **(b)** ⛔ `globals.css` da `@theme inline` — **0 marta** (§11.3). **(c)** ⛔⛔ **TO'PLAM TENGLIGI:** `[data-theme="dark"]` va `[data-theme="sun"]` bloklaridagi o'zgaruvchi nomlari `@theme` dagi `--color-*` to'plamining **QISM to'plami**, va ⛔ **`--color-*-text` oilasining HAMMASI ikkala scope'da HAM bor** (M-18 darsining mexanik shakli). **(d)** `data-theme` qiymatlari reyestri ⛔ **aynan 3 a'zo** (`light`,`dark`,`sun`) va `theme.*` kalitlari ⛔ **uchala locale'da** — to'plam tengligi. **(e)** ⛔ `<html>` da `suppressHydrationWarning` **bor** va inline tema skripti `<head>` da **bor**. ⛔ **SABOTAJ:** dark scope'dan `--color-danger-text` olib tashlanadi — **(c) qizarishi SHART**; `@theme` → `@theme inline` — **(b) qizarishi SHART** | ⛔ **SC#3 + §11.3.** (b) eng nozigi: `inline` bitta so'z va u tema qatlamini ⛔ **jimgina** o'ldiradi — sahifa yuklanadi, tugma bosiladi, **hech nima o'zgarmaydi**. (c) [M-18] ning darsi: sketch tokenlari **beshta AA buzilishini** olib kelgan edi va uni **faqat** to'plam tengligi ushlaydi |
| **G-motion-5** | ⛔⛔ **KONTRAST — DA'VO EMAS, O'LCHOV** | `scripts/contrast.test.mjs` | **(a)** ⛔ `globals.css` dan `oklch(...)` qiymatlari **parse qilinadi** (qo'lda ko'chirilmaydi) va WCAG 2.x nisbati **hisoblanadi**. **(b)** ⛔ **E'LON QILINGAN JUFTLIKLAR REYESTRI** (matn/fon) uchala temada: `text`/`bg`, `text`/`surface`, `text-muted`/`surface-muted`, `accent-fg`/`accent`, `danger-fg`/`danger`, ⛔ `success-fg`/`success` (M-20), `*-text`/tint — ⛔ har biri **≥4.5:1**; `border-ui`/`surface`, `border-ui`/`bg`, `border-ui`/`surface-muted` — **≥3:1**; quyi chegara **≥12 juftlik × 3 tema**. **(c)** ⛔⛔ **IZOHLAR MASHINA O'QIYDIGAN DA'VO:** `globals.css` izohlaridagi `N.NN:1` shaklidagi **har** son topiladi va hisoblangan qiymat bilan ⛔ **±0.01 aniqlikda** solishtiriladi; quyi chegara **≥4 da'vo** [M-16]. **(d)** ⛔ `bg-accent` bilan bir `className` da `text-accent-text` — **0 marta** (M-19 ning regressiya qulfi). ⛔ **SABOTAJ:** `--color-text-muted` ni `oklch(0.62 0 0)` ga o'zgartirish — **(b) qizarishi SHART**; izohdagi `4.81` ni `5.20` ga o'zgartirish — **(c) qizarishi SHART** | ⛔ **[M-15] Bugun oltita nisbat izohda yozilgan va ularni HECH NIMA tekshirmaydi.** Bu faza fonni **va** ikkita yangi temani qo'shadi — ya'ni qo'lda tekshirish yuzasi **uch baravar** oshadi. (c) eng qimmati: izoh **eskiradi** va eskirgan izoh keyingi ijrochiga **yolg'on gapiradi** — 08-fazaning butun madaniyati shunga qarshi |
| **G-motion-6** | ⛔⛔ **KO'R DEKLARATSIYA — MOTION QATLAMIDA HAM** | `scripts/collect-surface.test.mjs` (kengaytiriladi) + `dashboard/page.test.tsx` | **(a)** ⛔ Mavjud `BLIND_DECLARATION_TOKENS` va `MIN_BLIND_DECLARATION_TOKENS = 7` ⛔ **O'ZGARMAYDI**; qamrovga `components/dashboard/**` ⛔ **QO'SHILMAYDI** (u boshqa yuza), o'rniga **(b)**. **(b)** ⛔⛔ `dashboard/page.tsx` testi: `cashier` rolli sessiya mock'ida ⛔ **tushum kartasi DOM'da YO'Q** **va** ⛔ so'rov **yuborilmagan** (query mock chaqiruvlar soni **0**); `director` sessiyasida ⛔ **bor**. **(c)** ⛔ `components/dashboard/**` da `report_view` **darvozasi komponentdan TASHQARIDA** — komponent manbasida `hasPermission(` **0 marta** (shart sahifada). **(d)** ⛔ Bayram copy'si: `collect.*` qiymatlarida «Ajoyib», «Zo'r», «Tabrik», «Отлично», «Поздравля» — **0 marta**, uchala locale'da; quyi chegara **≥5 token**. **(e)** ⛔ `components/collect/**` da `confetti`/`burst`/`particle` — **0 marta** (§9 ning ijro yo'qligi **o'lchanadi**). ⛔ **SABOTAJ:** dashboard testidagi rol `cashier` → `director` qilinadi, karta esa darvozasiz qoldiriladi — **(b) qizarishi SHART** | ⛔ **§0.2 — bu fazaning eng qimmat TUZOG'I.** «Direktor paneliga tushum kartasi qo'shildi» degan bezarar jumla, `/dashboard` **hamma rol** kiradigan sahifa bo'lgani uchun, ⛔ **6-fazaning butun ko'rlik mexanikasini** bir commitda buzardi. (b) ⛔ **ikki qatlam** (DOM **va** so'rov) ataylab: `hidden` bilan yashirilgan karta so'rovni **baribir** yuborardi va tarmoq panelida summa **ko'rinardi** |
| **G-motion-7** | ⛔ **SKELETON GEOMETRIYASI (CLS) VA DISPLAY-XL YOPIQ QAMROVI** | `scripts/typography.test.mjs` + `headline/headline-card.test.tsx` | **(a)** ⛔ `text-display` ⛔ **≤2 mahsulot faylida** va ular reyestrga **teng**: `collect/pending-card.tsx`, `headline/headline-card.tsx` (§7.1). **(b)** ⛔ `headline-card` da `text-display` ⛔ **shartli**: `unit === "soum"` mock'ida **bor**, `unit === "count"` mock'ida ⛔ **YO'Q** — ikkalasi **bitta testda**. **(c)** ⛔⛔ **GEOMETRIYA JUFTLIGI:** `isPending` shoxidagi `Skeleton` ning balandlik sinfi (`h-N`) kontent shoxining qator qutisi bilan ⛔ **teng**: `text-display` → `h-11`, `text-2xl` → `h-8`; ⛔ reyestr **jadvaldan** o'qiladi, testda qayta yozilmaydi. **(d)** ⛔ `text-base`, `text-xl`, `text-3xl`, `text-[` — ⛔ **sanoq O'SMAYDI**: `text-base` **≤7**, `text-xl` **≤4**, `text-3xl` **0**, `text-[` **0** [M-21]. **(e)** ⛔ `font-medium` **≤21** [M-22]. ⛔ **SABOTAJ:** `pending-card` skeletonini `h-9` da qoldirish — **(c) qizarishi SHART**; `text-display` ni uchinchi faylga qo'shish — **(a) qizarishi SHART** | ⛔ **§1.2 qoida 5 + L-9.** (c) ⛔ **CLS ning yagona mexanik o'lchovi** bu repozitoriyada: Lighthouse CI'da yo'q (§16.6), skeleton↔kontent farqi esa **CLS ning aynan sababi** [M-25: bugun 8–12px farq]. (d) 4 rolli e'lonning **quyi chegarasi** — deviatsiyalar **tuzatilmaydi**, lekin ⛔ **o'smaydi** |

### 16.5 ⛔ Mavjud darvozalarga TEGILMAYDI

| Darvoza | 9-fazada |
|---------|----------|
| `collect-surface.test.mjs` `MIN_FORBIDDEN_NAMES = 14` / `MIN_BLIND_DECLARATION_TOKENS = 7` | ⛔ **O'zgarmaydi** — kamaytirish **taqiq** |
| `submit-gate.test.mjs`, `role-gate.test.mjs`, `forbidden-notice.test.mjs` | ⛔ **Tegilmaydi** |
| `bulk-action-surface.test.mjs` (G-18 e'loni) | ⛔ **Tegilmaydi** — §16.1 qoida 3 |
| `report-copy.test.mjs` (G-38…G-43) | ⛔ **Tegilmaydi**; ⛔ sparkline `/reports` ga **qo'yilmagani** uchun G-42 ham tinch (§10.1) |
| `i18n:check` (parity + generatsiya) | ⛔ Yangi kalitlar **shundan o'tadi** |

### 16.6 ⛔ Lighthouse va CLS — HALOL joylashtirish

⛔ **Lighthouse CI'da YO'Q va bu fazada QO'SHILMAYDI**: u headless Chrome + yangi ishlab chiqish bog'liqligini talab qiladi va `gate` byudjetiga **daqiqalar** qo'shardi.

| Talab | Qayerda o'lchanadi |
|-------|--------------------|
| Performance **≥90** (arzon Android) | ⛔ **`09-HUMAN-UAT.md`** — egasi **ijrochi**, tetigi **faza darvozasi**; natija **son bilan** yoziladi |
| CLS **< 0.05** | ⛔ Mexanik **proksi**: **G-motion-7(c)** (skeleton geometriyasi) — CLS ning **aynan sababi**; to'liq o'lchov HUMAN-UAT'da |
| Bundle byudjeti | ⛔ **G-motion-3(d)** — `dependencies` to'plam tengligi (**0 KB o'sish**) |
| 60fps | ⛔ **G-motion-3(a)** — GPU xossalari; qurilmadagi o'lchov HUMAN-UAT'da |

⛔ **Mexanika qatlamining yashilligi bilan o'lchov qatlamining yo'qligini yopish TAQIQLANADI** [MEROS: D-01, FOUND-07 va AI-02 darsi]. HUMAN-UAT bandi **son bilan** yopiladi, «ko'rinishi yaxshi» bilan emas.

### 16.7 Sampling — mavjud byudjetlar

| Daraja | Buyruq | Byudjet |
|--------|--------|---------|
| Task commit | `npm run gate:fast` | **200 s** |
| Wave merge | `npm run test` + `npm run test:tenancy` | — |
| Faza darvozasi | `npm run gate` | **2300 s** [MEROS: 08 D-26] |

⚠ Baholangan qo'shimcha: vitest **+~55 test**, 4 ta yangi `scripts/*.test.mjs` (sof matn/CSS parse, **tez**) → **~40–60 s**. ⛔ Oshsa — 05-15 W0-13 protokoli: **tinch xost**, **uch o'lchov**, **eng yomon × 1,20**, sabab **yozilgan**. ⚠ [MEROS: STATE.md] `frontend/node_modules` bo'shligi 8-fazada **29-daqiqada** ko'ringan edi — zanjir boshida `npm ci` **tekshiriladi**.

---

## 17. Bu fazada BO'LMAYDIGAN UI

### 17.1 Keyingi fazaga / v2 ga qoldiriladigan

| Imkoniyat | 9-fazada aynan nima qilinadi | Nima QILINMAYDI |
|-----------|-------------------------------|------------------|
| **Landing (`sbozor.uz`)** | ⛔ **Hech narsa** [L-10] | Hero sikli, 3-qadam chizig'i — **Phase 10** |
| **Konfetti ijrosi** | ⛔ Shartnoma **to'liq yoziladi** (§9) | Kod, paket, soxta tetik |
| **«Bugun yig'ildi» hisoblagichi** | ⛔ **Hech narsa** (§9.4) | Kassir yuzasida yig'indi |
| **Masterplan §6.3 to'liq 2-ustunli grid** | ⛔ **Ikki karta** (§10.1) | Qarzdorlik kartasi, nomuvofiqlik lentasi, shared-element o'tish |
| **View Transitions API** | ⛔ **Hech narsa** | Sahifalararo o'tish — u `proxy.ts`/marshrut qatlamiga tegadi |
| **12 ta bo'sh-holat illustratsiyasi** | ⛔ **Hech narsa** | SVG to'plami — **copy va rasm** ishi, motion emas |
| **Plan-xarita zoom inersiyasi / rasta glow** | ⛔ **Hech narsa** | `react-konva` yuzasi — 5-faza mexanikasi |
| **Kamera thumbnail'lari (§6.5)** | ⛔ **Hech narsa** | Yangi rasm yuzasi + huquq savoli |
| **Smena «muhri» (§4.2)** | ⛔ **Hech narsa** | Alohida xoreografiya, alohida o'lchov |
| **Usta yakuni / NVR radar animatsiyasi (§4.4, §4.5)** | ⛔ **Hech narsa** | Ular **kunlik oqim emas** — ROI past |
| **Terse validatsiyalarni to'liq gapga (§7 №4)** | ⛔ **Hech narsa** | 1362 kalitli copy auditi — alohida topshiriq |
| **Storybook / skrinshot-solishtiruv** | ⛔ **Hech narsa** | Yangi asboblar zanjiri |

### 17.2 Ataylab qurilMAYDIGAN — sabab bilan

| Nima | Nima uchun |
|------|-------------|
| ⛔ **`motion` / `framer-motion`** | §3.2 — **0 ta noyob imkoniyat**, Lighthouse byudjetiga **o'lchanadigan** zarar |
| ⛔ **`canvas-confetti`** | Konfetti **qurilmaydi** (§9); qurilganda ham **12 ta `<span>`** paket talab qilmaydi |
| ⛔ **`recharts` yoki boshqa diagramma paketi** | Sparkline/donut — ⛔ **sof SVG**; 08 §17.2 ning ruhi saqlanadi |
| ⛔ **`next-themes`** | Uchta tema + `sun` rejimi uning ikki holatli modeliga **sig'maydi**; ⛔ 20 qatorlik hook + inline skript **kamroq** yuza |
| ⛔ **Sparkline `/reports` sahifasida** | §10.1 — ⛔ **hujjat yuzasi**; ekran bilan `.xlsx` ajralardi |
| ⛔ **Sahifa yuklanishida aylanuvchi spinner** | Skeleton bor (54 fayl, M-24); ⛔ spinner **kontent shaklini** aytmaydi va CLS ni **oshiradi** |
| ⛔ **Jadval saralashda qayta-tartib animatsiyasi** | 1000 qatorda FLIP **budjetni yeydi**; foyda — nol |
| ⛔ **`prefers-color-scheme` avtomatik ergashish** | §11.2 — qurilma taxminlari **jimgina** noto'g'ri natija beradi (D-15 falsafasi) |
| ⛔ **Tema o'zgarishida toast** | §15 — natija **ekranning o'zida** ko'rinadi |
| ⛔ **Login kartasining shake animatsiyasi** | [MEROS: masterplan §6.1] — xato matni **allaqachon yaxshi**; shake **ayblov** hissini beradi |
| ⛔ **Xoreografiyaning `await` qilinishi** | §8.2 — bu fazaning **eng qimmat nuqsoni** |

### 17.3 Erta optimizatsiya deb baholangan «ilgaklar»

Animatsiya tezligining foydalanuvchi sozlamasi (`prefers-reduced-motion` **yetarli**) · tema uchun server profili maydoni (§11.2) · `--motion-*` ga to'rtinchi qiymat (`instant`/`crawl` — uchtasi **butun ilovani** qopladi) · umumiy `<AnimatedList>` abstraktsiyasi (uch iste'molchi, uch xil kontrakt) · count-up uchun umumiy formatter registri · motion tokenlarining Storybook katalogi.

---

## 18. Ochiq qoldirilgan savollar — har biri uchun ishlaydigan standart bor

Bu subagent kontekstida foydalanuvchiga savol berish vositasi yo'q (avtonom rejim). Har biri uchun standart tanlangan; rejalashtirish javob kutib **to'xtamaydi**.

| # | Savol | Bilamiz | Noaniq | Tanlangan standart va TETIGI |
|---|-------|---------|--------|-------------------------------|
| **O-01** | ⛔⛔ Konfetti tetigi — `market_day_cleared` bayrog'i **shu fazada** qo'shilsinmi? | [M-10] hech qanday plan konsepsiyasi yo'q; [M-11] klientdagi hosila **taqiqlangan** | Karmanada «kunlik plan» **rasmiy** tushunchami yoki gapdagi iborami | ⛔ **QO'SHILMAYDI** (§9). Sabab **mexanik**: `paymentResponseSchema` — `z.strictObject`, ya'ni server yolg'iz maydon qo'sha olmaydi (klient **parse'da yiqiladi**); bu **kelishilgan, ikki tomonlama** o'zgarish va u **backend fazasining** ishi. ⛔ Shartnoma §9.1/§9.3 da **to'liq** turadi — yoqish **bir qator**. **Tetigi:** buyurtmachi «plan» ni **rasmiy ko'rsatkich** deb tasdiqlasa (kunlik summa maqsadi) — u holda to'g'ri yo'l bayroq **emas**, **direktor** yuzasidagi plan/fakt kartasi; kassirga plan ko'rsatish **boshqaruv qarori** |
| **O-02** | Standart tema — `light` mi yoki `prefers-color-scheme` mi? | [M-27] infratuzilma yo'q; 06:00 smenalar bor | Karmanada telefonlar **qaysi rejimda** turadi | ⛔ **`light`** (§11.2). Sabab: `sun` rejimi tizim signaliga bog'lanmaydi, ya'ni **baribir** qo'lda tanlanadi — avtomatika faqat **ikkitasini** qamrab, uchinchisini yolg'iz qoldirardi. **Tetigi:** dala UAT'da foydalanuvchilar **ko'pchiligi** birinchi kuni `dark` ni bosgani ko'rinsa — standartni `prefers-color-scheme` ga o'tkazish mumkin, LEKIN shunda §11.2 dagi «qurilma taxmini» qoidasi **ochiq** qayta ko'riladi |
| **O-03** | Dashboard'ga qo'shiladigan ikki karta **`report_view`** ostidami yoki yangi huquq kerakmi? | [MEROS: 08 M-6] `report_view` **aynan** `director` + `market_admin` da; kassirda **yo'q** | Direktor «bosh ekranda ko'rsam» deydimi yoki «hisobotda yetarli» deymi | ⛔ **`report_view`, yangi huquq YO'Q** (§10.1). Sabab: ikkala karta ham **hisobot ma'lumotining** qisqartmasi; ikkinchi huquq matritsani **ikki joyda** (`rbac.py`/`rbac.ts`) kengaytirardi va yangi kesim tug'dirardi. **Tetigi:** `platform_admin` ga ham kerak bo'lsa — ⛔ **ikkala matritsada bitta commitda**, marshrut qamrovi yangilangan holda |
| **O-04** | Sparkline **nechta kun** ko'rsatadi? | 08 `/reports/revenue?from&to` ixtiyoriy davr beradi | Direktor «hafta» bilan o'ylaydimi yoki «oy» bilanmi | ⛔ **`[ASSUMED]` 7 kun** (§10.4). Sabab: 7 nuqta **telefonda** o'qiladi va «shu hafta qanday ketyapti» — bosh ekranning savoli; oy esa **hisobot** savoli va u `/reports` da **allaqachon** bor. ⛔ 7 kundan kam ma'lumotda chiziq **chizilmaydi**. **Tetigi:** direktor doim `/reports` ga o'tayotgani ko'rinsa — davr **tanlanadigan** qilinmaydi (u bosh ekranni hisobotga aylantirardi), balki kartaga **havola** qo'yiladi |
| **O-05** | Xoreografiyaning 4-qadami (uchish) **desktopda** ham kerakmi? | Kassir **telefonda** ishlaydi; ro'yxat desktopda **yonda** turadi | Bozor adminlari to'lovni desktopda yozadimi | ⛔ **Ha, ikkalasida ham** (§8.1). Sabab: masofa `getBoundingClientRect()` dan **hosila**, ya'ni kod **bir xil**; `@media` bilan bo'lish ikkinchi shox va ikkinchi o'lchov yuzasini ochardi. **Tetigi:** desktopda uchish **uzoq** ko'rinsa (>800px) — davomiylik emas, **masofa** cheklanadi (klon ro'yxat **ko'rinadigan** qismiga uchadi) |
| **O-06** | `--color-success-fg` ni quyuq qilish (M-20) **bu fazadami**? | Juftlik kodda **ishlatilmaydi** (M-20) | Kelajakda yashil to'yingan tugma kerak bo'ladimi | ⛔ **Ha, shu fazada** (§5.6). Sabab: ⛔ **hech qanday piksel o'zgarmaydi** (juftlik render bo'lmaydi), lekin G-motion-5 ning e'lon qilingan juftliklar reyestri **to'liq** bo'ladi. Aks holda darvoza o'z ro'yxatidan bitta juftlikni **chiqarib tashlashga** majbur bo'lardi va bu **istisno** bo'lib qolardi. **Tetigi:** dizayn yashil **to'yingan** tugmani talab qilsa — u allaqachon AA bilan tayyor |
| **O-07** | Shimmer **1.5s** arzon Androidda qimmatmi? | [L-5] qulflangan qiymat; `background-position` — ⛔ **kompozit emas** | Contabo emas, **telefon** GPU'si | ⛔ **1.5s saqlanadi** (§10.2), LEKIN ⛔ **skeleton faqat ko'rinadigan hududda** chiziladi va ⛔ ekranda **bir vaqtda ≤8** skeleton bloki bo'ladi. **Tetigi:** HUMAN-UAT'da arzon qurilmada jank o'lchansa — to'g'ri tuzatish `opacity` pulsiga **qaytish** (mavjud `animate-pulse`), davomiylikni o'zgartirish **emas** |

---

## 19. Dizayn tizimi xulosasi (checker uchun jamlanma)

| Xossa | Qiymat |
|-------|--------|
| **Tool** | `none` (shadcn **ishlatilmaydi** — §3.1) |
| **Preset** | not applicable |
| **Component library** | Radix primitivlari + CVA, ⛔ **mahalliy `ui/` (10 primitiv, kengaymaydi)** |
| **Icon library** | `lucide-react@1.27.0` (ISC) — ⛔ **yangi ikonka kerak emas** |
| **Font** | `--font-sans` (system stack) + `--font-mono` |
| **Bo'shliq** | 4-panjara: **4 · 8 · 12 · 16 · 24 · 32 · 48** (§6). **Istisnolar:** 44px barmoq nishoni, 56px mobil panel, 20px karta ichki `x` — ⛔ **barchasi MEROS, yangi istisno YO'Q** |
| **Tipografiya** | ⛔ **4 matn roli** (24 / 18 / 14 / 12) + ⛔ **1 raqamli display roli** (**40px**, `text-display`, ⛔ **aynan 2 faylda**, G-motion-7(a)); ⛔ **2 og'irlik** (400, 600) |
| **Rang 60/30/10** | 60% `--color-bg` (⛔ **iliq** `oklch(0.985 0.001 106)`) · 30% `--color-surface` (+`-muted`) · 10% `--color-accent` |
| **Aksent faqat** | fokus halqasi · faol maydon chegarasi · joriy mobil nav elementi · `Badge tone="accent"` (tint) · ⛔ **to'yingan fon AYNAN 5 joyda** (§5.4) |
| **Destruktiv** | `--color-danger` — `variant="destructive"` **faqat** `ConfirmDialog` ichida [MEROS: 08 §14.8] |
| **Yangi token** | ⛔ **6 ta, YOPIQ REYESTR**: `--motion-fast/base/slow`, `--ease-out` (qayta ta'rif), `--ease-spring`, `--text-display` (§4.1) |
| **Yangi npm paketi** | ⛔⛔ **YO'Q** — jumladan `motion`, `recharts`, `canvas-confetti`, `next-themes` **ham** (§3.2, G-motion-3(d)) |
| **Temalar** | ⛔ **3 ta, YOPIQ**: `light` (iliq) · `dark` · `sun`; ⛔ **token-scope**, `dark:` varianti **0**, `@theme inline` **TAQIQ** |
| **Primary CTA** | ⛔ **Yangi CTA YO'Q** — mavjud «To'lovni tasdiqlash» (`collect.confirm`) 6-qadam xoreografiyasini **oladi** |
| **Bo'sh holatlar** | ⛔ **2 ta yangi**: `dashboard.revenueTrendEmpty`, `dashboard.occupancyEmpty` (§14.1) |
| **Xato holatlari** | ⛔ **Yangi xato kodi YO'Q** (§14.3) |
| **Destruktiv tasdiq** | ⛔ **Yangi destruktiv amal YO'Q** |
| **Yangi copy kalitlari** | ⛔ **11 ta**, uchala tilda; transliteratsiya **0 defekt** [M-31] |
| **Registry safety** | ⛔ **Qo'llanmaydi** — shadcn ishlatilmaydi, uchinchi tomon registry **yo'q**, vendored blok **yo'q** |
| **Yangi darvozalar** | **G-motion-1 … G-motion-7**, har biri **sabotaj** bilan (§16.4) |

---

## Checker Sign-Off

- [ ] Dimension 1 Copywriting: PASS
- [ ] Dimension 2 Visuals: PASS
- [ ] Dimension 3 Color: PASS
- [ ] Dimension 4 Typography: PASS
- [ ] Dimension 5 Spacing: PASS
- [ ] Dimension 6 Registry Safety: PASS

**Approval:** pending

---

*Phase: 09-ui-polish-motion-qatlami*
*UI-SPEC yakunlandi: 2026-08-17 — `gsd-ui-researcher`*
*Upstream: `sketch-findings-bozor` skill (001-B, 002-B — foydalanuvchi tasdiqlagan 2026-08-16), UI-UX-MASTERPLAN.md (§1–§9), ROADMAP Phase 9 (SC#1–SC#5 + Chegaralar), 08-UI-SPEC.md (dizayn tizimi, darvoza mexanikasi, §3.5/§16.2/§17.2), 06-UI-SPEC.md (ko'r deklaratsiya, G-7/G-22), 05-UI-SPEC.md (o'lchanmagan son chizilmaydi), STATE.md (gate byudjeti, sabotaj darslari), CLAUDE.md (Tailwind 4 CSS-first, tailwind.config TAQIQ)*
