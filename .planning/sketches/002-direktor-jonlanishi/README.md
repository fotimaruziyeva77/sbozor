---
sketch: 002
name: direktor-jonlanishi
question: "Dashboard qanday jonlanadi (skeleton → count-up → sparkline) va fon iliqmi, neytralmi?"
winner: "B"
tags: [dashboard, motion, rang-2.0, dark]
---

# Sketch 002: Direktor jonlanishi

## Dizayn savoli
8-faza direktor paneli ma'lumotini qurdi; masterplan §4.3 va §6.3 uni qanday
JONLANTIRISHNI aytadi. Savol: qancha harakat "professional jilo", qayerdan
boshlab "sirk"? Va rang 2.0 iliq foni haqiqatan yaxshiroqmi?

## Ochish
`start .planning\sketches\002-direktor-jonlanishi\index.html` (Windows)

## Variantlar
- **A: Sokin** — skeleton → crossfade, stagger 30ms, count-up YO'Q.
- **B: Jonli + iliq ★ (tavsiya)** — count-up 600ms + tick, sparkline chizilib
  chiqadi, bandlik halqasi aylanib to'ladi, nomuvofiqlik case amber sirg'alib
  kiradi. «+ Yangi to'lov» → raqam yumshoq yangilanadi + yashil nafas.
- **C: Tungi rejim** — B ning o'zi dark tokenlar bilan (06:00 smena).

## Nimaga qarash kerak
1. «↻ Qayta yuklash» bilan skeleton→data siklini his qiling — spinner
   sog'inasizmi? (yo'q bo'lishi kerak)
2. B ning count-up'i ishonch beradimi yoki chalg'itadimi?
3. «+ Yangi to'lov» — real vaqt yangilanishining "yashil nafasi" yetarlimi?
4. Toolbar'dan iliq temaga o'ting: farq sezilarli, lekin bosiqmi?
5. C: dark'da kontrast va soya ierarxiyasi saqlanganmi?

## Tavsiya sababi (avtonom rejim)
**B.** Masterplan §4.3 count-up'ni va §6.3 sparkline/donut'ni nomma-nom talab
qiladi; A ularni bermaydi. Iliq fon (§1.1) ko'z charchashini kamaytiradi va
"qog'oz" hissi beradi — raqib tahlilida ham iliq fon kuchli tomon deb qayd
etilgan. C g'olib emas, lekin dark tokenlari UI-SPEC'ga alohida rejim sifatida
kiradi (§1.3) — komponent kodi o'zgarmasligi maketda isbotlandi (token-scope).
