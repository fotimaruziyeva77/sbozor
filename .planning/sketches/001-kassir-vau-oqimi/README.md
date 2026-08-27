---
sketch: 001
name: kassir-vau-oqimi
question: "To'lov muvaffaqiyati qay darajada «bayram» bo'lsin — minimal, to'liq xoreografiya yoki konfetti bilan?"
winner: "B"
tags: [motion, kassir, vau]
---

# Sketch 001: Kassir vau-oqimi

## Dizayn savoli
Masterplan §4.1 bosh vau-lahzani belgilagan (check-draw → pulse → uchish →
count-up). Savol: bu xoreografiyaning QANCHASI to'g'ri his beradi — va konfetti
qachon o'rinli?

## Ochish
`start .planning\sketches\001-kassir-vau-oqimi\index.html` (Windows)

## Variantlar
- **A: Minimal** — check-draw + qator qo'shilishi, ~400ms. Hech narsa uchmaydi.
- **B: Apple Pay to'liq ★ (tavsiya)** — §4.1 ning 6 qadami to'liq: check →
  halqa pulsi → summa ro'yxatga uchib qo'nadi → yashil so'nish → count-up →
  avtofokus. ~700ms, lekin bloklamaydi (input darhol tayyor).
- **C: B + plan-konfetti** — hudди B; KUNLIK PLAN bajarilganda (maketda har
  3-to'lovda) 12 zarra, 600ms, bir marta.

## Nimaga qarash kerak
1. B ning "uchishi" ortiqcha his beradimi yoki aynan Apple Pay darajasimi?
2. To'lovdan keyin qidiruvga qaytish tezligi — kassir ritmi buziladimi?
3. C konfettisi har 3-to'lovda ko'rsatilgan; realda faqat kunlik plan
   bajarilganda bo'ladi — shart yetarlicha tormi?
4. Toolbar'dan «Iliq (rang 2.0)» temaga o'tkazib ko'ring — fon hissi.

## Tavsiya sababi (avtonom rejim)
**B.** Masterplan §4.1 aynan shu 6-qadam xoreografiyani mijoz talabi sifatida
yozgan; A uni bajarmaydi, C esa konfettini odatiy oqimga aralashtirish xavfiga
ega. C ning konfettisi UI-SPEC'ga TOR shart bilan kiradi: faqat kunlik plan
bajarilganda, sessiyada bir marta. ≤150ms qoidasi B da buzilmaydi: bloklovchi
qism yo'q, input ~150ms ichida yana tayyor.
