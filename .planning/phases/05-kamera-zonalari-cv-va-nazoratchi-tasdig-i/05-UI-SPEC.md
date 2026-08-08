---
phase: 05-kamera-zonalari-cv-va-nazoratchi-tasdig-i
status: draft
created: 2026-08-08
design_system: shadcn-pattern (manual, CVA + Radix — Phase 1/2 tokens)
response_language: uz-Latn
inherits: .planning/phases/04-snapshot-pipeline/04-UI-SPEC.md
---

# Phase 5 — Kamera zonalari, CV va nazoratchi tasdig'i: UI dizayn kontrakti

> Bitta va'daning vizual kontrakti: **rasta band ekanini tizim aytdi — va bu javob to'g'rimi, buni XOLIS o'lchash mumkinmi.**
> 4-fazaning UI'si «yo'qlikni ko'rinadigan qilish» edi. Bu fazaniki — **xolislikni buzib bo'lmaydigan qilish**. Farq shundaki, bu yerda UI o'zi kafolatning **buzuvchisi** bo'la oladi: bitta ortiqcha maydon, bitta orqaga qaytish tugmasi — va «aniqlik 94%» degan raqam hech nimani anglatmay qoladi, buni esa hech kim sezmaydi.
> Yaratdi: `gsd-ui-researcher`. Tekshiradi: `gsd-ui-checker`. Iste'mol qiladi: `gsd-planner`, `gsd-executor`.

---

## 0. Dalil holati va shu sessiyada bajarilgan o'lchovlar

Belgilar 3 va 4-fazadagi bilan bir xil [MEROS: 04-UI-SPEC §0]:

| Belgi | Ma'nosi |
|-------|---------|
| **[O'LCHANDI]** | Shu sessiyada kodbazada yoki skript bilan o'lchandi — natija keltirilgan |
| **[KOD]** | Kodbazadan o'qildi — aniq `fayl:qator` yoki buyruq keltirilgan |
| **[MEROS]** | Upstream artefaktdan (05-CONTEXT, 05-RESEARCH, 04-UI-SPEC, 02-UI-SPEC, ROADMAP, CLAUDE.md) |
| **[QAROR]** | Shu hujjatda qabul qilindi — sabab yozilgan, muqobil rad etilgan |
| **[TALAB]** | UI backend'dan talab qiladigan narsa — rejaga bevosita kiradi |

### 0.1 O'lchovlar

| # | O'lchov | Natija |
|---|---------|--------|
| **M-1** | **shadcn darvozasi** — `find . -maxdepth 3 -name components.json` | **0 natija** → `Tool: none` (§3.4). 2, 3 va 4-faza qarori davom etadi |
| **M-2** | **Wave 0 primitivlari** — `ls frontend/src/components/ui/` | **10 primitiv** (`badge, button, card, confirm-dialog, dialog, empty-state, field, input, select, skeleton`). 5-fazada **yangi `ui/` primitivi qurilmaydi** (§3.2) |
| **M-3** | **Ikonka mavjudligi** — `node -e "require('lucide-react')"` bilan **93 ta** nom tekshirildi | **0 ta yetishmayapti.** `lucide-react@1.27.0` da hammasi bor: `Spline, PenTool, Shapes, Undo2, Redo2, Move, Crosshair, ScanEye, EyeOff, Lock, LockKeyhole, Dices, Shuffle, ClipboardCheck, ListChecks, CircleCheckBig, CircleX, CircleSlash, CircleDashed, SquareDashed, Grid2x2, Copy, CopyPlus, Split, Percent, Scale, FlaskConical, Target, …` |
| **M-4** | **Transliterator sinovi** — **88 ta** 5-faza nomzod satri `gen-cyrillic.mjs::transliterate()` dan **mavjud** override lug'ati bilan o'tkazildi | **0 ta mexanik defekt.** Ikki satr `ъ` bilan chiqdi va **ikkalasi ham TO'G'RI**: `Ma'lumot` → `Маълумот`, `Ta'sir` → `Таъсир` (tutuq belgisi) |
| **M-5** | ⛔ **YANGI DEFEKT SINFI — ARALASH ALIFBO.** `AI`, `CV`, `RF-DETR`, `ONNX`, `IoU`, `SVG`, `JSON` override**siz** o'tkazildi | **Beshta defekt, biri yangi sinf:** `AI`→`АИ`, `RF-DETR`→`РФ-ДЕТР`, `ONNX`→`ОННХ`, `JSON`→`ЖСОН` — bular 4-fazadagi `IR`→`ИР` bilan bir sinf. **`CV`→`CВ` esa YANGI**: `C` **lotin** qoldi, `V` **kirill** `В` bo'ldi — bitta tokenda ikki alifbo. Override ikkalasini ham tuzatadi (`AI жавоби` ✅), **lekin bu hujjat override o'rniga TAQIQNI tanlaydi** (§12.9) |
| **M-6** | **`ru` / `uz-Latn` uzunlik nisbati** — 32 ta 5-faza yorlig'i | O'rtacha **1,03×**. Eng yomoni: `Dalil rasmi` (11) → `Снимок-доказательство` (21) = **1,91×**; `Bo'sh` (5) → `Свободно` (8) = **1,60×**; `Band` (4) → `Занято` (6) = **1,50×**. Eng qisqasi: `Sizning javobingiz` (18) → `Ваш ответ` (9) = **0,50×** |
| **M-7** | **Navigatsiya sig'imi** — `NAV_ITEMS` + `ROLE_PERMISSIONS` matritsasi skript bilan hisoblandi [KOD: `app-shell.tsx:88-222`, `rbac.ts:55-109`] | Hozir **11 element**; 5-fazadan keyin **13**. Rol bo'yicha ko'rinadigan: `platform_admin` 11 (**o'zgarmaydi**), `director` 10→**11**, `market_admin` 10→**11**, `cashier` 1, ⛔ **`inspector` 1→2**. `MOBILE_PRIMARY_COUNT = 4` [KOD: `app-shell.tsx:222`] → mobil panel har rolda **≤5**. **Kontrakt saqlanadi** |
| **M-8** | ⛔ **RBAC — kerakli huquq ALLAQACHON MAVJUD** — `grep occupancy_review src/` | `PERMISSIONS` da **`occupancy_review` bor** [KOD: `rbac.ts:45`] va `inspector: ["occupancy_review"]` [KOD: `rbac.ts:108`]. Ya'ni 5-faza **yangi `Permission` qo'shmaydi** va `rbac.py`/`rbac.ts` juftligi **tegilmaydi** (§5.1 W0-F5) |
| **M-9** | ⚠ **Hedging darvozasining qamrovi** — `grep HEDGED scripts/nvr-copy.test.mjs` | `HEDGED_NAMESPACES = ["cameras", "snapshots"]` [KOD: `nvr-copy.test.mjs:143`]. 5-fazaning `cameraZones`/`review`/`occupancy` namespace'lari **skanerlanmaydi** → bu fazaning copy'si «Ehtimol» so'zini **umuman ishlatmaydi** va darvoza kengaytirilmaydi (§12.9 Qoida 3) |
| **M-10** | **`ъ` diskriminatori — ishlaydigan shakl** [KOD: `gen-cyrillic.test.mjs:754-758`] | 04-UI-SPEC dagi `/[A-Za-z]ъ/` **hech qachon ishlamaydi** (4-fazada o'lchangan: transliterator akronimni allaqachon kirillga o'girgan). Ishlaydigan shart — **`/[A-ZА-ЯЁҚҒҲЎ]{2,}ъ/u`** (`ъ` dan oldin ≥2 bosh harf). 5-faza shu shaklni **qayta ishlatadi**, ikkinchi nusxa yozmaydi |
| **M-11** | **Yangi bog'liqlik ehtiyoji** — `package.json` | `konva` va `react-konva` **o'rnatilmagan**. SVG muharriri **0 ta yangi paket** talab qiladi. Mavjud 18 ta prod bog'liqligi yetarli (§3.5) |
| **M-12** | **2-fazaning canvas o'lchovi** [KOD: `stall-map.tsx:22-36`] | Sarlavha izohi ayni: *«Canvas kutubxonasi … **O'LCHOV bilan rad etilgan** … 1000 elementli React yangilanishi memo bilan **~4 ms**; narxi esa haqiqiy bo'lardi: SSR yo'q, a11y yo'q, matn o'lchamlari qo'lda.»* — D-05 aynan shu o'lchovga tayanadi |
| **M-13** | **Yakuniy copy validatsiyasi** — §12 ning **51 ta shipping uz-Latn satri** (barcha `cameraZones.*`, `review.*`, `occupancy.*`, xato va bo'sh holat matnlari) to'liq override to'plami bilan transliteratordan o'tkazildi | **0 ta defekt.** Lotin qoldig'i **0**; akronim defekti (`/[A-ZА-ЯЁҚҒҲЎ]{2,}ъ/`) **0**; raqam aralashgan lotin token (`/[A-Za-z]+\.?[0-9]/`) **0**; tutuq belgisi yolg'on-defekti **0**. Ya'ni 5-faza `uz-Cyrl.overrides.json` ga **birorta yozuv qo'shmaydi** (§12.11 Qoida 2) |

### 0.2 M-5 ning xom chiqishi (dalil)

```
(1) Override SIZ — besh defekt, biri YANGI SINF:
  "AI javobi"      -> "АИ жавоби"      ❌ akronim buzildi (IR sinfi)
  "RF-DETR modeli" -> "РФ-ДЕТР модели" ❌ akronim buzildi
  "ONNX fayli"     -> "ОННХ файли"     ❌ akronim buzildi
  "JSON eksporti"  -> "ЖСОН экспорти"  ❌ akronim buzildi
  "CV xizmati"     -> "CВ хизмати"     ⛔ ARALASH ALIFBO: C=U+0043 (lotin), В=U+0412 (kirill)

(2) Override QO'SHILGANDAN KEYIN — hammasi tuzaladi (sof harfli token):
  words["AI"]="AI" -> "AI жавоби"      ✅
  words["CV"]="CV" -> "CV хизмати"     ✅

(3) Taqiq varianti — override umuman kerak emas:
  "Tizim javobi"   -> "Тизим жавоби"   ✅ toza
  "Tizim bahosi"   -> "Тизим баҳоси"   ✅ toza
  "Avtomatik baho" -> "Автоматик баҳо" ✅ toza
```

**Xulosa va qaror [QAROR]:** akronimlar **override bilan tuzatilmaydi — copy'dan chiqariladi**. Sabab uchta:

1. `CV`→`CВ` **aralash alifbo** beradi va uni ushlaydigan sodda darvoza yo'q: «lotin qoldi» detektori (`/[A-Za-z]/`) `CВ` da lotin `C` ni **ko'radi** va uni **defekt emas** deb o'tkazib yuboradi. Ya'ni bu defekt sinfi M-4 ning «0 defekt» natijasida ham **yashiringan bo'lardi**.
2. Override ro'yxati har fazada uzayadi va **hech qachon qisqarmaydi** — 4-fazada 2 yozuv qo'shildi, bu yerda 4–6 ta kerak bo'lardi.
3. ⛔ **Foydalanuvchi uchun ma'nosi yo'q.** Karmana nazoratchisi uchun `AI` va `tizim` orasida **farq yo'q** — u ikkalasini ham «kompyuter aytdi» deb o'qiydi; `RF-DETR` esa umuman ma'no tashimaydi. Bu 4-fazadagi `S3 omborida` → `omborda` qarorining aynan takrori (§11.11 Qoida 1).

Ya'ni **G-11** (§15) `messages/*.json` da `AI`, `CV`, `ONNX`, `RF-DETR`, `JSON` tokenlarini **taqiqlaydi** va `uz-Cyrl.overrides.json` ga 5-fazada **birorta yozuv qo'shilmaydi**.

---

## 1. Ko'lam va ko'lamdan tashqari

### 1.1 To'rtta yuza — va ular teng og'ir emas

| # | Yuza | Nimaga javob beradi | Foydalanuvchi | Ustuvorlik |
|---|------|---------------------|---------------|------------|
| **Y-1** | **Zona muharriri** (AI-01) | «Kadrda qaysi to'rtburchak qaysi rasta?» | Bozor admini, bir martalik ish | O'rta |
| **Y-2** | **Noaniq navbati** (AI-03) | «Tizim shubhalanganda kim hal qiladi?» | Nazoratchi, kunlik | Yuqori |
| **Y-3** | ⛔ **Ko'r audit** (AI-04) | «Tizimning javobi to'g'rimi — XOLIS o'lchov» | Nazoratchi, kunlik | ⛔ **ENG YUQORI** |
| **Y-4** | **Bandlik va aniqlik hisoboti** (AI-04 chiqishi, AI-05, AI-06, D-22) | «Kecha nima bo'ldi? Qancha rasta ko'rilmagani uchun bo'sh deb yozildi?» | Direktor, bozor admini | Yuqori |

### 1.2 Y-3 nima uchun eng yuqori — va nima uchun UI uni JIMGINA buza oladi

ROADMAP Phase 5 SC#4: *«Nazoratchi ko'r audit navbatida tizim javobini **ko'rmasdan** tasodifiy tanlangan zonalarni baholaydi — aniqlik hisoboti **faqat shu namunadan** chiqadi.»*

05-RESEARCH §C ochiq aytadi: *«AI-04 — UI tafsiloti emas: u butun mahsulotning yagona xolis o'lchov asbobi. Agar u noto'g'ri qurilsa, "aniqlik 94%" degan raqam chiqadi, lekin u hech nimani anglatmaydi — va buni hech kim sezmaydi.»*

Bu 4-fazadagi «bo'sh katak» muammosidan **jiddiyroq**, chunki u **jimroq**:

> 4-fazada buzilgan UI **ko'rinadigan** yolg'on aytardi (bo'sh katak → «ko'radigan narsa yo'q»).
> Bu yerda buzilgan UI **ko'rinmaydigan** yolg'on aytadi: raqam chiqadi, u chiroyli, u yaxshilanib boradi — va u soxta.

Shuning uchun uchta UI qoidasi **muzokarasiz** va §15 da darvozaga aylanadi:

| # | Qoida | Nima uchun UI qatlamida ham kerak |
|---|-------|------------------------------------|
| **1** | ⛔ Tizim javobi **payloadda umuman yo'q** — CSS bilan yashirilgan emas, shartli render bilan chetlab o'tilgan emas | Brauzerga yetgan maydon **o'qiladi**: DevTools, React DevTools, `JSON.stringify`, kesh inspektori. «Ko'rsatmayapmiz» — kod-ko'rik da'vosi, o'lchov emas |
| **2** | ⛔ Javob yozilgandan **keyin** oshkor qilinadi, va **orqaga qaytish yo'li yo'q** | Oshkor bo'lgandan keyin javobni «tuzatish» — o'lchovni ichkaridan buzish. Bu strukturaviy bo'lishi kerak: URL'da element identifikatori **yo'q** |
| **3** | ⛔ Ko'r audit bandi oddiy navbat bandidan **ko'rinishda ajraladi** | Nazoratchi «bu qaysi navbat?» deb o'ylamasligi kerak: ko'r auditda javob **o'zgarmas**, noaniq navbatida esa **ustiga yozilishi mumkin** (§7.7). Ikki xil oqibat — ikki xil ko'rinish |

### 1.3 Bu fazaning UI'si NIMA QILMAYDI (qisqa ro'yxat — to'lig'i §16)

- Patta summasi, tarif, kassir — **6-faza**
- «Band, lekin to'lovsiz» case oqimi — **7-faza**
- `.xlsx` eksporti, diagramma, haftalik/oylik trend — **8-faza**
- Model o'qitish, fine-tuning boshqaruvi — **`V2-AI-04`** (D-25)
- `no_coverage` rastalar uchun **qo'lda bandlik kiritish** — **`V2-AI-02`**
- Chegaralarni (`uncertain` bo'sag'asi) UI'dan sozlash — **SQL bilan** (D-11)

### 1.4 Talab qamrovi

| REQ | Bu fazada UI'da qanday ko'rinadi |
|-----|----------------------------------|
| **AI-01** | Y-1 — `/cameras/[cameraId]/zones` muharriri; normalangan, versiyalangan, ko'p kamerali |
| **AI-02** | Y-2/Y-3 — dalil rasmi (zona chizilgan holda); confidence **hech qayerda ko'rsatilmaydi** (§7.5) |
| **AI-03** | Y-2 — kunlik byudjet, ustuvorlik, ⛔ «hammasini tasdiqlash» **yo'q** (D-18) |
| **AI-04** | Y-3 — ko'r sessiya; Y-4 — chalkashlik matritsasi va Wilson oralig'i |
| **AI-05** | Y-4 — rasta darajasidagi kunlik bandlik xulosasi (kameralararo agregatsiya natijasi) |
| **AI-06** | Y-4 — ⛔ **`Ko'rilmagani uchun bo'sh`** alohida hisoblagich (D-19) |
| **D-22** | Y-1 va Y-4 — ⛔ **`Qamrov yo'q`** hech qachon «bo'sh» ga qo'shilmaydi |

---

## 2. Yuqori oqim qarorlaridan meros

27 ta qulflangan qarordan **o'n ikkitasi** UI shaklini bevosita belgilaydi.

| Qaror | Manba | UI'dagi bevosita oqibati |
|-------|-------|--------------------------|
| **D-05** — SVG, `react-konva` emas | 05-CONTEXT, 05-RESEARCH §A.5 | Muharrir `<image>` + `<polygon>` + `<circle>` dan quriladi. **Geometriya `lib/zone-geometry.ts` da sof funksiyalarda** — render qatlami almashtiriladi, geometriya emas (§6.2). `konva` **o'rnatilmaydi** [O'LCHANDI: M-11] |
| **D-06** — jadval nomi `camera_zones` | 05-CONTEXT | ⛔ UI matnida «zona» so'zi **hech qachon kvalifikatorsiz** ishlatilmaydi: **`kamera zonasi`** yoki **`bozor zonasi`**. `components/zones/` allaqachon **bozor zonasi** uchun band [KOD: `src/components/zones/`] → yangi katalog **`components/camera-zones/`** (§5.2) |
| **D-07** — normalangan (0..1) + versiyalangan koordinata | 05-CONTEXT, 05-RESEARCH §A.2 | Muharrir **hech qachon piksel saqlamaydi**; `source_width/height` bilan nisbat (aspect) o'zgarsa **`needs_review` ogohlantirishi** chiqadi va **avtomatik to'g'rilash QILINMAYDI** (§6.8) |
| **D-12** — tizim javobi **hech qachon o'zgartirilmaydi**; inson qarori **alohida yozuv** | 05-CONTEXT | UI'da «tahrirlash» tugmasi **yo'q**; ikkala javob **yonma-yon** ko'rsatiladi (§7.7, §11.4). «Tuzatish» so'zi copy'da **taqiqlangan** |
| **D-13** — 30 band/kun | 05-CONTEXT | Byudjet **hisoblagich** sifatida ko'rinadi (`7 / 30`), ⛔ **progress bar EMAS** (§7.3) |
| **D-14** — 70/30 `eval`/`train`, **tortish paytida** | 05-CONTEXT | Nazoratchi bu belgini **ko'rmaydi** (u xulqni o'zgartirardi). Belgi faqat Y-4 hisobotida **agregat** sifatida ko'rinadi (§11.6) |
| **D-15** — ko'r audit javobi **ham tuzatadi, ham o'lchaydi** | 05-CONTEXT | Y-4 hisoboti `queue_kind` bo'yicha **ajratadi**; bandlik xulosasida ko'r audit javobi ham `human` manba sifatida sanaladi (§11.4) |
| **D-16** — takroriy band ~10% | 05-CONTEXT | Nazoratchi uchun ⛔ **ko'rinmaydi** — takroriy band oddiy banddan farq qilmaydi, aks holda o'lchov ma'nosini yo'qotadi (§7.6). Natija faqat Y-4 da |
| **D-17** — beshta strukturaviy himoya | 05-CONTEXT, 05-RESEARCH §C.8 | §7.7 jadvali + **G-12/G-13/G-14** darvozalari (§15) |
| **D-18** — «hammasini tasdiqlash» **yo'q** | 05-CONTEXT | ⛔ Navbat **ro'yxat emas** — bir vaqtda **bitta band** (§7.3). Ko'p tanlash, checkbox ustuni, ommaviy amal paneli — **yo'q** |
| **D-19** — tasdiqlanmagan noaniq → «bo'sh», **alohida belgi bilan** | 05-CONTEXT, 05-RESEARCH §C.10 | Y-4 da ⛔ **to'rtinchi hisoblagich**: `Ko'rilmagani uchun bo'sh`. Nol bo'lsa ham ko'rsatiladi (§11.4) |
| **D-22** — `no_coverage` **alohida**, hech qachon «bo'sh» ga qo'shilmaydi | 05-CONTEXT | Y-4 da ⛔ **beshinchi hisoblagich**: `Qamrov yo'q` + `/cameras` ga yo'l. Y-1 da qamrov kartasi (§6.9) |

### 2.1 3 va 4-fazadan meros olinadigan UI qoidalari — qayta muhokama qilinmaydi

| Qoida | Manba | 5-fazada qayerda |
|-------|-------|------------------|
| Rang **hech qachon yagona signal emas** (WCAG 1.4.1) | 03-UI-SPEC §2.5 | §10.4 |
| `--color-warning` **hech qachon matn rangi emas** | 02-UI-SPEC §4.2 | §10.2 |
| `disabled` o'rniga **`aria-disabled`** | 02-UI-SPEC §6.6 | §13.3 |
| Xom `detail` / stack izi foydalanuvchiga **hech qachon** | 02-UI-SPEC T-02-99 | §12.6 |
| Soxta progress bar **qurilmaydi** | 02-UI-SPEC, 03-UI-SPEC §5.2 | §7.3 — byudjet **hisoblagich** |
| Poll terminal holatda **to'xtaydi** | 03-UI-SPEC §5.3 | §8.5 |
| Kalit nomlash: `namespace.camelCaseKey`, uchinchi daraja **faqat enum xaritalari** | 02-UI-SPEC §1.1 | §12 |
| Kesh kaliti **tug'ilishidanoq** `market_id` bilan doiralangan | 04-PATTERNS §S-14 | §5.4 |
| Kadr **core-api proxysi** orqali; presigned URL **hech qachon** | 04-UI-SPEC §14.3 | §14.2 |
| Nol hisoblagich **doim ko'rsatiladi** | 03-UI-SPEC §6.3, 04-UI-SPEC §6.3 | §11.4 |

---

## 3. Dizayn tizimi holati

### 3.1 Meros — o'zgarmaydi va qayta qurilmaydi

| Nima | Fayl | 5-fazada |
|------|------|----------|
| Tailwind 4 CSS-first `@theme` bloki (20 rang tokeni) | `frontend/src/app/globals.css` | **O'zgarmaydi** |
| `Button` (4 variant, `lg` = 44px) | `ui/button.tsx` | Qayta ishlatiladi |
| `Card` / `CardHeader` / `CardContent` | `ui/card.tsx` | Muharrir yon paneli, sessiya kartasi, hisobot bloklari |
| `Input` (+`aria-invalid`), `Field` (`${id}-error` / `${id}-hint`) | `ui/input.tsx`, `ui/field.tsx` | Qator yordamchisi, rasta tanlagichi |
| `Select` (native `<select>`) | `ui/select.tsx` | Kamera tanlagichi, kun tanlagichi |
| `Badge` (`neutral/muted/accent/success/warning/danger`) [KOD: `badge.tsx:28-43`] | `ui/badge.tsx` | Bandlik holati, zona versiyasi, navbat turi |
| `Skeleton` (`motion-reduce:animate-none`) | `ui/skeleton.tsx` | Kadr va navbat yuklanishi |
| `EmptyState` (`title`/`description`/`action`) [KOD: `empty-state.tsx:22-27`] | `ui/empty-state.tsx` | **6 ta** bo'sh holat (§12.8) |
| `Dialog` (`sm/md/lg` + `sheetOnMobile`) | `ui/dialog.tsx` | DL-1, DL-2, DL-5 |
| `ConfirmDialog` (fokus destruktiv tugmada **emas**) | `ui/confirm-dialog.tsx` | DL-3, DL-4 |
| `sonner` Toaster (`top-center richColors`) | `app/[locale]/layout.tsx:82` | 5 ta toast (§12.7) |
| `nuqs` URL holati | `audit-filters.tsx`, `stall-filters.tsx` | ⛔ **Faqat Y-1 va Y-4 da** — Y-2/Y-3 da URL holati **taqiqlanadi** (§4.5) |
| RBAC UI ko'zgusi (huquq yo'q → **render qilinmaydi**) | `lib/rbac.ts` | `camera_manage` / `occupancy_review` / `report_view` |
| next-intl 3 til + `i18n:check` darvozasi | `messages/*`, `scripts/*.mjs` | §12 |
| Roving tabindex naqshi (4-fazada birinchi marta) | `snapshots/capture-grid.tsx` | Zona muharririning **tepalar ro'yxati** shu naqshni qayta ishlatadi (§13.4) |
| Kadr ramkasi `bg-text` letterbox + `text-bg` (15,6:1) | 03-UI-SPEC §2.3 | Dalil rasmi va zona kadri ramkasi |

### 3.2 Yangi `ui/` primitivi — YO'Q [O'LCHANDI: M-2]

**5-fazada `frontend/src/components/ui/` ga hech nima qo'shilmaydi.** To'rtala yuza mavjud 10 primitiv ustida yig'iladi.

Ikkita chegaraviy holat **ataylab** `ui/` ga ko'tarilmaydi:

| Komponent | Nega `ui/` emas |
|-----------|------------------|
| `camera-zones/zone-canvas.tsx` | Uning semantikasi (normalangan koordinata, `source_width/height`, `needs_review`, rasta biriktirish) 5-faza domeniga xos. `ui/` ga chiqarish uni ma'nosiz umumiylashtirardi — 3-fazadagi `nvr-error-block.tsx` va 4-fazadagi `capture-grid.tsx` qarorlarining aynan takrori |
| `review/decision-bar.tsx` | Uchta javob tugmasi «umumiy tanlov guruhi» emas: ular **bitta so'rov = bitta qaror** qoidasini (D-18) olib yuradi va rasm yuklanmaguncha `aria-disabled` bo'ladi. Bu xulq umumiy primitivda ma'nosiz |

### 3.3 Analogi yo'q komponentlar — soxta analog berilmaydi

| Komponent | Nega analog yo'q | Nima qilinadi |
|-----------|------------------|---------------|
| `zone-canvas.tsx` | Kodbazada **SVG interaktiv yuzasi yo'q**: `grep -l "<svg" src/components` faqat `button.tsx` (spinner) va bitta testni beradi. `stall-map.tsx` — CSS Grid, SVG emas | §6.3–§6.6 da to'liq yoziladi: element ierarxiyasi, hodisalar, klaviatura, `aria-hidden` ko'zgusi |
| `blind-audit/blind-session.tsx` | Kodbazada «oldinga qarab yuradigan, orqaga qaytmaydigan sessiya» naqshi yo'q. Ustaning `wizard-stepper` i **orqaga qaytadi** — bu yerda u **taqiqlangan** | §7.6–§7.8 da to'liq yoziladi |
| `occupancy/confusion-matrix.tsx` | Kodbazada 2×2 statistik jadval yo'q; `recharts` **bog'liqlik emas** | §11.5 da to'liq yoziladi — sof `<table>`, diagramma yo'q |

### 3.4 shadcn darvozasi — natija [O'LCHANDI: M-1]

**`components.json` topilmadi** → **`Tool: none`. `shadcn init` BAJARILMAYDI.** [QAROR — 2, 3 va 4-faza qarorini davom ettiradi]

Sabablar o'zgarmagan: (1) `shadcn init` `package.json` ga yangi paket keltiradi; (2) Tailwind 4 rejimida u `globals.css` ga **o'z token nomlarini** yozadi va 1–2-fazada o'rnatilgan `--color-bg` / `--color-surface` / `--color-accent` to'plamining yonida **ikkinchi dizayn tizimi** paydo bo'lardi; (3) bu subagent kontekstida interaktiv savol vositasi yo'q — darvoza hujjatlashtirilgan qaror bilan yopiladi.

**Oqibat:** `Registry Safety` darvozasi shadcn uchun **qo'llanmaydi** (§14.1).

### 3.5 Yangi bog'liqlik so'rovi — YO'Q

**Yangi npm paketi: YO'Q. Yangi vendored artefakt: YO'Q.** [QAROR]

| Ehtiyoj | Mavjud yechim | Nega yangi paket kerak emas |
|---------|---------------|------------------------------|
| **Poligon chizish yuzasi** | **Native SVG + React** | D-05. `konva` + `react-konva` = **2 paket** va jsdom'da **testlanmaydi** [MEROS: 05-RESEARCH §A.5]. Batafsil §6.1 |
| Geometriya (nuqta qo'shish, kesishish, interpolatsiya) | **`lib/zone-geometry.ts` — o'z sof funksiyalarimiz** | `polygon-clipping`, `martinez` va shu kabilar butun boolean-geometriya kutubxonasini olib kelardi; bizga **11 funksiya** kerak va ular ~150 qator |
| Sudrash (drag) | Native `pointerdown`/`pointermove`/`pointerup` + `setPointerCapture` | `@dnd-kit`, `react-draggable` — sudrash baribir **normalangan koordinataga** o'girilishi kerak, ya'ni kutubxona o'ralardi |
| Zoom / pan | SVG `viewBox` (sof matematika) | Kutubxona kerak emas; `viewBox` — to'rt raqam |
| Ishonch oralig'i (Wilson) | **`lib/wilson.ts` — sof funksiya** | Statistika kutubxonasi bitta formula uchun |
| Chalkashlik matritsasi | Native `<table>` | `recharts` `package.json` da **yo'q** va 4 ta son diagramma talab qilmaydi |
| Sana/vaqt, ikonka, toast, URL holati, forma | `date-fns`, `lucide-react`, `sonner`, `nuqs`, `react-hook-form` + `zod` | Hammasi mavjud |

> Agar reja bajarilishida boshqa paket zarur bo'lib chiqsa, u **UI-SPEC ga qaytariladi** va shu bo'limga sabab + rad etilgan muqobil bilan yoziladi — jimgina `npm install` **qilinmaydi** [MEROS: 02-UI-SPEC §13].

---

## 4. Ekranlar reyestri

### 4.1 Marshrutlar

| Marshrut | Yuza | Vazifa | Huquq (UI ko'zgusi) |
|----------|------|--------|---------------------|
| `/[locale]/(app)/cameras/[cameraId]/zones` | **Y-1** | Zona muharriri: kadr + poligonlar + rasta biriktirish | `camera_manage` |
| `/[locale]/(app)/cameras/[cameraId]/zones?stall=<id>` | Y-1 | O'sha sahifa, tanlangan zona ochilgan | `camera_manage` |
| `/[locale]/(app)/review` | **Y-2 uyi** | Nazoratchi uyi: ikki sessiya kartasi + bugungi byudjetlar | `occupancy_review` |
| `/[locale]/(app)/review/uncertain` | **Y-2** | Noaniq navbati sessiyasi — bir vaqtda **bitta band** | `occupancy_review` |
| `/[locale]/(app)/review/blind` | ⛔ **Y-3** | Ko'r audit sessiyasi — **URL'da band identifikatori YO'Q** | `occupancy_review` |
| `/[locale]/(app)/occupancy` | **Y-4** | Kunlik bandlik xulosasi + aniqlik hisoboti | `report_view` |
| `/[locale]/(app)/occupancy?day=YYYY-MM-DD` | Y-4 | O'sha sahifa, tanlangan biznes-kun | `report_view` |

**Boshqa marshrut YO'Q.** `/camera-zones` (mustaqil indeks), `/review/blind/[id]`, `/review/history`, `/accuracy` — **qurilmaydi**.

### 4.2 Nega zona muharriri `/cameras` ostida, mustaqil bo'lim emas [QAROR]

Muqobil ko'rib chiqildi: `/camera-zones` — kameralar ro'yxati + har birining zona soni + qamrov bo'shlig'i.

**Rad etildi.** Sabab:

1. **Muharrirning indeksi ALLAQACHON mavjud** — u `/cameras`. Ikkinchi kamera ro'yxatini qurish «qaysi kameralar bor?» savoliga **ikki joyda** javob berardi, va ular arxivlash/qayta kashfiyotdan keyin **ajralib ketardi**.
2. **Zona kameraning xossasi** — u kamerasiz mavjud emas (`camera_zones.camera_id` `NOT NULL`, FK `cameras (market_id, id)`). URL ierarxiyasi domen ierarxiyasini takrorlaydi.
3. **Navigatsiya byudjeti.** Mustaqil bo'lim `NAV_ITEMS` ni 14 ga chiqarardi va yon panelning `market` guruhi 8 elementga yetardi — u skanerlanadigan bo'lishdan to'xtardi [MEROS: `app-shell.tsx:80-90` izohi].
4. **Self-service qoidasi buzilmaydi**: `/cameras` sahifasiga **bitta qamrov kartasi** va har kamera qatoriga **bitta amal** qo'shiladi (§5.5) — ya'ni «qayerdan boshlayman?» savoli javobsiz qolmaydi.

### 4.3 Nega ko'r audit ALOHIDA marshrut, tab emas [QAROR — xolislik uchun kritik]

Muqobil: `/review` da ikki tab — «Noaniq» va «Ko'r audit».

⛔ **Rad etildi va sabab strukturaviy, estetik emas:**

| # | Sabab |
|---|-------|
| 1 | **Tab — bitta komponent daraxti.** Ikkala navbat bitta sahifada yashasa, ko'r audit payloadining tipi va tizim javobini olib yuradigan tip **bitta modulda** uchrashadi. Shundan keyin `verdict` maydonining ko'r ekranga tushishi — bitta `props` uzatilishi, ya'ni **kod-ko'rik masalasi**. Alohida marshrut esa alohida katalog demak, va **G-12** darvozasi (§15) aynan katalogni skanerlaydi |
| 2 | **Tab — bitta React Query keshi.** `/review/uncertain` javobida kelgan tizim verdikti brauzer keshida yashaydi; tab almashtirilganda u **hamon o'sha kesh grafida** va DevTools bilan ochib ko'rish — bir bosish. Alohida marshrut + alohida `queryKey` prefiksi buni ajratadi (§5.4, §14.3) |
| 3 | **Tab — arzon almashish.** Ko'r auditning butun ma'nosi «bu bandni AVVAL ko'rmaganman» da. DB `UNIQUE (occupancy_event_id)` buni **hodisa darajasida** to'sadi [MEROS: 05-RESEARCH §C.8.3], lekin **rasta darajasida** to'smaydi — bir rasta bir kunda ikkala navbatda ham bo'lishi mumkin (turli slot). Alohida marshrut xotira ko'chishini kamaytiradi |
| 4 | **Tab holati URL'da yashaydi.** `?tab=blind` — ulashiladigan, orqaga-tugmasi bilan qaytiladigan holat. §4.5 esa Y-3 uchun URL holatini **umuman taqiqlaydi** |

### 4.4 Dialoglar (marshrut emas, sahifa holati)

| # | Dialog | Ochiladi | O'lcham | Huquq |
|---|--------|----------|---------|-------|
| **DL-1** | **Zona tafsiloti** — rasta biriktirish, versiya tarixi | Y-1 zona ro'yxatidan | `size="md" sheetOnMobile` | `camera_manage` |
| **DL-2** | **Qator bo'yicha bo'lish** — birinchi/oxirgi zona + rasta oralig'i + oldindan ko'rish | Y-1 asboblar qatoridan | `size="lg" sheetOnMobile` | `camera_manage` |
| **DL-3** | **Zonani o'chirish** (tasdiq) | DL-1 dan | `ConfirmDialog` 1-daraja | `camera_manage` |
| **DL-4** | **Sessiyadan chiqish** (tasdiq) | Y-2/Y-3 dan chiqishda, javobsiz band qolganda | `ConfirmDialog` 1-daraja | `occupancy_review` |
| **DL-5** | **Rasta tafsiloti** — kunlik bandlik qaydi, dalil kadrlar ro'yxati | Y-4 ro'yxatidan | `size="lg" sheetOnMobile` | `report_view` |

**Dialog holati URL'da EMAS** [MEROS: 02-UI-SPEC §7.1].

### 4.5 ⛔ URL holati kontrakti — Y-2 va Y-3 da URL holati TAQIQLANADI

| Marshrut | URL'da nima bor | URL'da nima YO'Q va nega |
|----------|-----------------|--------------------------|
| Y-1 `…/zones` | `?stall=<uuid>` — tanlangan zona (`nuqs`, `history: "replace"`) | Chizish rejimi, zoom/pan, undo steki — **sessiya holati**, ulashiladigan emas |
| Y-2 `/review/uncertain` | ⛔ **Hech nima** | Band identifikatori URL'da bo'lsa, nazoratchi orqaga qaytib **javobni qayta ko'ra olardi**. Navbat serverda yuriydi |
| Y-3 `/review/blind` | ⛔⛔ **Hech nima** | **D-17 ning UI shakli.** Identifikatorli URL: (a) orqaga-tugmasi bilan javob berilgan bandga qaytish; (b) havolani nusxalab qayta ochish; (c) tarixdan bandni topib qayta urinish. Uchalasi ham namunani **keyin tahrirlash** (05-RESEARCH §C.8, 4-dushman). URL'da identifikator bo'lmasa — uchalasi ham **imkonsiz** |
| Y-4 `/occupancy` | `?day=YYYY-MM-DD` (`nuqs`, `history: "push"`) | Filtrlar 8-fazada; bu fazada faqat kun |

**Sessiya holatining manbai — server.** `GET /review/blind/next` **navbatdagi bandni** qaytaradi; klient qaysi band kelishini tanlay olmaydi. Sahifa yangilansa — server o'sha bandni qaytaradi (javob yozilmagan bo'lsa) yoki **keyingisini** (yozilgan bo'lsa). Bu «yangilab qayta ko'raman» yo'lini ham yopadi.

> **[TALAB]** `POST /review/blind/{assignment_id}/answer` ikkinchi marta chaqirilsa **`409 blind_answer_locked`** qaytaradi. UI bu kodni tarjima qiladi (§12.6) va **qayta urinish tugmasi bermaydi**.

### 4.6 Navigatsiya kengaytmasi — ikkita yozuv [QAROR]

`NAV_ITEMS` ga **ikkita** element qo'shiladi [KOD: `app-shell.tsx:88-220`]:

```ts
{ href: "/review",    labelKey: "review",    icon: ClipboardCheck, permission: "occupancy_review", group: "market" },
{ href: "/occupancy", labelKey: "occupancy", icon: Store,          permission: "report_view",      group: "market" },
```

`NavItem["href"]` va `NavItem["labelKey"]` literal union'lariga to'rt satr qo'shiladi — aks holda kompilyatsiya yiqiladi (bu **maqsadli** darvoza) [KOD: `app-shell.tsx:56-79`].

**Joylashuv: `market` guruhida, `/snapshots` dan bevosita KEYIN.** Domen zanjiri shunday o'qiladi: *kamera → kadr → ko'rib chiqish → bandlik*.

| Savol | Javob |
|-------|-------|
| Ikonkalar? | `ClipboardCheck` (ko'rib chiqish ro'yxati) va `Store` (rasta/bandlik). `Camera`, `Video`, `CalendarClock` **band**; `ScanEye` rad etildi — u «kuzatuv» ni anglatib, nazoratchini kameraga qaratardi |
| Mobil kontrakt buzilmaydimi? | **Yo'q** [O'LCHANDI: M-7]. `NAV_ITEMS` 11 → **13**; har rolda mobil panel **≤5** |
| ⛔ Nazoratchi uchun nima o'zgaradi? | **Eng muhim natija.** Bugun `inspector` **faqat Boshqaruv panelini** ko'radi (1 yozuv) — ya'ni uning ishi uchun ekran **umuman yo'q edi**. 5-fazadan keyin u **2 yozuv** ko'radi va `/review` uning uyiga aylanadi |
| ⚠ `platform_admin` nega `/occupancy` ni ko'rmaydi? | Unda `report_view` **yo'q** [KOD: `rbac.ts:68-81`] va bu fazada RBAC **tegilmaydi** (M-8). Rollar **to'plam** (1-faza D-05), ya'ni tekshirish uchun unga `market_admin` roli ham beriladi. Bu **O-03** sifatida qayd etildi (§16.4) |
| Nega `/review/blind` navigatsiyada yo'q? | U **sessiya**, bo'lim emas. Unga faqat `/review` uyidan, **ochiq niyat bilan** kiriladi (§7.2) |

### 4.7 Ustaga ulanish — YO'Q [QAROR]

`WIZARD_STEPS` ga **hech narsa qo'shilmaydi**; `wizard-stepper.tsx` va `activation-panel.tsx` **tegilmaydi**.

Sabab 3 va 4-fazadagi bilan bir xil va bu yerda **kuchliroq**: zona chizish — 0,5–5 soatlik ish (§6.7). Usta qadami bo'lsa, u `completedStepCount` ga tushardi va **bozor «chala» ko'rinardi** — bir necha kun davomida. Vaholanki **qisman zonalangan bozor to'liq ishlaydi**: zonalangan rastalar hisobga kiradi, qolganlari `no_coverage` (D-22). Ya'ni usta qadami mahsulot haqiqatiga **zid** bo'lardi.

⛔ Bu **SBOZOR self-service prinsipining** aynan qo'llanishi: dala ishi hech qachon bloklamaydi.

---

## 5. Komponentlar reyestri

### 5.1 Wave 0 — yangi ekranlardan OLDIN (bloklovchi)

| # | Ish | Fayl | Nega bloklovchi |
|---|-----|------|-----------------|
| **W0-F1** | `NAV_ITEMS` + `href`/`labelKey` literal union'lari (§4.6) | `components/shell/app-shell.tsx` | Usiz sahifalar navigatsiyadan **yetib bo'lmaydi**; nazoratchining ekrani **umuman ochilmaydi** |
| **W0-F2** | `lib/zone-geometry.ts` — 11 sof funksiya + `zone-geometry.test.mjs` | `lib/`, `scripts/` | ⛔ **D-05 ning butun mazmuni.** Render komponenti geometriyaga tayanadi; teskarisi emas. Usiz muharrir DOM'siz testlanmaydi |
| **W0-F3** | `lib/wilson.ts` + testi | `lib/`, `scripts/` | Y-4 hisoboti usiz **Wald oralig'ini** ishlatishga majbur bo'lardi — 05-RESEARCH §C.8.4 uni ochiq rad etadi |
| **W0-F4** | `blind-payload.test.mjs` — **yangi fayl** | `scripts/` | Darvozalar **G-12, G-13**. Ekran yozilmasdan **oldin** qo'yiladi: keyin qo'yilsa, birinchi ijro allaqachon maydonni kiritgan bo'lardi |
| **W0-F5** | ⚠ **RBAC — o'zgarish YO'Q, lekin TASDIQLANADI** | `lib/rbac.ts` | [O'LCHANDI: M-8] `occupancy_review` **mavjud**. Bandning vazifasi — planer yangi huquq **o'ylab topmasligi**. Agar topsa, `rbac.py` **birga** o'zgaradi va `scripts/role-gate.test.mjs` ni qondiradi |
| **W0-F6** | `zone-copy.test.mjs` — **yangi fayl** | `scripts/` | Darvozalar **G-11, G-15, G-16, G-18** |
| **W0-F7** | `error-codes.test.mjs` ni `zone_*` / `review_*` kodlari bilan kengaytirish | `scripts/` | Darvoza **G-17** — sabab↔tuzatish parity |

### 5.2 Yangi komponentlar

**Katalog nomlari [QAROR]:** `camera-zones/` (⛔ `zones/` **emas** — u bozor zonasi uchun band, D-06), `review/`, `blind-audit/` (⛔ `audit/` **emas** — u audit jurnali uchun band), `occupancy/`.

| Yo'l | Vazifa | Client? | Analog |
|------|--------|---------|--------|
| `app/[locale]/(app)/cameras/[cameraId]/zones/page.tsx` | Y-1 qobig'i, RBAC darvozasi, `Suspense` | ✅ | `cameras/page.tsx` |
| `components/camera-zones/zone-editor.tsx` | Y-1 tashkilotchisi: kadr + ro'yxat + asboblar | ✅ | **analog yo'q** (§3.3) |
| `components/camera-zones/zone-canvas.tsx` | ⛔ SVG yuzasi: `<image>`, `<polygon>`, tepa doiralari, `aria-hidden` | ✅ | **analog yo'q** |
| `components/camera-zones/zone-list.tsx` | ⛔ **Ochiqlikning asosiy yuzasi** — poligonlar va tepalar `<ul>` sifatida (§13.4) | ✅ | `stalls/stall-list.tsx` |
| `components/camera-zones/zone-toolbar.tsx` | Yangi zona, qator yordamchisi, nusxalash, undo/redo, saqlash | ✅ | `stalls/stall-filters.tsx` |
| `components/camera-zones/zone-detail-dialog.tsx` | DL-1 — rasta biriktirish, versiya tarixi | ✅ | `cameras/camera-rename-dialog.tsx` |
| `components/camera-zones/row-assist-dialog.tsx` | DL-2 — qator bo'yicha bo'lish + oldindan ko'rish | ✅ | `snapshots/slot-editor.tsx` (oraliq generatori naqshi) |
| `components/camera-zones/coverage-card.tsx` | §6.9 — qamrov xulosasi; `/cameras` da ham ishlatiladi | — | `snapshots/coverage-warning.tsx` |
| `app/[locale]/(app)/review/page.tsx` | Y-2 uyi: ikki sessiya kartasi | ✅ | `dashboard/page.tsx` |
| `app/[locale]/(app)/review/uncertain/page.tsx` | Y-2 sessiyasi | ✅ | — |
| `components/review/review-session.tsx` | Sessiya mashinasi: band → javob → keyingisi | ✅ | **analog yo'q** |
| `components/review/evidence-frame.tsx` | Dalil rasmi + zona konturi; `onLoad` darvozasi (§7.4) | ✅ | `snapshots/snapshot-dialog.tsx` (rasm holati mashinasi) |
| `components/review/decision-bar.tsx` | Uchta javob tugmasi + klaviatura yorliqlari | ✅ | **analog yo'q** |
| `components/review/budget-counter.tsx` | `7 / 30` hisoblagichi — ⛔ progress bar **emas** | — | `snapshots/slot-editor.tsx` (`7 / 12` naqshi) |
| `app/[locale]/(app)/review/blind/page.tsx` | ⛔ Y-3 sessiyasi | ✅ | — |
| `components/blind-audit/blind-session.tsx` | ⛔ Ko'r sessiya mashinasi; oldinga-faqat | ✅ | **analog yo'q** |
| `components/blind-audit/blind-banner.tsx` | ⛔ Doimiy sarlavha lentasi (§7.7) | — | — |
| `components/blind-audit/reveal-panel.tsx` | ⛔ Javobdan **keyin** oshkor bo'ladigan panel; ma'lumot **POST javobidan** | — | — |
| `app/[locale]/(app)/occupancy/page.tsx` | Y-4 qobig'i | ✅ | `snapshots/page.tsx` (zonalar naqshi) |
| `components/occupancy/day-breakdown.tsx` | §11.4 — **besh** hisoblagichli `<dl>` | — | `snapshots/day-summary.tsx` (**to'liq shablon**) |
| `components/occupancy/confusion-matrix.tsx` | §11.5 — 2×2 jadval + Wilson oralig'i | — | **analog yo'q** |
| `components/occupancy/round-summary.tsx` | §11.6 — tur, tortilgan vaqt, hajm, javobsizlar | — | `cameras/discovery-result.tsx` |
| `components/occupancy/stall-day-list.tsx` | §11.7 — rasta × kun ro'yxati, DL-5 ni ochadi | ✅ | `stalls/stall-list.tsx` |
| `lib/zone-geometry.ts` | ⛔ **Sof geometriya — DOM'siz** (W0-F2) | — | Phase 1 ning 37 sof funksiya naqshi |
| `lib/wilson.ts` | Wilson score oralig'i (W0-F3) | — | — |
| `lib/camera-zone-queries.ts` | Y-1 so'rovlari va mutatsiyalari | — | `lib/camera-queries.ts` (**to'liq shablon**) |
| `lib/review-queries.ts` | Y-2 so'rovlari | — | `lib/snapshot-queries.ts` |
| `lib/blind-audit-queries.ts` | ⛔ **Y-3 so'rovlari — ALOHIDA MODUL** (§5.3) | — | — |
| `lib/occupancy-queries.ts` | Y-4 so'rovlari | — | `lib/snapshot-queries.ts` |
| `lib/zone-errors.ts` | `zoneErrorView(code) → {causeKey, fixKey, tone}` | — | `lib/capture-errors.ts` |

### 5.3 ⛔ `lib/blind-audit-queries.ts` nega ALOHIDA modul — bu darvozaning asosi

Uni `review-queries.ts` ichiga qo'yish **texnik jihatdan to'g'ri** bo'lardi: bir domen, bir backend, o'xshash shakl. **Rad etiladi** [QAROR]:

> **G-12 darvozasi FAYL TO'PLAMINI skanerlaydi, satrni emas.** «`verdict` so'zi `blind-audit-queries.ts` va `components/blind-audit/**` da uchramaydi» — bu **to'liq va mexanik** shart. Agar ko'r audit kodi `review-queries.ts` da yashasa, darvoza «`verdict` faqat `uncertain` funksiyalarida uchraydi» degan **kontekstga bog'liq** shartga aylanardi — ya'ni `grep` bilan tekshirib bo'lmaydigan, kod-ko'rikka qaytadigan shartga.

Bu 4-fazadagi `alert-list.tsx` / `alert-row.tsx` da `<img` taqig'i bilan **aynan bir sinf**: qoida faylga bog'lanadi, chunki faqat shunda u testga bog'lanadi.

Bir xil mantiqni takrorlashning narxi — ~40 qator. Xolislik kafolatining narxi — undan **ancha yuqori**.

### 5.4 Kesh kalitlari — tug'ilishidanoq doiralangan

```ts
// frontend/src/lib/camera-zone-queries.ts
import { domainKey } from "@/lib/market-queries";   // ikkinchi nusxa YARATILMAYDI

export const cameraZonesKey  = (marketId: string, cameraId: string) => domainKey(marketId, "camera-zones", cameraId);
export const zoneCoverageKey = (marketId: string) => domainKey(marketId, "zone-coverage");

// frontend/src/lib/review-queries.ts
export const uncertainNextKey = (marketId: string) => domainKey(marketId, "review-uncertain", "next");
export const reviewBudgetKey  = (marketId: string, day: string) => domainKey(marketId, "review-budget", day);

// frontend/src/lib/blind-audit-queries.ts   ⛔ ALOHIDA PREFIKS
export const blindNextKey   = (marketId: string) => domainKey(marketId, "blind-audit", "next");
export const blindBudgetKey = (marketId: string, day: string) => domainKey(marketId, "blind-audit", "budget", day);

// frontend/src/lib/occupancy-queries.ts
export const occupancyDayKey = (marketId: string, day: string) => domainKey(marketId, "occupancy", day);
export const accuracyKey     = (marketId: string, from: string, to: string) => domainKey(marketId, "accuracy", from, to);
```

| Qoida | Sabab |
|-------|-------|
| **Har fabrikaning BIRINCHI argumenti `marketId`** | Doiralashni chetlab o'tish TypeScript xatosisiz **mumkin emas** [MEROS: 04-PATTERNS §S-14, `snapshot-queries.ts` izohi] |
| **Global (marketsiz) kalit konstantasi bu modullarda UMUMAN YO'Q** | 3-fazada global kalitlar **o'chirilgan** — CR-01 ning strukturaviy davosi |
| ⛔ **`blind-audit` prefiksi `review-*` dan AJRALGAN** | §14.3 — ko'r payload keshi `gcTime: 0` bilan yuritiladi va uni **prefiks bo'yicha** tozalash mumkin bo'lishi kerak |
| `enabled: marketId !== null` — **kontrakt** | Bozorsiz sessiyada `409 market_not_selected` kesh grafida yashab qolardi [KOD: `market-queries.ts:185-192`] |
| `query-provider.tsx` **o'zgartirilmaydi** | Sessiya identifikatori o'zgarganda `client.clear()` butun keshni bo'shatadi |

### 5.5 Kengaytiriladigan mavjud fayllar

| Fayl | O'zgarish |
|------|-----------|
| `components/shell/app-shell.tsx` | W0-F1 — ikkita `NAV_ITEMS` yozuvi + union'lar |
| `app/[locale]/(app)/cameras/page.tsx` | ⚠ **Bitta `CoverageCard`** (§6.9) — `camera_manage` ostida |
| `components/cameras/camera-row.tsx` | ⚠ **Bitta amal**: «Kamera zonalari» → `/cameras/{id}/zones`; qator o'ngida zona soni `Badge tone="muted"` |
| `lib/api-types.ts` | `cameraZone*`, `review*`, ⛔ `blindAuditItem*` (**`z.strictObject`**, §14.3), `occupancy*` zod sxemalari + `ZONE_ERROR_CODES` / `REVIEW_ERROR_CODES` reyestrlari (`CAPTURE_ERROR_CODES:1297` naqshi) |
| `messages/uz-Latn.json`, `messages/ru.json` | ~150 kalit (§12) |
| `messages/uz-Cyrl.overrides.json` | ⛔ **O'zgarish YO'Q** — M-5 qarori bo'yicha akronim copy'ga umuman kirmaydi |
| `scripts/error-codes.test.mjs` | W0-F7 |
| `lib/rbac.ts` | ⛔ **O'zgarish yo'q** — W0-F5 tasdig'i |

### 5.6 Komponent testlari

| Fayl | Nimani isbotlaydi |
|------|-------------------|
| `zone-canvas.test.tsx` | SVG'dagi poligon soni ro'yxatdagiga teng; SVG konteyneri `aria-hidden="true"`; tepa doirasi `pointerdown` da `setPointerCapture` chaqiradi |
| `zone-list.test.tsx` | ⛔ Har poligon `<li>` sifatida mavjud; tanlangan poligonning tepalari **ro'yxat bo'lib ochiladi**; `ArrowUp/Down` fokuslangan tepani siljitadi; `Shift+Arrow` 10× siljitadi; 3 tepada «o'chirish» `aria-disabled` |
| `row-assist-dialog.test.tsx` | ⛔ Rasta soni oldindan ko'rishdagi poligon soniga teng bo'lmasa — **hech nima qo'shilmaydi** va xato chiqadi (4-fazadagi «qisman to'ldirish yo'q» qoidasi) |
| `review-session.test.tsx` | ⛔ Rasm `onLoad` bo'lmaguncha uchala javob tugmasi `aria-disabled`; ⛔ **ko'p tanlash checkbox'i yo'q**; bitta javob = bitta `mutate` chaqiruvi |
| `blind-session.test.tsx` | ⛔⛔ **Eng muhim test.** Payloadda `verdict`/`confidence` bo'lsa `blindAuditItemSchema` **throw qiladi**; `reveal-panel` javob yozilmaguncha **render bo'lmaydi**; javobdan keyin uchala tugma `aria-disabled` va `blindBanner` matnida «o'zgartirib bo'lmaydi» bor |
| `day-breakdown.test.tsx` | ⛔ **Beshala** hisoblagich **doim** render bo'ladi, nol bo'lsa ham; `noCoverage` va `defaultEmpty` **alohida `<dt>`** |
| `confusion-matrix.test.tsx` | To'rt katak + `n` + bazaviy bandlik ulushi render bo'ladi; `n === 0` da matritsa **o'rniga** «hali o'lchanmadi» matni chiqadi va **foiz ko'rsatilmaydi** |
| `coverage-card.test.tsx` | `uncovered === 0` bo'lganda ham karta **render bo'ladi** va «hamma rasta qamrovda» deydi |

---

## 6. Y-1: Zona muharriri (AI-01)

### 6.1 SVG — qaror, o'lchov va CHIQISH YO'LI

D-05 [MEROS: 05-CONTEXT] `react-konva` ni **rad etadi** va bu CLAUDE.md ning stek yozuviga **zid**. Zidlik ochiq hujjatlashtiriladi:

| CLAUDE.md asosi | Haqiqat |
|-----------------|---------|
| *«Handles 1000 stalls with pan/zoom where SVG/DOM dies»* | **2-fazada O'LCHOV bilan rad etilgan** [O'LCHANDI: M-12] — 1000 element memo bilan **~4 ms** |
| — | Poligon muharririda ekranda **1 kadr + 10–40 poligon**, ya'ni Konva'ning kuchi (minglab obyekt) bu yerda **ishlamaydi** |
| — | ⛔ **Hal qiluvchi omil: test.** `vitest` + `jsdom` da **canvas yo'q**; `react-konva` uchun `node-canvas` (native build) kerak. Playwright loyihada **yo'q** va 8-fazaga qoldirilgan [KOD: `vitest.config.ts:14-20`] — ya'ni canvas'ni sinaydigan **ikkinchi yo'l ham yo'q** |
| — | SVG — **0 ta yangi paket** [O'LCHANDI: M-11]; Konva — 2 ta |

**⛔ CHIQISH YO'LI OCHIQ QOLDIRILADI va uning tetigi O'LCHOVDIR:**

> Agar **50+ poligonli kamerada tepani sudrash `pointermove` ishlovchisi >16 ms** olsa, render qatlami Konva'ga almashtiriladi. Almashish **faqat `zone-canvas.tsx`** ni o'zgartiradi, chunki geometriya §6.2 dagi sof funksiyalarda yashaydi.

O'lchash usuli reja uchun: `performance.now()` bilan `pointermove` ishlovchisini o'rab, 60 poligonli fixture'da 100 ta harakat o'rtachasi. Bu **UAT bandi**, darvoza emas — chunki qiymat brauzer va qurilmaga bog'liq.

### 6.2 ⛔ `lib/zone-geometry.ts` — geometriya render qatlamida YASHAMAYDI

Bu D-05 ning butun mazmuni va u **W0-F2** sifatida ekranlardan **oldin** yoziladi.

```ts
// Hammasi SOF: DOM yo'q, React yo'q, `window` yo'q.
// Koordinata tipi: type Pt = readonly [number, number];  // 0..1
// Poligon tipi:    type Poly = readonly Pt[];

normalize(px: Pt, w: number, h: number): Pt          // piksel -> 0..1
denormalize(pt: Pt, w: number, h: number): Pt        // 0..1 -> piksel
addVertex(poly: Poly, index: number, pt: Pt): Poly   // `index` dan KEYIN qo'shadi
moveVertex(poly: Poly, index: number, pt: Pt): Poly  // 0..1 ga QISADI (clamp)
deleteVertex(poly: Poly, index: number): Poly        // <3 bo'lsa THROW emas — o'zgarishsiz qaytaradi
insertMidpoint(poly: Poly, edgeIndex: number): Poly  // qirraning o'rtasiga tepa
translate(poly: Poly, dx: number, dy: number): Poly  // nusxalash+siljitish uchun
isSelfIntersecting(poly: Poly): boolean              // ⛔ saqlashni to'sadi
polygonArea(poly: Poly): number                      // 0..1 kvadratida
centroid(poly: Poly): Pt                             // yorliq joyi
interpolateRow(first: Poly, last: Poly, n: number): Poly[]  // §6.7 qator yordamchisi
```

| Qoida | Sabab |
|-------|-------|
| **Hammasi immutable** — kirish o'zgartirilmaydi | Undo/redo steki **nusxa** emas, **havola** ro'yxati bo'ladi |
| `moveVertex` **`clamp(0,1)` qiladi** | Kadr tashqarisidagi tepa `cv2.pointPolygonTest` da aniqlanmagan natija beradi |
| `deleteVertex` 3 tepada **o'zgarishsiz qaytaradi** (throw emas) | UI `aria-disabled` bilan to'sadi; funksiya **himoyaning ikkinchi qatlami**, birinchisi emas |
| ⛔ `isSelfIntersecting` — **saqlash darvozasi** | O'zi bilan kesishgan poligon `supervision.PolygonZone` da noaniq natija beradi [MEROS: 05-RESEARCH §A.5]. Bu **jimgina noto'g'ri hisob** demakdir |
| `interpolateRow` — **sof chiziqli**, CV yo'q | Tepa-bo'yicha `lerp`: `first[i]` va `last[i]` orasida `n` ta oraliq. Ikkala poligonning tepa soni **teng bo'lishi shart**, aks holda `[]` qaytaradi |
| Test yugurtgichi — **`node --test scripts/*.test.mjs`** | Phase 1 ning 37 sof funksiya testi shu shaklda; brauzer kerak emas |

### 6.3 Sahifaning tuzilishi

```
┌ Kamera zonalari · Kanal 03 — Kiyim qatori                      (h1, 24/600)
│  [◀ Kameralarga]                                    [Saqlash]  [Bekor qilish]
│
├─ (A) Kadr yuzasi ────────────────────────────────┬─ (B) Zonalar ───────────┐
│                                                   │  Zonalar        18 / 60 │
│   ┌───────────────────────────────────────────┐   │  ┌────────────────────┐ │
│   │  [ kadr — aspect-video, bg-text ]         │   │  │ ▸ 14-A · Sabzavot  │ │
│   │      ╭──────╮   ╭──────╮                  │   │  │ ▸ 14-B · Sabzavot  │ │
│   │      │ 14-A │   │ 14-B │                  │   │  │ ▾ 14-C · (rastasiz)│ │
│   │      ╰──○───╯   ╰──────╯                  │   │  │    Tepa 1  0.12 …  │ │
│   │                                            │   │  │    Tepa 2  0.31 …  │ │
│   └───────────────────────────────────────────┘   │  │    Tepa 3  0.30 …  │ │
│   Kadr: 2026-09-14 07:00 · 1280×720  [Yangilash]  │  │    Tepa 4  0.11 …  │ │
│                                                   │  └────────────────────┘ │
├─ (C) Asboblar ────────────────────────────────────┴─────────────────────────┤
│  [+ Yangi zona]  [Qator bo'yicha bo'lish]  [Nusxalash]  [↶]  [↷]           │
├─ (D) Qamrov kartasi ────────────────────────────────────────────────────────┤
│  Bu kamerada 18 zona · Bozorda qamrovsiz rasta: 42                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Zonalar hech qachon almashmaydi** [MEROS: 03-UI-SPEC §3.2]. Kadr yangilanganda (A) `aria-busy="true"` oladi; poligonlar **joyida qoladi**.

| Zona | Qoida |
|------|-------|
| **(A) Kadr** | `aspect-video`, `bg-text` letterbox. Kadr — **oxirgi yaroqli** (`is_billable = true`) snapshot; `GET /api/v1/snapshots/{id}/image` proxysi orqali (§14.2). **[Yangilash]** yangi kadr so'raydi va poligonlarni **tegmaydi** |
| **(B) Zonalar ro'yxati** | ⛔ **Ochiqlikning asosiy yuzasi** (§13.4). `18 / 60` hisoblagichi 4-fazadagi `7 / 12` naqshini takrorlaydi |
| **(C) Asboblar** | Barchasi `secondary`; ⛔ sahifada **aksent fonli tugma faqat bitta** — `[Saqlash]` (§10.3) |
| **(D) Qamrov** | §6.9 — nol bo'lganda ham render bo'ladi |
| Rasta biriktirilmagan zona | `(rastasiz)` yorlig'i + `Badge tone="warning"`. ⛔ **Saqlanadi** — biriktirish keyin bo'lishi mumkin; lekin saqlashda **ogohlantirish** chiqadi (§12.7) |

### 6.4 Chizish o'zaro ta'siri (sichqoncha va barmoq)

| Amal | Qanday |
|------|--------|
| **Yangi zona boshlash** | `[+ Yangi zona]` → kursor `crosshair`, `role="status"` da «Nuqtalarni bosib qo'ying» |
| **Tepa qo'shish** | Kadrga bosish. Har bosish yangi tepa |
| **Yopish** | Birinchi tepani bosish **yoki** `Enter`. <3 tepada — yopilmaydi, `role="status"` da sabab |
| **Bekor qilish** | `Esc` — chala poligon **butunlay tashlanadi** (qisman saqlanmaydi) |
| **Tanlash** | Poligon ichiga bosish **yoki** (B) ro'yxatidan tanlash. Tanlangan poligon `stroke-width` 2 → 3, to'ldirish `fill-opacity` 0,15 → 0,25 |
| **Tepani sudrash** | `pointerdown` → `setPointerCapture` → `pointermove` → `pointerup`. Faqat **tanlangan** poligonning tepalari sudraladi |
| **Qirraga tepa qo'shish** | Qirra o'rtasidagi **kichik shaffof doira** (`r=4`) — bosilsa `insertMidpoint` |
| **Butun poligonni siljitish** | Ichiga `pointerdown` + sudrash → `translate` |
| **Tepani o'chirish** | Tepani tanlab `Delete`/`Backspace`. 3 tepada — **hech nima** + sabab |
| **Zonani o'chirish** | (B) ro'yxatidan DL-1 → DL-3 tasdig'i |
| **Undo / redo** | `Ctrl+Z` / `Ctrl+Shift+Z` va `[↶]`/`[↷]` tugmalari. **Chuqurlik 50 qadam**, sessiyaga bog'liq, saqlanmaydi |
| **Zoom / pan** | `viewBox` bilan; `Ctrl` + g'ildirak zoom, o'rta tugma yoki `Space` + sudrash pan. ⛔ **Zoom holati saqlanmaydi** |

**Barmoq nishoni:** tepa doirasining ko'rinadigan radiusi **5px**, lekin ustida **`r=11` shaffof `<circle>`** turadi (22px diametr). Bu WCAG 2.5.8 ning 24×24 minimumiga **yetmaydi** va bu **ongli chegirma**: tepalar 44px bo'lsa, qo'shni rastalarning tepalari ustma-ust tushib chizishni imkonsiz qilardi. **Kompensatsiya majburiy** — (B) ro'yxatidagi har tepa tugmasi **to'liq 44px** va u aynan shu ish uchun **birlamchi**, muqobil emas (§13.4).

### 6.5 Chegaralar [QAROR]

| Chegara | Qiymat | Sabab |
|---------|--------|-------|
| `MIN_VERTICES` | **3** | Poligonning ta'rifi; DB'da ham `CHECK (jsonb_array_length(polygon) >= 3)` |
| `MAX_VERTICES_PER_ZONE` | **12** | Rasta amalda to'rtburchak. 12 — saxiy zaxira; undan yuqorisi `jsonb` hajmini va `pointermove` narxini o'stiradi, aniqlik qo'shmaydi |
| `MAX_ZONES_PER_CAMERA` | **60** | Kutilgan qiymat 10–40 [MEROS: 05-RESEARCH §A.4]. 60 — zaxira; **va u D-05 ning o'lchov tetigidan (50+) yuqori**, ya'ni chegaraga yaqinlashgan kamera Konva savolini ham ko'taradi. Chegaraga yetganda `[+ Yangi zona]` `aria-disabled` + sabab |
| Undo chuqurligi | **50** | Xotira chegarasi; immutable poligonlar arzon |
| Tepa nudge qadami | **1 render piksel** (`Shift` bilan **10**) | §13.4 |

> **[TALAB]** `MAX_ZONES_PER_CAMERA` va `MAX_VERTICES_PER_ZONE` **serverda ham** majburlanadi (`Settings`). Klientdagi chegara — **qulaylik**, xavfsizlik chegarasi emas [MEROS: 02-UI-SPEC §12.3].

### 6.6 Saqlash semantikasi — versiyalash UI'da qanday ko'rinadi

| Qoida | Ko'rinish |
|-------|-----------|
| Tahrir **yangi `version`** yaratadi, eskisi `is_active=false` [MEROS: 05-RESEARCH §A.2] | DL-1 da `Versiya 3` `Badge tone="muted"` + `<details>` «Oldingi versiyalar» (sana + kim) |
| ⛔ Eski versiya **o'chirilmaydi va tiklanmaydi** | «Tiklash» tugmasi **YO'Q** (§16.2): tiklash yangi versiya yaratardi va tarixni ikki ma'noli qilardi. Kerak bo'lsa — qaytadan chiziladi |
| Saqlash **butun kamera uchun atomar** | Bitta `PUT /camera-zones?camera_id=…` — barcha o'zgargan poligonlar. Qisman saqlash **yo'q**: yarim saqlangan kamera bandlik hisobini jimgina buzardi |
| Saqlanmagan o'zgarish bor | `[Saqlash]` `Badge` bilan: `3 ta o'zgarish`. Sahifadan chiqishda `beforeunload` **QO'YILMAYDI** — u lokalizatsiya qilinmaydi va brauzerlar uni bo'g'adi. O'rniga **ichki navigatsiyada** DL-4 uslubidagi tasdiq |
| ⛔ O'zi bilan kesishgan poligon | Saqlash **to'xtaydi**; ayblanuvchi poligon (B) ro'yxatida `aria-invalid` va kadrda `stroke-danger`; xato matni §12.6 |
| Rastasiz zona | Saqlanadi, lekin toast: «{count} ta zonaga rasta biriktirilmagan — ular hisobga kirmaydi.» |

### 6.7 ⛔ 300–1000 rasta uchun HALOL javob

Bu bo'lim savolga to'g'ridan-to'g'ri javob beradi: **poligonlar rasta-boshiga chiziladi, va buni avtomatlashtirishning ishonchli yo'li yo'q.**

**Ish hajmining arifmetikasi** [MEROS: 05-RESEARCH §A.4]:

| Kattalik | Qiymat |
|----------|--------|
| Rasta | 300–1000 |
| Kamera | 20–25 |
| Bir kamerada ko'rinadigan rasta | ~10–40 |
| Bitta poligon (4–6 nuqta), qo'lda | ~10–20 s |
| **Jami, yordamchisiz** | **~2–5 soat, bir martalik** |
| **Jami, qator yordamchisi bilan** | **~0,5–1 soat** (qatorda 10–20 rasta → 2 ta poligon + 1 dialog) |

**Uchta yordamchi ships qilinadi va uchalasi ham SOF GEOMETRIYA** — birortasi CV da'vo qilmaydi:

| # | Yordamchi | Nima qiladi | Nega halol |
|---|-----------|-------------|------------|
| **1** | ⛔ **Qator bo'yicha bo'lish** (DL-2) | Qatorning **birinchi** va **oxirgi** rastasi chiziladi → tizim orasini `n` ta poligonga **chiziqli** bo'ladi | Har rasta baribir **o'z poligonini** oladi va u keyin alohida tuzatiladi. Bozor rastalari qator-qator va bir xil o'lchamda — bu **kuzatilgan haqiqat**, model taxmini emas |
| **2** | **Nusxalash + siljitish** | Tanlangan poligon nusxalanadi va qo'shni joyga siljitiladi (`translate`) | Bir amal, sof matematika |
| **3** | ⛔ **Qisman qamrov QONUNIY** | Zonalanmagan rasta `no_coverage` bo'ladi, xato emas | Usta bloklanmaydi; ROADMAP ning «tashqi bog'liqlik hech qachon `Blocks:` bo'lmaydi» qoidasi |

**⛔ RAD ETILGAN yo'llar — sabab bilan:**

| Rad etilgan | Nega |
|-------------|------|
| **«Kadrdan rastalarni avtomatik ajratish»** | Real bozor kadrida ishlamaydi (soyabon, mol, odam, perspektiva). MVP'da urinib ko'rish — vaqtni yoqish [MEROS: 05-RESEARCH §A.4] |
| ⛔ **«Detektor topgan qutilarni zona qilish»** | **Aylanma mantiq.** Detektorning xatosi zona geometriyasiga aylanadi, keyin o'sha geometriya bo'yicha o'sha detektor baholanadi — va aniqlik **soxta ko'tariladi**. Bu AI-04 ning butun maqsadini yo'q qiladi |
| **«Bozor plan-xaritasidan (2-faza) proyeksiya»** | Plan-xarita **sxematik** (`stall-map.tsx` CSS Grid), u real geometriya emas va kamera perspektivasiga proyeksiya qilinmaydi |
| **«Bitta katta zona = butun qator»** | Rasta darajasidagi hisob yo'qoladi; BILL-01 rasta bo'yicha ishlaydi |

**DL-2 «Qator bo'yicha bo'lish» ning aniq oqimi:**

```
1. Foydalanuvchi (B) ro'yxatidan IKKI zonani tanlaydi (birinchi va oxirgi)
   -> Tanlanmagan bo'lsa dialog ochilmaydi; tugma `aria-disabled` + sabab
2. Dialogda:
     Birinchi zona   [14-A ▾]        Oxirgi zona   [14-K ▾]
     Oradagi rastalar (rasta raqami bo'yicha):  14-B, 14-C, … 14-J   (9 ta)
     Hosil bo'ladigan zona:  9 ta
     [ oldindan ko'rish — kadr ustida 9 ta punktir poligon, har biriga raqam ]
3. [Bo'lish]  [Bekor qilish]
```

| Qoida | Qiymat | Sabab |
|-------|--------|-------|
| Rasta ketma-ketligi | Ikki tanlangan rastaning **bozor zonasi ichida `stall_number` bo'yicha tartibi** | Yagona mavjud tartib manbai (2-faza). Operator uni **oldindan ko'rishda ko'zi bilan tekshiradi** |
| Tepa soni | Ikkala poligonda **teng bo'lishi shart** | `interpolateRow` aks holda `[]` qaytaradi → dialog xato ko'rsatadi |
| ⛔ Nomuvofiqlik | Oradagi rasta soni ≠ hosil bo'ladigan poligon soni → ⛔ **hech nima qo'shilmaydi** + xato | 4-fazadagi «qisman to'ldirish yo'q» qoidasi: qisman natija «qaysilari qo'shildi?» savolini tug'dirardi |
| Mavjud zonaning ustiga tushish | Rastada **allaqachon** zona bo'lsa — u ro'yxatdan **chiqariladi** va dialogda sanaladi: «3 ta rastada zona bor — ular o'tkazib yuborildi» | Jimgina ustiga yozish tahrirlarni yo'q qilardi |
| Natija | ⛔ **Darhol saqlanmaydi** — muharrirga qo'shiladi, `[Saqlash]` kutadi | Operator har birini tuzatib chiqishi kerak; avtomatik saqlash uni «bajarildi» deb ishontirardi |

### 6.8 Kadr nisbati o'zgarganda — `needs_review`, avtomatik to'g'rilash YO'Q

[MEROS: 05-RESEARCH §A.2] Poligon 0..1 da saqlanadi, ya'ni asosiy oqim ↔ sub-oqim almashuvi **nisbat saqlanganda** zararsiz. Nisbat o'zgarsa (16:9 → 4:3) koordinatalar **jimgina siljiydi**.

| Holat | UI |
|-------|-----|
| `source_width/height` nisbati joriy kadrnikiga **teng** | Hech nima ko'rsatilmaydi |
| Nisbat **farq qiladi** | ⛔ Kadr ustida doimiy lenta: `bg-warning/20 text-text` + `TriangleAlert` + «Kadr o'lchami zonalar chizilgandagidan farq qiladi — zonalarni tekshiring.» `role="status"`. (B) ro'yxatida har zona `Badge tone="warning"` `Tekshirish kerak` |
| Avtomatik to'g'rilash | ⛔ **QILINMAYDI.** Cho'zilganmi yoki kesilganmi — bilib bo'lmaydi; noto'g'ri tuzatish **jimgina noto'g'ri hisob** beradi. UI faqat **ogohlantiradi** |
| Kamera qayta kashf qilindi (CAM-08) | Hech nima — `cameras.id` o'zgarmaydi, FK omon qoladi [MEROS: 05-RESEARCH §A.2] |

### 6.9 Qamrov kartasi — `no_coverage` bu yerda tug'iladi (D-22)

```
┌ Zona qamrovi ───────────────────────────────────────────────┐
│  Qamrovdagi rasta      258                                  │
│  Qamrovsiz rasta        42   ⚠ ular hisobga kirmaydi        │
│  Zonasiz kamera          3   [Ro'yxatni ko'rish]            │
└─────────────────────────────────────────────────────────────┘
```

| Qoida | Sabab |
|-------|-------|
| ⛔ **Uchala son DOIM ko'rsatiladi, nol bo'lsa ham** | 3 va 4-fazaning «nol — natija» qoidasi |
| `<dl>` semantikasi | Raqam va yorliq **dasturiy** bog'lanadi |
| «Qamrovsiz rasta» matni | ⛔ **«Bo'sh» so'zi ISHLATILMAYDI.** D-22: qamrovsiz rasta bo'sh **emas** — u haqida **ma'lumot yo'q**. Bu farq copy darvozasiga kiradi (**G-15**) |
| Joyi | Y-1 sahifasining pastida **va** `/cameras` sahifasida (§5.5) |
| `role="status"` | Hisobot, ogohlantirish emas |

---

## 7. Y-2 va Y-3: Noaniq navbati va ko'r audit (AI-03, AI-04)

### 7.1 Ikki navbat — bir xil shakl, IKKI XIL OQIBAT

| | **Y-2 — Noaniq navbati** | **Y-3 — Ko'r audit** |
|---|---|---|
| Nimani tanlaydi | Tizim **shubhalangan** hodisalar | ⛔ **Tasodifiy** namuna (hosila urug') |
| Maqsadi | Bugungi hisobni **to'g'rilash** | Aniqlikni **o'lchash** |
| Kunlik byudjet | Sozlanadigan (standart 50) | **30** (D-13) |
| Tizim javobi ko'rsatiladimi? | ⛔ **Javobdan KEYIN** (§7.5) | ⛔ **Javobdan KEYIN** (§7.8) |
| Javob o'zgartiriladimi? | **Ha** — yangi yozuv ustiga qo'yiladi | ⛔ **YO'Q** — o'zgarmas |
| URL'da identifikator | Yo'q | ⛔ Yo'q |
| Ustuvorlik | Billing ta'siri → chegaraga yaqinlik | Tasodifiy (ustuvorlik **yo'q**) |

⛔ **Ikkalasi ham tizim javobini javobdan keyin ko'rsatadi — bu QAROR va u AI-03 talab qilganidan qattiqroq** [QAROR]:

> AI-03 «noaniq javoblarni tasdiqlash» deydi, ya'ni tizim javobini **ko'rsatishga ruxsat beradi**. Bu hujjat uni **ko'rsatmaydi**. Sabab: band navbatga tushgan bo'lsa, tizim allaqachon **ishonchsiz**, ya'ni uning moyilligi **deyarli ma'lumot tashimaydi**, lekin **to'liq ankorlash kuchiga ega** (05-RESEARCH §C.8: mustaqil qarorlarning ~7% i noto'g'ri maslahatdan teskarisiga o'zgargan). Yashirishning narxi **nol**, foydasi esa — **toza yorliqlar**.
>
> ⚠ Bu yangi xavf tug'diradi: ikki navbat **ko'rinishda bir xil** bo'lib qoladi va nazoratchi qaysi biridaligini bilmasligi mumkin. §7.7 aynan shu xavfni yopadi.

### 7.2 `/review` — nazoratchining uyi

```
┌ Ko'rib chiqish                                            (h1, 24/600)
│  2026-09-14 · payshanba
│
├─ ⛔ Ko'r audit ────────────────────────────────────────────┐
│    Tasodifiy tanlangan rastalar. Tizim javobini ko'rmaysiz. │
│    Bugun: 7 / 30                                            │
│    Javobingiz yozilgandan keyin o'zgartirib bo'lmaydi.      │
│                                    [Ko'r auditni boshlash]  │
└─────────────────────────────────────────────────────────────┘
│
├─ Noaniq navbati ────────────────────────────────────────────┐
│    Tizim aniq ayta olmagan rastalar.                        │
│    Bugun: 12 / 50 · Navbatda: 23                            │
│                                       [Navbatni davom ettirish] │
└─────────────────────────────────────────────────────────────┘
│
└─ Kecha: 4 ta rasta ko'rilmagani uchun bo'sh deb hisoblandi.
```

| Qoida | Sabab |
|-------|-------|
| ⛔ **Ko'r audit YUQORIDA** | 05-RESEARCH §C.8: *«kunlik byudjetli navbat aynan vaqt bosimi yaratadi»* — ya'ni AI-03 ni birinchi qo'yish AI-04 ni kunning oxiriga surib, shoshilinch bajarilishiga olib borardi. Tartib **o'lchov ustuvorligini** ko'rsatadi |
| Ikkala karta **doim ko'rinadi**, byudjet tugagan bo'lsa ham | Tugagan karta: hisoblagich `30 / 30` + `Badge tone="success"` `Bajarildi` + tugma `aria-disabled` |
| Oxirgi qator (D-19 ilgagi) | ⛔ **Doim ko'rinadi, nol bo'lsa ham**: «Kecha: 0 ta rasta ko'rilmagani uchun bo'sh deb hisoblandi.» — bu nazoratchining ishi qanchalik muhimligini har kuni ko'rsatadi |
| Havola | Oxirgi qator `report_view` bo'lsa `/occupancy` ga havola; nazoratchida bu huquq **yo'q**, ya'ni u faqat matn ko'radi (§4.6) |

### 7.3 ⛔ Sessiya — BIR VAQTDA BITTA BAND (D-18 ning UI shakli)

```
┌ Noaniq navbati                                    12 / 50   [Chiqish] ┐
│                                                                       │
│   ┌───────────────────────────────────────────────────────────┐       │
│   │   [ dalil rasmi — zona konturi chizilgan, aspect-video ]   │       │
│   └───────────────────────────────────────────────────────────┘       │
│                                                                       │
│   Rasta 14-C · Sabzavot qatori                                        │
│   2026-09-14 · 07:00 · Kanal 03                                       │
│                                                                       │
│   Bu rasta band edimi?                                                │
│   ┌──────────┐  ┌──────────┐  ┌────────────────────┐                  │
│   │ 1  Band  │  │ 2  Bo'sh │  │ 3 Aniq ayta olmayman│                 │
│   └──────────┘  └──────────┘  └────────────────────┘                  │
└───────────────────────────────────────────────────────────────────────┘
```

⛔ **Navbat RO'YXAT EMAS va bu D-18 ning butun mazmuni** [QAROR]:

> «Hammasini tasdiqlash» tugmasini olib tashlash **yetarli emas**. Har qatorda ikki tugmali ro'yxat — **qadamlari ko'proq bo'lgan «hammasini tasdiqlash»**: ko'z qatordan chiqmaydi, qo'l takrorlaydi, va natija **ma'lumotga o'xshagan shovqin** bo'ladi. Diqqat — bu ekranda sarflanadigan **yagona resurs**, shuning uchun ekranning eng katta elementi **dalil rasmi** bo'ladi, ro'yxat emas.

| Qoida | Qiymat | Sabab |
|-------|--------|-------|
| Bir ekranda | ⛔ **1 band** | Yuqoridagi |
| Ko'p tanlash, checkbox, «tanlanganlarni tasdiqlash» | ⛔ **YO'Q** | D-18 |
| Ommaviy endpoint | ⛔ **YO'Q** — bitta so'rov = bitta qaror | [MEROS: 05-RESEARCH §C.9]. **[TALAB]**: OpenAPI'da massiv qabul qiluvchi `zone_reviews` endpointi bo'lmasligi backend testi bilan tekshiriladi |
| Byudjet ko'rsatkichi | **`12 / 50`** hisoblagich, `text-xs`, sarlavha yonida | ⛔ **Progress bar QURILMAYDI** [QAROR]: bar navbatni **tugatiladigan o'yin**ga aylantiradi va bu aynan shosha-pisha bosishning rag'bati. Hisoblagich **fakt** aytadi, maqsad qo'ymaydi |
| Klaviatura yorliqlari | `1` / `2` / `3` | Halol ishni tezlashtiradi; **takrorlanish (`keydown` repeat) e'tiborsiz qoldiriladi** — tugmani bosib turish ketma-ket javob yubormaydi |
| «Shoshib bosish» | Server `decided_at` farqini yozadi; ⛔ **UI hech nima ko'rsatmaydi va hech nimani to'smaydi** | [MEROS: 05-RESEARCH §C.9]. Nazoratchiga ko'rsatilsa, u o'lchovni chetlab o'tishni o'rganardi. Natija faqat Y-4 da (§11.6) |
| Ustuvorlik ko'rsatiladimi? | **Qisman**: «Bu rastada sotuvchi biriktirilgan» qatori chiqadi | Bu **motivatsiya**, ankor emas — u bandlik haqida hech nima demaydi |
| ⛔ Confidence qiymati | **HECH QAYERDA** | §7.5 |

### 7.4 Dalil rasmi — va u qarorning DARVOZASI

| Holat | Ko'rinish | Javob tugmalari |
|-------|-----------|-----------------|
| Yuklanmoqda | `Skeleton` ramka ichida, `bg-surface-muted` | ⛔ **`aria-disabled`** |
| Yuklandi (`onLoad`) | Kadr + zona konturi (`stroke-accent`, `fill-accent/10`) | **Faol** |
| Yuklanmadi (`onError`) | `ImageOff` + `review.imageUnavailable` + **[Qayta urinish]** | ⛔ **`aria-disabled` bo'lib qoladi** |

⛔ **Rasm yuklanmasdan qaror yozilmaydi** [MEROS: 05-RESEARCH §C.9, 2-band]. Bu shunchaki UX emas: rasm ko'rilmagan qaror — **ma'lumot emas, taxmin**, va u trening to'plamiga ham, aniqlik hisobotiga ham **kiradi**.

| Element | Qoida |
|---------|-------|
| Ramka | `aspect-video`, `bg-text` letterbox [MEROS: 03-UI-SPEC §2.3] |
| Zona konturi | Serverda chizilgan (`supervision.PolygonZoneAnnotator`) **yoki** klientda SVG overlay bilan — ⛔ **klient varianti tanlanadi**: u kadrni o'zgartirmaydi, ya'ni bir xil kadr Y-2, Y-3 va Y-4 da **bitta keshdan** keladi |
| Yaqinlashtirish | Bosilganda kadr to'liq o'lchamda ochiladi (`Dialog size="lg"`). ⛔ Bu **javobni yozmaydi** |
| ⛔ Yuklab olish, ulashish, nusxalash | **YO'Q** — kadr tashrifchining shaxsiy ma'lumoti (§14.2) |
| Kadr manbai | `GET /api/v1/snapshots/{id}/image` proxysi; `audit_read` yoziladi | 

### 7.5 ⛔ Nazoratchi HECH QACHON ko'rmaydigan narsalar

| Nima | Nega |
|------|------|
| `confidence` qiymati (`0.42`) | Ankor. Va u foydalanuvchi uchun **ma'nosiz** — 0,42 nimani anglatadi? |
| Tizim verdikti **javobdan oldin** | §7.1 |
| `model_version` | Foydalanuvchi uchun ma'nosiz; Y-4 da agregat sifatida bor |
| ⛔ `purpose` (`eval` / `train`) belgisi | D-14. Bilinsa, «bu baholash uchun ekan» degan e'tibor farqi tug'ilardi — bu 70/30 bo'linishining ma'nosini yo'q qilardi |
| ⛔ Takroriy band ekanligi (D-16) | Bilinsa, nazoratchi «avvalgi javobimni eslay» deb urinardi — ichki moslik o'lchovi **o'zini o'lchashdan** to'xtardi |
| ⛔ Namuna urug'i, tur raqami, tortish vaqti | Y-4 da (`report_view`), sessiyada emas |
| Boshqa nazoratchining javobi | Kelishuvni buzardi |

### 7.6 ⛔ Ko'r audit — beshta himoyaning UI shakli

05-RESEARCH §C.8 beshta strukturaviy himoyani sanaydi. Har biri UI'da **aniq shaklga** ega va uchtasi **darvoza** oladi:

| # | Strukturaviy himoya | UI dagi shakli | Darvoza |
|---|---------------------|----------------|---------|
| **1** | **Hosila urug'** — namunani qayta chizib bo'lmaydi | ⛔ UI'da **«namunani qayta tortish» tugmasi YO'Q**. Y-4 turni faqat **ko'rsatadi** (§11.6) | §16.2 (aniq taqiq) |
| **2** | **Tizim javobi payloadda umuman yo'q** | `blindAuditItemSchema` — **`z.strictObject`**; alohida modul va alohida katalog (§5.3) | ⛔ **G-12, G-13** |
| **3** | **`CHECK (queue_kind <> 'blind_audit' OR shown_ai_verdict = false)`** | UI **`shown_ai_verdict` ni hech qachon yubormaydi** — u serverda hisoblanadi. Klient uni yuborsa, u **yolg'on gapira olardi** | ⛔ **G-14** |
| **4** | **O'zgarmas javob** | URL'da identifikator yo'q (§4.5); javobdan keyin tugmalar `aria-disabled`; qayta yuborish `409` (§4.5 [TALAB]) | ⛔ **G-14** |
| **5** | **70/30 bo'linishi** | Nazoratchiga **ko'rinmaydi** (§7.5) | — |

**Ko'r sessiyaning ko'rinishi — oddiy navbatdan UCH KANAL bilan ajraladi** (§1.2 Qoida 3):

```
┌ ⛔ KO'R AUDIT ───────────────────────────────────────── 7 / 30 ─┐   ← (1) doimiy lenta
│  🔒 Tizim javobini ko'rmaysiz. Javobingiz yozilgandan keyin      │
│     o'zgartirib bo'lmaydi.                                       │
└──────────────────────────────────────────────────────────────────┘
   … (qolgan tuzilish Y-2 bilan bir xil) …
```

| Kanal | Qiymat | Nega bu kanal |
|-------|--------|---------------|
| **1. Doimiy lenta** | `blind-banner.tsx`: `bg-surface-muted` + `border-l-4 border-text` + `LockKeyhole` ikonkasi + ikki jumla. ⛔ **Yopilmaydi, `<details>` ga solinmaydi, skroll bilan ketmaydi** (`sticky top-0`) | Rang **yagona signal emas**: ikonka (shakl) + matn (so'z) + chap chegara (tuzilma) |
| **2. Marshrut** | `/review/blind` — manzil qatorida ko'rinadi | §4.3 |
| **3. Sarlavha** | `<h1>` = «Ko'r audit», sahifa `<title>` ham | Skrinrider foydalanuvchisi uchun **birinchi** eshitiladigan narsa |

⛔ **Lenta rangi `warning` yoki `danger` EMAS** [QAROR]: ko'r audit — **nosozlik emas**, u normal va muhim ish. Ogohlantirish rangi nazoratchida «xato qildimmi?» tuyg'usini tug'dirib, uni shoshiltirardi. Neytral, lekin **og'ir** ko'rinish (qalin chap chegara + qulf ikonkasi) to'g'ri ohangni beradi.

### 7.7 Javob va oshkor qilish — ma'lumot POST JAVOBIDAN keladi

```
javobdan OLDIN:                      javobdan KEYIN:
┌───────────────────────┐            ┌─────────────────────────────────┐
│ 1 Band  2 Bo'sh  3 …  │    ───►    │ Sizning javobingiz:  Band       │  ← aria-disabled
└───────────────────────┘            │ Tizim javobi:        Bo'sh      │
                                      │ ⚠ Javoblar mos kelmadi          │
                                      │ Javobingiz yozildi va           │
                                      │ o'zgartirib bo'lmaydi.          │
                                      │                  [Keyingisi →]  │
                                      └─────────────────────────────────┘
```

| Qoida | Sabab |
|-------|-------|
| ⛔ **Oshkor ma'lumot `POST` JAVOBIDAN keladi** | Oldindan yuklab qo'yilsa (prefetch), u brauzerga **javobdan oldin** yetardi — ya'ni himoya №2 buzilardi. `reveal-panel.tsx` ma'lumotni `useMutation` ning `data` sidan oladi, `useQuery` dan **emas** |
| ⛔ Keyingi bandni oldindan yuklash (prefetch) | **Ruxsat**, chunki keyingi band ham **ko'r payload** — unda tizim javobi yo'q. Lekin `reveal` ma'lumoti **hech qachon** prefetch qilinmaydi |
| Javobdan keyin tugmalar | `aria-disabled` + `Lock` ikonkasi; bosilsa `role="status"` da «Javob yozildi — o'zgartirib bo'lmaydi» | 
| «Mos keldi / kelmadi» | ⛔ **Ko'rsatiladi** va bu **ataylab**: nazoratchi o'rganadi va motivatsiya oladi (05-RESEARCH §C.8.2, 3-qatlam). U javobni **o'zgartira olmaydi**, ya'ni yozilgan ma'lumot ifloslanmaydi |
| ⛔ «Bekor qilish» / «Orqaga» | **YO'Q** (§16.2) |
| `[Keyingisi →]` | Yagona oldinga yo'l. `Enter` ham ishlaydi |
| Sessiya tugadi | `EmptyState`: «Bugungi ko'r audit bajarildi — 30 / 30» + **[Ko'rib chiqishga qaytish]** |

### 7.8 Sessiyadan chiqish

| Vaziyat | Xulq |
|---------|------|
| `[Chiqish]` bosildi, joriy band javobsiz | **DL-4** tasdig'i: «Sessiyadan chiqasizmi? Javob berilmagan band navbatda qoladi.» Fokus **[Bekor qilish]** da |
| `[Chiqish]` bosildi, joriy band javoblangan (oshkor ko'rinib turibdi) | Tasdiqsiz chiqadi |
| ⛔ Ko'r auditda javobsiz chiqish | Band **namunada qoladi** va kun oxirigacha javob berilmasa hisobotda **«javobsiz»** deb sanaladi [MEROS: 05-RESEARCH §C.8, 4-dushman]. DL-4 matni buni **aniq aytadi**: «Javob berilmagan band hisobotda "javobsiz" deb qoladi.» |
| Brauzer orqaga tugmasi | Sessiyadan chiqaradi (URL'da holat yo'q) — bu **kutilgan** xulq |

---

## 8. Holatlar kontrakti

### 8.1 Ikki daraja

| Daraja | Nima | Qayerda |
|--------|------|---------|
| **Sahifa/zona holati** | Yuklanmoqda / bo'sh / xato / natija | §8.2–§8.4 |
| **Element holati** | Bitta zonaning yoki bitta bandning holati | §6.6, §7.4 |

### 8.2 Y-1 zona muharriri

| # | Holat | Ko'rinish |
|---|-------|-----------|
| **Z-1** | Kadr va zonalar yuklanmoqda | Kadr o'rnida `Skeleton` (`aspect-video`); (B) ro'yxatida 3 ta `Skeleton` qator; `aria-busy="true"` |
| **Z-2** | ⛔ Kamerada **yaroqli kadr yo'q** | `EmptyState` **E-1**: «Bu kamerada hali yaroqli kadr yo'q» + **[Kadr olishga o'tish]** (`/snapshots`). ⛔ **Muharrir ochilmaydi** — fonsiz chizish ma'nosiz |
| **Z-3** | Kadr bor, zona **yo'q** | ⛔ Muharrir **ochiladi** va bo'sh holat **(B) ro'yxati ichida**: «Hali zona chizilmagan» + **[+ Yangi zona]**. Kadr yuzasi **bo'sh emas** — u kadrni ko'rsatadi |
| **Z-4** | Zonalar bor | Normal ko'rinish |
| **Z-5** | Nisbat farq qiladi | §6.8 lentasi + har zonada `Tekshirish kerak` |
| **Z-6** | Saqlanmoqda | `[Saqlash]` matni «Saqlanmoqda», `aria-disabled`; kadr va ro'yxat **o'chmaydi** |
| **Z-7** | Saqlash xatosi | Xato bloki `role="alert"` + sabab + tuzatish (§12.6); ⛔ **o'zgarishlar YO'QOLMAYDI** |
| **Z-8** | `isError` (yuklashda) | Meros xato bloki: `errors.loadFailedTitle` + **[Qayta urinish]** |

### 8.3 Y-2 / Y-3 sessiyalari

| # | Holat | Ko'rinish |
|---|-------|-----------|
| **S-1** | Navbatdagi band yuklanmoqda | Kadr o'rnida `Skeleton`; javob tugmalari `aria-disabled` |
| **S-2** | Rasm yuklanmoqda | §7.4 |
| **S-3** | Band tayyor | Normal |
| **S-4** | Javob yuborilmoqda | Uchala tugma `aria-disabled`; bosilgan tugmada `Loader2` |
| **S-5** | Javob yozildi (Y-3) | Oshkor paneli (§7.7) |
| **S-6** | Javob yozildi (Y-2) | Toast «Javob yozildi» + **darhol keyingi band** (oshkor paneli **1,5 s** ko'rinadi, keyin o'zi ketadi) |
| **S-7** | ⛔ Navbat **bo'sh** | `EmptyState` **E-2** (Y-2): «Noaniq band qolmadi» / **E-3** (Y-3): «Bugungi ko'r audit bajarildi — {done} / {total}» |
| **S-8** | ⛔ Byudjet **tugadi** | `EmptyState` **E-4**: «Bugungi byudjet tugadi — {max} / {max}. Ertaga davom etadi.» ⛔ **«Yana ko'rish» tugmasi YO'Q** (§16.2) |
| **S-9** | Bugun uchun namuna **hali tortilmagan** (Y-3) | `EmptyState` **E-5**: «Bugungi namuna hali tortilmagan. Kadrlar yig'ilgandan keyin tayyor bo'ladi.» ⛔ **«Hozir tort» tugmasi YO'Q** |
| **S-10** | `409 blind_answer_locked` | `role="alert"` + §12.6 matni + **[Keyingisi →]**. ⛔ **[Qayta urinish] YO'Q** |
| **S-11** | `isError` | Meros xato bloki + **[Qayta urinish]** |

> **S-7 va S-8 farqi hayotiy.** S-7 — ish tugadi (yaxshi xabar). S-8 — byudjet tugadi, lekin ish qolgan bo'lishi mumkin. Ikkalasini bir xil ko'rsatish nazoratchida «hammasi bajarildi» degan **yolg'on** hosil qilardi.

### 8.4 Y-4 bandlik va aniqlik hisoboti

| # | Holat | Ko'rinish |
|---|-------|-----------|
| **O-1** | Yuklanmoqda | Hisoblagichlar o'rnida 1 `Skeleton` qator; matritsa o'rnida 1 `Skeleton` blok |
| **O-2** | Kun almashtirildi | Mazmun **o'chmaydi**, `aria-busy="true"` |
| **O-3** | ⛔ Bu kunda **bandlik hodisasi yo'q** | `EmptyState` **E-6**: «Bu kunda bandlik hisoblanmagan» + tavsifda sabab (kadr yo'q / zona yo'q). ⛔ **«0 band» EMAS** |
| **O-4** | Kun bor, ko'r audit javobi **hali yo'q** | ⛔ Hisoblagichlar **ko'rsatiladi**; chalkashlik matritsasi o'rnida «Aniqlik hali o'lchanmadi — {n} ta javob kerak» va ⛔ **foiz ko'rsatilmaydi** |
| **O-5** | `isError` | Meros xato bloki |

⛔ **O-4 muhim:** `n` kichik bo'lganda foiz ko'rsatish — 05-RESEARCH §C.8.4 ning aynan ogohlantirgan xatosi. **Chegara: `n < 20` bo'lsa foiz umuman chizilmaydi**, faqat xom sonlar va «hali o'lchanmadi» matni.

### 8.5 Poll kontrakti

| Yuza | Poll | Sabab |
|------|------|-------|
| **Y-1** | ⛔ **YO'Q** | Zonalar faqat foydalanuvchi tahriridan o'zgaradi. `refetchOnWindowFocus` yetarli |
| **Y-2 / Y-3 navbati** | ⛔ **YO'Q** | Navbat **so'rov bo'yicha** yuriydi: javob → `mutate` → `invalidate` → keyingi band. Poll «men javob berayotganda band o'zgardi» holatini tug'dirardi |
| **Y-2 / Y-3 byudjeti** | Faqat sessiya boshida va har javobdan keyin | O'sha sabab |
| **Y-4** | `refetchInterval: day === bugun ? 60_000 : false` | Bandlik kun davomida to'planadi. 60 s — 4-fazadagi 30 s dan **ikki barobar sekin**, chunki bandlik slot bo'yicha (eng tez 15 daqiqa) o'zgaradi |
| Yashirin tab | `refetchIntervalInBackground: false` | 3-faza kontrakti |
| Cheksiz poll | ⛔ **Hech qachon** | O'tgan kun o'zgarmaydi |

---

## 9. Bo'shliq va tipografiya

### 9.1 4-panjara — o'zgarishsiz [MEROS: 02-UI-SPEC §2, 04-UI-SPEC §7.1]

| Token | Qiymat | 5-fazada qayerda |
|-------|--------|------------------|
| `xs` | 4px (`1`) | Ikonka–matn oralig'i, badge ichki `y`, tepa ro'yxatidagi koordinatalar orasi |
| `sm` | 8px (`2`) | Javob tugmalari orasi, zona ro'yxati elementlari orasi |
| `md` | 12px (`3`) | Hisoblagichlar orasi, matritsa katagi ichki |
| `lg` | 16px (`4`) | Karta ichki, dialog bo'limlari, muharrir ustunlari orasi |
| `xl` | 24px (`6`) | Zona oralig'i (A↔B↔C↔D) |
| `2xl` | 32px (`8`) | Katta bo'lim uzilishi |
| `3xl` | 48px (`12`) | Bo'sh holat `py-12` |

**Meros istisnolari saqlanadi:** 44px (`min-h-11`) barcha barmoq nishoni; 56px (`min-h-14`) mobil pastki panel; 20px (`5`) `CardHeader`/`CardContent` ichki `x`; 112px (`w-28`) 4-fazadagi sticky ustun.

### 9.2 Uchta yangi o'lcham — uchalasi ham panjaradan [QAROR]

| O'lcham | Qiymat | Tailwind / SVG | Nima uchun panjaradan chiqmaydi |
|---------|--------|----------------|----------------------------------|
| **Tepa ro'yxati qatori** | **44 × 44px** | `min-h-11` | Meros barmoq nishoni. ⛔ Bu **birlamchi** tahrirlash yuzasi (§13.4), muqobil emas — kichraytirish WCAG 2.5.8 ni buzardi |
| **Tepa ushlagichi (SVG)** | ko'rinadigan **`r=5`** (10px), bosiladigan **`r=12`** (**24px**) | `<circle r={12} fill="transparent">` ustida `<circle r={5}>` | 24 = 6 × 4 — **panjarada**. WCAG 2.2 SC 2.5.8 minimumi aynan **24×24** |
| **Javob tugmasi (Y-2/Y-3)** | balandlik **48px** (`min-h-12`) | `size="lg"` + `min-h-12` | 12 × 4 — panjarada. 44px meros minimumidan **yuqori**: bu ekranning **yagona amali** va u telefonda, bozor ichida, bir qo'lda bosiladi |

⚠ **WCAG 2.5.8 va ustma-ust tushadigan tepalar — ochiq yozilgan chegirma.** Qo'shni rastalarning tepalari 24px doiralari bilan **kesishadi**, ya'ni SC 2.5.8 ning «Spacing» istisnosi qo'llanmaydi. Qo'llanadigan istisno — **«Essential»**: poligon tepasi kadrdagi **aniq nuqtaga** bog'langan va uni kattalashtirsa chizishning o'zi imkonsiz bo'lardi (xarita nuqtalari bilan bir sinf). ⛔ **Kompensatsiya majburiy va u shartsiz:** (B) tepa ro'yxati **to'liq 44px** qatorlardan iborat va u sichqonchasiz **to'liq muqobil yo'l** beradi (§13.4). Bu chegirma **faqat shu kompensatsiya bilan birga** kuchda.

**Boshqa yangi qiymat so'ralmaydi.** Kadr ramkasi `aspect-video` (16/9) — u kenglikdan hosil bo'ladi, spacing tokeni emas [MEROS: 03-UI-SPEC §2.1].

### 9.3 Tipografiya — to'rt rol, beshinchisi YO'Q [MEROS: 03-UI-SPEC §2.2]

| Rol | O'lcham | Og'irlik | Line-height | Tailwind |
|-----|---------|----------|-------------|----------|
| **Display** — sahifa sarlavhasi | 24px | 600 | 1.25 | `text-2xl font-semibold tracking-tight leading-tight` |
| **Heading** — karta/dialog/`<legend>` | 18px | 600 | 1.375 | `text-lg font-semibold leading-snug` |
| **Body** — barcha matn va boshqaruv elementi | 14px | 400 | 1.5 | `text-sm leading-normal` |
| **Meta** — badge, hisoblagich yorlig'i, koordinata | 12px | 400 | 1.33 | `text-xs` |

**Urg'u — faqat og'irlik (600), o'lcham emas, rang emas.** `font-medium` (500) va `text-base` (16px) **taqiqlangan** [MEROS: 02-UI-SPEC §3.2].

**Beshinchi o'lcham QO'SHILMAYDI** [QAROR]. Vasvasa ikkita va ikkalasi ham rad etiladi:

1. *Tepa ro'yxatidagi koordinatalar `text-[10px]` bo'lsa ko'proq sig'ardi* — koordinata **o'qib aytiladigan qiymat** (§9.4), uni 10px ga tushirish uni ishlatib bo'lmaydigan qiladi.
2. *Chalkashlik matritsasidagi ishonch oralig'i kichikroq bo'lsin* — u **aynan o'sha o'lchamda** turishi kerak: 05-RESEARCH §C.8.4 «aniqlik yolg'iz e'lon qilinmasin» deydi, ya'ni oraliq **asosiy raqam bilan teng og'irlikda**.

⚠ Yagona chegaraviy holat — **kadr ustidagi zona yorlig'i** (`14-C`). U SVG `<text>` va uning o'lchami **`viewBox` bilan masshtablanadi**, ya'ni CSS shkalasidan tashqarida. Kontrakt: yorliq zoom 1× da **12px ga teng ko'rinadi** va zoom bilan o'sadi/kichrayadi. ⛔ Zoom 0,5× dan pastda yorliqlar **umuman chizilmaydi** (o'qilmaydigan matn — shovqin), o'rniga (B) ro'yxati javob beradi.

### 9.4 `font-mono` — hujjatlashtirilgan istisno, 5-faza ro'yxati

`font-mono` — **faqat** o'qib aytiladigan yoki belgima-belgi solishtiriladigan texnik qiymat uchun [MEROS: 03-UI-SPEC §2.2].

| Qiymat | Uslub | Sabab |
|--------|-------|-------|
| Normalangan koordinata (`0,124 · 0,318`) | `font-mono text-xs` | Ustunlashadi; SQL va API bilan solishtiriladi |
| Zona versiyasi (`v3`) | `font-mono text-xs` | Identifikator |
| Kanal raqami (`03`) | `font-mono text-xs` | `/cameras`, `/snapshots` bilan bir xil |
| Kadr vaqti (`07:00`) | `font-mono text-xs` | 4-faza bilan bir xil |
| Chalkashlik matritsasining **to'rt soni** | `font-mono` | Ustunlar tik solishtiriladi — bu jadvalning butun ma'nosi |
| Ishonch oralig'i (`91,2% (87,4–94,0)`) | `font-mono text-sm` | O'sha sabab |
| Namuna hajmi `n` | `font-mono` | O'sha sabab |
| `object_key`, ombor manzili | ⛔ **HECH QACHON** | §14.2 |

**Rasta raqami (`14-C`) `font-mono` EMAS** — u **DB kontenti** va odam o'qiydigan yorliq, solishtiriladigan token emas. **Foiz belgisi `%` matn ichida qoladi**, alohida uslub olmaydi.

---

## 10. Rang kontrakti (60/30/10)

### 10.1 Taqsimot — o'zgarishsiz, yangi token YO'Q

| Rol | Token | Qiymat | 5-fazada qayerda |
|-----|-------|--------|------------------|
| **Dominant (60%)** | `--color-bg` | `oklch(0.985 0 0)` | Sahifa foni |
| **Ikkilamchi (30%)** | `--color-surface` | `oklch(1 0 0)` | Kartalar, dialoglar, zona ro'yxati, matritsa |
| | `--color-surface-muted` | `oklch(0.968 0 0)` | `Skeleton`, ⛔ **ko'r audit lentasi** (§7.7), tugagan sessiya kartasi |
| **Aksent (10%)** | `--color-accent` | `oklch(0.56 0.19 255)` | §10.3 — **qisqargan** ro'yxat |
| **Destruktiv** | `--color-danger` | `oklch(0.58 0.21 27)` | Kesishgan poligon konturi, «band deb xato» katagi, zonani o'chirish tasdig'i |
| **Kadr ramkasi** | `bg-text` + `text-bg` | 15,6:1 | Dalil rasmi va zona kadri letterbox'i [MEROS: 03-UI-SPEC §2.3] |

**Yangi token kiritilmaydi va yangi rang juftligi so'ralmaydi.**

### 10.2 `--color-warning` matn sifatida ISHLATILMAYDI

Sariq tintdagi matn — `bg-warning/20 text-text` (o'lchangan **15,64:1**) [KOD: `badge.tsx:17-25`]. `--color-warning` oq fonda **2,03:1** — falokat.

5-fazada bu **to'rt joyda** muhim: `Tekshirish kerak` badge'i (§6.8), `Qamrovsiz rasta` qatori (§6.9), `Ko'rilmagani uchun bo'sh` hisoblagichi (§11.4), `(rastasiz)` zona yorlig'i. To'rtalasi ham `bg-warning/20 text-text`.

### 10.3 ⛔ Aksent — 5-fazada eng qisqa ro'yxat [QAROR]

Aksent rang **faqat** quyidagilarda:

1. **Fokus halqasi** (`:focus-visible outline`) — barcha interaktiv elementlar, jumladan SVG tepa ushlagichi va zona poligoni.
2. **Faol maydon chegarasi va halqasi** (`focus-visible:border-accent`, `ring-accent/25`).
3. **Joriy navigatsiya elementi** — faqat mobil pastki panelda.
4. **Tanlangan zona konturi** — `stroke-accent` + `fill-accent/25` (§10.5).
5. **Dalil rasmidagi zona konturi** — `stroke-accent` + `fill-accent/10` (§7.4).
6. **Y-1 dagi `[Saqlash]`** — sahifadagi **yagona** aksent fonli tugma.

> ⛔ **Y-2 va Y-3 da AKSENT FONLI TUGMA UMUMAN YO'Q** [QAROR — xolislik uchun kritik].
>
> Uchala javob tugmasi (`Band` / `Bo'sh` / `Aniq ayta olmayman`) — **`variant="secondary"`, bir xil kenglik, bir xil og'irlik**. Birortasini aksent qilish yoki kattalashtirish — **vizual ankor**: ko'z birinchi navbatda unga tushadi va shosha-pisha bosishda qo'l ham. Bu 05-RESEARCH §C.8 dagi 1-dushmanning (avtomatizatsiya tarafkashligi) **dizayn orqali kiritilgan** shakli bo'lardi.
>
> `[Keyingisi →]` ham `secondary` — u javobdan **keyin** paydo bo'ladi va raqobatchisi yo'q, ya'ni urg'uga muhtoj emas.

**Aksent ishlatilMAYDIGAN joylar (aniq taqiq):** javob tugmalari, byudjet hisoblagichi, ko'r audit lentasi, bandlik hisoblagichlari, chalkashlik matritsasi kataklari, sessiya kartalarining tugmalari, `<details>` ochilish belgisi, kun tanlagichi, zona ro'yxatidagi tanlanmagan elementlar.

### 10.4 Rang hech qachon YAGONA signal emas (WCAG 1.4.1)

| Holat | Rang kanali | Qo'shimcha kanal 1 | Qo'shimcha kanal 2 |
|-------|-------------|--------------------|--------------------|
| **Tanlangan zona** | `stroke-accent` | `stroke-width` 2 → **3** (qalinlik) | (B) ro'yxatida `aria-selected` + fon |
| **Kesishgan zona** (saqlashni to'suvchi) | `stroke-danger` | ⛔ **`stroke-dasharray`** (punktir) | (B) ro'yxatida `aria-invalid` + xato matni |
| **Rastasiz zona** | `bg-warning/20` badge | `Badge` **matni** «(rastasiz)» | `stroke-dasharray` kadrda |
| **Tekshirish kerak** (nisbat) | `bg-warning/20` | `TriangleAlert` ikonkasi | Lenta **matni** (§6.8) |
| **Qator yordamchisi oldindan ko'rishi** | `stroke-text-muted` | ⛔ **punktir** | Har poligonda rasta raqami `<text>` |
| **Band** (bandlik holati) | `Badge tone="success"` | `CircleCheckBig` | Badge **matni** «Band» |
| **Bo'sh** | `Badge tone="muted"` | `CircleDashed` | Badge **matni** «Bo'sh» |
| ⛔ **Ko'rilmagani uchun bo'sh** | `Badge tone="warning"` | `EyeOff` | Badge **matni** — to'liq, qisqartirilmagan |
| ⛔ **Qamrov yo'q** | `Badge tone="neutral"` | `CircleSlash` | Badge **matni** «Qamrov yo'q» |
| **Mos keldi** (oshkor paneli) | `tone="success"` | `CircleCheckBig` | Jumla «Javoblar mos keldi» |
| **Mos kelmadi** | `tone="warning"` | `TriangleAlert` | Jumla «Javoblar mos kelmadi» |
| **Band deb xato** (matritsa) | `bg-danger/12 text-danger-text` | Katak **yorlig'i** | Oqibat jumlasi (§11.5) |
| **Bo'sh deb xato** | `bg-warning/20 text-text` | Katak **yorlig'i** | Oqibat jumlasi |
| **Ko'r audit sessiyasi** | `bg-surface-muted` | `LockKeyhole` ikonkasi | ⛔ `border-l-4` + ikki jumla (§7.7) |

> ⛔ **«Ko'rilmagani uchun bo'sh» va «Bo'sh» turli `tone` oladi va bu MUZOKARASIZ.** Ikkalasi ham hisob-kitobda «bo'sh» ga olib keladi, lekin **ma'nosi qarama-qarshi**: biri — o'lchov, ikkinchisi — **o'lchovning yo'qligi**. Bir xil ko'rinsa, D-19 ning butun mazmuni (§11.4) yo'qolardi.

### 10.5 SVG yuzasining rang jadvali

| Element | Chizish | Sabab |
|---------|---------|-------|
| Kadr foni | `bg-text` letterbox | Qorong'i bozor kadrida chegarani ko'rsatadi |
| Zona (tanlanmagan) | `stroke: --color-surface`, `stroke-width: 2`, `fill: none` | ⛔ **Oq kontur** — kadr rangidan qat'i nazar ko'rinadi; to'ldirish **yo'q**, aks holda 40 ta zona kadrni bosib qo'yardi |
| Zona (tanlanmagan) — ikkinchi kontur | `stroke: --color-text`, `stroke-width: 4`, **ostida** | ⛔ **Ikki qatlamli kontur** (qora ostida, oq ustida) — **oq va och kadrda ham** ko'rinadi. Yagona rangli kontur qorli/yorug' kadrda yo'qolardi |
| Zona (tanlangan) | `stroke: --color-accent`, `stroke-width: 3`, `fill: accent/25` | §10.3 №4 |
| Zona (kesishgan) | `stroke: --color-danger`, `stroke-dasharray: 6 3` | §10.4 |
| Tepa ushlagichi | `fill: --color-surface`, `stroke: --color-text`, `r=5` | Kadr rangidan mustaqil |
| Tepa (fokusda) | `stroke: --color-accent`, `stroke-width: 3` + `outline` | Fokus halqasi SVG'da ham ko'rinishi shart |
| Qirra o'rtasi («qo'shish») | `fill: transparent`, `stroke: --color-surface`, `stroke-dasharray` | Faqat **tanlangan** poligonda ko'rinadi |
| Zona yorlig'i (`14-C`) | `fill: --color-bg` + `paint-order: stroke` bilan `stroke: --color-text` (3px) | Har qanday fonda o'qiladi — «matn konturi» usuli |
| Oldindan ko'rish (DL-2) | `stroke: --color-text-muted`, `stroke-dasharray: 4 4`, `fill: none` | Bu **hali mavjud emas** — punktir shuni aytadi |

---

## 11. Y-4: Bandlik va aniqlik hisoboti (AI-04 chiqishi, AI-05, AI-06, D-22)

### 11.1 Sahifaning vertikal tuzilishi

```
┌ Bandlik                                                     (h1, 24/600)
│  [◀] [Bugun] [2026-09-14 ▾] [▶]
│
├─ (A) Kunlik xulosa ────────────────────────────────────────────────────┐
│    Rasta 300 ta                                                        │
│    ✔ Band 186 · ○ Bo'sh 68 · 👁 Ko'rilmagani uchun bo'sh 4              │
│    ⊘ Qamrov yo'q 42 · 🖐 Nazoratchi tasdig'i bilan 31                   │
└────────────────────────────────────────────────────────────────────────┘
│
├─ (B) Aniqlik ──────────────────────────────────────────────────────────┐
│    Ko'rmasdan tekshirish namunasidan · 2026-08-16 – 2026-09-14 · n=612  │
│    ┌────────────────┬───────────────┬───────────────┐                  │
│    │                │ Nazoratchi:   │ Nazoratchi:   │                  │
│    │                │ band          │ bo'sh         │                  │
│    ├────────────────┼───────────────┼───────────────┤                  │
│    │ Tizim: band    │ 401           │ 23  ⚠         │                  │
│    │ Tizim: bo'sh   │ 38  ⚠         │ 150           │                  │
│    └────────────────┴───────────────┴───────────────┘                  │
│    To'g'ri: 90,0 % (87,4 – 92,2)                                       │
│    Band deb xato: 5,4 % (3,6 – 8,0) — sotuvchi bilan nizo xavfi        │
│    Bo'sh deb xato: 8,7 % (6,4 – 11,7) — yig'ilmagan patta              │
│    Rastalarning 71,7 % i band edi                                      │
└────────────────────────────────────────────────────────────────────────┘
│
├─ (C) Namuna holati ── tur, tortilgan vaqt, javobsizlar, ichki moslik
│
└─ (D) Rastalar ro'yxati ── rasta × holat, DL-5 ni ochadi
```

**Zonalar hech qachon almashmaydi.** Kun almashtirilganda (A) va (D) `aria-busy="true"` oladi; (B) **o'zgarmaydi** — u kunlik emas, **oyning to'plangan namunasi**.

### 11.2 Kun tanlagichi

4-fazadagi bilan **aynan bir xil** [MEROS: 04-UI-SPEC §6.3] va qayta ta'riflanmaydi: `[◀] [Bugun] [<input type="date" max=bugun>] [▶]`, `?day=` `nuqs` `history:"push"`, yaroqsiz `?day=` **jimgina bugunga tushadi**, kelajak kun **tanlanmaydi**.

Yagona farq: `snapshots.noFutureDays` o'rniga `occupancy.noFutureDays` — sababi boshqa («bandlik kun tugagach hisoblanadi», reja emas).

### 11.3 (A) Kunlik xulosa — AI-05 ning chiqishi

Bu **rasta darajasidagi** javob: kameralararo agregatsiya (D-20: birortasi «band» desa band) allaqachon bajarilgan, ya'ni bir rasta bir kunda **bitta** hisoblagichga tushadi.

> ⚠ **Slotlararo agregatsiya bu yerda YO'Q va bo'lmaydi ham.** «Kamida 2 slotda band» qoidasi — **BILL-01, 6-faza** [MEROS: 05-RESEARCH §D.11]. Bu sahifa «kun davomida kamida bir marta band ko'rindi» deydi, «pattaga tushadi» **demaydi**. Copy shuni aniq aytadi (§12.5) — aks holda direktor bu raqamni kunlik daromad deb o'qib, 6-faza kelganda ikki xil son ko'rardi.

### 11.4 ⛔ BESH hisoblagich — birortasi ikkinchisiga qo'shilmaydi

```html
<dl role="status">
  <div><dt>Band</dt>                      <dd>186</dd></div>
  <div><dt>Bo'sh</dt>                     <dd>68</dd></div>
  <div><dt>Ko'rilmagani uchun bo'sh</dt>  <dd>4</dd></div>   ⛔ D-19
  <div><dt>Qamrov yo'q</dt>               <dd>42</dd></div>  ⛔ D-22
  <div><dt>Nazoratchi tasdig'i bilan</dt> <dd>31</dd></div>
</dl>
```

| Qoida | Sabab |
|-------|-------|
| ⛔ **Beshala hisoblagich HAM DOIM ko'rinadi — nol bo'lsa ham** | 3 va 4-fazadagi qoidaning takrori: nol — **natija**, uning yo'qligi emas |
| ⛔ **`Ko'rilmagani uchun bo'sh` `Bo'sh` ga QO'SHILMAYDI** | D-19. `resolution_source = 'default_empty'` [MEROS: 05-RESEARCH §C.10]. Qo'shilsa, «nazoratchi ulgurmadi» degan **yagona signal** yo'qolardi va bozor jimgina pul yo'qotardi |
| ⛔ **`Qamrov yo'q` HECH QACHON `Bo'sh` ga QO'SHILMAYDI** | D-22. Bu rasta haqida **ma'lumot yo'q**, u bo'sh **emas**. Qo'shilsa aniqlik hisoboti ham jimgina noto'g'ri bo'lardi |
| `Band + Bo'sh + Ko'rilmagani… + Qamrov yo'q = Rasta soni` | ⛔ Yig'indi sarlavhada **ko'rsatiladi** («Rasta 300 ta») — o'quvchi o'zi jamlashi shart emas va nomuvofiqlik darhol ko'rinadi |
| `Nazoratchi tasdig'i bilan` — **kesishuvchi** o'lcham | U `Band`/`Bo'sh` ichida yashaydi, ya'ni yig'indiga **kirmaydi**. Yorlig'i buni aytadi va `title` da to'liq jumla (D-15: ko'r audit javobi ham shu yerda sanaladi) |
| Har hisoblagich `<dt>`/`<dd>` | Raqam va yorliq **dasturiy** bog'lanadi — «4» yolg'iz eshitilmaydi |
| `role="status"`, `alert` **EMAS** | Hisobot, ogohlantirish emas |
| ⛔ `Ko'rilmagani uchun bo'sh > 0` | Xulosa ostida **majburiy** qo'shimcha jumla: «{count} ta rasta ko'rilmadi va bo'sh deb hisoblandi. Ular uchun patta yozilmadi.» + **[Ko'rib chiqishga o'tish]** (`occupancy_review` bo'lsa) |
| ⛔ Foiz | **QO'YILMAYDI.** `186 / 300` aniqroq va yaxlitlanmaydi [MEROS: 04-UI-SPEC §6.3] |

### 11.5 (B) ⛔ Chalkashlik matritsasi — «aniqlik» YOLG'IZ e'lon qilinmaydi

05-RESEARCH §C.8.4 ochiq ogohlantiradi: *«Agar rastalarning 90% i band bo'lsa, "har doim band" deb javob beradigan soxta model 90% aniqlik oladi.»*

| Element | Kontrakt |
|---------|----------|
| Semantika | Native `<table>` + `<caption>` + `<th scope="col">` (nazoratchi javobi) + `<th scope="row">` (tizim javobi). ⛔ Diagramma **yo'q** (§3.5) |
| **To'rt katak** | Xom sonlar, `font-mono`. Ikki xato katagi `⚠` + o'z toni (§10.4) |
| ⛔ **Ikki xato TENG EMAS va matn shuni aytadi** | «**Band deb xato**» → *sotuvchi bilan nizo xavfi* (mahsulot ishonchini buzadi); «**Bo'sh deb xato**» → *yig'ilmagan patta* (faqat pul). Har biri **o'z jumlasi** bilan, `text-xs text-text-muted` |
| **Uch nisbat, uchtasi ham Wilson oralig'i bilan** | To'g'ri ulush, band deb xato ulushi, bo'sh deb xato ulushi. `lib/wilson.ts` (W0-F3) |
| ⛔ **Wald oralig'i ISHLATILMAYDI** | 05-RESEARCH §C.8.4: kichik `n` va chetdagi `p` da u ishonchsiz. Bu **kod qarori**, lekin UI'ga bevosita ta'sir qiladi — ko'rsatilgan oraliq **haqiqiy** bo'lishi shart |
| ⛔ **Bazaviy bandlik ulushi MAJBURIY** | «Rastalarning 71,7 % i band edi» — usiz «90 %» raqami **o'qilmaydi** |
| **`n` majburiy** | Sarlavhada: «n=612» + davr. Namuna hajmisiz foiz — bezak |
| ⛔ **`n < 20`** | Matritsa **o'rniga** matn: «Aniqlik hali o'lchanmadi — kamida {min} ta javob kerak. Hozircha: {n}.» ⛔ **Birorta foiz chizilmaydi** (§8.4 O-4) |
| **Davr** | Standart — **oxirgi 30 kun** (D-13: ~900 javob → ±2–3 f.p.). ⛔ Davr tanlagichi **yo'q** (§16.2) — u 8-fazaning hisobot yuzasi |
| ⛔ **Faqat `purpose = 'eval'` qatorlar** | D-14. Sarlavha buni **aniq aytadi**: «Ko'rmasdan tekshirish namunasidan» — ya'ni noaniq navbat javoblari bu raqamga **kirmaydi** |
| ⛔ **`queue_kind` bo'yicha aralashtirish** | **TAQIQLANADI.** D-15 ko'r audit javobi bandlikni ham tuzatishini aytadi, lekin **hisobot faqat ko'r namunadan** chiqadi (SC#4) |

### 11.6 (C) Namuna holati — o'lchovning o'zini ko'rsatadi

```
┌ Namuna holati ──────────────────────────────────────────────┐
│  Bugungi tur:  3-tur · 06:10 da tortilgan · 30 band          │
│  Javob berildi: 26 · Javobsiz: 4                             │
│  Aniq ayta olmadi: 2                                         │
│  Nazoratchining ichki mosligi: 94 % (takroriy 3 banddan)     │
│  Tez qaror: 1 ta (2 soniyadan tez)                           │
└──────────────────────────────────────────────────────────────┘
```

| Qator | Sabab |
|-------|-------|
| **Tur, tortilgan vaqt, hajm** | Hosila urug'ning **ko'rinadigan izi** [MEROS: 05-RESEARCH §C.8.1]. ⛔ Urug'ning **o'zi ko'rsatilmaydi** — u foydalanuvchi uchun ma'nosiz va uni ko'rsatish «tanlash mumkin» degan taassurot berardi |
| ⛔ **«Namunani qayta tortish» tugmasi YO'Q** | D-17, 1-himoya. §16.2 da aniq taqiq |
| **Javobsiz** | 05-RESEARCH §C.8, 4-dushman: javobsiz band **namunadan chiqmaydi**, u «javobsiz» deb sanaladi. Nol bo'lsa ham ko'rsatiladi |
| **Aniq ayta olmadi** | Uchinchi javobning agregati (§7.3). U **xato emas** — u kadr sifati haqidagi ma'lumot |
| **Ichki moslik** (D-16) | 05-RESEARCH §C.8.5. `< 90 %` bo'lsa `bg-warning/20 text-text` + jumla: «Tizimning o'lchangan aniqligi shu darajadan yuqori bo'la olmaydi.» Takroriy band soni `< 3` bo'lsa: «Hali yetarli takroriy band yo'q» |
| **Tez qaror** | 05-RESEARCH §C.9, 3-band: *«bloklamaydi, faqat hisobotda ko'rinadi»*. ⛔ Nazoratchiga **ko'rinmaydi** (§7.5) — u bu yerda, `report_view` ostida |
| `role="status"` | Hisobot |

### 11.7 (D) Rastalar ro'yxati va DL-5

| Element | Qoida |
|---------|-------|
| Semantika | `<ul>`/`<li>`; har element — rasta raqami + nomi + holat `Badge` + slot soni |
| Tartib | Bozor zonasi → `stall_number`, `/stalls` bilan **bir xil** |
| Filtr | ⛔ Bu fazada **faqat bitta**: «Faqat qamrovsizlarni ko'rsatish» (`?nocov=1`). Boshqa filtrlar 8-fazada |
| Holat badge'lari | §10.4 dagi besh holat; ⛔ `Ko'rilmagani uchun bo'sh` va `Qamrov yo'q` **to'liq matn bilan**, qisqartirilmaydi |
| **DL-5 — rasta tafsiloti** | Kun davomidagi har vaqt uchun bitta qator: vaqt · kamera · natija · manba (`tizim` / `nazoratchi` / `ko'rilmadi`). Har qatordan **dalil kadri** ochiladi |
| ⛔ DL-5 da tizim javobi | **Ko'rsatiladi** — bu `report_view` yuzasi, nazoratchi yuzasi emas. Direktor uchun ankor xavfi **yo'q**, chunki u yorliq ishlab chiqarmaydi |
| ⛔ DL-5 da patta/summa | **YO'Q** — 6-faza (§16.1) |
| Virtualizatsiya | ⛔ **Qurilmaydi** — 1000 `<li>` DOM uchun arzon [O'LCHANDI: M-12]. `content-visibility: auto` naqshi mavjud (`globals.css`) |

---

## 12. Matn (copywriting) kontrakti

> **[O'LCHANDI: M-13 — yakuniy copy validatsiyasi]** Quyidagi jadvallarning **51 ta shipping uz-Latn satri** to'liq override to'plami bilan transliteratordan o'tkazildi: **0 ta lotin qoldig'i**, **0 ta akronim defekti** (`/[A-ZА-ЯЁҚҒҲЎ]{2,}ъ/`), **0 ta raqam aralashgan lotin token** (`/[A-Za-z]+\.?[0-9]/`). Ya'ni 5-fazaning copy'si `uz-Cyrl.overrides.json` ga **birorta yozuv qo'shmasdan** toza chiqadi.

### 12.1 ⛔ Uchta atama qarori — kod bir narsa deydi, ekran boshqa narsa

| Kod / DB / API | Ekranda (uz-Latn) | Ekranda (ru) | Nega |
|----------------|-------------------|--------------|------|
| `blind_audit` | **Ko'rmasdan tekshirish** | **Проверка вслепую** | «Ko'r audit» — kalka va jargon. Nazoratchi uchun **nomning o'zi ko'rsatma bo'lishi** kerak: «ko'rmasdan tekshirish» ishning nima ekanini aytadi. Kod atamasi **o'zgarmaydi** — bu 4-fazadagi `slot_time` → «vaqt» qarorining aynan takrori |
| `AI` / `model` / detektor nomi | **tizim** | **система** | [O'LCHANDI: M-5] — akronim transliteratorda buziladi va foydalanuvchi uchun ma'no tashimaydi. **G-11** |
| `polygon` / `camera_zone` | **kamera zonasi** (yoki qisqa: **zona**, faqat kamera kontekstida) | **зона камеры** | D-06. ⛔ «Poligon» — muhandis so'zi (**G-16**). ⛔ Kvalifikatorsiz «zona» **bozor zonasi** bilan chalkashadi |

### 12.2 Navigatsiya va sarlavhalar

| Kalit | uz-Latn | ru |
|-------|---------|-----|
| `nav.review` | **Ko'rib chiqish** | **Проверка** |
| `nav.occupancy` | **Bandlik** | **Занятость** |
| `cameraZones.title` | Kamera zonalari | Зоны камеры |
| `review.title` | Ko'rib chiqish | Проверка |
| `review.uncertainTitle` | Noaniq navbati | Очередь неясных |
| `review.blindTitle` | **Ko'rmasdan tekshirish** | **Проверка вслепую** |
| `occupancy.title` | Bandlik | Занятость |
| `occupancy.accuracyTitle` | Aniqlik | Точность |
| `occupancy.sampleTitle` | Namuna holati | Состояние выборки |
| `occupancy.stallsTitle` | Rastalar | Места |

### 12.3 Zona muharriri (`cameraZones.*`)

| Kalit | uz-Latn | ru |
|-------|---------|-----|
| `cameraZones.zones` | Zonalar | Зоны |
| `cameraZones.zonesUsage` | {used} / {max} | {used} / {max} |
| `cameraZones.newZone` | Yangi zona | Новая зона |
| `cameraZones.drawHint` | Nuqtalarni bosib qo'ying. Yopish uchun birinchi nuqtani bosing. | Расставьте точки. Чтобы замкнуть, нажмите первую точку. |
| `cameraZones.vertices` | Tepalar | Вершины |
| `cameraZones.vertex` | Tepa {index} | Вершина {index} |
| `cameraZones.addVertex` | Tepa qo'shish | Добавить вершину |
| `cameraZones.removeVertex` | Tepani o'chirish | Удалить вершину |
| `cameraZones.moveHint` | Tepani ko'chirish: o'q tugmalari. 10 barobar tez: Shift + o'q. | Двигать вершину: стрелки. В 10 раз быстрее: Shift + стрелка. |
| **`cameraZones.minVertices`** | **Kamida uch tepa kerak** | **Нужно хотя бы три вершины** |
| **`cameraZones.maxVertices`** | **Bitta zonada ko'pi bilan {max} tepa bo'ladi** | **В одной зоне не больше {max} вершин** |
| **`cameraZones.maxZones`** | **Bitta kamerada ko'pi bilan {max} zona bo'ladi** | **На одну камеру не больше {max} зон** |
| `cameraZones.saveZones` | Zonalarni saqlash | Сохранить зоны |
| `cameraZones.unsaved` | {count} ta o'zgarish | Изменений: {count} |
| `cameraZones.discard` | Bekor qilish | Отменить |
| `cameraZones.undo` | Qaytarish | Отменить действие |
| `cameraZones.redo` | Qaytarilganni tiklash | Вернуть действие |
| `cameraZones.copyZone` | Nusxalash | Скопировать |
| `cameraZones.noStall` | (rastasiz) | (без места) |
| **`cameraZones.noStallWarning`** | **{count} ta zonaga rasta biriktirilmagan — ular hisobga kirmaydi.** | **К {count} зонам не привязано место — они не идут в расчёт.** |
| `cameraZones.assignStall` | Rastani biriktirish | Привязать место |
| `cameraZones.version` | Versiya {version} | Версия {version} |
| `cameraZones.previousVersions` | Oldingi versiyalar | Прежние версии |
| `cameraZones.frameAt` | Kadr: {time} | Кадр: {time} |
| `cameraZones.refreshFrame` | Yangi kadr olish | Взять новый кадр |
| **`cameraZones.aspectChanged`** | **Kadr o'lchami zonalar chizilgandagidan farq qiladi — zonalarni tekshiring.** | **Размер кадра отличается от того, при котором рисовались зоны — проверьте зоны.** |
| `cameraZones.needsReview` | Tekshirish kerak | Нужна проверка |
| `cameraZones.deleteZone` | Zonani o'chirish | Удалить зону |
| **`cameraZones.deleteZoneBody`** | **«{stall}» rastasining bu kameradagi zonasi o'chiriladi. Olingan kadrlarga va o'tgan kunlarning hisobiga ta'sir qilmaydi.** | **Зона места «{stall}» на этой камере будет удалена. На снятые кадры и расчёт прошлых дней это не влияет.** |

**Qator yordamchisi (DL-2):**

| Kalit | uz-Latn | ru |
|-------|---------|-----|
| `cameraZones.rowSplit` | Qator bo'yicha bo'lish | Разбить по ряду |
| `cameraZones.rowFirst` | Birinchi zona | Первая зона |
| `cameraZones.rowLast` | Oxirgi zona | Последняя зона |
| `cameraZones.rowBetween` | Oradagi rastalar: {count} ta | Мест между ними: {count} |
| `cameraZones.rowPreview` | Hosil bo'ladigan zona: {count} ta | Появится зон: {count} |
| `cameraZones.rowApply` | Bo'lish | Разбить |
| **`cameraZones.rowNeedsTwo`** | **Avval qatorning birinchi va oxirgi zonasini chizing.** | **Сначала нарисуйте первую и последнюю зону ряда.** |
| **`cameraZones.rowVertexMismatch`** | **Ikkala zonada tepalar soni bir xil bo'lishi kerak.** | **В обеих зонах должно быть одинаковое число вершин.** |
| **`cameraZones.rowCountMismatch`** | **Rastalar soni zonalar soniga to'g'ri kelmadi — hech nima qo'shilmadi.** | **Число мест не совпало с числом зон — ничего не добавлено.** |
| `cameraZones.rowSkipped` | {count} ta rastada zona bor — ular o'tkazib yuborildi. | У {count} мест зона уже есть — они пропущены. |

**Qamrov kartasi:**

| Kalit | uz-Latn | ru |
|-------|---------|-----|
| `cameraZones.coverageTitle` | Zona qamrovi | Охват зонами |
| `cameraZones.covered` | Qamrovdagi rasta | Мест в охвате |
| **`cameraZones.uncovered`** | **Qamrovsiz rasta** | **Мест вне охвата** |
| **`cameraZones.uncoveredWhy`** | **Bu rastalarni birorta kamera ko'rmaydi. Ular haqida ma'lumot yig'ilmaydi.** | **Эти места не видит ни одна камера. По ним данные не собираются.** |
| `cameraZones.camerasWithoutZones` | Zonasiz kamera | Камер без зон |
| `cameraZones.allCovered` | Hamma rasta qamrovda | Все места в охвате |

### 12.4 Ko'rib chiqish (`review.*`) — ikkala navbat uchun umumiy

| Kalit | uz-Latn | ru |
|-------|---------|-----|
| `review.today` | Bugun: {done} / {max} | Сегодня: {done} / {max} |
| `review.inQueue` | Navbatda: {count} | В очереди: {count} |
| `review.startBlind` | Ko'rmasdan tekshirishni boshlash | Начать проверку вслепую |
| `review.continueUncertain` | Navbatni davom ettirish | Продолжить очередь |
| **`review.blindLead`** | **Tasodifiy tanlangan rastalar. Tizim javobini ko'rmaysiz.** | **Случайно выбранные места. Ответ системы вы не видите.** |
| `review.uncertainLead` | Tizim aniq ayta olmagan rastalar. | Места, по которым система не смогла ответить точно. |
| **`review.question`** | **Bu rasta band edimi?** | **Было ли это место занято?** |
| `review.answerOccupied` | Band | Занято |
| `review.answerEmpty` | Bo'sh | Свободно |
| **`review.answerUnclear`** | **Aniq ayta olmayman** | **Не могу сказать точно** |
| `review.stallLine` | Rasta {stall} · {zone} | Место {stall} · {zone} |
| `review.frameLine` | {date} · {time} · Kanal {channel} | {date} · {time} · Канал {channel} |
| `review.vendorAttached` | Bu rastada sotuvchi biriktirilgan | К этому месту привязан продавец |
| `review.zoomFrame` | Kadrni kattalashtirish | Увеличить кадр |
| `review.imageUnavailable` | Rasm ochilmadi — javob bera olmaysiz | Изображение не открылось — ответить нельзя |
| `review.imageRetry` | Qayta urinish | Повторить |
| **`review.imageRequired`** | **Avval rasm ochilishi kerak.** | **Сначала должно открыться изображение.** |
| `review.next` | Keyingisi | Дальше |
| `review.exit` | Chiqish | Выйти |
| `review.answerSaved` | Javob yozildi | Ответ записан |
| **`review.exitTitle`** | **Sessiyadan chiqasizmi?** | **Выйти из сессии?** |
| **`review.exitBody`** | **Javob berilmagan band navbatda qoladi.** | **Пункт без ответа останется в очереди.** |
| **`review.exitBlindBody`** | **Javob berilmagan band hisobotda «javobsiz» deb qoladi.** | **Пункт без ответа останется в отчёте как «без ответа».** |
| `review.shortcutHint` | Tugmalar: 1 — band, 2 — bo'sh, 3 — aniq emas | Клавиши: 1 — занято, 2 — свободно, 3 — неясно |

### 12.5 Ko'rmasdan tekshirish (`review.blind*`) — ⛔ ekranning eng muhim matni

| Kalit | uz-Latn | ru |
|-------|---------|-----|
| **`review.blindBanner`** | **Tizim javobini ko'rmaysiz. Javobingiz yozilgandan keyin o'zgartirib bo'lmaydi.** | **Ответ системы вы не видите. После записи ответ изменить нельзя.** |
| `review.blindProgress` | {done} / {total} | {done} / {total} |
| `review.yourAnswer` | Sizning javobingiz | Ваш ответ |
| `review.systemAnswer` | Tizim javobi | Ответ системы |
| **`review.answersMatch`** | **Javoblar mos keldi** | **Ответы совпали** |
| **`review.answersDiffer`** | **Javoblar mos kelmadi** | **Ответы не совпали** |
| **`review.answerLocked`** | **Javobingiz yozildi va o'zgartirib bo'lmaydi.** | **Ваш ответ записан и изменению не подлежит.** |
| **`review.blindDone`** | **Bugungi tekshiruv bajarildi — {done} / {total}** | **Сегодняшняя проверка выполнена — {done} / {total}** |
| `review.backToReview` | Ko'rib chiqishga qaytish | Вернуться к проверке |

> ⛔ **`review.blindBanner` — ikki jumla, ikkalasi ham MAJBURIY.** Birinchisi «nega boshqacha», ikkinchisi «nima uchun ehtiyot bo'lish kerak». Faqat birinchisi qolsa, nazoratchi javobni **sinab ko'rish mumkin** deb o'ylardi; faqat ikkinchisi qolsa, u **nima uchun ko'rmayotganini** bilmasdi.

### 12.6 Bandlik hisoboti (`occupancy.*`)

| Kalit | uz-Latn | ru |
|-------|---------|-----|
| `occupancy.stallCount` | Rasta {count} ta | Мест: {count} |
| `occupancy.occupied` | Band | Занято |
| `occupancy.empty` | Bo'sh | Свободно |
| ⛔ **`occupancy.defaultEmpty`** | **Ko'rilmagani uchun bo'sh** | **Свободно, так как не проверено** |
| ⛔ **`occupancy.defaultEmptyWhy`** | **{count} ta rasta ko'rilmadi va bo'sh deb hisoblandi. Ular uchun patta yozilmadi.** | **{count} мест не проверены и посчитаны свободными. Патта по ним не начислена.** |
| ⛔ **`occupancy.noCoverage`** | **Qamrov yo'q** | **Нет обзора** |
| ⛔ **`occupancy.noCoverageWhy`** | **Bu rastalarni birorta kamera ko'rmaydi. Ular bo'sh emas — ular haqida ma'lumot yo'q.** | **Эти места не видит ни одна камера. Они не свободны — по ним просто нет данных.** |
| `occupancy.humanConfirmed` | Nazoratchi tasdig'i bilan | С подтверждением контролёра |
| `occupancy.humanConfirmedWhy` | Bu rastalar yuqoridagi «band» yoki «bo'sh» ichida sanalgan. | Эти места уже посчитаны выше — в «занято» или «свободно». |
| `occupancy.goToReview` | Ko'rib chiqishga o'tish | Перейти к проверке |
| **`occupancy.notBillingYet`** | **Bu — kun davomida kamida bir marta band ko'ringan rastalar. Patta hisobi alohida qoidaga ko'ra yuritiladi.** | **Это места, занятые хотя бы один раз за день. Начисление патты идёт по отдельному правилу.** |
| `occupancy.noFutureDays` | Kelajakdagi kun tanlanmaydi — bandlik kun tugagach hisoblanadi | Будущий день выбрать нельзя — занятость считается по завершении дня |
| `occupancy.showNoCoverage` | Faqat qamrovsizlarni ko'rsatish | Показать только вне обзора |

**Aniqlik bloki:**

| Kalit | uz-Latn | ru |
|-------|---------|-----|
| `occupancy.accuracyFrom` | Ko'rmasdan tekshirish namunasidan · {from} – {to} · n={n} | По выборке проверки вслепую · {from} – {to} · n={n} |
| `occupancy.humanSaysOccupied` | Nazoratchi: band | Контролёр: занято |
| `occupancy.humanSaysEmpty` | Nazoratchi: bo'sh | Контролёр: свободно |
| `occupancy.systemSaysOccupied` | Tizim: band | Система: занято |
| `occupancy.systemSaysEmpty` | Tizim: bo'sh | Система: свободно |
| `occupancy.correctShare` | To'g'ri: {value} % ({low} – {high}) | Верно: {value} % ({low} – {high}) |
| ⛔ **`occupancy.falseOccupied`** | **Band deb xato: {value} % ({low} – {high})** | **Ошибочно занято: {value} % ({low} – {high})** |
| ⛔ **`occupancy.falseOccupiedWhy`** | **Sotuvchidan nohaq patta so'ralishi mumkin — nizo xavfi.** | **С продавца могут неправомерно потребовать патту — риск спора.** |
| ⛔ **`occupancy.falseEmpty`** | **Bo'sh deb xato: {value} % ({low} – {high})** | **Ошибочно свободно: {value} % ({low} – {high})** |
| ⛔ **`occupancy.falseEmptyWhy`** | **Band rastadan patta yig'ilmay qoladi.** | **С занятого места патта не будет собрана.** |
| ⛔ **`occupancy.baseRate`** | **Rastalarning {value} % i band edi** | **Занятыми были {value} % мест** |
| ⛔ **`occupancy.notMeasuredYet`** | **Aniqlik hali o'lchanmadi — kamida {min} ta javob kerak. Hozircha: {n}.** | **Точность ещё не измерена — нужно хотя бы {min} ответов. Пока: {n}.** |

**Namuna holati:**

| Kalit | uz-Latn | ru |
|-------|---------|-----|
| `occupancy.roundLine` | {round}-tur · {time} da tortilgan · {size} band | Тур {round} · выборка в {time} · пунктов: {size} |
| `occupancy.answered` | Javob berildi | Отвечено |
| `occupancy.unanswered` | Javobsiz | Без ответа |
| `occupancy.unclearCount` | Aniq ayta olmadi | Не смог сказать точно |
| `occupancy.selfConsistency` | Nazoratchining ichki mosligi: {value} % ({count} ta takroriy banddan) | Внутренняя согласованность контролёра: {value} % (по {count} повторным пунктам) |
| **`occupancy.selfConsistencyLow`** | **Tizimning o'lchangan aniqligi shu darajadan yuqori bo'la olmaydi.** | **Измеренная точность системы не может быть выше этого уровня.** |
| `occupancy.selfConsistencyNotEnough` | Hali yetarli takroriy band yo'q | Повторных пунктов пока недостаточно |
| `occupancy.fastDecisions` | Tez qaror: {count} ta ({seconds} soniyadan tez) | Быстрых решений: {count} (быстрее {seconds} с) |
| `occupancy.resolutionSource` | Manba | Источник |
| `occupancy.sourceSystem` | Tizim | Система |
| `occupancy.sourceHuman` | Nazoratchi | Контролёр |
| `occupancy.sourceNotReviewed` | Ko'rilmadi | Не проверено |

### 12.7 Xato kontrakti — SABAB + NIMA QILISH KERAK

`lib/zone-errors.ts` `nvrErrorView`/`captureErrorView` naqshini davom ettiradi, lekin **`actor` ustuni YO'Q**: 5-fazaning xatolarining hammasi **foydalanuvchining o'z amali** bilan bog'liq (u chizyapti yoki javob beryapti), ya'ni «kim tuzatadi?» savoli **har doim bir xil javobga** ega va uni ekranga chiqarish shovqin bo'lardi.

| Kalit | uz-Latn | ru |
|-------|---------|-----|
| `cameraZones.errorCauseLabel` | Sabab | Причина |
| `cameraZones.errorFixLabel` | Nima qilish kerak | Что делать |

**`zone_self_intersecting`** — `danger`

| | uz-Latn | ru |
|---|---------|-----|
| `errorCause` | Zona o'zi bilan kesishgan — chegaralari bir-birini kesib o'tadi. | Зона пересекает саму себя — её границы накладываются. |
| `errorFix` | Tepalarni shunday joylashtiringki, chegara chizig'i kesishmasin. Kesishgan zona qizil punktir bilan belgilangan. | Расставьте вершины так, чтобы граница не пересекалась. Пересекающаяся зона отмечена красным пунктиром. |

**`zone_too_few_points`** — `danger`

| | uz-Latn | ru |
|---|---------|-----|
| `errorCause` | Zonada uchtadan kam tepa qolgan. | В зоне осталось меньше трёх вершин. |
| `errorFix` | Tepa qo'shing yoki zonani o'chirib, qaytadan chizing. | Добавьте вершину либо удалите зону и нарисуйте заново. |

**`zone_stall_taken`** — `warning`

| | uz-Latn | ru |
|---|---------|-----|
| `errorCause` | Bu rastaning shu kameradagi zonasi allaqachon bor. | У этого места уже есть зона на этой камере. |
| `errorFix` | Mavjud zonani tahrirlang yoki boshqa rastani tanlang. Bir rasta bir necha kamerada bo'lishi mumkin — bu normal. | Отредактируйте существующую зону или выберите другое место. Одно место может быть на нескольких камерах — это нормально. |

**`zone_no_frame`** — `warning`

| | uz-Latn | ru |
|---|---------|-----|
| `errorCause` | Bu kamerada hali yaroqli kadr yo'q, shuning uchun zona chizib bo'lmaydi. | На этой камере ещё нет годного кадра, поэтому зону не нарисовать. |
| `errorFix` | Kadr olish bo'limida kamera holatini tekshiring. Birinchi yaroqli kadr kelgach, bu sahifa o'zi ochiladi. | Проверьте состояние камеры в разделе съёмки кадров. Как появится первый годный кадр, страница откроется сама. |

**`review_budget_exhausted`** — `warning`

| | uz-Latn | ru |
|---|---------|-----|
| `errorCause` | Bugungi byudjet tugadi — {max} / {max}. | Сегодняшний лимит исчерпан — {max} / {max}. |
| `errorFix` | Ertaga davom etadi. Byudjet diqqatni saqlash uchun qo'yilgan: shoshib berilgan javob ma'lumotni buzadi. | Продолжится завтра. Лимит нужен, чтобы сохранить внимание: поспешный ответ портит данные. |

**`blind_answer_locked`** — `warning` · ⛔ **D-17 ning foydalanuvchiga ko'rinadigan yuzasi**

| | uz-Latn | ru |
|---|---------|-----|
| `errorCause` | Bu bandga javob allaqachon yozilgan. | По этому пункту ответ уже записан. |
| `errorFix` | Ko'rmasdan tekshirishda javob bir marta yoziladi va o'zgartirilmaydi — o'lchov shu bilan halol qoladi. Keyingi bandga o'ting. | В проверке вслепую ответ записывается один раз и не меняется — так измерение остаётся честным. Перейдите к следующему пункту. |

**`review_sample_not_drawn`** — `neutral`

| | uz-Latn | ru |
|---|---------|-----|
| `errorCause` | Bugungi namuna hali tortilmagan. | Сегодняшняя выборка ещё не сформирована. |
| `errorFix` | Namuna kunlik kadrlar yig'ilgandan keyin o'zi tortiladi. Qo'lda tortish mumkin emas — bu tanlovning tasodifiyligini saqlaydi. | Выборка формируется сама после сбора дневных кадров. Вручную её не сформировать — так сохраняется случайность отбора. |

### 12.8 Toastlar — beshta

| Kalit | uz-Latn | ru | Tur |
|-------|---------|-----|-----|
| `cameraZones.toastSaved` | Zonalar saqlandi | Зоны сохранены | success |
| `cameraZones.toastZoneDeleted` | Zona o'chirildi | Зона удалена | success |
| `cameraZones.toastRowSplit` | {count} ta zona qo'shildi — har birini tekshiring | Добавлено зон: {count} — проверьте каждую | success |
| `review.toastAnswerSaved` | Javob yozildi | Ответ записан | success |
| `review.toastSessionDone` | Bugungi ish bajarildi | Сегодняшняя работа выполнена | success |

### 12.9 Bo'sh holatlar — oltitasi, har biri boshqa keyingi qadam bilan

| # | Kalit | uz-Latn sarlavha / tavsif | Keyingi qadam |
|---|-------|---------------------------|---------------|
| **E-1** | `cameraZones.emptyNoFrame` | **Bu kamerada hali yaroqli kadr yo'q** / Zona chizish uchun kadr kerak. Kamera kadr berganidan keyin bu sahifa ochiladi. | **[Kadr olishga o'tish]** → `/snapshots` |
| **E-2** | `cameraZones.emptyNoZones` | **Hali zona chizilmagan** / Rastalarni kadrda belgilang — shundan keyin tizim ularning band yoki bo'shligini aniqlaydi. | **[+ Yangi zona]** |
| **E-3** | `review.emptyUncertain` | **Noaniq band qolmadi** / Tizim bugun shubhalangan hamma rasta ko'rib chiqilgan. | Amal **yo'q** |
| **E-4** | `review.emptyBlindDone` | **Bugungi tekshiruv bajarildi** / {done} / {total} band baholandi. Ertaga yangi namuna tortiladi. | **[Ko'rib chiqishga qaytish]** |
| **E-5** | `review.emptyBudget` | **Bugungi byudjet tugadi** / {max} / {max}. Ertaga davom etadi. | Amal **yo'q** — ⛔ «Yana ko'rish» **YO'Q** |
| **E-6** | `occupancy.emptyDay` | **Bu kunda bandlik hisoblanmagan** / Bu kunda yaroqli kadr yoki chizilgan zona bo'lmagan. | **[Zona qamrovini ko'rish]** → `/cameras` |

⛔ **E-3 va E-4 — tabrik EMAS, fakt.** «Barakalla!», «Ajoyib!» kabi matnlar **taqiqlanadi**: ular ishni o'yinga aylantiradi va bu §7.3 dagi progress-bar taqig'i bilan bir mantiq.

⛔ **E-6 «0 band» EMAS** (§8.4 O-3): nol bandlik va hisoblanmagan bandlik — **turli narsa**.

### 12.10 ⛔ Taqiqlangan so'zlar

| Taqiq | Nima uchun | Darvoza |
|-------|------------|---------|
| ⛔ **`AI`, `CV`, `ONNX`, `RF-DETR`, `JSON`** (uchala tilda) | [O'LCHANDI: M-5] Transliteratorda buziladi (`АИ`, `CВ` — aralash alifbo) **va** foydalanuvchi uchun ma'no tashimaydi. O'rniga **`tizim`** | **G-11** |
| ⛔ **«poligon» / «полигон»** | Muhandis atamasi. Foydalanuvchi uchun bu **zona** | **G-16** |
| ⛔ **«dataset» / «датасет», «konfidens», «model versiyasi»** | O'sha sinf. Trening ma'lumoti — bu fazada foydalanuvchi yuzasi **emas** (D-25) | **G-16** |
| ⛔ **Qamrovsiz rasta uchun «bo'sh» / «свободн»** | **D-22 ning copy shakli.** `noCoverage` kalitlarida «bo'sh» so'zi bo'lsa, farq **matn darajasida** yo'qolardi va hisobot jimgina noto'g'ri o'qilardi | **G-15** |
| ⛔ **«tuzatish» / «исправить»** tizim javobiga nisbatan | **D-12:** tizim javobi **hech qachon o'zgartirilmaydi**; nazoratchi qarori — **alohida yozuv**. «Tuzatish» so'zi ustiga yozishni anglatib, D-12 ni jimgina yolg'onga aylantirardi. To'g'ri so'z — **«javob berish»** | **G-16** |
| ⛔ **«hammasini tasdiqlash» / «подтвердить все»** va shu ma'nodagi har qanday shakl | **D-18.** So'z copy'ga kirsa, keyingi ijrochi uni **amalga oshirishga** urinardi | **G-18** |
| ⛔ **«namunani qayta tortish» / «пересобрать выборку»** | D-17, 1-himoya. §16.2 | **G-18** |
| **«xatolik yuz berdi»** yolg'iz | Sababsiz xato — 3-faza D-02 ning taqig'i | **G-17** |
| **«Barakalla», «Ajoyib»** va shu kabi tabriklar | §12.9 | Ko'rik |

### 12.11 Transliteratsiya kontrakti

| # | Qoida | Holat |
|---|-------|-------|
| **1** | Raqam aralashgan lotin token `messages/*.json` ga **kiritilmaydi** (4-faza M-3) | ✅ [O'LCHANDI: M-13 — 0 ta] |
| **2** | Sof harfli akronim override **talab qiladi** — **lekin 5-fazada akronim COPY'GA UMUMAN KIRMAYDI** (§12.10), ya'ni `uz-Cyrl.overrides.json` **o'zgarmaydi** | ✅ [O'LCHANDI: M-5] |
| **3** | ⚠ **Hedge so'zi («Ehtimol») bu fazada ISHLATILMAYDI** | 3-fazaning G-3 darvozasi `HEDGED_NAMESPACES = ["cameras","snapshots"]` ni skanerlaydi [O'LCHANDI: M-9]. 5-faza namespace'larini qo'shish darvozani kengaytirishni talab qilardi; hedging esa **arzonlashsa ma'nosini yo'qotadi** (4-faza Qoida 4). 5-fazaning xatolari **taxminiy emas** — ular DB va geometriyadan aniq kelib chiqadi, ya'ni hedge kerak **emas** |
| **4** | 3-fazadan meros taqiqlar kuchda: `NVR'ga` → `NVR qurilmasiga`, `Asia/Tashkent` → `Toshkent` | ✅ 5-faza copy'sida birortasi yo'q |
| **5** | ⛔ `ъ` diskriminatori — **`/[A-ZА-ЯЁҚҒҲЎ]{2,}ъ/u`**, `/[A-Za-z]ъ/` **emas** | [O'LCHANDI: M-10, M-13] Mavjud `gen-cyrillic.test.mjs` naqshi **qayta ishlatiladi**, ikkinchi nusxa yozilmaydi |
| **6** | Mas'uliyat: `uz-Latn.json` va `ru.json` — **qo'lda**; `uz-Cyrl.json` — **avtomatik** (`npm run i18n:gen`); `uz-Cyrl.overrides.json` — ⛔ **tegilmaydi** | — |

### 12.12 Mobil va uch til [O'LCHANDI: M-6]

O'rtacha nisbat **1,03×**, lekin taqsimot keng va uchta oqibati bor:

| Kalit | uz-Latn | ru | Nisbat | Oqibat |
|-------|---------|-----|--------|--------|
| `review.evidenceLabel` («Dalil rasmi») | 11 | 21 | **1,91×** | Faqat `title`/`aria-label` da ishlatiladi — **ko'rinadigan yorliq emas**, ya'ni layoutga ta'sir qilmaydi |
| `review.answerEmpty` («Bo'sh») | 5 | 8 | **1,60×** | ⛔ Javob tugmalari **teng kenglikda** (`flex-1`) va matn **qisqartirilmaydi** — rus tilida tugmalar balandroq bo'lishi mumkin, bu **qabul qilinadi** |
| `review.answerOccupied` («Band») | 4 | 6 | 1,50× | O'sha |
| `occupancy.defaultEmpty` | 24 | 30 | 1,25× | ⛔ Badge **`truncate` QILINMAYDI** — u ma'no tashiydi; konteyner o'sadi |

| Zona | ≥768px | <768px |
|------|--------|--------|
| **Y-1 muharrir** | Ikki ustun: kadr (2/3) + zona ro'yxati (1/3) | ⛔ **Ustma-ust**: kadr yuqorida, ro'yxat pastda. Ro'yxat `<details>` ga **solinmaydi** — u yagona klaviatura yo'li (§13.4) |
| **Y-1 asboblar** | Bir qatorda | `flex-wrap`, 2 qator; tugmalar `min-h-11` |
| **Y-2/Y-3 sessiya** | Kadr markazda, `max-w-3xl` | Kadr to'liq kenglikda; ⛔ javob tugmalari **`sticky bottom-0`** + `bg-surface` + yuqori chegara — barmoq ostida turadi |
| **Y-3 lenta** | `sticky top-0` | O'sha; matn 2–3 qatorga tushadi va **qisqartirilmaydi** |
| **Y-4 hisoblagichlar** | Bir qatorda `flex-wrap` | 2–3 qator. ⛔ **Hech biri yashirilmaydi** |
| **Y-4 matritsa** | To'liq sig'adi | Gorizontal aylantirish (`role="region"` + `tabIndex={0}`, 4-faza naqshi); nisbatlar **matn sifatida** ostida takrorlangan, ya'ni aylantirmagan foydalanuvchi ham javobni oladi |
| **DL-1…DL-5** | `Dialog` markazda | `sheetOnMobile` |

⛔ **Mobilda birorta komponent boshqasiga ALMASHMAYDI** [MEROS: 04-UI-SPEC §13.2]. Sabab o'sha: bir xil ma'lumot ikki xil semantikaga ega bo'lardi va klaviatura naqshi ikki marta yozilardi.

**Sana va vaqt:** slot vaqti `HH:mm` `font-mono` (uchala tilda bir xil); biznes-kun `next-intl` + hafta kuni; `?day=` **hech qachon mahalliylashtirilmaydi**. Toshkent **UTC+5, yozgi vaqt YO'Q** — DST himoyasi qurilmaydi.

---

## 13. Qulaylik (a11y)

### 13.1 Umumiy talablar

| Talab | Kontrakt | Tekshiruv |
|-------|----------|-----------|
| **Kontrast — matn** | AA 4.5:1. Yangi juftlik **yo'q** (§10.1) | §10 |
| **Kontrast — boshqaruv elementi** | ≥3:1 → `border-border-ui` (3,64:1) barcha `Input`/`Select`/checkbox'da | WCAG 2.2 SC 1.4.11 |
| **Kontrast — SVG grafikasi** | ⛔ Zona konturi **ikki qatlamli** (qora ostida 4px, oq ustida 2px, §10.5) — u **har qanday kadr fonida** ≥3:1 beradi. Yagona rangli kontur qorli yoki qorong'i kadrda yo'qolardi | WCAG 2.2 SC 1.4.11 (Non-text) |
| **Fokus ko'rinishi** | Global `:focus-visible` halqasi. ⛔ SVG ichida: tepa doirasi `stroke-accent` + `stroke-width: 3` **va** `outline` — brauzerlar SVG'da `outline` ni turlicha chizadi, shuning uchun **ikki kanal** | Klaviatura UAT |
| **Rang yagona signal emas** | §10.4 jadvali | Komponent testi |
| **Nishon o'lchami** | ≥44×44px: javob tugmalari (48px), tepa ro'yxati qatorlari, zona ro'yxati qatorlari, kun tanlagichi. ⚠ SVG tepa ushlagichi **24px** — «Essential» istisnosi + majburiy kompensatsiya (§9.2) | §9.2 |
| **Til atributi** | `<html lang>` locale bo'yicha; DB kontenti (rasta nomi, kamera nomi) `lang` bilan belgilanMAYDI | [MEROS: 1-faza D-16] |
| **Harakat** | `prefers-reduced-motion`: `Skeleton` pulsi va `Loader2` aylanishi o'chadi. ⛔ Zona sudralayotganda **animatsiya yo'q** — u to'g'ridan-to'g'ri kuzatib boradi (`transition` **qo'yilmaydi**), ya'ni bu qoida sudrash uchun ahamiyatsiz | `motion-reduce:animate-none` |
| **Matn kattalashtirish** | 200% zoomda layout buzilmaydi. ⛔ SVG kadri `viewBox` bilan masshtablanadi, ya'ni zoom **kadrni ham kattalashtiradi** — bu **foyda**, muammo emas | `maximum-scale` **qo'yilmaydi** |
| **Forma yorliqlari** | Har boshqaruv elementida `<label htmlFor>`; placeholder yorliq o'rnini **bosmaydi** | `Field` primitivi |

### 13.2 `fieldset` / `legend`

**Ikkita mantiqiy guruh:**

```tsx
{/* DL-2 — qator yordamchisi */}
<fieldset className="m-0 border-0 p-0">
  <legend className="mb-4 text-lg font-semibold">{t("cameraZones.rowSplit")}</legend>
  <Field id="row-first" …/> <Field id="row-last" …/>
</fieldset>

{/* Javob guruhi — Y-2 va Y-3 */}
<fieldset className="m-0 border-0 p-0">
  <legend className="mb-2 text-lg font-semibold">{t("review.question")}</legend>
  {/* uchta tugma */}
</fieldset>
```

| Qoida | Sabab |
|-------|-------|
| ⛔ **«Bu rasta band edimi?» — `<legend>`, oddiy `<p>` emas** | Skrinrider foydalanuvchisi tugmaga fokus qilganda savolni **eshitmasdi**. `<legend>` uni har tugma bilan birga e'lon qiladi |
| ⛔ Javob tugmalari — `<button>`, **radio EMAS** | Radio guruh «tanlash → tasdiqlash» ikki qadamini anglatadi va u **ikkinchi tugmani** talab qilardi. Bitta bosish = bitta qaror (D-18) |
| Zona ro'yxati **`fieldset` EMAS** | U navigatsiya, kiritma emas |
| `<legend>` **`sr-only` EMAS** | U ko'rinadigan sarlavha [MEROS: 03-UI-SPEC §12.2] |
| `display: contents` **ISHLATILMAYDI** | `<legend>` semantikasini buzadi |

### 13.3 `aria-disabled`, `disabled` EMAS

| Element | Qachon | Bosilganda |
|---------|--------|------------|
| Uchala javob tugmasi | Rasm yuklanmagan | So'rov **yuborilmaydi**; `role="status"` `review.imageRequired` ni e'lon qiladi |
| Uchala javob tugmasi (Y-3) | Javob allaqachon yozilgan | `role="status"` `review.answerLocked` |
| `[+ Yangi zona]` | `zones >= MAX_ZONES_PER_CAMERA` | `role="status"` `cameraZones.maxZones` |
| «Tepani o'chirish» | Tepa soni = 3 | `role="status"` `cameraZones.minVertices` |
| «Tepa qo'shish» | Tepa soni = `MAX_VERTICES_PER_ZONE` | `role="status"` `cameraZones.maxVertices` |
| `[Qator bo'yicha bo'lish]` | Ikki zona tanlanmagan | `role="status"` `cameraZones.rowNeedsTwo` |
| `[Zonalarni saqlash]` | `isPending` yoki kesishgan zona bor | Matn «Saqlanmoqda» / xato bloki fokusga oladi |
| `[Ko'rmasdan tekshirishni boshlash]` | Byudjet tugagan | `role="status"` `review.emptyBudget` tavsifi |

⛔ `disabled` **ishlatilmaydi**: fokus olmaydi va skrinrider uni o'qimaydi — «nega bosilmayapti?» javobsiz qolardi [MEROS: 02-UI-SPEC §6.6].

### 13.4 ⛔⛔ Klaviatura bilan zona tahrirlash — ro'yxat BIRLAMCHI, SVG ko'zgu

Bu bo'lim hujjatning **ikkinchi eng muhim** qismi (birinchisi — §7.7). Sabab: **kadr ustiga bosish klaviatura bilan bajarilmaydi.** Agar chizish faqat sichqoncha bilan bo'lsa, klaviatura foydalanuvchisi bu ekrandan **butunlay chiqarib tashlanadi** — WCAG 2.1.1 ning to'g'ridan-to'g'ri buzilishi.

**Yechim [QAROR]: ochiqlik daraxti ROY'XATDA yashaydi, SVG esa uning KO'ZGUSI.**

```
SVG konteyner:  aria-hidden="true"          ← ⛔ ochiqlik daraxtida YO'Q
Zona ro'yxati:  <ul> → <li> → <button>      ← ⛔ YAGONA ochiqlik yuzasi
                  tanlanganda ochiladi:
                <ul> → <li> → <button>      ← tepalar, har biri 44px
```

| Nima uchun bu to'g'ri yechim | |
|---|---|
| **Bitta haqiqat manbai** | SVG ham, ro'yxat ham ochiq bo'lsa, skrinrider har poligonni **ikki marta** e'lon qilardi va foydalanuvchi qaysi biri «haqiqiy» ekanini bilmasdi |
| **jsdom'da to'liq testlanadi** | Ro'yxat — oddiy DOM. Bu D-05 ning test argumentini **ochiqlikda ham** amalga oshiradi |
| **`role="application"` KERAK EMAS** | U butun sahifada skrinriderning brauz rejimini o'chirardi — qo'pol va xavfli chora |
| **Sichqonchali foydalanuvchi hech nima yo'qotmaydi** | SVG to'liq interaktiv qoladi; `aria-hidden` faqat **ochiqlik daraxtiga** ta'sir qiladi, hodisalarga emas |

**Klaviatura kontrakti — tepalar ro'yxati (roving tabindex, 4-fazadagi `capture-grid` naqshi):**

| Tugma | Amal |
|-------|------|
| `Tab` | Ro'yxatga **bitta** to'xtash. Faol tepa `tabIndex={0}`, qolganlari `-1` |
| `ArrowUp` / `ArrowDown` | ⛔ Fokuslangan tepani **1 render piksel** yuqoriga/pastga siljitadi |
| `ArrowLeft` / `ArrowRight` | ⛔ Fokuslangan tepani **1 render piksel** chapga/o'ngga siljitadi |
| `Shift` + o'q | **10 render piksel** |
| `Home` / `End` | Poligonning **birinchi / oxirgi** tepasiga fokusni ko'chiradi |
| `PageUp` / `PageDown` | Oldingi / keyingi **tepaga** fokus (o'qlar siljitishga band bo'lgani uchun) |
| `Enter` | Fokuslangan tepadan **keyin** yangi tepa qo'shadi (qirra o'rtasiga) |
| `Delete` / `Backspace` | Fokuslangan tepani o'chiradi (3 tepada — `aria-disabled` xulqi) |
| `Esc` | Zonadan chiqib, zonalar ro'yxatiga qaytadi |
| `Ctrl+Z` / `Ctrl+Shift+Z` | Undo / redo (sahifa darajasida) |

> ⚠ **O'q tugmalari siljitadi, ko'chirmaydi — va bu ataylab.** Ro'yxatda o'qlar odatda fokusni ko'chiradi. Bu yerda **siljitish asosiy amal**: tepa tanlangandan keyin foydalanuvchi 90% vaqt uni **ko'chirishga** harakat qiladi. Fokus ko'chirish `PageUp`/`PageDown` va `Home`/`End` ga berilgan, va **ko'rinadigan ko'rsatma** (`cameraZones.moveHint`) ro'yxat tepasida **doim turadi** — `<details>` ichida emas.

**Klaviatura bilan YANGI zona yaratish** — ⛔ **sichqonchasiz yo'l MAJBURIY:**

| Qadam | Xulq |
|-------|------|
| `[+ Yangi zona]` bosiladi (klaviatura bilan ham) | ⛔ Kadr **markazida** standart to'rtburchak yaratiladi: kenglik `0.20`, balandlik `0.15` |
| | ⛔ **«Bosib chizing» rejimi klaviatura foydalanuvchisiga TAKLIF QILINMAYDI** — u bajarilmaydigan yo'l |
| Fokus | Darhol **birinchi tepaga** ko'chadi |
| `role="status"` | «Yangi zona qo'shildi. Tepalarni o'q tugmalari bilan ko'chiring.» |
| Rasta biriktirish | Zona ro'yxatidan DL-1 (oddiy forma) |

Sichqonchali foydalanuvchi ham shu yo'ldan yurishi mumkin — ya'ni bu **muqobil emas, ikkinchi to'liq yo'l**. «Bosib chizish» esa qo'shimcha tezlik beradi.

**Har elementning nomi:**

| Element | `aria-label` |
|---------|--------------|
| Zona `<li>` tugmasi | `«Rasta 14-C · Sabzavot qatori · 4 tepa»` (rastasiz bo'lsa: `«Rasta biriktirilmagan · 4 tepa»`) |
| Tepa `<li>` tugmasi | `«Tepa 2 · 0,318 · 0,441»` — koordinata **uch xonagacha**, o'zgarganda `aria-live` **QILINMAYDI** (har piksel e'lon qilinsa skrinrider bo'g'ilardi) |
| Koordinata o'zgarishi | ⛔ **`debounce` 500 ms** dan keyin bitta `role="status"` e'loni: «Tepa 2: 0,318 · 0,441» |
| SVG konteyner | `aria-hidden="true"` — nomi **yo'q** |

### 13.5 Y-2 / Y-3 klaviaturasi va fokus tartibi

| Vaziyat | Xulq |
|---------|------|
| Sessiya ochildi | ⛔ Fokus **rasm konteynerida** (`tabIndex={-1}` + `focus()`), javob tugmasida **emas**. Sabab: tugmada fokus «bos» degan taklif, rasmda fokus esa «qara» degan taklif — va bu ekranning butun mazmuni **qarash** |
| Rasm yuklandi | `role="status"`: «Rasm tayyor» + rasta va vaqt. ⛔ Tugmalarga fokus **avtomatik ko'chmaydi** |
| `1` / `2` / `3` | Javob yuboriladi. ⛔ `event.repeat === true` bo'lsa **e'tiborsiz qoldiriladi** (§7.3) |
| ⛔ Tugma bosilib turilsa | **Bitta javob** yuboriladi, ketma-ket emas |
| Javob yuborildi | `role="status"`: «Javob yozildi» (Y-2) / oshkor paneli matni (Y-3). Fokus **`[Keyingisi →]`** ga ko'chadi |
| `Enter` (oshkor panelida) | Keyingi bandga o'tadi |
| Keyingi band keldi | Fokus **yana rasm konteynerida** — sikl yopiladi |
| `Esc` | Sessiyadan chiqish (DL-4 orqali) |
| Kadrni kattalashtirish dialogi | Radix: tuzoq, `Esc`, fokus **ochgan elementga** qaytadi |
| Tasdiq dialogi | Fokus **[Bekor qilish]** da — hech qachon destruktiv tugmada |

### 13.6 Jonli hududlar reyestri

⛔ **Bir vaqtda ikkitadan ortiq faol bo'lmaydi** [MEROS: 04-UI-SPEC §12.6].

| Hudud | Rol | Nima e'lon qiladi | Qayerda |
|-------|-----|-------------------|---------|
| Muharrir holati | `role="status"` | Zona qo'shildi/o'chirildi, tepa koordinatasi (debounce 500 ms), chegara xabarlari | Y-1 |
| Zona/forma xatosi | `role="alert"` | Sabab + tuzatish | Y-1, Y-4 |
| Sessiya holati | `role="status"` | Rasm tayyor, javob yozildi, oshkor natijasi, byudjet | Y-2, Y-3 |
| Kunlik xulosa | `role="status"` | Besh hisoblagich + `defaultEmptyWhy` | Y-4 |

| ⛔ E'lon QILINMAYDIGAN narsalar | Sabab |
|---|---|
| Har `pointermove` da koordinata | Skrinriderni yaroqsiz qilardi |
| Zona ro'yxatining har qayta chizilishi | O'sha |
| Y-4 poll yangilanishi (60 s) | 4-fazadagi qoida: jimgina yangilanadi; foydalanuvchi xulosani o'zi o'qiydi |
| ⛔ **Ko'r audit lentasi `role="alert"` OLMAYDI** | U sahifa yuklanganda mavjud bo'lgan **holat**, yangi hodisa emas. `role="alert"` uni har band almashganda qayta o'qitardi va nazoratchi uni **eshitmay qo'yardi** — ya'ni himoya kuchsizlanardi. U `<h2>` + doimiy matn sifatida **bir marta** o'qiladi va sarlavha navigatsiyasida topiladi |

---

## 14. Ma'lumot chegaralari va registry xavfsizligi

### 14.1 shadcn va uchinchi tomon registrlari

| Registry | Ishlatilgan bloklar | Safety Gate |
|----------|---------------------|-------------|
| shadcn (rasmiy) | — | **Qo'llanmaydi** — `components.json` yo'q, `shadcn init` bajarilmadi (§3.4) [O'LCHANDI: M-1] |
| Uchinchi tomon registrlari | **YO'Q** | **Qo'llanmaydi** — birorta uchinchi tomon registri e'lon qilinmadi |

**`npx shadcn add` bu fazada ishlatilmaydi.** Barcha komponentlar mavjud bog'liqliklar ustida qo'lda yoziladi.

**Vendored artefakt:** 3-fazadagi `public/vendor/go2rtc/` ga **tegilmaydi**; yangi vendored fayl **qo'shilmaydi**. **Yangi npm paketi ham qo'shilmaydi** (§3.5).

### 14.2 Kadr yuzasi — 4-fazadan meros, o'zgarishsiz

| Narsa | Qoida |
|-------|-------|
| SeaweedFS / S3 endpointi | **Foydalanuvchiga hech qachon** — na to'g'ridan-to'g'ri, na proxy orqali |
| Presigned URL | ⛔ **Berilmaydi va so'ralmaydi.** Kadr **core-api orqali proxy**: `GET /api/v1/snapshots/{id}/image` |
| `object_key`, bucket, region, access key | UI'da **hech qanday ko'rinishda** |
| Kadrni yuklab olish / ulashish | ⛔ **YO'Q** — Y-1, Y-2, Y-3, Y-4 va DL-5 ning **hech birida** |
| ⛔ **Kadrni SVG'ga `<image href>` bilan qo'yish** | **Ruxsat**, lekin `href` faqat `/api/v1/snapshots/{id}/image` bo'ladi. `crossOrigin` **qo'yilmaydi** — u boshqa manba borligini anglatardi |
| ⛔ **Kadrni `canvas` ga chizib `toDataURL()` qilish** | **TAQIQLANADI** — u kadrni yuklab olinadigan qilardi va `audit_read` chegarasini chetlab o'tardi. Bu D-05 ning **qo'shimcha** foydasi: SVG'da bunday yo'l yo'q |
| Kadr o'qilishi | `audit_read` yozadi [MEROS: 2-faza D-09] |

**Frontend grep darvozasi (4-fazadagi G-4 davom etadi):** `frontend/src` da `presign`, `X-Amz`, `s3.`, `seaweed`, `:8333` **bo'lmasligi** shart.

### 14.3 ⛔⛔ Ko'r payload chegarasi — bu fazaning O'Z xavfsizlik chizig'i

Bu 4-fazadagi «ombor yuzasi» qoidasining ekvivalenti, lekin **himoya qilinadigan narsa boshqa**: bu yerda maxfiy narsa — **tizimning javobi**, va uni ko'radigan odam — **bizning o'z nazoratchimiz**.

| Qatlam | Kontrakt | Darvoza |
|--------|----------|---------|
| **1. Server** | `GET /review/blind/next` javobida `verdict`, `confidence`, `model_version`, `effective_verdict`, `resolution_source` **kalitlarining o'zi yo'q** (`None` emas). **[TALAB]** Backend testi javobni **rekursiv** skanerlaydi | backend |
| **2. Klient sxemasi** | `blindAuditItemSchema` — ⛔ **`z.strictObject`**. Taqiqlangan kalitli payload **parse paytida throw qiladi**, ya'ni server sizib ketsa **klient qizaradi** | **G-13** |
| **3. Modul chegarasi** | `lib/blind-audit-queries.ts` va `components/blind-audit/**` da taqiqlangan **nomlar umuman uchramaydi** (§5.3) | **G-12** |
| **4. Kesh** | ⛔ Ko'r so'rovlar `gcTime: 0`, `staleTime: 0`, `refetchOnWindowFocus: false`. Javob yozilgach `queryClient.removeQueries({ queryKey: [marketId, "blind-audit"] })` — ⛔ **`invalidate` emas, `remove`** | **G-14** |
| **5. Oshkor ma'lumot** | ⛔ **`useMutation` ning `data` sidan**, `useQuery` dan **emas** (§7.7). Ya'ni u kesh grafiga **umuman tushmaydi** | **G-14** |
| **6. `shown_ai_verdict`** | ⛔ Klient bu maydonni **hech qachon yubormaydi** — u serverda hisoblanadi. Klient yuborsa, u **yolg'on gapira olardi** va DB `CHECK` i aldangan bo'lardi | **G-14** |

**Taqiqlangan nomlar reyestri (G-12 va G-13 shu ro'yxatdan oziqlanadi):**

```
verdict        aiVerdict        ai_verdict
confidence     aiConfidence     ai_confidence
modelVersion   model_version
effectiveVerdict  effective_verdict
resolutionSource  resolution_source
shownAiVerdict    shown_ai_verdict
purpose        thresholdsVersion   thresholds_version
```

> ⚠ **`purpose` ham ro'yxatda va bu ataylab** (D-14): `eval`/`train` belgisi ko'rinsa, «bu baholash uchun ekan» degan e'tibor farqi tug'ilardi va 70/30 bo'linishi ma'nosini yo'qotardi (§7.5).

> ⚠ **Qamrov chegarasi majburiy** [MEROS: 04-faza darvoza qoidasi]: `components/blind-audit/` katalogi mavjud bo'lsa, **kamida 3 fayl** bo'lishi shart. Aks holda darvoza bo'sh to'plamda ishlab, **yashil bo'lib turgan holda mavjudligini yo'qotardi**.

## 15. Darvozalar (G-N)

Raqamlash 4-fazadan **davom etadi** (G-1…G-10 band) — darvoza skriptlari bitta katalogda yashaydi va raqam takrorlanishi jurnalda chalkashlik tug'dirardi.

| # | Darvoza | Fayl | Nimani tekshiradi | Nima uchun mavjud |
|---|---------|------|-------------------|-------------------|
| **G-11** | **Akronim taqig'i** | `scripts/zone-copy.test.mjs` (yangi) | Uchala `messages/*.json` ning `cameraZones.*` / `review.*` / `occupancy.*` kalitlarida `AI`, `CV`, `ONNX`, `RF-DETR`, `JSON` **yo'q** | ⛔ [O'LCHANDI: M-5] `CV`→`CВ` **aralash alifbo** beradi va uni «lotin qoldi» detektori **ushlamaydi** — ya'ni bu defekt sinfi boshqa hech qanday darvozadan o'tmaydi |
| **G-12** | ⛔⛔ **Ko'r payload — modul chegarasi** | `scripts/blind-payload.test.mjs` (yangi, W0-F4) | `lib/blind-audit-queries.ts` va `components/blind-audit/**` da §14.3 dagi **taqiqlangan nomlar reyestri** umuman uchramaydi. **Qamrov chegarasi:** katalog mavjud bo'lsa ≥3 fayl | **D-17, 2-himoyaning mexanik shakli.** Bu darvoza `components/blind-audit/` **alohida katalog** bo'lgani uchungina yozilishi mumkin (§5.3) — aralash katalogda u kontekstga bog'liq, ya'ni `grep` bilan tekshirib bo'lmaydigan shartga aylanardi |
| **G-13** | ⛔ **Ko'r payload — sxema qattiqligi** | `blind-session.test.tsx` (vitest) | `blindAuditItemSchema.parse({...toza, verdict: "occupied"})` **throw qiladi**; sxema `z.strictObject` bilan qurilgan | **Ikkinchi qatlam.** G-12 kodni tekshiradi, bu esa **xulqni**: server bir kun maydon qo'shsa, klient **darhol qizaradi** va u jimgina ekranga oqib o'tmaydi |
| **G-14** | ⛔ **Ko'r javobning o'zgarmasligi** | `scripts/blind-payload.test.mjs` + `blind-session.test.tsx` | (a) `app/[locale]/(app)/review/blind/` da dinamik segment (`[`) **yo'q** — URL'da identifikator bo'lolmaydi; (b) `blind-audit-queries.ts` da `invalidateQueries` **yo'q**, `removeQueries` **bor**; (c) `shownAiVerdict`/`shown_ai_verdict` mutatsiya tanasida **yo'q**; (d) javobdan keyin uchala tugma `aria-disabled` | **D-17 ning 3 va 4-himoyasi.** Uchalasi ham «keyin tahrirlash» yo'lini yopadi, va uchalasi ham **kod-ko'rikda eng oson qaytib keladigan** sinf |
| **G-15** | ⛔ **`no_coverage` ≠ «bo'sh»** | `scripts/zone-copy.test.mjs` | `occupancy.noCoverage*` va `cameraZones.uncovered*` kalitlarining qiymatlarida `bo'sh` / `бо'ш` / `свободн` **yo'q** | **D-22 ning copy shakli.** Farq DB'da bor, lekin u **matn darajasida** yo'qolsa, hisobot jimgina noto'g'ri o'qilardi — va bu xatoni hech qanday sxema ushlamaydi |
| **G-16** | **Jargon taqig'i** | `scripts/zone-copy.test.mjs` | `cameraZones.*` / `review.*` / `occupancy.*` da `poligon`, `полигон`, `dataset`, `датасет`, `konfidens`, `конфиденс` **yo'q**; va tizim javobiga nisbatan `tuzatish` / `исправить` **yo'q** | §12.10. 4-fazadagi «slot» taqig'i bilan bir sinf: so'z taqig'i — kod-ko'rikda **eng oson o'tkazib yuboriladigan** narsa |
| **G-17** | **Sabab↔tuzatish parity** | `scripts/error-codes.test.mjs` (kengaytiriladi, W0-F7) | Har `cameraZones.errorCause.{code}` uchun `cameraZones.errorFix.{code}` **uchala tilda** mavjud; `ZONE_ERROR_CODES` va `REVIEW_ERROR_CODES` reyestrlari `lib/zone-errors.ts` bilan mos | 3-fazadagi G-1 ning davomi |
| **G-18** | ⛔ **Ommaviy tasdiq va qayta tortish taqig'i** | `scripts/zone-copy.test.mjs` + `review-session.test.tsx` | (a) `messages/*.json` da «hammasini tasdiqlash» / «подтвердить все» / «намунани қайта» va shu ma'nodagi shakllar **yo'q**; (b) `components/review/**` va `components/blind-audit/**` da `type="checkbox"` va `Array.isArray` bilan yuboriladigan mutatsiya **yo'q** | **D-18 va D-17, 1-himoya.** So'z copy'ga kirsa, keyingi ijrochi uni **amalga oshirishga** urinardi — 2 va 3-fazada aynan shunday bo'lgan |
| **G-19** | **Geometriya invariantlari** | `scripts/zone-geometry.test.mjs` (yangi, W0-F2) | `isSelfIntersecting` «soat mili» va «qum soati» to'rtburchakni **ajratadi**; `moveVertex` 0..1 dan tashqariga **chiqmaydi**; `deleteVertex` 3 tepada **o'zgarishsiz** qaytaradi; `interpolateRow` tepa soni teng bo'lmaganda **`[]`** qaytaradi; `normalize`/`denormalize` — aylanma (round-trip) mos | ⛔ **D-05 ning butun mazmuni.** Bu funksiyalar noto'g'ri bo'lsa, xato **poligon geometriyasiga** yoziladi va u yerdan **billing'ga** o'tadi — jimgina, dalilsiz |

> **G-12 va G-13 nima uchun IKKALASI ham kerak.** G-12 — **statik** (kod nima yozilgan), G-13 — **dinamik** (kod nima qiladi). Faqat G-12 bo'lsa, `data["verd" + "ict"]` uni chetlab o'tardi. Faqat G-13 bo'lsa, u faqat **test yozilgan** payloadni tekshirardi. Ikkalasi birga — statik chegara + xulq chegarasi.
>
> ⚠ **G-14 (a) sharti — `[` belgisining yo'qligi — qo'pol, lekin ATAYIN qo'pol.** U «dinamik marshrut segmenti bo'lmasin» degan niyatni **fayl tizimi darajasida** ifodalaydi va uni chetlab o'tish uchun ataylab harakat kerak bo'ladi. Nozikroq tekshiruv (URL parametrlarini tahlil qilish) yozilishi mumkin edi, lekin u o'zi buzilishi mumkin bo'lgan kodga aylanardi.

---

## 16. Bu fazada BO'LMAYDIGAN UI

[MEROS: 05-CONTEXT `<domain>` + `<deferred>` + 05-RESEARCH Scope Fence]

### 16.1 Keyingi fazalarga qoldiriladigan

| Imkoniyat | Faza | 5-fazada aynan nima qilinadi | Nima QILINMAYDI |
|-----------|------|-------------------------------|------------------|
| **Patta hisobi, tarif, summa** | 6 | Hech narsa. ⛔ Y-4 ochiq aytadi: «Patta hisobi alohida qoidaga ko'ra yuritiladi» (`occupancy.notBillingYet`) | Kunlik summa, qarz, tarif ko'rsatkichi |
| **Slotlararo agregatsiya («kamida 2 slot»)** | 6 | ⛔ **Faqat 1-daraja** — kameralararo (D-20). Y-4 «kun davomida kamida bir marta band» deydi | «Pattaga tushadi» degan har qanday ko'rsatkich |
| **Kassir oqimi** | 6 | Hech narsa | To'lov, smena, chek |
| **«Band, lekin to'lovsiz» case oqimi** | 7 | Hech narsa | Nomuvofiqlik ro'yxati, case holati, qaror |
| **Model o'qitish, fine-tuning** | `V2-AI-04` | ⛔ Ma'lumot **yig'iladi**, o'qitish **yo'q** (D-25) | «O'qitishni boshlash» tugmasi, dataset eksporti, model tanlash |
| **`no_coverage` uchun qo'lda bandlik kiritish** | `V2-AI-02` | Faqat **ko'rsatiladi** (§11.4) | Qo'lda «band» deb belgilash |
| **`.xlsx` eksporti, diagramma, trend** | 8 | Sonlar matn sifatida | Yuklab olish tugmasi, `recharts`, haftalik/oylik grafik |
| **Aniqlikning kesimlari** (kamera, vaqt, yorug'lik bo'yicha) | 8 | Bitta umumiy matritsa | Kesim tanlagichi, filtrlar |

### 16.2 Ataylab qurilMAYDIGAN — sabab bilan

| Nima | Nima uchun qurilmaydi |
|------|------------------------|
| ⛔ **«Namunani qayta tortish» tugmasi** | **D-17, 1-himoya.** Urug' hosila — u tanlanmaydi. Tugma bo'lsa, «bu turda xato ko'p chiqdi, qaytadan tortaman» degan yo'l ochilardi va u **aniqlikni yuqoriga siljitardi** (05-RESEARCH §C.8.1) |
| ⛔ **«Hammasini tasdiqlash» va har qanday ommaviy amal** | **D-18.** Va undan ham muhimi — ⛔ **har qatorda tugmali NAVBAT RO'YXATI ham qurilmaydi** (§7.3): u qadamlari ko'proq bo'lgan o'sha tugma |
| ⛔ **Ko'r auditda «Orqaga» / «Javobni o'zgartirish»** | **D-17, 4-himoya.** Va u faqat tugma emas — URL'da identifikator ham **yo'q** (§4.5), ya'ni yo'lning o'zi mavjud emas |
| ⛔ **Ko'r audit tarixi («men nima javob berdim?»)** | O'sha. Tarix bo'lsa, nazoratchi o'z javoblarini **eslab qolardi** va takroriy band (D-16) o'z-o'zini o'lchashdan to'xtardi |
| ⛔ **Byudjetdan keyin «yana ko'rish»** | Byudjet — **diqqat chegarasi**, kvota emas. Uni ochish charchagan holda berilgan javoblarni ma'lumotga aylantirardi |
| ⛔ **Navbatda confidence yoki tizim javobini oldindan ko'rsatish** | §7.1 — ankorlash. Bu AI-03 talab qilganidan qattiqroq va sabab yozilgan |
| ⛔ **Nazoratchiga uning o'z aniqligini ko'rsatish** | §11.6 `report_view` ostida. Ko'rsatilsa, u **raqamni yaxshilashga** urinardi — ya'ni o'lchov o'zi o'lchayotgan narsani o'zgartirardi |
| ⛔ **Zonaning eski versiyasini «tiklash»** | §6.6. Tiklash **yangi versiya** yaratardi va tarix ikki ma'noli bo'lardi. Kerak bo'lsa — qaytadan chiziladi |
| ⛔ **Kadrni `canvas` ga chizib yuklab olish** | §14.2. SVG'da bunday yo'l yo'q — D-05 ning qo'shimcha foydasi |
| **Kadrdan rastalarni avtomatik ajratish** | §6.7 — real bozor kadrida ishlamaydi |
| ⛔ **Detektor qutilarini zona qilish** | §6.7 — **aylanma mantiq**: detektor xatosi geometriyaga aylanadi, keyin o'sha geometriya bilan o'sha detektor baholanadi va aniqlik **soxta ko'tariladi** |
| **Zonalarni bir kameradan boshqasiga ko'chirish** | Perspektiva boshqa — ko'chirilgan poligon **noto'g'ri joyni** ko'rsatardi va buni sezish qiyin |
| **Zonalar eksporti / importi (fayl)** | Bir martalik ish uchun ikkinchi format va uning validatsiyasi. Kerak bo'lsa 8-fazada |
| **`uncertain` chegaralarini UI'dan sozlash** | D-11 — ular `thresholds_version` bilan **qatorda** yashaydi va SQL bilan sozlanadi. Admin uchun ma'nosi yo'q sonlarni ekranga chiqarish — yolg'on nazorat tuyg'usi |
| **Model versiyasini tanlash / almashtirish** | D-24: ONNX build paytida `COPY` bilan kiradi. UI'da tanlov bo'lsa, u yo'q imkoniyatni va'da qilardi |
| **Kameralar bo'yicha aniqlik reytingi** | 8-faza kesimi. Hozir `n` kichik va kamera bo'yicha bo'lingan namuna **hech nimani ko'rsatmasdi** |
| **Zona ustida jonli oqim (live view)** | 3-fazaning yuzasi. Jonli oqimda chizish — kadr har soniya o'zgaradi, ya'ni `source_width/height` langari **yo'qoladi** |
| **Bir vaqtda bir necha zonani tanlash va ko'chirish** | Foydasi kam (qator yordamchisi bu ehtiyojni yopadi), narxi — ikkinchi tanlov modeli va ikkinchi klaviatura naqshi |

### 16.3 Erta optimizatsiya deb baholangan «ilgaklar»

Ro'yxat virtualizatsiyasi (1000 `<li>` — DOM uchun arzon, o'lchangan); umumiy `<PolygonEditor>` abstraktsiyasi (bitta iste'molchi); zonalarning offline keshi; dark mode tokenlari; Storybook; dalil kadrlarini oldindan yuklash (⛔ ko'r auditda **taqiqlangan**, §7.7); zona ustida hover-preview; undo stekini `localStorage` ga saqlash.

### 16.4 Ochiq qoldirilgan savollar — har biri uchun ishlaydigan standart bor

Bu subagent kontekstida foydalanuvchiga savol berish vositasi yo'q. Quyidagilar **taxmin qilinib jimgina qulflanmadi**; har biri uchun standart tanlangan, ya'ni rejalashtirish javob kutib **to'xtamaydi**.

| # | Savol | Bilamiz | Noaniq | Tanlangan standart |
|---|-------|---------|--------|--------------------|
| **O-01** | «Ko'rmasdan tekshirish» atamasi to'g'rimi? | «Ko'r audit» — kalka; tanlangan shakl o'z-o'zini tushuntiradi (§12.1) | Ona tilida so'zlashuvchi ko'rigi bo'lmadi | **Shu shakl.** Kod `blind_audit` da qoladi. 8-fazadagi «uch tilli interfeys yakuniy tekshiruvi» mezoniga kiritilsin (4-fazadagi O-03 va O-05 bilan bir yo'lda) |
| **O-02** | `MAX_ZONES_PER_CAMERA = 60` Karmana uchun yetarlimi? | Kutilgan 10–40 (05-RESEARCH §A.4); 60 — zaxira va u D-05 ning 50+ o'lchov tetigidan yuqori | Keng burchakli kamera 50+ rastani ko'rishi mumkin | **60.** Qiymat `Settings` da — o'zgartirish **bitta qator**. Chegaraga yetgan kamera **Konva savolini ham** ko'taradi (§6.1) |
| **O-03** | `platform_admin` bandlik hisobotini ko'rmasligi to'g'rimi? | Unda `report_view` yo'q [KOD: `rbac.ts:68-81`]; RBAC bu fazada tegilmaydi (M-8) | Platforma admini pilotni tekshirishi kerak bo'lishi mumkin | **RBAC o'zgarmaydi.** Rollar **to'plam** (1-faza D-05) — tekshirish uchun `market_admin` roli beriladi. Agar bu real to'siq bo'lib chiqsa, `report_view` ni `platform_admin` ga qo'shish **bitta qator** va `rbac.py` bilan **birga** qilinadi |
| **O-04** | SVG 60 poligonda yetarlicha tezmi? | 2-faza 1000 elementni ~4 ms da o'lchagan [O'LCHANDI: M-12]; bu yerda 60 obyekt | ⚠ **Sudrash paytidagi `pointermove` narxi o'lchanmagan** — u boshqa profil (har kadrda qayta render) | **SVG.** Chiqish yo'li ochiq va tetigi **o'lchangan**: >16 ms bo'lsa `zone-canvas.tsx` Konva'ga almashtiriladi (§6.1). UAT bandi sifatida qayd etilsin |
| **O-05** | Ko'r audit uchun `n < 20` chegarasi to'g'rimi? | 05-RESEARCH §C.8.4: kichik `n` da Wilson ham keng oraliq beradi; 30/kun da 20 ga **bir kunda** yetiladi | Chegara 20 mi, 30 mi — statistik jihatdan ikkalasi ham himoyalanadi | **20.** Sabab: birinchi kunning oxirida direktor **nimadir** ko'rishi kerak, aks holda «tizim ishlamayapti» degan xulosa chiqarardi. Oraliq kengligi buni o'zi aytadi |
| **O-06** | Uchinchi javob («Aniq ayta olmayman») aniqlik hisobotida qanday sanaladi? | 05-RESEARCH javobsiz bandni «javobsiz» deb sanashni aytadi, lekin «aniq emas» ni ko'rmagan | U «xato» ham emas, «to'g'ri» ham emas | **Matritsadan TASHQARIDA**, alohida qator (§11.6). Sabab: uni matritsaga majburan joylash **ikkala yo'nalishda ham** aniqlikni buzardi. U kadr sifati haqidagi ma'lumot va u **shu sifatida** ko'rsatiladi |

---

## Checker Sign-Off

- [ ] Dimension 1 Copywriting: PASS
- [ ] Dimension 2 Visuals: PASS
- [ ] Dimension 3 Color: PASS
- [ ] Dimension 4 Typography: PASS
- [ ] Dimension 5 Spacing: PASS
- [ ] Dimension 6 Registry Safety: PASS

**Approval:** pending

---

*Phase: 05-kamera-zonalari-cv-va-nazoratchi-tasdig-i*
*UI-SPEC yakunlandi: 2026-08-08 — `gsd-ui-researcher`*
*Upstream: 05-CONTEXT.md (D-01…D-27), 05-RESEARCH.md (§A, §B, §C, §D, §E), 04-UI-SPEC.md (dizayn tizimi, i18n, a11y, darvoza mexanikasi), 02-UI-SPEC.md, ROADMAP Phase 5 (SC#1–SC#5), CLAUDE.md*
