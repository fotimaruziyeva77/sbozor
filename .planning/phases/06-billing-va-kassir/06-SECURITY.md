---
phase: 6
slug: billing-va-kassir
status: verified
threats_open: 0
asvs_level: 1
created: 2026-08-11
---

# Phase 6 — Security

> Faza xavfsizlik shartnomasi: tahdid reyestri, qabul qilingan xavflar va audit izi.
>
> ⛔ **Audit qoidasi:** REJA — DA'VO, KOD — DALIL. Har bir `mitigate` bandi
> uchun quyida `fayl:qator` yoki **haqiqatan yugurtirilgan** buyruq va uning
> natijasi keltirilgan. «Rejada yozilgan» hech qachon yopish asosi bo'lmadi.

---

## Trust Boundaries

| Chegara | Tavsif | Kesib o'tuvchi ma'lumot |
|---------|--------|--------------------------|
| kassir mijozi → `POST /payments` | Takror so'rov, o'zgartirilgan payload, uch tez bosish | Pul yozuvi (`bigint` so'm), idempotentlik kaliti |
| bozor A → bozor B | RLS `ENABLE`+`FORCE` + kompozit FK tenant chegarasi | Hisob, to'lov, smena, anomaliya qatorlari |
| kassir → tizim summasi | Deklaratsiyadan **oldin** tizim summasini bilish ko'r deklaratsiyani buzadi | `system_soum`, `variance_soum`, to'lovlar yig'indisi |
| kassir roli → shaxsiy ma'lumot yuzasi | Yangi huquq berish `PERSONAL_FIELDS` yuzasini ochib qo'yardi | `vendor_name`, `phone`, `full_name` |
| kassir roli → dalil-kadr baytlari | `camera_view` berish `require_any_permission()` yopiq to'plamini kengaytirardi | JPEG baytlari (tashrifchilar tasviri) |
| ilova / xom SQL → yozilgan pul yozuvi | Ilova validatsiyasi migratsiya va xom SQL yo'lini qamramaydi | `daily_charges`, `payments`, `cashier_shifts` |
| job / `SECURITY DEFINER` yuza → RLS | Chaqiruvchisiz DEFINER funksiya — chetlab o'tish yuzasi | Bozorlar ro'yxati, kalendar qarori |
| bandlik hosilasi → pul qarori | Noto'g'ri predikat sotuvchini to'lamagan patta uchun qarzdor qiladi | `stall_slot_occupancy` → `daily_charges` |
| proyeksiya ↔ yozilgan hisob | Bir ekranda uchrashsa proyeksiya kvitansiya bo'lib o'qiladi | `data-billing-block` to'plamlari |
| server javobi → brauzer | E'lon qilingan maydon DevTools bilan **o'qiladi**; `null` ham maydon borligini tasdiqlaydi | Javob sxemalari |
| yashil darvoza → «faza tugadi» xulosasi | Yashil natija o'lchanmagan qatlamni yashirishi mumkin | Mezon moduli, byudjet, talab belgisi |
| paket registri → repo | Yangi bog'liqlik yuzasi (bu fazada **ochilmadi**) | `package.json`, `pyproject.toml`, lockfayllar |

---

## Threat Register

⛔ **106 ta noyob ID.** 104 × `mitigate`, 2 × `accept` (T-06-36, T-06-SC).
`T-06-SC` o'n to'rtala rejada bir xil ID bilan takrorlanadi va bu yerda **bir marta** yoziladi.

| Threat ID | Category | Component | Disposition | Mitigation (dalil) | Status |
|-----------|----------|-----------|-------------|--------------------|--------|
| T-06-01 | Repudiation | idempotent yozuv oynasi | mitigate | `tests/tenancy/test_idempotency_concurrency.py:326` — `IDEMPOTENT_GET_OR_CREATE_SUPPORTED` marker **o'lchanadi**, taxmin emas | closed |
| T-06-02 | Tampering | `billable_from_slots()` predikati | mitigate | `tests/unit/test_billable_from_slots.py:246` — `test_human_empty_on_another_slot_does_not_make_it_billable()` (nomlangan test, aynan C-6 holati) | closed |
| T-06-03 | Tampering | `variance()` ishorasi | mitigate | `packages/sbozor-core/sbozor_core/billing.py:310` — `declared_soum - system_soum`; `grep -cE "\babs\("` → **0** | closed |
| T-06-04 | Tampering | pul turi | mitigate | `billing.py:308-309` `assert_safe_soum()` kirishda; `grep -cE "\bfloat\(\|Decimal\|round\("` → **0** | closed |
| T-06-04a | Repudiation | «qaysi kunning pattasi to'landi?» (D-24) | mitigate | `billing.py:80` — `ALLOCATION_RULE = "FIFO_OLDEST_SERVICE_DATE_FIRST"`; taqsimlash **saqlanmaydi** | closed |
| T-06-04b | Tampering | taqsimlashning qoldiqdan ajralishi | mitigate | `billing.py:470` `allocate_charge_credit()` + `billing_repo.py:1023` `vendor_outstanding()` — bir xil son | closed |
| T-06-04c | Tampering | ikkinchi pul arifmetikasi | mitigate | `billing.py:339` `total_due_soum()` **yagona**; `billing.py:410` `payment_quote_set()` **shuni** chaqiradi; prod chaqiruv `billing_repo.py:1394` | closed |
| T-06-05 | Information disclosure | `ROLE_PERMISSIONS[CASHIER]` | mitigate | `services/core-api/app/security/rbac.py:287-293` — **aynan uch huquq**; `market_data_view`/`vendor_view`/`camera_view`/`report_view` **yo'q**; rad sababi `rbac.py:129-150` | closed |
| T-06-06 | Elevation of privilege | `require_any_permission()` yopiq to'plami | mitigate | Butun ilovada **2 chaqiruv**, ikkalasi ham `api/v1/snapshots.py:236,479` (`EVIDENCE_FRAME_PERMISSIONS`); 6-fazada **0** | closed |
| T-06-07 | Tampering | `AdjustmentReason`/`ReversalReason` | mitigate | `node --test frontend/scripts/billing-copy.test.mjs` → G-24 «reyestrda `other`/`custom` YO'Q» **yashil** | closed |
| T-06-08 | Tampering | backend↔frontend enum drifti | mitigate | Shu yugurish: «§5.10: domen enumlari `api-types.ts` ko'zgusi bilan AYNAN mos» + «parser tirik» nazorati **yashil** | closed |
| T-06-09 | Information disclosure | xato matnida ichki tafsilot | mitigate | `node --test frontend/scripts/error-codes.test.mjs` → G-17 «billing reyestri AYNAN o'n to'rt kod» **yashil**; server matn emas, **KOD** qaytaradi | closed |
| T-06-09a | Repudiation | biriktirilmagan rastaga to'lov | mitigate | `api/v1/payments.py:360` — `STALL_NOT_ASSIGNED` **409** | closed |
| T-06-09b | Tampering | «summa yo'q» sukunati | mitigate | `payments.py:409-415` — 422 **bo'sh kvota to'plamiga** bog'langan, `amount_soum is None` ga emas | closed |
| T-06-10 | Information disclosure | `shiftCloseResponseSchema` | mitigate | `frontend/src/lib/shift-queries.ts:103-108` — `z.strictObject` aynan `{id,status,declared_soum,closed_at}` | closed |
| T-06-11 | Tampering | `pendingStallSchema` | mitigate | `frontend/src/lib/billing-pending-queries.ts` — `charge_id\|chargeId\|tariff_id\|tariffId\|category_id` grep → **0** | closed |
| T-06-12 | Tampering | kesh eskirishi | mitigate | `billing-pending-queries.ts:371-372` va `:403-404` `staleTime:0`+`gcTime:0`; `removeQueries` `:66,296` | closed |
| T-06-13 | Information disclosure | `GET /payments/recent` yig'indisi | mitigate | `frontend/src/lib/payment-queries.ts` — `limit\|offset\|cursor\|page` grep → **0**; server oynasi `payment_repo.py:145` `RECENT_PAYMENT_WINDOW = 5` | closed |
| T-06-14 | Information disclosure | kassir yuzasida shaxsiy maydon | mitigate | `collect-surface.test.mjs` → «G-22: `lib/billing-pending-queries.ts` da taqiqlangan nom YO'Q» **yashil** | closed |
| T-06-15 | Tampering | `daily_charges` tahriri | mitigate | `migrations/entities/triggers.py:601-621` — **shartsiz** `RAISE EXCEPTION`; `RETURN OLD` faqat qoralama bozor shoxida; ulanish `0020:740-744` | closed |
| T-06-16 | Repudiation | `payments` o'chirilishi | mitigate | `triggers.py:651-671` shartsiz; storno ikki tomonlama `CHECK` — `models/billing.py:316` | closed |
| T-06-16a | Repudiation | `service_date` ustunining yo'qligi | mitigate | `0020:380,548,629` `service_date` ustuni; `payment_allocations`/`allocated_*`/`balance_soum` jadval va ustuni → **0** | closed |
| T-06-17 | Tampering | bir kalit, boshqa summa | mitigate | `0020:598` `uq_payments_market_id_idempotency_key` + `0020:560` `request_fingerprint` | closed |
| T-06-18 | Tampering | server summasidan chetlanish | mitigate | `packages/sbozor-core/sbozor_core/models/billing.py:346` `(amount_soum = quote_soum) = (override_reason IS NULL)`; qo'llanishi `0020:610` | closed |
| T-06-19 | Tampering | ko'r deklaratsiyani qayta yozish | mitigate | `triggers.py:691-732` — `closed` → har qanday `UPDATE` rad; `IS DISTINCT FROM` (`<>` emas) | closed |
| T-06-20 | Repudiation | ikkinchi ochiq smena | mitigate | `0020:696-700` — `unique=True` + `postgresql_where=SHIFT_OPEN_PREDICATE` | closed |
| T-06-21 | Information disclosure | bozorlararo hisob/to'lov o'qish | mitigate | `0020:708-711` — `BILLING_TENANT_TABLES` (**6 jadval**) ustidan `enable_tenant_rls`+`tenant_policy`+`owner_bootstrap_policy`; kompozit FK `entities/__init__.py:445-457` | closed |
| T-06-22 | Elevation of privilege | RLS chetlab o'tish yuzasi | mitigate | `0020:762-763` ikki orfan DEFINER **DROP**; `tests/tenancy/test_occupancy_domain_meta.py:75` `DEFINER_SURFACES = ()`; yangi DEFINER **0** | closed |
| T-06-23 | Tampering | pul `float` bo'lib qolishi | mitigate | `0020:322,323,383,384,437,549,551` `sa.BigInteger()`; G-3 to'plam tengligi `test_phase6_criteria.py:1851` | closed |
| T-06-24 | Tampering | mutable qatorga «dalil» ishorasi | mitigate | `0020:480` `occupancy_event_id` **NOT NULL** + `0020:505` kompozit FK; `stall_slot_occupancy_id` faqat audit havolasi | closed |
| T-06-25 | Tampering | `daily_charges`/`payments` tahriri | mitigate | `pytest tests/integration/test_billing_immutable.py` → **12 test yashil**; `test_a_written_charge_cannot_be_edited_or_deleted:193`, `test_a_payment_cannot_be_edited_or_deleted:275` | closed |
| T-06-26 | Tampering | shartli qo'riqchi chegarasi | mitigate | `test_billing_immutable.py:414` `test_a_shift_closes_once_and_never_reopens`, `:471` `test_an_open_shift_cannot_carry_a_declaration` — yashil | closed |
| T-06-27 | Repudiation | rad etilgan amal audit izi | mitigate | `test_billing_immutable.py:616` `test_the_audit_log_records_only_what_actually_happened` — **ikki yo'nalish** — yashil | closed |
| T-06-28 | Tampering | seedning mahsulot yo'lidan chetlashishi | mitigate | `tests/fixtures/billing_domain.py:5,18` — slotlar **faqat** `day_close` orqali; qo'lda `INSERT` taqiqlangan | closed |
| T-06-29 | Repudiation | ikkinchi ochiq smena | mitigate | `test_billing_immutable.py:558` `test_a_cashier_cannot_open_a_second_shift` — yashil | closed |
| T-06-30 | Tampering | D-04 predikati | mitigate | `app/repositories/billing_repo.py:557` `billable_from_slots()` **qayta ishlatilgan**; `human_confirmed` grep → **0** | closed |
| T-06-31 | Tampering | tarifning retroaktiv ta'siri | mitigate | `billing_repo.py:208,217` `valid_from <= :as_of`; summa va `tariff_id` qatorda saqlanadi (`0020:383-384`) | closed |
| T-06-32 | Tampering | ko'r nuqtadan tushum | mitigate | `billing_repo.py:776-785` — `no_coverage_stall` alohida `kind`, hisob yozilmaydi; juftlangan `CHECK` `0020:664` | closed |
| T-06-33 | Repudiation | «kim qarzdor noma'lum» | mitigate | `billing_repo.py:609-611` — `vendor_id is None` → `ValueError`; `daily_charges.vendor_id` `NOT NULL` | closed |
| T-06-34 | Tampering | yopiq kunda jimgina tushum | mitigate | `billing_repo.py:193` `market_is_open()` tenant konteksti ostida; INVOKER + fail-closed (`:46,389`) | closed |
| T-06-35 | Tampering | dalilning «qayta hisoblanishi» | mitigate | `billing_repo.py:492,501,547` — `winning_occupancy_event_id` muzlatilgan pointer (C-7) | closed |
| T-06-36a | Repudiation | kun kesimida javobning yo'qolishi | mitigate | `billing_repo.py:129` `vendor_charge_allocation()` — **hosila** ko'rinish, hech nima saqlanmaydi | closed |
| T-06-36b | Tampering | ikki hosila ko'rinishning ajralishi | mitigate | `billing_repo.py:1115` — belgili to'lov ifodasi **bitta** konstanta, ikkala funksiya shuni ishlatadi | closed |
| **T-06-36** | Information disclosure | qoldiqning rasta kesimida bo'linishi | **accept** | Sabab kodda: `billing_repo.py:996` «QOLDIQ NEGA SOTUVCHI KESIMIDA (C-4)»; Accepted Risks Log da | closed (accepted) |
| T-06-37 | Elevation of privilege | job ning bozor ro'yxati | mitigate | `app/jobs/billing_close.py:116,272` — **faqat** `active_market_ids()`; `occupancy_day_close_markets\|audit_draw_due_markets` grep → **0** | closed |
| T-06-38 | Tampering | yopiq kunda hisob | mitigate | `billing_close.py:49,166` — `market_is_open()` tenant konteksti ostida | closed |
| T-06-39 | Denial of service | bir bozor xatosi butun yugurishni yiqitishi | mitigate | `billing_close.py:289-291` — har bozor alohida tranzaksiya, `SQLAlchemyError` yutiladi | closed |
| T-06-40 | Information disclosure | xato matni / heartbeat `detail` | mitigate | `billing_close.py:290-291` — **faqat** `type(exc).__name__`; xabar matni javobga chiqmaydi | closed |
| T-06-41 | Repudiation | cron hech qachon ishlamasligi | mitigate | `app/api/internal/self_check.py:113` `EXPECTED_COMPONENTS` da `"billing_close"`; `app/jobs/alerting.py:627` `(BILLING_CLOSE_COMPONENT, "billing_close_stale")`, `:315` `AlertMeta(..., CRITICAL)` | closed |
| T-06-42 | Tampering | Pitfall 2 — nol hisob «joyida» ko'rinishi | mitigate | `billing_close.py:207,380` — `no_slot_rows` **ajratilgan** hisoblagich | closed |
| T-06-43 | Information disclosure | `PendingStallResponse` | mitigate | `app/schemas.py` — **aynan 7 maydon**, `charge_id`/`tariff_id`/`vendor_*` **yo'q**; SC#4 `test_phase6_criteria.py:1243` | closed |
| T-06-44 | Information disclosure | kassirga shaxsiy ma'lumot | mitigate | `PERSONAL_FIELDS = {vendor_name, phone, full_name}` — birortasi ham 6-faza javob modelida yo'q (butun `schemas.py` skani); `PERSONAL_ROUTES` marshrut grafidan **hosila** (`test_personal_data_coverage.py:323`) | closed |
| T-06-45 | Information disclosure | bozorlararo hisob o'qish | mitigate | `pytest tests/tenancy/test_cross_tenant.py` → **578 test yashil, exit 0**; `PARAM_FILLERS` da B bozorining **haqiqiy** qiymati | closed |
| T-06-46 | Elevation of privilege | `require_any_permission()` yopiq to'plami | mitigate | `billing.py:95,109`, `payments.py:115,129`, `shifts.py:107,126` — **hammasi** `require_permission()` (bitta huquq) | closed |
| T-06-47 | Repudiation | tenant da'vosining sinalmasligi | mitigate | `tests/tenancy/test_cross_tenant.py:2089` `test_no_matrix_route_returns_422` — yugurdi, yashil | closed |
| T-06-48 | Tampering | kelajak kuni uchun hisob | mitigate | `api/v1/billing.py:124` `_DAY_IN_FUTURE`, majburlanishi `:207-210` → **422** | closed |
| T-06-49 | Repudiation | takror to'lov | mitigate | `0020:598` UNIQUE + `payments.py:327-342` ikki bayonotli get-or-create; `test_idempotency_concurrency.py` yashil | closed |
| T-06-50 | Tampering | bir xil kalit, boshqa summa | mitigate | `payments.py:333-342` — `request_fingerprint` mos kelmasa **409 `idempotency_key_reused`** | closed |
| T-06-51 | Tampering | sabab-kodsiz summa o'zgarishi | mitigate | `payments.py:425` **422 `reason_required`**; sxema qatlami `0020:610`; audit `payments.py:459-468` (`quote_soum`, `reason_code`) | closed |
| T-06-52 | Repudiation | to'lovni o'chirib «pul kelmagan» qilish | mitigate | `payments.py` da `@router.put\|patch\|delete` → **0** (faqat 2 `post` + 1 `get`); trigger `triggers.py:651` | closed |
| T-06-53 | Information disclosure | kassirning tizim summasini yig'ishi | mitigate | `payment_repo.py:145` `RECENT_PAYMENT_WINDOW = 5`; `payments.py:588-606` imzosida `limit`/`offset`/`cursor` **yo'q** | closed |
| T-06-54 | Tampering | `quote_soum` ni mijozdan olish | mitigate | `schemas.py:3296` — `quote_soum` `PaymentCreateRequest` da **e'lon qilinmagan**; server `payments.py:408` `payment_quote_set()` dan oladi | closed |
| T-06-54a | Repudiation | yopiq kunda qarzning undirilmasligi | mitigate | `payments.py:409-415` — 422 **bo'sh kvota to'plamiga** bog'langan; `outstanding_soum` `market_is_open()` dan mustaqil | closed |
| T-06-54b | Repudiation | biriktirilmagan rasta yoki noto'g'ri 404 | mitigate | `payments.py:360` — **409 `stall_not_assigned`** (404 emas) | closed |
| T-06-54c | Tampering | ma'nosiz sabab-kodning auditga tushishi | mitigate | `payments.py:421` — **422 `override_not_applicable`**, jimgina tashlanmaydi | closed |
| T-06-55 | Information disclosure | bozorlararo to'lov | mitigate | `test_cross_tenant.py` matritsasi yashil (578 test); RLS + kompozit FK | closed |
| T-06-56 | Information disclosure | kassir yuzasida shaxsiy maydon | mitigate | `PaymentResponse` — 8 maydon, `vendor_name`/`phone` **yo'q** (to'liq `schemas.py` skani) | closed |
| T-06-57 | Elevation of privilege | boshqa smenaning to'lovini bekor qilish | mitigate | `payments.py:538-544` — `owner.shift_id != shift_id` → **403** (404 emas: qator mavjudligi allaqachon tasdiqlangan) | closed |
| T-06-58 | Information disclosure | `ShiftCloseResponse` | mitigate | `schemas.py` — **aynan 4 maydon** `{id,status,declared_soum,closed_at}`; sakkiztasi `null` bo'lib ham yo'q | closed |
| T-06-59 | Information disclosure | variance orqali tizim summasi | mitigate | `variance_soum`/`system_soum` faqat `ShiftReportRow` da; marshrut `shifts.py:126` `ReportViewerDep` (`REPORT_VIEW`); kassirda bu huquq **yo'q** (`rbac.py:287`) | closed |
| T-06-60 | Tampering | deklaratsiyani qayta yozish | mitigate | Ilova: ikkinchi `close` → 409; sxema: `triggers.py:712-721` | closed |
| T-06-61 | Repudiation | ortiqcha naqdni jimgina yutish | mitigate | `schemas.py:3585` — `variance_soum` **belgili**; `grep -c "abs("` `shifts.py`,`shift_repo.py` → **0/0** | closed |
| T-06-62 | Elevation of privilege | begona smenani yopish | mitigate | `shifts.py:272,306,372` `cashier_id=principal.user_id`; mos kelmasa `:379` **403** | closed |
| T-06-63 | Repudiation | ikkinchi ochiq smena bilan variance dan qutulish | mitigate | `0020:696-700` qisman UNIQUE; ilovada oldindan tekshiruv yo'q — poyga DB da | closed |
| T-06-64 | Information disclosure | smenasiz to'lovlarning yo'qolishi | mitigate | `schemas.py:3652-3653` — `shiftless_payment_count`/`_soum` **alohida sanoq** | closed |
| T-06-65 | Information disclosure | kassir ismi javobda | mitigate | `shifts.py:439,453` — `cashier_id` qaytadi, **ism emas**; klient `GET /users` bilan joinlaydi | closed |
| T-06-66 | Repudiation | uch tez bosish / `Enter` bosib turish | mitigate | `components/collect/payment-bar.tsx:159` `submittedRef = useRef(...)`; `:220` `if (event.repeat) return;`; server kaliti (T-06-49) — ikki qatlam | closed |
| T-06-67 | Tampering | eski summa yangi rasta ostida | mitigate | `pending-card.tsx:100` `pending.stall_code === enteredCode`; `gcTime:0`/`staleTime:0`; `data-collect-step` invarianti `collect-session.tsx:40` | closed |
| T-06-68 | Tampering | klientda pul arifmetikasi | mitigate | `tariff_id`/`category_id` klient sxemasida **yo'q**; G-22 «tarif kirish ma'lumoti reyestrda NOMMA-NOM bor» **yashil** | closed |
| T-06-69 | Tampering | sabab-kodsiz summa o'zgarishi | mitigate | `reason-dialog.tsx:254` `aria-disabled`, `:244` `inputMode="numeric"`; `<textarea>` **yo'q** (`:45`); server 422 (T-06-51) | closed |
| T-06-70 | Information disclosure | yig'indi orqali tizim summasi | mitigate | `collect-surface.test.mjs` → «G-7: `components/collect/**` da tizim summasi va farq YO'Q» **yashil**; `payment-row.tsx` da `reduce(`/`sum`/`total` → **0** | closed |
| T-06-71 | Information disclosure | kassir ekranida shaxsiy maydon | mitigate | `collect-surface.test.mjs` → «G-22: `components/collect/**` da taqiqlangan nom YO'Q» **yashil** | closed |
| T-06-72 | Repudiation | to'lovni tahrirlash/o'chirish | mitigate | `payment-row.tsx` — `Tahrirlash\|O'chirish\|editPayment\|deletePayment` grep → **0** | closed |
| T-06-73 | Tampering | ommaviy to'lov («hammasini to'lash») | mitigate | `node --test frontend/scripts/bulk-action-surface.test.mjs` → «e'lon qilingan KATALOGLARDA ommaviy amal yuzasi YO'Q» **yashil**; `collect-surface.test.mjs` §15.4 ham yashil | closed |
| T-06-74 | Information disclosure | `shift-close-form` ekrani | mitigate | `shift-close-form.tsx` — faqat `result.declared_soum` (`:183`); `system_soum`/`variance` **yo'q**; `blind-payload.test.mjs` yashil | closed |
| T-06-75 | Information disclosure | ko'rinadigan ikkinchi son | mitigate | `blind-payload.test.mjs` (to'liq zanjirda) — ko'rinadigan sonlar to'plami da'vosi **yashil** | closed |
| T-06-76 | Information disclosure | ochiq smena kartasidagi yig'indi | mitigate | `shift-open-card.tsx` — `reduce(\|\.sum\|paymentCount\|totalSoum\|total` grep → **0** | closed |
| T-06-77 | Tampering | deklaratsiyani oldindan to'ldirish | mitigate | `shift-close-form.tsx` — `useSearchParams\|nuqs` grep → **0** | closed |
| T-06-78 | Tampering | ikkinchi ochiq smena | mitigate | `shift-open-card.tsx:158` vs `:168` — holat bo'yicha **yo tugma, yo karta**; server 409 (`shifts.py:275`); DB qisman UNIQUE — uch qatlam | closed |
| T-06-79 | Repudiation | nol naqdni yozib bo'lmasligi | mitigate | `shift-close-form.tsx:119` `parseSoumInput(raw, { min: 0 })`; `shift-close-form.test.tsx:342` «NOL deklaratsiya RUXSAT» | closed |
| T-06-80 | Tampering | proyeksiyani kvitansiya deb o'qish | mitigate | `app/[locale]/(app)/billing/page.tsx:137,146` — shartli render (`? … : null`), `hidden`/`display:none` **0**; to'plam tengligi `page.test.tsx:298` `{day,pending,shifts}` va `:316` `{day,charges,anomalies,shifts}` — **disjunkt** | closed |
| T-06-81 | Elevation of privilege | dalil-kadr yuzasining kengayishi | mitigate | `tests/tenancy/test_personal_data_coverage.py:488` — `SNAPSHOT_EVIDENCE_FRAME_ROUTES = ("/api/v1/snapshots/{snapshot_id}/image",)`, **aynan bitta**. `git log -S` → oxirgi o'zgarish `795a63b` (**05-16**), 6-fazada **tegilmagan**. Yangi huquq **0** (`require_any_permission` 6-fazada ishlatilmaydi) | closed |
| T-06-82 | Information disclosure | kadr baytlarining chetlab olinishi | mitigate | `presign\|X-Amz\|s3.\|seaweed\|:8333\|toDataURL\|download` butun `components/billing/**` + `billing/page.tsx` bo'yicha → **0**. `charge-detail-dialog.test.tsx:222` yo'llar to'plami tengligi, `:287` `crossOrigin` yo'q, `:298-299` `<a>` va `<canvas>` soni **0** | closed |
| T-06-83 | Repudiation | ortiqcha naqdni jimgina yutish | mitigate | `variance-cell.tsx:55-59` uch shox, `:87` ikonka + `:89` belgili son + `:92` **MATN** (WCAG 1.4.1); `abs(` → **0**. Ikki yo'nalish **bitta** testda: `variance-list.test.tsx:176` (matn `:200-203`, ikonka to'plami `:217-219`) | closed |
| T-06-84 | Tampering | variance ni «to'g'rilash» | mitigate | `variance-list.test.tsx:290-300` — `button, a, input, select, textarea` to'plami `toEqual(new Set())`, nazorat asserti `:288` `tbody tr === 3` | closed |
| T-06-85 | Tampering | ko'r nuqtadan tushum da'vosi | mitigate | `anomaly-list.tsx:90,95,101` — `unassigned_count`/`closed_day_count`/`no_coverage_count` **uch alohida sanoq**; `:198` `snapshot_id === null ? null : <AnomalyEvidence/>` — **chizilmaydi**, `disabled` emas; DB jufti `0020:664` | closed |
| T-06-86 | Information disclosure | moliyaviy marshrutga ism qo'shilishi | mitigate | `schemas.py` to'liq skani: `vendor_name`/`full_name`/`phone` faqat 2–4-faza modellarida (`StallListItem`, `VendorListItem`, `UserListItem`, `ProfileResponse`, `AssignmentItem`, `StaffCredentialItem`) — **birorta 6-faza modelida yo'q**. Klient joini `variance-list.test.tsx:358-367` (`/users`) | closed |
| T-06-87 | Tampering | saqlangan balans nomining paydo bo'lishi | mitigate | `grep -rin "balance" frontend/src/components/billing/ app/[locale]/(app)/billing/` → **0**; server tomonda `0020` da `balance_soum` ustuni → **0** | closed |
| T-06-88 | Repudiation | mezonning jimgina tushib qolishi | mitigate | `tests/integration/test_phase6_criteria.py:1530-1564` — ro'yxat `inspect.getmembers` dan **hosila** (`:1548`), bo'shlikka qarshi `len(names) >= 7` (`:1551`), har `sc<N>` uchun `len(owned) == 1` (`:1558`) | closed |
| T-06-89 | Tampering | soxtalashtirilgan o'lchov | mitigate | `test_phase6_criteria.py:1567-1676` — **ikki mustaqil yo'l**: `ast` daraxti (`:1602-1626`) + modul globallari/test imzolari (`:1629-1657`); D-11 taqig'i (`:1663-1676`). O'lchandi: `unittest.mock\|MagicMock\|monkeypatch\|patch\(` → **0**, `\bfloat\(\|Decimal\|round\(` → **0** | closed |
| T-06-90 | Tampering | sabotajning o'lchanayotgan tizimga yetmasligi | mitigate | S-2 `ALTER TABLE daily_charges DISABLE TRIGGER USER` testning **o'z sessiyasida** bajarilgan → «DID NOT RAISE RaiseException» (06-14-SUMMARY «Sabotaj»); qaytarilgani tekshirildi: prod kodda `DISABLE TRIGGER` → **0** (faqat izohlar), `git status` — **toza** | closed |
| T-06-91 | Repudiation | yashil sabotajdan xulosa chiqarish | mitigate | S-1 yashil qolgach **HOLAT** kengaytirilgan va u kodda: `test_phase6_criteria.py:935` `assert again.errors == []`, `:939` `again.skipped_existing >= len(written)`. Ikkinchi urinish qizardi. `on_conflict_do_update` prod kodda → **0** | closed |
| T-06-92 | Repudiation | byudjetning jimgina ko'tarilishi | mitigate | **Uch o'lchov tinch xostda:** 1703 / 1733 / 1899 s, tarqoqlik 196 s (`06-VALIDATION.md:85-95`). Son **ikki joyda BIR XIL — 2300 s**: `package.json:23` `//gate-budget` va `06-VALIDATION.md:75,94`. Sabab izohda («o'sish to'plamning o'sishidan»). `node scripts/check-validation-signoff.mjs` → exit 0, `nyquist_compliant: true` hisob-kitob bilan mos. ⚠ 06-14-SUMMARY.md bu bandni «o'lchanmadi» deb yozadi — **u eskirgan** (pastdagi Findings) | closed |
| T-06-93 | Repudiation | o'lchanmagan talabni `Done` deb belgilash | mitigate | `node scripts/check-requirements-sync.mjs` → **exit 0**, «49 talab, ro'yxat va Traceability jadvali MOS · Done 30 · Pending 17 · **Blocked 2**» — `Blocked` mexanizmi tirik, dekorativ emas. 6-faza qatorlari `REQUIREMENTS.md:167-175` | closed |
| T-06-94 | Denial of service | disk to'lib o'lchovning buzilishi | mitigate | O'lchovdan **oldin** tekshirildi: `06-VALIDATION.md:85` «Disk tekshiruvi (`C:` da ≥ 10 GB) ✅», xavf yozildi `:116` «92 % to'la (bo'sh 15 GB)». Audit paytida jonli tasdiq: `df -h /c` → **14G Avail (92 %)** — chegara hamon bajarilgan | closed |
| **T-06-SC** | Tampering | npm/pip/cargo o'rnatish | **accept** | Mexanik tasdiq: `git diff 5cf3602..HEAD -- package.json frontend/package.json pyproject.toml services/*/pyproject.toml packages/*/pyproject.toml uv.lock frontend/package-lock.json` → **1 fayl, 2 qator**, ikkalasi ham `//gate-budget` **izohi**. Birorta bog'liqlik qatori qo'shilmagan | closed (accepted) |

*Status: open · closed*
*Disposition: mitigate (ijro talab qilinadi) · accept (hujjatlashtirilgan xavf) · transfer (uchinchi tomon)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-06-01 | T-06-36 | Qoldiq **sotuvchi kesimida** hisoblanadi (C-4), rasta kesimida emas. Bir sotuvchining ikki rastasi bo'lsa kassir har rastada **o'sha** qoldiqni ko'radi — bu **to'g'ri**, chunki qarz sotuvchiniki. Rasta kesimiga bo'lish `payments.charge_id` ni talab qilardi, u esa mavjud emas va bo'lishi ham mumkin emas (kassir hisobga emas, **rastaga** to'laydi). Sabab kodda: `services/core-api/app/repositories/billing_repo.py:996`; atama UI-SPEC §13.1 «Eski qarz» bilan mos. Ta'sir: ma'lumot **oshkor bo'lmaydi** — sotuvchi o'z qarzini ko'radi; xavf faqat kassirning noto'g'ri talqinida va u matn bilan yopilgan | 06-06 reja + orkestrator | 2026-08-10 |
| AR-06-02 | T-06-SC | Bu fazada **birorta yangi paket o'rnatilmaydi**: idempotentlik kaliti `crypto.randomUUID()` (native), pul formatlash `useFormatter().number()`, jadval — native `<table>`, `sha256` — stdlib `hashlib`, `recharts` **qo'shilmaydi** (egasi 8-faza). Butun faza mavjud pinlar ustida ishlaydi (`06-RESEARCH.md` § Package Legitimacy Audit). Ta'sir: ta'minot zanjiri yuzasi **o'smaydi**; xavf nolga yaqin va u yuqoridagi `git diff` bilan **mexanik tasdiqlangan** | 06-01…06-14 rejalari + orkestrator | 2026-08-11 |

*Qabul qilingan xavflar keyingi audit yugurishlarida qayta ko'tarilmaydi.*

---

## Unregistered Flags

**Yo'q.** `## Threat Flags` bo'limi bor o'n ikki SUMMARY (06-01…06-12) da e'lon qilingan
butun yangi hujum yuzasi reyestrdagi ID ga **to'liq** xaritalanadi:

- **11 yangi HTTP marshruti** (`GET /billing/{pending,charges,charges/{id},anomalies}`,
  `POST /payments`, `POST /payments/{id}/reverse`, `GET /payments/recent`,
  `POST /shifts`, `POST /shifts/{id}/close`, `GET /shifts`, `GET /shifts/open`) —
  T-06-43…48, T-06-49…57, T-06-58…65 bilan qoplangan va uchalasi ham
  `TenantSessionDep` ostida cross-tenant matritsasiga **avtomatik** tushgan
  (`MINIMUM_MATRIX_ROUTES = 80`, amaldagi son **88**).
- **6 yangi jadval** — T-06-15…24.
- **Yangi `SECURITY DEFINER` funksiya: 0**; aksincha **ikkitasi DROP qilindi** (T-06-22).
- **Yangi rasm/fayl yuzasi: 0** — dalil kadri mavjud yagona proxydan (T-06-81).
- **Yangi paket: 0** (T-06-SC, `git diff` bilan tasdiqlangan).

---

## Findings — jarayon nuqsonlari (BLOCKER emas)

⚠ Quyidagilar **xavfsizlik bo'shlig'i emas**: uchala band ham hujjat sifatida
noaniqlik, kod emas. Ular audit izining to'liq bo'lishi uchun yoziladi.

| # | Topilma | Sinf | Ta'siri | Tavsiya |
|---|---------|------|---------|---------|
| F-1 | `06-13-SUMMARY.md` va `06-14-SUMMARY.md` da `## Threat Flags` bo'limi **umuman yo'q** (`grep -c "T-06-"` → **0/0**). Ya'ni 15 tahdid (T-06-80…T-06-94 + T-06-SC) ijrochi tomonidan **hech qachon attestatsiya qilinmagan** | Jarayon | Attestatsiya yo'qligi tahdid ochiqligini anglatmaydi: bu auditda o'sha 15 bandning **har biri** mustaqil ravishda kod ustida tekshirildi va **hammasi CLOSED**. Lekin darvoza ijrochi tomonida **ko'r** edi | Keyingi fazada SUMMARY andozasining `## Threat Flags` bo'limi bo'sh qolsa `/gsd-execute-phase` ni qizartirish (mexanik shart) |
| F-2 | `06-14-SUMMARY.md:226-256` «⛔ Byudjet — O'LCHANMADI» va «`nyquist_compliant` HAMON false» deb yozadi. Amaldagi holat **boshqa**: byudjet to'lqin 9 dan keyin uch marta o'lchangan (1703/1733/1899 s), `package.json:23` va `06-VALIDATION.md:75,94` da **2300 s**, `06-VALIDATION.md` frontmatterida `nyquist_compliant: true`, `check-validation-signoff.mjs` exit 0 | Hujjat eskirgan | T-06-92 **CLOSED** — dalil `package.json` + `06-VALIDATION.md` + `deferred-items.md` 7-bandida. SUMMARY o'z holatidan orqada qolgan va uni **so'zma-so'z o'qigan** keyingi ijrochi fazani ochiq deb hisoblardi | `06-14-SUMMARY.md` ning «Byudjet» va «Ochiq bandlar → 1» bandlariga yopilish eslatmasi qo'shilsin (hujjat tuzatishi, kod emas) |
| F-3 | `06-14-SUMMARY.md:116` `test_phase6_criteria.py` ni **1949 satr** deb yozadi; commit `553aefc` dagi haqiqiy son — **1978**. Shu bo'limda `inspect.getmembers` «2 ta» deyilgan, amalda **3 ta** | O'lchov drifti | Ikkala farq ham **kuchaytirish** yo'nalishida (ko'proq satr, ko'proq introspeksiya) — da'voni zaiflashtirmaydi | Sanoqlar SUMMARY yozilgandan keyingi hunk larda o'zgargan; keyingi fazada sanoq **oxirgi commitdan** olinsin |

---

## Verification Method — nima haqiqatan yugurtirildi

| Buyruq | Natija | Qaysi tahdidlarni yopadi |
|--------|--------|--------------------------|
| `docker compose --profile test run --rm tests pytest tests/integration/test_billing_immutable.py tests/tenancy/test_route_coverage.py -q` | **25 test, 0 fail** | T-06-15/16/19/25…29, T-06-47 chegarasi |
| `… pytest tests/integration/test_phase6_criteria.py tests/tenancy/test_personal_data_coverage.py tests/tenancy/test_occupancy_domain_meta.py -q` | **35 test, 0 fail** | T-06-05/06/22/44/81/88/89/91, SC#1…SC#5 |
| `… pytest tests/integration/test_payments_api.py test_shifts_api.py test_billing_api.py tests/tenancy/test_idempotency_concurrency.py test_cross_tenant.py -q` | **578 test, exit 0** | T-06-01, T-06-43…48, T-06-49…57, T-06-58…65 |
| `node --test frontend/scripts/{collect-surface,billing-copy,blind-payload,bulk-action-surface,error-codes}.test.mjs` | **66 test, 0 fail** | T-06-07/08/09/14/70/71/73/75 |
| `node scripts/check-requirements-sync.mjs` | **exit 0** (49 talab · Done 30 · Blocked 2) | T-06-93 |
| `node scripts/check-validation-signoff.mjs` | **exit 0**, `nyquist_compliant: true` hisob-kitobga mos | T-06-92 |
| `git diff <faza-boshi>..HEAD -- <barcha bog'liqlik manifestlari>` | **1 fayl, 2 izoh qatori** | T-06-SC |
| `git log -S 'SNAPSHOT_EVIDENCE_FRAME_ROUTES = ('` | oxirgi o'zgarish `795a63b` (**05-16**) | T-06-81 |
| `git status --porcelain tests/ services/ frontend/ migrations/ packages/` | **bo'sh** — sabotaj qoldig'i yo'q | T-06-90/91 |
| `df -h /c` | **14 GB bo'sh / 162 GB (92 %)** — ≥10 GB sharti bajarilgan | T-06-94 |

⛔ **O'zgartirilmagan fayllar:** bu audit `services/`, `frontend/`, `tests/`,
`migrations/`, `packages/` ostidagi **birorta faylga tegmadi**. Yagona yozuv —
shu fayl.

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-08-11 | 106 | 106 | 0 | gsd-security-auditor (ASVS L1) |

---

## Sign-Off

- [x] Har bir tahdidda disposition bor (104 mitigate · 2 accept · 0 transfer)
- [x] Qabul qilingan xavflar Accepted Risks Log da (AR-06-01, AR-06-02)
- [x] `threats_open: 0` tasdiqlandi
- [x] `status: verified` frontmatterda qo'yildi
- [x] Attestatsiyasiz 15 band (T-06-80…T-06-94 + T-06-SC) **nomma-nom** kod ustida tekshirildi
- [x] Ro'yxatga olinmagan bayroq (`unregistered_flag`) **yo'q**

**Approval:** verified 2026-08-11
