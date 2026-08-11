---
phase: 06-billing-va-kassir
status: approved
created: 2026-08-10
reviewed_at: 2026-08-10
review_verdict: APPROVED — 6/6 o'lchov PASS, 4 ta bloklamaydigan FLAG (gsd-ui-checker)
open_flags:
  - "§8.8 to'lov turi ikonkasiga aria-label / ko'rinadigan matn qo'shilsin (WCAG 1.4.1 — hujjatdagi yagona juftlanmagan ikonka)"
  - "§11.5 «Smenasiz to'lovlar» agregatiga maydon NOMI berilsin (ehtimol GET /shifts?day= ga shiftless_payment_count + shiftless_payment_soum)"
  - "§8.2/G-20: noaniq ko'p-moslikdagi rasta qidiruvi 1-qadam ichida «ikkinchi o'zaro ta'sir» — u steps === 3 invariantida QANDAY sanaladi, collect-session.test.tsx yozilishidan OLDIN qaror qilinsin"
  - "§11.2 jadvalida [TALAB] tegi to'rtala qatorda bir xil bo'lsin (kosmetik)"
not_verified:
  - "M-5 transliteratsiya da'vosi (67 satr × gen-cyrillic.mjs) tekshiruvchi tomonidan QAYTA yugurtirilmadi — hech qaysi o'lchov uchun yuk ko'taruvchi emas"
design_system: shadcn-pattern (manual, CVA + Radix — Phase 1/2 tokenlari)
response_language: uz-Latn
inherits: .planning/phases/05-kamera-zonalari-cv-va-nazoratchi-tasdig-i/05-UI-SPEC.md
---

# Phase 6 — Billing va kassir: UI dizayn kontrakti

> Bitta va'daning vizual kontrakti: **odam pul to'ladi — va buni isbotlab beradigan yozuv bor.**
> 5-fazaning UI'si «xolislikni buzib bo'lmaydigan qilish» edi. Bu fazaniki — **pulni yo'qotib bo'lmaydigan qilish**. Farq shundaki, bu yerda UI xatosi *raqamda* emas, **nizoda** ko'rinadi: sotuvchi to'laganini isbotlay olmaydi, kassir kamomadni tushuntira olmaydi, direktor kimga ishonishni bilmaydi. Bitta noto'g'ri joylashtirilgan maydon — va «kutilayotgan patta» kvitansiya bo'lib o'qiladi.
> Yaratdi: `gsd-ui-researcher`. Tekshiradi: `gsd-ui-checker`. Iste'mol qiladi: `gsd-planner`, `gsd-executor`.

---

## 0. Dalil holati va shu sessiyada bajarilgan o'lchovlar

Belgilar 3, 4 va 5-fazadagi bilan bir xil [MEROS: 05-UI-SPEC §0]:

| Belgi | Ma'nosi |
|-------|---------|
| **[O'LCHANDI]** | Shu sessiyada kodbazada yoki skript bilan o'lchandi — natija keltirilgan |
| **[KOD]** | Kodbazadan o'qildi — aniq `fayl:qator` keltirilgan |
| **[MEROS]** | Upstream artefaktdan (06-CONTEXT, 06-RESEARCH, 05-UI-SPEC, 02-UI-SPEC, ROADMAP, CLAUDE.md) |
| **[QAROR]** | Shu hujjatda qabul qilindi — sabab yozilgan, muqobil rad etilgan |
| **[TALAB]** | UI backend'dan talab qiladigan narsa — rejaga bevosita kiradi |

### 0.1 O'lchovlar

| # | O'lchov | Natija |
|---|---------|--------|
| **M-1** | **shadcn darvozasi** — `find . -maxdepth 3 -name components.json` | **0 natija** → `Tool: none` (§3.4). 2, 3, 4 va 5-faza qarori davom etadi |
| **M-2** | **`ui/` primitivlari** — `ls frontend/src/components/ui/` | **10 primitiv** (`badge, button, card, confirm-dialog, dialog, empty-state, field, input, select, skeleton`). 6-fazada **yangi `ui/` primitivi qurilmaydi** (§3.2) |
| **M-3** | **Ikonka mavjudligi** — `node -e "require('lucide-react')"` bilan **61 ta** 6-faza nomzod nomi | **0 ta yetishmayapti.** `lucide-react@1.27.0`: `Banknote, BanknoteArrowUp, CreditCard, Coins, Wallet, HandCoins, Receipt, ReceiptText, Calculator, Hash, Undo2, RotateCcw, ScrollText, ClipboardList, LogIn, LogOut, DoorOpen, DoorClosed, Scale, Sigma, Landmark, PiggyBank, ArrowLeftRight, TrendingUp, TrendingDown, Equal, UserX, Store, Ban, ShieldAlert, Delete, Smartphone, …` |
| **M-4** | ⛔⛔ **`G-18(b)` darvozasi UI-SPEC FAYLLARINI O'QIYDI** — `bulk-action-surface.test.mjs:79-125` | `findSpecsDeclaringG18()` `.planning/phases/*/*-UI-SPEC.md` ni skanerlaydi va `assert.equal(SPEC_FILES.length, 1)` qiladi. O'lchandi: `05-UI-SPEC.md` da AYNAN **1** ta `^\|\s*\*\*G-18\*\*\s*\|` qatori bor; undan o'qilgan naqshlar — `["components/review/**","components/blind-audit/**"]`. ⛔ **Oqibat: BU FAYL `\| **G-18** \|` bilan boshlanadigan qator YOZMAYDI** — yozsa, darvoza «birdan ko'p e'lon» deb **butun `npm run gate` ni qizartirardi**. Kengaytirish yo'li §15.4 da |
| **M-5** | **Transliterator sinovi** — 67 ta 6-faza nomzod satri `gen-cyrillic.mjs::transliterate()` dan **mavjud** override lug'ati bilan o'tkazildi | **0 ta mexanik defekt.** Lotin qoldig'i 0; akronim defekti (`/[A-ZА-ЯЁҚҒҲЎ]{2,}ъ/u`) 0; raqam-aralash lotin token 0. Namuna: `Kutilayotgan patta`→`Кутилаётган патта`, `Naqd`→`Нақд`, `Kamomad`→`Камомад`, `Ortiqcha`→`Ортиқча`, `Ro'yxatga olinmagan savdo`→`Рўйхатга олинмаган савдо`. Ya'ni 6-faza `uz-Cyrl.overrides.json` ga **birorta yozuv qo'shmaydi**. ⚠ Bu o'lchov **nomzod** satrlar ustida — yakuniy copy §13 dan olinadi va uni `npm --prefix frontend run i18n:gen` **generatsiya qiladi**; qo'lda tuzatish zarurati chiqsa, u §13.9 qoidasi bo'yicha hal qilinadi |
| **M-6** | **Navigatsiya sig'imi** — `NAV_ITEMS` + `ROLE_PERMISSIONS` matritsasi skript bilan hisoblandi [KOD: `app-shell.tsx:97-283`, `rbac.ts:55-113`] | Hozir **13 element**: `platform_admin` 11 · `director` 11 · `market_admin` 11 · ⛔ **`cashier` 1** · `inspector` 2. 6-fazadan keyin (**15 element**, `/collect` + `/billing`): `platform_admin` 11 (**o'zgarmaydi**) · `director` **12** · `market_admin` **12** · ⛔ **`cashier` 1→2** · `inspector` 2. `MOBILE_PRIMARY_COUNT = 4` [KOD: `app-shell.tsx:283`] → kassirning mobil paneli **`/dashboard` + `/collect`**, overflow **0**. **Kontrakt saqlanadi** |
| **M-7** | ⛔ **RBAC — kassirda O'QISH huquqi UMUMAN YO'Q** [KOD: `rbac.ts:112`] | `cashier: ["payment_create"]` — boshqa hech nima. Ya'ni bugun kassir rasta ro'yxatini ham, proyeksiyani ham, smenani ham **403** oladi. 6-faza **ikkita yangi huquq** qo'shadi (§5.6) va ikkala fayl (`rbac.py` + `rbac.ts`) **bitta commitda** o'zgaradi — `role-gate.test.mjs:29-56` ikkalasini **matn sifatida** solishtiradi |
| **M-8** | ⛔ **Dalil kadri uchun RBAC O'ZGARISHI KERAK EMAS** [KOD: `rbac.ts:88-108`] | `director` va `market_admin` ikkalasida ham **`camera_view` BOR**. `GET /snapshots/{id}/image` esa 05-15 da `CAMERA_VIEW` **yoki** `OCCUPANCY_REVIEW` ostiga o'tgan. Dalil kadri 6-fazada **faqat direktor yuzasida** ko'rsatilgani uchun (§11) `require_any_permission()` ning **yopiq to'plami TEGILMAYDI** va `SNAPSHOT_EVIDENCE_FRAME_ROUTES` **aynan bitta marshrutda qoladi**. C-9 ning eng qimmat to'sig'i shu tanlov bilan **umuman tug'ilmaydi** |
| **M-9** | **Pul ko'rsatish naqshi** [KOD: `tariff-list.tsx:263,277`, `api-types.ts:45`, `money.py:87-111`] | Server `amount_soum` ni **butun son** sifatida yuboradi (`soumSchema = z.number().int().max(Number.MAX_SAFE_INTEGER)`), klient `useFormatter().number(...)` + `t("<ns>.amountUnit")` bilan chizadi. Uchala locale'da birlik bor: `so'm` / `сўм` / `сум` [KOD: `messages/*.json:389`]. Server tomonda `format_soum()` NBSP guruhlaydi — **klientda pul kutubxonasi YO'Q va qo'shilmaydi** |
| **M-10** | **Mijoz qulfi naqshi** [KOD: `blind-session.tsx:92-137`, `review-session.test.tsx:403-429`] | `submittedRef = useRef<string \| null>(null)` — qulf **band identifikatorini** saqlaydi, `onError` da nolga qaytadi, `onSuccess` da qolmaydi. Sanoq testi `apiFetch.mock.calls` ni filtrlab `toHaveLength(1)` qiladi. Ikkalasi ham 6-fazada **shakl o'zgarishisiz** qayta ishlatiladi |

### 0.2 M-4 ning oqibati — ochiq yozilgan tuzoq

```
bulk-action-surface.test.mjs:112-125
  assert.equal(SPEC_FILES.length, 1,
    "G-18 ni e'lon qilgan UI-SPEC soni ... (kutilgan: 1)
     Birdan ko'pda — qaysi e'lon bog'lovchi ekani noaniq.")
```

Bu darvoza 05-16 ning **W-2** tuzatishi: qamrov e'londan **hosila**. Uning narxi — **e'lon YAGONA bo'lishi shart**. Ya'ni 6-faza `components/collect/**` ni ommaviy-amal skaniga qo'shishni **yangi G-18 qatori yozib** hal qila olmaydi.

**Tanlangan yo'l** (§15.4): mavjud `05-UI-SPEC.md` §15 ning G-18 qatoriga uchinchi naqsh — `` `components/collect/**` `` — **qo'shiladi**, va aynan **birinchi `components/collect/*.tsx` mahsulot fayli bilan bitta commitda** (darvoza e'lon qilingan har katalogning **mavjud va bo'sh emasligini** ham tekshiradi — `:293-308`).

**Rad etilgan muqobil:** `SPEC_FILES.length === 1` ni `>= 1` ga bo'shatib globlarni **birlashtirish**. Rad etish sababi: o'sha assert «e'lon ko'chirildi/qayta nomlandi» tuzog'i uchun bor va uni bo'shatish darvozani **jimgina bo'sh skanga** ochib qo'yardi — ya'ni tuzatish o'zi tuzatayotgan sinfdagi xato bo'lardi.

---

## 1. Ko'lam va ko'lamdan tashqari

### 1.1 To'rtta yuza — va ular teng og'ir emas

| # | Yuza | Nimaga javob beradi | Foydalanuvchi | Ustuvorlik |
|---|------|---------------------|---------------|------------|
| **Y-1** | ⛔ **Kassir yig'ish ekrani** (CASH-01, CASH-02, CASH-03) | «Bu rastadan qancha olinadi va u yozildimi?» | Kassir, **telefonda, bozor ichida, kuniga 300–1000 marta** | ⛔ **ENG YUQORI** |
| **Y-2** | **Kutilayotgan patta proyeksiyasi** (BILL-05) | «Bugun qancha kutilyapti — va bu hisob EMAS» | Kassir (rasta kesimida) + direktor (bozor kesimida) | Yuqori |
| **Y-3** | **Smena va ko'r naqd deklaratsiyasi** (CASH-04) | «Qutimda qancha naqd bor — tizim aytmasdan» | Kassir, kuniga 2 marta | Yuqori |
| **Y-4** | **Hisoblar, qarz, anomaliya va dalil** (BILL-02, BILL-03, BILL-04) | «Bu patta nimaga asoslangan — va kadrni ko'rsat» | Direktor, bozor admini | O'rta |

### 1.2 Y-1 nima uchun eng yuqori — va nima uchun UI uni JIMGINA buza oladi

ROADMAP Phase 6 SC#4: *«kassir rastani raqamdan topib, tarifdan kelgan summani **≤3 bosishda** tasdiqlaydi va summani **faqat sabab-kod bilan** o'zgartira oladi.»*

06-CONTEXT D-02 nizo modelini nomlaydi: *«bu yerda xato — **odam pul to'laganini isbotlay olmasligi**.»*

5-fazadagi buzilgan UI **ko'rinmaydigan yolg'on** aytardi (soxta aniqlik raqami). Bu yerda buzilgan UI **ko'rinadigan, lekin kechikkan** yolg'on aytadi:

> Kassir 80 ta to'lov yozdi. Uchtasi tarmoq uzilishi paytida **ikki marta** ketdi. Kechqurun sotuvchi «men to'lagandim» deydi, tizim «yo'q» deydi — va **hech kim** buni sababini topolmaydi, chunki xato yozuvda emas, **bosishda** edi.

Shuning uchun to'rtta UI qoidasi **muzokarasiz** va §15 da darvozaga aylanadi:

| # | Qoida | Nima uchun UI qatlamida ham kerak |
|---|-------|------------------------------------|
| **1** | ⛔ Bosish soni **SANALADI**, «uchta tugma bor» deb tekshirilmaydi | Strukturaviy tekshiruv to'rtinchi qadam qo'shilganda **yashil qoladi**. D-18 miqdor, ya'ni u o'lchanadi (§15 G-20) |
| **2** | ⛔ Dublikat **ikki qatlamda** to'siladi — server kaliti **va** mijoz `useRef` qulfi | 05-13 o'lchadi: uch tez bosish **uchta so'rov** yubordi, chunki `isPending` faqat **keyingi renderda** o'zgaradi. Server kafolati UI ni to'xtatmadi (§15 G-21) |
| **3** | ⛔ Summa **serverdan keladi** va klient uni **hisoblab chiqara olmaydi** | D-20. Kuchli shakl: klientda tarif **kirish ma'lumotining o'zi yo'q** — ya'ni hisoblash *taqiqlanmaydi*, **imkonsiz** bo'ladi (§15 G-22) |
| **4** | ⛔ Proyeksiya kvitansiya bo'lib **o'qilishi mumkin emas** | D-17. Eng kuchli kanal — ikkisi **bir ekranda hech qachon uchrashmaydi** (§9.3, §15 G-25) |

### 1.3 Bu fazaning UI'si NIMA QILMAYDI (qisqa ro'yxat — to'lig'i §16)

- Telegram push-kvitansiya (`CASH-05`) — **7-faza**
- «Band, lekin to'lovsiz» ro'yxati va case oqimi — **7-faza**
- `.xlsx` eksporti, diagramma, oylik trend, qarzdorlik reyestri **sotuvchi kesimida** — **8-faza**
- Offline navbat, PWA manifesti, service worker — **`V2-CASH-05`** (§16.2)
- QR / bank o'tkazma, fiskal kvitansiya maydonlari — **`V2-CASH-03/04`**
- Variance chegarasi va uning alerti — **8-faza** (06-RESEARCH OQ-7 / A6)

### 1.4 Talab qamrovi

| REQ | Bu fazada UI'da qanday ko'rinadi |
|-----|----------------------------------|
| **BILL-01** | UI'da **bevosita yo'q** (job). Y-4 uning **natijasini** ko'rsatadi: `/billing?day=<kecha>` da yozilgan hisoblar |
| **BILL-02** | Y-4 — DL-3 hisob tafsiloti: dalil kadrlari + `charge_adjustments` ro'yxati + ⛔ «Bu hisob o'zgartirilmaydi» jumlasi |
| **BILL-03** | Y-4 — qarz **hisoblanadigan** qoldiq sifatida; ⛔ hech qayerda `balance` **ustuni** ko'rinmaydi (§15 G-22 taqiqlangan nomlar) |
| **BILL-04** | Y-4 — anomaliya ro'yxati, **uchta `kind` uchta boshqa yorliq** (§11.4); ⛔ case oqimi YO'Q |
| **BILL-05** | Y-2 — proyeksiya; ⛔ `charge_id` payloadda **umuman yo'q** (§9.2) |
| **CASH-01** | Y-1 — `autoFocus` + `inputMode="numeric"` + `Enter` → summa serverdan → to'lov turi → tasdiq = **3 qadam** (§8) |
| **CASH-02** | Y-1 — DL-1 **yopiq sabab-kod** ro'yxati; ⛔ erkin matn maydoni **yo'q** (§8.6) |
| **CASH-03** | Y-1 — `useRef` qulfi + idempotentlik kaliti hayot davri (§8.7); storno = DL-2, **yangi qator**, sabab-kod majburiy |
| **CASH-04** | Y-3 — ko'r deklaratsiya; ⛔ `system_*` **va** `variance*` javob kalitlari to'plamida **yo'q** (§10.3); direktor variance ni Y-4 da **ikki tomonlama** ko'radi |

---

## 2. Yuqori oqim qarorlaridan meros

32 ta qulflangan qarordan **o'n to'rttasi** UI shaklini bevosita belgilaydi. 13 ta contradiction (C-1…C-13) dan **oltitasi** UI'ga tegadi.

| Qaror / Contradiction | Manba | UI'dagi bevosita oqibati |
|---|---|---|
| **D-02** nizo modeli — sotuvchi bilan | 06-CONTEXT | Har ekranda savol: «nizo paytida qaysi yozuv dalil?» → Y-4 DL-3 ning butun mavjudlik sababi |
| **D-11** pul `BIGINT` so'm | 06-CONTEXT | Klientda `soumSchema` (`z.number().int()`); ⛔ `Decimal`/`Intl.NumberFormat({style:"currency"})`/pul kutubxonasi **yo'q** (§12.5) |
| **D-17** proyeksiya hisob EMAS, `charge_id` **umuman yo'q** | 06-CONTEXT | §9.2 payload kontrakti + §9.3 yetti kanalli vizual farq + G-22/G-23/G-25 |
| **D-18** ≤3 bosish aniq ta'rifi | 06-CONTEXT | §8.2 qadam mashinasi + `data-collect-step` kontrakti + **G-20 sanoq darvozasi** |
| **D-19** yopiq sabab-kod ro'yxati | 06-CONTEXT | §8.6 DL-1; ⛔ `other`/`custom` **yo'q**; override **ataylab qimmat** (§8.6) |
| **D-20** klient tarif summasini hisoblamaydi | 06-CONTEXT | §9.2: klientga `tariff_id`/`category_id` **umuman yuborilmaydi** → hisoblash imkonsiz (G-22) |
| **D-21** idempotentlik kaliti **mijozda** tug'iladi | 06-CONTEXT | §8.7 kalit hayot davri: qachon tug'iladi, qachon **saqlanadi**, qachon iste'foga chiqadi |
| **D-22** ikki qatlam majburiy | 06-CONTEXT | §8.7 `useRef` qulfi + **G-21** |
| **D-25** ko'r deklaratsiya, tizim summasi **e'lon qilinmagan** | 06-CONTEXT | §10.3 javob kalitlari to'plami + **G-7 (frontend yarmi)** |
| **D-26** variance **ikki tomonlama**, avtomatik to'g'rilanmaydi | 06-CONTEXT | §11.5: ikki yo'nalish, ikki `tone`, ⛔ **yozuv yuzasi 0** (G-27) |
| **D-31** inkor tasdiq ishlatilmaydi — **to'plam tengligi** | 06-CONTEXT | Har darvoza `not.toContain` emas, `deepEqual`/`Set` tengligi bilan yozilgan (§15.2) |
| **D-32** darvoza qamrovi **hosila** | 06-CONTEXT | Har darvoza katalogni/reyestrni/marshrut grafini **o'qiydi** (§15.2) |
| **C-3** hisob **ertasi kuni 04:10** da tug'iladi | 06-RESEARCH | ⛔ §9.3 kanal 6: `day = bugun` da yozilgan hisob **BO'LMAYDI** → proyeksiya va hisob **bir ekranda uchrashmaydi**; §11.2 kun tanlagichining standarti **kecha** |
| **C-4** `payments.charge_id` **YO'Q** — sotuvchi darajasidagi kredit | 06-RESEARCH | §9.2: kassir «qaysi kun uchun» ni `service_date` bilan ko'radi; ⛔ «bu hisobni to'lash» degan tugma **yo'q** |
| **C-8** proyeksiya **tarif-asosli**, hisob **bandlik-asosli** | 06-RESEARCH | §9.1: proyeksiyada `is_billable`/`occupied_slots` **yo'q** — u bugun **bilinmaydi** va soxta ko'rsatkich bo'lardi |
| **C-9** kassirda o'qish huquqi yo'q; `require_any_permission()` **yopiq to'plam** | 06-RESEARCH | §5.6: ikki yangi huquq, `require_permission` bilan; ⛔ dalil kadri kassirga **berilmaydi** → yopiq to'plam **tegilmaydi** [O'LCHANDI: M-8] |
| **C-10** kassir yuzasida shaxsiy maydon **yo'q** | 06-RESEARCH | §5.5 **[QAROR]**: 6-fazada birorta **yangi** marshrut `PERSONAL_FIELDS` nomini qaytarmaydi; ismlar mavjud audit qilingan marshrutlardan **klientda** joinlanadi |
| **C-12** anomaliya `kind` va dalil **juftlangan** | 06-RESEARCH | §11.4: `no_coverage_stall` da dalil affordansi **umuman chizilmaydi** (o'chirilgan emas) |
| **C-13** yangi `AuditAction`/xato kodi **uchala tilni** talab qiladi | 06-RESEARCH | §13.7 xato reyestri + §15 G-24/G-26; `uz-Cyrl` **generatsiya** |

---

## 3. Dizayn tizimi holati

### 3.1 Meros — o'zgarmaydi va qayta qurilmaydi

| Nima | Fayl | 6-fazada |
|------|------|----------|
| Tailwind 4 CSS-first `@theme` (20+ rang tokeni) | `frontend/src/app/globals.css` | **O'zgarmaydi** |
| `Button` (4 variant, `lg` = 44px) | `ui/button.tsx` | To'lov turi, tasdiq, smena amallari |
| `Card` / `CardHeader` / `CardContent` | `ui/card.tsx` | Proyeksiya kartasi, smena kartasi, hisobot bloklari |
| `Input` (+`aria-invalid`), `Field` (`${id}-error` / `${id}-hint`) | `ui/input.tsx`, `ui/field.tsx` | Rasta qidirish, deklaratsiya summasi, override summasi |
| `Select` (native `<select>`) | `ui/select.tsx` | ⛔ **Sabab-kod ro'yxati** (D-19) — native, chunki yopiq to'plam |
| `Badge` (`neutral/muted/accent/success/warning/danger`) [KOD: `badge.tsx:28-43`] | `ui/badge.tsx` | To'lov holati, anomaliya turi, variance yo'nalishi |
| `Skeleton` (`motion-reduce:animate-none`) | `ui/skeleton.tsx` | ⛔ **Summa maydonining yuklanishi** — eski summani ko'rsatish o'rniga (§9.4) |
| `EmptyState` (`title`/`description`/`action`) | `ui/empty-state.tsx` | **7 ta** bo'sh holat (§13.8) |
| `Dialog` (`sm/md/lg` + `sheetOnMobile`) | `ui/dialog.tsx` | DL-1, DL-2, DL-3 |
| `ConfirmDialog` (fokus destruktiv tugmada **emas**) | `ui/confirm-dialog.tsx` | DL-4 (smenani yopish), DL-2 tasdig'i |
| `sonner` Toaster (`top-center richColors`) | `app/[locale]/layout.tsx:82` | 6 ta toast (§13.8) |
| `nuqs` URL holati | `audit-filters.tsx`, `stall-filters.tsx` | ⛔ **Faqat Y-4 da** (`?day=`) — Y-1/Y-3 da URL holati **taqiqlanadi** (§4.5) |
| RBAC UI ko'zgusi (huquq yo'q → **render qilinmaydi**) | `lib/rbac.ts` | `payment_create` / `billing_collect_view` / `shift_manage` / `report_view` |
| next-intl 3 til + `i18n:check` darvozasi | `messages/*`, `scripts/*.mjs` | §13 |
| Kadr ramkasi `bg-text` letterbox + `text-bg` (15,6:1) | 03-UI-SPEC §2.3 | DL-3 dalil kadri |
| Pul ko'rsatish: `useFormatter().number()` + `*.amountUnit` | `tariff-list.tsx:263,277` | ⛔ **Yagona yo'l** — pul kutubxonasi qo'shilmaydi [O'LCHANDI: M-9] |
| `useRef` dublikat qulfi | `blind-session.tsx:92` | §8.7 — shakl **o'zgarishisiz** [O'LCHANDI: M-10] |
| Bosish sanoq testi naqshi | `review-session.test.tsx:403-429` | §15 G-20/G-21 asosi |

### 3.2 Yangi `ui/` primitivi — YO'Q [O'LCHANDI: M-2]

**6-fazada `frontend/src/components/ui/` ga hech nima qo'shilmaydi.** To'rtala yuza mavjud 10 primitiv ustida yig'iladi.

Uchta chegaraviy holat **ataylab** `ui/` ga ko'tarilmaydi:

| Komponent | Nega `ui/` emas |
|-----------|------------------|
| `collect/payment-bar.tsx` | Uning semantikasi (idempotentlik kaliti, `useRef` qulfi, server summasi) 6-faza domeniga xos. Umumiy primitiv qilish qulfni **shartsizdan shartliga** aylantirardi — `review/decision-bar.tsx` qarorining aynan takrori (05-UI-SPEC §3.2) |
| `collect/shift-close-form.tsx` | Uning butun ma'nosi — **ko'rmaslik**. `ui/` ga chiqarilgan «summa kiritish formasi» ertaga tizim summasini `prop` sifatida qabul qilardi va D-25 **bitta `props` uzatilishi** bilan buzilardi |
| `billing/variance-cell.tsx` | Ikki tomonlama ishora + `tone` + ikonka + yorliq — bu **domen qoidasi** (D-26), umumiy «delta katagi» emas |

### 3.3 Analogi yo'q komponentlar — soxta analog berilmaydi

| Komponent | Nega analog yo'q | Nima qilinadi |
|-----------|------------------|---------------|
| `collect/collect-session.tsx` | Kodbazada «bir ekranda takrorlanadigan, har takrorda nolga qaytadigan tranzaksiya oqimi» naqshi yo'q. `review-session.tsx` **navbatni** boshqaradi (band tugadi → keyingisi), bu esa **foydalanuvchi kiritgan** identifikatordan boshlanadi va **fokusni qaytaradi** | §8.2–§8.7 da to'liq yoziladi: qadam mashinasi, `data-collect-step`, fokus qaytishi, kalit hayot davri |
| `collect/stall-lookup.tsx` | `stall-filters.tsx` — **filtr** (ro'yxatni toraytiradi). Bu esa **navigator** (aynan bitta natijada darhol o'tadi) | §8.3; kontrakt 2-fazada allaqachon yozilgan va o'lchangan [MEROS: `02-UI-SPEC.md:503-513`] |
| `billing/charge-detail-dialog.tsx` | `DL-5` (05-UI-SPEC §11.7) rasta kunini ko'rsatadi, hisobni emas; va u **slot qatorlarisiz** qurilgan | §11.3 da to'liq yoziladi — faqat marshrut **bergan** maydonlar |

### 3.4 shadcn darvozasi — natija [O'LCHANDI: M-1]

**`components.json` topilmadi** → **`Tool: none`. `shadcn init` BAJARILMAYDI.** [QAROR — 2, 3, 4 va 5-faza qarorini davom ettiradi]

Sabablar o'zgarmagan: (1) `shadcn init` `package.json` ga yangi paket keltiradi; (2) Tailwind 4 rejimida u `globals.css` ga **o'z token nomlarini** yozadi va `--color-bg`/`--color-surface`/`--color-accent` yonida **ikkinchi dizayn tizimi** paydo bo'lardi; (3) bu subagent kontekstida interaktiv savol vositasi yo'q — darvoza hujjatlashtirilgan qaror bilan yopiladi.

**Oqibat:** `Registry Safety` darvozasi shadcn uchun **qo'llanmaydi** (§14.1).

### 3.5 Yangi bog'liqlik so'rovi — YO'Q

**Yangi npm paketi: YO'Q. Yangi vendored artefakt: YO'Q.** [QAROR — 06-RESEARCH § Package Legitimacy Audit bilan mos: «bu faza birorta yangi paket o'rnatmaydi»]

| Ehtiyoj | Mavjud yechim | Nega yangi paket kerak emas |
|---------|---------------|------------------------------|
| Pul formatlash | `useFormatter().number()` + `*.amountUnit` kaliti | [O'LCHANDI: M-9] Uchala locale'da birlik bor. `dinero.js`/`currency.js` **butun pul modelini** olib kelardi va u serverda (`money.py`) allaqachon bor — ikkinchi haqiqat manbai |
| Raqamli klaviatura | `inputMode="numeric"` (OS klaviaturasi) | 06-RESEARCH OQ-2: rasta kodi **`text`** (`12a`, `A-3` bo'lishi mumkin — `market.py:154-183`), ya'ni faqat raqamli panel ba'zi kodlarni **kiritib bo'lmaydigan** qilardi (§8.3) |
| Idempotentlik kaliti | `crypto.randomUUID()` (native) | `uuid` paketi kerak emas; brauzer API'si yetarli |
| Sabab-kod tanlash | native `<select>` (`ui/select.tsx`) | Yopiq to'plam — Radix `Select` ham kerak emas; native OS ro'yxati telefonda **tezroq** va bir qo'lda ishlaydi |
| Jadval / saralash | native `<table>` + server tartibi | `@tanstack/react-table` — Y-4 da 3 ustunli jadvallar; saralash **serverda** (`code_sort`) |
| Diagramma | ⛔ **YO'Q** | `recharts` `package.json` da yo'q va 8-faza egasi (§16.1) |

> Agar reja bajarilishida boshqa paket zarur bo'lib chiqsa, u **UI-SPEC ga qaytariladi** va shu bo'limga sabab + rad etilgan muqobil bilan yoziladi — jimgina `npm install` **qilinmaydi** [MEROS: 02-UI-SPEC §13].

---

## 4. Ekranlar reyestri

### 4.1 Marshrutlar

| Marshrut | Yuza | Vazifa | Huquq (UI ko'zgusi) |
|----------|------|--------|---------------------|
| `/[locale]/(app)/collect` | ⛔ **Y-1 + Y-2 (rasta kesimi)** | Kassir yig'ish oqimi: rasta → summa → to'lov turi → tasdiq | `payment_create` |
| `/[locale]/(app)/collect/shift` | **Y-3** | Smena ochish / **ko'r naqd deklaratsiyasi** bilan yopish | `shift_manage` |
| `/[locale]/(app)/billing` | **Y-4 + Y-2 (bozor kesimi)** | Hisoblar, qarz, anomaliya, smena variance; `day` bo'yicha | `report_view` |
| `/[locale]/(app)/billing?day=YYYY-MM-DD` | Y-4 | O'sha sahifa, tanlangan biznes-kun (`nuqs`) | `report_view` |

**Boshqa marshrut YO'Q.** `/payments`, `/payments/[id]`, `/collect/[stallCode]`, `/shifts`, `/shifts/[id]`, `/charges/[id]`, `/debts` — **qurilmaydi**.

### 4.2 Nega smena `/collect` OSTIDA, mustaqil bo'lim emas [QAROR]

Muqobil ko'rib chiqildi: `/shifts` — mustaqil navigatsiya elementi.

**Rad etildi.** Sabab:

1. **Smena kassir oqimining SHARTI, alohida ish emas.** `/collect` ochiq smenasiz **ishlamaydi** (§8.1 `no-shift` holati) va u yerdan bitta havola bilan `/collect/shift` ga o'tiladi. URL ierarxiyasi shu bog'liqlikni takrorlaydi.
2. **Navigatsiya byudjeti.** Mustaqil element `NAV_ITEMS` ni **16** ga chiqarardi; kassirda 3 element bo'lardi va mobil panelda `/dashboard` + `/collect` + `/shifts` — ya'ni kuniga 2 marta bosiladigan narsa kuniga 500 marta bosiladigan narsa bilan **teng og'irlikda** turardi [O'LCHANDI: M-6].
3. **Direktorga `/shifts` KERAK EMAS.** Direktor variance ni **Y-4 da**, kun kesimida ko'radi (§11.5) — ya'ni ikkinchi marshrut ikkinchi iste'molchi topmasdi.

### 4.3 Nega hisoblar reyestri `/billing`, `/occupancy` ga qo'shilmaydi [QAROR]

Muqobil: `/occupancy?day=` sahifasiga «Patta» ustuni qo'shish.

⛔ **Rad etildi va sabab strukturaviy:**

| # | Sabab |
|---|-------|
| 1 | **`/occupancy` `report_view` ostida bandlikni** ko'rsatadi va uning copy'si 05-UI-SPEC §16.1 da **ochiq va'da beradi**: *«Patta hisobi alohida qoidaga ko'ra yuritiladi»* (`occupancy.notBillingYet`). Ustun qo'shish o'sha jumlani **yolg'onga** aylantirardi va uni olib tashlash 5-faza copy darvozasini o'zgartirardi |
| 2 | **Bandlik ≠ hisob** va D-04/D-05 aynan shu farqda yashaydi: `no_coverage` bandlikda **ko'rinadi**, hisobda **yo'q**. Bitta jadvalda ikki semantika — 4-fazadagi «bo'sh katak» sinfidagi jim xato |
| 3 | **Kun semantikasi boshqa.** `/occupancy` `stall_slot_occupancy.business_date` bo'yicha (ma'lumot tegishli kun), `/billing` `daily_charges.service_date` bo'yicha. Ikkalasi bir sahifada bir `?day=` ni bo'lishsa, **Pitfall 1** (C-2 nom tuzog'i) UI qatlamiga ko'chardi |
| 4 | **Alohida katalog — darvozaning sharti.** `components/billing/**` alohida bo'lgani uchun G-22 `components/collect/**` da `charge_id` **yo'qligini**, G-25 esa ikki blokning **uchrashmasligini** skanerlab bera oladi. Aralash katalogda ikkalasi ham kontekstga bog'liq shartga aylanardi (05-UI-SPEC §4.3 mulohazasining aynan takrori) |

### 4.4 Dialoglar (marshrut emas, sahifa holati)

| # | Dialog | Ochiladi | O'lcham | Huquq |
|---|--------|----------|---------|-------|
| **DL-1** | ⛔ **Summani o'zgartirish** — yopiq sabab-kod + yangi summa | Y-1 dan, `[Summani o'zgartirish]` | `size="sm" sheetOnMobile` | `payment_create` |
| **DL-2** | **To'lovni bekor qilish** — yopiq sabab-kod + tasdiq | Y-1 dagi to'lov qatoridan | `size="sm" sheetOnMobile` | `payment_create` |
| **DL-3** | **Hisob tafsiloti** — tarif, tuzatishlar, **dalil kadrlari** | Y-4 hisoblar ro'yxatidan | `size="lg" sheetOnMobile` | `report_view` |
| **DL-4** | **Smenani yopish** (tasdiq) — deklaratsiya **o'zgarmas** | Y-3 dan | `ConfirmDialog` 1-daraja | `shift_manage` |

**Dialog holati URL'da EMAS** [MEROS: 02-UI-SPEC §7.1].

⚠ **DL-1 va DL-2 `size="sm"`** — ataylab kichik va **bitta ekranga sig'adi**: telefonda skroll qilinадиган dialog ichida «tasdiqlash» tugmasi ko'rinmay qolsa, kassir uni **topmaydi** va oqim to'xtaydi.

### 4.5 ⛔ URL holati kontrakti — Y-1 va Y-3 da URL holati TAQIQLANADI

| Yuza | URL holati | Sabab |
|------|-----------|-------|
| **Y-1** `/collect` | ⛔ **YO'Q** — rasta kodi URL'da **emas** | Uch sabab: (1) URL'dagi kod **ulashiladigan va zakladkaga qo'yiladigan** to'lov varag'i yaratardi va u **eski summa** bilan qayta ochilardi; (2) idempotentlik kaliti sahifa holatida yashaydi (§8.7) va URL bilan qaytish **kalitni yo'qotib**, dublikat yaratardi; (3) orqaga-tugmasi bilan «to'lovdan oldingi holat» ga qaytish tasdiqlangan to'lovni **bekor qilingandek** ko'rsatardi |
| **Y-3** `/collect/shift` | ⛔ **YO'Q** | Deklaratsiya bir marta yoziladi; `?declared=` shaklidagi har qanday holat uni **oldindan to'ldirilgan** qilib qo'yardi |
| **Y-4** `/billing` | ✅ **`?day=YYYY-MM-DD`** (`nuqs`) | `/occupancy?day=` bilan aynan bir xil naqsh — kun ulashiladi, chunki u **hisobot**, tranzaksiya emas |

### 4.6 Navigatsiya kengaytmasi — ikkita yozuv [QAROR]

| Yozuv | Guruh | Ikonka | Huquq | Joyi |
|-------|-------|--------|-------|------|
| **Yig'ish** (`/collect`) | `market` | `HandCoins` | `payment_create` | `/occupancy` dan **keyin** |
| **Patta hisobi** (`/billing`) | `market` | `ReceiptText` | `report_view` | `/collect` dan **keyin** |

[O'LCHANDI: M-6] Natija: `NAV_ITEMS` 13→**15**. `platform_admin` **11 (o'zgarmaydi)** · `director` 11→**12** · `market_admin` 11→**12** · ⛔ **`cashier` 1→2** · `inspector` **2 (o'zgarmaydi)**. `MOBILE_PRIMARY_COUNT = 4` — kassirning mobil paneli **`/dashboard` + `/collect`**, overflow **0**.

⚠ **`/collect/shift` NAV_ITEMS ga QO'SHILMAYDI** — u `/collect` sahifasining sarlavhasidagi havola (`/cameras/[id]/zones` bilan bir xil naqsh: bola marshrut nav elementi emas).

⚠ **Kassirning boshlang'ich sahifasi `/dashboard` bo'lib QOLADI** [QAROR]. Rol bo'yicha bosh ekran — **7-fazaning** ishi (ROADMAP Phase 7 SC#3: «har rol bosh ekranida o'ziga mos bitta asosiy raqamni ko'radi»). Bu 6-fazada zarar keltirmaydi: navigatsiya **≤3 bosish sanog'idan tashqarida** (§8.2 sanoq **sahifa ochilgandan** boshlanadi), va kassir kuniga **bir marta** `/collect` ga o'tadi — keyin §8.5 fokus qaytishi tufayli sahifadan **chiqmaydi**.

---

## 5. Komponentlar reyestri

### 5.1 Wave 0 — yangi ekranlardan OLDIN (bloklovchi)

| # | Ish | Fayl | Nega bloklovchi |
|---|-----|------|------------------|
| **W0-F1** | Ikki huquq **ikki faylda** | `services/core-api/app/security/rbac.py` **+** `frontend/src/lib/rbac.ts` | [O'LCHANDI: M-7] Bittasi yangilansa: backendda tugma ko'rinmaydi (huquq bor) yoki tugma ko'rinib turib **403** beradi. `role-gate.test.mjs:29-56` ikkalasini matn sifatida solishtiradi. ⛔ **BITTA commit** |
| **W0-F2** | Xato kodlari reyestri | `frontend/src/lib/billing-errors.ts` | §13.7 dagi har kod uchun `errorCause`/`errorFix` **juftligi** kerak; `error-codes.test.mjs` naqshi (G-17) buni **uchala tilda** talab qiladi |
| **W0-F3** | Ikki **alohida** so'rov moduli | `lib/billing-pending-queries.ts` **va** `lib/billing-charge-queries.ts` | ⛔ **G-22 ning butun asosi.** Bitta modulda proyeksiya va yozilgan hisob uchrashsa, `charge_id` ning proyeksiya tipiga o'tishi **bitta `props` uzatilishi** bo'lardi — 05-UI-SPEC §5.3 mulohazasining aynan takrori |
| **W0-F4** | `frontend/scripts/collect-surface.test.mjs` | yangi | **G-7 (frontend yarmi)** + **G-22**. `stripComments()` helperi `bulk-action-surface.test.mjs:163-225` dan **ko'chiriladi** (ikkinchi implementatsiya yozilmaydi) |
| **W0-F5** | `frontend/scripts/billing-copy.test.mjs` | yangi | **G-24** + **G-26**. Sabab-kod va anomaliya turlari **to'plam tengligi** bilan uchala locale'da |
| **W0-F6** | `05-UI-SPEC.md` §15 G-18 qatoriga `` `components/collect/**` `` | mavjud fayl (bitta qator) | [O'LCHANDI: M-4] §15.4. ⛔ **Aynan birinchi `components/collect/*.tsx` bilan bitta commitda** — darvoza e'lon qilingan katalogning **mavjud va bo'sh emasligini** ham tekshiradi |
| **W0-F7** | `AnomalyKind` / `AdjustmentReason` / `ReversalReason` / `PaymentMethod` ko'zgusi | `frontend/src/lib/api-types.ts` | G-24/G-26 reyestrdan **iteratsiya qiladi**; to'plam bu faylda **bir joyda** yashaydi (05-13 darsi: darvoza tekshirayotgan qiymatni **import qilmaydi**, ikkinchi marta **yozadi**) |

### 5.2 Yangi komponentlar

| Fayl | Yuza | Vazifa | Kontrakt bo'limi |
|------|------|--------|------------------|
| `components/collect/collect-session.tsx` | Y-1 | Qadam mashinasi, fokus qaytishi, kalit hayot davri | §8.1–§8.7 |
| `components/collect/stall-lookup.tsx` | Y-1 | `autoFocus` + `inputMode="numeric"` + `Enter` | §8.3 |
| `components/collect/pending-card.tsx` | Y-2 (rasta) | Kutilayotgan patta — ⛔ `charge_id` **YO'Q** | §9.2–§9.4 |
| `components/collect/payment-bar.tsx` | Y-1 | To'lov turi (radiogroup) + tasdiq + `useRef` qulfi | §8.4, §8.7 |
| `components/collect/reason-dialog.tsx` | DL-1 / DL-2 | Yopiq sabab-kod ro'yxati (native `<select>`) | §8.6 |
| `components/collect/payment-row.tsx` | Y-1 | Yozilgan to'lov qatori + bekor qilish kirish nuqtasi | §8.8 |
| `components/collect/shift-open-card.tsx` | Y-3 | Smena ochish | §10.1 |
| `components/collect/shift-close-form.tsx` | Y-3 | ⛔ **Ko'r naqd deklaratsiyasi** | §10.2–§10.4 |
| `components/billing/pending-summary.tsx` | Y-2 (bozor) | Bozor kesimida kutilayotgan patta | §9.5 |
| `components/billing/charge-list.tsx` | Y-4 | Yozilgan hisoblar + qoldiq | §11.2 |
| `components/billing/charge-detail-dialog.tsx` | DL-3 | Tarif, tuzatishlar, **dalil kadrlari** | §11.3 |
| `components/billing/anomaly-list.tsx` | Y-4 | ⛔ **Uch `kind` — uch yorliq** | §11.4 |
| `components/billing/variance-list.tsx` | Y-4 | ⛔ **Ikki tomonlama variance**, yozuv yuzasi 0 | §11.5 |
| `components/billing/variance-cell.tsx` | Y-4 | Ishora + `tone` + ikonka + yorliq | §11.5 |
| `components/billing/day-picker.tsx` | Y-4 | `?day=` (`nuqs`), maksimum **bugun** | §11.1 |

### 5.3 ⛔ Nega `lib/billing-pending-queries.ts` ALOHIDA modul — bu darvozaning asosi

`GET /billing/pending` (proyeksiya) va `GET /billing/charges` (yozilgan hisob) **bitta domenning ikki savoli**, lekin ular **bitta modulda yashamaydi**:

1. **G-22 shundan keyin yozilishi mumkin bo'ladi.** Taqiqlangan nomlar (`charge_id`, `vendor_name`, `tariff_id`, `system_total`, …) **butun faylda** izlanadi. Aralash modulda ular **qonuniy** bo'lardi (`charges` uchun `charge_id` kerak) va darvoza kontekstga bog'liq shartga aylanardi — ya'ni `grep` bilan tekshirib bo'lmaydigan narsaga.
2. **Kesh grafi ajraladi.** Proyeksiya `gcTime: 0` bilan yashaydi (§9.4), yozilgan hisoblar esa oddiy kesh bilan. Bitta modulda ikki siyosat **bir `queryClient` opsiyalar to'plamiga** siqilib ketardi.
3. **Tip tizimi ish qiladi.** `PendingStall` da `charge_id` **yo'q** → `item.charge_id` **kompilyatsiya xatosi**. Aralash modulda tip birlashmasi (`union`) paydo bo'lardi va `charge_id` `undefined` bo'lib **jimgina** o'tardi.

### 5.4 Kesh kalitlari — tug'ilishidanoq doiralangan

Kalitlar `marketId` bilan **boshlanadi** [MEROS: 04-UI-SPEC; `tenant-cache.test.tsx`].

| Kalit | Modul | `staleTime` | `gcTime` | Sabab |
|-------|-------|-------------|----------|-------|
| `[marketId, "billing-pending", stallCode]` | `billing-pending-queries.ts` | **0** | ⛔ **0** | §9.4 — **eski rastaning summasi yangi rasta kodi ostida ko'rinishi** noto'g'ri pul yig'ishga olib kelardi |
| `[marketId, "billing-pending", "market"]` | `billing-pending-queries.ts` | **0** | ⛔ **0** | O'sha sabab, bozor kesimida |
| `[marketId, "billing-charges", day]` | `billing-charge-queries.ts` | 60 s | standart | Yozilgan hisob **o'zgarmas** (D-07) → keshlash xavfsiz |
| `[marketId, "billing-anomalies", day]` | `billing-charge-queries.ts` | 60 s | standart | O'sha sabab (faqat qo'shiladi) |
| `[marketId, "shifts", day]` | `shift-queries.ts` | 30 s | standart | Direktor variance ro'yxati |
| `[marketId, "shift", "open"]` | `shift-queries.ts` | **0** | ⛔ **0** | Ochiq smena holati — eski javob «smena ochiq» deb yolg'on gapirardi |
| `[marketId, "payments", "recent"]` | `payment-queries.ts` | **0** | ⛔ **0** | §8.8 — bekor qilish oynasi |

⛔ **`invalidateQueries` emas, `removeQueries`** — muvaffaqiyatli `POST /payments` dan keyin `[marketId, "billing-pending"]` prefiksi **keshdan chiqariladi**. Sabab 05-13 da o'lchangan: kafolat **juftlikdan** (`gcTime: 0` + `removeQueries`) chiqadi va ikkala yarim alohida qo'riqlanadi (§15 G-23).

### 5.5 ⛔⛔ Shaxsiy ma'lumot: 6-fazada YANGI marshrut ism QAYTARMAYDI [QAROR]

**Kontrakt:** 6-faza qo'shadigan **birorta** marshrut `PERSONAL_FIELDS = {vendor_name, phone, full_name}` dan bittasini ham qaytarmaydi. Ekranda ko'rinadigan har ism **mavjud, audit qilingan** marshrutdan (`GET /vendors`, `GET /users`) olinib, **klientda** `id → nom` xaritasi bilan joinlanadi.

| Yuza | Ism kerakmi | Manba | Huquq |
|------|-------------|-------|-------|
| Y-1 `/collect` | ⛔ **YO'Q** | — | Kassirda `vendor_view` **yo'q** → ism **strukturaviy ravishda** olinmaydi |
| Y-2 proyeksiya | ⛔ **YO'Q** | — | O'sha |
| Y-3 smena | ⛔ **YO'Q** | — | Kassir o'z smenasini ko'radi, ism kerak emas |
| Y-4 hisoblar / qarz | ✅ sotuvchi nomi | mavjud `GET /vendors` | `vendor_view` (direktor, bozor admini) |
| Y-4 variance | ✅ kassir nomi | mavjud `GET /users` | `user_view` (direktor, bozor admini) |

**Nega bu yo'l tanlandi** [QAROR]:

1. **`PERSONAL_ROUTES` o'smaydi.** C-10 darvozasi (`test_personal_data_coverage.py:732-758`) har ism qaytaruvchi `GET` dan `VENDOR_VIEW` **va** `audit_read(...)` talab qiladi. Yangi moliyaviy marshrutga `VENDOR_VIEW` qo'yish — moliyaviy yuzaga **shaxsiy-ma'lumot qo'riqchisini** o'rnatish va keyingi ijrochi bu naqshni **ko'chirardi**.
2. **Kassirning istisnosi STRUKTURAVIY bo'ladi.** Ism marshrut darajasida emas, **huquq darajasida** yo'q: kassirda `vendor_view` yo'q, ya'ni `GET /vendors` **403** — hech qanday «kassir ekranida ism ko'rsatmaymiz» degan kod-ko'rik da'vosi kerak emas.
3. **Audit izi o'zgarmaydi.** Ism o'qilishi allaqachon `audit_read` bilan yozilgan marshrutda qoladi (2-faza D-09).
4. ⛔ **Darvozani NOM bilan aylanib o'tish TAQIQLANADI.** `vendor_label`, `payer`, `who` — hech biri. C-10 buni ochiq aytadi va §15 G-22 buni **taqiqlangan nomlar reyestri** bilan mexanik qiladi.

⚠ **Ochiq yozilgan narx:** Y-4 sahifasi **bitta qo'shimcha** `GET /vendors` so'rovi qiladi. Agar bozorning sotuvchi soni bu so'rovni og'ir qilsa, to'g'ri tuzatish — **mavjud** `/vendors` marshrutini sahifalash, hisob marshrutiga ism maydoni **qo'shish emas**.

⚠ **Kassir «kim to'layapti» ni ko'rmaydi** — 06-RESEARCH A7 buni `[ASSUMED]` deb belgilagan. §17 O-01 da ishlaydigan standart va tetigi yozilgan.

### 5.6 RBAC kengaytmasi — ikki yangi huquq, `require_any_permission()` TEGILMAYDI

| Huquq | Holat | Kim oladi | Nimani qo'riqlaydi |
|-------|-------|-----------|--------------------|
| `payment_create` | **mavjud** | `cashier` | `POST /payments`, `POST /payments/{id}/reverse` |
| `billing_collect_view` | ⛔ **yangi** | `cashier`, `market_admin`, `director` | `GET /billing/pending`, `GET /payments/recent` |
| `shift_manage` | ⛔ **yangi** | `cashier`, `market_admin` | `POST /shifts`, `GET /shifts/open`, `POST /shifts/{id}/close` |
| `report_view` | **mavjud** | `director`, `market_admin` | `GET /billing/charges`, `GET /billing/anomalies`, `GET /shifts` |

⛔ **Kassir OLMAYDIGAN huquqlar va sabablari:**

| Huquq | Nega yo'q |
|-------|-----------|
| `market_data_view` | `test_personal_data_coverage.py:761-787` — uning egasida `vendor_view` ham **bo'lishi SHART**, `vendor_view` esa **butun shaxsiy-ma'lumot yuzasini** ochadi (C-9 ⚠) |
| `vendor_view` | §5.5 — kassir yuzasida ism **bo'lmasligi** shu bilan strukturaviy bo'ladi |
| `camera_view` | ⛔ Dalil kadri kassirga **kerak emas** — u pul yig'adi, hukm chiqarmaydi. Bu tanlov `require_any_permission()` ning yopiq to'plamini **tegilmagan qoldiradi** [O'LCHANDI: M-8] |
| `report_view` | Kassir hisobot o'qimaydi; qarz **rasta kesimida** proyeksiyada ko'rinadi |

⛔ **`require_any_permission()` YANGI MARSHRUTDA ISHLATILMAYDI** (C-9, 06-RESEARCH § Anti-Patterns). Kassir va direktor bitta marshrutni bo'lishishi kerak bo'lsa — **bitta huquq bir necha rolga** beriladi (`billing_collect_view` aynan shunday), «yo P yo Q» **emas**.

### 5.7 Kengaytiriladigan mavjud fayllar

| Fayl | O'zgarish | Sabab |
|------|-----------|-------|
| `components/shell/app-shell.tsx` | `NAV_ITEMS` ga **2 yozuv** | §4.6 |
| `lib/rbac.ts` | `PERMISSIONS` ga **2 a'zo**, `ROLE_PERMISSIONS` ga taqsimot | §5.6, W0-F1 |
| `lib/api-types.ts` | 4 enum ko'zgusi + `soumSchema` qayta ishlatiladi | W0-F7 |
| `messages/uz-Latn.json` + `ru.json` | `collect.*`, `billing.*` namespace'lari | §13 |
| `messages/uz-Cyrl.json` | ⛔ **QO'LDA TAHRIRLANMAYDI** — `npm --prefix frontend run i18n:gen` | §13.9 |
| `05-UI-SPEC.md` §15 | G-18 qatoriga uchinchi katalog naqshi | §15.4, W0-F6 |
| `scripts/error-codes.test.mjs` | `BILLING_ERROR_CODES` reyestri qo'shiladi | §13.7, G-17 davomi |

### 5.8 Komponent testlari

| Test fayli | Nimani o'lchaydi | Darvoza |
|------------|-------------------|---------|
| `collect/collect-session.test.tsx` | ⛔ **Bosish SANOG'I** (§8.2), fokus qaytishi (§8.5), summa POST tanasida serverdan kelgani bilan **teng** | **G-20** |
| `collect/payment-bar.test.tsx` | Uch tez bosish → **bitta** so'rov; `Enter` bosib turish → **hech nima**; xatodan keyin qulf **ochiladi** | **G-21** |
| `collect/pending-card.test.tsx` | `pendingStallSchema.parse({...toza, charge_id})` **throw**; juftlangan invariant (`amount_soum === null` ⇔ `amount_unavailable_reason !== null`) | **G-23** |
| `collect/reason-dialog.test.tsx` | Sabab tanlanmasa tasdiq **`aria-disabled`**; ⛔ erkin matn maydoni **yo'q** | **G-24** |
| `collect/shift-close-form.test.tsx` | `shiftCloseResponseSchema.parse({...toza, system_total_soum})` **throw**; ekranda tizim summasi **va variance** yo'q | **G-7**, **G-23** |
| `billing/variance-list.test.tsx` | `declared > system` **va** `declared < system` **ikkalasi ham** ko'rsatiladi; ⛔ yozuv tugmasi **yo'q** | **G-27** |
| `billing/charge-detail-dialog.test.tsx` | Dalil kadri `src` **aynan** `/api/v1/snapshots/{id}/image`; `snapshot_id` yo'q qatorda kadr bloki **umuman chizilmaydi** | **G-28** |

---

## 6. Bo'shliq

### 6.1 4-panjara — o'zgarishsiz [MEROS: 02-UI-SPEC §2, 04-UI-SPEC §7.1, 05-UI-SPEC §9.1]

| Token | Qiymat | 6-fazada qayerda |
|-------|--------|------------------|
| `xs` | 4px (`1`) | Ikonka–matn oralig'i, badge ichki `y` |
| `sm` | 8px (`2`) | To'lov turi tugmalari orasi, to'lov qatorlari orasi |
| `md` | 12px (`3`) | Proyeksiya kartasidagi qatorlar orasi, jadval katagi ichki |
| `lg` | 16px (`4`) | Karta ichki, dialog bo'limlari |
| `xl` | 24px (`6`) | Y-1 ning uch bloki orasi (qidiruv ↔ summa ↔ to'lov) |
| `2xl` | 32px (`8`) | Y-4 bo'limlari orasi (hisoblar ↔ anomaliya ↔ variance) |
| `3xl` | 48px (`12`) | Bo'sh holat `py-12` |

**Meros istisnolari saqlanadi:** 44px (`min-h-11`) barcha barmoq nishoni; 56px (`min-h-14`) mobil pastki panel; 20px (`5`) `CardHeader`/`CardContent` ichki `x`.

### 6.2 Ikkita yangi o'lcham — ikkalasi ham panjaradan [QAROR]

| O'lcham | Qiymat | Tailwind | Nima uchun panjaradan chiqmaydi va nega meros minimumidan YUQORI |
|---------|--------|----------|-------------------------------------------------------------------|
| ⛔ **Tasdiqlash tugmasi va rasta qidiruv maydoni** | **56px** | `min-h-14` | 14 × 4 — panjarada, va u **meros istisnosi** (mobil pastki panel allaqachon 56px). Sabab **o'lchangan sharoit**: bu ikki element fazaning **eng ko'p bosiladigan** yuzasi (kuniga 300–1000 marta), **quyoshda**, **bir qo'lda**, ehtimol **qo'lqopda**. 44px minimum — *ruxsat etilgan* eng kichik, *tavsiya etilgan* emas |
| **To'lov turi tugmalari** (`Naqd` / `Terminal`) | **48px** | `min-h-12` | 12 × 4 — panjarada. 5-fazaning javob tugmalari bilan **aynan bir xil** o'lcham (05-UI-SPEC §9.2) va sabab ham bir xil: ular **tanlov**, ya'ni teng og'irlikda |

**Boshqa yangi qiymat so'ralmaydi.**

⚠ **Nima uchun tasdiqlash tugmasi to'lov turi tugmalaridan KATTA** [QAROR]: to'lov turi — **tanlov** (ikkitasi teng), tasdiqlash — **oqibat** (yagona, qaytarib bo'lmaydigan). Ierarxiya o'lchamda ko'rinadi va u §12.3 dagi rang ierarxiyasi bilan **bir yo'nalishda** ishlaydi. Teng o'lchamdagi uchta tugma kassirni «qaysi biri oxirgisi?» deb o'ylashga majburlardi — bu kuniga 500 marta takrorlanadigan mikro-pauza.

---

## 7. Tipografiya

### 7.1 To'rt rol — beshinchisi YO'Q [MEROS: 05-UI-SPEC §9.3, 03-UI-SPEC §2.2]

| Rol | O'lcham | Og'irlik | Line-height | Tailwind |
|-----|---------|----------|-------------|----------|
| **Display** — sahifa sarlavhasi, ⛔ **to'lanadigan summa** | 24px | 600 | 1.25 | `text-2xl font-semibold tracking-tight leading-tight` |
| **Heading** — karta/dialog sarlavhasi, `<legend>` | 18px | 600 | 1.375 | `text-lg font-semibold leading-snug` |
| **Body** — barcha matn va boshqaruv elementi | 14px | 400 | 1.5 | `text-sm leading-normal` |
| **Meta** — badge, yorliq, sana | 12px | 400 | 1.33 | `text-xs` |

**Urg'u — faqat og'irlik (600), o'lcham emas, rang emas.** `font-medium` (500) va `text-base` (16px) **taqiqlangan** [MEROS: 02-UI-SPEC §3.2].

**Beshinchi o'lcham QO'SHILMAYDI** [QAROR]. Vasvasa aniq va u rad etiladi: *«to'lanadigan summa quyoshda 24px da kichik ko'rinadi, 32px qilaylik»*. Rad etish sababi — **32px panjarada bo'lsa ham beshinchi rol** bo'lardi va u keyingi fazada «katta raqam» uslubiga aylanib, hisobotlarda ham paydo bo'lardi. To'lanadigan summa **Display rolini** oladi va u sahifada **yagona** Display elementi (§9.4), ya'ni raqobatchisi yo'q.

⚠ **Tetik ochiq yozilgan** (§17 O-04): agar dala UAT 24px ni yetarsiz deb topsa, tuzatish — **hujjatlashtirilgan beshinchi rol**, `text-[32px]` shaklidagi bir martalik qiymat **emas**.

### 7.2 `font-mono` — 6-faza ro'yxati

`font-mono` — **faqat** o'qib aytiladigan yoki tik ustunda solishtiriladigan texnik qiymat uchun [MEROS: 03-UI-SPEC §2.2].

| Qiymat | Uslub | Sabab |
|--------|-------|-------|
| ⛔ **Har qanday `*_soum` summasi** | `font-mono` | Ustunlar **tik solishtiriladi** — qarzdorlik va variance jadvalining butun ma'nosi shunda. Va bu D-02 ning shakli: nizoda raqam **o'qib aytiladi** |
| Variance (ishorasi bilan) | `font-mono` | O'sha |
| `charge_id` qisqa shakli (8 belgi) | `font-mono text-xs` | Identifikator — nizoda o'qib aytiladi |
| Idempotentlik kaliti | ⛔ **HECH QACHON ko'rsatilmaydi** | §8.7 — u ichki mexanizm, foydalanuvchi uchun ma'nosi yo'q |
| **Rasta raqami** (`14-C`) | ⛔ **`font-mono` EMAS** | 05-UI-SPEC §9.4 qoidasi o'zgarishsiz: u **DB kontenti** va odam o'qiydigan yorliq |
| Sana (`service_date`) | ⛔ **`font-mono` EMAS** | `useFormatter().dateTime()` locale formatini beradi |

---

## 8. Y-1: Kassir yig'ish ekrani (CASH-01, CASH-02, CASH-03)

### 8.1 Sahifaning holat mashinasi

| Holat | Ekranda | Keyingi qadam |
|-------|---------|---------------|
| `no-shift` | `EmptyState` «Ochiq smena yo'q» + `[Smenani ochish]` → `/collect/shift` | ⛔ To'lov **yozilmaydi** — sababi §10.1 |
| `idle` | Qidiruv maydoni **fokusda va bo'sh**; hint «Rasta raqamini kiriting» | Kod terish |
| `looking-up` | Summa maydonida `Skeleton` | — |
| `not-found` | `stall_not_found` sabab+tuzatish; maydon fokusda, **matn tanlangan** | Qayta terish |
| `ready` | Proyeksiya kartasi + to'lov turi + tasdiq | 2 va 3-qadam |
| `amount-unavailable` | Summa o'rnida **nomlangan sabab** (§9.4); faqat qarz to'lanadi | Qarzni olish yoki chiqish |
| `submitting` | Tasdiqda `Loader2`; ⛔ qulf **yopiq** | — |
| `written` | `Badge tone="success"` «To'lov yozildi» + to'lov qatori; ⛔ **fokus qidiruvga qaytadi** | Keyingi rasta |
| `error` | `role="alert"` sabab+tuzatish; ⛔ **kalit SAQLANADI** | `[Qayta yuborish]` |

⛔ **`no-shift` da to'lov yozilmasligi «jarayonni to'xtatish» EMAS** (mahsulot qoidasi #5): smena ochish **bitta bosish** va u shu ekrandan boshlanadi. Sabab — CASH-04 ning variance i `shift_id` ga tayanadi (D-27); smenasiz yozilgan kassir to'lovi variance dan **jimgina tushib qolardi**.

### 8.2 ⛔⛔ ≤3 bosish: ta'rif, mexanizm, va u qanday SANALADI

**D-18 ta'rifi:** (1) rasta raqamini kiritish/tanlash, (2) to'lov turi, (3) tasdiqlash. **Summa bosish EMAS** — u tarifdan keladi. Raqam terishdagi bosqichlar **bitta qadam**.

**Mexanizm — `data-collect-step` kontrakti** [QAROR]:

| Qadam | `data-collect-step` qiymati | Element | Nima sanaladi |
|-------|------------------------------|---------|----------------|
| 1 | `"stall"` | `<input>` (`stall-lookup.tsx`) | ⛔ **Raqam terish + `Enter` = BITTA qadam** (nechta belgi bo'lishidan qat'i nazar) |
| 2 | `"method"` | `<fieldset>` ichidagi radio (`payment-bar.tsx`) | Bitta bosish |
| 3 | `"confirm"` | `<button>` (`payment-bar.tsx`) | Bitta bosish |

⛔ **INVARIANT: har lahzada DOM'da AYNAN BITTA `[data-collect-step]` elementi bo'ladi.** Bu shunchaki uslub emas — u **sanoqni hosila qiladi** va ikki narsani bir vaqtda mexanik qiladi: (a) qadamlar soni, (b) «ikki asosiy element bir vaqtda» degan noaniqlikning yo'qligi.

**Sanoq testi** (`collect-session.test.tsx`, **G-20**) — naqsh `review-session.test.tsx:403-429` dan, lekin sanoq **DOM'dan hosila**:

```
let steps = 0; const visited = [];
while (!posted("/payments") && steps < 10) {
  const el = document.querySelectorAll("[data-collect-step]");
  expect(el).toHaveLength(1);              // (a) noaniqlik yo'q
  visited.push(el[0].dataset.collectStep);
  actOn(el[0]);                            // input -> type+Enter ; boshqa -> click
  steps += 1;
}
expect(posted("/payments")).toBe(true);
expect(steps).toBe(3);                                        // (b) AYNAN uch
expect(visited).toEqual(["stall", "method", "confirm"]);       // (c) tartib+to'plam tengligi
```

**Nega bu shakl tanlandi** [QAROR]:

1. ⛔ **«Uchta tugma bor» degan tekshiruv to'rtinchi qadam qo'shilganda YASHIL qoladi.** Sanoq esa **4** ni qaytaradi va test qizaradi — **hech kim ro'yxatni yangilamasdan**. Bu D-32 ning UI shakli.
2. ⛔ **`toBe(3)`, `toBeLessThanOrEqual(3)` EMAS.** Sanoq **2** ga tushsa ham test qizarishi kerak: 2 qadam degani tasdiqlash **avtomatik** bo'lgan, ya'ni **tasdiqsiz pul yozilgan**. «≤3» talab matnining chegarasi, o'lchovning maqsadi esa **aynan 3**.
3. **Ro'yxat qo'lda yozilmaydi:** `visited` DOM'dan yig'iladi, testda **e'lon qilinmaydi**. Faqat **kutilgan natija** yozilgan.

⚠ **Sanoq SAHIFA OCHILGANDAN boshlanadi** — navigatsiya, login, bozor tanlash sanoqdan **tashqarida**. Bu D-18 ning matni bilan mos (u oqim haqida gapiradi) va §4.6 dagi «boshlang'ich sahifa 7-fazaniki» qarorini **buzmaydi**.

### 8.3 1-qadam: rasta raqamini topish [MEROS: 02-UI-SPEC §6.9]

Kontrakt 2-fazada **allaqachon yozilgan va o'lchangan** — u qayta muhokama qilinmaydi:

> *«rasta raqami bo'yicha topish **≤2 ta o'zaro ta'sirda** … aynan bitta natija bo'lsa rasta kartasi darhol ochiladi … 6-fazaning ≤3 bosishi shundan bitta bosishni oladi.»* [KOD: `02-UI-SPEC.md:503-513`]

| Xossa | Qiymat | Sabab |
|-------|--------|-------|
| `autoFocus` | ✅ | Sahifa ochilishi bilan terish boshlanadi |
| `inputMode` | `"numeric"` | OS raqamli klaviaturasini ochadi (⛔ o'z klaviaturamiz **qurilmaydi**) |
| `enterKeyHint` | `"go"` | ⛔ `"search"` **emas** — bu **navigator**, filtr emas (§3.3) |
| `type` | `"text"` | ⛔ `"number"` **emas**: rasta kodi `12a`, `A-3` bo'lishi mumkin [KOD: `market.py:154-183`] |
| `autoComplete` | `"off"` | Brauzer tarixi boshqa bozorning kodini taklif qilardi |
| Balandlik | **56px** | §6.2 |
| Aynan bitta natija | ⛔ **darhol `ready`** — oraliq ro'yxat **yo'q** | 2-faza kontrakti |
| Bir nechta natija | Ro'yxat, `stalls.code_sort` tartibida [KOD: `market.py:154-183`] | Inson-raqamli tartib; ⚠ tanlash **ikkinchi** o'zaro ta'sir bo'ladi va bu 2-faza kontraktining ruxsat etilgan chegarasi (≤2) |
| Topilmadi | `not-found`, matn **tanlangan** holda fokusda | Qayta terish uchun `Ctrl+A` kerak emas |

⛔ **O'z raqamli klaviaturamiz QURILMAYDI** — 06-RESEARCH OQ-2 buni o'lchagan: raqam-only panel `A-3` kabi kodlarni **kiritib bo'lmaydigan** qilardi va bu «ba'zi rastalardan pul yig'ib bo'lmaydi» degan nosozlikka aylanardi.

### 8.4 2-qadam: to'lov turi — RADIOGROUP, ikki tugma emas [QAROR]

```
<fieldset data-collect-step="method">
  <legend>To'lov turi</legend>
  <input type="radio" name="method" value="cash" />      → Naqd     (Banknote)
  <input type="radio" name="method" value="terminal" />  → Terminal (CreditCard)
</fieldset>
```

| Qoida | Sabab |
|-------|-------|
| `<fieldset>` + `<legend>` | [MEROS: 05-UI-SPEC §13.2] Skrinrider guruhni **nomi bilan** e'lon qiladi |
| `type="radio"`, ⛔ **`checkbox` EMAS** | Bitta tanlov semantikasi. Va `checkbox` — §15.4 dagi ommaviy-amal skanining **taqiqlangan tokeni** |
| Ikkalasi **48px**, **teng kenglik**, **teng og'irlik** | §6.2 + §12.3: birortasini urg'ulash to'lov turini **buzardi**, u esa solishtiruv (`method`) uchun muhim ma'lumot |
| ⛔ **Standart tanlov YO'Q** | Naqd oldindan tanlansa, kassir terminal to'lovini **naqd deb yozib** yuborardi va solishtiruv jimgina buzilardi. Tanlanmagan holatda tasdiq `aria-disabled` |
| Klaviatura | `←`/`→` radiogroup ichida (native) | ⛔ Global `1`/`2` yorliqlari **YO'Q** — §14.4 |

### 8.5 ⛔ 3-qadam va undan KEYIN: fokus qaytishi — fazaning haqiqiy o'tkazuvchanlik kontrakti

Muvaffaqiyatli `POST /payments` dan **keyin**, **avtomatik** va **bosishsiz**:

1. To'lov qatori qo'shiladi (§8.8) va `role="status"` bilan e'lon qilinadi;
2. `[marketId, "billing-pending"]` prefiksi **keshdan chiqariladi** (`removeQueries`);
3. Rasta kodi maydoni **bo'shatiladi**;
4. ⛔ **Fokus qidiruv maydoniga qaytadi**;
5. To'lov turi tanlovi **nolga qaytadi**;
6. Idempotentlik kaliti **iste'foga chiqadi** (§8.7).

**Nega bu kontrakt darajasida** [QAROR]: kassirning kuni — bitta 3-qadamli oqim **emas**, uning **300–1000 marta takrori**. Agar har takrordan keyin qidiruv maydoniga qaytish uchun **bitta bosish** kerak bo'lsa, real sanoq **4 ga** chiqadi — D-18 rasmiy ravishda bajarilib, amalda **buzilgan** bo'lardi. `collect-session.test.tsx` ikkinchi takrorni ham o'lchaydi: ⛔ **ikkinchi to'lov ham AYNAN 3 qadam** (G-20).

### 8.6 ⛔ Summani o'zgartirish (D-19, CASH-02) — ATAYIN QIMMAT

**Kirish nuqtasi:** `ready` holatida, proyeksiya kartasi ostida, `variant="ghost"` `text-sm` havola-tugma «Summani o'zgartirish». ⛔ **`data-collect-step` YO'Q** — u baxtli yo'lning qadami emas.

**DL-1 ichidagi ketma-ketlik (minimum 3 qo'shimcha o'zaro ta'sir):**

| # | Element | Qoida |
|---|---------|-------|
| 1 | native `<select>` — **sabab-kod** | ⛔ **Yopiq ro'yxat.** Birinchi element — `placeholder` («Sabab tanlang»), `value=""`, va u **tanlov sifatida qabul qilinmaydi** |
| 2 | `<input inputMode="numeric">` — **yangi summa** | `soumSchema` bilan; ⛔ manfiy va nol **rad etiladi** (`money.py` chegarasi bilan bir xil) |
| 3 | `[Tasdiqlash]` | Sabab tanlanmasa **`aria-disabled`** (⛔ `disabled` emas — §14.3) |

**Nega qimmat bo'lishi KERAK** [QAROR]: override — **istisno**, va uning narxi baxtli yo'lning narxidan **yuqori** bo'lishi shart. Aks holda kassir har rastada uni bosib, tarifni **effektiv ravishda bekor** qilardi va BILL-01 ning butun ma'nosi (o'zgarmas, tarifga asoslangan patta) yo'qolardi. Uch qadam + dialog + `aria-disabled` to'sig'i — bu **anti-affordans** va u ataylab.

⛔ **Erkin matn maydoni YO'Q** (D-19). Sabab ochiq yozilgan: erkin matn hisobotda **guruhlanmaydi** va amalda **bo'sh qoladi**.
⛔ **`other` / `custom` sabab-kodi YO'Q** (06-RESEARCH OQ-3). U erkin matnni **qaytarib keltirardi** va hisobotda **eng katta guruh** bo'lib qolardi.

**Sabab-kodlar (boshlang'ich yopiq to'plam, `AdjustmentReason`)** — har biri **uchala tilda** (§13.5, G-24):

| Kod | uz-Latn yorlig'i |
|-----|-------------------|
| `late_review` | Nazoratchi keyin tasdiqladi |
| `ai_false_positive` | Tizim xato band dedi |
| `tariff_correction` | Tarif noto'g'ri kiritilgan |
| `partial_day` | Rasta kun o'rtasida bo'shatilgan |
| `director_waiver` | Direktor kechirdi |

### 8.7 ⛔⛔ Dublikat to'siq: ikki qatlam (D-21, D-22) — bu bo'lim UI ning eng qimmat qismi

**05-13 O'LCHADI:** uch tez bosish **uchta so'rov** yubordi, chunki `isPending` faqat **keyingi renderda** o'zgaradi. Server kafolati UI ni **to'xtatmadi**.

**Qatlam 1 — server (D-21):** `UNIQUE (market_id, idempotency_key)`; takror so'rov **o'sha to'lovni 200 bilan** qaytaradi, 409 emas.

**Qatlam 2 — mijoz (D-22):** `useRef` qulfi, naqsh `blind-session.tsx:92-137` dan **o'zgarishsiz** [O'LCHANDI: M-10]:

```
const submittedRef = useRef<string | null>(null);   // ⛔ isPending EMAS
const submit = useCallback((method: PaymentMethod) => {
  if (idempotencyKey === null) return;
  if (submittedRef.current === idempotencyKey) return;     // qulf
  submittedRef.current = idempotencyKey;
  pay.mutate({ idempotencyKey, method, stallCode, amountSoum },
    { onError: () => { submittedRef.current = null; } });   // ⛔ faqat xatoda ochiladi
}, [idempotencyKey, stallCode, amountSoum, pay]);
```

**Idempotentlik kaliti — hayot davri** [QAROR, D-21 ning UI shakli]:

| Hodisa | Kalitga nima bo'ladi | Sabab |
|--------|----------------------|-------|
| Rasta topildi (`ready` ga o'tish) | ⛔ **Tug'iladi** — `crypto.randomUUID()` | «To'lov varag'i ochilganda» (D-21) ning aniq lahzasi |
| Tarmoq xatosi / 5xx | ⛔ **SAQLANADI** | Qayta yuborish kassir uchun **ko'rinmas** bo'lishi kerak — server o'sha to'lovni 200 bilan qaytaradi |
| Foydalanuvchi `[Qayta yuborish]` bosdi | **SAQLANADI**, qulf **ochilgan** | O'sha |
| Summa DL-1 da o'zgartirildi | ⛔ **YANGI kalit** | Pitfall 4: bir xil kalit + boshqa summa → server **409 `idempotency_key_reused`**. Yangi kalit bu holatni **umuman tug'ilmasligini** ta'minlaydi |
| To'lov turi o'zgartirildi | ⛔ **YANGI kalit** | O'sha sabab (`method` — `request_fingerprint` ning qismi) |
| 2xx javob | **Iste'foga chiqadi** (`null`) | To'lov yozildi |
| Rasta kodi o'zgardi | **Iste'foga chiqadi** | Boshqa rasta — boshqa varaq |

⛔ **Kalit ekranda HECH QACHON ko'rsatilmaydi** (§7.2) va URL'da **yashamaydi** (§4.5).

**O'lchov (G-21), uchala kanal:**

| Kanal | Harakat | Kutilgan |
|-------|---------|----------|
| Sichqoncha/barmoq | Tasdiqni **uch marta tez** bosish | `apiFetch("/payments")` **AYNAN 1 marta** |
| Klaviatura | Tasdiqda `Enter` **bosib turish** (`repeat: true`) | ⛔ **0 qo'shimcha so'rov** — `decision-bar.tsx:101` ning `event.repeat` qoidasi bilan bir sinf |
| Xatodan keyin | 5xx → `[Qayta yuborish]` | **2-chi** so'rov ketadi va **o'sha kalit** bilan |

### 8.8 Yozilgan to'lov qatori va bekor qilish (CASH-03 / D-23)

⛔ **Oyna QAT'IY CHEGARALANGAN:** `GET /payments/recent` — **oxirgi 5 to'lov**, server tomonda **qat'iy**, `limit`/`offset`/`cursor` **parametri YO'Q**.

**Nega chegara serverda va nega u aynan 5** [QAROR — bu §10.3 ko'rligining ikkinchi yarmi]:

Kassir o'zi yozgan to'lovlarni ko'rishi **kerak** (bekor qilish uchun). Lekin agar u smenasining **hamma** to'lovlarini ko'rsa, ularni **qo'shib** tizim summasini chiqarib olardi — ya'ni §10.3 ning ko'r deklaratsiyasi **arifmetika bilan** buzilardi. 5 ta qator bekor qilish uchun yetadi (xato darhol sezilади) va jamlash uchun **ma'nosiz**. Sahifalash **yo'qligi** — mexanizm: yig'indi yo'lini **maydon yashirish** emas, **marshrutning imkoniyati** to'sadi.

| Qatorda ko'rinadi | Ko'rinmaydi |
|--------------------|-------------|
| Rasta kodi, summa (`font-mono`), to'lov turi ikonkasi, vaqt | ⛔ **Jami / yig'indi — HECH QANDAY shaklda** |
| `Badge tone="success"` yoki `tone="muted"` (bekor qilingan) | ⛔ Sotuvchi ismi, telefoni (§5.5) |
| `[Bekor qilish]` — faqat `kind='payment'` va hali bekor qilinmagan qatorda | ⛔ `[Tahrirlash]`, `[O'chirish]` — **umuman yo'q** (D-23) |

**DL-2 (bekor qilish):** yopiq sabab-kod (`ReversalReason`: `wrong_stall`, `wrong_amount`, `duplicate_entry`, `customer_refund`) + `ConfirmDialog` 1-daraja. Natija — **yangi qator** (`kind='reversal'`), eski qator **o'zgarmaydi** va ekranda `tone="muted"` bo'lib qoladi.

⛔ **Kassir FAQAT o'z ochiq smenasidagi to'lovni bekor qiladi.** Eski to'lovni bekor qilish yuzasi **6-fazada qurilmaydi** — marshruti ham, egasi ham yo'q; tabiiy egasi 7-fazaning case oqimi (§16.2).

---

## 9. Y-2: Kutilayotgan patta proyeksiyasi (BILL-05, D-17)

### 9.1 Proyeksiya NIMA EMAS — va nega bu birinchi navbatda yozilgan

06-RESEARCH C-8 o'lchadi: bugungi kun uchun `stall_slot_occupancy` **bo'sh** (u D+1 03:40 da to'ladi). Ya'ni:

| Vasvasa | Nega yo'q |
|---------|-----------|
| «Bugun band» belgisi | ⛔ Bugun **bilinmaydi**. Ko'rsatilsa, u **soxta ko'rsatkich** bo'lardi va kassir unga tayanib pul yig'ardi (yoki yig'masdi) |
| `occupied_slots` sanog'i | O'sha sabab |
| «Bu rasta pattaga tushadi» | ⛔ Bu **BILL-01 ning qaroricha** va u kechqurun chiqadi. Oldindan aytish — 05-UI-SPEC §16.1 ning taqig'ini buzardi |

**Proyeksiya = tarif + qoldiq** (BILL-05 matnining o'zi), **bandlik shartisiz**. Yozilgan hisob esa **bandlik-asosli**. Umumiy narsa — **pul yechimi** (`resolve_stall_day_money`), bandlik darvozasi emas (C-8).

### 9.2 ⛔⛔ Payload kontrakti — `charge_id` YO'Q, `tariff_id` HAM YO'Q

`GET /billing/pending?stall_code=NN` javobi. ⛔ **Kalitlar to'plami AYNAN quyidagi** (`z.strictObject`, to'plam tengligi bilan o'lchanadi — G-23):

```
{ stall_code, service_date, market_open,
  amount_soum, amount_unavailable_reason,
  outstanding_soum, total_due_soum }
```

| Maydon | Tip | Ma'nosi |
|--------|-----|---------|
| `stall_code` | `string` | ⛔ Kassir yuzasidagi **yagona identifikator** (§5.5) |
| `service_date` | `date` | «Qaysi kun uchun» — C-4 ning javobi |
| `market_open` | `boolean` | `market_is_open(market, today)` natijasi |
| `amount_soum` | `int \| null` | Bugungi patta. `null` — **nomlangan sabab bilan** |
| `amount_unavailable_reason` | `"market_closed" \| "tariff_missing" \| null` | ⛔ **Yopiq enum**, serverdan |
| `outstanding_soum` | `int` | Eski qarz (hisoblanadigan qoldiq — BILL-03) |
| `total_due_soum` | `int` | ⛔ **Serverda** hisoblangan yig'indi (§9.6) |

⛔ **YO'Q va yo'qligi o'lchanadigan maydonlar:**

| Yo'q maydon | Nega yo'q | Darvoza |
|-------------|-----------|---------|
| `charge_id` | **D-17.** Proyeksiya hisob emas → hisob identifikatori **mavjud emas**, yashirilgan emas | G-22 + G-23 |
| `tariff_id`, `category_id`, `valid_from` | ⛔ **D-20 ning kuchli shakli:** klientda tarif **kirish ma'lumoti yo'q** → summani hisoblash *taqiqlanmaydi*, **imkonsiz** | G-22 |
| `vendor_id`, `vendor_name`, `phone` | **C-10 + §5.5** | G-22 |
| `occupied_slots`, `is_billable` | **§9.1** — bugun bilinmaydi | G-22 |
| `balance`, `balance_soum` | **BILL-03** — saqlangan balans yo'q; nom ham yo'q | G-22 |

⛔ **Juftlangan invariant** (`z.refine` + G-23): `(amount_soum === null) === (amount_unavailable_reason !== null)`. Naqsh `NO_COVERAGE_IS_PAIRED_CHECK` dan [KOD: `models/occupancy.py:333-344`] — «sababsiz yo'q summa» ham, «summasi bor sabab» ham **ifodalab bo'lmaydi**.

### 9.3 ⛔⛔ Proyeksiya ↔ yozilgan hisob: yetti kanalli farq (WCAG 1.4.1)

Rang **hech qachon yagona signal emas**. Va eng kuchli kanal — oxirgisi.

| # | Kanal | **Kutilayotgan patta** (proyeksiya) | **Yozilgan hisob** |
|---|-------|--------------------------------------|--------------------|
| 1 | Yuza | `bg-warning/20` lenta + `border-l-4 border-warning` | `bg-surface` karta, lenta **yo'q** |
| 2 | Ikonka | `Clock` | `Receipt` |
| 3 | Sarlavha | «Kutilayotgan patta» | «Kunlik patta» |
| 4 | ⛔ To'liq jumla | «Bu kutilayotgan summa — hisob hali yozilmagan.» | «Yozilgan hisob · {sana}» |
| 5 | ⛔ Ma'lumot | `charge_id` **mavjud emas** → identifikator **ko'rsatilishi mumkin emas** | `charge_id` qisqa shakli, `font-mono text-xs` |
| 6 | ⛔ Amal | ⛔ **`[Dalilni ko'rish]` YO'Q** — dalil hisobda tug'iladi, proyeksiyada mavjud emas | `[Dalilni ko'rish]` → DL-3 |
| 7 | ⛔⛔ **Ekran** | ⛔ **`day = bugun`: yozilgan hisoblar bloki UMUMAN chizilmaydi** | ⛔ **`day < bugun`: proyeksiya bloki UMUMAN chizilmaydi** |

**Kanal 7 nima uchun eng kuchli** [QAROR]: C-3 ga ko'ra hisob **ertasi kuni 04:10 da** tug'iladi, ya'ni bugungi kun uchun yozilgan hisob **mavjud emas**. Bu tabiiy fakt UI'da **strukturaviy kafolatga** aylantiriladi: ikki blok **bir ekranda hech qachon uchrashmaydi**. Shundan keyin «kassir proyeksiyani kvitansiya deb o'qidi» xatosi uchun **fizik joy qolmaydi** — u ikkalasini yonma-yon **ko'ra olmaydi**. G-25 buni to'plam **disjunktligi** bilan o'lchaydi (`not.toContain` bilan emas — D-31).

### 9.4 ⛔ Eski summa yangi rasta ostida KO'RINMAYDI — «bayondan ko'ra yo'qlik»

Bu fazaning eng jim xato sinfi: kassir `14-C` ni terdi (15 000), keyin `15-A` ni terdi va **bir zumga** `15-A` kodi ostida **15 000** ko'rindi — u shu paytda `[Naqd]` va `[Tasdiqlash]` ni bosdi.

⛔ **Uch qatlamli to'siq** [QAROR]:

1. **Kesh:** `gcTime: 0`, `staleTime: 0` (§5.4) — proyeksiya **hech qachon** keshdan chiqmaydi.
2. ⛔ **Moslik sharti:** summa **faqat** `data.stall_code === enteredCode` bo'lganda chiziladi. Aks holda — `Skeleton`. Ya'ni server javobining **o'zi** kalitni tasdiqlaydi, kesh emas.
3. **Qadam bloki:** `data-collect-step="method"` elementi `ready` holatida **paydo bo'ladi**; `looking-up` da DOM'da **umuman yo'q** → §8.2 invarianti tufayli 2-qadamni **bosish imkoni yo'q**.

**`amount_unavailable_reason` ko'rinishi** (D-20: «yo'q summani ko'rinadigan qil, taxmin qilma»):

| Sabab | Ekranda | To'lanadigan |
|-------|---------|--------------|
| `market_closed` | `bg-warning/20 text-text` + `CalendarDays` + «Bugun bozor yopiq — bugungi patta hisoblanmaydi» | Faqat `outstanding_soum` |
| `tariff_missing` | `role="alert"` sabab+tuzatish: «Bu rastaning bugungi tarifi belgilanmagan» / «Tarif sahifasida toifa narxini kiriting» | Faqat `outstanding_soum` |
| So'rov xatosi | ⛔ **Summa umuman chizilmaydi** + `[Qayta urinish]` | ⛔ **Hech nima** — tasdiq `aria-disabled` |

⛔ **Klient «taxminiy summa» KO'RSATMAYDI** va «oxirgi ma'lum summa» ni ham ko'rsatmaydi. Yo'q summa — **yo'q summa**.

### 9.5 Bozor kesimi (direktor) — `/billing?day=bugun`

`GET /billing/pending` (rasta parametrisiz) → `components/billing/pending-summary.tsx`:

| Ko'rsatkich | Manba | Uslub |
|-------------|-------|-------|
| Kutilayotgan bugungi patta (jami) | server yig'indisi | Display + `font-mono` |
| Eski qarz (jami) | server yig'indisi | Body + `font-mono` |
| Kutilayotgan rasta soni | server sanog'i | Body |
| ⛔ Kanal 1–4 (§9.3) | — | Lenta + `Clock` + «Kutilayotgan patta» + to'liq jumla |

**Yangilanish** [QAROR]: ⛔ **avtomatik taymer YO'Q.** `refetchOnWindowFocus` standart holida qoladi va sahifada `[Yangilash]` tugmasi + **oxirgi olingan vaqt** ko'rsatiladi. Sabab: direktor raqamni **o'qib turgan paytda** uni jimgina o'zgartirib qo'yadigan taymer — «men boshqa raqam ko'rgandim» degan nizoning manbai. Qo'lda yangilash + vaqt tamg'asi buni **ko'rinadigan** qiladi.

⛔ Bu blok **`day = bugun`** da **faqat**; boshqa kunda **umuman chizilmaydi** (§9.3 kanal 7).

### 9.6 ⛔ Qarz bilan birga olish — bir bosishga qimmat, LEKIN arifmetikasiz

`ready` holatida ikki summa ko'rinadi va **birinchisi standart**:

| Tanlov | Yuboriladigan summa | Narx |
|--------|---------------------|------|
| **Standart** — bugungi patta | `amount_soum` | 3 qadam (§8.2) |
| `[Qarzni ham olish]` | ⛔ **`total_due_soum`** — **serverdan** | 4 qadam (bitta qo'shimcha bosish) |

**Nega standart faqat bugungi patta** [QAROR]: kassirning kunlik ishi — **bugungi pattani** yig'ish. Agar standart `total_due_soum` bo'lsa, 45 000 qarzi bor sotuvchi bugungi 15 000 ni **≤3 bosishda to'lay olmasdi** — kassir DL-1 (override) ga majbur bo'lardi, ya'ni **normal holat istisno yo'lidan** o'tardi. Bu dizayn xatosi.

⛔ **`amount_soum + outstanding_soum` KLIENTDA HISOBLANMAYDI** — shu sababdan `total_due_soum` **serverdan** keladi (§9.2). Aks holda `[Qarzni ham olish]` D-20 ni **bitta qo'shish amali** bilan buzardi. G-22 klientda pul arifmetikasi uchun kirish ma'lumotini **yo'q qilib** buni qo'llab-quvvatlaydi.

⚠ **Qisman va ortiqcha to'lov** (06-RESEARCH OQ-4 / A4): qisman **ruxsat** (`amount_soum` shunchaki kichikroq kredit), ortiqcha ham **ruxsat** va u `outstanding_soum < 0` bo'lib kelganda ekranda `Badge tone="success"` **«Avans»** bo'lib ko'rinadi. ⛔ Bloklash kassirni pulni **umuman yozmaslikka** majburlardi.

---

## 10. Y-3: Smena va ko'r naqd deklaratsiyasi (CASH-04, D-25, D-26)

### 10.1 Smena ochish

`GET /shifts/open` → ikki holat, uchinchisi yo'q:

| Holat | Ekranda | Amal |
|-------|---------|------|
| Ochiq smena **yo'q** | `EmptyState` + `[Smenani ochish]` (`DoorOpen`) | `POST /shifts` |
| Ochiq smena **bor** | Karta: boshlangan vaqt + `[Smenani yopish]` | §10.2 |

⛔ **Bir vaqtda bitta ochiq smena** — strukturaviy (D-27, qisman `UNIQUE` indeks). UI ikkinchi «ochish» tugmasini **ko'rsatmaydi**; server `shift_already_open` qaytarsa, u §13.7 dagi sabab+tuzatish bilan chiziladi.

⛔ **Ochiq smena kartasida KO'RINMAYDI:** to'lovlar soni, yig'ilgan summa, o'rtacha, «bugungi natija» — **hech qanday shaklda**. Sabab §10.3.

### 10.2 ⛔⛔ Ko'r naqd deklaratsiyasi — forma

`components/collect/shift-close-form.tsx`:

| Element | Xossa | Sabab |
|---------|-------|-------|
| Sarlavha | «Smenani yopish» (Heading) | — |
| ⛔ **Yo'riqnoma jumlasi** | «Qo'lingizdagi naqdni sanab kiriting. Tizim summasini ko'rsatmaydi — farqni direktor ko'radi.» | ⛔ Ko'rlik **tushuntirilishi shart**: tushuntirilmagan ko'rlik «tizim buzuq» deb o'qiladi va kassir raqamni **taxmin qilib** kiritardi |
| Kirish maydoni | `<input inputMode="numeric">`, `autoFocus`, **56px**, `Field` bilan | §6.2 |
| Validatsiya | `soumSchema`; ⛔ manfiy **rad etiladi**; **0 RUXSAT** | Nol naqd — real holat (butun smena terminal bo'lgan kun) va uni rad etish kassirni **yolg'on son** kiritishga majburlardi |
| Tasdiq | `[Yopish]` → **DL-4** (`ConfirmDialog` 1-daraja) | Deklaratsiya **o'zgarmas** — tasdiq shundan |
| DL-4 matni | «Deklaratsiya yozilgach o'zgartirilmaydi. {summa} kiritildi — yopilsinmi?» | Oqibat **summani takrorlab** aytiladi |

⛔ **Fokus DL-4 da destruktiv tugmada EMAS** — mavjud `ConfirmDialog` xulqi [MEROS: 05-UI-SPEC §3.1].

### 10.3 ⛔⛔ Javob kalitlari to'plami — YO'QLIK, YASHIRISH EMAS

`POST /shifts/{id}/close` javobi. ⛔ **Kalitlar to'plami AYNAN** (`z.strictObject` + to'plam tengligi — **G-7**, **G-23**):

```
{ id, status, declared_soum, closed_at }
```

⛔ **YO'Q va yo'qligi TO'PLAM TENGLIGI bilan o'lchanadigan maydonlar:**

| Yo'q maydon | Nega |
|-------------|------|
| `system_soum`, `system_total_soum`, `expected_soum` | **D-25.** Ko'rlikning to'g'ridan-to'g'ri buzilishi |
| ⛔ `variance_soum`, `variance` | ⛔ **BU QAROR RESEARCH SC#5(d) NI QAT'IYLASHTIRADI — §10.4 ni o'qing** |
| `payment_count`, `cash_count`, `terminal_soum` | Ular **yig'indiga olib boradigan** kirish ma'lumoti |

**Nega CSS/shartli render mexanizm EMAS** (Pitfall 6): brauzerga yetgan maydon **o'qiladi** — DevTools, tarmoq paneli, React DevTools, `JSON.stringify`. «Ko'rsatmayapmiz» — kod-ko'rik da'vosi, **o'lchov emas**. Va `null` qilib yuborish ham **yaramaydi**: `null` maydonning **borligini** tasdiqlaydi va keyingi ijrochi uni to'ldirardi.

**Kassir yopgandan keyin ko'radigan narsa — aynan uchtasi:** `Badge tone="success"` «Deklaratsiya yozildi» · kiritilgan summa (`font-mono`) · `[Yangi smena ochish]`. ⛔ Boshqa hech nima: na variance, na «to'g'ri/noto'g'ri», na tizim summasi.

### 10.4 ⛔ Variance KASSIRGA ko'rsatilmaydi [QAROR — research SC#5(d) ni qat'iylashtiradi]

06-RESEARCH SC#5(d) shunday deydi: *«variance **serverda** hisoblangan va `declared > system` holatida ham **qaytariladi** (D-26)»*. **Kimga** qaytariladi — yozilmagan. Bu hujjat javob beradi:

| Kim | Variance ni ko'radimi | Marshrut |
|-----|------------------------|----------|
| **Kassir** | ⛔ **YO'Q** | `POST /shifts/{id}/close` javobida **maydon yo'q** |
| **Direktor / bozor admini** | ✅ **HA, ikki tomonlama** | `GET /shifts?day=` → §11.5 |

**Uch sabab:**

1. ⛔ **Variance tizim summasini OSHKOR QILADI.** `system = declared − variance` — bitta ayirish. Ya'ni variance ni qaytarish `system_soum` ni qaytarish bilan **matematik jihatdan bir xil** va D-25 ni **hisob-kitob bilan** buzardi.
2. ⛔ **Keyingi smenaning ko'rligini buzadi.** Kassir har kun variance ni ko'rsa, bir haftada «tizim odatda ~1,2 mln deydi» degan **langar** hosil qiladi va sanashdan oldin **taxmin** qiladi. Bu 05-RESEARCH §C.8 dagi ankorlash mexanizmining aynan o'zi.
3. **Bu smenada tuzatish yo'li YO'Q.** Deklaratsiya **o'zgarmas** (D-25) va variance **avtomatik to'g'rilanmaydi** (D-26). Ya'ni kassirga variance ni ko'rsatish **hech qanday harakatni ochmaydi** — u faqat ma'lumot oqadi.

⚠ **Mezon o'lchanishi SAQLANADI:** SC#5(d) «`declared > system` holatida ham qaytariladi» talabini `GET /shifts?day=` **qondiradi** va u aynan shu marshrutda o'lchanadi. Reja bu qatorni **o'qishi** va mezon testini shu marshrutga qaratishi shart — aks holda u yo'q maydonni izlab qizarardi.

⚠ **Ochiq yozilgan narx:** kassir o'z kamomadini **darhol** bilmaydi. Bu qabul qilinadi: naqdni topshirish paytida direktor variance ni ko'radi va suhbat **o'sha yerda**, ikki tomon ishtirokida bo'ladi — bu 06-CONTEXT D-02 ning nizo modeliga **mos**.

---

## 11. Y-4: Hisoblar, qarz, anomaliya va dalil (BILL-02, BILL-03, BILL-04)

### 11.1 Kun tanlagichi — standarti KECHA [QAROR]

`components/billing/day-picker.tsx`, `?day=YYYY-MM-DD` (`nuqs`):

| Qoida | Qiymat | Sabab |
|-------|--------|-------|
| Standart | ⛔ **kecha** (`business_today() − 1`) | C-3: hisob **D+1 04:10** da tug'iladi. Standarti **bugun** bo'lsa, sahifa **har doim bo'sh** ochilardi va direktor «tizim ishlamayapti» degan xulosaga kelardi |
| Maksimum | **bugun** | Kelajak kuni uchun hisob **imkonsiz** (`CHECK (service_date <= business_date)`) |
| `day = bugun` | ⛔ Faqat **proyeksiya** (§9.5) + variance | §9.3 kanal 7 |
| `day < bugun` | Hisoblar + anomaliya + variance; ⛔ proyeksiya **chizilmaydi** | O'sha |

### 11.2 Sahifaning vertikal tuzilishi

| # | Blok | Manba | `day = bugun` | `day < bugun` |
|---|------|-------|----------------|----------------|
| A | Kun tanlagichi | — | ✅ | ✅ |
| B | ⛔ Kutilayotgan patta (proyeksiya) | `GET /billing/pending` | ✅ | ⛔ **chizilmaydi** |
| C | Yozilgan hisoblar va qoldiq | `GET /billing/charges?day=` | ⛔ **chizilmaydi** | ✅ |
| D | Anomaliyalar | `GET /billing/anomalies?day=` | ⛔ **chizilmaydi** | ✅ |
| E | Smena variance | `GET /shifts?day=` | ✅ | ✅ |

**(C) Yozilgan hisoblar** — jadval, ustunlari **marshrut bergan maydonlardan**:

| Ustun | Manba | Uslub |
|-------|-------|-------|
| Rasta | `stall_code` | Body |
| Sotuvchi | ⛔ `vendor_id` → **klientda** `GET /vendors` bilan join (§5.5) | Body |
| Tarif summasi | `tariff_amount_soum` (D-09) | `font-mono` |
| Hisob summasi | `amount_soum` | `font-mono` |
| Qoldiq | `outstanding_soum` (**hisoblanadigan** — BILL-03) | `font-mono` |
| — | `[Tafsilot]` → DL-3 | `variant="ghost"` |

⛔ **Tarif summasi va hisob summasi TENG bo'lsa, ikkinchi ustun ko'rsatilmaydi** (bitta ustun, «Summa»). Farq bo'lsa **ikkalasi ham** ko'rinadi — farq **tuzatish bo'lganini** aytadi va u DL-3 da ochiladi. Sabab: doim ikki bir xil ustun ko'rsatish direktorni «nima farqi?» deb o'ylashga majburlardi.

⛔ **Hech qayerda `balance` NOMLI ustun yo'q** (BILL-03) — qoldiq **hisoblanadigan ko'rinish**. G-22 bu nomni klient kodida ham **taqiqlaydi**.

### 11.3 DL-3 — hisob tafsiloti va dalil-kadrga o'tish (BILL-02, SC#2)

`GET /billing/charges/{id}` **[TALAB]**. Dialog besh bo'limdan iborat va **har bir qator marshrut bergan maydondan oziqlanadi**:

| Bo'lim | Maydonlar | Yo'q bo'lsa nima bo'ladi |
|--------|-----------|---------------------------|
| **1. Sarlavha** | `service_date`, `stall_code`, `charge_id` (qisqa, `font-mono`) | — |
| **2. Summa** | `tariff_amount_soum`, `amount_soum`; ⛔ `tariff_id` **KO'RSATILMAYDI** (direktorga ham ma'nosiz identifikator) | — |
| ⛔ **3. O'zgarmaslik jumlasi** | «Bu hisob o'zgartirilmaydi. Tuzatish alohida yozuv sifatida qo'shiladi.» | ⛔ **Har doim ko'rinadi** — tuzatish bo'lmasa ham |
| **4. Tuzatishlar** | `charge_adjustments[]`: `direction`, `amount_soum`, `reason_code` (tarjima qilingan), aktor, `created_at` | ⛔ Bo'sh bo'lsa — **«Tuzatish yo'q»** jumlasi (yashirilmaydi: **nol — natija**) |
| **5. Dalil kadrlari** | `evidence[]`: har element **`snapshot_id`** + slot vaqti | ⛔ **`snapshot_id` bo'lmasa qator UMUMAN chizilmaydi** — na placeholder, na «yuklanmadi» |

⛔ **5-bo'limning qoidasi 05-14 ning darsidan**: DL-5 ning slot qatorlari **marshrut bermagani uchun** olib tashlangan edi; to'qish (stub) va bo'sh jadval (placeholder) **ikkalasi ham rad etilgan**. Bu yerda ham xuddi shunday: agar `GET /billing/charges/{id}` `snapshot_id` bermasa, **dalil bo'limi mavjud emas** va bu UI-SPEC da **[TALAB]** sifatida turadi — «yo'qolgan funksiya» sifatida emas.

⛔ **Dalil kadri — mavjud yagona marshrut, yangi huquq YO'Q** [O'LCHANDI: M-8]:

| Qoida | Qiymat |
|-------|--------|
| Rasm manzili | ⛔ **AYNAN** `/api/v1/snapshots/{snapshot_id}/image` |
| Huquq | ⛔ **Mavjud** `require_any_permission(CAMERA_VIEW, OCCUPANCY_REVIEW)` — `director` va `market_admin` ikkalasida ham `camera_view` **bor** [KOD: `rbac.ts:88-108`] |
| `SNAPSHOT_EVIDENCE_FRAME_ROUTES` | ⛔ **TEGILMAYDI** — aynan bitta marshrut bo'lib qoladi (C-9) |
| Ramka | `bg-text` letterbox + `text-bg` (15,6:1) [MEROS: 03-UI-SPEC §2.3] |
| `crossOrigin` | ⛔ **QO'YILMAYDI** — u boshqa manba borligini anglatardi [MEROS: 05-UI-SPEC §14.2] |
| Yuklab olish / ulashish / `canvas` → `toDataURL()` | ⛔ **YO'Q** [MEROS: 05-UI-SPEC §14.2] |
| `presign`, `X-Amz`, `s3.`, `seaweed`, `:8333` | ⛔ **Klient kodida yo'q** — 4-fazadagi grep darvozasi davom etadi |

⛔ **Nega dalil kadri KASSIR yuzasida yo'q** [QAROR — bu fazaning eng arzon xavfsizlik yutug'i]: kassir pul yig'adi, hukm chiqarmaydi. Kadr uning ishida **hech narsani o'zgartirmaydi**, lekin uni ko'rsatish `camera_view` ni kassirga berishni talab qilardi — yoki, yomoni, `require_any_permission()` ning **yopiq to'plamini** kengaytirishni (`test_personal_data_coverage.py:674-706` uni **aynan bitta marshrutga** qulflagan). Ya'ni C-9 ning eng qimmat to'sig'i shu **bitta ko'lam qarori** bilan umuman tug'ilmaydi.

### 11.4 Anomaliya ro'yxati (BILL-04) — uch `kind`, uch YORLIQ, hech qachon qo'shilmaydi

| `kind` | Yorliq | `tone` | Ikonka | Dalil |
|--------|--------|--------|--------|-------|
| `unassigned_occupied` | «Ro'yxatga olinmagan savdo» | `warning` | `UserX` | ✅ **majburiy** → kadr |
| `closed_day_occupied` | «Yopiq kunda savdo» | `warning` | `CalendarDays` | ✅ **majburiy** → kadr |
| `no_coverage_stall` | ⛔ «Qamrovsiz rasta» | `neutral` | `CircleSlash` | ⛔ **YO'Q** — affordans **umuman chizilmaydi** |

⛔ **Uchalasi ALOHIDA sanaladi va bitta «anomaliya» soniga qo'shilmaydi** [MEROS: 05-UI-SPEC §11.4 qoidasi]. Sabab D-05 da ochiq yozilgan: *«ko'ra olmadik» ≠ «band, lekin biriktirilmagan»*. Ikkisini qo'shish **ko'r nuqtadan tushum da'vosi to'qish** bo'lardi.

⛔ **`no_coverage_stall` matnida «bo'sh» so'zi YO'Q** — 5-fazaning G-15 mulohazasi bu yerda ham amal qiladi: farq DB'da bor, lekin **matn darajasida** yo'qolsa, hisobot jimgina noto'g'ri o'qilardi va bu xatoni **hech qanday sxema ushlamaydi**. G-26 buni uchala locale'da o'lchaydi.

⛔ **Dalil affordansining yo'qligi — `disabled` EMAS, chizilmaydi.** C-12 ning juftlangan `CHECK` i (`(kind = 'no_coverage_stall') = (occupancy_event_id IS NULL)`) UI'da **shu shaklda** takrorlanadi: o'chirilgan tugma «kadr bor, lekin ochilmayapti» deb yolg'on gapirardi.

⛔ **Case oqimi YO'Q:** holat, mas'ul, qaror, izoh, `[Ko'rildi]` — **birortasi ham**. 7-faza egasi (§16.1).

### 11.5 Smena variance (CASH-04, D-26) — ikki tomonlama va YOZUV YUZASI 0

`GET /shifts?day=` **[TALAB]** → `components/billing/variance-list.tsx`:

| Ustun | Manba | Uslub |
|-------|-------|-------|
| Smena | `opened_at` – `closed_at` | Body |
| Kassir | ⛔ `cashier_id` → **klientda** `GET /users` bilan join (§5.5) | Body |
| Deklaratsiya | `declared_soum` | `font-mono` |
| Tizim | `system_soum` | `font-mono` |
| ⛔ **Farq** | `variance_soum` — **serverda** hisoblangan | `variance-cell.tsx` |

⛔ **`variance-cell.tsx` — uch yo'nalish, har biri UCH kanalda** (WCAG 1.4.1):

| Holat | Rang kanali | Ikonka | ⛔ Matn kanali |
|-------|-------------|--------|----------------|
| `variance < 0` | `bg-danger/12 text-danger-text` | `TrendingDown` | **«Kamomad»** |
| `variance > 0` | `bg-warning/20 text-text` | `TrendingUp` | ⛔ **«Ortiqcha»** |
| `variance = 0` | `Badge tone="success"` | `Equal` | **«Mos keldi»** |

⛔ **`declared > system` (ortiqcha) TENG OG'IRLIKDA ko'rsatiladi va JIM YUTILMAYDI** — D-26 ning so'zma-so'z talabi: *«Ortiqcha naqd ham signal — uni jimgina yutish kamomadni yashirish bilan bir xil xato.»* G-27 **ikkala yo'nalishni ham** o'lchaydi.

⛔ **`abs(variance)` KO'RSATILMAYDI** — ishora **ma'no tashiydi** (Pitfall 7).

⛔ **Yozuv yuzasi AYNAN NOL:** bu blokda `[To'g'rilash]`, `[Tasdiqlash]`, `[Izoh qo'shish]`, `[Kechirish]` — **birortasi ham yo'q**. D-26: variance **hech qachon avtomatik to'g'rilanmaydi**, va qo'lda to'g'rilash yo'li ham 6-fazada **ochilmaydi** (marshruti yo'q). G-27 buni **interaktiv element to'plamining tengligi** bilan o'lchaydi.

⚠ **Smenasiz to'lovlar alohida sanoq** (06-RESEARCH OQ-6 / A5): `shift_id IS NULL` bo'lgan to'lovlar variance ga **kirmaydi** (ular kassir qutisiga tushmagan) va jadval ostida **alohida qator** bilan ko'rsatiladi: «Smenasiz to'lovlar: {n} · {summa}». ⛔ Ko'rsatilmasa, ular **jimgina yo'qolardi** (D-14 ruhi: o'lchanadigan miqdor).

⚠ **Variance chegarasi va alerti YO'Q** (06-RESEARCH OQ-7 / A6): `alert_key = 'shift_variance'` **yozilmaydi**. Chegara kelishilmagan va u **bozor bo'yicha sozlanadigan** bo'lishi kerak — 8-faza egasi (§17 O-06).

---

## 12. Rang kontrakti (60/30/10)

### 12.1 Taqsimot — o'zgarishsiz, yangi token YO'Q

| Rol | Token | Qiymat [KOD: `globals.css:33-85`] | 6-fazada qayerda |
|-----|-------|-----------------------------------|------------------|
| **Dominant (60%)** | `--color-bg` | `oklch(0.985 0 0)` | Sahifa foni |
| **Ikkilamchi (30%)** | `--color-surface` | `oklch(1 0 0)` | Kartalar, dialoglar, jadvallar, ⛔ **yozilgan hisob kartasi** |
| | `--color-surface-muted` | `oklch(0.968 0 0)` | `Skeleton`, bekor qilingan to'lov qatori, yopilgan smena kartasi |
| **Aksent (10%)** | `--color-accent` | `oklch(0.56 0.19 255)` | §12.3 — **to'rt element** |
| **Destruktiv** | `--color-danger` | `oklch(0.58 0.21 27)` | Kamomad katagi, bekor qilish tasdig'i, o'zgarmaslik xatosi |
| **Ogohlantirish** | `--color-warning` | `oklch(0.78 0.15 85)` | ⛔ **Faqat `bg-warning/20` sifatida** — §12.2 |
| **Muvaffaqiyat** | `--color-success` | `oklch(0.63 0.16 150)` | `Badge tone="success"`: «To'lov yozildi», «Avans», «Mos keldi» |
| **Kadr ramkasi** | `bg-text` + `text-bg` | 15,6:1 | DL-3 dalil kadri letterbox'i |

**Yangi token kiritilmaydi va yangi rang juftligi so'ralmaydi.**

### 12.2 `--color-warning` matn sifatida ISHLATILMAYDI

Sariq tintdagi matn — `bg-warning/20 text-text` (o'lchangan **15,64:1**) [KOD: `badge.tsx:17-25`]. `--color-warning` oq fonda **2,03:1** — falokat.

6-fazada bu **besh joyda** muhim va beshalasi ham `bg-warning/20 text-text`:

1. ⛔ **Kutilayotgan patta lentasi** (§9.3 kanal 1) — fazaning eng muhim ogohlantirishi
2. «Bugun bozor yopiq» (§9.4)
3. «Ro'yxatga olinmagan savdo» va «Yopiq kunda savdo» badge'lari (§11.4)
4. ⛔ **«Ortiqcha» variance katagi** (§11.5)
5. «Avans» tushuntirish jumlasi (§9.6)

### 12.3 ⛔ Aksent — to'rtta element, beshinchisi yo'q [QAROR]

Aksent rang **faqat** quyidagilarda:

1. **Fokus halqasi** (`:focus-visible outline`) — barcha interaktiv elementlar;
2. **Faol maydon chegarasi va halqasi** (`focus-visible:border-accent`, `ring-accent/25`);
3. **Joriy navigatsiya elementi** — faqat mobil pastki panelda;
4. ⛔ **`[To'lovni tasdiqlash]` — `/collect` dagi to'lov tasdig'i.** Fazadagi **yagona** aksent fonli tugma.

> ⛔ **Nega tasdiqlash tugmasi aksent OLADI — 5-fazadan FARQLI [QAROR]**
>
> 05-UI-SPEC §10.3 javob tugmalarini aksentsiz qildi va sabab **ankorlash** edi: ko'z birinchi navbatda aksentga tushadi, shosha-pisha bosishda qo'l ham — ya'ni **tanlovga ta'sir qilardi**.
>
> Bu yerda vaziyat **teskari**: `[To'lovni tasdiqlash]` — **tanlov emas, oqibat**. Uning raqobatchisi yo'q (to'lov turi allaqachon tanlangan), ya'ni urg'u **hech narsani buzmaydi**. Buning ustiga u kuniga 300–1000 marta, **quyoshda**, **bir qo'lda** bosiladi — eng yuqori kontrast va eng katta nishon (56px, §6.2) shu yerda **funksional talab**.
>
> ⛔ **`[Naqd]` / `[Terminal]` esa AKSENT OLMAYDI** — ular **tanlov** va ular ustida 5-fazaning ankorlash mulohazasi **to'liq kuchda**: birortasini urg'ulash to'lov turini buzardi, u esa bank/terminal solishtiruvi uchun muhim ma'lumot.

**Aksent ishlatilMAYDIGAN joylar (aniq taqiq):** to'lov turi tugmalari · `[Summani o'zgartirish]` · `[Bekor qilish]` · `[Qarzni ham olish]` · smena ochish/yopish · deklaratsiya maydoni · har qanday summa raqami · qarz raqami · variance katagi · anomaliya badge'lari · kun tanlagichi · jadval sarlavhalari · `[Tafsilot]` · dalil kadri ramkasi.

### 12.4 Rang hech qachon YAGONA signal emas (WCAG 1.4.1)

| Holat | Rang kanali | Qo'shimcha kanal 1 | Qo'shimcha kanal 2 |
|-------|-------------|--------------------|--------------------|
| ⛔ **Kutilayotgan patta** | `bg-warning/20` + `border-l-4` | `Clock` ikonkasi | ⛔ **To'liq jumla** «hisob hali yozilmagan» |
| **Yozilgan hisob** | `bg-surface` | `Receipt` ikonkasi | `charge_id` + «Yozilgan hisob · {sana}» |
| **To'lov yozildi** | `tone="success"` | `CircleCheckBig` | Badge matni + `role="status"` e'loni |
| **Bekor qilingan to'lov** | `tone="muted"` | `Undo2` | Badge matni «Bekor qilingan» |
| ⛔ **Kamomad** | `bg-danger/12 text-danger-text` | `TrendingDown` | ⛔ Katak **yorlig'i** «Kamomad» |
| ⛔ **Ortiqcha** | `bg-warning/20 text-text` | `TrendingUp` | ⛔ Katak **yorlig'i** «Ortiqcha» |
| **Mos keldi** | `tone="success"` | `Equal` | Badge matni «Mos keldi» |
| **Ro'yxatga olinmagan savdo** | `tone="warning"` | `UserX` | Badge matni — **to'liq, qisqartirilmagan** |
| **Yopiq kunda savdo** | `tone="warning"` | `CalendarDays` | Badge matni |
| ⛔ **Qamrovsiz rasta** | `tone="neutral"` | `CircleSlash` | Badge matni «Qamrovsiz rasta» |
| **Avans** | `tone="success"` | `PiggyBank` | Jumla «Ortiqcha to'langan — avans» |
| **Bozor yopiq** | `bg-warning/20` | `CalendarDays` | To'liq jumla |
| **Summa yo'q** | — (rang **yo'q**) | ⛔ `Skeleton` yoki `role="alert"` | ⛔ **Nomlangan sabab** (§9.4) |

> ⛔ **«Kamomad» va «Ortiqcha» turli `tone` oladi va bu MUZOKARASIZ.** Ikkalasi ham «variance ≠ 0» ga olib keladi, lekin **ma'nosi qarama-qarshi**: biri — pul **yetmadi**, ikkinchisi — pul **ortiqcha** (va u ham xato manbai). Bir xil ko'rinsa, D-26 ning butun mazmuni yo'qolardi.

---

## 13. Matn (copywriting) kontrakti

### 13.1 ⛔ Atama qarorlari — kod bir narsa deydi, ekran boshqa narsa

| Kod / DB | ⛔ Ekranda | Nega |
|----------|-----------|------|
| `kind = 'reversal'`, «storno» | ⛔ **«Bekor qilish»** / «Bekor qilingan to'lov» | «Storno» — buxgalteriya atamasi. Karmana kassiri uni **o'qimaydi**; u qilayotgan ishning nomi «bekor qilish». Kod `reversal` da **qoladi** |
| `variance` | ⛔ **«Farq»**, natijasi «Kamomad» / «Ortiqcha» | «Variance» hech qanday ma'no tashimaydi |
| `idempotency_key`, «idempotent» | ⛔ **«Qayta yuborish dublikat yaratmaydi»** | Mexanizm nomi emas, **kafolat** aytiladi |
| `projection` | ⛔ **«Kutilayotgan»** | O'z-o'zini tushuntiradigan shakl |
| `daily_charges` | ⛔ **«Kunlik patta»** / «Yozilgan hisob» | «Patta» — mahalliy atama va u talab matnining o'zida ishlatilgan |
| `outstanding_soum` | ⛔ **«Eski qarz»** (kassirga) / «Qoldiq» (direktorga) | Kassirga **harakat** ma'nosi kerak, direktorga **hisob** ma'nosi |

[MEROS: 05-UI-SPEC §12.1 naqshi — kod nomi va ekran matni **ataylab** ajraladi va bu jadval ajralishning **reyestri**.]

### 13.2 Namespace'lar va navigatsiya

| Namespace | Egasi |
|-----------|-------|
| `collect.*` | Y-1, Y-2 (rasta kesimi), Y-3 — **kassir yuzasi** |
| `billing.*` | Y-2 (bozor kesimi), Y-4 — **direktor yuzasi** |
| `collect.errorCause.*` / `collect.errorFix.*` | §13.7 |
| `billing.errorCause.*` / `billing.errorFix.*` | §13.7 |
| `audit.actions.*` | Yangi `AuditAction` a'zolari (§13.6) |

| Kalit | uz-Latn |
|-------|---------|
| `nav.collect` | Yig'ish |
| `nav.billing` | Patta hisobi |

### 13.3 Kassir yuzasi (`collect.*`) — shipping matn

| Kalit | uz-Latn |
|-------|---------|
| `collect.title` | Patta yig'ish |
| `collect.stallLabel` | Rasta raqami |
| `collect.stallHint` | Raqamni kiritib «Enter» bosing |
| `collect.pendingTitle` | ⛔ Kutilayotgan patta |
| `collect.pendingNotice` | ⛔ Bu kutilayotgan summa — hisob hali yozilmagan. |
| `collect.todayAmount` | Bugungi patta |
| `collect.oldDebt` | Eski qarz |
| `collect.totalDue` | Bugungi patta va qarz |
| `collect.noDebt` | Qarzi yo'q |
| `collect.advance` | Ortiqcha to'langan — avans |
| `collect.methodLegend` | To'lov turi |
| `collect.methodCash` | Naqd |
| `collect.methodTerminal` | Terminal |
| `collect.confirm` | To'lovni tasdiqlash |
| `collect.withDebt` | Qarzni ham olish |
| `collect.written` | To'lov yozildi |
| `collect.recentTitle` | Oxirgi to'lovlar |
| `collect.reverse` | Bekor qilish |
| `collect.reversed` | Bekor qilingan |
| `collect.override` | Summani o'zgartirish |
| `collect.reasonLabel` | O'zgartirish sababi |
| `collect.reasonPlaceholder` | Sabab tanlang |
| `collect.reverseTitle` | To'lovni bekor qilish |
| `collect.reverseReasonLabel` | Bekor qilish sababi |
| `collect.newAmountLabel` | Yangi summa |
| `collect.retry` | Qayta yuborish |
| `collect.retrySafe` | ⛔ Qayta yuborish dublikat yaratmaydi |
| `collect.marketClosed` | Bugun bozor yopiq — bugungi patta hisoblanmaydi |
| `collect.amountUnit` | so'm |

**Smena (`collect.shift*`):**

| Kalit | uz-Latn |
|-------|---------|
| `collect.shiftTitle` | Smena |
| `collect.shiftOpen` | Smenani ochish |
| `collect.shiftOpenedAt` | Boshlangan vaqt |
| `collect.shiftClose` | Smenani yopish |
| ⛔ `collect.shiftBlindNotice` | ⛔ Qo'lingizdagi naqdni sanab kiriting. Tizim summasini ko'rsatmaydi — farqni direktor ko'radi. |
| `collect.declaredLabel` | Yig'ilgan naqd |
| `collect.shiftConfirmBody` | Deklaratsiya yozilgach o'zgartirilmaydi. |
| `collect.declarationWritten` | Deklaratsiya yozildi |
| `collect.shiftClosedAt` | Yopilgan vaqt |
| `collect.shiftNew` | Yangi smena ochish |

### 13.4 Direktor yuzasi (`billing.*`) — shipping matn

| Kalit | uz-Latn |
|-------|---------|
| `billing.title` | Patta hisobi |
| `billing.dayLabel` | Kun |
| `billing.pendingTitle` | ⛔ Kutilayotgan patta |
| `billing.pendingNotice` | ⛔ Bu kutilayotgan summa — hisob hali yozilmagan. |
| `billing.pendingStalls` | Kutilayotgan rasta |
| `billing.refresh` | Yangilash |
| `billing.fetchedAt` | Olingan vaqt |
| `billing.chargesTitle` | Yozilgan hisoblar |
| `billing.chargeWritten` | Yozilgan hisob |
| `billing.tariffAmount` | Tarif summasi |
| `billing.chargeAmount` | Hisob summasi |
| `billing.amount` | Summa |
| `billing.outstanding` | Qoldiq |
| `billing.detail` | Tafsilot |
| ⛔ `billing.immutableNotice` | ⛔ Bu hisob o'zgartirilmaydi. Tuzatish alohida yozuv sifatida qo'shiladi. |
| `billing.adjustmentsTitle` | Tuzatishlar |
| `billing.noAdjustments` | Tuzatish yo'q |
| `billing.increase` | Qo'shildi |
| `billing.decrease` | Kamaytirildi |
| `billing.evidenceTitle` | Dalil kadrlari |
| `billing.anomaliesTitle` | Anomaliyalar |
| `billing.anomalyKind.unassigned_occupied` | Ro'yxatga olinmagan savdo |
| `billing.anomalyKind.closed_day_occupied` | Yopiq kunda savdo |
| ⛔ `billing.anomalyKind.no_coverage_stall` | ⛔ Qamrovsiz rasta |
| `billing.shiftsTitle` | Smena hisobi |
| `billing.declared` | Deklaratsiya |
| `billing.systemTotal` | Tizim summasi |
| `billing.variance` | Farq |
| `billing.varianceShort` | ⛔ Kamomad |
| `billing.varianceOver` | ⛔ Ortiqcha |
| `billing.varianceMatch` | Mos keldi |
| `billing.shiftlessPayments` | Smenasiz to'lovlar |
| `billing.chargesLaterNotice` | Kunlik patta kun yopilgandan keyin, ertasi kuni ertalab yoziladi. |
| `billing.amountUnit` | so'm |

### 13.5 Sabab-kodlar — yopiq ro'yxat, uchala tilda (D-19, G-24)

| Kalit | uz-Latn |
|-------|---------|
| `collect.adjustmentReason.late_review` | Nazoratchi keyin tasdiqladi |
| `collect.adjustmentReason.ai_false_positive` | Tizim xato band dedi |
| `collect.adjustmentReason.tariff_correction` | Tarif noto'g'ri kiritilgan |
| `collect.adjustmentReason.partial_day` | Rasta kun o'rtasida bo'shatilgan |
| `collect.adjustmentReason.director_waiver` | Direktor kechirdi |
| `collect.reversalReason.wrong_stall` | Noto'g'ri rasta |
| `collect.reversalReason.wrong_amount` | Noto'g'ri summa |
| `collect.reversalReason.duplicate_entry` | Takroriy kiritish |
| `collect.reversalReason.customer_refund` | Sotuvchiga qaytarildi |

⛔ **`other` / `custom` YO'Q** (§8.6). ⛔ **To'plam `lib/api-types.ts` dagi reyestr bilan TENG** — G-24 buni uchala locale'da **to'plam tengligi** bilan o'lchaydi (D-31: `not.toContain` **emas**).

⚠ Ro'yxat buyurtmachi bilan **kelishilmagan** (06-RESEARCH OQ-3 / A3) — §17 O-02 da tetigi bilan.

### 13.6 Yangi `AuditAction` a'zolari — reyestrdan HOSILA (C-13)

⛔ **Bu hujjat a'zolar ro'yxatini QULFLAMAYDI** va bu ataylab: `AUDITED_TABLES` (06-RESEARCH tavsiyasi: `charge_adjustments` **HA**, `cashier_shifts` **HA**, qolganlari **YO'Q**) va `write_app_audit()` chaqiruvlari **rejaning natijasi**, ya'ni qo'lda yozilgan ro'yxat **ortda qolardi** (D-32).

**Kontrakt:** `sbozor_core/enums.py::AuditAction` ga qo'shilgan **har** a'zo uchun `audit.actions.<nom>` kaliti **uchala locale'da** bo'lishi shart — buni mavjud `audit-actions.test.mjs` **enumdan iteratsiya qilib** talab qiladi.

**Nomzod to'plam (rejaga yo'l-yo'riq, darvoza EMAS):** `charge_adjust`, `shift_open`, `shift_close`. ⚠ Reja bu to'plamdan chetga chiqsa, darvoza **o'zi** aytadi va bu hujjat tuzatishni talab qilmaydi.

### 13.7 Xato kontrakti — SABAB + NIMA QILISH KERAK (G-17 davomi)

Har kod **ikki** kalitga ega: `errorCause.{kod}` (nima bo'ldi) va `errorFix.{kod}` (nima qilish kerak). Reyestr `lib/billing-errors.ts` da (W0-F2).

| Kod | `errorCause` (uz-Latn) | `errorFix` (uz-Latn) |
|-----|------------------------|----------------------|
| `stall_not_found` | Bunday raqamli rasta topilmadi | Raqamni tekshirib qayta kiriting |
| `tariff_missing` | Bu rastaning bugungi tarifi belgilanmagan | Tarif sahifasida toifa narxini kiriting |
| `amount_unavailable` | Server summani bermadi | Sahifani yangilang — summa serverdan keladi va qo'lda kiritilmaydi |
| ⛔ `market_closed` | Bugun bozor yopiq — bugungi patta hisoblanmaydi | Faqat eski qarzni olish mumkin; qarz ham yo'q bo'lsa bugun bu rastaga to'lov yozilmaydi |
| ⛔ `stall_not_assigned` | Bu rastaga sotuvchi biriktirilmagan | Biriktirishlar sahifasida sotuvchini biriktiring — to'lov sotuvchiga yoziladi |
| `no_open_shift` | Ochiq smena yo'q | Avval smenani ochish kerak |
| `shift_already_open` | Sizda ochiq smena bor | Avvalgi smenani yoping |
| `shift_already_closed` | Bu smena allaqachon yopilgan | Yangi smena ochish |
| `reason_required` | Sabab tanlanmagan | Ro'yxatdan sabab tanlang |
| ⛔ `override_not_applicable` | Summa server taklifiga teng — sabab kerak emas | Sababni olib tashlab qaytadan yuboring |
| `idempotency_key_reused` | Bu to'lov varag'i boshqa summa bilan yuborildi | Sahifani yangilab qaytadan kiriting |
| `payment_already_reversed` | Bu to'lov allaqachon bekor qilingan | Yangi to'lov kiriting |
| `charge_immutable` | Yozilgan hisob o'zgartirilmaydi | Tuzatishni alohida yozuv sifatida kiriting |
| `network_unreachable` | Tarmoq uzildi | Qayta yuboring — dublikat yaratilmaydi |

⛔ **Uch qator 06-02 da QO'SHILDI** (jadval **14** kod). Uchalasi ham 06-09 ning **haqiqiy** shoxidan chiqadi — «ehtimol kerak bo'ladi» degan kod qo'shilmadi: `market_closed` D-24 ning «yopiq kunda ham qarz undiriladi» mexanizmidan (§9.4), `stall_not_assigned` D-28 ning `vendor_id NOT NULL` langaridan, `override_not_applicable` esa `payments` dagi `CHECK ((amount_soum = quote_soum) = (override_reason IS NULL))` dan. §13.6 ning presedenti bu kengaytmani ochiq ruxsat etadi va `06-UI-SPEC.md` **yakuniy manba** bo'lib qoladi.

⛔ **Har kod uchala tilda va JUFTLIKDA** — G-17 (`error-codes.test.mjs` kengaytmasi) `billing_errors.py` ning **to'rt** sirt reyestridan **iteratsiya qiladi** va bitta yarim yetishmasa qizaradi. Reyestr `occupancy_errors.py` ga **qo'shilmaydi**: u yerdagi `occupancyConstants.size === 15` nazorat qiymati darhol qizarardi (§0.1 M-B).

### 13.8 Toastlar (6) va bo'sh holatlar (7)

**Toastlar** (`sonner`, `top-center richColors`):

| # | Matn | Tur |
|---|------|-----|
| 1 | To'lov yozildi · {rasta} · {summa} | success |
| 2 | To'lov bekor qilindi | success |
| 3 | Summa o'zgartirildi | success |
| 4 | Smena ochildi | success |
| 5 | Deklaratsiya yozildi | success |
| 6 | ⛔ Tarmoq uzildi — qayta yuborish dublikat yaratmaydi | error + `[Qayta yuborish]` |

**Bo'sh holatlar** (`EmptyState`) — har birida **boshqa** keyingi qadam:

| # | Joyi | Sarlavha | Keyingi qadam |
|---|------|----------|---------------|
| 1 | Y-1 `no-shift` | Ochiq smena yo'q | `[Smenani ochish]` |
| 2 | Y-1 `idle` | Rasta raqamini kiriting | ⛔ Amal **yo'q** — fokusning o'zi amal |
| 3 | Y-1 to'lovlar | Bu smenada to'lov yozilmagan | ⛔ Amal **yo'q** |
| 4 | Y-4 `day = bugun` | Bugungi hisoblar hali yozilmagan | `[Kechagi kunni ko'rish]` |
| 5 | Y-4 hisoblar bo'sh | Bu kunda hisob yozilmagan | `[Anomaliyalarni ko'rish]` |
| 6 | Y-4 anomaliya bo'sh | ⛔ Anomaliya topilmadi | ⛔ Amal **yo'q** — **nol natija** |
| 7 | Y-4 smena bo'sh | Bu kunda yopilgan smena yo'q | ⛔ Amal **yo'q** |

⛔ **№4 ning tavsifi C-3 ni ochiq TUSHUNTIRADI** (`billing.chargesLaterNotice`): «Kunlik patta kun yopilgandan keyin, ertasi kuni ertalab yoziladi.» Tushuntirilmasa, direktor bo'sh sahifani **nosozlik** deb o'qirdi — 4-fazadagi «bo'sh katak» sinfidagi jim xato.

### 13.9 Uch til va transliteratsiya kontrakti

| Qoida | Mexanizm |
|-------|----------|
| Har ko'rinadigan satr — **uchala** locale'da | `check-messages.mjs` (`i18n:check`) |
| ⛔ `uz-Cyrl.json` **QO'LDA YOZILMAYDI** | `npm --prefix frontend run i18n:gen` (`gen-cyrillic.mjs`) — **generatsiya** |
| Qo'lda tuzatish | ⛔ Faqat `uz-Cyrl.overrides.json` orqali va **sabab bilan**. [O'LCHANDI: M-5] 67 nomzod satrda **0 defekt** → 6-faza yozuv **qo'shmasligi kutiladi**; qo'shish zarur bo'lsa sabab shu bo'limga yoziladi. ⚠ Yakuniy tekshiruv **`i18n:gen --check`** ning ishi, bu hujjatning emas |
| ⛔ **Akronim taqig'i** | `AI`, `CV`, `ONNX`, `RF-DETR`, `JSON` — `collect.*`/`billing.*` da **yo'q**. Sabab 05-UI-SPEC §0.2 da o'lchangan: `CV`→`CВ` **aralash alifbo** beradi va «lotin qoldi» detektori uni **ushlamaydi** (G-26) |

⛔ **Taqiqlangan so'zlar** (G-26, uchala locale'da):

| Taqiq | O'rniga | Sabab |
|-------|---------|-------|
| `storno` / `сторно` | «Bekor qilish» | §13.1 |
| `variance` / `варианс` | «Farq» / «Kamomad» / «Ortiqcha» | §13.1 |
| `idempotent` / `идемпотент` | «Qayta yuborish dublikat yaratmaydi» | §13.1 |
| `proyeksiya` / `проекция` | «Kutilayotgan» | §13.1 |
| ⛔ «hammasini to'lash» / «оплатить все» | ⛔ **Muqobil YO'Q** | §15.4 — so'z copy'ga kirsa, keyingi ijrochi uni **amalga oshirishga** urinardi (2 va 3-fazada aynan shunday bo'lgan) |
| ⛔ `to'g'rila*` / `исправить` — **variance ga nisbatan** | ⛔ **Muqobil YO'Q** | D-26: variance **hech qachon to'g'rilanmaydi**; so'z ekranda bo'lsa, tugma ham talab qilinardi |
| `bo'sh` / `бўш` / `свободн` — **`no_coverage` matnida** | «Qamrovsiz» | §11.4 |
| `balans` / `баланс` — **ustun/maydon nomi sifatida** | «Qoldiq» | BILL-03 |

---

## 14. Qulaylik (a11y)

### 14.1 Umumiy talablar [MEROS: 05-UI-SPEC §13.1]

| Talab | 6-fazada |
|-------|----------|
| Barmoq nishoni ≥ 44px | ✅ va **oshiriladi**: 48px (to'lov turi), 56px (qidiruv, tasdiq, deklaratsiya) — §6.2 |
| Fokus halqasi `:focus-visible` | ✅ Barcha interaktiv element, jumladan radio va jadval `[Tafsilot]` tugmalari |
| Klaviatura bilan **to'liq** oqim | ✅ §14.4 |
| `motion-reduce` | ✅ `Skeleton` va `Loader2` mavjud primitivlar orqali |
| Rang yagona signal emas | ✅ §12.4 — 13 holat, har biri **≥3 kanal** |
| Kontrast ≥ 4,5:1 matn | ✅ Yangi rang juftligi kiritilmadi (§12.1) |

### 14.2 `fieldset` / `legend`

| Guruh | `<legend>` | Sabab |
|-------|-----------|-------|
| To'lov turi (`Naqd` / `Terminal`) | `collect.methodLegend` = «To'lov turi» | Ikki radio — skrinrider guruhni **nomi bilan** e'lon qiladi (§8.4) |
| DL-1 (sabab + summa) | `collect.override` = «Summani o'zgartirish» | Ikki maydon bitta qarorga xizmat qiladi |

### 14.3 `aria-disabled`, `disabled` EMAS [MEROS: 05-UI-SPEC §13.3]

| Element | Qachon `aria-disabled` | Bosilganda nima bo'ladi |
|---------|------------------------|--------------------------|
| `[To'lovni tasdiqlash]` | To'lov turi tanlanmagan | `role="status"`: «Avval to'lov turini tanlang» |
| `[To'lovni tasdiqlash]` | Summa yo'q (`amount-unavailable`) | `role="alert"`: nomlangan sabab (§9.4) |
| DL-1 `[Tasdiqlash]` | Sabab tanlanmagan | `role="status"`: «Ro'yxatdan sabab tanlang» |
| `[Yopish]` (smena) | Summa kiritilmagan | `role="status"`: «Yig'ilgan naqdni kiriting» |

`disabled` tugma fokus olmaydi va skrinrider uni **umuman o'qimaydi** — «nega bosilmayapti?» savoliga javob beradigan joy qolmaydi. Bozor sharoitida bu **oqim to'xtashi** demak.

### 14.4 ⛔ Klaviatura va nima uchun BU EKRANDA YORLIQ YO'Q [QAROR]

| Qadam | Klaviatura |
|-------|-----------|
| 1 — rasta | `autoFocus`, terish, **`Enter`** |
| 2 — to'lov turi | `Tab` bilan radiogroup'ga, `←`/`→` bilan tanlash (native) |
| 3 — tasdiq | `Tab`, keyin `Enter` yoki `Space` |
| To'lovdan keyin | ⛔ Fokus **avtomatik** qidiruvga qaytadi (§8.5) — `Tab` bosish kerak emas |

⛔ **Global bir-tugmali yorliqlar (`1`/`2`/`3`) BU EKRANDA YO'Q** — 5-fazadagi `decision-bar` dan **ataylab farqli**:

1. **Qidiruv maydoni ko'p vaqt fokusda** (§8.5 fokus qaytishi tufayli **har to'lovdan keyin**). Global `keydown` ishlovchisi raqam terish bilan **to'qnashardi** — `1` bosilishi ham rasta kodining belgisi, ham «naqd» buyrug'i bo'lardi.
2. ⛔ **Adashgan tugma bosilishi HECH QACHON to'lov yozmasligi kerak.** 5-fazada yorliqning oqibati — bitta baho; bu yerda — **pul yozuvi**.
3. `decision-bar.tsx:101` ning `event.repeat` qoidasi shunga qaramay **kuchda**: tasdiq tugmasida `Enter` **bosib turish** bir necha so'rov yubormasligi G-21 da o'lchanadi.

### 14.5 Jonli hududlar reyestri

| # | Hudud | `role` | Nima e'lon qiladi |
|---|-------|--------|--------------------|
| 1 | Qidiruv natijasi | `status` | «Rasta {kod} topildi» / «Rasta topilmadi» |
| 2 | To'lov yozildi | `status` | «To'lov yozildi · {rasta} · {summa}» |
| 3 | Summa yo'q sababi | `alert` | Nomlangan sabab + tuzatish |
| 4 | Tarmoq xatosi | `alert` | Sabab + «Qayta yuborish dublikat yaratmaydi» |
| 5 | Deklaratsiya yozildi | `status` | «Deklaratsiya yozildi · {summa}» |

⛔ **Ikkitadan ko'p `role="alert"` bir vaqtda chizilmaydi** [MEROS: 04-UI-SPEC `NvrCard.showErrorBlock` darsi] — skrinrider ikkinchisini **uzib qo'yardi**.

---

## 15. Darvozalar (G-N)

### 15.1 ⛔ Raqamlash — IKKI KETMA-KETLIK bor va bu ochiq yozilishi SHART

Loyihada bugun **ikki mustaqil** `G-N` ketma-ketligi mavjud va ular **kesishadi**:

| Ketma-ketlik | Diapazon | Uyi | Kim yozgan |
|--------------|----------|-----|------------|
| **Frontend darvozalari** | `G-1`…`G-19` **band** | `frontend/scripts/*.test.mjs`, `*.test.tsx` | 03/04/05-UI-SPEC |
| **Backend/faza darvozalari** | `G-1`…`G-16` **band** | `tests/**` | **06-RESEARCH § Validation Architecture** + `06-VALIDATION.md` |

⛔ **Backend diapazoni 06-02 da `G-12` dan `G-16` ga kengaytirildi.** Sabab shu jadvalning **o'z qoidasi**: diapazon kelajakdagi to'qnashuvni oldini olish uchun yozilgan va eskirgan diapazon `G-13`…`G-16` ni **jimgina qayta ishlatishga** olib kelardi (yangilari `06-VALIDATION.md` da: D-24 kun kesimi · hosila↔hisoblanadigan qoldiq tengligi · §9.4 ning «faqat qarz» ustuni · `stall_not_assigned`).
⚠ **Frontend ketma-ketligi TEGILMADI** — `G-1`…`G-19` band, yangilari `G-20` dan. Bu **ikki mustaqil** ketma-ketlik.

⛔ **Bu hujjat RENOMERLAMAYDI.** Sabab: 06-RESEARCH ning `G-7` i (ko'r deklaratsiya serializatori) allaqachon **ikki qatlamli** — backend yarmi `ShiftCloseResponse` kalitlar to'plamini, **frontend yarmi** `components/collect/**` katalogini skanerlaydi. Uni ko'chirish rejaning va research'ning **ikkalasini** ham tuzatishni talab qilardi.

**Qoidalar:**

1. **`G-7`** — 06-RESEARCH egaligida qoladi; bu hujjat uning **frontend yarmini** aniqlashtiradi (§15.3).
2. Bu hujjatning **yangi** darvozalari **`G-20` dan** boshlanadi — frontend ketma-ketligi 5-fazada `G-19` da tugagan.
3. ⛔ Kod izohlarida darvoza ID'si **ketma-ketligi bilan** yoziladi: `G-7 (06-RESEARCH)` yoki `G-20 (06-UI-SPEC)`. Yalang'och `G-7` **yozilmaydi**.

### 15.2 Har darvozaning ikki muzokarasiz xossasi

| Xossa | Ma'nosi | Sabab |
|-------|---------|-------|
| ⛔ **HOSILA qamrov** (D-32) | Darvoza katalogni **o'qiydi**, marshrut grafini **so'raydi**, reyestrdan **iteratsiya qiladi**. Qo'lda yozilgan komponent/marshrut ro'yxati **YO'Q** | 05-16 W-2: qo'lda ro'yxat yangi komponent paydo bo'lganda **jimgina yashil** qoladi |
| ⛔ **TO'PLAM TENGLIGI** (D-31) | `deepEqual` / `Set` tengligi. ⛔ `not.toContain(...)` **ishlatilmaydi** | 05-14 sabotaj S7: inkor tasdiq **faqat aynan o'sha nomni** ushlaydi; maydon `chargeId` deb qayta nomlanса **o'tib ketardi** |

Har darvozada **quyi chegara** ham bor (`MIN_*`): skanerlanadigan fayl soni yoki reyestr hajmi kamaysa, darvoza **qizaradi**. Sabab `blind-payload.test.mjs:274` da o'lchangan: bo'sh to'plamda «taqiqlangan token topilmadi» **jimgina rost** bo'ladi.

### 15.3 Darvozalar

| # | Darvoza | Fayl | Mexanik ravishda NIMANI o'qiydi | Nima uchun mavjud |
|---|---------|------|----------------------------------|-------------------|
| **G-7** (06-RESEARCH) | ⛔⛔ **Ko'r deklaratsiya yuzasi** — frontend yarmi | `scripts/collect-surface.test.mjs` (yangi, W0-F4) | (a) `components/collect/**` katalogini **`readdirSync` bilan rekursiv** o'qiydi (mahsulot fayllari, `*.test.tsx` chiqariladi), izohlar `stripComments()` bilan olib tashlanadi; (b) `system_soum`, `system_total_soum`, `expected_soum`, `variance`, `varianceSoum`, `payment_count` tokenlari **umuman uchramaydi**; (c) ⛔ **quyi chegara**: katalog mavjud va ≥5 mahsulot fayli; (d) `shiftCloseResponseSchema` maydonlari to'plami `{id, status, declared_soum, closed_at}` ga **teng** (vitest, `shift-close-form.test.tsx`) | **D-25 + §10.3/§10.4.** Bu darvoza `components/collect/**` **alohida katalog** bo'lgani uchungina yozilishi mumkin (§5.3) — aralash katalogda `variance` qonuniy bo'lardi (direktor yuzasi) va shart **kontekstga bog'liq** bo'lib qolardi |
| **G-20** | ⛔⛔ **≤3 o'zaro ta'sir — DOM'dan hosila SANOQ** | `collect-session.test.tsx` (vitest) | Sikl DOM'dan `[data-collect-step]` elementini oladi va unga ta'sir qiladi; har iteratsiyada (a) `querySelectorAll("[data-collect-step]")` **uzunligi 1**; sikl tugagach (b) `apiFetch("/payments")` **1 marta**; (c) sanoq **`toBe(3)`**; (d) `visited` massivi **`["stall","method","confirm"]` ga teng** (tartib + to'plam); (e) POST tanasidagi `amount_soum` **server bergan** `pending.amount_soum` ga **teng**; (f) ⛔ **ikkinchi takror ham AYNAN 3** (§8.5 fokus qaytishi) | ⛔ **D-18 miqdor, ya'ni o'lchanadi.** «Uchta tugma bor» degan strukturaviy tekshiruv to'rtinchi qadam qo'shilganda **yashil qoladi**. `toBe(3)`, `<=3` emas: 2 qadam degani tasdiq **avtomatik** bo'lgan, ya'ni **tasdiqsiz pul yozilgan** (§8.2) |
| **G-21** | ⛔⛔ **Ikki qatlamli dublikat qulfi** | `payment-bar.test.tsx` (vitest) | (a) Tasdiqni **uch marta tez** bosish → `apiFetch("/payments")` **1 marta**; (b) tasdiqda `keyDown{key:"Enter",repeat:true}` **uch marta** → **0 qo'shimcha** so'rov; (c) 5xx dan keyin `[Qayta yuborish]` → **2-chi** so'rov va **o'sha `idempotency_key`**; (d) summa DL-1 da o'zgartirilgach → **boshqa** kalit | **D-22.** 05-13 o'lchagan: uch bosish **uchta so'rov** yubordi, chunki `isPending` faqat **keyingi renderda**. (c) va (d) Pitfall 4 ni qo'riqlaydi: bir xil kalit + boshqa summa **409** bo'lardi |
| **G-22** | ⛔⛔ **Kassir yuzasining taqiqlangan nomlari** | `scripts/collect-surface.test.mjs` | `components/collect/**` **va** `lib/billing-pending-queries.ts` (izohlar olib tashlangan) da reyestrdagi **birorta** nom uchramaydi: `charge_id`, `chargeId`, `tariff_id`, `tariffId`, `category_id`, `categoryId`, `valid_from`, `vendor_name`, `vendorName`, `phone`, `full_name`, `fullName`, `balance`, `balance_soum`, `occupied_slots`, `is_billable`. ⛔ **Quyi chegara: reyestrda ≥14 nom** | **D-17 + D-20 + C-10, uchalasi bitta mexanizmda.** `tariff_id` taqig'i D-20 ni *taqiqdan* **imkonsizlikka** aylantiradi: klientda tarif **kirish ma'lumoti yo'q**, ya'ni summani hisoblab bo'lmaydi. `balance` taqig'i BILL-03 ni, ism taqig'i C-10 ni qo'riqlaydi — va §5.5 ning «nom bilan aylanib o'tish TAQIQLANADI» qoidasi shu reyestrda yashaydi |
| **G-23** | ⛔ **Sxema qattiqligi va juftlangan invariant** | `pending-card.test.tsx` + `shift-close-form.test.tsx` (vitest) | (a) `pendingStallSchema.parse({...toza, charge_id:"x"})` **throw**; (b) `shiftCloseResponseSchema.parse({...toza, system_total_soum:1})` **throw**; (c) ikkala sxema `z.strictObject`; (d) ⛔ juftlangan invariant: `{amount_soum:null, amount_unavailable_reason:null}` **throw** **va** `{amount_soum:1000, amount_unavailable_reason:"tariff_missing"}` **throw**; (e) `billing-pending-queries.ts` da `invalidateQueries` **yo'q**, `removeQueries` **bor** | **Ikkinchi qatlam.** G-22 kodni tekshiradi (**statik**), bu esa **xulqni** (**dinamik**): server bir kun maydon qo'shsa, klient **darhol qizaradi** va u jimgina ekranga oqib o'tmaydi. Faqat G-22 bo'lsa `data["charge" + "_id"]` uni chetlab o'tardi; faqat G-23 bo'lsa u faqat **testda yozilgan** payloadni tekshirardi (05-UI-SPEC G-12/G-13 mulohazasi) |
| **G-24** | **Sabab-kodlarning yopiqligi va narxi** | `scripts/billing-copy.test.mjs` (yangi, W0-F5) + `reason-dialog.test.tsx` | (a) `lib/api-types.ts` dagi `ADJUSTMENT_REASONS` va `REVERSAL_REASONS` reyestrlaridan **iteratsiya qilib**, `collect.adjustmentReason.*` / `collect.reversalReason.*` kalitlari **uchala locale'da** — ⛔ **to'plam tengligi**; (b) reyestrda `other`/`custom` **yo'q**; (c) DOM: DL-1 da `<textarea>` va `type="text"` bo'lgan sabab maydoni **yo'q**; (d) sabab tanlanmasa tasdiq **`aria-disabled`** | **D-19 + CASH-02 + SC#4c.** (b) eng muhimi: `other` erkin matnni **qaytarib keltirardi** va hisobotda **eng katta guruh** bo'lib qolardi. (c) taqiqni **DOM darajasida** o'lchaydi — «erkin matn yo'q» kod-ko'rik da'vosi bo'lib qolmasin |
| **G-25** | ⛔⛔ **Proyeksiya va yozilgan hisob BIR EKRANDA uchrashmaydi — VA BLOK BO'SH BO'LMAYDI** [KUCHAYTIRILDI 2026-08-10] | `billing/page.test.tsx` (asosiy) + `scripts/billing-copy.test.mjs` (copy yarmi) | ⛔ **UCH QATLAM, uchalasi ham majburiy.** **(a) BLOK TO'PLAMI:** `?day=bugun` bilan render → DOM'dagi `[data-billing-block]` qiymatlari to'plami **`{"day","pending","shifts"}` ga TENG**; `?day=kecha` bilan → **`{"day","charges","anomalies","shifts"}` ga TENG**; ⛔ ikki to'plamning **kesishmasi `{"day","shifts"}`** — ya'ni `pending` va `charges` **hech qachon birga** chiqmaydi. **(b) ⛔ MAZMUN JUFTLIGI — bo'sh o'ram O'TMAYDI:** ro'yxat komponentining ⛔ **O'ZI** (⛔ `page.tsx` **EMAS**) o'z ildizida `data-billing-content="<blok>"` chiqaradi; da'vo (a) ning blok to'plamidan ⛔ **aylanib HOSILA** qilinadi (D-32): har `b ∉ CONTENT_EXEMPT` uchun `blockEl.querySelector('[data-billing-content="' + b + '"]')` ⛔ **null EMAS**, va `Set([data-billing-content])` ⛔ **=** `Set(blocks) \ CONTENT_EXEMPT`; `CONTENT_EXEMPT = new Set(["day"])` — kun tanlagichi **boshqaruv**, ro'yxat emas (uning o'z da'volari `billing/day-picker.test.tsx` da) — va ⛔ `CONTENT_EXEMPT.size === 1` ⛔ **alohida assert** (istisno jimgina o'smaydi); ⛔ mexanik kafolat: `grep -c "data-billing-content" billing/page.tsx` → ⛔ **0**. **(c) ⛔ HAQIQIY MAZMUN — mock javobidan HOSILA (literal YOZILMAYDI):** `pending` → formatlangan `pending_total_soum`; `charges` → `items[0].stall_code` **va** `querySelectorAll("tbody tr").length === items.length`; `anomalies` → `items[0].kind` ning `ANOMALY_KINDS` yorlig'i; `shifts` → formatlangan `items[0].declared_soum`; ⛔ `items: []` bergan blok ⛔ **o'z bo'sh-holat matnini** ko'rsatishi shart (§13.8 №5/№6/№7) — ⛔ bo'sh `<div>` ⛔ **hech qaysi holatda** o'tmaydi. ⛔ **SABOTAJ (D-30, majburiy):** `billing/page.tsx` da `<ChargeList …/>` → `<div data-billing-block="charges" />`; (a) ⛔ **yashil qolishi KUTILADI** (eski darvozaning ko'rligi — SUMMARY ga **shu sifatda** yoziladi), (b) **va** (c) ⛔ **QIZARISHI SHART** | ⛔ **D-17 ning eng kuchli kanali (§9.3 kanal 7)** — va ⛔ **O'LCHANGAN KO'RLIKDAN keyin kuchaytirilgan (2026-08-10).** Vizual farq (lenta, ikonka, jumla) — **odam o'qiydigan** himoya; (a) esa **strukturaviy**: direktor ikkisini yonma-yon **ko'ra olmaydi**, ya'ni «proyeksiyani kvitansiya deb o'qish» uchun fizik joy qolmaydi. ⛔ **Lekin (a) YOLG'IZ bo'sh o'ramni MUKAMMAL o'tkazardi:** `<div data-billing-block="charges" />` atribut to'plamini **o'zgartirmaydi**, ya'ni BILL-02/03/04 direktor ekranida ⛔ **umuman chizilmagan** holda darvoza, task **va** faza ⛔ **yashil** qaytardi. Bu 05-15 ning ⛔ **S-D sinfi** (sabotaj sistemaga yetib boradi, lekin tanlangan **ma'lumot/yuza** ikkala shoxda **bir xil** javob beradi) va o'sha darsning yechimi ham shu: ⛔ **yuzani kengaytirish**, assertni almashtirish **emas**. (b) yuzani **ro'yxatning o'z chiqishiga** kengaytiradi, (c) esa uni **mock'dan hosila haqiqiy qiymatga** bog'laydi. To'plam **tengligi** bilan (D-31), `not.toContain` bilan **emas** |
| **G-26** | **Anomaliya turlari, akronim va taqiqlangan so'zlar** | `scripts/billing-copy.test.mjs` | (a) `lib/api-types.ts::ANOMALY_KINDS` dan **iteratsiya qilib** `billing.anomalyKind.*` kalitlari uchala locale'da — **to'plam tengligi**; (b) nomi `no_coverage` ni o'z ichiga olgan **har** kalitning qiymatida `bo'sh`/`бўш`/`свободн` **yo'q**; (c) `collect.*`/`billing.*` da `AI`,`CV`,`ONNX`,`RF-DETR`,`JSON` **yo'q** (⛔ reyestrda ≥5 token); (d) §13.9 taqiqlangan so'zlari **yo'q** (⛔ reyestrda ≥8 token) | (a) **BILL-04**: uch `kind` uch yorliq. (b) **D-05 ning copy shakli** — farq DB'da bor, matn darajasida yo'qolsa hisobot jimgina noto'g'ri o'qilardi va **hech qanday sxema** buni ushlamaydi. (c) [O'LCHANDI: 05-UI-SPEC M-5] `CV`→`CВ` **aralash alifbo** beradi va «lotin qoldi» detektori uni **ushlamaydi**. (d) so'z taqig'i — kod-ko'rikda **eng oson o'tkazib yuboriladigan** narsa |
| **G-27** | ⛔ **Variance ikki tomonlama va YOZUV YUZASI NOL** | `billing/variance-list.test.tsx` (vitest) | (a) `variance_soum < 0` bo'lgan qatorda «Kamomad» **va** `TrendingDown`; (b) ⛔ `variance_soum > 0` bo'lgan qatorda «Ortiqcha» **va** `TrendingUp` — **ikkalasi ham bitta testda**; (c) `= 0` da «Mos keldi»; (d) ⛔ blok ichidagi interaktiv elementlar to'plami **`{"Tafsilot"}` ga TENG** (ya'ni `[To'g'rilash]`, `[Tasdiqlash]`, `[Izoh]`, `[Kechirish]` **yo'q**); (e) `abs()` ishlatilmagani — manfiy qiymat ekranda **minus bilan** | **D-26.** (b) muzokarasiz: *«Ortiqcha naqd ham signal — uni jimgina yutish kamomadni yashirish bilan bir xil xato.»* (d) to'plam **tengligi** bilan: yangi tugma qo'shilsa darvoza **o'zi** qizaradi — `not.toContain("To'g'rilash")` esa faqat o'sha nomni ushlardi |
| **G-28** | ⛔ **Dalil-kadr yuzasi — YANGI marshrut YO'Q** | `charge-detail-dialog.test.tsx` + `scripts/collect-surface.test.mjs` | (a) DL-3 dagi `<img>` elementlarining `src` to'plami **butunlay** `/api/v1/snapshots/{id}/image` shabloniga mos (regeks bilan, **har biri**); (b) `snapshot_id` bo'lmagan `evidence` elementi uchun `<img>` **umuman yo'q** (`querySelectorAll` **0**); (c) `crossOrigin` atributi **yo'q**; (d) `components/collect/**` da `/snapshots/` **umuman uchramaydi** — kassir yuzasida dalil kadri **yo'q** | **C-9 + M-8.** (d) eng qimmati: kassir yuzasida kadr **bo'lmaganda** `require_any_permission()` ning yopiq to'plami **tegilmagan** qoladi va `test_personal_data_coverage.py:674-706` **o'zicha** yashil turadi. (b) — 05-14 darsi: marshrut bermagan qator **chizilmaydi**, placeholder ham qo'yilmaydi |

### 15.4 ⛔ Ommaviy amal taqig'i — MAVJUD darvozaga QO'SHILADI, yangi ID olmaydi

`components/collect/**` ham ommaviy-amal skanidan o'tishi **shart**: «Hammasini to'lash» yoki ko'p-tanlovli rasta ro'yxati kassirga **bir bosishda 50 rastani to'langan** deb belgilash imkonini berardi — bu 5-fazadagi «hammasini tasdiqlash» dan **qimmatroq** xato, chunki natijasi **pul yozuvi**.

⛔ **Mexanizm — mavjud e'lonni KENGAYTIRISH, ikkinchi e'lon YOZMASLIK** [O'LCHANDI: M-4]:

| Qadam | Ish |
|-------|-----|
| 1 | `05-UI-SPEC.md` §15 dagi ommaviy-amal qatoriga **uchinchi** naqsh qo'shiladi: `` `components/collect/**` `` |
| 2 | ⛔ Bu **aynan birinchi `components/collect/*.tsx` mahsulot fayli bilan bitta commitda** bo'ladi — `bulk-action-surface.test.mjs:293-308` e'lon qilingan **har** katalogning mavjud va **bo'sh emasligini** tekshiradi |
| 3 | Skan **o'zi** kengayadi: `MIN_SCANNED_FILES = 5` chegarasi ham, `checkbox` / `Array.isArray` tokenlari ham **o'zgarmaydi** |

⛔ **BU HUJJAT O'SHA DARVOZA UCHUN QATOR YOZMAYDI.** `bulk-action-surface.test.mjs:112-125` e'lon qilgan UI-SPEC soni **aynan 1** bo'lishini talab qiladi; ikkinchi e'lon `npm run gate` ni **butunlay** qizartirardi. Bu tuzoq §0.2 da o'lchov bilan yozilgan va **keyingi fazalar ham** shu qoidaga bo'ysunadi.

### 15.5 Sampling — mavjud byudjetlar

| Daraja | Buyruq | Byudjet |
|--------|--------|---------|
| Task commit | `npm run gate:fast` | **180 s** (joriy 87 s) |
| Wave merge | `npm run test` + `npm run test:tenancy` | — |
| Faza darvozasi | `npm run gate` | **1250 s** (joriy ~1009 s) |

⚠ **Byudjet xavfi ochiq yozilgan:** 6-faza ~10 komponent + 7 test fayli + 2 skript qo'shadi. `gate` da **241 s zaxira** bor. Reja har to'lqinda `gate` vaqtini **o'lchashi** va oshsa byudjetni **sabab bilan** qayta belgilashi shart — 05-15 W0-13 naqshi (tinch xost, uch o'lchov, sabab yozilgan).

---

## 16. Bu fazada BO'LMAYDIGAN UI

[MEROS: 06-CONTEXT `<domain>` + `<deferred>` + 06-RESEARCH Scope Fence]

### 16.1 Keyingi fazalarga qoldiriladigan

| Imkoniyat | Faza | 6-fazada aynan nima qilinadi | Nima QILINMAYDI |
|-----------|------|-------------------------------|------------------|
| **Telegram push-kvitansiya** (`CASH-05`) | 7 | Hech narsa | «Kvitansiya yuborish» tugmasi, yuborilganlik holati |
| **«Band, lekin to'lovsiz» ro'yxati va case oqimi** | 7 | ⛔ Anomaliya **yozuvi ko'rsatiladi** (§11.4) | Holat, mas'ul, qaror, `[Ko'rildi]`, hit-rate |
| **Eski to'lovni direktor tomonidan bekor qilish** | 7 | Kassir **o'z ochiq smenasidagi** to'lovni bekor qiladi (§8.8) | Eski to'lov uchun bekor qilish yuzasi — **marshruti yo'q** |
| **`.xlsx` eksporti, diagramma, oylik trend** | 8 | Sonlar matn sifatida, `<table>` da | Yuklab olish tugmasi, `recharts`, haftalik/oylik grafik |
| **Qarzdorlik reyestri SOTUVCHI kesimida** | 8 | Qoldiq **hisob qatorida** ko'rinadi (§11.2) | Sotuvchi bo'yicha guruhlangan reyestr, TOP-10 qarzdor |
| **Variance chegarasi va alerti** | 8 | Variance **ko'rsatiladi** (§11.5) | ⛔ `alert_key = 'shift_variance'` **yozilmaydi** (OQ-7 / A6) |
| **Rol bo'yicha bosh ekran** | 7 | `/dashboard` **tegilmaydi** | Kassir uchun boshlang'ich sahifa redirekti (§4.6) |
| **Offline navbat, PWA** | `V2-CASH-05` | Tarmoq uzilishida **toast + qayta yuborish** (§8.1 `error`) | ⛔ `manifest.json`, service worker, navbat, `localStorage` |
| **QR / bank o'tkazma** | `V2-CASH-03` | Ikki tur: `cash`, `terminal` | Uchinchi tur, referens maydoni, UzQR solishtiruvi |
| **Fiskal kvitansiya maydonlari** | `V2-CASH-04` | Hech narsa | INN, QQS, «nofiskal» belgisi, chek chiqarish |
| **Jonli undirish ro'yxati** | `V2-CASH-01` | Kassir **rasta bo'yicha** so'raydi (§8.3) | «Band, hali to'lamagan» real vaqt ro'yxati |
| **Kassir↔zona biriktirish, kassir samaradorligi** | `V2-CASH-02` | Hech narsa | Zona tanlagichi, kassir reytingi |

### 16.2 Ataylab qurilMAYDIGAN — sabab bilan

| Nima | Nima uchun qurilmaydi |
|------|------------------------|
| ⛔ **«Hammasini to'lash» va har qanday ommaviy to'lov** | §15.4. Bir bosishda 50 rasta «to'langan» bo'lardi va **hech qanday dalil** qolmasdi. Va undan ham muhimi — ⛔ **har qatorda tugmali «to'lanmaganlar ro'yxati» ham qurilmaydi**: u qadamlari ko'proq bo'lgan **o'sha tugma** |
| ⛔ **Kassirga tizim summasini yoki variance ni ko'rsatish** | §10.3, §10.4. `system = declared − variance` — bitta ayirish, ya'ni variance ni ko'rsatish D-25 ni **hisob-kitob bilan** buzardi |
| ⛔ **Smena to'lovlarining JAMI yig'indisi** | §8.8. Oyna **5 qator** va sahifalash **yo'q** — yig'indi yo'lini maydon yashirish emas, **marshrutning imkoniyati** to'sadi |
| ⛔ **Klientda pul arifmetikasi** (`amount + outstanding`) | §9.6. `total_due_soum` **serverdan** keladi; G-22 klientda tarif kirish ma'lumotini **yo'q qilib** buni qo'llab-quvvatlaydi |
| ⛔ **Proyeksiyada «bugun band» belgisi** | §9.1. Bugun **bilinmaydi** (C-8) — ko'rsatilsa **soxta ko'rsatkich** bo'lardi va kassir unga tayanib pul yig'ardi |
| ⛔ **Proyeksiyada `[Dalilni ko'rish]`** | §9.3 kanal 6. Dalil **hisobda** tug'iladi; proyeksiyada u **mavjud emas**, ya'ni tugma yo'q imkoniyatni va'da qilardi |
| ⛔ **Dalil kadri kassir yuzasida** | §11.3. Kadr kassirning ishida hech narsani o'zgartirmaydi, lekin `require_any_permission()` ning **yopiq to'plamini** kengaytirishni talab qilardi (C-9) |
| ⛔ **Hisob yoki to'lovni tahrirlash / o'chirish** | D-07, D-23. Tuzatish faqat `charge_adjustments` va storno. `[Tahrirlash]`/`[O'chirish]` tugmalari **umuman yozilmaydi** |
| ⛔ **Variance uchun `[To'g'rilash]`** | D-26 va G-27(d). Avtomatik ham, qo'lda ham to'g'rilash yo'li **ochilmaydi** |
| ⛔ **Erkin matnli sabab** | D-19, G-24(c). Hisobotda **guruhlanmaydi** va amalda **bo'sh qoladi** |
| ⛔ **`other` / «Boshqa» sabab-kodi** | §13.5. Erkin matnni **qaytarib keltirardi** va hisobotda **eng katta guruh** bo'lardi |
| ⛔ **O'z raqamli klaviaturamiz** | §8.3. Rasta kodi `text` (`12a`, `A-3`) — raqam-only panel ba'zi rastalardan **pul yig'ib bo'lmaydigan** qilardi |
| ⛔ **Rasta kodi URL'da** | §4.5. Ulashiladigan to'lov varag'i + kalitning yo'qolishi = **dublikat** |
| ⛔ **Proyeksiyaning avtomatik taymeri** | §9.5. Direktor raqamni o'qib turganda uni jimgina o'zgartirish — «men boshqa raqam ko'rgandim» nizosining manbai |
| ⛔ **Kassir ekranida sotuvchi ismi/telefoni** | §5.5, C-10. Rasta kodi — **identifikator**; ism `vendor_view` ni talab qilardi |
| ⛔ **Global bir-tugmali yorliqlar (`1`/`2`)** | §14.4. Qidiruv maydoni ko'p vaqt fokusda; adashgan bosish **pul yozardi** |
| ⛔ **Hisoblar reyestrini `/occupancy` ga qo'shish** | §4.3. Bandlik ≠ hisob; kun semantikasi ham boshqa (C-2 nom tuzog'i UI'ga ko'chardi) |
| ⛔ **`billing_runs` ko'rinishi / job holati paneli** | 06-RESEARCH: yurak urishi `system_heartbeats` da va uni 4-fazaning alert mexanizmi ko'radi. Ikkinchi kuzatuv yuzasi qurilmaydi |

### 16.3 Erta optimizatsiya deb baholangan «ilgaklar»

Rasta kodlari uchun avtomatik to'ldirish/taklif ro'yxati (⛔ boshqa bozorning kodini taklif qilardi, §8.3 `autoComplete="off"`); to'lovlar ro'yxati virtualizatsiyasi (5 qator); proyeksiya uchun optimistik yangilash (⛔ pul raqamida optimizm **taqiqlanadi**); `components/billing/**` uchun umumiy `<MoneyTable>` abstraktsiyasi (uch iste'molchi, uch xil ustun); dark mode; Storybook; dalil kadrlarini oldindan yuklash; klaviatura yorliqlari palitrasi.

---

## 17. Ochiq qoldirilgan savollar — har biri uchun ishlaydigan standart bor

Bu subagent kontekstida foydalanuvchiga savol berish vositasi yo'q (`--auto`). Quyidagilar **taxmin qilinib jimgina qulflanmadi**; har biri uchun standart tanlangan, ya'ni rejalashtirish javob kutib **to'xtamaydi**.

| # | Savol | Bilamiz | Noaniq | Tanlangan standart va TETIGI |
|---|-------|---------|--------|-------------------------------|
| **O-01** | Kassir sotuvchi ismini ko'rmasligi mahsulot uchun qabul qilinadimi? (06-RESEARCH **A7**) | C-10 darvozasi ism qaytaruvchi `GET` dan `VENDOR_VIEW` + `audit_read` talab qiladi; kassirda `vendor_view` yo'q va berilishi **xavfli** (C-9 ⚠) | Kassir «kim to'layapti» ni ko'rmaydi | ⛔ **Ism YO'Q. Rasta kodi — identifikator** (§5.5). Sabab: kassir **rasta yonida turadi** va sotuvchi ham o'z rastasining raqamini biladi. **Tetigi:** dala UAT bandi. Agar real to'siq bo'lsa, to'g'ri yechim — **`stalls` jadvalidagi ochiq yorliq** (masalan rasta nomi), shaxsiy maydon **emas** |
| **O-02** | Sabab-kodlar to'plami to'g'rimi? (06-RESEARCH **OQ-3 / A3**) | `.planning/` da kelishilgan ro'yxat **yo'q** (`STATE.md:265` — 7 ochiq buyurtmachi savoli) | Karmana amalda boshqa sabablar ishlatishi mumkin | ⛔ **§13.5 ning 5+4 kodi, `other` YO'Q.** Sabab: kichik yopiq to'plam kengaytirilishi mumkin, `other` esa **qaytarib bo'lmaydigan** darvoza bo'shashi. **Tetigi:** birinchi hafta hisobotida bitta kod **80 %** dan ko'p bo'lsa, to'plam noto'g'ri tanlangan. Yangi kod = migratsiya + 3 locale + G-24 |
| **O-03** | Qisman va ortiqcha to'lov ruxsat etiladimi? (06-RESEARCH **OQ-4 / A4**) | BILL-03 qoldiqni **hisoblanadigan** qilgani uchun ikkalasi ham qo'shimcha mantiqsiz ishlaydi | Mahsulot qarori yo'q | ⛔ **Ikkalasi ham RUXSAT**; ortiqcha «Avans» bo'lib ko'rinadi (§9.6). Sabab: bloklash kassirni pulni **umuman yozmaslikka** majburlardi. **Tetigi:** `CHECK (amount_soum = tariff_amount_soum)` **yozilmaydi** — agar buyurtmachi qat'iy to'liq to'lov talab qilsa, u **serverda** qo'shiladi va UI xato kodi bilan ko'rsatadi |
| **O-04** | 24px (Display) to'lanadigan summa uchun quyoshda yetarlimi? | Display — mavjud eng katta rol; `font-mono` + 600 og'irlik; sahifadagi **yagona** Display elementi | Real yorug'lik va qo'lqop sinovi bo'lmagan | ⛔ **24px (Display).** Beshinchi o'lcham **qo'shilmaydi** (§7.1). **Tetigi:** dala UAT. Tuzatish — **hujjatlashtirilgan beshinchi rol**, `text-[32px]` shaklidagi bir martalik qiymat **emas** |
| **O-05** | Kassirning boshlang'ich sahifasi `/dashboard` bo'lib qolishi to'g'rimi? | [O'LCHANDI: M-6] Kassirning mobil paneli **`/dashboard` + `/collect`**, overflow 0; sanoq **sahifa ochilgandan** boshlanadi (§8.2) | Kuniga bir marta ortiqcha bosish | ⛔ **`/dashboard` qoladi.** Rol bo'yicha bosh ekran — **7-fazaning mezoni**. **Tetigi:** 7-faza `/dashboard` ni rolga moslashtirganda kassir uchun `/collect` ga havola **birinchi element** bo'lishi kerak |
| **O-06** | Variance chegarasi qancha? (06-RESEARCH **OQ-7 / A6**) | `alert_events` mexanizmi tayyor; chegara **kelishilmagan** | Karmana uchun ma'noli son bilinmaydi | ⛔ **MVP da alert YO'Q**, variance faqat hisobotda (§11.5). Sabab: kodda literal son **barcha bozorlarga** tarqalardi. **Tetigi:** chegara qo'shilsa u **bozor bo'yicha sozlanadigan** bo'lishi shart; egasi — 8-faza |
| **O-07** | «Patta» atamasi barcha uchala tilda tabiiy eshitiladimi? | Atama **talab matnining o'zida** ishlatilgan (BILL-01…05) va u mahalliy | `ru` locale'da «патта» transliteratsiya bo'lib qoladi | ⛔ **«Patta» / «патта» qoladi.** Sabab: bu **mahsulotning nomi bo'lgan tushuncha**; «сбор»/«пошлина» ga o'girish uni **boshqa narsaga** aylantirardi. **Tetigi:** 8-fazadagi «uch tilli interfeys yakuniy tekshiruvi» mezoni (05-UI-SPEC O-01 bilan bir yo'lda) |

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

*Phase: 06-billing-va-kassir*
*UI-SPEC yakunlandi: 2026-08-10 — `gsd-ui-researcher`*
*Upstream: 06-CONTEXT.md (D-01…D-32), 06-RESEARCH.md (C-1…C-13, § Validation Architecture, OQ-1…OQ-7, A1…A8), 05-UI-SPEC.md (dizayn tizimi, i18n, a11y, darvoza mexanikasi), 02-UI-SPEC.md §6.9 (≤2 o'zaro ta'sir kontrakti), ROADMAP Phase 6 (SC#1–SC#5), REQUIREMENTS.md (BILL-01…05, CASH-01…04), CLAUDE.md*
