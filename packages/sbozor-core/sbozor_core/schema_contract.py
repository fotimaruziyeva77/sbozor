"""Sxema reyestrlari — tenancy meta-testlari uchun YAGONA manba.

Bu modul faqat jadval NOMLARINI saqlaydi (model ham, DDL ham emas). Sabab:
meta-testlar "har bir jadvalda `market_id` bor, RLS ENABLE+FORCE qilingan va
tenant policy'si mavjud" degan invariantni `pg_catalog` dan tekshiradi, va
istisnolar ro'yxati TESTDA emas, shu yerda yashashi kerak. Shunda yangi
istisno qo'shish ataylab qilingan, ko'rinadigan va commit'da ko'zga
tashlanadigan harakat bo'ladi.

Kengaytirish qoidasi: yangi jadval qo'shilganda u AVTOMATIK ravishda
tenant-scoped deb hisoblanadi. Reyestrga qo'shish faqat istisno uchun —
va istisnoning sababi shu yerda izohda yozilishi shart.
"""

from __future__ import annotations

__all__ = ["AUDITED_TABLES", "FINANCIAL_TABLES", "GLOBAL_TABLES"]

GLOBAL_TABLES: frozenset[str] = frozenset(
    {
        # Identifikatsiya a'zolikdan ajratilgan (Pattern 2): login paytida
        # `app.market_id` hali NOMA'LUM, shuning uchun `users` da `market_id`
        # ustuni ham, tenant policy'si ham YO'Q. Uning o'rniga app-rolga
        # `REVOKE ALL` qo'yiladi va o'qish faqat ikkita tor `SECURITY DEFINER`
        # funksiya orqali o'tadi.
        "users",
        # `markets` — MAXSUS HOLAT, "global" emas (RESEARCH Open Question 4).
        # U tenant chegarasining O'ZI, shuning uchun policy'si boshqa
        # jadvallardagidan farq qiladi: `market_id = ...` emas, `id = ...`.
        # Meta-test uni umumiy tsikldan chiqarib, alohida qulflaydi
        # (`test_markets_rls_and_policy`, 01-04).
        "markets",
        # Alembic ning o'z buxgalteriyasi — ilova ma'lumoti emas.
        "alembic_version",
    }
)
"""`market_id` ustuni va standart tenant policy'si BO'LMASLIGI kutilgan jadvallar."""

FINANCIAL_TABLES: frozenset[str] = frozenset(
    {
        "daily_charges",
        "charge_adjustments",
        "payments",
        "tariffs",
        "stall_assignments",
    }
)
"""D-10 audit qamrovi + mezon #5 konstraytlari majburiy bo'lgan jadvallar.

1-fazada bu jadvallarning HECH BIRI hali mavjud emas (ular 2- va 6-fazalarda
tug'iladi). Reyestr shunga qaramay hozir yoziladi, chunki meta-test uni
"jadval mavjud bo'lsa — quyidagi konstraytlar ham bo'lishi shart" shaklida
ishlatadi: shunda 6-fazada `payments` yaratilgan kuni darvoza avtomatik
yopiladi va hech kim `UNIQUE(market_id, idempotency_key)` ni unutib
qo'ymaydi.
"""

AUDITED_TABLES: frozenset[str] = frozenset(
    {
        # 1-fazada DB-trigger qo'llanadigan yagona jadval: rol berish/olib
        # tashlash — huquq ko'tarilishining asosiy yo'li, shuning uchun u
        # moliyaviy jadvallardan oldin audit ostiga olinadi.
        "user_market_roles",
    }
)
"""`fn_audit_row()` triggeri O'RNATILGAN jadvallar (hozirgi holat, kutilgan emas).

Bu reyestr `FINANCIAL_TABLES` bilan ATAYIN birlashtirilmagan: u kutilgan
qamrovni emas, AMALDAGI holatni bildiradi. Har yangi jadval tug'ilganda
`PGTrigger` bilan birga shu ro'yxatga ham bir satr qo'shiladi — meta-test
shu ikki manbani `pg_trigger` bilan solishtiradi.
"""
