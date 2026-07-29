---
phase: 01-poydevor-va-tenant-xavfsizligi
plan: 03
subsystem: core
tags:
  [
    sbozor-core,
    money,
    timezone,
    phone,
    enums,
    jwt,
    argon2,
    tenancy,
    structlog,
    tdd,
  ]

# Dependency graph
requires:
  - "01-01 (packages/sbozor-core paketi, editable install, tests/ infratuzilmasi)"
provides:
  - "sbozor_core.enums — Role (5 panel roli), Locale (3 til), AuditAction, AuditSource, ActorKind"
  - "sbozor_core.money — Soum tipi, MAX_SAFE_SOUM, assert_safe_soum, format_soum"
  - "sbozor_core.timeutil — MARKET_TZ, now_tz(), business_date()"
  - "sbozor_core.phone — normalize_phone() (E.164), InvalidPhoneError"
  - "sbozor_core.security — hash_password/verify_password/dummy_verify, TokenClaims, encode_access/encode_refresh/decode_token"
  - "sbozor_core.db — make_engine(), make_sessionmaker()"
  - "sbozor_core.tenancy — SET_TENANT_CONTEXT, set_tenant_context(), TenantScopedRepository, GUC nomlari"
  - "sbozor_core.logging — configure_logging(), bind_request_context(), clear_request_context(), censor_secrets"
  - "sbozor_core.schema_contract — GLOBAL_TABLES, FINANCIAL_TABLES, AUDITED_TABLES reyestrlari"
  - "tests/unit/ — 145 ta bazasiz test (tez qaytish halqasi)"
affects:
  - "01-04 (Alembic + RLS: GUC nomlari, schema_contract reyestrlari, business_date semantikasi)"
  - "01-05 (audit: AuditAction/AuditSource/ActorKind qiymatlari, ActorKind GUC'i)"
  - "01-06 (auth API: security.py butunlay, phone.py login identifikatori uchun)"
  - "01-07..01-10 (money/timeutil formatlash va hisobot chegaralari)"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pul — faqat butun `int` so'm; `float`, `bool` va `Decimal` tipda rad etiladi (TypeError)"
    - "Biznes-kun kod qatlamida FAQAT o'qish/taqqoslash uchun; yozishda DB generated column"
    - "JWT dekodlashda algoritm allowlist'i LITERAL yoziladi — token header'idan hech qachon olinmaydi"
    - "Tenant konteksti `set_config(..., true)` bilan va faqat ochiq tranzaksiyada"
    - "Sir filtri log protsessori sifatida — kalit NOMI bo'yicha, qiymat ichidan qidirmasdan"
    - "Chegara normalizatsiyasi (telefon) kutubxona bilan, regex bilan emas"

key-files:
  created:
    - packages/sbozor-core/sbozor_core/enums.py
    - packages/sbozor-core/sbozor_core/money.py
    - packages/sbozor-core/sbozor_core/timeutil.py
    - packages/sbozor-core/sbozor_core/phone.py
    - packages/sbozor-core/sbozor_core/schema_contract.py
    - packages/sbozor-core/sbozor_core/security.py
    - packages/sbozor-core/sbozor_core/db.py
    - packages/sbozor-core/sbozor_core/tenancy.py
    - packages/sbozor-core/sbozor_core/logging.py
    - tests/unit/__init__.py
    - tests/unit/test_money.py
    - tests/unit/test_timeutil.py
    - tests/unit/test_phone.py
    - tests/unit/test_enums.py
    - tests/unit/test_jwt.py
    - tests/unit/test_password.py
    - tests/unit/test_tenancy.py
    - tests/unit/test_logging.py
  modified:
    - packages/sbozor-core/sbozor_core/__init__.py

key-decisions:
  - "`AuditAction` qiymatlari KICHIK harfda (`insert`/`update`/`delete`) — DB trigger `lower(TG_OP)` yozadi, ikkalasi bir xil hisobotga tushadi"
  - "`decode_token` da `algorithms=[\"HS256\"]` literal ro'yxat (konstanta orqali EMAS) — xavfsizlik uchun kritik satr o'z-o'zini tushuntirishi kerak; moslik testlar bilan qulflangan"
  - "`TokenClaims` ga `family_id` maydoni qo'shildi — `fam` claim'isiz refresh reuse aniqlanganda oilani bekor qilib bo'lmasdi"
  - "`db.py` global `SessionLocal` yaratmaydi — engine `lifespan` da quriladi va yopiladi"
  - "`format_soum` manfiy qiymatni qabul qiladi (`assert_safe_soum` esa yo'q) — `charge_adjustments` chegirmasi ekranda minus bilan ko'rsatiladi"
  - "`AUDITED_TABLES` 1-fazada faqat `user_market_roles` — reyestr KUTILGAN emas, AMALDAGI trigger qamrovini bildiradi"
  - "`type Soum = int` (PEP 695) — `TypeAlias` shakli py313 target'da ruff UP040 beradi"

patterns-established:
  - "Pattern: har bir primitiv aniq I/O kontrakti + chegara testi bilan yoziladi (79 -> 145 test)"
  - "Pattern: xavfsizlik ogohlantirishlari xato bilan almashtiriladi — qisqa JWT siri warning emas, `InvalidKeyError`"
  - "Pattern: 'jimgina noto'g'ri' holatlar (naive datetime, filtrsiz select, market_id'siz model) exception ko'taradi"
  - "Pattern: unit testlar `tests/unit` da bazasiz — `tests/tenancy` konteyner talab qiladi; ikki halqa ajratilgan"

requirements-completed: [FOUND-05]

# Metrics
duration: 30min
completed: 2026-07-29
---

# Phase 1 Plan 03: sbozor-core infra primitivlari Summary

**`sbozor_core` ning to'qqizta biznes-logikasiz moduli — butun so'm, Asia/Tashkent biznes-kuni, E.164 telefon, Argon2id parol va qattiqlashtirilgan JWT, tenant GUC helperi hamda sir-filtrli JSON logging — 145 ta bazasiz test bilan qulflangan.**

## Performance

- **Duration:** ~30 min
- **Started:** 2026-07-29T04:54:43Z
- **Completed:** 2026-07-29T05:24:32Z
- **Tasks:** 3/3
- **Files created:** 18 (modifikatsiya: 1)
- **Tests:** 145 unit + 5 tenancy meta = 150, hammasi yashil

## Accomplishments

- **Pul endi strukturaviy ravishda butun son.** `assert_safe_soum` kasrli tipni ham, `bool` ni ham (u `int` ning bolasi — oddiy `isinstance` tekshiruvi uni o'tkazib yuborardi) `TypeError` bilan rad etadi. `MAX_SAFE_SOUM` JSON chegarasini qo'riqlaydi. `money.py` da `float` so'zi faqat ikki joyda: modul docstringidagi TAQIQ va uni rad etuvchi `isinstance` satri.
- **Biznes-kun chegarasi raqam bilan qulflandi.** RESEARCH Pattern 7 dagi o'lchangan jadval test bo'lib ko'chdi: `19:30Z → 2026-11-06`, `18:30Z → 2026-11-05`. Alohida regressiya testi naive `moment.date()` aynan shu holatda **boshqa** javob berishini ko'rsatadi — ya'ni test o'zi nimani qo'riqlayotganini isbotlaydi. Naive datetime `ValueError` beradi.
- **JWT hujum yuzasi yopildi va isbotlandi.** `alg=none` (qo'lda qurilgan imzosiz token), HS512 bilan **bir xil sir** ostida imzolangan token, access↔refresh almashtirish, buzilgan imzo, boshqa sir, muddati o'tgan token, noto'g'ri `iss`/`aud` va oltita majburiy claim'ning har biri alohida — 32 ta test. 31 baytlik sir `encode` da ham, `decode` da ham `InvalidKeyError` (ogohlantirish emas).
- **Parol parametrlari kelajakka tayyor.** `verify_and_update` zaif parametrli (`m=8,t=1,p=1`) legacy hash bilan sinaldi: `(True, yangi_hash)` qaytdi, ya'ni parametrlarni yillar davomida oshirib borish yo'li ochiq va u **test bilan** tasdiqlangan, taxmin emas.
- **Tenant konteksti darvozasi ishlaydi.** `set_tenant_context` tranzaksiyasiz sessiya bilan chaqirilganda `RuntimeError` ko'taradi — va bu bazasiz test bilan tekshirilgan (engine dangasa, ulanish ochilmaydi). `TenantScopedRepository.scoped` `market_id` ustuni bo'lmagan modelni ham, entity'siz `select(func.count())` ni ham `TypeError` bilan rad etadi: filtrsiz jimgina qaytish imkonsiz.
- **Sirlar log'dan chiqmaydi.** `censor_secrets` uchdan-uchi tekshirildi: `logger.info("login_attempt", password=..., phone=...)` chiqishi JSON bo'lib, `password` maydoni `***`, `phone` esa o'zgarishsiz, va satrda `request_id`/`user_id`/`market_id` avtomatik bor.

## Task Commits

1. **Task 1: Pul, biznes-kun, telefon, enum'lar va sxema reyestri (TDD)**
   - `0095faf` (test) — RED: 70 ta test, `ModuleNotFoundError` bilan yiqiladi
   - `099c3fa` (feat) — GREEN: 5 modul + `test_enums.py`, 79/79 yashil
2. **Task 2: Xavfsizlik primitivlari — Argon2id parol va JWT (TDD)**
   - `0034cfb` (test) — RED: 42 ta test, `ModuleNotFoundError`
   - `dee3ba6` (feat) — GREEN: `security.py`, 121/121 yashil
3. **Task 3: DB engine, tenant konteksti helperi va structured logging**
   - `d2c848f` (feat) — `db.py`, `tenancy.py`, `logging.py` + 24 ta offline test, 145/145 yashil

## Files Created/Modified

**Primitivlar (`packages/sbozor-core/sbozor_core/`)**

- `enums.py` — `Role` (aynan 5 panel roli; `vendor` ATAYIN yo'q), `Locale` (`uz-Latn`/`uz-Cyrl`/`ru`), `AuditAction` (13 qiymat, kichik harfda), `AuditSource`, `ActorKind`
- `money.py` — `type Soum = int`, `MAX_SAFE_SOUM`, `assert_safe_soum`, `format_soum` (NBSP guruh ajratgichi, uch tilda birlik)
- `timeutil.py` — `MARKET_TZ`, `now_tz()`, `business_date()`; docstringda "yozish yo'lida ishlatilmaydi" ogohlantirishi
- `phone.py` — `normalize_phone()` (`phonenumbers`, `is_valid_number` bilan), `InvalidPhoneError(ValueError)`, `DEFAULT_REGION`
- `security.py` — Argon2id (`hash_password`/`verify_password`/`dummy_verify`) + JWT (`encode_access`/`encode_refresh`/`decode_token`, `TokenClaims`, `ALG`, `MIN_SECRET_BYTES`, `REQUIRED_CLAIMS`)
- `db.py` — `make_engine()`, `make_sessionmaker()`; global engine YO'Q
- `tenancy.py` — `SET_TENANT_CONTEXT`, `set_tenant_context()`, `TenantScopedRepository`, `MARKET_ID_GUC`/`ACTOR_ID_GUC`/`REQUEST_ID_GUC`/`ACTOR_KIND_GUC`, `TENANT_GUCS`
- `logging.py` — `configure_logging()`, `bind_request_context()`, `clear_request_context()`, `censor_secrets`, `SENSITIVE_KEYS`, `CENSORED`
- `schema_contract.py` — `GLOBAL_TABLES` (`users`/`markets`/`alembic_version`), `FINANCIAL_TABLES` (5 jadval), `AUDITED_TABLES` (`user_market_roles`)
- `__init__.py` — docstring amaldagi modul ro'yxatiga yangilandi (eskisi "01-03 da qo'shiladi" deb turardi)

**Testlar (`tests/unit/`)** — 145 ta, hammasi bazasiz

| Fayl | Testlar | Nima qulflangan |
| ---- | ------- | --------------- |
| `test_money.py` | 32 | butun son invarianti, chegara, uch tildagi formatlash |
| `test_timeutil.py` | 18 | yarim tun chegarasi, naive rad etilishi, yil chegarasi |
| `test_phone.py` | 20 | 8 xil kirish shakli -> bitta E.164, 8 xil yaroqsiz kirish |
| `test_jwt.py` | 32 | T-01-12, T-01-13, T-01-14 + standart claim tekshiruvlari |
| `test_password.py` | 10 | argon2id, tuz, qayta hash (T-01-18), vaqt tekisligi (T-01-15) |
| `test_tenancy.py` | 11 | GUC matni, tranzaksiya darvozasi (T-01-17), `scoped` predikati |
| `test_logging.py` | 13 | sir filtri (T-01-16), JSON chiqish, kontekst tozalash |
| `test_enums.py` | 9 | qiymat kontrakti + frontend `routing.ts` bilan drift darvozasi |

## Decisions Made

- **`AuditAction` qiymatlari kichik harfda.** RESEARCH Code Example §5 dagi trigger `lower(TG_OP)` yozadi. Agar ilova `INSERT` yozsa, bitta hisobotda `insert` va `INSERT` ikki xil qiymat bo'lib ajralardi.
- **Dekodlash allowlist'i literal.** `algorithms=["HS256"]` — konstanta orqali emas. Xavfsizlik uchun kritik satrni o'qiyotgan odam nimaga ruxsat berilayotganini boshqa joyga qaramasdan ko'rishi kerak. `ALG` bilan mosligi `test_algorithm_constant_is_hs256` va HS512/`alg=none` testlari bilan qulflangan (divergensiya fail-closed: barcha tokenlar rad etiladi, birinchi test ishlashida ko'rinadi).
- **`schema_contract` dagi `markets` — "global" emas, MAXSUS HOLAT.** Izoh faylda: uning policy'si `market_id = ...` emas, `id = ...` bo'ladi (Open Question 4), shuning uchun meta-test uni umumiy tsikldan chiqaradi.
- **`AUDITED_TABLES` KUTILGAN emas, AMALDAGI qamrovni bildiradi.** U `FINANCIAL_TABLES` bilan atayin birlashtirilmagan: meta-test ikki manbani `pg_trigger` bilan solishtiradi, ya'ni jadval tug'ilgan kuni trigger unutilsa darvoza qizaradi.
- **`censor_secrets` faqat KALIT nomiga qaraydi.** Qiymat ichidan sir "topishga" urinish yolg'on-musbat (JSON'ga o'xshagan matn) va yolg'on-manfiy beradi. Qoida oddiy: sirni nomlangan kalit sifatida uzating.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Tahdid reyestridagi ikki mitigatsiya avtomatik tekshiruvsiz qolardi**

- **Found during:** Task 3 (`<verify>` faqat import + mypy + ruff edi)
- **Issue:** `<threat_model>` da `T-01-16` (sir filtri) va `T-01-17` (tenant GUC sizishi) `mitigate` dispozitsiyasi bilan turibdi, lekin rejada ular uchun test yo'q edi — ya'ni kod yozilgan, isbot yo'q. Xuddi shunday, "`Role` da aynan 5 a'zo", "`Locale` frontend bilan mos" qabul mezonlari ham faqat qo'lda grep bilan tekshirilardi.
- **Fix:** Uchta qo'shimcha test fayli: `tests/unit/test_tenancy.py` (11), `tests/unit/test_logging.py` (13), `tests/unit/test_enums.py` (9). Hammasi **bazasiz** — `create_async_engine` dangasa, shuning uchun tranzaksiya darvozasi ham ulanmasdan sinaladi. `test_enums.py` `frontend/src/i18n/routing.ts` ni o'qib backend↔frontend locale drift'ini qulflaydi.
- **Files modified:** `tests/unit/test_tenancy.py`, `tests/unit/test_logging.py`, `tests/unit/test_enums.py` (yangi)
- **Verification:** 33 ta yangi test yashil; sabotaj tekshirildi — `set_tenant_context` dagi `in_transaction()` shartini olib tashlasa test yiqiladi
- **Committed in:** `099c3fa`, `d2c848f`

**2. [Rule 2 - Missing Critical] `TokenClaims` da `fam` claim'i o'qilmasdi**

- **Found during:** Task 2
- **Issue:** Reja `encode_refresh` ga `fam=str(family_id)` yozishni buyuradi (reuse aniqlanganda butun oilani bekor qilish uchun), lekin `TokenClaims` maydonlari ro'yxatida `family_id` yo'q edi. Natijada token oilasi yoziladi, lekin dekodlashda **qaytarib olib bo'lmaydi** — ya'ni Pattern 3 dagi reuse-detection 01-06 da amalga oshmasdi.
- **Fix:** `TokenClaims` ga `family_id: str | None = None` (standart qiymat bilan, shuning uchun e'lon qilingan kontrakt buzilmaydi). Access tokenda `None` bo'lib qaytadi.
- **Files modified:** `packages/sbozor-core/sbozor_core/security.py`
- **Verification:** `test_refresh_token_round_trip` — `claims.family_id == str(FAMILY_ID)`
- **Committed in:** `dee3ba6`

**3. [Rule 1 - Bug] `SET LOCAL` izohi faza grep-darvozasini yiqitardi**

- **Found during:** Task 3 yakuniy tekshiruvi
- **Issue:** Reja verifikatsiyasi: `grep -rn "SET LOCAL" packages/` → natija yo'q. Mening `tenancy.py` docstringimda "nega bu shakl ishlatilmaydi" izohi aynan shu satrni o'z ichiga olardi → yolg'on-musbat. (01-01 rejasida ham xuddi shu sinf xatosi bo'lgan — deviatsiya #7.)
- **Fix:** Docstring ma'nosini saqlagan holda, qo'shni literal so'zsiz qayta yozildi (`Postgres'ning `SET` buyrug'i (uning tranzaksiya-lokal varianti ham) bind parametr QABUL QILMAYDI`). Literal shakl `tests/unit/test_tenancy.py` da qoldi — u yerda grep darvozasi yo'q va u yerda uning o'rni.
- **Files modified:** `packages/sbozor-core/sbozor_core/tenancy.py`
- **Verification:** `grep -rn "SET LOCAL" packages/` → bo'sh; `test_uses_set_config_not_set_local` yashil
- **Committed in:** `d2c848f`

**4. [Rule 1 - Bug] `algorithms=[ALG]` must-have naqshiga tushmasdi**

- **Found during:** Task 2 yakuniy tekshiruvi
- **Issue:** Dastlab `algorithms=[ALG]` yozilgan edi (bitta haqiqat manbai). Reja `must_haves.key_links` esa `algorithms=["HS256"]` literalini grep qiladi, qabul mezoni ham shuni talab qiladi.
- **Fix:** Dekodlash satri literal shaklga o'tkazildi. Bu **kod sifati jihatidan ham to'g'riroq**: xavfsizlik uchun kritik satrda indirection o'qishni qiyinlashtiradi. `ALG` chiqarish yo'lida qoldi; ikkalasining mosligi test bilan qulflangan va divergensiya fail-closed (barcha tokenlar rad etiladi).
- **Files modified:** `packages/sbozor-core/sbozor_core/security.py`
- **Verification:** `grep -n 'algorithms=\["HS256"\]' ...` → topildi; 32 ta JWT testi yashil
- **Committed in:** `dee3ba6`

**5. [Rule 3 - Blocking] ruff `S105` audit hodisa nomlarini parol deb bildi**

- **Found during:** Task 1 (`ruff check`)
- **Issue:** `AuditAction.PASSWORD_RESET = "password_reset"` va `PASSWORD_CHANGED` — `S105 Possible hardcoded password`. Bular audit hodisa nomlari, sir emas.
- **Fix:** Ikki satrga `# noqa: S105` + sababni tushuntiruvchi izoh (per-file-ignore emas — istisno tor va ko'rinadigan qolsin).
- **Files modified:** `packages/sbozor-core/sbozor_core/enums.py`
- **Verification:** `ruff check .` → `All checks passed!`
- **Committed in:** `099c3fa`

**6. [Rule 3 - Blocking] `InsecureKeyLengthWarning` `jwt.exceptions` da emas**

- **Found during:** Task 2 (test to'plami yig'ilishda yiqildi)
- **Issue:** HS512 forging testi PyJWT ogohlantirishi chiqarardi. `@pytest.mark.filterwarnings("ignore::jwt.exceptions.InsecureKeyLengthWarning")` esa `AttributeError: module 'jwt.exceptions' has no attribute ...` bilan **butun to'plamni** yiqitdi — klass `jwt.warnings` modulida.
- **Fix:** Marker `jwt.warnings.InsecureKeyLengthWarning` ga tuzatildi; nega 48 baytlik sir ataylab qoldirilgani izohda yozildi.
- **Files modified:** `tests/unit/test_jwt.py`
- **Verification:** `pytest tests/unit -q` → ogohlantirishsiz yashil
- **Committed in:** `dee3ba6`

**7. [Rule 2 - Missing Critical] `make_engine` chaqiruvchi `pool_pre_ping` bersa yiqilardi**

- **Found during:** Task 3
- **Issue:** Rejadagi `create_async_engine(url, pool_pre_ping=True, **kw)` shakli chaqiruvchi `pool_pre_ping` ni `kw` da uzatsa `TypeError: got multiple values` beradi.
- **Fix:** `kw.setdefault("pool_pre_ping", True)` — standart qiymat saqlanadi, bekor qilish mumkin.
- **Files modified:** `packages/sbozor-core/sbozor_core/db.py`
- **Committed in:** `d2c848f`

**8. [Rule 2 - Missing Critical] Log kontekstini tozalash yo'li yo'q edi**

- **Found during:** Task 3
- **Issue:** Reja faqat `bind_request_context` ni ko'rsatadi. Tozalashsiz, qayta ishlatilgan vazifada oldingi so'rovning `market_id` si keyingi log satrlarida qolib ketishi mumkin — multi-tenant audit hikoyasida bu jimgina yolg'on dalil.
- **Fix:** `clear_request_context()` qo'shildi va `bind_request_context` docstringida "har so'rov boshida chaqiring" deb yozildi.
- **Files modified:** `packages/sbozor-core/sbozor_core/logging.py`
- **Verification:** `test_clear_request_context_removes_bound_values`
- **Committed in:** `d2c848f`

### Kichik moslashtirishlar (xato emas, tanlov)

- **`type Soum = int` (PEP 695)** — reja `Soum: TypeAlias = int` deydi, lekin `target-version = "py313"` da ruff `UP040` bilan uni PEP 695 shakliga majburlaydi. Semantikasi bir xil.
- **`format_soum` manfiy qiymatni qabul qiladi**, `assert_safe_soum` esa yo'q. `charge_adjustments` chegirmasi ekranda minus bilan ko'rsatiladi; kattalik chegarasi baribir tekshiriladi.
- **`REQUIRED_CLAIMS` da `typ` yo'q** — reja bergan ro'yxat aynan saqlandi. Tur tekshiruvi alohida va aniqroq xato xabari bilan (`wrong token type: kutilgan ... kelgani ...`) bajariladi.

---

**Total deviations:** 8 auto-fixed — 2× Rule 1 (grep darvozasi va must-have naqshi), 4× Rule 2 (tahdid testlari, `family_id`, `pool_pre_ping`, `clear_request_context`), 2× Rule 3 (ruff S105, noto'g'ri warning moduli).
**Impact on plan:** Scope creep yo'q — barcha o'zgarishlar rejaning o'z qabul mezonlari va tahdid reyestri doirasida. Uchtasi (#1, #2, #8) isbotsiz qolgan xavfsizlik da'volarini yopdi. Rejaning barcha qabul mezonlari o'zgarishsiz bajarildi.

## Issues Encountered

- **`.env` fayli yo'q** (worktree bilan yo'qolgan, gitignore'da). `docker compose --profile test run` har chaqiruvda "variable is not set" ogohlantirishlari beradi, lekin `tests` profili testcontainers ishlatgani uchun ularning hech biri kerak emas — testlar ta'sirlanmadi.
- **NBSP belgisi manba faylida.** Guruh ajratgichi (U+00A0) fayl ichida ko'rinmas belgi bo'lib qolardi. Ikkala joyda ham `chr(0x00A0)` shakliga o'tkazildi — kod o'qiganda ham, `git diff` da ham aniq ko'rinadi.
- **ruff isort `sbozor_core` ni uchinchi tomon deb biladi** (`known-first-party` sozlanmagan). Import bloklari shu qoidaga moslashtirildi; ildiz `pyproject.toml` ga tegilmadi, chunki u bu rejaning qamrovida emas.

## Known Stubs

Yo'q. Bu rejada yozilgan har bir funksiya to'liq ishlaydi va test bilan qoplangan.

Atayin **keyingi rejalarga** qoldirilgan (stub emas, hali navbati kelmagan):

- `sbozor_core.models` — ORM modellari 01-04 da (`schema_contract` reyestrlari ularni kutmoqda).
- `FINANCIAL_TABLES` dagi beshta jadvalning hech biri hali mavjud emas (2- va 6-fazalar). Reyestr "jadval mavjud bo'lsa — konstraytlar ham bo'lishi shart" shaklida ishlatiladi.
- `TenantScopedRepository` dan meros oluvchi konkret repozitoriylar — 01-06 va keyin.
- `configure_logging` stdlib logging bilan to'liq birlashtirilmagan (uvicorn satrlari JSON emas, oddiy matn). Bu ataylab: 12-faktor uslubida ikkala oqim ham stdout'ga tushadi va konteyner logi ularni yig'adi. To'liq `ProcessorFormatter` integratsiyasi kerak bo'lsa — 8-faza (mustahkamlash).

## Threat Flags

Yo'q — bu rejada `<threat_model>` da qayd etilmagan yangi xavfsizlik yuzasi paydo bo'lmadi. Reyestrdagi 8 ta dispozitsiya bajarildi va **har biri test bilan** qoplandi:

| Threat  | Qanday yopildi | Tekshiruv |
| ------- | -------------- | --------- |
| T-01-12 | `algorithms=["HS256"]` literal allowlist; algoritm header'dan olinmaydi | `test_alg_none_token_is_rejected`, `test_token_signed_with_other_algorithm_is_rejected` |
| T-01-13 | `typ` claim'i majburiy; `decode_token(expected_type=...)` mos kelmasa rad etadi; refresh'da `roles`/`mid` yo'q | `test_access_token_rejected_when_refresh_expected`, `test_refresh_does_not_carry_roles_or_market` |
| T-01-14 | `_assert_secret_length` (encode) + `enforce_minimum_key_length=True` (decode) | `test_encode_access_rejects_short_secret`, `test_decode_rejects_short_secret` |
| T-01-15 | `dummy_verify()` import paytida hisoblangan hash'ga qarshi to'liq Argon2 ishi bajaradi | `test_dummy_verify_costs_measurable_time`, `test_dummy_verify_and_real_verify_are_same_order_of_magnitude` |
| T-01-16 | `censor_secrets` protsessori 16 ta kalitni maskalaydi, renderergacha ishlaydi | `test_censor_secrets_masks_required_keys`, `test_log_line_is_json_with_context_and_censored_secret` |
| T-01-17 | `set_tenant_context` tranzaksiyasiz `RuntimeError`; `None` → `""` → policy `NULLIF` bilan fail-closed | `test_set_tenant_context_requires_open_transaction` |
| T-01-18 | `verify_and_update` eskirgan parametrli hash uchun yangisini qaytaradi | `test_verify_password_rehashes_outdated_parameters` |
| T-01-19 | `assert_safe_soum` `float`/`bool`/`Decimal` ni rad etadi, `MAX_SAFE_SOUM` chegarasi | `test_assert_safe_soum_rejects_non_int_types`, `test_assert_safe_soum_rejects_bool` |

## User Setup Required

Yo'q — tashqi servis konfiguratsiyasi talab qilinmaydi. Testlar `docker compose --profile test run --rm tests pytest tests/unit -q` bilan `.env` siz ham ishlaydi.

## Next Phase Readiness

**Tayyor:**

- **01-04 (Alembic + RLS):** GUC nomlari (`sbozor_core.tenancy.MARKET_ID_GUC` va boshqalar) va policy predikati uchun `NULLIF` naqshi hujjatlashtirilgan; `schema_contract` reyestrlari meta-testlar uchun kutmoqda; `business_date` semantikasi kod tomonda test bilan belgilangan, endi generated column bilan solishtirish mumkin.
- **01-05 (audit):** `AuditAction`/`AuditSource`/`ActorKind` qiymatlari trigger SQL'idagi literal qiymatlar bilan **aynan** mos qilib yozilgan (`lower(TG_OP)`, `'db_trigger'`, `'user'`).
- **01-06 (auth API):** `security.py` to'liq — parol, ikkala token turi, `family_id` bilan reuse-detect asosi; `phone.normalize_phone` login identifikatori uchun; `settings.py` dagi `jwt_secret`/`jwt_issuer`/`jwt_audience`/TTL qiymatlari to'g'ridan-to'g'ri `encode_*` argumentlariga mos keladi.
- **01-07+:** `format_soum` va `Locale` frontend bilan bir xil kodlarni ishlatadi (drift testi bor).

**Ochiq e'tibor nuqtalari:**

- `TenantScopedRepository.scoped()` `stmt.column_descriptions[0]` ga tayanadi — ya'ni JOIN'li so'rovda **birinchi** entity'ga predikat qo'yadi. 01-04 da ko'p jadvalli so'rovlar paydo bo'lganda bu xulq-atvor qayta ko'rib chiqilishi kerak (ehtimol har bir tenant-scoped entity uchun alohida predikat).
- `dummy_verify()` uchun hash **import paytida** hisoblanadi (~100 ms). Bu ataylab (birinchi so'rov sekin bo'lmasligi uchun), lekin `sbozor_core.security` ni import qiladigan har bir jarayon shu narxni to'laydi — CLI vositalarida seziladi.
- `censor_secrets` faqat yuqori darajadagi kalitlarni ko'radi. Ichma-ich `dict` (masalan butun `headers` obyekti bitta qiymat sifatida) maskalanmaydi. Agar middleware sarlavhalarni to'plam sifatida yozadigan bo'lsa, 01-06 da rekursiv variantga o'tish kerak.
