---
phase: 07-nomuvofiqlik-bildirishnoma-va-botlar
plan: 11
subsystem: bot-service
tags: [bot-service, aiogram, i18n, gettext, d-24, d-26, d-04, g7-9, glossary]
requires:
  - "services/bot-service/ — 07-01 skeleti (`settings.telegram_bot_token`, `main.py`, `bot-tests`)"
  - "services/core-api/app/api/internal/bot.py — 07-08 ning uchta marshruti (`resolve` / `vendor/summary` / `vendor/payments`)"
  - "frontend/messages/*.json — 1-6-fazalarning copy'si (G7-9 (a) bandining o'lchov maydoni)"
  - "frontend/scripts/gen-cyrillic.mjs — apostrof normalizatsiyasi qoidasi"
provides:
  - "services/bot-service/app/core_client.py — Bearer + timeout + SIRSIZ xato turi (D-04)"
  - "services/bot-service/app/i18n.py — `get_i18n()`, `compile_catalogues()`, uch locale reyestri"
  - "services/bot-service/app/handlers/{start,binding,vendor}.py — BOT-01 va BOT-02"
  - "uch gettext katalogi (`uz_Latn` / `uz_Cyrl` / `ru`), ko'plik `.po` sarlavhasidan"
  - "ops/i18n/glossary.json — G7-9 ning YAGONA manbai (per-locale `banned_synonyms`)"
  - "frontend/scripts/glossary.test.mjs — G7-9 (a)-(g), 9 test"
  - "services/bot-service/tests/fixtures/ — tarmoqsiz Telegram uskunasi + `CoreDouble`"
affects:
  - "07-17 (faza darvozasi) — `bot:test` endi 66 test beradi"
  - "8-faza (O-03) — `сбор` terminologik siljishi hujjatlashtirildi, egasi o'sha faza"
tech-stack:
  added: []
  patterns:
    - "Sirga ochiq borish AYNAN BITTA joyda + `ast` darvozasi + XULQIY nazorat (`httpx.MockTransport`)"
    - "Taqiq matnini emas, STRUKTURANI qurish: `no_match`/`multiple_matches` uchun ikkinchi shox YO'Q"
    - "Yo'qlikni o'lchash: `dp` ning handler reyestri + magic-filtr zanjiri + izohsiz manba"
    - "PER-LOCALE taqiq — mustaqil tarjima faylini o'z tokeni bilan skanerlash"
    - "Kutilgan to'plamni darvoza faylida QAYTA YOZISH (manbadan import qilmaslik)"
key-files:
  created:
    - services/bot-service/app/core_client.py
    - services/bot-service/app/i18n.py
    - services/bot-service/app/handlers/__init__.py
    - services/bot-service/app/handlers/start.py
    - services/bot-service/app/handlers/binding.py
    - services/bot-service/app/handlers/vendor.py
    - services/bot-service/app/locales/uz_Latn/LC_MESSAGES/bot.po
    - services/bot-service/app/locales/uz_Cyrl/LC_MESSAGES/bot.po
    - services/bot-service/app/locales/ru/LC_MESSAGES/bot.po
    - services/bot-service/tests/conftest.py
    - services/bot-service/tests/fixtures/__init__.py
    - services/bot-service/tests/fixtures/telegram.py
    - services/bot-service/tests/fixtures/core_double.py
    - services/bot-service/tests/unit/test_core_client_secrets.py
    - services/bot-service/tests/unit/test_binding.py
    - services/bot-service/tests/unit/test_vendor_handlers.py
    - services/bot-service/tests/unit/test_locale_parity.py
    - ops/i18n/glossary.json
    - frontend/scripts/glossary.test.mjs
  modified:
    - services/bot-service/app/main.py
    - services/bot-service/Dockerfile
    - services/bot-service/README.md
    - .gitignore
decisions:
  - "`aiogram.test_utils.mocked_bot` CHOP ETILGAN g'ildirakda YO'Q — uskuna `BaseSession` ustida qayta qurildi"
  - "`I18n` DANGASA (`get_i18n()`): modul darajasidagi obyekt `conftest.py` ni ilojsiz qilardi"
  - "`.mo` gitignore'da va HAR YUGURISHDA qayta kompilyatsiya qilinadi — commit qilingani `.po` dan jimgina eskirardi"
  - "`pybabel compile` `base` da EMAS, `dev` va `runtime` da (base'da na venv, na manba bor)"
  - "`bot.help.terms` (/help) qo'shildi — `smena` atamasi sotuvchi yuzasida faqat shu yerda tabiiy uchraydi (G7-9 b)"
  - "«Ko'proq» kursori FSM da (bozor, kursor) NAVBATI — bitta kursor ikki bozor tarixini aralashtirardi"
metrics:
  duration: "~2 soat"
  completed: 2026-08-12
  tasks: 3
  commits: 3
  files: 23
---

# Phase 7 Plan 11: Sotuvchi botga o'zi kiradi — BOT-01 / BOT-02 va G7-9 Summary

**Sotuvchi endi Telegram'da o'z qarzini ko'radi, va uni ko'rish uchun yagona
yo'l — Telegram O'ZI kafolatlagan `contact` obyekti: terilgan raqamni o'qiydigan
handler kodda strukturaviy ravishda YO'Q va bu yo'qlik butun dispatcher bo'yicha
o'lchanadi.**

## Nima qurildi

### Task 1 — `core_client` + `i18n` + `/start` (`7377ff5`)

`core_client.py` — `httpx` ustidagi yupqa qobiq. Uchta qaror mexanik:

| Qaror | Shakl | O'lchov |
|---|---|---|
| Sirga ochiq borish **bitta joyda** | `_service_token_header()`; token `self` ga saqlanmaydi (`__slots__ = ("_client",)`) | `grep -c "Authorization"` → **1**; AST: `get_secret_value()` sanog'i **1** |
| Istisno **matni** yozilmaydi (D-04) | `_failure()` uch fakt beradi: amal / `type(exc).__name__` / status | `test_core_client_secrets.py` — `ast`, 13 test |
| Yuza istisno **ko'taradi** | `AlertSender` dan ATAYIN farq: bu **kiruvchi** yuza, jim yiqilish sotuvchini javobsiz qoldirardi | docstringda + handler testlarida |

⛔ **Darvoza `grep` emas, `ast`** — va bu tanlov o'lchandi (quyida «Sabotaj 2»).
U `app/core_client.py` **va** `app/handlers/*.py` ni skanerlaydi: D-04 ning
ikkinchi yarmi «istisno matni FOYDALANUVCHIGA ko'rsatilmaydi» degani.

⛔ **To'rtinchi qatlam — XULQIY.** Manba skani «token jurnalga tushmaydi» ni
**isbotlamaydi**, u faqat bitta yozish yo'lini yopadi. Shuning uchun
`httpx.MockTransport` bilan (⛔ soketsiz) haqiqiy so'rov qilinadi va **to'rtta**
da'vo o'lchanadi: token **sarlavhada bor** (ijobiy nazorat), URL da **yo'q**,
istisno matnida **yo'q**, jurnal chiqishida **yo'q**. Beshinchi test telefon
raqamining **so'rov tanasida** ketishini va URL da **yo'qligini** o'lchaydi.

### Task 2 — uch darvoza va sotuvchi yuzasi (`fd35266`)

`binding.py` — uch darvoza **bitta shartda** (`or` bilan): alohida `if` lar
biriga qo'shilgan istisno bilan qolgan ikkitasini chetlab o'tish yo'lini ochardi.

⛔ **D-26(a) tenglik TESTGA emas, STRUKTURAGA tayanadi.** Modulda faqat **bitta**
nomlangan holat bor (`BOUND_STATUS`); `no_match` va `multiple_matches` uchun na
konstanta, na shox mavjud. Ikkinchi matnni yozish uchun avval **ikkinchi shoxni
tug'dirish** kerak bo'ladi.

`vendor.py` — «Qarzim» / «To'lovlarim» / «Ko'proq». Kursor FSM da
**(bozor, kursor) juftliklari NAVBATI** sifatida saqlanadi: bitta «oxirgi
kursor» qiymati ikki bozorda faol akkauntning tarixini **aralashtirardi**
(07-08 ning `active_bindings` ko'pligi aynan shu holatni qonuniy deb belgilagan).

### Task 3 — G7-9 va locale parity (`1f62acb`)

`ops/i18n/glossary.json` — ikki manbani bog'laydigan yagona reyestr. Qiymatlar
**o'zak** (o'zbek agglyutinativ, rus **flektiv**): to'liq so'z bilan qidirish
`торговые места` ni topmasdi.

⛔⛔ **`banned_synonyms` IKKI POG'ONALI VA PER-LOCALE** — va bu bu fazaning eng
nozik «jimgina yashil» tuzog'ini yopadi. `ru.json` **mustaqil tarjima fayli**,
lotin matnidan transliteratsiya **hosilasi emas**; uni lotin `yig'im` tokeni
bilan skanerlash **mazmunidan qat'i nazar har doim 0** qaytarardi — darvoza
mavjud bo'lib ko'rinib, **hech nimani o'lchamasdi**. (f) bandi shuning uchun
**uchala locale** uchun alohida nazorat sabotajini talab qiladi.

## O'lchangan dalillar

| Da'vo | Natija |
|---|---|
| `bot-tests pytest -q` | ✅ **66 test** (07-01 dan 21 + yangi 45) |
| `bot-tests`: `ruff check` + `ruff format --check` + `mypy` | ✅ `All checks passed` · `21 files already formatted` · `no issues in 20 source files` |
| `node --test frontend/scripts/glossary.test.mjs` | ✅ **9 test** (7 band + 2 nazorat) |
| `node --test frontend/scripts/*.test.mjs` | ✅ **191 test** (182 + 9 yangi) |
| `node scripts/check-messages.mjs` | ✅ **1115 kalit × 3 til** — kalit va ICU parity to'liq |
| `node scripts/gen-cyrillic.mjs --check` | ✅ drift yo'q |
| root `tests/unit/test_sentry_processes.py` | ✅ **6 test** (`main` atributi va ilmoq TEGILMAGAN) |
| root `pytest tests/unit -q` | ✅ yashil (exit 0) |
| `grep -c "Authorization" core_client.py` | **1** |
| `grep -c "request_contact" start.py` | **4** (≥1) |
| `grep -c "msgfmt" Dockerfile` | **0** |
| `grep -ciE "\bbalance\b" vendor.py` | **0** |
| `grep -cE "\bfloat\(\|\bround\(\|Decimal" vendor.py` | **0** |
| `grep -cE "https?://\|snapshot" vendor.py` | **0** |
| Ishlab chiqarish image'i (`bot-service`, runtime) | ✅ `start`/`binding`/`vendor` routerlari · **6 handler** · `locales: ('uz_Cyrl','uz_Latn','ru')` |
| G7-9 (a) bugungi uchrash soni | `patta` **25/25/17** · `rasta` **99/99/101** · `qarz` **6/6/6** · `smena` **16/16/22** — §14.5 ning [M-10] o'lchovi bilan **aynan mos** |
| G7-9 (c) taqiqlangan tokenlar | oltalasi ham **0** (uz-Latn `yig'im`/`do'kon`, uz-Cyrl `йиғим`/`дўкон`, ru `лавк`/`магазин`) |

## ⛔ Sabotaj natijalari (beshalasi ham BAJARILDI)

| # | Sabotaj | Kutilgan | Natija |
|---|---------|----------|--------|
| 1 | `core_client.py` ga `log.warning("x", detail=str(exc))` | AST darvozasi **qizaradi** | ⛔ **QIZARDI** — `core_client.py:318 — str(...) argumenti ISTISNO (D-04)` |
| 2 | AYNI qator **docstringga** (`str(exc)` va `repr(exc)` so'zlari) | **YASHIL qoladi** | ✅ **YASHIL** (13/13) — darvoza `grep` emasligi o'lchandi |
| 3 | `binding.py` dan `contact.user_id != message.from_user.id` sharti olib tashlandi | AYNAN bitta test qizaradi | ⛔ **QIZARDI** — faqat `test_contact_of_another_user_is_rejected` |
| 4 | `yig'im` → `uz-Latn.json`, `йиғим` → `uz-Cyrl.json`, `магазин` → `ru.json` | (c) bandi **uchalasida ham** qizaradi | ⛔ **QIZARDI, UCHALASI HAM** — chiqishda uchta locale **alohida** nomlandi |
| 5a | ru `bot.po` dan `долг` ning barcha uchrashlari olib tashlandi | (b) bandi qizaradi | ⛔ **QIZARDI** — `ru/bot.po: «qarz» (o'zak «долг») -> 0` |
| 5b | `glossary.json` dan `лавк` tokeni o'chirildi | (d) bandi qizaradi | ⛔ **QIZARDI** — `expected: ['лавк','магазин']`, topilgan `['магазин']` |

⚠ **Sabotaj 5a ning birinchi urinishi YETARLI EMAS edi va bu qimmatli topilma.**
`долг` ni faqat menyu va qoldiq matnlaridan olib tashlaganda darvoza **yashil
qoldi** — chunki so'z `bot.help.terms` da hamon bor edi. Ya'ni (b) bandi
**haqiqatan uchrash sonini** o'lchaydi, «kalit bormi?» ni emas. Sabotaj oxirigacha
(0 uchrash) yetkazilganda darvoza qizardi.

Barcha sabotajlar qaytarildi (`cp` zaxiradan / `git checkout -- <fayl>`;
⛔ `git clean` va `git reset` **ishlatilmadi**), qaytargandan keyin to'plam
yashil va ish daraxti toza.

## Rejadan chetlanishlar

### Rule 3 — bloklovchi: reja MATNI talab qilgan, `files_modified` sanamagan fayllar

**1. [Rule 3] `services/bot-service/Dockerfile` — `pybabel compile`**

- **Topildi:** Task 1. Rejaning qabul mezoni `grep -c "msgfmt" Dockerfile → 0`
  va «`pybabel compile` Dockerfile'da chaqiriladi» deydi, lekin fayl
  `files_modified` da yo'q edi.
- **Muammo:** reja kompilyatsiyani `base` bosqichida so'ragan. U yerda
  **bajarib bo'lmaydi**: `base` da na `uv sync` bajarilgan (`pybabel` yo'q),
  na `app/` ko'chirilgan (`.po` yo'q).
- **Yechim:** qadam ikkala **hosila** bosqichda (`dev` va `runtime`) — manba va
  venv ikkalasi ham mavjud bo'lgan eng erta nuqtada. `runtime` da u
  `useradd`/`USER` dan **oldin** (aks holda `appuser` `/app` ga yoza olmasdi).
  Ikkala bosqich ham qurildi va `runtime` image'da `.mo` fayllari mavjudligi
  o'lchandi.
- **Commit:** `7377ff5`

**2. [Rule 3] `services/bot-service/tests/conftest.py` (YANGI fayl)**

- **Topildi:** Task 1, birinchi yugurishda — `RuntimeError: Found locale 'ru'
  but this language is not compiled!`
- **Muammo:** `aiogram.utils.i18n.I18n.find_locales()` `.po` topib `.mo`
  topmasa **istisno ko'taradi** (o'lchandi: `aiogram/utils/i18n/core.py:78`).
  `bot-tests` esa repo ildizini `/app` **ustiga mount qiladi**, ya'ni image'da
  qurilgan `.mo` fayllari mount ostida **ko'rinmay qoladi**.
- **Yechim:** `conftest.py` (fixture EMAS — pytest uni test modullarini import
  qilishdan **oldin** yuklaydi) `app.i18n.compile_catalogues()` ni chaqiradi.
  U `pybabel compile` ning **o'zi chaqiradigan** ikki funksiyani (`read_po` +
  `write_mo`) ishlatadi — natija ayni, subprocess yo'q.
- **Commit:** `7377ff5`

**3. [Rule 3] `.gitignore` — `*.mo`**

- **Sabab:** `.mo` build artefakti. Commit qilingani `.po` dan **jimgina
  eskirardi**: matn o'zgargan, darvoza esa eski baytni o'lchagan bo'lardi.
  Shartsiz qayta kompilyatsiya bu holatni **strukturaviy ravishda imkonsiz**
  qiladi.
- **Commit:** `7377ff5`

**4. [Rule 3] `services/bot-service/README.md` §5 / §5.1**

- **Sabab:** reja ochiq talab qiladi («kompilyatsiya ... README'da yoziladi»),
  qolaversa §5 «Bot bugun `/start` ga JAVOB BERMAYDI» deb turardi va u endi
  **yolg'on** edi.
- **Commit:** `7377ff5`

**5. [Rule 3] `services/bot-service/tests/fixtures/__init__.py`**

- **Muammo:** paketsiz katalogni mypy **ikki nom** bilan ko'radi
  (`core_double` va `fixtures.core_double`) va «Source file found twice under
  different module names» bilan **butun tekshiruvni to'xtatadi**.
- **Yechim:** `cv-service`/`core-api` dagi bilan **ayni** naqsh — `fixtures/`
  paket, `tests/` ning o'zi emas.
- **Commit:** `fd35266`

### Rule 1 — reja ko'rsatgan API MAVJUD EMAS

**6. [Rule 1 - Nuqson] `aiogram.test_utils.mocked_bot.MockedBot` CHOP ETILGAN
g'ildirakda YO'Q**

- **Topildi:** Task 2 ga tayyorgarlikda, o'lchov bilan:
  `ls /opt/venv/lib/python3.13/site-packages/aiogram/test_utils/` →
  **«No such file or directory»**. Modul aiogram'ning **o'z test to'plamida**
  (GitHub repo) yashaydi va PyPI paketiga kirmaydi.
- **Yechim:** uskuna `tests/fixtures/telegram.py` da **ayni shaklda** qayta
  qurildi: `BaseSession` ning uch abstrakt metodi bajariladi, `make_request`
  so'rovni **ro'yxatga** yozadi va tayyor `Message` qaytaradi. ⛔ Rejaning
  «tarmoqqa chiqmaydi» talabi **kuchaydi**: `make_request` tanasida tarmoq
  chaqiruvi **umuman yo'q**, ya'ni da'vo strukturaviy.
- **Commit:** `fd35266`

### Rejadan ongli chetlanishlar (struktura)

**`vendor_payments()` `market_id` ni MAJBURIY oladi.** Reja imzoni
`(telegram_user_id, cursor)` deb yozgan; 07-08 esa `market_id` ni majburiy
qildi va sababini yozdi (serverda «birinchisini tanlash» sotuvchiga BOSHQA
bozorning tarixini ko'rsatardi). Bot qiymatni `vendor_summary()` javobidan
oladi — tanov **ma'lumotdan** keladi, taxmindan emas.

**`I18n` modul darajasida EMAS, `get_i18n()` (`lru_cache`).** Modul
darajasidagi obyekt `conftest.py` ni **ilojsiz** qilardi: conftest
kompilyatsiya uchun shu moduldan import qilishi kerak, modul darajasidagi
`I18n` esa o'sha import paytida — **kompilyatsiyadan oldin** — yiqilardi.
Fail-loud xossasi saqlandi: `SimpleI18nMiddleware(get_i18n())` `main.py` da
modul darajasida, ya'ni ishlab chiqarishda istisno **import paytida** chiqadi.

**`bot.help.terms` (`/help`) qo'shildi.** G7-9 (b) har atamani bot `.po` da
talab qiladi; `smena` esa sotuvchi yuzasida faqat **atamalar izohida** tabiiy
uchraydi. Uni qoldiq yoki tarix matniga sun'iy tiqishtirish copy'ni buzardi.

**Kataloglar Task 1 commitida to'liq tug'ildi.** `app/i18n.py` import paytida
kataloglarni o'qiydi, ya'ni Task 1 ning O'Z darvozasi (`pytest -q`) `.po`
fayllarisiz **umuman yugurmasdi**. Kalit to'plami — uchala faylning
**kontrakti** va u faqat to'liq holida ma'noli.

## Ochiq bandlar

**1. `npm --prefix frontend test` ning vitest yarmi BU WORKTREE'DA
BAJARILMADI.** `frontend/node_modules` gitignore'da va bu worktree'ga
o'rnatilmagan. ⚠ Lekin bu reja `frontend/` ga **faqat bitta yangi skript**
qo'shdi (`scripts/glossary.test.mjs`) va birorta `.tsx` / `messages/*.json`
**tegilmadi** (`git diff --name-only` bilan o'lchandi). Node'ga bog'liq
bo'lmagan darvozalarning **hammasi** bajarildi va yashil: `node --test
frontend/scripts/*.test.mjs` (**191**), `check-messages.mjs`,
`gen-cyrillic.mjs --check`. Egasi: orkestrator (merge'dan keyin asosiy repoda
`node_modules` mavjud).

**2. `uz_Cyrl` katalogi bugun `language_code` orqali TANLANMAYDI.** Telegram
«o'zbek kirillcha» degan til kodini bermaydi (u faqat `uz` ni beradi). Katalog
**o'lik emas**: mazmuni G7-9 va parity darvozasi bilan o'lchanadi, iste'molchisi
til tanlagichi bo'ladi. Holat `app/i18n.py` docstringida va `README.md` §5.1 da
ochiq yozilgan; ⛔ uni «ishlatilmayapti» deb o'chirish D-31 ni buzardi.

**3. `сбор` terminologik siljishi — 8-fazaga qoldirildi (O-03).** Sabab
`glossary.json` ning `_sbor_exception` bandida **so'z bilan** yozilgan: ru
copy'da 13 kalitda va **ikki xil ma'noda**. Yo'qligi (d) bandining to'plam
tengligidan **hosila** — alohida `not.toContain` yozilmagan.

**4. Haqiqiy Telegram yetkazishi o'lchanmadi.** Barcha testlar `RecordingSession`
va `MockTransport` bilan; tarmoqqa **birorta soket ochilmadi**. Haqiqiy
yetkazish `07-HUMAN-UAT.md` bandi (07-RESEARCH § Environment Availability
buni oldindan qayd etgan).

## Known Stubs

Yo'q. Uchala handler ham haqiqiy `core-api` javobini chizadi; birorta qattiq
kodlangan bo'sh qiymat renderga oqmaydi. `bot.summary.noStalls`
(«biriktirilmagan») — stub emas, **nomlangan holat**: bo'sh joy chizish
o'rniga sabab aytiladi.

## Threat Flags

Yangi, rejaning `<threat_model>` idan tashqaridagi xavf yuzasi **topilmadi**.
`T-07-62`…`T-07-69` mitigatsiyalari amalga oshirildi va mexanik o'lchandi;
`T-07-SC` («yangi paket yo'q») kuchda — birorta bog'liqlik qo'shilmadi
(`pyproject.toml` **tegilmadi**).

⚠ Bitta **kuchaytirish** qayd etiladi: `T-07-65` (servis tokenining istisno
matni orqali sizishi) reja faqat AST skani bilan qoplagan edi; bu yerda unga
**xulqiy** qatlam qo'shildi (`MockTransport` bilan sarlavha / URL / istisno /
jurnal o'lchovi). Bu **yangi yuza emas**, mavjud mitigatsiyaning ikkinchi
qatlami.

## Self-Check: PASSED

Barcha e'lon qilingan fayllar diskda mavjud (19 yangi + 4 tahrirlangan;
`git diff --name-only 4aec616 HEAD` — **23 fayl**) va uchala commit `git log`
da: `7377ff5`, `fd35266`, `1f62acb`.

⛔ Birorta commitda fayl o'chirilishi **YO'Q**
(`git diff --diff-filter=D --name-only 4aec616 HEAD` — bo'sh).

⛔ **`services/core-api/` ostida birorta fayl TEGILMADI** (yondosh agentlar
o'sha katalogda ishlayapti). ⛔ `STATE.md` va `ROADMAP.md` ham **tegilmadi** —
worktree rejimida ularni orkestrator markazlashgan holda yangilaydi.

⛔ Sir commitga tushmadi: `.env` va `ops/seaweedfs/s3.json` gitignore'da va
`git ls-files` ularni ko'rmaydi (ikkalasi ham asosiy repodan **nusxalandi**,
chunki worktree'da yo'q edi). Testdagi tokenlar **uskuna**: `123456:TEST-TOKEN-
NOT-REAL` va `bot-service-token-NOT-REAL-0123456789` — ikkalasi ham hech qanday
muhitda haqiqiy emas. ⛔ Telefon raqami birorta jurnal yozuvida, URL da yoki
foydalanuvchiga ko'rsatiladigan matnda **yo'q** va bu ikkala yo'nalishda ham
test bilan o'lchangan.
