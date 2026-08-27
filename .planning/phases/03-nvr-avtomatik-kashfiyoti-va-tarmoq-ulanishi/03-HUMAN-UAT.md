---
status: partial
phase: 03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi
source: [03-VERIFICATION.md, 03-VALIDATION.md]
started: 2026-08-03
updated: 2026-08-03
---

## Bu fazada nima YOPILDI

`02-HUMAN-UAT.md` faqat OCHIQ bandlarni sanaydi. Bu yerda yopilganini ham
nomlash kerak — aks holda keyingi o'quvchi ro'yxatning qisqarganini
tasodif deb o'ylardi.

`03-VERIFICATION.md` fazani **5/8** ga tushirib ikkita bo'shliq qoldirgan
edi va ikkalasi ham **muhandislik nuqsoni** deb tasniflangan, uskuna
yo'qligi emas:

| Bo'shliq | Nima yetishmasdi | Nima bilan yopildi |
|---|---|---|
| **GAP-1** | go2rtc'ga RTSP rekviziti UZATILMASDI (`decrypt_nvr_password` butun ilovada BIR joyda chaqirilardi) va sim'da mos keladigan RTSP nishoni yo'q edi | `03-12` — `nvr-sim:554` da MediaMTX (anonim o'qish RAD ETILADI); `03-13` — `cameras.py::_ensure_stream` da rekvizit oyog'i; `03-14` — o'lchov |
| **GAP-2** | Zanjirning oxirgi bo'g'ini MOCK bilan kesilardi — media hech qachon oqmasdi | **`tests/integration/test_live_view_e2e.py`** — kashfiyot hosil qilgan `stream_name` bilan, jonli ko'rish chiptasidan KEYIN, mahsulot go2rtc'i orqali `/api/frame.jpeg` dan **99 681 baytli HAQIQIY JPEG** olinadi. Mock UMUMAN ishlatilmaydi |

O'lchovning mavjudligi meta-darvoza bilan qulflangan:
`test_phase3_criteria.py::test_the_mockless_end_to_end_measurement_exists_and_runs`
— modul bor, `sim` markeri bor va **birorta testi go2rtc mock'ini
so'ramaydi**. Darvozasiz o'lchov fayl qayta tashkil qilinganda jimgina
yo'qolardi va bo'shliq ikkinchi marta ochilardi.

Natijada **CAM-03** va **CAM-09** `Blocked` -> `Done` ga o'tdi
(`REQUIREMENTS.md`, dalil jadvali bilan). **CAM-02** `Blocked` bo'lib
QOLDI — quyidagi 1- va 2-bandlar aynan shu talabniki.

⚠ **Quyidagi oltita bandning BIRORTASI ham «o'lchandi» deb
ko'rsatilmaydi.** Ular fazani BLOKLAMAYDI (2026-08-01 self-service
direktivasi), lekin ularning natijasi hech qayerda da'vo qilinmagan.

---

## Current Test

[inson tekshiruvini kutmoqda — fazaning muhandislik yetkazmalari
tugallandi va sakkizala mezon yashil; bu bandlar oqimni bloklamaydi]

## Tests

### 1. `ip route get <nvr_ip>` javobi `wg0` ni ko'rsatishi (SC#5 ning 3-da'vosi)

**Nega avtomatlashtirib bo'lmaydi:** CI konteynerida `wg0` interfeysi
UMUMAN yo'q. Bunday test har doim «tunnel uzilgan» shoxidan o'tib yashil
bo'lardi va HECH NIMA isbotlamasdi — bu Pitfall 10 ning aynan o'zi. Faza
buni yashirmaydi: `test_sc5_...` faqat VOSITANING mavjudligini
(`ops/scripts/verify-tunnel.sh` bor, shebangli va bajariladigan)
tekshiradi va qolganini ochiq «QO'LDA» deb belgilaydi.

**Kim bajaradi:** Ops
**Qachon:** VPS deploy'idan keyin, go-live checklist'ining bandi sifatida

expected: `ip route get <nvr_ip>` chiqishida `dev wg0` ko'rinadi; tunnel
o'chirilganda o'sha manzilga ulanish UZILADI (marshrut ommaviy
interfeysga tushib ketmaydi). Vositasi `ops/scripts/verify-tunnel.sh`,
tartibi `ops/docs/nvr-onboarding.md`. Bu **CAM-02** ning yagona
o'lchanmagan jumlasi.
result: [pending]

### 2. CGNAT ostidagi WireGuard tunnelining ko'tarilishi

**Nega avtomatlashtirib bo'lmaydi:** bozor tomonidagi ISP topologiyasini
(CGNAT, NAT o'tish, keepalive xulqi) simulyatsiya qilib bo'lmaydi — u
tarmoq operatorining xulqiga bog'liq va laboratoriyada takrorlanmaydi.

**Kim bajaradi:** Ops
**Qachon:** bozor tomonidagi qurilma o'rnatilganda

expected: mini-PC/router rozetkaga ulangach o'zi VPS peer'ga qo'ng'iroq
qiladi (`PersistentKeepalive = 25`), handshake `wg show` da ko'rinadi va
uzilishdan keyin O'ZI tiklanadi — kirish porti ochilmaydi va SSH tunnel
qadami TALAB QILINMAYDI (D-14; runbookda `ssh` so'zi 0 marta uchraydi).
Havolasi: `ops/wireguard/README.md`. Bu ham **CAM-02** ga tegishli.
result: [pending]

### 3. Real Hikvision firmware'ining XML shakli va kanal raqamlash chetlanishi

**Nega avtomatlashtirib bo'lmaydi:** simulyator **modul** darajasida
ishonchli (fixture'lar real yozib olingan dumplardan, D-04), lekin real
firmware'ning kutilmagan XML shakli yoki kanal raqamlash o'ziga xosligi
faqat qurilmada chiqadi. Sim'ni real qurilmaning NUSXASI deb e'lon qilish
aynan Pitfall 4 — simulyatorning o'zini o'zi tasdiqlashi — bo'lardi.

**Kim bajaradi:** bozor admini (rekvizit beradi) + ijrochi (zondni ishga
tushiradi)
**Qachon:** NVR kirish ma'lumotlari kelgan kun; tartib
`ops/docs/nvr-onboarding.md` §4 da

expected: `ops/scripts/verify-real-nvr.sh <url> <login> <parol>` ning JSON
chiqishi sim fixture'lari bilan bir xil SHAKLDA bo'ladi (model, seriya,
kanallar ro'yxati, `adminAccesses` dagi RTSP porti); `pytest -m hardware`
(5 test) real qurilmaga qaratilganda o'tadi. Chetlanish topilsa u
fixture'ga QO'SHILADI, sim esa unga moslanadi.
result: [pending]

### 4. Bir vaqtdagi RTSP sessiya limitining HAQIQIY qiymati (D-05)

**Nega avtomatlashtirib bo'lmaydi:** chegara firmware va bitreytga
bog'liq. Simulyatorda **ikkala** stsenariy (`reject` / `silent`)
modellashtirilgan va ikkalasi ham test bilan qoplangan, lekin SONNING
O'ZI faqat qurilmada o'lchanadi. ⚠ Sim RTSP oyog'i (MediaMTX) sessiya
limitini UMUMAN modellamaydi va bu `ops/docs/nvr-onboarding.md` da ochiq
yozilgan.

**Kim bajaradi:** Ops
**Qachon:** real NVR ulanganda

expected: `verify-real-nvr.sh` ning `rtsp.concurrent_failed` maydoni
haqiqiy chegarani ko'rsatadi (kutilayotgan diapazon: 6–16 masofaviy
sessiya). Natija `03-RESEARCH.md` D-05 ning taxminini TASDIQLAYDI yoki
RAD ETADI; rad etilsa go2rtc sub-oqimlarga o'tkaziladi va snapshot ISAPI
`/picture` dan olinadi (`test_real_nvr.py::test_three_concurrent_rtsp_sessions`).
result: [pending]

### 5. Jonli tasvirning BRAUZERDAGI ijrosi, sifati va kechikishi

⚠ **BU BAND QAYTA TA'RIFLANDI — farq muhim.**
`03-VERIFICATION.md` uni «⚠ AVVAL GAP-1 yopilishi shart: bugungi kod
bilan tasvir umuman kelmaydi» ogohlantirishi bilan yozgan edi. **GAP-1
endi yopildi va media yo'li SERVER TOMONDA o'lchandi:**
`tests/integration/test_live_view_e2e.py` kadr HAQIQATAN kelishini
tasdiqlaydi (99 681 bayt, birinchi urinishda, 0.26 s).

Qolgan qism shuning uchun ancha TOR va uni aniq aytish kerak:
**«tasvir kelmaydi» EMAS — «tasvir keladi, uning brauzerdagi ijrosi va
idroki o'lchanmagan».**

**Nega avtomatlashtirib bo'lmaydi:** ikki mustaqil sabab. (a) jsdom
`RTCPeerConnection` bermaydi, ya'ni WebRTC/MSE transporti va videoning
O'ZI birorta avtomatik testda IJRO ETILMAYDI; (b) «sifat» va «kechikish
qabul qilinadigan» — perseptual baho: real tarmoq, real kamera, real
ekran va baholovchi odam kerak.

**Kim bajaradi:** direktor (baholovchi) + frontend egasi (yozib boruvchi)
**Qachon:** pilot tayyorgarligi haftasi

expected: direktor panelda kamerani ochadi va tasvirni KO'RADI; transport
badge'i haqiqiy transportni ko'rsatadi (`03-UI-SPEC.md` §8.4); kechikish
va tasvir sifati bozor sharoitida qabul qilinadigan deb baholanadi.
Nosozlik holatida birinchi gumondorlar tartibi `ops/docs/nvr-onboarding.md`
§6 da (UDP 8555 bloklangan -> MSE'ga tushish; NVR bitreyti; `rtsp_port_assumed`).
result: [pending]

### 6. Vendored `video-stream.js` / `video-rtc.js` kodini odam o'qishi

**Nega avtomatlashtirib bo'lmaydi:** uchinchi tomon kodini birinchi
kiritishda odam o'qishi SHART — `eval(`, `new Function`, tashqi `fetch(`,
obfuskatsiya. SHA-256 qulfi faylning **O'ZGARMASLIGINI** kafolatlaydi,
**XAVFSIZLIGINI** emas: qulf birinchi kiritilgan holatni muhrlaydi,
o'sha holat zararli bo'lsa ham.

**Kim bajaradi:** ijrochi
**Qachon:** `03-08` T3 da BAJARILDI; keyingi versiyaga ko'tarilganda
TAKRORLANADI (qulf shuning uchun `frontend/scripts/vendor-integrity.test.mjs`
da yashaydi va ko'tarish uni majburan qizartiradi)

expected: `03-UI-SPEC.md` §14.2 jadvalining har bandi bo'yicha «yo'q»
javobi; topilma bo'lsa vendoring RAD ETILADI va transport HLS'ga
tushiriladi.
result: [pending]

## Summary

total: 6
passed: 0
issues: 0
pending: 6
skipped: 0
blocked: 0

## Gaps

Yo'q — bu bandlar bo'shliq emas, **inson ishtirokini yoki uskunani talab
qiladigan tekshiruvlar**. 2026-08-01 self-service direktivasi bo'yicha
ular fazani yoki jarayonni bloklamaydi.

Bu ro'yxat `03-VALIDATION.md` ning `human_only_verifications` bloki bilan
**bir xil to'plam** (oltita band, tartibi boshqa) va `nyquist_compliant`
hisob-kitobi aynan o'sha blokdan o'qiladi — bu fayl unga kirmaydi,
lekin unga ZID ham bo'lmasligi kerak.

**Diqqat — holatga ta'siri:**

* 1- va 2-bandlar **CAM-02** niki. Ular bajarilmaguncha CAM-02
  `Blocked` bo'lib qoladi va bu **to'g'ri**: soxta yashil test yozish
  yomonroq bo'lardi (Pitfall 10).
* 5-band **CAM-03** ning `Done` holatini BEKOR QILMAYDI — u talab
  matnidagi server tomondagi zanjirni o'lchagan. Lekin agar brauzerdagi
  ijro to'xtash nuqtasini topsa (masalan UDP bloklangan tarmoqda MSE ham
  ishlamasa), CAM-03 `Blocked` ga QAYTARILISHI kerak va sabab shu
  banddan yoziladi.
* 3- va 4-bandlar **CAM-08/CAM-09** ning simulyator ustidagi dalilining
  CHEGARASINI belgilaydi: «real qurilmada ishlaydi» degan da'vo hech
  qayerda berilmagan.
