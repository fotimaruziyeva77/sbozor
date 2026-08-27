# Phase 5: Kamera zonalari, CV va nazoratchi tasdig'i — Context

**Gathered:** 2026-08-05
**Status:** Ready for planning
**Source:** `05-RESEARCH.md` ning 14 ochiq savoli (hammasi taklif qilingan standartda qulflandi) + 4-fazadan meros o'lchovlar

<domain>
## Phase Boundary

**Bu fazada:** kamera kadrida rasta zonalarini poligon qilib chizish (versiyalangan, normalangan), RF-DETR + ONNX Runtime bilan aniqlash, `supervision.PolygonZone` bilan bandlik qarori, noaniq navbati, **ko'r audit** va uning xolis aniqlik hisoboti, ko'p kamerali agregatsiya, hamda `occupancy_events` ning billing chegarasiga strukturaviy ulanishi.

**Bu fazada EMAS:** patta hisoblash va kassir (6-faza), nomuvofiqlik case oqimi (7-faza), RF-DETR ni fine-tune qilish (`V2-AI-04` — HITL ma'lumoti buni baribir qo'llab-quvvatlamaydi).

</domain>

<decisions>
## Implementation Decisions

### Fazaning tub farqi (rejalashtirishga ta'sir qiladi)

- **D-01**: **Oldingi to'rt fazada «to'g'ri ishlayaptimi?» savoliga test javob berardi. Bu fazada bermaydi.** Modelning band/bo'sh qarori to'g'riligi — bu haqiqatga qarshi **o'lchov**, va haqiqat (real Karmana kadrlari) hali yo'q va faza tugagunicha kelmasligi mumkin. Shuning uchun fazaning yetkazib berish mahsuloti — **aniqlikni o'lchanadigan va yaxshilanadigan qiladigan mexanizm**, ma'lum bir aniqlik raqami emas.
- **D-02**: Seam — **`sv.Detections`**. Modeldan keyingi hamma narsa to'liq testlanadi. Oltin to'plam darvozasi **uxlab yotgan** holatda quriladi va `source='karmana'` yorlig'i bilan qatorlar paydo bo'lgan kuni **kodsiz o'zi uyg'onadi**.

### Litsenziya — endi mexanik

- **D-03**: `rfdetr` **1.9.1** (Apache-2.0). PML komponenti 1.9.x da **alohida distributivga** ko'chgan: `rfdetr-plus` 1.0.2, `LicenseRef-PML-1.0`, faqat `[plus]` ekstrasi orqali tortiladi. Ya'ni taqiq **lockfile invarianti**: `rfdetr-plus` yo'qligini (va umuman `LicenseRef-*`/AGPL distributiv o'rnatilmaganini) tekshiradigan test yozilади — o'sha darvoza `ultralytics` ni ham ushlaydi.
- **D-04**: **`torch` — `rfdetr` ning majburiy bog'liqligi**, ekstra emas. Ishlab chiqarish `cv-service` image'i `rfdetr` ni **umuman o'rnatmaydi**: faqat `onnxruntime` + oldindan tayyorlangan `.onnx`.

### Poligon muharriri (AI-01)

- **D-05** (OQ-1): **SVG**, `react-konva` emas — nol bog'liqlik, jsdom'da testlanadi, va 2-faza canvasni **o'lchov bilan** rad etgan (`stall-map.tsx` buni hujjatlashtirgan). Geometriya sof funksiyalarda yashaydi, ya'ni render qatlami almashtiriladi, geometriya emas. 50+ poligonda sudrash >16 ms bo'lsa — Konva'ga o'tiladi.
- **D-06**: Jadval nomi **`camera_zones`** — `zones` 2-fazada bozor hududlari uchun band va `stalls.zone_id NOT NULL` unga ishora qiladi. `zones` deb nomlash migratsiyani to'qnashtiradi.
- **D-07**: Koordinatalar normalangan (0..1) va **versiyalangan** — kamera qayta kashf qilinganda yoki ruxsati o'zgarganda poligonlar omon qoladi.

### Aniqlash (AI-02)

- **D-08** (OQ-2): Model varianti — **`RFDETRLarge`** (Apache-2.0). **Kechikish chegara emas**: 175 kadr/kun/bozor da eng yomon holat ham ~47 daq CPU/kun. Ya'ni variant **aniqlik** uchun tanlanadi, tezlik uchun emas, va ROADMAP dagi «EPYC'da benchmark» darvoza bo'lmasligi kerak.
- **D-09** (OQ-3): `triggering_anchors` — **`(CENTER, BOTTOM_CENTER)`**, sozlama sifatida.
- **D-10** (OQ-4): Tiling/SAHI — **yo'q**, v1 da butun kadr. Byudjet bor, lekin murakkablik aniqlik dalilisiz qo'shilmaydi. Rasta kadrda <32 px bo'lsa qayta ko'riladi.
- **D-11** (OQ-8): `uncertain` chegaralari **qatorda** yashaydi (`thresholds_version`) — 4-fazadagi `quality_thresholds_version` naqshi. Sozlash SQL bilan bo'ladi, migratsiya bilan emas.
- **D-12**: AI natijasi confidence bilan saqlanadi va **hech qachon o'zgartirilmaydi**; nazoratchi qarori **alohida yozuv**. Bu strukturaviy bo'lishi kerak, konventsiya emas.

### Nazoratchi tasdig'i va ko'r audit (AI-03, AI-04, AI-06)

- **D-13** (OQ-5): Ko'r audit kunlik byudjeti — **30 band/kun** → oylik ±2–3 f.p. aniqlik oralig'i.
- **D-14** (OQ-6): `eval`/`train` nisbati — **70/30**, **tortish paytida** belgilanadi. Bu audit ma'lumoti o'qitishda ishlatilsa ham hisobot aniqligini shishira olmasligini kafolatlaydi.
- **D-15** (OQ-7): Ko'r audit javobi bandlikni **ham tuzatadi, ham o'lchaydi** — inson javobi sifatliroq haqiqat va uni tashlab yuborish isrof. Hisobot `queue_kind` bo'yicha ajratadi.
- **D-16** (OQ-13): Nazoratchi ishonchliligi (takroriy band) **v1 da yoqiladi**, ~10% — arzon va real kadrsiz ishlaydi.
  ⛔ **QURILMADI (05-11) va bu qaror ONGLI.** Bugungi sxemada D-16 ni
  strukturaviy ravishda **ifodalab bo'lmaydi**: `audit_draw` har hodisani
  eng ko'pi bilan **bir marta** tortadi. Yolg'on mexanizm qurilmadi,
  UI-SPEC §11.6 qatori olib tashlandi, i18n kaliti yozilmadi. To'liq
  bayonot — `05-VALIDATION.md` ning `automated_replacements` bloki.
  Ya'ni **§C.8 ning 5-dushmani bugun ochiq** va u yashirilmagan.
- **D-17**: **Ko'r auditning xolisligi beshta strukturaviy MEXANIZM bilan qo'riqlanadi**, konventsiya bilan emas. Ular repo bo'ylab **`D-17.1`…`D-17.5`** deb ataladi:
  - **D-17.1** — hosila urug' (namunani qayta chizib bo'lmaydi);
  - **D-17.2** — AI maydonlari payloadda **umuman yo'q** (yashirilgan emas);
  - **D-17.3** — «ko'r, lekin ko'rsatilgan» holatini ifodalab bo'lmaydigan qiladigan `CHECK`;
  - **D-17.4** — o'zgarmas javoblar (oshkor qilingandan keyin tahrirlash imkonsiz);
  - **D-17.5** — 70/30 bo'linishi.

  ⛔ **BU RO'YXAT `05-RESEARCH §C.8` NING «BESHTA DUSHMANI» EMAS** — ikkalasi
  ham beshta a'zoli va aynan shu tasodif 05-VERIFICATION ning W-1
  ogohlantirishini tug'dirgan. Ular bir-birining qayta raqamlanishi
  **emas**: §C.8 ning 3-dushmaniga qarshi chora (`UNIQUE(occupancy_event_id)`)
  bu beshlikda **yo'q**, D-17.5 (70/30) esa dushmanlar jadvalida alohida
  qator **emas**. Moslik **1:1 emas** — masalan §C.8 ning 4-dushmaniga
  D-17.1 va D-17.4 **birgalikda** javob beradi.

  ⚠ **Sanoq qaysi ro'yxatga tegishli ekani HAR SAFAR aytilishi shart.**
  «Beshalasi qurilgan» — **mexanizmlar** haqida rost (5/5). «To'rttasi
  qurilgan» — **dushmanlar** haqida rost (5-dushmanning chorasi D-16 va u
  qurilmagan, sabab D-16 bandida).
- **D-18**: «Hammasini tasdiqlash» tugmasi **yo'q** (AI-03).
- **D-19** (AI-06): Kun oxirigacha tasdiqlanmagan noaniq → **«bo'sh»**, hisobotda **alohida belgi bilan**. Bu standart billing kirishiga jimgina aylana olmasligi kerak.

### Agregatsiya va billing chegarasi (AI-05)

- **D-20**: Rasta bir necha kamerada ko'rinsa — **birortasi «band» desa rasta band**.
- **D-21**: `occupancy_events` 4-fazaning **strukturaviy langari**ga osiladi: `snapshots` dagi `UNIQUE (id, is_billable)` ga kompozit FK. Shunda yaroqsiz kadr **umuman** bandlik dalili yarata olmaydi — DB rad etadi. Langar mavjudligi 4-fazada o'lchangan (`BILLABLE_ANCHOR_SUPPORTED = true`, PostgreSQL 18.4).
- **D-22** (OQ-12): `no_coverage` rastalar (birorta kamera ko'rmaydigan) hisobotda **alohida** ko'rsatiladi va hech qachon «bo'sh» ga qo'shilmaydi.

### Servis topologiyasi

- **D-23** (OQ-9): `cv-service` — **HTTP xizmat emas**: `taskiq` worker + health/self-check uchun minimal FastAPI. Bu «aynan 3 servis» cheklovini buzmaydi (CLAUDE.md da `cv-service` allaqachon uchtaning biri).
- **D-24** (OQ-10): ONNX fayli image'ga **build paytida `COPY`** bilan kiradi — takrorlanadigan va tarmoqsiz start. Ish paytida yuklab olish qilinmaydi.
- **D-25** (OQ-11): RF-DETR fine-tuning **bu fazada emas** (`V2-AI-04`). Sabab texnik: nazoratchi **zona darajasidagi ikkilik yorliq** ishlab chiqaradi, detektorga esa **box annotatsiyasi** kerak — ular bir-biriga aylanmaydi. Faza **ma'lumot yig'adi**, o'qitmaydi. Yig'ilgan ma'lumot `timm` krop-klassifikatori uchun yaroqli.

### Meros bandlar

- **D-26** (OQ-14): `npm run gate` byudjeti **qayta o'lchanadi** — 4-faza uni 900 s da qoldirib, ochiq band sifatida shu fazaga topshirgan. Xost sekinlashuvi hisobga olinsin: o'lchov paytida ikkinchi Docker steki ishlab turgan bo'lishi mumkin.
- **D-27**: `scripts/check-validation-signoff.mjs` ning `DEFAULT_FILE` i hamon 2-fazaga qadalgan — tuzatilsin.

### Claude's Discretion

Jadval/ustun nomlari (yuqoridagi `camera_zones` dan tashqari), indekslar, poligon geometriyasining ichki tuzilishi, navbat UI'sining parchalanishi, ONNX sessiya sozlamalari — mavjud `03-PATTERNS.md`/`04-PATTERNS.md` konventsiyalariga mos bo'lsa yetarli.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agentlar rejalashtirish yoki implementatsiyadan OLDIN o'qishi SHART.**

- `.planning/phases/05-kamera-zonalari-cv-va-nazoratchi-tasdig-i/05-RESEARCH.md` — 1408 qator; litsenziya tekshiruvi, `sv.Detections` seam'i, ko'r auditning besh tahdidi, `## Validation Architecture`
- `CLAUDE.md` — stek yozuvi; **2026-08-05 da RF-DETR 1.9.1, supervision 0.30.0 va PML lockfile invarianti yozildi**
- `.planning/ROADMAP.md` — Phase 5 mezonlari va «Mahsulot qoidasi» bo'limi
- `.planning/phases/04-snapshot-pipeline/04-03-SUMMARY.md` — `snapshots` sxemasi va **billing langari** (`UNIQUE (id, is_billable)`)
- `.planning/phases/04-snapshot-pipeline/04-04-SUMMARY.md` — sifat verdikti va `light_mode`; kadr **qachon** `is_billable=false` bo'lishi
- `.planning/phases/04-snapshot-pipeline/04-07-SUMMARY.md` — kadr olish quvuri, `capture_runs`
- `.planning/phases/04-snapshot-pipeline/04-06-SUMMARY.md` — ombor klienti (kadrni undan olasiz)
- `.planning/phases/02-.../02-PATTERNS.md`, `03-PATTERNS.md`, `04-PATTERNS.md` — kod konventsiyalari

</canonical_refs>

<specifics>
## Specific Ideas

- `sv.PolygonZone` / `sv.PolygonZoneAnnotator` — bandlik qadami va nazoratchi ko'radigan belgilangan dalil-rasm. Nuqta-poligon ichida tekshiruvini **qo'lda yozmaslik**
- Bitta rasta bir necha kamerada — ko'p-ko'pga bog'lanish; 2-fazaning `stalls` va 4-fazaning `cameras` bilan kesishadi
- `occupancy_events.model_version` — `timm` krop-klassifikatori kelajakda **raqobatlashuvchi** verdikt yozib, o'sha ajratilgan namunada solishtirilishi uchun
- Eng katta qoldiq xavf: RF-DETR ning COCO sinflari o'zbek bozori mollarida **umuman ishlaydimi** — noma'lum, hamma joyda LOW confidence deb belgilangan
- 300–1000 rasta uchun poligon chizish — halol minimal o'zaro ta'sir nima? Bulk/grid-assist yo'li bormi yoki har rasta alohida chiziladimi

</specifics>

<deferred>
## Deferred Ideas

- RF-DETR fine-tuning — `V2-AI-04`
- `timm` krop-klassifikatori — ikkinchi oy aniqlik richagi; `model_version` bilan ilgak hozirdan qoldiriladi
- `no_coverage` rastalar uchun qo'lda rejim — `V2-AI-02`
- Tiling/SAHI — rasta kadrda <32 px bo'lsa qayta ko'riladi
- Real kadrda chegaralarni sozlash — Phase 0, fazani bloklamaydi

</deferred>

---

*Phase: 05-kamera-zonalari-cv-va-nazoratchi-tasdig-i*
*Context gathered: 2026-08-05 — tadqiqot standartlari + 4-faza o'lchovlari*
