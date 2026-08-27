---
status: pending
phase: 10-landing-sbozor-uz
source: [10-RESEARCH.md human_only_verifications, 10-UI-SPEC.md §16.5, 10-VALIDATION.md]
started: 2026-08-17
updated: 2026-08-17
---

> ⛔ **Mexanik qatlam 2026-08-17 da uch to'liq `gate` o'lchovi bilan
> tasdiqlangan (10-08, natijalar `package.json //gate-budget` jurnalida);
> bu bandlar INSON o'lchovini kutadi.** №2 dan boshqa birortasiga raqam
> YOZILMAGAN va birortasi «bajarildi» deb BELGILANMAGAN — o'lchovlar real
> qurilma, real deploy yoki inson idrokini talab qiladi va ular hali
> olinmagan (10-08 orkestrator qarori: RAQAM UYDIRILMAYDI). №2 istisno
> ATAYIN: uning o'lchovi 10-03 to'lqinida allaqachon OLINGAN va SUMMARY
> jadvalida saqlangan — bu yerda faqat ro'yxatga olinadi.

## Bu ro'yxat nima va nima EMAS

Bu — 10-fazaning **inson o'lchovi bandlari** (08/09-HUMAN-UAT naqshi):
CI'da **hech qachon o'lchanmaydigan** oltita xulq, har biri **egasi**,
**tetigi** va **SON bilan yopilish sharti** bilan. Mexanik qatlam nimani
o'lchagani va nimani o'lchay OLMAGANI har bandda ochiq yozilgan.

⛔ **Mexanika qatlamining yashilligi bilan o'lchov qatlamining yo'qligini
yopish TAQIQLANADI** [MEROS: D-01, FOUND-07 va AI-02 darsi]. Har band
⛔ **SON bilan** yopiladi — «tez ko'rinadi» / «chiroyli» imzo emas.

### Fazaning mezonlari bilan bog'liqlik

| Mezon | Mexanik qatlam (proksi) | ⛔ IMZO shu yerda |
|-------|--------------------------|-------------------|
| **SC#5** — Lighthouse ≥95, LCP <1,5 s | G-land-1(b) LCP yo'lida `"use client"` 0 · G-land-3 GPU xossalari · SEO fayl-konventsiyalari | **1, 2-bandlar** |
| **SC#2** — 12s sikl 60fps | G-land-2 taymer/IO/reduced-motion xulqi (jsdom) · G-land-3 layout-thrash sabablari 0 | **3-band** |
| **SC#3** — demo-forma → admin Telegram | `test_demo_request.py` (`respx` tarmoq chegarasida) · `EXEMPT_ROUTES` qamrovi | **4-band** |
| **SC#1/SC#4** — uch tilda halol matn | i18n parity · glossariy · G-land-4 taqiq-token/raqam skani | **5, 6-bandlar** |

---

## Current Test

[inson tekshiruvini kutmoqda — №1/№3 birinchi deploy yoki
`/gsd-verify-work` bosqichida, №4 birinchi deploy'da, №5 pilot
tayyorgarligi haftasida, №6 go-live'gacha; ijro oqimini bloklamaydi]

⚠ Sinov muhiti (2026-08-17 holati): `http://localhost:8081/uz` —
frontend prod build (nginx orqali); telefon uchun ayni tarmoqda
`http://<xost-LAN-IP>:8081/uz`. Lighthouse o'lchovi dev-serverda EMAS,
aynan prod-build ustida olinsin.

## Tests

### 1. SC#5 — LIGHTHOUSE ≥95 VA LCP <1,5 s (ARZON ANDROID PROFILI)

| Egasi | Tetigi | Imzo |
|-------|--------|------|
| **Ijrochi** (arzon Android qurilmasi bilan) | **Birinchi deploy yoki `/gsd-verify-work` bosqichi** | [ ] `____________` sana: `______` |

Lighthouse CI'da YO'Q va bu fazada QO'SHILMAGAN (10-UI-SPEC §16.5,
[QAROR]) — headless Chrome bog'liqligi `gate` byudjetiga daqiqalar
qo'shardi. Mexanik proksi TOR va u ATAYIN tor: G-land-1 LCP yo'lida
`"use client"` yo'qligini qulflaydi, G-land-3 layout-thrash sababini
yo'q qiladi. ⛔ Sabab yo'qligi natija borligini isbotlamaydi —
tadqiqotda o'lchangan uchinchi omil: `.motion-enter` `opacity:0` dan
boshlanadi va Chrome LCP `opacity:0` elementni chizilgan deb
hisoblamaydi, ya'ni `h1` ga `--i` kechikishi berilsa LCP mexanik
darvoza KO'RMAYDIGAN yo'l bilan suriladi.

expected: prod-build landing (`/uz`, `/uz-cyrl`, `/ru` uchalasi)
Lighthouse mobile profili (arzon Android emulyatsiyasi) bilan:
Performance ⛔ **≥95** va LCP ⛔ **<1,5 s**. Natija shu yerga **SON
bilan** yoziladi: `/uz` perf `____`, LCP `____ ms`; `/uz-cyrl` perf
`____`, LCP `____ ms`; `/ru` perf `____`, LCP `____ ms`. «Tez
ko'rinadi» imzo EMAS.
result: [pending]

### 2. SC#5 — PAYLOAD FARQI: PROVAYDER KO'CHIRISHIDAN OLDIN va KEYIN

| Egasi | Tetigi | Imzo |
|-------|--------|------|
| **Ijrochi** | **Provayder ko'chirishi to'lqini yakuni (10-03)** | [x] 10-03 ijrochisi — SUMMARY jadvali, sana: 2026-08-17 |

Bu o'lchov `next build` chiqishini talab qiladi va u test qatlamida
PRINSIPIAL ko'rinmaydi. ⛔ «~110 KB tejaladi» degan OLDINDAN da'vo
BERILMAGAN edi va o'lchovsiz BERILMADI (10-UI-SPEC §4.3 halollik
bandi) — quyidagi raqamlar refaktordan KEYINGI haqiqiy `next build`
jadvalidan (Turbopack chunk chegaralari qayta hisoblangan holda).

expected: route jadvali ikki nusxada (OLDIN/KEYIN), farq gzip KB da SON
bilan.
result: ⛔ **O'LCHANDI — 10-03 (2026-08-17), jadval
`10-03-SUMMARY.md` da saqlangan.** Ildiz marshruti First Load JS
**287,8 → 208,4 KB gz (−79,4)**; HTML(ru) **32,3 → 8,0 KB gz (−24,3)**;
HTML(uz-Cyrl) 30,0 → 7,7 (−22,3); HTML(uz-Latn) 26,3 → 6,9 (−19,4);
nazorat: `/ru/dashboard` **348,2 → 348,2 (0)**. Xom JS 1033,6 → 695,7 KB.
Ru anonim tashrifchi jami **~103,7 KB gzip** kam yuklaydi.

### 3. SC#2 — 60FPS ARZON ANDROID QURILMADA (12s SIKL + SCROLL-REVEAL)

| Egasi | Tetigi | Imzo |
|-------|--------|------|
| **Ijrochi** (dala qurilmasi bilan) | **Birinchi deploy yoki `/gsd-verify-work` bosqichi** | [ ] `____________` sana: `______` |

jsdom layout ham, kompozitsiya ham QILMAYDI — `getBoundingClientRect()`
nol, `Element.animate`/`getAnimations()` yo'q [O'LCHANDI: jsdom 30.0.1 +
vitest 4.1.10, 09-RESEARCH Tuzoq 1]. G-land-3 `transition`/`@keyframes`
xossalarini `transform`/`opacity` bilan qulflaydi — layout-thrash
SABABINI yo'q qiladi, lekin 30 katak + sweep + count-up bir vaqtda
ishlaganda arzon GPU baribir to'lishi mumkin. ⚠ Ikkinchi o'lchanmagan
omil [A2]: `container-type: inline-size` va `100cqw` ning maqsad
qurilmalardagi haqiqiy xulqi — sweep kengligi konteyner so'roviga
tayanadi va uni jsdom umuman hisoblamaydi.

expected: arzon Android (≤$150 sinf) Chrome DevTools remote profiling
bilan: (1) hero 12s sikli ⛔ **kamida 2 to'liq aylanish** kuzatiladi —
o'rtacha kadr tezligi ⛔ **≥55 fps**, 32ms dan uzun kadr ⛔ **≤2 ta**
har aylanishda; (2) sahifa oxirigacha scroll (reveal'lar) — o'rtacha
⛔ **≥55 fps**. `100cqw` sweep chizig'i konteynerdan chiqmasligi ko'z
bilan tasdiqlanadi. Natija **KADR/SONIYA raqami** bilan: hero
`____ fps`, scroll `____ fps`, uzun kadrlar `____ ta`.
result: [pending]

### 4. SC#3 — DEMO SO'ROVINING UCHIDAN-UCHIGA YETKAZILISHI

| Egasi | Tetigi | Imzo |
|-------|--------|------|
| **Mahsulot egasi** (admin akkaunti bilan) | **Birinchi deploy** | [ ] `____________` sana: `______` |

Integratsiya testi Telegram Bot API'ni `respx` bilan TUTADI va u to'g'ri
qaror — haqiqiy tokenni CI'ga bermaslik `alerts.py` 2-taqig'ining
bevosita talabi. Ya'ni test «biz to'g'ri so'rov yubordik»ni o'lchaydi,
«xabar chatga tushdi»ni EMAS. O'lchanmagani: token/chat_id
konfiguratsiyasi, chatning bot tomonidan yozish huquqi, xabar formatining
o'qilishi (uch tilda kelgan bozor nomi va ism) va admin uni haqiqatan
sotuv signali sifatida ko'rishi. `alerts_enabled=False` o'rnatmada tizim
`delivery_failed` beradi va bu HALOL — lekin uni faqat inson farqlaydi.

⛔ **PII intizomi (T-10-25, accept):** sinov so'rovlari ⛔ **FAQAT SOXTA
ism va soxta telefon** bilan yuboriladi — haqiqiy shaxs ma'lumoti sinov
uchun Telegram chegarasidan chiqarilmaydi. Bu shart LITERAL: «Sinov
Sinovov / +998 90 000 00 00» sinfidagi qiymatlar ishlatilsin.

expected: haqiqiy landing formasidan (uchala til birma-bir) haqiqiy
admin Telegram chatiga so'rov: natija ⛔ **«N ta sinov so'rovidan M tasi
chatga tushdi»** shaklida (kutilgan M=N), va kamida bitta ataylab buzuq
telefon `invalid_phone` xatosini formada ko'rsatadi (chatga tushmaydi).
result: [pending]

### 5. SC#1/SC#4 — KIRILL VA RUS MATNINING DAVLAT AUDITORIYASIDA O'QILISHI

| Egasi | Tetigi | Imzo |
|-------|--------|------|
| **Mahsulot egasi** (kirill o'qiydigan davlat vakili bilan) | **Pilot tayyorgarligi haftasi** | [ ] `____________` sana: `______` |

Transliteratsiya darvozasi lotin harfi qolmaganini o'lchaydi, glossariy
taqiqlangan sinonimlarni ushlaydi — ikkalasi LUG'AT darajasi.
O'lchanMAGANI ma'noning o'zi: tadqiqotda AYNAN shu bo'shliqdan ikki
defekt chiqdi (`AI` → `АИ` va `demonstratsiya` → `демонстратсия`),
ikkalasi sof kirill chiqish bergani uchun birorta darvoza ularni
ko'rmasdi. Qolgan ~119 kalitda shunga o'xshash semantik siljish bo'lishi
mumkin va uni faqat ona tilida o'qiydigan odam ko'radi. Rus matni esa
transliteratsiya hosilasi EMAS — mustaqil yozilgan va uslubi hech qanday
mexanik o'lchov ostida turmaydi.

expected: hokimlik proyektorida VA telefonda `/uz-cyrl` hamda `/ru`
to'liq o'qib chiqiladi (hero → FAQ → forma → maxfiylik sahifasi);
natija ⛔ **«N ta tuzatish kiritildi»** ro'yxati bilan (N=0 ham natija —
lekin u ham SON) va tuzatishlar `messages/*.json` commit'iga bog'lanadi.
result: [pending]

### 6. SC#4 — `landing.trustBlock.residency.body` NING YURIST TASDIG'I

| Egasi | Tetigi | Imzo |
|-------|--------|------|
| **Mahsulot egasi** (mahalliy yurist bilan) | **Go-live** (STATE.md «Huquqiy ko'rik» blokeri, 10-UI-SPEC §11.2 huquqiy tuguni) | [ ] `____________` sana: `______` |

Ishonch blokining rezidentlik bandi («ma'lumotlar O'zbekistonda…»)
ommaviy HUQUQIY da'vo — u O'zR shaxsiy ma'lumotlar qonuni ostidagi
majburiyat matni. Mexanik qatlam faqat kalitning uchala tilda
MAVJUDLIGINI o'lchaydi (G-land-4(c)); matnning yuridik to'g'riligi,
Telegram chegarasi (xabar matni O'zR tashqarisidagi Telegram serverlari
orqali o'tishi — `alerts.py` 1-taqiq konteksti) bilan zid emasligini va
maxfiylik sahifasi bilan izchilligini faqat mahalliy yurist tasdiqlaydi.
STATE.md «Huquqiy ko'rik» blokeri (kvitansiya maydonlari, CCTV shaxsiy
ma'lumot) bilan BIR tugunda ko'riladi.

expected: yurist ko'rigi uchala tildagi residency matni + maxfiylik
sahifasi ustida; natija ⛔ **«N ta tahrir talab qilindi»** ro'yxati
bilan (N=0 ham SON) va imzo yurist ismi bilan qo'yiladi.
result: [pending]
