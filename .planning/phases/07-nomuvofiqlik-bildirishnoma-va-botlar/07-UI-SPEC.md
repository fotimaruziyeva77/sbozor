---
phase: 07-nomuvofiqlik-bildirishnoma-va-botlar
status: draft
shadcn_initialized: false
preset: none
design_system: shadcn-pattern (manual, CVA + Radix — 1/2-faza tokenlari)
response_language: uz-Latn
inherits: .planning/phases/06-billing-va-kassir/06-UI-SPEC.md
created: 2026-08-11
---

# Phase 7 — Nomuvofiqlik, bildirishnoma va botlar: UI dizayn kontrakti

> Bitta va'daning vizual kontrakti: **raqam jarayonga aylanadi, va har xabar o'zi haqida rost gapiradi.**
> 6-fazaning UI'si «pulni yo'qotib bo'lmaydigan qilish» edi. Bu fazaniki — **da'voni isbotlanadigan darajaga tushirish**. Farq shundaki, bu yerda UI xatosi *pulda* emas, **ishonchda** ko'rinadi: direktor ikki xil raqam ko'rib tizimga ishonmay qo'yadi; «yetkazildi» degan yozuv nizoda **isbotlab bo'lmaydigan** da'voga aylanadi; kassir bosh ekranidan bitta sonni o'qib, smena yopishda **ko'r bo'lishdan to'xtaydi**.
> ⛔ Bu faza dizayn tizimini **meros qilib oladi**, boshlamaydi. Yangi token, yangi bo'shliq shkalasi yoki ikkinchi pul-formatlash yo'li — **o'zi nuqson** bo'lardi.
> Yaratdi: `gsd-ui-researcher`. Tekshiradi: `gsd-ui-checker`. Iste'mol qiladi: `gsd-planner`, `gsd-executor`.

---

## 0. Dalil holati va shu sessiyada bajarilgan o'lchovlar

| Belgi | Ma'nosi |
|-------|---------|
| **[O'LCHANDI]** | Shu sessiyada kodbazada yoki skript bilan o'lchandi — natija keltirilgan |
| **[KOD]** | Kodbazadan o'qildi — aniq `fayl:qator` keltirilgan |
| **[MEROS]** | Upstream artefaktdan (07-CONTEXT, 07-RESEARCH, 06/05/04-UI-SPEC, ROADMAP, CLAUDE.md) |
| **[QAROR]** | Shu hujjatda qabul qilindi — sabab yozilgan, muqobil rad etilgan |
| **[TALAB]** | UI backend'dan talab qiladigan narsa — rejaga bevosita kiradi |
| **[ASSUMED]** | Dalilsiz tanlangan qiymat — sabab va tetigi yozilgan (07-CONTEXT D-19 konvensiyasi) |

### 0.1 O'lchovlar

| # | O'lchov | Natija |
|---|---------|--------|
| **M-1** | **shadcn darvozasi** — `find . -maxdepth 3 -name components.json` | **0 natija** → `Tool: none` (§3.4). 2–6-faza qarori davom etadi |
| **M-2** | **`ui/` primitivlari** — `ls frontend/src/components/ui/` | **10 primitiv** (`badge, button, card, confirm-dialog, dialog, empty-state, field, input, select, skeleton`). 7-fazada **yangi `ui/` primitivi qurilmaydi** (§3.2) |
| **M-3** | **Ikonka mavjudligi** — `node -e "require('lucide-react')"` bilan **67 ta** 7-faza nomzod nomi | **0 ta yetishmayapti.** Jumladan: `FileWarning, ClipboardCheck, Gavel, Scale, Send, CheckCheck, Check, Clock, Ban, UserX, TriangleAlert, Link2Off, Bell, Target, Percent, ExternalLink, Inbox, CircleSlash, Timer, RotateCcw, CircleCheckBig, Receipt` |
| **M-4** | ⛔⛔ **`G-18(b)` darvozasi UI-SPEC FAYLLARINI O'QIYDI** — `bulk-action-surface.test.mjs:79-125` | Regeks — `` /^\|\s*\*\*G-18\*\*\s*\|/ ``, ya'ni **shu belgilar bilan BOSHLANADIGAN jadval qatori**; `assert.equal(SPEC_FILES.length, 1)`. ⛔ **Oqibat: BU FAYL ham shunday qator YOZMAYDI**; qamrov `05-UI-SPEC.md` §15 dagi **mavjud** qatorga to'rtinchi naqsh qo'shish bilan kengaytiriladi (§16.5, W0-F6). Prozada «G-18» deb yozish **xavfsiz** |
| **M-5** | **Navigatsiya sig'imi** — `NAV_ITEMS` × `ROLE_PERMISSIONS` skript bilan hisoblandi [KOD: `app-shell.tsx:103+`, `rbac.ts:64-133`] | Hozir **15 element**: `platform_admin` 11 · `director` 12 · `market_admin` 12 · ⛔ `cashier` **2** · `inspector` 2. `/reconciliation` (`report_view`) qo'shilgach → **16**: `platform_admin` **11 (o'zgarmaydi)** · `director` **13** · `market_admin` **13** · ⛔ `cashier` **2 (o'zgarmaydi)** · `inspector` **2 (o'zgarmaydi)**. `MOBILE_PRIMARY_COUNT = 4` — kassir paneli **`/dashboard` + `/collect`**, overflow **0**. **6-faza kontrakti saqlanadi** |
| **M-6** | ⛔ **YANGI HUQUQ KERAK EMAS** [KOD: `rbac.py:170,243`; `rbac.ts:56-58`] | `Permission.DISPUTE_DECIDE = "dispute_decide"` **allaqachon bor** va **faqat `director`** da; bugungacha **iste'molchisi yo'q**. Case ko'rish — `report_view`, case **hukmi** — `dispute_decide`. ⛔ Ya'ni 7-faza `rbac.py`/`rbac.ts` **juftligiga TEGMAYDI** va 6-fazaning W0-F1 (ikki-fayl) xavfi **umuman tug'ilmaydi** (§5.6) |
| **M-7** | ⛔⛔ **Sessiya tokeni — `Authorization: Bearer`, cookie EMAS** [KOD: `api-client.ts:215`; cookie faqat refresh uchun, `:155,226`] | `<a href="/api/v1/snapshots/{id}/image">` brauzer tomonidan **tokensiz** ketadi → **401**. «Dalil havolasi» **rasm baytlariga havola BO'LA OLMAYDI** — bu intizom emas, **mexanika** (§0.2) |
| **M-8** | **Transliterator sinovi** — 26 ta 7-faza nomzod satri `gen-cyrillic.mjs::transliterate()` dan o'tkazildi | **1 ta mexanik defekt: `Case yopildi` → `Cасе ёпилди`** (aralash alifbo — G-26(c) sinfi). ⛔ **Oqibat: «case» so'zi ekran matniga KIRMAYDI**; ekranda **«nomuvofiqlik»** (§9.1). Qolgan **25 satr toza**: `Nomuvofiqliklar`→`Номувофиқликлар`, `Band, lekin to'lovsiz`→`Банд, лекин тўловсиз`, `Ko'rilmoqda`→`Кўрилмоқда`, `Asossiz`→`Асоссиз`, `Mas'ul`→`Масъул`, `Aniqlik ulushi`→`Аниқлик улуши` |
| **M-9** | **`Telegram` brendi kirillda saqlanadi** [KOD: `uz-Cyrl.overrides.json` `words` bo'limi, **44 yozuv**] | `words.Telegram = "Telegram"` **bor**. Isbot: `snapshots.alertNotified` — uz «Telegram xabari yuborildi», cy «**Telegram** хабари юборилди». Ya'ni «Telegram qabul qildi» uchala locale'da **xavfsiz** (§11.2) |
| **M-10** | **Glossariy atamalari — bugungi holat** (**parity 1109 / 1109 / 1109** kalit) | `patta` **25 / 25 / 17** (ru o'zagi `патт`) · `rasta` **99 / 99 / 101** (ru o'zagi `мест` — «Торговые места»; ⛔ `прилавок` **0**) · `qarz` **6 / 6 / 6** (ru `долг`) · `smena` **16 / 16 / 22** (ru `смен`). ⛔ Ya'ni **G7-9(a) bugundan yashil** |
| **M-11** | ⛔ **Taqiqlangan sinonimlar — bugungi holat** | uz-Latn `yig'im` **0**, `do'kon` **0** · uz-Cyrl `йиғим` **0**, `дўкон` **0** · ru `лавк` **0**, `магазин` **0** → **G7-9(c) bugundan yashil**. ⛔⛔ **LEKIN `сбор` TAQIQ RO'YXATIGA KIRMAYDI**: u ru'da **13 kalitda** va **ikki ma'noda** — `nav.collect` = «Сбор» (amal, «Yig'ish») **va** `ежедневный сбор` = «kunlik patta» (8 kalit). Uni taqiqlash 1–6-fazaning **13 kalitini** qizartirardi (§14.5, O-03) |
| **M-12** | **Tugma variantlari** [KOD: `button.tsx:21-35`] | `default` = ⛔ **`bg-accent`** · `secondary` · `ghost` · `destructive`. O'lchamlar: `sm` 36px · `md` 40px · `lg` **min 44px**. 7-faza `default` ni **aynan bir joyda** ishlatadi (§13.3) |
| **M-13** | **Yo'q narsalar** | `frontend/src/app/[locale]/(app)/reconciliation` — **yo'q**; `ops/i18n/glossary.json` — **yo'q**. Ikkalasi ham Wave 0 (§5.1) |

### 0.2 M-7 ning oqibati — ochiq yozilgan tuzoq

```
api-client.ts:215   if (token) headers.Authorization = `Bearer ${token}`;
```

Access token **xotirada** yashaydi va **so'rov sarlavhasida** ketadi; cookie'da faqat **refresh** bor. Demak:

> ⛔ Yangi oynada ochiladigan `<a href="…/snapshots/{id}/image">` **hech qachon ishlamaydi** — u tokensiz ketadi va **401** oladi. «Dalil havolasi» ni shunday tushunish UI'ni **birinchi bosishdayoq** buzardi, va ijrochi buni tuzatish uchun tabiiy ravishda **rasmni sahifaga qo'yishga** o'tardi — ya'ni ⛔ **D-03 taqig'ini aylanib o'tardi**.

**Tanlangan yo'l** (§8.4): dalil havolasi — **`next-intl` `<Link>`**, nishoni **mavjud veb yuzasi** (`/billing?day=…`), u yerda kadr **allaqachon** `useEvidenceImageHref()` bilan, sessiya tokeni ostida chiziladi [KOD: `review-queries.ts:239`, `anomaly-list.tsx:233-260`].

**Rad etilgan muqobil:** `useEvidenceImageHref` ni `/reconciliation` da qayta ishlatib kadrni **shu yerda** chizish. Sabab: `components/reconciliation/**` — **xabar/ogohlantirish yuzasi** (04-UI-SPEC D-19 ma'nosida) va **G7-3** aynan shu katalogni skanerlaydi; ikkinchi kadr yuzasi `SNAPSHOT_EVIDENCE_FRAME_ROUTES` ni kengaytirish bosimini tug'dirardi (06-UI-SPEC M-8).

---

## 1. Ko'lam

### 1.1 Beshta yuza — ular teng og'ir emas

| # | Yuza | Nimaga javob beradi | Foydalanuvchi | Ustuvorlik |
|---|------|---------------------|---------------|------------|
| **Y-1** | ⛔ **Kunlik nomuvofiqlik hisoboti** (RECON-01) | «Kecha qaysi rasta band edi-yu, patta kelmadi?» | Direktor, bozor admini | ⛔ **ENG YUQORI** |
| **Y-2** | **Case navbati, tafsiloti, aniqlik ulushi** (RECON-02) | «Buni kim ko'ryapti va u asosli chiqdimi?» | Direktor (hukm), bozor admini (o'qish) | Yuqori |
| **Y-3** | ⛔ **Bosh ekran ko'rsatkichi** (RECON-06) | «Bugun men uchun eng muhim bitta raqam qaysi?» | ⛔ **Uchala rol** | Yuqori |
| **Y-4** | **Xabar yetkazilishi** (BOT-04) | «Sotuvchi xabar oldimi — yoki aloqa uzilganmi?» | Direktor | O'rta |
| **Y-5** | **Xabar matni** (RECON-03, CASH-05, BOT-01/02/03) | «Telegramda nima yozilgan?» | Sotuvchi, direktor — ⛔ **veb emas, lekin copy kontraktida** | O'rta |

### 1.2 Y-1 nima uchun eng yuqori — va UI uni QANDAY jimgina buzadi

ROADMAP Phase 7 SC#1: *«Kunlik nomuvofiqlik hisoboti "band, lekin to'lovsiz" rastalar va "ro'yxatga olinmagan savdo" anomaliyalarini **rasm-dalil havolalari** bilan ko'rsatadi.»*
07-CONTEXT D-02: 6-fazadagi «sotuvchi to'laganini isbotlay olmasligi» ustiga ikkinchi nizo qo'shiladi — **«xabar kelmadi»**.

> Direktor kechqurun «bugun kutilayotgan: 4 200 000» oldi. Ertalab «kecha yozilgan: 3 950 000» chiqdi. Hech qayerda **nega ikki xil** ekani yozilmagan. Uchinchi kuni direktor ikkala xabarni ham **o'qimay qo'yadi** — va tizim texnik jihatdan **mukammal ishlaganicha** qadrsizlanadi.

Beshta qoida **muzokarasiz** va §16 da darvozaga aylanadi:

| # | Qoida | Nega UI qatlamida ham kerak |
|---|-------|------------------------------|
| **1** | ⛔ Ikki sinf (**A** band-lekin-to'lovsiz · **B** ro'yxatga olinmagan savdo) **hech qachon qo'shilmaydi** | Turli manba (hosila ↔ qator), turli dalil yo'li (Pattern 4). «Jami nomuvofiqlik» hisobotni **jimgina noto'g'ri** qilardi (**G-30**) |
| **2** | ⛔ Dalil **havola**, kadr **emas** | D-03 + M-7 (**G7-3**) |
| **3** | ⛔ Aniqlik ulushi **maxraji bilan** ko'rsatiladi | `yangi`/`ko'rilmoqda` maxrajga kirmaydi (D-13). Maxrajsiz 68% — direktor uni «100 tadan 68 tasi» deb o'qiydi (**G-32**) |
| **4** | ⛔ Bosh ekranda **aynan bitta son**, kassirniki **SUMMA emas** | D-28/D-29 + Pitfall 1 (**G-33**) |
| **5** | ⛔ «Yetkazildi» **isbotlanmagan narsani da'vo qilmaydi** | Bot API yetkazilganlik kvitansiyasi **bermaydi** (Pitfall 2) (**G-34**) |

### 1.3 Talab qamrovi

| REQ | UI'da qanday ko'rinadi |
|-----|------------------------|
| **RECON-01** | Y-1 — ⛔ **ikki alohida blok** `unpaid` va `unregistered`; har qatorda **dalil havolasi**; birlashtirilgan jami **yo'q** |
| **RECON-02** | Y-2 — `cases` bloki + DL-5 (holat, mas'ul, yechim, audit izi) + `hitrate` bloki |
| **RECON-03** | UI'da bevosita yo'q (job). §12 uning **matn kontrakti**: «kutilayotgan» ↔ «yozilgan» majburiy |
| **RECON-06** | Y-3 — `/dashboard` da `headline-card.tsx`; ⛔ **bitta son + bitta yorliq** |
| **CASH-05** | UI'da bevosita yo'q. Y-4 uning **yetkazilganligini** ko'rsatadi; §14.6 matni |
| **BOT-01/02/03** | Veb'da yo'q. §14.6 matn kontrakti; ⛔ `balance` so'zi **hech qayerda** (**G-36**) |
| **BOT-04** | Y-4 — `delivery` bloki, **5 holat**, ⛔ `blocked` **xato emas** |

### 1.4 Bu faza UI'si NIMA QILMAYDI (to'lig'i §17)

Direktor botining **buyruq** yuzasi · botdan **to'lov** · `.xlsx`/diagramma/arxiv qidiruvi (8-faza) · **AI aniqlik hisoboti** (`RECON-05`, 8-faza — ⛔ bu fazadagi «aniqlik ulushi» **case hit-rate**, AI aniqligi **emas**) · qo'lda «xabarni qayta yuborish» tugmasi (⛔ **umuman qurilmaydi**, §17.2).

---

## 2. Yuqori oqim qarorlaridan meros

| Qaror / Topilma | Manba | UI'dagi bevosita oqibati |
|---|---|---|
| **D-02** nizo modeli kengaydi — «xabar kelmadi» | 07-CONTEXT | Y-4 ning butun mavjudlik sababi; §11.2 «yetkazildi» ning aniq ta'rifi |
| **D-03** dalil-kadr Telegramga **hech qachon** | 07-CONTEXT | §8.4 havola kontrakti + **G7-3**; §14.6 bot matnida havola, bayt emas |
| **D-05** `PERSONAL_ROUTES` **o'smaydi** | 07-CONTEXT | §5.5: yangi marshrutlar ism **qaytarmaydi**; ⛔ `chat_id` ham **yo'q** |
| **D-06/D-07** saqlangan balans yo'q; pul `BIGINT`↔`int` | 07-CONTEXT | §5.5 + **G-36**; pul **faqat** `useFormatter().number()` + `*.amountUnit` |
| **D-12** case holati — yopiq 4 a'zo, `other` **yo'q** | 07-CONTEXT | §9.2 native `<select>`; **G-31** to'plam tengligi × 3 locale |
| **D-13** hit-rate **hosila**; `yangi`/`ko'rilmoqda` maxrajda yo'q | 07-CONTEXT | §9.5 maxraj jumlasi **majburiy**; 0/0 da foiz **chizilmaydi** (**G-32**) |
| **D-14** holat o'zgarishi — **audit qatori**; yechim erkin, holat yopiq | 07-CONTEXT | §9.3/§9.4; ⛔ `[Tahrirlash]`/`[O'chirish]` **yo'q** |
| **D-22** bloklagan foydalanuvchi — **ma'lumot**, xato emas | 07-CONTEXT | §11.2: `tone="neutral"`, ⛔ `danger` **emas**, `role="alert"` **emas** |
| **D-28/D-29** bitta marshrut, **aynan bitta son + yorliq** | 07-CONTEXT | §10.2 komponent **rolni umuman o'qimaydi** → ikkinchi son **imkonsiz** (**G-33**) |
| **D-30/D-31** atamalar yagona, uchala locale | 07-CONTEXT | §14.5 glossariy + **G7-9**; §14.1 atama jadvali |
| **Pitfall 1** RECON-06 ↔ CASH-04 to'qnashuvi | 07-RESEARCH:866 | §10.3: kassirniki — **kvitansiyalar SONI**; `HEADLINE_UNIT` + **G-33(d)** |
| **Pitfall 2** Telegram yetkazilganlikni tasdiqlamaydi | 07-RESEARCH:887 | §11.2 «Telegram qabul qildi»; ⛔ `CheckCheck` **taqiq** (**G-34**) |
| **DQ-4** kun kesimi + keyset; envelope `ChargeListResponse` naqshi | 07-RESEARCH:366 | §5.4 kesh + §9.2 envelope — klient sxemasi **birinchi kundan** mos |
| **DQ-6** `ReconciliationCaseStatus` = `new/in_review/justified/unjustified` | 07-RESEARCH:413 | ⛔ **Qiymatlar inglizcha, ekran matni i18n kaliti** — §14.1 |
| **Pattern 3** ikki xabar, ikki manba; farq **matnda** | 07-RESEARCH:667 | §12 (**G-35**) |
| **Pattern 4** ikki sinf bir jadvalga tushmaydi | 07-RESEARCH:683 | §8.2 (**G-30**) |
| **Pattern 5** case `recon.open` cron'ida, `overdue_days` chegarasi bilan | 07-RESEARCH:701 | §8.5: ⛔ `[Case ochish]` tugmasi **qurilmaydi** |

---

## 3. Dizayn tizimi holati

### 3.1 Meros — o'zgarmaydi va qayta qurilmaydi

| Nima | Fayl | 7-fazada |
|------|------|----------|
| Tailwind 4 CSS-first `@theme` | `frontend/src/app/globals.css` | ⛔ **O'zgarmaydi. Yangi token YO'Q** |
| `Button` (4 variant, `lg` min 44px) [M-12] | `ui/button.tsx` | DL-5 saqlash (`default`), qolgani `secondary`/`ghost` |
| `Card`/`CardHeader`/`CardContent` | `ui/card.tsx` | Beshala blok, headline kartasi |
| `Input` + `Field` (`${id}-error`/`${id}-hint`) | `ui/input.tsx`, `ui/field.tsx` | DL-5 yechim maydoni |
| `Select` (native `<select>`) | `ui/select.tsx` | ⛔ Case **holati** va **mas'ul** — yopiq to'plam |
| `Badge` (`neutral/muted/accent/success/warning/danger`) [KOD: `badge.tsx:28-43`] | `ui/badge.tsx` | Case holati, yetkazilganlik, sinf yorlig'i |
| `Skeleton` (`motion-reduce:animate-none`) | `ui/skeleton.tsx` | Blok va headline yuklanishi |
| `EmptyState` (`title`/`description`/`action`) | `ui/empty-state.tsx` | **5 ta** bo'sh holat (§14.7) |
| `Dialog` (`sm/md/lg` + `sheetOnMobile`) | `ui/dialog.tsx` | **DL-5** |
| `ConfirmDialog` | `ui/confirm-dialog.tsx` | ⛔ **ISHLATILMAYDI** — bu fazada destruktiv amal **yo'q** (§14.8) |
| `sonner` Toaster (`top-center richColors`) | `layout.tsx:82` | 3 ta toast (§14.7) |
| `nuqs` URL holati | `day-picker.tsx` naqshi | ⛔ **Faqat `?day=`** (§4.5) |
| RBAC UI ko'zgusi (huquq yo'q → **render qilinmaydi**) | `lib/rbac.ts` | ⛔ **Yangi huquq YO'Q** [M-6] |
| next-intl 3 til + `i18n:check` | `messages/*`, `scripts/*.mjs` | §14; ⛔ `uz-Cyrl.json` **qo'lda tahrirlanmaydi** |
| Pul: `useFormatter().number()` + `*.amountUnit` | `pending-summary.tsx:155`, `variance-cell.tsx:90` | ⛔ **Yagona yo'l** — pul kutubxonasi qo'shilmaydi |
| Dalil kadri: `useEvidenceImageHref()` + `bg-text` letterbox | `review-queries.ts:239`, `anomaly-list.tsx:233` | ⛔ `components/reconciliation/**` da **ISHLATILMAYDI** (§0.2) |
| Blok reyestri: `data-billing-block` + mazmun juftligi | `billing/page.tsx:126-197` | §8.1 `data-recon-block` — **shu naqshning nusxasi** |

### 3.2 Yangi `ui/` primitivi — YO'Q [M-2]

Ikkita chegaraviy holat **ataylab** `ui/` ga ko'tarilmaydi:

| Komponent | Nega `ui/` emas |
|-----------|------------------|
| `headline/headline-card.tsx` | Uning butun ma'nosi — ⛔ **ikkinchi sonni ko'rsata olmaslik** (§10.2). `ui/` dagi «katta raqam kartasi» ertaga `secondaryValue` propini olardi va D-29 **bitta `props` uzatilishi** bilan buzilardi — 06-UI-SPEC `shift-close-form.tsx` mulohazasining takrori |
| `reconciliation/delivery-badge.tsx` | 5 holat + ikonka + `tone` + «o'qildi demaydigan» matn — **domen qoidasi** (D-22, Pitfall 2), umumiy «holat nishoni» emas |

### 3.3 Analogi yo'q komponentlar

| Komponent | Nega analog yo'q | Nima qilinadi |
|-----------|------------------|---------------|
| `case-detail-dialog.tsx` | «Yopiq holat + erkin matn + o'zgarmas audit izi» uchligi kodbazada yo'q. `charge-detail-dialog.tsx` — **o'qish uchun**; `reason-dialog.tsx` — ⛔ **erkin matn taqiqlangan** | §9.3–§9.4; ⛔ `<textarea>` istisnosi **ochiq yozilgan** |
| `delivery-list.tsx` | `alert-list.tsx` — holat mashinasisiz; `variance-list.tsx` — **uch** holatli | §11.3 |
| `headline-card.tsx` | `pending-summary.tsx` — **uch** ko'rsatkichli. Bu esa **bitta**, va bitta bo'lishi uning **kontrakti** | §10.2 |

### 3.4 shadcn darvozasi — natija [M-1]

**`components.json` topilmadi** → **`Tool: none`. `shadcn init` BAJARILMAYDI.** [QAROR — 2–6-faza qarorini davom ettiradi]

Sabablar: (1) `shadcn init` `package.json` ga yangi paket keltiradi; (2) Tailwind 4 rejimida u `globals.css` ga **o'z token nomlarini** yozadi va `--color-bg`/`--color-surface`/`--color-accent` yonida **ikkinchi dizayn tizimi** paydo bo'lardi; (3) bu subagent kontekstida interaktiv savol vositasi yo'q (`--auto`).

**Oqibat:** `Registry Safety` darvozasi shadcn uchun **qo'llanmaydi** (§15).

### 3.5 Yangi bog'liqlik — YO'Q

**Yangi npm paketi: YO'Q.** [QAROR — 07-RESEARCH § Package Legitimacy Audit: yangi paketlar **faqat `bot-service`** ga; frontendga **hech nima**]

| Ehtiyoj | Mavjud yechim | Nega yangi paket kerak emas |
|---------|---------------|------------------------------|
| Foiz formatlash (hit-rate) | `useFormatter().number(v,{style:"percent"})` | Node 24 to'liq ICU. ⛔ Qo'lda `Math.round(x*100)+"%"` **yozilmaydi** — `%` joyi va ajratkich locale'ga bog'liq |
| Nisbiy vaqt («2 soat oldin») | ⛔ **YO'Q — absolut vaqt** | Nizoda «2 soat oldin» **o'qib aytib bo'lmaydi**; `useFormatter().dateTime()` yetadi, `date-fns` kerak emas |
| Case sahifalash | `nuqs` + keyset (DQ-4) | 5 ustunli `<table>` — jadval kutubxonasi kerak emas |
| Holat tanlash | native `<select>` | Yopiq 4 a'zo; telefonda OS ro'yxati tezroq |
| Diagramma | ⛔ **YO'Q** | `recharts` `package.json` da yo'q; **8-faza** egasi |

> Reja bajarilishida boshqa paket zarur bo'lsa, u **UI-SPEC ga qaytariladi** — jimgina `npm install` **qilinmaydi** [MEROS: 02-UI-SPEC §13].

---

## 4. Ekranlar reyestri

### 4.1 Marshrutlar

| Marshrut | Yuza | Vazifa | Huquq (UI ko'zgusi) |
|----------|------|--------|---------------------|
| `/[locale]/(app)/reconciliation` | **Y-1 + Y-2 + Y-4** | Nomuvofiqlik hisoboti, case navbati, aniqlik ulushi, xabar yetkazilishi | `report_view` |
| `…/reconciliation?day=YYYY-MM-DD` | O'sha | O'sha sahifa, tanlangan biznes-kun (`nuqs`) | `report_view` |
| `/[locale]/(app)/dashboard` | **Y-3** | ⛔ **Mavjud sahifa** — unga `headline-card.tsx` qo'shiladi | ⛔ huquq **yo'q** (`permission: null`) |

⛔ **Boshqa marshrut YO'Q.** `/reconciliation/[caseId]`, `/cases`, `/notifications`, `/outbox`, `/delivery`, `/bot` — **qurilmaydi**.

### 4.2 Nega case tafsiloti DIALOG, marshrut emas [QAROR]

Muqobil: `/reconciliation/[caseId]`. **Rad etildi:**

1. ⛔ **Yarim yozilgan yechim matni ulashiladigan URL yaratardi.** DL-5 da erkin matnli yechim maydoni bor (§9.4); havolani nusxalab yuborganda qabul qiluvchi **boshqa holatdagi** formani ko'rardi — 06-UI-SPEC §4.5 `?declared=` mulohazasi aynan shu sinfda.
2. **Deep-link ehtiyoji KUN darajasida.** Kechki xabar va dayjest havolasi `/reconciliation?day=YYYY-MM-DD` ga boradi (§14.6) — bu **hisobot**, ulashiladi. Bitta case — **jarayon**, ulashilmaydi.
3. **Dialog holati URL'da emas** [MEROS: 02-UI-SPEC §7.1] — 2-fazadan beri o'zgarmagan, istisno so'ralmaydi.

### 4.3 Nega `/reconciliation` ALOHIDA marshrut, `/billing` ga blok qo'shilmaydi [QAROR]

⛔ **Rad etildi va sabab MEXANIK:**

| # | Sabab |
|---|-------|
| 1 | ⛔⛔ **`G-25` blok to'plamini TO'PLAM TENGLIGI bilan qulflagan** [KOD: `06-UI-SPEC.md` §15.3 G-25(a)]: `?day=bugun` → `{"day","pending","shifts"}`; `?day=kecha` → `{"day","charges","anomalies","shifts"}`. Oltinchi blok **ikkala assertni ham** o'zgartirishni talab qilardi — ya'ni 7-faza 6-fazaning **darvozasini tahrirlardi**. Bu 06-UI-SPEC §0.2 ning aynan darsi |
| 2 | **Kun semantikasi boshqa.** `/billing` da bugun uchun **proyeksiya bor**; `/reconciliation` da proyeksiya **umuman yo'q** — case'lar **04:25 da** kechagi kun uchun tug'iladi (Pattern 5). §4.4 |
| 3 | ⛔ **Alohida katalog — darvozaning sharti.** `components/reconciliation/**` alohida bo'lgani uchun **G7-3** kadr taqig'ini va **G-36** taqiqlangan nomlarni skanerlay oladi. Aralash katalogda `<img>` **qonuniy** bo'lardi (`anomaly-list.tsx` da u **bor**) va shart **kontekstga bog'liq** bo'lardi — 06-UI-SPEC §4.3/§5.3 takrori |
| 4 | **Navigatsiya sig'imi buzilmaydi** [M-5]: 16-element kassir panelini **umuman o'zgartirmaydi** |

### 4.4 ⛔ Kun tanlagichi — standart KECHA, maksimum BUGUN, bloklar KUNGA QARAB [QAROR]

| Qoida | Qiymat | Sabab |
|-------|--------|-------|
| Standart | ⛔ **kecha** | Case'lar `recon.open` da **04:25**, `billing.close` (04:10) dan keyin tug'iladi (Pattern 5). Standarti **bugun** bo'lsa sahifa **har doim bo'sh** ochilardi — 06-UI-SPEC §11.1 mulohazasi |
| Maksimum | **bugun** | Kelajak **imkonsiz**; **bugun** esa **kerak** ⬇ |
| `day < bugun` | Oltala blok | Kecha **yozilgan** va **o'zgarmas** |
| `day = bugun` | ⛔ **Faqat** `day` + `delivery`; qolgan **to'rttasi UMUMAN chizilmaydi** | ⬇ |

⛔ **Nega `day = bugun` da to'rt blok CHIZILMAYDI (bo'sh emas — YO'Q):**

1. **Ular bugun MAVJUD EMAS.** `daily_charges` D+1 **04:10**, case'lar D+1 **04:25**. Bo'sh ro'yxat «bugun nomuvofiqlik yo'q» degan **soxta ijobiy** javob bo'lardi — 06-UI-SPEC §9.1 «soxta ko'rsatkich» sinfi.
2. ⛔ **Yetkazilganlik esa BUGUN kerak.** Kvitansiya **hozir** ketadi (D-18) va «xabar kelmadi» nizosi **o'sha kuni** chiqadi. `delivery` ham kechaga qulflansa, BOT-04 ning **amaliy qiymati nolga tushardi** (07-CONTEXT `<specifics>`).

⛔ **Kesishma `{"day","delivery"}`** — hisobot bloklari va **yo'q-hisobot** hech qachon uchrashmaydi. Bu 06-UI-SPEC §9.3 kanal 7 naqshi; **G-29** da to'plam tengligi bilan o'lchanadi.

### 4.5 URL holati kontrakti

| Yuza | URL holati | Sabab |
|------|-----------|-------|
| `/reconciliation` | ✅ **`?day=YYYY-MM-DD`** (`nuqs`) | `/billing?day=`, `/occupancy?day=` bilan **aynan bir naqsh** — kun ulashiladi, chunki u **hisobot** |
| **DL-5** | ⛔ **YO'Q** | §4.2 |
| `/dashboard` (Y-3) | ⛔ **YO'Q** | Ko'rsatkich **serverdan** keladi (D-28) |
| Case filtri `?status=` | ⛔ **YO'Q — bu fazada** | §17.3. Navbat kuniga ~10 qator (Pattern 5 chegarasi bilan); filtr **hal qilinmagan muammoni yashirardi**. Envelope'dagi to'rt sanoq (§9.2) filtrsiz ham javob beradi |

### 4.6 Dialog

| # | Dialog | Ochiladi | O'lcham | Huquq |
|---|--------|----------|---------|-------|
| **DL-5** | **Nomuvofiqlik tafsiloti** — subyekt, dalil havolasi, holat, mas'ul, yechim, audit izi | Y-2 case qatoridan `[Ko'rib chiqish]` | `size="lg" sheetOnMobile` | Ko'rish: `report_view` · ⛔ Yozuv: `dispute_decide` |

⛔ Boshqa dialog **yo'q**: yetkazilganlik qatorining tafsiloti **yo'q** (§11.3 — jadval o'zi to'liq), headline tafsiloti **yo'q** (D-29).

### 4.7 Navigatsiya — bitta yozuv [QAROR]

| Yozuv | Guruh | Ikonka | Huquq | Joyi |
|-------|-------|--------|-------|------|
| **Nomuvofiqliklar** (`/reconciliation`) | `market` | `FileWarning` | `report_view` | ⛔ `/billing` dan **keyin** |

[M-5] `NAV_ITEMS` 15→**16**. ⛔ `cashier` **2 (o'zgarmaydi)**, mobil overflow **0**.

⚠ **`FileWarning` nima uchun** (`Gavel`/`Scale` emas): bolg'a va tarozi — **hukm** metaforasi; ular navbatni «sud» qilib ko'rsatardi va `asossiz` a'zosini **ayblovga** aylantirardi. `TriangleAlert` rad etildi — u **xato** ikonkasi va §11.2 da `failed` uchun band.

---

## 5. Komponentlar reyestri

### 5.1 Wave 0 — bloklovchi

| # | Ish | Fayl | Nega bloklovchi |
|---|-----|------|------------------|
| **W0-F1** | ⛔ `ops/i18n/glossary.json` — 4 atama × 3 locale (**o'zak** shaklida) | yangi | [M-10] **G7-9** ning asosi. Fayl bo'lmasa darvoza **jimgina bo'sh skan** qiladi — 06-UI-SPEC §15.2 `MIN_*` darsi |
| **W0-F2** | `frontend/scripts/glossary.test.mjs` — G7-9 ning **frontend yarmi** | yangi | §16.4 |
| **W0-F3** | `frontend/scripts/reconciliation-copy.test.mjs` | yangi | ⛔ **G7-3** + **G-30/G-31/G-34/G-35**. `stripComments()` `bulk-action-surface.test.mjs:163-225` dan **ko'chiriladi** |
| **W0-F4** | `lib/reconciliation-queries.ts` — ⛔ **yagona** so'rov moduli | yangi | **G-36** asosi. Yetkazilganlik so'rovi ham **shu modulda** |
| **W0-F5** | `lib/headline-queries.ts` + `HEADLINE_UNIT` | yangi | **G-33(d)** |
| **W0-F6** | `05-UI-SPEC.md` §15 G-18 qatoriga `` `components/reconciliation/**` `` | mavjud fayl (**1 qator**) | [M-4] §16.5. ⛔ **Birinchi `components/reconciliation/*.tsx` bilan bitta commitda** — darvoza katalogning **mavjud va bo'sh emasligini** tekshiradi (`:293-308`) |
| **W0-F7** | `RECON_ERROR_CODES` | `lib/reconciliation-errors.ts` | §14.9; `error-codes.test.mjs` (G-17) **uchala tilda** talab qiladi |
| **W0-F8** | `CASE_STATUSES`, `DELIVERY_STATES`, `NOTIFICATION_KINDS` ko'zgusi | `lib/api-types.ts` | **G-31**/**G-34** reyestrdan **iteratsiya qiladi**; darvoza tekshirayotgan qiymatni **import qilmaydi**, ikkinchi marta **yozadi** (05-13 darsi) |

⛔ **Hech qaysi Wave 0 ishi `rbac.ts`/`rbac.py` ga tegmaydi** [M-6].

### 5.2 Yangi komponentlar

| Fayl | Yuza | Vazifa | Bo'lim |
|------|------|--------|--------|
| `reconciliation/day-picker.tsx` | Y-1 | `?day=`, maks **bugun**, standart **kecha** | §4.4 |
| `reconciliation/unpaid-list.tsx` | Y-1 | ⛔ **Sinf A** | §8.2, §8.3 |
| `reconciliation/unregistered-list.tsx` | Y-1 | ⛔ **Sinf B** | §8.2, §8.3 |
| `reconciliation/evidence-link.tsx` | Y-1, Y-2 | ⛔ **Havola**, kadr **emas** | §8.4 |
| `reconciliation/case-list.tsx` | Y-2 | Case navbati | §9.2 |
| `reconciliation/case-status-badge.tsx` | Y-2 | 4 holat — 4 `tone` + 4 ikonka | §9.2 |
| `reconciliation/case-detail-dialog.tsx` | DL-5 | Holat, mas'ul, yechim, **audit izi** | §9.3–§9.4 |
| `reconciliation/hit-rate-card.tsx` | Y-2 | ⛔ Foiz + **maxraj jumlasi**; 0/0 da foiz **yo'q** | §9.5 |
| `reconciliation/delivery-list.tsx` | Y-4 | 5 holat | §11.3 |
| `reconciliation/delivery-badge.tsx` | Y-4 | ⛔ `CheckCheck` **taqiq**; `blocked` **xato emas** | §11.2 |
| `headline/headline-card.tsx` | Y-3 | ⛔ Bitta son + bitta yorliq; ⛔ rol **o'qilmaydi** | §10.2 |

### 5.3 ⛔ Nega `lib/reconciliation-queries.ts` YAGONA va nega `billing-*` ga qo'shilmaydi

1. **G-36 shundan keyin yozilishi mumkin.** Taqiqlangan nomlar (`chat_id`, `balance`, `vendor_name`, `hit_rate`, `last_error` matni) **butun faylda** izlanadi; aralash modulda ba'zisi **qonuniy** bo'lardi.
2. **Kesh siyosati bir xil** — hammasi yozilgan ma'lumot; ⛔ istisno faqat `delivery` (`day=bugun` da jonli, §5.4).
3. **Tip tizimi ish qiladi** — aralash modulda tip birlashmasi paydo bo'lardi va `undefined` **jimgina** o'tardi.

### 5.4 Kesh kalitlari — tug'ilishidanoq doiralangan

Kalitlar `marketId` bilan **boshlanadi** [MEROS: 04-UI-SPEC; `tenant-cache.test.tsx`].

| Kalit | `staleTime` | `gcTime` | Sabab |
|-------|-------------|----------|-------|
| `[marketId,"recon-report",day]` | 60 s | standart | Yozilgan hisob **o'zgarmas** (D-07) |
| `[marketId,"recon-cases",day,cursor]` | 30 s | standart | Case **o'zgaradi** (holat, mas'ul) |
| `[marketId,"recon-hitrate",day]` | 30 s | standart | Case'lardan **hosila** — u bilan bir tezlikda |
| `[marketId,"recon-delivery",day]` | ⛔ `bugun` → **0**; `<bugun` → 60 s | ⛔ `bugun` → **0** | ⛔ Bugungi yetkazilganlik **jonli**: `pending→sent→delivered` soniyalarda o'zgaradi; eski javob «hali yuborilmadi» deb **yolg'on gapirardi** |

⛔ **Case o'zgargandan keyin — `invalidateQueries`, `removeQueries` EMAS.** Sabab 6-fazadan **farqli** va u ochiq yozilishi shart: u yerda keshdan chiqarish kerak edi, chunki eski rastaning summasi **noto'g'ri pul yig'ishga** olib borardi (06-UI-SPEC §9.4); bu yerda keshdan chiqarish ro'yxatni **bo'shatib**, direktor o'z o'zgarishini **yo'qolgan** deb o'ylardi. ⛔ **Uchta** kalit birga: `recon-cases`, `recon-hitrate` **va** `recon-report` (§8.5 dagi case belgisi). Bittasi unutilsa, ekranda **ikki xil haqiqat** qoladi.

### 5.5 ⛔⛔ Shaxsiy ma'lumot: yangi marshrut ism QAYTARMAYDI [QAROR — D-05]

7-faza qo'shadigan **birorta** marshrut `PERSONAL_FIELDS = {vendor_name, phone, full_name}` dan bittasini ham qaytarmaydi. Har ism **mavjud, audit qilingan** marshrutdan (`GET /vendors`, `GET /users`) olinib, **klientda** joinlanadi [MEROS: 06-UI-SPEC §5.5].

| Yuza | Ism kerakmi | Manba | Huquq |
|------|-------------|-------|-------|
| `unpaid` / `unregistered` | ✅ sotuvchi | `GET /vendors` | `vendor_view` (director + market_admin — ikkalasida **bor**) |
| Case ro'yxati, DL-5 | ✅ sotuvchi + **mas'ul** | `GET /vendors` + `GET /users` | `vendor_view` + `user_view` |
| Headline | ⛔ **YO'Q** | — | Javob `{metric,value}` — ism uchun **joy yo'q** |
| `delivery` | ✅ sotuvchi | `GET /vendors` | `vendor_view` |

⛔⛔ **`chat_id` / `telegram_user_id` / `telegram_username` MARSHRUT JAVOBIDA UMUMAN YO'Q** [QAROR — D-05 kengaytmasi]:

Telegram identifikatori `PERSONAL_FIELDS` da **yo'q**, ya'ni C-10 darvozasi uni **ushlamaydi**. Lekin u **aynan shu sinfdagi** ma'lumot: odamni **tashqi tizimda** aniqlaydi va u chegaradan **chiqib bo'lgan** (D-01). Qator sotuvchini **`vendor_id`** bilan aytadi; ⛔ **G-36** bu uch nomni taqiqlangan nomlar reyestriga qo'shadi — C-10 ushlamaydigan bo'shliq **frontend darvozasi** bilan yopiladi.

⚠ **Ochiq narx:** sahifa **ikkita qo'shimcha** so'rov qiladi (`/vendors`, `/users`) — `deferred-items.md` 9-bandi bilan bir sinfda. ⛔ To'g'ri tuzatish — **mavjud** marshrutlarni sahifalash, nomuvofiqlik marshrutiga ism maydoni **qo'shish emas**. Egasi — 8-faza.

### 5.6 RBAC — ⛔ YANGI HUQUQ YO'Q [QAROR — M-6]

| Huquq | Holat | Kim | Nimani qo'riqlaydi |
|-------|-------|-----|--------------------|
| `report_view` | mavjud | `director`, `market_admin` | Sahifa, `GET /reconciliation/*` **o'qish** |
| `dispute_decide` | ⛔ **mavjud, bugungacha iste'molchisiz** [KOD: `rbac.py:170,243`] | ⛔ **faqat `director`** | DL-5 **yozuv** yuzasi |
| `camera_view` \|\| `occupancy_review` | mavjud | director, market_admin, platform_admin, inspector | Dalil havolasining **chizilishi** (§8.4) |
| `vendor_view` / `user_view` | mavjud | director, market_admin | Ism joini |
| — | ⛔ headline uchun huquq **yo'q** | hamma | `GET /me/headline` — rol **serverda** (D-28) |

**Nega `dispute_decide`:** (1) nomi aynan shu ishni aytadi — yangi `case_manage` **ikkinchi nom** bo'lardi; (2) ⛔ `rbac.py`↔`rbac.ts` juftligi **tegilmaydi**, `role-gate.test.mjs:29-56` **o'zgarishsiz** yashil qoladi; (3) hukm direktorda qolishi D-07 bilan izchil.

⚠ **Ochiq narx va TETIGI** (§18 O-01): bozor admini navbatni **ishlata olmaydi**. Dala UAT buni to'siq desa — ⛔ to'g'ri tuzatish **`dispute_decide` ni `market_admin` ga BERISH** (ikkala matritsada, **bitta commitda**), yangi huquq **emas**.

### 5.7 Kengaytiriladigan mavjud fayllar

| Fayl | O'zgarish |
|------|-----------|
| `components/shell/app-shell.tsx` | `NAV_ITEMS` ga **1 yozuv** (§4.7) |
| `app/[locale]/(app)/dashboard/page.tsx` | `<HeadlineCard />` — ⛔ sarlavhadan **keyin**, `SECTIONS` dan **oldin** (§10.4) |
| `lib/api-types.ts` | 3 enum ko'zgusi; `soumSchema` **qayta ishlatiladi** |
| `messages/uz-Latn.json` + `ru.json` | `recon.*`, `headline.*` |
| `messages/uz-Cyrl.json` | ⛔ **QO'LDA TAHRIRLANMAYDI** — `npm --prefix frontend run i18n:gen` |
| `messages/uz-Cyrl.overrides.json` | ⛔ **Tegilishi KUTILMAYDI** [M-8: 26 satrdan 25 tasi toza; 26-chisi «case» — u copy'ga **kirmaydi**] |
| `05-UI-SPEC.md` §15 | G-18 qatoriga **to'rtinchi** katalog naqshi (W0-F6) |
| `scripts/error-codes.test.mjs` | `RECON_ERROR_CODES` qo'shiladi |

### 5.8 Komponent testlari

| Test | Nimani o'lchaydi | Darvoza |
|------|-------------------|---------|
| `reconciliation/page.test.tsx` | Blok to'plami `bugun` ↔ `kecha`; ⛔ mazmun juftligi (bo'sh o'ram **o'tmaydi**) | **G-29** |
| `reconciliation/unpaid-list.test.tsx` | ⛔ A va B **hech qanday jami bermaydi**; dalil `<Link>`, `<img>` **0** | **G-30**, **G7-3** |
| `reconciliation/case-detail-dialog.test.tsx` | `<option>` **qiymatlari to'plami = 4**; `dispute_decide` yo'q → yozuv yuzasi **0**; terminal holatda yechimsiz `[Saqlash]` **`aria-disabled`** | **G-31** |
| `reconciliation/hit-rate-card.test.tsx` | Foiz chizilsa **to'rt sanoq ham** DOM'da; `justified+unjustified===0` → foiz **umuman yo'q** | **G-32** |
| `reconciliation/delivery-list.test.tsx` | Beshala holat; `blocked` — `tone="neutral"`, `role="alert"` **yo'q**; `CheckCheck` **0** | **G-34** |
| `headline/headline-card.test.tsx` | ⛔ `[data-headline]` ichida **raqamli tugun AYNAN 1**; `roles` **umuman o'qilmaydi**; `receipts_written` → birlik **yo'q** | **G-33** |

---

## 6. Bo'shliq

### 6.1 4-panjara — o'zgarishsiz [MEROS: 06-UI-SPEC §6.1, 02-UI-SPEC §2]

| Token | Qiymat | 7-fazada qayerda |
|-------|--------|------------------|
| `xs` | 4px (`1`) | Ikonka–matn oralig'i, badge ichki `y` |
| `sm` | 8px (`2`) | Nishonlar orasi, audit izi qatorlari orasi |
| `md` | 12px (`3`) | Jadval katagi ichki, hit-rate qatorlari orasi |
| `lg` | 16px (`4`) | Karta ichki, DL-5 bo'limlari |
| `xl` | 24px (`6`) | Blok ichidagi guruhlar orasi |
| `2xl` | 32px (`8`) | ⛔ **Oltala blok orasi** (§8.1) |
| `3xl` | 48px (`12`) | Bo'sh holat `py-12` |

**Meros istisnolari saqlanadi:** 44px (`min-h-11`) barmoq nishoni; 56px (`min-h-14`) mobil pastki panel; 20px (`5`) `CardHeader`/`CardContent` ichki `x`.

### 6.2 ⛔ Yangi o'lcham SO'RALMAYDI [QAROR]

Vasvasa: *«headline soni katta bo'lsin, kartaga `p-10` beraylik»*. `p-10` (40px) **panjarada bor**, lekin u **beshinchi karta ichki qiymati** bo'lardi va keyingi fazada «muhim karta» uslubiga aylanardi. Headline **`lg` (16px)** ichki bo'shliq oladi; urg'u **tipografiyadan** keladi (§7.2).

⛔ Bu 6-fazadan **farqli** qaror va farq ochiq yozilishi shart: 6-faza **ikkita** yangi o'lcham (56px, 48px) so'ragan edi va sababi **o'lchangan sharoit** edi (quyosh, bir qo'l, qo'lqop, kuniga 300–1000 marta). Bu fazaning yuzalari — **direktor stolida, kuniga bir-ikki marta**. Bir xil dalil **yo'q**, demak bir xil istisno ham **yo'q**.

---

## 7. Tipografiya

### 7.1 To'rt rol — beshinchisi YO'Q [MEROS: 06-UI-SPEC §7.1]

| Rol | O'lcham | Og'irlik | Line-height | Tailwind |
|-----|---------|----------|-------------|----------|
| **Display** — sahifa sarlavhasi, ⛔ **headline soni**, ⛔ **hit-rate foizi** | 24px | 600 | 1.25 | `text-2xl font-semibold tracking-tight leading-tight` |
| **Heading** — karta/blok/dialog sarlavhasi, `<legend>` | 18px | 600 | 1.375 | `text-lg font-semibold leading-snug` |
| **Body** — barcha matn va boshqaruv elementi | 14px | 400 | 1.5 | `text-sm leading-normal` |
| **Meta** — badge, yorliq, sana, ⛔ **maxraj jumlasi** | 12px | 400 | 1.33 | `text-xs` |

**Urg'u — faqat og'irlik (600).** `font-medium` (500) va `text-base` (16px) **taqiqlangan** [MEROS: 02-UI-SPEC §3.2].

**Beshinchi o'lcham QO'SHILMAYDI** [QAROR]: (1) 32/40px beshinchi rol bo'lardi va hisobotlarga **tarqalardi**; (2) ⛔ **headline urg'usi o'lchamdan emas, YOLG'IZLIKDAN keladi** — u sahifadagi **yagona** Display elementi (§10.2). ⚠ Tetik: §18 O-05.

### 7.2 Headline'ning ikki elementi — rolda ajraladi

| Element | Rol | Sabab |
|---------|-----|-------|
| **Son** (`value`) | **Display** + ⛔ `font-mono` | Nizoda **o'qib aytiladi** |
| **Yorliq** (`metric`→i18n) | **Body** + `text-text-muted` | ⛔ Heading **emas**: sarlavha bilan raqobatlashardi va ko'z «bo'lim nomi» deb o'qirdi |

### 7.3 `font-mono` — 7-faza ro'yxati

| Qiymat | Uslub | Sabab |
|--------|-------|-------|
| ⛔ Har qanday `*_soum` summasi | `font-mono` | Tik solishtiriladi; nizoda o'qib aytiladi |
| ⛔ **Headline soni** (summa **ham**, sanoq **ham**) | `font-mono` | Ikki rolda ikki uslub «bu boshqa turdagi son» degan **yolg'on kanal** bo'lardi (D-28: qaysi son ekanini **server** hal qiladi, ekran **bilmaydi**) |
| ⛔ **Hit-rate foizi** | `font-mono` | Kunlar bo'ylab solishtiriladi |
| Maxraj sanoqlari (17 / 25 / 8) | `font-mono text-xs` | O'sha ustunda |
| Case identifikatorining qisqa shakli (8 belgi) | `font-mono text-xs` | Nizoda o'qib aytiladi |
| Rasta raqami (`14-C`) | ⛔ **`font-mono` EMAS** | 05-UI-SPEC §9.4: u **DB kontenti** |
| Urinishlar (`2/5`) | ⛔ **EMAS** | **Ichki mexanizm o'lchovi**, o'qib aytilmaydi |
| Sana va vaqt | ⛔ **EMAS** | `useFormatter().dateTime()` |

---

## 8. Y-1: Kunlik nomuvofiqlik hisoboti (RECON-01)

### 8.1 Blok reyestri

`data-recon-block` — `data-billing-block` naqshining **aynan nusxasi** [KOD: `billing/page.tsx:126-197`]:

| # | Blok | `data-recon-block` | Manba | `day=bugun` | `day<bugun` |
|---|------|--------------------|-------|-------------|-------------|
| A | Kun tanlagichi | `day` | — | ✅ | ✅ |
| B | ⛔ **Band, lekin to'lovsiz** | `unpaid` | `GET /reconciliation/report?day=` | ⛔ **chizilmaydi** | ✅ |
| C | ⛔ **Ro'yxatga olinmagan savdo** | `unregistered` | o'sha marshrut | ⛔ **chizilmaydi** | ✅ |
| D | Case navbati | `cases` | `GET /reconciliation/cases?day=` | ⛔ **chizilmaydi** | ✅ |
| E | Aniqlik ulushi | `hitrate` | o'sha envelope sanoqlaridan | ⛔ **chizilmaydi** | ✅ |
| F | ⛔ **Xabar yetkazilishi** | `delivery` | `GET /reconciliation/delivery?day=` | ✅ | ✅ |

⛔ **Blok to'plamlari (G-29, TO'PLAM TENGLIGI):** `bugun` → `{"day","delivery"}` · `kecha` → `{"day","unpaid","unregistered","cases","hitrate","delivery"}` · kesishma → `{"day","delivery"}`.

⛔ **Mazmun juftligi** (G-25 dan **ko'chirilgan** mexanizm): ro'yxat komponentining **O'ZI** (⛔ `page.tsx` **emas**) ildizida `data-recon-content="<blok>"` chiqaradi; `CONTENT_EXEMPT = new Set(["day"])` va ⛔ `CONTENT_EXEMPT.size === 1` **alohida assert**. Sabab 06-UI-SPEC da o'lchangan: faqat atribut to'plamini tekshiradigan darvoza **bo'sh `<div>` ni mukammal o'tkazardi**.

### 8.2 ⛔⛔ Ikki sinf — ikki BLOK, va ular hech qachon qo'shilmaydi [QAROR — Pattern 4 ning UI shakli]

| Xossa | **Sinf A** — band, lekin to'lovsiz | **Sinf B** — ro'yxatga olinmagan savdo |
|-------|-----------------------------------|--------------------------------------|
| Manba | ⛔ **Hosila**: `daily_charges` − `payments` | ⛔ **Qator**: `billing_anomalies(kind='unassigned_occupied')` |
| O'zgarmasmi | Hisob o'zgarmas, «to'landimi» **o'zgaradi** | Qator **o'zgarmas** |
| Dalil yo'li | `charge_evidence.snapshot_id` | `billing_anomalies.snapshot_id` |
| Blok | `unpaid` | `unregistered` |
| Ikonka | `Receipt` | `UserX` |
| Badge | `tone="danger"` «To'lovsiz» | `tone="warning"` «Ro'yxatga olinmagan savdo» |
| Asosiy son | Qarz summasi (`font-mono` + `so'm`) | ⛔ **Rasta SONI** — summa **yo'q** |

⛔⛔ **BIRLASHTIRILGAN JAMI YO'Q:**

| Taqiqlangan | Nega |
|-------------|------|
| «Jami nomuvofiqlik: 23» | A **hosila** (ertaga to'lov kelsa **yo'qoladi**), B **qator** (**qolaveradi**). Bitta son ikki xil umr ko'radigan narsani teng qilardi |
| «Jami yo'qotish: 4 200 000» | ⛔ **B da summa YO'Q** — biriktirilmagan zonaning tarifi **bilinmaydi**. Yig'indi **nol qo'shib** hisoblanardi va u **kam ko'rsatilgan yo'qotish** bo'lardi |
| Umumiy foiz («bandlikning 12% i to'lovsiz») | Maxraji ikki xil: A da **hisoblar**, B da **band slotlar**. Bitta foiz **ma'nosiz** |

⚠ **Ruxsat etilgan:** har blok **o'z ichida** o'z sanog'ini (A uchun — o'z summasini) ko'rsatadi. Ular **ikki blokda**, `2xl` (32px) bilan ajratilgan va ⛔ **hech qachon bir qatorda emas**.

### 8.3 Qator mazmuni

**(B) `unpaid`:** Rasta (`stall_code`) · Sotuvchi (⛔ klientda join) · Hisob summasi · To'langan · ⛔ **Qarz** (`outstanding_soum`, `font-mono` + `text-danger-text`) · ⛔ `[Dalilni ochish]` (`ghost`) · Holat (§8.5).

**(C) `unregistered`:** Kamera/zona · Vaqt (`slot_time`) · ⛔ `[Dalilni ochish]` · Holat.

⛔ **`unregistered` da RASTA USTUNI YO'Q** — ta'rifi bo'yicha u **hech qaysi rastaga biriktirilmagan** zona. Bo'sh «—» ustuni 4-fazadagi «bo'sh katak» sinfidagi jim xato bo'lardi.

### 8.4 ⛔⛔ Dalil — HAVOLA, kadr EMAS [QAROR — D-03 + M-7]

```
<Link href={`/billing?day=${service_date}`}>
  <ExternalLink aria-hidden /> Dalilni ochish
</Link>
```

| Xossa | Qiymat | Sabab |
|-------|--------|-------|
| Element | ⛔ **`next-intl` `<Link>`** (ilova ichidagi navigatsiya) | [M-7] `<a href>` rasm baytlariga **401** oladi |
| Nishon | ⛔ `/billing?day={service_date}` — **mavjud** DL-3 yuzasi | Kadr u yerda **allaqachon** sessiya ostida chiziladi [KOD: `charge-detail-dialog.tsx:325-360`]. Yangi kadr yuzasi **qurilmaydi** |
| Ikonka | `ExternalLink` | Affordans matn bilan **juftlangan** |
| Matn | «Dalilni ochish» | ⛔ **«Kadrni ko'rish» EMAS** — bu sahifada kadr **ko'rinmaydi** |
| `target="_blank"` | ⛔ **YO'Q** | Yangi ilova nusxasi auth holatini qayta tiklaydi va foydalanuvchini login ekraniga tashlashi mumkin |
| ⛔ `<img>` | ⛔ **`components/reconciliation/**` da 0 ta** | **G7-3**. `next/image`, `background-image`, `useEvidenceImageHref` importi ham **yo'q** |

⛔ **Huquqsiz ko'ruvchida NIMA BO'LADI** [QAROR]: dalil kadri marshruti `EVIDENCE_FRAME_PERMISSIONS` = «`CAMERA_VIEW` **yoki** `OCCUPANCY_REVIEW`» ostida [KOD: `review-queries.ts:225-232`]. Havola **shartli chiziladi**:

| Holat | Xulq | Sabab |
|-------|------|-------|
| Huquq **bor** | Havola chiziladi | — |
| Huquq **yo'q** | ⛔ **Element UMUMAN chizilmaydi** (o'chirilgan tugma **emas**, tooltip **emas**) | RBAC UI ko'zgusining mavjud qoidasi [KOD: `rbac.ts` fayl boshi]. O'chirilgan tugma **mavjud imkoniyatni** e'lon qilardi — 06-UI-SPEC §11.4 (`no_coverage_stall` uchun affordans **umuman chizilmaydi**) bilan bir naqsh |
| `snapshot_id === null` | ⛔ **Chizilmaydi** | 05-14 darsi: marshrut bermagan qator **chizilmaydi**, placeholder ham qo'yilmaydi |

⚠⚠ **OCHIQ CHEGARA — bu shox bugun ERISHIB BO'LMAYDI** [M-6; 07-RESEARCH Pitfall 10 sinfi]: bugungi matritsada `report_view` egalarining **ikkalasida ham `camera_view` bor**. Ya'ni «huquqsiz ko'ruvchi» shoxi **real sessiyada erishib bo'lmaydi**. Shuning uchun: (a) u **kelajakka mo'ljallangan qo'riqchi**; (b) testi **sun'iy `roles` massivi** bilan yoziladi va **shu sabab test faylida izoh sifatida yoziladi** — aks holda keyingi ijrochi uni «foydasiz test» deb o'chirardi.

### 8.5 Hisobot qatori ↔ case: ikki tomonlama, YOZUV YUZASI 0

| Holat | Qatorda | Amal |
|-------|---------|------|
| Case **ochilgan** | `case-status-badge` | `[Ko'rib chiqish]` → DL-5 |
| Case **ochilmagan** | ⛔ `Badge tone="muted"` «Navbatga olinmagan» | ⛔ **Amal YO'Q** |

⛔ **`[Case ochish]` TUGMASI QURILMAYDI** [QAROR]: case'lar `recon.open` cron'ida **avtomatik** va sinf A uchun **`overdue_days` chegarasi** bilan tug'iladi (Pattern 5). Qo'lda ochish: (1) **chegarani aylanib o'tardi** — direktor bugungi hisobga case ochib, ertaga to'lov kelganda uni **yopishga majbur** bo'lardi (shovqin — `alerting.py` D-22 bo'limidagi aynan nosozlik); (2) ⛔ **idempotentlikni buzardi** — qisman UNIQUE indeks (DQ-5) qo'lda va cron urinishlari orasida **poyga** yaratardi; (3) direktorning haqiqiy ehtiyoji — «**buni tezroq ko'ring**», ya'ni **mas'ul biriktirish** (DL-5 da bor), yangi case emas.

⚠ **Ochiq narx:** chegaradan **oldingi** to'lovsiz hisob uchun case **yo'q**; direktor uni faqat `unpaid` ro'yxatida ko'radi. Bu **ataylab**: navbat **hal qilinishi kerak** bo'lganlar uchun, **kutish mumkin** bo'lganlar uchun emas.

---

## 9. Y-2: Case navbati, tafsiloti va aniqlik ulushi (RECON-02)

### 9.1 Nima uchun bu yuza «case» so'zini ISHLATMAYDI [QAROR — M-8]

`transliterate("Case yopildi")` → ⛔ **`Cасе ёпилди`** — lotin `C`/`e` kirill `асе` bilan **aralashgan**. Bu 05-UI-SPEC M-5 va G-26(c) dagi **akronim defekti** sinfi va «lotin qoldi» detektori uni ushlaydi → **`i18n:check` qizaradi**.

| Kod / DB | ⛔ Ekranda | Nega |
|----------|-----------|------|
| `reconciliation_cases`, «case» | ⛔ **«Nomuvofiqlik»** | Transliteratsiya defekti (M-8) **va** «case» mahalliy foydalanuvchi uchun begona. Kod `reconciliation_cases` da **qoladi** [MEROS: 06-UI-SPEC §13.1] |
| `ReconciliationCaseStatus` | ⛔ **«Holat»** | — |
| «hit-rate» | ⛔ **«Aniqlik ulushi»** | Lotin defis-so'z transliteratsiyada buzilardi; ⛔ va **«AI aniqligi» bilan ADASHTIRMASLIK** uchun matnda **«nomuvofiqlik»** so'zi bilan birga keladi (§9.5) |
| `assignee` | ⛔ **«Mas'ul»** | O'lchandi: `Масъул` ✓ |
| `resolution` | ⛔ **«Yechim»** | O'lchandi: `Ечим` ✓ |

### 9.2 Case navbati — `case-list.tsx`

**Envelope** (DQ-4, `ChargeListResponse` naqshi bilan **bir xil shaklda**):

```
{ day, rows, next_cursor,
  new_count, in_review_count, justified_count, unjustified_count }
```

⛔ **To'rt sanoq envelope'da keladi** — hit-rate (§9.5) ularning **hosilasi** va **ikkinchi so'rov qilmaydi**, ya'ni «ekranda ikki xil raqam» sinfi **tug'ilmaydi**.

| Ustun | Manba | Uslub |
|-------|-------|-------|
| Subyekt | `subject_kind` → yorliq + rasta/zona | Body + ikonka |
| Sotuvchi | ⛔ `vendor_id` → klientda join | Body |
| Holat | `case-status-badge` | Badge |
| Mas'ul | ⛔ `assignee_user_id` → klientda join; `null` → «Biriktirilmagan» (`text-text-muted`) | Body |
| Ochilgan | `created_at` | Body |
| — | `[Ko'rib chiqish]` → DL-5 | `ghost` |

**Holat nishoni — 4 a'zo, 3 kanal** (rang **hech qachon yagona signal emas**, WCAG 1.4.1):

| Kod | uz-Latn | `tone` | Ikonka |
|-----|---------|--------|--------|
| `new` | **Yangi** | `accent` | `Inbox` |
| `in_review` | **Ko'rilmoqda** | `warning` | `Timer` |
| `justified` | **Asosli** | ⛔ **`danger`** | `CircleCheckBig` |
| `unjustified` | **Asossiz** | `muted` | `CircleSlash` |

⛔ **Nega `justified` = `danger`, `success` EMAS** [QAROR]: «asosli» degani — **nomuvofiqlik ROST chiqdi**, ya'ni bozor **pul yo'qotgan**. `success` uni «yaxshi natija» qilib ko'rsatardi va direktor ro'yxatni **teskari** o'qirdi. `unjustified` esa `muted` — «hech narsa bo'lmagan», e'tibor talab qilmaydi. ⛔ Bu 06-UI-SPEC §12.4 dagi «Kamomad ↔ Ortiqcha» qoidasining aynan sinfi: bir xil «hal qilingan» holati, **qarama-qarshi ma'no**.

**Sahifalash:** keyset kursor (DQ-4), sahifa **50** [MEROS: `market-queries.ts:97`]. ⛔ `offset` **ishlatilmaydi** — navbat kun davomida o'sadi va offset **takroriy/tushib qolgan** qatorlar berardi.

### 9.3 DL-5 — tafsilot va holat o'zgarishi

| # | Bo'lim | Mazmun | Huquq |
|---|--------|--------|-------|
| 1 | **Subyekt** | Sinf yorlig'i + rasta/zona + sana + summa (A) yoki vaqt (B) | `report_view` |
| 2 | ⛔ **Dalil** | `evidence-link.tsx` — **havola** (§8.4) | `camera_view` \|\| `occupancy_review` |
| 3 | **Holat** | native `<select>` — ⛔ **4 a'zo** | `dispute_decide` |
| 4 | **Mas'ul** | native `<select>` — bozor foydalanuvchilari | `dispute_decide` |
| 5 | **Yechim** | `<textarea>` — ⛔ **erkin matn** | `dispute_decide` |
| 6 | ⛔ **Audit izi** | O'zgarmas ro'yxat: aktor · eski→yangi holat · vaqt | `report_view` |
| — | `[Holatni saqlash]` | ⛔ `variant="default"` — **fazadagi yagona aksent tugma** (§13.3) | `dispute_decide` |

⛔ **`dispute_decide` yo'q bo'lganda: 3, 4, 5-bo'lim va tugma UMUMAN CHIZILMAYDI** (o'chirilgan emas). Bozor admini DL-5 ni **o'qish** uchun ochadi va u **hisobot** bo'lib ko'rinadi.

⛔⛔ **`<textarea>` — bu TAQIQNING ISTISNOSI va sabab yozilishi SHART** [QAROR]:

06-UI-SPEC **G-24(c)** DL-1 da `<textarea>` ni taqiqlaydi va sabab aniq edi: sabab-kod **yopiq to'plam** bo'lishi kerak, erkin matn **guruhlanmaydi**. Bu yerda vaziyat **boshqa**:

1. ⛔ **Guruhlash allaqachon YOPIQ TO'PLAMDA** — `status` 4 a'zoli va hit-rate **undan** hisoblanadi (D-13). Erkin matn **hech qanday metrikani buzmaydi**;
2. **D-14 buni ochiq ajratadi:** *«Yechim matni erkin, lekin holat yopiq ro'yxat — ikkisi aralashmaydi»*;
3. ⛔ **Nizoda (D-02) hukmning SABABI kerak** — «asossiz» degan bir so'z sotuvchiga tushuntirib bo'lmaydi.

⛔ **G-24 ning qamrovi `components/collect/**` — bu yerda U QO'LLANMAYDI** va `components/reconciliation/**` uchun `<textarea>` taqig'i **yozilmaydi**. Bu ochiq yozilishi shart, aks holda ijrochi «taqiq global» deb o'ylab yechim maydonini **`<select>` ga aylantirardi**.

### 9.4 Yozuv qoidalari

| Qoida | Xulq | Sabab |
|-------|------|-------|
| ⛔ Terminal holatga (`justified`/`unjustified`) o'tishda **yechim MAJBURIY** | Bo'sh → `[Holatni saqlash]` **`aria-disabled`** (⛔ `disabled` **emas** — 06-UI-SPEC §14.3) | Sababsiz hukm nizoda **himoyasiz**. Va bu erkin matnning «amalda bo'sh qoladi» nosozligini **aynan shu joyda** yopadi |
| `new` → `in_review` da yechim **shart emas** | Tugma faol | «Ko'rmoqdaman» — hukm emas |
| ⛔ **Holat orqaga qaytishi RUXSAT** (`justified` → `in_review`) | Ruxsat | Xato hukm **tuzatilishi** kerak va u **audit qatori** bilan ko'rinadi (D-14). Bloklash direktorni yangi case **ochishga** majburlardi |
| ⛔ **Audit izi TAHRIRLANMAYDI** | `[Tahrirlash]`/`[O'chirish]` **umuman yozilmaydi** | D-14, append-only |
| Dublikat yuborish | ⛔ `useRef` qulfi — naqsh `blind-session.tsx:92-137` dan **o'zgarishsiz** | Ikki bosish **ikki audit qatori** yozardi va tarix **yolg'on** ko'rinardi |
| Poyga (boshqa direktor allaqachon o'zgartirgan) | `case_status_conflict` → sabab+tuzatish (§14.9) | ⛔ **Jimgina ustiga yozilmaydi** — kim qachon nima qilgani D-14 ning butun mazmuni |

### 9.5 ⛔⛔ Aniqlik ulushi — MAXRAJSIZ FOIZ YOLG'ON [QAROR — D-13 ning UI shakli]

**Formula:** `justified / (justified + unjustified)`. ⛔ `new` va `in_review` maxrajga **kirmaydi**.

⛔ **Kontrakt: foiz KO'RINSA, to'rt sanoq ham SHU BLOKDA ko'rinadi.**

```
┌─ Aniqlik ulushi ─────────────────────────────────┐
│  68 %                          ← Display+font-mono│
│  Hal qilingan 25 ta nomuvofiqlikdan 17 tasi       │
│  asosli chiqdi.                          ← Body   │
│  Hali hal qilinmagan 8 ta (yangi, ko'rilmoqda)    │
│  hisobga olinmagan.                      ← Meta   │
└───────────────────────────────────────────────────┘
```

| Element | Majburiymi | Sabab |
|---------|-----------|-------|
| Foiz | Faqat maxraj > 0 | ⬇ |
| ⛔ **Maxraj jumlasi** («Hal qilingan **25** tadan **17** tasi») | ⛔ **HA** | Maxrajsiz 68% ni direktor «100 tadan 68 tasi» deb o'qiydi. **Ko'rinmaydigan yolg'on** — 5-fazadagi soxta aniqlik raqami sinfi |
| ⛔ **Istisno jumlasi** («Hali hal qilinmagan **8** ta … hisobga olinmagan») | ⛔ **HA** | D-13 istisnosi ekranda ko'rinmasa, u **yashirin qoida** bo'lardi. `aria-describedby` bilan foizga bog'lanadi |
| `Target` ikonkasi | Ixtiyoriy | — |

⛔⛔ **`justified + unjustified === 0` BO'LGANDA foiz UMUMAN CHIZILMAYDI:**

| Ekranda | ⛔ Ekranda BO'LMAYDI |
|---------|---------------------|
| «Hali hal qilingan nomuvofiqlik yo'q» (Body) | ⛔ **`0 %`** |
| «Navbatda {n} ta nomuvofiqlik ko'rib chiqilmoqda.» | ⛔ `—%`, `n/a`, `∞`, `NaN` |

**Sabab** [QAROR]: `0/0` — **aniqlanmagan**, «nol foiz» **emas**. `0 %` «biz tekshirdik va hech biri asosli chiqmadi» degan **teskari xulosani** beradi — 06-UI-SPEC §9.4 «yo'q summa — **yo'q summa**» qoidasining aynan o'zi.

⛔ **Hit-rate SAQLANMAYDI** (D-13): klientda ham `hit_rate` nomli o'zgaruvchi/maydon **yo'q** — u to'rt sanoqdan **render paytida** hisoblanadi. **G-36** bu nomni taqiqlaydi.

⚠ **Kun kesimidagi ma'no:** `?day=` bo'yicha ulush **o'sha kunning** case'lari uchun; namuna **kichik** (~10 case/kun) va 68% **uch case'dan** chiqishi mumkin. Maxraj jumlasi **majburiy** — u namunaning kichikligini **o'zi ko'rsatadi**. ⛔ Haftalik/oylik trend — **8-faza**.

---

## 10. Y-3: Bosh ekran ko'rsatkichi (RECON-06)

### 10.1 Marshrut va javob

`GET /me/headline` → ⛔ **`{ metric: string, value: number }`** — aynan **ikki maydon** (Pattern 8).

| Maydon | Ma'nosi |
|--------|---------|
| `metric` | ⛔ **i18n KALITI** (`headline.revenue_today` \| `headline.review_queue` \| `headline.receipts_written`). Matn **serverdan qaytmaydi** [MEROS: `alerting.py:1003-1008`] |
| `value` | ⛔ **Yagona son**. Pulmi/sanoqmi — `HEADLINE_UNIT` hal qiladi (§10.3) |

⛔ Klient sxemasi **`z.strictObject({metric, value})`** — server `secondary_value`/`label` qo'shsa klient **darhol qizaradi** (G-33(b)).

### 10.2 ⛔⛔ Komponent IKKINCHI SONNI KO'RSATA OLMAYDI [QAROR]

```
type HeadlineCardProps = { metric: HeadlineMetric; value: number };
//  ⛔ ikkinchi son uchun PROP YO'Q — ikkinchi son *taqiqlanmaydi*, IMKONSIZ
```

⛔⛔ **Va undan kuchlisi: komponent ROLNI UMUMAN O'QIMAYDI.**

| Taqiq | Nega |
|-------|------|
| ⛔ `useAuthStore()` / `principal.roles` — **import ham qilinmaydi** | D-28: «qaysi son qaysi rolga» ni **server** hal qiladi. Klient rolni o'qisa, ertaga kimdir `if (isCashier) …` yozardi va **uchinchi haqiqat** tug'ilardi |
| ⛔ `hasPermission(...)` | O'sha |
| ⛔ `"cashier"`/`"director"`/`"platform_admin"` **satrlari** | **G-33(c)** token skani |

Bu 06-UI-SPEC §9.2 «`tariff_id` klientga umuman yuborilmaydi» naqshining aynan o'zi: taqiqni **imkonsizlikka** aylantirish.

**Ko'rinishi:**

```
┌──────────────────────────────────────┐
│  47                     ← Display, font-mono
│  Bugun yozilgan kvitansiyalar  ← Body, text-text-muted
└──────────────────────────────────────┘
```

| Xossa | Qiymat |
|-------|--------|
| Konteyner | `Card` + `data-headline` |
| Son | Display (24px/600) + `font-mono` |
| Yorliq | Body (14px/400) + `text-text-muted` |
| ⛔ Ikonka | ⛔ **YO'Q** — ikonka «bu qanday son» ni aytishga urinardi va **rolga bog'liq shart** tug'ilardi |
| ⛔ Trend / o'q / «kechagiga nisbatan» | ⛔ **YO'Q** — bu **ikkinchi son** (D-29) |
| ⛔ Havola / `[Batafsil]` | ⛔ **YO'Q** — §10.5 |
| Yuklanish | `Skeleton` (⛔ `0` **emas** — nol soxta javob bo'lardi) |
| Xato | ⛔ **Karta umuman chizilmaydi** (`null`) |

⛔ **Xatoda karta CHIZILMAYDI** [QAROR]: bosh ekranda «ko'rsatkichni yuklab bo'lmadi» qizil bloki — foydalanuvchi **hech narsa qila olmaydigan** shovqin. Marshrut qayta urinadi; ko'rsatkich **yo'q bo'lsa — yo'q**, sahifaning qolgani ishlayveradi.

### 10.3 ⛔⛔ Kassirniki — SUMMA EMAS, SANOQ [QAROR — Pitfall 1]

**To'qnashuv o'lchangan.** 6-faza kassir ko'rligini **uch mustaqil qatlamda** qurgan:

| Qatlam | Joyi | Nima qiladi |
|--------|------|-------------|
| 1 | `payment_repo.py:145` — `RECENT_PAYMENT_WINDOW = 5` | Kassir 5 dan ortiq to'lovini ko'rmaydi → qo'shib chiqara olmaydi (T-06-53) |
| 2 | `ShiftCloseResponse` da `system_*` **e'lon qilinmagan** | T-06-59 |
| 3 | `variance_soum` faqat `REPORT_VIEW` ostida (`shifts.py:126`) | 06-UI-SPEC §10.4 |

⛔ **Bosh ekranga SUMMA chiqarish uchalasini ham BIR QATORDA bekor qiladi** — kassir uni o'qib, smena yopishda **aynan shu sonni** deklaratsiya qiladi va variance **har doim nol** bo'ladi. CASH-04 ning butun qiymati yo'qoladi.

**Yechim — reyestr, shart emas:**

| `metric` | Kim (huquq) | Qiymat | `HEADLINE_UNIT` |
|----------|-------------|--------|------------------|
| `headline.revenue_today` | `REPORT_VIEW` | Bugungi tushum (so'm) | `"soum"` |
| `headline.review_queue` | `OCCUPANCY_REVIEW` | Ko'rib chiqish navbati (dona) | `"count"` |
| ⛔ `headline.receipts_written` | `PAYMENT_CREATE` | ⛔ **Kvitansiyalar SONI** (`COUNT(*)`, bugun, o'sha kassir) | ⛔ **`"count"`** |

⛔ `HEADLINE_UNIT` — `lib/headline-queries.ts` da, yopiq **3 a'zoli** `Record`. `"soum"` → `t("headline.amountUnit")`; `"count"` → ⛔ **birlik QO'SHILMAYDI** [MEROS: `pending-summary.tsx:177` — «Rasta SONI — pul emas, shuning uchun `amountUnit` YO'Q»].

⛔ **G-33(d) ikki tomonlama:** (a) reyestr kalitlari to'plami = **3 a'zo** (to'plam tengligi); (b) ⛔ `HEADLINE_UNIT["headline.receipts_written"] === "count"`; (c) javob sxemasida `_soum` bilan tugaydigan maydon **yo'q**.

⚠ **Nima uchun talab BUZILMAYDI:** RECON-06 «o'ziga mos bitta asosiy raqam» deydi (ROADMAP SC#3), «yig'im summasi» demaydi. «Bugun 47 ta patta yozdim» — kassir uchun **haqiqiy va foydali** ko'rsatkich va D-29 ga to'liq mos.

### 10.4 Joylashuvi

| Qoida | Sabab |
|-------|-------|
| ⛔ `<HeadlineCard />` sarlavha + rol yorliqlaridan **keyin**, `SECTIONS` dan **oldin** | Bosh ekranning birinchi mazmunli elementi — u shu ekranning **javobi** |
| ⛔ **Boshlang'ich sahifa redirekti QO'SHILMAYDI** | 06-UI-SPEC O-05: redirekt login oqimini o'zgartirardi. ⛔ Buning o'rniga `SECTIONS` **kassirga `/collect` havolasini birinchi element** qilib beradi (O-05 tetigi aynan shu) |
| Mavjud izoh **yangilanadi, o'chirilmaydi** | `dashboard/page.tsx:12-19` — «bu yerda birorta SOXTA raqam yo'q». Headline — **birinchi haqiqiy raqam** |

### 10.5 ⛔ Headline QILMAYDIGAN narsalar

Ikkinchi son / trend / foiz / o'q (D-29) · `[Batafsil]` havolasi (har rol uchun **boshqa** nishon kerak bo'lardi → komponent **rolni o'qishga** majbur bo'lardi) · avtomatik yangilanish taymeri (jimgina o'zgaradigan raqam — «men boshqa raqam ko'rgandim» nizosi) · bir necha rolli foydalanuvchiga **ikki karta** (server `HEADLINE_ORDER` bo'yicha **birinchi mos huquqni** tanlaydi) · ko'rsatkichni tanlash/sozlash (V2).

---

## 11. Y-4: Xabar yetkazilishi (BOT-04)

### 11.1 Nima uchun direktor ko'radigan yuzada [MEROS: 07-CONTEXT `<specifics>`]

> *«"Xabar kelmadi" nizosi uchun yetkazilganlik holati **direktor ko'radigan yuzada** bo'lishi kerak, faqat jadvalda emas — aks holda BOT-04 ning amaliy qiymati nolga tushadi.»*

Shuning uchun `delivery` — `/reconciliation` bloki (§8.1 F) va u ⛔ **`day = bugun` da ham chiziladi** (§4.4).

### 11.2 ⛔⛔ Beshta holat — matn ISBOTLANGANDAN ORTIQ DA'VO QILMAYDI

**Pitfall 2 o'lchagan:** Bot API `sendMessage` javobi — `Message` obyekti (`message_id`, `date`). ⛔ **Yetkazilganlik yoki o'qilganlik kvitansiyasi YO'Q** [CITED: core.telegram.org/bots/api#sendmessage].

| Kod | uz-Latn | uz-Cyrl | ru | `tone` | Ikonka | Ma'nosi (⛔ aynan shu) |
|-----|---------|---------|-----|--------|--------|------------------------|
| `pending` | **Navbatda** | Навбатда | В очереди | `muted` | `Clock` | Qator yozilgan, urinish qilinmagan |
| `sent` | **Yuborilmoqda** | Юборилмоқда | Отправляется | `neutral` | `Send` | Ijara olingan, HTTP so'rov yo'lda |
| `delivered` | ⛔ **Telegram qabul qildi** | ⛔ **Telegram қабул қилди** | ⛔ **Telegram принял** | `success` | ⛔ **`Check`** | Telegram **200** qaytardi va `message_id` berdi |
| `failed` | **Yuborilmadi** | Юборилмади | Не отправлено | `danger` | `TriangleAlert` | Urinishlar tugadi yoki qayta urinib bo'lmaydigan xato |
| `blocked` | ⛔ **Aloqa uzilgan** | ⛔ **Алоқа узилган** | ⛔ **Связь потеряна** | ⛔ **`neutral`** | ⛔ **`Link2Off`** | `403` — sotuvchi botni bloklagan (D-22) |

[M-9] «Telegram» kirillda **saqlanadi** — `words.Telegram = "Telegram"` overrayди bor va u `snapshots.alertNotified` da **allaqachon ishlaydi**.

⛔⛔ **`delivered` MATNI — uchta taqiq:**

| ⛔ Taqiqlangan | Nega |
|----------------|------|
| «**Yetkazildi**» / «Доставлено» **yolg'iz** | Bu **qabul qiluvchi** haqidagi da'vo. Telegram uni tasdiqlamaydi → D-02 nizosida tizim **isbotlab bo'lmaydigan** narsani da'vo qilardi |
| «**O'qildi**»/«Ko'rildi»/«Прочитано» | Undan kuchliroq da'vo. ⛔ **G-34(b)** bu leksikani **uchala locale'da** taqiqlaydi |
| ⛔ **`CheckCheck` ikonkasi** | ⛔ **Ikki belgi — messenjerlarning universal «O'QILDI» glifi.** Matn rost gapirib turib **ikonka yolg'on gapirardi**, va ikonka kanali WCAG 1.4.1 bo'yicha matn bilan **teng og'irlikda** o'qiladi. ⛔ **`Check` (bitta)** ishlatiladi; **G-34(c)** `CheckCheck` tokenini `components/reconciliation/**` da **0** ga qulflaydi |

⛔⛔ **`blocked` — MA'LUMOT, XATO EMAS (D-22):**

| Qoida | Sabab |
|-------|-------|
| ⛔ `tone="neutral"`, **`danger` EMAS** | Bloklash — sotuvchining **huquqi**, bozorning nosozligi emas. Qizil rang direktorni «tizim buzildi» deb o'ylashga majburlardi |
| ⛔ `role="alert"` **YO'Q** | O'sha |
| ⛔ To'liq jumla **majburiy**: «Sotuvchi botni bloklagan — unga xabar bormaydi.» | Yolg'iz «Aloqa uzilgan» nishoni **texnik nosozlik** deb o'qilardi |
| ⛔ Keyingi qadam **matnda**: «Sotuvchi bilan bevosita bog'laning.» | D-22: bu **qarz undirish jarayonining bir qismi** |
| ⛔ **Amal tugmasi YO'Q** | Ilova ichida qiladigan ish **yo'q**; tugma mavjud bo'lmagan imkoniyatni va'da qilardi (06-UI-SPEC §9.3 kanal 6) |

### 11.3 `delivery-list.tsx` — jadval

| Ustun | Manba | Uslub |
|-------|-------|-------|
| Vaqt | `created_at` → `useFormatter().dateTime()` | Body. ⛔ **Nisbiy vaqt YO'Q** (§3.5) |
| Xabar turi | `kind` → yopiq to'plam yorlig'i (§14.6) | Body + ikonka |
| Sotuvchi | ⛔ `vendor_id` → klientda join (§5.5) | Body |
| Holat | `delivery-badge.tsx` | Badge |
| Urinishlar | `attempt_count`/`max_attempts` (`2/5`) | Meta, ⛔ `font-mono` **emas** |

⛔⛔ **JADVALDA BO'LMAYDIGAN USTUNLAR:**

| Yo'q ustun | Nega | Darvoza |
|------------|------|---------|
| ⛔ `chat_id`, `telegram_user_id`, `telegram_username` | §5.5 — tashqi tizimdagi shaxs identifikatori; C-10 uni ushlamaydi, **G-36** ushlaydi | **G-36** |
| ⛔ **Xato MATNI** (`last_error` xom holda) | **D-04**: Telegram istisnosining matni **bot tokenini tashiydi** (token URL'ning qismi). Faqat **TURI** ko'rsatiladi va u §14.9 kalitiga xaritalanadi | **G-36** |
| ⛔ Xabar **tanasi** | Kvitansiya matnida summa va rasta bor; takrorlash ⛔ **ikkinchi pul yuzasi** bo'lardi va u yig'indiga olib borardi | **G-36** |
| ⛔ `[Qayta yuborish]` | §17.2 | **G-34(d)** |

**Xato turi** (`failed` qatorida, Meta, `text-text-muted`): §14.9 dagi yopiq to'plamdan. ⛔ **Xom istisno matni HECH QACHON**.

### 11.4 Jonli yangilanish — `day = bugun`

| Qoida | Qiymat | Sabab |
|-------|--------|-------|
| Kesh | ⛔ `staleTime: 0`, `gcTime: 0` | §5.4 |
| Avtomatik so'rov | ⛔ **YO'Q** (`refetchInterval` **yozilmaydi**) | Ochiq qoldirilgan sahifa har 5 soniyada so'rov yuborardi; va §10.5 «jimgina o'zgaradigan raqam» taqig'i bilan bir sinf |
| Qo'lda yangilash | ✅ `[Yangilash]` — `secondary` + `RotateCcw` | Direktor **o'zi** so'raydi va o'zgarishni **kutadi** |
| `role="status"` | ✅ Yangilangandan keyin qatorlar soni e'lon qilinadi | Skrinrider foydalanuvchisi o'zgarishni **eshitadi** |

⚠ `day < bugun` da `[Yangilash]` **chizilmaydi** — o'tgan kunning yetkazilganligi **o'zgarmas**.

---

## 12. RECON-03: ikki raqamning matn kontrakti

### 12.1 ⛔⛔ Farq — NUQSON EMAS, DIZAYN

| Vaqt | Job | Manba | ⛔ Matnda MAJBURIY sifatlovchi |
|------|-----|-------|-------------------------------|
| **20:45** | `notify.digest_evening` | `pending_projection(as_of=business_today())` | ⛔ **«kutilayotgan»** |
| **08:00** | `notify.digest_morning` | `daily_charges` + `payments` (kechagi, **yozilgan**) | ⛔ **«yozilgan»** |

Mexanik sabab: `BILLING_CLOSE_CRON = "10 4 * * *"` [KOD: `worker.py:445`] — D kunining hisobi **D+1 04:10** da tug'iladi; kechqurun `daily_charges` da bugungi kun **hali yo'q**.

⛔ Sifatlovchisiz: direktor kechqurun 4 200 000, ertalab 3 950 000 ko'radi, sababini **topa olmaydi** va uchinchi kuni ikkalasini ham **o'qimay qo'yadi**.

### 12.2 Sifatlovchi kontrakti

| Kalit | uz-Latn | uz-Cyrl | ru |
|-------|---------|---------|-----|
| `recon.qualifier.expected` | ⛔ **kutilayotgan** | ⛔ **кутилаётган** | ⛔ **ожидаемый** |
| `recon.qualifier.recorded` | ⛔ **yozilgan** | ⛔ **ёзилган** | ⛔ **записанный** |

⛔ **Qoida: sifatlovchi RAQAM BILAN BIR JUMLADA turadi**, alohida sarlavhada emas.

| ✅ To'g'ri | ⛔ Noto'g'ri |
|-----------|-------------|
| «Bugun **kutilayotgan** patta: 4 200 000 so'm» | «Kechki hisobot ⏎ Patta: 4 200 000 so'm» |
| «Kecha **yozilgan** patta: 3 950 000 so'm» | «Dayjest (kutilayotgan) ⏎ 4 200 000 so'm» |

**Sabab:** sarlavhadagi sifatlovchi Telegram bildirishnomasining **qisqartirilgan ko'rinishida** kesilib qoladi va foydalanuvchi faqat raqamni ko'radi.

⛔ **Ikkalasi bir xabarda uchrashsa** (bu fazada **yo'q**), har biri **o'z raqami bilan** turadi va farq **uchinchi jumla** bilan aytiladi: «Farq — kechki hisob **proyeksiya**, ertalabkisi **yozilgan hisob**.»

### 12.3 O'lchov — **G-35**

Yopiq lug'at ustida **to'plam tengligi** (⛔ `not.toContain` **emas** — D-31):

```
QUALIFIER_VOCAB = {expected, recorded}
EXPECTED = { "recon.digest.evening": {"expected"},
             "recon.digest.morning": {"recorded"} }
har (kalit × 3 locale):
  found = { q ∈ VOCAB : matn q ning shu locale'dagi so'zini o'z ichiga oladi }
  assert deepEqual(found, EXPECTED[kalit])     // ⛔ AYNAN bittasi
```

⛔ **Nega to'plam tengligi:** oddiy «kutilayotgan bormi?» tekshiruvi kechki xabarga **«yozilgan»** ham qo'shilganda **yashil qolardi** — va aynan o'sha aralashuv direktorni chalkashtiradi.

### 12.4 Veb yuzasida

⛔ `/reconciliation` da proyeksiya bloki **yo'q** (§4.4) — bu sahifada faqat **yozilgan** ma'lumot bor va sifatlovchi **kerak emas**. Proyeksiya `/billing?day=bugun` da yashaydi va G-25 ikkalasini **bir ekranda uchrashtirmaydi**. ⛔ Ya'ni sifatlovchi kontrakti **faqat xabar matnida** qo'llanadi — shuning uchun u §14 copy kontraktining bir qismi, komponent kontrakti emas.

---

## 13. Rang kontrakti (60/30/10)

### 13.1 Taqsimot — o'zgarishsiz, yangi token YO'Q

| Rol | Token | Qiymat [KOD: `globals.css:33-85`] | 7-fazada qayerda |
|-----|-------|-----------------------------------|------------------|
| **Dominant (60%)** | `--color-bg` | `oklch(0.985 0 0)` | Sahifa foni |
| **Ikkilamchi (30%)** | `--color-surface` | `oklch(1 0 0)` | Oltala blok, DL-5, headline kartasi |
| | `--color-surface-muted` | `oklch(0.968 0 0)` | `Skeleton`, `tone="muted"` nishonlar |
| **Aksent (10%)** | `--color-accent` | `oklch(0.56 0.19 255)` | §13.3 — **to'rt element** |
| **Destruktiv** | `--color-danger` | `oklch(0.58 0.21 27)` | Qarz raqami, «Asosli», «Yuborilmadi» |
| **Ogohlantirish** | `--color-warning` | `oklch(0.78 0.15 85)` | ⛔ Faqat `bg-warning/20` sifatida — §13.2 |
| **Muvaffaqiyat** | `--color-success` | `oklch(0.63 0.16 150)` | ⛔ **Faqat bitta joy**: «Telegram qabul qildi» |

**Yangi token kiritilmaydi va yangi rang juftligi so'ralmaydi.**

### 13.2 `--color-warning` matn sifatida ISHLATILMAYDI

Sariq tintdagi matn — `bg-warning/20 text-text` (o'lchangan **15,64:1**) [KOD: `badge.tsx:17-25`]. `--color-warning` oq fonda **2,03:1** — falokat. 7-fazada bu **ikki joyda**: «Ro'yxatga olinmagan savdo» badge'i (§8.2) va «Ko'rilmoqda» holati (§9.2).

### 13.3 ⛔ Aksent — to'rtta element, beshinchisi yo'q [QAROR]

1. **Fokus halqasi** (`:focus-visible outline`) — barcha interaktiv elementlar;
2. **Faol maydon chegarasi va halqasi** (`focus-visible:border-accent`, `ring-accent/25`);
3. **Joriy navigatsiya elementi** — faqat mobil pastki panelda;
4. ⛔ **`[Holatni saqlash]` — DL-5 dagi yagona yakunlovchi amal.** Fazadagi **yagona** aksent fonli tugma (`variant="default"`).

> ⛔ **Nega `[Holatni saqlash]` aksent oladi**: u **tanlov emas, oqibat** — holat va yechim allaqachon tanlangan, tugma faqat **yozadi**. Raqobatchisi yo'q, ya'ni urg'u **hech narsani buzmaydi**. Bu 06-UI-SPEC §12.3 dagi `[To'lovni tasdiqlash]` mulohazasining aynan o'zi.
>
> ⛔ **`new/in_review/justified/unjustified` `<select>` esa AKSENT OLMAYDI** — u **tanlov** va 5-fazaning ankorlash mulohazasi to'liq kuchda: birortasini urg'ulash hukmga **ta'sir qilardi**.

⛔ **Aksent ishlatilMAYDIGAN joylar:** `[Ko'rib chiqish]` · `[Dalilni ochish]` · `[Yangilash]` · kun tanlagichi · jadval sarlavhalari · har qanday summa/foiz raqami · ⛔ **headline soni** · yetkazilganlik nishonlari · sinf badge'lari.

⛔ **`[Ko'rib chiqish]` — `ghost`, `default` EMAS** [QAROR]: case ro'yxatida u **har qatorda** takrorlanadi; `default` bo'lsa sahifada 10–50 ta aksent tugma paydo bo'lardi va 10% chegarasi **buzilardi**. **G-36** buni o'lchaydi: `components/reconciliation/**` da `variant="default"` **aynan 1 marta**.

### 13.4 Rang hech qachon YAGONA signal emas (WCAG 1.4.1)

| Holat | Rang kanali | Kanal 2 | Kanal 3 |
|-------|-------------|---------|---------|
| **Band, lekin to'lovsiz** | `tone="danger"` | `Receipt` | Badge matni «To'lovsiz» |
| **Ro'yxatga olinmagan savdo** | `tone="warning"` | `UserX` | Badge matni — **to'liq, qisqartirilmagan** |
| **Yangi** (case) | `tone="accent"` | `Inbox` | Badge matni |
| **Ko'rilmoqda** | `tone="warning"` | `Timer` | Badge matni |
| ⛔ **Asosli** | `tone="danger"` | `CircleCheckBig` | Badge matni |
| ⛔ **Asossiz** | `tone="muted"` | `CircleSlash` | Badge matni |
| **Navbatga olinmagan** | `tone="muted"` | — | Badge matni |
| **Navbatda** (xabar) | `tone="muted"` | `Clock` | Badge matni |
| **Yuborilmoqda** | `tone="neutral"` | `Send` | Badge matni |
| ⛔ **Telegram qabul qildi** | `tone="success"` | ⛔ **`Check`** (bitta!) | ⛔ **To'liq jumla** — «Telegram qabul qildi» |
| **Yuborilmadi** | `tone="danger"` | `TriangleAlert` | Badge matni + xato **turi** |
| ⛔ **Aloqa uzilgan** | ⛔ `tone="neutral"` | `Link2Off` | ⛔ **To'liq jumla** «Sotuvchi botni bloklagan — unga xabar bormaydi» |
| **Aniqlik ulushi yo'q (0/0)** | — (rang **yo'q**) | — | ⛔ **Nomlangan sabab** (§9.5) |

> ⛔ **«Asosli» va «Asossiz» turli `tone` oladi va bu MUZOKARASIZ.** Ikkalasi ham «hal qilingan», lekin **ma'nosi qarama-qarshi**: biri — bozor **pul yo'qotgan**, ikkinchisi — **hech narsa bo'lmagan**. Bir xil ko'rinsa, hit-rate ning butun mazmuni yo'qolardi.

---

## 14. Matn (copywriting) kontrakti

### 14.1 ⛔ Atama qarorlari — kod bir narsa deydi, ekran boshqa narsa

| Kod / DB | ⛔ Ekranda | Nega |
|----------|-----------|------|
| `reconciliation_cases`, «case» | ⛔ **«Nomuvofiqlik»** | [M-8] `Case` → `Cасе` **aralash alifbo**; va «case» mahalliy foydalanuvchi uchun begona |
| `new`/`in_review`/`justified`/`unjustified` | **Yangi / Ko'rilmoqda / Asosli / Asossiz** | DQ-6: qiymatlar inglizcha, **ekran matni i18n kaliti** |
| «hit-rate» | ⛔ **«Aniqlik ulushi»** | Lotin defis-so'z; ⛔ **AI aniqligi bilan adashtirmaslik** uchun matnda «nomuvofiqlik» so'zi bilan birga |
| `outbox`, `notification_outbox` | ⛔ **«Xabar yetkazilishi»** | «Outbox» — mexanizm nomi; foydalanuvchiga **natija** kerak |
| `delivered` | ⛔ **«Telegram qabul qildi»** | §11.2 — «Yetkazildi» isbotlanmagan da'vo |
| `blocked` | ⛔ **«Aloqa uzilgan»** | D-22 — «Bloklandi» xato bo'lib o'qilardi |
| `attempt_count` | **«Urinishlar»** | — |
| `assignee` | **«Mas'ul»** | — |
| `resolution` | **«Yechim»** | — |
| `unassigned_occupied` | **«Ro'yxatga olinmagan savdo»** | 06-UI-SPEC §11.4 dan **o'zgarishsiz** — ikki fazada ikki xil yorliq bo'lmasin |

### 14.2 Namespace'lar va navigatsiya

| Namespace | Egasi |
|-----------|-------|
| `recon.*` | Y-1, Y-2, Y-4 — nomuvofiqlik yuzasi |
| `recon.caseStatus.*` | §9.2 (G-31) |
| `recon.deliveryState.*` | §11.2 (G-34) |
| `recon.qualifier.*` | §12.2 (G-35) |
| `recon.errorCause.*` / `recon.errorFix.*` | §14.9 |
| `headline.*` | Y-3 — ⛔ **3 metrik kaliti + `amountUnit`** |
| `bot.*` (bot-service Babel katalogi) | Y-5 — §14.6 |

| Kalit | uz-Latn | uz-Cyrl | ru |
|-------|---------|---------|-----|
| `nav.reconciliation` | **Nomuvofiqliklar** | Номувофиқликлар | Расхождения |

### 14.3 Y-1/Y-2/Y-4 — shipping matn (uz-Latn; qolgan ikkitasi §14.4 bo'yicha)

| Kalit | uz-Latn |
|-------|---------|
| `recon.title` | Nomuvofiqliklar |
| `recon.unpaidTitle` | Band, lekin to'lovsiz |
| `recon.unpaidHint` | Kecha hisob yozilgan, lekin to'lov to'liq kelmagan rastalar. |
| `recon.unregisteredTitle` | Ro'yxatga olinmagan savdo |
| `recon.unregisteredHint` | Kamera band deb ko'rsatgan, lekin hech qaysi rastaga biriktirilmagan zonalar. |
| `recon.evidenceOpen` | Dalilni ochish |
| `recon.casesTitle` | Nomuvofiqlik navbati |
| `recon.caseReview` | Ko'rib chiqish |
| `recon.caseUnqueued` | Navbatga olinmagan |
| `recon.assigneeNone` | Biriktirilmagan |
| `recon.hitRateTitle` | Aniqlik ulushi |
| `recon.hitRateBody` | Hal qilingan {resolved} ta nomuvofiqlikdan {justified} tasi asosli chiqdi. |
| `recon.hitRateExcluded` | Hali hal qilinmagan {pending} ta (yangi, ko'rilmoqda) hisobga olinmagan. |
| `recon.hitRateNone` | Hali hal qilingan nomuvofiqlik yo'q |
| `recon.hitRateNoneHint` | Navbatda {pending} ta nomuvofiqlik ko'rib chiqilmoqda. |
| `recon.deliveryTitle` | Xabar yetkazilishi |
| `recon.deliveryRefresh` | Yangilash |
| `recon.deliveryAttempts` | Urinishlar |
| `recon.blockedBody` | Sotuvchi botni bloklagan — unga xabar bormaydi. |
| `recon.blockedFix` | Sotuvchi bilan bevosita bog'laning. |
| `recon.caseStatusLabel` | Holat |
| `recon.assigneeLabel` | Mas'ul |
| `recon.resolutionLabel` | Yechim |
| `recon.resolutionHint` | Qaroringiz sababini yozing — u nizoda dalil bo'ladi. |
| `recon.save` | Holatni saqlash |
| `recon.auditTrailTitle` | Holat o'zgarishlari |
| `headline.revenue_today` | Bugungi tushum |
| `headline.review_queue` | Ko'rib chiqish navbati |
| `headline.receipts_written` | Bugun yozilgan kvitansiyalar |
| `headline.amountUnit` | so'm |

⛔ **`recon.hitRateBody` da `{resolved}` va `{justified}` — ICU platsholderlari**, ya'ni maxraj **matndan ajralmaydi** va G-32 uni DOM'da topa oladi.

### 14.4 Uch til va transliteratsiya kontrakti

| Fayl | Kim yozadi |
|------|-----------|
| `messages/uz-Latn.json` | Qo'lda |
| `messages/ru.json` | Qo'lda |
| `messages/uz-Cyrl.json` | ⛔ **`npm --prefix frontend run i18n:gen`** — qo'lda tahrirlanmaydi |
| `messages/uz-Cyrl.overrides.json` | ⛔ **Tegilishi KUTILMAYDI** [M-8] |

[M-8] 26 nomzod satrdan **25 tasi mexanik defektsiz** o'tdi; yagona defekt (`Case`) **copy'ga kirmaydi** (§9.1). [M-9] `Telegram` overrayди **allaqachon bor**.

⚠ Agar qo'lda tuzatish zarurati chiqsa, u `uz-Cyrl.overrides.json` ning `words` bo'limiga **so'z** sifatida yoziladi (o'zbek **agglyutinativ** — har qo'shimchali shakl **alohida yozuv**), `uz-Cyrl.json` ga **emas**.

### 14.5 ⛔ Glossariy — D-30 ning yagona o'lchanadigan ta'rifi (G7-9)

`ops/i18n/glossary.json` — ⛔ **qiymatlar O'ZAK**, to'liq so'z emas (o'zbek agglyutinativ, rus tili **flektiv**):

```json
{
  "patta": { "uz-Latn": "patta", "uz-Cyrl": "патта", "ru": "патт" },
  "rasta": { "uz-Latn": "rasta", "uz-Cyrl": "раста", "ru": "мест" },
  "qarz":  { "uz-Latn": "qarz",  "uz-Cyrl": "қарз",  "ru": "долг" },
  "smena": { "uz-Latn": "smena", "uz-Cyrl": "смена", "ru": "смен" }
}
```

[M-10] Bugungi uchrash soni: `patta` **25/25/17** · `rasta` **99/99/101** · `qarz` **6/6/6** · `smena` **16/16/22** → ⛔ **G7-9(a) bugundan yashil**.

⛔ **Taqiqlangan sinonimlar (band c) — PER-LOCALE va TOKEN-ANIQ:**

| Locale | Taqiqlangan | Bugun |
|--------|-------------|-------|
| uz-Latn | `yig'im`, `do'kon` | **0**, **0** |
| uz-Cyrl | `йиғим`, `дўкон` | **0**, **0** |
| ru | `лавк`, `магазин` | **0**, **0** |

⛔⛔ **`сбор` TAQIQ RO'YXATIGA KIRMAYDI — va sabab ochiq yozilishi SHART** [QAROR — M-11]:

ru'da `сбор` **13 kalitda** va **ikki xil ma'noda**: `nav.collect` = «Сбор» (**amal**, «Yig'ish») **va** `ежедневный сбор` = «kunlik patta» (**levy**, 8 kalit — `categories.emptyStateHint`, `stalls.noTariffHint`, `tariffs.emptyStateHint`, `calendar.*`, `wizard.weekdaysHint`). Uni taqiqlash 1–6-fazaning **13 kalitini** qizartirardi va tuzatish **copy migratsiyasi** bo'lardi — 7-faza qamrovidan tashqarida. ⚠ Bu **haqiqiy terminologik siljish** va uning tetigi §18 O-03 da yozilgan; egasi — **8-fazaning uch tilli yakuniy tekshiruvi**.

⛔ **`yig'im` va `yig'ish` FARQLANADI:** `nav.collect` = «Yig'ish» (**amal**) — **qonuniy**; `yig'im` (**levy** ma'nosidagi ot) — **taqiqlangan**. Darvoza tokeni aynan `yig'im` bo'lishi shart, `yig'` **emas** — aks holda u `nav.collect` ni birinchi kunidayoq qizartirardi.

### 14.6 Y-5 — bot va xabar matni (⛔ veb emas, lekin copy kontraktida)

⛔ **Barchasi MATN.** Kadr — **hech qachon** (D-03). Dalil — **havola**: `{base}/{locale}/reconciliation?day=YYYY-MM-DD` yoki `{base}/{locale}/billing?day=…`.

| Kalit | uz-Latn | Qoida |
|-------|---------|-------|
| `bot.receipt` | To'lov qabul qilindi. Rasta {stall}, {amount} so'm, kassir {cashier}, {time}. | ⛔ **CASH-05.** Hech qachon to'xtatilmaydi (D-18) |
| `bot.reminder` | Rasta {stall} bo'yicha {days} kundan beri {amount} so'm qarz turibdi. | ⛔ BOT-03; quiet hours ga **bo'ysunadi** |
| `bot.summary` | Rasta {stall}: qarz {amount} so'm. | ⛔ **BOT-02.** «balans» so'zi **yo'q** (D-06) |
| `bot.digest.evening` | Bugun **kutilayotgan** patta: {amount} so'm. Nomuvofiqliklar: {link} | ⛔ §12.2 sifatlovchi |
| `bot.digest.morning` | Kecha **yozilgan** patta: {amount} so'm. Bandlik: {rate}. Nomuvofiqliklar: {link} | ⛔ §12.2 sifatlovchi |
| `bot.binding.neutral` | Bog'lanib bo'lmadi. Bozor ma'muriyatiga murojaat qiling. | ⛔ **D-26(a)** — «bu raqam ro'yxatda yo'q» **DEMAYDI**: u reyestrni tashqaridan tekshirish yo'li bo'lardi |
| `bot.binding.ok` | Ulandingiz. Endi qarzingiz va to'lovlaringizni shu yerda ko'rasiz. | BOT-01 |
| `bot.binding.rebound` | Yangi Telegram akkaunti ulandi. Eski ulanish bekor qilindi. | D-26(c) |
| `bot.shareContact` | Raqamni ulashish | ⛔ **D-24** — `request_contact=True` tugmasi; ⛔ qo'lda terish **taklif qilinmaydi** |

⛔ **`bot.binding.neutral` uchala shoxda (mos kelmadi / bir nechta moslik / noto'g'ri contact) AYNAN BIR XIL** — farqli matn reyestrni tashqaridan **probe qilish** yo'lini ochardi (D-26(a) ning butun mazmuni).

⛔ **Atamalar veb bilan YAGONA** (D-30): «qarz», «patta», «rasta», «smena» — §14.5 glossariysi ikkala manbani ham o'lchaydi (G7-9).

### 14.7 Toastlar (3) va bo'sh holatlar (5)

**Toastlar:** «Holat saqlandi» (success) · «Mas'ul biriktirildi» (success) · xato (error — sabab+tuzatish, §14.9).

**Bo'sh holatlar (`EmptyState`):**

| # | Blok | Sarlavha | Tavsif |
|---|------|----------|--------|
| 1 | `unpaid` | To'lanmagan hisob yo'q | {date} kuni yozilgan har bir hisob to'liq to'langan. |
| 2 | `unregistered` | Ro'yxatga olinmagan savdo yo'q | {date} kuni har band zona rastaga biriktirilgan. |
| 3 | `cases` | Nomuvofiqlik navbati bo'sh | {date} kuni ko'rib chiqiladigan nomuvofiqlik topilmadi. |
| 4 | `hitrate` | ⛔ `EmptyState` **EMAS** — inline nomlangan sabab | §9.5 |
| 5 | `delivery` | Bu kuni xabar yuborilmagan | To'lov yoki eslatma bo'lmasa, xabar ham bo'lmaydi. |

⛔ Bo'sh holatda `action` **yo'q** — bu ekranlarda foydalanuvchi qiladigan «keyingi qadam» **yo'q** (kutish — qadam emas).

### 14.8 ⛔ Destruktiv amal — YO'Q

Bu fazada **birorta** qaytarib bo'lmaydigan amal **yo'q**: holat o'zgarishi **append-only** (D-14) va **orqaga qaytariladi** (§9.4); case **o'chirilmaydi**; xabar **bekor qilinmaydi**. Shuning uchun:

- ⛔ `ConfirmDialog` **ishlatilmaydi**;
- ⛔ `variant="destructive"` **ishlatilmaydi** — **G-36** buni `components/reconciliation/**` da **0** ga qulflaydi;
- «Destruktiv tasdiq» copy'si **yozilmaydi**.

⚠ Bu **ataylab yozilgan yo'qlik**: keyingi ijrochi «case'ni yopish» uchun destruktiv tasdiq qo'shishga urinsa, darvoza **qizaradi** va u shu bo'limni o'qiydi.

### 14.9 Xato kontrakti — SABAB + NIMA QILISH KERAK (G-17 davomi)

| Kod | `errorCause` (uz-Latn) | `errorFix` (uz-Latn) |
|-----|------------------------|----------------------|
| `case_not_found` | Bu nomuvofiqlik topilmadi. | Ro'yxatni yangilang — u boshqa kunga tegishli bo'lishi mumkin. |
| `case_status_conflict` | Holatni boshqa foydalanuvchi allaqachon o'zgartirgan. | Yangilang va o'zgarishlar tarixini ko'ring. |
| `case_resolution_required` | Yakuniy holat uchun yechim matni kerak. | Qaroringiz sababini yozing. |
| `case_forbidden` | Bu amalga ruxsatingiz yo'q. | Direktorga murojaat qiling. |

**Yetkazilmaslik TURLARI** (⛔ xom istisno matni **hech qachon** — D-04):

| Kod | uz-Latn |
|-----|---------|
| `telegram_unreachable` | Telegram javob bermadi |
| `chat_not_found` | Chat topilmadi |
| `rate_limited` | Chegara oshdi |
| `unknown` | Noma'lum xato |

---

## 15. Qulaylik (a11y)

| Talab | Shakl |
|-------|-------|
| Fokus halqasi | `:focus-visible` aksent outline — barcha interaktiv elementlar |
| `fieldset`/`legend` | DL-5 dagi holat+mas'ul guruhi |
| ⛔ `aria-disabled`, `disabled` **emas** | `[Holatni saqlash]` [MEROS: 05-UI-SPEC §13.3] |
| `aria-describedby` | ⛔ Hit-rate foizi → maxraj jumlasi **va** istisno jumlasi (§9.5) |
| Jonli hududlar | `role="status"`: toast, `[Yangilash]` dan keyingi qatorlar soni · ⛔ `role="alert"`: **faqat** xato (⛔ `blocked` **emas** — §11.2) |
| Rang yolg'iz signal **emas** | §13.4 — 13 holat, har birida ≥2 qo'shimcha kanal |
| Jadval semantikasi | native `<table>` + `<caption class="sr-only">` |
| ⛔ Global bir-tugmali yorliqlar | ⛔ **YO'Q** [MEROS: 06-UI-SPEC §14.4] |
| Barmoq nishoni | ≥44px (`size="lg"` yoki `min-h-11`) |

---

## 16. Darvozalar

### 16.1 ⛔ Raqamlash — UCH ketma-ketlik bor va bu ochiq yozilishi SHART

| Ketma-ketlik | Diapazon | Uyi |
|--------------|----------|-----|
| **Frontend darvozalari** | `G-1`…**`G-28` band** → yangilari **`G-29` dan** | `frontend/scripts/*.test.mjs`, `*.test.tsx` |
| **Backend/faza darvozalari** | `G-1`…`G-16` band | `tests/**` (06-VALIDATION.md) |
| ⛔ **7-fazaning taqiq darvozalari** | ⛔ **`G7-1`…`G7-9` band** | 07-RESEARCH § Validation Architecture:1287-1310 |

**Qoidalar:**

1. ⛔ Bu hujjatning **yangi** darvozalari **`G-29` dan** boshlanadi (frontend ketma-ketligi 6-fazada `G-28` da tugagan).
2. ⛔ **`G7-3` va `G7-9` — 07-RESEARCH egaligida qoladi**; bu hujjat ularning **frontend yarmini aniqlashtiradi** (§16.3, §16.4), **yangi ID bermaydi**. Bu 06-UI-SPEC ning `G-7` bilan qilgan ishining aynan takrori.
3. ⛔ Kod izohlarida ID **ketma-ketligi bilan**: `G-29 (07-UI-SPEC)`, `G7-3 (07-RESEARCH)`. Yalang'och `G-3` **yozilmaydi** (u 04-UI-SPEC niki).

### 16.2 Har darvozaning ikki muzokarasiz xossasi [MEROS: 06-UI-SPEC §15.2]

| Xossa | Ma'nosi |
|-------|---------|
| ⛔ **HOSILA qamrov** (D-32) | Darvoza katalogni **o'qiydi**, reyestrdan **iteratsiya qiladi**. Qo'lda yozilgan ro'yxat **yo'q** |
| ⛔ **TO'PLAM TENGLIGI** (D-31) | `deepEqual`/`Set`. ⛔ `not.toContain(...)` **ishlatilmaydi** |

Har darvozada **quyi chegara** (`MIN_*`): skanerlanadigan fayl soni kamaysa darvoza **qizaradi** — bo'sh to'plamda «taqiqlangan token topilmadi» **jimgina rost** bo'ladi.

### 16.3 ⛔⛔ G7-3 ning frontend shakli (07-RESEARCH egaligida — YANGI ID YO'Q)

**Fayl:** `frontend/scripts/reconciliation-copy.test.mjs`

| # | Nima o'lchanadi |
|---|-----------------|
| (a) | `components/reconciliation/**` **`readdirSync` bilan rekursiv** o'qiladi (mahsulot fayllari; `*.test.tsx` chiqariladi), izohlar `stripComments()` bilan olib tashlanadi |
| (b) | ⛔ `<img`, `next/image`, `Image from "next/image"`, `background-image`, `backgroundImage`, `useEvidenceImageHref`, `URL.createObjectURL` tokenlari — **har biri 0** |
| (c) | ⛔ `/snapshots/` satri — **0** (dalil havolasi `/billing?day=` ga boradi, §8.4) |
| (d) | ⛔ **Quyi chegara:** katalog mavjud **va** ≥6 mahsulot fayli |
| (e) | `evidence-link.tsx` da `href` **`/billing`** bilan boshlanadi (regeks) |

**Nima uchun mavjud:** D-03 ning frontend jufti; 04-UI-SPEC G-3 ni **kengaytiradi**, yumshatmaydi. (c) eng qimmati: kadr marshrutiga **hech qanday** murojaat bo'lmasa, `SNAPSHOT_EVIDENCE_FRAME_ROUTES` **tegilmagan** qoladi (06-UI-SPEC M-8).

### 16.4 ⛔ G7-9 ning frontend yarmi (07-RESEARCH egaligida — YANGI ID YO'Q)

**Fayl:** `frontend/scripts/glossary.test.mjs`

| # | Nima o'lchanadi |
|---|-----------------|
| (a) | `ops/i18n/glossary.json` dan **iteratsiya qilib**, har atama × har locale uchun **flatten qilingan** `messages/<locale>.json` qiymatlarida o'zak ≥1 marta |
| (b) | ⛔ Taqiqlangan sinonimlar (§14.5, **per-locale**) — **har birida 0** |
| (c) | ⛔ **Quyi chegara:** glossariyda ≥4 atama **va** har atamada aynan 3 locale kaliti |
| (d) | ⛔ `сбор` taqiq ro'yxatida **yo'q** — reyestrning **to'plam tengligi** bilan (⛔ ro'yxat testda **qayta yoziladi**, `glossary.json` dan import qilinmaydi) |

Bot yarmi (`.po` `msgstr` skani) — `bot-tests` konteynerida, 07-RESEARCH G7-9 bo'yicha.

### 16.5 ⛔ Ommaviy amal taqig'i — MAVJUD darvozaga QO'SHILADI, yangi ID olmaydi

`components/reconciliation/**` ham ommaviy-amal skanidan o'tishi **shart**: «Hammasini asossiz deb belgilash» yoki ko'p-tanlovli case ro'yxati direktorga **bir bosishda 50 nomuvofiqlikni yopish** imkonini berardi — bu «hammasini tasdiqlash» dan **qimmatroq** xato, chunki natijasi **hukm** va u hit-rate ni **buzadi**.

| Qadam | Ish |
|-------|-----|
| 1 | `05-UI-SPEC.md` §15 dagi ommaviy-amal qatoriga **to'rtinchi** naqsh qo'shiladi: `` `components/reconciliation/**` `` |
| 2 | ⛔ **Aynan birinchi `components/reconciliation/*.tsx` mahsulot fayli bilan bitta commitda** — `bulk-action-surface.test.mjs:293-308` e'lon qilingan **har** katalogning mavjud va **bo'sh emasligini** tekshiradi |
| 3 | Skan **o'zi** kengayadi: `MIN_SCANNED_FILES = 5` ham, `checkbox`/`Array.isArray` tokenlari ham **o'zgarmaydi** |

⛔ **BU HUJJAT O'SHA DARVOZA UCHUN JADVAL QATORI YOZMAYDI** [M-4]: `bulk-action-surface.test.mjs:112-125` e'lon qilgan UI-SPEC soni **aynan 1** bo'lishini talab qiladi; ikkinchi e'lon `npm run gate` ni **butunlay** qizartirardi.

### 16.6 Yangi darvozalar

| # | Darvoza | Fayl | Mexanik ravishda NIMANI o'qiydi | Nima uchun mavjud |
|---|---------|------|----------------------------------|-------------------|
| **G-29** | ⛔⛔ **Blok to'plami va MAZMUN JUFTLIGI** | `reconciliation/page.test.tsx` | **(a)** `?day=bugun` → `[data-recon-block]` qiymatlari to'plami **`{"day","delivery"}` ga TENG**; `?day=kecha` → **`{"day","unpaid","unregistered","cases","hitrate","delivery"}` ga TENG**; kesishma **`{"day","delivery"}`**. **(b)** ⛔ **Mazmun juftligi:** ro'yxat komponentining **O'ZI** `data-recon-content="<blok>"` chiqaradi; da'vo (a) dan **aylanib HOSILA**; `Set([data-recon-content]) === Set(blocks) \ CONTENT_EXEMPT`; `CONTENT_EXEMPT = new Set(["day"])` va ⛔ `CONTENT_EXEMPT.size === 1` **alohida assert**; ⛔ `grep -c "data-recon-content" reconciliation/page.tsx` → **0**. **(c)** ⛔ **Haqiqiy mazmun mock'dan HOSILA:** `unpaid` → `items[0].stall_code` **va** `querySelectorAll("tbody tr").length === items.length`; `cases` → `items[0]` holat yorlig'i; `delivery` → `items[0]` holat yorlig'i; ⛔ `items: []` bergan blok **o'z bo'sh-holat matnini** ko'rsatishi shart. ⛔ **SABOTAJ (majburiy):** `<UnpaidList/>` → `<div data-recon-block="unpaid"/>` — (a) **yashil qolishi kutiladi**, (b) **va** (c) ⛔ **QIZARISHI SHART** | ⛔ **§4.4 ning strukturaviy shakli** + 06-UI-SPEC G-25 ning **o'lchangan ko'rligidan** olingan dars: faqat atribut to'plamini tekshiradigan darvoza ⛔ **bo'sh o'ramni MUKAMMAL o'tkazardi** va butun yuza **chizilmagan** holda faza yashil qaytardi (S-D sinfi) |
| **G-30** | ⛔⛔ **Ikki sinf hech qachon QO'SHILMAYDI** | `reconciliation/unpaid-list.test.tsx` + `scripts/reconciliation-copy.test.mjs` | **(a)** `components/reconciliation/**` va `lib/reconciliation-queries.ts` da reyestrdagi **birorta** nom yo'q: `total_anomalies`, `totalAnomalies`, `combined_total`, `combinedTotal`, `total_discrepancies`, `totalDiscrepancies`, `grand_total`, `grandTotal`, `all_total`, `overall_total` — ⛔ **quyi chegara: ≥10 nom**. **(b)** ⛔ DOM: `unpaid` va `unregistered` **bloklaridan tashqarida** ikkala blokning sonini birlashtirgan element **yo'q** — `[data-recon-block]` tashqarisidagi raqamli tugunlar to'plami **`day` va `hitrate` bilan cheklangan** (to'plam tengligi). **(c)** copy: `messages/*.json` `recon.*` da «jami nomuvofiqlik»/«jami yo'qotish» va ru/cy juftlari **0** | ⛔ **Pattern 4 + §8.2.** A **hosila**, B **qator** — bitta songa qo'shish ikki xil umr ko'radigan narsani teng qilardi va B da summa **umuman yo'q** bo'lgani uchun yig'indi **kam ko'rsatilgan yo'qotish** bo'lardi |
| **G-31** | **Case holatining yopiqligi × 3 locale** | `scripts/reconciliation-copy.test.mjs` + `case-detail-dialog.test.tsx` | **(a)** `lib/api-types.ts::CASE_STATUSES` dan **iteratsiya qilib** `recon.caseStatus.*` kalitlari **uchala locale'da** — ⛔ **to'plam tengligi**; **(b)** reyestr **aynan 4 a'zo** va `other`/`custom`/`unknown` **yo'q**; **(c)** DOM: DL-5 dagi `<select>` ning `<option>` **qiymatlari to'plami** reyestrga **TENG** (⛔ `placeholder` `value=""` dan tashqari); **(d)** DL-5 da holat uchun `type="text"` maydon **yo'q** | **D-12.** (b) eng muhimi: `other` erkin matnni qaytarib keltirardi **va hit-rate maxrajini aniqlanmagan qilardi** — `justified/(justified+unjustified)` da beshinchi a'zo qayerga tushishi **hech qayerda yozilmagan** bo'lardi |
| **G-32** | ⛔⛔ **Maxrajsiz foiz — YOLG'ON** | `reconciliation/hit-rate-card.test.tsx` | **(a)** `{justified:17, unjustified:8, new:5, in_review:3}` bilan render → DOM'da **`68`** (yoki locale foizi) **va** `17`, `25`, `8` — **to'rttasi ham**; **(b)** ⛔ `{justified:0, unjustified:0, new:4, in_review:2}` → foiz belgisi (`%`/`％`) DOM'da **0 marta** **va** `recon.hitRateNone` matni **bor**; **(c)** `0`, `NaN`, `Infinity`, `—%` satrlari **yo'q**; **(d)** foiz elementining `aria-describedby` i maxraj jumlasi **va** istisno jumlasi id'lariga ishora qiladi; **(e)** ⛔ `hit_rate`/`hitRate` **maydon nomi** sifatida kodda **yo'q** (D-13 — saqlanmaydi) | ⛔ **D-13 ning UI shakli.** Maxrajsiz 68% ni direktor «100 tadan 68 tasi» deb o'qiydi — **ko'rinmaydigan yolg'on**, 5-fazadagi soxta aniqlik raqami sinfi. (b) `0/0` — **aniqlanmagan**, «nol foiz» emas |
| **G-33** | ⛔⛔ **Bitta son, va kassirniki SUMMA EMAS** | `headline/headline-card.test.tsx` | **(a)** ⛔ `[data-headline]` ichida **raqam tutuvchi matn tugunlari soni AYNAN 1** (`/\d/` bilan, `textContent` bo'yicha, `Skeleton` chiqarilgan); **(b)** `headlineResponseSchema` — `z.strictObject`, kalitlar to'plami **`{metric, value}` ga TENG**; `parse({...toza, secondary_value:1})` **throw**; **(c)** ⛔ `components/headline/**` da `useAuthStore`, `principal`, `roles`, `hasPermission`, `"cashier"`, `"director"`, `"market_admin"`, `"platform_admin"`, `"inspector"` tokenlari — **har biri 0** (⛔ quyi chegara: ≥9 token); **(d)** ⛔ `HEADLINE_UNIT` kalitlari to'plami **3 a'zo** va `HEADLINE_UNIT["headline.receipts_written"] === "count"`; **(e)** javob sxemasida `_soum` bilan tugaydigan maydon **yo'q**; **(f)** `"count"` metrikada `headline.amountUnit` matni DOM'da **0 marta** | ⛔ **D-29 + Pitfall 1.** (c) taqiqni **imkonsizlikka** aylantiradi: komponent rolni **o'qiy olmaydi**, ya'ni `if (isCashier)` yozib bo'lmaydi. (d)+(e) CASH-04 ning **uch qatlamli ko'rligini** (T-06-53/59, `shifts.py:126`) bosh ekrandan himoya qiladi — summa chiqsa variance **har doim nol** bo'lardi |
| **G-34** | ⛔⛔ **Yetkazilganlik ISBOTLANGANDAN ORTIQ da'vo qilmaydi** | `reconciliation/delivery-list.test.tsx` + `scripts/reconciliation-copy.test.mjs` | **(a)** `DELIVERY_STATES` dan **iteratsiya qilib** `recon.deliveryState.*` **uchala locale'da** — **to'plam tengligi**, reyestr **aynan 5 a'zo**; **(b)** ⛔ `recon.*` qiymatlarida «o'qildi», «ko'rildi», «ўқилди», «кўрилди», «прочитан», «просмотр» **va** yolg'iz «yetkazildi»/«етказилди»/«доставлен» — **har biri 0** (⛔ quyi chegara: ≥9 token); **(c)** ⛔ `components/reconciliation/**` da `CheckCheck` tokeni **0**; `delivered` qatorida `Check` **bor**; **(d)** ⛔ `blocked` qatorida `tone="danger"` **yo'q**, `role="alert"` **yo'q**, va blok ichidagi interaktiv elementlar to'plami **`{"Ko'rib chiqish","Dalilni ochish","Yangilash"}` bilan cheklangan** (ya'ni `[Qayta yuborish]`, `[Bloklashni yechish]` **yo'q**); **(e)** `chat_id`/`telegram_user_id`/`telegram_username` DOM'da **0** | ⛔ **Pitfall 2 + D-22.** Bot API **yetkazilganlik kvitansiyasi bermaydi**; ortiqcha da'vo D-02 nizo modelini **teskarisiga** aylantirardi. (c) muzokarasiz: `CheckCheck` — messenjerlarning **«o'qildi» glifi**, ya'ni matn rost gapirib turib **ikonka yolg'on gapirardi**. (d) `blocked` **ma'lumot**, xato emas |
| **G-35** | ⛔ **Ikki xabar — ikki sifatlovchi** | `scripts/reconciliation-copy.test.mjs` | Yopiq lug'at `{expected, recorded}` ustida, har (kalit × locale) uchun: topilgan sifatlovchilar to'plami **`{expected}`** (kechki) yoki **`{recorded}`** (ertalabki) ga ⛔ **TENG** — ya'ni ikkinchisining **yo'qligi** ham o'lchanadi; ⛔ har ikki matnda ICU raqam platsholderи **bor** (sifatlovchi raqam bilan **bir jumlada**) | ⛔ **RECON-03 + Pattern 3.** Oddiy «kutilayotgan bormi?» tekshiruvi kechki xabarga «yozilgan» **ham** qo'shilganda **yashil qolardi** — va aynan o'sha aralashuv direktorni chalkashtiradi (§1.2 ssenariysi) |
| **G-36** | ⛔ **Nomuvofiqlik yuzasining taqiqlangan nomlari va aksent byudjeti** | `scripts/reconciliation-copy.test.mjs` | `components/reconciliation/**` **va** `lib/reconciliation-queries.ts` (izohlarsiz) da reyestrdagi **birorta** nom yo'q: `chat_id`, `chatId`, `telegram_user_id`, `telegramUserId`, `telegram_username`, `balance`, `balance_soum`, `hit_rate`, `hitRate`, `last_error`, `lastError`, `vendor_name`, `vendorName`, `phone`, `full_name`, `fullName` — ⛔ **quyi chegara: ≥16 nom**; **(b)** ⛔ `float(`, `Decimal`, `.toFixed(`, `parseFloat(` — **0** (D-07); **(c)** ⛔ `variant="default"` **aynan 1 marta** (§13.3); **(d)** ⛔ `variant="destructive"` **0 marta** (§14.8) | **D-04 + D-05 + D-06/D-07 + §13.3/§14.8, bittа mexanizmda.** `chat_id` taqig'i C-10 **ushlamaydigan** bo'shliqni yopadi; `last_error` taqig'i D-04 ning frontend jufti (istisno matni **tokenni tashiydi**); `hit_rate` taqig'i D-13 ni; (c) 10% aksent chegarasini **sonli** qiladi |

### 16.7 Sampling — mavjud byudjetlar [MEROS: 07-RESEARCH § Validation Architecture]

| Daraja | Buyruq | Byudjet |
|--------|--------|---------|
| Task commit | `npm run gate:fast` | **200 s** |
| Wave merge | `npm run test` + `npm run test:tenancy` + `npm run bot:test` | — |
| Faza darvozasi | `npm run gate` + `tests/integration/test_phase7_criteria.py` | **2300 s** (oxirgi o'lchov 1899 s → **401 s zaxira**) |

⚠ 07-RESEARCH bu fazaning frontend qo'shimchasini **~60 s** deb baholagan (vitest +~60 test, **1 ta** yangi SSG marshruti × 3 locale). ⛔ Byudjet **oshsa «shunchaki oshirilmaydi»** — 05-15 W0-13 protokoli (tinch xost, uch o'lchov, eng yomon × 1,20).

---

## 17. Bu fazada BO'LMAYDIGAN UI

### 17.1 Keyingi fazalarga qoldiriladigan

| Imkoniyat | Faza | 7-fazada aynan nima qilinadi | Nima QILINMAYDI |
|-----------|------|-------------------------------|------------------|
| **`.xlsx` eksporti, diagramma, oylik trend** | 8 | Sonlar matn sifatida, `<table>` da | Yuklab olish tugmasi, `recharts`, haftalik/oylik grafik |
| **Nomuvofiqlik ARXIVI va qidiruv** | 8 | ⛔ **Bitta kun** (`?day=`) | Sana oralig'i, matn qidiruvi, holat filtri (§17.3) |
| **AI aniqlik hisoboti** (`RECON-05`) | 8 | ⛔ **Hech narsa** | ⛔ «Aniqlik ulushi» — **case hit-rate**, AI aniqligi **EMAS** (§14.1) |
| **Qarzdorlik reyestri sotuvchi kesimida, TOP-10** | 8 | Qarz **hisob qatorida** (§8.3) | Sotuvchi bo'yicha guruhlangan reyestr |
| **Direktor botining BUYRUQ yuzasi** | V2/8 | Direktor — ⛔ **faqat oluvchi** (RECON-03) | Bot orqali holat o'zgartirish, hisobot so'rash |
| **Sotuvchi botidan to'lov / da'vo** | V2 | CASH-05 — ⛔ **bir tomonlama kvitansiya** | Ikki tomonlama oqim |
| **Quiet hours / `overdue_days` sozlash yuzasi** | 8 | ⛔ **Hech narsa** — bozor kesimida, `market_notification_settings` (D-19) | Sozlash formasi (wizard yoki sozlamalar sahifasi egasi) |

### 17.2 Ataylab qurilMAYDIGAN — sabab bilan

| Nima | Nima uchun |
|------|-------------|
| ⛔ **`[Xabarni qayta yuborish]`** | Uchta mustaqil sabab: (1) outbox **o'zi** qayta uradi (DQ-3 backoff); (2) ⛔ qo'lda yuborish `UNIQUE (market_id, dedupe_key)` (D-21) bilan **to'qnashardi** yoki uni aylanib o'tib **ikkinchi kvitansiya** yuborardi — 6-fazaning T-06-49 sinfi; (3) `blocked` da qayta urinish **ta'rifan** foydasiz (D-22) |
| ⛔ **`[Case ochish]` / qo'lda case yaratish** | §8.5 |
| ⛔ **Ommaviy holat o'zgartirish** («hammasini asossiz») | §16.5. Bir bosishda 50 hukm — **hit-rate ni buzadi** va hech qanday yechim matni qolmasdi |
| ⛔ **Case o'chirish / audit izini tahrirlash** | D-14, append-only. `[Tahrirlash]`/`[O'chirish]` **umuman yozilmaydi** |
| ⛔ **Headline'da ikkinchi son / trend** | D-29, §10.5 |
| ⛔ **Kassirga bugungi yig'im SUMMASI** | §10.3. `system = declared − variance` sinfidagi bir qatorli buzilish |
| ⛔ **Dalil kadri `/reconciliation` da** | §0.2, §8.4. Kadr `/billing` DL-3 da tug'iladi va u yerda qoladi |
| ⛔ **Bot xabarining tanasi yetkazilganlik jadvalida** | §11.3. Ikkinchi pul yuzasi bo'lardi |
| ⛔ **`chat_id` ekranda** | §5.5 |
| ⛔ **Xom istisno matni** (`last_error`) | D-04 — Telegram istisnosi **bot tokenini tashiydi** |
| ⛔ **Yetkazilganlikning avtomatik taymeri** | §11.4 |
| ⛔ **`ConfirmDialog` / `variant="destructive"`** | §14.8 — bu fazada destruktiv amal **yo'q** |
| ⛔ **Nomuvofiqlik ro'yxatini `/billing` ga qo'shish** | §4.3 — G-25 ning qulflangan blok to'plami |

### 17.3 Erta optimizatsiya deb baholangan «ilgaklar»

Case holat filtri `?status=` (navbat ~10 qator; filtr **hal qilinmagan muammoni yashirardi**; envelope'dagi to'rt sanoq javob beradi) · case ro'yxati virtualizatsiyasi · yetkazilganlik uchun WebSocket/SSE · holat o'zgarishida optimistik yangilash (⛔ **hukm raqamida optimizm taqiqlanadi** — 06-UI-SPEC ning pul qoidasi bilan bir sinf) · `components/reconciliation/**` uchun umumiy `<RecordTable>` abstraktsiyasi (uch iste'molchi, uch xil ustun) · dark mode · Storybook.

---

## 18. Ochiq qoldirilgan savollar — har biri uchun ishlaydigan standart bor

Bu subagent kontekstida foydalanuvchiga savol berish vositasi yo'q (`--auto`). Har biri uchun standart tanlangan; rejalashtirish javob kutib **to'xtamaydi**.

| # | Savol | Bilamiz | Noaniq | Tanlangan standart va TETIGI |
|---|-------|---------|--------|-------------------------------|
| **O-01** | Nomuvofiqlikni bozor admini yuritishi kerakmi? (`STATE.md` 7 ochiq savolidan biri — «nomuvofiqlik mas'uli») | [M-6] `dispute_decide` **mavjud** va **faqat direktorda**; `report_view` ikkalasida | Karmanada amalda kim ishlaydi | ⛔ **Hukm — direktorda (`dispute_decide`), ko'rish — ikkalasida.** Sabab: mavjud huquq nomi aynan shu ishni aytadi va `rbac` juftligi **tegilmaydi** (§5.6). **Tetigi:** dala UAT. To'g'ri tuzatish — `dispute_decide` ni `market_admin` ga **berish** (ikkala matritsada, bitta commitda), yangi huquq **emas** |
| **O-02** | Sinf A uchun `overdue_days` standarti nechchi? | Chegara **majburiy** (Pattern 5); bozor kesimida sozlanadi (D-19) | Karmana uchun ma'noli son | ⛔ **`[ASSUMED]` 3 kun**, `market_notification_settings.overdue_days` da, **kodda sabab bilan**. Sabab: 1 kun — to'lov kun davomida keladi, navbat shovqinga aylanardi; 7 kun — nomuvofiqlik **sovib** qoladi va dalil kadri retention siyosatiga yaqinlashadi. **Tetigi:** birinchi haftada navbat kuniga 30 tadan oshsa yoki 2 tadan kam bo'lsa — qiymat noto'g'ri |
| **O-03** | ru'dagi «патта» ↔ «сбор» ikkiligi tuzatilishi kerakmi? | [M-11] `сбор` **13 kalitda**, ikki ma'noda: `nav.collect` (amal) va `ежедневный сбор` (levy) | Buyurtmachi qaysi so'zni tabiiy deb biladi | ⛔ **Bu fazada TEGILMAYDI**; `сбор` taqiq ro'yxatiga **kirmaydi** (§14.5). Sabab: taqiqlash 1–6-fazaning 13 kalitini qizartirardi va tuzatish **copy migratsiyasi** bo'lardi. **Tetigi:** 8-fazaning «uch tilli interfeys yakuniy tekshiruvi» mezoni (05-UI-SPEC O-01 va 06-UI-SPEC O-07 bilan **bir yo'lda**) |
| **O-04** | Aniqlik ulushi kun kesimida ma'noli namunami? | Kuniga ~10 case (Pattern 5 chegarasi bilan); 68% uch case'dan chiqishi mumkin | Direktor uni qanday o'qiydi | ⛔ **Kun kesimi qoladi + maxraj jumlasi MAJBURIY** (§9.5) — jumla namunaning kichikligini **o'zi ko'rsatadi**. **Tetigi:** 8-fazaning arxiv/trend yuzasi haftalik ulushni beradi; agar direktor kunlik ulushni **noto'g'ri o'qisa**, tuzatish — haftalik agregat, kunlikni **o'chirish emas** |
| **O-05** | 24px (Display) headline soni uchun yetarlimi? | Display — mavjud eng katta rol; `font-mono` + 600; sahifadagi **yagona** Display | Real ko'rish sinovi yo'q | ⛔ **24px.** Beshinchi o'lcham **qo'shilmaydi** (§7.1). **Tetigi:** dala UAT; tuzatish — **hujjatlashtirilgan beshinchi rol**, `text-[32px]` **emas** (06-UI-SPEC O-04 bilan bir yo'lda) |
| **O-06** | Dalil havolasi `/billing?day=` ga borsa, direktor **qaysi qatorni** ko'rishini biladimi? | Havola kunni **beradi**; DL-3 esa hisob qatoridan ochiladi | Ko'p qatorli kunda u qatorni **qidiradi** | ⛔ **Kun darajasidagi havola qoladi.** Sabab: qator darajasidagi deep-link `?charge=` shaklidagi **yangi URL holatini** talab qilardi va u `/billing` ning G-25 blok kontraktiga **tegishi** mumkin edi (§4.3). **Tetigi:** agar dala UAT «qatorni topa olmayapman» desa, to'g'ri tuzatish — `/billing` ga **`?focus=` kabi qidiruv-qatori**, `/reconciliation` ga kadr **qo'shish emas** |

---

## 19. Dizayn tizimi xulosasi (checker uchun jamlanma)

| Xossa | Qiymat |
|-------|--------|
| **Tool** | `none` (shadcn **ishlatilmaydi** — §3.4) |
| **Preset** | not applicable |
| **Component library** | Radix primitivlari + CVA, ⛔ **mahalliy `ui/` (10 primitiv, kengaymaydi)** |
| **Icon library** | `lucide-react@1.27.0` (ISC) — [M-3] 67 nomzoddan **0 tasi yetishmaydi** |
| **Font** | `--font-sans` (system stack) + `--font-mono` (§7.3) |
| **Bo'shliq** | 4-panjara: 4 · 8 · 12 · 16 · 24 · 32 · 48 (§6.1). **Istisnolar:** 44px barmoq nishoni, 56px mobil panel, 20px karta ichki `x` — ⛔ **barchasi MEROS, yangi istisno YO'Q** |
| **Tipografiya** | ⛔ **4 rol** (24 / 18 / 14 / 12), ⛔ **2 og'irlik** (400, 600) — §7.1 |
| **Rang 60/30/10** | 60% `--color-bg` · 30% `--color-surface` (+`-muted`) · 10% `--color-accent` |
| **Aksent faqat** | fokus halqasi · faol maydon chegarasi · joriy mobil nav elementi · ⛔ **`[Holatni saqlash]` (DL-5) — fazadagi YAGONA aksent fonli tugma** |
| **Destruktiv** | `--color-danger` — ⛔ **faqat MATN/BADGE rangi sifatida**; `variant="destructive"` **0 marta** (§14.8) |
| **Yangi token** | ⛔ **YO'Q** |
| **Yangi npm paketi** | ⛔ **YO'Q** (§3.5) |
| **Primary CTA** | «Ko'rib chiqish» (sahifa) → «Holatni saqlash» (DL-5) |
| **Bo'sh holatlar** | 5 ta (§14.7) |
| **Xato holatlari** | 4 case kodi + 4 yetkazilmaslik turi, ⛔ har biri **sabab + tuzatish** (§14.9) |
| **Destruktiv tasdiq** | ⛔ **YO'Q — bu fazada destruktiv amal yo'q** (§14.8) |
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

*Phase: 07-nomuvofiqlik-bildirishnoma-va-botlar*
*UI-SPEC yakunlandi: 2026-08-11 — `gsd-ui-researcher`*
*Upstream: 07-CONTEXT.md (D-01…D-31), 07-RESEARCH.md (DQ-1…DQ-6, Pattern 1…8, Pitfall 1…10, G7-1…G7-9, § Validation Architecture), 06-UI-SPEC.md (dizayn tizimi, darvoza mexanikasi, §5.5/§8.8/§10.4), 05-UI-SPEC.md §15 (G-18 e'loni), 04-UI-SPEC.md G-3 (kadr taqig'i), ROADMAP Phase 7 (SC#1–SC#5), REQUIREMENTS.md (RECON-01/02/03/06, CASH-05, BOT-01…04), CLAUDE.md*
