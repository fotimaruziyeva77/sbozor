---
phase: 10-landing-sbozor-uz
plan: 06
subsystem: frontend-landing-sections
tags: [landing, scroll-reveal, intersection-observer, step-line, trust, pilot, faq, honesty]
requires:
  - "10-02 (landing.* 121 kalit, .landing-step-fill + [data-step] selektorlari, tokenlar)"
  - "10-03 (section.tsx qobiq, (marketing) guruhi, toraytirilgan provayder)"
provides:
  - "Reveal — IntersectionObserver'ning YAGONA umumiy ta'rifi (klient oroli; delayIndex/threshold/onReveal kontrakti, 6 test)"
  - "PainCards · Proof · RoleCards · TrustBlock (#ishonch) · Pilot · Faq — Server Component bloklar, har biri Reveal bilan"
  - "StepLine — 3-qadam chizig'i data-step atributi orqali (geometriya 0, reduced-motion'da daraja darhol 3)"
affects:
  - "10-07 (page.tsx kompozitsiyasi shu bloklardan; G-land-1(a) reyestri endi step-line/reveal'ni ham ko'radi)"
tech-stack:
  added: []
  patterns:
    - "Scroll-reveal: boshlang'ich holat KO'RINADIGAN, .motion-enter faqat kirish animatsiyasini QO'SHADI (JS'siz kontent yo'qolmaydi)"
    - "reduced-motion hosila useSyncExternalStore bilan (effektda setState yo'q — react-hooks/set-state-in-effect toza)"
    - "Taqiqlangan token nomlari izohlarda ham literal yozilmaydi (badge.tsx konvensiyasi marketing'ga tatbiq etildi)"
key-files:
  created:
    - frontend/src/components/marketing/reveal.tsx
    - frontend/src/components/marketing/reveal.test.tsx
    - frontend/src/components/marketing/pain-cards.tsx
    - frontend/src/components/marketing/proof.tsx
    - frontend/src/components/marketing/role-cards.tsx
    - frontend/src/components/marketing/trust-block.tsx
    - frontend/src/components/marketing/pilot.tsx
    - frontend/src/components/marketing/faq.tsx
    - frontend/src/components/marketing/step-line.tsx
  modified: []
decisions:
  - "Bloklar O'Z <h2> sini chizadi — 10-07 ularni <Section> bilan TITLE PROP'SIZ o'raydi (aks holda h2 ikkilanadi); proof sarlavhasi karta ICHIDA"
  - "id=\"ishonch\" trust-block.tsx ning o'zida — 10-07 Section'ga id bermasin (dublikat anchor bo'lardi)"
  - "Reveal kontrakti rejadagidan ikki prop keng: threshold (steps 0.4) va onReveal (step-line data-step tetigi) — qo'shimcha observer ochmasdan qayta ishlatish sharti"
  - "step-line reduced-motion: mount-effekt setState o'rniga useSyncExternalStore HOSILASI (server snapshot false -> SSG kadri data-step=0 bilan mos, gidratatsiyadan keyin 3)"
  - "Rol ikonkalari app'ning o'zidan: Banknote (kassir oqimi), Camera (wizard), FileSpreadsheet — yangi aksent yuzasi yo'q (ikonka text-text-muted, da'vo text-accent-text)"
  - "Card'ning meros hover-ko'tarilishi rol/og'riq kartalarida saqlanadi — §17.2 taqig'i YANGI bespoke hover animatsiyasi haqida, dizayn tizimining o'z xulqi emas"
  - "Proof'da dekorativ yulduz/ikonka YO'Q — aksent reyestri (§6.3) yangi aksent yuzasini taqiqlaydi; surface karta farqi yetarli"
metrics:
  duration: "~45 min"
  completed: "2026-08-17T13:30:00Z"
  tasks: 3
  commits: 5
---

# Phase 10 Plan 06: Landing hikoya bloklari Summary

**Bir qator:** `Reveal` (IntersectionObserver'ning yagona ta'rifi, TDD 6/6) + oltita Server Component blok (og'riq/dalil/rollar/ishonch/pilot/FAQ) + `StepLine` `data-step` bilan — geometriya komponentlarda 0, avtomatik harakat 0, pilot raqamsiz, FAQ matni faqat katalogdan.

## Bajarilgan vazifalar

| # | Vazifa | Commit | Kalit fayllar |
|---|--------|--------|---------------|
| 1 (RED) | Reveal xulq kontrakti — yiqiladigan test | `5b52667` | reveal.test.tsx |
| 1 (GREEN) | Reveal + og'riq kartalari + bosh dalil | `7e5043a` | reveal.tsx, pain-cards.tsx, proof.tsx |
| 2 | Rol-kartalar, ishonch bloki, pilot, FAQ | `90bfc3a` | role-cards.tsx, trust-block.tsx, pilot.tsx, faq.tsx |
| 3 | 3-qadam seksiyasi — data-step to'lishi | `c6ddde7` | step-line.tsx |
| docs | SUMMARY | (shu commit) | 10-06-SUMMARY.md |

## Nima qurildi

- **`Reveal`** — `"use client"`, vanilla `IntersectionObserver` (kodbazada birinchi va yagona ta'rif). Boshlang'ich holat KO'RINADIGAN (`opacity:0` yashirish yo'q — JS kelmasa kontent yo'qolmaydi); `prefersReducedMotion()` effektning BIRINCHI qatorida — `true` da observer UMUMAN qurilmaydi; bir martalik guard (`revealedRef`) + `disconnect()` ochilishda VA unmount'da (T-10-12). `delayIndex` -> `--i` (revenue-card naqshi), `threshold` (default 0.2), `onReveal` (bir marta).
- **`PainCards`** — 3 karta (`ui/card` naqshi), stagger 60ms; «patta» glossi katalogda (`pain.a.body`, «kunlik savdo to'lovi») — komponentda literal copy yo'q.
- **`Proof`** — O-07 qabul qilindi: hero'da bir qatorli qulflangan da'vo (10-05 tomoni), bu yerda KENGAYTIRILGAN shakl `surface` kartada: nima kerak (`proof.body`) / nima kerak EMAS (`proof.note`); hero copy'si takrorlanmadi.
- **`RoleCards`** — skrinshot ham, soxta mockup ham YO'Q (T-10-10, §9.3 ning uch o'lchanadigan sababi kod izohida); har rol: meros lucide ikonka (aria-hidden, matn bilan juft) + h3 `text-lg` + 2 jumla `text-sm` + bitta tekshiriladigan da'vo `text-xs text-accent-text`.
- **`TrustBlock`** — `id="ishonch"` blokning o'zida; 4 band katalogdan. Rezidentlik bandi bugungi mexanizmni aytadi, kelajakni va'da qilmaydi (T-10-13); yurist-tasdiq sharti kod izohida (tetigi go-live, bandi 10-08 HUMAN-UAT).
- **`Pilot`** — `Badge tone="warning"` («Karmana bozorida sinovda»), matn raqamsiz (K-7; katalog 10-02 da `\d`=0 o'lchangan, komponent literal qo'shmaydi).
- **`Faq`** — 5 savol native `<details>`/`<summary>` (ARIA akkordeon qurilmadi); savol satri ≥44px (§15.10, py-4 bilan 60px); matn FAQAT `landing.faq.*` dan — 10-07 JSON-LD ayni manbadan o'qiydi (T-10-14).
- **`StepLine`** — `"use client"`; komponent faqat `data-step="0..3"` yozadi, `scaleY` darajalari va 900ms `globals.css` da (10-02); tetik — `Reveal` qayta ishlatildi (`threshold: 0.4`, `onReveal` -> `Math.max`); sketch'ning balandlik-tranzitsiyasi takrorlanmadi (L-8). Reduced-motion: `useSyncExternalStore` hosilasi bilan daraja darhol 3 — SSR kadri (`data-step="0"`) bilan gidratatsiya mos.

## Reja bo'yicha o'lchovlar (verification)

| O'lchov | Natija |
|---------|--------|
| `npm test` (22 skript darvozasi + vitest) | **350/350** + **1181/1181 (101 fayl)** yashil |
| `reveal.test.tsx` | **6/6** (beshala reja bandi + onReveal kontrakti) |
| `typecheck` / `lint` / `next build` | exit 0 / exit 0 / **exit 0 (81 marshrut prerender)** |
| `glossary.test.mjs` | 9/9 |
| Taqiq tokenlari 9 faylda (`text-base`/`text-3xl`/`text-[`/`font-medium`/`text-display`/`text-hero`/`py-16`/`py-24`/taymerlar) | **0** (py-16/py-24 faqat section.tsx da — 10-03 holicha) |
| Inline `style` geometriyasi (`height`/`width`/`left`/`top`) | **0** (yagona inline style — `--i` indeksi) |
| `components/marketing/**` da taymer chaqiruvlari | **0 fayl** |
| `id="ishonch"` | trust-block.tsx da bor; `<details` faq.tsx da 5 dona |

## Sabotaj o'lchovlari

**1. `role-cards.tsx` ga `setInterval(() => {}, 60_000)` (modul darajasida, import qilinadigan holda):**
- **O'lchandi:** `npm test` **350/350 + 1181/1181 YASHIL**, lint **toza** — **bugun HECH NIMA qizarmaydi**. Bu o'lchangan bo'shliq: bironta darvoza marketing fayllarida taymer chaqiruvini skanerlamaydi. **10-07 dagi G-land-3(c) shu teshikni yopadi** — u yozilganda bu sabotaj qizarishi shart.
- Qaytarildi (`git checkout -- <fayl>`), keyingi grep: 0.

**2. `pilot.tsx` JSX'iga `{"30% o'sish"}` literal (katalogga TEGILMASDAN):**
- **O'lchandi:** `npm test` **to'liq YASHIL**, lint **toza** — **bugun HECH NIMA qizarmaydi**. G-land-4(e)/(f) (10-07) uni yopadi. ⚠ **10-07 rejalovchisiga nuans:** (e)/(f) SPEC'da `landing.*` KATALOG qiymatlarini skanerlaydi — bu sabotaj esa KOMPONENT literalidir; yopish uchun G-land-4 komponent-matn kanalini ham qamrashi kerak (G-land-4(d) FAQ uchun shu sinfni allaqachon nazarda tutadi — pilot/marketing bloklariga ham ayni satr-skan kengaytmasi kerak bo'ladi).
- Qaytarildi, keyingi grep: 0.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Lint] reveal.test.tsx JSX apostrof xatosi**
- **Found during:** Task 1 GREEN verifikatsiyasi
- **Issue:** `react/no-unescaped-entities` — JSX matnida `'` (uz-Latn apostrofi)
- **Fix:** String ifoda `{"…ko'rinadigan…"}`; assertlar o'zgarmadi
- **Commit:** `7e5043a`

**2. [Rule 1 - Lint] step-line.tsx da `react-hooks/set-state-in-effect`**
- **Found during:** Task 3 lint
- **Issue:** Reja «mount effekti darajani 3 ga qo'ysin» dedi — effektda sinxron `setStep(3)` lint xatosi beradi (kaskadli render qoidasi)
- **Fix:** `useSyncExternalStore` hosilasi (no-op obuna, server snapshot `false`) — xulq kontrakti AYNI (reduced-motion'da daraja darhol 3, SSG kadri mos), mexanizm toza. `lib/motion.ts` sarlavhasi bu qatlamni oldindan nazarda tutgan («useSyncExternalStore qatlami kerak bo'lsa…»); yagona iste'molchi bo'lgani uchun alohida lib-hook ochilmadi (files_modified chegarasi)
- **Commit:** `c6ddde7`

**3. [Rule 2 - Konvensiya] Taqiqlangan token nomlari izohlardan olib tashlandi**
- **Found during:** Task 2 taqiq-token o'lchovi
- **Issue:** pain-cards/reveal/step-line izohlarida taymer-chaqiruv nomlari va balandlik xossasi LITERAL yozilgan edi — bo'lajak G-land-3 satr-skani (va badge.tsx dagi mavjud kodbaza konvensiyasi: «taqiqlangan utilita nomi izohda literal yozilmaydi») bunga qoqilardi
- **Fix:** Izohlar aylanma ifoda bilan qayta yozildi; kod o'zgarmadi
- **Commits:** `90bfc3a`, `c6ddde7`

### Reja ruhida qabul qilingan mikro-qarorlar

- `Reveal` kontrakti rejadagi minimal shakldan ikki prop keng (`threshold`, `onReveal`) — rejaning «Mumkin bo'lsa Reveal primitivini qayta ishlating» sharti aynan shu ikkalasisiz bajarilmasdi (aks holda step-line ikkinchi observer to'plamini ochardi).
- FAQ `<summary>` da display o'zgartirilmadi (`flex` bilan native marker yo'qolardi) — balandlik `py-4` bilan.
- Blok sarlavhalari komponentlarning O'ZIDA (`<h2 class="text-2xl">`): §15.11 ierarxiyasi bir faylda to'liq o'qiladi va 10-07 kompozitsiyasi «dumb stacking» bo'ladi. **10-07 uchun shartnoma:** `<Section>` bu bloklarni `title` PROP'SIZ va (trust-block uchun) `id` SIZ o'raydi.

## Deferred Issues

- **`next build` stderr'ida `Error: ENVIRONMENT_FALLBACK` loglari** — `app-guard.tsx` chunk'idan (10-03 fayli, bazada mavjud), exit code 0, 81 marshrut prerender bo'ladi. Mening fayllarim import zanjirida emas — scope tashqarisida, tuzatilmadi. Egasi: 10-07/10-08 (build-log gigiyenasi yoki Next 16 ma'lum xulqi sifatida hujjatlash).

## TDD Gate Compliance

Task 1 (`tdd="true"`): RED `5b52667` (test; yiqilish tasdiqlandi — modul mavjud emas, 1 failed) → GREEN `7e5043a` (feat; 6/6). Gate ketma-ketligi to'liq, REFACTOR bosqichi talab qilinmadi.

## Known Stubs

Yo'q — barcha bloklar haqiqiy katalog matni bilan; platsholder/TODO/bo'sh massiv UI'ga oqmaydi. (Bloklar hali sahifaga ulanmagan — bu 10-07 ning `page.tsx` kompozitsiyasi, reja shunday bo'lgan.)

## Threat Flags

Yangi yuza yo'q (tarmoq so'rovi 0, auth yo'li 0, tenant so'rovi 0 — landing bloklari faqat katalog o'qiydi). Reja threat-registri qo'llandi: **T-10-10** (skrinshot/mockup 0 — da'vo matn bilan), **T-10-13** (pilot raqamsiz + rezidentlik bugungi mexanizm tilida + yurist-tasdiq izohi), **T-10-14** (FAQ literal 0 — faqat katalog), **T-10-21** (to'lish `scaleY`, geometriya komponentda 0), **T-10-12** (bir martalik guard + disconnect ochilish/unmount — testda qulflangan).

## Self-Check: PASSED

- [x] 9 fayl mavjud: reveal.tsx/.test.tsx, pain-cards, proof, role-cards, trust-block, pilot, faq, step-line
- [x] Commitlar mavjud: `5b52667`, `7e5043a`, `90bfc3a`, `c6ddde7`
- [x] `id="ishonch"` trust-block.tsx da; `data-step` step-line.tsx da; `<details` faq.tsx da
- [x] Sabotajlar qaytarilgan (grep: 0/0); ish daraxti toza
- [x] STATE.md / ROADMAP.md TEGILMADI
