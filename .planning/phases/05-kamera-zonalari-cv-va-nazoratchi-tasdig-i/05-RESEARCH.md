# Faza 5: Kamera zonalari, CV va nazoratchi tasdig'i — Tadqiqot

**Tadqiqot sanasi:** 2026-08-05
**Domen:** Computer vision (occupancy detection), polygon zone editor, human-in-the-loop verification, blind audit sampling
**Ishonch darajasi:** **MEDIUM-HIGH** — stek va sxema HIGH (tekshirilgan), *aniqlik* LOW (o'lchanmagan va o'lchab bo'lmaydi, quyiga qarang)

---

## Xulosa

**Bu faza oldingi to'rttasidan tubdan farq qiladi va rejalashtirish
aynan shu farqdan boshlanishi kerak.**

1–4 fazalarning har biri o'z to'g'riligini **test bilan isbotlay
olardi**. «Slot ertasi kuni paydo bo'ldimi» — ha yoki yo'q. «Dublikat
yozildimi» — ha yoki yo'q. 5-faza esa markazida shunday da'vo turadi:
**«bu rasta band»**. Bu da'vo to'g'rimi degan savol — testning javobi
emas, **haqiqat bilan solishtirilgan o'lchov** natijasi. Haqiqat esa —
real Karmana kadrlari — **hozir mavjud emas**, va Phase 0 bloklamaydigan
trekka tushirilgani uchun **bu faza yopilgunga qadar kelmasligi ham
mumkin**.

Bundan yagona to'g'ri xulosa chiqadi va u butun rejani belgilaydi:

> **Bu fazaning muhandislik mahsuloti — ma'lum bir aniqlik raqami emas,
> balki aniqlikni O'LCHASH VA YAXSHILASH MUMKIN QILADIGAN MASHINA.**
> Real kadrlar kelgan kuni aniqlik o'lchanishi, chegaralar sozlanishi
> va model qayta o'rgatilishi kerak — **qayta loyihalashsiz**.

Amalda bu uch narsani anglatadi: (a) modelning atrofidagi hamma narsa —
geometriya, post-processing arifmetikasi, agregatsiya, sxema kafolatlari,
namuna tortish, hisobot matematikasi — **real kadrsiz to'liq
isbotlanadi**; (b) modelning **o'zi** chok (seam) bo'lib ajratiladi va
uning ustidagi da'volar «uskunasiz isbotlanmaydi» ro'yxatiga ochiq
yoziladi; (c) **aniqlik darvozasi birinchi kundan quriladi, lekin real
ma'lumot tushmaguncha uxlab turadi** (§Validation → «oltin to'plam»).

Fazaning eng muhim yagona komponenti — **AI-04 ko'r audit**. U UI
tafsiloti emas: bu mahsulotning **yagona xolis o'lchov asbobi**. Uni
noto'g'ri qurish «AI aniqligi 94%» degan ma'nosiz raqam beradi va buni
hech kim sezmaydi. §C da uning xolisligini buzadigan **beshta**
mexanizm va har biriga qarshi **strukturaviy** (kelishuv emas) chora
ko'rsatilgan.

**Tekshiruv paytida topilgan to'rtta muhim narsa:**

| # | Topilma | Ta'siri |
|---|---|---|
| 1 | **RF-DETR litsenziya bo'linishi TASDIQLANDI va endi STRUKTURAVIY** — 1.9.x da PML komponenti alohida `rfdetr-plus` distribution'iga ajratilgan (`license_expression = LicenseRef-PML-1.0`) | Litsenziya xavfi *intizom* emas, **lockfile invarianti** bo'ladi — testlanadi (§B.1) |
| 2 | ⚠ **`zones` jadvali ALLAQACHON band** — 2-faza uni «bozor zonasi» ma'nosida yaratgan va `stalls.zone_id` unga `NOT NULL` bog'langan | Kamera poligonlari **`camera_zones`** deb atalishi SHART (§A.1) |
| 3 | ⚠ **HITL ma'lumoti RF-DETR ni fine-tune qila OLMAYDI** — nazoratchi *zona-boshiga ikkilik yorliq* beradi, detektor esa *quti annotatsiyalari* talab qiladi | AI-03 ning «dataset» i aslida **`timm` klassifikatori** uchun; RF-DETR fine-tuning allaqachon **V2-AI-04** (§E.14) |
| 4 | **Kechikish bu fazaning chegarasi EMAS** — 175 kadr/kun/bozor eng og'ir ssenariyda ham ~47 daqiqa CPU | ROADMAP ning «EPYC benchmark» bandi darvoza emas; model varianti **aniqlik** bo'yicha tanlanadi (§B.3) |

**CLAUDE.md ning uchta raqami eskirgan** (`rfdetr` 1.8.3 → **1.9.1**,
`supervision` 0.29.1 → **0.30.0**) va bittasi **to'g'ri** bo'lib chiqdi
(`opencv-python-headless` 4.14.0.94, 5.x emas). Bittasi esa **empirik
rad etilgan**: CLAUDE.md ning `react-konva` asosi («SVG/DOM 1000
rastada o'ladi») 2-fazada o'lchov bilan noto'g'ri deb topilgan (§A.5).

**Asosiy tavsiya:** poligonlarni **SVG** bilan chizing va butun
geometriyani sof funksiyalarga chiqaring; `RFDETRLarge` (Apache-2.0)
ni ONNX'ga eksport qilib faqat `onnxruntime` bilan ishlating; AI
javobini `occupancy_events` da o'zgarmas qilib, nazoratchi qarorini
`zone_reviews` da **alohida** saqlang; ko'r auditni hosila seed +
deterministik hash bilan **qayta chiqariladigan** qiling; va butun
fazani **`sv.Detections` chokidan** ajratib testlang.

---

## A. Zona poligonlari (AI-01)

### A.1 — ⚠ NOM TO'QNASHUVI: `zones` jadvali ALLAQACHON BAND

Bu bo'limning eng birinchi topilmasi va u rejaga darhol ta'sir qiladi.

2-faza `zones` jadvalini **bozor zonasi** (rastalar guruhi — «qator»,
«sabzavot bo'limi») ma'nosida yaratgan:

```python
class Zone(Base, TenantMixin, TimestampMixin):
    """Bozor zonasi — YASSI ro'yxat, ierarxiya YO'Q (D-03)."""
    __tablename__ = "zones"
```

va `stalls.zone_id` **`NOT NULL`** bo'lib unga kompozit FK bilan
bog'langan. Frontendda ham `frontend/src/components/zones/` mavjud.
`[VERIFIED: packages/sbozor-core/sbozor_core/models/market.py:295-317,
352-371; frontend/src/components/ ro'yxati]`

5-fazaning «zonasi» esa **butunlay boshqa narsa** — kamera kadridagi
poligon. Ikkisi bir nomda yashay olmaydi.

**Qaror: `camera_zones`.** Bu CLAUDE.md ishlatayotgan nom bilan ham
bir xil («`camera_zones` → `occupancy_events`»). Reja hech qachon
«zona» so'zini kvalifikatorsiz ishlatmasin: **bozor zonasi** yoki
**kamera zonasi**. UI matnlarida ham (uch tilda) shu farq saqlansin,
aks holda admin ustada ikki xil «zona» ko'rib chalkashadi.

### A.2 (Q1) — Sxema: normalangan koordinata, versiya va rezolyutsiya

```
camera_zones
  id, market_id, camera_id, stall_id,
  version int NOT NULL,                    -- monoton, 1 dan
  polygon jsonb NOT NULL,                  -- [[x,y],...] hammasi 0..1
  source_width int NOT NULL,               -- chizilgan kadr o'lchami
  source_height int NOT NULL,
  is_active boolean NOT NULL,
  created_by, created_at
  -> FK (market_id, camera_id) REFERENCES cameras (market_id, id)
  -> FK (market_id, stall_id)  REFERENCES stalls  (market_id, id)
  -> UNIQUE (market_id, camera_id, stall_id, version)
  -> CHECK (jsonb_array_length(polygon) >= 3)
```

**Nega 0..1:** poligon kadr o'lchamiga emas, kadrning **nisbatiga**
bog'lanadi. Shu bilan asosiy oqim (4 MP) va sub-oqim (D1) o'rtasida
almashish poligonni buzmaydi — bu 4-fazadagi ochiq `capture_stream`
qarorining bevosita foydasi (`04-RESEARCH.md` §D.11).

⚠ **Lekin bu FAQAT nisbat (aspect ratio) saqlanganda ishlaydi.** 4 MP
(16:9) dan D1 (4:3) ga o'tish kadrni **cho'zadi yoki kesadi** va 0..1
koordinatalar jimgina siljiydi. Shuning uchun `source_width/height`
saqlanadi:

- yangi kadrning nisbati chizilgandagidan farq qilsa, tizim
  **ogohlantiradi** va zonani `needs_review` deb belgilaydi;
- avtomatik «to'g'rilash» qilinMAYDI — cho'zishmi yoki kesishmi
  ekanini bilmasdan tuzatish noto'g'ri javob beradi va bu jimgina
  noto'g'ri hisob demakdir.

**Kamera qayta kashf qilinganda (CAM-08) nima bo'ladi:** hech nima.
Kamera identifikatori `UNIQUE (market_id, nvr_id, channel_no)`, ya'ni
qayta skanerlash mavjud kamerani **tegmaydi** va `cameras.id`
o'zgarmaydi. Demak `camera_zones.camera_id` FK'si omon qoladi.
`[VERIFIED: models/nvr.py:443-444 + CAM-08 talabi «mavjudi tegilmaydi»]`

**Versiyalash — nega `UPDATE` emas:** poligonni tahrirlash **yangi
`version` qatori** yaratadi, eskisi `is_active=false` bo'ladi. Sabab
§B.5 dagi bilan bir xil: `occupancy_events.zone_version` o'sha paytdagi
poligonga ishora qiladi, ya'ni bir oy oldingi dalil rasmini bugungi
poligon bilan ustma-ust qo'yish **noto'g'ri** bo'lardi. Poligon
o'zgarishi o'tmishdagi dalilni qayta yozmaydi — bu tariflarning
tarixiyligi (MARKET-03) bilan bir xil naqsh.

### A.3 (Q2) — Bitta rasta bir necha kamerada: many-to-many ALLAQACHON hal

`camera_zones` ning o'zi **assotsiatsiya jadvali** — unda ham
`camera_id`, ham `stall_id` bor. Bitta rasta uch kamerada ko'rinsa —
**uchta qator**, har birida o'sha kameradagi o'z poligoni.

Ya'ni «many-to-many» uchun alohida jadval kerak emas va u tabiiy
chiqadi. `UNIQUE (market_id, camera_id, stall_id, version)` — bir
kamerada bir rastaga bir faol poligon.

Bu §D dagi AI-05 agregatsiyasining kirish ma'lumoti: bir rastaning
bir slotdagi javobi = o'sha rastaning **barcha** `camera_zones`
qatorlaridan chiqqan verdictlar to'plami.

⚠ Teskari holat ham bor va u modelda ochiq qolishi kerak: **kamera
ko'rmaydigan rastalar**. `stalls` da `camera_zones` qatori yo'q rasta
mutlaqo qonuniy (REQUIREMENTS `V2-AI-02` aynan shu ~10% haqida).
Bunday rasta uchun AI hisobi **yo'q** — «bo'sh» emas, **`no_coverage`**.
Bu farq hisobotda ko'rinishi shart, aks holda qamrovsiz rasta
«bo'sh» deb ko'rinib, jimgina yo'qotishga aylanadi.

### A.4 (Q3) — Self-service: 300–1000 rasta uchun HALOL javob

**Halol javob: poligonlar rasta-boshiga chiziladi va buni avtomatik
qilishning ishonchli yo'li yo'q.** «Chizmadan avtomatik ajratish»
degan va'da real kadrda ishlamaydi va uni MVP'da urinib ko'rish
vaqtni yoqish demak.

Lekin **ish hajmi ko'ringanidan ancha kichik** va buni aniq aytish
kerak:

| Kattalik | Qiymat |
|---|---|
| Bozordagi rasta | 300–1000 |
| Kamera | 20–25 |
| Bir kamerada ko'rinadigan rasta | ~10–40 |
| Jami chiziladigan poligon | ~300–1000 (bir necha kamerada ko'rinsa ko'proq) |
| Bitta poligon (4–6 nuqta) | ~10–20 s |
| **Jami** | **~2–5 soat, bir martalik** |

Bu ko'p, lekin **bir martalik** va NVR o'rnatishdan arzon. Uni
uch yo'l bilan kamaytirish mumkin va uchalasi ham halol (har rasta
baribir o'z poligonini oladi):

1. **Qator bo'yicha interpolyatsiya (eng katta yutuq).** Bozor
   rastalari qator-qator va bir xil o'lchamda. Operator qatorning
   **birinchi** va **oxirgi** rastasini chizadi, «N ta rastaga bo'l»
   deydi — tizim oralig'ini teng bo'lib N ta to'rtburchak yaratadi.
   Har biri keyin alohida tuzatiladi. ~10× tezlashtiradi va hech
   qanday CV talab qilmaydi — sof geometriya.
2. **Oxirgi poligonni nusxalash + siljitish** — qo'shni rasta uchun.
3. **To'liq bo'lishi SHART EMAS.** Kamera qisman zonalangan holda ham
   foydali: zonalangan rastalar AI hisobiga kiradi, qolganlari
   `no_coverage`. Ya'ni **usta bu qadamda bloklanmaydi** — bu
   ROADMAP ning «tashqi bog'liqlik hech qachon `Blocks:` bo'lmaydi»
   qoidasining aynan qo'llanishi.

### A.5 — ⚠ Kutubxona tanlovi: CLAUDE.md `react-konva` deydi, men **SVG** ni tavsiya qilaman

Bu tavsiya CLAUDE.md ga zid, shuning uchun sababi to'liq yoziladi.

**CLAUDE.md ning asosi:** *«Handles 1000 stalls with pan/zoom where
SVG/DOM dies»*.

**Bu asos 2-fazada EMPIRIK RAD ETILGAN.** `stall-map.tsx` ning
sarlavha izohi (o'qildi):

> *«Canvas kutubxonasi (RESEARCH Pattern 11) O'LCHOV bilan rad etilgan…
> 1000 elementli React yangilanishi memo bilan ~4 ms; narxi esa haqiqiy
> bo'lardi: SSR yo'q, a11y yo'q, matn o'lchamlari qo'lda.»*

`[VERIFIED: frontend/src/components/stalls/stall-map.tsx:22-36 — manba o'qildi]`

Ya'ni loyiha «1000 element DOM'da o'ladi» degan da'voni allaqachon
o'lchab, noto'g'ri deb topgan.

**Poligon muharriri uchun qo'shimcha dalillar:**

| Omil | Poligon muharriridagi haqiqat |
|---|---|
| Ekrandagi interaktiv obyekt | **1 ta kadr + ~10–40 poligon** — Konva'ning kuchli tomoni (minglab obyekt) bu yerda ishlamaydi |
| Test qilinishi | **Bu hal qiluvchi omil.** `vitest` + `jsdom` — jsdom'da **canvas yo'q**; `react-konva` ni sinash uchun `node-canvas` (native build) kerak. SVG esa oddiy DOM tugunlari — Testing Library ularni to'g'ridan-to'g'ri ko'radi |
| Playwright | Loyihada **YO'Q** — `vitest.config.ts` izohi: *«Playwright E2E ATAYIN bu yerda EMAS — u 8-fazaga qoldirilgan (OQ-2)»*. Ya'ni canvas'ni sinaydigan ikkinchi yo'l ham yo'q |
| Yangi bog'liqlik | SVG — **0 ta**; Konva — `konva` + `react-konva` |
| a11y / klaviatura | SVG'da `<polygon tabIndex>` ishlaydi; canvasda qo'lda quriladi |

`[VERIFIED: frontend/package.json — konva va react-konva O'RNATILMAGAN;
frontend/vitest.config.ts:14-20 — Playwright 8-fazaga qoldirilgani]`

**Tavsiya:** **SVG + React** (`<image>` fon + `<polygon>` + `<circle>`
tepalar). Konva **rad etilmaydi, kechiktiriladi**: agar o'lchov
(50+ poligonli kamerada tepani sudrash) 16 ms dan oshsa, renderni
Konva'ga almashtirish mumkin — chunki quyidagi qoida bu almashtirishni
arzon qiladi.

**Eng muhim me'moriy qoida (kutubxonadan qat'i nazar):**

> **Geometriya sof funksiyalarda yashaydi, render qatlamida emas.**

`frontend/src/lib/zone-geometry.ts`:

```
addVertex, moveVertex, deleteVertex, closePolygon, undo/redo,
normalize(px, w, h) / denormalize(norm, w, h),
isSelfIntersecting(polygon), polygonArea, centroid,
interpolateRow(first, last, n)     // A.4 dagi qator yordamchisi
```

Bularning **hammasi DOM'siz** va loyihada allaqachon mavjud
`node --test scripts/*.test.mjs` yugurtgichida sinaladi (Phase 1 dagi
37 sof funksiya testi shu shaklda). Render komponenti esa mantiqsiz
bo'ladi: kirishi — nuqtalar massivi, chiqishi — SVG. Shunda:

- muharrirning **butun xulqi real brauzersiz isbotlanadi**;
- SVG → Konva almashinuvi **faqat render faylini** o'zgartiradi;
- jsdom'ning canvas yo'qligi muammo bo'lib qolmaydi.

⚠ `isSelfIntersecting` ni e'tibordan qoldirmaslik kerak: o'zi bilan
kesishgan poligon `cv2.pointPolygonTest` da aniqlanmagan natija beradi.
Uni saqlash paytida rad etish kerak — bu sof geometriya, to'liq
testlanadi.

---

## B. Aniqlash — RF-DETR va ONNX (AI-02)

### B.0 — ⚠ CLAUDE.md eskirgan: `rfdetr` 1.8.3 emas, **1.9.1**

CLAUDE.md `rfdetr 1.8.3` deb yozadi. O'lchandi: `1.8.3` **2026-06-29**
da chiqqan, undan keyin ikkita reliz bo'lgan.

| Nima | CLAUDE.md (iyul) | PyPI, 2026-08-05 da o'lchandi |
|---|---|---|
| Oxirgi versiya | `1.8.3` | **`1.9.1`** — yuklangan **2026-08-04** (kecha) |
| Oraliq reliz | — | `1.9.0` (2026-07-29) |
| `requires_python` | — | `>=3.10` — loyihaning 3.13 i ichida ✓ |

`[VERIFIED: pypi.org/pypi/rfdetr/json — 2026-08-05 da o'qildi]`

Bu **eskirish, xato emas** — lekin 4-fazadagi `aioboto3` epizodi
ko'rsatdiki, CLAUDE.md dagi versiya raqamini ko'chirib yozish yetarli
emas. Reja `1.9.1` ni pin qilsin va bog'liqliklarini o'zi tekshirsin.

`rfdetr 1.9.1` ning bog'liqliklari (PyPI `requires_dist` dan aynan):

```
torch>=2.2.0, torchvision>=0.17.0, transformers>=5.1.0,<6.0.0,
pydantic>=2.0,<3, supervision>=0.29.0, numpy, requests, tqdm,
pyDeprecate>=0.9,<0.10
```

⚠ **`torch` — `rfdetr` ning MAJBURIY bog'liqligi, ixtiyoriy emas.** U
`extra` ostida emas, asosiy ro'yxatda. Ya'ni `pip install rfdetr` prod
image'ga ~800 MB torch tortadi va bu CLAUDE.md ning «torch hech qachon
prod image'da bo'lmaydi» qoidasini buzadi. Buning yagona to'g'ri
oqibati §E da: **prod cv-service `rfdetr` ni umuman o'rnatmaydi** —
faqat `onnxruntime` + tayyor `.onnx` fayl. `rfdetr` faqat trening
image'ida yashaydi. `[VERIFIED: requires_dist]`

**Boshqa paketlarning holati (hammasi 2026-08-05 da PyPI'dan):**

| Paket | CLAUDE.md | Haqiqiy | Izoh |
|---|---|---|---|
| `supervision` | 0.29.1 | **0.30.0** (2026-08-04) | ESKIRGAN. MIT. `rfdetr` `>=0.29.0` talab qiladi → 0.30.0 mos ✓ |
| `onnxruntime` | 1.28.0 | **1.28.0** (2026-07-25) | ✓ to'g'ri. `requires_python >=3.11`; `cp313` manylinux_2_28 x86_64 g'ildiragi BOR ✓ |
| `opencv-python-headless` | 4.14.0.94 (5.x EMAS) | **4.14.0.94** (2026-07-29) | ✓ **CLAUDE.md HAQ**: 5.0.0.93 — 2026-07-02, ya'ni 4.14 undan KEYIN chiqqan. 4.x hamon tirik liniya |
| `timm` | 1.0.28 | **1.0.28** (2026-07-11) | ✓ Apache-2.0 |

### B.1 (Q4) — Litsenziya bo'linishi: TASDIQLANDI va endi **STRUKTURAVIY**

Bu fayldagi eng katta xavf, shuning uchun to'rt mustaqil manbadan
tekshirildi. **CLAUDE.md ning da'vosi to'g'ri — va 1.9.x da ahvol
CLAUDE.md tasvirlaganidan ancha yaxshiroq.**

| Manba | Nima dedi |
|---|---|
| PyPI `rfdetr` 1.9.1 `info.license` | `"Apache License 2.0"` |
| PyPI klassifikatori | `License :: OSI Approved :: Apache Software License` |
| GitHub API `roboflow/rf-detr` | `license.spdx_id = "Apache-2.0"`, `archived: false`, `pushed_at: 2026-08-04`, 8868 yulduz |
| `LICENSE` fayli (`develop`) | Apache License, Version 2.0 matni |
| README `## License` | *«The open-source `rfdetr` package and Apache-designated model weights are licensed under Apache License 2.0… Plus components, including the `rfdetr_plus` extension and RF-DETR-XL / RF-DETR-2XL detection models, are licensed under PML 1.0.»* |

`[VERIFIED: pypi.org + api.github.com/repos/roboflow/rf-detr + raw LICENSE + raw README — hammasi 2026-08-05]`

README model jadvali litsenziyani variant-boshiga ustun qilib beradi:

| Variant | Sinf | Ruxsat | COCO AP50 | Rezolyutsiya | Litsenziya |
|---|---|---|---|---|---|
| N | `RFDETRNano` | ✅ | 67.6 | 384×384 | Apache 2.0 |
| S | `RFDETRSmall` | ✅ | 72.1 | 512×512 | Apache 2.0 |
| M | `RFDETRMedium` | ✅ | 73.6 | 576×576 | Apache 2.0 |
| L | `RFDETRLarge` | ✅ | 75.1 | 704×704 | Apache 2.0 |
| XL | `RFDETRXLarge` | ⛔ **TAQIQ** | 77.4 | 700×700 | **PML 1.0** |
| 2XL | `RFDETR2XLarge` | ⛔ **TAQIQ** | 78.5 | 880×880 | **PML 1.0** |

**MUHIM YANGILIK — 1.9.x da PML komponenti ALOHIDA PAKETGA
AJRATILGAN.** CLAUDE.md buni bilmaydi, chunki u `1.8.3` davridan.

| Xususiyat | Qiymat |
|---|---|
| Paket nomi | **`rfdetr-plus`** — `rfdetr` dan BOSHQA distribution |
| Versiya | `1.0.2` |
| `license_expression` | **`LicenseRef-PML-1.0`** — mashina o'qiy oladigan, OSI'ga kirmaydigan havola |
| `requires_dist` | `rfdetr<2,>=1.6.0` |
| Homepage | `github.com/roboflow/rf-detr-plus` → GitHub API **`404 Not Found`** (ochiq emas) |
| `rfdetr` dan qanday keladi | FAQAT `rfdetr_plus<2.0.0,>=1.0.1; extra == "plus"` orqali |

`[VERIFIED: pypi.org/pypi/rfdetr-plus/json + api.github.com/repos/roboflow/rf-detr-plus → 404 — 2026-08-05]`

**Buning loyiha uchun ma'nosi katta va u rejaga aylanishi kerak:**

1. **PML kodi tasodifan kirib qololmaydi.** U `rfdetr` ichida emas —
   `pip install rfdetr` PML hech nima keltirmaydi. Faqat
   `pip install rfdetr[plus]` deb ATAYIN yozilsa keladi.
2. **Litsenziya xavfi endi *intizom* emas, *lockfile invarianti*.**
   «XLarge ishlatmang» eslatmasi o'rniga tekshiriladigan shart:
   `uv.lock` da `rfdetr-plus` **yo'q**.
3. Ikkinchi, kuchliroq darvoza: o'rnatilgan har bir distribution
   metadata'sida `License-Expression` / `Classifier: License` o'qilib,
   `LicenseRef-*` (OSI bo'lmagan) topilsa test yiqiladi. Bu kelajakdagi
   noma'lum proprietar paketni ham ushlaydi, faqat `rfdetr-plus` ni emas.
4. `ultralytics` (AGPL — CLAUDE.md TAQIQ) xuddi shu darvozaning
   ro'yxatiga qo'shiladi. Bitta test ikkala qoidani qo'riqlaydi.

**Yon topilma:** segmentatsiya jadvalida `RF-DETR-Seg-XL` va `-Seg-2XL`
**Apache 2.0** — PML faqat *detection* XL/2XL ga tegishli. Taqqoslash
jadvalida `LW-DETR-X` (Apache-2.0) AP50 = 76.9, ya'ni PML bo'lgan
RF-DETR-XL ning 77.4 iga juda yaqin: **aniqlik shiftiga yetganda ham
PML ga o'tish shart emas.** ⚠ `rfdetr` paketi LW-DETR sinflarini
eksport qiladimi — tekshirilmadi. `[LOW confidence — README taqqoslash
jadvalidan o'qildi, paket API'si sinalmadi]`

### B.2 (Q4b) — ONNX eksport yo'li va ⚠ **post-processing ONNX grafida YO'Q**

Rasmiy hujjatdan (`rfdetr.roboflow.com/latest/learn/export/`):

```python
# TRENING image'ida bajariladi, prod'da emas
from rfdetr import RFDETRMedium
model = RFDETRMedium(pretrain_weights="<path/to/checkpoint.pth>")
model.export()          # -> output/inference_model.onnx
```

| Argument | Standart | Ma'nosi |
|---|---|---|
| `output_dir` | `"output"` | Chiqish papkasi |
| `opset_version` | `17` | ONNX operator set |
| `batch_size` | `1` | Bizga aynan shu kerak |
| `shape` | `None` | `(height, width)` |

Kerakli extra: `pip install "rfdetr[onnx]"`.
`[CITED: rfdetr.roboflow.com/latest/learn/export/]`

⚠⚠ **ENG MUHIM TEXNIK TAFSILOT — va u eng oson o'tkazib yuboriladigan
joy.** Eksport qilingan graf **xom tenzor** qaytaradi:

> *«The model returns raw tensors: `dets` (normalized `cxcywh` boxes) and
> `labels` (unnormalized logits). You must apply sigmoid activation,
> remove the background class column, and convert box coordinates
> yourself.»* `[CITED: rfdetr.roboflow.com/latest/learn/export/]`

Ya'ni `onnxruntime` chaqiruvi bilan `sv.Detections` orasida **qo'lda
yoziladigan post-processing** bor: sigmoid → background ustunini olib
tashlash → `cxcywh` (normalangan) dan `xyxy` (piksel) ga o'tkazish →
confidence bo'yicha filtr. Bu ~20 satr, lekin:

- **background ustunini noto'g'ri olib tashlash BARCHA klass ID'larini
  bittaga suradi va jimgina noto'g'ri javob beradi** — istisno
  tashlanmaydi, faqat «odam» o'rniga «boshqa narsa» chiqadi;
- `rfdetr` ning o'z post-processing kodi ishlatilmaydi, chunki u torch
  talab qiladi (§B.0);
- shuning uchun bu **§Validation Architecture da alohida birlik test
  bilan qoplanishi shart** — kirishi qo'lda yasalgan tenzor, kutilgan
  chiqishi qo'lda hisoblangan quti. Bu «model to'g'rimi» degan savol
  emas, «arifmetika to'g'rimi» degan savol, ya'ni **real kadrsiz ham
  to'liq isbotlanadi**.

Kirish tayyorlash (rasmiy misoldan): `resize(w,h)` → `/255.0` →
ImageNet `mean=[0.485,0.456,0.406]`, `std=[0.229,0.224,0.225]` →
`transpose(2,0,1)` → `expand_dims(0)`; kirish nomi `"input"`.
Rezolyutsiyani `session.get_inputs()[0].shape[2:4]` dan **o'qib olish**
kerak, qattiq yozib qo'yish emas — model varianti almashsa kod
o'zgarmaydi.

⚠ `shape` argumenti ixtiyoriy qiymat qabul qiladimi yoki 56 ga
karrali bo'lishi shartmi — **tekshirilmadi**. Reja `shape` ni standart
holida qoldirsin (variantning o'z rezolyutsiyasi) va o'zgartirish kerak
bo'lsa o'sha paytda o'lchasin. `[LOW confidence]`

### B.3 (Q5) — CPU kechikishi: ⚠ **bu fazaning chegarasi EMAS**

ROADMAP kechikishni «o'lchang, taxmin qilmang» deb belgilagan. O'lchov
o'rniga men avval **arifmetikani** qildim va u savolni ahamiyatsiz
qilib qo'ydi.

**Birinchi — README raqamlari CPU raqamlari EMAS:**

> *«All latency numbers were measured on an NVIDIA T4 using TensorRT,
> FP16, and batch size 1.»* `[CITED: rf-detr README]`

Ya'ni jadvaldagi `Nano = 2.3 ms` — **T4 GPU + TensorRT**. Uni Contabo
EPYC'ga taalluqli deb o'qish xato bo'lardi.

**Ikkinchi — jamoa tomonidan aytilgan CPU raqamlari:**

| Manba | O'lchov |
|---|---|
| `roboflow/rf-detr` issue #285 muhokamasi | RF-DETR Nano @320² CPU'da **~180 ms** |
| `roboflow/rf-detr` issue #641 | `RFDETRSegNano` @312² CPU'da **~200 ms** |

`[LOW-MEDIUM confidence — GitHub issue muhokamasidan, WebSearch orqali;
qaysi CPU ekani noma'lum, EPYC'da o'lchanmagan]`

**Uchinchi — 4-fazadan kelgan haqiqiy hajm:**

`04-RESEARCH.md` §D.11: `25 kamera × 7 slot = 175 kadr/kun/bozor`.

| Faraz | Kadr/kun | Bir kadr | Kunlik CPU vaqti |
|---|---|---|---|
| Nano @384², ~180 ms | 175 | 0,18 s | **~32 soniya** |
| Large @704², ~10× sekinroq (~1,8 s) | 175 | 1,8 s | **~5,3 daqiqa** |
| Large + 3×3 tiling (SAHI) | 1575 | 1,8 s | **~47 daqiqa** |
| Yuqoridagining 10 bozori | 15 750 | 1,8 s | **~7,9 soat** |

**Xulosa: MVP miqyosida kechikish chegara emas.** Bitta bozor uchun
eng og'ir ssenariy ham kunlik ~47 daqiqa CPU — 4–6 vCPU li VPS'da bu
bitta yadroning bir qismi, va ish **partiyali va vaqtga bog'liq emas**
(kadr ertalab olinadi, hisobot kun oxirida kerak). Ya'ni:

1. **Model variantini kechikish emas, ANIQLIK tanlaydi.** Standart
   tanlov — eng kattasi (`RFDETRLarge`, Apache-2.0), chunki uning narxi
   arzon. CLAUDE.md ning «RF-DETR-Small, kerak bo'lsa Large» tavsiyasi
   teskari yo'nalishda optimallashtiradi.
2. **Tiling/SAHI qarori ham kechikish bilan bloklanmaydi** — u
   ~3–9× qimmatroq, lekin baribir byudjet ichida. Uni **aniqlik**
   o'lchovi hal qilsin (kichik rastalar), tezlik emas.
3. Sozlama sifatida qoladigan narsa: `intra_op_num_threads` ≈ vCPU
   soni va `providers=["CPUExecutionProvider"]` ATAYIN yoziladi.
4. ⚠ Chegara **10+ bozorda** paydo bo'ladi (7,9 soat/kun). O'shanda
   javob — model kichraytirish emas, **gorizontal worker** yoki
   `timm` krop-klassifikatori (§E). Bu v2 masalasi.

**Shu sababli reja «EPYC'da benchmark» ni darvoza qilib qo'ymasin.**
U foydali o'lchov (va `test_inference_budget.py` sifatida yozilishi
kerak — kadr boshiga vaqtni o'lchab, konfiguratsiyadagi byudjetdan
oshsa yiqiladi), lekin **fazani bloklamaydi**, chunki natija qanday
chiqishidan qat'i nazar arxitektura o'zgarmaydi.

### B.4 (Q6) — `supervision.PolygonZone`: aynan mos, lekin uchta tuzoq bilan

API (rasmiy hujjatdan, `supervision` 0.30.0):

```python
class PolygonZone:
    def __init__(
        self,
        polygon: npt.NDArray[np.int64],
        triggering_anchors: Iterable[Position] = (Position.BOTTOM_CENTER,),
    ): ...
    def trigger(self, detections: Detections) -> npt.NDArray[np.bool_]: ...
    # + `current_count`
```

`PolygonZoneAnnotator(zone, color, thickness, opacity, ...)` →
`annotate(scene, label) -> np.ndarray` — bu **nazoratchiga
ko'rsatiladigan belgilangan dalil rasmini** beradi (§C).
`[CITED: supervision.roboflow.com/latest/detection/tools/polygon_zone/]`

**Tuzoq 1 — poligon PIKSELDA, bizniki 0..1 da.** Konstruktor
`npt.NDArray[np.int64]` kutadi, AI-01 esa normalangan 0..1 saqlashni
talab qiladi. Bu qarama-qarshilik emas, **chegara**: baza 0..1 saqlaydi,
`PolygonZone` yaratishdan oldin `(x*W, y*H)` ga aylantiriladi. Aynan shu
konversiya §A.2 dagi «kamera rezolyutsiyasi o'zgarsa zona omon qoladi»
kafolatining mexanizmi. Uni **sof funksiya** qilib ajratish shart —
u real kadrsiz to'liq testlanadi.

**Tuzoq 2 — `triggering_anchors` standarti `BOTTOM_CENTER` va bu
BIZNING masalaga to'g'ri kelmasligi mumkin.** `BOTTOM_CENTER` odam
uchun mantiqiy (oyoq yerda). Lekin «rastada mol bormi?» savolida
aniqlangan obyekt stol ustidagi savat bo'lishi mumkin va uning
bottom-center'i qo'shni zonaga tushishi mumkin. Variantlar:
`Position.CENTER`, bir nechta ankor birga, yoki umuman ankor emas —
**quti bilan poligonning kesishish YUZASI** (`IoU`/overlap ulushi).
`PolygonZone` yuza asosida ishlamaydi.

**Tavsiya (Claude ixtiyorida):** boshlang'ich standart —
`triggering_anchors=(Position.CENTER, Position.BOTTOM_CENTER)`, va
ankor to'plami **sozlama** bo'lsin, chunki to'g'ri javobni faqat real
kadr aytadi. Bu 4-fazaning `light_mode` bilan bir xil naqsh: mexanizm
quriladi va o'lchanadi, QIYMAT keyin sozlanadi.

**Tuzoq 3 — rasmiy misol `ultralytics` ishlatadi.** Hujjatdagi to'liq
misol `from ultralytics import YOLO` bilan boshlanadi — bu loyihada
**TAQIQLANGAN (AGPL)**. Misolni ko'chirib olish AGPL paketini
`pyproject.toml` ga olib kiradi. `sv.Detections` ni xom ONNX
chiqishidan qo'lda qurish kerak (§B.2). §B.1 dagi litsenziya darvozasi
aynan shu xatoni ushlaydi.

**Nimani QO'LDA YOZMASLIK kerak:** nuqta-poligon ichidami testi
(`cv2.pointPolygonTest` ustidagi mantiq), zona hisoblagichi va
annotator. Bularning hammasi `supervision` da bor va MIT.

### B.5 (Q7) — «AI javobi hech qachon o'zgartirilmaydi» — KELISHUV emas, SXEMA

Loyihada bu naqsh **ikki marta** ishlatilgan va uchinchi marta shu
yerda ishlatilishi kerak. Mavjud mexanizmlar (o'qildi, ixtiro
qilinmadi):

| Mexanizm | Qayerda | Nima qiladi |
|---|---|---|
| `attach_immutability_trigger(table, function, name)` | `migrations/helpers.py:269` | `BEFORE UPDATE OR DELETE ... FOR EACH ROW` qo'riqchi |
| `uq_snapshots_billable_anchor` | `models/snapshot.py:699` | `UNIQUE (id, is_billable)` — 5-faza uchun ATAYIN qo'yilgan langar |
| `TimestampMixin` NING YO'QLIGI | `models/snapshot.py` | «`updated_at` — bu qatorni tahrirlash mumkin degan yolg'on va'da» |

`[VERIFIED: manba kodi o'qildi — migrations/helpers.py:269-310, packages/sbozor-core/sbozor_core/models/snapshot.py:1-25,630-712]`

**Tavsiya etilgan shakl — ikkita AYRIM jadval:**

```
occupancy_events        -- AI ning javobi. O'ZGARMAS.
  id, market_id, snapshot_id, snapshot_is_billable, camera_zone_id,
  zone_version, verdict ('occupied'|'empty'|'uncertain'),
  confidence numeric, model_version, thresholds_version,
  detected_at
  -> FK (market_id, snapshot_id) ...            (tenant kompozit FK)
  -> FK (snapshot_id, snapshot_is_billable)
         REFERENCES snapshots (id, is_billable) (D-16 langari)
  -> CHECK (snapshot_is_billable)               (yaroqsiz kadr IMKONSIZ)
  -> UNIQUE (market_id, snapshot_id, camera_zone_id, model_version)
  -> trg_occupancy_event_immutable (BEFORE UPDATE OR DELETE)
  -> TimestampMixin YO'Q

zone_reviews            -- Nazoratchining qarori. ALOHIDA yozuv.
  id, market_id, occupancy_event_id, reviewer_id, queue_kind
  ('uncertain'|'blind_audit'), human_verdict, reviewed_at,
  shown_ai_verdict boolean NOT NULL
```

Nima uchun aynan shunday:

1. **`verdict`/`confidence` ustunlari `UPDATE` bilan yangilanmaydi** —
   qo'riqchi trigger buni `RAISE EXCEPTION` bilan rad etadi. `tariff`
   dagi triggerdan farqi: u faqat *o'tmishdagi* qatorni himoya qiladi,
   bu yerda esa **shartsiz** — AI javobi hech qachon tahrirlanmaydi.
2. **Nazoratchi qarori boshqa jadvalda**, ya'ni «ustiga qo'yish» —
   `UPDATE` emas, `INSERT`. Yakuniy javob **hisoblanadigan ko'rinish**:
   `COALESCE(review.human_verdict, event.verdict)`. Bu 2-fazadagi
   «qoldiq har doim hisoblanadigan ko'rinish» qoidasining takrori.
3. **`model_version` + `thresholds_version` yoziladi**, aynan
   `snapshots.quality_thresholds_version` sababiga ko'ra: modelni
   almashtirish o'tmishdagi javoblarni RETROAKTIV o'zgartirmasin.
   `UNIQUE (..., model_version)` esa yangi model bilan qayta ishlashni
   *yangi qator* qiladi, eskisini o'chirmaydi — ya'ni «eski model
   nima degan edi?» savoli har doim javobli. **Bu §E dagi
   yaxshilanishni o'lchash mexanizmining o'zi.**
4. **`zone_version` yoziladi** (§A.2) — poligon o'zgargandan keyin eski
   dalil qaysi poligonga tegishli ekani ma'lum qoladi.
5. `shown_ai_verdict` ustuni — §C dagi ko'r auditning **strukturaviy**
   isboti.

⚠ **Reja `occupancy_events` ni `AUDITED_TABLES` reyestriga
qo'shmasin.** Audit trigger'i `AFTER INSERT OR UPDATE OR DELETE` —
kuniga 175 kadr × ~30 zona = ~5000 qator/kun/bozor audit yozuvini
ikkilantirardi, va o'zgarmas jadval uchun audit ma'nosiz (o'zgarish
bo'lmaydi). `zone_reviews` esa **audit qilinsin** — u insonning
moliyaviy oqibatli qarori.

---

## C. Nazoratchi tasdig'i va ko'r audit (AI-03, AI-04, AI-06)

> Bu fazaning eng muhim loyihalash bo'limi. AI-04 — UI tafsiloti emas:
> u **butun mahsulotning yagona xolis o'lchov asbobi**. Agar u noto'g'ri
> qurilsa, «AI aniqligi 94%» degan raqam chiqadi, lekin u hech nimani
> anglatmaydi — va buni hech kim sezmaydi.

### C.8 (Q9) — Ko'r audit (AI-04): xolislikning beshta dushmani

Ko'r auditning maqsadi bitta: **AI ning aniqligini xolis baholash**.
Xolislikni buzadigan beshta yo'l bor va ularning har biri alohida
qarshi chora talab qiladi. Agar bittasi ochiq qolsa, chiqqan raqam
haqiqiy aniqlikdan **yuqori** bo'ladi — ya'ni xato har doim
xushomadgo'ylik tomonga og'adi.

| # | Dushman | Nima bo'ladi | Qarshi chora |
|---|---|---|---|
| 1 | **Ankorlash / avtomatizatsiya tarafkashligi** | Nazoratchi AI javobini ko'rsa, unga qo'shilib ketadi | Javob API'da UMUMAN yuborilmaydi (C.8.2) |
| 2 | **Tanlanma tarafkashligi** | Namuna faqat «noaniq» lardan yoki faqat kunduzgi slotlardan olinsa, natija umumlashmaydi | Namuna doirasi = BARCHA `is_billable` zona-hodisalari |
| 3 | **Ikki navbatning ifloslanishi** | Bir zona avval «noaniq» navbatida ko'rilib, keyin auditda chiqsa — nazoratchi eslaydi | O'zaro istisno (C.8.3) |
| 4 | **Namunani keyin tahrirlash** | «Bu kadr tushunarsiz edi, o'tkazib yuboraman» → qiyin holatlar namunadan chiqib ketadi | Namuna tortilganda MUZLATILADI; javobsiz band «javobsiz» deb hisobotga kiradi |
| 5 | **Nazoratchining o'zi ishonchsiz** | Inson javobi shovqin bo'lsa, «haqiqat» ham shovqin | Takroriy band bilan ichki mosligi o'lchanadi (C.8.5) |

Ankorlash effekti taxmin emas — o'lchangan hodisa. Hisob-kitob
patologiyasi bo'yicha yaqinda chiqqan ishda AI maslahati ko'rsatilganda
mutaxassislarning qaroriga **statistik ahamiyatli musbat siljish**
qayd etilgan va effekt **vaqt bosimi ostida kuchaygan**; boshqa
tadqiqotda ilgari to'g'ri bo'lgan mustaqil qarorlarning **~7%** i
noto'g'ri AI maslahati tufayli teskarisiga o'zgargan.
`[CITED: arxiv.org/abs/2603.11821 — «Stuck on Suggestions: Automation
Bias, the Anchoring Effect…»; melba-journal.org/pdf/2026:007.pdf]`
`[MEDIUM confidence — boshqa domen (tibbiyot), lekin mexanizm umumiy]`

Vaqt bosimi bandiga alohida e'tibor: **kunlik byudjetli navbat aynan
vaqt bosimi yaratadi.** Ya'ni AI-03 ning byudjeti AI-04 ning
ko'rligini yanada muhimroq qiladi.

#### C.8.1 — «Tekshiriladigan darajada tasodifiy» nimani anglatadi

«Tasodifiy» degan da'vo tekshirilmasa, u da'voligicha qoladi. Talab —
**boshqa odam o'sha namunani qayta chiqara olishi** va uning
tanlanmaganini ko'rishi.

⚠ Sodda yechim — `ORDER BY random() LIMIT n` — **yaramaydi**: u qayta
chiqarilmaydi, ya'ni tekshirib bo'lmaydi.

⚠ Ikkinchi sodda yechim — `setseed()` bilan seed saqlash — yaxshiroq,
lekin **seedni tanlagan odam uni bir necha marta sinab ko'rishi mumkin**
(«bu namunada xato ko'p chiqdi, boshqa seed bilan qayta tortaman»).

**Tavsiya — hosila seed + deterministik hash tartibi:**

```sql
-- Seed TANLANMAYDI, HOSILA qilinadi:
--   seed = digest(market_id || business_date || round_no, 'sha256')
-- Namuna = hash bo'yicha eng kichik n ta qator:
SELECT id FROM <frame>
ORDER BY digest(id::text || :seed, 'sha256')
LIMIT :n
```

Nima uchun bu tekshiriladigan:

- **Seed tanlanmaydi** — u `market_id` + `business_date` + tur raqamidan
  hosila, ya'ni «boshqa seed sinab ko'rish» degan harakat mumkin emas.
- **Qayta chiqariladi** — test namunani qayta hisoblab, bazadagi
  yozuv bilan **aynan** mosligini tasdiqlaydi
  (`test_blind_audit_sample_is_reproducible.py`).
- **Doira muzlatiladi** — `audit_rounds` qatorida `frame_size`,
  `frame_predicate_hash`, `drawn_at` saqlanadi. Doira keyin o'zgarsa
  (kadrlar qo'shilsa), eski tur o'zgarmaydi.

`[ASSUMED — bu men taklif qilayotgan naqsh; bevosita manbadan
ko'chirilmagan. Lekin uning ikkala xossasi (hosila seed, qayta
hisoblanadigan tartib) testlanadigan, ya'ni da'vo emas, o'lchov]`

#### C.8.2 — «Tekshiriladigan darajada ko'r» — uchta qatlam

Ko'rlikni «UI ko'rsatmaydi» deb ta'minlash **yetarli emas** — UI
o'zgaradi, va hech qanday test uni ushlamaydi. Uchta qatlam kerak:

**1-qatlam — API javobida maydon UMUMAN yo'q.** `queue_kind =
'blind_audit'` bo'lgan element uchun serializer `verdict`,
`confidence`, `model_version` maydonlarini **chiqarmaydi** (`None`
qilib emas — kalitning o'zi bo'lmaydi). Test: javobni rekursiv
skanerlab, taqiqlangan kalitlar yo'qligini tasdiqlash. Bu 4-fazadagi
«alertga kadr rasmi biriktirilmaydi» testining aynan shakli.

**2-qatlam — sxema darajasida yozib qo'yish.**

```
CHECK (queue_kind <> 'blind_audit' OR shown_ai_verdict = false)
```

Ya'ni «ko'r audit, lekin javob ko'rsatilgan» qator **mavjud bo'la
olmaydi**.

**3-qatlam — javob yozilgandan KEYIN oshkor qilish, va javobni
o'zgartirib bo'lmaslik.** UI nazoratchi javob bergandan so'ng AI
javobini ko'rsatishi mumkin (bu foydali — nazoratchi o'rganadi va
motivatsiya oladi). Lekin `zone_reviews.human_verdict` ga ham
**o'zgarmaslik triggeri** qo'yiladi, ya'ni oshkor qilingandan keyin
javobni «tuzatish» imkonsiz. Shu bilan hatto UI sizib ketsa ham
**yozilgan javob ifloslana olmaydi**.

#### C.8.3 — Ikki navbatning ifloslanishi

Qoida: **bir `occupancy_event` ko'pi bilan bitta navbatda bo'ladi.**
Amalga oshirish — `review_assignments` jadvali va
`UNIQUE (occupancy_event_id)`. Ya'ni ikkinchi navbatga qo'shish urinishi
DB xatosi beradi, kelishuv emas.

Tartib ham muhim: **avval ko'r audit namunasi tortiladi, keyin noaniq
navbat quriladi.** Teskari tartibda audit doirasi «noaniq» lardan
tozalangan bo'lardi va bu 2-dushman (tanlanma tarafkashligi) —
aniqlik sun'iy ko'tarilardi, chunki eng qiyin holatlar o'lchovdan
chiqib ketardi.

⚠ **Doira BARCHA `is_billable` zona-hodisalarini o'z ichiga oladi** —
`occupied`, `empty` VA `uncertain`. «Faqat ishonchli javoblarni
tekshiraylik» degan qisqartma o'lchovni ma'nosiz qiladi.

#### C.8.4 — Namuna hajmi va nima e'lon qilinadi

Nisbat uchun ishonch oralig'i: kichik `n` va chetdagi `p` da
**Wald oralig'i (odatiy `p ± 1.96·√(p(1-p)/n)`) ishonchsiz** — Wilson
score oralig'i sezilarli darajada yaxshiroq qoplama beradi.
`[CITED: corplingstats.wordpress.com — Wilson intervals; arxiv.org/pdf/2503.01747
«Don't Use the CLT in LLM Evals With Fewer Than a Few Hundred Datapoints»]`
`[MEDIUM-HIGH confidence — bu standart statistika]`

Kerakli hajm (±5 f.p., 95%):

| Haqiqiy aniqlik | Taxminiy `n` |
|---|---|
| ~50% (eng yomon holat) | ~384 |
| ~90% | ~138 |
| ~95% | ~73 |

**Tavsiya etilgan standart:** kuniga **30 ta ko'r audit bandi**.
Bir haftada ~210, o'ttiz kunda ~900 — ya'ni **oylik hisobot ±2–3 f.p.
aniqlikda**, haftalik hisobot ±5–7 f.p. da. Bu nazoratchi uchun
real yuk (30 ta rasm ≈ 10–15 daqiqa).

⚠ **«Aniqlik» yolg'iz ko'rsatkich sifatida E'LON QILINMASIN.** Agar
rastalarning 90% i band bo'lsa, «har doim band» deb javob beradigan
soxta model 90% aniqlik oladi. Shuning uchun hisobot **chalkashlik
matritsasi** bo'lishi shart va u ROADMAP ning 8-faza SC#2 si bilan
aynan mos keladi:

| | Inson: band | Inson: bo'sh |
|---|---|---|
| **AI: band** | to'g'ri | ⚠ **«band deb xato» — NIZO xavfi** (sotuvchidan nohaq patta) |
| **AI: bo'sh** | ⚠ **«bo'sh deb xato» — YO'QOTISH** | to'g'ri |

Bu ikki xato **teng emas**: «band deb xato» sotuvchi bilan nizo
keltiradi va mahsulotning ishonchini buzadi; «bo'sh deb xato» esa
faqat pul yo'qotadi. Hisobotda ikkalasi **alohida** ko'rsatiladi,
har biri Wilson oralig'i bilan. Bazaviy bandlik ulushi ham yoziladi —
usiz «94%» raqami o'qilmaydi.

#### C.8.5 — Nazoratchining o'zini o'lchash

«Haqiqat» insondan kelayotgan bo'lsa, insonning ishonchliligi ham
o'lchanishi kerak. Eng arzon usul — **takroriy band**: audit
namunasining ~10% i **oldin ko'rilgan** bandlardan qayta olinadi
(bir necha kun oralig'i bilan) va nazoratchining o'ziga-o'zi mosligi
hisoblanadi. Agar ichki moslik 100% dan sezilarli past bo'lsa,
AI ning o'lchangan aniqligining shifti ham shu darajada past —
va buni bilish shart.

Bu tashqi «gold standard» talab qilmaydi, shuning uchun **real kadrsiz
ham ishlaydi va birinchi kundan yoqilishi mumkin**. `[ASSUMED — bu
crowdsourcing amaliyotidagi standart usul (gold/honeypot bandlari),
lekin bu loyiha uchun men taklif qilyapman]`

### C.9 (Q8) — Noaniq navbat (AI-03): byudjet, ustuvorlik, «hammasini tasdiqlash» yo'qligi

**Ustuvorlik — ikki maqsad qarama-qarshi va tanlov ochiq yozilishi
kerak:**

| Maqsad | Qaysi bandni birinchi qo'yadi |
|---|---|
| Mahsulot qiymati | Ko'rilishi **hisob-kitobni o'zgartiradigan** bandlar (biriktirilgan sotuvchisi bor rasta) |
| Trening qiymati | **Chegaraga eng yaqin** confidence — klassik uncertainty sampling |

**Tavsiya:** avval **billing ta'siri**, ichida **chegaraga yaqinlik**.
Sabab: mahsulotning va'dasi — patta to'g'ri yig'ilishi; trening
ma'lumoti shundan kelib chiqadigan yon mahsulot. Teskari tartib
nazoratchining vaqtini modelni yaxshilashga sarflab, bugungi hisobni
noto'g'ri qoldirardi.

**«Hammasini tasdiqlash» tugmasi yo'qligi — bu ham UI qoidasi emas,
API qoidasi bo'lishi kerak:**

1. Ommaviy endpoint **mavjud emas** — bitta so'rov = bitta qaror.
   Test: OpenAPI sxemasini skanerlab, `zone_reviews` yaratadigan
   ro'yxat/massiv qabul qiluvchi endpoint yo'qligini tasdiqlash.
2. Har qaror **ko'rilgan dalil rasmiga** bog'lanadi — ya'ni rasm
   yuklanmasdan qaror yozilmaydi.
3. *(Ixtiyoriy, tavsiya etiladi)* «shoshib bosish» detektori: agar
   ketma-ket qarorlar orasidagi vaqt juda kichik bo'lsa, seans
   belgilanadi. Bu bloklamaydi, faqat hisobotda ko'rinadi.

**⚠ Trening dataseti haqida jiddiy ogohlantirish.** AI-03 «tasdiqlangan
javoblar fine-tuning dataseti bo'ladi» deydi. Lekin **noaniq navbatidan
kelgan javoblar — tanlanma jihatdan og'gan namuna** (faqat qiyin
holatlar). Faqat shularga o'rgatish modelni yomonlashtirishi mumkin.

**Yechim va u bepul:** trening to'plami = *noaniq navbat javoblari*
(qiyin holatlar) **+ ko'r audit javoblari** (tasodifiy, ya'ni oson
holatlar ham bor). Ko'r audit allaqachon aynan kerakli tasodifiy
qatlamni ishlab chiqaradi.

**⚠⚠ Lekin bu yangi tuzoq yaratadi:** ko'r audit ma'lumoti trening
uchun ishlatilsa, u **toza test to'plami bo'lmay qoladi** — model o'zi
o'rgangan bandlarda baholanadi va aniqlik soxta ko'tariladi.

**Yechim (arzon va strukturaviy):** har bir audit bandi tortilgan
paytda **`purpose ∈ ('eval','train')`** deb belgilanadi, qat'iy
nisbatda (tavsiya: **70% `eval` / 30% `train`**). Aniqlik hisoboti
**faqat `eval`** qatorlardan hisoblanadi va bu qatorlar hech qachon
trening eksportiga tushmaydi. Belgi tortish paytida qo'yilgani muhim —
keyin qo'yilsa, natijani ko'rib turib taqsimlash mumkin bo'lardi.

### C.10 (Q10) — AI-06: tasdiqlanmagan noaniq → «bo'sh», va u qayerda yashaydi

Talab: kun oxirigacha tasdiqlanmagan `uncertain` → `empty`, hisobotda
**alohida belgi** bilan.

**Asosiy qaror: bu HISOBLANADI, YOZILMAYDI.** Ya'ni:

- `occupancy_events` da hech nima o'zgarmaydi (u o'zgarmas);
- `zone_reviews` ga **soxta qator yozilmaydi** — aks holda tizim
  «nazoratchi buni bo'sh deb tasdiqladi» deb yolg'on gapirardi va
  o'sha yolg'on keyin trening datasetiga tushardi;
- yakuniy javob uchta manbali hosila:

```
effective_verdict, resolution_source =
    review mavjud       -> (review.human_verdict, 'human')
    verdict='uncertain' -> ('empty',              'default_empty')
    aks holda           -> (event.verdict,        'ai')
```

**`resolution_source` — hisobotdagi «alohida belgi» ning o'zi.**

⚠ **Xavf yo'nalishini to'g'ri tushunish kerak.** Standart qiymat
«bo'sh», ya'ni **hisob yozilmaydi**. Demak xato *ortiqcha hisob* emas,
**jimgina yo'qotish**. Shuning uchun bu bandning xavfsizlik chorasi
«billing'ga kirib ketmasin» emas (u allaqachon kirmaydi), balki
**«ko'rinmay qolmasin»**:

> Kunlik hisobotda **«N ta zona ko'rilmagani uchun bo'sh deb
> hisoblandi»** degan raqam direktorga ko'rinadi. Agar bu raqam katta
> bo'lsa, demak nazoratchi navbatga ulgurmayapti va bozor pul
> yo'qotmoqda.

Bu raqam nolga teng bo'lsa ham ko'rsatiladi — 4-fazadagi
«yo'qlikka alert» prinsipining aynan takrori.

---

## D. Agregatsiya va billing chegarasi (AI-05)

### D.11 (Q11) — «Birortasi band desa band» — qayerda yashaydi va qanday sinaladi

⚠ **Avval chalkashlikni ochish kerak: bu yerda IKKI xil agregatsiya
bor va ular IKKI xil fazaga tegishli.**

| Daraja | Nima birlashtiriladi | Qoida | EGASI |
|---|---|---|---|
| **1. Kameralararo** | Bitta rasta, bitta slot, bir necha kamera | **Birortasi «band» → band** (AI-05) | **5-faza** |
| **2. Slotlararo** | Bitta rasta, bitta kun, 7 slot | «kamida 2 slotda band, yoki 1 slot + nazoratchi tasdig'i» (BILL-01) | **6-faza** |

Bu chegara ochiq yozilmasa, 5-faza bilmasdan billing qoidasini
amalga oshirib qo'yadi va 6-faza uni ikkinchi marta yozadi. **5-faza
faqat 1-darajani beradi** va chiqishi «rasta X, sana D, slot T da
band edi» degan qator bo'ladi.

**Qoida qayerda yashaydi:** `packages/sbozor-core` ichida **sof
funksiya** — bazada emas, API'da emas.

```python
def aggregate_stall_slot(
    zone_results: Sequence[EffectiveZoneVerdict],
) -> StallSlotVerdict:
    """Bir rastaning bir slotdagi javobi.

    Ustuvorlik: occupied > uncertain > empty > no_coverage
    """
```

Ustuvorlik tartibi to'liq va u talabdagidan uzunroq, chunki
`no_coverage` (§A.3) ham mavjud:

| Kirish (kameralar bo'yicha) | Chiqish | Sabab |
|---|---|---|
| birorta `occupied` | **`occupied`** | AI-05 ning aynan matni |
| `occupied` yo'q, birorta `uncertain` | `uncertain` | kun oxirida C.10 bo'yicha hal bo'ladi |
| hammasi `empty` | `empty` | |
| poligon umuman yo'q | `no_coverage` | «bo'sh» EMAS — §A.3 |

⚠ **Muhim nozik nuqta: `effective` verdictlar birlashtiriladi, xom AI
verdictlari emas.** Ya'ni nazoratchi 2-kamerada «bo'sh» deb tasdiqlagan
bo'lsa, 1-kameraning AI «band» i baribir g'olib bo'ladi — bu to'g'ri,
chunki rasta bir kamerada ko'rinib, boshqasida ko'rinmasligi mumkin.
Inson qarori **o'sha kameraning zonasini** almashtiradi, agregatsiya
qoidasini emas.

**Qanday sinaladi:** bu **sof funksiya ustidagi jadval-testi** —
kameralar soni × verdictlar kombinatsiyasi to'liq sanab chiqiladi
(3 verdict + yo'qlik, 1–4 kamera → o'nlab holat). **Real kadr, model,
hatto baza ham kerak emas.** Ya'ni AI-05 — bu fazaning
**to'liq isbotlanadigan** talabi.

### D.12 (Q12) — Billing langari: MAVJUD, tasdiqlandi, va undan qanday foydalaniladi

**Langar bor va u aytilganidek ishlaydi.** Manba kodidan aynan:

```python
UniqueConstraint("id", "is_billable", name="uq_snapshots_billable_anchor"),
```

va uning yonidagi izoh 5-faza yozishi kerak bo'lgan DDL ni **so'zma-so'z
beradi**:

```sql
snapshot_is_billable boolean NOT NULL DEFAULT true
CHECK  (snapshot_is_billable)
FOREIGN KEY (snapshot_id, snapshot_is_billable)
    REFERENCES snapshots (id, is_billable)
```

`[VERIFIED: packages/sbozor-core/sbozor_core/models/snapshot.py:685-699 —
manba o'qildi]`

Bundan tashqari 4-faza bu shaklni **haqiqiy `postgres:18.4` da
o'lchagan** (`tests/fixtures/billable_probe.py`, 2026-08-04):
`GENERATED ... STORED` ustun ustidagi `UNIQUE` kompozit FK nishoni
bo'la **oladi**, va zond ikkala yo'nalishni ham tekshirgan —
`'dark'` qatorga havola `ForeignKeyViolation` beradi, mavjud `'ok'`
qatorni `'dark'` ga `UPDATE` qilish **ham** rad etiladi.
`[VERIFIED: models/snapshot.py:639-652 izohi]`

**Ya'ni 5-faza uchun bu ish TUGAGAN — faqat ishlatish kerak.** Reja
`occupancy_events` ni aynan shu uch satr bilan qursin (§B.5) va
`04-12` dagi meta-test uslubida **darvoza** qo'ysin: yaroqsiz kadrga
bandlik hodisasini yozish urinishi `ForeignKeyViolation` berishi
kerak. Bu **mock'siz, haqiqiy Postgres'da** o'lchanadi (loyihada
`testcontainers` bor, SQLite TAQIQ).

**Rasta darajasidagi materializatsiya.** 6-faza o'zgarmas hisob
yozadi va BILL-02 «har hisob yozuvidan dalil-kadrlarga o'tish»ni
talab qiladi. Shuning uchun 5-faza kun yopilishida
`stall_slot_occupancy` qatorini materializatsiya qiladi:

```
stall_slot_occupancy
  market_id, stall_id, business_date, slot_time,
  verdict, resolution_source ('ai'|'human'|'default_empty'|'no_coverage'),
  winning_occupancy_event_id   -- «band» degan hodisa; dalilga BIR sakrash
  -> FK (market_id, winning_occupancy_event_id) ...
  -> UNIQUE (market_id, stall_id, business_date, slot_time)
```

Kafolat **tranzitiv tarqaladi**: `stall_slot_occupancy` →
`occupancy_events` → `snapshots (id, is_billable)`. Ya'ni yaroqsiz
kadr **hech qanday zanjir orqali** hisobga yeta olmaydi va buning
uchun yangi mexanizm o'ylab topish shart emas.

⚠ `winning_occupancy_event_id` **`NULL` bo'lishi mumkin** (`empty`,
`no_coverage`, `default_empty` holatlarida) — `CHECK` bilan bog'lansin:
`(verdict = 'occupied') = (winning_occupancy_event_id IS NOT NULL)`.
Bu 4-fazadagi `purged_has_deletion_time` konstraytining aynan shakli.

---

## E. Servis topologiyasi va fine-tuning

### E.13 (Q13) — `cv-service`: uchtaning biri, qo'shimcha emas

CLAUDE.md: *«Servislar soni: aynan 3 ta (core-api, cv-service,
bot-service) — ortiqcha mikroservis bo'linmaydi»*. Ya'ni **`cv-service`
allaqachon rejalashtirilgan uchlikning a'zosi** va uni oqlash shart
emas. Hozir `compose.yaml` da yo'qligi kutilgan holat — u shu fazada
tug'iladi. `[VERIFIED: compose.yaml xizmatlari — db, cache, storage,
migrate, core-api, worker, scheduler, go2rtc, frontend, nginx,
nvr-sim, nvr-sim-rtsp, tests]`

**Mas'uliyat chegarasi:**

| `cv-service` EGASI | `core-api` DA QOLADI |
|---|---|
| ONNX sessiyasi va uning umri | Sxema, migratsiya, RLS |
| Kadr yuklash, `resize`/normalize | `camera_zones` CRUD va poligon API'si |
| Xom tenzor → `sv.Detections` (§B.2) | Navbatlar, `zone_reviews`, hisobotlar |
| `PolygonZone.trigger()` va zona verdicti | Ko'r audit namunasini tortish |
| Dalil rasmini belgilash (`PolygonZoneAnnotator`) | Kun yopilishi va materializatsiya |

**Kadrni qanday oladi: S3 KALITI beriladi, BAYTLAR emas.**
`snapshots.object_key` allaqachon deterministik va saqlangan
(4-faza §D.9). Navbat xabari `{snapshot_id}` bo'ladi, `cv-service`
qatorni o'qib `object_key` ni oladi va S3'dan **o'zi** yuklaydi.
Sabablari:

- baytlarni Valkey orqali uzatish brokerni bo'g'ardi (~500 KB × 175);
- 4-fazaning Valkey'i `--save "" --appendonly no` bilan ishlaydi —
  unga hech qanday muhim ma'lumot ishonib topshirilmaydi;
- `cv-service` ga faqat **o'qish** huquqli S3 rekviziti beriladi.

**Shakl: HTTP xizmat emas, `taskiq` WORKER + minimal FastAPI.**
Ish partiyali va navbatdan keladi, ya'ni core-api uni HTTP bilan
chaqirishi uchun sabab yo'q. Lekin FastAPI ilovasi baribir kerak,
chunki 4-faza **yurak urishi** va `/internal/self-check` mexanizmini
o'rnatgan (`EXPECTED_COMPONENTS`) — `cv-service` o'sha reyestrga
yangi komponent sifatida qo'shilishi kerak, aks holda u jimgina
o'lib qolsa hech kim bilmaydi. Bu FOUND-06 ning tabiiy davomi.

**Ishga tushish tetigi:** kadr muvaffaqiyatli saqlangandan keyin
`detect` taski navbatga qo'yiladi. **Kadr olish bilan bir tranzaksiyada
BOG'LANMAYDI** — aks holda CV nosozligi kadr olishni yiqitardi.
Idempotentlik `UNIQUE (market_id, snapshot_id, camera_zone_id,
model_version)` bilan ta'minlanadi, ya'ni takroriy ishga tushish
dublikat yaratmaydi (4-fazadagi `ON CONFLICT DO NOTHING` naqshi).

⚠ **`quality_verdict <> 'ok'` bo'lgan kadr uchun `detect` UMUMAN
ishga tushmasin** — u `is_billable = false`, ya'ni FK baribir rad
etardi. Buni oldindan filtrlash mumkin bo'lgan xatoni imkonsiz
xatoga aylantirishdan yaxshiroq.

### E.14 (Q14) — Fine-tuning: ⚠ **HITL ma'lumoti RF-DETR ni o'rgata OLMAYDI**

Bu bo'limning eng muhim topilmasi va u AI-03 ning matniga zid
tuyulishi mumkin, shuning uchun ochiq yoziladi.

**Muammo:** RF-DETR — **detektor**. Uni fine-tune qilish uchun
**cheklovchi to'rtburchaklar (bounding box)** kerak: har rasmda «mana
bu yerda odam, mana bu yerda quti». Nazoratchi esa **zona bo'yicha
ikkilik yorliq** beradi: «bu rasta band / bo'sh». Bu ikki xil
ma'lumot va biridan ikkinchisi kelib chiqmaydi.

Ya'ni: **nazoratchining javoblari to'plansa ham, ular bilan RF-DETR ni
fine-tune qilib bo'lmaydi.**

**Bu qarama-qarshilik emas — REQUIREMENTS buni allaqachon hal qilgan.**
`V2-AI-04: Karmana ma'lumotida RF-DETR fine-tuning` — **v2 ro'yxatida**.
`[VERIFIED: .planning/REQUIREMENTS.md:100]` Ya'ni v1 da **trening
bajarilmaydi**, faqat **ma'lumot yig'iladi**.

**Shunda AI-03 ning «fine-tuning dataseti bo'ladi» deganini qanday
o'qish kerak:** yig'ilgan ma'lumot **ikki xil kelajakni** ochiq
qoldirishi kerak, va buning uchun **krop emas, HAVOLA saqlanadi**:

| Kelajak | Nima kerak | HITL ma'lumoti yetadimi |
|---|---|---|
| **`timm` zona-krop klassifikatori** | krop rasmi + `occupied/empty` | ✅ **TO'LIQ YETADI** |
| **RF-DETR fine-tune (V2-AI-04)** | quti annotatsiyalari | ❌ alohida annotatsiya bosqichi kerak |
| **Chegara sozlash** | confidence + haqiqat | ✅ yetadi |

**Shu sababli eksportning shakli:**

`zone_reviews` + `occupancy_events` + `camera_zones` + `snapshots`
allaqachon hamma narsani saqlaydi. Eksport **hosila** bo'ladi va
istalgan vaqtda qayta yaratiladi:

```
export/
  manifest.jsonl     # har satr: snapshot object_key, camera_zone_id,
                     # zone_version, polygon (0..1), human_verdict,
                     # ai_verdict, confidence, model_version,
                     # queue_kind, purpose ('eval'|'train')
  crops/             # hosila: poligonning cheklovchi to'rtburchagi
                     # bo'yicha kesilgan JPEG
```

**Muhim: `crops/` HOSILA, manba emas.** Manba — object_key + poligon.
Shu bilan kelajakda krop qoidasi o'zgarsa (masalan ~10% chegara
qo'shish), ma'lumot **qayta yig'ilmaydi**, faqat qayta hosil qilinadi.
Bu 4-fazadagi «obyekt kaliti deterministik» qaroridan kelib chiqadigan
bevosita foyda.

⚠ `rfdetr[train]` COCO formatidagi datasetni kutadi
(`pycocotools`, `faster-coco-eval` bog'liqliklari shunga ishora
qiladi). `manifest.jsonl` → COCO konvertori **v2 ishi**, chunki
qutilar baribir yo'q. `[MEDIUM confidence — bog'liqliklardan xulosa,
rasmiy dataset hujjati o'qilmadi]`

**Trening image'i (v2, ijaraga olingan GPU):** `rfdetr[train,onnx]` +
torch — **prod image'da HECH QACHON**. §B.0 dagi sabab. Bu compose'da
alohida `profile` bo'lib, standart `docker compose up` da ishga
tushmaydi.

### E.15 (Q15) — `timm` krop-klassifikatori: v2 ishi, LEKIN ilgagi HOZIR qo'yiladi

**Kod hozir yozilmaydi.** Lekin uchta narsa hozir qilinsa, keyin uni
qo'shish **sozlama** bo'ladi, qayta loyihalash emas:

1. **`occupancy_events.model_version`** (§B.5) — klassifikator o'z
   qatorlarini boshqa `model_version` bilan yozadi. Detektor
   qatorlari saqlanadi. Ikkalasi **bir xil `eval` namunasida**
   taqqoslanadi. **Bu — «yaxshilanishni o'lchash mashinasi» ning o'zi.**
2. **Verdict manbasining abstraksiyasi:** zona verdicti «detektor →
   `PolygonZone`» dan chiqadi, lekin interfeys `(snapshot, camera_zone)
   → (verdict, confidence)` bo'lsin. Klassifikator o'sha interfeysning
   ikkinchi amalga oshirilishi bo'ladi.
3. **Eksport formati (E.14)** allaqachon krop + ikkilik yorliq beradi —
   ya'ni `timm` uchun ma'lumot birinchi kundan yig'ila boshlaydi.

Nega bu ehtimoldan yuqori: «stol ustida mol bormi» — bu **klassifikatsiya
masalasi**, detektsiya emas. Detektor COCO klasslarini («person»,
«handbag») qidiradi va bozor rastasidagi savat/qop ularning hech
biriga tushmasligi mumkin. Krop klassifikatori esa aynan bizning
savolga o'rgatiladi va **ancha kam ma'lumot** talab qiladi. CLAUDE.md
buni «v2 accuracy lever» deb ataydi — men bir qadam kuchliroq
aytaman: **agar detektorning aniqligi past chiqsa, javob shu, va
ma'lumot allaqachon yig'ilgan bo'ladi.**

---

## Validation Architecture

> `workflow.nyquist_validation: true` — bu bo'lim majburiy va undan
> `05-VALIDATION.md` hosil qilinadi.

### Markaziy muammo, ochiq aytilgan

4-faza sifat filtrini **sintetik JPEG** bilan sinaydigan qildi va
buning sababini fixture modulining o'zida yozib qoldirdi:

> *«chegara bilan nomlangan fixture testni O'Z FARAZINING AKS-SADOSIGA
> aylantiradi… `frame_rejected_by_filter()` degan fixture "filtr rad
> etadigan kadr" ni yasash uchun filtrning CHEGARASINI bilishi kerak —
> ya'ni u chegarani chegaraning O'ZI bilan tekshiradi va chegara
> noto'g'ri qo'yilgan bo'lsa ham YASHIL qoladi.»*

`[VERIFIED: tests/fixtures/frames.py:1-30 — manba o'qildi]`

**5-fazada aynan shu tuzoqning kuchliroq shakli bor.** «Bu rasta band»
degan sintetik sahna yasab, uni detektordan o'tkazib, «band» degan
javobni kutish — o'zini o'zi tasdiqlash. Loyiha bu shaklni **ikki
marta rad etgan** (2-fazadagi o'ziga-o'zi havola qiluvchi shablon,
3-fazadagi «simdan kadr tortib, sim'ni tasdiqlash»). **Uchinchi marta
rad etilishi kerak.**

### Yechim: CHOK (seam) — `sv.Detections`

Sintetik rasm **idrokni** isbotlay olmaydi. Lekin sintetik
**`sv.Detections`** modeldan keyingi HAMMA narsani isbotlaydi.

```
  kadr  ->  [ONNX sessiya]  ->  xom tenzor  ->  post-proc  ->  sv.Detections
                  ▲                                                  │
          ISBOTLANMAYDI                                              ▼
          (idrok — real kadr kerak)              [ CHOK — testlar shu yerdan kiradi ]
                                                                     │
                                    PolygonZone -> zona verdicti -> occupancy_events
                                    -> agregatsiya -> navbatlar -> ko'r audit -> hisobot
                                                  HAMMASI TO'LIQ ISBOTLANADI
```

Ya'ni: **model chegara qilib ajratiladi**, uning ustidagi da'volar
«uskunasiz isbotlanmaydi» ro'yxatiga ochiq yoziladi, va **qolgan
hamma narsa haqiqiy darvoza oladi.** Bu 4-fazaning aynan strategiyasi
(sim baytlarni boshqaradi; filtr esa sintetik kadrda o'lchanadi) —
faqat chok bir qavat yuqoriroqda.

### Fixture nomlash qoidasi (4-fazadan meros, majburiy)

| ✅ To'g'ri (geometrik/fizik fakt) | ❌ Noto'g'ri (verdict aks-sadosi) |
|---|---|
| `detections_at(boxes=[(0.4,0.5,0.5,0.6)])` | `detections_that_make_zone_occupied()` |
| `polygon_unit_square()` | `polygon_that_catches_the_box()` |
| `review_pairs(ai=[...], human=[...])` | `reviews_with_94_percent_accuracy()` |

Kutilgan natijalar **qo'lda hisoblanadi va testda literal yoziladi** —
tekshirilayotgan funksiyani chaqirib olinmaydi.

### Test Framework

| Xususiyat | Qiymat |
|---|---|
| Backend | `pytest 9.1.1` + `pytest-asyncio` (`asyncio_mode="auto"`) + `testcontainers` (haqiqiy `postgres:18.4`; SQLite **TAQIQ** — RLS yo'q) |
| Frontend (sof funksiya) | `node --test frontend/scripts/*.test.mjs` — **geometriya shu yerda** |
| Frontend (komponent) | `vitest 4.1.10` + `jsdom` + Testing Library |
| Markerlar | mavjudlar yetadi: `sim`, `hardware`, `slow`; **yangi marker `golden`** |
| Tez | `npm run test:fast` |
| To'liq | `npm run test`, `npm run test:sim` |
| Darvoza | `npm run gate` |

⚠ **`gate` byudjeti ochiq band sifatida meros qoldi** (`04-VERIFICATION`
`open_items`): 900 s hujjatlashtirilgan, o'lchov 1009–1174 s bergan.
Egasi aynan **«Phase 5 validation plan»** deb belgilangan. Shu bilan
birga `scripts/check-validation-signoff.mjs::DEFAULT_FILE` hamon
2-fazaga qadalgan — u ham shu fazaning bandi. **Ikkalasi ham Wave 0 ga
kiritilsin.**

### Faza mezonlari → test xaritasi

| SC | Xulq | Tur | Buyruq | Bormi |
|---|---|---|---|---|
| **SC#1** Poligon chiziladi, 0..1, versiyalanadi, ko'p kameraga bog'lanadi | Geometriya + sxema | unit + integration | `node --test frontend/scripts/zone-geometry.test.mjs`; `pytest tests/integration/test_camera_zones_api.py -x` | ❌ W0 |
| **SC#2** Har zona confidence bilan baho oladi; AI javobi **hech qachon** tahrirlanmaydi | Post-proc + o'zgarmaslik | unit + integration | `pytest tests/unit/test_rfdetr_postprocess.py tests/integration/test_occupancy_immutable.py -x` | ❌ W0 |
| **SC#3** Byudjetli, ustuvorlashtirilgan noaniq navbat; «hammasini tasdiqlash» YO'Q | Navbat + API shakli | integration | `pytest tests/integration/test_uncertain_queue.py -x` | ❌ W0 |
| **SC#4** Ko'r audit: AI javobi ko'rsatilmaydi; hisobot **faqat** shu namunadan | Ko'rlik + namuna + hisobot | integration + unit | `pytest tests/integration/test_blind_audit.py tests/unit/test_accuracy_report.py -x` | ❌ W0 |
| **SC#5** Birortasi band → band; tasdiqlanmagan noaniq → bo'sh, **alohida belgi** bilan | Agregatsiya + kun yopilishi | unit + integration | `pytest tests/unit/test_aggregate_stall_slot.py tests/integration/test_day_close.py -x` | ❌ W0 |
| **HAMMASI** | Yagona darvoza | integration | `pytest tests/integration/test_phase5_criteria.py -x` | ❌ W0 |

### Talab → test xaritasi

| REQ | Tekshiriladigan xulq | Buyruq |
|---|---|---|
| AI-01 | `normalize`/`denormalize` aylanma yo'qotishsiz; o'zi bilan kesishgan poligon RAD etiladi; `interpolateRow(a,b,n)` → n ta teng to'rtburchak | `node --test frontend/scripts/zone-geometry.test.mjs` |
| AI-01 | Poligon tahriri **yangi versiya** yaratadi, eskisi qoladi | `pytest tests/integration/test_camera_zones_api.py::test_edit_creates_new_version -x` |
| AI-01 | Nisbat o'zgarsa zona `needs_review` bo'ladi | `pytest tests/integration/test_camera_zones_api.py::test_aspect_change_flags_zone -x` |
| AI-02 | Xom tenzor → quti: sigmoid, background ustuni, `cxcywh`→`xyxy` **qo'lda hisoblangan** natijaga teng | `pytest tests/unit/test_rfdetr_postprocess.py -x` |
| AI-02 | `occupancy_events` ga `UPDATE`/`DELETE` → `RAISE EXCEPTION` | `pytest tests/integration/test_occupancy_immutable.py -x` |
| AI-02 | `quality_verdict<>'ok'` kadrga bandlik hodisasi → `ForeignKeyViolation` | `pytest tests/integration/test_occupancy_billing_fence.py -x` |
| AI-02 | ONNX sessiya **determinstik**: bir xil kirish → bir xil chiqish | `pytest tests/integration/test_onnx_session.py -m sim -x` |
| AI-03 | Ommaviy tasdiqlash endpointi **mavjud emas** (OpenAPI skani) | `pytest tests/integration/test_uncertain_queue.py::test_no_bulk_approve_endpoint -x` |
| AI-03 | Kunlik byudjet oshib ketmaydi; ustuvorlik billing ta'siri bo'yicha | `pytest tests/integration/test_uncertain_queue.py -x` |
| AI-04 | Ko'r audit javobida `verdict`/`confidence` kalitlari **umuman yo'q** (rekursiv skan) | `pytest tests/integration/test_blind_audit.py::test_payload_has_no_verdict_keys -x` |
| AI-04 | Namuna **qayta chiqariladi** — qayta hisoblash bazadagi to'plamga aynan teng | `pytest tests/integration/test_blind_audit.py::test_sample_is_reproducible -x` |
| AI-04 | Doira `uncertain` larni ham **o'z ichiga oladi** | `pytest tests/integration/test_blind_audit.py::test_frame_includes_uncertain -x` |
| AI-04 | Bir hodisa ikki navbatda bo'la olmaydi (DB rad etadi) | `pytest tests/integration/test_blind_audit.py::test_event_cannot_be_in_two_queues -x` |
| AI-04 | `queue_kind='blind_audit'` + `shown_ai_verdict=true` → `CHECK` buzilishi | `pytest tests/integration/test_blind_audit.py::test_blind_implies_not_shown -x` |
| AI-04 | Javob yozilgandan keyin **o'zgartirib bo'lmaydi** | `pytest tests/integration/test_blind_audit.py::test_review_is_immutable -x` |
| AI-04 | Hisobot **faqat `purpose='eval'`** qatorlardan; `train` qatorlar hisobga kirmaydi | `pytest tests/unit/test_accuracy_report.py::test_train_rows_excluded -x` |
| AI-04 | Chalkashlik matritsasi + Wilson oralig'i **qo'lda hisoblangan** qiymatga teng | `pytest tests/unit/test_accuracy_report.py -x` |
| AI-05 | Agregatsiya ustuvorligi — barcha kombinatsiyalar sanab chiqilgan | `pytest tests/unit/test_aggregate_stall_slot.py -x` |
| AI-06 | Tasdiqlanmagan `uncertain` → `empty` + `resolution_source='default_empty'`; `zone_reviews` ga **qator yozilmaydi** | `pytest tests/integration/test_day_close.py::test_unreviewed_uncertain_defaults_to_empty -x` |
| AI-06 | Hisobotda «N ta zona ko'rilmagani uchun bo'sh» soni chiqadi (0 bo'lsa ham) | `pytest tests/integration/test_day_close.py::test_default_empty_count_is_reported -x` |
| **LITSENZIYA** | `uv.lock` da `rfdetr-plus` yo'q; o'rnatilgan hech bir dist `LicenseRef-*` yoki AGPL emas | `pytest tests/unit/test_license_fence.py -x` |

### «Oltin to'plam» — aniqlikni O'LCHASH MASHINASI

Bu — fazaning **haqiqiy mahsuloti**. Aniqlik raqami emas, uni
chiqaradigan mexanizm.

```
tests/fixtures/golden_set/
  manifest.jsonl    # {image_ref, polygon(0..1), true_verdict,
                    #  source: 'synthetic'|'karmana', labeled_by, labeled_at}
  images/
scripts/eval-golden-set.py   # to'plamni to'liq quvurdan o'tkazadi,
                             # chalkashlik matritsasi + Wilson oralig'i chiqaradi
```

Ishlashi:

1. **Bugun** to'plamda faqat `source='synthetic'` yozuvlar bor.
   Test **harness'ni** tekshiradi: buyruq ishlaydi, hisobot shakli
   to'g'ri, matematikasi qo'lda hisoblangan javobga teng.
2. **Aniqlik darvozasi allaqachon yozilgan, lekin UXLAYDI:**

   ```
   karmana_rows = [r for r in manifest if r.source == 'karmana']
   if len(karmana_rows) >= MIN_N:      # aks holda skip
       assert accuracy_lower_wilson_bound >= THRESHOLD
   ```

3. **Real kadrlar kelgan kuni** ular shu papkaga qo'yiladi va
   `source='karmana'` deb belgilanadi. **Kod o'zgarmaydi.** Darvoza
   o'zi uyg'onadi.

Shu bilan «real kadrlar kelganda aniqlik o'lchanishi kerak» degan
va'da **hujjatdagi niyat emas, ishga tushadigan kod** bo'ladi. Bu
4-fazadagi «chegara — parametr, sana in'ektsiya qilinadi» qarorining
aynan analogi.

⚠ **Sintetik yozuvlar `true_verdict` ni FAQAT geometriyadan oladi**
(«bu poligon ichida shu koordinatalarda quti bor»), detektorning
javobidan emas. Aks holda §Validation ning boshidagi tuzoq qaytadi.

### Uskunasiz / real kadrsiz nima isbotlanMAYDI

| Da'vo | Nega isbotlanmaydi | Qanday boshqariladi |
|---|---|---|
| **RF-DETR bozor rastasidagi molni ko'radimi** | COCO klasslari («person», «handbag») o'zbek bozoridagi savat/qopga mos kelmasligi mumkin. Sintetik rasm buni ayta olmaydi | «Oltin to'plam» darvozasi + `05-HUMAN-UAT` bandi. Zaxira yo'l — `timm` klassifikatori (§E.15), ma'lumot allaqachon yig'iladi |
| **`occupied`/`uncertain` confidence chegaralari** | Real taqsimot yo'q | Chegaralar **sozlama** + `thresholds_version` qatorda saqlanadi (§B.5) — sozlash SQL bilan, migratsiyasiz |
| **`triggering_anchors` to'g'ri tanlanganmi** | Real sahna kerak | Sozlama (§B.4); oltin to'plamda ikkala variant taqqoslanadi |
| **Tiling/SAHI kerakmi** | Rastaning kadrdagi piksel o'lchami noma'lum | Byudjet bor (§B.3) — qaror **o'lchovdan keyin**, faza ichida emas |
| **Nazoratchi 30 ta bandni kuniga ulguradimi** | Real odam kerak | `05-HUMAN-UAT` bandi; byudjet **sozlama** |
| **Ankorlash effekti bizning nazoratchida qanchalik kuchli** | Real odam kerak | C.8.5 takroriy bandi buni **vaqt o'tishi bilan o'lchaydi** |
| **EPYC'dagi haqiqiy kechikish** | VPS CI'da yo'q | `test_inference_budget.py` + `hardware` markeri; arifmetika (§B.3) chegara emasligini ko'rsatdi |

### Sampling Rate

- **Har task commitida:** `npm run test:fast` (`tests/unit` + `node --test`)
- **Har to'lqin merge'ida:** `npm run test` + `npm run test:sim`
- **Faza darvozasi:** `npm run gate` yashil + `tests/integration/test_phase5_criteria.py` beshala mezoni + `pytest -m golden`

### Security Domain

`workflow.security_enforcement: true`, ASVS level 1.

| ASVS toifasi | Tegishlimi | Nazorat |
|---|---|---|
| V2 Authentication | yo'q (yangi emas) | 1-fazadagi PyJWT oqimi |
| V4 Access Control | **ha** | Ko'r audit va noaniq navbat **faqat nazoratchi/admin** rolida; `camera_zones` yozish — bozor admini. RLS + rol tekshiruvi |
| V5 Input Validation | **ha** | Poligon JSON: nuqta soni, 0..1 oralig'i, o'z-o'zi bilan kesishmaslik — **serverda** tekshiriladi (frontend tekshiruvi takror, ishonch emas) |
| V6 Cryptography | qisman | Namuna seedi `sha256` hosila — sir emas, **qayta chiqarilishi** kerak. Bu yerda «kuchli tasodifiylik» xavfsizlik talabi EMAS, shaffoflik talabi |
| V7 Error Handling | ha | Detektor xatosi kadr olishni yiqitmaydi (§E.13) |

| Tahdid | STRIDE | Yumshatish |
|---|---|---|
| Nazoratchi o'z aniqlik hisobotini «yaxshilash» uchun namunani qayta tortishi | Tampering | Hosila seed — namuna tanlanmaydi (C.8.1) |
| Ko'r audit javobining API'dan sizib chiqishi | Information disclosure | Serializer'dan maydon **olib tashlanadi** + rekursiv skan testi (C.8.2) |
| Bir bozor admini boshqa bozor kadrini ko'rishi | Information disclosure | RLS + kompozit FK (mavjud naqsh) |
| Yaroqsiz kadrdan hisob chiqishi | Tampering | `uq_snapshots_billable_anchor` kompozit FK (§D.12) |
| Poligon JSON'i orqali resurs sarflash (juda ko'p nuqta) | DoS | Nuqta soniga yuqori chegara + `CHECK` |

### Wave 0 Gaps

- [ ] `frontend/src/lib/zone-geometry.ts` + `frontend/scripts/zone-geometry.test.mjs` — sof geometriya (§A.5)
- [ ] `tests/fixtures/detections.py` — `sv.Detections` konstruktori **geometrik fakt bo'yicha** nomlangan
- [ ] `tests/fixtures/golden_set/` skeleti + `manifest.jsonl` sxemasi + sintetik yozuvlar
- [ ] `scripts/eval-golden-set.py` — uxlab turadigan aniqlik darvozasi bilan
- [ ] `tests/unit/test_license_fence.py` — `rfdetr-plus` / `LicenseRef-*` / AGPL darvozasi (**birinchi migratsiyadan oldin**)
- [ ] `tests/unit/test_rfdetr_postprocess.py` — xom tenzor arifmetikasi
- [ ] `tests/unit/test_aggregate_stall_slot.py` — AI-05 to'liq jadval
- [ ] `tests/unit/test_accuracy_report.py` — chalkashlik matritsasi + Wilson
- [ ] `tests/integration/test_occupancy_billing_fence.py` — D-16 langari (haqiqiy PG)
- [ ] `tests/integration/test_blind_audit.py` — oltita ko'r audit invarianti
- [ ] `tests/integration/test_phase5_criteria.py` — beshala mezonning yagona darvozasi
- [ ] `compose.yaml` da `cv-service` + `self_check.EXPECTED_COMPONENTS` ga qo'shish
- [ ] ONNX model artefaktini image'ga olib kirish yo'li (yuklab olish emas — **build paytida yoki volume**)
- [ ] ⚠ `npm run gate` byudjetini **tinch xostda uch marta o'lchash** va 900 s ni qayta belgilash (`04-VERIFICATION` open_item)
- [ ] ⚠ `scripts/check-validation-signoff.mjs::DEFAULT_FILE` ni fazadan mustaqil qilish (`04-VERIFICATION` open_item)

---

## Open Questions (RESOLVED where possible)

Har bandda **taklif qilingan standart** bor — rejalashtirish hech
qachon javob kutib to'xtamaydi.

| # | Savol | Taklif qilingan standart | Kim/qachon o'zgartiradi |
|---|---|---|---|
| **OQ-1** | Poligon muharriri: SVG yoki `react-konva`? | **SVG** — 0 bog'liqlik, jsdom'da testlanadi, 2-faza canvasni o'lchov bilan rad etgan (§A.5) | 50+ poligonda sudrash >16 ms bo'lsa → Konva. Render qatlami almashadi, geometriya emas |
| **OQ-2** | Model varianti? | **`RFDETRLarge`** (Apache-2.0). Kechikish chegara emas (§B.3) | Oltin to'plam o'lchovi; sozlama |
| **OQ-3** | `triggering_anchors`? | **`(CENTER, BOTTOM_CENTER)`**, sozlama sifatida | Real kadr; SQL bilan |
| **OQ-4** | Tiling/SAHI kerakmi? | **Yo'q** — v1 da butun kadr. Byudjet bor, lekin murakkablik aniqlik dalilisiz qo'shilmaydi | Rasta kadrda <32 px bo'lsa |
| **OQ-5** | Ko'r audit kunlik byudjeti? | **30 band/kun** → oylik ±2–3 f.p. (§C.8.4) | Nazoratchi ulgurmasa; sozlama |
| **OQ-6** | `eval`/`train` nisbati? | **70 / 30**, tortish paytida belgilanadi (§C.9) | Trening boshlanganda |
| **OQ-7** | Ko'r audit javobi bandlikni ham TUZATADIMI yoki faqat o'lchaydimi? | **Ikkalasi** — inson javobi sifatliroq haqiqat, uni tashlab yuborish isrof. Hisobot `queue_kind` bo'yicha ajratadi | — |
| **OQ-8** | `uncertain` chegaralari qayerda yashaydi? | **Qatorda** (`thresholds_version`), 4-fazadagi `quality_thresholds_version` naqshi — sozlash SQL, migratsiya emas | Real ma'lumot |
| **OQ-9** | `cv-service` HTTP xizmatmi? | **Yo'q — `taskiq` worker + minimal FastAPI** (health/self-check uchun) (§E.13) | — |
| **OQ-10** | ONNX fayli image'ga qanday kiradi? | **Build paytida COPY** (reproducible, tarmoqsiz start). Yuklab olish qilinmasin | Model hajmi image'ni haddan oshirsa → volume |
| **OQ-11** | RF-DETR fine-tuning shu fazadami? | **Yo'q** — `V2-AI-04`, va HITL ma'lumoti buni baribir qo'llab-quvvatlamaydi (§E.14). Faza faqat **ma'lumot yig'adi** | v2 |
| **OQ-12** | `no_coverage` rastalarni nima qilish? | Hisobotda **alohida** ko'rsatiladi, «bo'sh» ga qo'shilmaydi (§A.3) | `V2-AI-02` qo'lda rejim |
| **OQ-13** | Nazoratchi ishonchliligi (takroriy band) v1 dami? | **Ha, yoqilsin** — arzon, real kadrsiz ishlaydi, ~10% (§C.8.5) | Nazoratchi shikoyat qilsa nisbat kamaytiriladi |
| **OQ-14** | `gate` byudjeti 900 s qoladimi? | **Yo'q — qayta o'lchanadi.** 4-faza uni ochiq band qilib shu fazaga qoldirgan | Wave 0 o'lchovi |

---

## Sources

### Primary (HIGH — o'zim o'lchadim yoki rasmiy/manba kodi)

| Manba | Nima olindi |
|---|---|
| `pypi.org/pypi/rfdetr/json` | 1.9.1, 2026-08-04, `requires_python>=3.10`, to'liq `requires_dist`, Apache klassifikatori |
| `pypi.org/pypi/rfdetr-plus/json` | **1.0.2, `license_expression = LicenseRef-PML-1.0`**, `requires_dist: rfdetr<2,>=1.6.0` |
| `api.github.com/repos/roboflow/rf-detr` | `Apache-2.0`, `archived:false`, `pushed_at 2026-08-04`, 8868★ |
| `api.github.com/repos/roboflow/rf-detr-plus` | **404 — ochiq repo emas** |
| `raw.githubusercontent.com/roboflow/rf-detr/develop/LICENSE` | Apache 2.0 matni |
| `raw.githubusercontent.com/roboflow/rf-detr/develop/README.md` | Litsenziya bo'limi, variant jadvali, **«latency… NVIDIA T4 using TensorRT, FP16»** |
| `pypi.org` — `supervision`, `onnxruntime`, `timm`, `opencv-python-headless` | 0.30.0 / 1.28.0 / 1.0.28 / 4.14.0.94 va reliz sanalari |
| `rfdetr.roboflow.com/latest/learn/export/` | `export()` argumentlari, `inference_model.onnx`, **xom tenzor ogohlantirishi** |
| `supervision.roboflow.com/latest/detection/tools/polygon_zone/` | `PolygonZone` / `trigger()` / `PolygonZoneAnnotator` imzolari |
| `packages/sbozor-core/sbozor_core/models/snapshot.py` | `uq_snapshots_billable_anchor` va 5-faza uchun DDL izohi |
| `packages/sbozor-core/sbozor_core/models/market.py` | **`zones` nom to'qnashuvi**, `stalls.zone_id` |
| `packages/sbozor-core/sbozor_core/models/nvr.py` | `UNIQUE (market_id, nvr_id, channel_no)` |
| `migrations/helpers.py:269-310` | `attach_immutability_trigger()` |
| `tests/fixtures/frames.py:1-30` | Fixture nomlash majburiyati |
| `frontend/src/components/stalls/stall-map.tsx:22-36` | **Canvas'ning o'lchov bilan rad etilishi** |
| `frontend/vitest.config.ts`, `frontend/package.json` | Playwright yo'q; konva o'rnatilmagan |
| `.planning/phases/04-*` (RESEARCH/VERIFICATION/VALIDATION) | 175 kadr/kun, ochiq bandlar, darvoza uslubi |
| `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md`, `.planning/config.json` | AI-01…AI-06, V2-AI-*, mezonlar, `nyquist_validation`/`security_enforcement` |

### Secondary (MEDIUM — tekshirilgan, lekin bevosita o'lchanmagan)

- `arxiv.org/abs/2603.11821` + `melba-journal.org/pdf/2026:007.pdf` — avtomatizatsiya/ankorlash tarafkashligi, vaqt bosimi effekti
- `arxiv.org/pdf/2503.01747` — kichik namunada CLT/Wald ishonchsizligi
- `corplingstats.wordpress.com` — Wilson score oralig'i
- `roboflow/rf-detr` issues #285, #641 — CPU kechikishi (~180–200 ms)

### Tertiary (LOW — tasdiqlanmagan, rejada shunday belgilansin)

- `rfdetr` LW-DETR sinflarini eksport qiladimi — README jadvalidan taxmin
- `export(shape=...)` cheklovlari (56 ga karralik?) — sinalmagan
- `rfdetr[train]` COCO formati — bog'liqliklardan xulosa, dataset hujjati o'qilmagan
- RF-DETR ning COCO klasslari o'zbek bozori mollarini qamraydimi — **butunlay noma'lum, fazaning asosiy xavfi**
