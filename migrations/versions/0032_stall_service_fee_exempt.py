"""stalls.service_fee_exempt — tarozi olinmaydigan rasta

Revision ID: 0032
Revises: 0031
Create Date: 2026-10-22

=============================================================================
⛔⛔ NEGA BU MIGRATSIYA BOR (foydalanuvchi talabi, 2026-10-22).

Karmanadagi 5-rastada ko'kat sotiladi: u bog'lab sotiladi, bozor tarozisi
ishlatilmaydi va undan tarozi puli OLINMAYDI. Tizim esa tarozini (0027)
sotuvchining hisob oladigan eng kichik kodli rastasiga har kuni qo'shardi
(260930): tizim 26 000 kutardi, kassir esa goh 26 000, goh tarozi
belgisini olib 22 000 yozardi.

⛔ USTUN `NOT NULL DEFAULT false`: mavjud 53 rastaning hammasida tarozi
   avvalgidek olinadi — hech bir rastaning puli migratsiya bilan
   o'zgarmaydi. Belgini ma'muriyat rasta oynasida qo'yadi.

⛔ PUL QOIDASI `billing_repo._STALL_DAY_MONEY` da: belgilangan rasta
   tarozini KO'TARMAYDI; sotuvchining boshqa hisob oladigan rastasi bo'lsa
   tarozi o'sha rastaga o'tadi. Tarif (rasta puli) o'zgarmaydi.
=============================================================================
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0032"
down_revision: str | Sequence[str] | None = "0031"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "stalls",
        sa.Column(
            "service_fee_exempt",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("stalls", "service_fee_exempt")
