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
    "AUDIT_APPEND_SIGNATURE",
    "AUDIT_READ_PLATFORM_SIGNATURE",
    "AUDIT_READ_SIGNATURE",
    "MARKETS_PREDICATE",
    "OWNER_BOOTSTRAP_SIGNATURE",
    "OWNER_ROLE",
    "PLATFORM_AUDIT_PREDICATE",
    "TENANT_PREDICATE",
    "TENANT_POLICY_SIGNATURE",
    "audit_append_policy",
    "audit_read_platform_policy",
    "audit_read_policy",
    "markets_policy",
    "owner_bootstrap_policy",
    "tenant_policy",
]

APP_ROLE = "sbozor_app"
OWNER_ROLE = "sbozor_owner"

TENANT_POLICY_SIGNATURE = "tenant_isolation"
OWNER_BOOTSTRAP_SIGNATURE = "owner_bootstrap"
AUDIT_APPEND_SIGNATURE = "audit_append"
AUDIT_READ_SIGNATURE = "audit_read"
AUDIT_READ_PLATFORM_SIGNATURE = "audit_read_platform"

TENANT_PREDICATE = "market_id = NULLIF(current_setting('app.market_id', true), '')::uuid"
"""Standart tenant jadvallari uchun predikat (`market_id` ustuni bo'yicha)."""

MARKETS_PREDICATE = "id = NULLIF(current_setting('app.market_id', true), '')::uuid"
"""`markets` MAXSUS HOLATI: unda `market_id` ustuni yo'q — tenant kaliti `id` ning O'ZI.

RESEARCH Open Question 4. `test_markets_rls_and_policy` buni doimiy qulflaydi.
"""

PLATFORM_AUDIT_PREDICATE = "market_id IS NULL"
"""Platforma-global audit qatorlari — hech qaysi bozorga tegishli EMAS.

`login_failed` kabi yozuvlar ataylab `market_id = NULL` bilan yoziladi: rad
etilgan login urinishida bozor NOMA'LUM va uni taxmin qilish jurnalga YOLG'ON
dalil yozish bo'lardi (01-05/01-06). Bu predikat `TENANT_PREDICATE` ning
to'ldiruvchisi, ALTERNATIVASI EMAS: ikkalasi kesishmaydi (`market_id = X` va
`market_id IS NULL` bir qatorga bir vaqtda mos kelolmaydi), shuning uchun
bittasini ochish ikkinchisining yuzasini kengaytirmaydi.
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


def audit_append_policy() -> PGPolicy:
    """`audit_log` ga YOZISH — har doim ruxsat, hech qanday predikatsiz.

    Bu jadvaldagi ikkita policy'ning BIRINCHISI va u ataylab boshqa hamma
    joydagi qoidadan chetga chiqadi. Sabab: jurnalga yozishni bloklash
    IMKONSIZ bo'lishi kerak. Agar `WITH CHECK` tenant predikatiga
    bo'ysunganida, tenant kontekstisiz bajarilgan har qanday o'zgarish
    (fon job, migratsiya, admin skripti) audit yozuvini yo'qotardi — ya'ni
    aynan eng kam nazorat qilinadigan yo'l eng kam iz qoldirardi.

    `TO` bandi ATAYIN YO'Q (ya'ni `PUBLIC`): `fn_audit_row()` `SECURITY
    DEFINER` EMAS, shuning uchun u DML qilayotgan rol nomidan yozadi — bu
    `sbozor_app` ham, migratsiya/seed paytida `sbozor_owner` ham bo'lishi
    mumkin. Policy'ni bitta rolga bog'lash ikkinchisining yozuvini jimgina
    yo'qotardi.

    Bu — `tests/tenancy/test_meta.py::test_app_role_policies_all_reference_tenant_guc`
    dagi YAGONA hujjatlashtirilgan istisno. Uning xavfsiz bo'lishining sababi:
    predikatsiz ruxsat faqat YOZISHDA berilgan; O'QISH esa
    `audit_read_policy()` orqali to'liq tenant-scoped.
    """
    return PGPolicy(
        schema="public",
        signature=AUDIT_APPEND_SIGNATURE,
        on_entity="public.audit_log",
        definition="""
            AS PERMISSIVE
            FOR INSERT
            WITH CHECK (true)
        """,
    )


def audit_read_policy() -> PGPolicy:
    """`audit_log` dan O'QISH — oddiy tenant predikatiga to'liq bo'ysunadi (D-11).

    `UPDATE` va `DELETE` uchun policy ATAYIN YARATILMAYDI. Bu — o'zgarmaslik
    zanjirining 2-QATLAMI: policy'siz komanda hech qanday qatorni KO'RMAYDI,
    ya'ni jadval egasiga qarshi ham `UPDATE 0` / `DELETE 0` qaytadi. Diqqat:
    bu JIMGINA himoya, exception EMAS — shuning uchun uning testi "xato
    bo'ldimi?" emas, "holat o'zgarmadimi?" ni tekshiradi (Pitfall 9).

    `market_id IS NULL` bo'lgan platforma-global yozuvlar bu predikat ostida
    hech kimga ko'rinmaydi. Bu ataylab: ular platforma admini uchun alohida
    tor yo'l bilan beriladi — `audit_read_platform_policy()` +
    `auth_list_platform_audit()` (0005), umumiy o'qish yuzasi orqali emas.
    """
    return PGPolicy(
        schema="public",
        signature=AUDIT_READ_SIGNATURE,
        on_entity="public.audit_log",
        definition=f"""
            AS PERMISSIVE
            FOR SELECT
            USING ({TENANT_PREDICATE})
        """,
    )


def audit_read_platform_policy() -> PGPolicy:
    """`audit_log` dagi PLATFORMA-GLOBAL (`market_id IS NULL`) qatorlarni ochadi.

    Bu jadvaldagi UCHINCHI policy va u `owner_bootstrap_policy()` bilan AYNAN
    bir qolipda ishlaydi: EGAGA tor yo'l ochadi, ilova roliga emas.

    NEGA UMUMAN KERAK (Gap 5 — 01-06, 01-07, 01-09 SUMMARY'larida uch marta
    ketma-ket ochiq qayd etilgan): `login_failed` kabi yozuvlar ataylab
    `market_id = NULL` bilan yoziladi, `audit_read` predikati esa
    `market_id = app.market_id` — ya'ni bu qatorlar HECH QANDAY tenant
    konteksti bilan mos kelmaydi va mahsulot yo'lida HECH KIMGA ko'rinmaydi.
    Ular faqat test-superuseri bilan o'qilardi, ya'ni "kim tizimga kirishga
    urinmoqda" savoli FOUND-03 ostida javobsiz qolardi.

    NEGA YOLG'IZ `SECURITY DEFINER` YETMAYDI: `audit_log` da RLS ENABLE+FORCE
    va `sbozor_owner` `NOSUPERUSER NOBYPASSRLS`. FORCE tufayli EGA HAM
    policy'ga bo'ysunadi, ya'ni ega uchun birorta `SELECT` policy'si bo'lmasa
    natija deny-all bo'ladi va `SECURITY DEFINER` funksiya (u ega nomidan
    ishlaydi) **0 qator** qaytarardi. `users` naqshi (funksiya global jadvalni
    o'qiydi) bu yerda ISHLAMAYDI, chunki `users` da RLS umuman yo'q.

    NEGA `TO sbozor_owner`: haqiqiy xavfsizlik chegarasi — `sbozor_app`.
    Ilova FAQAT o'sha rol bilan ulanadi va bu policy unga UMUMAN qo'llanmaydi,
    ya'ni ilova `SELECT ... FROM audit_log WHERE market_id IS NULL` yozsa
    baribir 0 qator oladi. NULL qatorlarga yagona yo'l — grant qilingan
    `auth_list_platform_audit()` funksiyasi, ya'ni yuza aniq, tor va
    greplanadigan bo'lib qoladi.

    NEGA `FOR SELECT`, `FOR ALL` EMAS (BU BAND KRITIK): `audit_log` ga
    `owner_bootstrap` policy'si ATAYIN berilmagan, chunki u `FOR ALL ...
    USING (true)` bo'lib egaga `UPDATE`/`DELETE` da qatorlarni ko'rsatib
    qo'yardi va o'zgarmaslikning 2-QATLAMINI bir zarbada yo'q qilardi
    (`migrations/versions/0002_audit.py`). Bu policy esa FAQAT `SELECT` —
    `UPDATE`/`DELETE` uchun baribir birorta policy yo'q, ya'ni 2-qatlam
    o'zgarishsiz qoladi va `tests/integration/test_audit_immutable.py`
    yashil turaveradi.

    Ikki meta-test qulflaydi:
      * `test_audit_read_platform_is_owner_only` — rollar AYNAN
        `{sbozor_owner}` va komanda AYNAN `SELECT`;
      * `test_audit_read_policy_is_tenant_scoped` — `audit_log` policy'lari
        to'plami aynan shu uchtasi (`w`/`d` paydo bo'lishi darhol qizaradi).
    """
    return PGPolicy(
        schema="public",
        signature=AUDIT_READ_PLATFORM_SIGNATURE,
        on_entity="public.audit_log",
        definition=f"""
            AS PERMISSIVE
            FOR SELECT
            TO {OWNER_ROLE}
            USING ({PLATFORM_AUDIT_PREDICATE})
        """,
    )
