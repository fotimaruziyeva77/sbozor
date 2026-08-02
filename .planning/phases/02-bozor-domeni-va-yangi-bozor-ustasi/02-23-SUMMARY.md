---
phase: 02-bozor-domeni-va-yangi-bozor-ustasi
plan: 23
subsystem: testing
tags: [xlsx, import, scale, fixtures, determinism, sabotage, validation-signoff, runbook, gap-closure, gate]

# Dependency graph
requires:
  - phase: 02-bozor-domeni-va-yangi-bozor-ustasi
    provides: "02-12 — xavfsiz `.xlsx` o'qish (`xlsx_reader`), `import_validator`, all-or-nothing tranzaksiya, D-15 qayta-import himoyasi va `test_stall_import.py` ning 24 testi"
  - phase: 02-bozor-domeni-va-yangi-bozor-ustasi
    provides: "02-17 — `ops/data/karmana/README.md` runbook'i, `scripts/karmana-import.mjs` va `test_phase2_criteria.py` (FAQAT HTTP orqali usta oqimi naqshi)"
  - phase: 02-bozor-domeni-va-yangi-bozor-ustasi
    provides: "02-21 — usta 1-qadamidagi `open_weekdays` (WR-06) va WR-05 registr-farqli dublikat qo'riqchisi"
  - phase: 02-bozor-domeni-va-yangi-bozor-ustasi
    provides: "02-22 — `scripts/check-requirements-sync.mjs` ning `node:`-only vosita uslubi; 02-24 — `_SAMPLE_PHONE` defektining tuzatilishi (`+` va `escape_formula` chegarasi)"
provides:
  - "`tests/fixtures/karmana_seed.py` — Karmana miqyosidagi (8 zona / 600 rasta / 480 sotuvchi) IFLOS `.xlsx` generatori; quvurning shablon yo'lidan BUTUNLAY mustaqil"
  - "Generatorning E'LON qiladigan kutilmalari: `expected_stall_issues()`, `expected_vendor_issues()`, `clean_stall_rows()`, `clean_vendor_rows()`, `blank_stall_rows()`"
  - "Bayt darajasidagi determinizm: `random.Random(SEED)` + `_freeze_zip()` (XlsxWriter ZIP sanasini SOATdan oladi)"
  - "`tests/unit/test_karmana_seed.py` — 15 test, shu jumladan `ast` bilan qurilgan mustaqillik darvozasi (T-02-165)"
  - "`tests/integration/test_karmana_scale_import.py` — 11 bosqichli uchidan-uchiga miqyos isboti, FAQAT HTTP orqali"
  - "`frontend/.../stall-map.test.tsx` — 8 zona × 75 katak miqyos testi (600 katak, kodlar to'plami serverdagi bilan aynan teng)"
  - "`scripts/check-validation-signoff.mjs` — `nyquist_compliant` bayrog'ining mexanik darvozasi (4 qoida)"
  - "`ops/data/karmana/README.md` — darvoza emas, OPERATSION tartib; quruq mashq bo'limi va O'LCHANGAN chegaralar"
  - "`02-VALIDATION.md` — «Verification triage»: 2 band avtomatlashtirildi, 4 band egasi va sharti bilan inson bandiga aylantirildi; Per-Task xaritasi 71 qator"
  - "`package.json` — `karmana:sample`, `validation:check`, `requirements:check`"
affects: [02-VERIFICATION qayta tekshiruvi, 03-nvr, 04-snapshot, 06-billing]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Test yuki MAHSULOT generatoridan mustaqil quriladi; mustaqillik `ast` bilan (grep emas) qulflanadi — docstring taqiqning SABABINI literal aytadi va grep uni o'z-o'ziga qarshi qo'yardi"
    - "Kutilgan natijani FIXTURE e'lon qiladi, test qayta hisoblamaydi; solishtiruv IKKI TOMONLAMA tenglik — kutilmagan xato ham nomuvofiqlik"
    - "Toza variant iflosning FILTRLANGAN ko'rinishi, ikkinchi ro'yxat emas — ikki ro'yxat bir kun ajralib ketardi"
    - "Bayt determinizmi ikki qatlamda: urug'langan RNG + ZIP metama'lumotini muzlatish (`writestr` sanani soatdan oladi)"
    - "Miqyos testi BITTA funksiyada — bosqichlar bir-biriga bog'langan va bo'lish 600 qatorlik importni takrorlashni talab qilardi"
    - "Hujjat bayrog'i KELISHUV emas, HISOB-KITOB: skript qoidani majburlaydi va bayroq bilan hisob-kitob ajralsa exit 1"
    - "«Avtomatlashtirib bo'lmaydi» da'vosi hech qachon bepul emas — `owner` va `trigger` MAJBURIY va ular skript bilan tekshiriladi"
    - "Runbook fazani bloklamaydi: tashqi bog'liqlik `Blocks:` emas, keyin to'ldiriladigan ma'lumot"

key-files:
  created:
    - tests/fixtures/karmana_seed.py
    - tests/unit/test_karmana_seed.py
    - tests/integration/test_karmana_scale_import.py
    - scripts/check-validation-signoff.mjs
  modified:
    - frontend/src/components/stalls/stall-map.test.tsx
    - ops/data/karmana/README.md
    - package.json
    - .planning/phases/02-bozor-domeni-va-yangi-bozor-ustasi/02-VALIDATION.md

key-decisions:
  - "Mustaqillik darvozasi `grep` emas, `ast` bilan qurildi — reja `grep -c \"xlsx_template\" = 0` ni talab qilardi, lekin O'ZI docstringda taqiqning sababini LITERAL yozishni ham talab qilardi; ikkalasi bir vaqtda mumkin emas, `ast` esa qat'iyroq (import satrini nomdan qat'i nazar ushlaydi)"
  - "`_freeze_zip()` qo'shildi — `XlsxWriter` `in_memory` rejimida `ZipFile.writestr()` ni ishlatadi va u a'zo sanasini SOATdan oladi; usiz «baytlar aynan teng» testi sekundlar chegarasida GOHIDA qizarardi (rejaning o'zi taqiqlagan test turi)"
  - "Ikkinchi bo'sh qator sobit `300` o'rniga `count * 2 // 3` pozitsiyasiga qo'yildi — kichik miqyosda sobit qiymat qatorni faylning OXIRIGA surib, «bo'sh qator raqamni surmaydi» da'vosini o'lchanmay qoldirardi"
  - "S1 va S2 sabotajlari REJADA YOZILGAN shaklda O'LCHANDI va IKKALASI HAM TEGMADI (sabab o'lchandi va hujjatlashtirildi); ularning o'rniga AYNI fayllardagi, generator HAQIQATAN bosadigan qo'shni normallashtirishlar sabotaj qilindi"
  - "Miqyos testi bitta funksiyada — 11 bosqich ketma-ket bog'langan; bo'lish har test uchun 600 qatorlik importni qaytadan bajarishni talab qilardi"
  - "Toifa davrlari sanog'i `market_scope` (ILOVA roli) bilan FAQAT O'QISH uchun olinadi — jadval API'da ko'rinmaydi, D-15 ning va'dasi esa unga ham tegishli; barcha YOZUVLAR faqat HTTP orqali"
  - "`nyquist_compliant: true` skript tomonidan HISOBLANDI: 71 yashil Per-Task qatori, 0 ochiq band belgisi, 4 to'liq inson bandi, 5 avtomatlashtirilgan almashtirish"
  - "Ochiq band belgisining LITERAL so'zi hujjat prozasidan olib tashlandi — darvoza ataylab qo'pol va prozaga istisno bersa haqiqiy ochiq band proza ichida yashirinardi"

patterns-established:
  - "Pattern: fixture kutilmani E'LON qiladi (`expected_*_issues()`), test uni QAYTA HISOBLAMAYDI — ikkalasi birga xato bo'lganda yashil qolish yo'li yopiladi"
  - "Pattern: rad etish yo'lining yagona yuk ko'taruvchi assertion'i — SANOQ (javob kodi emas), va u har rad etishdan keyin qayta o'lchanadi"
  - "Pattern: hujjat darvozasi bayroqni ikkala yo'nalishda tekshiradi (erta `true` ham, abadiy `false` ham nomuvofiqlik)"
  - "Pattern: rejada yozilgan sabotaj TEGMASA — bu topilma, uni yashirmaslik va sababini o'lchash kerak; o'rniga ayni fayldagi qo'shni mexanizm sabotaj qilinadi"

requirements-completed: [MARKET-01, MARKET-02, MARKET-03, MARKET-04, MARKET-05, MARKET-06]

# Metrics
duration: 115min
completed: 2026-08-03
---

# Phase 2 Plan 23: Import qobiliyatining Karmana miqyosidagi isboti

**Import quvuri endi Karmananing haqiqiy miqyosida (8 zona / 605 rasta / 480 sotuvchi), quvurning O'ZI ishlab chiqarmagan iflos ma'lumot bilan uchidan-uchiga o'lchanadi; runbook fazani bloklaydigan hujjatdan operatsion tartibga aylandi; `nyquist_compliant` bayrog'i esa endi kelishuv emas — uni `scripts/check-validation-signoff.mjs` hisoblaydi va u yolg'on gapira olmaydi.**

## Holat

**Reja to'liq bajarildi.** Uchala task ham yetkazildi, `npm run gate` yashil (464 s, exit 0). Rejada yozilgan **beshta sabotajdan ikkitasi TEGMADI** — bu topilma va u pastda to'liq ochib berilgan; ikkalasining o'rniga ayni fayllardagi, generator haqiqatan bosadigan mexanizmlar sabotaj qilindi va ular AYNAN kutilgan darvozani qizartirdi.

## Performance

- **Duration:** ~115 min
- **Tasks:** 3/3
- **Files created:** 4 · **modified:** 4
- **`npm run gate`:** 464 s, exit 0 — **992 backend + 322 tenancy + 57 node + 74 vitest**

## Task Commits

1. **Task 1: Realistik miqyosdagi iflos ma'lumot generatori** — `8c38d12` (test)
2. **Task 2: Uchidan-uchiga miqyos testi va sabotaj** — `029b1fd` (test)
3. **Task 3: Runbook, validatsiya imzosi va mexanik darvoza** — `fd80e67` (docs)
4. **O'lchangan darvoza raqamlarini haqiqatga keltirish** — `2401448` (docs)

## O'lchovlar (taxmin EMAS)

`test_karmana_scale_import.py` `KARMANA_SCALE_PERF` sifatida bosadi:

| Nima | Qiymat |
|------|--------|
| 600 qatorli rasta importi (validatsiya + bitta tranzaksiya) | **0,281 s** |
| 480 qatorli sotuvchi importi (biriktirishlar bilan) | **0,226 s** |
| `GET /api/v1/stalls/map` (605 katak, 8 zona) | **0,039 s** |
| `GET /api/v1/stalls/map` javobining hajmi | **58 235 bayt (~57 KB)** |
| 600 rastali `.xlsx` (`npm run karmana:sample`) | **19 860 bayt** |
| 480 sotuvchili `.xlsx` (`npm run karmana:sample`) | **17 042 bayt** |
| Miqyos fayli YOLG'IZ (konteyner ko'tarilishi bilan) | **14,1 s** (sof pytest ~5 s) |
| Frontend to'plami (57 node + 74 vitest) | **13,8 s** |
| To'liq darvoza (`npm run gate`) | **464 s** |

**Kechikish byudjeti haqida halol yozuv.** `npm run gate` 02-22 da 585 s, 02-24 da ~571 s, bugun **464 s** chiqdi. Bu **tezlashtirish emas** — devor-soati Docker keshi va `next build` holatiga qattiq bog'liq, ya'ni trend o'lchovi sifatida ishonchsiz. Ishonchli raqam — ajratilgan fayl narxi: yangi miqyos fayli to'plamga **~5 s** qo'shdi (yolg'iz 14,1 s, undan ~9 s konteyner ko'tarilishi). Byudjetning buzilishi 02-17 dayoq strukturaviy edi (function-scope seed) va egasi **3-faza**; bu reja uni ~1% ga kattalashtirdi, evaziga `02-VERIFICATION.md` ning 2-bo'shlig'i yopildi.

## README §7 — yettala raqam endi assertion

| # | Raqam | Manba endpoint | Natija |
|---|-------|----------------|--------|
| 1 | Umumiy rasta soni | `GET /stalls` (keyset varaqlash) | **605** = 600 + 5 (qisman qayta import) |
| 2 | Zona bo'yicha taqsimot | `GET /zones` → `stall_count` | 8 zona, yig'indi = 605; har zona generator e'loni bilan teng |
| 3 | Holat bo'yicha taqsimot | `GET /stalls?status=` (uchala holat) | `active` / `maintenance` / `closed` — uchalasi ham e'lon bilan teng, yig'indi = 605 |
| 4 | Toifa bo'yicha taqsimot | `GET /categories` → `stall_count` | 6 toifa, e'lon bilan teng |
| 5 | Sotuvchi soni | `GET /vendors` (varaqlash) | **480**, hammasi `+998` bilan boshlanadi |
| 6 | Biriktirilgan rasta soni | `GET /stalls` → `vendor_name is not null` | 468 (12 sotuvchi ATAYIN rastasiz — D-11) |
| 7 | Toifa bo'yicha amaldagi narx | `GET /categories` → `current_tariff_soum` | oltala toifa, olti HAR XIL summa |

Qog'oz reestr bilan solishtirish esa **operatsion amal** bo'lib qoladi va u `02-VALIDATION.md` da `human_only_verifications` bandi sifatida, egasi va sharti bilan yuritiladi.

## Sabotaj o'lchovlari

Nazorat guruhi har o'lchovda bir xil: `tests/integration/test_stall_import.py` (02-12, 24 test), `tests/unit/test_xlsx_reader.py`, `tests/unit/test_import_validator.py`. Barcha o'lchovlarda to'plam **70 test**.

### S1a — REJADA YOZILGAN shakl: `import_validator._at()` dan `strip()` olib tashlandi

**Natija: HECH NARSA QIZARMADI (70/70 yashil).** Bu topilma va u yashirilmaydi.

**Sabab o'lchandi:** `xlsx_reader._cell_text()` qiymatni validatorga BERISHDAN OLDIN allaqachon `strip()` qiladi. Ya'ni `_at()` dagi `strip()` o'quvchi yo'lida ORTIQCHA — u faqat `_at()` ning o'z docstringi aytgan ikkinchi maqsad uchun bor: validatorni o'quvchi qatlamdan MUSTAQIL qilish (qo'lda qurilgan `SheetRow` uchun). Generator esa faylni HAQIQIY `.xlsx` sifatida quradi, ya'ni o'quvchi yo'lidan boradi.

**Xulosa:** reja `_at()` ni «atrofida bo'sh joyli zona nomi» da'vosining darvozasi deb hisoblagan; haqiqiy darvoza esa `_cell_text()` da. Kod noto'g'ri emas — reja modelining aniqligi noto'g'ri edi.

### S1b — o'rnini bosuvchi: `import_validator._lookup()` dan registrsiz fallback olib tashlandi

Generator zona nomini bir qatorda kichik harflar + atrofida bo'sh joy bilan (`"  markaziy qator "`), toifani esa bosh harflar + ortida bo'sh joy bilan yozadi — ya'ni bu tarmoq HAQIQATAN bosiladi.

**Qizardi (4):**
- `tests/integration/test_karmana_scale_import.py::test_karmana_scale_import_runs_end_to_end` — iflos faylning xato xaritasi 6 o'rniga 8 element berdi (ortiqcha `zone_not_found` + `category_not_found`)
- `tests/unit/test_karmana_seed.py::test_clean_stall_file_passes_validation_completely`
- `tests/unit/test_karmana_seed.py::test_dirty_stall_issues_match_the_declaration_exactly`
- `tests/unit/test_import_validator.py::test_mixed_case_stall_code_is_reported_as_a_duplicate` (02-21 / WR-05 — qonuniy qo'shni qurbon, ayni `_lookup` mexanizmi)

**NAZORAT YASHIL QOLDI:** `test_stall_import.py` ning **24 testi ham**, `test_xlsx_reader.py` ham. Sabab aniq va u rejaning da'vosini tasdiqlaydi: 02-12 ning testlari zona/toifa nomini `A_ZONE_NAMES` dan AYNAN o'sha registrda oladi, ya'ni ular bu tarmoqni umuman bosmaydi. **Miqyos testi kichik testlar ko'rmagan narsani o'lchadi.**

### S2a — REJADA YOZILGAN shakl: `xlsx_reader._cell_text()` dan butun-qiymatli float normallashtirishi olib tashlandi

**Natija: HECH NARSA QIZARMADI (70/70 yashil).** Ikkinchi topilma.

**Sabab o'lchandi:** `XlsxWriter` sonni `'%.16G'` bilan yozadi, ya'ni `12` → `12` (nuqta ham, eksponenta ham yo'q). `openpyxl._cast_number()` esa `float` ni FAQAT matnda `.` yoki `E`/`e` bo'lganda qaytaradi — aks holda `int`. Ya'ni **`XlsxWriter` bilan qurilgan fayl `12.0` shaklini UMUMAN hosil qila olmaydi**. Bu empirik tasdiq: S2a qo'llanganda `test_numeric_code_cell_becomes_a_plain_integer_string` YASHIL qoldi, ya'ni katak `int` bo'lib kelgan.

**Xulosa:** `_cell_text()` dagi float tarmog'i **hamon zarur** — u boshqa yozuvchilar (haqiqiy Excel, LibreOffice, eksportyorlar) uchun himoya. Lekin uni bu generator BOSA OLMAYDI, ya'ni sabotaj bu yo'ldan o'lchanmaydi. Bu — generatorning cheklovi, mahsulotning nuqsoni emas.

### S2b — o'rnini bosuvchi: AYNI funksiyadan (`_cell_text`) sana normallashtirishi olib tashlandi

Generator sotuvchi faylida HAQIQIY Excel sana katagini yozadi (`write_datetime` + sana formati), ya'ni bu tarmoq bosiladi.

**Qizardi (6):**
- `tests/integration/test_karmana_scale_import.py::test_karmana_scale_import_runs_end_to_end`
- `tests/unit/test_xlsx_reader.py::test_date_cells_become_iso_dates[datetime]`
- `tests/unit/test_xlsx_reader.py::test_date_cells_become_iso_dates[date]`
- `tests/unit/test_karmana_seed.py::test_clean_vendor_file_normalises_three_phone_shapes_to_one_e164`
- `tests/unit/test_karmana_seed.py::test_clean_vendor_file_keeps_stall_free_rows_and_default_dates`
- `tests/unit/test_karmana_seed.py::test_dirty_vendor_issues_match_the_declaration_exactly`

**NAZORAT YASHIL QOLDI:** `test_stall_import.py` ning 24 testi. Sabab: 02-12 ning sotuvchi testlari sana katagini HAR DOIM bo'sh qoldiradi (`""`), ya'ni ular sana normallashtirishini umuman bosmaydi.

### S3 — `02-VALIDATION.md`: `nyquist_compliant: true` qoldirilib, bir banddan `owner` olib tashlandi

```
check-validation-signoff: `nyquist_compliant: true` HISOB-KITOBGA MOS EMAS (hisoblangani: false)
  1 ta qoida buzilishi:
  ✗ (3) human_only_verifications «Sxematik xaritaning maqsadli qurilmada O'QILISHI
        (shrift, kontrast, skroll masofasi)»: `owner` yo'q yoki bo'sh —
        «avtomatlashtirib bo'lmaydi» da'vosi ism va shart talab qiladi
exit=1
```

Darvoza **AYNAN kutilganidek** bitdi: exit 1 va xabar bandning to'liq nomini ko'rsatdi. Har sabotajdan keyin fayl `git checkout` bilan tiklandi va `git status --short` bo'sh bo'lgani tasdiqlandi.

## Deviations from Plan

### 1. [Rule 4 → hujjatlashtirilgan qaror] `grep -c "xlsx_template" = 0` mezoni bajarilmadi — reja O'ZIGA ZID

- **Topildi:** Task 1
- **Muammo:** Rejaning `<action>` bandi *«Sabab modul docstringiga LITERAL yoziladi»* deb talab qiladi, qabul mezoni esa `grep -c "xlsx_template" tests/fixtures/karmana_seed.py` = **0** deydi. Ikkalasi bir vaqtda mumkin emas: sababni literal yozish uchun modul nomini aytish kerak, `grep` esa uni prozada ham ko'radi.
- **Qaror:** Docstring SAQLANDI (u qimmatroq artefakt — u keyingi o'quvchining darvozani jimgina bekor qilishiga to'sqinlik qiladi), operativ darvoza esa `ast` ga ko'chirildi.
- **O'lchov:**
  - `grep -c "xlsx_template" …/karmana_seed.py` = **2** (ikkalasi ham proza: docstring va izoh)
  - `grep -cE "^\s*(from|import)\s.*xlsx_template" …` = **0** ← operativ darvoza
  - `grep -cE "^\s*(from|import)\s+app([.\s]|$)" …` = **0** — generator butun `app` paketidan mustaqil
  - `test_generator_does_not_import_the_template_module` — `ast` bilan: import nomlari, `app.*` bog'liqligi va KOD ichidagi (docstring EMAS) `imports/` satr literallari
- **Nega `ast` kuchliroq:** u prozani e'tiborsiz qoldiradi, `import app.services.xlsx_template as t` kabi taxallusli shakllarni ham ushlaydi va docstringni darvozaga qarshi qo'ymaydi.

### 2. [Rule 1 - Bug] Determinizm testi «gohida yiqiladigan» bo'lardi — ZIP sanasi muzlatildi

- **Topildi:** Task 1
- **Muammo:** `XlsxWriter` `in_memory` rejimida `ZipFile.writestr(nom, ...)` ni chaqiradi; `zipfile` bunday chaqiruvda a'zo sanasini SOATdan oladi. Ikki qo'shni chaqiruv baytlari sekund chegarasida farq qilardi — ya'ni «AYNAN bir xil baytlar» testi rejaning O'ZI taqiqlagan («gohida yiqiladi») turga aylanardi.
- **Tuzatish:** `_freeze_zip()` — chiqish ZIP'i sobit `date_time` bilan qayta o'raladi (mazmun, siqish turi va ochilgan hajm o'zgarmaydi); `set_properties({"created": ...})` esa `docProps/core.xml` ni muzlatadi.
- **Fayl:** `tests/fixtures/karmana_seed.py`
- **Tekshiruv:** `test_two_builds_with_the_same_seed_are_byte_identical` yashil; `xlsx_reader._check_zip()` darvozalari o'zgarmagan (600 qatorli fayl import qilinadi).
- **Commit:** `8c38d12`

### 3. [Rule 1 - Bug] Ikkinchi bo'sh qatorning sobit pozitsiyasi da'voni o'lchanmay qoldirardi

- **Topildi:** Task 1 (test birinchi ishga tushirishda qizardi)
- **Muammo:** Reja bo'sh qatorlarni sobit pozitsiyalarga qo'yishni nazarda tutgan (`300`). Kichik miqyosda (`count=60`) bu qator faylning OXIRIGA tushdi va «bo'sh qator keyingi raqamlarni surmaydi» da'vosi o'lchanmay qoldi — oxirgi qatordan keyingi bo'shliq umuman ko'rinmaydi.
- **Tuzatish:** pozitsiya miqyosga nisbatan (`max(1, count * 2 // 3)`).
- **Tekshiruv:** `test_blank_rows_are_dropped_without_shifting_the_row_numbers` — tashlangan qatorlar to'plami generator e'loni bilan AYNAN teng.
- **Commit:** `8c38d12`

### 4. [Rule 3 - Blocking] Rejadagi ikkala sabotaj ham tegmadi — o'rnini bosuvchilar tanlandi

Yuqoridagi «Sabotaj o'lchovlari» bo'limida to'liq ochib berilgan (S1a/S2a — o'lchandi, sababi hujjatlashtirildi; S1b/S2b — AYNI fayllardagi qo'shni normallashtirishlar, generator haqiqatan bosadigan). Reja bu holatni oldindan ko'rgan: *«Kutilganidan boshqa natija — topilma, uni yashirmang»*.

### 5. [Rule 2 - Missing Critical] Ochiq band belgisining literal so'zi hujjat prozasidan olib tashlandi

- **Topildi:** Task 3
- **Muammo:** Yangi «Verification triage» prozasi eski holatni tasvirlash uchun `BAJARILMADI` so'zini KELTIRGAN edi. Skriptning 2-qoidasi bu so'zni butun faylda taqiqlaydi, ya'ni bayroq `true` bo'la olmasdi.
- **Qaror:** Darvozaga proza istisnosi BERILMADI (istisno berilsa haqiqiy ochiq band bir kun proza ichida yashirinardi), matn qayta yozildi va nega literal yozib bo'lmasligi hujjatning o'zida tushuntirildi.
- **Tekshiruv:** `grep -c "BAJARILMADI" 02-VALIDATION.md` = **0**; `node scripts/check-validation-signoff.mjs` exit 0.
- **Commit:** `fd80e67`

### 6. [Rule 1 - Bug] SUMMARY'gacha yozilgan darvoza raqamlari TAXMIN edi — o'lchov bilan almashtirildi

- **Topildi:** Task 3 dan keyin, `npm run gate` ni o'lchashda
- **Muammo:** `02-VALIDATION.md` ga vaqtincha «1000 backend testi» va «599 s» yozilgan edi; ikkalasi ham o'lchanmagan taxmin.
- **Tuzatish:** `npm run gate` chiqishidan sanaldi — **992 backend + 322 tenancy + 57 node + 74 vitest**, davomiylik **464 s**. Devor-soatining 02-22 dagidan KAM chiqqani ham ochiq yozildi (bu tezlashtirish emas, kesh variatsiyasi).
- **Commit:** `2401448`

---

**Jami deviatsiya:** 6 ta (1 reja ichki ziddiyati + 3 bug + 1 sabotaj o'rnini bosish + 1 kritik hujjat tuzatishi). **Ta'sir:** doiraga chiqish yo'q — hammasi rejaning o'z da'volarini haqiqatga keltirish uchun edi.

## Issues Encountered

- **`GET /stalls` da umumiy sanoq maydoni yo'q** (ATAYIN — chegarasiz `count(*)` har so'rovga qo'shilardi). README §7 buni «sahifani oxirigacha varaqlash» deb yozgan, shuning uchun test `_page_through()` yordamchisini qurdi (`limit=200`, kursor, 64 sahifalik cheksiz-sikl himoyasi). Bu hujjat bilan mos va u ham o'sha yo'lni sinaydi.
- **`GET /calendar/weekdays` mavjud emas** — haftalik jadval `GET /calendar` javobida keladi. Test tegishli endpointga o'tkazildi.
- **Ustunlari surilgan fayl ATAYIN kichik (40 qator)** — 600 qatorli variant har qatorga 2–3 xato berib, 1500+ elementli 422 tanasini qurardi. O'lchanayotgan da'vo miqyosga bog'liq emas.

## Known Stubs

Yo'q. Bu reja mahsulot kodiga umuman tegmadi (faqat test, skript va hujjat), migratsiya ham, yangi paket ham qo'shilmadi:
`git diff --name-only -- services/core-api/uv.lock frontend/package-lock.json migrations/` → **BO'SH**.

## Next Phase Readiness

- **`02-VERIFICATION.md` ning 2-bo'shlig'i («HOLLOW Level 4», `✗ DISCONNECTED`) yopildi:** quvur endi o'zi ishlab chiqarmagan ma'lumotni Karmana miqyosida ko'taradi va bu CI'da takrorlanadi. Qayta tekshiruv uchun buyruq: `docker compose --profile test run --rm tests pytest tests/integration/test_karmana_scale_import.py -q`.
- **`02-VALIDATION.md` endi halol:** avtomatik qamrov va inson bandlari ajratilgan, har inson bandida egasi va ishga tushish sharti bor, bayroqni skript majburlaydi.
- **3-fazaga o'tadigan ikki ochiq band** (`open_items` da, egasi bilan): to'lqin darajasidagi kechikish byudjeti (strukturaviy, function-scope seed) va miqyos konstantasining Python↔vitest orasida takrorlanishi.
- **Keyingi fazalar uchun tayyor vosita:** `npm run karmana:sample` realistik miqyosdagi iflos dataset beradi — 4-faza (snapshot) va 6-faza (billing) uni 600 rastali bozor ustida o'lchov qilish uchun ishlatishi mumkin.

---
*Phase: 02-bozor-domeni-va-yangi-bozor-ustasi*
*Completed: 2026-08-03*
