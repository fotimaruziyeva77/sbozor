---
phase: 08-hisobotlar-mustahkamlash-va-ishga-tushirish
plan: 19
subsystem: ops
tags: [runbook, go-live, deploy, rollback, cutover, restic, restore-drill, human-uat, static-gate]

# Dependency graph
requires:
  - phase: 08-hisobotlar-mustahkamlash-va-ishga-tushirish
    provides: "08-05 ning `ops/backup/README.md` (kalitlar, parol bandi, versiya tartibi) va `backup` konteyneri"
  - phase: 08-hisobotlar-mustahkamlash-va-ishga-tushirish
    provides: "08-08 ning ikki o'lchangan fakti: `--no-privileges` GRANT'larni yo'qotadi (163 -> 0); `pg_dump` superuser/BYPASSRLS talab qiladi"
  - phase: 07-nomuvofiqlik-bildirishnoma-va-botlar
    provides: "`deferred-items.md` №5 ning OCHIQ qismi — `npm run up` qo'lda tasdiqlanmagan"
provides:
  - "`ops/docs/go-live.md` — deploy tartibi, konteyner qayta yaratish qoidasi, WireGuard, birinchi zaxira va TIKLASH TARTIBI (GRANT qadami bilan), offsite data-rezidentligi, versiya tartibi, cutover, rollback"
  - "`tests/unit/test_runbook_shape.py` — SC#4(1) statik darvozasi: buyruq + kutilgan natija juftligi, natijasiz buyruq taqig'i"
  - "`08-HUMAN-UAT.md` — olti bandlik jamlangan go-live oldi ro'yxati; SC#3 va SC#4 ning IMZO joyi"
  - "Mexanika: `**Kutilgan natija:**` — runbookda ham, darvozada ham AYNAN shu satr"
affects: [08-20-faza-mezoni, go-live, ops-deploy]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Hujjat SHAKLI ustidagi statik darvoza: fenced blok -> keyingi bo'sh bo'lmagan qator markerni olib yuradi"
    - "Bo'lim QAMROVI (to'plam tengligi EMAS): bo'lim qo'shilishi darvozani qizartirmaydi, yo'qolishi qizartiradi"
    - "Apostrofli o'zbek so'zlari uchun `\\b` o'rniga `(?<![\\w'])…(?![\\w'])` — `ko'ring` tutiladi, `ko'rinadi` tutilmaydi"

key-files:
  created:
    - ops/docs/go-live.md
    - tests/unit/test_runbook_shape.py
    - .planning/phases/08-hisobotlar-mustahkamlash-va-ishga-tushirish/08-HUMAN-UAT.md
  modified: []

key-decisions:
  - "08-19: tanlangan mexanika — har fenced blokdan KEYINGI birinchi bo'sh bo'lmagan qator `**Kutilgan natija:**` bilan boshlanadi; qoida runbookning kirish qismida LITERAL yozilgan, ya'ni hujjat va darvoza bir narsani aytadi"
  - "08-19: `ops/docs/monitoring.md` bu darvoza ostiga KIRITILMADI — u konvensiyadan OLDIN yozilgan boshqa janr va uni qayta yozish 08-19 ning qamrovidan tashqarida (SCOPE BOUNDARY); sabab test modulining docstringida"
  - "08-19: (d) taqiqlangan iboralar `\\b` bilan EMAS, `(?<![\\w'])…(?![\\w'])` bilan izlanadi — apostrof `\\w` emas va `\\b` so'z chegarasini `ko'ring` ning O'RTASIDA topardi"
  - "08-19: (b) QAMROV o'lchovi, to'plam TENGLIGI emas — teng to'plam har yangi bo'limda testni tahrirlashga majburlab, «testni moslashtirish» odatini tug'dirardi"
  - "08-19: tiklash tartibiga GRANT qadami (`npm run migrate`) KIRITILDI (deferred-items №5, egasi ATAYIN 08-19 edi) va uning O'LCHANMAGANI runbookda ham, UAT bandida ham LITERAL"
  - "08-19: `08-HUMAN-UAT.md` ning 6-bandi oldingi fazalarni HAVOLA bilan sanaydi — matn ko'chirilsa ikki nusxa bir kun ajralib ketardi (biri «yopildi», ikkinchisi mangu `pending`)"
  - "08-19: `01-HUMAN-UAT.md` va `02-HUMAN-UAT.md` ham 6-bandga kiritildi — reja beshtasini nomlagan edi, lekin ro'yxatning MAQSADI «hech biri jimgina tushib qolmasin»"

patterns-established:
  - "Hujjatning SHAKLI mexanik qulflanadi: matn «tartibli ko'rinishi» odam ko'zida nuqsonni yashiradi, blok/marker juftligi esa yashira olmaydi"
  - "Quyi chegara `autouse` fixture'da (08-05/08-08 naqshining takrori) — fayl yo'qolganda «topilmadi» shaklidagi UCH da'vo bo'sh matn ustida jimgina yashil bo'lardi"
  - "«0 marta» shaklidagi da'vo IKKI nazorat namunasi bilan o'lchanadi: detektor sintetik namunada TOPADI va to'g'ri so'zni TUTMAYDI"

requirements-completed: []

# Metrics
duration: 50min
completed: 2026-08-16
---

# Phase 8 Plan 19: Go-live runbook, uning shakl darvozasi va jamlangan UAT ro'yxati — Summary

**`ops/docs/go-live.md` endi o'qib BAJARILADIGAN hujjat — 28 buyruq blokining har biri `**Kutilgan natija:**` bilan juft va bu juftlik `tests/unit/test_runbook_shape.py` da mexanik qulflangan; `08-HUMAN-UAT.md` esa loyihaning butun umri davomida to'plangan CI'da o'lchanmaydigan bandlarni bitta joyga, egasi va tetigi bilan yig'di — ya'ni SC#3 va SC#4 ning imzo joyi endi mavjud.**

## HOLAT: CHECKPOINT YOPILDI (Task 3 — approved)

Reja `autonomous: false` va uning 3-vazifasi `checkpoint:human-verify`
(`gate="blocking"`). Ijrochi rejaning `<action>` bandi bo'yicha
`08-HUMAN-UAT.md` ni **yozdi va commit qildi**, so'ng ishni to'xtatib
tasdiq so'radi. **Orkestrator artefaktni tekshirib `approved` berdi:**

- oltala bandda **Egasi** va **Tetigi** ustunlari to'ldirilgan —
  tasdiqlandi;
- 6-band matn **ko'chirmasdan** havola qiladi va 01–07 fazalarning
  **yettala** `*-HUMAN-UAT.md` fayli sanalgan — tasdiqlandi;
- offsite S3 savoliga javob berildi va u ⛔ **o'lchov bilan**
  (quyidagi «Foydalanuvchining javobi» bo'limi) — ijrochi uni faraz
  qilmadi.

⚠ `08-HUMAN-UAT.md` ning oltala bandi `result: [pending]` holatida
**qoladi** va bu **to'g'ri**: bandlar go-live oldida, imzo bilan
yopiladi — ijro paytida emas.

## Performance

- **Duration:** ~50 min (Task 1 + Task 2 + Task 3 ning artefakti)
- **Tasks:** 3/3 (2 tasi avtonom; 3-vazifa — artefakt yozildi va checkpoint **approved**)
- **Files:** 3 yangi, 0 tahrirlangan

## Accomplishments

- **Runbook o'qib BAJARILADIGAN shaklda yozildi.** 519 qator, 28 buyruq
  bloki, har biri kutilgan natijasi bilan. Natijasiz buyruq bandi
  («…ni bajaring» deb aytib, nima chiqishi kerakligini aytmaydigan
  qator) endi faylga **kira olmaydi** — darvoza uni qaytaradi.
- **Ikki meros band runbookda YOPILDI va ikkalasi ham o'lchangan fakt
  ustida turadi:** (1) tiklash tartibiga **GRANT qadami** qo'shildi
  (`deferred-items.md` №5, egasi ATAYIN «08-19» deb yozilgan edi);
  (2) `BACKUP_DATABASE_URL` ning superuser/`BYPASSRLS` talabi
  tushuntirildi (08-08 ning fakti, aks holda birinchi tunggi zaxira
  `pg_dump` bosqichida yiqilardi va sababi hech qayerda yozilmagan
  bo'lardi).
- **`RESTIC_PASSWORD` ning off-server bandi endi IKKI qatlamda:**
  runbookda imzolanadigan uch bandlik jadval, `08-HUMAN-UAT.md` da
  imzo qatori, va statik darvozada uning **mavjudligi** (T-08-85).
- **Uch tilli tekshiruv uchun yangi mexanik darvoza YOZILMADI** (D-23
  ning talabi): `i18n:check`, `glossary.test.mjs` va
  `error-codes.test.mjs` yetarli deb topildi va bu `08-HUMAN-UAT.md`
  ning 4-bandida literal yozilgan.
- **Regressiya yo'q:** `pytest tests/unit` to'liq to'plami EXIT **0**
  (1300+ o'lchov), `ruff check` / `ruff format --check` / `mypy` yangi
  fayl ustida toza.

## Task Commits

1. **Task 1: `ops/docs/go-live.md`** — `349afd7` (docs)
2. **Task 2: `tests/unit/test_runbook_shape.py`** — `c1b6abc` (test)
3. **Task 3 ning ARTEFAKTI: `08-HUMAN-UAT.md`** — `47d0824` (docs); checkpoint **approved**, offsite S3 holati keyingi commitda literal yozildi

## Tanlangan mexanika (reja uni SUMMARY da nomlashni talab qiladi)

**`**Kutilgan natija:**`** — har fenced kod blokining yopilgan
fence'idan keyingi **birinchi bo'sh bo'lmagan qator** aynan shu satr
bilan boshlanadi.

Uch sabab:

1. **Bir ma'noli:** «blokdan keyingi qator» — parser uchun ham, odam
   uchun ham bir xil joy. Muqobil («blok ustida yoki ostida») ikki
   holatni ham qabul qilib, mexanikani noaniq qilardi.
2. **Hujjat va darvoza BIR narsani aytadi:** qoida runbookning kirish
   qismida (`14–16-qatorlar`) LITERAL yozilgan, ya'ni keyingi
   tahrirchi mexanikani **faylning o'zidan** o'qiydi va testni
   ochishi shart emas.
3. **Namuna manbasi mavjud:** `ops/scripts/verify-tunnel.sh` ning
   «Chiqish kodi: 0 — …; 1 — …» sarlavhasi — buyruqning yonida uning
   natijasi turadi.

## Ikki sabotaj — o'lchandi va qaytarildi

| # | Sabotaj | Kutilgan | O'lchangan natija |
|---|---------|----------|-------------------|
| 1 | §1.2 dagi `**Kutilgan natija:**` qatori O'CHIRILDI | (c) qizaradi | ✅ **QIZARDI**, faqat (c): «KUTILGAN NATIJASIZ buyruq bloki bor (qator -> blokdan keyingi matn): [(52, "⚠ `frontend` va `nginx` **profil ortida** …")]» — ⛔ qator raqami va o'rniga tushgan matn bilan |
| 2 | §4.3 (`RESTIC_PASSWORD` ning off-server bandi) BUTUNLAY o'chirildi | (e) qizaradi | ✅ **QIZARDI**, faqat (e): «saqlash bandi TO'LIQ EMAS — yetishmayotgan belgi(lar): ['serverdan tashqarida', 'ikki joyda', 'ikki odam']» |

⛔ **2-sabotajning eng muhim tafsiloti:** `RESTIC_PASSWORD` kaliti
faylda **QOLDI** (u §4.1 ning kalitlar ro'yxatida ham bor) va darvoza
baribir qizardi. Ya'ni (e) kalitning **eslatilishini** emas,
**SAQLASH BANDINING** mavjudligini o'lchaydi — 08-05 va 08-08 ning
«sabotaj sistemaga yetib borsa ham, tekshirilayotgan PREDIKATGA yetib
bormasligi mumkin» darsi shu shaklda oldindan yopildi.

Ikkala sabotaj ham `git checkout -- ops/docs/go-live.md` bilan
qaytarildi (Task 1 sabotajlardan OLDIN commit qilingani uchun) va
qaytarilgandan keyin to'plam qayta **yashil**.

## Nazorat namunalari (predikatlarning o'zi o'lchandi)

«Topilmadi» shaklidagi da'vo buzuq predikat bilan **mangu yashil**
bo'ladi, shuning uchun ikkala skaner ham avval sintetik namunada
**topadi**:

| Nazorat | Nima isbotlaydi |
|---------|-----------------|
| `_unpaired_command_blocks("```bash\\nls\\n```\\n\\nOddiy matn…")` -> **1 topilma** | fence parseri ishlayapti; usiz «juftlanmagan blok yo'q» da'vosi bo'sh-rost bo'lardi |
| `_resultless_hits("Jurnalni tekshiring.")` -> **topildi** | regex ishlayapti |
| `_resultless_hits("… tekshiriladi va ko'rinadi.")` -> **bo'sh** | ⛔ regex so'z ICHIDAN moslashmaydi; usiz darvoza to'g'ri so'zlarni qizartirib, muallifni matnni buzishga majburlardi |

## Verification natijalari

| O'lchov | Natija |
|---------|--------|
| `pytest tests/unit/test_runbook_shape.py -q` | ✅ **5 passed** |
| `pytest tests/unit -q` (to'liq to'plam) | ✅ EXIT **0**, regressiya yo'q |
| `ruff check` + `ruff format --check` + `mypy` (yangi fayl) | ✅ `All checks passed` / `1 file already formatted` / `no issues found` |
| `grep -c "def test_" tests/unit/test_runbook_shape.py` | **5** (rejaning talabi) |
| `MIN_*` konstantalar | **3**: `MIN_RUNBOOK_LINES`, `MIN_COMMAND_BLOCKS`, `MIN_FORBIDDEN_PHRASES` |
| `ops/docs/go-live.md` uzunligi | **519** qator (chegara 200) |
| Buyruq bloklari | **28** (chegara 12), juftlanmagani **0** |
| `grep -c "ops/backup/README.md" ops/docs/go-live.md` | **5** — takrorlash o'rniga havola |
| `grep -c "HALOL CHEGARA" ops/docs/go-live.md` | **9** (har bo'limda bittadan) |
| `grep -c '^### ' 08-HUMAN-UAT.md` | **7** (olti band + kirish jadvali) — runbook §9 ning chegarasi ≥6 |
| Havolalar | 01..07 fazalarning ETTALA `*-HUMAN-UAT.md` fayli diskda mavjud |

⚠ **O'lchov muhiti:** worktree izolyatsiyasi `deferred-items.md` №3
ning retsepti bilan — `docker compose -p sbozor-w0819 --profile test
run --rm --no-deps tests …`, image mavjudidan teglandi
(`sbozor-w0819-tests`), oxirida `down -v` va teg **o'chirildi**.
Asosiy stekning konteynerlariga tegilmadi.

## Deviations from Plan

### Ongli shakl farqlari (xato emas, qaror)

**1. Quyi chegara ALOHIDA TEST emas, `autouse` FIXTURE (08-05/08-08 naqshining takrori).**
Reja AYNAN 5 ta `def test_` talab qiladi va AYNI PAYTDA
`test_compose_sim_env.py` ning «quyi chegara majburiy» qoidasini
talab qiladi. Faylning mavjudligi alohida test bo'lganda sanoq 6 ga
chiqardi — va u yolg'iz qizarib, (b)/(c)/(d) bo'sh matn ustida
**jimgina yashil** bo'lib turardi («taqiqlangan ibora 0 marta
uchradi» bo'sh faylda ham ROST). `autouse` shaklida chegara BESHALA
o'lchovdan oldin bajariladi va sanoq 5 bo'lib qoladi.

**2. `ops/docs/monitoring.md` skanerga KIRITILMADI.**
Reja uni ixtiyoriy qoldirgan («skaner uni ham o'lchashi mumkin»).
Kiritilmadi va sabab o'lchangan: `monitoring.md` bu konvensiyadan
OLDIN yozilgan, boshqa janr (sozlash yo'riqnomasi) va uning matnida
taqiqlangan iboralar bor — ya'ni kiritish 08-19 ning qamrovidan
tashqaridagi faylni qayta yozishni talab qilardi (SCOPE BOUNDARY).
Band test modulining docstringida OCHIQ nomlangan.

**3. `08-HUMAN-UAT.md` ning 6-bandiga IKKI QO'SHIMCHA fayl kirdi.**
Reja `03/04/05/06/07` ni sanaydi; ro'yxatga `01-HUMAN-UAT.md` va
`02-HUMAN-UAT.md` ham **alohida eslatma** bilan qo'shildi (ular
go-live'ni bloklamaydi). Sabab bandning O'Z maqsadi: «hech biri
jimgina tushib qolmasin». Ikkitasini qoldirish ro'yxatni
to'liqmasligini yashirardi.

**4. Runbookning bo'limlari rejadagi ro'yxatdan KO'PROQ.**
Reja sakkiz mavzuni sanaydi; ular to'qqiz `## ` bo'limga yoyildi
(offsite bucket va `pg_dump` versiyasi alohida bo'lim bo'ldi). Sabab
mexanik: (b) o'lchovi `## ` sarlavhalarida marker izlaydi, ya'ni
mavzu bo'lim darajasida ko'rinsa u YO'QOLGANDA darvoza qizaradi;
kichik sarlavha ichida qolganda esa yo'qolishi sezilmasdan o'tib
ketardi.

**Total deviations:** 0 auto-fixed (Rule 1/2/3 hech biri ishlamadi —
reja hujjat va test yozadi, mahsulot kodiga tegmaydi) + 4 ongli shakl
farqi.

## Foydalanuvchining javobi (Task 3 ning qabul mezoni)

Reja aynan bitta savolning javobini SUMMARY da LITERAL talab qiladi:

> «Offsite S3 hisobi ochilganmi, byudjet bormi?»

**Javob (2026-08-16):** ⛔ **OFFSITE S3 HISOBI HOZIRCHA OCHILMAGAN VA
BYUDJET QARORI QABUL QILINMAGAN.** Bu rejaning O'ZI «TO'G'RI javob»
deb atagan variant (self-service qoidasi 2) va u bandni **ochiq**
qoldiradi.

⛔ **Javob TAXMIN emas — o'lchangan holat.** Uch dalil:

| # | O'lchov | Natija |
|---|---------|--------|
| 1 | `.env` da `RESTIC*` kalitlari (`grep -c`) | **0** — bironta ham yo'q |
| 2 | `.env.example:240` | `RESTIC_REPOSITORY=` — **bo'sh** |
| 3 | `compose.yaml:846` | `RESTIC_REPOSITORY: ${RESTIC_REPOSITORY}` — o'zgaruvchi **kutilyapti**, qiymat berilmagan |

⚠ 1-dalil ASOSIY checkout'da o'lchandi (`.env` gitignore'da va bu
worktree'da umuman yo'q). Mustaqil ikkinchi iz shu ijroning O'ZIDA
qoldi: har `docker compose` chaqiruvi
`The "RESTIC_REPOSITORY" variable is not set` va
`The "RESTIC_PASSWORD" variable is not set` ogohlantirishlarini berdi.

**Oqibati va uning EGASI:**

- `backup` konteyneri `backup_unconfigured` yozadi, zaxirani
  **boshlamaydi** va yurak urishini **yozmaydi** -> 26 soatdan keyin
  `backup_stale` (**CRITICAL**, `never_suppressed`) chiqadi.
- ⛔ **Bu alertni o'chirib qo'yish TAQIQLANADI:** u bandning
  ochiqligini ko'rsatuvchi **YAGONA** signal; o'chirilsa FOUND-07
  qog'ozda bajarilgan, amalda bajarilmagan holatga qaytardi va buni
  faqat falokat kuni bilib olinardi.
- **Qarorning egasi:** **buyurtmachi** (byudjet) va **Ops**
  (provayder tanlovi — D-14 bo'yicha VPS bilan BOSHQA failure domain:
  Backblaze B2 yoki ikkinchi Contabo regioni).
- Band `08-HUMAN-UAT.md` ning 3-bandida **ochiq** (`result: [pending]`)
  qoldi va holat o'sha yerda ham LITERAL yozildi — uni yopish
  byudjet qaroriga bog'liq, ijro qaroriga emas.

⚠ **Checkpoint natijasi:** orkestrator artefaktni tekshirib
**approved** berdi (oltala bandda Egasi/Tetigi to'ldirilgan; 6-band
matn ko'chirmasdan havola qiladi va 01–07 fazalarning yettala fayli
sanalgan).

## Issues Encountered

- **`pytest -q` bu repoda yakuniy «N passed» satrini chiqarmaydi** —
  yagona ishonchli signal chiqish kodi. To'liq unit to'plami uchun u
  alohida o'lchandi (`EXIT=0`), sanoq esa progress belgilaridan
  hosila.
- **Worktree'da `.env` yo'q**, ya'ni `docker compose` har chaqiruvda
  ~20 «variable is not set» ogohlantirishi beradi. Testlar unga
  bog'liq emas (`tests` bloki `:-` standartlari bilan ishlaydi va
  `--no-deps` ostida `storage` ko'tarilmaydi), lekin chiqishni
  filtrlash kerak bo'ldi.

## Known Stubs

Yo'q. `ops/docs/go-live.md` dagi har bir buyruq — haqiqiy, shu repoda
mavjud yo'l (`npm run migrate`, `npm run up`,
`ops/scripts/verify-tunnel.sh`, `ops/backup/run-backup.sh`); qattiq
yozilgan soxta natija yoki «coming soon» yo'q. `08-HUMAN-UAT.md` ning
`result: [pending]` qatorlari **stub emas** — ular imzolanadigan
bandning to'g'ri boshlang'ich holati.

⛔ CI'da o'lchanmaydigan da'volar OCHIQ nomlangan va har birining egasi
bor: (1) «offsite repodan tiklandi» — 1-band, egasi Ops; (2) tiklash
tartibining GRANT qadami — o'sha bandda, ⚠ **tartibning O'ZI
o'lchanmagan** va bu runbookda ham literal; (3) uch tilli idrok —
4-band, egasi mahsulot egasi.

## Threat Flags

Rejadagi `<threat_model>` dan TASHQARIDA yangi hujum yuzasi topilmadi:
bu reja mahsulot kodiga, migratsiyalarga va tarmoq yuzasiga **umuman
tegmaydi** — u ikki hujjat va bitta statik skaner qo'shadi. Reyestrning
to'rt bandidan uchtasi mexanik qatlam oldi (T-08-85 (e) o'lchovi bilan,
T-08-88 (c)/(d) bilan, T-08-86 runbook §5 bilan); T-08-87 esa ATAYIN
mexaniklashtirilmadi — «tiklash mashqi o'tkazilgan» da'vosining yagona
manbai inson imzosi (`08-HUMAN-UAT.md` 1-band).

## Next Phase Readiness

- **08-20 (faza mezoni testi) uchun tayyor:** `ops/docs/go-live.md`
  mavjud va uning shakli `tests/unit/test_runbook_shape.py` bilan
  o'lchanadi, ya'ni mezon testi runbookning MAVJUDLIGINI ham,
  SHAKLINI ham nomma-nom chaqira oladi. `08-HUMAN-UAT.md` da
  `^### ` sanog'i **7** (chegara ≥6).
- **Go-live uchun ochiq va EGASI BOR:** `08-HUMAN-UAT.md` ning oltala
  bandi. Ulardan uchtasi FOUND-07 ga tegishli (1, 2, 3) va bittasi
  SC#4 ni yopadi (4).
- **⚠ Orkestrator uchun:** 3-vazifaning checkpointi **yopildi**
  (`approved`). Ochiq qolgan yagona band — **offsite S3 hisobi**
  (3-band) va uning egasi buyurtmachi/Ops; u ijro oqimini
  **bloklamaydi**, lekin `backup_stale` (CRITICAL) alerti go-live'dan
  keyin ham chiqib turadi va uni o'chirish **taqiqlanadi**.

## Self-Check: PASSED

Yaratilgani da'vo qilingan UCHALA fayl ham diskda mavjud
(`ops/docs/go-live.md`, `tests/unit/test_runbook_shape.py`,
`08-HUMAN-UAT.md`) va UCHALA commit ham `git log` da:
`349afd7` -> `c1b6abc` -> `47d0824`. Sabotajlar `git checkout --`
bilan qaytarilgani `git status` bilan tasdiqlandi (ishchi daraxt
toza), vaqtinchalik Docker artefaktlari (`sbozor-w0819` loyihasi,
tarmoq, hajm va image tegi) o'chirildi. Yo'qolgan artefakt yo'q.

---
*Phase: 08-hisobotlar-mustahkamlash-va-ishga-tushirish*
*Completed: 2026-08-16 (Task 3 checkpointi `approved`; 3-band — offsite S3 — ATAYIN ochiq)*
