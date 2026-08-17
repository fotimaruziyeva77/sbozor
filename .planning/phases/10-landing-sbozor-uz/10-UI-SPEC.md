---
phase: 10-landing-sbozor-uz
status: approved
reviewed_at: 2026-08-17
shadcn_initialized: false
preset: none
design_system: shadcn-pattern (manual, CVA + Radix — 1/2-faza tokenlari, 9-faza motion/tema qatlami)
response_language: uz-Latn
inherits: .planning/phases/09-ui-polish-motion-qatlami/09-UI-SPEC.md
created: 2026-08-17
---

# Phase 10 — Landing (`sbozor.uz`): UI dizayn kontrakti

> Bitta va'daning vizual kontrakti: **mahsulotning o'zi gapiradi.**
> Raqobatchi (`raqamli-bozor.uz`) statik skrinshot ko'rsatadi va «samaradorlikni oshiradi» deydi. Biz **voqeani sodir bo'layotganini** ko'rsatamiz: 12 soniyada bozor xaritasi chiziladi, kamera tekshiradi, bitta rasta amber qoladi — «Band, lekin to'lovsiz» — to'lov tushadi, hisobot yig'iladi. So'zsiz. ⛔ Hokimlik vakili ikkala saytni ochganda farqni **10 soniyada** his qilishi kerak.
> ⛔ Bu faza **9-fazaning dizayn tizimini MEROS qilib oladi** — landing app tokenlaridan **oqadi**, o'z tizimini qurmaydi. Mijoz demoda «reklamadagi bilan bir xil ekan» deyishi — bu fazaning **o'lchanadigan maqsadi**, bezak emas.
> ⛔⛔ Hero, copy va 3-qadam naqshi **foydalanuvchi tomonidan 2026-08-16 da tasdiqlangan** (sketch 003-B). Ular bu hujjatda **qayta ochilmaydi** — shartnoma sifatida yoziladi.
> Yaratdi: `gsd-ui-researcher`. Tekshiradi: `gsd-ui-checker`. Iste'mol qiladi: `gsd-planner`, `gsd-executor`.

---

## 0. Dalil holati va shu sessiyada bajarilgan o'lchovlar

| Belgi | Ma'nosi |
|-------|---------|
| **[O'LCHANDI]** | Shu sessiyada kodbazada yoki skript bilan o'lchandi — natija keltirilgan |
| **[KOD]** | Kodbazadan o'qildi — aniq `fayl:qator` keltirilgan |
| **[QULF]** | Foydalanuvchi tasdiqlagan qaror (sketch 003-B, 2026-08-16) — **qayta ochilmaydi** |
| **[MEROS]** | Upstream artefaktdan (ROADMAP Phase 10, LANDING-BRIEF, 09-UI-SPEC, `landing-sehri.md`, CLAUDE.md) |
| **[QAROR]** | Shu hujjatda qabul qilindi — sabab yozilgan, muqobil rad etilgan |
| **[TALAB]** | UI backend'dan talab qiladigan narsa — rejaga bevosita kiradi |
| **[ASSUMED]** | Dalilsiz tanlangan qiymat — sabab va qayta ko'rish tetigi yozilgan |

### 0.1 O'lchovlar

| # | O'lchov | Natija |
|---|---------|--------|
| **L-1** | **shadcn darvozasi** — `find . -maxdepth 3 -name components.json` (node_modules'siz) | **0 natija** → `Tool: none`. 2–9-faza qarori davom etadi (§3.1) |
| **L-2** | ⛔⛔ **`text-base` chegarasi TO'LGAN** — `src/**` (test/izohsiz) skani | **`text-base` = 7**, `typography.test.mjs:318` da qulflangan chegara ham **7**. ⛔ **Landing birorta 16px matn yoza olmaydi** — §7 ning butun asosi |
| **L-3** | **Qolgan tipografiya sanog'i** [O'LCHANDI] | `text-xl` **3** (chegara 4 — **1 joy bo'sh**) · `text-3xl` **0** (qattiq nol) · `text-[` **0 fayl** (qattiq nol) · `font-medium` **21** (chegara 21 — **bo'sh joy yo'q**) · `text-lg` **47** va `text-2xl` **31** — ⛔ **chegarasiz**, landing shulardan quradi |
| **L-4** | ⛔ **`text-display` reyestri** [O'LCHANDI] | **Aynan 2 fayl**: `collect/pending-card.tsx`, `headline/headline-card.tsx` — `deepEqual` bilan qulflangan. ⛔ Landing bu utilitani **ishlata olmaydi** (§7.2) |
| **L-5** | ⛔⛔ **ILDIZ LAYOUT BUTUN MATN KATALOGINI KLIENTGA JO'NATADI** [KOD: `app/[locale]/layout.tsx:112`] | `<NextIntlClientProvider messages={messages}>` — `messages` **to'liq**. O'lchandi: uz-Latn **77 117 B raw / 21 768 B gzip** · uz-Cyrl **107 432 B / 25 195 B** · ru **109 805 B / 27 051 B**. ⛔ Landing ~90 kalit ishlatadi, **1373** tasini yuklaydi (§4.3) |
| **L-6** | **Ildiz layout klient provayderlari** [KOD: `layout.tsx:112-121`] | `NextIntlClientProvider` → `NuqsAdapter` → `QueryProvider` → `AuthProvider` → `Toaster` — **beshtasi ham** har marshrutga tushadi, jumladan anonim landing'ga. ⚠ Ularning JS og'irligi **o'lchanmadi** (§4.3 da halol yozilgan) |
| **L-7** | ⛔ **Ildiz sahifa bugun `/dashboard` ga redirect qiladi** [KOD: `app/[locale]/page.tsx:29`] | `redirect({ href: "/dashboard", locale })`. ⛔ ROADMAP SC#1 aynan shu faylni **landing bilan almashtirishni** talab qiladi (§4.1) |
| **L-8** | ⛔⛔ **SKETCH SAHNASINING IKKI ANIMATSIYASI GPU QOIDASINI BUZADI** [KOD: `003-landing-hero.html:66,89`] | `@keyframes sweepgo { left: 0 → 100% }` va `.prog { transition: height 900ms }`. ⛔ `left` va `height` — `motion-tokens.test.mjs:101` dagi `BANNED_KEYFRAME_PROPS` **ro'yxatida**. Ikkalasi ham §5.3 da qayta yoziladi |
| **L-9** | **`@keyframes` reyestri bugun** [O'LCHANDI: `globals.css`] | **8 nom**: `draw · ringpulse · landin · enter · shimmer · breath · attention · shake`. ⛔ Landing **aynan bitta** yangi nom qo'shadi — `sweep` (§5.4) |
| **L-10** | ⛔ **Hero'ning ikki animatsiyasi ALLAQACHON MAVJUD** [O'LCHANDI] | `.motion-enter` (`translateY(8px)`+fade, `--i` stagger) = sketch'ning `fade-up` **ayni**; `.motion-attention` (amber halqa, **BIR marta**, `--motion-slow`) = sketch'ning `attn` **ayni**. ⛔ **Ikkalasi ham qayta yozilmaydi** (§5.4) |
| **L-11** | ⛔⛔ **`AI` KIRILLDA BUZILADI** [O'LCHANDI: `transliterate("AI band rastani aniqlaydi", words)`] | Natija — **`АИ банд растани аниқлайди`**. ⛔ `AI` `uz-Cyrl.overrides.json` `words` da **YO'Q** (`SBOZOR`, `NVR`, `VPN`, `NTP`, `RTSP`, `ISAPI` bor). Tuzatish **JUFT** (§13.4) |
| **L-12** | **Transliteratsiya sinovi** — 40 nomzod landing satri `words` lug'ati bilan | ⛔ **`AI` dan boshqa 0 defekt.** `Har bir band rastadan patta to'liq yig'ilyaptimi?` → `Ҳар бир банд растадан патта тўлиқ йиғиляптими?`; `Demo so'rang` → `Демо сўранг`; `SBOZOR`/`NVR`/`VPN` **lotin** qoladi ✅ |
| **L-13** | ⛔⛔ **LANDING RANG JUFTLIKLARI UCHALA TEMADA AA'DAN O'TADI** [O'LCHANDI: mustaqil kalkulyator, 5 kanonik qiymat bilan **baytma-bayt** tasdiqlangan] | `warning-text/surface` **6.05 / 6.94 / 8.50** · `success-text/bg` **5.83 / 6.04 / 8.08** · `accent/bg` **4.52 / 5.66 / 4.72** · `text-muted/bg` **5.06 / 7.71 / 11.31** (light/dark/sun). ⛔ **Birorta buzilish yo'q** → §6.4 ning butun asosi: landing temani **qulflamaydi** |
| **L-14** | **Kalkulyator nazorati** [O'LCHANDI] | Mustaqil oklch→sRGB→WCAG kalkulyatori loyihaning `contrast.test.mjs --print` chiqishidagi **beshala** kanonik sonni aynan qaytardi: `text/bg` **17.16** · `text/surface` **17.91** · `text-muted/bg` **5.06** · `accent-fg/accent` **4.72** · `warning/surface` **2.02**. Ya'ni L-13 sonlari **da'vo emas** |
| **L-15** | ⛔ **`LocaleSwitcher` anonim holatda ISHLAYDI** [KOD: `shell/locale-switcher.tsx:103`] | `if (!accessToken) return;` — izoh so'zma-so'z: «Kirish qilinmagan holatda (login sahifasi) profil yo'q — faqat URL almashadi». ⛔ Landing uni **qayta yozmaydi** (§9.2) |
| **L-16** | **`LocaleSwitcher` bugun QAYERDA** [O'LCHANDI] | ⛔ **Aynan 1 joy**: `shell/app-shell.tsx:483`. Login sahifasida **yo'q**. Landing **ikkinchi iste'molchi** bo'ladi |
| **L-17** | ⛔ **`ui/button.tsx` da hero o'lchami YO'Q** [KOD: `ui/button.tsx:41-46`] | `sm` (h-9) · `md` (h-10) · `lg` (min-h-11) — ⛔ **uchalasi ham `text-sm`**. Hero CTA uchun beshinchi o'lcham qo'shiladi (§7.4) |
| **L-18** | **`Button` variant reyestri darvoza bilan qulflanmagan** [O'LCHANDI] | `scripts/*.test.mjs` da `buttonVariants`/`SIZES` skani — **0 natija** (`submit-gate.test.mjs:440` faqat fikstura satri). ⛔ Ya'ni yangi o'lcham **hech qanday darvozani buzmaydi** |
| **L-19** | ⛔⛔ **G-SUBMIT LANDING FORMASINI HAM QAMRAYDI** [KOD: `scripts/submit-gate.test.mjs:52`] | Skan yuzasi — `src/**` (test fayllarsiz). ⛔ Demo-forma «jim-disabled submit» anti-naqshini **ishlata olmaydi** (§12.3) |
| **L-20** | **`useCountUp` va `prefersReducedMotion` MAVJUD** [KOD: `lib/use-count-up.ts:77,96`, `lib/motion.ts`] | Ikkalasi ham `prefers-reduced-motion` ni **o'zi hurmat qiladi**. ⛔ Hero tushum hisoblagichi **shulardan** quriladi (§5.5) |
| **L-21** | **`dependencies` reyestri** [O'LCHANDI] | **18 nom**, `motion-tokens.test.mjs:134` dagi `EXPECTED_DEPENDENCIES` bilan `deepEqual`. ⛔ Landing **0 paket** qo'shadi [QULF] |
| **L-22** | **Matn katalogi hajmi** [O'LCHANDI] | **1373 / 1373 / 1373** kalit, **31** fazoviy nom — parity bugundan yashil. Landing **32-chi** fazoviy nomni ochadi |
| **L-23** | ⛔ **Glossariy landing matnini ham bog'laydi** [KOD: `ops/i18n/glossary.json`] | `rasta` → ru **`мест`**; ⛔ **taqiq**: uz `do'kon`, ru `лавк`/`магазин`. `patta` → ru **`патт`**; ⛔ **taqiq**: uz `yig'im`. §13.3 |
| **L-24** | **`proxy.ts` matcher `sitemap.xml`/`robots.txt` ni chetlab o'tadi** [KOD: `proxy.ts:17`] | `"/((?!api\|_next\|_vercel\|.*\\..*).*)"` — nuqtali yo'llar tashqarida. ⛔ SEO fayllari `src/app/` ildizida yashaydi (§14.2) |
| **L-25** | **Backend'da anonim (public) marshrut yo'q** [O'LCHANDI: `services/core-api/app/api/v1/`] | 25 modul, birortasi ham public emas. ⛔ Demo-forma **yangi yuza** ochadi — §12.5 [TALAB] |
| **L-26** | ⛔ **`G-18` e'lon darvozasi** [KOD: `bulk-action-surface.test.mjs:88,113`] | Skan **barcha** `*-UI-SPEC.md` fayllarini ko'radi, lekin **faqat** `` /^\|\s*\*\*G-18\*\*\s*\|/ `` qatori **borlarini** sanaydi va **aynan 1** talab qiladi. ⛔ **Oqibat: bu fayl ham shunday qator YOZMAYDI** (§16.1) |

### 0.2 ⛔⛔ L-2 + L-4 ning oqibati — bu fazaning eng qimmat tuzog'i

```
typography.test.mjs:318   locked = { "text-base": 7, "text-xl": 4, "text-3xl": 0, "font-medium": 21 }
o'lchov (2026-08-17)              text-base 7 · text-xl 3 · text-3xl 0 · font-medium 21
                          ⛔⛔ text-base va font-medium — CHEGARADA. BO'SH JOY NOL.
```

Landing — **marketing yuzasi**: sarlavha katta, matn uzun, o'qish masofasi uzoq (hokimlik proyektori!). Tabiiy refleks — `text-base` (16px) va `text-[clamp(...)]`. ⛔ **Ikkalasi ham bugun mexanik ravishda imkonsiz**: birinchisi chegarani 7→8 ga chiqarib darvozani qizartiradi, ikkinchisi `text-[` ning **qattiq nol**iga uriladi.

> ⛔ Bu «intizom masalasi» emas: `typography.test.mjs` bugun tirik va landing'ning **birinchi** `text-base` i darvozani qizartiradi.

**Rad etilgan muqobil — `text-base` chegarasini ko'tarish (7 → 20).** ⛔ Rad sababi mexanik: chegara **repozitoriya bo'ylab** ishlaydi, katalog bo'yicha emas. 20 ga ko'tarish landing'ga 13 joy bermaydi — u **butun ilovaga** 13 joy beradi va `typography.test.mjs:30` da yozilgan maqsadni («MEROS DEVIATSIYALAR **O'SMAYDI**») jimgina bekor qiladi. Bir fazaning qulayligi uchun boshqa fazaning leshi kesilmaydi.

**Tanlangan yo'l** (§7): landing **aynan bitta** yangi tipografiya tokeni oladi — `--text-hero` (suyuq `clamp`, h1 uchun) — qolgan hammasi **mavjud rollarga** tushadi: `text-2xl` (24px, seksiya sarlavhasi, **chegarasiz**) · `text-lg` (18px, lid va qadam sarlavhasi, **chegarasiz**) · `text-sm` (14px, proza) · `text-xs` (12px, ishonch qatori). ⛔ Iliqlik va havo **o'lchamdan emas, joylashuvdan** keladi: tor proza ustuni (≤66ch), `leading-relaxed`, kengaytirilgan seksiya ritmi (§8.2).

---

## 1. Ko'lam

### 1.1 To'rtta yuza

| # | Yuza | Nimaga javob beradi | Foydalanuvchi | Ustuvorlik |
|---|------|---------------------|---------------|------------|
| **Y-1** | ⛔ **Hero — 12s «jonli bozor» sikli** | «Bu nima va menga nima beradi?» — **so'zsiz** | Direktor, hokimlik vakili | ⛔ **ENG YUQORI** |
| **Y-2** | **Demo-forma** — yagona konversiya nuqtasi | «Qanday bog'lanaman?» | Qaror qabul qiluvchi | ⛔ **Yuqori — bu sahifaning YAGONA maqsadi** |
| **Y-3** | **Ishonch qatlami** — davlat bloki, pilot holati, maxfiylik siyosati | «Bu qonuniymi va ishonsam bo'ladimi?» | Hokimlik, yurist | Yuqori — ⛔ **va u huquqiy masala, did emas** |
| **Y-4** | **Hikoya bloklari** — og'riq, 3 qadam, ⭐ dalil, rollar, FAQ | «Qanday ishlaydi?» | Hammasi | O'rta — ⛔ **lekin matn og'irligi shu yerda** |

⛔ **App yuzalari (`/dashboard`, `/collect`, …) BU FAZAGA KIRMAYDI** — landing ularga **faqat havola** qiladi (`/login`).

### 1.2 ⛔ Y-1 nima uchun eng yuqori — va u sahifani QANDAY jimgina o'ldiradi

ROADMAP Phase 10 SC#5: *«Lighthouse ≥95, LCP <1.5s»*. `landing-sehri.md` so'zma-so'z: *«Hero LCP > 1.5s — sahna birinchi ekran matnini bloklamasin»*.

> Hokimlik vakili telefonda havolani ochadi. Sahna 30 ta katak, 5 fazali taymer, tushum hisoblagichi va hisobot kartasidan iborat. Agar sarlavha shu sahna **hidratatsiyasini kutsa** — birinchi 1,5 soniyada ekranda **oq bo'shliq** turadi. ⛔ Foydalanuvchi orqaga qaytadi. **Sehr sekin yuklansa, sehr emas.**
> ⛔⛔ Ya'ni bu fazada **eng qimmat nuqson — sahnaning o'zi**.

Beshta qoida **muzokarasiz** va §16 da darvozaga aylanadi:

| # | Qoida | Nega |
|---|-------|------|
| **1** | ⛔ **Birinchi ekran matni sahnani KUTMAYDI** — `h1`, lid, CTA, ⭐ dalil, ishonch qatori **Server Component** | LCP nomzodi — `h1`. U klient JS'ga bog'lanmaydi (**G-land-1**) |
| **2** | ⛔ **Server YAKUNIY KADRNI chizadi, sahna undan DAVOM etadi** | JS kelmasa ham kompozitsiya **to'liq**; `prefers-reduced-motion` shoxi **alohida kod emas** (§5.2, **G-land-2**) |
| **3** | ⛔ **Faqat `transform`/`opacity`** — `left`/`height`/`width` **animatsiya qilinmaydi** | L-8: sketch manbasi **ikki joyda** buzgan; arzon Androidda layout-thrash 60fps ni o'ldiradi (**G-land-3**) |
| **4** | ⛔ **Yangi npm paketi 0** | [QULF] + L-21: `dependencies` `deepEqual` bilan qulflangan (mavjud **G-motion-3(d)**) |
| **5** | ⛔ **Yolg'on raqam yo'q** — sahnadagi har son «namunaviy» belgisi ostida | [QULF] + brief §7.5 «Halollik» qatori: raqib «ishlab chiqilmoqda» yozib do'kon badge'larini qo'ygan — biz **teskarisini** qilamiz (**G-land-4**) |

### 1.3 ROADMAP mezonlarining qamrovi

| SC | UI'da qanday ko'rinadi |
|----|------------------------|
| **SC#1** | §4 — `(marketing)` route-guruhi, ildiz sahifa almashtiriladi, uchala til SSG, «Kirish» → `/login` |
| **SC#2** | §5 — 12s siklning **5 fazasi**, har birida **aniq timing** va **aniq DOM holati**; reduced-motion = **server kadri** |
| **SC#3** | §12 — demo-forma, uchta holat (idle / yuborilmoqda / natija), G-SUBMIT ga mos, [TALAB] §12.5 |
| **SC#4** | §11 (davlat bloki) + §13.6 (pilot holati) — ⛔ **halollik darvozasi G-land-4** |
| **SC#5** | §4.3 (payload) + §14 (SEO) + §16.5 (Lighthouse **halol joylashtirish**) |

### 1.4 Bu faza NIMA QILMAYDI (to'lig'i §17)

Brief §7.2 ning to'liq «Bozorning bir kuni» kino-scroll'i · app'dan real skrinshotlar · CTA'da kursor-yaqinlik nuri · fon donadorligi (grain) · rol-kartalarida hover mini-animatsiyasi · narx kalkulyatori · blog · ro'yxatdan o'tish · pilot **raqamlari** · A/B test · analitika skripti.

---

## 2. Qulflangan qarorlar — shartnoma sifatida

⛔ Quyidagi o'nta band **topshiriqda qulflangan** (sketch 003-B, foydalanuvchi tasdiqlagan 2026-08-16). Ular **qayta so'ralmaydi va qayta ochilmaydi**.

| # | Qulflangan qaror | Manba | Bu hujjatdagi joyi |
|---|------------------|-------|--------------------|
| **K-1** | Hero = **12s «jonli bozor» sikli**, 5 faza yorlig'i bilan; **video EMAS** (CSS/JS); reduced-motion'da **statik final-kadr** | sketch 003-B | §5 |
| **K-2** | Copy qulflangan: sarlavha · javob · ⭐ dalil · ishonch qatori (4 band) · CTA «Demo so'rang» (**yagona**) · ikkilamchi «Tizimga kirish» | brief §2 + sketch 003-B | §13.1 |
| **K-3** | **3-qadam** «qanday ishlaydi» — C variantining chiziq-to'lish naqshi, **hero EMAS**, sahifaning **3-seksiyasi** | sketch 003-C | §10 |
| **K-4** | `(marketing)` route-guruhi **mavjud Next.js ichida**; anonim root = landing; **SSG**, 3 til | ROADMAP Chegaralar | §4 |
| **K-5** | Demo-forma → **admin Telegram-bot** (mavjud `bot-service`); **CRM yo'q** | ROADMAP SC#3 | §12.5 |
| **K-6** | **Lighthouse ≥95, LCP <1.5s** — birinchi ekran matni sahnani **kutmaydi** | ROADMAP SC#5 | §1.2, §4, §16.5 |
| **K-7** | ⛔ **Yolg'on raqam TAQIQ** — pilot holati «Karmana bozorida sinovda»; hero raqamlari **namunaviy** deb belgilanadi | brief §2.7 + `landing-sehri.md` | §5.6, §13.6, G-land-4 |
| **K-8** | **Maxfiylik siyosati sahifasi majburiy** (CCTV shaxsiy ma'lumot qonuni) | ROADMAP Chegaralar | §11.3, §15.4 |
| **K-9** | ⛔ **Yangi npm paketi TAQIQ**; landing **app tokenlaridan oqadi** — «bir oila» ko'rinishi | 09-UI-SPEC §3.2 + L-21 | §3.2 |
| **K-10** | Mavjud `G-*` va `G-motion-*` darvozalari **buzilmaydi**; skan maydonlari kengaysa — **ONGLI** (nom o'zgarishi bilan) | Topshiriq | §16 |

⛔ **K-9 ning o'qilishi — bu hujjatning yagona «kengaytiruvchi» talqini va u ochiq yoziladi:** «landing app tokenlaridan oqadi» **teng** degani emas. Landing **bitta** yangi tipografiya tokeni (`--text-hero`), **bitta** yangi `@keyframes` (`sweep`), **ikkita** yangi bo'shliq qiymati (64/96px seksiya ritmi) va **bitta** yangi tugma o'lchami (`hero`) oladi. Hammasi **nomlangan, sanoqli va darvoza bilan cheklangan**. ⛔ Yangi **rang** tokeni — **0**; yangi **paket** — **0**; yangi **tema** — **0**.

---

## 3. Dizayn tizimi holati

### 3.1 shadcn darvozasi — natija [L-1]

**`components.json` topilmadi** → **`Tool: none`. `shadcn init` BAJARILMAYDI.** [QAROR — 2–9-faza qarorini davom ettiradi]

Sabablar o'zgarmadi va bittasi **kuchaydi**: (1) `shadcn init` Tailwind 4 rejimida `globals.css` ga **o'z token nomlarini** yozadi va 9-faza qurgan **uch temali `data-theme` scope'i** bilan to'qnashardi; (2) `shadcn` ning `dark` konvensiyasi `.dark` **class** ga tayanadi, bizda esa `data-theme` **atributi** + **uch** tema; (3) ⛔ **yangisi** — landing'ning butun qiymati «app bilan bir oila» ko'rinishida, ikkinchi dizayn tizimi esa aynan buni buzardi.

**Oqibat:** `Registry Safety` darvozasi shadcn uchun **qo'llanmaydi** (§15, §19). Uchinchi tomon registry **yo'q**, vendored blok **yo'q**.

### 3.2 ⛔⛔ Yangi npm paketi — **YO'Q** [K-9, L-21]

**[QAROR]** Bu fazada `package.json` ning `dependencies` bo'limi **o'zgarmaydi** (18 nom, `deepEqual`).

| Landing ehtiyoji | Kerakli mexanizm | Kutubxona kerakmi |
|---|---|---|
| Hero 12s sikli (5 faza) | `setTimeout` reyestri + sinf almashtirish — **~70 qator** | ⛔ Yo'q |
| Kamera nuri | `@keyframes sweep` (`transform: translateX`) | ⛔ Yo'q |
| Rasta kataklarining stagger'i | CSS `transition` + inline `--i` indeks | ⛔ Yo'q |
| Amber diqqat-halqasi | ⛔ **`.motion-attention` ALLAQACHON BOR** [L-10] | ⛔ Yo'q |
| Hero kirish ketma-ketligi | ⛔ **`.motion-enter` ALLAQACHON BOR** (`--i` stagger) [L-10] | ⛔ Yo'q |
| Tushum count-up | ⛔ **`useCountUp` ALLAQACHON BOR** [L-20] | ⛔ Yo'q |
| Scroll-reveal | `IntersectionObserver` (native) + `.motion-enter` sinfini qo'shish | ⛔ Yo'q |
| 3-qadam chizig'ining to'lishi | `transform: scaleY()` + `data-step` atributi (§10.2) | ⛔ Yo'q |
| Demo-forma validatsiyasi | ⛔ **`react-hook-form` + `zod` ALLAQACHON BOR** | ⛔ Yo'q |
| SEO / OG | ⛔ **Next 16 `generateMetadata` + fayl konventsiyalari** | ⛔ Yo'q |

⛔ **Dalil:** [09-UI-SPEC M-14] sketch 001/002/003 fayllarida `cdn`/`unpkg`/`<script src` — **0 marta**. ⛔ Ya'ni foydalanuvchi tasdiqlagan 12s siklning **o'zi** kutubxonasiz qurilgan va tasdiqlangan.

**Qayta ko'rish tetigi:** agar reja bajarilishida sahnaning birorta fazasi **o'lchangan** ravishda sof CSS+vanilla bilan chiqmasa — paket **UI-SPEC ga qaytariladi**, byudjet **0 KB dan chiqmaydi** (Lighthouse ≥95 **arzon Android** profilida, §16.5).

### 3.3 Meros — o'zgarmaydi va qayta qurilmaydi

| Nima | Fayl | 10-fazada |
|------|------|-----------|
| Tailwind 4 CSS-first `@theme` | `globals.css` | ⛔ **Kengayadi** (1 tipografiya tokeni + 1 `@keyframes` + landing sinflari), lekin ⛔ `@theme inline` **TAQIQ** (G-motion-4(b)) |
| Uch tema (`light`/`dark`/`sun`) token-scope | `globals.css` | ⛔ **TEGILMAYDI** — landing ularni **meros oladi** (§6.4) |
| 8 nomli `@keyframes` reyestri | `globals.css` | ⛔ **9 ga chiqadi** (`sweep`), boshqasi tegilmaydi |
| Motion tokenlari (`--motion-*`, `--ease-*`) | `globals.css` | ⛔ **Tegilmaydi** — landing shulardan oziqlanadi |
| `Button` (4 variant, 3 o'lcham) | `ui/button.tsx` | ⛔ **Beshinchi o'lcham** `hero` qo'shiladi (§7.4) — variantlar **tegilmaydi** |
| `Card`, `Field`, `Input`, `Select`, `Badge`, `EmptyState`, `Skeleton`, `Dialog`, `ConfirmDialog` | `ui/*` | ⛔ **Tegilmaydi** |
| `LocaleSwitcher` | `shell/locale-switcher.tsx` | ⛔ **Tegilmaydi** — landing **ikkinchi iste'molchi** [L-15, L-16] |
| `ThemeToggle` | `shell/theme-toggle.tsx` | ⛔ **Landing'da KO'RSATILMAYDI** (§6.4) |
| `AppShell`, navigatsiya, RBAC | `shell/*`, `lib/rbac.ts` | ⛔ **Tegilmaydi** — landing ularni **import qilmaydi** |
| `sonner` Toaster | `layout.tsx:117` | ⛔ **Landing'da ISHLATILMAYDI** (§12.4) |
| `useCountUp`, `prefersReducedMotion` | `lib/use-count-up.ts`, `lib/motion.ts` | ⛔ **Qayta yozilmaydi** [L-20] |
| `i18n:check`, `gen-cyrillic` zanjiri | `scripts/*` | ⛔ Yangi kalitlar **shundan o'tadi**; `AI` bandi §13.4 |

### 3.4 Yangi `ui/` primitivi — YO'Q

Landing komponentlari `src/components/marketing/**` da yashaydi va ⛔ **`ui/` ga ko'tarilmaydi**:

| Komponent | Nega `ui/` emas |
|-----------|------------------|
| `marketing/hero-scene.tsx` | Uning kontrakti — **12 soniyalik rejissyorlangan hikoya**, umumiy «animatsiyali karta» emas |
| `marketing/step-line.tsx` | 3 qadam **qulflangan** [K-3]; `ui/` dagi «timeline» ertaga `steps={n}` propini olardi |
| `marketing/demo-form.tsx` | Yagona anonim yozuv yuzasi; `ui/Field` + `ui/Input` ni **ishlatadi**, ularni **almashtirmaydi** |
| `marketing/section.tsx` | Faqat marketing ritmi (§8.2) — app'da sahifa ritmi **boshqa** |

⛔⛔ **JOYLASHUV QOIDASI MEXANIK, DID EMAS:** landing komponentlari **`src/components/marketing/**` da bo'lishi SHART**, chunki `motion-tokens.test.mjs` ning G-motion-3(b) skani (`duration-<raqam>` = 0, `transition-[` = 0, inline `animation:` = 0) aynan **`src/components/**`** ni ko'radi. ⛔ Agar landing markup'i `app/[locale]/(marketing)/page.tsx` ichida yozilsa, u **darvozadan tashqarida** qoladi va sehrli sonlar **jimgina** qaytadi.

---

## 4. Marshrut va yetkazish arxitekturasi

### 4.1 Marshrut xaritasi [K-4, L-7]

| URL | Fayl | Render | Kim |
|-----|------|--------|-----|
| `/` | — | `proxy.ts` → `/uz` [KOD: `routing.ts` `localePrefix: always`] | Hamma |
| `/uz` · `/uz-cyrl` · `/ru` | ⛔ `app/[locale]/(marketing)/page.tsx` | **SSG** | ⛔ **Anonim** |
| `/uz/maxfiylik` · `/uz-cyrl/maxfiylik` · `/ru/maxfiylik` | `app/[locale]/(marketing)/maxfiylik/page.tsx` | **SSG** | Anonim [K-8] |
| `/uz/login` | mavjud `(auth)/login` | ⛔ **Tegilmaydi** | Anonim |
| `/uz/dashboard` … | mavjud `(app)/**` | ⛔ **Tegilmaydi** | Sessiyali |

⛔⛔ **`app/[locale]/page.tsx` O'CHIRILADI va uning `redirect` i QAYTARILMAYDI** [L-7]. Sabab **muzokarasiz**: ROADMAP SC#1 — *«`sbozor.uz/` (anonim root) landing ko'rsatadi»*.

⛔⛔ **SESSIYAGA QARAB REDIRECT QILINMAYDI** [QAROR]. «Kirgan foydalanuvchini `/dashboard` ga yuborish» **jozibali va xato**: (a) u sahifani **dinamik** qiladi va SSG'ni — ya'ni SC#5 ning butun asosini — yo'q qiladi; (b) sessiya `httpOnly` cookie'dagi **refresh** tokenida, ya'ni tekshiruv **serverda API chaqirig'ini** talab qiladi va u LCP yo'liga tushadi; (c) hokimlik vakili demo ko'rsatayotgan direktorning telefonida landing **umuman ochilmasdi**. ⛔ Ildiz **har doim** landing; app'ga o'tish — **ko'rinadigan tugma** (`landing.login`).

⛔ **Maxfiylik sahifasi slug'i locale bo'yicha o'zgarmaydi** — uchala tilda `maxfiylik` [ASSUMED]. Sabab: `next-intl` ning `pathnames` xaritasi bugun **konfiguratsiya qilinmagan** (`routing.ts` da yo'q) va uni faqat bitta sahifa uchun ochish marshrut qatlamiga **yangi mexanizm** qo'shardi. **Tetigi:** SEO auditi lokalizatsiyalangan slug talab qilsa — `defineRouting` ga `pathnames` **bir marta** qo'shiladi va **barcha** marshrutlar bir vaqtda ko'chadi.

### 4.2 SSG shartlari

| Talab | Mexanizm |
|-------|----------|
| Uchala til oldindan chiziladi | ⛔ **Mavjud** `generateStaticParams()` [KOD: `layout.tsx:26-29`] — `(marketing)` guruhi uni **meros oladi** |
| Sahifa dinamik bo'lib qolmaydi | ⛔ `setRequestLocale(locale)` **birinchi** chaqiriladi [KOD: `layout.tsx:61` naqshi]; `cookies()`, `headers()`, `searchParams` ⛔ **ishlatilmaydi** |
| Sahna sahifani dinamik qilmaydi | Sahna — **klient oroli**, sahifa — server |
| Forma sahifani dinamik qilmaydi | Yuborish — **klient `fetch`**, server amali emas |

### 4.3 ⛔⛔ Payload — bu fazaning ikkinchi eng qimmat qarori [L-5, L-6]

**O'lchangan holat:** ildiz layout **butun** matn katalogini klientga uzatadi — landing ~90 kalit ishlatib **1373** tasini yuklaydi:

| Locale | Raw | ⛔ Gzip |
|--------|-----|---------|
| uz-Latn | 77 117 B | **21 768 B** |
| uz-Cyrl | 107 432 B | **25 195 B** |
| ru | 109 805 B | **27 051 B** |

⛔ **Ya'ni rus tilidagi landing 27 KB gzip'lik ADMIN satrlarini yuklaydi** — kassir smenasi, NVR xatolari, xlsx sarlavhalari. Lighthouse ≥95 va LCP <1.5s byudjetida bu **o'lchanadigan** yo'qotish, va u sahifaning birorta pikselini chizmaydi.

**[QAROR] Provayderlar `(app)` va `(auth)` guruhlariga TUSHIRILADI; `(marketing)` o'z toraytirilgan provayderini beradi.**

| Fayl | Keyin nima qoladi |
|------|-------------------|
| `app/[locale]/layout.tsx` | ⛔ **Faqat**: `<html>` + `data-theme` + `suppressHydrationWarning` + FOUC skripti + `<body>` + `generateStaticParams` + `generateMetadata`. ⛔ **Beshala provayder chiqadi** |
| `app/[locale]/(app)/layout.tsx` | ⛔ **Mavjud** `AppProviders` ni o'raydi (`NextIntlClientProvider` **to'liq katalog** + `NuqsAdapter` + `QueryProvider` + `AuthProvider` + `Toaster`) |
| `app/[locale]/(auth)/layout.tsx` | ⛔ **Ayni** `AppProviders` |
| `components/shell/app-providers.tsx` | ⛔ **YANGI** — beshala provayderning **yagona** ta'rifi; ikki guruh uni **import qiladi**, nusxa **olinmaydi** |
| `app/[locale]/(marketing)/layout.tsx` | ⛔ **Faqat** `NextIntlClientProvider` va **faqat ikki fazoviy nom**: `landing` + `common` |

⛔ **Nega bu «yo'l-yo'lakay refaktor» emas:** SC#5 ning raqami (**≥95**) mexanizmsiz bajarilmaydi. Va xavf **o'lchangan darajada tor**: `[locale]/` ildizida `layout.tsx` va `page.tsx` dan **boshqa fayl yo'q** [O'LCHANDI], `page.tsx` esa aynan landing bilan almashtiriladi. Ya'ni provayderlarsiz qoladigan **birorta mavjud sahifa yo'q**.

⚠ **HALOLLIK — o'lchangan va o'lchanmagan yarim:** matn katalogining **21,8–27,1 KB gzip** i **o'lchandi**. Beshala provayderning **JS** og'irligi (react-query, nuqs, sonner, auth-store, zod grafi) ⛔ **O'LCHANMADI** — u `next build` chiqishini talab qiladi va bu sessiyada bajarilmadi. ⛔ **«~50 KB tejaladi» degan da'vo BERILMAYDI.** Rejaning birinchi vazifasi — o'zgarishdan **oldin va keyin** `next build` route-payload jadvalini olish va farqni **son bilan** yozish (§16.5, HUMAN-UAT).

**Rad etilgan muqobil — ildiz layout'ni tegmasdan qoldirish.** ⛔ Rad sababi: landing'ning har ochilishi 22–27 KB gzip **o'lik** matn yuklardi va SC#5 birinchi o'lchovdayoq xavf ostiga tushardi. **Qayta ko'rish tetigi:** agar `AppProviders` ko'chirishi `(app)` yoki `(auth)` da **o'lchangan** regressiya bersa — ko'chirish **qaytariladi**, landing esa o'z `NextIntlClientProvider` ini **ichkarida ikkinchi marta** e'lon qiladi (ichki provayder tashqarisini **soyalaydi**), va payload yo'qotilishi HUMAN-UAT bandiga **son bilan** yoziladi.

### 4.4 Klient orollari — YOPIQ reyestr

⛔ Landing'da `"use client"` **aynan to'rt** faylda:

| # | Fayl | Nega klient |
|---|------|-------------|
| 1 | `marketing/hero-scene.tsx` | 12s taymer reyestri, `IntersectionObserver`, `useCountUp` |
| 2 | `marketing/step-line.tsx` | `IntersectionObserver` (qadam ochilishi) |
| 3 | `marketing/reveal.tsx` | `IntersectionObserver` o'ramasi (scroll-reveal) — ⛔ **bitta** umumiy ta'rif |
| 4 | `marketing/demo-form.tsx` | `react-hook-form` + `fetch` |

⛔ Qolgan hammasi — **Server Component**. ⛔ `LocaleSwitcher` **beshinchi emas**: u allaqachon klient komponenti va landing uni **import qiladi**, yangi orol ochmaydi (**G-land-1(c)**).

---

## 5. Y-1 — Hero: 12 soniyalik «jonli bozor» sikli [K-1]

### 5.1 Sahna kompozitsiyasi

```
┌─ hero (grid 1.05fr / 1fr; ≤840px da 1 ustun) ─────────────────────────┐
│  CHAP — SERVER COMPONENT (LCP)          O'NG — KLIENT OROLI          │
│  ┌───────────────────────────┐          ┌──────────────────────────┐ │
│  │ SBOZOR            (brand) │          │ ⓘ Namunaviy ma'lumot     │ │
│  │ H1: Har bir band rasta…   │          │ Namuna bozori · 2 306 000│ │
│  │ Lid: SBOZOR buni…         │          │ ┌──┬──┬──┬──┬──┬──┐      │ │
│  │ [Demo so'rang] [Kirish]   │          │ │  │  │  │██│  │  │      │ │
│  │ ⭐ Yangi uskuna shart emas │          │ ├──┼──┼──┼──┼──┼──┤      │ │
│  │ ✓ … ✓ … ✓ … ✓ …           │          │ │  │  │  │  │  │  │  ×5  │ │
│  └───────────────────────────┘          │ └──┴──┴──┴──┴──┴──┘      │ │
│                                          │ ┌─ Kunlik hisobot ───┐  │ │
│                                          │ │ Band 215 · To'l 214│  │ │
│                                          │ │ Band, to'lovsiz 1→0│  │ │
│                                          │ └────────────────────┘  │ │
│                                          └──────────────────────────┘ │
└───────────────────────────────────────────────────────────────────────┘
```

### 5.2 ⛔⛔ Server YAKUNIY KADRNI chizadi — sahna undan DAVOM etadi [QAROR]

Bu §1.2 qoida 2 ning mexanikasi va u **uchta muammoni bir vaqtda** yechadi.

| Muammo | Yechim |
|--------|--------|
| LCP sahnani kutadi | ⛔ Server **to'liq final-kadrni** chizadi (30 katak `on`+`paid`, bitta `unpaid`, hisobot **ochiq**, tushum `2 306 000`). JS kelmasa ham **hech nima yetishmaydi** |
| `prefers-reduced-motion` shoxi ikkinchi kod bo'ladi | ⛔ **Bo'lmaydi**: reduced-motion — bu **hech nima qilmaslik**. Server kadri **o'zi** javob (`landing-sehri.md`: «xarita to'liq, bitta amber, hisobot ochiq») |
| Gidratatsiyadan keyin sahna «orqaga qaytib» miltillaydi | ⛔ **Sikl 5-fazadan boshlanadi** — ya'ni server chizgan kadrdan. Pauza tugagach **1-fazaga** o'tadi. ⛔ Foydalanuvchi ko'radigan **birinchi** kadr = server kadri. **Rewind YO'Q** |

⛔ Sikl tartibi shuning uchun: **5 → (pauza) → 1 → 2 → 3 → 4 → 5 → …**

**Rad etilgan muqobil** — serverda **bo'sh** xarita chizib JS bilan to'ldirish. ⛔ Rad sababi: JS o'chirilgan yoki sekin kelgan holatda hero **bo'sh to'rt burchak** bo'lardi va reduced-motion uchun **alohida shox** yozilardi.

### 5.3 ⛔⛔ Sketch manbasining IKKI GPU BUZILISHI — tuzatiladi [L-8]

| # | Sketch'da [KOD: `003-landing-hero.html`] | ⛔ Landing'da |
|---|------------------------------------------|---------------|
| 1 | `:66` `@keyframes sweepgo { 0%{left:0} 100%{left:100%} }` | ⛔ `@keyframes sweep { from{transform:translateX(0)} to{transform:translateX(100cqw)} }`; xarita konteyneri `container-type: inline-size` |
| 2 | `:89` `.prog { height:0; transition: height 900ms }` | ⛔ `transform: scaleY(var(--step-fill))` + `transform-origin: top`, `transition: transform 900ms var(--ease-out)` (§10.2) |

⛔ **Nega bu «pedantlik» emas:** `left` va `height` — `motion-tokens.test.mjs:101` dagi `BANNED_KEYFRAME_PROPS` ro'yxatida **nomma-nom**. Har kadrda layout hisobi qo'zg'aladi va **arzon Androidda 60fps imkonsiz** bo'ladi — bu esa aynan ROADMAP SC#5 ning byudjeti.

⚠ **`100cqw` ning tetigi:** konteyner-so'rov birliklari (Chrome 105+/Safari 16+/Firefox 110+) tanlandi, chunki masofa **sof CSS** dan keladi — JS geometriya o'qimaydi va reduced-motion shoxi qo'shimcha kod talab qilmaydi. ⛔ **Tetigi:** maqsad qurilmalarda qo'llab-quvvatlash muammosi **o'lchansa** — sahna mount'da `--sweep-distance` ni **bir marta** yozadi (`offsetWidth`), `@keyframes` esa `translateX(var(--sweep-distance, 100cqw))` bo'lib **o'zgarmaydi**.

⛔⛔ **`transition` xossalari ham qo'riqlanadi:** `motion-tokens.test.mjs` ning G-motion-3(a) si faqat `@keyframes` bloklarini parse qiladi — ya'ni sketch'ning `transition: height` i **bugun jimgina o'tib ketardi**. **G-land-3** aynan shu bo'shliqni yopadi (§16.4).

### 5.4 `@keyframes` reyestri — 8 dan 9 ga [L-9, L-10]

| Nom | Holat | Landing'da |
|-----|-------|------------|
| `enter` (`.motion-enter`) | ⛔ **MAVJUD** | Hero kirish ketma-ketligi (`--i`: brand → h1 → lid → CTA → ⭐ → ishonch) **va** scroll-reveal |
| `attention` (`.motion-attention`) | ⛔ **MAVJUD** | Amber rasta diqqat-halqasi — ⛔ **BIR marta**, `--motion-slow` |
| ⛔ `sweep` (`.landing-sweep`) | ⛔ **YANGI — yagona** | Kamera nuri, **2s linear**, `transform` |
| `draw`, `ringpulse`, `landin`, `shimmer`, `breath`, `shake` | ⛔ **MAVJUD** | ⛔ Landing **ishlatmaydi** — reyestrda qoladi |

⛔ **`animation-delay` orqali stagger — mavjud `--i` mexanizmi** [KOD: `globals.css:306` `animation-delay: calc(var(--i, 0) * 60ms)`]. ⛔ Rasta kataklari **70ms** qadam bilan chiziladi (sketch 003-B) — bu `--i` ning **60ms** idan farq qiladi, shuning uchun katak stagger'i `@keyframes` bilan emas, ⛔ **`transition-delay`** bilan beriladi (`transition`, `animation` emas — katak holati **qaytariladigan**).

### 5.5 12s siklning ijro shartnomasi [K-1]

| Faza | Oyna | Yorliq (`landing.scene.phase*`) | DOM o'zgarishi | Texnika |
|------|------|--------------------------------|----------------|---------|
| **1** | 0–2,6s | «Bozor xaritasi chizilmoqda…» | 30 katak `.on` — **70ms** qadam | `opacity 0→1` + `scale(.85→1)`, `--motion-base`, `--ease-out` |
| **2** | 2,6–5,3s | «Kamera tekshiryapti…» | `.landing-sweep` **2s** o'tadi; kataklar **ustunma-ustun** `.paid` — **280ms** qadam; ⛔ **№16 tegilmaydi** | `sweep` + `background`/`border-color` `transition` |
| **3** | 5,3–8,3s | «Nomuvofiqlik topildi» | ⛔ №16 `.unpaid` + `.motion-attention` (**bir marta**); amber yorliq chiqadi; tushum **2 298 000** gacha sanaydi (**900ms**) | `.motion-attention` + `useCountUp` |
| **4** | 8,3–10,0s | «Kassir to'lovni qayd etdi» | Yorliq **yashilga** aylanadi («To'landi — 8 000 so'm»); №16 `.paid`; tushum **2 306 000** (**600ms**) | `transition` + `useCountUp` |
| **5** | 10,0–13,5s | «Kunlik hisobot» | Yorliq ketadi; hisobot kartasi **pastdan** ko'tariladi (`translateY(12px)`+fade, `--motion-slow`); ⛔ **~1,5s pauza** | `transition` |
| **→1** | 13,5s | — | Reset va sikl qaytadi | Taymer reyestri tozalanadi |

⛔ **Yorliq (`stage-head`) HAR fazada o'zgaradi** — bu sahnaning **matnli hikoyasi** va u har tilda almashadi (video bo'lganda **imkonsiz** bo'lardi).

⛔ **Taymerlar REYESTRDA:** har `setTimeout` id'si massivga yoziladi va reset/unmount'da **hammasi** `clearTimeout` qilinadi. ⛔ Sizib qolgan taymer sahifani tark etgandan keyin ham ishlab, arzon telefonda batareyani yeydi (**G-land-2(d)**).

### 5.6 ⛔⛔ Sikl QACHON o'ynaydi — «avtomatik harakat» qoidasi bilan yarashuv

09-UI-SPEC §4.4 qoida 4 so'zma-so'z: *«HECH QACHON: cheksiz pulsatsiya · **foydalanuvchi boshlamagan avtomatik harakat**»*. ⛔ Hero sikli — aynan shunday harakat. Ziddiyat **yashirilmaydi, hal qilinadi**:

| Savol | Javob |
|-------|-------|
| Qoida nega app'da bor | App — **asbob**: foydalanuvchi vazifa bajaradi, so'ralmagan harakat **shovqin** |
| Landing nega boshqacha | Landing — **hikoya**: harakat **kontentning o'zi** [K-1, foydalanuvchi tasdiqlagan] |
| Qoidaning ruhi qanday saqlanadi | ⛔ **To'rt mexanizm bilan** (quyida) — niyat bilan emas |

| # | Mexanizm | Shakli |
|---|----------|--------|
| 1 | ⛔ `prefers-reduced-motion` | Sikl **umuman boshlanmaydi** — server kadri qoladi (§5.2) |
| 2 | ⛔ Ko'rinmaganda **to'xtaydi** | `IntersectionObserver`: hero ekrandan chiqsa taymerlar tozalanadi; qaytsa **davom etadi** |
| 3 | ⛔ Yorug'lik yo'q ekranda **to'xtaydi** | `document.visibilitychange` — fon tabda sikl **ishlamaydi** |
| 4 | ⛔ Sahifada **AYNAN BITTA** harakatlanuvchi sahna | Rol-kartalarida, FAQ'da, footer'da **hech qanday** avtomatik harakat yo'q (**G-land-3(c)**) |

⛔ **Sun'iy sikl chegarasi («3 martadan keyin to'xtasin») RAD ETILADI:** u foydalanuvchi hikoyaga **qaytganda** heroni muzlagan holatda qoldirardi. Ko'rinuvchanlik chegarasi (2) **aniqroq** signal — u foydalanuvchi **qarayotganini** o'lchaydi, taxmin qilmaydi.

### 5.7 ⛔ Halollik — sahnadagi har son «namunaviy» [K-7]

| Element | Sketch'da | ⛔ Landing'da | Sabab |
|---------|-----------|---------------|-------|
| Sahna sarlavhasi | «**Karmana bozori · jonli**» | ⛔ «**Namuna bozori · demonstratsiya**» | ⛔ **Bu K-7 ning ayni sinfi**: «jonli» **yolg'on da'vo** (jonli oqim yo'q), real bozor nomi esa **real feed** ni anglatardi |
| Ko'rinadigan belgi | yo'q | ⛔ **Majburiy**: sahna yuqorisida `landing.scene.sampleBadge` = «Namunaviy ma'lumot» — ⛔ **hamma fazada ko'rinadi**, hover'da emas | Brief §7.5 «Halollik» qatori |
| Raqamlar (2 306 000, 215, 214, 8 000, D-11) | «jonli» kontekstda | ⛔ **Namunaviy belgi ostida** | K-7 |
| Pilot raqamlari (§13.6) | — | ⛔ **UMUMAN YOZILMAYDI** — faqat holat: «Karmana bozorida sinovda» | K-7 |

⛔⛔ **G-land-4 buni MEXANIK qiladi:** sahna komponentida `landing.scene.sampleBadge` chaqirig'i **bo'lishi shart** va u shartli render ichida **bo'lmasligi** shart.

### 5.8 Mobil soddalashuvi [MEROS: brief §7.4]

| Xossa | ≥840px | ⛔ <840px |
|-------|--------|-----------|
| Layout | 2 ustun (matn / sahna) | 1 ustun — ⛔ matn **birinchi**, sahna **ostida** |
| Xarita | 6×5 = **30** katak | ⛔ **5×4 = 20** katak — katak o'lchami saqlanadi, ish hajmi **33% kamayadi** |
| Amber rasta indeksi | **16** | ⛔ **11** (o'rtaga yaqin, yorliq ekranga sig'adi) |
| Sikl timinglari | ⛔ **O'zgarmaydi** | ⛔ **O'zgarmaydi** — hikoya bir xil tezlikda aytiladi |
| Yorliq joylashuvi | Rastaning yonida | ⛔ Xarita **ostida**, markazda — o'lchov `getBoundingClientRect` **talab qilmaydi** |

⛔ **`@media` shoxi CSS'da, JS'da EMAS** — katak soni `grid-template-columns` va `nth-child` bilan boshqariladi; JS **bir xil** DOM'ni chizadi. ⛔ Aks holda `window.innerWidth` o'qish SSG kadrini **klientda boshqacha** qilardi (gidratatsiya nomuvofiqligi).

---

## 6. Rang — yangi token YO'Q

### 6.1 60/30/10 — o'zgarmaydi [MEROS: 09-UI-SPEC §5.1]

| Rol | Token | Landing'da qayerda |
|-----|-------|--------------------|
| Dominant (60%) | `--color-bg` (iliq `oklch(0.985 0.001 106)`) | Sahifa foni, seksiyalarning ko'pchiligi |
| Ikkilamchi (30%) | `--color-surface` + `--color-surface-muted` | Sahna kartasi, og'riq kartalari, FAQ, forma kartasi, footer |
| Aksent (10%) | `--color-accent` | §6.3 reyestri |
| Destruktiv | `--color-danger` | ⛔ **Faqat forma xato holati** (§12.4) — landing'da destruktiv **amal yo'q** |

### 6.2 ⛔ Yangi rang tokeni — **0** [QAROR]

Landing sahnasining **hamma** rangi mavjud tokenlardan keladi: rasta bo'sh — `surface-muted` + `border`; band+to'langan — `success/25` + `border-success`; band+to'lovsiz — `warning/30` + `border-warning`; kamera nuri — `accent` gradienti; yorliq matni — `warning-text` / `success-text`; hisobot — `surface` + `border` + `shadow-raised`.

⛔ **O'lchandi [L-13]: uchala temada AA dan o'tadi.** Ya'ni `contrast.test.mjs` ning `PAIR_REGISTRY` si **kengaytirilmaydi** va G-motion-5 **tegilmaydi**.

### 6.3 Aksent byudjeti — landing reyestri

⛔ Aksent **to'yingan fon** sifatida landing'da **aynan uch** joyda:

| # | Joy | Izoh |
|---|-----|------|
| 1 | Hero birlamchi CTA «Demo so'rang» | `Button variant="default" size="hero"` |
| 2 | Yakuniy CTA seksiyasidagi forma tugmasi | ⛔ **Ayni tugma** — sahifada **yagona** CTA [K-2] |
| 3 | 3-qadam chizig'ining to'lgan qismi + faol qadam nuqtasi | `.landing-step-fill` |

Bulardan tashqari aksent: **brand yorlig'i** (`SBOZOR`, `text-accent`, **4.52:1** [L-13]) · **fokus halqasi** (meros) · **faol til tugmasi** (`LocaleSwitcher`, meros) · **havolalar** (`text-accent-text`). ⛔ Yangi aksentli **yuza** qo'shilmaydi.

⛔ **CTA hover soyasi TOKENDAN:** sketch `:32` da `box-shadow: 0 6px 20px oklch(0.56 0.19 255 / 0.3)` — ⛔ **qattiq yozilgan aksent qiymati**. Dark temada `--color-accent` `oklch(0.64 0.15 255)` ga o'tadi va soya **eskirib qolardi**. ⛔ To'g'ri shakl: `color-mix(in oklch, var(--color-accent) 30%, transparent)`.

### 6.4 ⛔⛔ Tema — landing QULFLAMAYDI, MEROS OLADI [QAROR]

Topshiriq savol qo'ydi: landing app temalarini majburan olmaydi — tavsiya «faqat iliq». ⛔ **O'lchov teskari javob berdi va sabab yoziladi.**

| Savol | Javob |
|-------|-------|
| Anonim tashrifchi qaysi temani ko'radi | ⛔ **Iliq (`light`)** — `localStorage` **bo'sh**, FOUC skripti [KOD: `layout.tsx:96-98`] hech nima qo'ymaydi, `<html data-theme="light">` server qiymati qoladi. ⛔ **Maqsadli auditoriyaning 100% i** aynan shu holatda |
| Ilovadan kelgan `dark` foydalanuvchi nima ko'radi | ⛔ **Qorong'i landing** — va u **buzuq emas**: [L-13] landing juftliklari dark'da **5,66–7,67:1** |
| «Faqat iliq» ni majburlash nimani talab qilardi | ⛔ **Yangi `[data-theme="light"]` scope bloki** butun token to'plami bilan — chunki bugun light qiymatlar `@theme` (`:root`) da yashaydi va ichki `data-theme="light"` element **hech nimani qaytarmaydi**. ⛔ Bu `theme-tokens.test.mjs` ning `SCOPED_THEMES = ["dark","sun"]` reyestrini va `contrast.test.mjs` ning uch temali halqasini **ikkalasini ham** ochardi |
| Xulosa | ⛔ **Landing temani meros oladi.** Mexanizm **nol**, natija **ayni**, darvoza **tegilmaydi** |

⛔ **LEKIN tema ALMASHTIRGICHI landing'da KO'RSATILMAYDI** [QAROR]: (a) tema — **ish qurolining** sozlamasi (06:00 smena, quyosh ostidagi kassir), marketing yuzasining emas; (b) uchinchi boshqaruv elementi «yagona CTA» intizomini suyultirardi; (c) anonim tashrifchi uchun u **ma'nosiz** — u hali hech narsani sozlamagan. ⛔ Til almashtirgich esa **KO'RSATILADI** va bu ziddiyat emas: kirill — **davlat auditoriyasining** o'qish sharti [MEROS: brief §4].

---

## 7. Tipografiya — bitta yangi token, sanoqli sabab bilan

### 7.1 Rollar jadvali

| Rol | O'lcham | Og'irlik | Satr balandligi | Utilita | Landing'da qayerda |
|-----|---------|----------|-----------------|---------|--------------------|
| ⛔ **Hero** (**YANGI**) | ⛔ `clamp(28px, 4.4vw, 44px)` | 600 | **1.15** | ⛔ `text-hero` | ⛔ **AYNAN 1 joy**: `marketing/hero.tsx` ning `h1` i |
| Display-XL | 40px | 600 | 1.1 | `text-display` | ⛔ **ISHLATILMAYDI** [L-4] |
| Heading | 24px | 600 | 1.2 | `text-2xl` | Seksiya sarlavhalari (6 ta), forma sarlavhasi |
| Subheading | 18px | 600/400 | 1.3 | `text-lg` | Hero lidi, qadam sarlavhalari, karta sarlavhalari, FAQ savoli, CTA matni |
| Body | 14px | 400 | 1.5 (proza'da **1.65**) | `text-sm` | Barcha proza, FAQ javoblari, forma yorliqlari |
| Caption | 12px | 400 | 1.4 | `text-xs` | Ishonch qatori, namunaviy belgi, footer, forma yordami |

⛔ **Og'irliklar — 2 ta** (400, 600). ⛔ `font-medium` **yozilmaydi** — chegara to'lgan [L-3].

#### 7.1.1 ⛔ Checker uchun izoh — nega bu 5 rolli shkala EMAS

E'lon **beshta o'lchamli** ko'rinadi. ⛔ **Sahifaning MATN shkalasi esa — 4 rol**, va farq mexanik:

| # | Da'vo | Mexanik shakli |
|---|-------|----------------|
| **1** | ⛔ **Kontent ierarxiyasi 4 rolda qoladi**: 24 (`text-2xl`) / 18 (`text-lg`) / 14 (`text-sm`) / 12 (`text-xs`) | ⛔ Sahifa bo'ylab **takrorlanadigan** har bir matn — seksiya sarlavhalari, qadam va karta sarlavhalari, butun proza, ishonch qatori, FAQ, forma — shu **to'rtlikda**. Beshinchi o'lcham **ierarxiyaning bir bo'g'ini emas** |
| **2** | ⛔ **`--text-hero` — bir martalik DISPLAY registri, shkala a'zosi emas** | ⛔ **Aynan 1 fayl** (`components/marketing/hero.tsx`), ⛔ **aynan 1 element** (`h1`), ⛔ sahifada **takrorlanmaydi**, ⛔ boshqa **birorta** sarlavha uni olmaydi. Bu `text-display` ning «faqat pul» cheklovi bilan **bir sinf**: displey registri ≠ matn shkalasi |
| **3** | ⛔⛔ **HALOLLIK BANDI** | ⛔ Ha — `h1` **ierarxiyaning boshida** turadi, ya'ni bu `text-display` ning («pul roli», matn ierarxiyasidan **butunlay tashqarida») pozitsiyasidan **kuchsizroq**. ⛔ Argument shuning uchun **ritorikaga emas, mexanikaga** tayanadi: **G-land-5(a)** `text-hero` ni **1 fayl / 1 uchrashuvga** `deepEqual` bilan qulflaydi va **ikkinchi** ishlatish sinovda **qizaradi**. Chegaraning maqsadi — **o'lcham xaosi** — shu bilan ta'minlangan; o'lchamning o'zi esa foydalanuvchi tasdiqlagan qaror (sketch 003-B, `clamp(28→44px)`) va u **qayta ochilmaydi** [K-1] |
| **4** | ⛔ **Kengayish yo'li yopiq** | ⛔ Yangi hero-o'lchamli sarlavha qo'shish uchun **darvoza reyestrini** o'zgartirish kerak — ya'ni u **ko'rinadigan, sababi yozilgan** qaror bo'ladi, jimgina siljish **emas** |

⛔ **Xulosa:** **4 matn roli** + **1 mexanik qulflangan hero-display registri**. ⛔ Shkala tarqalishi darvoza darajasida **imkonsiz**.

### 7.2 ⛔⛔ Nega `text-display` emas, nega `text-[clamp(...)]` emas

| Muqobil | Nega rad etildi |
|---------|------------------|
| `text-display` (40px) ni ishlatish | ⛔ **Mexanik imkonsiz** [L-4]: `typography.test.mjs` ning `TEXT_DISPLAY_FILES` reyestri `deepEqual` bilan **ikki app fayliga** qulflangan. Uchinchi fayl — **darvoza qizil**. ⛔ Va bu **to'g'ri qulf**: `text-display` — **pul roli** (§7.1, L-9), sarlavha roli emas |
| `text-[clamp(28px,4.4vw,44px)]` | ⛔ **Mexanik imkonsiz** [L-3]: `text-[` — **qattiq nol** (`ARBITRARY_TEXT_TOKEN`) |
| `text-4xl` (36px) | ⛔ Tailwind standarti, **token emas** — shkala e'loni tashqarisiga chiqadi va `text-3xl = 0` qoidasining ruhini buzadi; suyuq emas, telefonda **kesiladi** |
| `text-2xl` (24px) bilan cheklanish | ⛔ Hero sarlavhasi seksiya sarlavhasi bilan **teng** bo'lardi — ierarxiya **yassilanadi** va «mahsulot gapiryapti» hissi yo'qoladi |

⛔ **Tanlov — `--text-hero`**, chunki u: (a) **token** (mavjud `--text-display` naqshi), (b) **suyuq** — telefondan proyektorgacha bitta qiymat, (c) **bitta faylga** qulflanadi (**G-land-5**), (d) ilovaga **0 ta'sir** qiladi.

```css
@theme {
  /* ---- Landing hero sarlavhasi — AYNAN 1 faylda (G-land-5) ------------
   * Suyuq: telefonda 28px, hokimlik proyektorida 44px. `text-display`
   * (40px) ISHLATILMAYDI — u pul roli va reyestri ikki app fayliga
   * qulflangan (typography.test.mjs TEXT_DISPLAY_FILES). */
  --text-hero: clamp(1.75rem, 4.4vw, 2.75rem);
  --text-hero--line-height: 1.15;
  --text-hero--letter-spacing: -0.02em;
}
```

### 7.3 Proza o'qilishi — o'lchamdan emas, joylashuvdan

⛔ Landing prozasi **14px** (`text-sm`) — ilovadagi bilan **ayni**, chunki `text-base` chegarasi to'lgan [L-2] va uni ko'tarish repozitoriya bo'ylab leshni kesardi (§0.2). O'qilish **uch mexanizm** bilan ta'minlanadi:

| # | Mexanizm | Qiymat |
|---|----------|--------|
| 1 | ⛔ Proza ustuni **tor** | `max-w-[66ch]` — ⛔ **`text-[` emas**, `max-w-*` ixtiyoriy qiymati darvoza tashqarisida; ⚠ agar reja uni ham tokenlashtirmoqchi bo'lsa — `--container-prose` |
| 2 | ⛔ Satr oralig'i **kengroq** | `leading-relaxed` (1.625) — ilovadagi 1.5 dan **ko'proq**; chegarasiz utilita |
| 3 | ⛔ Bloklar orasida **havo** | §8.2 seksiya ritmi (64/96px) |

### 7.4 ⛔ `Button` ning beshinchi o'lchami — `hero` [L-17, L-18]

| O'lcham | Sinflar | Ishlatiladigan joy |
|---------|---------|--------------------|
| `sm` / `md` / `lg` | ⛔ **Tegilmaydi** | App (meros) |
| ⛔ **`hero`** (YANGI) | `min-h-14 px-8 text-lg` | ⛔ **Landing birlamchi CTA — 2 joy** (hero, yakuniy forma) |

⛔ **56px balandlik — MAVJUD bo'shliq istisnosi** [MEROS: 09-UI-SPEC §6 «56px mobil panel/tasdiq tugmasi»], yangi istisno **emas**. ⛔ `text-lg` (18px) — **chegarasiz** rol [L-3]. ⛔ `Button` variant reyestri darvoza bilan qulflanmagan [L-18], ya'ni qo'shish **hech nimani buzmaydi**.

⛔ **Ikkilamchi CTA «Tizimga kirish»** — `Button variant="secondary" size="lg"`, ⛔ **`hero` emas**: ikki teng og'irlikdagi tugma «yagona CTA» qoidasini [K-2] buzardi.

---

## 8. Bo'shliq

### 8.1 Panjara — meros [MEROS: 09-UI-SPEC §6]

4-panjara: **4 · 8 · 12 · 16 · 24 · 32 · 48**. Istisnolar: **44px** barmoq nishoni · **56px** mobil panel/CTA · **20px** karta ichki `x`.

### 8.2 ⛔ Seksiya ritmi — ikkita YANGI qiymat, nomlangan [QAROR]

| Qiymat | Utilita | ⛔ Ishlatiladigan YAGONA joy |
|--------|---------|------------------------------|
| **64px** | `py-16` | ⛔ `<section>` vertikal ichki bo'shlig'i — **mobil** (<840px) |
| **96px** | `py-24` | ⛔ `<section>` vertikal ichki bo'shlig'i — **desktop** (≥840px) |

⛔ **Nega kengaytma kerak:** 48px — **admin ro'yxatining** ritmi. Marketing sahifasida u bloklarni **bir-biriga yopishtiradi** va hikoyaning «nafas»ini o'ldiradi. ⛔ **Nega xavfsiz:** ikkala qiymat ham **4 ning karrasi** va **16 ning karrasi**; ikkalasi ham **aynan bitta rolda** (`marketing/section.tsx` ning tashqi `padding` i) — ⛔ boshqa hech qayerda yozilmaydi (**G-land-5(c)**).

⛔ **Uchinchi qiymat (80px, 128px) YO'Q.** Ikkitasi butun sahifani qopladi.

⛔⛔ **96px — ONGLI MAKRO-RITM KENGAYTMASI, tasodifiy istisno EMAS.** U **4 ning** (24×4) va **16 ning** (6×16) karrasi, ya'ni panjaraning **arifmetikasidan chiqmaydi**; ⛔ **yagona rol** (`<section>` vertikal ichki bo'shlig'i) va ⛔ **yagona fayl** (`components/marketing/section.tsx`) bilan cheklangan; ⛔ **G-land-5(c)** uni shu faylga `deepEqual` bilan qulflaydi va ikkinchi joyda ishlatilishi sinovda **qizaradi**. ⛔ **Reference to'plamiga (4·8·12·16·24·32·48) ATAYLAB kiritilmaydi**: o'sha to'plam — **komponent ichi** bo'shlig'ining lug'ati va u butun ilovaga tegishli; 64/96 esa **marketing seksiyalari orasidagi makro-ritm** va u ilovada **umuman ishlatilmaydi**. ⛔ Ikkovini bitta ro'yxatga qo'shish `p-24` ni har qanday admin kartasida **qonuniylashtirardi** — aynan shu sababdan u alohida, nomlangan va darvoza bilan bog'langan qatlamda qoladi.

---

## 9. Sahifa strukturasi — 9 blok [MEROS: brief §2]

### 9.1 Bloklar

| # | Blok | Fon | Kontent | Harakat |
|---|------|-----|---------|---------|
| **0** | ⛔ **Header** (sticky emas) | `bg` | `SBOZOR` brand · `LocaleSwitcher` · «Tizimga kirish» havolasi | ⛔ **Yo'q** |
| **1** | **Hero** | `bg` | §5 | ⛔ **12s sikl** |
| **2** | **Og'riq — 3 karta** | `surface-muted` | Daftar-hisob adashadi · Kim to'lamaganini bilib bo'lmaydi · Nazoratchi hammasini ko'rolmaydi | Scroll-reveal (stagger 60ms) |
| **3** | ⛔ **Qanday ishlaydi — 3 qadam** [K-3] | `bg` | §10 | Chiziq to'lishi + qadam reveal |
| **4** | ⭐ **Bosh dalil** | `surface` (karta) | «Yangi uskuna shart emas — mavjud NVR kameralaringiz bilan ishlaydi. Ulanish — login-parol kiritish, xolos.» | Scroll-reveal |
| **5** | **Rol-kartalar — 3 ta** | `surface-muted` | Direktor · Kassir · Nazoratchi (§9.3) | Scroll-reveal (stagger) |
| **6** | **Ishonch bloki (davlat)** | `bg` | §11 — 4 band | Scroll-reveal |
| **7** | **Pilot holati** | `surface-muted` | ⛔ «Karmana bozorida sinovda» — **raqamsiz** [K-7] | Scroll-reveal |
| **8** | **FAQ — 5 savol** | `bg` | §13.7 | Scroll-reveal; ⛔ **native `<details>`** (JS'siz ishlaydi) |
| **9** | ⛔ **CTA takrori + demo-forma** | `surface` (karta) | §12 | Scroll-reveal |
| **10** | **Footer** | `surface-muted` | Maxfiylik siyosati · aloqa · © | ⛔ **Yo'q** |

⛔ **Boshqa blok YO'Q** [MEROS: brief §1]: narx kalkulyatori, ro'yxatdan o'tish, blog, mijozlar logotiplari, «biz haqimizda» — ⛔ **hech biri**.

### 9.2 Header — mavjud komponentlardan

| Element | Manba |
|---------|-------|
| `SBOZOR` brand | `common.appName` matni + `text-accent` + `font-semibold` — ⛔ yangi komponent yo'q |
| Til almashtirgich | ⛔ **`shell/locale-switcher.tsx`** [L-15, L-16] — ⛔ **tegilmaydi** |
| «Tizimga kirish» | `Link` (`@/i18n/navigation`) + `Button variant="ghost" size="md"` |
| Tema tugmasi | ⛔ **YO'Q** (§6.4) |

### 9.3 ⛔ Rol-kartalar — skrinshotsiz [QAROR, brief §2.5 dan CHEKINISH]

Brief §2.5 va §3 «har birida app'dan **real skrinshot**» deydi. ⛔ **Bu fazada skrinshot QO'YILMAYDI va sabab uchta, har biri o'lchanadigan:**

| # | Sabab |
|---|-------|
| 1 | ⛔ **Shaxsiy ma'lumot.** App ekranlarida sotuvchi F.I.Sh. va telefoni bor. Ommaviy sahifaga qo'yish — ⛔ **K-8 bilan bir sinfdagi** huquqiy xavf. Tozalash **tekshiruv ro'yxatini** talab qiladi, u esa hali yozilmagan |
| 2 | ⛔ **Uch til.** Skrinshotdagi matn **rasmga qotgan** — 3 rol × 3 til = **9 rasm**, va ular app har o'zgarganda **eskiradi**. Kirill auditoriyasi lotin skrinshotini ko'rardi |
| 3 | ⛔ **Byudjet.** 9 ta ekran rasmi Lighthouse ≥95 va LCP <1.5s byudjetiga **o'lchanadigan** yuk |

⛔ **Bu fazada rol-kartasi:** ikonka (`lucide-react`, meros) + sarlavha (`text-lg`) + 2 jumlali tavsif (`text-sm`) + ⛔ **bitta aniq, tekshiriladigan da'vo** (`text-xs`, `text-accent-text`): Direktor — «Kunlik hisobot + xlsx» · Kassir — «≤3 bosishda to'lov» · Nazoratchi — «Rasm-dalil bilan tasdiqlash».

⛔ **Soxta mockup ham QO'YILMAYDI** — brief §3 ning taqig'i kuchda. ⛔ Vizual isbot yukini **hero sahnasi** ko'taradi va u **haqiqiy komponent shakllaridan** qurilgan. **Tetigi:** pilot go-live'dan keyin — shaxsiy-ma'lumot tozalash ro'yxati + locale bo'yicha rasm to'plami **alohida** topshiriq sifatida (§17.1).

---

## 10. 3-qadam seksiyasi [K-3]

### 10.1 Kompozitsiya

```
Qanday ishlaydi — 3 qadam          (text-2xl)
 │
 ●  1 · Mavjud kameralar kadr oladi        (text-lg, 600)
 │     Yangi uskuna shart emas: NVR'ingiz…  (text-sm, ≤66ch)
 │
 ●  2 · AI band rastani aniqlaydi
 │     Har kadr zonalar bo'yicha…
 │
 ●  3 · «Band, lekin to'lovsiz» fosh bo'ladi
       Kun oxirida hisobot: qaysi rasta…
```

| Element | Holat | Texnika |
|---------|-------|---------|
| Chiziq (fon) | Doim | `border` rangida 2px, `position:absolute` |
| ⛔ Chiziq (to'lgan) | 0 → 1/3 → 2/3 → 1 | ⛔ `transform: scaleY()` + `transform-origin: top`, `transition: transform 900ms var(--ease-out)` — ⛔ **`height` EMAS** [L-8] |
| Qadam nuqtasi | `border-ui` → `accent` | `background`/`border-color` `transition`, `--motion-base` |
| Qadam matni | Yashirin → ko'rinadi | `.motion-enter` (`translateY(8px)`+fade) |
| Tetik | — | ⛔ `IntersectionObserver` (`threshold: 0.4`), qadam **ko'ringanda** |

### 10.2 ⛔ To'lish darajasi — `data-step` atributi orqali [QAROR]

```css
.landing-step-fill { transform: scaleY(0); transform-origin: top;
  transition: transform 900ms var(--ease-out); }
[data-step="1"] .landing-step-fill { transform: scaleY(0.3333); }
[data-step="2"] .landing-step-fill { transform: scaleY(0.6667); }
[data-step="3"] .landing-step-fill { transform: scaleY(1); }
```

⛔ **Nega inline `style` emas:** deklarativ atribut CSS'ni **`globals.css` da bitta joyda** qoldiradi va komponent faylida geometriya **umuman yozilmaydi** — G-motion-3(c) ning ruhi. ⛔ **900ms — kompozit qiymat** va u `globals.css` ichida yashaydi, komponentda takrorlanmaydi [MEROS: 09-UI-SPEC §4.3].

⛔ **Reduced-motion:** global blok [KOD: `globals.css:184-193`] `transition-duration` ni **0.01ms** ga tushiradi — chiziq **darhol** to'lgan holatda chiziladi, qadamlar **darhol** ko'rinadi. ⛔ Qo'shimcha shox **yozilmaydi**.

---

## 11. Ishonch qatlami [Y-3]

### 11.1 Davlat bloki — 4 band [MEROS: ROADMAP SC#4]

| # | Sarlavha | Tavsif manbasi |
|---|----------|----------------|
| 1 | **Ma'lumotlar O'zbekistonda** | ⚠ **Ehtiyot shart:** bugungi holat — Contabo VPS, ko'chish **rejalashtirilgan** [MEROS: CLAUDE.md «Data-rezidentlik»]. ⛔ Copy **kelasi zamon** bilan yozilmaydi va **bugungi holatni** aytadi (§13.5) |
| 2 | **NVR faqat VPN orqali** | ⛔ **Rost va o'lchangan** [MEROS: CLAUDE.md; 3-faza] — NVR internetga ochilmaydi, RTSP parollari shifrlangan |
| 3 | **Har amal audit jurnalida** | ⛔ **Rost** [MEROS: 1-faza `audit_log`] |
| 4 | **3 til** | ⛔ **Rost va sahifaning O'ZIDA isbotlanadi** — til almashtirgich header'da |

### 11.2 ⛔⛔ Rezidentlik bandining halolligi — bu fazaning huquqiy tuguni

> ⛔ **«Ma'lumotlar O'zbekistonda» — bugun TO'LIQ ROST EMAS.** Server Contabo'da; O'zbekiston hostingiga ko'chish **davlat bosqichidan oldin** rejalashtirilgan [MEROS: CLAUDE.md]. Landing'da uni **shartsiz da'vo** sifatida yozish — brief §7.5 «Halollik» qatorida raqibni ayblagan narsaning **ayni o'zi** («ishlab chiqilmoqda» deb yozib do'kon badge'larini qo'yish).

⛔ **[QAROR] Copy shakli — bugungi mexanizmni aytadi, kelajakni va'da qilmaydi:**

| ⛔ YOZILMAYDI | ⛔ YOZILADI |
|---------------|-------------|
| «Ma'lumotlaringiz O'zbekistonda saqlanadi» | «Ma'lumotlar **O'zR qonunchiligiga muvofiq** boshqariladi; **kamera tasvirlari** bozor tarmog'idan tashqariga faqat shifrlangan tunnel orqali chiqadi. **Joylashuv talabi bo'lsa — hosting O'zbekistonga ko'chiriladi** va bu shartnomada qayd etiladi.» |

⛔ **Ishonch qatorining (hero) qisqa shakli** «Ma'lumotlar O'zbekistonda» ⛔ **QULFLANGAN COPY** [K-2] va u **o'zgartirilmaydi** — lekin §11 bloki uning **to'liq va halol** izohini beradi va hero yorlig'i shu blokga **havola** qiladi (**G-land-4(c)**).

⚠ **EGASI VA TETIGI:** bu bandning yakuniy shakli — ⛔ **mahalliy yurist tasdig'i** [MEROS: STATE.md «Huquqiy ko'rik»]. ⛔ **Tetigi: go-live.** Rejaga `10-HUMAN-UAT.md` bandi sifatida kiradi.

### 11.3 Maxfiylik siyosati sahifasi [K-8]

⛔ **Majburiy sahifa** (`/{locale}/maxfiylik`), uchala tilda, SSG. ⛔ Bo'limlar reyestri:

| # | Bo'lim | Nima yoziladi |
|---|--------|---------------|
| 1 | Kim ma'lumot yig'adi | Operator nomi, aloqa |
| 2 | ⛔ **Kamera tasvirlari** | Nima olinadi (rasta zonasi kadri), nima uchun, **qancha saqlanadi** (90 kun → siqilgan holda 1 yil [MEROS: CLAUDE.md]) |
| 3 | ⛔ **Demo-forma ma'lumotlari** | Ism, telefon, bozor nomi — ⛔ **DB'da saqlanmaydi**, admin Telegram kanaliga yetkaziladi va **o'chiriladi** (§12.5) |
| 4 | Sotuvchi ma'lumotlari | F.I.Sh., telefon — bozor ma'muriyati kiritadi; landing bunga **tegmaydi** |
| 5 | Kimga uzatiladi | ⛔ **Uchinchi tomonga uzatilmaydi**; analitika skripti **yo'q** (§17.2) |
| 6 | Huquqlar | Ma'lumotni o'chirish/tuzatish so'rovi — aloqa kanali |
| 7 | Cookie | ⛔ **Landing'da marketing cookie'si YO'Q**; `sbozor-theme` — `localStorage`, faqat qurilmada |

⛔ **Cookie-banner QO'YILMAYDI** [QAROR] — chunki landing marketing/analitika cookie'si **o'rnatmaydi**. ⛔ Banner qo'yish yolg'on taassurot berardi («bizda kuzatuv bor»), va u LCP yo'liga **overlay** qo'shardi. **Tetigi:** analitika qo'shilsa (§17.2 da rad etilgan) — banner **o'sha kunda** majburiy bo'ladi.

### 11.4 Pilot bloki [K-7]

| Element | Qiymat |
|---------|--------|
| Sarlavha | `landing.pilot.title` |
| ⛔ Holat rozetkasi | `Badge tone="warning"` — «Karmana bozorida sinovda» |
| Matn | ⛔ **Raqamsiz**: nima sinalayotgani, qachon natija bo'lishi |
| ⛔ Raqamlar | ⛔ **NOL.** «X% o'sish», «Y so'm topildi» — ⛔ **birortasi ham yozilmaydi** |

---

## 12. Y-2 — Demo-forma [K-5, ROADMAP SC#3]

### 12.1 Maydonlar — YOPIQ reyestr

| # | Maydon | Turi | Majburiy | Validatsiya |
|---|--------|------|----------|-------------|
| 1 | Ismingiz | `Input` | ⛔ **Ha** | ≥2 belgi |
| 2 | Telefon | `Input type="tel"` | ⛔ **Ha** | ⛔ O'zbek raqami: `+998` + 9 raqam (bo'sh joy/qavs qabul qilinadi, normalizatsiya **klientda**) |
| 3 | Bozor nomi | `Input` | ⛔ **Ha** | ≥2 belgi |
| 4 | Rastalar soni (taxminan) | `Input inputMode="numeric"` | ⛔ **Yo'q** | 1–100 000 oralig'i (kiritilsa) |
| 5 | ⛔ Rozilik | `checkbox` | ⛔ **Ha** [K-8] | ⛔ Maxfiylik siyosatiga **havola bilan** |
| 6 | ⛔ **Honeypot** | `input` — ⛔ `aria-hidden`, `tabIndex={-1}`, ekrandan tashqarida | — | ⛔ To'ldirilgan bo'lsa — **jimgina muvaffaqiyat**, so'rov **yuborilmaydi** |

⛔ **Oltinchi ko'rinadigan maydon YO'Q.** Email, lavozim, xabar matni — ⛔ **hech biri**: har qo'shimcha maydon konversiyani tushiradi va telefon **yetarli** (aloqa Telegram/qo'ng'iroq orqali).

### 12.2 Anti-spam — ikki qatlam, ikkalasi ham ko'rinmas

| Qatlam | Mexanizm | Nega captcha emas |
|--------|----------|-------------------|
| 1 | ⛔ **Honeypot** maydoni | — |
| 2 | ⛔ **Minimal turish vaqti**: mount'dan yuborishgacha **≥3s** | — |
| 3 | ⛔ **Server tomonda IP bo'yicha chegara** — §12.5 [TALAB] | — |
| ⛔ | ⛔ **CAPTCHA RAD ETILADI** | (a) **Uchinchi tomon skripti** — Lighthouse ≥95 byudjetini yeydi va K-9 ni buzadi; (b) **maxfiylik** — tashrifchi ma'lumoti uchinchi tomonga ketardi va §11.3 bandi 5 yolg'onga aylanardi; (c) **konversiya** — hokimlik vakili uchun to'siq |

### 12.3 ⛔⛔ G-SUBMIT — landing formasi ham qamrovda [L-19]

[KOD: `scripts/submit-gate.test.mjs:52`] skan yuzasi — `src/**`. ⛔ Qoida so'zma-so'z: *«submit tugmasi FAQAT yuborish jarayoni davomida yopiladi; domen sharti … validatsiya xabari bo'lib EKRANGA chiqadi»*.

| ⛔ TAQIQ | ⛔ TALAB |
|----------|----------|
| `disabled={!isValid}` | Tugma **doim bosiladi**; bo'sh maydon — **ko'rinadigan** validatsiya xabari |
| `disabled={!consent}` | Rozilik belgilanmagan — **xabar**, jim tugma emas |
| `type="button"` + `onClick` bilan qochish | ⛔ **D-2 detektori** bu qochishni ham ushlaydi |
| — | `disabled={isSubmitting}` — ⛔ **yagona ruxsat etilgan shart** |

### 12.4 Uch holat

| Holat | Ko'rinish | Texnika |
|-------|-----------|---------|
| **Idle** | Maydonlar + `Button size="hero"` («Demo so'rang») | — |
| **Yuborilmoqda** | Tugma matni `landing.form.submitting`; ⛔ `disabled` **faqat shu paytda**; ⛔ ichida `Loader2` + `motion-reduce:animate-none` [MEROS: 09-UI-SPEC §12.2] | — |
| ⛔ **Muvaffaqiyat** | ⛔ Forma **almashtiriladi**: yashil ✓ + `landing.form.success.title` + `.body` («24 soat ichida bog'lanamiz») | ⛔ `role="status"` + `aria-live="polite"` |
| ⛔ **Xato** | ⛔ Forma **saqlanadi** (kiritilgan ma'lumot **yo'qolmaydi**) + xato bloki: ⛔ **sabab VA tuzatish yo'li** [MEROS: D-02] | ⛔ `role="alert"`; ⛔ fokus xato blokiga |

⛔ **`sonner` toast ISHLATILMAYDI** [QAROR]: (a) toast **yo'qoladi** — muvaffaqiyat xabari sahifada **qolishi** kerak, chunki foydalanuvchi «yubordimmi?» deb qaytib qaraydi; (b) `Toaster` ildiz layout'dan chiqarilyapti (§4.3), landing uni **qaytarmaydi**; (c) inline natija skrinriderda **kuchliroq**.

⛔ **Muvaffaqiyat animatsiyasi:** `.motion-enter` (mavjud). ⛔ Konfetti — **yo'q** [MEROS: 09-UI-SPEC §9: konfetti **faqat** kunlik plan bajarilganda].

### 12.5 [TALAB] — backend yuzasi [L-25]

> ⛔ **`POST /api/v1/public/demo-requests`** — ⛔ **anonim** (sessiya talab qilmaydi), ⛔ **IP bo'yicha chegaralangan**.
> **Tanasi:** `{ name, phone, market_name, stall_count?, locale }`
> **Javob:** `202 Accepted` + `{ delivered: true }`
> **Xato kodlari:** `rate_limited` · `invalid_phone` · `validation_error` · `delivery_failed`
> ⛔⛔ **SHAXSIY MA'LUMOT DB'GA YOZILMAYDI** [QAROR]: so'rov `bot-service` orqali admin Telegram kanaliga yetkaziladi va **o'chiriladi**. Sabab: (a) CRM **yo'q** [K-5], ya'ni DB yozuvining **iste'molchisi yo'q**; (b) K-8 ostida saqlanmagan ma'lumot — **eng kichik yuza**; (c) `audit_log` **tenant** hodisalari uchun, anonim marketing so'rovi u yerga **tegishli emas**.
> ⛔ **Yetkazib bo'lmasa** — `delivery_failed` qaytadi va foydalanuvchi **telefon raqamni** ko'radi (§13.8 `landing.form.error.body`). ⛔ «Yubordik» deb **yolg'on aytilmaydi**.
> ⚠ Marshrut **tenant chegarasidan tashqarida** — ya'ni u `market_id` **so'ramaydi** va RLS kontekstiga **kirmaydi**. Bu 1-fazadagi ko'p-ijarali qoidaning **istisnosi** va u reja hujjatida **ochiq** yoziladi.

⚠ **Bu UI-SPEC backend shaklini QULFLAMAYDI** — yuqoridagi ⛔ **UI ning talabi**. Yakuniy shakl (marshrut nomi, chegara qiymati, bot kanali) — 10-faza rejasining **backend vazifasi**.

---

## 13. Copy kontrakti — `landing` fazoviy nomi

### 13.1 ⛔ Qulflangan matnlar — o'zgartirilmaydi [K-2]

| Kalit | uz-Latn (⛔ QULF) |
|-------|-------------------|
| `landing.hero.headline` | **Har bir band rastadan patta to'liq yig'ilyaptimi?** |
| `landing.hero.sub` | **SBOZOR buni raqamlar va rasm-dalil bilan ko'rsatadi — «band, lekin to'lovsiz» rastalar kunlik hisobotda avtomatik fosh bo'ladi.** |
| `landing.hero.claimStrong` | **Yangi uskuna shart emas** |
| `landing.hero.claim` | **— mavjud NVR kameralaringiz bilan ishlaydi. Ulanish — login-parol kiritish, xolos.** |
| `landing.hero.ctaPrimary` | **Demo so'rang** |
| `landing.hero.ctaSecondary` | **Tizimga kirish** |
| `landing.trust.residency` | **Ma'lumotlar O'zbekistonda** |
| `landing.trust.vpn` | **NVR faqat VPN orqali** |
| `landing.trust.audit` | **Har amal auditda** |
| `landing.trust.languages` | **3 til** |
| `landing.steps.title` | **Qanday ishlaydi — 3 qadam** |

### 13.2 Copy reyestri — hajm va shakl

| Guruh | Kalitlar soni (taxminiy) |
|-------|--------------------------|
| `landing.meta.*` (SEO) | 3 |
| `landing.nav.*` | 2 |
| `landing.hero.*` + `landing.trust.*` | 10 |
| `landing.scene.*` | 14 |
| `landing.pain.*` | 7 |
| `landing.steps.*` | 7 |
| `landing.proof.*` | 3 |
| `landing.roles.*` | 10 |
| `landing.trustBlock.*` | 9 |
| `landing.pilot.*` | 3 |
| `landing.faq.*` | 11 |
| `landing.form.*` | 20 |
| `landing.footer.*` | 4 |
| `landing.privacy.*` | ~16 (§11.3 bo'limlari) |
| ⛔ **Jami** | ⛔ **~119 kalit × 3 til** |

⛔ **`common` fazoviy nomidan foydalaniladi va TAKRORLANMAYDI:** `common.appName` (SBOZOR), `common.appTagline`, `common.languageLabel`. ⛔ Yangi `common` kaliti **qo'shilmaydi**.

### 13.3 ⛔⛔ Glossariy — landing matnini ham bog'laydi [L-23]

| Atama | uz-Latn | uz-Cyrl | ru | ⛔ TAQIQ |
|-------|---------|---------|-----|----------|
| rasta | `rasta` | `раста` | `торговое место` | ⛔ uz: **`do'kon`** · ru: **`лавка`**, **`магазин`** |
| patta | `patta` | `патта` | `патта` | ⛔ uz: **`yig'im`** |
| qarz | `qarz` | `қарз` | `долг` | — |
| smena | `smena` | `смена` | `смена` | — |

⛔⛔ **«Patta» ni tushuntirish tuzog'i:** hokimlik vakili «patta» ni bilmasligi mumkin va tabiiy refleks — qavsda «yig'im» deb izohlash. ⛔ **U TAQIQLANGAN SINONIM** va `glossary.test.mjs` (G7-9) uni **darhol** ushlaydi. ⛔ **To'g'ri gloss:** «patta — **kunlik savdo to'lovi**» / «патта — **ежедневный торговый платёж**». ⛔ Gloss **bir marta**, birinchi uchrashda (`landing.pain.a.body`).

### 13.4 ⛔⛔ `AI` — transliteratsiya defekti va uning JUFT tuzatishi [L-11]

**O'lchandi:** `transliterate("AI band rastani aniqlaydi", words)` → ⛔ **`АИ банд растани аниқлайди`**.

⛔ **Tuzatish IKKI faylda va ular JUFT** [MEROS: `uz-Cyrl.overrides.json` `_comment_acronyms`: *«bu ro'yxat `scripts/gen-cyrillic.test.mjs` dagi `allowed` regexi bilan JUFT yuritiladi: biri to'ldirilib ikkinchisi unutilsa, o'sha test qizaradi va bu KUTILGAN xulq»*]:

| # | Fayl | O'zgarish |
|---|------|-----------|
| 1 | `frontend/messages/uz-Cyrl.overrides.json` → `words` | ⛔ `"AI": "AI"` |
| 2 | `frontend/scripts/gen-cyrillic.test.mjs:502` → `allowed` regeksi | ⛔ akronim alternatsiyasiga `AI` qo'shiladi |

⛔ **Nega `AI` saqlanadi, `sun'iy intellekt` ga almashtirilmaydi:** (a) mavjud akronim qoidasi so'zma-so'z shunday — akronim o'quvchini **global atama** bilan bog'laydi; (b) brief §6 da «AI aniqligi» — **raqobat ustunligimizning nomi**; (c) `NVR`/`VPN` bilan **bir xil** muomala izchillikni saqlaydi. ⛔ Rus tilida ham **`AI`** — bitta glossariy, bitta atama.

### 13.5 ⛔ Rezidentlik copy'si — to'liq matn (§11.2)

| Kalit | uz-Latn |
|-------|---------|
| `landing.trustBlock.residency.title` | Ma'lumotlar va O'zR qonunchiligi |
| `landing.trustBlock.residency.body` | Kamera tasvirlari bozor tarmog'idan tashqariga faqat shifrlangan tunnel orqali chiqadi. Shaxsiy ma'lumotlar O'zR qonunchiligiga muvofiq boshqariladi. Joylashuv talabi bo'lsa — hosting O'zbekistonga ko'chiriladi va bu shartnomada qayd etiladi. |

⛔ **`landing.trust.residency` (hero, qisqa shakl) shu blokga HAVOLA qiladi** — `#ishonch` anchor'i (**G-land-4(c)**).

### 13.6 ⛔ Pilot — raqamsiz [K-7]

| Kalit | uz-Latn |
|-------|---------|
| `landing.pilot.title` | Pilot holati |
| `landing.pilot.status` | Karmana bozorida sinovda |
| `landing.pilot.body` | Tizim Navoiy viloyati Karmana tumani bozorida sinovdan o'tmoqda. Natijalar o'lchanib bo'lgach, aniq raqamlar shu yerda e'lon qilinadi — ⛔ **oldindan raqam yozmaymiz**. |

⛔ Oxirgi jumla — ⛔ **ataylab** va u **pozitsiyalash quroli**: raqib «ishlab chiqilmoqda» deb yozib do'kon badge'larini qo'ygan [MEROS: brief §6]. ⛔ Biz **kamroq** va'da qilib **ko'proq** ishonch olamiz.

### 13.7 FAQ — 5 savol, halol javoblar

| # | Savol | Javobning halol yadrosi |
|---|-------|-------------------------|
| 1 | Kameramiz eski — ishlaydimi? | Ko'p hollarda ha: kamera RTSP oqim bersa yoki NVR kadr qaytarsa yetarli. ⛔ **Aniq javob demo paytida NVR modelini ko'rgach beriladi** |
| 2 | Internetimiz sekin | ⛔ **Video uzatilmaydi** — kuniga bir necha marta bittadan kadr olinadi. Sekin ulanish yetarli |
| 3 | Nechta rasta ko'taradi? | Bugungi maqsad — **300–1000 rastali** bozor. Tizim ko'p bozorli: har bozor **alohida ma'lumot chegarasida** |
| 4 | Narx qanday shakllanadi? | Bozor hajmi va kameralar soniga bog'liq. ⛔ **Aniq raqam demo suhbatida** — bu yerda umumiy raqam yozish adashtirardi |
| 5 | O'rnatish qancha vaqt oladi? | ⛔ **Ulanish** — NVR login-paroli, daqiqalar ichida; kameralar avtomatik topiladi. ⛔ **To'liq sozlash** (rastalar, tariflar, zonalar) — bozor hajmiga qarab bir necha soat |

⛔ **4-savolda narx YOZILMAYDI** [MEROS: brief §2.8 «narx qanday shakllanadi (demo'da aytiladi)»]. ⛔ **5-savolda «5 daqiqada ishga tushadi» YOZILMAYDI**: brief §6 raqobat jadvalidagi «Login-parol, 5 daqiqa» — ⛔ **ulanish** haqida, **to'liq sozlash** haqida emas. Ikkovini aralashtirish — K-7 ning ayni sinfidagi yolg'on.

### 13.8 Forma matnlari — sabab VA tuzatish [MEROS: D-02]

| Kalit | uz-Latn | ru |
|-------|---------|-----|
| `landing.form.title` | Demo so'rang | Запросить демо |
| `landing.form.subtitle` | 24 soat ichida bog'lanamiz va bozoringiz uchun aniq javob beramiz. | Свяжемся в течение 24 часов и дадим конкретный ответ по вашему рынку. |
| `landing.form.name` | Ismingiz | Ваше имя |
| `landing.form.phone` | Telefon raqamingiz | Ваш телефон |
| `landing.form.market` | Bozor nomi | Название рынка |
| `landing.form.stallCount` | Rastalar soni (taxminan) | Количество торговых мест (примерно) |
| `landing.form.consent` | Maxfiylik siyosati bilan tanishdim va ma'lumotlarim shu so'rov uchun ishlatilishiga roziman. | Ознакомлен с политикой конфиденциальности и согласен на использование данных для этого запроса. |
| `landing.form.submit` | Demo so'rang | Запросить демо |
| `landing.form.submitting` | Yuborilmoqda… | Отправляется… |
| `landing.form.success.title` | So'rovingiz yuborildi | Запрос отправлен |
| `landing.form.success.body` | 24 soat ichida ko'rsatgan raqamingizga bog'lanamiz. | Свяжемся с вами по указанному номеру в течение 24 часов. |
| `landing.form.error.title` | So'rov yuborilmadi | Запрос не отправлен |
| `landing.form.error.body` | Ulanishda muammo bo'ldi. Qayta urinib ko'ring yoki bevosita qo'ng'iroq qiling: {phone} | Возникла проблема с соединением. Повторите попытку или позвоните напрямую: {phone} |
| `landing.form.error.rateLimited` | Juda ko'p so'rov yuborildi. Bir necha daqiqadan so'ng qayta urinib ko'ring. | Слишком много запросов. Повторите через несколько минут. |
| `landing.form.validation.nameRequired` | Ismingizni kiriting. | Укажите ваше имя. |
| `landing.form.validation.phoneRequired` | Telefon raqamingizni kiriting. | Укажите ваш телефон. |
| `landing.form.validation.phoneInvalid` | Raqamni +998 bilan, 9 raqamda kiriting. Masalan: +998 90 123 45 67 | Введите номер в формате +998 и 9 цифр. Например: +998 90 123 45 67 |
| `landing.form.validation.marketRequired` | Bozor nomini kiriting. | Укажите название рынка. |
| `landing.form.validation.consentRequired` | Davom etish uchun maxfiylik siyosatiga rozilik kerak. | Для продолжения нужно согласие с политикой конфиденциальности. |

⛔ **Har xato — sabab + keyingi qadam.** ⛔ Quruq «Xatolik yuz berdi» ⛔ **yozilmaydi**.

### 13.9 Sahna matnlari [K-7]

| Kalit | uz-Latn |
|-------|---------|
| `landing.scene.sampleBadge` | Namunaviy ma'lumot |
| `landing.scene.marketLabel` | Namuna bozori · demonstratsiya |
| `landing.scene.revenueLabel` | Bugungi tushum |
| `landing.scene.phase1` | Bozor xaritasi chizilmoqda… |
| `landing.scene.phase2` | Kamera tekshiryapti… |
| `landing.scene.phase3` | Nomuvofiqlik topildi |
| `landing.scene.phase4` | Kassir to'lovni qayd etdi |
| `landing.scene.phase5` | Kunlik hisobot |
| `landing.scene.tagUnpaid` | Band, lekin to'lovsiz — D-11 |
| `landing.scene.tagPaid` | To'landi — 8 000 so'm |
| `landing.scene.reportTitle` | Kunlik hisobot |
| `landing.scene.reportOccupied` | Band rastalar |
| `landing.scene.reportPaid` | To'langan |
| `landing.scene.reportUnpaid` | Band, lekin to'lovsiz |
| ⛔ `landing.scene.a11yDescription` | Namunaviy bozor xaritasi: 30 rastadan 29 tasi to'langan, bittasi band bo'lib to'lovsiz qolgan; kunlik hisobotda u fosh bo'ladi. |

⛔ **`a11yDescription` — sahnaning matnli ekvivalenti** (§15.2). ⛔ U «namunaviy» so'zini **o'z ichiga oladi** — skrinrider foydalanuvchisi ham vizual belgini ko'rmaydi (**G-land-4(b)**).

### 13.10 Transliteratsiya [L-12]

⛔ 40 nomzod satrdan — ⛔ **`AI` dan boshqa 0 defekt**. `uz-Cyrl.json` ⛔ **`npm --prefix frontend run i18n:gen`** bilan quriladi; `uz-Cyrl.overrides.json` ga ⛔ **aynan bitta yozuv** qo'shiladi (`AI`, §13.4).

⛔ **Rus tili — MUSTAQIL tarjima**, transliteratsiya hosilasi **emas** [MEROS: `glossary.json` `_banned_synonyms_readme`]. ⛔ Ya'ni ru copy **qayta yozilishi** kerak, «kirilldan ko'chirish» ⛔ **taqiq**.

---

## 14. SEO va metadata [ROADMAP SC#5]

### 14.1 Sahifa metadata'si

| Element | Manba | Shakl |
|---------|-------|-------|
| `title` | `landing.meta.title` | ⛔ Brend **va** va'da: «SBOZOR — bozor pattasi nazorati: har band rastadan to'lov yig'ilyaptimi?» ⛔ Raqibning `title="Smart Office"` xatosi [MEROS: brief §6] bu yerda **arzon g'alaba** |
| `description` | `landing.meta.description` | ≤160 belgi, ⛔ **savol + mexanizm** |
| `openGraph` | `generateMetadata` | `title`, `description`, `url`, `siteName`, `locale`, `type: "website"`, `images: [{ url, width: 1200, height: 630, alt: landing.meta.ogAlt }]` |
| `twitter` | `generateMetadata` | `card: "summary_large_image"` |
| `alternates.languages` | `generateMetadata` | ⛔ **Uchala locale** — `hreflang` |
| `alternates.canonical` | `generateMetadata` | Joriy locale URL'i |

⛔ **OG rasmi — STATIK PNG** (`/public/og/sbozor-og.png`), ⛔ **`ImageResponse` EMAS** [QAROR]: `next/og` **runtime** talab qiladi (satori), SSG sahifada **build vaqtini** va **paketni** oshiradi, va K-9 ning ruhiga zid. ⛔ **Bitta**, til-neytral rasm (SBOZOR belgisi + stilizatsiyalangan xarita, bitta amber katak); ⛔ **`alt` esa locale bo'yicha** tarjima qilinadi.

### 14.2 Fayl konventsiyalari [L-24]

| Fayl | Joyi | Vazifasi |
|------|------|----------|
| `sitemap.ts` | ⛔ `src/app/sitemap.ts` | Uchala locale ildizi + maxfiylik sahifasi; ⛔ `alternates.languages` bilan |
| `robots.ts` | ⛔ `src/app/robots.ts` | ⛔ **`/api/`, `/*/dashboard`, `/*/collect`, `/*/login` va boshqa app marshrutlari `Disallow`**; landing va maxfiylik — `Allow`; `sitemap` havolasi |
| `favicon.ico` | ⛔ **Mavjud** | Tegilmaydi |

⛔ **Ikkalasi ham `proxy.ts` matcher'idan TASHQARIDA** [L-24] — nuqtali yo'llar chetlab o'tiladi, ya'ni locale prefiksi **qo'shilmaydi**.

⛔⛔ **`robots.ts` DA APP MARSHRUTLARI YOPILADI** [QAROR]: app sahifalari `/login` ga redirect qiladi, lekin indekslangan `/uz/collect` havolasi qidiruv natijasida **ichki tuzilmani** oshkor qilardi va foydalanuvchini **o'lik havolaga** olib borardi.

### 14.3 Strukturaviy ma'lumot (JSON-LD)

⛔ **Ikki tur, ⛔ boshqasi yo'q:**

| Tur | Nima uchun |
|-----|------------|
| `Organization` | Brend nomi, logotip, aloqa — qidiruvda **bilim paneli** |
| `FAQPage` | §13.7 ning 5 savoli — ⛔ **qidiruv natijasida to'g'ridan-to'g'ri ko'rinadi** va bu **arzon g'alaba** |

⛔ **`Product`, `AggregateRating`, `Review` — TAQIQ** [K-7]: reyting yo'q, sharh yo'q; ⛔ ularni yozish **soxta ijtimoiy isbot** bo'lardi.

⛔ JSON-LD — ⛔ **Server Component** ichida `<script type="application/ld+json">`, matn **tarjima katalogidan** (FAQ matni **ikki marta** yozilmaydi — bitta manba, ikkita chiqish; **G-land-4(d)**).

---

## 15. Qulaylik (a11y)

| # | Talab | Shakl |
|---|-------|-------|
| **15.1** | ⛔ `prefers-reduced-motion` | ⛔ **Mavjud global blok** [KOD: `globals.css:184`] barcha `transition`/`animation` ni 0.01ms ga tushiradi; ⛔ sahna **sikl boshlamaydi** (§5.2) va **server kadri** qoladi |
| **15.2** | ⛔⛔ **Sahna — bezak emas, KONTENT** | ⛔ Sahna konteynerida `role="img"` + `aria-label={landing.scene.a11yDescription}`; ⛔ ichki o'zgaruvchan qismlar `aria-hidden="true"`. ⛔ **Faza yorlig'i `aria-live` ga QO'YILMAYDI** — 12s da 5 marta gapirish **shovqin** |
| **15.3** | Tushum hisoblagichi | ⛔ `aria-hidden` (sahna ichida) — yakuniy qiymat `a11yDescription` da |
| **15.4** | ⛔ **Rozilik havolasi** | ⛔ Maxfiylik siyosatiga havola **checkbox yorlig'i ICHIDA**, alohida qatorda emas — bosish maydoni aniq, skrinriderda kontekst saqlanadi [K-8] |
| **15.5** | Forma xatolari | ⛔ `aria-invalid` + `aria-describedby`; ⛔ **birinchi** xato maydoniga fokus; xato bloki `role="alert"` |
| **15.6** | Forma natijasi | ⛔ Muvaffaqiyat — `role="status"` + `aria-live="polite"`; xato — `role="alert"` |
| **15.7** | ⛔ **Skip-link** | ⛔ **Majburiy**: `landing.nav.skipToContent` → `#kontent`. Sahifa uzun va header'da til almashtirgichning **3 tugmasi** bor |
| **15.8** | FAQ | ⛔ Native `<details>`/`<summary>` — klaviatura va skrinrider **JS'siz** ishlaydi; ⛔ ARIA akkordeoni **qurilmaydi** |
| **15.9** | Fokus halqasi | ⛔ **Meros** `:focus-visible` [KOD: `globals.css:168`] — tegilmaydi |
| **15.10** | Barmoq nishoni | CTA ≥56px; header havolalari ≥44px; ⛔ til tugmalari — **meros** |
| **15.11** | ⛔ **Sarlavha ierarxiyasi** | ⛔ Sahifada **aynan bitta `<h1>`** (hero); har seksiya — `<h2>`; qadam/karta sarlavhalari — `<h3>`. ⛔ O'lcham uchun daraja **o'tkazib yuborilmaydi** |
| **15.12** | ⛔ **Rang yolg'iz signal emas** | ⛔ Sahnadagi amber rasta **yorliq matni** bilan juft; ishonch qatoridagi ✓ — dekorativ, ma'no **matnda** |
| **15.13** | Til | ⛔ `<html lang>` — **meros** [KOD: `layout.tsx:74`]; ⛔ lotin sahifasidagi kirill parcha **yo'q** (butun sahifa bir tilda) |

---

## 16. Darvozalar

### 16.1 ⛔ Raqamlash — BESHINCHI ketma-ketlik va sabab

| Ketma-ketlik | Diapazon | Uyi |
|--------------|----------|-----|
| Frontend darvozalari | `G-1`…`G-43` band | `frontend/scripts/*.test.mjs`, `*.test.tsx` |
| Backend/faza darvozalari | `G-1`…`G-16` band | `tests/**` |
| 7-fazaning taqiq darvozalari | `G7-1`…`G7-9` band | 07-RESEARCH |
| Motion darvozalari | `G-motion-1`…`G-motion-7` band | `frontend/scripts/*` |
| ⛔ **Landing darvozalari** | ⛔ **`G-land-1`…`G-land-5`** | `frontend/scripts/landing-surface.test.mjs`, `components/marketing/*.test.tsx` |

**Qoidalar:**

1. ⛔ Yangi darvozalar **`G-land-1`…`G-land-5`**; `G-44` ⛔ **band qilinmaydi** (09-UI-SPEC §16.1 qoida 1 ni davom ettiradi).
2. Kod izohlarida ID **manba bilan**: `G-land-3 (10-UI-SPEC)`.
3. ⛔⛔ **Bu hujjat `G-18` e'lon qatorini YOZMAYDI** [L-26] — `bulk-action-surface.test.mjs` uni e'lon qilgan UI-SPEC sonini **aynan 1** talab qiladi. `G-land-*` nomlari uning regeksiga **tushmaydi**.
4. ⛔ **Mavjud darvozalarning `MIN_*` chegaralari KAMAYTIRILMAYDI** [K-10]. Landing fayllari `MIN_SRC_FILES` (150) va `MIN_COMPONENT_FILES` (100) ni ⛔ **oshiradi** — bu **quyi** chegara, muammo emas.

### 16.2 Har darvozaning ikki muzokarasiz xossasi [MEROS: 06/07/08/09-UI-SPEC]

| Xossa | Ma'nosi |
|-------|---------|
| ⛔ **HOSILA qamrov** | Darvoza katalogni **o'qiydi**, reyestrdan **iteratsiya qiladi**. Qo'lda yozilgan ro'yxat **yo'q** |
| ⛔ **TO'PLAM TENGLIGI** | `deepEqual`/`Set`. ⛔ `not.toContain(...)` **ishlatilmaydi** |

### 16.3 ⛔ Sabotaj majburiyati [MEROS: 05-15, 08-20, 09 darslari]

Har darvoza uchun reja **sabotaj o'lchovini** yozadi. ⛔ **Sabotaj modulni IMPORT QILINADIGAN holda qoldirishi SHART** — aks holda u mezonni emas, **yig'ilishni** o'lchaydi. ⛔ Sabotaj sistemaga yetib borib ham hech nima qizarmasa, tuzatish **testda emas — HOLATDA**.

### 16.4 Yangi darvozalar — beshta, ⛔ **BITTA yangi skript fayli**

⛔ **Byudjet sababli qamrov ataylab tor** (§18 O-01): to'rtta darvoza **bitta** sof matn/CSS parse faylida (`scripts/landing-surface.test.mjs` — tez), beshinchisi mavjud vitest infratuzilmasida.

| # | Darvoza | Fayl | Mexanik ravishda NIMANI o'qiydi | Nima uchun mavjud |
|---|---------|------|----------------------------------|-------------------|
| **G-land-1** | ⛔⛔ **LCP YO'LI KLIENTGA BOG'LANMAGAN** (SC#5) | `scripts/landing-surface.test.mjs` | **(a)** `app/[locale]/(marketing)/**` va `components/marketing/**` da `"use client"` bo'lgan fayllar to'plami ⛔ **reyestrga `deepEqual`**: `hero-scene.tsx`, `step-line.tsx`, `reveal.tsx`, `demo-form.tsx` (§4.4). **(b)** ⛔ `marketing/hero.tsx` (h1 uyi) manbasida `"use client"` — **0**; `landing.hero.headline` chaqirig'i **bor**. **(c)** ⛔ `(marketing)/layout.tsx` da `NextIntlClientProvider` ga uzatilgan fazoviy nomlar ⛔ **aynan** `["common","landing"]` (§4.3). **(d)** ⛔ `app/[locale]/page.tsx` ⛔ **mavjud emas** va `(marketing)/page.tsx` **mavjud** (L-7 ning regressiya qulfi). ⛔ **SABOTAJ:** `hero.tsx` ga `"use client"` qo'shiladi — **(b) qizarishi SHART**; reyestrga beshinchi klient fayli qo'shiladi — **(a) qizarishi SHART** | ⛔ **§1.2 qoida 1.** Bitta `"use client"` LCP nomzodini (h1) hidratatsiya kutishiga bog'lab, **SC#5 ni jimgina** yiqitadi. (c) — L-5 ning 27 KB gzip'ini qaytarib olib kelishning **eng arzon yo'li** |
| **G-land-2** | ⛔⛔ **12s SIKL VA REDUCED-MOTION STATIK KADRI** (SC#2) | `components/marketing/hero-scene.test.tsx` | **(a)** ⛔ `matchMedia("(prefers-reduced-motion: reduce)")` **true** mock'ida: ⛔ **birorta `setTimeout` chaqirilmaydi** (`vi.useFakeTimers` + `setTimeout` josusi = **0**) **VA** DOM'da **to'liq final-kadr** — 30 katak, bittasi `unpaid`, hisobot **ko'rinadi**, tushum matni **`2 306 000`**. **(b)** ⛔ **false** mock'ida: soxta taymer bilan **0ms** — DOM **hamon final-kadr** (§5.2 «rewind yo'q»); **13 500ms** — ⛔ sikl **1-fazaga** qaytgan (kataklar `.on` emas). **(c)** ⛔ Beshala faza yorlig'i (`landing.scene.phase1..5`) sikl davomida **ketma-ket** ko'rinadi — reyestr **matn katalogidan** hosila, testda qayta yozilmaydi. **(d)** ⛔ **TAYMER SIZIB QOLMAYDI:** `unmount()` dan keyin `clearTimeout` chaqiriqlari soni ⛔ **yaratilgan taymerlar soniga TENG**. **(e)** ⛔ `IntersectionObserver` `isIntersecting: false` bersa — yangi taymer **yaratilmaydi**. ⛔ **SABOTAJ:** reduced-motion shoxidagi erta `return` olib tashlanadi — **(a) qizarishi SHART**; `unmount` tozalash funksiyasi olib tashlanadi — **(d) qizarishi SHART** | ⛔ **ROADMAP SC#2 ning yagona halol o'lchovi.** (a) eng muhimi: «statik final-kadr» **niyat** bo'lib qolishi oson — mexanizm esa **taymer chaqirilmasligi**. (d) — arzon telefonda sizib qolgan 12s halqa batareyani sahifa yopilgandan **keyin ham** yeydi |
| **G-land-3** | ⛔⛔ **GPU XOSSALARI — `transition` LARDA HAM** (SC#5) | `scripts/landing-surface.test.mjs` | **(a)** ⛔ `globals.css` dagi **har** `.landing-*` va `.motion-*` sinfining `transition` xossa ro'yxati ⛔ **ruxsat to'plamiga QISM**: `{transform, opacity, background, background-color, border-color, box-shadow, color}`; ⛔ `width`,`height`,`top`,`left`,`right`,`bottom`,`margin*`,`padding*`,`all` — **har biri 0**. ⛔⛔ **Bu G-motion-3(a) ning O'LCHANGAN bo'shlig'i** [L-8]: u faqat `@keyframes` ni parse qiladi. **(b)** ⛔ `components/marketing/**` da inline `style` ichida `height`/`width`/`left`/`top` ⛔ **0 marta** (AST emas, satr skani — inline geometriya **umuman** yozilmaydi). **(c)** ⛔ **Sahifada avtomatik harakat AYNAN BITTA sahnada**: `components/marketing/**` da `setInterval` — **0**, `setTimeout` ⛔ **faqat** `hero-scene.tsx` da (§5.6 mexanizm 4). **(d)** ⛔ `@keyframes` reyestri **9 nom** va yangisi ⛔ **aynan `sweep`** — mavjud 8 tasi `deepEqual` bilan **o'zgarmagan** [L-9]. ⛔ **SABOTAJ:** `.landing-step-fill` ga `transition: height 900ms` qo'shiladi — **(a) qizarishi SHART**; `roles-card.tsx` ga `setInterval` qo'shiladi — **(c) qizarishi SHART** | ⛔ **L-8 — sabotaj emas, O'LCHANGAN HOLAT:** foydalanuvchi tasdiqlagan maket manbasining **ikki** animatsiyasi taqiqlangan xossada yozilgan va ulardan **biri** (`transition: height`) bugungi darvozadan **jimgina o'tardi**. Bu darvoza aynan o'sha teshikni yopadi |
| **G-land-4** | ⛔⛔ **HALOLLIK — YOLG'ON RAQAM VA YOLG'ON DA'VO YO'Q** (SC#4, K-7) | `scripts/landing-surface.test.mjs` | **(a)** ⛔ `landing.scene.sampleBadge` chaqirig'i `hero-scene.tsx` da **bor** va u **shartli render ichida EMAS** (`{cond && ` naqshi yo'q). **(b)** ⛔ `landing.scene.a11yDescription` qiymatida «namunaviy»/«намунавий»/«демонстрацион» o'zagi ⛔ **uchala locale'da** bor. **(c)** ⛔ `landing.trustBlock.residency.body` uchala locale'da **bor** va hero'ning `trust.residency` i unga **anchor** bilan bog'langan (§13.5). **(d)** ⛔ FAQ JSON-LD matni **tarjima katalogidan** olinadi — `components/marketing/**` da FAQ savol/javob **literal** yozilmaydi (ikki manba **imkonsiz**). **(e)** ⛔ **TAQIQLANGAN DA'VO TOKENLARI** `landing.*` qiymatlarida uchala locale'da **0 marta**: `jonli` («jonli oqim» da'vosi), `%`, `martaga`, `в разы`, `гарантир`, `kafolatlaymiz`, `eng yaxshi`, `лучший`, `№1`; ⛔ quyi chegara **≥8 token**. **(f)** ⛔ `landing.pilot.*` qiymatlarida **raqam** (`\d`) ⛔ **0 marta**. ⛔ **SABOTAJ:** `landing.pilot.body` ga «30% o'sish» qo'shiladi — **(e) va (f) qizarishi SHART**; `sampleBadge` shartli render ichiga olinadi — **(a) qizarishi SHART** | ⛔ **K-7 + brief §7.5.** Bu **eng oson buziladigan** shartnoma: marketing matnini «kuchaytirish» refleksi tabiiy va u **bir commitda** brendning yagona ustunligini — **halollikni** — yo'q qiladi. (f) ataylab qattiq: pilotda **hech qanday** raqam bo'lmasligi kerak, «taxminan 200 rasta» ham |
| **G-land-5** | ⛔ **TIPOGRAFIYA VA BO'SHLIQ KENGAYTMASI — SANOQLI** (§0.2, §7, §8.2) | `scripts/landing-surface.test.mjs` | **(a)** ⛔ `text-hero` utilitasi ⛔ **AYNAN 1 mahsulot faylida** va u ⛔ **reyestrga teng**: `components/marketing/hero.tsx`; ⛔⛔ **VA o'sha faylda uchrashuvlar soni AYNAN 1** — ya'ni qulf **fayl darajasida ham, element darajasida ham** ishlaydi (§7.1.1 ning 2- va 3-bandi aynan shu ikki qatlamga tayanadi; faqat fayl qulfi bo'lsa, hero faylining ichida ikkinchi hero-o'lchamli sarlavha **jimgina** paydo bo'lardi). **(b)** ⛔ `--text-hero` `globals.css` ning `@theme` blokida **bor** va qiymati `clamp(` bilan boshlanadi. **(c)** ⛔ `py-16`/`py-24` ⛔ **faqat** `components/marketing/section.tsx` da (§8.2) — boshqa marketing faylida **0**. **(d)** ⛔ `components/marketing/**` va `(marketing)/**` da `text-base` **0**, `text-3xl` **0**, `text-[` **0**, `font-medium` **0** — ⛔ mavjud chegaralar **to'lgan** [L-2, L-3]. **(e)** ⛔ `text-display` `components/marketing/**` da **0 marta** [L-4]. ⛔ **SABOTAJ:** `roles-card.tsx` ga `text-base` qo'shiladi — **(d) qizarishi SHART**; `text-hero` ikkinchi faylga qo'shiladi — **(a) qizarishi SHART** | ⛔ **§0.2 ning mexanik shakli.** `typography.test.mjs` **butun `src/**`** ni skanerlaydi va `text-base` chegarasi **7 da to'lgan** — ya'ni landing'ning birinchi 16px matni **butun zanjirni** qizartiradi. (d) xatoni **landing faylida** ushlaydi va ijrochiga **sababni** aytadi; `typography.test.mjs` esa faqat «7 dan oshdi» derdi |

### 16.5 ⛔ Lighthouse, LCP va payload — HALOL joylashtirish

⛔ **Lighthouse CI'da YO'Q va bu fazada QO'SHILMAYDI** [MEROS: 09-UI-SPEC §16.6] — headless Chrome + yangi ishlab chiqish bog'liqligi `gate` byudjetiga **daqiqalar** qo'shardi, byudjet esa **41 s zaxirada** (§18 O-01).

| Talab | Qayerda o'lchanadi |
|-------|--------------------|
| Lighthouse **≥95** (arzon Android) | ⛔ **`10-HUMAN-UAT.md`** — egasi **ijrochi**, tetigi **birinchi deploy**; natija **son bilan** |
| **LCP < 1.5s** | ⛔ **`10-HUMAN-UAT.md`** — ⛔ mexanik **proksi**: **G-land-1** (LCP yo'li klientga bog'lanmagan) |
| ⛔ **Payload farqi** (§4.3) | ⛔ **`10-HUMAN-UAT.md`** — ⛔ `next build` route jadvali **o'zgarishdan OLDIN va KEYIN**, farq **son bilan**. ⛔ **Bu majburiy**: §4.3 da «~50 KB tejaladi» da'vosi **BERILMAGAN** va u o'lchovsiz **berilmaydi** |
| Bundle byudjeti (0 KB o'sish) | ⛔ **Mavjud G-motion-3(d)** — `dependencies` to'plam tengligi [L-21] |
| 60fps | ⛔ **G-land-3** (GPU xossalari); qurilmadagi o'lchov HUMAN-UAT'da |
| SEO to'liqligi | ⛔ Qisman **G-land-4(d)** (JSON-LD manbasi); to'liq audit HUMAN-UAT'da |

⛔ **Mexanika qatlamining yashilligi bilan o'lchov qatlamining yo'qligini yopish TAQIQLANADI** [MEROS: D-01, FOUND-07, AI-02 darslari]. ⛔ HUMAN-UAT bandi **son bilan** yopiladi, «tez ko'rinadi» bilan emas.

### 16.6 Sampling — mavjud byudjetlar va ⛔ **KRITIK ZAXIRA**

| Daraja | Buyruq | Byudjet | ⛔ Bugungi zaxira [MEROS: STATE.md] |
|--------|--------|---------|-------------------------------------|
| Task commit | `npm run gate:fast` | **200 s** | ⛔ **11 s (5,5 %)** — o'lchov 189/171 s |
| Faza darvozasi | `npm run gate` | **2300 s** | ⛔⛔ **41 s (1,8 %)** — o'lchov 2259/2102 s |

⛔⛔ **Bu SPEC ning qo'shimchasi ataylab kichik**: **1** yangi `scripts/*.test.mjs` (sof matn/CSS parse — tez) + **2** vitest fayli (`hero-scene.test.tsx`, `demo-form.test.tsx`). ⛔ Baholangan qo'shimcha — **~15–30 s**, ya'ni 41 s zaxira **yetishi mumkin, lekin kafolat yo'q**.

⛔ **Chegara masalasi 10-faza rejalovchisiga OCHIQ SAVOL sifatida topshiriladi** — §18 O-01.

---

## 17. Bu fazada BO'LMAYDIGAN UI

### 17.1 Keyingi fazaga / v2 ga qoldiriladigan

| Imkoniyat | 10-fazada aynan nima qilinadi | Nima QILINMAYDI | Tetigi |
|-----------|-------------------------------|------------------|--------|
| ⛔ **Brief §7.2 «Bozorning bir kuni» kino-scroll'i** | ⛔ **Scroll-reveal** (bloklar 8px+fade bilan ochiladi) | Ketma-ket sahna-o'tishlar, telefon mockup'ida jonli kassir ketma-ketligi, scroll-bog'langan xoreografiya | Pilot natijalari + **ikkinchi** sahna dvigateli byudjeti |
| ⛔ **App'dan real skrinshotlar** | ⛔ **Hech narsa** (§9.3) | 9 rasm (3 rol × 3 til) | Pilot go-live + ⛔ **shaxsiy-ma'lumot tozalash ro'yxati** |
| **Pilot raqamlari** | ⛔ Faqat **holat** [K-7] | «X% o'sish», «Y so'm topildi» | ⛔ Karmana o'lchovi **yakunlangach** |
| **Narx sahifasi / kalkulyator** | ⛔ **Hech narsa** | Tarif jadvali | Narx modeli **qulflangach** |
| **Blog / yangiliklar / case-study** | ⛔ **Hech narsa** | Kontent tizimi | Marketing resursi paydo bo'lganda |
| **Mijozlar logotiplari** | ⛔ **Hech narsa** | «Bizga ishonishadi» qatori | ⛔ Ikkinchi bozor **jonli** bo'lgach |
| **Ro'yxatdan o'tish (self-serve)** | ⛔ **Hech narsa** — faqat demo-forma | Onboarding oqimi | Mahsulot qarori |
| **Analitika / piksel** | ⛔ **Hech narsa** (§17.2) | GA, Meta piksel, hotjar | §17.2 tetigi |
| **A/B test** | ⛔ **Hech narsa** | Variant infratuzilmasi | Trafik **o'lchanadigan** bo'lgach |
| **`pathnames` lokalizatsiyasi** | ⛔ **Hech narsa** — `maxfiylik` uchala tilda (§4.1) | Locale bo'yicha slug | SEO auditi talab qilsa — ⛔ **barcha** marshrutlar bir vaqtda |

### 17.2 Ataylab qurilMAYDIGAN — sabab bilan

| Nima | Nima uchun |
|------|-------------|
| ⛔ **Analitika skripti (GA / Meta / hotjar)** | (a) Uchinchi tomon JS — Lighthouse ≥95 va K-9 ga **o'lchanadigan** zarar; (b) ⛔ **cookie-banner majburiy** bo'lardi (§11.3) va u LCP yo'liga overlay qo'shardi; (c) §11.3 bandi 5 («uchinchi tomonga uzatilmaydi») **yolg'onga** aylanardi. ⛔ **Tetigi:** konversiya o'lchovi zarur bo'lsa — **server tomonda** (demo-so'rov sanog'i botda), klient skripti **emas** |
| ⛔ **CTA'da kursor-yaqinlik nuri** (brief §7.3) | Har `mousemove` da JS; ⛔ **faqat desktop**; foydasi — **nol**, chunki CTA allaqachon sahifadagi **yagona** to'yingan aksent |
| ⛔ **Fon donadorligi / grain** (brief §7.3) | Takrorlanuvchi rasm yoki SVG filtri — ⛔ **baytlar va paint**; iliq `#FAFAF9` fon [L-1 09-faza] «tirik qog'oz» ishini **allaqachon** bajaradi |
| ⛔ **Rol-kartalarida hover mini-animatsiyasi** (brief §7.3) | Skrinshot **yo'q** (§9.3), ya'ni animatsiya qiladigan narsa yo'q; ⛔ **faqat desktop** naqsh |
| ⛔ **Parallax** | `landing-sehri.md` «Nimadan qochish» ro'yxatida **nomma-nom**; scroll-bog'langan `transform` arzon Androidda jank beradi |
| ⛔ **Avtoplay video** | [K-1] — sahna **CSS/JS**; video har tilda **qayta montaj** talab qilardi va LCP'ni o'ldirardi |
| ⛔ **Cookie-banner** | §11.3 — marketing cookie'si **yo'q**; banner **yolg'on taassurot** berardi |
| ⛔ **CAPTCHA** | §12.2 — uch sabab |
| ⛔ **`sonner` toast formada** | §12.4 — natija **sahifada qolishi** kerak |
| ⛔ **Tema almashtirgich landing'da** | §6.4 — anonim tashrifchi uchun **ma'nosiz**, «yagona CTA» intizomini suyultiradi |
| ⛔ **Sticky header** | Sahifa **konversiyaga** qaratilgan va CTA **ikki joyda** (hero + yakun); sticky header mobil ekranning **12%** ini yeydi |
| ⛔ **Chat-widget / onlayn maslahatchi** | Uchinchi tomon JS + maxfiylik + K-5 («CRM yo'q») ga zid |

### 17.3 Erta optimizatsiya deb baholangan «ilgaklar»

Sahna uchun tezlik sozlamasi (`prefers-reduced-motion` **yetarli**) · ikkinchi hero varianti (A/B uchun) · `--text-hero` ga ikkinchi suyuq rol · umumiy `<AnimatedSection>` abstraktsiyasi (bitta iste'molchi) · landing uchun alohida tema · sahna uchun WebGL/canvas qatlami · OG rasmini `ImageResponse` bilan generatsiya (§14.1).

---

## 18. Ochiq qoldirilgan savollar — har biri uchun ishlaydigan standart bor

Bu subagent kontekstida foydalanuvchiga savol berish vositasi yo'q (avtonom rejim). Har biri uchun standart tanlangan; rejalashtirish javob kutib **to'xtamaydi**.

| # | Savol | Bilamiz | Noaniq | Tanlangan standart va TETIGI |
|---|-------|---------|--------|-------------------------------|
| **O-01** | ⛔⛔ **`gate` byudjeti — 41 s zaxira landing darvozalarini ko'taradimi?** | [MEROS: STATE.md] `gate` **2259/2102 s**, chegara **2300 s** — zaxira **41 s (1,8 %)**; `gate:fast` zaxira **11 s**. Bu SPEC **1** skript + **2** vitest fayli qo'shadi (~15–30 s) | ⛔ **Sig'adimi — O'LCHANMAGAN.** Va 9-fazaning o'zi «~40–60 s» qo'shishni baholagan edi | ⛔ **BU SAVOL 10-FAZA REJALOVCHISIGA OCHIQ TOPSHIRILADI** [Topshiriq bandi]. Standart: ⛔ **darvozalar qo'shiladi, chegara REJADA o'lchanadi**. ⛔ Oshsa — 05-15 W0-13 protokoli **majburiy**: **tinch xost**, **uch o'lchov**, **eng yomon × 1,20**, sabab **yozilgan**, jurnal `package.json //gate-budget` da. ⛔ **Jimgina ko'tarish TAQIQ.** **Tetigi:** birinchi to'liq `gate` yugurishi. ⚠ **Muqobil, agar chegara ko'tarilishi rad etilsa:** G-land-5 ni `typography.test.mjs` ga **qo'shish** (yangi fayl ochilmaydi) va G-land-2 ni **bitta** vitest fayliga siqish — ⛔ lekin shunda xato xabarlari **noaniqroq** bo'ladi |
| **O-02** | Provayderlarni `(app)`/`(auth)` ga tushirish (§4.3) **shu fazadami**? | [L-5] matn katalogi **21,8–27,1 KB gzip** har marshrutga tushadi; `[locale]/` ildizida boshqa sahifa **yo'q** [O'LCHANDI] | ⛔ Provayderlarning **JS** og'irligi **o'lchanmagan** — `next build` kerak | ⛔ **HA, shu fazada** (§4.3). Sabab: SC#5 ning raqami (**≥95**) mexanizmsiz bajarilmaydi va xavf **o'lchangan darajada tor**. ⛔ **Tetigi:** ko'chirish `(app)`/`(auth)` da **o'lchangan** regressiya bersa — qaytariladi va landing **ichki** `NextIntlClientProvider` bilan tashqarisini **soyalaydi**; yo'qotish HUMAN-UAT'ga **son bilan** yoziladi |
| **O-03** | Landing temani **qulflasinmi** (faqat iliq)? | [L-13] landing juftliklari **uchala** temada AA dan o'tadi; anonim `localStorage` **bo'sh** → `light` | Ilovadan `dark` bilan kelgan foydalanuvchi landing'ni **qanday kutadi** | ⛔ **QULFLANMAYDI — meros olinadi** (§6.4). Sabab **mexanik**: majburlash **yangi `[data-theme="light"]` scope bloki**ni talab qilardi va `theme-tokens`/`contrast` darvozalarining **ikkalasini** ochardi; foyda esa **nol** (maqsadli auditoriya baribir iliq ko'radi). ⛔ **Tetigi:** dala UAT'da qorong'i landing **noto'g'ri o'qilsa** — u holda to'g'ri yechim tema qulfi emas, ⛔ **landing marshrutida `data-theme` ni `light` ga majburlovchi bitta qator** `(marketing)/layout.tsx` da (va u **uchinchi** scope bloki emas) |
| **O-04** | Demo-forma ma'lumoti **DB'ga yozilsinmi**? | [K-5] CRM **yo'q**; [K-8] shaxsiy ma'lumot rejimi qattiq; [L-25] public marshrut **yo'q** | Sotuv jarayoni kelajakda **tarix** talab qiladimi | ⛔ **YOZILMAYDI** (§12.5). Sabab: iste'molchisi yo'q ma'lumot — **eng katta yuza**; Telegram kanali **yozuvning o'zi**. ⛔ **Tetigi:** sotuv jarayoni tarix talab qilsa — bu **CRM qarori** (K-5 ni qayta ochish), landing UI'si emas; va u §11.3 maxfiylik matnini **birinchi navbatda** o'zgartiradi |
| **O-05** | Hero sikli **necha marta** aylansin? | [K-1] «sikl yumshoq qaytadi»; 09-UI-SPEC §4.4 «cheksiz pulsatsiya» ni taqiqlaydi | Foydalanuvchi hero'da **qancha** turadi | ⛔ **Ko'rinib turganda cheksiz, ko'rinmasa TO'XTAYDI** (§5.6). Sabab: sun'iy chegara (masalan 3 sikl) foydalanuvchi hero'ga **qaytganda** uni muzlagan holatda qoldirardi; ko'rinuvchanlik esa **taxmin emas, o'lchov**. ⛔ **Tetigi:** arzon qurilmada batareya/jank **o'lchansa** — birinchi tuzatish sikl sonini emas, ⛔ **faza 2 dagi katak stagger'ini** (280ms → kamroq qadam) kamaytirish |
| **O-06** | Aloqa telefoni raqami **qaysi**? | §13.8 `landing.form.error.body` da `{phone}` platsholderi bor; footer'da aloqa bandi bor | ⛔ Real raqam **berilmagan** | ⛔ **[ASSUMED] Platsholder qoladi va qiymat `.env` dan** (`NEXT_PUBLIC_CONTACT_PHONE`). Sabab: raqamni matn katalogiga qotirsak, u **uchala tilda** takrorlanadi va o'zgarganda uch joyda tahrirlanardi. ⛔ **Tetigi:** buyurtmachi raqamni bergan kunda — **bitta** env qiymati; ⛔ raqam **yo'q** bo'lsa xato matni platsholdersiz shoxga tushadi (`landing.form.error.bodyNoPhone`) — ⛔ **bo'sh qavs KO'RSATILMAYDI** |
| **O-07** | ⭐ dalil bloki (§9.1 blok 4) **hero'da takrorlanadimi**? | [K-2] ⭐ copy hero'da **qulflangan**; brief §2.4 uni **alohida blok** ham qiladi | Takror **kuchaytiradimi** yoki **suyultiradimi** | ⛔ **HA, ikki joyda ham — LEKIN shakli har xil** [ASSUMED]. Hero'da — **bir qatorli** da'vo (qulflangan copy); blok 4 da — ⛔ **kengaytirilgan** shakl: nima kerak (NVR login-parol), nima kerak **emas** (yangi kamera, server, muhandis tashrifi). ⛔ **Tetigi:** UAT'da takror «bir xil gapni ikki marta o'qidim» hissi bersa — blok 4 **3-qadam seksiyasiga** qo'shiladi va alohida blok sifatida **yo'qoladi** |

---

## 19. Dizayn tizimi xulosasi (checker uchun jamlanma)

| Xossa | Qiymat |
|-------|--------|
| **Tool** | `none` (shadcn **ishlatilmaydi** — §3.1) |
| **Preset** | not applicable |
| **Component library** | Radix primitivlari + CVA, ⛔ **mahalliy `ui/` (10 primitiv — kengaymaydi; `Button` ga BITTA o'lcham qo'shiladi)** |
| **Icon library** | `lucide-react@1.27.0` (ISC) — ⛔ **yangi ikonka paketi yo'q** |
| **Font** | `--font-sans` (system stack) + `--font-mono` — ⛔ **veb-shrift YUKLANMAYDI** (LCP byudjeti) |
| **Bo'shliq** | 4-panjara: **4 · 8 · 12 · 16 · 24 · 32 · 48** (meros). Istisnolar: 44px nishon · 56px CTA · 20px karta ichki `x` (meros) + ⛔ **YANGI, sanoqli**: seksiya ritmi **64px** (mobil) / **96px** (desktop), ⛔ **aynan 1 faylda** (§8.2, G-land-5(c)) |
| **Tipografiya** | ⛔ **4 matn roli** (24 `text-2xl` / 18 `text-lg` / 14 `text-sm` / 12 `text-xs`) **+ bitta mexanik qulflangan hero-display registri** (`text-hero`, `clamp(28→44px)` — ⛔ **aynan 1 fayl / 1 element**, G-land-5(a); asos §7.1.1); ⛔ **2 og'irlik** (400, 600); ⛔ `text-display` **ISHLATILMAYDI**, `text-base`/`text-3xl`/`text-[`/`font-medium` — ⛔ **0** (§7, L-2/L-3/L-4) |
| **Rang 60/30/10** | 60% `--color-bg` (iliq `oklch(0.985 0.001 106)`) · 30% `--color-surface` (+`-muted`) · 10% `--color-accent` |
| **Aksent faqat** | brand yorlig'i · fokus halqasi · havolalar · faol til tugmasi (meros) · ⛔ **to'yingan fon AYNAN 3 joyda**: hero CTA, forma CTA, 3-qadam chizig'ining to'lgan qismi (§6.3) |
| **Destruktiv** | `--color-danger` — ⛔ **faqat forma xato bloki**; landing'da destruktiv **amal yo'q** |
| **Yangi rang tokeni** | ⛔⛔ **0** — sahnaning hamma rangi mavjud tokenlardan; uchala temada AA'dan o'tadi [L-13] |
| **Yangi tipografiya tokeni** | ⛔ **1**: `--text-hero` (+`--line-height`, +`--letter-spacing`) |
| **Yangi `@keyframes`** | ⛔ **1**: `sweep` (8 → 9); `enter` va `attention` ⛔ **qayta ishlatiladi** [L-10] |
| **Yangi npm paketi** | ⛔⛔ **YO'Q** — `dependencies` 18 nomda `deepEqual` [K-9, L-21] |
| **Temalar** | ⛔ **3 ta, meros olinadi** (`light`/`dark`/`sun`); ⛔ landing tema **qulflamaydi**, almashtirgich **ko'rsatmaydi** (§6.4) |
| **Primary CTA** | ⛔ **«Demo so'rang»** — ⛔ **sahifada YAGONA** birlamchi harakat [K-2]; `Button variant="default" size="hero"` |
| **Ikkilamchi CTA** | «Tizimga kirish» — `variant="secondary" size="lg"`; header'da `variant="ghost"` |
| **Bo'sh holatlar** | ⛔ **Yo'q** — landing statik kontent; ⛔ sahnaning «bo'sh» holati **yo'q** (server final-kadr chizadi) |
| **Xato holatlari** | ⛔ **2 ta**: `landing.form.error.body` (sabab+yo'l) · `landing.form.error.rateLimited`; ⛔ **5 validatsiya xabari** (§13.8) |
| **Destruktiv tasdiq** | ⛔ **Yo'q** — landing'da destruktiv amal yo'q |
| **Yangi copy kalitlari** | ⛔ **~119 ta**, uchala tilda; ⛔ ru **mustaqil tarjima**; ⛔ `uz-Cyrl.overrides.json` ga **1 yozuv** (`AI`) + `gen-cyrillic.test.mjs` regeksi — **JUFT** (§13.4) |
| **Registry safety** | ⛔ **Qo'llanmaydi** — shadcn ishlatilmaydi, uchinchi tomon registry **yo'q**, vendored blok **yo'q** |
| **Yangi darvozalar** | **G-land-1 … G-land-5**, har biri **sabotaj** bilan; ⛔ **1 yangi skript fayli + 2 vitest fayli** (§16.4, byudjet §18 O-01) |

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

*Phase: 10-landing-sbozor-uz*
*UI-SPEC yakunlandi: 2026-08-17 — `gsd-ui-researcher`*
*Upstream: `sketch-findings-bozor` skill (003-B — foydalanuvchi tasdiqlagan 2026-08-16, `references/landing-sehri.md`, `sources/003-landing-hero.html`), LANDING-BRIEF.md (§1–§7), ROADMAP Phase 10 (SC#1–SC#5 + Chegaralar), 09-UI-SPEC.md (motion/tema/tipografiya shartnomasi, darvoza mexanikasi), `frontend/src/app/globals.css` (9-fazadan keyingi HAQIQIY tokenlar), STATE.md (gate byudjeti, sabotaj darslari), CLAUDE.md (Tailwind 4 CSS-first, data-rezidentlik, litsenziya), `frontend/AGENTS.md` (Next 16 — `proxy.ts`, metadata konventsiyalari)*
