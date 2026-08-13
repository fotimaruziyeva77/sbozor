---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: executing
stopped_at: Phase 8 context gathered
last_updated: "2026-08-13T04:57:28.455Z"
last_activity: 2026-08-12 -- Phase 07 execution started
progress:
  total_phases: 9
  completed_phases: 7
  total_plans: 119
  completed_plans: 119
  percent: 78
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-07-28)

**Core value:** Bozor ma'muriyati har bir band rastadan patta to'liq yig'ilayotganini raqamlar va rasm-dalil bilan ko'radi — "band, lekin to'lovsiz" rastalar kunlik hisobotda avtomatik fosh bo'ladi.
**Current focus:** Phase 07 — nomuvofiqlik-bildirishnoma-va-botlar

## Current Position

Phase: 07 (nomuvofiqlik-bildirishnoma-va-botlar) — EXECUTING
Plan: 1 of 17
Total Plans in Phase: 17
Status: Executing Phase 07
Last activity: 2026-08-12 -- Phase 07 execution started

Progress: [██████████] 100% (15/15 reja — 05-01…05-15)

✅ **5-FAZANING IJROSI TUGADI (15/15 reja).** `05-15` fazani yopdi:
beshala ROADMAP mezoni `tests/integration/test_phase5_criteria.py` da
**BITTA buyruqda** o'lchanadi va uchala darvozasi (mezon boshiga bitta
test · meta-test · soxtalashtirishsiz o'lchov) yashil.

⚠ **ROADMAP dagi faza belgisi HAMON `- [ ]`** va bu ataylab: fazani
yopish qarori **qayta tekshiruvniki** (`/gsd-verify-work`), ijrochi emas.
4-fazada ham aynan shunday saqlangan.

✅ **UCH REJA DAVOMIDA OCHIQ TURGAN XAVFSIZLIK BANDI YOPILDI.** Sof
`inspector` roli dalil kadrini endi **KO'RADI**: `GET /snapshots/{id}/
image` `CAMERA_VIEW` **YOKI** `OCCUPANCY_REVIEW` ostiga o'tdi
(`require_any_permission()`, `EVIDENCE_FRAME_PERMISSIONS`). Kengaytma
**AYNAN BITTA marshrutda** — kadr metama'lumoti, kun jurnali va alert
oqimi nazoratchiga YOPIQ QOLDI va bu ikki MUSTAQIL darvoza bilan
o'lchanadi (struktura: marshrut grafi; xulq: HTTP). `ROLE_PERMISSIONS`
matritsasi va `rbac.py`/`rbac.ts` juftligi **TEGILMADI**, ya'ni M-8
bandining o'zi hamon rost.

✅ **4-FAZADAN MEROS `gate` BANDI (D-26/W0-13) YOPILDI.** O'lchov
**TINCH XOSTDA** olindi: xostdagi 6 ta `parnikkpi-*` konteyner (aynan
`04-14` ni ifloslantirgan stek) `docker stop` bilan to'xtatildi va
o'lchovdan keyin tiklandi. Uch o'lchov: **1009 / 1004 / 983 s**
(tarqoqlik 26 s = 2,6 %). Nazorat: `gate:fast` **87 s** (chegara 180 s,
o'zgarmadi). Yangi chegara = 1009 × 1,20 → **1250 s**, `package.json`
dagi `//gate-budget` izohida ham, `05-VALIDATION.md` da ham BIR XIL.
⚠ Ko'tarish sababi degradatsiya EMAS: zanjirga `cv:lint` + `cv:test`
qo'shildi (05-02) va to'plam o'sdi.
⚠ **`C:` diski 91 % to'la (bo'sh 15 GB)** — Docker VHDX o'sha yerda;
kelajakdagi o'lchovlar uchun xavf sifatida yozib qo'yildi.

⛔ **AI-02 `Blocked` — VA BU FAZANING ENG MUHIM HALOLLIGI.** Talab
matnining ikkinchi jumlasi («AI natijasi confidence bilan saqlanadi va
hech qachon o'zgartirilmaydi») to'liq o'lchangan. Birinchi jumlasi
(«RF-DETR ONNX Runtime CPU da har zonani baholaydi») CI'da **real
artefakt bilan bajarilmaydi** — `.onnx` fayli yo'q, `-m model` bandlari
umuman chaqirilmaydi — va **modelning ANIQLIGI umuman o'lchanmagan**,
chunki oltin to'plam bo'sh. Mexanika qatlamining yashilligi bilan
aniqlik qatlamining yo'qligini yopish TAQIQLANADI (D-01) va bu endi
mexanik darvoza bilan ham qo'llab-quvvatlanadi: mezon modulida
`precision`/`recall`/`f1`/`map` **nomlari** `ast` daraxtidan taqiqlangan.
AI-01/03/04/05/06 esa dalil bilan `Done`. Sanoq: Done 21 · Pending 26 ·
Blocked 2.

⚠⚠ **D-16 (nazoratchining ichki mosligi) QURILMADI VA QURILMAYDI.**
`05-14` gacha u «ekranda yo'q» edi; `05-15` uni **spetsifikatsiyadan
ham** olib tashladi (UI-SPEC §11.6). Sabab: `audit_draw` har hodisani
eng ko'pi bilan bir marta tortadi va takroriy band mexanizmi YO'Q.
Spetsifikatsiya qurilmagan narsani ta'riflab tursa, keyingi faza uni
**yo'qolgan funksiya** deb o'qirdi. §11.7 (DL-5 per-slot jadvali) ham
shu sababdan tuzatildi — u marshrut YO'Q bo'lgan qatorlarni talab
qilardi.

⚠ **SABOTAJ O'LCHOVINING YANGI DARSI (`05-15`, S-D).** `accuracy_report`
ning `purpose AND queue_kind` filtri `or` ga o'zgartirilganda SC#4
**umuman qizarmadi** — sabotaj sistemaga yetib borgan, lekin test
tanlagan MA'LUMOT ikkala shoxda ham bir xil natija berardi. Tuzatish
testni emas, **HOLATNI** kengaytirish bo'ldi: endi butun ko'r namuna
javoblanadi (70/30 kvota `eval` ham, `train` ham beradi) va hisobotdagi
son `eval` lar soniga TENG bo'lishi talab qilinadi. Shundan keyin
sabotaj qizardi.

⚠ **OCHIQ BANDLAR (bloklamaydi, LEKIN nomlangan):**
`05-HUMAN-UAT.md` — sakkiz band, har birida ega va tetik. Birinchisi
**detektorning aniqligi**. Ikki `SECURITY DEFINER` funksiya
(`audit_draw_due_markets()`, `occupancy_day_close_markets()`) hamon
chaqiruvchisiz — qarori 6-fazaning billing tikida (Rule 4, yuzasi tor
va `FORBIDDEN_SURFACE_TOKENS` darvozasi bilan qulflangan).

**Muddat:** 12 hafta, 2026-07-28 → ~2026-10-18 (Karmanada jonli). Zaxira yo'q.

## Performance Metrics

**Velocity:**

- Total plans completed: 88 (o'lchov yozilgani: 1 — quyidagi jadval faqat metrikasi qayd etilgan rejalarni sanaydi)
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

## Accumulated Context

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

### Pending Todos

[From .planning/todos/pending/ — ideas captured during sessions]

None yet.

### Blockers/Concerns

- **[Phase 0 → 3/4] NVR kirish** — login/parol va CGNAT holati bozor ma'muriyatidan; 12 haftalik jadvaldagi eng katta tashqi xavf. 1-haftada boshlanmasa 3–5 fazalar siljiydi.
- **[Phase 0 → 8] Tushum bazasi** — faqat 1-haftada, yig'uvchilar bilishidan oldin o'lchanadi; o'tkazib yuborilsa ROI da'vosi isbotlanmaydi.
- **[Phase 4] Kadr olish usuli hal qilinmagan** — ISAPI vs go2rtc frame vs ffmpeg; tadqiqot fayllari uch xil javob beradi, real NVR'da o'lchanadi.
- **[Phase 4] Job orchestration** — DB-materialized `capture_runs` + `SKIP LOCKED` vs navbat kutubxonasi; bitta aniq qaror kerak. ⚠ `arq` variant sifatida O'CHDI (03-01 da qulflandi): u `redis[hiredis]<6` talab qiladi, core-api esa `8.0.1` ga qadalgan — `taskiq` + `taskiq-redis` o'rnatildi va `test_runtime_deps.py` `arq` ni bloklaydi.
- **[Phase 5] CV samaradorligi o'lchanmagan** — RF-DETR ONNX kechikishi Contabo AMD EPYC'da tekshirilmagan; qorong'i/IR kadrlar noyabrdan boshlab ertalabki 5 slotga ta'sir qiladi.
- **[Phase 1–2 parallel] Huquqiy ko'rik** — kvitansiya maydonlari, CCTV shaxsiy ma'lumot, KKM/UzQR talablari avtomatik xulosadan olingan; mahalliy yurist tasdig'i launch'gacha kerak.
- **[Phase 0] 7 ochiq buyurtmachi savoli** — javoblar Phase 2 va Phase 6 batafsil rejasidan oldin kerak.
- **Stek yangilanishi:** MinIO arxivlangan → SeaweedFS; detektor RF-DETR (Nano→Large, Apache-2.0). PROJECT.md Key Decisions yangilanishi kerak.
- ~~03-11: npm run gate 950 s ga chiqdi (03-01 nomzod chegarasi 618 s)~~ — **YOPILDI 03-11 da:** uch martadan o'lchandi (1000/994/983 s), sovuq va issiq yugurish ajratildi, chegara 1200 s qilib asoslandi; qolgan band — quyidagi 31 % qayta bajarish
- [Phase 4] npm run gate — 1000 s, shundan 316 s (31 %) qayta bajarish; taklif: sim:up ni zanjir boshiga, test:tenancy va test:sim ni gate'dan olib tashlash
- [Phase 4] go2rtc-sim oqimini birorta test iste'mol qilmaydi — CAM-03 va CAM-09 aynan shu sababdan Blocked; yopilish yo'li: -m sim ostida go2rtc-sim'dan bitta kadr olish
- CAM-02 Blocked: CI konteynerida wg0 yo'q — «server NVR'ga FAQAT tunnel orqali kiradi» o'lchanmaydi (Pitfall 10). Egasi Ops, tetigi VPS deploy'i, bandlari 03-HUMAN-UAT.md #1 va #2
- 05-10: sof inspector roli dalil kadrini ko'ra olmaydi — GET /snapshots/{id}/image CAMERA_VIEW talab qiladi, ROLE_PERMISSIONS[INSPECTOR] esa aynan {OCCUPANCY_REVIEW}. RBAC bu fazada ATAYIN tegilmagan (M-8); qaror 05-13 yoki 05-15 da

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 260811-kyz | 06-14-SUMMARY.md eskirgan byudjet da'vosini yopilgan holatga moslash (xavfsizlik auditi F-2) | 2026-08-11 | 8b5cf6f | [260811-kyz-06-14-summary-md-eskirgan-byudjet-da-vos](./quick/260811-kyz-06-14-summary-md-eskirgan-byudjet-da-vos/) |

## Deferred Items

Items acknowledged and carried forward from previous milestone close:

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| *(none)* | | | |

## Session Continuity

Last session: 2026-08-13T04:57:28.417Z
Stopped at: Phase 8 context gathered
Resume file: .planning/phases/08-hisobotlar-mustahkamlash-va-ishga-tushirish/08-CONTEXT.md
