"""Billing domenining META-INVARIANTLARI — hammasi `pg_catalog` dan.

=============================================================================
NEGA BU FAYL MODELNI IMPORT QILMAYDI.

`sbozor_core.models.billing` — ISTALGAN holat. Bazadagi sxema esa HAQIQIY
holat. Ikkisi ajralib qolishi mumkin (migratsiya qo'llanmagan, konstrayt
migratsiyada unutilgan, kimdir qo'lda `ALTER TABLE` qilgan) va aynan o'sha
holatda modeldan o'qiydigan test JIMGINA yashil qolardi.
`test_market_domain_meta.py` bu qoidani 2-fazada o'rnatgan,
`test_occupancy_domain_meta.py` uni 5-fazada davom ettirgan; bu fayl esa
6-fazada.

⚠ ISTISNO — ENUM REYESTRI. `test_every_check_is_derived_from_enum()`
`sbozor_core.enums` ni ATAYIN import qiladi: uning butun savoli aynan
«`CHECK` enumdan HOSILAMI?» va u ikkala tomonni ko'rmasdan javob bera
olmaydi. Import KONTENT uchun (enum a'zolarining QIYMATLARI DB kontenti),
KONSTRAYT IFODASI uchun EMAS — `billing.py` dagi `*_CHECK` konstantalari
bu faylda umuman ishlatilmaydi, aks holda test o'z kutilmasini o'zi
yozgan bo'lardi.
=============================================================================

O'N UCH INVARIANT VA HAR BIRI QAYSI DA'VONI QULFLAYDI:

  1. Idempotentlik kaliti `service_date` USTIDA — C-2 ning mexanik yarmi.
     `business_date` kalitga tushsa kunni QAYTA yopish ikkinchi hisob
     yaratardi.
  2. `business_date` beshala jadvalda HOSILA ustun — unga qiymat yozib
     bo'lmaydi, ya'ni audit fakti soxtalashtirilmaydi.
  3. `service_date` HOSILA EMAS — teskari yo'nalish. Ikki ustunning
     MA'NOSI aralashib ketmasligining mexanik yarmi.
  4. `CHECK (service_date <= business_date)` — kelajak kuniga hisob
     yozib bo'lmaydi (D-06).
  5. `payments` da `charge_id` YO'Q (C-4) — to'lov SOTUVCHI darajasidagi
     kredit. To'plam TENGLIGI bilan (D-31).
  6. `quote_soum` juftlangan `CHECK` — D-19 ilova qatlamidan SXEMAGA
     ko'chgan.
  7. Ikkala storno `CHECK` i ham IKKI TOMONLAMA (`=`), implikatsiya
     (`OR`) EMAS.
  8. Anomaliya `kind` i va dalili JUFT (C-12, D-29).
  9. Bir kassirda bir ochiq smena — QISMAN UNIQUE indeks (D-27),
     ilova mantig'i emas.
 10. Har `CHECK` enumdan HOSILA va to'plamlar TENG (D-31/D-32).
 11. Saqlangan qoldiq ustuni HECH QAYERDA yo'q (BILL-03).
 12. Ustun tiplari to'plami TENG — `float`/`numeric` paydo bo'lsa
     darvoza qizaradi (G-3, D-11).
 13. Migratsiyada QO'LDA yozilgan qiymat ro'yxati YO'Q — 10-bandning
     SHARTI: ikkinchi nusxa tug'ilmasa, ajralish ham tug'ilmaydi (D-32).
     Bu invariant 06-05 ning S-C sabotajidan TUG'ILDI va uning sababi
     `test_every_check_is_derived_from_enum()` docstringining oxirida
     o'lchov bilan yozilgan.

O'zgarmaslik triggerlarining XULQI bu yerda o'lchanmaydi — u
`tests/integration/test_billing_immutable.py` da. Shakl va xulq ikki xil
savol va ikkalasi ham alohida buzilishi mumkin.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from psycopg import Connection
from psycopg.rows import TupleRow
from sbozor_core.enums import (
    AdjustmentDirection,
    AdjustmentReason,
    AnomalyKind,
    PaymentKind,
    PaymentMethod,
    ReversalReason,
    ShiftStatus,
)

pytestmark = pytest.mark.tenancy

BILLING_TABLES: tuple[str, ...] = (
    "cashier_shifts",
    "daily_charges",
    "charge_adjustments",
    "charge_evidence",
    "payments",
    "billing_anomalies",
)
"""`0020` yaratgan OLTALA jadval — tip darvozasi (G-3) shular ustidan yuradi."""

BUSINESS_DATE_TABLES: tuple[str, ...] = (
    "daily_charges",
    "charge_adjustments",
    "payments",
    "cashier_shifts",
    "billing_anomalies",
)
"""`business_date` HOSILA ustuni BOR jadvallar — BESHTA, oltita EMAS.

⛔ `charge_evidence` ATAYIN YO'Q va bu 06-04 ning o'lchangan qarori: dalil
qatori kunni `daily_charges` dan (`charge_id` orqali) MEROS qiladi.
Ikkinchi hosila sana yarim tunda bir kun farq qilishi mumkin edi
(Pitfall 3) va o'shanda o'sha hisobning dalili hisobotda «yo'q» bo'lib
qolardi. Ro'yxatga `charge_evidence` ni qo'shish testni o'sha qarorga
qarshi qo'yardi.
"""

IDEMPOTENCY_KEY = "uq_daily_charges_market_id_stall_id_service_date"
"""D-06 ning idempotentlik kaliti — 6-faza uni AYNAN shu nom bilan izlaydi."""

SHIFT_OPEN_INDEX = "uq_cashier_shifts_market_id_cashier_open"
"""D-27 ning QISMAN UNIQUE indeksi."""

PAYMENT_COLUMNS: frozenset[str] = frozenset(
    {
        "id",
        "market_id",
        "stall_id",
        "vendor_id",
        "service_date",
        "amount_soum",
        "quote_soum",
        "kind",
        "method",
        "reverses_payment_id",
        "reversal_reason",
        "override_reason",
        "idempotency_key",
        "request_fingerprint",
        "shift_id",
        "cashier_id",
        "created_at",
        "business_date",
    }
)
"""`payments` ning KUTILGAN ustunlari — LITERAL yozilgan (D-31).

⛔ `assert "charge_id" not in columns` SHAKLI ATAYIN RAD ETILDI. U faqat
BITTA nomni qo'riqlardi: ertaga qo'shilgan `allocated_soum`,
`charge_ids uuid[]` yoki `settled_charge_id` uni CHETLAB o'tardi va C-4
ning qarori («to'lov SOTUVCHI darajasidagi kredit») jimgina buzilardi.

To'plam TENGLIGI esa IKKI YO'NALISHNI ham qulflaydi: kutilmagan ustun
qo'shilishi ham, kutilgan ustunning yo'qolishi ham darvozani qizartiradi.
Ro'yxatni yangilash ARZON, lekin u ONGLI qadam bo'ladi.
"""

BALANCE_SCANNED_TABLES: tuple[str, ...] = (
    "daily_charges",
    "payments",
    "charge_adjustments",
    "vendors",
    "stalls",
)
"""BILL-03 ning yuzasi — «qarzdorlik» tabiiy ravishda qo'nadigan jadvallar.

`vendors` va `stalls` ham ro'yxatda va bu ATAYIN: saqlangan qoldiq
odatda BILLING jadvaliga emas, «egasi» ga yoziladi
(`vendors.balance_soum` — eng ehtimolli shakl).
"""

ALLOWED_DATA_TYPES: frozenset[str] = frozenset(
    {
        "uuid",
        "bigint",
        "date",
        "text",
        "timestamp with time zone",
        "time without time zone",
    }
)
"""G-3 — oltala jadvalda RUXSAT ETILGAN `information_schema` tiplari.

⛔ SOLISHTIRUV TO'PLAM TENGLIGI BILAN, `not in` BILAN EMAS (D-31).
`assert "double precision" not in types` shakli faqat SANAB O'TILGAN
tiplarni qo'riqlardi: `numeric(12,2)`, `real`, `money` yoki
`double precision[]` uni chetlab o'tardi va D-11 («pul — `bigint` so'm»)
jimgina buzilardi. Tenglik esa HAR QANDAY yangi tipni ushlaydi.

⚠ `time without time zone` RO'YXATDA VA U MAJBURIY: `charge_evidence.
slot_time` — `stall_slot_occupancy` DAN nusxalanadigan slot vaqti
(«qaysi slot hisobga sabab bo'ldi»). Uni `text` qilish slotlarni
taqqoslashni matn taqqoslashiga aylantirardi.

⚠ `boolean` RO'YXATDA YO'Q va bu O'LCHANGAN FAKT, unutish emas: oltala
jadvalning birortasida ham bayroq ustuni yo'q. Holat `text` + enumdan
hosila `CHECK` bilan ifodalanadi (`status`, `kind`, `direction`) —
`is_closed`/`is_reversed` shaklidagi bayroq ikkinchi haqiqat manbai
bo'lardi. Ro'yxatga `boolean` ni «har ehtimolga qarshi» qo'shish
o'sha qarorni JIMGINA bo'shatardi.
"""

ENUM_BACKED_COLUMNS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("cashier_shifts", "status", tuple(m.value for m in ShiftStatus)),
    ("payments", "kind", tuple(m.value for m in PaymentKind)),
    ("payments", "method", tuple(m.value for m in PaymentMethod)),
    ("payments", "reversal_reason", tuple(m.value for m in ReversalReason)),
    ("payments", "override_reason", tuple(m.value for m in AdjustmentReason)),
    ("charge_adjustments", "direction", tuple(m.value for m in AdjustmentDirection)),
    ("charge_adjustments", "reason_code", tuple(m.value for m in AdjustmentReason)),
    ("billing_anomalies", "kind", tuple(m.value for m in AnomalyKind)),
)
"""(jadval, ustun, KUTILGAN qiymatlar) — qiymatlar ENUMDAN ITERATSIYA bilan.

⛔ QIYMATLAR QO'LDA KO'CHIRILMAYDI. Literal ro'yxat yozilganda backendga
yangi a'zo qo'shilib migratsiya yozilmasa IKKALA tomon ham eski holatda
qolardi va darvoza JIMGINA yashil bo'lardi — ya'ni test aynan o'zi
qo'riqlashi kerak bo'lgan holatni o'tkazib yuborardi (D-32).

⚠ YETTI ENUM, SAKKIZ QATOR: `AdjustmentReason` IKKI ustunni oziqlantiradi
(`charge_adjustments.reason_code` va `payments.override_reason`). Bu
06-04 ning ONGLI qarori — «nega hisob tuzatildi?» va «nega server bergan
summadan chetlandik?» BIR XIL sabablar to'plami. Ikkinchi enum ikki
ro'yxatni ajralib ketadigan qilardi.
"""

CONSTRAINT_DEFS = """
SELECT con.conname, pg_get_constraintdef(con.oid)
FROM pg_constraint con
JOIN pg_class c ON c.oid = con.conrelid
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public'
  AND c.relname = %s
  AND con.contype = %s
"""
"""Jadvalning konstraytlari — TA'RIFI bilan.

`pg_constraint` ishlatiladi (`information_schema` emas): oxirgisi o'z
ko'rinishlarini joriy rolning grant'lari bo'yicha filtrlaydi, ya'ni huquqi
tor rol ostida jimgina KAM konstrayt qaytarardi va darvoza sababsiz yashil
bo'lib qolardi (`test_occupancy_domain_meta.py` da o'rnatilgan qoida).
"""

GENERATED_COLUMN = """
SELECT a.attgenerated
FROM pg_attribute a
JOIN pg_class c ON c.oid = a.attrelid
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public'
  AND c.relname = %s
  AND a.attname = %s
  AND a.attnum > 0
  AND NOT a.attisdropped
"""

TABLE_COLUMNS = """
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = %s
"""
"""⚠ `information_schema` ATAYIN — reja G-3 ni AYNAN `data_type` bo'yicha
ta'riflaydi. Grant filtri xavfi NAZORAT ASSERTI bilan yopiladi: bo'sh
to'plam HAR DOIM yiqiladi, ya'ni «ko'rinmadi» «yo'q» ga aylanmaydi."""

INDEX_DEF = "SELECT indexdef FROM pg_indexes WHERE schemaname = 'public' AND indexname = %s"


def _defs(conn: Connection[TupleRow], table: str, contype: str) -> dict[str, str]:
    return {
        str(row[0]): str(row[1])
        for row in conn.execute(CONSTRAINT_DEFS, (table, contype)).fetchall()
    }


def _canonical(definition: str) -> str:
    """`pg_get_constraintdef` chiqishini SHAKLDAN mustaqil ko'rinishga keltiradi.

    Ikki narsa olib tashlanadi va ikkalasi ham MA'NOGA ta'sir qilmaydi:
    `::text` kastlari (PostgreSQL ularni o'zi qo'shadi) va ortiqcha
    bo'shliqlar. Qavslar QOLDIRILADI — aynan ular «ikki tomonlama
    tenglik» bilan «implikatsiya» ni ajratadi va ularni tozalash testni
    o'z da'vosidan mahrum qilardi.
    """
    return re.sub(r"\s+", " ", definition.replace("::text", "")).strip()


def _columns(conn: Connection[TupleRow], table: str) -> dict[str, str]:
    rows = conn.execute(TABLE_COLUMNS, (table,)).fetchall()
    columns = {str(row[0]): str(row[1]) for row in rows}
    assert columns, (
        f"`{table}` uchun `information_schema.columns` 0 qator qaytardi. "
        "Jadval yo'q, yoki joriy rolda unga birorta huquq yo'q — ikkala "
        "holatda ham quyidagi da'vo BO'SH ROST bo'lib qolardi."
    )
    return columns


def _unique_columns(conn: Connection[TupleRow], table: str, name: str) -> tuple[str, ...]:
    """`UNIQUE (a, b, c)` -> `('a', 'b', 'c')`."""
    uniques = _defs(conn, table, "u")
    assert name in uniques, f"`{table}` da `{name}` konstrayti YO'Q. Mavjudlari: {sorted(uniques)}"
    match = re.fullmatch(r"UNIQUE\s*\((.*)\)", _canonical(uniques[name]))
    assert match is not None, f"`{name}` `UNIQUE (...)` shaklida emas: {uniques[name]!r}"
    return tuple(part.strip() for part in match.group(1).split(","))


def test_daily_charges_idempotency_key_is_on_service_date(
    sync_app_conn: Connection[TupleRow], migrated: None
) -> None:
    """Idempotentlik kaliti `service_date` USTIDA — `business_date` USTIDA EMAS (C-2/D-06).

    =========================================================================
    ⛔ BU FAZANING ENG QIMMAT BITTA KONSTRAYTI VA UNI BUZISH UCHUN HECH
       NIMANI «BUZISH» KERAK EMAS — bitta ustun nomini almashtirish yetarli.

    Kun ERTASI KUNI 04:10 da yopiladi (C-3), ya'ni hisob HISOBLANAYOTGAN
    kundan KEYINGI kunda yoziladi. Kalit `business_date` ustida bo'lsa
    kunni QAYTA yopish (yoki backfill) IKKINCHI hisob yaratardi va
    sotuvchi bir kun uchun IKKI MARTA qarzdor bo'lardi — nizoda esa
    ikkala qator ham «to'g'ri» ko'rinardi.

    ⚠ TO'PLAM TENGLIGI EMAS, KETMA-KETLIK TENGLIGI: `UNIQUE` ustunlarining
      TARTIBI indeksning prefiks xususiyatini belgilaydi va `market_id`
      BIRINCHI bo'lishi tenant invarianti #5 (`test_meta.py::
      test_financial_tables_have_guards` ning uchinchi sharti).
    =========================================================================
    """
    columns = _unique_columns(sync_app_conn, "daily_charges", IDEMPOTENCY_KEY)

    assert columns == ("market_id", "stall_id", "service_date"), (
        f"`{IDEMPOTENCY_KEY}` ustunlari {columns} — kutilgani "
        "`('market_id', 'stall_id', 'service_date')`."
    )
    assert "business_date" not in columns, (
        f"idempotentlik kalitida `business_date` bor ({columns}) — kunni "
        "qayta yopish IKKINCHI hisob yaratadi va bu C-2 ning aynan o'zi."
    )


def test_business_date_is_generated_on_every_billing_table(
    sync_app_conn: Connection[TupleRow], migrated: None
) -> None:
    """Beshala jadvalda `business_date` HOSILA ustun (`attgenerated = 's'`).

    =========================================================================
    HOSILA USTUNGA QIYMAT YOZIB BO'LMAYDI va aynan shu uni AUDIT FAKTI
    qiladi. Oddiy ustun bo'lganda backfill skripti (yoki xato yozgan
    kassir) «bu qator kecha yozilgan» deb ko'rsata olardi va D-02 ning
    nizo modeli — «qaysi yozuv dalil?» — javobsiz qolardi.

    ⚠ RAD ETISHNING XULQI ALOHIDA o'lchanadi (`test_business_date.py:
      134-145`), bu yerda faqat SHAKL. Ikkalasi alohida buzilishi mumkin:
      ustun hosila bo'lib qolib, ilova unga baribir yozishga urinishi
      (va xatoni yutishi) mumkin edi.
    =========================================================================
    """
    for table in BUSINESS_DATE_TABLES:
        row = sync_app_conn.execute(GENERATED_COLUMN, (table, "business_date")).fetchone()
        assert row is not None, f"`{table}.business_date` `pg_attribute` da topilmadi"
        assert row[0] == "s", (
            f"`{table}.business_date` HOSILA ustun EMAS ({row[0]!r}) — unga "
            "qiymat yozish yo'li ochiq qolgan va audit fakti "
            "soxtalashtirilishi mumkin (C-2)."
        )

    # NAZORAT: `charge_evidence` da bu ustun UMUMAN YO'Q (06-04 ning
    # qarori). Usiz yuqoridagi tsikl «ro'yxat qisqarib qolgan» holatni
    # ham yashil ko'rsatardi.
    assert "business_date" not in _columns(sync_app_conn, "charge_evidence"), (
        "`charge_evidence` ga `business_date` qo'shilgan — dalil qatori "
        "kunni `daily_charges` dan MEROS qilishi kerak, ikkinchi hosila "
        "sana yarim tunda bir kun farq qilib dalilni 'yo'q' qilardi "
        "(Pitfall 3)."
    )


def test_service_date_is_not_generated(sync_app_conn: Connection[TupleRow], migrated: None) -> None:
    """`service_date` HOSILA EMAS — TESKARI YO'NALISH (C-2 ning ikkinchi yarmi).

    =========================================================================
    ⚠ YUQORIDAGI TESTNING JUFTI VA USIZ U YARIM DA'VO BO'LARDI.

    Ikkala ustun ham sana, ikkalasi ham bir xil jadvalda va ular IKKI XIL
    SAVOLGA javob beradi:

        service_date  — hisob QAYSI KUN uchun yozildi (DOMEN sanasi)
        business_date — qator QAYSI KUNDA yozildi   (AUDIT fakti)

    `service_date` ni ham hosila qilish (masalan `created_at` dan)
    ikkalasini bitta faktga aylantirardi: backfill qilingan hisob
    o'zining HISOBLANGAN kunini yo'qotardi va D-06 ning idempotentlik
    kaliti ma'nosini butunlay o'zgartirardi — u «yozilgan kun» kaliti
    bo'lib qolardi.
    =========================================================================
    """
    for table in ("daily_charges", "payments"):
        row = sync_app_conn.execute(GENERATED_COLUMN, (table, "service_date")).fetchone()
        assert row is not None, f"`{table}.service_date` `pg_attribute` da topilmadi"
        assert (row[0] or "") == "", (
            f"`{table}.service_date` HOSILA ustun ({row[0]!r}) — domen sanasi "
            "audit faktidan hisoblanyapti va ikki ustun bitta faktga "
            "aylangan (C-2)."
        )


def test_service_date_cannot_exceed_business_date(
    sync_app_conn: Connection[TupleRow], migrated: None
) -> None:
    """`CHECK (service_date <= business_date)` — KELAJAK kuniga hisob yo'q (D-06).

    `business_date` `created_at` dan hosila, ya'ni u HAR DOIM «bugun».
    Shart `service_date` ni o'tmish va bugun bilan cheklaydi: kelajakka
    yozilgan hisob qarz hisobotida BUGUNDAN ko'rinardi va sotuvchi hali
    bo'lmagan kun uchun qarzdor bo'lib qolardi.
    """
    checks = _defs(sync_app_conn, "daily_charges", "c")

    matching = [
        definition
        for definition in checks.values()
        if "service_date <= business_date" in _canonical(definition)
    ]
    assert matching, (
        "`daily_charges` da `CHECK (service_date <= business_date)` YO'Q. "
        f"Mavjud `CHECK` lar: {sorted(checks)}."
    )


def test_payments_has_no_charge_id_column(
    sync_app_conn: Connection[TupleRow], migrated: None
) -> None:
    """`payments` ustunlari to'plami KUTILGANIGA TENG — `charge_id` YO'Q (C-4/D-24).

    =========================================================================
    TO'LOV `charge_id` GA BOG'LANMAYDI VA SABAB MEXANIK, DIDGA OID EMAS:
    kassir kun davomida yig'adi, hisob esa ERTASI KUNI 04:10 da tug'iladi
    (C-3) — ya'ni to'lov paytida `charge_id` MAVJUD EMAS. Ustiga bitta
    to'lov bir necha kunlik qarzni yopishi mumkin (§9.6), ya'ni bog'lanish
    1:1 EMAS.

    Kun kesimi HOSILA qoida bilan olinadi
    (`FIFO_OLDEST_SERVICE_DATE_FIRST`) va HECH QAYERDA saqlanmaydi:
    `payment_allocations` jadvali ham, `allocated_*` ustuni ham yo'q
    (D-07, BILL-03).

    ⛔ SOLISHTIRUV TO'PLAM TENGLIGI BILAN — sabab `PAYMENT_COLUMNS`
       docstringida.
    =========================================================================
    """
    columns = frozenset(_columns(sync_app_conn, "payments"))

    assert columns == PAYMENT_COLUMNS, (
        "`payments` ustunlari to'plami kutilganidan farq qiladi.\n"
        f"  ORTIQCHA: {sorted(columns - PAYMENT_COLUMNS)}\n"
        f"  YETISHMAYDI: {sorted(PAYMENT_COLUMNS - columns)}\n"
        "Har ikkala yo'nalish ham ONGLI qaror talab qiladi: `charge_id` "
        "yoki `allocated_*` shaklidagi har qanday ustun C-4/D-24 ni "
        "bekor qiladi."
    )


def test_quote_pairing_check_exists(sync_app_conn: Connection[TupleRow], migrated: None) -> None:
    """`(amount_soum = quote_soum) = (override_reason IS NULL)` (D-19/CASH-02).

    =========================================================================
    BU KONSTRAYT D-19 NI ILOVA QATLAMIDAN SXEMAGA KO'CHIRADI.

    «422 `reason_required`» tekshiruvi FAQAT HTTP yo'lini qo'riqlaydi; xom
    SQL (migratsiya, import skripti, `psql`) uni BUTUNLAY chetlab
    o'tardi. `quote_soum` server bergan summani QATORDA saqlaydi,
    `CHECK` esa har qanday chetlanishdan sabab-kod TALAB QILADI.

    ⚠ IKKI TOMONLAMA TENGLIK MAJBURIY: SABABSIZ o'zgartirish ham,
      O'ZGARISHSIZ sabab ham ifodalab bo'lmaydi. Implikatsiya shakli
      (`amount_soum <> quote_soum OR override_reason IS NULL`) ikkinchi
      nosozlikni OCHIQ qoldirardi va hisobotda «sababi bor, lekin
      o'zgarish yo'q» qatorlari paydo bo'lardi.
    =========================================================================
    """
    checks = _defs(sync_app_conn, "payments", "c")

    matching = [
        definition for definition in checks.values() if "quote_soum" in _canonical(definition)
    ]
    paired = [
        definition
        for definition in matching
        if "(amount_soum = quote_soum) = (override_reason IS NULL)" in _canonical(definition)
    ]
    assert paired, (
        "`payments` da `quote_soum` juftlangan `CHECK` i YO'Q. `quote_soum` "
        f"uchraydigan `CHECK` lar: {[_canonical(d) for d in matching]}. "
        "Bu holatda summani sabab-kodsiz o'zgartirish yo'li XOM SQL uchun "
        "ochiq qoladi (D-19)."
    )


def test_reversal_pairing_checks_are_two_sided(
    sync_app_conn: Connection[TupleRow], migrated: None
) -> None:
    """Ikkala storno `CHECK` i ham `=` (tenglik), `OR` (implikatsiya) EMAS (D-23).

    =========================================================================
    ⚠ FARQ SHAKLDA VA U O'LCHANADI, chunki `payments` da UCHINCHI, ATAYIN
      IMPLIKATSIYA shaklidagi `CHECK` ham bor
      (`kind <> 'reversal' OR override_reason IS NULL`).

    Ya'ni «`payments` da tenglik shaklidagi `CHECK` bor» degan da'vo
    yetarli EMAS: ikki juftlangan konstrayt NOM bo'yicha olinadi va har
    biri ALOHIDA tekshiriladi. Implikatsiyaga aylantirilgan juftlik
    «storno, lekin nimani bekor qilgani noma'lum» yoki «sababsiz storno»
    qatorini bemalol o'tkazardi — ikkalasi ham nizoda dalilni yarim
    qoldirardi (D-02).
    =========================================================================
    """
    checks = _defs(sync_app_conn, "payments", "c")

    for name, expected in (
        (
            "ck_payments_reversal_is_paired",
            "(kind = 'reversal') = (reverses_payment_id IS NOT NULL)",
        ),
        (
            "ck_payments_reversal_reason_is_paired",
            "(kind = 'reversal') = (reversal_reason IS NOT NULL)",
        ),
    ):
        assert name in checks, f"`payments` da `{name}` YO'Q. Mavjudlari: {sorted(checks)}"
        definition = _canonical(checks[name])
        assert expected in definition, (
            f"`{name}` kutilgan shaklda emas: {definition!r} — kutilgani `{expected}`."
        )
        assert " OR " not in definition, (
            f"`{name}` IMPLIKATSIYA shakliga o'tgan: {definition!r}. Ikki "
            "tomonlama tenglik ikkala nosozlikni ham yopadi, `OR` esa "
            "faqat bittasini."
        )


def test_anomaly_kind_and_evidence_are_paired(
    sync_app_conn: Connection[TupleRow], migrated: None
) -> None:
    """Anomaliya `kind` i va DALILI juft (C-12, D-29).

    =========================================================================
    IKKI JUFTLANGAN `CHECK` VA HAR BIRI BOSHQA NOSOZLIKNI YOPADI:

      (kind = 'no_coverage_stall') = (occupancy_event_id IS NULL)
        * `unassigned_occupied`, lekin hodisa YO'Q -> «band, lekin
          to'lovsiz» da'vosi RASM-DALILSIZ qolardi va u aynan
          mahsulotning yagona qiymati (`PROJECT.md` Core Value);
        * `no_coverage_stall`, lekin hodisa BOR -> «ko'ra olmadik» degan
          da'vo ko'rilgan kadr bilan kelardi, ya'ni u YOLG'ON bo'lardi.

      (occupancy_event_id IS NULL) = (snapshot_id IS NULL)
        hodisasiz kadr «qaysi zona?» ni javobsiz qoldirardi, kadrsiz
        hodisa esa nazoratchiga KO'RSATADIGAN rasm bermasdi.
    =========================================================================
    """
    checks = _defs(sync_app_conn, "billing_anomalies", "c")
    canonical = {name: _canonical(definition) for name, definition in checks.items()}

    for expected in (
        "(kind = 'no_coverage_stall') = (occupancy_event_id IS NULL)",
        "(occupancy_event_id IS NULL) = (snapshot_id IS NULL)",
    ):
        assert any(expected in definition for definition in canonical.values()), (
            f"`billing_anomalies` da `{expected}` shaklidagi `CHECK` YO'Q. Mavjudlari: {canonical}."
        )


def test_one_open_shift_per_cashier_is_structural(
    sync_app_conn: Connection[TupleRow], migrated: None
) -> None:
    """Bir kassirda bir OCHIQ smena — QISMAN UNIQUE indeks bilan (D-27).

    =========================================================================
    POYGA DB'GA TOPSHIRILGAN, ILOVA MANTIG'IGA EMAS.

    Ikki oynadan bir vaqtda ochilgan smena — POYGA holati va «avval
    tekshir, keyin yoz» ikkalasiga ham bo'sh holatni ko'rsatardi.
    O'shanda kassir to'lovlarni ikki smenaga bo'lib yozardi va variance
    HAR IKKALASIDA ham kichik ko'rinardi — ya'ni nomuvofiqlik ikkiga
    bo'linib YO'QOLARDI (CASH-04 ning yagona signali).

    ⚠ UCH DETAL VA HAR BIRI ALOHIDA BUZILISHI MUMKIN: indeks UNIQUE mi,
      ustunlari `(market_id, cashier_id)` mi va predikati `status =
      'open'` mi. Predikatsiz (to'liq) UNIQUE bo'lsa kassir umuman
      IKKINCHI smena ocha olmasdi — ya'ni ertangi kun IMKONSIZ bo'lardi.
    =========================================================================
    """
    row = sync_app_conn.execute(INDEX_DEF, (SHIFT_OPEN_INDEX,)).fetchone()
    assert row is not None, (
        f"`{SHIFT_OPEN_INDEX}` indeksi bazada YO'Q — ikkinchi ochiq smenani "
        "faqat ilova mantig'i to'xtatardi va u poygada ishlamasdi (D-27)."
    )
    definition = _canonical(str(row[0]))

    assert "CREATE UNIQUE INDEX" in definition, (
        f"indeks UNIQUE emas: {definition!r} — u ikkinchi ochiq smenani umuman bloklamaydi."
    )
    assert "(market_id, cashier_id)" in definition, (
        f"indeks ustunlari kutilganidek emas: {definition!r}"
    )
    assert "WHERE (status = 'open')" in definition, (
        f"indeks predikati kutilganidek emas: {definition!r} — predikatsiz "
        "UNIQUE kassirning IKKINCHI (ertangi) smenasini ham bloklardi."
    )


def test_every_check_is_derived_from_enum(
    sync_app_conn: Connection[TupleRow], migrated: None
) -> None:
    """Har `CHECK` ning qiymatlar to'plami ENUM a'zolariga TENG (D-31/D-32).

    =========================================================================
    ⛔ «HAR A'ZO `CHECK` DA UCHRAYDI» DEGAN DA'VO YETARLI EMAS — TENGLIK
       TALAB QILINADI, VA U IKKI YO'NALISHNI HAM QULFLAYDI:

      * `CHECK` da enumda BO'LMAGAN qiymat bo'lsa (masalan `'other'`)
        -> darvoza QIZARADI. `AdjustmentReason` da `other` ning YO'QLIGI
        ro'yxatning butun qiymati (D-19: tuzatishni ATAYIN qimmat
        qilish) va uni SQL tomondan jimgina qaytarish mumkin bo'lardi;
      * enumda bor qiymat `CHECK` da bo'lmasa -> darvoza QIZARADI:
        backend uni qabul qilardi-yu, DB rad etardi va nosozlik faqat
        kassir tugmani bosganda ko'rinardi.

    ⛔ KUTILMA QO'LDA YOZILMAYDI — `ENUM_BACKED_COLUMNS` uni ENUMDAN
       ITERATSIYA bilan quradi (o'sha konstantaning docstringi).

    =========================================================================
    ⚠⚠ BU TEST NIMANI O'LCHAY OLMAYDI — O'LCHANGAN CHEGARA (06-05 / S-C).

    «Enumga a'zo qo'shilib MIGRATSIYA YOZILMASA bu test qizaradi» degan
    da'vo SINALDI va u YOLG'ON chiqdi: `ReversalReason` ga vaqtincha
    beshinchi a'zo qo'shildi, sabotaj konteynerga YETIB BORDI (import
    `/app/packages/...` dan, enum 5 a'zo bilan o'qildi) va test BARIBIR
    YASHIL qoldi.

    SABAB MEXANIK VA U ASLIDA YAXSHI XABAR: `0020_billing_domain.py`
    `REVERSAL_REASON_CHECK` ni `sbozor_core.models.billing` DAN import
    qiladi, u esa f-string bilan ENUMDAN quriladi. Ya'ni yangi bazaga
    `alembic upgrade head` yugurganda `CHECK` ham BESH qiymat bilan
    tug'iladi — ikkala tomon ham AYNI manbadan keladi va «migratsiyasiz
    a'zo» holati YANGI bazada IFODALAB BO'LMAYDI.

    DA'VO SUSAYMADI, U IKKIGA BO'LINDI:
      * bu test — MAVJUD (allaqachon migratsiya qilingan) bazaning
        enumdan ajralishini ushlaydi: qo'lda `ALTER TABLE`, konstraytni
        qayta ta'riflagan keyingi migratsiya, restore qilingan eski
        sxema. Testni prod nusxasiga qaratganda u AYNAN shuni o'lchaydi;
      * `test_no_migration_hard_codes_a_value_list()` — IKKINCHI NUSXA
        umuman TUG'ILMASLIGINI qo'riqlaydi. Aynan o'sha nusxa bo'lmagani
        uchun yuqoridagi sabotaj lands qilmadi, ya'ni ikkinchi test
        birinchisining SHARTI hisoblanadi.
    =========================================================================
    """
    for table, column, expected_values in ENUM_BACKED_COLUMNS:
        checks = _defs(sync_app_conn, table, "c")
        matching = [
            _canonical(definition)
            for name, definition in checks.items()
            if name == f"ck_{table}_{_check_suffix(column)}"
        ]
        assert matching, (
            f"`{table}.{column}` uchun enumdan hosila `CHECK` topilmadi. "
            f"Mavjud `CHECK` lar: {sorted(checks)}. Usiz ustun ixtiyoriy "
            "matn qabul qilardi va enum shunchaki TAVSIYA bo'lib qolardi."
        )
        found = set(re.findall(r"'([^']*)'", matching[0]))

        assert found == set(expected_values), (
            f"`{table}.{column}` `CHECK` i enumdan AJRALIB KETGAN.\n"
            f"  `CHECK` da bor, enumda YO'Q: {sorted(found - set(expected_values))}\n"
            f"  enumda bor, `CHECK` da YO'Q: {sorted(set(expected_values) - found)}\n"
            f"  `CHECK`: {matching[0]!r}\n"
            "Enumga a'zo qo'shilganda migratsiya ham yozilishi SHART "
            "(D-32) — aks holda backend qabul qiladi, DB rad etadi."
        )


def test_no_migration_hard_codes_a_value_list(migrated: None) -> None:
    """Billing migratsiyalarida QO'LDA yozilgan qiymat RO'YXATI yo'q (D-32).

    =========================================================================
    ⛔ BU TEST YUQORIDAGISINING SHARTI, TAKRORI EMAS — VA U 06-05 NING S-C
       SABOTAJIDAN TUG'ILDI.

    Yuqoridagi test «enum <-> DB» tengligini o'lchaydi, lekin YANGI bazada
    ikkala tomon ham BITTA manbadan (`models/billing.py` ning enumdan
    hosila f-stringlari) keladi — ya'ni u yerda ajralish IFODALAB
    BO'LMAYDI. Aynan shu sababdan «enumga a'zo qo'shildi, migratsiya
    yozilmadi» sabotaji yashil qoldi.

    Ajralish YAGONA yo'l bilan tug'iladi: kimdir migratsiyaga qiymat
    ro'yxatini QO'LDA yozadi (`IN ('open', 'closed')` yoki
    `ANY (ARRAY['cash', 'terminal'])`). O'sha kundan boshlab enum va DDL
    IKKI NUSXA bo'ladi va ular jimgina ajralib ketadi — hech qanday test
    buni sezmasdi, chunki har ikkalasi ham «to'g'ri» ko'rinardi.

    Shuning uchun bu yerda IKKINCHI NUSXANING TUG'ILISHI bloklanadi.

    ⚠ `server_default=sa.text("'open'")` TAQIQLANMAYDI va bu ONGLI
      chegara: u BITTA qiymat, RO'YXAT emas — enumning a'zolik to'plamini
      takrorlamaydi, ya'ni «yangi a'zo qo'shildi» holatida jimgina
      eskirmaydi. `0020` da ayni ikkita shunday qiymat bor
      (`cashier_shifts.status` va `payments.kind`) va ular bu darvozaning
      yuzasidan ATAYIN tashqarida.

    ⚠ NAQSHNING O'ZI POZITIV VA NEGATIV NAZORAT BILAN SINALADI (06-04 da
      o'rnatilgan qoida): naqsh hech nimani topmaydigan holatda «topilmadi»
      degan javob BO'SH ROST bo'lardi va darvoza abadiy yashil qolardi.
    =========================================================================
    """
    # NAZORAT (naqshning O'ZI ishlaydimi) — pozitiv va negativ.
    assert _VALUE_LIST_PATTERN.search("status IN ('open', 'closed')") is not None, (
        "naqsh QO'LDA yozilgan `IN (...)` ro'yxatini TOPMADI — quyidagi "
        "da'vo bo'sh rost bo'lib qolardi"
    )
    assert _VALUE_LIST_PATTERN.search("ANY (ARRAY['cash', 'terminal'])") is not None, (
        "naqsh `ANY (ARRAY[...])` shaklini TOPMADI — `pg_get_constraintdef` "
        "aynan shu shaklda chiqaradi va migratsiyaga ko'chirilgan nusxa ham "
        "shunday ko'rinardi"
    )
    assert _VALUE_LIST_PATTERN.search("server_default=sa.text(\"'open'\")") is None, (
        "naqsh BITTA qiymatli `server_default` ni ham topyapti — u ONGLI "
        "ravishda yuzadan tashqarida (docstringdagi birinchi ⚠)"
    )

    offenders: dict[str, list[str]] = {}
    for path in _BILLING_MIGRATIONS:
        source = path.read_text(encoding="utf-8")
        hits = _VALUE_LIST_PATTERN.findall(source)
        if hits:
            offenders[path.name] = hits

    assert offenders == {}, (
        f"billing migratsiyasida QO'LDA yozilgan qiymat ro'yxati topildi: "
        f"{offenders}. Ro'yxat `sbozor_core.models.billing` dagi enumdan "
        "hosila `*_CHECK` konstantasidan IMPORT qilinishi shart — aks holda "
        "enum va DDL ikki nusxa bo'lib jimgina ajralib ketadi (D-32)."
    )


_VALUE_LIST_PATTERN = re.compile(r"IN \('|ANY \(ARRAY\[")
"""QO'LDA yozilgan qiymat RO'YXATINING ikki shakli.

Naqsh SHAKLGA yozilgan, NOMGA emas (06-04 ning `DERIVED_ORDER_PATTERN`
qarori): `reversal_reason IN (...)` ni nom bo'yicha qidirish ertaga
qo'shiladigan yangi ustunni qamramasdi.
"""

_BILLING_MIGRATIONS = tuple(
    (Path(__file__).resolve().parents[2] / "migrations" / "versions" / name)
    for name in (
        "0020_billing_domain.py",
        "0021_market_delete_billing.py",
        # ⚠ 06-07 QO'SHDI: `0022` `charge_adjustments` ga qisman UNIQUE
        #   indeks olib keladi va uning predikati `AdjustmentReason` DAN
        #   HOSILA. Ro'yxat NOMMA-NOM bo'lgani uchun yangi migratsiya
        #   avtomatik qamralmasdi — ya'ni 6-fazaning YANGI fayli
        #   darvozadan JIMGINA chetda qolardi va D-32 shu fayldan
        #   boshlab kuchsizlanardi.
        "0022_billing_late_review.py",
    )
)
"""6-fazaning uchta migratsiyasi — NOMMA-NOM.

⚠ `glob("*.py")` ATAYIN EMAS: quyi fazalarning migratsiyalarida qo'lda
yozilgan ro'yxatlar BO'LISHI mumkin (ular boshqa qaror sinfida) va
ularni bu darvoza ostiga tortish 6-fazaning testini o'zga fazaning
qarziga bog'lab qo'yardi.
"""


def _check_suffix(column: str) -> str:
    """Ustun nomidan `CHECK` konstraytining qo'shimchasini quradi.

    ⚠ NAQSH `models/billing.py` DAN O'QILMAYDI, u yerda konstrayt nomlari
      `CheckConstraint(..., name="...")` bilan e'lon qilingan va ularni
      import qilish testni MODELGA qaytarardi (fayl docstringidagi
      birinchi qoida). Bu yerda nom KONVENSIYADAN quriladi:
      `<ustun>_allowed`, `naming_convention["ck"]` esa unga
      `ck_<jadval>_` prefiksini qo'shadi.
    """
    return f"{column}_allowed"


def test_no_stored_balance_column_anywhere(
    sync_app_conn: Connection[TupleRow], migrated: None
) -> None:
    """Saqlangan QOLDIQ ustuni hech qaysi jadvalda yo'q (BILL-03, G-3 ning jufti).

    =========================================================================
    QARZ — HAR DOIM HISOBLANADIGAN KO'RINISH.

    Saqlangan ustun IKKINCHI HAQIQAT MANBAI bo'lardi va u birinchisidan
    JIMGINA ajralib ketardi: bitta yo'qolgan `UPDATE` (yoki storno
    qatorining hisobga olinmasligi) yetarli. O'shanda «qancha qarzdor?»
    savoli IKKI XIL javob berardi va nizoda IKKALASI ham dalil bo'la
    olmasdi — ya'ni mahsulotning yagona qiymati (rasm-dalil bilan
    isbotlangan raqam) yo'qolardi.

    ⛔ SANOQ TO'PLAM TENGLIGI BILAN: mos keladigan ustunlar to'plami
       BO'SH to'plamga teng bo'lishi shart. `assert not found` shakli ham
       bir xil natija berardi, lekin xato xabarida QAYSI ustun
       topilganini ko'rsatmasdi.
    =========================================================================
    """
    found: set[str] = set()
    for table in BALANCE_SCANNED_TABLES:
        for column in _columns(sync_app_conn, table):
            lowered = column.lower()
            if lowered.startswith("balance") or lowered.endswith("balance"):
                found.add(f"{table}.{column}")

    assert found == set(), (
        f"saqlangan qoldiq ustuni topildi: {sorted(found)}. Qarz "
        "`total_due_soum()` / `vendor_outstanding()` bilan HISOBLANADI "
        "(BILL-03); saqlangan ustun ikkinchi haqiqat manbai bo'ladi."
    )

    # NAZORAT: skanerlangan jadvallarda ustun UMUMAN bor. Usiz yuqoridagi
    # inkor da'vosi jadval nomi xato yozilganda ham JIMGINA rost bo'lardi
    # (`_columns()` bo'sh to'plamda yiqiladi, ya'ni nazorat AVTOMATIK).
    assert len(BALANCE_SCANNED_TABLES) == 5, "skanerlanadigan yuza qisqarib ketgan"


def test_billing_columns_use_only_allowed_types(
    sync_app_conn: Connection[TupleRow], migrated: None
) -> None:
    """Oltala jadval ustunlarining TIPLAR TO'PLAMI ruxsat etilganiga TENG (G-3/D-11).

    =========================================================================
    ⛔ PUL — `bigint` SO'M. KASRLI TIP HECH QAYERDA ISHLATILMAYDI.

    Yaxlitlanish drifti aynan mahsulot bartaraf etadigan nizoni
    tug'diradi: kunlik patta agregatida bir tiyin farq oyiga bir necha
    so'mga aylanadi va sotuvchi bilan bozor ma'muriyati ikki xil son
    ko'radi. `float` da bu farq HECH QANDAY xato bermaydi — u shunchaki
    yig'iladi.

    ⛔ SOLISHTIRUV TENGLIK BILAN, `not in` BILAN EMAS — sabab
       `ALLOWED_DATA_TYPES` docstringida.
    =========================================================================
    """
    found: dict[str, set[str]] = {}
    for table in BILLING_TABLES:
        for column, data_type in _columns(sync_app_conn, table).items():
            found.setdefault(data_type, set()).add(f"{table}.{column}")

    assert set(found) == ALLOWED_DATA_TYPES, (
        "billing jadvallarining tip to'plami kutilganidan farq qiladi.\n"
        f"  ORTIQCHA tiplar: "
        f"{ {t: sorted(found[t]) for t in sorted(set(found) - ALLOWED_DATA_TYPES)} }\n"
        f"  YO'QOLGAN tiplar: {sorted(ALLOWED_DATA_TYPES - set(found))}\n"
        "Har ikkala yo'nalish ham ONGLI qaror talab qiladi: yangi tip "
        "(`numeric`, `double precision`, `money`) D-11 ni bekor qiladi, "
        "yo'qolgan tip esa ustunning jimgina o'chirilganini bildiradi."
    )
