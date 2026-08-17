---
phase: 10-landing-sbozor-uz
plan: 03
subsystem: frontend-routing-providers
tags: [landing, marketing, route-group, providers, payload, locale-switcher, ssg]
requires:
  - "10-02 (landing.* 121 kalit uch tilda, tokenlar)"
provides:
  - "MarketingLocaleSwitcher — anonim, zod grafisiz, AuthProvider'siz (B-1/B-2 yopildi)"
  - "shell/app-providers.tsx — beshala provayderning YAGONA ta'rifi"
  - "shell/app-guard.tsx — (app) sessiya darvozasining yangi uyi (tana ayna)"
  - "(marketing) route-guruhi: layout {common,landing} toraytirilgan provayder bilan"
  - "(marketing)/page.tsx — anonim ildiz QOBIG'I (redirect o'chirildi, SC#1)"
  - "marketing/section.tsx — py-16/md:py-24 ning yagona uyi (+h2 title, id ankerlar)"
  - "marketing/header.tsx (skip-link, brand, switcher, kirish) + footer.tsx"
affects:
  - "10-04..10-07 (landing kompozitsiyasi shu qobiq ustiga; page.tsx 10-07 da qayta yoziladi)"
  - "G-land-1(a) reyestri endi 5 klient orolini kutadi (locale-switcher beshinchi)"
tech-stack:
  added: []
  patterns:
    - "Route-guruh provayder chegarasi: guruh layouti server qobiq, klient provayderga locale/messages oshkora uzatiladi"
    - "Klient orolining import-graf quli: modul manbasi satr skani testda (B-2 regressiya)"
    - "next-intl toraytirish qo'lda obyekt bilan (4.13.4 da pick yo'q)"
key-files:
  created:
    - frontend/src/components/marketing/locale-switcher.tsx
    - frontend/src/components/marketing/locale-switcher.test.tsx
    - frontend/src/components/shell/app-providers.tsx
    - frontend/src/components/shell/app-guard.tsx
    - frontend/src/app/[locale]/(marketing)/layout.tsx
    - frontend/src/app/[locale]/(marketing)/page.tsx
    - frontend/src/components/marketing/header.tsx
    - frontend/src/components/marketing/footer.tsx
    - frontend/src/components/marketing/section.tsx
  modified:
    - frontend/src/app/[locale]/layout.tsx
    - frontend/src/app/[locale]/(app)/layout.tsx
    - frontend/src/app/[locale]/(app)/layout.test.tsx
    - frontend/src/app/[locale]/(auth)/layout.tsx
    - frontend/scripts/wizard-reachability.test.mjs
  deleted:
    - frontend/src/app/[locale]/page.tsx
decisions:
  - "AppGuard alohida klient faylga (shell/app-guard.tsx): klient NextIntlClientProvider locale'siz throw qiladi (4.13.4 manbasida o'lchandi) — AppLayout majburan server qobiq, hook tanasi esa klient modulda"
  - "(app)/(auth) layoutlari async server: hasLocale + setRequestLocale + getMessages, locale/messages AppProviders'ga oshkora"
  - "layout.test.tsx AppGuard'ni o'lchaydi (async server komponent jsdom'da render bo'lmaydi); layout qobig'ining o'zi next build prerender bilan o'lchanadi — sabotaj shu yo'lda qizardi"
  - "footer {year} ICU argumentiga SATR: raqam berilsa ICU guruhlash «2 026» chiqarardi"
  - "prerender-manifest kalitlari ICHKI locale qiymatlari (/uz-Latn, /uz-Cyrl, /ru) — verify regexi shunga moslandi (URL prefiksi rewrite qatlamida)"
metrics:
  duration: "~55 min"
  completed: "2026-08-17T12:40:00Z"
  tasks: 3
  commits: 5
---

# Phase 10 Plan 03: Anonim switcher, provayder ko'chirishi va (marketing) qobiq Summary

**Bir qator:** `MarketingLocaleSwitcher` (importsiz-zod, provayder-talabsiz) AVVAL yozilib B-1/B-2 yopildi, so'ng beshala provayder ildizdan `(app)`/`(auth)` ga tushdi va `(marketing)` guruhi anonim ildizni oldi — o'lchandi: ildiz JS **287.8→208.4 KB gz (−79.4)**, HTML(ru) **32.3→8.0 KB gz (−24.3)**, dashboard nazorati **o'zgarishsiz** (348.2).

## Bajarilgan vazifalar

| # | Vazifa | Commit | Kalit fayllar |
|---|--------|--------|---------------|
| 1 (RED) | Yiqiladigan test — B-1/B-2 kontrakti | `360b435` | locale-switcher.test.tsx |
| 1 (GREEN) | Anonim MarketingLocaleSwitcher | `2504407` | locale-switcher.tsx |
| 2 | AppProviders/AppGuard ajratish, ildiz tozalash | `aae66b0` | app-providers.tsx, app-guard.tsx, 3 layout, layout.test.tsx |
| 2 (deviation) | wizard-reachability darvozasi yangi uyga | `dd85d81` | wizard-reachability.test.mjs |
| 3 | (marketing) guruhi + qobiq, redirect o'chirildi | `48de7b1` | (marketing)/{layout,page}.tsx, header/footer/section.tsx |

## Nima qurildi

- **Anonim til almashtirgich** — `shell/` dagining sirg'anuvchi-indikator naqshi ayna, lekin: profil yozuvi yo'q, sessiya o'qish yo'q, `LOCALES`/`LOCALE_LABELS` literal (endonim — drift manbasi yo'q, A8). B-2 quli MEXANIK: test modul manbasini satr skani bilan tekshiradi (`api-client`/`api-types`/`auth-store`/`next/navigation` — 0 uchrashuv, izohda ham).
- **`AppProviders`** — beshala provayder yagona ta'rifda, tartib ayna (i18n→nuqs→query→auth; `Toaster` `AuthProvider` ichida, `{children}` yonida). `locale`+`messages` majburiy prop: klient provayder locale'siz throw qiladi (next-intl 4.13.4 `shared/NextIntlClientProvider.js:9-10` da o'lchandi).
- **`AppGuard`** — `(app)/layout.tsx` sobiq tanasining ayna ko'chirilishi (sessiya tiklash, `mustChangePassword`/`select-market` redirectlari, usta istisnosi, skelet — bironta shart o'zgarmadi, T-10-16).
- **Ildiz layout** — faqat `<html>`+FOUC skripti (bayt-ba-bayt tegilmadi)+`<body>`+`generateStaticParams`+`generateMetadata`.
- **`(marketing)`** — layout `setRequestLocale` birinchi, klientga AYNAN `{common, landing}`; page — qobiq (Header + bitta Section'da `h1 text-2xl` + Footer), sessiya redirecti YO'Q, `cookies()`/`headers()`/`searchParams` 0.
- **Qobiq komponentlari** — `section.tsx` (`py-16 md:py-24` YAGONA uyda — grep: faqat shu faylda), `header.tsx` (skip-link birinchi fokus, ≥44px nishonlar, sticky emas, tema tugmasi yo'q), `footer.tsx` (maxfiylik havolasi, env telefon bilan aloqa, ©, harakat yo'q).

## Reja bo'yicha o'lchovlar (verification)

| O'lchov | Natija |
|---------|--------|
| `next build` | exit 0; prerender **81 marshrut** (kamaymadi), ildiz **3/3** (`/uz-Latn`,`/uz-Cyrl`,`/ru`) |
| `npm test` (22 skript darvozasi + vitest) | **100 fayl / 1175 test yashil** |
| `typecheck` / `lint` | exit 0 / exit 0 |
| `py-16`/`py-24` | faqat `section.tsx` (src bo'ylab grep — 1 kod qatori) |
| Anonim HTML (uz-Latn) | landing sarlavhasi **bor**, `dashboard` **0**, `shell.loading` satri **0**; dashboard.html'da o'sha satr **1** (ikki tomonlama toraytirish dalili) |

## Payload jadvali — OLDIN/KEYIN (HUMAN-UAT #2 dalili)

O'lchov usuli: prerender HTML'dagi `<script src>` chunklari gzip(9) yig'indisi + HTML gzip (RSC flight'dagi katalog shu yerda). Ikki nusxa saqlab olindi (build route jadvallari bilan birga).

| Marshrut | JS gz OLDIN | JS gz KEYIN | Δ JS | HTML gz OLDIN | HTML gz KEYIN | Δ HTML |
|----------|-------------|-------------|------|----------------|----------------|--------|
| `/uz-Latn` (ildiz) | 287.8 KB | 208.4 KB | **−79.4 KB** | 26.3 KB | 6.9 KB | **−19.4 KB** |
| `/uz-Cyrl` (ildiz) | 287.8 KB | 208.4 KB | **−79.4 KB** | 30.0 KB | 7.7 KB | **−22.3 KB** |
| `/ru` (ildiz) | 287.8 KB | 208.4 KB | **−79.4 KB** | 32.3 KB | 8.0 KB | **−24.3 KB** |
| `/ru/dashboard` (nazorat) | 348.2 KB | 348.2 KB | **0** | 33.0 KB | 32.9 KB | ~0 |

Xom JS: 1033.6→695.7 KB. Ru anonim tashrifchi jami **~103.7 KB gzip** kam yuklaydi. «~110 KB tejaladi» degan OLDINDAN da'vo berilmagan edi — bu jadval o'lchov (Turbopack chunk chegaralari refaktordan keyin qayta hisoblangan holda).

## Sabotaj o'lchovlari

**1. (reja #5) `(app)/layout.tsx` da guard provayderdan TASHQARIGA chiqarildi** (`<AppGuard><AppProviders>...` — modul import qilinadigan holda):
- **O'lchandi:** `next build` **exit 1** — `Error occurred prerendering page "/uz-Latn/review/blind"` (useAuthStore provayder tashqarisida throw — Tuzoq 3 ning bevosita mexanikasi). Eslatma: `layout.test.tsx` bu sabotajni KO'RMAYDI (u AppGuard'ni to'g'ridan-to'g'ri o'lchaydi) — reja aytgan «yoki next build» sharti build tomonida bajarildi.
- Qaytarildi: `git checkout -- (app)/layout.tsx`, keyingi build yashil.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Reja verify buyrug'idagi xato] prerender-manifest kalitlari URL prefiksi emas**
- **Found during:** Bazaviy o'lchov (birorta o'zgarishdan OLDIN)
- **Issue:** Reja regexi `/^\/(uz|uz-cyrl|ru)$/` — manifest esa ICHKI locale qiymatlarini saqlaydi (`/uz-Latn`, `/uz-Cyrl`, `/ru`); bazada ham faqat `/ru` mos kelardi (roots=1 → verify har doim qizil)
- **Fix:** Tekshiruv `/^\/(uz-Latn|uz-Cyrl|ru)$/` bilan — semantika ayni (uch ildiz SSG'da), URL prefikslari rewrite qatlamida
- **Commit:** o'lchov buyrug'i (kodga tegilmadi)

**2. [Rule 3 - Bloklovchi] AppGuard uchun yangi fayl: `shell/app-guard.tsx` (reja ro'yxatida yo'q edi)**
- **Found during:** Task 2
- **Issue:** Reja «ikki komponent» dedi, lekin fayl ko'rsatmadi. `(app)/layout.tsx` klientligicha qolsa `messages`/`locale` ni olib BO'LMAYDI: klient `NextIntlClientProvider` locale'siz throw qiladi (4.13.4 manbasida o'lchandi), katalogni klient importi esa uch tilni bundle'ga qo'shardi. Bitta faylda esa server layout + klient hook tanasi birga yashay olmaydi
- **Fix:** `AppLayout` — async server qobiq (`hasLocale`+`setRequestLocale`+`getMessages`); tana AYNAN `shell/app-guard.tsx` ga (`"use client"`)
- **Files modified:** frontend/src/components/shell/app-guard.tsx, (app)/layout.tsx
- **Commit:** `aae66b0`

**3. [Rule 3 - Bloklovchi] `wizard-reachability.test.mjs` darvozasi eski manzilni o'qirdi**
- **Found during:** To'liq `npm test` (Task 3 verifikatsiyasi)
- **Issue:** Darvoza usta-istisno MEXANIZMINI `(app)/layout.tsx` manbasidan qulflagan — mexanizm `app-guard.tsx` ga ko'chgach 1-to'siq qizardi
- **Fix:** Manba yo'li yangi uyga; ASSERTLARNING BIRORTASI O'ZGARMADI (o'lchov yuzasi ayni)
- **Files modified:** frontend/scripts/wizard-reachability.test.mjs
- **Commit:** `dd85d81`

**4. [Rule 1 - Test infratuzilma] jsdom'da `import.meta.url` file-sxema emas + tsc tip toraytirish**
- **Found during:** Task 1 GREEN / Task 2 typecheck
- **Fix:** manba skani yo'li `process.cwd()` dan; `renderSwitcher` parametri Locale ittifoqi
- **Commit:** `2504407`, `aae66b0`

### Zaruriy test tahriri (reja ruxsati doirasida)

`(app)/layout.test.tsx` endi `AppGuard`ni render qiladi (async server komponent jsdom'da render bo'lmaydi). O'lchanayotgan xulq TO'LIQ saqlandi: 5 test (usta istisnosi, nazorat redirecti, parol darvozasi ustunligi, T-02-140 tenglik, bozorli sessiya) — bironta assert o'zgarmadi, faqat render nishoni. Layout qobig'ining o'zi build prerender bilan o'lchanadi (yuqoridagi sabotaj isboti).

## TDD Gate Compliance

Task 1 (`tdd="true"`): RED `360b435` (test, yiqilishi tasdiqlandi — modul yo'q) → GREEN `2504407` (feat, 5/5). Gate ketma-ketligi to'liq.

## Known Stubs

| Stub | Fayl | Sabab |
|------|------|-------|
| Qobiq sahifa (hero/seksiyalar/forma/metadata yo'q) | `(marketing)/page.tsx` | ATAYIN — reja «bu to'lqinda u QOBIQ» deydi; 10-07 shu faylni qayta yozadi |
| `/maxfiylik` havolasi hozircha 404 | `footer.tsx` | Sahifa shu fazaning keyingi rejasida (K-8); havola reja buyrug'i bilan qo'yildi |
| Aloqa telefoni faqat `NEXT_PUBLIC_CONTACT_PHONE` berilganda | `footer.tsx` | O-06 — env'siz yolg'on kanal ko'rsatilmaydi |

## Threat Flags

Yangi yuza yo'q. Reja threat-registri qo'llandi: **T-10-15** (klientga aynan `["common","landing"]` — HTML darajasida ikki tomonlama o'lchandi), **T-10-16** (AppGuard shartlari ayna — layout.test 5/5 + wizard-reachability darvozasi yashil), **T-10-17** (`PATCH /me` yuzasi anonim sahifadan ochilmadi — manba skani quli), **T-10-18** (`redirect()` chaqiruvi o'chirildi — landing hech qayerga yo'naltirmaydi).

## Self-Check: PASSED

- [x] `frontend/src/components/marketing/locale-switcher.tsx` + `.test.tsx` mavjud
- [x] `frontend/src/components/shell/app-providers.tsx` (`AuthProvider` bor) va `app-guard.tsx` mavjud
- [x] `frontend/src/app/[locale]/(marketing)/layout.tsx` (`messages.landing` bor) va `page.tsx` mavjud
- [x] `frontend/src/app/[locale]/page.tsx` MAVJUD EMAS (ataylab o'chirildi)
- [x] `header.tsx`/`footer.tsx`/`section.tsx` mavjud; `py-16`/`py-24` faqat section.tsx da
- [x] Commitlar mavjud: `360b435`, `2504407`, `aae66b0`, `dd85d81`, `48de7b1`
- [x] STATE.md / ROADMAP.md TEGILMADI
