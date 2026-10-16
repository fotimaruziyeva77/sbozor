"""Smena deklaratsiyasining TUZATISHI — append-only qator

Revision ID: 0030
Revises: 0029
Create Date: 2026-10-16

=============================================================================
⛔⛔ NEGA BU MIGRATSIYA BOR (261016, buyurtmachi qarori).

16-oktabrda kassir smenani 1 318 000 bilan yopdi, tizimda esa 1 289 000
bor edi; rahbariyat «kassir xato kiritgan» dedi va deklaratsiyani
tuzatishni talab qildi. Yopilgan smena (D-25) `shift_declaration_
immutable()` bilan QULFLANGAN va u QULFLANGANICHA QOLADI — qulfni
chetlab o'tish kassirning asl sonini IZSIZ o'chirardi.

Yechim — `charge_adjustments` / storno bilan AYNI naqsh: tuzatish YANGI
QATOR. Kassirning soni joyida, tuzatish alohida, «kim,
qachon, nega» esa audit jurnalida. Smena hisobotidagi amaldagi
deklaratsiya — smenaning ENG OXIRGI tuzatishi (bo'lmasa kassirning soni).

-----------------------------------------------------------------------------
⛔ `financial_guards()` CHAQIRILMAYDI va jadval `FINANCIAL_TABLES` da EMAS:
   u pul HARAKATI emas (patta ham, to'lov ham emas), sanalgan naqd
   haqidagi TUZATILGAN DA'VO. `declared_soum >= 0` — `cashier_shifts`
   bilan bir xil sabab (butun smena terminal orqali o'tgan kun real).

⛔ YANGI `SECURITY DEFINER` FUNKSIYA QO'SHILMAYDI: `market_delete_draft()`
   ning faqat TANASI kengayadi (`0027` naqshi).
=============================================================================
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from alembic_utils.pg_function import PGFunction
from sbozor_core.models.billing import (
    BILLING_BUSINESS_DATE_EXPR,
    SHIFT_CORRECTION_INDEX,
    SHIFT_CORRECTION_REASON_CHECK,
)
from sqlalchemy.dialects import postgresql as pg

from migrations.entities import (
    SHIFT_CORRECTION_AUDITED_TABLES,
    SHIFT_CORRECTION_TENANT_TABLES,
)
from migrations.entities.functions import MARKET_DELETE_DRAFT
from migrations.entities.policies import owner_bootstrap_policy, tenant_policy
from migrations.entities.triggers import SHIFT_CORRECTION_IMMUTABLE
from migrations.helpers import (
    attach_audit_trigger,
    attach_immutability_trigger,
    create_entity,
    detach_audit_trigger,
    detach_immutability_trigger,
    drop_entity,
    enable_tenant_rls,
    grant_app_dml,
    replace_entity,
)

# revision identifiers, used by Alembic.
revision: str = "0030"
down_revision: str | Sequence[str] | None = "0029"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE = "shift_declaration_corrections"

SHIFT_CORRECTION_IMMUTABLE_TRIGGER = "trg_shift_correction_immutable"
"""Trigger nomi — `attach_immutability_trigger()` hosila nom yasamaydi."""

MARKET_DELETE_DRAFT_WITHOUT_CORRECTIONS = PGFunction(
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

  -- 8-faza qog'oz daftar reyestri (0024_ledger_entries). BLOK ENG BOSHDA
  -- va bu ENG XAVFSIZ o'rin: `ledger_entries` ga HECH KIM tayanmaydi
  -- (unga kompozit FK bilan keladigan bola yo'q), ya'ni uni birinchi
  -- o'chirish birorta FK ni buzmaydi.
  --
  -- ⛔ BLOK `stalls` O'CHIRILISHIDAN OLDIN TURISHI SHART: `ledger_entries`
  -- unga kompozit FK `(market_id, stall_id)` bilan tayanadi (`ondelete`
  -- YO'Q, ya'ni NO ACTION), `stalls` esa 2-faza blokining ichida —
  -- kaskadning ANCHA PASTIDA. Blok keyinga qo'yilganda chaqiruv
  -- `ForeignKeyViolation: update or delete on table "stalls" violates
  -- foreign key constraint "fk_ledger_entries_stall"` bilan yiqilardi va
  -- STATIK DARVOZA BUNI SEZMASDI (matnda jadval baribir bor) —
  -- `0013`/`0015`/`0019`/`0021`/`0023` juftliklarining OLTINCHI takrori.
  --
  -- ⚠ JADVALDA O'ZGARMASLIK QO'RIQCHISI YO'Q va shuning uchun bu blok
  --   yuqoridagi `IS DISTINCT FROM false` shartiga TEXNIK jihatdan
  --   bog'liq emas: daftar qatori qonuniy ravishda ALMASHTIRILADI
  --   (`ON CONFLICT DO UPDATE`, D-21). Shart baribir kuchda — u butun
  --   funksiyaning kirish darvozasi.
  DELETE FROM public.ledger_entries               WHERE market_id = p_market_id;

  -- 7-faza bildirishnoma domeni (0023_notification_domain). BLOK BILLING
  -- BLOKIDAN OLDIN TURISHI SHART va bu O'LCHANGAN, taxmin emas:
  -- `reconciliation_cases` IKKI MUSTAQIL kompozit FK bilan
  -- `billing_anomalies` VA `daily_charges` ga tayanadi (DQ-5), ikkalasi
  -- ham pastdagi billing blokining ichida. Blok keyinga qo'yilganda
  -- chaqiruv `ForeignKeyViolation: update or delete on table
  -- "billing_anomalies" violates foreign key constraint
  -- "fk_reconciliation_cases_anomaly"` bilan yiqiladi — va STATIK DARVOZA
  -- BUNI SEZMAYDI (matnda beshala jadval baribir bor). Bu
  -- `0013`/`0015`/`0019`/`0021` juftliklarining BESHINCHI takrori.
  --
  -- Ichki tartib `NOTIFICATION_DELETE_ORDER` dan:
  -- `reconciliation_case_events` -> `reconciliation_cases` ->
  -- `notification_outbox` -> `vendor_telegram_bindings` ->
  -- `market_notification_settings`. Oxirgi uchtasi FK zanjiridan CHETDA
  -- (ularga hech kim tayanmaydi), ya'ni ularning o'zaro tartibi ixtiyoriy
  -- — `alert_events` bilan aynan bir xil holat.
  --
  -- ⚠ `reconciliation_case_events` USTIDA O'ZGARMASLIK TRIGGERI BOR
  --   (`case_event_immutable()`, 0023) va u `DELETE` ni FAQAT QORALAMA
  --   bozor uchun o'tkazadi. Yuqoridagi `IS DISTINCT FROM false` sharti
  --   aynan shu holatni kafolatlaydi, ya'ni bu yerga faqat qoralama bozor
  --   yetib keladi. `occupancy_events` / `daily_charges` bilan AYNAN bir
  --   xil naqsh.
  DELETE FROM public.reconciliation_case_events   WHERE market_id = p_market_id;
  DELETE FROM public.reconciliation_cases         WHERE market_id = p_market_id;
  DELETE FROM public.notification_outbox          WHERE market_id = p_market_id;
  DELETE FROM public.vendor_telegram_bindings     WHERE market_id = p_market_id;
  DELETE FROM public.market_notification_settings WHERE market_id = p_market_id;

  -- 6-faza billing domeni (0020_billing_domain). BLOK BANDLIK VA SNAPSHOT
  -- BLOKLARIDAN OLDIN TURISHI SHART va bu O'LCHANGAN, taxmin emas:
  -- `charge_evidence` UCHTA quyi jadvalga birdan tayanadi —
  -- `stall_slot_occupancy` (audit havolasi), `occupancy_events`
  -- (muzlatilgan dalil) va `snapshots` (kadrga yo'l); `billing_anomalies`
  -- esa `occupancy_events` va `snapshots` ga. Ular pastdagi ikki blokning
  -- BIRINCHI `DELETE` lari, ya'ni blok keyinga qo'yilganda chaqiruv
  -- `ForeignKeyViolation: update or delete on table "stall_slot_occupancy"
  -- violates foreign key constraint "fk_charge_evidence_stall_slot_
  -- occupancy"` bilan yiqiladi — va STATIK DARVOZA BUNI SEZMAYDI (matnda
  -- oltala jadval baribir bor). Aynan shuning uchun
  -- `test_draft_market_deletion_covers_the_billing_domain` funksiyani
  -- HAQIQATAN chaqiradi. Bu `0013`/`0015`/`0019` juftliklarining
  -- TO'RTINCHI takrori.
  --
  -- Ichki tartib `BILLING_DELETE_ORDER` dan: `charge_evidence` ->
  -- `charge_adjustments` -> `payments` -> `billing_anomalies` ->
  -- `daily_charges` -> `cashier_shifts`. Bu domenda IKKI MUSTAQIL zanjir
  -- bor (`charge_evidence`/`charge_adjustments` -> `daily_charges` va
  -- `payments` -> `cashier_shifts`), shuning uchun ro'yxat
  -- `reversed(BILLING_TENANT_TABLES)` bilan USTMA-UST TUSHMAYDI —
  -- 5-fazadagi tasodifiy ustma-ustlikdan farqli o'laroq.
  --
  -- ⚠ UCHALA JADVALDA (`daily_charges`, `payments`, `cashier_shifts`)
  --   O'ZGARMASLIK TRIGGERI BOR (0020) va ular `DELETE` ni FAQAT QORALAMA
  --   bozor uchun o'tkazadi. Yuqoridagi `IS DISTINCT FROM false` sharti
  --   aynan shu holatni kafolatlaydi, ya'ni bu yerga faqat qoralama bozor
  --   yetib keladi. `tariffs` / `occupancy_events` bilan AYNAN bir xil
  --   naqsh.
  DELETE FROM public.charge_evidence            WHERE market_id = p_market_id;
  DELETE FROM public.charge_adjustments         WHERE market_id = p_market_id;
  DELETE FROM public.payments                   WHERE market_id = p_market_id;
  DELETE FROM public.billing_anomalies          WHERE market_id = p_market_id;
  DELETE FROM public.daily_charges              WHERE market_id = p_market_id;
  DELETE FROM public.cashier_shifts             WHERE market_id = p_market_id;

  -- 5-faza bandlik domeni (0018_occupancy_domain). BLOK SNAPSHOT BLOKIDAN
  -- OLDIN TURISHI SHART va bu O'LCHANGAN, taxmin emas: `occupancy_events`
  -- `snapshots (id, is_billable)` ga kompozit FK bilan tayanadi (D-21),
  -- `snapshots` esa pastdagi blokning BIRINCHI o'chirishi. Blok keyinga
  -- qo'yilganda chaqiruv `ForeignKeyViolation: update or delete on table
  -- "snapshots" violates foreign key constraint
  -- "fk_occupancy_events_snapshot_billable"` bilan yiqiladi — va STATIK
  -- DARVOZA BUNI SEZMAYDI (matnda oltala jadval baribir bor). Aynan
  -- shuning uchun `test_draft_market_deletion_covers_the_occupancy_domain`
  -- funksiyani HAQIQATAN chaqiradi.
  --
  -- Ichki tartib `OCCUPANCY_DELETE_ORDER` dan: `stall_slot_occupancy` ->
  -- `zone_reviews` -> `review_assignments` -> `audit_rounds` ->
  -- `occupancy_events` -> `camera_zones`. Bu domenda FK zanjiridan chetda
  -- turgan jadval YO'Q (4-fazadagi `alert_events` dan farqli).
  --
  -- ⚠ `occupancy_events` VA `zone_reviews` USTIDA O'ZGARMASLIK TRIGGERI
  --   BOR (0018) va u `DELETE` ni FAQAT QORALAMA bozor uchun o'tkazadi.
  --   Yuqoridagi `IS DISTINCT FROM false` sharti aynan shu holatni
  --   kafolatlaydi, ya'ni bu yerga faqat qoralama bozor yetib keladi.
  --   `tariffs` / `stall_category_periods` bilan AYNAN bir xil naqsh.
  DELETE FROM public.stall_slot_occupancy      WHERE market_id = p_market_id;
  DELETE FROM public.zone_reviews              WHERE market_id = p_market_id;
  DELETE FROM public.review_assignments        WHERE market_id = p_market_id;
  DELETE FROM public.audit_rounds              WHERE market_id = p_market_id;
  DELETE FROM public.occupancy_events          WHERE market_id = p_market_id;
  DELETE FROM public.camera_zones              WHERE market_id = p_market_id;

  -- 4-faza snapshot domeni (0014_snapshot_domain). BLOK NVR BLOKIDAN
  -- OLDIN TURISHI SHART va bu O'LCHANGAN, taxmin emas: `capture_runs`
  -- `cameras` ga kompozit FK `(market_id, camera_id)` bilan tayanadi,
  -- `cameras` esa pastdagi BIRINCHI o'chirish. Blok keyinga qo'yilganda
  -- chaqiruv `ForeignKeyViolation: update or delete on table "cameras"
  -- violates foreign key constraint "fk_capture_runs_market_id_camera_id_
  -- cameras"` bilan yiqiladi — va statik darvoza buni SEZMAYDI (matnda
  -- beshala jadval baribir bor).
  --
  -- Ichki tartib `SNAPSHOT_DELETE_ORDER` dan: `snapshots` ->
  -- `capture_runs` -> slotlar -> profillar -> `alert_events`.
  -- `alert_events` FK zanjirida umuman turmaydi, shuning uchun uning o'rni
  -- ixtiyoriy va u oxirida.
  DELETE FROM public.snapshots                  WHERE market_id = p_market_id;
  DELETE FROM public.capture_runs               WHERE market_id = p_market_id;
  DELETE FROM public.snapshot_schedule_slots    WHERE market_id = p_market_id;
  DELETE FROM public.snapshot_schedules         WHERE market_id = p_market_id;
  DELETE FROM public.alert_events               WHERE market_id = p_market_id;

  -- 3-faza NVR domeni (0012_nvr_domain). TARTIB MAJBURIY va u composite FK
  -- zanjiridan kelib chiqadi: uchala bolasi ham `nvr_devices` ga
  -- `(market_id, nvr_id)` bilan tayanadi, ya'ni ota-ona ULARDAN KEYIN
  -- o'chiriladi. `ON DELETE CASCADE` bu yerda ham ATAYIN ishlatilmadi —
  -- sabab pastdagi docstringda (u 4-fazadagi snapshotlarga ham JIMGINA
  -- tarqalardi va rasm-dalil izini o'chirib yuborardi).
  DELETE FROM public.cameras                    WHERE market_id = p_market_id;
  DELETE FROM public.nvr_discovery_runs         WHERE market_id = p_market_id;
  DELETE FROM public.nvr_credentials            WHERE market_id = p_market_id;
  DELETE FROM public.nvr_devices                WHERE market_id = p_market_id;

  DELETE FROM public.stall_assignments          WHERE market_id = p_market_id;
  DELETE FROM public.stall_category_periods     WHERE market_id = p_market_id;
  DELETE FROM public.tariffs                    WHERE market_id = p_market_id;
  -- Majburiy kunlik xizmat haqi reyestri (0027_service_fee_domain).
  -- O'RNI ERKIN va bu O'LCHANGAN: jadvalning YAGONA FK'si
  -- `market_id -> markets.id`, unga esa HECH KIM tayanmaydi (kompozit FK
  -- bilan keladigan bola yo'q). Ya'ni yagona shart — `markets` ning
  -- O'ZIDAN oldin turishi. `tariffs` bilan YONMA-YON qo'yildi: ikkalasi
  -- ham «bozor narxi» oilasidan.
  --
  -- ⚠ JADVAL USTIDA O'ZGARMASLIK TRIGGERI BOR
  --   (`service_fee_past_immutable()`, 0027) va u `DELETE` ni FAQAT
  --   QORALAMA bozor uchun o'tkazadi. Yuqoridagi `IS DISTINCT FROM false`
  --   sharti aynan shu holatni kafolatlaydi. `tariffs` bilan AYNAN bir
  --   xil naqsh.
  DELETE FROM public.market_service_fees        WHERE market_id = p_market_id;
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
"""`0029` davridagi `market_delete_draft()` — tuzatish jadvalisiz.

MIGRATSIYANING O'ZIDA MUZLATILGANI ATAYIN (`0024::MARKET_DELETE_DRAFT_
WITHOUT_LEDGER` bilan aynan bir xil sabab): `alembic_utils` `PGFunction`
ni MODUL ta'rifidan oladi, `functions.py` esa endi YANGI tanani saqlaydi.
Bu nusxasiz `downgrade()` yangi tanani qoldirardi va u o'chirilgan
jadvalga havola qilib, CHAQIRUVDA yiqilardi.
"""


def upgrade() -> None:
    """Upgrade schema."""
    # ------------------------------------------------------------------
    # 1. Jadval — model (`ShiftDeclarationCorrection`) bilan AYNAN bir xil:
    #    indeks nomi va CHECK ifodasi modeldan import qilinadi (0020 qoidasi).
    # ------------------------------------------------------------------
    op.create_table(
        TABLE,
        sa.Column("market_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "id",
            pg.UUID(as_uuid=True),
            server_default=sa.text("uuidv7()"),
            nullable=False,
        ),
        sa.Column("shift_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("declared_soum", sa.BigInteger(), nullable=False),
        sa.Column("reason_code", sa.Text(), nullable=False),
        sa.Column("actor_user_id", pg.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "business_date",
            sa.Date(),
            sa.Computed(BILLING_BUSINESS_DATE_EXPR, persisted=True),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_shift_declaration_corrections"),
        sa.ForeignKeyConstraint(
            ["market_id"],
            ["markets.id"],
            name="fk_shift_declaration_corrections_market_id_markets",
        ),
        sa.ForeignKeyConstraint(
            ["market_id", "shift_id"],
            ["cashier_shifts.market_id", "cashier_shifts.id"],
            name="fk_shift_declaration_corrections_shift",
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["users.id"],
            name="fk_shift_declaration_corrections_actor_user_id_users",
        ),
        sa.UniqueConstraint(
            "market_id", "id", name="uq_shift_declaration_corrections_market_id_id"
        ),
        sa.CheckConstraint(SHIFT_CORRECTION_REASON_CHECK, name="reason_code_allowed"),
        sa.CheckConstraint("declared_soum >= 0", name="declared_soum_non_negative"),
    )
    op.create_index(SHIFT_CORRECTION_INDEX, TABLE, ["market_id", "shift_id"])

    # ------------------------------------------------------------------
    # 2. RLS — ENABLE + FORCE + GRANT -> policy (Pitfall 10, `0027` tartibi).
    # ------------------------------------------------------------------
    for table in SHIFT_CORRECTION_TENANT_TABLES:
        enable_tenant_rls(table)
        grant_app_dml(table)
        create_entity(tenant_policy(table))
        create_entity(owner_bootstrap_policy(table))

    # ------------------------------------------------------------------
    # 3. Audit — «kim, qachon» DB-trigger yozadi (`charge_adjustments` oilasi).
    # ------------------------------------------------------------------
    for table in SHIFT_CORRECTION_AUDITED_TABLES:
        attach_audit_trigger(table)

    # ------------------------------------------------------------------
    # 4. APPEND-ONLY qo'riqchi — `payment_immutable()` naqshi.
    # ------------------------------------------------------------------
    create_entity(SHIFT_CORRECTION_IMMUTABLE)
    attach_immutability_trigger(
        TABLE, "shift_correction_immutable", SHIFT_CORRECTION_IMMUTABLE_TRIGGER
    )

    # ------------------------------------------------------------------
    # 5. KASKAD KENGAYTMASI — tuzatishlar `cashier_shifts` dan OLDIN.
    #    `replace_entity` (CREATE OR REPLACE) huquqlarni saqlaydi.
    # ------------------------------------------------------------------
    replace_entity(MARKET_DELETE_DRAFT)


def downgrade() -> None:
    """Downgrade schema."""
    # KASKAD AVVAL qaytariladi (`0024` sababi): jadval o'chgandan keyin yangi
    # tana mavjud bo'lmagan jadvalga havola qilib qolardi.
    replace_entity(MARKET_DELETE_DRAFT_WITHOUT_CORRECTIONS)

    detach_immutability_trigger(TABLE, SHIFT_CORRECTION_IMMUTABLE_TRIGGER)
    drop_entity(SHIFT_CORRECTION_IMMUTABLE)

    for table in SHIFT_CORRECTION_AUDITED_TABLES:
        detach_audit_trigger(table)

    for table in SHIFT_CORRECTION_TENANT_TABLES:
        drop_entity(owner_bootstrap_policy(table))
        drop_entity(tenant_policy(table))

    op.drop_index(SHIFT_CORRECTION_INDEX, table_name=TABLE)
    op.drop_table(TABLE)
