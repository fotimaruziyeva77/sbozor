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

from migrations.entities.functions import (
    ALL_FUNCTIONS,
    AUTH_SUPPORT_FUNCTIONS,
    PLATFORM_AUDIT_FUNCTIONS,
    USER_ADMIN_FUNCTIONS,
)
from migrations.entities.policies import (
    audit_append_policy,
    audit_read_platform_policy,
    audit_read_policy,
    markets_policy,
    owner_bootstrap_policy,
    tenant_policy,
)
from migrations.entities.triggers import ALL_TRIGGER_FUNCTIONS

__all__ = ["ALL_ENTITIES", "RLS_TABLES", "TENANT_TABLES"]

TENANT_TABLES: tuple[str, ...] = ("user_market_roles", "refresh_tokens")
"""`market_id` ustuni + standart tenant policy'si bo'lgan jadvallar.

Yangi tenant jadvali qo'shilganda BU RO'YXATGA ham bir satr qo'shiladi.
Unutilsa `tests/tenancy/test_meta.py::test_every_table_is_tenant_scoped`
jadvalni policy'siz topib darvozani yopadi.
"""

RLS_TABLES: tuple[str, ...] = ("markets", *TENANT_TABLES)
"""RLS yoqilgan barcha jadvallar (`markets` maxsus policy bilan).

`audit_log` bu ro'yxatda ATAYIN YO'Q: unga `owner_bootstrap` policy'si
BERILMASLIGI shart. O'sha policy `FOR ALL ... USING (true)` bo'lgani uchun
egaga `UPDATE`/`DELETE` da qatorlarni ko'rsatib qo'yardi va o'zgarmaslikning
2-qatlamini bir zarbada yo'q qilardi (`migrations/versions/0002_audit.py`).

DIQQAT — `audit_read_platform` (0005) BUNGA ZID EMAS. U ham EGAGA
mo'ljallangan (`TO sbozor_owner`), lekin `FOR SELECT`: `UPDATE`/`DELETE`
uchun baribir birorta policy paydo bo'lmaydi, ya'ni 2-qatlam o'zgarishsiz
qoladi. Butun farq komanda bandida — uni kelajakda `FOR ALL` ga
"soddalashtirish" o'zgarmaslikni JIMGINA yo'q qilardi, shuning uchun
`test_audit_read_platform_is_owner_only` komandani `SELECT` ga qulflaydi.
"""

ALL_ENTITIES: list[Any] = [
    # `markets` — tenant chegarasining o'zi: predikat `id` bo'yicha.
    markets_policy(),
    *(tenant_policy(table) for table in TENANT_TABLES),
    # Ega uchun bootstrap: `SECURITY DEFINER` login funksiyalari va bozor
    # yaratish yo'li FORCE ostida bloklanib qolmasligi uchun.
    *(owner_bootstrap_policy(table) for table in RLS_TABLES),
    # `audit_log` — yozish predikatsiz, o'qish tenant-scoped, UPDATE/DELETE
    # uchun policy YO'Q (o'zgarmaslikning 2-qatlami).
    audit_append_policy(),
    audit_read_policy(),
    # Platforma-global (`market_id IS NULL`) qatorlar uchun EGAGA ochiladigan
    # tor `FOR SELECT` yo'li — `auth_list_platform_audit()` ning jufti (Gap 5).
    audit_read_platform_policy(),
    # Login bootstrap — global o'qish yuzasining BUTUN ro'yxati (Pattern 2).
    *ALL_FUNCTIONS,
    # Sessiya va parol YOZISH yo'li (0003): `refresh_tokens` ustidagi
    # operatsiyalar ham tenant kontekstisiz bajarilishi kerak, chunki
    # refresh cookie kelganda bozor hali noma'lum.
    *AUTH_SUPPORT_FUNCTIONS,
    # Foydalanuvchi boshqaruvi va profil (0004): `users` app-rolga yopiq,
    # ya'ni yaratish/profil o'qish/til saqlash ham shu yuzadan o'tadi.
    *USER_ADMIN_FUNCTIONS,
    # Platforma-global audit o'qish (0005): yuqoridagi `audit_read_platform`
    # policy'si bilan JUFTLIKDA ishlaydi — biri ikkinchisisiz 0 qator beradi.
    *PLATFORM_AUDIT_FUNCTIONS,
    # Audit yozuvchisi + append-only qo'riqchisi (D-10).
    *ALL_TRIGGER_FUNCTIONS,
]
