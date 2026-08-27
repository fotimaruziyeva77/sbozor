"""Composite FK — cross-tenant havolaning STRUKTURAVIY imkonsizligi (T-01-26).

RLS "kim nimani ko'radi" savolini hal qiladi, lekin "A bozori qatori B
bozori qatoriga havola qila oladimi" savolini hal QILMAYDI. Ikkinchisi
sxema darajasidagi masala va u faqat composite kalit bilan yopiladi:

    UNIQUE (market_id, id)                       <- ota-jadvalda
    FOREIGN KEY (market_id, parent_id)           <- bola-jadvalda
        REFERENCES parent (market_id, id)

Bunda bola qatorining `market_id` si ota qatorining `market_id` si bilan
mos kelishi SHART — aks holda juftlik umuman mavjud emas va FK yiqiladi.
`market_id` ni bolaga takrorlash ortiqcha ko'rinadi, aslida u aynan shu
tekshiruvni mumkin qiladi.

1-fazada bunday bola-jadval hali yo'q (ular 2- va 6-fazalarda tug'iladi),
shuning uchun test uni O'ZI yaratadi: shu bilan `UNIQUE(market_id, id)`
konstraytining kelajakdagi maqsadi HOZIRDAN isbotlanadi va u tasodifan
o'chirilsa test yiqiladi.

DDL `sbozor_owner` bilan bajariladi (`sbozor_app` `public` sxemada obyekt
yarata olmaydi — T-01-06).
"""

from __future__ import annotations

from collections.abc import Iterator

import psycopg
import pytest
from fixtures.two_markets import TwoMarketSeed
from psycopg import Connection
from psycopg.rows import TupleRow

pytestmark = pytest.mark.tenancy

# Jadval nomi SQL matnlarida LITERAL yozilgan (o'zgaruvchi bilan
# birlashtirilmagan): bu yerda dinamiklikka ehtiyoj yo'q va literal shakl
# testni o'qishni osonlashtiradi.
DROP_CHILD = "DROP TABLE IF EXISTS t_composite_fk_probe"

CREATE_CHILD = """
CREATE TABLE t_composite_fk_probe (
    market_id     uuid NOT NULL,
    id            uuid PRIMARY KEY DEFAULT uuidv7(),
    membership_id uuid NOT NULL,
    CONSTRAINT fk_probe_membership
        FOREIGN KEY (market_id, membership_id)
        REFERENCES user_market_roles (market_id, id)
)
"""

INSERT_CHILD = "INSERT INTO t_composite_fk_probe (market_id, membership_id) VALUES (%s, %s)"
COUNT_CHILD = "SELECT count(*) FROM t_composite_fk_probe"


@pytest.fixture
def child_table(
    sync_owner_conn: Connection[TupleRow],
    migrated: None,
    two_markets: TwoMarketSeed,
) -> Iterator[Connection[TupleRow]]:
    """Composite FK bilan vaqtinchalik bola-jadval.

    `two_markets` ATAYIN shu yerda so'raladi (test signaturasida ham
    bo'lsa-da): pytest fixture'larni teskari tartibda yopadi, ya'ni seed
    AVVAL qurilib, bola-jadval KEYIN qurilishi kerak — aks holda seed
    tozalanayotganda hali havola qilib turgan probe jadvali `DELETE` ni
    FK buzilishi bilan yiqitadi.
    """
    sync_owner_conn.execute(DROP_CHILD)
    sync_owner_conn.execute(CREATE_CHILD)
    try:
        yield sync_owner_conn
    finally:
        sync_owner_conn.execute(DROP_CHILD)


def test_same_tenant_reference_is_accepted(
    child_table: Connection[TupleRow], two_markets: TwoMarketSeed
) -> None:
    """NAZORAT HOLATI: to'g'ri juftlik qabul qilinadi.

    Bu test busiz keyingi test yolg'on-yashil bo'lardi — FK hamma narsani
    rad etayotgan bo'lsa ham "cross-tenant bloklandi" deb ko'rinardi.
    """
    child_table.execute(
        INSERT_CHILD,
        (str(two_markets.market_a.id), str(two_markets.market_a.admin_role_id)),
    )
    row = child_table.execute(COUNT_CHILD).fetchone()
    assert row is not None
    assert row[0] == 1


def test_cross_tenant_reference_is_rejected(
    child_table: Connection[TupleRow], two_markets: TwoMarketSeed
) -> None:
    """B bozori qatori A bozorining a'zoligiga havola qila OLMAYDI."""
    with pytest.raises(psycopg.errors.ForeignKeyViolation) as excinfo:
        child_table.execute(
            INSERT_CHILD,
            # market_id = B, lekin a'zolik A bozoriniki -> (B, A_id) juftligi yo'q.
            (str(two_markets.market_b.id), str(two_markets.market_a.admin_role_id)),
        )

    assert "fk_probe_membership" in str(excinfo.value)


def test_composite_unique_constraints_exist(
    sync_app_conn: Connection[TupleRow], migrated: None
) -> None:
    """`UNIQUE(market_id, id)` har bir tenant jadvalda bor.

    Bu — yuqoridagi FK ning MAQSADI: konstrayt bo'lmasa keyingi fazalar
    composite FK yoza olmaydi va cross-tenant havola faqat ilova
    intizomiga tayanib qoladi.
    """
    rows = sync_app_conn.execute(
        "SELECT c.conrelid::regclass::text, c.conname "
        "FROM pg_constraint c "
        "WHERE c.contype = 'u' "
        "AND c.connamespace = 'public'::regnamespace "
        "AND (SELECT array_agg(a.attname ORDER BY a.attname) "
        "     FROM unnest(c.conkey) k JOIN pg_attribute a "
        "       ON a.attrelid = c.conrelid AND a.attnum = k) = ARRAY['id','market_id']::name[]"
    ).fetchall()

    tables = {row[0] for row in rows}
    assert {"user_market_roles", "refresh_tokens"} <= tables, (
        f"`UNIQUE(market_id, id)` yo'q jadval(lar) bor — topilgani: {sorted(tables)}"
    )
