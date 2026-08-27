---
phase: 09-ui-polish-motion-qatlami
plan: 03
subsystem: ui
tags: [data-theme, useSyncExternalStore, MutationObserver, fouc, i18n, node-test]
requires:
  - "09-01: globals.css token-scope ([data-theme=dark]/[data-theme=sun], *-text oilasi to'liq)"
  - "locale-switcher.tsx naqshi (role=group + aria-current)"
  - "stall-map.tsx useIsDesktop naqshi (useSyncExternalStore, DOM tashqi tizim)"
provides:
  - "lib/theme.ts: THEMES uch a'zoli yopiq reyestr, readTheme/setTheme, useTheme (MutationObserver obunasi)"
  - "layout.tsx: data-theme=light + suppressHydrationWarning + <head> bloklovchi skript (FOUC yo'q)"
  - "shell/theme-toggle.tsx: 3 tugmali role=group almashtirgich, min-h-11, LocaleSwitcher yonida"
  - "11 copy kaliti x 3 til: theme.* (4) + dashboard.revenueTrend*/occupancy* (7)"
  - "scripts/theme-tokens.test.mjs: G-motion-4(a-e) darvozasi, 14 test"
affects:
  - "09-05 (dashboard.* kalitlarining iste'molchisi shu rejada tug'iladi)"
  - "09-07 (faza darvozasi: to'liq gate + byudjet qayta o'lchovi)"
tech-stack:
  added: []
  patterns:
    - "Tema — DOM haqiqat manbai: hook documentElement.dataset.theme'ni o'qiydi, useState nusxa yaratmaydi"
    - "FOUC yechimi: <head> statik inline skript + suppressHydrationWarning (Next.js rasmiy naqshi)"
    - "Segment-chegarali skan: dark: detektori className=/cn( argumentlari ichidagi satr literallari bilan cheklanadi"
key-files:
  created:
    - frontend/src/lib/theme.ts
    - frontend/src/components/shell/theme-toggle.tsx
    - frontend/src/components/shell/theme-toggle.test.tsx
    - frontend/scripts/theme-tokens.test.mjs
  modified:
    - frontend/src/app/[locale]/layout.tsx
    - frontend/src/components/shell/app-shell.tsx
    - frontend/messages/uz-Latn.json
    - frontend/messages/ru.json
    - frontend/messages/uz-Cyrl.json
decisions:
  - "theme namespace fayl OXIRIDA (feature-xronologik konvensiya); dashboard 7 kaliti mavjud blokka qo'shildi"
  - "CSS reyestr manbai (d) uchun: light — BAZA (scope'siz @theme), scope reyestri {dark, sun} — 'light' scope yozish ortiqcha ikkinchi manba bo'lardi"
  - "Testda fireEvent (user-event EMAS) — loyiha konvensiyasi, uch mavjud test fayli izohda ochiq aytadi"
  - "ThemeToggle LocaleSwitcher'dan CHAPDA — ikkalasi ham header'ning shrink-0 blokida"
metrics:
  duration: "~40 min"
  completed: "2026-08-17"
  tasks: 3
  commits: 4
  tests_added: 26
---

# Phase 9 Plan 03: Tema qatlami — light/dark/sun, FOUC'siz skript, 11 kalit Summary

**Uch temaning to'liq almashtirish mexanizmi: DOM-manba `useTheme` (useSyncExternalStore + MutationObserver), `<head>` dagi reyestr-validatsiyali bloklovchi skript, `LocaleSwitcher` naqshidagi `ThemeToggle` va G-motion-4(a–e) darvozasi — «komponent kodi o'zgarmaydi» endi mexanik da'vo.**

## Bajarilgan vazifalar

| # | Vazifa | Commit |
|---|--------|--------|
| 1 | 11 kalit × 3 til (theme 4 + dashboard 7); uz-Cyrl generatsiyadan (0 defekt: `Ko'rinish`→`Кўриниш`, `Yorug'`→`Ёруғ`, `Quyosh ostida`→`Қуёш остида`); overrides/glossary tegilmadi; i18n:check 1373 kalit parity | `73f2cae` |
| 2 | TDD RED: theme-toggle.test.tsx — 12 test (reyestr, DOM o'qish/yozish, bloklangan localStorage, aria-current ko'chishi, tashqi atribut o'zgarishi, toast taqiqi) | `edb1913` |
| 2 | TDD GREEN: lib/theme.ts + layout.tsx (head skript + suppressHydrationWarning) + theme-toggle.tsx + app-shell mount | `a61f6f1` |
| 3 | theme-tokens.test.mjs — G-motion-4(a–e), 14 test, 2 sabotaj ikki natija bilan | `d92fd73` |

## Interface kontrakt holati (keyingi rejalar uchun)

- `lib/theme.ts`: `THEMES = ["light","dark","sun"] as const` · `Theme` tipi · `THEME_STORAGE_KEY = "sbozor-theme"` · `readTheme()` (reyestr validatsiyasi, standart `light`) · `setTheme(next)` (DOM + try/catch localStorage) · `useTheme()` (getServerSnapshot `"light"`)
- `layout.tsx` skripti STATIK: `t==="light"||t==="dark"||t==="sun"` — ixtiyoriy satr `data-theme`ga o'tolmaydi (T-09-01 mitigate)
- `dashboard.revenueTrendTitle/Period/Empty/EmptyHint`, `dashboard.occupancyTitle/Summary/Empty` — 09-05 uchun TAYYOR (occupancySummary ICU: `{occupied}`/`{empty}`)
- `ThemeToggle` — propssiz, header'da mount qilingan; tema o'zgarishi faqat token qiymatlarini almashtiradi

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Bloklovchi muammo] Worktree'da `frontend/node_modules` yo'q edi**
- **Topildi:** Task 2 RED o'lchovida (vitest yugurmadi)
- **Muammo:** Yangi worktree checkout — bog'liqliklar o'rnatilmagan
- **Tuzatish:** `npm ci --no-audit` (mavjud `package-lock.json` dan deterministik; YANGI paket qo'shilmadi — 530 paket, 2 min)
- **Fayl:** yo'q (faqat lokal muhit) · **Commit:** yo'q

**2. [Rule 1 - Test nuqsoni] `@testing-library/user-event` loyihada yo'q**
- **Topildi:** Task 2 GREEN o'lchovida (import hal bo'lmadi)
- **Muammo:** RED testi user-event import qilgan edi; loyiha konvensiyasi — `fireEvent` (uch mavjud test fayli buni izohda ochiq aytadi)
- **Tuzatish:** `fireEvent.click` ga o'tkazildi, paket QO'SHILMADI
- **Fayl:** `theme-toggle.test.tsx` · **Commit:** `a61f6f1`

### Rejalashtirilgan oqim eslatmalari (deviatsiya emas)

- Task 3 darvozasi yozilganda darhol yashil chiqdi — kutilgan: o'lchanadigan implementatsiya (globals.css scope'lari 09-01dan, theme.ts Task 2dan) allaqachon mavjud edi; mexanizm tirikligi ikki sabotaj bilan isbotlandi (pastda).
- T-09-02 (accept) bandi: loyihada CSP sarlavhasi YO'Q [O'LCHANDI 09-RESEARCH] — **CSP qo'shilgan kunda `<head>` inline skriptiga `nonce` kerak bo'ladi**. Bu shu yerda ochiq qayd sifatida qoladi.

### Verifikatsiya chetlanishlari (halollik bandi)

- **`npm run gate:fast` ning backend yarmi (docker pytest) yugurtirilmadi** — 09-01 protokoli: bu reja backend fayllariga TEGMAGAN (faqat `frontend/` + `.planning/`), backend testlari baza commitdagi bilan bit-aynan; worktree'dan ikkinchi compose loyihasi ko'tarish disk xavfi. Frontend yarmi TO'LIQ: skriptlar **320/320**, vitest **1122/1122**, `tsc --noEmit`, `next build` (81/81 SSG, exit 0). To'liq `gate` — faza darvozasida (09-07, W0-13 protokoli).
- `npm run build` Task 2 commit'idan keyin o'lchandi; Task 3 faqat `scripts/` ga test qo'shdi (mahsulot kodi o'zgarmadi) — build qayta yugurtirilmadi, holat bit-aynan.

## Sabotaj jurnali (2/2 — har birida IKKI natija)

| # | Sabotaj | Nishon | Qo'shnilar |
|---|---------|--------|------------|
| S-1 | `[data-theme="dark"]` dan `--color-danger-text` olib tashlandi (CSS yaroqli qoldi) | **G-motion-4(c) QIZARDI** (*-text oilasi to'liq emas) VA **contrast G-motion-5(b) QIZARDI** (danger-text bazaga tushdi) — IKKI QATLAM | collect-surface + bulk-action-surface + role-gate **25/25 yashil** |
| S-2 | `@theme` → `@theme inline` (kompilyatsiya qilinadigan holat) | **G-motion-4(b) QIZARDI** — yagona qizil | contrast + collect-surface + bulk-action-surface **29/29 yashil** |

Ikkalasi ham qaytarildi; yakuniy holat: `git status` toza, theme-tokens 14/14, butun skript to'plami 320/320.

## Verifikatsiya natijalari

| Buyruq | Natija |
|--------|--------|
| `npm run i18n:gen` + `i18n:check` | drift yo'q; **1373 kalit × 3 til** parity to'liq |
| `node --test scripts/glossary.test.mjs` | 9/9 |
| `node --test scripts/theme-tokens.test.mjs` | **14/14** (a: 166 fayl skan, 0 hit · b/c/d/e yashil · sun'iy-ijobiy nazorat) |
| `node --test scripts/*.test.mjs` | **320/320** (20 darvoza — mavjud 19 tasi REGRESSIYASIZ) |
| `npx vitest run` | **1122/1122** (95 fayl; +12 yangi) |
| `npx tsc --noEmit` | yashil |
| `npm run build` | exit 0 — **81/81 SSG** (3 locale × 27); `login.html` da `data-theme="light"` + head skripti tasdiqlandi |

## Known Stubs

Yo'q — tema qatlami to'liq ulangan (tugma → DOM → token-scope → saqlash → birinchi bo'yash). `dashboard.*` 7 kaliti hozircha iste'molchisiz, LEKIN bu stub emas: `messages/*.json` fayl egaligi shu rejada va kalitlar 09-05 ning interface kontrakti (reja ⛔ bandi shuni ochiq belgilagan; `check-messages.mjs` ishlatilmagan kalitni xato sanamaydi).

## Threat Flags

Yo'q — yangi endpoint, sir, sessiya yuzasi yo'q. `dangerouslySetInnerHTML` (statik satr) va `localStorage["sbozor-theme"]` plan `<threat_model>` da allaqachon T-09-02/T-09-13 (accept) sifatida ro'yxatda.

## Self-Check: PASSED

- FOUND: frontend/src/lib/theme.ts
- FOUND: frontend/src/components/shell/theme-toggle.tsx
- FOUND: frontend/src/components/shell/theme-toggle.test.tsx
- FOUND: frontend/scripts/theme-tokens.test.mjs
- FOUND: commit 73f2cae · edb1913 · a61f6f1 · d92fd73
