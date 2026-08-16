---
phase: 04-snapshot-pipeline
status: complete
created: 2026-08-04
design_system: shadcn-pattern (manual, CVA + Radix — Phase 1/2 tokens)
response_language: uz-Latn
inherits: .planning/phases/03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi/03-UI-SPEC.md
---

# Phase 4 — Snapshot pipeline: UI dizayn kontrakti

> Bitta va'daning vizual kontrakti: **kadr o'z vaqtida olindimi, olinmadimi — va olinmagan bo'lsa, buni EKRANDA KO'RISH mumkinmi.**
> Bu fazaning UI'si ataylab kichik: D-01 admin jadval uchun **hech nima kiritmasligini** qulflaydi. Shuning uchun bu hujjat konfiguratsiya yuzasini emas, **yo'qlikni ko'rinadigan qilish** yuzasini loyihalaydi.
> Yaratdi: `gsd-ui-researcher`. Tekshiradi: `gsd-ui-checker`. Iste'mol qiladi: `gsd-planner`, `gsd-executor`.

---

## 0. Dalil holati va shu sessiyada bajarilgan o'lchovlar

Belgilar 3-fazadagi bilan bir xil [MEROS: 03-UI-SPEC §0]:

| Belgi | Ma'nosi |
|-------|---------|
| **[O'LCHANDI]** | Shu sessiyada kodbazada yoki skript bilan o'lchandi — natija keltirilgan |
| **[KOD]** | Kodbazadan o'qildi — aniq `fayl:qator` yoki buyruq keltirilgan |
| **[MEROS]** | Upstream artefaktdan (04-CONTEXT, 04-RESEARCH, 04-PATTERNS, 03-UI-SPEC, ROADMAP, CLAUDE.md) |
| **[QAROR]** | Shu hujjatda qabul qilindi — sabab yozilgan, muqobil rad etilgan |
| **[TALAB]** | UI backend'dan talab qiladigan narsa — rejaga bevosita kiradi |

### 0.1 O'lchovlar

| # | O'lchov | Natija |
|---|---------|--------|
| **M-1** | **Transliterator sinovi** — 85 ta 4-faza nomzod satri `frontend/scripts/gen-cyrillic.mjs` ning `transliterate()` funksiyasidan **mavjud** override lug'ati bilan o'tkazildi | **0 ta mexanik defekt** (lotin harfi yoki `ъ` qolmadi). Ya'ni 4-fazaning asosiy so'z boyligi 3-fazadagi apostrof-akronim tuzog'iga **tushmaydi** |
| **M-2** | **Akronim va brend sinovi** — `IR`, `JPEG`, `Sentry`, `Telegram`, `S3`, `SeaweedFS`, `MB`, `GB` alohida o'tkazildi | **To'rt yangi defekt** (§11.11): `IR`→`ИР`, `JPEG`→`ЖПЕГ`, `Sentry`→`Сентрй`, `Telegram`→`Телеграм`. `MB`→`МБ` va `GB`→`ГБ` — **to'g'ri**, override QO'YILMAYDI |
| **M-3** | **⛔ YANGI DEFEKT SINFI — alfanumerik token** — `S3` override lug'atiga **qo'shilgan holda** qayta o'tkazildi | `"S3 omborida"` → `"С3 омборида"` — **override TUZATMAYDI**. Tokenizator raqamli qo'shimchali so'zni boshqa token deb ko'radi. Bu 3-fazadagi apostrof defektining **jiyani** va yechimi ham o'sha: **copy qoidasi** (§11.11 Qoida 1) |
| **M-4** | **`ru` / `uz-Latn` uzunlik nisbati** — 21 ta 4-faza yorlig'i | O'rtacha **0,99×** (3-fazada 1,14× edi — bu to'plamda rus tili qisqaroq). Lekin eng yomoni `Buzuq` (5) → `Повреждён` (9) = **1,80×** → **matn 44px hujayraga sig'maydi** → §6.4 dagi «hujayrada matn YO'Q» qarorining o'lchangan asosi |
| **M-5** | **Wave 0 primitivlari** — `ls frontend/src/components/ui/` | **10 ta primitiv mavjud** (`badge, button, card, confirm-dialog, dialog, empty-state, field, input, select, skeleton`). 4-fazada **yangi `ui/` primitivi qurilmaydi** |
| **M-6** | **shadcn darvozasi** — `find . -maxdepth 3 -name components.json` | **0 natija** → `Tool: none` (§3.3), 2 va 3-faza qarori davom etadi |
| **M-7** | **Navigatsiya sig'imi** — `NAV_ITEMS` sanog'i [KOD: `app-shell.tsx:88-190`] | Hozir **10 element**; +1 = **11**. Rol bo'yicha: `platform_admin` 11, `market_admin` 10, `director` 6, kassir 1, nazoratchi 1. `MOBILE_PRIMARY_COUNT = 4` [KOD: `app-shell.tsx:193`] → mobil panel har rolda **4 + «Ko'proq» = 5**. **≤5 kontrakti saqlanadi** |
| **M-8** | **Ikonka mavjudligi** — `node -e "require('lucide-react')"` bilan 32 ta nom tekshirildi | `CheckCircle2, MoonStar, ImageOff, FileWarning, XCircle, CircleSlash, Clock, Loader2, Minus, CalendarClock, CalendarDays, Bell, BellOff, ChevronLeft, ChevronRight, Plus, Trash2, Pencil, TriangleAlert, Camera, ListFilter, Info` — **hammasi mavjud**, `lucide-react@1.27.0` |
| **M-9** | **Yakuniy copy validatsiyasi** — §11 ning **70 ta shipping uz-Latn satri** (barcha `verdict.*`, `errorCause.*`, `errorFix.*`, `alertKey.*`, `cell.*`, bo'sh holatlar) to'liq override to'plami bilan transliteratordan o'tkazildi | **0 ta defekt.** Ikkita satr sodda detektorda «flagged» bo'ldi va **ikkalasi ham TO'G'RI**: `ma'lumot` → `маълумот`, `ta'sir` → `таъсир` — bu **tutuq belgisi**, defekt emas. Bu G-6 ning tekshiruv shakliga bevosita ta'sir qiladi (§11.11 Qoida 6). **G-6 alfanumerik sharti:** 70 satrda raqam aralashgan lotin tokeni **0 ta** |

### 0.2 M-2 va M-3 ning xom chiqishi (dalil)

```
(1) Mavjud lug'at bilan — TO'RT DEFEKT:
  "Tungi IR rejimi"           -> "Тунги ИР режими"            ❌ akronim buzildi
  "JPEG sifati"               -> "ЖПЕГ сифати"                ❌ akronim buzildi
  "Sentry xatosi"             -> "Сентрй хатоси"              ❌ brend buzildi ("рй" — mavjud bo'lmagan shakl)
  "Telegram xabari yuborildi" -> "Телеграм хабари юборилди"   ⚠ o'qiladi, lekin brend qoidasiga zid

(2) To'g'ri chiqqanlar — override QO'YILMAYDI:
  "Ombor: 84 MB"              -> "Омбор: 84 МБ"               ✅ МБ — kirill birligining to'g'ri shakli
  "1,2 GB"                    -> "1,2 ГБ"                     ✅
  "06:00 dan 08:00 gacha"     -> "06:00 дан 08:00 гача"       ✅ raqamli vaqt buzilmaydi

(3) ⛔ OVERRIDE QO'SHILGANDAN KEYIN HAM TUZALMAYDI:
  words["S3"] = "S3"  ->  "S3 omborida" -> "С3 омборида"      ❌ HAMON BUZUQ
  words["SeaweedFS"] = "SeaweedFS" -> "SeaweedFS омборида"    ✅ sof harfli token TUZALADI
```

**Xulosa:** raqam bilan aralashgan token (`S3`, `H.264`, `IPv4`) override bilan **qutqarilmaydi** — u faqat **copy qoidasi** bilan yopiladi. `SeaweedFS` esa sof harfli va u tuzaladi. Ikkalasi ham §11.11 ga majburiy qoida bo'lib kiradi.

---

## 1. Ko'lam va ko'lamdan tashqari

### 1.1 Bu fazaning UI'si ATAYIN kichik — va bu qaror, kamchilik emas

D-01 [MEROS: 04-CONTEXT]: *«Admin snapshot jadvali uchun **hech nima kiritmaydi**. Usta bozor yaratilganda 7 slotli standart profil yozadi.»*

Ya'ni: 4-faza foydalanuvchidan **kirish ma'lumoti so'ramaydi**. Uning UI'si — kirish emas, **chiqish** yuzasi. Katta konfiguratsiya ekrani qurish D-01 ni ham, self-service qoidasini ham buzardi: admin ekranga qarab «nimadir kiritishim kerakmi?» degan savolga tushardi va javob **yo'q**.

Shuning uchun bu fazada aynan **to'rtta yuza** quriladi va beshinchisi yo'q.

| # | Yuza | Nimaga javob beradi | Ustuvorlik |
|---|------|---------------------|------------|
| **Y-1** | **Jadval ko'rinishi** | «Kadr qachon olinadi? Men o'zgartirsam qachon kuchga kiradi?» (D-05) | O'rta |
| **Y-2** | **Ijro jurnali** | «Bugun kadrlar olindimi? Qaysi biri olinmadi?» (SC#2) | ⛔ **ENG YUQORI** |
| **Y-3** | **Kadr sifati** | «Kamera buzuqmi yoki shunchaki tun edimi?» (SC#3, D-12) | Yuqori |
| **Y-4** | **Ogohlantirish holati** | «Nima ishlamadi va qachon xabar berildi?» (D-19, D-20) | Yuqori |

### 1.2 Y-2 nima uchun eng yuqori: SC#2 «ochiq ko'rinadi» deydi

ROADMAP Phase 4 SC#2: *«Kadr olish uzilsa yoki takror ishga tushsa — dublikat yozuv yaratilmaydi, urinish qayta bajariladi, **o'tkazib yuborilgan slot jurnalda ochiq ko'rinadi**.»*

«Jurnalga yozilgan» va «jurnalda ochiq ko'rinadi» — **boshqa talab**. Birinchisi backend ishi (D-20 ni `capture_runs` materializatsiyasi bajaradi). Ikkinchisi **UI ishi** va uni buzishning aniq bir usuli bor:

> **Bo'sh katak = «bu yerda ko'radigan narsa yo'q» degan xabar beradi.**
> Yo'q kadr — bo'shliq emas, **hodisa**. U bajarilgan kadr bilan **bir xil joyni egallaydi**, o'z ikonkasi, o'z so'zi va o'z izohiga ega bo'ladi.

Bu 3-fazadagi «uch hisoblagich» muammosining aynan takrori [MEROS: 03-UI-SPEC §6.3]: *«Hech narsa o'zgarmagan skan buzuq skandan farqlanmasa, idempotentlik isbotlanmagan hisoblanadi.»* U yerda yechim nol hisoblagichni **majburiy ko'rsatish** edi; bu yerda yechim yo'q kadrni **majburiy chizish**.

### 1.3 Bu fazaning UI'si NIMA QILMAYDI (qisqa ro'yxat — to'lig'i §16)

- Kamera zonasi, poligon, band/bo'sh qarori — **5-faza**
- Kadrdan pul hisoblash, dalil-hisob bog'lanishi — **6-faza**
- Ogohlantirish sozlamalari ekrani, Telegram chat tanlash — ops fayli, ekran emas
- Ombor brauzeri, S3 kalitini ko'rsatish — hech qachon (§14.3)
- Har kamera uchun alohida jadval — CAM-04 buni so'ramaydi (§16)

### 1.4 Talab qamrovi

| REQ | Bu fazada UI'da qanday ko'rinadi |
|-----|----------------------------------|
| **CAM-04** | Y-1 — jadval kartasi + mavsumiy profil dialogi + qoplanmagan kun ogohlantirishi |
| **CAM-05** | Y-2 — ijro jurnali; `missed` **birinchi darajali holat** (§6.4 C6) |
| **CAM-06** | Y-3 — sifat verdikti + `light_mode`, «hisobga kirmaydi» belgisi (§6.4 C2–C4) |
| **CAM-07** | Y-3 — kadr detali dialogida ombor qatlami (`to'liq` / `siqilgan`); ombor **brauzeri yo'q** |
| **FOUND-06** | Y-4 — ochiq ogohlantirishlar zonasi + oxirgi xabar vaqti; **rasm hech qachon yo'q** (D-19) |

---

## 2. Yuqori oqim qarorlaridan meros

23 ta qulflangan qarordan **o'ntasi** UI shaklini bevosita belgilaydi. Qolganlari backend ichida qoladi va bu yerda takrorlanmaydi.

| Qaror | Manba | UI'dagi bevosita oqibati |
|-------|-------|--------------------------|
| **D-01** — admin hech nima kiritmaydi; usta 7 slotli standart profil yozadi | 04-CONTEXT | Sahifada **bo'sh jadval holati YO'Q**. `EmptyState` «jadval qo'shing» **hech qachon chiqmaydi** — jadval har doim mavjud. Bu §10.4 ning E-1 bandiga aylanadi |
| **D-05** — kun o'rtasidagi tahrir **bugunga ta'sir qilmaydi** | 04-CONTEXT, SC#1 | ⛔ Jadval kartasi **ikki qatorni doim ko'rsatadi**: «Bugun … · Ertaga …». Tahrir dialogida bu qoida **doimiy izoh** sifatida turadi (§4.4). Buni yashirish birinchi kunning support savolini tug'diradi |
| **D-10** — yopiq kunda ham kadr olinadi | 04-CONTEXT | Jadval kartasida bitta **o'qish uchun** qator + sabab. Tugma emas (§4.3) |
| **D-12** — `light_mode` enum **va** alohida `quality_verdict` | 04-CONTEXT | Sifat detali **ikki qiymatni bitta jumlaga qo'shadi** (§6.6). Ikki alohida badge **rad etildi**: `dark`+`ir_night` normal, `dark`+`day` esa nosozlik — ma'no juftlikda |
| **D-15** — o'lchovlar saqlanadi, faqat verdikt emas | 04-RESEARCH §C.7 | `quality_mean`/`stddev`/`saturation` — kadr detalining `<details>` bloki ichida, `font-mono` (§8.3) |
| **D-16** — billing kafolati **strukturaviy** | 04-CONTEXT | «Hisobga kirmaydi» — UI'da **fakt**, ogohlantirish emas. Matn «tekshiring» demaydi, «bu kadr hisob-kitobga kirmaydi» deydi (§10.3) |
| **D-18** — 90 kun to'liq + 365 kun siqilgan | 04-CONTEXT | Kadr detalida `storage_tier` bitta badge: `To'liq` / `Siqilgan`. Kun va sana hisobi **UI'da qayta hisoblanmaydi** |
| **D-19** — ⛔ **alertlarga kadr rasmi HECH QACHON biriktirilmaydi** | 04-CONTEXT | **G-3 darvozasi** (§15). Ogohlantirish zonasida `<img>`, rasm havolasi, thumbnail — **yo'q**. Ular tashrifchilarning shaxsiy ma'lumoti va Telegram data-rezidentlik chegarasidan **tashqarida** |
| **D-20** — alert **yo'qlikka** qo'yiladi | 04-CONTEXT, CLAUDE.md | Y-2 va Y-4 **bir sahifada** turadi: yo'qlik jurnaldagi katak, ogohlantirish esa uning yuqori zonadagi aksi. Ikkisi ajratilsa admin ikkitasini solishtira olmasdi |
| **D-22** — guruhlash va chegara majburiy; backup xatosi va uzluksiz kamera offline **bo'g'ilmaydi** | 04-CONTEXT | Ogohlantirish qatorida `occurrences` **doim ko'rinadi** («so'nggi soatda yana 47 marta») — aks holda guruhlash **ma'lumot yashirish** bo'lib ko'rinardi (§6.7) |

### 2.1 3-fazadan meros olinadigan UI qoidalari — qayta muhokama qilinmaydi

| Qoida | Manba | 4-fazada qayerda |
|-------|-------|------------------|
| Rang **hech qachon yagona signal emas** (WCAG 1.4.1) | 03-UI-SPEC §2.5 | §9.4 — har hujayra holati uchun ≥2 qo'shimcha kanal |
| `--color-warning` **hech qachon matn rangi emas** | 02-UI-SPEC §4.2 | §9.2 |
| `disabled` o'rniga **`aria-disabled`** | 02-UI-SPEC §6.6 | §12.3 |
| Xom `detail` / stack izi foydalanuvchiga **hech qachon** | 02-UI-SPEC T-02-99 | §10.5 |
| Soxta progress bar **qurilmaydi** | 02-UI-SPEC, 03-UI-SPEC §5.2 | §6.2 — `running` hujayrasi foiz ko'rsatmaydi |
| Poll terminal holatda **to'xtaydi**, cheksiz poll **hech qachon** | 03-UI-SPEC §5.3 | §6.8 |
| Kalit nomlash: `namespace.camelCaseKey`, uchinchi daraja **faqat enum xaritalari** | 02-UI-SPEC §1.1 | §11 |
| Kesh kaliti **tug'ilishidanoq** `market_id` bilan doiralangan | 04-PATTERNS §S-14 | §5.4 |

---

## 3. Dizayn tizimi holati

### 3.1 Meros — o'zgarmaydi va qayta qurilmaydi

| Nima | Fayl | 4-fazada |
|------|------|----------|
| Tailwind 4 CSS-first `@theme` bloki (20 rang tokeni) | `frontend/src/app/globals.css` | O'zgarmaydi |
| `Button` (4 variant, `lg` = 44px) | `ui/button.tsx` | Qayta ishlatiladi |
| `Card` / `CardHeader` / `CardContent` | `ui/card.tsx` | Jadval kartasi, xulosa, jurnal |
| `Input` (+`aria-invalid`), `Field` (`${id}-error` / `${id}-hint`) | `ui/input.tsx`, `ui/field.tsx` | Mavsumiy profil formasi |
| `Select` (native `<select>`) | `ui/select.tsx` | Qadam tanlagichi (§4.5) |
| `Badge` (`neutral/muted/accent/success/warning/danger`) [KOD: `badge.tsx:28-43`] | `ui/badge.tsx` | Legenda, sifat, ombor qatlami |
| `Skeleton` (`motion-reduce:animate-none`) | `ui/skeleton.tsx` | Jurnal yuklanishi |
| `EmptyState` | `ui/empty-state.tsx` | 4 ta bo'sh holat (§10.4) |
| `Dialog` (`sm/md/lg` + `sheetOnMobile`) | `ui/dialog.tsx` | Kadr detali, jadval tahriri |
| `ConfirmDialog` (1/2-daraja, fokus destruktiv tugmada **emas**) | `ui/confirm-dialog.tsx` | Kelajakdagi profilni o'chirish |
| `sonner` Toaster (`top-center richColors`) | `app/[locale]/layout.tsx:82` | 4 ta toast (§10.6) |
| `nuqs` URL holati | `audit-filters.tsx`, `stall-filters.tsx` | `?day=`, `?issues=`, `?closed=` |
| RBAC UI ko'zgusi (huquq yo'q → **render qilinmaydi**) | `lib/rbac.ts` | `camera_view` / `camera_manage` |
| next-intl 3 til + `i18n:check` darvozasi | `messages/*`, `scripts/*.mjs` | §11 |
| Domen xato kodi → tarjima kaliti moduli | `lib/nvr-errors.ts` naqshi | `lib/capture-errors.ts` (§5.3) |

### 3.2 YETISHMAYDIGAN primitiv — YO'Q [O'LCHANDI: M-5]

**Bu fazada yangi `ui/` primitivi qurilmaydi.** To'rtala yuza mavjud 10 ta primitiv ustida yig'iladi.

Yagona chegaraviy holat — `components/snapshots/capture-grid.tsx` (§6.4). U `ui/` ga **ko'tarilmaydi**: uning semantikasi (kamera × vaqt matritsasi, roving tabindex, 9 ta hujayra holati) 4-faza domeniga xos. `ui/` ga chiqarish uni ma'nosiz umumiylashtirardi — bu 3-fazadagi `nvr-error-block.tsx` qarorining aynan takrori [MEROS: 03-UI-SPEC §1.2].

### 3.3 shadcn darvozasi — natija [O'LCHANDI: M-6]

**`components.json` topilmadi** → **`Tool: none`. `shadcn init` BAJARILMAYDI.** [QAROR — 2 va 3-faza qarorini davom ettiradi]

Sabablar o'zgarmagan: (1) `shadcn init` `package.json` ga yangi paket keltiradi; (2) Tailwind 4 rejimida u `globals.css` ga **o'z token nomlarini** yozadi va 1–2-fazada o'rnatilgan `--color-bg` / `--color-surface` / `--color-accent` to'plamining yonida **ikkinchi dizayn tizimi** paydo bo'lardi; (3) bu subagent kontekstida interaktiv savol vositasi yo'q — darvoza hujjatlashtirilgan qaror bilan yopiladi.

**Oqibat:** `Registry Safety` darvozasi shadcn uchun **qo'llanmaydi** (§14.1).

### 3.4 Yangi bog'liqlik so'rovi

**Yangi npm paketi: YO'Q. Yangi vendored artefakt: YO'Q.** [QAROR]

| Ehtiyoj | Mavjud yechim | Nega yangi paket kerak emas |
|---------|---------------|------------------------------|
| Vaqt kiritish (slot) | Native `<input type="time">` | `zod` bilan `HH:mm` validatsiyasi; uchala tilda tarjimasiz. Datepicker kutubxonasi **rad etildi** — u 40+ KB va lokalizatsiyani qaytadan hal qilishni talab qilardi |
| Sana kiritish (profil davri, kun tanlash) | Native `<input type="date">` | O'sha sabab. Mobil brauzerlarda native tanlagich **yaxshiroq** |
| Kun bo'yicha navigatsiya | `nuqs@2.9.2` `?day=` | Mavjud naqsh |
| Jurnal poll'i | `@tanstack/react-query@5.101.4` `refetchInterval` | 3-fazada o'rnatilgan naqsh (§6.8) |
| Sana matematikasi va nisbiy vaqt | `date-fns@4.4.0` + `next-intl` | Mavjud |
| Ikonkalar | `lucide-react@1.27.0` [O'LCHANDI: M-8] | 22 ta ikonka mavjud |
| Toast | `sonner@2.0.7` | O'rnatilgan |
| Grafik / diagramma | **Qurilmaydi** | `recharts` `package.json` da **yo'q** va u bu fazaga **so'ralmaydi** — kunlik xulosa raqam va matn (§6.3) |

> Agar reja bajarilishida boshqa paket zarur bo'lib chiqsa, u **UI-SPEC ga qaytariladi** va shu bo'limga sabab + rad etilgan muqobil bilan yoziladi — jimgina `npm install` **qilinmaydi** [MEROS: 02-UI-SPEC §13].

---

## 4. Ekranlar reyestri

### 4.1 Marshrut — bitta sahifa, to'rtta vertikal zona [QAROR]

| Marshrut | Vazifa | Kirish huquqi (UI ko'zgusi) |
|----------|--------|------------------------------|
| `/[locale]/(app)/snapshots` | **Yagona 4-faza sahifasi.** To'rt zona: (A) jadval kartasi, (B) ogohlantirishlar, (C) kun xulosasi, (D) ijro jurnali | `camera_view` |
| `/[locale]/(app)/snapshots?day=YYYY-MM-DD` | O'sha sahifa, tanlangan biznes-kun | `camera_view` |
| `/[locale]/(app)/snapshots?day=…&issues=1` | O'sha sahifa, jurnal faqat muammoli qatorlarda | `camera_view` |

**Ikkinchi marshrut YO'Q. `/schedule`, `/snapshots/[id]`, `/alerts` — QURILMAYDI.**

> ⚠ **`04-PATTERNS.md` §1.7 dan ataylab chekinish.** U `app/[locale]/(app)/schedule/page.tsx` va `components/schedule/*` ni nomlagan. Bu hujjat marshrutni **`/snapshots`** deb belgilaydi va fayllarni `components/snapshots/` ostiga yig'adi. Sabab: jadval — bu fazaning **kichik** yuzasi (uch qator), ijro jurnali esa **asosiy** yuzasi; marshrutni «schedule» deb nomlash sahifaning nomini uning eng kichik qismidan olardi. Fayl xaritasi §5.2 da aniq berilgan, ya'ni planer uchun noaniqlik qolmaydi.

Sabablar [QAROR]:

1. **Reja va ijro yonma-yon turishi kerak.** «Bugun 7 marta rejalashtirilgan» qatori «6/7 olindi» xulosasining **ustida** turadi. Ikki marshrutga bo'lish bu solishtirishni navigatsiyaga aylantirardi.
2. **D-20 ni UI'da bajaradi.** Ogohlantirish — yo'qlikning aksi. Ogohlantirishni alohida ekranga chiqarish «nima ishlamadi?» va «qayerda ishlamadi?» savollarini ikki ekranga bo'lardi.
3. **Sahifa uzun emas.** (A) uch qator, (B) odatda **umuman render qilinmaydi** (ochiq ogohlantirish yo'q), (C) bir qator, (D) matritsa. Bitta ekran balandligiga yaqin.
4. **3-faza precedenti** [MEROS: 03-UI-SPEC §3.1]: `/cameras` ham uch zonali yagona sahifa va u ishladi.

### 4.2 Sahifaning vertikal tuzilishi

```
┌ Kadr olish                                                     (h1, 24/600)
│
├─ (A) Jadval kartasi ───────────────────────────────────────────────────┐
│    Standart · 2026-08-15 dan                                          │
│    Bugun   7 marta   06:00 · 06:30 · 07:00 · 07:30 · 08:00 · 16:00 …  │
│    Ertaga  5 marta   07:00 · 07:30 · 08:00 · 15:00 · 17:00            │
│    ⚠ Bugungi reja o'zgarmaydi — yangi vaqtlar ertadan kuchga kiradi.  │
│    Yopiq kunlarda ham kadr olinadi.                                    │
│                                   [Jadvalni tahrirlash]  [Mavsumiy …]  │
│    (bo'shliq bo'lsa) CoverageWarning                                   │
└────────────────────────────────────────────────────────────────────────┘
│
├─ (B) Ogohlantirishlar ── faqat ochiq ogohlantirish bo'lsa render qilinadi
│      ⛔ rasm YO'Q, rasm havolasi YO'Q (D-19, G-3)
│
├─ (C) Kun tanlagichi + kunlik xulosa
│      [◀] [Bugun] [2026-09-01 ▾] [▶]
│      Kadrlar 173/175 · Yaroqli 168 · Qorong'i 3 · Bo'sh 1 · Buzuq 1 · Olinmadi 2
│
└─ (D) Ijro jurnali — legenda + matritsa (kamera × vaqt) + filtr
```

**Zonalar hech qachon almashmaydi** [MEROS: 03-UI-SPEC §3.2]. Kun almashtirilganda (C) va (D) `aria-busy="true"` oladi, **mazmuni joyida qoladi** va yangilanadi. Jadval yiqilib qayta qurilsa admin «ma'lumotim yo'qoldimi?» deb qo'rqardi.

### 4.3 Zona A — jadval kartasi (Y-1)

| Element | Qoida |
|---------|-------|
| Profil nomi + boshlanish sanasi | Body 14/600 + `text-xs text-text-muted`. Nom — **DB kontenti, tarjima qilinmaydi** [MEROS: 1-faza D-16] |
| **«Bugun» qatori** | `{count} marta` + vaqtlar `font-mono text-xs`, `·` bilan ajratilgan, `flex-wrap` |
| **«Ertaga» qatori** | ⛔ **DOIM render qilinadi**, bugungi bilan bir xil bo'lsa ham. D-05 ning butun mazmuni shu ikki qatorning **mavjudligida** |
| **Farq izohi** | `tomorrow ≠ today` bo'lganda **majburiy** qo'shimcha qator: `TriangleAlert` + `bg-warning/20 text-text` + `snapshots.scheduleTakesEffectTomorrow`. `role="status"` |
| **Yopiq kun qatori** | `capture_on_closed_days === true` bo'lganda bitta qator: «Yopiq kunlarda ham kadr olinadi.» + `title` bilan sabab. **O'qish uchun — tugma emas** (§16) |
| **[Jadvalni tahrirlash]** | `variant="secondary"`, `camera_manage` yo'q bo'lsa **render qilinmaydi** |
| **[Mavsumiy jadval qo'shish]** | `variant="secondary"`, o'sha huquq darvozasi |
| **CoverageWarning** | Faqat `uncovered_days > 0` bo'lganda. `AlertTriangle` + sabab + tuzatish yo'li (§10.5) |
| Yuklanish | Bitta `Skeleton` blok |

> **[TALAB]** `GET /api/v1/snapshot-schedules/today` bitta so'rovda quyidagini qaytarishi shart:
> `{ profile: {id, name, starts_on, ends_on|null, mode: "past"|"active"|"future"}, today: {date, times[]}, tomorrow: {date, times[]}, differs: bool, capture_on_closed_days: bool, uncovered_days: int, uncovered_horizon_days: int }`.
> Ikki so'rovga bo'lish «bugun» va «ertaga» ni **turli lahzada** olib kelardi va yarim tun atrofida ikkalasi bir kunni ko'rsatib qolardi.

### 4.4 Dialoglar (marshrut emas, sahifa holati)

| # | Dialog | Ochiladi | O'lcham | Huquq |
|---|--------|----------|---------|-------|
| **DL-1** | **Jadvalni tahrirlash** — joriy profilning vaqtlari | Zona A tugmasidan | `size="md" sheetOnMobile` | `camera_manage` |
| **DL-2** | **Mavsumiy jadval qo'shish** — nom + davr + vaqtlar | Zona A tugmasidan | `size="md" sheetOnMobile` | `camera_manage` |
| **DL-3** | **Kadr detali** — rasm + sifat + o'lchovlar | Jurnal hujayrasidan | `size="lg" sheetOnMobile` | `camera_view` |
| **DL-4** | **Kelajakdagi profilni o'chirish** (tasdiq) | DL-2 ro'yxatidan | `ConfirmDialog` 1-daraja | `camera_manage` |

**Dialog holati URL'da EMAS** [MEROS: 02-UI-SPEC §7.1]. URL'da faqat `?day=`, `?issues=`, `?closed=`.

> **DL-3 nima uchun URL'da emas:** kadr — bozor tashrifchilarining shaxsiy ma'lumoti. Ulashiladigan havola uni sessiyadan tashqariga olib chiqish taassurotini berardi. Bu D-19 ning ruhi bilan bir xil chiziq.

### 4.5 DL-1 va DL-2 — jadval tahriri

**Uch rejim, uchtasining ham nima tahrirlanishi FARQLI** [QAROR]:

| Profil rejimi | Shart | Tahrirlanadi | Sabab |
|---------------|-------|--------------|-------|
| **`future`** | `starts_on > bugun` | Nom, boshlanish, tugash, vaqtlar. **O'chirish mumkin** (DL-4) | Hali birorta kadr olinmagan — xato tuzatiladi |
| **`active`** | `starts_on ≤ bugun < ends_on` | **Faqat vaqtlar** | D-05: o'zgarish ertadan. Davrni siljitish o'tmishdagi `capture_runs` ni tushuntirmay qo'yardi |
| **`past`** | `ends_on ≤ bugun` | **Hech nima** — o'qish uchun | U o'tmishdagi kadrlarni tushuntiradi. Tahrirlash tarixni yolg'onga aylantirardi |

**DL-1 ichidagi doimiy izoh (yopib bo'lmaydi):**

```
ℹ  Bugungi reja allaqachon tuzilgan. Yangi vaqtlar ERTADAN boshlab
   ishlaydi — bugungi kadrlar eski jadval bo'yicha olinadi.
```

`Info` ikonkasi + `bg-surface-muted`, `role="note"` emas — oddiy matn (`aria-describedby` orqali forma bilan bog'lanadi). ⛔ **`role="alert"` QO'YILMAYDI** — bu nosozlik emas, qoida.

> **Nega tasdiq dialogi emas:** saqlashdan keyingi `ConfirmDialog` («bilasizmi, ertadan…») foydalanuvchini **allaqachon qaror qabul qilgandan keyin** to'xtatardi. Doimiy izoh esa kutilmani **qaror paytida** shakllantiradi — arzonroq va mehribonroq.

### 4.6 Slot muharriri (DL-1/DL-2 ning yuragi)

```
Vaqtlar                                         7 / 12
┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐
│06:00×│ │06:30×│ │07:00×│ │07:30×│ │08:00×│  …
└──────┘ └──────┘ └──────┘ └──────┘ └──────┘

[ 09:15 ]  [Vaqt qo'shish]

▸ Oraliq bo'yicha to'ldirish
    Boshlanish [06:00]  Tugash [08:00]  Qadam [30 daqiqa ▾]   [To'ldirish]
```

| Qoida | Qiymat | Sabab |
|-------|--------|-------|
| Saqlanadigan shakl | **Tekis vaqtlar ro'yxati** | [MEROS: 04-RESEARCH §A.1] — oraliq **saqlanmaydi**, UI uni kengaytiradi. Ikki shakl ikki kod yo'lini tug'dirardi |
| Tartib | Har doim **o'sish** bo'yicha, avtomatik | Admin tartibni boshqarmaydi — u ma'no tashimaydi |
| Format | `HH:mm`, `font-mono` | Ustunlashish |
| Dublikat | Qo'shishda rad etiladi + `snapshots.slotDuplicate` | Jimgina yutish «qo'shdim, ko'rinmadi» tuyg'usini berardi |
| Minimum | **1 ta vaqt** | Nol vaqt = kadr olinmaydigan bozor. Uni jadval orqali qilish mumkin emas |
| **Maksimum** | **`MAX_TIMES_PER_DAY = 12`** | ⛔ **Majburiy chegara.** 12 × 25 kamera = 300 kadr/kun/bozor ≈ 18 MB/kun ≈ 6,5 GB/yil. Chegarasiz «06:00–20:00 har 5 daqiqada» = 169 vaqt = **4 225 kadr/kun** va Contabo diski bir necha oyda to'lardi |
| Chegara ko'rsatkichi | Sarlavha yonida `7 / 12`, `text-xs` | Foydalanuvchi chegaraga **yetgunicha** ko'radi |
| Chegaraga yetganda | «Vaqt qo'shish» `aria-disabled` + `snapshots.slotLimitReached` `role="status"` da | `disabled` **emas** [MEROS: 02-UI-SPEC §6.6] |
| Qadam (`step`) | `Select`: **15 / 30 / 60 daqiqa** | Erkin raqam maydoni 1 daqiqalik qadam bilan chegarani darhol yeb qo'yardi va xato holatini normal ish jarayoniga aylantirardi |
| «To'ldirish» natijasi | Mavjud vaqtlar bilan **birlashtiriladi** (dublikatlar tashlanadi), almashtirilmaydi | Almashtirish qo'lda kiritilgan 16:00 ni jimgina yo'qotardi |
| To'ldirish chegaradan oshsa | **Hech nima qo'shilmaydi** + xato matni. Qisman to'ldirish **yo'q** | Qisman natija «qaysilari qo'shildi?» savolini tug'dirardi |

> **[TALAB]** `MAX_TIMES_PER_DAY` **serverda ham** majburlanadi (`Settings`, standart 12). Klientdagi chegara — **qulaylik**, xavfsizlik chegarasi emas [MEROS: 02-UI-SPEC §12.3].

### 4.7 DL-2 — mavsumiy profil formasi

| # | Maydon | Tip | Qoida |
|---|--------|-----|-------|
| 1 | **Nom** | `text` | Majburiy, ≤ 40 belgi. Misol matni `hint` da: «Qishki», «Ramazon» |
| 2 | **Boshlanish sanasi** | `date` | Majburiy. **`min` = ertaga** — bugundan boshlanadigan profil D-05 ni buzardi |
| 3 | **Tugash sanasi** | `date` | **Ixtiyoriy.** Bo'sh = ochiq oxirli. To'ldirilsa `> boshlanish` |
| 4 | **Vaqtlar** | Slot muharriri (§4.6) | Standart holat: **joriy profilning vaqtlari nusxasi** — noldan boshlash emas |

**Jonli natija qatori (forma ostida, `role="status"`):**

```
2026-11-01 dan 2027-03-01 gacha — kuniga 5 marta.
Keyin «Standart» jadvali qaytadi.
```

Oxirgi jumla **faqat tugash sanasi berilganda** chiqadi va u **kutilmani belgilaydi** — mavsumiy profilni qo'shgan admin «keyin nima bo'ladi?» degan savolga javob olishi kerak.

> **[TALAB]** Backend `POST /snapshot-schedules` da davrni **bo'lish** (split) semantikasini bajaradi va tugash sanasidan keyin oldingi profilni **nusxa** sifatida tiklaydi [MEROS: 04-RESEARCH §A.1]. UI bu mantiqni **takrorlamaydi** — u faqat natija qatorini backend qaytargan `preview` dan chizadi yoki (preview bo'lmasa) kiritilgan qiymatlardan hosil qiladi.

### 4.8 Navigatsiya kengaytmasi — bitta yozuv [QAROR]

`NAV_ITEMS` ga **bitta** element qo'shiladi [KOD: `app-shell.tsx:88-190`]:

```ts
{
  href: "/snapshots",
  labelKey: "snapshots",
  icon: CalendarClock,
  permission: "camera_view",
  group: "market",
}
```

`NavItem["href"]` va `NavItem["labelKey"]` literal union'lariga `"/snapshots"` va `"snapshots"` qo'shiladi — aks holda kompilyatsiya yiqiladi (bu **maqsadli** darvoza) [KOD: `app-shell.tsx:53-77`].

**Joylashuv: `market` guruhida, `/cameras` dan bevosita KEYIN, `/users` dan OLDIN.**

| Savol | Javob |
|-------|-------|
| Nega `/cameras` dan keyin? | Kadr olish — kameraning bevosita davomi. `Permission` ham aynan bir xil (`camera_view`), ya'ni ikkalasi bir vaqtda paydo bo'ladi va bir vaqtda yo'qoladi |
| Mobil kontrakt buzilmaydimi? | **Yo'q** [O'LCHANDI: M-7]. `NAV_ITEMS` 10 → **11**; `MOBILE_PRIMARY_COUNT = 4`, ya'ni panel `4 + «Ko'proq» = ` **5**. Kontrakt (≤5) saqlanadi |
| Ikonka nega `CalendarClock`? | Reja (kalendar) + vaqt (soat) — fazaning ikkala mazmuni. `Camera` **ishlatilmaydi**: u `/cameras` da band va ikki bo'limni bir xil ko'rsatardi |
| Nega `snapshots` labelKey, `capture` emas? | Marshrut nomi bilan mos — `app-shell.tsx` ning literal union'lari ikkalasini juft yuritadi |

`nav.snapshots` kaliti uch tilda qo'shiladi (§11.1).

### 4.9 Ustaga ulanish — YO'Q [QAROR]

D-01 bo'yicha jadval **usta tomonidan avtomatik yoziladi**. Ya'ni:

- `WIZARD_STEPS` ga **hech narsa qo'shilmaydi**
- `wizard-stepper.tsx`, `activation-panel.tsx` — **tegilmaydi**
- Ustada «snapshot jadvali» qadami **ko'rinmaydi**

Sabab: usta qadami bo'lsa u avtomatik `completedStepCount` ga, `blockedBy` grafiga va «bajarilganmi?» savoliga tushardi — ya'ni admin **hech nima kiritmasa** bozor «chala» ko'rinardi. Bu D-01 ning aynan teskarisi. 3-fazada kamera uchun aynan shu qaror qabul qilingan [MEROS: 03-UI-SPEC §3.4].

---

## 5. Komponentlar reyestri

### 5.1 Wave 0 — yangi ekranlardan OLDIN (bloklovchi)

| # | Ish | Fayl | Nega bloklovchi |
|---|-----|------|-----------------|
| **W0-F1** | `NAV_ITEMS` + `href`/`labelKey` literal union'lari (§4.8) | `components/shell/app-shell.tsx` | Usiz sahifa navigatsiyadan **yetib bo'lmaydi** |
| **W0-F2** | `uz-Cyrl.overrides.json` — **2 ta yangi yozuv** + `gen-cyrillic.test.mjs` ning `allowed` regexi (§11.11 Qoida 2) | `messages/uz-Cyrl.overrides.json`, `scripts/gen-cyrillic.test.mjs` | Ikkisi **juft** yuritiladi [MEROS: 04-PATTERNS §S-14]. Biri to'ldirilib ikkinchisi unutilsa test qizaradi — bu **kutilgan** xulq. Usiz birinchi kirill build'i buzuq matn chiqaradi |
| **W0-F3** | `gen-cyrillic.test.mjs` — 4 ta yangi assertion (M-2/M-3 holatlari) | `scripts/` | Darvoza **G-6** |
| **W0-F4** | `snapshot-copy.test.mjs` — yangi fayl | `scripts/` | Darvozalar **G-1, G-2, G-3, G-4** |
| **W0-F5** | `error-codes.test.mjs` ni `capture_*` kodlari bilan kengaytirish | `scripts/` | Darvoza **G-5** — sabab↔tuzatish parity |
| **W0-F6** | ⚠ **RBAC — o'zgarish YO'Q, lekin TASDIQLANADI** | `lib/rbac.ts` | [MEROS: 04-PATTERNS §3.9] — 4-faza yangi `Permission` **qo'shmaydi**; `camera_view`/`camera_manage` qayta ishlatiladi. Bu bandning vazifasi — planer yangi huquq **o'ylab topmasligi**. Agar o'ylab topsa, `rbac.py` **birga** o'zgaradi va `scripts/role-gate.test.mjs` ni qondiradi |
| **W0-F7** | ⛔ **3-fazaning G-3 hedging darvozasini kengaytirish** — `HEDGED_KEYS` ikki kalitli to'plamga aylanadi | `scripts/nvr-copy.test.mjs` | [O'LCHANDI: §11.11 Qoida 4] 3-faza G-3 «boshqa hech bir `errorCause.*` da hedge so'zi yo'q» deydi; 4-faza `snapshots.errorCause.capture_stream_limit` ni **aynan o'sha so'z bilan** qo'shadi. Kengaytirilmasa darvoza **birinchi kunning o'zida qizaradi** va ijrochi uni «tuzatish» uchun copy'ni buzardi |

> **W0-F6 nega ro'yxatda bo'lsa ham «o'zgarish yo'q»:** 3-fazada `platform_admin` da `camera_view` **yo'q** edi va bu faqat o'lchov bilan topilgan [MEROS: 03-UI-SPEC M-8]. Bu safar matritsa **oldindan** tekshirildi va u yetarli — lekin bandni ro'yxatdan **olib tashlash** keyingi ijrochida «tekshirilganmi?» savolini qoldirardi.

### 5.2 Yangi komponentlar

| Yo'l | Vazifa | Client? | `04-PATTERNS.md` analogi |
|------|--------|---------|--------------------------|
| `app/[locale]/(app)/snapshots/page.tsx` | Sahifa qobig'i, to'rt zona, RBAC darvozasi, **`Suspense` majburiy** (URL parametri o'qiydi) | ✅ | §3.12 → `app/[locale]/(app)/cameras/page.tsx` + `audit/page.tsx` |
| `components/snapshots/schedule-card.tsx` | §4.3 — bugun/ertaga, farq izohi, yopiq kun qatori | ✅ | §1.7 `schedule/schedule-list.tsx` → `tariffs/tariff-list.tsx` |
| `components/snapshots/schedule-dialog.tsx` | §4.5 — DL-1/DL-2 qobig'i, uch rejim | ✅ | `cameras/camera-rename-dialog.tsx` |
| `components/snapshots/slot-editor.tsx` | §4.6 — chip ro'yxati + oraliq generatori | ✅ | §1.7 → `calendar/weekday-picker.tsx` |
| `components/snapshots/coverage-warning.tsx` | §10.5 — «N kun qoplanmagan» | — | §1.7 → `cameras/nvr-error-block.tsx` |
| `components/snapshots/day-picker.tsx` | §6.3 — `?day=` navigatsiyasi | ✅ | `stalls/stall-filters.tsx` (nuqs) |
| `components/snapshots/day-summary.tsx` | §6.3 — `<dl>` hisoblagichlari | — | `cameras/discovery-result.tsx` (**to'liq shablon**) |
| `components/snapshots/capture-grid.tsx` | §6.4 — matritsa, roving tabindex, 9 holat | ✅ | **analog yo'q** (§5.5) |
| `components/snapshots/capture-cell.tsx` | §6.4 — bitta hujayra | — | `cameras/camera-status-badge.tsx` (rang+ikonka+matn naqshi) |
| `components/snapshots/capture-legend.tsx` | §6.5 — 9 ta holat lug'ati | — | **analog yo'q** (§5.5) |
| `components/snapshots/snapshot-dialog.tsx` | §6.6 — DL-3, kadr + sifat + `<details>` | ✅ | `cameras/live-view-dialog.tsx` (holat mashinasi shakli) |
| `components/snapshots/alert-list.tsx` | §6.7 — ochiq ogohlantirishlar | ✅ | `users/user-list.tsx` (to'rtlik: pending/error/bo'sh/natija) |
| `components/snapshots/alert-row.tsx` | §6.7 — bitta ogohlantirish | — | `cameras/camera-row.tsx` |
| `lib/snapshot-queries.ts` | So'rovlar, mutatsiyalar, poll, `queryKey` fabrikalar | — | §3.12 → `lib/camera-queries.ts` (**to'liq shablon**) |
| `lib/capture-errors.ts` | `captureErrorView(code) → {causeKey, fixKey, tone, actor}` | — | `lib/nvr-errors.ts` |

### 5.3 `lib/capture-errors.ts` nega alohida modul

`nvrErrorView(code)` **beshta** qiymat qaytaradi (`causeKey`, `fixKey`, `tone`, `retrySafe`, `authLocking`). `captureErrorView(code)` esa **to'rtta** qaytaradi va beshinchisi o'rniga yangi o'lcham bor: **`actor`** — «kim tuzatadi?» (`admin` / `platform` / `hech kim`).

Sabab: kadr olish xatolarining bir qismi **bozor adminining ishi emas** (`capture_worker_lost`, `capture_storage_unavailable` — platforma ishi), bir qismi esa **hech kimning ishi emas** (`capture_plan_created_late` — normal holat). 3-fazada bunday bo'linish yo'q edi, chunki u yerda har xato adminga tegishli edi. Turli shakl — turli modul [MEROS: 03-UI-SPEC §13.4 mantiqi].

### 5.4 Kesh kalitlari — tug'ilishidanoq doiralangan

```ts
// frontend/src/lib/snapshot-queries.ts
import { domainKey } from "@/lib/market-queries";   // ikkinchi nusxa YARATILMAYDI

export const scheduleTodayKey = (marketId: string) => domainKey(marketId, "schedule", "today");
export const schedulesKey     = (marketId: string) => domainKey(marketId, "schedules");
export const captureDayKey    = (marketId: string, day: string) => domainKey(marketId, "capture-runs", day);
export const alertsKey        = (marketId: string, closed: boolean) => domainKey(marketId, "alerts", String(closed));
```

| Qoida | Sabab |
|-------|-------|
| **Har fabrikaning BIRINCHI argumenti `marketId`** | Doiralashni chetlab o'tish TypeScript xatosisiz **mumkin emas** [MEROS: 04-PATTERNS §S-14, `camera-queries.ts:32-40`] |
| **Global (marketsiz) kalit konstantasi bu modulda UMUMAN YO'Q** | 3-fazada global kalitlar **o'chirilgan** — CR-01 ning strukturaviy davosi |
| `enabled: marketId !== null` — **kontrakt, qulaylik emas** | Bozorsiz sessiyada `409 market_not_selected` kesh grafida yashab qolardi [KOD: `market-queries.ts:185-192`] |
| `query-provider.tsx` **o'zgartirilmaydi** | Sessiya identifikatori o'zgarganda `client.clear()` butun keshni bo'shatadi |

### 5.5 Analog yo'q — ikkita komponent, soxta analog berilmaydi

| Komponent | Nega analog yo'q | Nima qilinadi |
|-----------|------------------|---------------|
| `capture-grid.tsx` | Kodbazada **matritsa/jadval semantikasi yo'q**: `stalls` plan-xaritasi CSS Grid, lekin u **klaviatura matritsasi emas** (har rasta alohida tugma). Roving tabindex **hech qayerda ishlatilmagan** [MEROS: 03-UI-SPEC §6.1 — *«≤32 qator, roving tabindex kerak emas»*] | ARIA APG `grid` naqshi §12.4 da **to'liq** yoziladi — ijrochi uni o'ylab topmaydi |
| `capture-legend.tsx` | Kodbazada legenda yo'q, chunki bugungacha har holat **matn bilan birga** ko'rsatilgan. Bu yerda matn hujayraga sig'maydi [O'LCHANDI: M-4] | §6.5 da to'liq spetsifikatsiya |

### 5.6 Kengaytiriladigan mavjud fayllar

| Fayl | O'zgarish |
|------|-----------|
| `components/shell/app-shell.tsx` | W0-F1 |
| `lib/api-types.ts` | `snapshot*` zod sxemalari + `CAPTURE_ERROR_CODES` reyestri (`ERROR_CODES:1019-1092` naqshi) |
| `messages/uz-Latn.json`, `messages/ru.json` | ~110 kalit (§11) |
| `messages/uz-Cyrl.overrides.json` | 5 so'z (W0-F2) |
| `scripts/gen-cyrillic.test.mjs` | W0-F2 (`allowed`) + W0-F3 |
| `scripts/error-codes.test.mjs` | W0-F5 |
| `lib/rbac.ts` | **O'zgarish yo'q** — W0-F6 tasdig'i |

### 5.7 Komponent testlari

| Fayl | Nimani isbotlaydi |
|------|-------------------|
| `capture-cell.test.tsx` | ⛔ `missed` hujayrasi **bo'sh emas**: ikonka + `aria-label` + dashed chegara mavjud; `succeeded+dark` hujayrasi `succeeded+ok` dan **ikonkasi bilan** farq qiladi |
| `capture-grid.test.tsx` | Bitta tab to'xtashi (roving tabindex); `ArrowRight`/`ArrowDown` fokusni ko'chiradi; `Home`/`End` qatorning chetiga; `Enter` DL-3 ni ochadi |
| `day-summary.test.tsx` | ⛔ Oltala hisoblagich **doim** render bo'ladi, nol bo'lsa ham; `planned === 0` da «rejalashtirilmagan» matni chiqadi va **«0/0 olindi» chiqmaydi** |
| `schedule-card.test.tsx` | «Ertaga» qatori **doim** bor; `differs === true` da farq izohi chiqadi; `camera_manage` yo'q rolda tugmalar **render bo'lmaydi** |
| `slot-editor.test.tsx` | Chegaraga yetganda «qo'shish» `aria-disabled`; oraliq to'ldirish chegaradan oshsa **hech nima qo'shilmaydi**; dublikat rad etiladi |
| `alert-list.test.tsx` | ⛔ Ogohlantirish qatorida **`<img>` yo'q** va `href` da `/snapshots/` **yo'q** (D-19); `occurrences > 1` da takror soni ko'rinadi |
| `snapshot-dialog.test.tsx` | `dark`+`ir_night` va `dark`+`day` **turli matn** beradi (§6.6); noma'lum kodda `error_detail` **chiqmaydi** |

---

## 6. Holatlar kontrakti (idle / running / success / partial / ABSENT / error)

> Bu bo'lim — hujjatning yadrosi. SC#2 ning «ochiq ko'rinadi» talabi shu yerda mexanik shaklga aylanadi.

### 6.1 Ikki daraja: sahifa holati va hujayra holati

| Daraja | Nima | Qayerda |
|--------|------|---------|
| **Sahifa/zona holati** | Yuklanmoqda / bo'sh / xato / natija | §6.2, §10.4 |
| **Hujayra holati** | Bitta (kamera, vaqt) juftligining natijasi — **9 ta** | §6.4 |

Ikkisi **aralashtirilmaydi**: zona xatosi (tarmoq yiqildi) hujayra xatosidan (kadr olinmadi) butunlay boshqa narsa va ular bir xil ko'rinmaydi.

### 6.2 Zona holatlari

| # | Zona | Holat | Ko'rinish |
|---|------|-------|-----------|
| **Z-1** | A (jadval) | `isPending` | 1 ta `Skeleton` blok |
| **Z-2** | A | `isError` | Meros xato bloki: `role="alert"`, `errors.loadFailedTitle` + **[Qayta urinish]** |
| **Z-3** | B (ogohlantirish) | Ochiq ogohlantirish **yo'q** | ⛔ Zona **umuman render qilinmaydi**. Bo'sh «hammasi yaxshi» paneli — shovqin |
| **Z-4** | B | `closed=1` yoqilgan, lekin tarix bo'sh | `EmptyState` E-4 (§10.4) |
| **Z-5** | C+D | `isPending` (birinchi yuklash) | Xulosa: 1 `Skeleton` qator; jurnal: **3 ta `Skeleton` qator** real qator balandligida, konteyner `role="status" aria-busy="true"` + `sr-only` «Yuklanmoqda» |
| **Z-6** | C+D | Kun almashtirildi (qayta yuklash) | Mazmun **o'chmaydi**, `aria-busy="true"` oladi (§4.2) |
| **Z-7** | C+D | Kunda reja **umuman yo'q** | `EmptyState` E-2 — «Bu kunda kadr rejalashtirilmagan» ⛔ **«0/0 olindi» EMAS** |
| **Z-8** | C+D | Bugun, lekin birinchi vaqt hali kelmagan | Xulosa `0/7`, jurnal to'liq `pending` hujayralardan iborat. **Bu bo'sh holat EMAS** |
| **Z-9** | C+D | `isError` | Z-2 bilan bir xil blok |
| **Z-10** | D | Filtr (`issues=1`) hech narsa topmadi | `EmptyState` E-3 + **[Filtrni tozalash]** |

> **Z-7 va Z-8 ning farqi hayotiy.** Z-7 — jadval bu kunni qoplamaydi (bo'shliq yoki bozor hali faollashmagan). Z-8 — jadval bor, kun boshlanmagan. Ikkalasini bir xil ko'rsatish adminni «tizim ishlamayapti» degan xulosaga olib borardi.

### 6.3 Zona C — kun tanlagichi va xulosa

**Tanlagich:**

| Element | Qoida |
|---------|-------|
| `[◀]` `[▶]` | Bir kun orqaga/oldinga. `▶` bugunda `aria-disabled` + sabab (`snapshots.noFutureDays`) |
| `[Bugun]` | `variant="secondary"`; joriy kun bugun bo'lsa `aria-disabled` |
| `<input type="date">` | `max` = bugun. Kelajak kun **tanlanmaydi**: ertangi reja hali materializatsiya qilinmagan va bo'sh jurnal yolg'on signal berardi |
| URL | `?day=YYYY-MM-DD`, `nuqs`, `history: "push"` — orqaga tugmasi kun bo'yicha ishlaydi |
| Yaroqsiz `?day=` | Jimgina bugunga tushadi, **xato ko'rsatilmaydi** [MEROS: 03-UI-SPEC §5.4 naqshi] |
| Sana formati | `next-intl` locale bo'yicha; `font-mono` **emas** (u sana emas, matn) |

**Xulosa — `<dl>`, oltita hisoblagich [MEROS: 03-UI-SPEC §6.3]:**

```
┌ 2026-09-01 · payshanba ──────────────────────────────────────────────┐
│  Olindi 173 / 175                                                    │
│  ✓ 168 yaroqli · 🌑 3 qorong'i · ⬛ 1 bo'sh · ⚠ 1 buzuq              │
│  ✕ 0 xato · ⊘ 2 olinmadi                                             │
└──────────────────────────────────────────────────────────────────────┘
```

| Qoida | Nima uchun |
|-------|-----------|
| ⛔ **Oltala hisoblagich HAM DOIM ko'rinadi — nol bo'lsa ham** | 3-fazadagi uch hisoblagich qoidasining aynan takrori [MEROS: 03-UI-SPEC §6.3]: nol — **natija**, uning yo'qligi emas |
| Har hisoblagich `<dt>`/`<dd>` | Raqam va yorliq **dasturiy jihatdan** bog'lanadi — skrinriderda «0» yolg'iz eshitilmaydi |
| `role="status"`, `alert` **EMAS** | Kunlik xulosa — hisobot, ogohlantirish emas |
| **Barcha nol emas, lekin `missed > 0`** | Sarlavha ostida bitta qo'shimcha jumla: «{count} ta kadr umuman olinmadi.» + [Muammolilarni ko'rsatish] havolasi (`?issues=1`) |
| **`planned === 0`** | Z-7 ga o'tadi — hisoblagichlar **umuman render qilinmaydi** |
| Foizli ko'rsatkich (`98,9%`) | **QO'YILMAYDI.** `173/175` aniqroq va u yaxlitlanmaydi. Foiz kunlik dayjest (Telegram) uchun — u yerda joy tor |

### 6.4 ⛔ Zona D — to'qqizta hujayra holati va ABSENT ning birinchi darajaliligi

```
            06:00  06:30  07:00  07:30  08:00  16:00  18:00
01 Sabzavot   ✓      ✓      ✓      ✓      ✓      ✓      ✓
02 Go'sht     🌑     ✓      ✓      ✓      ✓      ✓      ✓
03 Kiyim      ✓      ⊘      ✓      ✓      ✓      ✕      ✓
                     └── dashed chegara: BU YERDA KADR YO'Q
```

| # | Hujayra holati | Manba (`capture_runs` × `snapshots`) | Ikonka | Tone | Chegara |
|---|----------------|--------------------------------------|--------|------|---------|
| **C1** | **Olindi** | `succeeded` + `quality_verdict='ok'` | `CheckCircle2` | `success` | solid |
| **C2** | **Qorong'i** | `succeeded` + `dark` | `MoonStar` | `warning` | solid |
| **C3** | **Bo'sh** | `succeeded` + `blank` | `ImageOff` | `warning` | solid |
| **C4** | **Buzuq** | `succeeded` + `corrupt` | `FileWarning` | `warning` | solid |
| **C5** | **Xato** | `failed` | `XCircle` | `danger` | solid |
| **C6** | ⛔ **Olinmadi** | `missed` | `CircleSlash` | `danger` | ⛔ **`border-dashed`** |
| **C7** | **Kutilmoqda** | `pending`, `scheduled_at > now` | `Clock` | `muted` | solid |
| **C8** | **Olinmoqda** | `running` | `Loader2` (aylanadi) | `neutral` | solid |
| **C9** | **Rejaga kirmagan** | `skipped` | `Minus` | `muted` | `border-dashed` |

#### C6 — ABSENT nima uchun birinchi darajali holat

| Qoida | Amalda | Nima uchun |
|-------|--------|------------|
| ⛔ **Hujayra HECH QACHON bo'sh render qilinmaydi** | `missed` hujayra `succeeded` hujayra bilan **bir xil o'lchamda** (44×44) va ikonka bilan to'ldiriladi | Bo'shliq «ko'radigan narsa yo'q» deydi. Bu SC#2 ni jimgina buzardi |
| **Uchinchi, rangsiz kanal — `border-dashed`** | Faqat C6 va C9 punktir chegara oladi | Rang (danger) + ikonka (`CircleSlash`) + **shakl** (punktir) = uchta mustaqil kanal. Punktir «bu yerda nimadir bo'lishi kerak edi» ning universal shakli |
| **Ikonkasi C5 (xato) dan farq qiladi** | `CircleSlash` ≠ `XCircle` | `missed` = **bizning tizimimiz ishlamadi**; `failed` = **NVR javob bermadi**. Ular operatsion jihatdan butunlay boshqa va bir xil ko'rinishi dala diagnostikasini o'ldirardi [MEROS: 04-RESEARCH §B.5] |
| **`aria-label` to'liq jumla** | `«06:30 · Kiyim qatori · Kadr olinmadi»` | Skrinrider foydalanuvchisi uchun ikonka yo'q — matn **yagona** kanal |
| **DL-3 ochilganda sabab majburiy** | «Tizim bu vaqtda ishlamadi, shuning uchun kadr umuman olinmagan.» + `error_code` (`capture_slot_missed`) tarjimasi | «Nega?» savoli javobsiz qolmaydi |
| **Xulosada alohida sanaladi** | `⊘ 2 olinmadi` — `✕ 0 xato` dan alohida qator | §6.3 |

#### Hujayrada matn YO'Q — o'lchangan qaror [O'LCHANDI: M-4]

Hujayra o'lchami 44×44px (barmoq nishoni, §7.2). Eng uzun holat yorlig'i rus tilida `Повреждён` = **9 belgi** (`Buzuq` dan **1,80×** uzun) — `text-xs` da ~58px, ya'ni **sig'maydi**.

Shuning uchun:

| Kanal | Qayerda |
|-------|---------|
| **Ikonka** (shakl) | Hujayrada |
| **Rang** (tone) | Hujayrada |
| **Chegara uslubi** (C6/C9) | Hujayrada |
| **So'z** | ⛔ **Legendada (§6.5) — doimiy va yopilmaydigan** + hujayraning `aria-label` va `title` atributlarida + DL-3 sarlavhasida |

Muqobillar rad etildi: *hujayrani kengaytirish* (7 ustun × 90px = 630px, mobilda gorizontal aylantirish zarurati ikki barobar oshardi); *matnni qisqartirish* (`Повр.` — qisqartma tarjima qilinmaydigan jargon tug'diradi); *faqat ikonka, legendasiz* (ikonka lug'ati o'rgatilmasa taxminga qoladi).

#### Matritsa tuzilishi

| Element | Qiymat |
|---------|--------|
| Semantika | `<table>` + `<caption class="sr-only">` + `<th scope="col">` (vaqt) + `<th scope="row">` (kamera) |
| Qator tartibi | `channel_no` bo'yicha o'sish — `/cameras` bilan **bir xil** [MEROS: 03-UI-SPEC §6.1] |
| Ustun tartibi | Vaqt bo'yicha o'sish |
| Ustun sarlavhasi | `font-mono text-xs`, `HH:mm` |
| Qator sarlavhasi | Kanal raqami (`font-mono`, ikki xonali) + kamera nomi (`truncate` + `title`) |
| Kenglik | Hujayra `min-w-11` (44px); qator sarlavhasi `w-28` (112px) `sticky left-0 bg-surface` |
| Aylantirish | Konteyner `overflow-x-auto` + `tabIndex={0}` + `role="region"` + `aria-label` (§12.5) |
| Arxivlangan kamera | Jurnalda **ko'rinmaydi** (uning `capture_runs` qatorlari ham yaratilmaydi). Sanoq: xulosa ostida «Arxivlangan kameralar hisobga kirmaydi» — **faqat arxivlangan kamera mavjud bo'lsa** |

### 6.5 Legenda — doimiy, yopilmaydigan, to'liq

```
✓ Olindi   🌑 Qorong'i   ⬛ Bo'sh   ⚠ Buzuq   ✕ Xato   ⊘ Olinmadi
🕐 Kutilmoqda   ⟳ Olinmoqda   − Rejaga kirmagan
```

| Qoida | Nima uchun |
|-------|-----------|
| ⛔ **To'qqizala yozuv DOIM ko'rinadi** — o'sha kunda uchramasa ham | «Faqat mavjudlarini ko'rsatish» legendani kunga qarab o'zgaruvchan qilardi va admin ikonkani **hech qachon** o'rganmasdi |
| Joyi | Matritsaning **ustida**, `<caption>` dan keyin, `flex-wrap`, `text-xs` |
| `<details>` ichida **EMAS** | Yopiq legenda — o'qilmagan legenda |
| Ikonka `aria-hidden="true"` | So'z yonida turibdi, ikki marta e'lon qilinmaydi |
| Bog'lanish | Har legenda yozuvi `id` oladi; hujayra `aria-describedby` **QO'YMAYDI** (175 hujayrada bu skrinriderni bo'g'ardi) — hujayraning to'liq `aria-label` i yetarli |

### 6.6 DL-3 — kadr detali va D-12 ning UI tarjimasi

```
┌ 06:30 · Kiyim qatori (kanal 03) ─────────────────────────────┐
│                                                              │
│   [ kadr rasmi — aspect-video, bg-text letterbox ]           │
│                                                              │
│   Qorong'i kadr — kamera kunduzgi rejimda edi.                │
│   Bu kutilmagan holat: linzani va yoritishni tekshiring.      │
│                                                              │
│   [Hisobga kirmaydi]  [To'liq saqlangan]                      │
│   Olingan: 06:30:04 · Usul: go2rtc · 62 KB · 1280×720         │
│   ▸ Texnik tafsilot                                           │
└──────────────────────────────────────────────────────────────┘
```

**⛔ `quality_verdict` va `light_mode` BITTA JUMLADA birlashadi** [QAROR — D-12 ning UI tarjimasi]:

| `quality_verdict` | `light_mode` | Matn | Tone |
|-------------------|--------------|------|------|
| `ok` | `day` | «Kadr yaroqli — kunduzgi yorug'lik.» | `success` |
| `ok` | `low_light` | «Kadr yaroqli — kam yorug'lik.» | `success` |
| `ok` | `ir_night` | «Kadr yaroqli — kamera tungi IR rejimida.» | `success` |
| `dark` | `ir_night` | «Qorong'i kadr — kamera tungi rejimda edi. **Bu normal holat.**» | `warning` |
| `dark` | `low_light` | «Qorong'i kadr — yorug'lik kam edi.» | `warning` |
| **`dark`** | **`day`** | ⛔ «Qorong'i kadr — kamera **kunduzgi** rejimda edi. Bu kutilmagan holat: linzani va yoritishni tekshiring.» | `warning` |
| `blank` | har qanday | «Bo'sh kadr — tasvirda hech qanday ma'lumot yo'q. Kamera signalini tekshiring.» | `warning` |
| `corrupt` | `unknown` | «Kadr buzuq holda keldi — u to'liq yuklanmagan.» | `warning` |

> **Nega ikkita alohida badge RAD ETILDI:** `[Qorong'i]` `[IR tungi]` juftligi **ikki fakt** beradi, lekin **xulosa bermaydi**. Adminning savoli «kamera buzuqmi?» va unga javob faqat **juftlikning talqinidan** chiqadi. Ikki badge bu talqinni foydalanuvchining zimmasiga yuklardi — va u har kuni 175 marta takrorlanardi.

**Boshqa elementlar:**

| Element | Qoida |
|---------|-------|
| **Rasm** | `aspect-video`, `bg-text` letterbox [MEROS: 03-UI-SPEC §2.3]. **Faqat DL-3 ichida** — jurnalda thumbnail **YO'Q** (G-2) |
| Rasm yuklanmoqda | `Skeleton` ramka ichida; xato bo'lsa `ImageOff` + `snapshots.imageUnavailable`, **dialog yiqilmaydi** |
| **`storage_tier`** | `Badge tone="muted"`: `To'liq saqlangan` / `Siqilgan`. `Siqilgan` bo'lsa `title`: «90 kundan oshgan kadrlar siqilgan holda saqlanadi» |
| **`is_billable === false`** | `Badge tone="warning"` `Hisobga kirmaydi` — **doim `storage_tier` dan oldin** |
| Meta qatori | `captured_at` (soniyagacha) · `capture_method` · `size_bytes` · `width×height`, `text-xs text-text-muted` |
| **`<details>` «Texnik tafsilot»** | `quality_mean`, `quality_stddev`, `quality_saturation`, `quality_thresholds_version`, `attempts`, `capture_method` — `font-mono text-xs`. **Faqat qiymat mavjud bo'lganda** render qilinadi |
| C5/C6/C7/C8/C9 hujayrasida | Rasm **yo'q** — o'rniga sabab bloki (`capture-errors.ts`): SABAB + NIMA QILISH KERAK + kim tuzatadi (`actor`) |
| Navigatsiya | Dialog ichida `[◀]` `[▶]` — **o'sha qatordagi** oldingi/keyingi vaqtga. Kamera bo'ylab emas: admin bitta kameraning kunini ketma-ket ko'radi |

> **[TALAB]** Kadr rasmi **core-api orqali proxy qilinadi**: `GET /api/v1/snapshots/{id}/image`. Ombor (SeaweedFS) endpointi brauzerga **hech qachon** ochilmaydi va presigned URL **berilmaydi** — bu 3-fazadagi go2rtc HTTP yuzasi qoidasining aynan takrori [MEROS: 03-UI-SPEC §8.7]. **G-4 darvozasi** buni mexanik tekshiradi.
>
> **[TALAB]** Kadr rasmini o'qish `audit_read` yozuvini yozadi — kadr bozor tashrifchilarining shaxsiy ma'lumoti [MEROS: 2-faza D-09 naqshi, `stalls.py:304-345`].

### 6.7 Zona B — ogohlantirishlar (Y-4, D-19, D-22)

```
┌ ⚠ Kadr olish to'xtadi ────────────────────────── critical ─┐
│   Birinchi marta: bugun 07:02 · Oxirgi marta: 3 daqiqa oldin│
│   So'nggi soatda yana 47 marta                              │
│   Telegram xabari yuborildi: bugun 07:05                    │
│   Sabab: NVR qurilmasiga ulanib bo'lmadi (22 kamera)        │
└─────────────────────────────────────────────────────────────┘
```

| Element | Qoida |
|---------|-------|
| Render sharti | ⛔ **Faqat ochiq ogohlantirish bo'lsa** (Z-3). Bo'sh «hammasi yaxshi» paneli **qurilmaydi** |
| `severity` | `Badge`: `info` → `neutral`, `warning` → `warning`, `critical` → `danger` |
| Sarlavha | `alert_key` → tarjima kaliti (`snapshots.alertKey.*`), **xom kalit hech qachon** |
| Vaqtlar | `first_seen_at` va `last_seen_at` — ikkalasi ham **majburiy**. Faqat oxirgisi «bu qachondan beri davom etyapti?» savolini javobsiz qoldirardi |
| **`occurrences > 1`** | ⛔ **Majburiy qator**: «So'nggi soatda yana {count} marta». D-22 ning guruhlashi **ma'lumot yashirish** bo'lib ko'rinmasligi kerak |
| **`notified_at`** | «Telegram xabari yuborildi: {time}». `null` bo'lsa: «Telegram xabari **yuborilmadi**» + `title` bilan sabab (token sozlanmagan / xato). ⛔ Bu qator **yashirilmaydi** — «alert bor deb o'ylash» yolg'oni aynan shu yerda tug'iladi [MEROS: 04-RESEARCH §E.12] |
| Tafsilot | `detail` dagi **ruxsat berilgan kalitlar**: `market_name`, `camera_count`, `error_code`, `slot_time`, `stale_hours`, `disk_pct`. Noma'lum kalit **render qilinmaydi** |
| ⛔ **Rasm** | **YO'Q.** `<img>`, thumbnail, «dalilni ko'rish» havolasi — **hech biri** (D-19, **G-3**) |
| Yopilgan ogohlantirish | Checkbox «Yopilganlarni ham ko'rsatish» (`?closed=1`), standart **o'chiq**. Yopilgan qator `bg-surface-muted` + `resolved_at` + davomiylik («2 s 15 daq davom etdi») |
| Sanoq | Zona sarlavhasida: «Ochiq: {n}». Nol bo'lsa zona render qilinmaydi |
| Amal | ⛔ **Yopish/bostirish tugmasi YO'Q.** Ogohlantirishni faqat **tiklanish** yopadi (backend `resolved_at`). Qo'lda yopish tugmasi adminga muammoni ko'rmasdan yashirish imkonini berardi |
| Semantika | `<ul>`/`<li>`; zona `role="region"` + `aria-label`. `role="alert"` **QO'YILMAYDI** — ro'yxat sahifa yuklanganda mavjud, u yangi hodisa emas |

### 6.8 Poll kontrakti — bugungi kun uchun, boshqa kun uchun emas

```ts
useQuery({
  queryKey: captureDayKey(marketId, day),
  refetchInterval: day === todayIso && hasActiveRuns ? CAPTURE_POLL_INTERVAL_MS : false,
  refetchIntervalInBackground: false,
  enabled: marketId !== null,
})
```

| Parametr | Qiymat | Sabab |
|----------|--------|-------|
| **`CAPTURE_POLL_INTERVAL_MS`** | **30 000** | Slotlar orasidagi eng kichik oraliq — 15 daqiqa (§4.6). 30 s yangilanish «hozir olinyapti» ni ko'rsatish uchun **yetarlidan ko'p**; 2 s (3-fazadagi qiymat) bu yerda serverni **900 barobar** ortiqcha yuklardi |
| **Poll sharti** | `day === bugun` **VA** kunda `pending`/`running` qator bor | O'tgan kun **o'zgarmaydi** — uni poll qilish bekor yuk. Bugungi kun tugagach (`hasActiveRuns === false`) poll **o'zi to'xtaydi** |
| **Yashirin tab** | `refetchIntervalInBackground: false` | 3-faza kontrakti |
| **Cheksiz poll** | ⛔ **Hech qachon** | Terminal shart yuqorida; qo'shimcha taymer kerak emas, chunki shart ma'lumotdan hosil bo'ladi |
| **Ogohlantirish zonasi** | O'sha `CAPTURE_POLL_INTERVAL_MS`, faqat `day === bugun` bo'lganda | Ogohlantirish jurnal bilan **bir vaqtda** yangilanishi kerak — aks holda «2 kadr olinmadi» ko'rinib turib ogohlantirish paydo bo'lmasdi |
| **Jadval zonasi (A)** | Poll **YO'Q** | Jadval kunda bir marta o'zgaradi; `refetchOnWindowFocus` yetarli |

---

## 7. Bo'shliq (spacing)

### 7.1 4-panjara — o'zgarishsiz [MEROS: 02-UI-SPEC §2, 03-UI-SPEC §2.1]

| Token | Qiymat | 4-fazada qayerda |
|-------|--------|------------------|
| `xs` | 4px (`1`) | Hujayralar orasi (`gap-1`), ikonka–matn oralig'i, badge ichki `y` |
| `sm` | 8px (`2`) | Legenda yozuvlari orasi, vaqt chiplari orasi, yorliq↔maydon |
| `md` | 12px (`3`) | Ogohlantirish qatorlari orasi, xulosa hisoblagichlari orasi |
| `lg` | 16px (`4`) | Karta ichki, forma maydonlari orasi, dialog bo'limlari |
| `xl` | 24px (`6`) | Zona oralig'i (A↔B↔C↔D) |
| `2xl` | 32px (`8`) | Katta bo'lim uzilishi |
| `3xl` | 48px (`12`) | Bo'sh holat `py-12` |

**Meros istisnolari saqlanadi:** 44px (`min-h-11`) barcha barmoq nishoni; 56px (`min-h-14`) mobil pastki panel; 20px (`5`) `CardHeader`/`CardContent` ichki `x`.

### 7.2 Ikkita yangi o'lcham — ikkalasi ham panjaradan [QAROR]

| O'lcham | Qiymat | Tailwind | Nima uchun panjaradan chiqmaydi |
|---------|--------|----------|----------------------------------|
| **Jurnal hujayrasi** | **44 × 44px** | `min-h-11 min-w-11` | Bu **yangi qiymat emas** — 2-fazadan meros qolgan barmoq nishoni o'lchami. Hujayra bosiladigan (DL-3 ni ochadi), ya'ni u nishon; kichraytirish WCAG 2.5.8 ni buzardi |
| **Qator sarlavhasi ustuni** | **112px** | `w-28` | 28 × 4 = 112 — **panjarada**. Kanal raqami (`font-mono`, 2 xona ≈ 18px) + bo'shliq + nom (`truncate`). 96px (`w-24`) da rus tilidagi kamera nomi ikki belgidan keyin kesilardi |

**Boshqa yangi qiymat so'ralmaydi.** Rasm ramkasi **balandlik bermaydi** — u `aspect-video` (16/9) bilan kenglikdan hosil bo'ladi, ya'ni spacing tokeni emas [MEROS: 03-UI-SPEC §2.1].

### 7.3 Matritsaning umumiy kengligi — o'lchangan arifmetika

```
7 vaqt × 44px + 6 × 4px (gap) = 308px    (hujayralar)
+ 112px (sticky qator sarlavhasi)        = 420px
```

| Ekran | Natija |
|-------|--------|
| Desktop (≥1024px) | To'liq sig'adi, ortiqcha joy qoladi |
| Planshet (768px) | Sig'adi |
| Mobil (390px) | **30px gorizontal aylantirish** — sticky sarlavha kontekstni ushlab turadi (§13.2) |
| Mobil (360px) | 60px aylantirish |
| Qishki profil (5 vaqt) | `5 × 44 + 4 × 4 + 112 = 348px` — **360px'da ham to'liq sig'adi** |

⛔ **Aylantirish ma'lumot yashirmaydi:** kunlik xulosa (§6.3) barcha sonlarni **matn sifatida** beradi, ya'ni matritsani umuman aylantirmagan foydalanuvchi ham kunning javobini oladi. Matritsa — tafsilot, yagona manba emas.

---

## 8. Tipografiya

### 8.1 To'rt rol — o'zgarishsiz [MEROS: 03-UI-SPEC §2.2]

| Rol | O'lcham | Og'irlik | Line-height | Tailwind |
|-----|---------|----------|-------------|----------|
| **Display** — sahifa sarlavhasi | 24px | 600 | 1.25 | `text-2xl font-semibold tracking-tight leading-tight` |
| **Heading** — karta/dialog/`<legend>` | 18px | 600 | 1.375 | `text-lg font-semibold leading-snug` |
| **Body** — barcha matn va boshqaruv elementi | 14px | 400 | 1.5 | `text-sm leading-normal` |
| **Meta** — badge, legenda, hisoblagich yorlig'i, vaqt belgisi | 12px | 400 | 1.33 | `text-xs` |

**Urg'u — faqat og'irlik (600), o'lcham emas, rang emas.** `font-medium` (500) va `text-base` (16px) **taqiqlangan** [MEROS: 02-UI-SPEC §3.2 — Wave 0 da chiqarib tashlangan].

### 8.2 Beshinchi o'lcham QO'SHILMAYDI — matritsa uchun ham

Vasvasa aniq: 175 hujayrali matritsada `text-[10px]` «ko'proq sig'dirardi». **Rad etiladi** [QAROR]:

1. Hujayrada **matn yo'q** (§6.4) — kichraytiriladigan narsaning o'zi yo'q.
2. Ustun sarlavhasi (`06:30`) `text-xs` da o'qiladi; 10px 200% zoomda ham, keksa foydalanuvchida ham yiqiladi.
3. Beshinchi o'lcham kiritilsa u **butun kodbazaga** tarqaladi — 2-fazada `text-base` aynan shunday kirib kelgan va Wave 0 da chiqarib tashlangan.

### 8.3 `font-mono` — hujjatlashtirilgan istisno, 4-faza ro'yxati

`font-mono` — **faqat** o'qib aytiladigan yoki belgima-belgi solishtiriladigan texnik qiymat uchun [MEROS: 03-UI-SPEC §2.2].

| Qiymat | Uslub | Sabab |
|--------|-------|-------|
| Vaqt (`06:30`) — matritsa sarlavhasi, jadval kartasi, slot chiplari | `font-mono text-xs` | Vaqtlar **ustunlashadi** — proporsional shriftda `06:00` va `18:00` turli kenglikda bo'lib, ro'yxat qiyshayardi |
| Kanal raqami (`03`) | `font-mono text-xs` | `/cameras` bilan bir xil [MEROS: 03-UI-SPEC §6.1] |
| `quality_mean` / `stddev` / `saturation` | `font-mono text-xs` | Raqamlar ustunlashadi va SQL bilan solishtiriladi (D-15) |
| `size_bytes`, `width×height` | `font-mono text-xs` | O'sha sabab |
| `capture_method` ning **xom tokeni** (`go2rtc`) | `font-mono text-xs`, **faqat `<details>` ichida** | Texnik yordamga nusxalanadi (§10.7) |
| `object_key` | ⛔ **HECH QACHON ko'rsatilmaydi** | §14.3 |

**Sana `font-mono` EMAS** — u `next-intl` bilan formatlanadi va matn sifatida o'qiladi, solishtirilmaydi.

`font-mono text-xl` (2-fazadagi vaqtinchalik parol istisnosi) bu fazada **ishlatilmaydi** — ovoz chiqarib o'qiladigan sir yo'q.

---

## 9. Rang kontrakti (60/30/10)

### 9.1 Taqsimot — o'zgarishsiz

| Rol | Token | Qiymat | 4-fazada qayerda |
|-----|-------|--------|------------------|
| **Dominant (60%)** | `--color-bg` | `oklch(0.985 0 0)` | Sahifa foni, matritsaning bo'sh joyi |
| **Ikkilamchi (30%)** | `--color-surface` | `oklch(1 0 0)` | Kartalar, hujayralar, dialoglar, sticky qator sarlavhasi |
| | `--color-surface-muted` | `oklch(0.968 0 0)` | Skeleton, yopilgan ogohlantirish qatori, `pending`/`skipped` hujayra |
| **Aksent (10%)** | `--color-accent` | `oklch(0.56 0.19 255)` | §9.3 ro'yxati — **qisqargan** |
| **Destruktiv** | `--color-danger` | `oklch(0.58 0.21 27)` | `failed`/`missed` hujayra, `critical` ogohlantirish, profil o'chirish tasdig'i |

**Yangi token kiritilmaydi.** Yangi rang juftligi ham so'ralmaydi: kadr ramkasining `bg-text` + `text-bg` juftligi (15,6:1) 3-fazada allaqachon hisoblangan va **qayta ishlatiladi** [MEROS: 03-UI-SPEC §2.3].

### 9.2 `--color-warning` matn sifatida ISHLATILMAYDI

Sariq tintdagi matn — `bg-warning/20 text-text` (o'lchangan **15,64:1**) [KOD: `badge.tsx:17-25`]. `--color-warning` oq fonda **2,03:1** — falokat.

Bu 4-fazada **uch joyda** muhim: `warning` tone'li hujayralar (C2/C3/C4), D-05 farq izohi, `CoverageWarning` bloki. Uchalasi ham `bg-warning/20 text-text`.

### 9.3 ⛔ Aksent — 4-fazada QISQARGAN ro'yxat [QAROR]

Aksent rang **faqat** quyidagilarda:

1. **Fokus halqasi** (`:focus-visible outline`) — barcha interaktiv elementlar, jumladan matritsa hujayrasi.
2. **Faol maydon chegarasi va halqasi** (`focus-visible:border-accent`, `ring-accent/25`).
3. **Joriy navigatsiya elementi** — faqat mobil pastki panelda.
4. **Checkbox `accent-color`** — «Faqat muammolilarni ko'rsatish», «Yopilganlarni ham ko'rsatish».
5. **Dialog ichidagi birlamchi tugma** — DL-1/DL-2 dagi «Saqlash» / «Qo'shish». **Dialogda eng ko'pi bilan bitta.**

> ⛔ **Sahifaning O'ZIDA aksent fonli tugma YO'Q** [QAROR]. Bu 3-fazadan **farq** va u ataylab: `/cameras` bir va'dani bajaradigan **harakat** sahifasi edi («tugmani bos — kameralar paydo bo'lsin»), `/snapshots` esa **kuzatuv** sahifasi. Uning to'g'ri javobi — «hamma narsa joyida», ya'ni foydalanuvchini birinchi navbatda bosishga chaqiradigan tugma **yo'q**. «Jadvalni tahrirlash» va «Mavsumiy jadval qo'shish» — ikkalasi ham `secondary`.

**Aksent ishlatilMAYDIGAN joylar (aniq taqiq):** hujayra holatlari (to'qqizala), legenda, sifat badge'lari, ombor qatlami badge'i, ogohlantirish darajasi, kun tanlagichi, `<details>` ochilish belgisi, xulosa hisoblagichlari, «Bugun» tugmasi.

### 9.4 Rang hech qachon YAGONA signal emas (WCAG 1.4.1)

| Holat | Rang kanali | Qo'shimcha kanal 1 | Qo'shimcha kanal 2 | Qo'shimcha kanal 3 |
|-------|-------------|--------------------|--------------------|--------------------|
| **C1** Olindi | `success` | `CheckCircle2` | `aria-label` + legenda so'zi | — |
| **C2** Qorong'i | `warning` | `MoonStar` | `aria-label` + legenda so'zi | — |
| **C3** Bo'sh | `warning` | `ImageOff` | `aria-label` + legenda so'zi | — |
| **C4** Buzuq | `warning` | `FileWarning` | `aria-label` + legenda so'zi | — |
| **C5** Xato | `danger` | `XCircle` | `aria-label` + legenda so'zi | — |
| **C6** ⛔ Olinmadi | `danger` | `CircleSlash` | `aria-label` + legenda so'zi | ⛔ **`border-dashed`** (shakl) |
| **C7** Kutilmoqda | `muted` | `Clock` | `aria-label` + legenda so'zi | — |
| **C8** Olinmoqda | `neutral` | `Loader2` (harakat) | `aria-label` + legenda so'zi | — |
| **C9** Rejaga kirmagan | `muted` | `Minus` | `aria-label` + legenda so'zi | `border-dashed` |
| Ogohlantirish `critical` | `Badge tone="danger"` | Badge **matni** «Jiddiy» | Sarlavha matni | — |
| Ogohlantirish `warning` | `Badge tone="warning"` | Badge matni «Ogohlantirish» | Sarlavha matni | — |
| Ogohlantirish yopilgan | qator `bg-surface-muted` | `resolved_at` vaqti | Davomiylik matni | — |
| «Hisobga kirmaydi» | `Badge tone="warning"` | Badge **matni** | DL-3 dagi to'liq jumla | — |
| `storage_tier` | `Badge tone="muted"` | Badge matni | `title` izohi | — |

> **C2/C3/C4 bir xil tone'da (`warning`) — bu qabul qilinadi.** Ular **bir sinfning** uchta a'zosi («hisobga kirmaydi») va ularni rang bilan ajratish to'rtinchi ogohlantirish rangini talab qilardi. Ajratish **ikonka** bilan bajariladi va u legenda orqali o'rgatiladi. Kunlik xulosa esa uchalasini **alohida sanaydi** (§6.3), ya'ni kun darajasidagi javob rangsiz ham to'liq.

### 9.5 Kadr rasmi va uning ramkasi

| Element | Token | Sabab |
|---------|-------|-------|
| DL-3 dagi rasm ramkasi (letterbox) | `bg-text` (`oklch(0.205 0 0)`) | Oq letterbox qorong'i bozor kadrida tasvir chegarasini yo'q qilardi [MEROS: 03-UI-SPEC §2.3] |
| Ramka ustidagi holat matni | `text-bg` | O'lchangan **15,6:1** ✅ AAA |
| Rasm hali yuklanmagan | `bg-surface-muted` + `Skeleton` | Qora to'rtburchak «buzilgan» degan yolg'on signal berardi — 3-faza `idle` qoidasining aynan takrori |

---

## 10. Matn (copywriting) kontrakti

### 10.1 Birlamchi amallar — sahifada ikkita, ikkalasi ham `secondary`

| Amal | Yorliq (uz-Latn) | Variant | Qayerda |
|------|------------------|---------|---------|
| Jadval vaqtlarini o'zgartirish | **Jadvalni tahrirlash** | `secondary` | Zona A |
| Yangi mavsumiy davr | **Mavsumiy jadval qo'shish** | `secondary` | Zona A |
| Dialogda saqlash (DL-1) | **Saqlash** | `default` (dialogning yagona aksenti) | DL-1 |
| Dialogda qo'shish (DL-2) | **Qo'shish** | `default` | DL-2 |
| Vaqt qo'shish | **Vaqt qo'shish** | `secondary` | Slot muharriri |
| Oraliqni kengaytirish | **To'ldirish** | `secondary` | Slot muharriri |
| Muammoli qatorlarga o'tish | **Muammolilarni ko'rsatish** | `ghost` havola | Zona C |

**Yorliq fe'l + ot bo'ladi, generic emas** [MEROS: 02-UI-SPEC §10.6]. «Tasdiqlash», «OK», «Yuborish» — **ishlatilmaydi**.

### 10.2 ⛔ Taqiqlangan so'zlar

| Taqiq | Nima uchun | Darvoza |
|-------|------------|---------|
| **«slot»** (uchala tilda) | Bu **orkestratsiya muhandisining atamasi**, bozor adminining emas. `capture_runs.slot_time` — DB ustuni; foydalanuvchi uchun bu shunchaki **vaqt**. Uch tilga «slot» ni olib kirish tarjimonni ham, adminni ham yangi tushunchaga majbur qilardi va u hech qanday aniqlik qo'shmaydi | **G-1** |
| **«kadrni o'chirish» / «kadrlarni o'chirish» / «удалить кадр» / «удалить снимок»** | 04-RESEARCH §D.10: *«⚠ QATOR HECH QACHON O'CHIRILMAYDI»* — kadr faqat **siqiladi**, hech qachon o'chirilmaydi. Bu so'z UI'ga bir marta kirsa, u tarjima orqali tarqaladi va D-18 ni jimgina yolg'onga aylantiradi | **G-10** |
| **«xatolik yuz berdi»** yolg'iz | Sababsiz xato — 3-faza D-02 ning aynan taqig'i | **G-5** |
| **«tekshirilmoqda…» / «yuklanmoqda…» tugallanmaydigan shaklda** | Har holat nomlanadi va chegaralanadi (§6.2) | Ko'rik |

> **«slot» taqig'iga bitta istisno YO'Q.** «Vaqt», «kadr olish vaqti», «reja» — uchala tilda yetarli. Kod, DB, API va bu hujjatning texnik bo'limlarida «slot» **qoladi** — taqiq faqat `messages/*.json` ning `snapshots.*` kalitlariga tegishli.

### 10.3 «Hisobga kirmaydi» — fakt, ogohlantirish emas [D-16]

| ❌ Taqiqlangan shakl | ✅ To'g'ri shakl | Sabab |
|---------------------|------------------|-------|
| «Diqqat! Bu kadr yaroqsiz» | «Hisobga kirmaydi» | Bu **nosozlik emas** — filtr aynan shu ish uchun qurilgan. Ogohlantirish tili adminni har qorong'i tong kadridan qo'rqitardi |
| «Bu kadr rad etildi» | «Sifat tekshiruvidan o'tmagan kadr kunlik hisobga kirmaydi.» | «Rad etildi» kadr **yo'q qilingan** degan taassurot beradi; u saqlanadi (§16) |
| «Xato: qorong'i kadr» | «Qorong'i kadr — kamera tungi rejimda edi. Bu normal holat.» | D-12 ning butun mazmuni: qorong'ilik o'z-o'zidan nosozlik emas |

### 10.4 Bo'sh holatlar — to'rttasi, har biri boshqa keyingi qadam bilan

| # | Holat | Sarlavha | Keyingi qadam |
|---|-------|----------|---------------|
| **E-1** | Bozorda kamera yo'q | **Bu bozorda kamera yo'q** | **[Kameralar bo'limiga o'tish]** — `variant="secondary"`, `/cameras` ga havola |
| **E-2** | Kun jadvalga kirmagan (Z-7) | **Bu kunda kadr rejalashtirilmagan** | Amal **yo'q**; tavsifda sabab. `uncovered_days > 0` bo'lsa qo'shimcha havola: **[Jadvalni ko'rish]** |
| **E-3** | Filtr hech narsa topmadi (Z-10) | **Muammoli qator topilmadi** | **[Filtrni tozalash]** — `variant="secondary"` |
| **E-4** | Yopilgan ogohlantirish yo'q (Z-4) | **Yopilgan ogohlantirish yo'q** | Amal **yo'q** — checkbox allaqachon ko'rinadi |

⛔ **«Jadval qo'shing» bo'sh holati YO'Q** — D-01 bo'yicha jadval har doim mavjud. Agar u yo'q bo'lsa, bu ma'lumot nosozligi va u E-2 ning tavsifi orqali ko'rinadi, «qo'shing» chaqirig'i orqali emas.

**DL-1 ning «profil topilmadi» holati** [quick 260815-86p]. Yuqoridagi qoida endi dialog ichida ham nomlangan holat: `GET /snapshot-schedules` bo'sh ro'yxat qaytarganda DL-1 `snapshots.scheduleMissing` sarlavhasi va `snapshots.scheduleMissingHint` izohini chizadi. Bu **E-5 emas** va yuqoridagi to'rtlikka qo'shilmaydi — u bo'sh holat emas, **ma'lumot nosozligining ta'rifi**: matn faktni aytadi (jadval yozilmagan, uni usta avtomatik yozadi) va dialogni yopib sahifani yangilashni so'raydi. ⛔ Unda **tugma ham, havola ham yo'q** — «qo'shing» chaqirig'i D-01 ni jimgina yolg'onga aylantirardi va nosozlik uchun javobgarlikni adminga yuklardi. Ilgari bu holat `common.loading` chizardi, ya'ni tugagan so'rovni tugamagan deb ko'rsatardi (TEST-REPORT 2026-08-14, Topilma №6). Bir xil sababdan **profilsiz kartada «Jadvalni tahrirlash» tugmasi umuman render qilinmaydi**; «Mavsumiy jadval qo'shish» esa qoladi — u yangi profil yaratadi va obyektsiz ham ma'noli.

**Va bu holat AYNAN BITTA emas, IKKITA** [quick 260816-5yz]. `target === null` bo'lishining ikki sababi bor va ular **boshqa-boshqa fakt**:

| Shart | Sarlavha / izoh | Nima ro'y bergan |
|-------|-----------------|------------------|
| `items.length === 0` | `snapshots.scheduleMissing` / `scheduleMissingHint` | Bozorda jadval **umuman yozilmagan** — D-01 bo'yicha bu tizimning nosozligi |
| `items.length > 0 && target === null` | `snapshots.scheduleNotFound` / `scheduleNotFoundHint` | Jadval **yozilgan**, faqat so'ralgan profil ro'yxatda yo'q (o'chirilgan yoki ro'yxat yangilangan) |

⛔ Ikkinchi holatda «Bu bozorda jadval yozilmagan» deyish **faktik yolg'on** edi va u adminni mavjud bo'lmagan nosozlikni izlashga yuborardi. ⛔ **Ikkalasi ham `EmptyState` bilan chiziladi va `action` proppi BERILMAYDI** — yuqoridagi «tugma ham, havola ham yo'q» qoidasining mexanik shakli. Ikkalasi ham **E-1…E-4 to'rtligiga qo'shilmaydi**.

⛔ **E-3 «hammasi yaxshi» degani EMAS** — u filtr natijasi. Matni «Bu kunda barcha kadrlar yaroqli» — bu **fakt**, tabrik emas.

### 10.5 Xato kontrakti — SABAB + NIMA QILISH KERAK + KIM

`NvrErrorBlock` ning shakli meros olinadi [MEROS: 03-UI-SPEC §7.1] va **bitta ustun qo'shiladi**:

```
┌ [icon] ──────────────────────────────────────────────┐
│  SABAB                                               │
│  Kamera manbasiga ulanib bo'lmadi.                   │
│                                                      │
│  NIMA QILISH KERAK                                   │
│  WireGuard tunneli yoqilganini va NVR qurilmasi      │
│  tarmoqda ekanini tekshiring.                        │
│                                                      │
│  Bozor admini tuzatadi                               │
└──────────────────────────────────────────────────────┘
```

**Uchinchi qator — `actor`** [QAROR, §5.3]:

| `actor` | Matn | Nima uchun kerak |
|---------|------|------------------|
| `admin` | «Bozor admini tuzatadi» | Adminning o'z ishi — u darhol harakat qiladi |
| `platform` | «Platforma jamoasi tuzatadi» | ⛔ Bozor admini bu xatoni tuzata **olmaydi**. Usiz u soatlab NVR sozlamalarini titkilardi. Bu 4-fazada **yangi** va u kerak, chunki xatolarning bir qismi (worker o'lishi, ombor yiqilishi) infratuzilma ishi |
| `none` | «Harakat talab qilinmaydi» | `capture_plan_created_late` — normal holat. «Nima qilay?» savoliga «hech nima» javobi **aniq aytilishi** kerak |

`actor` — `text-xs text-text-muted`, ikonkasiz. **Badge emas** — u sabab va tuzatish bilan bir darajaga chiqmasligi kerak.

**Ikkita tone** [MEROS: 03-UI-SPEC §7.2]:

| Tone | Uslub | Ikonka | Qachon |
|------|-------|--------|--------|
| **`danger`** | `bg-danger/10 text-danger-text` | `AlertCircle` | Kadr **umuman olinmadi** (C5, C6) |
| **`warning`** | `bg-warning/20 text-text` | `TriangleAlert` | Kadr olindi, lekin **hisobga kirmaydi** (C2, C3, C4); yoki normal holat (C9) |

**Noma'lum kod** → `errors.generic` + **`error_detail` KO'RSATILMAYDI** [MEROS: 02-UI-SPEC T-02-99].

### 10.6 Toast reyestri — uchtasi, boshqa emas

`sonner`, `position="top-center" richColors` [KOD: `layout.tsx:82`].

| # | Qachon | Kalit |
|---|--------|-------|
| T-1 | Jadval vaqtlari saqlandi | `snapshots.toastScheduleSaved` |
| T-2 | Mavsumiy jadval qo'shildi | `snapshots.toastSeasonalAdded` |
| T-3 | Mavsumiy jadval o'chirildi | `snapshots.toastSeasonalDeleted` |

**Toast QO'YILMAYDIGAN joylar** [QAROR]: kun almashtirish, filtr yoqish, DL-3 ochilishi/yopilishi, jurnalning poll bilan yangilanishi, ogohlantirishning paydo bo'lishi yoki yopilishi.

> **Ogohlantirish uchun toast nima uchun YO'Q:** ogohlantirish — **davomiy holat**, o'tkinchi hodisa emas. Toast 4 soniyada yo'qoladi va admin uni o'tkazib yuborardi; zona B esa muammo hal bo'lgunicha **ekranda turadi**. D-20 aynan shu farqni talab qiladi.

### 10.7 Texnik qiymatlar — foydalanuvchi tilida, xom token `<details>` da

| Xom qiymat | Foydalanuvchi ko'radi | Xom token qayerda |
|------------|----------------------|-------------------|
| `capture_method = "go2rtc"` | «Oqimdan» | `<details>` ichida `font-mono` |
| `capture_method = "isapi"` | «NVR qurilmasidan» | O'sha joyda |
| `capture_method = "ffmpeg"` | «Zaxira yo'l bilan» | O'sha joyda |
| `quality_thresholds_version = 1` | «Chegaralar to'plami: 1» | `<details>` ichida |
| `object_key` | ⛔ **Hech qachon** | ⛔ **Hech qachon** (§14.3) |

> **Nega xom token butunlay olib tashlanmaydi:** dala diagnostikasida «qaysi yo'l bilan olingan?» birinchi savol va `go2rtc` — texnik yordam tushunadigan yagona aniq javob. Lekin u **birlamchi** matn bo'lsa, admin uni tarjima qilinmagan xato deb qabul qilardi. Yechim 3-fazadagi bilan bir xil: inson tili yuzada, xom token `<details>` da.
>
> ⚠ **Xom token `messages/*.json` ga KIRMAYDI** — u API javobidan to'g'ridan-to'g'ri chiziladi. Sabab o'lchangan (M-3): `go2rtc` — alfanumerik token va u xabar katalogiga tushsa transliterator uni buzardi (`го2ртc`), override esa uni **tuzata olmaydi**.

### 10.8 Destruktiv amal — bittasi, va u ataylab tor

| Amal | Tasdiq | Sabab |
|------|--------|-------|
| **Boshlanmagan mavsumiy jadvalni o'chirish** | `ConfirmDialog` **1-daraja**, `confirmVariant="destructive"`, tasdiq tugmasi matni **«O'chirish»** | 2-daraja (nom yozib tasdiqlash) **faqat UI'dan qaytarib bo'lmaydigan** amallar uchun [MEROS: 02-UI-SPEC §10.6]. Bu jadval hali birorta kadr olmagan — o'chirish **ma'lumot yo'qotmaydi** va uni qayta qo'shish mumkin |
| Fokus dialog ochilganda | **Bekor qilishda** — hech qachon destruktiv tugmada [KOD: `confirm-dialog.tsx`] | Meros |
| Dialog tanasi | «…hali boshlanmagan, shuning uchun uni o'chirish mumkin. **Olingan kadrlarga ta'sir qilmaydi.**» | Ikkinchi jumla majburiy: admin «kadrlarim ham ketadimi?» savolini bermasligi kerak |

**Boshqa destruktiv amal YO'Q.** Amaldagi yoki tugagan jadval o'chirilmaydi (§4.5) — tugma **render qilinmaydi**, `aria-disabled` ham emas, chunki u umuman mavjud bo'lmasligi kerak. Sabab qator `title` ida: «Boshlangan jadval o'chirilmaydi — u o'tmishdagi kadrlarni tushuntiradi».

---

## 11. Xabar-katalog kalitlari

> `uz-Cyrl` **avtomatik hosil qilinadi** (`npm run i18n:gen`) — qo'lda yozilmaydi. Qo'lda yoziladigan tillar: **uz-Latn** (manba) va **ru**.
> Quyidagi barcha uz-Latn satrlari `transliterate()` dan o'tkazildi — **0 mexanik defekt** [O'LCHANDI: M-1].
> Yagona namespace — **`snapshots.*`**; uchinchi daraja **faqat enum xaritalari** uchun (`cell`, `verdict`, `alertKey`, `errorCause`, `errorFix`, `actor`, `severity`, `method`) [MEROS: 02-UI-SPEC §1.1].

> **Nega `schedule.*` alohida namespace EMAS** [QAROR]: jadval foydalanuvchi uchun mustaqil obyekt emas — u «kadr olish» bo'limining bir qismi. Ikkita namespace bir-biriga yaqin ~110 kalitni ikkiga bo'lardi va tarjimonni ikki joyga qaratardi. Jadvalga xos kalitlar `snapshots.schedule*` prefiksi bilan ajratiladi.

### 11.1 Navigatsiya va sarlavhalar

| Kalit | uz-Latn | ru |
|-------|---------|-----|
| `nav.snapshots` | **Kadr olish** | **Съёмка кадров** |
| `snapshots.title` | Kadr olish | Съёмка кадров |
| `snapshots.scheduleTitle` | Jadval | Расписание |
| `snapshots.logTitle` | Ijro jurnali | Журнал выполнения |
| `snapshots.alertsTitle` | Ogohlantirishlar | Оповещения |

> **`nav.snapshots` = «Kadr olish», «Kadrlar» EMAS** [QAROR]. O'zbek tilida «kadrlar» **xodimlar** ma'nosini ham beradi (`kadrlar bo'limi` = HR). Yolg'iz ot sifatida u ikki ma'noli; `Kadr olish` — harakat nomi va u bir ma'noli. Rus tilida bu muammo yo'q, lekin izchillik uchun `Съёмка кадров` ishlatiladi (`Снимки` emas — u fotosurat albomini eslatadi).

### 11.2 Jadval kartasi (zona A)

| Kalit | uz-Latn | ru |
|-------|---------|-----|
| `snapshots.today` | Bugun | Сегодня |
| `snapshots.tomorrow` | Ertaga | Завтра |
| `snapshots.timesCount` | {count} marta | {count} раз |
| `snapshots.scheduleFrom` | {date} dan | с {date} |
| `snapshots.scheduleUntil` | {date} gacha | до {date} |
| `snapshots.scheduleModePast` | Tugagan | Завершено |
| `snapshots.scheduleModeActive` | Amaldagi | Действует |
| `snapshots.scheduleModeFuture` | Boshlanmagan | Ещё не началось |
| `snapshots.editSchedule` | Jadvalni tahrirlash | Изменить расписание |
| `snapshots.addSeasonal` | Mavsumiy jadval qo'shish | Добавить сезонное расписание |
| **`snapshots.takesEffectTomorrow`** | **Bugungi reja o'zgarmaydi — yangi vaqtlar ertadan kuchga kiradi.** | **Сегодняшний план не меняется — новые времена вступают в силу с завтра.** |
| **`snapshots.editNote`** | **Bugungi reja allaqachon tuzilgan. Yangi vaqtlar ertadan boshlab ishlaydi — bugungi kadrlar eski jadval bo'yicha olinadi.** | **Сегодняшний план уже составлен. Новые времена начнут действовать с завтра — сегодняшние кадры снимаются по старому расписанию.** |
| `snapshots.closedDaysIncluded` | Yopiq kunlarda ham kadr olinadi | Кадры снимаются и в закрытые дни |
| `snapshots.closedDaysWhy` | Yopiq kunda band rasta — tizim izlaydigan nomuvofiqlikning o'zi. | Занятое место в закрытый день — именно то несоответствие, которое ищет система. |
| **`snapshots.coverageTitle`** | **Ba'zi kunlar jadvalga kirmagan** | **Некоторые дни не входят в расписание** |
| `snapshots.coverageBody` | Keyingi {horizon} kunda {count} kun qoplanmagan — o'sha kunlarda kadr olinmaydi. | В ближайшие {horizon} дней не покрыто дней: {count} — в эти дни кадры не снимаются. |
| `snapshots.coverageFix` | Mavsumiy jadval qo'shing yoki amaldagi jadvalning tugash sanasini olib tashlang. | Добавьте сезонное расписание или уберите дату окончания у действующего. |

### 11.3 Slot muharriri

| Kalit | uz-Latn | ru |
|-------|---------|-----|
| `snapshots.times` | Vaqtlar | Времена |
| `snapshots.addTime` | Vaqt qo'shish | Добавить время |
| `snapshots.removeTime` | Vaqtni olib tashlash | Убрать время |
| `snapshots.timesUsage` | {used} / {max} | {used} / {max} |
| **`snapshots.slotLimitReached`** | **Kuniga ko'pi bilan {max} marta kadr olinadi.** | **В день снимается не больше {max} раз.** |
| `snapshots.slotDuplicate` | Bu vaqt allaqachon qo'shilgan | Это время уже добавлено |
| `snapshots.slotRequired` | Kamida bitta vaqt kerak | Нужно хотя бы одно время |
| `snapshots.slotInvalid` | Vaqt noto'g'ri kiritilgan | Время указано неверно |
| `snapshots.rangeFill` | Oraliq bo'yicha to'ldirish | Заполнить по интервалу |
| `snapshots.rangeFrom` | Boshlanish vaqti | Время начала |
| `snapshots.rangeTo` | Tugash vaqti | Время окончания |
| `snapshots.rangeStep` | Qadam | Шаг |
| `snapshots.rangeStep15` | 15 daqiqa | 15 минут |
| `snapshots.rangeStep30` | 30 daqiqa | 30 минут |
| `snapshots.rangeStep60` | 1 soat | 1 час |
| `snapshots.rangeApply` | To'ldirish | Заполнить |
| **`snapshots.rangeTooMany`** | **Bu oraliq chegaradan oshib ketadi — hech nima qo'shilmadi.** | **Этот интервал превышает лимит — ничего не добавлено.** |
| `snapshots.rangeInvalid` | Tugash vaqti boshlanishdan keyin bo'lishi kerak | Время окончания должно быть позже начала |

### 11.4 Mavsumiy jadval (DL-2, DL-4)

| Kalit | uz-Latn | ru |
|-------|---------|-----|
| `snapshots.seasonalLegend` | Mavsumiy jadval | Сезонное расписание |
| `snapshots.scheduleName` | Nomi | Название |
| `snapshots.scheduleNameHint` | Masalan: Qishki, Ramazon | Например: Зимнее, Рамазан |
| `snapshots.startsOn` | Boshlanish sanasi | Дата начала |
| `snapshots.startsOnHint` | Eng erta — ertangi kun | Самое раннее — завтра |
| `snapshots.endsOn` | Tugash sanasi | Дата окончания |
| `snapshots.endsOnOptional` | Ixtiyoriy | Необязательно |
| `snapshots.previewOpen` | {from} dan boshlab — kuniga {count} marta. | С {from} — {count} раз в день. |
| **`snapshots.previewBounded`** | **{from} dan {to} gacha — kuniga {count} marta. Keyin «{next}» jadvali qaytadi.** | **С {from} по {to} — {count} раз в день. Затем вернётся расписание «{next}».** |
| `snapshots.startsOnTooSoon` | Boshlanish sanasi ertangi kundan erta bo'la olmaydi | Дата начала не может быть раньше завтрашнего дня |
| `snapshots.endsOnBeforeStart` | Tugash sanasi boshlanishdan keyin bo'lishi kerak | Дата окончания должна быть позже начала |
| `snapshots.deleteSchedule` | O'chirish | Удалить |
| `snapshots.deleteScheduleTitle` | Mavsumiy jadvalni o'chirish | Удалить сезонное расписание |
| **`snapshots.deleteScheduleBody`** | **«{name}» jadvali hali boshlanmagan, shuning uchun uni o'chirish mumkin. Olingan kadrlarga ta'sir qilmaydi.** | **Расписание «{name}» ещё не началось, поэтому его можно удалить. На снятые кадры это не влияет.** |
| `snapshots.deleteBlocked` | Boshlangan jadval o'chirilmaydi — u o'tmishdagi kadrlarni tushuntiradi | Начавшееся расписание не удаляется — оно объясняет прошлые кадры |
| `snapshots.toastScheduleSaved` | Jadval saqlandi | Расписание сохранено |
| `snapshots.toastSeasonalAdded` | Mavsumiy jadval qo'shildi | Сезонное расписание добавлено |
| `snapshots.toastSeasonalDeleted` | Mavsumiy jadval o'chirildi | Сезонное расписание удалено |

### 11.5 Kun tanlagichi va kunlik xulosa (zona C)

| Kalit | uz-Latn | ru |
|-------|---------|-----|
| `snapshots.day` | Kun | День |
| `snapshots.dayToday` | Bugun | Сегодня |
| `snapshots.dayPrev` | Oldingi kun | Предыдущий день |
| `snapshots.dayNext` | Keyingi kun | Следующий день |
| **`snapshots.noFutureDays`** | **Kelajakdagi kun tanlanmaydi — reja o'sha kunning ertalabida tuziladi** | **Будущий день выбрать нельзя — план составляется утром того же дня** |
| `snapshots.captured` | Olindi | Снято |
| `snapshots.capturedOf` | {done} / {planned} | {done} / {planned} |
| `snapshots.countOk` | yaroqli | годных |
| `snapshots.countDark` | qorong'i | тёмных |
| `snapshots.countBlank` | bo'sh | пустых |
| `snapshots.countCorrupt` | buzuq | повреждённых |
| `snapshots.countFailed` | xato | с ошибкой |
| `snapshots.countMissed` | olinmadi | не снято |
| **`snapshots.missedCallout`** | **{count} ta kadr umuman olinmadi.** | **Не снято кадров вовсе: {count}.** |
| `snapshots.showIssuesLink` | Muammolilarni ko'rsatish | Показать проблемные |
| `snapshots.showIssues` | Faqat muammolilarni ko'rsatish | Показать только проблемные |
| `snapshots.issuesHidden` | {count} ta qator yashirilgan | Скрыто строк: {count} |
| `snapshots.clearFilter` | Filtrni tozalash | Сбросить фильтр |
| `snapshots.archivedNote` | Arxivlangan kameralar hisobga kirmaydi | Архивные камеры не учитываются |

### 11.6 Hujayra holatlari va legenda (enum xaritasi)

| Kalit | uz-Latn | ru |
|-------|---------|-----|
| `snapshots.legend` | Belgilar | Обозначения |
| `snapshots.cell.ok` | Olindi | Снято |
| `snapshots.cell.dark` | Qorong'i | Тёмный |
| `snapshots.cell.blank` | Bo'sh | Пустой |
| `snapshots.cell.corrupt` | Buzuq | Повреждён |
| `snapshots.cell.failed` | Xato | Ошибка |
| **`snapshots.cell.missed`** | **Olinmadi** | **Не снято** |
| `snapshots.cell.pending` | Kutilmoqda | Ожидается |
| `snapshots.cell.running` | Olinmoqda | Снимается |
| `snapshots.cell.skipped` | Rejaga kirmagan | Вне плана |
| **`snapshots.cellLabel`** | **{time} · {camera} · {state}** | **{time} · {camera} · {state}** |
| `snapshots.gridCaption` | Kadr olish natijalari: kameralar va vaqtlar | Результаты съёмки: камеры и времена |
| `snapshots.gridRegion` | Kadr olish jadvali — gorizontal aylantiriladi | Таблица съёмки — прокручивается по горизонтали |
| `snapshots.camera` | Kamera | Камера |
| `snapshots.time` | Vaqt | Время |

### 11.7 Kadr detali — sifat, `light_mode` va ombor (DL-3)

**⛔ `quality_verdict` × `light_mode` — sakkizta juftlik, sakkizta jumla** (§6.6):

| Kalit | uz-Latn | ru |
|-------|---------|-----|
| `snapshots.verdict.okDay` | Kadr yaroqli — kunduzgi yorug'lik. | Кадр годный — дневной свет. |
| `snapshots.verdict.okLowLight` | Kadr yaroqli — kam yorug'lik. | Кадр годный — мало света. |
| `snapshots.verdict.okIrNight` | Kadr yaroqli — kamera tungi IR rejimida. | Кадр годный — камера в ночном режиме IR. |
| **`snapshots.verdict.darkIrNight`** | **Qorong'i kadr — kamera tungi rejimda edi. Bu normal holat.** | **Тёмный кадр — камера была в ночном режиме. Это нормально.** |
| `snapshots.verdict.darkLowLight` | Qorong'i kadr — yorug'lik kam edi. | Тёмный кадр — было мало света. |
| **`snapshots.verdict.darkDay`** | **Qorong'i kadr — kamera kunduzgi rejimda edi. Bu kutilmagan holat: linzani va yoritishni tekshiring.** | **Тёмный кадр — камера была в дневном режиме. Это неожиданно: проверьте объектив и освещение.** |
| `snapshots.verdict.blank` | Bo'sh kadr — tasvirda hech qanday ma'lumot yo'q. Kamera signalini tekshiring. | Пустой кадр — в изображении нет никакой информации. Проверьте сигнал камеры. |
| `snapshots.verdict.corrupt` | Kadr buzuq holda keldi — u to'liq yuklanmagan. | Кадр пришёл повреждённым — он загрузился не полностью. |

| Kalit | uz-Latn | ru |
|-------|---------|-----|
| `snapshots.notBillable` | Hisobga kirmaydi | Не идёт в расчёт |
| `snapshots.notBillableWhy` | Sifat tekshiruvidan o'tmagan kadr kunlik hisobga kirmaydi. | Кадр, не прошедший проверку качества, не идёт в дневной расчёт. |
| `snapshots.tierFull` | To'liq saqlangan | Хранится полностью |
| `snapshots.tierCompressed` | Siqilgan | Сжат |
| `snapshots.tierCompressedWhy` | 90 kundan oshgan kadrlar siqilgan holda saqlanadi | Кадры старше 90 дней хранятся сжатыми |
| `snapshots.lightMode.day` | Kunduzgi yorug'lik | Дневной свет |
| `snapshots.lightMode.lowLight` | Kam yorug'lik | Мало света |
| `snapshots.lightMode.irNight` | Tungi IR rejimi | Ночной режим IR |
| `snapshots.lightMode.unknown` | Aniqlanmadi | Не определено |
| `snapshots.method.stream` | Oqimdan | Из потока |
| `snapshots.method.device` | NVR qurilmasidan | С устройства NVR |
| `snapshots.method.fallback` | Zaxira yo'l bilan | Резервным способом |

> ⚠ **TUZATILDI (04-12).** Bu jadval avval `snapshots.method` ni IKKI ma'noda
> ishlatardi: yuqoridagi **enum xaritasi** (`method.stream`/`.device`/
> `.fallback`) va pastdagi **yorliq** («Usul»). JSON bitta kalitda satr va
> obyektni birga ushlay olmaydi, ya'ni spetsifikatsiya o'sha holida
> **bajarilmasdi** — buni `04-11` amalga oshirish paytida topdi va yorliqni
> `snapshots.methodLabel` ga ko'chirdi. Kod shu shaklda ishlaydi; jadval
> endi kodga MOS. Enum xaritasi ATAYIN ko'chirilmadi: uni ko'chirish uchala
> tildagi uch kalitni ham qayta nomlashni talab qilardi.
| `snapshots.capturedAt` | Olingan | Снято в |
| `snapshots.methodLabel` | Usul | Способ |
| `snapshots.size` | Hajmi | Размер |
| `snapshots.dimensions` | O'lchami | Разрешение |
| `snapshots.attempts` | Urinishlar | Попыток |
| `snapshots.qualityMean` | O'rtacha yorug'lik | Средняя яркость |
| `snapshots.qualityStddev` | Kontrast | Контраст |
| `snapshots.qualitySaturation` | To'yinganlik | Насыщенность |
| `snapshots.thresholdsVersion` | Chegaralar to'plami | Набор порогов |
| `snapshots.technicalDetails` | Texnik tafsilot | Технические подробности |
| `snapshots.imageUnavailable` | Rasm ochilmadi | Изображение не открылось |
| `snapshots.prevSlot` | Oldingi vaqt | Предыдущее время |
| `snapshots.nextSlot` | Keyingi vaqt | Следующее время |

### 11.8 ⛔ Xato kontrakti — har kod uchun SABAB, TUZATISH va KIM

| Kalit | uz-Latn | ru |
|-------|---------|-----|
| `snapshots.errorCauseLabel` | Sabab | Причина |
| `snapshots.errorFixLabel` | Nima qilish kerak | Что делать |
| `snapshots.actor.admin` | Bozor admini tuzatadi | Исправляет админ рынка |
| `snapshots.actor.platform` | Platforma jamoasi tuzatadi | Исправляет команда платформы |
| `snapshots.actor.none` | Harakat talab qilinmaydi | Действий не требуется |

**`capture_slot_missed`** — `danger`, actor `platform` · ⛔ **C6 ning matni**

| | uz-Latn | ru |
|---|---------|-----|
| `errorCause` | Tizim bu vaqtda ishlamadi, shuning uchun kadr umuman olinmagan. | В это время система не работала, поэтому кадр не был снят вовсе. |
| `errorFix` | Bu vaqt qaytarilmaydi — kechikkan kadr «o'sha payt rasta band edimi?» degan savolga javob bermaydi. Takrorlansa, platforma jamoasiga xabar bering. | Это время не вернуть — запоздалый кадр не отвечает на вопрос «было ли место занято тогда». Если повторится, сообщите команде платформы. |

**`capture_worker_lost`** — `danger`, actor `platform`

| | uz-Latn | ru |
|---|---------|-----|
| `errorCause` | Kadr olish boshlandi, lekin tugallanmadi — jarayon to'xtab qoldi. | Съёмка началась, но не завершилась — процесс остановился. |
| `errorFix` | Tizim keyingi urinishda o'zi qayta bajaradi. Takrorlansa, platforma jamoasiga xabar bering. | Система повторит попытку сама. Если повторится, сообщите команде платформы. |

**`capture_plan_created_late`** — `warning`, actor `none` · **C9 ning matni**

| | uz-Latn | ru |
|---|---------|-----|
| `errorCause` | Bu vaqt bozor tizimga ulangunicha o'tib ketgan edi. | Это время прошло ещё до подключения рынка к системе. |
| `errorFix` | Harakat talab qilinmaydi — ertadan boshlab barcha vaqtlar to'liq bajariladi. | Действий не требуется — со следующего дня все времена выполняются полностью. |

**`capture_source_unreachable`** — `danger`, actor `admin`

| | uz-Latn | ru |
|---|---------|-----|
| `errorCause` | Kamera manbasiga ulanib bo'lmadi. | Не удалось подключиться к источнику камеры. |
| `errorFix` | WireGuard tunneli yoqilganini va NVR qurilmasi tarmoqda ekanini tekshiring. Bozor tomonidagi qurilma rozetkada bo'lishi kerak. | Проверьте, что туннель WireGuard включён и NVR в сети. Устройство на стороне рынка должно быть включено в розетку. |

**`capture_camera_offline`** — `danger`, actor `admin`

| | uz-Latn | ru |
|---|---------|-----|
| `errorCause` | Kamera bu vaqtda ulanmagan edi. | Камера в это время была не в сети. |
| `errorFix` | Kamera quvvatini va kabelini tekshiring, so'ng kameralar bo'limida qayta skanerlang. | Проверьте питание камеры и кабель, затем выполните пересканирование в разделе камер. |

**`capture_bad_credentials`** — `danger`, actor `admin`

| | uz-Latn | ru |
|---|---------|-----|
| `errorCause` | NVR qurilmasi login yoki parolni qabul qilmadi. | NVR не принял логин или пароль. |
| `errorFix` | Kameralar bo'limida parolni yangilang. Diqqat: ketma-ket xato urinishlar NVR hisobini 30 daqiqaga qulflaydi — shuning uchun tizim o'zi qayta urinmaydi. | Обновите пароль в разделе камер. Внимание: неудачные попытки подряд блокируют учётную запись NVR на 30 минут — поэтому система не повторяет попытки сама. |

**`capture_stream_limit`** — `warning`, actor `admin` · **hedged (§11.11 Qoida 4)**

| | uz-Latn | ru |
|---|---------|-----|
| `errorCause` | **Ehtimol** NVR bir vaqtda ochiladigan oqimlar chegarasiga yetgan. Aniq sabab qurilma javobidan tasdiqlanmadi. | **Возможно,** достигнут предел одновременных потоков NVR. Точная причина по ответу устройства не подтверждена. |
| `errorFix` | Boshqa dasturlarda ochiq turgan oqimlarni yoping. Takrorlansa, quyidagi texnik tafsilotni yordam xizmatiga yuboring. | Закройте потоки, открытые в других программах. Если повторяется, отправьте технические подробности ниже в службу поддержки. |

**`capture_timeout`** — `danger`, actor `admin`

| | uz-Latn | ru |
|---|---------|-----|
| `errorCause` | Kamera javob bermadi — kutish vaqti tugadi. | Камера не ответила — время ожидания истекло. |
| `errorFix` | Tarmoq sekin bo'lishi mumkin. Takrorlansa, kameralar bo'limida ulanishni tekshiring. | Возможно, сеть медленная. Если повторяется, проверьте подключение в разделе камер. |

**`capture_invalid_response`** — `danger`, actor `admin`

| | uz-Latn | ru |
|---|---------|-----|
| `errorCause` | Kamera javobida tasvir yo'q edi. | В ответе камеры не было изображения. |
| `errorFix` | Kamera oqimini kameralar bo'limida jonli ko'rish bilan tekshiring. | Проверьте поток камеры прямым эфиром в разделе камер. |

**`capture_storage_unavailable`** — `danger`, actor `platform`

| | uz-Latn | ru |
|---|---------|-----|
| `errorCause` | Kadr olindi, lekin omborga yozilmadi. | Кадр был снят, но не записан в хранилище. |
| `errorFix` | Tizim keyingi urinishda kadrni qayta yozadi. Takrorlansa, platforma jamoasiga xabar bering. | Система перезапишет кадр при следующей попытке. Если повторится, сообщите команде платформы. |

**`capture_credential_unreadable`** — `danger`, actor `platform` · **hech qachon bostirilmaydi (D-22)**

| | uz-Latn | ru |
|---|---------|-----|
| `errorCause` | NVR paroli o'qib bo'lmadi — shifr kaliti mos kelmayapti. | Пароль NVR не удалось прочитать — ключ шифрования не подходит. |
| `errorFix` | Bu sozlama nosozligi va u o'zi tuzalmaydi. Platforma jamoasiga darhol xabar bering. | Это сбой конфигурации, и он сам не исправится. Немедленно сообщите команде платформы. |

### 11.9 Ogohlantirishlar (zona B)

| Kalit | uz-Latn | ru |
|-------|---------|-----|
| `snapshots.severity.info` | Ma'lumot | Информация |
| `snapshots.severity.warning` | Ogohlantirish | Предупреждение |
| `snapshots.severity.critical` | Jiddiy | Критично |
| `snapshots.alertKey.captureStopped` | Kadr olish to'xtadi | Съёмка кадров остановилась |
| `snapshots.alertKey.captureMissed` | Kadrlar o'tkazib yuborildi | Кадры пропущены |
| `snapshots.alertKey.cameraOffline` | Kamera uzoq vaqt javob bermayapti | Камера долго не отвечает |
| `snapshots.alertKey.backupStale` | Zaxira nusxa yangilanmadi | Резервная копия не обновлялась |
| `snapshots.alertKey.retentionStale` | Saqlash siyosati bajarilmadi | Политика хранения не выполнялась |
| `snapshots.alertKey.diskPressure` | Disk to'lib bormoqda | Диск заполняется |
| `snapshots.alertKey.credentialUnreadable` | NVR paroli o'qilmadi | Пароль NVR не читается |
| **`snapshots.alertKey.nvrAccountLocked`** | **NVR hisobi qulflandi** | **Учётная запись NVR заблокирована** |
| `snapshots.alertKey.captureRecovered` | Kadr olish tiklandi | Съёмка кадров восстановлена |
| `snapshots.alertOpenCount` | Ochiq: {count} | Открытых: {count} |
| `snapshots.alertFirstSeen` | Birinchi marta: {time} | Впервые: {time} |
| `snapshots.alertLastSeen` | Oxirgi marta: {time} | Последний раз: {time} |
| **`snapshots.alertRepeated`** | **So'nggi soatda yana {count} marta** | **За последний час ещё {count} раз** |
| `snapshots.alertNotified` | Telegram xabari yuborildi: {time} | Сообщение в Telegram отправлено: {time} |
| **`snapshots.alertNotNotified`** | **Telegram xabari yuborilmadi** | **Сообщение в Telegram не отправлено** |
| `snapshots.alertNotNotifiedWhy` | Telegram sozlanmagan yoki xabar yuborishda xato bo'lgan. | Telegram не настроен либо при отправке произошла ошибка. |
| `snapshots.showClosed` | Yopilganlarni ham ko'rsatish | Показать закрытые |
| `snapshots.alertResolvedAt` | Yopildi: {time} | Закрыто: {time} |
| `snapshots.alertDuration` | {duration} davom etdi | Длилось {duration} |
| `snapshots.alertCameraCount` | {count} ta kamera | Камер: {count} |

### 11.10 Bo'sh holatlar — to'rttasi

| Kalit | uz-Latn sarlavha / tavsif | ru sarlavha / tavsif |
|-------|---------------------------|----------------------|
| **`snapshots.emptyNoCameras`** | **Bu bozorda kamera yo'q** / Avval kameralar bo'limida NVR qurilmasini ulang — kadr olish undan keyin o'zi boshlanadi. | **На этом рынке нет камер** / Сначала подключите NVR в разделе камер — съёмка начнётся сама. |
| **`snapshots.emptyNoPlan`** | **Bu kunda kadr rejalashtirilmagan** / Jadval bu kunni qoplamaydi, shuning uchun kadr olinmagan. | **На этот день съёмка не планировалась** / Расписание не покрывает этот день, поэтому кадры не снимались. |
| `snapshots.emptyFiltered` | **Muammoli qator topilmadi** / Bu kunda barcha kadrlar yaroqli. | **Проблемных строк не найдено** / В этот день все кадры годные. |
| `snapshots.emptyClosedAlerts` | **Yopilgan ogohlantirish yo'q** / Yopilgan ogohlantirishlar shu yerda ko'rinadi. | **Закрытых оповещений нет** / Закрытые оповещения появятся здесь. |
| `snapshots.goToCameras` | Kameralar bo'limiga o'tish | Перейти в раздел камер |
| `snapshots.viewSchedule` | Jadvalni ko'rish | Посмотреть расписание |

### 11.11 ⛔ Transliteratsiya kontrakti — O'LCHANGAN defektlar va majburiy qoidalar

#### Qoida 1 — ⛔ RAQAM ARALASHGAN TOKEN override bilan TUZALMAYDI [O'LCHANDI: M-3]

Bu **yangi defekt sinfi** va u 3-fazadagi apostrof qoidasining jiyani: override **token**ni qidiradi, `S3` esa harf va raqam aralashmasi bo'lgani uchun boshqa token sifatida bo'linadi.

```
words["S3"] = "S3"  ->  "S3 omborida"  ->  "С3 омборида"   ❌ HAMON BUZUQ
words["SeaweedFS"]  ->  "SeaweedFS…"   ->  "SeaweedFS…"    ✅ sof harfli token TUZALADI
```

| ❌ Taqiqlangan | ✅ To'g'ri | Sabab |
|----------------|-----------|-------|
| `S3 omborida` | **`omborda`** / **`arxivda`** | Foydalanuvchi uchun ombor texnologiyasi ahamiyatsiz (§14.3) |
| `JPEG fayli` | **`kadr`** | Format nomi hech qanday aniqlik qo'shmaydi |
| `H.264 oqimi` | **`oqim`** | O'sha sabab |
| `IPv4 manzili` | **`manzil`** | O'sha sabab |

**Qoida:** `messages/*.json` ga **raqam bilan aralashgan lotin tokeni umuman kiritilmaydi**. Bunday qiymat kerak bo'lsa, u **API javobidan to'g'ridan-to'g'ri** chiziladi (`<details>` ichida, §10.7) — u yerda transliterator umuman ishlamaydi.

#### Qoida 2 — Sof harfli akronim va brend override TALAB QILADI [O'LCHANDI: M-2]

```
"Tungi IR rejimi"           -> "Тунги ИР режими"          ❌ override'siz
"Telegram xabari yuborildi" -> "Телеграм хабари юборилди" ⚠ o'qiladi, lekin brend qoidasiga zid
```

**W0-F2 da `uz-Cyrl.overrides.json -> words` ga qo'shiladigan IKKI yozuv:**

```json
"IR": "IR",
"Telegram": "Telegram"
```

`gen-cyrillic.test.mjs::allowed` regexi **shu ikki token bilan birga** yangilanadi — ikkisi **juft** yuritiladi [MEROS: 04-PATTERNS §S-14]. `JPEG`, `Sentry`, `S3`, `SeaweedFS`, `UTC` **qo'shilmaydi**, chunki ular Qoida 1/3 bo'yicha copy'ga umuman kirmaydi.

#### Qoida 3 — Kirill BIRLIKLARI to'g'ri, ularga tegilmaydi [O'LCHANDI: M-2]

```
"Ombor: 84 MB" -> "Омбор: 84 МБ"   ✅ to'g'ri
"1,2 GB"       -> "1,2 ГБ"         ✅ to'g'ri
```

`МБ` / `ГБ` — kirill yozuvining **standart** birlik qisqartmalari. Ularni override bilan lotinda qoldirish **xato** bo'lardi: bu akronim emas, **o'lchov birligi** va u qurilma interfeysi bilan solishtirilmaydi. Ya'ni 3-fazaning «akronim lotinda qoladi» qoidasi bu yerda **qo'llanmaydi** va farq shu yerda hujjatlashtiriladi.

#### Qoida 4 — ⛔ HEDGING DARVOZASINING KENGAYTIRILISHI (3-fazadagi G-3 bilan TO'QNASHUV)

3-faza G-3 darvozasi shunday yozilgan [MEROS: 03-UI-SPEC §12.4]:

> *«`errorCause.nvr_stream_limit` hedge so'zi bilan **boshlanadi**; boshqa hech bir `errorCause.*` da bu so'z **yo'q**.»*

4-faza `snapshots.errorCause.capture_stream_limit` ni **aynan o'sha hedge so'zi bilan** qo'shadi (§11.8) — sabab bir xil: chegaraga yetish **heuristika**, qurilma javobidan tasdiqlanmaydi [MEROS: 04-RESEARCH §B.4]. Ya'ni darvoza **hozirgi shaklida qizaradi**.

**Yechim (W0-F7):** G-3 ning ruxsat ro'yxati **ikki kalitga** kengaytiriladi va boshqa hech qayerda hedge so'zi bo'lmasligi sharti **saqlanadi**:

```
HEDGED_KEYS = {
  "cameras.errorCause.nvr_stream_limit",
  "snapshots.errorCause.capture_stream_limit",
}
```

⛔ **Hedging arzonlashsa, ma'nosini yo'qotadi.** 23 ta xato kodidan faqat **ikkitasi** hedged va ikkalasi ham bir xil fizik hodisani (NVR sessiya chegarasi) tasvirlaydi. Uchinchi kalit qo'shilsa, darvoza yana ko'rib chiqilishi shart.

#### Qoida 5 — 3-fazadan meros olingan taqiqlar KUCHDA

| ❌ Taqiqlangan | ✅ To'g'ri | Manba |
|----------------|-----------|-------|
| `NVR'ga`, `NVR'da`, `NVR'ning` | `NVR qurilmasiga`, `NVR sozlamalarida`, `NVR qurilmasining` | 03-UI-SPEC §11.7 Qoida 1 |
| `Asia/Tashkent` (IANA identifikatori) | `Toshkent` | 03-UI-SPEC §11.7 Qoida 2 |
| `ts` birikmali o'zlashma override'siz | Override majburiy (`ts` → `ц`) | 03-UI-SPEC §11.7 Qoida 2 |

4-fazaning copy'sida yuqoridagilarning birortasi **yo'q** [O'LCHANDI: M-1 — 85 satr; M-9 — §11 ning 70 shipping satri, 0 defekt].

#### Qoida 6 — ⛔ `ъ` NING IKKI MA'NOSI: darvoza uni SODDA tekshirmasin [O'LCHANDI: M-9]

M-9 o'lchovida ikkita satr «flagged» bo'lib chiqdi va **ikkalasi ham TO'G'RI**:

```
"…hech qanday ma'lumot yo'q…"      -> "…ҳеч қандай маълумот йўқ…"      ✅ TO'G'RI
"…Olingan kadrlarga ta'sir qilmaydi." -> "…Олинган кадрларга таъсир қилмайди." ✅ TO'G'RI
```

`ma'lumot` → `маълумот` va `ta'sir` → `таъсир` — bu **tutuq belgisi** va u o'zbek kirill imlosining to'g'ri shakli.

3-fazadagi defekt esa boshqa narsa edi: `NVR'ga` → `НВРъга` — u yerda apostrof **lotin akronimidan keyingi qo'shimcha ajratgichi** bo'lgan va `ъ` u yerda **ma'nosiz**.

| Shakl | Misol | Baho |
|-------|-------|------|
| Apostrof **o'zak ichida**, sof o'zbek so'zida | `ma'lumot`, `ta'sir`, `ma'no` | ✅ `ъ` **to'g'ri** |
| Apostrof **lotin akronimidan keyin** | `NVR'ga`, `NTP'ni`, `S3'da` | ❌ `ъ` **defekt** (3-faza Qoida 5) |

⚠ **G-6 ning tekshiruvi shuni ajratishi SHART.** «Chiqishda `ъ` bor → yiqil» degan sodda qoida `маълумот` va `таъсир` ni **yolg'on defekt** deb belgilardi va ijrochi uni «tuzatish» uchun to'g'ri o'zbek so'zini almashtirardi. To'g'ri shart:

```
DEFEKT := /[A-Za-z]ъ/         // ъ dan OLDIN lotin harfi
TO'G'RI := /[а-яёқғҳўъ]ъ/i    // ъ dan oldin kirill harfi — tutuq belgisi
```


#### Qoida 7 — mas'uliyat taqsimoti

| Fayl | Kim yozadi | 4-fazada |
|------|-----------|----------|
| `messages/uz-Latn.json` | **Qo'lda — manba** | ~145 yangi kalit |
| `messages/ru.json` | **Qo'lda** | ~145 yangi kalit (§11.1–§11.10 jadvallarida berilgan) |
| `messages/uz-Cyrl.json` | **Avtomatik** (`npm run i18n:gen`) | Qo'l tegizilmaydi |
| `messages/uz-Cyrl.overrides.json` | **Qo'lda** | **2** ta yangi so'z (Qoida 2) |

---

## 12. Qulaylik (a11y)

### 12.1 Umumiy talablar

| Talab | Kontrakt | Tekshiruv |
|-------|----------|-----------|
| **Kontrast — matn** | AA 4.5:1. 2-fazada tuzatilgan tokenlar; yangi juftlik **yo'q** (§9.1) | §9 |
| **Kontrast — boshqaruv elementi** | ≥3:1 → `border-border-ui` (3,64:1) barcha `Input`/`Select`/checkbox'da va **hujayra chegarasida** | WCAG 2.2 SC 1.4.11 |
| **Fokus ko'rinishi** | Global `:focus-visible` halqasi; matritsa hujayrasida `outline-offset: 2px` + `z-10` (sticky ustun ustidan ko'rinsin) | Klaviatura UAT |
| **Rang yagona signal emas** | §9.4 jadvali — har holatga ≥2 qo'shimcha kanal | Komponent testi |
| **Nishon o'lchami** | ≥44×44px: matritsa hujayrasi, kun tanlagichi tugmalari, vaqt chipining `×` tugmasi, checkbox yorlig'i | §7.2 |
| **Til atributi** | `<html lang>` locale bo'yicha; DB kontenti (kamera nomi, jadval nomi) `lang` bilan belgilanMAYDI [MEROS: 1-faza D-16] | — |
| **Harakat** | `prefers-reduced-motion`: `Skeleton` pulsi **va** `Loader2` aylanishi o'chadi. C8 hujayrasi harakatsiz holatda ham ikonka bilan farqlanadi | `skeleton.tsx` + `motion-reduce:animate-none` |
| **Matn kattalashtirish** | 200% zoomda layout buzilmaydi; matritsa gorizontal aylantiriladi, ma'lumot yo'qolmaydi (§7.3) | `maximum-scale` **qo'yilmaydi** |
| **Forma yorliqlari** | Har boshqaruv elementida `<label htmlFor>`; placeholder yorliq o'rnini **bosmaydi** | `Field` primitivi |
| **iOS avtomatik kattalashtirish** | 2-fazadagi `@media (pointer: coarse)` qoidasi kuchda — `<input type="time">` va `type="date"` undan foyda ko'radi | `globals.css` |

### 12.2 `fieldset` / `legend` — guruhlangan kiritmalar

**Ikkita mantiqiy guruh bor va ikkalasi ham `fieldset` oladi:**

```tsx
{/* DL-2 — mavsumiy jadval */}
<fieldset className="m-0 border-0 p-0">
  <legend className="mb-4 text-lg font-semibold">{t("snapshots.seasonalLegend")}</legend>
  <Field id="sched-name"  label={…} hint={…}>…</Field>
  <Field id="sched-start" label={…} hint={…}>…</Field>
  <Field id="sched-end"   label={…} hint={…}>…</Field>
</fieldset>

{/* Slot muharriri — DL-1 va DL-2 ning ichida */}
<fieldset className="m-0 border-0 p-0">
  <legend className="mb-2 text-sm font-semibold">{t("snapshots.times")}</legend>
  {/* chip ro'yxati + qo'shish + oraliq generatori */}
</fieldset>
```

| Qoida | Sabab |
|-------|-------|
| **Oraliq generatori — ichki `fieldset` EMAS** | Uch boshqaruv (`from`, `to`, `step`) + tugma bitta amalni tashkil qiladi va ular allaqachon «Vaqtlar» guruhi ichida. Ichma-ich `fieldset` skrinriderda ikki daraja e'lon qilardi va foyda bermasdi. Ular `<div role="group" aria-labelledby="range-label">` oladi |
| `<legend>` **`sr-only` EMAS** | U ko'rinadigan sarlavha [MEROS: 03-UI-SPEC §12.2] |
| `display: contents` **ISHLATILMAYDI** | Ba'zi brauzerlarda `<fieldset>` ning `display` ini o'zgartirish `<legend>` semantikasini buzadi |
| Kun tanlagichi **`fieldset` EMAS** | Uch mustaqil boshqaruv (ikki tugma + `<input type="date">`), umumiy yorliq bermaydi |
| Filtr checkbox'lari **`fieldset` EMAS** | Ikki mustaqil filtr, har biri o'z `<label>` iga ega |

### 12.3 `aria-disabled`, `disabled` EMAS

| Element | Qachon | Bosilganda |
|---------|--------|------------|
| «Keyingi kun» `▶` | Joriy kun bugun | So'rov yuborilmaydi; `role="status"` `snapshots.noFutureDays` ni e'lon qiladi |
| «Bugun» | Joriy kun allaqachon bugun | Hech nima; e'lon yo'q (holat allaqachon aniq) |
| «Vaqt qo'shish» | `used >= max` | `role="status"` `snapshots.slotLimitReached` ni e'lon qiladi |
| «Saqlash» (DL-1/DL-2) | `isPending` | So'rov yuborilmaydi; matn «Saqlanmoqda» ga o'zgaradi |

⛔ `disabled` **ishlatilmaydi**: fokus olmaydi va skrinrider uni umuman o'qimaydi — «nega bosilmayapti?» savoliga javob qolmaydi [MEROS: 02-UI-SPEC §6.6].

### 12.4 ⛔ Matritsa klaviaturasi — ARIA APG `grid` naqshi (kodbazada BIRINCHI marta)

175 hujayra × alohida tab to'xtashi = **klaviatura tuzog'i**. 3-fazada roving tabindex kerak emas edi (≤32 qator, qatorda 2 tugma) [MEROS: 03-UI-SPEC §6.1]; bu yerda u **majburiy**.

| Talab | Kontrakt |
|-------|----------|
| **Tab to'xtashlari** | Butun matritsa uchun **bitta**. Faol hujayra `tabIndex={0}`, qolgan 174 tasi `tabIndex={-1}` |
| **Boshlang'ich faol hujayra** | Birinchi qatorning birinchi hujayrasi; foydalanuvchi qaytganda **oxirgi faol hujayra** tiklanadi (komponent holati) |
| `ArrowRight` / `ArrowLeft` | Qator ichida keyingi/oldingi hujayra. Qator oxirida **to'xtaydi** (keyingi qatorga o'tmaydi) |
| `ArrowDown` / `ArrowUp` | Ustun ichida pastki/yuqori hujayra. Chetda **to'xtaydi** |
| `Home` / `End` | Qatorning birinchi / oxirgi hujayrasi |
| `Ctrl+Home` / `Ctrl+End` | Matritsaning birinchi / oxirgi hujayrasi |
| `Enter` / `Space` | DL-3 ni ochadi |
| `Esc` | DL-3 ni yopadi; fokus **o'sha hujayraga** qaytadi (Radix `Dialog` buni beradi) |
| Fokus ko'chganda aylantirish | `scrollIntoView({ block: "nearest", inline: "nearest" })` — sahifa **sakramaydi** |
| Semantika | `<table>` + `<caption class="sr-only">`; hujayralar `<td>` ichidagi `<button type="button">` |
| ⛔ **`role="grid"` QO'YILMAYDI** | Native `<table>` + `<th scope>` semantikasi skrinriderlarda **kuchliroq** (qator/ustun sarlavhasi avtomatik e'lon qilinadi). `role="grid"` bu semantikani almashtirardi va `aria-rowindex`/`aria-colindex` ni qo'lda yuritishni talab qilardi. Roving tabindex `role="grid"` **siz ham** ishlaydi |
| Hujayraning nomi | `aria-label={t("snapshots.cellLabel", {time, camera, state})}` — ikonka `aria-hidden="true"` |
| `title` | O'sha matn — sichqoncha foydalanuvchisi uchun |

### 12.5 Aylantiriladigan hudud

```tsx
<div role="region" aria-label={t("snapshots.gridRegion")} tabIndex={0}
     className="overflow-x-auto">
  <table>…</table>
</div>
```

`tabIndex={0}` **majburiy**: WCAG 2.1.1 bo'yicha gorizontal aylantiriladigan hudud klaviatura bilan ham aylantirilishi kerak. `role="region"` + `aria-label` esa uni skrinrider landmark'i qiladi.

⚠ Bu **ikkita** tab to'xtashi degani (hudud + matritsa). Bu qabul qilinadi va bu naqsh — WAI-ARIA APG ning o'z tavsiyasi.

### 12.6 Fokus tartibi va e'lonlar

| Vaziyat | Xulq |
|---------|------|
| Sahifa ochildi | Fokus tabiiy tartibda; `autoFocus` **qo'yilmaydi** |
| Kun almashtirildi | Fokus tugmada **qoladi**; xulosa `role="status"` orqali yangi sonlarni e'lon qiladi |
| Jurnal poll bilan yangilandi | ⛔ **Hech narsa e'lon qilinmaydi.** Har 30 soniyada 175 hujayrali jadvalni e'lon qilish skrinriderni yaroqsiz qilardi. Yangilanish jimgina bo'ladi; foydalanuvchi kun xulosasini o'zi o'qiydi |
| ⚠ Yangi `missed` paydo bo'ldi (poll orqali) | **Faqat kunlik xulosa** `role="status"` bilan yangilanadi («Olindi 173 / 175») — hujayra emas. Yagona istisno: `missed` soni **oshsa**, xulosaning `missedCallout` qatori qayta e'lon qilinadi |
| DL-3 ochildi | Radix: tuzoq, `Esc`, fokus **hujayraga** qaytadi |
| DL-1/DL-2 yuborildi, zod yiqildi | Fokus **birinchi noto'g'ri maydonga** (`setFocus`) |
| DL-1/DL-2 yuborildi, server xatosi | Fokus xato blokiga (`tabIndex={-1}`) — tuzatish yo'li o'sha yerda |
| Vaqt qo'shildi/olib tashlandi | `role="status"`: «{count} ta vaqt» — chiplar ro'yxati **o'zi** e'lon qilinmaydi |
| Tasdiq dialogi ochildi | Fokus **bekor qilishda** — hech qachon destruktiv tugmada |

**Jonli hududlar reyestri** (ikkitadan ortiq bir vaqtda faol bo'lmaydi):

| Hudud | Rol | Nima e'lon qiladi |
|-------|-----|-------------------|
| Kunlik xulosa | `role="status"` | Hisoblagichlar va `missedCallout` |
| D-05 farq izohi | `role="status"` | «…ertadan kuchga kiradi» |
| Slot muharriri holati | `role="status"` | Vaqtlar soni, chegara, dublikat xatosi |
| Zona/forma xatosi | `role="alert"` | Sabab + tuzatish |

⛔ **Zona B (ogohlantirishlar) `role="alert"` OLMAYDI** — u sahifa yuklanganda mavjud bo'lgan **holat**, yangi hodisa emas. `role="alert"` uni har sahifa yuklanishida qayta o'qitardi (§6.7).

---

## 13. Mobil va uch til

### 13.1 Navigatsiya sig'imi — o'lchangan [O'LCHANDI: M-7]

`NAV_ITEMS` 10 → **11**. `MOBILE_PRIMARY_COUNT = 4` [KOD: `app-shell.tsx:193`], ya'ni mobil panel = `4 + «Ko'proq»` = **5**.

| Rol | Ko'rinadigan yozuvlar | Mobil panel | Kontrakt (≤5) |
|-----|----------------------|-------------|----------------|
| `platform_admin` | 11 | 4 + «Ko'proq» = **5** | ✅ |
| `market_admin` | 10 | 4 + «Ko'proq» = **5** | ✅ |
| `director` | 6 | 4 + «Ko'proq» = **5** | ✅ |
| `cashier` | 1 | **1** | ✅ |
| `inspector` | 1 | **1** | ✅ |

**Kadr olish mobilda «Ko'proq» ostida qoladi** (`market` guruhida yettinchi). Bu **qabul qilinadi**: kadr olish jurnali — telefonda tez-tez ochiladigan ekran emas; u nomuvofiqlik tekshiruvida yoki ertalabki nazoratda ochiladi. Tartibni rolga qarab o'zgartirish `NAV_ITEMS` ni global konstanta bo'lishdan chiqarardi [MEROS: 03-UI-SPEC §3.3].

### 13.2 Mobil layout — zona bo'yicha

| Zona | ≥768px | <768px |
|------|--------|--------|
| **A** Jadval kartasi | Vaqtlar bir qatorda `flex-wrap` | Vaqtlar 2–3 qatorga tushadi; tugmalar **to'liq kenglikda ustma-ust** (`flex-col`) |
| **B** Ogohlantirish | Meta qatori bir satr | Meta qatori `flex-wrap`, 2–3 satr |
| **C** Kun tanlagichi | `[◀] [Bugun] [sana] [▶]` bir qatorda | O'sha, lekin `[Bugun]` matni saqlanadi (qisqartirilmaydi) |
| **C** Xulosa | Hisoblagichlar bir qatorda | `flex-wrap`, 2–3 qator. ⛔ **Hech biri yashirilmaydi** |
| **D** Legenda | 1–2 qator | 3–4 qator `flex-wrap`. ⛔ **Hech biri yashirilmaydi va `<details>` ga solinmaydi** |
| **D** Matritsa | To'liq sig'adi | **Gorizontal aylantirish** ≤60px (§7.3); sticky qator sarlavhasi kontekstni ushlaydi |
| **DL-1…DL-4** | `Dialog` markazda | `sheetOnMobile` — pastdan chiqadigan varaq |

⛔ **Mobilda matritsa boshqa komponentga ALMASHMAYDI** [QAROR]. «Mobilda kartalar ro'yxati» varianti rad etildi: u DOM tuzilishini breakpoint bilan o'zgartirardi, ya'ni bir xil ma'lumot ikki xil semantikaga ega bo'lardi va klaviatura naqshi (§12.4) ikki marta yozilardi. Gorizontal aylantirish — arzonroq va u WCAG 1.4.10 ni buzmaydi, chunki **barcha sonlar xulosada matn sifatida** takrorlangan (§7.3).

### 13.3 Rus tilining uzunligi — o'lchangan [O'LCHANDI: M-4]

O'rtacha nisbat **0,99×** — ya'ni bu to'plamda rus tili uzunroq **emas**. Lekin taqsimot keng:

| Kalit | uz-Latn | ru | Nisbat |
|-------|---------|-----|--------|
| `snapshots.cell.corrupt` | Buzuq (5) | Повреждён (9) | **1,80×** |
| `snapshots.cell.failed` | Xato (4) | Ошибка (6) | 1,50× |
| `snapshots.logTitle` | Ijro jurnali (12) | Журнал выполнения (17) | 1,42× |
| `nav.snapshots` | Kadr olish (10) | Съёмка кадров (13) | 1,30× |
| `snapshots.cell.skipped` | Rejaga kirmagan (15) | Вне плана (9) | 0,60× |
| `snapshots.alertsTitle` | Ogohlantirishlar (16) | Оповещения (10) | 0,63× |

**Oqibatlari:**

1. ⛔ **`cell.corrupt` ning 1,80× nisbati matnni 44px hujayraga sig'dirishni imkonsiz qiladi** → §6.4 dagi «hujayrada matn YO'Q» qarorining o'lchangan asosi. Bu qaror rus tilisiz olinganda ham to'g'ri bo'lardi, lekin o'lchov uni **muzokarasiz** qiladi.
2. **Legenda `flex-wrap`** — rus tilida u bir qator ko'proq egallaydi va bu normal.
3. `nav.snapshots` mobil panelda **«Ko'proq» ostida**, ya'ni 13 belgi hech qanday siqilishga uchramaydi.

**Kontrakt o'zgarishsiz** [MEROS: 02-UI-SPEC §5.1]: qat'iy kenglik **yo'q**; tugma `whitespace-nowrap` + tabiiy kenglik; qator `flex-wrap`; badge **`truncate` QILINMAYDI** (u ma'no tashiydi) — konteyner o'sadi; faqat **DB kontenti** (kamera nomi, jadval nomi) `truncate` + `title`.

**4-fazaga xos xavf:** matritsaning qator sarlavhasida kanal raqami + kamera nomi 112px'ga sig'ishi kerak. Kamera nomi — **DB kontenti**, ya'ni u tarjima qilinmaydi va uzunligi ma'lum emas. Kontrakt: nom `truncate` + `title`, kanal raqami **hech qachon kesilmaydi** (u identifikator).

### 13.4 Sana va vaqt formatlari

| Qiymat | Format | Manba |
|--------|--------|-------|
| Slot vaqti (`06:30`) | `HH:mm`, **24 soatlik**, uchala tilda bir xil | `font-mono`; `next-intl` **ishlatilmaydi** — bu jadval qiymati, mahalliylashtirilgan vaqt emas |
| Biznes-kun sarlavhada | `next-intl` `dateTime` + hafta kuni | `Asia/Tashkent` |
| `captured_at` (DL-3) | `HH:mm:ss` | Forenzika uchun soniya **majburiy** |
| Nisbiy vaqt («3 daqiqa oldin») | `date-fns` + locale | Ogohlantirish `last_seen_at` |
| `?day=` URL parametri | `YYYY-MM-DD` (ISO) | ⛔ **Hech qachon mahalliylashtirilmaydi** — u ulashiladigan havolaning bir qismi |

⚠ **Toshkent UTC+5, yozgi vaqt YO'Q** [MEROS: 04-RESEARCH §A.1]. UI'da DST bilan bog'liq hech qanday himoya, ogohlantirish yoki mintaqa tanlagichi **qurilmaydi**.

---

## 14. Registry xavfsizligi

### 14.1 shadcn va uchinchi tomon registrlari

| Registry | Ishlatilgan bloklar | Safety Gate |
|----------|---------------------|-------------|
| shadcn (rasmiy) | — | **Qo'llanmaydi** — `components.json` yo'q, `shadcn init` bajarilmadi (§3.3) [O'LCHANDI: M-6] |
| Uchinchi tomon registrlari | **YO'Q** | **Qo'llanmaydi** — birorta uchinchi tomon registri e'lon qilinmadi |

**`npx shadcn add` bu fazada ishlatilmaydi.** Barcha komponentlar mavjud bog'liqliklar ustida qo'lda yoziladi va kod-ko'rikdan o'tadi.

### 14.2 Vendored artefakt — YO'Q

3-fazada `public/vendor/go2rtc/` bilan birinchi uchinchi tomon fayli bundlga kirgan edi va unga SHA-256 darvozasi qo'yilgan (G-7). **4-faza yangi vendored fayl QO'SHMAYDI** va mavjudlariga **tegmaydi** — ularning yaxlitlik darvozasi o'z joyida ishlashda davom etadi.

**Yangi npm paketi ham qo'shilmaydi** (§3.4).

### 14.3 ⛔ Ombor yuzasi — brauzerga HECH QACHON ochilmaydi [QAROR]

Bu 4-fazaning **o'z** xavfsizlik darvozasi va u 3-fazadagi go2rtc qoidasining aynan takrori [MEROS: 03-UI-SPEC §8.7].

| Narsa | Qoida |
|-------|-------|
| SeaweedFS / S3 endpointi | **Foydalanuvchiga hech qachon** — na to'g'ridan-to'g'ri, na proxy orqali. Frontend bu manzilga **hech qanday** so'rov yubormaydi |
| Presigned URL | ⛔ **Berilmaydi va so'ralmaydi.** Kadr **core-api orqali proxy** qilinadi: `GET /api/v1/snapshots/{id}/image` (§6.6 [TALAB]) |
| `object_key` | UI'da **ko'rsatilmaydi**, nusxa olinmaydi, `<details>` ga ham chiqmaydi |
| Bucket nomi, region, access key | **Hech qanday ko'rinishda** |
| Kadr havolasini ulashish | Ulashish tugmasi **yo'q**; DL-3 URL'da emas (§4.4) |
| Kadr rasmi ogohlantirishda | ⛔ **D-19 — hech qachon** (§6.7) |

**Nima uchun presigned URL rad etildi** (u «arzonroq» ko'rinadi):

1. **Auditni buzadi.** Presigned URL bir marta berilgach, u muddati tugagunicha **audit yozuvisiz** ishlaydi. Kadr — shaxsiy ma'lumot va uning o'qilishi `audit_read` ga tushishi kerak (2-faza D-09).
2. **RLS'ni chetlab o'tadi.** URL sessiyadan mustaqil bo'lib qoladi: rol o'zgarsa, foydalanuvchi bloklansa yoki bozor almashsa ham havola ishlayveradi.
3. **Ombor manzilini oshkor qiladi.** Brauzer tarixida, `Referer` da va nusxalangan havolada ichki xizmat manzili paydo bo'lardi.
4. **Data-rezidentlik.** Ombor manzili tashqariga chiqmasa, uni O'zbekiston hostingiga ko'chirish **sozlama o'zgarishi** bo'lib qoladi — CLAUDE.md ning aniq talabi.

Frontend'da **grep darvozasi** (G-4): `frontend/src` da `presign`, `X-Amz`, `s3.`, `seaweed`, `:8333` satrlari **bo'lmasligi** shart.

---

## 15. Darvozalar (G-N)

Bu fazaning qoidalari **taxminga emas, testga** bog'lanadi.

| # | Darvoza | Fayl | Nimani tekshiradi | Nima uchun mavjud |
|---|---------|------|-------------------|-------------------|
| **G-1** | **«slot» so'zi taqig'i** | `scripts/snapshot-copy.test.mjs` (yangi) | Uchala `messages/*.json` ning `snapshots.*` kalitlarida `slot` / `слот` **yo'q** | §10.2 — orkestratsiya atamasi mahsulot tiliga sizib kirmasin |
| **G-2** | **Jurnalda rasm taqig'i** | `scripts/snapshot-copy.test.mjs` | `components/snapshots/capture-grid.tsx` va `capture-cell.tsx` da `<img`, `next/image`, `background-image` **yo'q** | §6.6 — 175 ta thumbnail tarmoqni ham, shaxsiy ma'lumot yuzasini ham portlatardi |
| **G-3** | ⛔ **Ogohlantirishda rasm taqig'i (D-19)** | `scripts/snapshot-copy.test.mjs` | `components/snapshots/alert-list.tsx` va `alert-row.tsx` da `<img`, `next/image`, `/image` satri **yo'q** | **D-19 ning mexanik shakli.** Kadr — tashrifchining shaxsiy ma'lumoti; Telegram data-rezidentlik chegarasidan tashqarida |
| **G-4** | ⛔ **Ombor yuzasi taqig'i** | `scripts/snapshot-copy.test.mjs` | `frontend/src` da `presign`, `X-Amz`, `seaweed`, `:8333` **yo'q** | §14.3 — audit, RLS va data-rezidentlik uchalasi shu bitta chiziqqa tayanadi |
| **G-5** | **Sabab↔tuzatish↔`actor` parity** | `scripts/error-codes.test.mjs` (kengaytiriladi) | Har `snapshots.errorCause.{code}` uchun `snapshots.errorFix.{code}` **va** `capture-errors.ts` da `actor` **uchala tilda** mavjud | 3-fazadagi G-1 ning davomi + `actor` ustuni (§10.5) |
| **G-6** | **Transliterator regressiyasi** | `scripts/gen-cyrillic.test.mjs` (kengaytiriladi) | 5 ta holat: `IR` va `Telegram` **lotin** qoladi; `ъ` tekshiruvi tutuq belgisini defektdan ajratadi (Qoida 6); `MB` → `МБ`; ⛔ `messages/*.json` da raqam aralashgan lotin tokeni (`/[A-Za-z]+[0-9]/`) **umuman yo'q** | §11.11 Qoida 1–3. Oxirgi shart — **M-3 ning mexanik shakli**: u override bilan tuzalmaydigan defektni **kirishida** to'sadi |
| **G-7** | ⛔ **ABSENT bo'sh emas** | `capture-cell.test.tsx` | `missed` hujayrada: ikonka render bo'ladi, `aria-label` `cell.missed` matnini o'z ichiga oladi, `class` da `border-dashed` bor va hujayra `min-h-11 min-w-11` | **SC#2 ning mexanik shakli.** «Jurnalda ochiq ko'rinadi» talabi shu yerda testga aylanadi |
| **G-8** | **Nol hisoblagichlar** | `day-summary.test.tsx` | `{ok:0, dark:0, blank:0, corrupt:0, failed:0, missed:0}` bilan **oltala** `<dt>`/`<dd>` juftligi render bo'ladi | §6.3 — 3-fazadagi «uch hisoblagich» qoidasining takrori |
| **G-9** | **RBAC ko'zgusi** | Mavjud `scripts/role-gate.test.mjs` | `lib/rbac.ts` va `rbac.py` matritsalari mos; 4-faza yangi `Permission` **qo'shmagan** | W0-F6 — 04-PATTERNS §3.9 |
| **G-10** | **Kadrni o'chirish taqig'i** | `scripts/snapshot-copy.test.mjs` | `snapshots.*` kalitlarida `kadrni o'chir`, `kadrlarni o'chir`, `удалить кадр`, `удалить снимок` **yo'q** | §10.2 — 04-RESEARCH §D.10: kadr **hech qachon o'chirilmaydi**, faqat siqiladi |

> **G-1 va G-10 nima uchun mexanik:** ikkalasi ham **so'z** taqig'i, ya'ni ular kod-ko'rikda **eng oson o'tkazib yuboriladigan** sinf. 2-fazada `Excel'dan`, 3-fazada `o'chirish` aynan shunday sizib kirgan va ikkalasi ham darvoza bilan yopilgan. Bu fazada darvoza **avvaldan** qo'yiladi.
>
> ⚠ **G-6 ning oxirgi sharti butun `messages/*.json` ga qo'llanadi**, faqat `snapshots.*` ga emas. Sabab: M-3 defekti loyihaning har qanday kalitida takrorlanishi mumkin va uni faqat 4-faza uchun to'sish keyingi fazada aynan shu xatoni qaytarardi.

---

## 16. Bu fazada BO'LMAYDIGAN UI

[MEROS: 04-CONTEXT `<domain>` + `<deferred>` + 04-RESEARCH Scope Fence]

### 16.1 Keyingi fazalarga qoldiriladigan

| Imkoniyat | Faza | 4-fazada aynan nima qilinadi | Nima QILINMAYDI |
|-----------|------|-------------------------------|------------------|
| **Kamera zonalari, poligon muharriri** | 5 | Hech narsa | Canvas, `react-konva`, zona chizish |
| **Band/bo'sh qarori, CV natijasi** | 5 | ⛔ **Faqat `is_billable` ilgagi** — yaroqsiz kadr «hisobga kirmaydi» deb belgilanadi | Bandlik ko'rsatkichi, confidence, noaniq navbati |
| **Nazoratchi tasdig'i, HITL navbati** | 5 | Hech narsa | Tasdiqlash tugmalari, ko'r audit |
| **Kadrdan pul hisoblash, dalil-hisob bog'lanishi** | 6 | Hech narsa | Kadr detalida «bu kadr qaysi pattaga tegishli» qatori |
| **«Band, lekin to'lovsiz» case oqimi** | 7 | Hech narsa | Nomuvofiqlik ro'yxati |
| **Telegram dayjesti va uning sozlamalari** | ops / 7 | Backend yuboradi; UI **faqat `notified_at` ni ko'rsatadi** | Dayjest matni, chat tanlash, jo'natish jadvali ekrani |
| **Aniqlik hisoboti `light_mode` kesimida** | 8 | `light_mode` **saqlanadi va ko'rsatiladi** | Kesim bo'yicha hisobot, diagramma |
| **`.xlsx` eksporti** | 8 | Hech narsa | Yuklab olish tugmasi |

### 16.2 Ataylab qurilMAYDIGAN — sabab bilan

| Nima | Nima uchun qurilmaydi |
|------|------------------------|
| **Har kamera uchun alohida jadval** | CAM-04 buni so'ramaydi. D-04 vazifa birligini **NVR + slot** qilib qulflagan; kamera bo'yicha jadval konfiguratsiya yuzasini 25 barobar oshirib, hech qanday mahsulot savoliga javob bermasdi |
| **`capture_on_closed_days` ni UI'dan yoqish/o'chirish** | D-10 uni `true` qilib qulflagan va u `market_profile` ning maydoni (2-faza egaligida). Bitta checkbox uchun boshqa fazaning sozlamalar yuzasini ochish — noto'g'ri egalik. Zona A da **o'qish uchun** qatori bor (§4.3) |
| **`max_concurrent_captures`, `grace_seconds`, sifat chegaralari sozlamasi** | Ular `Settings` da (D-08, D-15) va **pilotda SQL bilan sozlanadi**. Admin uchun ma'nosi yo'q sonlarni ekranga chiqarish — yolg'on nazorat tuyg'usi |
| **Kadrni qo'lda qayta olish tugmasi («hozir kadr ol»)** | Slot vaqti — **biznes identifikatori** (`business_date` + `slot_time`). Qo'lda olingan kadr qaysi slotga tegishli bo'lardi? Javob yo'q. `grace` oynasidan tashqarida olingan kadr «o'sha payt rasta band edimi?» savoliga javob **bermaydi** [MEROS: 04-RESEARCH §A.2] — ya'ni tugma foydali emas, **zararli** bo'lardi |
| **Kadrni o'chirish** | 04-RESEARCH §D.10: qator **hech qachon o'chirilmaydi**. G-10 darvozasi |
| **Ombor brauzeri / fayl daraxti** | §14.3. Kadr faqat o'z kontekstida (kamera + vaqt) ko'riladi, fayl sifatida emas |
| **Ogohlantirishni qo'lda yopish/bostirish** | §6.7 — admin muammoni ko'rmasdan yashira olmasligi kerak. Ogohlantirishni faqat **tiklanish** yopadi |
| **Jurnalda thumbnail** | G-2. 175 rasm + shaxsiy ma'lumot yuzasi + tarmoq |
| **Kunlik xulosa diagrammasi** | `recharts` bog'liqlik emas (§3.4) va olti son diagramma talab qilmaydi |
| **Kadrlarni taqqoslash (oldingi kun bilan yonma-yon)** | 5-fazadagi zona qarori bu ehtiyojni yopadi; hozir u faqat qiziqarli, foydali emas |
| **Bir necha kunni bir ekranda (haftalik ko'rinish)** | Kunlik javob — mahsulotning javob birligi. Haftalik agregat 8-fazaning hisoboti |
| **Kadr yuklab olish tugmasi** | Shaxsiy ma'lumotni sessiyadan tashqariga chiqarish. 6/7-fazadagi dalil oqimi bu ehtiyojni **audit bilan** yopadi |
| **`/internal/self-check` holatini UI'da ko'rsatish** | U **tashqi kuzatuvchi** uchun (04-RESEARCH §E.12). Admin uchun uning aksi — zona B ning o'zi |

### 16.3 Erta optimizatsiya deb baholangan «ilgaklar»

Ro'yxat virtualizatsiyasi (175 hujayra — DOM uchun arzon), umumiy `<DataMatrix>` abstraktsiyasi (bitta iste'molchi; ikkinchisi kelganda ajratiladi), jurnalning offline keshi, dark mode tokenlari, Storybook, kadr rasmini oldindan yuklash (prefetch), matritsa hujayrasining hover-preview'i.

### 16.4 Ochiq qoldirilgan savollar — har biri uchun ishlaydigan standart bor

Bu subagent kontekstida foydalanuvchiga savol berish vositasi yo'q. Quyidagilar **taxmin qilinib jimgina qulflanmadi**; har biri uchun standart tanlangan, ya'ni rejalashtirish javob kutib **to'xtamaydi**.

| # | Savol | Bilamiz | Noaniq | Tanlangan standart |
|---|-------|---------|--------|--------------------|
| **O-01** | `MAX_TIMES_PER_DAY = 12` Karmana uchun yetarlimi? | 12 × 25 kamera = 300 kadr/kun ≈ 6,5 GB/yil; standart profil **7** ta vaqt ishlatadi | Buyurtmachi «har soatda» so'rashi mumkin (06:00–18:00 = 13) | **12**. Qiymat `Settings` da — o'zgartirish **bitta qator**. Pilotda o'lchansin |
| **O-02** | Ijro jurnali direktорga kerakmi yoki faqat adminga? | `camera_view` direktorda **bor** [KOD: `rbac.ts`] | Direktor kunlik kadr jurnalini ochadimi | **Beriladi** (`camera_view`). Yangi huquq **qo'shilmaydi** — 04-PATTERNS §3.9 |
| **O-03** | `capture_method` ning inson tilidagi yorliqlari to'g'rimi? | «Oqimdan» / «NVR qurilmasidan» / «Zaxira yo'l bilan» (§10.7) | Ona tilida so'zlashuvchi ko'rigi bo'lmadi | Shu shakl; 8-fazadagi «uch tilli interfeys yakuniy tekshiruvi» mezoniga kiritilsin |
| **O-04** | Gorizontal aylantirish 360px'da qabul qilinarlimi? | 7 vaqt → 60px aylantirish; 5 vaqt → sig'adi (§7.3) | Dala foydalanuvchisi buni sezadimi | Aylantirish **qoladi**; barcha sonlar xulosada matn sifatida takrorlangan, ya'ni ma'lumot yo'qolmaydi. UAT'da o'lchansin |
| **O-05** | «Ogohlantirish» (`alert`) atamasi ru'da `Оповещение` to'g'rimi? | §11.9 da taklif qilindi | `Оповещение` / `Уведомление` / `Тревога` orasida tanlov | **`Оповещение`**. 8-fazadagi til ko'rigiga kiritilsin (2-fazadagi O-07 va 3-fazadagi O-05 bilan bir yo'lda) |
| **O-06** | Kadr rasmini ko'rish `audit_read` yozadimi — backend buni beradimi? | 2-faza D-09 naqshi mavjud (`stalls.py:304-345`) | 4-faza API'si hali yozilmagan | Talab **saqlanadi** (§6.6 [TALAB]). Zaxira: rasm endpointi `audit_read` siz chiqsa, u **G-4 ni buzmaydi**, lekin 8-fazadagi shaxsiy ma'lumot ko'rigida bo'shliq sifatida qayd etiladi |

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

*Phase: 04-snapshot-pipeline*
*UI-SPEC yakunlandi: 2026-08-04 — `gsd-ui-researcher`*
*Upstream: 04-CONTEXT.md (D-01…D-23), 04-RESEARCH.md (§A, §B, §C, §D, §E), 04-PATTERNS.md (§S-14, §1.7, §3.9, §3.12, §5), 03-UI-SPEC.md (dizayn tizimi, i18n, a11y kontrakti), ROADMAP Phase 4 (SC#1–SC#5), CLAUDE.md*
