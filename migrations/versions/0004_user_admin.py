"""user_admin: foydalanuvchi boshqaruvi va profil uchun SECURITY DEFINER funksiyalari

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-29

=============================================================================
BU MIGRATSIYA HAM SXEMANI O'ZGARTIRMAYDI — u faqat funksiyalar qo'shadi.

`0001` login uchun O'QISH yuzasini, `0003` sessiya va parol uchun YOZISH
yuzasini ochgan edi. Foydalanuvchi BOSHQARUVI (D-04) esa uchinchi guruh
operatsiyani talab qiladi va ularning hammasi bir xil devorga uriladi —
`REVOKE ALL ON TABLE users FROM sbozor_app` (0001):

| Operatsiya                       | Nega `SECURITY DEFINER` kerak            |
| -------------------------------- | ---------------------------------------- |
| foydalanuvchi yaratish           | `users` — app-rolga `INSERT` huquqi yo'q |
| ro'yxatdagi profil ma'lumoti     | `users` — app-rolga `SELECT` huquqi yo'q |
| til tanlovini saqlash (D-13)     | `users` — app-rolga `UPDATE` huquqi yo'q |
| bozor ro'yxati `timezone` bilan  | `markets` — RLS faqat TANLANGAN bozorni  |
|                                  | ko'rsatadi, platforma adminiga hammasi   |
|                                  | kerak (D-06)                             |

XAVFSIZLIK CHEGARASI KENGAYMAYDI. `auth_list_users(uuid[])` ixtiyoriy
`WHERE` qabul qilmaydi — u faqat ANIQ ID ro'yxati bo'yicha ishlaydi va
ID'lar chaqiruvchida `user_market_roles` dan RLS OSTIDA olinadi. Ya'ni
boshqa bozor a'zosining ID'si birinchi qadamda umuman qaytmaydi va bu
funksiya "hamma foydalanuvchini bering" so'roviga aylantirib bo'lmaydi.
=============================================================================
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

from migrations.entities.functions import (
    USER_ADMIN_FUNCTIONS,
    USER_ADMIN_GRANT_SIGNATURES,
)
from migrations.helpers import APP_ROLE, create_entity, drop_entity

# revision identifiers, used by Alembic.
revision: str = "0004"
down_revision: str | Sequence[str] | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    for function in USER_ADMIN_FUNCTIONS:
        create_entity(function)

    for signature in USER_ADMIN_GRANT_SIGNATURES:
        # PUBLIC dan AVVAL olib tashlanadi: Postgres yangi funksiyaga
        # `EXECUTE TO PUBLIC` ni STANDART beradi, ya'ni REVOKE'siz
        # foydalanuvchi yaratish yo'li bazadagi har qanday rol uchun
        # ochiq bo'lib qolardi.
        op.execute(f"REVOKE ALL ON FUNCTION {signature} FROM PUBLIC")
        op.execute(f"GRANT EXECUTE ON FUNCTION {signature} TO {APP_ROLE}")


def downgrade() -> None:
    """Downgrade schema."""
    for function in reversed(USER_ADMIN_FUNCTIONS):
        drop_entity(function)
