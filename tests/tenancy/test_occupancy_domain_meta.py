"""Bandlik domenining META-INVARIANTLARI — hammasi `pg_catalog` dan.

=============================================================================
NEGA BU FAYL MODELNI IMPORT QILMAYDI.

`sbozor_core.models.occupancy` — ISTALGAN holat. Bazadagi sxema esa HAQIQIY
holat. Ikkisi ajralib qolishi mumkin (migratsiya qo'llanmagan, konstrayt
migratsiyada unutilgan, kimdir qo'lda `ALTER TABLE` qilgan) va aynan o'sha
holatda modeldan o'qiydigan test JIMGINA yashil qolardi — ya'ni u eng
kerakli paytda ishlamasdi. `test_market_domain_meta.py` bu qoidani 2-fazada
o'rnatgan, `test_nvr_domain_meta.py` uni 3-fazada, `test_snapshot_domain_
meta.py` 4-fazada davom ettirgan; bu fayl esa 5-fazada.

⚠ ISTISNO — REYESTR TESTI. `test_occupancy_registries_match_the_database()`
`migrations.entities` ni ATAYIN import qiladi: uning butun savoli aynan
«reyestr bazaga mos keladimi?» va u ikkala tomonni ko'rmasdan javob bera
olmaydi. Import test funksiyasining ICHIDA (`test_meta.py` dagi jufti bilan
bir xil sabab: modul darajasidagi import butun faylning yig'ilishini
yiqitishi mumkin).
=============================================================================

TO'QQIZTA INVARIANT VA HAR BIRI QAYSI DA'VONI QULFLAYDI:

  1. `occupancy_events` `snapshots (id, is_billable)` LANGARIGA osilgan —
     D-21 ning FK yarmi. Yo'qolsa yaroqsiz kadr bandlik dalilini bemalol
     ko'tarardi.
  2. `CHECK (snapshot_is_billable)` — langarning IKKINCHI yarmi. Usiz FK
     `(id, false)` juftligiga havolani ham QABUL QILARDI.
  3. `CHECK (queue_kind <> 'blind_audit' OR shown_ai_verdict = false)` —
     D-17.3. «Ko'r, lekin ko'rsatilgan» IFODALAB BO'LMAYDI.
  4. `zone_reviews.queue_kind` MANBASIGA QADALGAN (kompozit FK) — usiz
     3-band o'z nusxasiga ishonardi.
  5. `UNIQUE (occupancy_event_id)` — bir hodisa ikki navbatda bo'la olmaydi.
  6. `occupancy_events` da audit trigger YO'Q; `camera_zones`/`zone_reviews`
     da BOR — hajm/o'zgarmaslik qarori HAQIQATAN bajarilgan.
  7. `occupancy_events.business_date` HOSILA USTUN EMAS — u `snapshots` dan
     NUSXALANADI va ikki mustaqil hisoblash manbai yo'q (Pitfall 3).
  8. Uchala reyestr (`OCCUPANCY_TENANT_TABLES` / `_AUDITED_` / `_DELETE_ORDER`)
     bazadagi haqiqiy jadvallarga mos.
  9. Ikkala yangi `SECURITY DEFINER` funksiya FAQAT identifikator va sanoq
     qaytaradi (T-05-19) va `search_path` ni pin qiladi.

Onunchisi — o'zgarmaslik triggerlarining SHAKLI (`BEFORE UPDATE OR DELETE`).
Uning XULQI `tests/integration/test_occupancy_immutable.py` da o'lchanadi;
bu yerda faqat trigger UMUMAN ULANGANI va qaysi hodisalarga bog'langani
tekshiriladi — ikkalasi ham alohida buzilishi mumkin.
"""

from __future__ import annotations

import re

import pytest
from psycopg import Connection
from psycopg.rows import TupleRow

from migrations.helpers import audit_trigger_name

pytestmark = pytest.mark.tenancy

BILLABLE_ANCHOR_FK = "fk_occupancy_events_snapshot_billable"
"""D-21 langariga osiladigan kompozit FK — 5-faza uni AYNAN shu nom bilan izlaydi."""

QUEUE_KIND_ANCHOR_FK = "fk_zone_reviews_queue_kind_anchor"
"""`zone_reviews.queue_kind` nusxasini manbasiga qadaydigan FK (D-17.3)."""

UNAUDITED_OCCUPANCY_TABLES: tuple[str, ...] = (
    "occupancy_events",
    "audit_rounds",
    "review_assignments",
    "stall_slot_occupancy",
)
"""Audit triggeri ATAYIN ULANMAGAN jadvallar (§S-1, audit assimetriyasi)."""

DEFINER_SURFACES: tuple[str, ...] = ()
"""⛔ BO'SHATILDI (`06-04` / T2, 2026-08-10) — IKKALA YUZA `0020` DA DROP QILINDI.

=============================================================================
NEGA BO'SH TO'PLAM «TESTNI O'CHIRISH» EMAS.

`audit_draw_due_markets()` va `occupancy_day_close_markets()`
CHAQIRUVCHISIZ qoldi: argumentli job modeli (D-12) ularni PRINSIPIAL
ravishda ishlata olmaydi — ikkalasining tanasi ham `now()` ga qadalgan,
job esa kunni ARGUMENT sifatida oladi. Chaqiruvchisiz `SECURITY DEFINER`
funksiya — RLS'ni chetlab o'tadigan ISHLATILMAYOTGAN yuza, ya'ni u faqat
xavf qo'shadi (C-11/G-10, T-06-22). `0020` ikkalasini ham DROP qildi.

⛔ RO'YXATNI BO'SHATISH MAJBURIY, TANLOV EMAS:
`test_due_markets_functions_expose_only_identifiers` har bir imzo uchun
`assert row is not None, "bazada topilmadi"` bajaradi, ya'ni bazada
YO'Q funksiya nomi qolgan taqdirda test AYNAN o'sha assert bilan
qizarardi — va yagona «tuzatish» yo'li funksiyani QAYTA YARATISH bo'lardi,
ya'ni endigina yopilgan yuzani qayta ochish.

⚠ DA'VO SUSAYMADI, U KO'CHDI: «RLS'ni chetlab o'tadigan yuza tor
bo'lsin» invarianti endi `test_meta.py::test_security_definer_functions_
set_search_path` (`found >= EXPECTED_DEFINER_FUNCTIONS`) va
`test_snapshot_domain_meta.py::test_capture_due_markets_exposes_only_
identifiers` da yashaydi — ikkalasi ham HAMON YASHIL va HAMON amalda.
`capture_due_markets()` esa bu ro'yxatdagi ikkovidan farqli o'laroq
HAQIQIY chaqiruvchiga ega, ya'ni u DROP qilinmadi.

⛔ YANGI NOM BU YERGA FAQAT SHU BILAN QO'SHILADI: `0018` yoki keyingi
migratsiya bandlik domeniga YANGI `SECURITY DEFINER` funksiya qo'shsa.
Bo'sh to'plam «tik yuzasi yo'q» degani, «tekshirilmaydi» degani EMAS.
=============================================================================
"""

FORBIDDEN_SURFACE_TOKENS: tuple[str, ...] = (
    "verdict",
    "confidence",
    "model_version",
    "shown_ai_verdict",
    "human_verdict",
    "polygon",
)
"""Bu yuzalardan HECH QACHON chiqmasligi kerak bo'lgan tushunchalar.

⚠ `verdict` VA `confidence` D-17 SHAROITIDA IKKINCHI MA'NOGA EGA: namuna
tortadigan funksiya ularni qaytara olsa, ko'r auditning NAMUNASINI
OLDINDAN KO'RISH yo'li ochilardi — ya'ni xolis o'lchov oldindan bilib
olinadigan bo'lardi (T-05-19). 4-fazadagi `market_name`/`vendor` ro'yxati
faqat tenant sizishi haqida edi; bu yerda ro'yxat KENGROQ.
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
bo'lib qolardi (`test_market_delete_guard.py` da o'rnatilgan qoida).
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

NON_INTERNAL_TRIGGERS = """
SELECT tg.tgname, pg_get_triggerdef(tg.oid)
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
qo'yadi va usiz «trigger yo'q» da'vosi HECH QACHON rost bo'lmasdi.
"""

PUBLIC_TABLES = """
SELECT c.relname
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public' AND c.relkind = 'r'
"""


def _defs(conn: Connection[TupleRow], table: str, contype: str) -> dict[str, str]:
    return {
        str(row[0]): str(row[1])
        for row in conn.execute(CONSTRAINT_DEFS, (table, contype)).fetchall()
    }


def _triggers(conn: Connection[TupleRow], table: str) -> dict[str, str]:
    return {
        str(row[0]): str(row[1]) for row in conn.execute(NON_INTERNAL_TRIGGERS, (table,)).fetchall()
    }


def _normalized(definition: str) -> str:
    """Bo'shliqlarni bir xillashtiradi — `pg_get_constraintdef` shaklidan mustaqil.

    PostgreSQL `REFERENCES snapshots(id, is_billable)` deb chiqaradi (jadval
    nomidan keyin BO'SHLIQSIZ), reja va hujjatlar esa `REFERENCES snapshots
    (id, is_billable)` deb yozadi. Ikkalasini bitta shaklga keltirish
    testni FORMATLASHDAN emas, MAZMUNDAN bog'liq qiladi.
    """
    return re.sub(r"\s+", " ", definition).replace("(", " (").replace("  ", " ")


def test_occupancy_events_reference_the_billable_anchor(
    sync_app_conn: Connection[TupleRow], migrated: None
) -> None:
    """`occupancy_events` `snapshots (id, is_billable)` LANGARIGA osilgan (D-21).

    =========================================================================
    BU FK — FAZANING ENG QIMMAT SATRI VA U 4-FAZADA QO'YILGAN LANGARGA
    OSILADI (`uq_snapshots_billable_anchor`).

    `snapshots.is_billable` — `GENERATED ALWAYS AS (quality_verdict = 'ok')
    STORED`, ya'ni `quality_verdict <> 'ok'` kadr uchun kerak bo'lgan
    `(id, true)` juftligi JADVALDA UMUMAN MAVJUD BO'LMAYDI. Natijada
    «yaroqsiz kadr billing'ga ta'sir qilmaydi» da'vosi KELISHUV emas, DB
    XATOSI bo'ladi.

    FK olib tashlansa yagona «tuzatish» yo'li kafolatni ilova qatlamiga
    ko'chirish — ya'ni uni BUTUNLAY yo'qotish — bo'lardi: kod qatlamidagi
    `if snapshot.is_billable` tekshiruvini xom `INSERT` ham, kelajakdagi
    ikkinchi yozuvchi ham chetlab o'tardi.
    =========================================================================
    """
    foreign_keys = _defs(sync_app_conn, "occupancy_events", "f")

    assert BILLABLE_ANCHOR_FK in foreign_keys, (
        f"`occupancy_events` da `{BILLABLE_ANCHOR_FK}` YO'Q. Mavjudlari: "
        f"{sorted(foreign_keys)}. Busiz yaroqsiz kadrga bandlik dalilini "
        "bog'lash mumkin bo'lib qoladi va D-21 ning kafolati kelishuvga "
        "aylanadi (T-05-18)."
    )
    definition = _normalized(foreign_keys[BILLABLE_ANCHOR_FK])
    assert "FOREIGN KEY (snapshot_id, snapshot_is_billable)" in definition, (
        f"FK ustunlari kutilganidek emas: {definition!r}. Juftlik AYNAN "
        "`(snapshot_id, snapshot_is_billable)` bo'lishi shart."
    )
    assert "REFERENCES snapshots (id, is_billable)" in definition, (
        f"FK nishoni kutilganidek emas: {definition!r}. Nishon "
        "`uq_snapshots_billable_anchor` konstrayti, ya'ni AYNAN "
        "`(id, is_billable)` juftligi — boshqa tartib yoki qo'shimcha "
        "ustun bilan langar ishlamaydi."
    )


def test_occupancy_events_check_forbids_false(
    sync_app_conn: Connection[TupleRow], migrated: None
) -> None:
    """`CHECK (snapshot_is_billable)` — LANGARNING IKKINCHI YARMI.

    =========================================================================
    ⚠ FK YOLG'IZ O'ZI YETARLI EMAS VA BU O'LCHANGAN FAKT
    (`tests/fixtures/billable_probe.py:87-104`).

    `snapshots` da HAR IKKALA juftlik ham mavjud: `(id, true)` yaroqli
    kadrlar uchun va `(id, false)` yaroqsizlar uchun. Ya'ni FK yolg'iz
    o'zi `snapshot_is_billable = false` bilan yozilgan qatorni BEMALOL
    qabul qilardi — u ham HAQIQIY juftlikka ishora qiladi.

    `CHECK` `false` ni butunlay taqiqlaydi, ya'ni yagona mumkin bo'lgan
    havola — `is_billable = true` bo'lgan kadrga. Ikkovi BIRGA ishlaydi va
    bittasi ikkinchisisiz MA'NOSIZ.
    =========================================================================
    """
    checks = _defs(sync_app_conn, "occupancy_events", "c")

    matching = {
        name: definition
        for name, definition in checks.items()
        if "snapshot_is_billable" in definition
    }
    assert matching, (
        "`occupancy_events` da `snapshot_is_billable` ustidagi `CHECK` YO'Q. "
        f"Mavjud `CHECK` lar: {sorted(checks)}. Usiz kompozit FK "
        "`(id, false)` juftligiga havolani ham qabul qiladi va yaroqsiz "
        "kadr bandlik dalilini ko'tara oladi."
    )
    definition = _normalized(next(iter(matching.values())))
    assert "CHECK (snapshot_is_billable)" in definition, (
        f"`CHECK` ifodasi kutilganidek emas: {definition!r} — u `false` ni "
        "SHARTSIZ taqiqlashi kerak (`snapshot_is_billable = true` shakli ham "
        "to'g'ri bo'lardi, lekin `NULL` ni o'tkazib yuborardi)."
    )


def test_blind_queue_implies_not_shown(sync_app_conn: Connection[TupleRow], migrated: None) -> None:
    """«KO'R AUDIT, LEKIN JAVOB KO'RSATILGAN» QATORI MAVJUD BO'LA OLMAYDI (D-17.3).

    =========================================================================
    Bu fazadagi eng nozik kafolat, chunki uni buzish uchun hech narsani
    "buzish" kerak emas: yetarli bo'lardi ko'r audit sahifasiga AI javobini
    ko'rsatib qo'yish va qatorni odatdagidek yozish. O'shanda nazoratchi
    javobi ANKORLANARDI (u model bilan rozi bo'lish tomon siljirdi) va
    aniqlik hisoboti o'z-o'zini tasdiqlardi — nosozlik esa hech qayerda
    ko'rinmasdi, chunki hamma qator "to'g'ri" bo'lardi.

    `CHECK` konstrayti bu holatni IFODALAB BO'LMAYDIGAN qiladi: yozib
    bo'lmaydigan holat "unutilishi" ham mumkin emas.
    =========================================================================
    """
    checks = _defs(sync_app_conn, "zone_reviews", "c")

    matching = [definition for definition in checks.values() if "shown_ai_verdict" in definition]
    assert matching, (
        "`zone_reviews` da `shown_ai_verdict` ustidagi `CHECK` YO'Q. "
        f"Mavjudlari: {sorted(checks)}. Usiz ko'r audit sahifasiga AI "
        "javobini ko'rsatib qo'yish DB darajasida to'sqinliksiz bo'lardi "
        "(D-17.3, T-05-44)."
    )
    definition = _normalized(matching[0])
    assert "blind_audit" in definition, f"`CHECK` ko'r audit navbatiga bog'lanmagan: {definition!r}"
    assert "shown_ai_verdict = false" in definition or "NOT shown_ai_verdict" in definition, (
        f"`CHECK` `shown_ai_verdict` ni `false` ga majburlamayapti: {definition!r}"
    )


def test_zone_review_queue_kind_is_anchored_to_its_assignment(
    sync_app_conn: Connection[TupleRow], migrated: None
) -> None:
    """`zone_reviews.queue_kind` NUSXASI MANBASIGA QADALGAN (D-17.3 ning ikkinchi yarmi).

    =========================================================================
    ⚠ USIZ YUQORIDAGI `CHECK` O'Z NUSXASIGA ISHONARDI.

    `CHECK` boshqa jadvalni o'qiy olmaydi, ya'ni ko'r audit sharti
    `zone_reviews` dagi DENORMALIZATSIYA qilingan `queue_kind` ga tayanadi.
    Nusxani `'uncertain'` deb yozish sharti YOLG'ONGA aylantirardi va
    `shown_ai_verdict = true` bemalol o'tardi — ya'ni kafolat bitta
    `INSERT` bilan chetlab o'tilardi.

    Kompozit FK `(review_assignment_id, queue_kind)` ni
    `review_assignments (id, queue_kind)` langariga qadaydi, ya'ni nusxa
    manbadan FARQ QILA OLMAYDI. Bu 4-fazadagi `uq_snapshots_billable_anchor`
    naqshining aynan takrori: denormalizatsiya haqiqat chegarasini
    bo'shatish uchun bahona emas.
    =========================================================================
    """
    foreign_keys = _defs(sync_app_conn, "zone_reviews", "f")

    assert QUEUE_KIND_ANCHOR_FK in foreign_keys, (
        f"`zone_reviews` da `{QUEUE_KIND_ANCHOR_FK}` YO'Q. Mavjudlari: "
        f"{sorted(foreign_keys)}. Busiz `queue_kind` nusxasi yolg'on "
        "yozilishi mumkin va D-17.3 ning `CHECK` i chetlab o'tiladi."
    )
    definition = _normalized(foreign_keys[QUEUE_KIND_ANCHOR_FK])
    assert "FOREIGN KEY (review_assignment_id, queue_kind)" in definition, (
        f"FK ustunlari kutilganidek emas: {definition!r}"
    )
    assert "REFERENCES review_assignments (id, queue_kind)" in definition, (
        f"FK nishoni kutilganidek emas: {definition!r}"
    )


def test_one_event_cannot_be_in_two_queues(
    sync_app_conn: Connection[TupleRow], migrated: None
) -> None:
    """`UNIQUE (occupancy_event_id)` — bir hodisa ENG KO'PI BILAN bitta navbatda.

    =========================================================================
    POYGA DB'GA TOPSHIRILGAN (`nvr_repo.py:509-517` naqshi).

    Ko'r audit tortish va noaniq navbat qurish — IKKI ALOHIDA job va ular
    bir vaqtda ishlashi mumkin. «Avval tekshir, keyin yoz» ikkalasiga ham
    bo'sh holatni ko'rsatardi va bitta hodisa uchun IKKITA yozuv
    tug'ilardi: nazoratchi bir zonani ikki marta ko'rardi va uning
    ikkinchi javobi aniqlik hisobotiga IKKINCHI marta kirardi.

    ⚠ KONSTRAYT `market_id` BILAN BOSHLANMAYDI va bu ATAYIN — da'vo tenant
    chegarasiga bog'liq BO'LMASLIGI kerak. Nom `test_meta.py::
    INDEX_EXCEPTIONS` ga sabab bilan qo'shilgan.
    =========================================================================
    """
    uniques = _defs(sync_app_conn, "review_assignments", "u")

    matching = [
        definition
        for definition in uniques.values()
        if _normalized(definition).strip() == "UNIQUE (occupancy_event_id)"
    ]
    assert matching, (
        "`review_assignments` da AYNAN `UNIQUE (occupancy_event_id)` YO'Q. "
        f"Mavjudlari: {uniques}. `(market_id, occupancy_event_id)` shakli "
        "bugun bir xil natija berardi, lekin u kafolatni IKKINCHI faktga "
        "bog'lab qo'yardi."
    )


def test_occupancy_events_have_no_audit_trigger(
    sync_app_conn: Connection[TupleRow], migrated: None
) -> None:
    """To'rtta jadvalda audit trigger YO'Q; ikkitasida BOR (§S-1 assimetriyasi).

    =========================================================================
    IKKI MUSTAQIL SABAB, BIR XIL QAROR:

      (a) HAJM: 175 kadr/kun/bozor x ~30 zona ~ 5 000 qator/kun/bozor —
          4-fazadagi ~525 audit qatorining O'N BAROBARI;
      (b) `occupancy_events` SHARTSIZ o'zgarmas (`0018`), ya'ni audit faqat
          `INSERT` ni ko'rardi — o'sha ma'lumotning IKKINCHI NUSXASI.

    NAZORAT BANDI: `camera_zones` va `zone_reviews` da trigger BO'LISHI
    tekshiriladi. Usiz so'rov noto'g'ri yozilganda (sxema nomi xato,
    `tgisinternal` filtri teskari) u HAR BIR jadval uchun bo'sh qaytarardi
    va yuqoridagi inkor da'vosi JIMGINA rost bo'lib qolardi
    (`test_nvr_domain_meta.py::test_nvr_credentials_has_no_audit_trigger`
    da o'rnatilgan qoida).
    =========================================================================
    """
    for table in UNAUDITED_OCCUPANCY_TABLES:
        triggers = _triggers(sync_app_conn, table)
        assert audit_trigger_name(table) not in triggers, (
            f"`{table}` ga audit triggeri ulangan ({sorted(triggers)}). Bu "
            "jadval hodisa jurnali yoki o'zgarmas jadval: audit unga o'sha "
            "ma'lumotning ikkinchi nusxasini yozadi va `audit_log` ni "
            "kuniga ~5 000 qatorga o'stiradi (§S-1)."
        )

    for table in ("camera_zones", "zone_reviews"):
        audited = _triggers(sync_app_conn, table)
        assert audit_trigger_name(table) in audited, (
            f"`{table}` da audit triggeri topilmadi ({sorted(audited)}) — "
            "so'rov buzilgan bo'lishi mumkin, bunday holatda yuqoridagi "
            "inkor da'vosi hech nimani o'lchamasdi. Bu jadval AUDITDA "
            "bo'lishi SHART: poligonni siljitish ham, nazoratchining "
            "verdikti ham moliyaviy oqibatga ega."
        )


def test_immutability_triggers_are_before_update_or_delete(
    sync_app_conn: Connection[TupleRow], migrated: None
) -> None:
    """Ikkala qo'riqchi ham `BEFORE UPDATE OR DELETE ... FOR EACH ROW` (D-12).

    =========================================================================
    UCH DETAL VA HAR BIRI ALOHIDA BUZILISHI MUMKIN:

      * `BEFORE` — qo'riqchi o'zgarish SODIR BO'LISHIDAN OLDIN to'xtatishi
        kerak. `AFTER` variantida qator allaqachon o'zgargan bo'lardi va
        istisno faqat tranzaksiyani qaytarardi — xom `COMMIT` yo'li bilan
        yozilgan har qanday o'zgarish esa o'tib ketardi.
      * `UPDATE OR DELETE` — faqat bittasini qamrash yarim himoya bo'lardi:
        `UPDATE` siz javobni MOSLASHTIRISH, `DELETE` siz noqulay dalilni
        YO'Q QILISH mumkin bo'lardi.
      * IKKI ALOHIDA FUNKSIYA — xato xabari QAYSI qoida buzilganini
        aytishi kerak (`helpers.py::attach_immutability_trigger`).

    XULQ (haqiqiy `UPDATE`/`DELETE` urinishi)
    `tests/integration/test_occupancy_immutable.py` da o'lchanadi — shakl
    va xulq ikki xil savol.
    =========================================================================
    """
    for table, trigger_name, function_name in (
        ("occupancy_events", "trg_occupancy_event_immutable", "occupancy_event_immutable"),
        ("zone_reviews", "trg_zone_review_immutable", "zone_review_immutable"),
    ):
        triggers = _triggers(sync_app_conn, table)
        assert trigger_name in triggers, (
            f"`{table}` da `{trigger_name}` YO'Q ({sorted(triggers)}) — AI "
            "javobi yoki nazoratchi javobi tahrirlanadigan bo'lib qoladi "
            "(D-12/D-17.4)."
        )
        definition = triggers[trigger_name]
        assert "BEFORE" in definition, (
            f"`{trigger_name}` `BEFORE` emas: {definition!r} — qator o'zgarishi "
            "SODIR BO'LGANDAN keyin to'xtatish kech."
        )
        for event in ("UPDATE", "DELETE"):
            assert event in definition, (
                f"`{trigger_name}` `{event}` ni qamramaydi: {definition!r} — "
                "yarim himoya himoya emas."
            )
        assert function_name in definition, (
            f"`{trigger_name}` boshqa funksiyani chaqiryapti: {definition!r} — "
            "xato xabari qaysi qoida buzilganini aytmaydi."
        )


def test_business_date_is_not_generated(
    sync_app_conn: Connection[TupleRow], migrated: None
) -> None:
    """`occupancy_events.business_date` HOSILA USTUN EMAS — u NUSXA (Pitfall 3).

    =========================================================================
    ⚠ BU TEST TESKARI YO'NALISHDA ISHLAYDI VA U ATAYIN SHUNDAY.

    4-fazada `business_date` HOSILA bo'lishi TALAB qilinadi
    (`snapshots`/`capture_runs` — ular biznes-kunni `scheduled_at` dan
    hisoblaydi). Bu yerda esa TESKARISI talab qilinadi: `occupancy_events`
    biznes-kunni QAYTA HISOBLAMASLIGI kerak.

    Sabab: hodisa `snapshots` ga bog'langan va kadrning biznes-kuni
    ALLAQACHON hisoblangan. Ikkinchi (mustaqil) ifoda yarim tunda bir kun
    farq qilishi mumkin edi — o'shanda kadr `snapshots` da 09-01 ga,
    bandlik dalili esa 09-02 ga tushardi va 6-faza uni "yo'q" deb ko'rardi.
    Ikkala qator ham mavjud, ikkalasi ham to'g'ri ko'rinadi — nosozlik
    JIMGINA.

    NAZORAT BANDI: `snapshots.business_date` HOSILA ekani tekshiriladi.
    Usiz so'rov noto'g'ri yozilganda (`attgenerated` o'rniga boshqa ustun)
    yuqoridagi inkor da'vosi HAR DOIM rost bo'lardi.
    =========================================================================
    """
    for table in ("occupancy_events", "stall_slot_occupancy"):
        row = sync_app_conn.execute(GENERATED_COLUMN, (table, "business_date")).fetchone()
        assert row is not None, f"`{table}.business_date` `pg_attribute` da topilmadi"
        assert (row[0] or "") == "", (
            f"`{table}.business_date` HOSILA ustun ({row[0]!r}) — ya'ni "
            "biznes-kun IKKINCHI marta, mustaqil ravishda hisoblanadi. "
            "Yarim tun atrofida ikki manba bir kun farq qiladi va dalil "
            "hisobda 'yo'q' bo'lib qoladi (Pitfall 3)."
        )

    control = sync_app_conn.execute(GENERATED_COLUMN, ("snapshots", "business_date")).fetchone()
    assert control is not None and control[0] == "s", (
        f"`snapshots.business_date` HOSILA ustun EMAS ({control}) — so'rov "
        "buzilgan bo'lishi mumkin, bunday holatda yuqoridagi inkor da'vosi "
        "hech nimani o'lchamasdi"
    )


def test_occupancy_registries_match_the_database(
    sync_app_conn: Connection[TupleRow], migrated: None
) -> None:
    """Uchala reyestr bazadagi HAQIQIY jadvallarga mos (W0-4/W0-5/W0-6).

    `test_meta.py::test_occupancy_registries_are_self_consistent` reyestrlarni
    BIR-BIRIGA solishtiradi va u jadval tug'ilishidan OLDIN ham ishlaydi.
    Bu esa ularni BAZAGA solishtiradi va faqat `0018` qo'ngandan keyin
    ma'noga ega. Ikkalasi ketma-ket turadi: birinchisi reyestrlar ajralib
    ketganini, ikkinchisi reyestr bilan sxema ajralib ketganini ushlaydi.
    """
    from migrations.entities import (
        OCCUPANCY_AUDITED_TABLES,
        OCCUPANCY_DELETE_ORDER,
        OCCUPANCY_TENANT_TABLES,
    )

    existing = {str(row[0]) for row in sync_app_conn.execute(PUBLIC_TABLES).fetchall()}

    missing = sorted(set(OCCUPANCY_TENANT_TABLES) - existing)
    assert not missing, (
        f"reyestrdagi jadval bazada YO'Q: {missing} — `0018` migratsiyasi reyestrdan ajralib ketgan"
    )
    assert set(OCCUPANCY_DELETE_ORDER) == set(OCCUPANCY_TENANT_TABLES), (
        "kaskad tartibi tenant reyestriga mos emas — `0019` ba'zi jadvallarni "
        "o'chirmasdi va qoralama bozorni o'chirish FK buzilishi bilan yiqilardi"
    )
    assert set(OCCUPANCY_AUDITED_TABLES) < set(OCCUPANCY_TENANT_TABLES), (
        "`OCCUPANCY_AUDITED_TABLES` tenant reyestrining QAT'IY kichik to'plami "
        f"bo'lishi shart. Topilgani: {list(OCCUPANCY_AUDITED_TABLES)}"
    )

    # Reyestr va SXEMA: auditda deb e'lon qilingan har bir jadvalda trigger
    # HAQIQATAN bor. Bu `test_meta.py::test_audited_tables_have_trigger` ning
    # takrori EMAS — u `AUDITED_TABLES` (butun loyiha) ustidan yuradi, bu esa
    # domen reyestri bilan sxemani solishtiradi.
    for table in OCCUPANCY_AUDITED_TABLES:
        assert audit_trigger_name(table) in _triggers(sync_app_conn, table), (
            f"`{table}` `OCCUPANCY_AUDITED_TABLES` da, lekin bazada audit triggeri yo'q"
        )


def test_due_markets_functions_expose_only_identifiers(
    sync_owner_conn: Connection[TupleRow], migrated: None
) -> None:
    """Ikkala tik yuzasi FAQAT identifikator va sanoq qaytaradi (T-05-19).

    =========================================================================
    `test_snapshot_domain_meta.py::test_capture_due_markets_exposes_only_
    identifiers` ning JUFTI, LEKIN RO'YXAT KENGROQ.

    4-fazada taqiq faqat tenant sizishi haqida edi (`market_name`,
    `vendor`). Bu yerda unga IKKINCHI ma'no qo'shiladi (D-17): namuna
    tortadigan funksiya `verdict` yoki `confidence` ni qaytara olsa, ko'r
    auditning NAMUNASINI OLDINDAN KO'RISH yo'li ochilardi — ya'ni xolis
    o'lchov oldindan bilib olinadigan bo'lardi va butun AI-04 mexanizmi
    ma'nosini yo'qotardi.

    Ta'rif `pg_get_functiondef()` dan o'qiladi, ya'ni SQL IZOHLARI HAM
    tekshiriladi (Python docstringi unga kirmaydi — u xavfsiz).

    QAYTISH TIPI ALOHIDA tekshiriladi: tanada taqiqlangan so'z bo'lmasligi
    «yuza tor» degani EMAS — `RETURNS TABLE (..., verdict text)` shakli
    tanada bironta taqiqlangan so'zsiz ham yozilishi mumkin edi.
    =========================================================================
    """
    for signature in DEFINER_SURFACES:
        row = sync_owner_conn.execute(
            "SELECT pg_get_functiondef(%s::regprocedure), "
            "       pg_get_function_result(%s::regprocedure)",
            (f"public.{signature}", f"public.{signature}"),
        ).fetchone()
        assert row is not None, f"`{signature}` bazada topilmadi"
        body, result = str(row[0]), str(row[1])

        assert "SECURITY DEFINER" in body, (
            f"`{signature}` `SECURITY DEFINER` emas — fon-vazifa tenant "
            "kontekstisiz birorta bozorni ko'ra olmaydi va u JIMGINA 0 "
            "bozor ustida ishlardi"
        )
        assert "search_path" in body, (
            f"`{signature}` da `SET search_path` yo'q — `SECURITY DEFINER` "
            "funksiyada bu klassik privilege-escalation vektori"
        )
        for forbidden in FORBIDDEN_SURFACE_TOKENS:
            assert forbidden not in body, (
                f"`{signature}` ta'rifida `{forbidden}` uchraydi. Funksiya "
                "RLS'ni chetlab o'tadi, ya'ni uning yuzasi FAQAT "
                "identifikator va sanoqdan iborat bo'lishi shart; D-17 "
                "sharoitida bu ko'r audit namunasini oldindan ko'rish "
                "yo'lini ham ochardi (T-05-19)."
            )

        columns = _table_result_columns(result)
        assert columns, f"`{signature}` `RETURNS TABLE` shaklida emas: {result!r}"
        for name, sql_type in columns:
            assert sql_type in {"uuid", "integer"}, (
                f"`{signature}` `{name} {sql_type}` ustunini qaytaryapti — "
                "ruxsat etilgani faqat `uuid` (identifikator) va `integer` "
                "(sanoq)."
            )


def _table_result_columns(result: str) -> list[tuple[str, str]]:
    """`TABLE(market_id uuid, frame_size integer)` -> `[('market_id', 'uuid'), ...]`.

    Parser ATAYIN sodda: u faqat `TABLE(...)` shaklini tushunadi va boshqa
    har qanday shaklda BO'SH ro'yxat qaytaradi — chaqiruvchi esa bo'sh
    ro'yxatni YIQILISH deb hisoblaydi. Ya'ni funksiya `SETOF snapshots`
    ga aylantirilsa (butun qatorni qaytaradigan shakl) test JIMGINA
    yashil qolmaydi.
    """
    match = re.fullmatch(r"TABLE\((.*)\)", result.strip(), flags=re.DOTALL)
    if match is None:
        return []
    columns: list[tuple[str, str]] = []
    for part in match.group(1).split(","):
        tokens = part.split()
        if len(tokens) != 2:
            return []
        columns.append((tokens[0], tokens[1]))
    return columns
