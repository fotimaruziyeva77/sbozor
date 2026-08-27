# Sketch Wrap-Up Summary

**Sana:** 2026-08-16
**Qayta ishlangan:** 3 sketch (3 kiritildi, 0 chiqarildi)
**Dizayn sohalari:** motion+kassir · dashboard · landing
**Skill:** `./.claude/skills/sketch-findings-bozor/`

## Kiritilgan sketchlar

| # | Nomi | G'olib | Soha |
|---|------|--------|------|
| 001 | kassir-vau-oqimi | B (Apple Pay to'liq) | Motion + kassir |
| 002 | direktor-jonlanishi | B (jonli + iliq fon) | Dashboard |
| 003 | landing-hero | B (12s jonli bozor sikli) | Landing |

G'oliblar 2026-08-16 foydalanuvchi tomonidan tasdiqlangan
(«tavsiyalar bilan roziman»).

## Dizayn yo'nalishi (jamlangan)

Apple-minimal jilo mavjud tizim ustiga: iliq fon `#FAFAF9` (rang 2.0 qabul),
motion 150/250/400ms `ease-out`, faqat transform/opacity, skeleton (spinner
yo'q), `prefers-reduced-motion` global, kassir interaktiv ≤150ms, pul
Display-XL + `tabular-nums`.

## Asosiy qarorlar

- To'lov muvaffaqiyati: 6-qadam xoreografiya ~700ms, bloklamaydi; konfetti
  FAQAT kunlik plan bajarilganda, sessiyada bir marta
- Dashboard: skeleton→stagger 60ms→count-up 600ms+tick; sparkline/donut
  chizilib chiqadi; case amber BIR marta diqqat oladi; dark = token-scope
- Landing hero: 12s sikl (video emas), amber «Band, lekin to'lovsiz» lahzasi
  markazda; A varianti reduced-motion/mobil fallback; 3-qadam chiziq
  3-seksiyada; copy brief matnidan qulflangan

## Ochiq savollar (UI-SPEC bosqichiga)

- 001: «kunlik plan» qiymatining manbai (bozor sozlamasi?)
- 003: hero raqamlari namunaviy — pilotgacha «Karmana sinovda» holati
- Landing copy yakuniy tahriri (3 tilda) — quick-faza ichida
