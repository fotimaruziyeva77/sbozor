---
phase: 07-nomuvofiqlik-bildirishnoma-va-botlar
verified: 2026-08-13T12:00:00Z
status: human_needed
score: 5/5 ROADMAP muvaffaqiyat mezoni VERIFIED
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: "2/5 to'liq VERIFIED (qolgan 3 tasi qisman/NOT MET)"
  gaps_closed:
    - "Mezon #3(a) — market_notification_settings.director_chat_id ga YAGONA yozuv yo'li ochildi (binding_repo.bind_director(), POST /internal/bot/director/resolve) va test_sc3 endi shu HTTP yo'lini yuritib, natijani BAZADAN o'qib tasdiqlaydi (07-18)"
    - "Mezon #3(a) — outbox _settle() da UNRESOLVED shoxi endi UNRESOLVED_MAX_AGE_HOURS=72 bilan terminal holatga chiqadi — qator abadiy pending qolmaydi (07-19)"
    - "Mezon #2 — assignee_user_id endi marshrutdan transition() ga yetadi va user_market_roles ustidan begona-bozor tekshiruvi (422 assignee_not_in_market) bilan himoyalangan; COALESCE argument tartibi almashtirilib, holat o'zgarishi mavjud biriktirishni endi o'g'irlamaydi (07-20)"
    - "Mezon #2 — case-list.tsx/delivery-list.tsx endi next_cursor ni useInfiniteQuery bilan iste'mol qiladi — 50 qatorli jim qirqilish yo'q (07-22)"
    - "Mezon #2 — case-detail-dialog.tsx da ikkinchi ketma-ket HAQIQIY qaror endi serverga yetadi (dedupe bileti case_id:status juftligiga ko'chdi, onError->onSettled) (07-23)"
    - "Mezon #2 — saqlash xatosi endi HAR DOIM matn bilan ko'rinadi (shart errorView!==null dan update.isError ga o'zgardi, xaritada yo'q kod uchun errors.generic zaxira ishlaydi) (07-23)"
    - "Mezon #5 — outbox_tick() endi monotonic() deadline'ni HAR BOZORDAN va HAR QATORDAN oldin tekshiradi — ko'p-bozorli tikda takroriy yuborish strukturaviy imkonsiz (07-19)"
    - "Mezon #5 — attempt_count endi FAQAT uchta terminal bayonotda (_MARK_DELIVERED/_MARK_TERMINAL/_RESCHEDULE) oshadi, claim() va defer_unresolved() tegmaydi — kech ulangan sotuvchining urinish byudjeti yeyilmaydi (07-19)"
    - "Mezon #5 — delivery-list.tsx ham endi next_cursor ni iste'mol qiladi (07-22)"
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "Haqiqiy Telegram yetkazishi — jonli token bilan"
    expected: "notify.outbox_tick real token bilan bir marta yuguradi; direktor va sotuvchi chatiga xabar HAQIQATAN yetib keladi; notification_outbox qatorlari `delivered` bo'ladi, provider_message_id nol emas"
    why_human: "CI'da bot tokeni yo'q va bo'lmaydi ham; respx faqat tarmoq chegarasini tutadi — 'so'rov to'g'ri shakllandi' o'lchanadi, 'Telegram uni qabul qildi' emas (07-RESEARCH.md § Environment Availability)"
  - test: "'Yetkazildi' so'zining sotuvchi/direktor uchun ma'nosi"
    expected: "direktor GET /reconciliation/delivery holat matnini o'qib, 'tizim Telegramga topshirdi' va 'siz o'qidingiz' ikki BOSHQA fakt ekanini sotuvchiga tushuntira oladi"
    why_human: "Telegram Bot API yetkazilganlik kvitansiyasi bermaydi — sendMessage faqat Message qaytaradi (07-RESEARCH.md Key Finding 4)"
  - test: "Bot matnlarining sotuvchi uchun tushunarliligi"
    expected: "5 sotuvchiga bot ekrani (bog'lanish, qoldiq, tarix, kvitansiya, eslatma, endi direktor uchun ham bog'lanish javobi) ko'rsatiladi; qaysi so'z tushunilmagani nomma-nom yoziladi"
    why_human: "Glossariy parity mexanik o'lchangan (G7-9), lekin o'qish savodxonligi past sotuvchi uchun idrok savoli — lug'at emas"
  - test: "request_contact tugmasining haqiqiy klientlardagi xulqi (iOS/Android/Desktop) — endi direktor uchun ham"
    expected: "request_contact bosilganda Contact.user_id sender bilan teng bo'lib bog'lanish (sotuvchi YOKI direktor) hosil bo'ladi; boshqa odam kontakti qo'lda ulashilganda rad etiladi"
    why_human: "bot-tests MockedBot bilan ishlaydi — Contact obyektini test o'zi yasaydi; D-24 ning uch qo'riqchisi TAXMINGA (MEDIUM-HIGH ishonch) tayanadi"
  - test: "Deploy bandi — cron jadvali import paytida olinadi; bot-service endi npm run up bilan ko'tariladi"
    expected: "docker compose up -d --force-recreate scheduler worker bot-service dan keyin system_heartbeats da OLTITA komponent (notify_digest_morning/evening qo'shilgani bilan) last_seen_at yangilanadi"
    why_human: "jarayon holati, kod emas — qayta ishga tushirilmagan planer yangi vazifalarni hech qanday xatosiz ko'rmay qoladi; `npm run up` ning o'zi ijrochi worktree'da tarmoq yo'qligi sabab yugurtirilmagan (07-21 Issues Encountered #3)"
  - test: "Bir tokenga bitta poller (dev/prod ajratish)"
    expected: "prod tokeni faqat VPS'da, dev alohida bot/token bilan; ikkinchi nusxa ishga tushirilsa prod bot jim bo'lib qolishi kuzatiladi"
    why_human: "nosozlik ikki mashina orasida tug'iladi va bitta muhitda ifodalanmaydi (Telegram getUpdates bitta tokenga bitta klient beradi)"
  - test: "Quiet hours (21:00-08:00) va overdue_days=3 standartlarining buyurtmachi bilan tasdig'i"
    expected: "Karmana ma'muriyati bilan ikki savol hal qilinadi: qarz necha kundan 'kechikkan', xabar soat nechagacha maqbul"
    why_human: "ikkalasi ham [ASSUMED] qaror va buyurtmachi bilan hali tasdiqlanmagan; RAQAMLARNING O'ZI taxmin (mexanika to'g'ri ishlaydi). ⚠ N hamon FAQAT SQL bilan sozlanadi — admin UI yo'q (WARNING, Phase 8)"
---

# Phase 7: Nomuvofiqlik, bildirishnoma va botlar — Qayta tekshiruv hisoboti

**Phase Goal:** «Band, lekin to'lovsiz» raqamdan jarayonga aylanadi va har rol o'z xabarini o'z vaqtida oladi
**Verified:** 2026-08-13
**Status:** human_needed
**Re-verification:** Ha — 07-18…07-23 bo'shliqni yopish rejalari va orkestrator tuzatishi (`e32e40a`, `c477810`) HEAD `c477810` ga merge qilingandan keyin

## Metodologiya — bu qayta tekshiruv qanday o'tkazildi

Oldingi VERIFICATION.md (2026-08-12) 2/5 mezonni to'liq VERIFIED deb topgan va
uchta mezonni FAIL/PARTIAL qilgan edi. Bu safar HAR BIR da'vo **SUMMARY.md
so'ziga ishonmasdan**, to'g'ridan-to'g'ri kod o'qish bilan **mustaqil qayta**
tasdiqlandi — jumladan foydalanuvchi so'ragan nazorat buyrug'i:

```
grep -rn "market_notification_settings" services/ migrations/ packages/
```

**Natija — OLDINGI safar bilan solishtirilganda TUB FARQ bor.** Oldin
HAMMA uchrashuv `SELECT` yoki izoh edi. Hozir:

```
services/core-api/app/repositories/binding_repo.py:542:
    INSERT INTO market_notification_settings (market_id, director_chat_id)
         VALUES (:market_id, :chat_id)
    ON CONFLICT (market_id) DO UPDATE ...
```

Bitta, YAGONA `INSERT`/`UPSERT` — `binding_repo._BIND_DIRECTOR_CHAT`
(`services/core-api/app/repositories/binding_repo.py:540-552`), `bind_director()`
funksiyasi orqali chaqiriladi (`binding_repo.py:603-638`). Bu yo'l:

1. **Reachable by a real user, kodda:** `POST /internal/bot/director/resolve`
   (`services/core-api/app/api/internal/bot.py:362-405`) → `binding_repo.resolve_director()`
   (`binding_repo.py:641-715`, `Role.DIRECTOR` + `is_active` tekshiruvi bilan) →
   HAR mos bozor uchun `bind_director()`. Marshrut `services/core-api/app/main.py:420`
   da (`app.include_router(bot_internal_router)`) haqiqiy ilovaga ulangan —
   test-only qurilma emas.
2. **Bot tomonidan chaqiriladi:** `services/bot-service/app/handlers/binding.py:103-170`
   (`on_contact`) — sotuvchi reyestriga mos kelmasa, D-24 ning uch qo'riqchisidan
   (`message.chat.type != PRIVATE`, `contact is None`, `contact.user_id != from_user.id`)
   o'tgan HAQIQIY kontakt bilan `core.resolve_director()` chaqiradi
   (`services/bot-service/app/core_client.py:455-483`, `DIRECTOR_RESOLVE_PATH`).
3. **`test_sc3` endi shu yo'lni yuritadi, fixture'ni EMAS:** `tests/integration/test_phase7_criteria.py:1078-1097`
   `POST /internal/bot/director/resolve` ni HTTP orqali chaqiradi, javobni
   tekshiradi, SO'NGRA `market_notification_settings.director_chat_id` ni
   **bazadan** o'qib tasdiqlaydi (`sync_owner_conn.execute("SELECT
   director_chat_id FROM market_notification_settings ...")`). Fixture
   `seed_notification_settings()` esa `test_sc3` tanasida **0 marta** chaqiriladi
   — buni mustaqil `grep -n "def test_sc3" -A 250` bilan o'qib tasdiqladim.
   `tests/fixtures/notification_domain.py:519-533` ning o'z docstringi:
   *«bu seed HECH QAYERDA avtomatik chaqirilmaydi ... `test_sc3` endi o'sha
   marshrutga boradi va natijani BAZADAN o'qiydi; bu fixture esa `overdue_days`
   (D-19) shoxi uchun qoladi»*.

**Xulosa: mezon #3(a) endi kodda HAQIQIY, ishlaydigan, foydalanuvchi
bosishi mumkin bo'lgan yo'l bilan bajariladi.** Bu 07-18 dan oldin YO'Q edi.

## Goal Achievement — har mezon bo'yicha qayta hukm

### Mezon #1 — MET (o'zgarmadi, regressiya YO'Q)

> "Kunlik nomuvofiqlik hisoboti «band, lekin to'lovsiz» rastalar va «ro'yxatga
> olinmagan savdo» anomaliyalarini rasm-dalil havolalari bilan ko'rsatadi"

Bu mezon oldingi tekshiruvda ham MET edi va hech bir gap-rejasi
`GET /api/v1/reconciliation/report` yoki `_all_cases_of_day()` ga tegmadi.
**Regressiya nazorati:** `unpaid-list.tsx` 07-22 da klient pul arifmetikasini
o'chirish uchun tahrirlandi (WR-06) — `EvidenceLink`/`evidence_snapshot_ids`
render ikkala faylda ham (`unpaid-list.tsx:257`, `unregistered-list.tsx:181`)
**saqlanib qoldi**, mustaqil tekshirildi. Server tomoni
(`reconciliation.py:196` `REPORT_PAGE_BUDGET=100`, `:420,619`
`evidence_snapshot_ids=list(evidence.snapshot_ids)`) tegilmagan.

### Mezon #2 — ENDI MET (avval PARTIALLY MET)

> "Har nomuvofiqlik case sifatida yuritiladi — mas'ul, holat
> (yangi/ko'rilmoqda/asosli/asossiz) va yechim yoziladi; hit-rate metrikasi
> hisoblanadi"

To'rtta mustaqil nuqson (B-2, B-5, B-6, B-7) HAMMASI kodda mustaqil
tasdiqlandi — tuzatilgan holda:

1. **Mas'ul endi yoziladi (B-2).** `reconciliation.py:730-748`:
   `assignee_explicit = "assignee_user_id" in payload.model_fields_set`,
   so'ng `member_roles()` orqali begona-bozor tekshiruvi (`422
   assignee_not_in_market`, `_ASSIGNEE_NOT_IN_MARKET` konstantasi
   `reconciliation.py:161`), SO'NGRA `transition(..., assignee_user_id=assignee,
   assignee_explicit=assignee_explicit, ...)` chaqiriladi. SQL
   (`reconciliation_repo.py:929-931`):
   `assignee_user_id = CASE WHEN :assignee_explicit THEN :assignee_user_id ELSE
   COALESCE(assignee_user_id, :actor_user_id) END` — argumentlar TARTIBI
   almashtirilgan (mavjud ega SAQLANADI, aktor endi majburlanmaydi).
2. **Navbat 50 qatorda qirqilmaydi (B-6).** `frontend/src/lib/reconciliation-queries.ts:96,104`
   (`CASE_PAGE_SIZE`/`DELIVERY_PAGE_SIZE` — endi HAQIQIY iste'molchi bilan,
   `:580,672` `limit=` parametrida), `:535-587` `PagedQuery`/`useInfiniteQuery`.
   `case-list.tsx:244-263` — `[Yana yuklash]` tugmasi `cases.hasNextPage`
   bo'yicha chiziladi, `next_cursor === null` da UMUMAN yo'q.
3. **Ikkinchi ketma-ket qaror endi o'tadi (B-7).** `case-detail-dialog.tsx:388-410`:
   dedupe bileti endi `` `${detail.case_id}:${status}` `` (avval faqat
   `case_id`), `onError` → `onSettled` ga ko'chirilgan (muvaffaqiyatda ham
   bo'shaydi).
4. **Saqlash xatosi endi matnsiz o'tmaydi (B-5).** `case-detail-dialog.tsx:488`:
   shart `errorView !== null` dan `update.isError` ga o'zgargan; xaritada
   yo'q kod `t("errors.generic")` bilan chiziladi (`:493`).

Frontend locale fayllarida `assignee_not_in_market` uchala tilda (`sabab` +
`tuzatish` juft) mavjud: `frontend/messages/uz-Latn.json:1325,1332`,
`uz-Cyrl.json:1325,1332`, `ru.json:1325,1332`. Server ham buni `422`
(warning tone) bilan qaytaradi, `403` bilan emas — mustaqil tasdiqlandi.

**Qolgan, bloklamaydigan WARNING (o'zgarmagan, backend WR-09,
`deferred-items.md` 7a-band):** `_open_unpaid_cases()` da pastki vaqt
chegarasi yo'q — juda eski to'lanmagan hisoblar O'ZINING eski kunida case
ochadi, kunlik navbatda ko'rinmaydi. Bu funktsional TO'LIQLIKKA (juda eski
holatlar) tegishli, "case boshqariladimi" mezonining o'ziga emas — Phase 8
ga qoldirilgan, mustaqil ravishda ham hujjatda ochiq qoldi.

### Mezon #3 — ENDI MET (avval NOT MET)

> "Direktor ertalab dayjest (kechagi tushum, bandlik %, TOP-10 qarzdor) va
> kechqurun nomuvofiqlik xabarini Telegramda oladi; har rol bosh ekranida
> o'ziga mos bitta asosiy raqamni ko'radi"

**(a) Direktor dayjest — ENDI MET, produksiyada ishlaydi.**

Yuqoridagi "Metodologiya" bo'limida to'liq izlangan yozuv yo'lidan tashqari,
UNRESOLVED terminal chegarasi ham mustaqil tasdiqlandi:

- `services/core-api/app/jobs/outbox.py:239`: `UNRESOLVED_MAX_AGE_HOURS:
  Final[int] = 72`.
- `outbox.py:1382-1391` (`_settle()`): endi IKKI shart bor — `RETRY` uchun
  `attempt_count+1 >= MAX_ATTEMPTS` (o'zgarmadi) VA **yangi**
  `elif disposition is OutboxDisposition.UNRESOLVED and now - claim.created_at
  >= timedelta(hours=UNRESOLVED_MAX_AGE_HOURS): disposition =
  OutboxDisposition.FAILED`. Oldingi tekshiruvda bu `elif` shoxi UMUMAN yo'q
  edi — endi bor va u YOSHGA (yaratilgan vaqtga), URINISH SONIGA emas,
  tayanadi (chunki `UNRESOLVED` holatda urinish hisoblanmaydi — pastda).
- `test_sc3` (`test_phase7_criteria.py:1112-1124`): `respx` bilan
  Telegram'ga ketgan so'rovlarni ushlaydi va `route.call_count == 2` (aynan
  ikkita xabar — ertalab + kechqurun, direktorning chatiga) ni tasdiqlaydi.
  Bu HAQIQIY jo'natuvchi kodini (`AlertSender`) oxirigacha yuritadi.

**Kuzatuv teshigi ham yopilgan (WR-10, 07-21):** `notify_digest_morning` va
`notify_digest_evening` endi IKKI ALOHIDA heartbeat komponenti
(`services/core-api/app/api/internal/self_check.py`: `EXPECTED_COMPONENTS`
10 → 11), ya'ni ertalabki dayjest o'lib, kechkisi tirik qolsa ham
`digest_stale` ko'tariladi — avval bitta komponent bo'lgani uchun bu
KO'RINMAS edi.

**(b) Har rol bosh ekranida bitta raqam — MET (o'zgarmadi).**

`GET /me/headline` va uning testi (`test_phase7_criteria.py:1153-1190`)
gap-yopish rejalari tomonidan tegilmadi, mustaqil qayta o'qildi — hali ham
uch rol uch xil `metric`, javob shakli `{"metric","value"}` bilan qulflangan.

### Mezon #4 — MET (server yarmi, o'zgarmadi); haqiqiy Telegram xulqi — inson tekshiruvi

> "Sotuvchi contact ulashish orqali botga ulanadi (telefon raqami admin
> reestriga mos bo'lsa) va o'z qoldig'i/qarzi hamda to'lov tarixini
> ko'radi"

Bu mezonning ISHLASH mexanizmi (D-24 uch qo'riqchisi, `binding_repo.resolve()`,
`vendor/summary` — `billing_repo.vendor_outstanding()` orqali) hech bir
gap-rejasi tomonidan o'zgartirilmadi va mustaqil qayta tekshirildi —
`services/bot-service/app/handlers/binding.py:117-126` uch qo'riqchi
o'zgarmagan. 07-21 esa BOT-01 ga bog'liq ikkinchi darajali tuzatish
kiritdi: bot endi `404` javobini NOMLANGAN `detail == "not_bound"` bilan
o'qiydi (`core_client.py`, `_is_not_bound()`), ya'ni noto'g'ri
`CORE_API_URL` yoki proxy nosozligi endi soxta "siz bog'lanmagansiz"
xabarini bermaydi — bu ISHONCHLILIK yaxshilanishi, mezonning o'zi
o'zgarmadi.

**Inson tekshiruvi hamon kerak** (o'zgarmadi): `request_contact`
tugmasining HAQIQIY Telegram klientlarida (iOS/Android/Desktop) xulqi —
`bot-tests` `MockedBot` bilan ishlaydi.

### Mezon #5 — ENDI MET (avval PARTIALLY MET)

> "To'lov kiritilishi bilan sotuvchiga zudlik push-kvitansiya boradi
> (summa, rasta, kassir, vaqt) va qarz N kundan oshsa avtomatik eslatma
> keladi — barcha xabarlar outbox orqali, throttling va quiet hours
> hurmat qilinib, yetkazilganlik holati bilan"

Ikkita mustaqil, kodga tayangan nuqson (B-3, B-4) hamda delivery UI
qirqilishi HAMMASI mustaqil tasdiqlandi — tuzatilgan holda:

1. **Ikki marta yuborish endi strukturaviy imkonsiz (B-3).**
   `outbox.py:1070-1071`: `started = monotonic(); deadline = started +
   OUTBOX_TICK_BUDGET_SECONDS`. `:1084-1091` — HAR bozordan oldin
   `monotonic() >= deadline` tekshiriladi (`skipped_markets`,
   `budget_exhausted=True`). `:1100-1107` — HAR claim'dan oldin ham xuddi
   shu tekshiruv (`_settle()` chaqirilmaydi, ijara o'z-o'zidan bo'shaydi).
   Avval bu ikki tekshiruv UMUMAN yo'q edi.
2. **Kech ulangan sotuvchining byudjeti endi yeyilmaydi (B-4).**
   `outbox_repo.py:309-319` (`_CLAIM_DUE` ning `claimed` CTE'si) —
   `attempt_count` ga UMUMAN tegmaydi (faqat `SELECT`/`RETURNING`).
   Hisoblagich endi FAQAT uchta terminal bayonotda oshadi:
   `_MARK_DELIVERED` (`:689`), `_MARK_TERMINAL` (`:723`), `_RESCHEDULE`
   (`:756`) — hammasi `attempt_count = attempt_count + 1`. Yangi
   `_DEFER_UNRESOLVED` (`:782-800`) esa ATAYIN bu ustunga tegmaydi
   (`⛔ attempt_count OSHIRILMAYDI`). Ya'ni HTTP so'rovi umuman
   yuborilmagan (`UNRESOLVED`) holat endi byudjetni yemaydi.
3. **Yetkazilganlik ro'yxati endi 50 qatorda qirqilmaydi.**
   `delivery-list.tsx:276` `deliveries.fetchNextPage()` — 07-22 da
   `useReconciliationCases` bilan bir xil `useInfiniteQuery` naqshiga
   o'tkazilgan (`reconciliation-queries.ts:664-680`).

`403 → BLOCKED` (botni bloklagan foydalanuvchi belgilanishi, BOT-04 ning
oxirgi bandi) o'zgarmadi va mustaqil qayta tasdiqlandi
(`outbox.py:283,464-465,1397,1437` — qayta urinishsiz, bir marta).

**Qolgan, bloklamaydigan WARNING (o'zgarmagan):** `overdue_days` (BOT-03
ning "N sozlanadigan" bandi) hamon FAQAT to'g'ridan-to'g'ri SQL bilan
o'zgartiriladi — `grep -rn "overdue_days\|quiet_hours"
services/core-api/app/api/v1/*.py` **0 natija** berdi, ya'ni hech qanday
admin-yo'naltirilgan `/api/v1/*` marshruti bu ustunlarni yozmaydi. Mexanika
o'zi (COALESCE standart bilan, bozor-kesimida farqlanish) TO'G'RI ishlaydi
va `test_sc5` bilan tasdiqlangan — yo'q bo'lgani FAQAT admin UI, ma'lumot
yo'li emas. Bu Phase 8 ga tegishli, Phase 7 maqsadini bloklamaydi.

## Requirements Coverage

| Requirement | Tavsif (REQUIREMENTS.md) | Holat | Dalil |
| --- | --- | --- | --- |
| RECON-01 | Kunlik hisobot: ikkala sinf + dalil havolalari | ✓ SATISFIED | Mezon #1 (regressiyasiz) |
| RECON-02 | Case: mas'ul, holat, yechim, hit-rate | ✓ SATISFIED | Mezon #2 — 07-20 (mas'ul+tenancy), 07-22 (navbat), 07-23 (dedupe+xato) |
| RECON-03 | Direktor ertalab/kechqurun dayjest | ✓ SATISFIED | Mezon #3(a) — 07-18 (yozuv yo'li), 07-19 (terminal chegara), 07-21 (kuzatuv) |
| RECON-06 | Har rolga bitta ko'rsatkich | ✓ SATISFIED | Mezon #3(b), o'zgarmadi |
| CASH-05 | To'lov → zudlik push-kvitansiya | ✓ SATISFIED | Mezon #5 — yozuv/idempotentlik o'zgarmadi, yetkazish ishonchliligi 07-19/07-22 bilan tuzatildi |
| BOT-01 | Contact orqali ulanish, reestrga moslik | ✓ SATISFIED (server); bot yarmi inson tekshiruvi kutmoqda | Mezon #4 |
| BOT-02 | Qoldiq/qarz va to'lov tarixi | ✓ SATISFIED | Mezon #4, o'zgarmadi |
| BOT-03 | N kundan qarz eslatmasi, sozlanadigan N, quiet hours | ✓ SATISFIED (⚠ N faqat SQL bilan sozlanadi — admin UI yo'q, Phase 8) | Mezon #5 |
| BOT-04 | Outbox + throttling + yetkazilganlik + bloklangan foydalanuvchi | ✓ SATISFIED | Mezon #5 — 07-19 (byudjet+urinish), 07-22 (delivery UI) |

**Yetim (orphan) talab:** yo'q. 07-18…07-23 planlarining barcha
`requirements:` maydonlari (`RECON-01/02/03, CASH-05, BOT-01/04`)
ROADMAP'ning 9 ta e'lon qilingan ID to'plamiga (`RECON-01/02/03/06,
CASH-05, BOT-01/02/03/04`) mos keladi — mustaqil tekshirildi
(`.planning/phases/07-.../07-{18..23}-PLAN.md` frontmatter).

## Key Link Verification

| From | To | Via | Holat | Tafsilot |
| --- | --- | --- | --- | --- |
| `bot-service` `on_contact` (direktor shoxi) | `market_notification_settings.director_chat_id` | `core.resolve_director()` → `POST /internal/bot/director/resolve` → `binding_repo.bind_director()` UPSERT | ✓ WIRED (yangi, 07-18) | `binding_repo.py:540-638`, `bot.py:362-405`, `main.py:420`, `core_client.py:455-483` |
| `digest_morning`/`digest_evening` | Telegram (chiqqan so'rov) | `resolve_chat_id()` → `_RESOLVE_DIRECTOR_CHAT` (endi qator BOR) | ✓ WIRED (yangi) | `test_sc3` `route.call_count == 2` bilan tasdiqlangan |
| outbox `UNRESOLVED` qator | terminal `failed` holat | `_settle()` yosh tekshiruvi (`UNRESOLVED_MAX_AGE_HOURS`) | ✓ WIRED (yangi, 07-19) | `outbox.py:1385-1391` |
| `outbox_tick()` tsikli | `OUTBOX_TICK_BUDGET_SECONDS` deadline | `monotonic()` ikki nuqtali tekshiruv | ✓ WIRED (yangi, 07-19) | `outbox.py:1070-1071,1084-1091,1100-1107` |
| `case-detail-dialog.tsx` (assignee `<Select>`) | `reconciliation_cases.assignee_user_id` | `PATCH /cases/{id}` → `member_roles()` gate → `transition()` | ✓ WIRED (yangi, 07-20) | `reconciliation.py:730-748`, `reconciliation_repo.py:929-931` |
| `case-list.tsx`/`delivery-list.tsx` (`next_cursor`) | pagination state | `useInfiniteQuery` + `[Yana yuklash]` | ✓ WIRED (yangi, 07-22) | `reconciliation-queries.ts:575-587,668-679` |
| `case-detail-dialog.tsx` xato holati | ekran matni | `update.isError` sharti (avval `errorView!==null`) | ✓ WIRED (yangi, 07-23) | `case-detail-dialog.tsx:488-503` |
| `bot-service` `on_contact` (sotuvchi shoxi) | `POST /internal/bot/resolve` | `CoreClient.resolve()` | ✓ WIRED (o'zgarmadi) | oldingi tekshiruvda tasdiqlangan, qayta ko'rildi |
| `POST /payments` | `notification_outbox` (PAYMENT_RECEIPT) | bir tranzaksiyadagi INSERT | ✓ WIRED (o'zgarmadi) | `dedupe_key` bilan idempotent |
| `vendor_telegram_bindings` | vendor chat manzili | `resolve_chat_id(recipient_kind=vendor)` | ✓ WIRED (o'zgarmadi) | alohida jadval, B-1 dan mustaqil edi |

## Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| --- | --- | --- | --- | --- |
| `case-list.tsx` | `cases.data` (rows, `useInfiniteQuery`) | `GET /reconciliation/cases` → `reconciliation_repo.list_cases()` (real DB, keyset) | Ha | ✓ FLOWING |
| `delivery-list.tsx` | `deliveries.data` | `GET /reconciliation/delivery` → outbox delivery surface (real DB) | Ha | ✓ FLOWING |
| `hit-rate-card.tsx` | `cases.counts` (BIRINCHI sahifa) | Kun-kesimidagi server hisoblagichi (`reconciliation_repo`, filtrdan mustaqil — `reconciliation.py:485-487` docstringi bilan tasdiqlangan) | Ha | ✓ FLOWING |
| `case-detail-dialog.tsx` assignee `<Select>` | `useUsersQuery()` → `usersKey(marketId)` | `GET /users` (tenant-doiralangan, 07-23) | Ha | ✓ FLOWING |
| Direktor dayjest matni | `director_chat_id` | `market_notification_settings` ← `bind_director()` UPSERT ← `POST /internal/bot/director/resolve` | Ha | ✓ FLOWING (yangi) |

## Behavioral Spot-Checks / Probe Execution

**SKIPPED** (oldingi tekshiruvdagi bilan bir xil sabab) — bu faza to'liq
Docker Compose + real Postgres testcontainers talab qiladigan
backend/frontend/bot xizmatidan iborat va tezkor tekshiruv talabiga ko'ra
dinamik ijro (docker compose / pytest / vitest) bu agent tomonidan
BAJARILMADI.

⚠ **Farq oldingi safardan:** foydalanuvchi xabar berishicha, orkestrator
`npm run gate` (to'liq zanjir: `sim:up && lint && test && cv:lint && cv:test
&& bot:lint && bot:test && i18n:check && fe test && typecheck && lint &&
build`) ni HEAD `c477810` ustida yugurtirib **EXIT 0** olgan. Bu da'vo
**ikkinchi darajali dalil** sifatida qabul qilindi (o'z-o'zidan yetarli
emas — oldingi tekshiruvda aynan shunday "yashil, lekin noto'g'ri joyni
o'lchagan" test SC#3 ni yashirgan edi). Shu sababli bu tekshiruvning asosiy
dalili — yuqoridagi SQL/marshrut/handler zanjirining **to'g'ridan-to'g'ri
kod o'qish bilan** mustaqil tasdiqlanishi, `npm run gate` natijasi emas.
`test_sc3` ning o'zi HAM mustaqil o'qildi (`test_phase7_criteria.py:1016-1424`)
va u endi fixture emas, HAQIQIY HTTP yo'lini yuritib, natijani bazadan
o'qiydi — bu aynan oldingi FAIL sababini yopadi.

Qo'shimcha nazorat: `services/bot-service/tests/unit/test_binding.py:249-253`
o'qildi — `bot:lint` mypy xatosini yopgan `isinstance(item, SendMessage)`
toraytirish naqshi commit `e32e40a` da haqiqatan qo'llangan, `# type:
ignore` ISHLATILMAGAN (adashtiruvchi "tinchlantirish" emas).

## Requirements/Anti-Patterns — oldingi 9 blokerning holati

| # | Oldingi blokerning qisqacha nomi | Yangi holat | Dalil |
| --- | --- | --- | --- |
| B-1 | `market_notification_settings` yozuv yo'li yo'q + UNRESOLVED terminal chegara yo'q | ✓ TUZATILDI | Mezon #3(a), yuqorida |
| B-2 | `assignee_user_id` jimgina tashlanadi + tenancy teshigi | ✓ TUZATILDI | Mezon #2, `reconciliation.py:730-736` |
| B-3 | `outbox_tick` vaqt byudjetini o'lchamaydi → kvitansiya 2 marta | ✓ TUZATILDI | Mezon #5, `outbox.py:1070-1107` |
| B-4 | `attempt_count` `claim()` da oshadi | ✓ TUZATILDI | Mezon #5, `outbox_repo.py:309-319,689,723,756` |
| B-5 | Saqlash xatosi matnsiz o'tadi | ✓ TUZATILDI | Mezon #2, `case-detail-dialog.tsx:488` |
| B-6 | Navbat 50 qatorda jimgina qirqiladi | ✓ TUZATILDI | Mezon #2/#5, `reconciliation-queries.ts:575-679` |
| B-7 | Ikkinchi qaror jim tashlanadi | ✓ TUZATILDI | Mezon #2, `case-detail-dialog.tsx:388-410` |
| B-8 | `npm run up` botni ko'tarmaydi | ✓ TUZATILDI | `package.json:7` ga `bot-service` qo'shildi (07-21) |
| B-9 | `bot-tests` prod tokenini meros oladi | ✓ TUZATILDI | `compose.yaml` literal tokenlar (07-21) |
| — | (orkestrator) `bot:lint` mypy'da qizil edi | ✓ TUZATILDI | `test_binding.py:249-253`, commit `e32e40a` |

**TBD/FIXME/XXX qidiruvi** (`grep -nE "TBD|FIXME|XXX"`) 07-18…07-23
tomonidan o'zgartirilgan HAMMA ishlab chiqarish faylida (23 ta backend +
frontend fayl, testlar chetda) **0 natija** berdi — Debt marker gate
tegishli emas.

**Qolgan, bloklamaydigan WARNING'lar** (hammasi `deferred-items.md` da
egasi bilan, Phase 8 ga tegishli, ROADMAP'ning 5 mezonidan birortasini
BUZMAYDI):

| Fayl:qator | Naqsh | Darajasi | Nega bloklamaydi |
| --- | --- | --- | --- |
| `services/core-api/app/repositories/reconciliation_repo.py` (backend WR-09) | `_open_unpaid_cases()` da pastki vaqt chegarasi yo'q | ⚠️ Warning | Juda eski holatlar to'liqligiga tegishli, kunlik hisobotning o'zi to'g'ri (Mezon #1 tasdiqlangan) |
| `services/core-api/app/api/v1/*.py` | `overdue_days`/`quiet_hours` uchun admin marshrut yo'q | ⚠️ Warning | Mexanika COALESCE bilan to'g'ri ishlaydi; yo'q bo'lgani faqat sozlash UI'si |
| `packages/sbozor-core/sbozor_core/schema_contract.py:373` | `market_notification_settings` `AUDITED_TABLES`dan tashqarida (`id uuid` yo'q — texnik to'siq) | ⚠️ Warning | Ruxsat nazorati YOPIQ (faqat direktorning o'zi), yo'qolayotgani faqat TARIX |
| `/reconciliation` sahifasi | Sotuvchi ismi klientda `GET /vendors` birinchi sahifasi bilan cheklanadi | ⚠️ Warning | UI o'qilishi, case/hisobot MA'LUMOTINING o'zi to'g'ri |
| `services/core-api/app/jobs/alerting.py` | `digest_morning`/`digest_evening` bitta `digest_stale` kalitini bo'lishadi | ℹ️ Info | Ataylab qaror — qaysi dayjest o'lgani `/internal/self-check` da nomma-nom ko'rinadi |

## Human Verification Required

Frontmatterdagi `human_verification` bilan bir xil to'plam — 7 band,
`07-HUMAN-UAT.md` dan hosila, hech biri gap-yopish rejalari tomonidan
tegilmadi (barchasi qonuniy ravishda kod bilan tekshirib bo'lmaydigan
haqiqatlar: jonli Telegram, real klient xulqi, buyurtmachi tasdig'i).
Eng muhim ikkitasi:

### 1. Haqiqiy Telegram yetkazishi

**Test:** `notify.outbox_tick` ni jonli bot tokeni bilan bir marta
yuritish (test bozori, test chatida) — endi direktor dayjesti UCHUN ham.
**Kutilgan:** direktor va sotuvchi chatiga xabar HAQIQATAN yetib keladi;
`notification_outbox` qatorlari `delivered`, `provider_message_id` nolga
teng emas.
**Nega inson:** CI'da bot tokeni yo'q; `respx` faqat tarmoq chegarasini
tutadi.

### 2. `request_contact` real klient xulqi — endi direktor uchun ham

**Test:** iOS, Android, Desktop klientlarida `request_contact` tugmasini
bosish (sotuvchi VA direktor rolida) va boshqa odam kontaktini qo'lda
ulashishni sinash.
**Kutilgan:** o'z kontaktida bog'lanish hosil bo'ladi (sotuvchi bo'lsa
`bot.binding.ok`, direktor bo'lsa `bot.binding.director`); begona kontaktda
rad etiladi.
**Nega inson:** `bot-tests` `MockedBot` bilan ishlaydi, `Contact` obyekti
sun'iy; D-24 taxminga (MEDIUM-HIGH ishonch) tayanadi.

(Qolgan 5 band — dayjest ma'nosi, matn tushunarliligi, deploy bandi, bitta
poller qoidasi, quiet-hours/overdue_days standartlarining tasdig'i —
frontmatterda to'liq yozilgan.)

## Gaps Summary

**Gap yo'q.** Oldingi tekshiruvda FAIL/PARTIAL deb topilgan uchta mezon
(#2, #3, #5) endi kodda mustaqil VERIFIED — har biri file:line darajasida
qayta tasdiqlangan, SUMMARY.md so'ziga ishonilmagan. To'qqizala oldingi
bloker (B-1…B-9) va orkestrator tomonidan alohida yopilgan `bot:lint`
mypy xatosi — HAMMASI kodda TUZATILGAN holda topildi.

Qolgan WARNING-darajadagi bandlar (admin UI overdue_days uchun,
`market_notification_settings` audit bo'shlig'i, `_open_unpaid_cases()`
pastki vaqt chegarasi, `/reconciliation` sahifasidagi sotuvchi ismi
sahifalanishi, `digest_stale` kalitining bittaligi) — barchasi
`deferred-items.md` da egasi (Phase 8) bilan hujjatlashtirilgan, ROADMAP'ning
5 mezonidan birortasini to'g'ridan-to'g'ri buzmaydi va shu sababli GAP
emas, balki kelgusi faza uchun ochiq qoldirilgan operatsion/UX
takomillashtirish.

**Status `human_needed`, `passed` emas** — chunki 7 ta band faqat inson
(jonli Telegram, real klient, buyurtmachi tasdig'i) tomonidan
tekshirilishi mumkin va bular kod darajasida hal qilib bo'lmaydigan,
qonuniy UAT talablari, gap emas.

---

_Verified: 2026-08-13_
_Verifier: Claude (gsd-verifier), qayta tekshiruv_
