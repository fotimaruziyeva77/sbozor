"""SQLAlchemy 2.0 deklarativ bazasi va umumiy mixinlar.

Uch qat'iy qoida bu yerda qulflanadi:

1. **Vaqt — har doim `timestamptz`.** Naive vaqt TAQIQLANGAN: konteynerlar
   UTC'da ishlaydi, biznes-kun esa `Asia/Tashkent` bo'yicha yopiladi
   (Pitfall 6). Mahalliy 00:00-04:59 oralig'idagi har bir yozuv naive
   sanada OLDINGI kunga tushadi — bu aynan mahsulot bartaraf etadigan
   rekonsiliatsiya xatosi.
2. **Birlamchi kalit — `uuidv7()`.** PostgreSQL 18 native funksiyasi:
   vaqt bo'yicha tartiblangan UUID, ya'ni B-tree fragmentatsiyasi kam
   (`uuidv4` bilan har insert indeksning tasodifiy joyiga tushadi).
   Kalit DB tomonda hosil bo'ladi — ilova ID o'ylab topmaydi.
3. **Konstrayt nomlari — konvensiya bo'yicha.** `MetaData(naming_convention=)`
   busiz `downgrade()` va autogenerate anonim `CHECK`/`UNIQUE` nomlarini
   topa olmaydi.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, MetaData, func, text
from sqlalchemy.dialects.postgresql import UUID as PgUuid
from sqlalchemy.orm import DeclarativeBase, Mapped, MappedColumn, mapped_column

__all__ = [
    "NAMING_CONVENTION",
    "Base",
    "TenantMixin",
    "TimestampMixin",
    "market_fk_column",
    "uuid_pk",
]

NAMING_CONVENTION: dict[str, str] = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_N_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Barcha SBOZOR modellari uchun deklarativ baza."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def uuid_pk() -> MappedColumn[UUID]:
    """Vaqt-tartiblangan birlamchi kalit (`uuidv7()`, PG18 native)."""
    return mapped_column(
        PgUuid(as_uuid=True),
        primary_key=True,
        server_default=text("uuidv7()"),
    )


def market_fk_column() -> MappedColumn[UUID]:
    """`market_id` ustuni — tenant kaliti.

    FK `markets(id)` ga ATAYIN shu yerda emas, konkret modelning
    `__table_args__` ida e'lon qilinadi: keyingi fazalarda ba'zi jadvallar
    `(market_id, <parent_id>)` COMPOSITE FK ishlatadi va bitta ustunda
    ikkita FK bo'lishi keraksiz indeks/konstraytga olib keladi.
    """
    return mapped_column(PgUuid(as_uuid=True), nullable=False)


class TimestampMixin:
    """`created_at` / `updated_at` — ikkalasi ham `timestamptz`."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class TenantMixin:
    """Tenant-scoped jadval uchun `market_id`.

    Bu mixin'ga EGA BO'LMAGAN har bir jadval `sbozor_core.schema_contract`
    dagi `GLOBAL_TABLES` reyestrida bo'lishi SHART — aks holda
    `tests/tenancy/test_meta.py::test_every_table_is_tenant_scoped`
    darvozani yopadi.
    """

    market_id: Mapped[UUID] = market_fk_column()
