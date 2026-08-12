# 7-faza — keyinga qoldirilgan bandlar

Bu fayl ijro davomida topilgan, lekin **joriy rejaning qamrovidan
tashqaridagi** bandlarni qayd etadi. Ular tuzatilmaydi — egasi
belgilanadi.

---

## 1. ✅ YOPILDI (07-17) — `ALERT_TITLE_KEYS` uchala locale bilan MEXANIK bog'lanmagan edi

> **Yopildi:** 07-17 ijrosi, `frontend/scripts/snapshot-copy.test.mjs`
> ga **G-36** bloki qo'shildi (147 satr, `error-codes.test.mjs` ning
> G-17 naqshi):
>
> * **o'lcham qulfi** — `ALERT_TITLE_KEY_COUNT = 15` (parser sinsa
>   sikllar bo'sh to'plamda jimgina yashil bo'lardi);
> * **OLDINGA** — har turning matni uchala locale'da bor;
> * **TESKARI** — har matn kaliti reyestrda bor (o'lik kalit yo'q);
> * **zaxira yorliq** (`errors.generic`) ALOHIDA o'lchanadi — u
>   `snapshots.alertKey.*` guruhidan tashqarida, ya'ni teskari skanni
>   ifloslantirmaydi, lekin noma'lum tur uchun AYNAN u chiziladi.
>
> ⛔ **SABOTAJ BAJARILDI:** 16-a'zo (`sabotage_probe`) matnsiz
> qo'shilganda **ikki** darvoza qizardi — o'lcham qulfi (`16 != 15`) va
> OLDINGA parity **uchala locale'ni nomma-nom** ko'rsatib. Sabotaj
> qaytarildi.
>
> ⚠ **Quyidagi «Qo'shimcha» bandi OCHIQ QOLDI:** `alert-list.test.tsx`
> hamon 07-14 ning to'rt yangi kalitini **render qilmaydi**. G-36 matn
> MAVJUDLIGINI qo'riqlaydi, CHIZILISHINI emas — bu boshqa sinf va u
> 8-fazaning ishi.

**Asl yozuv (2026-08-11, 07-15):**

**Topildi:** 07-15 ijrosi, `frontend/node_modules` birinchi marta
o'rnatilgandan keyingi to'liq o'lchovda.

**Fayl:** `frontend/src/components/snapshots/alert-row.tsx:107-124`

**Holat — O'LCHANDI, hammasi TOZA:**

| O'lchov | Natija |
|---|---|
| `ALERT_TITLE_KEYS` a'zolari | **15** |
| 15 kalit × 3 locale matni mavjudmi | ⛔ **HAMMASI BOR** — yetishmagani **0** |
| `alert-list.test.tsx` ni yugurtirish | **yashil** (to'liq to'plamning bir qismi) |

**Bo'shliq:** yuqoridagi «15 × 3» tekshiruvi ⛔ **qo'lda** bajarildi.
`frontend/scripts/*.test.mjs` ichida `ALERT_TITLE_KEYS` ni
`messages/*.json` bilan bog'laydigan **birorta darvoza yo'q**
(`grep -n "alertKey\|ALERT_TITLE" frontend/scripts/*.test.mjs` → **0**).

Ya'ni: 07-08 (uchala locale matni) va 07-14 (to'rt yangi a'zo) ning
ishi **bugun to'g'ri**, lekin uni ushlab turadigan mexanizm **yo'q** —
o'n oltinchi a'zo matnsiz qo'shilsa, ekranda zaxira yorliq chiqardi va
buni **hech nima aytmasdi**. Bu `error-codes.test.mjs` (G-17) allaqachon
yopgan sinfning aynan o'zi, faqat boshqa reyestr ustida.

**Qo'shimcha:** `alert-list.test.tsx` 07-14 ning to'rt yangi kalitidan
(`outbox_stale`, `reconciliation_stale`, `digest_stale`, `overdue_stale`)
**birortasini ham render qilmaydi** — ya'ni ular **chizilgan holda**
o'lchanmagan.

**Nega 07-15 da tuzatilmadi:** fayl `components/snapshots/**` da va
07-15 ning fayl to'plamidan **tashqarida**; tuzatish `snapshot-copy.test.mjs`
ga yangi blok qo'shishni talab qiladi.

**Egasi:** 07-17 (faza yakuni) yoki 8-faza. Shakli tayyor:
`error-codes.test.mjs` ning `RECON_ERROR_CODES` bloki — reyestrdan
**oldinga** (kalit → matn) va **teskari** (matn → kalit) yuradigan
o'n besh qatorlik naqsh.

---

## 2. `/reconciliation` sahifasi ikkita qo'shimcha so'rov qiladi

**Manba:** 07-UI-SPEC §5.5 ning **o'z** ochiq narxi.

Sotuvchi ismi klientda `GET /vendors` bilan joinlanadi
(`lib/vendor-labels.ts`) va reestrning **birinchi sahifasi** bilan
cheklanadi. 50 dan ortiq sotuvchili bozorda ro'yxatning quyi qismidagi
qatorlar «Ko'rsatilmagan» yorlig'ini olishi mumkin.

⛔ **To'g'ri tuzatish — MAVJUD marshrutni sahifalash**, nomuvofiqlik
marshrutiga ism maydoni **qo'shish EMAS** (07-10 buni sabotaj bilan
o'lchagan: ism qo'shilganda to'rt tenancy testi qizaradi).

**Egasi:** 8-faza (§5.5 shu bandni `deferred-items.md` ning 9-bandi
bilan bir sinfga qo'ygan).

---

## 3. `test_overdue_reminder_is_held_by_quiet_hours` — DEVOR SOATIGA bog'liq

**Topildi:** 07-19 ijrosi (2026-08-12, mahalliy vaqt ~23:03).

**Fayl:** `tests/integration/test_notifications.py:711-773`

**Nosozlik:** test nazorat bandi uchun kvitansiya qatorini
`outbox_repo.enqueue()` bilan yozadi. `notification_outbox.next_attempt_at`
ning `server_default` i — `now()`, ya'ni qator **HAQIQIY** server
soatidan muddat oladi. Keyin `claim(now=_wall(today, time(22, 30)))`
chaqiriladi va `_CLAIM_DUE` ning `o.next_attempt_at <= :now` sharti
**mahalliy vaqt 22:30 dan keyin** yugurgan har qanday yugurishda
YOLG'ON bo'ladi — qator olinmaydi va nazorat bandi qulaydi:

```
assert 'payment_receipt' in set()
```

Ya'ni test **kuniga ~1.5 soat** (22:30 → 00:00) qizil bo'ladi.

**⛔ 07-19 NING O'ZGARISHI SABAB EMAS — O'LCHANDI:** ikkala mahsulot
fayli (`jobs/outbox.py`, `repositories/outbox_repo.py`) `3b1e964`
holatiga qaytarilib, AYNAN shu test qayta yugurtirildi — u **BAZADA
HAM QIZIL**. Fayllar `git checkout --` bilan tiklandi.

**Nega 07-19 da tuzatilmadi:** `tests/integration/test_notifications.py`
rejaning `files_modified` ro'yxatidan **tashqarida** va nosozlik
navbat mexanikasiga umuman aloqador emas.

**To'g'ri tuzatish:** kvitansiya qatorini `next_attempt_at` ni ANIQ
berib seed qilish (`seed_outbox_row(..., next_attempt_at=quiet_moment -
timedelta(hours=1))`) — `test_outbox.py` va `test_outbox_repo.py` dagi
barcha o'lchovlar allaqachon shu naqshni ishlatadi. `enqueue()` ning
idempotentligi bu testning predmeti EMAS, ya'ni mahsulot yo'lidan
yurishning bu yerda hech qanday qiymati yo'q.

**Egasi:** faza yakuni — `07-21` ga topshirildi (`notifications.py` uning fayl ro'yxatida).

---

## 4. `market_notification_settings` AUDIT ostida emas — direktor chatining tarixi yo'q

**Manba:** 07-18 ijrosi (`binding_repo.bind_director()` yozilgan reja).

07-18 `market_notification_settings.director_chat_id` ga **birinchi
yozuv yo'lini** ochdi: direktor botga kontakt ulashadi va uning chati
`UPSERT` bilan yoziladi. Ya'ni bugundan boshlab bu ustun **o'zgaradi** —
avval unga hech qachon yozilmagan edi.

**Bo'shliq:** jadval `schema_contract.AUDITED_TABLES` da **YO'Q**, ya'ni
«direktor chati qachon, kim tomonidan almashtirildi?» degan savolga
javob **faqat** `updated_at` (oxirgi o'zgarish payti) va tuzilmaviy
jurnal bilan beriladi. Oldingi qiymat va o'zgarishlar ketma-ketligi
**hech qayerda saqlanmaydi**.

⛔ **BU UNUTISH EMAS, TEXNIK TO'SIQ** va u
`schema_contract.AUDITED_TABLES` docstringida allaqachon nomma-nom
yozilgan: jadvalning birlamchi kaliti `market_id`, ya'ni unda `id uuid`
ustuni **yo'q**, `fn_audit_row()` esa `row_id` ni `uuid` ga keltiradi va
bunday jadvalda **har DML da yiqilardi** (`stall_code_registry` va
`nvr_credentials` bilan aynan bir xil to'siq). Ilova darajasida qo'lda
audit qatori yozish esa `revoke()` da topilgan **WR-03** nuqsonining
takrori bo'lardi.

**Nega 07-18 da tuzatilmadi:** tuzatish **migratsiya** talab qiladi
(`id uuid` ustuni + PK o'zgarishi), 07-18 esa `migrations/` ga **umuman
tegmaydi** — uning tahdid reyestridagi `T-07-SC` bandi diffda
`migrations/` bo'lmasligini talab qiladi.

⛔ **Yechim shakli allaqachon nomlangan** (o'sha docstring): jadvalga
`id uuid` ustuni **qo'shiladi**, audit funksiyasi **o'zgartirilmaydi** —
`fn_audit_row()` ni kalitsiz jadvallarga moslash uni butun sxema bo'ylab
qayta yozish bo'lardi.

**Xavf darajasi — PAST va u o'lchangan:** qiymat faqat raqamning EGASI
tomonidan (D-24 ning uch qo'riqchisi) va faqat `Role.DIRECTOR` +
`is_active` a'zosi bo'lganda yoziladi, ya'ni «begona odam chatni o'ziga
burib yubordi» stsenariysi **strukturaviy ravishda yopiq**. Yo'qolayotgan
narsa — **tarix**, ruxsat emas.

**Egasi:** 8-faza.
