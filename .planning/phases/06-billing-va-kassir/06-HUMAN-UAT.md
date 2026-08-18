---
status: partial
phase: 06-billing-va-kassir
source: [06-VERIFICATION.md]
started: 2026-08-11T08:24:54Z
updated: 2026-08-11T08:24:54Z
---

## Current Test

[inson tekshiruvi kutilmoqda]

## Tests

### 1. Dalil kadrining nizoda O'QILISHI
expected: Direktor `GET /snapshots/{id}/image` orqali ochilgan kadrni ko'rib, u orqali sotuvchi bilan nizoni hal qila oladi — kadrda rasta ko'rinadi, sotuvchi uni tanib oladi va kadr nizoda ishonch uyg'otadi.
result: [pending]
why_human: Zanjir oxirigacha mexanik o'lchangan va yashil (`daily_charges` → `charge_evidence` → `occupancy_events.snapshot_id` → `GET /snapshots/{id}/image`, 200 + `image/jpeg` + aynan o'sha baytlar, HAQIQIY SeaweedFS ustida — `test_sc2_charge_reaches_evidence_and_cannot_be_edited`). O'lchanmagani — **inson idroki**: kadr sifati va burchagi haqiqiy nizoda yetarlimi.
owner: Direktor + bozor admini
trigger: Karmananing birinchi real kadrlari kelganda (Phase 0 artefakti)

### 2. Kassir oqimining REAL TELEFONDA bajarilishi
expected: Kassir jonli qurilmada barmoq bilan bosa oladi, klaviatura ekranni qoplamaydi, oqim bir qo'lda bajariladi va ekran quyosh ostida ko'rinadi.
result: [pending]
why_human: ≤3 bosish DOM'dan **hosila** sanoq bilan o'lchangan (`collect-session.test.tsx` — baxtli yo'lda 3, ko'p moslikda 4, ikkalasi ham alohida assert bilan qulflangan, ya'ni sanoq qotirilgan emas). Lekin jsdom brauzer emas: tegish nishoni o'lchami sinf sifatida bor (`min-h-11` / `min-h-14`), real qurilmada bosish, klaviatura qoplashi va yorug'lik sharoiti o'lchanmagan.
owner: Kassir
trigger: Pilot tayyorgarligi haftasi — Karmana kassirining o'z telefonida

### 3. Ko'r deklaratsiyaning AMALIY ko'rligi
expected: Kassir smenani yopganda faqat o'zi sanagan naqdga tayanadi va boshqa hech qanday tashqi yozuvdan (qog'oz daftar, o'z xotirasi) foydalanmaydi.
result: [pending]
why_human: To'rt **mustaqil** strukturaviy qatlam o'lchangan va kodda tasdiqlangan — backend javobida `system_*` maydoni umuman e'lon qilinmagan (kalitlar to'plami tengligi), klientda `z.strictObject` (server qo'shsa parse vaqtida yiqiladi), `components/collect/**` katalogining statik token skani, va ekranda aynan uchta natija elementi (kesh tozalanib qayta chizilgandan keyin ham). O'lchanmagani — **tashkiliy shart**, texnik emas.
owner: Direktor
trigger: Parallel rejimning birinchi haftasi (hafta 13)

### 4. Sabab-kodlarning amalda TO'G'RI tanlanishi
expected: Kassir «boshqa» varianti yo'qligida vaziyatga eng mos sabab-kodni tanlaydi va bu tanlov keyingi hisobotda mazmunli guruhlanadi.
result: [pending]
why_human: Yopiq ro'yxat (`ReversalReason` / `AdjustmentReason`, `other` a'zosi **ataylab yo'q**) va 422 darvozasi (sabab-kodsiz chetlanish rad etiladi) HTTP darajasida o'lchangan. O'lchanmagani — kassirning real vaziyatda **qaysi** sababni tanlashi; bu pilotning birinchi oyida sabab taqsimoti hisobotidan kuzatiladi.
owner: Direktor + kassir
trigger: Pilotning birinchi oyi

## Summary

total: 4
passed: 0
issues: 0
pending: 4
skipped: 0
blocked: 0

## Gaps
