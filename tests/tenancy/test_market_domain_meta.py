"""Bozor domenining META-TESTLARI — ALEMBIC KO'RMAYDIGAN narsalar uchun darvoza.

=============================================================================
NEGA BU FAYL ALOHIDA MAVJUD (02-RESEARCH Pitfall 2, empirik):

`alembic revision --autogenerate` sxemaning katta qismini kuzatadi, LEKIN
uchta sinf obyekt uning ko'rish maydonidan BUTUNLAY tashqarida qoladi:

  1. **TRIGGERLAR.** `alembic-utils` trigger FUNKSIYASINI boshqaradi, lekin
     triggerning O'ZINI emas — u migratsiyada xom `op.execute("CREATE
     TRIGGER ...")` bilan yoziladi (`0002_audit.py` da o'rnatilgan naqsh).
     Ya'ni funksiya joyida turib, trigger jimgina yo'qolishi mumkin va
     autogenerate hech narsa demaydi. D-02 va D-07 kafolatlari esa AYNAN
     triggerlarda yashaydi.

  2. **`ExcludeConstraint`.** O'lchangan (Alembic 1.18.5 + SQLAlchemy 2.0.51,
     `compare_metadata()`): model va DB bir xil bo'lganda diff **0 element**
     (soxta drift yo'q — bu yaxshi), LEKIN konstrayt modeldan OLIB
     TASHLANGANDA ham diff **0 element** — ya'ni yo'qolish SEZILMAYDI.
     `ex_stall_assignments_no_overlap` (`0009_vendors`) uchun YAGONA darvoza —
     pastdagi `test_stall_assignments_has_exclusion_constraint`.

  3. **Funksiyaning HUQUQ REJIMI.** `prosecdef` / `proconfig` / `provolatile`
     autogenerate uchun ko'rinmas: `SECURITY DEFINER` ni tasodifan qo'shish
     yoki `SET search_path` ni tushirib qoldirish diff bermaydi.

Shuning uchun bu yerdagi testlar `pg_trigger` / `pg_proc` / `pg_attribute` /
`pg_constraint` dan O'QIYDI — entity modulining nusxasidan emas. Ular
quyidagi `test_autogenerate_is_empty` ni ALMASHTIRMAYDI, TO'LDIRADI.
=============================================================================
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date
from typing import Any
from uuid import UUID

import psycopg
import pytest
import sqlalchemy as sa
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from fixtures.market_domain import (
    A_STALL_CODES_BY_SORT,
    GAP_DAY,
    HANDOVER_DAY,
    MarketDomainSeed,
    cleanup_market_domain,
    seed_market_domain,
    to_pg_period,
)
from psycopg import Connection, sql
from psycopg.rows import TupleRow
from sbozor_core.models import Base

pytestmark = pytest.mark.tenancy

# `pg_trigger.tgtype` bit maskalari (`src/include/catalog/pg_trigger.h`).
# Ular RAQAM sifatida yozilgan, chunki Postgres ularni matn sifatida
# ochmaydi: `pg_get_triggerdef()` matni o'qishga qulay, lekin MASHINA
# haqiqati aynan shu bitlarda va ular formatlash o'zgarishidan qat'i nazar
# barqaror qoladi.
TRIGGER_ROW = 1 << 0
TRIGGER_BEFORE = 1 << 1
TRIGGER_INSERT = 1 << 2
TRIGGER_DELETE = 1 << 3
TRIGGER_UPDATE = 1 << 4

DOMAIN_TRIGGER_FUNCTIONS = (
    "stall_code_claim",
    "tariff_past_immutable",
    "category_period_past_immutable",
)

MARKET_WRITE_FUNCTIONS = ("market_create", "market_activate", "market_rename")

PENDING_DOMAIN_TABLES: frozenset[str] = frozenset()
"""BO'SH — 02-06 (`0009_vendors` + `0010_calendar`) qarzni to'liq yopdi.

Ro'yxat `tests/tenancy/test_meta.py::PENDING_AUDIT_TRIGGERS` bilan AYNAN bir
xil naqshda ishlaydi va pastdagi `test_autogenerate_is_empty` uni IKKI
TOMONLAMA qulflagan edi:

  * jadval TUG'ILSA  -> `missing` kichrayadi -> test QIZARADI va migratsiya
    muallifini nomni shu ro'yxatdan o'chirishga majbur qiladi. O'sha
    daqiqadan boshlab jadval to'liq autogenerate solishtiruviga tushadi,
    ya'ni qarz jimgina "yopilib" ketolmaydi.
  * mavjud jadval YO'QOLSA yoki modelda BO'LMAGAN jadval paydo bo'lsa ->
    test QIZARADI.

RO'YXAT BO'SHAGANI TESTNI ZAIFLASHTIRMAYDI, KUCHAYTIRADI: `include_object`
filtri endi HECH NIMANI chiqarib tashlamaydi va `compare_metadata()` butun
sxemani (o'nta domen jadvali bilan) qamraydi.
"""

_CLEAN_ORDER = (
    "stall_code_registry",
    "stalls",
    "zones",
    "stall_categories",
    "market_profile",
)
"""Probe ma'lumotini o'chirish tartibi — FK bo'yicha bolalardan ota-onaga."""

EXCLUSION_CONSTRAINT = "ex_stall_assignments_no_overlap"

DOMAIN_TABLES_FOR_CLEANUP_CHECK = (
    "stall_assignments",
    "stall_category_periods",
    "tariffs",
    "stall_code_registry",
    "stalls",
    "vendors",
    "zones",
    "stall_categories",
    "market_profile",
)
"""`cleanup_market_domain()` bo'shatishi SHART bo'lgan jadvallar."""

_INSERT_ASSIGNMENT = (
    "INSERT INTO stall_assignments (market_id, stall_id, vendor_id, period) VALUES (%s, %s, %s, %s)"
)


def _one(conn: Connection[TupleRow], sql: str, params: tuple[Any, ...] | None = None) -> Any:
    """Bitta qator qaytaradi va uning MAVJUDLIGINI talab qiladi."""
    row = conn.execute(sql, params).fetchone()
    assert row is not None, f"so'rov 0 qator qaytardi: {sql}"
    return row


def _trigger(conn: Connection[TupleRow], table: str, name: str) -> tuple[int, str, str]:
    """`(tgtype, trigger funksiyasi, to'liq ta'rif)`."""
    return _one(  # type: ignore[no-any-return]
        conn,
        "SELECT t.tgtype, t.tgfoid::regproc::text, pg_get_triggerdef(t.oid) "
        "FROM pg_trigger t JOIN pg_class c ON c.oid = t.tgrelid "
        "JOIN pg_namespace n ON n.oid = c.relnamespace "
        "WHERE n.nspname = 'public' AND c.relname = %s AND t.tgname = %s "
        "AND NOT t.tgisinternal",
        (table, name),
    )


@pytest.fixture
def probe_market(
    sync_app_conn: Connection[TupleRow],
    sync_owner_conn: Connection[TupleRow],
    migrated: None,
) -> Iterator[tuple[UUID, UUID]]:
    """Qoralama bozor + bitta zona, tenant konteksti O'RNATILGAN holda.

    Bozor `market_create()` ORQALI yaratiladi — `INSERT INTO markets` bilan
    EMAS. Sabab: aynan shu yo'l mahsulot yo'li (Pattern 6) va u
    `market_profile` qatorini ham bir tranzaksiyada tug'diradi. Fixture
    to'g'ridan-to'g'ri `INSERT` qilganida `test_app_role_cannot_insert_markets`
    da'vosini o'zi buzgan bo'lardi.

    Tozalash `sbozor_owner` bilan: `sbozor_app` `markets` dan `DELETE` qila
    olmaydi (unga faqat `SELECT` grant'i berilgan).
    """
    market_id: UUID = _one(
        sync_app_conn,
        "SELECT market_create(%s, '', DATE '2026-01-01', NULL, '', '', '', '', '')",
        ("Meta-test bozori",),
    )[0]
    sync_app_conn.execute("SELECT set_config('app.market_id', %s, false)", (str(market_id),))
    zone_id: UUID = _one(
        sync_app_conn,
        "INSERT INTO zones (market_id, name) VALUES (%s, 'A zona') RETURNING id",
        (market_id,),
    )[0]
    try:
        yield market_id, zone_id
    finally:
        sync_app_conn.execute("SELECT set_config('app.market_id', '', false)")
        for table in _CLEAN_ORDER:
            # `psycopg.sql.Identifier` — jadval nomi satr birlashtirish bilan
            # emas, quotalangan identifikator sifatida qo'yiladi (conftest.py
            # dagi `_bootstrap_roles` bilan bir xil naqsh).
            sync_owner_conn.execute(
                sql.SQL("DELETE FROM {} WHERE market_id = %s").format(sql.Identifier(table)),
                (market_id,),
            )
        sync_owner_conn.execute("DELETE FROM markets WHERE id = %s", (market_id,))


# ===========================================================================
# TRIGGERLAR — autogenerate ularni UMUMAN ko'rmaydi
# ===========================================================================


def test_stall_code_claim_trigger_exists(
    sync_app_conn: Connection[TupleRow], migrated: None
) -> None:
    """`trg_stall_code_claim` `stalls` da va u AFTER INSERT/UPDATE OF code (D-02).

    Bu trigger yo'qolsa `stall_code_registry` jadvali BO'SH qolaveradi va
    D-02 kafolati jimgina yo'qoladi: hech qanday xato chiqmaydi, faqat
    yopilgan rastaning raqami yangi rastaga o'tib ketaveradi va hisobotdagi
    "12-rasta" yillar davomida ikki xil jismoniy joyni anglatadi.

    ⚠ `AFTER`, `BEFORE` EMAS — va bu ATAYIN tekshiriladi. 02-RESEARCH
    Pattern 8 `BEFORE INSERT` deb yozgan edi, lekin `BEFORE` paytida `stalls`
    qatori hali yozilmagan bo'ladi va reyestrdagi composite FK darhol
    buziladi (02-04 da o'lchandi: `Key (market_id, stall_id)=(...) is not
    present in table "stalls"`). Ya'ni bu assertion "BEFORE ga qaytarish"
    regressiyasini bloklaydi.
    """
    tgtype, function, definition = _trigger(sync_app_conn, "stalls", "trg_stall_code_claim")

    assert function == "stall_code_claim", (
        f"`trg_stall_code_claim` `{function}()` ni chaqirmoqda — D-02 kafolati boshqa "
        "funksiyaga ulanib qolgan"
    )
    assert tgtype & TRIGGER_ROW, (
        "trigger `FOR EACH ROW` emas — kod har bir rasta uchun tekshiriladi"
    )
    assert not tgtype & TRIGGER_BEFORE, (
        "trigger `BEFORE` ga qaytarilgan — `stalls` qatori hali yozilmagan bo'ladi va "
        "`fk_stall_code_registry_market_id_stall_id_stalls` darhol buziladi (02-04 da o'lchangan)"
    )
    assert tgtype & TRIGGER_INSERT, (
        "trigger `INSERT` ni qamramaydi — yangi rasta reyestrga tushmaydi"
    )
    assert tgtype & TRIGGER_UPDATE, (
        "trigger `UPDATE` ni qamramaydi — kodni tahrirlash orqali D-02 chetlab o'tiladi"
    )
    assert "UPDATE OF code" in definition, (
        f"trigger ta'rifida `UPDATE OF code` yo'q: {definition!r} — har qanday ustun "
        "yangilanishida ishga tushish keraksiz yuk, `code` siz esa kafolat yo'q"
    )


@pytest.mark.parametrize(
    ("table", "trigger_name", "function_name"),
    [
        ("tariffs", "trg_tariff_past_immutable", "tariff_past_immutable"),
        (
            "stall_category_periods",
            "trg_category_period_past_immutable",
            "category_period_past_immutable",
        ),
    ],
)
def test_past_immutable_trigger_exists(
    sync_app_conn: Connection[TupleRow],
    migrated: None,
    table: str,
    trigger_name: str,
    function_name: str,
) -> None:
    """O'tmish qulfi IKKALA temporal jadvalda ham bor (D-04 / D-07, T-02-31).

    Ikkalasi ham tekshiriladi va bu takror EMAS: faqat tarifni qulflab toifa
    davrini ochiq qoldirish qo'riqchini BUTUNLAY bekor qilardi — o'tmishdagi
    rastani "arzon" toifaga surib qo'yish narxni o'zgartirish bilan bir xil
    natija beradi.

    `BEFORE` bu yerda MAJBURIY (`stall_code_claim` bilan teskari talab):
    qo'riqchi o'zgarishni SODIR BO'LISHIDAN OLDIN to'xtatishi kerak.
    """
    tgtype, function, _definition = _trigger(sync_app_conn, table, trigger_name)

    assert function == function_name, f"`{trigger_name}` `{function}()` ni chaqirmoqda"
    assert tgtype & TRIGGER_ROW, f"`{trigger_name}` `FOR EACH ROW` emas"
    assert tgtype & TRIGGER_BEFORE, (
        f"`{trigger_name}` `AFTER` ga o'tkazilgan — o'zgarish ALLAQACHON yozilgan bo'lardi"
    )
    assert tgtype & TRIGGER_UPDATE, f"`{trigger_name}` `UPDATE` ni qamramaydi (retroaktiv tahrir)"
    assert tgtype & TRIGGER_DELETE, (
        f"`{trigger_name}` `DELETE` ni qamramaydi — o'tmishdagi qatorni O'CHIRISH uni "
        "o'zgartirish bilan bir xil natija beradi"
    )


def test_domain_trigger_functions_are_not_security_definer(
    sync_app_conn: Connection[TupleRow], migrated: None
) -> None:
    """Uchala domen trigger funksiyasi `SECURITY DEFINER` EMAS, lekin `search_path` PIN qilingan.

    `fn_audit_row()` bilan AYNAN bir xil qaror (T-01-35): triggerlar
    chaqiruvchi huquqi bilan bemalol ishlaydi (`stall_code_registry` tenant
    policy'si ostida va `sbozor_app` ga `INSERT` grant'i bor), ya'ni ega
    huquqiga ko'tarish HECH QANDAY qo'shimcha imkoniyat bermaydi — faqat
    privilege-escalation yuzasini ochadi.

    `SET search_path` esa SHUNDA HAM majburiy: trigger DML qilayotgan
    sessiyaning `search_path` i bilan ishlaydi va chaqiruvchi o'z sxemasida
    soxta `stall_code_registry` yaratib kafolatni chetlab o'tishi mumkin
    bo'lardi.
    """
    rows = sync_app_conn.execute(
        "SELECT p.proname, p.prosecdef, p.proconfig FROM pg_proc p "
        "JOIN pg_namespace n ON n.oid = p.pronamespace "
        "WHERE n.nspname = 'public' AND p.proname = ANY(%s) ORDER BY p.proname",
        (list(DOMAIN_TRIGGER_FUNCTIONS),),
    ).fetchall()

    found = {row[0] for row in rows}
    assert found == set(DOMAIN_TRIGGER_FUNCTIONS), (
        f"domen trigger funksiyalari yo'q yoki nomi o'zgargan: {sorted(found)}"
    )

    for name, is_definer, proconfig in rows:
        assert not is_definer, (
            f"{name}() `SECURITY DEFINER` bo'lib qolgan — bu ataylab qilingan qarorning "
            "bekor qilinishi (T-01-35 bilan bir xil sabab)"
        )
        assert proconfig and "search_path=pg_catalog, public" in proconfig, (
            f"{name}(): `SET search_path = pg_catalog, public` yo'q — chaqiruvchi o'z "
            "sxemasida soxta jadval yaratib qoidani chetlab o'tishi mumkin"
        )


# ===========================================================================
# `markets` GA YOZISH YUZASI (Pattern 6, T-02-35)
# ===========================================================================


def test_app_role_cannot_insert_markets(
    sync_app_conn: Connection[TupleRow], migrated: None
) -> None:
    """`sbozor_app` `markets` ga TO'G'RIDAN-TO'G'RI yoza olmaydi.

    Bu — `market_create()` ning YAGONA yo'l ekanining darvozasi. Grant
    berilib qolsa funksiya "qulaylik" ga aylanadi va uning ichidagi literal
    `is_active = false` (ya'ni `activate` to'liqlik tekshiruvi) butunlay
    chetlab o'tiladi (T-02-35).

    ⚠ `InsufficientPrivilege` (42501) KUTILADI, RLS xatosi emas: `markets` da
    ikki mustaqil to'siq bor va BIRINCHISI grant'ning yo'qligi. Agar bir kun
    grant berilsa, bu test qizaradi va sabab darhol ko'rinadi — RLS'ning
    ikkinchi qatlami esa yashirin himoya bo'lib qolaverardi.
    """
    with pytest.raises(psycopg.errors.InsufficientPrivilege) as excinfo:
        sync_app_conn.execute("INSERT INTO markets (name) VALUES ('qo''lda yaratilgan')")

    assert "markets" in str(excinfo.value)


def test_market_write_functions_are_security_definer(
    sync_app_conn: Connection[TupleRow], migrated: None
) -> None:
    """Bozor yozish funksiyalari — `SECURITY DEFINER` + pin qilingan `search_path`.

    Yuqoridagi test yagona yo'lni QULFLAYDI, bu esa o'sha yo'lning ISHLASH
    SHARTINI: funksiya ega huquqi bilan ishlamasa `markets` ga baribir yoza
    olmaydi va usta 1-qadamda yiqiladi.

    `PUBLIC` dan `REVOKE` ham shu yerda tekshiriladi: Postgres yangi
    funksiyaga `EXECUTE TO PUBLIC` ni STANDART beradi, ya'ni `REVOKE`
    unutilsa bazadagi HAR QANDAY rol bozor yarata olardi.
    """
    rows = sync_app_conn.execute(
        "SELECT p.proname, p.prosecdef, p.proconfig, "
        "       has_function_privilege('public', p.oid, 'EXECUTE'), "
        "       has_function_privilege('sbozor_app', p.oid, 'EXECUTE') "
        "FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace "
        "WHERE n.nspname = 'public' AND p.proname = ANY(%s) ORDER BY p.proname",
        (list(MARKET_WRITE_FUNCTIONS),),
    ).fetchall()

    found = {row[0] for row in rows}
    assert found == set(MARKET_WRITE_FUNCTIONS), (
        f"bozor yozish funksiyalari yo'q yoki nomi o'zgargan: {sorted(found)}"
    )

    for name, is_definer, proconfig, public_can, app_can in rows:
        assert is_definer, (
            f"{name}() `SECURITY DEFINER` emas — u `markets` ga yoza olmaydi va usta "
            "1-qadamda yiqiladi"
        )
        assert proconfig and "search_path=pg_catalog, public" in proconfig, (
            f"{name}(): `SET search_path = pg_catalog, public` yo'q — klassik "
            "privilege-escalation vektori (T-01-23)"
        )
        assert not public_can, (
            f"{name}() `PUBLIC` uchun ochiq — `REVOKE ALL ... FROM PUBLIC` unutilgan"
        )
        assert app_can, f"{name}() `sbozor_app` uchun yopiq — usta oqimi `permission denied` beradi"


# ===========================================================================
# `code_sort` — inson-raqamli tartib DB kafolati (T-02-36)
# ===========================================================================


def test_stalls_code_sort_is_generated_stored(
    sync_app_conn: Connection[TupleRow], migrated: None
) -> None:
    """`stalls.code_sort` — STORED generated ustun va ifodasi RAQAMNI ajratadi.

    `attgenerated = 's'` bo'lmasa ustun oddiy `text` bo'lib qoladi va uni
    ILOVA to'ldirishi kerak bo'lardi — ya'ni tartiblash kalitining ikkinchi
    haqiqat manbai paydo bo'lardi va ro'yxat bilan xarita boshqa-boshqa
    tartibda chiqardi (`audit_log.business_date` bilan bir xil sabab).
    """
    row = _one(
        sync_app_conn,
        "SELECT a.attgenerated, pg_get_expr(d.adbin, d.adrelid) "
        "FROM pg_attribute a "
        "JOIN pg_class c ON c.oid = a.attrelid "
        "JOIN pg_namespace n ON n.oid = c.relnamespace "
        "LEFT JOIN pg_attrdef d ON d.adrelid = a.attrelid AND d.adnum = a.attnum "
        "WHERE n.nspname = 'public' AND c.relname = 'stalls' AND a.attname = 'code_sort'",
    )
    generated, expression = row

    assert generated == "s", (
        f"`code_sort` generated STORED emas (attgenerated={generated!r}) — inson-raqamli "
        "tartib endi DB kafolati emas"
    )
    assert expression and "regexp_replace" in expression, (
        f"`code_sort` ifodasida `regexp_replace` yo'q: {expression!r} — kod ichidagi "
        "RAQAM ajratilmasa tartib alfavit tartibiga qaytadi"
    )
    assert "lpad" in expression, (
        f"`code_sort` ifodasida `lpad` yo'q: {expression!r} — nol bilan to'ldirishsiz "
        "'2' va '10' baribir matn sifatida solishtiriladi"
    )


def test_stalls_human_numeric_order(
    sync_app_conn: Connection[TupleRow], probe_market: tuple[UUID, UUID]
) -> None:
    """`ORDER BY code_sort` -> `2, 10, 100`; `ORDER BY code` -> BOSHQA tartib.

    IKKINCHI ASSERTION MAJBURIY va u testning butun ma'nosi. Yolg'iz birinchi
    da'vo (`code_sort` to'g'ri tartib beradi) `code_sort` umuman ishlamasa
    ham YASHIL bo'lishi mumkin — masalan kodlar tasodifan alfavit tartibida
    ham to'g'ri chiqadigan qilib tanlansa. Nazorat holati ikkalasini
    ajratadi: agar `ORDER BY code` ham `2, 10, 100` bersa, demak test
    hech narsani isbotlamayapti va shuni aytadi.

    Kodlar (`2`, `10`, `100`) ATAYIN shunday tanlangan: matn tartibida ular
    `10, 100, 2` bo'ladi (o'lchangan) — ya'ni farq bir qarashda ko'rinadi.
    """
    market_id, zone_id = probe_market
    for code in ("2", "10", "100"):
        sync_app_conn.execute(
            "INSERT INTO stalls (market_id, zone_id, code) VALUES (%s, %s, %s)",
            (market_id, zone_id, code),
        )

    by_sort = [
        row[0]
        for row in sync_app_conn.execute(
            "SELECT code FROM stalls WHERE market_id = %s ORDER BY code_sort", (market_id,)
        ).fetchall()
    ]
    by_code = [
        row[0]
        for row in sync_app_conn.execute(
            "SELECT code FROM stalls WHERE market_id = %s ORDER BY code", (market_id,)
        ).fetchall()
    ]

    assert by_sort == ["2", "10", "100"], (
        f"`ORDER BY code_sort` -> {by_sort} — kassir qidirayotgan rasta ko'z bilan "
        "topilmaydigan joyga tushadi (UI-SPEC §7.3)"
    )
    assert by_code != by_sort, (
        f"NAZORAT HOLATI YIQILDI: `ORDER BY code` ham {by_code} berdi. Kodlar shunday "
        "tanlanganki, matn tartibi boshqacha bo'lishi SHART — aks holda bu test "
        "`code_sort` ishlamasa ham yashil bo'lardi"
    )


def test_stall_code_registry_is_populated_by_trigger(
    sync_app_conn: Connection[TupleRow], probe_market: tuple[UUID, UUID]
) -> None:
    """D-02 ning XULQ darajasidagi isboti: chetlangan kod QAYTA ISHLATILMAYDI.

    Yuqoridagi `test_stall_code_claim_trigger_exists` triggerning BORLIGINI
    tekshiradi; bu test uning ISHLASHINI. Ikkalasi ham kerak — trigger
    mavjud bo'lib, funksiya tanasi buzilgan holat birinchisidan o'tib
    ketardi.

    Uchinchi qadam (o'z kodini QAYTARIB OLISH) ham shu yerda: usiz kafolat
    "kodni hech qachon tahrirlab bo'lmaydi" ga aylanib ketardi va tuzatishni
    bekor qilish imkonsiz bo'lardi.
    """
    market_id, zone_id = probe_market
    stall_id = _one(
        sync_app_conn,
        "INSERT INTO stalls (market_id, zone_id, code) VALUES (%s, %s, '12') RETURNING id",
        (market_id, zone_id),
    )[0]

    registered = _one(
        sync_app_conn,
        "SELECT stall_id FROM stall_code_registry WHERE market_id = %s AND code = '12'",
        (market_id,),
    )
    assert registered[0] == stall_id, "reyestr qatori yaratilmadi — trigger ishlamayapti"

    # Kod tahrirlandi -> '12' BO'SHADI, lekin reyestrda o'sha rastaga qadalgan
    sync_app_conn.execute("UPDATE stalls SET code = '99' WHERE id = %s", (stall_id,))

    with pytest.raises(psycopg.errors.UniqueViolation) as excinfo:
        sync_app_conn.execute(
            "INSERT INTO stalls (market_id, zone_id, code) VALUES (%s, %s, '12')",
            (market_id, zone_id),
        )
    assert excinfo.value.sqlstate == "23505", (
        "chetlangan kod `23505` (unique_violation) bilan rad etilishi shart — chaqiruvchi "
        "uni oddiy 'kod band' holati bilan BIR XIL yo'lda 409 ga aylantiradi"
    )

    # O'Z eski kodini qaytarib olish — RUXSAT (tuzatishni bekor qilish)
    sync_app_conn.execute("UPDATE stalls SET code = '12' WHERE id = %s", (stall_id,))


# ===========================================================================
# EXCLUDE KONSTRAYTI (0009) — ALEMBIC BU SINFNI UMUMAN KO'RMAYDI
# ===========================================================================


def test_stall_assignments_has_exclusion_constraint(
    sync_app_conn: Connection[TupleRow], migrated: None
) -> None:
    """`ex_stall_assignments_no_overlap` bazada va u AYNAN kutilgan shaklda.

    ⚠ BU KONSTRAYT UCHUN YAGONA DARVOZA — BOSHQA HECH NARSA UNI USHLAMAYDI.
    O'lchangan (Alembic 1.18.5 + SQLAlchemy 2.0.51): konstrayt modeldan
    OLIB TASHLANGANDA `compare_metadata()` diff'i **0 element** qaytaradi,
    ya'ni `test_autogenerate_is_empty` yashil qolaveradi. Migratsiyadan
    o'chirilsa ham hech kim sezmaydi.

    Yo'qolishining narxi: D-09 ("bir vaqtda 1 rasta = 1 sotuvchi") ilova
    qatlamidagi "avval tekshir, keyin yoz" naqshiga tushib qoladi va u IKKI
    PARALLEL so'rovda ikkalasini ham o'tkazib yuboradi — bir kunda ikkita
    sotuvchi biriktirilgan bo'lib chiqadi va 6-fazadagi qarz egaligi ikkiga
    bo'linadi (T-02-37/T-02-43).

    To'rtala element ham tekshiriladi: `market_id` yo'qolsa konstrayt
    BOZORLARARO qamrab qolardi (A bozoridagi davr B bozoridagi rastani
    bloklardi), `stall_id` yo'qolsa butun bozorda bitta davr qolardi,
    `&&` boshqa operatorga almashsa qoplanish umuman tekshirilmasdi.
    """
    row = sync_app_conn.execute(
        "SELECT pg_get_constraintdef(c.oid) FROM pg_constraint c "
        "JOIN pg_class t ON t.oid = c.conrelid "
        "JOIN pg_namespace n ON n.oid = t.relnamespace "
        "WHERE n.nspname = 'public' AND t.relname = 'stall_assignments' AND c.conname = %s",
        (EXCLUSION_CONSTRAINT,),
    ).fetchone()

    assert row is not None, (
        f"`{EXCLUSION_CONSTRAINT}` konstrayti YO'Q. Alembic buni SEZMAYDI — u "
        "`0009_vendors.py` da LITERAL yozilgan va bu test uning yagona darvozasi"
    )
    definition = row[0]
    for fragment in ("EXCLUDE USING gist", "market_id", "stall_id", "&&"):
        assert fragment in definition, (
            f"konstrayt ta'rifida `{fragment}` yo'q: {definition!r} — D-09 kafolati "
            "kutilganidan tor yoki keng qamrovda ishlaydi"
        )


def test_exclusion_index_leads_with_market_id(
    sync_app_conn: Connection[TupleRow], migrated: None
) -> None:
    """EXCLUDE ostidagi GiST indeksining BIRINCHI ustuni — `market_id` (P9).

    `EXCLUDE` konstrayti o'z indeksini YARATADI va u tenant invariantidan
    (`test_meta.py::test_tenant_indexes_lead_with_market_id`) chetda
    qolmasligi kerak. Ustunlar tartibi almashtirilsa (`stall_id` birinchi)
    konstraytning MA'NOSI o'zgarmaydi — ya'ni yuqoridagi test yashil
    qolaveradi — lekin indeks `WHERE market_id = ...` filtri uchun
    yaroqsiz bo'lib qoladi va bozor kattalashgan sari har bir biriktirish
    so'rovi sekinlashadi.
    """
    row = _one(
        sync_app_conn,
        "SELECT a.attname, am.amname FROM pg_index x "
        "JOIN pg_class t ON t.oid = x.indrelid "
        "JOIN pg_class i ON i.oid = x.indexrelid "
        "JOIN pg_am am ON am.oid = i.relam "
        "JOIN pg_namespace n ON n.oid = t.relnamespace "
        "JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = x.indkey[0] "
        "WHERE n.nspname = 'public' AND t.relname = 'stall_assignments' AND i.relname = %s",
        (EXCLUSION_CONSTRAINT,),
    )
    first_column, access_method = row

    assert access_method == "gist", (
        f"`{EXCLUSION_CONSTRAINT}` indeksi `{access_method}` bilan qurilgan — `&&` "
        "operatori faqat GiST da ishlaydi"
    )
    assert first_column == "market_id", (
        f"EXCLUDE indeksining birinchi ustuni `{first_column}` — tenant filtri bu "
        "indeksdan foydalana olmaydi (P9)"
    )


def test_adjacent_assignments_are_accepted(
    sync_app_conn: Connection[TupleRow], market_domain: MarketDomainSeed
) -> None:
    """NAZORAT HOLATI: qo'shni (kesishmaydigan) davrlar QABUL qilinadi.

    Bu test keyingisidan OLDIN turadi va usiz keyingisi YOLG'ON-YASHIL
    bo'lardi: konstrayt HAR QANDAY ikkinchi davrni rad etayotgan bo'lsa
    ham (masalan `&&` o'rniga tasodifan `=` yozilgan bo'lsa) "qoplanish
    bloklandi" degan xulosa chiqardi. Ikkalasi birga esa aynan
    QOPLANISHNING rad etilishini isbotlaydi.

    Bu D-10 ning o'zi ham: `[)` chegarasida almashinuv kuni ikkala davrga
    tegishli EMAS — u faqat YANGISIGA tegishli, shuning uchun ular
    kesishmaydi.
    """
    a = market_domain.market_a
    stall = a.unassigned_stall_id
    assert stall is not None
    sync_app_conn.execute("SELECT set_config('app.market_id', %s, false)", (str(a.market_id),))
    try:
        sync_app_conn.execute(
            _INSERT_ASSIGNMENT,
            (
                a.market_id,
                stall,
                a.vendor_ids[0],
                to_pg_period(date(2026, 9, 1), date(2026, 9, 10)),
            ),
        )
        sync_app_conn.execute(
            _INSERT_ASSIGNMENT,
            (a.market_id, stall, a.vendor_ids[1], to_pg_period(date(2026, 9, 10), None)),
        )

        both = _one(
            sync_app_conn,
            "SELECT count(*) FROM stall_assignments WHERE market_id = %s AND stall_id = %s",
            (a.market_id, stall),
        )
        assert both[0] == 2, (
            f"qo'shni davrlar qabul qilinmadi ({both[0]} qator) — konstrayt kutilganidan "
            "KENG qamrayapti va sotuvchi almashinuvi umuman imkonsiz bo'lib qolgan"
        )
    finally:
        sync_app_conn.execute("SELECT set_config('app.market_id', '', false)")


def test_overlapping_assignment_is_rejected(
    sync_app_conn: Connection[TupleRow], market_domain: MarketDomainSeed
) -> None:
    """Qoplanuvchi davr `23P01` bilan rad etiladi (D-09, T-02-37).

    SQLSTATE ATAYIN tekshiriladi, xato matni EMAS: RLS yoqilgan jadvalda
    Postgres `EXCLUDE` buzilishining `DETAIL` qatorini BUTUNLAY o'chiradi
    (o'lchangan — ega uchun ham), `exc.orig.constraint_name` esa asyncpg
    o'ramida `None` bo'lib qaytadi. Ya'ni ilova qatlami uchun yagona
    ishonchli diskriminator — `sqlstate`, va u `409
    assignment_period_overlaps` ga aylanadi.
    """
    a = market_domain.market_a
    stall = a.unassigned_stall_id
    assert stall is not None
    sync_app_conn.execute("SELECT set_config('app.market_id', %s, false)", (str(a.market_id),))
    try:
        sync_app_conn.execute(
            _INSERT_ASSIGNMENT,
            (
                a.market_id,
                stall,
                a.vendor_ids[0],
                to_pg_period(date(2026, 9, 1), date(2026, 9, 10)),
            ),
        )
        with pytest.raises(psycopg.errors.ExclusionViolation) as excinfo:
            sync_app_conn.execute(
                _INSERT_ASSIGNMENT,
                (
                    a.market_id,
                    stall,
                    a.vendor_ids[1],
                    to_pg_period(date(2026, 9, 5), date(2026, 9, 20)),
                ),
            )
        assert excinfo.value.sqlstate == "23P01", (
            f"qoplanish `{excinfo.value.sqlstate}` bilan rad etildi, `23P01` emas — ilova "
            "qatlami uni `409 assignment_period_overlaps` dan ajrata olmaydi"
        )
    finally:
        sync_app_conn.execute("SELECT set_config('app.market_id', '', false)")


# ===========================================================================
# SEED KONTRAKTI — downstream testlarning yolg'on-yashil bo'lishini yopadi
# ===========================================================================


def test_seeded_stalls_have_a_category_period(
    sync_app_conn: Connection[TupleRow], market_domain: MarketDomainSeed
) -> None:
    """HAR BIR seed rastasida boshlang'ich toifa davri bor va sanasi to'g'ri.

    BU SEED KONTRAKTINING DARVOZASI (T-02-45a). Qator yo'qolganda 02-08
    dagi "joriy toifa" `LEFT JOIN LATERAL` qidiruvi `NULL` qaytaradi va
    o'sha testlar "toifa YO'Q" bilan "toifa NOTO'G'RI" ni ajrata olmay
    qoladi — nosozlik sababi butunlay boshqa faylda ko'rinardi. Shuning
    uchun buzilish AYNAN shu yerda, seed'ning o'zida ushlanadi.

    `valid_from` = `operating_since` ham tekshiriladi (A3): import kuni
    yozilganda 6-faza `operating_since` dan importgacha bo'lgan har bir
    kunni "toifasiz" deb topib butun tarixni anomaliyaga aylantirardi.

    IKKALA BOZOR ham tekshiriladi — B bozori kichikroq to'plam bo'lgani
    uchun seed'da unutilishi eng oson joy.
    """
    for rows in market_domain.markets:
        sync_app_conn.execute(
            "SELECT set_config('app.market_id', %s, false)", (str(rows.market_id),)
        )
        found: dict[UUID, date] = dict(
            sync_app_conn.execute(
                "SELECT stall_id, min(valid_from) FROM stall_category_periods "
                "WHERE market_id = %s GROUP BY stall_id",
                (rows.market_id,),
            ).fetchall()
        )
        missing = [stall_id for stall_id in rows.stall_ids if stall_id not in found]
        assert not missing, (
            f"{len(missing)} ta rastada toifa davri YO'Q — seed kontrakti buzilgan; "
            "02-08/02-11 testlari buni tushunarsiz joyda yo'qotardi"
        )
        for stall_id in rows.stall_ids:
            assert found[stall_id] == rows.operating_since, (
                f"rasta {stall_id} ning toifa davri `{found[stall_id]}` dan boshlanadi, "
                f"`operating_since` ({rows.operating_since}) dan emas — A3 buzilgan"
            )
    sync_app_conn.execute("SELECT set_config('app.market_id', '', false)")


def test_seeded_category_periods_use_more_than_one_category(
    sync_app_conn: Connection[TupleRow], market_domain: MarketDomainSeed
) -> None:
    """Seed toifalarni rastalar bo'ylab TAQSIMLAYDI, bittasiga jamlamaydi.

    Nazorat holatining o'zi: hamma rasta bitta toifada bo'lsa "toifa
    bo'yicha filtr" testi HECH NIMANI ajratmasdi — filtr umuman
    ishlamaganda ham to'g'ri javob qaytargandek ko'rinardi (u baribir
    hamma rastani qaytarardi).
    """
    a = market_domain.market_a
    sync_app_conn.execute("SELECT set_config('app.market_id', %s, false)", (str(a.market_id),))
    try:
        distinct = _one(
            sync_app_conn,
            "SELECT count(DISTINCT category_id) FROM stall_category_periods WHERE market_id = %s",
            (a.market_id,),
        )
        assert distinct[0] >= 2, (
            f"seed toifa davrlarida atigi {distinct[0]} xil toifa ishlatilgan — toifa "
            "filtri testlari hech nimani ajratmaydi"
        )
    finally:
        sync_app_conn.execute("SELECT set_config('app.market_id', '', false)")


def test_seeded_stalls_are_ordered_by_code_sort(
    sync_app_conn: Connection[TupleRow], market_domain: MarketDomainSeed
) -> None:
    """Seed rastalari `code_sort` bo'yicha INSON-RAQAMLI tartibda chiqadi.

    `test_stalls_human_numeric_order` uch kodli sun'iy probe bilan
    tekshiradi; bu esa AYNAN downstream testlar ishlatadigan seed ustida —
    ya'ni 02-08 dagi ro'yxat kursori (`(code_sort, id)`) tayanadigan
    haqiqiy ma'lumot ustida. Nazorat holati (matn tartibi BOSHQACHA)
    ham shu yerda: usiz kodlar tasodifan alfavit tartibida ham to'g'ri
    chiqadigan qilib tanlangan bo'lsa test hech narsani isbotlamasdi.
    """
    a = market_domain.market_a
    sync_app_conn.execute("SELECT set_config('app.market_id', %s, false)", (str(a.market_id),))
    try:
        by_sort = tuple(
            row[0]
            for row in sync_app_conn.execute(
                "SELECT code FROM stalls WHERE market_id = %s ORDER BY code_sort", (a.market_id,)
            ).fetchall()
        )
        by_code = tuple(
            row[0]
            for row in sync_app_conn.execute(
                "SELECT code FROM stalls WHERE market_id = %s ORDER BY code", (a.market_id,)
            ).fetchall()
        )
    finally:
        sync_app_conn.execute("SELECT set_config('app.market_id', '', false)")

    assert by_sort == A_STALL_CODES_BY_SORT, (
        f"`ORDER BY code_sort` -> {by_sort}, kutilgan {A_STALL_CODES_BY_SORT}"
    )
    assert by_code != by_sort, (
        f"NAZORAT HOLATI YIQILDI: `ORDER BY code` ham {by_code} berdi — seed kodlari "
        "shunday tanlanishi SHART-ki, matn tartibi inson tartibidan farq qilsin"
    )


def test_seeded_assignment_periods_follow_d10_and_d11(
    sync_app_conn: Connection[TupleRow], market_domain: MarketDomainSeed
) -> None:
    """Seed D-10 almashinuvini va D-11 bo'shlig'ini HAQIQATAN ifodalaydi.

    Seed'ning "shunday deb yozilgan" bo'lishi yetarli emas — davrlar DB
    ichida ham kutilgan javobni berishi kerak, aks holda downstream testlar
    noto'g'ri boshlang'ich holat ustida qurilardi:

      * ALMASHINUV KUNI aynan BITTA sotuvchiga tegishli (`[)`). Ikkalasiga
        tegishli bo'lsa o'sha kunning pattasi ikki marta yozilardi;
        hech kimga tegishli bo'lmasa — umuman yozilmasdi.
      * BO'SHLIQ kunida `period @> :d` **0 qator** beradi va bu XATO EMAS
        (D-11 anomaliyasi — 6-faza aynan shuni topadi).
    """
    a = market_domain.market_a
    sync_app_conn.execute("SELECT set_config('app.market_id', %s, false)", (str(a.market_id),))
    try:
        handover = sync_app_conn.execute(
            "SELECT vendor_id FROM stall_assignments "
            "WHERE market_id = %s AND stall_id = %s AND period @> %s::date",
            (a.market_id, a.handover_stall_id, HANDOVER_DAY),
        ).fetchall()
        assert len(handover) == 1, (
            f"almashinuv kunida ({HANDOVER_DAY}) {len(handover)} sotuvchi biriktirilgan — "
            "`[)` konventsiyasi buzilgan; o'sha kunning pattasi ikki marta yoki umuman "
            "yozilmaydi (D-10)"
        )
        assert handover[0][0] == a.vendor_ids[1], (
            "almashinuv kuni ESKI sotuvchida qolgan — `[)` da yuqori chegara davrga "
            "KIRMAYDI, ya'ni kun YANGI sotuvchiniki (D-10)"
        )

        gap = sync_app_conn.execute(
            "SELECT id FROM stall_assignments "
            "WHERE market_id = %s AND stall_id = %s AND period @> %s::date",
            (a.market_id, a.gap_stall_id, GAP_DAY),
        ).fetchall()
        assert gap == [], (
            f"bo'shliq kunida ({GAP_DAY}) sotuvchi topildi — seed D-11 anomaliyasini "
            "ifodalamayapti va 6-faza uni sinay olmaydi"
        )

        unassigned = sync_app_conn.execute(
            "SELECT id FROM stall_assignments WHERE market_id = %s AND stall_id = %s",
            (a.market_id, a.unassigned_stall_id),
        ).fetchall()
        assert unassigned == [], "seed'dagi 'biriktirilmagan rasta' aslida biriktirilgan"
    finally:
        sync_app_conn.execute("SELECT set_config('app.market_id', '', false)")


def test_market_domain_cleanup_leaves_no_rows(
    sync_owner_conn: Connection[TupleRow],
    two_markets: Any,
    migrated: None,
) -> None:
    """`cleanup_market_domain()` ikkala bozorni ham TO'LIQ bo'shatadi.

    ⚠ BU FIXTURE'NI O'ZINI himoyalaydi va u haqiqiy nosozlikni yopadi:
    seed tarif va toifa davrlarini O'TGAN `valid_from` bilan yozadi
    (A3), `two_markets` bozorlari esa `is_active = true` — ya'ni
    o'zgarmaslik triggerlari (D-07) ularni O'CHIRISHNI ham bloklaydi.
    Tozalash bayroqni qoralamaga tushirmasa BIRINCHI `DELETE FROM tariffs`
    da `23514` bilan yiqilardi va har bir test keyingisiga qoldiq
    ma'lumot qoldirardi — cross-tenant testlar esa o'sha qoldiq ustida
    JIMGINA noto'g'ri javob berardi.

    Shuning uchun seed/cleanup bu yerda TO'G'RIDAN-TO'G'RI chaqiriladi,
    `market_domain` fixture'i orqali emas: fixture teardown'idagi istisno
    testni yiqitmasdan "error" sifatida ko'rinishi mumkin edi.
    """
    seed = seed_market_domain(sync_owner_conn, two_markets)
    cleanup_market_domain(sync_owner_conn, seed)

    market_ids = [str(market_id) for market_id in seed.market_ids]
    leftovers = {
        table: _one(
            sync_owner_conn,
            f"SELECT count(*) FROM {table} WHERE market_id = ANY(%s::uuid[])",  # noqa: S608
            (market_ids,),
        )[0]
        for table in DOMAIN_TABLES_FOR_CLEANUP_CHECK
    }

    assert not [table for table, count in leftovers.items() if count], (
        f"tozalashdan keyin qoldiq qatorlar bor: {leftovers}"
    )


# ===========================================================================
# `market_is_open()` — SHU FAZADAGI YAGONA INVOKER FUNKSIYA
# ===========================================================================


def test_market_is_open_is_not_security_definer(
    sync_app_conn: Connection[TupleRow], migrated: None
) -> None:
    """`market_is_open()` CHAQIRUVCHI huquqi bilan ishlaydi (T-02-22/T-02-41).

    ⚠ BU TEST TESKARI YO'NALISHDA ISHLAYDI — u funksiyadan `SECURITY
    DEFINER` ni TALAB QILMAYDI, aksincha TAQIQLAYDI. Shu fayldagi va
    `test_meta.py` dagi qolgan hamma funksiya testi teskarisini talab
    qiladi, shuning uchun bu istisno ataylab va u yozma:

    `SECURITY DEFINER` qilinsa funksiya EGA huquqi bilan ishlardi va
    `owner_bootstrap` policy'si (`USING (true)`) tufayli RLS'dan BUTUNLAY
    chiqib ketardi — ya'ni A bozori `market_is_open(B_id, ...)` chaqirib B
    bozorining bayram/ish kunlari jadvalini o'qiy olardi. Hozir esa ikkala
    subquery ham 0 qator beradi va natija `false` bo'ladi.

    `STABLE` ham tekshiriladi: `VOLATILE` bo'lsa rejalashtiruvchi uni har
    bir qator uchun qayta chaqirardi va 6-fazadagi kunlik job (bir bozorda
    minglab rasta) sezilarli sekinlashardi.

    `EXPECTED_DEFINER_FUNCTIONS` bilan JUFTLIK: u yerda `market_is_open`
    ATAYIN yo'q va sabab izoh bilan yozilgan. Kimdir uni "unutilgan" deb
    o'sha ro'yxatga qo'shsa, ikkita test bir vaqtda buziladi.
    """
    row = _one(
        sync_app_conn,
        "SELECT p.prosecdef, p.provolatile, p.proconfig, "
        "       has_function_privilege('public', p.oid, 'EXECUTE'), "
        "       has_function_privilege('sbozor_app', p.oid, 'EXECUTE') "
        "FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace "
        "WHERE n.nspname = 'public' AND p.proname = 'market_is_open'",
    )
    is_definer, volatility, proconfig, public_can, app_can = row

    assert not is_definer, (
        "`market_is_open()` `SECURITY DEFINER` ga o'tkazilgan — u endi RLS'dan chiqib "
        "ketdi va bir bozor boshqasining kalendarini o'qiy oladi (T-02-41)"
    )
    assert volatility == "s", (
        f"`market_is_open()` volatilligi `{volatility}` — `STABLE` (`s`) bo'lishi kerak, "
        "aks holda u har bir qator uchun qayta chaqiriladi"
    )
    assert proconfig and "search_path=pg_catalog, public" in proconfig, (
        "`market_is_open()` da `SET search_path` yo'q — chaqiruvchi o'z sxemasida soxta "
        "`market_calendar_exceptions` yaratib javobni boshqarishi mumkin"
    )
    assert not public_can, (
        "`market_is_open()` `PUBLIC` uchun ochiq — `REVOKE ALL ... FROM PUBLIC` unutilgan"
    )
    assert app_can, "`market_is_open()` `sbozor_app` uchun yopiq — 6-fazadagi job ishlamaydi"


def test_market_calendar_exceptions_is_audited(
    sync_app_conn: Connection[TupleRow], migrated: None
) -> None:
    """Yopiq kun belgilash audit ostida (MARKET-05, T-02-40).

    Bu jadvalda PUL ustuni yo'q, ya'ni moliyaviy jadvallar auditi uni
    UMUMAN qamramaydi — lekin bir kunni "bayram" deb belgilash o'sha
    kunning BUTUN yig'imini hisobdan chiqaradi. Ya'ni bu tushumni nolga
    tushirishning eng arzon yo'li va undan qoladigan YAGONA iz — shu
    trigger.

    `DELETE` ham qamralishi shart: istisnoni qo'yib, kun o'tgach uni
    O'CHIRIB tashlash izni yo'qotishning eng oddiy usuli bo'lardi.
    """
    tgtype, function, _definition = _trigger(
        sync_app_conn, "market_calendar_exceptions", "trg_audit_market_calendar_exceptions"
    )

    assert function == "fn_audit_row", f"audit triggeri `{function}()` ni chaqirmoqda"
    assert tgtype & TRIGGER_ROW, "audit triggeri `FOR EACH ROW` emas"
    assert not tgtype & TRIGGER_BEFORE, (
        "audit triggeri `BEFORE` ga o'tkazilgan — u SODIR BO'LGAN o'zgarishni qayd etishi "
        "kerak, urinishni emas"
    )
    for bit, name in (
        (TRIGGER_INSERT, "INSERT"),
        (TRIGGER_UPDATE, "UPDATE"),
        (TRIGGER_DELETE, "DELETE"),
    ):
        assert tgtype & bit, (
            f"audit triggeri `{name}` ni qamramaydi — yopiq kun o'zgarishining bir qismi "
            "izsiz qoladi (T-02-40)"
        )


# ===========================================================================
# MODEL <-> SXEMA: autogenerate darvozasi
# ===========================================================================


def test_autogenerate_is_empty(owner_url: str, sync_app_conn: Connection[TupleRow]) -> None:
    """Model va sxema AJRALMAGAN: mavjud jadvallar uchun diff BO'SH.

    ⚠ BU TEKSHIRUV YUQORIDAGI TESTLARNI ALMASHTIRMAYDI. `compare_metadata()`
    ustun/tip/indeks/konstrayt qatlamini ko'radi, LEKIN triggerlarni,
    `ExcludeConstraint` ni va funksiyaning huquq rejimini UMUMAN ko'rmaydi
    (fayl boshidagi uchlik). Ya'ni bu — TO'LDIRUVCHI darvoza.

    ⚠ 02-06 DA DARVOZA KENGAYDI VA BU O'LCHANGAN O'ZGARISH.

    02-05 da bu test `alembic_utils` reyestrini VAQTINCHA bo'shatishga
    majbur edi: uning "schema" komparatori solishtirish uchun har bir
    entity'ni HAQIQATAN yaratib ko'radi (`simulate_entity`), 2-faza yarim
    bo'lgan holatda esa u `CREATE POLICY tenant_isolation ON public.vendors`
    ni bajarishga urinib `UndefinedTable` bilan yiqilardi. Ya'ni policy va
    funksiya qatlami solishtiruvdan CHETDA qolardi.

    `0009`/`0010` bilan hamma jadval tug'ildi va to'liq solishtiruv
    O'LCHANDI: reyestr TO'LIQ holatda (`env.py` dagidek) `compare_metadata()`
    **0 element** qaytaradi. Shuning uchun bo'shatish olib tashlandi va
    tekshiruv endi `ALL_ENTITIES` ni — policy'lar va funksiyalarni ham —
    qamraydi. Bu darvozaning KENGAYISHI: policy ta'rifi bazadan ajralsa
    endi shu yerda ko'rinadi.

    `include_object` filtri ham olib tashlandi: `PENDING_DOMAIN_TABLES`
    bo'sh, ya'ni filtr hech nimani chiqarib tashlamas edi va faqat
    "vaqtincha" degan yolg'on taassurot qoldirardi.

    ⚠ REYESTR BO'SHATISHNI QAYTA TIKLAMANG. Agar bu test bir kun
    `UndefinedTable` bilan yiqilsa, sabab — modelda E'LON QILINGAN, lekin
    migratsiyada YARATILMAGAN jadval. To'g'ri yechim — migratsiyani yozish,
    reyestrni yashirish EMAS (pastdagi birinchi ikki assertion aynan shu
    holatni oldinroq va tushunarliroq xabar bilan ushlaydi).
    """
    declared = set(Base.metadata.tables)
    in_database = {
        row[0]
        for row in sync_app_conn.execute(
            "SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
            "WHERE n.nspname = 'public' AND c.relkind = 'r'"
        ).fetchall()
    }

    missing = declared - in_database
    assert missing == set(PENDING_DOMAIN_TABLES), (
        f"modelda bor, bazada yo'q jadvallar: {sorted(missing)} — kutilgan: "
        f"{sorted(PENDING_DOMAIN_TABLES)}. Jadval tug'ilgan bo'lsa nomni "
        "`PENDING_DOMAIN_TABLES` dan O'CHIRING (aks holda u autogenerate "
        "solishtiruvidan chetda qolib ketardi)"
    )

    extra = in_database - declared - {"alembic_version"}
    assert not extra, (
        f"bazada bor, modelda yo'q jadvallar: {sorted(extra)} — migratsiya modelga "
        "kirmagan jadval yaratgan"
    )

    engine = sa.create_engine(owner_url.replace("postgresql+asyncpg://", "postgresql+psycopg://"))
    try:
        with engine.connect() as connection:
            context = MigrationContext.configure(
                connection,
                opts={
                    "compare_type": True,
                    "include_schemas": False,
                    "target_metadata": Base.metadata,
                },
            )
            diffs = compare_metadata(context, Base.metadata)
    finally:
        engine.dispose()

    assert diffs == [], (
        "model va sxema AJRALGAN — `alembic revision --autogenerate` bo'sh bo'lmaydi:\n  "
        + "\n  ".join(repr(diff) for diff in diffs)
    )
