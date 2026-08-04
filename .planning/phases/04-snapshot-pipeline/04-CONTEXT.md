# Phase 4: Snapshot pipeline — Context

**Gathered:** 2026-08-04
**Status:** Ready for planning
**Source:** `04-RESEARCH.md` ning 10 ochiq savoli (hammasi taklif qilingan standartda qulflandi) + 3-fazadan meros qolgan o'lchovlar

<domain>
## Phase Boundary

**Bu fazada:** mavsumiy snapshot jadvali (bozor bo'yicha), kunlik rejaning materializatsiyasi, idempotent kadr olish va retry, o'tkazib yuborilgan slotning **yo'qlik yozuvi**, sifat filtri (`light_mode` + `quality_verdict`), S3-mos omborga arxivlash va saqlash siyosati, hamda Telegram/Sentry alertlari.

**Bu fazada EMAS:** kamera zonalari va CV aniqlash (5-faza), band/bo'sh qarori va billing (5–6 faza). Bu faza **kadrni ishonchli yetkazib beradi va uning sifatini belgilaydi** — undan xulosa chiqarmaydi.

</domain>

<decisions>
## Implementation Decisions

### Mahsulot qoidasi (majburiy)

- **D-01**: Admin snapshot jadvali uchun **hech nima kiritmaydi**. Usta bozor yaratilganda 7 slotli standart profil yozadi (`06:00–08:00` har 30 daq + `16:00` + `18:00`), keyin xohlasa tahrirlaydi. Self-service qoidasi buni talab qiladi (OQ-10).

### Orkestratsiya — Open Decision #2 ning yechimi (2026-08-04)

- **D-02**: `taskiq scheduler` **faqat holatsiz 1-daqiqalik tik** beradi. Reja, ijara (lease), idempotentlik va yo'qlik yozuvi Postgres `capture_runs` da yashaydi (`SELECT … FOR UPDATE SKIP LOCKED`). **O'lchangan sabab:** taskiq'ning cron «oxirgi ijro» holati oddiy xotiradagi `dict`, taqsimlangan qulf yo'q — slot-boshiga cron o'tkazib yuborilgan slotni **izsiz** yo'qotadi va bu CAM-05 ning o'z talabiga zid. `RedisScheduleSource` yaroqsiz: loyihaning Valkey'i `--save "" --appendonly no` bilan ishlaydi, ya'ni kesh qayta ko'tarilganda hamma bozorning jadvali jimgina yo'qolardi.
- **D-03**: Tik **idempotent** bo'lgani uchun taskiq'ning uchala nosozlik rejimi (dublikat ishga tushish, o'tkazib yuborish, qayta ishga tushish) zararsiz bo'ladi — «aynan bitta scheduler» operatsion talabi ham shu bilan yo'qoladi.
- **D-04** (OQ-8): Vazifa birligi — **NVR + slot**, kamera + slot emas. Sabab: konkurentlik chegarasi **NVR ga** tegishli, ya'ni semafor bitta jarayon ichida bo'lishi kerak; kamera bo'yicha vazifa taqsimlangan qulf talab qilardi.
- **D-05** (OQ-9): Jadval kun o'rtasida o'zgartirilsa **bugungi rejaga ta'sir qilmaydi**. Reja kunning birinchi tikida materializatsiya qilinadi. SC#1 buni aniq yozgan: «**ertasi kuni** aynan o'sha slotlarda». UI «bugun: 7 slot · ertaga: 5 slot» ni ko'rsatadi.

### Kadr olish

- **D-06**: Standart usul — go2rtc `/api/frame.jpeg`, zaxira — Hikvision ISAPI `/picture`, oxirgi chora — ffmpeg. Uchalasi ham **sozlanadigan** quriladi (ROADMAP Open Decision #1, 2026-08-01 da hal qilingan).
- **D-07**: **ISAPI `/picture` nol RTSP sessiyasi ochadi** — ya'ni sessiya bosimi ostida u zaxira emas, eng **xavfsiz** usul. Buni sozlama tanlovida hujjatlashtirish shart.
- **D-08** (sessiya chegarasi): `max_concurrent_captures` standarti — **1** (ketma-ket). Arifmetika xavfni yo'q qiladi: sovuq kadr ~4 s, 25 kamera to'liq ketma-ket = 100 s, grace oynasi esa 600 s. Ya'ni NVR'ning o'lchanmagan sessiya chegarasi fazani **hech qachon bloklay olmaydi**, faqat kechikish narxini beradi. Simulyator sessiya chegarasini umuman modellashtirmaydi (3-faza tekshiruvida ochiq yozilgan).
- **D-09** (OQ-2): `cameras.capture_stream` = **`'main'`**, `'sub'` bitta sozlama bilan. ⚠ Bu tanlov omborni ~12× va 5-fazaning aniqlik shiftini o'zgartiradi — real kadrda Phase 0/pilotda o'lchanadi.
- **D-10** (OQ-5): Yopiq kunlarda ham kadr olinadi (`capture_on_closed_days` = `true`). Yopiq kundagi band rasta — aynan mahsulot izlaydigan anomaliya. Yiliga ~2 600 qo'shimcha kadr.
- **D-11** (OQ-7): Kadr olishdan keyin go2rtc oqimi **ro'yxatdan chiqarilmaydi**. go2rtc yalqov — tomoshabin bo'lmasa RTSP sessiyasini o'zi yopadi. `ensure_stream()` idempotent; `remove_stream()` faqat kamera arxivlanganda.

### Sifat filtri

- **D-12** (OQ-1): `light_mode` — **superset**: enum (`day`/`low_light`/`ir_night`/`unknown`) **va** alohida `quality_verdict`. Narxi ~15 qator, 5 va 8-fazalarga aniq foyda.
- **D-13**: Vosita — **faqat `Pillow`**, `opencv` kerak emas (`ImageStat` mean/stddev; kesilgan JPEG → `OSError: Truncated File Read`; `MAX_IMAGE_PIXELS`; `LOAD_TRUNCATED_IMAGES=False` — mahalliy tekshirilgan).
- **D-14**: `dark` **ikki shartli** qoida bo'lishi shart (`mean < X` **VA** `stddev < Y`). Faqat o'rtachaga tayangan qoida qonuniy qish-tong kadrlarini **oylab** jimgina tashlab yuborardi.
- **D-15**: **O'lchovlarning o'zi saqlanadi**, faqat hukm emas. Shunda Phase 0 ning real kadrlari chegaralarni SQL bilan sozlaydi, qayta kadr olish bilan emas. Chegaralar hozircha **LOW confidence** — real Karmana kadri yo'q, shuning uchun ular ataylab sozlanadigan.
- **D-16**: Billing kafolati **strukturaviy** bo'ladi, konventsiya emas: `snapshots` da `UNIQUE (id, is_billable)` langari, 5-fazada `occupancy_events` dan kompozit FK. Shunda yaroqsiz kadr **umuman** bandlik dalili yarata olmaydi — DB rad etadi. Bu 1-fazaning `FINANCIAL_TABLES` reyestri naqshining o'zi.

### Ombor

- **D-17**: `aiobotocore` **3.9.0** to'g'ridan-to'g'ri. `aioboto3` **o'rnatib bo'lmaydi** — u `aiobotocore[boto3]==2.25.1` ni qattiq qadaydi va `boto3` ni pindan pastga tushiradi; oxirgi relizi 2025-10-30 (2026-08-04 da PyPI bilan tasdiqlandi). `aiohttp` allaqachon `taskiq` orqali mavjud. **Hech qachon `minio-py`** — S3 API omborni sozlama o'zgarishi qilib saqlaydi.
- **D-18** (OQ-6): Saqlash — **90 kun to'liq + 365 kun siqilgan = 455 kun**. Ikkala qiymat ham `Settings` da, ya'ni buyurtmachi javobiga qarab bitta son o'zgaradi.

### Alert va kuzatuv

- **D-19**: **Alertlarga kadr rasmi HECH QACHON biriktirilmaydi.** Dalil-kadrlar bozor tashrifchilarining shaxsiy ma'lumoti, Telegram serverlari esa loyiha zimmasiga olgan O'zR data-rezidentlik chegarasidan tashqarida. Faqat matn va sonlar.
- **D-20**: Alert **muvaffaqiyat signalining yo'qligiga** qo'yiladi, faqat xato chiqish kodiga emas (CLAUDE.md talabi). «Bajarilmagan slot» ni aniqlash «bajarilib xato bergan slot» dan qiyinroq, chunki birinchisida hech qanday hodisa yo'q — shuning uchun yo'qlik yozuvi rejadan kelib chiqadi.
- **D-21** (OQ-3): Tashqi dead-man's switch v1 da **kod yozilmaydi**. `ops/docs/monitoring.md` ga bitta URL sozlash yo'riqnomasi (healthchecks.io / UptimeRobot) va `03-HUMAN-UAT.md` uslubidagi ops bandi.
- **D-22**: Alert charchashi — 25 kamera × 7 slot × N bozor ko'p shovqin beradi. Guruhlash va chegara majburiy; lekin **backup xatosi va uzluksiz kamera offline hech qachon bo'g'ilmaydi**.

### Wave 0

- **D-23** (OQ-4): `GENERATED STORED` ustun `UNIQUE`/FK nishoni bo'la oladimi — `postgres:18.4` da **birinchi migratsiyadan oldin bitta migratsiya bilan o'lchanadi**. Yiqilsa — `BEFORE INSERT/UPDATE` trigger varianti (~15 qator), kafolat saqlanadi.

### Claude's Discretion

Jadval/ustun nomlari, indekslar, `capture_runs` ning aniq holat mashinasi, S3 kalit tartibi, Pillow chaqiruvlarining tuzilishi, UI komponentlarining parchalanishi — mavjud `02-PATTERNS.md`/`03-PATTERNS.md` konventsiyalariga mos bo'lsa yetarli.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agentlar rejalashtirish yoki implementatsiyadan OLDIN o'qishi SHART.**

### Fazaning o'z tadqiqoti
- `.planning/phases/04-snapshot-pipeline/04-RESEARCH.md` — 1776 qator; taskiq scheduler manbasining o'qilishi, paket o'lchovlari, Pillow tekshiruvi, `## Validation Architecture`

### 3-fazadan meros (bevosita ishlatiladi)
- `.planning/phases/03-.../03-06-SUMMARY.md` — `taskiq` brokeri, worker konteyneri, **so'rov konteksti tashqarisida RLS o'rnatadigan job** (bu fazaning yagona analogi)
- `.planning/phases/03-.../03-13-SUMMARY.md` — `authenticated_rtsp_source()`, to'rt oqish yuzasi, foizli kodlash darvozasi
- `.planning/phases/03-.../03-14-SUMMARY.md` — mock'siz kadr o'lchovi; **`PUT /api/streams` natijadan o'lchanadi, status kodidan emas** (`:ro` config, D-11)
- `.planning/phases/03-.../03-05-SUMMARY.md` — ISAPI klienti, 12 kodli xato taksonomiyasi, teskari retry siyosati

### Loyiha darajasidagi
- `CLAUDE.md` — stek yozuvi; **2026-08-04 da `aioboto3` → `aiobotocore` tuzatildi**
- `.planning/ROADMAP.md` — Phase 4 ning 5 mezoni, «Mahsulot qoidasi» bo'limi, Open Decision #1 va #2 (ikkalasi ham hal qilingan)
- `.planning/phases/02-.../02-PATTERNS.md`, `03-PATTERNS.md` — kod konventsiyalari

</canonical_refs>

<specifics>
## Specific Ideas

- Idempotentlik kaliti: `(market_id, camera_id, slot, business_date)` — biznes-kun Asia/Tashkent bo'yicha (1-fazada o'rnatilgan)
- `capture_runs` holat mashinasi yo'qlikni ham ifodalashi kerak: rejalashtirilgan slot yozuvi **oldindan** yaratiladi, shunda «hech qachon bajarilmagan» aniqlanadigan bo'ladi
- Yarim muvaffaqiyat (kadr olindi, yuklash yiqildi) retry uchun alohida holat
- S3 kalit tartibi bozor/kamera/sana bo'yicha topishga imkon berishi kerak
- Ombor arifmetikasi: 175 kadr/kun/bozor — o'lcham, yillik o'sish va Contabo diskiga ta'siri tadqiqotning D bo'limida
- Simulyator qorong'i/buzuq/bo'sh kadrni buyurtma bo'yicha bera olishi kerak — aks holda sifat filtri darvoza emas, konventsiya bo'lib qoladi (tadqiqotning Validation Architecture bo'limi)

</specifics>

<deferred>
## Deferred Ideas

- Tashqi dead-man's switch kodi — v1 da yo'q (D-21), hujjat va ops bandi
- Audit hajmi remediatsiyasi (ustun bilan cheklangan trigger) — 3-fazadan meros, past ustuvorlik, qayta ochish sharti: skan CRON'ga o'tganda **yoki** bozorlar o'ntadan oshganda
- `Go2rtcClient.remove_stream` reconciliation (faol kameralar bilan go2rtc oqimlarini davriy moslashtirish) — 3-fazadan meros, egasi shu faza
- Darvoza chegarasini 1200 s dan tushirish — 538 s ga 2.2× zaxira, alohida qaror, bir necha yugurish o'lchoviga tayanishi kerak
- Real kadrda sifat chegaralarini sozlash — Phase 0, fazani bloklamaydi

</deferred>

---

*Phase: 04-snapshot-pipeline*
*Context gathered: 2026-08-04 — tadqiqot standartlari + 3-faza o'lchovlari*
