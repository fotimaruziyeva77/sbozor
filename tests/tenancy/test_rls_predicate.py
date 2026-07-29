"""RLS predikatining XULQI — fail-closed va cross-tenant izolyatsiya.

=============================================================================
BU FAYLNING SABABI BITTA O'LCHANGAN XATO (RESEARCH Pitfall 1):

`set_config('app.market_id', X, true)` tranzaksiya tugagach GUC'ni `NULL`
ga QAYTARMAYDI — u bo'sh satr (`''`) bo'lib qoladi va ULANISH UMRI davomida
shunday turadi. Puldagi ulanish keyingi so'rovga o'tganda `NULLIF` siz
policy predikati `''::uuid` ni hisoblamoqchi bo'ladi va butun so'rov
`invalid input syntax for type uuid: ""` bilan yiqiladi.

Shuning uchun bu yerdagi testlar ATAYIN `app_engine` (pool_size=1,
max_overflow=0) ustida ishlaydi: bitta ulanish qayta-qayta ishlatiladi va
GUC sizishi maksimal darajada ochib beriladi. Shu holatda o'tgan test
prod'da ham o'tadi.

DIQQAT — fail-closed testlari `pytest.raises` BILAN EMAS. Ular aynan
XATO BO'LMASLIGINI va 0 QATOR qaytishini tasdiqlaydi. `pytest.raises` bilan
yozilgan test noto'g'ri xulqni "kutilgan" deb muhrlab qo'yardi.
=============================================================================
"""

from __future__ import annotations

import pytest
from fixtures import TenantSessionFactory
from fixtures.two_markets import ROLES_PER_MARKET, TwoMarketSeed
from sbozor_core.db import make_sessionmaker
from sbozor_core.tenancy import set_tenant_context
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

pytestmark = pytest.mark.tenancy

COUNT_ROLES = text("SELECT count(*) FROM user_market_roles")
COUNT_MARKETS = text("SELECT count(*) FROM markets")


async def test_no_tenant_context_returns_zero_rows_without_error(
    app_engine: AsyncEngine, two_markets: TwoMarketSeed
) -> None:
    """Kontekstsiz so'rov: 0 qator, XATO YO'Q (fail-closed).

    Seed'da 6 ta a'zolik qatori bor, ya'ni 0 javobi "jadval bo'sh" degani
    emas — u aynan policy ishlaganini bildiradi.
    """
    async with app_engine.connect() as conn:
        roles = (await conn.execute(COUNT_ROLES)).scalar_one()
        markets = (await conn.execute(COUNT_MARKETS)).scalar_one()

    assert roles == 0, "tenant kontekstisiz a'zolik qatorlari ko'rinmoqda — policy ishlamayapti"
    assert markets == 0, "tenant kontekstisiz bozorlar ko'rinmoqda — policy ishlamayapti"


async def test_same_connection_after_commit_is_still_fail_closed(
    app_engine: AsyncEngine, two_markets: TwoMarketSeed
) -> None:
    """`NULLIF` shaklining ASOSIY isboti.

    Bir xil ulanishda: kontekst o'rnatiladi -> COMMIT -> yana so'rov.
    COMMIT dan keyin GUC `NULL` emas, `''` bo'lib qoladi. `NULLIF` siz
    policy shu yerda `InvalidTextRepresentationError` bilan yiqilardi;
    `NULLIF` bilan esa jimgina 0 qator qaytadi.

    Testning O'ZI istisno ko'tarmasligi — asosiy tasdiq.
    """
    async with app_engine.connect() as conn:
        async with conn.begin():
            await conn.execute(
                text("SELECT set_config('app.market_id', :market_id, true)"),
                {"market_id": str(two_markets.market_a.id)},
            )
            inside = (await conn.execute(COUNT_ROLES)).scalar_one()
            assert inside == ROLES_PER_MARKET

        # Tranzaksiya yopildi, ulanish esa O'SHA (pool_size=1).
        after_commit = (await conn.execute(COUNT_ROLES)).scalar_one()
        assert after_commit == 0, (
            "COMMIT dan keyin oldingi bozorning qatorlari hali ham ko'rinmoqda — "
            "GUC tranzaksiya-lokal emas"
        )

        # Ikkinchi marta ham: xato to'planib qolmaydi.
        again = (await conn.execute(COUNT_ROLES)).scalar_one()
        assert again == 0


async def test_context_a_sees_only_market_a(
    tenant_session: TenantSessionFactory, two_markets: TwoMarketSeed
) -> None:
    """A konteksti ostida faqat A qatorlari ko'rinadi."""
    async with tenant_session(two_markets.market_a.id) as session:
        rows = (
            (await session.execute(text("SELECT DISTINCT market_id FROM user_market_roles")))
            .scalars()
            .all()
        )
        market_rows = (await session.execute(text("SELECT id FROM markets"))).scalars().all()

    assert list(rows) == [two_markets.market_a.id]
    assert list(market_rows) == [two_markets.market_a.id]


async def test_context_b_sees_only_market_b(
    tenant_session: TenantSessionFactory, two_markets: TwoMarketSeed
) -> None:
    """B konteksti ostida faqat B qatorlari — A butunlay ko'rinmaydi."""
    async with tenant_session(two_markets.market_b.id) as session:
        rows = (
            (await session.execute(text("SELECT DISTINCT market_id FROM user_market_roles")))
            .scalars()
            .all()
        )

    assert list(rows) == [two_markets.market_b.id]
    assert two_markets.market_a.id not in rows


async def test_insert_into_other_market_violates_with_check(
    tenant_session: TenantSessionFactory, two_markets: TwoMarketSeed
) -> None:
    """A konteksti ostida B ga YOZISH rad etiladi (`WITH CHECK`, T-01-27).

    Faqat o'qish emas, yozish ham qamralgan bo'lishi shart: aks holda
    A bozori kassiri B bozoriga qator kirita olardi va uni keyin ko'ra
    olmasdi — ya'ni jimgina ma'lumot buzilishi.
    """
    from sqlalchemy.exc import DBAPIError

    with pytest.raises(DBAPIError) as excinfo:
        async with tenant_session(two_markets.market_a.id) as session:
            await session.execute(
                text(
                    "INSERT INTO user_market_roles (market_id, user_id, roles) "
                    "VALUES (:market_id, :user_id, ARRAY['cashier'])"
                ),
                {
                    "market_id": str(two_markets.market_b.id),
                    "user_id": str(two_markets.market_a.admin_user_id),
                },
            )

    assert "row-level security" in str(excinfo.value).lower()


async def test_update_cannot_move_row_to_other_market(
    tenant_session: TenantSessionFactory, two_markets: TwoMarketSeed
) -> None:
    """A qatorini B ga KO'CHIRIB bo'lmaydi (`WITH CHECK` UPDATE tomonida)."""
    from sqlalchemy.exc import DBAPIError

    with pytest.raises(DBAPIError) as excinfo:
        async with tenant_session(two_markets.market_a.id) as session:
            await session.execute(
                text("UPDATE user_market_roles SET market_id = :target WHERE id = :role_id"),
                {
                    "target": str(two_markets.market_b.id),
                    "role_id": str(two_markets.market_a.admin_role_id),
                },
            )

    assert "row-level security" in str(excinfo.value).lower()


async def test_update_outside_context_silently_affects_nothing(
    app_engine: AsyncEngine, two_markets: TwoMarketSeed
) -> None:
    """Kontekstsiz UPDATE 0 qatorga tegadi va XATO bermaydi.

    Bu fail-closed'ning yozish tomoni: qatorlar ko'rinmaydi, shuning uchun
    yangilanmaydi ham. Ilova kodi shu sababli `rowcount` ni tekshirishi
    kerak — "xato bo'lmadi" hali "o'zgardi" degani emas (Pitfall 4 bilan
    bir xil sinf).
    """
    async with app_engine.connect() as conn, conn.begin():
        result = await conn.execute(
            text("UPDATE user_market_roles SET roles = ARRAY['cashier'] WHERE id = :role_id"),
            {"role_id": str(two_markets.market_a.admin_role_id)},
        )
        assert result.rowcount == 0


async def test_set_tenant_context_requires_open_transaction(app_engine: AsyncEngine) -> None:
    """`set_tenant_context` tranzaksiyasiz `RuntimeError` beradi (T-01-17).

    Autocommit rejimida har operator o'z tranzaksiyasida ketadi, ya'ni
    `set_config(..., is_local=true)` qiymati DARHOL yo'qoladi va keyingi
    so'rov kontekstsiz — jimgina 0 qator bilan — bajariladi.
    """
    sessionmaker = make_sessionmaker(app_engine)
    async with sessionmaker() as session:
        with pytest.raises(RuntimeError, match="tranzaksiya"):
            await set_tenant_context(
                session,
                market_id=None,
                actor_id=None,
                request_id="pytest",
            )
