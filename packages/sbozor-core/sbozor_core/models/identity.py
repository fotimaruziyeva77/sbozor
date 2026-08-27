"""Identifikatsiya sxemasi: `markets`, `users`, `user_market_roles`, `refresh_tokens`.

=============================================================================
ASOSIY ARXITEKTURA QARORI — IDENTIFIKATSIYA A'ZOLIKDAN AJRATILGAN:

  `users`             GLOBAL   — `market_id` YO'Q, RLS YO'Q, app-rolga GRANT YO'Q
  `user_market_roles` TENANT   — `market_id` bor, RLS ENABLE+FORCE+policy
  `refresh_tokens`    TENANT   — bir xil
  `markets`           MAXSUS   — tenant chegarasining O'ZI, policy `id` bo'yicha

Sabab (RESEARCH Pitfall 3, empirik): login paytida `app.market_id` hali
noma'lum. Agar `users` tenant-policy ostida bo'lsa, hech kim hech qachon
kira olmaydi. Shuning uchun login yo'li faqat `migrations/entities/
functions.py` dagi to'rt `SECURITY DEFINER` funksiya orqali o'tadi.

D-05: bitta foydalanuvchi = bitta bozor + ROLLAR TO'PLAMI. Sxema
ko'p-bozorga tayyor (bir foydalanuvchi bir necha `user_market_roles`
qatoriga ega bo'lishi mumkin), MVP UI esa bitta bozor biriktiradi.
=============================================================================
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import UUID as PgUuid
from sqlalchemy.orm import Mapped, mapped_column

from sbozor_core.enums import Locale, Role
from sbozor_core.models.base import Base, TenantMixin, TimestampMixin, uuid_pk

__all__ = [
    "LOCALE_CHECK",
    "LOCALE_VALUES",
    "ROLES_SUBSET_CHECK",
    "ROLE_VALUES",
    "Market",
    "RefreshToken",
    "User",
    "UserMarketRole",
]

ROLE_VALUES: tuple[str, ...] = tuple(role.value for role in Role)
LOCALE_VALUES: tuple[str, ...] = tuple(locale.value for locale in Locale)


def _quoted(values: Iterable[str]) -> str:
    """SQL literal ro'yxati. Qiymatlar `StrEnum` a'zolari — tashqi kirish emas."""
    return ", ".join(f"'{value}'" for value in values)


ROLES_SUBSET_CHECK = f"roles <@ ARRAY[{_quoted(ROLE_VALUES)}]::text[]"
"""`user_market_roles.roles` faqat ma'lum rollardan iborat bo'lishi shart.

Ifoda `sbozor_core.enums.Role` dan HOSIL QILINADI, qo'lda ko'chirilmaydi.
Enum o'zgarib migratsiya unutilsa, `tests/tenancy/test_meta.py::
test_role_check_constraint_matches_enum` bazadagi amaldagi konstraytni
enum bilan solishtirib darvozani yopadi.
"""

LOCALE_CHECK = f"locale IN ({_quoted(LOCALE_VALUES)})"
"""D-13/D-15: til foydalanuvchi profilida, uchtasidan biri (bir manba)."""


class Market(Base, TimestampMixin):
    """Bozor — tenant chegarasining o'zi."""

    __tablename__ = "markets"

    id: Mapped[UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(Text(), nullable=False)
    # Pitfall 6: ustun 1-fazadayoq sxemada bo'lishi kerak. `business_date`
    # generated column 2-fazada shu ustunga tayanadi (hozircha literal
    # 'Asia/Tashkent' ishlatiladi — generated ifoda IMMUTABLE bo'lishi shart,
    # boshqa ustunga havola qila olmaydi).
    timezone: Mapped[str] = mapped_column(
        Text(), nullable=False, server_default=text("'Asia/Tashkent'")
    )
    is_active: Mapped[bool] = mapped_column(nullable=False, server_default=text("true"))


class User(Base, TimestampMixin):
    """Global identifikatsiya qatori — `market_id` ATAYIN YO'Q."""

    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("phone_e164", name="uq_users_phone_e164"),
        # DIQQAT: `ck` konvensiyasi `ck_%(table_name)s_%(constraint_name)s`,
        # ya'ni bu yerga QISQA mantiqiy nom beriladi va yakuniy nom
        # `ck_users_locale_allowed` bo'ladi. To'liq nom yozilsa u ikki marta
        # prefikslanadi (`ck_users_ck_users_...`).
        CheckConstraint(LOCALE_CHECK, name="locale_allowed"),
    )

    id: Mapped[UUID] = uuid_pk()
    # D-01: telefon — YAGONA login identifikatori. `email`/`username` ustuni
    # ATAYIN YARATILMAYDI. Normalizatsiya chegarada
    # (`sbozor_core.phone.normalize_phone`) bajariladi, aks holda bir odam
    # ikki xil yozuvda ("+998901234567" va "901234567") ikki hisob oladi.
    phone_e164: Mapped[str] = mapped_column(Text(), nullable=False)
    password_hash: Mapped[str] = mapped_column(Text(), nullable=False)
    full_name: Mapped[str | None] = mapped_column(Text(), nullable=True)
    locale: Mapped[str] = mapped_column(Text(), nullable=False, server_default=text("'uz-Latn'"))
    is_active: Mapped[bool] = mapped_column(nullable=False, server_default=text("true"))
    # D-02: admin bergan vaqtinchalik parol birinchi kirishda almashtiriladi.
    must_change_password: Mapped[bool] = mapped_column(nullable=False, server_default=text("false"))
    # D-06: platforma admini bozor TANLAB kiradi — bu bayroq RLS bypass
    # bermaydi, u faqat `auth_list_markets()` oqimini ochadi.
    is_platform_admin: Mapped[bool] = mapped_column(nullable=False, server_default=text("false"))


class UserMarketRole(Base, TenantMixin, TimestampMixin):
    """Bozordagi a'zolik + rollar to'plami (D-05)."""

    __tablename__ = "user_market_roles"
    __table_args__ = (
        ForeignKeyConstraint(
            ["market_id"], ["markets.id"], name="fk_user_market_roles_market_id_markets"
        ),
        ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_user_market_roles_user_id_users",
            ondelete="CASCADE",
        ),
        # Bitta bozorda bitta foydalanuvchi — bitta a'zolik qatori.
        # Bu ayni paytda `(market_id, user_id)` indeksining o'zi ham.
        UniqueConstraint("market_id", "user_id", name="uq_user_market_roles_market_id_user_id"),
        # COMPOSITE FK MAQSADI UCHUN: keyingi fazalardagi jadvallar
        # `(market_id, id)` ga havola qiladi va shu bilan cross-tenant
        # bog'lanish STRUKTURAVIY imkonsiz bo'ladi (T-01-26).
        UniqueConstraint("market_id", "id", name="uq_user_market_roles_market_id_id"),
        # Qisqa mantiqiy nomlar — `ck` konvensiyasi prefiksni o'zi qo'shadi.
        CheckConstraint(ROLES_SUBSET_CHECK, name="roles_allowed"),
        CheckConstraint("cardinality(roles) > 0", name="roles_not_empty"),
    )

    id: Mapped[UUID] = uuid_pk()
    user_id: Mapped[UUID] = mapped_column(PgUuid(as_uuid=True), nullable=False)
    roles: Mapped[list[str]] = mapped_column(ARRAY(Text()), nullable=False)


class RefreshToken(Base, TenantMixin):
    """Refresh token rotatsiyasi va reuse-detect uchun (Pattern 3).

    `updated_at` ATAYIN YO'Q: token qatori o'zgarmas hodisa yozuvi —
    u faqat bekor qilinadi (`revoked_at`) va almashtiriladi
    (`replaced_by_jti`), tahrir qilinmaydi.
    """

    __tablename__ = "refresh_tokens"
    __table_args__ = (
        ForeignKeyConstraint(
            ["market_id"], ["markets.id"], name="fk_refresh_tokens_market_id_markets"
        ),
        ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_refresh_tokens_user_id_users",
            ondelete="CASCADE",
        ),
        # `jti` — GLOBAL qidiruv kaliti: kelayotgan cookie'da bozor hali
        # ma'lum emas, shuning uchun bu yagona indeks `market_id` bilan
        # boshlanmaydi (meta-testda aniq istisno sifatida qayd etilgan).
        UniqueConstraint("jti", name="uq_refresh_tokens_jti"),
        UniqueConstraint("market_id", "id", name="uq_refresh_tokens_market_id_id"),
        Index(
            "ix_refresh_tokens_market_id_user_id_expires_at", "market_id", "user_id", "expires_at"
        ),
    )

    id: Mapped[UUID] = uuid_pk()
    user_id: Mapped[UUID] = mapped_column(PgUuid(as_uuid=True), nullable=False)
    jti: Mapped[str] = mapped_column(Text(), nullable=False)
    # Reuse aniqlanganda BUTUN oila bekor qilinadi — o'g'irlangan token
    # 30 kun emas, keyingi ishlatilishida o'ladi.
    family_id: Mapped[UUID] = mapped_column(PgUuid(as_uuid=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    replaced_by_jti: Mapped[str | None] = mapped_column(Text(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
