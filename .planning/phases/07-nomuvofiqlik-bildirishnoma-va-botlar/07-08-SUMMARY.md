---
phase: 07-nomuvofiqlik-bildirishnoma-va-botlar
plan: 08
subsystem: api
tags: [bot, internal-api, service-token, rls, d-26, binding, enumeration, alert-registry]
requires:
  - "0023_notification_domain — vendor_telegram_bindings + ikki qisman UNIQUE indeks"
  - "tests/fixtures/notification_domain.py::seed_same_phone_in_two_markets — D-26(b) ning YAGONA kirish holati (07-04)"
  - "app/jobs/retention.py::active_market_ids — YAGONA RLS-chetlab o'tuvchi yuza"
  - "app/repositories/billing_repo.py::vendor_outstanding / vendor_charge_allocation (06-06)"
  - "sbozor_core.phone.normalize_phone — D-25 normalizatsiyasi"
provides:
  - "binding_repo — resolve (uch shox) / bind / revoke / active_bindings / pending_vendors / stall_codes_by_vendor / tenant_session"
  - "POST /internal/bot/resolve · GET /internal/bot/vendor/summary · GET /internal/bot/vendor/payments"
  - "Settings.bot_service_token — fail-closed servis-servis tokeni"
  - "ALERT_META['vendor_binding_conflict'] + alerting.raise_alert()"
  - "ratelimit.check_bot_resolve_rate() — enumeratsiyaning ikkinchi qatlami"
  - "snapshots.alertKey.vendorBindingConflict — uchala locale"
affects:
  - "07-11 (bot handlerlari) — tayyor, tor va o'lchangan yuzaga yozadi"
  - "07-13/07-14 (admin «kutilmoqda» ro'yxati) — pending_vendors() ning iste'molchisi"
tech-stack:
  added: []
  patterns:
    - "servis-servis token: `hmac.compare_digest` + fail-closed 503"
    - "RLS chetlab o'tmasdan bozorlararo qidiruv — `active_market_ids()` tsikli"
    - "erta `break` YO'Q — taym-oracle AST + xulq bilan o'lchanadi"
    - "so'rov yo'lidan alert ochish — `raise_alert()` `_upsert()` ustida, debounce TAKRORLANMAYDI"
    - "taqiqlangan nom IZOHDA ham yozilmaydi (03-07 / 07-02 darsi)"
key-files:
  created:
    - services/core-api/app/repositories/binding_repo.py
    - services/core-api/app/api/internal/bot.py
    - tests/integration/test_bot_internal_api.py
  modified:
    - services/core-api/app/main.py
    - services/core-api/app/settings.py
    - services/core-api/app/jobs/alerting.py
    - services/core-api/app/security/ratelimit.py
    - tests/tenancy/test_route_coverage.py
    - tests/tenancy/test_cross_tenant.py
    - frontend/messages/uz-Latn.json
    - frontend/messages/ru.json
    - frontend/messages/uz-Cyrl.json
    - frontend/src/components/snapshots/alert-row.tsx
    - compose.yaml
decisions:
  - "`_tenant_session` OMMAVIY qilindi (`binding_repo.tenant_session`) — bot yo'lida `Principal` yo'q, ya'ni `TenantSessionDep` ishlamaydi va marshrutga o'z nusxasini yozish `actor_kind` ni ikkiga bo'lardi"
  - "`active_binding` -> `active_bindings` (ko'plik, kortej): bir Telegram ID ikki bozorda faol bo'lishi QONUNIY va `| None` imzosi chaqiruvchini birinchisini tanlashga majburlardi"
  - "`GET /vendor/payments` `market_id` ni MAJBURIY oladi — tanlovni foydalanuvchi qiladi, server emas"
  - "`as_of = business_today()` IKKALA billing chaqiruviga ham beriladi (G-14 tengligi)"
  - "`raise_alert()` `alerting.py` ga qo'shildi — `_upsert()` ning debounce mantig'i TAKRORLANMAYDI"
metrics:
  duration: ~75 min
  completed: 2026-08-12
  tasks: 2
  files: 14
---

# Phase 7 Plan 08: Bot ↔ core-api ishonch chegarasi — Summary

Faza birinchi marta **xodim bo'lmagan** shaxsga (sotuvchiga) tizim ma'lumotini
ochdi — va u sessiyasiz, sxemasiz, tokenli va o'lchangan tor yuzadan o'tdi.
D-26 ning uch shoxi nomlandi; «bir nechta moslik» shoxi **ikki bozorli** seed
bilan haqiqatan bajarildi va `alert_events` ga **ikkala bozorda ham** qator
yozdi.

## Nima qurildi

**Task 1 — `binding_repo` (`b916493`).** `resolve()` `sessionmaker` oladi
(`session` emas) va `active_market_ids()` bo'ylab yuradi: bu yagona
RLS-chetlab o'tuvchi yuza va u **import qilinadi**, nusxa olinmaydi. Tsiklda
erta `break` **yo'q** — moslik topilgan va topilmagan holatlarda aylantirilgan
bozorlar ro'yxati **aynan bir xil** boshlanadi. Uch shox:

| Shox | Xulq |
|---|---|
| `NO_MATCH` | Qator YOZILMAYDI; telefon **hech qayerga** saqlanmaydi (jurnalga ham) |
| `MULTIPLE_MATCHES` | Bog'lanish YOZILMAYDI; **har bozorda** `vendor_binding_conflict` alerti |
| `BOUND` | Eski bog'lanish(lar) **bekor qilinadi** (append-only) + audit, keyin yangi qator |

**Task 2 — `/internal/bot/*` (`364846f`).** `APIRouter(include_in_schema=False)`,
`hmac.compare_digest`, sozlanmagan token → `503` (fail-closed). Uchta marshrut:
`POST /resolve`, `GET /vendor/summary`, `GET /vendor/payments`. Qoldiq
`vendor_outstanding()` dan, tarix `vendor_charge_allocation()` dan — 6-faza
uni **ataylab** iste'molchisiz qoldirgan edi va bu faza uning iste'molchisi.

## O'lchangan dalillar

| Da'vo | Natija |
|---|---|
| `ResolveStatus` — yopiq uchlik | `{bound, no_match, multiple_matches}` ✓ |
| D-26(b) ikki bozorli seedda | `MULTIPLE_MATCHES`, `vendor_telegram_bindings` da **0** qator |
| Anomaliya HAQIQIY qator | `alert_events` da **ikkala** `market_id` ✓ |
| Takroriy urinish | qator soni **2** (o'zgarmadi), `occurrences = 2` |
| **Nazorat**: bitta bozorli holat | AYNI telefon → `BOUND` ✓ |
| D-26(a): noma'lum raqam | `NO_MATCH`, jadval **bo'sh** |
| Format xatosi | `NO_MATCH` — sabab **oshkor qilinmaydi** |
| `+` siz raqam (`9989…`) | `+` bilan kelgani bilan **bir xil** natija |
| D-26(c) qayta ulanish | jadvalda **2** qator (biri `revoked`), `audit_log` da **1** yangi yozuv |
| Ayni juftlik ikkinchi marta | **0** yangi audit qatori |
| Tokensiz / noto'g'ri token | `401` + **bayt-bayt ayni** javob |
| Sozlanmagan token | `503 unavailable` (fail-closed) |
| OpenAPI'da `/internal/bot` | **0** yo'l |
| `Set-Cookie` | **yo'q**; manbada sessiya primitivi **0** |
| `vendor/summary` soni | `vendor_outstanding()` bilan `==` va **nolga teng emas** |
| `vendor/payments` qatorlari | `vendor_charge_allocation().rows` bilan **aynan** mos |
| Rate-limit | 5 ta `200`, 6-si `429` |
| `PERSONAL_ROUTES` | **o'smadi** (G7-6) |
| Yangi RLS-chetlab o'tuvchi funksiya | **yo'q** (G7-7, tenglik darvozasi yashil) |

**Darvozalar:** `pytest tests/integration/test_bot_internal_api.py` — **31 test
yashil** · `pytest tests/tenancy` — **693 test yashil** (exit 0) ·
`pytest tests/unit` — yashil · `pytest tests/integration/test_alerting.py` —
16 yashil · `ruff check` + `ruff format --check` + `mypy` (317 fayl) — **toza**
· `node scripts/check-messages.mjs` — 1115 kalit × 3 til ✓ ·
`node scripts/gen-cyrillic.mjs --check` — drift yo'q ·
`node scripts/snapshot-copy.test.mjs` — 9/9 ✓.

## Rejadan chetlanishlar

### Rule 3 — reja MATNI talab qilgan, `files_modified` esa sanamagan fayllar

**1. [Rule 3] `services/core-api/app/jobs/alerting.py`**
- **Topildi:** Task 2 ochiq talab qiladi («`ALERT_META` reyestriga bitta yozuv
  qo'shiladi») va Task 1 ning qabul mezoni `K in ALERT_META` ni tekshiradi,
  lekin fayl `files_modified` da yo'q edi.
- **Yechim:** `AlertMeta("vendor_binding_conflict", WARNING, never_suppressed=
  False, platform_scoped=False)` + har bayroqning sababi izohda. **Ikkinchi
  o'zgarish:** `raise_alert()` — `_upsert()` ustidagi tor ommaviy yuza.
  Sabab mexanik: `_upsert()` ni qayta yozish uning O'Z docstringi bilan
  taqiqlangan (debounce ning yagona DB kafolati — qisman UNIQUE indeks va
  `ON CONFLICT` ifodasi indeksning AYNAN o'zidan quriladi). `alert_repo` ning
  «yozish metodi yo'q» qoidasi buzilmadi: u FOYDALANUVCHI yuzasi haqida
  (`POST/PATCH/DELETE /alerts` yo'q), bu yerda esa foydalanuvchi ham,
  ommaviy marshrut ham yo'q.
- **Commit:** `b916493`

**2. [Rule 3] `tests/tenancy/test_cross_tenant.py::EXEMPT_ROUTES`**
- **Topildi:** `tenant_resource_routes()` NEGATIV ro'yxat bilan quriladi —
  istisno qilinmagan har yangi marshrut matritsaga AVTOMATIK tushadi.
  Uchala `/internal/bot/*` yo'li o'sha matritsaning uchala token da'vosini
  (tokensiz → 401) olardi, ularning kontrakti esa `401`/`503` va u
  foydalanuvchi tokeni bilan umuman bog'liq emas. Reja darvozani
  `test_route_coverage.py` da qayd etishni buyurgan, lekin `EXEMPT_ROUTES`
  qo'shni faylda yashaydi.
- **Yechim:** uchala yo'l uchun **bitta** sabab konstantasi (`_BOT_INTERNAL_
  REASON`) — uch marta nusxalash bittasini tahrirlab ikkitasini unutish
  yo'lini ochardi. Sabab `EXEMPT_ROUTES` ning talabini bajaradi: qamrov
  `tests/integration/test_bot_internal_api.py` da TO'LIQ qayta tiklandi.
- **Commit:** `364846f`

**3. [Rule 3] `services/core-api/app/security/ratelimit.py`**
- **Topildi:** reja rate-limit yordamchisini `app/deps.py` da deb ko'rsatgan,
  amalda u `security/ratelimit.py` da (`check_login_rate` /
  `check_nvr_test_rate`).
- **Yechim:** `check_bot_resolve_rate()` o'sha modulga qo'shildi va mavjud
  `_bump()` ni QAYTA ISHLATADI. Kesim **`telegram_user_id` bo'yicha**,
  telefon bo'yicha EMAS: telefonni kalitga qo'yish uni Valkey'ga yozardi va
  bu modulning butun ma'nosiga (T-07-41) zid bo'lardi.
- **Commit:** `364846f`

### Rule 2 — usiz funksiya AMALDA yetib bormasdi

**4. [Rule 2] `frontend/src/components/snapshots/alert-row.tsx`**
- **Topildi:** reja faqat `messages/*.json` ni sanaydi, lekin `ALERT_TITLE_KEYS`
  xaritasiga kirmagan kalit ekranda `errors.generic` («Kutilmagan xato»)
  bo'lib chiziladi — ya'ni uchala tildagi matn **hech qachon renderlanmasdi**
  va reja «uchala locale'da matn bor» mezonini bo'sh-rost qilardi.
  Presedent aynan shu faylda yozilgan: `billing_close_stale` 6-fazada
  aynan shu sababdan qo'shilgan.
- **Yechim:** bir qator xarita + sabab izohi (matnda telefon va ism YO'Q).
- **Commit:** `364846f`

**5. [Rule 2] `compose.yaml` — `core-api` bloki**
- **Topildi:** `BOT_SERVICE_TOKEN` 07-01 da `.env.example` ga va
  `bot-service`/`bot-tests` bloklariga qo'shilgan, lekin **`core-api` ga
  berilmagan**. Ya'ni tokenni to'g'ri sozlagan operator ham `/internal/bot/*`
  ni `503` holatida ko'rardi va sabab konfiguratsiyada emas, compose'da
  bo'lardi.
- **Yechim:** `BOT_SERVICE_TOKEN: ${BOT_SERVICE_TOKEN}` — `bot-service`
  bloki bilan AYNI o'zgaruvchi. Bo'sh qiymat ishga tushishni to'xtatmaydi
  (`NVR_CREDENTIAL_KEY` dan farqi izohda yozildi): bot yuzasi yopiladi,
  kadr olish va patta hisobi ishlab turaveradi.
- **Commit:** `364846f`

### Rule 1 — rejaning O'Z darvozasi qizil bo'lardi

**6. [Rule 1] Taqiqlangan nomlar IZOHDAN olib tashlandi — IKKI MARTA**
- **Topildi:** birinchi yugurishda `binding_repo.py` ning docstringi
  taqiqni tushuntirish uchun RLS-chetlab o'tuvchi funksiya turining nomini
  literal yozgan edi; keyinroq `bot.py` ning docstringi saqlangan qoldiq
  ustunining nomini yozdi. Rejaning O'Z grep mezonlari (`→ 0`) ikkalasida
  ham musbat qaytardi.
- **Yechim:** ikkala matn ham nomni ishlatmasdan qayta yozildi (03-07 / 07-02
  darsi: sodda grep izohni koddan ajratmaydi va yagona «tuzatish» yo'li
  sababni o'chirish bo'lardi). Da'volar o'lchanadigan joyga ko'chdi: manba
  skanlari `test_bot_internal_api.py` da.
- **Commit:** `b916493` (birinchisi), `c55935b` (ikkinchisi)

**7. [Rule 1] Audit sanog'i EGA ulanishi bilan o'qilmaydi**
- **Topildi:** `audit_log` ni `sync_owner_conn` bilan sanagan test HAR DOIM
  `0` berardi — `audit_read` policy'si `sbozor_app` ga va tenant kontekstiga
  bog'langan. Ya'ni «audit yozildi» da'vosi bo'sh-rost bo'lib qolardi.
- **Yechim:** sanoq `tenant_session` fixture'i orqali, ILOVA roli bilan
  (`fixtures/auth_api.py::audit_rows` ning aynan o'sha qarori).
- **Commit:** `b916493`

**8. [Rule 1] `date` ISH VAQTIDA import qilinadi**
- **Topildi:** `bot.py` `date` ni `TYPE_CHECKING` ostida import qilgan edi;
  pydantic javob modelini QURISH paytida annotatsiyani hal qiladi va
  `PydanticUserError: ... is not fully defined` **ish vaqtida, birinchi
  so'rovda** chiqdi — `mypy` uni ko'rmadi.
- **Yechim:** import runtime blokiga ko'chirildi, sabab izohda.
- **Commit:** `364846f`

### Rejadan ongli chetlanishlar (struktura)

**`active_binding` → `active_bindings`.** Reja imzoni `-> BindingRef | None`
deb yozgan, lekin o'sha bandning O'ZIDA «bu holat `BindingRef` ro'yxati bilan
qaytadi» deb aytadi. `| None` imzosi chaqiruvchini birinchisini tanlashga
majburlardi — ya'ni reja taqiqlagan xulqni imzoning o'zi talab qilardi.
Funksiya kortej qaytaradi va `GET /vendor/summary` javobi **ro'yxat**.

**`_tenant_session` → ommaviy `tenant_session`.** `/internal/bot/*` da
`Principal` yo'q, ya'ni `deps.py::TenantSessionDep` (u bozorni `Principal` dan
oladi) ishlamaydi. Marshrut faylida ikkinchi nusxa yozish `actor_kind` yoki
tranzaksiya chegarasini jimgina ikkiga bo'lardi.

**`GET /vendor/payments` `market_id` ni majburiy oladi.** Reja imzoni
`?telegram_user_id=&cursor=` deb yozgan, lekin ayni rejada «jimgina
birinchisini tanlash TAQIQLANADI» deyilgan. Ikki bozorda faol bo'lgan akkaunt
uchun serverda tanlov qilish sotuvchiga BOSHQA bozorning tarixini
ko'rsatardi. Qiymatni bot `GET /vendor/summary` javobidan oladi.

**Sahifalash taqsimlangan natija ustida, SQL da emas.** `allocate_charge_
credit()` kreditni eng eski kundan boshlab tarqatadi, ya'ni u BUTUN tarixni
ko'rishi shart — `LIMIT` ni SQL ga tushirish natijani O'ZGARTIRARDI.

**`stall_codes_by_vendor()` ajratildi.** `pending_vendors()` va
`GET /vendor/summary` ikkalasi ham «hozir biriktirilgan rasta kodlari» ni
so'raydi; ikki nusxa o'sha ta'rifni ikkiga bo'lardi.

**`frontend/messages/uz-Cyrl.overrides.json` TEGILMADI** (u `files_modified`
da bor edi). Transliterator yangi satrni qo'shimcha qoidasiz to'g'ri o'girdi
va `gen-cyrillic --check` drift topmadi — ya'ni override qo'shish ishlatilmagan
yozuv qoldirardi. `uz-Cyrl.json` esa generatsiya qilindi (u qo'lda
tahrirlanmaydi).

## Ochiq bandlar

**1. `npm --prefix frontend test` (vitest) BU WORKTREE'DA BAJARILMADI.**
`frontend/node_modules` gitignored va bu worktree'da YO'Q. Bu reja frontendga
**tegdi** (uchta xabar fayli + `alert-row.tsx`), ya'ni band 07-02/07-04 dagidan
kuchliroq. Node'ga bog'liq bo'lmagan darvozalar BAJARILDI va yashil:
`check-messages.mjs` (kalit + ICU parity, 1115 × 3), `gen-cyrillic.mjs --check`
(drift yo'q), `snapshot-copy.test.mjs` (9/9 — shu jumladan G-3: ogohlantirish
qatorida rasm yuzasi yo'q). ⚠ **Bajarilmagani:** `alert-row.test.tsx` /
`alert-list.test.tsx` (vitest) — ya'ni yangi `ALERT_TITLE_KEYS` yozuvining
RENDER natijasi o'lchanmadi. Egasi: orkestrator (merge'dan keyin asosiy
repoda `node_modules` mavjud).

**2. `pending_vendors()` ning HTTP iste'molchisi hali yo'q.** Funksiya
o'lchandi (`test_pending_vendors_lists_unbound_vendors_and_drops_bound_ones`
uning `LEFT JOIN` ini HAQIQATAN yuguradi), lekin admin «kutilmoqda ro'yxati»
marshruti bu rejada emas. Naqsh va sabab `billing_repo.vendor_charge_
allocation()` bilan aynan bir xil: qoida bugun qulflanadi, yuza keyin
qo'shiladi — ⛔ ya'ni bu «o'lik kod» EMAS va o'chirilmaydi.

**3. `VENDOR_BINDING_CONFLICT_ALERT_KEY` satri IKKI JOYDA literal.**
`binding_repo` konstantasi va `ALERT_META` yozuvi. Import yo'nalishi
`binding_repo → alerting`, ya'ni teskari import siklga olib kelardi. Mosligi
to'plam a'zoligi bilan o'lchanadi (`test_the_conflict_alert_key_is_registered_
in_alert_meta`) — `ORIGINAL_URI_HEADER` bilan aynan bir xil holat va aynan
bir xil yechim.

**4. `next_cursor` ning ikkinchi sahifasi o'lchanmadi.** Seed bitta hisob
qatori beradi, ya'ni `limit` dan oshadigan natija tug'ilmadi va kursorning
IKKINCHI sahifasi hech qachon so'ralmadi. Kursor kaliti
(`service_date|stall_code`) taqsimlash tartibi bilan bir xil ekani KOD
darajasida yozilgan, lekin XULQ bilan tasdiqlanmagan. Birinchi haqiqiy
ehtiyoj 07-11 da (bot «Yana» tugmasi) tug'iladi.

**5. Sabotaj o'lchovi bajarilmadi.** Reja uni talab qilmagan (07-02/07-04
dan farqli), lekin qayd etib qo'yiladi: yangi darvozalarning (taym-oracle
AST, `balance` nom taqig'i, `PERSONAL_ROUTES` tekshiruvi) QIZARISHI ATAYIN
buzish bilan tasdiqlanmagan. Ularning uchalasi ham ijro davomida **haqiqiy
nosozlikda kamida bir marta qizardi** (D-06 nomi va RLS-chetlab o'tuvchi
funksiya turi nomi izohda topildi) — ya'ni ular bo'sh to'plam ustida
ishlamayotgani o'lchangan.

## Known Stubs

Yo'q. Uchala marshrut ham haqiqiy ma'lumot qaytaradi va ikkitasi
6-fazaning hisoblanadigan ko'rinishlariga `==` bilan bog'langan. Birorta
qattiq kodlangan bo'sh qiymat renderga oqmaydi.

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| threat_flag: new-network-surface | services/core-api/app/api/internal/bot.py | ⛔ **Fazaning ishonch chegarasi** (D-01): uchta yangi marshrut. Rejaning `<threat_model>` i buni to'liq qamraydi (T-07-37…T-07-45) — bu yozuv **yangi** yuza emas, ochiq qayd. Mitigatsiyalar: `include_in_schema=False`, nginx proxy qilmaydi, xost porti publish qilinmaydi, `hmac.compare_digest`, fail-closed `503`, `telegram_user_id` bo'yicha rate-limit, `Principal`/JWT/cookie YO'Q. |
| threat_flag: new-auth-path | services/core-api/app/settings.py | `bot_service_token` — loyihadagi **ikkinchi** autentifikatsiya materiali (JWT sirridan keyin). U foydalanuvchi sessiyasini tug'dirmaydi va huquq modeli KO'TARMAYDI: yagona qarori «servis so'rayaptimi?». Rotatsiya yo'li hali yo'zilmagan — `NVR_CREDENTIAL_KEYS_RETIRED` sinfidagi ikki kalitli oyna kerak bo'lishi mumkin (8-faza ish-ro'yxatiga nomzod). |

⚠ Rejaning tahdid reyestridagi **birorta** disposition o'zgarmadi va birorta
`accept` `mitigate` ga (yoki teskarisiga) ko'chmadi. `T-07-SC` («yangi paket
o'rnatilmaydi») ham kuchda: birorta bog'liqlik qo'shilmadi.

## Self-Check: PASSED

Yaratilgan fayllar diskda mavjud:
- `services/core-api/app/repositories/binding_repo.py` ✓ (717 satr)
- `services/core-api/app/api/internal/bot.py` ✓
- `tests/integration/test_bot_internal_api.py` ✓
- `.planning/phases/07-nomuvofiqlik-bildirishnoma-va-botlar/07-08-SUMMARY.md` ✓

Commitlar mavjud: `b916493` · `364846f` · `c55935b` · `8ce1e85`
(baza `461d5b9`). ⛔ Birorta commitda fayl o'chirilishi **YO'Q**
(`git diff --diff-filter=D --name-only 461d5b9 HEAD` — bo'sh).

⛔ Sir commitga tushmadi: `.env` va `ops/seaweedfs/s3.json` gitignored va
`git ls-files` ularni ko'rmaydi; `.env.example` da `BOT_SERVICE_TOKEN=`
(bo'sh, 07-01 dan) — o'zgartirilmadi. Test tokeni test uskunasi sifatida
nomlangan va u hech qanday muhitda haqiqiy emas. ⛔ Telefon raqami birorta
jurnal yozuvida, javob tanasida yoki URL da yo'q.

⚠ STATE.md va ROADMAP.md ATAYIN TEGILMADI — worktree rejimida ularni
orkestrator markazlashgan holda yangilaydi.
