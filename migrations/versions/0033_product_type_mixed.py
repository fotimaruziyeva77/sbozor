"""stalls.product_type — «aralash mahsulotlar» (mixed)

Revision ID: 0033
Revises: 0032
Create Date: 2026-10-22

=============================================================================
⛔⛔ NEGA BU MIGRATSIYA BOR (foydalanuvchi talabi, 2026-10-22).

Karmanada bir rastada bir necha turdagi mahsulot sotadiganlar bor. 0031 da
ular uchun «eng qimmat turni tanlab, qolganini izohga yozish» ko'zda
tutilgan edi; foydalanuvchi ularni alohida tur sifatida belgilashni so'radi.

⛔ SXEMA O'ZGARISHI FAQAT CHECK KONSTRAYT — USTUN YO'Q (`0028` naqshi):
   `PRODUCT_TYPE_CHECK` `ProductType` enumidan hosil qilinadi va unga
   `mixed` qo'shildi.

⛔ PULGA TA'SIR YO'Q — `product_type` ning qolgan qiymatlari kabi.
=============================================================================
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
from sbozor_core.models.market import PRODUCT_TYPE_CHECK, PRODUCT_TYPE_VALUES

# revision identifiers, used by Alembic.
revision: str = "0033"
down_revision: str | Sequence[str] | None = "0032"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ADDED = "mixed"


def upgrade() -> None:
    """⛔ Nom PREFIKSSIZ — `alembic.ini` konvensiyasi `ck_stalls_` ni o'zi qo'yadi."""
    op.drop_constraint("product_type_allowed", "stalls", type_="check")
    op.create_check_constraint("product_type_allowed", "stalls", PRODUCT_TYPE_CHECK)


def downgrade() -> None:
    """⚠ `mixed` qiymatli qator BOR bo'lsa downgrade CHECK yaratishda yiqiladi.

    Bu ATAYIN: jimgina `NULL` ga aylantirish ma'muriyat kiritgan ma'lumotni
    yo'qotardi. Avval o'sha rastalarga boshqa tur qo'yilsin.
    """
    previous = ", ".join(f"'{value}'" for value in PRODUCT_TYPE_VALUES if value != _ADDED)
    op.drop_constraint("product_type_allowed", "stalls", type_="check")
    op.create_check_constraint(
        "product_type_allowed",
        "stalls",
        f"product_type IS NULL OR product_type IN ({previous})",
    )
