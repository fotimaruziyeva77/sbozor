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
     TASHLANGANDA ham diff **0 element** — ya'ni yo'qolish SEZILMAYDI. Bu
     sinf `0009_vendors` bilan birga keladi va uning darvozasi 02-06 da shu
     faylga qo'shiladi.

  3. **Funksiyaning HUQUQ REJIMI.** `prosecdef` / `proconfig` / `provolatile`
     autogenerate uchun ko'rinmas: `SECURITY DEFINER` ni tasodifan qo'shish
     yoki `SET search_path` ni tushirib qoldirish diff bermaydi.

Shuning uchun bu yerdagi testlar `pg_trigger` / `pg_proc` / `pg_attribute`
dan O'QIYDI — entity modulining nusxasidan emas. Ular quyidagi
`test_autogenerate_is_empty` ni ALMASHTIRMAYDI, TO'LDIRADI.
=============================================================================

02-06 shu faylga qo'shadi: `stall_assignments` ning EXCLUDE konstrayti va
`market_is_open()` ning INVOKER huquq rejimi.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any
from uuid import UUID

import psycopg
import pytest
import sqlalchemy as sa
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from alembic_utils.pg_function import PGFunction
from alembic_utils.pg_policy import PGPolicy
from alembic_utils.replaceable_entity import register_entities, registry
from psycopg import Connection, sql
from psycopg.rows import TupleRow
from sbozor_core.models import Base

from migrations.entities import ALL_ENTITIES

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

PENDING_DOMAIN_TABLES = frozenset(
    {
        # 02-06 (`0010_calendar`)
        "market_calendar_exceptions",
    }
)
"""`Base.metadata` da E'LON QILINGAN, lekin bazada hali YO'Q jadvallar.

Ro'yxat `tests/tenancy/test_meta.py::PENDING_AUDIT_TRIGGERS` bilan AYNAN bir
xil naqshda ishlaydi va pastdagi `test_autogenerate_is_empty` uni IKKI
TOMONLAMA qulflaydi:

  * jadval TUG'ILSA  -> `missing` kichrayadi -> test QIZARADI va 02-06
    muallifini nomni shu ro'yxatdan o'chirishga majbur qiladi. O'sha
    daqiqadan boshlab jadval to'liq autogenerate solishtiruviga tushadi,
    ya'ni qarz jimgina "yopilib" ketolmaydi.
  * mavjud jadval YO'QOLSA yoki modelda BO'LMAGAN jadval paydo bo'lsa ->
    test QIZARADI.
"""

_CLEAN_ORDER = (
    "stall_code_registry",
    "stalls",
    "zones",
    "stall_categories",
    "market_profile",
)
"""Probe ma'lumotini o'chirish tartibi — FK bo'yicha bolalardan ota-onaga."""


def _one(conn: Connection[TupleRow], sql: str, params: tuple[Any, ...] | None = None) -> Any:
    """Bitta qator qaytaradi va uning MAVJUDLIGINI talab qiladi."""
    row = conn.execute(sql, params).fetchone()
    assert row is not None, f"so'rov 0 qator qaytardi: {sql}"
    return row


def _clear_entity_registry() -> None:
    """`alembic_utils` reyestrini bo'shatadi (`ReplaceableEntityRegistry.clear()`).

    Ignore `migrations/helpers.py::create_entity()` bilan bir xil sababdan
    shu yerda BIR MARTA, izohi bilan yoziladi: `alembic_utils` 0.8.8
    annotatsiyalanmagan va `mypy --strict` uning har bir metod chaqiruvini
    `no-untyped-call` deb belgilaydi. Ignore'ni ikki joyda takrorlash
    o'rniga o'ram funksiya beriladi.
    """
    registry.clear()  # type: ignore[no-untyped-call]


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
# MODEL <-> SXEMA: autogenerate darvozasi
# ===========================================================================


def test_autogenerate_is_empty(owner_url: str, sync_app_conn: Connection[TupleRow]) -> None:
    """Model va sxema AJRALMAGAN: mavjud jadvallar uchun diff BO'SH.

    ⚠ BU TEKSHIRUV YUQORIDAGI TESTLARNI ALMASHTIRMAYDI. `compare_metadata()`
    ustun/tip/indeks/konstrayt qatlamini ko'radi, LEKIN triggerlarni,
    `ExcludeConstraint` ni va funksiyaning huquq rejimini UMUMAN ko'rmaydi
    (fayl boshidagi uchlik). Ya'ni bu — TO'LDIRUVCHI darvoza.

    NEGA `alembic_utils` REYESTRI VAQTINCHA BO'SHATILADI (o'lchangan
    zaruriyat, qulaylik emas): `alembic_utils` ning "schema" komparatori
    solishtirish uchun har bir ro'yxatdagi entity'ni HAQIQATAN yaratib
    ko'radi (`simulate_entity`). 2-faza yarim bo'lgan holatda u `CREATE
    POLICY tenant_isolation ON public.vendors` ni bajarishga urinadi va
    `UndefinedTable: relation "public.vendors" does not exist` bilan
    YIQILADI — ya'ni to'liq `compare_metadata()` faza tugamaguncha texnik
    jihatdan MUMKIN EMAS. Reyestr `ReplaceableEntityRegistry.clear()` /
    `register()` ommaviy API'si bilan boshqariladi va `finally` da AYNAN
    `env.py` dagi holatga tiklanadi.

    Policy va funksiya qatlami baribir qamrovsiz QOLMAYDI — u
    `tests/tenancy/test_meta.py` da `pg_policies`/`pg_proc` dan
    o'qiladi (`test_app_role_policies_all_reference_tenant_guc`,
    `test_owner_bootstrap_policies_are_owner_only`,
    `test_security_definer_functions_pin_search_path`) va yuqoridagi
    `test_market_write_functions_are_security_definer` da.

    IKKI TOMONLAMA QULF: pastdagi birinchi assertion `PENDING_DOMAIN_TABLES`
    ni AYNAN solishtiradi. 02-06 jadvallarni yaratganda test qizaradi va
    muallifni ro'yxatni bo'shatishga majbur qiladi — shu daqiqadan boshlab
    `include_object` filtri hech nimani chiqarib tashlamaydi va tekshiruv
    BUTUN sxemani qamraydi.
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

    def include_object(
        obj: Any, name: str | None, type_: str, reflected: bool, compare_to: Any
    ) -> bool:
        return not (type_ == "table" and name in PENDING_DOMAIN_TABLES)

    engine = sa.create_engine(owner_url.replace("postgresql+asyncpg://", "postgresql+psycopg://"))
    _clear_entity_registry()
    try:
        with engine.connect() as connection:
            context = MigrationContext.configure(
                connection,
                opts={
                    "compare_type": True,
                    "include_schemas": False,
                    "include_object": include_object,
                    "target_metadata": Base.metadata,
                },
            )
            diffs = compare_metadata(context, Base.metadata)
    finally:
        # `env.py` dagi AYNAN o'sha chaqiruv — reyestr keyingi testlar va
        # `alembic revision --autogenerate` uchun to'liq holatda qoladi.
        _clear_entity_registry()
        register_entities(ALL_ENTITIES, entity_types=[PGPolicy, PGFunction])
        engine.dispose()

    assert diffs == [], (
        "model va sxema AJRALGAN — `alembic revision --autogenerate` bo'sh bo'lmaydi:\n  "
        + "\n  ".join(repr(diff) for diff in diffs)
    )
