---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: executing
stopped_at: Completed 03-09-PLAN.md
last_updated: "2026-08-03T12:19:01.846Z"
last_activity: 2026-08-03
progress:
  total_phases: 9
  completed_phases: 2
  total_plans: 50
  completed_plans: 48
  percent: 22
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-07-28)

**Core value:** Bozor ma'muriyati har bir band rastadan patta to'liq yig'ilayotganini raqamlar va rasm-dalil bilan ko'radi — "band, lekin to'lovsiz" rastalar kunlik hisobotda avtomatik fosh bo'ladi.
**Current focus:** Phase 03 — nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi

## Current Position

Phase: 03
Plan: 10 of 11
Status: Ready to execute
Last activity: 2026-08-03

Progress: [████████░░] 82% (9/11 reja)

**Muddat:** 12 hafta, 2026-07-28 → ~2026-10-18 (Karmanada jonli). Zaxira yo'q.

## Performance Metrics

**Velocity:**

- Total plans completed: 60 (o'lchov yozilgani: 1 — quyidagi jadval faqat metrikasi qayd etilgan rejalarni sanaydi)
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

## Deferred Items

Items acknowledged and carried forward from previous milestone close:

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| *(none)* | | | |

## Session Continuity

Last session: 2026-08-03T12:19:01.838Z
Stopped at: Completed 03-09-PLAN.md
Resume file: None
