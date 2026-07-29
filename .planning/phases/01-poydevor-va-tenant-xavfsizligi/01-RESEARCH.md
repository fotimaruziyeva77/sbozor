# Phase 1: Poydevor va tenant xavfsizligi — Research

**Researched:** 2026-07-29
**Domain:** Multi-tenant SaaS poydevori — Postgres RLS tenant izolyatsiyasi, JWT/RBAC auth, o'zgarmas audit jurnali, biznes-kun/pul tiplari, 3 tilli i18n skaffolding, monorepo + Compose skeleti
**Confidence:** HIGH (kritik DB xulq-atvorlari jonli `postgres:18.4-trixie` konteynerida empirik tekshirildi; kutubxona versiyalari registrylardan tasdiqlandi)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Kirish va sessiya siyosati**
- **D-01:** Login identifikatori — **telefon raqami** (+998, E.164 normalizatsiya `phonenumbers` bilan) + parol. Email/username ishlatilmaydi. Telefon `users` jadvalida unique.
- **D-02:** Parol tiklash — **admin orqali**: bozor admini / platforma admini vaqtinchalik parol beradi, foydalanuvchi birinchi kirishda majburiy almashtiradi. Har tiklash auditda. SMS/email/bot-kod oqimi yo'q (MVP).
- **D-03:** Sessiya — **30 kun sliding refresh** (har faol ishlatilganda uzayadi); access token qisqa (stack: 15 daq, httpOnly cookie'da refresh). Kassir telefonida amalda qayta login so'ralmaydi.
- **D-04:** Foydalanuvchi yaratish — **ikki bosqichli**: platforma admini bozor va uning admin/direktorini yaratadi; bozor admini o'z bozori xodimlarini (kassir, nazoratchi) o'zi yaratadi. O'z-o'zidan ro'yxatdan o'tish yo'q. Foydalanuvchi boshqaruv UI (yaratish, bloklash, parol tiklash) 1-fazada.

**Rol va bozor biriktirish modeli**
- **D-05:** Bitta foydalanuvchi = **bitta bozor + rollar TO'PLAMI** (masalan, bozor admini + kassir bir odamda). Sxema kelajakda ko'p-bozorga kengayadigan qilib quriladi (user↔market↔role strukturasi), lekin MVP UI faqat bitta bozor biriktiradi.
- **D-06:** Platforma admini — **bozor tanlab kiradi** (kontekst tanlash): global bozorlar ro'yxatini ko'radi, ichiga kirganda RLS o'sha bozorga o'rnatiladi. **RLS bypass yo'li yo'q**; harakatlari auditda "platforma admini X bozorida" sifatida yoziladi.
- **D-07:** Direktor — **faqat ko'rish + nizo qarori**: hisobotlar, dayjest, jonli kamera; nomuvofiqlik case qarori (7-faza). Rasta/tarif/xodim o'zgartirmaydi. Rol-huquq matritsasi kodda qat'iy (sozlanadigan permission tizimi emas).
- **D-08:** Bloklash — **darhol kuchga kiradi**: har so'rovda foydalanuvchi holati tekshiriladi (Valkey kesh bilan arzon qilinadi). Bloklangan kassir bir soniya ham to'lov kirita olmaydi.

**Audit jurnali qamrovi**
- **D-09:** Qamrov — **barcha moliyaviy/ma'muriy o'zgarishlar + shaxsiy ma'lumot O'QISHLARI ham** (kim qaysi sotuvchining qarzini/ma'lumotini ko'rdi). O'zR shaxsiy ma'lumotlar qonuni ostida himoya; davlat bosqichiga tayyor. Texnik/pipeline yozuvlari (snapshot olish va h.k.) audit jurnaliga kirmaydi.
- **D-10:** Mexanizm — **moliyaviy jadvallarda DB-trigger** (`daily_charges`, `charge_adjustments`, `payments`, `tariffs`, `stall_assignments` — hech qanday kod yo'li chetlab o'tolmaydi), qolgan jadvallarda app-qatlam. Audit jadvalidan app DB-roliga UPDATE/DELETE huquqi umuman berilmaydi (append-only).
- **D-11:** Ko'rish huquqi — **platforma admini + direktor + bozor admini**, har biri o'z bozori doirasida (RLS ostida). Auditni ko'rish ham audit-o'qish sifatida yoziladi.
- **D-12:** Ko'rish UI — **minimal filtrlanadigan ro'yxat 1-fazada** (kim / qachon / nima / eski→yangi). Muvaffaqiyat mezoni #3 ko'rsatib isbotlanadi; keyingi fazalarda boyitiladi.

**Til mexanikasi**
- **D-13:** Til tanlovi — **foydalanuvchi profilida (DB)** saqlanadi + cookie tez routing uchun. 7-fazada bot xabarlari ham shu manbadan oladi — bitta haqiqat manbai.
- **D-14:** Kirillcha — **build-time avto-transliteratsiya** uz-Latn → uz-Cyrl + qo'lda tuzatish lug'ati (е/э, ь, o'zlashma so'zlar). Tarjima yuzasi: uz-Latn (asosiy) + ru qo'lda, uz-Cyrl generatsiya.
- **D-15:** Standart til — **har doim uz-Latn** (brauzer Accept-Language'dan aniqlash YO'Q). Bir bosishda almashtiriladi va profilda qoladi.
- **D-16:** DB kontent (toifa/zona nomlari, rekvizitlar) — **bir tilda qoladi** (qanday kiritilgan bo'lsa shunday ko'rinadi). Faqat interfeys (UI chrome) 3 tilda. Multi-til kontent sxemasi qurilmaydi.

### Claude's Discretion
- JWT tuzilishi, token claim'lari, refresh-rotatsiya detali — stack hujjati doirasida (PyJWT, pwdlib[argon2]).
- RLS policy sintaksisi, `SET LOCAL` mexanikasi, TenantScopedRepository dizayni — tadqiqot tavsiyalari asosida.
- Audit jadval sxemasi (JSONB diff formati, indekslash) va o'qish-audit qayerda yozilishi (middleware vs endpoint).
- Dizayn-tizim komponentlari va login/shell UI detallari (Apple-uslub minimal, PROJECT.md cheklovi doirasida).
- Docker Compose skeleti, CI quvuri, migratsiya tartibi.

### Deferred Ideas (OUT OF SCOPE)
- Ko'p-bozorli foydalanuvchi (bir direktor ikki bozorda) — sxema tayyor bo'ladi, UI va bozor almashtirgich keyingi bosqichda (v2)
- Parol tiklash Telegram-bot orqali — bot 7-fazada kelgach ko'rib chiqilishi mumkin
- Maker-checker tarif tasdiqlash (direktor tasdiqlaydi) — v2 nomzodi
- Sozlanadigan permission tizimi (rol-huquq matritsasini bozor kesimida o'zgartirish) — MVP'da qat'iy kodda
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Tavsif (REQUIREMENTS.md) | Tadqiqot qanday qo'llab-quvvatlaydi |
|----|--------------------------|--------------------------------------|
| **FOUND-01** | Foydalanuvchi rolga mos kirish oladi — platforma admini, direktor, bozor admini, kassir, nazoratchi (RBAC); har rol faqat o'z bozori ma'lumotini ko'radi | Pattern 2 (Login bootstrap — `SECURITY DEFINER` funksiya orqali tenant-kontekstsiz kirish, empirik tasdiqlangan); Pattern 3 (JWT + rollar to'plami); Pitfall 3 (login RLS qopqoni); Code Example 3, 4 |
| **FOUND-02** | Tenant izolyatsiyasi: har jadvalda `market_id` + Postgres RLS; cross-tenant kirish avtomatik test bilan isbotlangan | Pattern 1 (ikki qatlamli RLS + composite FK); Pitfall 1 (`''::uuid` xatosi — empirik tasdiqlangan); Pitfall 2 (superuser/BYPASSRLS); Pattern 8 (tenancy meta-test + cross-tenant CI testi); Code Example 1, 2 |
| **FOUND-03** | Har moliyaviy/ma'muriy harakat audit jurnaliga yoziladi (kim, qachon, nima, eski→yangi); jurnal o'zgartirib bo'lmaydigan | Pattern 4 (DB-trigger audit — raw SQL ham ushlanadi, empirik tasdiqlangan); Pattern 5 (o'zgarmaslikning 4 qatlami); Pattern 6 (o'qish-audit); Code Example 5, 6 |
| **FOUND-04** | Interfeys 3 tilda (o'zbek-lotin asosiy, o'zbek-kirill, rus); til bir bosishda almashadi | Pattern 9 (next-intl 4.13 + Next 16 `proxy.ts`, custom prefixes); Pattern 10 (build-time transliteratsiya); Pitfall 8 (ICU platsholderlarini transliteratsiya qilmaslik); Code Example 7, 8 |
| **FOUND-05** | Biznes-kun Asia/Tashkent bo'yicha hisoblanadi (`business_date`); pul qiymatlari butun so'mda (BIGINT) | Pattern 7 (`GENERATED ALWAYS AS ... STORED` business_date — `timezone(text,timestamptz)` IMMUTABLE ekani tasdiqlangan); Pitfall 6 (UTC sana chegarasi); Pitfall 7 (JS `Number` chegarasi); Code Example 9 |

**Qo'shimcha (mezon #5, 6-fazadan oldin talab qilinadi):** `UNIQUE(market_id, stall_id, business_date)` + `CHECK (amount_soum > 0)` + composite FK + append-only konstraytlar — Pattern 7, Code Example 9, empirik tasdiqlangan (`ON CONFLICT DO NOTHING` idempotentligi bilan birga).
</phase_requirements>

---

## Summary

Bu faza **texnologiya tanlash fazasi emas** — stek CLAUDE.md'da qat'iy qulflangan va tekshiruv shuni ko'rsatdiki, u **bugungi kunga to'liq mos** (PyPI/npm registrylardagi barcha versiyalar 2026-07-29 holatiga aynan mos keldi). Shuning uchun tadqiqot butunlay **implementatsiya mexanikasiga** yo'naltirildi va kritik xulq-atvorlar taxmin qilinmadi — jonli `postgres:18.4-trixie` konteynerida hamda haqiqiy `SQLAlchemy 2.0.51 + asyncpg 0.31.0` ulanish pulida **empirik o'lchandi**.

Uchta topilma rejaga bevosita ta'sir qiladi. **Birinchi:** `.planning/research/ARCHITECTURE.md` dagi namunaviy RLS policy — `USING (market_id = current_setting('app.market_id', true)::uuid)` — **ishlab turgan tizimda xato tashlaydi**. Sababi: `set_config(..., true)` tranzaksiya tugagach GUC'ni NULL'ga emas, **bo'sh satrga (`''`)** aylantiradi, va `''::uuid` → `invalid input syntax for type uuid`. Bu pool'dagi ulanish qayta ishlatilganda sodir bo'ladi, ya'ni **prod'da birinchi kundan**. Yagona to'g'ri shakl — `NULLIF(current_setting('app.market_id', true), '')::uuid`, u fail-closed (0 qator) beradi. **Ikkinchi:** `FORCE ROW LEVEL SECURITY` **superuser'ga umuman ta'sir qilmaydi** — o'lchov shuni ko'rsatdiki, FORCE qo'yilgandan keyin ham superuser hamma bozorni ko'raveradi. Ya'ni tenant izolyatsiyasi *policy sintaksisiga emas*, **ilova qaysi DB-rol bilan ulanishiga** bog'liq; meta-test buni ham tekshirishi shart. **Uchinchi:** eng katta arxitektura qopqoni — **login RLS ostida imkonsiz**. Foydalanuvchi telefon+parol yuborganda hali `market_id` ma'lum emas; agar `users`/`user_market_roles` tenant-policy ostida bo'lsa, so'rov 0 qator qaytaradi va **hech kim hech qachon kira olmaydi**. Yechim empirik tasdiqlandi: identifikatsiyani (global `users`) a'zolikdan (tenant-scoped `user_market_roles`) ajratish + login yo'lini `SECURITY DEFINER` funksiya orqali o'tkazish — bu `BYPASSRLS` rol talab qilmaydi va D-06 ning "bypass yo'li yo'q" shartini buzmaydi.

Audit tomonida DB-trigger yondashuvi (D-10) to'liq isbotlandi: **ORM'ni chetlab o'tgan xom SQL ham audit yozuvini hosil qildi**, `changed_keys` faqat haqiqatan o'zgargan ustunlarni berdi, no-op UPDATE esa shovqin yozmadi, va app-rol audit jadvalini na UPDATE, na DELETE qila oldi. `business_date` uchun `GENERATED ALWAYS AS ((created_at AT TIME ZONE 'Asia/Tashkent')::date) STORED` ishlaydi, chunki `timezone(text, timestamptz)` PG'da IMMUTABLE — bu kod-qatlamida sanani hisoblash zaruratini butunlay yo'q qiladi.

**Primary recommendation:** RLS'ni **`NULLIF(...)` shakli bilan**, **superuser bo'lmagan `sbozor_app` roli ostida**, **`set_config(..., true)` faqat ochiq tranzaksiya ichida** qo'llang; loginni `SECURITY DEFINER` funksiya orqali RLS'dan tashqariga chiqaring (jadval GRANT'isiz); auditni moliyaviy jadvallarda DB-trigger bilan yozing va uni 4 qatlamli o'zgarmaslik bilan qulflang; `business_date` ni generated column qiling; i18n'ni Next 16 `proxy.ts` + `localePrefix: {mode:'always', prefixes:{...}}` + `localeDetection:false` bilan 1-haftadayoq o'rnating.

---

## Architectural Responsibility Map

| Qobiliyat | Asosiy qatlam | Ikkinchi qatlam | Sabab |
|-----------|---------------|-----------------|-------|
| Tenant izolyatsiyasi (`market_id`) | **Database (RLS + composite FK)** | API (TenantScopedRepository) | RLS — oxirgi himoya to'ri; app-filtr unutilsa ham ma'lumot chiqmaydi. Ikkalasi ham kerak (PITFALLS.md P9) |
| Parol tekshirish (Argon2id) | **API (core-api)** | — | Hech qachon brauzerda; hash DB'da, tekshiruv serverda |
| Token chiqarish/tekshirish (JWT) | **API (core-api)** | — | HS256 sirri faqat serverda; frontend tokenni faqat tashiydi |
| Sessiya saqlash (refresh) | **Browser (httpOnly cookie)** | API (rotation/reuse-detect DB) | httpOnly → XSS o'qiy olmaydi; rotatsiya holati serverda |
| Rol-huquq matritsasi (RBAC) | **API (core-api)** | Frontend (UI yashirish) | Frontend faqat UX; qaror har doim serverda (D-07 kodda qat'iy) |
| Bozor konteksti tanlash (D-06) | **API (core-api)** | Frontend (picker UI) | `app.market_id` faqat serverda o'rnatiladi; klient uni tanlay olmaydi |
| Bloklangan foydalanuvchi (D-08) | **API + Valkey kesh** | Database (`users.is_active`) | Haqiqat DB'da; Valkey faqat tezlik uchun (TTL qisqa, invalidatsiya yozuvda) |
| Audit — moliyaviy jadvallar | **Database (trigger)** | — | D-10: hech qanday kod yo'li chetlab o'tolmaydi (xom SQL ham) |
| Audit — ma'muriy + o'qish (D-09) | **API (service layer)** | Database (append-only jadval) | SELECT uchun Postgres'da trigger yo'q — o'qish faqat app-qatlamida yoziladi |
| Audit o'zgarmasligi | **Database (REVOKE + trigger + RLS)** | — | Insider tahdidi app-qatlamidan yuqorida |
| `business_date` hisoblash | **Database (generated column)** | — | Bir marta, yozuv paytida; kod-qatlamida takrorlanmaydi (P8/Anti-Pattern 10) |
| Pul (BIGINT so'm) | **Database (`bigint` + CHECK)** | API (Python `int`) | `float` taqiqlangan; DB konstraytda |
| Locale routing (URL prefiks) | **Frontend Server (proxy.ts)** | — | Next 16 `proxy.ts` Node runtime; SSR sahifa locale bilan render qilinadi |
| Locale doimiyligi (D-13) | **Database (`users.locale`)** | Browser (cookie) | Bitta haqiqat manbai; cookie faqat tez routing uchun |
| uz-Cyrl matnlari (D-14) | **Build-time (script)** | — | Runtime transliteratsiya emas — deterministik, CI'da tekshiriladigan artefakt |
| Migratsiyalar (DDL) | **Alembic (one-shot job)** | — | App startup'da EMAS (ARCHITECTURE.md Internal Boundaries) |

---

## Project Constraints (from CLAUDE.md)

Quyidagilar **majburiy** va rejada qayta muhokama qilinmaydi. Bu faza uchun tegishlilari:

| Direktiva | Bu fazada nimani anglatadi |
|-----------|----------------------------|
| Python **3.13.x** barcha servislarda | `python:3.13-slim-trixie` bazasi (Alpine EMAS — `manylinux_2_28` g'ildiraklar uchun glibc kerak) |
| **`pwdlib[argon2]` 0.3.0** — `passlib` EMAS | passlib Python 3.13'da import bo'lmaydi (`crypt` moduli olib tashlangan) |
| **`PyJWT` 2.13.0** — `python-jose` EMAS | python-jose amalda qo'llab-quvvatlanmaydi |
| **`alembic-utils` 0.8.8** RLS policy autogenerate uchun | `CREATE POLICY` ni Alembic o'zi autogenerate qilmaydi |
| **`postgres:18.4-trixie`** — PG 19 EMAS | 19 hali `19beta2` |
| **Valkey 9.1.1** — Redis EMAS | Litsenziya pozitsiyasi (BSD-3) |
| **`proxy.ts`** — `middleware.ts` EMAS (Next 16) | Har bir onlayn next-intl darsligi endi noto'g'ri |
| **TypeScript 5.9.3** — 7.0.2 EMAS | Next 16 TS 7 ni faqat `experimental.useTypeScriptCli` ortida qo'llaydi |
| **Tailwind 4.3.3** CSS-first | `tailwind.config.js` YO'Q — `@theme {}` CSS ichida |
| **`float` pul uchun TAQIQLANGAN** | `BIGINT` so'm ↔ Python `int` |
| **Naive datetime TAQIQLANGAN** | `TIMESTAMPTZ` + `ZoneInfo` + `tzdata` paketi slim image'da |
| **Testlarda SQLite TAQIQLANGAN** | RLS SQLite'da yo'q → testcontainers + haqiqiy `postgres:18.4` |
| **`uv` per-service `pyproject.toml`** | Har servis o'z `uv.lock`i bilan (aiogram pin konflikti uchun) |
| **Servislar soni aynan 3** | Ortiqcha mikroservis bo'linmaydi |
| **GSD Workflow Enforcement** | Fayl o'zgartirish faqat GSD komandasi ichida |

---

## Standard Stack

Barcha versiyalar CLAUDE.md'da qulflangan va **2026-07-29 da registrylarda qayta tasdiqlandi**.

### Core (core-api — bu fazada faol)

| Kutubxona | Versiya | Maqsad | Nega standart |
|-----------|---------|--------|---------------|
| `fastapi` | **0.140.13** (2026-07-28) | HTTP qatlam | Cheklovda qat'iy. `lifespan=`, `Annotated[X, Depends(...)]` uslubi [VERIFIED: PyPI] |
| `uvicorn` | 0.51.0 | ASGI server | Compose'da `--workers 1` (scheduler dublikatining oldini oladi) [CITED: CLAUDE.md] |
| `pydantic` | **2.13.4** | DTO/validatsiya | `<2.14` — aiogram (7-faza) qattiq chegarasi [CITED: CLAUDE.md] |
| `pydantic-settings` | 2.14.2 | Typed env config | Bitta `Settings` klass, per-service `.env` |
| `sqlalchemy[asyncio]` | **2.0.51** (2026-06-15) | ORM + Core | `Mapped[]`/`mapped_column()`, `AsyncSession` [VERIFIED: PyPI] |
| `alembic` | **1.18.5** (2026-06-25) | Migratsiyalar | `alembic init -t async` shabloni mavjud [VERIFIED: CLI'da tekshirildi] |
| `alembic-utils` | **0.8.8** | `PGPolicy`, `PGTrigger`, `PGFunction`, `PGGrantTable` autogenerate | alembic 1.18.5 bilan **ishlashi empirik tasdiqlandi** [VERIFIED: import + `to_sql_statement_create()`] |
| `asyncpg` | **0.31.0** | Postgres drayver | `postgresql+asyncpg://` [VERIFIED: PyPI] |
| `PyJWT` | **2.13.0** (2026-05-21) | Access/refresh token | HS256; ≥32 baytli sir majburiy (pastga qarang) [VERIFIED: PyPI] |
| `pwdlib[argon2]` | **0.3.0** | Argon2id parol hash | `PasswordHash.recommended()` [VERIFIED: PyPI + rasmiy docs] |
| `phonenumbers` | **9.0.35** (2026-07-26) | +998 → E.164 normalizatsiya | D-01 identifikatori — chegarada normallashtirilmasa dublikat foydalanuvchi [VERIFIED: PyPI] |
| `structlog` | **26.1.0** | Structured JSON log | Har log satriga `market_id`, `user_id`, `request_id` [VERIFIED: PyPI] |
| `asgi-correlation-id` | 5.0.1 | `request_id` propagatsiyasi | Audit yozuvi bilan bir xil ID |
| `cryptography` | 49.0.0 | Fernet (3-fazada RTSP), 1-fazada faqat bog'liqlik | — |
| `tzdata` | 2026.3 | `ZoneInfo("Asia/Tashkent")` slim image'da | **Busiz `ZoneInfo` xato tashlaydi** |
| `redis[hiredis]` | 8.0.1 (core-api) | Valkey klient — bloklash keshi (D-08) | bot-service'da **7.4.1** (aiogram `<8`) — per-service lock shu uchun |
| `sentry-sdk[fastapi]` | 2.66.1 | Xato kuzatuvi | `before_send` bilan PII filtri |
| `postgres` | **18.4-trixie** | Baza | `uuidv7()` native [VERIFIED: konteynerda ishga tushirildi] |
| `valkey/valkey` | 9.1.1-alpine | Kesh/FSM | BSD-3 |

### Frontend (bu fazada faol)

| Kutubxona | Versiya | Maqsad | Izoh |
|-----------|---------|--------|------|
| `next` | **16.2.12** (2026-07-25) | App Router | `engines.node >= 20.9.0` [VERIFIED: npm] |
| `react` / `react-dom` | **19.2.8** | UI | [VERIFIED: npm] |
| `typescript` | **5.9.3** | Typing | npm'dagi `latest` = 7.0.2 — **pin qilinsin** [VERIFIED: npm] |
| `next-intl` | **4.13.4** (2026-07-23) | i18n | `peerDeps.next` `^16.0.0` ni o'z ichiga oladi [VERIFIED: npm] |
| `tailwindcss` + `@tailwindcss/postcss` | 4.3.3 | Styling | CSS-first |
| `@tanstack/react-query` | 5.101.4 | Server state | Login/refresh oqimi uchun |
| `zod` | 4.4.3 | Form validatsiya | |
| `react-hook-form` + `@hookform/resolvers` | 7.83.0 + 5.5.7 | Login/user formlari | |
| `@radix-ui/*`, `lucide-react`, `clsx`, `tailwind-merge`, `class-variance-authority`, `sonner` | CLAUDE.md bo'yicha | Dizayn-tizim asosi | |
| `date-fns` | 4.4.0 | Sana matematikasi | Ko'rsatish `next-intl` orqali |

### Dev / Test

| Vosita | Versiya | Maqsad |
|--------|---------|--------|
| `uv` | 0.11.33 | Per-service deps + `uv.lock` (`uv sync --frozen --no-dev` Dockerfile'da) |
| `ruff` | 0.16.0 | Lint + format (`E,F,I,UP,B,SIM,ASYNC,S`) |
| `mypy` | 2.3.0 | `strict = true` |
| `pytest` + `pytest-asyncio` + `pytest-cov` | 9.1.1 / 1.4.0 / 7.1.0 | `asyncio_mode = "auto"` |
| `testcontainers` | **4.15.0** (2026-07-24) | Haqiqiy `postgres:18.4-trixie` — `PostgresContainer(..., driver="asyncpg")` [VERIFIED: PyPI + docs] |

### Alternatives Considered

| O'rniga | Ishlatish mumkin edi | Trade-off |
|---------|----------------------|-----------|
| `NULLIF(current_setting(...),'')::uuid` | Har tranzaksiya oxirida `RESET app.market_id` | Xatoga moyil (exception yo'lida bajarilmaydi); NULLIF — bitta joyda, policy ichida |
| `SECURITY DEFINER` login funksiyasi | `BYPASSRLS` li alohida `sbozor_auth` roli | BYPASSRLS = butun bazaga ochiq eshik; funksiya faqat 2 ta aniq so'rovni ochadi |
| DB-trigger audit (moliyaviy) | SQLAlchemy `before_flush` hook | Hook xom SQL, bulk UPDATE va migratsiyalarni **ko'rmaydi** (M10). Ikkalasi ham kerak: trigger — moliyaviy, hook/service — ma'muriy |
| `GENERATED ... STORED` business_date | Kod-qatlamida hisoblash | Kod-qatlami har yozuv joyida takrorlanadi va bittasi unutiladi (P8) |
| Qo'lda transliteratsiya skripti | `@eloqnt/cli`, `UzTransliterator`, `transliteration` | Pastga qarang — litsenziya/yosh muammolari |
| `@eloqnt/cli` (i18n lint) | ~40 satrlik Node skript | `@eloqnt/cli` **litsenziyasiz** va 41 kunlik — MVP uchun tavsiya etilmaydi |
| Nginx + certbot | Caddy 2.11.4 | Cheklovda Nginx; Caddy kam ish talab qiladi, lekin stek qulflangan |

**Installation (core-api, bu faza):**
```bash
uv init services/core-api
uv add --project services/core-api \
  "fastapi==0.140.13" "uvicorn[standard]==0.51.0" \
  "pydantic==2.13.4" "pydantic-settings==2.14.2" \
  "sqlalchemy[asyncio]==2.0.51" "asyncpg==0.31.0" "alembic==1.18.5" "alembic-utils==0.8.8" \
  "pyjwt==2.13.0" "pwdlib[argon2]==0.3.0" "cryptography==49.0.0" \
  "phonenumbers==9.0.35" "structlog==26.1.0" "asgi-correlation-id==5.0.1" \
  "redis[hiredis]==8.0.1" "sentry-sdk[fastapi]==2.66.1" "tzdata==2026.3" \
  "python-multipart==0.0.32" "email-validator==2.3.0"
uv add --project services/core-api --dev \
  "ruff==0.16.0" "mypy==2.3.0" "pytest==9.1.1" "pytest-asyncio==1.4.0" \
  "pytest-cov==7.1.0" "testcontainers[postgres]==4.15.0" "httpx==0.28.1"
```

```bash
# frontend
npx create-next-app@16.2.12 frontend --typescript --tailwind --app --src-dir
npm i next-intl@4.13.4 @tanstack/react-query@5.101.4 zod@4.4.3 \
      react-hook-form@7.83.0 @hookform/resolvers@5.5.7 \
      clsx@2.1.1 tailwind-merge@3.6.0 class-variance-authority@0.7.1 \
      lucide-react@1.27.0 sonner@2.0.7 date-fns@4.4.0
npm i -D typescript@5.9.3          # latest = 7.0.2, pin majburiy
```

---

## Package Legitimacy Audit

`slopcheck` mahalliy muhitda mavjud edi va **barcha paketlar** uchun ishlatildi (`slopcheck scan --json`, pypi + npm ekotizimlari alohida).

| Paket | Registry | slopcheck | Bayroq | Disposition |
|-------|----------|-----------|--------|-------------|
| fastapi, uvicorn, pydantic, pydantic-settings, sqlalchemy, alembic, asyncpg, psycopg, PyJWT, pwdlib, argon2-cffi, cryptography, phonenumbers, structlog, asgi-correlation-id, tzdata, redis, email-validator, greenlet, pytest, pytest-asyncio, mypy, ruff, testcontainers | PyPI | **[OK]** | — | Approved |
| `alembic-utils` | PyPI | **[OK]** | `HALLUCINATION_PATTERN` (info) — nom LLM-bait ko'rinadi, lekin paket haqiqiy | Approved (oxirgi reliz **2025-04-10** — 15 oy; pastdagi Open Question) |
| `sentry-sdk` | PyPI | **[OK]** | `HALLUCINATION_PATTERN` (info) | Approved |
| `python-multipart` | PyPI | **[OK]** | `HALLUCINATION_PATTERN` (info) — `python-` prefiksi | Approved |
| `pytest-cov` | PyPI | **[OK]** | `NO_REPO` (info) | Approved |
| next, react, react-dom, next-intl, @tanstack/react-query, zod, react-hook-form, @hookform/resolvers, tailwind-merge, clsx, class-variance-authority, lucide-react, sonner, nuqs, @radix-ui/react-dialog, @radix-ui/react-select, typescript, tailwindcss, @tailwindcss/postcss, eslint, eslint-config-next | npm | **[OK]** | — | Approved |
| `date-fns` | npm | **[OK]** | `NO_REPO` (info) | Approved |
| **`@eloqnt/cli`** | npm | **[OK]** (mavjud, next-intl rasmiy hujjatida tavsiya etilgan) | **Yaratilgan 2026-06-17 (41 kun), `license: None`, v0.5.4 pre-1.0** | **RAD ETILDI** — litsenziyasiz paket loyihaning Apache-2.0/MIT pozitsiyasiga zid. O'rniga qo'lda yozilgan i18n-parity skripti |

**slopcheck [SLOP] verdikti bilan olib tashlangan paketlar:** yo'q
**Shubhali [SUS] deb belgilangan paketlar:** yo'q (slopcheck bo'yicha). **Qo'lda rad etilgan:** `@eloqnt/cli` (litsenziya + yosh), `UzTransliterator` / `uzbek-latin-cyrillic-converter` / `cyrillic-to-translit-js` (oxirgi reliz 2022, ruscha-yo'naltirilgan)

> Registry mavjudligi + slopcheck [OK] **birga** olinganda ham, paketlarning barchasi CLAUDE.md loyiha-darajasidagi tadqiqotida rasmiy manbalardan olingan — shuning uchun `[VERIFIED: npm/PyPI registry]` maqomiga ega.

---

## Architecture Patterns

### System Architecture Diagram

```
┌─ BROWSER ──────────────────────────────────────────────────────────────────┐
│  GET /uz/... | /uz-cyrl/... | /ru/...                                       │
└───────────┬────────────────────────────────────────────────────────────────┘
            │
┌───────────▼─ FRONTEND SERVER (Next.js 16, Node runtime) ───────────────────┐
│  src/proxy.ts  ──► createMiddleware(routing)                                │
│      prefiks → locale:  /uz → uz-Latn · /uz-cyrl → uz-Cyrl · /ru → ru       │
│      localeDetection:false  →  `/` har doim `/uz` (D-15)                     │
│              │                                                              │
│              ▼                                                              │
│  app/[locale]/layout.tsx  ─► setRequestLocale ─► NextIntlClientProvider      │
│      messages/{uz-Latn,uz-Cyrl,ru}.json   (uz-Cyrl = build artefakti)       │
│              │                                                              │
│              ├── login sahifasi ──► POST /api/v1/auth/login                 │
│              └── boshqa sahifalar ─► Bearer access token                     │
└──────────────┬─────────────────────────────────────────────────────────────┘
               │ HTTPS (nginx, TLS)
┌──────────────▼─ core-api (FastAPI 0.140) ──────────────────────────────────┐
│                                                                             │
│  [middleware] asgi-correlation-id → request_id → structlog contextvars      │
│                                                                             │
│  ┌── LOGIN yo'li (tenant konteksti YO'Q) ────────────────────────────────┐  │
│  │  telefon ──► phonenumbers → E.164                                     │  │
│  │       ▼                                                               │  │
│  │  auth_find_login(phone)         ◄── SECURITY DEFINER, search_path pin │  │
│  │       ▼                              (users jadvaliga GRANT yo'q)     │  │
│  │  pwdlib Argon2id verify ──► is_active? must_change_password?          │  │
│  │       ▼                                                               │  │
│  │  auth_memberships(user_id) ──► [ {market_id, roles[]} ... ]           │  │
│  │       ├─ 1 ta bozor  ──► avtomatik tanlanadi                          │  │
│  │       └─ platforma admini ──► bozor tanlash ekrani (D-06)             │  │
│  │       ▼                                                               │  │
│  │  PyJWT HS256:  access 15 daq (JSON body) · refresh 30 kun (cookie)    │  │
│  │                cookie: HttpOnly Secure SameSite=Lax Path=/api/v1/auth │  │
│  │       ▼                                                               │  │
│  │  audit_log ◄── 'login' | 'login_failed' | 'market_selected'  (app)    │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌── HAR KEYINGI SO'ROV ─────────────────────────────────────────────────┐  │
│  │  Depends(get_current_principal) ──► JWT decode                        │  │
│  │        └─► Valkey `user:blocked:{id}` (TTL 30s) ──► miss? → DB (D-08) │  │
│  │  Depends(require_roles(...))    ──► RBAC matritsasi (kodda, D-07)     │  │
│  │  Depends(get_tenant_session)                                          │  │
│  │        BEGIN                                                          │  │
│  │        set_config('app.market_id',  <uuid>, true)                     │  │
│  │        set_config('app.actor_id',   <uuid>, true)                     │  │
│  │        set_config('app.request_id', <str>,  true)                     │  │
│  │             ... biznes so'rovlari ...                                 │  │
│  │        COMMIT   ──► GUC lar '' bo'ladi → keyingi so'rov fail-closed   │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└──────────────┬─────────────────────────────────────────────────────────────┘
               │  postgresql+asyncpg://sbozor_app@db     (superuser EMAS, BYPASSRLS EMAS)
┌──────────────▼─ PostgreSQL 18.4 ───────────────────────────────────────────┐
│                                                                             │
│  GLOBAL                       TENANT-SCOPED (RLS ENABLE + FORCE)            │
│  ├ markets                    ├ user_market_roles                           │
│  ├ users        (GRANT yo'q)  ├ ... (keyingi fazalar jadvallari)            │
│  └ alembic_version            └ audit_log  (INSERT: WITH CHECK true         │
│                                             SELECT: market_id = GUC)        │
│                                                                             │
│  policy:  market_id = NULLIF(current_setting('app.market_id', true),'')::uuid│
│  composite FK: (market_id, id) ──► cross-tenant havola strukturaviy imkonsiz │
│  indekslar:    (market_id, ...) — market_id DOIM birinchi                    │
│                                                                             │
│  AFTER INSERT/UPDATE/DELETE triggerlari (moliyaviy jadvallar, D-10)         │
│        └─► audit_log(old_value, new_value, changed_keys, actor, request_id) │
│            ▲ xom SQL ham shu yerdan o'tadi — chetlab o'tish yo'li yo'q      │
│                                                                             │
│  audit_log o'zgarmasligi (4 qatlam):                                        │
│    1. REVOKE UPDATE,DELETE,TRUNCATE FROM sbozor_app   → "permission denied" │
│    2. RLS: UPDATE/DELETE uchun policy YO'Q            → 0 qator (owner ham) │
│    3. BEFORE UPDATE OR DELETE trigger                 → RAISE EXCEPTION     │
│    4. BEFORE TRUNCATE statement trigger               → RAISE EXCEPTION     │
└──────────────┬─────────────────────────────────────────────────────────────┘
               │  Alembic (ONE-SHOT job, app startup'da EMAS)
               │  sbozor_owner  ──► DDL + GRANT + PGPolicy (alembic-utils)
               ▼
        migrations/versions/*.py   (yagona tarix, ildizda)
```

### Recommended Project Structure

`.planning/research/ARCHITECTURE.md` dagi rejaga mos, **1-fazada haqiqatan yaratiladigan** qism:

```
sbozor/
├── compose.yaml                      # db, cache, migrate(one-shot), core-api, frontend, nginx
├── compose.override.yml              # dev: hot reload, port mapping
├── .env.example                      # SIRLAR YO'Q — faqat kalit nomlari
├── package.json                      # root: "scripts" (make YO'Q — Windows'da mavjud emas)
│
├── packages/
│   └── sbozor-core/                  # editable install; MODELLAR + INFRA, biznes logikasi YO'Q
│       ├── pyproject.toml
│       └── sbozor_core/
│           ├── models/
│           │   ├── base.py           # Base, TenantMixin(market_id), TimestampMixin
│           │   ├── identity.py       # users, user_market_roles, refresh_tokens
│           │   └── ops.py            # audit_log
│           ├── enums.py              # Role, AuditAction, AuditSource, Locale
│           ├── db.py                 # async engine, async_sessionmaker
│           ├── tenancy.py            # contextvar + set_config helper + TenantScopedRepository
│           ├── money.py              # Soum = int; formatlash; JS-safe chegara tekshiruvi
│           ├── timeutil.py           # MARKET_TZ, business_date(), now_tz()
│           ├── security.py           # Argon2id hash/verify, JWT encode/decode
│           └── logging.py            # structlog + request_id/market_id binding
│
├── services/
│   └── core-api/
│       ├── Dockerfile                # python:3.13-slim-trixie, uv sync --frozen --no-dev
│       ├── pyproject.toml + uv.lock  # PER-SERVICE (aiogram pin konflikti uchun)
│       └── app/
│           ├── main.py               # lifespan; /healthz; /readyz
│           ├── deps.py               # get_current_principal, require_roles, get_tenant_session
│           ├── api/v1/
│           │   ├── auth.py           # login, refresh, logout, change-password
│           │   ├── me.py             # profil + locale PATCH (D-13)
│           │   ├── users.py          # D-04 boshqaruv UI backend
│           │   ├── markets.py        # D-06 bozor ro'yxati + tanlash
│           │   └── audit.py          # D-12 filtrlanadigan ro'yxat
│           └── security/
│               ├── jwt.py            # claim'lar, rotation, reuse-detect
│               ├── rbac.py           # ROL→HUQUQ matritsasi (qat'iy, D-07)
│               └── audit.py          # app-qatlam audit + @audit_read (D-09)
│
├── migrations/                       # YAGONA Alembic tarixi (async shablon)
│   ├── env.py                        # target_metadata + register_entities(alembic-utils)
│   ├── entities/                     # PGPolicy / PGFunction / PGTrigger ta'riflari
│   └── versions/
│
├── frontend/
│   ├── src/
│   │   ├── proxy.ts                  # ⚠ middleware.ts EMAS
│   │   ├── i18n/{routing,navigation,request}.ts
│   │   ├── global.ts                 # next-intl AppConfig augmentation
│   │   └── app/[locale]/
│   │       ├── layout.tsx            # setRequestLocale + NextIntlClientProvider
│   │       ├── (auth)/login/
│   │       └── (app)/{dashboard,users,audit}/
│   ├── messages/
│   │   ├── uz-Latn.json              # ASOSIY — qo'lda
│   │   ├── ru.json                   # qo'lda
│   │   ├── uz-Cyrl.json              # GENERATSIYA — qo'lda tahrirlanmaydi
│   │   └── uz-Cyrl.overrides.json    # qo'lda tuzatish lug'ati (D-14)
│   └── scripts/
│       ├── gen-cyrillic.mjs          # build-time transliteratsiya
│       └── check-messages.mjs        # kalit-parity + ICU argument tekshiruvi
│
├── ops/
│   ├── nginx/
│   └── db/init/                      # rollarni yaratish (sbozor_owner, sbozor_app)
└── tests/
    ├── conftest.py                   # testcontainers postgres:18.4-trixie fixture
    ├── unit/                         # money, timeutil, jwt, rbac
    ├── integration/                  # auth oqimi, audit, user CRUD
    └── tenancy/                      # META-TEST + CROSS-TENANT MATRITSA
```

---

### Pattern 1: Ikki qatlamli tenant izolyatsiyasi — `NULLIF` majburiy

**What:** DB qatlamida RLS (himoya to'ri), app qatlamida `TenantScopedRepository` (asosiy filtr), sxema qatlamida composite FK (strukturaviy imkonsizlik). Uchtasi ham kerak.

**When to use:** har bir tenant jadvalida, istisnosiz.

**Kritik detal (empirik tasdiqlangan):** policy ifodasi **`NULLIF(...)` bilan** yozilishi shart.

```sql
-- ✗ NOTO'G'RI (.planning/research/ARCHITECTURE.md dagi namunaviy shakl)
--   pool'dagi ulanish qayta ishlatilganda:
--   ERROR: invalid input syntax for type uuid: ""
CREATE POLICY tenant_isolation ON stalls
  USING (market_id = current_setting('app.market_id', true)::uuid);

-- ✓ TO'G'RI — fail-closed (0 qator), xato yo'q
CREATE POLICY tenant_isolation ON stalls
  AS PERMISSIVE FOR ALL TO sbozor_app
  USING      (market_id = NULLIF(current_setting('app.market_id', true), '')::uuid)
  WITH CHECK (market_id = NULLIF(current_setting('app.market_id', true), '')::uuid);

ALTER TABLE stalls ENABLE ROW LEVEL SECURITY;
ALTER TABLE stalls FORCE  ROW LEVEL SECURITY;   -- oson unutiladi
```

**Nega:** `set_config('app.market_id', X, true)` tranzaksiya tugagach GUC'ni **o'chirmaydi** — u `''` bo'lib qoladi va ulanish umri davomida shunday qoladi. O'lchov:

| Holat | `current_setting('app.market_id', true)` | `::uuid` |
|-------|------------------------------------------|----------|
| Hech qachon o'rnatilmagan | `NULL` | NULL (xatosiz) |
| **`set_config(...,true)` + COMMIT dan keyin** | **`''`** | **ERROR** |
| `NULLIF(..., '')` bilan | `NULL` | NULL → 0 qator |

**Trade-offs:** (+) RLS ~1–5% overhead. (+) app-filtr unutilsa ham chiqmaydi. (−) `WITH CHECK` INSERT/UPDATE'ni ham qamraydi — bu yaxshi, lekin xato xabari "new row violates row-level security policy" bo'lib, dasturchiga tushunarsiz; API'da 403/404 ga tarjima qilinsin.

---

### Pattern 2: Login bootstrap — RLS ostida kirish qanday ishlaydi

**What:** Identifikatsiya (global) a'zolikdan (tenant-scoped) ajratiladi; login yo'li `SECURITY DEFINER` funksiya orqali o'tadi.

**Muammo (empirik tasdiqlangan):** login paytida `market_id` hali noma'lum. Agar `user_market_roles` tenant-policy ostida bo'lsa:

```
SET ROLE sbozor_app;
SELECT count(*) FROM user_market_roles;   →  0
```

→ **hech kim hech qachon kira olmaydi.** Bu faza uchun eng katta arxitektura qopqoni.

**Yechim:**

| Jadval | `market_id` | RLS | App-rol GRANT |
|--------|-------------|-----|---------------|
| `users` (telefon, hash, is_active, locale, is_platform_admin) | **yo'q** | — | **YO'Q** (`REVOKE ALL`) |
| `user_market_roles` (market_id, user_id, roles[]) | bor | ENABLE + FORCE | SELECT/INSERT/UPDATE/DELETE |
| `markets` | — (o'zi tenant) | maxsus | SELECT |

Login yo'li — ikkita tor `SECURITY DEFINER` funksiya (`search_path` pin qilingan, `REVOKE ALL FROM PUBLIC`):

```sql
CREATE FUNCTION auth_find_login(p_phone text)
RETURNS TABLE (user_id uuid, password_hash text, is_active boolean,
               must_change_password boolean, locale text, is_platform_admin boolean)
LANGUAGE sql SECURITY DEFINER SET search_path = pg_catalog, public STABLE
AS $$ SELECT u.id, u.password_hash, u.is_active, u.must_change_password,
             u.locale, u.is_platform_admin
      FROM users u WHERE u.phone_e164 = p_phone $$;
REVOKE ALL ON FUNCTION auth_find_login(text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION auth_find_login(text) TO sbozor_app;
```

**Empirik natija:**
- `SELECT count(*) FROM users` app-rol bilan → `ERROR: permission denied for table users` ✓
- `SELECT * FROM auth_find_login('+998901111111')` tenant-kontekstsiz → **ishlaydi** ✓
- Bozor tanlangandan keyin `app.market_id` bilan → faqat o'sha bozor qatorlari ✓
- Platforma admini 2-bozorni tanlaganda → faqat 2-bozor qatorlari — **bypass yo'li yo'q** ✓ (D-06)

**Trade-offs:** (+) `BYPASSRLS` rol umuman kerak emas. (+) Global o'qish yuzasi aynan 2 ta funksiya bilan cheklangan va audit qilinadi. (−) `users` ni ORM orqali oddiy `select()` bilan o'qib bo'lmaydi — repository `text()` bilan funksiyani chaqiradi (ataylab: bu "tasodifan global o'qish" ni imkonsiz qiladi).

---

### Pattern 3: JWT + rollar to'plami + darhol bloklash

**What:** Access token qisqa va stateless; refresh token uzun, httpOnly cookie'da, DB'da rotatsiya bilan; bloklash har so'rovda Valkey keshi orqali tekshiriladi.

**Token claim'lari (tavsiya):**

| Claim | Qiymat | Izoh |
|-------|--------|------|
| `sub` | `str(user_id)` | **PyJWT 2.10+ `sub` ni validatsiya qiladi — `str` bo'lishi shart**, UUID obyekti emas |
| `iss` | `"sbozor"` | PyJWT 2.11+ `iss` ni `str` deb talab qiladi |
| `aud` | `"sbozor-api"` | |
| `exp` / `iat` / `jti` | standart | `jti` — reuse-detect uchun |
| `mid` | `str(market_id)` | tanlangan bozor (D-06) |
| `roles` | `["market_admin","cashier"]` | D-05 rollar TO'PLAMI |
| `pa` | `true/false` | platforma admini bayrog'i |
| `typ` | `"access"` / `"refresh"` | ikkalasini aralashtirmaslik uchun majburiy |

**Sir uzunligi:** PyJWT **2.11.0** dan boshlab HMAC kalitining minimal uzunligi tekshiriladi (`InsecureKeyLengthWarning`). HS256 uchun RFC 7518 minimumi **32 bayt**. `JWT_SECRET` ni `secrets.token_urlsafe(48)` bilan hosil qiling va `enforce_minimum_key_length=True` bering — ogohlantirish emas, xato bo'lsin.

**Refresh cookie (D-03, 30 kun sliding):**
```
Set-Cookie: sbozor_rt=<token>; HttpOnly; Secure; SameSite=Lax;
            Path=/api/v1/auth; Max-Age=2592000
```
`Path` ni `/api/v1/auth` ga cheklash — cookie boshqa endpointlarga yuborilmaydi (CSRF yuzasi kichrayadi). `SameSite=Lax` — bir xil site'dan navigatsiya ishlaydi, cross-site POST yuborilmaydi.

**Rotatsiya + reuse detection:** har `POST /auth/refresh` da eski `jti` bekor qilinadi va yangisi beriladi. Bekor qilingan `jti` qayta kelsa → **o'sha foydalanuvchining butun token oilasi bekor qilinadi** + audit yozuvi (`refresh_reuse_detected`). Bu o'g'irlangan tokenni 30 kun emas, keyingi navbatdagi ishlatishda o'ldiradi.

**Darhol bloklash (D-08):**
```
get_current_principal:
  JWT decode  →  Valkey GET user:state:{id}       (TTL 30 s)
                  ├─ hit  → is_active tekshiriladi
                  └─ miss → DB (auth_find_login yo'lidagi funksiya) → Valkey SET
  bloklash/o'chirish yozuvi  →  Valkey DEL user:state:{id}  (bir xil tranzaksiyadan keyin)
```
TTL 30 s → eng yomon holatda 30 soniya kechikish; kesh invalidatsiyasi bilan amalda darhol. Valkey o'chgan holatda DB'ga tushadi (fail-open emas — kesh yo'q bo'lsa DB javob beradi).

---

### Pattern 4: Audit — moliyaviy jadvallarda DB-trigger (D-10)

**What:** `AFTER INSERT OR UPDATE OR DELETE ... FOR EACH ROW` trigger `to_jsonb(OLD)`/`to_jsonb(NEW)` ni yozadi; aktor GUC'dan olinadi.

**Empirik natija (`postgres:18.4`):**

| Tekshiruv | Natija |
|-----------|--------|
| Oddiy tenant-scoped INSERT + UPDATE | 2 ta audit qator; `changed_keys = {amount_soum}`, `old=5000 → new=7000` ✓ |
| **ORM'ni chetlab o'tgan xom `UPDATE tariffs SET ...`** | **audit qator yozildi** ✓ (M10 oldini olish isbotlandi) |
| No-op UPDATE (bir xil qiymat) | audit qator **yozilmadi** — shovqin yo'q ✓ |
| Cross-tenant o'qish (bozor B) | 0 qator ✓ |

**Trigger — `SECURITY DEFINER` bo'lmasligi kerak.** `audit_log` da `FOR INSERT WITH CHECK (true)` policy va app-rolga `INSERT` grant bo'lsa, trigger chaqiruvchi huquqi bilan yozadi. Bu soddaroq va xavfsizroq (privilege escalation yuzasi yo'q).

**Aktor konteksti:** `app.actor_id` va `app.request_id` — `app.market_id` bilan **bir xil `set_config(..., true)` blokida** o'rnatiladi. Fon job'lari uchun `actor_kind='system'` va `actor_label='system:billing'`.

**Qamrov (D-10):** `daily_charges`, `charge_adjustments`, `payments`, `tariffs`, `stall_assignments`. 1-fazada bu jadvallarning aksari hali yo'q — shuning uchun **trigger funksiyasi + `alembic-utils` `PGTrigger` shabloni** shu fazada yaratiladi va `users`/`user_market_roles` ga qo'llanadi; 2- va 6-fazalarda jadval tug'ilishi bilan bir qatorda `PGTrigger` qo'shiladi (bir satrlik ish).

---

### Pattern 5: `audit_log` o'zgarmasligi — 4 qatlam

**What:** Har qatlam boshqa tahdid modelini yopadi. Barchasi empirik tekshirildi.

| # | Mexanizm | Kimga qarshi | Kuzatilgan natija |
|---|----------|--------------|-------------------|
| 1 | `REVOKE UPDATE, DELETE, TRUNCATE ON audit_log FROM sbozor_app` | Ilova kodi, SQL injection | `ERROR: permission denied for table audit_log` (baland ovozda) |
| 2 | RLS ENABLE+FORCE, **UPDATE/DELETE uchun policy YO'Q** | Jadval egasi (`sbozor_owner`), migratsiyalar | `UPDATE 0` / `DELETE 0` (**jimgina**) |
| 3 | `BEFORE UPDATE OR DELETE ... FOR EACH ROW → RAISE EXCEPTION` | Policy tasodifan qo'shilsa | `ERROR: audit_log is append-only (attempted UPDATE)` |
| 4 | `BEFORE TRUNCATE ... FOR EACH STATEMENT → RAISE EXCEPTION` | `TRUNCATE` (2-qatlam uni to'xtatmaydi) | `ERROR: ... (attempted TRUNCATE)` — **egaga qarshi ham ishladi** |

> ⚠ **Testni yozishda muhim nuqta:** 2-qatlam tufayli egaga qarshi `UPDATE` **xato tashlamaydi**, u `UPDATE 0` qaytaradi. Shuning uchun verifikatsiya testi "exception ko'tarildimi?" emas, **"qatorlar o'zgarmadimi?"** ni tekshirishi kerak. Faqat exception'ni kutgan test yolg'on-yashil beradi.

**RLS policy'lari:**
```sql
CREATE POLICY audit_append ON audit_log FOR INSERT WITH CHECK (true);
CREATE POLICY audit_read   ON audit_log FOR SELECT
  USING (market_id = NULLIF(current_setting('app.market_id', true), '')::uuid);
```
`WITH CHECK (true)` — yozish har doim ruxsat (jurnalga yozishni bloklash mumkin emas); o'qish tenant-scoped (D-11). Platforma-global yozuvlar (`market_id IS NULL`) app-rolga ko'rinmaydi — ular platforma admini uchun alohida `SECURITY DEFINER` funksiya orqali beriladi.

---

### Pattern 6: Shaxsiy ma'lumot O'QISHLARI auditi (D-09)

**What:** Postgres'da `SELECT` uchun trigger **yo'q** — o'qish auditi faqat app-qatlamida yoziladi.

**Qanday EMAS:** blanket middleware. U har so'rovni (statik, health, list) yozadi, resurs ID'larini bilmaydi va jurnalni foydasiz shovqin bilan to'ldiradi.

**Qanday:** endpointda **aniq e'lon qilinadigan** dependency:

```python
@router.get("/audit")
async def list_audit(
    _: Annotated[None, Depends(audit_read("audit_log", reason="audit_view"))],
    ...
)
```

Yozuv: `actor`, `market_id`, `resource_type`, `resource_ids` (yoki filtr tavsifi), `result_count`, `request_id`, `at`. Yozuv `source='app'`, `action='read'`.

**1-fazada qamrov:** sotuvchilar (`vendors`) hali 2-fazada tug'iladi, shuning uchun bu fazada o'qish-auditining yagona iste'molchisi — **audit ko'rish UI'ning o'zi** (D-11: "auditni ko'rish ham audit-o'qish sifatida yoziladi"). Mexanizm shu yerda quriladi va keyingi fazalar unga bir dekorator bilan ulanadi.

**Anti-pattern:** o'qish-auditini o'sha tranzaksiyada `audit_log` ga yozib, keyin biznes tranzaksiyasi rollback bo'lsa — audit ham yo'qoladi. O'qish auditi **alohida tranzaksiyada** (yoki `after_response` background task'da) yozilsin, chunki o'qish sodir bo'lgan.

---

### Pattern 7: `business_date` — generated column (FOUND-05)

**What:** `business_date` — DB tomonidan hisoblanadigan `STORED` ustun. Kod-qatlamida umuman hisoblanmaydi.

```sql
business_date date GENERATED ALWAYS AS
  ((created_at AT TIME ZONE 'Asia/Tashkent')::date) STORED
```

**Nega ishlaydi (empirik):** `timezone(text, timestamp with time zone)` funksiyasi `pg_proc.provolatile = 'i'` — **IMMUTABLE**. Shuning uchun generated column'da ruxsat etiladi. (Taqqoslash uchun: `timezone(timestamptz)` — bitta argumentli, GUC'ga bog'liq versiya — `'s'` (STABLE) va **ishlamaydi**.)

**Chegara xulq-atvori (o'lchandi):**

| UTC vaqt | Asia/Tashkent devor-vaqti | `business_date` | Naive `::date` (XATO) |
|----------|---------------------------|-----------------|------------------------|
| `2026-11-05 18:30Z` | 2026-11-05 **23:30** | `2026-11-05` | `2026-11-05` |
| `2026-11-05 19:30Z` | 2026-11-06 **00:30** | **`2026-11-06`** | ❌ `2026-11-05` |
| `2026-11-05 01:00Z` | 2026-11-05 06:00 | `2026-11-05` | `2026-11-05` |

Ya'ni mahalliy yarim tundan keyingi 5 soat naive UTC sanasida **oldingi kunga** tushadi — bu aynan ROADMAP mezoni #4 talab qilgan xulq-atvor.

**Kelajakka moslik:** kun yopilishi yarim tunda emas, masalan 02:00 da bo'lsa — `((created_at AT TIME ZONE 'Asia/Tashkent') - interval '2 hours')::date` ham generated column'da ishlaydi (tekshirildi). MVP'da yarim tun (offset yo'q) — mezon #4 shuni talab qiladi.

**Per-market timezone:** `markets.timezone` ustuni bo'lsa ham, generated column **boshqa jadvalga murojaat qila olmaydi**. Agar kelajakda kerak bo'lsa, `timezone` ni qatorga denormalizatsiya qilish kerak (`(created_at AT TIME ZONE tz)::date` — bir xil qatordagi ustun bilan ishlaydi, tekshirildi). **MVP'da `'Asia/Tashkent'` literal + `markets.timezone TEXT NOT NULL DEFAULT 'Asia/Tashkent'` ustuni sxemada bo'lsin** (P8 tavsiyasi) — lekin generated column'da hozircha literal ishlatiladi.

**Moliyaviy konstraytlar (mezon #5 — 6-fazadan oldin o'rnatilishi shart):**
```sql
UNIQUE (market_id, stall_id, business_date)     -- BILL-01 idempotentligi
CHECK  (amount_soum > 0)                         -- pul musbat
FOREIGN KEY (market_id, stall_id) REFERENCES stalls(market_id, id)   -- cross-tenant imkonsiz
UNIQUE (market_id, idempotency_key)              -- CASH-03 takror bosish
```
`ON CONFLICT (market_id, stall_id, business_date) DO NOTHING` — qayta ishga tushirish `INSERT 0` qaytardi va summa o'zgarmadi (tekshirildi).

---

### Pattern 8: Tenancy meta-test + cross-tenant matritsa (FOUND-02)

**What:** CI gate sifatida ikkita test to'plami. Bu 1-fazaning eng qimmatli artefakti — u keyingi 7 fazadagi regressiyani doimiy ushlab turadi.

**A. Meta-test (sxema invariantlari):** har yangi jadval uchun avtomatik:

```python
GLOBAL_TABLES = {"markets", "users", "alembic_version"}

def test_every_table_is_tenant_scoped(sync_conn):
    for t in table_names(sync_conn):
        if t in GLOBAL_TABLES: continue
        assert has_column(t, "market_id"),  f"{t}: market_id yo'q"
        assert rls_enabled(t) and rls_forced(t), f"{t}: RLS ENABLE/FORCE yo'q"
        assert has_policy(t), f"{t}: policy yo'q"          # RLS+policy'siz = deny-all

def test_tenant_indexes_lead_with_market_id(sync_conn):
    # PK (id) istisno; qolgan har bir indeks market_id bilan boshlanadi
    ...

def test_app_role_cannot_bypass_rls(sync_conn):
    row = sync_conn.execute(text(
        "SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = 'sbozor_app'"
    )).one()
    assert not row.rolsuper and not row.rolbypassrls   # ← FORCE buni qoplamaydi

def test_security_definer_functions_pin_search_path(sync_conn):
    rows = sync_conn.execute(text(
        "SELECT proname, proconfig FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace "
        "WHERE n.nspname='public' AND p.prosecdef"
    )).all()
    for r in rows:
        assert r.proconfig and any(c.startswith("search_path=") for c in r.proconfig)
```

**B. Cross-tenant matritsa (PITFALLS.md P9 #4):** ikki bozor seed qilinadi; **`app.routes` dan avtomatik ro'yxat olinadi** va har bir route A-tokeni bilan B-obyekt ID'sida chaqiriladi → **404 kutiladi** (403 emas — 403 mavjudlikni tasdiqlaydi). Yangi route qo'shilganda test avtomatik uni qamraydi; qamrab olinmagan route uchun `xfail` emas, **fail** bo'lsin.

---

### Pattern 9: next-intl 4.13 + Next 16 — `proxy.ts` va custom prefikslar (FOUND-04)

**What:** URL prefiksi locale'ni to'liq belgilaydi; Accept-Language aniqlash o'chirilgan (D-15).

```ts
// src/i18n/routing.ts
import {defineRouting} from 'next-intl/routing';

export const routing = defineRouting({
  locales: ['uz-Latn', 'uz-Cyrl', 'ru'],
  defaultLocale: 'uz-Latn',
  localePrefix: {
    mode: 'always',
    prefixes: {
      'uz-Latn': '/uz',
      'uz-Cyrl': '/uz-cyrl'
      // 'ru' prefiksi o'zgartirilmaydi → /ru
    }
  },
  localeDetection: false          // D-15: Accept-Language YO'Q
});
```

```ts
// src/proxy.ts   ⚠ middleware.ts EMAS (Next 16)
import createMiddleware from 'next-intl/middleware';
import {routing} from './i18n/routing';

export default createMiddleware(routing);

export const config = {
  matcher: '/((?!api|_next|_vercel|.*\\..*).*)'
};
```

**Kritik nuanslar:**
- `localePrefix` custom shakli **`{mode, prefixes}`** obyekti — tekis `{locale: prefix}` obyekti EMAS. (Ikkinchisi ba'zi manbalarda uchraydi va noto'g'ri.)
- Custom prefikslar **faqat foydalanuvchiga ko'rinadi**; ichkarida `/uz/...` → `/uz-Latn/...` ga rewrite qilinadi. Ya'ni `app/[locale]/` segmenti **`uz-Latn`** qiymatini oladi, `uz` emas. `generateStaticParams()` `routing.locales` ni qaytaradi.
- `localeDetection: false` **cookie'dan aniqlashni ham o'chiradi**. D-13 bilan ziddiyat yo'q: locale — foydalanuvchi profilida (DB), va **login'dan keyin server `users.locale` ni o'qib to'g'ri prefiksga redirect qiladi**. Cookie faqat login'gacha bo'lgan sahifalar uchun qoladi (`localeCookie` sozlanadi yoki `false` qilinadi).
- Til almashtirish (bir bosish, FOUND-04): `router.replace(pathname, {locale})` + parallel `PATCH /api/v1/me {locale}` — DB bitta haqiqat manbai bo'lib qoladi (D-13).

**TypeScript kalit xavfsizligi:**
```ts
// src/global.ts
import {routing} from '@/i18n/routing';
import messages from '../messages/uz-Latn.json';

declare module 'next-intl' {
  interface AppConfig {
    Locale: (typeof routing.locales)[number];
    Messages: typeof messages;
  }
}
```
Bu noto'g'ri kalitni **kompilyatsiya vaqtida** xatoga aylantiradi.

---

### Pattern 10: uz-Latn → uz-Cyrl build-time transliteratsiya (D-14)

**What:** `messages/uz-Cyrl.json` — **generatsiya artefakti**, qo'lda tahrirlanmaydi. `scripts/gen-cyrillic.mjs` uni `uz-Latn.json` + `uz-Cyrl.overrides.json` dan hosil qiladi.

**Nega tayyor kutubxona emas:** ekotizim yupqa va eskirgan — `UzTransliterator` (PyPI, oxirgi reliz **2022-10-23**), `uzbek-latin-cyrillic-converter` (**2022-05-03**), `cyrillic-to-translit-js` (**2022-05-05**, ruscha-yo'naltirilgan). Mapping o'zi ~40 qoidadan iborat va deterministik — o'z skriptingiz eskirmaydi va CI'da tekshiriladi.

**Tartib muhim (uzun digraflar avval):**
```
o' oʻ ô → ў   |  g' gʻ ĝ → ғ   |  sh → ш   |  ch → ч
yo → ё  |  yu → ю  |  ya → я  |  ye → е   |  ts → ц
q → қ   |  x → х   |  h → ҳ   |  ' ʼ → ъ
```
Qolgan harflar bir-birga: a→а, b→б, d→д, e→е/э (pastga qarang), f→ф, g→г, i→и, j→ж, k→к, l→л, m→м, n→н, o→о, p→п, r→р, s→с, t→т, u→у, v→в, y→й, z→з.

**Noaniqlik to'plami (`overrides.json` shu yerda kerak):**

| Holat | Qoida | Misol |
|-------|-------|-------|
| `e` so'z boshida yoki unlidan keyin | → **э** | `Eslatma` → `Эслатма` |
| `e` undoshdan keyin | → **е** | `kelmoq` → `келмоқ` |
| `ts` o'zlashma so'zlarda | → **ц** | `protsent` → `процент` |
| Ruscha o'zlashmalar | qo'lda | `sertifikat`, `terminal` |
| Xos ismlar, brend | **o'zgarmaydi** | `SBOZOR`, `Karmana` (tekshirilsin) |
| Apostrof variantlari | normallashtirilsin | ASCII `'` · U+02BB `ʻ` · U+02BC `ʼ` · U+2018 `'` — hammasi bir xil qoidaga tushsin |

**Eng katta amaliy tuzoq — ICU platsholderlarini transliteratsiya qilib qo'yish:**
```
"Rasta {stallNumber} uchun {count, plural, one {# patta} other {# patta}}"
```
Bu yerda **`{stallNumber}`, `{count}`, `plural`, `one`, `other`, `#`** — ICU sintaksisi, matn emas. Skript ularni **daxlsiz** qoldirishi shart. Amalga oshirish: `{...}` bloklarini regex bilan ajratib, faqat blokdan tashqaridagi matnni transliteratsiya qilish; `plural`/`select` ichidagi **branch matni** transliteratsiya qilinadi, **branch nomlari** — yo'q. Shuningdek: URL, e-mail, HTML teglar, `<b>`/`</b>` markerlari.

**CI qoidalari:**
1. `node scripts/gen-cyrillic.mjs --check` — generatsiya natijasi commit qilingan `uz-Cyrl.json` bilan bir xil bo'lmasa → fail (drift'ning oldini oladi).
2. `node scripts/check-messages.mjs` — uchala fayl kalitlari **aynan bir xil** to'plam; har bir xabardagi ICU argumentlari to'plami mos.
3. Fallback zanjiri `uz-Latn → ru → kalit` (P: UX pitfall — kalit ko'rinishi "Apple-uslub" ishonchini o'ldiradi).

---

### Pattern 11: Alembic — async shablon + `alembic-utils` + RLS bayroqlari

**What:** `alembic init -t async migrations` (shablon mavjudligi tekshirildi) → `env.py` `connection.run_sync(do_run_migrations)` ishlatadi, ya'ni **asyncpg URL yetarli**, alohida `psycopg` URL shart emas.

**`alembic-utils` nimani qoplaydi va nimani QOPLAMAYDI:**

| Obyekt | `alembic-utils` | Izoh |
|--------|-----------------|------|
| `CREATE POLICY` / `DROP POLICY` | ✅ `PGPolicy(schema, signature, definition, on_entity)` | Tekshirildi: to'g'ri SQL generatsiya qiladi |
| Trigger | ✅ `PGTrigger` | |
| Funksiya | ✅ `PGFunction` | |
| GRANT | ✅ `PGGrantTable` | |
| **`ALTER TABLE ... ENABLE ROW LEVEL SECURITY`** | ❌ **YO'Q** | Manba kodida `CREATE/DROP POLICY` dan boshqa hech narsa yo'q |
| **`ALTER TABLE ... FORCE ROW LEVEL SECURITY`** | ❌ **YO'Q** | Shu bilan birga |
| `REVOKE` | ❌ | `PGGrantTable` faqat GRANT |

→ **ENABLE/FORCE va REVOKE xom `op.execute()` bo'lishi shart.** Buni unutish eng oson yo'l bilan sodir bo'ladi: policy autogenerate bo'ladi, RLS esa yoqilmay qoladi va policy **hech qanday ta'sir ko'rsatmaydi**. Meta-test (Pattern 8) aynan shu holatni ushlaydi.

**Tavsiya:** jadval yaratuvchi migratsiya uchun bitta yordamchi:
```python
def enable_tenant_rls(table: str, role: str = "sbozor_app") -> None:
    op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {table} FORCE  ROW LEVEL SECURITY")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {table} TO {role}")
```

---

### Anti-Patterns to Avoid

- **`SET LOCAL app.market_id = :param`** — Postgres `SET` bind-parametr qabul qilmaydi. Empirik: `PostgresSyntaxError: syntax error at or near "$1"`. Har doim `SELECT set_config('app.market_id', :m, true)`.
- **`connection.exec_driver_sql("... %s ...", (v,))`** — asyncpg `$1` paramstyle ishlatadi, `%s` emas. Empirik: `syntax error at or near "%"`. Event listener ichida ham `text()` + nomlangan parametrlar ishlating.
- **`set_config(..., true)` ni tranzaksiyasiz chaqirish** — autocommit'da har statement o'z tranzaksiyasi; qiymat **darhol yo'qoladi** va `''` qoldiradi. Empirik tasdiqlangan.
- **`FORCE ROW LEVEL SECURITY` ni yagona himoya deb bilish** — superuser va `BYPASSRLS` roli FORCE'dan qat'i nazar hammasini ko'radi. Empirik: FORCE qo'yilgandan keyin ham superuser 2/2 qatorni ko'rdi.
- **Migratsiyada ma'lumot backfill qilish (owner + FORCE)** — jimgina `UPDATE 0`. Empirik tasdiqlangan. `SET LOCAL row_security = off` **ishlamaydi** (`ERROR: query would be affected by row-level security policy`). Yagona yo'l: `ALTER TABLE ... NO FORCE ROW LEVEL SECURITY` → backfill → `FORCE` qaytarish (yoki har bozor uchun `set_config` bilan aylanish).
- **`SECURITY DEFINER` funksiyani `search_path` pin qilmasdan yozish** — privilege escalation vektori. Har doim `SET search_path = pg_catalog, public`.
- **Audit'ni faqat ORM hook'ida yozish** — bulk UPDATE, xom SQL va migratsiyalar chetlab o'tadi (M10).
- **Yangi jadval qo'shib RLS'ni unutish** — jadval hech qanday policy'siz RLS bilan **deny-all** bo'ladi (fail-closed, yaxshi), lekin RLS umuman yoqilmasa **hamma narsa ochiq**. Meta-test majburiy.
- **`middleware.ts`** Next 16 da — jimgina ishlamaydi. `proxy.ts`.
- **`float` pul uchun** — `BIGINT` so'm.
- **`date_trunc('day', created_at)` hisobotda** — `business_date` ustuni bo'yicha guruhlash.

---

## Don't Hand-Roll

| Muammo | Qurmang | O'rniga | Nega |
|--------|---------|---------|------|
| Tenant filtri har so'rovda | Qo'lda `WHERE market_id=` intizomi | **Postgres RLS + `TenantScopedRepository`** | Bitta unutilgan predikat = moliyaviy ma'lumot sizishi; RLS bir kunlik ish, audit — bir haftalik va hech qachon to'liq emas |
| Parol hash | SHA/bcrypt qo'lda, `passlib` | **`pwdlib[argon2]`** | passlib Python 3.13'da import bo'lmaydi; Argon2id parametrlari OWASP tavsiyasiga mos |
| JWT kodlash/dekodlash | Qo'lda HMAC | **PyJWT 2.13** | `alg=none`, `crit`, kalit uzunligi, `sub`/`iss` tiplari — hammasi kutubxonada yopilgan |
| Telefon normalizatsiyasi | Regex `+998...` | **`phonenumbers`** | Formatlar ko'p (`998901234567`, `+998 90 123 45 67`, `901234567`); dublikat foydalanuvchi = D-01 buzilishi |
| Eski→yangi farq (diff) | Python'da model taqqoslash | **`to_jsonb(OLD/NEW)` + `jsonb_each`** | Xom SQL yo'lini ham qamraydi; `changed_keys` bitta so'rovda |
| Biznes-kun hisoblash | Kodda `datetime.astimezone(...).date()` | **`GENERATED ALWAYS AS ... STORED`** | Kod-qatlamida har yozuv joyida takrorlanadi va bittasi unutiladi |
| Idempotentlik | "Avval SELECT, keyin INSERT" | **`UNIQUE(...)` + `ON CONFLICT DO NOTHING`** | Race condition; DB konstrayti yagona ishonchli yo'l |
| Locale routing | Qo'lda `[lang]` segmenti + kontekst | **next-intl `proxy.ts`** | Redirect, cookie, `hreflang`, ICU format — hammasi tayyor |
| Sana/son formatlash 3 tilda | Qo'lda formatlash | **`Intl` (Node 24 full ICU) `next-intl` orqali** | `uz-Latn-UZ`, `uz-Cyrl-UZ`, `ru-UZ` — native |
| Test uchun baza | SQLite / mock | **testcontainers + `postgres:18.4-trixie`** | SQLite'da RLS yo'q → eng xavfli kod yo'li testsiz qoladi |
| Request ID propagatsiyasi | Qo'lda header uzatish | **`asgi-correlation-id`** | Audit yozuvi bilan log satrini bog'lash |

**Key insight:** bu domenda "qo'lda qilish" narxi kechikkan holda to'lanadi. Tenant sizishi, audit teshigi va sana chegarasi xatosi — uchalasi ham **jimgina** buziladi va faqat nizo paytida (ya'ni mahsulot ishonchini yo'qotgandan keyin) ko'rinadi. Shuning uchun ularning har biri **DB konstraytiga** aylantirilgan.

---

## Common Pitfalls

### Pitfall 1: `current_setting(...)::uuid` — bo'sh satr xatosi (VERIFIED)

**Nima buziladi:** Pool'dagi ulanish qayta ishlatilganda RLS policy `ERROR: invalid input syntax for type uuid: ""` tashlaydi. Login sahifasi, health-check, yoki har qanday tenant-kontekstsiz so'rov 500 beradi.
**Nega:** `set_config(..., is_local=>true)` tranzaksiya oxirida GUC'ni NULL'ga qaytarmaydi — u `''` bo'lib qoladi (Postgres'ning ma'lum xulqi; `RESET` ham shunday qiladi).
**Qanday oldini olish:** policy'da **har doim** `NULLIF(current_setting('app.market_id', true), '')::uuid`.
**Ogohlantirish belgilari:** `InvalidTextRepresentationError` loglarda; birinchi so'rov ishlaydi, ikkinchisi yiqiladi; `pool_size=1` da har doim takrorlanadi.

### Pitfall 2: `FORCE ROW LEVEL SECURITY` superuser'ni to'xtatmaydi (VERIFIED)

**Nima buziladi:** RLS to'g'ri yozilgan, FORCE qo'yilgan, lekin `DATABASE_URL` da `postgres` superuser ishlatilgan (dev'da oson sodir bo'ladi, keyin prod'ga ko'chadi) → **hech qanday izolyatsiya yo'q**, va hech bir test buni ko'rsatmaydi, chunki testlar ham o'sha rol bilan ishlaydi.
**Nega:** FORCE faqat **jadval egasini** policy'ga bo'ysundiradi. Superuser va `BYPASSRLS` atributli rollar har doim chetlab o'tadi.
**Qanday oldini olish:** uchta rol — `sbozor_owner` (DDL, superuser EMAS), `sbozor_app` (DML, superuser EMAS, BYPASSRLS EMAS), va zarur bo'lsa `sbozor_worker` (BYPASSRLS — faqat cross-tenant tick uchun, 4-fazada). Meta-testda `pg_roles` tekshiriladi. Testcontainers fixture'i ham **`sbozor_app` bilan** ulanishi shart, `postgres` bilan emas.
**Ogohlantirish belgilari:** cross-tenant test yashil, lekin `SET ROLE` ishlatilmagan; `DATABASE_URL` da `postgres:` foydalanuvchisi.

### Pitfall 3: Login RLS ostida imkonsiz (VERIFIED)

**Nima buziladi:** `users`/`user_market_roles` ga tenant-policy qo'yiladi; login endpoint 0 qator oladi; **hech kim kira olmaydi**. Bu integratsiya testi yozilgunga qadar ko'rinmaydi, chunki unit testlar RLS'siz ishlaydi.
**Nega:** login paytida `app.market_id` hali mavjud emas — u aynan login natijasida aniqlanadi.
**Qanday oldini olish:** Pattern 2 — global `users` + `SECURITY DEFINER` funksiyalar. **`BYPASSRLS` rol yaratib qo'ymang** — u D-06 ni buzadi va butun bazani ochadi.
**Ogohlantirish belgilari:** login "noto'g'ri parol" qaytaradi, lekin parol to'g'ri; DB'da foydalanuvchi bor.

### Pitfall 4: Migratsiyadagi ma'lumot backfill jimgina 0 qator (VERIFIED)

**Nima buziladi:** `sbozor_owner` (superuser emas) + FORCE RLS ostida `op.execute("UPDATE ... SET ...")` **`UPDATE 0`** qaytaradi. Migratsiya "muvaffaqiyatli" tugaydi, ma'lumot esa o'zgarmaydi.
**Nega:** FORCE egani ham policy'ga bo'ysundiradi; `app.market_id` migratsiyada o'rnatilmagan.
**Qanday oldini olish:** `ALTER TABLE ... NO FORCE ROW LEVEL SECURITY` → backfill → `FORCE` qaytarish. `SET LOCAL row_security = off` **ishlamaydi** — `ERROR: query would be affected by row-level security policy` (tekshirildi). Har backfill migratsiyasidan keyin `assert result.rowcount == expected`.
**Ogohlantirish belgilari:** migratsiya loglarida `UPDATE 0`; keyingi migratsiya NOT NULL qo'shishda yiqiladi.

### Pitfall 5: Audit teshigi — hook faqat ORM yo'lini ko'radi

**Nima buziladi:** `before_flush` hook'i bulk UPDATE, `session.execute(text(...))` va migratsiyalarni ko'rmaydi — ya'ni aynan texnik savodli insider ishlatadigan yo'llarni.
**Nega:** ORM hook — ORM abstraksiyasining ichida.
**Qanday oldini olish:** moliyaviy jadvallarda DB-trigger (D-10). Verifikatsiya: **testda xom SQL bilan `UPDATE payments SET ...` qiling va audit qator paydo bo'lishini tekshiring** (PITFALLS.md "Looks Done But Isn't" ro'yxatidagi punkt).
**Ogohlantirish belgilari:** audit yozuvlari faqat API orqali kelgan o'zgarishlarda.

### Pitfall 6: UTC konteyner soati vs Asia/Tashkent biznes-kuni

**Nima buziladi:** Docker konteynerlar `TZ=UTC`. Mahalliy 00:00–04:59 orasidagi har bir yozuv naive UTC sanasida **oldingi kunga** tushadi (o'lchandi). To'lovlar va hisoblar qaysi kunga tegishli ekanida kelishmaydi — bu mahsulot ishlab chiqaradigan aynan o'sha rekonsiliatsiya.
**Qanday oldini olish:** (1) `business_date` — generated `STORED` ustun; (2) barcha vaqtlar `timestamptz`; (3) `tzdata` paketi slim image'da (busiz `ZoneInfo("Asia/Tashkent")` xato tashlaydi); (4) compose'da `TZ=Asia/Tashkent`, lekin kodda **aniq** `ZoneInfo` ishlatilsin — `TZ` ga tayanmang; (5) `markets.timezone` ustuni 1-fazadayoq sxemada.
**Ogohlantirish belgilari:** hisobotda bir kun cho'kadi, ertasi ko'tariladi; log timestamplari 5 soat farq qiladi.

### Pitfall 7: BIGINT so'm ↔ JavaScript `Number`

**Nima buziladi:** `BIGINT` maksimumi ~9.2×10¹⁸, JS `Number.MAX_SAFE_INTEGER` esa 9.007×10¹⁵. Kattaroq qiymat JSON orqali o'tganda jimgina yaxlitlanadi.
**Amaliy baho:** kunlik patta ~5 000–50 000 so'm; 1000 rasta × 365 kun × 50 000 ≈ 1.8×10¹⁰ — **xavfsiz chegaradan 5 daraja past**. Ya'ni MVP'da muammo yo'q.
**Qanday oldini olish:** API'da pul oddiy JSON `number` bo'lib qolsin (`string` ga o'tish keraksiz murakkablik), lekin `money.py` da `MAX_SAFE_SOUM = 9_007_199_254_740_991` konstantasi va aggregatlarda tekshiruv bo'lsin; frontend tomonda `zod` sxemasida `.int().max(...)`.
**Ogohlantirish belgilari:** yillik agregatlarda oxirgi raqamlar mos kelmasligi.

### Pitfall 8: ICU platsholderlari transliteratsiya qilinishi

**Nima buziladi:** `gen-cyrillic.mjs` `{stallNumber}` ni `{сталлНумбер}` ga aylantiradi → uz-Cyrl'da har bir dinamik xabar buziladi, faqat runtime'da ko'rinadi.
**Qanday oldini olish:** `{...}` bloklarini ajratish; `plural`/`select` **branch nomlarini** (`one`, `other`, `few`, `many`, `zero`, `=0`) o'zgarmas qoldirish; `#` belgisini saqlash; URL/e-mail/HTML teglarini istisno qilish. CI'da `check-messages.mjs` uchala fayldagi ICU argumentlari to'plamini taqqoslaydi.
**Ogohlantirish belgilari:** uz-Cyrl'da xabar o'rniga `{...}` ko'rinadi yoki `IntlError: MISSING_ARGUMENT`.

### Pitfall 9: `audit_log` egaga qarshi jimgina himoyalanadi (VERIFIED)

**Nima buziladi:** Test "UPDATE exception ko'taradimi?" deb yozilsa, egaga qarshi holatda **exception ko'tarilmaydi** — `UPDATE 0` qaytadi (chunki UPDATE uchun policy yo'q, qatorlar ko'rinmaydi). Test yiqiladi yoki (yomonroq) noto'g'ri "himoya yo'q" xulosasi chiqadi.
**Qanday oldini olish:** verifikatsiya **holat bo'yicha** bo'lsin: `UPDATE`/`DELETE` urinishidan keyin qator soni va `action` qiymati o'zgarmaganini tekshiring. App-rol uchun alohida test — `permission denied` kutiladi. `TRUNCATE` uchun exception kutiladi.

### Pitfall 10: `alembic-utils` RLS bayroqlarini boshqarmaydi (VERIFIED)

**Nima buziladi:** `PGPolicy` autogenerate bo'ladi, `ENABLE`/`FORCE ROW LEVEL SECURITY` esa yo'q — policy mavjud, lekin **ta'sir ko'rsatmaydi**. Cross-tenant test faqat policy borligini tekshirsa, yashil qoladi.
**Qanday oldini olish:** `enable_tenant_rls()` yordamchisi + meta-testda `pg_class.relrowsecurity` VA `relforcerowsecurity` ikkalasini tekshirish.

---

## Code Examples

### 1. Tenant session dependency (core-api)

```python
# services/core-api/app/deps.py
from typing import Annotated, AsyncIterator
from uuid import UUID
from fastapi import Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sbozor_core.db import SessionLocal

SET_CTX = text(
    "SELECT set_config('app.market_id', :market_id, true),"
    "       set_config('app.actor_id',  :actor_id,  true),"
    "       set_config('app.request_id',:request_id,true)"
)

async def get_tenant_session(
    principal: Annotated["Principal", Depends(get_current_principal)],
) -> AsyncIterator[AsyncSession]:
    """Tenant konteksti HAR TRANZAKSIYADA, ulanishda EMAS."""
    async with SessionLocal() as session:
        async with session.begin():                     # ← tranzaksiya majburiy
            await session.execute(SET_CTX, {
                "market_id":  str(principal.market_id),
                "actor_id":   str(principal.user_id),
                "request_id": principal.request_id,
            })
            yield session
        # COMMIT → GUC lar '' bo'ladi → keyingi so'rov fail-closed
```

> `set_config(..., true)` — uchinchi argument `is_local`. `SET LOCAL app.market_id = :m` **sintaksis xatosi beradi** (tekshirildi): Postgres `SET` bind-parametr qabul qilmaydi.

### 2. RLS policy (alembic-utils entity)

```python
# migrations/entities/policies.py
from alembic_utils.pg_policy import PGPolicy

TENANT_PREDICATE = (
    "market_id = NULLIF(current_setting('app.market_id', true), '')::uuid"
)

def tenant_policy(table: str) -> PGPolicy:
    return PGPolicy(
        schema="public",
        signature="tenant_isolation",
        on_entity=f"public.{table}",
        definition=f"""
            AS PERMISSIVE
            FOR ALL
            TO sbozor_app
            USING      ({TENANT_PREDICATE})
            WITH CHECK ({TENANT_PREDICATE})
        """,
    )
```
```python
# migrations/versions/xxxx_users_and_roles.py
def upgrade() -> None:
    op.create_table("user_market_roles", ...)
    # alembic-utils ENABLE/FORCE ni boshqarmaydi — xom SQL majburiy:
    op.execute("ALTER TABLE user_market_roles ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE user_market_roles FORCE  ROW LEVEL SECURITY")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON user_market_roles TO sbozor_app")
    op.create_entity(tenant_policy("user_market_roles"))
```

### 3. Login bootstrap funksiyalari (SECURITY DEFINER)

```sql
-- migrations: PGFunction sifatida ro'yxatga olinadi
CREATE OR REPLACE FUNCTION auth_find_login(p_phone text)
RETURNS TABLE (user_id uuid, password_hash text, is_active boolean,
               must_change_password boolean, locale text, is_platform_admin boolean)
LANGUAGE sql
SECURITY DEFINER
SET search_path = pg_catalog, public      -- ← privilege-escalation himoyasi
STABLE
AS $$
  SELECT u.id, u.password_hash, u.is_active, u.must_change_password,
         u.locale, u.is_platform_admin
  FROM users u
  WHERE u.phone_e164 = p_phone
$$;
REVOKE ALL ON FUNCTION auth_find_login(text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION auth_find_login(text) TO sbozor_app;

-- users jadvaliga app-rolga to'g'ridan-to'g'ri huquq BERILMAYDI:
REVOKE ALL ON users FROM sbozor_app;
```

### 4. Parol va JWT (pwdlib + PyJWT)

```python
# packages/sbozor-core/sbozor_core/security.py
import jwt
from datetime import datetime, timedelta, timezone
from pwdlib import PasswordHash

_hasher = PasswordHash.recommended()          # Argon2id

def hash_password(raw: str) -> str:
    return _hasher.hash(raw)

def verify_password(raw: str, stored: str) -> tuple[bool, str | None]:
    """(to'g'ri_mi, yangilangan_hash_yoki_None) — parametrlar o'zgarsa qayta hash."""
    return _hasher.verify_and_update(raw, stored)

ALG = "HS256"

def encode_access(*, user_id, market_id, roles, is_platform_admin, secret: str) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "sub": str(user_id),               # ← PyJWT 2.10+ `sub` str bo'lishini talab qiladi
            "iss": "sbozor",                   # ← 2.11+ `iss` str bo'lishi shart
            "aud": "sbozor-api",
            "iat": now,
            "exp": now + timedelta(minutes=15),
            "typ": "access",
            "mid": str(market_id),
            "roles": list(roles),
            "pa": is_platform_admin,
        },
        secret, algorithm=ALG,
    )

def decode_access(token: str, secret: str) -> dict:
    claims = jwt.decode(
        token, secret,
        algorithms=[ALG],                      # ← hech qachon token header'idan olinmaydi
        audience="sbozor-api",
        issuer="sbozor",
        options={
            "require": ["exp", "iat", "sub", "iss", "aud"],
            "verify_exp": True,
            "enforce_minimum_key_length": True,   # ← 2.11+: <32 bayt sir → InvalidKeyError
        },
    )
    if claims.get("typ") != "access":
        raise jwt.InvalidTokenError("wrong token type")
    return claims
```

### 5. Audit trigger funksiyasi (moliyaviy jadvallar, D-10)

```sql
CREATE OR REPLACE FUNCTION fn_audit_row() RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public
AS $$
DECLARE
  v_old  jsonb := CASE WHEN TG_OP IN ('UPDATE','DELETE') THEN to_jsonb(OLD) END;
  v_new  jsonb := CASE WHEN TG_OP IN ('INSERT','UPDATE') THEN to_jsonb(NEW) END;
  v_keys text[];
BEGIN
  IF TG_OP = 'UPDATE' THEN
    SELECT array_agg(n.k) INTO v_keys
    FROM jsonb_each(v_new) n(k, v)
    WHERE n.v IS DISTINCT FROM (v_old -> n.k);
    IF v_keys IS NULL THEN RETURN NULL; END IF;      -- no-op update → audit shovqini yo'q
  END IF;

  INSERT INTO audit_log(market_id, actor_user_id, actor_kind, action, table_name,
                        row_id, old_value, new_value, changed_keys, request_id, source)
  VALUES (
    COALESCE((v_new->>'market_id')::uuid, (v_old->>'market_id')::uuid),
    NULLIF(current_setting('app.actor_id',   true), '')::uuid,
    COALESCE(NULLIF(current_setting('app.actor_kind', true), ''), 'user'),
    lower(TG_OP), TG_TABLE_NAME,
    COALESCE((v_new->>'id')::uuid, (v_old->>'id')::uuid),
    v_old, v_new, v_keys,
    NULLIF(current_setting('app.request_id', true), ''),
    'db_trigger'
  );
  RETURN NULL;                                        -- AFTER trigger
END $$;
```

### 6. `audit_log` jadvali va o'zgarmaslik qatlamlari

```sql
CREATE TABLE audit_log (
  id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  at            timestamptz NOT NULL DEFAULT now(),
  business_date date GENERATED ALWAYS AS ((at AT TIME ZONE 'Asia/Tashkent')::date) STORED,
  market_id     uuid,                    -- NULL faqat platforma-global harakatlar uchun
  actor_user_id uuid,
  actor_kind    text NOT NULL DEFAULT 'user',     -- user | system
  actor_label   text,                    -- "platforma admini X bozorida" (D-06)
  action        text NOT NULL,           -- insert|update|delete|read|login|login_failed|...
  table_name    text NOT NULL,
  row_id        uuid,
  old_value     jsonb,
  new_value     jsonb,
  changed_keys  text[],
  request_id    text,
  ip            inet,
  source        text NOT NULL            -- db_trigger | app
);
CREATE INDEX ON audit_log (market_id, at DESC);
CREATE INDEX ON audit_log (market_id, table_name, row_id);
CREATE INDEX ON audit_log (market_id, actor_user_id, at DESC);

-- 1-qatlam: grantlar
GRANT SELECT, INSERT ON audit_log TO sbozor_app;
REVOKE UPDATE, DELETE, TRUNCATE ON audit_log FROM sbozor_app;

-- 2-qatlam: RLS (UPDATE/DELETE uchun policy YO'Q → egaga ham 0 qator)
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_log FORCE  ROW LEVEL SECURITY;
CREATE POLICY audit_append ON audit_log FOR INSERT WITH CHECK (true);
CREATE POLICY audit_read   ON audit_log FOR SELECT
  USING (market_id = NULLIF(current_setting('app.market_id', true), '')::uuid);

-- 3- va 4-qatlam: triggerlar
CREATE OR REPLACE FUNCTION audit_immutable() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, public AS $$
BEGIN RAISE EXCEPTION 'audit_log is append-only (attempted %)', TG_OP; END $$;

CREATE TRIGGER audit_no_mutate   BEFORE UPDATE OR DELETE ON audit_log
  FOR EACH ROW       EXECUTE FUNCTION audit_immutable();
CREATE TRIGGER audit_no_truncate BEFORE TRUNCATE        ON audit_log
  FOR EACH STATEMENT EXECUTE FUNCTION audit_immutable();
```

### 7. next-intl — request config va navigation

```ts
// src/i18n/request.ts
import {getRequestConfig} from 'next-intl/server';
import {hasLocale} from 'next-intl';
import {routing} from './routing';

export default getRequestConfig(async ({requestLocale}) => {
  const requested = await requestLocale;
  const locale = hasLocale(routing.locales, requested)
    ? requested
    : routing.defaultLocale;                       // D-15: har doim uz-Latn

  return {
    locale,
    messages: (await import(`../../messages/${locale}.json`)).default,
    timeZone: 'Asia/Tashkent'                      // FOUND-05: ko'rsatish vaqti
  };
});
```
```ts
// src/i18n/navigation.ts
import {createNavigation} from 'next-intl/navigation';
import {routing} from './routing';

export const {Link, redirect, usePathname, useRouter, getPathname} =
  createNavigation(routing);
```

### 8. Til almashtirgich (bir bosish — FOUND-04, D-13)

```tsx
'use client';
import {useLocale} from 'next-intl';
import {usePathname, useRouter} from '@/i18n/navigation';
import {useTransition} from 'react';

const LOCALES = [
  {code: 'uz-Latn', label: "O'zbekcha"},
  {code: 'uz-Cyrl', label: 'Ўзбекча'},
  {code: 'ru',      label: 'Русский'}
] as const;

export function LocaleSwitcher() {
  const active   = useLocale();
  const pathname = usePathname();
  const router   = useRouter();
  const [pending, start] = useTransition();

  function change(locale: string) {
    start(() => {
      router.replace(pathname, {locale});                  // URL prefiksi almashadi
      void fetch('/api/v1/me', {                           // D-13: DB — bitta haqiqat manbai
        method: 'PATCH',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({locale})
      });
    });
  }
  // ... render
}
```

### 9. Moliyaviy jadval konstraytlari (mezon #5, 6-fazadan oldin)

```sql
CREATE TABLE daily_charges (
  id            uuid PRIMARY KEY DEFAULT uuidv7(),        -- PG18 native
  market_id     uuid NOT NULL,
  stall_id      uuid NOT NULL,
  created_at    timestamptz NOT NULL DEFAULT now(),
  business_date date GENERATED ALWAYS AS
                  ((created_at AT TIME ZONE 'Asia/Tashkent')::date) STORED,
  amount_soum   bigint NOT NULL CHECK (amount_soum > 0),  -- float EMAS
  tariff_id     uuid NOT NULL,
  tariff_amount_soum bigint NOT NULL,                     -- M12: tarif SNAPSHOT qilinadi
  UNIQUE (market_id, stall_id, business_date),            -- BILL-01 idempotentligi
  FOREIGN KEY (market_id, stall_id) REFERENCES stalls(market_id, id)   -- cross-tenant imkonsiz
);
CREATE INDEX ON daily_charges (market_id, business_date, stall_id);
```
```sql
-- kunni qayta yopish dublikat yaratmaydi (tekshirildi: INSERT 0, summa o'zgarmadi)
INSERT INTO daily_charges (market_id, stall_id, amount_soum, tariff_id, tariff_amount_soum)
VALUES (...)
ON CONFLICT (market_id, stall_id, business_date) DO NOTHING;
```

### 10. testcontainers fixture (RLS testlari uchun)

```python
# tests/conftest.py
import pytest
from testcontainers.postgres import PostgresContainer
from sqlalchemy.ext.asyncio import create_async_engine

@pytest.fixture(scope="session")
def pg():
    # SQLite EMAS — RLS faqat Postgres'da mavjud
    with PostgresContainer("postgres:18.4-trixie", driver="asyncpg") as c:
        yield c

@pytest.fixture(scope="session")
async def app_engine(pg, migrated):
    """DIQQAT: sbozor_app roli bilan ulanadi, postgres superuser bilan EMAS —
    aks holda RLS testlari yolg'on-yashil beradi."""
    url = pg.get_connection_url().replace(
        f"{pg.username}:{pg.password}", "sbozor_app:app_pw"
    )
    engine = create_async_engine(url, pool_size=1, max_overflow=0)
    yield engine
    await engine.dispose()
```
> `pool_size=1` — GUC sizishini maksimal darajada ochib beradi; agar test shu holatda o'tsa, prod'da ham o'tadi.

---

## State of the Art

| Eski yondashuv | Joriy yondashuv | Qachon o'zgardi | Ta'siri |
|----------------|-----------------|-----------------|---------|
| `passlib[bcrypt]` | **`pwdlib[argon2]`** | fastapi-users v13; Python 3.13 dan `crypt` olib tashlandi | passlib Python 3.13'da **import bo'lmaydi** — eski darsliklar ishlamaydi |
| `python-jose` | **PyJWT 2.13** | python-jose amalda tashlab qo'yilgan (2025-05) | CVE tarixi; PyJWT 2.11+ kalit uzunligi va `sub`/`iss` tiplarini tekshiradi |
| `middleware.ts` (Next) | **`proxy.ts`** (Node runtime, Edge yo'q) | Next.js 16 | Barcha onlayn next-intl darsliklari eskirgan; **jimgina** locale routing buziladi |
| `IntlMessages` global tip | **`declare module 'next-intl' { interface AppConfig }`** | next-intl 4.0 | 3.x uslubidagi augmentation ishlamaydi |
| `tailwind.config.js` | **`@theme {}` CSS ichida** | Tailwind 4 | Config fayli umuman yo'q |
| `gen_random_uuid()` / `uuid-ossp` | **`uuidv7()`** native | PostgreSQL 18 | Vaqt-tartiblangan PK → B-tree fragmentatsiyasi kamayadi; `uuid_extract_timestamp()` bonus |
| Sync Alembic + alohida `psycopg` URL | **`alembic init -t async`** | Alembic 1.11+ | `connection.run_sync()` — bitta asyncpg URL yetadi |
| `@on_event("startup")` | **`lifespan=`** | FastAPI 0.93+ | Eski shakl deprecated |
| MinIO | **SeaweedFS** | MinIO repo arxivlangan 2026-04-25 | (bu fazada emas, 4-fazada) |
| Redis | **Valkey** | Redis litsenziya o'zgarishi | `redis-py` klienti o'zgarmaydi |

**Deprecated / eskirgan:**
- `passlib` — 2020-10-08 dan beri reliz yo'q, Python 3.13'da ishlamaydi
- `python-jose` — 2025-05-28 dan beri reliz yo'q
- SQLAlchemy 1.x `Query` API — 2.0 `select()` uslubi
- FastAPI `@app.on_event` — `lifespan`
- next-intl 3.x `createSharedPathnamesNavigation` — `createNavigation`

---

## Assumptions Log

| # | Da'vo | Bo'lim | Xato bo'lsa ta'siri |
|---|-------|--------|---------------------|
| A1 | Valkey keshi TTL 30 s bloklash uchun yetarli (D-08 "darhol") | Pattern 3 | 30 soniyagacha bloklangan kassir to'lov kiritishi mumkin. Agar "darhol" qat'iy 0 soniya bo'lishi kerak bo'lsa — keshni butunlay olib tashlab har so'rovda DB'ga borish kerak (~1 ms qo'shimcha). **Buyurtmachi bilan aniqlanishi kerak.** |
| A2 | Refresh cookie `SameSite=Lax` + `Path=/api/v1/auth` CSRF uchun yetarli | Pattern 3 | Agar frontend va API turli origin'da bo'lsa (`SameSite=None` kerak bo'ladi), double-submit CSRF token qo'shilishi shart. **Deployment topologiyasi (bitta domen ostida nginx orqali?) tasdiqlanishi kerak.** |
| A3 | MVP'da biznes-kun chegarasi = mahalliy yarim tun (offset yo'q) | Pattern 7 | ROADMAP mezoni #4 shuni aytadi, lekin PITFALLS P8 "kun yopilish vaqtini bozor sozlamasi qiling (masalan 22:00)" deydi. Agar bozor 20:00 dan keyin ham savdo qilsa va kun 22:00 da yopilsa — generated column offset bilan qayta yozilishi kerak (migratsiya kerak). **Buyurtmachi savoli.** |
| A4 | `market_id` — `users` jadvalida YO'Q, faqat `user_market_roles` da | Pattern 2 | Agar keyinchalik `users` ga `market_id` kerak bo'lsa, meta-testdagi `GLOBAL_TABLES` ro'yxati va login yo'li qayta ko'rib chiqiladi. D-05 "kelajakda ko'p-bozorga kengayadi" shuni talab qiladi — ishonch yuqori. |
| A5 | Pul qiymatlari JS `Number` xavfsiz chegarasidan oshmaydi | Pitfall 7 | Hisoblangan baho 5 daraja zaxira beradi; noto'g'ri bo'lsa API'da `string` ga o'tish kerak (frontend refactor). |
| A6 | Frontend test freymvorki 1-fazada talab qilinmaydi (typecheck + build + i18n-parity yetarli) | Validation Architecture | Mezon #2 ("til bir bosishda almashadi") avtomatik tekshirilmay qoladi — brauzer testi (Playwright) stekda yo'q. **Rejalashtiruvchi/foydalanuvchi qarori.** |
| A7 | Nginx + Let's Encrypt sozlash 1-fazada emas (dev'da HTTP yetarli) | Compose skeleti | `Secure` cookie bayrog'i HTTP'da ishlamaydi → dev uchun shartli bayroq kerak. Agar 1-fazada TLS talab qilinsa, qo'shimcha ish. |
| A8 | `sbozor_worker` (BYPASSRLS) roli 1-fazada yaratilmaydi | Pattern 1 | 4-fazada cross-tenant tick uchun kerak bo'ladi; hozir yaratilmasa meta-test soddaroq. Erta yaratilsa — meta-test uni istisno qilishi kerak. |
| A9 | `alembic-utils` autogenerate async Alembic env'da ishlaydi | Pattern 11 | Kutilishi bor: autogenerate `run_sync()` ichida sync `Connection` bilan ishlaydi, shuning uchun mos kelishi kerak — lekin **empirik tekshirilmadi**. Wave 0 da 5 daqiqalik tekshiruv. Ishlamasa: policy'larni xom `op.execute()` bilan yozish (past ko'chish narxi). |

---

## Open Questions

1. **`alembic-utils` uzoq muddatli qo'llab-quvvatlanishi**
   - Bilamiz: 0.8.8 oxirgi reliz **2025-04-10** (15 oy oldin); alembic 1.18.5 bilan **ishlashi tekshirildi** (import + SQL generatsiya).
   - Noaniq: alembic 1.19/2.0 chiqqanda mos qoladimi.
   - Tavsiya: ishlatilsin, lekin `PGPolicy` ta'riflari **bitta faylda** (`migrations/entities/policies.py`) jamlansin — kerak bo'lsa `op.execute()` ga ko'chirish bir soatlik ish. Bu qarorni qaytarish narxi past.

2. **Frontend brauzer testi (mezon #2 avtomatik isboti)**
   - Bilamiz: CLAUDE.md stekida test freymvorki yo'q; Next 16 `@playwright/test` ni **ixtiyoriy** peer sifatida ko'rsatadi.
   - Noaniq: 12 haftalik jadvalda Playwright o'rnatish oqlanadimi.
   - Tavsiya: 1-fazada `tsc --noEmit` + `next build` + `check-messages.mjs` + **qo'lda tekshirish** (mezon #2 `human-verify` sifatida). Playwright'ni 8-fazaga (mustahkamlash) qoldirish.

3. **Deployment topologiyasi va cookie bayroqlari**
   - Bilamiz: nginx reverse proxy rejalashtirilgan; frontend va API bir xil domen ostida bo'lishi mumkin (`/` → Next, `/api` → FastAPI).
   - Noaniq: shundaymi yoki alohida subdomen (`app.` / `api.`).
   - Tavsiya: **bitta domen** tanlansin — `SameSite=Lax` yetarli bo'ladi va CSRF ishi kamayadi. Bu 1-fazada qaror qilinishi kerak, chunki keyin o'zgartirish auth oqimini qayta yozishni talab qiladi.

4. **`markets` jadvali uchun RLS siyosati**
   - Bilamiz: `markets` — tenant chegarasining o'zi; platforma admini hammasini ko'rishi kerak (D-06), boshqalar faqat o'zinikini.
   - Noaniq: policy `id = GUC` bo'ladimi yoki `SECURITY DEFINER` ro'yxat funksiyasi.
   - Tavsiya: `markets` da `USING (id = NULLIF(current_setting('app.market_id',true),'')::uuid)` + platforma admini uchun alohida `auth_list_markets()` `SECURITY DEFINER` funksiyasi (login yo'lidagi bilan bir xil naqsh). Meta-testda `markets` `GLOBAL_TABLES` da emas, **maxsus holat** sifatida qayd etilsin.

5. **Huquqiy ko'rik (STATE.md blocker)**
   - Bilamiz: shaxsiy ma'lumot lokalizatsiyasi va audit-o'qish talablari (D-09) avtomatik xulosadan olingan.
   - Noaniq: O'zR qonuni audit jurnali saqlash muddatini belgilaydimi (retention).
   - Tavsiya: `audit_log` uchun retention siyosati 1-fazada **belgilanmasin** (o'chirish yo'li bo'lmasin) — mahalliy yurist tasdig'igacha jurnal cheksiz saqlansin. Bu `[ASSUMED]` — yuridik tasdiq kerak.

---

## Environment Availability

Xost mashinasi (Windows 11, `E:\bozor`) tekshirildi 2026-07-29.

| Bog'liqlik | Kim talab qiladi | Mavjud | Versiya | Fallback |
|------------|------------------|--------|---------|----------|
| Docker Engine | Compose steki (db, cache, api, frontend) | ✓ | 29.4.2 | — |
| Docker Compose v2 | Orkestratsiya | ✓ | v5.1.3 (plugin) | — |
| `postgres:18.4-trixie` image | DB + testcontainers | ✓ | **mahalliy keshda** (tortib olindi va ishga tushirildi) | — |
| Node.js | frontend build/dev | ✓ | **24.14.1** (Next 16 `>=20.9.0` talabidan yuqori) | — |
| npm | frontend paketlar | ✓ | 11.11.0 | — |
| git | VCS | ✓ | 2.53.0 | — |
| Python (xost) | Faqat mahalliy skriptlar | ✓ | 3.14.3 | Servislar Docker'da 3.13 — xost versiyasi ahamiyatsiz |
| **`uv`** | Python deps + `uv.lock` (CLAUDE.md majburiy) | **✗** | — | (a) `pip install uv` xostga, yoki (b) `uv` faqat Dockerfile ichida (`ghcr.io/astral-sh/uv` COPY) va xostda ishlatilmaydi. **(b) tavsiya etiladi** — xost muhitini iflos qilmaydi |
| **`make`** | ARCHITECTURE.md `Makefile` rejasi | **✗** | — | **Windows'da `make` yo'q.** Root `package.json` `"scripts"` bo'limi (`npm run up`, `npm run migrate`, `npm run test`) — Node allaqachon mavjud. Bu tavsiya etiladi |
| `psql` (xost) | Qo'lda DB tekshiruvi | ✗ | — | `docker compose exec db psql -U ...` |
| `gh` CLI | — | ✗ | — | Bu fazada kerak emas |
| `slopcheck` | Paket legitimligi | ✓ | mavjud | — |

**Fallback'siz bloklovchi bog'liqliklar:** yo'q.

**Fallback bilan yetishmayotganlar:**
- `uv` — Dockerfile ichida ishlatilsin (`COPY --from=ghcr.io/astral-sh/uv:0.11.33 /uv /bin/uv`); xostga o'rnatish ixtiyoriy.
- `make` — `Makefile` o'rniga root `package.json` skriptlari. **Bu rejaga kiritilishi kerak**, chunki ARCHITECTURE.md `Makefile` ni nazarda tutadi va u bu mashinada ishlamaydi.

---

## Validation Architecture

### Test Framework

| Xususiyat | Qiymat |
|-----------|--------|
| Framework (backend) | pytest 9.1.1 + pytest-asyncio 1.4.0 + testcontainers 4.15.0 |
| Config file | **yo'q — Wave 0** (`services/core-api/pyproject.toml` `[tool.pytest.ini_options]`, `asyncio_mode = "auto"`) |
| Quick run command | `docker compose run --rm core-api pytest tests/unit -x -q` |
| Full suite command | `docker compose run --rm core-api pytest -q --cov=sbozor_core --cov=app` |
| Framework (frontend) | **yo'q** — 1-fazada `tsc --noEmit` + `next build` + `node scripts/check-messages.mjs` (A6 ga qarang) |
| Lint/type gate | `ruff check . && ruff format --check . && mypy .` · `npm run lint && npx tsc --noEmit` |

### Phase Requirements → Test Map

| Req | Xulq-atvor | Turi | Avtomatik buyruq | Fayl bormi? |
|-----|-----------|------|------------------|-------------|
| FOUND-01 | Telefon+parol bilan kirish, rollar to'plami tokenga tushadi | integration | `pytest tests/integration/test_auth_login.py -x` | ❌ Wave 0 |
| FOUND-01 | Noto'g'ri parol / bloklangan / `must_change_password` yo'llari | integration | `pytest tests/integration/test_auth_login.py -k "invalid or blocked or must_change" -x` | ❌ Wave 0 |
| FOUND-01 | RBAC: direktor rasta/tarif o'zgartira olmaydi (D-07) | unit | `pytest tests/unit/test_rbac_matrix.py -x` | ❌ Wave 0 |
| FOUND-01 | Bloklash darhol kuchga kiradi (D-08) | integration | `pytest tests/integration/test_user_block.py -x` | ❌ Wave 0 |
| FOUND-02 | **Har jadvalda `market_id` + RLS ENABLE va FORCE** | integration | `pytest tests/tenancy/test_meta.py -x` | ❌ Wave 0 |
| FOUND-02 | **`sbozor_app` superuser/BYPASSRLS EMAS** | integration | `pytest tests/tenancy/test_meta.py::test_app_role_cannot_bypass_rls -x` | ❌ Wave 0 |
| FOUND-02 | **Cross-tenant matritsa: A tokeni + B ID → 404** | integration | `pytest tests/tenancy/test_cross_tenant.py -x` | ❌ Wave 0 |
| FOUND-02 | Tenant kontekstisiz so'rov 0 qator (fail-closed), xato tashlamaydi | integration | `pytest tests/tenancy/test_rls_predicate.py -x` | ❌ Wave 0 |
| FOUND-02 | Composite FK cross-tenant havolani bloklaydi | integration | `pytest tests/tenancy/test_composite_fk.py -x` | ❌ Wave 0 |
| FOUND-03 | Ma'muriy o'zgarish audit qator hosil qiladi (eski→yangi) | integration | `pytest tests/integration/test_audit_write.py -x` | ❌ Wave 0 |
| FOUND-03 | **Xom SQL (ORM'siz) UPDATE ham audit yozadi** | integration | `pytest tests/integration/test_audit_write.py::test_raw_sql_is_audited -x` | ❌ Wave 0 |
| FOUND-03 | `audit_log` UPDATE/DELETE/TRUNCATE — **holat o'zgarmaydi** (Pitfall 9) | integration | `pytest tests/integration/test_audit_immutable.py -x` | ❌ Wave 0 |
| FOUND-03 | Audit ko'rish o'qish-audit yozuvini hosil qiladi (D-11) | integration | `pytest tests/integration/test_audit_read.py -x` | ❌ Wave 0 |
| FOUND-04 | 3 locale fayli aynan bir xil kalit to'plamiga ega | unit (node) | `node frontend/scripts/check-messages.mjs` | ❌ Wave 0 |
| FOUND-04 | uz-Cyrl generatsiyasi commit bilan mos (drift yo'q) | unit (node) | `node frontend/scripts/gen-cyrillic.mjs --check` | ❌ Wave 0 |
| FOUND-04 | ICU platsholderlari transliteratsiya qilinmagan | unit (node) | `node frontend/scripts/check-messages.mjs` (ICU arg diff) | ❌ Wave 0 |
| FOUND-04 | `/` → `/uz` redirect; `/ru` locale = `ru` | manual + build | `npm run build` + qo'lda (A6) | ❌ Wave 0 |
| FOUND-05 | `business_date` mahalliy yarim tunda suriladi (23:30 va 00:30) | integration | `pytest tests/integration/test_business_date.py -x` | ❌ Wave 0 |
| FOUND-05 | Pul `bigint`; `CHECK (amount_soum > 0)` ishlaydi | integration | `pytest tests/integration/test_money_constraints.py -x` | ❌ Wave 0 |
| Mezon #5 | `UNIQUE(market_id, stall_id, business_date)` + `ON CONFLICT DO NOTHING` idempotent | integration | `pytest tests/integration/test_idempotency.py -x` | ❌ Wave 0 |

### Sampling Rate

- **Har task commit:** `ruff check . && mypy . && pytest tests/unit -x -q` (< 30 s, konteynersiz)
- **Har wave merge:** `pytest -q` (testcontainers bilan to'liq to'plam) + `npm run lint && npx tsc --noEmit && node scripts/check-messages.mjs`
- **Faza darvozasi:** to'liq to'plam yashil + `tests/tenancy/` **majburiy** yashil, `/gsd-verify-work` dan oldin

### Wave 0 Gaps

- [ ] `services/core-api/pyproject.toml` → `[tool.pytest.ini_options] asyncio_mode = "auto"`
- [ ] `tests/conftest.py` — `PostgresContainer("postgres:18.4-trixie", driver="asyncpg")` + Alembic upgrade + **`sbozor_app` roli bilan engine** (superuser bilan EMAS)
- [ ] `tests/fixtures/two_markets.py` — cross-tenant matritsa uchun ikki bozor seed
- [ ] `tests/tenancy/test_meta.py` — sxema invariantlari (4 ta assert guruhi)
- [ ] `tests/tenancy/test_cross_tenant.py` — `app.routes` dan avtomatik route ro'yxati
- [ ] `frontend/scripts/check-messages.mjs` — kalit-parity + ICU argument diff
- [ ] `frontend/scripts/gen-cyrillic.mjs` — `--check` rejimi bilan
- [ ] CI workflow — `ruff`, `mypy`, `pytest`, `tsc --noEmit`, `next build`, i18n skriptlari
- [ ] **Tekshiruv (A9):** `alembic-utils` autogenerate async env'da ishlashini 5 daqiqada tasdiqlash

---

## Security Domain

`security_enforcement: true`, `security_asvs_level: 1`. Quyida **ASVS 5.0** (2025-05, joriy versiya) bo'limlari ishlatilgan.

### Applicable ASVS Categories

| ASVS 5.0 bo'limi | Tegishli | Standart nazorat (bu fazada) |
|------------------|----------|------------------------------|
| **V2 Validation & Business Logic** | ha | Pydantic 2.13 DTO'lari chegarada; `phonenumbers` E.164 normalizatsiya; `zod` frontendda |
| **V3 Web Frontend Security** | ha | httpOnly refresh cookie (XSS o'qiy olmaydi); `SameSite=Lax`; Next 16 default CSP-friendly build; token `localStorage` da EMAS |
| **V4 API & Web Service** | ha | FastAPI OpenAPI sxemasi; barcha yozuv endpointlari `Depends(require_roles(...))` ostida |
| **V6 Authentication** | **ha (yadro)** | Argon2id (`pwdlib.PasswordHash.recommended()`); parol tiklash faqat admin orqali (D-02) + majburiy almashtirish; login rate-limit (Valkey) |
| **V7 Session Management** | **ha (yadro)** | Access 15 daq; refresh 30 kun sliding + **rotatsiya** + **reuse detection**; logout token oilasini bekor qiladi; bloklash darhol (D-08) |
| **V8 Authorization** | **ha (yadro)** | Kodda qat'iy RBAC matritsasi (D-07); **Postgres RLS** — funksiya emas, ma'lumot darajasidagi nazorat; cross-tenant CI matritsasi |
| **V9 Self-contained Tokens** | **ha (yadro)** | PyJWT `algorithms=["HS256"]` aniq ro'yxat; `iss`/`aud`/`exp`/`sub` majburiy; `typ` ajratish; sir ≥32 bayt (`enforce_minimum_key_length=True`) |
| **V11 Cryptography** | ha | Hech narsa qo'lda yozilmaydi — `pwdlib`, `PyJWT`, `cryptography`; sirlar `.env` da, repoda emas |
| **V12 Secure Communication** | qisman | TLS nginx'da (A7 — 1-fazada ixtiyoriy); dev'da `Secure` bayrog'i shartli |
| **V13 Configuration** | ha | `.env.example` da sir yo'q; `sbozor_app` **superuser emas**; `public` sxemada `CREATE` huquqi PUBLIC'ga berilmagan (PG18 default, tekshirildi) |
| **V14 Data Protection** | ha | Shaxsiy ma'lumot o'qishlari auditda (D-09); Sentry `before_send` PII filtri; parol hashlari hech qachon log/response'da |
| **V16 Security Logging & Error Handling** | **ha (yadro)** | Append-only `audit_log` (4 qatlamli); `login_failed` yoziladi; `request_id` bog'lanishi; xato javoblari ichki tafsilot bermaydi (RLS xatosi → 404) |
| V5 File Handling | yo'q | Bu fazada fayl yuklash yo'q (2-fazada plan-rasm) |
| V10 OAuth / OIDC | yo'q | Uchinchi tomon IdP yo'q (D-01) |
| V17 WebRTC | yo'q | 3-fazada (go2rtc) |

### Known Threat Patterns for FastAPI + Postgres RLS + Next.js

| Naqsh | STRIDE | Standart yumshatish | Bu fazada isbot |
|-------|--------|---------------------|-----------------|
| Cross-tenant ma'lumot sizishi (yetishmagan `market_id`) | Information Disclosure | RLS + composite FK + scoped repository | `tests/tenancy/test_cross_tenant.py` (har route) |
| Ilova superuser sifatida ulanadi → RLS bekor | Elevation of Privilege | `sbozor_app` superuser/BYPASSRLS emas | `test_app_role_cannot_bypass_rls` (**empirik zarurat tasdiqlangan**) |
| GUC pool orqali sizishi (`SET` vs `SET LOCAL`) | Information Disclosure | `set_config(..., true)` + tranzaksiya + `NULLIF` fail-closed | `test_rls_predicate.py` (`pool_size=1`) |
| SQL injection | Tampering | SQLAlchemy bound parametrlari; `text()` ichida f-string TAQIQ; ruff `S608` | `ruff` qoidasi + code review |
| `SECURITY DEFINER` funksiyada `search_path` hijacking | Elevation of Privilege | `SET search_path = pg_catalog, public` har bir funksiyada | `test_security_definer_functions_pin_search_path` |
| Audit jurnalini insider tomonidan o'chirish | Repudiation | REVOKE + RLS + 2 trigger (**egaga qarshi ham tekshirildi**) | `test_audit_immutable.py` |
| Auditni chetlab o'tuvchi xom SQL | Repudiation | DB-trigger (D-10) | `test_raw_sql_is_audited` (**empirik tasdiqlangan**) |
| Triggerlarni `session_replication_role` bilan o'chirish | Tampering | App-rolga ruxsat yo'q — `ERROR: permission denied to set parameter` (**tekshirildi**) | `test_app_cannot_disable_triggers` |
| JWT `alg` almashtirish / `none` | Spoofing | `algorithms=["HS256"]` aniq; PyJWT 2.13 `alg` bog'lash tuzatishi | `test_jwt_alg_confusion` |
| O'g'irlangan refresh token 30 kun ishlaydi | Spoofing | Rotatsiya + reuse detection → oila bekor qilinadi | `test_refresh_reuse_detection` |
| XSS orqali token o'g'irlash | Spoofing | Refresh httpOnly cookie'da; access faqat xotirada (localStorage EMAS) | Code review |
| CSRF `/auth/refresh` ga | Spoofing | `SameSite=Lax` + `Path` cheklovi (A2 — topologiyaga bog'liq) | Deployment qarori |
| Parol brute-force | Spoofing | Valkey rate-limit (telefon + IP kesimida); Argon2id sekinligi | `test_login_rate_limit` |
| Foydalanuvchi sanab chiqish (enumeration) | Information Disclosure | Login xatosi har doim bir xil ("telefon yoki parol noto'g'ri"); vaqt farqi minimallashtirilgan (topilmasa ham dummy verify) | `test_login_no_user_enumeration` |
| Mavjudlikni 403 orqali tasdiqlash | Information Disclosure | Cross-tenant → **404**, 403 emas | `test_cross_tenant.py` assert 404 |

---

## Sources

### Primary (HIGH confidence)

**Empirik o'lchov — `postgres:18.4-trixie` konteyneri (2026-07-29, 6 ta skript):**
- `current_setting(..., true)` NULL vs `''` xulqi va `''::uuid` xatosi
- `timezone(text, timestamptz)` volatility = `i` (IMMUTABLE) → generated column ruxsati
- `FORCE ROW LEVEL SECURITY` superuser'ga ta'sir qilmasligi; superuser bo'lmagan egaga ta'sir qilishi
- `BYPASSRLS` roli xulqi; `pg_roles` meta-test so'rovi
- `WITH CHECK` cross-tenant INSERT/UPDATE ni bloklashi
- Composite FK cross-tenant havolani bloklashi
- Migratsiya qopqoni (`UPDATE 0`) va `SET LOCAL row_security = off` ning ishlamasligi
- `audit_log` o'zgarmasligining 4 qatlami (app-rol, ega, TRUNCATE)
- Xom SQL audit trigger orqali ushlanishi; no-op UPDATE shovqinsizligi
- `session_replication_role` ni app-rol o'zgartira olmasligi
- `public` sxemada `CREATE` huquqi (PG18 default) va yangi jadval ACL'i
- Login bootstrap: `SECURITY DEFINER` + `search_path` pin, tenant-kontekstsiz ishlashi
- `UNIQUE(market_id, stall_id, business_date)` + `ON CONFLICT DO NOTHING` idempotentligi
- `uuidv7()` / `uuid_extract_timestamp()` mavjudligi

**Empirik o'lchov — SQLAlchemy 2.0.51 + asyncpg 0.31.0 (`pool_size=1`):**
- Tenant kontekstining tranzaksiya bilan chegaralanishi va pool'da `''` qolishi
- `SET LOCAL app.x = :param` → `PostgresSyntaxError` (bind parametr qabul qilinmaydi)
- `exec_driver_sql("%s")` → asyncpg paramstyle nomuvofiqligi
- `after_begin` event listener orqali avtomatik tenant o'rnatish (ishlaydi)
- Exception → rollback → keyingi tranzaksiya toza

**Empirik o'lchov — kutubxonalar:**
- `alembic-utils 0.8.8` + `alembic 1.18.5` mosligi; `PGPolicy.to_sql_statement_create()` chiqishi
- `alembic init -t async` shabloni mavjudligi va `run_sync` naqshi

**Registry tekshiruvlari (2026-07-29):**
- PyPI JSON API — fastapi 0.140.13, sqlalchemy 2.0.51, alembic 1.18.5, alembic-utils 0.8.8 (2025-04-10), asyncpg 0.31.0, PyJWT 2.13.0, pwdlib 0.3.0, phonenumbers 9.0.35, structlog 26.1.0, testcontainers 4.15.0
- npm registry API — next 16.2.12, next-intl 4.13.4 (peer `next ^16.0.0`), react 19.2.8, typescript `latest`=7.0.2, @tanstack/react-query 5.101.4, zod 4.4.3, @eloqnt/cli 0.5.4 (yaratilgan 2026-06-17, `license: None`)
- `slopcheck scan` — pypi (29 paket) va npm (22 paket) ekotizimlarida alohida

**Rasmiy hujjatlar:**
- https://next-intl.dev/docs/routing/middleware — `proxy.ts` (Next 16), matcher
- https://next-intl.dev/docs/routing/configuration — `localePrefix {mode, prefixes}`, `localeDetection`, `localeCookie` (`NEXT_LOCALE`), `alternateLinks`
- https://next-intl.dev/docs/getting-started/app-router/with-i18n-routing — `defineRouting`, `createNavigation`, `getRequestConfig`, `setRequestLocale`
- https://next-intl.dev/docs/workflows/typescript — `AppConfig` augmentation (4.x)
- https://next-intl.dev/docs/workflows/messages — `@eloqnt/cli` tavsiyasi
- https://pyjwt.readthedocs.io/en/stable/changelog.html — 2.10→2.13 o'zgarishlari (`sub`/`jti` validatsiyasi, `iss` tipi, kalit uzunligi, `alg` bog'lash)
- https://frankie567.github.io/pwdlib/ — `PasswordHash.recommended()`, `verify_and_update`
- https://olirice.github.io/alembic_utils/api/ — entity ro'yxati va `register_entities`
- https://github.com/olirice/alembic_utils/blob/master/src/alembic_utils/pg_policy.py — `PGPolicy` faqat CREATE/DROP POLICY
- https://testcontainers-python.readthedocs.io/en/latest/modules/postgres/README.html — `PostgresContainer(image, driver=...)`
- https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html — Argon2id parametrlari

**Loyiha hujjatlari:**
- `CLAUDE.md` — qulflangan stek, versiyalar, taqiqlar
- `.planning/phases/01-.../01-CONTEXT.md` — D-01…D-16
- `.planning/research/ARCHITECTURE.md` — Pattern 4 (multi-tenant), Pattern 8 (audit), Anti-Pattern 7/10, Build Order
- `.planning/research/PITFALLS.md` — P8 (UTC/Tashkent), P9 (tenant leak), M10 (audit teshiklari), M12 (tarif snapshot), Security Mistakes, "Looks Done But Isn't"
- `SBOZOR-MVP-texnik-topshiriq.md` — §3 rollar, §5 arxitektura, §6 ma'lumotlar modeli, §7 UI/i18n

### Secondary (MEDIUM confidence)
- PostgreSQL pgsql-hackers arxivi — "Transaction local custom settings set to '' rather than removed entirely after transaction ends" (rasmiy o'lchov bilan mustaqil tasdiqlandi)
- OWASP ASVS 5.0 bo'lim ro'yxati — bir nechta ikkilamchi manba (securecodinghub, sentrixhub, arc42) bir xil raqamlashni beradi
- FastAPI refresh token / CSRF amaliyoti — bir nechta jamoa manbai; `SameSite`+`Path` yondashuvi standart, lekin topologiyaga bog'liq (A2)
- Docker Compose healthcheck naqshlari (`pg_isready`, `valkey-cli ping` + `depends_on: condition: service_healthy`)

### Tertiary (LOW confidence — validatsiya kerak)
- O'zbek lotin↔kirill transliteratsiya qoidalari to'plami (`e`→`э`/`е`, `ts`→`ц`, apostrof variantlari) — akademik maqolalar (arxiv 2101.05162, CEUR Vol-3315) va amaliy manbalardan; **`overrides.json` lug'ati Karmana kontentida qo'lda tekshirilishi kerak**
- O'zR shaxsiy ma'lumotlar qonuni bo'yicha audit retention muddati — **yurist tasdig'i kerak** (Open Question 5)

---

## Metadata

**Confidence breakdown:**

| Soha | Daraja | Sabab |
|------|--------|-------|
| Postgres RLS mexanikasi | **HIGH** | 6 ta skript jonli `postgres:18.4-trixie` da bajarildi; har bir da'vo o'lchangan natijaga tayanadi |
| SQLAlchemy async + asyncpg integratsiyasi | **HIGH** | Haqiqiy engine + pool bilan 8 ta stsenariy o'lchandi |
| Audit dizayni (FOUND-03) | **HIGH** | Trigger, o'zgarmaslik va xom-SQL qamrovi empirik tasdiqlandi |
| `business_date` / pul (FOUND-05) | **HIGH** | Generated column, volatility, chegara xulqi va idempotentlik o'lchandi |
| Login bootstrap naqshi (FOUND-01) | **HIGH** | To'liq oqim (muammo + yechim + D-06 bypass yo'qligi) empirik tasdiqlandi |
| Kutubxona versiyalari | **HIGH** | PyPI/npm registrylardan 2026-07-29 da; CLAUDE.md bilan to'liq mos |
| `alembic-utils` mosligi | **HIGH** (bugun) / **MEDIUM** (kelajak) | Import + SQL generatsiya tekshirildi; oxirgi reliz 15 oy oldin |
| next-intl 4.13 + Next 16 konfiguratsiyasi | **MEDIUM-HIGH** | Rasmiy hujjatdan olindi; `localePrefix` shakli ikki manbadan kesib tekshirildi (birinchi javob noto'g'ri edi). Loyihada hali ishga tushirilmagan |
| Transliteratsiya qoidalari (D-14) | **MEDIUM** | Mapping akademik manbalardan; noaniqlik to'plami real kontentda sinalmagan |
| CSRF / cookie topologiyasi | **MEDIUM** | Deployment topologiyasiga bog'liq (Open Question 3) |
| Huquqiy talablar (retention) | **LOW** | Yurist tasdig'i kerak |

**Research date:** 2026-07-29
**Valid until:** 2026-08-28 (30 kun) — istisno: `next` va `next-intl` tez harakatlanadi, ular uchun **2026-08-12** (14 kun); `alembic-utils` holati har fazada qayta ko'rilsin
