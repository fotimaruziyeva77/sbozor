"""D-23 ZONDI — `GENERATED STORED` ustunning kompozit FK'dagi xulqi.

=============================================================================
ZONDNING YAGONA SAVOLI:

    `GENERATED ALWAYS AS (...) STORED` ustun ustidagi `UNIQUE`
    kompozit FK ning NISHONI bo'la oladimi (`postgres:18.4`)?

Javob `migrations/versions/0014_snapshot_domain.py` NING SHAKLINI
belgilaydi (D-16 / D-23 / OQ-4):

  * HA  -> `snapshots.is_billable` `GENERATED ALWAYS AS
           (quality_verdict = 'ok') STORED` + `UNIQUE (id, is_billable)`;
           5-fazadagi `occupancy_events` unga kompozit FK bilan tayanadi
           va yaroqsiz kadr bandlik dalilini UMUMAN yarata olmaydi.
  * YO'Q -> `is_billable` oddiy `boolean NOT NULL` va uni
           `BEFORE INSERT/UPDATE` trigger `quality_verdict` dan
           hisoblaydi. Kafolat SAQLANADI, narxi ~15 qator.

⚠ NEGA JADVAL EMAS, ZOND. `snapshots` ning o'zi hali mavjud emas
  (`0014` uni shu o'lchovdan KEYIN yaratadi) va aynan shu sabab
  o'lchovni migratsiyadan OLDIN qilishga majbur qiladi: natijani keyin
  bilib olish QAYTA MIGRATSIYA demakdir. Shabloni —
  `tests/fixtures/financial.py:59-145` (u ham mavjud bo'lmagan
  moliyaviy jadvalning DDL yo'lini oldindan isbotlagan).

⚠ IKKI DDL ALOHIDA BAJARILADI VA BU MAJBURIY. Bitta `execute` da
  birlashtirilsa ota-jadvalning muvaffaqiyati bola-jadvalning
  nosozligi bilan BIR XIL tranzaksiyada yo'qolardi va zond «nima
  ishlamadi» ni ayta olmasdi — natija «probe qurilmadi» degan
  ma'nosiz signalga aylanardi.
=============================================================================

Jadvallar `sbozor_owner` bilan yaratiladi (`sbozor_app` `public` sxemada
obyekt yarata olmaydi — T-01-06) va har testdan keyin o'chiriladi. RLS
ATAYIN yoqilmaydi: bu zond KONSTRAYTNI o'lchaydi, izolyatsiyani emas.
"""

from __future__ import annotations

from dataclasses import dataclass

import psycopg
from psycopg import Connection
from psycopg.rows import TupleRow

__all__ = [
    "CHILD_TABLE",
    "INSERT_OCCUPANCY",
    "INSERT_SNAPSHOT",
    "PARENT_TABLE",
    "SELECT_VERDICT_ID",
    "UPDATE_VERDICT",
    "BillableProbe",
    "create_billable_probe",
    "drop_billable_probe",
]

# Jadval nomlari SQL matnlarida LITERAL yozilgan (`financial.py:53-58` da
# o'rnatilgan qoida): bu yerda dinamiklikka ehtiyoj yo'q, literal shakl
# SQL'ni o'qishni osonlashtiradi va ruff `S608` yolg'on-musbatini bermaydi.
PARENT_TABLE = "probe_snapshots"
CHILD_TABLE = "probe_occupancy"

_DROP_SQL = (
    "DROP TABLE IF EXISTS probe_occupancy",
    "DROP TABLE IF EXISTS probe_snapshots",
)

# Ota-jadval: `snapshots` ning MINIMAL shakli. Faqat o'lchov uchun kerak
# bo'lgan uchta ustun — `market_id`, `capture_run_id`, `object_key` va
# boshqalar bu savolga hech nima qo'shmaydi.
#
# `UNIQUE (id, is_billable)` — D-16 ning LANGARI. `id` yolg'iz o'zi ham
# noyob (PK), ya'ni bu konstrayt ma'lumot jihatidan ORTIQCHA ko'rinadi —
# va aynan shu ortiqchalik FK ga `is_billable` ni juftlikka kirita
# oladigan yagona nishon beradi.
_CREATE_PARENT = """
CREATE TABLE probe_snapshots (
    id              uuid PRIMARY KEY DEFAULT uuidv7(),
    quality_verdict text NOT NULL,
    is_billable     boolean GENERATED ALWAYS AS (quality_verdict = 'ok') STORED,
    CONSTRAINT uq_probe_snapshots_billable_anchor UNIQUE (id, is_billable)
)
"""

# Bola-jadval: 5-fazadagi `occupancy_events` ning minimal shakli.
#
# `CHECK (snapshot_is_billable)` — juftlikning IKKINCHI yarmi va usiz
# butun konstruksiya ma'nosiz bo'lardi: FK yolg'iz o'zi `(id, false)`
# juftligiga havolani ham QABUL QILARDI (u ham mavjud juftlik). CHECK
# `false` ni butunlay taqiqlaydi, ya'ni yagona mumkin bo'lgan havola —
# `is_billable = true` bo'lgan kadrga.
_CREATE_CHILD = """
CREATE TABLE probe_occupancy (
    id                   uuid PRIMARY KEY DEFAULT uuidv7(),
    snapshot_id          uuid NOT NULL,
    snapshot_is_billable boolean NOT NULL DEFAULT true,
    CONSTRAINT ck_probe_occupancy_billable CHECK (snapshot_is_billable),
    CONSTRAINT fk_probe_occupancy_snapshot
        FOREIGN KEY (snapshot_id, snapshot_is_billable)
        REFERENCES probe_snapshots (id, is_billable)
)
"""

INSERT_SNAPSHOT = "INSERT INTO probe_snapshots (quality_verdict) VALUES (%s)"
SELECT_VERDICT_ID = "SELECT id FROM probe_snapshots WHERE quality_verdict = %s"
INSERT_OCCUPANCY = "INSERT INTO probe_occupancy (snapshot_id) VALUES (%s)"
UPDATE_VERDICT = "UPDATE probe_snapshots SET quality_verdict = %s WHERE id = %s"

_SERVER_VERSION = "SELECT version()"


@dataclass(frozen=True)
class BillableProbe:
    """O'lchov natijasi — `fk_supported` shu zondning BUTUN mahsuloti.

    `failure` `fk_supported = False` bo'lganda DDL xatosining TO'LIQ
    matnini tashiydi: «yaratilmadi» degan yalang'och `False` `04-03`
    ga `0014` ni qanday yozishni aytmasdi, xato matni esa aytadi.

    `server_version` SUMMARY uchun: o'lchov AYNAN qaysi serverda
    olingani yozilmasa, natija keyinroq «qayerda o'lchangan?» degan
    javobsiz savolga aylanardi.
    """

    conn: Connection[TupleRow]
    fk_supported: bool
    failure: str | None
    server_version: str


def create_billable_probe(conn: Connection[TupleRow]) -> BillableProbe:
    """Ota-jadvalni, so'ng bola-jadvalni ALOHIDA quradi va natijani o'lchaydi.

    Ota-jadvalning yiqilishi KUTILMAGAN holat va u ATAYIN yuqoriga
    ko'tariladi: `GENERATED STORED` + `UNIQUE` allaqachon isbotlangan
    sinf, ya'ni u yerdagi xato zondning savoliga emas, muhitga tegishli
    (noto'g'ri PG versiyasi, yetishmayotgan huquq) va uni `fk_supported`
    ga aylantirish o'lchovni SOXTALASHTIRARDI.
    """
    drop_billable_probe(conn)

    row = conn.execute(_SERVER_VERSION).fetchone()
    assert row is not None, "`SELECT version()` javob bermadi"
    server_version = str(row[0])

    conn.execute(_CREATE_PARENT)

    try:
        conn.execute(_CREATE_CHILD)
    except psycopg.Error as error:
        return BillableProbe(
            conn=conn,
            fk_supported=False,
            failure=f"{type(error).__name__}: {error}".strip(),
            server_version=server_version,
        )

    return BillableProbe(
        conn=conn,
        fk_supported=True,
        failure=None,
        server_version=server_version,
    )


def drop_billable_probe(conn: Connection[TupleRow]) -> None:
    """Zond jadvallarini FK tartibida o'chiradi (bola -> ota)."""
    for statement in _DROP_SQL:
        conn.execute(statement)
