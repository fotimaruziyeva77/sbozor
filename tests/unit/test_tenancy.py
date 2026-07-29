"""`sbozor_core.tenancy` — GUC mexanikasi va ikkinchi qatlam filtri.

Bu testlar BAZASIZ ishlaydi: ular SQL MATNINI va chaqiruv shartlarini
tekshiradi. Haqiqiy izolyatsiya isboti (cross-tenant matritsa, RLS policy'lar)
01-04 va 01-05 rejalarida, haqiqiy Postgres ustida quriladi.

Qamralgan tahdid: T-01-17 — tenant GUC'ining pul orqali sizishi.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from uuid import UUID, uuid4

import pytest
from sbozor_core.db import make_engine
from sbozor_core.enums import ActorKind
from sbozor_core.tenancy import (
    ACTOR_ID_GUC,
    ACTOR_KIND_GUC,
    MARKET_ID_GUC,
    REQUEST_ID_GUC,
    SET_TENANT_CONTEXT,
    TENANT_GUCS,
    TenantScopedRepository,
    set_tenant_context,
)
from sqlalchemy import Uuid, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Hech qachon ulanmaydigan manzil: engine dangasa, `create_async_engine`
# o'zi tarmoqqa chiqmaydi. Shu sababli bu testlar Docker'siz ham ishlaydi.
OFFLINE_URL = "postgresql+asyncpg://unit:test@127.0.0.1:1/none"


class _Base(DeclarativeBase):
    """Faqat shu fayl uchun alohida registry — ilova metadata'siga tegmaydi."""


class _Stall(_Base):
    __tablename__ = "unit_test_stalls"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    market_id: Mapped[UUID] = mapped_column(Uuid)


class _GlobalThing(_Base):
    """`market_id` ustunisiz jadval — `GLOBAL_TABLES` dagilarga o'xshash."""

    __tablename__ = "unit_test_global_things"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)


@pytest.fixture
async def offline_session() -> AsyncIterator[AsyncSession]:
    engine = make_engine(OFFLINE_URL)
    async with AsyncSession(bind=engine) as session:
        yield session
    await engine.dispose()


# --------------------------------------------------------------------------
# SQL matni
# --------------------------------------------------------------------------


def test_uses_set_config_not_set_local() -> None:
    """`SET LOCAL app.x = :param` Postgres'da sintaksis xatosi beradi."""
    sql = str(SET_TENANT_CONTEXT)
    assert "set_config('app.market_id'" in sql
    assert "SET LOCAL" not in sql.upper()


def test_sets_all_four_gucs_in_one_statement() -> None:
    sql = str(SET_TENANT_CONTEXT)
    for guc in (MARKET_ID_GUC, ACTOR_ID_GUC, REQUEST_ID_GUC, ACTOR_KIND_GUC):
        assert f"set_config('{guc}'" in sql, f"{guc} o'rnatilmagan"


def test_guc_values_are_transaction_local() -> None:
    """Uchinchi argument `true` — commit'dan keyin qiymat tark etiladi."""
    assert str(SET_TENANT_CONTEXT).count(", true)") == len(TENANT_GUCS)


def test_tenant_guc_names_are_exported() -> None:
    assert TENANT_GUCS == (
        "app.market_id",
        "app.actor_id",
        "app.request_id",
        "app.actor_kind",
    )


# --------------------------------------------------------------------------
# T-01-17: tranzaksiya majburiyati
# --------------------------------------------------------------------------


async def test_set_tenant_context_requires_open_transaction(
    offline_session: AsyncSession,
) -> None:
    """Autocommit'da `set_config(..., true)` qiymatni DARHOL yo'qotadi."""
    assert offline_session.in_transaction() is False

    with pytest.raises(RuntimeError, match="tranzaksiya"):
        await set_tenant_context(
            offline_session,
            market_id=uuid4(),
            actor_id=uuid4(),
            request_id="req-1",
        )


async def test_set_tenant_context_error_names_the_fix(
    offline_session: AsyncSession,
) -> None:
    with pytest.raises(RuntimeError, match=r"session\.begin"):
        await set_tenant_context(
            offline_session,
            market_id=uuid4(),
            actor_id=uuid4(),
            request_id="req-1",
            actor_kind=ActorKind.SYSTEM,
        )


# --------------------------------------------------------------------------
# Ikkinchi qatlam: TenantScopedRepository
# --------------------------------------------------------------------------


def _repo(session: AsyncSession, market_id: UUID) -> TenantScopedRepository:
    return TenantScopedRepository(session=session, market_id=market_id)


def test_scoped_adds_market_predicate(offline_session: AsyncSession) -> None:
    market_id = uuid4()
    stmt = _repo(offline_session, market_id).scoped(select(_Stall))

    assert stmt.whereclause is not None
    assert "unit_test_stalls.market_id = " in str(stmt)
    assert market_id in stmt.compile().params.values()


def test_scoped_keeps_existing_predicates(offline_session: AsyncSession) -> None:
    market_id = uuid4()
    stall_id = uuid4()
    stmt = _repo(offline_session, market_id).scoped(select(_Stall).where(_Stall.id == stall_id))

    rendered = str(stmt)
    assert "unit_test_stalls.id = " in rendered
    assert "unit_test_stalls.market_id = " in rendered


def test_scoped_works_on_column_selects(offline_session: AsyncSession) -> None:
    stmt = _repo(offline_session, uuid4()).scoped(select(_Stall.id))
    assert "unit_test_stalls.market_id = " in str(stmt)


def test_scoped_rejects_model_without_market_id(offline_session: AsyncSession) -> None:
    """Jimgina filtrsiz qaytish — aynan oldini olinayotgan nosozlik."""
    with pytest.raises(TypeError, match="market_id"):
        _repo(offline_session, uuid4()).scoped(select(_GlobalThing))


def test_scoped_rejects_entityless_select(offline_session: AsyncSession) -> None:
    with pytest.raises(TypeError):
        _repo(offline_session, uuid4()).scoped(select(func.count()))
