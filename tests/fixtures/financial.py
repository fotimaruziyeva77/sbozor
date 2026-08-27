"""Moliyaviy PROBE jadvali — mezon #5 ni 6-fazadan OLDIN isbotlash uchun.

=============================================================================
NEGA PROBE JADVALI, NEGA `daily_charges` EMAS:

Mezon #5 moliyaviy jadvallar "dublikat-himoyasi bilan TUG'ILISHINI" talab
qiladi — ya'ni konstraytlar 6-fazada emas, undan OLDIN tayyor bo'lishi
kerak. Lekin `daily_charges` ning o'zi `stalls` jadvaliga tayanadi va
`stalls` 2-fazada tug'iladi, ya'ni jadvalni hozir yaratib bo'lmaydi.

Yechim: yordamchi (`migrations.helpers.financial_guards`) hozir yoziladi,
testlar esa uni HAQIQIY jadvalda ishga tushiradi. Shunda 6-fazada
`daily_charges` yaratilganda ishlatiladigan DDL yo'li AYNAN shu yerda
isbotlangan bo'ladi.

MUHIM: probe jadvalining konstraytlari QO'LDA yozilmaydi — ular
`financial_guard_statements()` dan olinadi. Nusxa yozilganida test yashil
qolib, migratsiya yordamchisi boshqa narsa qilishi mumkin edi (aynan
oldini olinayotgan drift).
=============================================================================

Jadvallar `sbozor_owner` bilan yaratiladi (`sbozor_app` `public` sxemada
obyekt yarata olmaydi) va har testdan keyin o'chiriladi. Ularda RLS
ATAYIN yoqilmaydi: bu testlar KONSTRAYTLARNI sinaydi, izolyatsiyani emas —
u `tests/tenancy` da alohida isbotlangan.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

from psycopg import Connection
from psycopg.rows import TupleRow

from migrations.helpers import financial_guard_statements

__all__ = [
    "CHILD_TABLE",
    "INSERT_CHARGE",
    "INSERT_CHARGE_AT",
    "INSERT_CHARGE_IDEMPOTENT",
    "INSERT_CHARGE_WITH_BUSINESS_DATE",
    "PARENT_TABLE",
    "SELECT_AMOUNT",
    "SELECT_DATES",
    "SELECT_ROWS",
    "FinancialProbe",
    "create_financial_probe",
    "drop_financial_probe",
]

# Jadval nomlari SQL matnlarida LITERAL yozilgan (o'zgaruvchi bilan
# birlashtirilmagan) — `tests/tenancy/test_composite_fk.py` da o'rnatilgan
# qoida: bu yerda dinamiklikka ehtiyoj yo'q, literal shakl SQL'ni o'qishni
# osonlashtiradi va ruff `S608` yolg'on-musbatini ham keltirib chiqarmaydi.
# Quyidagi ikki konstanta faqat jadval NOMI kerak bo'lgan joylar uchun
# (`financial_guard_statements()` argumenti, `information_schema` so'rovi).
PARENT_TABLE = "probe_stalls"
CHILD_TABLE = "probe_charges"

_DROP_SQL = (
    "DROP TABLE IF EXISTS probe_charges",
    "DROP TABLE IF EXISTS probe_stalls",
)

# Ota-jadval: `stalls` ning minimal shakli. `UNIQUE(market_id, id)` —
# composite FK ning MAQSADI (T-01-26): usiz bola-jadval `(market_id, id)`
# juftligiga havola qila olmaydi.
_CREATE_PARENT = """
CREATE TABLE probe_stalls (
    market_id uuid NOT NULL,
    id        uuid NOT NULL DEFAULT uuidv7(),
    CONSTRAINT pk_probe_stalls PRIMARY KEY (id),
    CONSTRAINT uq_probe_stalls_market_id_id UNIQUE (market_id, id)
)
"""

# Bola-jadval `financial_guards()` GACHA bo'lgan holatda yaratiladi:
# `business_date`, `CHECK`, `UNIQUE` va composite FK ni AYNAN o'sha yordamchi
# qo'shadi. Ya'ni test yordamchining hissasini alohida o'lchay oladi.
_CREATE_CHILD = """
CREATE TABLE probe_charges (
    id          uuid PRIMARY KEY DEFAULT uuidv7(),
    market_id   uuid NOT NULL,
    stall_id    uuid NOT NULL,
    created_at  timestamptz NOT NULL DEFAULT now(),
    amount_soum bigint NOT NULL
)
"""

_INSERT_PARENT = "INSERT INTO probe_stalls (market_id, id) VALUES (%s, %s)"

INSERT_CHARGE = "INSERT INTO probe_charges (market_id, stall_id, amount_soum) VALUES (%s, %s, %s)"
INSERT_CHARGE_AT = (
    "INSERT INTO probe_charges (market_id, stall_id, amount_soum, created_at) "
    "VALUES (%s, %s, %s, %s)"
)
INSERT_CHARGE_WITH_BUSINESS_DATE = (
    "INSERT INTO probe_charges (market_id, stall_id, amount_soum, business_date) "
    "VALUES (%s, %s, %s, %s)"
)
INSERT_CHARGE_IDEMPOTENT = (
    "INSERT INTO probe_charges (market_id, stall_id, amount_soum) VALUES (%s, %s, %s) "
    "ON CONFLICT (market_id, stall_id, business_date) DO NOTHING"
)

SELECT_ROWS = (
    "SELECT amount_soum, business_date FROM probe_charges "
    "WHERE market_id = %s AND stall_id = %s ORDER BY business_date"
)
SELECT_AMOUNT = "SELECT amount_soum FROM probe_charges WHERE stall_id = %s"
SELECT_DATES = "SELECT business_date, (created_at)::date FROM probe_charges WHERE stall_id = %s"


@dataclass(frozen=True)
class FinancialProbe:
    """Ikki bozor, A da uchta rasta, B da bitta — cross-tenant testi uchun."""

    conn: Connection[TupleRow]
    market_a: UUID
    market_b: UUID
    stalls_a: tuple[UUID, UUID, UUID]
    stall_b: UUID


def create_financial_probe(conn: Connection[TupleRow]) -> FinancialProbe:
    """Probe jadvallarini quradi va `financial_guards()` DDL'ini qo'llaydi."""
    drop_financial_probe(conn)

    conn.execute(_CREATE_PARENT)
    conn.execute(_CREATE_CHILD)
    for statement in financial_guard_statements(
        CHILD_TABLE,
        unique_cols=["stall_id"],
        parent=(PARENT_TABLE, "stall_id"),
    ):
        conn.execute(statement)

    market_a, market_b = uuid4(), uuid4()
    stalls_a = (uuid4(), uuid4(), uuid4())
    stall_b = uuid4()
    for stall in stalls_a:
        conn.execute(_INSERT_PARENT, (str(market_a), str(stall)))
    conn.execute(_INSERT_PARENT, (str(market_b), str(stall_b)))

    return FinancialProbe(
        conn=conn,
        market_a=market_a,
        market_b=market_b,
        stalls_a=stalls_a,
        stall_b=stall_b,
    )


def drop_financial_probe(conn: Connection[TupleRow]) -> None:
    """Probe jadvallarini FK tartibida o'chiradi."""
    for statement in _DROP_SQL:
        conn.execute(statement)
