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
    MARKET_DOMAIN_FUNCTIONS,
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

__all__ = [
    "ALL_ENTITIES",
    "ALL_RLS_TABLES",
    "ALL_TENANT_TABLES",
    "CALENDAR_TENANT_TABLES",
    "MARKET_DOMAIN_TENANT_TABLES",
    "RLS_TABLES",
    "TEMPORAL_TENANT_TABLES",
    "TENANT_TABLES",
    "VENDOR_TENANT_TABLES",
]

TENANT_TABLES: tuple[str, ...] = ("user_market_roles", "refresh_tokens")
"""`0001_identity` YARATGAN tenant jadvallari — BU RO'YXAT MUZLATILGAN.

⚠ YANGI JADVAL BU YERGA QO'SHILMAYDI. `migrations/versions/0001_identity.py`
shu tuple ustidan TSIKL qiladi (`enable_tenant_rls(table)`,
`create_entity(tenant_policy(table))`), ya'ni qiymatni kengaytirish nol
holatdan qilingan migratsiyani `relation "stalls" does not exist` bilan
yiqitardi — 0001 hali mavjud bo'lmagan jadvalga RLS qo'ymoqchi bo'lardi.

Yangi jadvallar quyidagi MIGRATSIYA-SCOPE'li tuple'larga qo'shiladi
(`MARKET_DOMAIN_TENANT_TABLES`, `TEMPORAL_TENANT_TABLES`,
`VENDOR_TENANT_TABLES`, `CALENDAR_TENANT_TABLES`), ularning yig'indisi esa
`ALL_TENANT_TABLES` — autogenerate va policy reyestri aynan shundan
quriladi.
"""

RLS_TABLES: tuple[str, ...] = ("markets", *TENANT_TABLES)
"""`0001_identity` da RLS yoqilgan jadvallar — BU RO'YXAT HAM MUZLATILGAN.

Kengaytirish o'rniga `ALL_RLS_TABLES` ishlatiladi (pastda).

`markets` maxsus policy bilan.

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


# ===========================================================================
# 2-FAZA — MIGRATSIYA-SCOPE'LI TENANT JADVALLARI
# ===========================================================================
#
# Reyestr MIGRATSIYA bo'yicha bo'lingan, chunki har bir tuple ustidan AYNAN
# uni yaratgan migratsiya tsikl qiladi. Bitta katta ro'yxat bo'lganda
# 0001 hali mavjud bo'lmagan jadvalga RLS qo'ymoqchi bo'lardi (yuqoriga
# qarang), yoki har bir migratsiya "mening ulushim qaysi" degan savolni
# qo'lda hal qilardi.

MARKET_DOMAIN_TENANT_TABLES: tuple[str, ...] = (
    "market_profile",
    "zones",
    "stall_categories",
    "stalls",
    "stall_code_registry",
)
"""`0007_market_domain` yaratadigan tenant jadvallari (MARKET-01/02)."""

TEMPORAL_TENANT_TABLES: tuple[str, ...] = (
    "stall_category_periods",
    "tariffs",
)
"""`0008_temporal` — VORIS modelidagi ikkita tarix jadvali (D-04/D-06, MARKET-03).

Alohida migratsiyada, chunki ular `stalls` va `stall_categories` ga composite
FK bilan tayanadi va o'zgarmaslik triggerlarini ham olib keladi.
"""

VENDOR_TENANT_TABLES: tuple[str, ...] = (
    "vendors",
    "stall_assignments",
)
"""`0009_vendors` — sotuvchilar va biriktirish davrlari (MARKET-04).

Alohida migratsiyada, chunki `stall_assignments` `btree_gist` kengaytmasini
talab qiladi va migratsiya `require_extension("btree_gist")` bilan
boshlanadi (Pitfall 1).
"""

CALENDAR_TENANT_TABLES: tuple[str, ...] = ("market_calendar_exceptions",)
"""`0010_calendar` — yopiq kun istisnolari (MARKET-05, D-18)."""

ALL_TENANT_TABLES: tuple[str, ...] = (
    *TENANT_TABLES,
    *MARKET_DOMAIN_TENANT_TABLES,
    *TEMPORAL_TENANT_TABLES,
    *VENDOR_TENANT_TABLES,
    *CALENDAR_TENANT_TABLES,
)
"""BARCHA tenant jadvallari — policy reyestrining yagona manbai.

`ALL_ENTITIES` aynan shundan quriladi, ya'ni autogenerate har bir jadvalning
`tenant_isolation` policy'sini kuzatadi. Bu reyestr UNUTILISHI mumkin bo'lgan
yagona joy, shuning uchun u YOLG'IZ darvoza EMAS:
`tests/tenancy/test_meta.py::test_every_table_is_tenant_scoped` jadvallarni
`pg_catalog` dan o'qiydi va reyestrga UMUMAN tayanmaydi — reyestrga
qo'shilmagan jadval baribir topiladi (T-02-28).
"""

ALL_RLS_TABLES: tuple[str, ...] = ("markets", *ALL_TENANT_TABLES)
"""RLS yoqilgan barcha jadvallar — `owner_bootstrap` policy'si shu ro'yxatga.

`market_create()` va `market_delete_draft()` `SECURITY DEFINER` bo'lib EGA
huquqi bilan ishlaydi, `FORCE ROW LEVEL SECURITY` esa EGANI HAM policy'ga
bo'ysundiradi. Ya'ni `owner_bootstrap` policy'siz o'sha funksiyalar
`market_profile` ga yoza olmasdi va usta 1-qadamda jimgina 0 qator bilan
tugardi.
"""

ALL_ENTITIES: list[Any] = [
    # `markets` — tenant chegarasining o'zi: predikat `id` bo'yicha.
    markets_policy(),
    *(tenant_policy(table) for table in ALL_TENANT_TABLES),
    # Ega uchun bootstrap: `SECURITY DEFINER` login funksiyalari va bozor
    # yaratish yo'li FORCE ostida bloklanib qolmasligi uchun.
    *(owner_bootstrap_policy(table) for table in ALL_RLS_TABLES),
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
    # Bozor hayot sikli (0007): yaratish/faollashtirish/nomlash/o'chirish
    # `SECURITY DEFINER`, `market_is_open()` esa ATAYIN INVOKER.
    *MARKET_DOMAIN_FUNCTIONS,
    # Audit yozuvchisi + append-only qo'riqchisi (D-10) + 2-faza domen
    # qoidalari (kod reyestri, tarif/toifa daxlsizligi).
    *ALL_TRIGGER_FUNCTIONS,
]
