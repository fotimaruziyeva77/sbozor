---
phase: 03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi
plan: 10
subsystem: frontend-kamera-yuzasi
tags: [ui, poll, idempotentlik, a11y, webrtc, vendored-artifact, soft-delete, nuqs, wave-9]

# Dependency graph
requires:
  - phase: 03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi
    plan: 09
    provides: "`/cameras` sahifasi (uch zona), `NvrErrorBlock`, `NvrCard`, `camera-page-state.ts`"
  - phase: 03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi
    plan: 08
    provides: "`camera-queries.ts` ning 9 hooki va oltita konstantasi, vendored pleyer + G-7, 132 `cameras.*` satri"
  - phase: 03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi
    plan: 07
    provides: "`POST /cameras/{id}/live-token` (opaque `url`), `archive`/`restore`, `live_view_unavailable`"
  - phase: 03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi
    plan: 06
    provides: "`discovery-runs` poll javobi va `channels_found` ning erta yozilishi (S2a->S2b)"
provides:
  - "`discovery-result.tsx` — uch hisoblagich NOL BILAN BIRGA; anti-«buzuq ko'rinadi» jumlasi (SC#2 ning UI isboti)"
  - "`discovery-panel.tsx` — S1…S5, `discoveryStageOf()` sof funksiyasi, poll 180 s da to'xtaydi"
  - "`camera-list.tsx` — to'rtlik holat, `nuqs` filtrlari, arxiv sanog'i"
  - "`camera-row.tsx` + `camera-status-badge.tsx` — uch signal kanali; ulanmagan va arxivlangan ATAYIN farqlanadi"
  - "`archive-camera-dialog.tsx` / `camera-rename-dialog.tsx` — D-10 va §6.5"
  - "`live-view-dialog.tsx` — L0…L6, `liveStageOf()`, 5 daqiqalik sessiya chegarasi"
  - "`live-player.tsx` — vendored pleyer o'ramasi + `applyPlayerPolicy()` (tashqi STUN yo'q, audio yo'q)"
  - "`NvrCard.showErrorBlock` — bir xil xato ikki joyda chizilmaydi"
affects: [03-11-yakuniy-darvoza, 04-snapshot-pipeline]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Vaqtga bog'langan HAR QANDAY UI qarori SOF FUNKSIYAGA chiqariladi (`discoveryStageOf`, `liveStageOf`): chegarani testda soatni ushlab turmasdan o'lchash mumkin bo'ladi va qaror TanStack/React ning ichki shakliga qadalmaydi"
    - "Uchinchi tomon kodining XAVFSIZLIK SOZLAMASI o'zi ham SOF FUNKSIYA (`applyPlayerPolicy`) — «izohda yozilgan qoida» emas, birlik testi bilan o'lchanadigan da'vo"
    - "«Prop o'zgarganda holatni tozalash» EFFEKTDA emas, MONTAJ CHEGARASIDA: `key={id}` yoki holatni dialog bolasiga ko'chirish. React Compiler shaklni dikta qiladi va natija to'g'riroq chiqadi"
    - "Sinxron `expect(mock).not.toHaveBeenCalled()` async yo'lda YOLG'ON YASHIL beradi — chaqiruv bir mikrotask narida bo'lishi mumkin. «Bu chaqiruv umuman bo'lmadi» da'vosi taymer bo'shatilgandan KEYIN tekshiriladi"
    - "Bir xil `queryKey` — bir xil kesh yozuvi: sahifa yugurish natijasini panelga PROP bilan uzatmaydi, o'sha hookni o'zi chaqiradi va TanStack so'rovni deduplikatsiya qiladi"

key-files:
  created:
    - frontend/src/components/cameras/discovery-result.tsx
    - frontend/src/components/cameras/discovery-result.test.tsx
    - frontend/src/components/cameras/discovery-panel.tsx
    - frontend/src/components/cameras/discovery-panel.test.tsx
    - frontend/src/components/cameras/camera-status-badge.tsx
    - frontend/src/components/cameras/camera-row.tsx
    - frontend/src/components/cameras/camera-row.test.tsx
    - frontend/src/components/cameras/camera-list.tsx
    - frontend/src/components/cameras/archive-camera-dialog.tsx
    - frontend/src/components/cameras/camera-rename-dialog.tsx
    - frontend/src/components/cameras/live-player.tsx
    - frontend/src/components/cameras/live-view-dialog.tsx
    - frontend/src/components/cameras/live-view-dialog.test.tsx
  modified:
    - frontend/src/app/[locale]/(app)/cameras/page.tsx
    - frontend/src/components/cameras/nvr-card.tsx
    - frontend/messages/uz-Latn.json
    - frontend/messages/ru.json
    - frontend/messages/uz-Cyrl.json

key-decisions:
  - "«O'zgarish topilmadi» jumlasining sharti `added === 0 && offline === 0`, «uchala nol» EMAS. Rejaning `<action>` bandi va `<behavior>` bandi bir-biriga ZID edi; harfma-harf «uchala nol» jumlani faqat `channels_found === 0` da (kanalsiz NVR) chiqarardi — ya'ni ishlab turgan 6 kanalli NVR ning IDEMPOTENT qayta skani aynan «hech narsa qilmadi» ko'rinishida qolardi. Tanlangan shart rejaning IKKALA da'vosini ham qamraydi"
  - "`discoveryStageOf` `started_at` YO'Q bo'lganda MONTAJ LAHZASIDAN hisoblaydi. Usiz birinchi javob umuman kelmagan holatda chegaraning boshlanish nuqtasi bo'lmasdi va panel S1 da MANGU qotib qolardi — «tugamasligi mumkin bo'lgan spinner» ning aynan o'zi, eng ehtimolli nosozlikda"
  - "Ulanmagan kameraning «Ko'rish» tugmasi IKKI SHOX bilan yozildi (bloklangan va faol), bitta elementdagi uchta ternary bilan emas. Ikkala tugmaning atributi ham, handleri ham, ma'nosi ham boshqa; ochiq bo'lish o'qilishliroq va `\\bdisabled=\\{` mezonini LITERAL 0 bilan bajaradi (03-09 da bu mumkin emas edi)"
  - "`NvrCard` ga `showErrorBlock` propi qo'shildi: kashfiyot yugurishining nosozligini PANEL chizadi (§5.2 S4), karta esa faqat QULFNI oladi. Ikkala joyda ham chizish bir xil matnni takrorlab, ikkita `role=\"alert\"` hududini bir vaqtda faol qilardi (§12.3)"
  - "Arxiv sanog'i MUSTAQIL so'rov bilan olinadi. Muqobil variant (har doim arxiv bilan so'rab klientda filtrlash) bitta so'rovni tejab, AUDIT IZINI buzardi: `camera-queries.ts` «checkbox ataylab yoqildi» va «umuman tegilmadi» ni ikki xil hodisa deb ataydi va bu farq `audit_log.new_value.filters` da ko'rinadi"
  - "Pleyerning ikki majburiy sozlamasi SOF FUNKSIYAGA (`applyPlayerPolicy`) chiqarildi va uchta birlik testi bilan qamraldi. 03-08 ularni «03-10 uchun majburiy band» deb qoldirgan edi; izohda qolganda ular keyingi refaktorda jimgina yo'qolardi"
  - "Sessiya holati `Dialog.Content` ning BOLASIDA yashaydi: yopilganda Radix uni portaldan chiqaradi, ya'ni «dialog yopilishi = oqim to'xtashi» kafolati STRUKTURAVIY bo'ladi. `open` ni effektda kuzatish React Compiler qoidasiga urilardi va «yopildi, lekin oqim hali tirik» oynasini ochiq qoldirardi"
  - "`live-player.tsx` transportni vendored qobiqning `.mode` BO'LAGIDAN o'qiydi, `video-rtc.js` ning ichki holatidan EMAS: ichki holat keyingi versiyada jimgina uzilardi, `.mode` esa qobiqning e'lon qilingan GUI yuzasi"

patterns-established:
  - "Pattern: sabotaj FAQAT «qaysi test qizardi» ni emas, «assert TO'G'RI joyda qizardimi» ni ham o'lchaydi. S3 birinchi yugurishda kutilgan testni qizartirdi, LEKIN noto'g'ri assertda — da'vo async yo'lda o'lchanmagan edi"
  - "Pattern: qabul mezonining grep naqshi KOD BILAN ZIDDIYATGA kirganda niyat bajariladi, o'lchov yoziladi va TUZATILGAN naqsh 03-11 ga qayd etiladi (bu fazada sakkizinchi–o'ninchi holat)"
  - "Pattern: vitest TIPLARNI TEKSHIRMAYDI — obyekt argumentidan tushib qolgan maydon testda `undefined` bo'lib ishlaydi va faqat `tsc --noEmit` ushlaydi. Har task oxirida typecheck MAJBURIY, test yashilligi yetarli emas"

requirements-completed: []

# Metrics
duration: 70min
completed: 2026-08-03
---

# Phase 3 Plan 10: Kashfiyot paneli, kameralar ro'yxati va jonli ko'rish Summary

**Hech narsa o'zgarmagan skan endi buzuq skandan ekranda farqlanadi (uchala hisoblagich nol bilan birga ko'rinadi va anti-«buzuq ko'rinadi» jumlasi chiqadi), kashfiyot 180 soniyada to'xtaydi, kamerani yo'q qilish yo'li umuman yo'q — faqat arxivlash, va jonli ko'rish faqat aniq bosishdan keyin ochilib besh daqiqada tugaydi, tashqi STUN'siz va ovozsiz.**

## Performance

- **Duration:** ~70 min
- **Tasks:** 3/3 (beshta commit — sabab «Rejadagi ziddiyatlar» B bandida)
- **Files:** 18 (13 yangi, 5 o'zgargan), 3824 qator qo'shildi
- **Sabotajlar:** 3 ta (har biri commit'dan keyin, `git checkout -- <aniq fayl>` bilan tiklandi)

## Accomplishments

- **SC#2 ning UI isboti ekranga chiqdi va U MUSTAQIL O'LCHANADI:** sabotaj (nol qatorni yashirish) **4** testni qizartirdi va jumla testlarini yashil qoldirdi — ya'ni «hisoblagichlar ko'rinadi» va «jumla chiqadi» ikki mustaqil da'vo.
- **Fazaning uchala oxirgi yuzasi ham SAHIFAGA ULANDI:** 03-09 ning ikkita ochiq stubi (zona B va zona C) yopildi.
- **03-08 ning ikki majburiy sozlamasi bajarildi VA testga bog'landi:** tashqi STUN ro'yxati bo'shatildi, audio umuman so'ralmaydi.
- **Vitest 177 → 246** (+69). Node darvozalari **86** (o'zgarmadi), i18n **574 → 576** kalit × 3 til.
- **Yangi npm paketi qo'shilmadi** (T-03-SC): `package.json` va `package-lock.json` diffi **bo'sh**.
- **`npm run gate` exit 0 — 950 s.**

## Task Commits

1. **Kashfiyot paneli va uch hisoblagichli natija (reja Task 1)** — `142eb4b` (feat)
2. **Kamera qatori, holat badge'i va ikki dialog (reja Task 2, 1-yarim)** — `2427784` (feat)
3. **Jonli ko'rish dialogi va vendored pleyer (reja Task 3)** — `4814fd0` (feat)
4. **L0 assertini mikrotaskdan keyingi holga keltirish (sabotaj S3 ning natijasi)** — `f1280e9` (test)
5. **Kameralar ro'yxati va uch zonaning ulanishi (reja Task 2, 2-yarim)** — `cea9de1` (feat)

## Files Created/Modified

| Fayl | Nima qiladi |
|---|---|
| `cameras/discovery-result.tsx` | Uch hisoblagich `<dl>` ichida, NOL BILAN BIRGA; `runNoChanges()`; `role="status"`; qisman muvaffaqiyat qatori |
| `cameras/discovery-panel.tsx` | `discoveryStageOf()` (S1…S5), `elapsedLabel()`, poll chegarasi, S5 neytral rangda |
| `cameras/camera-status-badge.tsx` | Rang + ikonka + matn; arxiv statusdan ustun; `truncate` **yo'q** |
| `cameras/camera-row.tsx` | Ikki xonali kanal, `name_overridden`, `last_seen_at`; bloklangan va faol «Ko'rish» — ikki shox |
| `cameras/camera-list.tsx` | To'rtlik holat, `nuqs` filtrlari, arxiv sanog'i, uch dialog, arxivdan qaytarish |
| `cameras/archive-camera-dialog.tsx` | `ConfirmDialog level={1}`, fe'l «Arxivlash», tarix saqlanishi matnda |
| `cameras/camera-rename-dialog.tsx` | `key` bilan montaj qilinadigan forma, hint, NVR nomiga qaytarish |
| `cameras/live-player.tsx` | `applyPlayerPolicy()`, skript o'z originimizdan, `.mode` dan transport |
| `cameras/live-view-dialog.tsx` | `liveStageOf()` (L0…L6), sessiya taymeri, qayta mount, ramka fokusi |
| `app/…/cameras/page.tsx` | Zona (B) va (C) ulandi; failed yugurish kodi kartaga QULF uchun |
| `cameras/nvr-card.tsx` | `showErrorBlock` propi (standart `true` — 03-09 xulqi saqlandi) |
| `messages/{uz-Latn,ru,uz-Cyrl}.json` | `cameras.actions`, `cameras.nameLabel` |

## Sabotajlar — nima qizardi VA nima yashil qoldi

| # | Sabotaj | Qizardi | **Yashil qoldi** | Ma'nosi |
|---|---|---|---|---|
| **S1** | `discovery-result.tsx` da nol qiymatli hisoblagich yashirildi (`value > 0 ? … : null`) | `discovery-result.test.tsx` — **4**: «uchala nol holatida uchalasi render bo'ladi», «idempotent qayta skan (0/0/6)», «`<dl>` bilan dasturiy bog'langan», «`added > 0` da jumla chiqmaydi» | Uchala **jumla** testi, sarlavha/rol testlari, sof funksiya testlari, **20 ta `discovery-panel` testi** | ⚠ Reja **1** ta qizarishni bashorat qilgan edi, o'lchov **4** berdi. Muhimi ikkinchi ustun: «jumla chiqadi» testlari YASHIL qoldi — ya'ni SC#2 ning ikki belgisi (hisoblagichlar va jumla) bir-biridan MUSTAQIL o'lchanadi |
| **S2** | `camera-row.tsx` da `status !== "online"` da «Ko'rish» butunlay render qilinmadi | `camera-row.test.tsx` — **AYNAN 3**: «yashirilmaydi va sababi bilan bog'lanadi», «bosilganda dialog ochilmaydi», «`unknown` ham bloklanadi» | **Uchala arxiv testi** («Ko'rish umuman yo'q», «faqat qaytarish», «badge Arxivda»), kanal formati, `name_overridden`, `truncate`, meta qatori | ⚠ Rejaning bashorati **aynan tasdiqlandi**: ikki holat («ulanmagan» va «arxivlangan») ATAYIN farqlanadi va ular alohida o'lchanadi. Bitta qoidaga yig'ilsa qaysi biri tanlansa ham bittasi noto'g'ri chiqardi |
| **S3** | `live-view-dialog.tsx` da dialog ochilishi bilan `startSession()` chaqirildi (L0 chetlab o'tildi) | `live-view-dialog.test.tsx` — **8** (butun DOM guruhi) | **12 ta SOF FUNKSIYA testi**: `liveStageOf` (7) va `applyPlayerPolicy` (5) | ⚠ **Ikki topilma.** (1) Sessiya taymeri va pleyerning xavfsizlik sozlamalari L0 qaroridan **mustaqil** o'lchanadi — reja shuni kutgan edi. (2) **BIRINCHI yugurishda L0 testi NOTO'G'RI assertda qizardi**: `expect(apiFetch).not.toHaveBeenCalled()` **o'tib ketdi**, chunki avtomatik boshlanish so'rovni keyingi mikrotaskka qoldiradi. Da'vo tuzatildi (commit `f1280e9`) va takrorlangan sabotaj endi AYNAN `apiFetch` assertida qizaradi |

Uchala sabotaj ham commit'dan **keyin** bajarildi va `git checkout -- <aniq fayl>` bilan tiklandi; har tiklanish testlar bilan tasdiqlandi va ish daraxti toza qoldi.

## O'lchangan dalillar

### SC#2 — hech narsa o'zgarmagan skan (natija paneli)

| Holat (`added` / `offline` / `unchanged`) | Uchala hisoblagich | «O'zgarish topilmadi» jumlasi |
|---|---|---|
| 0 / 0 / 0 | ✅ ko'rinadi | ✅ chiqadi |
| **0 / 0 / 6** (idempotent qayta skan) | ✅ ko'rinadi | ✅ chiqadi |
| 6 / 0 / 0 | ✅ ko'rinadi | ✅ **chiqmaydi** |
| 0 / 2 / 6 | ✅ ko'rinadi | ✅ **chiqmaydi** (o'rniga «2 ta kanal hozir ulanmagan…») |

`channels_found` **sanab chiqilgan** kanallarni bildiradi (oflayn ham) — bu formula alohida test bilan qulflandi: `0 / 2 / 6` holatida `unchanged = 6`, `4` emas.

### Kashfiyot poll'i

| Da'vo | O'lchov |
|---|---|
| S2a → S2b `channels_found` yozilishi bilan almashadi | DOM testi: «Qurilma aniqlanmoqda…» → «6 ta kanal topildi…» |
| `channels_found === 0` S2b ga o'tkazmaydi | Sof funksiya testi (ma'nosiz matn oldi olindi) |
| 180 s da poll **to'xtaydi** | Qotib qolgan yugurishda S5 chiqadi va soat +30 s surilganda **yangi so'rov ketmaydi** (`apiFetch` sanog'i o'zgarmaydi) |
| Terminal holatda poll to'xtaydi | `succeeded` javobidan keyin +20 s da sanoq o'zgarmaydi |
| Terminal holat timeout'dan **ustun** | Sof funksiya testi: 30 daqiqa o'tgan `succeeded` baribir natija panelini beradi |
| `started_at` yo'q bo'lsa ham S5 ga yetadi | Sof funksiya testi (montaj lahzasidan) |
| O'tgan vaqt e'lon **qilinmaydi** | `aria-hidden="true"` elementda; 5 s dan oldin umuman yo'q |
| S5 xato **emas** | `role="status"`, `role="alert"` DOM'da **yo'q** |

### Jonli ko'rish (CAM-03, SC#6, T-03-69)

| Da'vo | O'lchov |
|---|---|
| **Dialog ochilishida token so'ralmaydi** | Taymer bo'shatilgandan keyin `apiFetch` **0 marta**; pleyer mount sanog'i **0** |
| [Ko'rish] chipta oladi va pleyerni montaj qiladi | `apiFetch` **1**, `mounts` **1**, `url` — opaque satr |
| 5 daqiqada pleyer **unmount** | `queryByTestId("live-player")` → `null`; `role="alert"` yo'q (xato rangi ishlatilmaydi) |
| L4 videoni **to'smaydi** | Ogohlantirish qatori chiqqanda pleyer HAMON DOM'da |
| [Davom ettirish] **qayta mount** qiladi | `apiFetch` **2**, `mounts` **2** — «uzilmasdan yangilash» emasligining yagona isboti |
| Dialog yopilganda pleyer darhol unmount | `open={false}` dan keyin `null` |
| Sessiya chegarasi **avtorizatsiyadan qat'i nazar** | Sof funksiya: `connecting` holatida ham 5 daqiqada `expired` |
| Oqim identifikatori DOM'da **yo'q** | `body.textContent` da opaque satrning bo'lagi ham, to'liq `url` ham yo'q; `queryByRole("link")` → `null` |
| `grep -rn "stream_name\|streamName" components/cameras/` | **0** |

### Vendored pleyerning ikki majburiy sozlamasi (03-08 dan meros)

| Sozlama | Standart (upstream) | Bizda | O'lchov |
|---|---|---|---|
| ICE serverlari | `stun.cloudflare.com`, `stun.l.google.com` | **bo'sh ro'yxat** | `iceServers` `[]` **va** serializatsiyada `stun:` satri **yo'q** |
| So'raladigan media | video **va ovoz** | **faqat video** | `media === "video"`; `audio`/`microphone` satrlari yo'q |
| Ko'rinmayotgan oqim | (kelajakda o'zgarishi mumkin) | ushlab turilmaydi | `background === false`, `visibilityCheck === true` |
| Skript manbai | — | **o'z originimiz** | `/vendor/go2rtc/video-stream.js`, `https?:` bilan boshlanmaydi |

### Arxivlash (D-10)

| Da'vo | O'lchov |
|---|---|
| Fe'l hech qaysi tilda «yo'q qilish» emas | G-4 yashil (576 kalit × 3 til + `components/cameras/` ning 13 fayli) |
| Tasdiq 1-darajali va fe'li o'z nomi bilan | `level={1}`, tugma matni `cameras.archive` |
| Qayta skan qaytarmasligi **matnda** aytiladi | `cameras.archiveBody` uch bandni sanaydi |
| Arxivlangan qatorda «Ko'rish» **umuman yo'q** | Rol bo'yicha ham, `body.textContent` bo'yicha ham |
| Arxivdan qaytarish tasdiqsiz | Bosish → mutatsiya + toast |

### Bazaviy darvoza

| Bosqich | Natija |
|---|---|
| `ruff check` + `format --check` + `mypy` | ✅ (backend **TEGILMADI**) |
| `pytest -q` | ✅ **1448** (o'zgarmadi) |
| `pytest tests/tenancy -q` | ✅ **412** (o'zgarmadi) |
| `npm run test:sim` | ✅ **61** (o'zgarmadi) |
| `npm --prefix frontend run i18n:check` | ✅ **576 kalit × 3 til** (574 → 576) |
| frontend node testlari | ✅ **86** (o'zgarmadi) |
| frontend vitest | ✅ **246** (177 → 246) |
| frontend typecheck / lint / build | ✅ toza / toza / `/[locale]/cameras` uchala tilda prerender |
| `git diff frontend/package{,-lock}.json` | ✅ **bo'sh** (T-03-SC) |
| `grep -rnE "/api/streams\|exec:\|ffmpeg:" frontend/src` | ✅ **0** (G-6) |
| **`npm run gate`** | ✅ **exit 0 — 15 daq 50 s (950 s), «issiq» yugurish** |

⚠ **Darvoza vaqti 676 s → 950 s (+274 s).** O'sish frontendda: vitest **177 → 246** (+69, ularning bir qismi soxta taymer bilan ishlaydigan DOM testlari) va uning ustiga to'liq `next build`. Bu 03-01 ning 618 s nomzod chegarasidan **ikkinchi marta** oshdi va farq endi sezilarli. **03-11 uchun aniq band:** chegarani qayta o'lchash va «sovuq»/«issiq» yugurishni ajratish (03-08 dan meros, 03-09 da takrorlangan) — aks holda u fazani yopishda yolg'on-qizil beradi.

### Transliteratsiya (ikki yangi kalit)

| uz-Latn | uz-Cyrl (hosila) |
|---|---|
| `Amallar` | `Амаллар` ✅ |
| `Kamera nomi` | `Камера номи` ✅ |

Buzuq shakl (`ъ`, lotin harfi, `ts` defekti) — yo'q; override talab qilinmadi.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Xato] `discoveryStageOf` chaqiruvidan `status` maydoni tushib qolgan edi**

- **Found during:** Task 1, birinchi DOM test yugurishi
- **Issue:** Panel bosqich funksiyasiga `status` ni **umuman uzatmagan** edi va panel har doim «Navbatga qo'yildi» da qotib qolardi. ⚠ **Vitest buni ko'rmadi va ko'rmasligi ham kerak edi:** u esbuild bilan tiplarni **olib tashlaydi**, tekshirmaydi — yetishmagan maydon `undefined` bo'lib ishladi. Faqat `tsc --noEmit` uni xato deb belgilaydi.
- **Fix:** `status: run?.status` qo'shildi. Qoida qayd etildi: **har task oxirida typecheck majburiy, test yashilligi yetarli emas.**
- **Files modified:** `discovery-panel.tsx`
- **Commit:** `142eb4b`

**2. [Rule 1 — Xato] G-4 darvozasi O'Z izohim ustida qizardi**

- **Found during:** Task 2, `node --test scripts/nvr-copy.test.mjs`
- **Issue:** `archive-camera-dialog.tsx` ning izohida taqiqlangan HTTP metodining nomi **literal** yozilgan edi («Qattiq `DELETE` marshruti backendда yo'q»). Naqsh `\bdelete\b` ni ikki tomonlama so'z chegarasi bilan qidiradi va `-`/backtick so'z belgisi emas, ya'ni u ushlanadi. Jumlaning O'ZI D-10 ni **tushuntirardi**. Bu fazada takrorlangan sinfning **sakkizinchi** holati; `camera-queries.ts` dagi bir xil jumla darvozadan faqat `src/lib/` da yashagani uchun o'tadi.
- **Fix:** Izoh qayta yozildi («qaytarib bo'lmaydigan yo'q qilish marshruti … YOZILMAGAN») va chegara izohning o'zida qayd etildi. Darvoza **o'zgartirilmadi** — u to'g'ri ishlayapti.
- **Files modified:** `archive-camera-dialog.tsx`
- **Commit:** `2427784`

**3. [Rule 2 — Yetishmayotgan kritik funksiya] L0 da'vosi mikrotaskdan keyin o'lchanadigan qilindi**

- **Found during:** Sabotaj S3
- **Issue:** «Dialog ochilishida token so'ralmaydi» — bu rejaning va T-03-69 ning markaziy da'vosi. Sinxron `expect(apiFetch).not.toHaveBeenCalled()` esa L0 **chetlab o'tilgan** holatda ham **o'tib ketdi**: avtomatik boshlanish `setPhase()` ni sinxron bajarib, so'rovni keyingi mikrotaskka qoldiradi. Ya'ni test noto'g'ri sababdan (matn topilmadi) qizarardi va sabotaj olib tashlangach yana yashil bo'lardi — da'vo o'lchanmagan hisoblanadi.
- **Fix:** Assert taymer bo'shatilgandan **keyin** tekshiriladi va yoniga `playerMock.mounts === 0` qo'shildi. Takrorlangan sabotaj endi AYNAN `apiFetch` assertida qizaradi (`been called 1 times`).
- **Files modified:** `live-view-dialog.test.tsx`
- **Commit:** `f1280e9`

**4. [Rule 2 — Yetishmayotgan kritik funksiya] `started_at` yo'q holatining chegarasi**

- **Found during:** Task 1, `discoveryStageOf` ning tartibini yozganda
- **Issue:** Vaqt chegarasi yugurishning `started_at` iga tayanadi (03-08 ning qarori, va u to'g'ri). Lekin `started_at` **birinchi muvaffaqiyatli javob** bilan keladi. So'rov osilib qolsa (`failureCount` ham oshmaydi) chegaraning boshlanish nuqtasi umuman bo'lmasdi va panel S1 da **mangu** qotib qolardi — «kashfiyot hech qachon tugamasligi mumkin bo'lgan spinner ko'rinishida bo'lmaydi» qoidasi aynan eng ehtimolli nosozlikda buzilardi.
- **Fix:** `startedAt === null` bo'lganda **montaj lahzasi** olinadi. Alohida test bilan qamraldi.
- **Files modified:** `discovery-panel.tsx`, `discovery-panel.test.tsx`
- **Commit:** `142eb4b`

**5. [Rule 1 — Xato] Bir xil xato ikki joyda chizilardi**

- **Found during:** Task 2 ning ikkinchi yarmi, zona (A) va (B) ni birga ulaganda
- **Issue:** Kashfiyot `failed` bilan qaytganda PANEL `NvrErrorBlock` chizadi (§5.2 S4), `NvrCard` esa `errorCode` prop kelishi bilan **o'z nusxasini** chizadi. Natija: bir xil matn ikki marta va **ikkita `role="alert"`** hududi bir vaqtda faol — §12.3 «ikkitadan ortiq bo'lmaydi» qoidasining buzilishi.
- **Fix:** `NvrCard` ga `showErrorBlock` propi (standart `true` — 03-09 xulqi **o'zgarmadi**). Sahifa uni `false` qiladi; karta **qulfni** baribir oladi, ya'ni «Qayta skanerlash» tugmasi `nvr_bad_credentials` dan keyin bloklanadi (D-03).
- **Files modified:** `nvr-card.tsx`, `page.tsx`
- **Commit:** `cea9de1`

**6. [Rule 2 — Yetishmayotgan kritik funksiya] Zona (B) va zona (C) sahifaga ULANDI**

- **Found during:** Task 2 ning ikkinchi yarmi
- **Issue:** Rejaning `files_modified` ro'yxatida `page.tsx` **yo'q**, lekin usiz uchala yangi yuza ham **yetib bo'lmaydigan** kod bo'lib qolardi: 03-09 zona (B) va (C) ni ochiq stub deb qoldirgan va ularni yopish 03-10 ning zimmasiga yozilgan edi. Yuzalarni ulamasdan «faza tugadi» deyish tekshirgich uchun ham stub bo'lardi.
- **Fix:** Zona (B) — `DiscoveryPanel` (`?run=` tekshirilgan qiymat bilan); zona (C) — `CameraList`. Sahifadagi `CameraListZone` yordamchi komponenti (03-09 ning vaqtinchalik shakli) **olib tashlandi**, uning qarori `camera-list.tsx` ga ko'chdi. `LoadFailed` bloki qurilma zonasi uchun qoldi.
- **Files modified:** `page.tsx`, `camera-list.tsx`
- **Commit:** `cea9de1`

**7. [Rule 3 — Bloklovchi] React Compiler qoidalari UCH shaklni dikta qildi**

- **Found during:** Task 2 va Task 3, `npm run lint`
- **Issue:** (a) `camera-rename-dialog.tsx` — maydonni effektda `setState` bilan to'ldirish; (b) `live-view-dialog.tsx` — `open` o'zgarganda effektda holatni tozalash; (c) `live-player.tsx` — callback `ref` ini **render paytida** yangilash (`react-hooks/refs`).
- **Fix:** (a) forma `key={camera.id}` bilan montaj qilinadigan alohida komponentga chiqarildi — bu ayni paytda **haqiqiy xatoni ham** yopdi: so'rov fonda qayta yuklanganda yangi obyekt havolasi admin **terayotgan** matnni bosib ketardi; (b) sessiya holati `Dialog.Content` ning bolasiga ko'chirildi, ya'ni yopilish = to'liq unmount va «yopildi, lekin oqim tirik» oynasi **strukturaviy** ravishda yo'q; (c) `ref` effektda yangilanadi, boshlang'ich qiymat `useRef` ning o'zida.
- **Files modified:** `camera-rename-dialog.tsx`, `live-view-dialog.tsx`, `live-player.tsx`
- **Commits:** `2427784`, `4814fd0`

**8. [Rule 2 — Yetishmayotgan kritik funksiya] Ikki matn kaliti qo'shildi**

- **Found during:** Task 2
- **Issue:** Amallar menyusining `aria-label` i va nom maydonining `<label>` i uchun kalit yo'q edi. `users.actions` ni kamera yuzasida ishlatish ikki domenni bog'lab qo'yardi.
- **Fix:** `cameras.actions` va `cameras.nameLabel` uz-Latn va ru'ga qo'lda, uz-Cyrl'ga `npm run i18n:gen` bilan. Transliteratsiya toza (`Амаллар`, `Камера номи`).
- **Files modified:** `messages/{uz-Latn,ru,uz-Cyrl}.json`
- **Commit:** `2427784`

### Rejadagi ziddiyatlar (NIYAT bajarildi, literal emas)

**A. «Uchala nol» sharti O'Z ICHIDA zid edi.**

Rejaning `<action>` bandi jumlani «uchala hisoblagich nol bo'lganda» talab qiladi. Rejaning `<behavior>` bandi va UI-SPEC §6.3 ning **eskizi** esa AYNAN `added=0, offline=0, unchanged=6` holatida shu jumlani ko'rsatadi. Ikkalasi bir vaqtda faqat bitta shakl bilan bajariladi: **`added === 0 && offline === 0`**.

Bu shakl semantik jihatdan ham to'g'ri — `unchanged` **o'zgarish emas**, uning teskarisi. Harfma-harf «uchala nol» jumlani faqat `channels_found === 0` bo'lganda (NVR'da umuman kanal yo'q) chiqarardi, ya'ni **ishlab turgan 6 kanalli NVR ning idempotent qayta skani aynan «hech narsa qilmadi» ko'rinishida qolardi** — reja maqsadining va SC#2 ning teskarisi.

**O'lchov:** ikkala holat ham alohida test bilan qulflandi (`0/0/0` va `0/0/6` — ikkalasida jumla **bor**; `6/0/0` va `0/2/6` — ikkalasida **yo'q**).

**B. Task 2 IKKI COMMITGA bo'lindi va tartib 1 → 2a → 3 → 2b bo'ldi.**

`camera-list.tsx` uchala dialogni ham (nom, arxiv, **jonli ko'rish**) iste'mol qiladi, ya'ni Task 3 dan **oldin** yozib bo'lmasdi: birinchi commit mavjud bo'lmagan modulga murojaat qilardi va build yiqilardi. Muqobil — vaqtinchalik zaglushka — keyingi commitda butunlay almashtirilardi. Bu 03-09 dagi bilan aynan bir xil sabab va aynan bir xil yechim.

**C. `grep -cE "\bcontrols\b" live-player.tsx` = 0 mezoni BAJARILMAS.**

Vendored qobiq `oninit()` da native boshqaruvlarni **yoqib qo'yadi**. §12.4 ularni **o'chirishni** talab qiladi, va o'chirishning yagona yo'li — o'sha xususiyatni **nomi bilan** yozish. Ya'ni mezon o'zi talab qilgan qoidani bajaradigan yagona qatorni taqiqlaydi. Mezonni harfma-harf bajarish uchun nomni hisoblab qurish (`"cont" + "rols"`) kerak bo'lardi — 03-09 obfuskatsiyani ochiq rad etgan.

**O'lchov:** rejaning naqshi bilan **1** (aynan o'sha bitta enforcing qator), `<video controls>` shaklidagi JSX esa **0**. **03-11 uchun tuzatilgan naqsh:** `grep -cE "controls\s*=\s*true|<video[^>]*\bcontrols\b"` = 0.

**D. `grep -c "stream_name\|streamName" frontend/src/components/cameras/` — mezon KATALOG ustida.**

`grep -c` katalogga qo'llanganda xato qaytaradi (`-r` yo'q). Niyat aniq va u `grep -rn … | wc -l` bilan o'lchandi: **0**.

**E. `tabIndex={-1}` `live-view-dialog.tsx` da — LEKIN video elementida emas.**

`<video>` elementini vendored qobiq **imperativ** yaratadi, ya'ni uni JSX'da `tabIndex={-1}` bilan belgilash printsipial ravishda mumkin emas (u `live-player.tsx` da `video.tabIndex = -1` bilan qo'yiladi). Dialogdagi `tabIndex={-1}` esa **haqiqiy ehtiyojga** berildi: `[Davom ettirish]` bosilganda o'sha tugmaning o'zi DOM'dan chiqadi va fokus `body` ga tushib, foydalanuvchi dialogdan «tashqarida» qolardi. Ramka dasturiy fokusni qabul qiladi, fokus **tartibiga** esa kirmaydi.

**F. `grep -cE "\bdisabled=\{" camera-row.tsx` = 0 — bu safar LITERAL bajarildi.**

03-09 da bu mezon bajarilmas edi (`aria-disabled={…}` naqshga tushardi). Bu yerda bloklangan va faol «Ko'rish» **ikki shox** bilan yozildi va ARIA atributi **satr literali** (`aria-disabled="true"`) bo'lgani uchun naqsh unga umuman tegmaydi. **O'lchov: rejaning naqshi bilan 0, tuzatilgan naqsh `(^|[^-])\bdisabled=\{` bilan ham 0.** Ikki shox obfuskatsiya emas — ular boshqa-boshqa handler, atribut va ma'noga ega.

### Rejadan ataylab chetlangan bandlar

**G. TDD RED/GREEN commitlari ajratilmadi.** Uchala task ham `tdd="true"`, `.planning/config.json` da esa `workflow.tdd_mode: false`. Faza konventsiyasi (03-02…03-09) — har task uchun bitta commit. **RED dalili yo'qolmadi:** uchala sabotaj darvozalarning kodsiz qizarishini (va S3 da — noto'g'ri assertda qizarishini) o'lchov bilan ko'rsatadi.

**H. `requirements mark-complete` ATAYIN bajarilmadi.** Frontmatterda `requirements: [CAM-03, CAM-08]` bor. CAM-03 (jonli ko'rish) va CAM-08 ning ekran tomoni shu rejada yopildi, lekin faza mezonlari 03-11 da yakunlanadi va 03-01…03-09 ning hech biri belgilamagan. Belgilash **03-11** ning zimmasida — aks holda REQUIREMENTS.md yarim holatda qolardi.

**I. `Go2rtcClient.remove_stream` chaqirilmadi — va bu ATAYIN.** Bu reja **faqat frontend**: server kodi umuman tegilmadi. Qoldiq ta'sir **chegaralangan va o'lchangan**: `POST /cameras/{id}/live-token` arxivlangan kamerada **404** qaytaradi (`cameras.py:431`), ya'ni arxivlangandan keyin go2rtc'da **yangi oqim ochilmaydi**; faqat oldindan ro'yxatga olingan oqim servis qayta ishga tushgunicha qolishi mumkin. Server tomonidagi tozalash — **03-11 yoki 4-faza**.

---

**Total deviations:** 8 auto-fixed (2 × Rule 1 + 1 × Rule 1, 4 × Rule 2, 1 × Rule 3 — jami 3 × Rule 1, 4 × Rule 2, 1 × Rule 3) + 6 ta rejadagi ziddiyat + 3 ta hujjatlashtirilgan chetlanish
**Impact on plan:** Scope creep yo'q. To'rtala Rule 2 tuzatishi ham **qoidaning jimgina buzilish yo'lini** yopdi (o'lchanmagan L0 da'vosi, mangu poll, ulanmagan yuzalar, yetishmagan kalitlar); Rule 1 tuzatishlari ikkita haqiqiy xatoni (`status` maydoni, ikkilangan xato bloki) va bitta darvoza-ziddiyatini tuzatdi.

## Issues Encountered

1. **Vitest tiplarni tekshirmaydi va bu «hammasi yashil» hisobotini YOLG'ON qiladi.** `discoveryStageOf` ga `status` uzatilmagani DOM testini qizartirdi, lekin sabab test xabaridan **ko'rinmadi** — panel shunchaki boshqa bosqichda edi. Xatoni `tsc --noEmit` ochdi. Bu sinf 03-08 dagi «`.test.ts` fayl jimgina ishga tushmaydi» ning qo'shnisi: **darvoza mavjud, lekin u boshqa narsani o'lchaydi.**
2. **Sabotaj noto'g'ri assertda qizarishi mumkin va bu YASHIRIN nosozlik.** S3 birinchi yugurishda «kutilgan test qizardi» degan xulosa berardi — holbuki da'voning O'ZI o'lchanmagan edi. Endi sabotaj hisobotiga «qaysi assertda qizardi» ustuni ham kiritildi.
3. **React Compiler qoidalari UCHINCHI va TO'RTINCHI marta shakl dikta qildi** (03-08: poll, 03-09: taymer, bu yerda: dialog holati va callback refi). To'rtala holatda ham majburiy qayta loyihalash natijani **yaxshiladi** — bu yerda eng qimmatlisi: sessiya holati dialog bolasiga ko'chgach, «yopildi, lekin oqim hali tirik» oynasi **strukturaviy ravishda** yo'q bo'ldi.
4. **`grep`-ziddiyat sinfi bu rejada UCH marta uchradi** (G-4 ning `DELETE` i, `\bcontrols\b`, katalog ustidagi `grep -c`) va bittasi **teskari yo'nalishda** hal bo'ldi: `\bdisabled=\{` bu safar hech qanday murosasiz **literal 0** chiqdi.

## Known Stubs

| Joy | Stub | Nega bu fazada yetarli | Kim yopadi |
|---|---|---|---|
| `cameraEmptyKind` ning `archived` shoxi | `camera-list.tsx` `archivedOnly: false` uzatadi | Checkbox faqat `archivedCount > 0` da render qilinadi, ya'ni «arxivni ko'rsat» yoqilgan bo'lsa kamida bitta arxivlangan kamera **bor** — E-4 bu yuzada yetib bo'lmaydigan holat. Qaror sof funksiyada qoldi va kelajakdagi «faqat arxiv» ko'rinishi uni to'ldiradi | Kerak bo'lsa — 4-faza |
| `live-player.tsx` ning brauzer yo'li | jsdom `WebSocket` va `RTCPeerConnection` bermaydi, shuning uchun ulanish yo'li **komponent testi bilan qamralmagan** | Xavfsizlik qarori (`applyPlayerPolicy`) va transport xaritasi (`transportOf`) sof funksiya sifatida **to'liq** o'lchanadi; qolgani — vendored kodning o'zi (SHA-256 bilan qulflangan) va u brauzerda tekshiriladi | **03-VALIDATION** ning inson bandi (real NVR / simulyator bilan) |
| `setup-status.cameras` sanog'i | hamon `—` (03-08 dan meros) | Backend maydonni har doim `0` qaytaradi | 03-11 yoki 4-faza |

## Threat Flags

Yangi ishonch chegarasi **ochilmadi** — bu reja mavjud endpointlarga murojaat qiladi, server kodi tegilmadi, yangi tarmoq yuzasi yoki sxema o'zgarishi yo'q. Reja `<threat_model>` idagi **sakkizala** band bajarildi:

| Threat | Holat |
|---|---|
| T-03-69 (nazoratsiz jonli sessiya → NVR bitreyt byudjeti) | ✅ `LIVE_SESSION_MAX_MS` **avtorizatsiyadan qat'i nazar** (sof funksiya testi: `connecting` da ham `expired`); dialog yopilganda pleyer darhol unmount (montaj chegarasi bilan **strukturaviy**); **L0 majburiy** va u endi mikrotaskdan keyin o'lchanadi; uchalasi ham alohida test bilan |
| T-03-70 (havolaning ulashilishi yoki oqim identifikatorining sizishi) | ✅ Dialog holati URL'da **emas**, ulashish tugmasi yo'q, `queryByRole("link")` → `null`; `grep -rn` `components/cameras/` da **0**; opaque `url` ning bo'lagi ham `body.textContent` da yo'q |
| T-03-71 (vendored pleyerning almashtirilishi / runtime'da yuklanishi) | ✅ Skript **o'z originimizdan** (`/vendor/…`, test bilan qulflangan); G-7 yashil (xesh + import grafi + MIT + teg); G-6 `frontend/src` da **0** |
| T-03-72 (sessiya yangilanishida huquqning qayta tekshirilmasligi) | ✅ Har yangilashda **yangi chipta** (`apiFetch` sanog'i 1 → 2) va pleyer **qayta mount** (`mounts` 1 → 2); «uzilmasdan yangilash» ataylab rad etilgan va bu mount sanog'i bilan isbotlanadi |
| T-03-73 (cheksiz poll) | ✅ `DISCOVERY_POLL_TIMEOUT_MS`; terminal holatda `false`; `refetchIntervalInBackground: false` (03-08); **`started_at` yo'q holatining chegarasi qo'shildi** (Rule 2 #4); poll to'xtagach yangi so'rov ketmasligi **sanoq bilan** o'lchandi |
| T-03-74 (idempotentlikning UI'da ko'rinmasligi) | ✅ Uch hisoblagich **doim**; anti-«buzuq ko'rinadi» jumlasi; `last_seen_at` meta qatorida **majburiy**; **sabotaj S1** bilan o'lchandi |
| T-03-75 (arxivlashning «yo'q qilish» sifatida taqdim etilishi) | ✅ G-4 yashil (576 × 3 + 13 komponent fayli); `level={1}` + fe'l «Arxivlash» + fokus bekor qilishda; dialog tanasi tarix saqlanishini va qayta skan qaytarmasligini **aniq** aytadi |
| T-03-SC (npm o'rnatishlari) | ✅ `package.json` va `package-lock.json` diffi **bo'sh**; video yuzasi mavjud `ui/dialog.tsx` va vendored pleyer ustida qurildi |

## Next Phase Readiness

**03-11 (yakuniy darvoza) uchun ochiq bandlar:**

1. **`npm run gate` vaqti — 950 s** (03-09: 676 s, 03-08: 611 s). 618 s nomzod chegarasi ikkinchi marta va **sezilarli** oshib ketdi. Chegara qayta o'lchansin va «sovuq»/«issiq» yugurish ajratilsin.
2. **`requirements mark-complete`** — CAM-01…CAM-08 shu yerda belgilanadi (03-01…03-10 ning hech biri belgilamagan).
3. **`Go2rtcClient.remove_stream`** — arxivlashda server tomonidagi tozalash (chetlanish I; ta'siri chegaralangan, chunki arxivlangan kamera token **olmaydi**).
4. **`audit-volume` remediatsiyasi** (03-04/03-06/03-07 dan meros). Bu reja **bitta qo'shimcha o'qish** qo'shdi: arxiv sanog'i so'rovi (`camera-list.tsx`), va u sahifa ochilishida bir marta ketadi.
5. **`npm run test:sim:slow`** fazani yopishdan oldin bir marta.
6. **Qabul mezonlarining tuzatilgan naqshlari:** `\bcontrols\b` → `controls\s*=\s*true|<video[^>]*\bcontrols\b`; `grep -c <katalog>` → `grep -rn … | wc -l`; `\bdisabled=\{` → `(^|[^-])\bdisabled=\{` (03-09 dan).
7. **«Diagnostika» uchun endpoint qarori** (03-09 ziddiyat C) va **`setup-status.cameras`** ning haqiqiy sanog'i (03-08 dan meros).

**4-faza uchun:** `cameras.id` barqaror (arxivlash qatorni saqlaydi); `last_seen_at` UI'da allaqachon ko'rinadi; jonli ko'rish yo'li va vendored pleyer snapshot yuzasidan **mustaqil**.

## Self-Check: PASSED

- **Fayllar:** 18/18 mavjud (13 yangi + 5 o'zgargan) + SUMMARY
- **Commitlar:** 5/5 mavjud (`142eb4b`, `2427784`, `4814fd0`, `f1280e9`, `cea9de1`)
- **`must_haves.artifacts` `contains`:** 4/4 — `runNoChanges` (3), `DISCOVERY_POLL_TIMEOUT_MS` (2), `nameOverridden` (2), `LIVE_SESSION_MAX_MS` (4)
- **`must_haves.key_links`:** 2/2 — `useDiscoveryRunQuery` (`discovery-panel.tsx`), `video-stream` (`live-player.tsx` → `public/vendor/go2rtc/video-stream.js`)
- **Qabul mezonlari:** `runNoChanges` 3, `<dl|<dt|<dd` 6, `role="status"` 2 / `role="alert"` **0** (natija), `aria-hidden` 2 (panel), progress **elementi** 0, `\bdisabled=\{` **0**, `aria-describedby` 2, `last_seen_at` 3, `level={1}` 1, badge `truncate` **0**, vendor yo'li 1, `tabIndex={-1}` 2, `stream_name` **0**
- **`npm run gate`:** ✅ exit 0 (1448 / 412 / 61 / 576×3 / 86 / 246), 950 s
- **Ish daraxti:** uchala sabotajdan keyin ham **toza**

---
*Phase: 03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi*
*Completed: 2026-08-03*
