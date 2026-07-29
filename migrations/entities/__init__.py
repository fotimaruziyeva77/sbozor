"""`alembic-utils` entity reyestri — `env.py` shu ro'yxatni ro'yxatga oladi.

`register_entities(ALL_ENTITIES)` autogenerate'ga bu obyektlarni kuzatishni
buyuradi: fabrikaning matni o'zgarsa, keyingi `alembic revision
--autogenerate` `op.replace_entity(...)` ni o'zi taklif qiladi va policy
ta'rifi bazadan ajralib qolmaydi.

DIQQAT: `alembic-utils` `ENABLE`/`FORCE ROW LEVEL SECURITY` ni BILMAYDI —
u faqat `CREATE POLICY` ni boshqaradi. Bayroqlar `migrations/helpers.py`
dagi `enable_tenant_rls()` orqali qo'yiladi (Pitfall 10).
"""

from __future__ import annotations

from typing import Any

from migrations.entities.functions import ALL_FUNCTIONS
from migrations.entities.policies import (
    markets_policy,
    owner_bootstrap_policy,
    tenant_policy,
)

__all__ = ["ALL_ENTITIES", "RLS_TABLES", "TENANT_TABLES"]

TENANT_TABLES: tuple[str, ...] = ("user_market_roles", "refresh_tokens")
"""`market_id` ustuni + standart tenant policy'si bo'lgan jadvallar.

Yangi tenant jadvali qo'shilganda BU RO'YXATGA ham bir satr qo'shiladi.
Unutilsa `tests/tenancy/test_meta.py::test_every_table_is_tenant_scoped`
jadvalni policy'siz topib darvozani yopadi.
"""

RLS_TABLES: tuple[str, ...] = ("markets", *TENANT_TABLES)
"""RLS yoqilgan barcha jadvallar (`markets` maxsus policy bilan)."""

ALL_ENTITIES: list[Any] = [
    # `markets` — tenant chegarasining o'zi: predikat `id` bo'yicha.
    markets_policy(),
    *(tenant_policy(table) for table in TENANT_TABLES),
    # Ega uchun bootstrap: `SECURITY DEFINER` login funksiyalari va bozor
    # yaratish yo'li FORCE ostida bloklanib qolmasligi uchun.
    *(owner_bootstrap_policy(table) for table in RLS_TABLES),
    # Login bootstrap — global o'qish yuzasining BUTUN ro'yxati (Pattern 2).
    *ALL_FUNCTIONS,
]
