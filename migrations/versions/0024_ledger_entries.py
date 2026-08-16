"""ledger_entries: qog'oz daftar reyestri — SC#5 ning uchinchi manbasi

Revision ID: 0024
Revises: 0023
Create Date: 2026-08-16

8-FAZANING BIRINCHI MIGRATSIYASI. Bitta yangi tenant jadvalini olib keladi
VA kaskadni AYNI MIGRATSIYADA kengaytiradi — ya'ni `0012`->`0013`,
`0014`->`0015`, `0018`->`0019` va `0020`->`0021` juftliklari bu yerda
TAKRORLANMAYDI (`0023` ning qarori bilan aynan bir xil mulohaza).

⚠ NEGA JUFTLIK EMAS, NEGA BITTA MIGRATSIYA: to'rt marta takrorlangan
naqshda ikkinchi migratsiya faqat `market_delete_draft()` tanasini
almashtirardi va oradagi holatda `test_cascade_covers_every_table_
referencing_markets` ATAYIN QIZIL turardi. Bu migratsiya ikkala qadamni
ham o'z oynasida bajaradi, ya'ni darvoza HECH QACHON qizil bo'lmaydi.

=============================================================================
BU MIGRATSIYADA QOTIB QOLADIGAN UCH QAROR (`sbozor_core.models.ledger`
modulining docstringi bilan BIR MANBA — u yerda batafsil):

1. ⛔⛔ `ledger_entries` MOLIYAVIY JADVAL EMAS — U TASHQI QOG'OZ MANBANING
   NUSXASI. Shuning uchun `financial_guards()` CHAQIRILMAYDI va nom
   `schema_contract.FINANCIAL_TABLES` ga QO'SHILMAYDI.

   Sabab MEXANIK: `financial_guards()` `CHECK (amount_soum > 0)` ni
   majburlaydi, daftar esa `0` summani ham yozishi mumkin va bu QONUNIY
   holat — «bu rastadan bugun hech nima yig'ilmadi» degan yozuv AYNAN
   nomuvofiqlikning dalili va u solishtiruvdan CHIQARIB TASHLANMASLIGI
   kerak.

   ⚠ BU IZOHSIZ KEYINGI IJROCHI UNI REYESTRGA QO'SHISHGA URINARDI:
   jadvalda `amount_soum` NOMLI ustun BOR, ya'ni u `cashier_shifts` /
   `billing_anomalies` dan FARQLI o'laroq `test_financial_tables_have_
   guards` ning regeksini qanoatlantirardi — «soxta pul ustuni» tuzog'i
   bu yerda ISHLAMAYDI va aynan shuning uchun sabab OCHIQ yozilishi
   shart.

2. ⛔ `ON CONFLICT DO UPDATE`, `DO NOTHING` EMAS — daftar KUN ICHIDA
   tuzatiladi va ikkinchi fayl birinchisini ALMASHTIRADI. Bu
   `daily_charges` ning o'zgarmaslik qoidasini BUZMAYDI (1-band: bu
   jadval hisob emas). Idempotentlikning O'ZI esa DB KAFOLATI:
   `UNIQUE (market_id, business_date, stall_id)` — ilova intizomi emas,
   chunki «avval tekshir, keyin yoz» ikki parallel import yugurishida
   IKKITA qator yozardi (D-21).

3. ⛔ YANGI `SECURITY DEFINER` FUNKSIYA QO'SHILMAYDI (D-21, T-06-22 /
   G7-7). Bu migratsiya DEFINER yuzasini KENGAYTIRMAYDI:
   `market_delete_draft(uuid)` ning faqat TANASI kengayadi, IMZOSI
   o'zgarmaydi va yangi funksiya umuman tug'ilmaydi.
   `tests/tenancy/test_occupancy_domain_meta.py::DEFINER_SURFACES` BO'SH
   qolishi SHART (`0023:65-69` bandining so'zma-so'z takrori).
=============================================================================

⚠ `business_date` USTUNI BOR, LEKIN U `FINANCIAL_TABLES` NING TALABI
EMAS va GENERATED ham EMAS. U DOMEN sanasi — daftar QAYSI KUNGA
yozilgan. `created_at` dan hosila qilish import kechikib ertasi kuni
bajarilganda qatorni NOTO'G'RI kunga tushirardi
(`daily_charges.service_date` bilan aynan bir xil ajratma, C-2).

⚠ KOMPOZIT FK NISHONI (`stalls (market_id, id)`) ALLAQACHON MAVJUD —
`uq_stalls_market_id_id` (2-faza), ya'ni bu migratsiya uni YARATMAYDI.
`0020` ning `stall_slot_occupancy` holati (OP-11, `InvalidForeignKeyError`)
bu yerda TAKRORLANMAYDI.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

import sqlalchemy as sa
from alembic import op
from alembic_utils.pg_function import PGFunction
from sbozor_core.models.ledger import LEDGER_DAY_STALL_UNIQUE
from sqlalchemy.dialects import postgresql as pg

from migrations.entities import (
    LEDGER_AUDITED_TABLES,
    LEDGER_DELETE_ORDER,
    LEDGER_TENANT_TABLES,
)
from migrations.entities.functions import MARKET_DELETE_DRAFT
from migrations.entities.policies import owner_bootstrap_policy, tenant_policy
from migrations.helpers import (
    APP_ROLE,
    attach_audit_trigger,
    create_entity,
    detach_audit_trigger,
    drop_entity,
    enable_tenant_rls,
)

# revision identifiers, used by Alembic.
revision: str = "0024"
down_revision: str | Sequence[str] | None = "0023"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# ⚠ UNIQUE CHEKLOVNING NOMI SHU YERDA E'LON QILINMAYDI — u
#   `sbozor_core.models.ledger` dan IMPORT qilinadi (yuqoriga qarang).
#
#   Sabab `0023` da O'LCHANGAN (OP-10): autogenerate model metadata'sini
#   baza bilan solishtiradi, ya'ni nom ikki joyda literal yozilsa ular
#   ajralib ketishi mumkin va `downgrade()` boshqa nomni qidirardi.

MARKET_DELETE_DRAFT_SIGNATURE = "market_delete_draft(uuid)"


def _uuid_pk() -> sa.Column[UUID]:
    """PG18 native `uuidv7()` — vaqt-tartiblangan, B-tree do'st."""
    return sa.Column(
        "id",
        pg.UUID(as_uuid=True),
        server_default=sa.text("uuidv7()"),
        nullable=False,
    )


def _market_id() -> sa.Column[UUID]:
    """Tenant kaliti — HAR BIR jadvalda birinchi ustun."""
    return sa.Column("market_id", pg.UUID(as_uuid=True), nullable=False)


def _created_at() -> sa.Column[datetime]:
    return sa.Column(
        "created_at",
        sa.DateTime(timezone=True),
        server_default=sa.text("now()"),
        nullable=False,
    )


def _updated_at() -> sa.Column[datetime]:
    """`updated_at` — bu jadvalda MA'NOLI va u ATAYIN bor.

    Daftar qatori QONUNIY ravishda almashtiriladi (`ON CONFLICT DO UPDATE`,
    fayl boshidagi 2-band), ya'ni «bu qatorni tahrirlash mumkin» degan
    VA'DA bu yerda ROST. `models/billing.py` ning oltala jadvalida u
    ATAYIN yo'q edi — o'sha yerda qatorlar o'zgarmas.
    """
    return sa.Column(
        "updated_at",
        sa.DateTime(timezone=True),
        server_default=sa.text("now()"),
        nullable=False,
    )


def _regrant(signature: str) -> None:
    """`REVOKE PUBLIC` + `GRANT sbozor_app` — `0013`/`0015`/`0019`/`0021`/`0023` naqshi.

    `DROP FUNCTION` grant'ni ham olib tashlaydi va `CREATE FUNCTION` dan
    keyin Postgres yangi funksiyaga `EXECUTE TO PUBLIC` ni STANDART beradi.
    Usiz funksiyaning «tor yuza» qarori jimgina bekor bo'lardi: u
    `SECURITY DEFINER` va endi O'TTIZ BESHTA jadvaldan `DELETE` qiladi.
    """
    op.execute(f"REVOKE ALL ON FUNCTION {signature} FROM PUBLIC")
    op.execute(f"GRANT EXECUTE ON FUNCTION {signature} TO {APP_ROLE}")


MARKET_DELETE_DRAFT_WITHOUT_LEDGER = PGFunction(
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

  DELETE FROM public.reconciliation_case_events   WHERE market_id = p_market_id;
  DELETE FROM public.reconciliation_cases         WHERE market_id = p_market_id;
  DELETE FROM public.notification_outbox          WHERE market_id = p_market_id;
  DELETE FROM public.vendor_telegram_bindings     WHERE market_id = p_market_id;
  DELETE FROM public.market_notification_settings WHERE market_id = p_market_id;

  DELETE FROM public.charge_evidence            WHERE market_id = p_market_id;
  DELETE FROM public.charge_adjustments         WHERE market_id = p_market_id;
  DELETE FROM public.payments                   WHERE market_id = p_market_id;
  DELETE FROM public.billing_anomalies          WHERE market_id = p_market_id;
  DELETE FROM public.daily_charges              WHERE market_id = p_market_id;
  DELETE FROM public.cashier_shifts             WHERE market_id = p_market_id;

  DELETE FROM public.stall_slot_occupancy      WHERE market_id = p_market_id;
  DELETE FROM public.zone_reviews              WHERE market_id = p_market_id;
  DELETE FROM public.review_assignments        WHERE market_id = p_market_id;
  DELETE FROM public.audit_rounds              WHERE market_id = p_market_id;
  DELETE FROM public.occupancy_events          WHERE market_id = p_market_id;
  DELETE FROM public.camera_zones              WHERE market_id = p_market_id;

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
"""`0023`–`0024` davridagi `market_delete_draft()` — daftar reyestrisiz.

BU YERDA, MIGRATSIYANING O'ZIDA MUZLATILGANI ATAYIN va sabab
`0023_notification_domain.py::MARKET_DELETE_DRAFT_WITHOUT_NOTIFICATIONS`
bilan AYNAN BIR XIL: `alembic_utils` `PGFunction` ni MODUL ta'rifidan
oladi va `migrations/entities/functions.py` endi YANGI (daftar bloki
bilan) tanani saqlaydi. `drop_entity()` faqat imzo bilan ishlaydi,
`create_entity()` esa TANANI yozadi — ya'ni bu nusxa bo'lmasa
`downgrade()` YANGI tanani qaytarardi va «`0023` ga qaytdim» degan da'vo
YOLG'ON bo'lardi.

Bundan tashqari bu yerda u ZARURAT: downgrade'dan keyin `ledger_entries`
shu migratsiyaning `downgrade()` i bilan o'chiriladi, ya'ni unga
o'chirish qatori yozgan funksiya CHAQIRILGANDA `relation
"public.ledger_entries" does not exist` bilan yiqilardi (`plpgsql` tanasi
CREATE paytida tekshirilmaydi — xato faqat CHAQIRUVDA, ya'ni eng yomon
paytda chiqadi).
"""


def upgrade() -> None:
    """Upgrade schema."""
    # ------------------------------------------------------------------
    # 1. ledger_entries — qog'oz daftar yozuvi (RECON-04, D-17/D-21/R-4).
    #
    #    ⛔ `financial_guards()` CHAQIRILMAYDI — fayl boshidagi 1-band.
    #    ⛔ `business_date` GENERATED EMAS, DOMEN ustuni — fayl boshidagi
    #       ogohlantirish.
    # ------------------------------------------------------------------
    op.create_table(
        "ledger_entries",
        _market_id(),
        _uuid_pk(),
        # DOMEN sanasi — daftar QAYSI KUNGA yozilgan.
        sa.Column("business_date", sa.Date(), nullable=False),
        sa.Column("stall_id", pg.UUID(as_uuid=True), nullable=False),
        # ⚠ `BIGINT` so'm ↔ `int`. ⛔ `CHECK (> 0)` ATAYIN YO'Q: `0`
        #   QONUNIY qiymat va u SC#5 ning eng muhim holati.
        sa.Column("amount_soum", sa.BigInteger(), nullable=False),
        # ⛔ `users` GA FK YO'Q: `users` GLOBAL jadval va unga kompozit
        #   tenant FK yozib bo'lmaydi; yagona ustunli FK esa begona bozor
        #   xodimini biriktirishni to'xtata olmasdi — ya'ni u kafolat emas,
        #   kafolat KO'RINISHI bo'lardi. Tekshiruv ilova qatlamida
        #   (`reconciliation_cases.assignee_user_id` bilan aynan bir xil
        #   qaror).
        sa.Column("imported_by", pg.UUID(as_uuid=True), nullable=False),
        _created_at(),
        _updated_at(),
        sa.PrimaryKeyConstraint("id", name="pk_ledger_entries"),
        sa.ForeignKeyConstraint(
            ["market_id"], ["markets.id"], name="fk_ledger_entries_market_id_markets"
        ),
        # ⛔ KOMPOZIT — `market_id` BILAN: A bozorining daftar qatori B
        #   bozorining rastasiga havola qila OLMAYDI (T-08-04). Bu RLS
        #   emas, SXEMA darajasidagi kafolat va u kontekst o'rnatilmay
        #   qolgan holatda ham kuchda qoladi.
        #
        # ⛔ `ondelete` YO'Q (NO ACTION): daftar qatori bor rastani
        #   o'chirish RAD ETILADI. Aynan shu sababdan kaskaddagi daftar
        #   bloki `stalls` dan OLDIN turadi.
        sa.ForeignKeyConstraint(
            ["market_id", "stall_id"],
            ["stalls.market_id", "stalls.id"],
            name="fk_ledger_entries_stall",
        ),
        # KOMPOZIT FK NISHONI — keyingi fazalar uchun (`0023` naqshi).
        sa.UniqueConstraint("market_id", "id", name="uq_ledger_entries_market_id_id"),
        # ⛔⛔ TAKRORIY IMPORTNI IDEMPOTENT QILADIGAN KAFOLAT — fayl
        #    boshidagi 2-band. ILOVA INTIZOMI EMAS.
        sa.UniqueConstraint("market_id", "business_date", "stall_id", name=LEDGER_DAY_STALL_UNIQUE),
    )

    # ------------------------------------------------------------------
    # 2. RLS. TARTIB MAJBURIY: ENABLE + FORCE + GRANT -> policy (Pitfall 10).
    #    `alembic-utils` `ENABLE`/`FORCE` ni BILMAYDI — ularsiz policy HECH
    #    QANDAY ta'sir ko'rsatmaydi va jadval hamma uchun ochiq bo'ladi.
    # ------------------------------------------------------------------
    for table in LEDGER_TENANT_TABLES:
        enable_tenant_rls(table)
        create_entity(tenant_policy(table))
        create_entity(owner_bootstrap_policy(table))

    # ------------------------------------------------------------------
    # 3. Audit (C-10) — daftar KIM tomonidan almashtirilgani auditda
    #    ko'rinishi SHART.
    #
    #    ⚠ NOM `schema_contract.AUDITED_TABLES` GA SHU MIGRATSIYA BILAN
    #      BIR COMMITDA qo'shildi (`06-04` OP-4 naqshi), ya'ni
    #      `PENDING_AUDIT_TRIGGERS` BO'SH qoladi va
    #      `test_audited_tables_have_trigger` UZLUKSIZ yashil turadi.
    # ------------------------------------------------------------------
    for table in LEDGER_AUDITED_TABLES:
        attach_audit_trigger(table)

    # ------------------------------------------------------------------
    # 4. KASKAD KENGAYTMASI (`0021`/`0023` naqshi).
    #
    #    ⛔ YANGI `SECURITY DEFINER` FUNKSIYA QO'SHILMAYDI (T-06-22/G7-7):
    #    mavjud funksiyaning faqat TANASI kengayadi, IMZOSI o'zgarmaydi.
    #    `DEFINER_SURFACES` BO'SH qoladi.
    #
    #    ⚠ BLOK KASKADNING ENG BOSHIGA QO'YILADI va sabab
    #    `LEDGER_DELETE_ORDER` docstringida: `ledger_entries` `stalls` ga
    #    tayanadi, ya'ni u `stalls` dan OLDIN o'chirilishi SHART.
    # ------------------------------------------------------------------
    drop_entity(MARKET_DELETE_DRAFT_WITHOUT_LEDGER)
    create_entity(MARKET_DELETE_DRAFT)
    _regrant(MARKET_DELETE_DRAFT_SIGNATURE)


def downgrade() -> None:
    """Downgrade schema."""
    # KASKAD AVVAL QAYTARILADI: jadval o'chirilgandan keyin funksiya tanasi
    # mavjud bo'lmagan jadvalga havola qilib qolardi va CHAQIRUVDA
    # yiqilardi (`plpgsql` tanasi CREATE paytida tekshirilmaydi).
    drop_entity(MARKET_DELETE_DRAFT)
    create_entity(MARKET_DELETE_DRAFT_WITHOUT_LEDGER)
    _regrant(MARKET_DELETE_DRAFT_SIGNATURE)

    for table in reversed(LEDGER_AUDITED_TABLES):
        detach_audit_trigger(table)

    for table in reversed(LEDGER_TENANT_TABLES):
        drop_entity(owner_bootstrap_policy(table))
        drop_entity(tenant_policy(table))

    # TARTIB — `LEDGER_DELETE_ORDER` bo'yicha, ya'ni FK zanjirida
    # BOLALARDAN ota-onaga. Ro'yxat `reversed(LEDGER_TENANT_TABLES)` dan
    # HOSIL QILINMAYDI va sabab reyestrning o'z docstringida.
    for table in LEDGER_DELETE_ORDER:
        op.drop_table(table)
