"""audit: audit_log jadvali, 4 qatlamli o'zgarmaslik va fn_audit_row triggeri

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-29

=============================================================================
O'ZGARMASLIKNING TO'RT QATLAMI — har biri BOSHQA tahdid modelini yopadi va
har biri ALOHIDA buzilishi mumkin (RESEARCH Pattern 5, empirik o'lchangan):

| # | Mexanizm                        | Kimga qarshi         | Kuzatilgan natija        |
| - | ------------------------------- | -------------------- | ------------------------ |
| 1 | `REVOKE UPDATE, DELETE, ...`    | ilova kodi, injection| `permission denied`      |
| 2 | RLS ENABLE+FORCE, policy'siz    | jadval egasi         | `UPDATE 0` (JIMGINA)     |
| 3 | `BEFORE UPDATE OR DELETE` -> ex | qo'shilgan policy    | `audit_log is append-only` |
| 4 | `BEFORE TRUNCATE` -> exception  | `TRUNCATE`           | `audit_log is append-only` |

2-QATLAM JIMGINA ISHLAYDI — bu testni yozishda hal qiluvchi fakt (Pitfall 9):
egaga qarshi `UPDATE` XATO TASHLAMAYDI, u shunchaki 0 qatorga tegadi.
Shuning uchun `tests/integration/test_audit_immutable.py` "exception
bo'ldimi?" emas, "HOLAT o'zgarmadimi?" ni o'lchaydi. Faqat exception kutgan
test yolg'on-yashil berardi.

4-QATLAM ALOHIDA KERAK: 2-qatlam `TRUNCATE` ni TO'XTATMAYDI — RLS umuman
`TRUNCATE` ga qo'llanmaydi.
=============================================================================
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sbozor_core.models.ops import AUDIT_BUSINESS_DATE_EXPR
from sqlalchemy.dialects import postgresql as pg

from migrations.entities.policies import audit_append_policy, audit_read_policy
from migrations.entities.triggers import ALL_TRIGGER_FUNCTIONS
from migrations.helpers import (
    attach_audit_trigger,
    create_entity,
    detach_audit_trigger,
    drop_entity,
    enable_rls,
)

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: str | Sequence[str] | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

AUDITED_TABLE = "user_market_roles"
"""D-10 mexanizmi 1-fazada shu jadvalda faollashadi.

Moliyaviy jadvallar (`daily_charges`, `payments`, ...) 2- va 6-fazalarda
tug'iladi; ular uchun `attach_audit_trigger()` bir satrlik ish bo'lib qoladi.
Rol berish/olib tashlash esa huquq ko'tarilishining asosiy yo'li, shuning
uchun u audit ostiga BIRINCHI olinadi.
"""


def upgrade() -> None:
    """Upgrade schema."""
    # ------------------------------------------------------------------
    # 1. Trigger funksiyalari. Jadvaldan OLDIN: `fn_audit_row()` ichida
    #    `audit_log` ga murojaat bor, lekin plpgsql tanasi CREATE paytida
    #    tekshirilmaydi — shunga qaramay tartib mantiqan shunday: funksiya
    #    jadvalning bir qismi emas, mustaqil obyekt.
    # ------------------------------------------------------------------
    for function in ALL_TRIGGER_FUNCTIONS:
        create_entity(function)

    # ------------------------------------------------------------------
    # 2. audit_log jadvali
    # ------------------------------------------------------------------
    op.create_table(
        "audit_log",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column(
            "at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        # DB tomonda hisoblanadigan biznes-kun (FOUND-05). Ifoda modeldan
        # olinadi, ya'ni model va migratsiya orasida drift bo'lishi mumkin emas.
        sa.Column(
            "business_date",
            sa.Date(),
            sa.Computed(AUDIT_BUSINESS_DATE_EXPR, persisted=True),
            nullable=False,
        ),
        # NULL = platforma-global harakat (hech qaysi bozorga tegishli emas).
        # FK ATAYIN YO'Q — sabab `sbozor_core/models/ops.py` da.
        sa.Column("market_id", pg.UUID(as_uuid=True), nullable=True),
        sa.Column("actor_user_id", pg.UUID(as_uuid=True), nullable=True),
        sa.Column("actor_kind", sa.Text(), server_default=sa.text("'user'"), nullable=False),
        sa.Column("actor_label", sa.Text(), nullable=True),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("table_name", sa.Text(), nullable=False),
        sa.Column("row_id", pg.UUID(as_uuid=True), nullable=True),
        sa.Column("old_value", pg.JSONB(), nullable=True),
        sa.Column("new_value", pg.JSONB(), nullable=True),
        sa.Column("changed_keys", pg.ARRAY(sa.Text()), nullable=True),
        sa.Column("request_id", sa.Text(), nullable=True),
        sa.Column("ip", pg.INET(), nullable=True),
        sa.Column("source", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_audit_log"),
    )

    # Uchala indeks ham `market_id` bilan boshlanadi (P9): tenant filtri har
    # so'rovda bor, shuning uchun boshqa ustundan boshlangan indeks
    # rejalashtiruvchi uchun foydasiz bo'lardi.
    op.create_index("ix_audit_log_market_id_at", "audit_log", ["market_id", sa.text("at DESC")])
    op.create_index(
        "ix_audit_log_market_id_table_name_row_id",
        "audit_log",
        ["market_id", "table_name", "row_id"],
    )
    op.create_index(
        "ix_audit_log_market_id_actor_user_id_at",
        "audit_log",
        ["market_id", "actor_user_id", sa.text("at DESC")],
    )

    # ------------------------------------------------------------------
    # 3. 1-QATLAM: huquqlar.
    #    Ikkala satr ham ATAYIN literal (yordamchilar mavjud bo'lsa ham):
    #    bu jadvalning butun xavfsizlik da'vosi shu ikki satrda va u
    #    o'qiganda ham, `grep` qilganda ham ko'rinib turishi shart.
    # ------------------------------------------------------------------
    op.execute("GRANT SELECT, INSERT ON TABLE audit_log TO sbozor_app")
    op.execute("REVOKE UPDATE, DELETE, TRUNCATE ON TABLE audit_log FROM sbozor_app")

    # ------------------------------------------------------------------
    # 4. 2-QATLAM: RLS. `enable_tenant_rls()` EMAS — u to'liq DML GRANT
    #    beradi va yuqoridagi REVOKE'ni bekor qilardi.
    #
    #    `owner_bootstrap` policy'si bu jadvalga BERILMAYDI: u
    #    `FOR ALL ... USING (true)` bo'lgani uchun egaga UPDATE/DELETE da
    #    qatorlarni ko'rsatib qo'yardi va 2-qatlamni yo'q qilardi.
    # ------------------------------------------------------------------
    enable_rls("audit_log")
    create_entity(audit_append_policy())
    create_entity(audit_read_policy())

    # ------------------------------------------------------------------
    # 5. 3- va 4-QATLAM: triggerlar.
    #    3-qatlam odatda UMUMAN ISHGA TUSHMAYDI (2-qatlam qatorlarni
    #    ko'rsatmaydi) — u aynan "kimdir UPDATE policy'si qo'shib qo'ysa"
    #    holati uchun. 4-qatlam esa HAR DOIM ishlaydi: RLS `TRUNCATE` ga
    #    umuman qo'llanmaydi.
    # ------------------------------------------------------------------
    op.execute(
        "CREATE TRIGGER audit_no_mutate BEFORE UPDATE OR DELETE ON audit_log "
        "FOR EACH ROW EXECUTE FUNCTION audit_immutable()"
    )
    op.execute(
        "CREATE TRIGGER audit_no_truncate BEFORE TRUNCATE ON audit_log "
        "FOR EACH STATEMENT EXECUTE FUNCTION audit_immutable()"
    )

    # ------------------------------------------------------------------
    # 6. D-10 mexanizmini mavjud jadvalda faollashtirish.
    #    `sbozor_core.schema_contract.AUDITED_TABLES` shu ro'yxatning
    #    kod-tomondagi nusxasi; ikkalasining mosligi meta-test bilan
    #    qulflangan.
    # ------------------------------------------------------------------
    attach_audit_trigger(AUDITED_TABLE)


def downgrade() -> None:
    """Downgrade schema."""
    detach_audit_trigger(AUDITED_TABLE)

    op.execute("DROP TRIGGER IF EXISTS audit_no_truncate ON audit_log")
    op.execute("DROP TRIGGER IF EXISTS audit_no_mutate ON audit_log")

    drop_entity(audit_read_policy())
    drop_entity(audit_append_policy())

    op.drop_index("ix_audit_log_market_id_actor_user_id_at", table_name="audit_log")
    op.drop_index("ix_audit_log_market_id_table_name_row_id", table_name="audit_log")
    op.drop_index("ix_audit_log_market_id_at", table_name="audit_log")
    op.drop_table("audit_log")

    # Funksiyalar OXIRIDA: ularga bog'langan triggerlar yuqorida
    # o'chirilmagan bo'lsa `DROP FUNCTION` bog'liqlik xatosi bilan yiqiladi.
    for function in reversed(ALL_TRIGGER_FUNCTIONS):
        drop_entity(function)
