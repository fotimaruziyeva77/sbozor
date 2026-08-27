"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from migrations.helpers import (
    enable_rls,
    enable_tenant_rls,
    grant_app_dml,
    revoke_app_all,
)
${imports if imports else ""}

# revision identifiers, used by Alembic.
revision: str = ${repr(up_revision)}
down_revision: str | Sequence[str] | None = ${repr(down_revision)}
branch_labels: str | Sequence[str] | None = ${repr(branch_labels)}
depends_on: str | Sequence[str] | None = ${repr(depends_on)}


def upgrade() -> None:
    """Upgrade schema.

    ESLATMA — yangi TENANT jadvali qo'shsangiz uch qadam MAJBURIY va
    ularning tartibi ham muhim:

        op.create_table("stalls", sa.Column("market_id", ...), ...)
        enable_tenant_rls("stalls")                       # ENABLE+FORCE+GRANT
        op.create_entity(tenant_policy("stalls"))         # app-rol policy'si
        op.create_entity(owner_bootstrap_policy("stalls"))

    `alembic-utils` faqat uchinchi qadamni biladi. Ikkinchisi unutilsa
    policy TA'SIRSIZ qoladi va jadval hamma uchun ochiq bo'ladi — buni
    `tests/tenancy/test_meta.py` ushlaydi, lekin faqat test ishga
    tushirilganda. Yangi jadvalni `migrations/entities/__init__.py` dagi
    `TENANT_TABLES` ro'yxatiga ham qo'shing.
    """
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    """Downgrade schema."""
    ${downgrades if downgrades else "pass"}
