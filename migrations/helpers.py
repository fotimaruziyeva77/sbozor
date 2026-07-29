"""RLS DDL yordamchilari — `alembic-utils` QOPLAMAYDIGAN qism.

=============================================================================
NEGA BU FAYL BOR (RESEARCH Pattern 11 / Pitfall 10 — empirik tasdiqlangan):

`alembic-utils` 0.8.8 `CREATE POLICY` / `PGFunction` / `PGTrigger` /
`PGGrantTable` ni biladi, LEKIN quyidagilarni umuman bilmaydi:

  * `ALTER TABLE ... ENABLE ROW LEVEL SECURITY`
  * `ALTER TABLE ... FORCE  ROW LEVEL SECURITY`
  * `REVOKE ...`

Natija jimgina buziladi: policy yaratiladi va autogenerate'da ko'rinadi,
RLS esa yoqilmay qoladi — ya'ni policy HECH QANDAY ta'sir ko'rsatmaydi va
jadval hamma uchun ochiq bo'ladi. Shuning uchun bu uch DDL xom
`op.execute()` bilan yoziladi va `tests/tenancy/test_meta.py`
`relrowsecurity` VA `relforcerowsecurity` ikkalasini ham tekshiradi.
=============================================================================

Yangi tenant jadvali qo'shganda TARTIB muhim:

    op.create_table("stalls", ...)
    enable_tenant_rls("stalls")                     # ENABLE + FORCE + GRANT
    op.create_entity(tenant_policy("stalls"))       # policy
    op.create_entity(owner_bootstrap_policy("stalls"))
"""

from __future__ import annotations

import re
from typing import Any

from alembic import op

__all__ = [
    "APP_ROLE",
    "DEFAULT_DML",
    "OWNER_ROLE",
    "create_entity",
    "disable_force_for_backfill",
    "drop_entity",
    "enable_rls",
    "enable_tenant_rls",
    "grant_app_dml",
    "restore_force",
    "revoke_app_all",
]

APP_ROLE = "sbozor_app"
"""Ilova DML roli — NOSUPERUSER NOBYPASSRLS (`ops/db/init/01-roles.sql`)."""

OWNER_ROLE = "sbozor_owner"
"""DDL/migratsiya egasi — jadvallar shu rol nomidan yaratiladi."""

DEFAULT_DML = "SELECT, INSERT, UPDATE, DELETE"

_IDENT_RE = re.compile(r"^[a-z_][a-z0-9_]*$")
_DML_RE = re.compile(
    r"^(SELECT|INSERT|UPDATE|DELETE|REFERENCES|TRIGGER)"
    r"(,\s*(SELECT|INSERT|UPDATE|DELETE|REFERENCES|TRIGGER))*$"
)


def _ident(name: str) -> str:
    """Identifikatorni tekshiradi.

    Bu yordamchilar DDL'ni satr birlashtirish bilan quradi (Postgres `ALTER
    TABLE` / `GRANT` bind parametr qabul qilmaydi), shuning uchun kirish
    QAT'IY cheklanadi: faqat kichik harfli `snake_case`. Argumentlar
    migratsiya kodidan keladi, lekin bu darvoza sinf sifatida butun
    injection yuzasini yopadi.
    """
    if not _IDENT_RE.match(name):
        raise ValueError(
            f"{name!r} yaroqli identifikator emas — faqat kichik harf, raqam "
            "va pastki chiziq ruxsat etiladi (snake_case)"
        )
    return name


def _dml(ops: str) -> str:
    """`GRANT` uchun huquqlar ro'yxatini tekshiradi."""
    if not _DML_RE.match(ops.strip()):
        raise ValueError(f"{ops!r} yaroqli DML huquqlari ro'yxati emas")
    return ops.strip()


def create_entity(entity: Any) -> None:
    """`op.create_entity()` ning tipli o'ram'i.

    `alembic-utils` o'z operatsiyalarini import paytida `Operations` ga
    DINAMIK ro'yxatdan o'tkazadi, shuning uchun mypy ularni ko'rmaydi
    (`Module has no attribute "create_entity"`). Ignore'ni har bir
    migratsiyada takrorlash o'rniga u shu yerda BIR MARTA, sababi bilan
    yoziladi — va migratsiyalar `attr-defined` tekshiruvini yo'qotmaydi.
    """
    op.create_entity(entity)  # type: ignore[attr-defined]


def drop_entity(entity: Any) -> None:
    """`op.drop_entity()` ning tipli o'ram'i (`create_entity` jufti)."""
    op.drop_entity(entity)  # type: ignore[attr-defined]


def enable_rls(table: str) -> None:
    """`ENABLE` + `FORCE ROW LEVEL SECURITY` (GRANT'siz).

    `markets` kabi maxsus holatlar uchun: u tenant chegarasining O'ZI,
    shuning uchun policy'si boshqacha va app-rolga faqat `SELECT` beriladi.
    """
    tbl = _ident(table)
    op.execute(f"ALTER TABLE {tbl} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {tbl} FORCE  ROW LEVEL SECURITY")


def enable_tenant_rls(table: str, role: str = APP_ROLE) -> None:
    """Standart tenant jadvali: `ENABLE` + `FORCE` + to'liq DML GRANT.

    GRANT'siz policy ma'nosiz bo'ladi (huquq yo'q -> `permission denied`),
    ENABLE/FORCE'siz esa policy ma'nosiz bo'ladi (hamma narsa ochiq).
    Uchtasi birga yuradi, shuning uchun bitta chaqiruvda.
    """
    enable_rls(table)
    grant_app_dml(table, role=role)


def grant_app_dml(table: str, ops: str = DEFAULT_DML, role: str = APP_ROLE) -> None:
    """Ilova roliga jadval ustida huquq beradi."""
    op.execute(f"GRANT {_dml(ops)} ON TABLE {_ident(table)} TO {_ident(role)}")


def revoke_app_all(table: str, role: str = APP_ROLE) -> None:
    """Ilova rolidan jadval ustidagi BARCHA huquqni olib tashlaydi.

    `users` uchun ishlatiladigan naqsh (Pattern 2): global identifikatsiya
    jadvaliga ORM orqali oddiy `select()` bilan borish IMKONSIZ bo'lishi
    kerak — o'qish faqat tor `SECURITY DEFINER` funksiyalari orqali o'tadi.
    """
    op.execute(f"REVOKE ALL ON TABLE {_ident(table)} FROM {_ident(role)}")


def disable_force_for_backfill(table: str) -> None:
    """Backfill oldidan `NO FORCE` (RESEARCH Pitfall 4 — empirik).

    `sbozor_owner` (superuser EMAS) FORCE ostida ham policy'ga bo'ysunadi,
    ya'ni migratsiyadagi `UPDATE ... SET ...` **jimgina `UPDATE 0`** qaytaradi
    va migratsiya "muvaffaqiyatli" tugaydi. `row_security` sozlamasini
    o'chirish YO'L BERMAYDI — Postgres `query would be affected by
    row-level security policy` xatosini beradi.

    Yagona to'g'ri ketma-ketlik::

        disable_force_for_backfill("stalls")
        result = op.get_bind().execute(sa.text("UPDATE stalls SET ..."))
        assert result.rowcount == kutilgan_son     # jim 0 ni ushlaydi
        restore_force("stalls")

    1-fazada backfill yo'q; yordamchi naqshni hujjatlashtirish uchun bor.
    """
    op.execute(f"ALTER TABLE {_ident(table)} NO FORCE ROW LEVEL SECURITY")


def restore_force(table: str) -> None:
    """Backfill tugagach FORCE'ni qaytaradi (`disable_force_for_backfill` jufti)."""
    op.execute(f"ALTER TABLE {_ident(table)} FORCE  ROW LEVEL SECURITY")
