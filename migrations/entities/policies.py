"""RLS policy ta'riflari — `PGPolicy` obyektlarining YAGONA joyi.

=============================================================================
`NULLIF(...)` MAJBURIY — bu ixtiyoriy stil emas (RESEARCH Pattern 1 / Pitfall 1,
empirik o'lchangan):

`set_config('app.market_id', X, true)` tranzaksiya tugagach GUC'ni `NULL` ga
QAYTARMAYDI — u bo'sh satr (`''`) bo'lib qoladi va ulanish umri davomida
shunday turadi. Puldagi ulanish keyingi so'rovga o'tganda predikat bo'sh
satrni `uuid` ga keltirishga urinadi:

    ERROR: invalid input syntax for type uuid: ""

Ya'ni `NULLIF` siz shakl login sahifasini, `/readyz` ni va har qanday
tenant-kontekstsiz so'rovni 500 bilan yiqitadi. `NULLIF(..., '')` esa bo'sh
satrni `NULL` ga aylantiradi va natija FAIL-CLOSED bo'ladi: 0 qator, xato
emas. Buni `tests/tenancy/test_rls_predicate.py` `pool_size=1` engine bilan
isbotlaydi.

| Holat                                   | GUC qiymati | Natija            |
| --------------------------------------- | ----------- | ----------------- |
| hech qachon o'rnatilmagan               | `NULL`      | 0 qator           |
| `set_config(..., true)` + COMMIT dan so'ng | `''`     | `NULLIF` -> 0 qator |
| bozor tanlangan                         | `<uuid>`    | faqat o'sha bozor |
=============================================================================

Nega hammasi bitta faylda: `alembic-utils` 0.8.8 ning oxirgi relizi
2025-04-10 (RESEARCH Open Question 1). Agar u kelajakdagi alembic bilan mos
kelmasa, bu fayldagi ikkita fabrikani xom `op.execute("CREATE POLICY ...")`
ga ko'chirish bir soatlik ish — ta'rif boshqa hech qayerda takrorlanmaydi.
"""

from __future__ import annotations

from alembic_utils.pg_policy import PGPolicy

__all__ = [
    "APP_ROLE",
    "MARKETS_PREDICATE",
    "OWNER_BOOTSTRAP_SIGNATURE",
    "OWNER_ROLE",
    "TENANT_PREDICATE",
    "TENANT_POLICY_SIGNATURE",
    "markets_policy",
    "owner_bootstrap_policy",
    "tenant_policy",
]

APP_ROLE = "sbozor_app"
OWNER_ROLE = "sbozor_owner"

TENANT_POLICY_SIGNATURE = "tenant_isolation"
OWNER_BOOTSTRAP_SIGNATURE = "owner_bootstrap"

TENANT_PREDICATE = "market_id = NULLIF(current_setting('app.market_id', true), '')::uuid"
"""Standart tenant jadvallari uchun predikat (`market_id` ustuni bo'yicha)."""

MARKETS_PREDICATE = "id = NULLIF(current_setting('app.market_id', true), '')::uuid"
"""`markets` MAXSUS HOLATI: unda `market_id` ustuni yo'q — tenant kaliti `id` ning O'ZI.

RESEARCH Open Question 4. `test_markets_rls_and_policy` buni doimiy qulflaydi.
"""


def tenant_policy(table: str) -> PGPolicy:
    """Berilgan tenant jadvali uchun `sbozor_app` policy'si.

    `WITH CHECK` `USING` bilan bir xil: boshqa bozorga YOZISH ham
    (INSERT/UPDATE) strukturaviy rad etiladi, faqat o'qish emas.
    """
    return PGPolicy(
        schema="public",
        signature=TENANT_POLICY_SIGNATURE,
        on_entity=f"public.{table}",
        definition=f"""
            AS PERMISSIVE
            FOR ALL
            TO {APP_ROLE}
            USING      ({TENANT_PREDICATE})
            WITH CHECK ({TENANT_PREDICATE})
        """,
    )


def markets_policy() -> PGPolicy:
    """`markets` uchun policy — solishtirish `id` bo'yicha, `market_id` bo'yicha EMAS.

    App-rolga `markets` da faqat `SELECT` beriladi (yozish `sbozor_owner` va
    2-fazadagi bozor ustasi orqali), shuning uchun `WITH CHECK` shart emas —
    lekin u ham qo'yiladi: kelajakda GRANT kengaysa policy allaqachon yopiq
    bo'ladi (fail-closed default).
    """
    return PGPolicy(
        schema="public",
        signature=TENANT_POLICY_SIGNATURE,
        on_entity="public.markets",
        definition=f"""
            AS PERMISSIVE
            FOR ALL
            TO {APP_ROLE}
            USING      ({MARKETS_PREDICATE})
            WITH CHECK ({MARKETS_PREDICATE})
        """,
    )


def owner_bootstrap_policy(table: str) -> PGPolicy:
    """`sbozor_owner` uchun bootstrap policy — login yo'lini ochiq tutadi.

    NEGA KERAK (empirik, Pitfall 4 bilan bir xil mexanizm):
    `FORCE ROW LEVEL SECURITY` jadval EGASINI ham policy'ga bo'ysundiradi.
    Yuqoridagi policy'lar `TO sbozor_app` bilan cheklangani uchun egaga
    HECH QANDAY policy qo'llanmaydi — ya'ni ega uchun natija deny-all.
    Buning ikki oqibati bor:

    1. `SECURITY DEFINER` login funksiyalari (`auth_memberships`,
       `auth_list_markets`) ega huquqi bilan ishlaydi va **0 qator** qaytaradi
       -> hech kim tizimga kira olmaydi (Pitfall 3 ning boshqa ko'rinishi).
    2. Bozor yaratish (`INSERT INTO markets`) migratsiya/seed yo'lida
       `new row violates row-level security policy` bilan yiqiladi.

    XAVFSIZLIK CHEGARASI QAYERDA: haqiqiy chegara — `sbozor_app`. Ilova
    FAQAT o'sha rol bilan ulanadi va u `NOSUPERUSER NOBYPASSRLS`, ya'ni
    yuqoridagi tenant predikatidan chiqa olmaydi. `sbozor_owner` esa
    jadvallarning EGASI: u xohlagan payt `ALTER TABLE ... NO FORCE` qila
    oladi, shuning uchun unga qarshi FORCE hech qachon xavfsizlik nazorati
    bo'lmagan — u faqat tasodifiy ega-tomon o'qish/yozishning oldini oladi.
    Bu policy o'sha kirishni YASHIRIN emas, AShKORA va greplanadigan qiladi.

    `tests/tenancy/test_meta.py::test_owner_bootstrap_policies_are_owner_only`
    uni qulflaydi: bu policy hech qachon `sbozor_app` ga yoki `PUBLIC` ga
    berilmasligi shart.
    """
    return PGPolicy(
        schema="public",
        signature=OWNER_BOOTSTRAP_SIGNATURE,
        on_entity=f"public.{table}",
        definition=f"""
            AS PERMISSIVE
            FOR ALL
            TO {OWNER_ROLE}
            USING      (true)
            WITH CHECK (true)
        """,
    )
