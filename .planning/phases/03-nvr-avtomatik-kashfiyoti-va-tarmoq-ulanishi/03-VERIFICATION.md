---
phase: 03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi
verified: 2026-08-04T00:35:00Z
status: human_needed
score: 7/8 must-haves verified
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 5/8
  previous_verified: 2026-08-03T15:59:39Z
  closure_plans: ["03-12", "03-13", "03-14"]
  gaps_closed:
    - "SC#6 — Direktor avtorizatsiyadan keyin panelda jonli kamera tasvirini KO'RADI (GAP-1)"
    - "SC#7 — Butun oqim simulyator ustida UCHIDAN-UCHIGA ishlaydi va CI'da o'lchanadi (GAP-2)"
  gaps_remaining: []
  regressions: []
  new_findings:
    - "Yopilish ishi mahsulot NUQSONINI ochdi va tuzatdi: `PUT /api/streams` bu o'rnatmada **400** qaytaradi (go2rtc oqimni xotiraga qo'shadi, keyin `:ro` `go2rtc.yaml` ga yozolmaydi). `raise_for_status()` ISHLAB TURGAN jonli ko'rishni doimiy 503 qilardi. Men buni mustaqil takrorladim."
deferred:
  - truth: "SC#5 ning 3-da'vosi — `ip route get <nvr_ip>` javobi `wg0` ni ko'rsatishi"
    addressed_in: "Ops / VPS deploy (03-HUMAN-UAT.md #1 va #2)"
    evidence: >-
      CI konteynerida `wg0` interfeysi yo'q; bunday test har doim yashil
      bo'lib hech nima isbotlamasdi (Pitfall 10). Boshqa ikki da'vo
      o'lchanadi. ROADMAP ning 2026-08-01 self-service direktivasi
      uskunasizlikni ATAYIN bloker qilmaydi. Egasi va tetigi nomlangan.
  - truth: "Real Hikvision firmware'ining XML shakli, kanal raqamlash chetlanishi va HAQIQIY sessiya limiti"
    addressed_in: "Rekvizit kelgan kun (03-HUMAN-UAT.md #3 va #4)"
    evidence: >-
      `tests/integration/test_real_nvr.py` (5 test, `hardware` markeri)
      tayyor va bloklamaydi — o'zim tasdiqladim: to'liq to'plamda
      1520/1525 to'planadi, aynan 5 tasi `hardware` sifatida deselect
      qilinadi.
human_verification:
  - test: "`ip route get <nvr_ip>` -> `wg0` (SC#5 ning 3-da'vosi)"
    expected: "Marshrut `wg0` orqali; tunnel o'chsa ulanish uziladi"
    why_human: "CI konteynerida `wg0` yo'q (Pitfall 10). Egasi Ops, tetigi VPS deploy"
  - test: "CGNAT ostidagi WireGuard tunnelining ko'tarilishi"
    expected: "Bozor tomonidagi qurilma rozetkaga ulangach o'zi qo'ng'iroq qiladi"
    why_human: "ISP topologiyasini simulyatsiya qilib bo'lmaydi. Egasi Ops"
  - test: "Real NVR'da kashfiyot — XML shakli va kanal raqamlash"
    expected: "`verify-real-nvr.sh` chiqishi sim fixture'lari bilan bir xil SHAKLDA"
    why_human: "Real firmware'ning kutilmagan shakli faqat qurilmada chiqadi"
  - test: "Bir vaqtdagi RTSP sessiya limitining HAQIQIY qiymati (D-05)"
    expected: "`rtsp.concurrent_failed` maydoni haqiqiy chegarani ko'rsatadi (6–16)"
    why_human: "Chegara firmware va bitreytga bog'liq; sim RTSP oyog'i buni modellamaydi"
  - test: "Jonli tasvirning BRAUZERDAGI ijrosi, sifati va kechikishi"
    expected: "Direktor panelda tasvirni ko'radi; transport badge'i haqiqiy transportni ko'rsatadi"
    why_human: >-
      ⚠ QAYTA TA'RIFLANGAN. Tasvir SERVER TOMONDA keladi va o'lchandi
      (99 681 baytli JPEG — o'zim takrorladim). O'lchanmagani — brauzerdagi
      IJRO va IDROK: jsdom `RTCPeerConnection` bermaydi
  - test: "Vendored `video-stream.js` / `video-rtc.js` kodini odam o'qishi"
    expected: "`eval`, `new Function`, tashqi fetch, obfuskatsiya yo'q"
    why_human: "SHA-256 qulfi O'ZGARMASLIKNI kafolatlaydi, XAVFSIZLIKNI emas"
---

# Phase 3: NVR avtomatik kashfiyoti va tarmoq ulanishi — Tekshiruv hisoboti (QAYTA)

**Faza maqsadi:** Admin saytga NVR manzili va login/parolini kiritadi — tizim Hikvision qurilmasini o'zi aniqlaydi, kanallarni sanab chiqadi va kameralarni avtomat qo'shadi; direktor jonli tasvirni panelda ko'radi.
**Tekshirildi:** 2026-08-04T00:35:00Z
**Holat:** `human_needed`
**Qayta tekshiruv:** HA — `gaps_found` (5/8, 2026-08-03) dan keyin; yopilish rejalari `03-12`, `03-13`, `03-14`

---

## Xulosa — bir jumlada

**Ikkala bo'shliq ham HAQIQATAN yopilgan va men buni SUMMARY da'volariga emas, o'z o'lchovlarimga tayanib tasdiqladim: maqsad jumlasining ikkinchi yarmi — «direktor jonli tasvirni panelda ko'radi» — endi mahsulot yo'lidan o'tib, mock'siz, 99 681 baytli haqiqiy JPEG kadr bilan isbotlanadi.**

Oldingi hisobotning markaziy topilmasi shu edi: bu **test qamrovi bo'shlig'i emas, mahsulot yo'lidagi ulanish uzilishi**. Shuning uchun bu safar birinchi ish — o'sha uzilishni **sabotaj bilan qayta ochish** va testning aynan o'sha joyda qizarishini talab qilish bo'ldi. Qizardi, aynan kutilgan assertda.

---

## Oldingi bo'shliqlarning yopilishi — men bajardim

### GAP-1: jonli ko'rish yo'li ULANMAGAN edi

Oldingi hisobotning to'rtta `missing[]` bandi. Har birini alohida tekshirdim:

| # | `missing[]` bandi | Holat | Men o'lchagan dalil |
|---|---|---|---|
| 1 | go2rtc'ga rekvizit yetkazadigan mexanizm (`decrypt_nvr_password` ning ikkinchi chaqiruv joyi) | ✓ YOPILGAN | `grep` -> `cameras.py:458` da **ikkinchi** chaqiruv joyi (birinchisi `discovery.py:429`). Zanjir: `rtsp_url()` -> `repo.get_credential()` -> `decrypt_nvr_password()` -> `authenticated_rtsp_source()` -> `ensure_stream()` |
| 2 | Kashfiyot hosil qilgan `stream_name`/`src` juftligini HAQIQATAN uzatadigan RTSP manbai | ✓ YOPILGAN | `nvr-sim:554` javob beradi. **Xom TCP DESCRIBE bilan o'zim tekshirdim** (test orqali emas) |
| 3 | `SIM_RTSP_HOST` ni yo iste'mol qilish, yo olib tashlash | ✓ YOPILGAN | Izohsiz qismda `SIM_RTSP_HOST` = **0**, `SIM_RTSP_PORT:` = **0**, `SIM_RTSP_PORT_ADVERTISED` = 1 (qoladi, `state.py` o'qiydi) |
| 4 | Mahsulot yo'lidan o'tadigan mock'siz uchidan-uchiga test | ✓ YOPILGAN | `test_live_view_e2e.py` — **2 passed (10.27 s)**, o'zim bajardim |

**Rekvizitsiz RTSP haqiqatan rad etiladi — testga ishonmasdan o'zim so'radim:**

```
RTSP/1.0 401 Unauthorized
WWW-Authenticate: Basic realm="ipcam"
WWW-Authenticate: Digest realm="ipcam", nonce="af2ac5ff...", algorithm="MD5"
```

Bu muhim, chunki **aynan shu narsa o'lchovga ma'no beradi**: manba anonim o'qishga ruxsat bersa, rekvizit oyog'i olib tashlanganda ham test yashil qolardi. Bundan tashqari ISAPI (8080) va RTSP (554) **bir xil manzilda** (`nvr-sim`) javob beradi — `network_mode: service:nvr-sim` da'vosi tasdiqlandi.

### GAP-2: zanjirning oxirgi bo'g'ini mock edi

`test_live_view_e2e.py` ni o'qib chiqdim. Zanjir haqiqatan chetlab o'tilmaydi:

1. `create_device` -> `run_discovery` -> `list_cameras` — mahsulot marshrutlari;
2. **direktor** `POST /cameras/{id}/live-token` chaqiradi — HAQIQIY `Go2rtcClient`;
3. `stream_name` **chipta javobining `url` idagi `src=` dan** olinadi;
4. `GET /api/frame.jpeg?src={stream_name}` — kadr keladi.

**«Oqim nomi o'ylab topilishi mumkinmi?» — YO'Q, va men buni izlab ko'rdim.** Nom `rtsp.py:126` da `f"cam_{uuid4().hex}"` sifatida tug'iladi, `nvr_repo.py:363` da kashfiyot yozadi, testga esa **faqat chipta URL'i orqali** yetib boradi. Sabotaj yugurishimda u `cam_1ee446207cdd4001bca29b0112666018` bo'lgan — test bunday qiymatni yozib qo'ya olmaydi. Meta-darvoza (`test_the_mockless_end_to_end_measurement_exists_and_runs`) uchta mustaqil da'voni majburlaydi: modul import qilinadi, `sim` markeri bor, va **birorta testining parametrida `go2rtc_calls` yo'q**.

---

## SABOTAJ — markaziy da'vo o'lchanadimi?

Bu hisobotning eng muhim o'lchovi. `cameras.py::_ensure_stream` dan rekvizit oyog'ini olib tashladim (manba yana rekvizitsiz `rtsp_url()` chiqishi bo'ldi):

```
FAILED test_live_view_e2e.py::test_a_frame_arrives_through_the_discovered_stream
AssertionError: `cam_1ee446...` uchun 45 s ichida JPEG kadr KELMADI:
  45 urinish, 45.0 s, oxirgi status 200, tana uzunligi 0 bayt
test_live_view_e2e.py:307
1 failed, 1 passed in 55.80s
```

**Aynan kutilgan shakl va bu tafsilot hal qiluvchi:**

* qizargani — **kadr asserti** (307-qator), sozlash xatosi EMAS;
* chipta baribir **200** keldi (`live_token_issued` jurnalda), oqim baribir ro'yxatga olindi (`go2rtc_stream_registered`) — ya'ni test qo'shni alomatni emas, **media oqishini** o'lchaydi;
* ikkinchi test (arxiv/avtorizatsiya) **yashil qoldi** — u rekvizitni emas, avtorizatsiyani o'lchaydi;
* go2rtc konteynerining O'Z jurnali sababni mustaqil tasdiqladi: `error="streams: user/pass not provided"`.

Fayl `git checkout` bilan tiklandi; `git diff --stat HEAD` — **bo'sh**.

---

## Mahsulot nuqsoni va uning tuzatilishi — mustaqil takrorladim

Yopilish ishi **haqiqiy mahsulot nuqsonini** ochdi. `PUT /api/streams` bu o'rnatmada 400 qaytaradi. Men buni SUMMARY dan emas, bevosita o'lchadim:

```
PUT status: 400
PUT body: yaml: line 38: did not find expected key
stream present after PUT: True
FRAME OK bytes= 99681 soi= ffd8ff
```

Ya'ni: go2rtc oqimni **xotiraga qo'shadi**, keyin uni `/config/go2rtc.yaml` ga yozmoqchi bo'ladi, fayl esa D-11 bo'yicha `:ro` — natijada 400. `raise_for_status()` ga so'zsiz ishonish **ishlab turgan** jonli ko'rishni doimiy 503 qilardi. Bu nosozlikni `go2rtc_calls` mock'i yashirgan edi va uni birinchi mock'siz o'lchov ochdi — bu oldingi hisobotning «mock zanjirni kesadi» da'vosining mustaqil tasdig'i.

**Tuzatishning JOYLASHUVI ham tekshirildi va u to'g'ri.** `ensure_stream` da qayta o'qish `except` blokidan **tashqarida**:

* `except` ichida `put_failure = _failure("PUT", exc)` faqat **yasaladi**, ko'tarilmaydi;
* qayta tekshiruv blokdan tashqarida bajariladi, ya'ni yangi istisnoning `__context__` i parol tashuvchi `httpx` URL'i BO'LMAYDI (T-03-87 qayta ochilmaydi);
* `raise put_failure from None` — `__cause__` ham bostiriladi.

**Tri-state `_registered()` fail-closed ekanini kod bilan tasdiqladim:** `None` = «ayta olmadim»; `ensure_stream` `is not True` bilan, `remove_stream` esa `is not False` bilan tekshiradi — ikkalasi ham noaniqlikda **nosozlik** tomoniga qaror qiladi.

**Farq atayin va u to'g'ri:** `remove_stream` `from delete_cause` ishlatadi — o'sha chaqiruvning URL'ida (`?src=cam_<uuid4>`) sir YO'Q, ya'ni sabab zanjirini bostirish diagnostikani bekorga yo'qotardi. Ikkala jurnal qatorini ham haqiqiy yugurishda ko'rdim: `go2rtc_stream_not_persisted` va `go2rtc_removal_not_persisted`.

---

## Kuzatiladigan haqiqatlar (ROADMAP ning sakkizala mezoni)

| # | Mezon | Oldin | Hozir | Dalil (men bajardim) |
|---|---|---|---|---|
| SC#1 | Faqat manzil+login/parol; model aniqlanadi, kanallar sanaladi, kameralar avtomat | ✓ | ✓ VERIFIED | Darvozada yashil; kashfiyot jurnalida `channels_added=6`, `rtsp_port=554`, `rtsp_port_assumed=False` |
| SC#2 | Qayta skan idempotent | ✓ | ✓ VERIFIED | `test_sc2_...` yashil |
| SC#3 | Xato sababi va tuzatish yo'li bilan | ✓ | ✓ VERIFIED | `test_sc3_...` yashil; 12 kod × 3 til |
| SC#4 | Parol Fernet; javobda ham, jurnalda ham ko'rinmaydi | ✓ | ✓ VERIFIED | `test_sc4_...` yashil; quyida D-12 ning yangi yuzalari ham tekshirildi |
| SC#5 | NVR faqat tunnel orqali; internetdan ochiq emas | ⚠ | ⚠ PARTIAL | 2/3 da'vo avtomat. 3-da'vo (`wg0`) — `deferred`, egasi Ops. **O'zgarishsiz va bu to'g'ri** |
| **SC#6** | **Direktor jonli tasvirni KO'RADI; avtorizatsiyasiz havola ishlamaydi** | **✗ FAILED** | **✓ VERIFIED** | Avtorizatsiya avvaldan isbotlangan; **tasvir endi keladi** — 99 681 bayt, sabotaj bilan tasdiqlangan |
| **SC#7** | **Butun oqim uchidan-uchiga ishlaydi va CI'da o'lchanadi** | **⚠ PARTIAL** | **✓ VERIFIED** | Oxirgi bo'g'in mock'siz kesib o'tiladi; meta-darvoza uni qulflaydi |
| SC#8 | WR-02 DB darajasida | ✓ | ✓ VERIFIED | `test_sc8_...` yashil |

**Ball: 7/8 to'liq tasdiqlandi** (oldin 5/8). Yagona to'liq bo'lmagani — SC#5, va uning ochiq da'vosi **uskuna/deploy yo'qligi**, muhandislik nuqsoni emas.

---

## D-12 — yopilish ishi uni ATAYIN bosim ostiga qo'ydi

`03-13` parolni go2rtc yetib boradigan joyga qo'ydi, ya'ni bu fazadagi eng sir-zich o'zgarish. To'rtala oqish yuzasini tekshirdim:

| Yuza | Yopilishi | O'lchov |
|---|---|---|
| `httpx` istisno matni (to'liq URL'ni tashiydi) | `_failure()` faqat amal + sinf nomi + status yozadi | `test_go2rtc_client.py` da `Sekret123` testi |
| Sentry breadcrumb (chiquvchi URL, query bilan) | `before_breadcrumb=_scrub_breadcrumb` | `test_sentry_scrub.py` — 3 ta breadcrumb testi |
| Sentry `stacktrace.frames[].vars` (lokal o'zgaruvchilar) | `_RTSP_USERINFO` zaxira naqshi + `_mask_deep` | `test_stack_frame_locals_lose_the_raw_source` |
| Assert xabaridagi interpolyatsiya | `source` xabarlardan olib tashlangan | `test_phase3_criteria.py` SC#7 |

**Foizli kodlash darvozasi HAQIQIY darvoza, ehtiyot chorasi emas:** `authenticated_rtsp_source()` `quote(..., safe="")` dan keyin natijani **qayta ajratib**, xost/port/yo'l/query/fragment tengligini talab qiladi va tengsizlikda `CREDENTIAL_INJECTION` bilan yiqiladi (T-03-88, avtoritet qayta yozilishi = SSRF).

**Eng kuchli mustaqil dalil — uchinchi tomon servisining O'Z jurnali:**

```
docker compose logs go2rtc | grep -c "Sim12345"   ->  0
grep -n "Sim12345|password|rtsp://" ops/go2rtc/go2rtc.yaml  ->  faqat 19-qatordagi IZOH
streams: {}   (bo'sh — birorta rekvizit konfiguratsiyaga muhrlanmagan)
```

Ya'ni parol na go2rtc jurnalida, na uning konfiguratsiyasida. D-12 **kengaytirilgan yuzada ham** saqlanadi.

---

## 17 qaror (D-01…D-17) — bosim ostidagilar qayta tekshirildi

| Qaror | Holat | Dalil |
|---|---|---|
| **D-11** (go2rtc foydalanuvchiga ochilmaydi) | ✅ | Uchala qatlam joyida: 1984 publish qilinmaydi; nginx `^/(api/streams\|api/config\|api/restart)` **va** `^/live/api/(streams\|config\|restart)` -> 403; `/live/` allow-listi `$` bilan anchorlangan va `frame.jpeg` ham `auth_request` ortida. `mediamtx.yml` da `api: false` |
| **D-12** (parol hech qayerda) | ✅ | Yuqoridagi jadval + go2rtc jurnali/konfiguratsiyasi toza |
| **D-03** (401 ni qayta urinmaslik) | ✅ | `test_nvr_errors.py:234` — `after - before == 1` (auth); `:205` — `== 0` (soat farqi). **O'zgarishsiz** |
| D-01, D-02, D-04…D-10, D-13…D-17 | ✅ | Oldingi tekshiruvdan o'zgarmagan; darvoza yashil |

**17/17 hurmat qilingan.** Yopilish ishi birortasini yumshatmadi: `rtsp_url()` hamon parol parametrini **qabul qilmaydi** (T-03-24 strukturasi saqlanib qoldi — sir alohida modulda, `SecretStr` ichida tashiladi).

---

## 03-07 ning xavfsizlik tuzatishlari — REGRESSIYA YO'Q

| Tuzatish | Holat | Dalil |
|---|---|---|
| `_stream_matches()` `src` ni chiptadagi kamera qatori bilan solishtiradi | ✅ | `live_authz.py` — `return not camera.is_archived and camera.stream_name == stream` **joyida** |
| Nginx ikkala 403 bloki | ✅ | `nginx.conf:75-76` va `:80-81` |
| `/live/` anchorlangan allow-list | ✅ | `nginx.conf:95` — `^/live/(api/ws\|api/webrtc\|api/frame\.jpeg\|api/stream\.m3u8\|api/hls/.+)$` |

---

## Darvoza — o'zim bajardim, uchdan-uchgacha

`npm run gate` -> **exit 0**. Sanoqlar SUMMARY da'volari bilan **aynan** mos:

| Qadam | Natija | Holat |
|---|---|---|
| `lint` (ruff + format + mypy) | Toza · 202 formatlangan · **196 fayl, muammo yo'q** | ✓ |
| `pytest` (to'liq) | **1520 passed**, 0 fail (dotlarni sanab tasdiqladim) | ✓ |
| i18n pariteti | **576 kalit × 3 til**, drift yo'q | ✓ |
| vitest | **246 passed** (20 fayl) | ✓ |
| node darvozalari | **86 pass, 0 fail** | ✓ |
| typecheck / lint / build | exit 0 | ✓ |
| `requirements:check` | 49 talab MOS · **Done 11 · Blocked 1** | ✓ |
| `validation:check` | `nyquist_compliant: true` — 43 Per-Task · 6 inson bandi | ✓ |

**Darvozadan `test:tenancy` va `test:sim` olib tashlangani QAMROVNI KAMAYTIRMAGAN — buni alohida tekshirdim**, chunki bu jimgina yo'qotish bo'lishi mumkin edi:

* to'liq to'plam: **1520/1525** (5 deselected = `hardware`);
* `tests/tenancy`: **412** — `testpaths = ["tests"]` ostida 1520 ning ICHIDA;
* `-m sim`: **77** (oldin 70; yangi `test_rtsp_source`, `test_compose_sim_env`, `test_live_view_e2e` hisobiga) — u ham 1520 ning ichida.

Ya'ni 31 % qayta bajarishning olib tashlanishi **takrorni** kesgan, qamrovni emas.

---

## `nyquist_compliant` — HISOBLANADI, yozilmaydi (qayta tasdiqlandi)

Bayroqqa ishonmasdan hisob-kitobni sinadim:

| Qadam | Natija |
|---|---|
| Skript joriy holatda | `true — hisob-kitob bilan MOS. Per-Task: 43 · inson bandlari: 6` |
| Bayroq qo'lda `false` ga o'zgartirilganda | `HISOB-KITOBGA MOS EMAS (hisoblangani: true)` — **rad etdi** |
| Fayl tiklangandan keyin | Toza |

**Bayroq haqiqatan hisob-kitob, kelishuv emas.** Per-Task qatorlari 33 dan 43 ga o'sgan — uchala yopilish rejasining tasklari kiritilgan.

---

## Talablar qamrovi — dalil bilan

| Talab | Holat | Mening hukmim | Dalil |
|---|---|---|---|
| CAM-01 | Done | ✅ SATISFIED | O'zgarishsiz |
| CAM-08 | Done | ✅ SATISFIED | O'zgarishsiz |
| **CAM-03** | `Blocked` -> **Done** | ✅ **SATISFIED** | (a) avtorizatsiya — avvaldan; (b) media yo'li — `test_live_view_e2e.py`, 99 681 baytli JPEG. **Men mustaqil takrorladim.** Qolgan idrok qismi `03-HUMAN-UAT.md` #5 ga chiqarilgan va dalil satrida ochiq aytilgan |
| **CAM-09** | `Blocked` -> **Done** | ✅ **SATISFIED** | Beshala bandi o'lchanadi; «kadr olish yo'li» aynan `/api/frame.jpeg` orqali — 4-fazaning standart mexanizmi |
| **CAM-02** | **Blocked (o'zgarmadi)** | ✅ **TO'G'RI** — nuqson emas | CI'da `wg0` yo'q. Egasi (Ops), tetigi (VPS deploy), vositasi (`verify-tunnel.sh`) va bandlari (`03-HUMAN-UAT.md` #1, #2) **nomlangan** |

`check-requirements-sync.mjs` exit 0. **Yetim talab yo'q.**

**CAM-02 ning `Blocked` qolgani — bu hisobotning ijobiy topilmasi.** Ikkita talabni dalil bilan ko'targan va uchinchisini dalilsiz ko'tarmagan yopilish ishi o'z holatlarini **halol** boshqargan.

---

## `03-HUMAN-UAT.md` — oltita band

Oltalasi ham «Kim bajaradi» + «Qachon» + `expected:` + `result: [pending]` bilan yozilgan; `03-VALIDATION.md` ning `human_only_verifications` bloki bilan **bir xil to'plam** (skript 6 ni sanaydi).

**5-band halol qayta ta'riflangan va bu muhim.** Eski matn: «AVVAL GAP-1 yopilishi shart: bugungi kod bilan tasvir umuman kelmaydi». Yangi matn: **«tasvir kelmaydi» EMAS — «tasvir keladi, uning brauzerdagi ijrosi va idroki o'lchanmagan»**, ikkita mustaqil sabab bilan (jsdom `RTCPeerConnection` bermaydi; «sifat» perseptual baho). Bu aynan to'g'ri chegara: server tomon o'lchandi, brauzer tomon o'lchanmadi — va hech qayerda o'lchangan deb ko'rsatilmayapti.

Fayl «Bu fazada nima YOPILDI» bo'limi bilan boshlanadi va `test_live_view_e2e.py` ni nomma-nom ko'rsatadi. Ro'yxatning qisqargani tasodif emasligi ochiq yozilgan.

---

## Anti-naqshlar

| Tekshiruv | Natija |
|---|---|
| `TBD` / `FIXME` / `XXX` (bloker markerlar) | **0** — oxirgi 12 commit'ning barcha manba fayllarida |
| `TODO` / `HACK` / `PLACEHOLDER` yangi yopilish fayllarida | **0** |
| `ruff` / `mypy` | Toza (196 fayl) |
| `compose.yaml:345` `SIM_RTSP_HOST` (oldingi ⚠ WARNING) | **YO'Q QILINGAN** + `test_compose_sim_env.py` regressiyani to'sadi |

Oldingi hisobotning yagona ⚠ ogohlantirishi yopilgan. Yangi darvoza o'z-o'zini qanoatlantirmaydi: skaner **o'z faylini** iste'molchilar to'plamidan chiqaradi va quyi chegarasi bor (`MIN_SIM_KEYS`, `CONSUMERS >= 50`) — noto'g'ri yo'lda bo'sh to'plamda jimgina yashil bo'lmasligi uchun. Qo'shimcha: `SIM_PASSWORD` ning compose'dagi qiymati bilan `mediamtx.yml` dagi parol **mexanik ravishda** solishtiriladi.

---

## Nima ISBOTLANDI va nima ISBOTLANMADI

**ISBOTLANDI (qayta tekshiruvda qo'shilgani qalin):**
- ISAPI kashfiyot mantiqi real dumplar ustida; xato taksonomiyasi; D-03 ning retry siyosati
- Idempotentlik, shifrlash, RBAC, RLS, kaskad qo'riqchisi
- **Rekvizit oyog'i — go2rtc'ga alohida kanal bilan uzatiladi va sir hech qayerga sizmaydi**
- **Media HAQIQATAN oqadi: kashfiyot -> chipta -> autentifikatsiyalangan RTSP -> JPEG kadr**
- **4-fazaning oldingi sharti (`/api/frame.jpeg`) ishlaydi — oldingi hisobot buni «oldingi shart» deb nomlagan edi**

**ISBOTLANMADI (va hech qayerda isbotlangan deb ko'rsatilmayapti):**
- Real firmware'ning XML chetlanishlari va kanal raqamlash o'ziga xosliklari
- HAQIQIY sessiya/bitreyt chegarasi — sim RTSP oyog'i (MediaMTX) sessiya limitini **umuman modellamaydi** va bu ochiq yozilgan
- Tunnel marshrutlanishi (`wg0`)
- **Tasvirning BRAUZERDA ijro etilishi va idroki** — server tomon o'lchandi, mijoz tomon yo'q

Bu chegaralar uskuna/deploy yo'qligidan kelib chiqadi va ROADMAP ning 2026-08-01 self-service direktivasi ularni **ATAYIN** bloker qilmaydi. Oldingi hisobotdagi GAP-1 esa boshqa toifada edi — **muhandislik nuqsoni** — va aynan shuning uchun yopilishi talab qilingan edi. U yopildi.

---

## Bo'shliqlar xulosasi

**Bo'shliq qolmadi.** Oldingi hisobotning ikkala bo'shlig'i ham yopilgan va ikkalasi ham **da'vo bilan emas, o'lchov bilan** yopilgan:

* GAP-1 — sabotaj bilan tasdiqladim: rekvizit oyog'i olib tashlanganda test **aynan kadr assertida** qizaradi, chipta esa 200 bo'lib qolaveradi;
* GAP-2 — mock'siz o'lchov mavjud, meta-darvoza bilan qulflangan, va u `gate` zanjirida haqiqatan bajariladi.

Qo'shimcha ijobiy signal: yopilish ishi **o'z yo'lida mahsulot nuqsonini topdi** (`PUT` -> 400 -> doimiy 503) va uni sirni qayta ochmaydigan joylashuv bilan tuzatdi. Bu — mock'siz o'lchovning birinchi kunidayoq qaytargan foydasi va oldingi hisobotning «mock zanjirni kesadi» tashxisini mustaqil tasdiqlaydi.

**Holat `passed` emas, `human_needed` — chunki oltita band inson tekshiruvini kutmoqda.** Ularning birortasi ham fazani bloklamaydi va birortasi ham «o'lchandi» deb ko'rsatilmagan. Muhandislik yetkazmalari bo'yicha faza **tugallangan** va 4-fazaga o'tishga tayyor: uning standart kadr olish yo'li endi ulangan va o'lchangan.

---

*Verified: 2026-08-04T00:35:00Z*
*Verifier: Claude (gsd-verifier) — goal-backward, FORCE stance, qayta tekshiruv*
*Oldingi: 2026-08-03T15:59:39Z — `gaps_found`, 5/8*
