# SBOZOR — UI/UX Masterplan: "10/10" darajasiga yo'l

> **Maqsad:** Bozor ma'muriyati ko'rganda "vau" deydigan, kassir charchamasdan ishlaydigan, direktor faxrlanib ko'rsatadigan platforma.
> **Tamoyil:** Redesign EMAS — mavjud sinalgan tizim ustiga professional jilo qatlami.
> **Sana:** 2026-08-15 · **Ijro:** limit tiklangach, 8-fazadan keyin

---

## 0. Falsafa — "10/10" nimadan iborat

Apple dizaynining uch ustuni (HIG) bizning kontekstda:

| Ustun | Apple'da | SBOZOR'da |
|---|---|---|
| **Clarity** (ravshanlik) | Har element o'z vazifasini aytadi | Kassir 1 soniyada nima qilishni biladi; direktor raqamni izlamaydi |
| **Deference** (kamtarlik) | UI kontentga xizmat qiladi | Rang va animatsiya PULGA va HOLATGA e'tibor qaratadi, o'ziga emas |
| **Depth** (chuqurlik) | Qatlamlar va harakat ma'no beradi | Dialog qayerdan ochilgani ko'rinadi; muhim narsa yaqinroq turadi |

**Psixologik qulaylik formulasi:** kam qaror + aniq javob + yumshoq harakat = charchamaslik.
Har ekranda foydalanuvchidan ko'pi bilan BITTA asosiy qaror so'raladi (kassir oqimi allaqachon shunday — bu standartni hamma yuzaga yoyamiz).

**Auditoriya cheklovlari (unutmaslik shart):**
- Bozor xodimlari — 40–60 yosh, texnikaga o'rganmagan → katta nishonlar, aniq yozuvlar, jargon yo'q
- Quyosh ostida telefon → yuqori kontrast rejimi
- Arzon Android telefonlar → 60fps faqat GPU-transformlar bilan, og'ir kutubxonasiz
- Erta tong (06:00) smenalar → dark mode qimmatli qulaylik

---

## 1. Rang tizimi 2.0

Mavjud 60/30/10 qoidasi saqlanadi, sifati ko'tariladi:

### 1.1 Asos palitra (light)
- **Fon:** sof oq EMAS — iliq neytral `#FAFAF9` (stone-50). Sof oq ko'zni tez charchatadi; iliq oq "qog'oz" hissi beradi
- **Yuzalar:** 3 daraja balandlik: `surface-0` (fon), `surface-1` (karta, +soya S), `surface-2` (dialog/popover, +soya M). Har daraja o'z soyasi bilan — "qatlam" hissi shu yerdan
- **Aksent:** mavjud ko'k saqlanadi, lekin ikki ton qo'shiladi: `accent-hover` (bosishdan oldin), `accent-pressed` (bosilganda quyuqroq) — tugma "tirik" bo'ladi
- **Semantik ranglar faqat ma'no uchun:** yashil = pul keldi/muvaffaqiyat, amber = kutilmoqda/e'tibor, qizil = qarz/xato. Hech qachon bezak uchun ishlatilmaydi

### 1.2 Gradientlar — juda ehtiyotkor
- Faqat 2 joyda: login sahifasi foni (juda nozik, deyarli sezilmas radial) va direktor bosh stat-kartasi (aksent 4% opacity)
- Boshqa hech qayerda — gradient ko'paysa "bozor bannerlari"ga aylanadi

### 1.3 Dark mode (yangi)
- Tong smenalari va kechki hisobot ko'rish uchun
- Token-almashtirish orqali (Tailwind 4 `@theme` allaqachon token asosida — arzon qo'shiladi)
- Kontrast: WCAG AA hamma matnda, pul raqamlarida AAA

### 1.4 Quyosh rejimi (yangi, kassir uchun)
- Bitta tugma: kontrast maksimal, soyalar o'chadi, shrift og'irlashadi
- Kassir sozlamasida saqlanadi

---

## 2. Tipografiya 2.0

Mavjud 4 rol (24/18/14/12) saqlanadi, ustiga:

- **Display-XL (36–44px)** — faqat pul summalari uchun: kassir "Kutilayotgan patta" va direktor "Bugungi tushum". Pul — bosh qahramon, shrifti ham shuni aytsin
- **`font-variant-numeric: tabular-nums`** — barcha raqamlarda (jadvallar, summalar): raqamlar ustun bo'ylab tekis turadi, "sakramaydi"
- Satr balandligi ritmi: 1.2 (sarlavha) / 1.5 (matn) — allaqachon bor, buziladigan joylar tekshiriladi

---

## 3. Harakat (Motion) tizimi — yadro

### 3.1 Tokenlar
```
--motion-fast:    150ms  (bosish javoblari, hover)
--motion-base:    250ms  (dialog, sahifa elementlari)
--motion-slow:    400ms  (sahna almashinuvi, bayram lahzalari)
--ease-out:       cubic-bezier(0.22, 1, 0.36, 1)   (standart — "yumshoq tormoz")
--ease-spring:    spring(1, 80, 12)                 (vau-lahzalar — jonli prujina)
```

### 3.2 Xoreografiya qoidalari
1. **Kirish:** elementlar 8px pastdan + fade, ro'yxatlarda 30ms ketma-ketlik (stagger) — sahifa "nafas olib" ochiladi
2. **Chiqish:** kirishdan 2× tez (150ms) — ketayotgan narsa ushlab turmaydi
3. **Dialog:** trigger tugmadan scale(0.96)+fade bilan ochiladi — "qayerdan kelgani" ko'rinadi
4. **Hech qachon:** aylanuvchi spinner (skeleton bor), cheksiz pulsatsiya, avtomatik harakat (foydalanuvchi boshlamagan)
5. **`prefers-reduced-motion`:** hamma harakat 0ms ga tushadi, faqat opacity qoladi — majburiy hurmat

### 3.3 Kassir oqimi — maxsus rejim
- Interaktiv javoblar ≤150ms (tezlik ≤3 bosishning bir qismi)
- Faqat YAKUN lahzasi sekin bo'lishi mumkin (pastga qarang) — chunki u bloklamaydi, mukofotlaydi

---

## 4. "VAU" lahzalari — imzo animatsiyalar

Mijoz kutayotgan qism. Har biri did bilan — sirk emas, Apple Pay darajasi:

### 4.1 ⭐ TO'LOV MUVAFFAQIYATI (bosh vau — kassir)
Xoreografiya (jami ~700ms, bloklamaydi):
1. "To'lovni tasdiqlash" bosilishi — tugma 0.97 scale, 100ms
2. Tugma ichida oq check-mark **chizilib paydo bo'ladi** (SVG stroke-draw, 250ms)
3. Karta yashil halqa to'lqini bilan "urib yuboriladi" (pulse ring, 300ms) — Apple Pay hissi
4. Summa raqami yuqoriga uchib, "Oxirgi to'lovlar" ro'yxatiga **qo'nadi** (shared-element, 400ms)
5. Ro'yxatdagi yangi qator yashildan neytralga so'nadi (800ms)
6. Qidiruv maydoni avtomatik fokus + tozalanadi — keyingi mijozga tayyor
- Katta summalarda (kunlik plan bajarilganda?) — bir martalik nozik konfetti (12 zarra, 600ms, faqat shu holatda)

### 4.2 SMENA YOPILISHI (kassir)
- Deklaratsiya tasdiqlangach: hujjat "muhrlanadi" — pechat bosilgan effekt (scale-down + soya urishi, 350ms), keyin summa kartasi qulflanadi (qulf ikonkasi jiringlab kiradi)

### 4.3 DIREKTOR TUSHUMI
- Sahifa ochilganda summa 0 dan haqiqiy qiymatgacha **sanab o'sadi** (600ms, ease-out) + oxirida nozik "tick" scale
- Yangi to'lov real vaqtda kelsa: raqam yumshoq yangilanadi + karta bir marta yashil nafas oladi

### 4.4 BOZOR YARATILDI (usta yakuni)
- 7/7 qadam tugaganda: qadamlar ro'yxati ketma-ket ✓ bo'lib chiqadi (stagger 60ms), so'ng bozor nomi markazga ko'tarilib "Bozor tayyor!" — bir martalik bayram (1s)

### 4.5 NVR KASHFIYOTI (admin)
- Kanallar topilganda ro'yxatga **birma-bir** qo'shiladi (stagger 80ms, chapdan slide+fade) — "radar topayapti" hissi
- Onlayn badge birinchi paydo bo'lishda bir marta yashil pulse

### 4.6 NOMUVOFIQLIK TOPILDI (direktor/admin)
- Yangi case amber chetdan sirg'alib kiradi + bir marta diqqat-pulse — lekin qayta-qayta pulsatsiya YO'Q (ogohlantirish charchatmasin)

---

## 5. Komponent darajasidagi jilo

| Komponent | Hozir | Bo'ladi |
|---|---|---|
| Tugmalar | statik | press scale 0.97 + soya chuqurlashishi; disabled holatda sabab tooltip |
| Kartalar | statik | hover'da 2px ko'tarilish + soya (faqat desktop) |
| Dialoglar | shunchaki paydo | trigger'dan scale+fade; fon 8% qorayadi + blur(4px) |
| Toast | bor (sonner) | spring bilan kiradi; muvaffaqiyat toastida mini check-draw |
| Yuklanish | Yuklanmoqda matni | skeleton-kartalar (kontent shakli oldindan); shimmer 1.5s |
| Formalar | yaxshi | xato maydoni yumshoq shake (2px, 200ms) + xabar slide-down; muvaffaqiyatda yashil border-pulse |
| Bo'sh holatlar | matn (yaxshi) | + nozik chiziqli SVG illustratsiyalar (bir uslub, 12 dona: bo'sh rasta, kamera, hisobot...) |
| Jadvallar | oddiy | qator hover; yangi qator kirish animatsiyasi; saralashda yumshoq qayta-tartib |
| Til almashtirgich | tugmalar | joriy til ostida sirg'aluvchi indikator (layout-persist) |

---

## 6. Yuzalar bo'yicha reja

### 6.1 Login
- Nozik jonli gradient-fon (juda sekin, 20s sikl, reduced-motion'da statik)
- Karta kirish animatsiyasi; xatoda karta shake EMAS — faqat xabar (xato allaqachon yaxshi)

### 6.2 Kassir (eng muhim yuza)
- 4.1 va 4.2 vau-lahzalari
- Qidiruv maydoni doim autofocus (bor) + katta raqamli klaviatura rejimi (inputmode)
- "Bugun yig'ildi" mini-hisoblagich headerda — kassir o'z natijasini ko'rib boradi (motivatsiya)

### 6.3 Direktor paneli (8-faza bilan birga)
- 2 ustunli grid (desktop bo'shligi yo'qoladi): tushum karta (count-up + 7 kunlik sparkline) · bandlik halqasi (donut, band/bo'sh) · qarzdorlik karta (qizil aksent, top-3 qarzdor) · nomuvofiqlik lenta
- Har karta bosilsa — tegishli hisobotga shared-element o'tish
- `.xlsx` yuklab olish tugmasi: bosilganda fayl ikonkasi "tushib kelayotgan" mikro-animatsiya

### 6.4 Plan-xarita (konva)
- **Avval MARKET-06 bo'shlig'i yopiladi** (TEST-REPORT №C): rang qatlami (yashil bo'sh · ko'k to'langan · qizil qarzdor · sariq nomuvofiq) + rasta bosilganda karta (dalil-rasm bilan) — bu MVP talabi
- **Keyin V2-PROC-04**: plan-rasm yuklash + rastalarni rasm ustida joylashtirish/chizish — kamera-zona muharririning (5-faza, konva) tayyor asosida; foydalanuvchi kutgan "bozor chizmasi asosida yaratish" tajribasi shu yerda to'liq bo'ladi
- Zoom inersiya bilan; rasta hover'da yumshoq glow; band rasta — to'liq holat rangi bilan
- Rasta bosilganda yon panel spring bilan ochiladi

### 6.5 Kameralar
- Kanal kartalariga snapshot thumbnail (pipeline'dan oxirgi kadr) — ro'yxat "jonli" ko'rinadi
- Onlayn/oflayn almashinuvida badge crossfade

### 6.6 Nazoratchi (ko'r audit)
- Klaviatura-birinchi: ←/→ = bo'sh/band, katta kadr, qaror ostida progress "bugun: 34/50"
- Har qarordan keyin kadr yumshoq almashinadi (crossfade 200ms) — konveyer charchatmaydi

### 6.7 Kadr olish / jadval
- Kunlik slotlar gorizontal timeline'da; bajarilgan slot ✓, o'tkazilgan ✗ qizil — bir qarashda kun holati

---

## 7. Mikro-UX tuzatishlar (majburiy, "vau"dan oldin)

Bular tuzatilmasa hech qanday animatsiya 10/10 qilmaydi:

1. **№1 — sana formati:** yagona util (`formatDate`) — `15-avg, 2026` / `15 авг 2026` (M08 yo'qoladi)
2. **№3 — pul formati:** yagona util (`formatMoney`) — `8 000 so'm` (bo'shliq ajratgich, so'm suffiks, uchala tilda izchil)
3. **№5 — manfiy vaqt:** `hozirgina / 2 daqiqa oldin / 3 soat oldin` nisbiy format
4. Terse validatsiyalar to'liq gapga: "To'lov turi" → "To'lov turini tanlang — Naqd yoki Terminal"
5. Desktop max-width konteyner + direktor 2 ustun
6. Sahifa sarlavhalarida breadcrumb emas — joriy bozor konteksti (bor) + sahifa ikonkasi

---

## 8. Texnik asos

- **Kutubxona:** `motion` (framer-motion vorisi, React 19 mos) — faqat vau-lahzalar va layout-animatsiyalar uchun; qolgan hamma narsa sof CSS (Tailwind 4 tokenlar). Bundle byudjeti: +35KB gzip MAX
- **Faqat GPU xossalari:** transform + opacity. width/height/top animatsiya QILINMAYDI (arzon telefonlarda 60fps sharti)
- **View Transitions API** — sahifalararo o'tishlar uchun progressiv (qo'llamaydigan brauzerda oddiy almashinuv)
- **Skeleton** — har async yuzada; data kelgach content crossfade
- **Tokenlar `@theme`da** — dark mode va quyosh rejimi token almashtirish orqali, komponent kodi o'zgarmaydi

## 9. Sifat darvozalari (GSD intizomi)

- Har yuza o'zgarishi UI-SPEC yangilanishi bilan (mavjud G-* darvoza tizimi kengayadi: G-motion-1 "reduced-motion hurmati", G-motion-2 "kassir interaktiv ≤150ms")
- Vitest: motion tokenlari mavjudligi, reduced-motion shoxlari
- Lighthouse byudjet: Performance ≥90 (arzon Android profili), CLS < 0.05
- 3 til: yangi copy kalitlari `i18n:check` dan o'tadi (1214+ kalit)
- Har bosqich alohida commit + skrinshot-solishtirish

## 10. Ijro tartibi (limit tiklangach)

| # | Buyruq | Nima beradi | Hajm |
|---|---|---|---|
| 1 | `/clear` → `/gsd-execute-phase 8` | Direktor hisobotlari + №1/№3/№5 tuzatishlar (20 reja tayyor) | katta |
| 2 | `/gsd:sketch` (shu hujjat asosida) | 3 jonli HTML maket: (a) motion tizimi namoyishi, (b) kassir vau-oqimi, (c) direktor paneli — **siz tanlaysiz** | kichik |
| 3 | `/gsd:ui-phase` (polish mini-faza) | Tanlangan yo'nalish UI-SPEC'ga qulflanadi | kichik |
| 4 | `/gsd:plan-phase` + `/gsd-execute-phase` (polish) | 5–7 to'lqinda butun platformaga tatbiq | o'rta |
| 5 | Yakuniy brauzer-sayr (4 rol) + mijoz demo tayyorligi | "10/10" tekshiruvi shu hujjat bo'yicha | kichik |

---

*Bu hujjat `/gsd:sketch` va UI-SPEC bosqichlarining kirish manbasi. O'zgartirish taklif qilinsa — shu faylga yozing, dizayn qarorlari shu yerdan oqadi.*
