---
phase: 08-hisobotlar-mustahkamlash-va-ishga-tushirish
plan: 11
subsystem: bot-service-va-muhit-gigiyenasi
tags: [WR-02, WR-03, WR-04, WR-14, IN-01, IN-07, D-24, D-31, RECON-04, deferred-items-7a]
requires:
  - "app/handlers/__init__.py — uch routerning determinlashgan ro'yxati"
  - "app/handlers/vendor.py — on_payments / on_more va PAGES_KEY navbati"
  - "app/handlers/start.py — main_menu_keyboard()"
  - "app/i18n.py — SUPPORTED_LOCALES va gettext katalogi"
  - "tests/unit/test_compose_sim_env.py — o'lik muhit kalitining darvoza naqshi"
provides:
  - "fallback_router — filtrsiz zaxira handler, ro'yxatning ENG OXIRIDA"
  - "bot.unknown / bot.payments.marketHeader / bot.payments.marketFallback / bot.payments.stale — to'rt yangi kalit, uchala locale'da"
  - "_market_header() / _market_block() — blok sarlavhasining YAGONA shakli"
  - "PAGES_KEY navbati UCH a'zoli: (bozor, kursor, rasta kodlari)"
  - "test_the_dead_frontend_api_base_url_key_does_not_come_back — WR-14 regressiya to'sig'i"
affects:
  - "services/bot-service/Dockerfile — ikkala bosqichda ham CMD"
  - "services/bot-service/app/main.py — _main() finally bloki uch resursni yopadi"
  - "compose.yaml — frontend blokidan o'lik NEXT_PUBLIC_API_BASE_URL olib tashlandi"
  - ".env.example — o'sha kalit va uning sababi izohga aylandi"
tech-stack:
  added: []
  patterns:
    - "Filtrsiz router ro'yxat OXIRIDA; tartib mexanik darvoza bilan o'lchanadi"
    - "Router daraxti `propagate_event` bilan sinaladi — handler qo'lda chaqirilmaydi"
    - "FSM sxemasi versiya raqami bilan emas, SHAKL tekshiruvi bilan himoyalanadi"
    - "O'lik muhit kaliti YO tiriltiriladi, YO olib tashlanadi — uchinchi yo'l yo'q"
    - "Xato matni o'lchanmagan FAKTNI da'vo qilmaydi: «holat buzuq» ≠ «tarix tugadi»"
key-files:
  created: []
  modified:
    - services/bot-service/app/handlers/__init__.py
    - services/bot-service/app/handlers/vendor.py
    - services/bot-service/app/main.py
    - services/bot-service/Dockerfile
    - services/bot-service/app/locales/uz_Latn/LC_MESSAGES/bot.po
    - services/bot-service/app/locales/uz_Cyrl/LC_MESSAGES/bot.po
    - services/bot-service/app/locales/ru/LC_MESSAGES/bot.po
    - services/bot-service/tests/unit/test_vendor_handlers.py
    - tests/unit/test_compose_sim_env.py
    - compose.yaml
    - .env.example
decisions:
  - "WR-14 uchun B yo'li: kalit OLIB TASHLANDI, `build.args` bilan tiriltirilmadi — 08-UI-SPEC M-9 ga ko'ra core-api'da CORSMiddleware yo'q va boshqa origin AVTORIZATSIYANI yiqitardi, ya'ni A yo'li o'lik kalitni ishlaydigan TUZOQQA aylantirardi"
  - "Zaxira handlerda `core` argumenti YO'Q: filtrga tushmagan har xabar so'rov tug'dirsa begona odam haqiqiy sotuvchining rate-limit sanagichini yeb qo'ya olardi"
  - "Buzuq FSM `bot.payments.noMore` EMAS, yangi `bot.payments.stale` beradi — «tarix tugadi» o'lchangan fakt da'vosi bo'lardi, holbuki haqiqat «saqlangan holat buzuq»"
  - "Bozor yorlig'i FSM navbatida SAQLANADI (uchinchi a'zo) — «Ko'proq» uchun ikkinchi so'rov ochilmaydi"
  - "Rasta kodi yo'q bozor uchun ALOHIDA kalit (`marketFallback`), bitta `{label}` li kalit emas — aks holda «Rasta 11111111» degan yolg'on satr chiqardi"
  - "`UUID(str(...))` — FSM JSON dan son qaytsa `AttributeError` `except (ValueError, TypeError)` dan o'tib ketardi"
metrics:
  duration: 40min
  tasks: 3
  files: 11
  completed: 2026-08-16
---

# Phase 8 Plan 11: Bot ogohlantirishlari va muhit gigiyenasi Summary

7-fazadan meros qolgan uchta **jim yo'l** yopildi: sotuvchi yozgan har
qanday xabar endi javob oladi, buzuq FSM «Ko'proq» tugmasini sukunatga
aylantirmaydi va ikki bozorli sotuvchi qaysi bozorning tarixini
o'qiyotganini biladi. Bularga image va muhit gigiyenasining uch
tuzatishi qo'shildi — o'lik `NEXT_PUBLIC_API_BASE_URL` kaliti sabab
bilan **olib tashlandi**.

## Nima qilindi

### Task 1 — WR-04: zaxira handler (`feat`, `test`)

Bu to'plamning eng qimmat tuzatishi. 08-11 gacha bot ro'yxatida uchta
router bor edi va ularning filtrlari `CommandStart()`, `Command("help")`,
`F.contact` va uchta qat'iy tugma matni bilan cheklanardi. **Boshqa hech
qanday xabar handlerga tushmasdi** — ya'ni sotuvchining eng tabiiy
harakati («qarzim qancha?» deb yozish) mutlaq sukunat bilan tugardi.

Bu `app/main.py:130-136` ning o'z asosiga zid edi: «Botning butun
qiymati — sotuvchi yozgan xabar javob oladi».

- `app/handlers/__init__.py` ga filtrsiz `fallback_router` qo'shildi va u
  ro'yxatning **eng oxirida** ulanadi. Tartibning sababi modul
  docstringida literal yozilgan: filtrsiz router boshda tursa u
  bog'lanish, qarz va to'lov tarixi oqimlarini **ushlab qolardi** va
  nosozlik eng yomon shaklda ko'rinardi — bot javob berib turardi, faqat
  noto'g'ri javobni.
- ⛔ **D-24 BUZILMAYDI.** Taqiq qo'lda terilgan raqamni **O'QISHGA**
  tegishli, javob berishga emas. Handler xabarning mazmuniga umuman
  qaramaydi: na tahlil qiladi, na aks-sado qiladi, na `core-api` ga
  uzatadi. `test_binding.py::test_typed_phone_number_is_not_handled`
  butun dispatcher bo'yicha yashil qoldi.
- Handlerda `core` argumenti **yo'q** — zaxira hech qanday so'rov
  qilmaydi (rate-limit sanagichi himoyalanadi).

### Task 2 — WR-02 va WR-03: buzuq FSM va bozor sarlavhasi (`fix`, `test`)

**WR-02.** `on_more` da `market_id_raw, cursor = pages[0]` ochish `try`
blokidan **tashqarida** edi va `UUID(...)` ning `ValueError` i hech
qayerda ushlanmasdi. Istisno aiogram jurnaliga tushardi, foydalanuvchi
esa hech qanday javob olmasdi.

Endi ochish ham, `UUID()` ham `try/except (ValueError, TypeError)`
ichida; xatoda navbat tozalanadi va **nomlangan** javob yuboriladi.

⚠ Bu faraziy stsenariy emas — **shu commitning fakti**: navbat elementi
WR-03 tufayli ikki a'zolidan uch a'zoliga o'tdi, FSM esa `db 1` da
`--save "" --appendonly no` bilan yashaydi va sxema versiyasini
tashimaydi. Tirik Valkey'da qolgan eski yozuvlar aynan shu yo'ldan
o'tadi — va o'sha yo'l endi `ValueError` emas, javob beradi.

**WR-03.** `on_payments` har bozor uchun sahifa olib ularni `"\n\n"`
bilan yopishtirardi — qaysi blok qaysi bozorniki ekani hech qayerda
yozilmagan edi. `on_more` esa navbatning birinchisini olib oxiriga
qaytadan qo'yardi, ya'ni bosishlar A-sahifa2, B-sahifa2, A-sahifa3
tartibida kelardi va hech birida bozor ko'rsatilmasdi.

Endi har blok o'z sarlavhasi bilan keladi. Yorliq manbai —
`vendor_summary` javobining `stall_codes` i (**ikkinchi so'rov
ochilmaydi**), u FSM navbatiga uchinchi a'zo bo'lib yoziladi va
«Ko'proq» uni qayta ishlatadi.

Rasta kodi yo'q bozor uchun **alohida kalit** (`bot.payments.marketFallback`)
ishlatiladi va u bozor identifikatorining qisqargan shaklini ko'rsatadi —
bo'sh ham emas, to'qilgan nom ham emas.

### Task 3 — IN-01, IN-07, WR-14 (`chore`)

- **IN-01:** `services/bot-service/Dockerfile` ning ikkala bosqichiga ham
  `CMD` qo'shildi (`dev` -> `pytest -q`, `runtime` -> `python -m app.main`).
  Izohning «mount'siz `docker run` ham ishlasin» va'dasi endi **rost**:
  jonli tekshirildi — `docker run` bilan `import app.main` mount'siz
  muvaffaqiyatli o'tdi (`.mo` kataloglari image ichida).
- **IN-07:** `_main()` ning `finally` bloki endi `RedisStorage` va `Bot`
  sessiyasini ham yopadi. `start_polling` odatda buni o'zi qiladi, lekin
  `TelegramConflictError` yo'lida kafolatlanmagan — `restart:
  unless-stopped` ostida bu har qayta urinishda ochiq ulanish pulini
  qoldirardi.
- **WR-14:** quyida alohida bandda.

## WR-14 — tanlangan yo'l va uning sababi

⛔ **B yo'li tanlandi: kalit `compose.yaml` va `.env.example` dan OLIB
TASHLANDI.** A yo'li (`ARG` + `build.args` bilan tiriltirish) ataylab
rad etildi.

Sabab reja yozilganidan keyin topilgan va u **o'lchangan**:

> `08-UI-SPEC.md` §M-9: «KOD: `api-client.ts:31` `API_BASE_URL = "/api/v1"`;
> core-api'da `CORSMiddleware` **umuman yo'q** ... ⛔ Boshqa origin
> (`NEXT_PUBLIC_API_BASE_URL`) qo'yilsa CORS umuman sozlanmagani uchun
> **avtorizatsiyaning o'zi** yiqiladi — ya'ni bir xil origin farazi
> loyihada **allaqachon ko'taruvchi**.»

Ya'ni kalitni «ishlaydigan» qilish uning yagona ta'sirini shunday
qilardi: operator qiymatni o'zgartiradi va **butun avtorizatsiya**
yiqiladi. Bu o'lik kalitni ishlaydigan **tuzoqqa** aylantirish bo'lardi
— o'lik konfiguratsiyadan ham yomonroq holat, chunki nosozlik endi
ishga tushish paytida emas, foydalanuvchi kirmoqchi bo'lganda
ko'rinardi.

Bitta domen topologiyasi (nginx `/api/` -> core-api) loyihaning ko'taruvchi
farazi, ya'ni yagona haqiqat manbai `api-client.ts:31` ning `/api/v1`
zaxirasi bo'lib qoladi. Boshqa origin haqiqatan kerak bo'lganda avval
CORS va `SameSite=Lax` refresh cookie'si qayta ko'rib chiqiladi —
o'shanda kalit `build.args` bilan qaytadi. Bu shart ikkala faylning
izohida ham yozilgan.

**Darvoza:** reja gate'ni faqat A yo'li uchun talab qilgan edi, lekin B
yo'li uchun ham qo'shildi — `tests/unit/test_compose_sim_env.py` ga
`test_the_dead_frontend_api_base_url_key_does_not_come_back` va uning
**nazorat bandi** (`test_the_frontend_service_block_is_still_scanned`).
Nazorat bandi usiz birinchi test bo'sh-rost bo'lardi: `frontend` bloki
ko'chirilsa «kalit yo'q» da'vosi mazmunidan qat'i nazar yashil qolardi.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical functionality] `.env.example` dagi kalit ham olib tashlandi**

- **Found during:** Task 3 (WR-14)
- **Issue:** Reja faqat `compose.yaml` ni nomlagan edi. Lekin compose
  interpolyatsiyasi olib tashlangach `.env.example:278` dagi
  `NEXT_PUBLIC_API_BASE_URL=/api/v1` **hech qayerda o'qilmaydigan**
  kalit bo'lib qolardi — ya'ni o'lik konfiguratsiya compose'dan
  `.env.example` ga **ko'chgan** bo'lardi, yo'qolmasdan.
- **Fix:** Kalit olib tashlanib, o'rniga sababni tushuntiruvchi izoh
  qo'yildi (`cp .env.example .env` qilgan yangi o'rnatma endi yolg'on
  tugma olmaydi).
- **Files modified:** `.env.example`
- **Commit:** 6b3ad15

**2. [Rule 2 - Missing critical functionality] `UUID(str(...))` majburlashi**

- **Found during:** Task 2 (WR-02)
- **Issue:** Reja `except (ValueError, TypeError)` ni so'ragan. Lekin FSM
  qiymatlari JSON dan qaytadi va navbat elementiga **son** yozilgan
  holatda `UUID(5)` `AttributeError` beradi — u yuqoridagi `except`
  dan **o'tib ketardi** va WR-02 ning tuzatishi aynan o'sha yo'lda
  ishlamasdi.
- **Fix:** `UUID(str(market_id_raw))` — son ham `ValueError` ga aylanadi,
  ya'ni barcha buzuq shakllar bitta yo'lga tushadi.
- **Files modified:** `services/bot-service/app/handlers/vendor.py`
- **Commit:** fdaccd0

**3. [Rule 2 - Missing critical functionality] WR-14 uchun nazorat bandi**

- **Found during:** Task 3
- **Issue:** Regressiya to'sig'i («kalit qaytmadi») `frontend` bloki
  compose'dan ko'chirilganda mazmunidan qat'i nazar yashil bo'lardi.
- **Fix:** `test_the_frontend_service_block_is_still_scanned` qo'shildi.
- **Files modified:** `tests/unit/test_compose_sim_env.py`
- **Commit:** 6b3ad15

### Rejadan ongli chetlanish (arxitektura emas, matn tanlovi)

**`bot.payments.stale` — yangi kalit, `bot.payments.noMore` qayta
ishlatilmadi.** 07-REVIEW ning taklif qilgan tuzatishi buzuq FSM uchun
`bot.payments.noMore` ni ko'rsatgan edi. U rad etildi: «Boshqa yozuv
qolmadi» — **o'lchangan fakt da'vosi** («tarixingiz tugadi»), holbuki
haqiqat butunlay boshqa («saqlangan holat buzuq»). Bu loyiha ataylab
yopib kelayotgan sinf (05-14, WR-05 bilan bir xil). Reja matni ham
«NOMLANGAN xato» talab qiladi, ya'ni bu chetlanish rejaning o'z
niyatiga mos.

## Test qamrovi

`services/bot-service/tests/unit/test_vendor_handlers.py` ga **11 yangi
test** qo'shildi (81 -> 86 bot testi; ba'zilari mavjudlarini
kengaytirdi):

| Test | Nimani o'lchaydi |
| --- | --- |
| `test_the_fallback_router_is_the_last_one` | Zaxira router ro'yxat oxirida (quyi chegara bilan) |
| `test_an_unrecognised_text_still_gets_an_answer` | WR-04 ning o'zi: javob bor, matn takrorlanmaydi, `core` chaqirilmaydi |
| `test_the_start_command_still_reaches_its_own_handler` | Zaxira `/start` ni ushlab qolmaydi |
| `test_a_shared_contact_still_reaches_its_own_handler` | Zaxira `F.contact` ni ushlab qolmaydi |
| `test_the_fallback_text_exists_in_every_locale` | `bot.unknown` uchala locale'da, nomma-nom |
| `test_more_with_a_legacy_two_element_entry_...` | Eski ikki a'zoli yozuv javob beradi, istisno ko'tarilmaydi |
| `test_more_with_a_non_uuid_market_id_...` | Yaroqsiz UUID ham javobga aylanadi |
| `test_payments_labels_every_block_with_its_own_market` | Ikki bozor, ikki sarlavha, BITTA `summary` so'rovi |
| `test_more_says_which_market_the_next_page_belongs_to` | «Ko'proq» sahifasi o'zini tanishtiradi |
| `test_a_market_without_stall_codes_is_named_by_its_identifier` | Bo'sh yorliq emas, identifikator |
| `test_the_dead_frontend_api_base_url_key_does_not_come_back` (+nazorat) | WR-14 regressiyasi |

⚠ **Muhim uslub qarori:** WR-04 testlari handlerni qo'lda
chaqirmaydi — ular `dp.propagate_event("message", ...)` orqali
**haqiqiy router daraxtini** yuritadi. Handlerni qo'lda chaqirish
«u javob qaytaradimi?» degan savolga javob berardi, holbuki WR-04 ning
savoli boshqa: «xabar UNGACHA yetib boradimi va u boshqa oqimlarni
ushlab qolmaydimi?».

⚠ `build_router()` testlarda chaqirilmaydi: `include_router` bolaga
`parent_router` yozadi, ya'ni ikkinchi chaqiruv «Router is already
attached» bilan yiqilardi. Testlar `app.main.dp` ning bir marta
qurilgan nusxasini o'qiydi (`test_binding.py` bilan bir xil naqsh).

## Verification Results

| Buyruq | Natija |
| --- | --- |
| `npm run bot:lint` (ruff check + format + mypy) | ✅ EXIT 0 — 21 fayl formatlangan, 20 manba mypy'dan o'tdi |
| `npm run bot:test` | ✅ EXIT 0 — **86 test** |
| `docker compose config --quiet` | ✅ EXIT 0 |
| `tests/unit` (to'liq) | ✅ EXIT 0 — **1268 test** |
| `node --test frontend/scripts/glossary.test.mjs` (G7-9) | ✅ 9/9 — yangi `.po` matnlari taqiqlangan sinonimsiz |
| `docker build --target runtime` + mount'siz `import app.main` | ✅ IN-01 jonli tasdiqlandi |

⚠ Testlar ajratilgan compose loyihasida (`-p sbozor-w0811`, `--no-deps`)
yuritildi va oxirida `down -v` bilan tozalandi. Umumiy
`sbozor-storage-1` konteyneri tegilmadi (`Up (healthy)` bo'lib qoldi),
`ops/seaweedfs/s3.json` fayl bo'lib qoldi.

## Known Stubs

Yo'q. Barcha yangi kalitlar haqiqiy matn bilan to'ldirilgan (uchala
locale), zaxira handler ro'yxatga ulangan va jonli yo'lda ishlaydi.

## Threat Flags

Yangi yuza yo'q. Zaxira handler yangi xabar yo'li ochadi, lekin u
rejaning `<threat_model>` ida allaqachon qayd etilgan (T-08-43 va
T-08-44) va ikkalasi ham `mitigate` sifatida bajarildi:

| Threat ID | Holat | Bajarilishi |
| --- | --- | --- |
| T-08-43 | ✅ mitigated | Zaxira router oxirida; uchta test bilan o'lchandi |
| T-08-44 | ✅ mitigated | Javob terilgan matnni o'qimaydi/takrorlamaydi; chegara izohda literal |
| T-08-45 | ✅ mitigated | `try/except` + FSM tozalash + nomlangan xabar |
| T-08-46 | ✅ mitigated | Har blok sarlavhasida bozor; ikkinchi so'rov yo'q |
| T-08-47 | ✅ mitigated | Kalit olib tashlandi (B yo'li) + regressiya to'sig'i |
| T-08-SC | ✅ accept | Yangi paket yo'q — `pyproject.toml` diffda yo'q |

⚠ Bir qo'shimcha kuzatuv (yangi flag emas, mavjud farazning
tasdig'i): WR-14 ni tekshirish paytida `08-UI-SPEC` M-9 ning «bir xil
origin farazi allaqachon ko'taruvchi» bandi **kod darajasida
tasdiqlandi** — core-api'da `CORSMiddleware` yo'q. Bu faraz endi
`compose.yaml` izohida ham yozilgan, ya'ni keyingi ishlovchi uni
UI-SPEC dan qidirmaydi.

## Commits

| Commit | Turi | Mazmun |
| --- | --- | --- |
| `0ce3cc8` | test | WR-04 uchun yiqiladigan testlar (RED) |
| `2e7a44b` | feat | Zaxira handler + `bot.unknown` uchala locale'da (GREEN) |
| `1552001` | test | WR-02/WR-03 uchun yiqiladigan testlar (RED) |
| `fdaccd0` | fix | Buzuq FSM javob beradi, blokda bozor ko'rinadi (GREEN) |
| `6b3ad15` | chore | IN-01, IN-07, WR-14 |

## Keyingi ish uchun eslatma

`deferred-items.md` dagi WR-14 bandi shu rejada **yopildi**. Uning
yozuvidagi «8-faza» egasi endi bajarilgan — reyestrni yangilash 08-faza
yakunidagi umumiy tozalash ishiga qoladi (bu reja `deferred-items.md`
ni tegmadi, chunki u boshqa to'lqin rejalari bilan kesishadigan
umumiy fayl).
