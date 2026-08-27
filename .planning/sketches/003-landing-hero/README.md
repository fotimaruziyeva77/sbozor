---
sketch: 003
name: landing-hero
question: "Hero qanday sotadi: matn-birinchi, 12s «jonli bozor» sikli yoki 3-qadam scroll-hikoya?"
winner: "B"
tags: [landing, hero, marketing]
---

# Sketch 003: Landing hero

## Dizayn savoli
LANDING-BRIEF §7: Realsoft statik skrinshot ko'rsatadi — biz voqeani sodir
bo'layotganini ko'rsatamiz. Savol: hero'ning og'irligi qayerda — matnda,
jonli sahnada yoki qadamlar hikoyasida?

## Ochish
`start .planning\sketches\003-landing-hero\index.html` (Windows)

## Variantlar
- **A: Matn-birinchi** — og'riq-savol + statik xarita kartasi. Eng tez LCP.
- **B: Jonli bozor ★ (tavsiya)** — 12s rejissyorlangan sikl (brief §7.1):
  xarita chiziladi → kamera nuri → yashil rastalar → bittasi amber + «Band,
  lekin to'lovsiz» → to'lov → tushum sanaydi → hisobot kartasi → sikl qaytadi.
  Video emas — CSS/JS, reduced-motion'da statik final-kadr.
- **C: 3-qadam scroll** — hero ixcham, og'irlik «qanday ishlaydi» chizig'ida.

## Nimaga qarash kerak
1. B siklini 2–3 marta to'liq ko'ring: har fazaning yorlig'i (stage-head)
   hikoyani so'zsiz aytadimi?
2. Amber lahza (5–8s) — mahsulotning butun ma'nosi shu bir soniyada. Sezildimi?
3. A bilan solishtiring: B ning qo'shimcha «sehri» kutishga arziydimi?
4. Copy: sarlavha, ⭐ dalil, ishonch qatori — brief matni joyidami?

## Tavsiya sababi (avtonom rejim)
**B.** Bu brief §7 ning bosh g'oyasi va raqobat strategiyasining o'zagi:
«ularniki kompaniya prezentatsiyasi, bizniki mahsulot o'zi gapiryapti».
A — reduced-motion/mobil fallback sifatida B ichida yashaydi (statik
final-kadr allaqachon shu maketda bor). C ning 3-qadam bloki hero EMAS,
sahifaning 3-seksiyasi sifatida kiradi (brief §2.3) — chiziq-to'lish naqshi
shu maketdan olinadi. Realda sikl IntersectionObserver bilan faqat ko'rinishda
ishlaydi va LCP birinchi ekran matnidan buziladi emas (sahna `contain` bilan).
