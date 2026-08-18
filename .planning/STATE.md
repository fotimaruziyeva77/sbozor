---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: executing
stopped_at: Phase 10 UI-SPEC approved
last_updated: "2026-08-17T19:22:29.456Z"
last_activity: 2026-08-17
progress:
  total_phases: 11
  completed_phases: 10
  total_plans: 154
  completed_plans: 154
  percent: 91
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-07-28)

**Core value:** Bozor ma'muriyati har bir band rastadan patta to'liq yig'ilayotganini raqamlar va rasm-dalil bilan ko'radi — "band, lekin to'lovsiz" rastalar kunlik hisobotda avtomatik fosh bo'ladi.
**Current focus:** Phase 10 — landing-sbozor-uz

## Current Position

Phase: 10
Plan: Not started
Total Plans in Phase: 8
Status: Ready to execute
Last activity: 2026-08-17

Progress: [██████████] 100% (7/7 reja — 09-01…09-07)

✅ **9-FAZANING IJROSI TUGADI (7/7 reja).** `09-07` faza darvozasini yopdi:
beshala ROADMAP mezoni `frontend/scripts/phase9-criteria.test.mjs` da
**BITTA buyruqda** o'lchanadi (8 test: 5 mezon + META ROADMAP-parse +
soxtalashtirish darvozasi + reyestr nazorati; uch sabotaj ikki natija
bilan). To'liq `npm run gate` bu fazada BIRINCHI marta backend yarmi
bilan ikki marta exit 0.

⛔ **HUMAN-UAT BESHALA BANDI RAQAMSIZ OCHIQ (orkestrator chegarasi).**
Mexanik qatlam tasdiqlangan, LEKIN birortasiga son yozilmagan — o'lchovlar
real qurilma/inson idrokini talab qiladi: №1 60fps, №2 Lighthouse/CLS
(ikkalasi — birinchi deploy yoki verify bosqichi), №3 uch tema idroki,
№4 20 ketma-ket to'lov (ikkalasi — pilot haftasi), №5 OS reduced-motion.
`nyquist_compliant: true` bunga ZID EMAS — bayroq «har xulq darvozaga
yoki egali-tetikli bandga biriktirilgan» hisob-kitobi va signoff exit 0.

✅ **`gate` BYUDJETI QAYTA O'LCHANDI VA O'ZGARMADI — LEKIN ZAXIRA KRITIK
TOR.** Tinch xostda IKKI yaroqli o'lchov: **2259 / 2102 s** (chegara
2300) — zaxira **41 s (1,8 %)**; `gate:fast` **189 / 171 s** (chegara
200) — zaxira 11 s. Egasi: 10-faza rejalashtiruvchisi (deferred №2).
⚠ HALOLLIK: uch emas, IKKI o'lchov; yana IKKI YAROQSIZ urinish bo'ldi
(jurnal `package.json //gate-budget` da): dushanba-ko'rlik va flake №12.

⛔ **DUSHANBA-KO'RLIK SINFI OCHILDI (birinchi dushanba gate yugurishi).**
Seed A bozori dushanba yopiq (`A_OPEN_WEEKDAYS=2..7`); ikki billing testi
«bugun ochiq» prekonditsiyasini o'rnatmagan va deterministik qizardi —
`11a4f3a` tuzatdi (arrange'da `open_weekdays=1..7`, mahsulotga nol
ta'sir). Sinf sifatida ochiq: 09-faza `deferred-items.md` №3.

⚠ **Verify muhiti:** frontend `:8081` da JORIY kod bilan qayta qurilgan
(prod build); core-api vaqtincha `127.0.0.1:8010` (xost `:8000` ni
`parnikkpi-backend-1` band qilgan, `.env` tegilmagan); `bot-service`
restart halqasi — o'lchovdan oldingi holat, tiklangan.

---

*Quyidagi 8-faza bloklari 08-20 yakunidan MEROS — ochiq bandlari
(FOUND-07, backup_stale, flake №12) hamon kuchda:*

✅ **8-FAZANING IJROSI TUGADI (20/20 reja).** `08-20` faza darvozasini
yopdi: beshala ROADMAP mezoni `tests/integration/test_phase8_criteria.py`
da **BITTA buyruqda** o'lchanadi (9 test: 5 mezon + meta-test +
soxtalashtirish darvozasi + reyestr nazorati + seed nazorati).

⚠ **ROADMAP dagi FAZA belgisi HAMON `- [ ]`** va bu ataylab: fazani
yopish qarori **qayta tekshiruvniki** (`/gsd-verify-work`), ijrochi emas.
4-, 5-, 6- va 7-fazalarda aynan shunday saqlangan; izoh ROADMAP ning
Phase 8 bo'limida LITERAL yozilgan.

⛔ **IKKI YANGI SOXTALASHTIRISH TAQIG'I MEXANIK REYESTRDA.** Bu
fazaning eng arzon ikki yolg'oni nomma-nom yopildi: (1) zaxira zanjiri
yugurmasdan turib «ishladi» degan qatorni QO'LDA yozish -- yurak urishi
FAQAT `ops/backup/heartbeat.sql` dan kelishi mumkin (`DELETE` taqiqdan
CHIQARILGAN: u faktni yozmaydi, u o'lchov boshlanadigan bo'sh holatni
quradi); (2) `.xlsx` javobini faqat `status_code` bilan tasdiqlash --
hujjat yo'liga tegib javob KODI haqida da'vo qilgan HAR test
`read_rows` ni ham chaqirishi SHART. Ikkalasi ham `ast` daraxtidan.

⛔ **FOUND-07 `Blocked` -- VA BU FAZANING ENG MUHIM HALOLLIGI.**
Mexanizm UCH qatlamda yashil (zanjirning statik shakli, yurak urishi
halqasi, dump -> TOZA server -> `pg_restore`), LEKIN talab matnining
IKKALA jumlasi ham yarim qoldi: `.env` da `RESTIC_REPOSITORY`/
`RESTIC_PASSWORD` YO'Q, ya'ni zanjir bugungacha **HECH QACHON
YUGURMAGAN**, va toza serverda tiklash mashqi CI'da bajarilmaydi.
Egasi **Ops**, tetigi **VPS deploy'i**, bandlari `08-HUMAN-UAT.md` #1
va #2. Mexanika qatlamining yashilligi bilan haqiqat qatlamining
yo'qligini yopish TAQIQLANADI (3- va 5-fazaning darsi).
RECON-04 va RECON-05 esa dalil bilan `Done`.
Sanoq: Done 41 · Pending 5 · Blocked 3.

⛔ **GO-LIVE'DAN KEYIN HAM CHIQIB TURADIGAN ALERT VA UNI O'CHIRISH
TAQIQ.** Offsite hisob ochilmaguncha `backup_stale` (CRITICAL,
`never_suppressed`) 26 soatda bir chiqadi. U aynan o'z ishini
bajarayapti: zaxira olinmayotganini AYTAYAPTI.

✅ **`gate` BYUDJETI O'LCHANDI VA O'ZGARMADI.** Tinch xostda (6 ta
`parnikkpi-*` + qayta-qayta yiqilayotgan `sbozor-bot-service-1`
to'xtatilib, o'lchovdan keyin TIKLANDI): `gate` **1909 / 1842 s**
(tarqoqlik 3,5 %), chegara **2300 s** -- zaxira 391 s (17 %);
`gate:fast` **155 / 152 s**, chegara **200 s**.
⚠ **HALOLLIK: uch emas, IKKI o'lchov olindi** -- ijro paytida tezlik
ustuvor deb belgilandi va uchinchisi BOSHLANMADI. «Uch marta o'lchandi»
da'vosi BERILMAYDI; darvoza byudjet sababli yolg'on qizil bersa,
birinchi shubha shu yerga tushadi.
WARN `C:` diski **84 % to'la (28 GB bo'sh)** -- 5-fazadagi 91 % dan
yaxshiroq, `docker system prune` kerak bo'lmadi.

⚠ **SABOTAJ O'LCHOVINING YANGI DARSI (`08-20`).** Beshala sabotaj
aynan o'z mezonini qizartirdi, LEKIN S-5 ning BIRINCHI shakli
(`:ai_mismatch` -> `:match`) modulni YIG'ILISH xatosi bilan yiqitdi
(ishlatilmagan `bindparam`) -- ya'ni u mezonni emas, yig'ilishni
o'lchardi. **Sabotaj modulni IMPORT QILINADIGAN holda qoldirishi
shart**, aks holda «qo'shnilari yashil qoladimi?» degan yarim
o'lchanmay qoladi.

⚠ **MEROS FLAKE NOMLANDI VA O'LCHANDI (`deferred-items.md` №12).**
`test_phase5_criteria.py::test_sc4_*` **1/70 = 1,4 %** ehtimollik bilan
yiqiladi: market A ning doirasi 8 hodisadan iborat (seed 2 + test 6),
ulardan 4 tasi `uncertain`, `audit_draw` esa 4 tasini tasodifiy
tanlaydi. Yakka holda 20/20 yashil. SCOPE BOUNDARY sababli
TUZATILMADI -- u boshqa fazaning mezon fayli.

⚠ **`npm run gate` ning frontend yarmi bog'liqliksiz umuman
yugurmaydi** (`deferred-items.md` №13): `frontend/node_modules` BO'SH
edi va nosozlik faqat 29-daqiqada ko'rindi. `npm ci` (qulflangan
lockfile) bilan tiklandi; yo'nalish -- zanjir boshiga arzon
mavjudlik darvozasi.

⚠ **OCHIQ BANDLAR (bloklamaydi, LEKIN nomlangan):**
`08-HUMAN-UAT.md` -- besh band, har birida ega va tetik; uchtasi
FOUND-07 ni bloklaydi. `deferred-items.md` -- 14 band, shundan 7 tasi
ochiq; ular ichida MAHSULOT SAVOLI ham bor (#9: direktor solishtiruv
ekranida farqni ISM bilan ko'rishi kerakmi? -- ijrochi hal qilmaydi).

**Muddat:** 12 hafta, 2026-07-28 → ~2026-10-18 (Karmanada jonli). Zaxira yo'q.

## Performance Metrics

**Velocity:**

- Total plans completed: 123 (o'lchov yozilgani: 1 — quyidagi jadval faqat metrikasi qayd etilgan rejalarni sanaydi)
- Average duration: 95 min (n=1)
- Total execution time: 1.6 hours (qayd etilgan qismi)

**By Phase:**

| Phase | Plan | Duration | Tasks | Files |
|-------|------|----------|-------|-------|
| 02 | 21 | 95 min | 3 | 16 |

**Recent Trend:**

- Last 5 plans: 02-21 (95 min) — undan oldingilarning metrikasi qayd etilmagan
- Trend: —

*Updated after each plan completion*
| Phase 02 P22 | 60 | 2 tasks | 2 files |
| Phase 02 P24 | 195min | 3 tasks | 29 files |
| Phase 02 P23 | 115min | 3 tasks | 8 files |
| Phase 03 P01 | 65min | 3 tasks | 12 files |
| Phase 03 P04 | 110min | 3 tasks | 12 files |
| Phase 03 P05 | 115min | 3 tasks | 11 files |
| Phase 03 P06 | 195min | 3 tasks | 16 files |
| Phase 03 P07 | 205min | 3 tasks | 21 files |
| Phase 03 P08 | 95 | 3 tasks | 29 files |
| Phase 03 P09 | 105min | 3 tasks | 15 files |
| Phase 03 P10 | 70min | 3 tasks | 18 files |
| Phase 03 P11 | 150min | 3 tasks | 8 files |
| Phase 3 P14 | 95min | 3 tasks | 10 files |
| Phase 04 P07 | 125min | 3 tasks | 17 files |
| Phase 04 P10 | 140 | 3 tasks | 16 files |
| Phase 04 P11 | 1h 45m | 3 tasks | 17 files |
| Phase 04 P13 | 125min | 3 tasks | 6 files |
| Phase 05 P05 | 185min | 3 tasks | 15 files |
| Phase 05 P10 | 111 | 3 tasks | 9 files |
| Phase 05 P12 | 175min | 3 tasks | 16 files |
| Phase 05 P13 | 165min | 3 tasks | 20 files |
| Phase 05 P14 | 150 | 3 tasks | 17 files |
| Phase 05 P15 | 235min | 3 tasks | 12 files |
| Phase 08 P20 | 385 | 3 tasks | 6 files |
| Phase 09 P07 | 180 min | 3 tasks | 8 files |
| Phase 10 P08 | 3h43m | 3 tasks | 7 files |

## Accumulated Context

### Roadmap Evolution

- Phase 9 added (2026-08-16): UI-polish — motion qatlami (sketch 001/002 g'oliblari asosida, foydalanuvchi tasdiqlagan)
- Phase 10 added (2026-08-16): Landing — sbozor.uz (sketch 003-B asosida, go-live'dan oldin shart)

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Roadmap]: Bog'liqlik zanjiri bo'yicha 8 build fazasi + parallel dala treki (Phase 0) — uch tadqiqot yo'nalishi bir xil tartibga keldi
- [Roadmap]: Dala treki (baza o'lchovi + NVR kirish) ketma-ketlikdan chiqarildi — ikkalasi ham keyinroq bajarilmaydi
- [Roadmap]: Phase 5 (poligon muharriri + detektor) atayin bir joyga yig'ildi — kesish kerak bo'lsa moliyaviy yadroga tegmasdan qisqartiriladi
- [Roadmap]: MARKET-06 plan-xaritasi **sxematik** (grid) bo'lib qoladi; to'liq interaktiv xarita v2
- [Phase 02]: 02-21: open_weekdays NULL = «hali tanlanmagan» (ruxsat, calendar_missing to'sig'ini yoqadi); '{}' = «hech qachon ochilmaydi» (hamon rad etiladi)
- [Phase 02]: 02-21: DB ish rejimini TAXMIN QILMAYDI, UI esa TAKLIF qiladi — usta 1-qadamida yettala kun oldindan belgilangan, lekin qiymat sifatida yuboriladi
- [Phase 02]: 02-21: WR-02 (market_activate/market_delete_draft tenant predikati) 3-fazaga YUQORI ustuvorlik bilan kechiktirildi — yangi migratsiya talab qiladi
- [Phase 02]: 02-22: MARKET-01…06 belgilandi — 02-VERIFICATION.md ning ochilish sharti bajarilgan (CR-01/02/03 yopilgan + real ma'lumot bandi ROADMAP'da 2026-08-01 da ochiq qayta ta'riflangan)
- [Phase 02]: 02-22: REQUIREMENTS.md holat lug'ati uch qiymat bilan chegaralandi (Done/Pending/Blocked); ro'yxat va Traceability jadvalining mosligi scripts/check-requirements-sync.mjs bilan mexanik qulflandi
- [Phase 02]: 02-22: Coverage sanoq bloklari ATAYIN tegilmadi (46 deydi, haqiqiysi 49) — qayta hisoblash 02-24 zimmasida; farq faylda va skript ogohlantirishida ko'rinadi
- [Phase 02]: 02-24: D-04 rol berish darajasi services/staff_accounts.py ga ko'chirildi (ikkinchi chaqiruvchi POST /imports/staff paydo bo'ldi; nusxa olinmadi)
- [Phase 02]: 02-24: import shablonining namunaviy telefoni + belgisisiz — + formula prefiksi va qochirish uni o'z importidan invalid_phone bilan qaytarardi
- [Phase 02]: 02-24: xodimlar rosterida D-15 skip xavfsizlik qarori — muqobil variant faylni ommaviy parol tiklash quroliga aylantirardi
- [Phase 02]: 02-23: mustaqillik darvozasi grep emas, ast bilan — docstring taqiqning sababini literal aytadi va grep uni o'z-o'ziga qarshi qo'yardi
- [Phase 02]: 02-23: XlsxWriter ZIP sanasini soatdan oladi — bayt determinizmi uchun _freeze_zip majburiy
- [Phase 02]: 02-23: nyquist_compliant kelishuv emas, hisob-kitob — skript uni ikkala yo'nalishda majburlaydi
- [Phase 02]: 02-23: rejada yozilgan sabotaj tegmasa — bu topilma; sababi o'lchanadi va ayni fayldagi qo'shni mexanizm sabotaj qilinadi
- [Phase 03]: 03-01: D-16 o'lchov bilan tasdiqlandi — o'zgarishdan oldingi `--no-dev` runtime image'da `import httpx` ModuleNotFoundError berardi; birinchi zond (`sbozor-core-api:latest`) yolg'on signal bergan edi, u aslida `dev` build ekan
- [Phase 03]: 03-01: kaskad to'liqligi `markets` ga CHET EL KALITI bo'yicha o'lchanadi, `market_id` USTUNI bo'yicha emas — `audit_log` da ustun bor, FK yo'q, ustun bo'yicha izlash darvozani yolg'on-qizil qilardi
- [Phase 03]: 03-01: `rbac.py` <-> `rbac.ts` parity darvozasi (G-8) YO'Q edi — «qo'lda sinxron saqlanadi» ikkala faylda yozilgan, tekshiradigan mexanizm esa yo'q edi; `role-gate.test.mjs` ga qo'shildi
- [Phase 03]: 03-01: `CAMERA_MANAGE` `CAMERA_VIEW` dan ajratildi (D-07) — bitta huquq ikkalasini qamrasa «direktor ko'rsin» so'rovi «NVR parolini yangilay olsin» ga aylanardi
- [Phase 03]: 03-01: teskari aloqa ikki lentaga bo'lindi va 2-fazadan meros band yopildi — `gate:fast` 32 s (chegara 180 s, KO'TARILMADI), `gate` 515 s (nomzod chegara 618 s, 03-11 yakunlaydi)
- [Phase 03]: 03-01: talablar (CAM-01/03/08/09) ATAYIN `Pending` qoldirildi — ular faza darajasida, dalil bilan, 03-11 da belgilanadi
- [Phase 03]: 03-04: NVR shifr kaliti Settings'da SecretStr va MAJBURIY — repr/Sentry lokal-o'zgaruvchi yo'lini yopadi, yo'q kalit esa startup'da yiqitadi (birinchi kamera qo'shilganda emas)
- [Phase 03]: 03-04: xususiylik is_global bo'yicha tekshiriladi (is_private EMAS) — CGNAT 100.64/10 yagona ajratuvchi holat va u sabotaj bilan o'lchandi
- [Phase 03]: 03-04: SC#2 ning uch qoidasi ON CONFLICT ning SET ifodasida, ilova mantig'ida EMAS — parallel skanda poyga bo'lmasin; channels_added esa RETURNING (xmax = 0) bilan sanaladi
- [Phase 03]: 03-04: ilova kodida simulyator NOMI izohda ham yozilmaydi — 03-02 darvozasi kodni izohdan ajratmaydi va bu ataylab; nomga bog'langan regressiya testi test faylida qoladi
- [Phase 03]: 03-05: ISAPI xato taksonomiyasi BITTA reyestrda: kodlar HTTP javobiga ham, nvr_discovery_runs.error_code ustuniga ham xizmat qiladi
- [Phase 03]: 03-05: retry predikati TESKARI (D-03): httpx.HTTPStatusError ATAYIN qamralmaydi — sabotaj urinishlar sonini 0 dan 5 ga (Hikvision qulflash chegarasi) chiqardi
- [Phase 03]: 03-05: Basic auth diagnostikasi challenge SXEMASI bo'yicha bajariladi, nvr_bad_credentials xulosasidan oldin EMAS — aks holda urinishlar sanog'i 2 bo'lardi
- [Phase 03]: 03-05: device_not_supported sharti: manufacturer BOR VA Hikvision emas — DS-7732NI-M4 dumpida bu maydon umuman yo'q
- [Phase ?]: 03-06: redis-py 8 ning socket_timeout=5 standarti ListQueueBroker ning BRPOP ini har 5 soniyada uzadi — bloklanuvchi navbat o'quvchisida socket_timeout=None MAJBURIY
- [Phase ?]: 03-06: create_run ning IntegrityError idan KEYIN o'qish uchun SAVEPOINT (begin_nested) shart — abort holatidagi tranzaksiya 409+run_id ni 500 ga aylantirardi
- [Phase ?]: 03-06: fon jobi tenant kontekstini O'ZI o'rnatadi (ActorKind.SYSTEM); kontekstsiz job HTTP qatlamidan KO'RINMAYDI va NVR ni queued qator bilan qulflaydi
- [Phase 03]: 03-07: jonli ko'rish chiptasi RESURSGA bog'lanadi — auth_request src ni chiptadagi camera_id ning stream_name i bilan solishtiradi (T-03-46; faqat chiptani tekshirish begona bozor oqimini ochiq qoldirardi)
- [Phase 03]: 03-07: go2rtc API'si IKKI yo'lda bloklanadi (/api/... va /live/api/...) — /live/ bloki prefiksni olib tashlab uzatgani uchun ikkinchisi majburiy
- [Phase 03]: 03-07: kamera yuzasining strukturaviy darvozasi METOD bo'yicha cheklanmaydi — GET ga qadalgan qamrov eng nozik POST (live-token) ni tashqarida qoldirgan edi (sabotaj bilan topildi)
- [Phase 03]: 03-07: taqiqlangan literal konfiguratsiya faylida IZOHDA ham yozilmaydi — shunda sodda grep darvozasi istisnosiz tirik qoladi va parser bilan birga ikki qatlam beradi
- [Phase ?]: 03-08: video-stream.js YOLG'IZ ISHLAMAYDI — video-rtc.js ham vendored; aks holda 03-10 bog'liqlikni go2rtc'dan yuklab D-11 ni buzardi
- [Phase ?]: 03-08: MIT izohi vendored faylga QO'SHILMAYDI (upstreamda yo'q) — u yonidagi LICENSE da; izoh qo'shish xeshni upstream tegi bilan solishtirib bo'lmas qilardi
- [Phase ?]: 03-08: poll chegarasi SERVER started_at iga tayanadi, klient taymeriga emas — ?run= bilan yangilanganda taymer noldan boshlanib qotgan yugurishni mangu poll qilardi
- [Phase ?]: 03-08: parity darvozasi (i18n:check) to'plam TO'LIQLIGINI ko'rmaydi — kalit uchala tildan olib tashlanganda u yashil qoladi va D-02 ni faqat G-1 ushlaydi (sabotaj bilan o'lchandi)
- [Phase ?]: 03-08: G-4 BUYRUQ FE'LINI izlaydi, o'zakni emas — «o'chirilmaydi» taqiqning teskarisi va u matnda BO'LISHI kerak; chegara ijobiy va salbiy nazorat testi bilan qulflandi
- [Phase ?]: 03-10: SC#2 ning UI isboti: uch hisoblagich nol bilan birga ko'rinadi; «o'zgarish topilmadi» jumlasining sharti added===0 && offline===0
- [Phase ?]: 03-10: jonli sessiya chegarasi UI tomonda (5 daq), avtorizatsiyadan qat'i nazar; [Davom ettirish] pleyerni qayta mount qiladi
- [Phase ?]: 03-10: vendored pleyerning ikki majburiy sozlamasi applyPlayerPolicy() sof funksiyasida va testga bog'langan: tashqi STUN yo'q, audio so'ralmaydi
- [Phase ?]: 03-10: NvrCard.showErrorBlock — kashfiyot nosozligini faqat panel chizadi (ikkita role=alert oldi olindi)
- [Phase 03]: 03-14: go2rtc PUT/DELETE natijasi status kodidan emas, oqimlar RO'YXATIDAN o'lchanadi — :ro config (D-11) tufayli go2rtc har doim 400 qaytaradi, amalning o'zi esa bajariladi
- [Phase 03]: 03-14: uchidan-uchiga o'lchov nomlarni MAHSULOTDAN oladi (kashfiyot hosil qilgan cam_<uuid4>, chipta URL'idan) — o'z nomini o'ylab topgan test Pitfall 4 bo'lardi
- [Phase 03]: 03-14: gate chegarasi 1200 s da qoldi — o'lchov 538 s bo'lsa ham na ko'tarildi, na tushirildi; qayta belgilash 4-fazaga band
- [Phase ?]: 04-07: succeeded+corrupt ziddiyati YOPILDI — (a) va (b) IKKALASI ham kerak, ular ikki xil qatlamda hal bo'ladi (0016)
- [Phase ?]: 04-07: D-07 endi koddagi mexanizm — _claims_rtsp_session() /picture ni RTSP oqim da'vosidan chiqaradi; usiz eng xavfsiz usul o'zini chegara qurboni deb belgilardi
- [Phase ?]: 04-07: capture_due_markets() ga uchinchi disjunkt (0017) — ijarasi tugagan running qatorli bozor ham tikda ko'rinadi; usiz ijara AYNAN o'zi qoplashi kerak bo'lgan holatda ishlamasdi
- [Phase ?]: 04-07: navbat nomi sbozor:discovery -> sbozor:jobs; ikkinchi navbat OCHILMAYDI — u ikkinchi broker va ikkinchi worker konteynerini talab qilardi
- [Phase ?]: 04-07: yurak urishi except Exception ni yutadi — o'lchandi: socket.gaierror SQLAlchemyError ga o'ralmaydi va tikni ENG OXIRIDA yiqitardi
- [Phase 04]: 04-10: kalit fabrikasining birinchi argumenti marketId — LEKIN tip tizimi yolg'iz yetarli emas, kalit shakli birlik testi bilan qiymat bo'yicha qulflandi
- [Phase 04]: 04-10: ko'zgu darvozasi MATN KATALOGIGA emas, BACKEND REYESTRIGA langarlanadi — aks holda u ichki izchillikni o'lchab TO'LIQLIKNI o'lchamaydi (04-09 12-deviatsiyasi bilan bir sinf)
- [Phase 04]: 04-10: darvozaning TETIGI artefakt chegarasidan o'tishi kerak — «katalog mavjud» tetigi ikki to'lqinga bo'lingan katalogda yolg'on-qizil beradi
- [Phase 04]: 04-10: javob enumlari z.enum bilan qulflanmaydi — bitta yangi backend a'zosi butun 175 hujayrali kunni chegarada yiqitardi
- [Phase 04]: 04-10: DL-1 da future profilning nomi/davri tahrirlanmaydi (PATCH faqat times) — yo'l o'chirib qayta qo'shish; backend yuzasi frontend rejasida kengaytirilmadi
- [Phase ?]: 04-11: yo'q kadr UCH mustaqil kanalda ko'rsatiladi (ikonka + to'liq jumlali aria-label + punktir chegara) va 44x44 nishonda — bo'sh katak SC#2 ni jimgina buzardi
- [Phase ?]: 04-11: 175 hujayrali matritsa native table semantikasida qoladi — matritsa roli QO'YILMAYDI; roving tabindex usiz ham ishlaydi va native th-scope skrinriderda kuchliroq
- [Phase ?]: 04-11: dalil-kadr baytlari sessiya tokeni bilan proxydan olinadi (tasvir elementi sarlavha qo'sha olmaydi) — har ochilish audit_read yozadi, imzolangan havola so'ralmaydi
- [Phase 04]: 04-13: planer jarayoni CLIENT_STARTUP ni ateshlaydi (taskiq cli/scheduler/run.py:392 BOSHQA bayroqni o'rnatadi) — WORKER_STARTUP ilmog'i u yerda ISHLAMAYDI; init_sentry() endi uchinchi jarayonda ham chaqiriladi
- [Phase 04]: 04-13: Sentry darvozasi KOD kirish nuqtalarini emas, compose.yaml dagi JARAYONlarni sanaydi — ro'yxatga uchinchi nom qo'shish nosozlikni n+1 da qaytadan tug'dirardi
- [Phase 04]: 04-13: kuzatuv ilmog'i get_settings() ni CHAQIRMAYDI — settings.py:329 bo'sh S3_ACCESS_KEY ni rad etadi va planer bugun Settings ni qurmaydi; aks holda kuzatuv qatlami o'zi kuzatishi kerak bo'lgan nosozlikdan yiqilardi
- [Phase 04]: 04-13: init_sentry() ning O'ZI yetarli emas — taskiq send() da try/except yo'q (cli/scheduler/run.py:157-174), add_done_callback esa istisnoni o'qimaydi (:346-350); ObservedScheduler.on_ready log.exception + capture_exception qiladi va QAYTA KO'TARADI
- [Phase 04]: 04-13: global holat (sentry_sdk.init) SUBPROCESS da o'lchanadi va har zondga NAZORAT yugurishi juft — DSN'siz False bermasa da'vo bo'sh bo'lardi
- [Phase 04]: 04-13: O'LCHOV — inspect.getsource(app.router.lifespan_context) FastAPI ning merged_lifespan ini beradi, __wrapped__ ham; bizning lifespan closure zanjirining oxirida (8 va 40 chuqurlikda TOPILMADI)
- [Phase 05]: 05-10: D-18 API qoidasi — ommaviy endpoint YOZILMAYDI; yo'qligi OpenAPI sxemasidan hosila IKKI predikat bilan o'lchanadi (yuza: router moduli; lug'at: AnswerRequest maydoni massiv ichida)
- [Phase 05]: 05-10: byudjet KUNI zone_reviews.decided_at dan olinadi (occupancy_events.business_date dan EMAS) — byudjet INSON diqqatiga qo'yilgan, ya'ni kechagi qoldiqni bugun ko'rish BUGUNGI byudjetni yeyishi kerak
- [Phase 05]: 05-10: navbat ustuvorligi avval BILLING TA'SIRI, ichida chegaraga yaqinlik (RESEARCH C.9); tanlov bitta _PRIORITY_ORDER konstantasida va uni navbat qurish ham, band olish ham ishlatadi
- [Phase 05]: 05-10 O'LCHANDI: src.queue_kind -> :queue_kind sabotaji 28 testni YASHIL qoldirdi (WHERE filtri ikkalasini teng qiladi) — da'vo 'yozilgan qiymat konstanta emas' shakliga toraytirildi va sabotaj D-prime bilan qizartirildi
- [Phase 05]: 05-10: AnswerResponse.locked HAR DOIM true — UI-SPEC 7.1 noaniq javobni tahrirlanadigan deydi, 05-05 sxemasi esa buni imkonsiz qilgan (UNIQUE + shartsiz BEFORE UPDATE); sxema ustun olindi va UI-SPEC 7.1 ESKIRGAN deb belgilandi
- [Phase 05]: 05-10: yo'l parametri review_assignment_id (assignment_id EMAS) — nom to'qnashuvi cross-tenant matritsasiga marshrutga begona OBYEKT TURINI berardi va u yashil turib hech nimani o'lchamasdi
- [Phase 05]: 05-12: D-16 (nazoratchining ichki mosligi) aniqlik hisobotida NA SON, NA MAYDON — o'lchanmagan miqdor uchun maydon ham yozilmaydi (T-05-04)
- [Phase 05]: 05-12: ikki xatoning MAXRAJI UI-SPEC 11.1 ishlangan misolidan O'LCHAB olindi — band deb xato = fp/(tp+fp), bo'sh deb xato = fn/(tp+fn)
- [Phase 05]: 05-13: darvozaning O'ZI kod shaklini boshqardi — server maydoni G-12 tokenini o'z ichiga olgani uchun kodlash api-types.ts ga ko'chdi, ikki nusxa MEXANIK ravishda imkonsiz
- [Phase 05]: 05-13: G-13 ning taqiqlangan nomlari test faylida LITERAL yozilmaydi (fayl G-12 ning skaner maydonida) — ular REYESTRDAN iteratsiya qilinadi va natija rejadagidan kuchliroq
- [Phase 05]: 05-13: «bitta so'rov = bitta qaror» POYGA masalasi — test uch bosishda uch javob yuborilishini topdi; qulf useRef da va u BAND IDENTIFIKATORINI saqlaydi (nollash kerak emas)
- [Phase 05]: 05-13: sabotaj "removeQueries vs invalidateQueries" da'vosining bugungi sozlamada O'LCHANMASLIGINI fosh qildi — kafolat JUFTLIKDAN (gcTime: 0 + removeQueries) chiqadi va ikkala yarim alohida qo'riqlanadi
- [Phase 05]: 05-13: o'lchanmagan sonning o'rniga NOL yozilmaydi — D-19 qatori report_view yo'q sessiyada UMUMAN chizilmaydi (T-05-04)
- [Phase 05]: 05-14: foiz KLIENTDA hisoblanmaydi — uch nisbat, uch oraliq, baseRate, measured va min_sample SERVERDAN; klientdagi qayta hisob xato bo'lib emas, IKKINCHI JAVOB bo'lib chiqardi (5,4 % vs 3,8 %)
- [Phase 05]: 05-14: D-16 ekranda ham YO'Q — na qator, na tire, na nol, na kalit; yo'qlik «so'z topilmadi» bilan emas, <dt> to'plamining literal tengligi va z.strictObject bilan o'lchanadi
- [Phase 05]: 05-14: DL-5 slot qatorlarisiz qurildi — OccupancyStallItem da slot vaqti, kamera va snapshot_id YO'Q; to'qish (stub) va bo'sh jadval (placeholder) rad etildi, yangi marshrut Rule 4 sifatida 05-15 ga
- [Phase 05]: 05-15: dalil-kadr huquq bo'shligi TO'RTINCHI marta kechiktirilmadi — fazani yopishdan OLDIN yopildi. Kengaytma AYNAN BITTA marshrutda (`GET /snapshots/{id}/image`), `ROLE_PERMISSIONS` matritsasi va `rbac.py`/`rbac.ts` juftligi TEGILMADI
- [Phase 05]: 05-15: `require_any_permission()` ning introspektsiya tegi KO'PLIKDA (`required_any_permissions`) va `required_permission` QO'YILMAYDI — qo'yilsa struktura skanerlari «CAMERA_VIEW MAJBURIY» deb yolg'on gapirardi
- [Phase 05]: 05-15: ruxsat etilgan huquqlar to'plami darvozada IKKINCHI marta yoziladi, mahsulot konstantasidan import QILINMAYDI — import darvozani o'zi tekshirayotgan qiymatga bog'lardi va mahsulotga uchinchi huquq qo'shilsa u jimgina kengayardi
- [Phase 05]: 05-15: `gate` chegarasi 900 -> 1250 s KO'TARILDI, lekin JIMGINA emas — tinch xost ta'minlandi (6 ta `parnikkpi-*` konteyner to'xtatilib, o'lchovdan keyin tiklandi), uchala o'lchov (1009/1004/983 s) alohida yozildi va sabab o'lchandi: zanjirga `cv:lint` + `cv:test` qo'shilgan
- [Phase 05]: 05-15: AI-02 `Blocked` — talab matnining birinchi jumlasi CI'da REAL ONNX artefakti bilan bajarilmaydi va modelning aniqligi umuman o'lchanmagan; mexanika qatlamining yashilligi bilan aniqlik qatlamining yo'qligini yopish TAQIQLANADI (D-01)
- [Phase 05]: 05-15: UI-SPEC ning ikki eskirgan bo'limi (§11.6 D-16 qatori, §11.7 DL-5 per-slot jadvali) TUZATILDI — qurilmagan narsani ta'riflagan spetsifikatsiyani keyingi faza «yo'qolgan funksiya» deb o'qiydi
- [Phase 05]: 05-15: sabotaj sistemaga YETIB BORSA ham hech nima qizarmasa, tuzatish TESTDA emas — HOLATDA. SC#4 `and`->`or` sabotajini o'tkazib yuborgan edi; endi butun ko'r namuna javoblanadi (70/30 kvota `eval` ham, `train` ham beradi) va shundan keyin sabotaj qizardi
- [Phase ?]: 08-20: mezon moduli mavjud testlarni TAKRORLAMAYDI — u ularni zanjir sifatida bog'laydi va yagona savol beradi: ROADMAP dagi jumla bugun rostmi?
- [Phase ?]: 08-20: SC#2 namunasi shunday qurildi-ki «band deb xato» O'LCHANADI, «bo'sh deb xato» esa BO'SH KATAK qoladi — ikki maxrajning boshqaligi FAQAT shunda hujjatning O'ZIDA ko'rinadi
- [Phase ?]: 08-20: AST darvozasining TETIGI «nomni ishlatgan» emas, «javob haqida DA'VO qilgan» (status_code) — birinchi shakl nazorat testini yolg'on-qizil qilgan edi
- [Phase ?]: 08-20: zaxira yurak urishi FAQAT ops/backup/heartbeat.sql dan; DELETE taqiqdan CHIQARILGAN — u faktni yozmaydi, o'lchov boshlanadigan bo'sh holatni quradi
- [Phase ?]: 08-20: respx bu fazada TAQIQLANGAN ildizlarga qo'shildi (7-fazada ATAYIN yo'q edi) — bu fazaning birorta mezoni tashqi tarmoqqa chiqmaydi
- [Phase ?]: 08-20: FOUND-07 Blocked — mexanizm uch qatlamda yashil, lekin zanjir BUGUNGACHA HECH QACHON yugurmagan (.env da RESTIC kalitlari yo'q)
- [Phase ?]: 08-20: gate byudjeti KO'TARILMADI (1909/1842 s < 2300 s); HALOLLIK — uch emas, IKKI o'lchov olindi va bu uch joyda yozildi
- [Phase ?]: 08-20: sabotaj modulni IMPORT QILINADIGAN holda qoldirishi shart — aks holda u mezonni emas, yig'ilishni o'lchaydi (S-5 ning birinchi shakli)

### Pending Todos

[From .planning/todos/pending/ — ideas captured during sessions]

None yet.

### Blockers/Concerns

- **[Phase 0 → 3/4] NVR kirish** — login/parol va CGNAT holati bozor ma'muriyatidan; 12 haftalik jadvaldagi eng katta tashqi xavf. 1-haftada boshlanmasa 3–5 fazalar siljiydi.
- **[Phase 0 → 8] Tushum bazasi** — faqat 1-haftada, yig'uvchilar bilishidan oldin o'lchanadi; o'tkazib yuborilsa ROI da'vosi isbotlanmaydi.
- **[Phase 5 → dala] AI-02: CV aniqligi o'lchanmagan** — real ONNX artefakti + oltin to'plam kerak; RF-DETR kechikishi Contabo AMD EPYC'da ham tekshirilmagan; qorong'i/IR kadrlar noyabrdan ertalabki slotlarga ta'sir qiladi. Mexanika yashilligi bilan YOPILMAYDI (D-01).
- **[Phase 8 → dala] FOUND-07 ochiq yarmi: offsite S3** — provayder + byudjet qarori buyurtmachidan; ungacha `backup_stale` (CRITICAL) halol chiqib turadi va uni o'chirish TAQIQ. 08-HUMAN-UAT №2/№3.
- **[Phase 1–2 parallel] Huquqiy ko'rik** — kvitansiya maydonlari, CCTV shaxsiy ma'lumot, KKM/UzQR talablari avtomatik xulosadan olingan; mahalliy yurist tasdig'i launch'gacha kerak.
- **[Phase 0] Tushum bazasi** — yig'uvchilar bilishidan oldin o'lchanadi; o'tkazib yuborilsa ROI da'vosi isbotlanmaydi (yagona qaytarilmas band).
- **Xavfsizlik ko'rigi (08)** — enforcement=true, lekin 08-SECURITY.md yo'q (7-faza presedenti bilan yopildi); shaxsiy-ma'lumot eksport yuzalari qo'shilgani uchun go-live'dan oldin `/gsd-secure-phase 08` tavsiya etiladi.
- CAM-02 Blocked: CI konteynerida wg0 yo'q — «server NVR'ga FAQAT tunnel orqali» dala o'lchovi. Egasi Ops, tetigi VPS deploy'i, 03-HUMAN-UAT #1/#2.
- Go-live dala darvozalari jamlangan: `08-HUMAN-UAT.md` (6 band, har biri egasi/tetigi bilan; 01–07 meros bandlari havola bilan).

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 260816-75e | Topilma №C: MARKET-06 plan-xarita to'lov ranglari + rasta kartasi + /billing/map | 2026-08-16 | 9dbd631, 192eb2e, 43b4628 | [260816-75e-topilma-c-market-06-plan-xarita-tolov-ra](./quick/260816-75e-topilma-c-market-06-plan-xarita-tolov-ra/) |
| 260816-75g | Topilma №F+№G+№H: diagnostika rejimi, rol tahrirlash, admin dashboard holati | 2026-08-16 | 4d0e583, f57c3da, a13c447 | [260816-75g-topilma-f-g-h-diagnostika-yorligi-rol-ta](./quick/260816-75g-topilma-f-g-h-diagnostika-yorligi-rol-ta/) |
| 260816-75c | Topilma №L+№E+№M: kassir lookup konteksti, kelajak tarif yorlig'i, bekor qatorlarini ajratish | 2026-08-16 | f2b1830, aed8391, 93c0a78 | [260816-75c-topilma-l-e-m-kassir-lookup-kontksti-kel](./quick/260816-75c-topilma-l-e-m-kassir-lookup-kontksti-kel/) |
| 260816-6r3 | Topilma №I: notification_stale alerti (navbat yoshi) + yetkazish jadvalida sana/sabab | 2026-08-16 | 1ea9c5d, 55535f0 | [260816-6r3-topilma-i-xabar-navbati-stale-alerti-va-](./quick/260816-6r3-topilma-i-xabar-navbati-stale-alerti-va-/) |
| 260816-6r1 | Topilma №J+№K: kamera amallari RBAC-ko'zgusi (majburiy prop) + 20 sahifada ForbiddenNotice | 2026-08-16 | 154c751, 1708fa7 | [260816-6r1-topilma-j-k-direktor-kamera-tugmalari-rb](./quick/260816-6r1-topilma-j-k-direktor-kamera-tugmalari-rb/) |
| 260816-6r1 | Topilma №J+№K: NVR kartasining uchta amali `camera_manage` ostiga (majburiy prop + WIRING testi, sabotaj bilan) va rad etish ekrani 20 sahifadan bitta `ForbiddenNotice` ga (+`localeHref` 7→1) | 2026-08-16 | 154c751, 1708fa7 | [260816-6r1-topilma-j-k-direktor-kamera-tugmalari-rb](./quick/260816-6r1-topilma-j-k-direktor-kamera-tugmalari-rb/) |
| 260816-5yz | Kod-review: stall-dialog tri-state + schedule-dialog 3 tozalash (halol topilmadi-holati, guard-clause, EmptyState) | 2026-08-16 | 067a4dd, 8c142a3 | [260816-5yz-tri-state-va-schedule-dialog-tozalash-st](./quick/260816-5yz-tri-state-va-schedule-dialog-tozalash-st/) |
| 260816-5ys | Kod-review: jim-disabled submit anti-naqshi 5 saytda supurildi + G-SUBMIT darvozasi | 2026-08-16 | 04a473b, 486fdb1, 0315196 | [260816-5ys-jim-forma-supurish-disabled-submit-anti-](./quick/260816-5ys-jim-forma-supurish-disabled-submit-anti-/) |
| 260816-5mn | Topilma №B+№A: bozorni faollashtirish yo'li ochildi, qoralama-redirect tuzatildi | 2026-08-16 | b90bb09, 9e52fd5, 96171c1 | [260816-5mn-topilma-b-a-bozorni-faollashtirish-yo-li](./quick/260816-5mn-topilma-b-a-bozorni-faollashtirish-yo-li/) |
| 260815-86p | Topilma №2/№4/№6: usta 5-qadamiga qo'lda qo'shish, rolsiz saqlashda ko'rinadigan validatsiya, jadval dialogining bo'sh/xato holatlari — uchalasi TDD bilan | 2026-08-15 | c411636, d059a7d, dc2ea27 | [260815-86p-topilma-2-4-6-usta-rastalar-qadamiga-qo-](./quick/260815-86p-topilma-2-4-6-usta-rastalar-qadamiga-qo-/) |
| 260814-p4g | Topilma №8: kassir rasta qidiruvida Enter — tashxis: kod sog'lom, fokus-yo'naltirilgan regressiya darvozasi qo'shildi | 2026-08-14 | 8ee8e2e, e3e0cf4 | [260814-p4g-topilma-8-kassir-rasta-qidiruvida-enter-](./quick/260814-p4g-topilma-8-kassir-rasta-qidiruvida-enter-/) |
| 260811-kyz | 06-14-SUMMARY.md eskirgan byudjet da'vosini yopilgan holatga moslash (xavfsizlik auditi F-2) | 2026-08-11 | 8b5cf6f | [260811-kyz-06-14-summary-md-eskirgan-byudjet-da-vos](./quick/260811-kyz-06-14-summary-md-eskirgan-byudjet-da-vos/) |

## Deferred Items

Items acknowledged and carried forward from previous milestone close:

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| Test infra | **Flake №13 — `test_cross_tenant_object_returns_404[POST .../unblock]`: `ExpiredSignatureError`.** Uzun (75 daq) va yuklangan yugurishda bitta tenant testi `401 invalid_token` oldi. Sabab MAHSULOTDA EMAS: header fixture'lari FUNKSIYA doirasida (`@pytest.fixture` scope'siz) va tokenni har testda qaytadan oladi — ya'ni token so'rovdan bir necha SEKUND oldin yasalgan va 15 daqiqalik token qonuniy ravishda eskirgan bo'lishi MUMKIN EMAS. Yagona izoh — konteyner soatining siljishi (Docker Desktop/WSL2 host uyquga ketganda ma'lum hodisa). ⛔ ISBOTLANMAGAN: o'lchov paytida siljish 5 s edi, ya'ni gipotezani retroaktiv tasdiqlay olmadim. ⛔ TUZATILMADI VA BU ONGLI: `test_settings` da TTL ni uzaytirish urinildi va u `test_auth_login::test_login_returns_access_token_and_roles` ni buzdi (`assert 28800 == 900`) — o'sha test 15 daqiqalik token MAHSULOT KAFOLATINI o'lchaydi, ya'ni uni testga moslash shartnomani buzardi; o'zgarish QAYTARILDI. ⚠ MUHIM YON TOPILMA: o'sha testning birinchi asserti (`status_code != 403`) 401 BILAN O'TIB KETDI — kuchsizroq yozilgan darvoza yashil qolib «begona bozor obyekti 404» da'vosini hech nima bilan isbotlamasdi. Ikki assert naqshi (T-01-76) aynan shuni qutqardi va u boshqa xavfsizlik darvozalarida ham saqlanishi kerak. Alohida yugurtirilganda fayl 0 yiqilish beradi (o'lchandi). | Open — kuzatilsin | 2026-08-18 |

## Session Continuity

Last session: 2026-08-17T19:17:13.255Z
Stopped at: Phase 10 UI-SPEC approved
Resume file: None
