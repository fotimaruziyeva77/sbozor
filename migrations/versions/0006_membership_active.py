"""membership_active: auth_memberships() qaytish to'plamiga `is_active` qo'shiladi

Revision ID: 0006
Revises: 0005
Create Date: 2026-07-31

=============================================================================
BU MIGRATSIYA SXEMANI O'ZGARTIRMAYDI — jadval ham, ustun ham qo'shilmaydi.
U BITTA funksiyaning QAYTISH TIPINI kengaytiradi va aynan shu sababdan
oddiy "ustun qo'shish" emas.

MUAMMO (UI-SPEC §12.1.1, W0-12 zanjirining 1-bandi): usta 1-qadamda
qoralama bozor tug'diradi (`markets.is_active = false`) va foydalanuvchi
ishni yarim tashlab ketishi mumkin. U qaytib kelganda bozor tanlash
ekranida o'sha qoralamani `Qoralama` belgisi bilan ko'rishi kerak. Ekranning
ASOSIY manbai — `POST /auth/login` javobidagi `markets`, u esa a'zolik
tarmog'ida `auth_memberships()` dan keladi. Funksiya bozor faolligini
UMUMAN qaytarmasdi, ya'ni qoralama bozor ro'yxatda ko'rinardi-yu,
"faol"dan farqi bilinmasdi (X-2: jimgina YOLG'ON yorliq).

NEGA `CREATE OR REPLACE` YETMAYDI (empirik, `postgres:18.4`):

    ERROR:  cannot change return type of existing function
    HINT:   Use DROP FUNCTION public.auth_memberships(uuid) first.

`RETURNS TABLE (...)` ro'yxatiga ustun qo'shish qaytish tipini o'zgartiradi,
Postgres esa buni `REPLACE` bilan bajarmaydi. Shuning uchun bu yerda
`DROP` + qayta yaratish.

NEGA XOM `DROP`, `drop_entity(AUTH_MEMBERSHIPS)` EMAS — ATAYIN:
`alembic_utils` obyektni `signature` bo'yicha taniydi va bu yerda ESKI
(uch ustunli) hamda YANGI (to'rt ustunli) ta'riflarning imzosi AYNAN bir
xil — `auth_memberships(p_user_id uuid)`. `drop_entity` esa modulning
JORIY (allaqachon yangilangan) ta'rifidan quriladi, ya'ni u bazadagi eski
obyektni emas, o'zining yangi nusxasini tushirmoqchi bo'ladi.
`replaceable_entity` mexanizmini bu ikkiligi bilan chalkashtirmaslik uchun
tushirish TO'G'RIDAN-TO'G'RI, imzo bilan yoziladi.

NEGA `GRANT`/`REVOKE` QAYTADAN QO'YILADI: `DROP` funksiya bilan birga
uning huquqlarini ham olib ketadi va Postgres YANGI funksiyaga
`EXECUTE TO PUBLIC` ni STANDART beradi. Ya'ni bu ikki satrsiz natija ikki
tomonlama noto'g'ri bo'lardi — `sbozor_app` funksiyani chaqira olmasdi
(login oqimi `permission denied` bilan yiqilardi), PUBLIC esa uni chaqira
olardi.
=============================================================================
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

from migrations.entities.functions import AUTH_MEMBERSHIPS
from migrations.helpers import APP_ROLE, create_entity

# revision identifiers, used by Alembic.
revision: str = "0006"
down_revision: str | Sequence[str] | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SIGNATURE = "public.auth_memberships(uuid)"
"""GRANT/REVOKE va DROP uchun Postgres imzosi (argument TIPLARI bilan)."""

_DROP = f"DROP FUNCTION IF EXISTS {_SIGNATURE}"

_LEGACY_DEFINITION = """
CREATE FUNCTION public.auth_memberships(p_user_id uuid)
RETURNS TABLE (
    market_id uuid,
    market_name text,
    roles text[]
)
LANGUAGE sql
SECURITY DEFINER
SET search_path = pg_catalog, public
STABLE
AS $$
    SELECT r.market_id,
           m.name,
           r.roles
    FROM public.user_market_roles AS r
    JOIN public.markets AS m ON m.id = r.market_id
    WHERE r.user_id = p_user_id
    ORDER BY m.name
$$
"""
"""`0001` dagi ESKI (uch ustunli) ta'rif — `downgrade()` uchun LITERAL.

Entity modulidan olib bo'lmaydi: `migrations.entities.functions` allaqachon
YANGI holatda va downgrade undan eski ta'rifni tiklay olmaydi. Ikki
nusxaning ajralib ketishi bu yerda xavfsiz — `downgrade()` faqat
`0006` dan orqaga qaytish uchun va u yerda kutilayotgan holat aynan
`0001`/`0005` dagi holat.
"""


def _restore_grants() -> None:
    """`REVOKE ALL FROM PUBLIC` + `GRANT EXECUTE TO sbozor_app`.

    Har `CREATE FUNCTION` dan KEYIN chaqirilishi SHART — `DROP` huquqlarni
    ham olib ketadi va yangi funksiya PUBLIC uchun ochiq tug'iladi.
    """
    op.execute(f"REVOKE ALL ON FUNCTION {_SIGNATURE} FROM PUBLIC")
    op.execute(f"GRANT EXECUTE ON FUNCTION {_SIGNATURE} TO {APP_ROLE}")


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(_DROP)
    create_entity(AUTH_MEMBERSHIPS)
    _restore_grants()


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(_DROP)
    op.execute(_LEGACY_DEFINITION)
    _restore_grants()
