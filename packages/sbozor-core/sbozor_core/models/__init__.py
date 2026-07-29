"""SBOZOR ORM modellari.

`Base.metadata` — Alembic `target_metadata` sining yagona manbai. Har bir
model moduli SHU YERDA import qilinishi shart: import qilinmagan modul
metadata'ga tushmaydi va autogenerate uni "o'chirilgan jadval" deb hisoblab
`op.drop_table()` taklif qiladi.
"""

from __future__ import annotations

from sbozor_core.models.base import (
    NAMING_CONVENTION,
    Base,
    TenantMixin,
    TimestampMixin,
    market_fk_column,
    uuid_pk,
)
from sbozor_core.models.identity import (
    LOCALE_CHECK,
    LOCALE_VALUES,
    ROLE_VALUES,
    ROLES_SUBSET_CHECK,
    Market,
    RefreshToken,
    User,
    UserMarketRole,
)

__all__ = [
    "LOCALE_CHECK",
    "LOCALE_VALUES",
    "NAMING_CONVENTION",
    "ROLES_SUBSET_CHECK",
    "ROLE_VALUES",
    "Base",
    "Market",
    "RefreshToken",
    "TenantMixin",
    "TimestampMixin",
    "User",
    "UserMarketRole",
    "market_fk_column",
    "uuid_pk",
]
