# 3-fazada topilgan, LEKIN DOIRADAN TASHQARIDAGI bandlar

> Bu bandlar 3-fazada **topildi** va **tuzatilmadi** — ular shu fazaning
> rejalaridagi fayllar to'plamidan tashqarida. Ular yo'qolib ketmasligi
> uchun shu yerda yozib qo'yilgan.

## 1. `ROADMAP.md` § Progress jadvalining 1- va 2-faza qatorlari eskirgan

**Topildi:** `03-11` (2026-08-03), Phase 3 qatorini yangilashda.

**Nima:** Jadval `1. Poydevor va tenant xavfsizligi | 0/10 | Planned` va
`2. Bozor domeni va ustasi | 0/17 | Planned` deydi, holbuki:

* 1-faza **bajarilgan** (`- [x] **Phase 1: ...** (completed 2026-07-29)`);
* 2-faza **bajarilgan** va faza ro'yxatida «24/24 reja bajarildi» deb
  yozilgan, jadvalda esa reja soni ham (`17`) eskirgan.

**Nega tuzatilmadi:** `03-11` ning doirasi Phase 3 qatori bilan
chegaralangan; boshqa fazalarning holatini shu rejadan yozish sanoqni
**uchinchi joyda** taxmin qilish bo'lardi (aynan `REQUIREMENTS.md` da
ikki oy yashagan drift shakli).

**Kim yopadi:** keyingi faza yopilishi yoki `roadmap update-plan-progress`
ni har faza uchun bir marta bajarish.

⚠ `node gsd-tools.cjs roadmap.update-plan-progress 03` `updated: true`
qaytardi, lekin jadval qatori **o'zgarmadi** — qator `3. <nom>` shaklida,
skript esa boshqa naqshni izlayotgan bo'lishi mumkin. Qator qo'lda
yangilandi. Skriptning o'zi ham tekshirilishi kerak.
