---
phase: 07-nomuvofiqlik-bildirishnoma-va-botlar
reviewed: 2026-08-12T00:00:00Z
depth: standard
files_reviewed: 26
files_reviewed_list:
  - migrations/entities/__init__.py
  - migrations/entities/functions.py
  - migrations/entities/triggers.py
  - migrations/versions/0023_notification_domain.py
  - packages/sbozor-core/sbozor_core/enums.py
  - packages/sbozor-core/sbozor_core/models/__init__.py
  - packages/sbozor-core/sbozor_core/models/notification.py
  - packages/sbozor-core/sbozor_core/schema_contract.py
  - services/core-api/app/api/internal/bot.py
  - services/core-api/app/api/internal/self_check.py
  - services/core-api/app/api/v1/me.py
  - services/core-api/app/api/v1/payments.py
  - services/core-api/app/api/v1/reconciliation.py
  - services/core-api/app/jobs/alerting.py
  - services/core-api/app/jobs/notification_meta.py
  - services/core-api/app/jobs/notifications.py
  - services/core-api/app/jobs/outbox.py
  - services/core-api/app/jobs/reconciliation.py
  - services/core-api/app/main.py
  - services/core-api/app/repositories/binding_repo.py
  - services/core-api/app/repositories/digest_repo.py
  - services/core-api/app/repositories/headline_repo.py
  - services/core-api/app/repositories/outbox_repo.py
  - services/core-api/app/repositories/reconciliation_repo.py
  - services/core-api/app/schemas.py
  - services/core-api/app/security/ratelimit.py
  - services/core-api/app/services/alerts.py
  - services/core-api/app/settings.py
  - services/core-api/app/worker.py
findings:
  critical: 4
  warning: 10
  info: 0
  total: 14
status: issues_found
---

# 7-faza: Backend kod ko'rigi

**Ko'rildi:** 2026-08-12
**Chuqurlik:** standard
**Fayllar:** 26
**Holat:** issues_found

## Summary

Sxema qatlami (`0023`, `models/notification.py`, reyestrlar, kaskad tartibi, o'zgarmaslik
qo'riqchisi) **mustahkam**: XOR/diskriminator juftligi, ikkita qisman UNIQUE indeks,
kompozit FK'lar va `NOTIFICATION_DELETE_ORDER` ning billing blokidan oldin turishi —
hammasi to'g'ri. Sirlar bilan ishlash (`SecretStr`, `hmac.compare_digest`, `_LAST_FAILURE`
ni `ContextVar` ga ko'chirish, `_validate_error_type()`) ham puxta. Pul hech qayerda
`float` ga aylanmaydi; shaxsiy ma'lumot javob shakllaridan chetlangan.

Nuqsonlar **rejalar chegarasida** joylashgan — ya'ni ular aynan hech bir reja o'z
worktree'sida ko'ra olmagan joyda:

1. **Yozuv yo'li umuman qurilmagan jadval** (`market_notification_settings`) — direktor
   dayjestlari HECH QACHON yetkazilmaydi va navbat cheksiz o'sadi (CR-01).
2. **Frontend yuboradigan maydonni backend jimgina tashlab yuboradi**
   (`assignee_user_id`, CR-02).
3. **Ijara/byudjet arifmetikasi bir bozor uchun hisoblangan, tsikl esa hamma bozor
   bo'ylab yuradi** — takroriy kvitansiya oynasi (CR-03).
4. **`attempt_count` `claim()` da oshiriladi**, ya'ni `_settle()` ochiq e'lon qilgan
   «byudjet faqat haqiqiy urinishga qo'llanadi» kafolati bajarilmaydi (CR-04).

## Critical Issues

### CR-01: `market_notification_settings` ga BIRORTA yozuv yo'li yo'q — direktor dayjestlari abadiy `pending`, navbat esa kvitansiyalarni bo'g'adi

**File:** `packages/sbozor-core/sbozor_core/models/notification.py:792-871`,
`migrations/versions/0023_notification_domain.py:541-568`,
`services/core-api/app/repositories/outbox_repo.py:404-411`,
`services/core-api/app/jobs/outbox.py:1029-1043`, `services/core-api/app/jobs/outbox.py:1155-1213`,
`services/core-api/app/jobs/notifications.py:523-531`, `services/core-api/app/jobs/notifications.py:573-581`

**Issue:**
Butun repo bo'ylab `market_notification_settings` ga `INSERT`/`UPDATE` qiladigan **birorta
kod yo'q** — na migratsiya backfill'i, na usta (wizard), na `/api/v1/*` marshruti, na
`/internal/bot/*`, na `bot-service` (unda direktor handleri umuman yaratilmagan:
`services/bot-service/app/handlers/` = `binding.py`, `start.py`, `vendor.py`).
`deferred-items.md` da ham bu band qayd etilmagan.

Oqibat zanjiri MEXANIK va u har kuni takrorlanadi:

1. `digest_morning` (08:00) va `digest_evening` (20:45) har faol bozor uchun
   `recipient_kind='market_director'` qatorini yozadi;
2. `outbox_tick` `resolve_chat_id()` ni chaqiradi -> `_RESOLVE_DIRECTOR_CHAT` 0 qator ->
   `None`;
3. `_deliver()` `_UNRESOLVED_FAILURE` bilan `_settle()` ga tushadi;
4. `_settle()` da `UNRESOLVED` shoxi `MAX_ATTEMPTS` tekshiruvidan **CHETLAB O'TADI**
   (`disposition is OutboxDisposition.RETRY and ...` sharti faqat `RETRY` ga tegishli),
   ya'ni qator `reschedule(now + 900s)` bilan **abadiy** `pending` ga qaytadi.

Ya'ni RECON-03 (direktor dayjesti, D-15/D-16) **umuman ishlamaydi** va bu hech qanday
xato bermaydi — aynan `alerting.py` ning D-20 falsafasi qarshi turgan sukunat.

Ikkinchi, undan ham og'ir oqibat — **HEAD-OF-LINE BLOKLASH**:
`_CLAIM_DUE` `ORDER BY o.created_at, o.id` (eng eski birinchi), `OUTBOX_BATCH_SIZE = 500`.
Bozor kuniga 2 ta o'lik dayjest qatori to'playdi (yiliga ~730). Ular navbatning ENG ESKI
qatorlari, ya'ni har tikda partiyaning boshini egallaydi. ~250 kundan keyin o'lik qatorlar
soni 500 dan oshadi va **har tikning butun partiyasi yetkazib bo'lmaydigan dayjestlarga
sarflanadi** — bugungi kvitansiya (CASH-05, D-02 dalili) navbatga umuman chiqmaydi.
`OUTBOX_DUE_INDEX` qisman indeksi ham aynan shu «`pending` qatorlar o'tkinchi» taxminiga
qurilgan (`models/notification.py:334-341`) va u ham buziladi.

Uchinchisi: D-19 ning «quiet hours va `overdue_days` BOZOR KESIMIDA sozlanadi» va'dasi
ham amalda **ishlamaydi** — qator yaratish yo'li yo'q, ya'ni `COALESCE` fallbacklari
platformaning yagona xulqi bo'lib qoladi va «yangi bozor kod yozmasdan ulanadi» cheklovi
bu domenda bajarilmaydi.

**Fix:**
Kamida bittasi majburiy (birinchisi eng arzon va CR-01 ning to'liq yechimi emas):

```python
# (a) OUTBOX'NI HIMOYALASH — `_settle()` da UNRESOLVED uchun ham terminal chegara:
UNRESOLVED_MAX_ATTEMPTS: Final[int] = 96 * 3   # ~3 kunlik 15 daqiqalik urinish

if disposition is OutboxDisposition.UNRESOLVED and claim.attempt_count >= UNRESOLVED_MAX_ATTEMPTS:
    disposition = OutboxDisposition.FAILED
```

```python
# (b) SOZLAMA QATORINI TUG'DIRISH — `market_create()` kaskadiga qo'shish
#     (`market_profile` bilan AYNI tranzaksiyada, `MARKET_CREATE` naqshi):
INSERT INTO public.market_notification_settings (market_id) VALUES (v_market_id);
```

```python
# (c) `director_chat_id` NI YOZISH YO'LI — ikkitasidan biri:
#   * `bot-service` ga direktor `/start` handleri + `POST /internal/bot/director/bind`
#     (servis tokeni ostida, `binding_repo.resolve()` naqshi bilan);
#   * yoki `PATCH /api/v1/markets/{id}/notification-settings` (`MARKET_MANAGE` ostida).
```

⚠ (b) va (c) siz (a) faqat navbatni himoyalaydi — direktor dayjesti baribir
yetkazilmaydi. Agar bu ONGLI keyinga qoldirish bo'lsa, u holda `digest_morning` /
`digest_evening` `director_chat_id IS NULL` bozorlar uchun **enqueue QILMASLIGI** kerak
(`enums.py::OutboxRecipientKind` docstringi allaqachon shu xulqni va'da qilgan:
«jo'natuvchi bunday qatorni ... o'z navbatiga umuman qo'ymaydi») va band
`deferred-items.md` ga egasi bilan yozilishi shart.

---

### CR-02: `PATCH /reconciliation/cases/{case_id}` `assignee_user_id` ni JIMGINA tashlab yuboradi va case'ni HUKM CHIQARGAN odamga biriktiradi

**File:** `services/core-api/app/api/v1/reconciliation.py:657-665`,
`services/core-api/app/schemas.py:4003-4007`,
`services/core-api/app/repositories/reconciliation_repo.py:873-903`

**Issue:**
`CaseUpdateRequest` `assignee_user_id: UUID | None = None` maydonini **e'lon qiladi**
(`extra="forbid"` ostida, ya'ni bu tasodifiy qoldiq emas — u ATAYIN kontraktda),
frontend esa uni **HAQIQATAN yuboradi**:

```ts
// frontend/src/lib/reconciliation-queries.ts:625-634
body: {
  status: input.status,
  resolution_note: input.resolutionNote,
  assignee_user_id: input.assigneeUserId,   // <- DecisionForm dagi tanlov
},
```

Marshrut esa uni **hech qachon o'qimaydi**:

```python
await reconciliation_repo.transition(
    session, market_id=market_id, case_id=case_id,
    to_status=payload.status.value,
    actor_user_id=principal.user_id,     # <- assignee SIFATIDA ISHLATILADI
    note=payload.resolution_note,
)
```

`_UPDATE_CASE_STATUS` esa `assignee_user_id = COALESCE(:actor_user_id, assignee_user_id)`
qiladi, ya'ni **tanlangan mas'ul o'rniga HAR DOIM direktorning o'zi yoziladi**. Javob
(`CaseDetailResponse`) direktorning `user_id` sini qaytaradi, dialog uni qayta chizadi va
foydalanuvchi «biriktirdim» degan yolg'on tasdiqni oladi. Nosozlik jimgina — 200, xatosiz,
faqat noto'g'ri odam.

⛔ IKKINCHI, XAVFSIZLIK BANDI: `0023` ochiq yozadi — «`users` GA FK YO'Q ... yagona
ustunli FK esa begona bozor xodimini biriktirishni to'xtata olmasdi. **Tekshiruv ilova
qatlamida.**» (`migrations/versions/0023_notification_domain.py:344-347`). Repoda
`assignee_user_id` uchun `user_market_roles` ustidan **birorta tekshiruv yo'q**. Ya'ni
«maydonni ulab qo'yish» degan tabiiy tuzatish begona bozor xodimini biriktirish yo'lini
OCHADI. Ikkalasi birga tuzatilishi shart.

**Fix:**

```python
# app/api/v1/reconciliation.py — `reconciliation_case_update()` ichida:

assignee = payload.assignee_user_id
if assignee is not None and not await user_repo.is_market_member(
    session, market_id=market_id, user_id=assignee
):
    raise _reject("assignee_not_in_market", status.HTTP_422_UNPROCESSABLE_CONTENT)

await reconciliation_repo.transition(
    session,
    market_id=market_id,
    case_id=case_id,
    to_status=payload.status.value,
    actor_user_id=principal.user_id,
    assignee_user_id=assignee,          # <- YANGI, ALOHIDA argument
    note=payload.resolution_note,
)
```

```sql
-- reconciliation_repo._UPDATE_CASE_STATUS: mas'ul VA aktor AJRATILADI
   SET status = :to_status,
       assignee_user_id = COALESCE(:assignee_user_id, :actor_user_id, assignee_user_id),
       ...
```

Muqobil (agar biriktirish bu fazada ATAYIN yo'q bo'lsa): maydonni
`CaseUpdateRequest` dan **olib tashlash** va frontenddan ham chiqarish — `extra="forbid"`
o'shanda 422 beradi, ya'ni jimgina yo'qotish o'rniga baland ovozli rad etish bo'ladi.

---

### CR-03: `outbox_tick` da vaqt byudjeti YO'Q — ijara tik tugashidan oldin muddati o'tadi va kvitansiya IKKI MARTA yuboriladi

**File:** `services/core-api/app/jobs/outbox.py:184-209`,
`services/core-api/app/jobs/outbox.py:925-958`, `services/core-api/app/jobs/outbox.py:961-995`

**Issue:**
Konstantalar **bitta bozor** uchun hisoblangan, tsikl esa **hamma bozor** bo'ylab
KETMA-KET yuradi:

```
OUTBOX_TICK_BUDGET_SECONDS = 20      # "tik keyingi tikdan oldin tugashi SHART"
OUTBOX_BATCH_SIZE = 25 * 20 = 500    # "partiya AYNAN vaqt byudjetiga teng"
OUTBOX_LEASE_SECONDS = 120           # "tik byudjetidan KATTA"
GLOBAL_RATE_PER_SECOND = 25          # `_Throttle` — BUTUN tik uchun bitta
```

`outbox_tick()` da byudjetni o'lchaydigan **birorta shart yo'q** (`grep` bilan
o'lchandi: `OUTBOX_TICK_BUDGET_SECONDS` faqat `OUTBOX_BATCH_SIZE` ni hisoblashda
ishlatiladi, boshqa hech qayerda o'qilmaydi). `_Throttle` esa 25 msg/s ni **butun tik**
uchun qo'llaydi. Ya'ni N ta to'la navbatli bozorda tik `N * 20` soniya davom etadi:

| bozorlar | tik davomiyligi | `OUTBOX_LEASE_SECONDS = 120` |
|---|---|---|
| 1 | ~20 s | xavfsiz |
| 6 | ~120 s | chegara |
| 7+ | >120 s | ⛔ **birinchi bozor qatorlarining ijarasi MUDDATI O'TADI** |

Muddati o'tgan ijara -> keyingi tikdagi `release_expired_leases()` uni `pending` ga
qaytaradi -> `claim()` uni QAYTA oladi -> **o'sha kvitansiya ikkinchi marta yuboriladi**.
Bu `outbox_repo.py` ning 2-majburiyati ochiq taqiqlagan holat («bitta kvitansiya IKKI
MARTA yuborilardi va sotuvchi ikki xil tasdiq olardi — D-02 ning aynan qarama-qarshi
holati») va `dedupe_key` uni **ushlamaydi**: cheklov faqat `enqueue` bosqichida ishlaydi,
jo'natishda emas.

⚠ IKKINCHI, MUSTAQIL NUQSON SHU KODDA: `now` tikning BOSHIDA bir marta hisoblanadi
(`worker.py:1171` — `now=now_tz()`) va u ikki joyda ishlatiladi:
* `lease_until = :now + make_interval(...)` — ya'ni 80-soniyada olingan partiyaning
  ijarasi allaqachon 80 soniya «yeb bo'lingan»;
* `_next_attempt_at(..., now=now)` — 80-soniyada yiqilgan qator uchun
  `next_attempt_at = tik_boshi + 30s`, ya'ni u ALLAQACHON o'tgan va backoff amalda
  qo'llanmaydi (qator keyingi daqiqadagi tikda darhol qayta olinadi).

**Fix:**

```python
# app/jobs/outbox.py — `outbox_tick()`:
deadline = monotonic() + OUTBOX_TICK_BUDGET_SECONDS
for market_id in market_ids:
    if monotonic() >= deadline:
        # ⚠ Qolgan bozorlar keyingi tikda olinadi — navbat KONVERGENT.
        log.info("outbox_tick_budget_exhausted", remaining=len(market_ids) - result.markets)
        break
    ...
    for claim in claims:
        if monotonic() >= deadline:
            break        # ijara o'z-o'zidan bo'shaydi, `attempt_count` oshirilmaydi
        await _deliver(...)
```

va ijara/backoff uchun tikning boshidagi `now` o'rniga **joriy** paytni ishlatish:

```python
moment = now + timedelta(seconds=monotonic() - started)   # yoki `now_tz()` ni argument
                                                          # sifatida `_claim_batch`/`_settle` ga
```

Muqobil (arzonroq): `OUTBOX_LEASE_SECONDS` ni `OUTBOX_TICK_BUDGET_SECONDS * max_markets`
dan katta qilish YETMAYDI — u faqat chegara sonini siljitadi. Byudjet tekshiruvi
majburiy.

---

### CR-04: `attempt_count` HAR `claim()` da oshadi — `_settle()` ning «byudjet faqat haqiqiy urinishga» kafolati bajarilmaydi

**File:** `services/core-api/app/repositories/outbox_repo.py:284-295`,
`services/core-api/app/jobs/outbox.py:1143-1213`, `services/core-api/app/jobs/outbox.py:1015-1027`

**Issue:**
`_CLAIM_DUE` `attempt_count = o.attempt_count + 1` ni **shartsiz** bajaradi. `_settle()`
esa faqat *tekshiruvni* o'tkazib yuboradi:

```python
if disposition is OutboxDisposition.RETRY and claim.attempt_count >= MAX_ATTEMPTS:
    disposition = OutboxDisposition.FAILED
```

ya'ni `UNRESOLVED` shoxida hisoblagich **BARIBIR oshib boradi**. `_settle()` ning o'z
docstringi buni ochiq taqiqlaydi:

> «⛔ BYUDJET FAQAT HAQIQIY URINISHGA QO'LLANADI: `unresolved` shoxida HTTP so'rovi
> UMUMAN yuborilmagan, ya'ni uni `MAX_ATTEMPTS` ga hisoblash sotuvchining byudjetini u
> hali BOTGA ULANMAGANI uchun yeb qo'yardi — kvitansiya `failed` bo'lardi va Telegram
> bilan hech qanday muammo bo'lmasdi»

Aynan shu sodir bo'ladi. O'lchanadigan ssenariy:

1. Sotuvchi botga hali ulanmagan. Kvitansiya har 15 daqiqada qayta olinadi
   (`UNRESOLVED_RETRY_SECONDS = 900`) -> kuniga **96 marta** `attempt_count++`;
2. 3 kundan keyin sotuvchi ulanadi. `attempt_count ≈ 288`;
3. Birinchi HAQIQIY urinishda Telegram `502` qaytaradi (`RETRY`);
4. `288 >= MAX_ATTEMPTS (5)` -> darhol `FAILED`. Qayta urinish YO'Q.

Natija: kvitansiya (D-02 ning dalili) mangu yo'qoladi, holbuki Telegram bilan atigi bir
martalik vaqtinchalik nosozlik bo'lgan. `mark_failed()` ning `last_error_type` i esa
`HTTPStatusError` deb yozadi — ya'ni jurnal ham noto'g'ri sababni ko'rsatadi.

⚠ AYNI SINFDAGI IKKINCHI YO'L: `_deliver()` ning `outbox_chat_lookup_failed` shoxi
(`outbox.py:1025-1027`) `_settle()` ni **umuman chaqirmaydi** va `return` qiladi. Qator
`sent` holatida ijara bilan qoladi, `release_expired_leases()` uni 120 s dan keyin
qaytaradi — lekin `claim()` allaqachon `attempt_count` ni oshirgan. Ya'ni takroriy DB
nosozligi ham byudjetni yeydi.

**Fix:**

```sql
-- outbox_repo._CLAIM_DUE: hisoblagichni BU YERDA oshirmaslik
   SET status = :sent,
       lease_until = :now + make_interval(secs => :lease_seconds),
       updated_at = now()
```

va urinishni AYNAN jo'natilgan joyda sanash:

```python
# app/repositories/outbox_repo.py — `mark_failed`/`reschedule`/`mark_blocked` bayonotlariga:
   SET ..., attempt_count = attempt_count + 1
# ⛔ `_UNRESOLVED_FAILURE` shoxida esa OSHIRILMAYDI — u alohida bayonotdan o'tadi:
async def defer_unresolved(session, *, market_id, outbox_id, next_attempt_at) -> None: ...
```

Minimal muqobil (agar SQL o'zgarishi qimmat bo'lsa): `OutboxClaim` ga
`unresolved_attempts` qo'shish o'rniga `_settle()` da `UNRESOLVED` shoxidan chiqishda
`attempt_count` ni **qaytarib kamaytirish** — bu shakl xunuk, lekin invariantni tiklaydi
va `release_expired_leases()` ning mavjud «oshirilmaydi» qarori bilan bir oilada bo'ladi.

## Warnings

### WR-01: `open_cases()` case TUG'ILISHI uchun `reconciliation_case_events` qatorini yozmaydi — `from_status IS NULL` yo'li O'LIK

**File:** `services/core-api/app/repositories/reconciliation_repo.py:177-296`,
`services/core-api/app/repositories/reconciliation_repo.py:323-375`

**Issue:** Sxema, model va API uchta joyda «case TUG'ILGANDA `from_status` `NULL`» degan
holatni e'lon qiladi:
`EVENT_FROM_STATUS_CHECK` (`from_status IS NULL OR ...`),
`ReconciliationCaseEvent` docstringi («⛔ `actor_user_id` `NULL` = TIZIM ... Case'ni
`recon.open` cron TUG'DIRADI, ya'ni birinchi hodisa qatorida hech qanday odam yo'q»),
`CaseEvent.from_status: str | None` va `CaseEventRow.from_status`.

Lekin `_OPEN_ANOMALY_CASES` / `_OPEN_UNPAID_CASES` faqat `reconciliation_cases` ga
`INSERT` qiladi — tug'ilish hodisasi **hech qachon yozilmaydi**. Natijada:
* yangi case'ning `events` ro'yxati BO'SH keladi (`GET /reconciliation/cases/{id}`);
* D-14 ning «case tarixi 'kim, qachon, qaysi holatdan qaysi holatga' savolining YAGONA
  javobi» da'vosi birinchi qadamni qamramaydi;
* `from_status IS NULL` shoxi mahsulotda **hech qachon bajarilmaydi**, ya'ni u sinalmagan
  o'lik yo'l.

**Fix:** `open_cases()` da ikkala `INSERT ... SELECT` ga `RETURNING id` qo'shib, o'sha
tranzaksiyada tug'ilish qatorini yozish:

```sql
), born AS (
    INSERT INTO reconciliation_case_events
                (market_id, case_id, from_status, to_status, actor_user_id)
    SELECT :market_id, i.id, NULL, :status_new, NULL
      FROM inserted i
)
```
(`inserted` CTE si `RETURNING id AS id` ga o'zgaradi; `actor_user_id = NULL` = TIZIM.)

---

### WR-02: Kechki dayjestning `anomaly_count` i STRUKTURAVIY ravishda HAR DOIM `0`

**File:** `services/core-api/app/jobs/notifications.py:558-571`

**Issue:**
```python
cases = await list_cases(session, market_id=market_id, day=as_of)   # as_of = BUGUN
anomaly_count=(cases.new_count + cases.in_review_count
               + cases.justified_count + cases.unjustified_count)
```
`list_cases(day=...)` `service_date = :day` bo'yicha filtrlaydi. Bugungi `service_date`
li case esa faqat ERTAGA 04:25 da (`RECON_OPEN_CRON`) tug'iladi — manbai
(`daily_charges`, `billing_anomalies`) ham ertaga 04:10 da yoziladi. Ya'ni 20:45 da bu
son **har kuni, istisnosiz `0`**.

Xabarda u «Anomaliyalar: 0» / «Аномалии: 0» bo'lib chiqadi — ya'ni o'lchanmagan holat
o'lchangan nol bo'lib ko'rinadi. Bu loyihaning o'z qoidasining (`digest_repo.
occupancy_percent()`: «MAXRAJ NOL BO'LGANDA JAVOB `None`, ⛔ `0` EMAS») bevosita
buzilishi va `DigestResult.charges` uchun aynan shu sinf allaqachon nomlangan.

**Fix:** Ikkitasidan biri —
(a) kechki xabardan `anomaly_count` ni **olib tashlash** (`NOTIFICATION_META
["digest_evening"].payload_keys` dan ham) va `_EVENING_TEXT` dagi `anomalies` yorlig'ini
o'chirish; yoki
(b) manbani KECHAGI kunga burish (`day=as_of - timedelta(days=1)`) va yorliqni ochiq
qilish: `«Kecha aniqlangan nomuvofiqliklar»` — o'shanda sifatlovchi kontrakti (§12.2)
buzilmaydi, chunki son «kutilayotgan» emas, «yozilgan» guruhga tegishli.

---

### WR-03: `binding_repo.revoke()` da `revoked_at IS NULL` qo'riqchisi yo'q, `old` audit qiymati TO'QILGAN, va u ATAYIN auditsiz jadvalga audit yozadi

**File:** `services/core-api/app/repositories/binding_repo.py:461-504`

**Issue:** Uchta mustaqil nuqson bitta funksiyada:

1. `UPDATE ... WHERE market_id = ... AND id = ...` — `revoked_at IS NULL` sharti YO'Q.
   `revoke()` `__all__` da (ommaviy), ya'ni allaqachon bekor qilingan qatorga chaqiruv
   `revoked_at` ni **qayta yozadi** va asl bekor qilish payti hamda sababi yo'qoladi.
   Jadvalning butun mazmuni — TARIX (D-27) — shu bilan buziladi.
2. `old={"revoked_at": None, "revoked_reason": None}` — bu **o'qilgan emas, to'qilgan**
   qiymat. Yuqoridagi holatda audit jurnaliga YOLG'ON eski holat tushadi. Loyihaning o'z
   qoidasi (`me.py::update_profile` — «Eski qiymat yozuvdan OLDIN o'qiladi») bu yerda
   bajarilmagan.
3. `schema_contract.AUDITED_TABLES` docstringi `vendor_telegram_bindings` ni ATAYIN
   chiqarib tashlagan: «jadvalning O'ZI TARIX (D-27) ... audit unga **ikkinchi nusxa**
   yozardi». `revoke()` esa aynan o'sha ikkinchi nusxani `write_app_audit()` bilan
   yozadi — reyestr qarori va kod bir-biriga zid.

**Fix:**

```python
result = await session.execute(
    update(VendorTelegramBinding)
    .where(
        VendorTelegramBinding.market_id == market_id,
        VendorTelegramBinding.id == binding_id,
        VendorTelegramBinding.revoked_at.is_(None),   # <- QO'RIQCHI
    )
    .values(revoked_at=func.now(), revoked_reason=reason)
    .returning(VendorTelegramBinding.id)
)
if result.first() is None:
    return          # allaqachon bekor qilingan — no-op, audit ham yozilmaydi
```
va `write_app_audit(...)` chaqiruvini olib tashlash (reyestr qarori bilan moslash) yoki
`AUDITED_TABLES` docstringining o'sha bandini qayta yozib, qarorni ochiq o'zgartirish.
Ikkalasidan biri — lekin ikkisi bir vaqtda to'g'ri bo'la olmaydi.

---

### WR-04: `resolve()` ning doimiy-vaqtlilik da'vosi tsikldan KEYINGI ish bilan buziladi

**File:** `services/core-api/app/repositories/binding_repo.py:331-415`

**Issue:** Modul docstringi «⛔ ERTA `break` YO'Q — VA BU XAVFSIZLIK QARORI ... javob
vaqti moslikning bor-yo'qligini oshkor qilmaydi» deb yozadi va tsikl haqiqatan oxirigacha
yuradi. Lekin tsikldan **keyin** uch shox butunlay boshqa narx bilan tugaydi:

| shox | tsikldan keyingi ish |
|---|---|
| `NO_MATCH` | `log.info` — I/O yo'q |
| `BOUND` | yangi tenant tranzaksiyasi + `SELECT` + (ehtimol) `UPDATE` + `INSERT` + `flush` |
| `MULTIPLE_MATCHES` | HAR bozor uchun yangi tranzaksiya + `alert_events` upsert |

Ya'ni «raqam reyestrda bormi?» savoliga javob vaqti baribir javob beradi — faqat
tsiklda emas, undan keyin. Tsikldagi `break` ni olib tashlash bu bo'shliqni yopmagan.

**Fix:** Da'voni kodga moslashtirish — masalan yozuv yo'lini javobdan AJRATISH
(`BOUND` shoxida ham javobni birinchi qaytarib, `bind()` ni fon vazifasiga surish) yoki
minimal doimiy kechikish qo'shish:

```python
# `resolve()` ning boshida:
deadline = monotonic() + RESOLVE_MIN_LATENCY_SECONDS
...
# oxirida, HAR uchala shoxda:
await asyncio.sleep(max(0.0, deadline - monotonic()))
```
Agar bu narx oqlanmasa — docstringdagi da'voni **kamaytirish** kerak: himoya amalda
rate-limit (`BOT_RESOLVE_LIMIT = 5`), tayming emas.

---

### WR-05: Buzuq kursor 422 emas, 500 beradi (naive/sana-only ISO qiymat)

**File:** `services/core-api/app/api/v1/reconciliation.py:251-266`,
`services/core-api/app/api/v1/reconciliation.py:802-816`

**Issue:** `_decode_cursor()` faqat `ValueError` ni ushlaydi:

```python
created_at = datetime.fromisoformat(head)   # "2026-01-01" -> NAIVE datetime, xato YO'Q
case_id = UUID(tail)
```
`?cursor=2026-01-01|<uuid>` ISO sifatida **yaroqli**, lekin natija tz-siz. U
`_TIMESTAMPTZ` bind parametriga uzatiladi va `asyncpg` uni `timestamptz` ga kodlay
olmaydi (`can't subtract offset-naive and offset-aware datetimes`) — istisno `DBAPIError`
bo'lib `main.py` ning handleriga tushadi va **500 `internal_error`** qaytadi.

Bu `_decode_cursor()` ning o'z niyatiga zid: docstring «buzilgan qiymat ⛔ 422, jim
e'tiborsizlik EMAS» deydi, lekin buzilgan qiymatning bir sinfi 422 ga umuman yetib
bormaydi.

**Fix:**

```python
try:
    created_at = datetime.fromisoformat(head)
    case_id = UUID(tail)
except ValueError as exc:
    raise _reject("cursor_invalid", status.HTTP_422_UNPROCESSABLE_CONTENT) from exc
if created_at.tzinfo is None:
    # ⛔ Kursor SERVER qurgan qiymat: u HAR DOIM tz-aware. Naive qiymat —
    #   qo'lda yasalgan kursor, ya'ni KIRISH xatosi.
    raise _reject("cursor_invalid", status.HTTP_422_UNPROCESSABLE_CONTENT)
```
(`_decode_delivery_cursor()` da ham aynan shunday.)

---

### WR-06: «BIR KNOB» tengligi FAQAT testda amal qiladi — mahsulotda ikki chegara bir kunga farq qiladi

**File:** `services/core-api/app/worker.py:1193-1195`,
`services/core-api/app/worker.py:1268`,
`services/core-api/app/repositories/reconciliation_repo.py:446`,
`services/core-api/app/repositories/digest_repo.py:467`

**Issue:** `notifications.py` va `reconciliation.py` ikkalasi ham `_MARKET_OVERDUE_DAYS`
ni SO'ZMA-SO'Z takrorlaydi va docstring «`test_overdue_reminder_shares_the_knob_with_
case_opening` AYNI bozorda IKKALA mexanizmni ham yuritadi va ularning javobi BIR XIL
bo'lishini talab qiladi» deydi. Test ikkalasini **bir xil `business_date`** bilan
chaqiradi — mahsulotda esa qobiqlar boshqacha beradi:

```python
reconciliation_open_task:  business_date = business_today() - 1   # cutoff = T-1-N
overdue_reminder_task:     business_date = business_today()       # cutoff = T-N
```

Ya'ni ikki chegara **har doim bir kunga farq qiladi**. Bugungi oqibat zararsiz (eslatma
case'dan bir kun OLDIN keladi, ya'ni «sotuvchi ogohlantirilmagan holda navbatga tushadi»
holati yuz bermaydi), lekin:
* da'vo («AYNI knob, AYNI javob») **yolg'on** va uni qo'riqlaydigan darvoza mahsulot
  yo'lini o'lchamaydi;
* qobiqlardan birining kuni o'zgarganda (masalan `overdue_reminder` kechagi kunga
  o'tkazilsa) yo'nalish TESKARIGA aylanadi va D-19 buziladi — hech qanday test buni
  ko'rmaydi.

**Fix:** Qobiqlarni tenglashtirish (ikkalasi ham `business_today() - 1`, chunki ikkala
mexanizm ham YOZILGAN hisob ustida ishlaydi) yoki farqni ATAYIN deb, o'lchov bilan qayd
etish:

```python
# app/jobs/notifications.py / reconciliation.py da BIR joyda:
def overdue_cutoff(business_date: date, overdue_days: int) -> date:
    """Chegaraning YAGONA ta'rifi — ikkala mexanizm ham SHU funksiyani chaqiradi."""
    return business_date - timedelta(days=overdue_days)
```
va testni `business_date` ni **qobiqlardan** olib solishtiradigan qilib kuchaytirish.

---

### WR-07: `outbox_repo` ning «har bind parametri tiplanadi» majburiyati uchta joyda bajarilmagan

**File:** `services/core-api/app/repositories/outbox_repo.py:300-307`,
`services/core-api/app/repositories/outbox_repo.py:638-641`,
`services/core-api/app/repositories/outbox_repo.py:688-694`,
`services/core-api/app/repositories/outbox_repo.py:717-721`

**Issue:** Modul ochiq yozadi: «⚠ HAR BIR BIND PARAMETRI TIPLANADI (`capture_repo.py`
ning 2-majburiyati): `text()` da SQLAlchemy tipni ustundan CHIQARA OLMAYDI va tipsiz
qiymat asyncpg'ga xom `str` bo'lib borardi.» Lekin:

* `_CLAIM_DUE` — `now` **tiplanmagan** (`:now AT TIME ZONE`, `<= :now`, `:now + interval`);
* `_RELEASE_EXPIRED` — `now` tiplanmagan;
* `_RESCHEDULE` — `next_attempt_at` tiplanmagan;
* `_MARK_DELIVERED` — `provider_message_id` tiplanmagan.

Bugun ular ishlaydi, chunki PostgreSQL tipni kontekstdan chiqaradi. Lekin `:now` ning
birinchi konteksti `timezone(text, unknown)` — bu **noaniq** funksiya chaqiruvi va uning
yechimi PG ning tur-ustuvorligi qoidasiga tayanadi. Aynan shu qoidaga tayanish majburiyat
yozilishiga sabab bo'lgan; ustiga naive `datetime` bergan kelajakdagi chaqiruvchi tushunarsiz
`DataError` oladi (WR-05 dagi bilan bir xil sinf).

**Fix:**

```python
).bindparams(
    ...,
    bindparam("now", type_=_TIMESTAMPTZ),               # _CLAIM_DUE, _RELEASE_EXPIRED
    bindparam("next_attempt_at", type_=_TIMESTAMPTZ),   # _RESCHEDULE
    bindparam("provider_message_id", type_=BigInteger()),  # _MARK_DELIVERED
)
```

---

### WR-08: `OUTBOX_TICK_BUDGET_SECONDS` — o'lik konstanta va YOLG'ON hujjat

**File:** `services/core-api/app/jobs/outbox.py:108-121`,
`services/core-api/app/jobs/outbox.py:184-191`,
`services/core-api/app/jobs/outbox.py:235-236`

**Issue:** Konstanta e'lon qilingan va batafsil hujjatlangan («Bitta tikning JO'NATISHGA
sarflaydigan vaqt byudjeti ... tik keyingi tik boshlanishidan oldin tugashi SHART»),
`OutboxDisposition.FAILED` ning docstringi esa uni HAQIQIY marshrut deb ko'rsatadi:
«Qayta urinib bo'lmaydigan xato (`400`/`401`/`404`) **yoki byudjet tugadi**».

Amalda:
* byudjet **hech qayerda o'lchanmaydi** (CR-03);
* `FAILED` shoxiga «byudjet tugadi» sababi bilan HECH QACHON kelinmaydi;
* konstanta `__all__` da ham yo'q, ya'ni u ommaviy ham emas, ichki ham emas.

Bu «hujjat kodni aytadi» konventsiyasining buzilishi va u keyingi ijrochini byudjet
mavjud deb ishontiradi.

**Fix:** CR-03 ni tuzatishda konstantani HAQIQATAN ishlatish va `__all__` ga qo'shish;
`OutboxDisposition.FAILED` docstringini o'sha paytdagi haqiqatga moslash. Agar byudjet
qo'shilmasa — konstantani va docstringdagi «byudjet tugadi» bandini **o'chirish**.

---

### WR-09: `_open_unpaid_cases()` ning tarixiy chegarasi yo'q — ko'rinmas case'lar tug'iladi

**File:** `services/core-api/app/repositories/reconciliation_repo.py:226-244`,
`services/core-api/app/repositories/reconciliation_repo.py:406-494`

**Issue:** `_OVERDUE_CHARGES` da `c.service_date <= :cutoff` — **quyi chegara yo'q**.
Ya'ni har yugurishda BUTUN tarixning to'lanmagan hisoblari nomzod bo'ladi va ular uchun
`service_date` **o'sha hisobning kuni** bilan case ochiladi.

Yagona ro'yxat yuzasi esa KUN kesimida:
`GET /reconciliation/cases?day=` va `GET /reconciliation/report?day=` ikkalasi ham
`service_date = :day` bilan filtrlaydi, standart kun esa KECHA. Ya'ni:

* birinchi yugurishda (yoki backfill'dan keyin) o'nlab/yuzlab eski case ochiladi;
* ular navbat ekranida **hech qachon ko'rinmaydi** — direktor aniq eski sanani qo'lda
  tanlamasa;
* `hit_rate()` ning `pending` sanog'i ular bilan doimiy shishib turadi va u
  «hali O'LCHOV YO'Q» signalini shovqinga aylantiradi;
* `skipped_existing` esa har kuni o'sha eski nomzodlarni qayta sanaydi.

**Fix:** Nomzodlarni oynaga qamash (yugurish kunidan orqaga eng ko'pi bilan N kun) yoki
«barcha ochiq case'lar» yuzasini qo'shish:

```python
CASE_LOOKBACK_DAYS: Final[int] = 30
"""⛔ NOMZODLAR OYNASI: undan eski to'lanmagan hisob ALOHIDA yuzaga (qarzdorlik
reestri) tegishli — navbatga tushsa u KUN kesimidagi ekranda ko'rinmasdi."""
...
    "floor": business_date - timedelta(days=CASE_LOOKBACK_DAYS),
# `_OVERDUE_CHARGES` ga: AND c.service_date >= :floor
```

---

### WR-10: `notify_digest` bitta yurak urishi ikki jobni yashiradi — D-20 kuzatuvi yarim ishlaydi

**File:** `services/core-api/app/jobs/notifications.py:132-153`,
`services/core-api/app/api/internal/self_check.py:108-119`,
`services/core-api/app/jobs/alerting.py:700-707`

**Issue:** `digest_morning` (08:00) va `digest_evening` (20:45) **bitta**
`system_heartbeats['notify_digest']` qatorini yangilaydi. `HEARTBEAT_STALE_HOURS`
chegarasi 24+ soat, ya'ni:

* `digest_morning` butunlay o'lsa ham `digest_evening` har kuni qatorni yangilab turadi;
* `/internal/self-check` `stale` ga tushmaydi, `alert_sweep` `digest_stale` ochmaydi;
* direktor ertalabki dayjestni olmay qo'yadi va buni **hech nima aytmaydi**.

Bu aynan D-20 («alert MUVAFFAQIYAT SIGNALINING YO'QLIGIGA qo'yiladi») ning bu fazadagi
bo'shlig'i va u izohlarda «ongli narx» deb qayd etilgan — lekin narxning o'zi
o'lchanmaydigan qilingan: darvoza **yarim o'lgan juftlikni ko'ra olmaydi**.

**Fix:**

```python
DIGEST_MORNING_COMPONENT: Final[str] = "notify_digest_morning"
DIGEST_EVENING_COMPONENT: Final[str] = "notify_digest_evening"
```
va ikkalasini `self_check.EXPECTED_COMPONENTS` hamda `alerting._platform_signals`
`watched` kortejiga qo'shish (`test_heartbeat_registry.py` AST darvozasi
`app/jobs/` ni to'liq skanerlagani uchun reyestrlar avtomatik moslashadi).

---

_Reviewed: 2026-08-12_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
