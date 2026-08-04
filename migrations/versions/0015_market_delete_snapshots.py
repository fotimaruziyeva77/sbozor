"""market_delete_snapshots: kaskad snapshot domenini qamraydi + tik yuzasi + standart profil

Revision ID: 0015
Revises: 0014
Create Date: 2026-08-04

=============================================================================
`0012` -> `0013` JUFTLIGINING AYNAN TAKRORI (W0-6 / D-17).

`0014` beshta yangi tenant jadvalini olib keldi va
`tests/integration/test_market_delete_guard.py::
test_cascade_covers_every_table_referencing_markets` AYTGANIDEK QIZARDI —
xato xabarida beshala nom ham turdi:

    ['alert_events', 'capture_runs', 'snapshot_schedule_slots',
     'snapshot_schedules', 'snapshots']

Bu migratsiya uni qayta yashil qiladi. Uchala funksiya ham AYNI birida
almashtiriladi va bu SODDALASHTIRISH, tasodif emas: uchalasi ham bitta
domenga tegadi, ya'ni `downgrade()` bitta qaytish nuqtasini beradi.
=============================================================================

UCHTA O'ZGARISH VA HAR BIRI BOSHQA NOSOZLIKNI YOPADI:

1. `market_delete_draft()` — KASKAD. Yetim qolgan `snapshots`/`capture_runs`
   qatorlari bozor tashrifchilarining tasvirlariga havola qiladi, ya'ni
   kaskaddan tushib qolish SHAXSIY MA'LUMOTNI qoldirardi (T-04-20).
   ⚠ Snapshot bloki NVR blokidan OLDIN — sabab `functions.py` dagi
   izohda va u O'LCHANGAN (`ForeignKeyViolation`, `capture_runs` ->
   `cameras`).

2. `capture_due_markets()` — TIK YUZASI. Usiz tik hamma bozorlarni ko'ra
   olmaydi (`sbozor_app` tenant kontekstisiz BIRORTA bozorni ko'rmaydi) va
   yagona muqobil butun `markets` ni ochish bo'lardi (T-04-16).

3. `market_activate()` — STANDART PROFIL (D-01). Usiz admin jadvalni
   QO'LDA kiritishi kerak bo'lardi va self-service qoidasi buzilardi.

⚠ `capture_due_markets()` UCHUN `_regrant()` MAJBURIY: `CREATE FUNCTION`
dan keyin Postgres unga `EXECUTE TO PUBLIC` ni STANDART beradi, ya'ni
RLS'ni chetlab o'tadigan funksiyani bazadagi HAR QANDAY rol chaqira
olardi. Bu `0010`/`0011`/`0013` dagi bilan aynan bir xil naqsh.

⚠ BACKFILL QAYTARILMAYDI (`downgrade()` da). Ma'lumot o'chirish
downgrade'ning ishi EMAS: «`0014` ga qaytdim» degan da'vo SXEMAGA
tegishli, admin allaqachon tahrirlagan bo'lishi mumkin bo'lgan jadval
qatorlariga emas. Teskari yo'l `market_activate()` ning idempotentligi
bilan ham xavfsiz: qayta upgrade IKKINCHI profil yaratmaydi.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
from alembic_utils.pg_function import PGFunction

from migrations.entities.functions import (
    CAPTURE_DUE_MARKETS,
    DEFAULT_SCHEDULE_NAME,
    DEFAULT_SLOT_VALUES,
    MARKET_ACTIVATE,
    MARKET_DELETE_DRAFT,
    SNAPSHOT_GRANT_SIGNATURES,
)
from migrations.helpers import APP_ROLE, create_entity, drop_entity

# revision identifiers, used by Alembic.
revision: str = "0015"
down_revision: str | Sequence[str] | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

MARKET_DELETE_DRAFT_SIGNATURE = "market_delete_draft(uuid)"
MARKET_ACTIVATE_SIGNATURE = "market_activate(uuid)"


MARKET_DELETE_DRAFT_WITHOUT_SNAPSHOTS = PGFunction(
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
"""`0013`/`0014` davridagi `market_delete_draft()` — snapshot jadvallarisiz.

BU YERDA, MIGRATSIYANING O'ZIDA MUZLATILGANI ATAYIN va sabab
`0013_market_delete_guard.py::MARKET_DELETE_DRAFT_WITHOUT_NVR` bilan AYNAN
BIR XIL: `alembic_utils` `PGFunction` ni MODUL ta'rifidan oladi va
`migrations/entities/functions.py` endi YANGI (snapshot jadvallari bilan)
tanani saqlaydi. `drop_entity()` faqat imzo bilan ishlaydi,
`create_entity()` esa TANANI yozadi — ya'ni bu nusxa bo'lmasa
`downgrade()` yangi tanani qaytarardi va «`0014` ga qaytdim» degan da'vo
YOLG'ON bo'lardi.

Bundan tashqari bu yerda u ZARURAT: downgrade'dan keyin snapshot jadvallari
`0014` ning `downgrade()` i bilan o'chiriladi, ya'ni ularga o'chirish
qatori yozgan funksiya `relation "public.snapshots" does not exist` bilan
yiqilardi (`plpgsql` tanasi CREATE paytida tekshirilmaydi — xato faqat
CHAQIRUVDA, ya'ni eng yomon paytda chiqadi).
"""

MARKET_ACTIVATE_WITHOUT_SCHEDULE = PGFunction(
    schema="public",
    signature=MARKET_ACTIVATE.signature,
    definition="""
RETURNS void
LANGUAGE sql
SECURITY DEFINER
SET search_path = pg_catalog, public
VOLATILE
AS $$
    UPDATE public.markets
       SET is_active = true,
           updated_at = now()
     WHERE id = p_market_id
$$
""",
)
"""`0007`–`0014` davridagi `market_activate()` — standart profilsiz.

Yuqoridagi nusxa bilan bir xil sabab, LEKIN bu yerda ikkinchi, KUCHLIROQ
argument ham bor: `market_activate()` `LANGUAGE sql` va uning tanasi
`CREATE FUNCTION` paytida PARSE VA VALIDATSIYA qilinadi
(`check_function_bodies` standart `on`). Ya'ni downgrade'dan keyin, snapshot
jadvallari o'chirilgan holatda yangi tanani qayta yaratishga urinish
`relation "public.snapshot_schedules" does not exist` bilan DARHOL
yiqilardi — `plpgsql` dagidek chaqiruvgacha kutmasdan.
"""


def upgrade() -> None:
    """Upgrade schema."""
    # ------------------------------------------------------------------
    # 1. Kaskad snapshot domenini qamraydi (W0-6).
    #
    #    IMZO O'ZGARMAYDI, lekin `DROP FUNCTION` grant'ni ham olib tashlaydi
    #    va `CREATE` dan keyin Postgres `EXECUTE TO PUBLIC` ni STANDART
    #    qaytaradi — shuning uchun `REVOKE`/`GRANT` jufti QAYTA yoziladi
    #    (`0013` dagi bilan bir xil naqsh). Usiz bazadagi HAR QANDAY rol
    #    qoralama bozorni o'chira olardi.
    # ------------------------------------------------------------------
    drop_entity(MARKET_DELETE_DRAFT_WITHOUT_SNAPSHOTS)
    create_entity(MARKET_DELETE_DRAFT)
    _regrant(MARKET_DELETE_DRAFT_SIGNATURE)

    # ------------------------------------------------------------------
    # 2. Tik yuzasi (§S-3, T-04-16).
    #
    #    YANGI funksiya, ya'ni `drop_entity()` KERAK EMAS. `_regrant()` esa
    #    baribir MAJBURIY — u RLS'ni chetlab o'tadi.
    # ------------------------------------------------------------------
    create_entity(CAPTURE_DUE_MARKETS)
    for signature in SNAPSHOT_GRANT_SIGNATURES:
        _regrant(signature)

    # ------------------------------------------------------------------
    # 3. Faollashtirish standart profilni yozadi (D-01).
    # ------------------------------------------------------------------
    drop_entity(MARKET_ACTIVATE_WITHOUT_SCHEDULE)
    create_entity(MARKET_ACTIVATE)
    _regrant(MARKET_ACTIVATE_SIGNATURE)

    # ------------------------------------------------------------------
    # 4. BACKFILL — mavjud FAOL bozorlar ham jadvalga ega bo'lishi kerak.
    #
    #    Usiz D-01 faqat KELAJAKDAGI bozorlar uchun ishlardi va bugungi
    #    faol bozor (Karmana pilotining o'zi) jimgina kadrsiz qolardi:
    #    `capture_due_markets()` uni qaytarardi, materializatsiya esa 0
    #    slot topib 0 qator yozardi va hech qanday xato chiqmasdi.
    #
    #    ⚠ FUNKSIYANI QAYTA ISHLATMAYDI. `market_activate()` ni har bir
    #    bozor uchun chaqirish `markets` ga `UPDATE` ham yozardi
    #    (`is_active = true`, `updated_at = now()`) — ya'ni migratsiya
    #    allaqachon faol bozorlarning `updated_at` ini jimgina
    #    o'zgartirardi va audit jurnalida sababsiz o'zgarish paydo
    #    bo'lardi. Shuning uchun bu yerda AYNAN o'sha `INSERT` mantig'i,
    #    `UPDATE` siz takrorlanadi — va slot literallari baribir
    #    `DEFAULT_SNAPSHOT_SLOTS` dan keladi.
    #
    #    `WHERE NOT EXISTS` — idempotent: qayta upgrade ikkinchi profil
    #    yaratmaydi va `ex_snapshot_schedules_no_overlap` ni buzmaydi.
    #
    #    RLS: migratsiya `sbozor_owner` bilan ishlaydi va `0014`
    #    `owner_bootstrap` policy'sini beshala jadvalga ham qo'ygan, ya'ni
    #    `FORCE ROW LEVEL SECURITY` ostida ham yozuv o'tadi.
    # ------------------------------------------------------------------
    op.execute(f"""
        WITH created AS (
            INSERT INTO public.snapshot_schedules (market_id, name, period)
            SELECT m.id, '{DEFAULT_SCHEDULE_NAME}', daterange(current_date, NULL, '[)')
              FROM public.markets AS m
             WHERE m.is_active
               AND NOT EXISTS (
                   SELECT 1
                     FROM public.snapshot_schedules AS existing
                    WHERE existing.market_id = m.id
               )
            RETURNING market_id, id
        )
        INSERT INTO public.snapshot_schedule_slots (market_id, schedule_id, slot_time)
        SELECT created.market_id, created.id, defaults.slot_time
          FROM created
          CROSS JOIN (VALUES {DEFAULT_SLOT_VALUES}) AS defaults(slot_time)
        ON CONFLICT DO NOTHING
    """)  # noqa: S608 -- literallari modul konstantalaridan (`DEFAULT_SLOT_VALUES`,
    # `DEFAULT_SCHEDULE_NAME`), tashqi kirishdan EMAS.


def downgrade() -> None:
    """Downgrade schema."""
    # Teskari tartib: faollashtirish -> tik yuzasi -> kaskad.
    drop_entity(MARKET_ACTIVATE)
    create_entity(MARKET_ACTIVATE_WITHOUT_SCHEDULE)
    _regrant(MARKET_ACTIVATE_SIGNATURE)

    drop_entity(CAPTURE_DUE_MARKETS)

    drop_entity(MARKET_DELETE_DRAFT)
    create_entity(MARKET_DELETE_DRAFT_WITHOUT_SNAPSHOTS)
    _regrant(MARKET_DELETE_DRAFT_SIGNATURE)

    # ⚠ BACKFILL QAYTARILMAYDI — fayl boshidagi oxirgi ogohlantirish.
    #   Yozilgan profillar va slotlar JOYIDA qoladi: ular endi ma'lumot,
    #   sxema emas, va admin ularni allaqachon tahrirlagan bo'lishi mumkin.


def _regrant(signature: str) -> None:
    """`REVOKE PUBLIC` + `GRANT sbozor_app` — `0010`/`0011`/`0013` naqshi.

    `DROP FUNCTION` grant'ni ham olib tashlaydi va `CREATE FUNCTION` dan
    keyin Postgres yangi funksiyaga `EXECUTE TO PUBLIC` ni STANDART beradi.
    Usiz uchala funksiyaning ham «tor yuza» qarori jimgina bekor bo'lardi:
    ikkitasi `SECURITY DEFINER` bo'lib RLS'ni chetlab o'tadi, uchinchisi esa
    o'n yettita jadvaldan `DELETE` qiladi.

    Imzo PARAMETR (`0013` dagi modul konstantasidan farqli): bu migratsiya
    UCHTA funksiyaga tegadi va har biriga alohida yordamchi yozish uchala
    nusxani ajralib ketadigan qilardi.
    """
    op.execute(f"REVOKE ALL ON FUNCTION {signature} FROM PUBLIC")
    op.execute(f"GRANT EXECUTE ON FUNCTION {signature} TO {APP_ROLE}")
