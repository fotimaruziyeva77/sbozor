---
phase: 03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi
plan: 13
subsystem: live-view-credential-leg
tags: [gap-closure, rtsp-credentials, secretstr, ssrf, percent-encoding, sentry-scrub, breadcrumb, d-12, wave-1]

# Dependency graph
requires:
  - phase: 03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi
    plan: 04
    provides: "`encrypt_nvr_password`/`decrypt_nvr_password`, `SecretStr` sozlama standarti, `NvrRepository.get_credential`"
  - phase: 03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi
    plan: 07
    provides: "`services/go2rtc.py` (allow-list + `Go2rtcClient`), `api/v1/cameras.py::_ensure_stream`, `test_live_view.py` ning `go2rtc_calls` fixture'i"
  - phase: 03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi
    plan: 06
    provides: "`jobs/discovery.py` dagi `get_credential` -> `decrypt` -> `InvalidToken` naqshi"
  - phase: 01-poydevor-va-tenant-xavfsizligi
    plan: 06
    provides: "`main.py::_scrub_event` va `_PII_KEYS` (Sentry `before_send`)"
provides:
  - "`app/services/live_source.py` — `authenticated_rtsp_source()`: foizli kodlash + avtoritet-saqlanish darvozasi, natija `SecretStr`"
  - "`decrypt_nvr_password` ning ILOVADAGI IKKINCHI chaqiruv joyi — `api/v1/cameras.py::_ensure_stream` (jonli ko'rish yo'li)"
  - "`Go2rtcClient.ensure_stream(name, src: SecretStr)` — sir tashuvchi imzo va sirsiz `Go2rtcError`"
  - "`main.py::_scrub_breadcrumb` (`before_breadcrumb`) + `_scrub_event` ning matn darajasidagi maskalash qatlami"
  - "50 yangi test items (`test_live_source.py` 24, `test_sentry_scrub.py` 17, `test_go2rtc_client.py` +8, `test_live_view.py` +1)"
affects: [03-14-uchidan-uchiga-jonli-korish, 04-snapshot-pipeline]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Sirni URL'ga qo'shish IKKI QADAM: `quote(..., safe=\"\")` va natijani QAYTA AJRATIB xost/port/yo'l/query/fragment tengligini talab qilish. Ikkinchisi kodlashning ishlaganini NATIJADAN o'lchaydi, kod o'qishdan emas — fail-closed"
    - "Sir tashuvchi `SecretStr` FUNKSIYA CHEGARASIDA, sozlamada emas: `repr()` istisno matnida, pytest diffida va Sentry lokal-o'zgaruvchilar suratida chiqadi, ya'ni oddiy `str` birinchi istisnodayoq oqardi"
    - "`{exc}` interpolyatsiyasi SIRLI URL bo'lgan chaqiruvda TAQIQ: `httpx.HTTPStatusError` matni to'liq so'rov URL'ini tashiydi. O'rniga istisno SINFI + status kodi — diagnostika uchun yetadi"
    - "`raise ... from None` FAQAT sirli URL bo'lgan blokda; sirsiz bloklarda kontekst TO'LIQ qoladi. Farq ataylab va u kod ichida sabab bilan yozilgan"
    - "Sentry uchun maskalash MAYDON RO'YXATI bilan emas, MATN darajasida va CHUQUR: sir kamida uch joydan tushadi (istisno matni, query satri, freym lokallari) va ro'yxat to'rtinchi joy paydo bo'lganda jimgina eskirardi"
    - "`before_send` YETMAYDI — `before_breadcrumb` ALOHIDA kerak: breadcrumb hodisadan OLDIN, muvaffaqiyatli chaqiruvda ham yoziladi"
    - "Darvozaning O'ZI test bilan o'lchanadi: to'g'ri kodda hech qachon ishga tushmaydigan tekshiruv `monkeypatch` bilan sun'iy buzilgan holatda sinaladi (`test_no_sim_branching::test_gate_detects_a_planted_marker` naqshi)"
    - "Test seed'ining ATAYIN yaroqsiz qiymati (`NVR_PASSWORD_PLACEHOLDER`) o'rniga to'g'ri qiymat TEST DOIRASIDA yoziladi — seed'ni o'zgartirish o'sha yaroqsizlikka tayanadigan boshqa testni jimgina ma'nosiz qilardi"

key-files:
  created:
    - services/core-api/app/services/live_source.py
    - tests/unit/test_live_source.py
    - tests/unit/test_sentry_scrub.py
  modified:
    - services/core-api/app/services/go2rtc.py
    - services/core-api/app/api/v1/cameras.py
    - services/core-api/app/main.py
    - tests/unit/test_go2rtc_client.py
    - tests/integration/test_live_view.py
    - tests/integration/test_phase3_criteria.py

key-decisions:
  - "GAP-1 ning mexanizmi yozildi: `_ensure_stream()` endi `repo` ni oladi va `rtsp_url()` -> `get_credential()` -> `decrypt_nvr_password()` -> `authenticated_rtsp_source()` -> `ensure_stream()` ketma-ketligini bajaradi. Bu `decrypt_nvr_password` ning ilovadagi IKKINCHI chaqiruv joyi va u `03-RESEARCH.md` D.13 ning «faqat go2rtc konfiguratsiyasi hosil qilinayotganda ochiladi» talabini AYNAN bajaradi"
  - "`rtsp_url()` NING IMZOSI TEGILMADI (T-03-24). Saqlanadigan/jurnalga tushadigan manzil hamon rekvizitsiz; rekvizit ALOHIDA modulda (`live_source.py`) va faqat chiqish paytida qo'shiladi. Ikkalasini bir faylga yig'ish `rtsp_url()` ning imzo darvozasini ma'nosiz qilardi"
  - "Inyeksiya darvozasi (natijani qayta ajratib avtoritet tengligini talab qilish) — «ehtiyot chorasi» emas, T-03-88 ning YAGONA o'lchovi. `pa@evil.example/` shaklidagi parol kodlanmasa go2rtc'ni butunlay boshqa xostga ulantirardi va NVR rekvizitini o'sha yerga TAQDIM ETARDI"
  - "DEVIATION (reja ichidagi ziddiyat hal qilindi): Task 2 ning `<behavior>` i «`__cause__` zanjiri parolni tashimaydi» deydi, `<action>` esa «`from exc` zanjiri saqlanadi». Ikkalasi bir vaqtda bajarilmaydi — `httpx.HTTPStatusError` matni tabiatan URL'ni tashiydi. Yechim: `from None` FAQAT `PUT` blokida (uning URL'ida sir bor), `has_stream`/`remove_stream` da esa `from exc` saqlandi (ularning URL'ida sir yo'q). Yo'qolgan yagona narsa — httpx ning o'z matni; amal/tur/status `_failure()` da qoladi"
  - "DEVIATION (Rule 2, rejada yo'q): `_scrub_event` maydon ro'yxati bilan emas, CHUQUR va MATN darajasida ishlaydi. Sabab o'lchangan: `go2rtc.py::ensure_stream` da ochilgan manba LOKAL O'ZGARUVCHIDA yotadi va Sentry `include_local_variables` bilan uni `stacktrace.frames[].vars` ga qo'yadi — `request.query_string` ni tozalash u yerda hech nimani himoya qilmasdi"
  - "Maskalash IKKI QOIDA bilan va ular bir-birini ALMASHTIRA OLMAYDI: `src=<qiymat>` (`&` gacha) percent-encoded shaklni ushlaydi (`httpx` chiquvchi URL'da aynan shunday yozadi — o'lchandi), `rtsp://user:pass@` esa freym lokallaridagi XOM satrni. Ikkalasi ham o'z testiga ega"
  - "Rekvizit nosozligi (qator yo'q / `InvalidToken`) uchun YANGI xato kodi kiritilmadi: admin uchun sabab bir xil (`503 live_view_unavailable`) va bu yo'l NVR hisobiga urinish YUBORMAYDI, ya'ni §4.4 qulfi qo'llanmaydi"
  - "`test_stream_registered_dynamically` ning `\"@\" not in src` asserti TESKARISIGA aylandi (`count(\"@\") == 1`) va bu T-03-24 ni BUZMAYDI: o'sha kafolat `rtsp_url()` ning imzosida yashaydi va `test_rtsp_url.py` da ikkita alohida test bilan qulflanadi. go2rtc'ga boradigan manba esa boshqa qiymat — u saqlanmaydi va `SecretStr` ichida tashiladi"
  - "Seed'ning `NVR_PASSWORD_PLACEHOLDER` i O'ZGARTIRILMADI. U ATAYIN Fernet tokeni emas va `test_nvr_discovery_job.py` aynan shunga tayanib `InvalidToken` shoxini o'lchaydi; almashtirish o'sha testni jimgina ma'nosiz qilardi. Haqiqiy token TEST DOIRASIDA yoziladi (`real_credentials` fixture'i / `_store_real_credential()` yordamchisi)"
  - "`test_phase3_criteria.py` ning 948/950-qatorlaridagi `source` interpolyatsiyasi olib tashlandi (T-03-91) — VA `assert len(go2rtc_calls) == 1, go2rtc_calls` ham: u ham butun ro'yxatni, ya'ni parolli manbani CI jurnaliga chiqarardi. Rejada faqat ikkita qator nomlangan edi, uchinchisi shu yerda topildi"

patterns-established:
  - "Pattern: sirni qabul qiladigan funksiyaning imzosi `SecretStr` bo'ladi va `get_secret_value()` BITTA, grep bilan topiladigan qatorda chaqiriladi (`nvr_cipher()` ning 03-04 dagi qoidasi funksiya chegarasiga ko'chirildi)"
  - "Pattern: xavfsizlik darvozasi to'g'ri kodda hech qachon ishga tushmasa, uning O'ZI monkeypatch bilan sun'iy buzilgan holatda sinaladi — «yashil» aks holda darvozaning tirikligini isbotlamaydi"
  - "Pattern: test assertining XATO XABARI ham sizish yuzasi. Sir tashiydigan qiymat xabarga interpolyatsiya qilinmaydi; o'rniga «nima kutilgan» yoziladi va qiymat `urlsplit` bilan qismlarga ajratib tekshiriladi"
  - "Pattern: «hech qayerda ko'rinmaydi» testi NAZORAT BANDI bilan tugaydi — izlanayotgan qiymat mahsulot yo'lida HAQIQATAN mavjud ekani alohida assert bilan tasdiqlanadi, aks holda mexanizmni olib tashlash testni jimgina yashil qoldirardi"

requirements-completed: [CAM-03, CAM-01]

# Metrics
duration: 82min
completed: 2026-08-03
---

# Phase 3 Plan 13: go2rtc rekvizit oyog'i va uch oqish yo'lining yopilishi Summary

**`03-VERIFICATION.md` GAP-1 ning birinchi `missing[]` bandi yopildi: `decrypt_nvr_password` endi ilovada IKKI joyda chaqiriladi va ikkinchisi jonli ko'rish yo'lida — go2rtc'ga boradigan `src` rekvizitli, foizli kodlangan va `SecretStr` ichida tashiladi; parolning ochiq matni javobda, jurnalda, auditda, istisno matnida va Sentry hodisasida yo'qligi beshta mustaqil test bilan o'lchandi.**

## Performance

- **Duration:** ~82 min (21:39 → 23:01)
- **Tasks:** 3/3, uchtasi ham alohida commit
- **Files:** 9 (3 yangi, 6 o'zgargan), 1667 qator qo'shildi / 44 o'chirildi
- **Sabotajlar:** 4/4 bajarildi, har biridan keyin ish daraxti toza

## Accomplishments

- **Fazani 5/8 ga tushirgan uzilish yopildi.** Kechagi kodda `_ensure_stream()` `src` ni faqat `host`, `rtsp_port`, `channel_no` dan qurar va `nvr_credentials` ga umuman murojaat qilmasdi — real Hikvision NVR bunday manbaga **401** beradi. Endi ketma-ketlik to'liq: `rtsp_url()` → `repo.get_credential()` → `decrypt_nvr_password()` → `authenticated_rtsp_source()` → `client.ensure_stream()`.
- **T-03-88 (SSRF) yopildi va O'LCHANDI.** Parolda `@`/`/` bo'lsa avtoritet qayta yozilardi; `quote(..., safe="")` + natijani qayta ajratib xost/port/yo'l tengligini talab qilish buni imkonsiz qildi. Darvozaning o'zi `monkeypatch` bilan kodlashni chetlab o'tgan holatda sinaladi.
- **T-03-87 (istisno matni) yopildi.** `httpx.HTTPStatusError` ning matni to'liq so'rov URL'ini tashiydi va u `?src=rtsp://admin:PAROL@…`. Sabotaj S2 buni AYNAN ko'rsatdi (quyida, xom chiqish bilan).
- **T-03-89 (Sentry breadcrumb) yopildi.** `before_breadcrumb` qo'shildi; `_scrub_event` esa endi butun hodisa bo'ylab matn darajasida maskalaydi — chunki sir freym lokallariga ham tushadi.
- **T-03-91 (test xabari) yopildi va REJADAN KENGROQ:** rejada ikkita qator nomlangan edi, uchinchisi (`assert len(go2rtc_calls) == 1, go2rtc_calls`) shu yerda topildi.
- **D-11 REGRESSIYA QILMADI:** `assert_safe_go2rtc_src` o'zgarmadi, u ochilgan qiymat ustida va tarmoqqa chiqishdan OLDIN ishlaydi; `SecretStr("exec:rm -rf /")` uchun `ValueError` va tarmoqqa **hech nima chiqmasligi** yangi test bilan qulflandi.
- **Bazaviy darvoza kengaydi:** backend `pytest --co` → **1507** (5 hardware deselected), ya'ni **+50** test item; tenancy **412** (o'zgarmadi). `npm run lint` → exit 0.

## Task-by-task

| Task | Nomi | Commit | Asosiy fayllar |
| ---- | ---- | ------ | -------------- |
| 1 | `authenticated_rtsp_source()` (TDD) | `1ae4138` | `app/services/live_source.py`, `tests/unit/test_live_source.py` |
| 2 | `Go2rtcClient` `SecretStr` oladi, istisno matni tozalandi (TDD) | `9ee9b19` | `app/services/go2rtc.py`, `tests/unit/test_go2rtc_client.py` (+ chaqiruv joylari) |
| 3 | Jonli ko'rish yo'li rekvizitni ochadi; uch oqish yo'li yopildi | `1cbfe89` | `app/api/v1/cameras.py`, `app/main.py`, `tests/unit/test_sentry_scrub.py`, ikkala integratsiya fayli |

## `test_go2rtc_client.py` — test soni

| Holat | Test items |
| ----- | ---------- |
| O'zgarishdan OLDIN | **19** |
| O'zgarishdan KEYIN | **27** (+8) |

Yangi sakkiztasi: imzo darvozasi, rekvizitli `PUT` ning yuborilishi, mavjud oqimda `PUT` yuborilmasligi, `exec:` ning tarmoqqa chiqmasligi, `PUT` xatosida URL/parolning yo'qligi, `GET` xatosida javob tanasining yo'qligi, muvaffaqiyatli `has_stream` ning ro'yxatni jurnalga yozmasligi, `DELETE` xatosining shakli.

Klient testlari `httpx.MockTransport` bilan ishlaydi va **mahsulot konstruktori to'liq bajariladi** — `_client` xususiy atributiga tegilmaydi (u yopilmagan klient qoldirardi va `timeout` berilishini chetlab o'tardi).

## Sabotajlar — nomma-nom natija

### S1 — `quote(password, safe="")` → `quote(password)`

**Buyruq:** `pytest tests/unit/test_live_source.py tests/unit/test_rtsp_url.py` → **3 failed, 43 passed**

| Qizardi | Qaysi assert |
| ------- | ------------ |
| `test_password_with_slash_at_and_colon_keeps_the_authority_and_path` | chaqiruvning O'ZI: `ValueError: rtsp_credential_injection` |
| `test_password_shaped_like_an_authority_cannot_redirect_the_stream` | chaqiruvning O'ZI: `ValueError: rtsp_credential_injection` |
| `test_quote_is_called_with_an_empty_safe_set` | `assert recorded == ["", ""]` → `['', '/']` |

**Yashil qoldi:** `test_live_source.py` ning qolgan 21 item'i va `tests/unit/test_rtsp_url.py` ning **22/22** si.

⚠ **REJADAN CHETLANISH (kutilgandan KUCHLIROQ natija).** Reja «aynan `path` tengligi assertida» qizarishini kutgan edi. Amalda inyeksiya DARVOZASI (natijani qayta ajratish) ishga tushib, funksiya `path` assertigacha yetmasdan `ValueError` ko'tardi — ya'ni qizarish assert qatorida emas, chaqiruv qatorida ko'rindi. O'lchanayotgan DA'VO aynan bir xil (standart `safe` bilan yo'l chegarasi siljiydi), lekin nosozlik shakli boshqa: darvoza uni assertdan OLDIN ushlaydi va bu to'g'ri fail-closed yo'nalish. Uchinchi qizargan test (`test_quote_is_called_with_an_empty_safe_set`) esa usulni to'g'ridan-to'g'ri qulflaydi va «nima buzildi» savoliga bir qatorda javob beradi.

### S2 — `PUT` blokidagi xabar `{exc}` ga qaytarildi (`raise ... from exc` bilan)

**Buyruq:** `pytest tests/unit/test_go2rtc_client.py` → **1 failed, 26 passed**

| Qizardi | Qaysi assert |
| ------- | ------------ |
| `test_ensure_stream_failure_carries_neither_the_url_nor_the_password` | `assert SECRET not in rendered` (fayl qatori 318) |

Xom chiqish (oqish yo'lining bevosita dalili):

```
Go2rtcError("go2rtc `PUT /api/streams` yiqildi: Client error '400 Bad Request' for url
'http://go2rtc.invalid:1984/api/streams?name=cam_…&src=rtsp%3A%2F%2Fadmin%3ASekret123%40nvr.invalid%3A554%2F…'")
```

**Yashil qoldi:** `test_rejects_exec_source` va `test_go2rtc_client.py` ning qolgan **26/27** i.

### S3 — `_ensure_stream` dan rekvizit oyog'i olib tashlandi

**Buyruq:** `pytest tests/integration/test_phase3_criteria.py tests/unit/test_go2rtc_client.py tests/integration/test_live_view.py` → **3 failed, 53 passed**

| Qizardi | Qaysi assert |
| ------- | ------------ |
| `test_phase3_criteria.py::test_sc7_the_whole_flow_runs_against_a_simulator` | **`assert parts.username == quote(username, safe="")`** → `assert None == 'admin'` (aynan reja talab qilgan «manbada foydalanuvchi nomi bor» asserti) |
| `test_live_view.py::test_stream_registered_dynamically` | `assert parts.username == NVR_USERNAME` |
| `test_live_view.py::test_live_token_never_leaks_the_device_password` | nazorat bandi: `assert real_credentials in source` |

**Yashil qoldi:** `test_sc6_live_view_requires_authorization` (u avtorizatsiyani o'lchaydi, rekvizitni emas), qolgan yettita mezon testi va `tests/unit/test_go2rtc_client.py` ning **27/27** i.

### S4 — `_scrub_breadcrumb` tanasi `return crumb` ga tushirildi

**Buyruq:** `pytest tests/unit/test_sentry_scrub.py` → **3 failed, 14 passed**

| Qizardi | Qaysi assert |
| ------- | ------------ |
| `test_http_breadcrumb_url_loses_the_rtsp_credentials` | `assert SECRET not in str(data["url"])` |
| `test_http_breadcrumb_query_field_is_masked_too` | `assert SECRET not in str(data["http.query"])` |
| `test_breadcrumb_message_is_masked` | `assert SECRET not in str(result["message"])` |

**Yashil qoldi:** `_scrub_event` ning to'qqizala testi, `test_non_http_breadcrumb_passes_through_untouched` (nazorat) va `test_sentry_init_wires_both_hooks` — oxirgisi ULANISHNI o'lchaydi, XULQNI emas, ya'ni ikkalasi to'ldiruvchi darvoza.

## `_scrub_event` / `_scrub_breadcrumb` qamragan Sentry maydonlari

| Ilmoq | Maydon | Nima qilinadi | Testi |
| ----- | ------ | ------------- | ----- |
| `before_breadcrumb` | `data["url"]` | `src=<qiymat>` → `src=***` | `test_http_breadcrumb_url_loses_the_rtsp_credentials` |
| `before_breadcrumb` | `data["http.query"]` (va `data` dagi har satr) | bir xil | `test_http_breadcrumb_query_field_is_masked_too` |
| `before_breadcrumb` | `message` | xom `rtsp://user:pass@` → `rtsp://***@` | `test_breadcrumb_message_is_masked` |
| `before_send` | `request.data`, `request.cookies` | butunlay OLIB TASHLANADI (mavjud xulq) | `test_request_body_and_cookies_are_dropped` |
| `before_send` | `request.headers[Authorization|Cookie]` | `***` (mavjud xulq) | `test_authorization_and_cookie_headers_are_masked` |
| `before_send` | `extra[<_PII_KEYS>]` | `***`; reyestrga **`src`** va **`source`** qo'shildi | `test_pii_keys_in_extra_are_masked` |
| `before_send` | `exception.values[].value` | `src=***` / `rtsp://***@` | `test_exception_value_loses_the_request_url` |
| `before_send` | `request.query_string` | bir xil | `test_request_query_string_is_masked` |
| `before_send` | `exception.values[].stacktrace.frames[].vars` | bir xil | `test_stack_frame_locals_lose_the_raw_source` |

Rekvizitsiz `rtsp://` manzil **o'zgarmaydi** (`test_masking_leaves_credential_free_sources_alone`) — aks holda Sentry'dagi hodisadan qaysi NVR haqida gap ketayotgani yo'qolardi.

## Deviations from Plan

### Auto-fixed / hal qilingan ziddiyatlar

**1. [Rule 3 - Blocking] `ensure_stream` imzosi o'zgarishi chaqiruv joylarini buzdi**
- **Found during:** Task 2
- **Issue:** `src: str` → `src: SecretStr` o'zgarishi `cameras.py` ni va ikkala test mock'ini (`_RecordingClient`) darhol tip xatosiga olib keldi; `npm run lint` Task 2 ning done-mezoni.
- **Fix:** Task 2 commit'iga `cameras.py` ning minimal moslashuvi (`SecretStr(source)`) va ikkala mock'ning yangi imzosi kiritildi. Task 3 `SecretStr(source)` ni haqiqiy rekvizit oyog'i bilan almashtirdi.
- **Files modified:** `app/api/v1/cameras.py`, `tests/integration/test_live_view.py`, `tests/integration/test_phase3_criteria.py`
- **Commit:** `9ee9b19`

**2. [Rule 1 - Bug] `test_phase3_criteria.py` ga qo'yilgan izoh SC#1 ning usul qulfini buzdi**
- **Found during:** Task 3, to'liq to'plam yurgizilganda
- **Issue:** «`source` interpolyatsiyasi nega olib tashlandi» degan izohda RTSP sxemasining LITERALI yozilgan edi. `test_sc1_...` esa fayl matnini o'qib o'sha literalning YO'QLIGINI talab qiladi va izohlarni ajratmaydi — bu shu fazadagi grep-darvoza darsining to'rtinchi takrori.
- **Fix:** izoh `<sxema>://<user>:<PAROL>@...` shakliga o'tkazildi + qoidaning O'ZI o'sha izohga yozildi.
- **Commit:** `1cbfe89`

**3. [Rule 2 - Missing critical] `assert len(go2rtc_calls) == 1, go2rtc_calls` ham parolni chiqarardi**
- **Found during:** Task 3
- **Issue:** Reja T-03-91 uchun 948 va 950-qatorlarni nomlagan. Uchinchi qator (`946`) esa butun `go2rtc_calls` ro'yxatini xato xabariga qo'yardi — ya'ni yiqilganda AYNAN o'sha rekvizitli manbani CI jurnaliga chiqarardi.
- **Fix:** xabar `f"`ensure_stream` {len(go2rtc_calls)} marta chaqirildi"` ga o'zgartirildi. Bir xil tuzatish `test_live_view.py` da ham qo'llandi.
- **Commit:** `1cbfe89`

**4. [Rule 2 - Missing critical] Sentry freym lokallari — rejada nomlanmagan to'rtinchi yuza**
- **Found during:** Task 3(B)
- **Issue:** Reja `_scrub_event` uchun `request.query_string` ni va `_PII_KEYS` ga `src` qo'shishni nomlagan. Lekin `go2rtc.py::ensure_stream` da OCHILGAN manba lokal o'zgaruvchida (`source`) yotadi va Sentry `include_local_variables` bilan uni `stacktrace.frames[].vars` ga `repr` qilib qo'yadi — `src=` naqshi u yerda ishlamaydi (qiymat yalang'och satr).
- **Fix:** `_scrub_event` chuqur va matn darajasida ishlaydigan qildi; ikkinchi qoida (`rtsp://user:pass@` → `rtsp://***@`) qo'shildi; `_PII_KEYS` ga `source` ham kirdi. `test_stack_frame_locals_lose_the_raw_source` bu yuzani alohida o'lchaydi.
- **Commit:** `1cbfe89`

**5. [Reja ziddiyati hal qilindi] `__cause__` zanjiri va `from exc`**
- **Issue:** Task 2 ning `<behavior>` i «`Go2rtcError` ning `__cause__` zanjiri ham parolni tashimaydi» deydi; `<action>` esa «`raise ... from exc` zanjiri saqlanadi». `httpx.HTTPStatusError` ning matni tabiatan URL'ni tashiydi, ya'ni ikkalasi bir vaqtda bajarilmaydi.
- **Qaror:** `from None` FAQAT `PUT` blokida (uning so'rov URL'ida sir bor), `has_stream`/`remove_stream` da `from exc` saqlandi (ularning URL'ida sir yo'q). Farq kod ichida sabab bilan yozilgan. `test_ensure_stream_failure_carries_neither_the_url_nor_the_password` ham `__cause__ is None`, ham `__suppress_context__ is True` ni tekshiradi.
- **Nima yo'qoldi:** faqat `httpx` ning O'Z xabari. Qaysi amal, qaysi istisno turi va qaysi status `_failure()` da saqlanadi va test ularning borligini alohida assert qiladi.

**6. [Test uskunasi] Seed rekviziti — `fixtures/nvr_domain.py` TEGILMADI**
- **Issue:** `NVR_PASSWORD_PLACEHOLDER` ATAYIN Fernet tokeni emas, jonli ko'rish yo'li esa endi uni ochishga urinadi → seed ustida ishlaydigan muvaffaqiyat testlari 503 olardi.
- **Nega seed o'zgartirilmadi:** `tests/integration/test_nvr_discovery_job.py:404` aynan o'sha yaroqsizlikka tayanib `InvalidToken` shoxini o'lchaydi; placeholder'ni almashtirish o'sha testni JIMGINA ma'nosiz qilardi.
- **Yechim:** haqiqiy Fernet tokeni TEST DOIRASIDA yoziladi — `test_live_view.py::real_credentials` fixture'i va `test_phase3_criteria.py::_store_real_credential()` yordamchisi. Reja `files_modified` idan chetga chiqilmadi.

**7. [Reja buyrug'i ishlamadi] `done` mezonidagi `python -c` chaqiruvi**
- **Issue:** `docker compose --profile test run --rm tests python -c "import app..."` → `ModuleNotFoundError: No module named 'app'`. `app` paketi faqat pytest'ning `pythonpath` i orqali ko'rinadi (`pyproject.toml:26`), yalang'och `python` da emas.
- **Yechim:** ekvivalent buyruq ishlatildi: `sh -c 'PYTHONPATH=/app/services/core-api python -c "…"'`. Ikkala imzo darvozasi ham shu bilan tasdiqlandi (natijalar quyida).

### Rejada bo'lgan, LEKIN topilmagan

`test_go2rtc_client.py` da «mavjud `ensure_stream` testlari» YO'Q edi — fayl faqat `assert_safe_go2rtc_src` ni va konfiguratsiya darvozalarini sinardi, klientning O'ZI birorta test bilan qamralmagan edi. Ya'ni «moslash» o'rniga sakkizta YANGI test yozildi va klientning tarmoq xulqi shu rejada BIRINCHI marta o'lchandi.

## Verification

| Tekshiruv | Natija |
| --------- | ------ |
| `ruff check . && ruff format --check . && mypy .` | **exit 0** — 197 fayl formatlangan, 192 manbada mypy xatosi yo'q |
| `pytest -q` (backend, `-m "not hardware"`) | **exit 0** |
| `pytest --co -q` | **1507 tests collected (5 deselected)** — kamaymadi, +50 |
| `pytest tests/tenancy` | **412 passed** — o'zgarmadi |
| `pytest tests/integration/test_phase3_criteria.py` | **9 passed** — sakkizala mezon + `test_every_criterion_has_its_own_test` |
| `pytest tests/integration/test_live_view.py tests/unit/test_sentry_scrub.py tests/unit/test_no_sim_branching.py` | **42 passed** |
| `grep -rl 'decrypt_nvr_password' services/core-api/app/` | **5 fayl** — `security/secrets.py`, `jobs/discovery.py`, **`api/v1/cameras.py`**, `repositories/nvr_repo.py` (docstring), `services/live_source.py` (docstring) |
| `grep -c 'authenticated_rtsp_source' services/core-api/app/api/v1/cameras.py` | **3** |
| `authenticated_rtsp_source` imzosi | `(source: 'str', username: 'str', password: 'str') -> 'SecretStr'` |
| `Go2rtcClient.ensure_stream` imzosi | `(self, stream_name: 'str', src: 'SecretStr') -> 'bool'` |
| `test_no_sim_branching.py` | yashil — yangi modulda taqiqlangan satr yo'q |

## Known Stubs

Yo'q. Bu reja birorta placeholder/`TODO` qoldirmadi — barcha yangi kod mahsulot yo'lida chaqiriladi va test bilan qamralgan.

## Threat Flags

Yo'q. Yangi tarmoq endpointi, autentifikatsiya yo'li yoki sxema o'zgarishi kiritilmadi; o'zgargan yagona ishonch chegarasi (`core-api` → go2rtc HTTP API) rejaning `<threat_model>` ida allaqachon nomlangan va uning to'rtala `mitigate` dispozitsiyasi (T-03-87…T-03-92) bajarildi.

## Issues & Notes

1. **`GET /api/streams` javobi endi barcha bozorlarning rekvizitli `src` larini qaytaradi (T-03-90).** D-11 ning uchala qatlami buni to'sadi va ular o'zgarmadi, LEKIN yuza qimmatlashdi: 1984-portning publish qilinmagani endi «ehtiyot chorasi» emas, TO'G'RIDAN-TO'G'RI sir himoyasi. `test_compose_does_not_publish_the_go2rtc_api_port` va nginx'ning ikkala 403 bloki shu sababdan endi yanada kritik.
2. **go2rtc'ning O'Z jurnali sirni ko'radi.** `PUT /api/streams?...&src=rtsp://admin:PAROL@…` — bu go2rtc API'sining shakli va uni o'zgartirib bo'lmaydi. Konteyner jurnali `docker logs` da qoladi. 8-faza (deploy runbook) uchun: go2rtc jurnal darajasi va jurnal rotatsiyasi ko'rib chiqilsin, jurnal tashqi log-agregatorga UZATILMASIN.
3. **`t=<jonli chipta>` query parametri maskalanmaydi.** `_mask_secrets` faqat `src=` ni oladi. Chipta 60 soniya yashaydi (D-08), ya'ni xavf past — lekin `t=` ni ham qo'shish bir qatorlik ish va 04-fazada ko'rilsin.
4. **`Go2rtcClient.remove_stream` hamon mahsulot yo'lida chaqirilmaydi** (03-07 dan meros). Arxivlangan kameraning oqimi go2rtc xotirasida rekvizit bilan qolib ketadi — bu endi shunchaki tozalik emas, sir muddati masalasi.
5. **`03-14` uchun:** mock'siz uchidan-uchiga o'lchov endi yozilishi mumkin. `ensure_stream` haqiqiy `SecretStr` oladi va uning ochilgan qiymati `rtsp://` allow-listidan o'tadi; sinash uchun kerak bo'ladigan yagona narsa — 554-portni tinglaydigan RTSP manbai (GAP-1 ning ikkinchi `missing[]` bandi, `03-12` da).
6. **Parallel ish:** `03-12` bilan bir vaqtda ishlandi. Ular `compose.yaml`, `ops/go2rtc/`, `ops/mediamtx/`, `services/nvr-sim/` ni o'zgartiradi; men ularning birorta fayliga tegmadim. `test_go2rtc_client.py::test_production_go2rtc_config_has_no_exec_source` ning docstringidagi `go2rtc.sim.yaml` havolasi olib tashlandi (assert'ning O'ZI tegilmadi — u prod faylni o'qiydi).

## Self-Check: PASSED

- **Fayllar:** 9/9 mavjud (3 yangi: `live_source.py`, `test_live_source.py`, `test_sentry_scrub.py`; 6 o'zgargan)
- **Commitlar:** 3/3 mavjud — `1ae4138`, `9ee9b19`, `1cbfe89`
- **`must_haves.truths`:** 3/3 — `decrypt_nvr_password` ning ikkinchi chaqiruv joyi (`cameras.py`), D-12 ning beshala yuzasi test bilan, maxsus belgilar avtoritetni o'zgartirmasligi
- **`must_haves.artifacts`:** `live_source.py` **178 qator** (min 60 ✓), `test_live_source.py` **383 qator** (min 90 ✓), `authenticated_rtsp_source` eksport qilinadi ✓
- **`must_haves.key_links`:** 2/2 — `cameras.py` → `decrypt_nvr_password` ✓, `cameras.py` → `authenticated_rtsp_source` ✓
- **Sabotajlar:** 4/4, har biridan keyin `git status` **toza**
- **Ish daraxti:** toza; `STATE.md` va `ROADMAP.md` **tegilmadi** (to'lqin merge'idan keyin orkestrator yangilaydi)

---
*Phase: 03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi*
*Completed: 2026-08-03*
