---
quick_id: 260925-kvq
type: quick
mode: quick (orchestrator inline — rejalash va bajarish bitta kontekstda)
created: 2026-09-25
status: complete
---

# Quick 260925-kvq: 25-sentabrgacha bo'lgan qarzlarni yopish va ochiq ishlarni yopish

Buyurtmachi qarori (2026-09-25): «bugundan boshlab hisoblasin, qolgan kunlarning qarzlarini
to'langan qilamiz, bugun to'lanmasa — shunaqa bo'lsin».

## Kontekst (prod, 2026-09-24/25)

- 28-avgust–23-sentabr hisoblari `backfill_charges.py` bilan tiklandi (726 hisob). Kassir o'sha
  kunlarda pattani ko'rmagan, ya'ni «qarz» ma'muriy tiklashning natijasi.
- `recon.open` (04:25) tiklangan to'lanmagan hisoblar uchun `occupied_unpaid` ishlarini ochdi —
  xaritada o'nlab sariq rasta, kassirga qo'ng'iroqlar.
- Qarzni kamaytirishning UI/API yo'li YO'Q (`charge-detail-dialog` faqat o'qiydi).

## Qarorlar

1. **Mexanizm — `charge_adjustments`, `decrease`, sabab `director_waiver`** (yopiq ro'yxatda
   bor, ekranda «Direktor kechirdi»). Soxta to'lov YOZILMAYDI: `payments` naqd pul yozuvi —
   smena deklaratsiyasi, kassa daftari va kvitansiya undan o'qiydi, soxta qator kassani buzardi.
   `actor_user_id` — bozor DIREKTORI («kim qaror qildi?» savolining halol javobi); audit
   qatorini DB-trigger yozadi (`BILLING_AUDITED_TABLES`).
2. **Kredit chegarasi — to'lovning O'Z kuni.** Eski davr krediti = `business_date < D` bo'lgan
   to'lovlar; storno ASL to'lovning kuniga tegishli. Bugungi (va keyingi) to'lovlar tegilmaydi —
   ular bugungi pattani yopadi; eski davrdan qolgan avans o'zgarmaydi.
3. **Qaysi hisob qancha kamayadi — mahsulot qoidasi** `allocate_charge_credit()`
   (`FIFO_OLDEST_SERVICE_DATE_FIRST`): eski kredit eng eski kunlarni yopadi, har eski hisobning
   YOPILMAGAN qoldig'i aynan shu summaga kamaytiriladi. Natija: `vendor_outstanding(as_of=D)`
   har sotuvchida `<= 0`.
4. **Ishlar — `service_date < D` bo'lgan barcha `new`/`in_review` ishlar** (ikkala sinf:
   xarita sarig'i ikkalasidan chiqadi) `unjustified` («Asossiz») holatiga, izoh bilan,
   `reconciliation_repo.transition()` orqali (tarix qatori + audit). «Asossiz» — «to'langan deb
   hisoblandi» qarorining ma'nosi: «to'lovsiz» da'vosi tasdiqlanmadi. Aniqlik ulushi `service_date`
   oynasida hisoblanadi, ya'ni D dan keyingi davr ko'rsatkichiga ta'sir yo'q.
5. **Xavfsizlik:** standart holatda quruq yugurish (READ ONLY tranzaksiya); yozish faqat
   `SETTLE_APPLY=1` bilan; bozor boshiga BITTA tranzaksiya + `pg_advisory_xact_lock` (ikki
   parallel yugurish ikki marta kamaytira olmaydi); reja qulf ICHIDA qayta hisoblanadi;
   konvergent (qayta yugurish hech narsa yozmaydi); yakuniy invariantlar buzilsa — rollback.
   `D` bugundan keyin bo'lishi mumkin emas va u MAJBURIY (standart qiymat yo'q — keyingi kun
   yugurtirilsa jimgina ko'proq kun kechirilmasin).

## Task 1 — Mahsulot qatlami

files:
- services/core-api/app/repositories/billing_repo.py — `settlement_charge_dues()`,
  `settlement_credit()`, `write_director_waiver()`, `old_negative_dues()` (belgili ifodalar
  QAYTA ISHLATILADI, ikkinchi nusxa yozilmaydi).
- services/core-api/app/jobs/debt_settlement.py (yangi) — `plan_market_settlement()`,
  `settle_market()`, `market_directors()`, izoh matnlari.

## Task 2 — Ops skripti

files:
- ops/scripts/settle_debts.py (yangi) — `SETTLE_BEFORE` (majburiy), `SETTLE_APPLY=1`,
  `SETTLE_DIRECTOR_PHONE` (bozorda bittadan ko'p/kam faol direktor bo'lsa), `SETTLE_MARKET_ID`
  (ixtiyoriy); sotuvchi kesimida hisobot, ishlar kun/sinf kesimida.

## Task 3 — Integratsiya testlari (haqiqiy postgres:18.4)

files:
- tests/integration/test_debt_settlement.py (yangi)

verify:
- qarz to'liq kechiriladi, soxta to'lov yozilmaydi (`payments` soni o'zgarmaydi);
- eski to'lov qisman yopgan hisob — faqat qoldiq kamayadi (FIFO);
- bugungi to'lov eski qarzga ketmaydi, avans o'zgarmaydi;
- eski to'lovning bugungi stornosi eski kunga tegishli;
- `D` va undan keyingi hisoblar/ishlar tegilmaydi;
- ochiq ishlar `unjustified` + izoh + tarix qatori + direktor aktor; yopiq ishlar tegilmaydi;
- quruq yugurish hech narsa yozmaydi; qayta yugurish 0 yozadi;
- `recon.open` yopilgan davr uchun yangi ish ochmaydi;
- ikkinchi bozorga tegmaydi;
- ruff + ruff format + mypy toza.

## Task 4 — Hujjat va chiqarish

- SUMMARY.md, STATE.md, `docs/KAMCHILIKLAR-REESTRI.md` (qaror qayd etiladi);
- commit + push; serverda: `git fetch && git reset --hard origin/main`, quruq yugurish,
  zaxira, yozish.
