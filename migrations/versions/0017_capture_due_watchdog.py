"""capture_due_watchdog: ijarasi tugagan `running` qatorli bozor ham tikda ko'rinadi

Revision ID: 0017
Revises: 0016
Create Date: 2026-08-04

=============================================================================
O'LCHANGAN NOSOZLIK: IJARA MEXANIZMI AYNAN O'ZI QOPLASHI KERAK BO'LGAN
HOLATDA ISHLAMASDI.

`0015` ning `capture_due_markets()` i ikki shart bilan qurilgan edi:
muddati kelgan `pending` qator BOR, yoki bugungi reja HALI yo'q. Uchinchi
holat — «reja bor, `pending` qator yo'q, lekin ijarasi tugagan `running`
qator bor» — ikkalasiga ham tushmaydi.

Bu 04-07 ning `test_expired_lease_returns_to_pending` testida O'LCHANDI:

    tik natijasi -> TickResult(markets=1, created=0, released=0, ...)

ya'ni fixture bozori funksiyadan UMUMAN chiqmadi va `release_expired()`
chaqirilmadi. Ketma-ketlik ishlab chiqarishda shunday ko'rinardi:

    06:00 worker batch o'rtasida o'ldi   -> 25 qator `running`
    06:01 tik -> bozor ko'rinmaydi       -> ijara tekshirilmaydi
    ...
    06:30 tik -> bozor qaytadi           -> qatorlar bo'shatiladi, LEKIN
                                            grace (600 s) o'tgan -> `missed`

Qayta urinish uchun berilgan 9 daqiqa JIMGINA yo'qolardi: xato yo'q,
jurnal yozuvi yo'q, alert esa faqat kun oxirida. CAM-05 ning «kadr olish
uzilsa urinish QAYTA BAJARILADI» talabi bajarilmasdi.
=============================================================================

TUZATISH: uchinchi disjunkt — ijarasi TUGAGAN `running` qatori bor bozor.

Shart ATAYIN tor (`locked_until IS NULL OR locked_until <= now()`): har
qanday `running` qator bo'yicha filtrlash normal kadr olish davomida
BARCHA bozorlarni qaytarib, ikkinchi shartning («muddati kelmagan slot —
ish emas», `0015` da alohida test bilan qulflangan) ma'nosini yo'qotardi.

⚠ IMZO O'ZGARMAYDI, ya'ni chaqiruvchi kod ham, `SNAPSHOT_GRANT_SIGNATURES`
ham tegilmaydi. Lekin `DROP FUNCTION` grant'ni ham olib tashlaydi va
`CREATE` dan keyin Postgres `EXECUTE TO PUBLIC` ni STANDART qaytaradi —
shuning uchun `REVOKE`/`GRANT` jufti QAYTA yoziladi (`0013`/`0015` dagi
bilan aynan bir xil naqsh). Usiz bazadagi HAR QANDAY rol RLS'ni chetlab
o'tadigan funksiyani chaqira olardi.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
from alembic_utils.pg_function import PGFunction

from migrations.entities.functions import CAPTURE_DUE_MARKETS, SNAPSHOT_GRANT_SIGNATURES
from migrations.helpers import APP_ROLE, create_entity, drop_entity

revision: str = "0017"
down_revision: str | Sequence[str] | None = "0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


CAPTURE_DUE_MARKETS_WITHOUT_WATCHDOG = PGFunction(
    schema="public",
    signature=CAPTURE_DUE_MARKETS.signature,
    definition="""
RETURNS TABLE (market_id uuid, due_count integer)
LANGUAGE sql
SECURITY DEFINER
SET search_path = pg_catalog, public
STABLE
AS $$
    SELECT m.id,
           COALESCE(due.total, 0)::integer
      FROM public.markets AS m
      LEFT JOIN LATERAL (
          SELECT count(*)::integer AS total
            FROM public.capture_runs AS r
           WHERE r.market_id = m.id
             AND r.status = 'pending'
             AND r.scheduled_at <= now()
      ) AS due ON true
     WHERE m.is_active
       AND (
           COALESCE(due.total, 0) > 0
           OR NOT EXISTS (
               SELECT 1
                 FROM public.capture_runs AS planned
                WHERE planned.market_id = m.id
                  AND planned.business_date = ((now() AT TIME ZONE 'Asia/Tashkent')::date)
           )
       )
$$
""",
)
"""`0015` davridagi tana — MIGRATSIYANING O'ZIDA MUZLATILGAN.

`0013`/`0015` dagi bilan aynan bir xil sabab: `alembic_utils` `PGFunction`
ni MODUL ta'rifidan oladi va `migrations/entities/functions.py` endi YANGI
tanani saqlaydi. `drop_entity()` faqat imzo bilan ishlaydi,
`create_entity()` esa TANANI yozadi — ya'ni bu nusxa bo'lmasa
`downgrade()` yangi tanani qaytarardi va «`0016` ga qaytdim» degan da'vo
YOLG'ON bo'lardi.
"""


def _regrant(signature: str) -> None:
    """`REVOKE ALL ... FROM PUBLIC` + `GRANT EXECUTE TO sbozor_app`."""
    op.execute(f"REVOKE ALL ON FUNCTION public.{signature} FROM PUBLIC")
    op.execute(f"GRANT EXECUTE ON FUNCTION public.{signature} TO {APP_ROLE}")


def upgrade() -> None:
    drop_entity(CAPTURE_DUE_MARKETS_WITHOUT_WATCHDOG)
    create_entity(CAPTURE_DUE_MARKETS)
    for signature in SNAPSHOT_GRANT_SIGNATURES:
        _regrant(signature)


def downgrade() -> None:
    drop_entity(CAPTURE_DUE_MARKETS)
    create_entity(CAPTURE_DUE_MARKETS_WITHOUT_WATCHDOG)
    for signature in SNAPSHOT_GRANT_SIGNATURES:
        _regrant(signature)
