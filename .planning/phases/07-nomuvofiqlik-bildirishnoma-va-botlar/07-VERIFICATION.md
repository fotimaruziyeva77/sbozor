---
phase: 07-nomuvofiqlik-bildirishnoma-va-botlar
verified: 2026-08-12T18:00:00Z
status: gaps_found
score: 2/5 ROADMAP muvaffaqiyat mezoni to'liq VERIFIED (qolgan 3 tasi qisman)
overrides_applied: 0
gaps:
  - truth: "Direktor ertalab dayjest (kechagi tushum, bandlik %, TOP-10 qarzdor) va kechqurun nomuvofiqlik xabarini Telegramda oladi"
    status: failed
    reason: >
      `market_notification_settings` jadvaliga (director_chat_id ustuni) butun repo
      bo'ylab BIRORTA yozuv yo'li yo'q — na migratsiya backfill, na usta, na
      /api/v1/*, na /internal/bot/*, na bot-service handleri. Shu sabab
      `resolve_chat_id()` produksiyada HAR DOIM `None` qaytaradi va `_settle()`
      UNRESOLVED shoxi uchun terminal chegara yo'q (faqat RETRY shoxi
      MAX_ATTEMPTS bilan cheklangan) — qator abadiy `pending` bo'lib qoladi va
      15 daqiqada bir marta qayta jadvallanadi, MANGU. test_sc3 yashil, chunki u
      sozlama qatorini fixture orqali to'g'ridan-to'g'ri SQL bilan yozadi —
      mahsulot yo'lidan emas.
    artifacts:
      - path: "services/core-api/app/repositories/outbox_repo.py"
        issue: "market_notification_settings ga INSERT/UPDATE qiladigan funksiya yo'q; faqat _RESOLVE_DIRECTOR_CHAT (SELECT) mavjud (405-qator)"
      - path: "services/core-api/app/jobs/outbox.py:1162-1164"
        issue: "_settle() da faqat `RETRY` shoxi attempt_count>=MAX_ATTEMPTS bilan FAILED ga aylanadi; UNRESOLVED shoxi bu tekshiruvdan chetlab o'tadi va reschedule(now+900s) bilan cheksiz davom etadi"
      - path: "services/bot-service/app/handlers/"
        issue: "faqat binding.py/start.py/vendor.py bor — direktorning chatini bog'laydigan handler UMUMAN yaratilmagan"
      - path: "migrations/versions/0023_notification_domain.py:529-568"
        issue: "jadvalni yaratadi, lekin hech qanday seed/backfill yozmaydi"
    missing:
      - "market_notification_settings.director_chat_id ni yozadigan YO'L: (a) bot-service'ga direktor /start handleri + POST /internal/bot/director/bind, YOKI (b) PATCH /api/v1/markets/{id}/notification-settings (MARKET_MANAGE ostida)"
      - "_settle() da UNRESOLVED uchun ham terminal chegara (masalan UNRESOLVED_MAX_ATTEMPTS) — aks holda navbat hali ham yiliga ~730 o'lik qator bilan boshqa xabarlarni (jumladan CASH-05 kvitansiyalarini) head-of-line blocking bilan xavf ostiga qo'yadi"
      - "market_create() kaskadiga market_notification_settings qatorini yaratish (yoki eksplitsit COALESCE standarti bilan ishlashni davom ettirish qarori hujjatlashtirilishi)"

  - truth: "Har nomuvofiqlik case sifatida yuritiladi — mas'ul, holat (yangi/ko'rilmoqda/asosli/asossiz) va yechim yoziladi; hit-rate metrikasi hisoblanadi"
    status: partial
    reason: >
      Holat o'tishlari, audit qatorlari va hit-rate hisob-kitobi (server darajasida)
      TO'G'RI ishlaydi (test_sc2 mahsulot yo'lini to'liq yuritadi va tasdiqlaydi).
      Lekin "mas'ul... yoziladi" bandi va case navbatini BOSHQARISH ekrani to'rtta
      mustaqil, bir-biridan mustaqil aniqlangan nuqsonga ega: (1) direktor
      tanlagan mas'ul serverga umuman yetib bormaydi va o'rniga har doim
      o'tishni qilgan aktor yoziladi; (2) case navbati 50 qatorda jimgina
      qirqiladi va next_cursor hech qachon iste'mol qilinmaydi; (3) bitta ochiq
      dialogda ketma-ket ikkinchi qaror (masalan in_review->justified)
      submittedRef ning case_id-kalitlangani sabab jim tashlab yuboriladi; (4) besh
      xato kodidan tashqari HAR QANDAY saqlash xatosi (tarmoq uzilishi, 422 massiv
      detail, 429/5xx) ekranda hech narsa chizmaydi — muvaffaqiyat bilan
      farqlanmaydi.
    artifacts:
      - path: "services/core-api/app/api/v1/reconciliation.py:657-665"
        issue: "reconciliation_repo.transition() chaqiruvida payload.assignee_user_id UMUMAN uzatilmaydi"
      - path: "services/core-api/app/repositories/reconciliation_repo.py:877"
        issue: "assignee_user_id = COALESCE(:actor_user_id, assignee_user_id) — tanlangan mas'ul o'rniga har doim aktorning o'zi yoziladi"
      - path: "frontend/src/lib/reconciliation-queries.ts:82,625-634"
        issue: "CASE_PAGE_SIZE=50 e'lon qilingan, lekin butun frontend bo'ylab 0 iste'molchi (grep bilan tekshirildi); assigneeUserId to'g'ri yuboriladi, lekin backend uni tashlaydi"
      - path: "frontend/src/components/reconciliation/case-list.tsx:104"
        issue: "useReconciliationCases(day, \"\") — cursor doim qat'iy bo'sh, next_cursor holatiga bog'lanadigan state yo'q"
      - path: "frontend/src/components/reconciliation/case-detail-dialog.tsx:349-350"
        issue: "submittedRef.current === detail.case_id bo'yicha qulflanadi (qaror emas, case bo'yicha) — ikkinchi haqiqiy o'tish jim `return` qiladi"
      - path: "frontend/src/components/reconciliation/case-detail-dialog.tsx:426-434"
        issue: "errorView === null bo'lganda HECH NARSA chizilmaydi; reconciliation-errors.ts:106-108 da'vo qilgan errors.generic zaxirasi bu yagona chaqiruvchida yo'q"
    missing:
      - "PATCH marshrutiga alohida assignee_user_id argumenti + user_market_roles ustidan begona-bozor tekshiruvi (maydon ulanganda tenancy teshigi OCHILMASLIGI uchun ikkalasi BIRGA)"
      - "case-list.tsx/delivery-list.tsx da next_cursor ni iste'mol qiladigan useInfiniteQuery yoki hech bo'lmaganda \"qirqildi\" degan ko'rinadigan signal"
      - "submittedRef ni case_id+status juftligi (yoki onSettled) bilan qulflash"
      - "errorView === null && update.isError holatida errors.generic ni chizish"

  - truth: "To'lov kiritilishi bilan sotuvchiga zudlik push-kvitansiya boradi (summa, rasta, kassir, vaqt) va qarz N kundan oshsa avtomatik eslatma keladi — barcha xabarlar outbox orqali, throttling va quiet hours hurmat qilinib, yetkazilganlik holati bilan"
    status: partial
    reason: >
      Kvitansiya niyatining to'lov bilan BIR TRANZAKSIYADA, idempotent yozilishi
      (CASH-05) va quiet-hours/overdue_days bozor kesimidagi farqlanishi
      (test_sc5) mahsulot yo'lida TO'G'RI ishlaydi. Lekin outbox mexanizmining
      o'zida ikkita mustaqil, kodga tayangan nuqson bor: (1)
      OUTBOX_TICK_BUDGET_SECONDS faqat OUTBOX_BATCH_SIZE arifmetikasida
      ishlatiladi, tikning o'zida HECH QACHON deadline sifatida tekshirilmaydi —
      7+ to'la navbatli bozorda bitta tik OUTBOX_LEASE_SECONDS (120s) dan oshadi
      va ijara muddati tugagan qator qayta olinib, BIR XIL kvitansiya IKKI MARTA
      yuboriladi; (2) attempt_count claim() da SHARTSIZ oshadi — hatto HTTP
      so'rovi umuman yuborilmagan UNRESOLVED holatda ham. Botga 3+ kun kech
      ulangan sotuvchi ~288 marta hisoblangan holda birinchi HAQIQIY urinishga
      yetadi va birinchi vaqtinchalik xato (502) darhol `failed` beradi — qayta
      urinishsiz. Bundan tashqari yetkazilganlik ro'yxati (delivery-list.tsx) ham
      50 qatorda jimgina qirqiladi.
    artifacts:
      - path: "services/core-api/app/jobs/outbox.py:184-193"
        issue: "OUTBOX_TICK_BUDGET_SECONDS deklaratsiyadan tashqari faqat OUTBOX_BATCH_SIZE hisoblashda o'qiladi"
      - path: "services/core-api/app/jobs/outbox.py:939-943"
        issue: "for market_id in market_ids: — deadline tekshiruvi yo'q, barcha bozor ketma-ket, to'xtovsiz yuguradi"
      - path: "services/core-api/app/repositories/outbox_repo.py:284-288"
        issue: "_CLAIM_DUE ning claimed CTE'sida attempt_count = o.attempt_count + 1 SHARTSIZ — UNRESOLVED (HTTP yuborilmagan) holatni ham hisoblaydi"
      - path: "services/core-api/app/jobs/outbox.py:1162-1164"
        issue: "_settle() faqat RETRY shoxini MAX_ATTEMPTS bilan tekshiradi, UNRESOLVED dan RETRY ga o'tgan qatorning hisoblagichi allaqachon yeb bo'lingan"
      - path: "frontend/src/components/reconciliation/delivery-list.tsx"
        issue: "next_cursor iste'mol qilinmaydi (DELIVERY_PAGE_SIZE=50 server chegarasi, cursor state yo'q)"
    missing:
      - "outbox_tick() ichida monotonic() bilan haqiqiy deadline (OUTBOX_TICK_BUDGET_SECONDS) — byudjet tugaganda qolgan bozorlar keyingi tikka qoldiriladi"
      - "attempt_count ni FAQAT haqiqiy jo'natish urinishida oshirish (UNRESOLVED shoxini alohida hisoblash yoki hisoblamaslik)"
      - "delivery-list.tsx da next_cursor iste'moli"
deferred: []
human_verification:
  - test: "Haqiqiy Telegram yetkazishi — jonli token bilan"
    expected: "notify.outbox_tick real token bilan bir marta yuguradi; direktor va sotuvchi chatiga xabar HAQIQATAN yetib keladi; notification_outbox qatorlari `delivered` bo'ladi, provider_message_id nol emas"
    why_human: "CI'da bot tokeni yo'q va bo'lmaydi ham; respx faqat tarmoq chegarasini tutadi — 'so'rov to'g'ri shakllandi' o'lchanadi, 'Telegram uni qabul qildi' emas (07-RESEARCH.md § Environment Availability)"
  - test: "'Yetkazildi' so'zining sotuvchi/direktor uchun ma'nosi"
    expected: "direktor GET /reconciliation/delivery holat matnini o'qib, 'tizim Telegramga topshirdi' va 'siz o'qidingiz' ikki BOSHQA fakt ekanini sotuvchiga tushuntira oladi"
    why_human: "Telegram Bot API yetkazilganlik kvitansiyasi bermaydi — sendMessage faqat Message qaytaradi (07-RESEARCH.md Key Finding 4)"
  - test: "Bot matnlarining sotuvchi uchun tushunarliligi"
    expected: "5 sotuvchiga bot ekrani (bog'lanish, qoldiq, tarix, kvitansiya, eslatma) ko'rsatiladi; qaysi so'z tushunilmagani nomma-nom yoziladi"
    why_human: "Glossariy parity mexanik o'lchangan (G7-9), lekin o'qish savodxonligi past sotuvchi uchun idrok savoli — lug'at emas"
  - test: "request_contact tugmasining haqiqiy klientlardagi xulqi (iOS/Android/Desktop)"
    expected: "request_contact bosilganda Contact.user_id sender bilan teng bo'lib bog'lanish hosil bo'ladi; boshqa odam kontakti qo'lda ulashilganda rad etiladi"
    why_human: "bot-tests MockedBot bilan ishlaydi — Contact obyektini test o'zi yasaydi; D-24 ning uch qo'riqchisi TAXMINGA (MEDIUM-HIGH ishonch) tayanadi"
  - test: "Deploy bandi — cron jadvali import paytida olinadi"
    expected: "docker compose up -d --force-recreate scheduler worker bot-service dan keyin system_heartbeats da beshala komponent last_seen_at yangilanadi"
    why_human: "jarayon holati, kod emas — qayta ishga tushirilmagan planer yangi vazifalarni hech qanday xatosiz ko'rmay qoladi"
  - test: "Bir tokenga bitta poller (dev/prod ajratish)"
    expected: "prod tokeni faqat VPS'da, dev alohida bot/token bilan; ikkinchi nusxa ishga tushirilsa prod bot jim bo'lib qolishi kuzatiladi"
    why_human: "nosozlik ikki mashina orasida tug'iladi va bitta muhitda ifodalanmaydi (Telegram getUpdates bitta tokenga bitta klient beradi)"
  - test: "Quiet hours (21:00-08:00) va overdue_days=3 standartlarining buyurtmachi bilan tasdig'i"
    expected: "Karmana ma'muriyati bilan ikki savol hal qilinadi: qarz necha kundan 'kechikkan', xabar soat nechagacha maqbul"
    why_human: "ikkalasi ham [ASSUMED] qaror va buyurtmachi bilan hali tasdiqlanmagan; RAQAMLARNING O'ZI taxmin (mexanika to'g'ri ishlaydi)"
---

# Phase 7: Nomuvofiqlik, bildirishnoma va botlar — Verification Report

**Phase Goal:** «Band, lekin to'lovsiz» raqamdan jarayonga aylanadi va har rol o'z xabarini o'z vaqtida oladi
**Verified:** 2026-08-12
**Status:** gaps_found
**Re-verification:** Yo'q — birinchi tekshiruv

## Metodologiya haqida eslatma

Bu tekshiruv `07-REVIEW.md`/`07-REVIEW-backend.md`/`07-REVIEW-frontend.md` da
topilgan 9 blokerni **qayta hosil qilmadi** — ular allaqachon boshqa agent
tomonidan topilgan. Mening ishim boshqa edi: **har bir bloker ROADMAP'ning 5
muvaffaqiyat mezoniga qanday ta'sir qilishini** kod ustida **mustaqil**
tasdiqlash. Har bir quyidagi da'vo SUMMARY.md yoki REVIEW.md ning so'ziga
ishonmasdan, to'g'ridan-to'g'ri fayl:qator darajasida o'qilgan kod bilan
tekshirildi (pastdagi jadvallarda ko'rsatilgan). To'qqizala blokerning
HAMMASI ushbu tekshiruv davomida **qayta, mustaqil ravishda** tasdiqlandi —
birortasi faqat REVIEW.md ning so'ziga tayanib qabul qilinmadi.

**Confirmation-bias qarshi o'tkazilgan disконfirmatsiya o'tishi (majburiy
band):**
1. **Qisman bajarilgan talab:** RECON-02 — server holat mashinasi ishlaydi,
   lekin "mas'ul... yoziladi" bandi ishlamaydi (pastda batafsil).
2. **Yashil, lekin da'voni sinamaydigan test:** `test_sc3_...` — SC#3 ni
   YASHIL qiladi, lekin `seed_notification_settings()` ni fixture ichida
   to'g'ridan-to'g'ri chaqiradi (`test_phase7_criteria.py:987-989`), ya'ni
   mahsulotning HAQIQIY yozuv yo'lini emas, uning YO'QLIGINI yashiradi.
3. **Qamrovsiz xato yo'li:** `case-detail-dialog.tsx` da `errorView === null`
   holati (tarmoq xatosi, 422 massiv, 429/5xx, `market_not_selected`) —
   birorta test bu chaqiruvchi tomonda "noma'lum xato `errors.generic`
   chizadi" da'vosini tekshirmaydi, va kod haqiqatda buni bajarmaydi.

## Goal Achievement — har mezon bo'yicha MET / PARTIALLY MET / NOT MET

### Mezon #1 — MET

> "Kunlik nomuvofiqlik hisoboti «band, lekin to'lovsiz» rastalar va «ro'yxatga
> olinmagan savdo» anomaliyalarini rasm-dalil havolalari bilan ko'rsatadi"

**Dalil:**
- `GET /api/v1/reconciliation/report` (`services/core-api/app/api/v1/reconciliation.py:269-320`)
  ikkala sinfni (`occupied_unpaid`, `anomaly`) BIRGA, lekin sanoqlari
  ALOHIDA qaytaradi; har qatorda `evidence_snapshot_ids` (UUID) bor.
- `_all_cases_of_day()` (`reconciliation.py:393-423`) hisobotni
  `REPORT_PAGE_BUDGET=100` sahifagacha SERVER TOMONIDA to'liq yig'adi — bu
  case navbatining 50-qatorli qirqilishidan (Mezon #2 muammosi) **mustaqil**:
  hisobot HAR DOIM kunning to'liq to'plamini qaytaradi.
- Frontend surfaces (`unpaid-list.tsx:66`, `unregistered-list.tsx:63`)
  `useReconciliationReport(day)` orqali serverning to'liq javobini
  `.slice()` siz chizadi — mustaqil tekshirildi, klient darajasida qirqish
  YO'Q.
- `test_sc1_report_shows_both_classes_with_evidence_links`
  (`tests/integration/test_phase7_criteria.py:693-807`) mahsulot yo'lini
  (`reconciliation_open` job, HTTP orqali) yuritadi — seed bilan case
  yozilmagan; javobda kadr bayti/havola yo'qligi (`FORBIDDEN_EVIDENCE_MARKERS`)
  va shaxsiy maydonlarning yo'qligi (`PERSONAL_FIELDS`) ham tasdiqlanadi.

**Ogohlantirish (mezonni bekor qilmaydi, lekin bog'liq):** backend review
WR-09 — `_open_unpaid_cases()` da pastki vaqt chegarasi yo'q, ya'ni juda
eski to'lanmagan hisoblar ham case ochadi, lekin ular O'ZINING eski
`service_date` kunida — bugungi hisobotda emas. Bu case-navbat
to'liqligiga (Mezon #2) tegishli, kunlik hisobotning O'ZI to'g'ri.

### Mezon #2 — PARTIALLY MET

> "Har nomuvofiqlik case sifatida yuritiladi — mas'ul, holat
> (yangi/ko'rilmoqda/asosli/asossiz) va yechim yoziladi; hit-rate metrikasi
> hisoblanadi"

**Ishlaydigan qism (mustaqil tasdiqlandi):**
- `test_sc2_case_is_managed_and_hit_rate_is_derived`
  (`test_phase7_criteria.py:815-939`) `PATCH /cases/{id}` orqali
  `new→in_review→justified` va `new→unjustified` o'tishlarini HTTP orqali
  yuritadi; `reconciliation_case_events` ga ikki qator yoziladi
  (`_COUNT_CASE_EVENTS` bilan bazadan tasdiqlangan); `GET /hit-rate` HAR
  SO'ROVDA case holatlaridan hosila hisoblanadi (`justified=1,
  unjustified=1, open_cases=1, hit_rate=0.5`), o'lchov yo'q oraliqda `null`
  (`0.0` emas).
- `status` maydoni yopiq to'rt a'zoli enum — `"other"` HTTP darajasida
  `422` oladi (test bilan tasdiqlangan).

**Ishlamaydigan qism (kodda mustaqil tasdiqlandi):**
- **Mas'ul (assignee) yozilmaydi.** Frontend `assigneeUserId` ni to'g'ri
  yuboradi (`frontend/src/lib/reconciliation-queries.ts:625-634`), lekin
  marshrut (`services/core-api/app/api/v1/reconciliation.py:657-665`) uni
  `reconciliation_repo.transition()` ga UMUMAN uzatmaydi. SQL
  (`reconciliation_repo.py:877`): `assignee_user_id = COALESCE(:actor_user_id,
  assignee_user_id)` — ya'ni case har doim **o'tishni qilgan odamga**
  biriktiriladi, direktorning tanlovi jimgina yo'qoladi. `<option
  value="">Biriktirilmagan</option>` amalda ishlamaydigan amalni va'da
  qiladi. Bugun bu maydon backendda o'qilmagani uchun begona-bozor
  tenancy teshigi **UYQUDA** (aktiv emas — hech kim uni ishlatmaydi), lekin
  kelajakda "maydonni ulash" `user_market_roles` tekshiruvisiz qilinsa,
  darhol OCHILADI.
- **Navbat 50 qatorda jimgina qirqiladi.** `CASE_PAGE_SIZE=50`
  (`reconciliation-queries.ts:82`) frontendning HECH BIR faylida
  ishlatilmaydi (mustaqil `grep` bilan tekshirildi — 0 iste'molchi).
  `case-list.tsx:104` `useReconciliationCases(day, "")` — cursor doim
  qat'iy bo'sh satr. 300-1000 rastali Karmana bozorida bir kunda 50 dan
  ortiq case ochilsa (masalan ko'p rastada bir vaqtda to'lov kechikishi),
  qolganlari DOM'da UMUMAN yo'q va ularga yetadigan boshqaruv ham yo'q —
  jim ma'lumot yo'qotish.
- **Ikkinchi ketma-ket qaror jim tashlanadi.** `case-detail-dialog.tsx:349-350`
  qulfni `detail.case_id` bilan kalitlaydi (QARORNING o'zi bilan emas):
  `if (submittedRef.current === detail.case_id) return;`. Dialog
  muvaffaqiyatdan keyin YOPILMAYDI (`case-list.tsx` faqat `onOpenChange(false)`
  da tozalaydi), ya'ni `new→in_review` dan keyin bir dialogda
  `in_review→justified` bosilsa — so'rov UMUMAN ketmaydi, xato ham yo'q.
- **Saqlash xatosi matnsiz o'tadi.** `case-detail-dialog.tsx:426-434`:
  `errorView === null ? null : (...)`. `reconErrorView()` faqat 5 kodni
  biladi; qolgan HAMMASI (`NetworkError`, `422` massiv detail, `429`,
  `5xx`, `market_not_selected`) `null` beradi va HECH NARSA chizilmaydi —
  muvaffaqiyat bilan farqlanmaydi.

**Xulosa:** case'ning holat mashinasi va hit-rate hisob-kitobi mustahkam,
lekin "mas'ul... yoziladi" bandi amalda ishlamaydi va case navbatini
BOSHQARISH ekranining o'zi (aynan Karmana miqyosida, 300-1000 rasta) uchta
mustaqil nuqtada jim buziladi. Bu **backend-frontend chegarasidagi**
nuqson sinfi — ikkala tomon ham alohida to'g'ri ko'rinadi.

### Mezon #3 — NOT MET

> "Direktor ertalab dayjest (kechagi tushum, bandlik %, TOP-10 qarzdor) va
> kechqurun nomuvofiqlik xabarini Telegramda oladi; har rol bosh ekranida
> o'ziga mos bitta asosiy raqamni ko'radi"

Bu mezon ikki bandga bo'linadi va ular MUSTAQIL tekshirildi:

**(a) Direktor dayjest — NOT MET, produksiyada ishlamaydi.**

Mustaqil tekshiruv (REVIEW.md ning da'vosini takrorlamasdan, o'zim kod
ustida yurdim):

1. `grep -rn "market_notification_settings" services/ migrations/ packages/`
   — **BIRORTA** `INSERT`/`UPDATE` yo'q. Migratsiya (`0023`) faqat jadval
   yaratadi (`migrations/versions/0023_notification_domain.py:529-568`).
   Barcha boshqa uchrashuvlar — `SELECT` (o'qish) yoki hujjat izohi.
2. `services/bot-service/app/handlers/` — faqat `binding.py`, `start.py`,
   `vendor.py`. Direktor uchun bog'lash handleri UMUMAN yo'q.
3. `resolve_chat_id()` (`outbox_repo.py:553-592`) `recipient_kind !=
   vendor` bo'lganda `_RESOLVE_DIRECTOR_CHAT` (SELECT) chaqiradi — qator
   yo'qligi sabab har doim `None` qaytaradi.
4. `_settle()` (`services/core-api/app/jobs/outbox.py:1143-1213`) da:
   ```python
   if disposition is OutboxDisposition.RETRY and claim.attempt_count >= MAX_ATTEMPTS:
       disposition = OutboxDisposition.FAILED
   ```
   Bu tekshiruv **faqat `RETRY`** ga tegishli. `UNRESOLVED` (manzil
   topilmagani) shoxi bu shartdan **chetlab o'tadi** va har doim
   `reschedule(now + 900s)` bilan tugaydi (1185-1192-qatorlar) — hech
   qachon terminal holatga o'tmaydi.
5. `_CLAIM_DUE` (`outbox_repo.py:252-282`) `ORDER BY o.created_at, o.id`
   (eng eskisi birinchi) va `OUTBOX_BATCH_SIZE=500`
   (`outbox.py:193`) — ya'ni bu o'lik dayjest qatorlari vaqt o'tishi bilan
   navbatning ENG ESKI qismini egallab, boshqa (jumladan CASH-05
   kvitansiya) qatorlarini siqib chiqarish xavfini tug'diradi.

`test_sc3_director_gets_two_messages_and_every_role_gets_one_number`
(`test_phase7_criteria.py:986-989`) buni **ustidan chetlab o'tadi**:
```python
seed_notification_settings(
    sync_owner_conn, market_id=env.market_id, director_chat_id=DIRECTOR_CHAT
)
```
`tests/fixtures/notification_domain.py:508-527` bu funksiyaning o'zi
ochiq yozadi: *"bu seed HECH QAYERDA avtomatik chaqirilmaydi — uni faqat
'sozlama BOR' shoxini o'lchayotgan test chaqiradi"*. Ya'ni test HALOL —
u chaqqan HTTP so'rovni to'g'ri o'lchaydi (`respx` orqali) — lekin
o'lchagan sharoiti (sozlama qatori mavjud) produksiyada **hech qachon**
yuzaga kelmaydi. Bu **darvozaning nuqsoni emas, qamrovining chegarasi** —
ammo natija bir xil: **haqiqiy Karmana bozorida direktor birorta dayjest
olmaydi, hech qachon**, chunki hech kim `director_chat_id` ni yoza olmaydi.

Kuzatuv teshigi ham qo'shimcha: `WR-10` (backend review) —
`digest_morning` va `digest_evening` BITTA `notify_digest` heartbeat
qatorini yangilaydi, ya'ni ertalabki dayjest butunlay o'lsa ham
kechqurungisi qatorni yangilab, `alert_sweep` hech qanday `digest_stale`
signalini bermaydi. Bu B-1 bilan birlashganda: dayjest **hech qachon
yetib bormaydi VA bu haqda hech qanday avtomatik ogohlantirish ham
kelmaydi**.

**(b) Har rol bosh ekranida bitta raqam — MET.**

`test_sc3` ning (b) qismi (`test_phase7_criteria.py:1044-1096`)
`GET /api/v1/me/headline` ni uch rol (direktor/kassir/nazoratchi) bilan
mustaqil chaqiradi: javob maydonlari to'plami AYNAN `{"metric","value"}`
(faqat `len==2` emas), uch rol uch XIL `metric` oladi, kassirning qiymati
SANOQ (`1`) — kunlik summaga (`15 000`) TENG EMAS. Bu band `director_chat_id`
muammosidan **mustaqil** — alohida marshrut, alohida ma'lumot manbai.

**Xulosa:** mezonning birinchi, og'irroq va murakkabroq yarmi (Telegram
dayjest) bugun produksiyada **strukturaviy jihatdan imkonsiz** — B-1 ni
tuzatmasdan bu o'zgarmaydi. Ikkinchi yarim (headline) to'liq ishlaydi.
Kritik kirish (`<critical_input_read_this_first>`) da so'ralganidek —
green test HAQIQATNI aks ettirmaydi va mezon **NOT MET** deb belgilanadi.

### Mezon #4 — MET (server yarmi); haqiqiy Telegram xulqi — inson tekshiruvi kerak

> "Sotuvchi contact ulashish orqali botga ulanadi (telefon raqami admin
> reestriga mos bo'lsa) va o'z qoldig'i/qarzi hamda to'lov tarixini
> ko'radi"

**Dalil (server yarmi, `core-api` image'ida):**
- `test_sc4_vendor_binds_and_sees_own_debt_and_history`
  (`test_phase7_criteria.py:1119-1291`) uch da'voni mustaqil isbotlaydi:
  (1) `POST /internal/bot/resolve` telefon reestrga YAGONA mos kelganda
  bog'laydi, sessiya/cookie yaratmaydi; (2) qoldiq
  `billing_repo.vendor_outstanding()` bilan **teng** (`==`), tarix
  `vendor_charge_allocation()` dan hosila — botda IKKINCHI arifmetika
  yo'q; (3) ikki bozorda bir xil telefon → `multiple_matches`,
  `vendor_telegram_bindings` da 0 qator (D-26b).
- Server javobida `PERSONAL_FIELDS` (`vendor_name`, `phone`, `full_name`)
  yo'qligi ham tasdiqlangan.

**Dalil (bot yarmi, ALOHIDA konteynerda):**
- `services/bot-service/app/handlers/binding.py:99-113` uch D-24
  qo'riqchisini to'g'ridan-to'g'ri kod o'qish bilan tasdiqladim:
  `message.chat.type != ChatType.PRIVATE`, `contact is None`,
  `contact.user_id is None`, `contact.user_id != message.from_user.id` —
  to'rttasi ham OR zanjirida, birortasi bo'lsa rad etiladi.
- Bu handler `services/bot-service/tests/unit/test_binding.py` bilan
  ALOHIDA konteynerda (`bot-tests`) sinaladi va `npm run bot:test` orqali
  `npm run gate` zanjiriga ULANGAN — ya'ni bu ikkinchi yarim ham HAR
  DARVOZADA o'lchanadi, faqat boshqa jarayonda.
- **Chegara sababi mustaqil tasdiqlandi:** `services/core-api/app` va
  `services/bot-service/app` ikkalasi ham `app` nomli top-level paket
  (`ls` bilan tekshirildi) — ikkinchisining importi birinchisini soya
  qiladi, ya'ni bitta pytest jarayonida ikkalasini birga yugurtirib
  bo'lmaydi. Bu haqiqiy texnik cheklov, qamrov bo'shlig'i emas.

**Inson tekshiruvi kerak:** `request_contact` tugmasining HAQIQIY
Telegram klientlarida (iOS/Android/Desktop) xulqi — `bot-tests`
`MockedBot` bilan ishlaydi, ya'ni `Contact` obyektini test o'zi yasaydi.
Tadqiqot buni faqat MEDIUM-HIGH ishonch bilan yozgan (`07-HUMAN-UAT.md`
#4). Bu **kod bo'shlig'i emas**, tabiiy chegara.

### Mezon #5 — PARTIALLY MET

> "To'lov kiritilishi bilan sotuvchiga zudlik push-kvitansiya boradi
> (summa, rasta, kassir, vaqt) va qarz N kundan oshsa avtomatik eslatma
> keladi — barcha xabarlar outbox orqali, throttling va quiet hours
> hurmat qilinib, yetkazilganlik holati bilan"

**Ishlaydigan qism (mustaqil tasdiqlandi):**
- `test_sc5_receipt_is_immediate_and_overdue_reminder_respects_settings`
  (`test_phase7_criteria.py:1299-1447`): to'lov → kvitansiya niyati BIR
  TRANZAKSIYADA yoziladi, takror `POST` ikkinchi qator bermaydi
  (`dedupe_key` bilan tasdiqlangan); ikki bozorda IKKI XIL `overdue_days`
  (3 vs 90) BIR XIL 30 kunlik qarzga IKKI XIL natija beradi; quiet oynada
  (22:30) kvitansiya O'TADI, eslatma esa navbatdan UMUMAN olib
  tashlanadi (`attempt_count == 0`).
- `403 → BLOCKED` xulqi mustaqil tasdiqlandi
  (`services/core-api/app/jobs/outbox.py:232-233,392-393` — qayta
  urinishsiz, D-22 bilan mos).
- **Muhim aniqlik:** B-1 (`market_notification_settings` yozuv yo'qligi)
  bu mezonga **TA'SIR QILMAYDI** — vendor (sotuvchi) chatlari
  `vendor_telegram_bindings` dan keladi (`_RESOLVE_VENDOR_CHAT`,
  `outbox_repo.py:585-587`), bu jadvalning HAQIQIY yozuv yo'li bor
  (`POST /internal/bot/resolve` → bot-service `on_contact`). `overdue_days`
  esa `COALESCE(..., DEFAULT_OVERDUE_DAYS)` bilan sozlama qatorisiz ham
  ishlaydi (`notifications.py:635-637`) — faqat bozor-kesimidagi
  QIYMATNI sozlash imkoniyati yo'q (BOT-03 ning "N sozlanadigan" bandi
  bugun faqat SQL bilan mumkin, admin UI bilan emas — WARNING, blocker
  emas).

**Ishlamaydigan qism (kodda mustaqil tasdiqlandi):**
- **Tik vaqt byudjetini o'lchamaydi.** `OUTBOX_TICK_BUDGET_SECONDS=20`
  (`outbox.py:184`) faqat `OUTBOX_BATCH_SIZE` hisoblashda ishlatiladi
  (193-qator); `outbox_tick()` ning `for market_id in market_ids:`
  tsiklida (939-943-qatorlar) deadline tekshiruvi YO'Q. 7+ to'la navbatli
  bozorda tik `OUTBOX_LEASE_SECONDS=120` dan oshadi → muddati o'tgan
  ijara → `release_expired_leases()` qatorni `pending` ga qaytaradi →
  **bir xil kvitansiya ikki marta yuboriladi** (`dedupe_key` buni
  ushlamaydi — u faqat `enqueue` bosqichida ishlaydi, jo'natishda emas).
  Karmana yagona-bozor piloti uchun bu shart (7+ bozor) DARHOL
  yuzaga kelmaydi, lekin bu ko'p-bozor SaaS platformasining o'z
  arxitekturasi va'dasiga (`CLAUDE.md`: "bitta kod bazasi, cheksiz
  bozor") to'g'ridan-to'g'ri zid.
- **`attempt_count` haqiqiy urinishsiz ham oshadi.** `_CLAIM_DUE`
  (`outbox_repo.py:284-288`) `attempt_count = o.attempt_count + 1` ni
  SHARTSIZ bajaradi — hatto `UNRESOLVED` (HTTP so'rovi yuborilmagan)
  holatda ham. `_settle()` ning docstringi (`outbox.py:1155-1160`) buni
  ochiq TAQIQLAGAN: *"BYUDJET FAQAT HAQIQIY URINISHGA QO'LLANADI"*. Amalda
  botga 3 kundan keyin ulangan sotuvchi ~288 marta hisoblangan holda
  birinchi HAQIQIY urinishga yetadi; birinchi vaqtinchalik `502` da
  `288 >= MAX_ATTEMPTS(5)` — darhol `failed`, qayta urinishsiz. Bu
  senariy Karmana pilotida REAL: barcha sotuvchilar birinchi kunda botga
  ulanmaydi.
- **Yetkazilganlik ro'yxati 50 qatorda qirqiladi.**
  `DELIVERY_PAGE_SIZE=50` (`outbox_repo.py:883`),
  `delivery-list.tsx` da cursor iste'moli yo'q (mustaqil tekshirildi —
  komponentda `cursor` so'zi umuman yo'q).

**Xulosa:** "kiritilishi bilan... boradi" va'dasi to'g'ri yozadigan
yo'lda (happy path, quiet-hours, ikki-bozorli farqlash) mustahkam
tasdiqlangan. Lekin ikkita mustaqil, kodga tayangan nuqson ("boradi"
so'zining o'zini) real, oldindan bashorat qilinadigan senariylarda
(kech ulangan sotuvchi, ko'p bozorli tik) buzadi. BOT-04 ning
"throttling" (per-chat 1 msg/s) qismi to'g'ri ishlaydi — nuqson
byudjet/ijara ARIFMETIKASIDA, throttling mexanizmining o'zida emas.

## Requirements Coverage

| Requirement | Tavsif (REQUIREMENTS.md) | Holat | Dalil |
| --- | --- | --- | --- |
| RECON-01 | Kunlik hisobot: ikkala sinf + dalil havolalari | ✓ SATISFIED | Mezon #1 |
| RECON-02 | Case: mas'ul, holat, yechim, hit-rate | ~ PARTIAL | Mezon #2 — holat/hit-rate ishlaydi, mas'ul yo'q, navbat UI 3 joyda buzuq |
| RECON-03 | Direktor ertalab/kechqurun dayjest | ✗ BLOCKED | Mezon #3(a) — produksiyada yetkazib bo'lmaydi |
| RECON-06 | Har rolga bitta ko'rsatkich | ✓ SATISFIED | Mezon #3(b) |
| CASH-05 | To'lov → zudlik push-kvitansiya | ~ PARTIAL | Mezon #5 — yozuv/idempotentlik to'g'ri, yetkazish ishonchliligi B-3/B-4 bilan buzilgan |
| BOT-01 | Contact orqali ulanish, reestrga moslik | ✓ SATISFIED (server) | Mezon #4 — bot yarmi inson tekshiruvi kutmoqda |
| BOT-02 | Qoldiq/qarz va to'lov tarixi | ✓ SATISFIED | Mezon #4 |
| BOT-03 | N kundan qarz eslatmasi, sozlanadigan N, quiet hours | ✓ SATISFIED (⚠ N faqat SQL bilan sozlanadi — admin UI yo'q, B-1 bilan bir ildiz) | Mezon #5 |
| BOT-04 | Outbox + throttling + yetkazilganlik + bloklangan foydalanuvchi | ~ PARTIAL | Mezon #5 — 403→blocked va per-chat throttling to'g'ri; attempt-byudjet va tik-byudjet buzuq; delivery UI qirqiladi |

**Yetim (orphan) talab:** yo'q — barcha 17 ta PLAN.md frontmatteridagi
`requirements:` maydonlari ROADMAP'ning 9 ta e'lon qilingan ID'siga
(RECON-01/02/03/06, CASH-05, BOT-01/02/03/04) mos keladi, ortiqcha yoki
yetishmagan ID topilmadi.

## Key Link Verification

| From | To | Via | Holat | Tafsilot |
| --- | --- | --- | --- | --- |
| `digest_morning`/`digest_evening` | `market_notification_settings.director_chat_id` | `resolve_chat_id()` → `_RESOLVE_DIRECTOR_CHAT` | ✗ NOT_WIRED | Yozuv yo'li yo'q, o'qish doim `None` |
| `case-detail-dialog.tsx` (assignee `<Select>`) | `reconciliation_cases.assignee_user_id` | `PATCH /cases/{id}` → `transition()` | ✗ NOT_WIRED | Frontend yuboradi, backend o'qimaydi/tashlaydi |
| `case-list.tsx`/`delivery-list.tsx` (`next_cursor`) | pagination state | `useReconciliationCases`/`useReconciliationDelivery` `cursor` argumenti | ✗ NOT_WIRED | Sxema parse qiladi, iste'molchi yo'q |
| `OUTBOX_TICK_BUDGET_SECONDS` | `outbox_tick()` tsikl deadline | `monotonic()` tekshiruvi | ✗ NOT_WIRED | Faqat `OUTBOX_BATCH_SIZE` arifmetikasida ishlatiladi |
| `bot-service` `on_contact` | `POST /internal/bot/resolve` | `CoreClient.resolve()` | ✓ WIRED | Uch D-24 qo'riqchisi bilan mustaqil tasdiqlandi |
| `POST /payments` | `notification_outbox` (PAYMENT_RECEIPT) | bir tranzaksiyadagi INSERT | ✓ WIRED | `dedupe_key` bilan idempotent, test_sc5 bilan tasdiqlangan |
| `vendor_telegram_bindings` | vendor chat manzili | `resolve_chat_id(recipient_kind=vendor)` | ✓ WIRED | B-1 dan mustaqil — alohida jadval, real yozuv yo'li bor |

## Anti-Patterns Found

| Fayl:qator | Naqsh | Darajasi | Ta'sir |
| --- | --- | --- | --- |
| `services/core-api/app/jobs/outbox.py:1162-1164` | Terminal-holat tekshiruvi faqat bitta shoxqa (`RETRY`) qo'llanadi, `UNRESOLVED` chetlab o'tadi | 🛑 Blocker | Mezon #3 — dayjest abadiy `pending` |
| `services/core-api/app/repositories/outbox_repo.py` | `market_notification_settings` ga yozuvchi funksiya UMUMAN yo'q | 🛑 Blocker | Mezon #3 |
| `services/core-api/app/api/v1/reconciliation.py:657-665` | Qabul qilingan payload maydoni (`assignee_user_id`) jimgina tashlanadi | 🛑 Blocker | Mezon #2 |
| `frontend/src/components/reconciliation/case-detail-dialog.tsx:426-434` | Xato xaritasida yo'q kod → hech narsa render qilinmaydi (va'da qilingan zaxira ishlamaydi) | 🛑 Blocker | Mezon #2 |
| `frontend/src/components/reconciliation/case-detail-dialog.tsx:349-350` | Qulf noto'g'ri kalit (case_id, qaror emas) bilan ikkinchi harakatni bloklaydi | 🛑 Blocker | Mezon #2 |
| `frontend/src/lib/reconciliation-queries.ts:82` | E'lon qilingan konstanta (`CASE_PAGE_SIZE`) 0 iste'molchi bilan — o'lik kod, silliq UI qirqilishi | 🛑 Blocker | Mezon #2, #5 |
| `services/core-api/app/jobs/outbox.py:184-193` | Hujjatlashtirilgan byudjet konstantasi hech qachon deadline sifatida tekshirilmaydi | 🛑 Blocker | Mezon #5 |
| `services/core-api/app/repositories/outbox_repo.py:284-288` | Hisoblagich (`attempt_count`) shartsiz oshiriladi, hujjat esa "faqat haqiqiy urinish" deb va'da qiladi | 🛑 Blocker | Mezon #5 |
| `package.json:7` | `npm run up` `bot-service` ni ko'tarmaydi, compose izohi teskarisini da'vo qiladi | ⚠️ Warning | Operatsion (dev muhiti), prod deploy jarayoniga bog'liq emas |
| `compose.yaml:720-721` | `bot-tests` prod token/servis-token'ni `:-` standart bilan meros oladi | ⚠️ Warning | Test infratuzilmasi xavfsizligi |
| `services/core-api/app/jobs/notifications.py:558-571` (WR-02, review) | Kechki dayjestning `anomaly_count` i strukturaviy jihatdan har doim `0` | ⚠️ Warning | Mezon #3 — B-1 tuzatilsa ham matn noto'g'ri bo'lib qoladi |
| `services/core-api/app/jobs/alerting.py` (WR-10, review) | Ikki mustaqil job (ertalab/kechqurun) bitta heartbeat komponentini bo'lishadi | ⚠️ Warning | Mezon #3 — dayjest o'lsa ham hech qanday avtomatik signal yo'q |
| `services/core-api/app/repositories/reconciliation_repo.py` (WR-09, review) | `_open_unpaid_cases()` da pastki vaqt chegarasi yo'q | ⚠️ Warning | Mezon #2 — eski case'lar kunlik navbatda ko'rinmaydi |

TBD/FIXME/XXX belgilarini qidirish (`grep -rn "TBD\|FIXME\|XXX"`) fazaning
o'zgargan fayllarida topilmadi — bu Blocker Gate'ga tegishli emas.

## Behavioral Spot-Checks / Probe Execution

**SKIPPED** — bu faza to'liq Docker Compose + real Postgres testcontainers
talab qiladigan backend/frontend/bot xizmatidan iborat; tezkor tekshiruv
talabiga ko'ra (`"Keep verification fast. Use grep/file checks, not
running the app"`) dinamik ijro (docker compose / pytest / vitest)
BAJARILMADI. Buning o'rniga yuqoridagi barcha da'volar **to'g'ridan-to'g'ri
kod o'qish** (fayl:qator darajasida, `grep` bilan nol-natija tasdiqlangan
holatlar bilan birga) orqali mustaqil tekshirildi — bu SUMMARY/REVIEW
so'ziga ishonishdan farqli, lekin haqiqiy test yugurishidan past ishonch
darajasi. Agar `docker compose --profile test run --rm tests pytest
tests/integration/test_phase7_criteria.py -q` ijro etilsa, SC#1/#2/#4(server)/
qisman #5 baribir YASHIL chiqadi — chunki testlar o'zlari HALOL (mahsulot
yo'lini yuritadi), faqat SC#3 va SC#5'ning muvaffaqiyati **fixture
seed'iga** tayanadi, produksiyaning haqiqiy yozuv yo'liga emas.

## Human Verification Required

Frontmatterdagi `human_verification` bilan bir xil to'plam (7 band,
`07-HUMAN-UAT.md` dan hosila — takrorlanmaydi). Eng muhim ikkitasi:

### 1. Haqiqiy Telegram yetkazishi

**Test:** `notify.outbox_tick` ni jonli bot tokeni bilan bir marta
yuritish (test bozori, test chatida).
**Kutilgan:** direktor va sotuvchi chatiga xabar HAQIQATAN yetib keladi;
`notification_outbox` qatorlari `delivered`, `provider_message_id` nolga
teng emas.
**Nega inson:** CI'da bot tokeni yo'q; `respx` faqat tarmoq chegarasini
tutadi.

### 2. `request_contact` real klient xulqi

**Test:** iOS, Android, Desktop klientlarida `request_contact` tugmasini
bosish va boshqa odam kontaktini qo'lda ulashishni sinash.
**Kutilgan:** o'z kontaktida bog'lanish hosil bo'ladi; begona kontaktda
rad etiladi.
**Nega inson:** `bot-tests` `MockedBot` bilan ishlaydi, `Contact` obyekti
sun'iy; D-24 taxminga (MEDIUM-HIGH ishonch) tayanadi.

(Qolgan 5 band — dayjest ma'nosi, matn tushunarliligi, deploy bandi, bitta
poller qoidasi, quiet-hours/overdue_days standartlarining tasdig'i —
frontmatterda to'liq yozilgan, `07-HUMAN-UAT.md` bilan bir xil.)

## Gaps Summary

To'qqizala blokerning (B-1...B-9, `07-REVIEW.md`) HAMMASI mustaqil
tasdiqlandi va ular uchta guruhga tushadi:

1. **B-1 (yagona haqiqiy BLOCKER darajasidagi struktura nuqsoni):**
   `market_notification_settings` ga yozuv yo'li yo'qligi Mezon #3'ning
   asosiy va'dasini (Telegramda dayjest) produksiyada TO'LIQ imkonsiz
   qiladi. Bu ROADMAP'ning o'z faza nomiga ("har rol o'z xabarini o'z
   vaqtida oladi") to'g'ridan-to'g'ri zid — 8-fazaga (hisobot/backup/go-live)
   qoldirib bo'lmaydigan, aynan shu faza qamroviga tegishli bo'shliq.

2. **B-2, B-5, B-6, B-7 (case boshqaruv yuzasi, Mezon #2):** to'rttasi ham
   bir-biridan mustaqil, lekin bitta umumiy oqibatga olib keladi — direktor
   case navbatini 300-1000 rastali bozorda **ishonchli boshqara olmaydi**:
   mas'ulni tanlay olmaydi, 50 dan ortiq case'ni ko'ra olmaydi, bitta
   o'tirishda ketma-ket ikki qaror qabul qila olmaydi, xatoni muvaffaqiyatdan
   ajrata olmaydi.

3. **B-3, B-4 (outbox ishonchliligi, Mezon #5):** happy path to'g'ri, lekin
   real vaqt (kech ulangan sotuvchi — B-4, ko'p bozorli tik — B-3)
   sharoitida kvitansiya "boradi" va'dasini buzadi. B-4 Karmana pilotida
   DARHOL yuzaga kelishi mumkin (sotuvchilar bir kunda ulanmaydi); B-3
   yagona-bozor pilotida darhol emas, lekin ko'p-bozor SaaS kengayishida
   muqarrar.

**8-fazaga qoldirish mumkin bo'lgan, lekin YASHIRIN QOLDIRILMASLIGI kerak
bo'lgan bandlar:** B-8 (`npm run up` bot-service'ni ko'tarmaydi — dev
qulayligi, prod deploy jarayoniga bog'liq emas) va B-9 (`bot-tests` token
merosi — test infratuzilmasi xavfsizligi). Bu ikkitasi ROADMAP'ning 5
mezonidan birortasini to'g'ridan-to'g'ri buzmaydi, lekin operatsion xavf
sifatida `deferred-items.md` ga ATAYIN va egasi bilan yozilishi shart —
hozircha `deferred-items.md` da qayd etilmagan (faqat 2 ta eski band bor:
#1 yopilgan, #2 8-fazaga tegishli va bu topilmalarga aloqasi yo'q).

**Deferred (8-fazaga mos keladigan):** yo'q. Phase 8'ning success
criteria (Excel eksport, AI aniqlik hisoboti, backup mashqi, go-live
runbook, 3-tomonlama solishtiruv) ushbu 9 blokerning birortasini
qamramaydi — hammasi Phase 7'ning o'z REQ-ID doirasida (RECON-02/03,
BOT-04) qoladi.

---

_Verified: 2026-08-12_
_Verifier: Claude (gsd-verifier)_
