"""user_market_roles.roles — «buxgalter» (accountant) roli

Revision ID: 0034
Revises: 0033
Create Date: 2026-10-26

=============================================================================
⛔⛔ NEGA BU MIGRATSIYA BOR (foydalanuvchi talabi, 2026-10-26).

Buxgalterga pul hisobotlari kerak edi, lekin eng yaqin rol — direktor —
kameralar, audit jurnali va nizo qarorini ham ochib berardi. Yangi
`accountant` roli FAQAT o'qiydi; huquqlari `services/core-api/app/security/
rbac.py` da.

⛔ SXEMA O'ZGARISHI FAQAT CHECK KONSTRAYT — USTUN YO'Q (`0028` naqshi):
   `ROLES_SUBSET_CHECK` `Role` enumidan hosil qilinadi va unga
   `accountant` qo'shildi.
=============================================================================
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
from sbozor_core.models.identity import ROLE_VALUES, ROLES_SUBSET_CHECK

# revision identifiers, used by Alembic.
revision: str = "0034"
down_revision: str | Sequence[str] | None = "0033"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ADDED = "accountant"


def upgrade() -> None:
    """⛔ Nom PREFIKSSIZ — `alembic.ini` konvensiyasi `ck_user_market_roles_` ni o'zi qo'yadi."""
    op.drop_constraint("roles_allowed", "user_market_roles", type_="check")
    op.create_check_constraint("roles_allowed", "user_market_roles", ROLES_SUBSET_CHECK)


def downgrade() -> None:
    """⚠ `accountant` roli berilgan a'zolik BOR bo'lsa downgrade yiqiladi — ATAYIN:
    jimgina olib tashlash odamning kirishini indamay yo'qotardi.
    """
    previous = ", ".join(f"'{value}'" for value in ROLE_VALUES if value != _ADDED)
    op.drop_constraint("roles_allowed", "user_market_roles", type_="check")
    op.create_check_constraint(
        "roles_allowed",
        "user_market_roles",
        f"roles <@ ARRAY[{previous}]::text[]",
    )
