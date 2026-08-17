---
phase: 10-landing-sbozor-uz
plan: 02
subsystem: frontend-i18n-tokens
tags: [landing, i18n, tokens, tailwind, transliteration, copy]
requires: []
provides:
  - "--text-hero (+line-height +letter-spacing) @theme tokeni"
  - "@keyframes sweep + .landing-sweep (+.landing-sweep-frame konteyner sinfi)"
  - ".landing-step-fill + [data-step=1..3] selektorlari (scaleY, height EMAS)"
  - "Button size=\"hero\" (min-h-14 px-8 text-lg)"
  - "landing.* fazoviy nomi — 121 kalit × 3 til (uz-Latn/ru qo'lda, uz-Cyrl generatsiya)"
  - "AI akronimining JUFT tuzatishi (overrides + allowed regeks + L-11 unit testi)"
affects:
  - "10-03..10-07 (barcha frontend landing rejalar tayyor matn/token ustida ishlaydi)"
  - "10-04/10-08 (form.error.* xato-kod xaritasi iste'molchilari)"
tech-stack:
  added: []
  patterns:
    - "Tailwind 4 @theme token kengaytmasi (--text-display naqshi bo'yicha)"
    - "container-type: inline-size + 100cqw (sof CSS sweep masofasi)"
    - "data-step atribut selektorlari — geometriya faqat globals.css'da"
key-files:
  created:
    - .planning/phases/10-landing-sbozor-uz/deferred-items.md
  modified:
    - frontend/src/app/globals.css
    - frontend/src/components/ui/button.tsx
    - frontend/messages/uz-Latn.json
    - frontend/messages/ru.json
    - frontend/messages/uz-Cyrl.json (generatsiya)
    - frontend/messages/uz-Cyrl.overrides.json
    - frontend/scripts/gen-cyrillic.test.mjs
decisions:
  - "B-3 A varianti: scene.marketLabel 'demonstratsiya' → 'namoyish' (override o'smaydi, so'z o'zbekcha)"
  - "scene.tagUnpaid'dan '— D-11' olib tashlandi (kirillda Д-11; raqam sahnada vizual ko'rinadi)"
  - "AI akronim sifatida saqlanadi — sun'iy intellektga almashtirilmaydi (brief §6, NVR/VPN izchilligi)"
  - "uz copy'da 'NVR'ingiz' kabi qo'shimchali akronim yozilmadi (НВРъингиз tuzog'i — B-3 sinfi)"
  - "uz privacy s7'da 'cookie' so'zi ishlatilmadi ('kuzatuv fayli') — c harfi transliteratorda yo'q, override 1 yozuvdan oshmasin"
metrics:
  duration: "~21 min"
  completed: "2026-08-17T11:14:16Z"
  tasks: 3
  commits: 3
---

# Phase 10 Plan 02: Landing tokenlar va uch tilli copy katalogi Summary

**Bir qator:** `--text-hero` clamp(28→44px) + `sweep`/`.landing-step-fill` GPU-toza CSS + `Button hero` + `landing.*` 121 kalit uch tilda (B-3 `namoyish` tuzatishi, `AI` JUFT quli, pilot raqamsiz).

## Bajarilgan vazifalar

| # | Vazifa | Commit | Kalit fayllar |
|---|--------|--------|---------------|
| 1 | globals.css tokenlari, sweep, step-fill, Button hero | `d829dac` | globals.css, button.tsx |
| 2 | landing fazoviy nomi — uz-Latn va ru (121 kalit) | `bfea81f` | uz-Latn.json, ru.json |
| 3 | AI JUFT tuzatishi + uz-Cyrl generatsiya + deferred | `1c650c3` | uz-Cyrl.overrides.json, gen-cyrillic.test.mjs, uz-Cyrl.json, deferred-items.md |

## Nima qurildi

- **`@theme` kengaytmasi:** `--text-hero: clamp(1.75rem, 4.4vw, 2.75rem)` + line-height 1.15 + letter-spacing -0.02em, `--text-display`dan keyin, izohda `text-display` nega ishlatilmagani LITERAL (pul roli, `TEXT_DISPLAY_FILES` deepEqual quli).
- **`@keyframes` reyestri 8→9:** `sweep` (faqat `transform: translateX(0→100cqw)`) — sketch'ning `left: 0→100%` shakli ATAYIN takrorlanmadi (`left` — `BANNED_KEYFRAME_PROPS`da, L-8). `.landing-sweep-frame` (`container-type: inline-size`) — `cqw` konteynerga bog'lanishi uchun; nur chizig'i konteyner FARZANDI bo'lishi sharti izohda.
- **3-qadam chizig'i:** `.landing-step-fill` `transform: scaleY()` + `transform-origin: top` + `transition: transform 900ms var(--ease-out)`; uch `[data-step]` darajasi (0.3333/0.6667/1). 900ms kompozit qiymat faqat globals.css'da.
- **`Button size="hero"`:** `min-h-14 px-8 text-lg`; `variant`/`defaultVariants` tegilmadi.
- **`landing.*` — 121 kalit** (meta 3 · nav 2 · hero 6 · trust 4 · scene 15 · pain 7 · steps 7 · proof 3 · roles 10 · trustBlock 9 · pilot 3 · faq 11 · form 21 · footer 4 · privacy 16), uz-Latn/ru kalit to'plamlari AYNAN teng, ru mustaqil tarjima. K-2 qulflangan 11 matn ayna ko'chirildi. `common`ga yangi kalit qo'shilmadi.
- **Xato-kod zanjiri kalitlari:** `form.error.{body,bodyNoPhone,rateLimited,validation}` + 5 `form.validation.*` — 4 backend kodi (`rate_limited`/`invalid_phone`/`validation_error`/`delivery_failed`) xaritasi uchun tayyor; `{phone}` ICU argumenti uchala tilda ayni nomda, raqamsiz shox `bodyNoPhone` (O-06).
- **AI JUFT tuzatishi:** `"AI": "AI"` overrides `words`da (IR yonida) + `allowed` regeksda + yangi `L-11` unit testi. `uz-Cyrl.json` faqat `i18n:gen`dan (drift 0).

## Reja bo'yicha o'lchovlar (verification)

| O'lchov | Natija |
|---------|--------|
| `i18n:check` | exit 0 — **1494 kalit × 3 til**, kalit va ICU parity to'liq |
| `test:unit` | **350/350** yashil (typography, motion-tokens, theme-tokens, contrast, glossary, gen-cyrillic hammasi) |
| `lint` / `typecheck` | exit 0 / exit 0 |
| Kalit soni | **121 ≥ 110**, uz-Latn va ru to'plamlari `deepEqual` teng |
| `pilot.*` da `\d` | **0** |
| `demonstratsiya` / `— D-11` | katalogda **0** |
| Taqiqlangan da'vo tokenlari (jonli, %, martaga, в разы, гарантир, kafolatlaymiz, eng yaxshi, лучший, №1) | landing.* da **0** (hosila skan bilan o'lchandi) |
| Glossariy taqiqlari (yig'im/do'kon/лавк/магазин) | **0**; patta glossi `kunlik savdo to'lovi` faqat `pain.a.body`da |
| uz landing'da `/[a-z]+ts[iy]/` tokenlar | **0** (G-land-4(g) uchun toza baza) |
| Yangi npm paketi | **0** (package.json diff bo'sh) |

## Sabotaj o'lchovlari

**1. `AI` overrides'dan olib tashlanadi (regeks qoladi):**
- **Birinchi o'lchov (tuzatishdan oldin):** `gen-cyrillic.test.mjs` **66/66 YASHIL qoldi** — chiqish sof kirill (`АИ`) bo'lgani uchun lotin-qoldiq testi ko'rmaydi; faqat `i18n:gen --check` drift'i qizardi. Rejaning «gen-cyrillic.test.mjs qizarishi SHART» da'vosi bu yo'nalishda o'lchov bilan RAD etildi.
- **Tuzatish (Rule 2):** IR/T-10 naqshida `L-11` unit testi qo'shildi (`transliterate("AI band rastani aniqlaydi")` === `AI банд растани аниқлайди`).
- **Ikkinchi o'lchov (tuzatishdan keyin):** sabotaj **fail 1** beradi (`АИ банд растани аниқлайди` actual) — juftlik endi test faylining o'zida ikki tomonlama qulflangan.

**2. `.landing-step-fill`ga `transition: height 900ms` qo'shiladi:**
- **O'lchandi:** `test:unit` 350/350 YASHIL, lint toza — **bugun HECH NIMA qizarmaydi**. Bu L-8'ning o'lchangan bo'shlig'i: `motion-tokens.test.mjs` faqat `@keyframes` bloklarini parse qiladi, sinflardagi `transition:` deklaratsiyasini o'qimaydi. **10-07 dagi G-land-3(a) shu teshikni yopadi** — u yozilganda bu sabotaj qizarishi shart.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - JUFT qulf bir tomonlama edi] gen-cyrillic.test.mjs'ga L-11 unit testi qo'shildi**
- **Found during:** Task 3 sabotaj o'lchovi
- **Issue:** Rejaning sabotaj bandi «AI overrides'dan olib tashlansa gen-cyrillic.test.mjs qizarishi SHART» dedi; o'lchov 66/66 yashil ko'rsatdi (faqat drift qizaradi — u esa `uz-Cyrl.json` qayta generatsiya qilinsa jimgina yashilga qaytadi).
- **Fix:** Mavjud IR (T-10) / Telegram (T-11) testlari naqshida `AI` uchun unit test — endi overrides tomoni ham test faylida qizaradi.
- **Files modified:** frontend/scripts/gen-cyrillic.test.mjs
- **Commit:** `1c650c3`

### Copy-darajadagi mikro-qarorlar (reja ruhida, katalog toza qolishi uchun)

- `NVR'ingiz` kabi apostrof-qo'shimchali akronim yozilmadi — transliterator `NVR'ingiz`ni bitta token sifatida `НВРъингиз`ga aylantirardi (B-3 bilan ayni sinf, sof kirill chiqish darvozadan o'tardi). O'rniga `tizim NVR orqali ... kadr oladi`.
- uz privacy 7-bo'limda `cookie` so'zi ishlatilmadi (`c` harfi transliterator xaritasida yo'q → `Cооkие` aralash chiqish, lotin-qoldiq darvozasi qizarardi; override esa «aynan bitta yozuv — AI» cheklovini buzardi). uz: `marketing kuzatuv fayli`; ru'da `Cookie` qoldi (ru skanerlanmaydi).
- `sbozor.uz` domeni copy'ga kiritilmadi (`sbozor`/`uz` tokenlari `сбозор.уз` bo'lardi) — `SBOZOR sayti` yozildi.

## Meros defekt (deferred)

`Deklaratsiya` (×3, `collect.shiftConfirmBody`) va `deklaratsiya` (×1, `billing.emptyShiftsHint`) → bugun `Декларатсия` (to'g'risi `Декларация`). **10-fazada tuzatilmadi** (scope boundary, 08-20 presedenti) — `.planning/phases/10-landing-sbozor-uz/deferred-items.md`da band sifatida: sinf `-tsiya → тсия` semantik transliteratsiya defekti, egasi keyingi i18n ishi, tetigi rus/kirill UAT'i. Shu sababdan G-land-4(g) darvozasi (10-07) `landing.*` bilan chegaralanishi SHART.

## Known Stubs

Yo'q — bu reja komponent yozmaydi; barcha kalitlar haqiqiy qiymatlar bilan to'ldirilgan, platsholder matn (`TODO`/`coming soon`) 0.

## Threat Flags

Yo'q — yangi tarmoq yuzasi/auth yo'li ochilmadi; reja threat-modelidagi T-10-10 (namunaviy belgi `scene.sampleBadge`+`a11yDescription`da), T-10-13 (pilot raqamsiz, rezidentlik bugungi mexanizm tilida) mitigatsiyalari copy darajasida qo'llandi; T-10-14 uchun FAQ matnida xom HTML/`</script>` ketma-ketligi yo'q.

## Self-Check: PASSED

- [x] `frontend/src/app/globals.css` — `--text-hero`, `sweep`, `.landing-sweep-frame`, `.landing-step-fill`, `[data-step=` mavjud
- [x] `frontend/messages/uz-Latn.json` / `ru.json` / `uz-Cyrl.json` — `"landing"` nomi bor, 121 kalit teng
- [x] `frontend/messages/uz-Cyrl.overrides.json` — `"AI": "AI"` bor
- [x] `.planning/phases/10-landing-sbozor-uz/deferred-items.md` mavjud
- [x] Commitlar mavjud: `d829dac`, `bfea81f`, `1c650c3`
