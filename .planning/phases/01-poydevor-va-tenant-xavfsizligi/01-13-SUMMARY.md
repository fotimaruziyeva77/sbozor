---
phase: 01-poydevor-va-tenant-xavfsizligi
plan: 13
subsystem: infra
tags: [docker-compose, uvicorn, nginx, rate-limit, valkey, structlog, audit, security]

# Dependency graph
requires:
  - phase: 01-01
    provides: "compose steki (core-api, nginx `proxy` profili), .env.example, ops/nginx/nginx.conf"
  - phase: 01-03
    provides: "sbozor_core.logging — censor_secrets protsessori va SENSITIVE_KEYS reyestri"
  - phase: 01-06
    provides: "auth.py::_client_ip, security/ratelimit.py (rl:login:phone / rl:login:ip sanagichlari)"
provides:
  - "core-api uvicorn `--proxy-headers --forwarded-allow-ips` bilan ishga tushadi (base VA dev override) — nginx `X-Forwarded-For` ishonchli"
  - "FORWARDED_ALLOW_IPS muhit o'zgaruvchisi + `*` nega xavfsizligi hujjatlashtirilgan"
  - "tests/integration/test_rate_limit_proxy.py — IP-kesim ajralishini qulflovchi 5 ta regressiya testi"
  - "REKURSIV censor_secrets — ichma-ich lug'at/ro'yxat/kortejdagi sirlar stdout va Sentry'ga chiqmaydi"
affects:
  - "01-VERIFICATION qayta tekshiruvi (gap 4 / CR-04 yopildi)"
  - "Kelajakdagi deploy ishlari: core-api porti publish qilinsa FORWARDED_ALLOW_IPS ni nginx manziliga qadash SHART"
  - "Barcha keyingi loglovchi kod — ichma-ich payload'lar endi avtomatik maskalanadi"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Deploy-qatlam shartnomasi testda qulflanadi: ASGI scope'dagi `client` juftligi o'zgartirilib, uvicorn `--forwarded-allow-ips` qo'yadigan qiymat takrorlanadi"
    - "Teskari-yo'nalish qulfi: xom `X-Forwarded-For` sarlavhasining O'ZI sanagichni ko'chira olmasligi ham test bilan mahkamlanadi"
    - "Sir maskalash bir xil chuqurlikda: sbozor_core.logging._censor va audit_repo.mask_sensitive bitta mantiqni bajaradi"
    - "compose `command` MERGE QILINMAYDI — override faylida bayroqlar takrorlanishi shart"

key-files:
  created:
    - tests/integration/test_rate_limit_proxy.py
  modified:
    - compose.yaml
    - compose.override.yml
    - .env.example
    - packages/sbozor-core/sbozor_core/logging.py
    - tests/unit/test_logging.py

key-decisions:
  - "`--forwarded-allow-ips=${FORWARDED_ALLOW_IPS:-*}` tanlandi (nginx manzilini qadash o'rniga): compose tarmog'idagi konteyner IP'si barqaror emas, `*` esa core-api xost portiga publish qilinmagani uchun xavfsiz — sabab compose'da va .env.example'da yozib qo'yilgan"
  - "compose.override.yml ham tuzatildi: `command` almashtiriladigan (merge bo'lmaydigan) maydon, aks holda dev stek tuzatilmagan qolardi"
  - "IP chegarasi HTTP darajasida 51 ta so'rov bilan emas, sanagichni oldindan IP_LIMIT ga qo'yib sinaldi — natija bir xil, vaqt esa Argon2 hisobiga o'nlab soniyaga cho'zilmaydi"
  - "censor_secrets endi ichma-ich qiymatlarning NUSXASINI qaytaradi — protsessor chaqiruvchining payload'ini o'zgartirmasligi kerak"

patterns-established:
  - "Sabotaj tekshiruvi: har ikkala tuzatish uchun buzuq holat qayta tiklanib, testlar qizarishi isbotlandi"
  - "Gap-closure testlari faqat 'to'g'ri holat'ni emas, BUZILGAN holat qanday ko'rinishini ham qayd etadi (test_shared_client_scope_collapses_into_one_counter)"

requirements-completed: [FOUND-01, FOUND-03]

# Metrics
duration: 19min
completed: 2026-07-29
---

# Phase 01 Plan 13: Proxy IP ishonchi va rekursiv sir maskalash Summary

**uvicorn endi nginx uzatgan haqiqiy mijoz IP'siga ishonadi (`--proxy-headers --forwarded-allow-ips`), shu bilan anonim platforma-keng login qulflash DoS'i yopildi va `audit_log.ip` haqiqiy manbani yozadi; `censor_secrets` esa rekursiv bo'lib, ichma-ich sirlar Sentry'ga chiqmaydi.**

## Performance

- **Duration:** 19 min
- **Started:** 2026-07-29T14:10:30Z
- **Completed:** 2026-07-29T14:29:30Z
- **Tasks:** 2
- **Files modified:** 6 (1 yaratildi, 5 o'zgartirildi)

## Accomplishments

- **CR-04 yopildi.** `core-api` buyrug'iga `--proxy-headers` va `--forwarded-allow-ips` qo'shildi. Busiz uvicorn faqat `127.0.0.1` ga ishonardi, nginx esa compose tarmog'ida boshqa konteyner manzilida turadi — ya'ni uning `X-Forwarded-For` sarlavhasi tashlab yuborilardi va `request.client.host` har doim proxy IP'si bo'lardi. Ikkita oqibat bir vaqtda yopildi: (1) butun platforma uchun bitta `rl:login:ip:<proxy-ip>` sanagichi — chegara parol tekshiruvidan OLDIN ishlagani uchun muvaffaqiyatli login uni tozalay olmasdi, ya'ni ~51 anonim so'rov barcha kassir/admin/direktorni 15 daqiqaga qulflardi; (2) `audit_log.ip` har doim proxy manzilini yozardi.
- **Deploy-only folklor testga aylandi.** 5 ta regressiya testi ASGI scope'idagi `client` juftligini o'zgartirib, ikkita turli mijoz ikkita MUSTAQIL `rl:login:ip:*` kaliti hosil qilishini va bir kesim chegaraga yetganda ikkinchisi ochiq qolishini isbotlaydi.
- **WR-01 yopildi.** `censor_secrets` rekursiv bo'ldi — ichma-ich lug'at, ro'yxat va kortejdagi sirlar ham `***` bilan almashtiriladi. Endi u `audit_repo.mask_sensitive` bilan bir xil chuqurlikda ishlaydi (ikki qatlam bitta tahdidga — T-01-16 — qarshi turadi).
- **To'liq backend to'plami yashil:** 387 passed (375 baseline + 12 yangi), 0 xato. `ruff check` + `ruff format --check` + `mypy` (strict, 84 fayl) — toza.

## Task Commits

1. **Task 1: uvicorn --proxy-headers + IP-scope regressiya testi (CR-04)** — `368d557` (fix)
2. **Task 2: censor_secrets ni rekursiv qilish (WR-01)** — `2e91adf` (fix)

## Files Created/Modified

- `compose.yaml` — `core-api.command` ko'p qatorli ro'yxatga aylandi va `--proxy-headers` + `--forwarded-allow-ips ${FORWARDED_ALLOW_IPS:-*}` qo'shildi. Yonida izoh: bayroqsiz nima buziladi, `*` nega xavfsiz (port publish QILINMAYDI) va port publish qilinsa nima qilish shart.
- `compose.override.yml` — dev buyrug'iga o'sha ikki bayroq qo'shildi (deviatsiya #1, pastga qarang).
- `.env.example` — `FORWARDED_ALLOW_IPS=*` yangi "Reverse proxy (CR-04)" bo'limi bilan.
- `tests/integration/test_rate_limit_proxy.py` (YANGI) — 5 ta test:
  - `test_distinct_client_scopes_get_independent_ip_keys` — ikki mijoz, ikki mustaqil kalit, ikkalasi ham 1.
  - `test_shared_client_scope_collapses_into_one_counter` — BUZILGAN holat qanday ko'rinishini qayd etadi (uch telefon, bitta sanagich = 3).
  - `test_forwarded_header_alone_does_not_move_the_counter` — xom `X-Forwarded-For` sarlavhasining o'zi sanagichni ko'chira olmaydi (teskari-yo'nalish qulfi).
  - `test_ip_limit_on_one_scope_does_not_lock_out_another` — bir kesim 429, ikkinchisi odatdagi 401.
  - `test_exhausted_ip_scope_leaves_other_scope_open` — sanagich darajasida to'liq isbot (`IP_LIMIT` marta, har safar yangi telefon bilan).
- `packages/sbozor-core/sbozor_core/logging.py` — `_is_sensitive()` va rekursiv `_censor()` yordamchilari; `censor_secrets` endi sezgir bo'lmagan kalit qiymatini `_censor()` dan o'tkazadi. Docstringda `audit_repo.mask_sensitive` bilan parallellik qayd etilgan.
- `tests/unit/test_logging.py` — 7 ta yangi test: ikki darajali ichma-ich dict, ro'yxat ichidagi dict, kortej, ichma-ich registr farqi, oddiy ma'lumot buzilmasligi, chaqiruvchi payload'i O'ZGARMASLIGI va uchdan-uchi JSON chiqish satri.

## Decisions Made

- **`*` vs nginx manzilini qadash.** Compose tarmog'idagi konteyner IP'si barqaror emas (qayta yaratishda o'zgaradi) va servis nomi bu bayroqda ishlamaydi, shuning uchun `${FORWARDED_ALLOW_IPS:-*}` tanlandi. Xavfsizlik asosi: `core-api` xost portiga publish QILINMAYDI (base compose'da `ports:` yo'q — tekshirildi), dev override esa uni faqat `127.0.0.1` ga bog'laydi. Ya'ni sarlavhani soxtalashtira oladigan yagona tomon — allaqachon ichkarida bo'lgan tomon. Bu shart compose'da ham, `.env.example` da ham yozib qo'yilgan, kelajakda port ochilsa nima qilish kerakligi bilan birga.
- **Testda 51 ta HTTP so'rov yuborilmadi.** IP chegarasini HTTP darajasida sinash uchun sanagich oldindan `IP_LIMIT` ga qo'yildi — 51 ta login har biri Argon2 (`dummy_verify`) hisobiga testni o'nlab soniyaga cho'zardi. To'liq sanash faqat `check_login_rate` darajasida (HTTP'siz, tez) bajarildi.
- **Teskari-yo'nalish testi qo'shildi (planda yo'q edi).** `test_forwarded_header_alone_does_not_move_the_counter` — CR-04 ni "kodda XFF ni o'qiymiz" deb yopishga urinish sanagichni SOXTALASHTIRILADIGAN qiymatga bog'lardi (hujumchi har so'rovda yangi IP yozib chegaradan butunlay qutulardi). Bu test ishonch qarorini deploy qatlamida ushlab turadi.
- **`_censor()` nusxa qaytaradi, joyida o'zgartirmaydi.** Log protsessori chaqiruvchining ma'lumotini buzmasligi kerak — aks holda log yozgandan keyin o'sha obyekt bilan davom etayotgan kod `***` ni haqiqiy qiymat sifatida ishlatardi.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] `compose.override.yml` ham tuzatildi**

- **Found during:** Task 1 (compose.yaml tahriri)
- **Issue:** Planning `files_modified` da faqat `compose.yaml` bor edi. Lekin `compose.override.yml` `docker compose` tomonidan AVTOMATIK yuklanadi va `core-api.command` ni butunlay ALMASHTIRADI (compose `command` ni merge qilmaydi). Ya'ni dev stekda (`npm run up` — aynan nginx + core-api birga sinaladigan yo'l) bayroqlar yo'qolardi va plan `must_haves` dagi "core-api uvicorn `--proxy-headers --forwarded-allow-ips` bilan ishga tushadi" da'vosi yolg'on bo'lardi. Tuzatish qog'ozda qolardi.
- **Fix:** Dev buyrug'iga (`--reload` bilan birga) o'sha ikki bayroq qo'shildi va nega takrorlanishi kerakligi izohda yozildi.
- **Files modified:** `compose.override.yml`
- **Verification:** `docker compose config` (override avtomatik yuklangan holda) `--proxy-headers`, `--forwarded-allow-ips`, `'*'` ni ko'rsatadi; `docker compose -f compose.yaml config` base variantini ham tasdiqlaydi va `core-api` da `ports:` yo'qligi qayta tekshirildi.
- **Committed in:** `368d557` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 missing critical)
**Impact on plan:** Deviatsiya plan doirasini kengaytirmaydi — u AYNAN shu tuzatishning kuchga kirishi uchun zarur edi. Boshqa fayl ochilmadi.

## Issues Encountered

- **mypy strict `int(await cache.get(...))` ni rad etdi** (`bytes | str | None`). `_counter()` yordamchisi qo'shilib, `None` narrowing bir joyda bajarildi — test o'qilishi ham yaxshilandi.
- **Testning halol chegarasi (qayd uchun).** Test to'plamida uvicorn ishga tushmaydi (`httpx.ASGITransport` to'g'ridan-to'g'ri ilovaga boradi), shuning uchun compose bayrog'ining O'ZINI test isbotlay olmaydi. Test ILOVA tomonidagi shartnomani qulflaydi: kalit faqat `request.client.host` dan olinadi, turli scope'lar ajraladi va xom sarlavha hech narsani ko'chira olmaydi. Deploy tomoni esa `docker compose config` chiqishi va compose/`.env.example` izohlari bilan qamralgan. Ikkalasi birga CR-04 ni yopadi.

### Sabotaj tekshiruvi (ikkala tuzatish uchun)

- **CR-04:** `_client_ip` vaqtincha qat'iy `172.18.0.9` qaytaradigan qilindi (uvicorn XFF ni tashlagandagi holat) → 5 testdan 4 tasi qizardi (5-chisi `check_login_rate` ni to'g'ridan-to'g'ri sinaydi, shuning uchun ta'sirlanmaydi). Sabotaj bekor qilindi, `git diff` da `auth.py` YO'Q.
- **WR-01:** rekursiv chaqiruv olib tashlandi → 7 yangi testdan 6 tasi qizardi (7-chisi "oddiy ma'lumot buzilmasin" qulfi, u ataylab ikkala holatda ham yashil).

## Known Stubs

Yo'q — bu plan mavjud, ishlaydigan kodga xirurgik tuzatish kiritdi.

## Threat Flags

Yangi xavfsizlik yuzasi qo'shilmadi. Plan `<threat_model>` dagi uchala dispozitsiya bajarildi:

| Threat ID | Disposition | Holat |
|-----------|-------------|-------|
| T-01-85 (login IP rate-limit DoS) | mitigate | Yopildi — bayroq + 5 ta regressiya testi |
| T-01-86 (audit_log.ip repudiation) | mitigate | Yopildi — `request.client.host` endi haqiqiy mijoz IP'si |
| T-01-87 (logging.py sir sizishi) | mitigate | Yopildi — rekursiv maskalash + 7 ta unit test |

## User Setup Required

Yo'q — tashqi servis sozlash talab qilinmaydi. Faqat qayd: mavjud `.env` fayli bo'lgan muhitlarda `FORWARDED_ALLOW_IPS` KERAK EMAS (standart `*` compose'ning o'zida), lekin `core-api` porti kelajakda tashqi interfeysga chiqarilsa uni nginx manziliga qadash SHART.

## Next Phase Readiness

- CR-04 (gap 4) va WR-01 yopildi; 01-VERIFICATION qayta tekshiruviga tayyor.
- Qolgan warninglar bu plan doirasidan tashqarida: **WR-02** (`409 phone_taken` cross-tenant oracle) va **WR-03** (`markets.is_active` login/select-market'da tekshirilmaydi — markaziy `auth.py` ni ochadi, 8-fazaga qoldirilgan).
- REVIEW CR-04 dagi ixtiyoriy tavsiya bajarilmadi (doiradan tashqari, `auth.py` ni ochardi): "IP chegarasi buzilganda ham `dummy_verify()` ishlatib, 429 ni telefon sanagichidan KEYIN qaytarish va autentifikatsiyalangan refresh oqimini chegaradan ozod qilish". Bu portlash radiusini yanada kamaytirardi — kelajakdagi plan uchun nomzod.

## Self-Check: PASSED

- Fayllar mavjud: `compose.yaml`, `compose.override.yml`, `.env.example`, `tests/integration/test_rate_limit_proxy.py`, `packages/sbozor-core/sbozor_core/logging.py`, `tests/unit/test_logging.py`, `01-13-SUMMARY.md`.
- Kommitlar mavjud: `368d557`, `2e91adf`.
- Acceptance grep'lari: `forwarded-allow-ips` compose.yaml da (3 marta), `FORWARDED_ALLOW_IPS` .env.example da, `_censor` + `isinstance(dict/list|tuple)` logging.py da.
- `docker compose config --quiet` → exit 0; base `compose.yaml` da `core-api` uchun `ports:` YO'Q.
- `pytest` → 387 passed, 0 failed. `ruff check` + `ruff format --check` + `mypy` (strict) → toza.
- STATE.md / ROADMAP.md TEGILMAGAN (worktree rejimi — orkestrator yozadi).

---
*Phase: 01-poydevor-va-tenant-xavfsizligi*
*Completed: 2026-07-29*

---

## Hotfix (2026-07-29) — `X-Forwarded-For` soxtalashtirish teshigi yopildi

> Bu bo'lim yuqoridagi xulosadan KEYIN qo'shildi. Yuqoridagi matn 01-13
> topshirilgan paytdagi holatni saqlaydi va O'ZGARTIRILMAGAN — quyidagi
> tuzatish uni bir nechta joyda BEKOR QILADI (pastda "Eskirgan da'volar").

### Muammo: 01-13 DoS'ni spoofing'ga almashtirgan edi

01-13 `--forwarded-allow-ips *` ni jo'natdi. uvicorn 0.51.0 manbasi
(`uvicorn/middleware/proxy_headers.py`, o'qib tasdiqlandi) shuni qiladi:

```python
self.always_trust = trusted_hosts in ("*", ["*"])
...
if self.always_trust:
    return _parse_host_port(x_forwarded_for_hosts[0])   # ENG CHAP element
```

`ops/nginx/nginx.conf` esa `$proxy_add_x_forwarded_for` ishlatardi — bu
nginx o'zgaruvchisi mijoz YUBORGAN sarlavhaga `$remote_addr` ni QO'SHADI.
Zanjir:

1. Internetdagi mijoz: `X-Forwarded-For: 1.2.3.4`
2. nginx uzatadi: `X-Forwarded-For: 1.2.3.4, <haqiqiy mijoz IP>`
3. uvicorn (`always_trust`) `[0]` ni oladi → `request.client.host == "1.2.3.4"`

Ya'ni `request.client.host` TO'LIQ hujumchi nazoratida edi. Ta'siri 01-13
tuzatmoqchi bo'lgan nuqsondan OG'IRROQ:

| Ta'sir | Tafsilot |
|---|---|
| Rate-limit chetlab o'tish | Har so'rovga yangi soxta IP → `rl:login:ip:*` cheksiz aylanadi, parol terish chegarasiz |
| Maqsadli qulflash | Qurbonning haqiqiy IP'sini yozib, o'sha bozorni 15 daqiqaga qulflash |
| Soxta audit dalili | `audit_log.ip` hujumchi TANLAGAN qiymatni yozadi — FOUND-03 ning "kim qildi" ustuni |

01-13 gacha XFF umuman o'qilmasdi: bu umumiy-kalit DoS edi, lekin
SOXTALASHTIRIB bo'lmasdi. 01-13 DoS'ni autentifikatsiyaga tegishli
spoofing teshigiga almashtirdi.

### Nega 01-13 testi buni ushlamadi

`tests/integration/test_rate_limit_proxy.py` `httpx.ASGITransport(client=...)`
orqali ASGI scope'idagi `client` juftligini TO'G'RIDAN-TO'G'RI yozardi, ya'ni
`ProxyHeadersMiddleware` umuman ishga tushmasdi. Middleware'ning O'ZIDAGI
(va uni haydab turgan konfiguratsiyadagi) nuqson testga ko'rinmas edi —
buni 01-13 ning o'zi "Issues Encountered" da halol qayd etgan, lekin
xulosa noto'g'ri edi: bo'shliqni izoh emas, TEST yopishi kerak.

### Tuzatish — uchta mustaqil qatlam

**1-qatlam — nginx USTIGA yozadi (asosiy tuzatish).** `ops/nginx/nginx.conf`,
ikkala `location` da:

```nginx
proxy_set_header X-Forwarded-For   $remote_addr;   # oldin: $proxy_add_x_forwarded_for
```

Endi nginx mijoz yuborgan har qanday `X-Forwarded-For` ni TASHLAYDI va aynan
bitta element qoldiradi. `X-Real-IP $remote_addr` o'z holicha qoldirildi.
Faylga izoh yozildi: bu OVERWRITE bo'lib qolishi shart; oldinga ishonchli
upstream proxy (CDN/L7) qo'yilsa, ishonchli hop soni va
`--forwarded-allow-ips` BIRGALIKDA qayta ko'rib chiqiladi.

**2-qatlam — wildcard olib tashlandi.** `compose.yaml` + `compose.override.yml`:

```yaml
- "${FORWARDED_ALLOW_IPS:-172.16.0.0/12}"   # oldin: ${FORWARDED_ALLOW_IPS:-*}
```

Wildcard bo'lmaganda uvicorn zanjirni O'NGDAN CHAPGA yuradi va birinchi
ishonchsiz hop'da to'xtaydi — to'g'ri algoritm aynan shu.

Qiymat EMPIRIK aniqlandi, taxmin qilinmadi:

```
$ docker network inspect sbozor_default --format '{{json .IPAM.Config}}'
[{"Subnet":"172.19.0.0/16","Gateway":"172.19.0.1"}]
```

Kuzatilgan `172.19.0.0/16` QADALMADI: Docker bridge tarmoqlariga subnetni
standart puldan (`172.16.0.0/12` → `/16` bo'laklar) DINAMIK beradi, ya'ni
tarmoq qayta yaratilsa `sbozor_default` `172.20.x` bo'lib qolishi mumkin va
qadalgan `/16` jimgina ishlamay qo'yardi. Shuning uchun standart — butun
pul. Sabab va o'lchov `compose.yaml` hamda `.env.example` izohlarida yozildi;
prod uchun toraytirish yo'li ham ko'rsatildi.

**3-qatlam — haqiqatan ushlaydigan test.** `test_rate_limit_proxy.py` ga 9 ta
test qo'shildi. Ular ilovani HAQIQIY `ProxyHeadersMiddleware` ga o'raydi
(`uvicorn.middleware.proxy_headers` dan import) va uni SHIPPED
konfiguratsiyadan o'qilgan qiymatlar bilan haydaydi — sarlavha
`nginx.conf` direktivasidan HISOBLANADI, ishonch ro'yxati `compose*.yml` dan
o'qiladi:

| Test | Nimani qulflaydi |
|---|---|
| `test_spoofed_forwarded_for_cannot_set_client_host` | Hujumchi prefiksi `request.client.host` ga TUSHMAYDI (asosiy da'vo) |
| `test_trusted_hop_still_sets_the_real_client_host` | Sog'lom zanjirda proxy bergan qiymat ISHLATILADI — CR-04 buzilmadi |
| `test_proxy_layers_are_independently_sufficient` (4 holat) | 2×2 matritsa: har bir qatlam YAKKA O'ZI yetarli; `append+wildcard` holati 01-13 teshigi haqiqatan ishlaganini qayd etadi |
| `test_nginx_overwrites_forwarded_for_instead_of_appending` | `$proxy_add_x_forwarded_for` qaytarilsa QIZARADI |
| `test_compose_never_trusts_every_proxy` | `*` qaytarilsa QIZARADI; ikkala compose fayli kelishgan bo'lishi shart |
| `test_env_example_does_not_ship_the_wildcard` | `.env.example` `*` tarqatmaydi (u har bir dev'ning `.env` iga ko'chadi) |

### Sabotaj tekshiruvi

Ikkala qatlam 01-13 holatiga qaytarildi (`$proxy_add_x_forwarded_for` +
`${FORWARDED_ALLOW_IPS:-*}`), keyin `pytest tests/integration/test_rate_limit_proxy.py`:

```
FAILED test_spoofed_forwarded_for_cannot_set_client_host
FAILED test_nginx_overwrites_forwarded_for_instead_of_appending
FAILED test_compose_never_trusts_every_proxy
```

Asosiy xulq-atvor testi aynan ekspluatatsiyani ko'rsatdi:

```
>       assert await _counter(valkey_client, ATTACKER_IP) is None
E       assert 1 is None
```

— ya'ni hujumchi tanlagan `192.0.2.66` HAQIQATAN `rl:login:ip:192.0.2.66`
kalitiga tushdi. Sabotaj bekor qilindi (fayllar `md5sum` bo'yicha bayt-ma-bayt
tiklandi) va to'plam qayta yashil bo'ldi.

### Verifikatsiya

| Tekshiruv | Natija |
|---|---|
| `docker compose config --quiet` | exit 0 |
| `docker compose -f compose.yaml config --quiet` | exit 0 |
| `nginx -t` (`nginx:1.30.4-alpine`, upstream'lar `--add-host` bilan) | `syntax is ok` / `test is successful` |
| `docker compose --profile test run --rm tests pytest -q` | **425 passed**, 0 failed (416 baseline + 9 yangi) |
| `ruff check` + `ruff format --check` + `mypy` (strict) | toza |

### O'zgargan fayllar

`ops/nginx/nginx.conf`, `compose.yaml`, `compose.override.yml`,
`.env.example`, `tests/integration/test_rate_limit_proxy.py`.
`services/core-api/` va `frontend/` OCHILMADI — ilova kodi o'zgarmadi.
`STATE.md` / `ROADMAP.md` TEGILMAGAN.

### Eskirgan da'volar (yuqoridagi matnda)

- **"User Setup Required"** endi noto'g'ri: standart `*` EMAS, `172.16.0.0/12`.
  `*` ni `.env` ga yozish TAQIQLANADI — u soxtalashtirish teshigini qayta ochadi.
- **"Issues Encountered" → "Testning halol chegarasi"** endi amal qilmaydi:
  deploy qatlami izohlar bilan emas, `ProxyHeadersMiddleware` ni haqiqatan
  ishga tushiradigan testlar bilan qamralgan.
- **T-01-86 (audit repudiation)** 01-13 dan keyin aslida OCHIQ qolgan edi
  (`audit_log.ip` soxtalashtirilardi); shu hotfix bilan yopildi.
