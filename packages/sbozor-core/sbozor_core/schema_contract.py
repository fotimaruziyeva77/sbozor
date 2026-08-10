"""Sxema reyestrlari — tenancy meta-testlari uchun YAGONA manba.

Bu modul faqat jadval NOMLARINI saqlaydi (model ham, DDL ham emas). Sabab:
meta-testlar "har bir jadvalda `market_id` bor, RLS ENABLE+FORCE qilingan va
tenant policy'si mavjud" degan invariantni `pg_catalog` dan tekshiradi, va
istisnolar ro'yxati TESTDA emas, shu yerda yashashi kerak. Shunda yangi
istisno qo'shish ataylab qilingan, ko'rinadigan va commit'da ko'zga
tashlanadigan harakat bo'ladi.

Kengaytirish qoidasi: yangi jadval qo'shilganda u AVTOMATIK ravishda
tenant-scoped deb hisoblanadi. Reyestrga qo'shish faqat istisno uchun —
va istisnoning sababi shu yerda izohda yozilishi shart.
"""

from __future__ import annotations

__all__ = ["AUDITED_TABLES", "FINANCIAL_TABLES", "GLOBAL_TABLES"]

GLOBAL_TABLES: frozenset[str] = frozenset(
    {
        # Identifikatsiya a'zolikdan ajratilgan (Pattern 2): login paytida
        # `app.market_id` hali NOMA'LUM, shuning uchun `users` da `market_id`
        # ustuni ham, tenant policy'si ham YO'Q. Uning o'rniga app-rolga
        # `REVOKE ALL` qo'yiladi va o'qish faqat ikkita tor `SECURITY DEFINER`
        # funksiya orqali o'tadi.
        "users",
        # `markets` — MAXSUS HOLAT, "global" emas (RESEARCH Open Question 4).
        # U tenant chegarasining O'ZI, shuning uchun policy'si boshqa
        # jadvallardagidan farq qiladi: `market_id = ...` emas, `id = ...`.
        # Meta-test uni umumiy tsikldan chiqarib, alohida qulflaydi
        # (`test_markets_rls_and_policy`, 01-04).
        "markets",
        # Alembic ning o'z buxgalteriyasi — ilova ma'lumoti emas.
        "alembic_version",
        # --- 4-faza (0014_snapshot_domain, FOUND-06) ---
        # Fon komponentlarining «oxirgi marta qachon ishladi» yozuvi
        # (`capture_tick`, `retention`, `backup`). Unda `market_id` ustuni
        # ATAYIN YO'Q, chunki komponent BOZORGA TEGISHLI EMAS: tik butun
        # platforma uchun bitta jarayonda ishlaydi va uning to'xtagani
        # hamma bozorga birdan tegadi.
        #
        # Bu FOUND-06 ning eng pastki qatlami — «detektorning O'ZI
        # bajarilmadi» holati. Uni tenant-scoped qilish mantiqiy xato
        # bo'lardi: tik umuman ishlamayotgan bo'lsa, uning yo'qligini
        # bozor kontekstida qidirish 0 qator berardi va sukunat
        # «hammasi joyida» bilan bir xil ko'rinardi (D-20).
        #
        # ⚠ `alert_events` bu ro'yxatda ATAYIN YO'Q va bo'lmasligi ham
        # kerak: unda `market_id NOT NULL` bor (ogohlantirish har doim
        # aniq bir bozorning kamerasiga tegishli) va UI uni bozor
        # sahifasida ko'rsatadi. `04-RESEARCH.md` §E.13 uni "global" deb
        # atagan, lekin o'sha yerdayoq unga `market_id` bergan — ikkisi
        # bir vaqtda to'g'ri bo'la olmaydi.
        "system_heartbeats",
    }
)
"""`market_id` ustuni va standart tenant policy'si BO'LMASLIGI kutilgan jadvallar.

`audit_log` bu ro'yxatda ATAYIN YO'Q va bo'lmasligi ham kerak: unda
`market_id` ustuni bor, RLS ENABLE+FORCE qilingan va o'qish policy'si oddiy
tenant predikatiga bo'ysunadi — ya'ni u umumiy invariantdan o'tadi. Uning
YAGONA farqi YOZISH tomonida: `audit_append` policy'si `WITH CHECK (true)`,
chunki jurnalga yozishni bloklash imkonsiz bo'lishi kerak (kontekstsiz
bajarilgan o'zgarish ham iz qoldirsin). O'sha bitta istisno
`tests/tenancy/test_meta.py::POLICY_TENANT_GUC_EXCEPTIONS` da sabab bilan
qayd etilgan.
"""

FINANCIAL_TABLES: frozenset[str] = frozenset(
    {
        "daily_charges",
        "charge_adjustments",
        "payments",
        # `tariffs` QOLADI: unda haqiqiy pul ustuni (`amount_soum`) bor va
        # uchala qo'riqchi ham ma'noga ega. Qo'riqchilari `financial_guards()`
        # bilan emas, 02-05 da QO'LDA yoziladi — tarif qatorida `created_at`
        # emas, `valid_from` biznes sanasi hukmron.
        "tariffs",
    }
)
"""Mezon #5 konstraytlari majburiy bo'lgan jadvallar.

Meta-test (`test_financial_tables_have_guards`) ro'yxatdagi har bir MAVJUD
jadvaldan UCHTA narsani talab qiladi: `business_date` STORED generated
ustuni, `CHECK (amount_soum > 0)` va `market_id` bilan boshlanadigan UNIQUE.
Ya'ni bu reyestr "pul yozuvi" degan da'vo, "audit kerak" degan da'vo emas —
audit qamrovi alohida `AUDITED_TABLES` da yashaydi.

1-fazada bu jadvallarning HECH BIRI hali mavjud emas (ular 2- va 6-fazalarda
tug'iladi). Reyestr shunga qaramay hozir yoziladi, chunki meta-test uni
"jadval mavjud bo'lsa — quyidagi konstraytlar ham bo'lishi shart" shaklida
ishlatadi: shunda 6-fazada `payments` yaratilgan kuni darvoza avtomatik
yopiladi va hech kim `UNIQUE(market_id, idempotency_key)` ni unutib
qo'ymaydi.

`stall_assignments` bu ro'yxatdan ATAYIN OLIB TASHLANDI (2-faza, Pitfall 3).
Biriktirish jadvalida pul ustuni YO'Q va D-10 bo'yicha BO'LMASLIGI ham kerak:
qarz `daily_charges` da tug'iladi va sotuvchida jamlanadi. U ro'yxatda
qolganda jadval tug'ilgan kuni meta-test `stall_assignments: CHECK
(amount_soum > 0) yo'q` bilan qizarardi va yagona "tuzatish" yo'li unga
soxta pul ustuni qo'shish bo'lardi — ya'ni reyestr sxemani noto'g'ri
shaklga majburlagan bo'lardi. Uning o'rniga u `AUDITED_TABLES` ga
qo'shilgan: D-10 aynan AUDITni talab qiladi, pul konstraytini emas.

3-FAZA BU REYESTRGA HECH NIMA QO'SHMAYDI va bu ATAYIN (`03-PATTERNS.md` §0).
`nvr_devices`, `nvr_credentials`, `cameras`, `nvr_discovery_runs` —
to'rtalasida ham pul ustuni YO'Q. Birortasini qo'shish 2-fazadagi Pitfall 3
ni takrorlardi: `test_financial_tables_have_guards` undan
`CHECK (amount_soum > 0)` talab qilardi va yagona "tuzatish" yo'li soxta
pul ustuni qo'shish bo'lardi.

4-FAZA HAM BU REYESTRGA HECH NIMA QO'SHMAYDI va bu ATAYIN. Beshala
snapshot jadvalida (`snapshot_schedules`, `snapshot_schedule_slots`,
`capture_runs`, `snapshots`, `alert_events`) pul ustuni YO'Q — bu faza
kadrni yetkazib beradi va sifatini belgilaydi, undan XULOSA CHIQARMAYDI
(billing 6-fazada). `snapshots` ni bu yerga qo'shish 3-fazadagi bilan
aynan bir xil tuzoqni ochardi: test undan `CHECK (amount_soum > 0)` va
`business_date` ni talab qilardi, birinchisining yagona "tuzatishi" esa
soxta pul ustuni bo'lardi.

⚠ CHALKASHTIRMANG: `snapshots` da `business_date` HAQIQATAN bo'ladi
(D-16), lekin u `FINANCIAL_TABLES` ning talabi sifatida emas —
idempotentlik kaliti `(market_id, camera_id, slot, business_date)` ning
qismi sifatida. Billing kafolati bu yerda BOSHQA mexanizm bilan
quriladi: `UNIQUE (id, is_billable)` langari va 5-fazadagi kompozit FK.

6-FAZA HAM BU REYESTRGA HECH NIMA QO'SHMAYDI va bu ATAYIN. Uchala
moliyaviy jadval (`daily_charges`, `charge_adjustments`, `payments`)
1-fazadan BERI shu yerda — reyestrni oldindan yozishning butun ma'nosi
shu edi va `0020` qo'ngan kuni darvoza O'ZI YOPILDI.

Qolgan uchtasi ATAYIN QO'SHILMAYDI va sabab yuqoridagi
`stall_assignments` (Pitfall 3) bilan AYNAN bir xil sinfda:

  * `cashier_shifts` — unda PUL BOR (`declared_soum`, `system_soum`),
    lekin ⛔ `amount_soum` NOMLI USTUN YO'Q va bo'lishi ham kerak emas:
    smena qatorida BITTA summa emas, IKKI TOMONLAMA solishtiruv yashaydi
    (ko'r deklaratsiya va tizim summasi). `test_financial_tables_have_
    guards` esa `amount_soum\\s*>\\s*0` regeksini izlaydi, ya'ni yagona
    «tuzatish» yo'li SOXTA PUL USTUNI qo'shish bo'lardi. Ustiga
    `declared_soum = 0` QONUNIY holat (butun smena terminalda o'tdi,
    UI-SPEC §10.2) — `> 0` sharti uni imkonsiz qilardi.
  * `billing_anomalies` — pul ustuni UMUMAN YO'Q: anomaliya aynan hisob
    YOZILMAGAN holat (C-12).
  * `charge_evidence` — dalil pointerlari, pul emas; summa `charge_id`
    ko'rsatgan `daily_charges` qatorida.
"""

AUDITED_TABLES: frozenset[str] = frozenset(
    {
        # 1-fazada DB-trigger qo'llanadigan yagona jadval: rol berish/olib
        # tashlash — huquq ko'tarilishining asosiy yo'li, shuning uchun u
        # moliyaviy jadvallardan oldin audit ostiga olinadi.
        "user_market_roles",
        # --- 2-faza domen jadvallari (02-05 va 02-06 migratsiyalari) ---
        # Haftalik ish jadvali: yopiq kun qo'shilishi o'sha kunning butun
        # tushumini nolga tushiradi (D-17/D-18) — kim va qachon o'zgartirgani
        # izsiz qolmasligi kerak.
        "market_profile",
        # Rasta holati (faol/ta'mirda/yopiq) va kodi — "band, lekin to'lovsiz"
        # da'vosining asosi. Holat jimgina "yopiq" ga o'tsa hisob yo'qoladi (SC#2).
        "stalls",
        # Rastaning mahsulot toifasi tarixi (D-04): toifa tarif orqali
        # to'g'ridan-to'g'ri summani belgilaydi.
        "stall_category_periods",
        # Tarif tarixi (D-06/D-07): pul miqdorining o'zi.
        "tariffs",
        # Sotuvchi — SHAXSIY MA'LUMOT (F.I.Sh., telefon). 1-faza D-09 bo'yicha
        # bunday ma'lumotning O'ZGARISHI ham, O'QILISHI ham auditda.
        "vendors",
        # Biriktirish davri — qarz EGALIGINI belgilaydi (D-10). Davr chegarasi
        # bir kunga surilsa qarz boshqa odamga o'tadi.
        "stall_assignments",
        # Yopiq kun istisnolari (MARKET-05) — `market_profile` bilan bir xil
        # sababdan: bitta qator butun kunlik hisobni o'chiradi.
        "market_calendar_exceptions",
        # --- 3-faza NVR domeni (0012_nvr_domain) ---
        # NVR qurilmasi: manzil (`host`/`port`) va `username` o'zgarishi
        # butun bozorning kameralarga kirish yo'lini boshqa qurilmaga
        # burib yuborardi — "kim va qachon burdi" izsiz qolmasligi kerak.
        "nvr_devices",
        # Kamera (kanal): `name_overridden`/`is_archived`/`status` bayroqlari
        # 5-fazadagi zona va 4-fazadagi snapshot zanjirining kirishi. Kanal
        # jimgina arxivlansa o'sha rastaning "band, lekin to'lovsiz"
        # dalili yo'qoladi (SC#2).
        "cameras",
        # --- 4-faza snapshot quvuri (0014_snapshot_domain) ---
        # Bozorning kadr olish jadvali: qaysi kunlarda, qaysi soatlarda
        # kadr olinadi. Slot olib tashlansa o'sha vaqtdagi "band, lekin
        # to'lovsiz" dalili UMUMAN tug'ilmaydi va hisobot kamaygani
        # bilinmaydi — ya'ni jadvalni tahrirlash nazoratni JIMGINA
        # o'chirishning eng arzon yo'li.
        "snapshot_schedules",
        # Jadvalning aniq vaqtlari (`06:00`, `06:30`, ...). Bitta slotni
        # o'chirish yuqoridagi bilan aynan bir xil oqibatga olib keladi,
        # faqat mayda donadorlikda — shuning uchun ikkalasi ham auditda.
        "snapshot_schedule_slots",
        # --- 5-faza bandlik domeni (0018_occupancy_domain) ---
        # ⚠ IKKALA NOM HAM JADVAL TUG'ILISHIDAN OLDIN qo'shildi (`05-01`/T1)
        # va shuning uchun ular `tests/tenancy/test_meta.py::
        # PENDING_AUDIT_TRIGGERS` da AYNI COMMITDA ro'yxatga olingan. Reyestr
        # IKKI TOMONLAMA qulflangan (`missing == PENDING_AUDIT_TRIGGERS`):
        # bu yerga qo'shib u yerga qo'shmaslik `regressed` bilan, `0018`
        # triggerlarni ulagandan keyin u yerdan O'CHIRMASLIK esa `closed`
        # bilan qizartiradi. Ya'ni darvoza `05-01` dan `05-05` gacha YASHIL
        # turadi va qarz JIMGINA yopilib keta olmaydi.
        #
        # Kamera zonasi (poligon) — «band, lekin to'lovsiz» da'vosining
        # GEOMETRIK asosi. Poligon jimgina siljitilsa yoki zona o'chirilsa
        # o'sha rastaning dalili UMUMAN tug'ilmaydi va hisobot kamaygani
        # bilinmaydi — `cameras.is_archived` bilan aynan bir xil sinf:
        # nazoratni jimgina o'chirishning eng arzon yo'li.
        "camera_zones",
        # Nazoratchining verdikti — INSONNING moliyaviy oqibatli qarori:
        # u AI ning javobini bekor qiladi va kunlik patta hisobini
        # o'zgartiradi (AI-06). `tariffs` / `stall_assignments` bilan bir
        # oilada. ⚠ `occupancy_events` bu ro'yxatda ATAYIN YO'Q — sabab
        # `migrations/entities/__init__.py::OCCUPANCY_AUDITED_TABLES`
        # docstringida (hajm: ~5000 qator/kun/bozor, VA jadval D-12
        # bo'yicha SHARTSIZ o'zgarmas — o'zgarmas jadval uchun audit faqat
        # INSERT ni ko'rardi, ya'ni ikkinchi nusxa yozardi).
        "zone_reviews",
        # --- 6-faza billing domeni (0020_billing_domain) ---
        # ⚠ IKKALA NOM HAM JADVAL TUG'ILISHIDAN OLDIN qo'shildi (06-04/T1)
        # va shuning uchun ular `tests/tenancy/test_meta.py::
        # PENDING_AUDIT_TRIGGERS` da AYNI COMMITDA ro'yxatga olingan
        # (OP-4). Reyestr IKKI TOMONLAMA qulflangan: bu yerga qo'shib u
        # yerga qo'shmaslik `regressed` bilan, `0020` triggerlarni
        # ulagandan keyin u yerdan O'CHIRMASLIK esa `closed` bilan
        # qizartiradi. `05-01`→`05-05` juftligining AYNAN takrori.
        #
        # Hisob tuzatishi — INSONNING moliyaviy oqibatli qarori: u
        # yozilgan pattaning summasini o'zgartiradi (D-19). `tariffs` va
        # `zone_reviews` bilan BIR OILADA. Sabab-kod yopiq ro'yxatdan
        # bo'lgani AUDITNI ORTIQCHA QILMAYDI: «qaysi sabab» qatorda,
        # «kim va qachon» esa faqat jurnalda.
        "charge_adjustments",
        # Kassir smenasi — ko'r deklaratsiya (CASH-04) nizoda dalil bo'ladi
        # va smenaning ochilishi/yopilishi INSON qarori. `0020` unga
        # SHARTLI o'zgarmaslik qo'riqchisini qo'yadi (`open` -> `closed`
        # o'tishi ruxsat), ya'ni jadval `daily_charges` dan farqli o'laroq
        # HAQIQATAN `UPDATE` ni ko'radi — audit esa aynan o'sha o'tishni
        # yozadi. Bu «o'zgarmas jadvalga audit qo'yilmaydi» qoidasiga zid
        # emas, u qoidaning TESKARI tomoni.
        "cashier_shifts",
    }
)
"""`fn_audit_row()` triggeri O'RNATILGAN jadvallar (hozirgi holat, kutilgan emas).

Bu reyestr `FINANCIAL_TABLES` bilan ATAYIN birlashtirilmagan: u pul
konstraytlarini emas, AUDIT qamrovini bildiradi. Har yangi jadval
tug'ilganda `attach_audit_trigger()` bilan birga shu ro'yxatga ham bir satr
qo'shiladi — meta-test shu ikki manbani `pg_trigger` bilan solishtiradi.

DIQQAT — ORALIQ HOLAT (2-faza, ATAYIN): yuqoridagi yetti domen jadvali
02-05 va 02-06 migratsiyalari `attach_audit_trigger()` ni chaqirgandan
KEYIN haqiqat bo'ladi. O'sha migratsiyalar yozilmaguncha
`tests/tenancy/test_meta.py::test_audited_tables_have_trigger` QIZIL turadi
va bu KUTILGAN: qizil test aynan hali yopilmagan qarzni ko'rsatadi. Teskari
tartib (avval migratsiya, keyin reyestr) darvozani vaqtincha ochiq
qoldirardi — ya'ni triggersiz jadval hech qayerda ko'rinmasdan o'tib
ketishi mumkin bo'lardi.

RO'YXATGA KIRMAYDIGANLAR va sababi:
  * `zones`, `stall_categories` — nomlar lug'ati. Ular moliyaviy ham,
    huquqiy ham yozuv emas; ularga havola qiluvchi jadvallar
    (`stalls`, `stall_category_periods`) allaqachon auditda.
  * `stall_code_registry` — birlamchi kaliti `(market_id, code)`, ya'ni
    unda `id uuid` ustuni YO'Q. `fn_audit_row()` esa `row_id` ni `uuid` ga
    keltiradi va bunday jadvalda ishga tushirilsa har DML da yiqilardi
    (`attach_audit_trigger()` docstringidagi TALAB).
  * `nvr_credentials` — IKKI MUSTAQIL sabab, bir xil qaror (3-faza, SC#4):
      (a) `fn_audit_row()` `to_jsonb(NEW)` yozadi, ya'ni Fernet SHIFRMATNI
          `audit_log.new_value` ga tushardi. Kalit buzilganda bu TARIXIY
          parollarni beradi va `audit_log` (append-only, o'chirib
          bo'lmaydigan) eng uzoq yashaydigan sir omboriga aylanardi;
      (b) birlamchi kaliti `nvr_id`, ya'ni `id uuid` ustuni YO'Q — yuqoridagi
          `stall_code_registry` bilan aynan bir xil texnik to'siq.
    Audit izi yo'qolmaydi: parol o'zgarishining FAKTI ilova qatlamida
    `nvr_devices` ustiga QIYMATSIZ yoziladi
    (`action='nvr_credentials_updated'`).
  * `capture_runs`, `snapshots`, `alert_events` — IKKI MUSTAQIL sabab,
    bir xil qaror (4-faza):
      (a) uchalasi ham HODISA JURNALI va faqat QO'SHILADI (odam
          tahrirlamaydi) — audit ularning ustiga o'sha ma'lumotning
          IKKINCHI NUSXASINI yozardi (`nvr_discovery_runs` bilan bir xil
          sinf);
      (b) HAJM: 175 kadr/kun/bozor × har holat o'tishi
          (`pending`->`running`->`succeeded`) ≈ kuniga 525 audit qatori
          BITTA bozordan; o'nta bozorda yiliga ~1.9 mln qator. `audit_log`
          append-only, ya'ni u hech qachon kichraymaydi.
    Audit izi yo'qolmaydi: JADVAL o'zgarishi (kim kadr olish rejasini
    o'zgartirdi) `snapshot_schedules`/`snapshot_schedule_slots` orqali
    auditda, KUNLIK YUGURISHLAR esa `capture_runs` ning O'ZIDA tarixga
    ega (`status`, `attempt_count`, `error_code`, vaqt tamg'alari).
  * `daily_charges` (6-faza) — jadval D-07 bo'yicha SHARTSIZ o'zgarmas
    (`charge_immutable()`), ya'ni audit FAQAT `INSERT` ni ko'rardi va bu
    o'sha ma'lumotning IKKINCHI NUSXASI bo'lardi (`occupancy_events`
    bilan aynan bir xil dalil). Ikkinchi, mustaqil sabab HAJM:
    ~300–1000 qator/kun/bozor va `audit_log` hech qachon kichraymaydi.
    Iz yo'qolmaydi: summani o'zgartiradigan YAGONA yo'l
    `charge_adjustments` va U auditda.
  * `payments` (6-faza) — jadval APPEND-ONLY (`payment_immutable()`) va
    iz `payments` NING O'ZIDA yashaydi: `kind`, `reverses_payment_id`,
    `reversal_reason`, `override_reason`, `cashier_id`. Ya'ni «kim, nima
    qildi, nega» savolining javobi qatorning ichida. Ilova darajasidagi
    audit esa `AuditAction.PAYMENT_OVERRIDE` / `PAYMENT_REVERSE` bilan
    yoziladi (06-09) — `enums.py::AuditAction` o'sha ikki a'zoni AYNAN
    shu sababdan qo'shgan.
  * `billing_anomalies` (6-faza) — HODISA JURNALI: uni odam
    tahrirlamaydi, `billing_close` jobi yozadi (`capture_runs` /
    `alert_events` bilan bir sinfda).
  * `charge_evidence` (6-faza) — `daily_charges` ning MUZLATILGAN
    nusxasi; u ham hech qachon tahrirlanmaydi.
"""
