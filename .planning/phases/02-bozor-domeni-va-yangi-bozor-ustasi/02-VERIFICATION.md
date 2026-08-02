---
phase: 02-bozor-domeni-va-yangi-bozor-ustasi
verified: 2026-08-03T01:46:23Z
status: human_needed
score: 9/9 must-haves verified
re-verification: yes
overrides_applied: 0
re_verification:
  previous_verified: 2026-08-01T12:00:00Z
  previous_status: gaps_found
  previous_score: 4/8
  gaps_closed:
    - "SC#1 — usta mahsulot ichidan yetib boriladigan bo'ldi (CR-03: marshrut istisnosi + navigatsiya yozuvi + bo'sh holat havolasi)"
    - "Shaxsiy ma'lumot O'QISHI auditda (CR-02 / D-09: `stalls`, `stalls/{id}`, `stalls/{id}/assignments` -> `audit_read` + `VENDOR_VIEW`; qamrov marshrut grafi darvozasi bilan qulflandi)"
    - "Klient keshining tenant chegarasi (CR-01: domen kalitlari `[\"m\", marketId, ...]` bilan doiralandi + sessiya identifikatori o'zgarganda `client.clear()`)"
    - "Import qobiliyati Karmana miqyosida, quvurning O'ZI ishlab chiqarmagan yuk bilan isbotlandi (600 rasta / 480 sotuvchi, `ast` mustaqillik darvozasi bilan)"
  gaps_remaining: []
  regressions: []
  additional_closed:
    - "WR-06 — `open_weekdays` endi ustada YIG'ILADI; migratsiya `0011` jimgina «har kuni ochiq» standartini ikkala yo'ldan ham olib tashladi"
    - "MARKET-07 (yangi talab) — xodimlar rosterining ommaviy importi, rollar va vaqtinchalik parollar"
    - "Traceability — MARKET-01…07 ikkala joyda `Done`, moslik `scripts/check-requirements-sync.mjs` bilan mexanik qulflangan"
warnings:
  - id: WARN-1
    item: "`test_phase2_criteria.py` — ROADMAP mezonlarining YAGONA bog'langan fayli — hamon BESHTA mezonni qamraydi; ROADMAP'da esa 2026-08-01 dan beri OLTITA (SC#6 = MARKET-07)"
    impact: "SC#6 mazmunan qamralgan (`test_staff_import.py`, 21 test), lekin ROADMAP matniga bog'langan regressiya darvozasidan TASHQARIDA — ROADMAP tahrirlanganda mos kelmaslik endi ko'zga tashlanmaydi"
    severity: warning
  - id: WARN-2
    item: "`USERS_QUERY_KEY = [\"users\"]` va `[\"audit\", filters]` — `market_id` bilan doiralanMAGAN ikkita kalit (`frontend/src/lib/queries.ts`)"
    impact: "Bugun sizish YO'Q: bozor almashtirishning yagona yo'li `applySession()` va u `client.clear()` ni ishga tushiradi. Lekin `market-queries.ts:72` ning «ISTISNO YO'Q» da'vosi noto'g'ri (uni `market-queries.ts:1062` ning o'zi ochiq rad etadi) va YANGI global kalit qo'shilishini to'sadigan darvoza yo'q"
    severity: warning
  - id: WARN-3
    item: "`GET /api/v1/users` (xodim `full_name` + `phone`) o'qish auditidan ATAYIN ozod"
    impact: "D-09 ning O'Z matni «sotuvchining ma'lumoti» deydi, ya'ni istisno qaror bilan mos; lekin xodim telefoni ham O'zR shaxsiy ma'lumotlar qonuni ostida. Istisno ikki tomonlama qulflangan va sababi yozilgan — qaror ONGLI, qarz esa OCHIQ"
    severity: warning
  - id: WARN-4
    item: "WR-02 (`market_activate()` / `market_delete_draft()` da tenant predikati yo'q) 3-fazaga eskalatsiya qilingan, lekin ROADMAP §Phase 3 ning `Success Criteria` sida NOMLANMAGAN"
    impact: "Eskalatsiya `02-CONTEXT.md` §Deferred Ideas va `STATE.md` §Decisions da yashaydi. `market_delete_draft()` o'n ikki jadval bo'ylab kaskad o'chiradi va uning yagona chegarasi ilova qatlami — 3-faza rejalashtiruvchisi buni ROADMAP'dan KO'RMAYDI"
    severity: warning
human_verification:
  - test: "Ustaning kod yozmasdan yakunlanishi — foydalanuvchanlik kuzatuvi (SC#1 ning FOYDALANUVChANLIK yarmi)"
    expected: "Platforma admini yordamsiz, hujjatsiz va URL qo'lda termasdan `login -> /select-market -> «Birinchi bozorni yaratish» -> 7 qadam -> faollashtirish` zanjirini oxirigacha bosib o'tadi; hech bir qadamda to'xtamaydi"
    why_human: "«Kod yozilmaydi» — foydalanuvchanlik da'vosi, manba tekshiruvi emas. Mexanik yarmi (zanjir uzilmaydimi) `test_sc1_...` va `wizard-reachability.test.mjs` bilan qamralgan; odam qayerda to'xtashini faqat kuzatish ko'rsatadi. 02-18 uchala to'siqni yopgani uchun kuzatuv endi BAJARILADIGAN holatda (ilgari bajarib bo'lmasdi)"
  - test: "Ma'muriyatning qog'oz reestri bilan raqamlarni solishtirish (`ops/data/karmana/README.md` §7 ning yettala raqami)"
    expected: "Tizimdagi rasta soni, zona/holat/toifa bo'yicha taqsimot va toifa narxlari ma'muriyat daftariga mos keladi"
    why_human: "Taqqoslanadigan ikkinchi tomon tizimdan TASHQARIDA. Tizimning O'ZI bilan mosligi `test_karmana_scale_import.py` bilan avtomatlashtirilgan; qog'oz bilan mosligini mashina o'lchay olmaydi. ⚠ Bu band FAZA DARVOZASI EMAS (ROADMAP self-service qoidasi, 2026-08-01) — lekin u YO'QOLGAN ham emas"
  - test: "Sxematik xaritaning maqsadli qurilmada O'QILISHI (shrift, kontrast, skroll masofasi) — real zona/rasta soni yuklangandan keyin"
    expected: "Bozor admini o'z ish kompyuteri va telefonida 600+ rastali xaritani skroll qilib o'qiy oladi; kontrast va shrift o'lchami yetarli"
    why_human: "Perseptual baho. jsdom shrift o'lchamini, kontrastni va skroll masofasini o'lchay olmaydi; «birorta rasta tushib qolmaydi» degan MEXANIK yarmi `stall-map.test.tsx` bilan avtomatlashtirilgan"
  - test: "Rekvizit formatlarini (STIR, bank hisob raqami, MFO) buyurtmachi bilan tasdiqlash"
    expected: "Buyurtmachi rasmiy hujjat talabidagi format va majburiylik darajasini tasdiqlaydi"
    why_human: "Tashqi manba talabi (A1/A2 taxminlari, LOW confidence). Bugungi holat xavfsiz tomonga qiya — server rekvizitlarni ATAYIN formatlamaydi — ya'ni kechiktirish zarar keltirmaydi"
---

# Phase 2: Bozor domeni va "Yangi bozor" ustasi — QAYTA TEKSHIRUV hisoboti

**Phase Goal (2026-08-01 da qayta ta'riflangan):** Platforma admini kod yozmasdan yangi bozorni tizimga kiritadi — rasta/tarif/sotuvchi va xodimlar ro'yxati saytning o'zidan, fayl yuklash orqali kiritiladi
**Verified:** 2026-08-03
**Status:** human_needed
**Re-verification:** HA — 2026-08-01 dagi `gaps_found` (4/8) hisobotidan keyin, oltita yopish rejasi (02-18…02-24) bajarilgandan keyin

---

## Birinchi tekshiruv nima topgan edi (tarix o'chirilmaydi)

2026-08-01: **`gaps_found`, 4/8**. To'rt bo'shliq:

| # | Bo'shliq | Manba |
|---|---|---|
| 1 | Usta QURILGAN, lekin mahsulotda unga BIRORTA yo'l yo'q (bozorsiz admin `/select-market` da qamalardi) | CR-03 |
| 2 | Import yo'li faqat O'Z-O'ZIGA qaytadigan shablon bilan sinalgan — quvur hech qachon o'zi ishlab chiqarmagan ma'lumotni ko'tarmagan | Level-4 DISCONNECTED |
| 3 | React Query kalitlari `market_id` ni olib yurmaydi va kesh sessiya o'zgarganda tozalanmaydi | CR-01 |
| 4 | `GET /stalls`, `/stalls/{id}`, `/stalls/{id}/assignments` sotuvchi F.I.Sh./telefonini IZSIZ beradi | CR-02, D-09 |

Shu hisobotning o'z xulosasi ham saqlanadi: *«a green gate is not proof the phase goal was reached»* — 890 yashil test ostida to'rtta haqiqiy bo'shliq turgan edi. Quyidagi qayta tekshiruv aynan shu shubha bilan, SUMMARY da'volariga ishonmasdan bajarildi.

---

## Maqsadning qayta ta'riflanishi haqida — mening hukmim

Maqsad jumlasining ikkinchi yarmi («Karmananing real … ma'lumoti tizimda yashaydi») **2026-08-01 da ataylab olib tashlandi** (ROADMAP §"Mahsulot qoidasi: self-service onboarding" + §Phase 2 "Real ma'lumot haqida"). Ikkala matnni ham o'qidim. Hukmim ikki qismli va men uni yumshatmayman:

**Qayta ta'riflash QONUNIY — jadval/darvoza masalasi sifatida.** Sabablari kuchli va ular tekshiriladigan:

1. Qoida **bir tekis** qo'llangan, 2-fazani qutqarish uchun emas: ayni qaror Phase 0 ning Phase 3/4/8 ni bloklashini ham olib tashladi, Phase 3 ga NVR avtomatik kashfiyotini kiritdi va MARKET-07/CAM-08/CAM-09 talablarini tug'dirdi. Bu — mahsulot pozitsiyasi, oqlov emas.
2. Qayta ta'riflash tekshiruvni **bo'shatmadi, qattiqlashtirdi**. O'rniga qo'yilgan dalil (600 rasta / 480 sotuvchi, quvurdan mustaqil yuk, 11 bosqichli uchidan-uchiga test) bitta real fayl yuklashdan **ko'proq** narsani isbotlaydi: takroriy import, qisman qayta import, uch xil telefon shakli, surilgan ustunlar, iflos fayl rad etilganda sanoqning o'zgarmasligi.
3. Band **yo'qolmadi**: u `02-VALIDATION.md` `human_only_verifications[0]` da EGASI va ISHGA TUSHISH SHARTI bilan, hamda `open_items[3]` da yashaydi.

**LEKIN u haqiqiy xavfni to'liq YOPMAYDI, va buni ochiq aytish kerak.** Birinchi tanqid *epistemik* edi: quvur hech qachon o'zi kutmagan ma'lumotni ko'rmagan. Generator — o'sha jamoa, o'sha repo, o'sha README §3 ustun tartibi. `ast` darvozasi `xlsx_template` importini taqiqlaydi, ya'ni **modul mustaqilligini** isbotlaydi; **epistemik mustaqillikni** esa isbotlay olmaydi. Ma'muriyat `A-12/1` shaklidagi kod, qo'shilgan katak yoki README bilmagan to'rtinchi ustun bilan kelsa, buni faqat real fayl ko'rsatadi.

**Xulosa:** re-framing bo'shliqni *ta'rif bilan yo'q qilmaydi* — u bo'shliqni **darvozadan operatsion bandga ko'chiradi** va ko'chirish egasi hamda sharti bilan hujjatlashtirilgan. Bu qabul qilinadi. Shart: `nyquist_compliant: true` ni hech kim «real ma'lumot solishtirildi» deb o'qimasin — u endi «har band yo avtomatlashtirilgan, yo egasi bilan `human_only_verifications` ga ko'chirilgan» degani. Skript aynan shu SHAKLNI majburlaydi, MAZMUNNI emas (skriptning o'z docstringi buni ochiq yozgan).

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|---|---|---|
| 1 | SC#1 — Platforma admini ustadan o'tib bozor yaratadi, kod yozilmaydi; **usta mahsulot ichidan yetib boriladi** | ✓ VERIFIED (mexanik yarmi) | `(app)/layout.tsx:62` — `pathname !== WIZARD_NEW_PATH`, TENGLIK; `app-shell.tsx:154-160` — `NAV_ITEMS` da `/markets/new` + `permission: "market_manage"` + `group: "system"`; `market-picker.tsx:170-177` — bo'sh holatda `canCreate ? <Link href={NEW_MARKET_PATH}>`. Manba darvozasi (`wizard-reachability.test.mjs`, 3 test) + xulq testlari (`layout.test.tsx` 5, `app-shell.test.tsx` 4, `market-picker.test.tsx` 3) — **o'zim ishga tushirdim, 57/57 yashil**. Zanjirning oxiri ham tekshirildi: `auth.py:327` bozorsiz login javobida ham `is_platform_admin` beradi, `login-form.tsx:106` uni store'ga yozadi, ya'ni `markets/new/page.tsx` ning ikkinchi darvozasi bootstrap holatida OCHILADI |
| 2 | SC#2 — Reestr o'zgarishlari (holat/toifa/biriktirish) auditda | ✓ VERIFIED (regressiya) | `test_sc2_registry_changes_are_audited` — **o'zim ishga tushirdim, yashil** |
| 3 | SC#3 — Tarif o'zgarganda o'tmish eski narxda qoladi | ✓ VERIFIED (regressiya) | `test_sc3_past_charges_keep_the_old_price` — **o'zim ishga tushirdim, yashil** |
| 4 | SC#4 — Bayram/ishlamaydigan kun belgilanadi, o'sha kunga hisob asosi yo'q | ✓ VERIFIED (**ogohlantirish YOPILDI**) | Migratsiya `0011_weekday_choice.py` `market_create()` dagi `COALESCE(...ARRAY[1..7])` ni HAM, ustundagi `server_default` ni HAM olib tashladi; yangi kontrakt `NULL` = «tanlanmagan» (`calendar_missing` yonadi), `'{}'` = rad. Usta endi qiymatni YUBORADI: `market-requisites-form.tsx:268` -> `open_weekdays`. Ilgari «strukturaviy jihatdan erishib bo'lmaydigan» deb yozilgan holat endi yozib bo'ladigan bo'ldi |
| 5 | SC#5 — Sxematik plan-xarita zona bo'yicha grid; rasta bosilganda karta | ✓ VERIFIED (regressiya) | `test_sc5_map_groups_stalls_by_zone_in_code_order` yashil; `stall-map.test.tsx` 74 vitest ichida yashil |
| 6 | **SC#6 (YANGI)** — Xodimlar ro'yxati bitta fayl bilan yuklanadi, hisoblar rollar bilan yaratiladi, vaqtinchalik parollar beriladi | ✓ VERIFIED (⚠ WARN-1) | `POST /imports/staff` (`imports.py:327-461`): `market_id` FAQAT `_market_id(principal)` dan, fayldan EMAS; ochiq parol `secrets_by_row` lug'atida qoladi, repozitoriyga faqat `hash_password(...)` ketadi, `log.info` faqat sanoqlarni oladi, javobda `Cache-Control: no-store`. UI ulangan: `users/page.tsx:88` `<ImportPanel kind="staff" />` `canManage` ostida. `test_staff_import.py` 21 test — jumladan `test_import_into_market_a_leaves_market_b_untouched` va `test_audit_never_contains_a_temporary_password` — **o'zim ishga tushirdim, yashil** |
| 7 | Klient tomonidagi ma'lumot bozor almashtirilganda / chiqishda boshqa bozorga sizib chiqmaydi (CLAUDE.md) | ✓ VERIFIED (⚠ WARN-2) | `market-queries.ts:116-138` — `domainKey(marketId, ...)` fabrikasi; global konstantalar (`ZONES_KEY`, `STALLS_KEY`, …) **haqiqatan o'chirilgan** (repo bo'yicha 0 ta e'lon; yagona uchrash — sababi yozilgan izoh). `auth-store.ts` `setSession`/`clearSession` shartsiz, `applySession` esa `previousMarketId !== next.market.id` bo'lganda `emitSessionReset()` chaqiradi; `query-provider.tsx:73` unga obuna bo'lib `client.clear()` qiladi. `tenant-cache.test.tsx` ikki yarimni ATAYIN ALOHIDA o'lchaydi (doiralash testi `updatePrincipal` orqali tozalash kanalini chetlab o'tadi) + nazorat holati «token yangilash keshni SAQLAYDI» |
| 8 | Shaxsiy ma'lumotni O'QISH ham auditda (D-09; CLAUDE.md «audit jurnali majburiy») | ✓ VERIFIED (⚠ WARN-3) | `stalls.py:304-311` va `392-400`: `dependencies=[Depends(require_permission(Permission.VENDOR_VIEW))]` + `StallReadIntentDep`; `assignments.py:357-362` — ayni shakl. Orfan konstantalar endi ISTE'MOL QILINADI (`TABLE_STALLS`). Eng muhimi: qamrov endi bitta marshrutga emas, **QOIDAGA** aylantirilgan — `tests/tenancy/test_personal_data_coverage.py` marshrut GRAFINI (manba matnini emas) yurib, javob modelida `vendor_name`/`phone`/`full_name` bo'lgan har `GET` dan `audit_read` VA `VENDOR_VIEW` talab qiladi; `GET /stalls/map` esa NAZORAT sifatida talabdan ozod ekani alohida o'lchanadi. **O'zim ishga tushirdim, yashil** |
| 9 | Import qobiliyati Karmana miqyosida, **quvurning O'ZI ishlab chiqarmagan** yuk bilan isbotlangan (qayta ta'riflangan maqsad bandi) | ✓ VERIFIED | `tests/fixtures/karmana_seed.py` — `import` ro'yxatida faqat `argparse/io/random/zipfile/dataclasses/datetime/pathlib/typing/xlsxwriter`; `app.*` YO'Q, `xlsx_template` YO'Q. Mustaqillik `ast` bilan qulflangan (`grep` EMAS — docstringda taqiqning nomi ataylab uchraydi). `test_karmana_scale_import.py` — 11 bosqich, FAQAT HTTP orqali: 600 rasta `inserted`, qayta import `{inserted: 0, skipped: 600}`, qisman qayta import faqat yangi kodlarni qo'shadi, 480 sotuvchining uch xil telefon shakli BITTA E.164 ga tushadi, iflos/surilgan fayllar rad etilganda SANOQ qayta o'lchanadi. **O'zim ishga tushirdim, yashil** |

**Score: 9/9 truths verified** (ogohlantirishlar bilan; birorta BLOCKER yo'q)

---

### Bo'shliqlarni yopish bo'yicha bandma-band tekshiruv

Oldingi hisobotning `missing[]` ro'yxatlarining **HAR BIR bandi** alohida bosildi:

| Oldingi `missing[]` bandi | Holat | Kodbazadagi dalil |
|---|---|---|
| `(app)/layout.tsx` da `/markets/new` ni redirectdan ozod qilish | ✓ | `layout.tsx:62` `const needsMarket = pathname !== WIZARD_NEW_PATH;` — **TENGLIK**, prefiks emas. Ijrochining `startsWith` bo'lsa butun `(app)` daraxti ochilardi degan da'vosi TO'G'RI va u ikki joyda qulflangan: `wizard-reachability.test.mjs:142-147` (`startsWith|includes|match` taqiqi) va `layout.test.tsx:175` (`/markets/new-anything` istisnoga tushmasligi). Shuningdek `ready` ifodasi ham AYNI `needsMarket` ni ishlatadi — usiz redirect yo'qolib, ekran abadiy skelet bo'lardi (bu ham qulflangan) |
| `app-shell.tsx` ga `market_manage`-himoyalangan yozuv | ✓ | `app-shell.tsx:154-160`; `NavItem.href` union tipiga ham qo'shilgan (63-qator), ya'ni yozuv o'chirilsa TS xatosi |
| `market-picker.tsx` bo'sh holatiga havola | ✓ | `market-picker.tsx:170-177`; «Chiqish» SAQLANGAN (`canCreate === false` bo'lgan foydalanuvchi qamalib qolmaydi) va bu alohida assert bilan qulflangan |
| 02-VALIDATION.md Manual-Only #2 ni qayta o'tkazish | ⏳ ODAMGA | To'siq yo'qoldi, kuzatuvning O'ZI hali bajarilmagan → `human_verification[0]` |
| Uchala marshrutga `Depends(audit_read(TABLE_STALLS, ...))` | ✓ | `stalls.py:131-134` + `assignments.py:132-134`; ikkinchi talab (`VENDOR_VIEW`) MARSHRUT DEKORATORIDA — FastAPI dekorator bog'liqliklarini imzo parametrlaridan OLDIN hal qiladi, ya'ni 403 olgan so'rov `audit_read` gacha YETIB BORMAYDI va jurnalda YOLG'ON dalil qolmaydi |
| `MARKET_DATA_VIEW`/`VENDOR_VIEW` chegarasini aniqlash | ✓ | `rbac.py:72-118` docstringlari qayta yozilgan; `test_market_data_view_holders_already_have_vendor_view` yangi talab BIRORTA amaldagi rolning kirishini toraytirmaganini matritsa ustida isbotlaydi |
| Har bir domen so'rov kalitini `market_id` bilan doiralash | ✓ (2 ta meros istisno bilan — WARN-2) | `market-queries.ts:116-138`; `queries.ts` dagi `["users"]` va `["audit"]` doiralanmagan |
| Bozor almashtirilganda va logout'da `queryClient.clear()` | ✓ | `query-projector` zanjiri: `auth-store.ts:135-232` -> `query-provider.tsx:73` |
| Ma'muriyatdan beshta hujjatni olish | ⏳ ODAMGA (darvoza EMAS) | ROADMAP qayta ta'rifi bo'yicha faza darvozasidan chiqarildi → `human_verification[1]` |
| `scripts/karmana-import.mjs` orqali real faylni yuklash | ⏳ ODAMGA (darvoza EMAS) | Yo'l qurilgan va hujjatlashtirilgan; 600 qatorlik quruq mashq bajarilgan |

**Ikki istisnoni alohida tekshirdim** (topshiriq ularni nomma-nom so'ragan edi):

* **`/api/v1/me`** — istisno **ASOSLI**. Da'vo tekshirildi: `rbac.py:181` `Role.CASHIER: frozenset({Permission.PAYMENT_CREATE})` va `rbac.py:184` `Role.INSPECTOR: frozenset({Permission.OCCUPANCY_REVIEW})` — ikkalasida ham `VENDOR_VIEW` YO'Q. Ya'ni `/me` ga `VENDOR_VIEW` qo'yilsa har kassir va nazoratchi O'Z ismini ko'ra olmay 403 olardi. Bundan tashqari subyekt O'ZINING ma'lumotini o'qiydi — uchinchi shaxsning shaxsiy ma'lumoti oshkor bo'lmaydi.
* **`/api/v1/users`** — istisno **QISMAN ASOSLI** (WARN-3). D-09 ning o'z matni (1-faza `01-CONTEXT.md:31`) qamrovni «kim qaysi **sotuvchining** qarzini/ma'lumotini ko'rdi» deb yozadi, ya'ni xodimlar reestri qarorning literal doirasidan tashqarida va istisno matnga MOS. Lekin xodim telefoni ham shaxsiy ma'lumot va uning o'qilishi izsiz qolyapti. Istisno ikki tomonlama qulflangan (`test_exempt_routes_still_exist_and_have_reasons`, `test_every_exemption_is_load_bearing`) va sababi kodda yozilgan — qaror ONGLI, qarz esa OCHIQ. **Bu bo'shliq emas; bu nomlangan qarz.**

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `frontend/src/app/[locale]/(app)/layout.tsx` | Marshrut qo'riqchisi + usta istisnosi | ✓ VERIFIED | Ilgari «Gap source» edi — endi TENGLIK bilan yozilgan istisno, ikki joyda ishlatiladi (`useEffect` + `ready`) |
| `frontend/src/components/shell/app-shell.tsx` | Navigatsiya yozuvi | ✓ VERIFIED | Ilgari «Gap source» — endi `market_manage` ostida, `system` guruhida |
| `frontend/src/components/auth/market-picker.tsx` | Bo'sh holat havolasi | ✓ VERIFIED | Ilgari «Gap source» — endi huquq ostida havola + saqlangan «Chiqish» |
| `frontend/src/app/[locale]/(app)/markets/new/page.tsx` | Usta 1-qadam kirish nuqtasi | ✓ VERIFIED | Ilgari ⚠ ORPHANED — endi uch mustaqil yo'ldan yetib boriladi |
| `services/core-api/app/api/v1/stalls.py`, `assignments.py` | Reestr API + o'qish auditi | ✓ VERIFIED | Ilgari «Partially wired» — endi `audit_read` + `VENDOR_VIEW` |
| `services/core-api/app/security/audit.py` | O'qish-audit reyestri | ✓ VERIFIED | `TABLE_STALLS` iste'mol qilinadi. ⚠ `TABLE_TARIFFS` / `TABLE_MARKET_PROFILE` hamon faqat o'z ta'riflarida — LEKIN bu endi to'g'ri: ular qaytaradigan javoblarda shaxsiy maydon YO'Q, ya'ni `PERSONAL_FIELDS` darvozasi ularni ATAYIN talab qilmaydi (T-02-148 mulohazasi) |
| `frontend/src/lib/market-queries.ts` | Domen so'rov hooklari | ✓ VERIFIED | Ilgari «Partially wired» — endi kalit fabrikasi; global konstantalar o'chirilgan (bypass = TS xatosi) |
| `frontend/src/lib/auth-store.ts` + `query-provider.tsx` | Sessiya -> kesh tozalash kanali | ✓ VERIFIED | Ilgari 0 ta chaqiruv joyi — endi 3 ta (`setSession`, `clearSession`, shartli `applySession`) |
| `migrations/versions/0011_weekday_choice.py` | WR-06 tuzatishi | ✓ VERIFIED | Zanjir `0001…0011` uzluksiz; ikkala standart yo'li ham yopilgan |
| `services/core-api/app/api/v1/imports.py::import_staff` | MARKET-07 serveri | ✓ VERIFIED | Tenant kafolati + parol gigiyenasi tekshirildi (yuqorida) |
| `frontend/src/components/import/staff-credentials.tsx` + `import-panel.tsx` | MARKET-07 yuzasi | ✓ VERIFIED | `/users` sahifasiga `canManage` ostida ulangan |
| `tests/fixtures/karmana_seed.py` | Mustaqil miqyos generatori | ✓ VERIFIED | `app.*` va `xlsx_template` importlari YO'Q; `ast` darvozasi bilan qulflangan; chiqish `ops/data/karmana/local/` — `git check-ignore` tasdiqladi (`ops/data/karmana/.gitignore:25`) |
| `tests/integration/test_karmana_scale_import.py` | Level-4 dalili | ✓ VERIFIED | Ilgari ✗ DISCONNECTED — endi FLOWING |
| `tests/tenancy/test_personal_data_coverage.py` | D-09 qamrov darvozasi | ✓ VERIFIED | Marshrut grafini yuradi, manba matnini emas |
| `frontend/scripts/wizard-reachability.test.mjs` | CR-03 regressiya darvozasi | ✓ VERIFIED | Izoh qatorlari filtrlanadi (aks holda darvoza o'z-o'ziga qarshi ishlardi) |
| `scripts/check-validation-signoff.mjs` | `nyquist_compliant` ni majburlash | ✓ VERIFIED | **O'zim ishga tushirdim** — exit 0, «hisob-kitob bilan MOS», 71 Per-Task qatori / 4 inson bandi |
| `scripts/check-requirements-sync.mjs` | Checklist ↔ jadval mosligi | ✓ VERIFIED | **O'zim ishga tushirdim** — exit 0, 49 talab, Done 7 / Pending 42 / Blocked 0 |
| `tests/integration/test_phase2_criteria.py` | ROADMAP mezonlari darvozasi | ⚠ ESKIRGAN (WARN-1) | Hamon 5 ta SC (`test_sc1`…`test_sc5`); modul docstringi «Fazaning BESHTA muvaffaqiyat mezoni» deydi. ROADMAP'da 2026-08-01 dan beri OLTITA |

---

### Key Link Verification

| From | To | Via | Status | Details |
|---|---|---|---|---|
| `(app)/layout.tsx` | `/markets/new` | marshrut istisnosi (TENGLIK) | ✓ WIRED | `pathname !== WIZARD_NEW_PATH`; prefiks taqiqi qulflangan |
| `app-shell.tsx` `NAV_ITEMS` | `/markets/new` | navigatsiya yozuvi | ✓ WIRED | `permission: "market_manage"`, `group: "system"` |
| `market-picker.tsx` bo'sh holat | `/markets/new` | `<Link>` | ✓ WIRED | `hasPermission(..., "market_manage")` ostida |
| Bozorsiz login | `markets/new/page.tsx` ikkinchi darvozasi | `is_platform_admin` | ✓ WIRED | `auth.py:327` -> `login-form.tsx:106` -> `principal.isPlatformAdmin` |
| `stalls.py::list_stalls` / `get_stall` | `audit.py::audit_read` | `Depends(...)` | ✓ WIRED | + `VENDOR_VIEW` dekoratorda (403 auditdan OLDIN) |
| `assignments.py::list_stall_assignments` | `audit.py::audit_read` | `Depends(...)` | ✓ WIRED | `reason="stall_assignments_view"` — `vendor_view` dan ATAYIN farqli |
| `market-queries.ts` kalitlari | `market_id` | `domainKey(marketId, ...)` | ✓ WIRED | 14 ta kalit fabrikasi |
| `auth-store.ts` | `QueryClient.clear()` | `subscribeSessionReset` kanali | ✓ WIRED | `listeners` dan ATAYIN ALOHIDA to'plam (har `locale` yangilanishida tozalamaslik uchun) |
| `queries.ts::USERS_QUERY_KEY` | `market_id` | — | ⚠ NOT_WIRED (meros) | Faqat `client.clear()` bilan himoyalangan — WARN-2 |
| `queries.ts` `["audit", filters]` | `market_id` | — | ⚠ NOT_WIRED (meros) | Ayni holat |
| `market-requisites-form.tsx` | `open_weekdays` | forma maydoni -> API | ✓ WIRED | `market-requisites-form.tsx:268`; WR-06 yopildi |
| `users/page.tsx` | `POST /imports/staff` | `<ImportPanel kind="staff" />` | ✓ WIRED | `canManage` ostida |
| `karmana_seed.py` | `POST /imports/stalls` va `/vendors` | test HTTP klienti | ✓ WIRED (haqiqiy yuk bilan) | 600 + 480 qator |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|---|---|---|---|---|
| Import quvuri (`imports.py` + reyestr ekranlari) | rasta / sotuvchi qatorlari | `karmana_seed.py` — quvurdan MUSTAQIL generator | Ha — 600 rasta, 480 sotuvchi haqiqatan yozildi; sanoq, taqsimot va E.164 normallash assertion bilan o'lchandi | ✓ FLOWING (ilgari ✗ DISCONNECTED) |
| `staff-credentials.tsx` | `credentials[]` | `POST /imports/staff` javobi | Ha — ochiq parollar javobda keladi, DB'ga faqat hash yoziladi | ✓ FLOWING |
| Usta `activation-panel.tsx` | `setup-status` sanoqlari | `GET /markets/{id}/setup-status` (fail-closed CTE) | Ha — `calendar_missing` endi HAQIQATAN yonishi mumkin (0011) | ✓ FLOWING |
| `stall-map.tsx` grid | zona/rasta kataklari | `GET /stalls/map` | Ha — 600 rasta miqyosida ham o'lchandi | ✓ FLOWING |

---

### Behavioral Spot-Checks (mustaqil bajarildi — SUMMARY da'volari EMAS)

| Behavior | Command | Result | Status |
|---|---|---|---|
| Frontend to'plami | `npm --prefix frontend test` | `57 node pass / 0 fail` + `74 vitest passed (11 files)`, 10.13 s | ✓ PASS |
| Usta yo'lining uchala to'sig'i | (yuqoridagi `node --test` ichida) | `1-to'siq` ✔ · `2-to'siq` ✔ · `3-to'siq` ✔ | ✓ PASS |
| Generator mustaqilligi + D-09 qamrov darvozasi | `pytest tests/unit/test_karmana_seed.py tests/tenancy/test_personal_data_coverage.py -q` | 23 passed | ✓ PASS |
| Karmana miqyosi + shaxsiy ma'lumot auditi | `pytest tests/integration/test_karmana_scale_import.py tests/integration/test_personal_data_audit.py -q` | 9 passed | ✓ PASS |
| Faza mezonlari + xodimlar importi + usta oqimi | `pytest tests/integration/test_phase2_criteria.py tests/integration/test_staff_import.py tests/integration/test_wizard_flow.py -q` | 54 passed | ✓ PASS |
| Tenant izolyatsiyasi darvozasi | `pytest tests/tenancy -q` | **322 passed** — da'vo bilan AYNAN mos | ✓ PASS |
| Backend test sanog'i da'vosi (992) | `pytest --collect-only -q` + yig'indi | **TOTAL: 992** — da'vo bilan AYNAN mos | ✓ PASS |
| `nyquist_compliant` hisob-kitobi | `node scripts/check-validation-signoff.mjs` | exit 0, «MOS», 71 qator / 4 inson bandi | ✓ PASS |
| REQUIREMENTS.md moslik darvozasi | `node scripts/check-requirements-sync.mjs` | exit 0, 49 talab, 7 Done | ✓ PASS |
| Seed fayllari git tarixiga tushmaydi | `git check-ignore -v ops/data/karmana/local/stalls.xlsx` | `ops/data/karmana/.gitignore:25 local/` | ✓ PASS |
| To'liq `npm run gate` (992 + 322 + 57 + 74 + lint + mypy + build) | *(yaxlit holda qayta ishga tushirilmadi)* | Qismlari alohida o'lchandi (yuqorida); `lint`/`mypy`/`next build` qismi o'lchanmadi | ? SKIP — sanoqlar aynan mos chiqqani uchun qolgan qismning yashilligi ishonarli, lekin MUSTAQIL o'lchanmagan |

**`nyquist_compliant: true` ni tekshirdim, bayroqqa ishonmadim.** Skriptning o'zi bayroqqa qiymat buyurmaydi — u to'rt qoidani (Per-Task jadvalining har qatorida buyruq + yashil holat; faylda `BAJARILMADI` qolmasligi; `human_only_verifications` to'liq to'rt kalit bilan; `automated_replacements` `was`/`now` bilan) majburlaydi va e'lon bilan hisob-kitob ajralsa exit 1 beradi. Ishga tushirdim: exit 0. **Lekin bayroqning MA'NOSI o'zgargan va buni yozib qo'yish shart:** u endi «to'rtala qo'lda tekshiruv BAJARILDI» degani emas, balki «har band yo avtomatlashtirildi, yo egasi va sharti bilan `human_only_verifications` ga KO'CHIRILDI» degani. To'rt band hamon bajarilmagan — ular endi ochiq nomlangan.

---

### Probe Execution

`scripts/*/tests/probe-*.sh` shaklidagi fayl repoda YO'Q va birorta PLAN/SUMMARY probe e'lon qilmagan.

**Step 7c: SKIPPED** (bu faza uchun probe yo'q). Uning o'rnini yuqoridagi to'qqizta mustaqil bajarilgan buyruq bosdi.

---

### Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
|---|---|---|---|---|
| MARKET-01 | 02-01, 02-02, 02-11, 02-16, **02-18** | Usta orqali bozor yaratish | ✓ SATISFIED (hukm bilan — pastga qarang) | CR-03 yopildi; `test_sc1` + 3 to'siq darvozasi yashil |
| MARKET-02 | 02-01, 02-02, 02-08, 02-14 | Rasta reestri | ✓ SATISFIED | SC#2 regressiyasi yashil |
| MARKET-03 | 02-01, 02-07, 02-09, 02-15 | Tarixiy tarif | ✓ SATISFIED | SC#3 regressiyasi yashil |
| MARKET-04 | 02-01, 02-07, 02-10, 02-15, **02-19** | Sotuvchi reestri + biriktirish | ✓ SATISFIED | CR-02 yopildi; qamrov endi QOIDA (marshrut grafi darvozasi) |
| MARKET-05 | 02-06, 02-07, 02-09, 02-15, **02-21** | Ish kunlari / bayram | ✓ SATISFIED (ogohlantirish YOPILDI) | `0011` + usta hafta tanlovi |
| MARKET-06 | 02-02, 02-08, 02-14 | Sxematik plan-xarita | ✓ SATISFIED | SC#5 yashil |
| MARKET-07 | **02-24** | Xodimlar rosterining ommaviy importi | ✓ SATISFIED | 21 test yashil; UI ulangan; tenant va parol kafolatlari tekshirildi |

**Orphaned requirements: yo'q.** `REQUIREMENTS.md` Phase 2 ga 7 ta ID biriktiradi va yettalasi ham reja `requirements:` maydonlarida uchraydi.

**MARKET-01 ning `Done` belgisi — hukm bilan qo'yilgani haqidagi savolga javob: QABUL QILAMAN, lekin shartli.**

Sabablari:
1. `REQUIREMENTS.md` belgi ma'nosini **fayl ichida qayta ta'riflaydi**: «Belgi «faza to'liq yopildi» degani EMAS» va chalkashish mumkin bo'lgan **uchta joyni nomma-nom sanaydi** (real ma'lumot sharti; MARKET-01 ning kamera/kamera-zona/kadr jadvali qadamlari; odam ishtirokidagi tasdiqlar). Ya'ni belgi yolg'on signal bermaydi — u o'z chegarasini o'zi e'lon qiladi.
2. MARKET-01 matni **sakkiz** qadamni sanaydi, 2-faza **beshtasini** yetkazadi; qolgan uchtasi ROADMAP §Phase 2 `Note` bo'yicha 3–5 fazalarga tegishli. Bu farq 02-22 tomonidan reja talab qilmagan holda ATAYIN yozilgan — jim qoldirilsa, aynan shu qayta tekshiruv «belgi asossiz» degan xulosaga kelardi.
3. Mexanik yarmi to'liq isbotlangan; foydalanuvchanlik yarmi egasi va sharti bilan ochiq yuritilyapti.

**Sharti:** MARKET-01 — yettitasining ichida eng zaifi. Foydalanuvchanlik kuzatuvi to'xtash nuqtasini topsa, bu belgi `Pending` ga QAYTARILISHI kerak, `02-VALIDATION.md` da izoh bilan yopib qo'yilmasin.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|---|---|---|---|---|
| — | — | `TBD` / `FIXME` / `XXX` skaneri (`services/`, `frontend/src/`, `frontend/scripts/`, `tests/`, `scripts/`, `migrations/`) | ℹ️ Info | **TOZA** — 0 ta uchrash (telefon namunasi `+998XXXXXXXXX` filtrlangandan keyin). Darvoza qoidasi buzilmagan |
| `frontend/src/components/wizard/wizard-steps.ts` | 144 | `CAMERA_PLACEHOLDER` | ℹ️ Info | D-16 bo'yicha ATAYIN: usta 6-qadami 3-fazada ulanadi va bu ekranda ochiq e'lon qilinadi — stub emas, hujjatlashtirilgan holat |
| `frontend/src/lib/market-queries.ts` | 72 vs 1062 | Ichki qarama-qarshilik: «ISTISNO YO'Q» da'vosi vs `staff` tarmog'ining o'z e'tirofi | ⚠️ Warning | WARN-2. Ikkinchi joy halol, birinchisi eskirgan — keyingi o'quvchini chalg'itadi |
| `tests/integration/test_phase2_criteria.py` | 1 | Modul docstringi «BESHTA mezon» deydi, ROADMAP'da OLTITA | ⚠️ Warning | WARN-1. Faylning butun ma'nosi ROADMAP matni bilan bog'lanishida edi |

**Blocker darajasidagi qarz markeri topilmadi.**

---

### Ochiq qolgan va JIM YUTILMAYDIGAN bandlar

Topshiriq ikkitasini nomma-nom eslatgan edi; ikkalasi ham shu hisobotda ochiq turadi:

1. **Foydalanuvchanlik kuzatuvi** — bajarilmagan, egasi bor (platforma admini + mahsulot egasi), sharti bor (pilot tayyorgarligi haftasi). Aynan shu sabab bu hisobotning statusi `passed` emas, `human_needed`. To'siq yo'qoldi, kuzatuvning o'zi qoldi.
2. **WR-02** — `market_delete_draft()` o'n ikki jadval bo'ylab kaskad o'chiradi va uning yagona chegarasi ilova qatlami. 3-fazaga YUQORI ustuvorlik bilan eskalatsiya qilingan, sababi (yangi migratsiya kerak, `0011` bilan aralashtirish downgrade'ni ishonchsiz qilardi) asosli. **⚠ WARN-4: eskalatsiya `02-CONTEXT.md` va `STATE.md §Decisions` da yashaydi, lekin ROADMAP §Phase 3 ning `Success Criteria` sida YO'Q** — 3-faza rejalashtiruvchisi ROADMAP'dan buni ko'rmaydi. Tavsiya: Phase 3 ning mezonlariga bir qatorlik band qo'shilsin.

Bularga qo'shimcha, o'z tekshiruvim ochgan ikki band: **WARN-1** (mezon darvozasi ROADMAP'dan orqada qoldi) va **WARN-2** (ikkita meros global kesh kaliti + yangi global kalitni to'sadigan darvozaning yo'qligi).

---

### Gaps Summary

**Bo'shliq yo'q. To'rtala bo'shliq ham yopilgan va yopilish SUMMARY da'vosi bilan emas, kodbaza va mustaqil bajarilgan buyruqlar bilan tasdiqlandi.**

Adversarial pozitsiya saqlandi: boshlang'ich gipoteza «oltita reja o'z-o'ziga yashil deb hisobot berdi, demak bo'shliq bordir» edi. Uni yiqitish uchun har bo'shliqning `missing[]` bandi alohida bosildi, ikkita ayblov nuqtasi (`/me` va `/users` istisnolari) qaror matnigacha (`01-CONTEXT.md:31` D-09) va rol matritsasigacha (`rbac.py:181`) kuzatildi, generatorning mustaqilligi import ro'yxati darajasida o'qildi, sanoq da'volari (`992`, `322`, `57`, `74`) esa qayta o'lchandi va **to'rttasi ham aynan mos chiqdi**.

Birinchi tekshiruvdan farqli o'laroq, bu safar yashil darvoza yolg'iz dalil emas: yopilishlarning har biri **QOIDAGA** aylantirilgan, bir martalik tuzatish holida qoldirilmagan —

* usta yo'li → uchta mustaqil to'siqning har birini alohida nomlab qizartiradigan manba darvozasi;
* o'qish auditi → marshrut GRAFI bo'yicha yuradigan qamrov darvozasi (yangi `vendor_name` qaytaradigan endpoint yozgan odam CI'ni qizartiradi);
* kesh chegarasi → doiralash va tozalash ATAYIN alohida o'lchanadi (bittasi o'chirilsa ikkinchisi uni yopib turmasligi uchun);
* import qobiliyati → generatorning quvurga qaytishini `ast` bilan taqiqlaydigan darvoza.

Bu — «bugungi xatoni tuzatish» emas, «xatoning qaytishini bloklash» sinfidagi ish, ya'ni birinchi tekshiruvning asosiy tanqidiga to'g'ridan-to'g'ri javob.

**Nega baribir `passed` emas:** to'rtta odam ishtirokidagi tasdiq ochiq (`human_verification`), va ulardan biri — foydalanuvchanlik kuzatuvi — SC#1 ning «kod yozilmaydi» da'vosining **ikkinchi yarmi**. Mexanik yarmi isbotlangan; foydalanuvchanlik yarmini mashina ayta olmaydi. To'rt ogohlantirish (WARN-1…WARN-4) fazani bloklamaydi va keyingi fazaga o'tishga to'sqinlik qilmaydi, lekin ularning hech biri yopilgan deb hisoblanmasin.

---

_Verified: 2026-08-03_
_Verifier: Claude (gsd-verifier) — qayta tekshiruv, 2026-08-01 dagi `gaps_found` (4/8) dan keyin_
