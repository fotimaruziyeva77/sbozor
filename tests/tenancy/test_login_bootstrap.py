"""Login bootstrap — RLS ostida kirish qanday ishlaydi (Pattern 2 / Pitfall 3).

Bu faza uchun eng katta arxitektura qopqoni: login paytida `app.market_id`
HALI NOMA'LUM. Agar identifikatsiya ma'lumoti tenant-policy ostida bo'lsa,
hech kim hech qachon kira olmaydi — va bu faqat integratsiya testi
yozilgunga qadar ko'rinmaydi, chunki unit testlar RLS'siz ishlaydi.

Shu sababli bu fayl login yo'lini UCHDAN-UCHIGA `sbozor_app` roli bilan
sinaydi:

  1. `users` ga to'g'ridan-to'g'ri borish IMKONSIZ (`permission denied`);
  2. `auth_find_login()` esa tenant kontekstisiz ISHLAYDI;
  3. bozor tanlangach faqat o'sha bozor ko'rinadi — platforma admini uchun
     ham (D-06: bypass yo'li yo'q).
"""

from __future__ import annotations

import psycopg
import pytest
from fixtures import TenantSessionFactory
from fixtures.two_markets import ROLES_PER_MARKET, TwoMarketSeed
from psycopg import Connection
from psycopg.rows import TupleRow
from sqlalchemy import text

from migrations.entities.functions import ALL_FUNCTIONS, GRANT_SIGNATURES

pytestmark = pytest.mark.tenancy


def test_app_role_cannot_select_users(sync_app_conn: Connection[TupleRow], migrated: None) -> None:
    """`sbozor_app` `users` ni umuman o'qiy olmaydi (T-01-25).

    Bu ATAYIN: global identifikatsiya jadvaliga ORM orqali tasodifan
    `select(User)` yozish imkonsiz bo'lishi kerak. Yagona yo'l — pastdagi
    tor `SECURITY DEFINER` funksiyalari.
    """
    with pytest.raises(psycopg.errors.InsufficientPrivilege) as excinfo:
        sync_app_conn.execute("SELECT count(*) FROM users")

    assert "users" in str(excinfo.value)


def test_auth_find_login_works_without_tenant_context(
    sync_app_conn: Connection[TupleRow], two_markets: TwoMarketSeed
) -> None:
    """Tenant kontekstisiz login qatori topiladi — login yo'li ochiq."""
    rows = sync_app_conn.execute(
        "SELECT user_id, password_hash, is_active, is_platform_admin FROM auth_find_login(%s)",
        (two_markets.market_a.admin_phone,),
    ).fetchall()

    assert len(rows) == 1, "auth_find_login aynan bitta qator qaytarishi kerak"
    user_id, password_hash, is_active, is_platform_admin = rows[0]
    assert user_id == two_markets.market_a.admin_user_id
    assert password_hash, "parol hash'i qaytmadi — parolni tekshirib bo'lmaydi"
    assert is_active is True
    assert is_platform_admin is False


def test_auth_find_login_unknown_phone_returns_zero_rows(
    sync_app_conn: Connection[TupleRow], two_markets: TwoMarketSeed
) -> None:
    """Noma'lum telefon: 0 qator, XATO EMAS.

    Xato qaytarilsa u foydalanuvchi sanashning yon kanali bo'lardi
    ("bu raqam bormi?"). Chaqiruvchi 0 qatorda `dummy_verify()` bilan bir
    xil vaqt sarflaydi (T-01-15).
    """
    rows = sync_app_conn.execute(
        "SELECT user_id FROM auth_find_login(%s)", ("+998900000000",)
    ).fetchall()
    assert rows == []


def test_auth_memberships_returns_all_markets_without_context(
    sync_app_conn: Connection[TupleRow], two_markets: TwoMarketSeed
) -> None:
    """Platforma adminining IKKALA a'zoligi tenant kontekstisiz ko'rinadi.

    Bu bozor tanlash ekranining manbai: kontekst hali o'rnatilmagan, ya'ni
    oddiy `SELECT` bu yerda 0 qator berardi.
    """
    rows = sync_app_conn.execute(
        "SELECT market_id, market_name, roles FROM auth_memberships(%s)",
        (two_markets.platform_admin_id,),
    ).fetchall()

    assert {row[0] for row in rows} == {two_markets.market_a.id, two_markets.market_b.id}
    assert all(row[2] == ["platform_admin"] for row in rows)


def test_auth_memberships_of_market_admin_is_single_market(
    sync_app_conn: Connection[TupleRow], two_markets: TwoMarketSeed
) -> None:
    """Oddiy bozor admini faqat O'Z bozorini ko'radi (D-05)."""
    rows = sync_app_conn.execute(
        "SELECT market_id FROM auth_memberships(%s)",
        (two_markets.market_a.admin_user_id,),
    ).fetchall()

    assert [row[0] for row in rows] == [two_markets.market_a.id]


def test_auth_list_markets_is_readable_without_context(
    sync_app_conn: Connection[TupleRow], two_markets: TwoMarketSeed
) -> None:
    """`auth_list_markets()` — platforma admini oqimidagi yagona global ro'yxat (D-06)."""
    rows = sync_app_conn.execute(
        "SELECT market_id, market_name, is_active FROM auth_list_markets()"
    ).fetchall()

    market_ids = {row[0] for row in rows}
    assert {two_markets.market_a.id, two_markets.market_b.id} <= market_ids


def test_auth_user_state_returns_block_flags(
    sync_app_conn: Connection[TupleRow], two_markets: TwoMarketSeed
) -> None:
    """`auth_user_state()` — kesh promahida DB'ga tushish yo'li (D-08)."""
    rows = sync_app_conn.execute(
        "SELECT is_active, must_change_password, locale FROM auth_user_state(%s)",
        (two_markets.market_a.cashier_user_id,),
    ).fetchall()

    assert len(rows) == 1
    is_active, must_change_password, locale = rows[0]
    assert is_active is True
    assert must_change_password is False
    assert locale == "uz-Latn"


async def test_platform_admin_sees_only_the_selected_market(
    tenant_session: TenantSessionFactory, two_markets: TwoMarketSeed
) -> None:
    """D-06 NING ASOSIY ISBOTI — bozor tanlash bypass emas.

    Platforma admini ikkala bozorga a'zo, lekin ilova ulanishi baribir
    `sbozor_app` — ya'ni u tanlagan bozorining oddiy tenant policy'siga
    bo'ysunadi. A ni tanlaganda B umuman ko'rinmaydi va aksincha.
    """
    for selected, other in (
        (two_markets.market_a, two_markets.market_b),
        (two_markets.market_b, two_markets.market_a),
    ):
        async with tenant_session(selected.id, two_markets.platform_admin_id) as session:
            visible = (
                (await session.execute(text("SELECT DISTINCT market_id FROM user_market_roles")))
                .scalars()
                .all()
            )
            total = (
                await session.execute(text("SELECT count(*) FROM user_market_roles"))
            ).scalar_one()

        assert list(visible) == [selected.id], (
            f"{selected.name} tanlangan, lekin ko'ringan bozorlar: {visible}"
        )
        assert other.id not in visible
        assert total == ROLES_PER_MARKET


def test_definer_functions_are_executable_by_app_role(
    sync_app_conn: Connection[TupleRow], migrated: None
) -> None:
    """`sbozor_app` to'rt funksiyaning HAMMASINI chaqira oladi.

    `GRANT_SIGNATURES` ro'yxati `ALL_FUNCTIONS` dan ajralib qolsa, funksiya
    yaratiladi-yu, ilova uni chaqira olmaydi — va login sahifasi
    `permission denied` bilan yiqiladi.
    """
    assert len(GRANT_SIGNATURES) == len(ALL_FUNCTIONS), (
        "GRANT_SIGNATURES va ALL_FUNCTIONS uzunligi mos emas — "
        "yangi funksiyaga GRANT berilmagan bo'lishi mumkin"
    )

    for signature in GRANT_SIGNATURES:
        row = sync_app_conn.execute(
            "SELECT has_function_privilege('sbozor_app', %s, 'EXECUTE')", (signature,)
        ).fetchone()
        assert row is not None
        assert row[0] is True, f"{signature}: sbozor_app EXECUTE huquqiga ega emas"


def test_definer_functions_are_not_granted_to_public(
    sync_app_conn: Connection[TupleRow], migrated: None
) -> None:
    """`PUBLIC` dan `REVOKE ALL` bajarilgan.

    Postgres yangi funksiyaga `EXECUTE TO PUBLIC` ni STANDART beradi.
    REVOKE unutilsa, global o'qish yuzasi bazadagi HAR QANDAY rol uchun
    ochiq bo'lib qolardi. `proacl` da `PUBLIC` grant'i `=X/...` shaklida
    ko'rinadi (chapda rol nomi yo'q).
    """
    rows = sync_app_conn.execute(
        "SELECT p.proname, coalesce(p.proacl::text[], ARRAY[]::text[]) FROM pg_proc p "
        "JOIN pg_namespace n ON n.oid = p.pronamespace "
        "WHERE n.nspname = 'public' AND p.prosecdef"
    ).fetchall()
    assert rows, "birorta SECURITY DEFINER funksiya topilmadi"

    for name, acl in rows:
        public_grants = [item for item in acl if item.startswith("=")]
        assert not public_grants, (
            f"{name}: PUBLIC ga grant qolgan ({public_grants}) — "
            "`REVOKE ALL ON FUNCTION ... FROM PUBLIC` bajarilmagan"
        )
