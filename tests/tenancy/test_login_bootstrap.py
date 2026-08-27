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

from uuid import uuid4

import psycopg
import pytest
from fixtures import TenantSessionFactory
from fixtures.two_markets import ROLES_PER_MARKET, TwoMarketSeed
from psycopg import Connection
from psycopg.rows import TupleRow
from sqlalchemy import text

from migrations.entities.functions import (
    ALL_FUNCTIONS,
    AUTH_SUPPORT_FUNCTIONS,
    AUTH_SUPPORT_GRANT_SIGNATURES,
    GRANT_SIGNATURES,
    PLATFORM_AUDIT_FUNCTIONS,
    PLATFORM_AUDIT_GRANT_SIGNATURES,
    USER_ADMIN_FUNCTIONS,
    USER_ADMIN_GRANT_SIGNATURES,
)

pytestmark = pytest.mark.tenancy

# (funksiyalar ro'yxati, `GRANT` imzolari) juftliklari. Yangi migratsiya
# yangi juftlik qo'shadi va u AVTOMATIK ravishda quyidagi ikkala darvozadan
# o'tadi — ro'yxat qo'lda ikki joyda yuritilmaydi.
DEFINER_FUNCTION_SETS = (
    (ALL_FUNCTIONS, GRANT_SIGNATURES),
    (AUTH_SUPPORT_FUNCTIONS, AUTH_SUPPORT_GRANT_SIGNATURES),
    (USER_ADMIN_FUNCTIONS, USER_ADMIN_GRANT_SIGNATURES),
    (PLATFORM_AUDIT_FUNCTIONS, PLATFORM_AUDIT_GRANT_SIGNATURES),
)


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


# ===========================================================================
# PLATFORMA-GLOBAL AUDIT (Gap 5, 0005) — `market_id IS NULL` qatorlar
# ===========================================================================


def _insert_platform_audit_row(conn: Connection[TupleRow], marker: str) -> None:
    """`login_failed` shaklidagi platforma-global audit qatorini yozadi.

    ILOVA ROLI bilan, ataylab: `audit_append` policy'si `FOR INSERT WITH
    CHECK (true)` va `TO` bandisiz, ya'ni `sbozor_app` bunday qatorni yoza
    oladi — mahsulotda `login_failed` aynan shu yo'l bilan yoziladi (01-06).
    Yozish tomonini owner bilan qilib qo'yish testni haqiqiy oqimdan
    uzoqlashtirardi.

    `id` va `business_date` BERILMAYDI: birinchisi `IDENTITY ALWAYS`,
    ikkinchisi generated STORED ustun.
    """
    conn.execute(
        "INSERT INTO audit_log (market_id, action, table_name, source, request_id) "
        "VALUES (NULL, 'login_failed', 'users', 'app', %s)",
        (marker,),
    )


def test_platform_audit_rows_are_invisible_to_app_role_directly(
    sync_app_conn: Connection[TupleRow], migrated: None
) -> None:
    """`sbozor_app` NULL qatorlarni TO'G'RIDAN-TO'G'RI o'qiy olmaydi (T-01-88).

    Bu — `audit_read_platform` policy'sining chegarasi. Policy `TO
    sbozor_owner`, ya'ni ilova roli uni UMUMAN ishlata olmaydi va unga faqat
    `audit_read` (`market_id = app.market_id`) qo'llanadi. Tenant konteksti
    yo'q -> `NULLIF(...) -> NULL` -> predikat NULL -> 0 qator (fail-closed,
    XATO EMAS).

    Agar bu test bir kun qizarsa, demak policy `sbozor_app` yoki `PUBLIC` ga
    kengaygan va funksiya-darvoza chetlab o'tiladigan bo'lib qolgan.
    """
    marker = f"pytest-platform-{uuid4().hex}"
    _insert_platform_audit_row(sync_app_conn, marker)

    rows = sync_app_conn.execute(
        "SELECT count(*) FROM audit_log WHERE market_id IS NULL"
    ).fetchone()
    assert rows is not None
    assert rows[0] == 0, (
        "sbozor_app `market_id IS NULL` audit qatorlarini to'g'ridan-to'g'ri "
        "ko'ryapti — SECURITY DEFINER darvozasi chetlab o'tilmoqda (Gap 5)"
    )


def test_auth_list_platform_audit_returns_null_market_rows(
    sync_app_conn: Connection[TupleRow], migrated: None
) -> None:
    """Funksiya `market_id IS NULL` qatorni QAYTARADI — Gap 5 ning yopilishi.

    Yuqoridagi test "to'g'ridan-to'g'ri yo'l yopiq" deydi; bu test o'sha
    yopiqlikning ma'nosini beradi: yozuv YO'QOLMAGAN, u tor darvoza orqali
    O'QILADI. Ikkalasi birga bo'lmasa da'vo yarim qoladi — biri "hech kim
    ko'rmaydi", ikkinchisi "kerakli odam ko'radi".

    Chaqiruv `sbozor_app` roli bilan bajariladi (ilova aynan shunday
    chaqiradi). Funksiya `SECURITY DEFINER`, ya'ni ichkarida `sbozor_owner`
    huquqi bilan ishlaydi va `audit_read_platform` policy'sidan foydalanadi.

    SABOTAJ (qo'lda o'lchangan): `DROP POLICY audit_read_platform ON
    audit_log` bajarilganda bu test aynan shu yerda 0 qator bilan yiqiladi —
    ya'ni `SECURITY DEFINER` YOLG'IZ YETMAYDI, `audit_log` da FORCE RLS
    egani ham bog'laydi. Policy qaytarilgach test yana yashil.

    Qator ENG YANGISI (`at` o'sib boradi, `at DESC, id DESC` tartibi), shuning
    uchun 50 lik sahifada bo'lishi kafolatlangan — test boshqa testlar
    yozgan qatorlar soniga bog'liq emas.
    """
    marker = f"pytest-platform-{uuid4().hex}"
    _insert_platform_audit_row(sync_app_conn, marker)

    rows = sync_app_conn.execute(
        "SELECT id, at, action, table_name, request_id, source "
        "FROM auth_list_platform_audit(%s, NULL, NULL)",
        (50,),
    ).fetchall()

    matched = [row for row in rows if row[4] == marker]
    assert len(matched) == 1, (
        f"`auth_list_platform_audit()` yangi yozilgan `{marker}` qatorini "
        f"qaytarmadi ({len(rows)} qator keldi) — platforma-global audit "
        "hamon o'qilmaydi (Gap 5)"
    )
    assert matched[0][2] == "login_failed"
    assert matched[0][3] == "users"
    assert matched[0][5] == "app"


def test_auth_list_platform_audit_keyset_excludes_boundary_row(
    sync_app_conn: Connection[TupleRow], migrated: None
) -> None:
    """Keyset chegarasi `(at, id)` JUFTLIGI bo'yicha — `audit_repo` bilan bir xil.

    Chegara qatorining O'ZI natijaga TUSHMAYDI (predikat qat'iy `<`), aks
    holda sahifalar chegarada bitta qatorni takrorlardi. Juftlik kerak, `at`
    yolg'iz emas: bir tranzaksiyada yozilgan qatorlar aynan bir xil `at` ga
    ega bo'lishi mumkin.
    """
    marker = f"pytest-platform-{uuid4().hex}"
    _insert_platform_audit_row(sync_app_conn, marker)

    first_page = sync_app_conn.execute(
        "SELECT id, at, request_id FROM auth_list_platform_audit(%s, NULL, NULL)", (1,)
    ).fetchall()
    assert len(first_page) == 1, "birinchi sahifa aynan bitta qator bo'lishi kerak"
    row_id, row_at, row_marker = first_page[0]
    assert row_marker == marker, "eng yangi qator birinchi kelmadi (`at DESC, id DESC`)"

    next_page = sync_app_conn.execute(
        "SELECT id FROM auth_list_platform_audit(%s, %s, %s)", (50, row_at, row_id)
    ).fetchall()

    assert row_id not in {row[0] for row in next_page}, (
        "chegara qatori keyingi sahifada ham qaytdi — kursor `<` emas, `<=` "
        "bo'lib qolgan va sahifalar chegarada takrorlanadi"
    )


def test_auth_list_platform_audit_without_limit_returns_nothing(
    sync_app_conn: Connection[TupleRow], migrated: None
) -> None:
    """`p_limit IS NULL` -> 0 qator (FAIL-CLOSED), CHEKLOVSIZ EMAS.

    Xom `LIMIT p_limit` da `NULL` Postgres uchun "cheklovsiz" degani, ya'ni
    chaqiruvchidagi bitta `None` butun platforma-global jurnalni bir so'rovda
    tortib olardi. `LIMIT COALESCE(p_limit, 0)` uni RLS predikatidagi
    `NULLIF` bilan bir xil qoidaga bo'ysundiradi: noto'g'ri kirish XATO emas,
    0 QATOR beradi.
    """
    _insert_platform_audit_row(sync_app_conn, f"pytest-platform-{uuid4().hex}")

    rows = sync_app_conn.execute(
        "SELECT id FROM auth_list_platform_audit(NULL, NULL, NULL)"
    ).fetchall()

    assert rows == [], (
        "`p_limit IS NULL` da funksiya qator qaytardi — `LIMIT NULL` cheklovsiz bo'lib qolgan"
    )


def test_definer_functions_are_executable_by_app_role(
    sync_app_conn: Connection[TupleRow], migrated: None
) -> None:
    """`sbozor_app` ro'yxatga olingan HAR BIR funksiyani chaqira oladi.

    `GRANT` imzolari ro'yxati funksiyalar ro'yxatidan ajralib qolsa,
    funksiya yaratiladi-yu, ilova uni chaqira olmaydi — va login sahifasi
    (yoki `/auth/refresh`) `permission denied` bilan yiqiladi.
    """
    for functions, signatures in DEFINER_FUNCTION_SETS:
        assert len(signatures) == len(functions), (
            "`GRANT` imzolari va funksiyalar ro'yxati uzunligi mos emas — "
            "yangi funksiyaga GRANT berilmagan bo'lishi mumkin"
        )

        for signature in signatures:
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
