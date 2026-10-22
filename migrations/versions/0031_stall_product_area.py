"""stalls.product_type / area_m2 — rasta nima sotadi va maydoni qancha

Revision ID: 0031
Revises: 0030
Create Date: 2026-10-22

=============================================================================
⛔⛔ NEGA BU MIGRATSIYA BOR (foydalanuvchi talabi, 2026-10-22).

Navoiy viloyati hokimining 2025-yil 28-maydagi 131-5-0-Q/25-son qarori
bozor ma'muriyati oladigan joy haqini MAHSULOT TURI va JOY O'LCHAMI bo'yicha
belgilaydi. Tizimda esa rastaning na nima sotishi, na o'lchami bor edi —
ya'ni «bu rastaning 22 000 lik tarifi qarorga mosmi?» savoliga javob
berishning iloji yo'q edi.

⛔ BU USTUNLAR PULNI O'ZGARTIRMAYDI: kunlik tarif hamon toifa → tarif
   zanjiridan keladi (D-04/D-05). Ular solishtirish uchun ma'lumot.

⛔ IKKALASI HAM `NULL` — mavjud 53 ta Karmana rastasi hech narsa
   yo'qotmaydi; ma'muriyat ularni bittalab to'ldiradi (`0026` bilan bir xil
   qaror).

⛔ `product_type` RO'YXATI QO'LDA YOZILMAYDI — `PRODUCT_TYPE_CHECK`
   `ProductType` enumidan hosil qilinadi (`0028` bilan aynan bir xil naqsh).

⛔ `area_m2` — `NUMERIC(6,2)`: kasr o'lchov (3,6 m²) aniq saqlanadi; nol
   va 10 000 m² dan kattasi rad etiladi (sabab `AREA_M2_CHECK` docstringida).
=============================================================================
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sbozor_core.models.market import AREA_M2_CHECK, PRODUCT_TYPE_CHECK

# revision identifiers, used by Alembic.
revision: str = "0031"
down_revision: str | Sequence[str] | None = "0030"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """⛔ Cheklov nomlari PREFIKSSIZ — `alembic.ini` konvensiyasi `ck_stalls_` ni o'zi qo'yadi."""
    op.add_column("stalls", sa.Column("product_type", sa.Text(), nullable=True))
    op.add_column("stalls", sa.Column("area_m2", sa.Numeric(6, 2), nullable=True))
    op.create_check_constraint("product_type_allowed", "stalls", PRODUCT_TYPE_CHECK)
    op.create_check_constraint("area_m2_range", "stalls", AREA_M2_CHECK)


def downgrade() -> None:
    op.drop_constraint("area_m2_range", "stalls", type_="check")
    op.drop_constraint("product_type_allowed", "stalls", type_="check")
    op.drop_column("stalls", "area_m2")
    op.drop_column("stalls", "product_type")
