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
from sbozor_core.models.market import (
    OPEN_WEEKDAYS_CHECK,
    STALL_CODE_SORT_EXPR,
    STALL_STATUS_CHECK,
    STALL_STATUS_VALUES,
    TARIFF_BUSINESS_DATE_EXPR,
    MarketCalendarException,
    MarketProfile,
    Stall,
    StallAssignment,
    StallCategory,
    StallCategoryPeriod,
    StallCodeRegistry,
    Tariff,
    Vendor,
    Zone,
)
from sbozor_core.models.nvr import (
    CAMERA_STATUS_CHECK,
    CAMERA_STATUS_VALUES,
    DISCOVERY_RUN_ACTIVE_STATUSES,
    DISCOVERY_RUN_STATUS_CHECK,
    DISCOVERY_RUN_STATUS_VALUES,
    Camera,
    NvrCredential,
    NvrDevice,
    NvrDiscoveryRun,
)
from sbozor_core.models.ops import AUDIT_BUSINESS_DATE_EXPR, AuditLog

__all__ = [
    "AUDIT_BUSINESS_DATE_EXPR",
    "CAMERA_STATUS_CHECK",
    "CAMERA_STATUS_VALUES",
    "DISCOVERY_RUN_ACTIVE_STATUSES",
    "DISCOVERY_RUN_STATUS_CHECK",
    "DISCOVERY_RUN_STATUS_VALUES",
    "LOCALE_CHECK",
    "LOCALE_VALUES",
    "NAMING_CONVENTION",
    "OPEN_WEEKDAYS_CHECK",
    "ROLES_SUBSET_CHECK",
    "ROLE_VALUES",
    "STALL_CODE_SORT_EXPR",
    "STALL_STATUS_CHECK",
    "STALL_STATUS_VALUES",
    "TARIFF_BUSINESS_DATE_EXPR",
    "AuditLog",
    "Base",
    "Camera",
    "Market",
    "MarketCalendarException",
    "MarketProfile",
    "NvrCredential",
    "NvrDevice",
    "NvrDiscoveryRun",
    "RefreshToken",
    "Stall",
    "StallAssignment",
    "StallCategory",
    "StallCategoryPeriod",
    "StallCodeRegistry",
    "Tariff",
    "TenantMixin",
    "TimestampMixin",
    "User",
    "UserMarketRole",
    "Vendor",
    "Zone",
    "market_fk_column",
    "uuid_pk",
]
