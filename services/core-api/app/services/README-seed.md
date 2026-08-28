# Urug' rejimi — dataset qanday yig'iladi

> `review_seed.py` ning yonidagi izoh. Model o'qitish kuni bu fayl
> «nima yig'ildi va u qayerda?» savoliga javob beradi.

---

## Muammo

Nazoratchi navbati AI hodisasidan quriladi
(`review_assignments.occupancy_event_id` — `NOT NULL`), hodisani esa
modeli bor `cv-service` yozadi. Model o'qitish uchun dataset kerak,
dataset nazoratchi javoblaridan yig'iladi:

```
model → hodisa → navbat → javob → dataset → model
```

Halqa yopiq. Birinchi kunda model ham, dataset ham yo'q — ya'ni tizim
o'zi boshlana olmasdi.

## Yechim

Hodisa **modelsiz** yoziladi, lekin uni model qarori deb ko'rsatmaydigan
uchta belgi bilan:

| Maydon | Qiymat | Nega |
|---|---|---|
| `verdict` | `uncertain` | tizim BILMAYDI |
| `confidence` | `0.0` | taxmin ham qilinmagan (`uncertain` oynasining o'rtasi 0.45 EMAS) |
| `model_version` | `seed-v0` | hisobotda ko'rinadi — model bilan adashtirilmaydi |

Bu hodisa `uncertain` navbatiga tabiiy tushadi
(`ix_occupancy_events_uncertain` indeksi), nazoratchi esa mavjud
ekranda — kadr + zona konturi + «Band / Bo'sh / Aniq emas» — javob
beradi.

## Kunlik oqim

```
kadr olindi (quality_verdict='ok')
        │
        ▼
seed_snapshot()  ──►  occupancy_events (uncertain, seed-v0)
   kadr x faol zona          │
   BIR TRANZAKSIYADA         ▼
                      review_assignments (uncertain, train)
                             │
                             ▼
                   nazoratchi ekrani (/uz/review/uncertain)
                             │
                             ▼
                      zone_reviews  ◄── DATASET SHU YERDA
```

## Dataset nimadan iborat

`zone_reviews` qatori + unga bog'langan zanjir:

| Nima | Qayerdan |
|---|---|
| Rasm | `snapshots.object_key` → S3 |
| Zona konturi | `camera_zones.polygon` (normalangan 0..1) |
| Zona versiyasi | `occupancy_events.zone_version` — kontur keyin o'zgarsa ham qaysi biri edi |
| Inson javobi | `zone_reviews.human_verdict` |
| Kim va qachon | `reviewer_id`, `decided_at`, `decision_ms` |
| Ko'rsatilganmi | `shown_ai_verdict` — urug'da doim `false` |

Ya'ni o'qitish uchun kerakli hamma narsa bazada. Eksport
(`.jsonl` + kesilgan rasmlar) — o'qitish kunidagi bir soatlik ish.

## Nimaga tegmaydi

⛔ **Aniqlik hisobiga tushmaydi.** U faqat `blind_audit` + `purpose='eval'`
dan hisoblanadi (`accuracy_report.py`), urug' esa `uncertain` + `train`
yozadi. Aks holda model yo'q holatda «tizim aniqligi 87%» degan son
paydo bo'lardi va u nazoratchining javobini o'ziga solishtirgan
bo'lardi.

⛔ **Patta hisobiga tushmaydi.** `billable_from_slots()` qoidasi
o'zgarmaydi: 2 slot `occupied` yoki 1 slot + nazoratchi tasdig'i.
`uncertain` verdikt band deb sanalmaydi, ya'ni urug' hech kimga patta
yozdirmaydi.

## Model paydo bo'lgan kun

1. `ops/models/rfdetr-large.onnx` joyiga qo'yiladi
2. `OCCUPANCY_SEED_MODE=false`
3. `cv-service` ko'tariladi

Ikkalasi birga ishlamasin: `uq_occupancy_events_..._model` kalitida
`model_version` bor, ya'ni baza ikkita qarorni RAD ETMAYDI va patta
hisobi qaysi birini olishini bilmasdi.

Eski `seed-v0` qatorlari **qoladi** — ular dataset va ularni o'chirish
o'qitish tarixini yo'q qilardi.
