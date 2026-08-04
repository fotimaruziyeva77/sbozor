"""Snapshot domenining META-INVARIANTLARI — oltita, hammasi `pg_catalog` dan.

=============================================================================
NEGA BU FAYL MODELNI IMPORT QILMAYDI.

`sbozor_core.models.snapshot` — ISTALGAN holat. Bazadagi sxema esa HAQIQIY
holat. Ikkisi ajralib qolishi mumkin (migratsiya qo'llanmagan,
`op.create_index(...)` unutilgan, kimdir qo'lda `ALTER TABLE` qilgan) va
aynan o'sha holatda modeldan o'qiydigan test JIMGINA yashil qolardi — ya'ni
u eng kerakli paytda ishlamasdi. `tests/tenancy/test_market_domain_meta.py`
shu qoidani 2-fazada o'rnatgan, `test_nvr_domain_meta.py` uni 3-fazada davom
ettirgan, bu fayl esa 4-fazada.

OLTITA INVARIANT VA HAR BIRI QAYSI DA'VONI QULFLAYDI:

  1. `UNIQUE (id, is_billable)` — D-16 NING YAGONA ILGAGI. Yo'qolsa
     5-fazaning FK'si quriladigan joy qolmaydi.
  2. `is_billable` HAQIQATAN hosila ustun (`attgenerated = 's'`) — ya'ni
     ilova unga YOZA OLMAYDI.
  3. `capture_runs`/`snapshots`/`alert_events` da audit trigger YO'Q —
     hajm qarori (§S-1) haqiqatan bajarilgan.
  4. `capture_runs.business_date` `scheduled_at` ga tayanadi, `created_at`
     ga TAYANMAYDI — yarim tun oynasidagi bir kunlik siljish yo'q.
  5. `snapshot_schedules` da `EXCLUDE` konstrayti bor — «bir kunga bitta
     profil» (Alembic uni KO'RMAYDI, ya'ni bu YAGONA darvoza).
  6. `snapshots.business_date` ifodasi `capture_runs` niki bilan AYNAN bir
     xil — Pitfall 3 ning invarianti.

Ikkinchi va oltinchi banddan tashqari hammasi INKOR yoki MAVJUDLIK da'vosi
va ular avtomatik invariantlar (`test_meta.py` ning beshtasi) bilan
QOPLANMAYDI: o'sha yerdagi testlar `market_id` + RLS + policy + indeks
tartibini tekshiradi, bu yerdagilar esa domenning O'Z qarorlarini.
=============================================================================
"""

from __future__ import annotations

import pytest
from psycopg import Connection
from psycopg.rows import TupleRow

from migrations.helpers import audit_trigger_name

pytestmark = pytest.mark.tenancy

BILLABLE_ANCHOR = "uq_snapshots_billable_anchor"
"""D-16 ilgagining nomi — 5-faza uni AYNAN shu nom bilan izlaydi."""

UNAUDITED_EVENT_TABLES: tuple[str, ...] = ("capture_runs", "snapshots", "alert_events")
"""Audit triggeri ATAYIN ULANMAGAN hodisa jurnallari (§S-1)."""

UNIQUE_CONSTRAINT_COLUMNS = """
SELECT con.conname,
       array_agg(att.attname ORDER BY key.ord)
FROM pg_constraint con
JOIN pg_class c ON c.oid = con.conrelid
JOIN pg_namespace n ON n.oid = c.relnamespace
JOIN LATERAL unnest(con.conkey) WITH ORDINALITY AS key(attnum, ord) ON true
JOIN pg_attribute att ON att.attrelid = c.oid AND att.attnum = key.attnum
WHERE n.nspname = 'public'
  AND c.relname = %s
  AND con.contype = 'u'
GROUP BY con.conname
"""
"""Jadvalning UNIQUE konstraytlari — ustunlar E'LON TARTIBIDA.

Tartib saqlanadi (`WITH ORDINALITY`), chunki da'voning o'zi tartibga
bog'liq: kompozit FK nishoni ustunlarning AYNAN shu ketma-ketligini talab
qiladi. `(is_billable, id)` bir xil to'plam bo'lardi-yu, 5-fazaning
`FOREIGN KEY (snapshot_id, snapshot_is_billable)` i unga tusha olmasdi.
"""

GENERATED_COLUMN = """
SELECT a.attgenerated,
       pg_get_expr(d.adbin, d.adrelid)
FROM pg_attribute a
JOIN pg_class c ON c.oid = a.attrelid
JOIN pg_namespace n ON n.oid = c.relnamespace
LEFT JOIN pg_attrdef d ON d.adrelid = a.attrelid AND d.adnum = a.attnum
WHERE n.nspname = 'public'
  AND c.relname = %s
  AND a.attname = %s
  AND a.attnum > 0
  AND NOT a.attisdropped
"""
"""Ustunning HOSILA ekanligi va uning ifodasi.

`attgenerated` — `'s'` (STORED) yoki bo'sh satr (oddiy ustun). Ifoda
`pg_attrdef` da yashaydi: PostgreSQL generated ustunning ifodasini AYNAN
standart qiymat mexanizmida saqlaydi, ya'ni `pg_get_expr()` uni
NORMALLASHTIRILGAN shaklda qaytaradi (`((scheduled_at AT TIME ZONE
'Asia/Tashkent'::text))::date`). Shuning uchun pastdagi testlar matnni
model konstantasi bilan HARFMA-HARF solishtirmaydi — ular ustun NOMLARINI
va ikki jadval ifodasining TENGLIGINI tekshiradi.
"""

NON_INTERNAL_TRIGGERS = """
SELECT tg.tgname
FROM pg_trigger tg
JOIN pg_class c ON c.oid = tg.tgrelid
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public'
  AND c.relname = %s
  AND NOT tg.tgisinternal
ORDER BY tg.tgname
"""
"""Jadvalga ULANGAN triggerlar (FK uchun yaratilgan ichkilaridan tashqari).

`tgisinternal` filtri MAJBURIY: kompozit FK har bir jadvalga ichki trigger
qo'yadi va usiz «trigger yo'q» da'vosi HECH QACHON rost bo'lmasdi — test
doim qizil bo'lardi va sabab noto'g'ri joyda qidirilardi.
"""

EXCLUSION_CONSTRAINTS = """
SELECT con.conname, pg_get_constraintdef(con.oid)
FROM pg_constraint con
JOIN pg_class c ON c.oid = con.conrelid
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public'
  AND c.relname = %s
  AND con.contype = 'x'
"""


def _unique_constraints(conn: Connection[TupleRow], table: str) -> dict[str, list[str]]:
    return {
        str(row[0]): [str(col) for col in row[1]]
        for row in conn.execute(UNIQUE_CONSTRAINT_COLUMNS, (table,)).fetchall()
    }


def _generated(conn: Connection[TupleRow], table: str, column: str) -> tuple[str, str]:
    row = conn.execute(GENERATED_COLUMN, (table, column)).fetchone()
    assert row is not None, f"`{table}.{column}` ustuni `pg_attribute` da topilmadi"
    return str(row[0] or ""), str(row[1] or "")


def _triggers(conn: Connection[TupleRow], table: str) -> list[str]:
    return [str(row[0]) for row in conn.execute(NON_INTERNAL_TRIGGERS, (table,)).fetchall()]


def test_snapshots_have_the_billable_anchor(
    sync_app_conn: Connection[TupleRow], migrated: None
) -> None:
    """`UNIQUE (id, is_billable)` MAVJUD va ustunlar TARTIBI aynan shunday (D-16).

    =========================================================================
    BU KONSTRAYT BOSHQA FAZA UCHUN BOR VA AYNAN SHUNING UCHUN U OSON
    YO'QOTILADI: bugungi kodda uni ishlatadigan birorta so'rov YO'Q.

    5-fazada `occupancy_events` shunday quriladi:

        snapshot_is_billable boolean NOT NULL DEFAULT true
        CHECK  (snapshot_is_billable)
        FOREIGN KEY (snapshot_id, snapshot_is_billable)
            REFERENCES snapshots (id, is_billable)

    Ya'ni `quality_verdict <> 'ok'` bo'lgan kadrga bandlik dalilini bog'lash
    uchun kerak bo'lgan `(id, true)` juftligi JADVALDA UMUMAN MAVJUD
    BO'LMAYDI va FK rad etadi. «Yaroqsiz kadr billing'ga ta'sir qilmaydi»
    da'vosi shu bilan KELISHUV emas, DB XATOSI bo'ladi (T-04-17).

    Konstrayt olib tashlansa yoki `market_id` qo'shilsa 5-fazaning FK'si
    qurilmasdi va yagona «tuzatish» yo'li kafolatni ilova qatlamiga
    ko'chirish — ya'ni uni BUTUNLAY yo'qotish — bo'lardi.

    TARTIB TEKSHIRILADI, faqat to'plam emas: FK nishoni ustunlarning aynan
    shu ketma-ketligini talab qiladi.
    =========================================================================
    """
    constraints = _unique_constraints(sync_app_conn, "snapshots")

    assert BILLABLE_ANCHOR in constraints, (
        f"`snapshots` da `{BILLABLE_ANCHOR}` konstrayti YO'Q. Mavjudlari: "
        f"{constraints}. Busiz 5-fazadagi `occupancy_events` yaroqsiz kadrga "
        "bandlik dalilini bog'lay OLADI va D-16 ning billing kafolati "
        "kelishuvga aylanadi."
    )
    assert constraints[BILLABLE_ANCHOR] == ["id", "is_billable"], (
        f"`{BILLABLE_ANCHOR}` ustunlari {constraints[BILLABLE_ANCHOR]} — kutilgani "
        "AYNAN `['id', 'is_billable']`. Kompozit FK nishoni ustunlarning shu "
        "ketma-ketligini talab qiladi; boshqa tartib yoki qo'shimcha ustun "
        "5-fazaning FK'sini qura olmaydigan qiladi."
    )


def test_is_billable_is_a_stored_generated_column(
    sync_app_conn: Connection[TupleRow], migrated: None
) -> None:
    """`is_billable` HOSILA ustun (`attgenerated = 's'`) — ilova unga YOZA OLMAYDI.

    =========================================================================
    ⚠ IKKI SHAKLDAN AYNAN BITTASI BO'LISHI SHART, IKKALASI EMAS.

    `04-01` ning W0-1 zondi HAQIQIY `postgres:18.4` da o'lchadi:
    `BILLABLE_ANCHOR_SUPPORTED = true`, ya'ni `GENERATED ... STORED` ustun
    ustidagi `UNIQUE` kompozit FK NISHONI bo'la OLADI. Shuning uchun `0014`
    TUZILMAVIY shaklni tanladi va `BEFORE INSERT/UPDATE` trigger varianti
    yozilmadi.

    Bu test tanlangan shaklga MOSLASHMAYDI — u aynan o'lchov natijasini
    talab qiladi. Trigger variantiga «jimgina qaytish» (ustunni oddiy
    `boolean` qilib, qiymatni ilovada qo'yish) IKKI teshik ochardi:

      * ilova `is_billable = true` ni `quality_verdict = 'dark'` bilan birga
        yoza olardi — ya'ni yaroqsiz kadr billing uchun YAROQLI bo'lib
        qolardi;
      * hukm o'zgarganda (`UPDATE ... SET quality_verdict = 'dark'`) ustun
        eski qiymatida qolardi va 5-fazadagi FK buni SEZMASDI.

    Hosila ustunda ikkala yo'l ham YO'Q: qiymat `quality_verdict` dan
    hisoblanadi va `UPDATE` da avtomatik qayta hisoblanadi. Zond aynan shu
    ikkinchi yo'nalishni ham o'lchagan.
    =========================================================================
    """
    generated, expression = _generated(sync_app_conn, "snapshots", "is_billable")

    assert generated == "s", (
        f"`snapshots.is_billable` ning `attgenerated` qiymati {generated!r} — "
        "kutilgani `'s'` (STORED). Oddiy ustunga aylantirilgan bo'lsa ilova "
        "unga ISTALGAN qiymatni yoza oladi va D-16 ning kafolati sxemadan "
        "ilova qatlamiga ko'chib ketadi (`04-01` W0-1 o'lchovi: "
        "`BILLABLE_ANCHOR_SUPPORTED = true`, ya'ni bu shakl QO'LLAB-QUVVATLANADI)."
    )
    assert "quality_verdict" in expression, (
        f"`is_billable` ifodasi `quality_verdict` ga tayanmayapti: {expression!r}. "
        "Boshqa manbadan hisoblangan qiymat sifat verdikti bilan ajralib "
        "ketardi va yaroqsiz kadr billing'ga o'tib ketardi."
    )


def test_event_log_tables_have_no_audit_trigger(
    sync_app_conn: Connection[TupleRow], migrated: None
) -> None:
    """`capture_runs`/`snapshots`/`alert_events` da audit trigger YO'Q (§S-1).

    =========================================================================
    IKKI MUSTAQIL SABAB, BIR XIL QAROR:

      (a) uchalasi ham HODISA JURNALI va faqat qo'shiladi — audit ularning
          ustiga o'sha ma'lumotning IKKINCHI NUSXASINI yozardi;
      (b) HAJM: 175 qator/kun/bozor x har holat o'tishi ~ kuniga 525 audit
          qatori BITTA bozordan; o'nta bozorda yiliga ~1.9 mln qator.
          `audit_log` append-only, ya'ni u hech qachon kichraymaydi.

    IZ YO'QOLMAYDI va bu shu qarorning SHARTI: jadval o'zgarishi (kim
    slotni o'chirdi) `snapshot_schedules`/`snapshot_schedule_slots` orqali
    auditda, kunlik yugurishlar esa `capture_runs` ning O'ZIDA tarixga ega.

    NAZORAT BANDI: `snapshot_schedules` da trigger BO'LISHI tekshiriladi.
    Usiz so'rov noto'g'ri yozilganda (sxema nomi xato, `tgisinternal`
    filtri teskari) u HAR BIR jadval uchun bo'sh qaytarardi va yuqoridagi
    inkor da'vosi JIMGINA rost bo'lib qolardi — `test_nvr_domain_meta.py::
    test_nvr_credentials_has_no_audit_trigger` da o'rnatilgan qoida.
    =========================================================================
    """
    for table in UNAUDITED_EVENT_TABLES:
        triggers = _triggers(sync_app_conn, table)
        assert audit_trigger_name(table) not in triggers, (
            f"`{table}` ga audit triggeri ulangan ({triggers}). Bu jadval HODISA "
            "JURNALI: audit unga o'sha ma'lumotning ikkinchi nusxasini yozadi va "
            "`audit_log` ni yiliga ~1.9 mln qatorga o'stiradi (§S-1). Iz "
            "yo'qolmaydi — jadval o'zgarishi `snapshot_schedules` orqali auditda."
        )

    # NAZORAT: so'rov haqiqatan trigger topa oladimi?
    audited = _triggers(sync_app_conn, "snapshot_schedules")
    assert audit_trigger_name("snapshot_schedules") in audited, (
        f"`snapshot_schedules` da audit triggeri topilmadi ({audited}) — so'rov "
        "buzilgan bo'lishi mumkin, bunday holatda yuqoridagi inkor da'vosi hech "
        "nimani o'lchamasdi"
    )


def test_capture_business_date_derives_from_scheduled_at(
    sync_app_conn: Connection[TupleRow], migrated: None
) -> None:
    """`capture_runs.business_date` `scheduled_at` dan, `created_at` dan EMAS.

    =========================================================================
    BU 1-FAZADAGI MOLIYAVIY SHAKLDAN ATAYIN FARQ QILADI va farq bir kunlik
    siljishning oldini oladi.

    `migrations/helpers.py::BUSINESS_DATE_EXPR` `created_at` ga tayanadi va
    u yerda TO'G'RI: moliyaviy qator hodisa SODIR BO'LGANDA yoziladi.

    Reja qatori esa TESKARI — u o'zi tegishli bo'lgan kundan OLDIN
    yaratiladi (kunning birinchi tikida, 00:00-00:05 oynasida). Aynan o'sha
    oynada `created_at` ga tayanish qatorni OLDINGI kunga tushirardi va
    06:00 sloti KECHAGI hisobotga tushib qolardi — 6-fazada esa bu pul
    chegarasining bir kunga surilishi degani.

    Ifoda `pg_attrdef` dan o'qiladi, model konstantasidan EMAS: model —
    istalgan holat, baza esa haqiqiy holat.
    =========================================================================
    """
    generated, expression = _generated(sync_app_conn, "capture_runs", "business_date")

    assert generated == "s", (
        f"`capture_runs.business_date` hosila ustun EMAS ({generated!r}) — "
        "ilova biznes-kunni o'zi hisoblab yozadigan bo'lib qoladi va ikkinchi "
        "haqiqat manbai paydo bo'ladi"
    )
    assert "scheduled_at" in expression, (
        f"`business_date` ifodasi `scheduled_at` ga tayanmayapti: {expression!r}"
    )
    assert "created_at" not in expression, (
        f"`business_date` ifodasi `created_at` ga tayanyapti: {expression!r}. "
        "Reja qatori tegishli kunidan OLDIN yaratiladi, ya'ni 00:00-00:05 "
        "oynasida yozilgan qator OLDINGI kunga tushardi."
    )
    assert "Asia/Tashkent" in expression, (
        f"`business_date` ifodasida mintaqa literali yo'q: {expression!r}. "
        "Mintaqasiz `::date` konteynerning UTC soatiga tayanadi va mahalliy "
        "00:00-04:59 oralig'idagi har bir qator oldingi kunga tushadi."
    )


def test_snapshot_schedules_have_an_exclusion_constraint(
    sync_app_conn: Connection[TupleRow], migrated: None
) -> None:
    """`snapshot_schedules` da `EXCLUDE` bor — «bir kunga AYNAN bitta profil».

    =========================================================================
    BU TEST — KAFOLATNING YAGONA DARVOZASI, va sabab Alembic'da:

    `ExcludeConstraint` ni Alembic KO'RMAYDI — IKKI TOMONLAMA (empirik,
    `0009_vendors.py:29-40`): model va DB bir xil bo'lganda diff bo'sh,
    LEKIN konstrayt modeldan OLIB TASHLANGANDA HAM diff bo'sh. Ya'ni
    `alembic check` uning yo'qolganini HECH QACHON aytmaydi va
    `test_autogenerate_is_empty` ham jim qoladi.

    Ikki kesishuvchi profil bir kunga IKKI XIL slot to'plamini berardi va
    materializatsiya qaysi biriga tayanishni tasodifga qoldirardi — «ertasi
    kuni AYNAN o'sha slotlarda» (SC#1) da'vosi tekshirib bo'lmaydigan holga
    kelardi (T-04-19). Ilova qatlamidagi tekshiruv ikki parallel so'rovda
    ikkalasini ham o'tkazib yuborardi; `EXCLUDE` esa atomik va xom SQL
    yo'lini ham qamraydi.

    Ta'rifning O'ZI tekshiriladi, faqat mavjudligi emas: `(market_id, ...)`
    siz konstrayt BARCHA bozorlarni bir-biriga to'qnashtirardi, `period`
    siz esa u umuman davr kesishuvini o'lchamasdi.
    =========================================================================
    """
    rows = sync_app_conn.execute(EXCLUSION_CONSTRAINTS, ("snapshot_schedules",)).fetchall()

    assert len(rows) == 1, (
        f"`snapshot_schedules` da {len(rows)} ta EXCLUDE konstrayti topildi "
        f"({rows}), kutilgani AYNAN bitta. Yo'q bo'lsa bir kunga ikkita profil "
        "yozilishi mumkin va kunlik reja tasodifiy bo'lib qoladi (T-04-19)."
    )

    name, definition = str(rows[0][0]), str(rows[0][1])
    assert "gist" in definition.lower(), (
        f"`{name}` GiST bilan qurilmagan: {definition!r} — `daterange` ning `&&` "
        "operatori faqat GiST da indekslanadi"
    )
    for expected in ("market_id", "period", "&&"):
        assert expected in definition, (
            f"`{name}` ta'rifida `{expected}` yo'q: {definition!r}. `market_id` siz "
            "konstrayt bozorlarni bir-biriga to'qnashtiradi, `period &&` siz esa "
            "u davr kesishuvini umuman o'lchamaydi."
        )


def test_both_business_date_expressions_are_identical(
    sync_app_conn: Connection[TupleRow], migrated: None
) -> None:
    """`snapshots` va `capture_runs` ning `business_date` ifodalari AYNAN BIR XIL.

    =========================================================================
    PITFALL 3 NING INVARIANTI.

    Ikki jadval bir xil savolga («bu kadr qaysi biznes-kunga tegishli?»)
    javob beradi. Ifodalar MUSTAQIL yozilsa ular ajralib ketishi mumkin va
    nosozlik shakli o'ta yomon bo'lardi:

        yarim tunga yaqin olingan kadr
          -> `capture_runs` da 09-01
          -> `snapshots`    da 09-02

    6-faza dalilni `business_date` bo'yicha izlaydi, ya'ni o'sha kadr
    hisobda «yo'q» bo'lib qolardi va hech kim buni sezmasdi: ikkala qator
    ham mavjud, ikkalasi ham to'g'ri ko'rinadi.

    Kafolat UCH QATLAMLI va bu test uchinchisi:
      1. `SNAPSHOT_BUSINESS_DATE_EXPR` — `CAPTURE_BUSINESS_DATE_EXPR` ning
         ALIASI (nusxa emas), ya'ni kodda bitta literal;
      2. `snapshots.scheduled_at` `capture_runs` dan NUSXALANADI, mustaqil
         hisoblanmaydi;
      3. bu yerda — BAZADAGI ikki ifoda tenglikka solishtiriladi.

    Uchinchisi zarur, chunki birinchi ikkitasi KODDAGI da'vo, bu esa
    bazadagi HAQIQAT: migratsiya qo'lda tahrirlansa faqat shu darvoza
    sezadi.
    =========================================================================
    """
    _, capture_expr = _generated(sync_app_conn, "capture_runs", "business_date")
    snapshot_generated, snapshot_expr = _generated(sync_app_conn, "snapshots", "business_date")

    assert snapshot_generated == "s", (
        f"`snapshots.business_date` hosila ustun EMAS ({snapshot_generated!r})"
    )
    assert snapshot_expr == capture_expr, (
        "`business_date` ifodalari AJRALIB KETGAN:\n"
        f"  capture_runs: {capture_expr!r}\n"
        f"  snapshots:    {snapshot_expr!r}\n"
        "Yarim tunga yaqin olingan kadr ikki jadvalda ikki xil biznes-kunga "
        "tushadi va 6-fazada dalil hisobda 'yo'q' bo'lib qoladi (Pitfall 3)."
    )
