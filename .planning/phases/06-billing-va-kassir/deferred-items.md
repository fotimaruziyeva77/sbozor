# Phase 6 — kechiktirilgan bandlar

Ijro paytida topilgan, LEKIN joriy rejaning qamrovidan **tashqaridagi** narsalar.
Ijrochi qoidasi: faqat joriy vazifaning O'ZGARISHLARIDAN kelib chiqqan nosozlik
avtomatik tuzatiladi; qolgani shu yerga yoziladi va **tegilmaydi**.

| # | Topilma | Qayerda topildi | Sinf | Nima qilish kerak |
|---|---------|-----------------|------|-------------------|
| 1 | `tests/integration/test_blind_audit.py::test_a_different_round_number_draws_a_different_sample` — **FLAKY**. To'liq to'plamning bir yugurishida `AssertionError: Both sets are equal` bilan qizardi, boshqa yugurishida yashil; izolyatsiyada (33/33) va yolg'iz qayta yugurganda ham yashil. | 06-06 ijrosi, `pytest -q` (to'liq to'plam) | 5-fazadan meros, ehtimoliy da'vo | Namuna hajmi nomzodlar havzasiga yaqin bo'lganda ikki har xil urug' **bir xil** to'plamni berishi mumkin — ya'ni «tur raqami namunani o'zgartiradi» da'vosi determinlashtirilgan emas. Yechim yo'nalishi: seedni kengaytirib nomzodlar havzasini kattalashtirish (05-15 ning S-D darsi: da'vo susaytirilmaydi, **HOLAT** kengaytiriladi), yoki da'voni «urug' `ORDER BY` ifodasiga kiradi» degan strukturaviy shaklga o'tkazish. ⚠ 06-06 unga **tegmadi**: bu reja birorta bandlik/audit fayliga tegmaydi. |

| 2 | `day_close` ning yurak urishi `system_heartbeats` ga YOZILADI (`DAY_CLOSE_COMPONENT`), lekin uning **YO'QLIGI** hech qayerda ko'rinmaydi: u `self_check.EXPECTED_COMPONENTS` da ham, `alerting._platform_signals::watched` da ham YO'Q. Ya'ni `occupancy.day_close` cron'i ro'yxatga olinmasa (deployda `scheduler` qayta ishga tushirilmasa) nosozlik JIMGINA qoladi. | 06-07 ijrosi, Task 3 (M-C) | 5-faza domeni, 6-fazaning qamrovidan tashqarida | Ikki qatorlik o'zgarish: `EXPECTED_COMPONENTS` ga `"day_close"` va `watched` ga `(DAY_CLOSE_COMPONENT, "day_close_stale")` + `ALERT_META` yozuvi + uchala locale matni. ⚠ 06-07 unga **ATAYIN tegmadi**: `day_close` ning yurak urishi 5-fazadagi testlar bilan o'lchanadi va reyestrga qo'shilishi ularning kutilmasini ham siljitardi — 6-fazani 5-fazaning qarziga bog'lardi. Sabab `self_check.py::EXPECTED_COMPONENTS` docstringida OCHIQ yozilgan. |
| 3 | `gate` ning **frontend yarmi** bu worktree'da yugurmaydi (`frontend/node_modules` yo'q). 06-07 uchta locale fayliga va `alert-row.tsx` ga matn qo'shdi, ya'ni `billing-copy` / `alert-list` darvozalari o'lchanmagan. | 06-07 ijrosi, Task 3 | infratuzilma (worktree), mahsulot emas | Asosiy checkout'da `npm test` yugurtirilishi kerak. ⛔ Junction/symlink **YARATILMAYDI** (o'sha xatolik ilgari asosiy checkout'ning `node_modules` ini yo'q qilgan), `npm ci` esa paket-menejer amali va ijrochi qoidasi bo'yicha avto-tuzatishdan chiqarilgan. O'zgarish mexanik (bitta kalit + uchta satr), lekin **o'lchanmagan**. |

---
*Phase: 06-billing-va-kassir*
