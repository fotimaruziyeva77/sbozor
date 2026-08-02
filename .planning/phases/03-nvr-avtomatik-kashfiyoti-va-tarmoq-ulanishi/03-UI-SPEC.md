---
phase: 3
slug: nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi
status: draft
shadcn_initialized: false
preset: none
design_system: manual (1–2-fazadan meros, Tailwind 4 CSS-first + Radix primitivlari)
created: 2026-08-03
inherits: .planning/phases/02-bozor-domeni-va-yangi-bozor-ustasi/02-UI-SPEC.md
---

# Phase 3 — UI Design Contract

> Bitta va'daning vizual kontrakti: **admin NVR manzili + login/parolni kiritadi, bitta tugma bosadi, kameralar paydo bo'ladi.**
> UI'ning ikkinchi vazifasi — bu va'da bajarilmaganda **nega** bajarilmaganini va **nima qilish kerakligini** aytish.
> Yaratdi: `gsd-ui-researcher`. Tekshiradi: `gsd-ui-checker`. Iste'mol qiladi: `gsd-planner`, `gsd-executor`.

---

## 0. Dalil holati — taxmin va faktni ajratish

Har bir qiymat quyidagi beshta toifadan biriga tegishli. "Yaxshi ko'rinadi" asosida qo'yilgan qiymat yo'q.

| Belgi | Ma'nosi |
|-------|---------|
| **[O'LCHANDI]** | Shu sessiyada kodbazada yoki skript bilan o'lchandi — natija keltirilgan |
| **[KOD]** | Kodbazadan o'qildi — aniq `fayl:qator` keltirilgan |
| **[MEROS]** | Upstream artefaktdan olindi (03-CONTEXT, 03-RESEARCH, 02-UI-SPEC, ROADMAP, CLAUDE.md) |
| **[QAROR]** | Shu hujjatda qabul qilindi — sabab yozilgan, muqobil rad etilgan |
| **[TALAB]** | UI backend'dan talab qiladigan narsa — rejaga bevosita kiradi |

### 0.1 Bu sessiyada bajarilgan o'lchovlar

| # | O'lchov | Natija |
|---|---------|--------|
| **M-1** | **Transliterator sinovi** — 53 ta 3-faza nomzod matni `frontend/scripts/gen-cyrillic.mjs` ning `transliterate()` funksiyasidan mavjud override lug'ati bilan o'tkazildi | **3 ta jimgina buziladigan defekt sinfi** (§11.7) |
| **M-2** | **Override yetarlimi?** — o'sha matnlar 20 ta yangi override bilan qayta o'tkazildi | Yalang'och akronim **tuzaladi**; **apostrofli qo'shimchali shakl TUZALMAYDI** — copy qoidasi majburiy |
| **M-3** | **Polling naqshi bormi?** — `grep -rn "refetchInterval" frontend/src` | **0 hodisa.** Poll — bu fazada butunlay yangi naqsh; kontrakt shu hujjatda o'rnatiladi (§5.3) |
| **M-4** | **`ru` / `uz-Latn` uzunlik nisbati** — 16 ta 3-faza nomzod yorlig'i | O'rtacha **1.14×**, lekin `NVR ulash` → `Подключить видеорегистратор` = **3.00×** → ru'da ham `NVR` saqlanadi (§11.7) |
| **M-5** | **Wave 0 primitivlari mavjudmi?** — `ls frontend/src/components/ui/` | 10 ta primitiv **mavjud** (`badge, button, card, confirm-dialog, dialog, empty-state, field, input, select, skeleton`) — 2-fazaning W0-9 bandi bajarilgan, qayta qurilmaydi |
| **M-6** | **shadcn darvozasi** — `find . -maxdepth 3 -name components.json` | **0 natija** → `Tool: none` (§1.3) |
| **M-7** | **Navigatsiya sig'imi** — `NAV_ITEMS` sanog'i | Hozir **9 element** [KOD: `app-shell.tsx:86-161`]; +1 = 10. Mobil kontrakt (≤5) saqlanadi (§3.3) |
| **M-8** | **RBAC ko'zgusi** — `frontend/src/lib/rbac.ts` o'qildi | `camera_view` bor, **`camera_manage` YO'Q**; `platform_admin` da `camera_view` **YO'Q** → §13.1 W0 bandi |
| **M-9** | **Dialog imkoniyatlari** — `ui/dialog.tsx` o'qildi | `size: sm\|md\|lg` + `sheetOnMobile` **mavjud** [KOD: `dialog.tsx:27,77,79`] — jonli ko'rish uchun yangi primitiv kerak emas |
| **M-10** | **Yakuniy copy validatsiyasi** — §11 dagi **92 + 19** uz-Latn satri to'liq override to'plami bilan transliteratordan o'tkazildi | **0 ta defekt.** Har bir shipping satri o'lchandi, taxmin qilinmadi |

### 0.2 M-1, M-2 va M-10 ning xom chiqishi (dalil)

```
(1) Mavjud override lug'ati bilan — UCH DEFEKT SINFI:
  "NVR sozlamalarida NTP'ni yoqing"    -> "НВР созламаларида НТПъни ёқинг"    ❌ apostrof+akronim
  "Firmware digest/basic rejimini..."  -> "Фирмwаре дигест/басиc режимини..."  ❌ aralash yozuv
  "WireGuard tunneli faolmi"           -> "WиреГуард туннели фаолми"           ❌ brend nomi

(2) 20 ta override qo'shilgandan keyin — akronim tuzaldi, APOSTROF TUZALMADI:
  "NVR qurilmasida NTP xizmatini yoqing" -> "NVR қурилмасида NTP хизматини ёқинг"  ✅
  "NVR'ga ulanmadi"                      -> "НВРъга уланмади"                       ❌ HAMON BUZUQ
  "NVR'da NTP'ni yoqing"                 -> "НВРъда НТПъни ёқинг"                   ❌ HAMON BUZUQ

(3) Ikki qo'shimcha SEMANTIK defekt (yozuv to'g'ri, MA'NO noto'g'ri):
  "Asia/Tashkent"        -> "Асиа/Ташкент"          ❌ IANA identifikatori buzildi
  "autentifikatsiyasini" -> "аутентификатсиясини"   ❌ to'g'risi "аутентификациясини"

(4) Yakuniy to'plam bilan — 111 satr, 0 defekt:
  "Qurilma firmware sozlamasi digest autentifikatsiyasini qabul qilmayapti"
     -> "Қурилма firmware созламаси digest аутентификациясини қабул қилмаяпти"  ✅
  "Ehtimol NVR bir vaqtda ochiladigan oqimlar chegarasiga yetgan."
     -> "Эҳтимол NVR бир вақтда очиладиган оқимлар чегарасига етган."           ✅
```

(1) va (2) — 2-fazadagi `Excel'dan` defektining (T-01) **aynan takrori**: override **token**ni qidiradi, o'zakni emas. (3) — **yangi defekt sinfi**: skript tekshiruvi uni **ushlamaydi**, chunki chiqish sof kirill. Ikkalasi ham §11.7 dagi majburiy qoidalarga aylanadi.

---

## 1. Design System — meros va delta

### 1.1 Meros — o'zgarmaydi va qayta qurilmaydi

| Nima | Fayl | Holat |
|------|------|-------|
| Tailwind 4 CSS-first `@theme` bloki (2-faza tuzatishlaridan keyin) | `frontend/src/app/globals.css:12-100` | 20 rang tokeni, `--color-border-ui`, `*-text` tokenlari **mavjud** [KOD] |
| `Button` (4 variant, 3 o'lcham, `lg` = 44px) | `ui/button.tsx` | Qayta ishlatiladi |
| `Card` / `CardHeader` / `CardContent` | `ui/card.tsx` | Qayta ishlatiladi |
| `Input` (+ `aria-invalid` uslubi, `border-border-ui`) | `ui/input.tsx` | Qayta ishlatiladi |
| `Field` (label + control + error + hint, `${id}-error`/`${id}-hint` konvensiyasi) | `ui/field.tsx` | Qayta ishlatiladi |
| `Select` (native `<select>`) | `ui/select.tsx` | Filtr uchun |
| `Badge` (`neutral/muted/accent/success/warning/danger`) | `ui/badge.tsx` | Kamera holati, skan natijasi |
| `Skeleton` (`motion-reduce:animate-none`) | `ui/skeleton.tsx` | Ro'yxat yuklanishi |
| `EmptyState` (sarlavha + tavsif + amal) | `ui/empty-state.tsx` | 4 ta bo'sh holat |
| `Dialog` (`sm/md/lg` + `sheetOnMobile`) | `ui/dialog.tsx` | Jonli ko'rish, nom o'zgartirish |
| `ConfirmDialog` (1/2 daraja, `aria-disabled`, fokus destruktiv tugmada emas) | `ui/confirm-dialog.tsx` | Arxivlash |
| `sonner` Toaster (`top-center richColors`) | `app/[locale]/layout.tsx:82` | Amal tasdiqlari |
| `nuqs` URL holati | `audit-filters.tsx`, `stall-filters.tsx` | `?run=` va filtrlar |
| RBAC UI ko'zgusi (huquq yo'q → **render qilinmaydi**) | `lib/rbac.ts` + `user-list.tsx:60` | Kamera amallari |
| next-intl 3 til + `i18n:check` darvozasi | `messages/*`, `scripts/{gen-cyrillic,check-messages}.mjs` | Kalit + ICU parity |
| Domen xato kodi → tarjima kaliti moduli naqshi | `lib/market-errors.ts` | `lib/nvr-errors.ts` shu naqshda |
| `DropdownMenu` qator amallari | `user-list.tsx:215-251` | Kamera qatori |

**Kalit nomlash konvensiyasi saqlanadi** [MEROS: 02-UI-SPEC §1.1]: `namespace.camelCaseKey`; **uchinchi daraja faqat enum xaritalari uchun**. 3-faza yagona `cameras.*` namespace'ini ishlatadi + uchta enum xaritasi: `cameras.status.*`, `cameras.errorCause.*`, `cameras.errorFix.*`.

> **Nega `nvr.*` alohida namespace EMAS** [QAROR]: NVR foydalanuvchi uchun mustaqil obyekt emas — admin mental modelida bu «kameralar bo'limi»dagi bitta qurilma. Ikkita namespace bir-biriga yaqin ~90 ta kalitni ikkiga bo'lardi va tarjimonni ikki joyga qaratardi. NVR'ga xos kalitlar `cameras.nvr*` prefiksi bilan ajratiladi (`cameras.nvrAddress`, `cameras.nvrLogin`).

### 1.2 YETISHMAYDIGAN primitiv — YO'Q

2-fazaning W0-9 bandi bajarilgan [O'LCHANDI: M-5]. **Bu fazada yangi `ui/` primitivi qurilmaydi.** 3-fazaning barcha yuzalari mavjud 10 ta primitiv ustida yig'iladi.

Yagona istisno — `components/cameras/nvr-error-block.tsx` (§7). U **`ui/` primitivi emas**: uning mazmuni (sabab + tuzatish + tone + retry ruxsati) 3-faza domeniga xos va boshqa fazada qayta ishlatilmaydi. `ui/` ga ko'tarish uni ma'nosiz umumiylashtirardi.

### 1.3 shadcn darvozasi — natija

**`components.json` topilmadi** [O'LCHANDI: M-6 → 0 natija].

**Qaror: `Tool: none`. shadcn init BAJARILMAYDI.** [QAROR — 2-faza §1.3 ni davom ettiradi]

Uch sabab o'zgarmagan: (1) `shadcn init` `package.json` ga yangi paket keltiradi; (2) u Tailwind 4 rejimida `globals.css` ga **o'z token nomlarini** yozadi va 1–2-fazada o'rnatilgan `--color-bg`/`--color-surface`/`--color-accent` to'plamining yonida ikkinchi dizayn tizimi paydo bo'lardi; (3) bu subagent kontekstida interaktiv savol vositasi yo'q — darvoza hujjatlashtirilgan qaror bilan yopiladi.

**Oqibat:** `Registry Safety` darvozasi shadcn uchun **qo'llanmaydi**. Lekin bu fazada **birinchi marta uchinchi tomon kodi bundlga kiradi** (go2rtc pleyeri) — unga o'z darvozasi qo'yiladi (§14.2).

### 1.4 Yangi bog'liqlik so'rovi

**Yangi npm paketi: YO'Q.** Barcha yuzalar mavjud 18 ta bog'liqlik bilan quriladi [O'LCHANDI: `frontend/package.json`].

| Ehtiyoj | Mavjud yechim | Nega yangi paket kerak emas |
|---------|---------------|------------------------------|
| NVR formasi + validatsiya | `react-hook-form@7.83.0` + `zod@4.4.3` + `@hookform/resolvers@5.5.7` | — |
| Kashfiyot poll'i | `@tanstack/react-query@5.101.4` `refetchInterval` | Kutubxonada bor; naqsh §5.3 da o'rnatiladi |
| `run_id` URL'da | `nuqs@2.9.2` | Mavjud naqsh |
| Jonli ko'rish dialogi | `@radix-ui/react-dialog@1.1.15` + `ui/dialog.tsx` | `size="lg"` + `sheetOnMobile` mavjud [O'LCHANDI: M-9] |
| Qator amallari (mobil) | `@radix-ui/react-dropdown-menu@2.1.16` | Mavjud naqsh [KOD: `user-list.tsx:215-251`] |
| Ikonkalar | `lucide-react@1.27.0` | `Video, VideoOff, RefreshCw, Wifi, WifiOff, Archive, ArchiveRestore, Eye, EyeOff, Pencil, AlertCircle, AlertTriangle, CheckCircle2, Clock, Plus, Minus, Play` |
| Nisbiy vaqt / taymer | `date-fns@4.4.0` + `next-intl` | — |
| Toast | `sonner@2.0.7` | O'rnatilgan |

#### 1.4.1 YAGONA yangi tashqi artefakt — go2rtc pleyeri [QAROR]

| Nima | Qiymat |
|------|--------|
| Fayl | `frontend/public/vendor/go2rtc/video-stream.js` |
| Manba | `AlexxIT/go2rtc` **v1.9.14** (CLAUDE.md da qulflangan versiya), `www/video-stream.js` |
| Litsenziya | **MIT** — CLAUDE.md ning AGPL taqig'iga tegmaydi |
| Yetkazish | **Repozitoriyaga nusxalanadi** (vendored), npm'dan **emas**, go2rtc'dan runtime'da **emas** |
| Darvoza | §14.2 — SHA-256 yozib qo'yiladi + test |

**Nega runtime'da go2rtc'dan yuklanmaydi** (`<script src="/live/video-stream.js">`): D-11 go2rtc'ning HTTP yuzasini foydalanuvchiga ochishni taqiqlaydi. Statik JS uchun yo'l ochish nginx allow-list'iga **yana bitta** yozuv qo'shardi va allow-list qancha uzun bo'lsa, u shunchalik **drift qiladi** — GHSA-wwww-5h25-jf98 (CVSS 9.1) aynan shunday yuzadan kelib chiqqan. Vendored fayl bu yuzani **o'stirmaydi**: brauzer go2rtc'ga faqat imzolangan token bilan signalling uchun boradi.

**Nega o'z pleyerimiz yozilmaydi:** WebRTC → MSE → HLS avtomatik tushish mantiqi go2rtc'ning wire protokoliga qadalgan. Uni qayta yozish har go2rtc yangilanishida qayta sinovni talab qilardi va 12 haftalik MVP'da bu ishning qiymati nolga teng.

**Nega npm paketi emas:** go2rtc npm'da rasmiy paket sifatida e'lon qilinmagan. Vendored fayl kod-ko'rikdan o'tadi va git'da ko'rinadi — bu npm'dan **ko'proq** nazorat.

> Agar reja bajarilishida boshqa paket zarur bo'lib chiqsa, u **UI-SPEC ga qaytariladi** va shu bo'limga sabab + rad etilgan muqobil bilan yoziladi — jimgina `npm install` **qilinmaydi** [MEROS: 02-UI-SPEC §13].

---

## 2. Spacing / Typography / Color — meros kontrakt

> Bu bo'lim 2-faza kontraktini **takrorlamaydi va o'zgartirmaydi**. Faqat 3-fazaga tegishli qo'llanish va **bitta yangi hujjatlashtirilgan qo'llanish** yoziladi.

### 2.1 Spacing — o'zgarishsiz

| Token | Qiymat | 3-fazada qayerda |
|-------|--------|------------------|
| `xs` | 4px (`1`) | Ikonka–matn oralig'i, badge ichki `y` |
| `sm` | 8px (`2`) | Yorliq↔maydon, hisoblagichlar orasi |
| `md` | 12px (`3`) | Kamera qatorlari orasi |
| `lg` | 16px (`4`) | Karta ichki, forma maydonlari orasi |
| `xl` | 24px (`6`) | Bo'lim oralig'i (NVR kartasi ↔ kameralar ro'yxati) |
| `2xl` | 32px (`8`) | Katta bo'lim uzilishi |
| `3xl` | 48px (`12`) | Bo'sh holat `py-12` |

**Meros istisnolari saqlanadi:** 44px (`min-h-11`) barcha barmoq nishoni; 56px (`min-h-14`) mobil pastki panel; 20px (`5`) `CardHeader`/`CardContent` ichki `x`.

**Yangi istisno so'ralmaydi.** 4-panjaradan tashqari birorta qiymat kiritilmaydi. Video ramkasi **balandlik bermaydi** — u `aspect-video` (16/9) bilan kenglikdan hosil bo'ladi, ya'ni spacing tokeni emas.

### 2.2 Typography — o'zgarishsiz

| Rol | O'lcham | Og'irlik | Line-height | Tailwind |
|-----|---------|----------|-------------|----------|
| **Display** — sahifa sarlavhasi | 24px | 600 | 1.25 | `text-2xl font-semibold tracking-tight leading-tight` |
| **Heading** — karta/dialog/`<legend>` | 18px | 600 | 1.375 | `text-lg font-semibold leading-snug` |
| **Body** — barcha matn va boshqaruv elementi | 14px | 400 | 1.5 | `text-sm leading-normal` |
| **Meta** — badge, hisoblagich yorlig'i, vaqt belgisi | 12px | 400 | 1.33 | `text-xs` |

**Urg'u — faqat og'irlik (600), o'lcham emas, rang emas.** `font-medium` (500) va `text-base` (16px) **taqiqlangan** [MEROS: 02-UI-SPEC §3.2 — Wave 0 da chiqarib tashlangan].

**Hujjatlashtirilgan istisno saqlanadi:** `font-mono` — **faqat** o'qib aytiladigan/nusxa olinadigan texnik qiymat uchun. 3-fazada bu:

| Qiymat | Uslub | Sabab |
|--------|-------|-------|
| NVR seriya raqami, firmware versiyasi | `font-mono text-xs` | Qurilma web-interfeysi bilan **belgima-belgi** solishtiriladi |
| IP manzil va port | `font-mono text-xs` | Yuqoridagi bilan bir xil sabab |
| Kanal raqami badge'i | `font-mono text-xs` | Ustunlashgan ro'yxat |
| `error_detail.raw` (`<details>` ichida) | `font-mono text-xs` | Texnik yordamga **nusxalanadi** |

`font-mono text-xl` (2-fazadagi vaqtinchalik parol istisnosi) bu fazada **ishlatilmaydi** — 3-fazada ovoz chiqarib o'qiladigan sir yo'q (NVR paroli **hech qachon ko'rsatilmaydi**, D-12).

### 2.3 Color — 60/30/10 o'zgarishsiz + bitta yangi qo'llanish

| Rol | Token | Qiymat | 3-fazada qayerda |
|-----|-------|--------|------------------|
| **Dominant (60%)** | `--color-bg` | `oklch(0.985 0 0)` | Sahifa foni |
| **Ikkilamchi (30%)** | `--color-surface` | `oklch(1 0 0)` | NVR kartasi, kamera qatorlari, dialog |
| | `--color-surface-muted` | `oklch(0.968 0 0)` | Skeleton, arxivlangan qator, video **idle** foni |
| **Aksent (10%)** | `--color-accent` | `oklch(0.56 0.19 255)` | §2.4 ro'yxati |
| **Destruktiv** | `--color-danger` | `oklch(0.58 0.21 27)` | **Faqat** arxivlash tasdiq tugmasi foni |

**Yangi qo'llanish (yangi token EMAS)** [QAROR]:

| Element | Token | O'lchangan kontrast |
|---------|-------|---------------------|
| Jonli video ramkasi (oqim ochiq bo'lganda letterbox maydoni) | `bg-text` (`oklch(0.205 0 0)`) | — (matnsiz holatda) |
| O'sha ramka ustidagi holat matni (ulanmoqda / muddat tugadi / xato) | `text-bg` (`oklch(0.985 0 0)`) | `0.985` vs `0.205` → **15.6:1** ✅ AAA |

Sabab: video letterboxi oq bo'lsa tasvir chegarasi yo'qoladi va oq yo'llar qorong'i bozor kadrida ko'zni qamashtiradi. Yangi token **kiritilmaydi**: `--color-text` allaqachon shu qiymatda va bu juftlik 2-fazada hisoblangan juftlikning teskarisi.

**Video ramkasi `bg-text` FAQAT `connecting`/`playing`/`expired`/`error` holatlarida.** `idle` holatida ramka `bg-surface-muted` bo'ladi — u yerda oqim yo'q, ya'ni qora to'rtburchak «buzilgan» degan yolg'on signal berardi.

### 2.4 Aksent nima uchun saqlangan — 3-faza ro'yxati

Aksent rang **faqat** quyidagilarda:

1. **Birlamchi tugma foni** — sahifada **eng ko'pi bilan bitta**. `/cameras` da holatga qarab **bittasi**: NVR yo'q → «NVR ulash»; NVR bor, kamera yo'q → «Kameralarni topish»; hammasi bor → **birlamchi tugma umuman yo'q** (qayta skanerlash `secondary`).
2. **Fokus halqasi** (`:focus-visible outline`) — barcha interaktiv elementlar.
3. **Faol maydon chegarasi va halqasi** (`focus-visible:border-accent`, `ring-accent/25`).
4. **Joriy navigatsiya elementi** — faqat mobil pastki panelda.
5. **Checkbox `accent-color`** — «Arxivlanganlarni ko'rsatish».

**Aksent ishlatilMAYDIGAN joylar (aniq taqiq):** kamera holati badge'i, skan natijasi hisoblagichlari, video ramkasi, transport badge'i («WebRTC»), «Ko'rish» tugmasi (u `secondary`), qayta skanerlash tugmasi, `<details>` ochilish belgisi, xato bloklari.

### 2.5 Rang hech qachon YAGONA signal emas (WCAG 1.4.1)

| Holat | Rang kanali | Qo'shimcha kanal 1 | Qo'shimcha kanal 2 |
|-------|-------------|--------------------|--------------------|
| Kamera **onlayn** | `Badge tone="success"` | `Wifi` ikonkasi (12px) | Badge **matni** «Onlayn» |
| Kamera **oflayn** | `Badge tone="muted"` | `WifiOff` ikonkasi | Badge matni «Ulanmagan» |
| Kamera **noma'lum** | `Badge tone="muted"` | `Clock` ikonkasi | Badge matni «Hali tekshirilmagan» |
| Kamera **arxivlangan** | qator `bg-surface-muted` | `Archive` ikonkasi | Badge matni «Arxivda» + `text-muted` |
| Skan: **yangi qo'shildi** | `tone="success"` | `Plus` ikonkasi | Raqam + to'liq so'z yorlig'i |
| Skan: **ulanmagan belgilandi** | `tone="warning"` | `WifiOff` ikonkasi | Raqam + to'liq so'z yorlig'i |
| Skan: **o'zgarishsiz** | `tone="neutral"` | `Minus` ikonkasi | Raqam + to'liq so'z yorlig'i |
| Xato: **qat'iy** (`danger`) | `bg-danger/10 text-danger-text` | `AlertCircle` | «Sabab» / «Nima qilish kerak» yorliqlari |
| Xato: **sozlama** (`warning`) | `bg-warning/20 text-text` | `AlertTriangle` | O'sha ikki yorliq |
| Nom **qo'lda o'zgartirilgan** | — (rang yo'q) | `Pencil` ikonkasi (12px) | `sr-only` + `title` matn |
| RTSP porti **taxmin qilingan** | `tone="warning"` badge | `AlertTriangle` 12px | Badge matni «taxmin qilingan» |

> ⚠ `--color-warning` **hech qachon matn rangi emas** [MEROS: 02-UI-SPEC §4.2]. Sariq tintdagi matn — `bg-warning/20 text-text` (o'lchangan 15.63:1).

---

## 3. Ekran inventarizatsiyasi va navigatsiya

### 3.1 Marshrutlar — bitta sahifa, uchta vertikal zona [QAROR]

| Marshrut | Vazifa | Kirish huquqi (UI ko'zgusi) |
|----------|--------|------------------------------|
| `/[locale]/(app)/cameras` | **Yagona 3-faza sahifasi.** Uch zona: (A) NVR kartasi, (B) kashfiyot paneli, (C) kameralar ro'yxati | `camera_view` |
| `/[locale]/(app)/cameras?run={uuid}` | O'sha sahifa, kashfiyot yugurishi poll qilinmoqda | `camera_view` |

**Ikkinchi marshrut YO'Q. `/cameras/new`, `/cameras/[id]`, `/cameras/nvr` — QURILMAYDI.**

Sabablar [QAROR]:

1. **MVP'da bitta NVR** [MEROS: 03-RESEARCH Scope Fence — *«Bir nechta NVR bitta bozorda | Sxema qo'llaydi | UI'da MVP'da bitta»*]. NVR ro'yxati marshruti bitta elementli ro'yxatni ko'rsatardi.
2. **Oqim uzluksiz bo'lishi kerak.** SC#1 ning va'dasi — «forma → tugma → kameralar». Uch marshrutga bo'lish bu va'dani uch navigatsiyaga bo'lardi va har o'tishda «endi nima?» savolini tug'dirardi.
3. **Kashfiyot natijasi kontekst talab qiladi.** «6 ta kamera qo'shildi» xabari kameralar ro'yxatining **yonida** turishi kerak, aks holda admin natijani ko'rish uchun boshqa sahifaga o'tishi va u yerda hisoblagichlarni yo'qotishi kerak bo'lardi.
4. **Kamera detali alohida sahifani oqlamaydi.** Kamerada ko'rsatiladigan narsa 6 ta maydon va 3 ta amal — u qatorga va dialogga to'liq sig'adi.

**Dialoglar (marshrut emas, sahifa holati):**

| Dialog | Ochiladi | O'lcham |
|--------|----------|---------|
| Jonli ko'rish | Qator «Ko'rish» tugmasidan | `size="lg" sheetOnMobile` |
| Kamera nomini o'zgartirish | Qator menyusidan | `size="sm"` |
| Kamerani arxivlash (tasdiq) | Qator menyusidan | `ConfirmDialog` 1-daraja |
| NVR parolini yangilash | NVR kartasidan | `size="sm"` |

**Dialog holati URL'da EMAS** [MEROS: 02-UI-SPEC §7.1 qoida 3 — tanlangan element sahifa holatida yashaydi]. Yagona istisno — `?run={uuid}` (§5.4). Jonli ko'rish dialogining URL'da bo'lmasligi **maqsadli**: ulashiladigan havola avtorizatsiya ortidagi oqimga ishora qilardi va SC#6 ning ruhiga zid tushardi.

### 3.2 Sahifaning vertikal tuzilishi

```
┌ Kameralar                                            (h1, 24/600)
│
├─ (A) NVR kartasi  ────────────────────────────────────────────┐
│   NVR mavjud emas  →  EmptyState + [NVR ulash] (birlamchi)     │
│   NVR mavjud       →  model · seriya · firmware · manzil       │
│                       [Kameralarni topish] yoki [Qayta skan]   │
│                       [Parolni yangilash]  [Diagnostika]       │
│                       (xato bo'lsa) NvrErrorBlock              │
└───────────────────────────────────────────────────────────────┘
│
├─ (B) Kashfiyot paneli  ── faqat faol yoki yaqinda tugagan run bo'lsa
│      queued / running(a) / running(b) / succeeded / failed / timeout
│
└─ (C) Kameralar ro'yxati  ── filtr qatori + qatorlar yoki EmptyState
```

Uch zona **hech qachon almashmaydi** — (B) paydo bo'lganda (C) o'z joyida qoladi va **o'chmaydi**. Sabab: qayta skanerlash paytida mavjud ro'yxatning yo'qolishi «kameralarim o'chib ketdimi?» degan qo'rquv tug'diradi. (C) faqat `aria-busy` oladi va yangilanishdan keyin joyida yangilanadi.

### 3.3 Navigatsiya kengaytmasi — bitta yozuv [QAROR]

`NAV_ITEMS` ga **bitta** element qo'shiladi [KOD: `app-shell.tsx:86-161`]:

```ts
{
  href: "/cameras",
  labelKey: "cameras",
  icon: Video,
  permission: "camera_view",
  group: "market",
}
```

`NavItem["href"]` va `NavItem["labelKey"]` literal union'lariga `"/cameras"` va `"cameras"` qo'shiladi — aks holda kompilyatsiya yiqiladi (bu **maqsadli** darvoza [KOD: `app-shell.tsx:53-77`]).

**Joylashuv: `market` guruhida, `/calendar` dan KEYIN, `/users` dan OLDIN.**

| Savol | Javob | Sabab |
|-------|-------|-------|
| Nega `market` guruhi? | Kamera — **bozor ichidagi** obyekt (xarita, rastalar, tariflar bilan bir qatorda), platforma amali emas | `/markets/new` `system` guruhida turishi bilan izchil [KOD: `app-shell.tsx:154-160`] |
| Nega `/calendar` dan keyin? | `NAV_ITEMS` tartibi mobil pastki panelning birinchi **to'rttasini** belgilaydi (`MOBILE_PRIMARY_COUNT = 4`) [KOD: `app-shell.tsx:164`]. Kamerani yuqoriga ko'chirish kassir/admin eng ko'p ishlatadigan bo'limni paneldan siqib chiqarardi | 02-UI-SPEC §12.3 kontrakti |
| Mobil kontrakt buzilmaydimi? | **Yo'q** [O'LCHANDI: M-7 — rol matritsasi bo'yicha hisoblandi]. `platform_admin` **10**, `director` **9**, `market_admin` **9**, kassir **1**, nazoratchi **1**. To'rttadan ortiq bo'lgan har uch rolda panel `4 + «Ko'proq» = `**5** | ≤5 saqlanadi |
| Direktorga jonli ko'rish mobilda chuqurroqda qolmaydimi? | Ha — «Ko'proq» ostida, ya'ni 2 bosish. Bu **qabul qilinadi**: jonli ko'rish direktorning **kunlik** amali emas, u nizo yoki tekshiruv paytida ochiladi | Tartibni rolga qarab o'zgartirish `NAV_ITEMS` ni global konstanta bo'lishdan chiqarardi |

`nav.cameras` kaliti uch tilda qo'shiladi (§11.1).

### 3.4 Ustaga ulanish — «keyinroq» endi «hozir» [QAROR]

2-faza D-16 aniq: **kamera usta QADAMI EMAS** va `WIZARD_STEPS` massiviga **qo'shilmaydi** [KOD: `wizard-steps.ts:132-146` — sabab uzun izohda]. Bu qaror **o'zgarmaydi**: bozor kamerasiz faollashtiriladi va kamera hech qachon `blocking[]` ga tushmaydi.

Lekin 3-fazadan keyin `Kamera (keyinroq)` yozuvi **yolg'onga aylanadi** — bo'lim endi mavjud. Uchta minimal o'zgarish:

| # | Fayl | Hozir | O'zgarish |
|---|------|-------|-----------|
| **U-1** | `wizard-steps.ts:144-146` | `CAMERA_PLACEHOLDER = { labelKey: "wizard.step.cameras" }` | `href: "/cameras"` qo'shiladi. **`WIZARD_STEPS` massiviga QO'SHILMAYDI** — progress sanog'i, `blockedBy` grafi va `blocking[]` tegilmaydi |
| **U-2** | `wizard-stepper.tsx` | Kamera elementi `aria-disabled="true"`, havola **emas** | Haqiqiy `<Link href="/cameras">` bo'ladi; `aria-disabled` **olib tashlanadi**; qadam **raqami berilmaydi** va `Check`/`Lock` ikonkasi **qo'yilmaydi** — u hamon qadam emas |
| **U-3** | `activation-panel.tsx` | `·  Kamera (keyinroq ulanadi)   —` | `·  Kameralar   {count} ta` (yoki `—`) va **havola**. Belgi hamon `·` — hech qachon `✓` yoki `✗` |

**QAT'IY TAQIQ saqlanadi** [MEROS: 02-UI-SPEC §6.7]: `AlertTriangle`/`AlertCircle` ikonkasi, `bg-warning/*` yoki `bg-danger/*` fon, `role="alert"`, «chala»/«tugallanmagan»/«e'tibor bering» so'zlari, sariq/qizil chegara — **usta ichida kamera bilan bog'liq hech bir joyda**. Kamerasiz bozor **normal**, nosozlik emas.

`wizard.cameraNote` matni yangilanadi (§11.5) — «keyinroq ulanadi» o'rniga «istalgan vaqtda ulanadi».

**Nega kamera ustaga to'liq qadam qilib kiritilmaydi (muqobil rad etildi):** qadam qilinsa u avtomatik ravishda progress sanog'iga (`completedStepCount`), `blockedBy` grafiga va «bajarilganmi?» savoliga tushardi — ya'ni bozor kamerasiz hech qachon «to'liq» ko'rinmasdi. Bu D-16 ning aynan teskarisi va `wizard-steps.ts` dagi izoh buni oldindan taqiqlagan.

---

## 4. Yuza 1 — NVR qo'shish formasi (CAM-01, SC#1, D-01)

### 4.1 Maydonlar — uchta, boshqa emas [QAROR]

D-01: *«Admin saytga **faqat** NVR manzili + login/parolni kiritadi.»*

| # | Maydon | Tip | Standart | Majburiy |
|---|--------|-----|----------|----------|
| 1 | **NVR manzili** (`cameras.nvrAddress`) | `text`, `inputMode="url"`, `autoComplete="off"` | — | ✅ |
| 2 | **Foydalanuvchi nomi** (`cameras.nvrLogin`) | `text`, `autoComplete="username"` | — | ✅ |
| 3 | **Parol** (`cameras.nvrPassword`) | `password`, `autoComplete="new-password"` | — | ✅ |

**Port va TLS uchun ALOHIDA MAYDON YO'Q.** Ular **manzil maydonidan ajratiladi**:

| Kiritilgan | `host` | `port` | `use_tls` |
|------------|--------|--------|-----------|
| `192.168.1.64` | `192.168.1.64` | `80` | `false` |
| `192.168.1.64:8080` | `192.168.1.64` | `8080` | `false` |
| `http://192.168.1.64` | `192.168.1.64` | `80` | `false` |
| `https://192.168.1.64` | `192.168.1.64` | `443` | `true` |
| `https://192.168.1.64:8443` | `192.168.1.64` | `8443` | `true` |
| `nvr.local` | `nvr.local` | `80` | `false` |

Ajratish **klientda** (`zod` `.transform()`) bajariladi; serverga allaqachon ajratilgan `{host, port, use_tls}` yuboriladi.

**Nega maydon emas, ajratish** [QAROR]:
- **D-01 ni harfma-harf bajaradi** — ekranda uchta maydon turadi va uchalasi ham adminda **bor** (manzil o'rnatuvchi qog'ozida, login/parol o'sha yerda).
- Yashirin `<details>` «Qo'shimcha sozlamalar» ham **rad etildi**: u ekranda to'rtinchi affordans hosil qiladi va admin uni ochishga majbur bo'lgan holatda («nega ishlamayapti? balki shu yerdadir») D-01 ning ruhini buzadi.
- Odamlar NVR manzilini **allaqachon** `192.168.1.64:8080` shaklida yozadi.
- `use_tls` alohida checkbox bo'lsa admin uni **tasodifan** yoqib qo'yishi va `nvr_tls_untrusted` xatosini sababsiz olishi mumkin edi.

**Yordamchi matn (`hint`) majburiy** — u qoidani ko'rsatadi, aks holda ajratish sehr bo'lib qoladi (matn §11.2).

### 4.2 Parol maydoni — yozish uchun, o'qish uchun emas (D-12)

| Qoida | Amalda |
|-------|--------|
| **Parol hech qachon qaytarilmaydi** | API javob sxemasida maydon **umuman yo'q** [MEROS: 03-RESEARCH §C.10]. Frontend uni **hech qachon** so'ramaydi va `useQuery` keshiga tushirmaydi |
| **Tahrirlashda maydon bo'sh** | NVR mavjud bo'lsa forma parolni **ko'rsatmaydi**; parol o'zgartirish — **alohida dialog** (§4.6) |
| **`autoComplete="new-password"`** | Brauzer NVR parolini foydalanuvchining o'z paroli deb saqlab qo'ymasligi uchun |
| **Toast/jurnal/URL/`localStorage` ga hech qachon tushmaydi** | 2-fazadagi vaqtinchalik parol naqshi [KOD: `temp-password-dialog.tsx:18-27`] |
| **`useMutation`, `useQuery` EMAS** | Parol React Query keshiga tushmasligi kerak — o'sha naqsh |

**Parolni ko'rsatish tugmasi qulaylik uchun EMAS, xavfsizlik uchun** [QAROR]:

D-03: `401` da hisob **~5 urinishdan keyin 30 daqiqaga qulflanadi**. Ya'ni **bitta terish xatosi 30 daqiqalik to'xtash** demakdir. Ko'rsatish tugmasi terish xatosini yuborishdan **oldin** ushlaydi — bu qulflanish ehtimolini pasaytiradigan eng arzon chora.

```tsx
<button type="button"
        aria-pressed={visible}
        aria-controls="nvr-password"
        aria-label={visible ? t("cameras.hidePassword") : t("cameras.showPassword")}
        className="min-h-11 min-w-11 ...">
  {visible ? <EyeOff aria-hidden="true" /> : <Eye aria-hidden="true" />}
</button>
```

`aria-pressed` — `aria-label` ning o'zgarishi bilan **birga**, chunki ba'zi skrinriderlar faqat bittasini o'qiydi.

### 4.3 Ikkita tugma va ularning ierarxiyasi

| Tugma | Variant | Vazifa | Kutish |
|-------|---------|--------|--------|
| **Ulanishni tekshirish** | `secondary` | `POST /nvr-devices/test-connection` — **yozuv yaratmaydi** | inline, ≤2 s [MEROS: 03-RESEARCH §E.16] |
| **Saqlash va kameralarni topish** | `default` (**birlamchi**) | `POST /nvr-devices` → `POST /{id}/discover` → `202` | Saqlash inline, kashfiyot **job** |

**Nega ikkitasi ham kerak** (bittaga qisqartirish rad etildi): «Ulanishni tekshirish» **hech narsa saqlamaydi** va shuning uchun **xavfsiz sinov maydoni**. Usiz admin har urinishda DB'da yozuv qoldirardi yoki — yomoni — noto'g'ri parol bilan **darhol kashfiyot jobiga** kirib, 25 kanal bo'ylab 401 olardi va hisobni qulflardi.

**Tekshiruv MAJBURIY EMAS.** Admin to'g'ridan-to'g'ri «Saqlash va kameralarni topish» ni bosishi mumkin — bu yo'l to'liq ishlaydi va u SC#1 ning «bitta tugma» va'dasini saqlaydi.

**Yuborish paytida:** birlamchi tugma matni «Saqlanmoqda», `aria-disabled="true"`; ikkinchisi ham bloklanadi. `disabled` **ishlatilmaydi** [MEROS: 02-UI-SPEC §6.6 qoida 2 — `disabled` tugma fokus olmaydi va skrinrider uni o'qimaydi].

### 4.4 ⛔ AUTH-XATO QULFI — bu fazaning eng muhim interaksiya qoidasi [QAROR]

D-03: *«401 ni qayta urinish TAQIQLANADI — Hikvision hisobni bloklaydi (~5 urinish / 30 daqiqa).»*

Odatiy UI naqshi («xato → «Qayta urinish» tugmasi») bu yerda **zararli**: admin tugmani uch marta bosadi va hisobni qulflaydi. Quyidagi qoida **butun fazaga** taalluqli.

```
AUTH_LOCKING_CODES = {
  nvr_bad_credentials,      // parol/login xato
  nvr_account_locked,       // allaqachon qulflangan
  nvr_user_no_permission,   // huquq yo'q — qayta urinish foyda bermaydi, lekin sanaladi
}
```

| Holat | Xulq |
|-------|------|
| Javobda `error_code ∈ AUTH_LOCKING_CODES` | `authLocked = true` |
| `authLocked === true` | **Ikkala tugma ham** `aria-disabled="true"` + `variant="secondary"` |
| `authLocked === true` | Xato blokida **«Qayta urinish» affordansi RENDER QILINMAYDI** — u yo'q, yashirilgan emas |
| Bloklangan tugma bosilsa | So'rov **yuborilmaydi**; fokus **parol maydoniga** ko'chadi; `role="status"` e'lon qiladi: «Qayta urinishdan oldin login yoki parolni o'zgartiring» |
| `authLocked` qachon ochiladi | **FAQAT** `username` yoki `password` maydonining qiymati o'zgarganda (`react-hook-form` `watch`). Vaqt bo'yicha **emas**, tugma bilan **emas**, sahifa yangilash bilan **emas** |
| `nvr_account_locked` qo'shimchasi | Yuqoridagilarga qo'shimcha: `error_detail.unlock_at` gacha **taymer**; qulf **ikkala shart** bajarilgunicha ochilmaydi (vaqt o'tgan **VA** rekvizit o'zgargan) |

**Bu qoida `<form>` darajasida emas, umumiy hook darajasida yashaydi** — `useNvrAuthLock()`. Uni forma ham, NVR kartasi ham («Diagnostika», «Qayta skanerlash») iste'mol qiladi. Aks holda qoida bir yuzada bo'lib, ikkinchisida unutilardi.

> **Nega «30 daqiqadan keyin avtomatik qayta urinish» ham RAD ETILDI:** avtomatik urinish adminning ko'zi oldida bo'lmaydi va u qulflanish sababini bilmasdan uni qayta tug'diradi. Har urinish **odamning aniq qarori** bo'lishi shart.

### 4.5 Muvaffaqiyatli tekshiruv — nima ko'rsatiladi

`test-connection` `{ok: true}` qaytarganda [MEROS: 03-RESEARCH §E.16]:

```
┌ ✓ Qurilma topildi ─────────────────────────────────────┐
│  Model            DS-7616NI-K2                          │
│  Turi             NVR                                   │
│  Kanallar         6 ta                                  │
│  Soat farqi       12 soniya                             │
└─────────────────────────────────────────────────────────┘
```

| Qoida | Sabab |
|-------|-------|
| `role="status"`, sarlavhada `tone="success"` badge | Muvaffaqiyat — `alert` **emas** |
| **Kanallar soni MAJBURIY** | Adminning «to'g'ri qurilmaga ulandimmi?» savoliga yagona javobi. 16 kanalli NVR'da 6 ta kamera ko'rinishi **normal** — hint buni aytadi |
| **Soat farqi DOIM ko'rsatiladi**, 300 s dan kichik bo'lsa ham | 250 soniyalik farq bugun ishlaydi, ertaga sinadi. Ko'rsatish uni **oldindan** tuzatish imkonini beradi |
| Soat farqi ≥ 120 s | Qiymat yonida `AlertTriangle` + `tone="warning"` badge va `cameras.clockDriftWarning` matni — **xato emas, ogohlantirish** |
| **Seriya raqami bu bosqichda KO'RSATILMAYDI** | U yozuv saqlangandan keyin NVR kartasida chiqadi; tekshiruv ekranida u shovqin |

Natija bloki paydo bo'lganda **fokus ko'chmaydi** (foydalanuvchi tugmada qoladi) — e'lon `aria-live="polite"` bilan yetkaziladi.

### 4.6 NVR mavjud bo'lganda — karta va uning amallari

```
┌ NVR qurilmasi ────────────────────────────────────────────────┐
│  DS-7616NI-K2                                    [Onlayn]     │
│  192.168.1.64:80  ·  V4.74.210  ·  DS-7616NI-K2000...         │ ← font-mono text-xs
│  RTSP porti 554  [taxmin qilingan]                            │
│  Oxirgi skan: 3 daqiqa oldin                                  │
│                                                               │
│  [Qayta skanerlash]  [Parolni yangilash]  [Diagnostika]       │
└───────────────────────────────────────────────────────────────┘
```

| Element | Qoida |
|---------|-------|
| `rtsp_port_assumed === true` | Port yonida `tone="warning"` badge «taxmin qilingan» + hint (§11.2). Sabab: 554 fallback **jimgina ishlamaydigan** kamera yozuvlari tug'diradi — kashfiyot yashil, kadr olish qora [MEROS: 03-RESEARCH §A.2] |
| Manzilni tahrirlash | **Bu fazada YO'Q.** Manzil `UNIQUE (market_id, host, port)` kalitining bir qismi; uni tahrirlash idempotentlik semantikasini ochib yuboradi. Manzil o'zgarsa NVR qayta qo'shiladi |
| «Parolni yangilash» | `size="sm"` dialog, bitta maydon + ko'rsatish tugmasi. Muvaffaqiyatda toast. **Eski parol so'ralmaydi** — u bizda ochiq matnda yo'q |
| «Diagnostika» | `POST /test-connection` ni **saqlangan** rekvizitlar bilan qayta ishga tushiradi va §4.5 blokini yoki xato blokini beradi. Auth-xato qulfi (§4.4) bu tugmaga ham **qo'llanadi** |
| «Qayta skanerlash» | `variant="secondary"` (§6.2) |

### 4.7 Forma validatsiyasi (klient, `zod`)

| Maydon | Qoida | Xato kaliti |
|--------|-------|-------------|
| Manzil | Bo'sh emas | `errors.required` |
| Manzil | Ajratilgandan keyin `host` yaroqli IPv4 yoki hostname | `cameras.invalidAddress` |
| Manzil | **Ommaviy IP rad etiladi** (`10.*`, `172.16–31.*`, `192.168.*`, `100.64–127.*` dan tashqarisi) | `cameras.publicAddressBlocked` |
| Manzil | Port `1–65535` | `cameras.invalidPort` |
| Login | Bo'sh emas | `errors.required` |
| Parol | Bo'sh emas | `errors.required` |

> **Ommaviy IP klientda ham bloklanadi** — bu **qulaylik**, xavfsizlik chegarasi **emas** [MEROS: 02-UI-SPEC §12.3 DIQQAT bandi]. Haqiqiy darvoza serverda (`nvr_devices.host` validatsiyasi, 03-RESEARCH §C.11). Klientdagi tekshiruv adminni **tushuntirish bilan** to'xtatadi (§11.2); serverda bu quruq 4xx bo'lardi va sabab yo'qolardi.

**Xatolar joyi** [MEROS: 02-UI-SPEC §6.8]:

| Xato turi | Joyi | ARIA |
|-----------|------|------|
| Maydon xatosi (zod) | Maydon **ostida**, `Field` `error` propi | `aria-invalid` + `aria-describedby="{id}-error"` |
| NVR ulanish xatosi (`error_code`) | Forma **ostida**, `NvrErrorBlock` | `role="alert"` |
| Server 4xx (domen kodi) | Forma **tepasida**, `role="alert"` | `role="alert"` |

**Yuborishdan keyingi fokus:** zod yiqilsa → birinchi noto'g'ri maydon (`setFocus`); `error_code` kelsa → `NvrErrorBlock` ning o'ziga (`tabIndex={-1}` + `.focus()`), chunki tuzatish yo'li **o'sha yerda** yozilgan.

---

## 5. Yuza 2 — Kashfiyot oqimi (SC#1, SC#2)

### 5.1 Kashfiyot — so'rov emas, JOB [MEROS: 03-RESEARCH §E.16]

Byudjet hisobi: ~29 ISAPI so'rovi × 2 borish × 300 ms ≈ **17 s yaxshi holatda, 60 s+ sekin NVR'da**. HTTP so'rovi ichida bu qabul qilinmaydi.

```
POST /api/v1/nvr-devices/{id}/discover                  →  202 { run_id }
GET  /api/v1/nvr-devices/{id}/discovery-runs/{run_id}   →  poll
```

**UI kontrakti:** kashfiyot **hech qachon** «tugamasligi mumkin bo'lgan spinner» ko'rinishida bo'lmaydi. Har bir holat nomlanadi, o'lchanadi va **chegaralanadi**.

### 5.2 Oltita holat — hech biri yashirin emas

| # | Holat | Shart | Ko'rinish |
|---|-------|-------|-----------|
| **S0** | `idle` | Faol run yo'q | Panel **render qilinmaydi** |
| **S1** | `queued` | `status === "queued"` | «Navbatga qo'yildi» + Skeleton |
| **S2a** | `running` (aniqlash) | `status === "running"` **va** `channels_found === null` | «Qurilma aniqlanmoqda…» + Skeleton |
| **S2b** | `running` (tekshirish) | `status === "running"` **va** `channels_found > 0` | «{n} ta kanal topildi — oqimlar tekshirilmoqda…» + Skeleton |
| **S3** | `succeeded` | `status === "succeeded"` | Uch hisoblagichli natija paneli (§6.3) |
| **S4** | `failed` | `status === "failed"` | `NvrErrorBlock` (§7) |
| **S5** | `timeout` | 180 s ichida terminal holat kelmadi | «Kashfiyot javob bermayapti» + [Holatni tekshirish] |

#### S2a → S2b — bu UI backend'dan talab qiladigan narsa [TALAB]

> **Worker `channels_found` ni kanallar ro'yxati parse qilinishi bilanoq, har-kanal sub-oqim tekshiruvlaridan OLDIN `nvr_discovery_runs` qatoriga yozishi SHART.**

Sabab: byudjet hisobiga ko'ra vaqtning **katta qismi** (25 kanal × 2 borish) aynan sub-oqim tekshiruviga ketadi. Agar `channels_found` faqat oxirida yozilsa, admin ~50 soniya davomida **bir xil** «yuklanmoqda» ni ko'radi. Bitta qo'shimcha `UPDATE` 50 soniyalik qorong'ilikni **ikkita o'qiladigan bosqichga** ajratadi va UI tomonda **nol** qo'shimcha ish talab qiladi.

**Soxta progress bar QURILMAYDI** [MEROS: 02-UI-SPEC — import panelidagi *«PROGRESS INDIKATORI YO'Q — soxta ko'rsatkich yolg'on bo'lardi»* qarori]. Foiz ma'lum emas; uni o'ylab topish yolg'on. Uning o'rniga: **bosqich nomi** (haqiqiy ma'lumot) + **o'tgan vaqt** (haqiqiy o'lchov).

#### O'tgan vaqt ko'rsatkichi

| Qoida | Qiymat | Sabab |
|-------|--------|-------|
| Qachon paydo bo'ladi | `elapsed >= 5000 ms` | Tez run'da hisoblagichning miltillashi bezovta qiladi |
| Format | `{n} soniya`, 60 s dan keyin `{m}:{ss}` | — |
| ARIA | **`aria-hidden="true"`** | Har soniyada e'lon qilinsa panel skrinrider foydalanuvchisi uchun o'qib bo'lmas holga keladi |
| 60 s dan keyin | Ostida qo'shimcha qator: «Sekin tarmoqda bu 1–2 daqiqa davom etishi mumkin» | Adminni «osilib qoldi» degan xulosadan qaytaradi |

### 5.3 Poll kontrakti — kodbazada BIRINCHI marta [O'LCHANDI: M-3 → 0 hodisa]

```ts
useQuery({
  queryKey: discoveryRunKey(marketId, nvrId, runId),
  queryFn: ...,
  refetchInterval: (query) =>
    isTerminal(query.state.data?.status) ? false : DISCOVERY_POLL_INTERVAL_MS,
  refetchIntervalInBackground: false,   // (standart) — yashirin tabda poll YO'Q
  gcTime: 5 * 60_000,
})
```

| Parametr | Qiymat | Sabab |
|----------|--------|-------|
| **`DISCOVERY_POLL_INTERVAL_MS`** | **2000** | Byudjet 17–60 s → 9–30 ta poll. 1000 ms ikki barobar yuk beradi va sezilarli foyda bermaydi; 5000 ms 17 soniyalik jobni javobsiz ko'rsatadi |
| **To'xtash sharti** | `status ∈ {succeeded, failed}` → `false` | Terminal holatda poll **butunlay** to'xtaydi |
| **Yashirin tab** | `refetchIntervalInBackground: false` | Admin boshqa tabga o'tsa server bekorga yuklanmaydi; qaytganda `refetchOnWindowFocus` darhol yangilaydi |
| **`DISCOVERY_POLL_TIMEOUT_MS`** | **180 000** (3 daqiqa) | Byudjetning eng yomon holatining (60 s+) **3 barobari**. Undan keyin poll **to'xtaydi** va S5 chiqadi. **Cheksiz poll HECH QACHON** |
| **Poll'ning o'zi yiqilsa** | 3 ta ketma-ket tarmoq xatosi → S5 | Tarmoq yo'qligi kashfiyot xatosi sifatida ko'rsatilmaydi |

**S5 (timeout) — bu xato EMAS.** Job hamon ishlayotgan bo'lishi mumkin. Ko'rinish: `tone="neutral"`, `role="status"`, matn §11.3, + **[Holatni tekshirish]** tugmasi (bitta qo'lda `refetch`). Xato rangi **ishlatilmaydi**.

### 5.4 `run_id` URL'da — uzilishdan tiklanish

`nuqs` bilan `?run={uuid}` [MEROS: 03-RESEARCH §E.16 — *«sahifa yangilanganda poll davom etadi»*].

| Vaziyat | Xulq |
|---------|------|
| `POST /discover` → 202 | `setRun(run_id)` → URL yangilanadi (`history: "replace"`) |
| Sahifa yangilandi / boshqa qurilmadan ochildi | `?run=` bor → darhol poll boshlanadi |
| Terminal holatga yetdi | `?run=` **saqlanadi** — natija paneli o'qilishi kerak |
| Foydalanuvchi natijani yopdi | `setRun(null)` → URL tozalanadi |
| `?run=` yaroqsiz UUID yoki 404 | Jimgina `setRun(null)`; panel render qilinmaydi. **Xato ko'rsatilmaydi** — eski havolani ochish nosozlik emas |

### 5.5 Bekor qilish — YO'Q [QAROR]

Tadqiqotda bekor qilish endpointi yo'q va u qo'shilmaydi.

| Savol | Javob |
|-------|-------|
| Nega? | Kashfiyot **hech narsani buzmaydi**: u faqat o'qiydi va idempotent upsert qiladi. Bekor qilish faqat **kutishni** qisqartirardi, holbuki sahifadan chiqib ketish ham xuddi shuni beradi |
| Admin sahifadan chiqsa? | Job **davom etadi**. Qaytganda `?run=` orqali natijani ko'radi |
| Bu qayerda aytiladi? | S1/S2 panelida bitta meta qator: «Sahifani yopsangiz ham kashfiyot davom etadi» |

### 5.6 Ikki marta bosish va poyga holati (409)

`nvr_discovery_runs` da `UNIQUE ... WHERE status IN ('queued','running')` qisman indeks bor → ikkinchi `POST` **409** oladi [MEROS: 03-RESEARCH §E.16].

**UI buni XATO deb ko'rsatMAYDI** [QAROR]. Ikki admin (yoki bitta admin ikki tabda) tugmani bir vaqtda bosishi — **normal ish jarayoni**, nosozlik emas.

| Xulq | Tafsilot |
|------|----------|
| 409 kelganda | Javob tanasidagi mavjud `run_id` **qabul qilinadi** va UI o'sha run'ni poll qila boshlaydi |
| Toast | **Yo'q.** Panelning paydo bo'lishi — yetarli tasdiq |
| Xato bloki | **Yo'q** |

> **[TALAB]** `409` javob tanasi mavjud yugurishning `run_id` sini o'z ichiga olishi shart: `{"detail": "discovery_already_running", "run_id": "..."}`. Aks holda UI ikkinchi so'rov qilishga majbur bo'ladi — bu poyga holatining o'zida yana bitta poyga.

Tugmaning o'zi ham himoyalanadi: `mutation.isPending` bo'lganda `aria-disabled` va matn «Boshlanmoqda».

---

## 6. Yuza 3 — Kameralar ro'yxati va qayta skanerlash (SC#2)

### 6.1 Qator tuzilishi — jadval emas, zich karta qatori [MEROS: 02-UI-SPEC §8.1]

```
┌──────────────────────────────────────────────────────────────────┐
│  01   Sabzavot qatori  ✎              [Onlayn]        [Ko'rish] ⋮ │
│       192.168.1.101 · DS-2CD2143G0 · oxirgi ko'rilgan: 2 daq     │
└──────────────────────────────────────────────────────────────────┘
```

| Element | Uslub | Qoida |
|---------|-------|-------|
| Kanal raqami | `font-mono text-xs`, `Badge tone="neutral"` | **Ikki xonali** formatlanadi (`01`, `07`, `16`) — ro'yxat ustunlashadi |
| Nom | Body 14/600 | **DB kontenti — TARJIMA QILINMAYDI** [MEROS: 1-faza D-16]. `truncate` + `title` |
| `name_overridden === true` | Nom yonida `Pencil` 12px + `sr-only` matn + `title` | §6.5 |
| Holat badge'i | §2.5 jadvali | Rang + ikonka + matn |
| Meta qatori | `text-xs text-text-muted` | IP (`font-mono`) · model · `last_seen_at` (nisbiy vaqt) |
| Amallar | «Ko'rish» — `secondary` tugma; qolgani `DropdownMenu` (`⋮`) | Mobil naqsh [KOD: `user-list.tsx:215-251`] |
| Semantika | `<ul>` / `<li>`; qator **o'zi bosiladigan emas** | Faqat ichidagi tugmalar fokuslanadi — roving tabindex kerak emas (≤32 qator) |

**Tartib: `channel_no` bo'yicha o'sish. Har doim. Saralash boshqaruvi YO'Q** [QAROR] — kanal raqami NVR'dagi jismoniy slotga mos keladi va admin uni **shu tartibda** ko'radi (NVR monitorida ham shunday). Boshqa saralash uni chalkashtirardi.

**Qidiruv maydoni YO'Q** [QAROR] — 16/32 kanalli NVR'da eng ko'pi 32 qator, kanal bo'yicha saralangan. Qidiruv ekranga affordans qo'shib, hech narsa bermasdi.

**Filtr — ikkita, `nuqs` bilan** [MEROS: `stall-filters.tsx` naqshi]:

| Filtr | Qiymatlar | Standart |
|-------|-----------|----------|
| `status` (`Select`) | hammasi / onlayn / ulanmagan | hammasi |
| `archived` (checkbox) | yashirin / ko'rinadi | **yashirin** |

### 6.2 Qayta skanerlash — tugma va uning kutishi

| Element | Qiymat |
|---------|--------|
| Joyi | NVR kartasi (zona A), ro'yxatning tepasida **emas** |
| Variant | `secondary` — sahifada allaqachon kameralar bor, ya'ni bu birlamchi amal emas |
| Ikonka | `RefreshCw` |
| Bosilganda | §5 dagi aynan bir xil oqim — S1…S5 |
| Ro'yxat (zona C) | **O'chmaydi.** `aria-busy="true"` oladi, mazmuni joyida qoladi (§3.2) |
| Auth-xato qulfi | **Qo'llanadi** (§4.4) |

### 6.3 ⛔ Uch natija — «hech narsa qilmadi» ko'rinishi TAQIQLANADI [QAROR]

SC#2 ning UI tomondagi butun mazmuni shu blokda. **Hech narsa o'zgarmagan skan buzuq skandan farqlanmasa, idempotentlik isbotlanmagan hisoblanadi.**

```
┌ ✓ Skanerlash yakunlandi ·  bugun 14:32 ─────────────────────┐
│                                                              │
│   ＋  0     Yangi qo'shildi                                  │
│   ⊘  0     Ulanmagan deb belgilandi                          │
│   −  6     O'zgarishsiz                                      │
│                                                              │
│   Barcha kanallar avvalgidek — o'zgarish topilmadi.          │
│                                                     [Yopish] │
└──────────────────────────────────────────────────────────────┘
```

| Qoida | Nima uchun |
|-------|-----------|
| **Uchala hisoblagich HAM DOIM ko'rinadi — nol bo'lsa ham** | Nol qatorni yashirish «bu skan hech narsa qilmadi» degan yolg'on signal beradi. Nol — **natija**, uning yo'qligi emas |
| **Sarlavha «Skanerlash yakunlandi», «0 ta kamera qo'shildi» EMAS** | Sarlavha **amalning** natijasini aytadi, birinchi hisoblagichni takrorlamaydi |
| **Vaqt belgisi sarlavhada** | Bu skan **hozir** bo'lganini isbotlaydigan ikkinchi kanal |
| **`tone="success"` — `added === 0` bo'lganda ham** | Skan **muvaffaqiyatli** o'tdi. Yashil rang «yangi kamera» ni emas, «amal bajarildi» ni bildiradi |
| **Uchala nol bo'lganda qo'shimcha jumla MAJBURIY** | «Barcha kanallar avvalgidek — o'zgarish topilmadi.» Bu **anti-«buzuq ko'rinadi»** jumlasi va u boshqa hech qachon chiqmaydi |
| **`role="status"`, `alert` EMAS** | Muvaffaqiyat ogohlantirish emas |
| Hisoblagichlar formulasi | `added = channels_added` · `offline = channels_marked_offline` · `unchanged = channels_found − channels_added` |
| Har hisoblagich `<dl>`/`<dt>`/`<dd>` | Raqam va yorliq **dasturiy jihatdan** bog'lanadi — skrinriderda «0» yolg'iz eshitilmaydi |

**Ikkinchi, mustaqil dalil kanali:** har qatordagi `last_seen_at` skan bilan **yangilanadi**. Admin natija panelini o'qimasa ham, ro'yxatdagi «2 daqiqa oldin» → «hozir» o'zgarishi skan haqiqatan ishlaganini ko'rsatadi. Shuning uchun `last_seen_at` meta qatorida **majburiy**.

> **`channels_found` ning ta'rifi** [TALAB]: shu yugurishda **sanab chiqilgan** kanallar soni — onlayn/oflayn holatidan **qat'i nazar**. Aks holda `unchanged` formulasi noto'g'ri chiqadi. Bu ta'rif rejaga yoziladi va testda tekshiriladi.

### 6.4 Qisman muvaffaqiyat — kashfiyot o'tdi, ba'zi kanal ulanmagan

Bu **eng ko'p uchraydigan real holat** va u xato **emas**.

| Nima bo'ldi | Ko'rinish |
|-------------|-----------|
| 6 kanal topildi, 2 tasi `online=false` | S3 natija paneli **normal** (`tone="success"`), qo'shimcha qator: «2 ta kanal hozir ulanmagan — ular ro'yxatda «Ulanmagan» deb turadi» |
| Ro'yxatda | O'sha 2 qator `tone="muted"` badge + `WifiOff` |
| `NvrErrorBlock` | **Chiqmaydi.** `channel_offline` — sahifa darajasidagi xato emas [MEROS: 03-RESEARCH §A.3 — *«Kamera yozuvi baribir yaratiladi»*] |
| Qator darajasida | «Ko'rish» tugmasi `aria-disabled` + sabab (§8.6) |

### 6.5 Nomni qo'lda o'zgartirish va uning ma'nosi (SC#2)

`name_overridden` bayrog'i [MEROS: 03-RESEARCH §A.4] — «mavjudi tegilmaydi» qoidasining aynan mazmuni. **Admin buni bilishi shart**, aks holda u nomini qayta skanerlash o'chirib yuborishidan qo'rqadi.

| Vaziyat | UI |
|---------|-----|
| Nom o'zgartirish dialogi ochiq | Maydon ostida `hint`: «Bu nom qayta skanerlashda saqlanadi — NVR qurilmasidagi nom uni almashtirmaydi» |
| Saqlangandan keyin | Toast «Nom saqlandi» + qatorda `Pencil` ikonkasi paydo bo'ladi |
| `name_overridden === true` qatorda | `Pencil` 12px `text-text-muted` + `sr-only` matn + `title` |
| Qaytarish | Dialogda **[NVR qurilmasidagi nomga qaytarish]** — `ghost` tugma; `name_overridden = false` qiladi va keyingi skanda nom NVR'dan olinadi |

### 6.6 Arxivlanganlar ro'yxatda

| Qoida | Qiymat |
|-------|--------|
| Standart | **Yashirin** |
| Ochish | Filtr qatorida checkbox «Arxivlanganlarni ko'rsatish» (yorlig'i `min-h-11`) |
| Ko'rinish | Qator `bg-surface-muted`, nom `text-text-muted`, `Archive` ikonkasi + `tone="muted"` badge |
| Amallar | Faqat **[Arxivdan qaytarish]**. «Ko'rish» **render qilinmaydi** — arxivlangan kameraning oqimi go2rtc'da ro'yxatga olinmaydi |
| Sanoq | Filtr yonida meta «Arxivda: {n} ta»; nol bo'lsa checkbox **umuman render qilinmaydi** |

---

## 7. Yuza 4 — Xato kontrakti (SC#3, D-02)

> **Bu fazadagi eng qimmatli ekran.** D-02: *«Xato hech qachon "ulanmadi" degan quruq xabar bo'lmaydi — sababi va tuzatish yo'li ko'rsatiladi.»*

### 7.1 `NvrErrorBlock` — tuzilishi

```
┌ [icon] ────────────────────────────────────────────────────┐
│                                                             │
│  SABAB                                                      │
│  Login yoki parol noto'g'ri.                                │
│                                                             │
│  NIMA QILISH KERAK                                          │
│  Login va parolni qayta kiriting. Diqqat: ketma-ket 5 ta    │
│  xato urinishdan keyin NVR hisobni 30 daqiqaga qulflaydi.   │
│                                                             │
│  [amal tugmasi — faqat ruxsat berilgan holatda]             │
│  ▸ Texnik tafsilot                                          │
└─────────────────────────────────────────────────────────────┘
```

**«Tuzatish sabab bilan teng darajada ko'rinadi» — mexanizm** [QAROR]:

Ikkalasi ham **yorliqlangan blok**. Yorliq — `text-xs font-semibold tracking-wide` (Meta), mazmun — Body 14/400. **Ikkalasi bir xil tipografik og'irlikda**, ya'ni birortasi ikkinchisining «izohi» bo'lib ko'rinmaydi.

Rad etilgan muqobillar:
- *Tuzatishni qalin qilish* — ikkita qalin matn bir-biri bilan raqobatlashadi va ierarxiya yo'qoladi.
- *Tuzatishni sabab jumlasining dumiga ulash* («… — NTP xizmatini yoqing») — bu aynan D-02 taqiqlagan shakl: tuzatish **ikkinchi darajali** bo'lib qoladi va uzun matnda o'qilmaydi.
- *Faqat tuzatishni ko'rsatish* — admin nimani tuzatayotganini bilmasa, u tasodifan boshqa narsani o'zgartiradi.

**Mexanik darvoza** (§12.4): `cameras.errorCause.{code}` bo'lib `cameras.errorFix.{code}` bo'lmasa — **test yiqiladi**. D-02 shunday qilib taxminga emas, CI'ga bog'lanadi.

### 7.2 Ikkita tone va ularning chegarasi

| Tone | Uslub | Ikonka | Qachon |
|------|-------|--------|--------|
| **`danger`** | `bg-danger/10 text-danger-text` | `AlertCircle` | Sabab **rekvizit yoki qurilmada** — admin uni saytda tuzata olmaydi va amal **bajarilmadi** |
| **`warning`** | `bg-warning/20 text-text` | `AlertTriangle` | Sabab **sozlamada** — admin uni NVR interfeysida yoki tarmog'ida tuzatadi; yoki tashxis **taxminiy** |

> `--color-warning` matn sifatida **ishlatilmaydi**; sariq tintda matn `text-text` (o'lchangan 15.63:1) [MEROS: 02-UI-SPEC §4.2].

**Uchinchi tone yo'q.** `channel_offline` — blok **emas**, u qator badge'i (§6.4).

### 7.3 To'liq xato taksonomiyasi — kod → tone → retry → joy

| `error_code` | Tone | Retry affordansi | Auth qulfi | Ko'rsatiladigan joy |
|--------------|------|------------------|-----------|---------------------|
| `nvr_bad_credentials` | `danger` | ⛔ **YO'Q** | ✅ | Forma / NVR kartasi |
| `nvr_account_locked` | `danger` | ⛔ **YO'Q** + taymer | ✅ | Forma / NVR kartasi |
| `nvr_user_no_permission` | `danger` | ⛔ **YO'Q** | ✅ | Forma / NVR kartasi |
| `nvr_clock_drift` | `warning` | ✅ [Qayta tekshirish] | — | Forma / NVR kartasi |
| `nvr_digest_stale` | `warning` | ✅ [Qayta tekshirish] | — | Forma / NVR kartasi |
| `nvr_auth_mode_basic_only` | `warning` | ✅ [Qayta tekshirish] | — | Forma / NVR kartasi |
| `nvr_unreachable` | `danger` | ✅ [Qayta tekshirish] | — | Forma / NVR kartasi |
| `nvr_isapi_unavailable` | `danger` | ✅ [Qayta tekshirish] | — | Forma |
| `nvr_tls_untrusted` | `warning` | ✅ [Qayta tekshirish] | — | Forma |
| `device_not_supported` | `danger` | ⛔ **YO'Q** (qayta urinish ma'nosiz) | — | Forma |
| `nvr_stream_limit` | `warning` | ✅ [Qayta urinish] | — | Jonli ko'rish dialogi |
| `channel_offline` | — | — | — | **Qator badge'i** (blok emas) |
| Noma'lum kod | `danger` | ✅ [Qayta tekshirish] | — | `errors.generic` + **`error_detail` KO'RSATILMAYDI** |

**Retry affordansining qoidasi bitta jumlada:** *tugma faqat qayta urinish **holatni o'zgartirmaydigan** hollarda ko'rinadi. Autentifikatsiya urinishi holatni o'zgartiradi (qulflanish hisoblagichini oshiradi), shuning uchun u yerda tugma **yo'q**.*

Noma'lum kod → `errors.generic` [MEROS: 02-UI-SPEC — T-02-99: xom `detail`, stack izi yoki SQL matni foydalanuvchiga **hech qachon** ko'rsatilmaydi].

### 7.4 `error_detail` qanday ko'rsatiladi

| Ma'lumot | Ko'rsatilishi |
|----------|---------------|
| `drift_seconds`, `device_time`, `server_time` | Matnga **ICU bilan interpolatsiya**: «…soati server soatidan **{minutes} daqiqa** farq qilyapti» |
| `unlock_at` | Taymer: «Qulf **{time}** dan keyin ochiladi» — har soniyada yangilanadi, `aria-live` **yo'q** |
| `channel_no`, `channel_name` | Matnga interpolatsiya |
| `model` | Matnga interpolatsiya (`device_not_supported`) |
| `raw` (xom RTSP/HTTP javobi) | **`<details>` ichida**, yopiq, `font-mono text-xs`, `<summary>` = «Texnik tafsilot» |

**`<details>` qoidalari:**
- **Faqat `error_detail.raw` mavjud bo'lganda render qilinadi.** Bo'sh `<details>` — shovqin.
- Mazmun **matn sifatida** chiqadi (`whitespace-pre-wrap break-all`), HTML sifatida **hech qachon**.
- Uzunligi **2000 belgidan** kesiladi + «…» — uzun XML sahifani yeb qo'yadi.
- **[TALAB]** backend `error_detail` ni `mask_sensitive` dan o'tkazganini kafolatlaydi [MEROS: 03-RESEARCH §E.15]. UI **maskalamaydi va tekshirmaydi** — u faqat kelgan satrni chizadi. Ikkinchi maskalash qatlami yolg'on xotirjamlik berardi.
- **[TALAB]** `error_detail` faqat ruxsat berilgan kalitlardan iborat bo'lsin (`drift_seconds`, `device_time`, `server_time`, `unlock_at`, `channel_no`, `channel_name`, `model`, `raw`). Noma'lum kalit UI'da **render qilinmaydi**.

### 7.5 «Ehtimol» — hedging kontrakti (D-05)

D-05: *«Xabar "ehtimol sessiya limitiga yetildi" deydi.»*

| Qoida | Amalda |
|-------|--------|
| `nvr_stream_limit` **sabab** matni «Ehtimol» so'zi bilan **boshlanadi** — uchala tilda | uz-Latn «Ehtimol…», ru «Возможно,…», uz-Cyrl «Эҳтимол…» (o'lchangan hosila) |
| Sabab matnining **ikkinchi jumlasi** noaniqlikni ochiq aytadi | «Aniq sabab qurilma javobidan tasdiqlanmadi.» |
| `<details>` **majburiy** | Texnik yordam heuristikani tekshira olsin |
| Tuzatish yo'li **shartli fe'l** bilan | «…yoping va qayta urinib ko'ring» — «tuzatiladi» **emas** |
| **Boshqa hech bir xato kodi «ehtimol» ishlatmaydi** | Hedging arzonlashsa, ma'nosini yo'qotadi. 12 ta koddan faqat **bittasi** hedged |

**Darvoza** (§12.4): `cameras.errorCause.nvr_stream_limit` hedge so'zi bilan boshlanishi **shart**, va boshqa hech bir `errorCause.*` kalitida bu so'z **bo'lmasligi** shart.

### 7.6 Xato paydo bo'lganda fokus va e'lon

| Vaziyat | Xulq |
|---------|------|
| Forma yuborildi → `error_code` keldi | Fokus `NvrErrorBlock` ga (`tabIndex={-1}` + `.focus()`) |
| Blok `role="alert"` | Skrinrider mazmunni **bir marta** to'liq o'qiydi |
| Auth qulfi yoqildi | Blokdan keyingi `role="status"` konteynerda: «Qayta urinishdan oldin login yoki parolni o'zgartiring» |
| Kashfiyot jobi `failed` bilan qaytdi | Fokus **ko'chmaydi** — 60 soniya o'tgan va foydalanuvchi boshqa ish qilayotgan bo'lishi mumkin. `role="alert"` e'lon qiladi |
| Xato yo'qoldi (yangi urinish) | Blok DOM'dan **olib tashlanadi**; bo'sh e'lon qilinmaydi |

---

## 8. Yuza 5 — Jonli ko'rish (CAM-03, SC#6, D-08)

### 8.1 Joyi — dialog, marshrut emas [QAROR]

`ui/dialog.tsx`, `size="lg" sheetOnMobile`.

| Savol | Javob |
|-------|-------|
| Nega marshrut emas? | Marshrutda «oqim qachon to'xtaydi?» savoli **noaniq** qoladi (orqaga bosish? tab yopish?). Dialogda javob bitta va ko'rinadigan: **dialog yopilishi = oqim to'xtashi** |
| Fokus | Radix: tuzoq + `Esc` + yopilganda fokus **bosilgan qator tugmasiga** qaytadi |
| Mobil | `sheetOnMobile` — pastdan chiqadigan varaq; video `aspect-video`; boshqaruvlar ostida, ≥44px |
| Sarlavha | Kamera nomi + kanal raqami — **DB kontenti, tarjima qilinmaydi** |

### 8.2 Yettita holat

| # | Holat | Ramka foni | Nima ko'rinadi | ARIA |
|---|-------|-----------|----------------|------|
| **L0** | `idle` | `bg-surface-muted` | `Video` ikonkasi + «Jonli tasvirni ko'rish» + **[Ko'rish]** tugmasi | — |
| **L1** | `authorizing` | `bg-surface-muted` | Skeleton | `role="status"` «Ruxsat tekshirilmoqda» |
| **L2** | `connecting` | `bg-text` | Skeleton + `text-bg` matn | `role="status"` «Ulanmoqda» |
| **L3** | `playing` | `bg-text` | `<video>` + transport badge'i | `aria-label` = «{nom}, kanal {n} — jonli tasvir» |
| **L4** | `expiring` | `bg-text` | L3 + pastda taymer qatori + **[Davom ettirish]** | `role="status"`, **faqat bir marta** e'lon |
| **L5** | `expired` | `bg-text` | «Ko'rish muddati tugadi» + **[Davom ettirish]** | `role="status"` |
| **L6** | `error` | `bg-text` | `NvrErrorBlock` (ramka **ustida**, `bg-surface` panel sifatida) | `role="alert"` |

**L0 majburiy — oqim avtomatik ochilmaydi** [QAROR]. Dialog ochilishi bilan oqim boshlanmaydi; foydalanuvchi **[Ko'rish]** ni bosishi kerak.

Sabab: go2rtc oqimni **faqat birinchi tomoshabin ulanganda** ochadi va har ochilgan oqim NVR'ning **bitreyt byudjetidan** yeydi [MEROS: 03-RESEARCH §A.5, §D.14]. Dialogni tasodifan ochish NVR sessiyasini ochmasligi kerak. Bitta qo'shimcha bosish — bu narxning to'liq to'lovi.

### 8.3 ⛔ Token va sessiya muddati — D-08 ning UI tarjimasi [QAROR]

D-08: token `exp <= 60s`. Lekin **60 soniyalik token 60 soniyalik ko'rish sessiyasini anglatmaydi** va bu farq aniqlanmasa dala xatosiga aylanadi.

**Nima aslida bo'ladi** [MEROS: 03-RESEARCH §D.13]: nginx `auth_request` tokenni **ulanish paytida** tekshiradi. WebRTC'da signalling bir marta bo'ladi va media UDP 8555 orqali nginx'dan **tashqarida** oqadi — ya'ni ulanish o'rnatilgach sessiya tokendan **uzoqroq yashaydi**. HLS'da esa har segment nginx'dan o'tadi — ya'ni 60 soniyada oqim **uziladi**. Bir xil UI, ikki xil xulq.

**Qaror: token — ULANISH CHIPTASI. Sessiya muddatini UI o'zi belgilaydi.**

| Konstanta | Qiymat | Ma'nosi |
|-----------|--------|---------|
| Token `exp` | **60 s** (D-08, o'zgarmaydi) | Token berilgandan keyin bir necha soniyada iste'mol qilinadi |
| `LIVE_SESSION_MAX_MS` | **300 000** (5 daqiqa) | Bitta ko'rish sessiyasining chegarasi |
| `LIVE_EXPIRY_WARNING_MS` | **30 000** | Tugashdan 30 s oldin L4 holati |
| `LIVE_CONNECT_TIMEOUT_MS` | **15 000** | Ulanish o'rnatilmasa L6 |

**Nega 5 daqiqa** (to'rtta mustaqil sabab):

1. **NVR byudjeti.** Nazoratsiz qolgan jonli ko'rish RTSP sessiyasini **cheksiz** ushlab turadi va A.5 dagi bitreyt chegarasini yeydi. Avtorizatsiyadan qat'i nazar qattiq chegara **kerak**.
2. **Transportlar bir xil ishlaydi.** WebRTC ham, HLS ham 5 daqiqada to'xtaydi — dala nosozligi transportga bog'liq bo'lmaydi.
3. **Avtorizatsiya qayta tekshiriladi.** Har yangilanishda server `CAMERA_VIEW` + `market_id` + kamera mavjudligini **qaytadan** tekshiradi va **yangi `audit_read` qatori** yozadi. D-08 ataylab bekor qilishdan voz kechgan (60 s) — 5 daqiqalik yangilash o'sha xususiyatni saqlagan holda huquq o'zgarishini ushlaydi.
4. **Bo'sh brauzer tunab qolmaydi.** «Davom ettirish» — **odamning aniq harakati**.

**Yangilash mexanikasi:**

| Qadam | Xulq |
|-------|------|
| `t = 4:30` | L4: video davom etadi, pastda qator «Ko'rish {n} soniyadan keyin to'xtaydi» + **[Davom ettirish]**. Modal **emas**, video ustini **to'smaydi** |
| **[Davom ettirish]** bosildi | Yangi token olinadi → pleyer **qayta mount qilinadi** → taymer nolga qaytadi |
| Qayta mount narxi | WebRTC'da ~0.5 s qora kadr. **Bu qabul qilinadi va hujjatlashtiriladi**: 5 daqiqada bir marta bo'ladi va foydalanuvchi oldindan ogohlantirilgan |
| `t = 5:00`, hech narsa bosilmadi | Pleyer **unmount** → L5. `bg-text` fonda `text-bg` matn + **[Davom ettirish]**. **Xato rangi ishlatilmaydi** — bu normal tugash |
| Dialog yopildi | Pleyer darhol unmount; taymer tozalanadi |

> **Nega pleyer «uzilmasdan» yangilanmaydi:** token faqat yangi ulanishga ta'sir qiladi. Eski media sessiyasini saqlab, faqat serverda huquqni tekshirish «yangilandi» degan **yolg'on** hissini berardi — media yo'li aslida eski ruxsat ustida ishlab turardi. Qayta mount — halolroq va u nima bo'layotganini aniq ko'rsatadi.

### 8.4 Transport badge'i — dala diagnostikasi

`playing` holatida video ustining o'ng yuqori burchagida `Badge tone="muted"` `text-xs`: `WebRTC` / `MSE` / `HLS`.

| Qoida | Sabab |
|-------|-------|
| Ko'rsatiladi | Bozorda «tasvir kechikyapti» shikoyati kelganda birinchi savol — qaysi transport ishlayapti. Buni **ko'rsatish** telefon orqali diagnostikani bir bosqichga qisqartiradi [MEROS: 03-RESEARCH §D.13 tavsiyasi] |
| **Aksent rangda EMAS** | Bu holat ko'rsatkichi, harakat emas (§2.4) |
| `aria-label` bilan | «Ulanish turi: {transport}» — qisqartma yolg'iz e'lon qilinmaydi |
| Tarjima qilinmaydi | `WebRTC`/`MSE`/`HLS` — protokol nomlari, uchala tilda bir xil (§11.7 override) |

### 8.5 Ishga tushmagan oqim — L6 va uning sabablari

| Sabab | `error_code` | Ko'rsatiladigan matn |
|-------|--------------|----------------------|
| Ulanish `LIVE_CONNECT_TIMEOUT_MS` ichida o'rnatilmadi | `nvr_stream_limit` (heuristika) | §11.4 — hedged (§7.5) |
| Token endpointi `403` | — | `errors.forbidden` + havola yo'q. **Bu bo'lmasligi kerak** (tugma huquq bilan darvozalangan), lekin rol o'zgargan sessiyada bo'ladi |
| Token endpointi `404` | — | «Bu kamera topilmadi — u arxivlangan bo'lishi mumkin» + **[Ro'yxatni yangilash]** |
| Tarmoq yo'q | — | `errors.network` + **[Qayta urinish]** |

**[Qayta urinish] bu yerda XAVFSIZ** — jonli ko'rish NVR hisobiga autentifikatsiya urinishini **yubormaydi** (u go2rtc'ning allaqachon ochiq sessiyasidan foydalanadi). §4.4 qulfi bu yerga **qo'llanmaydi**.

### 8.6 Ulanmagan kamera — tugma yashirilmaydi, sababi aytiladi

`status !== "online"` bo'lganda:

```tsx
<Button variant="secondary"
        aria-disabled="true"
        aria-describedby={`cam-${id}-offline`}>
  {t("cameras.view")}
</Button>
<span id={`cam-${id}-offline`} className="sr-only">
  {t("cameras.viewDisabledOffline")}
</span>
```

| Qoida | Sabab |
|-------|-------|
| `aria-disabled`, `disabled` **EMAS** | `disabled` tugma fokus olmaydi va skrinrider uni umuman o'qimaydi — «nega bosilmayapti?» savoliga javob qolmaydi [MEROS: 02-UI-SPEC §6.6] |
| Tugma **yashirilmaydi** | Yo'qolgan tugma «bu kamerada ko'rish umuman yo'q» degan yolg'on xabar berardi |
| Bosilganda | Dialog **ochilmaydi**; `role="status"` sababni e'lon qiladi |
| Sabab ko'rinadigan joyda ham bor | Qator meta satrida holat badge'i allaqachon «Ulanmagan» deydi |

### 8.7 Nima HECH QACHON ochilmaydi (D-11, SC#6)

| Narsa | Qoida |
|-------|-------|
| go2rtc HTTP API'si (`/api/streams`, `/api/config`, `/api/restart`) | **Foydalanuvchiga hech qachon** — na to'g'ridan-to'g'ri, na proxy orqali. Frontend bu yo'llarga **hech qanday** so'rov yubormaydi |
| `stream_name` (`cam_<uuid4>`) | UI'da **ko'rsatilmaydi** va nusxa olinmaydi. U faqat token javobidagi opaque URL ichida bo'ladi |
| RTSP URL | UI'da **hech qachon** ko'rsatilmaydi va **hech qachon** kiritilmaydi (D-01) |
| NVR paroli | D-12 — hech qanday ko'rinishda |
| Jonli ko'rish havolasi | URL'ga chiqarilmaydi, ulashish tugmasi **yo'q** |

Frontend'da **grep darvozasi**: `/api/streams`, `exec:`, `ffmpeg:` satrlari `frontend/src` da **bo'lmasligi** shart.

---

## 9. Yuza 6 — Kamerani arxivlash (D-10)

### 9.1 Fe'l — «Arxivlash». «O'chirish» EMAS, hech qaysi tilda

D-10: qattiq `DELETE` **hech qachon** — snapshot va zona bog'lanishlari saqlanishi kerak.

| Til | To'g'ri | ⛔ Taqiqlangan |
|-----|---------|----------------|
| uz-Latn | **Arxivlash** | O'chirish, Olib tashlash |
| ru | **Архивировать** | Удалить, Убрать |
| uz-Cyrl | **Архивлаш** (hosila) | — |

**Darvoza** (§12.4): `frontend/src/components/cameras/` va `cameras.*` kalitlarida `o'chirish` / `удалить` / `delete` so'zlari **bo'lmasligi** mexanik tekshiriladi. Sabab: bu so'z bir marta kirsa, u tarjima orqali tarqaladi va D-10 ni jimgina buzadi.

### 9.2 Tasdiq — 1-daraja, chunki qaytariladi

`ConfirmDialog` `level={1}`, `confirmVariant="destructive"`.

| Savol | Javob |
|-------|-------|
| Nega 2-daraja emas (nom yozib tasdiqlash)? | 2-daraja **faqat UI'dan qaytarib bo'lmaydigan** amallar uchun [MEROS: 02-UI-SPEC §10.6]. Arxivlash **qaytariladi** — «Arxivdan qaytarish» mavjud (§9.3) |
| Nega `destructive` variant (qizil)? | Amal **oqibatli**: kamera ishchi ro'yxatdan chiqadi va 4-fazada undan kadr olinmaydi. 2-fazada «Rastani yopish» ham ma'lumot o'chirmasdan qizil bo'lgan — izchil |
| Qizil «o'chirildi» degan yolg'on bermaydimi? | **Matn** buni to'g'irlaydi: dialog tanasi tarix saqlanishini **aniq** aytadi (§11.5). Rang og'irlikni, matn ma'noni tashiydi |
| Fokus ochilganda | **Bekor qilishda** — hech qachon destruktiv tugmada [KOD: `confirm-dialog.tsx`] |
| Tasdiq tugmasining matni | **«Arxivlash»** — generic «Tasdiqlash» **emas** [MEROS: 02-UI-SPEC §10.6] |

### 9.3 Arxivdan qaytarish — tasdiqsiz

| Qoida | Sabab |
|-------|-------|
| Tasdiq dialogi **YO'Q** | Amal zararsiz: kamera ro'yxatga qaytadi, boshqa hech narsa o'zgarmaydi |
| Toast bilan tasdiqlanadi | «Kamera arxivdan qaytarildi» |
| Ikonka | `ArchiveRestore` |
| Variant | `secondary` |

**Arxivdan qaytarish MAJBURIY mavjud bo'lishi kerak** — usiz arxivlash amalda qaytarib bo'lmaydigan bo'lardi va u holda §9.2 bo'yicha 2-daraja tasdiq talab qilinardi. Mavjudligi arzonroq va mehribonroq.

### 9.4 Qayta skanerlash bilan o'zaro ta'sir (D-10)

> *«Arxivlangan kanal qayta skanda tiklanmaydi (`is_archived` `name_overridden` kabi ishlaydi). Qayta skan hech qachon `DELETE` qilmaydi.»*

Admin buni **bilishi shart**, aks holda u arxivlagan kamerasi qaytib kelishidan qo'rqadi:

| Joy | Matn |
|-----|------|
| Arxivlash tasdiq dialogida | «…qayta skanerlashda u avtomatik qaytmaydi» — dialog tanasining bir qismi |
| Arxivlangan qatorda (`title`) | «Arxivda — qayta skanerlash uni qaytarmaydi» |

---

## 10. Umumiy holat kontrakti — yuklanish / bo'sh / xato

### 10.1 Yuklanish — meros naqsh, yangi variant yo'q

[MEROS: 02-UI-SPEC §9.1 — «Skeleton kontent uchun; matnli `role="status"` amal holatlari uchun»]

| Vaziyat | Naqsh |
|---------|-------|
| Kameralar ro'yxati birinchi marta yuklanmoqda | **3 ta `Skeleton` qatori** (real qator balandligida), konteyner `role="status" aria-busy="true"` + `<span className="sr-only">{t("common.loading")}</span>` |
| NVR kartasi yuklanmoqda | 1 ta `Skeleton` blok |
| Tugma bosildi, so'rov ketdi | Tugma matni almashadi + `aria-disabled` |
| Kashfiyot ishlamoqda (S1/S2) | `Skeleton` + **bosqich matni** (§5.2) |
| Qayta skanerlash — mavjud ro'yxat ustida | Ro'yxat **o'chmaydi**, `aria-busy="true"` oladi (§3.2) |

`motion-reduce:animate-none` — `Skeleton` da allaqachon [KOD: `skeleton.tsx`].

### 10.2 Bo'sh holatlar — to'rttasi, har biri boshqa keyingi qadam bilan

| # | Holat | Keyingi qadam (amal tugmasi) |
|---|-------|------------------------------|
| **E-1** | NVR umuman ulanmagan | **[NVR ulash]** — `variant="default"` (sahifaning yagona birlamchi tugmasi) |
| **E-2** | NVR bor, kamera yo'q (hali skan qilinmagan yoki 0 topilgan) | **[Kameralarni topish]** — `variant="default"` |
| **E-3** | Filtr hech narsa topmadi | **[Filtrlarni tozalash]** — `variant="secondary"` |
| **E-4** | Arxiv ko'rsatilgan, lekin arxivda hech narsa yo'q | Amal **yo'q** — checkbox allaqachon ko'rinadi |

Matnlar §11.6. **E-1 va E-2 hech qachon aralashtirilmaydi** — birinchisida qurilma yo'q, ikkinchisida qurilma bor lekin kanal topilmagan, va bularning keyingi qadami butunlay boshqa.

### 10.3 Xato holati — meros naqsh + domen bloki

| Xato turi | Komponent |
|-----------|-----------|
| Ro'yxat/karta yuklanmadi (tarmoq, 5xx) | Meros bloki: `role="alert"`, `bg-danger/10 text-danger-text`, `errors.loadFailedTitle` + `errors.loadFailedBody` + **[Qayta urinish]** |
| NVR ulanish xatosi (`error_code`) | **`NvrErrorBlock`** (§7) |
| `403` | `errors.forbidden` |
| `404` | `errors.notFound` |
| Noma'lum kod | `errors.generic` — xom `detail` **hech qachon** |

### 10.4 Toast inventarizatsiyasi — beshta, boshqa emas

`sonner`, `position="top-center" richColors` [KOD: `layout.tsx:82`].

| # | Qachon | Matn kaliti |
|---|--------|-------------|
| T-1 | NVR paroli yangilandi | `cameras.toastPasswordUpdated` |
| T-2 | Kamera nomi saqlandi | `cameras.toastNameSaved` |
| T-3 | Kamera arxivlandi | `cameras.toastArchived` |
| T-4 | Kamera arxivdan qaytarildi | `cameras.toastRestored` |
| T-5 | NVR saqlandi (kashfiyot boshlanishidan oldin) | `cameras.toastNvrSaved` |

**Toast QO'YILMAYDIGAN joylar** [QAROR]: kashfiyot tugashi (natija paneli o'zi tasdiq), ulanish testi natijasi (blok o'zi tasdiq), 409 poyga holati (§5.6), jonli ko'rish ochilishi/yopilishi. Sabab: ekranda allaqachon ko'rinadigan natija ustiga toast qo'yish e'tiborni ikkiga bo'ladi.

---

## 11. Copywriting Contract (uz-Latn manba + ru)

> `uz-Cyrl` **avtomatik hosil qilinadi** (`npm run i18n:gen`) — qo'lda yozilmaydi. Qo'lda yoziladigan tillar: **uz-Latn** (manba) va **ru**.
> Quyidagi **barcha** uz-Latn satrlari `transliterate()` dan o'tkazilgan — **0 defekt** [O'LCHANDI: M-10].

### 11.1 Navigatsiya, sarlavha va birlamchi amallar

| Kalit | uz-Latn | ru |
|-------|---------|-----|
| `nav.cameras` | Kameralar | Камеры |
| `cameras.title` | Kameralar | Камеры |
| **`cameras.connectNvr`** | **NVR ulash** | **Подключить NVR** |
| **`cameras.discover`** | **Kameralarni topish** | **Найти камеры** |
| **`cameras.saveAndDiscover`** | **Saqlash va kameralarni topish** | **Сохранить и найти камеры** |
| `cameras.testConnection` | Ulanishni tekshirish | Проверить подключение |
| `cameras.rescan` | Qayta skanerlash | Пересканировать |
| `cameras.updatePassword` | Parolni yangilash | Обновить пароль |
| `cameras.diagnostics` | Diagnostika | Диагностика |
| `cameras.view` | Ko'rish | Смотреть |
| `cameras.rename` | Nomni o'zgartirish | Переименовать |
| `cameras.archive` | Arxivlash | Архивировать |
| `cameras.restore` | Arxivdan qaytarish | Вернуть из архива |
| `cameras.checkStatus` | Holatni tekshirish | Проверить состояние |
| `cameras.retryCheck` | Qayta tekshirish | Проверить снова |
| `cameras.resume` | Davom ettirish | Продолжить |
| `cameras.refreshList` | Ro'yxatni yangilash | Обновить список |
| `cameras.clearFilters` | Filtrlarni tozalash | Сбросить фильтры |

> **`cameras.connectNvr` ru'da `NVR` saqlanadi** [O'LCHANDI: M-4]. «Подключить видеорегистратор» = **3.00×** uzunroq va u mobil pastki panelda ham, karta tugmasida ham ikki qatorga tushardi. `NVR` — o'rnatuvchilar va Hikvision hujjatlari ishlatadigan atama; ruscha tarjima aniqlik qo'shmaydi.

### 11.2 NVR formasi va kartasi

| Kalit | uz-Latn | ru |
|-------|---------|-----|
| `cameras.nvrLegend` | Qurilma ma'lumotlari | Данные устройства |
| `cameras.nvrAddress` | NVR manzili | Адрес NVR |
| `cameras.nvrAddressHint` | Standart port — 80. Boshqa port bo'lsa manzilga qo'shing: 192.168.1.64:8080 | Порт по умолчанию — 80. Если порт другой, добавьте его к адресу: 192.168.1.64:8080 |
| `cameras.nvrLogin` | Foydalanuvchi nomi | Имя пользователя |
| `cameras.nvrPassword` | Parol | Пароль |
| `cameras.showPassword` | Parolni ko'rsatish | Показать пароль |
| `cameras.hidePassword` | Parolni yashirish | Скрыть пароль |
| `cameras.passwordHint` | Parol shifrlangan holda saqlanadi va boshqa hech qachon ko'rsatilmaydi | Пароль хранится в зашифрованном виде и больше никогда не отображается |
| `cameras.deviceFound` | Qurilma topildi | Устройство найдено |
| `cameras.model` | Model | Модель |
| `cameras.deviceType` | Turi | Тип |
| `cameras.channelCount` | Kanallar | Каналы |
| `cameras.channelCountValue` | {count} ta | {count} |
| `cameras.clockDrift` | Soat farqi | Расхождение часов |
| `cameras.clockDriftValue` | {seconds} soniya | {seconds} с |
| `cameras.clockDriftWarning` | Farq katta — hozir ishlaydi, lekin tez orada ulanish uzilishi mumkin | Расхождение велико — сейчас работает, но подключение скоро может прерваться |
| `cameras.nvrCard` | NVR qurilmasi | Устройство NVR |
| `cameras.firmware` | Proshivka | Прошивка |
| `cameras.serial` | Seriya raqami | Серийный номер |
| `cameras.rtspPort` | RTSP porti | Порт RTSP |
| `cameras.rtspPortAssumed` | taxmin qilingan | предположительно |
| `cameras.rtspPortAssumedHint` | RTSP porti aniqlanmadi — 554 deb taxmin qilindi. Kadr olishda muammo bo'lsa portni NVR sozlamalaridan tekshiring | Порт RTSP не определён — предположительно 554. При проблемах с получением кадров проверьте порт в настройках NVR |
| `cameras.lastScan` | Oxirgi skan | Последнее сканирование |
| `cameras.invalidAddress` | Manzil noto'g'ri kiritilgan | Адрес указан неверно |
| `cameras.invalidPort` | Port noto'g'ri | Неверный порт |
| **`cameras.publicAddressBlocked`** | NVR internetga to'g'ridan-to'g'ri ochilmaydi — u WireGuard tunneli ichidagi manzilda bo'lishi kerak | NVR не открывается напрямую в интернет — он должен быть по адресу внутри туннеля WireGuard |
| `cameras.authLockHint` | Qayta urinishdan oldin login yoki parolni o'zgartiring | Прежде чем повторить, измените логин или пароль |

### 11.3 Kashfiyot paneli

| Kalit | uz-Latn | ru |
|-------|---------|-----|
| `cameras.runQueued` | Navbatga qo'yildi | Поставлено в очередь |
| `cameras.runDetecting` | Qurilma aniqlanmoqda… | Определяется устройство… |
| `cameras.runProbing` | {count} ta kanal topildi — oqimlar tekshirilmoqda… | Найдено каналов: {count} — проверяются потоки… |
| `cameras.runStarting` | Boshlanmoqda | Запускается |
| `cameras.runSlowHint` | Sekin tarmoqda bu 1–2 daqiqa davom etishi mumkin | В медленной сети это может занять 1–2 минуты |
| `cameras.runLeaveHint` | Sahifani yopsangiz ham kashfiyot davom etadi | Даже если закрыть страницу, поиск продолжится |
| `cameras.runElapsed` | {seconds} soniya | {seconds} с |
| **`cameras.runDone`** | **Skanerlash yakunlandi** | **Сканирование завершено** |
| `cameras.runAdded` | Yangi qo'shildi | Добавлено новых |
| `cameras.runOffline` | Ulanmagan deb belgilandi | Отмечено как не в сети |
| `cameras.runUnchanged` | O'zgarishsiz | Без изменений |
| **`cameras.runNoChanges`** | **Barcha kanallar avvalgidek — o'zgarish topilmadi.** | **Все каналы как прежде — изменений не найдено.** |
| `cameras.runSomeOffline` | {count} ta kanal hozir ulanmagan — ular ro'yxatda «Ulanmagan» deb turadi | {count} канала сейчас не в сети — в списке они помечены «Не в сети» |
| **`cameras.runTimeout`** | Kashfiyot javob bermayapti — u fonda davom etayotgan bo'lishi mumkin | Поиск не отвечает — возможно, он продолжается в фоне |
| `cameras.runClose` | Yopish | Закрыть |

### 11.4 ⛔ Xato kontrakti — har kod uchun SABAB va TUZATISH

| Kalit | uz-Latn | ru |
|-------|---------|-----|
| `cameras.errorCauseLabel` | Sabab | Причина |
| `cameras.errorFixLabel` | Nima qilish kerak | Что делать |
| `cameras.errorDetails` | Texnik tafsilot | Технические подробности |

**`nvr_bad_credentials`** — `danger`, retry ⛔

| | uz-Latn | ru |
|---|---------|-----|
| `errorCause` | Login yoki parol noto'g'ri. | Неверный логин или пароль. |
| `errorFix` | Login va parolni qayta kiriting. Diqqat: ketma-ket 5 ta xato urinishdan keyin NVR hisobni 30 daqiqaga qulflaydi — shuning uchun avtomatik qayta urinish yo'q. | Введите логин и пароль заново. Внимание: после 5 неудачных попыток подряд NVR блокирует учётную запись на 30 минут — поэтому автоматических повторов нет. |

**`nvr_account_locked`** — `danger`, retry ⛔ + taymer

| | uz-Latn | ru |
|---|---------|-----|
| `errorCause` | NVR hisobi qulflangan — ketma-ket xato urinishlar sababli. Qulf {time} dan keyin ochiladi. | Учётная запись NVR заблокирована из-за неудачных попыток входа. Разблокировка через {time}. |
| `errorFix` | Qulf ochilishini kuting yoki NVR sozlamalarida hisobni qo'lda oching. Qulf ochilgunicha har urinish uni yana uzaytiradi. | Дождитесь разблокировки или снимите её вручную в настройках NVR. Каждая попытка до разблокировки продлевает её. |

**`nvr_user_no_permission`** — `danger`, retry ⛔

| | uz-Latn | ru |
|---|---------|-----|
| `errorCause` | Bu foydalanuvchida NVR qurilmasiga masofaviy kirish huquqi yo'q. | У этого пользователя нет прав удалённого доступа к NVR. |
| `errorFix` | NVR sozlamalarida foydalanuvchiga masofaviy sozlash va jonli ko'rish huquqlarini bering yoki administrator hisobidan foydalaning. | В настройках NVR выдайте пользователю права удалённой настройки и просмотра или используйте учётную запись администратора. |

**`nvr_clock_drift`** — `warning`, retry ✅

| | uz-Latn | ru |
|---|---------|-----|
| `errorCause` | NVR qurilmasining soati server soatidan {minutes} daqiqa farq qilyapti. Farq 5 daqiqadan oshsa qurilma ulanishni rad etadi. | Часы NVR расходятся с часами сервера на {minutes} мин. При расхождении больше 5 минут устройство отклоняет подключение. |
| `errorFix` | NVR sozlamalarida sana va vaqt bo'limini oching, NTP xizmatini yoqing va vaqt mintaqasini Toshkent qilib qo'ying. | В настройках NVR откройте раздел даты и времени, включите службу NTP и задайте часовой пояс Ташкент. |

**`nvr_digest_stale`** — `warning`, retry ✅

| | uz-Latn | ru |
|---|---------|-----|
| `errorCause` | NVR ulanish so'rovini rad etdi — deyarli har doim bu soat farqidan bo'ladi. | NVR отклонил запрос подключения — почти всегда причина в расхождении часов. |
| `errorFix` | NVR sozlamalarida NTP xizmatini yoqing va vaqtni tekshiring, so'ng qayta urinib ko'ring. | Включите службу NTP в настройках NVR, проверьте время и повторите попытку. |

**`nvr_auth_mode_basic_only`** — `warning`, retry ✅

| | uz-Latn | ru |
|---|---------|-----|
| `errorCause` | Qurilma firmware sozlamasi digest autentifikatsiyasini qabul qilmayapti. | Прошивка устройства не принимает digest-аутентификацию. |
| `errorFix` | NVR web-interfeysining xavfsizlik sozlamalarida autentifikatsiya rejimini digest/basic qilib belgilang. | В настройках безопасности веб-интерфейса NVR установите режим аутентификации digest/basic. |

**`nvr_unreachable`** — `danger`, retry ✅

| | uz-Latn | ru |
|---|---------|-----|
| `errorCause` | Manzilga ulanib bo'lmadi — qurilma javob bermayapti. | Не удалось подключиться по адресу — устройство не отвечает. |
| `errorFix` | WireGuard tunneli yoqilganini tekshiring, so'ng manzil va portni tekshiring. Bozor tomonidagi qurilma rozetkada va tarmoqqa ulangan bo'lishi kerak. | Проверьте, что туннель WireGuard включён, затем проверьте адрес и порт. Устройство на стороне рынка должно быть включено в розетку и подключено к сети. |

**`nvr_isapi_unavailable`** — `danger`, retry ✅

| | uz-Latn | ru |
|---|---------|-----|
| `errorCause` | Bu manzilda Hikvision boshqaruv interfeysi topilmadi. | По этому адресу не найден интерфейс управления Hikvision. |
| `errorFix` | Manzil NVR qurilmasining web-portiga tegishli ekanini tekshiring. Kamera yoki router manzili kiritilgan bo'lishi mumkin. | Проверьте, что адрес указывает на веб-порт NVR. Возможно, введён адрес камеры или роутера. |

**`nvr_tls_untrusted`** — `warning`, retry ✅

| | uz-Latn | ru |
|---|---------|-----|
| `errorCause` | Qurilma o'zi imzolagan sertifikat ishlatyapti. | Устройство использует самоподписанный сертификат. |
| `errorFix` | Tunnel ichidagi qurilma uchun bu normal holat. Manzil boshida https o'rniga http yozib ko'ring. | Для устройства внутри туннеля это нормально. Попробуйте указать в начале адреса http вместо https. |

**`device_not_supported`** — `danger`, retry ⛔

| | uz-Latn | ru |
|---|---------|-----|
| `errorCause` | Bu qurilma qo'llab-quvvatlanmaydi: {model}. | Это устройство не поддерживается: {model}. |
| `errorFix` | Hozircha faqat Hikvision qurilmalari ulanadi. Boshqa brend kerak bo'lsa texnik yordamga murojaat qiling. | Пока подключаются только устройства Hikvision. Если нужен другой бренд, обратитесь в техподдержку. |

**`nvr_stream_limit`** — `warning`, retry ✅, **YAGONA hedged kod** (§7.5)

| | uz-Latn | ru |
|---|---------|-----|
| `errorCause` | **Ehtimol** NVR bir vaqtda ochiladigan oqimlar chegarasiga yetgan. Aniq sabab qurilma javobidan tasdiqlanmadi. | **Возможно,** достигнут предел одновременных потоков NVR. Точная причина по ответу устройства не подтверждена. |
| `errorFix` | Boshqa dasturlarda ochiq turgan oqimlarni yoping va qayta urinib ko'ring. Takrorlansa, quyidagi texnik tafsilotni yordam xizmatiga yuboring. | Закройте потоки, открытые в других программах, и повторите попытку. Если повторяется, отправьте технические подробности ниже в службу поддержки. |

**`channel_offline`** — qator badge'i, blok emas

| | uz-Latn | ru |
|---|---------|-----|
| `errorCause` | Kanal {channel} hozir ulanmagan. | Канал {channel} сейчас не в сети. |
| `errorFix` | Kamera quvvatini va kabelni tekshiring, so'ng qayta skanerlang. | Проверьте питание камеры и кабель, затем выполните повторное сканирование. |

### 11.5 Ro'yxat, jonli ko'rish va arxiv

| Kalit | uz-Latn | ru |
|-------|---------|-----|
| `cameras.channel` | Kanal | Канал |
| `cameras.status.online` | Onlayn | В сети |
| `cameras.status.offline` | Ulanmagan | Не в сети |
| `cameras.status.unknown` | Hali tekshirilmagan | Ещё не проверено |
| `cameras.status.archived` | Arxivda | В архиве |
| `cameras.lastSeen` | oxirgi ko'rilgan: {time} | последний раз: {time} |
| `cameras.filterStatus` | Holat | Состояние |
| `cameras.filterAll` | Hammasi | Все |
| `cameras.showArchived` | Arxivlanganlarni ko'rsatish | Показать архивные |
| `cameras.archivedCount` | Arxivda: {count} ta | В архиве: {count} |
| `cameras.nameOverridden` | Nom qo'lda kiritilgan — qayta skanerlashda saqlanadi | Имя задано вручную — сохраняется при пересканировании |
| `cameras.renameHint` | Bu nom qayta skanerlashda saqlanadi — NVR qurilmasidagi nom uni almashtirmaydi | Это имя сохранится при пересканировании — имя с NVR его не заменит |
| `cameras.resetName` | NVR qurilmasidagi nomga qaytarish | Вернуть имя с NVR |
| `cameras.liveTitle` | {name} · kanal {channel} | {name} · канал {channel} |
| `cameras.liveIdle` | Jonli tasvirni ko'rish | Смотреть прямой эфир |
| `cameras.liveAuthorizing` | Ruxsat tekshirilmoqda | Проверяются права |
| `cameras.liveConnecting` | Ulanmoqda | Подключение |
| `cameras.liveLabel` | {name}, kanal {channel} — jonli tasvir | {name}, канал {channel} — прямой эфир |
| `cameras.liveTransport` | Ulanish turi: {transport} | Тип подключения: {transport} |
| `cameras.liveExpiring` | Ko'rish {seconds} soniyadan keyin to'xtaydi | Просмотр остановится через {seconds} с |
| **`cameras.liveExpired`** | **Ko'rish muddati tugadi** | **Время просмотра истекло** |
| `cameras.liveFailed` | Tasvir ochilmadi | Не удалось открыть изображение |
| `cameras.liveNotFound` | Bu kamera topilmadi — u arxivlangan bo'lishi mumkin | Камера не найдена — возможно, она в архиве |
| **`cameras.viewDisabledOffline`** | Bu kamera hozir ulanmagan — jonli tasvir mavjud emas | Камера сейчас не в сети — прямой эфир недоступен |
| **`cameras.archiveTitle`** | **Kamerani arxivlash** | **Архивировать камеру** |
| **`cameras.archiveBody`** | «{name}» (kanal {channel}) ro'yxatdan olib qo'yiladi. Kamera va uning tarixi o'chirilmaydi — qayta skanerlashda u avtomatik qaytmaydi. Istalgan vaqtda arxivdan qaytarishingiz mumkin. | «{name}» (канал {channel}) будет убрана из списка. Камера и её история не удаляются — при пересканировании она не вернётся автоматически. Вы можете вернуть её из архива в любой момент. |
| `cameras.archivedHint` | Arxivda — qayta skanerlash uni qaytarmaydi | В архиве — пересканирование её не вернёт |
| `cameras.toastArchived` | Kamera arxivlandi | Камера архивирована |
| `cameras.toastRestored` | Kamera arxivdan qaytarildi | Камера возвращена из архива |
| `cameras.toastNameSaved` | Nom saqlandi | Имя сохранено |
| `cameras.toastPasswordUpdated` | Parol yangilandi | Пароль обновлён |
| `cameras.toastNvrSaved` | NVR saqlandi | NVR сохранён |

**Usta matnining yangilanishi (U-3):**

| Kalit | uz-Latn | ru |
|-------|---------|-----|
| `wizard.step.cameras` | Kameralar *(«(keyinroq)» olib tashlanadi)* | Камеры |
| **`wizard.cameraNote`** | Kamera bo'limi istalgan vaqtda ulanadi. Bozor hozirdan to'liq ishlaydi: rasta, tarif va kunlik patta hisobi kamerasiz yuritiladi. | Камеры можно подключить в любой момент. Рынок уже полностью работает: торговые места, тарифы и ежедневный учёт сбора ведутся без камер. |

### 11.6 Bo'sh holatlar — to'rttasi

| Kalit | uz-Latn sarlavha / tavsif | ru sarlavha / tavsif |
|-------|---------------------------|----------------------|
| **`cameras.emptyNoNvr`** | **Bu bozorda hali NVR ulanmagan** / Qurilma manzili va login-parolini kiriting — tizim kameralarni o'zi topadi. | **На этом рынке ещё не подключён NVR** / Введите адрес устройства, логин и пароль — система сама найдёт камеры. |
| **`cameras.emptyNoCameras`** | **Kamera hali topilmagan** / «Kameralarni topish» tugmasini bosing — tizim NVR qurilmasidagi barcha kanallarni sanaydi. | **Камеры ещё не найдены** / Нажмите «Найти камеры» — система пересчитает все каналы на NVR. |
| `cameras.emptyFiltered` | **Filtrga mos kamera topilmadi** / Holat filtrini o'zgartiring yoki filtrlarni tozalang. | **Камер по фильтру не найдено** / Измените фильтр состояния или сбросьте фильтры. |
| `cameras.emptyArchived` | **Arxivlangan kamera yo'q** / Arxivlangan kameralar shu yerda ko'rinadi. | **Архивных камер нет** / Архивные камеры появятся здесь. |

### 11.7 ⛔ Transliteratsiya kontrakti — O'LCHANGAN defektlar va majburiy qoidalar

#### Qoida 1 — Lotin akronimga APOSTROFLI qo'shimcha ULANMAYDI [O'LCHANDI: M-2]

Override akronimni tuzatadi, **apostrofli shaklni tuzatmaydi** — u boshqa token:

```
"NVR'ga"  -> "НВРъга"    ❌  (override BOR bo'lsa ham)
"NTP'ni"  -> "НТПъни"    ❌  (override BOR bo'lsa ham)
```

| ❌ Taqiqlangan | ✅ To'g'ri | O'lchangan natija |
|----------------|-----------|-------------------|
| `NVR'ga ulanmadi` | **`NVR qurilmasiga ulanib bo'lmadi`** | `NVR қурилмасига уланиб бўлмади` |
| `NVR'da tekshiring` | **`NVR sozlamalarida tekshiring`** | `NVR созламаларида текширинг` |
| `NVR'ning soati` | **`NVR qurilmasining soati`** | `NVR қурилмасининг соати` |
| `NTP'ni yoqing` | **`NTP xizmatini yoqing`** | `NTP хизматини ёқинг` |
| `RTSP'ni tekshiring` | **`RTSP portini tekshiring`** | `RTSP портини текширинг` |

Bu 2-fazadagi `Excel'dan` qoidasining aynan davomi va u `messages/README.md` ga **Qoida 2** sifatida yoziladi.

#### Qoida 2 — SEMANTIK defekt: sof kirill chiqish ham NOTO'G'RI bo'lishi mumkin [O'LCHANDI]

```
"Asia/Tashkent"        -> "Асиа/Ташкент"          ❌ IANA identifikatori buzildi
"autentifikatsiyasini" -> "аутентификатсиясини"   ❌ to'g'risi "аутентификациясини"
```

**Bu defektni skript tekshiruvi USHLAMAYDI** — chiqishda lotin harfi ham, `ъ` ham yo'q. Shuning uchun:

| ❌ Taqiqlangan | ✅ To'g'ri |
|----------------|-----------|
| `Asia/Tashkent` (IANA identifikatori) | **`Toshkent`** → `Тошкент` |
| `autentifikatsiya` override'siz | **override majburiy** (pastdagi ro'yxat) |

Qoida: **`ts` birikmasi bo'lgan har o'zlashma so'z override talab qiladi** (`ts` → `ц`, `тс` emas). Mavjud lug'atda `protsent`, `protsess`, `litsenziya`, `aktsiya` shu sababdan bor — 3-faza ro'yxatni davom ettiradi.

#### Qoida 3 — `uz-Cyrl.overrides.json` ga qo'shiladigan 20 ta yozuv

```json
"NVR": "NVR",
"NTP": "NTP",
"RTSP": "RTSP",
"ISAPI": "ISAPI",
"IP": "IP",
"VPN": "VPN",
"GMT": "GMT",
"Hikvision": "Hikvision",
"WireGuard": "WireGuard",
"WebRTC": "WebRTC",
"MSE": "MSE",
"HLS": "HLS",
"digest": "digest",
"basic": "basic",
"firmware": "firmware",
"http": "http",
"https": "https",
"web": "веб",
"Web": "Веб",
"autentifikatsiya": "аутентификация",
"autentifikatsiyasini": "аутентификациясини"
```

> **Nega akronimlar kirillga o'girilmaydi** (`NVR` → `НВР` **emas**): admin bu satrni NVR qurilmasining o'z interfeysi bilan solishtiradi va u yerda `NVR`, `NTP`, `RTSP` **lotin yozuvida** turadi. `НВР` foydalanuvchini qurilma bilan bog'lay olmaydigan yangi atama tug'dirardi. Rus tilida ham shu sabab: `NVR` saqlanadi (§11.1).

#### Qoida 4 — `ru` uzunligi [O'LCHANDI: M-4]

O'rtacha nisbat **1.14×**, lekin ayrim kalitlar 1.4–3.0×:

| Kalit | uz-Latn | ru | Nisbat |
|-------|---------|-----|--------|
| `cameras.connectNvr` | NVR ulash (9) | Подключить NVR (14) | **1.56×** |
| `cameras.status.offline` | Ulanmagan (9) | Не в сети (9) | 1.00× |
| `cameras.runUnchanged` | O'zgarishsiz (12) | Без изменений (13) | 1.08× |
| `cameras.archive` | Arxivlash (9) | Архивировать (12) | 1.33× |

Kontrakt [MEROS: 02-UI-SPEC §5.1] o'zgarishsiz: qat'iy kenglik **yo'q**; tugma `whitespace-nowrap` + tabiiy kenglik; qator `flex-wrap`; badge **`truncate` QILINMAYDI** (u ma'no tashiydi) — konteyner o'sadi; faqat **DB kontenti** (kamera nomi, model) `truncate` + `title`.

**3-fazaga xos xavf:** kamera qatorida uchta element bir qatorda turadi (badge + tugma + menyu). Rus tilida `Не в сети` + `Смотреть` = 18 belgi va 360px'da bu tor. Kontrakt: qator `flex-wrap`, badge va amallar **hech qachon** bir-birini siqmaydi — kerak bo'lsa amallar keyingi qatorga tushadi.

#### Qoida 5 — mas'uliyat taqsimoti

| Fayl | Kim yozadi | 3-fazada |
|------|-----------|----------|
| `messages/uz-Latn.json` | **Qo'lda — manba** | ~95 yangi kalit |
| `messages/ru.json` | **Qo'lda** | ~95 yangi kalit (yuqoridagi jadvallarda berilgan) |
| `messages/uz-Cyrl.json` | **Avtomatik** (`npm run i18n:gen`) | Qo'l tegizilmaydi |
| `messages/uz-Cyrl.overrides.json` | **Qo'lda** | 20 ta yangi so'z |

---

## 12. Accessibility Contract

### 12.1 Umumiy talablar

| Talab | Kontrakt | Tekshiruv |
|-------|----------|-----------|
| **Kontrast — matn** | AA 4.5:1. 2-fazada tuzatilgan tokenlar ishlatiladi; yangi juftlik faqat `text-bg` on `bg-text` = **15.6:1** | §2.3 |
| **Kontrast — boshqaruv elementi** | ≥3:1 → `border-border-ui` (3.64:1) barcha `Input`/`Select`/checkbox'da | WCAG 2.2 SC 1.4.11 |
| **Fokus ko'rinishi** | Global `:focus-visible` halqasi; video ustidagi tugmalarda `outline-offset: 2px` + `z-10` | Klaviatura o'tishi UAT |
| **Rang yagona signal emas** | §2.5 jadvali — har holatga ≥2 qo'shimcha kanal | Komponent testi |
| **Nishon o'lchami** | ≥44×44px: qator amallari, parol ko'rsatish tugmasi, checkbox yorlig'i, video boshqaruvlari | §2.1 |
| **Til atributi** | `<html lang>` locale bo'yicha; DB kontenti (kamera nomi) `lang` bilan belgilanMAYDI [MEROS: 1-faza D-16] | — |
| **Harakat** | `prefers-reduced-motion`: Skeleton pulsi o'chadi | `skeleton.tsx` da mavjud |
| **Matn kattalashtirish** | 200% zoom'da layout buzilmaydi; `maximum-scale` **qo'yilmaydi** | §11.7 Qoida 4 |
| **Forma yorliqlari** | Har boshqaruv elementida `<label htmlFor>`; placeholder yorliq o'rnini **bosmaydi** | `Field` primitivі |
| **iOS avtomatik kattalashtirish** | 2-fazadagi `@media (pointer: coarse)` qoidasi kuchda — NVR formasi undan foyda ko'radi | `globals.css` |

### 12.2 `fieldset` / `legend` — guruhlangan kiritmalar

NVR formasi bitta mantiqiy guruh:

```tsx
<Card>
  <CardContent>
    <fieldset className="m-0 border-0 p-0">
      <legend className="mb-4 text-lg font-semibold">
        {t("cameras.nvrLegend")}
      </legend>
      <Field id="nvr-address" label={...} hint={...}>...</Field>
      <Field id="nvr-login"   label={...}>...</Field>
      <Field id="nvr-password" label={...} hint={...}>...</Field>
    </fieldset>
  </CardContent>
</Card>
```

| Qoida | Sabab |
|-------|-------|
| `CardHeader` bu kartada **ishlatilmaydi** | `<legend>` ning o'zi sarlavha — ikkitasi bo'lsa ekranda ham, skrinriderda ham takroriy sarlavha chiqardi |
| `<legend>` **`sr-only` EMAS** | U ko'rinadigan sarlavha; yashirish vizual foydalanuvchini kontekstdan mahrum qilardi |
| `display: contents` **ISHLATILMAYDI** | Ba'zi brauzerlarda `<fieldset>` ning `display` ini o'zgartirish `<legend>` semantikasini buzadi. `border-0 p-0` yetarli |
| Filtr qatori **`fieldset` EMAS** | Ikki mustaqil boshqaruv (Select + checkbox), umumiy yorliq bermaydi. Ularning har biri o'z `<label>` iga ega |

### 12.3 Fokus tartibi va e'lonlar

| Vaziyat | Xulq |
|---------|------|
| Sahifa ochildi, NVR yo'q | Fokus tabiiy tartibda; `autoFocus` **qo'yilmaydi** (2-fazadagi `/stalls` istisnosi bu yerda qo'llanmaydi — bu qidiruv emas) |
| Forma yuborildi, zod yiqildi | Fokus **birinchi noto'g'ri maydonga** (`setFocus`) |
| Forma yuborildi, `error_code` keldi | Fokus **`NvrErrorBlock`** ga (`tabIndex={-1}`) |
| Auth qulfi ostida tugma bosildi | Fokus **parol maydoniga** + `role="status"` e'loni |
| Kashfiyot bosqichi o'zgardi (S1→S2a→S2b→S3) | `role="status"` **faqat bosqich matnini** e'lon qiladi. O'tgan vaqt `aria-hidden` (§5.2) |
| Kashfiyot `failed` | `role="alert"` e'lon qiladi; **fokus ko'chmaydi** (§7.6) |
| Natija paneli chiqdi | `role="status"`; hisoblagichlar `<dl>` bo'lgani uchun «Yangi qo'shildi: 0» juftlik bo'lib eshitiladi |
| Dialog ochildi/yopildi | Radix: tuzoq, `Esc`, fokus **triggerga** qaytadi |
| Tasdiq dialogi ochildi | Fokus **bekor qilishda** — hech qachon destruktiv tugmada |

**Jonli hududlar reyestri** (ikkitadan ortiq bir vaqtda faol bo'lmaydi):

| Hudud | Rol | Nima e'lon qiladi |
|-------|-----|-------------------|
| Kashfiyot paneli | `role="status"` | Bosqich nomi va yakuniy natija |
| Xato bloki | `role="alert"` | Sabab + tuzatish |
| Auth qulfi izohi | `role="status"` | «Qayta urinishdan oldin…» |
| Jonli ko'rish holati | `role="status"` | Ulanmoqda / muddat tugadi |

### 12.4 Video yuzasining a11y'si

| Talab | Kontrakt |
|-------|----------|
| `<video>` | `muted` + `playsInline` + `autoPlay` (foydalanuvchi allaqachon [Ko'rish] ni bosgan) |
| `aria-label` | `cameras.liveLabel` — «{nom}, kanal {kanal} — jonli tasvir» |
| **Subtitr / audio tavsif** | **Talab qilinmaydi va berilmaydi.** Oqim **ovozsiz** va **jonli video-only**. WCAG 1.2.1/1.2.3/1.2.5 **oldindan yozilgan** mediaga tegishli; 1.2.4 **jonli audio** subtitriga tegishli — bu yerda audio yo'q. Kontrakt: audio trek **hech qachon** so'ralmaydi va bu qaror shu yerda hujjatlashtiriladi, aks holda tekshirgich uni buzilish deb belgilardi |
| Matn ekvivalenti | Video **yonida** (dialog sarlavhasi va meta qatorida) kamera nomi, kanal raqami va holati **matn sifatida** turadi |
| Boshqaruvlar | Native `controls` **o'chiriladi** (jonli oqimda `seek`/`speed` ma'nosiz). Yagona boshqaruv — dialogni yopish va [Davom ettirish], ikkalasi ham ≥44px |
| Klaviatura | `Esc` → dialog yopiladi → oqim to'xtaydi. Video elementining o'zi **fokuslanmaydi** (`tabIndex={-1}`) — u interaktiv emas |
| Miltillash | `bg-text` ↔ video o'tishi `transition` **bilan emas**, bir zumda — pulsatsiya yo'q |

### 12.5 Mexanik darvozalar — D-02 va D-10 ni CI'ga bog'lash

Bu fazaning qoidalari **taxminga emas, testga** bog'lanadi:

| # | Darvoza | Fayl | Nimani tekshiradi |
|---|---------|------|-------------------|
| **G-1** | **Sabab↔tuzatish parity** | `scripts/error-codes.test.mjs` (kengaytiriladi) | Har `cameras.errorCause.{code}` uchun `cameras.errorFix.{code}` **uchala tilda** mavjud. **D-02 ning mexanik shakli** |
| **G-2** | **Kod qamrovi** | `scripts/error-codes.test.mjs` | Backend'dagi har `NVR_ERROR_CODES` yozuvi uchun `lib/nvr-errors.ts` da `case` bor |
| **G-3** | **Hedging yagonaligi** | Yangi `scripts/nvr-copy.test.mjs` | `errorCause.nvr_stream_limit` hedge so'zi bilan **boshlanadi**; boshqa hech bir `errorCause.*` da bu so'z **yo'q** (D-05) |
| **G-4** | **«O'chirish» taqig'i** | `scripts/nvr-copy.test.mjs` | `cameras.*` kalitlarida `o'chirish`/`удалить` **yo'q** (D-10) |
| **G-5** | **Transliterator regressiyasi** | `scripts/gen-cyrillic.test.mjs` (kengaytiriladi) | §11.7 dagi 5 ta holat: `NVR qurilmasiga`, `NTP xizmatini`, `WireGuard`, `digest/basic`, `autentifikatsiyasini` — kutilgan kirill chiqishiga teng |
| **G-6** | **go2rtc yuzasi taqig'i** | `scripts/nvr-copy.test.mjs` | `frontend/src` da `/api/streams`, `exec:`, `ffmpeg:` satrlari **yo'q** (D-11) |
| **G-7** | **Vendored pleyer yaxlitligi** | `scripts/vendor-integrity.test.mjs` (yangi) | `public/vendor/go2rtc/video-stream.js` SHA-256 yozib qo'yilgan qiymatga teng (§14.2) |
| **G-8** | **RBAC ko'zgusi** | Mavjud `scripts/role-gate.test.mjs` | `lib/rbac.ts` va `rbac.py` matritsalari mos (`camera_view`, `camera_manage`) |

---

## 13. Component Inventory

### 13.1 Wave 0 — yangi ekranlardan OLDIN (bloklovchi)

| # | Ish | Fayl | Nega bloklovchi |
|---|-----|------|-----------------|
| **W0-1** | **RBAC ko'zgusi**: `PERMISSIONS` ga `"camera_manage"`; `platform_admin` ga `camera_view` + `camera_manage`; `market_admin` ga `camera_manage`. `director` — faqat `camera_view` (o'qish roli, D-07) | `lib/rbac.ts` | [O'LCHANDI: M-8] `platform_admin` da `camera_view` **yo'q** → self-service qoidasi bo'yicha aynan **platforma admini** bozorni ulaydi va kameralarni **ko'rishi kerak**. Bu 2-fazadagi Pitfall 6 ning takrori (D-15) |
| **W0-2** | `NAV_ITEMS` + `href`/`labelKey` literal union'lari | `shell/app-shell.tsx` | Usiz sahifa navigatsiyadan **yetib bo'lmaydi** |
| **W0-3** | `uz-Cyrl.overrides.json` — 20 ta yangi yozuv | `messages/uz-Cyrl.overrides.json` | Usiz **birinchi** kirill build'i buzuq matn chiqaradi (§11.7) |
| **W0-4** | `gen-cyrillic.test.mjs` — 5 ta yangi assertion | `scripts/` | Darvoza G-5 |
| **W0-5** | `error-codes.test.mjs` — cause/fix parity | `scripts/` | Darvoza G-1 — **D-02 ning mexanik shakli** |
| **W0-6** | `nvr-copy.test.mjs` — yangi fayl | `scripts/` | Darvozalar G-3, G-4, G-6 |
| **W0-7** | Vendored pleyer + SHA-256 + `vendor-integrity.test.mjs` | `public/vendor/go2rtc/`, `scripts/` | Darvoza G-7 (§14.2) |

> **W0-1 `rbac.py` bilan JUFT bajariladi.** `lib/rbac.ts` fayl boshidagi izoh ikki matritsa qo'lda sinxron saqlanishini talab qiladi [KOD: `rbac.ts:1-18`]. Faqat frontend tomonini o'zgartirish tugmani ko'rsatib, so'rovni 403 ga uchratardi.

### 13.2 Qayta ishlatiladigan komponentlar — o'zgarishsiz

`Button`, `Card`, `CardContent`, `Input`, `Field`, `Select`, `Badge`, `Skeleton`, `EmptyState`, `Dialog` (+`Dialog.Footer`, `Dialog.Close`), `ConfirmDialog`, `DropdownMenu` naqshi, `cn()`, `sonner`, `Link` (`@/i18n/navigation`).

**Birortasi ham o'zgartirilmaydi.**

### 13.3 Kengaytiriladigan mavjud fayllar

| Fayl | O'zgarish |
|------|-----------|
| `lib/rbac.ts` | W0-1 |
| `shell/app-shell.tsx` | W0-2 |
| `wizard/wizard-steps.ts` | U-1 — `CAMERA_PLACEHOLDER` ga `href` |
| `wizard/wizard-stepper.tsx` | U-2 — kamera elementi havolaga aylanadi |
| `wizard/activation-panel.tsx` | U-3 — kamera qatori havola + sanoq |
| `messages/{uz-Latn,ru}.json` | ~95 kalit |
| `messages/uz-Cyrl.overrides.json` | 20 so'z |
| `scripts/{gen-cyrillic,error-codes}.test.mjs` | Darvozalar |

### 13.4 Yangi komponentlar

| Yo'l | Vazifa | Client? |
|------|--------|---------|
| `app/[locale]/(app)/cameras/page.tsx` | Sahifa qobig'i, uch zona, RBAC darvozasi | ✅ |
| `components/cameras/nvr-form.tsx` | §4 — `fieldset` + 3 maydon + 2 tugma | ✅ |
| `components/cameras/nvr-card.tsx` | §4.6 — qurilma xulosasi + amallar | ✅ |
| `components/cameras/nvr-test-result.tsx` | §4.5 — muvaffaqiyatli tekshiruv bloki | — |
| `components/cameras/nvr-error-block.tsx` | §7 — sabab + tuzatish + tone + retry + `<details>` | — |
| `components/cameras/discovery-panel.tsx` | §5.2 — S1…S5 holatlari + poll | ✅ |
| `components/cameras/discovery-result.tsx` | §6.3 — uch hisoblagich (`<dl>`) | — |
| `components/cameras/camera-list.tsx` | §6.1 — filtr + `<ul>` | ✅ |
| `components/cameras/camera-row.tsx` | §6.1 — bitta qator + amallar menyusi | ✅ |
| `components/cameras/camera-status-badge.tsx` | §2.5 — rang + ikonka + matn | — |
| `components/cameras/camera-rename-dialog.tsx` | §6.5 | ✅ |
| `components/cameras/archive-camera-dialog.tsx` | §9 — `ConfirmDialog` o'ramasi | ✅ |
| `components/cameras/live-view-dialog.tsx` | §8 — L0…L6 + sessiya taymeri | ✅ |
| `components/cameras/live-player.tsx` | §8 — vendored `video-stream` web-komponenti o'ramasi | ✅ |
| `lib/nvr-errors.ts` | `nvrErrorView(code) → {causeKey, fixKey, tone, retrySafe, authLocking}` | — |
| `lib/camera-queries.ts` | So'rovlar, mutatsiyalar, poll, `queryKey` fabrikalar | — |
| `lib/use-nvr-auth-lock.ts` | §4.4 — auth qulfi hooki | ✅ |
| `public/vendor/go2rtc/video-stream.js` | Vendored pleyer (§1.4.1) | — |
| `public/vendor/go2rtc/video-stream.js.sha256` | Yaxlitlik darvozasi (§14.2) | — |

> **`lib/nvr-errors.ts` nega `market-errors.ts` ga qo'shilmaydi:** `marketErrorMessageKey` **bitta** kalit qaytaradi; NVR xatosi esa **beshta** qiymat qaytaradi (`causeKey`, `fixKey`, `tone`, `retrySafe`, `authLocking`). Turli shakl — turli modul. Bu 2-fazadagi `market-errors.ts` ni `queries.ts` dan ajratish qarorining aynan bir xil mantiqi [KOD: `market-errors.ts:4-30`].

### 13.5 Test fayllari (komponent darajasi)

| Fayl | Nimani isbotlaydi |
|------|-------------------|
| `nvr-form.test.tsx` | Manzil ajratish jadvali (§4.1); auth qulfi tugmalarni bloklashi va **faqat** rekvizit o'zgarganda ochilishi (§4.4) |
| `nvr-error-block.test.tsx` | Har kod uchun cause **va** fix render bo'lishi; `AUTH_LOCKING_CODES` da retry tugmasi **render bo'lmasligi**; noma'lum kodda `error_detail` **chiqmasligi** |
| `discovery-result.test.tsx` | Uchala nol holatida uchala hisoblagich **va** «o'zgarish topilmadi» jumlasi ko'rinishi (§6.3) |
| `discovery-panel.test.tsx` | S2a→S2b o'tishi; 180 s dan keyin poll **to'xtashi** |
| `live-view-dialog.test.tsx` | Dialog ochilishida oqim **boshlanmasligi** (L0); 5 daqiqada L5 ga o'tishi; yopilganda pleyer **unmount** bo'lishi |
| `camera-row.test.tsx` | `status !== "online"` da «Ko'rish» `aria-disabled` + sabab; arxivlangan qatorda «Ko'rish» **umuman yo'q** |

---

## 14. Registry Safety

### 14.1 shadcn va uchinchi tomon registrlari

| Registry | Ishlatilgan bloklar | Safety Gate |
|----------|---------------------|-------------|
| shadcn (rasmiy) | — | **Qo'llanmaydi** — `components.json` yo'q, shadcn init bajarilmadi (§1.3) |
| Uchinchi tomon registrlari | **YO'Q** | **Qo'llanmaydi** — birorta uchinchi tomon registri e'lon qilinmadi |

**`npx shadcn add` bu fazada ishlatilmaydi.** Barcha komponentlar mavjud bog'liqliklar ustida qo'lda yoziladi va kod-ko'rikdan o'tadi. **Yangi npm paketi qo'shilmaydi** (§1.4).

### 14.2 Vendored artefakt darvozasi — go2rtc pleyeri [YANGI]

Bu fazada **birinchi marta** uchinchi tomon kodi bundlga kiradi. Registry darvozasi qo'llanmasa ham, **ekvivalent darvoza** qo'yiladi:

| Band | Talab |
|------|-------|
| **Manba** | `AlexxIT/go2rtc`, teg **`v1.9.14`**, fayl `www/video-stream.js`. Boshqa teg yoki `master` **qabul qilinmaydi** |
| **Litsenziya** | **MIT.** Fayl boshidagi litsenziya izohi **saqlanadi**; olib tashlanmaydi |
| **Yaxlitlik** | `public/vendor/go2rtc/video-stream.js.sha256` da SHA-256 saqlanadi; **G-7** testi har CI'da tekshiradi |
| **Ko'rik** | Fayl birinchi kiritilganda **to'liq o'qib chiqiladi** va PR'da quyidagi naqshlar bo'yicha tekshiriladi: `eval(`, `new Function`, `fetch(` (o'z originidan tashqari), `document.write`, obfuskatsiya |
| **Yangilash** | Faqat go2rtc versiyasi CLAUDE.md da o'zgarganda; yangilash **alohida PR**, diff **to'liq o'qiladi**, SHA-256 yangilanadi |
| **Yozuv** | Ushbu bo'lim yangilash sanasi va tekshiruv natijasi bilan to'ldiriladi (quyidagi jadval) |

| Sana | Versiya | SHA-256 | Ko'rik natijasi |
|------|---------|---------|-----------------|
| *(reja bajarilishida to'ldiriladi)* | v1.9.14 | *(hisoblanadi)* | *(to'ldiriladi)* |

> ⚠ **Bu jadval `gsd-executor` tomonidan to'ldiriladi.** Bo'sh qolgan holda G-7 testi yiqiladi va faza tugallanmagan hisoblanadi.

---

## 15. Scope Fence — bu fazada BO'LMAYDIGAN UI

[MEROS: 03-RESEARCH §Scope Fence + 03-CONTEXT `<domain>`]

| Kelajak imkoniyati | Faza | 3-fazada aynan nima qilinadi | Nima QILINMAYDI |
|--------------------|------|-------------------------------|------------------|
| **Snapshot jadvali va mavsumiy profil** | **4** | **Hech narsa** | Jadval formasi, vaqt slotlari, mavsum tanlagichi |
| **Kadr olish, sifat filtri, `light_mode`** | 4 | Hech narsa | Kadr ko'rinishi, sifat ko'rsatkichi |
| **Kamera thumbnail'i ro'yxatda** | 4 | Hech narsa | Ro'yxatda rasm — qator **faqat matn** |
| **S3 / SeaweedFS arxiv ko'rinishi** | 4 | Hech narsa | — |
| **Telegram alertlar** | 4 | `nvr_discovery_runs.error_code` — alert manbai **tayyor** | Alert sozlamalari ekrani |
| **Kamera-zona poligonlari** | **5** | **Faqat `cameras.id` barqarorligi** — arxivlash `DELETE` qilmagani uchun avtomatik | Poligon muharriri, canvas, `react-konva` |
| **CV natijalari, band/bo'sh** | 5 | Hech narsa | — |
| **PTZ boshqaruvi** | v2 | Hech narsa | Video ustida yo'nalish tugmalari |
| **Kamera hodisalari (motion)** | v2 | Hech narsa | — |
| **Jonli tasvirni yozib olish** | Qurilmaydi | Hech narsa | Yozish tugmasi, arxiv pleyeri |
| **Bir nechta NVR bitta bozorda** | Sxema qo'llaydi | UI'da **bitta** (§3.1) | NVR ro'yxati marshruti, NVR tanlagichi |
| **WireGuard peer'larini UI'dan boshqarish** | v2 | Hech narsa (`tunnel_subnet` — ops fayli) | Tunnel sozlamalari ekrani |
| **ONVIF / Dahua / boshqa brend** | v2 | Hech narsa | Brend tanlagichi — forma **brendni so'ramaydi** |
| **NVR manzilini tahrirlash** | 4+ | Hech narsa (§4.6) | Manzil tahrirlash formasi |
| **Kameraning `resolution`/`codec` ko'rsatilishi** | 4 | Hech narsa | Qatorda texnik xarakteristika |
| **Kamerani qattiq o'chirish** | **Hech qachon** (D-10) | Hech narsa | «O'chirish» tugmasi — **G-4 darvozasi bilan taqiqlangan** |
| **Ko'p tilli DB kontenti** | — | Qurilmaydi (1-faza D-16) | Kamera nomini tarjima qilish |

**Erta optimizatsiya deb baholangan va QILINMAYDIGAN «ilgaklar»:** kamera guruhlash/teglar (5-faza zonalari bu ehtiyojni yopadi), ro'yxat virtualizatsiyasi (≤32 qator), umumiy `<AsyncJobPanel>` abstraktsiyasi (bitta iste'molchi — 4-fazada ikkinchisi kelganda ajratiladi), dark mode tokenlari, Storybook.

---

## 16. Open Questions

Bu subagent kontekstida foydalanuvchiga savol berish vositasi yo'q. Quyidagilar **taxmin qilinib jimgina qulflanmadi** — ular ochiq qoldiriladi va reja/UAT bosqichida hal qilinadi. **Har biri uchun ishlaydigan standart qiymat tanlangan** — rejalashtirish javob kutib to'xtamaydi.

| # | Savol | Bilamiz | Noaniq | Tanlangan standart |
|---|-------|---------|--------|--------------------|
| **O-01** | 5 daqiqalik jonli ko'rish sessiyasi (§8.3) direktor uchun **yetarlimi**? | D-08 tokenni 60 s qilib qulflagan; NVR bitreyt byudjeti qattiq chegara talab qiladi | Nizo tekshiruvida direktor 5 daqiqadan uzoq qarab turadimi | **5 daqiqa + [Davom ettirish]**. Qiymat `LIVE_SESSION_MAX_MS` konstantasi — o'zgartirish **bitta qator**. UAT'da o'lchansin |
| **O-02** | `channels_found` ni erta yozish (§5.2 [TALAB]) worker'da **arzonmi**? | Bir marta `UPDATE` | Worker tranzaksiya chegaralari qanday qo'yilgani rejaga bog'liq | Talab **saqlanadi**. Agar qimmat bo'lsa, S2b holati o'chadi va panel S2a'da qoladi — UI **yiqilmaydi**, faqat kamroq ma'lumot beradi |
| **O-03** | 409 javobida `run_id` (§5.6 [TALAB]) — backend buni **beradimi**? | Qisman unique indeks 409 tug'diradi | Javob tanasining shakli hali yozilmagan | Talab **saqlanadi**. Zaxira: UI `GET .../discovery-runs?active=true` bilan topadi (bitta qo'shimcha so'rov) |
| **O-04** | Vendored `video-stream.js` **qaysi transportni** Karmana tarmog'ida tanlaydi? | WebRTC UDP 8555 to'g'ridan-to'g'ri kerak; MSE proxy'dan o'tadi | Bozor DSL'i / CGNAT UDP'ni bloklaydimi | Avtomatik tushish **o'zgartirilmaydi**; §8.4 transport badge'i buni **dala'da o'lchanadigan** qiladi. Bu O-04 ning javobini UAT'dan olib keladi |
| **O-05** | «Ulanmagan» (`offline`) atamasi ru'da `Не в сети` **to'g'rimi** Karmana kontekstida? | §11.5 da taklif qilindi | Ona tilida so'zlashuvchi ko'rigi bo'lmadi | **`Не в сети`** ishlatiladi; 8-fazadagi «uch tilli interfeys yakuniy tekshiruvi» mezoniga kiritilsin (2-fazadagi O-07 bilan bir xil yo'l) |
| **O-06** | Kamera bo'limi **kassir**ga kerakmi? | `camera_view` kassirda **yo'q** [KOD: `rbac.ts`] | 6-fazada kassir «rasta band ekanini ko'rsin» talabi paydo bo'lishi mumkin | Kassirga **berilmaydi**. 6-fazada kerak bo'lsa, bu **rasta kartasidagi dalil-rasm** bo'ladi (2-faza §7.6 dagi `children` ilgagi), butun kamera bo'limi emas |

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

*Phase: 03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi*
*UI-SPEC yaratildi: 2026-08-03 — `gsd-ui-researcher`*
*Upstream: 03-CONTEXT.md (D-01…D-17), 03-RESEARCH.md (§A, §B, §D, §E), 02-UI-SPEC.md (dizayn tizimi, i18n, a11y kontrakti), ROADMAP Phase 3 (SC#1–SC#8), CLAUDE.md*
