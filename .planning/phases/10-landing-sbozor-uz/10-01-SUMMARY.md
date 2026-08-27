---
phase: 10-landing-sbozor-uz
plan: 01
subsystem: api
tags: [fastapi, telegram, rate-limit, honeypot, anonymous, landing]

# Dependency graph
requires:
  - phase: 04-08
    provides: "AlertSender (services/alerts.py) — sirsiz Telegram jo'natuvchisi"
  - phase: 07-08
    provides: "worker.py::_alert_sender — Settings->AlertSender tarjima funksiyasi"
  - phase: 01
    provides: "ratelimit.py::_bump naqshi, _client_ip, EXEMPT_ROUTES matritsasi"
provides:
  - "POST /api/v1/public/demo-requests — kodbazadagi birinchi anonim yozuv marshruti"
  - "DEMO_ERROR_CODES reyestri (schemas.py) — 10-08 ko'zgu darvozasi uchun manba"
  - "check_demo_request_rate — 5/15daq faqat-IP kesimi (ratelimit.py)"
  - "SenderDep (deps.py) va app.state.sender (main.py lifespan)"
  - "demo_request_chat_id sozlamasi — bo'sh bo'lsa telegram_chat_id ga tushadi"
affects:
  - "10-02/10-04: frontend demo-forma shu endpointga POST qiladi"
  - "10-08: error-codes.test.mjs DEMO_ERROR_CODES ko'zgusini ulaydi"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Anonim marshrut + EXEMPT_ROUTES istisnosi + qamrovni tiklovchi integratsiya fayli"
    - "Honeypot normalizatsiyadan OLDIN — javob kodi bot'ga signal bermaydi"
    - "html.escape(value, quote=False) — parse_mode:HTML ga chiqadigan har foydalanuvchi maydoni"

key-files:
  created:
    - services/core-api/app/api/v1/public.py
    - tests/unit/test_demo_request_contract.py
    - tests/integration/test_demo_request.py
  modified:
    - services/core-api/app/schemas.py
    - services/core-api/app/settings.py
    - services/core-api/app/security/ratelimit.py
    - services/core-api/app/deps.py
    - services/core-api/app/main.py
    - tests/tenancy/test_cross_tenant.py

key-decisions:
  - "Sinxron yuborish + 200 (202 emas): delivered faqat natija ma'lum bo'lganda halol (RESEARCH B-5)"
  - "phone'da field_validator YO'Q — 422 invalid_phone bitta satr bo'lishi uchun marshrutda normalizatsiya"
  - "Rate-limit kaliti FAQAT IP — telefon Valkey'ga yozilmaydi (T-07-41 merosi)"
  - "_alert_sender import qilindi, nusxalanmadi — tarjima bitta joyda (report_repo presedenti)"
  - "DB sanog'i superuser bilan hosila: owner FORCE RLS ostida 0 qator ko'rib yolg'on-yashil berardi"

patterns-established:
  - "Anonim kontrakt darvozalari: token da'volari o'rniga marshrutning o'z 7-band to'plami"

# Metrics
duration: 65min
completed: 2026-08-17
---

# Phase 10 Plan 01: Backend demo-so'rov yo'li Summary

**Anonim `POST /api/v1/public/demo-requests`: IP rate-limit + honeypot + `phonenumbers` normalizatsiya + `AlertSender` orqali sinxron Telegram yetkazish, DB'siz va yolg'onsiz (`delivery_failed`).**

## Nima qurildi

- **Kontrakt** (`schemas.py`): `DemoRequestPayload` (har satr maydonda `max_length`, honeypot `website`, `phone`da atayin validatorsiz), `DemoRequestResponse` (yagona `delivered`), `DEMO_ERROR_CODES` (4 kod, `MARKET_ERROR_CODES` shakli).
- **Rate-limit** (`ratelimit.py`): `check_demo_request_rate` — `check_bot_resolve_rate`ning aynan shakli, 5/15daq, fail-open, kalit faqat IP.
- **Lifespan** (`main.py`): `sender = _alert_sender(settings)` (worker'dan import), `app.state.sender`, `finally`da `aclose()` — `engine`/`cache` bilan bir xil egalik.
- **Router** (`public.py`): qadamlar qat'iy tartibda — IP → rate (429) → honeypot (jim 200, 0 chaqiruv) → normalize (422) → `html.escape` matn → sinxron `send_message` → 200/502.
- **Tenancy** (`test_cross_tenant.py`): `EXEMPT_ROUTES` yozuvi `"global"` bilan, sabab satri qamrov qayerda tiklanganini literal aytadi.
- **Testlar**: 21 unit (kontrakt) + 9 integratsiya (7 must_have bandi + honeypot-tartib isboti + T-10-04 escape xulqi).

## Tekshiruv natijalari

| O'lchov | Natija |
|---|---|
| `pytest tests/unit/test_demo_request_contract.py` | 21 passed |
| `pytest tests/integration/test_demo_request.py` | 9 passed |
| `pytest tests/tenancy tests/integration/test_delivery_surface.py` | exit 0 (to'liq yashil, RESEARCH A9 birinchi kunda yopildi) |
| `ruff check .` + `ruff format --check .` + `mypy .` | exit 0 (361 fayl) |
| Sabotaj 1: `html.escape` olib tashlandi | `test_user_fields_are_html_escaped_in_the_telegram_text` QIZARDI, qaytarildi |
| Sabotaj 2: `delivery_failed` shoxi yolg'on-200 | `test_a_telegram_failure_is_reported_honestly_and_writes_nothing` QIZARDI, qaytarildi |
| Yangi npm/pip paketi | 0 |

RED bosqichi ham o'lchandi: EXEMPT yozuvisiz `test_missing_token_is_rejected[POST_/api/v1/public/demo-requests]` matritsada yiqildi — ya'ni istisno «bepul» emas, usiz tenancy to'plami qizil.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Worktree'da `ops/seaweedfs/s3.json` sir-fayli yo'qligi storage konteynerini sindirdi**
- **Found during:** Task 3 (birinchi `--no-deps`siz `docker compose run`)
- **Issue:** `s3.json` gitignore'da (sir) va worktree checkout'ida mavjud emas; compose `depends_on` tekshiruvi storage'ni worktree yo'llari bilan qayta yaratdi va Docker mavjud bo'lmagan fayl-manzilni KATALOG qilib yaratdi — healthcheck doimiy yiqildi (`s3.json: is a directory`).
- **Fix:** Bo'sh katalog o'chirildi, fayl asosiy repodan (`E:/bozor/ops/seaweedfs/s3.json`) nusxalandi (gitignore'da qoladi, commitga tushmadi), konteyner `--force-recreate` bilan qayta ko'tarildi va healthy bo'ldi. Keyingi barcha test yugurishlari `--no-deps` bilan.
- **Files modified:** yo'q (faqat gitignore'dagi lokal fayl)
- **Commit:** yo'q (repo o'zgarishi yo'q)

**2. [Rule 1 - Bug] SIM300 (Yoda condition) yangi unit testda**
- **Found during:** Task 1 (ruff)
- **Issue:** `assert DEMO_ERROR_CODES == frozenset(...)` — konstanta chap tomonda.
- **Fix:** `expected` o'zgaruvchisi chapga olindi.
- **Files modified:** tests/unit/test_demo_request_contract.py
- **Commit:** bda237f

Boshqa jihatlarda reja aynan yozilganidek bajarildi.

## Known Stubs

Yo'q — barcha yo'llar (muvaffaqiyat, 429, 422, honeypot, 502) haqiqiy implementatsiya bilan yopilgan va testda o'lchangan.

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| threat_flag: new-anonymous-surface | services/core-api/app/api/v1/public.py | Kodbazadagi birinchi autentifikatsiyasiz yozuv endpointi — reja `<threat_model>`ida to'liq qamrovlangan (T-10-01…T-10-07, T-10-11), yangi qamrovlanmagan yuza YO'Q; qatorga faqat kuzatuv uchun qayd |

## Commits

| Hash | Turi | Mazmun |
|---|---|---|
| 3756af7 | test | RED — kontrakt testlari (import xatosi bilan yiqilgan holda) |
| bda237f | feat | GREEN — DTO, DEMO_ERROR_CODES, check_demo_request_rate, demo_request_chat_id |
| 59ef89c | feat | AlertSender lifespan'ga, SenderDep, public.py routeri |
| 8aac1d9 | test | EXEMPT_ROUTES yozuvi + 9 testli integratsiya fayli |

## Keyingi bosqichga eslatmalar

- `DEMO_REQUEST_CHAT_ID` env o'zgaruvchisi ixtiyoriy — bo'sh qoldirsa ops kanali (`TELEGRAM_CHAT_ID`) ishlatiladi; kanal ajratish uchun kod o'zgarishi kerak emas (user_setup bo'limi).
- 10-08 `error-codes.test.mjs` ga `DEMO_ERROR_CODES` ko'zgu blokini ulashi kerak (frontmatter `provides`).
- Frontend (10-04) Pydantic'ning standart 422 ro'yxatini `validation_error` ga o'zi xaritalaydi — server bunga alohida handler qo'shmagan (reja qadamlariga aynan rioya).

## Self-Check: PASSED

- Yaratilgan 4 fayl mavjud: `public.py`, `test_demo_request_contract.py`, `test_demo_request.py`, `10-01-SUMMARY.md`
- To'rtala commit tarixda: 3756af7, bda237f, 59ef89c, 8aac1d9
- `git diff` toza (sabotajlar to'liq qaytarilgan), STATE.md/ROADMAP.md TEGILMAGAN
