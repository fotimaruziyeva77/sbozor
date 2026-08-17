---
phase: 10-landing-sbozor-uz
plan: 05
subsystem: frontend-landing-hero
tags: [landing, hero, lcp, scene, intersection-observer, reduced-motion, vitest]
requires:
  - "10-02 (--text-hero tokeni, sweep/.landing-sweep-frame, Button hero, landing.* 121 kalit)"
  - "10-03 ((marketing) qobiq, toraytirilgan provayder {common,landing})"
provides:
  - "marketing/hero.tsx — Server Component, LCP matn ustuni, text-hero ning yagona uyi"
  - "marketing/hero-scene.tsx — 12s (haqiqiy 13 500 ms) jonli bozor sikli: taymer reyestri, IO + visibilitychange, server final-kadr"
  - "marketing/hero-scene.test.tsx — G-land-2(a…e), IO mock + matchMedia stub naqshi (IO kodbazada birinchi)"
affects:
  - "10-06/10-07 (sahifa kompozitsiyasi Hero'ni Section ichiga oladi; #demo/#ishonch ankerlar iste'molchilari)"
  - "10-07 G-land-1(a) reyestri (hero-scene.tsx — klient orollaridan biri), G-land-5(a) (text-hero quli)"
tech-stack:
  added: []
  patterns:
    - "Server final-kadr + klient sikl davomi (rewind'siz gidratatsiya, §5.2)"
    - "Taymer massiv-reyestri (review-session'ning bitta ref'idan kengaytma)"
    - "IntersectionObserver + visibilitychange — ikki mustaqil to'xtatgich, hosila running (kodbazada birinchi IO)"
    - "transition-delay stagger (qaytariladigan holat uchun @keyframes o'rniga)"
    - "Mobil katak kamaytirish CSS-shox bilan: max-[840px]:grid-cols-5 + nth-[3n]:hidden"
key-files:
  created:
    - frontend/src/components/marketing/hero.tsx
    - frontend/src/components/marketing/hero-scene.tsx
    - frontend/src/components/marketing/hero-scene.test.tsx
  modified: []
decisions:
  - "Sikl jadvali: mount → faza-5 hold 3500 ms (§5.5 oynasi) → reset+faza1; to'liq davr AYNAN 13 500 ms (2600+2700+3000+1700+3500)"
  - "G-land-2(b) ikki bosqichli advance bilan o'lchaydi (3500 + 13500): bitta advance(13500) HAR QANDAY jadvalda faza-5 startiga tushardi, reset nuqtasiga emas — 13 500 sikl DAVRI sifatida o'lchandi, literal 13500 testda"
  - "Tushum formati qo'lda (oddiy bo'shliq guruhlash), Intl formatter emas: SSG kadri uch locale'da ayn va test DOM matni deterministik"
  - "Server kadrida №16 amber (unpaidResolved=false) — sketch reduced-branch ayna; jonli sikl faza-5 i esa №16 yashil (hikoya yakuni)"
  - "Mobil 20 katak nth-child(3n) yashirish bilan: amberdan oldin aynan 5 katak yashirinib ko'rinadigan o'rni 11 (§5.8 jadvaliga aynan mos)"
  - "Izohlarda taqiq substringlar yozilmaydi (klient direktivasi, hero-utilita nomi) — satr-skan darvozalari izohga qoqilmasin (10-03 B-2 presedenti)"
metrics:
  duration: "~55 min"
  completed: "2026-08-17T13:29:00Z"
  tasks: 3
  commits: 3
---

# Phase 10 Plan 05: Hero — server matn + 12s jonli bozor sikli Summary

**Bir qator:** `hero.tsx` (Server Component, `text-hero` yagona uyi, `h1` ATAYIN `.motion-enter`siz — LCP ~310 ms tuzog'i izohda) + `hero-scene.tsx` (server final-kadr → 5→1→…→5 sikl, taymer massiv-reyestri, IO+visibilitychange mustaqil to'xtatgichlar) + G-land-2(a…e) beshala band ikki sabotaj isboti bilan.

## Bajarilgan vazifalar

| # | Vazifa | Commit | Kalit fayllar |
|---|--------|--------|---------------|
| 1 | hero.tsx — LCP matn ustuni | `4fe09d8` | hero.tsx |
| 2 | hero-scene.tsx — 12s sikl | `db47892` | hero-scene.tsx |
| 3 | hero-scene.test.tsx — G-land-2 + 2 sabotaj | `257c26b` | hero-scene.test.tsx |

## Nima qurildi

- **`hero.tsx` (server):** brand → `h1` (`text-hero`, ⛔ `.motion-enter`siz, sabab kod izohida LITERAL) → lid (`text-lg max-w-[66ch] leading-relaxed`) → ikki CTA (birlamchi `#demo` ankeriga `size="hero"`; ikkilamchi `/login` ga `size="lg"` — `@/i18n/navigation` `Link`) → ⭐ dalil → ishonch qatori (4 band, ✓ dekorativ, `trust.residency` → `#ishonch` anker). Kirish ketma-ketligi `--i` 0..4 brand'dan boshlanadi. Grid `min-[841px]:grid-cols-[1.05fr_1fr]`, ≤840px da matn birinchi.
- **`hero-scene.tsx` (klient, 486 qator):** boshlang'ich holat = SERVER FINAL-KADRI (30 katak yoniq, №16 amber, hisobot ochiq, `2 306 000`); sikl 5 → (3,5 s) → 1(2,6) → 2(2,7) → 3(3,0) → 4(1,7) → 5(3,5) → … = **13 500 ms davr**. Reduced-motion — effektning BIRINCHI qatorida erta `return` (0 taymer). Taymer massiv-reyestri; `IntersectionObserver` (kodbazada birinchi, vanilla) + `visibilitychange` — `running = visible && !pageHidden`; to'xtaganda taymerlar tozalanadi, DOM saqlanadi; davom — joriy fazadan (faza-5'da DOM'ga TEGILMAYDI — rewind imkonsiz). Stagger `transitionDelay` inline (70 ms katak / 280 ms ustun), sweep `.landing-sweep` (10-02 tokeni), №16 diqqat-halqasi `.motion-attention` bir marta, tushum `useCountUp(target, duration)` (qayta yozilmadi). `sampleBadge` shartsiz; `role="img"` + `a11yDescription`; faza yorlig'i `aria-live`siz. Mobil: `max-[840px]:grid-cols-5` + katakda `max-[840px]:nth-[3n]:hidden` — JS bir xil DOM chizadi.
- **`hero-scene.test.tsx` (333 qator):** beshala band alohida test; `matchMedia`/`IntersectionObserver` stublari HAR testda (setup'ga emas); IO mock `observe`/`disconnect`ni sanaydi, callback qo'lda ateshlanadi; yorliqlar reyestri `uz-Latn.json` katalogidan HOSILA; final-kadr tasdiqlari DOM matni/atributlari ustida (`data-state`, `data-on`, `2 306 000`).

## Reja bo'yicha o'lchovlar (verification)

| O'lchov | Natija |
|---------|--------|
| `vitest run src/components/marketing/` | **2 fayl / 10 test yashil** |
| `npm test` (skript darvozalari + vitest) | **101 fayl / 1180 test yashil** (10-04/10-06 parallel bazasiz holatda) |
| `typecheck` / `lint` / `build` | exit 0 / exit 0 / exit 0 |
| `text-hero` | hero.tsx'da **aynan 1** uchrashuv; boshqa faylda 0 |
| Klient direktivasi hero.tsx'da | **0** (izohda ham substring yo'q) |
| `setTimeout` `components/marketing/**` da | **faqat hero-scene.tsx** (mahsulot fayllari) |
| `setInterval` / inline `animation:` / `duration-<son>` / `transition-[` | **0 / 0 / 0 / 0** |
| Inline style geometriyasi | **0** — faqat `transitionDelay` (sahna) va `--i` (hero) |
| Taqiq tipografiya (text-base/3xl/`text-[`/font-medium/text-display) marketing yangi fayllarda | **0** |
| hero-scene.tsx / test qatorlari | 486 ≥ 120 / 333 ≥ 150 |

## Sabotaj o'lchovlari (§16.3 — har biri alohida qadam, modul import qilinadigan holda)

**1. Reduced-motion erta `return` olib tashlandi (hero-scene.tsx, effekt birinchi qatori):**
- **O'lchandi:** `vitest run src/components/marketing/hero-scene.test.tsx` → **exit 1**, xato matnida AYNAN band nomi: `G-land-2(a): reduced-motion — sikl UMUMAN boshlanmaydi > (a) reduce=true…` — **1 failed / 4 passed**. Modul kompilyatsiya qilindi va import qilindi (qolgan 4 test yugurdi — o'lchangan narsa mezon, yig'ilish emas).
- Muhim detal: (a) testi ichida IO trigger + advance ATAYIN bor — trigger'siz sabotaj bilan ham taymer 0 bo'lib qolar edi (sikl faqat ko'rinishda boshlanadi) va sabotaj jimgina o'tardi. Test shu yo'l bilan sabotajni haqiqatan ushlaydigan qilib yozildi.
- Qaytarildi: `git checkout -- hero-scene.tsx`, keyingi yugurish 5/5 yashil.

**2. `useEffect` tozalash funksiyasi olib tashlandi:**
- **O'lchandi:** → **exit 1**, xato matnida AYNAN: `G-land-2(d): unmount'da taymerlar to'liq tozalanadi > (d) unmount'dan keyin clearTimeout soni…` — **1 failed / 4 passed**, modul import qilinadigan holda.
- Qaytarildi: xuddi shu tarzda, yakuniy yugurish 5/5 yashil.

## Deviations from Plan

### Zaruriy talqin (reja behavior matni doirasida)

**1. G-land-2(b) — «13 500 ms da» ikki bosqichli advance bilan o'lchandi**
- **Found during:** Task 2/3 sikl jadvalini loyihalash
- **Issue:** Mount'dan keyingi bitta `advanceTimersByTimeAsync(13500)` HAR QANDAY §5.5-mos jadvalda reset nuqtasiga tusha olmaydi: faza-5 hold (3500) + faza 1–4 yig'indisi (10 000) = aynan 13 500 — bu nuqta faza-5 STARTI (kataklar yoniq), reset emas. «Kataklar on emas» sharti bitta advance bilan matematik qanoatlantirib bo'lmasdi.
- **Fix:** Test avval `advance(3500)` bilan siklga kiradi (reset tasdig'i), so'ng `advance(13500)` — TO'LIQ DAVR — sikl AYNAN o'sha reset nuqtasiga qaytganini o'lchaydi. 13 500 literal testda (reja talabi), «12 000 emas» sharti bajarilgan, «sikl 1-fazaga qaytgan (kataklar on emas)» ayni o'lchangan.
- **Files modified:** hero-scene.test.tsx — **Commit:** `257c26b`

**2. [Rule 2 - Satr-skan xavfsizligi] Izohlardan taqiq substringlar olib tashlandi**
- **Found during:** Task 1 o'z-tekshiruvi
- **Issue:** hero.tsx modul izohida klient direktivasi iborasi, hero-utilita nomi va displey-utilita nomi literal turgan edi — 10-03 presedenti (B-2 quli «izohda ham» skanerlaydi) bo'yicha G-land-1(b)/G-land-5(a) satr skanlari izohga qoqilishi mumkin edi.
- **Fix:** Izohlar ma'noni saqlab qayta yozildi (grep: direktiva 0, hero-utilita 1 — faqat `h1` sinfida).
- **Files modified:** hero.tsx — **Commit:** `4fe09d8`

### Reja aytgan transient holat

Task 1 commit nuqtasida `typecheck` AYNAN bitta xato berdi — `hero-scene` moduli hali yo'q (forward-reference, reja Info 3 aytgan holat). Task 2 commit'idan keyin typecheck to'liq exit 0. Boshqa transient xato bo'lmadi.

## TDD Gate Compliance

Task 3 `tdd="true"`, lekin reja tartibi implementatsiyani (Task 2) testdan OLDIN qo'ygan — klassik RED (implementatsiya yo'qligida qizil) shu tartibda imkonsiz edi. RED gate'ning maqsadi — «test haqiqatan qizara oladi»mi — reja MAJBURIY qilgan ikki sabotaj bilan bajarildi va IKKALASI mo'ljallangan bandni qizartirdi (yuqoridagi jadval: exit 1 + band nomi xatoda). Ketma-ketlik: `feat db47892` (implementatsiya) → `test 257c26b` (o'lchov + sabotaj isboti). Gap'ning yashil-holati commit qilinishidan oldin 5/5 tasdiqlangan.

## O'lchanmagan qoladi (HALOL — reja §verification 5-band)

- **60fps arzon Android qurilmada** va **`container-type: inline-size` + `100cqw`** ning maqsad qurilmalardagi haqiqiy xulqi — jsdom layout ham, kompozitsiya ham qilmaydi; test qatlamida «kadr tushdimi?» savoliga sirt YO'Q. Bu **HUMAN-UAT #3** (10-08) bandi, KADR/SONIYA raqami bilan yopiladi. Zaxira yo'l saqlangan: muammo o'lchansa sahna mount'da `--sweep-distance`ni `offsetWidth`dan BIR marta yozadi, `@keyframes` o'zgarmaydi.
- **LCP soni** — HUMAN-UAT #1 (G-land-1 faqat mexanik proksi).
- (a) testidagi `setTimeout` josusi jsdom + React 19 muhitida render shovqinisiz **0** chiqdi (o'lchandi) — bu jsdom'ga xos xulq, brauzer scheduler'iga da'vo emas.

## Known Stubs

Yo'q. Hisobot raqamlari (215 / 214 / 1 → 0) va tushum (2 306 000 / 2 298 000) — sketch 003-B dan ko'chirilgan NAMUNAVIY kontent, `sampleBadge` shartsiz belgisi ostida (K-7); bo'sh/placeholder qiymat emas, kelajak rejaga qoldirilgan sim ham yo'q.

## Threat Flags

Yangi yuza yo'q. Reja threat-registri qo'llandi: **T-10-12** (taymer reyestri + IO/visibility to'xtatgichlari — G-land-2(d)/(e) bilan o'lchandi), **T-10-10** (`sampleBadge` shartsiz, «Namuna bozori · namoyish», «jonli» so'zi manba kodda ham yo'q), **T-10-20** («namunaviy» o'zagi `a11yDescription` matni ichida — skrinriderga ham yetadi), **T-10-21** (holat o'tishlari faqat transform/opacity/rang; sweep `translateX`, inline geometriya 0).

## Self-Check: PASSED

- [x] `frontend/src/components/marketing/hero.tsx` — mavjud, `text-hero` bor (1 marta)
- [x] `frontend/src/components/marketing/hero-scene.tsx` — mavjud, `prefersReducedMotion()` effekt birinchi qatorida, `useCountUp` chaqirilgan, `disconnect()` tozalashda
- [x] `frontend/src/components/marketing/hero-scene.test.tsx` — mavjud, 5 band + IO mock
- [x] Commitlar mavjud: `4fe09d8`, `db47892`, `257c26b`
- [x] STATE.md / ROADMAP.md TEGILMADI
