---
phase: 3
slug: nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi
status: planned
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-03
updated: 2026-08-03
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
| **Estimated runtime** | ~470–590 s to'liq (2-fazada o'lchangan: 464 s / 571 s / 585 s); `--profile sim` ikkita konteyner qo'shadi → **`03-01` da qayta o'lchanadi** |

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

| O'lchov | Sovuq kesh | Issiq #1 | Issiq #2 | Eng yomon | Belgilangan chegara |
|---------|-----------|----------|----------|-----------|---------------------|
| `npm run gate:fast` | *(03-01 to'ldiradi)* | | | | 180 s |
| `npm run gate` | *(03-01 to'ldiradi)* | | | | *(03-11 asoslaydi)* |

> ⚠ **Jimgina oshib ketish qabul qilinmaydi.** Agar `gate:fast` ham 180 s dan oshsa, bu **topilma** sifatida yoziladi: qaysi qadam qancha vaqt olgani sanab o'tiladi va qisqartirish yo'li taklif qilinadi. Chegarani sababsiz ko'tarish taqiqlanadi.

---

## Per-Task Verification Map

*Har PLAN.md taski uchun bitta qator. `Status` ustunini ijrochi to'ldiradi (`03-11` Task 3).*

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| T03-01-1 | 03-01 | 1 | CAM-08, CAM-09 | T-03-01, T-03-06, T-03-SC | Prod image ISAPI klientini import qila oladi; `redis` pini pasaymaydi; `sim`/`slow`/`hardware` markerlari e'lon qilingan (D-09) | unit | `pytest tests/unit/test_runtime_deps.py -q` | ❌ yaratiladi | ⬜ pending |
| T03-01-2 | 03-01 | 1 | CAM-01, CAM-03 | T-03-02, T-03-03, T-03-04 | Platforma admini kamera ko'radi va boshqaradi; direktor faqat ko'radi; NVR paroli maskalanadi | unit | `pytest tests/unit/test_rbac_matrix.py tests/unit/test_logging.py -q` | ⚠ mavjud (kengaytiriladi) | ⬜ pending |
| T03-01-3 | 03-01 | 1 | CAM-08 | T-03-05, T-03-18 | Yangi tenant jadvali kaskaddan tushib qolsa CI qizaradi | integration | `pytest tests/integration/test_market_delete_guard.py -q` | ❌ yaratiladi | ⬜ pending |
| T03-02-1 | 03-02 | 2 | CAM-09 | T-03-09 | Sim haqiqiy RFC 7616 `response` ni hisoblab tekshiradi; noto'g'ri parol o'tmaydi | lint+type | `ruff check services/nvr-sim && mypy services/nvr-sim` | ❌ yaratiladi | ⬜ pending |
| T03-02-2 | 03-02 | 2 | CAM-09 | T-03-11, T-03-31 | Fixture'lar real dumpdan; namespace va manba izohi mavjud; **sessiya limiti D-05 ning ikkala shaklida** (`reject` / `silent`) modellashtirilgan | unit | `pytest tests/unit/test_sim_fixtures.py -q` + `grep -n stream_claims services/nvr-sim/sim/isapi.py` | ❌ yaratiladi | ⬜ pending |
| T03-02-3 | 03-02 | 2 | CAM-09 | T-03-07, T-03-08, T-03-10, T-03-12 | Sim prodga chiqmaydi; ilova kodida sim tarmoqlanishi yo'q; CI'da skip emas; sekin lenta (`test:sim:slow`) standart zanjirdan ajratilgan | unit + integration (sim) | `pytest tests/unit/test_no_sim_branching.py -q` va `npm run test:sim` | ❌ yaratiladi | ⬜ pending |
| T03-03-1 | 03-03 | 2 | CAM-01, CAM-08 | T-03-13, T-03-14 | `rtsp_url` ustuni yo'q; `nvr_credentials` auditdan tashqarida; reyestrlar to'liq | type + import | `ruff check . && mypy .` + model import assert'lari | ❌ yaratiladi | ⬜ pending |
| T03-03-2 | 03-03 | 2 | CAM-01, CAM-08 | T-03-14, T-03-16, T-03-19 | To'rt jadval RLS ENABLE+FORCE va policy bilan; qisman UNIQUE indekslar | migration + tenancy | `alembic upgrade head` + `npm run test:tenancy` | ❌ yaratiladi | ⬜ pending |
| T03-03-3 | 03-03 | 2 | CAM-08 | T-03-15, T-03-17, T-03-18 | Faol bozorni DB darajasida o'chirib bo'lmaydi; kanal noyobligi 23505 beradi | integration + tenancy | `pytest tests/integration/test_market_delete_guard.py tests/tenancy/test_nvr_domain_meta.py -q` | ⚠ qisman mavjud | ⬜ pending |
| T03-04-1 | 03-04 | 3 | CAM-01 | T-03-20, T-03-21, T-03-22 | Parol Fernet bilan shifrlanadi; kalit muhitda; rotatsiya ikki yo'nalishda | unit | `pytest tests/unit/test_nvr_secrets.py -q` | ❌ yaratiladi | ⬜ pending |
| T03-04-2 | 03-04 | 3 | CAM-02, CAM-08 | T-03-23, T-03-24, T-03-25 | Ommaviy IP rad etiladi; hostname qabul qilinadi; URL parol qabul qilmaydi | unit | `pytest tests/unit/test_rtsp_url.py tests/unit/test_nvr_host_validation.py -q` | ❌ yaratiladi | ⬜ pending |
| T03-04-3 | 03-04 | 3 | CAM-08 | T-03-26, T-03-27, T-03-28 | Upsert idempotent; `DELETE` yo'q; `error_detail` maskalanadi | integration | `pytest tests/integration/test_nvr_repo.py -q` | ❌ yaratiladi | ⬜ pending |
| T03-05-1 | 03-05 | 4 | CAM-08 | T-03-30, T-03-32, T-03-34 | Parser namespace bilan ishlaydi va jimgina bo'sh natija bermaydi; `detail` allowlist ostida | unit | `pytest tests/unit/test_isapi_parser.py tests/unit/test_isapi_errors.py -q` | ❌ yaratiladi | ⬜ pending |
| T03-05-2 | 03-05 | 4 | CAM-08 | T-03-29, T-03-31, T-03-32, T-03-33, T-03-35, T-03-36 | `401` qayta urinilmaydi (`attempts == 1`); drift `401` dan oldin (`attempts == 0`); **`nvr_stream_limit` ikkala stsenariyda** va **`nvr_tls_untrusted` transport darajasida** o'lchanadi — o'n ikkala koddan o'n bittasi shu faylda | integration (sim) | `npm run test:sim` (`test_nvr_errors.py`) | ❌ yaratiladi | ⬜ pending |
| T03-05-3 | 03-05 | 4 | CAM-08 | T-03-26, T-03-27 | Kashfiyot idempotent; yo'qolgan kanal `offline`; RTSP porti kashf etiladi; `channel_offline` (12-kod) shu yerda; **D-09 ning 25 kanalli sekin testi** | integration (sim) + slow | `npm run test:sim` va `npm run test:sim:slow` (`test_nvr_discovery.py`) | ❌ yaratiladi | ⬜ pending |
| T03-06-1 | 03-06 | 5 | CAM-08 | T-03-38, T-03-42 | Job tenant kontekstini o'zi o'rnatadi; navbat kutubxonasi faqat `worker.py` da | lint+type+grep | `ruff check . && mypy .` + `grep -c taskiq app/jobs/discovery.py` = 0 | ❌ yaratiladi | ⬜ pending |
| T03-06-2 | 03-06 | 5 | CAM-01, CAM-08 | T-03-37, T-03-39, T-03-44 | Javob modelida parol yo'q; `market_id` tanadan olinmaydi; `test-connection` rate-limit ostida | tenancy + type | `pytest tests/tenancy/test_route_coverage.py -q` + model assert'lari | ❌ yaratiladi | ⬜ pending |
| T03-06-3 | 03-06 | 5 | CAM-01, CAM-08 | T-03-37, T-03-38, T-03-40, T-03-41, T-03-43 | 202 → poll → succeeded zanjiri; 409 + `run_id`; cross-tenant 404 | integration (sim) | `npm run test:sim` (`test_nvr_discovery_job.py`) + `pytest tests/integration/test_nvr_api.py -q` | ❌ yaratiladi | ⬜ pending |
| T03-07-1 | 03-07 | 6 | CAM-01, CAM-03 | T-03-50, T-03-53 | `DELETE` marshruti yo'q; javob modelida `stream_name`/`rtsp_url` yo'q | tenancy | `pytest tests/tenancy/test_camera_route_coverage.py -q` | ❌ yaratiladi | ⬜ pending |
| T03-07-2 | 03-07 | 6 | CAM-03 | T-03-45, T-03-47, T-03-48, T-03-54 | `src` faqat `rtsp://`; go2rtc API nginx'da 403; token auditoriyasi ajratilgan | unit + config | `pytest tests/unit/test_go2rtc_client.py -q` + `nginx -t` | ❌ yaratiladi | ⬜ pending |
| T03-07-3 | 03-07 | 6 | CAM-02, CAM-03 | T-03-46, T-03-49, T-03-51, T-03-52 | `AllowedIPs` da `0.0.0.0/0` yo'q; jonli ko'rish auditda; 403 jurnalga yozmaydi | unit + integration | `pytest tests/unit/test_wireguard_config.py tests/integration/test_live_view.py -q` | ❌ yaratiladi | ⬜ pending |
| T03-08-1 | 03-08 | 7 | CAM-01, CAM-08 | T-03-61 | Kirill hosilasi defektsiz; akronim va `ts` birikmasi qulflangan | node:test + i18n | `npm --prefix frontend run i18n:check && node --test frontend/scripts/gen-cyrillic.test.mjs` | ⚠ mavjud (kengaytiriladi) | ⬜ pending |
| T03-08-2 | 03-08 | 7 | CAM-01, CAM-03 | T-03-57, T-03-58, T-03-60 | Kesh kalitlari `market_id` bilan doiralangan; parol keshga tushmaydi; poll chegaralangan | typecheck + vitest | `npm --prefix frontend run typecheck && npm --prefix frontend test` | ❌ yaratiladi | ⬜ pending |
| T03-08-3 | 03-08 | 7 | CAM-01, CAM-03 | T-03-55, T-03-56, T-03-61, T-03-62 | G-1…G-7 darvozalari; vendored pleyer SHA-256 bilan qulflangan — **qat'iy talab**, ikkita ekvivalent olish yo'li (git tegi yoki `alexxit/go2rtc:1.9.14` image'idan `docker cp`) | node:test | `node --test frontend/scripts/{error-codes,nvr-copy,vendor-integrity}.test.mjs` | ❌ yaratiladi (2 yangi) | ⬜ pending |
| T03-09-1 | 03-09 | 8 | CAM-01, CAM-08 | T-03-68 | Sahifa huquq bilan darvozalangan; bitta birlamchi tugma; `?run=` tiklanadi | typecheck + build | `npm --prefix frontend run typecheck && npm --prefix frontend run build` | ❌ yaratiladi | ⬜ pending |
| T03-09-2 | 03-09 | 8 | CAM-01 | T-03-63, T-03-65, T-03-67 | Manzil ajratiladi; parol keshga tushmaydi; auth qulfi faqat rekvizit o'zgarganda ochiladi | vitest | `npm --prefix frontend test -- nvr-form` | ❌ yaratiladi | ⬜ pending |
| T03-09-3 | 03-09 | 8 | CAM-01, CAM-08 | T-03-63, T-03-64, T-03-66 | Sabab va tuzatish teng og'irlikda; qulflaydigan kodda retry yo'q; `raw` matn sifatida | vitest | `npm --prefix frontend test -- nvr-error-block` | ❌ yaratiladi | ⬜ pending |
| T03-10-1 | 03-10 | 9 | CAM-08 | T-03-73, T-03-74 | Uch hisoblagich nol bo'lganda ham ko'rinadi; poll 180 s da to'xtaydi | vitest | `npm --prefix frontend test -- discovery` | ❌ yaratiladi | ⬜ pending |
| T03-10-2 | 03-10 | 9 | CAM-08 | T-03-75 | Arxivlash qaytariladigan amal; ulanmagan kamerada sabab aytiladi; «o'chirish» so'zi yo'q | vitest + node:test | `npm --prefix frontend test -- camera-row && node --test frontend/scripts/nvr-copy.test.mjs` | ❌ yaratiladi | ⬜ pending |
| T03-10-3 | 03-10 | 9 | CAM-03 | T-03-69, T-03-70, T-03-71, T-03-72 | Oqim faqat aniq bosishdan keyin; 5 daqiqada tugaydi; `stream_name` DOM'da yo'q | vitest | `npm --prefix frontend test -- live-view-dialog` | ❌ yaratiladi | ⬜ pending |
| T03-11-1 | 03-11 | 10 | CAM-01, CAM-02, CAM-03, CAM-08, CAM-09 | T-03-76, T-03-77 | Sakkizala mezon bitta zanjirda; SC#1 da `rtsp://` literali yo'q | integration (sim) | `npm run test:sim` (`test_phase3_criteria.py`) | ❌ yaratiladi | ⬜ pending |
| T03-11-2 | 03-11 | 10 | CAM-02, CAM-08 | T-03-81 | `hardware` markeri standart zanjirdan tashqarida; runbookda SSH qadami yo'q | collect-only + shell | `pytest -m hardware -q --collect-only && bash -n ops/scripts/verify-real-nvr.sh` | ❌ yaratiladi | ⬜ pending |
| T03-11-3 | 03-11 | 10 | CAM-01, CAM-02, CAM-03, CAM-08, CAM-09 | T-03-78, T-03-79, T-03-80 | `nyquist_compliant` hisoblanadi; talablar dalil bilan belgilanadi; `REQUIREMENTS.md` «Faza kesimida» jadvalidagi eskirgan faza nomi va soni **qayta hisoblanadi** | script | `npm run validation:check && npm run requirements:check` | ⚠ mavjud (to'ldiriladi) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

**Namuna uzluksizligi:** 33 taskning **hammasida** `<automated>` verify bor — ketma-ket uchta avtomatik verifysiz task holati **yo'q**.

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

- [ ] **W0-1** *(03-01 T1)* — `httpx` ni `[dependency-groups] dev` dan `[project] dependencies` ga ko'chirish. **Aks holda 24 test fayli yashil qoladi va deploy'da import xatosi beradi.** (D-16)
- [ ] **W0-2** *(03-01 T2)* — `rbac.py` da `CAMERA_MANAGE` + `PLATFORM_ADMIN` ga `CAMERA_VIEW`/`CAMERA_MANAGE`. Self-service onboarding'da bozorni aynan platforma admini ulaydi, ya'ni u o'zi topgan kameralarni ko'ra olmasdi. (D-15)
- [ ] **W0-3** *(03-01 T2)* — `frontend/src/lib/rbac.ts` ko'zgusi **birga** o'zgaradi. Unutish ma'lumot ochmaydi, lekin tugma ko'rinib turib 403 beradigan UI hosil qiladi.
- [ ] **W0-4** *(03-01 T2)* — `MARKET_ADMIN` ga `CAMERA_MANAGE`; `DIRECTOR` **olmaydi** (D-07 — o'qish roli).
- [ ] **W0-5** *(03-01 T1)* — `pyproject.toml` ga `sim` va `hardware` markerlari. `--strict-markers` tufayli marker e'lon qilinmasa `-m sim` yig'ilishda yiqiladi.
- [ ] **W0-6** *(03-01 T2)* — `SENSITIVE_KEYS` ni **tasdiqlash** (o'zgartirmaslik). ✅ 2026-08-03 da kod o'qildi: `rtsp_password` va `nvr_password` `logging.py:59-61` da allaqachon bor. Bu band **kod o'zgarishini talab qilmaydi** — u ichma-ich `error_detail` holati uchun test bilan o'lchanadi. (D-12)
- [ ] **W0-7** — `market_delete_draft()` kaskadi. **Ikkiga bo'lingan va sababi bilan:**
  - *(03-01 T3)* **muddatni majburlaydigan darvoza** — `pg_catalog` dan tenant jadvallarini o'qib funksiya tanasi bilan solishtiradi; bugun yashil (12 jadval), `0012` qo'ngan zahoti qizaradi;
  - *(03-03 T3)* **kengaytirishning o'zi** — `0012` bilan **bir oynada**, chunki mavjud bo'lmagan jadvalga `DELETE` yozish `market_delete_draft()` ni chaqiradigan bugungi testlarni darhol qizartirardi, ya'ni yashil darvozani sindirardi. WR-02 (D-17) DB darajasidagi cheklovi `0013` da.

**Frontend Wave 0** (`03-UI-SPEC.md` §13.1) — ekranlardan **oldin**, `03-08` da: RBAC ko'zgusi (03-01 da), `NAV_ITEMS`, `uz-Cyrl.overrides.json` (20 yozuv), `gen-cyrillic` assertion'lari (G-5), `error-codes` parity (G-1), `nvr-copy` (G-3/G-4/G-6), vendored pleyer + SHA-256 (G-7).

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Owner | Trigger | Havola |
|----------|-------------|------------|-------|---------|--------|
| Real Hikvision NVR'da kashfiyot | CAM-08 | Simulyator **modul** darajasida ishonchli, lekin real firmware'ning kutilmagan XML shakli yoki kanal raqamlash chetlanishi faqat qurilmada chiqadi | Bozor admini | NVR kirish ma'lumotlari kelganda | `ops/scripts/verify-real-nvr.sh`, `tests/integration/test_real_nvr.py` |
| CGNAT ostidagi WireGuard tunneli | CAM-02 | Bozor tomonidagi ISP topologiyasini simulyatsiya qilib bo'lmaydi | Ops | Bozor tomonidagi qurilma o'rnatilganda | `ops/wireguard/README.md`, `ops/scripts/verify-tunnel.sh` |
| `ip route get <nvr_ip>` → `wg0` (SC#5 ning 3-da'vosi) | CAM-02 | CI'da tunnel umuman yo'q — bunday test har doim «uzildi» deb o'tardi va hech nima isbotlamasdi (Pitfall 10) | Ops | VPS deploy'idan keyin | `ops/scripts/verify-tunnel.sh` |
| Bir vaqtdagi sessiya limiti (real qiymat) | CAM-08 | Chegara firmware va bitreytga bog'liq; simulyatorda **ikkala** stsenariy modellashtirilgan (D-05), lekin haqiqiy qiymat o'lchanmagan | Ops | Real NVR ulanganda | `ops/docs/nvr-onboarding.md` |
| Jonli tasvir sifati va kechikishi | CAM-03 | Idrok o'lchovi — real tarmoq, real kamera, real ekran | Direktor | Pilot tayyorlanganda | `03-UI-SPEC.md` §8.4 transport badge'i |
| Vendored `video-stream.js` kod-ko'rigi | CAM-03 | Uchinchi tomon kodini birinchi kiritishda odam o'qishi shart (`eval(`, `new Function`, tashqi `fetch(`, obfuskatsiya) | Ijrochi | `03-08` T3 da | `03-UI-SPEC.md` §14.2 jadvali |

> Bu bandlar **fazani bloklamaydi** (2026-08-01 self-service direktivasi). Ular egasi va tetigi bilan yozilgan; `nyquist_compliant` ularning bajarilganini emas, **shaklini** tekshiradigan skript bilan hisoblanadi — 2-fazadagi `scripts/check-validation-signoff.mjs` naqshi.

---

## Validation Sign-Off

- [ ] Har taskda `<automated>` verify yoki Wave 0 bog'liqligi bor
- [ ] Namuna uzluksizligi: ketma-ket 3 taskda avtomatik verify yo'qligi holati yo'q
- [ ] Wave 0 barcha MISSING havolalarni qoplaydi
- [ ] Watch-mode bayrog'i yo'q
- [ ] Teskari aloqa kechikishi o'lchangan va chegara asoslangan (2-fazadan meros qolgan 225 s / 180 s bandi hal qilingan)
- [ ] `nyquist_compliant: true` skript bilan **hisoblangan**, qo'lda yozilmagan
- [ ] Per-Task Map ning barcha 33 qatori holat oldi
- [ ] `NVR_ERROR_CODES` ning o'n ikkitasi ham funksional test bilan qoplangan (yuqoridagi jadval)
- [ ] D-09 ning 25 kanalli sekin testi bir marta bajarilgan (`npm run test:sim:slow`)

**Approval:** pending
