---
phase: 07-nomuvofiqlik-bildirishnoma-va-botlar
plan: 23
subsystem: frontend
tags: [error-handling, a11y, multi-tenant, pii, i18n, gap-closure]
gap_closure: true
requires:
  - "422 assignee_not_in_market (07-20, reconciliation.py:736)"
  - "reconErrorView() / RECON_ERROR_CODES (07-15)"
  - "domainKey(marketId, ...) — market-queries.ts doiralash konvensiyasi"
  - "G-38 jonli hudud darvozasi (07-22) — rol tanlovini CHEGARALAYDI"
provides:
  - "update.isError shoxi — xaritada YO'Q kod ham errors.generic bilan KO'RINADI"
  - "qarorga bog'langan dublikat qulfi (`case_id:status` + onSettled)"
  - "BLOCKED_REASON_ID + aria-describedby — «yechim majburiy» to'sig'ining sababi"
  - "assignee_not_in_market — ekran kodi + uchala locale'da sabab/tuzatish"
  - "usersKey(marketId) — xodimlar ro'yxatining tenant doirasi"
  - "useUsersInvalidator() — to'rt mutatsiya uchun bitta bekor qilish nuqtasi"
  - "G-17 zaxira kalit darvozasi (errors.generic uchala tilda)"
affects:
  - "frontend/src/lib/market-queries.ts — staff import tarmog'i endi doiralangan kalitni bekor qiladi"
  - "audit-filters / audit-list / charge-detail-dialog / variance-list / user-list — kalit o'zgarishi KO'RINMAS (hookni argumentsiz chaqiradi)"
tech-stack:
  added: []
  patterns:
    - "xato ko'rinishi mutatsiya HOLATIGA bog'lanadi (isError), xarita NATIJASIGA emas"
    - "dublikat qulfi = yuborilgan QAROR bileti, band identifikatori emas"
    - "bajarilmagan shart — aria-describedby, jonli hudud EMAS"
    - "yorliq zaxirasi = identifikatorning qisqa shakli, shaxsiy maydon EMAS"
key-files:
  created: []
  modified:
    - frontend/src/components/reconciliation/case-detail-dialog.tsx
    - frontend/src/components/reconciliation/case-detail-dialog.test.tsx
    - frontend/src/lib/reconciliation-errors.ts
    - frontend/src/lib/queries.ts
    - frontend/src/lib/market-queries.ts
    - frontend/src/lib/vendor-labels.ts
    - frontend/src/lib/tenant-cache.test.tsx
    - frontend/scripts/error-codes.test.mjs
    - frontend/messages/uz-Latn.json
    - frontend/messages/ru.json
    - frontend/messages/uz-Cyrl.json
decisions:
  - "To'siq sababi ROLSIZ matn: role=\"alert\" §14.9 bo'yicha faqat xatoga, role=\"status\" esa 07-22 ning G-38 olti-joyli qulfini buzardi"
  - "Sabab sharti `noteMissing`, `blocked` EMAS — nol o'tishda «yechim kerak» matni YOLG'ON bo'lardi"
  - "assignee_not_in_market tone=warning: server ham uni 422 (kirish xatosi) bilan rad etadi, 403 bilan emas"
  - "usersKey queries.ts da qoldi (must_haves artefakti), domainKey esa market-queries.ts dan import qilinadi — ikki modul orasidagi sikl ATAYIN qabul qilindi va o'lchandi"
  - "To'rt invalidatsiya bitta useUsersInvalidator() ga yig'ildi — kalit fabrikasining to'rt nusxasi biri ortda qolishi mumkin bo'lgan sinf edi"
metrics:
  duration: "~1.5 soat"
  completed: 2026-08-13
  tasks: 3
  commits: 5
  files_changed: 11
---

# Phase 7 Plan 23: Hukm dialogining uch jim nuqsoni va mas'ul yorlig'i Summary

Fazadagi yagona yozuv amali endi jim yiqilmaydi: xaritada bo'lmagan har qanday
xato `errors.generic` matni bilan ko'rinadi, ketma-ket ikkinchi haqiqiy qaror
serverga yetadi, «yechim majburiy» to'sig'ining sababi `aria-describedby` orqali
o'qiladi, 07-20 ning `assignee_not_in_market` kodi uchala tilda nomlandi va
mas'ul yorlig'i telefon raqamini ekranga umuman chiqarmaydi.

## Nima qilindi

### B-5 — yiqilgan hukm muvaffaqiyatlisidan farq qilmasdi (`7836b4f`)

Nuqsonning o'lchami shundaki, `reconErrorView()` **besh** kodni biladi va qolgan
hammasi `null` qaytaradi; chaqiruvchi esa `null` da **hech nima chizmasdi**.
Ya'ni `NetworkError` (`ApiError` emas), `422` (FastAPI `detail` ni massiv qiladi va
`detailOf()` bo'sh satr beradi), `429`, `5xx` va `market_not_selected` — **hammasi
jim** o'tardi. Dialog ochiq qolardi, tanlangan holat `<Select>` da turardi, tugma
yana faol ko'rinardi: direktor nizo hujjatini (D-02) **yozilgan deb hisoblardi**.

Shart `errorView !== null` dan `update.isError` ga o'tdi. Zaxira matn yangi kalit
emas — `reconciliation-errors.ts:106-108` **allaqachon** «chaqiruvchi
`errors.generic` ga tushadi» deb yozgan edi; yagona chaqiruvchi endi shu yozilgan
shartnomani bajaradi. Ekranga faqat lokalizatsiya kaliti chiqadi: xom `detail`,
istisno matni, stack izi va status kodi testlarda nomma-nom **taqiqlangan**.

### B-7 — bitta ochiq dialogda ikkinchi qaror jimgina tashlanardi (`7836b4f`)

Qulf `detail.case_id` ni saqlardi va faqat `onError` da bo'shardi. Muvaffaqiyatdan
keyin dialog **yopilmaydi** (`case-list.tsx` da `openCaseId` faqat
`onOpenChange(false)` da tozalanadi) va forma unmount bo'lmaydi. Real oqim:
`new→in_review` saqlanadi, keyin direktor yechim matnini yozib `in_review→justified`
qilmoqchi bo'ladi — `blocked` false, tugma faol, `aria-disabled` ham false, lekin
`onSave` **jim `return`** qiladi.

Bilet endi `` `${case_id}:${status}` ``, ya'ni **yuborilgan qaror**. Eski izohning
asosi («muvaffaqiyatda ikkinchi so'rov nol o'tish (409) bo'lardi») faqat holat
o'zgarmaganda rost, nol o'tish shoxini esa `unchanged` bayrog'i **allaqachon** to'sib
turibdi — ya'ni qulf 409 dan emas, **haqiqiy ikkinchi qarordan** himoyalanardi.
`onError` → `onSettled`. Dublikat qulfi saqlandi va bu tasodif emas: `mutate`
asinxron, ya'ni bir hodisa oqimidagi ikkinchi bosish `onSettled` dan **oldin**
sodir bo'ladi va hamon ayni biletni ko'radi (mavjud «uch tez bosish» darvozasi
yashil qoldi).

### WR-16 — «yechim majburiy» qoidasi hech bir tilda erishib bo'lmasdi (`7836b4f`)

Matn uchala locale'da yozilgan edi, lekin unga olib boradigan yo'l yo'q edi:
server bu kodni hech qachon qaytarmaydi (qoida **klientda** yashaydi), klientdagi
yagona tekshiruv esa `blocked` ichida va u hech nima chizmasdi.

`noteMissing` alohida bayroq bo'ldi va sabab+tuzatish `BLOCKED_REASON_ID`
elementida chiziladi; tugmaning `aria-describedby` si unga ishora qiladi.

**Rol tanlovi — ikki taqiq orasidagi yagona bo'sh joy:**

| Nomzod | Nega YARAMAYDI |
|--------|----------------|
| `role="alert"` | 07-UI-SPEC §14.9 jonli hududlar qatori: `alert` — **faqat xato**. Bu esa xato emas, bajarilmagan shart; `RECON_ERROR_TONE` ham uni `neutral` deb yozgan |
| `role="status"` | 07-22 ning **G-38** darvozasi bu katalogda `role="status"` ni **aynan olti** joyga va har birini `aria-busy` bilan bir elementda bo'lishga qulflagan. Yettinchi jonli hudud darvozani qizartirardi — va u **haqli** bo'lardi: shart render paytida rost, ya'ni e'lon hech kim kutmagan paytda yangrardi |
| **Rolsiz matn + `aria-describedby`** | ✅ Tanlandi. Skrinrider foydalanuvchisi sababni tugmaga fokuslanganda, ya'ni **so'raganda** eshitadi |

Shart `blocked` emas, `noteMissing`: `blocked` uch sababdan iborat va nol o'tishda
«yechim matni kerak» **yolg'on** bo'lardi — §9.4 ning nol o'tish qarori aynan
yolg'on matnning oldini olish uchun yozilgan. Bu alohida darvoza bilan o'lchandi.

### 07-20 chegarasi — `assignee_not_in_market` (`6198fbc`)

07-20 serverda `422` ni ochdi (`user_market_roles` ustidagi **ilova qatlami** —
sxemada FK yo'q, ya'ni bu tekshiruv yagona to'siq), klientda esa kod
xaritalanmagan edi: juda aniq va tuzatsa bo'ladigan muammo direktorga
«Kutilmagan xato yuz berdi» bo'lib chiqardi.

`RECON_ERROR_CODES` ga a'zo, `SERVER_CODE_MAP` ga yozuv, `tone: "warning"`
(server ham uni **kirish xatosi** deb `422` bilan rad etadi, `403` bilan emas —
`danger` direktorni o'z huquqidan shubhalantirardi). Matnda xodimning ismi,
telefoni yoki identifikatori **yo'q**: T-07-110 bo'yicha mavjud bo'lmagan
`user_id` ham ayni kodni oladi, ya'ni matn «bunday xodim yo'q» **deyolmaydi** —
aks holda javob kodi bo'yicha identifikatorlarni sanab chiqish yo'li ochilardi.

Zanjir uchidan-uchiga o'lchandi: mock server `422` beradi → dialog **nomlangan**
sabab+tuzatish juftligini chizadi va `errors.generic` ni **chizmaydi**. Da'vo ikki
tomonlama — faqat birinchisi B-5 ning zaxira shoxi bilan ham yashil bo'lardi.

### WR-09 (a) — xodimlar ro'yxati tenant-doiralanmagan kalitda edi (`6198fbc`)

`USERS_QUERY_KEY = ["users"]` `market-queries.ts` ning o'z qoidasidan
(«har bir domen kaliti `["m", marketId, ...]` bilan boshlanadi va **istisno yo'q**»)
yagona istisno edi. Ikki mustaqil zarar: bozor almashtirilganda 30 soniyalik
`staleTime` ichida oldingi bozorning xodimlari **hech qanday so'rovsiz** qayta
chizilardi (va audit izidagi aktor **begona bozor** xodimining nomi bilan
yorliqlanardi), hamda `domainKey(marketId)` prefiksi bo'yicha tozalash bu kalitga
**yetib bormasdi**.

`usersKey(marketId) = domainKey(marketId, "users")`. `useUsersQuery()` bozorni
`useMarketId()` dan **o'zi** oladi va `enabled` ga `marketId !== null` qo'shildi,
ya'ni oltala iste'molchi uchun o'zgarish **ko'rinmas** — ular hookni argumentsiz
chaqiradi va kalitni bilmaydi. To'rtta `invalidateQueries` bitta
`useUsersInvalidator()` ga yig'ildi: kalit fabrikasi va bozorni o'qish to'rt marta
takrorlansa, ulardan bittasi kelajakda ortda qolardi va faylning o'z docstringi
aynan shu sinfdagi xatoni («admin bloklagan foydalanuvchini ekranda hamon faol
ko'rib turadi») sabab qilib ko'rsatgan.

### WR-09 (b) — yorliq zaxirasi telefon raqami edi (`6198fbc`)

`user.full_name ?? user.phone` raqamni **ikki yuzaga** chiqarardi: mas'ul
tanlagichiga va **audit iziga** — ya'ni raqam D-02 nizo hujjatining o'zgarmas
nusxasiga tushardi. Telefon raqami O'zR qonuni ostidagi shaxsiy ma'lumot va u UI
bezagi bo'lolmaydi.

Zaxira `user.id.slice(0, 8)` bo'ldi va **ikki joyda bir vaqtda** (`byId` va
`options`) — bitta yordamchi funksiya orqali, chunki faqat bittasini tuzatish
raqamni ikkinchisida qoldirardi va darvoza «tuzatildi» deb yashil bo'lardi. Bu
yangi qoida emas: `ActorLabel` ning **o'z izohi** («Ism kelmasa identifikatorning
qisqa shakli») shuni ko'zda tutgan edi.

`useVendorLabels` **tegilmadi** — u allaqachon `vendorsKey(marketId, ...)` bilan
doiralangan va uning yorlig'i `vendor_view` ostidagi boshqa qoidaga bo'ysunadi.

## O'lchov nuqsoni — fikstura ATAYIN ikki xodimli

Ismsiz xodimning **to'g'ri** yorlig'i (`id.slice(0, 8)`) `ActorLabel` ning
**yuklanmagan** holatdagi zaxirasi bilan aynan bir xil satr. Birinchi urinishda
darvoza yolg'iz ismsiz xodim bilan yozilgan edi va u **sabotajda ham yashil
qolardi** — chunki `renderDialog()` `GET /users` javobini kutmaydi va o'lchov
paytida ro'yxat hali kelmagan bo'lardi (o'lchandi: dastlabki qizil yugurishda
tanlagichda faqat «Biriktirilmagan» bor edi va audit da'vosi **trivial yashil**
chiqdi). Fiksturaga **ismli** xodim qo'shildi: u ro'yxatning kelganini ishonchli
bildiradi va faqat shundan keyin telefon raqami yo'qligi o'lchanadi.

## Ikki sabotaj — o'lchandi va qaytarildi

| # | Sabotaj | Kutilgan | O'LCHANDI |
|---|---------|----------|-----------|
| **S-1** | `case-detail-dialog.tsx` da xato shoxi yana `errorView === null ? null : (...)` ga qaytarildi | tarmoq va `429`/`500` testlari qizaradi; nomlangan kod testi yashil qoladi | ✅ `tsc --noEmit` **toza** (kompilyatsiya qildi). **Aynan 3 da'vo qizardi**: `TARMOQ uzilganda`, `429 va 500`, `market_not_selected (403)`. ⛔ `NAZORAT: NOMLANGAN kod` (`status_unchanged`) va `assignee_not_in_market` uchidan-uchiga testi — **yashil qoldi**, ya'ni darvoza «hamma xato ko'rinadi» ni «hamma xato bir xil ko'rinadi» dan **ajratadi**. Qolgan 20 ta da'vo yashil |
| **S-2** | `recon.errorFix.assignee_not_in_market` `ru.json` dan o'chirildi | `error-codes.test.mjs` ning OLDINGA bandi qizaradi va yetishmagan tilni nomma-nom ko'rsatadi | ✅ 235 tadan **aynan 1 tasi** qizardi: `G-17: HAR NOMUVOFIQLIK kodi uchun sabab va tuzatish UCHALA tilda bor`, xabari — `` ru.json: recon.errorFix.assignee_not_in_market YO'Q ``. Til ham, kalit ham **nomma-nom**. Qolgan 234 gate yashil |

Ikkalasi ham `git checkout -- <fayl>` bilan qaytarildi (`git clean`/`reset`
**ishlatilmadi**); qaytargandan keyin `git status --porcelain frontend/` — **bo'sh**.

## uz-Cyrl — QO'LDA o'qildi

Yangi tokenlarning **har biri** alohida tekshirildi (i18n tuzog'i bu fazada ikki
marta tasdiqlangan: mexanik darvoza o'zlashma so'zning semantik xatosini
**ushlamaydi**):

| uz-Latn token | Generator chiqishi | Hukm |
|---------------|--------------------|------|
| Tanlangan | Танланган | ✅ sof o'zbekcha o'zak + qo'shimcha |
| xodim / xodimini | ходим / ходимини | ✅ arabcha o'zlashma, lekin **to'liq assimilyatsiya qilingan** va kirill imlosi aynan shu |
| bu / shu | бу / шу | ✅ |
| bozor / bozorga | бозор / бозорга | ✅ forscha o'zlashma, standart kirill shakli |
| biriktirilmagan | бириктирилмаган | ✅ sof o'zbekcha |
| Ro'yxatdan | Рўйхатдан | ✅ `o'` → `ў` to'g'ri; **рўйхат** standart shakl |
| tanlang | танланг | ✅ |

⛔ **`ns`/`ts` klasterli o'zlashma so'z yangi matnlarda YO'Q** va bu tasodif emas:
copy ataylab `identifikatsiya`, `registratsiya`, `instruksiya`, `litsenziya`
sinfidagi so'zlarsiz yozildi (07-16 ning `kvitansiya` darsi). Shu sababli
`uz-Cyrl.overrides.json` ga **yangi yozuv qo'shilmadi** va fayl umuman
tegilmadi — reja uni `files_modified` da shartli («agar chiqsa») sanagan edi.

`ru.json` matnlari qo'lda yozildi (transliteratsiya emas), ICU platsholderlari
ikkala kalitda ham **yo'q**, ya'ni parity trivial ravishda teng.

## Chetlanishlar

### 1. [Rule 3 — Blocking] `market-queries.ts` reja ro'yxatida yo'q edi, lekin kalitni TO'G'RIDAN-TO'G'RI import qilardi

- **Qachon topildi:** 2-vazifa, `USERS_QUERY_KEY` olib tashlangandan keyin
- **Muammo:** reja «blast radius **o'lchangan** va u kichik — oltala iste'molchi
  hookni **argumentsiz** chaqiradi va kalitni bilmaydi» deb yozgan edi. Bu
  o'lchov **yettinchi** iste'molchini o'tkazib yuborgan:
  `market-queries.ts:45` konstantani **hookdan emas, moduldan** import qiladi va
  uni `importInvalidationKeys(marketId, "staff")` da ishlatadi. Konstanta
  o'chirilgach `tsc` yiqilardi.
- **Tuzatish:** import `usersKey` ga o'tkazildi va `return [usersKey(marketId),
  setupStatusKey(marketId)]`. Yonidagi izoh ham yangilandi — u `staff` ni
  «**yagona doiralanmagan** kalitli tarmoq» deb ta'riflardi va bu endi
  **yolg'on** bo'lib qolardi.
- **Yon foyda:** import tugagandan keyingi bekor qilish ham doiralandi, ya'ni
  WR-09 ning **ikkinchi** yarmi (prefiks bo'yicha tozalash yetib bormasligi) shu
  yerda ham yopildi.
- **Fayl:** `frontend/src/lib/market-queries.ts`
- **Commit:** `6198fbc`

### 2. [O'lchov usuli] Reja `grep -c` bilan yozilgan «done» mezonlari izohlarni ham sanaydi

- Reja `grep -c "onSettled" case-detail-dialog.tsx` → **1** deb yozgan, lekin
  ayni reja `onSettled` ga o'tishning **sababini izohda yozishni ham TALAB
  qilgan**. Ikki talab so'zma-so'z bir vaqtda bajarilmaydi.
- **Qaror:** mazmunli invariant o'lchandi — `grep -c "onSettled:"` → **1**
  (callback aynan bitta), `grep -c "onError:"` → **0**. Qolgan 3 satr — reja
  talab qilgan izoh.
- Ayni holat `user.phone` va `USERS_QUERY_KEY` mezonlarida ham chiqdi; u yerda
  izohlar tokenni **umuman ishlatmaydigan** qilib qayta yozildi (ma'no
  yo'qolmadi), ya'ni ikkala grep hozir haqiqatan **0**.

## Ochiq bandlar

1. ⚠ **07-UI-SPEC §19 («Dizayn tizimi xulosasi») jadvali eskirdi:** «Xato holatlari | **4** case
   kodi + 4 yetkazilmaslik turi» deb yozilgan, endi **5** + 4. Spec bu rejaning
   `files_modified` ida **yo'q** va u faza kontrakti, shuning uchun **tegilmadi**.
   Egasi — faza yakunidagi tekshiruv.
2. ⚠ **`queries.ts` ↔ `market-queries.ts` — ikki tomonlama modul sikli.**
   Ilgari sikl bir tomonlama edi (`market-queries` → `queries`); reja `domainKey`
   ni **import qilishni** nomma-nom talab qilgani uchun ikkinchi yo'nalish
   qo'shildi. Xavfsiz, chunki ikkala referens ham **funksiya tanasida** (modul
   yuklanish paytida emas) va u `tsc`, `vitest`, `next build` — **uchalasida**
   toza o'lchandi. To'g'ri yakuniy shakl — `domainKey` ni alohida modulga
   ajratish; u `market-queries.ts` ni keng qamrab olardi va bu rejaning
   qamrovidan tashqarida.
3. ⚠ **`npm run bot:lint` hamon qizil** — `deferred-items.md` dagi mavjud band
   (07-18 ning `test_binding.py` mypy xatolari). Bu rejaning ishiga aloqasi yo'q
   va u tegilmadi.

## Tekshirish natijalari

| Buyruq | 07-22 bazasi | Shu reja | Izoh |
|--------|--------------|----------|------|
| `node --test scripts/*.test.mjs` | 234 pass / 0 fail | **235 pass / 0 fail** | +1 (G-17 zaxira kalit) |
| `vitest run` | 833 pass / 62 fayl | **849 pass / 62 fayl** | +16 (dialog 13, tenant-cache 3) |
| `npm run i18n:check` | 1210 × 3 | **1212 × 3**, drift yo'q | +2 kalit |
| `npm run typecheck` | toza | **toza** | |
| `npm run lint` | toza | **toza** | |
| `npm run build` | 75 SSG | **75 SSG**, 7.2 s | |

⛔ **T-07-SC (yangi paket yo'q) o'lchandi:** `git diff --name-only 88e59d4..HEAD`
da `frontend/package.json`, `frontend/package-lock.json` va
`frontend/src/lib/rbac.ts` — **yo'q**. Jami 11 fayl, hammasi kod/matn/test.

## Ma'lum stublar

Yo'q. Bu reja mavjud yuzalarning nuqsonlarini yopdi va yangi ulanmagan
komponent yoki qattiq kodlangan bo'sh qiymat kiritmadi.

## Self-Check: PASSED

Sanab o'tilgan 8 fayl ham diskda mavjud; beshala commit ham `git log` da
topildi (`b084ad8`, `7836b4f`, `782b9ab`, `6198fbc`, `00b3e4c`).
