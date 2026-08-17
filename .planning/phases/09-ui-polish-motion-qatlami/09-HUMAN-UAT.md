---
status: pending
phase: 09-ui-polish-motion-qatlami
source: [09-UI-SPEC.md §16.6, 09-RESEARCH.md human_only_verifications, 09-VALIDATION.md]
started: 2026-08-17
updated: 2026-08-17
---

## Bu ro'yxat nima va nima EMAS

Bu — 9-fazaning **inson o'lchovi bandlari** (08-HUMAN-UAT naqshi): CI'da
**hech qachon o'lchanmaydigan** beshta xulq, har biri **egasi**, **tetigi**
va **imzosi** bilan. Mexanik qatlam nimani o'lchagani va nimani o'lchay
OLMAGANI har bandda ochiq yozilgan.

⛔ **Mexanika qatlamining yashilligi bilan o'lchov qatlamining yo'qligini
yopish TAQIQLANADI** [MEROS: D-01, FOUND-07 va AI-02 darsi]. Har band
⛔ **SON bilan** yopiladi — «ko'rinishi yaxshi» imzo emas.

### Fazaning mezonlari bilan bog'liqlik

| Mezon | Mexanik qatlam (proksi) | ⛔ IMZO shu yerda |
|-------|--------------------------|-------------------|
| **SC#5** — 60fps + Lighthouse ≥90 | G-motion-3(a) GPU xossalari · G-motion-7(c) skeleton geometriyasi · G-motion-3(d) 0 KB | **1, 2-bandlar** |
| **SC#3** — uch tema | G-motion-4 token-scope · G-motion-5 kontrast reyestri | **3-band** |
| **SC#1/SC#4** — bayram bloklamaydi | G-motion-2 sintetik 150ms o'lchovi | **4-band** |
| **SC#4** — reduced-motion | G-motion-1 global blok + mock shoxi | **5-band** |

---

## Current Test

[inson tekshiruvini kutmoqda — bandlar Wave 3 yakuni va pilot
tayyorgarligi haftasida bajariladi; ijro oqimini bloklamaydi]

## Tests

### 1. SC#5 — 60FPS ARZON ANDROID QURILMADA

| Egasi | Tetigi | Imzo |
|-------|--------|------|
| **Ijrochi** (dala qurilmasi bilan) | **Wave 3 yakuni** | [ ] `____________` sana: `______` |

jsdom layout ham, kompozitsiya ham qilmaydi — `getBoundingClientRect()`
nol, `Element.animate`/`getAnimations()` yo'q [O'LCHANDI: jsdom 30.0.1].
G-motion-3(a) layout-thrash **sababini** yo'q qiladi (faqat GPU xossalari),
lekin sabab yo'qligi natija borligini isbotlamaydi.

expected: arzon Android (≤$150 sinf, masalan Redmi/Samsung A-seriya)
Chrome DevTools remote profiling bilan: (1) kassir 6-qadam xoreografiyasi
**5 marta** ketma-ket ishga tushiriladi — o'rtacha kadr tezligi
⛔ **≥55 fps**, 32ms dan uzun kadr ⛔ **≤2 ta** (har yugurishda);
(2) dashboard birinchi ochilishi (skeleton → stagger → count-up) —
o'rtacha ⛔ **≥55 fps**. Natija shu yerga **KADR/SONIYA raqami** bilan
yoziladi: xoreografiya `____ fps`, dashboard `____ fps`, uzun kadrlar
`____ ta`.
result: [pending]

---

### 2. SC#5 — LIGHTHOUSE PERFORMANCE ≥90 VA CLS <0.05

| Egasi | Tetigi | Imzo |
|-------|--------|------|
| **Ijrochi** | **Wave 3 yakuni** | [ ] `____________` sana: `______` |

Lighthouse CI'da YO'Q va bu fazada QO'SHILMAYDI (09-UI-SPEC §16.6) — u
headless Chrome + yangi dev bog'liqlik talab qiladi va `gate` byudjetiga
daqiqalar qo'shardi. CLS uchun mexanik proksi G-motion-7(c) (skeleton
geometriyasi) **TOR**: u CLS ning AYNAN sababini [M-25: 8–12px] yopadi,
lekin YAGONA sababini emas (shrift, kech kelgan karta, rasm).

expected: Chrome DevTools Lighthouse, **Moto G Power / Slow 4G** profili,
uchta sahifa: `/collect`, `/dashboard`, `/reports`. Har birida:
Performance ⛔ **≥90** va CLS ⛔ **<0.05**. Natija **SON bilan**:
collect `____ / CLS ____`, dashboard `____ / CLS ____`,
reports `____ / CLS ____`. «Ko'rinishi yaxshi» imzo EMAS.
result: [pending]

---

### 3. SC#3 — UCH TEMANING VIZUAL IDROKI (uch rol, real ekranlarda)

| Egasi | Tetigi | Imzo |
|-------|--------|------|
| **Mahsulot egasi** (kassir va direktor bilan) | **pilot tayyorgarligi haftasi** | [ ] `____________` sana: `______` |

G-motion-5 kontrast **nisbatini** o'lchaydi va u matematik to'liq
(12+ juftlik × 3 tema, izohlar ±0.01 qulflangan). O'lchanmagani — o'sha
nisbatlarning **odam ko'zida** ishlashi: ierarxiya o'qilishi, dark'da
karta konturining ko'rinishi, quyoshda soyasiz kartaning yuzadan ajralishi.

expected: ⛔ **3 tema × 3 rol = 9 katak** jadvali to'ldiriladi: kassir
(`/collect`, ochiq havoda telefonda — `sun` majburiy), direktor
(`/dashboard` + `/reports`, ofis), admin (usta + sozlamalar). Har katakda
«o'qildi / nuqson» va nuqson bo'lsa ⛔ **TOKEN NOMI** bilan (masalan
`--color-border` dark'da ko'rinmadi). To'ldirilgan kataklar soni: `__ / 9`;
topilgan nuqsonlar: `____ ta`, har biri token nomi bilan.
result: [pending]

---

### 4. SC#1/SC#4 — BAYRAM BLOKLAMAGANINING DALA TASDIG'I (20 ketma-ket to'lov)

| Egasi | Tetigi | Imzo |
|-------|--------|------|
| **Mahsulot egasi** (kassir bilan) | **pilot tayyorgarligi haftasi** | [ ] `____________` sana: `______` |

G-motion-2 buni sintetik o'lchaydi (150ms nuqtasida yozilgan belgi to'liq
turadi) — lekin BITTA to'lov, BITTA soxta taymer, jsdom. Dala nosozligi
boshqacha ko'rinadi: «input bloklandi» emas, «kassir ikkilanib to'xtadi» —
uni faqat kuzatish ko'radi. Bu fazaning eng qimmat nuqsoni (09-UI-SPEC §1.2).

expected: kassir real telefonda ⛔ **20 ketma-ket** to'lov yozadi, har
birida keyingi rasta kodini **darhol** (bayram tugashini kutmasdan) teradi.
O'lchov: (1) yo'qolgan/qayta terilgan belgi ⛔ **0 ta**; (2) kassir
to'xtab qolgan holat ⛔ **0 ta**; (3) 20 to'lovning jami vaqti yoziladi:
`____ daq ____ son`. Natija: `__ / 20` muvaffaqiyatli, yo'qolgan belgi
`____ ta`.
result: [pending]

---

### 5. SC#4 — VESTIBULYAR SEZGIR FOYDALANUVCHI TASDIG'I (OS reduced-motion)

| Egasi | Tetigi | Imzo |
|-------|--------|------|
| **Ijrochi** (OS sozlamasi yoqilgan holda) | **Wave 3 yakuni** | [ ] `____________` sana: `______` |

G-motion-1 `matchMedia` MOCK'i bilan o'lchaydi — «kod shoxi to'g'rimi?»
savoliga javob beradi. O'lchanmagani: brauzerning HAQIQIY signali bilan
CSS `@media` blokining ishlashi va uchinchi tomon xulqi (Radix dialog,
`sonner` toast). jsdom'da CSS umuman yuklanmaydi [O'LCHANDI].

expected: OS darajasida reduced-motion yoqiladi (Windows: Settings →
Accessibility → Visual effects → Animation effects OFF; Android: Remove
animations). ⛔ **6 sahifa** aylanib chiqiladi: `/collect` (to'lov yozish
bilan), `/dashboard`, `/reports`, `/review`, `/stalls`, dialog ochish +
toast chiqarish. Kuzatilgan harakat (spinner aylanishidan tashqari
istisno yo'q): ⛔ **0 ta**. To'lov natijasi AYNI qoladi (qator bor, fokus
inputda). Natija: tekshirilgan sahifalar `__ / 6`, kuzatilgan harakat
`____ ta` (kutilgan: 0).
result: [pending]
