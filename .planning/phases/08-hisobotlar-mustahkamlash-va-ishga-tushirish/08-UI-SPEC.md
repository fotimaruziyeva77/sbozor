---
phase: 08-hisobotlar-mustahkamlash-va-ishga-tushirish
status: draft
shadcn_initialized: false
preset: none
design_system: shadcn-pattern (manual, CVA + Radix — 1/2-faza tokenlari)
response_language: uz-Latn
inherits: .planning/phases/07-nomuvofiqlik-bildirishnoma-va-botlar/07-UI-SPEC.md
created: 2026-08-13
---

# Phase 8 — Hisobotlar, mustahkamlash va ishga tushirish: UI dizayn kontrakti

> Bitta va'daning vizual kontrakti: **direktor raqamni O'ZI chiqarib oladi, va chiqargan raqami hujjat sifatida turadi.**
> 7-fazaning UI'si «da'voni isbotlanadigan darajaga tushirish» edi. Bu fazaniki — **raqamni ekrandan chiqarib, qog'ozga va faylga o'tkazish**. Farq shundaki, bu yerda UI xatosi ekranda **qolmaydi**: u `.xlsx` bo'lib yuklab olinadi, chop etiladi, imzolanadi va nizoda **dalil** sifatida ishlatiladi. Ekrandagi noto'g'ri son tuzatiladi; **eksport qilingan noto'g'ri son esa tarqaladi**.
> ⛔ Bu faza dizayn tizimini **meros qilib oladi**, boshlamaydi. ROADMAP uni ochiq aytadi: «hafta 12 — **yangi funksiya emas, mustahkamlash haftasi**». Yangi token, yangi bo'shliq shkalasi, yangi npm paketi yoki ikkinchi pul-formatlash yo'li — **o'zi nuqson** bo'lardi.
> Yaratdi: `gsd-ui-researcher`. Tekshiradi: `gsd-ui-checker`. Iste'mol qiladi: `gsd-planner`, `gsd-executor`.

---

## 0. Dalil holati va shu sessiyada bajarilgan o'lchovlar

| Belgi | Ma'nosi |
|-------|---------|
| **[O'LCHANDI]** | Shu sessiyada kodbazada yoki skript bilan o'lchandi — natija keltirilgan |
| **[KOD]** | Kodbazadan o'qildi — aniq `fayl:qator` keltirilgan |
| **[MEROS]** | Upstream artefaktdan (08-CONTEXT, 07/06/05-UI-SPEC, ROADMAP, REQUIREMENTS, CLAUDE.md) |
| **[QAROR]** | Shu hujjatda qabul qilindi — sabab yozilgan, muqobil rad etilgan |
| **[TALAB]** | UI backend'dan talab qiladigan narsa — rejaga bevosita kiradi |
| **[ASSUMED]** | Dalilsiz tanlangan qiymat — sabab va tetigi yozilgan (07-CONTEXT D-19 konvensiyasi) |

### 0.1 O'lchovlar

| # | O'lchov | Natija |
|---|---------|--------|
| **M-1** | **shadcn darvozasi** — `find . -maxdepth 3 -name components.json` (node_modules chiqarilgan) | **0 natija** → `Tool: none` (§3.4). 2–7-faza qarori davom etadi |
| **M-2** | **`ui/` primitivlari** — `ls frontend/src/components/ui/` | **10 primitiv** (`badge, button, card, confirm-dialog, dialog, empty-state, field, input, select, skeleton`). 8-fazada **yangi `ui/` primitivi qurilmaydi** (§3.2) |
| **M-3** | **Ikonka mavjudligi** — `require('lucide-react')` bilan **61 ta** 8-faza nomzod nomi | **0 ta yetishmayapti.** Jumladan: `FileSpreadsheet, Download, FileDown, CalendarRange, CalendarDays, Wallet, Coins, HandCoins, Landmark, TrendingUp, TrendingDown, Scale, Columns3, Table, BookOpen, NotebookPen, Upload, FileUp, ShieldCheck, DatabaseBackup, ArchiveRestore, FileClock, Percent, Target, Signature, PenLine, Equal, Diff` |
| **M-4** | ⛔⛔ **`G-18(b)` darvozasi UI-SPEC FAYLLARINI O'QIYDI** [KOD: `bulk-action-surface.test.mjs:79-125`] | Regeks — `` /^\|\s*\*\*G-18\*\*\s*\|/ ``, ya'ni **shu belgilar bilan BOSHLANADIGAN jadval qatori**; `assert.equal(SPEC_FILES.length, 1)` **va** `rows.length === 1`. ⛔ **Oqibat: BU FAYL ham shunday qator YOZMAYDI**; qamrov `05-UI-SPEC.md` §15 dagi **mavjud** qatorga **beshinchi** naqsh qo'shish bilan kengaytiriladi (§16.5). Prozada «G-18» deb yozish **xavfsiz** |
| **M-5** | **Navigatsiya sig'imi** — `NAV_ITEMS` × `ROLE_PERMISSIONS` [KOD: `app-shell.tsx:105-372`, `rbac.ts:68-133`] | Hozir **16 element**. `/reports` (`report_view`) qo'shilgach → **17**: `platform_admin` **11 (o'zgarmaydi)** · `director` **14** · `market_admin` **14** · ⛔ `cashier` **2 (o'zgarmaydi)** · `inspector` **2 (o'zgarmaydi)**. `MOBILE_PRIMARY_COUNT = 4`, kassir paneli **`/dashboard` + `/collect`**, overflow **0**. **6-faza kontrakti saqlanadi** |
| **M-6** | ⛔ **YANGI HUQUQ KERAK EMAS** [KOD: `rbac.ts:57,99,119`] | `report_view` **allaqachon bor** va **aynan `director` + `market_admin`** da. ⛔ `platform_admin` da **YO'Q**, `cashier` da **YO'Q**, `inspector` da **YO'Q** — ya'ni D-04 («kassir hisobot yuzasini ko'rmaydi») va D-20 bugungi matritsada **allaqachon rost**. 8-faza `rbac.py`/`rbac.ts` **juftligiga TEGMAYDI** (§5.6) |
| **M-7** | ⛔⛔ **Sessiya tokeni — `Authorization: Bearer`, xotirada** [KOD: `api-client.ts:215`] | `<a href="…/reports/revenue.xlsx" download>` brauzer tomonidan **tokensiz** ketadi → **401** (yoki login HTML'i `.xlsx` nomi bilan saqlanadi). ⛔ «Yuklab olish havolasi» **fayl havolasi BO'LA OLMAYDI** — bu intizom emas, **mexanika** (§0.2) |
| **M-8** | **Mavjud yuklab olish naqshi** [KOD: `api-client.ts:203` `apiRequest()`, `market-queries.ts:1116` `saveBlob()`, `:1152` `downloadTemplate()`] | ⛔ **Naqsh ALLAQACHON bor va qayta ishlatiladi**: `apiRequest()` (Bearer + 401-refresh + `!ok` da `ApiError`) → `response.blob()` → `saveBlob(blob, nom)` (`revokeObjectURL` gigiyenasi bilan). ⛔ Ikkinchi `fetch` yozilmaydi |
| **M-9** | **`Content-Disposition` o'qilishi** [KOD: `api-client.ts:31` `API_BASE_URL = "/api/v1"`; core-api'da `CORSMiddleware` **umuman yo'q**] | So'rov **bir xil origin** (nginx orqali) → sarlavha klientga **ochiq**. ⛔ Boshqa origin (`NEXT_PUBLIC_API_BASE_URL`) qo'yilsa CORS umuman sozlanmagani uchun **avtorizatsiyaning o'zi** yiqiladi — ya'ni bir xil origin farazi loyihada **allaqachon ko'taruvchi** (§12.3) |
| **M-10** | ⛔⛔ **Aniqlik hisobotining davri 8-fazaga ATAYIN qoldirilgan** [KOD: `occupancy.py:174-186` `ACCURACY_WINDOW_DAYS` docstringi] | Verbatim: «⛔ **DAVR TANLAGICHI YO'Q (§16.2 — 8-fazaning hisobot yuzasi), lekin `from`/`to` parametrlari BOR**: ular klientga emas, TESTGA va **kelajakdagi eksportga** kerak.» ⛔ Ya'ni D-09(c) 5-faza bilan **ziddiyat emas**, **rejalashtirilgan topshiriq** (§9.1) |
| **M-11** | **Aniqlik yuzasi allaqachon qurilgan** [KOD: `confusion-matrix.tsx`, `occupancy-queries.ts:82,171`, `api-types.ts:1951`] | `accuracyKey(marketId, from, to)` **allaqachon** `from`/`to` oladi; `useAccuracyReport()` bugun `null, null` uzatadi. ⛔ Ikkinchi komponent **yozilmaydi** — `ConfusionMatrix` **qayta ishlatiladi** (§9.2) |
| **M-12** | ⛔ **Zaxira alerti va uning UCH TILLI matni ALLAQACHON bor** [KOD: `alerting.py:177,313,682`; `messages/*.json` `snapshots.alertKey.backupStale`] | `BACKUP_COMPONENT = "backup"`, `AlertMeta("backup_stale", CRITICAL, …)`, `HEARTBEAT_STALE_HOURS = 26`. Matn: uz «**Zaxira nusxa yangilanmadi**» · ru «Резервная копия не обновлялась». ⛔ **D-15 ning UI/copy qismi BUGUNDAN yashil** — 8-faza faqat **yurak urishini yozadigan jarayonni** qo'shadi (§11) |
| **M-13** | **Transliteratsiya sinovi** — 42 ta 8-faza nomzod satri `gen-cyrillic.mjs::transliterate()` dan o'tkazildi | **1 ta xom defekt: `Excel` → `Эхcэл`** (aralash alifbo). ⛔ **LEKIN u REAL emas**: `uz-Cyrl.overrides.json` `words` bo'limida (**46 so'z**) `Excel` **ham**, `xlsx` **ham** allaqachon bor va mahsulot katalogi buni isbotlaydi — `import.title` cy = «**Excel** файлдан юклаш». ⛔⛔ **`Backup` → `Баcкуп` — REAL defekt va overrides'da YO'Q** → ekran/alert matnida «Backup» **yozilmaydi**, «**Zaxira nusxa**» yoziladi (§14.1). Qolgan 40 satr toza: `Qarzdorlik ro'yxati`→`Қарздорлик рўйхати`, `Uch tomonlama solishtiruv`→`Уч томонлама солиштирув`, `Band deb xato`→`Банд деб хато`, `AI aniqlik hisoboti`→`АИ аниқлик ҳисоботи` |
| **M-14** | **Frontend darvoza raqamlari** — barcha UI-SPEC'lar bo'yicha `G-\d+` skani | Eng katta band ID — **`G-36`** (07-UI-SPEC). ⛔ Bu hujjatning yangilari **`G-37` dan** boshlanadi (§16.1) |
| **M-15** | **Tipografiya sanog'i** — `text-*` utilitalarining uchrash soni | `text-sm` **396** · `text-xs` **148** · `text-lg` **36** · `text-2xl` **28** · ⚠ `text-base` **7** · ⚠ `text-xl` **3`. Oxirgi ikkitasi — 4 rolli e'londan (24/18/14/12) tashqaridagi **meros deviatsiyalar**, 8 faylda; ⛔ 8-faza ularga **tegmaydi va yangisini qo'shmaydi** (§7.1) |
| **M-16** | **Kun tanlagichining mavjud naqshi** [KOD: `billing/day-picker.tsx:63-113`, `snapshots/day-picker.tsx:59,75,91`] | `?day=` + `nuqs`, standart **kecha**, maks **bugun**, yaroqsiz qiymat **jimgina standartga tushadi**. Sof yordamchilar: `businessDayIn()`, `isValidIsoDay()`, `shiftIsoDay()`. ⛔ **Oraliq tanlagichi bu yordamchilardan quriladi, ikkinchi sana arifmetikasi yozilmaydi** (§4.4) |
| **M-17** | **Matn katalogi hajmi** — `messages/*.json` yassilangan kalitlar | **1212 / 1212 / 1212** (uz-Latn / uz-Cyrl / ru) — parity bugundan yashil |
| **M-18** | **Yo'q narsalar** | `frontend/src/app/[locale]/(app)/reports` — **yo'q**; `frontend/src/components/reports/` — **yo'q**; `services/core-api/app/api/v1/reports.py` — **yo'q**; `recharts` `package.json` da — **yo'q**. Barchasi Wave 0 yoki ataylab (§3.5) |

### 0.2 M-7 ning oqibati — bu fazaning eng qimmat tuzog'i

```
api-client.ts:215   if (token) headers.Authorization = `Bearer ${token}`;
```

Access token **xotirada** yashaydi va **so'rov sarlavhasida** ketadi; cookie'da faqat **refresh** bor. Demak:

> ⛔ `<a href="/api/v1/reports/revenue.xlsx?from=…&to=…" download>` **hech qachon ishlamaydi**. U tokensiz ketadi va **401** oladi — brauzer esa 401 javob tanasini **`revenue.xlsx` nomi bilan diskka saqlaydi**. Foydalanuvchi «fayl yuklandi» deb o'ylaydi, Excel esa «fayl buzilgan» deydi. ⛔ Bu **jimgina nosozlik**: tugma ishlagandek ko'rinadi, xato hech qayerda ko'rinmaydi va direktor **hisobot tizimi ishlamaydi** degan xulosaga keladi.

**Tanlangan yo'l** (§12.2) — 2-fazadan beri ishlab turgan **mavjud** naqsh, ikkinchi nusxasiz:

```
apiRequest(path)  →  (Bearer + 401-refresh + !ok da ApiError)
    → response.blob()
    → saveBlob(blob, filenameFrom(response))
```

**Rad etilgan muqobillar:**

| Muqobil | Nega rad etildi |
|---------|------------------|
| `<a download>` + URL'da bir martalik token | Token URL'ga chiqadi → nginx access-log'ga, brauzer tarixiga va Referer'ga tushadi. 3-fazadagi jonli-ko'rish chiptasi aynan shu sababdan **resursga bog'langan** va qisqa umrli edi; hisobot uchun ikkinchi chipta tizimi qurish — yangi xavfsizlik yuzasi |
| Hisobotni cookie autentifikatsiyasiga o'tkazish | `api-client.ts:28-31` cookie siyosatini **atayin** faqat refresh bilan chegaralagan; ikkinchi autentifikatsiya yo'li CSRF yuzasini ochardi |
| Klientda `.xlsx` qurish (SheetJS va h.k.) | ⛔ **D-05 taqiqi.** Bayt-determinizm (`_freeze_zip`) serverda; klientdagi ikkinchi generator bir kun **boshqa faylni** berardi va qaysi biri «hujjat» ekani noaniq bo'lardi |

---

## 1. Ko'lam

### 1.1 To'rtta yuza — ular teng og'ir emas

| # | Yuza | Nimaga javob beradi | Foydalanuvchi | Ustuvorlik |
|---|------|---------------------|---------------|------------|
| **Y-1** | ⛔ **Davr hisobotlari** (RECON-04) — tushum · qarzdorlik · nomuvofiqlik arxivi | «Shu davrda qancha yig'ildi, kim qarzdor, nima nomuvofiq bo'ldi?» | Direktor, bozor admini | ⛔ **ENG YUQORI** |
| **Y-2** | **AI aniqlik hisoboti** (RECON-05) | «Detektorga qay darajada ishonsa bo'ladi — va xato qaysi tomonga og'yapti?» | Direktor, bozor admini | Yuqori |
| **Y-3** | ⛔ **Uch tomonlama solishtiruv** (SC#5) — daftar vs tizim vs AI-kutilgan | «Parallel rejimda tizim daftardan qayerda ajralyapti?» | Bozor admini (bajaruvchi), direktor (tasdiqlovchi) | Yuqori |
| **Y-4** | **Mustahkamlash to'lqini** (D-24) — 13 WR + Info bandlari + 07 №1/№2/№4 | «Mavjud ekranlardagi mayda yolg'onlar tuzatildimi?» | Hamma rollar | O'rta — ⛔ **lekin tarqoq** |

⛔ **Zaxira/tiklash (FOUND-07) veb yuzasi EMAS** — u compose xizmati, cron va runbook. Uning UI'dagi yagona izi **allaqachon mavjud** alert (`snapshots.alertKey.backupStale`, M-12) va 8-faza unga **matn ham, komponent ham qo'shmaydi** (§11).

### 1.2 Y-1 nima uchun eng yuqori — va UI uni QANDAY jimgina buzadi

ROADMAP Phase 8 SC#1: *«Direktor tushum (kunlik/oylik), qarzdorlik reestri va nomuvofiqlik arxivini ko'radi hamda har birini `.xlsx` qilib yuklab oladi.»*

> Direktor «Oktyabr» ni tanlaydi va 47 300 000 ko'radi. `.xlsx` ni yuklab oladi, chop etadi, yig'ilishga olib boradi. Yig'ilishda buxgalter 44 100 000 deydi. Farq — hisobot **bugungi kunni ham** qamrab olgani, `daily_charges` esa bugun uchun **hali yozilmagani** (D+1 04:10). Hech kim buni bilmaydi. ⛔ Natija: **eksport qilingan raqam yig'ilishda yiqiladi** va tizimga bo'lgan ishonch bir majlisda tugaydi — 7-fazadagi «ikki xil raqam» ssenariysining **qog'ozga chiqqan, orqaga qaytarib bo'lmaydigan** shakli.

Beshta qoida **muzokarasiz** va §16 da darvozaga aylanadi:

| # | Qoida | Nega UI qatlamida ham kerak |
|---|-------|------------------------------|
| **1** | ⛔ **Davrning yuqori chegarasi — KECHA, bugun EMAS** | `daily_charges` D+1 **04:10** da tug'iladi [KOD: `worker.py` `BILLING_CLOSE_CRON`]. Bugunni qamragan hisobot **kam ko'rsatilgan** bo'ladi va u **fayl bo'lib tarqaladi** (**G-38**) |
| **2** | ⛔ **Davr HAR DOIM raqam bilan bir joyda** — ekranda ham, faylda ham, fayl nomida ham | Chop etilgan varaqdan davr yo'qolsa, raqam **hech nimaga bog'lanmagan** bo'lib qoladi (**G-39**) |
| **3** | ⛔ **O'lchanmagan son chizilmaydi** — «0 %» ham, «—» ham, bo'sh katak ham **javob emas** | D-10 + 05-13/05-14 naqshi + 07 ko'rigining **WR-05** bandi (**G-40**) |
| **4** | ⛔ **Uch farq sinfi hech qachon QO'SHILMAYDI** | Uch xil sabab, uch xil harakat. «Jami farq» solishtiruvni **foydasiz** qilardi (**G-41**) |
| **5** | ⛔ **Yuklab olish `<a download>` EMAS** | M-7 — mexanik, intizom emas (**G-38**) |

### 1.3 Talab qamrovi

| REQ | UI'da qanday ko'rinadi |
|-----|------------------------|
| **RECON-04** | Y-1 — ⛔ **uch alohida blok** (`revenue`, `debtors`, `anomalies`), har birida **o'z** yuklab olish tugmasi; birlashtirilgan «jami hisobot» **yo'q** |
| **RECON-05** | Y-2 — mavjud `ConfusionMatrix` **qayta ishlatiladi** + davr ulanadi + **to'rtinchi** eksport |
| **FOUND-07** | ⛔ **Veb yuzasi yo'q.** Mavjud `backup_stale` alerti (M-12) + runbook + `08-HUMAN-UAT.md` bandi |
| **SC#4** | ⛔ **Yangi ekran yo'q.** Uch tilli yakuniy tekshiruv — **inson o'qishi** (D-23), mexanik parity allaqachon `i18n:check` da |
| **SC#5** | Y-3 — `/reports/compare`, kunlik, ⛔ **uch ustun + uch farq sinfi**, `.xlsx` da **imzo qatorlari** |

### 1.4 Bu faza UI'si NIMA QILMAYDI (to'lig'i §17)

Diagramma va `recharts` · direktor botining buyruq yuzasi · botdan to'lov · to'liq interaktiv plan-xarita · kassir offline-lite · AI-02 ni yopish (real ONNX + oltin to'plam) · zaxira boshqaruvining veb paneli · raqamli imzo · Phase 0 baza varaqalarini ulash.

---

## 2. Yuqori oqim qarorlaridan meros

| Qaror / Topilma | Manba | UI'dagi bevosita oqibati |
|---|---|---|
| **D-01** yangi `/reports` bo'lim; `/billing`+`/reconciliation` **operativ** qoladi | 08-CONTEXT | §4.1, §4.3 — mavjud sahifalarga blok **qo'shilmaydi** |
| **D-02** kunlik/oylik preset + erkin oraliq, biznes-kun, URL sinxroni | 08-CONTEXT | §4.4 `?from=&to=` (`nuqs`); §4.5 |
| **D-03** hisobot — **hosila**, agregat jadval **yo'q** | 08-CONTEXT | §5.5: klient **hech nima hisoblamaydi**; **G-42** da `.toFixed(`/`parseFloat(` taqig'i |
| **D-04** ⛔ kassir hisobotni **ko'rmaydi**; ruxsat direktor + bozor admini | 08-CONTEXT | §4.7 — [M-6] `report_view` **allaqachon aynan shunday** |
| **D-05** XlsxWriter serverda; `_freeze_zip` determinizmi | 08-CONTEXT | §12.4 — ⛔ klientda fayl **qurilmaydi** |
| **D-06** eksport tili — so'rovchining locale'i; **butun so'm**; deterministik fayl nomi | 08-CONTEXT | §12.3 fayl nomi, §12.5 til; ⛔ til **so'rovda yuborilmaydi** (`downloadTemplate` naqshi) |
| **D-07** ism **serverda** joinlanadi; hisobot marshruti `PERSONAL_ROUTES` ga **kirmaydi**; bitta `audit_read` | 08-CONTEXT | §5.5 — ⛔ `vendor_name` `components/reports/**` da **QONUNIY** (7-fazadagidan **farqli**!) |
| **D-08** ekran ro'yxatlarining ism bo'shlig'i; topilmagan ism — **bo'sh katak** | 08-CONTEXT | §8.4 — ⛔ «—» ham, «Noma'lum» ham **yozilmaydi** |
| **D-09** aniqlikda **yangi hisob YO'Q**; foiz klientda qayta hisoblanmaydi | 08-CONTEXT | §9.2 — `percentView()` **faqat miqyos**, bo'lish amali yo'q |
| **D-10** ⛔ o'lchanmagan son **chizilmaydi**; WR-05 shu qoida bilan yopiladi | 08-CONTEXT | §9.3, §10.5, **G-40** |
| **D-11** AI-02 ning `Blocked` holati **yashirilmaydi** | 08-CONTEXT | §9.4 — holat jumlasi, ⛔ ogohlantirish **bezagi emas** |
| **D-17** daftar kirishi — **xlsx import**, 2-fazaning infratuzilmasi | 08-CONTEXT | §10.3 — `import-panel.tsx` naqshi qayta ishlatiladi |
| **D-18** uch ustun: daftar · tizim · AI-kutilgan (**hosila**) | 08-CONTEXT | §10.4 |
| **D-19** ekran + `.xlsx`; imzo qatorlari **faylda**, raqamli imzo **yo'q** | 08-CONTEXT | §10.6 — ⛔ ekranda `[Imzolash]` tugmasi **yo'q** |
| **D-20** bajaruvchi — nazoratchi yoki admin, ⛔ **kassir emas** | 08-CONTEXT + ROADMAP | §4.7 + **O-01** (`inspector` roli va ko'r audit ziddiyati) |
| **D-23** uch tilli tekshiruv — **inson o'qishi**, yangi darvoza **yozilmaydi** | 08-CONTEXT | §14.6 — mavjud `i18n:check` yetarli |
| **D-24** mustahkamlash qarzlari **qamrovda** (13 WR + Info) | 08-CONTEXT | §13 — ⛔ ular **yangi token so'ramaydi** |
| **D-26** `gate` **2300 s** / `gate:fast` **200 s** o'zgarmaydi | 08-CONTEXT | §16.7 |
| **07 D-03** dalil-kadr chegaradan chiqmaydi — eksportga **rasm kirmaydi** | 07-CONTEXT | §8.5 + **G-42**: `components/reports/**` da kadr tokenlari **0** |
| **07 D-30/D-31** atamalar yagona; darvoza **to'plam tengligi** bilan | 07-CONTEXT | §14.5, §16.2 |
| **05 §11 + `occupancy.py:174`** davr tanlagichi **8-fazaniki** | 05-UI-SPEC / [KOD] | §9.1 — ⛔ ziddiyat **yo'q**, topshiriq **rejalashtirilgan** |

---

## 3. Dizayn tizimi holati

### 3.1 Meros — o'zgarmaydi va qayta qurilmaydi

| Nima | Fayl | 8-fazada |
|------|------|----------|
| Tailwind 4 CSS-first `@theme` | `frontend/src/app/globals.css` | ⛔ **O'zgarmaydi. Yangi token YO'Q** |
| `Button` (4 variant; `sm` 36 · `md` 40 · `lg` **min 44px**) | `ui/button.tsx` | ⛔ Yuklab olish — `secondary`; aksent **aynan bir joyda** (§13.3) |
| `Card`/`CardHeader`/`CardContent` | `ui/card.tsx` | To'rtala blok + solishtiruv bloklari |
| `Input` + `Field` (`${id}-error`/`${id}-hint`) | `ui/input.tsx`, `ui/field.tsx` | Oraliq sanalari (`type="date"`) |
| `Select` (native `<select>`) | `ui/select.tsx` | ⛔ Davr **preseti** — yopiq to'plam (§4.4) |
| `Badge` (6 `tone`) | `ui/badge.tsx` | Farq sinflari, hisobot holati |
| `Skeleton` (`motion-reduce:animate-none`) | `ui/skeleton.tsx` | Blok yuklanishi |
| `EmptyState` (`title`/`description`/`action`) | `ui/empty-state.tsx` | **6 ta** bo'sh holat (§14.7) |
| `Dialog` (`sm/md/lg` + `sheetOnMobile`) | `ui/dialog.tsx` | ⛔ **ISHLATILMAYDI** (§4.6) |
| `ConfirmDialog` (`level 1\|2`, `confirmVariant="destructive"`) | `ui/confirm-dialog.tsx` | ⛔ **AYNAN BIR MARTA** — daftarni almashtirish (§14.8) |
| `sonner` Toaster (`top-center richColors`) | `layout.tsx:82` | 2 ta toast (§14.7) |
| `nuqs` URL holati | `billing/day-picker.tsx` naqshi | ⛔ `?from=&to=` (Y-1/Y-2), `?day=` (Y-3) |
| Biznes-kun yordamchilari | `snapshots/day-picker.tsx:59,75,91` | ⛔ **Qayta ishlatiladi** — ikkinchi sana arifmetikasi **yo'q** [M-16] |
| Fayl yuklash: `apiRequest` + `saveBlob` | `api-client.ts:203`, `market-queries.ts:1116` | ⛔ **Yagona yo'l** [M-8] |
| Import naqshi (shablon → yuklash → 422 xatolar) | `import/import-panel.tsx`, `import-errors.tsx` | ⛔ Daftar importi **shu naqshda** (§10.3) |
| Aniqlik matritsasi | `occupancy/confusion-matrix.tsx` | ⛔ **Qayta ishlatiladi**, ko'chirilmaydi [M-11] |
| Pul: `useFormatter().number()` + `*.amountUnit` | `pending-summary.tsx:155` | ⛔ **Yagona yo'l** |
| RBAC UI ko'zgusi | `lib/rbac.ts` | ⛔ **Yangi huquq YO'Q** [M-6] |
| next-intl 3 til + `i18n:check` | `messages/*`, `scripts/*.mjs` | §14; ⛔ `uz-Cyrl.json` **qo'lda tahrirlanmaydi** |
| Blok reyestri: `data-*-block` + mazmun juftligi | `billing/page.tsx`, `reconciliation/page.tsx` | §8.1 `data-report-block` — **shu naqshning nusxasi** |

### 3.2 Yangi `ui/` primitivi — YO'Q [M-2]

Uchta chegaraviy holat **ataylab** `ui/` ga ko'tarilmaydi:

| Komponent | Nega `ui/` emas |
|-----------|------------------|
| `reports/period-picker.tsx` | Uning kontrakti **domen qoidasi**: maksimum **kecha** (§1.2 qoida 1), presetlar biznes-kun bo'yicha. `ui/` dagi «umumiy oraliq tanlagichi» ertaga `maxDate` propini olardi va **bugun** ni uzatish bir qator bilan mumkin bo'lardi |
| `reports/export-button.tsx` | Uning butun ma'nosi — ⛔ **`<a download>` bo'la olmaslik** (§0.2). `ui/` dagi «yuklab olish tugmasi» ertaga `href` propini olardi |
| `reports/diff-cell.tsx` | Uch farq **sinfi** — domen taksonomiyasi (D-18), umumiy «farq katagi» emas |

### 3.3 Analogi yo'q komponentlar

| Komponent | Nega analog yo'q | Nima qilinadi |
|-----------|------------------|---------------|
| `reports/period-picker.tsx` | Kodbazada **oraliq** tanlagichi umuman yo'q — hammasi bitta kun (`?day=`) [M-16] | §4.4; sof yordamchilar 4-fazadan |
| `reports/comparison-table.tsx` | «Uch manba, bir qator, uch xil farq sinfi» — kodbazada yo'q. `variance-cell.tsx` **ikki** manbani solishtiradi | §10.4 |
| `reports/export-button.tsx` | `import-errors.tsx:142` eng yaqini (inline holat + xato), lekin u **bitta** joyda va **parametrsiz** | §12.2 |

### 3.4 shadcn darvozasi — natija [M-1]

**`components.json` topilmadi** → **`Tool: none`. `shadcn init` BAJARILMAYDI.** [QAROR — 2–7-faza qarorini davom ettiradi]

Sabablar: (1) `shadcn init` `package.json` ga yangi paket keltiradi — ⛔ **mustahkamlash haftasida yangi bog'liqlik**; (2) Tailwind 4 rejimida u `globals.css` ga **o'z token nomlarini** yozadi va `--color-bg`/`--color-surface`/`--color-accent` yonida **ikkinchi dizayn tizimi** paydo bo'lardi — 8-faza aynan **birlashtirish** haftasi; (3) bu subagent kontekstida interaktiv savol vositasi yo'q (`--auto`).

**Oqibat:** `Registry Safety` darvozasi shadcn uchun **qo'llanmaydi** (§15, §19).

### 3.5 Yangi bog'liqlik — YO'Q

**Yangi npm paketi: YO'Q.** [QAROR — ROADMAP: «yangi funksiya emas, mustahkamlash haftasi»]

| Ehtiyoj | Mavjud yechim | Nega yangi paket kerak emas |
|---------|---------------|------------------------------|
| ⛔ **Diagramma / trend grafigi** | ⛔ **YO'Q — jadval** | `recharts` `package.json` da **yo'q** [M-18]. 7-UI-SPEC uni «8-faza egasi» degan edi — ⛔ **egasi qaror qildi: qurilmaydi** (§17.2) |
| `.xlsx` qurish | ⛔ **Serverda** (XlsxWriter, D-05) | Klient generatori **ikkinchi haqiqat manbai** bo'lardi |
| `.xlsx` o'qish (daftar importi) | ⛔ **Serverda** (`xlsx_reader.py`) | Klientda o'qish validatsiyani **ikki joyga** bo'lardi (02-faza D-14) |
| Sana oralig'i tanlagichi | native `<input type="date">` × 2 + preset `<select>` | OS tanlagichi telefonda tezroq va **uch tilda o'zi** ishlaydi; kutubxona +40 KB va o'z locale muammosi bilan kelardi |
| Foiz formatlash | `useFormatter().number(v,{style:"percent"})` | Node 24 to'liq ICU |
| Fayl saqlash | `saveBlob()` [M-8] | `file-saver` paketi **aynan shu 12 qatorni** takrorlardi |

> Reja bajarilishida boshqa paket zarur bo'lsa, u **UI-SPEC ga qaytariladi** — jimgina `npm install` **qilinmaydi** [MEROS: 02-UI-SPEC §13].

---

## 4. Ekranlar reyestri

### 4.1 Marshrutlar

| Marshrut | Yuza | Vazifa | Huquq (UI ko'zgusi) |
|----------|------|--------|---------------------|
| `/[locale]/(app)/reports` | **Y-1 + Y-2** | Uch davr hisoboti + AI aniqligi; har biri `.xlsx` | `report_view` |
| `…/reports?from=…&to=…` | O'sha | O'sha sahifa, tanlangan davr (`nuqs`) | `report_view` |
| `/[locale]/(app)/reports/compare` | **Y-3** | Uch tomonlama solishtiruv, daftar importi, `.xlsx` | `report_view` |
| `…/reports/compare?day=YYYY-MM-DD` | O'sha | Tanlangan biznes-kun (`nuqs`) | `report_view` |

⛔ **Boshqa marshrut YO'Q.** `/reports/revenue`, `/reports/debtors`, `/reports/[kind]`, `/backup`, `/ops` — **qurilmaydi**.

### 4.2 Nega uch hisobot BITTA sahifada, alohida marshrutlarda emas [QAROR]

Muqobil: `/reports/revenue`, `/reports/debtors`, `/reports/anomalies`. **Rad etildi:**

1. ⛔ **Davr — uchalasi uchun BIR XIL va u tanlanadigan holat.** Uch marshrutda davr uch marta tanlanardi yoki uch marta URL'da ko'chirilardi; direktor «oktyabr» ni tanlab, ikkinchi hisobotda **sentyabrni** ko'rishi mumkin bo'lardi — 7-fazadagi «ikki xil raqam» sinfi.
2. **Direktorning savoli bitta, javobi uchta.** «Oktyabrda nima bo'ldi?» — tushum, qarz va nomuvofiqlik **birga o'qiladi**; qarz tushumsiz ma'nosiz.
3. **Uchtasi ham bir xil `report_view` ostida** — marshrutni bo'lish ruxsat granularligini oshirmaydi, faqat marshrut qamrovi matritsasini uchga bo'lardi.

⛔ **Lekin `/reports/compare` ALOHIDA marshrut** — va sabab uchalasidan farqli (§4.3).

### 4.3 Nega solishtiruv ALOHIDA marshrut [QAROR]

| # | Sabab |
|---|-------|
| 1 | ⛔⛔ **Davr modeli BOSHQA.** Y-1/Y-2 — **oraliq** (`?from=&to=`); Y-3 — ⛔ **aynan bitta kun** (`?day=`), chunki u «**kunlik** chiqariladi va imzolanadi» (SC#5). Bitta sahifada ikki xil davr holati bo'lsa, foydalanuvchi qaysi boshqaruv qaysi blokni boshqarishini **hech qachon** bilmasdi |
| 2 | ⛔ **Y-3 da YOZUV bor** — daftar importi (D-17) va u **almashtiruvchi** amal (§14.8). Y-1/Y-2 — sof o'qish. Yozuvni o'qish sahifasiga qo'shish `/billing` ↔ `/reconciliation` ajratilishining (07 §4.3) aynan takrori |
| 3 | ⛔ **Blok to'plami darvozasi toza qoladi.** Y-1 bloklari **davrga** bog'liq, Y-3 bloklari **kunga**; bitta darvozada ikkisini o'lchash `CONTENT_EXEMPT` ni ikki ma'noli qilardi (06-faza G-25 ning o'lchangan ko'rligi) |
| 4 | **Umri boshqa.** Y-1/Y-2 — **doimiy**; Y-3 — ⛔ **parallel rejimning 2–4 haftasi uchun** (ROADMAP: qat'iy cutover). Vaqtinchalik asbob doimiy sahifani ifloslantirmaydi |

### 4.4 ⛔ Davr tanlagichi — maksimum KECHA, standart OXIRGI 30 KUN [QAROR]

| Qoida | Qiymat | Sabab |
|-------|--------|-------|
| ⛔ **Maksimum `to`** | ⛔ **kecha** | §1.2 qoida 1. `daily_charges` D+1 04:10 da tug'iladi; bugunni qamragan hisobot **kam ko'rsatilgan** bo'lib **fayl bo'lib tarqalardi**. ⛔ Bu qoida **uchala hisobotga ham, aniqlikka ham** bir xil qo'llanadi — bitta qoida, bitta chegara |
| ⛔ **Standart davr** | ⛔ **oxirgi 30 kun** (`to` = kecha, `from` = kecha − 29) | ⚠⚠ **Sabab MEXANIK:** `ACCURACY_WINDOW_DAYS = 30` [KOD: `occupancy.py:174`] — server aniqlik uchun **aynan shu** oynani standart qilgan. Standart mos kelganda `/reports` va `/occupancy` dagi aniqlik raqami **standart holatda AYNAN TENG** bo'ladi va «ikki xil haqiqat» **tug'ilmaydi**. Boshqa standart (masalan «joriy oy») ikki ekranda ikki xil son berardi va uni **hech qanday test ko'rmasdi** |
| **Presetlar** | ⛔ **Aynan 4 ta:** `last30` (standart) · `yesterday` · `thisMonth` · `lastMonth` | Yopiq to'plam → native `<select>`, **G-43** da to'plam tengligi bilan |
| **Erkin oraliq** | ikki `<input type="date">` (`from`, `to`) | D-02 |
| **Yaroqsiz qiymat** | ⛔ **jimgina standartga tushadi**, xato ko'rsatilmaydi | [MEROS: `billing/day-picker.tsx:80-85`] — eskirgan xatcho'pdan kelgan direktorga «URL noto'g'ri» deyish foydali qadam bermaydi |
| **`from > to`** | ⛔ **almashtirilmaydi — standartga tushadi** | Avtomatik almashtirish foydalanuvchi **so'ramagan** davrni ko'rsatardi va u buni sezmasdi |
| **Maksimal uzunlik** | ⛔ **chegara YO'Q** | Sahifalash serverda (§8.6); sun'iy chegara «yillik hisobot» ni imkonsiz qilardi |

⛔ **`thisMonth` oyning 1-kunida:** `from` = 1-kun, `to` = kecha → ⛔ **o'tgan oyning oxirgi kuni**, ya'ni oraliq **bo'sh** (`from > to`). Bu holatda preset **`lastMonth` ga tushmaydi va jimgina o'zgarmaydi** — u ⛔ **nomlangan holat** ko'rsatadi: «Joriy oyda hali yopilgan kun yo'q» (§14.7 bo'sh holat 5). Sabab: jimgina boshqa oyni ko'rsatish direktorga **noto'g'ri oyning** raqamini berardi.

### 4.5 URL holati kontrakti

| Yuza | URL holati | Sabab |
|------|-----------|-------|
| `/reports` | ✅ **`?from=&to=`** (`nuqs`) | D-02 — hisobot havolasi **ulashiladi** |
| `/reports` preset | ⛔ **URL'da YO'Q** | Preset — `from`/`to` ning **hosilasi**; ikkalasini yozish ikkinchi haqiqat manbai bo'lardi. Ochilishda preset qiymatlardan **teskari hisoblanadi**, mos kelmasa `custom` |
| `/reports` standart davr | ⛔ **parametrsiz** | [MEROS: `billing/day-picker.tsx:105-112`] — toza havola ertasiga **o'sha kungi** standartni ko'rsatadi, sana havolada qotib qolmaydi |
| `/reports/compare` | ✅ **`?day=YYYY-MM-DD`** | `/billing`, `/reconciliation`, `/occupancy` bilan **aynan bir naqsh** |
| Yuklab olish holati | ⛔ **URL'da YO'Q** | Yuklash — **yon ta'sir**, holat emas |

### 4.6 Dialoglar

| # | Dialog | Ochiladi | O'lcham | Turi |
|---|--------|----------|---------|------|
| **DL-6** | ⛔ **Daftarni almashtirish tasdig'i** | Y-3 da shu kun uchun daftar **allaqachon bor** bo'lganda `[Daftarni yuklash]` bosilsa | `ConfirmDialog` **`level: 1`** | Destruktiv (§14.8) |

⛔ **Boshqa dialog YO'Q.** Hisobot qatorining tafsiloti — **yo'q** (jadval o'zi to'liq); eksport sozlamalari dialogi — **yo'q** (§17.2); aniqlik tafsiloti — **yo'q** (`ConfusionMatrix` o'zi to'liq).

⛔ **`level: 2` (matn yozib tasdiqlash) ISHLATILMAYDI:** daftar importi **kunlik operatsion amal** (parallel rejimda har kuni) va `level: 2` uni har kuni jazolardi. Yo'qotish ham cheklangan — o'sha kunning daftar qatorlari, ular **qayta yuklanadi**.

### 4.7 Navigatsiya — bitta yozuv [QAROR]

| Yozuv | Guruh | Ikonka | Huquq | Joyi |
|-------|-------|--------|-------|------|
| **Hisobotlar** (`/reports`) | `market` | `FileSpreadsheet` | `report_view` | ⛔ `/reconciliation` dan **keyin**, `system` guruhidan **oldin** |

[M-5] `NAV_ITEMS` 16→**17**. ⛔ `cashier` **2 (o'zgarmaydi)**, `inspector` **2 (o'zgarmaydi)**, mobil overflow **0**.

⛔ **`/reports/compare` NAVIGATSIYAGA KIRMAYDI** [QAROR]. Sabablar: (1) u ⛔ **parallel rejimning 2–4 haftasi** uchun (ROADMAP: qat'iy cutover, cho'zilmaydi) — vaqtinchalik asbobga doimiy navigatsiya slotini berish uni cutover'dan keyin ham **abadiy** qoldirardi; (2) u `/reports` **ichidagi** havoladan ochiladi va shu kontekstda ma'noli; (3) navigatsiya byudjeti 4-fazadan beri har fazada o'lchanadi. **Tetigi:** parallel rejimda bozor admini «har kuni ikki bosish» dan shikoyat qilsa — bitta qator qo'shiladi va [M-5] bo'yicha kassir paneli **o'zgarmaydi**.

⚠ **`FileSpreadsheet` nima uchun** (`FileText`/`Download` emas): `FileText` — `/audit` da band bo'lgan «hujjat» ma'nosi; `Download` esa **amalni** bildiradi va u sahifa ichidagi tugmalarda takrorlanadi — navigatsiyada amal ikonkasi **joy** ikonkasidan kuchsizroq.

---

## 5. Komponentlar reyestri

### 5.1 Wave 0 — bloklovchi

| # | Ish | Fayl | Nega bloklovchi |
|---|-----|------|------------------|
| **W0-F1** | `lib/report-queries.ts` — ⛔ **yagona** so'rov + eksport moduli | yangi | **G-38**/**G-42** ning skan maydoni. Eksport funksiyasi ham **shu modulda** |
| **W0-F2** | `REPORT_KINDS` + `PERIOD_PRESETS` + `DIFF_CLASSES` ko'zgusi | `lib/api-types.ts` | **G-41**/**G-43** reyestrdan **iteratsiya qiladi**; darvoza tekshirayotgan qiymatni **import qilmaydi**, ikkinchi marta **yozadi** (05-15 darsi) |
| **W0-F3** | `frontend/scripts/report-copy.test.mjs` | yangi | ⛔ **G-38(a)**, **G-41**, **G-42**, **G-43**. `stripComments()` `bulk-action-surface.test.mjs:163-225` dan **ko'chiriladi** |
| **W0-F4** | `REPORT_ERROR_CODES` | `lib/report-errors.ts` | §14.9; `error-codes.test.mjs` (G-17) **uchala tilda** talab qiladi |
| **W0-F5** | `05-UI-SPEC.md` §15 ommaviy-amal qatoriga `` `components/reports/**` `` | mavjud fayl (**1 qator**) | [M-4] §16.5. ⛔ **Birinchi `components/reports/*.tsx` bilan bitta commitda** |
| **W0-F6** | `useAccuracyReport()` ni `{from, to}` oladigan qilib **kengaytirish** | `lib/occupancy-queries.ts:171` | ⛔ **Ikkinchi hook YOZILMAYDI** [M-11]; `accuracyKey` allaqachon `from`/`to` oladi |
| **W0-F7** | `confusion-matrix.tsx` ustidagi ⛔ **eskirgan izohni tuzatish** | mavjud fayl | ⚠⚠ §9.1 — izoh «davr tanlagichi yo'q» deydi; tanlagich qurilgach izoh **kodda yolg'on hujjat** bo'lib qolardi (`market-queries.ts:1067-1074` dagi WR-09 darsi aynan shu) |

⛔ **Hech qaysi Wave 0 ishi `rbac.ts`/`rbac.py` ga tegmaydi** [M-6].

### 5.2 Yangi komponentlar

| Fayl | Yuza | Vazifa | Bo'lim |
|------|------|--------|--------|
| `reports/period-picker.tsx` | Y-1, Y-2 | ⛔ `?from=&to=`, maks **kecha**, 4 preset | §4.4 |
| `reports/export-button.tsx` | Y-1, Y-2, Y-3 | ⛔ `apiRequest`+`saveBlob`; **`<a download>` emas** | §12.2 |
| `reports/revenue-report.tsx` | Y-1 | Tushum — kunlik qatorlar + davr yig'indisi | §8.2 |
| `reports/debtors-report.tsx` | Y-1 | ⛔ Qarzdorlik — **sotuvchi kesimida**, ism serverdan (D-07) | §8.3, §8.4 |
| `reports/anomaly-archive.tsx` | Y-1 | Nomuvofiqlik arxivi — ⛔ **ikki sinf ajratilgan** (07 Pattern 4) | §8.5 |
| `reports/compare-table.tsx` | Y-3 | ⛔ Uch ustun + uch farq sinfi | §10.4 |
| `reports/ledger-import.tsx` | Y-3 | Daftar `.xlsx` importi (D-17) | §10.3 |
| `reports/diff-cell.tsx` | Y-3 | ⛔ Farq sinfi — rang **yolg'iz signal emas** | §10.5, §13.4 |
| `app/[locale]/(app)/reports/page.tsx` | Y-1+Y-2 | Blok reyestri (`data-report-block`) | §8.1 |
| `app/[locale]/(app)/reports/compare/page.tsx` | Y-3 | Blok reyestri (`data-compare-block`) | §10.1 |

⛔ **`reports/accuracy-*.tsx` YOZILMAYDI** — `occupancy/confusion-matrix.tsx` **import qilinadi** [M-11], §9.2.

### 5.3 ⛔ Nega `lib/report-queries.ts` YAGONA

1. **G-42 shundan keyin yozilishi mumkin.** Taqiqlangan tokenlar (`chat_id`, `.toFixed(`, `parseFloat(`, kadr tokenlari) **butun faylda** izlanadi; aralash modulda ba'zisi **qonuniy** bo'lardi.
2. **Kesh siyosati bir xil** — hammasi **yozilgan, o'zgarmas** ma'lumot (`to <= kecha`), ya'ni bitta `staleTime` (§5.4).
3. ⛔ **Eksport funksiyasi so'rov moduli bilan bir joyda bo'lishi SHART**: ular **bir xil davrni** olishadi va ajralib qolsa, ekrandagi son bilan fayldagi son **boshqa davrga** tegishli bo'lib qolardi — bu fazaning eng qimmat nosozligi (§1.2).

### 5.4 Kesh kalitlari — tug'ilishidanoq doiralangan

Kalitlar `marketId` bilan **boshlanadi** [MEROS: 04-UI-SPEC; `tenant-cache.test.tsx`].

| Kalit | `staleTime` | `gcTime` | Sabab |
|-------|-------------|----------|-------|
| `[marketId,"report",kind,from,to]` | **5 daq** | standart | ⛔ `to <= kecha` → ma'lumot **o'zgarmas** (D-03: hosila, lekin manbasi yopilgan kun) |
| `[marketId,"occupancy","accuracy",from,to]` | ⛔ **mavjud kalit** [KOD: `occupancy-queries.ts:82`] | mavjud | ⛔ Ikkinchi kalit **yaratilmaydi** — `/occupancy` va `/reports` bir xil davrda **bir xil keshni** ulashadi va shu bilan «ikki xil haqiqat» **imkonsiz** bo'ladi |
| `[marketId,"compare",day]` | **30 s** | standart | Daftar importi uni **o'zgartiradi** |

⛔ **Daftar importidan keyin — `invalidateQueries`, `removeQueries` EMAS.** Sabab 6-fazadan **farqli**: u yerda keshdan chiqarish kerak edi, chunki eski summa **noto'g'ri pul yig'ishga** olib borardi; bu yerda keshdan chiqarish jadvalni **bo'shatib**, admin importni **muvaffaqiyatsiz** deb o'ylardi. ⛔ Faqat **bitta** kalit: `[marketId,"compare",day]`.

⛔ **Eksport keshlanmaydi** — u `useQuery` emas, oddiy `async` funksiya [MEROS: `market-queries.ts:1143-1150` `downloadTemplate` mulohazasi].

### 5.5 ⛔⛔ Shaxsiy ma'lumot: bu yerda qoida 7-fazadagidan TESKARI [QAROR — D-07]

| Nima | 7-faza (`components/reconciliation/**`) | ⛔ 8-faza (`components/reports/**`) |
|------|----------------------------------------|-------------------------------------|
| `vendor_name` | ⛔ **TAQIQ** (G-36) | ✅ ⛔ **QONUNIY** — D-07: qarzdorlik ro'yxatida ism **serverda joinlanadi** |
| `phone`, `full_name` | ⛔ TAQIQ | ⛔ **TAQIQ QOLADI** — ro'yxatga faqat **ism** kerak, aloqa ma'lumoti emas |
| `chat_id`, `telegram_*` | ⛔ TAQIQ | ⛔ **TAQIQ QOLADI** |
| Audit izi | har so'rov | ⛔ **Har hisobot so'rovi/eksporti AYNAN BITTA `audit_read`** — sotuvchi boshiga emas (D-07) |

⚠⚠ **Bu farq darvozada ochiq yozilishi SHART** (§16.6, G-42): ikkala katalogga bir xil taqiq ro'yxatini qo'llash D-07 ni **birinchi kunidayoq** buzardi, teskarisi esa 7-fazaning C-10 himoyasini yumshatardi. ⛔ **Ikki katalog — ikki ro'yxat.**

### 5.6 RBAC — juftlik tegilmaydi [M-6]

`report_view` **mavjud** va **aynan** `director` + `market_admin` da. Ya'ni:

- ⛔ `rbac.py` **tegilmaydi**, `rbac.ts` **tegilmaydi**, `role-gate.test.mjs` (G-8) **o'zgarmaydi**;
- ⛔ D-04 ning «kassir ko'rmaydi» kafolati **bugundan mexanik**;
- ⛔ `platform_admin` da `report_view` **yo'q va berilmaydi** — [QAROR] D-04 dagi «(+ platforma admini)» **qavs ichida** yozilgan va bugungi matritsa uni bermagan. Berilsa, platforma admini **har bozorning** qarzdorlik ro'yxatini (ismlar bilan) ko'rardi — bu C-10 ning bevosita kengayishi. **Tetigi:** platforma admini qo'llab-quvvatlash uchun hisobotni ko'rishi kerak bo'lsa, to'g'ri tuzatish — **ikkala matritsada bitta commitda** `report_view` berish, marshrut qamrovi matritsasini yangilash va buni `08-HUMAN-UAT.md` da yozib qo'yish.

---

## 6. Bo'shliq

### 6.1 Panjara — meros, kengaymaydi

**4-panjara:** `4 · 8 · 12 · 16 · 24 · 32 · 48` (Tailwind `1 · 2 · 3 · 4 · 6 · 8 · 12`).

| Kontekst | Qiymat |
|----------|--------|
| Blok (Card) ichki bo'shlig'i | `p-4` (16) mobil · `p-6` (24) desktop |
| Bloklar orasi | `gap-6` (24) |
| Jadval katagi | `px-3 py-2` (12/8) |
| Tugma va boshqaruvlar orasi | `gap-2` (8) |
| Preset `<select>` + ikki sana maydoni | `gap-2` (8), o'ralganda `gap-y-3` (12) |
| Ikonka ↔ matn | `gap-2` (8) |

⛔ **Istisnolar — barchasi MEROS, yangi istisno YO'Q:** 44px barmoq nishoni (`min-h-11`, WCAG 2.5.5) · 56px mobil pastki panel · 20px karta ichki `x` (mavjud `Card`).

⛔ **Yuklab olish tugmasi `size="md"` (40px), `lg` EMAS** — u desktop yuzasi (direktor kompyuterda hisobot chiqaradi) va sahifada 4 marta takrorlanadi; `lg` ularni sahifaning eng katta elementiga aylantirardi. ⛔ **Istisno: `/reports/compare` dagi `[Daftarni yuklash]` — `size="lg"`**, chunki uni bozor admini **telefonda** ham bosadi (parallel rejim dala ishi).

---

## 7. Tipografiya

### 7.1 To'rt rol, ikki og'irlik — o'zgarmaydi

| Rol | O'lcham | Tailwind | Og'irlik | Line-height | 8-fazada qayerda |
|-----|---------|----------|----------|-------------|------------------|
| **Display** | **24px** | `text-2xl` | **600** | 1.2 | ⛔ Davr yig'indisi (tushum) — sahifada **aynan bitta** Display |
| **Heading** | **18px** | `text-lg` | **600** | 1.2 | Blok sarlavhalari (4 ta) |
| **Body** | **14px** | `text-sm` | 400 / 600 | 1.5 | Jadval kataklari, tugmalar, yorliqlar |
| **Caption** | **12px** | `text-xs` | 400 / 600 | 1.5 | Davr jumlasi, maxraj, izohlar, bo'sh holat tavsifi |

⛔ **Beshinchi o'lcham qo'shilmaydi.** [M-15] `text-base` (7) va `text-xl` (3) — 8 fayldagi **meros deviatsiyalar**; 8-faza ularga **tegmaydi** (ular hisobot yuzasida emas) va **yangisini qo'shmaydi**. **G-42(e)** `components/reports/**` da `text-base`/`text-xl`/`text-3xl`/`text-\[` ni **0** ga qulflaydi.

### 7.2 ⛔ Nima uchun davr yig'indisi Display, qolgan hamma raqam Body

Sahifada **o'nlab** raqam bo'ladi. Agar har blokning yig'indisi Display bo'lsa, **to'rtta teng katta raqam** bir-biri bilan raqobatlashardi va direktor «eng muhimi qaysi?» degan savolga javob **topmasdi**. ⛔ Aynan bitta Display — **davr tushumi** — chunki RECON-04 ning birinchi jumlasi shu.

⛔ **Qarzdorlik yig'indisi Display OLMAYDI** va bu ataylab: u **salbiy** ko'rsatkich va uni tushum bilan teng kattalikda chizish sahifani «ikki katta raqam, qaysi biri yaxshi?» qilardi. U `text-lg font-semibold text-danger-text` (§13.4).

### 7.3 `font-mono` — solishtiriladigan ustunlar uchun [MEROS: 05/06-UI-SPEC]

| Oladi | Olmaydi |
|-------|---------|
| Jadval ustunlaridagi summa, foiz, sana | Proza jumlasidagi son («{n} ta javobdan…») |
| ⛔ Solishtiruvning **uch ustuni va farq ustuni** — ular **vertikal solishtiriladi** | Blok sarlavhasi, tugma matni |
| Aniqlik matritsasi kataklari va uch oraliq (mavjud) | Bo'sh holat matni |

---

## 8. Y-1 — Davr hisobotlari

### 8.1 Blok reyestri

Sahifa `[data-report-block]` atributi bilan **beshta** blok chiqaradi:

| Blok | Mazmuni | `data-report-content` |
|------|---------|------------------------|
| `period` | ⛔ **BOSHQARUV** — davr tanlagichi | ⛔ **YO'Q** (`CONTENT_EXEMPT`) |
| `revenue` | Tushum | ✅ `revenue-report.tsx` chiqaradi |
| `debtors` | Qarzdorlik ro'yxati | ✅ `debtors-report.tsx` chiqaradi |
| `anomalies` | Nomuvofiqlik arxivi | ✅ `anomaly-archive.tsx` chiqaradi |
| `accuracy` | AI aniqligi | ✅ ⛔ **o'ram** chiqaradi (`ConfusionMatrix` tegilmaydi, §9.2) |

⛔ **Blok to'plami DAVRGA QARAB O'ZGARMAYDI** — beshalasi **har doim** chiziladi. Sabab: maksimum allaqachon **kecha** (§4.4), ya'ni «ma'lumot hali tug'ilmagan» holati **umuman yuzaga kelmaydi**; blokni yashirish esa bo'sh davrni **muvaffaqiyat** kabi ko'rsatardi. Bo'sh davr — **bo'sh holat** (§14.7), yo'q blok emas.

⛔ **`data-report-content` ni sahifa CHIQARMAYDI** — uni **ro'yxat komponentining O'ZI** chiqaradi (07 G-29(b) mexanikasi): shunda «blok o'rami bor, ichi bo'sh» holati darvozada **qizaradi**.

### 8.2 Tushum hisoboti

| Element | Kontrakt |
|---------|----------|
| Yig'indi | ⛔ **Display**, `font-mono`, `useFormatter().number()` + `reports.amountUnit` |
| Davr jumlasi | ⛔ **Yig'indi bilan BIR BLOKDA**, `text-xs text-text-muted`: «{from} — {to}» — ⛔ serverning javobidan (§8.7) |
| Qatorlar | Biznes-kun kesimida: sana · hisoblangan · to'langan · farq |
| ⛔ **Farq ustuni** | `to'langan − hisoblangan`; ⛔ manfiy → `text-danger-text`, musbat → `text-text` (⛔ **yashil emas**: ortiqcha to'lov **yaxshilik emas**, u ham tekshiriladigan holat) |
| Oylik ko'rinish | ⛔ **Alohida rejim EMAS** — `thisMonth`/`lastMonth` preseti **o'sha jadvalni** beradi. «Oylik hisobot» — **davr**, ekran turi emas |
| Sahifalash | §8.6 |

⛔ **Klientda YIG'INDI HISOBLANMAYDI** (D-03): `rows.reduce(...)` **yozilmaydi** — server yig'indini beradi. Sabab 05-14 darsi: klientdagi qayta hisob **xato bo'lib emas, IKKINCHI JAVOB bo'lib** chiqadi (yaxlitlash, sahifalash, filtr — uchtasi ham ajratadi). **G-42(b)** buni `reduce(`/`.toFixed(`/`parseFloat(` taqig'i bilan o'lchaydi.

### 8.3 Qarzdorlik ro'yxati

| Element | Kontrakt |
|---------|----------|
| Kesim | ⛔ **Sotuvchi** (rasta emas) — RECON-04 «qarzdorlik reestri» |
| Ustunlar | Sotuvchi ismi · rasta(lar) · qarz summasi · eng eski qarz kuni |
| Tartib | ⛔ **Qarz summasi bo'yicha kamayish** — direktorning birinchi savoli «eng kattasi kim?» |
| Yig'indi | `text-lg font-semibold text-danger-text` (⛔ Display **emas**, §7.2) |
| Manba | `vendor_outstanding()` [MEROS: 08-CONTEXT canonical refs] |
| ⛔ **Ism** | **Serverda joinlanadi** (D-07); ⛔ klient ikkinchi so'rov **yubormaydi** |

### 8.4 ⛔ Topilmagan ism — BO'SH KATAK [QAROR — D-08]

| Holat | Ekranda |
|-------|---------|
| Ism bor | Ism |
| ⛔ Ism yo'q (biriktirilmagan / o'chirilgan sotuvchi) | ⛔ **Bo'sh katak** — na «—», na «Noma'lum», na «Sotuvchi #123» |

⛔ **Sabab (05-14 darsi):** to'qilgan qiymat (`—`, `Noma'lum`) **ma'lumot bordek** ko'rinadi va u **eksportga ham tushadi** — chop etilgan varaqda «Noma'lum» qatori buxgalter uchun **haqiqiy sotuvchi nomi** bo'lib o'qilardi. Bo'sh katak esa **o'zi savol tug'diradi** va bu to'g'ri natija.

⚠ A11y: bo'sh `<td>` skrinriderda **jimgina** o'tadi. Shuning uchun katak `<td>` **bo'sh qolmaydi**, uning ichida `<span class="sr-only">{reports.vendorUnknown}</span>` bo'ladi — ⛔ **vizual jihatdan bo'sh, semantik jihatdan nomlangan**. Bu 04-11 dagi «yo'q kadr uch kanalda» qarorining aynan sinfi.

### 8.5 Nomuvofiqlik arxivi

| Qoida | Kontrakt |
|-------|----------|
| ⛔ **Ikki sinf ajratilgan** | `unpaid` (band, lekin to'lovsiz) va `unregistered` (ro'yxatga olinmagan savdo) — ⛔ **hech qachon qo'shilmaydi** [MEROS: 07 Pattern 4, G-30] |
| Ko'rsatish | ⛔ **Bitta jadval, `kind` ustuni bilan** — chunki arxivda davr bo'ylab **xronologiya** muhim; ikki jadval bir hodisani ikki joyda qidirtirardi. ⛔ **Lekin yig'indi ikkita, alohida** |
| ⛔ **Dalil** | ⛔ **Kadr YO'Q** [MEROS: 07 D-03]. Arxivda — `/billing?day=…` ga **havola** yoki `snapshot_id` **identifikatori**; ⛔ **eksportda ham faqat identifikator** |
| Case holati | Yopiq 4 a'zo (07 D-12), mavjud `recon.caseStatus.*` kalitlari **qayta ishlatiladi** |

⛔ **`components/reports/**` da kadr tokenlari 0** (**G-42(d)**): `<img`, `next/image`, `useEvidenceImageHref`, `URL.createObjectURL`, `/snapshots/`. ⚠ `URL.createObjectURL` taqig'i **`saveBlob()` ga tegmaydi**, chunki u `lib/market-queries.ts` da yashaydi va `components/reports/**` skan maydonidan **tashqarida** — ⛔ bu ochiq yozilishi shart, aks holda ijrochi eksportni buzardi.

### 8.6 Sahifalash — keyset, mavjud naqsh

Uch hisobotning ham qatorlari sahifalanadi [MEROS: 07 DQ-4 envelope naqshi]. ⛔ **Lekin:**

| Nima | Qoida |
|------|-------|
| Ekrandagi yig'indi | ⛔ **BUTUN DAVRNIKI**, ko'rinayotgan sahifaniki **emas** — server beradi |
| ⛔ **Eksport** | ⛔ **BUTUN DAVR, sahifalashsiz** — server jadvalni to'liq quradi |
| Yig'indi yonidagi jumla | ⛔ **Majburiy**: «{shown} qatordan {total} tasi ko'rsatilmoqda» — usiz direktor ekrandagi 50 qatorni **butun davr** deb o'qirdi |

⛔⛔ **Eksportda sahifalash CHEGARASI bo'lsa, u JIM QOLMAYDI:** server chegarani qo'ysa (masalan 50 000 qator), fayl **kesilgan** bo'lishi mumkin — bu holda ⛔ **eksport rad etiladi** (`report_too_large` xatosi, §14.9) va foydalanuvchiga **davrni qisqartirish** aytiladi. ⛔ Kesilgan faylni jimgina berish — bu fazadagi eng qimmat nosozlik sinfi (§1.2).

### 8.7 ⛔ Davr HAR DOIM serverning javobidan chiziladi [QAROR]

Ekranda ko'rinadigan «{from} — {to}» jumlasi ⛔ **`nuqs` holatidan EMAS**, **javobdagi `from_date`/`to_date` dan** olinadi.

⛔ **Sabab:** server so'ralgan davrni **qisqartirishi** mumkin (maksimum kecha, ma'lumot boshlanish sanasi, chegara). So'ralgan davrni chizish «men oktyabrni so'radim, oktyabr ko'rsatildi» degan **yolg'on tasdiq** berardi — holbuki javob sentyabr 15 dan boshlangan bo'lishi mumkin. ⛔ Bu `ConfusionMatrix` ning **bugungi xulqi** [KOD: `confusion-matrix.tsx:123` `accuracyFrom` `report.from_date`/`report.to_date` dan] va u **uchala hisobotga** ham tarqatiladi. **G-39** buni o'lchaydi.

---

## 9. Y-2 — AI aniqlik hisoboti

### 9.1 ⛔⛔ 5-faza bilan ziddiyat YO'Q — topshiriq REJALASHTIRILGAN [M-10]

`confusion-matrix.tsx` ustidagi izoh «⛔ DAVR TANLAGICHI HAM … YO'Q» deydi. Bu **5-fazaning o'z yuzasi haqida** va u ⛔ **hamon kuchda**. Server tomondagi manba esa topshiriqni ochiq beradi [KOD: `occupancy.py:174-186`]:

> «⛔ DAVR TANLAGICHI YO'Q (**§16.2 — 8-fazaning hisobot yuzasi**), lekin `from`/`to` parametrlari BOR: ular klientga emas, TESTGA va **kelajakdagi eksportga** kerak.»

| Nima | Holat |
|------|-------|
| ⛔ Davr tanlagichi **`/reports` da** | ✅ **Quriladi** — D-09(c), topshiriq 5-fazada yozilgan |
| ⛔ Davr tanlagichi **`/occupancy` da** | ⛔ **QURILMAYDI** — 5-fazaning qarori o'z yuzasida kuchda |
| ⛔ `eval`/`train` filtri | ⛔ **HECH QAYERDA QURILMAYDI** — u 70/30 bo'linishining ma'nosini yo'qotardi (D-14). ⛔ Bu **muzokarasiz** va **G-42(c)** da `queue_kind`/`purpose`/`train`/`eval` tokenlari bilan o'lchanadi |

⚠⚠ **W0-F7 — izoh TUZATILADI:** `confusion-matrix.tsx` ustidagi «davr tanlagichi yo'q» jumlasi ⛔ **komponent ikki yuzada ishlashini** aytadigan qilib qayta yoziladi (`/occupancy` — server standarti; `/reports` — chaqiruvchi beradi). Eskirgan izohni qoldirish **kodda yolg'on hujjat** qoldirardi va keyingi ijrochi ikkinchi komponent yozardi.

### 9.2 ⛔ `ConfusionMatrix` QAYTA ISHLATILADI [M-11]

```
reports/page.tsx
  └─ <div data-report-block="accuracy">
       └─ <AccuracyBlock from={from} to={to}/>     ← o'ram (yangi, ~30 qator)
            ├─ useAccuracyReport({from, to})       ← MAVJUD hook, kengaytirilgan (W0-F6)
            ├─ <ConfusionMatrix report={report}/>  ← MAVJUD komponent, TEGILMAYDI
            └─ <ExportButton kind="accuracy"/>     ← yangi
```

⛔ **`ConfusionMatrix` ning props'i o'zgarmaydi** (`{report}`) va u ⛔ **davr yorlig'ini tashqaridan OLMAYDI** — u `report.from_date`/`report.to_date` dan o'zi chizadi (§8.7). **G-39(c)** buni qulflaydi: komponent `from`/`to`/`period`/`label` nomli prop **qabul qilmaydi**.

⛔ **Ikkinchi aniqlik komponenti yozilmaydi** va **G-42(f)** buni o'lchaydi: `components/reports/**` da `confusion`, `matrix`, `wilson`, `percentView` **ta'riflari** yo'q (⛔ `ConfusionMatrix` ni **import qilish** — qonuniy va u istisno sifatida ochiq yozilgan).

### 9.3 ⛔ O'lchanmagan son chizilmaydi [D-10 — WR-05 ning yopilishi]

| Holat | Ekranda |
|-------|---------|
| `measured === true` | Matritsa + uch oraliq (mavjud xulq) |
| ⛔ `measured === false` | ⛔ **Foiz belgisi DOM'da 0 marta.** Namuna holati jumlasi **ko'rinadi** (mavjud xulq) + ⛔ **nomlangan sabab**: «Bu davrda javoblar soni o'lchov uchun yetarli emas ({n} ta, kamida {min_sample} kerak)» |
| ⛔ So'rov yiqildi | ⛔ **Xato holati** — na «0 %», na bo'sh matritsa. ⛔ **Bu WR-05 ning aynan matni** (07 ko'rigi: «yiqilgan so'rov 0 % bo'lib chiziladi») |
| Davr bo'sh (`n === 0`) | `measured === false` shoxi bilan **bir xil** |

⛔ **`min_sample` va `measured` SERVERDAN** [KOD: `api-types.ts:1966-1968`] — ⛔ klient `n >= 20` ni **qayta yozmaydi**; ikkinchi chegara ikkinchi javob bo'lardi.

### 9.4 ⛔ AI-02 ning holati yashirilmaydi [D-11]

Aniqlik bloki **ostida**, `text-xs text-text-muted` bilan, ⛔ **doimiy** jumla:

> «Bu ulush **nazoratchining ko'r javoblaridan** hisoblanadi. Modelning o'zi CI'da o'lchanmagan.»

| Qoida | Sabab |
|-------|-------|
| ⛔ `tone="warning"` **emas**, `role="alert"` **emas** | Bu **holat**, xato emas (07 D-22 sinfi). Ogohlantirish bezagi uni har ochilishda **shovqin** qilardi va uch kundan keyin o'qilmay qolardi |
| ⛔ Jumla **shartsiz** — `measured` dan **mustaqil** | Aniqlik o'lchangan kunlarda uni yashirish «endi model tekshirilgan» degan **noto'g'ri xulosa** berardi |
| ⛔ **Eksportga ham tushadi** (§12.6) | Chop etilgan varaq kontekstsiz tarqaladi |

### 9.5 Ikki xato — ikki jumla, hech qachon bitta [MEROS: `confusion-matrix.tsx:44-49`]

| Xato | Ma'nosi | Ekrandagi jumla |
|------|---------|------------------|
| ⛔ **Band deb xato** = `fp/(tp+fp)` | ⛔ **Nizo xavfi** (ishonch) | «Band deb xato — sotuvchi bilan nizo xavfi» |
| ⛔ **Bo'sh deb xato** = `fn/(tp+fn)` | ⛔ **Yig'ilmagan patta** (pul) | «Bo'sh deb xato — yig'ilmagan patta» |

⛔ Ikkalasini bitta «xatolik ulushi» ga qo'shish **taqiqlanadi** — ular turli oqibatga ega va turli harakat talab qiladi. Formulalar **o'zgarmaydi** (D-09) va **klientda hisoblanmaydi**.

---

## 10. Y-3 — Uch tomonlama solishtiruv

### 10.1 Blok reyestri

| Blok (`data-compare-block`) | Mazmuni | `data-compare-content` |
|------------------------------|---------|-------------------------|
| `day` | ⛔ **BOSHQARUV** — kun tanlagichi | ⛔ **YO'Q** (`CONTENT_EXEMPT`) |
| `ledger` | Daftar importining **holati** + yuklash | ✅ `ledger-import.tsx` |
| `comparison` | Uch ustunli jadval + uch farq sinfi | ✅ `compare-table.tsx` |

⛔ **`CONTENT_EXEMPT.size === 1`** alohida assert bilan (07 G-29(b) mexanikasi).

### 10.2 Kun tanlagichi — 6-fazanikini QAYTA ISHLATADI

⛔ **Ikkinchi nusxa yozilmaydi** [MEROS: `reconciliation/day-picker.tsx` ning to'liq mulohazasi]. Standart **kecha**, maksimum **bugun**… ⛔ **YO'Q — maksimum KECHA.**

| Qoida | Y-3 da | Nega 6-fazadan farqli |
|-------|--------|------------------------|
| Standart | **kecha** | Bir xil |
| ⛔ Maksimum | ⛔ **kecha** (`/billing` da **bugun**) | ⛔ Bugungi tizim summasi **hali yopilmagan** (D+1 04:10) va daftar ham kun oxirida yig'iladi. «Bugun» ni solishtirish **har doim** farq ko'rsatardi va uchala sinf ham **soxta** bo'lardi |

⛔ **Oqibat:** `useBillingDay()` **to'g'ridan-to'g'ri qayta ishlatilmaydi** — u `todayIso` ni maksimum qiladi. Y-3 uchun ⛔ **`useCompareDay()`** yoziladi va u **`useBillingDay()` ning ichidagi yordamchilarni** (`businessDayIn`, `isValidIsoDay`, `shiftIsoDay`) ishlatadi, ⛔ **sana arifmetikasini qaytadan yozmaydi** [M-16].

### 10.3 Daftar importi [D-17]

⛔ **2-fazaning import naqshi qayta ishlatiladi**, ikkinchi oqim qurilmaydi:

| Qadam | Mexanizm | Manba |
|-------|----------|-------|
| 1. Shablon | `[Shablonni yuklab olish]` → `apiRequest` + `saveBlob` | `import-panel.tsx:114` |
| 2. Fayl tanlash | `<input type="file" accept=".xlsx">` | `import-panel.tsx:222` |
| 3. Yuborish | ⛔ **all-or-nothing**; 422 → xatolar ro'yxati | `imports.py` naqshi |
| 4. Xatolar | 5 tasi ekranda, qolgani `.xlsx` bo'lib | `import-errors.tsx` |
| 5. ⛔ Almashtirish | Shu kun uchun daftar **bor** bo'lsa → **DL-6** | §14.8 |

⛔ **Shablon ustunlari — aynan ikkita:** rasta kodi · daftar summasi (D-17). Uchinchi ustun (sotuvchi ismi, izoh) **qo'shilmaydi**: daftar **qog'oz** va har qo'shimcha ustun kunlik ishni sekinlashtiradi.

### 10.4 Uch ustun — manbalar va ularning umri [D-18]

| Ustun | Manba | Turi | Yo'q bo'lsa |
|-------|-------|------|-------------|
| **Daftar** | Import qatori | Yozilgan | ⛔ **Butun jadval chizilmaydi** (§10.5) |
| **Tizim** | `daily_charges` + `payments` | Yozilgan | Nol — **haqiqiy** nol (rasta bo'sh yoki to'lov yo'q) |
| **AI-kutilgan** | ⛔ **Hosila:** band rasta × amaldagi tarif | ⛔ **Saqlanmaydi** (D-03/D-18) | ⛔ **Bo'sh katak** — bandlik ma'lumoti yo'q kun uchun nol **yozilmaydi** |

⛔⛔ **«AI-kutilgan» ustunidagi NOL va BO'SH KATAK bir narsa EMAS:** nol = «AI rastani bo'sh dedi» (o'lchangan); bo'sh = «o'sha kun uchun bandlik ma'lumoti yo'q» (o'lchanmagan). Ularni tenglashtirish D-10 ning bevosita buzilishi bo'lardi va **G-40(c)** buni o'lchaydi.

### 10.5 ⛔ Uch farq sinfi — hech qachon qo'shilmaydi [specifics + D-18]

| Sinf | Sharti | Ma'nosi | `tone` | Ikonka | Matn kanali |
|------|--------|---------|--------|--------|-------------|
| **`ledger_over`** | daftar > tizim | ⛔ **Yo'qotish shubhasi** | `danger` | `TrendingDown` | «Daftar ortiq» |
| **`system_over`** | tizim > daftar | Daftar kamchiligi / yozuv xatosi | `warning` | `NotebookPen` | «Tizim ortiq» |
| **`ai_mismatch`** | AI-kutilgan ≠ tizim | Bandlik–billing farqi | `neutral` | `Diff` | «Bandlik farqi» |
| **`match`** | uchalasi teng | — | ⛔ **Badge YO'Q** | — | ⛔ **Bo'sh** |

⛔⛔ **«Jami farq» YOZILMAYDI.** Har sinf **o'z sanog'i** bilan blok sarlavhasida: «Daftar ortiq: {n} · Tizim ortiq: {m} · Bandlik farqi: {k}». ⛔ Bitta songa siqish uch **turli** harakatni («pulni qidiring» / «daftarni tuzating» / «detektorni tekshiring») bitta ma'nosiz songa aylantirardi — 6-faza D-05 va 07 Pattern 4 ning aynan sinfi. **G-41** buni o'lchaydi.

⛔ **`match` qatori ham jadvalda QOLADI** (yashirilmaydi): «300 rastadan 287 tasi mos» — ⛔ **maxraj** imzolanadigan hujjatda majburiy, aks holda 13 qatorli varaq «bozorda 13 ta rasta bor» bo'lib o'qilardi (07 G-32 darsi).

### 10.6 ⛔ Daftar yuklanmagan kun — «farq yo'q» EMAS [D-10]

| Holat | Ekranda |
|-------|---------|
| ⛔ Daftar **yo'q** | ⛔ **`comparison` bloki JADVAL CHIZMAYDI.** Nomlangan holat: «Bu kun uchun daftar yuklanmagan» + `[Daftarni yuklash]` ga yo'naltirish |
| Daftar bor, qator yo'q | Bo'sh holat: «Daftarda bu kun uchun qator yo'q» |
| Daftar bor, qatorlar bor | Jadval |

⛔⛔ **Bu bandning butun mazmuni:** daftar yuklanmaganda uch ustunli jadvalni «hamma farq 0» bilan chizish ⛔ **muvaffaqiyatli solishtiruv** bo'lib ko'rinardi va **imzolanardi** — ya'ni parallel rejimning butun maqsadi (SC#5) jimgina yo'qolardi. Bu WR-05 sinfining eng qimmat ko'rinishi.

### 10.7 Imzo — faqat faylda [D-19]

| Nima | Qayerda |
|------|---------|
| ⛔ **Imzo qatorlari** (bajaruvchi / tasdiqlovchi) | ⛔ **Faqat `.xlsx` ning pastida** (§12.6) |
| ⛔ `[Imzolash]` tugmasi | ⛔ **QURILMAYDI** — raqamli imzo yo'q (D-19); tugma uni **bordek** ko'rsatardi |
| ⛔ «Imzolangan» holati / sanasi | ⛔ **QURILMAYDI** — tizim qog'ozda nima bo'lganini **bilmaydi** va bilmagan narsasini ko'rsatmaydi |

---

## 11. Zaxira va tiklash — UI'da NIMA BOR va NIMA YO'Q [FOUND-07]

| Nima | Holat |
|------|-------|
| ⛔ Zaxira boshqaruvining veb paneli | ⛔ **QURILMAYDI** — D-13: compose xizmati + konteyner ichidagi jadval |
| ⛔ «Oxirgi zaxira: …» ko'rsatkichi | ⛔ **QURILMAYDI** — u `/internal/self-check` da (07 D-25 sinfi) |
| Zaxira nosozligi alerti | ✅ ⛔ **ALLAQACHON BOR** [M-12]: `backup_stale`, `CRITICAL`, `never_suppressed=True`, `HEARTBEAT_STALE_HOURS = 26` |
| Alert matni uch tilda | ✅ ⛔ **ALLAQACHON BOR**: `snapshots.alertKey.backupStale` — uz «Zaxira nusxa yangilanmadi» · ru «Резервная копия не обновлялась» |
| Tiklash mashqi | ⛔ **UI'da yo'q** — `08-HUMAN-UAT.md` bandi + CI mexanizmi (D-16) |

⛔ **8-faza bu yerda matn ham, komponent ham QO'SHMAYDI.** Uning ishi — `backup` komponentining **yurak urishini yozadigan jarayonni** qurish; UI o'sha yozuvning **yo'qligini** allaqachon ko'ra oladi. ⛔ Bu «mavjud mexanizmga ulanish, ikkinchisini qurmaslik» qoidasining eng toza namunasi.

⛔ **«Backup» so'zi ekran matnida YOZILMAYDI** [M-13]: `Backup` → `Баcкуп` (aralash alifbo) va u overrides'da **yo'q**. ⛔ Yagona shakl — «**Zaxira nusxa**» va u allaqachon katalogda.

---

## 12. ⛔⛔ `.xlsx` eksport kontrakti — bu fazaning yadrosi

### 12.1 To'rtta eksport + bittasi

| # | Eksport | Marshrut | Reyestr |
|---|---------|----------|---------|
| 1 | Tushum | `/reports` `revenue` | `REPORT_KINDS` |
| 2 | Qarzdorlik ro'yxati | `/reports` `debtors` | `REPORT_KINDS` |
| 3 | Nomuvofiqlik arxivi | `/reports` `anomalies` | `REPORT_KINDS` |
| 4 | AI aniqligi | `/reports` `accuracy` | `REPORT_KINDS` |
| 5 | ⛔ Uch tomonlama solishtiruv | `/reports/compare` | ⛔ **Reyestrdan TASHQARIDA** — davri **kun**, shakli **imzoli** |

⛔ **`REPORT_KINDS` — aynan 4 a'zo** va **G-43(a)** buni to'plam tengligi bilan qulflaydi. ⛔ Solishtiruv eksporti reyestrga **qo'shilmaydi**: u boshqa davr modeli va boshqa fayl shakliga ega; bitta reyestrga tiqish `REPORT_KINDS` ni «hisobot turi» dan «yuklab olinadigan narsa» ga aylantirardi va davr parametrlari **ixtiyoriy** bo'lib qolardi.

### 12.2 Yuklab olish mexanikasi — ⛔ YAGONA yo'l [§0.2]

```ts
// lib/report-queries.ts — YAGONA eksport yo'li
export async function downloadReport(kind, params): Promise<void> {
  const response = await apiRequest(buildReportPath(kind, params)); // Bearer + 401-refresh + !ok da ApiError
  saveBlob(await response.blob(), filenameFrom(response, kind, params));
}
```

| Qoida | Kontrakt |
|-------|----------|
| ⛔ `<a href … download>` | ⛔ **YOZILMAYDI** — **G-38(b)** `components/reports/**` da `download` atributini **0** ga qulflaydi |
| ⛔ `window.open` / `location.href` | ⛔ **YOZILMAYDI** — bir xil tokensiz muammo |
| ⛔ Ikkinchi `fetch` | ⛔ **YOZILMAYDI** — `apiRequest` **yagona** |
| ⛔ Klientda `.xlsx` qurish | ⛔ **YOZILMAYDI** (D-05) |
| Xato | ⛔ **Inline**, tugma yonida (`import-errors.tsx:221` naqshi) — ⛔ toast **emas**: toast g'oyib bo'ladi va foydalanuvchi tugmani qayta bosadi |
| Yuklanish holati | Tugma `disabled` + `aria-busy="true"` + matn **o'zgarmaydi** (o'lcham sakramasin) |

### 12.3 Fayl nomi — SERVER egasi, klient o'qiydi [QAROR — D-06]

D-06 nomni `{market}_{hisobot}_{from}_{to}.xlsx` deb belgilagan. ⛔ **Bozor nomi — o'zbekcha matn** (bo'sh joy, apostrof, kirill) va u fayl tizimida ham, `Content-Disposition` da ham **xavfsiz emas**.

| Qatlam | Qoida |
|--------|-------|
| ⛔ **Nomni SERVER quradi** | Bozor nomini ASCII slug'ga aylantirish **bir joyda** — `{market-slug}_{kind}_{from}_{to}.xlsx` |
| Klient | ⛔ `Content-Disposition` dan **o'qiydi** [M-9: bir xil origin, sarlavha ochiq] |
| ⛔ **Zaxira yo'l** | Sarlavha yo'q/o'qib bo'lmasa → ⛔ **`sbozor-{kind}-{from}_{to}.xlsx`** (bozorsiz). ⛔ Bo'sh nom, `undefined.xlsx` yoki `download` **hech qachon** |

⛔ **Rad etilgan muqobil:** nomni **klientda** qurish. Sabab: slug qoidasi (apostrof, `ʻ`, kirill) ikki tilda **ikki marta** yozilardi va bir kun ajralib ketardi — natijada server `karmana_revenue_….xlsx` deb, klient `Karmana-bozori_….xlsx` deb nomlardi va **qaysi biri hujjat** ekani noaniq bo'lardi.

### 12.4 Fayl mazmunining kontrakti [D-05]

| Qoida | Sabab |
|-------|-------|
| ⛔ **XlsxWriter serverda**, `_freeze_zip` bilan | Bayt determinizmi (02-23 darsi: ZIP sanasi soatdan keladi) |
| ⛔ **Summalar — butun so'm** (`BIGINT` ↔ `int`) | D-06; ⛔ suzuvchi nuqta **yo'q** |
| ⛔ **Sanalar — biznes-kun** (Asia/Tashkent) | D-02 |
| ⛔ **Davr fayl ichida ham** — birinchi qatorda | §1.2 qoida 2: chop etilgan varaqdan davr yo'qolmasin |
| ⛔ **Rasm YO'Q** | 07 D-03 — faqat identifikator/havola |

### 12.5 Eksport tili — so'rovchining profilidan [D-06]

⛔ **Til so'rovda YUBORILMAYDI** — server uni profildan oladi [MEROS: `market-queries.ts:1146-1148` `downloadTemplate` mulohazasi: «Til so'rovda YUBORILMAYDI — server uni profildan oladi (bitta haqiqat manbai)»].

⛔ **Fayldagi atamalar vebdagi bilan AYNI** (D-06 + 07 D-30): «qarz», «patta», «rasta», «smena» — glossariy (`ops/i18n/glossary.json`) ikkala manbani ham o'lchaydi (G7-9).

### 12.6 Solishtiruv eksportining qo'shimcha shakli [D-19]

Faylning **pastida**, jadvaldan keyin, ikki bo'sh imzo qatori:

```
Bajaruvchi (nazoratchi / bozor admini): ______________________  Sana: __________
Tasdiqlovchi (direktor):                ______________________  Sana: __________
```

⛔ Ism **oldindan to'ldirilmaydi** — kim imzolashini tizim **bilmaydi** (D-19: bu qog'oz jarayon). ⛔ AI aniqligi eksportida esa §9.4 jumlasi **majburiy** bo'lib tushadi.

---

## 13. Rang kontrakti (60/30/10)

### 13.1 Taqsimot — o'zgarishsiz, yangi token YO'Q

| Rol | Token | Qiymat [KOD: `globals.css:33-85`] | 8-fazada qayerda |
|-----|-------|-----------------------------------|------------------|
| **Dominant (60%)** | `--color-bg` | `oklch(0.985 0 0)` | Sahifa foni |
| **Ikkilamchi (30%)** | `--color-surface` | `oklch(1 0 0)` | Beshala blok, solishtiruv bloklari |
| | `--color-surface-muted` | `oklch(0.968 0 0)` | `Skeleton`, jadval sarlavha satri, `tone="muted"` |
| **Aksent (10%)** | `--color-accent` | `oklch(0.56 0.19 255)` | §13.3 — **to'rt element** |
| **Destruktiv** | `--color-danger` | `oklch(0.58 0.21 27)` | Qarz summasi, «Daftar ortiq», manfiy farq |
| **Ogohlantirish** | `--color-warning` | `oklch(0.78 0.15 85)` | ⛔ Faqat `bg-warning/20` sifatida — §13.2 |
| **Muvaffaqiyat** | `--color-success` | `oklch(0.63 0.16 150)` | ⛔ **Faqat bitta joy**: daftar importi muvaffaqiyatli toasti |

**Yangi token kiritilmaydi va yangi rang juftligi so'ralmaydi.**

### 13.2 `--color-warning` matn sifatida ISHLATILMAYDI

Sariq tintdagi matn — `bg-warning/20 text-text` (o'lchangan **15,64:1**) [KOD: `badge.tsx:17-25`]. `--color-warning` oq fonda **2,03:1** — falokat. 8-fazada bu **ikki joyda**: «Tizim ortiq» badge'i (§10.5) va namuna to'liqmasligi jumlasi (mavjud, `confusion-matrix.tsx`).

### 13.3 ⛔ Aksent — to'rtta element, beshinchisi yo'q [QAROR]

1. **Fokus halqasi** (`:focus-visible outline`) — barcha interaktiv elementlar;
2. **Faol maydon chegarasi va halqasi** (`focus-visible:border-accent`, `ring-accent/25`);
3. **Joriy navigatsiya elementi** — faqat mobil pastki panelda;
4. ⛔ **`[Daftarni yuklash]` — Y-3 dagi yagona yakunlovchi amal.** Fazadagi **yagona** aksent fonli tugma (`variant="default"`).

> ⛔ **Nega YUKLAB OLISH tugmalari aksent OLMAYDI**: ular **to'rtta** (§12.1) va teng og'irlikda. Har biri `variant="default"` bo'lsa sahifada **to'rtta raqobatlashuvchi aksent** paydo bo'lardi va 10% chegarasi buzilardi; bittasini tanlab aksent berish esa qolgan uchtasini **ikkinchi darajali** deb ko'rsatardi — holbuki RECON-04 uchalasini teng talab qiladi. ⛔ Hammasi **`secondary`**.
>
> ⛔ **Nega `[Daftarni yuklash]` aksent oladi**: u sahifadagi **yagona yozuv** va **raqobatchisi yo'q**; qolgan hamma narsa o'qish. Bu 07-UI-SPEC §13.3 dagi `[Holatni saqlash]` va 06-UI-SPEC §12.3 dagi `[To'lovni tasdiqlash]` mulohazasining aynan o'zi.

⛔ **Aksent ishlatilMAYDIGAN joylar:** to'rtta `[Excel bo'lib yuklab olish]` · `[Shablonni yuklab olish]` · davr tanlagichi va presetlar · kun tanlagichi · jadval sarlavhalari · ⛔ **har qanday summa, foiz yoki farq raqami** · farq badge'lari · sahifalash tugmalari.

**G-42(a):** `components/reports/**` da `variant="default"` — ⛔ **aynan 1 marta**.

### 13.4 Rang hech qachon YAGONA signal emas (WCAG 1.4.1)

| Holat | Rang kanali | Kanal 2 | Kanal 3 |
|-------|-------------|---------|---------|
| **Daftar ortiq** | `tone="danger"` | `TrendingDown` | Badge matni «Daftar ortiq» |
| **Tizim ortiq** | `tone="warning"` | `NotebookPen` | Badge matni «Tizim ortiq» |
| **Bandlik farqi** | `tone="neutral"` | `Diff` | Badge matni «Bandlik farqi» |
| **Mos** | ⛔ **rang yo'q** | ⛔ **ikonka yo'q** | ⛔ **bo'sh** — «mos» **bezak olmaydi** |
| **Qarz summasi** | `text-danger-text` | — | ⛔ **Ustun sarlavhasi** «Qarz» |
| **Manfiy farq (tushum)** | `text-danger-text` | ⛔ **minus belgisi** (formatlagichdan) | Ustun sarlavhasi «Farq» |
| ⛔ **Aniqlik o'lchanmagan** | ⛔ **rang yo'q** | — | ⛔ **Nomlangan sabab** (§9.3) |
| ⛔ **Daftar yuklanmagan** | ⛔ **rang yo'q** | — | ⛔ **Nomlangan holat** (§10.6) |
| **Ism topilmadi** | ⛔ **rang yo'q** | — | ⛔ **`sr-only` matn** (§8.4) |

> ⛔ **«Mos» qatori bezak olmasligi MUZOKARASIZ.** 287 ta yashil belgi 13 ta farqni **ko'mib** yuborardi — imzolanadigan varaqda ko'z **farqni** qidiradi, mos qatorlarni emas. Bu 07-UI-SPEC §13.4 dagi «Asosli/Asossiz» mulohazasining teskari tomoni.

---

## 14. Matn (copywriting) kontrakti

### 14.1 ⛔ Atama qarorlari — kod bir narsa deydi, ekran boshqa narsa

| Kod / DB / talab | ⛔ Ekranda (uz-Latn) | Nega |
|------------------|----------------------|------|
| «qarzdorlik **reestri**» (REQUIREMENTS) | ⛔ **«Qarzdorlik ro'yxati»** | [M-13] `reestr` → `реэстр` (kirillcha imlo `реестр` bo'lishi kerak, «е/э» noaniqlik to'plami). ⛔ Overrides'ga to'rt qo'shimchali shakl yozish o'rniga **mavjud, toza so'z**: `ro'yxat` katalogda allaqachon (`Хатолар рўйхати`). ru esa **«Реестр долгов»** — u qo'lda yoziladi va `долг` o'zagini saqlaydi (G7-9) |
| `backup`, «Backup» | ⛔ **«Zaxira nusxa»** | [M-13] `Backup` → `Баcкуп` (aralash alifbo), overrides'da **yo'q**. Katalogda allaqachon shu shakl bor |
| `.xlsx`, «Excel» | ✅ **«Excel»** — ruxsat | [M-13] `Excel` va `xlsx` overrides `words` da **bor**; `import.title` cy = «**Excel** файлдан юклаш» |
| `ledger` | **«Daftar»** | Bozorda qog'oz daftar shundoq ataladi |
| `expected`/`ai_expected` | ⛔ **«AI-kutilgan»** | ⛔ 07 §12.2 dagi «kutilayotgan» (proyeksiya) bilan **adashtirmaslik** uchun defis bilan va **AI** prefiksi bilan |
| `ledger_over` / `system_over` / `ai_mismatch` | **«Daftar ortiq» / «Tizim ortiq» / «Bandlik farqi»** | §10.5 |
| `revenue` | **«Tushum»** | ROADMAP SC#1 ning so'zi |
| `anomalies` (arxiv) | **«Nomuvofiqlik arxivi»** | 07 «Nomuvofiqliklar» ning davr shakli |
| «hit-rate» / «aniqlik ulushi» | ⛔ **Bu sahifada YO'Q** | ⛔ 07 §14.1: «aniqlik ulushi» = **case hit-rate**; bu yerda «**AI aniqligi**» — ikkalasi bir ekranda **hech qachon** uchrashmaydi (§17.2) |
| `false_occupied` / `false_empty` | **«Band deb xato» / «Bo'sh deb xato»** | ⛔ 05-fazadan **o'zgarishsiz** |

### 14.2 Namespace'lar va navigatsiya

| Namespace | Egasi |
|-----------|-------|
| `reports.*` | Y-1, Y-2 o'rami — hisobot yuzasi |
| `reports.preset.*` | §4.4 (**G-43**) |
| `reports.errorCause.*` / `reports.errorFix.*` | §14.9 |
| `compare.*` | Y-3 |
| `compare.diff.*` | §10.5 (**G-41**) |
| `occupancy.*` | ⛔ **Mavjud** — `ConfusionMatrix` o'z kalitlarini saqlaydi (§9.2) |

| Kalit | uz-Latn | uz-Cyrl | ru |
|-------|---------|---------|-----|
| `nav.reports` | **Hisobotlar** | Ҳисоботлар | Отчёты |

### 14.3 Shipping matn (uz-Latn; qolgan ikkitasi §14.4 bo'yicha)

| Kalit | uz-Latn |
|-------|---------|
| `reports.title` | Hisobotlar |
| `reports.periodLabel` | Davr |
| `reports.periodFrom` | Boshlanish |
| `reports.periodTo` | Tugash |
| `reports.periodShown` | {from} — {to} |
| `reports.preset.last30` | Oxirgi 30 kun |
| `reports.preset.yesterday` | Kecha |
| `reports.preset.thisMonth` | Joriy oy |
| `reports.preset.lastMonth` | O'tgan oy |
| `reports.preset.custom` | Tanlangan oraliq |
| `reports.maxDayHint` | Hisobot kechagi kungacha yopilgan ma'lumotdan chiqadi. |
| `reports.export` | Excel bo'lib yuklab olish |
| `reports.exporting` | Tayyorlanmoqda |
| `reports.revenueTitle` | Tushum |
| `reports.revenueTotal` | Davr tushumi |
| `reports.revenueCharged` | Hisoblangan |
| `reports.revenuePaid` | To'langan |
| `reports.revenueDiff` | Farq |
| `reports.debtorsTitle` | Qarzdorlik ro'yxati |
| `reports.debtorsTotal` | Jami qarz |
| `reports.debtorsOldest` | Eng eski qarz |
| `reports.vendorUnknown` | Sotuvchi ko'rsatilmagan |
| `reports.anomaliesTitle` | Nomuvofiqlik arxivi |
| `reports.anomaliesUnpaid` | Band, lekin to'lovsiz |
| `reports.anomaliesUnregistered` | Ro'yxatga olinmagan savdo |
| `reports.accuracyTitle` | AI aniqlik hisoboti |
| `reports.accuracyDisclaimer` | Bu ulush nazoratchining ko'r javoblaridan hisoblanadi. Modelning o'zi CI'da o'lchanmagan. |
| `reports.accuracyNotMeasured` | Bu davrda javoblar soni o'lchov uchun yetarli emas: {n} ta, kamida {min} kerak. |
| `reports.rowsShown` | {shown} qatordan {total} tasi ko'rsatilmoqda |
| `reports.amountUnit` | so'm |
| `reports.compareLink` | Uch tomonlama solishtiruv |
| `compare.title` | Uch tomonlama solishtiruv |
| `compare.ledger` | Daftar |
| `compare.system` | Tizim |
| `compare.aiExpected` | AI-kutilgan |
| `compare.diff.ledgerOver` | Daftar ortiq |
| `compare.diff.systemOver` | Tizim ortiq |
| `compare.diff.aiMismatch` | Bandlik farqi |
| `compare.diffCounts` | Daftar ortiq: {ledgerOver} · Tizim ortiq: {systemOver} · Bandlik farqi: {aiMismatch} |
| `compare.matched` | {matched} rasta uchala manbada mos |
| `compare.ledgerUpload` | Daftarni yuklash |
| `compare.ledgerTemplate` | Shablonni yuklab olish |
| `compare.ledgerMissing` | Bu kun uchun daftar yuklanmagan |
| `compare.ledgerMissingHint` | Daftar summalarini Excel shabloni orqali yuklang — solishtiruv shundan keyin chiqadi. |
| `compare.ledgerReplaceTitle` | Daftarni almashtirasizmi? |
| `compare.ledgerReplaceBody` | {day} kuni uchun daftar allaqachon yuklangan. Yangi fayl eskisining o'rnini oladi. |
| `compare.ledgerReplaceConfirm` | Almashtirish |
| `compare.ledgerLoaded` | Daftar yuklandi: {rows} qator |

⛔ **`reports.rowsShown` va `compare.matched` — ICU platsholderlari bilan**, ya'ni maxraj **matndan ajralmaydi** va **G-39**/**G-41** ularni DOM'da topa oladi.

### 14.4 Uch til va transliteratsiya kontrakti

| Fayl | Kim yozadi |
|------|-----------|
| `messages/uz-Latn.json` | Qo'lda |
| `messages/ru.json` | Qo'lda |
| `messages/uz-Cyrl.json` | ⛔ **`npm --prefix frontend run i18n:gen`** — qo'lda tahrirlanmaydi |
| `messages/uz-Cyrl.overrides.json` | ⛔ **Tegilishi KUTILMAYDI** [M-13: `Excel`, `xlsx` allaqachon bor] |

[M-13] 42 nomzod satrdan **40 tasi toza**; `Excel` overrides bilan **hal**; `Backup` ⛔ **copy'ga umuman kirmaydi** (§14.1).

⚠ Agar qo'lda tuzatish zarurati chiqsa, u `uz-Cyrl.overrides.json` ning `words` bo'limiga **so'z** sifatida yoziladi (o'zbek **agglyutinativ** — har qo'shimchali shakl **alohida yozuv**), `uz-Cyrl.json` ga **emas**.

### 14.5 Glossariy — mavjud reyestr o'zgarmaydi

`ops/i18n/glossary.json` (`patta`, `rasta`, `qarz`, `smena`) ⛔ **kengaytirilmaydi**: 8-faza yangi domen atamasi kiritmaydi — «daftar», «tushum», «farq» **hisobot** so'zlari, domen atamalari emas, va ular botda uchramaydi (glossariy veb↔bot yagonaligini o'lchaydi).

⛔ **`qarz` o'zagi ru'da saqlanadi:** `reports.debtorsTitle` ru = «Реестр **долг**ов», `reports.debtorsTotal` ru = «Итого **долг**» — G7-9(a) ning ru shoxi shu bilan hisobot yuzasida ham yashil qoladi.

### 14.6 Uch tilli yakuniy tekshiruv — INSON o'qishi [D-23]

⛔ **Yangi mexanik darvoza yozilmaydi.** Mavjudlari yetarli: `i18n:check` (parity + generatsiya), `glossary.test.mjs` (G7-9), `error-codes.test.mjs` (G-17).

Qo'shiladigan — `08-HUMAN-UAT.md` bandi: ⛔ **kassir, nazoratchi va admin** har biri **o'z** oqimini **uch tilda** bajaradi va ⛔ **topilgan har nuqson kalit nomi bilan** yoziladi. ⚠ Bu bandning ochiq merosi bor: 07-UI-SPEC **O-03** («ru'dagi `патта` ↔ `сбор` ikkiligi»), 05-UI-SPEC **O-01** va 06-UI-SPEC **O-07** — ⛔ **uchalasining tetigi aynan shu tekshiruv** va ular ro'yxatga **nomma-nom** kiradi.

### 14.7 Toastlar (2) va bo'sh holatlar (6)

**Toastlar:** «Daftar yuklandi: {rows} qator» (success) · eksport/import xatosi ⛔ **YO'Q — inline** (§12.2).

⛔ Ya'ni **aynan bitta** toast turi. Sabab: yuklab olish xatosi toastda g'oyib bo'lardi va foydalanuvchi tugmani qayta-qayta bosardi.

| # | Blok | Sarlavha | Tavsif |
|---|------|----------|--------|
| 1 | `revenue` | Bu davrda yozilgan tushum yo'q | {from} — {to} oralig'ida yopilgan hisob topilmadi. |
| 2 | `debtors` | Qarzdor sotuvchi yo'q | {from} — {to} oralig'ida to'lanmagan hisob qolmagan. |
| 3 | `anomalies` | Nomuvofiqlik topilmadi | {from} — {to} oralig'ida band-lekin-to'lovsiz rasta ham, ro'yxatga olinmagan savdo ham yo'q. |
| 4 | `accuracy` | ⛔ `EmptyState` **EMAS** — inline nomlangan sabab | §9.3 |
| 5 | `period` (`thisMonth`, oyning 1-kuni) | Joriy oyda hali yopilgan kun yo'q | Hisobot kechagi kungacha yopilgan ma'lumotdan chiqadi. |
| 6 | `comparison` | ⛔ Bu kun uchun daftar yuklanmagan | Daftar summalarini Excel shabloni orqali yuklang — solishtiruv shundan keyin chiqadi. |

⛔ **`action` faqat 6-holatda** (`[Daftarni yuklash]` ga yo'naltirish) — qolgan beshtasida foydalanuvchi qiladigan «keyingi qadam» **yo'q** (davrni o'zgartirish — qadam emas, u allaqachon ekranda).

### 14.8 ⛔ Destruktiv amal — AYNAN BITTA

| Amal | Tasdiq | `confirmVariant` |
|------|--------|------------------|
| ⛔ **Daftarni almashtirish** (shu kun uchun import allaqachon bor) | ⛔ **`ConfirmDialog` `level: 1`** | `destructive` (standart) |

Matn (§14.3): sarlavha «Daftarni almashtirasizmi?» · tana «{day} kuni uchun daftar allaqachon yuklangan. Yangi fayl eskisining o'rnini oladi.» · tasdiq «Almashtirish» · bekor «Bekor qilish».

⛔ **`level: 2` (matn yozib tasdiqlash) ISHLATILMAYDI** — §4.6.

⛔ **Boshqa destruktiv amal YO'Q:** hisobot o'chirilmaydi, daftar qatorlari **tahrirlanmaydi** (faqat butun kun almashtiriladi), eksport bekor qilinmaydi. ⛔ `variant="destructive"` tugma **`ConfirmDialog` dan tashqarida 0 marta** (**G-42(a)**).

### 14.9 Xato kontrakti — SABAB + NIMA QILISH KERAK (G-17 davomi)

| Kod | `errorCause` (uz-Latn) | `errorFix` (uz-Latn) |
|-----|------------------------|----------------------|
| `report_period_invalid` | Tanlangan davr yaroqsiz. | Boshlanish sanasi tugash sanasidan keyin bo'lmasin. |
| `report_period_future` | Hisobot kechagi kungacha yopilgan ma'lumotdan chiqadi. | Tugash sanasini kechagi kun yoki undan oldin qilib tanlang. |
| ⛔ `report_too_large` | Bu davrda qator soni faylga sig'maydi. | Davrni qisqartiring va qayta yuklab oling. |
| `report_export_failed` | Fayl tayyorlanmadi. | Qayta urinib ko'ring — muammo takrorlansa, davrni qisqartiring. |
| `ledger_day_locked` | Bu kun uchun daftar yopilgan. | Bozor ma'muriyatiga murojaat qiling. |
| `ledger_stall_unknown` | Faylda tizimda yo'q rasta kodi bor. | Rasta kodlarini shablondagi ro'yxat bilan solishtiring. |
| `report_forbidden` | Bu hisobotga ruxsatingiz yo'q. | Direktorga murojaat qiling. |

⛔ **Xom istisno matni HECH QACHON** [MEROS: 07 D-04] — server xato kodini beradi, UI kalitga xaritalaydi.

---

## 15. Qulaylik (a11y)

| Talab | Shakl |
|-------|-------|
| Fokus halqasi | `:focus-visible` aksent outline — barcha interaktiv elementlar |
| `fieldset`/`legend` | Davr guruhi (preset + ikki sana) |
| ⛔ `aria-busy="true"` | Eksport tugmasi yuklanayotganda; ⛔ matn **o'zgarmaydi** |
| ⛔ `aria-disabled`, `disabled` **emas** | Eksport tugmasi [MEROS: 05-UI-SPEC §13.3] — `disabled` tugma fokusni **yo'qotadi** va skrinrider foydalanuvchisi «tugma qayerga ketdi?» degan holatda qoladi |
| `aria-describedby` | Yig'indi → davr jumlasi **va** `rowsShown` jumlasi; aniqlik foizi → mavjud maxraj jumlalari |
| Jonli hududlar | `role="status"`: import natijasi, eksport tugagani · ⛔ `role="alert"`: **faqat** xato (⛔ §9.4 disclaimer **emas**) |
| Rang yolg'iz signal **emas** | §13.4 — 9 holat, har birida ≥2 qo'shimcha kanal |
| Jadval semantikasi | native `<table>` + `<caption class="sr-only">` + `<th scope>`; ⛔ `role="grid"` **yo'q** [MEROS: 04-11 darsi] |
| ⛔ Bo'sh katak | ⛔ **`sr-only` matn bilan nomlanadi** (§8.4) |
| ⛔ Global bir-tugmali yorliqlar | ⛔ **YO'Q** [MEROS: 06-UI-SPEC §14.4] |
| Barmoq nishoni | ≥44px (`size="lg"` yoki `min-h-11`) — `[Daftarni yuklash]` (§6.1) |
| Sana maydonlari | native `<input type="date">` — OS tanlagichi, o'z locale'i, o'z klaviatura qo'llab-quvvatlashi bilan |

---

## 16. Darvozalar

### 16.1 ⛔ Raqamlash — uch ketma-ketlik bor va bu ochiq yozilishi SHART

| Ketma-ketlik | Diapazon | Uyi |
|--------------|----------|-----|
| **Frontend darvozalari** | `G-1`…**`G-36` band** → yangilari **`G-37` dan** [M-14] | `frontend/scripts/*.test.mjs`, `*.test.tsx` |
| **Backend/faza darvozalari** | `G-1`…`G-16` band | `tests/**` (06-VALIDATION.md) |
| **7-fazaning taqiq darvozalari** | `G7-1`…`G7-9` band | 07-RESEARCH § Validation Architecture |

**Qoidalar:**

1. ⛔ Bu hujjatning **yangi** darvozalari **`G-37` dan** boshlanadi.
2. ⛔ Kod izohlarida ID **ketma-ketligi bilan**: `G-37 (08-UI-SPEC)`. Yalang'och `G-3` **yozilmaydi** (u 04-UI-SPEC niki).
3. ⛔⛔ **Bu hujjat `| **G-18** |` bilan boshlanadigan jadval qatori YOZMAYDI** [M-4] — `bulk-action-surface.test.mjs:112-125` e'lon qilgan UI-SPEC soni **aynan 1** bo'lishini talab qiladi va ikkinchi e'lon `npm run gate` ni **butunlay** qizartirardi.

### 16.2 Har darvozaning ikki muzokarasiz xossasi [MEROS: 06/07-UI-SPEC]

| Xossa | Ma'nosi |
|-------|---------|
| ⛔ **HOSILA qamrov** | Darvoza katalogni **o'qiydi**, reyestrdan **iteratsiya qiladi**. Qo'lda yozilgan ro'yxat **yo'q** |
| ⛔ **TO'PLAM TENGLIGI** | `deepEqual`/`Set`. ⛔ `not.toContain(...)` **ishlatilmaydi** |

Har darvozada **quyi chegara** (`MIN_*`): skanerlanadigan fayl soni kamaysa darvoza **qizaradi** — bo'sh to'plamda «taqiqlangan token topilmadi» **jimgina rost** bo'ladi.

### 16.3 ⛔ Sabotaj majburiyati [MEROS: 05-15 S-D darsi]

Har yangi darvoza uchun reja **sabotaj o'lchovini** yozadi. ⛔ Sabotaj sistemaga yetib borib ham hech nima qizarmasa, tuzatish ⛔ **testda emas — HOLATDA**: o'lchov tanlagan ma'lumot ikkala shoxda bir xil natija berayotgan bo'ladi.

### 16.4 ⛔ Byudjet oshsa — «shunchaki oshirilmaydi» [D-26]

`gate` **2300 s** / `gate:fast` **200 s** (06-VALIDATION) **o'zgarmaydi**. Oshsa — 05-15 W0-13 protokoli: **tinch xost**, **uch o'lchov**, **eng yomon × 1,20**, sabab **yozilgan**. ⚠ `STATE.md`: `C:` diski 91 % to'la — o'lchov oldidan bu **tekshiriladi** (05-15 dagi ogohlantirish).

### 16.5 ⛔ Ommaviy amal taqig'i — MAVJUD darvozaga QO'SHILADI, yangi ID olmaydi

`components/reports/**` ham ommaviy-amal skanidan o'tishi **shart**: «Hamma qarzdorga eslatma yuborish» yoki ko'p-tanlovli hisobot qatori direktorga **bir bosishda 300 sotuvchiga** ta'sir qilish imkonini berardi.

| Qadam | Ish |
|-------|-----|
| 1 | `05-UI-SPEC.md` §15 dagi ommaviy-amal qatoriga **beshinchi** naqsh qo'shiladi: `` `components/reports/**` `` |
| 2 | ⛔ **Aynan birinchi `components/reports/*.tsx` mahsulot fayli bilan bitta commitda** — darvoza e'lon qilingan **har** katalogning mavjud va **bo'sh emasligini** tekshiradi |
| 3 | Skan **o'zi** kengayadi: `MIN_SCANNED_FILES` va `checkbox`/`Array.isArray` tokenlari **o'zgarmaydi** |

### 16.6 Yangi darvozalar

| # | Darvoza | Fayl | Mexanik ravishda NIMANI o'qiydi | Nima uchun mavjud |
|---|---------|------|----------------------------------|-------------------|
| **G-37** | ⛔⛔ **Blok to'plami va MAZMUN JUFTLIGI** | `reports/page.test.tsx` + `reports/compare/page.test.tsx` | **(a)** `/reports` → `[data-report-block]` qiymatlari to'plami **`{"period","revenue","debtors","anomalies","accuracy"}` ga TENG** — ⛔ **davrdan QAT'I NAZAR** (ikki xil davr bilan ikki render, ikkala to'plam ham teng). **(b)** `/reports/compare` → **`{"day","ledger","comparison"}` ga TENG**. **(c)** ⛔ **Mazmun juftligi:** `Set([data-report-content]) === Set(blocks) \ CONTENT_EXEMPT`, `CONTENT_EXEMPT = {"period"}` va ⛔ `CONTENT_EXEMPT.size === 1` **alohida assert**; solishtiruvda `{"day"}`. **(d)** ⛔ `grep -c "data-report-content" reports/page.tsx` → **0** (atributni ro'yxat komponentining **O'ZI** chiqaradi). **(e)** ⛔ **Haqiqiy mazmun mock'dan HOSILA:** `revenue` → `rows[0].business_date` **va** `querySelectorAll("tbody tr").length === rows.length`; `debtors` → `rows[0].vendor_name`; `anomalies` → `rows[0].kind` yorlig'i; `accuracy` → matritsa katagi. ⛔ **SABOTAJ (majburiy):** `<RevenueReport/>` → `<div data-report-block="revenue"/>` — (a) **yashil qolishi kutiladi**, (c) **va** (e) ⛔ **QIZARISHI SHART** | ⛔ **§8.1 ning strukturaviy shakli** + 06-faza G-25 ning **o'lchangan ko'rligidan** olingan dars: faqat atribut to'plamini tekshiradigan darvoza ⛔ **bo'sh o'ramni MUKAMMAL o'tkazardi** |
| **G-38** | ⛔⛔ **Yuklab olish `<a download>` EMAS va davr chegarasi BUZILMAYDI** | `scripts/report-copy.test.mjs` + `reports/period-picker.test.tsx` | **(a)** `components/reports/**` va `lib/report-queries.ts` (izohlarsiz) da: `download=`, `download}`, `window.open`, `location.href`, `document.createElement("a")`, `href={` — ⛔ **har biri 0**; ⛔ **quyi chegara: ≥6 token va ≥6 skanerlangan fayl**. **(b)** `lib/report-queries.ts` da `apiRequest(` **bor** va `fetch(` ⛔ **0**. **(c)** ⛔ Davr: `to` maksimumi **kecha** — `period-picker` `max` atributi `shiftIsoDay(todayIso,-1)` ga **TENG**; `?to=bugun` uzatilganda ⛔ **standartga tushadi** (DOM'da bugungi sana **yo'q**). **(d)** ⛔ Preset `thisMonth` oyning 1-kunida → `reports.periodShown` DOM'da **yo'q**, bo'sh holat 5 **bor** | ⛔ **§0.2 + §1.2 qoida 1 va 5.** (a) **mexanik**, intizom emas: `<a download>` 401 tanasini `.xlsx` nomi bilan diskka **yozadi** va nosozlik **jim** bo'ladi. (c) eksport qilingan **kam ko'rsatilgan** raqamning oldini oladi — u faylga tushib **tarqaladi** |
| **G-39** | ⛔ **Davr HAR DOIM raqam bilan bir joyda va u SERVERNIKI** | `reports/revenue-report.test.tsx` + `scripts/report-copy.test.mjs` | **(a)** Server `{from_date:"2026-09-01", to_date:"2026-09-30"}` qaytarganda, `nuqs` esa `?from=2026-08-01&to=2026-09-30` bo'lganda → DOM'da **`2026-09-01`** bor va ⛔ **`2026-08-01` YO'Q**. **(b)** Yig'indi elementining `aria-describedby` i davr jumlasi **va** `rowsShown` jumlasi id'lariga ishora qiladi. **(c)** ⛔ `ConfusionMatrix` ning props tipi `from`/`to`/`period`/`label` nomli maydon **qabul qilmaydi** (manba matnidan regeks + `occupancy/confusion-matrix.tsx` **o'zgarmagani** — `data-report-block="accuracy"` o'rami undan **tashqarida**). **(d)** `reports.periodShown` uchala locale'da **ICU platsholderi bilan** | ⛔ **§8.7.** So'ralgan davrni chizish «men oktyabrni so'radim, oktyabr keldi» degan **yolg'on tasdiq** berardi — holbuki server davrni qisqartirgan bo'lishi mumkin. Bu ekranda tuzatiladigan, **faylda esa tarqaladigan** xato |
| **G-40** | ⛔⛔ **O'lchanmagan son chizilmaydi (WR-05 ning yopilishi)** | `reports/accuracy-block.test.tsx` + `reports/compare-table.test.tsx` | **(a)** `measured:false, n:7, min_sample:20` → foiz belgisi (`%`/`％`) DOM'da ⛔ **0 marta**; `reports.accuracyNotMeasured` matni **bor**; `0`, `NaN`, `Infinity`, `—%` satrlari **yo'q**. **(b)** ⛔ So'rov **yiqilganda** (`ApiError` mock) → foiz belgisi **0 marta** **va** xato matni `role="alert"` ichida — ⛔ **bu WR-05 ning aynan shakli**. **(c)** ⛔ Solishtiruv: `ai_expected:null` katagi **bo'sh** (matn tuguni yo'q) va `ai_expected:0` katagi **`0` chizadi** — ikkalasi **bitta testda**, farqi **assert bilan**. **(d)** ⛔ Daftar yo'q → `<table>` DOM'da **0 marta** va `compare.ledgerMissing` **bor**. **(e)** ⛔ Klientda chegara yo'q: `components/reports/**` da `min_sample`/`minSample` bilan **taqqoslash** operatori (`>=`,`<`) yo'q | ⛔ **D-10 + 05-13/05-14 naqshi.** (b) 07 ko'rigining **WR-05** bandini yopadi. (c) eng nozigi: `null` va `0` ni tenglashtirish «AI rastani bo'sh dedi» bilan «bandlik o'lchanmagan» ni bir narsa qilardi. (d) ⛔ eng qimmati: daftarsiz «hamma farq 0» jadvali **imzolanardi** va parallel rejim (SC#5) jimgina qadrsizlanardi |
| **G-41** | ⛔⛔ **Uch farq sinfi hech qachon QO'SHILMAYDI** | `reports/compare-table.test.tsx` + `scripts/report-copy.test.mjs` | **(a)** `DIFF_CLASSES` reyestridan **iteratsiya qilib** `compare.diff.*` kalitlari **uchala locale'da** — ⛔ **to'plam tengligi**; reyestr ⛔ **aynan 3 a'zo** (`match` **kalit olmaydi** — §13.4). **(b)** ⛔ `components/reports/**` va `lib/report-queries.ts` da: `total_diff`, `totalDiff`, `combined_diff`, `combinedDiff`, `total_variance`, `totalVariance`, `grand_total`, `grandTotal`, `diff_total`, `diffTotal` — ⛔ **har biri 0**; **quyi chegara: ≥10 nom**. **(c)** ⛔ DOM: uch sanoq **uch alohida** matn tugunida (`compare.diffCounts` ICU platsholderlari) va ularni **birlashtirgan** son yo'q. **(d)** ⛔ `match` qatori jadvalda **bor** va unda `Badge` **yo'q** (`match` qatorida `data-diff` atributi **yo'q**), `compare.matched` maxraj jumlasi **bor** | ⛔ **§10.5 + specifics.** Uch sinf uch **turli harakat** talab qiladi («pulni qidiring» / «daftarni tuzating» / «detektorni tekshiring»); bitta songa siqish solishtiruvni **foydasiz** qilardi. (d) 07 G-32 darsining takrori: maxrajsiz «13 ta farq» varaqda «bozorda 13 rasta» bo'lib o'qilardi |
| **G-42** | ⛔⛔ **Hisobot yuzasining taqiqlangan nomlari, aksent byudjeti va IKKI KATALOG IKKI RO'YXAT** | `scripts/report-copy.test.mjs` | **(a)** ⛔ `variant="default"` **aynan 1 marta**; `variant="destructive"` ⛔ **aynan 1 marta va u `ConfirmDialog` chaqiruvida** (§14.8). **(b)** ⛔ `float(`, `Decimal`, `.toFixed(`, `parseFloat(`, `.reduce(` — **0** (D-03). **(c)** ⛔ `queue_kind`, `queueKind`, `purpose`, `"train"`, `"eval"` — **0** (§9.1: `eval`/`train` filtri **hech qayerda**). **(d)** ⛔ Kadr tokenlari — `<img`, `next/image`, `useEvidenceImageHref`, `URL.createObjectURL`, `/snapshots/` — **0** (07 D-03). **(e)** ⛔ `text-base`, `text-xl`, `text-3xl`, `text-[` — **0** (§7.1). **(f)** ⛔ `confusion`/`matrix`/`wilson`/`percentView` **ta'rifi** yo'q — ⛔ **import istisno** (regeks `^import` qatorini chiqaradi). **(g)** ⛔⛔ **IKKI RO'YXAT:** `chat_id`, `chatId`, `telegram_user_id`, `telegram_username`, `balance`, `phone`, `full_name`, `fullName` — **0**; ⛔ `vendor_name`/`vendorName` ⛔ **BU RO'YXATDA YO'Q** va bu **to'plam tengligi** bilan o'lchanadi (⛔ ro'yxat testda **qayta yoziladi**, mahsulotdan import qilinmaydi); **quyi chegara: ≥8 nom** | ⛔ **D-03 + D-07 + §7.1/§9.1/§13.3/§14.8, bitta mexanizmda.** ⛔ (g) eng nozigi: 7-fazaning **G-36** i aynan `vendor_name` ni **taqiqlaydi**; shu ro'yxatni bu katalogga ko'chirish D-07 ni **birinchi kunidayoq** buzardi, teskarisi esa 7-fazaning C-10 himoyasini yumshatardi. ⛔ **Ikki katalog — ikki ro'yxat**, va bu **assert bilan** yozilgan |
| **G-43** | ⛔ **Yopiq reyestrlar × 3 locale** | `scripts/report-copy.test.mjs` | **(a)** ⛔ `REPORT_KINDS` — **aynan 4 a'zo** (`revenue,debtors,anomalies,accuracy`) va solishtiruv ⛔ **ichida YO'Q** (§12.1). **(b)** `PERIOD_PRESETS` dan **iteratsiya qilib** `reports.preset.*` **uchala locale'da** — **to'plam tengligi**; reyestr ⛔ **aynan 5 a'zo** (4 preset + `custom`). **(c)** ⛔ Taqiqlangan copy: `reports.*`/`compare.*` qiymatlarida «Backup»/«Баcкуп» **0** (§11) **va** «jami farq»/«умумий фарқ»/«общая разница» **0** **va** «aniqlik ulushi»/«аниқлик улуши» **0** (§14.1: u **case hit-rate** ning nomi va bu ekranda **AI aniqligi** bor) — ⛔ **quyi chegara: ≥9 token**. **(d)** `reports.rowsShown`, `compare.matched`, `compare.diffCounts`, `reports.accuracyNotMeasured` — uchala locale'da ⛔ **ICU platsholderi bilan** | ⛔ **§12.1 + §4.4 + §14.1.** (a) solishtiruvni reyestrga tiqish `REPORT_KINDS` ni «yuklab olinadigan narsa» ga aylantirardi va davr parametrlari **ixtiyoriy** bo'lib qolardi. (c) «aniqlik ulushi» taqig'i eng nozigi: bir xil ibora ikki ekranda **ikki xil miqdorni** bildirardi (07 §14.1) |

### 16.7 Sampling — mavjud byudjetlar

| Daraja | Buyruq | Byudjet |
|--------|--------|---------|
| Task commit | `npm run gate:fast` | **200 s** |
| Wave merge | `npm run test` + `npm run test:tenancy` | — |
| Faza darvozasi | `npm run gate` + `tests/integration/test_phase8_criteria.py` | **2300 s** [D-26] |

⚠ Baholanган frontend qo'shimchasi: vitest +~70 test, **2 ta** yangi SSG marshruti × 3 locale → **~70–90 s**. ⛔ Oshsa — §16.4 protokoli.

---

## 17. Bu fazada BO'LMAYDIGAN UI

### 17.1 V2 ga qoldiriladigan

| Imkoniyat | 8-fazada aynan nima qilinadi | Nima QILINMAYDI |
|-----------|-------------------------------|------------------|
| **Direktor botining buyruq yuzasi** | ⛔ **Hech narsa** | Botdan hisobot so'rash |
| **Sotuvchi botidan to'lov / da'vo** | ⛔ **Hech narsa** | Ikki tomonlama oqim |
| **To'liq interaktiv plan-xarita** | ⛔ **Hech narsa** | `react-konva` |
| **Kassir offline-lite** | ⛔ **Hech narsa** | Service worker, navbat |
| **AI-02 ning yopilishi** | ⛔ Holatni **halol ko'rsatadi** (§9.4) | Real ONNX, oltin to'plam, CI aniqlik o'lchovi |
| **Phase 0 baza varaqalari** | ⛔ **Ulanmaydi** | Solishtiruvga to'rtinchi ustun |
| **Dayjest alert kalitini ikkiga bo'lish** | ⛔ **Hech narsa** [D-25] | Ikkinchi kalit |

### 17.2 Ataylab qurilMAYDIGAN — sabab bilan

| Nima | Nima uchun |
|------|-------------|
| ⛔ **Diagramma / trend grafigi** | Uchta mustaqil sabab: (1) `recharts` **yo'q** va ⛔ mustahkamlash haftasida yangi paket **qo'shilmaydi**; (2) diagramma `.xlsx` ga **tushmaydi**, ya'ni ekran bilan hujjat **ajralardi** — bu fazaning butun mazmuniga qarshi; (3) ⛔ trend **davrlar aro** solishtiruvni taklif qiladi, davr esa **tanlanadigan** — «oktyabr vs sentyabr» degan savol ekranda tug'ilib, javobsiz qolardi |
| ⛔ **`[Imzolash]` tugmasi / raqamli imzo** | D-19 — qog'oz jarayon. Tugma tizim **bilmagan** narsani bilgandek ko'rsatardi |
| ⛔ **«Oxirgi zaxira: …» ko'rsatkichi** | §11 — u `/internal/self-check` da; ⛔ ikkinchi yuza ikkinchi haqiqat manbai bo'lardi |
| ⛔ **Zaxirani qo'lda ishga tushirish tugmasi** | Zaxira **jadval** bilan ishlaydi (D-13); qo'lda tugma retention arifmetikasini buzardi va ⛔ «alert on absence» signalini **soxta yashil** qilardi |
| ⛔ **Hisobotni Telegramga yuborish** | 07 D-03 — chegaradan chiqmaydi; `.xlsx` da ismlar bor |
| ⛔ **Rejalashtirilgan / avtomatik eksport** | Har eksport **bitta `audit_read`** yozadi (D-07); avtomatik eksport auditni **egasiz** qatorlar bilan to'ldirardi |
| ⛔ **Ommaviy amal** (hamma qarzdorga eslatma) | §16.5 |
| ⛔ **Hisobot filtri** (rasta, sotuvchi, kategoriya bo'yicha) | §17.3 |
| ⛔ **Dalil kadri hisobotda yoki eksportda** | 07 D-03 — faqat identifikator (§8.5) |
| ⛔ **`/reports` ni `/billing` yoki `/reconciliation` ga qo'shish** | D-01 + §4.2 — operativ ↔ hujjat ajratilishi |
| ⛔ **Klientda `.xlsx` qurish yoki o'qish** | D-05 + §3.5 |
| ⛔ **«Aniqlik ulushi» iborasi bu ekranda** | 07 §14.1 — u **case hit-rate**; bu yerda **AI aniqligi** (**G-43(c)**) |

### 17.3 Erta optimizatsiya deb baholangan «ilgaklar»

Hisobot filtri (rasta/sotuvchi/kategoriya — davr **allaqachon** asosiy kesim; filtr sahifalash + eksport + yig'indi uchligini **uch marta** murakkablashtirardi va «eksport filtrni hisobga oldimi?» degan javobsiz savol tug'dirardi) · hisobot qatorlarining virtualizatsiyasi (sahifalash yetarli) · eksport uchun progress bar (fayl serverda soniyalarda quriladi; progress **soxta** bo'lardi) · solishtiruv natijasining keshi/tarixi (kunlik `.xlsx` **o'zi arxiv**) · `components/reports/**` uchun umumiy `<ReportTable>` abstraktsiyasi (uch iste'molchi, uch xil ustun to'plami — 07 §17.3 bilan bir sinf) · dark mode · Storybook.

---

## 18. Ochiq qoldirilgan savollar — har biri uchun ishlaydigan standart bor

Bu subagent kontekstida foydalanuvchiga savol berish vositasi yo'q (`--auto`). Har biri uchun standart tanlangan; rejalashtirish javob kutib **to'xtamaydi**.

| # | Savol | Bilamiz | Noaniq | Tanlangan standart va TETIGI |
|---|-------|---------|--------|-------------------------------|
| **O-01** | ⛔⛔ ROADMAP «solishtiruvni **nazoratchi** yoki admin bajaradi» deydi. `inspector` roliga `report_view` berilsinmi? | [M-6] `inspector` da **faqat** `occupancy_review`; `report_view` — director + market_admin | Karmanada «nazoratchi» so'zi **lavozim**ni bildiradimi yoki **tizim rolini**mi | ⛔⛔ **BERILMAYDI, va sabab MEXANIK:** solishtiruvning «AI-kutilgan» ustuni — bandlik hosilasi, ya'ni ⛔ **detektorning xulosasi**. `inspector` roli 5-fazada **aynan ko'r audit** uchun tug'ilgan (u AI xulosasini **ko'rmasligi** kerak, aks holda javoblari ifloslanadi va AI-02 ning yagona o'lchov yo'li yopiladi). ⛔ Ya'ni `inspector` ga bu yuzani ochish **ko'r auditni jimgina buzardi** — 5-fazaning butun mexanikasi. «Nazoratchi» **lavozim** sifatida o'qiladi va u amalda **bozor admini** hisobiga kiradi; D-20 ning haqiqiy talabi — ⛔ **kassir emas** — bugungi matritsada **allaqachon** ta'minlangan. **Tetigi:** parallel rejimda solishtiruvni bajaradigan odamda `market_admin` roli **bo'lmasa** — to'g'ri tuzatish o'sha odamga `market_admin` **berish**, `inspector` ga `report_view` **emas** |
| **O-02** | Standart davr **oxirgi 30 kun**mi yoki **joriy oy**mi? | `ACCURACY_WINDOW_DAYS = 30` serverda [M-10] | Direktor «oy» bilan o'ylaydimi yoki «oxirgi 30 kun» bilanmi | ⛔ **Oxirgi 30 kun** (§4.4). Sabab **mexanik**, did emas: server aniqlik uchun **aynan shu** oynani standart qilgan, ya'ni `/reports` va `/occupancy` standart holatda **bir xil son** ko'rsatadi. **Tetigi:** direktor doim `thisMonth`/`lastMonth` ni bosayotgani ko'rinsa — standartni **`lastMonth`** ga o'tkazish mumkin, LEKIN shunda §9.2 dagi kesh ulashuvi buziladi va aniqlik bloki **ikki xil davr** ko'rsatadi; u holda to'g'ri tuzatish — aniqlik blokiga **o'z, alohida** davr yorlig'ini **ochiq** qo'yish |
| **O-03** | Qarzdorlik ro'yxatida **ism** yoki **ism + telefon**? | D-07 ismni ruxsat etadi; `phone` `PERSONAL_ROUTES` mantig'ida | Direktor qarzdorga qo'ng'iroq qilish uchun telefonni **shu yerdan** kutadimi | ⛔ **Faqat ism** (§5.5). Sabab: telefon — **aloqa** ma'lumoti va u eksportga tushib **fayl bo'lib tarqalardi**; qarz undirish oqimi esa allaqachon **bot eslatmasi** (BOT-03). **Tetigi:** dala UAT «telefonni qidirib yuribman» desa, to'g'ri tuzatish — `/vendors` ga **havola**, hisobotga ustun **emas** |
| **O-04** | Eksportda qator soni chegarasi qancha? | Server jadvalni to'liq quradi; XlsxWriter oqim rejimida | Karmana uchun 30 kunlik nomuvofiqlik arxivi necha qator | ⛔ **`[ASSUMED]` 50 000 qator**, kodda sabab izohi bilan; oshsa ⛔ **`report_too_large`** (§8.6) — ⛔ **jimgina kesilmaydi**. Sabab: 1000 rasta × 30 kun ≈ 30 000 qator, ya'ni oylik hisobot sig'adi; yillik esa ogohlantirish oladi. **Tetigi:** birinchi oyda `report_too_large` **bir marta ham** chiqmasa — chegara to'g'ri; har hafta chiqsa — server sahifalangan ko'p varaqli fayl berishi kerak, chegarani **ko'tarish emas** |
| **O-05** | `/reports/compare` navigatsiyada bo'lishi kerakmi? | [M-5] 17 element; kassir **2 (o'zgarmaydi)** | Parallel rejimda kunlik ish qanchalik og'ir | ⛔ **Yo'q** (§4.7) — u 2–4 haftalik vaqtinchalik asbob. **Tetigi:** bozor admini «har kuni ikki bosish» dan shikoyat qilsa — bitta `NAV_ITEMS` qatori qo'shiladi va [M-5] bo'yicha mobil panel **o'zgarmaydi** |
| **O-06** | «Qarzdorlik **reestri**» atamasi ekranda saqlansinmi? | [M-13] `reestri` → `реэстри` (kirillcha imlo `реестр`) | Buyurtmachi qaysi so'zni tabiiy deb biladi | ⛔ **uz'da «Qarzdorlik ro'yxati», ru'da «Реестр долгов»** (§14.1). Sabab: overrides'ga to'rt qo'shimchali shakl (`reestr`, `reestri`, `reestrga`, `reestrdan`) yozish o'rniga **mavjud, toza so'z** ishlatiladi. **Tetigi:** 8-fazaning **uch tilli yakuniy tekshiruvi** (D-23) — buyurtmachi «reestr» ni talab qilsa, to'g'ri tuzatish — `uz-Cyrl.overrides.json` `words` ga **to'rt shakl** qo'shish, `uz-Cyrl.json` ni qo'lda tahrirlash **emas** |
| **O-07** | `platform_admin` hisobotni ko'rsinmi? | [M-6] unda `report_view` **yo'q** | Qo'llab-quvvatlash oqimi | ⛔ **Yo'q** (§5.6). Sabab: u **bozorlararo** rol va unga hisobot berish **har bozorning** qarzdor ismlarini ochardi. **Tetigi:** qo'llab-quvvatlash uchun kerak bo'lsa — **ikkala matritsada bitta commitda**, marshrut qamrovi matritsasi yangilangan holda |

---

## 19. Dizayn tizimi xulosasi (checker uchun jamlanma)

| Xossa | Qiymat |
|-------|--------|
| **Tool** | `none` (shadcn **ishlatilmaydi** — §3.4) |
| **Preset** | not applicable |
| **Component library** | Radix primitivlari + CVA, ⛔ **mahalliy `ui/` (10 primitiv, kengaymaydi)** |
| **Icon library** | `lucide-react@1.27.0` (ISC) — [M-3] 61 nomzoddan **0 tasi yetishmaydi** |
| **Font** | `--font-sans` (system stack) + `--font-mono` (§7.3) |
| **Bo'shliq** | 4-panjara: 4 · 8 · 12 · 16 · 24 · 32 · 48 (§6.1). **Istisnolar:** 44px barmoq nishoni, 56px mobil panel, 20px karta ichki `x` — ⛔ **barchasi MEROS, yangi istisno YO'Q** |
| **Tipografiya** | ⛔ **4 rol** (24 / 18 / 14 / 12), ⛔ **2 og'irlik** (400, 600) — §7.1 |
| **Rang 60/30/10** | 60% `--color-bg` · 30% `--color-surface` (+`-muted`) · 10% `--color-accent` |
| **Aksent faqat** | fokus halqasi · faol maydon chegarasi · joriy mobil nav elementi · ⛔ **`[Daftarni yuklash]` — fazadagi YAGONA aksent fonli tugma**; ⛔ to'rtta yuklab olish tugmasi **`secondary`** (§13.3) |
| **Destruktiv** | `--color-danger` — matn/badge rangi sifatida; `variant="destructive"` ⛔ **aynan 1 marta** va u **`ConfirmDialog` ichida** (§14.8) |
| **Yangi token** | ⛔ **YO'Q** |
| **Yangi npm paketi** | ⛔ **YO'Q** (§3.5) — ⛔ jumladan `recharts` **ham** |
| **Primary CTA** | «Excel bo'lib yuklab olish» (Y-1/Y-2) → «Daftarni yuklash» (Y-3) |
| **Bo'sh holatlar** | 6 ta (§14.7) |
| **Xato holatlari** | 7 kod, ⛔ har biri **sabab + tuzatish** (§14.9) |
| **Destruktiv tasdiq** | ⛔ **Aynan bitta** — «Daftarni almashtirasizmi?» / `ConfirmDialog level: 1` (§14.8) |
| **Registry safety** | ⛔ **Qo'llanmaydi** — shadcn ishlatilmaydi, uchinchi tomon registry **yo'q**, vendored blok **yo'q** |

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

*Phase: 08-hisobotlar-mustahkamlash-va-ishga-tushirish*
*UI-SPEC yakunlandi: 2026-08-13 — `gsd-ui-researcher`*
*Upstream: 08-CONTEXT.md (D-01…D-26), 07-UI-SPEC.md (dizayn tizimi, darvoza mexanikasi, §13.3/§14.8/§16.2), 06-UI-SPEC.md (blok reyestri, G-25 darsi), 05-UI-SPEC.md §11 + §15 (aniqlik formulalari, G-18 e'loni), ROADMAP Phase 8 (SC#1–SC#5) + Post-Launch, REQUIREMENTS.md (RECON-04/05, FOUND-07), CLAUDE.md (XlsxWriter, restic, backup siyosati)*
