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
    "PARENT_TABLE",
    "SELECT_ROWS",
    "FinancialProbe",
    "create_financial_probe",
    "drop_financial_probe",
]

PARENT_TABLE = "probe_stalls"
CHILD_TABLE = "probe_charges"

_DROP_SQL = (
    f"DROP TABLE IF EXISTS {CHILD_TABLE}",
    f"DROP TABLE IF EXISTS {PARENT_TABLE}",
)

# Ota-jadval: `stalls` ning minimal shakli. `UNIQUE(market_id, id)` —
# composite FK ning MAQSADI (T-01-26): usiz bola-jadval `(market_id, id)`
# juftligiga havola qila olmaydi.
_CREATE_PARENT = f"""
CREATE TABLE {PARENT_TABLE} (
    market_id uuid NOT NULL,
    id        uuid NOT NULL DEFAULT uuidv7(),
    CONSTRAINT pk_{PARENT_TABLE} PRIMARY KEY (id),
    CONSTRAINT uq_{PARENT_TABLE}_market_id_id UNIQUE (market_id, id)
)
"""

# Bola-jadval `financial_guards()` GACHA bo'lgan holatda yaratiladi:
# `business_date`, `CHECK`, `UNIQUE` va composite FK ni AYNAN o'sha yordamchi
# qo'shadi. Ya'ni test yordamchining hissasini alohida o'lchay oladi.
_CREATE_CHILD = f"""
CREATE TABLE {CHILD_TABLE} (
    id          uuid PRIMARY KEY DEFAULT uuidv7(),
    market_id   uuid NOT NULL,
    stall_id    uuid NOT NULL,
    created_at  timestamptz NOT NULL DEFAULT now(),
    amount_soum bigint NOT NULL
)
"""

_INSERT_PARENT = f"INSERT INTO {PARENT_TABLE} (market_id, id) VALUES (%s, %s)"

INSERT_CHARGE = f"INSERT INTO {CHILD_TABLE} (market_id, stall_id, amount_soum) VALUES (%s, %s, %s)"
INSERT_CHARGE_AT = (
    f"INSERT INTO {CHILD_TABLE} (market_id, stall_id, amount_soum, created_at) "
    "VALUES (%s, %s, %s, %s)"
)
INSERT_CHARGE_IDEMPOTENT = (
    f"{INSERT_CHARGE} ON CONFLICT (market_id, stall_id, business_date) DO NOTHING"
)

SELECT_ROWS = (
    f"SELECT amount_soum, business_date FROM {CHILD_TABLE} "
    "WHERE market_id = %s AND stall_id = %s ORDER BY business_date"
)


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
