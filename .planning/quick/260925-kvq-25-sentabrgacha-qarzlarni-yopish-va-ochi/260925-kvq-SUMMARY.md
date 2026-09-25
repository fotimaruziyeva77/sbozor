---
quick_id: 260925-kvq
phase: quick
plan: 260925-kvq
subsystem: billing
tags: [billing, reconciliation, ops, director-waiver, settlement, map]
status: complete

provides:
  - "`ops/scripts/settle_debts.py` — chegara kunidan oldingi qarzlarni «Direktor kechirdi» tuzatishi bilan yopish; standart holatda quruq yugurish (amal bajariladi va ROLLBACK)"
  - "`app/jobs/debt_settlement.py` — `plan_market_settlement()`, `settle_market()` (qulf -> reja -> yozish -> invariant), `market_directors()`, `pick_decision_maker()`"
  - "`billing_repo`: `settlement_charge_dues()`, `settlement_credit()` (storno asl to'lov kuniga), `write_director_waiver()`"
  - "`reconciliation_repo.pending_cases_before()`"

key-files:
  created:
    - ops/scripts/settle_debts.py
    - services/core-api/app/jobs/debt_settlement.py
    - tests/integration/test_debt_settlement.py
  modified:
    - services/core-api/app/repositories/billing_repo.py
    - services/core-api/app/repositories/reconciliation_repo.py
    - docs/KAMCHILIKLAR-REESTRI.md

key-decisions:
  - "Soxta to'lov YOZILMAYDI — `charge_adjustments` (`decrease`, `director_waiver`), aktor bozor direktori; audit DB-triggerdan"
  - "Eski davr krediti — to'lov YOZILGAN kun (`business_date < D`), storno asl to'lovning kuniga; bugungi to'lov va eski avans tegilmaydi"
  - "Kechiriladigan summa mahsulot qoidasidan (`allocate_charge_credit`, FIFO) — faqat eski to'lov yopmagan qoldiq"
  - "D dan oldingi hamma hal qilinmagan ish (ikkala sinf) -> `unjustified` («Asossiz») + izoh, `transition()` orqali"
  - "Qaror egasi taxmin qilinmaydi: bozorda yagona faol direktor yoki `SETTLE_DIRECTOR_PHONE`"
  - "`SETTLE_BEFORE` majburiy, standart qiymatsiz; bugundan keyin bo'lolmaydi"

completed: 2026-09-25
---

# Quick 260925-kvq: 25-sentabrgacha bo'lgan qarzlarni yopish va ochiq ishlarni yopish

**Buyurtmachi qarori: 25-sentabrdan oldingi qarzlar to'langan deb hisoblanadi, bugundan tizim
odatdagidek. Bunga soxta to'lovsiz erishiladi: har eski hisobning eski to'lovlar yopmagan qoldig'i
«Direktor kechirdi» tuzatishi bilan kamayadi, eski ochiq ishlar «Asossiz» bo'lib yopiladi — xaritadagi
sariq yo'qoladi, kassir ekranida eski qarz ko'rinmaydi. Bugungi to'lovlar bugungi pattaga qoladi,
avanslar o'zgarmaydi; 25-sentabr pattasi to'lanmasa, 28-sentabr ertalab odatdagidek sariq bo'ladi.**

## Qanday ishlaydi

1. Bozor boshiga bitta tranzaksiya: `pg_advisory_xact_lock` -> reja -> yozish -> invariantlar.
2. Reja: `service_date < D` hisoblar (mavjud tuzatishlar bilan netlangan) + `business_date < D`
   kredit (storno asl to'lov kuniga) -> `allocate_charge_credit()` -> har `unpaid_soum > 0` qator
   uchun `director_waiver` tuzatishi.
3. `service_date < D` bo'lgan barcha `new`/`in_review` ishlar -> `unjustified` + izoh
   (`reconciliation_repo.transition()`: tarix qatori, direktor aktor, audit).
4. Invariantlar (buzilsa ROLLBACK): eski hisoblarning nettosi manfiy emas;
   `vendor_outstanding(as_of=D) <= 0` har sotuvchida; D dan oldingi ochiq ish qolmagan.
5. Quruq yugurish AYNI amalni bajaradi va ROLLBACK qiladi — hisobot yozish natijasining o'zi,
   konstrayt/trigger/FK ham o'lchanadi.

## Commitlar

| Commit | Mazmun |
|---|---|
| `a3a618e` | `debt_settlement` + `settle_debts.py` + repo funksiyalari + 15 ta integratsiya testi |

## Tekshiruv (2026-09-25, lokal Docker)

- `tests/integration/test_debt_settlement.py` — **15/15 yashil** (haqiqiy `postgres:18.4`):
  to'liq kechirish soxta to'lovsiz; audit qatori (direktor, `user`, `request_id`); FIFO —
  faqat qoldiq; bugungi to'lov eski qarzga ketmaydi va bugungi pattani yopadi; eski avans
  o'zgarmaydi; eski to'lovning bugungi stornosi eski davrga; chegara kuni tegilmaydi; ikkinchi
  bozor tegilmaydi; ishlar «Asossiz» + izoh + bitta tarix qatori + direktor, yopiq ish
  tegilmaydi; `recon.open` yopilgan davrga yangi ish ochmaydi; qayta yugurish 0 yozadi;
  skriptning quruq yugurishi saqlamaydi, `apply` saqlaydi; oldindan manfiy hisob — aniq xato
  bilan to'xtash; qaror egasi taxmin qilinmaydi.
- **Mutatsiya:** storno qoidasi ataylab buzilganda (`COALESCE(o.business_date, ...)` olib
  tashlandi) storno testi qizardi va yakuniy invariant yozuvni ROLLBACK qildi; fayl tiklandi
  (`cmp` bilan tasdiqlangan).
- `ruff check`, `ruff format --check`, `mypy` (strict) — o'zgargan fayllarda toza.
- Lokal dev bazada quruq yugurish: ikki faol direktorli bozorda nomzodlar ro'yxati bilan
  to'xtadi; direktor tanlanganda hisobot chiqdi, hech narsa saqlanmadi.

## Rejadan chetlanishlar

1. **Qaror egasining xabari.** Lokal dev bazada quruq yugurish «2 ta faol direktor» bilan to'g'ri
   to'xtadi, lekin xabarda nomzodlar va bozor nomi yo'q edi — operator qaysi telefonni berishni
   bilmasdi. Xabarga nomzodlar (ism + telefon) va bozor nomi qo'shildi.

## Prod'da bajarish (buyurtmachi, `/srv/sbozor` ichida)

1. `git fetch origin && git reset --hard origin/main`
2. `docker compose -f deployment/compose.yaml -f deployment/compose.prod.yml up -d --build core-api worker scheduler`
3. Quruq yugurish: `docker exec -i -e SETTLE_BEFORE=2026-09-25 sbozor-core-api-1 python - < ops/scripts/settle_debts.py`
4. Zaxira: `docker exec sbozor-db-1 sh -c 'pg_dump -U "$POSTGRES_USER" -Fc "$POSTGRES_DB"' > /srv/sbozor-baza-20260925.dump`
5. Saqlash: 3-qadam + `-e SETTLE_APPLY=1` (kerak bo'lsa `-e SETTLE_DIRECTOR_PHONE=+998...`).

## Ochiq qoldi

- Eski davrning to'lovi keyinroq bekor qilinsa (storno), o'sha summa qarz bo'lib qaytadi —
  skriptni qayta yurgizish (konvergent) uni yana yopadi.
- P-12 / P-13 (zonali rastalar, kadrsiz kun) — buyurtmachi qarori kutilmoqda.
