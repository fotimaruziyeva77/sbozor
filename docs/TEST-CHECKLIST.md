# SBOZOR — Qo'lda test chek-listi (1–7 fazalar)

> **Maqsad:** 8-faza (hisobotlar/backup/go-live) ijrosidan oldin qurilgan tizimni qo'lda sinash.
> **Sana:** 2026-08-14 · **Holat:** 1–7 fazalar qurilgan; 4/5-fazalar «qayta tekshiruv kutilmoqda»
> **Belgilash:** `[ ]` → `[x]` o'tdi · `[!]` muammo (pastdagi jadvalga yozing) · `[-]` o'tkazib yuborildi

---

## 0. Muhit tayyorlash

- [ ] Docker Desktop ishlayapti; `C:` diskda kamida 10–15 GB bo'sh joy bor (91% to'la edi — kerak bo'lsa: sbozor test-imijlarini o'chirish + `docker_data.vhdx` compact)
- [ ] `.env` fayllar joyida (DB parol, Fernet kaliti; bot testlari uchun Telegram tokenlar — ixtiyoriy)
- [ ] Asosiy stek: `npm run up` — db, cache, storage, core-api, worker, scheduler, cv-service, bot-service, go2rtc `--wait` bilan ko'tariladi
- [ ] UI uchun qo'shimcha: `docker compose up -d frontend nginx` (`up` skriptiga kirmaydi!)
- [ ] Migratsiyalar: `npm run migrate` — xatosiz tugaydi
- [ ] Seed ma'lumot: `node scripts/karmana-import.mjs` (kerak bo'lsa)
- [ ] `docker compose ps` — hamma xizmat `healthy`/`running`, **birortasi restart-loop'da EMAS**
- [ ] ⚠ **cv-service tuzog'i:** `CV_MODEL_PATH` ko'rsatgan `.onnx` fayl konteynerda yo'q bo'lsa, taskiq worker har ~1 soniyada qayta ishga tushib ~80% CPU yeydi (7-fazada kuzatilgan). `docker compose logs cv-service | tail` bilan tekshiring
- [ ] Kirish nuqtalari ochiladi:
  - UI (nginx): `http://localhost:8080`
  - API hujjati: `http://127.0.0.1:8000/docs`
- [ ] NVR simulyatori (3–5-bo'limlar uchun): `npm run sim:up`

---

## 1. Auth, rollar va tenant izolyatsiyasi (1-faza)

### Kirish/chiqish
- [ ] Login to'g'ri parol bilan kiradi; noto'g'ri parol aniq xato beradi (tizim ichki tafsilotni oshkor qilmaydi)
- [ ] Logout ishlaydi; qaytib himoyalangan sahifaga kirib bo'lmaydi
- [ ] Sessiya ~15 daqiqadan keyin ham ishlashda davom etadi (refresh-token avtomatik yangilaydi — kutib tekshiring)

### Rollar (har biri bilan alohida kiring)
- [ ] `platform_admin` — bozorlar ro'yxati/yaratish ko'rinadi
- [ ] `market_admin` — o'z bozori boshqaruvi to'liq
- [ ] `director` — ko'rish yuzalari; kassir amallari YO'Q
- [ ] `cashier` (kassir) — faqat to'lov qabul yuzasi
- [ ] `inspector` (nazoratchi) — faqat ko'r audit/tasdiq yuzasi; **hisobot va AI-natija ko'rinmaydi**
- [ ] Ruxsatsiz sahifaga to'g'ridan-to'g'ri URL bilan kirish → rad etiladi (UI redirect, API 403)

### Tenant izolyatsiyasi (RLS) — eng muhim xavfsizlik testi
- [ ] Ikkinchi bozor yarating (B), unga alohida admin qo'shing
- [ ] B-admin bilan kirganda A-bozorning rastalari/to'lovlari/kadrlari **umuman ko'rinmaydi**
- [ ] A-bozor obyekti ID'sini B-sessiyada URL/API'ga qo'lda qo'yib ko'ring → 403/404, ma'lumot sizmaydi
- [ ] Amallar audit jurnalida iz qoldiradi (kim, qachon, nima)

---

## 2. Bozor domeni va usta (2-faza)

- [ ] Usta (wizard) boshidan oxirigacha: yangi bozor → rastalar → tariflar → xodimlar → yakun
- [ ] Ustani yarmida tashlab chiqib, qaytganda holat saqlangan
- [ ] Rasta yaratish/tahrirlash/o'chirish; plan-xarita (canvas) pan/zoom silliq ishlaydi
- [ ] Ko'p rasta bilan (50+) xarita sekinlashmaydi
- [ ] Tarif yaratish: summa **butun so'mda** — kasr/tiyin kiritib bo'lmaydi yoki to'g'ri rad etiladi
- [ ] Xodimlar ommaviy importi (MARKET-07): namunaviy fayl yuklab olinadi, xatoli qator aniq ko'rsatiladi
- [ ] Kategoriyalar CRUD

---

## 3. NVR va kameralar (3-faza)

### Simulyator bilan (`npm run sim:up`)
- [ ] NVR ulash: simulyator manzili + login → **avtokashfiyot** kanallarni o'zi topadi
- [ ] Kanallar ro'yxati to'g'ri; kamera nomlash/rastaga bog'lash ishlaydi
- [ ] Jonli ko'rinish (go2rtc orqali) ochiladi
- [ ] Noto'g'ri login/parol bilan ulanish → aniq, tushunarli xato (timeout emas)

### Real NVR bilan (agar bir tarmoqda bo'lsangiz)
- [ ] NVR soati NTP bilan to'g'rilangan (5 daqiqadan ortiq farq ISAPI digest-auth'ni sindiradi)
- [ ] Real IP + login bilan avtokashfiyot kanallarni topadi
- [ ] Jonli ko'rinish real kameradan keladi
- [ ] Ko'p kanal ulasangiz: Hikvision parallel oqim limiti (6–16) — hammasi birdan ishlamasa, bu kutilgan; sub-stream sinang
- [ ] DB'da RTSP parol ochiq matnda EMAS (ixtiyoriy tekshiruv: `credentials` ustuni shifrlangan blob)
- [ ] ⛔ NVR'ni internetga port-forward QILMANG — faqat LAN/VPN

---

## 4. Snapshot pipeline (4-faza)

- [ ] Slot jadvali bo'yicha kadrlar kela boshlaydi (simulyator yoki real kamera)
- [ ] Snapshot ro'yxati UI'da ko'rinadi: bozor/sana/kamera/slot tartibida
- [ ] `capture_runs`da har slot uchun yozuv bor — muvaffaqiyat ham, **yo'qlik ham** yoziladi
- [ ] Kamerani ataylab o'chirib qo'ying → o'tkazib yuborilgan slot haqida ogohlantirish/alert paydo bo'ladi
- [ ] `docker compose restart scheduler worker` → jadval davom etadi, slot izsiz yo'qolmaydi
- [ ] Kun chegarasi: Asia/Tashkent bo'yicha 00:00 atrofidagi kadr **to'g'ri kunga** tushadi

---

## 5. Zonalar, CV va nazoratchi (5-faza)

- [ ] Kamera kadri ustida polygon zona chizish: nuqta qo'shish/surish/o'chirish, rastaga bog'lash
- [ ] Zonani saqlab qayta ochganda geometriya aynan saqlangan
- [ ] CV band/bo'sh xulosasi keladi (bazaviy model — aniqlik o'rtacha bo'lishi NORMAL, fine-tune 2-oy rejasi)
- [ ] Dalil-rasm (belgilangan/annotated kadr) ochiladi va zonalar to'g'ri chizilgan
- [ ] Nazoratchi ko'r auditi: nazoratchi AI xulosasini **ko'rmasdan** band/bo'sh deb belgilaydi
- [ ] O'lchanmagan ko'rsatkich chizilmaydi: ma'lumot yo'q joyda 0% yoki yolg'on raqam emas, aniq bo'sh holat
- [ ] Dalil-kadrga faqat ruxsatli rollar kira oladi (kassir kira olmasligi kerak)

---

## 6. Billing va kassir (6-faza)

- [ ] Band rasta uchun kunlik patta hisobi (`daily_charges`) avtomatik paydo bo'ladi
- [ ] **Kassir oqimi ≤3 bosish:** rasta tanlash → summa → tasdiq. Bosishlarni sanang!
- [ ] To'lov darhol ro'yxatda ko'rinadi (optimistik yozuv), toast/tasdiq chiqadi
- [ ] Telefonda (yoki brauzer mobil rejimida) kassir oqimi qulay — tugmalar barmoq o'lchamida
- [ ] Pul hamma joyda butun so'm, minglik ajratgichlar to'g'ri, hech qayerda `1234.56` ko'rinmaydi
- [ ] Qarz/balans to'g'ri hisoblanadi (bir necha kun + qisman to'lov stsenariysi)
- [ ] Yopilgan smena/to'lov o'zgartirib bo'lmaydi (immutability) — tahrir urinishlari rad etiladi
- [ ] Ikkita tabda parallel to'lov kiritib ko'ring — dublikat yaratilmaydi

---

## 7. Nomuvofiqlik va botlar (7-faza)

### Nomuvofiqlik
- [ ] Stsenariy yarating: zona **band** (CV/nazoratchi tasdiqlagan) + to'lov **yo'q** → nomuvofiqlik holati (case) ochiladi
- [ ] Case ro'yxati filtrlar bilan ishlaydi; detail oynasida dalil-rasm + hisob-kitob bor
- [ ] To'lov kiritilgach case holati to'g'ri o'zgaradi
- [ ] Hit-rate kartasi: ma'lumot yetarli bo'lmaganda bo'sh holat (0% emas)

### Bildirishnomalar
- [ ] Bildirishnoma yetkazish ro'yxati (delivery-list) yozuvlarni ko'rsatadi
- [ ] Yetkazilmagan bildirishnoma qayta urinish holatini ko'rsatadi

### Telegram botlar (token bo'lsa)
- [ ] Sotuvchi bot: telefon raqam orqali ro'yxatdan o'tish (+998 formatga normallashadi)
- [ ] Sotuvchi bot: o'z qarzi/to'lovlarini so'rab oladi
- [ ] Direktor bot: kunlik xulosa keladi
- [ ] ⚠ MA'LUM KAMCHILIK: botga ixtiyoriy/tushunarsiz matn yozsangiz javobsiz qolishi mumkin — bu 8-fazada tuzatiladi (08-11), bug deb yozmang

---

## 8. Kesma tekshiruvlar (hamma faza)

### Uch til
- [ ] uz-Latn ↔ uz-Cyrl ↔ ru almashtirish har sahifada ishlaydi va tanlov saqlanadi
- [ ] Har asosiy sahifada 3 tilda ham: tarjima qilinmagan kalit (`missing.key` ko'rinishi) YO'Q
- [ ] Sana/raqam formatlari har tilda to'g'ri
- [ ] Kirill va lotin o'zbekcha matnlar mazmunan bir xil (drift yo'q — tasodifiy 5 sahifani solishtiring)

### Barqarorlik
- [ ] `docker compose restart core-api` → UI bir necha soniyada tiklanadi, sessiya saqlanadi
- [ ] `storage`ni to'xtatib snapshot oqimini kuzating → aniq xato/alert, tizim qulamaydi; qayta yoqilgach o'zi tiklanadi
- [ ] Sekin tarmoqni simulyatsiya qiling (brauzer DevTools → Slow 3G) — kassir oqimi hali ham ishlatsa bo'ladi

### Avtomatik testlar (ixtiyoriy, vaqt bo'lsa)
- [ ] `npm run test:fast` — yashil (~2–3 daq)
- [ ] `npm run test:tenancy` — yashil (RLS izolyatsiya to'plami)
- [ ] To'liq: `npm run test` (~25–40 daq, tinch xostda)

---

## 9. MA'LUM kamchiliklar — bug deb yozmang (8-faza kutadi)

| Yo'q narsa | Qayerda tuzatiladi |
|---|---|
| Direktor hisobot sahifalari (tushum/qarzdorlik/nomuvofiqlik arxivi) va `.xlsx` yuklab olish | 08-07…08-13 |
| AI aniqlik hisoboti sahifasi | 08-15 |
| Avtomatik backup + tiklash | 08-05, 08-08 |
| 3 tomonlama solishtiruv (daftar vs tizim vs AI) | 08-14, 08-16, 08-18 |
| Bot fallback javobi (istalgan matnga javob) | 08-11 |
| Mayda WR-* / IN-* tuzatishlar ro'yxati | `.planning/phases/07-*/deferred-items.md` |

---

## 10. Natijalarni qayd etish

Har `[!]` uchun quyidagi jadvalga yozing (skrinshot bilan bo'lsa — zo'r):

| № | Bo'lim/band | Qadamlar | Kutilgan | Kuzatilgan | Jiddiylik (blocker/muhim/mayda) |
|---|---|---|---|---|---|
| 1 | | | | | |
| 2 | | | | | |

> Limit tiklangach shu jadvalni Claude'ga bering: mayda'lar `/gsd:quick`, murakkablar `/gsd:debug` bilan yopiladi. 4/5-faza bandlaridagi muammolar ularning qayta tekshiruviga kiradi.
