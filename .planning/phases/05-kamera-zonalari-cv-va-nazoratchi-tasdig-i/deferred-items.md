# 5-faza — kechiktirilgan bandlar

Bu fayl ijro paytida topilgan, LEKIN joriy rejaning qamrovidan TASHQARIDAGI
kuzatuvlarni yozadi. Ular tuzatilmaydi: qamrovdan tashqari «kichik
tuzatish» keyingi rejalarning o'lchov bazasini jimgina siljitadi.

---

## 1. `test_alerting.py::test_an_old_alert_escalates_by_level_not_by_frequency` — SOAT BOG'LIQ

**Topildi:** 05-12, to'liq to'plamning oxirgi yugurishida (2026-08-09, ~21:00 Asia/Tashkent)

**Alomat:**

```
AssertionError: eskalatsiya bo'lmadi
assert 0 == 1  where 0 = SweepResult(..., escalated=0, resolved=1, ...).escalated
```

**Mexanizm (o'lchangan, taxmin emas):** test `moment = datetime.now(tz=MARKET_TZ)`
oladi va IKKINCHI supurgini `moment + 3 soat 1 daqiqa` bilan chaqiradi.
Mahalliy vaqt **20:59 dan keyin** bo'lganda ikkinchi nuqta YARIM TUNDAN
o'tadi, ya'ni u BOSHQA biznes-kunga tushadi. O'sha kunda «o'tkazib
yuborilgan slot» sharti umuman mavjud emas — shuning uchun alert
eskalatsiya qilinmay, **hal qilinadi** (`resolved=1`, yugurish
chiqishida ko'rinib turibdi).

**Nega 05-12 ning bandi EMAS:**

- `tests/integration/test_alerting.py` va `services/core-api/app/jobs/alerting.py`
  ikkalasi ham `b5d4f78` (05-12 dan OLDINGI HEAD) dagi bilan **bayt-bayt
  bir xil** (`git hash-object` bilan solishtirildi);
- `alerting.py` da `day_close`, `stall_slot_occupancy` yoki `occupancy`
  so'zlari **umuman uchramaydi** — ikki kod yo'li kesishmaydi;
- 05-11 ning SUMMARY si to'liq to'plamni **2134 passed, exit 0** deb
  yozgan va o'sha yugurish kun davomida bo'lgan.

**Tuzatishning shakli (bajarilMADI):** `moment` ni `datetime.now()` dan
emas, kunning BELGILANGAN nuqtasidan (masalan mahalliy 09:00) olish —
`retention_daily(today=...)` va `day_close(business_date=...)` da
o'rnatilgan «vaqt in'ektsiya qilinadi» qoidasining aynan o'zi. Bu
`04-08` ning fayliga tegadi va uning egasi `05-15` (faza darvozasi).

---

## 2. `occupancy_day_close_markets()` — HAMON CHAQIRUVCHISIZ

**Holat:** `audit_draw_due_markets()` 05-11 da chaqiruvchisiz qolgan edi;
05-12 dan keyin `occupancy_day_close_markets()` ham shu holatda.

**Sabab (ikkalasida ham AYNAN bir xil):** funksiya kunni `now()` dan
oladi va uni argument qilib bo'lmaydi, ikkala job esa `business_date` ni
argument sifatida oladi. `occupancy_day_close_markets()` da ikkinchi
sabab ham bor: uning `event_count` ustuni har qanday BOSHQA kun uchun
noto'g'ri son bo'lardi.

**Nega tuzatilmadi:** migratsiya (`0018` ning funksiyalarini
o'zgartirish) 05-12 ning fayl ro'yxatida yo'q va u **arxitektura
qarori** (Rule 4): funksiyaga argument qo'shish uning `SECURITY DEFINER`
imzosini o'zgartiradi.

**Kim uchun:** `05-15` — ikkala funksiyani ham (a) `business_date`
argumentli shaklga o'tkazish, yoki (b) ularni `0018` dan olib tashlash
kerakligi haqida ONGLI qaror. Ikkalasi ham hozir `SECURITY DEFINER`
yuzasi bo'lib turibdi va chaqiruvchisi yo'q.

---

## 3. DL-5 SLOT QATORLARI — MARSHRUT YO'Q (05-14 da o'lchandi)

**Holat:** `stall-detail-dialog.tsx` (DL-5) rastaning KUN bo'yicha
hukmini, uning manbasini va slot nisbatini ko'rsatadi. UI-SPEC §11.7
esa undan **kun davomidagi har vaqt uchun bitta qator** talab qiladi:
`vaqt · kamera · natija · manba`, va har qatordan dalil kadri ochiladi.

**Sabab — MA'LUMOT MANBASI YO'Q va bu o'lchandi:**

- `GET /occupancy` bitta rasta uchun `OccupancyStallItem` beradi va unda
  **aynan yetti maydon** bor (`stall_id`, `stall_code`, `zone_name`,
  `status`, `slots`, `occupied_slots`, `human_confirmed`);
- na slot vaqti, na kamera nomi, na `snapshot_id` — ya'ni «har qatordan
  dalil kadri» uchun kerak bo'lgan identifikator **javobda yo'q**;
- `occupancy_repo.py` da rasta-slot qatorlarini beradigan metod ham
  **yozilmagan** (`day_stalls` agregat qaytaradi).

**Rad etilgan ikki variant:** (a) qatorlarni klientda to'qib chiqarish —
soxta ma'lumot, ya'ni eng yomon shakldagi stub; (b) «tez orada» degan
bo'sh jadval — placeholder, u ham va'da berib bajarmaydi.

**Nega bu rejada tuzatilmadi:** yangi marshrut (`GET
/occupancy/stalls/{id}?day=`) + repozitoriy metodi + `REPORT_VIEW`
tegi + `MINIMUM_MATRIX_ROUTES` 60 -> 61 + `tests/tenancy` qatorlari —
**Rule 4** (arxitektura), va 05-14 ning `files_modified` ro'yxati
**faqat `frontend/`**.

**Kim uchun:** `05-15` yoki 8-faza. ⚠ Qaror bilan birga **dalil-kadr
huquq bo'shlig'i** ham hal bo'lishi kerak (1-band emas — 05-13 ning
`threat_flag` i): DL-5 dan kadr ochiladigan bo'lsa, u `CAMERA_VIEW`
talab qiladi va direktorda bu huquq **bor**, ya'ni bu yerda bo'shliq
YO'Q — bo'shliq faqat sof `inspector` da.

---

## 4. «TEZ QAROR» CHEGARASI JAVOBDA YO'Q (05-14 da o'lchandi)

**Holat:** `round-summary.tsx` «Tez qaror: N» ni ko'rsatadi, lekin
chegarani (2 soniya) **nomlamaydi**. UI-SPEC §12.6 ning matni
`{seconds} soniyadan tez` deb yozilgan.

**Sabab:** chegara `accuracy_report.is_fast_decision()` da (2000 ms) va
`GET /occupancy/round` javobida **maydon sifatida yo'q**. Uni klientda
yozish server konstantasining IKKINCHI nusxasi bo'lardi — chegara
o'zgargan kuni yorliq jimgina yolg'on gapirardi. Bu aynan 05-12 ning
`min_sample` uchun tanlagan yo'lining teskarisi bo'lardi.

**Eng tor tuzatish:** `OccupancyRoundResponse` ga bitta maydon —
`fast_decision_ms` (yoki `fast_decision_seconds`). Marshrut allaqachon
`REPORT_VIEW` ostida, ya'ni yangi huquq yuzasi **ochilmaydi** va
matritsa qatori ham o'zgarmaydi. Shundan keyin §12.6 ning matni to'liq
tiklanadi.

**Kim uchun:** `05-15` yoki 8-faza (hisobot yuzasi).

---

# 5-fazani yopish (05-15, 2026-08-10) — YUQORIDAGI TO'RT BANDNING QARORI

⚠ Bu bo'lim to'rtala bandning ham holatini **ONGLI qaror** bilan yopadi.
«Keyingi rejaga» degan jimgina uzatish bu yerda TUGAYDI: faza yopilmoqda,
ya'ni har bandning egasi va tetigi NOMLANISHI shart.

## 1. `test_alerting.py` soat bog'liqligi — ✅ TUZATILDI (05-15 dan OLDIN)

`dc5f182` (`test_an_old_alert_escalates_by_level_not_by_frequency`) va
`bcc2d49` (ikkita debounce testi) bandni yopdi. Tuzatishning shakli
bandda taklif qilinganidan **kengroq** chiqdi: bitta emas, **uchta**
test Asia/Tashkent biznes-kun chegarasidan o'tar ekan, va ulardan
birining «nazorat» juftlashi yashil turib **boshqa narsani** o'lchayotgan
edi. Fayl `04-08` niki, egasi esa bandda yozilganidek `05-15` bo'ldi.

**Holati:** yopiq. Yangi qamrov yo'q — mavjud testlar tuzatildi.

## 2. `occupancy_day_close_markets()` va `audit_draw_due_markets()` — SAQLANADI, QARORI YOZILDI

**Qaror: ikkala funksiya ham `0018` da QOLADI. Rule 4 (arxitektura).**

**Nima o'lchandi:**

- Ikkalasi ham **chaqiruvchisiz**: repo bo'yicha ularning nomi faqat
  `migrations/entities/functions.py` (ta'rif), `migrations/entities/
  __init__.py` (reyestr), `0018` (migratsiya izohi), `day_close.py:280`
  (izoh) va `tests/tenancy/test_occupancy_domain_meta.py` (darvoza) da
  uchraydi. Birorta job ularni CHAQIRMAYDI;
- ikkalasining ham qaytaradigan yuzasi **tor**: `market_id` (+
  `frame_size` butun soni). Tenant ma'lumoti, verdikt, confidence yoki
  poligon **yo'q** va bu `FORBIDDEN_SURFACE_TOKENS` darvozasi bilan
  qulflangan (`test_occupancy_domain_meta.py`), ya'ni `SECURITY DEFINER`
  bo'lishiga qaramay ular RLS'ni chetlab o'tib **ma'lumot bermaydi**.

**Nega OLIB TASHLANMADI:** `DROP FUNCTION` yangi migratsiya (`0020`)
talab qiladi va u `05-15` ning `files_modified` ro'yxatida yo'q. Bundan
muhimi — **qaror uchun ma'lumot hali yetarli emas**: 6-faza (billing)
«qaysi bozorda kun yopilishi kerak» degan tikni quradi va aynan o'shanda
bu ikki funksiya yo ISHLATILADI, yo `business_date` argumentli shaklga
ko'chiriladi, yo tushiriladi. Bugun tushirish o'sha qarorni ma'lumotsiz
qabul qilish bo'lardi.

**Egasi:** 6-fazaning billing tiki. **Tetigi:** `day_close` ni planerga
ulash rejasi. **Oraliqdagi himoya:** `DEFINER_SURFACES` darvozasi ikkala
funksiyani ham nomma-nom skanerlaydi, ya'ni ularning yuzasi kengaysa CI
qizaradi.

## 3. DL-5 slot qatorlari — QURILMAYDI, SPETSIFIKATSIYA TUZATILDI

**Qaror: yangi marshrut bu fazada qurilmaydi (Rule 4, o'zgarmadi), LEKIN
`05-UI-SPEC.md` §11.7 TUZATILDI.**

Sabab: spetsifikatsiya qurilmagan narsani ta'riflab tursa, keyingi faza
uni **yo'qolgan funksiya** deb o'qiydi va uni «tiklashga» kirishadi.
§11.7 endi **bugun qurilganini** ta'riflaydi (rastaning KUN bo'yicha
hukmi, manbasi va slot nisbati) va per-slot qatorlarning YO'QLIGINI
sababi bilan yozadi.

⚠ **Huquq bo'shlig'i bandi YOPILDI va u endi to'siq emas:** `05-15`
dalil-kadr marshrutini `CAMERA_VIEW` **yoki** `OCCUPANCY_REVIEW` ga
kengaytirdi. Ya'ni slot qatorlari qo'shilgan kuni «har qatordan dalil
kadri ochiladi» talabi **yangi huquq yuzasi ochmaydi** — direktorda
`CAMERA_VIEW` bor, nazoratchida esa endi `OCCUPANCY_REVIEW` yetarli.

**Egasi:** 8-faza (hisobot yuzasi). **Tetigi:** `RECON-04`/`RECON-05`
rejalashtirilganda. **Ish hajmi (o'lchangan):** `GET /occupancy/stalls/
{id}?day=` + `occupancy_repo` metodi + `REPORT_VIEW` tegi +
`MINIMUM_MATRIX_ROUTES` 60 -> 61 + `tests/tenancy` qatorlari.

## 4. «Tez qaror» chegarasi javobda yo'q — QURILMAYDI, MATN TUZATILDI

**Qaror: `fast_decision_ms` maydoni bu fazada QO'SHILMAYDI.**

Sabab bandning o'zida yozilgan va u kuchli: chegarani klientda yozish
server konstantasining **ikkinchi nusxasi** bo'lardi. Lekin
`05-UI-SPEC.md` §12.6 chegarani yorliqda **nomlashni talab qilardi**
(`{seconds} soniyadan tez`) — ya'ni spetsifikatsiya va shipping copy
ajralib turgan edi. **Tuzatish spetsifikatsiya tomonida:** §12.6 endi
shipping matnni (`Tez qaror` + `fastDecisionsWhy` tushuntirishi)
ta'riflaydi va §11.6 chegara nega nomlanmasligini sabab bilan yozadi.

**Egasi:** 8-faza. **Tetigi:** hisobot yuzasi kengaytirilganda.
**Ish hajmi:** `OccupancyRoundResponse` ga bitta maydon — marshrut
allaqachon `REPORT_VIEW` ostida, ya'ni yangi huquq yuzasi ochilmaydi va
matritsa qatori ham o'zgarmaydi.
