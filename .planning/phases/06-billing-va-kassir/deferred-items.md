# Phase 6 — kechiktirilgan bandlar

Ijro paytida topilgan, LEKIN joriy rejaning qamrovidan **tashqaridagi** narsalar.
Ijrochi qoidasi: faqat joriy vazifaning O'ZGARISHLARIDAN kelib chiqqan nosozlik
avtomatik tuzatiladi; qolgani shu yerga yoziladi va **tegilmaydi**.

| # | Topilma | Qayerda topildi | Sinf | Nima qilish kerak |
|---|---------|-----------------|------|-------------------|
| 1 | `tests/integration/test_blind_audit.py::test_a_different_round_number_draws_a_different_sample` — **FLAKY**. To'liq to'plamning bir yugurishida `AssertionError: Both sets are equal` bilan qizardi, boshqa yugurishida yashil; izolyatsiyada (33/33) va yolg'iz qayta yugurganda ham yashil. | 06-06 ijrosi, `pytest -q` (to'liq to'plam) | 5-fazadan meros, ehtimoliy da'vo | Namuna hajmi nomzodlar havzasiga yaqin bo'lganda ikki har xil urug' **bir xil** to'plamni berishi mumkin — ya'ni «tur raqami namunani o'zgartiradi» da'vosi determinlashtirilgan emas. Yechim yo'nalishi: seedni kengaytirib nomzodlar havzasini kattalashtirish (05-15 ning S-D darsi: da'vo susaytirilmaydi, **HOLAT** kengaytiriladi), yoki da'voni «urug' `ORDER BY` ifodasiga kiradi» degan strukturaviy shaklga o'tkazish. ⚠ 06-06 unga **tegmadi**: bu reja birorta bandlik/audit fayliga tegmaydi. |

---
*Phase: 06-billing-va-kassir*
