---
phase: 03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi
verified: 2026-08-03T15:59:39Z
status: gaps_found
score: 5/8 must-haves verified
overrides_applied: 0
re_verification:
  previous_status: null
  previous_score: null
  note: "Initial verification — 03-VERIFICATION.md mavjud emas edi"
gaps:
  - truth: "SC#6 — Direktor avtorizatsiyadan keyin panelda jonli kamera tasvirini KO'RADI"
    status: partial
    reason: >-
      Avtorizatsiya qismi to'liq isbotlangan (sabotaj bilan tasdiqladim), lekin
      jumlaning ikkinchi yarmi — «tasvirni ko'radi» — na o'lchangan, na
      ULANGAN. Bu FAQAT test qamrovi bo'shlig'i emas (03-11 shunday deb
      nomlagan), balki MAHSULOT YO'LIDAGI ulanish uzilishi: go2rtc'ga
      yuboriladigan `src` da RTSP rekviziti YO'Q va uni beradigan kod
      umuman mavjud emas. `decrypt_nvr_password` butun ilovada BIR joyda
      chaqiriladi — `jobs/discovery.py:429` (ISAPI kashfiyoti). Jonli
      ko'rish yo'lida (`api/v1/cameras.py::_ensure_stream`) u chaqirilmaydi.
      `03-RESEARCH.md:262` esa aynan buni talab qiladi: «parol ... faqat
      go2rtc konfiguratsiyasi hosil qilinayotganda ochiladi (D.13)».
      Tavsiflangan mexanizm KODDA YO'Q.
    artifacts:
      - path: "services/core-api/app/services/rtsp.py"
        issue: >-
          `rtsp_url(host, port, channel_no, *, substream)` — rekvizit
          parametri yo'q (ataylab, T-03-24). Natijada hosil bo'ladigan
          `rtsp://host:port/Streaming/Channels/N` real Hikvision NVR'da
          401 oladi. Sirni yashirish qarori to'g'ri; unga MOS keladigan
          ikkinchi yarim (go2rtc'ga rekvizitni alohida uzatish) yozilmagan.
      - path: "services/core-api/app/api/v1/cameras.py"
        issue: >-
          `_ensure_stream()` (371–396) `src` ni faqat `host`, `rtsp_port`,
          `channel_no` dan quradi; `nvr_credentials` ga umuman murojaat
          qilmaydi.
      - path: "ops/go2rtc/go2rtc.yaml"
        issue: >-
          `streams: {}` bo'sh va faylda birorta rekvizit/`username` bloki
          yo'q — ya'ni parol go2rtc tomonda ham berilmaydi.
      - path: "compose.yaml"
        issue: >-
          `SIM_RTSP_HOST: go2rtc-sim` (345-qator) o'rnatilgan, lekin uni
          BIRORTA kod o'qimaydi (`nvr-sim` faqat `SIM_RTSP_PORT_ADVERTISED`
          ni ishlatadi). O'lik konfiguratsiya — RTSP oyog'i hech qachon
          ulanmaganining bevosita dalili.
      - path: ".planning/phases/03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi/03-VALIDATION.md"
        issue: >-
          `open_items` dagi yopilish yo'li («go2rtc-sim'dan bitta kadr olib
          JPEG ekanini tekshirish») bo'shliqni YOPMAYDI: u mahsulot
          yo'lini chetlab o'tadi. Kashfiyot `cam_<uuid4>` nomini va
          `rtsp://<nvr>:554/...` manbasini hosil qiladi; `go2rtc-sim` esa
          `sim_cam_01…06` ni boshqa xostda e'lon qiladi va `nvr-sim`
          554-portni umuman tinglamaydi. Taklif qilingan test aynan
          Pitfall 4 (simulyatorning o'zini o'zi tasdiqlashi) bo'lardi.
    missing:
      - "go2rtc'ga RTSP rekvizitini yetkazadigan mexanizm (kashfiyotdan tashqarida `decrypt_nvr_password` ning ikkinchi chaqiruv joyi)"
      - "Kashfiyot hosil qilgan `stream_name`/`src` juftligini HAQIQATAN uzatadigan RTSP manbai — `nvr-sim` 554 ni tinglashi yoki `go2rtc-sim` ni mahsulot yo'liga bog'lash"
      - "`SIM_RTSP_HOST` ni yoki iste'mol qilish, yoki compose'dan olib tashlash"
      - "Mahsulot yo'lidan o'tadigan (mock'siz `Go2rtcClient`) bitta uchidan-uchiga jonli ko'rish testi"
  - truth: "SC#7 — Butun oqim simulyator ustida UCHIDAN-UCHIGA ishlaydi va CI'da o'lchanadi"
    status: partial
    reason: >-
      Zanjir «forma -> saqlash -> kashfiyot -> poll -> kameralar ro'yxati ->
      jonli ko'rish CHIPTASI» gacha bir sessiyada haqiqatan kesib o'tiladi
      (o'zim bajardim: 9 passed). Lekin SC#7 «yuqoridagi oqim» deydi va
      unga SC#6 ham kiradi. Oxirgi bo'g'inda `Go2rtcClient` MOCK bilan
      almashtiriladi (`test_phase3_criteria.py` `go2rtc_calls`
      fixture'i, `test_live_view.py:108`), ya'ni media hech qachon
      oqmaydi. Zanjir chiptada tugaydi, tasvirda emas.
    artifacts:
      - path: "tests/integration/test_phase3_criteria.py"
        issue: >-
          `test_sc7_...` `go2rtc_calls` mock'idan foydalanadi va
          `ensure_stream` ga uzatilgan `src` satrini tekshiradi —
          go2rtc'ning javobini emas.
    missing:
      - "Zanjirning oxirgi bo'g'inini mock'siz kesib o'tadigan o'lchov (GAP-1 yopilgandan keyin)"
deferred:
  - truth: "SC#5 ning 3-da'vosi — `ip route get <nvr_ip>` javobi `wg0` ni ko'rsatishi"
    addressed_in: "Ops / VPS deploy (03-VALIDATION.md § human_only_verifications)"
    evidence: >-
      CI konteynerida `wg0` interfeysi yo'q; bunday test har doim yashil
      bo'lib hech nima isbotlamasdi (Pitfall 10). Test buni ochiq
      «QO'LDA» deb belgilaydi va faqat vositasining
      (`ops/scripts/verify-tunnel.sh`) mavjudligini tekshiradi — ya'ni
      o'lchanmagan narsa «o'lchandi» deb ko'rsatilmayapti.
  - truth: "Real Hikvision firmware'ining XML shakli, kanal raqamlash chetlanishi va HAQIQIY sessiya limiti"
    addressed_in: "Rekvizit kelgan kun (ops/docs/nvr-onboarding.md §4)"
    evidence: >-
      ROADMAP ning 2026-08-01 self-service direktivasi uskunasizlikni
      ATAYIN bloker qilmaydi. `tests/integration/test_real_nvr.py`
      (5 test, `hardware` markeri) va `ops/scripts/verify-real-nvr.sh`
      tayyor va ishlaydi — o'zim tasdiqladim: `pytest -m hardware` ->
      5 skip, exit 0; `--collect-only` -> 5/1462.
human_verification:
  - test: "Jonli tasvirning sifati va kechikishi (idrok o'lchovi)"
    expected: "Direktor panelda tasvirni ko'radi; kechikish qabul qilinadigan"
    why_human: "Perseptual baho — real tarmoq, real kamera, real ekran. jsdom `RTCPeerConnection` bermaydi. ⚠ AVVAL GAP-1 yopilishi shart: bugungi kod bilan tasvir umuman kelmaydi."
  - test: "CGNAT ostidagi WireGuard tunnelining ko'tarilishi"
    expected: "Bozor tomonidagi qurilma rozetkaga ulangach o'zi qo'ng'iroq qiladi"
    why_human: "ISP topologiyasini simulyatsiya qilib bo'lmaydi"
  - test: "`ip route get <nvr_ip>` -> `wg0` (SC#5 ning 3-da'vosi)"
    expected: "Marshrut `wg0` orqali; tunnel o'chsa ulanish uziladi"
    why_human: "CI konteynerida `wg0` yo'q (Pitfall 10)"
  - test: "Real NVR'da kashfiyot — XML shakli va kanal raqamlash"
    expected: "`verify-real-nvr.sh` chiqishi sim fixture'lari bilan mos"
    why_human: "Real firmware'ning kutilmagan shakli faqat qurilmada chiqadi"
  - test: "Bir vaqtdagi RTSP sessiya limitining HAQIQIY qiymati (D-05)"
    expected: "`rtsp.concurrent_failed` maydoni haqiqiy chegarani ko'rsatadi"
    why_human: "Chegara firmware va bitreytga bog'liq"
  - test: "Vendored `video-stream.js` / `video-rtc.js` kodini odam o'qishi"
    expected: "`eval`, `new Function`, tashqi fetch, obfuskatsiya yo'q"
    why_human: "SHA-256 qulfi O'ZGARMASLIKNI kafolatlaydi, XAVFSIZLIKNI emas"
---

# Phase 3: NVR avtomatik kashfiyoti va tarmoq ulanishi — Tekshiruv hisoboti

**Faza maqsadi:** Admin saytga NVR manzili va login/parolini kiritadi — tizim Hikvision qurilmasini o'zi aniqlaydi, kanallarni sanab chiqadi va kameralarni avtomat qo'shadi; direktor jonli tasvirni panelda ko'radi.
**Tekshirildi:** 2026-08-03T15:59:39Z
**Holat:** `gaps_found`
**Qayta tekshiruv:** Yo'q — birinchi tekshiruv

---

## Xulosa — bir jumlada

**Maqsad jumlasining BIRINCHI yarmi to'liq bajarilgan va men uni o'zim bajarib tasdiqladim; IKKINCHI yarmi («direktor jonli tasvirni panelda ko'radi») bajarilmagan — va sabab 03-11 aytganidan chuqurroq: bu test qamrovi bo'shlig'i emas, mahsulot yo'lidagi ULANISH uzilishi.**

`03-11` ning o'z-o'zini baholashi — CAM-01/CAM-08 `Done`, CAM-02/CAM-03/CAM-09 `Blocked` — **asosan to'g'ri va halol**. Bitta muhim tuzatish bilan: CAM-03 ning `Blocked` sababi **kam baholangan**.

---

## Kuzatiladigan haqiqatlar (ROADMAP ning sakkizala mezoni)

| # | Mezon | Holat | Dalil (men bajardim) |
|---|---|---|---|
| SC#1 | Admin faqat manzil+login/parol kiritadi; model aniqlanadi, kanallar sanaladi, kameralar avtomat yaratiladi | ✓ VERIFIED | `test_sc1_...` o'tdi. RTSP porti HAQIQATAN kashf etiladi: `adminAccesses` fixture'ida **HTTP=80 BIRINCHI**, RTSP=554 ikkinchi — sodda «birinchi `portNo`» implementatsiyasi 80 berardi, test esa 554 va `rtsp_port_assumed is False` ni talab qiladi |
| SC#2 | Qayta skan idempotent (yangi qo'shiladi, yo'qolgani `offline`, mavjudi tegilmaydi) | ✓ VERIFIED | `test_sc2_...` o'tdi (uch ketma-ket skan; admin qo'ygan nom saqlanadi) |
| SC#3 | Xato **sababi va tuzatish yo'li** bilan ko'rsatiladi | ✓ VERIFIED | `test_sc3_...` o'tdi. Uch tilning HAR BIRIDA `errorCause` **12** kalit, `errorFix` **12** kalit, bo'shi **0**, sababsiz tuzatish **0** — JSON'ni bevosita o'qib tekshirdim |
| SC#4 | Parol Fernet bilan shifrlangan; API javobida ham, jurnalda ham ko'rinmaydi | ✓ VERIFIED | `test_sc4_...` o'tdi. `nvr_credentials` da trigger YO'Qligi `pg_trigger` katalogidan o'qiladi (`test_nvr_credentials_has_no_audit_trigger`) — kod ta'rifidan emas |
| SC#5 | NVR faqat tunnel orqali; internetdan to'g'ridan-to'g'ri ochiq emas | ⚠ PARTIAL | 2/3 da'vo avtomat: ommaviy IP -> 422 `nvr_host_public_blocked`; `wg0.conf.example` da `AllowedIPs = 10.10.0.2/32, 192.168.1.0/24`, butun-internet CIDR'i **yo'q** (D-13). 3-da'vo ochiq «QO'LDA» deb belgilangan — **halol**, deferred'ga chiqarildi |
| SC#6 | Direktor avtorizatsiyadan keyin jonli tasvirni **ko'radi**; avtorizatsiyasiz havola ishlamaydi | ✗ FAILED (partial) | Avtorizatsiya **to'liq isbotlangan** (quyida sabotaj bilan). «Tasvirni KO'RADI» — o'lchanmagan **va ulanmagan**. GAP-1 |
| SC#7 | Butun oqim simulyator ustida uchidan-uchiga ishlaydi va CI'da o'lchanadi | ⚠ PARTIAL | Zanjir chiptagacha bir sessiyada kesib o'tiladi (o'zim: 9 passed). Oxirgi bo'g'in mock — media oqmaydi. GAP-2 |
| SC#8 | WR-02: `market_delete_draft()` DB darajasida cheklanadi | ✓ VERIFIED | `test_sc8_...` o'tdi: `DELETE FROM markets` ilova qatlamini **butunlay chetlab o'tib** `23514` (CheckViolation) oladi; B bozori tegilmaydi |

**Ball: 5/8 to'liq tasdiqlandi** (2 partial, 1 failed-partial).

---

## Kechiktirilgan bandlar (keyingi bosqich egaligida)

| # | Band | Egasi | Nega bu NUQSON EMAS |
|---|---|---|---|
| 1 | SC#5 ning 3-da'vosi (`ip route get` -> `wg0`) | Ops, VPS deploy | CI'da `wg0` yo'q; soxta yashil test yozish yomonroq bo'lardi (Pitfall 10). Test buni yashirmaydi — vositasining mavjudligini tekshiradi va qolganini ochiq «QO'LDA» deb belgilaydi |
| 2 | Real firmware XML shakli, kanal raqamlash, HAQIQIY sessiya limiti | Ops + ijrochi | ROADMAP ning 2026-08-01 self-service direktivasi uskunasizlikni ATAYIN bloker qilmaydi. `hardware` to'plami tayyor: `pytest -m hardware` -> **5 skip, exit 0** (o'zim bajardim) |

---

## GAP-1 — batafsil: jonli ko'rish yo'li ULANMAGAN (uskuna yo'qligi EMAS)

Bu hisobotning eng muhim topilmasi va u `03-11` da **nomlanmagan**.

`03-11` bo'shliqni shunday tavsiflaydi: «`go2rtc-sim` haqiqiy RTSP test-oqimlarini beradi, lekin **birorta test undan kadr olmaydi**» — ya'ni **test qamrovi** muammosi. Kodni o'qib boshqa narsa topdim: **test yozilgan taqdirda ham u ishlamasdi**, chunki mahsulot yo'lining o'zi uzilgan.

**Uch mustaqil uzilish:**

1. **RTSP rekviziti umuman uzatilmaydi.** `decrypt_nvr_password` butun ilovada **BIR** joyda chaqiriladi — `jobs/discovery.py:429`. Jonli ko'rish yo'lida (`api/v1/cameras.py::_ensure_stream`, 371–396) `nvr_credentials` ga murojaat **yo'q**. Hosil bo'ladigan manba — `rtsp://<host>:<port>/Streaming/Channels/<N>`, rekvizitsiz. Real Hikvision NVR bunga **401** beradi.

   `03-RESEARCH.md:262` aynan buni talab qiladi:
   > «parol URL'ga hech qachon kirmaydi — u alohida, shifrlangan holda turadi va **faqat go2rtc konfiguratsiyasi hosil qilinayotganda ochiladi** (D.13)»

   Sirni URL'dan chiqarish qarori **to'g'ri**. Unga mos keladigan ikkinchi yarim — rekvizitni go2rtc'ga boshqa kanal bilan berish — **yozilmagan**. `ops/go2rtc/go2rtc.yaml` da ham `streams: {}` bo'sh va birorta `username`/`password` bloki yo'q.

2. **Simulyatorda mos keladigan RTSP nishoni yo'q.** Kashfiyot `cam_<uuid4>` nomini va `rtsp://<nvr-sim>:554/...` manbasini hosil qiladi. `go2rtc-sim` esa `sim_cam_01…06` ni **boshqa xostda** e'lon qiladi, `nvr-sim` esa **554-portni umuman tinglamaydi** (buni `03-11` ning o'zi `test_three_concurrent_rtsp_sessions` ❌ natijasida qayd etgan).

3. **O'lik konfiguratsiya — bevosita dalil.** `compose.yaml:345` da `SIM_RTSP_HOST: go2rtc-sim` bor, lekin uni **birorta kod o'qimaydi** (`nvr-sim` faqat `SIM_RTSP_PORT_ADVERTISED` ni ishlatadi). Bu — RTSP oyog'ini ulash **niyat qilingan, lekin bajarilmagan** ekanining mexanik izi.

**Nega bu muhim:** `03-VALIDATION.md` ning `open_items` da taklif qilingan yopilish yo'li — «`go2rtc-sim`'dan bitta kadr olib JPEG ekanini tekshirish» — bo'shliqni **yopmaydi**. U mahsulot yo'lini chetlab o'tib, sim'ning o'z oqimini to'g'ridan-to'g'ri o'qiydi. Bu aynan **Pitfall 4** — simulyatorning o'zini o'zi tasdiqlashi — ya'ni faza boshqa joylarda ehtiyotkorlik bilan qochgan tuzoq. Yashil test paydo bo'lardi, maqsad jumlasi esa baribir isbotlanmagan qolardi.

**Klassifikatsiya:** bu **muhandislik nuqsoni**, uskuna yo'qligi emas. Self-service direktivasi uni oqlamaydi: SC#7 «real qurilmaga o'tish **sozlama** o'zgarishi bo'ladi, kod o'zgarishi emas» deydi — bugungi holatda esa jonli ko'rishni ishga tushirish **kod yozishni** talab qiladi.

---

## `03-11` ning o'z-o'zini baholashi — mening hukmim

| `03-11` ning da'vosi | Hukm |
|---|---|
| CAM-01 `Done` | ✅ **To'g'ri.** Qo'shish/sozlash, Fernet shifri va «ulanishni tekshirish» — uchalasi ham o'lchanadi va o'tadi |
| CAM-08 `Done` | ✅ **To'g'ri.** Avtomat kashfiyot, idempotentlik va sabab+tuzatish uchalasi ham mustaqil o'lchanadi. RTSP portining kashf etilishi fixture shakli bilan HAQIQATAN majburlanadi |
| CAM-02 `Blocked` | ✅ **To'g'ri va halol.** Tunnel CI'da yo'q; 2-da'vo o'lchangan, 1-da'vosi ochiq nomlangan |
| CAM-03 `Blocked` | ⚠️ **To'g'ri, LEKIN sababi kam baholangan.** «Birorta test iste'mol qilmaydi» deyilgan; aslida mahsulot yo'lining o'zi ulanmagan (GAP-1) |
| CAM-09 `Blocked` | ✅ **To'g'ri.** Profil, kashfiyot va ulanish testi o'lchangan; jonli ko'rish emas |
| «SC#7 yashil, CAM-09 `Blocked` — ziddiyat EMAS» | ⚠️ **Qisman.** CAM-09 dan kengroq bo'lgani rost. Lekin SC#6 «yuqoridagi oqim» ga KIRADI, ya'ni SC#7 ning o'zi ham to'liq yashil emas |

**Umumiy baho: o'z-o'zini baholash na juda qattiq, na juda yumshoq — deyarli aniq.** `Done` qo'yilgan ikkitasi haqiqatan `Done`; `Blocked` qo'yilgan uchtasi haqiqatan bloklangan. Yagona tuzatish — CAM-03 ning chuqurligi.

---

## Ikki xavfsizlik teshigi — IKKALASI HAM YOPILGAN

### 1. Chipta oqimga bog'lanmagan edi (cross-tenant chegara buzilishi)

`_stream_matches()` (`app/api/internal/live_authz.py:132-165`) HAQIQATAN `src` ni chiptadagi kameraning qatori bilan solishtiradi:

```python
return not camera.is_archived and camera.stream_name == stream
```

**Men buni sabotaj bilan sinadim** — `&& camera.stream_name == stream` bo'lagini olib tashlab testlarni bajardim:

```
FAILED tests/integration/test_live_view.py::test_token_does_not_work_for_another_cameras_stream
assert 204 == 403
1 failed, 18 passed
```

**AYNAN** kutilgan test, **AYNAN** to'g'ri assertda qizardi. Fayl `git checkout` bilan tiklandi, ish daraxti toza. Qo'shimcha: `_single()` parameter-pollution (`?t=a&t=b`) ni ham rad etadi — nginx birinchisini, go2rtc oxirgisini tanlashi mumkin bo'lgan klassik chetlab o'tish yo'li.

### 2. `/live/api/streams` go2rtc API'siga yetib borardi (RCE yuzasi)

`ops/nginx/nginx.conf` da **ikkala** blok ham bor:

```nginx
location ~ ^/(api/streams|api/config|api/restart) { return 403; }
location ~ ^/live/api/(streams|config|restart)   { return 403; }
```

`/live/` ning o'zi ham **allow-list** (qora ro'yxat emas) va `$` bilan yopilgan. Uchala qatlam ham joyida: (1) 1984-port publish qilinmaydi, (2) nginx 403, (3) `assert_safe_go2rtc_src` faqat `rtsp://` ni o'tkazadi — `strip()`/`lower()` **qo'llanmasdan** (kanonizatsiya farqida chetlab o'tish yashiringan bo'lardi). 38 ta test o'tadi, jumladan `test_nginx_blocks_the_api_path_through_the_live_prefix` — u konfiguratsiya faylini **o'qiydi**.

---

## 17 qaror (D-01…D-17)

| Qaror | Holat | Dalil |
|---|---|---|
| D-01 (faqat manzil+parol) | ✅ | SC#1; `test_phase3_criteria.py` da `rtsp://` literali **0** marta (o'zim: `grep -c` = 0) |
| D-02 (sabab + tuzatish) | ✅ | 12 kod × 3 til, bo'shi yo'q |
| **D-03 (401 ni HECH QACHON qayta urinmaslik)** | ✅ | **Eng yuqori xatarli va HAQIQATAN qulflangan.** `test_auth_failure_is_not_retried`: `after - before == 1`; `test_clock_drift_detected_before_auth`: `after - before == 0`. Sanoq simulyatordan o'qiladi va **test tomonidan yozila olmaydi** |
| D-04 (real dump fixture'lari) | ✅ | Har fixture'da manba qayd etilgan: `github.com/maciej-or/hikvision_next`, «dumpdan VERBATIM» |
| D-05 (sessiya limiti ikkala shaklda) | ✅ | `parametrize("limit_mode", ["reject", "silent"])` |
| D-06 (`taskiq`, `arq` emas) | ✅ | `taskiq==0.12.4` + `taskiq-redis==1.2.3` `[project] dependencies` da; navbat kutubxonasi faqat `worker.py` da ko'rinadi |
| D-07 (`tunnel_subnet` global noyob) | ✅ | `0012` da bozorlar aro noyoblik indeksi (`(market_id, tunnel_subnet)` EMAS) |
| D-08 (chipta `exp<=60s`, `aud="live"`) | ✅ | `LIVE_TOKEN_MAX_TTL_SECONDS = 60`, `LIVE_TOKEN_AUDIENCE = "live"`; access token bilan almashtirish ikki yo'nalishda ham rad etiladi |
| D-09 (6 kanal CI, 25 slow) | ✅ | `npm run test:sim` -> 70; `test:sim:slow` -> 1 |
| D-10 (soft-delete) | ✅ | `is_archived`; `test_archive_keeps_the_row` |
| **D-11 (go2rtc foydalanuvchiga ochilmaydi)** | ✅ | Yuqoridagi uch qatlam |
| D-12 (parol hech qayerda ko'rinmaydi) | ✅ | SC#4 `old_value` + `new_value` + `changed_keys` ni ham o'qiydi |
| D-13 (`AllowedIPs` faqat NVR subneti) | ✅ | `10.10.0.2/32, 192.168.1.0/24`; `0.0.0.0/0` yo'q |
| D-14 (CGNAT — mahsulot muammosi emas) | ✅ | `PersistentKeepalive`, runbook'da 2 qadam; `grep -ci "ssh"` = 0 |
| D-15 (`CAMERA_MANAGE` yaratilgan) | ✅ | `rbac.py:117-119`; `CAMERA_VIEW` dan ajratilgan |
| D-16 (`httpx` prod deps'ga) | ✅ | `pyproject.toml:47` `[project] dependencies` da, izohi bilan |
| D-17 (WR-02 DB darajasida) | ✅ | SC#8 |

**17/17 hurmat qilingan.**

---

## Sxema va ko'p-ijarachilik invariantlari

| Da'vo | Holat | Dalil |
|---|---|---|
| `cameras` da `rtsp_url` ustuni YO'Q | ✅ | `test_cameras_has_no_rtsp_url_column` — `pg_attribute` dan o'qiydi |
| `nvr_credentials` audit triggeridan chiqarilgan | ✅ | `test_nvr_credentials_has_no_audit_trigger` — `pg_trigger` dan o'qiydi |
| Har jadvalda `market_id` + RLS ENABLE + FORCE + policy | ✅ | `test_every_table_is_tenant_scoped` jadvallarni `pg_class` dan **dinamik** oladi — yangi jadval avtomatik qamraladi (CLAUDE.md majburiyati) |
| RTSP porti kashf etiladi, 554 taxmin qilinmaydi | ✅ | Fixture'da HTTP=80 birinchi; test 554 ni talab qiladi |
| `BYPASSRLS` roli yo'q | ✅ | `pg_roles` tekshiruvi |

---

## Xulq-atvor tekshiruvlari — men bajardim

| Tekshiruv | Buyruq | Natija | Holat |
|---|---|---|---|
| Faza darvozasi | `pytest tests/integration/test_phase3_criteria.py` | **9 passed** (18.53 s) | ✓ PASS |
| Sim to'plami | `pytest -m "sim and not slow"` | **70 passed** | ✓ PASS |
| `hardware` bloklamaydi | `pytest -m hardware` | **5 skipped**, exit 0 | ✓ PASS |
| `hardware` to'planadi | `pytest -m hardware --collect-only` | **5/1462** (1457 deselected) | ✓ PASS |
| Jonli ko'rish + go2rtc | `pytest test_live_view.py test_go2rtc_client.py` | **38 passed** | ✓ PASS |
| NVR tenancy meta | `pytest tests/tenancy/test_nvr_domain_meta.py` | **4 passed** | ✓ PASS |
| Kamera marshrut qamrovi | `pytest tests/tenancy/test_camera_route_coverage.py` | **22 passed** | ✓ PASS |
| Backend sifat | `npm run lint` | ruff ✅ · 195 formatted · mypy: **189 fayl, muammo yo'q** | ✓ PASS |
| Frontend testlar | `npx vitest run` | **246 passed** (20 fayl) | ✓ PASS |
| Node darvozalari | `node --test scripts/*.test.mjs` | **86 pass, 0 fail** | ✓ PASS |
| i18n pariteti | `npm run i18n:check` | **576 kalit × 3 til**, drift yo'q | ✓ PASS |
| Frontend typecheck | `npm run typecheck` | exit 0 | ✓ PASS |
| Talablar sinxroni | `npm run requirements:check` | 49 talab MOS · Done 9 · Blocked 3 | ✓ PASS |
| **Sabotaj: chipta bog'lanishi** | `_stream_matches` dan `stream_name` solishtiruvi olib tashlandi | **AYNAN** `test_token_does_not_work_for_another_cameras_stream` qizardi (`204 == 403`) | ✓ PASS |

**`03-11` ning barcha sanoq da'volari mening bajarishimda AYNAN tasdiqlandi.** Hisobot raqamlarni bo'rttirmagan.

---

## `nyquist_compliant` — HISOBLANADI, yozilmaydi

Bayroqqa ishonmasdan hisob-kitobning o'zini ikkala yo'nalishda sinadim:

| Qadam | Natija |
|---|---|
| `node scripts/check-validation-signoff.mjs 03-VALIDATION.md` | `true — hisob-kitob bilan MOS. Per-Task: 33 · inson bandlari: 6`, exit **0** |
| Bayroq qo'lda `false` ga o'zgartirilganda | `HISOB-KITOBGA MOS EMAS (hisoblangani: true)`, exit **1** |
| Fayl tiklangandan keyin | exit **0**, `git status` toza |

Skript `[Automated Command]` ustunining bo'shligini, `BAJARILMADI` qoldig'ini, `human_only_verifications` ning to'rtala kalitini va `automated_replacements` ni tekshiradi. **Bayroq haqiqatan hisob-kitob, kelishuv emas.**

---

## Uch «tishlamagan» sabotaj — tuzatishlari o'lchaydimi?

| Sabotaj | Topilma | Tuzatish o'lchaydimi? |
|---|---|---|
| `03-09` S3 (`page.tsx` ichidagi qaror) | Marshrut faylidagi sof qaror sabotajdan omon o'tdi — **hech nima qizarmadi** | ✅ **Ha.** `cameraEmptyKind` `components/` ga chiqarildi va endi mustaqil o'lchanadi |
| `03-10` S3 (L0: dialog ochilishida token so'ralmasligi) | Test **to'g'ri** qizardi, lekin **noto'g'ri assertda** — `expect(apiFetch).not.toHaveBeenCalled()` o'tib ketardi | ✅ **Ha.** Endi mikrotask navbati bo'shatiladi: `await act(async () => { await vi.advanceTimersByTimeAsync(1_000); })` **keyin** assert. Markaziy da'vo endi HAQIQATAN o'lchanadi |
| `03-10` G-4 (izohdagi literal) | Darvoza o'z izohi ustida qizardi | ✅ Izoh qayta yozildi, darvoza **o'zgartirilmadi** — to'g'ri yo'nalish |

**Uchalasi ham topilma sifatida ochiq yozilgan va uchalasining tuzatishi ham haqiqiy.** Bu — kuchli signal: faza sabotajlarni marosim sifatida emas, o'lchov sifatida ishlatgan.

---

## `03-11` ning beshta yopilgan bandi

| # | Band | Hukm |
|---|---|---|
| 1 | Darvoza vaqti / chegara | ✅ Halol: uch martadan o'lchangan, 31 % qayta bajarish **nomlangan** va tuzatilmagani sababi bilan yozilgan |
| 2 | `requirements mark-complete` | ✅ `requirements:check` exit 0; `Blocked` sabablari yozilgan |
| 3 | `remove_stream` chaqirilmaydi | ✅ Qoldiq ta'sir HAQIQATAN chegaralangan: arxivlangan kamera 404 oladi (test bor), `rtsp_url()` parolni **umuman qabul qilmaydi** (imzoni tasdiqladim) |
| 4 | Audit hajmi | ✅ O'lchov bilan qabul qilingan; qayta ochish sharti nomlangan |
| 5 | Sim testlari testcontainer'ni ko'taradi | ✅ O'lchangan va rad etilgan — 70 dan 32 tasi bazani talab qiladi |

**Beshalasi ham jimgina tashlanmagan** — yo yopilgan, yo sababi bilan qabul qilingan.

---

## Anti-naqshlar

| Tekshiruv | Natija |
|---|---|
| `TBD` / `FIXME` / `XXX` (bloker markerlar) | **0** — 265 o'zgargan manba faylida |
| `TODO` / `HACK` / `PLACEHOLDER` | **0** |
| `ruff` / `mypy` | Toza |

**Nol qarz markeri — bu faza uchun kuchli natija.**

| Joy | Kuzatuv | Og'irlik |
|---|---|---|
| `compose.yaml:345` `SIM_RTSP_HOST` | O'rnatilgan, hech kim o'qimaydi — o'lik konfiguratsiya | ⚠ WARNING (GAP-1 ning izi) |
| `setup-status.cameras` | Har doim `0` (`markets.py:248`) | ℹ INFO — ochiq stub deb e'lon qilingan, birorta mezon unga tayanmaydi |
| `ops/nginx/nginx.conf;C` | Bo'sh katalog, git'da kuzatilmaydi | ℹ INFO — zararsiz artefakt, o'chirilsa bo'ladi |

---

## Talablar qamrovi

| Talab | Reja da'vosi | Mening hukmim | Dalil |
|---|---|---|---|
| CAM-01 | Done | ✅ **SATISFIED** | SC#1–SC#4; `test_nvr_api.py`, `test_nvr_secrets.py`, `test_nvr_errors.py` |
| CAM-08 | Done | ✅ **SATISFIED** | SC#1–SC#3; idempotentlik va port kashfiyoti fixture shakli bilan majburlanadi |
| CAM-02 | Blocked | ⚠ **NEEDS HUMAN** (uskuna/deploy) | 2-da'vo o'lchangan; tunnel CI'da yo'q — **nuqson emas** |
| CAM-03 | Blocked | ✗ **BLOCKED** (muhandislik) | Avtorizatsiya ✅; media yo'li **ulanmagan** — GAP-1 |
| CAM-09 | Blocked | ✗ **BLOCKED** (muhandislik) | Profil/kashfiyot/ulanish testi ✅; jonli ko'rish sim ustida ishlamaydi — GAP-1 |

**Yetim talab yo'q:** `REQUIREMENTS.md` Phase 3 ga aynan shu beshtasini biriktiradi.

---

## Simulyator nimani isbotlaydi va nimani ISBOTLAMAYDI

Faza **ataylab** real uskunasiz tekshirildi (CAM-09, 2026-08-01 direktivasi). Bu **qonuniy**, lekin chegarasi aniq aytilishi kerak.

**ISBOTLAYDI:**
- ISAPI kashfiyot mantiqi real yozib olingan dumplar ustida ishlaydi (D-04 — fixture'lar o'ylab topilgan emas)
- Xato taksonomiyasi va D-03 ning qayta urinish siyosati raqam bilan qulflangan
- Idempotentlik, shifrlash, RBAC, RLS, kaskad qo'riqchisi
- «Kod o'zgarishi emas» — ilova kodida sim izi **yo'q** (`test_no_sim_branching`)

**ISBOTLAMAYDI:**
- Real firmware'ning XML chetlanishlari, kanal raqamlash o'ziga xosliklari
- HAQIQIY sessiya/bitreyt chegarasi (sim `TINY_JPEG`, 160 bayt — **protokol modeli, piksel emas**)
- Tunnel marshrutlanishi
- **Jonli tasvirning o'zi** — va bu simulyator cheklovi EMAS, kod cheklovi (GAP-1)

**2-fazaning darsi qo'llanildi:** yashil darvoza maqsadga yetilganini isbotlamaydi. Shuning uchun 1448+ yashil testga qaramay maqsad jumlasi bo'yicha orqaga ishladim va sabotaj bilan sinadim.

---

## Bo'shliqlar xulosasi

Faza **o'z ishining sifati bo'yicha kuchli**: 17/17 qaror hurmat qilingan, ikkala xavfsizlik teshigi yopilgan (birinchisini sabotaj bilan tasdiqladim), nol qarz markeri, `nyquist_compliant` haqiqatan hisoblanadi, va o'z-o'zini baholash deyarli aniq — `Blocked` qo'yilgan uchta talab haqiqatan bloklangan, `Done` qo'yilgan ikkitasi haqiqatan bajarilgan.

Maqsad jumlasining **birinchi yarmi to'liq bajarilgan**. **Ikkinchi yarmi bajarilmagan** va yagona haqiqiy bo'shliq shu.

Muhim nyuans: bu bo'shliq **uskuna yo'qligi sababli emas**. Self-service direktivasi uskunasizlikni bloker qilmaydi — lekin jonli ko'rish **simulyator ustida ham** ishlamaydi, chunki go2rtc'ga rekvizit uzatilmaydi va kashfiyot hosil qilgan oqim nishoni hech qayerda tinglanmaydi. SC#7 «real qurilmaga o'tish **sozlama** o'zgarishi bo'ladi, kod o'zgarishi emas» deydi; bugungi holatda jonli ko'rishni ishga tushirish **kod yozishni** talab qiladi.

`03-VALIDATION.md` dagi taklif qilingan yopilish yo'li ham yetarli emas: u mahsulot yo'lini chetlab o'tadi va aynan faza boshqa joylarda qochgan Pitfall 4 ga tushadi.

**Tavsiya:** 4-fazaga o'tishdan oldin GAP-1 yopilsin. U 4-fazaning **oldingi sharti**: kadr olishning standart yo'li — go2rtc `/api/frame.jpeg` — aynan shu ulangan RTSP sessiyasiga tayanadi. Bugun ulanmagan holda 4-faza birinchi kunidayoq shu devorga uriladi.

---

*Verified: 2026-08-03T15:59:39Z*
*Verifier: Claude (gsd-verifier) — goal-backward, FORCE stance*
