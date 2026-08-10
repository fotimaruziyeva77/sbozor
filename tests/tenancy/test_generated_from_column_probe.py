"""A2 O'LCHOVI — `GENERATED ALWAYS AS (<oddiy ustun>) STORED` (C-2 Varianti B).

=============================================================================
BU FAYL BIRORTA XULQNI HIMOYA QILMAYDI — U BITTA SAVOLGA JAVOB O'LCHAYDI.

`daily_charges` da IKKI SANA bo'ladi va ular BOSHQA savolga javob beradi:

    service_date   — QAYSI KUN uchun patta (domen sanasi, D-24 ning kaliti)
    business_date  — qator QAYSI kunda YOZILGAN (audit fakti)

`test_meta.py::test_financial_tables_have_guards` (`:1327-1356`) esa
moliyaviy jadvaldan `business_date` ning `attgenerated = 's'` bo'lishini
TALAB qiladi. C-2 shu talab bilan domen sanasini birlashtirishning uch
variantini sanab chiqqan; ikkinchisi — bu zondning savoli:

    `business_date date GENERATED ALWAYS AS (service_date) STORED`
    PG 18 da RUXSAT ETILADIMI?

⚠ SAVOL O'LCHANMAGAN. Repodagi HAMMA generated ustun ifodasi
  `created_at` USTIDA quriladi (`migrations/helpers.py::BUSINESS_DATE_EXPR`,
  `models/snapshot.py::CAPTURE_BUSINESS_DATE_EXPR`) — ya'ni «oddiy ustundan
  hosila» shakli repoda BIRORTA joyda yo'q (`06-PATTERNS.md` §5.3).

⛔ VA BU ZONDNING NATIJASI `0020` NI O'ZGARTIRMAYDI — QARORNI TASDIQLAYDI.
  Natija qanday bo'lishidan qat'i nazar `0020` **Variant A** ni ishlatadi
  (sabab `GENERATED_FROM_COLUMN_SUPPORTED` markerining docstringida).
  Zond baribir kerak: usiz «yana bir variant bor edi, nega tanlanmadi?»
  degan savol keyingi fazada JAVOBSIZ qolardi va kimdir uni qayta
  o'ylab topardi. Bu — hujjatlashtirilgan RAD ETISH, o'lchov bilan.

⛔ IFODA BU FAYLDA LITERAL YOZILMAYDI. Nazorat o'lchovi ifodani
  `migrations.helpers` DAN IMPORT qiladi (`0008_temporal.py:201-206`
  naqshi). Ikkinchi nusxa `test_financial_tables_have_guards` bilan
  jimgina ajralib ketardi va zond o'zi tekshirayotgan qiymatni o'zi
  yozgan bo'lardi.
=============================================================================

DDL `sbozor_owner` bilan bajariladi (`sbozor_app` `public` sxemada obyekt
yarata olmaydi — T-01-06). RLS ATAYIN yoqilmaydi: bu zond USTUN TA'RIFINI
o'lchaydi, izolyatsiyani emas.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING, Final

import psycopg
import pytest
from psycopg import Connection
from psycopg.rows import TupleRow

from migrations.entities import (
    GENERATED_FROM_COLUMN_MEASURED_AT,
    GENERATED_FROM_COLUMN_SUPPORTED,
)
from migrations.helpers import BUSINESS_DATE_EXPR

if TYPE_CHECKING:
    from collections.abc import Iterator

pytestmark = pytest.mark.tenancy

PLAIN_COLUMN_TABLE: Final[str] = "probe_generated_from_column"
CREATED_AT_TABLE: Final[str] = "probe_generated_from_created_at"

VARIANT_A: Final[str] = (
    "TANLANGAN VARIANT (C-2 / A): `0020` da `service_date date NOT NULL` "
    "DOMEN ustuni bo'ladi, `business_date` esa `created_at` dan hosila "
    "(`0008_temporal.py:164-182` presedenti). Bu satrni `06-03` o'qiydi."
)

_SERVER_VERSION = "SELECT version()"

# ⛔ VARIANT B — ZONDNING SAVOLI. `business_date` domen ustunidan hosila.
_CREATE_FROM_PLAIN_COLUMN = """
CREATE TABLE probe_generated_from_column (
    id            uuid PRIMARY KEY DEFAULT uuidv7(),
    service_date  date NOT NULL,
    business_date date GENERATED ALWAYS AS (service_date) STORED
)
"""

# NAZORAT O'LCHOVI — ifoda `migrations.helpers` DAN, literal EMAS.
_CREATE_FROM_CREATED_AT = f"""
CREATE TABLE probe_generated_from_created_at (
    id            uuid PRIMARY KEY DEFAULT uuidv7(),
    created_at    timestamptz NOT NULL DEFAULT now(),
    business_date date GENERATED ALWAYS AS {BUSINESS_DATE_EXPR} STORED
)
"""

_DROP_SQL = (
    "DROP TABLE IF EXISTS probe_generated_from_column",
    "DROP TABLE IF EXISTS probe_generated_from_created_at",
)

_INSERT_SERVICE_DATE = "INSERT INTO probe_generated_from_column (service_date) VALUES (%s)"
_SELECT_DERIVED = "SELECT service_date, business_date FROM probe_generated_from_column"
_INSERT_CREATED_AT = "INSERT INTO probe_generated_from_created_at DEFAULT VALUES"
_SELECT_CONTROL_DERIVED = "SELECT business_date FROM probe_generated_from_created_at"

_ATTGENERATED = """
SELECT a.attgenerated
  FROM pg_attribute a
  JOIN pg_class c ON c.oid = a.attrelid
  JOIN pg_namespace n ON n.oid = c.relnamespace
 WHERE n.nspname = 'public' AND c.relname = %s AND a.attname = 'business_date'
"""

_TO_REGCLASS = "SELECT to_regclass(%s)"

SERVICE_DATE_SAMPLE: Final[date] = date(2026, 9, 1)


@dataclass(frozen=True)
class GeneratedColumnProbe:
    """O'lchov natijasi — `plain_column_supported` shu zondning MAHSULOTI.

    `failure` va `sqlstate` `plain_column_supported = False` bo'lganda
    rad etishning TO'LIQ manzarasini tashiydi: yalang'och `False` keyingi
    o'quvchiga «nega?» degan savol qoldirardi, SQLSTATE esa javob beradi
    (`0A000` — qo'llab-quvvatlanmaydigan imkoniyat; `42P17` — noto'g'ri
    obyekt ta'rifi; ular butunlay boshqa xulosalar).

    ⚠ `stall_repo.sqlstate_of()` BU YERDA ISHLATILMAYDI VA SABAB
      MEXANIK: u `getattr(exc.orig, "sqlstate", None)` qiladi, ya'ni
      SQLAlchemy `IntegrityError` O'RAMINI kutadi. Xom `psycopg.Error`
      da `.orig` YO'Q — yordamchi JIMGINA `None` qaytarardi va o'lchov
      «SQLSTATE yo'q» degan YOLG'ON javob berardi. Zond o'ramsiz
      ishlaydi, shuning uchun kod ham o'ramsiz o'qiydi.
    """

    conn: Connection[TupleRow]
    plain_column_supported: bool
    failure: str | None
    sqlstate: str | None
    server_version: str


def _drop_probes(conn: Connection[TupleRow]) -> None:
    """Ikkala zond jadvalini o'chiradi va YO'QLIGINI O'LCHAYDI.

    ⛔ TEKSHIRUV `DROP` NING YONIDA, ALOHIDA TESTDA EMAS — VA BU ATAYIN.
      Alohida test uchinchi bo'lib qo'shilardi va u FAQAT o'zidan oldin
      yugurgan testning tozalanishini ko'rardi; bu yerda esa shart HAR
      testdan keyin bajariladi.

    ⚠ NEGA UMUMAN O'LCHANADI: `test_meta.py::test_every_table_is_tenant_scoped`
      jadvallarni reyestrdan EMAS, `pg_catalog` DAN o'qiydi (T-02-28).
      Qolib ketgan zond «RLS'siz tenant jadvali» bo'lib butun tenancy
      to'plamini qizartirardi va sabab bu faylda emas, o'sha testda
      ko'rinardi.
    """
    for statement in _DROP_SQL:
        conn.execute(statement)

    for table in (PLAIN_COLUMN_TABLE, CREATED_AT_TABLE):
        row = conn.execute(_TO_REGCLASS, (table,)).fetchone()
        assert row is not None, "`to_regclass` javob bermadi"
        assert row[0] is None, (
            f"zond jadvali `{table}` bazada QOLDI ({row[0]!r}) — u keyingi "
            "yugurishda `DuplicateTable` beradi va sabab o'lchov natijasi "
            "kabi ko'rinardi."
        )


@pytest.fixture
def probe(
    sync_owner_conn: Connection[TupleRow],
    migrated: None,
) -> Iterator[GeneratedColumnProbe]:
    """Ikkala zond jadvali — har testdan keyin tozalanadi.

    ⚠ NAZORAT JADVALINING YIQILISHI ATAYIN YUQORIGA KO'TARILADI.
      `created_at` dan hosila generated ustun ALLAQACHON isbotlangan
      sinf (`0008_temporal.py:201-206` prodda ishlaydi), ya'ni u yerdagi
      xato zondning savoliga emas, muhitga tegishli. Uni
      `plain_column_supported = False` ga aylantirish o'lchovni
      SOXTALASHTIRARDI (`billable_probe.py:133-141` bilan bir xil qaror).

    ⚠ `sync_owner_conn` `autocommit=True` — bu MAJBURIY detal: rad etilgan
      DDL tranzaksiyani abort holatiga tushirardi va keyingi bayonot
      `InFailedSqlTransaction` bilan yiqilardi, ya'ni nazorat o'lchovi
      birinchi o'lchovning natijasiga BOG'LANIB qolardi.
    """
    _drop_probes(sync_owner_conn)

    row = sync_owner_conn.execute(_SERVER_VERSION).fetchone()
    assert row is not None, "`SELECT version()` javob bermadi"
    server_version = str(row[0])

    sync_owner_conn.execute(_CREATE_FROM_CREATED_AT)

    supported = True
    failure: str | None = None
    sqlstate: str | None = None
    try:
        sync_owner_conn.execute(_CREATE_FROM_PLAIN_COLUMN)
    except psycopg.Error as error:
        supported = False
        failure = f"{type(error).__name__}: {error}".strip()
        sqlstate = error.sqlstate

    created = GeneratedColumnProbe(
        conn=sync_owner_conn,
        plain_column_supported=supported,
        failure=failure,
        sqlstate=sqlstate,
        server_version=server_version,
    )
    try:
        yield created
    finally:
        _drop_probes(sync_owner_conn)


# ===========================================================================
# 1-O'LCHOV — A2 ning yagona savoli
# ===========================================================================


def test_generated_from_plain_column_is_accepted_or_rejected(
    probe: GeneratedColumnProbe,
) -> None:
    """⚠ BU O'LCHOV — C-2 Varianti B ning imkoniyati (A2).

    Test IKKI TOMONGA HAM to'g'ri: DDL o'tsa qiymatning KO'CHIRILISHI va
    `attgenerated = 's'` tekshiriladi; DDL yiqilsa istisno sinfi va
    SQLSTATE yoziladi va test YASHIL qoladi — u DA'VO emas, O'LCHOV.

    Natija `GENERATED_FROM_COLUMN_SUPPORTED` markeri bilan solishtiriladi:
    marker o'lchovdan AJRALIB KETA OLMAYDI.
    """
    assert probe.plain_column_supported is GENERATED_FROM_COLUMN_SUPPORTED, (
        f"marker (`GENERATED_FROM_COLUMN_SUPPORTED = "
        f"{GENERATED_FROM_COLUMN_SUPPORTED}`) O'LCHOV natijasidan "
        f"({probe.plain_column_supported}) ajralib ketdi.\n"
        f"O'lchov sanasi markerda: {GENERATED_FROM_COLUMN_MEASURED_AT}\n"
        f"PostgreSQL: {probe.server_version}\n"
        f"DDL xatosi: {probe.failure}\n"
        f"SQLSTATE: {probe.sqlstate}\n\n" + VARIANT_A
    )

    if not probe.plain_column_supported:
        assert probe.sqlstate is not None, (
            "DDL rad etildi, lekin SQLSTATE o'qilmadi — rad etishning "
            f"SABABI o'lchanmay qoldi: {probe.failure}"
        )
        return

    # --- DDL o'tdi: qiymat HAQIQATAN ko'chiriladimi? ---
    probe.conn.execute(_INSERT_SERVICE_DATE, (SERVICE_DATE_SAMPLE,))
    row = probe.conn.execute(_SELECT_DERIVED).fetchone()
    assert row is not None, "zond qatori yozilmadi"
    assert row[0] == SERVICE_DATE_SAMPLE, f"`service_date` o'zgardi: {row[0]!r}"
    assert row[1] == SERVICE_DATE_SAMPLE, (
        f"`business_date` `service_date` dan KO'CHIRILMADI: {row[1]!r} != "
        f"{SERVICE_DATE_SAMPLE!r}. DDL o'tgani yolg'iz yetarli emas — "
        "ifoda haqiqatan hisoblanishi kerak."
    )

    generated = probe.conn.execute(_ATTGENERATED, (PLAIN_COLUMN_TABLE,)).fetchone()
    assert generated is not None, f"`{PLAIN_COLUMN_TABLE}.business_date` topilmadi"
    assert generated[0] == "s", (
        f"`business_date` GENERATED STORED emas (`attgenerated` = "
        f"{generated[0]!r}). `test_financial_tables_have_guards` "
        "(`test_meta.py:1327-1356`) aynan `'s'` ni talab qiladi, ya'ni "
        "VIRTUAL generated ustun bu talabni bajarmasdi."
    )


# ===========================================================================
# 2-O'LCHOV — NAZORAT (usiz birinchi o'lchov MA'NOSIZ)
# ===========================================================================


def test_generated_from_created_at_is_accepted(probe: GeneratedColumnProbe) -> None:
    """NAZORAT HOLATI: `created_at` dan hosila generated ustun ISHLAYDI.

    Bu ALLAQACHON ISBOTLANGAN sinf (`0008_temporal.py:201-206` prodda
    ishlaydi), lekin u SHU YERDA, SHU ULANISHDA ham tasdiqlanadi. Sababi
    mexanik: nazorat yugurishi bo'lmasa birinchi o'lchovning `False`
    natijasi «umuman generated ustun ishlamaydi» degan NOTO'G'RI xulosaga
    olib kelardi (masalan `sbozor_owner` da huquq yo'qligi ham aynan
    shunday ko'rinardi).

    ⛔ Ifoda `migrations.helpers.BUSINESS_DATE_EXPR` DAN import qilingan —
       bu yerda literal yozilmaydi (`0008_temporal.py:201-206` naqshi).
    """
    probe.conn.execute(_INSERT_CREATED_AT)
    row = probe.conn.execute(_SELECT_CONTROL_DERIVED).fetchone()
    assert row is not None, "nazorat qatori yozilmadi"
    assert isinstance(row[0], date), (
        f"nazorat ustuni sana bermadi: {row[0]!r} — ifoda hisoblanmagan"
    )

    generated = probe.conn.execute(_ATTGENERATED, (CREATED_AT_TABLE,)).fetchone()
    assert generated is not None, f"`{CREATED_AT_TABLE}.business_date` topilmadi"
    assert generated[0] == "s", (
        f"nazorat ustuni GENERATED STORED emas (`attgenerated` = "
        f"{generated[0]!r}) — bu KUTILMAGAN natija: prod migratsiyasi "
        "aynan shu ifodani ishlatadi."
    )
