---
status: resolved
trigger: "TEST-REPORT.md Topilma №7: sahifa almashishda sessiya to'satdan o'chadi (POST /api/v1/auth/refresh -> 401)"
created: 2026-08-14
updated: 2026-08-14
---

## Symptoms

DATA_START
**Expected:** Foydalanuvchi sahifaga o'tganda sessiya saqlanadi. Ruxsati yo'q sahifada — toza "ruxsat yo'q" holati yoki dashboard'ga redirect, lekin sessiya TIRIK qoladi.

**Actual:** To'liq sahifa navigatsiyasida ba'zan butun sessiya o'chadi: `POST /api/v1/auth/refresh -> 401 Unauthorized`, foydalanuvchi `/uz/login` ga uloqtiriladi. Ikki marta, ikki xil rolda kuzatildi:
1. Kassir (+998901111111) `/uz/users` ga URL orqali o'tganda.
2. Direktor (+998902222222) o'z navigatsiyasidagi "Patta hisobi" (`/uz/billing`) havolasini bosganda — bu havolani ilova O'ZI ko'rsatgan.

**Errors:** Tarmoq jurnali: `POST http://localhost:8081/api/v1/auth/refresh → 401 Unauthorized`, so'ng `GET /uz/login?_rsc=... → 200`. Oldingi navigatsiyalarda xuddi shu refresh 200 qaytargan (masalan snapshots sahifasida).

**Timeline:** 2026-08-14, avtonom UI test sessiyasida, yangi ko'tarilgan dev stekda. Avval ishlagan-ishlamagani noma'lum — auth kodi 1-fazadan beri mavjud.

**Reproduction:**
- Stek: `npm run up` + `API_HOST_PORT=8001 docker compose up -d core-api --wait` + `PROXY_HOST_PORT=8081 API_HOST_PORT=8001 docker compose up -d frontend nginx --wait` (8000/8080 portlarni boshqa loyiha band qilgan). UI: http://localhost:8081
- Kassir hisobi: +998901111111 / KassirTest-2026 → login → URL panelida `/uz/users` ga o'tish → login sahifasiga uloqtiriladi.
- Yoki direktor: +998902222222 / DirektorTest-2026 → login → chap navda "Patta hisobi" bosish.
- Repro deterministikligi noma'lum — poyga bo'lishi mumkin (har doim emas ehtimoli bor).

**Kontekst-gipotezalar (tekshirilmagan):**
1. Refresh-token ROTATSIYA poygasi: to'liq sahifa yuklanishida parallel so'rovlar (RSC prefetch + page load) bir vaqtda refresh chaqiradi; biri eski tokenni ishlatadi; reuse-detection butun sessiya oilasini bekor qiladi. Dalil-ishora: audit jurnalida "Eski sessiya kaliti qayta ishlatildi" hodisa turi MAVJUD (`/uz/audit` filtrlarida ko'rindi).
2. RBAC ko'zgu nomuvofiqligi: direktor navida `/uz/billing` havolasi ko'rsatiladi — backend rad etishi mumkin (`rbac.ts` vs `rbac.py`). Bu logoutni tushuntirmaydi, lekin alohida nuqson bo'lishi mumkin.
3. E'tibor: kassir birinchi marta parol almashtirgandan KEYIN ham (yangi sessiya) hodisa takrorlangan — must_change oqimiga bog'liq emas.

**Muhit eslatmalari:** cv-service to'xtatilgan (modelsiz, ataylab); nvr-sim ishlab turibdi; bularning auth'ga aloqasi yo'q deb taxmin qilinadi.
DATA_END

## Current Focus

status: TUZATILDI, TEKSHIRILDI va JONLI TASDIQLANDI (brauzer: nazoratchi birinchi kirish -> parol almashtirish -> to'liq navigatsiya -> refresh 200, sessiya tirik; 2026-08-14)

next_action: "Foydalanuvchi brauzerda tasdiqlasin: login -> parol almashtirish -> TO'LIQ sahifa navigatsiyasi (F5 yoki boshqa bo'limga o'tish) -> sessiya TIRIK qolishi kerak"

reasoning_checkpoint:
  hypothesis: "`POST /auth/change-password` foydalanuvchining BARCHA refresh oilalarini bekor qiladi (auth.py:875 `refresh_revoke_user`) VA brauzerdagi refresh cookie'ni o'chiradi (auth.py:890 `clear_refresh_cookie`), lekin parolni almashtirgan QURILMA uchun o'rniga yangi sessiya BERMAYDI. Natijada brauzerda faqat xotiradagi access token (15 daq) qoladi; to'liq sahifa navigatsiyasi xotirani tozalaydi -> `restoreSession()` cookie'siz `/auth/refresh` chaqiradi -> auth.py:682 `if not refresh_token` -> 401 -> /uz/login."
  confirming_evidence:
    - "Vaqt korrelyatsiyasi 100%: kassir 07:31:57 change-password 204 -> 07:32:20 va 07:32:32 refresh 401; direktor 07:40:25 change-password 204 -> 07:40:53 refresh 401. Parol almashtirilmagan sessiyalarda refresh HAR DOIM 200 (kassirning 2-sessiyasida 4 ta ketma-ket 200)."
    - "DB: direktor oilasi `ded52566` ning revoked_at = 12:40:25.772547 va audit `password_changed`.at = 12:40:25.772547 — millisoniyagacha bir xil, bitta tranzaksiya."
    - "Jonli tajriba (09:54:24-26): login -> change-password 204 javobida `set-cookie: sbozor_rt=\"\"; Max-Age=0; Path=/api/v1/auth` -> keyingi refresh 401 `invalid_refresh`."
    - "Falsifikatsiya jufti: cookie'SIZ refresh 401 -> HECH QANDAY log yozuvi yo'q; BEKOR QILINGAN cookie bilan refresh 401 -> `refresh_on_dead_family` log yozuvi CHIQDI. Asl hodisada bunday yozuv umuman yo'q edi -> asl 401'lar aynan 'cookie yo'q' shoxidan."
  falsification_test: "Agar sabab shu bo'lsa, change-password'dan KEYIN yangi refresh cookie berilsa, o'sha sessiyada refresh 200 qaytarishi SHART. Agar tuzatishdan keyin ham 401 qolsa — gipoteza noto'g'ri."
  fix_rationale: "Ildiz sabab — 'barcha sessiyalarni o'ldirish' bilan 'joriy qurilmani qayta tiklash' qadamining YO'QLIGI. Simptom (401) emas, aynan shu yetishmayotgan qadam tuzatiladi: revoke'dan KEYIN joriy qurilma uchun YANGI oila + yangi cookie beriladi. `refresh_revoke_user` saqlanadi, ya'ni ASVS V7 kafolati ('boshqa hamma sessiya o'ladi') buzilmaydi."
  blind_spots: "WR-02/CR-01 tahdid modeli: o'g'irlangan access token yangi oila ocha olmasligi kerak. Bu yerda xavf YO'Q, chunki `change_password` `current_password` ni tekshiradi (auth.py:865) — ya'ni yangi sessiya faqat joriy parolni BILGAN kishiga beriladi (qayta autentifikatsiya). Admin `reset-password` qilgan holatda hujumchi yangi vaqtinchalik parolni bilmaydi, demak bu yo'l u uchun yopiq. Ikkinchi ko'r nuqta: `market_id is None` (bozor tanlamagan platforma admini) — unda refresh cookie umuman bo'lmaydi, shuning uchun u holat eski xulqda (cookie tozalash) qoldiriladi."

separate_defect_check:
  question: "Direktorning `/uz/billing` havolasi ALOHIDA RBAC ko'zgu nomuvofiqligimi?"
  answer: "YO'Q — alohida nuqson YO'Q."
  evidence: "`billing_collect_view` frontend `rbac.ts:108` (director) va backend `rbac.py:247` (Role.DIRECTOR) da IKKALASIDA ham bor. Jonli tekshiruv: direktor tokeni bilan `GET /billing/pending`, `/billing/pending?day=...`, `/billing/charges?day=...` — uchalasi ham 200. Ya'ni havola to'g'ri ko'rsatilgan va backend ruxsat beradi. Direktorning logouti aynan yuqoridagi ildiz sabab (28 s oldin parol almashtirilgan)."

applied_action: "BAJARILDI — auth.py `change_password` ga `SettingsDep` qo'shildi, `refresh_revoke_user` dan KEYIN joriy qurilma uchun `_issue_session_cookie(...)` chaqiriladi (market_id mavjud bo'lsa), aks holda eski `clear_refresh_cookie` xulqi saqlanadi"

## Evidence

- timestamp: 2026-08-14 (tekshiruv 1)
  checked: "frontend/src/lib/api-client.ts:149-186 — refresh chaqiruvi"
  found: "Single-flight refresh MAVJUD (`refreshInFlight`, T-01-67). Butun frontend'da `/auth/refresh` ga boshqa chaqiruv yo'q (grep: faqat api-client.ts)."
  implication: "Bitta hujjat ichida parallel refresh bo'lishi mumkin emas — poyga gipotezasi zaiflashdi."

- timestamp: 2026-08-14 (tekshiruv 2)
  checked: "services/core-api/app/repositories/auth_repo.py:330-340 — refresh_rotate"
  found: "`UPDATE ... WHERE revoked_at IS NULL` atomar, rowcount qaytaradi — ikki parallel so'rovdan faqat bittasi g'olib."
  implication: "Rotatsiya poygaga qarshi to'g'ri himoyalangan."

- timestamp: 2026-08-14 (tekshiruv 3 — HAL QILUVCHI)
  checked: "docker compose logs core-api — refresh_reuse_detected / refresh_on_dead_family / refresh_token_rejected"
  found: "Bu yozuvlarning BIRORTASI YO'Q. Shu bilan birga structlog ishlayapti (`password_hash_unreadable`, `market_created`, `headline_unavailable` info/warning yozuvlari ko'rinadi)."
  implication: "401 javoblar LOGSIZ shoxdan kelgan. auth.py'da logsiz 401 shoxlari: (a) `not refresh_token` (682), (b) `row is None` (691), (c) muddati o'tgan, (d) user nofaol, (e) a'zolik yo'q."

- timestamp: 2026-08-14 (tekshiruv 4 — HAL QILUVCHI)
  checked: "audit_log: action ILIKE %refresh%/%reuse%"
  found: "REFRESH_REUSE_DETECTED qatori NOL ta. Jadvaldagi action turlari: insert/delete/read/update/login/login_failed/password_changed/logout/market_selected."
  implication: "Reuse-detection HECH QACHON ishga tushmagan. UI filtridagi 'Eski sessiya kaliti qayta ishlatildi' — shunchaki enum varianti, ma'lumot emas. Asosiy gipoteza yiqildi."

- timestamp: 2026-08-14 (tekshiruv 5)
  checked: "refresh_tokens jadvali holati"
  found: "25 token, 4 oila, TIRIK 0 ta. Ikkita oila atigi BITTA tokendan iborat va rotatsiyasiz bekor qilingan: `4ff0835b` (kassir 019fff25, 12:31:32) va `ded52566` (direktor 019fff26, 12:40:07, revoked_at=12:40:25.772547)."
  implication: "Bu oilalar rotatsiya orqali emas, TASHQI bekor qilish orqali o'lgan."

- timestamp: 2026-08-14 (tekshiruv 6 — SABABNI OCHDI)
  checked: "audit_log 12:39:50-12:41:00 oralig'i + auth hodisalari timeline"
  found: "Direktor: 12:40:07 login -> 12:40:25.772547 `password_changed`. Oila `ded52566` ning revoked_at AYNAN 12:40:25.772547 — millisoniyagacha bir xil (bitta tranzaksiya). Kassir: 12:31:32 login -> 12:31:56 `password_changed` -> oila `4ff0835b` o'ldi -> 12:33:04 QAYTA login."
  implication: "Sessiyani o'ldirgan narsa — parol almashtirish, navigatsiya emas."

- timestamp: 2026-08-14 (tekshiruv 7 — TO'LIQ KORRELYATSIYA)
  checked: "uvicorn access log, vaqt tamg'alari bilan (UTC, mahalliy = +5)"
  found: |
    Kassir:  07:31:33 login 200 -> 07:31:57 change-password 204 -> 07:32:20 refresh 401 -> 07:32:32 refresh 401 -> 07:33:04 QAYTA login 200
    Direktor: 07:40:07 login 200 -> 07:40:25 change-password 204 -> 07:40:53 refresh 401 (sessiya tugadi)
    Kassirning IKKINCHI sessiyasida (07:33:04 dan keyin) 4 ta refresh KETMA-KET 200 qaytargan, sessiya 12:39:49 da ANIQ logout bilan tugagan.
  implication: "HAR BIR sessiya-ichi refresh 401'i bevosita change-password 204 dan KEYIN keladi. Parol almashtirilmagan sessiyalarda refresh HAR DOIM 200. Korrelyatsiya 100%."

- timestamp: 2026-08-14 (tekshiruv 8)
  checked: "services/core-api/app/api/v1/auth.py:841-891 — change_password endpointi"
  found: "875: `refresh_revoke_user(principal.user_id)` — BARCHA oilalar, joriy sessiya ham. 890: `clear_refresh_cookie(out)` — brauzerdagi cookie o'chiriladi. YANGI sessiya (yangi oila/cookie) BERILMAYDI, javob 204 va tanasi bo'sh."
  implication: "Parol almashtirilgach brauzerda faqat xotiradagi access token qoladi (15 daq). To'liq sahifa navigatsiyasi xotirani tozalaydi -> `restoreSession()` cookie'siz refresh chaqiradi -> auth.py:682 `not refresh_token` -> 401, LOGSIZ, AUDITSIZ. Bu tekshiruv 3 va 4 dagi 'yozuv yo'q' faktini AYNAN tushuntiradi."

- timestamp: 2026-08-14 (tekshiruv 9 — TUZATISHDAN KEYINGI JONLI TAJRIBA)
  checked: "http://127.0.0.1:8001 — yangi `market_admin`, ikki mustaqil sessiya, to'liq zanjir"
  found: |
    change-password -> 204 va javobda YANGI `sbozor_rt` (before != after).
    JORIY qurilma refresh -> 200 + cookie rotatsiya qilindi.
    BOSHQA qurilmaning eski cookie'si refresh -> 401.
    Eski parol bilan login -> 401.
  implication: "Falsifikatsiya sharti bajarildi — gipoteza TASDIQLANDI. ASVS V7 kafolati ham buzilmagan."

- timestamp: 2026-08-14 (tekshiruv 10 — TESTLARNING O'ZINI SINASH)
  checked: "`auth.py` VAQTINCHA tuzatishdan oldingi holatga qaytarildi, ikkala yangi test ishga tushirildi"
  found: |
    Ikkalasi ham YIQILDI, aynan hisobotdagi simptom bilan:
    `AssertionError: {"detail":"invalid_refresh"} ... assert 401 == 200`
    Tuzatish tiklangach ikkalasi ham yashil.
  implication: "Testlar buzuq kodda yashil qolmaydi — bu haqiqiy regressiya himoyasi, bo'sh da'vo emas. Ayni paytda bu ildiz sababning yana bir mustaqil takrorlanishi."

- timestamp: 2026-08-14 (tekshiruv 11 — REGRESSIYA QAMROVI)
  checked: "auth/password to'plamlari + `npm run lint`"
  found: |
    test_password_gate.py 13/13; login+refresh+gate+unit/test_password 68/68;
    ruff check + ruff format --check + mypy — to'liq yashil (339 manba fayli).
  implication: "Qo'shni funksionallik buzilmagan; kod uslub va tip darvozalaridan o'tdi."

- timestamp: 2026-08-14 (tekshiruv 12 — FRONTEND SHARTNOMASI)
  checked: "frontend/src/components/auth/change-password-form.tsx:78-101"
  found: "204 dan keyin xotiradagi access token SAQLANADI, faqat `updatePrincipal` + klient tomon `router.replace` bajariladi; javob tanasi o'qilmaydi (`emptyResponseSchema`)."
  implication: "Javob shaklini o'zgartirish SHART EMAS — cookie'ni qayta berish minimal va yetarli tuzatish. Frontendga tegilmadi."

## Eliminated

- hypothesis: "Parallel refresh poygasi + rotatsiya reuse-detection sessiya oilasini bekor qiladi"
  evidence: "Loglarda `refresh_reuse_detected`/`refresh_on_dead_family` NOL ta (structlog esa ishlayapti); audit_log'da REFRESH_REUSE_DETECTED NOL qator; frontend'da single-flight refresh mavjud (api-client.ts:149-186) va boshqa refresh chaqiruvchi yo'q; `refresh_rotate` atomar `WHERE revoked_at IS NULL`. Barcha 401'lar change-password bilan 100% korrelyatsiyada."
  timestamp: 2026-08-14

## Resolution

root_cause: |
  `POST /auth/change-password` "barcha sessiyalarni o'ldirish" qadamini bajarardi,
  lekin "joriy qurilmani qayta tiklash" qadami YO'Q edi.

  Aniq mexanizm (auth.py, tuzatishdan oldingi holat):
    1. `refresh_revoke_user(principal.user_id)` — foydalanuvchining BARCHA refresh
       oilalarini bekor qiladi, JORIY sessiya ham shu qatorda.
    2. `clear_refresh_cookie(out)` — brauzerdagi `sbozor_rt` cookie'ni o'chiradi
       (`sbozor_rt=""; Max-Age=0`).
    3. O'rniga HECH NARSA berilmasdi — javob bo'sh tanali 204.

  Natijada brauzerda faqat XOTIRADAGI access token qolardi (15 daqiqa). Nuqson
  DARHOL ko'rinmasdi — ilova ishlayotgandek tuyulardi. Mina keyingi TO'LIQ SAHIFA
  navigatsiyasida portlardi: u xotirani tozalaydi, `(app)/layout.tsx` ning
  `restoreSession()` i cookie'siz `/auth/refresh` chaqiradi va auth.py:682
  `if not refresh_token` shoxiga tushadi -> 401 -> `/uz/login`.

  Aynan shu shox LOG HAM, AUDIT HAM yozmaydi — bu tekshiruv 3 va 4 dagi
  "hech qanday yozuv yo'q" faktini to'liq tushuntiradi va boshlang'ich
  "rotatsiya poygasi / reuse-detection" gipotezasini yiqitadi.

  Navigatsiyaning o'zi AYBDOR EMAS: u faqat oshkor qiluvchi hodisa edi.
  Sessiyani parol almashtirishning O'ZI o'ldirgan, 20-30 soniya oldin.

fix: |
  `services/core-api/app/api/v1/auth.py::change_password`:
    - `settings: SettingsDep` parametri qo'shildi.
    - `refresh_revoke_user(...)` dan KEYIN, `principal.market_id is not None`
      bo'lganda, joriy qurilma uchun `_issue_session_cookie(...)` chaqiriladi —
      YANGI oila (`family_id=None`) + yangi cookie.
    - `market_id is None` (bozor tanlamagan platforma admini) holatida eski
      `clear_refresh_cookie(out)` xulqi SAQLANADI: u rejimda refresh cookie
      umuman berilmagan (`refresh_tokens.market_id` `NOT NULL`), ya'ni
      tiklanadigan narsa yo'q.

  TARTIB QASDDAN: avval bekor qilish, keyin yangi oila. Teskarisi endigina
  berilgan tokenni ham o'ldirardi, `revoked` sanog'i esa yolg'on bo'lardi.

  ASVS V7 BUZILMAYDI: `refresh_revoke_user` JOYIDA QOLADI — boshqa hamma
  qurilma baribir o'ladi. WR-02/CR-01 teshigi ham qayta ochilmaydi: yangi
  oila faqat `current_password` tekshiruvidan O'TGAN so'rovga beriladi
  (qayta autentifikatsiya), ya'ni o'g'irlangan access token yolg'iz o'zi
  yangi sessiya ocholmaydi. Shu bilan `select-market` ni parol darvozasi
  ostiga olib kelgan mulohaza bu yerda buzilmaydi.

  Frontend O'ZGARTIRILMADI va bu ataylab: `change-password-form.tsx` xotiradagi
  access tokenni saqlab, faqat klient tomonda `router.replace` qiladi; keyingi
  to'liq navigatsiyada `restoreSession()` endi ISHLAYDIGAN cookie topadi.
  Javob shakli (204, bo'sh tana) o'zgarmagani uchun shartnoma ham buzilmadi.

verification: |
  1) JONLI FALSIFIKATSIYA TESTI (http://127.0.0.1:8001, yangi `market_admin`
     foydalanuvchi, ikki mustaqil sessiya):
       [A] change-password -> 204 + YANGI cookie berildi (before != after)
           -> JORIY qurilmada refresh -> 200 ✔ VA cookie rotatsiya qilindi ✔
       [B] NEGATIV NAZORAT: change-password'dan OLDIN olingan BOSHQA qurilma
           cookie'si -> refresh -> 401 ✔ (ASVS V7 saqlandi)
       [C] eski (vaqtinchalik) parol bilan login -> 401 ✔
     Falsifikatsiya sharti bajarildi: gipoteza TASDIQLANDI.

  2) REGRESSIYA TESTLARI QIZARISH BILAN ISBOTLANDI (eng muhim tekshiruv):
     `auth.py` VAQTINCHA tuzatishdan OLDINGI holatga qaytarildi va ikkala yangi
     test AYNAN hisobotdagi simptom bilan YIQILDI:
       `AssertionError: {"detail":"invalid_refresh"} / assert 401 == 200`
     So'ng tuzatish tiklandi va ikkalasi ham yashil bo'ldi. Ya'ni testlar
     buzuq kodda yashil qolmaydi — haqiqiy regressiya himoyasi.

  3) TO'PLAMLAR:
       - `tests/integration/test_password_gate.py` — 13/13 yashil
       - `test_auth_login.py` + `test_auth_refresh.py` + `test_password_gate.py`
         + `tests/unit/test_password.py` — 68/68 yashil
       - `tests/tenancy/test_cross_tenant.py` + `test_users_api.py`
         + `test_audit_read.py` — yashil (change-password'ga tegadigan qolgan
         barcha fayllar)
       - `npm run lint` (ruff check + ruff format --check + mypy) — TO'LIQ
         yashil: "All checks passed / 351 files already formatted /
         no issues found in 339 source files"

  4) QO'SHILGAN REGRESSIYA TESTLARI — ATAYIN JUFT (`test_password_gate.py`):
       - `test_password_change_keeps_the_current_device_signed_in`
       - `test_password_change_still_kills_the_other_devices`
     Juftlik majburiy: yolg'iz birinchisi `refresh_revoke_user()` ni butunlay
     olib tashlagan taqdirda ham yashil qolardi, ya'ni ASVS V7 kafolatini
     jimgina yo'q qilgan "tuzatish" ni o'tkazib yuborardi.

files_changed:
  - services/core-api/app/api/v1/auth.py  # change_password: revoke'dan keyin joriy qurilmaga yangi oila + cookie
  - tests/integration/test_password_gate.py  # ikkita yangi regressiya testi (juft)
