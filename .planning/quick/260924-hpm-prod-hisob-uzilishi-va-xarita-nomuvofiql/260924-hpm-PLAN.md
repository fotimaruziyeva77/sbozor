---
quick_id: 260924-hpm
type: quick
mode: quick (orchestrator inline — rejalash va bajarish bitta kontekstda)
created: 2026-09-24
status: complete
---

# Quick 260924-hpm: prod hisob uzilishi, jimjit uzilish alerti va xarita nomuvofiqligi

Buyurtmachi: «hamma sen ko'rib turgan xatolarni profisional tuzatla».

## Prod'da o'lchangan faktlar (2026-09-24)

- `daily_charges`: 22–27-avgust har kuni 41–42 qator, **28-avgustdan 24-sentabrgacha 0**;
  `payments` shu davrda kuniga 30–44 (jami ~820). 28 kun patta yozilmagan.
- Sabab: 28-avgustda CamAgent kameralari ulandi -> `camera_count > 0` -> bozor BUTUNLAY
  kamerali rejimga (D-04) o'tdi; 53 rastadan faqat 6–9 tasida zona bor, qolganlari
  `no_coverage_only` -> `_close_stall` (1)-shoxi faqat anomaliya yozib QAYTADI, hisob YO'Q.
  25-avgustdagi kamerasiz avto-rejim (`_close_market_without_cameras`) QISMAN qamrovni
  hisobga olmagan.
- Xaritadagi 5 sariq rasta (5, 21, 22, 26, 29) — 26–27-avgustdan qolgan `occupied_unpaid`
  case'lari (`new`, 4 hafta hech kim ko'rmagan); Nomuvofiqliklar sahifasi standart KECHAni
  ko'rsatadi, rasta kartasidan case kuniga havola yo'q; «ochiq nomuvofiqlik» matni «ochiq
  rasta» deb o'qiladi.
- Qarz preview (faqat-o'qish skript): 32 qarzdor, 12,27 mln (4 ta nol-to'lovli kun bilan) /
  7,28 mln (ularsiz); tarozisiz to'lovlar 156/776.
- Kamera qatoridagi manfiy «-22 s» — `41f5587` (2026-08-28) da ALLAQACHON tuzatilgan (qayta ish yo'q).

## Task 1 — Gibrid hisob qoidasi + xavfsiz tiklash (KRITIK)

files:
- services/core-api/app/jobs/billing_close.py
- services/core-api/app/repositories/billing_repo.py
- ops/scripts/backfill_charges.py
- ops/scripts/debt_preview.py (yangi, faqat-o'qish)
- tests/integration/test_billing_close.py

action:
1. `_close_stall` (1)-shox: `no_coverage_only` rastada anomaliya yozilgandan KEYIN hisob
   BIRIKTIRISH bo'yicha yoziladi — kamerasiz rejimning AYNI qoidalari bitta umumiy
   yordamchi orqali (`_charge_by_assignment`): fair/yopiq/ta'mirda/sotuvchisiz — hisob yo'q,
   tarif yo'q — `errors`, mavjud — `skipped_existing`, aks holda `charged_auto`.
   Qamrovli rastalar (zona bor) D-04 da QOLADI — o'lchov bilan bahslashilmaydi.
   Materializatsiya qilinmagan (`no_slot_rows`) rastaga TEGILMAYDI (Pitfall 2 saqlanadi).
2. `ExistingCharge.has_evidence` (`EXISTS charge_evidence`); `_late_review` dalilsiz
   (biriktirish bo'yicha yozilgan) hisobni KAMAYTIRMAYDI — keyin zona chizilib kun qayta
   yopilsa, noaniq AI hukmi avto-hisobni nolga tushirib, keyingi tasdiqda qayta yozilmay
   qolardi.
3. `backfill_charges.py`: har kun uchun avval `day_close`, keyin `billing_close`; kalendar
   ochiq, lekin bozorda bironta to'lov yo'q kunlar ro'yxati chiqariladi va ular
   `BACKFILL_ALLOW_EMPTY_DAYS` da ochiq sanalmaguncha skript HISOB YOZMASDAN to'xtaydi;
   «kamerali bozorga tegmaydi» va «rasta holati tarixiy» degan eskirgan da'volar
   tuzatiladi (holat — bugungi reyestr ustuni).
4. `debt_preview.py` — prod'da ishlatilgan faqat-o'qish qarz tekshiruvi repoga (READ ONLY
   tranzaksiya).

verify: `test_billing_close.py` to'liq yashil; yangi testlar: (a) kamerali bozorda zonasiz
biriktirilgan rasta dalilsiz avto-hisob oladi; (b) kech tasdiq dalilsiz hisobni
kamaytirmaydi; ruff + mypy toza.

done: kamerali bozorda qamrovsiz rastalarga hisob yoziladi, tiklash skripti bo'sh kunlarni
so'ramasdan hisoblamaydi.

## Task 2 — «To'lov bor, hisob yo'q» jimjit uzilish alerti

files:
- services/core-api/app/jobs/alerting.py
- tests/integration/test_alerting.py
- frontend/src/components/snapshots/alert-row.tsx
- frontend/messages/uz-Latn.json, ru.json (uz-Cyrl generatordan)
- frontend/scripts/snapshot-copy.test.mjs

action: `billing_no_charges` kaliti (warning -> 3 soatda critical, debounce qo'llanadi,
bozor kesimida). Sof `_billing_silence_signals()` + `_market_signals()` da oxirgi YOPILGAN
kun (06:00 dan keyin kecha, undan oldin — kechagidan oldingi kun, alert yarim tunda
«tiklanib» qayta tug'ilmasligi uchun) uchun: kalendar ochiq VA to'lov > 0 VA hisob = 0.
UI sarlavhasi uchala tilda.

verify: test_alerting (yangi holatlar), snapshot-copy darvozasi, i18n parity.

done: 28 kunlik sukunat takrorlansa, birinchi ertalabdayoq alert ko'tariladi.

## Task 3 — Xarita va Nomuvofiqliklar yuzasi

files:
- frontend/messages/uz-Latn.json, ru.json (+ uz-Cyrl)
- frontend/src/components/stalls/stall-card-dialog.tsx (+ test)
- services/core-api/app/repositories/reconciliation_repo.py
- services/core-api/app/api/v1/reconciliation.py, app/schemas.py
- tests/integration/test_reconciliation_api.py
- frontend/src/lib/reconciliation-queries.ts
- frontend/src/components/reconciliation/open-case-days.tsx (yangi) + page.tsx + page.test.tsx

action:
1. Matn: «ochiq nomuvofiqlik» -> «hal qilinmagan nomuvofiqlik» (legenda va holat so'zi).
2. Rasta kartasi: ochiq case bo'lsa `report_view` huquqida «Nomuvofiqlikni ochish»
   havolasi -> `/reconciliation?day=<case kuni>`.
3. `GET /reconciliation/open-days` — ochiq (`new`/`in_review`) case'li kunlar va sonlari
   (yangidan eskiga, cheklangan); sahifada kun tanlagichi BLOKI ICHIDA (blok to'plami
   o'zgarmaydi — G-29) «Boshqa kunlarda hal qilinmagan ishlar» e'loni, har kun havola.

verify: backend integratsiya testi (ikki bozor izolyatsiyasi bilan), page.test (mock + yangi
da'vo), stall-card testi, tsc, node darvozalari.

done: sariq rastadan bir bosishda o'sha kunning case'iga o'tiladi; eski ochiq ishlar
sahifada ko'rinadi.

## Tashqarida qoladi (ongli)

- Case'ni to'lov kelganda avtomatik yopish — D-C2 qulflangan mahsulot qarori («pul keldi»
  «bu to'g'rimi?» savolini yopmaydi); o'rniga topiluvchanlik tuzatiladi.
- Rasta holati tarixi (yopilgan rastaning o'tgan kunlari) — sxema o'zgarishi; tiklash
  skripti cheklovni ochiq aytadi.
- Prod'ga deploy va tiklashni yurgizish — buyurtmachi qarori (bo'sh kunlar va «kelmagan
  sotuvchi» siyosati) talab qilinadi.
