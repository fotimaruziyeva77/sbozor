---
status: partial
phase: 04-snapshot-pipeline
source: [04-VALIDATION.md, 04-RESEARCH.md, ops/docs/monitoring.md]
started: 2026-08-05
updated: 2026-08-05
---

## Bu fazada nima O'LCHANDI va nima O'LCHANMADI

`03-HUMAN-UAT.md` ning qoidasi shu yerda ham amal qiladi: ro'yxat faqat
ochiq bandlarni sanaydi, lekin YOPILGANINI ham nomlash kerak — aks holda
keyingi o'quvchi ro'yxatning qisqaligini «hammasi ishlayapti» deb
o'qirdi.

Fazaning beshala mezoni `tests/integration/test_phase4_criteria.py` da
**bitta buyruq** bilan o'lchanadi va uchala darvozasi (mezon boshiga
bitta test · meta-test · mock'siz o'lchov) yashil. Ombor — HAQIQIY
SeaweedFS konteyneri, NVR — HAQIQIY `nvr-sim` konteyneri (Digest auth
bilan), baza — HAQIQIY Postgres.

⛔ **LEKIN HAMMASI SIMULYATOR USTIDA O'LCHANGAN.** Quyidagi oltita band
real uskuna, real vaqt yoki real odam talab qiladi. Ularning
BIRORTASI ham «o'lchandi» deb ko'rsatilmaydi va ularning natijasi hech
qayerda da'vo qilinmagan. Ular fazani **bloklamaydi** (2026-08-01
self-service direktivasi), lekin «real bozorda ishlaydi» degan da'vo
BERILMAGAN.

⚠ Bu ro'yxat `04-VALIDATION.md` ning `human_only_verifications` bloki
bilan **bir xil to'plam** (oltita band, tartibi bir xil) va
`nyquist_compliant` hisob-kitobi aynan o'sha blokdan o'qiladi — bu fayl
unga kirmaydi, lekin unga ZID ham bo'lmasligi kerak.

---

## Current Test

[inson tekshiruvini kutmoqda — fazaning muhandislik yetkazmalari
tugallandi va beshala mezon yashil; bu bandlar oqimni bloklamaydi]

## Tests

### 1. Sifat chegaralarini REAL Karmana kadrida sozlash

**Nega avtomatlashtirib bo'lmaydi:** chegaralar (`QUALITY_DARK_MEAN`,
`QUALITY_BLANK_STDDEV`, `QUALITY_IR_SATURATION`, `QUALITY_NIGHT_MEAN`)
hozir **LOW confidence** — real Karmana kadri hali yo'q. Sintetik JPEG
generatori (`tests/fixtures/frames.py`) MEXANIZMNI isbotlaydi,
**QIYMATNI emas**: u fizik xususiyat bo'yicha kadr yasaydi
(`mean`/`stddev`/to'yinganlik) va chegaralarni UMUMAN bilmaydi. Chegara
bilan nomlangan fixture testni o'z farazining aks-sadosiga aylantirardi.

**Egasi:** nazoratchi (baholaydi) + ijrochi (SQL yozadi)
**Tetigi:** Phase 0 ning real kadrlari kelganda (06:00 va 18:00 slotlari
majburiy — IR va past yorug'lik holatlari aynan o'sha yerda)

expected: kamida 30 ta real kadr `snapshots` ga tushadi; D-15 bo'yicha
o'lchovlar (`quality_mean`, `quality_stddev`, `quality_saturation`)
qatorda SAQLANADI, ya'ni sozlash **SQL bilan** bo'ladi — qayta kadr
olish TALAB QILINMAYDI. `percentile_cont` bilan taqsimot chiqariladi va
`.env` dagi to'rt chegara yangilanadi; `quality_thresholds_version`
oshiriladi. Eski qatorlar QAYTA HISOBLANMAYDI — versiya ustuni aynan
shuning uchun bor.
result: [pending]

### 2. 90 kunlik saqlash siyosatining KALENDAR bo'yicha ishlashi

**Nega avtomatlashtirib bo'lmaydi:** **vaqtni kutib bo'lmaydi.**
`tests/integration/test_retention.py` va `test_phase4_criteria.py::
test_sc4_...` chegarani SOZLAMA (`full_days=0`) va vaqtni ARGUMENT
(`today=`) qilib mexanizmni isbotlaydi — siqish, o'lcham saqlanishi,
kalitning o'zgarmasligi, qatorning qolishi. Siyosatning 90 HAQIQIY kun
davomida ishlab turishini esa faqat kalendar tasdiqlaydi: `retention`
job'i har kecha ishga tushishi, `full` -> `compressed` o'tishi va disk
o'sish egri chizig'i vaqt bilan chiqadi.

**Egasi:** Ops
**Tetigi:** go-live + 90 kun (birinchi `full` -> `compressed` to'lqini);
+455 kun (birinchi `purged`)

expected: 91-kuni `SELECT storage_tier, count(*) FROM snapshots GROUP BY 1`
`compressed` qatorini ko'rsatadi; `system_heartbeats` da `retention`
komponenti 26 soatdan yangi; disk foizi `alert_sweep` ning 85 % chegarasi
ostida qoladi. Nosozlikda `backup_stale` emas, `retention` yurak
urishining eskirishi signal beradi (`ops/docs/monitoring.md` §1).
result: [pending]

### 3. Tiklash mashqi (restore drill)

**Nega avtomatlashtirib bo'lmaydi:** zaxirani tiklash REAL ombor, REAL
ma'lumot va TOZA server talab qiladi. «Zaxira olindi» bilan «zaxiradan
tiklandi» ikki boshqa da'vo va ikkinchisini faqat bajarish isbotlaydi.
⚠ Bu band 4-fazaning yetkazmasi EMAS — u FOUND-07 (8-faza) niki va bu
yerda faqat NOMLANADI: 4-faza `backup_stale` alertini qurdi, ya'ni
zaxiraning YO'QLIGI endi ko'rinadi, lekin zaxiraning ISHLASHI hali
o'lchanmagan.

**Egasi:** Ops
**Tetigi:** go-live'dan oldin, 8-fazada (FOUND-07)

expected: `restic check --read-data-subset=5%` yashil; `pg_dump -Fc`
dan tiklangan bazada oxirgi kunning `capture_runs` va `snapshots`
qatorlari to'liq; obyekt-ombordan tiklangan kadr `Image.open` bilan
ochiladi. Natija hujjatlashtiriladi (sana, davomiylik, topilmalar).
result: [pending]

### 4. Telegram alertining HAQIQATAN yetib borishi

**Nega avtomatlashtirib bo'lmaydi:** bot tokeni, chat ID va tarmoq CI'da
YO'Q. `tests/integration/test_alerting.py` va `test_phase4_criteria.py::
test_sc5_...` HTTP KONTRAKTINI o'lchaydi (`respx`): nechta so'rov ketdi,
qaysi yo'lga (`/sendMessage`), tanasida nima bor va nima YO'Q (rasm,
havola, obyekt kaliti). Haqiqiy Bot API ga borish testni tashqi xizmatga
va HAQIQIY TOKENGA bog'lardi — soxta yashil test esa «alert ishlayapti»
degan yolg'on ishonch berardi, bu Pitfall 10 ning aynan o'zi.

**Egasi:** Ops
**Tetigi:** bot sozlanganda (`.env` ga `TELEGRAM_BOT_TOKEN` va
`TELEGRAM_CHAT_ID` yozilgan kun)

**Qadamlar** (to'liq tartib `ops/docs/monitoring.md` §4 da):

| # | Qadam | Kutilgan natija |
|---|-------|-----------------|
| 1 | [@BotFather](https://t.me/BotFather) ga `/newbot` → token oling | `1234567890:AA...` |
| 2 | Ops guruhini yarating, botni **admin** qilib qo'shing, guruhga bitta xabar yozing | — |
| 3 | `https://api.telegram.org/bot<TOKEN>/getUpdates` → `"chat":{"id":-100...}` | Guruh ID **manfiy** |
| 4 | Serverdagi `.env` ga: `TELEGRAM_BOT_TOKEN=...`, `TELEGRAM_CHAT_ID=-100...` ⚠ repozitoriyga commit QILMANG | — |
| 5 | `docker compose up -d --build worker scheduler` | — |
| 6 | `docker compose logs worker --tail 20 \| grep -E "worker_started\|alerts_disabled"` | `worker_started ... alerts=True sentry=<bool>` |
| 7 | Keyingi **20:00** dagi dayjestni kuting | Guruhga BITTA xabar keladi |

expected: 6-qadamda `alerts=True` (agar `alerts_disabled` chiqsa token
yoki chat ID yo'q — tizim ishlashda davom etadi, lekin xabar KELMAYDI va
bu ATAYIN jurnalga yoziladi); 7-qadamda xabar keladi va uning ichida
**rasm ham, `http` havolasi ham, `.jpg` kaliti ham YO'Q** (D-19). UI'da
`notified_at` `NULL` bo'lgan alert «Telegram xabari yuborilmadi» deb
ko'rsatiladi — ya'ni yetkazilmaganlik JIM qolmaydi.

⚠ Bu band **FOUND-06** ning `Done` bo'lishi shartiga bevosita kiradi
(`04-12` Task 3): CI'da yetkazilish isbotlanmaydi va bu ochiq aytiladi.
result: [pending]

### 5. Tashqi dead-man's switch (D-21) — `/internal/self-check` ni tashqaridan so'rash

**Nega avtomatlashtirib bo'lmaydi:** ikki mustaqil sabab. (a) v1 da bu
qatlam uchun **kod yozilmaydi** — u bitta URL sozlash, ya'ni ops ishi;
uni kodga aylantirish yangi bog'liqlik va yangi nosozlik nuqtasi
qo'shardi. (b) O'lchanadigan hodisa — **VPS butunlay o'lishi**, ya'ni
ichkaridagi HECH BIR kod alert yubora olmaydigan holat. Bu kamchilik
emas, fizika: alert yuborish uchun ishlayotgan jarayon kerak.

**Egasi:** Ops
**Tetigi:** VPS deploy'idan keyin, domen va TLS ishlagan kun

**Qadamlar** (to'liq tartib `ops/docs/monitoring.md` §5 da):

| # | Qadam (healthchecks.io) | Qiymat |
|---|-------------------------|--------|
| 1 | Hisob oching → **Add Check** | nomi `sbozor-self-check` |
| 2 | **Schedule** | `Period: 10 minutes`, `Grace: 10 minutes` |
| 3 | Turi | «Check is up if URL returns 2xx» (HTTP check) |
| 4 | URL | `https://<domen>/internal/self-check` |
| 5 | **Notification** | Telegram yoki email kanali |

expected: monitor 200 oladi va yashil turadi; `worker` konteyneri
ataylab to'xtatilganda (`docker compose stop worker`) endpoint 26 soat
ichida **503** va `{"ok": false, "stale": ["capture_tick"]}` beradi,
tashqi monitor esa xabar yuboradi. ⚠ Bu endpoint konteyner
`healthcheck` iga ULANMAYDI va ulanmasligi ham test bilan qulflangan
(`test_self_check_is_not_wired_into_the_container_healthcheck`) —
worker'ning yurak urishi eskirgani uchun sog'lom `core-api` ni qayta
ishga tushirish sababni YASHIRARDI.

⚠ Bu band ham **FOUND-06** ning shartida (`04-12` Task 3).
result: [pending]

### 6. Real NVR'da bir vaqtdagi sessiya chegarasining kadr olishga ta'siri

**Nega avtomatlashtirib bo'lmaydi:** simulyator RTSP sessiya limitini
UMUMAN modellamaydi va bu 3-faza tekshiruvida ochiq yozilgan
(`03-HUMAN-UAT.md` #4). Chegara firmware va bitreytga bog'liq
(kutilayotgan diapazon 6–16 masofaviy sessiya) va SONNING O'ZI faqat
qurilmada o'lchanadi. Sim'ni real qurilmaning nusxasi deb e'lon qilish
Pitfall 4 — simulyatorning o'zini o'zi tasdiqlashi — bo'lardi.

**Egasi:** Ops
**Tetigi:** real NVR ulanganda (WireGuard tunneli ko'tarilgach)

expected: 25 kamerali bozorda bitta slotda (`06:00`) barcha kameralardan
kadr olinadi va `capture_runs` da `failed` qatori paydo BO'LMAYDI. Agar
limitga urilsa: xato kodi `capture_stream_limit` bo'ladi (quruq
«ulanmadi» EMAS) va yechim **sozlama** bo'ladi, qayta loyihalash emas —
(a) `CAPTURE_GLOBAL_CONCURRENCY` ni pasaytirish, (b) qurilmaning
`capture_method` ini `isapi` ga o'tkazish (`/picture` RTSP sessiyasini
umuman band qilmaydi). Ikkala yo'l ham bugun mavjud va ikkalasi ham
test bilan qoplangan; o'zgaradigan narsa — MA'LUMOT.
result: [pending]

## Summary

total: 6
passed: 0
issues: 0
pending: 6
skipped: 0
blocked: 0

## Gaps

Yo'q — bu bandlar bo'shliq emas, **inson ishtirokini, real uskunani yoki
kalendar vaqtni talab qiladigan tekshiruvlar**. 2026-08-01 self-service
direktivasi bo'yicha ular fazani yoki jarayonni bloklamaydi.

**Diqqat — talab holatlariga ta'siri:**

* **4- va 5-bandlar FOUND-06 niki.** Ular bajarilmaguncha «alert
  HAQIQATAN yetib boradi» degan da'vo BERILMAGAN bo'lib qoladi. Talabning
  qolgan uch jumlasi (kamera offline, o'tkazib yuborilgan snapshot,
  backup xatosi -> alert; xatolar Sentry'da) o'lchangan va dalili
  `04-12-SUMMARY.md` da nomma-nom.
* **1-band CAM-06 ning `Done` holatini BEKOR QILMAYDI** — talab matni
  «qorong'i/buzuq/bo'sh kadr avtomatik belgilanadi va `light_mode` bilan
  saqlanadi» deydi va aynan shu o'lchangan. Sozlanadigan narsa —
  chegaraning QIYMATI, mexanizm emas. Lekin agar real kadrlarda
  chegaralar butunlay noto'g'ri chiqsa (masalan barcha 06:00 kadrlari
  `dark` deb belgilansa), CAM-06 `Blocked` ga QAYTARILISHI kerak va
  sabab shu banddan yoziladi.
* **2-band CAM-07 ning chegarasini belgilaydi:** «90 kun to'liq, keyin
  siqilgan» mexanizmi o'lchangan, KALENDAR bo'yicha ishlashi emas.
* **6-band CAM-05 ning simulyator ustidagi dalilining chegarasi:** «real
  qurilmada ishlaydi» degan da'vo hech qayerda berilmagan.
* **3-band 4-fazaniki EMAS** — u FOUND-07 (8-faza) va bu yerda faqat
  ro'yxat to'liq bo'lishi uchun turadi.
