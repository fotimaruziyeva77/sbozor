# 10-faza — keyinga qoldirilgan bandlar

## 1. `-tsiya` → `тсия` semantik transliteratsiya defekti (meros katalog)

- **Sinf nomi:** `-tsiya` → `тсия` semantik transliteratsiya defekti — chiqish sof kirill bo'lgani uchun `gen-cyrillic.test.mjs` ning lotin-qoldiq darvozasi uni USHLAMAYDI (`_comment_semantic` bilan ayni sinf: `autentifikatsiya` → `аутентификатсия`).
- **O'lchangan holatlar** (10-RESEARCH B-3, mavjud katalog):
  - `Deklaratsiya` ×3 — `collect.shiftConfirmBody` → bugun `Декларатсия` (to'g'risi `Декларация`)
  - `deklaratsiya` ×1 — `billing.emptyShiftsHint` → bugun `декларатсия` (to'g'risi `декларация`)
- **Nega 10-fazada tuzatilmaydi:** scope boundary (08-20 presedenti) — bu 10-fazaning nuqsoni EMAS, meros katalogning defekti. 10-fazaning `landing.*` copy'si esa toza yozildi (`demonstratsiya` → `namoyish`, boshqa `-ts[iy]` token 0 — o'lchandi).
- **Darvoza chegarasi:** 10-07 dagi G-land-4(g) hosila skani shu sababdan **`landing.*` bilan CHEGARALANADI** — kengroq yozilsa u shu meros defektdan qizarib, 10-fazani o'z aybisiz bloklaydi.
- **Egasi:** keyingi i18n ishi (alohida copy-tuzatish yoki override juftligi: `Deklaratsiya`/`deklaratsiya` + qo'shimchali shakllar).
- **Tetigi:** rus/kirill UAT'i — kirill o'quvchi `Декларатсия` ni ko'rgan birinchi tekshiruv.
