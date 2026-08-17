---
phase: 09-ui-polish-motion-qatlami
plan: 01
subsystem: ui
tags: [tailwind4, oklch, wcag, motion-tokens, data-theme, node-test]
requires:
  - "globals.css @theme tuzilishi (1/7/8-faza tokenlari)"
  - "collect-surface.test.mjs darvoza naqshi (reyestr + quyi chegara + hosila skan)"
provides:
  - "Motion token reyestri: --motion-fast/base/slow, --ease-out (qayta ta'rif), --ease-spring, --text-display(+line-height) + 2 ta --default-transition-* bog'lash"
  - "@keyframes reyestri (8 nom): draw ringpulse landin enter shimmer breath attention shake + 8 .motion-* sinfi"
  - "Ikki qatlamsiz tema scope: [data-theme=dark] va [data-theme=sun] — *-text oilasi ikkalasida to'liq"
  - "scripts/contrast.test.mjs — G-motion-5(a,b,c,d) + --print (izoh generatori)"
  - "09-VALIDATION.md to'ldirilgan · 09-HUMAN-UAT.md (5 band) · deferred-items.md (konfetti)"
affects:
  - "09-02 (motion-tokens darvozasi shu tokenlarni o'qiydi)"
  - "09-03 (theme-tokens darvozasi shu scope'larni o'qiydi)"
  - "09-04/09-05 (.motion-* sinflari va Display-XL iste'molchilari)"
tech-stack:
  added: []
  patterns:
    - "Kanonik kontrast da'vosi: `[tema] fg/bg@AA: N.NN:1` — izoh endi mashina o'qiydigan shartnoma"
    - "Gamut siyosati: gamma fazoda [0,1] kesish; tint kompozitsiyasi gamma fazoda, ostki qatlam — tema surface'i"
key-files:
  created:
    - frontend/scripts/contrast.test.mjs
    - .planning/phases/09-ui-polish-motion-qatlami/09-HUMAN-UAT.md
    - .planning/phases/09-ui-polish-motion-qatlami/deferred-items.md
  modified:
    - frontend/src/app/globals.css
    - frontend/src/app/[locale]/(app)/review/page.tsx
    - frontend/src/components/blind-audit/blind-session.tsx
    - .planning/phases/09-ui-polish-motion-qatlami/09-UI-SPEC.md
    - .planning/phases/09-ui-polish-motion-qatlami/09-VALIDATION.md
decisions:
  - "Gamut siyosati testning O'ZIDA qulflangan: siyosat o'zgarsa SELF_CHECK (1.28/4.72) qizaradi"
  - "G-motion-5(d) skani TOKEN-ANIQ: bg-accent/10 tinti qonuniy va ushlanmaydi"
  - "Dark scope'da uch token SPEC'dan chetlandi (o'lchov majburladi, sabab izohda): accent-fg 0.205, success-text 0.64, warning-text 0.72"
  - "attention davomiyligi var(--motion-slow) — 400ms reyestr a'zosi, sehrli son yozilmadi"
metrics:
  duration: "45 min"
  completed: "2026-08-17"
  tasks: 3
  commits: 5
  tests_added: 10
---

# Phase 9 Plan 01: Manba qatlami — SPEC rostlash, kontrast darvozasi, globals.css Summary

**G-motion-5 kontrast darvozasi (oklch parse + 45 o'lchov × ±0.01 izoh qulfi) va `globals.css` ning to'liq motion/tema qatlami; jonli 1.28:1 nuqson TDD bilan yopildi va reyestr dark temada uchta yangi AA buzilishini fosh qilib tuzattirdi.**

## Bajarilgan vazifalar

| # | Vazifa | Commit |
|---|--------|--------|
| 1 | SPEC 4 nomuvofiqligi (⚠ 09-01 tuzatishi izohi bilan) · 09-VALIDATION to'ldirildi (5 inson bandi, 7 almashtirish, `>-`/`\|` skalyar 0) · 09-HUMAN-UAT (5 band, ega+tetik+SON) · deferred-items (konfetti) | `8a4cf0b` |
| 2 | TDD RED: kontrast kalkulyatori + G-motion-5(a,d) + `--print` — (d) ikkala jonli nuqsonni topdi | `16ffd86` |
| 2 | TDD GREEN: `review/page.tsx:217` va `blind-session.tsx:212` — `text-accent-text` → `text-accent-fg` (1.28 → 4.72) | `61e4f43` |
| 3 | `globals.css` to'liq qatlam (6+2 token, iliq baza, reduced-motion, 8 keyframes, 2 qatlamsiz scope, generatsiya izohlar) + G-motion-5(b,c) | `cab9e73` |

## Interface kontrakt holati (keyingi rejalar uchun)

- `@theme`: `--motion-fast: 150ms` · `--motion-base: 250ms` · `--motion-slow: 400ms` · `--ease-out: cubic-bezier(0.22,1,0.36,1)` (Tailwind standarti QAYTA ta'riflangan) · `--ease-spring` · `--text-display: 2.5rem` + `--line-height: 1.1` · `--default-transition-timing-function: var(--ease-out)` · `--default-transition-duration: var(--motion-fast)`
- `@keyframes` (faqat globals.css): `draw` · `ringpulse` · `landin` · `enter` · `shimmer` · `breath` · `attention` · `shake`; sinflar `motion-` prefiksida (`animate-` EMAS)
- Scope'lar `@layer` TASHQARISIDA — kompilyatsiya kaskadi bo'yicha kafolatli g'olib

## O'lchangan yangi topilmalar (SPEC'da yo'q edi)

Reyestr (b) uch temada yugurtirilganda **dark temada uchta yangi AA buzilishi** chiqdi — M-18 sinfining davomi, mexanik o'lchovsiz ko'rinmasdi:

| Juftlik | SPEC qiymatida | Sozlangan token | Endi |
|---------|----------------|------------------|------|
| `[dark] accent-fg/accent` | **3.38** ❌ (oq matn yorishgan 0.64 aksentda) | `--color-accent-fg: oklch(0.205 0 0)` (dark override QO'SHILDI) | **5.30** ✅ |
| `[dark] success-text/success@12` | **4.33** ❌ (tint kompozit surface-muted'dan yorug'roq) | L 0.62 → **0.64** | **4.68** ✅ |
| `[dark] warning-text/warning@20` | **3.41** ❌ (warning/20 — eng yorug' kompozit) | L 0.64 → **0.72** | **4.63** ✅ |

Reja (G) qoidasi qo'llandi: chegara PASAYTIRILMADI, juftlik reyestrdan CHIQARILMADI — token sozlandi va sabab `globals.css` izohida.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Yetishmayotgan majburiy funksionallik] Dark scope'ga `--color-accent-fg` override qo'shildi**
- **Topildi:** Task 3, (b) reyestrini birinchi yugurtirishda
- **Muammo:** Reja (E) dark scope ro'yxatida `accent-fg` yo'q edi; oq matn dark aksent (0.64) ustida 3.38 — birlamchi tugma dark rejimda AA'dan yiqiladi (T-09-07 mitigate)
- **Tuzatish:** `oklch(0.205 0 0)` override + izohda sabab (dark rejimlarda odatiy naqsh: yorishgan aksent + quyuq matn)
- **Fayl:** `frontend/src/app/globals.css` · **Commit:** `cab9e73`

**2. [Rule 1 - Reja qiymatidagi nuqson] Dark `success-text`/`warning-text` tint fonida yiqilardi**
- **Topildi:** Task 3, (b) reyestri
- **Muammo:** Reja (E) SPEC §5.3 qiymatlarini sanagan (0.62 / 0.64) — ular tekis surface-muted uchun yechilgan, tint kompozitlar esa YORUG'ROQ; 4.33 va 3.41
- **Tuzatish:** minimal ko'tarish (0.64 / 0.72), surface-muted juftliklari ham yashil qoladi (4.90 / 6.23)
- **Fayl:** `frontend/src/app/globals.css` · **Commit:** `cab9e73`

**3. [Rule 1 - Eskirgan da'vo] `accent-text` tint izohi 5.31 → 5.28**
- **Topildi:** Task 3, izohlarni generatsiya qilishda
- **Muammo:** Qo'lda yozilgan eski `5.31:1` da'vosi e'lon qilingan siyosat (gamma kompozitsiya, surface ostki qatlam) ostida 5.28 chiqadi — Tuzoq 2 aynan bashorat qilgan sinf
- **Tuzatish:** izoh `--print` chiqishidan qayta generatsiya qilindi
- **Fayl:** `frontend/src/app/globals.css` · **Commit:** `cab9e73`

### Rejalashtirilgan oqim eslatmalari (deviatsiya emas)

- SELF_CHECK ning ikki soni Task 3 da iliq bazaga qayta generatsiya qilindi: `4.81→4.84`, `3.32→3.34` (M-17 kutgan qiymatlar; Task 2 vaqtida sovuq baza amalda edi).
- `attention` davomiyligi `var(--motion-slow)` deb yozildi — reja «400ms» degan, 400ms esa reyestr a'zosining o'zi; sehrli son ochilmadi.

### Verifikatsiya chetlanishlari (halollik bandi)

- **`npm run gate:fast` ning backend yarmi (docker pytest) worktree'da yugurtirilmadi.** Sabab: bu reja backend fayllariga TEGMAGAN (faqat `.planning` + `frontend`), backend testlari baza commitdagi bilan bit-aynan; worktree'dan ikkinchi docker-compose loyihasini ko'tarish esa image qurish + disk (C: 84%) xavfi. Frontend yarmi TO'LIQ o'lchandi: skriptlar **306/306**, vitest **1110/1110**, `tsc --noEmit`, `next build` (SSG 3 locale, exit 0). To'liq `gate` — faza darvozasida (09-07, W0-13 protokoli).
- **Worktree sentinel fayli yozilmadi** (`.git/worktrees/...` ga yozish izolyatsiya tomonidan bloklangan) — o'rnini har commitdan oldin `git rev-parse --show-toplevel` + filial asserti bosdi (4 marta bajarildi, hammasi mos).
- Vitest yakka o'lchovi 216 s berdi — bu BYUDJET o'lchovi EMAS (sovuq kesh: import 148 s; tinch bo'lmagan xost). Bu reja vitest'ga 0 ta test qo'shdi; skript to'plamiga qo'shilgani ~0.3 s. Byudjet qayta o'lchovi — 09-07 bandi (05-15 W0-13).

## Sabotaj jurnali (3/3 — har birida IKKI natija)

| # | Sabotaj | Nishon | Qo'shnilar |
|---|---------|--------|------------|
| S-T2 | `review/page.tsx` `text-accent-fg` → `text-accent-text` (fayl yig'iladigan holda) | **G-motion-5(d) QIZARDI** — aynan o'sha fayl+satr literalini ko'rsatdi | **301/302 yashil** — yagona qizil nishonning o'zi |
| S-T3-1 | Dark scope'dan `--color-danger-text` olib tashlandi (CSS yaroqli qoldi) | **G-motion-5(b) QIZARDI** — `[dark] danger-text/danger@12: 2.40 < 4.5` (bazaga tushish o'lchandi) | **305/306 yashil** |
| S-T3-2 | Izoh soni `4.84` → `5.20` | **G-motion-5(c) QIZARDI** — «da'vo 5.2, hisob 4.84 (farq >0.01)» | **305/306 yashil** |

Uchalasida ham modul import/parse qilinadigan holda qoldi (08-20 S-5 darsi); uchalasi ham qaytarildi va yakuniy holat 10/10 yashil.

## Verifikatsiya natijalari

| Buyruq | Natija |
|--------|--------|
| `node --test scripts/contrast.test.mjs` | **10/10** (a: 6 qiymat ±0.01 · b: 45 o'lchov 3 temada · c: 30+ kanonik da'vo · d: 0 kombinatsiya, 197 fayl skan) |
| `node scripts/contrast.test.mjs --print` | exit 0 — 48 da'vo, uch tema |
| `npm --prefix frontend run test:unit` | **306/306** (19 skript-darvoza — mavjud 18 tasi REGRESSIYASIZ) |
| `npx vitest run` | **1110/1110** (94 fayl) |
| `npx tsc --noEmit` | yashil |
| `npm --prefix frontend run build` | exit 0 — SSG 3 locale |
| `node scripts/check-validation-signoff.mjs` | exit 0 — `nyquist_compliant: false` hisob-kitob bilan MOS (7 pending qator — kutilgan) |

## Known Stubs

Yo'q — bu reja UI render yuzasi qo'shmadi. `.motion-*` sinflari hozircha iste'molchisiz, LEKIN bu stub emas: ular 09-02/09-04/09-05 rejalarining interface kontrakti (reja `<interface_contract>` shunday belgilagan).

## Self-Check: PASSED

- FOUND: frontend/scripts/contrast.test.mjs
- FOUND: .planning/phases/09-ui-polish-motion-qatlami/09-HUMAN-UAT.md
- FOUND: .planning/phases/09-ui-polish-motion-qatlami/deferred-items.md
- FOUND: commit 8a4cf0b · 16ffd86 · 61e4f43 · cab9e73
