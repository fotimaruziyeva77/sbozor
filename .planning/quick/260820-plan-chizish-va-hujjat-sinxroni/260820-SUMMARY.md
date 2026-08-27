---
phase: quick
plan: 260820
subsystem: ui + docs
tags: [nextjs, react, fastapi, sqlalchemy, alembic, rls, pointer-events, wcag, tdd, planning-hygiene]

# Dependency graph
requires:
  - phase: 02-bozor-domeni-va-yangi-bozor-ustasi
    provides: "`GET /stalls/map` (zona bloklari, `code_sort` tartibi), `StallCell` — ton, ikonka, `aria-label`, 44px nishon"
  - phase: 05-kamera-zonalari-cv-va-nazoratchi-tasdig-i
    provides: "D-16 — kamera hech qachon faollashtirishni to'smaydi (kamerasiz rejimning asosi)"
  - phase: 06-billing-va-kassir
    provides: "`GET /billing/map` to'lov qatlami — chizilgan planda ham AYNAN o'sha ranglar"
provides:
  - "`PUT /stalls/plan` — butun chizma bitta tanada, sanoqlar `rowcount` dan"
  - "`stalls.plan_x` / `plan_y` (nullable) + uchta CHECK — 0026 migratsiyasi"
  - "`/map/plan` — qo'lda chizish muharriri (`stall_manage` ostida)"
  - "`plan-model.ts` — sof model: `cellsBetween`, `placeSequence`, `planDiff`"
  - "`/map` da Sxematik / Chizilgan plan almashtirgichi"
  - "`nav.switchMarket` — menyuda bozor almashtirish (avval orfan satr edi)"
  - "`check-requirements-sync.mjs` — to'rt reja faylini MEXANIK solishtiradi"
affects: [deploy-subdomain, kelajakdagi-faza-yopilishlari]
---

# 260820 — Qo'lda chizish, kamerasiz rejim va hujjat sinxroni

## Nima so'ralgan edi

Foydalanuvchi ketma-ket: «ha qo'lda chizish qurilsin» → «endi muammosiz
ishlaydimi tizim» → «nechi foiz» → «FOUND-01…05 tavsiya bo'yicha hal
qil» → «butunlay yop».

Va bitta shart butun ishning ustidan turdi:

> «hozir biz **vaqtinchalik kamerasiz** ishlatamiz o'shanda ham
> muammosiz ishlashi kerak bozor / kameralarni mikrotik orqali
> ulaymiz chiqaramiz ushanda ishlab ketadi hammasi»

## 1. Qo'lda chizish — nima qurildi

Bosh harakat **bitta**: bo'sh katakni bosish. Navbatdagi rasta o'sha
yerga tushadi va navbat o'zi siljiydi — ya'ni qator «bos-bos-bos»
bilan teriladi. Surish qatorni bir harakatda to'kadi.

Chizma **IXTIYORIY QATLAM**: koordinatasiz bozor sxematik ko'rinishda
ishlashda davom etadi va hech qachon «avval chizing» devoriga
urilmaydi — D-16 bilan bir xil falsafa.

⛔ **`konva`/`react-konva` QO'SHILMADI**, garchi `CLAUDE.md` ularni
aynan shu ish uchun sanab o'tgan bo'lsa ham. Sabab `stall-map.tsx` da
allaqachon o'lchangan: panjara STATIK va kataklar haqiqiy `<button>`
bo'lishi kerak — klaviatura, fokus, skrinrider va SSR tekinga keladi.
Canvas bularning hammasini qo'lda qayta yozishni talab qilardi,
evaziga esa bizga kerak bo'lmagan yagona narsani — 60 fps qayta
chizishni — berardi. **Ikki yangi bog'liqlik, nol foyda.**

## 2. Chromeda topilgan uch nuqson — hammasi «ishlaydigan ko'rinishda»

⛔⛔ **BULARNING BIRORTASI TESTDA, LINTDA YOKI BUILD'DA KO'RINMASDI.**

| # | Nuqson | Nima bo'lardi |
|---|---|---|
| 1 | Kataklar orasidagi **4px oraliq bosishni yutardi** | Hodisa katakka emas, konteynerga tushardi. Sichqonchada «tegmadim» bo'lib tuyulardi, barmoqda esa har uchinchi urinish yo'qolardi |
| 2 | **Tez surish oraliq kataklarni tashlab ketardi** | O'lchovda 1, 3 va 10-ustunlar to'ldi, oradagilari bo'sh qoldi. Bu shunchaki teshik EMAS: navbat siljigani uchun KEYINGI rastalar ham noto'g'ri joyga tushardi — ya'ni tez harakat chizmani jimgina buzardi |
| 3 | `hasPointerCapture` yo'q muhitda **`pointerdown` istisno bilan uzilardi** | Butun bosish yo'q bo'lardi. Chaqiruv endi asosiy ishdan KEYIN |

Uchalasi ham `plan-editor.test.tsx` va `plan-model.test.tsx` da
qulflandi, har biri **sabotaj bilan** tekshirildi.

## 3. Chizilgan ko'rinishning uchta kamchiligi

Chizma ekranga chiqqach uchtasi ko'rindi:

* **Legenda yo'qolardi.** Kataklar ikkala ko'rinishda AYNAN bir xil
  ranglarni oladi (bitta `StallCell`), lekin «Belgilar» faqat
  sxematikda edi — plan ochilganda qizil-ko'k-yashil tushuntirishsiz
  qolardi (WCAG 1.4.1).
* **Qidiruv jim ishlamasdi.** Maydon ikkala ko'rinish USTIDA turadi,
  fokus mantig'i esa faqat `stall-map.tsx` da edi.
* **«Topilmadi» degan nozik yolg'on.** Chizilmagan rastani qidirsangiz
  «xaritada topilmadi» derdi — aslida rasta bozorda BOR. Endi uch
  holat: chizilgan / bor-u chizilmagan (qayerga qarashni AYTADI) /
  umuman yo'q.

⚠ Yon topilma: `scrollIntoView` jsdom'da yo'q ekan va shu sabab
**sxematik xaritaning qidiruv effekti hech qachon test bilan
yurmagan**. Polifil MUHITGA qo'yildi, komponentga qo'riqchi
QO'YILMADI — brauzerda bu API har doim bor va qo'riqchi haqiqiy
nosozlikni yutib yuborardi.

## 4. Kamerasiz rejim

Panel «86% tayyor» deb turardi — ya'ni to'liq ishlayotgan bozorni
CHALA deb ko'rsatardi, har kuni. Kamera qadami `optional` bo'ldi,
«kamera ulanmagan» diqqat bandi esa BUTUNLAY olib tashlandi: har kuni
ko'rinadigan va hech qachon hal qilinmaydigan ogohlantirish
ogohlantirishning O'ZINI qadrsizlantiradi.

Brauzerda tasdiqlandi: **100% tayyor**, kamera «ixtiyoriy» deb turibdi.

## 5. Orfan satr

`nav.switchMarket` — «Bozorni almashtirish» — uchala tilda tarjima
qilingan, glossariy darvozasidan o'tgan, lekin **hech qayerda
chaqirilmagan** edi. Ya'ni bir nechta bozorga a'zo odam, avvalo
platforma admini, boshqa bozorga o'tish uchun tizimdan chiqishi kerak
edi — kunda o'nlab marta.

## 6. TO'LIQ TO'PLAM — bu kunning eng qimmat saboqi

⛔⛔ **«Tizim ishlaydi» deb aytilgandan KEYIN to'liq backend to'plami
yurgizildi va u OLTI nosozlik berdi.**

Ikkitasi o'sha kungi ishdan, **to'rttasi esa oldingi commitlardan** —
ular bir necha kun qizil turgan:

* `PUT /stalls/plan` cross-tenant matritsasiga qo'shilmagan → so'rov
  validatsiyada to'xtardi va marshrutning tenant da'vosi SHU DARVOZA
  tomonidan umuman sinalmay qoldi;
* xarita katagining aniq kalit to'plami (`plan_x`/`plan_y`);
* `/reports/live` hisobot yuzasi reyestriga kiritilmagan (260819);
* `row_prefixes` `PendingMarketResponse` to'plamini buzgan (260819).

Oltinchisi — ko'r audit testi — **kod nuqsoni emas**: `test_billing_api`
yiqilgach uning `reconciliation_cases` tozalashi bajarilmagan va
qoldiq holat qo'shni testni yiqitgan. Tuzatgandan keyin o'z-o'zidan
o'tdi.

⛔ **SABAB REYESTRDA EMAS, ODATDA EDI**: o'sha commitlarda faqat
tegishli fayllar yurgizilgan. Darvozalar ISHLAGAN — ularni hech kim
KO'RMAGAN.

Yakuniy: **2822 o'tdi · 31 tashlab ketildi · 0 nosozlik.**

## 7. Hujjat sinxroni — sinf butunlay yopildi

Bitta savolga («qaysi ish bajarilgan?») **to'rt fayl** javob beradi va
ular qo'lda yangilanadi. `check-requirements-sync.mjs` faqat
bittasining ICHINI ko'rardi.

Topilgan yolg'onlar:

| Fayl | Yolg'on |
|---|---|
| `REQUIREMENTS.md` | `FOUND-01…05` — `Pending`, holbuki Phase 1 2026-07-29 da yopilgan va dalil o'shandan beri bor |
| `REQUIREMENTS.md` | `LAND-05` — ro'yxatda `[x]`, jadvalda `Blocked` (darvoza QIZIL turgan) |
| `ROADMAP.md` | 1-faza «Planned 0/10», 2-faza «Planned 0/17» — ikkalasi ham yopilgan va ular ustiga sakkizta faza qurilgan |
| `ROADMAP.md` | 3-faza «11/11» — o'z belgisi 14/14 derdi; 9 va 10-fazalar jadvalda UMUMAN yo'q |
| `STATE.md` | «Phase 10 · Not started · Ready to execute» — sakkizala reja 2026-08-17 da yopilgan, uch kun eskirgan |

Skriptga uch yangi tekshiruv qo'shildi va **uchalasi ham sabotaj bilan
tasdiqlandi**:

* **(c)** ROADMAP faza ro'yxati ↔ ROADMAP holat jadvali;
* **(d)** YOPILGAN faza ↔ o'sha fazaning talablarida `Pending` YO'Q;
* **(e)** `STATE.md` `completed_phases` ↔ ROADMAP'da yopilgan sanoq.

⛔ **(d) `Pending` ni taqiqlaydi, `Blocked` ni EMAS.** `Blocked` —
«dalil to'liq emas va yetishmayotgani NOMLANGAN» degan ONGLI hukm.
`Pending` esa «hukm umuman yozilmagan».

⚠ **(e) yolg'iz YETARLI emas va bu hujjatda yozildi:** o'sha kuni
`STATE.md` «Not started» deb turgan, lekin sanog'i TASODIFAN to'g'ri
edi (10) — ya'ni bu tekshiruv qizarmasdi.

Sonlar `.planning/phases/*/*-PLAN.md` fayllarini **SANAB** olindi,
qo'lda yozilgan sondan ko'chirilmadi.

## Yakuniy holat

```
Backend:  2822 o'tdi · 31 skip · 0 nosozlik
Frontend: 1283 vitest · 399 darvoza · 0 nosozlik
Hujjat:   54 talab · 11 faza · to'rtala manba MOS
          Done 50 · Pending 0 · Blocked 4
```

## Ochiq qolgani — DALIL YO'QLIGI, KOD BO'SHLIG'I EMAS

| Band | Nima yetishmaydi | Tetigi |
|---|---|---|
| **AI-02** | `.onnx` artefakti YO'Q, oltin to'plamda faqat 8 ta `synthetic://` yozuv. Modelning ANIQLIGI o'lchanmagan — 0% aniq degani emas, UMUMAN o'lchanmagan | Haqiqiy Karmana kadrlari + nazoratchi yorliqlashi + ijara GPU |
| **CAM-02** | CI'da `wg0` yo'q — «faqat tunnel orqali» da'vosi har doim yashil bo'lardi va HECH NIMA isbotlamasdi | VPS deploy'i |
| **FOUND-07** | `RESTIC_REPOSITORY`/`RESTIC_PASSWORD` bo'sh — zaxira o'sha serverning O'ZIDA qoladi | VPS deploy'i |
| **LAND-05** | Lighthouse CI'ga qo'shilmagan | Birinchi deploy |

⚠ **Muhit eslatmasi:** lokal mashinada `127.0.0.1:8080` ni **EDB PEM
Apache**'si (`PEMHTTPD-x64`) egallagan; Docker nginx faqat `[::1]:8080`
da javob beradi. Chrome IPv4 ni tanlaganda Apache'ning 404 sahifasi
chiqadi — dastur emas. Qo'shimcha port ochish yordam bermaydi (Windows
Firewall yangi tinglovchini bloklaydi, 8090/8091 da o'lchandi).
Xizmatni to'xtatish administrator huquqini talab qiladi.

## Keyingi qadam

Subdomen deploy'i. Fayllar joyida: `compose.prod.yml`,
`ops/scripts/first-cert.sh`, `ops/nginx/app.inc`. Kerak bo'lgani —
**domen nomi va server**. Deploy'dan keyin uchta `Blocked` band
yopiladi; to'rtinchisi (AI-02) haqiqiy kadrlarni kutadi.
