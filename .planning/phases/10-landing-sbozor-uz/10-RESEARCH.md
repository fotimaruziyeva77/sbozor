# Phase 10: landing-sbozor-uz — Tadqiqot

**Tadqiqot sanasi:** 2026-08-17
**Domen:** Next 16 route-guruhlari · SSG + 3 locale · anonim public endpoint · Telegram yetkazish · payload byudjeti · transliteratsiya
**Ishonch:** HIGH (asosiy topilmalarning hammasi shu sessiyada kodbazada mashina bilan o'lchandi)
**Til:** uz-Latn

---

## Xuloso

`10-UI-SPEC.md` (APPROVED) **NIMA** qurilishini to'liq qulflagan: 26 o'lchov, 5 ta `G-land-*` darvozasi, 10 ta [QULF] qaror, ~119 copy kaliti. Bu tadqiqot faqat **QANDAY** qurilishiga javob beradi va u SPEC'ning **mexanikasini** kodbazaga urib ko'radi.

Natija: SPEC'ning arxitektura yo'nalishi to'g'ri, uning tipografiya/keyframes/dependencies o'lchovlari **mustaqil ravishda tasdiqlandi** (`text-base` 7/7 to'lgan, `text-xl` 3/4, `text-display` aynan 2 fayl, 8 `@keyframes`, 18 `dependencies`, 81 SSG marshrut). ⛔ **Lekin beshta bloklovchi mexanik ziddiyat topildi** va ularning ikkitasi SPEC'ning ikki bandini bir-biriga qarshi qo'yadi:

1. ⛔⛔ **`useAuthStore()` provayder bo'lmasa `throw` qiladi** — `LocaleSwitcher` uni chaqiradi. SPEC §4.3 («marketing layout FAQAT `NextIntlClientProvider`») va §9.2 («`LocaleSwitcher` — tegilmaydi») **bir vaqtda bajarilmaydi**: `next build` prerender'da yiqiladi.
2. ⛔⛔ **`LocaleSwitcher` ning import grafi `api-client` → `api-types` → **butun zod** ni tortadi.** O'lchandi: o'sha chunk **280 KB xom / 69 KB gzip** — §4.3 nishonga olgan matn katalogidan (22–27 KB gz) **2,5–3 barobar katta**.
3. ⛔⛔ **`demonstratsiya` → `демонстратсия`** — SPEC §13.9 da QULFLANGAN satr semantik transliteratsiya defektini beradi va uni **birorta darvoza ushlamaydi** (chiqish sof kirill). L-12 ning «AI dan boshqa 0 defekt» da'vosi **noto'g'ri**.
4. ⛔ **`bot-service` HTTP qabul QILA OLMAYDI** — u sof long-polling, HTTP serveri va DB'si yo'q. «Demo-forma → bot-service» faqat `core-api` → Telegram Bot API (ayni bot tokeni) → admin chat sifatida o'qiladi.
5. ⛔ **`202 Accepted` + `{delivered: true}` + `delivery_failed` o'z-o'ziga zid** — 202 paytida yetkazilganlik noma'lum.

Ijobiy yangilik: **darvoza byudjeti muammosi (O-01) o'lchandi va u SPEC baholaganidan ~4 barobar arzon.** Barcha 22 skript darvozasi jami **2,83 s**, to'liq vitest (99 fayl / 1170 test) **172,47 s** → fayl boshiga **~1,74 s**. Yangi 1 skript + 2 vitest fayli ≈ **+4–5 s**, SPEC esa 15–30 s baholagan edi.

**Asosiy tavsiya:** Wave 0 da **ikki mexanik ziddiyatni (B-1, B-2) bitta qaror bilan yopish** — `marketing/locale-switcher.tsx` ni `shell/` dagidan mustaqil, **`api-client` ga tegmaydigan** anonim variant sifatida yozish (u §4.4 reyestriga **beshinchi klient oroli** bo'lib qo'shiladi va G-land-1(a) shu holda yoziladi). Shundan keyingina provayder ko'chirishiga (§4.3) o'tish — aks holda ko'chirish `next build` da yiqiladi va sabab «provayder refaktori buzuq» deb o'qiladi.

---

<user_constraints>
## Foydalanuvchi cheklovlari

⛔ `CONTEXT.md` **mavjud emas** (`has_context: false`) — bu fazada `/gsd-discuss-phase` bajarilmagan. Cheklovlar o'rniga **APPROVED `10-UI-SPEC.md`** turadi va u shartnoma sifatida o'qiladi.

### Qulflangan qarorlar (10-UI-SPEC §2 — K-1…K-10, sketch 003-B, foydalanuvchi tasdiqlagan 2026-08-16)

| # | Qulflangan qaror |
|---|------------------|
| **K-1** | Hero = **12s «jonli bozor» sikli**, 5 faza yorlig'i bilan; **video EMAS** (CSS/JS); reduced-motion'da **statik final-kadr** |
| **K-2** | Copy qulflangan: sarlavha · javob · ⭐ dalil · ishonch qatori (4 band) · CTA «Demo so'rang» (**yagona**) · ikkilamchi «Tizimga kirish» |
| **K-3** | **3-qadam** «qanday ishlaydi» — C variantining chiziq-to'lish naqshi, **hero EMAS**, sahifaning **3-seksiyasi** |
| **K-4** | `(marketing)` route-guruhi **mavjud Next.js ichida**; anonim root = landing; **SSG**, 3 til |
| **K-5** | Demo-forma → **admin Telegram-bot** (mavjud `bot-service`); **CRM yo'q** |
| **K-6** | **Lighthouse ≥95, LCP <1.5s** — birinchi ekran matni sahnani **kutmaydi** |
| **K-7** | ⛔ **Yolg'on raqam TAQIQ** — pilot holati «Karmana bozorida sinovda»; hero raqamlari **namunaviy** deb belgilanadi |
| **K-8** | **Maxfiylik siyosati sahifasi majburiy** (CCTV shaxsiy ma'lumot qonuni) |
| **K-9** | ⛔ **Yangi npm paketi TAQIQ**; landing **app tokenlaridan oqadi** |
| **K-10** | Mavjud `G-*` va `G-motion-*` darvozalari **buzilmaydi**; skan maydonlari kengaysa — **ONGLI** |

### Claude'ning ixtiyoridagi maydonlar (SPEC §18 — O-01…O-07 «rejalovchiga ochiq»)

- **O-01** `gate` byudjeti — ⛔ **shu tadqiqotda O'LCHANDI**, quyida §«Darvoza byudjeti»
- **O-02** Provayder ko'chirishi shu fazadami — SPEC: **HA**; ⛔ shu tadqiqot **shart qo'yadi** (B-1 avval)
- **O-03** Tema qulflanmaydi — meros olinadi (o'zgarmadi)
- **O-04** Demo ma'lumoti DB'ga yozilmaydi (o'zgarmadi)
- **O-05** Sikl ko'rinib turganda cheksiz (o'zgarmadi)
- **O-06** Aloqa telefoni `.env` dan (`NEXT_PUBLIC_CONTACT_PHONE`)
- **O-07** ⭐ dalil hero'da **va** blok 4 da, shakli har xil

### Ko'lamdan tashqarida (SPEC §17)

Kino-scroll · app skrinshotlari · pilot raqamlari · narx kalkulyatori · blog · ro'yxatdan o'tish · analitika/piksel · A/B test · `pathnames` lokalizatsiyasi · kursor-nuri · grain · parallax · avtoplay video · cookie-banner · CAPTCHA · `sonner` toast formada · tema almashtirgich · sticky header · chat-widget.
</user_constraints>

---

<phase_requirements>
## Faza talablari

⛔ **`.planning/REQUIREMENTS.md` da landing uchun REQ-ID YO'Q** [O'LCHANDI: `LAND`, `landing`, `marketing` skani → 0 natija; ROADMAP Phase 10: *«Requirements: TBD (plan bosqichida)»*].

⚠ **Rejalovchi uchun qaror:** talab identifikatorlari **shu fazada tug'iladi**. Mavjud prefikslar (FOUND / MARKET / CAM / CASH / BILL / RECON / AI / BOT) landing'ni qamramaydi. Tavsiya: **`LAND-01`…`LAND-05`** — ROADMAP SC#1…SC#5 bilan **bir-birga** xaritalanadi, chunki SC lar allaqachon o'lchanadigan shaklda yozilgan va `scripts/check-requirements-sync.mjs` darvozasi mavjud (`npm run requirements:check`).

| ID (tavsiya) | Tavsif (ROADMAP SC dan) | Tadqiqot qaysi topilma bilan qo'llab-quvvatlaydi |
|----|-------------|-------------------|
| **LAND-01** | `sbozor.uz/` (anonim root) landing ko'rsatadi, uchala tilda SSG; «Kirish» app loginiga olib boradi | §«Marshrut mexanikasi» — `(marketing)` guruhi, `generateStaticParams` merosi, `page.tsx` almashtirish; ⛔ B-1 (AuthProvider) |
| **LAND-02** | Hero 12s siklni o'ynaydi; video EMAS; reduced-motion'da statik final-kadr | §«Sahna mexanikasi» — jsdom cheklovlari (meros), taymer reyestri, LCP + `opacity:0` tuzog'i |
| **LAND-03** | Demo-forma yuborilganda so'rov admin Telegram-botga yetadi | §«Demo-forma yo'li» — ⛔ B-4/B-5, `AlertSender`, `EXEMPT_ROUTES`, rate-limit naqshi |
| **LAND-04** | Ishonch bloki + pilot holati halol, yolg'on raqam YO'Q | §«Copy mexanikasi» — G-land-4 uchun matn katalogi hosila skani |
| **LAND-05** | Lighthouse ≥95, LCP <1.5s, SEO meta/OG/structured data to'liq | §«Payload byudjeti» (o'lchangan chunk sonlari) + §«SEO fayl konventsiyalari» |
</phase_requirements>

---

## Loyiha cheklovlari (CLAUDE.md dan)

| Direktiv | 10-fazaga ta'siri |
|----------|-------------------|
| **Next.js 16.2.12**, `middleware.ts` → **`proxy.ts`** (Node runtime, Edge yo'q) | ⛔ Mavjud `frontend/src/proxy.ts` **tegilmaydi**; marketing guruhi uning matcher'iga **hech nima qo'shmaydi** |
| **Tailwind 4.3.3 CSS-first `@theme`**, `tailwind.config.js` YO'Q | `--text-hero` va `sweep` **`globals.css` `@theme`/`@layer`** ichiga yoziladi; ⛔ `@theme inline` TAQIQ (G-motion-4(b)) |
| **TypeScript 5.9.3** (7.x EMAS) | O'zgarmaydi |
| **`next-intl` 4.13.4**, 3 locale (uz-Latn / uz-Cyrl / ru) | Landing 32-chi fazoviy nomni ochadi; ⛔ ru **mustaqil tarjima** |
| **Data-rezidentlik** — shaxsiy ma'lumot O'zR qonuni ostida | ⛔ Demo-forma ma'lumoti **DB'ga yozilmaydi** (SPEC §12.5); maxfiylik sahifasi majburiy |
| **`float` for money TAQIQ** — `BIGINT` so'm ↔ `int` | Sahnadagi `2 306 000` — **matn**, hisob emas; `useCountUp` butun son bilan ishlaydi |
| **Naive datetime TAQIQ** — `TIMESTAMPTZ` + `ZoneInfo` | Landing sana ko'rsatmaydi; `sitemap.ts` `lastModified` — build vaqti |
| **GSD Workflow Enforcement** | Fayl o'zgartirishlar faqat `/gsd-execute-phase` orqali |

---

## Arxitektura mas'uliyat xaritasi

| Imkoniyat | Birlamchi qatlam | Ikkilamchi qatlam | Sabab |
|-----------|-----------------|-------------------|-------|
| Landing markup + copy | **Frontend Server (SSG)** | — | Uchala locale build vaqtida chiziladi; `setRequestLocale` bilan dinamiklik yopiladi |
| Hero final-kadr (LCP nomzodi) | **Frontend Server (SSG)** | — | `h1` klient JS'ga bog'lanmaydi — G-land-1(b) |
| Hero 12s sikli | **Browser / Client** | — | Taymer reyestri + `IntersectionObserver` + `visibilitychange` |
| Til almashtirish | **Browser / Client** | Frontend Server (URL prefiks) | Anonim holatda **faqat URL** almashadi — profil yozuvi yo'q |
| Demo-forma validatsiyasi | **Browser / Client** | **API / Backend** | Klient — tezkor signal; server — **yagona haqiqat** (`normalize_phone`) |
| Demo so'rovini yetkazish | **API / Backend** | — | ⛔ Telegram Bot API ga chiqish faqat serverdan; bot tokeni klientga **hech qachon** chiqmaydi |
| Anti-spam (honeypot + dwell) | **Browser / Client** | **API / Backend** (IP chegara) | Klient qatlamlari arzon lekin chetlab o'tiladi; **chegara serverda** |
| SEO metadata / OG / JSON-LD | **Frontend Server (SSG)** | — | `generateMetadata` + Server Component `<script type="application/ld+json">` |
| `sitemap.xml` / `robots.txt` | **Frontend Server** | — | Fayl konventsiyasi; `proxy.ts` matcher'idan tashqarida (nuqtali yo'l) |
| Shaxsiy ma'lumot saqlash | ⛔ **HECH QAYSI** | — | K-8 + SPEC §12.5: DB yozuvi yo'q, Telegram kanali — yozuvning o'zi |

---

## ⛔⛔ Bloklovchi topilmalar — rejalashtirishdan OLDIN hal qilinadi

### B-1: `useAuthStore()` provayder bo'lmasa `throw` qiladi — §4.3 va §9.2 bir vaqtda bajarilmaydi

**Dalil** [KOD: `frontend/src/lib/auth-store.ts`, oxirgi funksiya]:

```ts
export function useAuthStore(): AuthStore {
  const store = useContext(AuthContext);
  if (!store) {
    throw new Error("useAuthStore() faqat <AuthProvider> ichida ishlaydi");
  }
  return store;
}
```

**Chaqiruvchi** [KOD: `frontend/src/components/shell/locale-switcher.tsx:92`]:
`const { accessToken, updatePrincipal } = useAuthStore();`

**Ziddiyat:**

| SPEC bandi | Nima deydi |
|------------|------------|
| §4.3 | `(marketing)/layout.tsx` — ⛔ **faqat** `NextIntlClientProvider`, **faqat** `["common","landing"]` |
| §9.2 + §3.3 | Header'dagi til almashtirgich — `shell/locale-switcher.tsx`, ⛔ **tegilmaydi** |
| §4.4 | `LocaleSwitcher` ⛔ **beshinchi klient oroli EMAS** — «landing uni **import qiladi**» |
| **G-land-1(c)** | `(marketing)/layout.tsx` provayderiga uzatilgan nomlar **aynan** `["common","landing"]` |

⛔ Bu to'rtta band birga **`AuthProvider` siz** `LocaleSwitcher` ni render qilishni talab qiladi → `throw`. Va u **run-time flake emas**: `next build` SSG prerender'da klient komponentini serverda ham render qiladi, ya'ni **build yiqiladi** (`gate` ning oxirgi qadami).

**Yechim variantlari:**

| # | Yechim | Narxi | Baho |
|---|--------|-------|------|
| **A** | `(marketing)/layout.tsx` ga **`AuthProvider` ham** qo'shiladi | G-land-1(c) reyestri o'zgaradi; ⛔ **B-2 ni hal QILMAYDI** (zod baribir keladi) | ⛔ **Rad** — payload muammosining kattaroq yarmi qoladi |
| **B** | `locale-switcher.tsx` ga «provayder ixtiyoriy» shoxi (`useContext` to'g'ridan-to'g'ri, `null` da faqat URL almashtirish) | §3.3 «tegilmaydi» buziladi; ⛔ **B-2 ni ham hal qilmaydi** (`apiFetch` importi qoladi) | ⛔ **Rad** — ikkinchi muammoni ochiq qoldiradi |
| **C** | ⛔ **`components/marketing/locale-switcher.tsx`** — mustaqil, **anonim** variant: `usePathname`/`useRouter` (`@/i18n/navigation`) + `useLocale` + `LOCALE_LABELS`; ⛔ `api-client`, `auth-store`, `api-types` **import QILMAYDI** | §4.4 reyestri **4 → 5** klient oroliga chiqadi; SPEC §3.4 ga bitta qator qo'shiladi | ✅ **TAVSIYA** — B-1 va B-2 ni **bitta** o'zgarish bilan yopadi |

⛔ **C ning mexanik oqibati rejaga:** `G-land-1(a)` ning `deepEqual` reyestri **besh** faylni sanaydi (`hero-scene.tsx`, `step-line.tsx`, `reveal.tsx`, `demo-form.tsx`, **`locale-switcher.tsx`**), va `G-land-1(c)` **o'zgarmaydi** (`["common","landing"]` yetarli — yangi almashtirgich `common.languageLabel` dan boshqa hech nima o'qimaydi).

⚠ **`LOCALE_LABELS` muammosi:** u bugun `@/lib/api-types` da yashaydi (zod fayli). Yangi almashtirgich uni **import qilmasligi** kerak — aks holda B-2 qaytadi. ⛔ Yechim: yorliqlar (`O'zbekcha` / `Ўзбекча` / `Русский`) **marketing komponentida literal** yoziladi va bu **takror emas** — SPEC §9.2 «endonim» qoidasi ostida ular **tarjima qilinmaydi**, ya'ni ikkinchi manba drift bermaydi. Muqobil (agar rejalovchi takrorni istamasa): `LOCALE_LABELS` ni `api-types.ts` dan **zodsiz** modulga (`lib/locales.ts`) ko'chirish — **bitta** qator ko'chirish, `api-types.ts` undan re-export qiladi.

---

### B-2: `LocaleSwitcher` **69 KB gzip** zod grafini tortadi — §4.3 ning nishoni noto'g'ri joyda

**O'lchandi** (`.next/` build chiqishi, 2026-08-17):

| Chunk | Xom | ⛔ Gzip | Ichida |
|-------|-----|---------|--------|
| `3-nwl99v6lee6.js` | 280 KB | ⛔ **69 KB** | `meLocaleResponseSchema`, `sessionResponseSchema`, `apiErrorSchema`, `invalid_credentials`, `ZodError` → ⛔ **zod + `api-client` + `api-types`** |
| `0sxhqci3sd_90.js` | 71 KB | **21 KB** | `QueryClientProvider` + `nuqs` + `Toaster` → ⛔ **§4.3 ning HAQIQIY nishoni** |
| `3yojlanhcwnlf.js` | 39 KB | 12 KB | `NextIntlClientProvider` → landing'ga **kerak** |
| `23nd96eljgqh1.js` | 31 KB | 11 KB | `useForm` + `ZodError` → `react-hook-form` + resolver, forma uchun **kerak** |
| rootMain (5 chunk) | 446 KB | 129 KB | React + Next runtime → ⛔ **hech qanday refaktor bilan kamaymaydi** |

**Matn katalogi** [O'LCHANDI, mustaqil gzip]:

| Locale | Xom | Gzip |
|--------|-----|------|
| uz-Latn | 77 117 B | **21 726 B** |
| uz-Cyrl | 107 432 B | **24 954 B** |
| ru | 109 805 B | **26 942 B** |
| ⛔ **faqat `common`** | — | ⛔ **196 B** |

⛔ **Xulosa raqamlar bilan:** §4.3 to'g'ri muammoni ko'rgan, lekin **eng katta bo'lagini emas**. Landing'ning yutuqlari kattaligi bo'yicha:

1. ⛔ **`api-client` ni grafdan chiqarish — ~69 KB gz** (B-1 ning C yechimi bilan **birga keladi**)
2. ⛔ **Provayder ko'chirishi (rq + nuqs + sonner) — ~21 KB gz** (§4.3 ning o'z nishoni)
3. **Matn katalogini toraytirish — ~21–27 KB gz** (`common` + `landing` ≈ 2–4 KB gz qoladi)

⚠ **HALOLLIK BANDI:** bu sonlar **bugungi** build'ning chunk chegaralari. Refaktordan keyin Turbopack guruhlashni **qayta hisoblaydi** va aynan shu chegaralar saqlanishi **kafolatlanmagan**. ⛔ Shuning uchun «~110 KB tejaladi» **da'vosi berilmaydi** — reja `next build` route jadvalini **oldin va keyin** olib, farqni **son bilan** yozadi (SPEC §16.5, HUMAN-UAT).

⛔ **`LocaleSwitcher` ni landing'dan olib tashlash TAQIQ** — kirill davlat auditoriyasining o'qish sharti [MEROS: brief §4, SPEC §6.4]. Yechim almashtirgichni **olib tashlash** emas, uning **import grafini kesish** (B-1 / C).

---

### B-3: `demonstratsiya` → `демонстратсия` — QULFLANGAN copy'dagi semantik defekt

**O'lchandi** (`transliterate()` mustaqil chaqiruvi, joriy `uz-Cyrl.overrides.json` bilan):

```
"Namuna bozori · demonstratsiya"  ->  "Намуна бозори · демонстратсия"     ⛔ NOTO'G'RI (to'g'risi: демонстрация)
"AI band rastani aniqlaydi"       ->  "АИ банд растани аниқлайди"          ⛔ NOTO'G'RI (L-11 topgan)
```

⛔ `landing.scene.marketLabel` = «Namuna bozori · demonstratsiya» — **SPEC §13.9 da qulflangan** kalit. Ya'ni L-12 ning *«40 nomzod satrdan — AI dan boshqa 0 defekt»* da'vosi **noto'g'ri**: nomzodlar orasida SPEC'ning **o'z** copy jadvalidagi satr yo'q edi.

**Sinf kengroq** [O'LCHANDI — 46 nomzod so'z]:

| Defektli (`-tsiya` → `тсия`) | To'g'ri |
|------------------------------|---------|
| `demonstratsiya` · `prezentatsiya` · `registratsiya` · `informatsiya` · `identifikatsiya` · `avtorizatsiya` · `integratsiya` · `operatsiya` · `optimizatsiya` | `statistika` · `instruksiya` · `konversiya` · `analitika` · `texnologiya` · `konfidensial` · `avtomatik` |

⛔ **Darvoza buni USHLAMAYDI** va sabab mexanik: `gen-cyrillic.test.mjs` ning `allowed` regeksi **lotin harfi qolganini** tekshiradi; `демонстратсия` esa **sof kirill**. Bu `_comment_semantic` da nomlangan sinf (`autentifikatsiya` → `аутентификатсия` bilan **ayni**).

⚠ **Sof kirill `тс` ni yoppasiga taqiqlab bo'lmaydi** [O'LCHANDI: mavjud `uz-Cyrl.json` da `кетсангиз` va `муваффақиятсиз` — ikkalasi ham **to'g'ri** o'zbek shakllari].

**Yechim (ikkalasi ham sinaldi va ishlaydi):**

| # | Yechim | Natija | Baho |
|---|--------|--------|------|
| **A** | ⛔ **Copy tuzatish:** `demonstratsiya` → **`namoyish`** | `Намуна бозори · намойиш` ✅ | ✅ **TAVSIYA** — override o'smaydi, aglyutinatsiya tuzog'i (`_comment_agglutination`) ochilmaydi, so'z **o'zbekcha** |
| **B** | Override: `"demonstratsiya": "демонстрация"` | `Намуна бозори · демонстрация` ✅ | Ishlaydi, lekin har qo'shimchali shakl **alohida yozuv** talab qiladi |

⚠ **A varianti K-2/§13.9 ga tegadimi?** `landing.scene.marketLabel` K-2 ning **qulflangan olti bandiga kirmaydi** (K-2 = sarlavha · javob · ⭐ dalil · ishonch qatori · CTA · ikkilamchi CTA). §13.9 sahna matnlari — SPEC'ning **o'z [QAROR]** i, [QULF] emas. Ya'ni tuzatish **qulflangan shartnomani buzmaydi**.

#### ⛔ Rejaga majburiy Wave-0 vazifasi: transliteratsiya probasi

Landing'ning **~119 kaliti × 3 til** yozilgandan **keyin, commitdan oldin**:

```bash
node -e "import('./scripts/gen-cyrillic.mjs').then(m=>{ /* landing.* qiymatlarini transliterate qilib, natijadagi 'тс' larni sanash */ })"
```

⛔ **Yaxshiroq shakl — darvozaga aylantirish:** `landing-surface.test.mjs` ga tor, **hosila** tekshiruv qo'shiladi — `uz-Latn.json` ning `landing.*` qiymatlaridagi **`/[a-z]+ts[iy]/` naqshiga mos har token** `uz-Cyrl.overrides.json` `words` da **bo'lishi shart**. Bu `тс` ni yoppasiga taqiqlamaydi (o'zbek fe'llari `-tsa`/`-tsiz` naqshga tushmaydi) va SPEC §16.2 ning «HOSILA qamrov» qoidasiga mos.

#### ⚠ Meros defekt — 10-fazaning ko'lamiga KIRMAYDI

[O'LCHANDI] Mavjud katalogda **`Deklaratsiya` (×3, `collect.shiftConfirmBody`)** va **`deklaratsiya` (×1, `billing.emptyShiftsHint`)** override'siz → bugun `Декларатсия` chiqadi (to'g'risi `Декларация`).

⛔ **Bu 10-fazada TUZATILMAYDI** [MEROS: 08-20 scope-boundary presedenti]. `deferred-items.md` ga yoziladi. ⚠ Lekin agar reja yuqoridagi **darvozani** `landing.*` dan kengroq yozsa — u **darhol qizaradi** va bu 10-fazaning nuqsoni bo'lmagan holda uni bloklaydi. ⛔ **Darvoza `landing.*` bilan chegaralanishi SHART.**

#### `AI` juftligi — aniq qatorlar

| # | Fayl | Aniq o'zgarish |
|---|------|----------------|
| 1 | `frontend/messages/uz-Cyrl.overrides.json` → `words` | `"AI": "AI",` (mavjud `"IR": "IR",` / `"Telegram": "Telegram"` bloki yoniga) |
| 2 | `frontend/scripts/gen-cyrillic.test.mjs:502` → `allowed` | `\b(?:Hikvision\|WireGuard\|WebRTC\|ISAPI\|RTSP\|HLS\|MSE\|NVR\|NTP\|VPN\|GMT\|IP\|IR\|Telegram)\b` → ichiga **`AI`** qo'shiladi |

⛔ **Ikkalasi JUFT** [`_comment_acronyms`: *«biri to'ldirilib ikkinchisi unutilsa, o'sha test qizaradi va bu KUTILGAN xulq»*].
✅ **Tasdiqlandi:** ikkalasi bilan → `AI банд растани аниқлайди`, `allowed` regeksidan keyin qoldiq `" банд растани аниқлайди"` (lotin harfi **yo'q**).

---

### B-4: `bot-service` HTTP qabul qila olmaydi — SC#3 ning yagona ishlaydigan o'qilishi

**O'lchandi** [KOD: `services/bot-service/app/main.py`, `settings.py`]:

| Fakt | Dalil |
|------|-------|
| ⛔ **HTTP serveri YO'Q** | `dp.start_polling(bot)` — long-polling; *«WEBHOOK QURILMAYDI — LONG-POLLING (DQ-1)»* |
| ⛔ **DB ulanishi YO'Q va bu QAROR** | `settings.py`: *«bu servisda u ATAYIN yo'q… `test_runtime_deps.py` da MEXANIK»* (D-08/1) |
| ⛔ **Oqim faqat bir tomonga** | `CoreClient` → `core-api` ichki API; teskarisi **umuman yo'q** |
| ✅ **Bot tokeni umumiy** | `settings.py`: *«`TELEGRAM_BOT_TOKEN` (A1: alert supurgisi bilan AYNAN BIR XIL token)»* |

⛔ **Ya'ni `core-api` → `bot-service` HTTP chaqirig'i MAVJUD BO'LMAGAN yuza.** Reja uni loyihalasa, ijro paytida to'siqqa uriladi.

**Mavjud mexanizmlar va ularning yaroqliligi:**

| Mexanizm | Fayl | Landing uchun yaroqlimi |
|----------|------|--------------------------|
| ✅ **`AlertSender.send_message()`** | `app/services/alerts.py` | ⛔ **HA** — `httpx` bilan to'g'ridan-to'g'ri Bot API; `telegram_bot_token` + `telegram_chat_id` (`Settings.alerts_enabled`) |
| ⛔ `notification_outbox` | `app/repositories/outbox_repo.py` | ⛔ **YO'Q** — tenant kesimida (`market_id` + RLS); anonim so'rovda bozor yo'q; SPEC §12.5 DB yozuvini taqiqlaydi |
| ⛔ `/internal/bot/*` | `app/api/internal/bot.py` | ⛔ **YO'Q** — bu **bot → core-api** yo'nalishi (servis tokeni bilan) |

⚠ **Muhim mexanik nuqta:** `AlertSender` bugun ⛔ **faqat `worker` jarayonida** quriladi [KOD: `app/worker.py:819 _alert_sender()`]; `app/main.py` ning `lifespan` ida u **yo'q** [O'LCHANDI: `app.state` ga `settings`/`engine`/`sessionmaker`/`cache`/`enqueue_discovery` yoziladi, jo'natuvchi **yozilmaydi**].

**Ikki yo'l:**

| # | Yo'l | Mexanika | Baho |
|---|------|----------|------|
| **A** | ⛔ **API `lifespan` ida `AlertSender`** — `app.state.alert_sender` | `worker.py::_alert_sender()` **tarjima funksiyasi qayta ishlatiladi**, nusxa olinmaydi; `finally` da `aclose()` | ✅ **TAVSIYA** — `delivered` ni **halol** biladi (B-5) |
| **B** | Taskiq job (`enqueue_discovery` naqshi) → worker jo'natadi | `nvr.py::_enqueue` naqshi mavjud; broker `lifespan` da allaqachon ochiq (`await broker.startup()`) | ⛔ **Rad** — 202 paytida yetkazilganlik **noma'lum**, ya'ni SPEC §12.5 ning «yolg'on aytilmaydi» bandi bajarilmaydi |

⛔ **`AlertSender` yuzasi kengaytirilMAYDI** — `tests/integration/test_alerting.py` uning metodlarini sanaydi va `alerts.py` ning 1-taqig'i (rasm biriktiruvchi metod **yo'q**) mexanik. Demo so'rovi **matn** sifatida yuboriladi, `send_message()` **o'zgarmaydi**.

⚠ **Chat manzili — rejaning qarori.** `telegram_chat_id` bugun **ops/alert kanali**. Sotuv so'rovlarini o'sha yerga tushirish MVP uchun ishlaydi, lekin ops shovqinini aralashtiradi. ⛔ Tavsiya: `Settings` ga **ixtiyoriy** `demo_request_chat_id: str = ""` qo'shiladi va **bo'sh bo'lsa `telegram_chat_id` ga tushadi** — bir qatorlik xarajat, keyin ajratish **konfiguratsiya** qarori bo'lib qoladi, kod qarori emas.

---

### B-5: `202 Accepted` + `{delivered: true}` + `delivery_failed` — o'z-o'ziga zid

SPEC §12.5 uchtasini birga so'raydi:

> **Javob:** `202 Accepted` + `{ delivered: true }` · **Xato kodlari:** … `delivery_failed` · ⛔ *«Yetkazib bo'lmasa — `delivery_failed` qaytadi… «Yubordik» deb yolg'on aytilmaydi»*

⛔ **202** = «qabul qildim, hali ishlamadim» → o'sha lahzada `delivered` **noma'lum** va `delivery_failed` **qaytarib bo'lmaydi**.

⛔ **[QAROR — rejaga tavsiya]:** **sinxron yuborish + `200 OK`**. Sabab **mexanik, did emas**: SPEC'ning o'z xato shartnomasi (`delivery_failed` → foydalanuvchi telefon raqamni ko'radi) **faqat** natija ma'lum bo'lganda bajariladi. ⚠ Narxi: so'rov Telegram javobini kutadi (`AlertSender` da `tenacity` retry bor) — **bu qabul qilinadi**, chunki bu **foydalanuvchi kutayotgan** amal (forma yuborish), fon vazifasi emas.

⛔ **SPEC buni bloklamaydi** — §12.5 oxirida so'zma-so'z: *«Bu UI-SPEC backend shaklini QULFLAMAYDI… Yakuniy shakl — 10-faza rejasining backend vazifasi»*.

---

## Marshrut mexanikasi — `(marketing)` guruhi qanday tug'iladi

### Bugungi holat [O'LCHANDI]

```
frontend/src/app/
├── favicon.ico
├── globals.css
└── [locale]/
    ├── layout.tsx          ← ILDIZ layout (<html>), 5 provayder, generateStaticParams, FOUC skripti
    ├── page.tsx            ← redirect({href:"/dashboard"})  ⛔ O'CHIRILADI
    ├── (app)/              ← 24 sahifa; layout.tsx "use client" (sessiya darvozasi)
    └── (auth)/             ← 3 sahifa; layout.tsx Server Component (tor ustun)
```

⛔ **`[locale]/` ildizida `layout.tsx` va `page.tsx` dan boshqa fayl YO'Q** [O'LCHANDI: `ls`]. ⛔ `not-found.tsx`, `error.tsx`, `global-error.tsx`, `loading.tsx` — ⛔ **birortasi ham mavjud emas** [O'LCHANDI: `find` → 0 natija]. Ya'ni SPEC §4.3 ning *«provayderlarsiz qoladigan birorta mavjud sahifa yo'q»* da'vosi **tasdiqlandi**.

### `/uz` → `/uz/dashboard` 307 qayerdan keladi

⛔ **`proxy.ts` dan EMAS.** Zanjir:

1. `proxy.ts` → `createMiddleware(routing)` — ⛔ **faqat locale prefiksini** hal qiladi (`/` → `/uz`, `localePrefix.mode: "always"`)
2. `app/[locale]/page.tsx:29` → `redirect({ href: "/dashboard", locale })` — ⛔ **shu yerda** 307
3. `(app)/layout.tsx` (`"use client"`) → sessiya yo'q bo'lsa `router.replace("/login")`

⛔ Ya'ni landing `page.tsx` ni almashtirgach, `/uz` **darhol** landing bo'ladi va `proxy.ts` **umuman tegilmaydi**.

### Route-guruh — Next 16 rasmiy ogohlantirishlari

[CITED: `node_modules/next/dist/docs/01-app/03-api-reference/03-file-conventions/route-groups.md`]

| Ogohlantirish | 10-fazaga ta'siri |
|---------------|-------------------|
| *«**Full page load**: … **only** applies to multiple root layouts»* | ✅ **Xavf yo'q** — `[locale]/layout.tsx` **yagona** root layout bo'lib qoladi (`<html>` faqat unda); `(marketing)`/`(app)`/`(auth)` — **ichki** guruhlar. Landing → `/login` klient navigatsiyasi bo'lib qoladi |
| *«**Conflicting paths**: routes in different groups should not resolve to the same URL path»* | ⛔ **HAQIQIY XAVF:** `(marketing)/page.tsx` yaratilib `[locale]/page.tsx` **o'chirilmasa** — ikkalasi ham `/{locale}` ga tushadi va **build xatosi**. G-land-1(d) aynan shuni qulflaydi |
| *«**Top-level root layout**: … make sure your home route (/) is defined within one of the route groups»* | ✅ Bajariladi — `(marketing)/page.tsx` |

### SSG merosi — o'lchangan

⛔ `generateStaticParams()` **`[locale]/layout.tsx:26-29` da** yashaydi va `(marketing)` uni **avtomatik meros oladi** — bu bugun **isbotlangan**: `.next/prerender-manifest.json` da ⛔ **81 prerendered marshrut** (27 `page.tsx` × 3 locale), va `(app)`/`(auth)` guruhlarining **birortasida ham** `generateStaticParams` yo'q.

**Har sahifa uchun majburiy naqsh** [KOD: `layout.tsx:61` va `page.tsx:27`]:

```tsx
export default async function Page({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  if (!hasLocale(routing.locales, locale)) notFound();
  setRequestLocale(locale);          // ⛔ BIRINCHI — busiz sahifa DINAMIK bo'lib qoladi
  ...
}
```

⛔ `cookies()`, `headers()`, `searchParams` — landing'da **ishlatilmaydi** (SSG'ni buzadi).

### Locale prefikslari — reja uchun aniq qiymatlar

[KOD: `frontend/src/i18n/routing.ts`]

| `[locale]` segmenti | URL prefiksi |
|---------------------|--------------|
| `uz-Latn` (default) | `/uz` |
| `uz-Cyrl` | `/uz-cyrl` |
| `ru` | `/ru` |

⛔ **`localeDetection: false`** (D-15) — brauzer tili **hech qachon** so'ralmaydi. ⛔ Landing havolalari `@/i18n/navigation` ning `Link` idan olinadi, `next/link` dan **emas** (grep darvozasi bilan qulflangan).

---

## Provayder ko'chirishi (§4.3) — mexanik reja

### Bugungi ildiz layout [KOD: `layout.tsx:112-121`]

```tsx
<NextIntlClientProvider messages={messages}>   {/* messages = TO'LIQ katalog */}
  <NuqsAdapter>
    <QueryProvider>
      <AuthProvider>
        {children}
        <Toaster position="top-center" richColors />
      </AuthProvider>
    </QueryProvider>
  </NuqsAdapter>
</NextIntlClientProvider>
```

### `NextIntlClientProvider` ni toraytirish — API tasdiqlandi

[VERIFIED: `node_modules/next-intl/dist/types/shared/NextIntlClientProvider.d.ts`, next-intl **4.13.4**]

```ts
type Props = Omit<ComponentProps<typeof IntlProvider>, 'locale'> & { locale?: Locale };
```

⛔ `messages` — **oddiy obyekt**; o'rnatilgan `pick` **yo'q**. Toraytirish qo'lda:

```tsx
const messages = await getMessages();          // server tomonda TO'LIQ — bepul
<NextIntlClientProvider messages={{ common: messages.common, landing: messages.landing }}>
```

⚠ **Ikkita xatti-harakat rejaga muhim:**
1. ⛔ **`messages` berilmasa** — `NextIntlClientProviderServer` uni **server kontekstidan meros oladi** (ya'ni **to'liq katalog** qaytadi). Marketing layout `messages` ni **oshkora** berishi SHART.
2. ✅ **Ichki provayder tashqarisini SOYALAYDI** — ya'ni §4.3 ning «qaytarish tetigi» (ildiz layout tegilmasa, landing ichkarida ikkinchi provayder e'lon qiladi) **mexanik ravishda ishlaydi**.

### Nima qayerga tushadi

| Fayl | Keyin |
|------|-------|
| `app/[locale]/layout.tsx` | `<html>` + `data-theme` + `suppressHydrationWarning` + FOUC skripti + `<body>` + `generateStaticParams` + `generateMetadata`. ⛔ **Beshala provayder chiqadi** |
| `components/shell/app-providers.tsx` | ⛔ **YANGI** — beshala provayderning **yagona** ta'rifi (`"use client"`) |
| `app/[locale]/(app)/layout.tsx` | ⛔ Allaqachon `"use client"` — `<AppProviders>` bilan o'raladi. ⚠ **Diqqat:** hozirgi `AppLayout` ning o'zi `useAuthStore()` va `useTranslations()` chaqiradi, ya'ni u provayderlar **ICHIDA** bo'lishi kerak → `AppProviders` **tashqarida** turishi va `AppLayout` mazmunini o'rashi SHART (ikkitasini bitta faylda aralashtirish provayder ichida hook chaqirish xatosini beradi) |
| `app/[locale]/(auth)/layout.tsx` | Server Component qoladi, `<AppProviders>` ni render qiladi (klient komponentini serverdan render qilish qonuniy) |
| `app/[locale]/(marketing)/layout.tsx` | ⛔ **Faqat** `NextIntlClientProvider`, **faqat** `{common, landing}` |

⚠ **FOUC skripti ildizda QOLADI** — dalil `layout.tsx:96-98` izohida: *«Skript locale'ga ham, sessiyaga ham bog'liq emas — SSG buzilmaydi»*. U `<html data-theme>` ni birinchi bo'yashdan oldin o'zgartiradi, ya'ni `<html>` bilan **bir faylda** turishi shart. ⛔ Landing tema almashtirgichni ko'rsatmaydi, lekin **temani meros oladi** (§6.4) — skript kerak.

### `(app)` / `(auth)` regressiya xavfi — o'lchangan darajada tor

| Xavf | Holat |
|------|-------|
| Provayder tartibi buziladi | ⛔ `AppProviders` da tartib **aynan ko'chiriladi**: i18n → nuqs → query → auth → Toaster (`layout.tsx:105-110` izohi sabab beradi: `AuthProvider` eng ichkarida, `QueryProvider` `subscribeSessionReset` ni ulaydi) |
| `Toaster` joyi o'zgaradi | ⛔ `Toaster` `AuthProvider` **ichida**, `{children}` **yonida** — nusxa aynan bo'lishi shart |
| Provayder yo'qolgan sahifa qoladi | ✅ ⛔ **Yo'q** — `[locale]/` ildizida boshqa sahifa **mavjud emas** [O'LCHANDI] |
| `not-found` / `error` provaydersiz qoladi | ✅ ⛔ **Fayl mavjud emas** — Next standarti ishlaydi va u tarjimasiz |

---

## Payload byudjeti — o'lchangan bazaviy

| O'lchov | Qiymat | Manba |
|---------|--------|-------|
| Prerendered marshrutlar | ⛔ **81** | `.next/prerender-manifest.json` |
| `page.tsx` soni | 27 | `find` |
| Root main chunk (har marshrut) | 446 KB xom / **129 KB gz** (5 fayl) | `build-manifest.json` + gzip |
| ⛔ zod + api-client chunk | 280 KB xom / **69 KB gz** | chunk skani |
| ⛔ rq + nuqs + sonner chunk | 71 KB xom / **21 KB gz** | chunk skani |
| next-intl chunk | 39 KB xom / **12 KB gz** | chunk skani |
| rhf + resolver chunk | 31 KB xom / **11 KB gz** | chunk skani |
| Matn katalogi (gz) | 21,7 / 25,0 / 26,9 KB | mustaqil gzip |
| Fazoviy nomlar / kalitlar | **31** / **1373** | JSON skani |

⛔ **Reja uchun majburiy o'lchov (SPEC §16.5):**

```bash
npm --prefix frontend run build          # OLDIN — route jadvalini saqlash
# ... o'zgarishlar ...
npm --prefix frontend run build          # KEYIN — farqni SON bilan yozish
```

⚠ Landing `+3` prerendered marshrut qo'shadi (`maxfiylik` × 3 locale); root uchtasi **almashtiriladi**, qo'shilmaydi → **81 → 84**.

---

## Sahna mexanikasi — LCP va hidratatsiya

### ⛔ LCP tuzog'i: `.motion-enter` `opacity: 0` dan boshlanadi

[KOD: `globals.css:294-308`]

```css
@keyframes enter { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
.motion-enter { animation: enter var(--motion-base) var(--ease-out) both; animation-delay: calc(var(--i, 0) * 60ms); }
```

⛔ **Chrome'ning LCP algoritmi `opacity: 0` elementni «chizilgan» deb hisoblamaydi** [ASSUMED — spetsifikatsiya matni bu sessiyada tekshirilmadi]. Ya'ni `h1` ga `.motion-enter` berilsa, LCP **`--i × 60ms + 250ms`** ga suriladi.

⛔ **SPEC §5.4 aynan shuni buyuradi:** *«Hero kirish ketma-ketligi (`--i`: brand → h1 → **lid** → CTA → ⭐ → ishonch)»* — ya'ni `h1` da `--i: 1` → **60 + 250 = ~310 ms** kechikish.

⚠ **Baho:** 1,5 s byudjetida 310 ms **halokatli emas**, lekin u **sof yo'qotish** va u LCP nomzodini klient JS'iga emas, **CSS animatsiyasiga** bog'laydi (G-land-1 buni **ushlamaydi** — u `"use client"` ni izlaydi).

⛔ **Tavsiya:** `h1` ga ⛔ **`--i: 0`** beriladi (kechikish 0, faqat 250 ms davomiylik) yoki `h1` `.motion-enter` **umuman olmaydi** va ketma-ketlik `brand` dan boshlab pastdagilarga qo'llanadi. Reja qaysi variantni tanlasa — **HUMAN-UAT da LCP soni bilan yopiladi**.

### Sikl davomiyligi — SPEC ichida nomuvofiqlik

⛔ SPEC §5.5 fazalari: 0–2,6 · 2,6–5,3 · 5,3–8,3 · 8,3–10,0 · 10,0–**13,5** s → ⛔ **haqiqiy sikl 13,5 s**, «12s» esa **nom**. G-land-2(b) buni to'g'ri yozgan (`13 500ms`). ⛔ Reja test kutilmalarida **13500** ishlatishi shart, 12000 emas.

### jsdom cheklovlari — MEROS, qayta o'lchanmadi

[MEROS: `09-RESEARCH.md` Tuzoq 1, O'LCHANDI 2026-08-17, jsdom 30.0.1 + vitest 4.1.10]

| Nima | jsdom'da |
|------|----------|
| `window.matchMedia` | ⛔ **YO'Q** — har testda `vi.stubGlobal` bilan stub |
| `Element.animate`, `document.getAnimations()` | ⛔ **YO'Q** |
| `getBoundingClientRect()` | ⛔ **0 qaytaradi** |
| Tailwind sinfidan `getComputedStyle` | ⛔ **`"auto"`** — sinf nomi tasdiq uchun **yaroqsiz** |
| `requestAnimationFrame` | ✅ **BOR** va `vi.useFakeTimers()` uni **patch qiladi** |
| `IntersectionObserver` | ⛔ **YO'Q** — `vi.stubGlobal("IntersectionObserver", ...)` bilan qo'lda mock |

⛔ **Oqibat G-land-2 ga:** «final-kadr» tasdiqlari **DOM matni va atributlari** ustida o'lchanadi (`2 306 000` matni, `data-state="unpaid"` kabi atribut), ⛔ **sinf nomi yoki hisoblangan uslub ustida EMAS**.

⛔ **Oqibat G-land-2(e) ga:** `IntersectionObserver` mock'i **`observe`/`disconnect` chaqiruvlarini sanashi** va callback'ni qo'lda ateshlashi kerak — jsdom real kesishuv hisoblamaydi.

### `container-type: inline-size` + `100cqw`

⛔ SPEC §5.3: `@keyframes sweep { from{translateX(0)} to{translateX(100cqw)} }`, xarita konteynerida `container-type: inline-size`.

⚠ **Ikki texnik eslatma:**
1. `cqw` **eng yaqin konteyner ajdodga** nisbatan hal bo'ladi. Nur chizig'i xarita konteynerining **farzandi** bo'lishi shart — konteynerning **o'zi** bo'lsa qiymat o'z-o'ziga havola qilardi.
2. `container-type: inline-size` ⛔ **inline o'qda o'lcham containment** beradi — konteyner kengligi **kontentiga bog'liq bo'lmasligi** kerak. Rasta gridi ota-onadan kenglik oladi → xavf past, lekin `width: fit-content` kabi qiymat qo'shilsa sahna **yopishib qoladi**.
3. Brauzer qo'llab-quvvatlashi (Chrome 105+ / Safari 16+ / Firefox 110+) — [ASSUMED], SPEC dan ko'chirildi, mustaqil tasdiqlanmadi. ⛔ SPEC'ning zaxira yo'li (mount'da `--sweep-distance` ni `offsetWidth` dan bir marta yozish) **saqlanadi**.

---

## Demo-forma yo'li — to'liq mexanika

### Anonim marshrut — qanday qabul qilinadi

**O'lchandi:** bugun `services/core-api/app/api/v1/` da **26 modul**, ⛔ **birortasi ham anonim emas** (L-25 tasdiqlandi).

⛔ **Mexanizm mavjud va u aniq:** `tests/tenancy/test_cross_tenant.py:270` — **`EXEMPT_ROUTES: dict[str, str]`**, sabab satri **majburiy** va u ⛔ **`EXEMPT_REASON_PREFIXES = ("auth bootstrap", "global", "health")`** dan biri bilan **boshlanishi shart** (`test_exempt_reasons_use_a_known_category`).

⛔ Landing marshruti → **`"global"`** toifasi (tenant chegarasidan tashqarida).

⛔⛔ **ISTISNO BEPUL EMAS.** `EXEMPT_ROUTES` docstringi so'zma-so'z:

> *«DIQQAT — ISTISNO MARSHRUTNI MATRITSADAN TO'LIQ CHIQARADI, faqat "404 qaytarsin" da'vosidan emas: tokensiz/buzilgan/muddati o'tgan token testlari ham unga qo'llanmaydi… Istisno qo'shgan odam bu qamrovni ham ko'chirishi SHART — aks holda marshrut "istisno" degan so'z bilan butunlay sinovsiz qolardi.»*

⛔ **Ya'ni reja MAJBURIY ravishda `tests/integration/test_demo_request.py` (yoki shunga o'xshash) yozadi** va u **kamida** quyidagilarni o'lchaydi (`/internal/self-check` va `/internal/live-authz` presedenti):

| # | Da'vo |
|---|-------|
| 1 | Autentifikatsiyasiz **muvaffaqiyat** (bu marshrutning **butun ma'nosi**) |
| 2 | Javobda bozor identifikatori/nomi/topologiyasi ⛔ **umuman yo'q** |
| 3 | ⛔ `Set-Cookie` **yo'q** (sessiya yuzasi ochilmaydi) |
| 4 | Chegaradan oshganda **429 `rate_limited`** |
| 5 | Noto'g'ri telefon → **422 `invalid_phone`** |
| 6 | Honeypot to'ldirilgan → ⛔ **jim muvaffaqiyat**, Telegram'ga **0 chaqiruv** |
| 7 | Yetkazish yiqilganda → **`delivery_failed`** va DB'da ⛔ **0 yangi qator** |

⚠ **Boshqa darvozalarga ta'siri — o'lchandi:**

| Darvoza | Ta'sir |
|---------|--------|
| `test_route_coverage.py::test_no_unclassified_routes` | ✅ Yangi marshrutda **yo'l parametri yo'q** → `PARAM_FILLERS` **tegilmaydi** |
| `MINIMUM_MATRIX_ROUTES = 80` | ✅ `>=` shart — istisno marshrut sanoqqa **kirmaydi**, chegara **tegilmaydi** |
| `QUERY_PARAM_ROUTES` | ✅ **Tegilmaydi** — `POST` + JSON tanasi, query parametri yo'q |
| `test_personal_data_coverage.py` | ✅ **Qamramaydi** — u ⛔ **`GET` javob modellarini** skanerlaydi (`PERSONAL_FIELDS = {vendor_name, phone, full_name}`), demo javobi esa `{delivered: bool}`. ⚠ **Lekin `phone` SO'ROV tanasida** — reja buni `EXEMPT_ROUTES` sababida **oshkora yozishi** kerak |
| `test_delivery_surface.py` | ⚠ OpenAPI ustidan ishlaydi — reja tekshirsin |

### Rate-limit — mavjud naqsh, yangi mexanizm YO'Q

[KOD: `services/core-api/app/security/ratelimit.py`]

⛔ **`_bump(cache, key, limit, window)`** — `INCR` + `EXPIRE(nx=True)` bitta pipeline'da. Uch mavjud iste'molchi: `check_login_rate` (telefon 10 / IP 50, 15 daq), `check_nvr_test_rate` (3 / 15 daq, `market_id:host` kesimi), `check_bot_resolve_rate` (5 / 15 daq, `telegram_user_id` kesimi).

⛔ **Landing uchun to'g'ri shakl — `check_bot_resolve_rate` ning aynan nusxasi:**

```python
DEMO_REQUEST_LIMIT = 5              # rejaning qarori
DEMO_REQUEST_WINDOW_SECONDS = 15 * 60
_DEMO_REQUEST_KEY = "rl:demo_request:"      # rl:demo_request:<ip>
```

⚠ **Uch mexanik band, hammasi mavjud naqshdan:**
1. ⛔ **Valkey yo'q bo'lsa — urinish O'TKAZILADI** (`RedisError` → `log.warning` → `return`). Bu **uchala** mavjud chaqiruvda bir xil qaror; teskarisi (fail-closed) demo formani Valkey uzilishida **butunlay o'ldirardi**.
2. ⛔ **IP manbasi** — `auth.py:118` da *«So'rov manbai IP'si (audit va rate-limit uchun)»* yordamchisi **allaqachon bor**; reja uni **qayta yozmaydi**.
3. ⛔ **Telefon raqami kalitga QO'YILMAYDI** — `_BOT_RESOLVE_KEY` docstringi (T-07-41): telefon Valkey'ga, u yerdan xotira dumpiga tushardi. ⛔ **Kesim faqat IP.**

### Telefon normalizatsiyasi — qo'lda yozilmaydi

[KOD: `packages/sbozor-core/sbozor_core/phone.py`]

```python
__all__ = ["DEFAULT_REGION", "InvalidPhoneError", "normalize_phone"]
```

⛔ `phonenumbers` + `DEFAULT_REGION = "UZ"` + `is_valid_number()`. Docstring so'zma-so'z: *«Regex bilan QILINMAYDI (Don't Hand-Roll)»*. ⛔ Server `normalize_phone(raw)` ni **chegarada** chaqiradi va `InvalidPhoneError` → **422 `invalid_phone`**.

⚠ **Klient tomonda** [O'LCHANDI]: `frontend/src/` da telefon formatini tekshiradigan **birorta** regex/sxema **yo'q** — `login-form.tsx:69` faqat `z.string().trim().min(1)`. ⛔ **Tavsiya: klientda ham qattiq regex yozilmaydi** — raqam sanog'i (`≥9 raqam`) + SPEC §13.8 ning `phoneInvalid` yordam matni yetadi. Qattiq klient regeksi serverning `phonenumbers` qabul qiladigan raqamlarini rad etib, **ikkinchi haqiqat manbai** tug'dirardi (D-01 ning buzilishi).

### Xato kodlari zanjiri — rejaga ochiq qaror

[KOD: `frontend/scripts/error-codes.test.mjs`] backend kod ro'yxatlarini frontend ko'zgusiga va tarjima kalitlariga bog'laydi. Bugun **oltita** nomlangan juftlik (`MARKET_ERROR_CODES`, `NVR_ERROR_CODES`, `CAPTURE_ERRORS`, `ZONE_ERRORS`, `BILLING_ERRORS`, import/wizard kodlari). ⛔ Reyestr **avtomatik kashf qilinmaydi** — fayl yo'llari testda **literal**.

| Variant | Narxi | Baho |
|---------|-------|------|
| **A** — yangi `DEMO_ERROR_CODES` registri + frontend ko'zgu + `error-codes.test.mjs` ga juftlik | Ikki yangi modul + darvoza tahriri | ✅ **TAVSIYA** — to'rt kod (`rate_limited`, `invalid_phone`, `validation_error`, `delivery_failed`) darvoza ostida qoladi |
| **B** — `demo-form.tsx` `detail` ni mahalliy `switch` bilan xaritalaydi | Nol qo'shimcha fayl | ⚠ Darvozada **ko'r nuqta**: backend kodni o'zgartirsa forma jim «Xatolik» ga tushardi — bu D-02 ning buzilishi |

---

## SEO va fayl konventsiyalari

### `sitemap.ts` / `robots.ts` — bugun MAVJUD EMAS

[O'LCHANDI: `find src/app -name "sitemap*" -o -name "robots*"` → **0 natija**; `public/` da `.gitkeep` va `vendor/` dan boshqa hech nima yo'q]

⛔ Ikkalasi ham **`src/app/` ildizida** (`[locale]/` **ICHIDA EMAS**), sabab `proxy.ts:17` matcher'i: `"/((?!api|_next|_vercel|.*\\..*).*)"` — ⛔ **nuqtali yo'llar chetlab o'tiladi**, ya'ni `/sitemap.xml` va `/robots.txt` ga locale prefiksi **qo'shilmaydi**.

**`sitemap.ts` — `hreflang` shakli** [CITED: Next 16 `sitemap.md`]:

```ts
import type { MetadataRoute } from 'next'
export default function sitemap(): MetadataRoute.Sitemap {
  return [{ url: '...', lastModified: new Date(),
            alternates: { languages: { /* locale -> URL */ } } }]
}
```

⚠ `sitemap.js` — *«a special Route Handler that is cached by default unless it uses a Request-time API»* → ⛔ `headers()`/`cookies()` **ishlatilmaydi**, bazaviy URL **`.env`** dan (`NEXT_PUBLIC_SITE_URL`).

### JSON-LD — Next'ning O'Z xavfsizlik naqshi

[CITED: `node_modules/next/dist/docs/01-app/02-guides/json-ld.md`]

```tsx
<script
  type="application/ld+json"
  dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd).replace(/</g, '\\u003c') }}
/>
```

⛔⛔ **`.replace(/</g, '\\u003c')` MAJBURIY va u dekorativ emas:** FAQ matni tarjima katalogidan keladi (G-land-4(d)), ya'ni satrda `</script>` ketma-ketligi paydo bo'lsa **skript bloki erta yopilardi** va qolgani HTML sifatida o'qilardi. ⚠ Matn repozitoriyadan keladi (foydalanuvchi kiritmasi emas) → xavf **past, lekin nolga teng emas**, va rasmiy naqsh **arzon**.

### OG rasmi

⛔ SPEC §14.1: statik PNG (`/public/og/sbozor-og.png`), `ImageResponse` **EMAS**. ✅ `public/` bo'sh — fayl **yaratiladi**. ⛔ `next/og` (satori) **paket qo'shmaydi** (u `next` ichida), lekin u **runtime** talab qiladi va SSG sahifada build vaqtini oshiradi — SPEC'ning rad sababi to'g'ri.

---

## Copy mexanikasi — i18n zanjiri

### Zanjir (o'zgarmaydi)

```
uz-Latn.json  --(npm run i18n:gen)-->  uz-Cyrl.json      [+ uz-Cyrl.overrides.json]
     |
     +---------------------------------> ru.json          ⛔ QO'LDA, mustaqil tarjima
                      |
                      +--> npm run i18n:check
                             ├─ gen-cyrillic.mjs --check   (drift => exit 1)
                             └─ check-messages.mjs         (kalit-parity + ICU-parity)
```

| Darvoza | Nima qiladi | Landing'ga ta'siri |
|---------|-------------|--------------------|
| `gen-cyrillic.mjs --check` | Commit qilingan `uz-Cyrl.json` generatsiya natijasiga **bayt-bayt** teng | ⛔ `landing.*` qo'shilgach `npm run i18n:gen` **majburiy** |
| `check-messages.mjs` (a) | Uchala faylning **kalit to'plamlari AYNAN teng** | ⛔ ru **bir vaqtda** yozilishi shart, keyin emas |
| `check-messages.mjs` (b) | Har kalitdagi **ICU argument nomlari** to'plami teng | ⛔ `landing.form.error.body` da `{phone}` — uchala tilda **bir xil nom** |
| `gen-cyrillic.test.mjs` `allowed` (`:502`) | `uz-Cyrl.json` da **lotin harfi qolmagan** | ⛔ `AI` juftligi (B-3) |
| `gen-cyrillic.test.mjs` alphanumeric | `[A-Za-z]+\.?[0-9]` ⛔ **taqiq** (uchala faylda) | ✅ `D-11` **o'tadi** (defis oralab), `2 306 000` o'tadi, `+998 90…` o'tadi |
| `glossary.test.mjs` (G7-9) | `rasta`/`patta` taqiqlangan sinonimlari | ⛔ «patta = **yig'im**» **TAQIQ**; to'g'ri gloss «kunlik savdo to'lovi» |

### Transliteratsiya — landing satrlari sinaldi [O'LCHANDI]

| uz-Latn | uz-Cyrl chiqishi | Holat |
|---------|------------------|-------|
| `Har bir band rastadan patta to'liq yig'ilyaptimi?` | `Ҳар бир банд растадан патта тўлиқ йиғиляптими?` | ✅ |
| `Demo so'rang` / `Tizimga kirish` | `Демо сўранг` / `Тизимга кириш` | ✅ |
| `Yangi uskuna shart emas` | `Янги ускуна шарт эмас` | ✅ |
| `Ma'lumotlar O'zbekistonda` | `Маълумотлар Ўзбекистонда` | ✅ |
| `NVR faqat VPN orqali` | `NVR фақат VPN орқали` | ✅ (akronimlar lotin) |
| `Band, lekin to'lovsiz — D-11` | `Банд, лекин тўловсиз — Д-11` | ⚠ `D-11` → `Д-11` (quyida) |
| `To'landi — 8 000 so'm` | `Тўланди — 8 000 сўм` | ✅ |
| `Karmana bozorida sinovda` | `Кармана бозорида синовда` | ✅ |
| `Namunaviy ma'lumot` | `Намунавий маълумот` | ✅ |
| `Maxfiylik siyosati` | `Махфийлик сиёсати` | ✅ |
| ⛔ `Namuna bozori · demonstratsiya` | ⛔ `Намуна бозори · демонстратсия` | ⛔ **DEFEKT — B-3** |
| ⛔ `AI band rastani aniqlaydi` | ⛔ `АИ банд растани аниқлайди` | ⛔ **DEFEKT — B-3** |

⚠ **`D-11` → `Д-11` — past xavfli, lekin qayd etiladi.** Rasta kodlari app'da DB'dan keladi va **tarjima qilinmaydi**; sahnadagi `D-11` esa **matn katalogidan** va u kirillashadi. ⛔ Sahna «namunaviy» deb belgilangani uchun mos kelmaslik yolg'on emas, lekin fazaning o'lchanadigan maqsadi *«reklamadagi bilan bir xil»*. ⛔ **Tavsiya:** raqamsiz shakl (`landing.scene.tagUnpaid` = «Band, lekin to'lovsiz») yoki rasta kodini **sof raqam** qilish (`№ 16`) — ⛔ ikkalasi ham `D-11` ni yo'q qiladi. Reja tanlaydi; **tetigi** — HUMAN-UAT dagi kirill o'qish bandi.

### Fazoviy nom byudjeti

⛔ Bugun **31** fazoviy nom / **1373** kalit. Landing **32-chi** (`landing`) ni ochadi va **~119** kalit qo'shadi → **~1492** kalit × 3 til.

⛔ ru **transliteratsiya hosilasi EMAS** [`glossary.json` `_banned_synonyms_readme`] — mustaqil yoziladi. ⚠ **Reja uchun hajm signali:** ~119 satrni uch tilda yozish **eng katta yagona ish bo'lagi** va u **kod emas** — reja uni alohida to'lqinga ajratsin, aks holda u kod vazifalarining ichiga yashirinib, byudjetni jimgina yeydi.

---

## Darvoza byudjeti — O-01 ga o'lchangan javob

### Bazaviy [O'LCHANDI 2026-08-17, shu sessiyada]

| Nima | O'lchov |
|------|---------|
| Barcha `scripts/*.test.mjs` (22 fayl, **349 test**) | ⛔ **2,83 s** (wall), `duration_ms 1864` |
| Bitta skript fayli (`typography.test.mjs`, 6 test) | **0,44 s** wall |
| To'liq `vitest run` (**99 fayl / 1170 test**) | ⛔ **172,47 s** |
| Fayl boshiga o'rtacha (vitest) | ⛔ **~1,74 s** |

### SPEC qo'shimchasining haqiqiy narxi

| Qo'shimcha | Baholangan narx | Asos |
|------------|-----------------|------|
| `scripts/landing-surface.test.mjs` (1 fayl, sof matn/CSS parse) | ⛔ **+0,5…1,0 s** | Mavjud 22 fayl 2,83 s; bu fayl ko'proq fayl o'qiydi |
| `components/marketing/hero-scene.test.tsx` | ⛔ **+~1,7 s** | vitest fayl boshiga o'rtacha |
| `components/marketing/demo-form.test.tsx` | ⛔ **+~1,7 s** | ayni |
| ⛔ **Jami test qo'shimchasi** | ⛔ **~+4…5 s** | — |
| `next build` +3 marshrut (81 → 84) | ⚠ **O'LCHANMADI** | Reja `build` ni oldin/keyin o'lchaydi |
| Backend: 1 integratsiya fayli (`test_demo_request.py`) | ⚠ **O'LCHANMADI** | `gate` da, `gate:fast` da **emas** |

### Byudjetga sig'adimi

| Daraja | Byudjet | Eng yomon o'lchov (09-07) | Zaxira | Qo'shimchadan keyin |
|--------|---------|---------------------------|--------|---------------------|
| `gate:fast` | **200 s** | **189 s** | **11 s (5,5 %)** | ⛔ **~6,5 s (3,3 %)** — ⚠ **JUDA TOR** |
| `gate` | **2300 s** | **2259 s** | **41 s (1,8 %)** | ⛔ **~35 s** (+ build va backend qo'shimchasi **hisobga olinmagan**) |

⛔ **XULOSA: SPEC ning «~15–30 s» bahosi ~4 barobar yuqori edi — test qo'shimchasi sig'adi.** ⚠ **LEKIN `gate:fast` ning 3,3 % zaxirasi shovqin darajasida** (o'lchov tarqoqligi 09-07 da **9,5 %** edi), ya'ni ⛔ **chegara nuqson sababli EMAS tripplashi ehtimoli yuqori**.

⛔ **[TAVSIYA] Reja `gate:fast` byudjetini 200 → 250 s ga OLDINDAN ko'taradi**, W0-13 protokoli bilan:

| Qadam | Talab |
|-------|-------|
| 1 | **Tinch xost** (`parnikkpi-*` va restart halqasidagi konteynerlar to'xtatiladi, keyin **tiklanadi**) |
| 2 | ⛔ **Uch o'lchov** (09-07 da ikki bo'lgan — bu faza uchtasini bersin) |
| 3 | Chegara = **eng yomon × 1,20**, 50 ga yuqoriga yaxlitlash |
| 4 | Sabab + jurnal ⛔ **`package.json` `//gate-fast-budget`** izohiga |
| 5 | ⛔ **Jimgina ko'tarish TAQIQ** |

⚠ `//gate-fast-budget` izohining o'zi buni **kutgan**: *«10-faza (landing) birinchi commitidayoq qayta baholansin — landing marshrutlari vitest'ga qo'shilsa chegara ko'tarilishi tabiiy va u NUQSON EMAS»*.

⛔ **`gate` (2300 s) ni ham qayta o'lchash kerak** — 41 s zaxira `next build` ning +3 marshruti va backend integratsiya faylini **ko'tarmasligi mumkin**. ⛔ Ikkalasi **bitta W0-13 seansida** o'lchansin.

⚠ **Zanjir boshida majburiy nazorat** [MEROS: 09-VALIDATION]: `frontend/node_modules` mavjudligi tekshirilsin — 8-fazada bo'shligi **29-daqiqada** ko'ringan.

---

## Qulflangan o'lchovlarni mustaqil tasdiqlash

| SPEC bandi | SPEC da'vosi | ⛔ Mustaqil o'lchov | Holat |
|------------|--------------|---------------------|-------|
| **L-1** | `components.json` yo'q | `find` → 0 | ✅ |
| **L-2** | `text-base` = **7**, chegara **7** | 7 uchrash (izohsiz), `typography.test.mjs:114` ceiling 7 | ✅ **TO'LGAN** |
| **L-3** | `text-xl` **3** / chegara 4 | grep 4 satr, biri **izoh** (`temp-password-dialog.tsx:66`) → kod **3** | ✅ |
| **L-3** | `text-3xl` **0** · `text-[` **0** · `font-medium` **21**/21 | 0 · 0 · 21 | ✅ |
| **L-3** | `text-lg` / `text-2xl` chegarasiz | 49 / 34 satr; `DEVIATION_CEILINGS` da **yo'q** | ✅ |
| **L-4** | `text-display` **aynan 2 fayl** | `collect/pending-card.tsx`, `headline/headline-card.tsx` (6 satr) | ✅ |
| **L-5** | Ildiz layout **to'liq** katalog uzatadi | `layout.tsx:112` `messages={messages}` | ✅ |
| **L-5** | 77 117 / 107 432 / 109 805 B xom | ✅ **aynan** | ✅ |
| **L-5** | gzip 21 768 / 25 195 / 27 051 | 21 726 / 24 954 / 26 942 (gzip darajasi farqi) | ✅ ±1 % |
| **L-6** | 5 provayder ildizda | `NextIntlClientProvider→NuqsAdapter→QueryProvider→AuthProvider→Toaster` | ✅ |
| **L-7** | Ildiz sahifa `/dashboard` ga redirect | `page.tsx:29` | ✅ |
| **L-8** | Sketch'da `left` va `height` animatsiyasi | `landing-sehri.md` CSS bloki: `@keyframes sweepgo{left}`, `transition:height 900ms` | ✅ |
| **L-8** | `BANNED_KEYFRAME_PROPS` da nomma-nom | `motion-tokens.test.mjs:101-110` = `width,height,top,left,right,bottom,margin,padding` | ✅ |
| **L-9** | **8** `@keyframes` nomi | `draw·ringpulse·landin·enter·shimmer·breath·attention·shake` | ✅ |
| **L-10** | `.motion-enter` + `.motion-attention` mavjud | `globals.css:304,355`; `--i × 60ms` stagger `:306` | ✅ |
| **L-11** | `AI` → `АИ` | `transliterate()` mustaqil chaqiruv | ✅ |
| **L-12** | «AI dan boshqa **0** defekt» | ⛔ **NOTO'G'RI** — `demonstratsiya` + 8 ta `-tsiya` so'z | ⛔ **RAD** (B-3) |
| **L-17** | `Button` da hero o'lchami yo'q | `ui/button.tsx`: `sm h-9` · `md h-10` · `lg min-h-11`, ⛔ **uchalasi `text-sm`** | ✅ |
| **L-18** | `Button` reyestri darvozasiz | `buttonVariants`/`SIZES` skani → 0 | ✅ |
| **L-19** | G-SUBMIT skan yuzasi `src/**` | `submit-gate.test.mjs`: `SRC` + `TEST_FILE` istisnosi | ✅ |
| **L-21** | `dependencies` **18** nom, `deepEqual` | `motion-tokens.test.mjs:134-153` + `length === 18` | ✅ |
| **L-22** | **1373** kalit, **31** fazoviy nom | ✅ **aynan** | ✅ |
| **L-24** | `proxy.ts` matcher nuqtali yo'llarni chetlaydi | `proxy.ts:17` | ✅ |
| **L-25** | Backend'da anonim marshrut yo'q | 26 modul, 0 anonim | ✅ |
| **L-26** | G-18 e'loni **aynan 1** UI-SPEC da | `bulk-action-surface.test.mjs:113` `assert.equal(SPEC_FILES.length, 1)`; ⛔ 10-UI-SPEC G-18 qatorini **yozmaydi** | ✅ |
| **§4.3** | `[locale]/` da boshqa fayl yo'q | ✅ + ⛔ `not-found`/`error`/`loading` ham **yo'q** | ✅ **kuchayadi** |
| **ROADMAP** | 81 SSG marshrut | `prerender-manifest.json` → 81 | ✅ |

---

## Qo'lda yozilmasin (Don't Hand-Roll)

| Muammo | Qurilmasin | Ishlatilsin | Sabab |
|--------|------------|-------------|-------|
| Telefon normalizatsiyasi | Regex `\+998\d{9}` | ⛔ `sbozor_core.phone.normalize_phone` (`phonenumbers`) | Modul docstringi: *«Regex bilan QILINMAYDI»*; D-01 — telefon **yagona kalit** |
| Rate-limit sanagichi | Yangi `INCR` mantiq | ⛔ `security/ratelimit._bump()` | `EXPIRE(nx=True)` pipeline'da — mangu kalit tuzog'i **allaqachon** yechilgan |
| Telegram jo'natish | `httpx.post(api.telegram.org/...)` | ⛔ `services/alerts.AlertSender` | Bot tokeni URL'da → istisno matni sirni **jurnalga → Sentry → DB** olib chiqadi (2-taqiq) |
| So'rov IP'si | `request.client.host` | ⛔ `auth.py` dagi mavjud yordamchi | Proksi ortida `X-Forwarded-For` mantiqi **bir joyda** |
| Scroll-reveal | Yangi kutubxona / scroll listener | ⛔ Native `IntersectionObserver` + `.motion-enter` | K-9: 0 paket; `.motion-enter` **mavjud** |
| Count-up | Yangi animatsiya hook | ⛔ `lib/use-count-up.ts` | `prefers-reduced-motion` ni **o'zi hurmat qiladi** [L-20] |
| Diqqat halqasi | Yangi `@keyframes` | ⛔ `.motion-attention` | Mavjud, **bir marta**, `--motion-slow` |
| Kirish animatsiyasi | Yangi `fade-up` | ⛔ `.motion-enter` + inline `--i` | Sketch'ning `fade-up` i bilan **ayni** |
| Akkordeon (FAQ) | ARIA disclosure widget | ⛔ Native `<details>`/`<summary>` | JS'siz ishlaydi, klaviatura + skrinrider **bepul** |
| JSON-LD xavfsizligi | Qo'lda escape | ⛔ `JSON.stringify(x).replace(/</g,'\\u003c')` | Next'ning **o'z** rasmiy naqshi |
| Forma holati | `useState` × 6 | ⛔ `react-hook-form` + `zod` resolver | Ikkalasi ham `dependencies` da |
| i18n kirill | Qo'lda `uz-Cyrl.json` tahriri | ⛔ `npm run i18n:gen` + `overrides` | `--check` drift'da **exit 1** |

**Asosiy fikr:** bu fazada qo'lda yozish tuzog'i **kutubxona qo'shishda emas** (K-9 uni yopgan) — u **mavjud loyiha modullarini takrorlashda**. Har takror ikkinchi haqiqat manbai tug'diradi va u **birinchi kunda ko'rinmaydi**.

---

## Umumiy tuzoqlar

### Tuzoq 1: ⛔⛔ Klient kontrakti **jimgina yutadi**

**Nima buziladi:** `(marketing)/layout.tsx` ga `messages={{common, landing}}` yozilib, landing komponentida `useTranslations("common")` **dan boshqa** fazoviy nom chaqiriladi (masalan `errors.generic` yoki `nav.*`). ⛔ Server render **o'tadi** (server kontekstda **to'liq** katalog bor), klient esa `MISSING_MESSAGE` bilan yiqiladi — ⛔ **faqat brauzerda, faqat hidratatsiyadan keyin**.

**Nega:** `NextIntlClientProviderServer` `messages` berilmasa server kontekstidan meros oladi; ⛔ **berilganda esa u aynan shu obyekt bilan cheklanadi**, server komponentlari esa baribir to'liq katalogni ko'radi. Ikki manzara **bir sahifada** yashaydi.

**Qanday oldini olish:** ⛔ **G-land-1(c) ni ikki tomonlama yozish** — reyestr `["common","landing"]` ga teng **VA** `components/marketing/**` + `(marketing)/**` da `useTranslations("...")` / `getTranslations("...")` argumentlari to'plami ⛔ **shu reyestrning QISMI**. SPEC (c) bandi faqat birinchi yarmini yozgan.

**Ogohlantirish belgilari:** brauzer konsolida `IntlError: MISSING_MESSAGE`; SSR HTML'da matn **bor**, hidratatsiyadan keyin **yo'qoladi**.

---

### Tuzoq 2: ⛔⛔ Sabotaj **import qilinadigan** modul qoldirmaydi

[MEROS: SPEC §16.3, 05-15 / 08-20 / 09 darslari]

**Nima buziladi:** «`hero.tsx` ga `"use client"` qo'shildi — G-land-1(b) qizardi» deb yoziladi, lekin aslida ⛔ **`next build` type/lint qadamida** yiqilgan bo'ladi — ya'ni o'lchangan narsa **darvoza emas, yig'ilish**.

**Nega:** sabotaj kodni **buzsa**, zanjir darvozaga **yetib bormaydi**.

**Qanday oldini olish:** har sabotaj ⛔ **kompilyatsiya qilinadigan, import qilinadigan** holatda qoldiriladi va ⛔ **aynan mo'ljallangan darvoza** qizarishi yoziladi. SPEC §16.3 so'zma-so'z: *«Sabotaj sistemaga yetib borib ham hech nima qizarmasa, tuzatish testda emas — HOLATDA»*.

⛔ **Reja har `G-land-*` uchun sabotajni ALOHIDA task-qadam qilib yozsin**, tasdiq mezoni: «sabotaj bilan `node --test scripts/landing-surface.test.mjs` **exit 1** va xato matnida **(a)/(b)/… bandi nomi**».

---

### Tuzoq 3: ⛔ Provayder ko'chirishi `(app)` ni **hook tartibida** sindiradi

**Nima buziladi:** `AppProviders` `(app)/layout.tsx` **ichiga** shunday qo'yiladiki, mavjud `AppLayout` ning `useAuthStore()` / `useTranslations()` chaqiruvlari ⛔ **provayderlardan tashqarida** qoladi → `throw`.

**Nega:** `(app)/layout.tsx` bugun **o'zi** `"use client"` va **o'zi** hook chaqiradi. `export default function AppLayout(){ const {...} = useAuthStore(); return <AppProviders>...</AppProviders> }` shakli **noto'g'ri** — hook provayderdan **oldin** ishlaydi.

**Qanday oldini olish:** ⛔ **Ikki komponent:** `(app)/layout.tsx` faqat `<AppProviders><AppGuard>{children}</AppGuard></AppProviders>` qaytaradi; mavjud mantiq ⛔ **`AppGuard`** ga (yangi fayl yoki ayni fayldagi ichki komponent) ko'chadi.

**Ogohlantirish belgilari:** `next build` prerender'da `useAuthStore() faqat <AuthProvider> ichida ishlaydi`; `(app)/layout.test.tsx` **qizaradi** (u bugun mavjud — bepul erta signal).

---

### Tuzoq 4: ⛔ Reduced-motion tarmog'i «hech nima qilmaslik» **emas**, **hech qanday taymer yaratmaslik**

**Nima buziladi:** `hero-scene.tsx` `prefers-reduced-motion` ni tekshirib, sikl **ichida** har fazada `if (reduced) return` yozadi. ⛔ Taymerlar **baribir yaratiladi** → G-land-2(a) (`setTimeout` josusi = **0**) qizaradi va arzon telefonda batareya baribir yeyiladi.

**Qanday oldini olish:** ⛔ **Erta `return`** — effektning **birinchi** qatorida, `setTimeout` ⛔ **umuman chaqirilmaydi**. SPEC §5.2: *«reduced-motion — bu **hech nima qilmaslik**»*.

**Ogohlantirish belgilari:** `matchMedia` stubi `true` bo'lgan testda `vi.getTimerCount() > 0`.

---

### Tuzoq 5: ⛔ `IntersectionObserver` **ikki** to'xtatgichni chalkashtirish

**Nima buziladi:** ko'rinuvchanlik (`IntersectionObserver`) va tab fokusi (`visibilitychange`) bitta bayroqqa yig'iladi → foydalanuvchi tabga qaytganda sahna **qayta boshlanadi** (rewind), holbuki SPEC §5.2 ⛔ **«Rewind YO'Q»** deydi.

**Qanday oldini olish:** ⛔ Ikki mustaqil shart, **bitta** samara: `const running = visible && !hidden`. To'xtaganda ⛔ **taymerlar tozalanadi, DOM holati SAQLANADI**; davom etganda **joriy fazadan** davom etadi.

---

### Tuzoq 6: ⛔ YAML `>-` (folded) skalyar — VALIDATION faylida **TAQIQ**

**Nima buziladi:** `10-VALIDATION.md` frontmatter'ida uzun `why_not_automatable` matni `>-` bilan yoziladi → parser uni **literal** o'qiydi yoki qatorlarni noto'g'ri qo'shadi va signoff skripti (`npm run validation:check`) **jimgina noto'g'ri** qiymat ko'radi.

**Qanday oldini olish:** ⛔ **Uzun qiymat — BITTA qator**, kerak bo'lsa `"` ichida. Presedent: `09-VALIDATION.md` frontmatter'i **aynan shunday** yozilgan.

---

### Tuzoq 7: ⛔ `EXEMPT_ROUTES` ga qo'shib **qamrovni ko'chirmaslik**

**Nima buziladi:** demo marshruti `EXEMPT_ROUTES` ga sabab bilan qo'shiladi, `test_route_coverage.py` **yashil**, matritsa **yashil** — va marshrut ⛔ **umuman sinovsiz** qoladi (tokensiz/buzilgan token da'volari ham unga qo'llanmaydi).

**Qanday oldini olish:** ⛔ Yuqoridagi **7 bandli** integratsiya testi (`/internal/self-check` presedenti). ⛔ `EXEMPT_ROUTES` sabab satrida ⛔ **qamrov qayerda tiklanganini yozish** — mavjud yozuvlarning hammasi shunday qilgan.

---

### Tuzoq 8: ⛔ `robots.ts` app marshrutlarini **yopishni unutish**

**Nima buziladi:** landing indekslanadi, u bilan birga `/uz/collect`, `/uz/dashboard` ham → qidiruv natijasida **ichki tuzilma** ko'rinadi va foydalanuvchi **o'lik havolaga** tushadi (u `/login` ga redirect bo'ladi).

**Qanday oldini olish:** ⛔ `robots.ts` da `Disallow` — `/api/`, `/*/dashboard`, `/*/collect`, `/*/login`, `/*/billing`, `/*/reports`, … ⛔ **Ro'yxat HOSILA bo'lsin**, qo'lda emas: `(app)`/`(auth)` kataloglaridan o'qilsin — aks holda 25-chi sahifa qo'shilganda u **jimgina ochiq** qoladi.

---

## Kod namunalari (tasdiqlangan manbalardan)

### Marketing layout — tor provayder

```tsx
// app/[locale]/(marketing)/layout.tsx — Server Component
// Manba: next-intl 4.13.4 NextIntlClientProvider.d.ts (VERIFIED)
import { NextIntlClientProvider } from "next-intl";
import { getMessages, setRequestLocale } from "next-intl/server";

export default async function MarketingLayout({
  children, params,
}: { children: React.ReactNode; params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  setRequestLocale(locale);                 // ⛔ SSG sharti
  const messages = await getMessages();     // server tomonda TO'LIQ — bepul

  // ⛔ G-land-1(c): KLIENTGA aynan ikki fazoviy nom
  return (
    <NextIntlClientProvider messages={{ common: messages.common, landing: messages.landing }}>
      {children}
    </NextIntlClientProvider>
  );
}
```

### JSON-LD — Next'ning rasmiy naqshi

```tsx
// Manba: node_modules/next/dist/docs/01-app/02-guides/json-ld.md (CITED)
<script
  type="application/ld+json"
  dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd).replace(/</g, "\\u003c") }}
/>
```

### `sitemap.ts` — hreflang

```ts
// src/app/sitemap.ts  ⛔ [locale] ICHIDA EMAS
// Manba: node_modules/next/dist/docs/.../metadata/sitemap.md (CITED)
import type { MetadataRoute } from "next";

const BASE = process.env.NEXT_PUBLIC_SITE_URL ?? "https://sbozor.uz";
const PREFIX = { "uz-Latn": "/uz", "uz-Cyrl": "/uz-cyrl", ru: "/ru" } as const;

export default function sitemap(): MetadataRoute.Sitemap {
  const languages = Object.fromEntries(
    Object.entries(PREFIX).map(([tag, p]) => [tag, `${BASE}${p}`]),
  );
  return [{ url: `${BASE}/uz`, lastModified: new Date(), alternates: { languages } }];
}
```

### Rate-limit — mavjud `_bump` naqshi

```python
# app/security/ratelimit.py ga qo'shiladi — YANGI mexanizm YO'Q
# Manba: check_bot_resolve_rate (KOD) ning aynan shakli
DEMO_REQUEST_LIMIT = 5
DEMO_REQUEST_WINDOW_SECONDS = 15 * 60
_DEMO_REQUEST_KEY = "rl:demo_request:"   # rl:demo_request:<ip> — ⛔ telefon YO'Q (T-07-41)

async def check_demo_request_rate(cache: Redis, *, ip: str) -> None:
    try:
        allowed = await _bump(cache, _DEMO_REQUEST_KEY + ip,
                              DEMO_REQUEST_LIMIT, DEMO_REQUEST_WINDOW_SECONDS)
    except RedisError as exc:
        log.warning("demo_request_rate_limit_unavailable", error=str(exc))
        return                      # ⛔ uchala mavjud chaqiruvdagi AYNI qaror
    if not allowed:
        raise TooManyAttempts("demo_request")
```

### `AI` juftligi — aniq ikki tahrir

```jsonc
// 1) frontend/messages/uz-Cyrl.overrides.json -> words
    "IR": "IR",
    "AI": "AI",              // ⛔ YANGI
    "Telegram": "Telegram",
```

```js
// 2) frontend/scripts/gen-cyrillic.test.mjs:502 -> allowed
//    ...|MSE|NVR|NTP|VPN|GMT|IP|IR|AI|Telegram)\b|...
//                              ^^^ YANGI
```

✅ **Tasdiqlandi:** `transliterate("AI band rastani aniqlaydi", words)` → `AI банд растани аниқлайди`; `allowed` dan keyin lotin harfi **qolmaydi**.

---

## Muhit mavjudligi

| Bog'liqlik | Kim talab qiladi | Mavjud | Versiya | Zaxira |
|------------|-----------------|--------|---------|--------|
| Node | frontend build/test | ✅ | ≥20.9 (`engines`) | — |
| `frontend/node_modules` | butun frontend zanjiri | ✅ | o'rnatilgan | `npm ci --prefix frontend` |
| `.next/` build artefakti | payload o'lchovi | ✅ | mavjud (81 marshrut) | qayta build |
| vitest 4.1.10 + jsdom 30.0.1 | komponent darvozalari | ✅ | `devDependencies` | — |
| `node --test` | skript darvozalari | ✅ | Node o'rnatilgan | — |
| Docker Compose | `gate` ning backend yarmi | ⚠ **o'lchanmadi** | — | — |
| ⛔ `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` | ⛔ **demo-forma yetkazishi** | ⚠ **o'lchanmadi** (`.env`) | — | ⛔ `alerts_enabled` **False** → `send_message()` darhol `False` → `delivery_failed`; ✅ **bu qonuniy holat** va `log.warning("alerts_disabled")` bir marta yoziladi |
| `NEXT_PUBLIC_CONTACT_PHONE` | `landing.form.error.body` `{phone}` | ⛔ **YO'Q** | — | ⛔ SPEC O-06: raqamsiz shox (`error.bodyNoPhone`) — **bo'sh qavs KO'RSATILMAYDI** |
| `NEXT_PUBLIC_SITE_URL` | `sitemap.ts`, `canonical`, OG `url` | ⛔ **YO'Q** | — | Standart `https://sbozor.uz` |

**Zaxirasiz bloklovchi:** ⛔ **yo'q.**
**Zaxira bilan yopiladigan:** `TELEGRAM_*` (alertsiz muhitda `delivery_failed` — halol yo'l, test uni `respx` bilan tutadi); `NEXT_PUBLIC_CONTACT_PHONE`; `NEXT_PUBLIC_SITE_URL`.

---

## Validatsiya arxitekturasi

> ⛔ Bu bo'lim **darhol** kiritildi — 9-fazada u keyin qo'shishga to'g'ri kelgan edi.
> `workflow.nyquist_validation: true` (`.planning/config.json`).

### Test infratuzilmasi

| Xossa | Qiymat |
|-------|--------|
| **Framework (birlamchi)** | vitest **4.1.10** + jsdom **30.0.1** + `@testing-library/react` **16.3.2** — `src/**/*.test.tsx` |
| **Framework (ikkilamchi)** | `node --test` (Node o'rnatilgan, ⛔ **nol bog'liqlik**) — `frontend/scripts/*.test.mjs` |
| **Framework (uchlamchi)** | pytest **9.1.1** — ⛔ **BU FAZADA ISHLATILADI** (9-fazadan farq): anonim endpoint `tests/integration/` + `EXEMPT_ROUTES` qamrovi |
| **Config — komponent** | `frontend/vitest.config.ts` (`environment: "jsdom"`, `include: ["src/**/*.test.tsx"]`, `setupFiles: ["./vitest.setup.ts"]`) |
| **Config — global setup** | `frontend/vitest.setup.ts` — ⛔ `matchMedia` va `IntersectionObserver` stublari bu yerga **QO'YILMAYDI**; teskari shox (reduced-motion **yoqilgan**) hech qachon o'lchanmasdi. Stub **har testda alohida** |
| **Quick run** | `npm run gate:fast` → `npm run test:fast && npm --prefix frontend test` |
| **Full suite** | `npm run gate` (sim:up → backend → cv → bot → i18n:check → frontend test/typecheck/lint/build) |
| **O'lchangan bazaviy (2026-08-17, shu tadqiqot)** | Skript darvozalari **2,83 s** (22 fayl / 349 test) · vitest **172,47 s** (99 fayl / 1170 test) → **~1,74 s/fayl** · prerender **81** marshrut |
| **O'lchangan byudjet (09-07)** | `gate` **2259 / 2102 s** · byudjet **2300 s** · zaxira **41 s (1,8 %)** · `gate:fast` **189 / 171 s** · byudjet **200 s** · zaxira **11 s (5,5 %)** |
| **Kutilayotgan o'sish** | ⛔ **O'LCHANDI: ~+4…5 s** (1 skript ~+0,5–1,0 s · 2 vitest ~+3,4 s). ⚠ `next build` **+3 marshrut** va backend integratsiya fayli **o'lchanmadi** |
| **Byudjet qarori** | ⛔ **`gate:fast` 200 → 250 s OLDINDAN ko'tarilsin** (W0-13: tinch xost, **uch** o'lchov, eng yomon × 1,20, jurnal `package.json //gate-fast-budget` da). `gate` **ayni seansda** qayta o'lchansin |
| **Zanjir boshida nazorat** | ⛔ `frontend/node_modules` mavjudligi (`npm ci --prefix frontend`) — 8-fazada bo'shligi **29-daqiqada** ko'ringan |

### Mezon → o'lchov xaritasi

| Req | Xulq | Test turi | Avtomatik buyruq | Fayl bormi? |
|-----|------|-----------|------------------|-------------|
| **LAND-01** | Anonim root uchala tilda landing ko'rsatadi; `[locale]/page.tsx` **mavjud emas** | skript (fayl skani) | `node --test frontend/scripts/landing-surface.test.mjs` (G-land-1(d)) | ❌ Wave 0 |
| **LAND-01** | LCP yo'li klientga bog'lanmagan (`hero.tsx` da `"use client"` **0**) | skript | ayni (G-land-1(b)) | ❌ Wave 0 |
| **LAND-01** | Klient orollari reyestrga `deepEqual` (**5** fayl — B-1/C) | skript | ayni (G-land-1(a)) | ❌ Wave 0 |
| **LAND-01** | Marketing provayderiga aynan `["common","landing"]` **VA** komponentlar shu nomlardan tashqariga chiqmaydi | skript | ayni (G-land-1(c), ⛔ **ikki tomonlama** — Tuzoq 1) | ❌ Wave 0 |
| **LAND-01** | Uchala locale SSG bo'lib chiziladi | build | `npm --prefix frontend run build` → `prerender-manifest.json` da **84** marshrut | ✅ mavjud infra |
| **LAND-02** | reduced-motion'da ⛔ **birorta `setTimeout` chaqirilmaydi** va DOM **to'liq final-kadr** | vitest | `npx vitest run src/components/marketing/hero-scene.test.tsx` (G-land-2(a)) | ❌ Wave 0 |
| **LAND-02** | 0 ms da final-kadr (rewind yo'q); **13 500 ms** da 1-fazaga qaytgan | vitest | ayni (G-land-2(b)) — ⛔ **13500**, 12000 emas | ❌ Wave 0 |
| **LAND-02** | Beshala faza yorlig'i ketma-ket ko'rinadi (reyestr **matn katalogidan hosila**) | vitest | ayni (G-land-2(c)) | ❌ Wave 0 |
| **LAND-02** | `unmount()` dan keyin `clearTimeout` soni = yaratilgan taymerlar soni | vitest | ayni (G-land-2(d)) | ❌ Wave 0 |
| **LAND-02** | `IntersectionObserver` `isIntersecting:false` → yangi taymer **yaratilmaydi** | vitest | ayni (G-land-2(e)); ⛔ **IO qo'lda stub** (jsdom'da yo'q) | ❌ Wave 0 |
| **LAND-02** | `.landing-*`/`.motion-*` `transition` xossalari ruxsat to'plamining **qismi**; `width/height/top/left/…` **0** | skript | `landing-surface.test.mjs` (G-land-3(a)) — ⛔ G-motion-3(a) ning **o'lchangan bo'shlig'i** | ❌ Wave 0 |
| **LAND-02** | `marketing/**` da inline `style` ichida geometriya **0** | skript | ayni (G-land-3(b)) | ❌ Wave 0 |
| **LAND-02** | `setInterval` **0**; `setTimeout` ⛔ **faqat** `hero-scene.tsx` da | skript | ayni (G-land-3(c)) | ❌ Wave 0 |
| **LAND-02** | `@keyframes` reyestri **9** nom; yangisi aynan `sweep`; mavjud 8 `deepEqual` | skript | ayni (G-land-3(d)) | ❌ Wave 0 |
| **LAND-03** | Anonim `POST` autentifikatsiyasiz **muvaffaqiyat**; `Set-Cookie` **yo'q**; javobda tenant izi **yo'q** | pytest | `docker compose --profile test run --rm tests pytest tests/integration/test_demo_request.py -q` | ❌ Wave 0 |
| **LAND-03** | Chegaradan oshsa **429 `rate_limited`** | pytest | ayni | ❌ Wave 0 |
| **LAND-03** | Noto'g'ri telefon → **422 `invalid_phone`** (`normalize_phone`) | pytest | ayni | ❌ Wave 0 |
| **LAND-03** | Honeypot to'ldirilgan → jim muvaffaqiyat, Telegram'ga **0 chaqiruv** | pytest (`respx`) | ayni | ❌ Wave 0 |
| **LAND-03** | Yetkazish yiqilsa `delivery_failed` **VA** DB'da **0 yangi qator** | pytest | ayni | ❌ Wave 0 |
| **LAND-03** | Marshrut `EXEMPT_ROUTES` da, sabab `"global"` bilan boshlanadi | pytest | `pytest tests/tenancy/test_route_coverage.py -q` (⛔ **mavjud**) | ✅ mavjud |
| **LAND-03** | Forma: `disabled` ⛔ **faqat** `isSubmitting` da | skript | `node --test frontend/scripts/submit-gate.test.mjs` (⛔ **mavjud**, `src/**` skani) | ✅ mavjud |
| **LAND-03** | Muvaffaqiyat `role="status"`, xato `role="alert"`, fokus xato blokiga | vitest | `npx vitest run src/components/marketing/demo-form.test.tsx` | ❌ Wave 0 |
| **LAND-04** | `sampleBadge` chaqirig'i bor **va shartli render ichida EMAS** | skript | `landing-surface.test.mjs` (G-land-4(a)) | ❌ Wave 0 |
| **LAND-04** | `a11yDescription` da «namunаviy» o'zagi **uchala locale'da** | skript | ayni (G-land-4(b)) | ❌ Wave 0 |
| **LAND-04** | `trustBlock.residency.body` uchala locale'da + hero anchor bog'langan | skript | ayni (G-land-4(c)) | ❌ Wave 0 |
| **LAND-04** | FAQ JSON-LD matni **tarjima katalogidan** (komponentda literal **yo'q**) | skript | ayni (G-land-4(d)) | ❌ Wave 0 |
| **LAND-04** | Taqiqlangan da'vo tokenlari `landing.*` da **0** (≥8 token, uchala locale) | skript | ayni (G-land-4(e)) | ❌ Wave 0 |
| **LAND-04** | `landing.pilot.*` da raqam (`\d`) **0** | skript | ayni (G-land-4(f)) | ❌ Wave 0 |
| **LAND-04** | ⛔ **YANGI (B-3):** `landing.*` dagi `/[a-z]+ts[iy]/` tokenlar `overrides.words` da | skript | ayni (⛔ **G-land-4(g) taklif**) — ⛔ qamrov **`landing.*` bilan CHEGARALANADI** (meros `deklaratsiya` defekti bloklamasin) | ❌ Wave 0 |
| **LAND-04** | Glossariy: `patta`/`rasta` taqiqlangan sinonimlari **0** | skript | `node --test frontend/scripts/glossary.test.mjs` (⛔ **mavjud**) | ✅ mavjud |
| **LAND-04** | Kalit-parity + ICU-parity 3 tilda; kirill drift yo'q | skript | `npm --prefix frontend run i18n:check` (⛔ **mavjud**) | ✅ mavjud |
| **LAND-05** | `text-hero` **1 fayl / 1 uchrash**; `--text-hero` `@theme` da `clamp(` | skript | `landing-surface.test.mjs` (G-land-5(a,b)) | ❌ Wave 0 |
| **LAND-05** | `py-16`/`py-24` ⛔ **faqat** `marketing/section.tsx` da | skript | ayni (G-land-5(c)) | ❌ Wave 0 |
| **LAND-05** | `marketing/**` da `text-base`/`text-3xl`/`text-[`/`font-medium`/`text-display` — **0** | skript | ayni (G-land-5(d,e)) | ❌ Wave 0 |
| **LAND-05** | Repozitoriya chegaralari oshmagan (`text-base` ≤7, `font-medium` ≤21) | skript | `node --test frontend/scripts/typography.test.mjs` (⛔ **mavjud**) | ✅ mavjud |
| **LAND-05** | `dependencies` **18** nom, to'plam tengligi (0 yangi paket) | skript | `node --test frontend/scripts/motion-tokens.test.mjs` (⛔ **mavjud**) | ✅ mavjud |
| **LAND-05** | Uch temada kontrast AA | skript | `node --test frontend/scripts/contrast.test.mjs` (⛔ **mavjud**, PAIR_REGISTRY **kengaymaydi**) | ✅ mavjud |
| **LAND-05** | Lighthouse ≥95 · LCP <1,5 s · payload farqi | ⛔ **inson** | ⛔ `10-HUMAN-UAT.md` — quyidagi `human_only_verifications` | — |
| **META** | Beshala ROADMAP SC bitta buyruqda | skript | ⛔ `frontend/scripts/phase10-criteria.test.mjs` (09-fazaning `phase9-criteria` presedenti) | ❌ Wave 0 |

### Sampling rate

| Daraja | Buyruq | Qachon |
|--------|--------|--------|
| **Task commit** | `npm run gate:fast` | Har task yakunida — byudjet ⛔ **250 s** (ko'tarilgandan keyin) |
| **Tez mahalliy halqa** (task ichida) | `node --test frontend/scripts/landing-surface.test.mjs` (**<1 s**) + `npx vitest run src/components/marketing/` | Har tahrirdan keyin — ⛔ to'liq vitest (**172 s**) **kutilmaydi** |
| **i18n tahriridan keyin** | `npm --prefix frontend run i18n:gen && npm --prefix frontend run i18n:check` | ⛔ **Majburiy** — `--check` drift'da exit 1 |
| **Backend tahriridan keyin** | `docker compose --profile test run --rm tests pytest tests/tenancy tests/integration/test_demo_request.py -q` | Endpoint to'lqinida |
| **Wave merge** | `npm run gate:fast` + `npm --prefix frontend run build` | Har to'lqin oxirida — ⛔ build **provayder ko'chirishidan keyin MAJBURIY** |
| **Faza darvozasi** | `npm run gate` **yashil**, so'ng `/gsd-verify-work` | Byudjet ⛔ **qayta o'lchangan** qiymat |

### Wave 0 bo'shliqlari

- [ ] ⛔ **`gate:fast` / `gate` byudjetlarini W0-13 bilan qayta o'lchash va ko'tarish** — jurnal `package.json` izohlariga (⛔ **birinchi vazifa**, chunki qolgan hamma narsa uni oshiradi)
- [ ] ⛔ **B-1 qarori:** `components/marketing/locale-switcher.tsx` (anonim, `api-client` siz) — ⛔ **provayder ko'chirishidan OLDIN**
- [ ] ⛔ **B-3 qarori:** `demonstratsiya` → `namoyish` copy tuzatishi **yoki** override; `AI` juftligi (2 fayl)
- [ ] `frontend/scripts/landing-surface.test.mjs` — G-land-1, 3, 4, 5 (⛔ **bitta** fayl, sof matn/CSS parse)
- [ ] `frontend/src/components/marketing/hero-scene.test.tsx` — G-land-2 (a…e)
- [ ] `frontend/src/components/marketing/demo-form.test.tsx` — forma holatlari + a11y
- [ ] `tests/integration/test_demo_request.py` — ⛔ **`EXEMPT_ROUTES` qamrovini tiklaydi** (7 band)
- [ ] `frontend/scripts/phase10-criteria.test.mjs` — beshala SC bitta buyruqda (⛔ faza darvozasi to'lqinida)
- [ ] `10-HUMAN-UAT.md` — quyidagi beshta band, ⛔ **son bilan** yopiladi
- [ ] ⛔ **`AppProviders` + `AppGuard` ajratish** (Tuzoq 3) — `(app)/layout.test.tsx` **mavjud** va u erta signal beradi

### `human_only_verifications` — `10-VALIDATION.md` frontmatter uchun

⛔ **YAML qoidasi:** uzun qiymatlar ⛔ **BITTA qatorda**; `>-` (folded) skalyar ⛔ **TAQIQ** — parser uni literal o'qiydi. Presedent: `09-VALIDATION.md`.

```yaml
human_only_verifications:
  - item: Lighthouse Performance >= 95 va LCP < 1.5 s (arzon Android profili, ROADMAP SC#5)
    why_not_automatable: Lighthouse CI'da YO'Q va bu fazada QO'SHILMAYDI (10-UI-SPEC §16.5, [QAROR]) — headless Chrome + yangi ishlab chiqish bog'liqligi `gate` byudjetiga daqiqalar qo'shardi, byudjet esa o'lchangan holda 41 s zaxirada. Mexanik proksi TOR va u ATAYIN tor: G-land-1 LCP yo'lida `"use client"` yo'qligini qulflaydi, G-land-3 esa layout-thrash sababini yo'q qiladi. Sabab yo'qligi natija borligini isbotlamaydi — tadqiqotda o'lchangan uchinchi omil buni ko'rsatadi: `.motion-enter` `opacity:0` dan boshlanadi va Chrome LCP `opacity:0` elementni chizilgan deb hisoblamaydi, ya'ni `h1` ga `--i` kechikishi berilsa LCP mexanik darvoza KO'RMAYDIGAN yo'l bilan suriladi. Bu — o'lchov, kod emas
    owner: Ijrochi (arzon Android qurilmasi bilan)
    trigger: Birinchi deploy yoki /gsd-verify-work bosqichi — 10-HUMAN-UAT.md #1; natija SON bilan yoziladi, «tez ko'rinadi» bilan EMAS
  - item: "Payload farqi: `next build` route jadvali provayder ko'chirishidan OLDIN va KEYIN, farq gzip KB da"
    why_not_automatable: Bu o'lchov `next build` chiqishini talab qiladi va u `gate` ning oxirgi qadami — test qatlamida route-payload jadvali PRINSIPIAL ravishda ko'rinmaydi. Tadqiqotda bugungi chunk sonlari o'lchandi (zod+api-client 280 KB xom / 69 KB gz, rq+nuqs+sonner 71 KB / 21 KB gz, next-intl 39 KB / 12 KB gz, matn katalogi 21,7–26,9 KB gz), LEKIN refaktordan keyin Turbopack chunk chegaralarini QAYTA hisoblaydi va o'sha guruhlash saqlanishi kafolatlanmagan. Shuning uchun «~110 KB tejaladi» da'vosi BERILMAYDI va u o'lchovsiz BERILMAYDI (10-UI-SPEC §4.3 halollik bandi)
    owner: Ijrochi
    trigger: Provayder ko'chirishi to'lqini yakuni — 10-HUMAN-UAT.md #2; jadval ikki nusxada saqlanadi va farq SON bilan yoziladi
  - item: 60fps arzon Android qurilmada — hero 12s sikli va scroll-reveal jank bermaydi
    why_not_automatable: jsdom layout ham, kompozitsiya ham QILMAYDI — `getBoundingClientRect()` nol qaytaradi, `Element.animate` va `document.getAnimations()` UMUMAN yo'q (09-RESEARCH Tuzoq 1, o'lchangan jsdom 30.0.1 + vitest 4.1.10). Ya'ni «kadr tushdimi?» savoliga test qatlamida javob beradigan sirt YO'Q. G-land-3 `transition` va `@keyframes` xossalarini `transform`/`opacity` bilan qulflaydi, ya'ni layout-thrash SABABINI yo'q qiladi — lekin sabab yo'qligi natija borligini isbotlamaydi: 30 katak + sweep + count-up bir vaqtda ishlaganda arzon GPU baribir to'lishi mumkin. Ikkinchi o'lchanmagan omil — `container-type: inline-size` va `100cqw` ning maqsad qurilmalarda haqiqiy xulqi
    owner: Ijrochi (dala qurilmasi bilan)
    trigger: Birinchi deploy yoki /gsd-verify-work bosqichi — 10-HUMAN-UAT.md #3; natija KADR/SONIYA raqami bilan yoziladi
  - item: "Demo so'rovining uchidan-uchiga yetkazilishi: haqiqiy formadan haqiqiy admin Telegram chatiga"
    why_not_automatable: Integratsiya testi Telegram Bot API'ni `respx` bilan TUTADI va u to'g'ri qaror — haqiqiy tokenni CI'ga bermaslik `alerts.py` ning 2-taqig'ining bevosita talabi. Ya'ni test «biz to'g'ri so'rov yubordik» ni o'lchaydi, «xabar chatga tushdi» ni EMAS. O'lchanmagani: token/chat_id konfiguratsiyasining to'g'riligi, chatning bot tomonidan yozish huquqi, xabar formatining o'qilishi (uch tilda kelgan bozor nomi va ism), va admin uni haqiqatan sotuv signali sifatida ko'rishi. `alerts_enabled` False bo'lgan o'rnatmada tizim `delivery_failed` beradi va bu HALOL — lekin uni faqat inson farqlaydi
    owner: Mahsulot egasi (admin akkaunti bilan)
    trigger: Birinchi deploy — 10-HUMAN-UAT.md #4; natija «N ta sinov so'rovidan M tasi chatga tushdi» shaklida
  - item: Kirill va rus landing matnining davlat auditoriyasi tomonidan o'qilishi — hokimlik proyektorida va telefonda
    why_not_automatable: Transliteratsiya darvozasi lotin harfi qolmaganini o'lchaydi va glossariy taqiqlangan sinonimlarni ushlaydi — ikkalasi ham LUG'AT darajasi. O'lchanMAGANI ma'noning o'zi: tadqiqotda AYNAN shu bo'shliqdan ikki defekt chiqdi (`AI` -> `АИ` va `demonstratsiya` -> `демонстратсия`), ikkalasi ham sof kirill chiqish bergani uchun birorta darvoza ularni ko'rmasdi. Qolgan ~119 kalitda shunga o'xshash semantik siljish bo'lishi mumkin va uni faqat ona tilida o'qiydigan odam ko'radi. Rus matni esa transliteratsiya hosilasi EMAS — u mustaqil yozilgan va uning uslubi hech qanday mexanik o'lchov ostida turmaydi
    owner: Mahsulot egasi (kirill o'qiydigan davlat vakili bilan)
    trigger: Pilot tayyorgarligi haftasi — 10-HUMAN-UAT.md #5; natija «N ta tuzatish kiritildi» ro'yxati bilan
```

---

## Xavfsizlik domeni

> `security_enforcement: true`, `security_asvs_level: 1`, `security_block_on: "high"`

### Qo'llanadigan ASVS toifalari

| ASVS toifasi | Qo'llanadimi | Standart nazorat |
|--------------|--------------|------------------|
| **V2 Autentifikatsiya** | ⚠ **Teskari yo'nalishda** | Marshrut ⛔ **ataylab anonim**; nazorat — `EXEMPT_ROUTES` da **sabab bilan** e'lon + qamrovni integratsiya testida **tiklash** |
| **V3 Sessiya boshqaruvi** | ⛔ **Yo'q** | Landing sessiyaga **tegmaydi**; ⛔ javobda `Set-Cookie` **bo'lmasligi** testda o'lchanadi |
| **V4 Kirish nazorati** | ✅ Ha | `robots.ts` app marshrutlarini `Disallow`; landing ⛔ **hech qanday tenant ma'lumotini o'qimaydi** |
| **V5 Kiruvchi ma'lumot validatsiyasi** | ✅ **Ha — asosiy yuza** | Klient: `zod` + `react-hook-form`; server: **pydantic** sxemasi + ⛔ `sbozor_core.phone.normalize_phone`; ⛔ **server — yagona haqiqat** |
| **V6 Kriptografiya** | ⛔ **Yo'q** | Yangi sir, yangi shifrlash **yo'q**; `telegram_bot_token` — `SecretStr`, **mavjud** |
| **V7 Xato va jurnal** | ✅ Ha | ⛔ Istisno matni Telegram URL'ini (token) tashiydi → `AlertSender._failure()` **majburiy**; `f"...{exc}"` ⛔ **TAQIQ** |
| **V12 Fayl va resurs** | ⛔ **Yo'q** | Landing fayl qabul qilmaydi |
| **V13 API** | ✅ Ha | Rate-limit + honeypot + dwell; ⛔ **DB yozuvi yo'q** → eng kichik yuza |

### `{Next 16 SSG + FastAPI anonim endpoint}` uchun ma'lum tahdid naqshlari

| Naqsh | STRIDE | Standart yumshatish |
|-------|--------|---------------------|
| Forma spam / bot to'ldirish | **DoS** | ⛔ **Uch qatlam:** honeypot (`aria-hidden`, `tabIndex={-1}`) + dwell ≥3 s + ⛔ **server IP chegarasi** (`_bump`). ⛔ CAPTCHA **rad** (SPEC §12.2) |
| Telegram bot tokenining sizishi | **Information Disclosure** | ⛔ Istisno obyekti **umuman ko'rilmaydi**; `_failure()` uch faktni beradi (amal, xato **turi**, status); `SENSITIVE_KEYS` `telegram_bot_token` ni qamraydi |
| Anonim endpoint orqali tenant sizishi | **Information Disclosure** | ⛔ Marshrut RLS kontekstiga **kirmaydi** va `market_id` **so'ramaydi**; javob `{delivered: bool}` — ⛔ tenant izi **yo'q** (testda o'lchanadi) |
| Shaxsiy ma'lumotning saqlanishi | **Repudiation / qonuniy** | ⛔ **DB'ga yozilmaydi** (SPEC §12.5); maxfiylik sahifasi §11.3 bandi 3 buni **e'lon qiladi** |
| Shaxsiy ma'lumotning chegaradan chiqishi | **qonuniy (O'zR)** | ⚠ Telegram serverlari **chegaradan tashqarida** [`alerts.py` 1-taqiq]. ⛔ **Faqat matn** (ism/telefon/bozor nomi) ketadi, ⛔ **rasm/fayl HECH QACHON**; maxfiylik sahifasi buni yozadi |
| JSON-LD orqali skript in'yeksiyasi | **Tampering / XSS** | ⛔ `JSON.stringify(x).replace(/</g,'\\u003c')` — Next'ning **rasmiy** naqshi (CITED) |
| FOUC skripti orqali XSS | **Tampering** | ✅ **Mavjud himoya**: satr **statik**, foydalanuvchi ma'lumoti interpolyatsiya **qilinmaydi**; `localStorage` qiymati **aynan** `light`/`dark`/`sun` ga tekshiriladi [KOD: `layout.tsx:96-98`] |
| SSRF (forma orqali) | **—** | ⛔ **Yuza yo'q** — endpoint URL qabul qilmaydi; `TELEGRAM_API_BASE` ⛔ **konstanta, sozlama emas** |
| Ochiq redirect | **—** | ⛔ **Yuza yo'q** — landing `redirect()` chaqirmaydi (`page.tsx` ning redirect'i **o'chiriladi**) |
| Ma'lumot to'plash uchinchi tomonga | **Information Disclosure** | ⛔ Analitika/piksel **yo'q** (§17.2); veb-shrift **yuklanmaydi**; CDN **yo'q** — ⛔ landing **hech qanday** uchinchi tomon so'rovi qilmaydi |

⛔ **Bloklovchi (`security_block_on: high`) daraja:** yuqoridagilar ichida **HIGH** darajali ochiq band ⛔ **yo'q** — barchasi mavjud mexanizm bilan yopiladi. ⚠ **Yagona shart:** `EXEMPT_ROUTES` qamrovini tiklovchi integratsiya testi ⛔ **yozilmasa**, anonim marshrut **sinovsiz** qoladi va bu **HIGH** ga ko'tariladi.

---

## Zamonaviy holat

| Eski yondashuv | Joriy yondashuv | Qachon o'zgargan | Ta'siri |
|----------------|-----------------|------------------|---------|
| `middleware.ts` | ⛔ **`proxy.ts`** (Node runtime, Edge yo'q) | Next 16 | ⛔ Onlayn next-intl darsliklarining hammasi **eskirgan**; loyihada allaqachon to'g'ri |
| `next/link` + qo'lda locale | `@/i18n/navigation` `Link` | next-intl 4 | Grep darvozasi bilan qulflangan |
| `createSharedPathnamesNavigation` | `createNavigation(routing)` | next-intl 4 | Loyihada allaqachon to'g'ri |
| `@app.on_event` | `lifespan=` | FastAPI 0.93+ | Loyihada allaqachon to'g'ri |
| `tailwind.config.js` | CSS-first `@theme` | Tailwind 4 | ⛔ `--text-hero` **`globals.css`** ga yoziladi |
| `robots.txt` / `sitemap.xml` statik fayl | `robots.ts` / `sitemap.ts` fayl konventsiyasi | Next 13+ App Router | ⛔ `src/app/` ildizida, `[locale]` **ichida emas** |
| `next/og` `ImageResponse` OG uchun | ⛔ **Statik PNG** (bu loyihada) | — | SSG + runtime'siz; SPEC §14.1 [QAROR] |

**Eskirgan / ishlatilmaydigan:**
- ⛔ `middleware.ts` nomi — Next 16 uni **umuman yuklamaydi**, xato ham, ogohlantirish ham **chiqmaydi** (T-01-08)
- ⛔ `arq` (loyiha `taskiq` da) — landing bunga tegmaydi, lekin reja `enqueue` naqshini ko'chirsa `taskiq` ni ishlatadi

---

## Taxminlar jurnali

| # | Da'vo | Bo'lim | Noto'g'ri bo'lsa ta'siri |
|---|-------|--------|---------------------------|
| **A1** | Chrome LCP algoritmi `opacity: 0` elementni «chizilgan» deb hisoblamaydi | Sahna mexanikasi | ⛔ Agar noto'g'ri bo'lsa — `h1` dagi `--i` kechikishi zararsiz va tavsiya (`--i: 0`) ortiqcha ehtiyot bo'ladi. ⚠ Zarar **nol** (o'zgarish baribir foydali) |
| **A2** | `container-type: inline-size` / `cqw` qo'llab-quvvatlashi Chrome 105+ / Safari 16+ / Firefox 110+ | Sahna mexanikasi | ⛔ Eski qurilmada sweep **umuman harakatlanmaydi** (masofa 0). ⛔ SPEC ning zaxira yo'li (`--sweep-distance` ni `offsetWidth` dan) **saqlanadi** — tetigi HUMAN-UAT #3 |
| **A3** | `next build` +3 marshrutning byudjetga qo'shimchasi kichik (<10 s) | Darvoza byudjeti | ⛔ Katta bo'lsa `gate` 41 s zaxirasi **yetmaydi** → W0-13 qayta o'lchovi buni **birinchi** kunda ko'rsatadi |
| **A4** | Backend integratsiya faylining `gate` ga qo'shimchasi <15 s | Darvoza byudjeti | Ayni A3 — o'lchov birinchi to'liq `gate` da |
| **A5** | Refaktordan keyin Turbopack chunk guruhlashi bugungiga o'xshash qoladi | Payload byudjeti | ⛔ **Shuning uchun hech qanday tejash SONI da'vo qilinmadi** — HUMAN-UAT #2 uni o'lchaydi |
| **A6** | `LAND-01…LAND-05` — talab identifikatorlari uchun to'g'ri prefiks | Faza talablari | ⛔ Boshqa prefiks tanlansa — **faqat nom** o'zgaradi, mexanika o'zgarmaydi |
| **A7** | `demo_request_chat_id` ajratish (ops kanalidan) — foydali | Demo-forma yo'li | ⛔ Bo'sh standart bilan **teskari mos** (`telegram_chat_id` ga tushadi) → zarar **nol** |
| **A8** | `LOCALE_LABELS` ni marketing komponentida literal yozish drift bermaydi | B-1 | ⛔ Bersa — `lib/locales.ts` ga ko'chirish **bir qatorlik** muqobil, allaqachon yozilgan |
| **A9** | `test_delivery_surface.py` yangi anonim marshrutni bloklamaydi | Demo-forma yo'li | ⚠ **O'qilmadi** (u `/reconciliation/delivery` ga qaratilgan). ⛔ Reja `pytest tests/integration/test_delivery_surface.py` ni birinchi kunda yugurtirsin |
| **A10** | Docker Compose mavjud va `gate` ning backend yarmi ishlaydi | Muhit | ⛔ Ishlamasa `gate` **umuman** yugurmaydi — bu 10-fazaning muammosi emas, lekin u **birinchi kunda** ko'rinadi |

---

## Ochiq savollar

1. **Chat manzili — sotuv va ops bir kanaldami?**
   - **Bilamiz:** `telegram_chat_id` bugun ops/alert kanali; `alerts_enabled` ikkalasiga bog'liq.
   - **Noaniq:** buyurtmachi sotuv so'rovlarini alohida kanalda ko'rishni xohlaydimi.
   - ⛔ **Tavsiya:** ixtiyoriy `demo_request_chat_id` (bo'sh → `telegram_chat_id`). Bir qatorlik xarajat, keyin **konfiguratsiya** qarori bo'lib qoladi.

2. **`D-11` kirillda `Д-11` — tuzatiladimi?**
   - **Bilamiz:** sahna «namunaviy», ya'ni mos kelmaslik yolg'on emas.
   - **Noaniq:** fazaning *«reklamadagi bilan bir xil»* maqsadiga ta'siri.
   - ⛔ **Tavsiya:** rasta kodini yorliqdan **olib tashlash** (`landing.scene.tagUnpaid` = «Band, lekin to'lovsiz»). Sahna raqami **№16** allaqachon vizual — matnda takrorlash **qiymat qo'shmaydi**.

3. **Xato kodlari zanjiri — registr yoki mahalliy `switch`?**
   - **Bilamiz:** `error-codes.test.mjs` reyestrni **avtomatik kashf qilmaydi**; to'rt yangi kod bor.
   - **Noaniq:** darvoza tahririning narxi vs ko'r nuqta narxi.
   - ⛔ **Tavsiya:** **registr (A varianti)** — D-02 (*«sabab VA tuzatish yo'li»*) bu fazada **G-SUBMIT ostida** ham, forma copy'sida ham talab qilingan; ko'r nuqta uni birinchi backend o'zgarishida yo'q qilardi.

4. **`(marketing)` da `data-theme` ni `light` ga majburlash kerakmi?**
   - **Bilamiz:** SPEC O-03 — **yo'q**, meros olinadi; anonim `localStorage` bo'sh → `light`.
   - **Noaniq:** app'dan `dark` bilan kelgan foydalanuvchi landing'ni qanday o'qiydi.
   - ⛔ **Tavsiya:** SPEC'ning qarori **saqlanadi**. Tetigi HUMAN-UAT; tuzatish **bir qator** (`(marketing)/layout.tsx`), **uchinchi tema scope'i emas**.

5. **G-land-1(c) ning ikkinchi yarmi (fazoviy nom qamrovi) qo'shiladimi?**
   - **Bilamiz:** Tuzoq 1 — reyestr tengligi yolg'iz **yetarli emas**; `MISSING_MESSAGE` faqat brauzerda chiqadi.
   - **Noaniq:** darvozaning narxi (bu — matn skani, ~0,1 s).
   - ⛔ **Tavsiya:** **qo'shiladi.** Narxi nolga yaqin, ushlaydigan xatosi esa ⛔ **build'dan o'tib ketadigan** sinfdan.

---

## Manbalar

### Birlamchi (HIGH ishonch)

- ⛔ **Kodbaza o'lchovlari (shu sessiya, 2026-08-17):** `frontend/src/app/[locale]/layout.tsx`, `page.tsx`, `(app)/layout.tsx`, `(auth)/layout.tsx`, `proxy.ts`, `i18n/routing.ts`, `lib/auth-store.ts`, `lib/api-client.ts`, `lib/api-types.ts`, `components/shell/locale-switcher.tsx`, `components/ui/button.tsx`, `app/globals.css`, `messages/*.json`, `scripts/*.test.mjs`, `vitest.config.ts`, `package.json` (root + frontend)
- ⛔ **Backend:** `services/core-api/app/main.py`, `settings.py`, `worker.py`, `security/ratelimit.py`, `services/alerts.py`, `jobs/outbox.py`, `jobs/alerting.py`, `repositories/outbox_repo.py`, `api/v1/nvr.py`, `packages/sbozor-core/sbozor_core/phone.py`
- ⛔ **Darvozalar:** `tests/tenancy/test_cross_tenant.py` (`EXEMPT_ROUTES`, `EXEMPT_REASON_PREFIXES`, `QUERY_PARAM_ROUTES`), `test_route_coverage.py`, `test_personal_data_coverage.py`
- ⛔ **`services/bot-service/app/main.py`, `settings.py`** — long-polling, DB'siz, HTTP serversiz
- ⛔ **Build artefakti:** `.next/prerender-manifest.json` (81 marshrut), `.next/build-manifest.json`, `.next/static/chunks/**` (chunk o'lchovlari + marker skani)
- ⛔ **Ijro o'lchovlari:** `node --test scripts/*.test.mjs` (2,83 s / 349 test) · `npx vitest run` (172,47 s / 99 fayl / 1170 test)
- ⛔ **Transliteratsiya probasi:** `scripts/gen-cyrillic.mjs` ning `transliterate()` funksiyasi, 46+21 nomzod satr
- **Next 16 rasmiy hujjatlari** (`node_modules/next/dist/docs/`): `route-groups.md`, `01-metadata/sitemap.md`, `01-metadata/robots.md`, `02-guides/json-ld.md`
- **next-intl 4.13.4 tiplari:** `dist/types/shared/NextIntlClientProvider.d.ts`, `dist/types/react-server/NextIntlClientProviderServer.d.ts`

### Ikkilamchi (MEDIUM)

- `.planning/phases/10-landing-sbozor-uz/10-UI-SPEC.md` (APPROVED) — shartnoma; o'lchovlari **mustaqil tasdiqlandi**, bittasi (L-12) **rad etildi**
- `.planning/phases/09-ui-polish-motion-qatlami/09-RESEARCH.md` — jsdom cheklovlari (MEROS, qayta o'lchanmadi)
- `.planning/phases/09-ui-polish-motion-qatlami/09-VALIDATION.md` — YAML frontmatter shakli (presedent)
- `.planning/STATE.md`, `.planning/ROADMAP.md` (Phase 10 SC#1–SC#5), `package.json` `//gate-budget` / `//gate-fast-budget`
- `LANDING-BRIEF.md` (§1–§7), `.claude/skills/sketch-findings-bozor/references/landing-sehri.md`, `sources/003-landing-hero.html`
- `./CLAUDE.md` — stek, litsenziya, data-rezidentlik

### Uchlamchi (LOW — tasdiqlash kutadi)

- Chrome LCP + `opacity: 0` xulqi [A1]
- Konteyner-so'rov birliklarining brauzer qamrovi [A2]
- `test_delivery_surface.py` ning yangi marshrutga ta'siri [A9]

---

## Metadata

**Ishonch taqsimoti:**

| Soha | Daraja | Sabab |
|------|--------|-------|
| Marshrut / route-guruh mexanikasi | **HIGH** | Fayl daraxti, `prerender-manifest`, Next 16 rasmiy hujjati — uchalasi ham o'qildi |
| Provayder ko'chirishi | **HIGH** | Import grafi va `useAuthStore` ning `throw` i **kodda** ko'rildi; next-intl tipi tasdiqlandi |
| Payload sonlari | **MEDIUM-HIGH** | Chunk o'lchovlari **haqiqiy build** dan; ⛔ refaktordan keyingi guruhlash **kafolatlanmagan** [A5] |
| Demo-forma yo'li | **HIGH** | `bot-service` ning HTTP'siz ekani, `AlertSender` ning worker'da yashashi, `EXEMPT_ROUTES` mexanizmi — hammasi kodda |
| Transliteratsiya defektlari | **HIGH** | Loyihaning **o'z** `transliterate()` funksiyasi bilan o'lchandi; ikkala tuzatish ham **sinaldi** |
| Darvoza byudjeti | **HIGH** (test qismi) / **MEDIUM** (build + backend) | Test o'lchovlari shu sessiyada; `next build` va pytest qo'shimchasi **o'lchanmadi** [A3, A4] |
| Sahna / jsdom | **MEDIUM-HIGH** | jsdom cheklovlari MEROS (09-RESEARCH da o'lchangan); LCP + `opacity:0` [A1] |
| Xavfsizlik | **HIGH** | Mavjud taqiqlar va ularning sabablari modul docstringlarida **o'qildi** |
| SEO / fayl konventsiyalari | **HIGH** | Next 16 rasmiy hujjatlaridan **CITED** |

**Tadqiqot sanasi:** 2026-08-17
**Amal qilish muddati:** ⛔ **7 kun** — sabab: `gate` byudjeti va chunk o'lchovlari **bugungi holat**, va ikkalasi ham keyingi commitda o'zgaradi. Marshrut/provayder topilmalari **30 kun** amal qiladi.
