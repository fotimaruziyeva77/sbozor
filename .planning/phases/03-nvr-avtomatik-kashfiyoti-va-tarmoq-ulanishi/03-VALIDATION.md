---
phase: 3
slug: nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi
status: automated-green-human-items-scheduled
nyquist_compliant: true
wave_0_complete: true
created: 2026-08-03
measured: 2026-08-03
updated: 2026-08-03
human_only_verifications:
  - item: "Real Hikvision NVR'da kashfiyot (XML shakli va kanal raqamlash chetlanishi)"
    why_not_automatable: "Simulyator MODUL darajasida ishonchli, lekin real firmware'ning kutilmagan XML shakli faqat qurilmada chiqadi. Sim'ni real qurilmaning nusxasi deb e'lon qilish aynan Pitfall 4 — simulyatorning o'zini o'zi tasdiqlashi."
    owner: "Bozor admini (rekvizit beradi) + ijrochi (zondni ishga tushiradi)"
    trigger: "NVR kirish ma'lumotlari kelgan kun; tartib ops/docs/nvr-onboarding.md §4 da"
  - item: "CGNAT ostidagi WireGuard tunnelining ko'tarilishi"
    why_not_automatable: "Bozor tomonidagi ISP topologiyasini (CGNAT, NAT o'tish, keepalive) simulyatsiya qilib bo'lmaydi — u tarmoq operatorining xulqiga bog'liq."
    owner: "Ops"
    trigger: "Bozor tomonidagi qurilma o'rnatilganda"
  - item: "ip route get <nvr_ip> javobi wg0 interfeysini ko'rsatishi (SC#5 ning 3-da'vosi)"
    why_not_automatable: "CI konteynerida wg0 interfeysi umuman yo'q. Bunday test har doim «tunnel uzilgan» shoxidan o'tib yashil bo'lardi va HECH NIMA isbotlamasdi (Pitfall 10)."
    owner: "Ops"
    trigger: "VPS deploy'idan keyin, go-live checklist'ining bandi sifatida"
  - item: "Bir vaqtdagi RTSP sessiya limitining HAQIQIY qiymati (D-05)"
    why_not_automatable: "Chegara firmware va bitreytga bog'liq. Simulyatorda ikkala stsenariy (reject/silent) modellashtirilgan, lekin sonning O'ZI faqat qurilmada o'lchanadi."
    owner: "Ops"
    trigger: "Real NVR ulanganda; vositasi verify-real-nvr.sh ning rtsp.concurrent_failed maydoni"
  - item: "Jonli tasvirning sifati va kechikishi (idrok o'lchovi)"
    why_not_automatable: "Perseptual baho — real tarmoq, real kamera, real ekran. jsdom RTCPeerConnection bermaydi, ya'ni videoning O'ZI birorta avtomatik testda ijro etilmaydi."
    owner: "Direktor (baholovchi) + frontend egasi (yozib boruvchi)"
    trigger: "Pilot tayyorgarligi haftasi"
  - item: "Vendored video-stream.js va video-rtc.js kodining odam tomonidan ko'rilishi"
    why_not_automatable: "Uchinchi tomon kodini birinchi kiritishda odam o'qishi shart (eval, new Function, tashqi fetch, obfuskatsiya). SHA-256 qulfi faylning O'ZGARMASLIGINI kafolatlaydi, XAVFSIZLIGINI emas."
    owner: "Ijrochi"
    trigger: "03-08 T3 da bajarildi; keyingi versiyaga ko'tarilganda takrorlanadi"
automated_replacements:
  - was: "Faza mezonlarini hujjatdan qo'lda o'qib «bajarildimi?» deb baholash"
    now: "npm run test:sim  (tests/integration/test_phase3_criteria.py — SC#1...SC#8 + meta-test)"
  - was: "Real NVR javoblarini qo'lda curl bilan olib fixture'lar bilan ko'z bilan solishtirish"
    now: "ops/scripts/verify-real-nvr.sh <url> <login> <parol>  (chiqishi JSON)"
  - was: "«hardware markeri darvozaga tushib qolmaganini» ko'z bilan tekshirish"
    now: "docker compose --profile test run --rm tests pytest --collect-only -m hardware"
  - was: "nyquist_compliant bayrog'ini kelishuv bilan qo'lda qo'yish"
    now: "npm run validation:check -- .planning/phases/03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi/03-VALIDATION.md"
  - was: "Talab holatini checkbox ro'yxati va Traceability jadvalida qo'lda sinxronlash"
    now: "npm run requirements:check"
open_items:
  - "TO'LQIN DARAJASIDAGI KECHIKISH (egasi: 4-FAZA). Chegara o'lchov bilan belgilandi, lekin u KATTA va sabab strukturaviy: `npm run test` `npm run test:tenancy` va `npm run test:sim` ning testlarini QAYTA bajaradi (testpaths=[\"tests\"] hammasini qamraydi). Batafsil raqamlar va taklif «Kechikish bandining yopilishi» bo'limida."
  - "JONLI OQIM SIM USTIDA ISTE'MOL QILINMAYDI (egasi: 4-FAZA). `go2rtc-sim` haqiqiy RTSP test-oqimlarini beradi, lekin birorta test undan kadr olmaydi — CAM-03 va CAM-09 aynan shu sababdan `Blocked`. Yopilish yo'li: `-m sim` ostida go2rtc-sim'dan bitta kadr olib JPEG ekanini tekshirish (4-fazaning kadr olish yo'li bilan bir xil mexanizm)."
  - "AUDIT HAJMI QABUL QILINDI (egasi: 4-FAZA, past ustuvorlik). `cameras.last_seen_at` har skanda va jonli ko'rish har yangilanishda `audit_log` ga qator yozadi. O'lchov: Karmana miqyosida (25 kamera) kuniga ~75 qator, yiliga ~27k qator ~14 MB — 400 GB diskda ahamiyatsiz. Remediatsiya (ustun bilan cheklangan trigger) MA'LUM va arzon, lekin u `migrations/helpers.py` ni va BARCHA audit ostidagi jadvallarni o'zgartiradi. Qayta ochish sharti: skan CRON'ga o'tganda (4-faza) yoki bozorlar soni o'ntadan oshganda."
  - "Go2rtcClient.remove_stream CHAQIRILMAYDI va bu QABUL QILINDI. Qoldiq ta'sir o'lchangan va chegaralangan: arxivlangan kamera `POST /cameras/{id}/live-token` dan 404 oladi (`test_live_view.py::test_archived_camera_has_no_live_token`), ya'ni YANGI oqim ochilmaydi; go2rtc ro'yxati XOTIRADA yashaydi va servis qayta ishga tushganda yo'qoladi; `rtsp_url()` parolni umuman olmaydi, ya'ni yetim yozuvda sir yo'q. Arxivlash yo'liga tarmoq chaqiruvini qo'shish uni go2rtc ning MAVJUDLIGIGA bog'lardi — yomonroq savdo. To'g'ri shakl — 4-fazada reconciliation (faol kameralar ro'yxati bilan go2rtc oqimlarini davriy moslashtirish)."
---

# Phase 3 — Validation Strategy

> Fazani ijro qilish davomida teskari aloqa namunasini olish uchun validatsiya kontrakti.
> **Manba:** `03-RESEARCH.md` § `Validation Architecture`, `03-UI-SPEC.md` darvozalari (G-1…G-8), `03-PATTERNS.md` §5 (Wave 0).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 (`asyncio_mode=auto`) · vitest (frontend) · `node:test` (skript darvozalari) |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`) · `frontend/vitest.config.ts` |
| **Quick run command** | `npm run gate:fast` (`03-01` da yaratiladi) |
| **Full suite command** | `npm run gate` (`test:sim` bilan — `03-02` da zanjirga qo'shiladi) |
| **Slow lane** | `npm run test:sim:slow` (`-m "sim and slow"`) — D-09 ning 25 kanalli stsenariysi; `gate` dan **ataylab tashqarida**, faza yopilishidan oldin bir marta bajariladi |
| **Estimated runtime** | **ESKI RAQAMLAR O'CHIRILMAYDI — o'sish byudjet muhokamasi uchun kerak.**<br>**03-01 (2026-08-03):** `gate` 515 / 502 / 496 s · `gate:fast` 32 / 32 / 31 s (1021 backend + 322 tenancy + 60 node + 74 vitest).<br>**03-11 (2026-08-03, faza to'liq):** `gate` **1000 / 994 / 983 s** · `gate:fast` **75 / 71 / 72 s** (1457 backend + 86 node + 246 vitest). Qadam kesimidagi taqsimot va 31 % qayta bajarish topilmasi — «Kechikish bandining yopilishi» bo'limida |

**Yangi infratuzilma (bu fazada tug'iladi):**

| Komponent | Nima uchun | Qaysi rejada |
|---|---|---|
| `--profile sim` (Hikvision NVR simulyatori) | CAM-09 — real uskunasiz uchidan-uchiga isbot | **03-02** |
| `taskiq` worker konteyneri | D-06 — loyihaning birinchi fon job'i | paketlar **03-01**, konteyner **03-06** |
| ISAPI fixture'lari (`DS-7616NI-K2`, `DS-7732NI-M4`) | D-04 — **real yozib olingan dumplar**, o'ylab topilgan XML emas | **03-02** |
| `sim`, `slow` va `hardware` pytest markerlari | `--strict-markers` ostida majburiy; `slow` — D-09 ning to'g'ridan-to'g'ri talabi | **03-01** |
| `gate:fast` tez yo'li | Task darajasidagi teskari aloqa ≤180 s | **03-01** |

---

## Sampling Rate

- **Har task commitidan keyin:** `npm run gate:fast` (backend unit + frontend vitest)
- **Har to'lqindan keyin:** `npm run gate` (lint + mypy + backend + tenancy + **sim** + i18n + vitest + typecheck + eslint + build)
- **`/gsd-verify-work` dan oldin:** to'liq to'plam yashil
- **Task darajasidagi maksimal kechikish:** **180 s** (`gate:fast`)
- **To'lqin darajasidagi maksimal kechikish:** **o'lchov bilan belgilanadi** — quyidagi jadvalga qarang

### Kechikish bandining yopilishi (2-fazadan meros)

2-fazada to'lqin darajasidagi kechikish **225 s** o'lchandi, chegara esa 180 s edi — ya'ni band **ochiq** qoldi. Bu fazada `--profile sim` yana ikkita konteyner qo'shadi, ya'ni jimgina chegaradan oshib ketish **kafolatlangan** bo'lardi.

**Qaror (03-01 da bajariladi, 03-11 da yakunlanadi):** kechikish **ikki lentaga** ajratiladi.

| Lenta | Buyruq | Nimani qamraydi | Chegara |
|-------|--------|-----------------|---------|
| **Tez** (task) | `npm run gate:fast` | `pytest tests/unit` + `npm --prefix frontend test` | **180 s** — o'zgarmaydi |
| **To'liq** (to'lqin) | `npm run gate` | butun zanjir, `test:sim` bilan | **o'lchangan eng yomon qiymat + 20 %** |

#### 03-01 dagi oraliq o'lchov (tarix — O'CHIRILMAYDI)

| O'lchov | Sovuq kesh | Issiq #1 | Issiq #2 | Eng yomon | O'sha kungi chegara |
|---------|-----------|----------|----------|-----------|---------------------|
| `npm run gate:fast` | 32 s | 32 s | 31 s | 32 s | 180 s ✅ |
| `npm run gate` | 515 s | 502 s | 496 s | 515 s | nomzod 618 s (`test:sim` QO'SHILMASDAN OLDIN) |

#### YAKUNIY O'LCHOV (2026-08-03, `03-11`, faza to'liq yig'ilgan holatda)

| O'lchov | Sovuq kesh | Issiq #1 | Issiq #2 | Eng yomon | **Belgilangan chegara** |
|---------|-----------|----------|----------|-----------|-------------------------|
| `npm run gate:fast` | **75 s** | **71 s** | **72 s** | **75 s** | **180 s** ✅ (2.4× zaxira) — **KO'TARILMADI** |
| `npm run gate` | **1000 s** | **994 s** | **983 s** | **1000 s** | **1200 s** (1000 + 20 %) |

Oltala o'lchovning ham har bir qadami `exit 0`. «Sovuq kesh» — `frontend/.next` va `frontend/node_modules/.vite` o'chirilgandan keyingi birinchi yugurish; «issiq» — undan keyingi ketma-ket ikkitasi. Test sanog'i: **1457** backend (shundan 412 tenancy, 70 sim) + **86** node:test + **246** vitest + i18n **576 × 3**.

#### Qaysi qadam qancha turadi (eng yomon qiymat bo'yicha)

| Qadam | Eng yomon | Ulush | Nima qiladi |
|---|---:|---:|---|
| `npm run test` | **557 s** | **56 %** | `pytest -q` — **butun** to'plam (`testpaths = ["tests"]`) |
| `npm run test:tenancy` | **249 s** | **25 %** | `pytest tests/tenancy` — **412 test, yuqoridagi 557 s ICHIDA ALLAQACHON bajarilgan** |
| `npm run test:sim` | **67 s** | 7 % | `pytest tests/integration -m "sim and not slow"` — **70 test, u ham 557 s ichida** |
| `npm --prefix frontend test` | 48 s | 5 % | 246 vitest + 86 node:test |
| `npm --prefix frontend run build` | 38 s | 4 % | `next build`, uch til uchun prerender |
| `npm --prefix frontend run lint` | 22 s | 2 % | eslint + React Compiler qoidalari |
| `npm --prefix frontend run typecheck` | 16 s | 2 % | `tsc --noEmit` |
| `npm run lint` | 14 s | 1 % | ruff + `ruff format --check` + mypy |
| `npm --prefix frontend run i18n:check` | 2 s | 0 % | parity darvozasi |

#### ⚠ TOPILMA: darvozaning 31 % i — QAYTA BAJARISH

`npm run test` (`pytest -q`) `pyproject.toml` dagi `testpaths = ["tests"]` tufayli **`tests/tenancy` va `tests/integration` ni ham** qamraydi. O'lchandi (`--collect-only`):

```
pytest                                      -> 1457 test
pytest tests/tenancy                        ->  412 test  (yuqoridagi 1457 ning QISMI)
pytest tests/integration -m "sim and not slow" ->  70 test  (yuqoridagi 1457 ning QISMI)
```

Ya'ni zanjirdagi `test:tenancy` (**249 s**) va `test:sim` (**67 s**) — jami **316 s**, darvozaning **31 % i** — allaqachon bajarilgan testlarni **ikkinchi marta** yangi konteynerda va yangi Postgres testcontainer'ida bajaradi.

**Bu reja uni TUZATMADI va sabab ochiq aytiladi.** Tuzatish `package.json` dagi `gate` zanjirini o'zgartirishni talab qiladi, bu esa (a) shu rejaning `<threat_model>` ida `git diff --exit-code package.json` bilan qulflangan va (b) sof tejash emas — ikkita haqiqiy xususiyat yo'qoladi:

1. **`test:sim` zanjirdan `sim:up --wait` ni olib keladi.** Usiz sim konteynerlari ko'tarilmagan holatda `npm run test` sim testlarini **JIMGINA SKIP** qilardi (`fixtures/nvr_sim.py` ning dev qoidasi) va SC#7 ning qamrovi ambient holatga bog'lanib qolardi — bu aynan T-03-10.
2. **`test:tenancy` ning NOMLANGAN signali.** Yiqilganda «tenant izolyatsiyasi buzildi» xabari darhol ko'rinadi; umumiy to'plam ichida u boshqa yuzta xato orasida yo'qolardi.

**Taklif (egasi: 4-FAZA, `03-VALIDATION.md` `open_items` da qayd etilgan):** `sim:up` ni zanjirning BOSHIGA chiqarish va `gate` dan `test:tenancy` bilan `test:sim` ni olib tashlash — **~316 s (31 %)** tejaydi va qamrovni **umuman kamaytirmaydi**. Ikkala buyruq ham mustaqil yorliq sifatida QOLADI (`npm run test:tenancy` — nosozlikni lokalizatsiya qilish uchun).

> ⚠ **Jimgina oshib ketish qabul qilinmadi.** Chegara 618 s dan 1200 s ga **ko'tarildi**, lekin sababsiz emas: yuqoridagi jadval har qadamning narxini sanaydi, o'sishning **31 % i** nomlangan va uni yopish yo'li taklif bilan yozilgan. Qolgan o'sish — fazaning O'Z hajmi: backend 1021 → **1457** test (+43 %), vitest 74 → **246** (+232 %), i18n 574 → **576** kalit × 3 til, ustiga `--profile sim` ning ikkita konteyneri.
>
> ✅ **2-fazadan meros qolgan 225 s / 180 s bandi YOPILDI.** Ikki lentaga ajratish ishladi: task darajasidagi `gate:fast` **75 s** — 180 s chegarasiga **2.4× zaxira** bilan sig'adi va chegara **KO'TARILMADI**. To'lqin darajasidagi `gate` esa o'z chegarasini o'lchovdan oladi.
>
> ⚠ **`gate:fast` ning zaxirasi 5.6× dan 2.4× ga tushdi** (32 s → 75 s) va bu ham **topilma**. Sababning yarmi frontendda: `fast:fe:vitest` 46–52 s (246 vitest, ularning bir qismi soxta taymer bilan ishlaydigan DOM testlari), backend unit esa 23–27 s. Bugun band emas, lekin trend aniq — 4-fazada `gate:fast` ham kuzatilsin.

---

## Per-Task Verification Map

*Har PLAN.md taski uchun bitta qator. `Status` ustunini ijrochi to'ldiradi (`03-11` Task 3).*

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| T03-01-1 | 03-01 | 1 | CAM-08, CAM-09 | T-03-01, T-03-06, T-03-SC | Prod image ISAPI klientini import qila oladi; `redis` pini pasaymaydi; `sim`/`slow`/`hardware` markerlari e'lon qilingan (D-09) | unit | `pytest tests/unit/test_runtime_deps.py -q` | ✅ 15 test | ✅ green |
| T03-01-2 | 03-01 | 1 | CAM-01, CAM-03 | T-03-02, T-03-03, T-03-04 | Platforma admini kamera ko'radi va boshqaradi; direktor faqat ko'radi; NVR paroli maskalanadi | unit | `pytest tests/unit/test_rbac_matrix.py tests/unit/test_logging.py -q` | ✅ 18 + 25 test | ✅ green |
| T03-01-3 | 03-01 | 1 | CAM-08 | T-03-05, T-03-18 | Yangi tenant jadvali kaskaddan tushib qolsa CI qizaradi | integration | `pytest tests/integration/test_market_delete_guard.py -q` | ✅ 4 test | ✅ green |
| T03-02-1 | 03-02 | 2 | CAM-09 | T-03-09 | Sim haqiqiy RFC 7616 `response` ni hisoblab tekshiradi; noto'g'ri parol o'tmaydi | lint+type | `ruff check services/nvr-sim && mypy services/nvr-sim` | ✅ mavjud | ✅ green |
| T03-02-2 | 03-02 | 2 | CAM-09 | T-03-11, T-03-31 | Fixture'lar real dumpdan; namespace va manba izohi mavjud; **sessiya limiti D-05 ning ikkala shaklida** (`reject` / `silent`) modellashtirilgan | unit | `pytest tests/unit/test_sim_fixtures.py -q` + `grep -n stream_claims services/nvr-sim/sim/isapi.py` | ✅ mavjud | ✅ green |
| T03-02-3 | 03-02 | 2 | CAM-09 | T-03-07, T-03-08, T-03-10, T-03-12 | Sim prodga chiqmaydi; ilova kodida sim tarmoqlanishi yo'q; CI'da skip emas; sekin lenta (`test:sim:slow`) standart zanjirdan ajratilgan | unit + integration (sim) | `pytest tests/unit/test_no_sim_branching.py -q` va `npm run test:sim` | ✅ mavjud | ✅ green |
| T03-03-1 | 03-03 | 2 | CAM-01, CAM-08 | T-03-13, T-03-14 | `rtsp_url` ustuni yo'q; `nvr_credentials` auditdan tashqarida; reyestrlar to'liq | type + import | `ruff check . && mypy .` + model import assert'lari | ✅ mavjud | ✅ green |
| T03-03-2 | 03-03 | 2 | CAM-01, CAM-08 | T-03-14, T-03-16, T-03-19 | To'rt jadval RLS ENABLE+FORCE va policy bilan; qisman UNIQUE indekslar | migration + tenancy | `alembic upgrade head` + `npm run test:tenancy` | ✅ mavjud | ✅ green |
| T03-03-3 | 03-03 | 2 | CAM-08 | T-03-15, T-03-17, T-03-18 | Faol bozorni DB darajasida o'chirib bo'lmaydi; kanal noyobligi 23505 beradi | integration + tenancy | `pytest tests/integration/test_market_delete_guard.py tests/tenancy/test_nvr_domain_meta.py -q` | ✅ mavjud | ✅ green |
| T03-04-1 | 03-04 | 3 | CAM-01 | T-03-20, T-03-21, T-03-22 | Parol Fernet bilan shifrlanadi; kalit muhitda; rotatsiya ikki yo'nalishda | unit | `pytest tests/unit/test_nvr_secrets.py -q` | ✅ mavjud | ✅ green |
| T03-04-2 | 03-04 | 3 | CAM-02, CAM-08 | T-03-23, T-03-24, T-03-25 | Ommaviy IP rad etiladi; hostname qabul qilinadi; URL parol qabul qilmaydi | unit | `pytest tests/unit/test_rtsp_url.py tests/unit/test_nvr_host_validation.py -q` | ✅ mavjud | ✅ green |
| T03-04-3 | 03-04 | 3 | CAM-08 | T-03-26, T-03-27, T-03-28 | Upsert idempotent; `DELETE` yo'q; `error_detail` maskalanadi | integration | `pytest tests/integration/test_nvr_repo.py -q` | ✅ mavjud | ✅ green |
| T03-05-1 | 03-05 | 4 | CAM-08 | T-03-30, T-03-32, T-03-34 | Parser namespace bilan ishlaydi va jimgina bo'sh natija bermaydi; `detail` allowlist ostida | unit | `pytest tests/unit/test_isapi_parser.py tests/unit/test_isapi_errors.py -q` | ✅ mavjud | ✅ green |
| T03-05-2 | 03-05 | 4 | CAM-08 | T-03-29, T-03-31, T-03-32, T-03-33, T-03-35, T-03-36 | `401` qayta urinilmaydi (`attempts == 1`); drift `401` dan oldin (`attempts == 0`); **`nvr_stream_limit` ikkala stsenariyda** va **`nvr_tls_untrusted` transport darajasida** o'lchanadi — o'n ikkala koddan o'n bittasi shu faylda | integration (sim) | `npm run test:sim` (`test_nvr_errors.py`) | ✅ mavjud | ✅ green |
| T03-05-3 | 03-05 | 4 | CAM-08 | T-03-26, T-03-27 | Kashfiyot idempotent; yo'qolgan kanal `offline`; RTSP porti kashf etiladi; `channel_offline` (12-kod) shu yerda; **D-09 ning 25 kanalli sekin testi** | integration (sim) + slow | `npm run test:sim` va `npm run test:sim:slow` (`test_nvr_discovery.py`) | ✅ mavjud | ✅ green |
| T03-06-1 | 03-06 | 5 | CAM-08 | T-03-38, T-03-42 | Job tenant kontekstini o'zi o'rnatadi; navbat kutubxonasi faqat `worker.py` da | lint+type+grep | `ruff check . && mypy .` + `grep -c taskiq app/jobs/discovery.py` = 0 | ✅ mavjud | ✅ green |
| T03-06-2 | 03-06 | 5 | CAM-01, CAM-08 | T-03-37, T-03-39, T-03-44 | Javob modelida parol yo'q; `market_id` tanadan olinmaydi; `test-connection` rate-limit ostida | tenancy + type | `pytest tests/tenancy/test_route_coverage.py -q` + model assert'lari | ✅ mavjud | ✅ green |
| T03-06-3 | 03-06 | 5 | CAM-01, CAM-08 | T-03-37, T-03-38, T-03-40, T-03-41, T-03-43 | 202 → poll → succeeded zanjiri; 409 + `run_id`; cross-tenant 404 | integration (sim) | `npm run test:sim` (`test_nvr_discovery_job.py`) + `pytest tests/integration/test_nvr_api.py -q` | ✅ mavjud | ✅ green |
| T03-07-1 | 03-07 | 6 | CAM-01, CAM-03 | T-03-50, T-03-53 | `DELETE` marshruti yo'q; javob modelida `stream_name`/`rtsp_url` yo'q | tenancy | `pytest tests/tenancy/test_camera_route_coverage.py -q` | ✅ mavjud | ✅ green |
| T03-07-2 | 03-07 | 6 | CAM-03 | T-03-45, T-03-47, T-03-48, T-03-54 | `src` faqat `rtsp://`; go2rtc API nginx'da 403; token auditoriyasi ajratilgan | unit + config | `pytest tests/unit/test_go2rtc_client.py -q` + `nginx -t` | ✅ mavjud | ✅ green |
| T03-07-3 | 03-07 | 6 | CAM-02, CAM-03 | T-03-46, T-03-49, T-03-51, T-03-52 | `AllowedIPs` da `0.0.0.0/0` yo'q; jonli ko'rish auditda; 403 jurnalga yozmaydi | unit + integration | `pytest tests/unit/test_wireguard_config.py tests/integration/test_live_view.py -q` | ✅ mavjud | ✅ green |
| T03-08-1 | 03-08 | 7 | CAM-01, CAM-08 | T-03-61 | Kirill hosilasi defektsiz; akronim va `ts` birikmasi qulflangan | node:test + i18n | `npm --prefix frontend run i18n:check && node --test frontend/scripts/gen-cyrillic.test.mjs` | ✅ mavjud | ✅ green |
| T03-08-2 | 03-08 | 7 | CAM-01, CAM-03 | T-03-57, T-03-58, T-03-60 | Kesh kalitlari `market_id` bilan doiralangan; parol keshga tushmaydi; poll chegaralangan | typecheck + vitest | `npm --prefix frontend run typecheck && npm --prefix frontend test` | ✅ mavjud | ✅ green |
| T03-08-3 | 03-08 | 7 | CAM-01, CAM-03 | T-03-55, T-03-56, T-03-61, T-03-62 | G-1…G-7 darvozalari; vendored pleyer SHA-256 bilan qulflangan — **qat'iy talab**, ikkita ekvivalent olish yo'li (git tegi yoki `alexxit/go2rtc:1.9.14` image'idan `docker cp`) | node:test | `node --test frontend/scripts/{error-codes,nvr-copy,vendor-integrity}.test.mjs` | ✅ mavjud | ✅ green |
| T03-09-1 | 03-09 | 8 | CAM-01, CAM-08 | T-03-68 | Sahifa huquq bilan darvozalangan; bitta birlamchi tugma; `?run=` tiklanadi | typecheck + build | `npm --prefix frontend run typecheck && npm --prefix frontend run build` | ✅ mavjud | ✅ green |
| T03-09-2 | 03-09 | 8 | CAM-01 | T-03-63, T-03-65, T-03-67 | Manzil ajratiladi; parol keshga tushmaydi; auth qulfi faqat rekvizit o'zgarganda ochiladi | vitest | `npm --prefix frontend test -- nvr-form` | ✅ mavjud | ✅ green |
| T03-09-3 | 03-09 | 8 | CAM-01, CAM-08 | T-03-63, T-03-64, T-03-66 | Sabab va tuzatish teng og'irlikda; qulflaydigan kodda retry yo'q; `raw` matn sifatida | vitest | `npm --prefix frontend test -- nvr-error-block` | ✅ mavjud | ✅ green |
| T03-10-1 | 03-10 | 9 | CAM-08 | T-03-73, T-03-74 | Uch hisoblagich nol bo'lganda ham ko'rinadi; poll 180 s da to'xtaydi | vitest | `npm --prefix frontend test -- discovery` | ✅ mavjud | ✅ green |
| T03-10-2 | 03-10 | 9 | CAM-08 | T-03-75 | Arxivlash qaytariladigan amal; ulanmagan kamerada sabab aytiladi; «o'chirish» so'zi yo'q | vitest + node:test | `npm --prefix frontend test -- camera-row && node --test frontend/scripts/nvr-copy.test.mjs` | ✅ mavjud | ✅ green |
| T03-10-3 | 03-10 | 9 | CAM-03 | T-03-69, T-03-70, T-03-71, T-03-72 | Oqim faqat aniq bosishdan keyin; 5 daqiqada tugaydi; `stream_name` DOM'da yo'q | vitest | `npm --prefix frontend test -- live-view-dialog` | ✅ mavjud | ✅ green |
| T03-11-1 | 03-11 | 10 | CAM-01, CAM-02, CAM-03, CAM-08, CAM-09 | T-03-76, T-03-77 | Sakkizala mezon bitta zanjirda; SC#1 da `rtsp://` literali yo'q | integration (sim) | `npm run test:sim` (`test_phase3_criteria.py`) | ✅ mavjud | ✅ green |
| T03-11-2 | 03-11 | 10 | CAM-02, CAM-08 | T-03-81 | `hardware` markeri standart zanjirdan tashqarida; runbookda SSH qadami yo'q | collect-only + shell | `pytest -m hardware -q --collect-only && bash -n ops/scripts/verify-real-nvr.sh` | ✅ mavjud | ✅ green |
| T03-11-3 | 03-11 | 10 | CAM-01, CAM-02, CAM-03, CAM-08, CAM-09 | T-03-78, T-03-79, T-03-80 | `nyquist_compliant` hisoblanadi; talablar dalil bilan belgilanadi; `REQUIREMENTS.md` «Faza kesimida» jadvalidagi eskirgan faza nomi va soni **qayta hisoblanadi** | script | `npm run validation:check && npm run requirements:check` | ✅ mavjud | ✅ green |

*Status lug'ati: ✅ green · ❌ red · ⚠️ flaky · ⬜ hali o'lchanmagan.*
**2026-08-03 holati: 33/33 ✅** — barcha qatorlar o'lchandi va yashil.

**Namuna uzluksizligi:** 33 taskning **hammasida** `<automated>` verify bor — ketma-ket uchta avtomatik verifysiz task holati **yo'q**.

### Reja va bajarilgan ish orasidagi farqlar

⚠ **Jadval qatorlari O'CHIRILMADI va QO'SHILMADI** — u rejalashtirilgan namuna bo'lib qoladi. Bajarish davomida topilgan farqlar quyida **alohida** yoziladi; ular `Status` ustuniga ta'sir qilmaydi, chunki har qatorning avtomatik buyrug'i bajarildi va yashil bo'ldi.

| Qator | Farq | Nima qilindi |
|---|---|---|
| T03-01-3 | Kaskad to'liqligi `market_id` USTUNI bo'yicha emas, `markets` ga CHET EL KALITI bo'yicha o'lchanadi | `audit_log` da ustun bor, FK yo'q — ustun bo'yicha izlash darvozani bugunoq yolg'on-qizil qilardi (03-01) |
| T03-02-2 | Rejadagi 5 ta o'rniga **7 ta** fixture olindi | `deviceType=IPCamera` yo'lini sintetik XML bilan qoplash aynan Pitfall 4 bo'lardi (03-02) |
| T03-05-2 | `device_not_supported` sharti «manufacturer BOR VA Hikvision emas» ga o'zgardi | `DS-7732NI-M4` dumpida bu maydon UMUMAN YO'Q — D-09 ning sekin testi topdi (03-05) |
| T03-08-3 · T03-09-* · T03-10-* | Bir necha `grep` qabul mezoni kod bilan ZIDDIYATGA kirdi (`\bcontrols\b`, katalog ustidagi `grep -c`, `\bdisabled=\{`) | Niyat bajarildi, o'lchov yozildi, tuzatilgan naqshlar `03-11-SUMMARY.md` da (03-09, 03-10) |
| T03-11-1 | `pytest -q --collect-only` naqshi bajarilmas | `addopts` da `-q` ALLAQACHON bor, ikkinchisi `-qq` beradi va faqat sanoq qatorini chiqaradi; tuzatilgan naqsh — `-q` siz (`03-11-SUMMARY.md`) |
| T03-11-3 | `npm run validation:check` FAZA ARGUMENTINI olmaydi | Alias 2-fazaning fayliga qadalgan; 3-faza uchun `npm run validation:check -- <yo'l>` ishlatiladi. `package.json` TEGILMADI (T-03-SC) |

**Xato kodlarining qamrovi (SC#3).** `NVR_ERROR_CODES` ning **o'n ikkitasi ham** funksional test bilan qoplangan va bu mexanik tekshiriladi (03-05 T2 ning qabul mezoni har kodni ikki test faylida nomma-nom izlaydi):

| Kod | Qayerda o'lchanadi |
|---|---|
| `nvr_bad_credentials`, `nvr_account_locked`, `nvr_user_no_permission`, `nvr_clock_drift`, `nvr_digest_stale`, `nvr_auth_mode_basic_only`, `nvr_unreachable`, `nvr_isapi_unavailable`, `device_not_supported` | `test_nvr_errors.py` — sim rejimi bilan (9 ta) |
| `nvr_stream_limit` | `test_nvr_errors.py::test_stream_limit_produces_actionable_error` — D-05 ning **ikkala** stsenariysi (`reject` / `silent`) |
| `nvr_tls_untrusted` | `test_nvr_errors.py::test_tls_untrusted_is_diagnosed` — transport darajasida (sim rejimi emas; sabab test docstringida) |
| `channel_offline` | `test_nvr_discovery.py` — `sim_mode("channel_offline", channels=[3,7])` |

---

## Wave 0 Requirements

`03-PATTERNS.md` §5 yetti bandni sanaydi; ulardan uchtasi **jimgina yiqiladigan** turdagi — testlar yashil bo'lgani holda ishlab chiqarish buziladi.

- [x] **W0-1** *(03-01 T1)* — `httpx` ni `[dependency-groups] dev` dan `[project] dependencies` ga ko'chirish. **Aks holda 24 test fayli yashil qoladi va deploy'da import xatosi beradi.** (D-16) — ✅ **O'LCHANDI 2026-08-03:** o'zgarishdan oldingi `--no-dev` runtime image'da `import httpx` → `ModuleNotFoundError: No module named 'httpx'`; keyin → `0.28.1`. Da'vo taxmin emas, ikki image ustida solishtirilgan fakt.
- [x] **W0-2** *(03-01 T2)* — `rbac.py` da `CAMERA_MANAGE` + `PLATFORM_ADMIN` ga `CAMERA_VIEW`/`CAMERA_MANAGE`. Self-service onboarding'da bozorni aynan platforma admini ulaydi, ya'ni u o'zi topgan kameralarni ko'ra olmasdi. (D-15)
- [x] **W0-3** *(03-01 T2)* — `frontend/src/lib/rbac.ts` ko'zgusi **birga** o'zgaradi. Unutish ma'lumot ochmaydi, lekin tugma ko'rinib turib 403 beradigan UI hosil qiladi. — ⚠ **Topilma:** ko'zguni tekshiradigan darvoza MAVJUD EMAS edi (`role-gate.test.mjs` faqat rol YORLIQLARINI solishtirardi). G-8 darvozasi shu rejada yaratildi; usiz sabotaj testi qizarmasdi.
- [x] **W0-4** *(03-01 T2)* — `MARKET_ADMIN` ga `CAMERA_MANAGE`; `DIRECTOR` **olmaydi** (D-07 — o'qish roli).
- [x] **W0-5** *(03-01 T1)* — `pyproject.toml` ga `sim` va `hardware` markerlari (+ `slow` — D-09). `--strict-markers` tufayli marker e'lon qilinmasa `-m sim` yig'ilishda yiqiladi. — ✅ **O'LCHANDI:** e'lon qilinmagan `@pytest.mark.X` → `'X' not found in markers configuration option`, pytest exit **2**; uchala yangi marker esa to'plandi va `-m` bilan filtrlandi.
- [x] **W0-6** *(03-01 T2)* — `SENSITIVE_KEYS` ni **tasdiqlash** (o'zgartirmaslik). ✅ 2026-08-03 da kod o'qildi: `rtsp_password` va `nvr_password` `logging.py:59-61` da allaqachon bor. Bu band **kod o'zgarishini talab qilmaydi** — u ichma-ich `error_detail` holati uchun test bilan o'lchandi (5 test; `git diff --exit-code logging.py` toza). Qoldiq xavf ham qulflandi: **formatlangan matn ichidagi parol maskalanMAYDI** va bu alohida test bilan hujjatlashtirilgan. (D-12)
- [x] **W0-7** — `market_delete_draft()` kaskadi. **IKKIGA BO'LINDI va bu ochiq qayd etiladi** — band bitta rejada bajarilmadi, chunki tartib teskari bo'lsa yashil darvoza sinardi:
  - [x] *(03-01 T3)* **muddatni majburlaydigan darvoza** — `pg_catalog` dan tenant jadvallarini o'qib funksiya tanasi bilan solishtiradi; 03-01 kunida yashil (12 jadval), `0012` qo'ngan zahoti qizaradi. ✅ Bajarildi. ⚠ **Topilma:** jadvallar `market_id` USTUNI bo'yicha emas, `markets` ga CHET EL KALITI bo'yicha topiladi — o'lchandi, `audit_log` da ustun bor, FK yo'q, ya'ni ustun bo'yicha izlash darvozani bugunoq yolg'on-qizil qilardi.
  - [x] *(03-03 T3)* **kengaytirishning o'zi** — `0012` bilan **bir oynada** bajarildi. Sabab tartibda: mavjud bo'lmagan jadvalga `DELETE` yozish `market_delete_draft()` ni chaqiradigan o'sha kungi testlarni DARHOL qizartirardi, ya'ni band alohida rejada bajarilsa yashil darvoza sinardi. WR-02 (D-17) ning DB darajasidagi cheklovi `0013` da. ✅ **O'LCHANDI:** `test_market_delete_guard.py::test_draft_market_deletion_covers_the_nvr_domain` (to'rtala jadval) va `::test_active_market_cannot_be_deleted_by_raw_sql` (`23514`, ilova qatlamini butunlay chetlab o'tib); mezon darajasida — `test_phase3_criteria.py::test_sc8_...`.

> ⚠ **W0-7 ning bo'linishi «yetti banddan olti yarim» degani EMAS.** Yettala band ham bajarildi; bo'linish faqat IJRO TARTIBIGA tegishli va u shu yerda qayd etiladi, chunki keyingi fazada xuddi shunday «darvoza avval, kengaytirish keyin» holati yana uchraydi (masalan 4-fazaning `capture_runs` jadvali).

**Frontend Wave 0** (`03-UI-SPEC.md` §13.1) — ekranlardan **oldin**, `03-08` da: RBAC ko'zgusi (03-01 da), `NAV_ITEMS`, `uz-Cyrl.overrides.json` (20 yozuv), `gen-cyrillic` assertion'lari (G-5), `error-codes` parity (G-1), `nvr-copy` (G-3/G-4/G-6), vendored pleyer + SHA-256 (G-7).

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Owner | Trigger | Havola |
|----------|-------------|------------|-------|---------|--------|
| Real Hikvision NVR'da kashfiyot | CAM-08 | Simulyator **modul** darajasida ishonchli, lekin real firmware'ning kutilmagan XML shakli yoki kanal raqamlash chetlanishi faqat qurilmada chiqadi | Bozor admini | NVR kirish ma'lumotlari kelganda | `ops/scripts/verify-real-nvr.sh`, `tests/integration/test_real_nvr.py` |
| CGNAT ostidagi WireGuard tunneli | CAM-02 | Bozor tomonidagi ISP topologiyasini simulyatsiya qilib bo'lmaydi | Ops | Bozor tomonidagi qurilma o'rnatilganda | `ops/wireguard/README.md`, `ops/scripts/verify-tunnel.sh` |
| `ip route get <nvr_ip>` → `wg0` (SC#5 ning 3-da'vosi) | CAM-02 | CI'da tunnel umuman yo'q — bunday test har doim «uzildi» deb o'tardi va hech nima isbotlamasdi (Pitfall 10) | Ops | VPS deploy'idan keyin | `ops/scripts/verify-tunnel.sh` |
| Bir vaqtdagi sessiya limiti (real qiymat) | CAM-08 | Chegara firmware va bitreytga bog'liq; simulyatorda **ikkala** stsenariy modellashtirilgan (D-05), lekin haqiqiy qiymat o'lchanmagan | Ops | Real NVR ulanganda | `ops/docs/nvr-onboarding.md` §4, `ops/scripts/verify-real-nvr.sh` (`rtsp.concurrent_failed`), `test_real_nvr.py::test_three_concurrent_rtsp_sessions` |
| Jonli tasvir sifati va kechikishi | CAM-03 | Idrok o'lchovi — real tarmoq, real kamera, real ekran | Direktor | Pilot tayyorlanganda | `03-UI-SPEC.md` §8.4 transport badge'i, `ops/docs/nvr-onboarding.md` §6 |
| Vendored `video-stream.js` kod-ko'rigi | CAM-03 | Uchinchi tomon kodini birinchi kiritishda odam o'qishi shart (`eval(`, `new Function`, tashqi `fetch(`, obfuskatsiya) | Ijrochi | `03-08` T3 da | `03-UI-SPEC.md` §14.2 jadvali |

> Bu bandlar **fazani bloklamaydi** (2026-08-01 self-service direktivasi). Ular egasi va tetigi bilan yozilgan; `nyquist_compliant` ularning bajarilganini emas, **shaklini** tekshiradigan skript bilan hisoblanadi — 2-fazadagi `scripts/check-validation-signoff.mjs` naqshi.

**03-11 da qo'shilgan vositalar.** Oltala band ham endi bajariladigan holatda: birinchi to'rttasi uchun `ops/scripts/verify-real-nvr.sh` (chiqishi JSON) va `pytest -m hardware` (5 test) mavjud, tartib esa `ops/docs/nvr-onboarding.md` §4 da. **Bajarilishi baribir talab qilinmaydi** — `hardware` markeri standart zanjirda (`pyproject.toml` dagi `-m "not hardware"`) umuman ishlamaydi.

⚠ **Simulyatorga qaratib O'LCHANDI (2026-08-03).** `hardware` to'plami `nvr-sim` ga qaratilganda **5 testdan 3 tasi o'tdi**. Qolgan ikkitasi simulyatorning **ataylab modellamagan** joylarini nomladi va ular 4-faza uchun ochiq band:
>
> * `test_every_channel_returns_one_frame` — sim `/picture` uchun 160 baytli `TINY_JPEG` beradi (protokol modeli, piksel emas);
> * `test_three_concurrent_rtsp_sessions` — `nvr-sim` 554-portni umuman tinglamaydi (RTSP manbasi alohida `go2rtc-sim` konteynerida).
>
> Ya'ni to'plam **haqiqatan bajariladi** va uning assert'lari haqiqatan o'lchaydi — «hech qachon ishlamaydigan to'plam» holati yopildi.

---

## Validation Sign-Off

- [x] Har taskda `<automated>` verify yoki Wave 0 bog'liqligi bor — 33/33
- [x] Namuna uzluksizligi: ketma-ket 3 taskda avtomatik verify yo'qligi holati yo'q
- [x] Wave 0 barcha MISSING havolalarni qoplaydi — yettala band bajarildi (W0-7 ikkiga bo'lindi, sababi yuqorida)
- [x] Watch-mode bayrog'i yo'q — `package.json` va `frontend/package.json` da `--watch` yo'q; vitest `run` rejimida
- [x] Teskari aloqa kechikishi o'lchangan va chegara asoslangan (2-fazadan meros qolgan 225 s / 180 s bandi hal qilingan) — raqamlar «Kechikish bandining yopilishi» bo'limida
- [x] `nyquist_compliant: true` skript bilan **hisoblangan**, qo'lda yozilmagan — `npm run validation:check -- .planning/phases/03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi/03-VALIDATION.md`
- [x] Per-Task Map ning barcha 33 qatori holat oldi — 33/33 ✅
- [x] `NVR_ERROR_CODES` ning o'n ikkitasi ham funksional test bilan qoplangan (yuqoridagi jadval)
- [x] D-09 ning 25 kanalli sekin testi bir marta bajarilgan (`npm run test:sim:slow`)

**Approval:** ✅ 2026-08-03, `03-11` (avtomatik qism to'liq yashil; inson bandlari egasi va tetigi bilan rejalashtirilgan va ular fazani BLOKLAMAYDI).

### ⚠ Imzo NIMANI ANGLATMAYDI

`nyquist_compliant: true` — bu **shakl** haqidagi da'vo: har taskning avtomatik buyrug'i bor, u bajarildi va yashil bo'ldi; qo'lda qoladigan har band esa egasi va tetigi bilan nomlangan. Skriptning o'zi buni ochiq aytadi («NIMA TEKSHIRILMAYDI VA NEGA: bandlarning MAZMUNI»).

U **quyidagilarni anglatmaydi** va bu farq 2-fazaning `02-VERIFICATION.md` darsidan keyin ataylab yozib qo'yilgan (890 yashil test ortida to'rtta haqiqiy bo'shliq topilgan edi):

1. **«Mahsulot real qurilmada ishlaydi»** — bu fazada HAMMASI simulyator ustida o'lchangan. Real firmware'ning chetlanishlari «Manual-Only» jadvalida, vositalari `ops/scripts/verify-real-nvr.sh` va `pytest -m hardware` da.
2. **«Talablar yopildi»** — beshta CAM bandidan ikkitasi `Done` (CAM-01, CAM-08), uchtasi `Blocked` va sababi `REQUIREMENTS.md` da NOMLANGAN.
3. **«Jonli tasvir ko'rinadi»** — avtorizatsiya zanjiri to'liq o'lchangan, videoning O'ZI esa hech qayerda ijro etilmagan: jsdom `RTCPeerConnection` bermaydi va `go2rtc-sim` ning oqimini birorta test iste'mol qilmaydi.
