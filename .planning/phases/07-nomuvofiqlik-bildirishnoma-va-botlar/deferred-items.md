# 7-faza — keyinga qoldirilgan bandlar

Bu fayl ijro davomida topilgan, lekin **joriy rejaning qamrovidan
tashqaridagi** bandlarni qayd etadi. Ular tuzatilmaydi — egasi
belgilanadi.

---

## 1. `ALERT_TITLE_KEYS` uchala locale bilan MEXANIK bog'lanmagan

**Topildi:** 07-15 ijrosi, `frontend/node_modules` birinchi marta
o'rnatilgandan keyingi to'liq o'lchovda.

**Fayl:** `frontend/src/components/snapshots/alert-row.tsx:107-124`

**Holat — O'LCHANDI, hammasi TOZA:**

| O'lchov | Natija |
|---|---|
| `ALERT_TITLE_KEYS` a'zolari | **15** |
| 15 kalit × 3 locale matni mavjudmi | ⛔ **HAMMASI BOR** — yetishmagani **0** |
| `alert-list.test.tsx` ni yugurtirish | **yashil** (to'liq to'plamning bir qismi) |

**Bo'shliq:** yuqoridagi «15 × 3» tekshiruvi ⛔ **qo'lda** bajarildi.
`frontend/scripts/*.test.mjs` ichida `ALERT_TITLE_KEYS` ni
`messages/*.json` bilan bog'laydigan **birorta darvoza yo'q**
(`grep -n "alertKey\|ALERT_TITLE" frontend/scripts/*.test.mjs` → **0**).

Ya'ni: 07-08 (uchala locale matni) va 07-14 (to'rt yangi a'zo) ning
ishi **bugun to'g'ri**, lekin uni ushlab turadigan mexanizm **yo'q** —
o'n oltinchi a'zo matnsiz qo'shilsa, ekranda zaxira yorliq chiqardi va
buni **hech nima aytmasdi**. Bu `error-codes.test.mjs` (G-17) allaqachon
yopgan sinfning aynan o'zi, faqat boshqa reyestr ustida.

**Qo'shimcha:** `alert-list.test.tsx` 07-14 ning to'rt yangi kalitidan
(`outbox_stale`, `reconciliation_stale`, `digest_stale`, `overdue_stale`)
**birortasini ham render qilmaydi** — ya'ni ular **chizilgan holda**
o'lchanmagan.

**Nega 07-15 da tuzatilmadi:** fayl `components/snapshots/**` da va
07-15 ning fayl to'plamidan **tashqarida**; tuzatish `snapshot-copy.test.mjs`
ga yangi blok qo'shishni talab qiladi.

**Egasi:** 07-17 (faza yakuni) yoki 8-faza. Shakli tayyor:
`error-codes.test.mjs` ning `RECON_ERROR_CODES` bloki — reyestrdan
**oldinga** (kalit → matn) va **teskari** (matn → kalit) yuradigan
o'n besh qatorlik naqsh.

---

## 2. `/reconciliation` sahifasi ikkita qo'shimcha so'rov qiladi

**Manba:** 07-UI-SPEC §5.5 ning **o'z** ochiq narxi.

Sotuvchi ismi klientda `GET /vendors` bilan joinlanadi
(`lib/vendor-labels.ts`) va reestrning **birinchi sahifasi** bilan
cheklanadi. 50 dan ortiq sotuvchili bozorda ro'yxatning quyi qismidagi
qatorlar «Ko'rsatilmagan» yorlig'ini olishi mumkin.

⛔ **To'g'ri tuzatish — MAVJUD marshrutni sahifalash**, nomuvofiqlik
marshrutiga ism maydoni **qo'shish EMAS** (07-10 buni sabotaj bilan
o'lchagan: ism qo'shilganda to'rt tenancy testi qizaradi).

**Egasi:** 8-faza (§5.5 shu bandni `deferred-items.md` ning 9-bandi
bilan bir sinfga qo'ygan).
