"""D-23 O'LCHOVI — `GENERATED STORED` ustun kompozit FK NISHONI bo'la oladimi.

=============================================================================
BU FAYL BIRORTA XULQNI HIMOYA QILMAYDI — U BITTA SAVOLGA JAVOB O'LCHAYDI.

D-16 billing kafolatini KELISHUV emas, TUZILMA qilishni talab qiladi:

    snapshots      UNIQUE (id, is_billable)              <- langar
    occupancy_events  FOREIGN KEY (snapshot_id, snapshot_is_billable)
                      REFERENCES snapshots (id, is_billable)
                      + CHECK (snapshot_is_billable)     <- 5-fazada

Bunda yaroqsiz kadr (`quality_verdict <> 'ok'`) bandlik dalili UMUMAN
yarata olmaydi — DB rad etadi. Intizom, code review yoki ORM qatlami
emas: SXEMA.

Butun konstruksiya bitta o'lchanmagan faktga tayanadi. `is_billable`
`GENERATED ALWAYS AS (...) STORED` ustun bo'ladi, ya'ni savol:

    `GENERATED STORED` ustunning UNIQUE'i kompozit FK NISHONI bo'la
    oladimi (`postgres:18.4`)?

⚠ SAVOLNING FAQAT YARIMI MA'LUM. `GENERATED STORED` ustunning `UNIQUE`
  ga kirishi ALLAQACHON ISBOTLANGAN va u yashil test fakti
  (`migrations/helpers.py:356-362` -> `business_date` + `uq_*_business_day`,
  `tests/fixtures/financial.py`). FK-NISHON tomoni esa hech qayerda
  o'lchanmagan.

⚠ NEGA MIGRATSIYADAN OLDIN. Javob `0014` NING SHAKLINI belgilaydi:
  yiqilsa `is_billable` oddiy `boolean NOT NULL` bo'ladi va uni
  `BEFORE INSERT/UPDATE` trigger `quality_verdict` dan hisoblaydi
  (~15 qator, kafolat SAQLANADI). Buni migratsiyadan KEYIN bilib olish
  QAYTA MIGRATSIYA demakdir — shuning uchun zond Wave 0 da (W0-1 / OQ-4).
=============================================================================
"""

from __future__ import annotations

from collections.abc import Iterator

import psycopg
import pytest
from fixtures.billable_probe import (
    INSERT_OCCUPANCY,
    INSERT_SNAPSHOT,
    SELECT_VERDICT_ID,
    UPDATE_VERDICT,
    BillableProbe,
    create_billable_probe,
    drop_billable_probe,
)
from psycopg import Connection
from psycopg.rows import TupleRow

pytestmark = pytest.mark.tenancy

TRIGGER_FALLBACK = (
    "ZAXIRA VARIANT (D-23): `0014` da `is_billable` oddiy `boolean NOT NULL` "
    "bo'ladi va `BEFORE INSERT/UPDATE` trigger uni `quality_verdict` dan "
    "hisoblaydi (`migrations/entities/triggers.py` fabrikasi). Kafolat "
    "SAQLANADI — narxi ~15 qator. Bu satrni `04-03` o'qiydi."
)


@pytest.fixture
def probe(
    sync_owner_conn: Connection[TupleRow],
    migrated: None,
) -> Iterator[BillableProbe]:
    """Zond jadvallari — har testdan keyin tozalanadi.

    Tozalash MAJBURIY: `DROP` qilinmasa keyingi yugurish `DuplicateTable`
    bilan yiqilardi va sabab o'lchov natijasi kabi ko'rinardi.

    DDL `sbozor_owner` bilan bajariladi — `sbozor_app` `public` sxemada
    obyekt yarata olmaydi (T-01-06, `test_composite_fk.py` bilan bir xil).
    """
    created = create_billable_probe(sync_owner_conn)
    try:
        yield created
    finally:
        drop_billable_probe(sync_owner_conn)


def test_generated_stored_column_can_be_unique(probe: BillableProbe) -> None:
    """NAZORAT HOLATI: `GENERATED STORED` ustun `UNIQUE` ga kiradi.

    Bu ALLAQACHON ISBOTLANGAN sinf (`business_date` +
    `uq_*_business_day`), lekin u shu YERDA, shu SHAKLDA ham
    tasdiqlanadi. Sababi mexanik: quyidagi o'lchov shu da'voga tayanadi,
    ya'ni langarning o'zi yo'qolsa o'lchov «FK qo'llab-quvvatlanmaydi»
    degan YOLG'ON xulosa berardi. Nazorat holati o'sha yolg'onni ajratadi.
    """
    generated = probe.conn.execute(
        "SELECT a.attgenerated FROM pg_attribute a "
        "JOIN pg_class c ON c.oid = a.attrelid "
        "JOIN pg_namespace n ON n.oid = c.relnamespace "
        "WHERE n.nspname = 'public' AND c.relname = 'probe_snapshots' "
        "AND a.attname = 'is_billable'"
    ).fetchone()
    assert generated is not None, "`probe_snapshots.is_billable` ustuni topilmadi"
    assert generated[0] == "s", (
        f"`is_billable` GENERATED STORED emas (`attgenerated` = {generated[0]!r}). "
        "`s` kutilgan — VIRTUAL generated ustun `UNIQUE` ga umuman kira olmaydi."
    )

    anchor = probe.conn.execute(
        "SELECT pg_get_constraintdef(c.oid) FROM pg_constraint c "
        "WHERE c.conname = 'uq_probe_snapshots_billable_anchor' "
        "AND c.conrelid = 'probe_snapshots'::regclass"
    ).fetchone()
    assert anchor is not None, (
        "`uq_probe_snapshots_billable_anchor` yaratilmadi — `GENERATED STORED` "
        "ustun UNIQUE ga kirmadi. Bu KUTILMAGAN natija: mavjud "
        "`uq_*_business_day` konstraytlari aynan shu sinfda ishlaydi."
    )
    assert "UNIQUE (id, is_billable)" in anchor[0], (
        f"langar konstraytining ta'rifi kutilgandan boshqa: {anchor[0]!r}"
    )


def test_generated_stored_column_can_be_composite_fk_target(probe: BillableProbe) -> None:
    """⚠ BU O'LCHOV — D-23 / OQ-4 ning yagona savoli.

    `probe_occupancy` `GENERATED STORED` ustunni o'z ichiga olgan UNIQUE
    ga kompozit FK bilan havola qiladi. Yaratildimi — `0014` D-16 ning
    tuzilmaviy shaklida yoziladi; yaratilmadimi — trigger variantida.

    Natija testning NOMIDA emas, assert XABARIDA qoladi: `04-03` uni
    SUMMARY dan o'qiydi va `0014` ning shaklini shundan chiqaradi.
    """
    assert probe.fk_supported, (
        "`GENERATED STORED` ustun kompozit FK NISHONI bo'la OLMADI "
        f"(PostgreSQL: {probe.server_version}).\n\n"
        f"DDL xatosi: {probe.failure}\n\n" + TRIGGER_FALLBACK
    )


def test_non_billable_snapshot_cannot_be_referenced(probe: BillableProbe) -> None:
    """D-16 ning BUTUN MAZMUNI: yaroqsiz kadr bandlik dalili yarata olmaydi.

    Uch da'vo, uchalasi ham kerak:

      1. `'ok'` kadrga havola O'TADI — usiz keyingi ikki da'vo yolg'on-yashil
         bo'lardi (FK hamma narsani rad etayotgan bo'lsa ham «bloklandi»
         deb ko'rinardi);
      2. `'dark'` kadrga havola RAD ETILADI — kafolatning o'zi;
      3. mavjud `'ok'` kadrni `'dark'` ga O'ZGARTIRISH ham RAD ETILADI.
         Uchinchisi eng nozigi: usiz kafolat faqat YOZISH paytida ishlardi
         va keyin bir dona `UPDATE` bilan chetlab o'tilardi.
    """
    if not probe.fk_supported:
        pytest.skip(
            "kompozit FK yaratilmadi, ya'ni bu testning nishoni yo'q. "
            f"O'lchov natijasi: {probe.failure}. " + TRIGGER_FALLBACK
        )

    conn = probe.conn
    conn.execute(INSERT_SNAPSHOT, ("ok",))
    conn.execute(INSERT_SNAPSHOT, ("dark",))
    row_ok = conn.execute(SELECT_VERDICT_ID, ("ok",)).fetchone()
    row_dark = conn.execute(SELECT_VERDICT_ID, ("dark",)).fetchone()
    assert row_ok is not None and row_dark is not None, "zond qatorlari yozilmadi"
    ok_id, dark_id = row_ok[0], row_dark[0]

    # 1. NAZORAT: yaroqli kadr bandlik dalilini KO'TARA OLADI.
    conn.execute(INSERT_OCCUPANCY, (ok_id,))

    # 2. Yaroqsiz kadrga havola — SXEMA darajasida imkonsiz.
    with pytest.raises(psycopg.errors.ForeignKeyViolation) as insert_error:
        conn.execute(INSERT_OCCUPANCY, (dark_id,))
    assert "fk_probe_occupancy_snapshot" in str(insert_error.value), (
        f"rad etish boshqa konstraytdan keldi: {insert_error.value}"
    )

    # 3. Hukmni keyin o'zgartirib chetlab o'tish ham imkonsiz: `is_billable`
    #    `true` -> `false` ga o'tsa mavjud FK juftligi YO'QOLADI.
    with pytest.raises(psycopg.errors.ForeignKeyViolation) as update_error:
        conn.execute(UPDATE_VERDICT, ("dark", ok_id))
    assert "fk_probe_occupancy_snapshot" in str(update_error.value), (
        "hukmni `'dark'` ga o'zgartirish RAD ETILMADI — kafolat faqat "
        f"INSERT paytida ishlayapti: {update_error.value}"
    )
