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
"""
