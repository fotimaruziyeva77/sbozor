---
status: partial
phase: 05-kamera-zonalari-cv-va-nazoratchi-tasdig-i
source: [05-VALIDATION.md, 05-RESEARCH.md, 05-UI-SPEC.md, 05-CONTEXT.md]
started: 2026-08-10
updated: 2026-08-10
---

## Bu fazada nima O'LCHANDI va nima O'LCHANMADI

`04-HUMAN-UAT.md` ning qoidasi shu yerda ham amal qiladi: ro'yxat faqat
ochiq bandlarni sanaydi, lekin YOPILGANINI ham nomlash kerak — aks holda
keyingi o'quvchi ro'yxatning qisqaligini «hammasi ishlayapti» deb
o'qirdi.

Fazaning beshala mezoni `tests/integration/test_phase5_criteria.py` da
**bitta buyruq** bilan o'lchanadi va uchala darvozasi (mezon boshiga
bitta test · meta-test · soxtalashtirishsiz o'lchov) yashil. Baza —
HAQIQIY `postgres:18.4`, marshrutlar — HAQIQIY FastAPI grafi, detektor
arifmetikasi esa `cv-tests` konteynerida HAQIQIY `supervision` bilan.

⛔⛔ **LEKIN BU FAZADA ENG MUHIM SAVOLGA JAVOB YO'Q VA U SHU YERDA
BIRINCHI TURADI: «DETEKTOR TO'G'RI JAVOB BERADIMI?»**

Bu kamchilik emas — **HAQIQAT YO'Q**. Oltin to'plam
(`tests/fixtures/golden_set/`) bo'sh, real Karmana kadri hali olinmagan.
Butun to'plam **mexanikani** isbotlaydi: zona geometriyasi saqlanadi va
versiyalanadi, hodisa tahrirlanmaydi, navbat byudjet va ustuvorlik
bilan ishlaydi, ko'r audit tizim javobini bermaydi, agregatsiya
qoidasi bajariladi, kun yopiladi. **MODEL esa umuman o'lchanmagan.**

⚠ Shuning uchun bu fazaning hech qayerida — na SUMMARY larda, na
`05-VALIDATION.md` da, na mezon modulida — detektorning aniqligi
haqida **birorta raqam yozilmagan**. Buni mexanik ravishda qo'riqlaydigan
darvoza ham bor:
`test_phase5_criteria.py::test_the_criteria_module_claims_no_accuracy_number`.

⚠ Bu ro'yxat `05-VALIDATION.md` ning **Manual-Only Verifications**
jadvali bilan **bir xil to'plam emas**: u yerda beshta band bor (ular
`nyquist_compliant` hisob-kitobiga kiradi), bu yerda esa sakkiztasi —
uchtasi (#3 ONNX artefakti, #7 D-05 chiqish yo'li, #8 O-01 atama ko'rigi)
**qo'shimcha operatsion bandlar** va ular hisob-kitobga KIRMAYDI. Ikkala
ro'yxat bir-biriga ZID bo'lmasligi shart va ular birga o'qiladi.

---

## Current Test

[inson tekshiruvini kutmoqda — fazaning muhandislik yetkazmalari
tugallandi va beshala mezon yashil; bu bandlar oqimni bloklamaydi]

## Tests

### 1. DETEKTORNING ANIQLIGI — verdikt qanchalik to'g'ri

**Nega avtomatlashtirib bo'lmaydi:** o'lchov HAQIQATGA qarshi bo'ladi va
haqiqat — bu real Karmana kadrida odam qo'ygan yorliq. Sintetik
`sv.Detections` (W0-7) **geometrik fakt** bo'yicha yasaladi va
kutilayotgan verdiktni UMUMAN bilmaydi (`box_center_in_polygon`) — ya'ni
u zona mantig'ini isbotlaydi, **modelni emas**. Modelni sintetik kadr
bilan o'lchash 2-fazaning o'zini o'zi tasdiqlovchi shabloni va
3-fazaning «simulyatordan kadr olib tekshiramiz» taklifi bilan **aynan
bir xil xato** bo'lardi; loyiha ikkalasini ham rad etgan.

**Egasi:** nazoratchi (yorliqlaydi) + ijrochi (o'lchaydi)
**Tetigi:** Phase 0 ning real kadrlari kelganda — kamida 06:00 va 18:00
slotlari (IR va past yorug'lik holatlari aynan o'sha yerda)

**Nima QURILGAN va u UXLAB YOTADI:** `tests/fixtures/golden_set/` +
`manifest.jsonl` sxemasi + `scripts/eval-golden-set.py` + `golden`
pytest markeri (W0-9, W0-10). Darvoza `source='karmana'` qatorlari
paydo bo'lgan kuni **kodsiz o'zi uyg'onadi**.

expected: `manifest.jsonl` ga kamida 200 ta yorliqlangan zona-kadr
juftligi tushadi (`source='karmana'`); `pytest -m golden` ishga tushadi
va chalkashlik matritsasini beradi. Natija **ikki yo'nalishda ajratiladi**
(RECON-05 ning matni): «band deb xato» = nizo xavfi, «bo'sh deb xato» =
yo'qotish. ⛔ Ular BITTA «aniqlik» foiziga yig'ilmaydi.
result: [pending]

### 2. COCO sinflari O'ZBEK BOZORI MOLLARIDA ishlaydimi

**Nega avtomatlashtirib bo'lmaydi:** RF-DETR COCO ustida o'qitilgan va
uning sinflari (`person`, `handbag`, `bottle`, `bowl`, …) o'zbek
bozorining mollarini — qop-qop un, gilam, ko'rpa, quritilgan meva
tepasi, bo'z mato — **qamramasligi mumkin**. Bu fazaning eng katta
qoldiq xavfi va u hamma joyda LOW confidence bo'lib chiqishi mumkin.
Sintetik detektsiya bu savolni **umuman bermaydi**: u sinf nomini
tanlab beradi.

**Egasi:** nazoratchi
**Tetigi:** birinchi real kadrlar to'plami

expected: 30 ta real kadrdagi band rastalarning kamida yarmida
detektorda `confidence >= 0.60` bo'lgan kamida bitta quti chiqadi.
Chiqmasa — yechim MA'LUMOT va SOZLAMA, qayta loyihalash emas:
(a) `occupancy_events.model_version` ustuni ikkinchi modelning
raqobatlashuvchi verdiktini yozishga imkon beradi (`UNIQUE(market_id,
snapshot_id, camera_zone_id, model_version)` — kalitning bir qismi);
(b) `timm` per-zone-crop binar klassifikatori (CLAUDE.md stek jadvali)
kam ma'lumotda ham o'qiydi va u ikkinchi bosqich bo'lib qo'shiladi.
result: [pending]

### 3. ONNX artefaktini eksport qilish va `ops/models/` ga qo'yish

**Nega avtomatlashtirib bo'lmaydi:** artefakt CI'da YO'Q va bo'lmaydi
ham. `rfdetr` paketi `torch` ni **majburiy bog'liqlik** sifatida tortadi
(~800 MB) va u ishlab chiqarish image'iga UMUMAN kirmasligi kerak
(CLAUDE.md ning qat'iy bandi). Eksport **ijara GPU'da**, alohida
`cv-train` image'ida bajariladi; natija — bitta `.onnx` fayl va u
image'ga `COPY` bilan olib kiriladi (**D-24**: yuklab OLINMAYDI —
build vaqtida tarmoqqa chiqish qayta ishlab chiqarilmaydigan build
demakdir).

**Egasi:** Ops
**Tetigi:** GPU ijarasi (2-oyning fine-tuning oynasi)

expected: `ops/models/rfdetr-<variant>-<version>.onnx` mavjud;
`docker compose --profile test run --rm cv-tests pytest -m model -q`
yashil (bugun bu bandlar CI'da **umuman chaqirilmaydi**);
`onnxruntime` sessiyasi `CPUExecutionProvider` bilan ochiladi va bitta
kadrdagi kechikish **Contabo AMD EPYC'da o'lchanadi** — ⛔ tadqiqotdagi
Intel raqamlari (74 ms / 180 ms) **da'vo sifatida ishlatilmaydi**.
⚠ Litsenziya darvozasi (`test_license_fence.py`) `rfdetr-plus` ni
lockfile invarianti sifatida taqiqlaydi — XLarge/2XLarge eksport
qilinmaydi.
result: [pending]

### 4. Ko'r auditning AMALIY xolisligi

**Nega avtomatlashtirib bo'lmaydi:** strukturaviy himoyalarning beshtasi
ham testlangan — hosila urug' (namunani qayta chizib bo'lmaydi),
payloadda tizim javobining **umuman yo'qligi** (maydon e'lon
qilinmaydi), `CHECK` konstraytlari, javobning o'zgarmasligi va 70/30
kvotasi tortish paytida. **Nazoratchining haqiqatan langarlanmaganini**
esa faqat real ish jarayoni ko'rsatadi: odam kadrni ko'rib, o'zining
oldingi javoblarini eslab yoki rastani tanib turib ham langarlanishi
mumkin va buni birorta test o'lchay olmaydi.

**Egasi:** nazoratchi + direktor
**Tetigi:** pilot tayyorgarligi haftasi

expected: bir hafta davomida ko'r audit natijalari `matched` ulushi
bo'yicha **barqaror** (kunlar orasida keskin sakramaydi); nazoratchi
so'rovda «qaysi javobni tizim bergani bilinmaydi» deydi;
`decision_ms` taqsimotida **2 soniyadan tez** javoblar ulushi 10 % dan
past. ⛔ «Tez qaror» nazoratchiga KO'RSATILMAYDI (§7.5) — ko'rsatilsa u
o'lchovni chetlab o'tishni o'rganardi.
result: [pending]

### 5. Poligon chizishning amalda bajariladiganligi (300–1000 rasta)

**Nega avtomatlashtirib bo'lmaydi:** UI-SPEC uch yordamchi (nusxalash,
klaviatura bilan siljitish, avtomatik keyingi rastaga o'tish) bilan
2–5 soatni 0,5–1 soatga tushirishni **hisoblab** chiqdi. Haqiqiy vaqt
faqat real bozor chizmasida, real kadrda va real admin bilan
o'lchanadi.

**Egasi:** bozor admini
**Tetigi:** Karmana chizmasi kelganda

expected: bitta kameradagi ~20 zona **30 daqiqadan kam** vaqtda
chiziladi; `GET /camera-zones/coverage` qamrovsiz rastalar sonini
ko'rsatadi va admin uni nolga tushira oladi; zona chegarasi
(`ZONE_MAX_PER_CAMERA = 60`) real kamerada **yetarli** bo'lib chiqadi.
Yetmasa — yechim SOZLAMA (chegarani ko'tarish), qayta loyihalash emas.
result: [pending]

### 6. Nazoratchining kunlik 30 bandlik byudjeti realmi

**Nega avtomatlashtirib bo'lmaydi:** charchash va tezlik — inson
o'lchovi. Byudjet SOZLAMA
(`Settings.review_uncertain_daily_budget = 50`,
`review_blind_daily_budget = 30`) va uning MEXANIZMI o'lchangan (409
`review_budget_exhausted`, «navbat bo'sh» dan ajratilgan kod bilan).
O'lchanmagani — **qiymatning o'zi**.

**Egasi:** nazoratchi
**Tetigi:** pilotning birinchi haftasi

expected: nazoratchi kunlik 30 ta ko'r audit bandini **charchamasdan**
bajaradi va `decision_ms` medianasi kun oxirida boshiga nisbatan
**2 barobardan ko'p oshmaydi**. Oshsa — byudjet `.env` orqali
tushiriladi; ⛔ «hammasini tasdiqlash» tugmasi HECH QACHON
qo'shilmaydi (SC#3 darvozasi uni OpenAPI sxemasi darajasida
qulflaydi).
result: [pending]

### 7. D-05 chiqish yo'li: 60 poligonli kamerada `pointermove` > 16 ms mi

**Nega avtomatlashtirib bo'lmaydi:** `jsdom` da **layout ham, real
raster ham yo'q** — u `requestAnimationFrame` va `pointermove` ni
o'lchay olmaydi. Geometriya sof funksiyalarga ajratilgan
(`lib/zone-geometry.ts`, W0-8) va aynan shu ajratish D-05 ning chiqish
yo'lini arzon qiladi: render qatlami SVG'dan `react-konva` ga
almashsa, geometriya **tegilmaydi**.

**Egasi:** ijrochi
**Tetigi:** real bozor chizmasi (yoki 60 zonali sintetik chizma) real
brauzerda

expected: Chrome DevTools Performance profilida sudrash paytidagi
`pointermove` ishlov berish vaqti **16 ms dan past** (60 fps). Oshsa —
D-05 ning chiqish yo'li ochiladi: `konva` + `react-konva` o'rnatiladi
(**M-11**: bugun ular o'rnatilmagan va SVG muharriri **0 ta yangi
paket** talab qilgan) va faqat render qatlami almashadi.
result: [pending]

### 8. «Ko'rmasdan tekshirish» atamasining ONA TILIDA ko'rigi (O-01)

**Nega avtomatlashtirib bo'lmaydi:** `blind_audit` ni «ko'r audit» emas,
**«ko'rmasdan tekshirish»** deb atash qarori (§12.1) — TIL qarori:
«ko'r audit» kalka va jargon, nazoratchi uchun nomning o'zi ko'rsatma
bo'lishi kerak. Atamaning **tabiiy eshitilishini** faqat ona tilida
so'zlashuvchi baholaydi; darvoza (G-11, G-16) faqat taqiqlangan
so'zlarning YO'QLIGINI o'lchaydi, tanlangan so'zning YAXSHILIGINI emas.

**Egasi:** bozor admini (ona tilida so'zlashuvchi) + direktor
**Tetigi:** 8-fazadagi uch tilli yakuniy tekshiruv

expected: uchala tilda (`uz-Latn`, `uz-Cyrl`, `ru`) atama tushunarli;
nazoratchi «bu nima?» deb so'ramaydi. O'zgartirilsa — **faqat copy**
o'zgaradi: kod atamasi (`blind_audit`, `queue_kind`) **tegilmaydi**
(4-fazadagi `slot_time` → «vaqt» qarorining aynan takrori).
result: [pending]

## Summary

total: 8
passed: 0
issues: 0
pending: 8
skipped: 0
blocked: 0

## Gaps

Yo'q — bu bandlar bo'shliq emas, **inson ishtirokini, real uskunani,
real ma'lumotni yoki real brauzerni talab qiladigan tekshiruvlar**.
2026-08-01 self-service direktivasi bo'yicha ular fazani yoki jarayonni
bloklamaydi.

**Diqqat — talab holatlariga ta'siri:**

* **1- va 2-bandlar AI-02 va AI-04 ning chegarasini belgilaydi.**
  AI-02 ning matni ikki jumla: «detektor har zonani band/bo'sh/noaniq
  deb baholaydi» va «AI natijasi confidence bilan saqlanadi va hech
  qachon o'zgartirilmaydi». **Ikkinchi jumla to'liq o'lchangan**
  (`test_occupancy_immutable.py`, `test_phase5_criteria.py::test_sc2_…`).
  **Birinchi jumla esa YARIM o'lchangan**: baholash yo'li uchidan-uchiga
  qurilgan va sintetik detektsiyalar bilan sinalgan, LEKIN
  baholashning TO'G'RILIGI o'lchanmagan. Shuning uchun AI-02 holati —
  **`Blocked`**, `Done` emas, va sabab REQUIREMENTS jadvalida yozilgan.

* **1-band RECON-05 (8-faza) ning ham sharti.** «AI aniqlik hisoboti:
  ko'r audit namunasidan, xatolik turlari ajratilgan» — hisobotning
  MASHINASI qurilgan (`accuracy_report.py`, `GET /occupancy/accuracy`,
  Y-4 ekrani), ichidagi RAQAM esa real yorliqsiz tug'ilmaydi.

* **4-band AI-04 ning `Done` holatini BEKOR QILMAYDI** — talab matni
  «nazoratchi AI javobini ko'rmasdan tasodifiy tanlangan zonalarni
  baholaydi; aniqlik hisoboti faqat shu namunadan olinadi» deydi va
  **aynan shu o'lchangan** (payloadda tizim javobi yo'q; hisobot
  `purpose='eval'` + `queue_kind='blind_audit'` dan tashqarisini
  sanamaydi — sabotaj bilan qizartirildi). O'lchanmagani —
  **odamning** langarlanishi, va bu talab matnida YO'Q.

* **5- va 6-bandlar AI-01 va AI-03 ning ERGONOMIKA chegarasi:**
  mexanizm o'lchangan, TEZLIK va CHIDAMLILIK esa yo'q.

* **3-band bu fazaning yetkazmasi EMAS** — u ops ishi va u yerda
  faqat ro'yxat to'liq bo'lishi uchun turadi. ⚠ Lekin u **AI-02 ning
  ishlab chiqarishdagi** sharti: artefaktsiz `cv-service` haqiqiy kadr
  ustida ishlay olmaydi.

* **7- va 8-bandlar birorta talabning matnida YO'Q** — ular
  ijro sifati (D-05 chiqish yo'li) va til sifati (O-01) bandlari.
