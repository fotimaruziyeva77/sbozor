"""Tenant izolyatsiyasi META-TESTLARI — rol invariantlari (FOUND-02).

Bu 1-fazaning eng qimmatli artefaktlaridan biri: u keyingi 7 fazada RLS
regressiyasini doimiy ushlab turadi.

NEGA ROLLAR, NEGA POLICY EMAS:
`FORCE ROW LEVEL SECURITY` faqat jadval EGASINI policy'ga bo'ysundiradi.
Superuser va `BYPASSRLS` atributli rollar RLS'ni HAR DOIM chetlab o'tadi —
va agar test fixture'i o'sha rol bilan ulansa, keyingi barcha RLS testlari
YOLG'ON-YASHIL beradi. Shuning uchun rol invariantlari birinchi qulflanadi.

SXEMA INVARIANTLARI (01-04): bu fayl endi rol invariantlaridan tashqari
SXEMA invariantlarini ham qulflaydi va ular HAR YANGI JADVALNI avtomatik
qamrab oladi — ro'yxat qo'lda yuritilmaydi, `pg_catalog` dan o'qiladi.
Yangi jadval qo'shgan odam RLS'ni unutsa, u testni "yangilashi" kerak
bo'ladi, ya'ni unutish ko'rinmas emas, ATAYIN qilingan harakatga aylanadi.

Istisnolar YAGONA manbada — `sbozor_core.schema_contract.GLOBAL_TABLES`.
Ro'yxat bu faylda TAKRORLANMAYDI.
"""

from __future__ import annotations

import re

import psycopg
import pytest
from psycopg import Connection
from psycopg.rows import TupleRow
from sbozor_core.models.identity import LOCALE_VALUES, ROLE_VALUES
from sbozor_core.schema_contract import AUDITED_TABLES, FINANCIAL_TABLES, GLOBAL_TABLES
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from migrations.helpers import audit_trigger_name

pytestmark = pytest.mark.tenancy

TENANT_GUC = "app.market_id"

# `market_id` bilan BOSHLANMASLIGI ruxsat etilgan indekslar. Har biri uchun
# sabab shu yerda yozilishi SHART — ro'yxat o'sib ketsa, u sharh bilan
# birga code review'da ko'rinadi.
INDEX_EXCEPTIONS = {
    # Refresh cookie kelganda bozor HALI noma'lum: token aynan shu global
    # kalit bo'yicha topiladi va bozor undan keyin aniqlanadi.
    "uq_refresh_tokens_jti",
}

EXPECTED_DEFINER_FUNCTIONS = {
    # 0001 — login bootstrap (O'QISH yuzasi, Pattern 2)
    "auth_find_login",
    "auth_memberships",
    "auth_list_markets",
    "auth_user_state",
    # 0003 — sessiya va parol (YOZISH yuzasi). `refresh_tokens` ham shu
    # yerda, chunki refresh cookie kelganda bozor hali noma'lum va RLS
    # `jti` bo'yicha global qidiruvni 0 qatorga tushiradi.
    "auth_find_login_by_id",
    "auth_update_password_hash",
    "auth_set_active",
    "auth_refresh_issue",
    "auth_refresh_find",
    "auth_refresh_rotate",
    "auth_refresh_revoke_family",
    "auth_refresh_revoke_user",
    # 0004 — foydalanuvchi boshqaruvi va profil. `users` app-rolga butunlay
    # yopiq, ya'ni yaratish, profil o'qish va til saqlash ham shu yuzadan
    # o'tadi; `auth_list_markets_full` esa `timezone` bilan bozor ro'yxati.
    "auth_create_user",
    "auth_set_locale",
    "auth_list_users",
    "auth_list_markets_full",
    # 0005 — platforma-global (`market_id IS NULL`) audit qatorlari. Bu
    # funksiya boshqalardan farqli o'laroq RLS QO'YILGAN jadvalni o'qiydi,
    # ya'ni u yolg'iz o'zi yetarli emas: `audit_read_platform` policy'si
    # bilan juftlikda ishlaydi (pastdagi alohida test).
    "auth_list_platform_audit",
    # 0007 — bozor hayot sikli (Pattern 6). `sbozor_app` ga `markets` da
    # FAQAT `SELECT` grant'i berilgan va policy predikati `id =
    # app.market_id`, ya'ni yangi bozor yaratishga ikki mustaqil to'siq bor —
    # yagona yo'l shu uchta funksiya.
    #
    # ⚠ `market_is_open` bu ro'yxatga HECH QACHON QO'SHILMAYDI: u ATAYIN
    # `SECURITY DEFINER` EMAS (u CHAQIRUVCHI huquqi bilan ishlashi va RLS
    # ostida qolishi kerak, aks holda bir bozor boshqasining bayram jadvalini
    # o'qiy olardi — T-02-22/T-02-41). U `0010` da tug'iladi va uning INVOKER
    # ekani `test_market_domain_meta.py` da ALOHIDA qulflanadi.
    # `market_delete_draft` esa `SECURITY DEFINER` va u ham `0010` da — nomi
    # o'sha yerda qo'shiladi (02-06).
    "market_create",
    "market_activate",
    "market_rename",
}

# `AUDITED_TABLES` da RO'YXATGA OLINGAN, lekin jadval hali TUG'ILMAGAN nomlar.
#
# Reyestr (`sbozor_core.schema_contract.AUDITED_TABLES`) 2-fazaning boshida,
# birinchi migratsiyadan OLDIN to'ldirildi — ATAYIN. Teskari tartib (avval
# migratsiya, keyin reyestr) darvozani vaqtincha ochiq qoldirardi: triggersiz
# jadval hech qayerda ko'rinmasdan o'tib ketishi mumkin bo'lardi.
#
# NEGA BU "SHUNCHAKI QIZIL TEST" EMAS: bu ro'yxat 02-05 va 02-06 migratsiyalari
# yozilgunga qadar 16 ta rejaning har birida `npm run test:tenancy` ni qizil
# qilib turardi va o'sha 16 reja uchun darvoza SIGNAL BERMAY qolardi — "mening
# o'zgarishim tenancy'ni buzdimi yoki bu o'sha ma'lum qizilmi?" savoliga javob
# yo'qolardi. Buzilgan darvoza — darvoza emas.
#
# Ro'yxat IKKI TOMONLAMA qulflangan (pastdagi `==` solishtiruvi):
#   * trigger ULANSA  -> `missing` kichrayadi -> test QIZARADI va migratsiya
#     muallifini shu ro'yxatdan nomni o'chirishga majbur qiladi. Ya'ni qarz
#     jimgina "yopilib" ketolmaydi.
#   * mavjud trigger YO'QOLSA (masalan `user_market_roles`) -> `missing`
#     kattalashadi -> test QIZARADI. Ya'ni amaldagi kafolat susaymaydi.
#
# Bu `INDEX_EXCEPTIONS` va `POLICY_TENANT_GUC_EXCEPTIONS` bilan bir xil naqsh:
# istisno testda, sababi yozma, o'zgartirish code review'da ko'zga tashlanadi.
PENDING_AUDIT_TRIGGERS = frozenset(
    {
        # 02-06 (`0010_calendar`): yopiq kun istisnolari
        "market_calendar_exceptions",
    }
)

# Ilova roliga tenant predikatisiz ruxsat beruvchi policy'lar. Har biri uchun
# sabab SHU YERDA yozilishi SHART — istisno qo'shish code review'da ko'zga
# tashlanadigan, ataylab qilingan harakat bo'lib qolsin.
POLICY_TENANT_GUC_EXCEPTIONS = {
    # `audit_log` ga YOZISH hech qachon bloklanmasligi kerak: tenant
    # kontekstisiz bajarilgan har qanday o'zgarish (fon job, migratsiya,
    # admin skripti) aks holda audit yozuvini jimgina yo'qotardi — ya'ni eng
    # kam nazorat qilinadigan yo'l eng kam iz qoldirardi. Istisno FAQAT
    # `WITH CHECK` ga tegishli; O'QISH (`audit_read`) to'liq tenant-scoped
    # va u pastdagi `test_audit_read_policy_is_tenant_scoped` bilan alohida
    # qulflangan.
    ("audit_log", "audit_append"),
}

# (policyname, roles, qual, with_check)
type PolicyRow = tuple[str, list[str], str, str | None]


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


def test_btree_gist_extension_is_installed(sync_app_conn: Connection[TupleRow]) -> None:
    """`btree_gist` bazada MAVJUD — ya'ni init qadami haqiqatan bajarilgan.

    `ops/db/init/00-extensions.sql` prod'da `docker-entrypoint-initdb.d`
    orqali, testda esa `_bootstrap_extensions` fixture'i orqali ishlaydi.
    Ikkinchisi jimgina o'chirilsa yoki fixture bog'liqligi uzilsa, sabab
    faqat 02-05 migratsiyasi yozilganda — ya'ni bir necha reja keyin —
    ko'rinardi. Bu test uni SHU ZAHOTI ko'rsatadi.

    Kengaytma `stall_assignments` dagi `EXCLUDE USING gist (market_id
    WITH =, stall_id WITH =, period WITH &&)` uchun kerak: `uuid`/`date`
    skalyar tiplarining GiST operator klasslarini aynan u beradi.

    `sync_app_conn` ATAYIN — `pg_extension` ni ilova roli ham o'qiy oladi
    va tekshiruv aynan ilova ko'radigan haqiqatga tegishli.
    """
    row = sync_app_conn.execute(
        "SELECT extname FROM pg_extension WHERE extname = 'btree_gist'"
    ).fetchone()
    assert row is not None, (
        "`btree_gist` kengaytmasi yo'q — `ops/db/init/00-extensions.sql` "
        "bajarilmagan. `sbozor_owner` uni O'ZI o'rnata olmaydi "
        "(`permission denied to create extension`), ya'ni migratsiya bu "
        "holatni tuzata olmaydi."
    )


def test_no_bypassrls_role_exists(sync_app_conn: Connection[TupleRow]) -> None:
    """Klasterda superuser bo'lmagan `BYPASSRLS` roli YO'Q (D-06 / T-01-24).

    Platforma admini bozorni TANLAB kiradi va tanlagan bozorining oddiy
    tenant policy'siga bo'ysunadi. `BYPASSRLS` roli paydo bo'lishi — bu
    qarorni jimgina bekor qilish yo'li, shuning uchun butun klaster
    tekshiriladi, faqat ma'lum ikki rol emas.
    """
    rows = sync_app_conn.execute(
        "SELECT rolname FROM pg_roles WHERE rolbypassrls AND NOT rolsuper"
    ).fetchall()
    assert rows == [], (
        f"BYPASSRLS atributli rol(lar) topildi: {[r[0] for r in rows]} — "
        "ular RLS'ni butunlay chetlab o'tadi va D-06 ni buzadi"
    )


# ===========================================================================
# SXEMA INVARIANTLARI (01-04) — har yangi jadval avtomatik qamraladi
# ===========================================================================


def _base_tables(conn: Connection[TupleRow]) -> list[str]:
    """`public` sxemadagi barcha oddiy jadvallar."""
    rows = conn.execute(
        "SELECT c.relname FROM pg_class c "
        "JOIN pg_namespace n ON n.oid = c.relnamespace "
        "WHERE n.nspname = 'public' AND c.relkind = 'r' "
        "ORDER BY c.relname"
    ).fetchall()
    return [row[0] for row in rows]


def _has_column(conn: Connection[TupleRow], table: str, column: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM pg_attribute a "
        "JOIN pg_class c ON c.oid = a.attrelid "
        "JOIN pg_namespace n ON n.oid = c.relnamespace "
        "WHERE n.nspname = 'public' AND c.relname = %s AND a.attname = %s "
        "AND a.attnum > 0 AND NOT a.attisdropped",
        (table, column),
    ).fetchone()
    return row is not None


def _rls_flags(conn: Connection[TupleRow], table: str) -> tuple[bool, bool]:
    row = conn.execute(
        "SELECT c.relrowsecurity, c.relforcerowsecurity FROM pg_class c "
        "JOIN pg_namespace n ON n.oid = c.relnamespace "
        "WHERE n.nspname = 'public' AND c.relname = %s",
        (table,),
    ).fetchone()
    assert row is not None, f"{table} jadvali `pg_class` da topilmadi"
    return bool(row[0]), bool(row[1])


def _policies(conn: Connection[TupleRow], table: str) -> list[PolicyRow]:
    rows = conn.execute(
        "SELECT policyname, roles, qual, with_check FROM pg_policies "
        "WHERE schemaname = 'public' AND tablename = %s ORDER BY policyname",
        (table,),
    ).fetchall()
    return [(r[0], list(r[1]), r[2], r[3]) for r in rows]


def test_every_table_is_tenant_scoped(sync_app_conn: Connection[TupleRow], migrated: None) -> None:
    """Har bir jadval: `market_id` + RLS ENABLE + FORCE + policy.

    Uchtasi ham kerak va uchtasi ham ALOHIDA buzilishi mumkin:
      * `market_id` yo'q -> jadval umuman tenant'ga bog'lanmagan;
      * ENABLE yo'q      -> policy TA'SIRSIZ, hamma narsa ochiq (Pitfall 10);
      * FORCE yo'q       -> ega (migratsiya roli) policy'dan chetda qoladi;
      * policy yo'q      -> RLS bor, lekin deny-all (fail-closed, lekin ilova ishlamaydi).
    """
    tables = _base_tables(sync_app_conn)
    assert tables, "`public` sxemada birorta jadval yo'q — migratsiya bajarilmagan"

    problems: list[str] = []
    checked = 0
    for table in tables:
        if table in GLOBAL_TABLES:
            continue
        checked += 1
        if not _has_column(sync_app_conn, table, "market_id"):
            problems.append(f"{table}: `market_id` ustuni yo'q")
            continue
        enabled, forced = _rls_flags(sync_app_conn, table)
        if not enabled:
            problems.append(f"{table}: `ENABLE ROW LEVEL SECURITY` yo'q")
        if not forced:
            problems.append(f"{table}: `FORCE ROW LEVEL SECURITY` yo'q")
        if not _policies(sync_app_conn, table):
            problems.append(f"{table}: birorta policy yo'q")

    assert checked > 0, (
        "birorta tenant jadval tekshirilmadi — GLOBAL_TABLES butun sxemani "
        "yutib yuborgan bo'lishi mumkin"
    )
    assert not problems, "Tenant invariantlari buzilgan:\n  " + "\n  ".join(problems)


def test_markets_rls_and_policy(sync_app_conn: Connection[TupleRow], migrated: None) -> None:
    """`markets` MAXSUS HOLATINING alohida isboti (RESEARCH Open Question 4).

    `markets` `GLOBAL_TABLES` da, ya'ni yuqoridagi umumiy tsikldan chiqib
    ketadi. Istisno qilingan jadval tekshiruvsiz qolmasligi SHART, shuning
    uchun uning RLS'i va policy'si shu yerda qulflanadi: predikat
    `market_id = ...` EMAS, `id = ...` — chunki `markets` da tenant kaliti
    `id` ning O'ZI.
    """
    enabled, forced = _rls_flags(sync_app_conn, "markets")
    assert enabled, "markets: `ENABLE ROW LEVEL SECURITY` yo'q"
    assert forced, "markets: `FORCE ROW LEVEL SECURITY` yo'q"

    policies = _policies(sync_app_conn, "markets")
    assert policies, "markets: birorta policy yo'q"

    app_policies = [p for p in policies if "sbozor_app" in p[1]]
    assert app_policies, "markets: `sbozor_app` uchun policy yo'q"

    quals = " ".join(p[2] or "" for p in app_policies)
    # DIQQAT: `market_id` satri GUC NOMIDA ham bor (`app.market_id`), shuning
    # uchun tekshiruv USTUN havolasi bo'yicha — ya'ni `<ustun> =` shakli
    # bo'yicha — qilinadi, oddiy substring bo'yicha emas.
    assert re.search(r"\bid\s*=", quals), "markets policy'si `id` ustuni bilan solishtirmayapti"
    assert not re.search(r"\bmarket_id\s*=", quals), (
        "markets policy'si `market_id` USTUNIGA murojaat qilmoqda — bunday "
        "ustun yo'q, tenant kaliti `id` ning o'zi"
    )
    assert "NULLIF" in quals.upper(), (
        "markets policy'sida `NULLIF` yo'q — pool'dagi ulanishda "
        '`invalid input syntax for type uuid: ""` beradi (Pitfall 1)'
    )
    assert TENANT_GUC in quals, f"markets policy'si `{TENANT_GUC}` GUC'iga tayanmaydi"


def test_tenant_indexes_lead_with_market_id(
    sync_app_conn: Connection[TupleRow], migrated: None
) -> None:
    """Tenant jadvallarining indekslari `market_id` bilan boshlanadi (P9).

    Ikkinchi qatlam filtri (`TenantScopedRepository`) har so'rovga
    `market_id = ...` qo'shadi; indeks boshqa ustundan boshlansa,
    rejalashtiruvchi uni ishlata olmaydi va bozor kattalashgan sari
    so'rovlar sekinlashadi.
    """
    rows = sync_app_conn.execute(
        "SELECT t.relname, i.relname, x.indisprimary, a.attname "
        "FROM pg_index x "
        "JOIN pg_class t ON t.oid = x.indrelid "
        "JOIN pg_class i ON i.oid = x.indexrelid "
        "JOIN pg_namespace n ON n.oid = t.relnamespace "
        "JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = x.indkey[0] "
        "WHERE n.nspname = 'public' AND t.relkind = 'r' "
        "ORDER BY t.relname, i.relname"
    ).fetchall()

    problems: list[str] = []
    for table, index, is_primary, first_column in rows:
        if table in GLOBAL_TABLES or is_primary or index in INDEX_EXCEPTIONS:
            continue
        if first_column != "market_id":
            problems.append(f"{table}.{index}: birinchi ustun `{first_column}`, `market_id` emas")

    assert not problems, (
        "Indekslar `market_id` bilan boshlanmayapti:\n  "
        + "\n  ".join(problems)
        + "\n(atayin istisno bo'lsa `INDEX_EXCEPTIONS` ga sabab bilan qo'shing)"
    )


def test_security_definer_functions_pin_search_path(
    sync_app_conn: Connection[TupleRow], migrated: None
) -> None:
    """Har bir `SECURITY DEFINER` funksiya `search_path` ni pin qiladi (T-01-23).

    Pin qilinmasa chaqiruvchi o'z sxemasida soxta `users` jadvali yaratib
    funksiyani unga qaratishi mumkin — klassik privilege escalation.
    Test butun `public` sxemani skanerlaydi, ya'ni kelajakdagi funksiyalar
    ham avtomatik qamraladi.
    """
    rows = sync_app_conn.execute(
        "SELECT p.proname, p.proconfig FROM pg_proc p "
        "JOIN pg_namespace n ON n.oid = p.pronamespace "
        "WHERE n.nspname = 'public' AND p.prosecdef ORDER BY p.proname"
    ).fetchall()

    found = {row[0] for row in rows}
    assert found >= EXPECTED_DEFINER_FUNCTIONS, (
        f"kutilgan login funksiyalari yo'q: {sorted(EXPECTED_DEFINER_FUNCTIONS - found)}"
    )

    for name, proconfig in rows:
        assert proconfig, f"{name}: `SECURITY DEFINER`, lekin `proconfig` bo'sh"
        assert any(item.startswith("search_path=") for item in proconfig), (
            f"{name}: `SET search_path = ...` yo'q — privilege escalation vektori"
        )


def test_auth_memberships_returns_is_active(
    sync_app_conn: Connection[TupleRow], migrated: None
) -> None:
    """`auth_memberships()` qaytish to'plamida `is_active boolean` bor (0006).

    NEGA BU ALOHIDA DARVOZA: funksiyaning IMZOSI (`auth_memberships(uuid)`)
    o'zgarmadi, faqat QAYTISH TIPI kengaydi. Ya'ni `EXPECTED_DEFINER_FUNCTIONS`,
    `GRANT_SIGNATURES` va mavjud bootstrap testlarining birortasi ham eski
    (uch ustunli) ta'rif tiklanib qolganini KO'RMAYDI: nom joyida, grant
    joyida, `search_path` joyida. Nosozlik faqat ilova qatlamida —
    `auth_repo.memberships()` da `column "is_active" does not exist` bo'lib
    chiqardi va sababi migratsiyada emas, repozitoriyda izlanardi.

    `pg_get_function_result()` bazadagi AMALDAGI ta'rifni o'qiydi, entity
    modulini emas — ya'ni test `0006` migratsiyasi HAQIQATAN bajarilganini
    tekshiradi, kod nusxasini emas.
    """
    row = sync_app_conn.execute(
        "SELECT pg_get_function_result('public.auth_memberships(uuid)'::regprocedure)"
    ).fetchone()

    assert row is not None, "`auth_memberships(uuid)` funksiyasi bazada yo'q"
    result_type = row[0]
    assert "is_active boolean" in result_type, (
        f"`auth_memberships()` qaytish to'plami: {result_type!r} — `is_active boolean` yo'q. "
        "Qoralama bozor (`markets.is_active = false`) a'zolik tarmog'ida "
        "'faol' deb yolg'on yorliqlanadi (UI-SPEC §12.1.1 X-2)"
    )


def test_app_role_policies_all_reference_tenant_guc(
    sync_app_conn: Connection[TupleRow], migrated: None
) -> None:
    """`sbozor_app` ga tegishli HAR BIR policy tenant GUC'iga tayanadi.

    Bu — butun dizaynning qulfi: ilova roliga `USING (true)` bergan bitta
    policy barcha tenant izolyatsiyasini bir zarbada yo'q qiladi va boshqa
    hech qanday test buni ko'rmaydi (hamma so'rov "muvaffaqiyatli" qaytadi,
    faqat begona qatorlar bilan).
    """
    rows = sync_app_conn.execute(
        "SELECT tablename, policyname, roles, qual, with_check FROM pg_policies "
        "WHERE schemaname = 'public' ORDER BY tablename, policyname"
    ).fetchall()
    assert rows, "birorta policy yo'q — migratsiya bajarilmagan"

    problems: list[str] = []
    for table, policy, roles, qual, with_check in rows:
        role_names = set(roles)
        if not ({"sbozor_app", "public"} & role_names):
            continue
        if (table, policy) in POLICY_TENANT_GUC_EXCEPTIONS:
            continue
        for label, expression in (("USING", qual), ("WITH CHECK", with_check)):
            if expression is None:
                continue
            if TENANT_GUC not in expression:
                problems.append(f"{table}.{policy} {label}: `{TENANT_GUC}` ga murojaat yo'q")

    assert not problems, (
        "Ilova roliga tenant filtri qo'ymaydigan policy topildi:\n  "
        + "\n  ".join(problems)
        + "\n(atayin istisno bo'lsa `POLICY_TENANT_GUC_EXCEPTIONS` ga sabab bilan qo'shing)"
    )


def test_audit_read_policy_is_tenant_scoped(
    sync_app_conn: Connection[TupleRow], migrated: None
) -> None:
    """`audit_append` istisnosi O'QISH tomoniga TARQALMAGAN (D-11).

    Yuqoridagi test `audit_log` uchun bitta istisnoga ruxsat beradi. Bu test
    o'sha istisnoning CHEGARASINI belgilaydi: `audit_log` da `SELECT`
    policy'si bo'lishi va u tenant GUC'iga tayanishi SHART. Aks holda
    "yozishni bloklab bo'lmaydi" degan to'g'ri qoida "hamma hammaning
    auditini o'qiy oladi" degan noto'g'ri natijaga aylanib ketardi.

    Shuningdek `UPDATE`/`DELETE` uchun policy YO'Q ekani tekshiriladi — bu
    o'zgarmaslikning 2-qatlami va u tasodifan qo'shilgan policy bilan
    jimgina yo'qoladi.

    UCHINCHI POLICY (`audit_read_platform`, 0005) — ATAYIN va u APP-ROLNING
    o'qish yuzasini KENGAYTIRMAYDI: u `TO sbozor_owner`, ya'ni `sbozor_app`
    uni umuman ishlata olmaydi, va u faqat `market_id IS NULL` qatorlarni
    ochadi — tenant qatorlari bilan kesishmaydi. Uning owner-only ekani
    pastdagi `test_audit_read_platform_is_owner_only` da alohida qulflanadi;
    bu yerda esa TO'PLAM qulflanadi: `w`/`d` komandali policy paydo bo'lishi
    (yoki bu uchtasidan biri yo'qolishi) darhol qizaradi.
    """
    rows = sync_app_conn.execute(
        "SELECT p.polname, p.polcmd FROM pg_policy p "
        "JOIN pg_class c ON c.oid = p.polrelid "
        "WHERE c.relname = 'audit_log' ORDER BY p.polname"
    ).fetchall()

    commands = {row[0]: row[1] for row in rows}
    assert commands == {
        "audit_append": "a",
        "audit_read": "r",
        "audit_read_platform": "r",
    }, (
        f"`audit_log` policy'lari kutilganidan farq qiladi: {commands} — "
        "`w` (UPDATE) yoki `d` (DELETE) policy'si paydo bo'lsa jadval "
        "egasiga qarshi o'zgarmaslikning 2-qatlami yo'qoladi"
    )

    read_qual = sync_app_conn.execute(
        "SELECT qual FROM pg_policies "
        "WHERE schemaname = 'public' AND tablename = 'audit_log' AND policyname = 'audit_read'"
    ).fetchone()
    assert read_qual is not None
    assert TENANT_GUC in (read_qual[0] or ""), (
        "`audit_read` policy'si tenant GUC'iga tayanmayapti — boshqa bozor "
        "auditi ko'rinadigan bo'lib qoladi"
    )


def test_audit_log_is_read_only_for_app_role(
    sync_app_conn: Connection[TupleRow], migrated: None
) -> None:
    """1-QATLAM: `sbozor_app` da faqat `SELECT` va `INSERT` huquqi bor (T-01-30).

    Bu qatlam BALAND OVOZDA ishlaydi (`permission denied`), qolgan uchtasi
    esa jimroq — shuning uchun u birinchi va eng muhim.
    """
    row = sync_app_conn.execute(
        "SELECT has_table_privilege('sbozor_app', 'audit_log', 'SELECT'), "
        "       has_table_privilege('sbozor_app', 'audit_log', 'INSERT'), "
        "       has_table_privilege('sbozor_app', 'audit_log', 'UPDATE'), "
        "       has_table_privilege('sbozor_app', 'audit_log', 'DELETE'), "
        "       has_table_privilege('sbozor_app', 'audit_log', 'TRUNCATE')"
    ).fetchone()
    assert row is not None
    can_select, can_insert, can_update, can_delete, can_truncate = row

    assert can_select, "sbozor_app `audit_log` ni o'qiy olmaydi — audit ekrani ishlamaydi"
    assert can_insert, "sbozor_app `audit_log` ga yoza olmaydi — trigger har DML da yiqiladi"
    assert not can_update, "sbozor_app `audit_log` ni TAHRIRLAY oladi (T-01-30)"
    assert not can_delete, "sbozor_app `audit_log` dan O'CHIRA oladi (T-01-30)"
    assert not can_truncate, "sbozor_app `audit_log` ni TRUNCATE qila oladi (T-01-32)"


def test_audit_trigger_function_is_not_security_definer(
    sync_app_conn: Connection[TupleRow], migrated: None
) -> None:
    """`fn_audit_row()` ATAYIN `SECURITY DEFINER` EMAS (T-01-35).

    `audit_log` da `WITH CHECK (true)` policy'si va app-rolga `INSERT` grant'i
    bor, ya'ni trigger chaqiruvchi huquqi bilan bemalol yozadi. Ega huquqiga
    ko'tarish hech qanday qo'shimcha imkoniyat bermaydi, faqat
    privilege-escalation yuzasini ochadi.

    `search_path` esa SHUNDA HAM pin qilinishi shart: trigger DML qilayotgan
    sessiyaning `search_path` i bilan ishlaydi va chaqiruvchi o'z sxemasida
    soxta `audit_log` yaratib yozuvni o'sha yerga burib yuborishi mumkin.
    """
    rows = sync_app_conn.execute(
        "SELECT p.proname, p.prosecdef, p.proconfig FROM pg_proc p "
        "JOIN pg_namespace n ON n.oid = p.pronamespace "
        "WHERE n.nspname = 'public' AND p.proname IN ('fn_audit_row', 'audit_immutable') "
        "ORDER BY p.proname"
    ).fetchall()

    found = {row[0] for row in rows}
    assert found == {"audit_immutable", "fn_audit_row"}, (
        f"audit trigger funksiyalari yo'q yoki nomi o'zgargan: {sorted(found)}"
    )

    for name, is_definer, proconfig in rows:
        assert not is_definer, (
            f"{name} `SECURITY DEFINER` bo'lib qolgan — bu ataylab qilingan "
            "qarorning bekor qilinishi (T-01-35)"
        )
        assert proconfig and "search_path=pg_catalog, public" in proconfig, (
            f"{name}: `SET search_path = pg_catalog, public` yo'q — chaqiruvchi "
            "soxta `audit_log` yaratib audit yozuvini burib yuborishi mumkin"
        )


def test_audit_log_business_date_is_stored_generated(
    sync_app_conn: Connection[TupleRow], migrated: None
) -> None:
    """`audit_log.business_date` — STORED generated ustun (FOUND-05).

    `attgenerated = 's'` bo'lmasa ustun oddiy `date` bo'lib qoladi va uni
    ilova to'ldirishi kerak bo'ladi — ya'ni mintaqa arifmetikasi ikkinchi
    marta, boshqa qatlamda takrorlanadi va aynan yarim tun atrofida farq
    qiladi (Anti-Pattern 10).
    """
    row = sync_app_conn.execute(
        "SELECT a.attgenerated FROM pg_attribute a "
        "JOIN pg_class c ON c.oid = a.attrelid "
        "JOIN pg_namespace n ON n.oid = c.relnamespace "
        "WHERE n.nspname = 'public' AND c.relname = 'audit_log' "
        "AND a.attname = 'business_date'"
    ).fetchone()
    assert row is not None, "`audit_log.business_date` ustuni yo'q"
    assert row[0] == "s", (
        f"`business_date` generated STORED emas (attgenerated={row[0]!r}) — "
        "biznes-kun endi DB kafolati emas"
    )


def test_owner_bootstrap_policies_are_owner_only(
    sync_app_conn: Connection[TupleRow], migrated: None
) -> None:
    """`owner_bootstrap` policy'si FAQAT `sbozor_owner` ga berilgan.

    Bu policy `SECURITY DEFINER` login funksiyalari FORCE ostida bloklanib
    qolmasligi uchun bor (`migrations/entities/policies.py` da batafsil).
    U `sbozor_app` ga yoki `PUBLIC` ga kengaysa, ilova roli bir zarbada
    barcha bozorlarni ko'radi — shuning uchun rollar ro'yxati qulflanadi.
    """
    rows = sync_app_conn.execute(
        "SELECT tablename, roles FROM pg_policies "
        "WHERE schemaname = 'public' AND policyname = 'owner_bootstrap' "
        "ORDER BY tablename"
    ).fetchall()
    assert rows, "birorta `owner_bootstrap` policy yo'q"

    for table, roles in rows:
        assert set(roles) == {"sbozor_owner"}, (
            f"{table}.owner_bootstrap `{sorted(roles)}` rollariga berilgan — "
            "faqat `sbozor_owner` bo'lishi shart"
        )


def test_audit_read_platform_is_owner_only(
    sync_app_conn: Connection[TupleRow], migrated: None
) -> None:
    """`audit_read_platform` FAQAT `sbozor_owner` ga va FAQAT `SELECT` uchun (Gap 5).

    Bu — 0005 ning butun xavfsizlik da'vosi bitta testda. Uchala shart
    ALOHIDA buzilishi mumkin va har biri boshqa nosozlik beradi:

      * rollar kengaysa (`sbozor_app` yoki `PUBLIC`) -> ilova roli
        platforma-global audit qatorlarini TO'G'RIDAN-TO'G'RI o'qiy oladi va
        `auth_list_platform_audit()` darvozasi ma'nosiz bo'lib qoladi;
      * komanda `ALL` ga aylansa -> egaga `UPDATE`/`DELETE` da qatorlar
        KO'RINADI va o'zgarmaslikning 2-qatlami yo'qoladi (aynan shu sababdan
        `audit_log` ga `owner_bootstrap` berilmagan);
      * predikat kengaysa (`market_id IS NULL` o'rniga `true`) -> policy
        BUTUN audit jurnalini ochadi, ya'ni `SECURITY DEFINER` funksiya
        orqali tenant qatorlari ham sizib chiqishi mumkin bo'lardi.

    Uchtasi ham `pg_policies` dan o'qiladi, kod ta'rifidan emas — ya'ni test
    fabrikaning nusxasini emas, BAZADAGI haqiqatni tekshiradi.
    """
    rows = sync_app_conn.execute(
        "SELECT roles, cmd, qual FROM pg_policies "
        "WHERE schemaname = 'public' AND tablename = 'audit_log' "
        "AND policyname = 'audit_read_platform'"
    ).fetchall()
    assert len(rows) == 1, (
        "`audit_read_platform` policy'si topilmadi — `market_id IS NULL` "
        "audit qatorlari yana hech kimga ko'rinmaydi (Gap 5)"
    )

    roles, cmd, qual = rows[0]

    assert set(roles) == {"sbozor_owner"}, (
        f"audit_read_platform `{sorted(roles)}` rollariga berilgan — faqat "
        "`sbozor_owner` bo'lishi shart, aks holda `sbozor_app` platforma-global "
        "qatorlarni to'g'ridan-to'g'ri o'qiy oladi"
    )
    assert cmd == "SELECT", (
        f"audit_read_platform komandasi `{cmd}` — `FOR ALL`/`UPDATE`/`DELETE` "
        "egaga o'zgartirish yo'lini ochadi va o'zgarmaslikning 2-qatlamini "
        "yo'q qiladi"
    )
    assert (qual or "").strip() == "(market_id IS NULL)", (
        f"audit_read_platform predikati `{qual}` — u AYNAN `market_id IS NULL` "
        "bo'lishi shart, aks holda policy tenant qatorlarini ham ochadi"
    )


def _check_literals(conn: Connection[TupleRow], constraint: str) -> set[str]:
    """Konstrayt ta'rifidagi matn literallarini ajratib oladi."""
    row = conn.execute(
        "SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conname = %s",
        (constraint,),
    ).fetchone()
    assert row is not None, f"{constraint} konstrayti topilmadi"
    return set(re.findall(r"'([^']+)'::text", row[0]))


def test_role_check_constraint_matches_enum(
    sync_app_conn: Connection[TupleRow], migrated: None
) -> None:
    """DB dagi rol ro'yxati `sbozor_core.enums.Role` bilan AYNAN mos.

    Enum'ga yangi rol qo'shilib migratsiya unutilsa, ilova o'sha rolni
    yozmoqchi bo'lganda `check constraint` xatosi bilan yiqilardi —
    va sabab kod bilan sxema orasidagi jimgina drift bo'lardi.
    """
    assert _check_literals(sync_app_conn, "ck_user_market_roles_roles_allowed") == set(ROLE_VALUES)


def test_locale_check_constraint_matches_enum(
    sync_app_conn: Connection[TupleRow], migrated: None
) -> None:
    """DB dagi til ro'yxati `sbozor_core.enums.Locale` bilan AYNAN mos (D-13)."""
    assert _check_literals(sync_app_conn, "ck_users_locale_allowed") == set(LOCALE_VALUES)


def test_audited_tables_have_trigger(sync_app_conn: Connection[TupleRow], migrated: None) -> None:
    """`AUDITED_TABLES` reyestri va amaldagi triggerlar AYNAN mos.

    Reyestr (`sbozor_core.schema_contract`) va amaldagi DDL
    (`migrations/versions/*.py`) ikki alohida joyda yashaydi, ya'ni ular
    ajralib ketishi mumkin. Bu darvoza ikkalasini `pg_trigger` bilan
    solishtiradi: 2- va 6-fazalarda `payments` yoki `daily_charges`
    yaratilib `attach_audit_trigger()` unutilsa, CI shu yerda qizaradi —
    va bu "audit bor" degan yolg'on ishonchdan ancha arzon.

    Solishtiruv `not missing` EMAS, `missing == PENDING_AUDIT_TRIGGERS`:
    reyestr birinchi migratsiyadan OLDIN to'ldirilgan (2-faza), ya'ni hali
    tug'ilmagan jadvallar unda ATAYIN bor. Tenglik ikkala yo'nalishni ham
    qulflaydi — sabab va mexanika `PENDING_AUDIT_TRIGGERS` yonida.
    """
    rows = sync_app_conn.execute(
        "SELECT c.relname, t.tgname FROM pg_trigger t "
        "JOIN pg_class c ON c.oid = t.tgrelid "
        "JOIN pg_namespace n ON n.oid = c.relnamespace "
        "WHERE n.nspname = 'public' AND NOT t.tgisinternal"
    ).fetchall()
    triggers = {(row[0], row[1]) for row in rows}

    missing = {
        table for table in AUDITED_TABLES if (table, audit_trigger_name(table)) not in triggers
    }

    regressed = missing - PENDING_AUDIT_TRIGGERS
    assert not regressed, (
        f"`AUDITED_TABLES` da bor, lekin audit triggeri YO'Q: {sorted(regressed)} — "
        "jadval o'zgarishlari izsiz qoladi (D-10)"
    )

    closed = PENDING_AUDIT_TRIGGERS - missing
    assert not closed, (
        f"{sorted(closed)} jadval(lar)iga audit triggeri ULANGAN, lekin ular hamon "
        "`PENDING_AUDIT_TRIGGERS` ro'yxatida — nomni o'sha ro'yxatdan O'CHIRING. "
        "Aks holda kelajakda trigger yo'qolsa bu test buni SEZMAY qolardi."
    )


def test_financial_tables_have_guards(sync_app_conn: Connection[TupleRow], migrated: None) -> None:
    """MAVJUD moliyaviy jadvallarning har birida uchta konstrayt bor (mezon #5).

    1-fazada `FINANCIAL_TABLES` dagi jadvallarning HECH BIRI hali yo'q
    (ular 2- va 6-fazalarda tug'iladi), ya'ni bu test HOZIRCHA vakuum —
    lekin u vakuum bo'lib QOLMAYDI: jadval paydo bo'lgan kuni darvoza
    avtomatik yopiladi va `financial_guards()` chaqirilmagan bo'lsa CI
    qizaradi. Reyestrni oldindan yozishning butun ma'nosi shu.

    Uch talab (har biri boshqa nosozlikni yopadi):
      * `business_date` STORED generated ustuni  -> biznes-kun chegarasi;
      * `CHECK (<amount> > 0)`                    -> pul musbat va `bigint`;
      * `market_id` bilan boshlanadigan UNIQUE    -> kun yopilishi idempotent.
    """
    existing = set(_base_tables(sync_app_conn)) & FINANCIAL_TABLES

    problems: list[str] = []
    for table in sorted(existing):
        generated = sync_app_conn.execute(
            "SELECT a.attgenerated FROM pg_attribute a "
            "JOIN pg_class c ON c.oid = a.attrelid "
            "JOIN pg_namespace n ON n.oid = c.relnamespace "
            "WHERE n.nspname = 'public' AND c.relname = %s AND a.attname = 'business_date'",
            (table,),
        ).fetchone()
        if generated is None or generated[0] != "s":
            problems.append(f"{table}: `business_date` STORED generated ustuni yo'q")

        checks = sync_app_conn.execute(
            "SELECT pg_get_constraintdef(c.oid) FROM pg_constraint c "
            "WHERE c.contype = 'c' AND c.conrelid = %s::regclass",
            (table,),
        ).fetchall()
        if not any(re.search(r"amount_soum\s*>\s*0", row[0]) for row in checks):
            problems.append(f"{table}: `CHECK (amount_soum > 0)` yo'q")

        uniques = sync_app_conn.execute(
            "SELECT (SELECT a.attname FROM pg_attribute a "
            "        WHERE a.attrelid = c.conrelid AND a.attnum = c.conkey[1]) "
            "FROM pg_constraint c WHERE c.contype = 'u' AND c.conrelid = %s::regclass",
            (table,),
        ).fetchall()
        if not any(row[0] == "market_id" for row in uniques):
            problems.append(f"{table}: `market_id` bilan boshlanadigan UNIQUE konstrayt yo'q")

    assert not problems, (
        "Moliyaviy jadval `financial_guards()` siz yaratilgan:\n  "
        + "\n  ".join(problems)
        + "\n(`migrations/helpers.py::financial_guards()` ni chaqiring)"
    )


def test_users_table_is_closed_to_app_role(
    sync_app_conn: Connection[TupleRow], migrated: None
) -> None:
    """`users` da `sbozor_app` uchun HECH QANDAY huquq yo'q (T-01-25)."""
    row = sync_app_conn.execute(
        "SELECT bool_or(has_table_privilege('sbozor_app', 'users', priv)) "
        "FROM unnest(ARRAY['SELECT','INSERT','UPDATE','DELETE','REFERENCES','TRIGGER']) AS priv"
    ).fetchone()
    assert row is not None
    assert row[0] is False, (
        "sbozor_app `users` jadvaliga huquqqa ega — global identifikatsiya "
        "ma'lumoti ORM orqali o'qilishi mumkin bo'lib qoladi"
    )
