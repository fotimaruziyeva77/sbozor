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

## 3. ✅ YOPILDI (07-21) — `test_overdue_reminder_is_held_by_quiet_hours` DEVOR SOATIGA bog'liq edi

> **Yopildi:** 07-21 ijrosi (2026-08-13). Nazorat qatori endi
> `outbox_repo.enqueue()` bilan emas, `seed_outbox_row(...,
> next_attempt_at=quiet_moment - timedelta(hours=1))` bilan seed
> qilinadi — ya'ni muddat SERVER soatidan emas, testning O'ZIDAN
> keladi.
>
> ⛔ **QO'SHIMCHA TUZATISH (bandda nomlanmagan, lekin AYNI SINF):**
> eslatma qatorining muddati ham `_set_due()` bilan qadaladi. Usiz
> «22:30 da eslatma OLINMAYDI» da'vosi mahalliy vaqt 22:30 dan keyin
> **bo'sh-rost** bo'lardi — qator quiet oyna tufayli emas, MUDDATI
> kelmagani uchun qolib ketardi va quiet-hours darvozasi butunlay
> buzuq holatda ham test yashil bo'lardi. Ya'ni band tuzatilganda
> testning IKKINCHI yarmi hamon ko'r bo'lib qolardi.
>
> ⛔ **SABOTAJ BAJARILDI (ikki yo'nalishli zond, 05:11 da — ya'ni
> muammoli oynadan TASHQARIDA):** `claim(now=...)` o'tmishdagi, lekin
> quiet oyna ichidagi paytga (`04:00`) qo'yildi va ikkita zond testi
> yugurtirildi:
>
> * `enqueue()` bilan seed qilingan qator ⛔ **OLINMADI** (qizil) —
>   nosozlik aynan takrorlandi;
> * aniq `next_attempt_at` bilan seed qilingan qator **OLINDI**
>   (yashil).
>
> Zond fayli o'lchovdan keyin o'chirildi. Ya'ni tuzatish soatni
> siljitmasdan, HAQIQIY nosozlik holatida o'lchandi.

**Asl yozuv (2026-08-12, 07-19):**

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

⚠ **07-21 QO'SHIMCHASI:** o'sha rejada `binding_repo.revoke()` dagi
qo'lda yozilgan audit chaqiruvi **butunlay olib tashlandi** (WR-03) —
`vendor_telegram_bindings` ham `AUDITED_TABLES` dan ATAYIN chiqarilgan
va kod endi reyestr bilan bir narsani aytadi. Ya'ni bu band **yagona
qolgan** «auditsiz jadval» holati emas, lekin u **yagona qolgan
BO'SHLIQ**: `vendor_telegram_bindings` da tarix jadvalning O'ZIDA
saqlanadi (`revoked_at` / `revoked_reason`), `market_notification_
settings` da esa **hech qayerda** saqlanmaydi.

---

## 5. ✅ YOPILDI (07-21) — `npm run up` botni ko'tarmasdi, `bot-tests` prod tokenini meros olardi

> Ikkala band ham bu faylda **ilgari umuman qayd etilmagan edi** —
> ular `07-REVIEW-frontend.md` da (CR-03 va WR-10) topilib, to'g'ridan-
> to'g'ri 07-21 ga berildi.

**B-8 — `npm run up` `bot-service` ni ko'tarmasdi.**
`compose.yaml:601-605` OCHIQ da'vo qiladi: «PROFILSIZ … `npm run up`
uni ham ko'taradi». `package.json` ning `scripts.up` satrida esa
`bot-service` **umuman yo'q** edi. Nosozlik hech qanday xato bermasdi:
sotuvchi botga yozardi, javob esa **hech qachon** kelmasdi — fazaning
mahsuloti hujjatlashtirilgan buyruq bilan ishga tushmasdi.

**B-9 — `bot-tests` PROD tokenlarini meros olardi.**
`${TELEGRAM_BOT_TOKEN:-…}` shakli **standart emas, MAJBURLASH**: u
faqat o'zgaruvchi BO'SH bo'lganda ishlaydi, ya'ni ishlaydigan har
qanday `.env` da test konteyneriga prod Telegram va prod servis tokeni
oqib o'tardi. `app/main.py` `Bot(token=…)` ni **modul darajasida**
quradi, ya'ni tasodifiy tarmoq chaqirig'i prod botni `409 Conflict`
bilan jim qoldirishi mumkin edi (DQ-1).

> **Yopildi:** `scripts.up` ga `bot-service` qo'shildi; `bot-tests`
> blokidagi ikkala token **literal** yozildi. Darvoza —
> `tests/unit/test_dev_environment.py` (to'rt test, Docker talab
> qilmaydi).
>
> ⛔ **NAZORAT BANDI DARVOZANING YARMI:** test «hamma joyda literal»
> ni emas, AYNAN test konteynerining ajratilganini o'lchaydi —
> `bot-service` blokida `${` **BOR** bo'lishi ham talab qilinadi. Usiz
> butun faylda interpolyatsiya o'chirilganda ham darvoza yashil
> bo'lardi va o'shanda mahsulot bloki tokenni muhitdan olmay qo'yardi.
>
> ⛔ **SABOTAJ BAJARILDI:** `${TELEGRAM_BOT_TOKEN:-…}` qaytarilganda
> darvoza qiymatni **nomma-nom ko'rsatib** qizardi. Qaytarildi.
>
> **O'LCHOV (empirik):** muhitga «prodga o'xshash» token qo'yib
> `docker compose config bot-tests bot-service` yugurtirildi —
> `bot-service` uni **oldi** (to'g'ri, mahsulot yo'li),
> `bot-tests` esa **literal qiymatda qoldi**. Tuzatishdan oldin
> `bot-tests` ham o'sha tokenni ko'rsatardi.

⚠ **OCHIQ QOLDI:** `npm run up` ning O'ZI **yugurtirilmadi** — u
standart compose loyihasiga (`sbozor`) tegadi va foydalanuvchining
**jonli stekidagi** `cv-service` ni qayta ishga tushirardi (u ATAYIN
to'xtatilgan: `CV_MODEL_PATH` artefakti yo'q va konteyner ~1 s da bir
qayta ishga tushib, xostning ~80 % CPU sini yeydi — `package.json` ning
`//gate-budget` izohida o'lchangan). Ajratilgan loyihada yugurtirish
esa `bot-service` ning `runtime` image'ini **qurishni** talab qiladi va
bu muhitda Docker Hub'ga tarmoq yo'q. O'rniga ikki mexanik o'lchov
bajarildi: `docker compose config` **xatosiz**, va darvozaning
4-testi `scripts.up` da nomlangan HAR servis `compose.yaml` da
mavjudligini tekshiradi. **Egasi:** dev mashinasida bir marta qo'lda
tasdiqlash (8-faza yoki faza yakuni).

---

## 6. ONGLI NARX — dayjest o'limi uchun alert kaliti BITTA (`digest_stale`)

**Manba:** 07-21 (WR-10) ning o'z qarori.

07-21 `notify_digest` ni ikki komponentga bo'ldi
(`notify_digest_morning` / `notify_digest_evening`) va ikkalasini ham
`alerting._platform_signals::watched` ga qo'shdi. Lekin **alert kaliti
bitta qoldi**: ikkala juftlik ham `digest_stale` ga bog'lanadi.

**Nega:** ikkinchi kalit `ALERT_META` reyestriga, frontend ning
`ALERT_TITLE_KEYS` xaritasiga va uchala locale matniga tegardi — ya'ni
sof backend o'zgarishi ikkita frontend faylni o'ziga tortardi va
`snapshot-copy.test.mjs` ning G-36 o'lcham qulfini (`ALERT_TITLE_KEY_
COUNT = 15`) ham siljitardi.

**Nima yo'qolmadi:** operatorga kerakli FAKT («dayjest o'lgan») bitta
kalit bilan ham to'liq yetadi, QAYSI BIRI o'lgani esa
`/internal/self-check` ning `stale` va `never_seen` ro'yxatlarida
**nomma-nom** ko'rinadi. `_upsert()` ning debounce'i ikki signalni
bitta qatorga yig'adi (`occurrences` o'sadi), ya'ni ikkala dayjest ham
o'lgan kunda admin **ikki emas, bitta** xabar oladi.

**Egasi:** 8-faza — agar amaliyotda «qaysi dayjest?» savoli Telegram
xabarining O'ZIDA kerak bo'lsa.

---

## 7. ⛔ ATAYIN REJALASHTIRILMAGAN KO'RIK TOPILMALARI — EGASI BILAN

**Manba:** `07-REVIEW-backend.md` va `07-REVIEW-frontend.md`.

⛔ Bu blok `07-VERIFICATION.md` ning «yashirin qoldirilmasligi kerak»
talabini bajaradi: quyidagi bandlar bo'shliqni yopish to'plamiga
**kirmadi** (ular ROADMAP ning beshala mezonidan birortasini
to'g'ridan-to'g'ri buzmaydi), lekin ular **jimgina tashlab
yuborilmadi** — har biri nomma-nom, sabab va egasi bilan yozildi.

**⛔ SANOQ IKKALA KO'RIK FAYLI USTIDA QAYTA BAJARILDI (07-21), reja
matniga ishonilmadi:**

| Manba | `Warnings` | `Info` |
|---|---|---|
| `07-REVIEW-backend.md` | **10** (WR-01…WR-10) | — (bo'lim yo'q) |
| `07-REVIEW-frontend.md` | **16** (WR-01…WR-16) | **8** (IN-01…IN-08) |
| **Jami** | **26** | **8** |

Ulardan **13 tasi** hech bir bo'shliq rejasiga kirmadi. Qolgan 13 tasi
egalik qilingan: 07-19 (backend WR-07, WR-08), 07-20 (backend WR-01,
WR-05), 07-21 (backend WR-02, WR-03, WR-10 + frontend WR-01, WR-10),
07-22 (frontend WR-06, WR-08), 07-23 (frontend WR-09, WR-16).

### 7a. Rejalashtirilmagan WARNING'lar — 13 ta

| Manba | Band | Bir qatorli sabab | Egasi |
|---|---|---|---|
| backend **WR-04** | `resolve()` ning doimiy-vaqtlilik da'vosi tsikldan KEYINGI ish bilan buziladi | Tayming yana enumeratsiya oracle'iga aylanishi mumkin; tuzatish yo NAVBATNI tekislash, yo da'voni kamaytirish | 8-faza |
| backend **WR-06** | «BIR KNOB» tengligi FAQAT testda; mahsulotda ikki chegara bir kunga farq qiladi | D-19 ning buzilishi: sotuvchi ogohlantirilmagan qarz uchun case navbatiga tushardi | 8-faza |
| backend **WR-09** | `_open_unpaid_cases()` da pastki vaqt chegarasi yo'q — ko'rinmas case'lar tug'iladi | Eski hisoblar uchun case ochiladi, lekin ular hech qaysi kunning navbatida ko'rinmaydi | 8-faza (qarzdorlik reestri yuzasi bilan birga) |
| frontend **WR-02** | `on_more` da FSM ma'lumoti buzilganda ushlanmagan `ValueError` | Sotuvchi «Ko'proq» ni bosadi va MUTLAQ sukunat oladi | 8-faza |
| frontend **WR-03** | To'lov sahifalarida bozor nomi yo'q, «Ko'proq» bozorlarni aylantiradi | Ikki bozorda faol sotuvchi qaysi bozorning tarixini ko'rayotganini bilmaydi | 8-faza |
| frontend **WR-04** | Botda zaxira handler yo'q — istalgan matn mutlaq sukunat oladi | «Bot ishlamayapti» taassuroti; hech qanday xato ham chiqmaydi | 8-faza |
| frontend **WR-05** | Aniqlik ulushi bloki so'rov YIQILGANDA o'lchangan faktni da'vo qiladi | Yiqilgan so'rov «0 %» bo'lib chiziladi — o'lchanmagan holat o'lchangan nol bo'lib ko'rinadi (WR-02 bilan AYNI sinf) | 8-faza |
| frontend **WR-07** | `service_date` uch faylda uch xil chiziladi; bittasi vaqt-mintaqasiga mo'rt | Yarim tunda sana bir kun siljiydi va hisobot boshqa kunni ko'rsatadi | 8-faza |
| frontend **WR-11** | Noma'lum `severity` jimgina ENG PAST darajaga tushiriladi | Yangi `critical` daraja qo'shilsa u ekranda `info` bo'lib chiqardi | 8-faza |
| frontend **WR-12** | `alertDurationParts` `NaN` ni ekranga chiqara oladi | Foydalanuvchi «NaN daqiqa» ko'radi — tizimga ishonch yo'qoladi | 8-faza |
| frontend **WR-13** | Noma'lum `subject_kind` qatorlari IKKALA blokdan ham jimgina yo'qoladi | Yangi tur qo'shilganda qator ekranda UMUMAN ko'rinmaydi va hech nima qizarmaydi | 8-faza |
| frontend **WR-14** | `compose.yaml` dagi `NEXT_PUBLIC_API_BASE_URL` ta'sirsiz | O'lik muhit kaliti — `test_compose_sim_env.py` yopgan sinfning aynan o'zi | 8-faza |
| frontend **WR-15** | Yechim matnini TOZALASH mumkin emas, lekin forma buni va'da qiladi | Foydalanuvchi maydonni bo'shatadi, saqlaydi, eski matn QOLADI | 8-faza |

### 7b. `Info` darajasidagi bandlar — 8 ta

⚠ **REJA MATNIDAN FARQ (SUMMARY da qayd etilgan):** reja sakkizala
bandni ham «rejalashtirilmagan» deb sanagan edi. Qayta sanoqda
**IN-05** `07-22` ning `<behavior>` bandida NOMMA-NOM turibdi
(«`t("headline.amountUnit")` o'rniga `recon` … namespace'idan
o'qiladi»), ya'ni u shu to'lqinda YOPILADI. Ko'rik ustun turadi, reja
matni emas — jadval shunga muvofiq to'ldirildi.

| Band | Bir qatorli sabab | Egasi |
|---|---|---|
| **IN-01** | `bot-service/Dockerfile` da `CMD`/`ENTRYPOINT` yo'q, izoh esa mount'siz `docker run` ni va'da qiladi | 8-faza |
| **IN-02** | Keraksiz `as` tur assertsiyalari `!== undefined` qo'riqchisi ichida — `strict` rejimda xato yashirishi mumkin | 8-faza |
| **IN-03** | Eskirgan izoh: `ALERT_META` 15 a'zoli, izoh «o'n bitta» deydi | 8-faza |
| **IN-04** | `delivery-list.tsx` `disabled` ishlatadi, `case-detail-dialog.tsx` uni taqiqlaydi — klaviatura fokusi yo'qoladi | 8-faza (⚠ 07-22 o'sha naqshni FAQAT o'zi qo'shadigan yangi tugmaga qo'llaydi; `delivery-list.tsx:141` dagi MAVJUD `disabled` uning qamrovida emas) |
| **IN-05** | Nomuvofiqlik bloki `headline` namespace'idan pul birligini o'qiydi | **07-22** (shu to'lqin) |
| **IN-06** | `app-shell.tsx` da bitta nav yozuvi formatlash bo'yicha izchil emas | 8-faza |
| **IN-07** | `_main()` ning `finally` bloki `RedisStorage` va `Bot` sessiyasini yopmaydi | 8-faza |
| **IN-08** | Recon bloklari `marketId === null` ni qo'riqlamaydi — cheksiz skelet | 8-faza |

---

## 8. ✅ YOPILDI (orkestrator, `e32e40a`) — `bot:lint` MYPY BOSQICHIDA QIZIL edi

> **Yopildi:** 2026-08-13, gap 2-to'lqinidan keyin, orkestrator tomonidan
> (hech bir gap rejasining `files_modified` ida bu fayl yo'q edi, darvoza
> esa butun `npm run gate` zanjirini to'xtatib turardi).
>
> Tuzatish repodagi **mavjud** naqshni takrorlaydi — `fixtures/telegram.py`
> dagi `sent_texts` aynan shunday qiladi: `isinstance(request, SendMessage)`.
> `type: ignore` **ishlatilmadi** (quyidagi tahlil aynan shuni taqiqlaydi).
>
> ⛔ **Bu tipni tinchlantirish emas, darvozani KUCHAYTIRISH:** endi test
> javobning `SendMessage` ekanini ham tasdiqlaydi — avval u faqat
> `.text`/`.reply_markup` mavjudligiga umid qilardi.
>
> **O'lchandi:** `npm run bot:lint` EXIT=0 (`ruff` toza, 21 fayl
> formatlangan, mypy 20 faylda 0 xato); `npm run bot:test` EXIT=0, 76 test.

**Asl yozuv (2026-08-13, 07-21):**

**Topildi:** 07-21 ijrosi (2026-08-13), `docker compose --profile test
run --rm bot-tests sh -c "… && mypy ."` yugurtirilganda.

**Fayl:** `services/bot-service/tests/unit/test_binding.py:251, 252,
295, 296, 297`

```
error: "TelegramMethod[Any]" has no attribute "reply_markup"  [attr-defined]
error: "TelegramMethod[Any]" has no attribute "text"          [attr-defined]
```

**⛔ 07-21 NING O'ZGARISHI SABAB EMAS — O'LCHANDI:** fayl bu rejaning
`files_modified` ro'yxatida YO'Q va u ijro davomida **umuman
o'zgartirilmadi** (`git status` da ko'rinmaydi), ya'ni uning mazmuni
bazadagi (`6b0a849`) holat bilan **bayt-bayt bir xil**. Fayl oxirgi
marta `0d8c1f3` (07-18) da o'zgargan. `ruff check` va `ruff format`
ikkalasi ham **toza**; yiqiladigan bosqich faqat `mypy`.

**Oqibati:** `npm run bot:lint` (va u orqali butun `npm run gate`
zanjiri) hozir **qizil**. Ya'ni faza yakunidagi darvoza yugurtirilsa u
07-21 ning ishi tufayli emas, shu besh xato tufayli to'xtaydi.

**Nega 07-21 da tuzatilmadi:** SCOPE BOUNDARY — nuqson joriy vazifaning
o'zgarishlari tufayli TUG'ILMAGAN va fayl reja qamrovidan tashqarida.
Uni «yo'l-yo'lakay» tuzatish 07-18 ning testini bu rejaning diffiga
tortardi.

**To'g'ri tuzatish shakli:** `MockedBot` qaytargan qiymatni aniq turga
tor qilish (`assert isinstance(sent, SendMessage)`), `# type: ignore`
qo'shish EMAS — ignore keyingi haqiqiy tur nuqsonini ham yashirardi.

**Egasi:** 8-faza yoki faza yakuni (kim `bot:lint` ni birinchi bo'lib
darvoza sifatida yugurtirsa).
