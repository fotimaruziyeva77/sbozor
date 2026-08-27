"""auth_support: sessiya va parol yozish yo'li uchun SECURITY DEFINER funksiyalari

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-29

=============================================================================
BU MIGRATSIYA SXEMANI O'ZGARTIRMAYDI — u faqat funksiyalar qo'shadi.

Sabab: 0001 login uchun O'QISH yuzasini ochgan edi (`auth_find_login` va
boshqalar), lekin auth oqimida YOZISH ham bor va u aynan bir xil devorga
uriladi:

| Operatsiya                      | Nega tenant kontekstisiz kerak            |
| ------------------------------- | ----------------------------------------- |
| parol hash'ini yangilash        | `users` — `sbozor_app` ga `REVOKE ALL`    |
| foydalanuvchini bloklash        | bir xil                                   |
| refresh token yozish/topish     | `refresh_tokens` — RLS, cookie kelganda   |
|                                 | bozor HALI NOMA'LUM (`mid` refresh'da yo'q)|

Ikkinchi qatorlar guruhi 01-06 rejasini yozishda ko'rinmagan: reja faqat
`auth_update_password_hash` va `auth_set_active` ni ko'rsatgan edi. Lekin
`refresh_tokens` ustidagi RLS `POST /auth/refresh` ni UMUMAN ishlamas
holga keltiradi — `jti` bo'yicha global qidiruv 0 qator qaytaradi. Sxema
buni allaqachon ko'zlagan: `uq_refresh_tokens_jti` — `market_id` bilan
BOSHLANMAYDIGAN yagona indeks va u meta-testda aniq istisno sifatida
qayd etilgan ("refresh cookie kelganda bozor hali noma'lum").

XAVFSIZLIK CHEGARASI KENGAYMAYDI: har bir funksiya bitta operatsiyani
bajaradi, aniq kalit bo'yicha filtrlaydi, `search_path` ni pin qiladi va
`PUBLIC` dan yopiq. Ular "RLS'siz `refresh_tokens` ustida ishlash"
imkonini BERMAYDI — ixtiyoriy `WHERE` qabul qilmaydi.
=============================================================================
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

from migrations.entities.functions import (
    AUTH_SUPPORT_FUNCTIONS,
    AUTH_SUPPORT_GRANT_SIGNATURES,
)
from migrations.helpers import APP_ROLE, create_entity, drop_entity

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: str | Sequence[str] | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    for function in AUTH_SUPPORT_FUNCTIONS:
        create_entity(function)

    for signature in AUTH_SUPPORT_GRANT_SIGNATURES:
        # PUBLIC dan AVVAL olib tashlanadi: Postgres yangi funksiyaga
        # `EXECUTE TO PUBLIC` ni STANDART beradi, ya'ni REVOKE'siz parol
        # yozish yo'li bazadagi har qanday rol uchun ochiq bo'lib qolardi.
        op.execute(f"REVOKE ALL ON FUNCTION {signature} FROM PUBLIC")
        op.execute(f"GRANT EXECUTE ON FUNCTION {signature} TO {APP_ROLE}")


def downgrade() -> None:
    """Downgrade schema."""
    for function in reversed(AUTH_SUPPORT_FUNCTIONS):
        drop_entity(function)
