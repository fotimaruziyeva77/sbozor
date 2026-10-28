"""payme — onlayn to'lov: payments.method 'payme' + payme_transactions

Revision ID: 0035
Revises: 0034
Create Date: 2026-10-28

=============================================================================
⛔⛔ NEGA BU MIGRATSIYA BOR (foydalanuvchi talabi, 2026-10-28).

Sotuvchi kunlik to'lovni rastadagi QR-kod orqali Payme'da to'laydi. Payme
Merchant API bizning serverga murojaat qiladi va to'lov `payments` ga
avtomatik yoziladi.

  1. `payments.method` CHECK ga `payme` (`PAYMENT_METHOD_CHECK` enumdan).
  2. `payments.cashier_id` NULLABLE — LEKIN faqat `payme` da
     (`PAYMENT_CASHIER_CHECK`): kassir yozgan to'lovda kassir MAJBURIY qoladi.
  3. `payme_transactions` — Payme tranzaksiyasining holati va referensi;
     tenant RLS, audit triggeri, `market_delete_draft()` kaskadi.
=============================================================================
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from alembic_utils.pg_function import PGFunction
from sbozor_core.models.billing import (
    PAYME_STATE_CHECK,
    PAYME_TRANSACTION_STALL_INDEX,
    PAYMENT_CASHIER_CHECK,
    PAYMENT_METHOD_CHECK,
    PAYMENT_METHOD_VALUES,
)
from sqlalchemy.dialects import postgresql as pg

from migrations.entities import PAYME_AUDITED_TABLES, PAYME_TENANT_TABLES
from migrations.entities.functions import MARKET_DELETE_DRAFT
from migrations.entities.policies import owner_bootstrap_policy, tenant_policy
from migrations.helpers import (
    attach_audit_trigger,
    create_entity,
    detach_audit_trigger,
    drop_entity,
    enable_tenant_rls,
    grant_app_dml,
    replace_entity,
)

# revision identifiers, used by Alembic.
revision: str = "0035"
down_revision: str | Sequence[str] | None = "0034"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE = "payme_transactions"
_ADDED_METHOD = "payme"

_PAYME_DELETE_LINE = (
    "  -- 0035 — Payme tranzaksiyasi `payments` ga kompozit FK bilan tayanadi.\n"
    "  DELETE FROM public.payme_transactions         WHERE market_id = p_market_id;\n"
)

MARKET_DELETE_DRAFT_WITHOUT_PAYME = PGFunction(
    schema="public",
    signature=MARKET_DELETE_DRAFT.signature,
    definition=MARKET_DELETE_DRAFT.definition.replace(_PAYME_DELETE_LINE, ""),
)
"""0034 holatidagi funksiya — downgrade uchun (joriy ta'rifdan Payme qatori olinadi)."""


def upgrade() -> None:
    """Upgrade schema."""
    if _PAYME_DELETE_LINE not in MARKET_DELETE_DRAFT.definition:
        raise RuntimeError("market_delete_draft() da payme_transactions qatori yo'q")

    op.drop_constraint("method_allowed", "payments", type_="check")
    op.create_check_constraint("method_allowed", "payments", PAYMENT_METHOD_CHECK)
    op.alter_column("payments", "cashier_id", existing_type=pg.UUID(as_uuid=True), nullable=True)
    op.create_check_constraint("cashier_required_unless_online", "payments", PAYMENT_CASHIER_CHECK)

    op.create_table(
        TABLE,
        sa.Column("market_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("id", pg.UUID(as_uuid=True), server_default=sa.text("uuidv7()"), nullable=False),
        sa.Column("paycom_id", sa.Text(), nullable=False),
        sa.Column("paycom_time", sa.BigInteger(), nullable=False),
        sa.Column("amount_soum", sa.BigInteger(), nullable=False),
        sa.Column("stall_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("vendor_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("state", sa.SmallInteger(), nullable=False),
        sa.Column("create_time", sa.BigInteger(), nullable=False),
        sa.Column("perform_time", sa.BigInteger(), nullable=True),
        sa.Column("cancel_time", sa.BigInteger(), nullable=True),
        sa.Column("reason", sa.SmallInteger(), nullable=True),
        sa.Column("payment_id", pg.UUID(as_uuid=True), nullable=True),
        sa.Column("reversal_payment_id", pg.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_payme_transactions"),
        sa.ForeignKeyConstraint(
            ["market_id"], ["markets.id"], name="fk_payme_transactions_market_id_markets"
        ),
        sa.ForeignKeyConstraint(
            ["market_id", "stall_id"],
            ["stalls.market_id", "stalls.id"],
            name="fk_payme_transactions_stall",
        ),
        sa.ForeignKeyConstraint(
            ["market_id", "vendor_id"],
            ["vendors.market_id", "vendors.id"],
            name="fk_payme_transactions_vendor",
        ),
        sa.ForeignKeyConstraint(
            ["market_id", "payment_id"],
            ["payments.market_id", "payments.id"],
            name="fk_payme_transactions_payment",
        ),
        sa.ForeignKeyConstraint(
            ["market_id", "reversal_payment_id"],
            ["payments.market_id", "payments.id"],
            name="fk_payme_transactions_reversal_payment",
        ),
        sa.UniqueConstraint("market_id", "id", name="uq_payme_transactions_market_id_id"),
        sa.UniqueConstraint(
            "market_id", "paycom_id", name="uq_payme_transactions_market_id_paycom_id"
        ),
        sa.CheckConstraint(PAYME_STATE_CHECK, name="state_allowed"),
        sa.CheckConstraint("amount_soum > 0", name="amount_soum_positive"),
    )
    op.create_index(PAYME_TRANSACTION_STALL_INDEX, TABLE, ["market_id", "stall_id", "state"])

    for table in PAYME_TENANT_TABLES:
        enable_tenant_rls(table)
        grant_app_dml(table)
        create_entity(tenant_policy(table))
        create_entity(owner_bootstrap_policy(table))

    for table in PAYME_AUDITED_TABLES:
        attach_audit_trigger(table)

    replace_entity(MARKET_DELETE_DRAFT)


def downgrade() -> None:
    """⚠ Payme to'lovi BOR bo'lsa downgrade CHECK/NOT NULL da yiqiladi — ATAYIN:
    pul yozuvini jimgina o'chirish yoki o'zgartirish mumkin emas.
    """
    replace_entity(MARKET_DELETE_DRAFT_WITHOUT_PAYME)

    for table in PAYME_AUDITED_TABLES:
        detach_audit_trigger(table)

    for table in PAYME_TENANT_TABLES:
        drop_entity(owner_bootstrap_policy(table))
        drop_entity(tenant_policy(table))

    op.drop_index(PAYME_TRANSACTION_STALL_INDEX, table_name=TABLE)
    op.drop_table(TABLE)

    op.drop_constraint("cashier_required_unless_online", "payments", type_="check")
    op.alter_column("payments", "cashier_id", existing_type=pg.UUID(as_uuid=True), nullable=False)
    previous = ", ".join(f"'{value}'" for value in PAYMENT_METHOD_VALUES if value != _ADDED_METHOD)
    op.drop_constraint("method_allowed", "payments", type_="check")
    op.create_check_constraint("method_allowed", "payments", f"method IN ({previous})")
