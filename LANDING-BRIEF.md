# sbozor.uz — Landing Page Brief

> **Maqsad:** Bozor direktori yoki hokimlik vakili 30 soniyada tushunadi: *"bu bizga kerak"* — va demo so'raydi.
> **Sana:** 2026-08-15 · **Ijro:** UI-polish bilan birga yoki undan keyin (go-live'dan OLDIN shart)

---

## 1. Auditoriya va bitta vazifa

| Kim | Nima izlaydi | Landing javobi |
|---|---|---|
| **Bozor direktori** | "Pattam to'liq yig'ilyaptimi?" | Bosh sarlavhaning o'zi shu savol |
| **Bozor MChJ ta'sischisi** | Daromad yo'qotish qayerda | Raqamlar: "band, lekin to'lovsiz" fosh bo'ladi |
| **Hokimlik / davlat dasturi** | Raqamlashtirish, shaffoflik, rezidentlik | Alohida blok: xavfsizlik + O'zR qonunlariga moslik |

**Yagona CTA:** "Demo so'rang" (telefon/forma). Ikkinchi darajali: "Tizimga kirish" (mavjud mijozlar → app).
Boshqa hech narsa — narx kalkulyatori, ro'yxatdan o'tish, blog — MVP landingda YO'Q.

## 2. Sahifa strukturasi (yuqoridan pastga)

1. **Hero:** sarlavha *"Har bir band rastadan patta to'liq yig'ilyaptimi?"* + javob: *"SBOZOR buni raqamlar va rasm-dalil bilan ko'rsatadi."* CTA + ekranda jonli animatsion mockup (direktor paneli: raqamlar sanab o'sadi, nomuvofiqlik kartasi kirib keladi — mahsulotning o'zi reklama)
2. **Og'riq (3 karta):** daftar-hisob adashadi · kim to'lamaganini bilib bo'lmaydi · nazoratchi hammasini ko'rolmaydi
3. **Yechim — qanday ishlaydi (3 qadam, chiziqli animatsiya):** Mavjud kameralar kadr oladi → AI band rastani aniqlaydi → kunlik hisobotda "band, lekin to'lovsiz" ro'yxati
4. **⭐ Bosh dalil:** *"Yangi uskuna shart emas — mavjud NVR kameralaringiz bilan ishlaydi. Ulanish — login-parol kiritish, xolos."* (self-service — raqobat ustunligi)
5. **Rol-kartalar:** Direktor (hisobot + xlsx) · Kassir (3 bosishda to'lov) · Nazoratchi (rasm-dalil) — har birida app'dan real skrinshot
6. **Ishonch bloki (davlat uchun):** ma'lumotlar O'zbekistonda · NVR faqat VPN orqali, internetga ochilmaydi · har amal audit jurnalida · 3 til
7. **Pilot natijalari** (Karmana go-live'dan keyin to'ldiriladi — hozircha "Karmana bozorida sinovda" holati, yolg'on raqam YO'Q)
8. **FAQ (5-6 savol):** kameramiz eskimi? · internetimiz sekin · nechta rasta ko'taradi · narx qanday shakllanadi (demo'da aytiladi) · o'rnatish qancha vaqt
9. **Kontakt/CTA takrori** + footer (maxfiylik siyosati — CCTV shaxsiy ma'lumot qonuni uchun majburiy sahifa)

## 3. Dizayn

- **Masterplan tizimining o'zi** (UI-UX-MASTERPLAN.md): iliq fon, bitta ko'k aksent, xuddi shu tipografiya — landing va app BIR OILA bo'lib ko'rinadi (mijoz demoda "reklamadagi bilan bir xil ekan" deydi)
- Landing'da harakat erkinroq: scroll-reveal bloklari, hero'da jonli mockup, qadamlar chizig'i animatsiyasi — lekin baribir did chegarasida
- Real skrinshotlar (app'dan) — stok rasm va soxta mockup YO'Q
- Mobil-birinchi: hokimlik vakili ham telefonda ochadi

## 4. Texnik qaror (tavsiya)

- **Alohida sayt EMAS — mavjud Next.js ichida `(marketing)` route-guruhi**: bir dizayn-tizim, bir i18n (uz-Latn / uz-Cyrl / ru — davlat uchun kirill muhim!), bir deploy
- Statik generatsiya (SSG) — tez, SEO-tayyor; auth talab qilmaydi
- Marshrut: `sbozor.uz/` (anonim) = landing · "Kirish" tugmasi → app login. App allaqachon `/login`ga redirect qiladi — landing anonim root'ni egallaydi
- SEO: meta + OG-rasmlar + structured data; Lighthouse ≥95 (statik sahifada oson)
- Forma: demo so'rovi → hozircha Telegram-xabar admin botga (mavjud bot-service infra) — alohida CRM YO'Q

## 5. Ijro tartibiga qo'shimcha

Masterplan 10-bo'limidagi jadvalga qo'shiladi:

| # | Buyruq | Nima |
|---|---|---|
| 2.5 | `/gsd:sketch` (landing varianti bilan birga) | Hero + 3-qadam bloki maketi ham sketch'ga kiradi |
| 4.5 | Landing quick-faza (3-4 reja) | `(marketing)` route-guruh + kontent 3 tilda + demo-forma → bot |

Hajmi kichik: asosan statik kontent + masterplan tokenlari. Eng qimmat qismi — matn (copywriting), u shu briefda 70% tayyor.

---

## 6. Raqobatchi tahlili: raqamli-bozor.uz (Realsoft MChJ) — 2026-08-15 jonli o'rganish

**Kim:** Realsoft MChJ (Toshkent, yirik dasturchi kompaniya). Jiddiy raqib: real deployment bor — landing'da Pastdargom bozori skrinshoti (828 rasta: 222 to'langan / 608 to'lanmagan rang-xaritada).

**Qamrovi bizdan keng:** bozor + avtoturargoh + avtomatik ijara shartnomalari + shaxsiy hisob varaqlari + sotuvchi mobil ilovasi (holati: "ishlab chiqilmoqda", lekin App Store/Google Play badge'lari allaqachon turibdi — halollik bo'shlig'i).

### Ularning kuchli tomonlari
- Brend jilosi: iliq krem fon + serif sarlavha + apelsin aksent, dark mode, 4 til (kirill default — davlat auditoriyasiga to'g'ri)
- Real mahsulot skrinshoti (plan-xarita, to'lov statuslari) — da'vo emas, isbot
- Keng qamrov hikoyasi hokimlikka yoqadi ("hammasi bitta tizimda")

### Ularning zaif joylari — bizning imkoniyatlar
| Bo'shliq | Bizning javob |
|---|---|
| **Lead-capture YO'Q** — demo formasi yo'q, CTA faqat "Kirish" (mavjud mijozlarga), aloqa faqat telefon/email footer'da | Bizda bosh CTA = "Demo so'rang" formasi (bot orqali) |
| **Copy umumiy-byurokratik** — "samaradorlikni oshiradi, korrupsiyani oldini oladi"; birorta konkret savol/raqam yo'q; bloklar takrorlangan | Bizniki og'riq-savol bilan boshlanadi + konkret mexanizm |
| **"Qanday ulanadi" umuman yo'q** — o'rnatish jarayoni sir; muhandis-o'rnatish modeli sezildi | ⭐ Bosh dalilimiz: "mavjud kameralar, login-parol kifoya" — self-service |
| **AI aniqligi — da'vo, dalil yo'q** | Bizda ko'r-audit metodikasi + AI aniqlik hisoboti (8-faza) — "aniqligimizni o'lchab ko'rsatamiz" |
| **Ishonch bloki yo'q** (rezidentlik, NVR xavfsizligi, audit) | Bizda alohida davlat-ishonch bloki |
| **SEO uyquda** — sahifa title'i "Smart Office" (!) | Title/OG/structured data — arzon g'alaba |
| **App UI eski uslub** (zich admin-panel skrinshoti) | Apple-minimal app skrinshotlari — yangi avlod farqi ko'zga ko'rinadi |

### Pozitsiyalash xulosasi
Ular — "keng platforma" (bozor+parking+hujjat). Biz — **bitta savolga o'tkir javob**: *"har bir band rastadan patta yig'ilyaptimi?"* + rasm-dalil + o'lchanadigan AI aniqligi + 5 daqiqada ulanish. Fokus = ishonch. Landing matni har blokda shu kontrastni his qildirsin (raqibni nomlamasdan).

*Qo'shimcha: repoda `Raqamli-bozor_vs_eBazaar_tahlil.docx` bor — chuqur biznes-tahlil; sketch bosqichida shu bilan birga ishlatiladi.*

---

## 7. "Sehr" kontsepti — landing odamni qanday rom qiladi

> Realsoft statik skrinshot ko'rsatadi. **Biz voqeani sodir bo'layotganini ko'rsatamiz.** Sehrning siri shu.

### 7.1 Bosh g'oya: "Jonli bozor" hero
Hero'da mahsulotning stilizatsiyalangan plan-xaritasi **yashaydi** — 12 soniyalik rejissyorlangan sikl, so'zsiz butun hikoyani aytadi:

1. (0–3s) Bozor xaritasi chiziladi — rastalar birma-bir paydo bo'ladi (stagger)
2. (3–5s) Kamera "nur chizig'i" xarita ustidan o'tadi — rastalar **yashil** yonadi (band + to'langan)
3. (5–8s) Bitta rasta **amber** yonib qoladi — "Band, lekin to'lovsiz" yorlig'i chiqadi (mahsulotning butun ma'nosi shu bir soniyada)
4. (8–10s) Kassir belgisi yaqinlashadi → to'lov → rasta yashilga o'tadi + tepada tushum raqami sanab o'sadi
5. (10–12s) Direktor hisoboti karta sifatida yig'iladi → sikl yumshoq qaytadi

Texnika: yengil canvas/SVG + CSS, video EMAS (tez yuklanadi, har tilda matn almashadi, reduced-motion'da statik final-kadr).

### 7.2 Scroll-hikoya: "Bozorning bir kuni"
Apple mahsulot sahifalari uslubida — scroll qilgan sari bitta uzluksiz voqea:
**06:00 kamera kadri** (haqiqiy snapshot estetikasi) → **AI ramkalari** chiziladi (band/bo'sh) → **kassir 3 bosishi** (telefon mockup'ida jonli ketma-ketlik) → **direktor hisoboti** (raqamlar ko'rinishga kirganda sanab o'sadi) → **"Demo so'rang"**.
Har blok scroll bilan ochiladi (reveal), lekin parallax-sirk YO'Q — bitta yo'nalish, bitta hikoya.

### 7.3 Mikro-sehrlar (desktop)
- CTA tugmasida kursor-yaqinlik nuri (subtle glow follow)
- Raqamlar har doim ko'rinishga kirganda count-up (bir marta)
- Rol-kartalarda hover: app skrinshoti ichida mini-harakat (masalan, kassir kartasida to'lov toasti ko'rinadi)
- Fonda juda nozik donadorlik (grain) — "tirik qog'oz" hissi, gradientsiz

### 7.4 Sehr chegarasi (intizom)
- Birinchi ekran LCP < 1.5s — sehr sekin yuklansa, sehr emas
- Hamma harakat GPU (transform/opacity), 60fps arzon telefonda
- `prefers-reduced-motion` → statik, lekin baribir chiroyli (kompozitsiya sehri harakatga bog'lanmagan)
- Mobilda scroll-hikoya soddalashadi (vertikal kartalar) — sehr desktop demo/proyektor uchun to'liq kuchda (hokimlik prezentatsiyalari!)

### 7.5 Ustunlik kartasi (Realsoft'ga nisbatan, o'lchanadigan)

| O'lchov | Ular (bugun) | Biz (maqsad) |
|---|---|---|
| Hero | Statik foto + umumiy shior | Jonli mahsulot-hikoya (12s sikl) |
| Lead | Faqat telefon footer'da | Demo-forma + 24 soatda aloqa va'dasi |
| Copy | Byurokratik, takrorlangan | Og'riq-savol + konkret mexanizm, 3 tilda toza |
| Isbot | 1 skrinshot | Jonli demo + o'lchanadigan AI aniqligi (ko'r-audit) |
| Ulanish hikoyasi | Yo'q | "Login-parol, 5 daqiqa" — qadamma-qadam ko'rsatiladi |
| SEO | title="Smart Office" | To'liq meta/OG/structured, Lighthouse ≥95 |
| App UI | Zich eski admin | Apple-minimal, motion-tizimli (masterplan) |
| Halollik | "Ishlab chiqilmoqda" + do'kon badge'lari | Faqat mavjud narsa ko'rsatiladi; pilot holati ochiq yoziladi |

**Strategik eslatma (halol maslahat):** ularning kengligi (avtoturargoh, shartnomalar) bilan MVP'da bellashmaymiz — bu ularning o'yin maydoni. Bizning sehr: **fokus + isbot + tezlik**. Hokimlik ikkala saytni ochganda farqni 10 soniyada his qilishi kerak: ularniki "kompaniya prezentatsiyasi", bizniki "mahsulot o'zi gapiryapti".

---

*Kontent-matnlar (hero, og'riq, FAQ) yakuniy tahriri sketch bosqichida siz bilan birga qilinadi — bu hujjat skelet va yo'nalish.*
