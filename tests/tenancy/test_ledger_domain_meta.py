"""Daftar reyestrining META-INVARIANTLARI — hammasi `pg_catalog` dan.

=============================================================================
NEGA BU FAYL MODELNI IMPORT QILMAYDI.

`sbozor_core.models.ledger` — ISTALGAN holat. Bazadagi sxema esa HAQIQIY
holat. Ikkisi ajralib qolishi mumkin (migratsiya qo'llanmagan, ustun
keyingi migratsiyada `ALTER TABLE` bilan qo'shilgan, kimdir qo'lda `psql`
ochgan) va aynan o'sha holatda modeldan o'qiydigan test JIMGINA yashil
qolardi. `test_market_domain_meta.py` bu qoidani 2-fazada o'rnatgan,
`test_notification_domain_meta.py` uni 7-fazada davom ettirgan; bu fayl
esa 8-fazada.

⚠ ISTISNO — `test_ledger_is_deliberately_not_a_financial_table()`
`schema_contract` ni ATAYIN import qiladi: uning savoli aynan «REYESTR
o'sdimi?» va u reyestrni ko'rmasdan javob bera olmaydi.
=============================================================================

OLTITA INVARIANT VA HAR BIRI QAYSI DA'VONI QULFLAYDI:

  1. RLS `ENABLE` + `FORCE` + tenant policy — T-08-04 ning uch qatlami.
  2. `sbozor_app` ga TO'LIQ DML grant'i — usiz policy ma'nosiz
     (`permission denied`) va import birinchi so'rovdayoq yiqilardi.
  3. ⛔ KOMPOZIT FK `(market_id, stall_id)` — begona bozorning rastasiga
     havola STRUKTURAVIY imkonsiz (T-08-04).
  4. ⛔ IKKALA `UNIQUE` — takroriy import idempotent (T-08-05) va kompozit
     FK nishoni mavjud.
  5. `amount_soum` — `bigint`; kasrli tip yaxlitlanish driftini olib
     kelardi va u HECH QANDAY xato bermasdan yig'iladi.
  6. ⛔⛔ `ledger_entries` `FINANCIAL_TABLES` da YO'Q — TO'PLAM TENGLIGI
     bilan. Bu faylning eng muhim darvozasi (sabab pastda).
"""

from __future__ import annotations

import pytest
from psycopg import Connection
from psycopg.rows import TupleRow

pytestmark = pytest.mark.tenancy

LEDGER_TABLE = "ledger_entries"

RLS_FLAGS = """
SELECT c.relrowsecurity, c.relforcerowsecurity
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public' AND c.relname = %s
"""

POLICY_NAMES = """
SELECT policyname
FROM pg_policies
WHERE schemaname = 'public' AND tablename = %s
ORDER BY policyname
"""

CONSTRAINT_DEFS = """
SELECT con.conname, pg_get_constraintdef(con.oid)
FROM pg_constraint con
JOIN pg_class c ON c.oid = con.conrelid
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public'
  AND c.relname = %s
  AND con.contype = ANY(%s)
"""
"""Jadvalning konstraytlari — TA'RIFI bilan.

`pg_constraint` ishlatiladi (`information_schema` emas): oxirgisi o'z
ko'rinishlarini joriy rolning grant'lari bo'yicha filtrlaydi, ya'ni huquqi
tor rol ostida jimgina KAM konstrayt qaytarardi va darvoza sababsiz yashil
bo'lib qolardi (`test_occupancy_domain_meta.py` da o'rnatilgan qoida).
"""

TABLE_COLUMNS = """
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = %s
"""

APP_GRANTS = """
SELECT has_table_privilege('sbozor_app', 'ledger_entries', 'SELECT'),
       has_table_privilege('sbozor_app', 'ledger_entries', 'INSERT'),
       has_table_privilege('sbozor_app', 'ledger_entries', 'UPDATE'),
       has_table_privilege('sbozor_app', 'ledger_entries', 'DELETE')
"""

TENANT_POLICY_NAME = "tenant_isolation"
"""`migrations/entities/policies.py::TENANT_POLICY_SIGNATURE` ning qiymati.

⚠ REYESTRDAN IMPORT QILINMAYDI va bu ATAYIN: `migrations.entities` dan
olingan nom reyestrning O'ZI xato bo'lganda test bilan BIRGA xato
bo'lardi — ya'ni darvoza o'z manbasini tekshirardi.
"""

EXPECTED_FINANCIAL_TABLES: frozenset[str] = frozenset(
    {
        "daily_charges",
        "charge_adjustments",
        "payments",
        "tariffs",
        # 0027 — majburiy xizmat haqi (tarozi). Unda haqiqiy pul ustuni
        # bor, ya'ni reyestrga KIRADI; `CHECK (amount_soum > 0)` talabidan
        # esa `NON_POSITIVE_MONEY_TABLES` orqali istisno qilingan.
        "market_service_fees",
    }
)
"""`schema_contract.FINANCIAL_TABLES` ning TO'LIQ holati (0027 dan keyin).

⛔ RO'YXAT LITERAL YOZILADI, REYESTRDAN IMPORT QILINMAYDI — aks holda
tenglik darvozasi O'ZINI tekshirardi va HAR DOIM yashil bo'lardi.
"""

DAY_STALL_UNIQUE = "uq_ledger_entries_market_day_stall"
"""⛔ NOM LITERAL YOZILADI, MODELDAN IMPORT QILINMAYDI.

Yuqoridagi `TENANT_POLICY_NAME` bilan aynan bir xil sabab: model
konstantasidan olingan nom modelning O'ZI xato bo'lganda test bilan BIRGA
xato bo'lardi va darvoza «migratsiya modelga mos» degan BO'SH da'voni
tekshirardi. Bu yerda savol boshqa: «BAZADA aynan shu nomli cheklov
bormi?»
"""


def _columns(conn: Connection[TupleRow], table: str) -> dict[str, str]:
    rows = conn.execute(TABLE_COLUMNS, (table,)).fetchall()
    columns = {str(row[0]): str(row[1]) for row in rows}
    assert columns, (
        f"`{table}` uchun `information_schema.columns` 0 qator qaytardi. "
        "Jadval yo'q, yoki joriy rolda unga birorta huquq yo'q — ikkala "
        "holatda ham quyidagi da'vo BO'SH ROST bo'lib qolardi."
    )
    return columns


def _constraints(conn: Connection[TupleRow], table: str, contypes: str) -> dict[str, str]:
    rows = conn.execute(CONSTRAINT_DEFS, (table, list(contypes))).fetchall()
    return {str(row[0]): str(row[1]) for row in rows}


def test_ledger_has_rls_enabled_forced_and_a_tenant_policy(
    sync_app_conn: Connection[TupleRow], migrated: None
) -> None:
    """RLS `ENABLE` + `FORCE` + tenant policy (T-08-04).

    =========================================================================
    UCHALASI HAM KERAK VA UCHALASI HAM ALOHIDA BUZILISHI MUMKIN:

      * `ENABLE` yo'q -> policy TA'SIRSIZ, jadval hamma uchun OCHIQ.
        `alembic-utils` `ENABLE`/`FORCE` ni BILMAYDI, ya'ni `PGPolicy`
        yaratilgan bo'lsa ham jadval qo'riqsiz qolishi mumkin (Pitfall 10);
      * `FORCE` yo'q -> jadval EGASI (migratsiya roli) policy'dan chetda
        qoladi va ega bilan ochilgan har qanday sessiya butun platformani
        ko'radi;
      * tenant policy yo'q -> RLS bor, lekin deny-all: xavfsiz, lekin
        import umuman ishlamaydi va nosozlik prodda birinchi faylda
        ko'rinardi.

    DAFTAR UCHUN BU AYNIQSA O'TKIR: qator NIZODA DALIL bo'ladi va begona
    bozorning daftar summasini o'qiy olish «qancha yig'ilgan?» degan
    tijorat sirini ochardi.
    =========================================================================
    """
    row = sync_app_conn.execute(RLS_FLAGS, (LEDGER_TABLE,)).fetchone()
    assert row is not None, f"`{LEDGER_TABLE}` `pg_class` da topilmadi — `0024` qo'llanmagan"

    enabled, forced = bool(row[0]), bool(row[1])
    problems: list[str] = []
    if not enabled:
        problems.append("`ENABLE ROW LEVEL SECURITY` yo'q")
    if not forced:
        problems.append("`FORCE ROW LEVEL SECURITY` yo'q")

    policies = {str(r[0]) for r in sync_app_conn.execute(POLICY_NAMES, (LEDGER_TABLE,)).fetchall()}
    if TENANT_POLICY_NAME not in policies:
        problems.append(f"`{TENANT_POLICY_NAME}` policy'si yo'q (mavjud: {sorted(policies)})")

    assert problems == [], f"`{LEDGER_TABLE}` da RLS to'liq emas:\n  " + "\n  ".join(problems)


def test_app_role_has_full_dml_on_the_ledger(
    sync_app_conn: Connection[TupleRow], migrated: None
) -> None:
    """`sbozor_app` ga TO'RTALA DML huquqi berilgan (`enable_tenant_rls`).

    ⛔ `UPDATE` HUQUQI ALOHIDA MA'NOGA EGA VA U ATAYIN TEKSHIRILADI: daftar
    takroriy importda `ON CONFLICT DO UPDATE` bilan ALMASHTIRILADI
    (`models/ledger.py` docstringining 2-bandi). `UPDATE` grant'i
    yo'qolsa import birinchi TUZATISHDA `permission denied` bilan
    yiqilardi — ya'ni birinchi yuklash ishlab, TUZATISH ishlamasdi va
    nosozlik faqat ikkinchi kuni ko'rinardi.
    """
    row = sync_app_conn.execute(APP_GRANTS).fetchone()
    assert row is not None, "grant so'rovi qator qaytarmadi"

    granted = dict(zip(("SELECT", "INSERT", "UPDATE", "DELETE"), map(bool, row), strict=True))
    missing = sorted(priv for priv, ok in granted.items() if not ok)

    assert missing == [], (
        f"`sbozor_app` ga `{LEDGER_TABLE}` ustida {missing} huquqi berilmagan. "
        "GRANT'siz tenant policy MA'NOSIZ bo'ladi: so'rov policy'ga yetib "
        "bormasdan `permission denied` bilan yiqiladi."
    )


def test_ledger_cannot_reference_a_stall_from_another_market(
    sync_app_conn: Connection[TupleRow], migrated: None
) -> None:
    """⛔ KOMPOZIT FK `(market_id, stall_id)` — T-08-04 ning SXEMA qatlami.

    =========================================================================
    YAGONA USTUNLI FK YETARLI EMAS VA BU FARQ MEXANIK.

    `FOREIGN KEY (stall_id) REFERENCES stalls (id)` shakli `market_id` ni
    UMUMAN tekshirmasdi, ya'ni A bozorining daftar qatori B bozorining
    rastasiga havola qila olardi. RLS buni to'xtatmaydi: policy QATORNI
    ko'rsatmaydi, lekin FK tekshiruvi tizim darajasida bajariladi va u
    policy'ga bo'ysunmaydi.

    Ya'ni bu kafolat RLS DAN MUSTAQIL va u kontekst o'rnatilmay qolgan
    (yoki noto'g'ri o'rnatilgan) holatda ham kuchda qoladi — «ikkinchi
    qatlam» degan ibora aynan shu ma'noda.

    ⚠ `ondelete` YO'Q (NO ACTION) ham TEKSHIRILADI: `CASCADE` bo'lsa
      rastani o'chirish uning daftar TARIXINI ham jimgina olib ketardi va
      nizoda dalil yo'qolardi.
    =========================================================================
    """
    foreign_keys = _constraints(sync_app_conn, LEDGER_TABLE, "f")

    assert "fk_ledger_entries_stall" in foreign_keys, (
        f"`fk_ledger_entries_stall` YO'Q. Mavjudlari: {sorted(foreign_keys)}. "
        "Usiz begona bozorning rastasiga havola SXEMA darajasida "
        "to'xtatilmasdi."
    )

    definition = foreign_keys["fk_ledger_entries_stall"]
    assert "market_id" in definition and "stall_id" in definition, (
        f"`fk_ledger_entries_stall` KOMPOZIT emas: {definition!r}. Yagona "
        "ustunli FK `market_id` ni tekshirmaydi va begona bozorning "
        "rastasiga havolani O'TKAZIB YUBORARDI."
    )
    assert "ON DELETE" not in definition.upper(), (
        f"`fk_ledger_entries_stall` da `ondelete` bor: {definition!r}. "
        "`CASCADE` rastani o'chirishda uning daftar TARIXINI ham olib "
        "ketardi — nizoda dalil yo'qolardi."
    )

    # NAZORAT: `markets` ga bo'lgan FK ham joyida. Usiz yuqoridagi da'vo
    # jadval `markets` dan butunlay uzilgan holatda ham rost bo'lardi.
    assert "fk_ledger_entries_market_id_markets" in foreign_keys, (
        "`markets` ga FK yo'q — jadval tenant chegarasidan uzilgan"
    )


def test_repeated_import_is_idempotent_by_a_database_constraint(
    sync_app_conn: Connection[TupleRow], migrated: None
) -> None:
    """⛔ IKKALA `UNIQUE` — T-08-05 (idempotentlik) va kompozit FK nishoni.

    =========================================================================
    IDEMPOTENTLIK — DB KAFOLATI, ILOVA INTIZOMI EMAS (D-21).

    `UNIQUE (market_id, business_date, stall_id)` bo'lmasa takroriy import
    o'sha kun × o'sha rasta uchun IKKINCHI qator yozardi va uch tomonlama
    solishtiruv (08-16) bitta daftar yozuvini IKKI MARTA sanardi — ya'ni
    hisobot «daftarda ortiqcha pul bor» degan SOXTA nomuvofiqlik
    ko'rsatardi.

    Ilova qatlamidagi «avval tekshir, keyin yoz» YETARLI EMAS: ikki
    parallel import yugurishi ikkalasi ham «yo'q ekan» deb ko'rib, ikkita
    qator yozardi (`notification_outbox.dedupe_key` bilan AYNAN bir sinf).
    =========================================================================
    """
    uniques = _constraints(sync_app_conn, LEDGER_TABLE, "u")

    assert DAY_STALL_UNIQUE in uniques, (
        f"`{DAY_STALL_UNIQUE}` YO'Q. Mavjudlari: {sorted(uniques)}. Usiz "
        "takroriy import ikkinchi qator yozardi va solishtiruv bitta "
        "daftar yozuvini ikki marta sanardi."
    )

    definition = uniques[DAY_STALL_UNIQUE]
    for column in ("market_id", "business_date", "stall_id"):
        assert column in definition, (
            f"`{DAY_STALL_UNIQUE}` da `{column}` yo'q: {definition!r} — "
            "kalit uchala ustundan iborat bo'lishi SHART."
        )

    # ⛔ KOMPOZIT FK NISHONI: keyingi fazalar bu jadvalga
    #   `(market_id, id)` bilan tayanishi uchun UNIQUE MAJBURIY —
    #   `0020` ning `stall_slot_occupancy` holati (OP-11,
    #   `InvalidForeignKeyError`) aynan shu cheklov yo'qligida tug'ilgan.
    assert "uq_ledger_entries_market_id_id" in uniques, (
        f"`uq_ledger_entries_market_id_id` YO'Q. Mavjudlari: {sorted(uniques)}. "
        "Usiz keyingi faza bu jadvalga kompozit FK bilan tayana olmasdi "
        "(`InvalidForeignKeyError`)."
    )


def test_amount_is_bigint_and_has_no_positive_check(
    sync_app_conn: Connection[TupleRow], migrated: None
) -> None:
    """`amount_soum` — `bigint`, VA `CHECK (> 0)` ATAYIN YO'Q.

    =========================================================================
    IKKI DA'VO, IKKI XIL SABAB — VA IKKINCHISI SHU FAZANING O'ZAGI.

    (a) `bigint` so'm ↔ Python `int`. Kasrli tip yaxlitlanish driftini
        olib kelardi va u HECH QANDAY xato bermasdan yig'iladi — aynan
        mahsulot bartaraf etadigan nizoni tug'diradi.

    (b) ⛔ `CHECK (amount_soum > 0)` BO'LMASLIGI SHART. `0` QONUNIY
        qiymat: «bu rastadan bugun hech nima yig'ilmadi» degan daftar
        yozuvi AYNAN nomuvofiqlikning dalili va u SC#5 ning ENG MUHIM
        holati. Cheklov qo'yilsa importer o'sha qatorni jimgina tashlab
        ketardi va solishtiruv o'zi fosh qilishi kerak bo'lgan holatni
        UMUMAN ko'rmasdi.

    Aynan (b) tufayli jadval `FINANCIAL_TABLES` ga qo'shilmaydi — quyidagi
    test o'sha qarorni reyestr tomonidan qulflaydi.
    =========================================================================
    """
    columns = _columns(sync_app_conn, LEDGER_TABLE)

    assert columns.get("amount_soum") == "bigint", (
        f"`amount_soum` tipi `{columns.get('amount_soum')}` — kutilgani "
        "`bigint`. Kasrli tip yaxlitlanish driftini olib keladi va u "
        "HECH QANDAY xato bermasdan yig'iladi."
    )

    checks = _constraints(sync_app_conn, LEDGER_TABLE, "c")
    positive = {
        name: definition
        for name, definition in checks.items()
        if "amount_soum" in definition and ">" in definition
    }

    assert positive == {}, (
        f"`amount_soum` ustida musbatlik `CHECK` i topildi: {positive}. "
        "`0` QONUNIY qiymat — «bu rastadan bugun hech nima yig'ilmadi» "
        "degan yozuv SC#5 ning eng muhim holati va u solishtiruvdan "
        "CHIQARIB TASHLANMASLIGI kerak."
    )


def test_ledger_is_deliberately_not_a_financial_table() -> None:
    """⛔⛔ `ledger_entries` `FINANCIAL_TABLES` da YO'Q — TO'PLAM TENGLIGI bilan.

    =========================================================================
    BU FAYLNING ENG MUHIM DARVOZASI VA U «UNUTILGAN» EMAS, «QAROR».

    Jadvalda `amount_soum` NOMLI ustun BOR, ya'ni u `cashier_shifts`
    (`declared_soum`/`system_soum`) yoki `billing_anomalies` (pul ustuni
    umuman yo'q) bilan BIR SINFDA EMAS: u
    `test_financial_tables_have_guards` ning regeksini QANOATLANTIRARDI.
    Ya'ni oldingi fazalarning «soxta pul ustuni» tuzog'i bu yerda
    ISHLAMAYDI va reyestrga qo'shish TABIIY ko'rinardi.

    Qo'shilsa NIMA BUZILARDI:

      * `financial_guards()` `CHECK (amount_soum > 0)` ni majburlardi ->
        `0` summali daftar yozuvi IMKONSIZ bo'lardi (yuqoridagi test);
      * `business_date` `created_at` DAN hosila bo'lardi -> import
        kechikib ertasi kuni bajarilganda qator NOTO'G'RI kunga tushardi,
        holbuki daftarda u DOMEN sanasi (`daily_charges.service_date`
        bilan aynan bir xil ajratma, C-2).

    ⛔ SOLISHTIRUV TO'PLAM TENGLIGI BILAN, `not in` BILAN EMAS. `assert
    "ledger_entries" not in FINANCIAL_TABLES` shakli faqat SHU nomni
    qo'riqlardi: keyingi faza `ledger_imports` yoki `ledger_lines` ni
    qo'shsa darvoza JIMGINA yashil qolardi. Tenglik esa reyestrga HAR
    QANDAY qo'shimchani ONGLI qaror qiladi.
    =========================================================================
    """
    from sbozor_core.schema_contract import AUDITED_TABLES, FINANCIAL_TABLES

    assert FINANCIAL_TABLES == EXPECTED_FINANCIAL_TABLES, (
        f"`FINANCIAL_TABLES` o'zgargan: {sorted(FINANCIAL_TABLES)}. 8-faza bu "
        "reyestrga HECH NIMA qo'shmaydi — sabab reyestrning o'z "
        "docstringida (`financial_guards()` `CHECK (amount_soum > 0)` ni "
        "majburlaydi, daftar esa `0` ni ham yozadi)."
    )

    # ⛔ TESKARI YO'NALISH: jadval AUDIT reyestrida esa BO'LISHI SHART
    #   (C-10). Usiz yuqoridagi da'vo «jadval hech qaysi reyestrda yo'q»
    #   holatida ham rost bo'lardi — ya'ni audit qarzi JIMGINA ochiq
    #   qolardi va «kim daftar summasini almashtirdi?» savoli javobsiz
    #   bo'lardi.
    assert "ledger_entries" in AUDITED_TABLES, (
        "`ledger_entries` `AUDITED_TABLES` da YO'Q. Daftar qatori "
        "`ON CONFLICT DO UPDATE` bilan ALMASHTIRILADI, ya'ni eski qiymat "
        "faqat `audit_log.old_value` da qoladi — audit bu yerda «ikkinchi "
        "nusxa» emas, YAGONA iz (C-10)."
    )
