"""Tenant izolyatsiyasi META-TESTLARI — rol invariantlari (FOUND-02).

Bu 1-fazaning eng qimmatli artefaktlaridan biri: u keyingi 7 fazada RLS
regressiyasini doimiy ushlab turadi.

NEGA ROLLAR, NEGA POLICY EMAS:
`FORCE ROW LEVEL SECURITY` faqat jadval EGASINI policy'ga bo'ysundiradi.
Superuser va `BYPASSRLS` atributli rollar RLS'ni HAR DOIM chetlab o'tadi —
va agar test fixture'i o'sha rol bilan ulansa, keyingi barcha RLS testlari
YOLG'ON-YASHIL beradi. Shuning uchun rol invariantlari birinchi qulflanadi.

DIQQAT: sxema invariantlari (har jadvalda `market_id`, RLS ENABLE+FORCE,
policy mavjudligi, indekslar `market_id` bilan boshlanishi) 01-04 rejasida
qo'shiladi — bu bosqichda hali hech qanday jadval yo'q.
"""

from __future__ import annotations

import psycopg
import pytest
from psycopg import Connection
from psycopg.rows import TupleRow
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

pytestmark = pytest.mark.tenancy


def _role_flags(conn: Connection[TupleRow], rolname: str) -> tuple[bool, bool]:
    """`(rolsuper, rolbypassrls)` juftligini qaytaradi."""
    row = conn.execute(
        "SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = %s",
        (rolname,),
    ).fetchone()
    assert row is not None, f"{rolname} roli mavjud emas — ops/db/init/01-roles.sql bajarilmagan"
    return bool(row[0]), bool(row[1])


def test_app_role_cannot_bypass_rls(sync_app_conn: Connection[TupleRow]) -> None:
    """`sbozor_app` RLS'ni chetlab o'ta olmaydi (T-01-01)."""
    is_super, can_bypass = _role_flags(sync_app_conn, "sbozor_app")
    assert not is_super, "sbozor_app SUPERUSER — tenant izolyatsiyasi umuman yo'q"
    assert not can_bypass, "sbozor_app BYPASSRLS — RLS policy'lari ta'sirsiz qoladi"


def test_owner_role_is_not_superuser(sync_app_conn: Connection[TupleRow]) -> None:
    """`sbozor_owner` (migratsiya roli) ham superuser emas."""
    is_super, can_bypass = _role_flags(sync_app_conn, "sbozor_owner")
    assert not is_super, "sbozor_owner SUPERUSER — migratsiyalar RLS'ni chetlab o'tadi"
    assert not can_bypass, "sbozor_owner BYPASSRLS — FORCE ROW LEVEL SECURITY ma'nosiz bo'ladi"


async def test_app_engine_connects_as_sbozor_app(app_engine: AsyncEngine) -> None:
    """Fixture'ning O'ZINI himoyalaydi (T-01-02).

    Agar kimdir `app_engine` ni `superuser_url` ga qaytarsa, bu test yiqiladi
    va CI to'xtaydi — RLS testlari jimgina yolg'on-yashil bo'lib qolmaydi.
    """
    async with app_engine.connect() as conn:
        current_user = (await conn.execute(text("SELECT current_user"))).scalar_one()

    assert current_user == "sbozor_app", (
        f"app_engine `{current_user}` bilan ulangan, `sbozor_app` bilan emas — "
        "RLS testlari endi hech narsani isbotlamaydi"
    )


def test_app_cannot_disable_triggers(sync_app_conn: Connection[TupleRow]) -> None:
    """`sbozor_app` audit triggerlarini o'chira olmaydi (T-01-05).

    `SET session_replication_role = replica` — triggerlarni butun sessiya uchun
    o'chirish yo'li. Ilova roli uni o'zgartira olsa, audit jurnali chetlab
    o'tiladi.
    """
    with pytest.raises(psycopg.errors.InsufficientPrivilege) as excinfo:
        sync_app_conn.execute("SET session_replication_role = replica")

    assert "session_replication_role" in str(excinfo.value)


def test_public_schema_create_revoked_from_public(sync_app_conn: Connection[TupleRow]) -> None:
    """`sbozor_app` `public` sxemada obyekt yarata olmaydi (T-01-06)."""
    row = sync_app_conn.execute(
        "SELECT has_schema_privilege('sbozor_app', 'public', 'CREATE')"
    ).fetchone()
    assert row is not None
    assert row[0] is False, (
        "sbozor_app `public` sxemada CREATE huquqiga ega — RLS'siz yordamchi "
        "jadval yaratib izolyatsiyani chetlab o'tish mumkin"
    )
