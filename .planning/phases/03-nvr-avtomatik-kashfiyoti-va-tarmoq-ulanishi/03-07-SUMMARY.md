---
phase: 03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi
plan: 07
subsystem: live-view-and-network-security
tags: [go2rtc, rce-guard, auth-request, nginx, jwt-audience, wireguard, split-tunnel, soft-delete, wave-6]

# Dependency graph
requires:
  - phase: 03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi
    plan: 06
    provides: "`api/v1/nvr.py` (dekoratordagi huquq naqshi), `TABLE_CAMERAS`, `nvr_router`"
  - phase: 03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi
    plan: 04
    provides: "`NvrRepository.list_cameras/rename/archive/restore`, `rtsp_url()`, `source_ip` ning `/32` artefakti"
  - phase: 02-bozor-domeni-va-yangi-bozor-ustasi
    plan: 19
    provides: "`audit_read` + `require_permission` introspektsiya teglari va marshrut grafini o'qish naqshi"
  - phase: 01-poydevor-va-tenant-xavfsizligi
    provides: "`sbozor_core.security` JWT qatlami, `ops/nginx/nginx.conf` ning `X-Forwarded-For` mexanikasi"
provides:
  - "`app/api/v1/cameras.py` — beshta marshrut; `DELETE` UMUMAN yo'q (D-10)"
  - "`app/services/go2rtc.py` — `assert_safe_go2rtc_src` allow-listi va `Go2rtcClient` (lazy `ensure_stream`)"
  - "`app/api/internal/live_authz.py` — nginx `auth_request` nishoni (204/403, tanasiz)"
  - "`sbozor_core.security.encode_live/decode_live` + `issue_live_token/decode_live_token` (`aud=\"live\"`)"
  - "`ops/nginx/nginx.conf` — `/live/` uchun `auth_request`, go2rtc API'sining IKKI yo'lda bloklanishi"
  - "`ops/go2rtc/go2rtc.yaml` + compose'dagi prod `go2rtc` (portsiz, `:ro` config)"
  - "`ops/wireguard/` — split-tunnel namunasi, README va `verify-tunnel.sh`"
  - "69 yangi test + cross-tenant matritsasining 28 ta avtomatik kengayishi"
affects: [03-08-frontend-matn, 03-10-frontend-kamera-yuzasi, 03-11-yakuniy-darvoza, 04-snapshot-pipeline]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Allow-list QORA RO'YXAT EMAS: `rtsp://` prefiksi AYNAN solishtiriladi — `strip()`/`lower()` yo'q, chunki har normalizatsiya darvoza bilan iste'molchi o'rtasida FARQ tug'diradi va chetlab o'tish aynan o'sha farqda yashaydi"
    - "Chipta RESURSGA bog'lanadi, foydalanuvchiga emas: `auth_request` `src` ni chiptadagi `camera_id` ning `stream_name` i bilan solishtiradi — aks holda haqiqiy chipta bilan begona oqim so'rash mumkin edi"
    - "Auditoriya (`aud`) ajratilishi IKKI TOMONLAMA o'lchanadi: bitta tomon 60 soniyalik chiptani 15 daqiqalik access tokenga aylantirardi"
    - "Konfiguratsiya darvozasi IZOHNI FILTRLAYDI: `compose.yaml` va `wg0.conf` izohlari o'z taqig'ini TUSHUNTIRADI, ya'ni xom grep yaxshi hujjatlashni jazolardi"
    - "Taqiqlangan LITERAL konfiguratsiya faylida izohda ham yozilmaydi — shunda sodda `grep -c` darvozasi istisnosiz tirik qoladi va parser bilan BIRGA ikki mustaqil qatlam beradi"
    - "Marshrut yuzasining strukturaviy darvozasi METOD bo'yicha cheklanmaydi: `GET` ga qadalgan qamrov eng nozik `POST` ni tashqarida qoldirgan edi (sabotaj bilan topildi)"
    - "`monkeypatch.setattr(\"<modul>.<nom>\", ...)` SATR nishoni bilan — re-export qilinmagan atributni almashtirishning yagona mypy-toza yo'li"

key-files:
  created:
    - services/core-api/app/api/v1/cameras.py
    - services/core-api/app/api/internal/__init__.py
    - services/core-api/app/api/internal/live_authz.py
    - services/core-api/app/services/go2rtc.py
    - ops/go2rtc/go2rtc.yaml
    - ops/wireguard/wg0.conf.example
    - ops/wireguard/README.md
    - ops/scripts/verify-tunnel.sh
    - tests/tenancy/test_camera_route_coverage.py
    - tests/unit/test_go2rtc_client.py
    - tests/unit/test_wireguard_config.py
    - tests/integration/test_live_view.py
  modified:
    - packages/sbozor-core/sbozor_core/security.py
    - services/core-api/app/security/tokens.py
    - services/core-api/app/schemas.py
    - services/core-api/app/settings.py
    - services/core-api/app/main.py
    - ops/nginx/nginx.conf
    - compose.yaml
    - package.json
    - tests/tenancy/test_cross_tenant.py

key-decisions:
  - "TOPILMA (sabotaj bilan): `POST /cameras/{id}/live-token` STRUKTURAVIY darvozadan TASHQARIDA edi. Huquq darvozasi butunlay olib tashlanganda `test_live_view.py` qizardi, `test_camera_route_coverage.py` esa YASHIL qoldi — u faqat `GET` larni tekshirardi. Fazaning eng nozik marshruti xulq testiga TAYANIB turgan ekan; `test_every_camera_route_declares_a_camera_permission` qo'shildi va u AYNAN o'sha sabotajni qizartirishi o'lchandi"
  - "TOPILMA (rejada yo'q, T-03-46 ni ochiq qoldirardi): faqat chiptani tekshirish YETARLI EMAS. URL `/live/api/ws?src=<oqim>&t=<chipta>` shaklida, ya'ni A bozori direktori O'Z kamerasi uchun HAQIQIY chipta olib `src` ni B bozori oqimiga almashtirsa, tekshiruv baribir 204 berardi. Chipta OQIM NOMIGA bog'landi (`src == camera.stream_name`)"
  - "go2rtc API'si IKKI yo'lda bloklanadi: `^/(api/streams|api/config|api/restart)` va `^/live/api/(streams|config|restart)`. Ikkinchisisiz `/live/` bloki prefiksni olib tashlab uzatgani uchun `/live/api/streams` o'sha API'ga YETIB BORARDI — birinchi blok `^/api/` ga langar tashlagan va uni umuman ko'rmasdi"
  - "`/live/` ning O'ZI ham ALLOW-LIST (`api/ws|api/webrtc|api/frame.jpeg|api/stream.m3u8|api/hls/...`), qora ro'yxat emas: go2rtc ning keyingi versiyasidagi yangi endpoint qora ro'yxatni jimgina eskirtirardi"
  - "`encode_live`/`decode_live` `sbozor_core.security` ga qo'shildi, `tokens.py` ga EMAS: o'sha modulning O'Z docstringi «bu modul KRIPTOGRAFIYA QILMAYDI» deydi. `LiveClaims` `TokenClaims` dan ALOHIDA sinf — bir sinf bo'lganda `roles`/`pa` maydonlari chiptada ham ko'rinardi va chaqiruvchi ularga qarab huquq qarori qabul qilishi mumkin edi"
  - "`assert_safe_go2rtc_src` `startswith` bo'yicha va REGISTRGA SEZGIR. `lstrip()`/`lower()` qo'shish ASVS V5.3 ning kanonizatsiya qoidasini buzardi: bizning `src` imiz `rtsp_url()` ning chiqishi, ya'ni bo'shliqli qiymat KODDAGI xato belgisi va uni jimgina «tuzatish» xatoni ko'rinmas qilardi"
  - "`Go2rtcClient` da `PATCH /api/config` va `POST /api/restart` metodlari UMUMAN yo'q — birinchisi ikkinchi haqiqat manbaini tug'diradi, ikkinchisi boshqa bozorlarning ko'rishini uzardi. Metodning yo'qligi kelishuv emas, STRUKTURA"
  - "`live-token` go2rtc yiqilganda **503**, 500 EMAS: bu bizning kodimizdagi xato emas, tashqi servisning holati. UI uni «Qayta urinish» affordansi bilan ko'rsatadi va bu yo'l NVR hisobiga urinish YUBORMAYDI (UI-SPEC §8.5 — §4.4 qulfi bu yerga qo'llanmaydi)"
  - "Taqiqlangan literal (`0.0.0.0/0`) `wg0.conf.example` da IZOHDA HAM yozilmaydi. Grep kodni izohdan ajratmaydi (shu fazada uch marta takrorlangan dars); literal izohga tushishi bilan sodda `grep -c` darvozasi mangu o'lardi. Literal FAQAT testda va `README.md` da (u parse qilinmaydi) — natijada IKKI mustaqil qatlam: parser (izohsiz) va oddiy grep"
  - "`test_wireguard_config.py` IKKALA tomonni ham parse qiladi (`wg0.conf.example` VA `README.md` §2 dagi `ini` bloki). Ikkita `[Interface]` bo'lgan fayl `wg-quick` uchun YAROQSIZ, ya'ni bozor tomonini bitta faylga tiqish nusxa olgan odamni sababsiz xatoga urardi; faqat VPS tomonini tekshirish esa bozor tomonida `0.0.0.0/0` yozilishini ochiq qoldirardi"
  - "`source_ip` normalizatsiyasi `ipaddress.ip_interface(...).ip` bilan, `split(\"/\")[0]` bilan EMAS: IPv6 da qiymat `fe80::1/128` bo'ladi va bitta qoida ikkala oilani ham yechadi. Parse qilib bo'lmaydigan qiymat XOM o'tadi — bu ustun kashfiyot yozadigan diagnostika va uni «tushunmadim» deb yo'qotish admindan kerakli ma'lumotni olib qo'yardi"

patterns-established:
  - "Pattern: xavfsizlik darvozasining TEST FAYLI konfiguratsiyani ham o'qiydi — himoya qatlamlari uch xil tilda (Python, nginx, YAML) yashaydi va faqat bittasi Python testlariga tabiiy ko'rinadi"
  - "Pattern: konfiguratsiya-darvozasi parseri IZOHLARNI FILTRLAYDI, chunki yaxshi konfiguratsiya izohi o'z taqig'ini nomma-nom tushuntiradi"
  - "Pattern: «nima YASHIL qoldi» ustuni darvozaning QAMROV chegarasini ochadi — S3 hech nimani qizartirmagani ikkita mustaqil mexanizm borligini, S3b esa strukturaviy darvozaning metod bo'yicha tor ekanini ko'rsatdi"
  - "Pattern: rad etish yo'llari (imzo, muddat, auditoriya, takror, mos kelmaslik) HAR BIRI ALOHIDA test — bitta parametrik test «hammasi rad etiladi» deb yashil bo'lardi, lekin qaysi yo'l ochiq qolgani ko'rinmasdi"

requirements-completed: []

# Metrics
duration: 205min
completed: 2026-08-03
---

# Phase 3 Plan 07: Kameralar API'si, jonli ko'rish va tarmoq darvozalari Summary

**Fazaning eng xavfsizlik-zich yuzasi yopildi: go2rtc'ning RCE qobiliyatli API'si uch qatlam bilan berkitildi, jonli ko'rish chiptasi RESURSGA bog'landi (rejada yo'q edi — usiz haqiqiy chipta bilan begona bozorning oqimini so'rash mumkin edi) va sabotaj strukturaviy darvozaning fazaning eng nozik marshrutini QAMRAMAYOTGANINI ko'rsatdi.**

## Performance

- **Duration:** ~205 min
- **Tasks:** 3/3 (+1 sabotaj-natijasi commit'i)
- **Files:** 21 (12 yangi, 9 o'zgargan), 3736 qator qo'shildi

## Accomplishments

- **D-11 ning uchala qatlami ham QURILDI va HAR BIRI alohida o'lchandi** — port publish qilinmagani (compose), nginx bloklari (ikki yo'lda!) va `assert_safe_go2rtc_src` allow-listi.
- **T-03-46 ning haqiqiy yuzasi topildi va yopildi:** chipta faqat imzo/muddat/bozor bilan tekshirilsa, `src` ni almashtirish orqali cross-tenant ko'rish OCHIQ qolardi.
- **Bazaviy darvoza kengaydi:** 1351 → **1448** backend (+97), 362 → **412** tenancy (+50); sim **61**, node **60**, vitest **74**, i18n **444×3** — o'zgarmadi. `npm run gate` → **exit 0 / 15 m 32 s**.
- **`pyproject.toml` va `frontend/package.json` TEGILMADI** (T-03-SC): birorta yangi paket qo'shilmadi.
- **Yangi xato kodi qo'shilmadi** — ya'ni 03-06 ning `MARKET_ERROR_CODES` ko'zgusi (`frontend/scripts/error-codes.test.mjs`) bu rejada qizarmadi.

## Task Commits

1. **Task 1: Kameralar reestri, arxivlash va qamrov darvozasi** — `0402481` (feat)
2. **Task 2: Jonli ko'rish chiptasi, go2rtc allow-listi va nginx darvozalari** — `f9f41eb` (feat)
3. **Task 3: WireGuard split-tunnel darvozasi va jonli ko'rishning isboti** — `8eacce9` (test)
4. **Sabotaj topilmasi: har marshrut huquq ostida** — `860edc8` (test)

## Files Created/Modified

| Fayl | Nima qiladi |
|---|---|
| `app/api/v1/cameras.py` | Beshta marshrut (`GET`, `PATCH`, `archive`, `restore`, `live-token`); `DELETE` UMUMAN yo'q; `normalize_source_ip` |
| `app/services/go2rtc.py` | `assert_safe_go2rtc_src` (allow-list), `Go2rtcClient` (lazy `ensure_stream`), `live_view_url` |
| `app/api/internal/live_authz.py` | `GET /internal/live-authz` — 204/403, tanasiz; chipta + `src` mosligi; kontekst CHIPTADAN |
| `sbozor_core/security.py` | `encode_live`/`decode_live`/`LiveClaims` — `typ="live"` VA `aud` ajratilgan |
| `app/security/tokens.py` | `LIVE_TOKEN_AUDIENCE`, `LIVE_TOKEN_MAX_TTL_SECONDS`, `issue_live_token`, `decode_live_token` |
| `app/schemas.py` | `CameraRead`/`CameraListResponse`/`CameraQuery`/`CameraUpdateRequest`/`LiveTokenResponse` |
| `ops/nginx/nginx.conf` | `/live/` allow-listi + `auth_request`; go2rtc API'sining IKKI blokdagi `403` i; `internal;` nishoni |
| `ops/go2rtc/go2rtc.yaml` | Prod konfiguratsiyasi — `streams: {}`, `exec:` YO'Q, API ichki interfeysda |
| `compose.yaml` | Prod `go2rtc` (profilsiz, `ports:` YO'Q, `:ro` config) |
| `ops/wireguard/*` | Split-tunnel namunasi, `AllowedIPs` ning ikki vazifasi, CGNAT, D-07, `vpn` profili bandi |
| `ops/scripts/verify-tunnel.sh` | SC#5 ning 3-da'vosi — deploy smoke-testi (CI'da ATAYIN bajarilmaydi) |
| `tests/tenancy/test_camera_route_coverage.py` | 22 test: huquq va sizib chiqish darvozalari ALOHIDA + nazorat marshruti |
| `tests/unit/test_go2rtc_client.py` | 19 test: sakkizta rad etish yo'li + uchala qatlamning konfiguratsiya darvozalari |
| `tests/unit/test_wireguard_config.py` | 9 test: IKKALA tomon parse qilinadi, quyi chegara bilan |
| `tests/integration/test_live_view.py` | 19 test: rad etish matritsasi, e'lon tartibi nazorati, auditoriyaning IKKI tomoni |

## O'lchangan dalillar

### D-11 — uch qatlam, uchtasi ham alohida

| Qatlam | O'lchov |
|---|---|
| go2rtc porti xostga publish QILINMAYDI | `test_compose_does_not_publish_the_go2rtc_api_port` — `ports:` yo'q, `1984` KODDA yo'q |
| nginx `/api/streams\|config\|restart` -> 403 | `test_nginx_blocks_the_go2rtc_api_path[×3]` — `location` bloki `return 403` bilan |
| nginx `/live/api/streams\|config\|restart` -> 403 | `test_nginx_blocks_the_api_path_through_the_live_prefix` — **rejada yo'q edi** |
| `src` allow-listi | 8 rad etish yo'li: `exec:`, `ffmpeg:`, `echo:`, `http://`, bo'sh, bosh bo'shliq, `RTSP://`, ichki `rtsp://` |
| Prod configda `exec:` yo'q | `test_production_go2rtc_config_has_no_exec_source` (sim configida BOR va u xavfsiz) |
| Konstanta ↔ nginx bloki mos | `test_go2rtc_streams_path_matches_the_blocked_path` |
| `nginx -t` | ✅ `syntax is ok` / `test is successful` |
| Mavjud proxy mexanikasi TEGILMAGAN | `git diff --unified=0 ... \| grep -cE 'X-Forwarded-For\|X-Real-IP\|remote_addr'` = **0** |

### SC#6 — rad etish matritsasi (`/internal/live-authz`)

| Kirish | Javob | Test |
|---|---|---|
| Chipta yo'q | **403** | `test_live_authz_without_a_token_is_denied` (+ tana BO'SH) |
| `src` yo'q | **403** | `test_live_authz_without_a_stream_is_denied` |
| Chipta takrorlangan (`?t=a&t=b`) | **403** | `test_repeated_token_parameter_is_rejected` |
| Muddati o'tgan chipta | **403** | `test_expired_live_token_is_rejected` |
| ODDIY access token | **403** | `test_api_token_is_not_a_live_ticket` |
| Boshqa kameraning oqim nomi | **403** | `test_token_does_not_work_for_another_cameras_stream` |
| Arxivlangan kameraning chiptasi | **403** | `test_ticket_for_an_archived_camera_is_rejected` |
| Haqiqiy chipta + mos oqim | **204**, tanasiz | `test_valid_ticket_and_stream_are_allowed` |

### Auditoriya ajratilishi — IKKI TOMONLAMA (T-03-48)

| Yo'nalish | O'lchov |
|---|---|
| Jonli chipta oddiy API'da | `GET /api/v1/cameras` -> **401** |
| Access token `auth_request` da | `GET /internal/live-authz` -> **403** |

### Audit — `reason` ajratilgan va 403 iz qoldirmaydi (T-03-49)

| Da'vo | O'lchov |
|---|---|
| Jonli ko'rish `reason='live_view'` yozadi | qatorlar soni **+1**, `filters.camera_id` chaqirilgan kamera |
| U `camera_view` qatorini YOZMAYDI | reestr o'qishlari soni **o'zgarmadi** (nazorat bandi) |
| Reestr o'qishi `reason='camera_view'` yozadi | +1, `result_count` = faol kameralar soni |
| **403 olgan so'rov HECH NIMA yozmaydi** | kassir 403 oldi, jonli ko'rish qatorlari soni **o'zgarmadi** |

### D-10 — soft-delete

| Da'vo | O'lchov |
|---|---|
| `DELETE` marshruti UMUMAN yo'q | `app.routes` da kamera yuzasida `DELETE` = **0** |
| `archive` juftisiz emas | `archive` VA `restore` ikkalasi ham mavjud |
| Arxivlash qatorni O'CHIRMAYDI | `count(cameras)` chaqiruvdan oldin va keyin **bir xil** |
| Standart ro'yxat arxivlanganni yashiradi | 3 kanaldan **2** qaytdi |
| `?archived=true` uni KO'RSATADI | **3** qaytdi (nazorat bandi) |

### SC#4 / UI-SPEC §8.7 — sizib chiqish

| Da'vo | O'lchov |
|---|---|
| `stream_name`/`rtsp_url`/`password` javob modellarida yo'q | **12/12** marshrutda rekursiv skan toza |
| Skaner HAQIQATAN maydon ko'radi | `channel_no` va `has_password` topildi (bo'sh to'plam emas) |
| `live-token` javobida faqat uch maydon | `{url, expires_in, transport_hint}` |

### SC#5 — uchta da'vo

| # | Da'vo | Holat |
|---|---|---|
| 1 | NVR manzili xususiy | ✅ 03-04 da (`assert_private_host`, `is_global` bo'yicha) |
| 2 | `AllowedIPs` toza | ✅ **CI'da**: IKKALA tomon parse qilinadi, `0.0.0.0/0` va `::/0` yo'q, har CIDR xususiy, quyi chegara 2 peer |
| 3 | Marshrut `wg0` dan | ⚠ `ops/scripts/verify-tunnel.sh` — deploy smoke-testi, CI'da ATAYIN bajarilmaydi |

Qo'shimcha: `test_no_real_key_material_is_committed` — namunadagi har `PrivateKey`/`PublicKey` `<...>` shaklida (haqiqiy kalit gitga tushmasin).

### Bazaviy darvoza

| Bosqich | Natija |
|---|---|
| `ruff check` + `ruff format --check` + `mypy` | ✅ exit 0 (192 fayl / 187 manba) |
| `pytest -q` (butun backend) | ✅ **1448** (1351 → **+97**) |
| `pytest tests/tenancy -q` | ✅ **412** (362 → **+50**) |
| `npm run test:sim` | ✅ **61** (o'zgarmadi) |
| frontend node / vitest | ✅ **60** / **74** (o'zgarmadi) |
| `npm run i18n:check` | ✅ **444 kalit × 3 til** (o'zgarmadi) |
| frontend typecheck / lint / build | ✅ toza / toza / to'liq prerender |
| `nginx -t` | ✅ syntax ok |
| `docker compose config --services` | ✅ `go2rtc` profilsiz, `ports:` yo'q |
| **`npm run gate`** | ✅ **exit 0** — **15 m 32 s** (932 s) |
| `git diff pyproject.toml frontend/package.json` | ✅ toza (T-03-SC) |

⚠ **Darvoza vaqti:** 03-06 dagi 819 s → **932 s** (+113 s). O'sish 97 ta yangi testdan (~40 s) va `test:sim` bosqichining `go2rtc` image'ini birinchi marta tortib olishidan. 03-01 ning nomzod chegarasi (618 s) **to'rtinchi rejada ketma-ket** buzildi — `03-11` uchun ochiq band bo'lib qolaveradi.

## Sabotajlar — nima qizardi VA nima yashil qoldi

| # | Sabotaj | Qizardi | **Yashil qoldi** | Ma'nosi |
|---|---|---|---|---|
| **S1** | `assert_safe_go2rtc_src` -> `src.lstrip().startswith(...)` | **AYNAN BITTA**: `test_rejects_leading_whitespace_source` | Qolgan 18 unit testi + **19/19** `test_live_view.py` | Chegara AYNAN o'lchanmoqda. Boshqa yettala rad etish yo'li ham, mahsulot yo'li ham (`ensure_stream` ga `rtsp://` boradi) o'zgarmadi — ya'ni «allow-list ishlaydi» degan umumiy da'vo kanonizatsiya teshigini QAMRAMAYDI |
| **S2** | `README.md` dagi bozor peer'ining `AllowedIPs` -> `0.0.0.0/0` | **IKKITA**: `test_no_peer_allows_the_full_tunnel[0.0.0.0/0]` va `test_every_allowed_ip_is_a_valid_private_cidr` | `test_live_view.py` (19) + `test_camera_route_coverage.py` (21) — **40 ta** | SC#5 ning 2-da'vosi HAQIQATAN o'lchanadi va u **bozor tomonini ham** qamraydi. Ikkinchi test «bonus» emas: u `128.0.0.0/1` kabi `FULL_TUNNEL_MARKERS` ga tushmaydigan kengaytmalarni ham ushlaydi |
| **S3** | `live-token` dan huquq DEKORATORDAN olib tashlanib IMZOGA ko'chirildi (audit dependency'sidan KEYIN) | **HECH NIMA** | **40 tasi**, shu jumladan `test_forbidden_live_token_is_not_audited` | **Bu ustun eng qimmatlisi.** «403 jurnalga yozmaydi» kafolatini IKKI mustaqil mexanizm ushlab turadi (`audit.py::audit_read` docstringi): e'lon tartibi VA `BackgroundTasks` ning faqat MUVAFFAQIYATLI javobga biriktirilishi. Ikkinchisi yolg'iz ham yetadi — ya'ni test MEXANIZMNI emas, DA'VONI o'lchaydi va bu to'g'ri |
| **S3b** | `live-token` dan huquq darvozasi BUTUNLAY olib tashlandi | **AYNAN BITTA**: `test_forbidden_live_token_is_not_audited` | **`test_camera_route_coverage.py` ning 21 tasi** | **Topilma.** Strukturaviy darvoza faqat `GET` larni qamrardi, ya'ni fazaning eng nozik marshruti (`POST /live-token`) undan TASHQARIDA edi va faqat xulq testiga tayanardi. `test_every_camera_route_declares_a_camera_permission` qo'shildi va u shu sabotajni AYNAN qizartirdi (commit `860edc8`) |
| **S4** | `list_cameras` imzosidan `intent: CameraReadIntentDep` olib tashlandi | **IKKITA**: `test_camera_list_declares_the_read_audit` (strukturaviy) va `test_camera_list_is_audited_and_hides_archived_rows` (xulq) | `test_personal_data_coverage.py` ning hammasi | Reja bu sabotaj darvozani qizartirmaydi deb bashorat qilgan edi. Ijobiy JUFT test (`test_camera_list_declares_the_read_audit`) qo'shilgani uchun u **qizardi** — ya'ni audit tomoni endi integratsiya testiga YAKKA tayanmaydi |

Hamma sabotajlar commit'dan **keyin** bajarildi va `git checkout -- <aniq fayl>` bilan tiklandi; har birida ish daraxti toza qoldi.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 — Yetishmayotgan kritik funksiya] Chipta OQIM NOMIGA bog'landi**

- **Found during:** Task 2 (`live_authz.py` ni loyihalash paytida)
- **Issue:** Reja `live-authz` ning ishini shunday belgilaydi: *«`decode_live_token` bilan tekshiradi, `camera_id` → `market_id` mosligini bazadan tasdiqlaydi va 204 yoki 403 qaytaradi»*. Ammo URL shakli `/live/api/ws?src=<oqim-nomi>&t=<chipta>` va **`src` ni go2rtc ishlatadi**, tekshiruv esa unga umuman qaramasdi. Natijada: A bozori direktori O'Z kamerasi uchun **haqiqiy** chipta oladi (imzo to'g'ri, muddat to'g'ri, bozor to'g'ri), keyin `src` ni **B bozori** kamerasining oqim nomiga almashtiradi — `auth_request` **204** beradi va go2rtc B bozorining tasvirini uzatadi. Ya'ni T-03-46 ning butun mitigatsiyasi chetlab o'tilardi.
- **Fix:** `_stream_matches()` chiptadagi `camera_id` ga mos qatorning `stream_name` ini so'rovdagi `src` bilan **aynan** solishtiradi; mos kelmasa 403.
- **Verification:** `test_token_does_not_work_for_another_cameras_stream` (B bozorining oqim nomi bilan A ning chiptasi -> 403).
- **Committed in:** `f9f41eb`

**2. [Rule 2 — Yetishmayotgan kritik funksiya] `/live/api/(streams|config|restart)` uchun ikkinchi 403 bloki**

- **Found during:** Task 2, nginx konfiguratsiyasini yozish paytida
- **Issue:** Reja bitta blok belgilaydi: `location ~ ^/(api/streams|api/config|api/restart) { return 403; }`. Ammo `/live/` bloki go2rtc'ga so'rovni **prefiksni olib tashlab** uzatadi (`rewrite ^/live/(.*)$ /$1 break`), ya'ni `/live/api/streams` go2rtc'ning `/api/streams` iga **yetib borardi**. Birinchi blok `^/api/...` ga langar tashlagan va uni umuman ko'rmasdi.
- **Fix:** Ikkinchi blok (`^/live/api/(streams|config|restart)`) **va** `/live/` ning o'zini ALLOW-LIST qilish (`api/ws|api/webrtc|api/frame.jpeg|api/stream.m3u8|api/hls/.+`). Ikki mustaqil to'siq: allow-listdan tushmagan yo'l `location /` orqali frontendga ketadi va go2rtc'ga UMUMAN bormaydi.
- **Verification:** `test_nginx_blocks_the_api_path_through_the_live_prefix`.
- **Committed in:** `f9f41eb`

**3. [Rule 2 — Yetishmayotgan kritik funksiya] Parametr takrorlanishi rad etiladi**

- **Found during:** Task 2
- **Issue:** `?t=<haqiqiy>&t=<yolg'on>` — HTTP parametrni ikki marta berishga ruxsat beradi va turli qatlamlar turli qiymatni tanlaydi (nginx birinchisini, go2rtc oxirgisini). Bitta qiymatni «tanlab olish» biz tekshirgan chipta go2rtc ishlatadigan chipta **bo'lmasligi** xavfini ochardi.
- **Fix:** `_single()` — parametr aynan bir marta berilgan bo'lishi shart, aks holda `None` (va 403).
- **Verification:** `test_repeated_token_parameter_is_rejected`.
- **Committed in:** `f9f41eb`

**4. [Rule 2 — Yetishmayotgan kritik funksiya] Kamera yuzasidagi HAR marshrut huquq ostida**

- **Found during:** S3b sabotaji (commit'dan keyin)
- **Issue:** `test_camera_route_coverage.py` ning huquq darvozasi ATAYIN `GET` larga qadalgan edi (reja shunday belgilagan: *«har `cameras`/`nvr-devices` `GET` marshrutining...»*). Sabotaj ko'rsatdiki, o'sha chegara fazaning **eng nozik** marshrutini — `POST /cameras/{id}/live-token` ni — darvozadan **butunlay chiqarib** qoldiradi: huquq dependency'si olib tashlanganda faqat xulq testi qizardi, strukturaviy darvoza esa yashil qoldi.
- **Fix:** `test_every_camera_route_declares_a_camera_permission` — metoddan qat'i nazar har marshrut `CAMERA_VIEW` yoki `CAMERA_MANAGE` e'lon qilishi shart.
- **Nega bu «ortiqcha» emas:** ikkala darvoza ikki xil paytda ishlaydi. Xulq testi mavjud marshrutni himoya qiladi; strukturaviy darvoza esa **YANGI** endpoint uchun — u hali birorta xulq testiga ega emas va aynan o'shanda unutish ehtimoli eng yuqori.
- **Committed in:** `860edc8`

**5. [Rule 3 — Bloklovchi] `encode_live`/`decode_live` `sbozor_core.security` ga qo'shildi**

- **Found during:** Task 2
- **Issue:** Reja `decode_live_token` ni *«`decode` (`:137-145`) ustidagi qobiq»* deb belgilaydi. Ammo `decode_token` `TokenClaims` qaytaradi va unda `camera_id` uchun **joy yo'q**; `TokenClaims` ga ixtiyoriy `camera_id` qo'shish esa access tokenni ham «kamera tokeni bo'lishi mumkin» degan shaklga keltirardi. Muqobil (JWT'ni `tokens.py` da to'g'ridan-to'g'ri kodlash) o'sha modulning **O'Z docstringiga zid**: *«Bu modul KRIPTOGRAFIYA QILMAYDI»*.
- **Fix:** Kripto `sbozor_core.security` da (`encode_live`/`decode_live`/`LiveClaims`), `Settings` bog'lash esa `tokens.py` da — mavjud chegara buzilmadi. Tekshiruvlar ro'yxati `decode_token` dagi bilan **aynan bir xil** (`REQUIRED_CLAIMS` + `mid`/`cam`, `algorithms=["HS256"]` LITERAL).
- **Committed in:** `f9f41eb`

**6. [Rule 3 — Bloklovchi] `/internal/live-authz` cross-tenant matritsasidan CHIQARILDI**

- **Found during:** Task 2
- **Issue:** Reja aytadi: *«Bu marshrut `/api/v1` prefiksida emas, ya'ni u cross-tenant matritsasiga tushmaydi»*. Bu **noto'g'ri**: `all_routes()` `app.routes` ning HAMMASINI yuradi (`/healthz` ham matritsada bo'lardi, agar istisno qilinmasa). Matritsa tokensiz/buzilgan/muddati o'tgan token uchun **401** kutadi, bu marshrutning kontrakti esa **403** — ya'ni uchala test ham qizarardi.
- **Fix:** `EXEMPT_ROUTES` ga `global` toifasidagi SABAB bilan qo'shildi va qamrovi `test_live_view.py` da **to'liq qayta tiklandi** (tokensiz, muddati o'tgan, ODDIY access token, begona bozor, boshqa oqim — beshta holat). Bu `EXEMPT_ROUTES` docstringining o'z talabi: *«Istisno qo'shgan odam bu qamrovni ham ko'chirishi SHART»*.
- **Committed in:** `f9f41eb`

**7. [Rule 3 — Bloklovchi] `Settings.go2rtc_url` qo'shildi**

- **Found during:** Task 2
- **Issue:** Reja `Go2rtcClient` ni belgilaydi, lekin uning `base_url` ini qayerdan olishini aytmaydi. Modul globali `app.state` naqshiga zid bo'lardi (03-06 ning §3.8 qarori).
- **Fix:** `Settings.go2rtc_url` (standart `http://go2rtc:1984`). **Standart qiymat BOR** va bu `nvr_credential_key` bilan qarama-qarshi emas: bu maydon sir emas, u compose xizmatining nomi — standart mahsulot topologiyasining o'zi.
- **Committed in:** `f9f41eb`

**8. [Rule 1 — Xato] `npm run up` `worker` va `go2rtc` ni ko'tarmasdi**

- **Found during:** Task 2
- **Issue:** `compose.yaml` ning izohi (03-06 yozgan) *«profilsiz -> db, cache, core-api, worker : `npm run up`»* deydi, `package.json` dagi skript esa `docker compose up -d db cache core-api --wait` — ya'ni **`worker` hech qachon ko'tarilmasdi**. Bu 03-06 ning o'z niyatiga zid (*«`npm run up` uni ham ko'taradi»*) va `POST /discover` ning 202 qaytarib, yugurishning mangu `queued` qolishiga olib kelardi — aynan o'sha reja bloklamoqchi bo'lgan xulq.
- **Fix:** `"up": "docker compose up -d db cache core-api worker go2rtc --wait"`.
- **Nega darvozaga ta'sir qilmaydi:** `npm run gate` `up` ni chaqirmaydi (`test:sim` `sim:up` ni chaqiradi).
- **Committed in:** `f9f41eb`

**9. [Rule 3 — Bloklovchi] Konfiguratsiya darvozalari izohlarni FILTRLAYDI**

- **Found during:** Task 2 (`test_compose_does_not_publish_the_go2rtc_api_port` birinchi yugurishda qizardi)
- **Issue:** `compose.yaml` dagi izoh D-11 ni tushuntiradi va u yerda `1984` soni **atayin** yozilgan (o'qiyotgan odam qaysi port haqida gap ketayotganini bilishi kerak). Xom matn bo'yicha qidiruv darvozani **o'z sababi uchun** qizartirdi:
  ```
  AssertionError: go2rtc ning API porti compose'da ko'rinib qoldi
  '1984' is contained here: P API'si (1984) `PUT /api/streams?src=exec:<buyruq>`
  ```
  Bu 03-04/03-05/03-06 dagi `test_no_sim_branching` bilan **bir xil sinf** ziddiyat (grep kodni izohdan ajratmaydi), lekin **teskari yo'nalishda**: u yerda izohni tuzatish to'g'ri edi, bu yerda esa — parserni.
- **Fix:** `_go2rtc_service_lines()` xizmat blokining faqat KOD qatorlarini qaytaradi. Sabab test docstringida ochiq yozildi.
- **Committed in:** `f9f41eb`

**10. [Rule 3 — Bloklovchi] `wg0.conf.example` dan taqiqlangan LITERAL olib tashlandi**

- **Found during:** Task 3 verifikatsiyasi (`grep -c "0.0.0.0/0" ops/wireguard/wg0.conf.example` = **1**, mezon esa **0** talab qiladi)
- **Issue:** Yagona uchrash — faylning O'Z ogohlantirishi: *«`AllowedIPs` DA `0.0.0.0/0` HECH QACHON YOZILMAYDI»*. Ya'ni mezon o'z-o'zidan bajarilmas edi: fayl taqiqni tushuntirsa qizarardi, tushuntirmasa esa keyingi tahrirlovchi nimani yozmaslikni bilmasdi.
- **Fix:** Izoh taqiqni **tushunchа** bilan aytadi («to'liq tunnel, butun-internet CIDR'i») va literallar sanalgan joyni ko'rsatadi (`test_wireguard_config.py::FULL_TUNNEL_MARKERS`). Literal `README.md` da (u parse qilinmaydi) va testda qoldi.
- **Nega bu darvozani KUCHAYTIRADI:** endi ikkita mustaqil qatlam ishlaydi — parser (izohsiz, ikkala tomon) **va** sodda `grep -c` (istisnosiz). Izohga literal tushishiga ruxsat berilsa, ikkinchisi mangu o'lardi va uni tirik saqlash uchun istisnolar ro'yxati kerak bo'lardi.
- **Committed in:** `8eacce9`

**11. [Rule 3 — Bloklovchi] `monkeypatch.setattr` SATR nishoni bilan**

- **Found during:** Task 3, mypy
- **Issue:** `cameras.py` `Go2rtcClient` ni import qiladi, lekin RE-EXPORT qilmaydi; mypy `--no-implicit-reexport` ostida testdagi `module.Go2rtcClient` besh xato berdi.
- **Fix:** `monkeypatch.setattr("app.api.v1.cameras.Go2rtcClient", ...)` — satr nishoni mypy tekshiruvidan tashqarida va monkeypatch atributni O'ZI tiklaydi (03-06 Issue 2 ning darsi: tiklash, o'chirish emas).
- **Committed in:** `8eacce9`

### Rejadagi ziddiyatlar (NIYAT bajarildi, literal emas)

**A. `POST /cameras/{id}/live-token` Task 1 ga emas, Task 2 ga qo'yildi.**

Reja `cameras.py` ni faqat Task 1 ning `<files>` ida sanaydi va marshrutlar ro'yxatida `live-token` ni ham beradi. Ammo o'sha marshrut Task 2 ning artefaktlariga (`issue_live_token`, `Go2rtcClient`, `Settings.go2rtc_url`) tayanadi va Task 2 ning `<behavior>` bandi uni **nomma-nom** o'z ichiga oladi (*«`POST /api/v1/cameras/{id}/live-token` `CAMERA_VIEW` talab qiladi, `audit_log` ga `reason='live_view'` yozadi»*).

**Bajarilgani:** Task 1 reestrni va **ikkala** audit aliasini (`camera_view` + `live_view`) berdi (rejaning o'z talabi: *«ikkinchisini Task 2 ishlatadi»*), Task 2 esa marshrutni qo'shdi. Natijada **har ikkala commit ham yashil** — Task 1 dan keyin to'liq to'plam 1393 test bilan o'tdi.

**B. `list_cameras` dan `intent` ni olib tashlash darvozani QIZARTIRADI.**

Reja: *«SABOTAJ: `list_cameras` imzosidan `intent: CameraReadIntentDep` ni olib tashlash `test_camera_route_coverage.py` ni qizartirmaydi (u huquqni tekshiradi)»*.

**O'lchandi — bashorat bajarilmadi:** darvozaga IJOBIY JUFT test qo'shilgan (`test_camera_list_declares_the_read_audit`), ya'ni sabotaj **strukturaviy darvozani ham** qizartiradi (S4). Ijobiy juft nazorat holatining (`discovery-runs` auditsiz) qarshi tomoni: usiz fayl «auditni umuman qo'ymang» degan ma'noga siljib ketardi.

**C. `next_cursor` har doim `null`.**

Reja `CameraQuery` da `limit`/`cursor` ni talab qiladi, ammo `nvr_repo.list_cameras()` (03-04) keyset sahifalashni **qo'llamaydi**.

**Bajarilgani:** maydonlar kontraktda TURADI (`StallListResponse` bilan bir xil shakl), `next_cursor` esa har doim `null`. Sabab kodda yozilgan: bitta NVR eng ko'pi 32 kanal beradi (UI-SPEC §6.1) va bir bozorda bir-ikkita NVR bo'ladi, ya'ni kursor mexanikasi **bugun hech qanday muammoni hal qilmasdi**; maydonni olib tashlash esa chegara oshganda klient kontraktini buzardi. `limit` Pydantic darajasida cheklangan (`CAMERA_PAGE_SIZE_MAX = 200`) va so'ralgan hajmni o'lchamdan chiqarishni bloklaydi.

**D. `POST /{id}/archive` da `is_archived` filtri bilan tenant bo'yicha qidirish `list_cameras()` orqali.**

Reja repozitoriyga yangi metod (`get_camera`) qo'shishni talab qilmaydi va `files_modified` da `nvr_repo.py` yo'q. `camera_or_404()` mavjud `list_cameras(include_archived=True)` ustidan qidiradi; sabab funksiya docstringida: bir bozorda kameralar soni o'nlab (UI-SPEC §6.1: eng ko'pi 32) va yangi metod repozitoriyning yuzasini o'lchanmaydigan foyda uchun kengaytirardi.

### Rejadan ataylab chetlangan bandlar

**E. TDD RED/GREEN commitlari ajratilmadi.** Uchala task ham `tdd="true"`, `.planning/config.json` da esa `workflow.tdd_mode: false`. Faza konventsiyasi (03-02, 03-04, 03-05, 03-06) — har task uchun bitta commit. **RED dalili yo'qolmadi:** beshala sabotaj testlarning kodsiz qizarishini o'lchov bilan ko'rsatadi.

**F. `requirements mark-complete` ATAYIN BAJARILMADI.** Frontmatterda `requirements: [CAM-01, CAM-02, CAM-03]` bor, lekin bu reja ularning birortasini ham **yakunlamaydi**: CAM-02 va CAM-03 ning UI tomoni 03-10 da, matn qatlami esa 03-08 da. 03-01, 03-03, 03-04 va 03-06 ham aynan shu sababdan belgilamagan; belgilash `03-11` ning zimmasida.

**G. WireGuard konteyneri `compose.yaml` ga QO'SHILMADI** (reja shunday buyurgan). U `vpn` profili ostidagi deploy komponenti va uni dev/CI muhitida ko'tarish ma'nosiz: WireGuard **kernel moduli** Windows dev xostida yo'q, CI konteynerida esa `NET_ADMIN` berilmagan. Compose bandi `ops/wireguard/README.md` §4 da YAML bloki sifatida hujjatlashtirilgan — **8-faza deploy runbook'i uchun tayyor**, `SYS_MODULE` ni olib tashlash tavsiyasi bilan.

---

**Total deviations:** 11 auto-fixed (1 × Rule 1, 4 × Rule 2, 6 × Rule 3) + 4 ta rejadagi ziddiyat + 3 ta hujjatlashtirilgan chetlanish
**Impact on plan:** Scope creep yo'q. To'rtala Rule 2 tuzatishi ham **xavfsizlik teshigini** yopdi (ikkitasi T-03-46 ni butunlay chetlab o'tish yo'li edi); Rule 3 tuzatishlari rejaning O'Z maqsadini bajarilishi mumkin holga keltirdi.

## Issues Encountered

1. **`npm run gate` 10 daqiqalik buyruq chegarasidan oshdi** (932 s). Uni fon rejimida ishga tushirish kerak bo'ldi. Bu `03-11` uchun amaliy qayd: darvoza endi bir o'tirishda kutib bo'lmaydigan uzunlikda va 03-04 dan beri to'rt marta ketma-ket o'sdi (728 → 742 → 819 → **932 s**).
2. **`grep` ziddiyati BU FAZADA TO'RTINCHI marta** takrorlandi, lekin **birinchi marta teskari yo'nalishda**: 03-04/03-05/03-06 da kodni izohdan ajratmaslik **kodni** tuzatishni talab qilgan edi, bu yerda esa ikkita darvozaning ikkitasi ham **konfiguratsiya izohiga** urildi va yechim har safar boshqacha bo'ldi — birinchisida parserni izohsiz qilish (`compose.yaml`), ikkinchisida literalni fayldan olib tashlash (`wg0.conf.example`). Umumiy qoida: **darvoza tanlagan matn sinfini ochiq belgilashi kerak.**
3. **S3 sabotaji hech nimani qizartirmadi va bu XATO EMAS.** «403 jurnalga yozmaydi» kafolatini ikki mustaqil mexanizm ushlab turadi va ularning ikkinchisi (`BackgroundTasks` faqat muvaffaqiyatli javobga biriktiriladi) yolg'iz ham yetadi. Test DA'VONI o'lchaydi, mexanizmni emas — bu to'g'ri, lekin uni sabotaj bilan o'lchamasdan bilib bo'lmasdi.
4. **`fixtures.auth_api` da `bearer` YO'Q** (u `fixtures.admin_api` da). Import xatosi butun modulni yig'ilishida yiqitdi — arzon, lekin fixture modullarining bo'linishi aniq emasligini ko'rsatadi.

## Known Stubs

Yo'q. Beshala marshrut ham, `auth_request` nishoni ham to'liq ishlaydi.

Uchta **ochiq belgilangan soddalashtirish** bor:

| Joy | Soddalashtirish | Nega bu fazada yetarli |
|---|---|---|
| `CameraListResponse.next_cursor` | Har doim `null` | Bitta NVR eng ko'pi 32 kanal (UI-SPEC §6.1); maydon kontraktda turadi va chegara oshganda to'ldiriladi (ziddiyat **C**) |
| `Go2rtcClient.remove_stream` | Yozildi, LEKIN mahsulot yo'lida CHAQIRILMAYDI | Arxivlangan kamera uchun oqimni o'chirish 03-10 ning UI oqimiga bog'liq; hozircha arxiv holatini **ikkala** avtorizatsiya qatlami mustaqil tekshiradi, ya'ni ro'yxatda qolgan oqim ochilmaydi |
| WireGuard konteyneri | Faqat hujjatlashtirilgan | Chetlanish **G** — deploy komponenti, dev/CI da ko'tarib bo'lmaydi |

## Threat Flags

Yangi ishonch chegarasi ochilmadi. Reja `<threat_model>` idagi **o'n ikkala** band bajarildi:

| Threat | Holat |
|---|---|
| T-03-45 (go2rtc RCE) | ✅ **To'rt** qatlam (rejada uchta): port yo'q + `^/api/...` 403 + `^/live/api/...` 403 + allow-list. 8 rad etish yo'li; **sabotaj S1** chegarani AYNAN o'lchadi |
| T-03-46 (cross-tenant ko'rish) | ✅ Chipta OQIM NOMIGA bog'landi (**deviation 1** — rejada yo'q edi); cross-tenant token so'rovi 404; matritsa `camera_id` ni avtomatik qamraydi |
| T-03-47 (havolaning ulashilishi) | ✅ `exp <= 60s` (`issue_live_token` chegaradan katta TTL ni `ValueError` bilan rad etadi), `user_id` ga bog'langan, `aud="live"`; muddat alohida testda |
| T-03-48 (auditoriya) | ✅ **Ikki tomonlama** o'lchandi: chipta -> API = 401; access token -> `auth_request` = 403 |
| T-03-49 (izsiz ko'rish) | ✅ `reason="live_view"` reestr o'qishidan AJRATILGAN; 403 iz qoldirmaydi (nazorat testi); **sabotaj S3/S3b** ikkala mexanizmni ham ochdi |
| T-03-50 (`stream_name` UI'da) | ✅ `CameraRead` da maydon umuman yo'q; **12/12** marshrut rekursiv skanerlanadi |
| T-03-51 (`AllowedIPs = 0.0.0.0/0`) | ✅ IKKALA tomon CI'da parse qilinadi; `::/0` va ommaviy CIDR'lar ham; quyi chegara 2 peer; **sabotaj S2** |
| T-03-52 (buzilgan bozor qurilmasi) | ✅ Kripto-marshrutlash `README.md` §1 da; `SYS_MODULE` ni olib tashlash **qoida** sifatida yozildi |
| T-03-53 (kamerani o'chirib dalilni yo'qotish) | ✅ `DELETE` marshruti UMUMAN yo'q (`app.routes` ustidagi mexanik darvoza); `archive`/`restore` jufti ham tekshiriladi |
| T-03-54 (`X-Forwarded-For` mexanikasi) | ✅ `git diff` bo'yicha proxy sarlavhalari qatorlari **tegilmagan** (0 o'zgarish); `nginx -t` toza |
| T-03-SC (paket o'rnatish) | ✅ `pyproject.toml` va `frontend/package.json` diffi **bo'sh**; `alexxit/go2rtc:1.9.14` — CLAUDE.md da qulflangan versiya |

⚠ **03-11 uchun ochiq band (yangi flag emas, 03-04/03-06 ning davomi):** `audit-volume` remediatsiyasi (ustun bilan cheklangan audit trigger) hamon bajarilmagan. Bu reja audit hajmini **oshirdi**: har jonli ko'rish sessiyasi 5 daqiqada bir marta yangilanadi va **har yangilanish** bitta `audit_log` qatori yozadi (UI-SPEC §8.3). Bu **ataylab** — «kim ko'rdi» dalili aynan shu qatorlar; lekin saqlash siyosati bilan birga ko'rilishi kerak.

## Next Phase Readiness

**03-08 (frontend matni) uchun:**
- ⚠ **Yangi xato kodi qo'shilmadi** — `MARKET_ERROR_CODES` hamon **43** kod va `frontend/scripts/error-codes.test.mjs` bu rejada qizarmadi.
- `live-token` ning javob kodlari: **404** (yo'q/begona/arxivlangan), **403** (huquq yo'q), **503** `live_view_unavailable` (go2rtc javob bermadi). Oxirgisi `detail` satr sifatida keladi va u `MARKET_ERROR_CODES` da **yo'q** — 03-08 uni `errors.*` da qamrashi kerak yoki reyestrga qo'shilishi.
- UI-SPEC §9.1 ning G-4 darvozasi (`o'chirish`/`удалить` so'zlari taqiqi) **hali qurilmagan** — u 03-08 ning ishi. Backend tomonda fe'l allaqachon «arxivlash».

**03-10 (kamera yuzasi) uchun TAYYOR:**
- `GET /api/v1/cameras?nvr_id=&status=&archived=` — UI-SPEC §6.1 ning ikkala filtri ham.
- `POST /cameras/{id}/live-token` -> `{url, expires_in: 60, transport_hint: "webrtc"}`. `url` **opaque** va u `<video>` ga to'g'ridan-to'g'ri beriladi.
- ⚠ **Sessiya byudjeti UI ning ishi** (UI-SPEC §8.3): `LIVE_SESSION_MAX_MS = 300_000`, `LIVE_EXPIRY_WARNING_MS = 30_000`, `LIVE_CONNECT_TIMEOUT_MS = 15_000`. Backend faqat 60 soniyalik CHIPTA beradi; har yangilanish yangi `POST /live-token` va u avtorizatsiyani QAYTA tekshiradi hamda yangi audit qatori yozadi.
- ⚠ Frontendda **grep darvozasi** kerak (UI-SPEC §8.7): `/api/streams`, `exec:`, `ffmpeg:` satrlari `frontend/src` da bo'lmasligi shart. Bu darvoza hali **yo'q**.

**03-11 (yakuniy darvoza) uchun ochiq bandlar:**
1. `audit-volume` remediatsiyasi (03-04/03-06 dan meros; bu reja hajmni oshirdi).
2. `npm run test:sim:slow` fazani yopishdan oldin bir marta.
3. **`npm run gate` 932 s** — 03-01 ning 618 s nomzod chegarasi to'rtinchi marta buzildi; qayta o'lchash yoki `gate` ni bo'lish.
4. `worker` va `go2rtc` konteynerlari kod/config o'zgargandan keyin **`--build`** talab qiladi (03-06 Issue 1).
5. `.env` da `NVR_CREDENTIAL_KEY` bo'lmasa `npm run up` ko'tarilmaydi.
6. **`Go2rtcClient.remove_stream` mahsulot yo'lida chaqirilmaydi** — arxivlash oqimini go2rtc bilan sinxronlash 03-10/03-11 da ko'rilsin.

**8-faza (deploy runbook) uchun meros:**
- `ops/wireguard/README.md` §4 — `vpn` profili uchun tayyor compose bandi (`SYS_MODULE` siz).
- `ops/scripts/verify-tunnel.sh` — go-live checklist'ining bandi: `ops/scripts/verify-tunnel.sh 192.168.1.64`.
- ⚠ **WebRTC UDP 8555 firewall darajasida ochiladi**, compose `ports:` bilan EMAS: `ports:` Docker'ning `iptables` qoidalarini yozadi va u host firewall'ini CHETLAB O'TADI — «UFW da yopiq» degan ishonch yolg'on bo'lardi.

**04-faza (snapshot pipeline) uchun meros:**
- `Go2rtcClient` — `/api/frame.jpeg` uchun tayyor qobiq; `assert_safe_go2rtc_src` allow-listi **har** yangi `src` yo'liga ham qo'llanishi shart.
- ⚠ Kadr olish jadvali 25 kamerani **bir vaqtda** so'rasa go2rtc 25 oqimni birdan ochadi va A.5 dagi bitreyt chegarasiga urilinadi — yechim `stagger` (RESEARCH D.14).

## Self-Check: PASSED

- **Fayllar:** 21/21 mavjud (12 yangi + 9 o'zgargan)
- **Commitlar:** 4/4 mavjud (`0402481`, `f9f41eb`, `8eacce9`, `860edc8`)
- **`must_haves.artifacts` `contains`:** 4/4 — `unsafe_go2rtc_source` (`go2rtc.py`), `204` (`live_authz.py`), `auth_request` (`nginx.conf`), `AllowedIPs` (`wg0.conf.example`), `0.0.0.0/0` (`test_wireguard_config.py`)
- **`must_haves.key_links`:** 3/3 — `live` (`cameras.py` -> `issue_live_token`), `live-authz` (`nginx.conf` -> `/internal/live-authz`), `rtsp://` (`go2rtc.py` -> `PUT /api/streams`)
- **`DELETE` darvozasi:** kamera yuzasida `DELETE` marshruti = **0**
- **`grep -c "0.0.0.0/0" ops/wireguard/wg0.conf.example`** = **0**
- **`test -x ops/scripts/verify-tunnel.sh`** = mode `100755`
- **Ish daraxti:** beshala sabotajdan keyin ham **toza**

---
*Phase: 03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi*
*Completed: 2026-08-03*
