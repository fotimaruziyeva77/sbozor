"""market_delete_occupancy: kaskad bandlik domenini qamraydi (uchinchi kengaytma)

Revision ID: 0019
Revises: 0018
Create Date: 2026-08-09

=============================================================================
`0012`->`0013` VA `0014`->`0015` JUFTLIKLARINING UCHINCHI TAKRORI (W0-6).

`0018` oltita yangi tenant jadvalini olib keldi va
`tests/integration/test_market_delete_guard.py::
test_cascade_covers_every_table_referencing_markets` AYTGANIDEK QIZARDI —
xato xabarida oltala nom ham turdi:

    ['audit_rounds', 'camera_zones', 'occupancy_events',
     'review_assignments', 'stall_slot_occupancy', 'zone_reviews']

Bu migratsiya uni qayta yashil qiladi va BOSHQA HECH NIMAGA TEGMAYDI:
`0015` uchta funksiyani birdan almashtirgan edi (uchalasi ham bitta
domenga tegardi), bu yerda esa AYNAN BITTA o'zgarish bor.
=============================================================================

⚠ BLOK SNAPSHOT BLOKIDAN OLDIN TURADI va bu O'LCHANGAN, taxmin emas:
`occupancy_events` `snapshots (id, is_billable)` ga kompozit FK bilan
tayanadi (D-21), `snapshots` esa snapshot blokining BIRINCHI `DELETE` i.
Blok keyinga qo'yilganda chaqiruv `ForeignKeyViolation` bilan yiqiladi —
va STATIK DARVOZA BUNI SEZMAYDI (matnda oltala jadval baribir bor).
Shuning uchun tartib `test_draft_market_deletion_covers_the_occupancy_domain`
da, funksiyani HAQIQATAN chaqirib o'lchanadi.

⚠ IKKI JADVALDA O'ZGARMASLIK TRIGGERI BOR (`occupancy_events`,
`zone_reviews`; `0018`). Ular `DELETE` ni FAQAT QORALAMA bozor uchun
o'tkazadi — `market_delete_draft()` ning `IS DISTINCT FROM false` sharti
aynan shuni kafolatlaydi, ya'ni triggergacha faqat qoralama bozor yetib
keladi. Bu `tariffs` / `stall_category_periods` bilan AYNAN bir xil naqsh
(2-fazadan beri ishlaydi) va shu sababdan `ALTER TABLE ... DISABLE
TRIGGER` ham, `session_replication_role` ham TALAB QILINMAYDI. Rad etilgan
muqobillar `migrations/entities/triggers.py` ning 0018 blokida.

⚠ `_regrant()` MAJBURIY: `DROP FUNCTION` grant'ni ham olib tashlaydi va
`CREATE` dan keyin Postgres `EXECUTE TO PUBLIC` ni STANDART qaytaradi.
Usiz bazadagi HAR QANDAY rol qoralama bozorni o'chira olardi
(`0013`/`0015` dagi bilan aynan bir xil naqsh).

⛔ `audit_log` KASKADGA QO'SHILMADI. 3-fazada o'lchangan tuzoq:
`market_id` USTUNI bo'yicha izlaydigan so'rov 13 jadval topadi, lekin
`audit_log` da `markets` ga CHET EL KALITI YO'Q — ya'ni u kaskadni
yiqitmaydi va unga qo'shilishi bozor o'chirilganda uning butun DALIL
IZINI yo'q qilardi.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
from alembic_utils.pg_function import PGFunction

from migrations.entities.functions import MARKET_DELETE_DRAFT
from migrations.helpers import APP_ROLE, create_entity, drop_entity

# revision identifiers, used by Alembic.
revision: str = "0019"
down_revision: str | Sequence[str] | None = "0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

MARKET_DELETE_DRAFT_SIGNATURE = "market_delete_draft(uuid)"


MARKET_DELETE_DRAFT_WITHOUT_OCCUPANCY = PGFunction(
    schema="public",
    signature=MARKET_DELETE_DRAFT.signature,
    definition="""
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
VOLATILE
AS $$
DECLARE
  v_is_active boolean;
BEGIN
  SELECT m.is_active INTO v_is_active
  FROM public.markets AS m
  WHERE m.id = p_market_id;

  IF v_is_active IS DISTINCT FROM false THEN
    RETURN false;
  END IF;

  DELETE FROM public.snapshots                  WHERE market_id = p_market_id;
  DELETE FROM public.capture_runs               WHERE market_id = p_market_id;
  DELETE FROM public.snapshot_schedule_slots    WHERE market_id = p_market_id;
  DELETE FROM public.snapshot_schedules         WHERE market_id = p_market_id;
  DELETE FROM public.alert_events               WHERE market_id = p_market_id;

  DELETE FROM public.cameras                    WHERE market_id = p_market_id;
  DELETE FROM public.nvr_discovery_runs         WHERE market_id = p_market_id;
  DELETE FROM public.nvr_credentials            WHERE market_id = p_market_id;
  DELETE FROM public.nvr_devices                WHERE market_id = p_market_id;

  DELETE FROM public.stall_assignments          WHERE market_id = p_market_id;
  DELETE FROM public.stall_category_periods     WHERE market_id = p_market_id;
  DELETE FROM public.tariffs                    WHERE market_id = p_market_id;
  DELETE FROM public.stall_code_registry        WHERE market_id = p_market_id;
  DELETE FROM public.stalls                     WHERE market_id = p_market_id;
  DELETE FROM public.vendors                    WHERE market_id = p_market_id;
  DELETE FROM public.zones                      WHERE market_id = p_market_id;
  DELETE FROM public.stall_categories           WHERE market_id = p_market_id;
  DELETE FROM public.market_calendar_exceptions WHERE market_id = p_market_id;
  DELETE FROM public.market_profile             WHERE market_id = p_market_id;
  DELETE FROM public.user_market_roles          WHERE market_id = p_market_id;
  DELETE FROM public.refresh_tokens             WHERE market_id = p_market_id;
  DELETE FROM public.markets                    WHERE id = p_market_id;

  RETURN true;
END $$
""",
)
"""`0015`–`0018` davridagi `market_delete_draft()` — bandlik jadvallarisiz.

BU YERDA, MIGRATSIYANING O'ZIDA MUZLATILGANI ATAYIN va sabab
`0015_market_delete_snapshots.py::MARKET_DELETE_DRAFT_WITHOUT_SNAPSHOTS`
bilan AYNAN BIR XIL: `alembic_utils` `PGFunction` ni MODUL ta'rifidan
oladi va `migrations/entities/functions.py` endi YANGI (bandlik jadvallari
bilan) tanani saqlaydi. `drop_entity()` faqat imzo bilan ishlaydi,
`create_entity()` esa TANANI yozadi — ya'ni bu nusxa bo'lmasa
`downgrade()` YANGI tanani qaytarardi va «`0018` ga qaytdim» degan da'vo
YOLG'ON bo'lardi.

Bundan tashqari bu yerda u ZARURAT: downgrade'dan keyin bandlik jadvallari
`0018` ning `downgrade()` i bilan o'chiriladi, ya'ni ularga o'chirish
qatori yozgan funksiya CHAQIRILGANDA `relation "public.camera_zones" does
not exist` bilan yiqilardi (`plpgsql` tanasi CREATE paytida tekshirilmaydi
— xato faqat CHAQIRUVDA, ya'ni eng yomon paytda chiqadi).
"""


def upgrade() -> None:
    """Upgrade schema."""
    drop_entity(MARKET_DELETE_DRAFT_WITHOUT_OCCUPANCY)
    create_entity(MARKET_DELETE_DRAFT)
    _regrant(MARKET_DELETE_DRAFT_SIGNATURE)


def downgrade() -> None:
    """Downgrade schema."""
    drop_entity(MARKET_DELETE_DRAFT)
    create_entity(MARKET_DELETE_DRAFT_WITHOUT_OCCUPANCY)
    _regrant(MARKET_DELETE_DRAFT_SIGNATURE)


def _regrant(signature: str) -> None:
    """`REVOKE PUBLIC` + `GRANT sbozor_app` — `0013`/`0015` naqshi.

    `DROP FUNCTION` grant'ni ham olib tashlaydi va `CREATE FUNCTION` dan
    keyin Postgres yangi funksiyaga `EXECUTE TO PUBLIC` ni STANDART beradi.
    Usiz funksiyaning «tor yuza» qarori jimgina bekor bo'lardi: u
    `SECURITY DEFINER` va yigirma uchta jadvaldan `DELETE` qiladi.
    """
    op.execute(f"REVOKE ALL ON FUNCTION {signature} FROM PUBLIC")
    op.execute(f"GRANT EXECUTE ON FUNCTION {signature} TO {APP_ROLE}")
