---
phase: 07-nomuvofiqlik-bildirishnoma-va-botlar
plan: 14
subsystem: scheduler-registry
tags: [cron, heartbeat, d-17, registry, ast-gate, g-35, i18n, postgres-ordering]
requires:
  - "app/jobs/outbox.py::outbox_tick + OUTBOX_COMPONENT (07-09)"
  - "app/jobs/reconciliation.py::reconciliation_open + RECON_OPEN_COMPONENT (07-07)"
  - "app/jobs/notifications.py::digest_morning / digest_evening / overdue_reminder (07-13)"
  - "app/api/internal/self_check.py::EXPECTED_COMPONENTS — /internal/* posturasi (07-08)"
  - "app/jobs/alerting.py::_platform_signals::watched — «None ham eskirish» (06-07)"
provides:
  - "worker.py — besh cron konstantasi + besh yupqa qobiq (notify.outbox_tick, recon.open, notify.digest_morning, notify.digest_evening, notify.overdue)"
  - "EXPECTED_COMPONENTS 6 -> 10; watched 3 -> 7 juftlik; ALERT_META 11 -> 15"
  - "tests/unit/test_heartbeat_registry.py — uch manbaning AST-HOSILA tengligi (D-17)"
  - "tests/unit/test_digest_qualifiers.py — G-35 ning MATN yarmi, uchala locale"
  - "outbox_repo._CLAIM_DUE — chiqish tartibi KAFOLATLANGAN (flake yopildi)"
  - "outbox._QUALIFIER_WORDS / _MORNING_TEXT / _EVENING_TEXT — recon.qualifier.* kod tomoni"
affects:
  - "07-17 (faza darvozasi) — tirik reyestrga tayanadi"
  - "07-15 (frontend G-35 jufti) — server matni endi uchala locale'da o'lchangan"
  - "deploy — `docker compose up -d --force-recreate scheduler` MAJBURIY (jadval import paytida olinadi)"
tech-stack:
  added: []
  patterns:
    - "reyestr tengligi NOMLAR RO'YXATI emas, AST-HOSILA predikat"
    - "yig'uvchi ANNOTATSIYA SHAKLIGA bog'liq bo'lmasligi shart (`Final[str]` vs `str`)"
    - "istisno ro'yxati NOMLANADI, sababi kodda yoziladi va UZUNLIGI assert qilinadi"
    - "sanoqni ko'tarish emas — EGALIK ro'yxatiga o'tkazish (darvoza kuchayadi, bo'shamaydi)"
    - "`UPDATE ... RETURNING` tartibi kafolatlanmaydi — tashqi `SELECT` + `ORDER BY`"
    - "til KO'RINISH tanlovi: noma'lum locale xabarni yiqitmaydi, standartga tushadi"
key-files:
  created:
    - tests/unit/test_heartbeat_registry.py
    - tests/unit/test_digest_qualifiers.py
  modified:
    - services/core-api/app/worker.py
    - services/core-api/app/api/internal/self_check.py
    - services/core-api/app/jobs/alerting.py
    - services/core-api/app/jobs/outbox.py
    - services/core-api/app/repositories/outbox_repo.py
    - tests/integration/test_alerting.py
    - tests/integration/test_capture_tick.py
    - tests/integration/test_capture_schedule.py
    - frontend/messages/uz-Latn.json
    - frontend/messages/ru.json
    - frontend/messages/uz-Cyrl.json
    - frontend/src/components/snapshots/alert-row.tsx
decisions:
  - "daqiqalik cron darvozasi SANOQDAN EGALIKKA o'tkazildi: {capture.tick, notify.outbox_tick} — `<= 2` yozish taqiqni sekin bekor qilish bo'lardi"
  - "WATCHED_EXEMPT UCHTA (day_close, alert_sweep, capture_tick), reja «aynan bitta» degan edi — farq TOPILMA sifatida qayd etildi"
  - "komponent yig'uvchisi annotatsiyaga bog'liq EMAS: day_close/billing_close `: str` bilan e'lon qilingan"
  - "MIN_COMPONENTS 8 -> 10: 8 sharti noto'g'ri yig'uvchini O'TKAZIB YUBORARDI (aynan 8 topadi)"
  - "_CLAIM_DUE tuzatishi TESTDA emas, SO'ROVDA — test tartibni ATAYIN o'lchaydi"
  - "noma'lum locale `_normalize_locale()` bilan standartga tushadi: `format_soum()` `ValueError` beradi va qator `failed` bo'lardi (kvitansiya yo'qolardi)"
  - "uz-Cyrl.overrides.json TEGILMADI — transliterator to'rtala satrni to'g'ri o'girdi (qo'lda tekshirildi)"
metrics:
  duration: ~110 min
  completed: 2026-08-12
  tasks: 3
  files: 14
---

# Phase 7 Plan 14: Fon oqimi jonlandi va endi JIMGINA o'la olmaydi — Summary

Beshala job nihoyat cron reyestrida; ularning **yo'qligi** ikki reyestr va
xulqiy test bilan alertga aylanadi; qo'shimcha ravishda `_CLAIM_DUE` ning
tasodifiy tartibi (CI ni vaqti-vaqti bilan qizartirgan flake) so'rov
darajasida yopildi va G-35 ning matn yarmi uchala locale'da **birinchi
marta o'lchandi**.

## Nima qurildi

**Task 1 — `worker.py` (`1bb4f3b`).** Besh cron konstantasi va besh yupqa
qobiq. Biznes-kun **qobiqda** hisoblanadi (07-13 ning `business_date`/`as_of`
argument qarori **hurmat qilindi** — jobga wall-clock qaytarilmadi).
`notify.outbox_tick` `state.alerts_enabled` chegarasini **olmaydi** (D-23):
ops chati sozlanmagan bozorda ham kvitansiya ketadi.

**Task 2 — ikki reyestr + to'rt alert kaliti (`220b1df`).**
`EXPECTED_COMPONENTS` 6 -> 10, `watched` 3 -> 7 juftlik (komponent nomlari
**import qilinadi**), `ALERT_META` 11 -> 15. Uchala locale'da matn;
`alert-row.tsx` xaritasi ham (usiz matn ekranda «Kutilmagan xato» bo'lardi).

**Task 3 — `test_heartbeat_registry.py` (`2c9fbfa`).** 7 test, darvoza
**hosila**: komponent nomlari `app/jobs/` dan AST bilan yig'iladi.

**`e0e8826`** — orkestrator ruxsat bergan (A) tuzatishi.
**`5bdf57c`** — orkestrator ruxsat bergan (B) darvozasi.

## O'lchangan dalillar

### ⛔ Sabotaj 1 — `EXPECTED_COMPONENTS` dan `notify_overdue` olib tashlandi

| Darvoza | Natija |
|---|---|
| `test_every_job_component_is_expected` | **QIZIL** — `assert ['notify_overdue'] == []` |
| Qolgan **6** test | **yashil** |

Xato xabari komponent nomini **atadi** va `deferred-items.md` ning 2-bandini
eslatdi, ya'ni darvoza «nimadir noto'g'ri» emas, «**aynan nima**» deydi.

### ⛔ Sabotaj 2 — `watched` dan `(OUTBOX_COMPONENT, "outbox_stale")` olib tashlandi

| Darvoza | Natija |
|---|---|
| `test_every_job_component_is_watched` | **QIZIL** |
| `test_missing_new_heartbeat_raises_an_alert` | **QIZIL** — `assert 'outbox_stale' in []` |

⛔ Reja **ikkalasining ham** qizarishini talab qilgan edi — struktura va
xulq **mustaqil** buziladi va ikkalasi ham o'lchandi.

### ⛔ Sabotaj 3 — G-35, kechki matnga ikkinchi sifatlovchi qo'shildi

`_EVENING_TEXT["uz-Latn"]["collected"]` -> `"Yozilgan yig'indi"`.

| Darvoza | Natija |
|---|---|
| `test_each_digest_names_exactly_one_qualifier[digest_evening-uz-Latn]` | **QIZIL** — `{'expected','recorded'} == {'expected'}` |
| Qolgan **16** test (jumladan `[digest_evening-ru]`, `[digest_evening-uz-Cyrl]`) | **yashil** |

⛔ Ikkinchi qator darvozaning **MANZILLI** ekanini isbotlaydi: sabotaj faqat
o'zi tekkan locale'da ko'rinadi. Oddiy «kutilayotgan bormi?» tekshiruvi bu
holatni **umuman ko'rmasdi** — aynan shuning uchun §12.3 to'plam tengligini
talab qiladi.

### Reja talab qilgan mexanik da'volar

| Da'vo | Natija |
|---|---|
| Beshala vazifa `broker` reyestrida | ✓ `notify.outbox_tick`, `recon.open`, `notify.digest_morning`, `notify.digest_evening`, `notify.overdue` |
| `"* * * * *"` literali `worker.py` da | **2** (talab: 2) va ikkalasi ham **konstanta e'lonida** |
| Literal **dekoratorda** | **0** — endi darvoza bilan qulflangan |
| `cron_offset` literali | **13** (talab: >= 8; bazada 8 edi) |
| Uchala kunlik yangi jadval | `cron_offset == "Asia/Tashkent"` ✓ |
| `notify.outbox_tick` dekoratorida `cron_offset` | **YO'Q** (reyestr metama'lumotidan o'lchandi) |
| `grep -c "business_today()"` `worker.py` | **8 -> 15** (kod darajasidagi chaqiruv: **4 -> 8**) |
| `EXPECTED_COMPONENTS` | **6 -> 10** |
| `ALERT_META` | **11 -> 15**; 7-faza kalitlari **AYNAN BESHTA** |
| `ALERT_META["outbox_stale"]` | `critical`, `never_suppressed=True`, `platform_scoped=True` ✓ |
| `vendor_binding_conflict` (07-08 chegarasi) | reyestrda **BOR**, `_platform_signals` da **YO'Q** ✓ |
| `alerting.py` da to'rt komponent nomi literal | **0** — import qilingan |
| `GET /internal/self-check` | **200**, to'rtala yangi komponent `never_seen` da (test bilan qulflandi) |
| `test_heartbeat_registry.py` | **7 test** (reja 5 so'ragan) |
| `test_digest_qualifiers.py` | **17 test** |
| `test_alerting.py` | **23 test** (07-09 da 22 edi) |

### Darvozalar

| Darvoza | Natija |
|---|---|
| `pytest tests/unit tests/tenancy` | **1945 yashil, 0 skip, 0 yiqilish — `EXIT=0`** |
| `pytest tests/integration -m "not sim and not slow"` — **1-yugurish** | **998 yashil, 5 skip, 0 yiqilish — `EXIT=0`** |
| AYNI to'plam — ⛔ **2-YUGURISH** (flake dalili) | **998 yashil, 5 skip, 0 yiqilish — `EXIT=0`** |
| `tests/integration/test_outbox_repo.py` — **KETMA-KET BESH yugurish** | har birida **21/21 yashil** |
| `ruff check .` + `ruff format --check .` + `mypy .` | **toza** (345 / 336 fayl) |
| `npm --prefix frontend run i18n:check` | **1119 kalit × 3 til** — kalit va ICU parity to'liq |
| `node scripts/gen-cyrillic.mjs --check` | **drift yo'q** |
| `node --test frontend/scripts/*.test.mjs` | **191 test yashil** (jumladan `glossary.test.mjs` — G7-9) |

## Rejadan chetlanishlar

### Orkestrator ATAYIN ruxsat bergan ikki chetlanish

**1. [Ruxsat etilgan A] `_CLAIM_DUE` — CI ni vaqti-vaqti bilan qizartirgan flake**

- **Topildi:** 07-12 to'liq to'plamni yugurtirganda
  (`test_the_oldest_row_is_claimed_first`: 1-yugurish QIZIL, 2-yugurish
  YASHIL, yolg'iz yugurtirilganda 21/21 yashil).
- **Sabab:** CTE ning `ORDER BY` i faqat **QAYSI** qatorlar tanlanishini
  belgilaydi (`LIMIT` bilan birga). Tashqi `UPDATE ... FROM due ...
  RETURNING` ning **chiqish tartibi** PostgreSQL da kafolatlanmaydi —
  planer `due` ni jadval bilan hash/merge join qiladi va natija tartibi
  rejaga qarab o'zgaradi. Qatorlar **to'g'ri tanlangan**, faqat tartibi
  suzib yurgan.
- **Yechim:** `UPDATE` `claimed` CTE siga o'raldi, yakuniy `SELECT` **o'z**
  `ORDER BY created_at, id` ini oldi. `UPDATE ... RETURNING` ning **o'ziga**
  `ORDER BY` yozib bo'lmaydi (PostgreSQL grammatikasi qabul qilmaydi), shu
  sababdan tartib yakuniy proyeksiyada beriladi. `created_at` `RETURNING`
  ro'yxatiga qo'shildi va yakuniy `SELECT` dan **chiqarib tashlandi** —
  `OutboxClaim` maydonlari **o'zgarmadi**.
- **⛔ Tuzatish TESTDA emas, SO'ROVDA** (orkestratorning ko'rsatmasi bilan
  bir xil): test tartibni **ATAYIN** o'lchaydi va uni to'plam tengligiga
  aylantirish «kvitansiya cheksiz kutmaydi» da'vosini o'lchovsiz
  qoldirardi. Vaqti-vaqti bilan qizaradigan darvoza — eng yomon sinf: u
  odamlarni **qarashga** emas, **qayta yugurtirishga** o'rgatadi.
- **O'lchov — flake AYNAN o'z sharoitida takrorlandi:** nosozlik TO'LIQ
  TO'PLAM kontekstida ko'ringan (yolg'iz yugurtirilganda hech qachon
  qizarmagan), shuning uchun dalil ham o'sha kontekstda yig'ildi:
  `pytest tests/integration -m "not sim and not slow"` **IKKI MARTA**
  yugurtirildi va **ikkalasi ham** `998 yashil / 5 skip / 0 yiqilish /
  EXIT=0` berdi. Ustiga `test_outbox_repo.py` **ketma-ket besh** yugurish,
  har birida **21/21 yashil**.
- **Commit:** `e0e8826`

**2. [Ruxsat etilgan B] G-35 ning MATN yarmi — uchala locale**

- **Topildi:** 07-13 SUMMARY ning 1-ochiq bandi: shakl yarmi (`payload`
  to'plam tengligi) bajarilgan, matn yarmi **o'lchanmagan** — `_build_text`
  o'sha paytda 07-09 ning worktree'sida edi.
- **Nima bor edi:** `_digest_*_text()` sifatlovchini **sarlavhada** yozardi
  (`«Kechki holat» (bugun kutilayotgan)`) va matn **bitta tilda** edi, ya'ni
  §12.2 ning ikkala talabi ham bajarilmagan: (a) sifatlovchi **raqam bilan
  bir jumlada** turishi shart — sarlavha Telegram bildirishnomasining
  qisqartirilgan ko'rinishida **kesiladi** va foydalanuvchi faqat raqamni
  ko'radi; (b) kontrakt **uchala locale** uchun.
- **Yechim:** `_QUALIFIER_WORDS` (§12.2 jadvalining kod tomoni) +
  `_MORNING_TEXT` / `_EVENING_TEXT` yorliq jadvallari; sifatlovchi endi
  `«Bugun kutilayotgan patta: 4 200 000 so'm»` shaklida **raqam bilan bir
  qatorda**. Darvoza (`test_digest_qualifiers.py`, 17 test): to'plam
  tengligi (2 xabar × 3 locale), sifatlovchining raqam bilan **bir qatorda**
  ekani, uchala locale'ning **haqiqatan farq qilishi**, fallback va **ikki
  nazorat bandi**.
- **⛔ Kutilgan so'zlar testda QAYTA YOZILGAN**, mahsulotdan import
  qilinmaydi (05-13 / 07-13 darsi) — manba `07-UI-SPEC.md` §12.2 jadvali.
- **Chegara OCHIQ yozildi:** kvitansiya va qarz eslatmasi matnlari hamon
  **bitta tilda**. Ular G-35 ning kontraktida **yo'q** va ularning uch tilli
  varianti 07-09 ning 2-ochiq bandiga (`vendors` dagi til ustuni, BOT-01
  doirasi) tegishli. `_LOCALE` **o'zgarmadi** — ya'ni mahsulot yo'lida bugun
  ham uz-Latn ishlatiladi, uchala variant esa `locale` **argumenti** orqali
  o'lchanadi.
- **Commit:** `5bdf57c`

### Rule 3 — rejaning O'Z akseptans mezoni mavjud darvoza bilan TO'QNASHDI

**3. [Rule 3] `test_capture_tick.py::test_the_scheduler_has_exactly_one_minute_cron`**

- **Topildi:** Task 1, birinchi yugurishda. Test **QIZARDI** (o'lchandi,
  taxmin qilinmadi).
- **Ziddiyat rejaning ICHIDA edi:** reja ogohlantiradi «yangi daqiqalik job
  **o'z konstantasi** bilan yoziladi, **aks holda mavjud darvoza
  qizaradi**» — lekin mavjud darvoza `"* * * * *"` literalini **fayl matni
  bo'ylab** sanaydi (`== 1`) va **ikkinchi konstanta e'loni ham** o'sha
  sanoqni oshiradi. Rejaning o'z qabul mezoni esa `grep -c` -> **2** ni
  talab qiladi. Ikkalasi bir vaqtda mumkin emas. Ikkinchi assert
  (`minute_crons == 1`) ham qizarardi: u jadval qiymatlarini **yechadi**.
- **Yechim — darvoza BO'SHATILMADI, KUCHAYTIRILDI:**
  1. literal sanog'i `== 2`, **ustiga** har uchrash **konstanta e'lonida**
     bo'lishi shart (dekoratorda literal **taqiqlangan** — bu talab ilgari
     umuman yo'q edi);
  2. `minute_crons == 1` **egalik to'plami** bilan almashtirildi:
     `{capture.tick, notify.outbox_tick}` va u **`broker` reyestridan**
     olinadi, matndan emas. **Uchinchi** daqiqalik oqim — nomi qanday
     bo'lishidan qat'i nazar — baribir qizaradi.
- **⛔ `<= 2` YOZILMADI va bu ongli:** chegarani ko'tarish — taqiqni bekor
  qilishning sekin shakli (03-07 ning o'lchangan darsi). Da'vo
  «daqiqalik oqim **nazorat ostida**» edi va u saqlandi.
- **Nega ikkinchi oqim qonuniy:** D-02/D-03 ning da'vosi kadr olish tikining
  idempotentligiga tayanadi; `notify.outbox_tick` — **boshqa** vazifa va
  uning **o'z** mexanizmi bor (ijara + `SKIP LOCKED`). Sabab test
  docstringida yozildi, ya'ni keyingi ijrochi uni qayta kashf qilmaydi.
- **Commit:** `1bb4f3b`

### Rule 2 — usiz da'vo BO'SH-ROST bo'lardi

**4. [Rule 2] `frontend/src/components/snapshots/alert-row.tsx`**

- **Topildi:** Task 2. Reja faqat `messages/*.json` ni sanaydi.
- **Nega muhim:** `ALERT_TITLE_KEYS` xaritasiga kirmagan kalit ekranda
  `errors.generic` («Kutilmagan xato») bo'lib chiziladi — ya'ni «uchala
  locale'da matn bor» mezoni **bo'sh-rost** bo'lardi. Presedent aynan shu
  faylda **ikki marta** yozilgan (`billing_close_stale` 06-fazada,
  `vendor_binding_conflict` 07-08 da).
- **Commit:** `220b1df`

**5. [Rule 2] `tests/integration/test_capture_schedule.py`**

- **Topildi:** rejaning qabul mezoni «`never_seen` ro'yxatida to'rt yangi
  komponent ko'rinadi va endpoint hamon **200**» — lekin uni o'lchaydigan
  test bu rejaning fayl ro'yxatida yo'q edi.
- **Yechim:** mavjud `test_self_check_is_ok_when_the_heartbeat_is_fresh`
  ga uch qator qo'shildi (to'rtala nom `never_seen` da). Yangi test
  **yozilmadi**: da'vo o'sha testning **aynan** da'vosi va uni ikkinchi
  faylga ko'chirish ikki nusxa tug'dirardi.
- **⛔ Bu mezon shunchaki «ehtimol o'tadi» emas edi:** reyestrni
  kengaytirish endpointni `503` qilib qo'yishi mumkin edi (u holda tashqi
  kuzatuvchi darvozani **o'chirib** qo'yardi) — endi bu **qulflangan**.
- **Commit:** `220b1df`

**6. [Rule 2] `tests/integration/test_alerting.py::_PLATFORM_COMPONENTS`**

- **Topildi:** `watched` to'rt juftlik bilan o'sgach **beshta** guruhlash
  testi `assert 4 == 2` / `assert 2 == 1` bilan qizardi — **o'lchandi**,
  taxmin qilinmadi.
- **Sabab MAHSULOTDA emas, TEST SHARTIDA:** yangi joblar bu seedda hech
  qachon yugurmaydi, ya'ni yurak urishi **yo'q** va `None` **ham
  eskirish** — supurgi har yugurishda to'rtta platforma alertini
  ko'taradi. Bu 06-07 ning `BILLING_CLOSE_COMPONENT` da o'lchagan
  nosozligining **aynan takrori** va o'sha yerda yozib qoldirilgan.
- **Yechim:** to'rt komponent `bed` fixture'ida **yangi** qilib qo'yiladi
  (nomlar import qilinadi); kalitlarning **o'zi** yangi xulqiy testda
  o'lchanadi.
- **Commit:** `220b1df`

### Rejadan farq qilgan TOPILMALAR (yashirilmadi)

**7. `WATCHED_EXEMPT` — reja «AYNAN BITTA» degan, haqiqat UCHTA.**

Reja `test_every_job_component_is_watched` uchun **bitta** nomlangan
istisno (`day_close`) talab qilgan va ro'yxatning **o'sishini taqiqlagan**.
O'lchov boshqa son berdi:

| Komponent | `watched` da? | Sabab |
|---|---|---|
| `day_close` | yo'q | 5-fazaning ochiq qarzi (`self_check.py` docstringi) |
| `alert_sweep` | yo'q | ⛔ **supurgining o'zi** — uni o'z ro'yxatiga qo'yish AYLANMA bo'lardi: o'lgan supurgi o'zining o'lgani haqida alert yoza olmaydi. Uni `/internal/self-check` **boshqa jarayondan** ko'radi (`self_check.py` 2-QOIDASI) |
| `capture_tick` | yo'q | ayni sabab **va** ikkinchisi: kadr olishning yo'qligi allaqachon bozor kesimida, boyroq signallar bilan o'lchanadi (`capture_missed` / `capture_stopped`); ikkinchi alert ularni takrorlardi (D-22) |

⛔ **Rejaning niyati saqlandi, soni emas:** har istisnoning sababi kodda
yozildi va to'plamning **uzunligi** assert qilindi (`== 3`). Himoya «uchta»
sonida emas — ro'yxatning **o'sa olmasligida**. Ikkala istisno ro'yxati ham
alohida test bilan qulflangan.

**8. Komponent yig'uvchisi ANNOTATSIYAGA bog'liq bo'lmasligi shart.**

Reja «modul darajasidagi `Final[str]` konstantalarni yig'adi» deydi. Ijro
paytida o'lchandi:

    app/jobs/outbox.py        OUTBOX_COMPONENT: Final[str] = "..."
    app/jobs/day_close.py     DAY_CLOSE_COMPONENT: str      = "..."   <- BOSHQA
    app/jobs/billing_close.py BILLING_CLOSE_COMPONENT: str  = "..."   <- BOSHQA

`Final[str]` ni talab qiladigan yig'uvchi **ikkita** komponentni jimgina
o'tkazib yuborardi. Shart **nomda** (`*_COMPONENT`) va **qiymatda** (satr
konstantasi) qoldirildi.

**⛔ Va bu topilma ikkinchi teshikni ham ochdi:** `MIN_COMPONENTS` dastlab
**8** qo'yilgan edi — noto'g'ri yig'uvchi **aynan 8 ta** komponent topadi,
ya'ni quyi chegara o'sha nosozlikni **o'tkazib yuborardi**. Chegara **10**
ga ko'tarildi va ustiga `ANNOTATION_VARIANTS` **ijobiy nazorati** qo'shildi
(`{day_close, billing_close}` topilishi SHART).

**9. `format_soum()` noma'lum locale'da `ValueError` KO'TARADI.**

`_labels()` ning birinchi varianti faqat yorliq jadvali uchun fallback
qilardi — o'lchov ko'rsatdiki bu **yarim** fallback: pul formatlovchisi
baribir yiqilardi va `_deliver()` qatorni `failed` ga tushirardi, ya'ni
bitta buzuq til qiymati **kvitansiyani butunlay yo'qotardi** (D-02 ning
dalili). Yechim: normalizatsiya **bitta joyda** — `_build_text()` da
(`_normalize_locale()`), quyi funksiyalarning hammasi **yechilgan** qiymatni
oladi. `_SUPPORTED_LOCALES` `Locale` enumidan **hosila**.

**10. `frontend/messages/uz-Cyrl.overrides.json` TEGILMADI** (u rejaning
fayl ro'yxatida bor edi). Transliterator to'rtala satrni ham to'g'ri
o'girdi va `gen-cyrillic --check` drift topmadi — override qo'shish
**ishlatilmaydigan yozuv** qoldirardi (07-08 ning aynan o'sha qarori).

⛔ **KNOWN TRAP QO'LDA TEKSHIRILDI** (mexanik darvoza bu sinfni
ushlamaydi — 07-05 ning `квитансиялар` darsi):

| uz-Latn | uz-Cyrl (generatsiya) | Verdikt |
|---|---|---|
| Bildirishnoma navbati to'xtadi | Билдиришнома навбати тўхтади | ✓ |
| Nomuvofiqlik tekshiruvi bajarilmadi | Номувофиқлик текшируви бажарилмади | ✓ |
| Kunlik hisobot xabari tayyorlanmadi | Кунлик ҳисобот хабари тайёрланмади | ✓ |
| Qarzdorlik eslatmasi tayyorlanmadi | Қарздорлик эслатмаси тайёрланмади | ✓ |

To'rttasi ham **sof o'zbekcha** so'zlardan iborat, ya'ni o'zlashgan so'z
tuzog'i bu satrlarga **umuman tegmaydi**. Dayjest matnlarining kirillchasi
esa `outbox.py` da **qo'lda** yozildi (u transliteratordan o'tmaydi) va
o'sha yerda ham tekshirildi.

### Ijro jarayonidagi hodisa (yashirilmaydi)

**11. Sabotaj 3 ni qaytarishda `git checkout --` BUTUN faylni qaytardi.**
`outbox.py` o'sha paytda hali **commit qilinmagan** edi, ya'ni revert
sabotaj bilan birga (B) ning butun implementatsiyasini ham oldi. O'zgarish
**qayta yozildi** va to'liq qayta o'lchandi (17 test, `ruff`/`mypy` toza).
⛔ **Dars va u shu yerda qoldiriladi: sabotajdan OLDIN commit qilinadi** —
qolgan ikki sabotaj aynan shunday bajarilgan edi va ular xavfsiz qaytdi.

## Ochiq bandlar

**1. Deploy bandi — MEXANIK RAVISHDA USHLANMAYDI.** Cron jadvali `import`
paytida olinadi, ya'ni beshala yangi vazifa `scheduler` konteyneri qayta
ishga tushirilmaguncha **ro'yxatga olinmaydi** va **hech qanday xato
chiqmaydi**:

    docker compose up -d --force-recreate scheduler

Endi bu **ko'rinadi**: yurak urishi kelmasa `outbox_stale` (`critical`,
bo'g'ilmaydi) va uchta `warning` alerti ochiladi. **Egasi:** deploy
bajaradigan reja (07-17 / 8-faza).

**2. Ikkala dayjest hamon BITTA `notify_digest` yurak urishini yangilaydi**
(07-13 ning ongli narxi). Oqibat: kechkisi ishlab, ertalabkisi o'lsa yurak
urishi **hamon yangi** ko'rinadi. Bu reja reyestrni **kengaytirdi**, lekin
konstantani ikkiga **bo'lmadi**: bu `notifications.py` ning yuzasini
o'zgartirardi va u bu rejaning fayl ro'yxatida yo'q. **Egasi:**
`notifications.py` ni ochadigan keyingi reja.

**3. `jobs/reconciliation.py` HAMON o'z `_schema_default_overdue_days()`
ini saqlaydi** (07-13 ning 3-ochiq bandi). Manba bitta (sxema), o'quvchi
ikkita. Bu reja `reconciliation.py` ga **tegmadi**: uning yagona aloqasi —
`reconciliation_open` ni **import qilish**. Bir satrlik o'zgarish, egasi
o'zgarmadi.

**4. `tests/fixtures/notification_domain.py::ALLOWED_PAYLOAD_KEYS` hamon
vaqtinchalik nusxa** (07-06 dan beri ochiq). Bu rejaga to'sqinlik
**qilmadi**: `test_digest_qualifiers.py` fixture'ga umuman tayanmaydi —
u `_build_text()` ni **to'g'ridan-to'g'ri**, literal `payload` bilan
chaqiradi.

**5. `npm --prefix frontend test` ning VITEST yarmi bu worktree'da
BAJARILMADI.** `frontend/node_modules` gitignored va **yo'q**. ⚠ Bu reja
frontendga **tegdi** (uch xabar fayli + `alert-row.tsx`), ya'ni band
haqiqiy. Node'ga bog'liq bo'lmagan yarmi **to'liq bajarildi va yashil**:
`node --test frontend/scripts/*.test.mjs` -> **191 test**
(`check-messages` 1119 × 3, `gen-cyrillic --check` drift yo'q,
`glossary.test.mjs` G7-9, `snapshot-copy.test.mjs`).
⚠ **Bajarilmagani:** `alert-row.test.tsx` / `alert-list.test.tsx` — ya'ni
to'rt yangi `ALERT_TITLE_KEYS` yozuvining **render** natijasi o'lchanmadi.
**Egasi:** orkestrator (merge'dan keyin asosiy repoda `node_modules` bor).
Bu band 07-08 da ham **aynan shu** shaklda edi.

## Known Stubs

Yo'q. Bu reja UI yoki API yuzasi **qurmaydi** — u mavjud jobларni reyestrga
oladi. Birorta qattiq kodlangan bo'sh qiymat renderga oqmaydi. To'rt yangi
alert kaliti **matn bilan** keladi (uchala locale) va `alert-row.tsx`
xaritasiga ulangan, ya'ni «kalit bor, matn yo'q» holati **imkonsiz**.

`_normalize_locale()` ning fallbacki **stub emas**: u hujjatlashtirilgan va
o'lchangan mahsulot qarori (`test_an_unknown_locale_falls_back_instead_of_
raising`) — noma'lum til xabarni yiqitmaydi.

## Threat Flags

Yo'q. Yangi tarmoq endpointi, yangi auth yo'li, yangi fayl kirishi va sxema
o'zgarishi qo'shilmadi (birorta migratsiya yo'q, `pyproject.toml` va
`uv.lock` **tegilmadi**). `/internal/*` posturasi **kuchaytirildi ham,
bo'shatilmadi ham**: `self_check.py` ga faqat **to'rt satr** qo'shildi,
marshrut, autentifikatsiya va javob shakli **o'zgarmadi**; javob yuzasi
darvozasi (`test_self_check_response_surface_stays_narrow`) va
`tests/tenancy` ning **1945** testli to'plami yashil.

| Threat ID | Qanday yopildi |
|---|---|
| T-07-82 | To'rt komponent **ikki reyestrda**; `test_heartbeat_registry.py` uch manbani **AST-hosila** sifatida solishtiradi; **ikki sabotaj** bilan o'lchandi |
| T-07-83 | `outbox_stale` — `critical` **va** `never_suppressed`; xulqiy test bilan (`test_missing_new_heartbeat_raises_an_alert`) |
| T-07-84 | Uchala kunlik jadval `cron_offset: Asia/Tashkent` (reyestr metama'lumotidan o'lchandi); daqiqalik tik **ataylab** offsetsiz; `cron_offset` sanog'i 8 -> 13 |
| T-07-85 | Yangi daqiqalik job **o'z konstantasi** bilan; literal **aynan ikki marta** va **faqat konstanta e'lonida**; darvoza egalik to'plami bilan **kuchaytirildi** |
| T-07-86 | `test_expected_components_is_not_derived_from_the_table` — **AST** bilan literal kortej talab qilinadi (grep emas: izohni koddan ajratmaydi) |
| T-07-SC | Yangi paket **yo'q** — `pyproject.toml` va `uv.lock` tegilmadi |

## Self-Check: PASSED

Yaratilgan fayllar diskda mavjud:
- `tests/unit/test_heartbeat_registry.py` ✓
- `tests/unit/test_digest_qualifiers.py` ✓
- `.planning/phases/07-nomuvofiqlik-bildirishnoma-va-botlar/07-14-SUMMARY.md` ✓

Commitlar mavjud: `1bb4f3b` · `220b1df` · `2c9fbfa` · `e0e8826` · `5bdf57c`
(baza `ff9e5cb`).

`git diff --diff-filter=D --name-only ff9e5cb HEAD` — **BO'SH**, ya'ni
birorta fayl o'chirilmadi. O'zgargan fayllar — **14 ta**: sakkiztasi
rejaning `files_modified` ro'yxatidan, oltitasi yuqorida chetlanish
sifatida ochiq hujjatlashtirilgan.

⚠ `STATE.md` va `ROADMAP.md` **ATAYIN TEGILMADI** — worktree rejimida
ularni orkestrator markazlashgan holda yangilaydi.
