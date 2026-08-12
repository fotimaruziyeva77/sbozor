---
phase: 07-nomuvofiqlik-bildirishnoma-va-botlar
plan: 18
subsystem: api
tags: [fastapi, aiogram, postgres, rls, telegram, i18n, gettext, sqlalchemy]

# Dependency graph
requires:
  - phase: 07-nomuvofiqlik-bildirishnoma-va-botlar
    provides: "07-08 — binding_repo D-26 mashinasi, tenant_session(), /internal/bot/* xavfsizlik holati (ServiceToken, hmac.compare_digest, 401/503)"
  - phase: 07-nomuvofiqlik-bildirishnoma-va-botlar
    provides: "07-11 — bot handlerlari, uchala locale katalogi, BaseSession test uskunasi"
  - phase: 07-nomuvofiqlik-bildirishnoma-va-botlar
    provides: "07-13 — direktor dayjestlari (digest_morning/digest_evening), ular director_chat_id ni ISTE'MOL qiladi"
provides:
  - "market_notification_settings.director_chat_id ga yozadigan BIRINCHI va YAGONA mahsulot yo'li"
  - "binding_repo.resolve_director() — telefon -> user_market_roles reyestri (Role.DIRECTOR + is_active)"
  - "binding_repo.bind_director() — bitta ustunli UPSERT, RETURNING (xmax = 0)"
  - "POST /internal/bot/director/resolve — servis tokeni ostidagi to'rtinchi ichki marshrut"
  - "CoreClient.resolve_director() + on_contact ning ikkinchi shoxi"
  - "bot.binding.director msgid uchala locale'da"
affects: [08-faza, market_notification_settings audit, direktor bot buyruq yuzasi]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Sozlama qatori LAZY tug'iladi: market_create() kaskadida EMAS, birinchi yozuvda ON CONFLICT bilan"
    - "Rate-limit sanagichi bir Telegram akkaunti uchun BITTA — ikki marshrut uni BO'LISHADI"
    - "Bir odam N bozorning direktori bo'lsa HAR BIR bozorning qatori alohida tranzaksiyada yoziladi"

key-files:
  created: []
  modified:
    - services/core-api/app/repositories/binding_repo.py
    - services/core-api/app/api/internal/bot.py
    - services/bot-service/app/core_client.py
    - services/bot-service/app/handlers/binding.py
    - services/bot-service/app/locales/uz_Latn/LC_MESSAGES/bot.po
    - services/bot-service/app/locales/uz_Cyrl/LC_MESSAGES/bot.po
    - services/bot-service/app/locales/ru/LC_MESSAGES/bot.po
    - services/bot-service/tests/unit/test_binding.py
    - services/bot-service/tests/fixtures/core_double.py
    - tests/integration/test_bot_internal_api.py
    - tests/integration/test_phase7_criteria.py
    - tests/fixtures/notification_domain.py
    - tests/tenancy/test_cross_tenant.py
    - tests/tenancy/test_route_coverage.py
    - .planning/phases/07-nomuvofiqlik-bildirishnoma-va-botlar/deferred-items.md

key-decisions:
  - "Direktor botga `contact` ulashadi — admin veb formaga chat identifikatorini KO'CHIRMAYDI (rejaning qulflangan qarori)"
  - "market_create() kaskadi market_notification_settings qatorini YARATMAYDI: uchala ustunning o'quvchisi ham COALESCE/LEFT JOIN bilan qatorsiz to'g'ri javob beradi; qator oldindan yaratilsa IKKINCHI standart manbai tug'ilardi"
  - "D-26(b) («bir nechta moslik» -> bog'lanish yo'q) direktorga QO'LLANMAYDI: users.phone_e164 global noyob, ya'ni bir telefon = bir odam va uning ikki bozorda direktor bo'lishi QONUNIY"
  - "Direktor javobida asosiy menyu klaviaturasi YO'Q — u OLUVCHI, «Qarzim»/«To'lovlarim» unga not_bound berardi"
  - "Rate-limit sanagichi sotuvchi shoxi bilan bo'linadi — alohida sanagich bitta akkauntning byudjetini ikki barobar oshirardi"
  - "market_notification_settings audit ostiga OLINMAYDI (id uuid ustuni yo'q — texnik to'siq); band deferred-items.md ga 8-faza egaligi bilan yozildi"

patterns-established:
  - "Yozuv yo'lini o'lchashning YAGONA halol shakli: mahsulot endpointini chaqirib, natijani BAZADAN o'qish (natija obyekti yetarli emas)"
  - "Sxemasiz ichki yuzaning o'lchami TENGLIK bilan qulflanadi (== , >= emas) — yuzaning jimgina kengayishini to'sadi"
  - "Taqiqlangan nom mahsulot faylida LITERAL yozilmaydi, chunki sanoq/matn darvozasi izohni koddan ajratmaydi (03-07 / 07-02 darsi)"

requirements-completed: [RECON-03, BOT-04]

# Metrics
duration: 62min
completed: 2026-08-12
---

# Phase 7 Plan 18: Direktorning dayjest manzili — yozuv yo'li Summary

**`market_notification_settings.director_chat_id` ga yozadigan mahsulot yo'li ochildi: direktor botga kontakt ulashadi -> `POST /internal/bot/director/resolve` -> `user_market_roles` reyestri (`Role.DIRECTOR` + `is_active`) -> bitta ustunli `UPSERT`; `test_sc3` fixture seedidan shu HTTP yo'liga ko'chdi va natijani bazadan o'qib tasdiqlaydi.**

## Performance

- **Duration:** ~62 min
- **Started:** 2026-08-12T22:39Z (worktree sozlash)
- **Completed:** 2026-08-12T23:41Z
- **Tasks:** 3/3
- **Files modified:** 15

## Accomplishments

- **Fazaning YAGONA *NOT MET* mezoni yopildi.** 07-VERIFICATION gap #1 ning
  ildizi bug emas, **YO'Q YO'L** edi: `director_chat_id` ga butun repo
  bo'ylab birorta yozuvchi yo'q edi, ya'ni `outbox_repo.resolve_chat_id()`
  produksiyada **har doim** `None` qaytarardi va direktor dayjestni **hech
  qachon** olmasdi. Endi yo'l bor va u HTTP orqali o'lchanadi.
- **`test_sc3` endi mahsulot yo'lini yuritadi.** U sozlama qatorini
  fixture bilan **emas**, yangi marshrut bilan hosil qiladi va
  `director_chat_id` ni **bazadan o'qib** tasdiqlaydi.
- **Ikkala majburiy sabotaj ham bajarildi va ikkalasi ham QIZARDI**
  (o'lchovlar pastda) — ya'ni yangi testlar mahsulotga **haqiqatan**
  tayanadi.
- **Bir odam ikki bozorning direktori** bo'lgan holat qamrab olindi:
  har bozorning qatori **alohida tranzaksiyada** yoziladi.
- **Uchala locale** yangi matn bilan; uz-Cyrl o'zlashmasi **qo'lda**
  tekshirildi.

## Task Commits

1. **Task 1: `binding_repo` — direktorni topadi va chatini yozadi** — `d5236f1` (feat)
2. **Task 2: `POST /internal/bot/director/resolve` + `test_sc3` ning mahsulot yo'li** — `dc3eb73` (feat)
3. **Task 3: bot-service — direktor ham kontakt orqali ulanadi** — `0d8c1f3` (feat)
4. **WARNING-1 qarori (`market_create()` kaskadi)** — `70526e9` (docs)
5. **Qaror izohidagi taqiqlangan nom** — `1c4950b` (fix, deviatsiya #4)

## Files Created/Modified

- `services/core-api/app/repositories/binding_repo.py` — `DirectorRef`,
  `DirectorResolveOutcome`, `DirectorResolveStatus` (AYNAN ikki a'zo),
  `resolve_director()` (erta `break` YO'Q), `bind_director()` (bitta
  ustunli `UPSERT`, `RETURNING (xmax = 0)`).
- `services/core-api/app/api/internal/bot.py` — to'rtinchi marshrut,
  `DirectorResolveRequest` / `DirectorResolveResponse`; rate-limit ishning
  O'ZIDAN oldin; javob faqat `{status, market_count}`.
- `services/bot-service/app/core_client.py` — `DirectorResolveResponse`
  modeli + `resolve_director()` metodi (mavjud `_request()` orqali, ya'ni
  istisno SIRSIZ `CoreApiError` ga aylanadi).
- `services/bot-service/app/handlers/binding.py` — `on_contact` ning
  ikkinchi shoxi; D-24 ning uch qo'riqchisi **o'zgarmadi**.
- `services/bot-service/app/locales/*/LC_MESSAGES/bot.po` —
  `bot.binding.director` (uchala katalogda 1 marta).
- `services/bot-service/tests/fixtures/core_double.py` — alohida
  `director_calls` sanagichi (deviatsiya, pastda).
- `services/bot-service/tests/unit/test_binding.py` — direktor shoxining
  olti da'vosi + locale mavjudligi.
- `tests/integration/test_bot_internal_api.py` — repo darajasidagi sakkiz
  xulq testi, `break`-freedom va audit-sanoq darvozalari, HTTP darajasidagi
  olti test.
- `tests/integration/test_phase7_criteria.py` — `test_sc3` yozuv yo'liga
  ko'chdi + DB readback.
- `tests/fixtures/notification_domain.py` — `seed_notification_settings()`
  docstringi endi mahsulot yo'lini **nomma-nom** ko'rsatadi.
- `tests/tenancy/test_cross_tenant.py`, `tests/tenancy/test_route_coverage.py`
  — reyestrlar 3 -> 4 (da'vo shakli `==` bo'lib qoldi).
- `.planning/.../deferred-items.md` — 3-band: audit bo'shlig'i, egasi 8-faza.

## Decisions Made

### 1. `market_create()` kaskadi sozlama qatorini YARATMAYDI (WARNING-1)

`07-VERIFICATION.md` gap #1 ning uchinchi bandi ikki variantni nomlagan
edi: kaskadga `market_notification_settings` qatorini qo'shish **yoki**
`COALESCE` standartlari bilan davom etish qarorini hujjatlashtirish.
**Qator yaratilmaydi** — va bu tanlov taxminga emas, o'lchovga tayanadi:

| Ustun | O'quvchi | Qator YO'Q bo'lganda |
|---|---|---|
| `quiet_hours_start` / `quiet_hours_end` | `outbox_repo._CLAIM_DUE` | `LEFT JOIN` + `COALESCE(s.quiet_hours_start, :quiet_start)` — standart qo'llanadi. `JOIN` **ATAYIN** emas: u sozlamasiz bozorning butun navbatini jimgina ko'rinmas qilardi. |
| `overdue_days` | `jobs/notifications._MARKET_OVERDUE_DAYS` va uning jufti `jobs/reconciliation` da | `COALESCE((SELECT s.overdue_days ...), :fallback)`; standartning o'zi **sxemadan hosila** (`notification_meta.DEFAULT_OVERDUE_DAYS` -> `server_default`). |
| `director_chat_id` | `outbox_repo._RESOLVE_DIRECTOR_CHAT` | `None` — va bu **QONUNIY**: direktor hali ulanmagan. |

Ya'ni qatorni oldindan yaratish **hech bir o'quvchining javobini
o'zgartirmaydi**, lekin **ikkinchi standart manbaini** tug'dirardi:
sxemaning `server_default` i va kaskadning yozgan qiymati bir kun ajralib
ketardi va «standart qaysi?» savoliga ikki joy ikki xil javob berardi.
Bundan tashqari kaskad `markets` ni yaratadigan migratsiya funksiyasida
yashaydi — unga yangi jadval qo'shish **migratsiya** talab qilardi,
holbuki bu rejaning tahdid reyestri (`T-07-SC`) diffda `migrations/`
bo'lmasligini talab qiladi.

`director_chat_id` boshqa toifada: uning standarti **yo'q** va u faqat
direktor botga ulanganda ma'lum bo'ladi. Shuning uchun qator **lazy**
tarzda, `bind_director()` ning `ON CONFLICT (market_id) DO UPDATE` si
bilan tug'iladi — va o'sha `ON CONFLICT` «qator allaqachon bor»
(masalan `overdue_days` boshqa yo'ldan o'zgartirilgan) shoxini ham
xatosiz qamraydi.

Qaror **kodda ham** yozilgan: `binding_repo._BIND_DIRECTOR_CHAT`
docstringi (commit `70526e9`).

### 2. Direktor shoxida `multiple_matches` holati YO'Q

`DirectorResolveStatus` da **aynan ikki** a'zo bor. Sabab **mexanik**,
kelishuv emas: sotuvchida noaniqlik **reyestr nuqsoni** (`vendors` da
telefon global noyob emas), `users.phone_e164` esa **global noyob**
(`auth_create_user` band telefonda `None` qaytaradi). Ya'ni bir telefon =
bir odam va uning ikki bozorda direktor bo'lishi **qonuniy** —
har bozorning qatori yoziladi.

### 3. Direktorga asosiy menyu klaviaturasi berilmaydi

Menyuning ikkala tugmasi ham (`Qarzim`, `To'lovlarim`) **sotuvchining**
savoli va ular direktor uchun `not_bound` javobini qaytarardi — ya'ni
menyu **ishlamaydigan tugmalar** bilan chiqardi. `ReplyKeyboardRemove()`
ham yuborilmaydi: kontakt tugmasi `/start` da one-time klaviatura va uni
Telegram o'zi yopadi; ortiqcha so'rov direktorning chatida ikkinchi
xabar tug'dirardi.

## Uz-Cyrl o'zlashmalari — QO'LDA tekshirilganlari

Yangi matn: `Уландингиз. Бозор бўйича кунлик хабарлар шу чатга келади.`

| So'z | Sinf | Tekshiruv natijasi |
|---|---|---|
| **чат** (`chat`) | ingliz o'zlashmasi (rus orqali) | ✅ To'g'ri shakl **`чат`**. `ns`/`ts` klasteri **yo'q**, ya'ni transliteratorning `kvitansiya -> квитанси…` sinfidagi nuqsoni bu so'zga **tegmaydi**. |
| **хабар** (`xabar`) | arab o'zlashmasi | ✅ Standart kirill shakli `хабар`. |
| **бозор** (`bozor`) | fors o'zlashmasi, reyestr atamasi | ✅ Katalogda allaqachon shu shaklda ishlatilgan. |

⛔ **`ns`/`ts` klasterli o'zlashma matnga ATAYIN kiritilmadi**
(`kvitansiya`, `informatsiya`, `autentifikatsiya` sinfi) — 07-05 da
o'lchangan nuqson sinfi va uni ushlaydigan mexanik darvoza **yo'q**.
Sabab `.po` faylining izohiga ham yozildi.

Ruscha matn (`Вы подключены. Ежедневные сообщения по рынку будут
приходить в этот чат.`) — **mustaqil tarjima**, transliteratsiya hosilasi
emas; `лавк`/`магазин`/`сбор` tokenlari **0 marta**.

## Majburiy sabotajlar — ikkalasi ham bajarildi

### Sabotaj 1 — `Role.DIRECTOR` sharti olib tashlandi

`resolve_director()` dagi `and Role.DIRECTOR.value in member.roles`
o'chirildi.

```
FAILED tests/integration/test_bot_internal_api.py::test_a_cashier_phone_never_becomes_a_digest_address
E   AssertionError: assert <DirectorResolveStatus.BOUND: 'bound'> is <DirectorResolveStatus.NO_MATCH: 'no_match'>
```

Ya'ni rol tekshiruvi **haqiqiy**: usiz har qanday xodim (kassir,
nazoratchi) bozorning butun kunlik tushumini o'z chatiga yo'naltira
olardi (T-07-97). **Qaytarildi.**

⚠ **Sabotaj yon ta'sir ham ko'rsatdi va u tuzatildi:** yozilgan qoldiq
qator `cleanup_two_markets()` ning `DELETE FROM markets` ini FK bilan
yiqitib, butun to'plamga `ERROR` kaskadi tarqatgan edi. To'rtala
«qator YOZILMAYDI» testiga `finally: _clear_settings(...)` qo'shildi —
da'vo (`== 0`) tozalashdan **oldin** o'lchanadi, ya'ni zaiflashmadi.

### Sabotaj 2 — `test_sc3` dagi yangi HTTP chaqiruvi olib tashlandi

```
FAILED tests/integration/test_phase7_criteria.py::test_sc3_director_gets_two_messages_and_every_role_gets_one_number
E   AssertionError: Telegram'ga AYNAN IKKI so'rov ketishi kerak edi, ketgani 0.
E   assert 0 == 2
[info] outbox_tick_done  blocked=0 claimed=4 delivered=0 errors=0 failed=0 unresolved=4
```

Ya'ni test endi **haqiqatan** yozuv yo'liga tayanadi: manzil yozilmasa
`resolve_chat_id()` `None` qaytaradi, navbat qatori `unresolved` bo'lib
qoladi va Telegram'ga **hech nima** ketmaydi. **Qaytarildi.**

⚠ **Birinchi urinish YETARLI EMAS EDI va bu qayd etiladi:** telefonga
`"SABOTAJ-"` prefiksi qo'shish **ishlamadi** — `phonenumbers` xom satrdan
birinchi `+` dan boshlab raqamni **ajratib oladi**, ya'ni raqam baribir
to'g'ri normallashdi va test yashil qoldi. Sabotaj chaqiruvni **butunlay
olib tashlash** bilan qayta bajarildi. (Bu fakt kelajakda `_normalize()`
ustidan test yozadigan odam uchun ham foydali.)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `CoreDouble` ga `resolve_director` qo'shildi**
- **Found during:** Task 3 (bot-service handleri)
- **Issue:** Handlerning ikkinchi shoxi test uskunasida **mavjud emas**
  edi: `CoreDouble` da `resolve_director` metodi yo'q, ya'ni yangi shox
  yozilgan zahoti barcha mavjud `on_contact` testlari `AttributeError`
  bilan yiqilardi. Fayl rejaning `files_modified` ro'yxatida yo'q, lekin
  usiz Task 3 ni **umuman bajarib bo'lmasdi**.
- **Fix:** `director_result` / `director_raises` argumentlari va
  **alohida** `director_calls` sanagichi qo'shildi. Sanagich atayin
  alohida: `resolve_calls` bilan birlashtirilsa «sotuvchi topilganda
  direktor reyestri SO'RALMAYDI» degan da'vo **o'lchab bo'lmas** bo'lardi.
- **Files modified:** `services/bot-service/tests/fixtures/core_double.py`
- **Verification:** `bot-tests` to'liq yashil (71 test).
- **Committed in:** `0d8c1f3` (Task 3 commit)
- **Sibling xavfi:** yo'q — fayl 07-19 ning to'plamida ham yo'q.

**2. [Rule 2 - Missing Critical] «Qator yozilmaydi» testlariga tozalash qo'shildi**
- **Found during:** Sabotaj 1 (Task 1 dan keyin)
- **Issue:** To'rtta negativ test qoldiq qator qoldirmasligiga
  **tayanardi**. Regressiyada (qator YOZILDI) `cleanup_two_markets()` ning
  `DELETE FROM markets` i FK bilan yiqilib, nosozlik **butun to'plamga**
  ERROR kaskadi bo'lib tarqalardi va asl sabab ko'rinmasdi.
- **Fix:** `try/finally` + `_clear_settings(...)`; da'vo `finally` dan
  **oldin** o'lchanadi.
- **Files modified:** `tests/integration/test_bot_internal_api.py`
- **Verification:** Sabotaj 1 qayta yugurtirilganda nosozlik **faqat o'z
  testida** qoldi.
- **Committed in:** `d5236f1` (Task 1 commit)

**3. [Rule 2 - Missing Critical] `no_match` shoxida alohida jurnal yozuvi**
- **Found during:** Task 1
- **Issue:** Reja yakunda **bitta** `log.info("director_chat_bound",
  market_count=..., rebound=...)` chaqiruvini ko'rsatgan edi. Uni
  `no_match` shoxida ham chaqirish jurnalda **yolg'on hodisa nomi**
  qoldirardi (`director_chat_bound` + `market_count=0`) va operator
  «bog'landi» degan qatordan bog'lanmaganlikni o'qishi kerak bo'lardi.
- **Fix:** `no_match` shoxi o'z hodisasini yozadi
  (`log.info("director_resolve_no_match")`) — ⛔ **argumentsiz**:
  `telegram_user_id` bu shoxda aynan `chat_id` ning o'zi va u SIR.
  Muvaffaqiyat shoxi rejadagi shaklda qoldi.
- **Files modified:** `services/core-api/app/repositories/binding_repo.py`
- **Verification:** `grep -nE "log\.[a-z]+\(.*(phone|chat_id|telegram_user_id)"` —
  yangi funksiyalarda **0 mos kelish**.
- **Committed in:** `d5236f1` (Task 1 commit)

**4. [Rule 1 - Bug] Qaror izohi G7-7 darvozasini qizartirdi**
- **Found during:** WARNING-1 qarorini yozgandan keyingi to'liq tekshiruv
- **Issue:** `70526e9` dagi izoh `binding_repo` da **literal yozilmasligi
  shart** bo'lgan nomni (`markets` ni yaratadigan DB funksiyasining
  bajarilish huquqi turi) ishlatgan edi va
  `test_binding_repo_adds_no_rls_bypassing_surface` darhol **qizardi**.
  ⚠ Bu darvozaning **to'g'ri ishlagani**: modul docstringi o'sha nomni
  izohda ham yozmaslikni **ochiq talab qiladi** (03-07 / 07-02 darsi) va
  men aynan o'sha tuzoqqa tushdim.
- **Fix:** Izohning **ma'nosi saqlandi**, nom «DB funksiyasi» bilan
  almashtirildi va o'quvchi modul docstringining «ikki taqiqlangan nom»
  bandiga yo'naltirildi.
- **Files modified:** `services/core-api/app/repositories/binding_repo.py`
- **Verification:** `grep -c "SECURITY DEFINER" ... -> 0`;
  `test_bot_internal_api.py` 47/47 yashil.
- **Committed in:** `1c4950b` (alohida `fix` commit — tarixda darvozaning
  ishlagani ko'rinib tursin)

### Reja matnining ikki ichki ziddiyati — qanday hal qilindi

**a) `write_app_audit` sanog'i.** Reja bir vaqtning o'zida (i) sababni
`bind_director` docstringiga yozishni va (ii) `grep -c "write_app_audit"`
qiymatining **o'zgarmasligini** talab qilgan edi — nomni docstringda
yozish sanoqni 2 dan 3 ga oshirardi. Yechim loyihaning o'z intizomi
(03-07 / 07-02 darsi): **sabab yozildi, nom yozilmadi**, va sanoq
`ast.Call` bo'yicha o'lchaydigan yangi darvoza bilan qulflandi
(`test_the_director_write_path_adds_no_audit_call`). Sanoq: **2**
(bazadagi qiymat), kod chaqiruvlari: **1** (`revoke()`).

**b) `test_sc3` manbasida fixture nomi.** Ayni shakl: reja docstringda
tarixni tushuntirishni va nomning **0 marta** uchrashini talab qilgan
edi. Docstring tarixni **nomsiz** aytadi; token endi `test_sc3` tanasida
**0 marta**.

---

**Total deviations:** 4 auto-fixed (1 blocking, 2 missing-critical,
1 bug) + 2 reja-ziddiyati hal qilindi.
**Impact on plan:** Scope creep yo'q. Uchtasi rejadagi da'volarni
**o'lchanadigan** qilish uchun, to'rtinchisi esa mavjud darvoza ushlagan
o'z xatoimni tuzatish uchun edi.

## Issues Encountered

1. **Sabotaj 2 ning birinchi urinishi soxta-yashil berdi** — sabab
   `phonenumbers` ning xom satrdan raqam ajratib olishi (yuqorida
   batafsil). Sabotaj qayta bajarildi va qizardi.
2. **Yangi worktree'da `.env` va `ops/seaweedfs/s3.json` yo'q edi**
   (ikkalasi ham gitignore ostida). Ikkalasi `E:/bozor` dan nusxalandi —
   busiz Docker `s3.json` ni **katalog** sifatida yaratib, `storage` ni
   nosog'lom qilardi.
3. **Izolyatsiya:** butun ijro `docker compose -p
   sbozor-a77df82ea45af17cb` ostida ketdi; foydalanuvchining jonli
   `sbozor` stacki'ga tegilmadi. `db`/`cache` konteynerlari umuman
   ko'tarilmadi (baza `testcontainers` bilan keladi), ya'ni
   `DB_HOST_PORT` to'qnashuvi tug'ilmadi.

## Threat Flags

Yangi xavfsizlik yuzasi topilmadi: reja `<threat_model>` ida nomlangan
`T-07-96…T-07-103` bandlarining hammasi qamrab olindi va yangi tarmoq
endpointi, auth yo'li yoki sxema o'zgarishi **qo'shilmadi**
(`git diff --name-only` da `migrations/`, `pyproject.toml`, `uv.lock`,
`package.json` — **yo'q**).

## Known Stubs

Yo'q. Rejadagi hamma yo'l uchma-uch ulangan: bot -> `core_client` ->
`/internal/bot/director/resolve` -> `binding_repo` -> `market_notification
_settings` -> `outbox_repo.resolve_chat_id()` -> Telegram (test'da
`respx` chegarasi bilan).

## User Setup Required

Yo'q — tashqi servis sozlamasi talab qilinmaydi. ⚠ Ishlab chiqarishda
direktor **bir marta** botga `/start` bosib kontaktini ulashishi kerak;
shundan keyin dayjestlar avtomatik keladi. Bu qadam `07-USER-SETUP`
emas, **oddiy mahsulot oqimi**.

## Next Phase Readiness

- Mezon #3 ning «Telegramda oladi» yarmi endi **produksiyada bajariladi**
  va u HTTP + DB readback bilan o'lchanadi.
- ⚠ **Qolgan yarmi 07-19 da:** manzili topilmagan qator hozir ham abadiy
  `pending` bo'lib qolishi mumkin (`_settle()` ning `UNRESOLVED` shoxida
  terminal chegara yo'q). Ikki reja birgalikda gap #1 ni to'liq yopadi.
- 8-fazaga qolgan band: `market_notification_settings` audit ostiga
  olinishi (`deferred-items.md` 3-band).
- Direktor botining **BUYRUQ** yuzasi (hisobot so'rash, case holatini
  o'zgartirish) `07-CONTEXT.md` ning `<deferred>` bandida qoladi va bu
  reja unga tegmadi — direktor bu fazada **OLUVCHI**.

## Verification o'lchovlari

| Darvoza | Buyruq | Natija |
|---|---|---|
| **Yakuniy birlashgan yugurish** (beshala commit ustida) | `pytest tests/integration/test_bot_internal_api.py tests/integration/test_phase7_criteria.py tests/tenancy -q` | **EXIT=0**, ~860 test, **0 nosozlik** |
| Repo + HTTP xulqi | `pytest tests/integration/test_bot_internal_api.py -q` | **47 passed** |
| Mezon #3 | `pytest ...::test_sc3_director_gets_two_messages_and_every_role_gets_one_number -q` | **1 passed** |
| Tenancy reyestrlari | `pytest tests/tenancy -q` | **passed** (yuza 3 -> 4, `==` shakli saqlangan) |
| bot-service | `pytest -q` (bot-tests) | **71 passed** |
| Lint / format / tiplar | `ruff check . && ruff format --check . && mypy .` | **toza** (338 fayl) |
| Glossariy G7-9 | `node --test frontend/scripts/glossary.test.mjs` | **9/9 passed** |
| `bot.binding.director` uchala `.po` da | `grep -c` | **1 / 1 / 1** |
| `test_sc3` da fixture nomi | `grep -c` (test tanasida) | **0** |
| Paket/migratsiya diffi (`T-07-SC`) | `git diff --name-only` | `pyproject.toml`, `uv.lock`, `package.json`, `migrations/` — **yo'q** |

## Self-Check: PASSED

- Barcha e'lon qilingan fayllar diskda mavjud va commit'larda ko'rinadi
  (`git show --stat` bilan tasdiqlandi).
- Beshala commit ham `git log` da: `d5236f1`, `dc3eb73`, `0d8c1f3`,
  `70526e9`, `1c4950b`.
- `STATE.md` va `ROADMAP.md` **tegilmadi** (orkestrator ularni merge'dan
  keyin o'zi yozadi).

---
*Phase: 07-nomuvofiqlik-bildirishnoma-va-botlar*
*Completed: 2026-08-12*
