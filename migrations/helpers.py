"""RLS DDL yordamchilari — `alembic-utils` QOPLAMAYDIGAN qism.

=============================================================================
NEGA BU FAYL BOR (RESEARCH Pattern 11 / Pitfall 10 — empirik tasdiqlangan):

`alembic-utils` 0.8.8 `CREATE POLICY` / `PGFunction` / `PGTrigger` /
`PGGrantTable` ni biladi, LEKIN quyidagilarni umuman bilmaydi:

  * `ALTER TABLE ... ENABLE ROW LEVEL SECURITY`
  * `ALTER TABLE ... FORCE  ROW LEVEL SECURITY`
  * `REVOKE ...`

Natija jimgina buziladi: policy yaratiladi va autogenerate'da ko'rinadi,
RLS esa yoqilmay qoladi — ya'ni policy HECH QANDAY ta'sir ko'rsatmaydi va
jadval hamma uchun ochiq bo'ladi. Shuning uchun bu uch DDL xom
`op.execute()` bilan yoziladi va `tests/tenancy/test_meta.py`
`relrowsecurity` VA `relforcerowsecurity` ikkalasini ham tekshiradi.
=============================================================================

Yangi tenant jadvali qo'shganda TARTIB muhim:

    op.create_table("stalls", ...)
    enable_tenant_rls("stalls")                     # ENABLE + FORCE + GRANT
    op.create_entity(tenant_policy("stalls"))       # policy
    op.create_entity(owner_bootstrap_policy("stalls"))
"""

from __future__ import annotations

import re
from typing import Any

import sqlalchemy as sa
from alembic import op

__all__ = [
    "APP_ROLE",
    "BUSINESS_DATE_EXPR",
    "DEFAULT_DML",
    "MARKET_TZ_LITERAL",
    "OWNER_ROLE",
    "attach_audit_trigger",
    "audit_trigger_name",
    "create_entity",
    "detach_audit_trigger",
    "disable_force_for_backfill",
    "drop_entity",
    "enable_rls",
    "enable_tenant_rls",
    "financial_guard_statements",
    "financial_guards",
    "grant_app_dml",
    "require_extension",
    "restore_force",
    "revoke_app_all",
]

APP_ROLE = "sbozor_app"
"""Ilova DML roli — NOSUPERUSER NOBYPASSRLS (`ops/db/init/01-roles.sql`)."""

OWNER_ROLE = "sbozor_owner"
"""DDL/migratsiya egasi — jadvallar shu rol nomidan yaratiladi."""

DEFAULT_DML = "SELECT, INSERT, UPDATE, DELETE"

_IDENT_RE = re.compile(r"^[a-z_][a-z0-9_]*$")
_DML_RE = re.compile(
    r"^(SELECT|INSERT|UPDATE|DELETE|REFERENCES|TRIGGER)"
    r"(,\s*(SELECT|INSERT|UPDATE|DELETE|REFERENCES|TRIGGER))*$"
)


def _ident(name: str) -> str:
    """Identifikatorni tekshiradi.

    Bu yordamchilar DDL'ni satr birlashtirish bilan quradi (Postgres `ALTER
    TABLE` / `GRANT` bind parametr qabul qilmaydi), shuning uchun kirish
    QAT'IY cheklanadi: faqat kichik harfli `snake_case`. Argumentlar
    migratsiya kodidan keladi, lekin bu darvoza sinf sifatida butun
    injection yuzasini yopadi.
    """
    if not _IDENT_RE.match(name):
        raise ValueError(
            f"{name!r} yaroqli identifikator emas — faqat kichik harf, raqam "
            "va pastki chiziq ruxsat etiladi (snake_case)"
        )
    return name


def _dml(ops: str) -> str:
    """`GRANT` uchun huquqlar ro'yxatini tekshiradi."""
    if not _DML_RE.match(ops.strip()):
        raise ValueError(f"{ops!r} yaroqli DML huquqlari ro'yxati emas")
    return ops.strip()


# ===========================================================================
# KENGAYTMA DARVOZASI (2-faza, Pitfall 1)
# ===========================================================================

_REQUIRE_EXTENSION = sa.text("SELECT 1 FROM pg_extension WHERE extname = :name")


def require_extension(name: str) -> None:
    """Kengaytma bazada MAVJUDLIGINI talab qiladi; yo'q bo'lsa `RuntimeError`.

    BU TEKSHIRUV MIGRATSIYANING BIRINCHI SATRI BO'LISHI KERAK. Sabab: kerakli
    kengaytmasiz `op.create_table(...)` o'rtada yiqiladi ("data type uuid has
    no default operator class for access method gist") va xabar aslida NIMA
    yetishmayotganini aytmaydi — dasturchi konstraytni "noto'g'ri yozilgan"
    deb o'ylab uni olib tashlaydi. Darvoza oldinda tursa, xato matni yagona
    to'g'ri harakatni ko'rsatadi.

    NEGA MIGRATSIYA KENGAYTMANI O'ZI YARATMAYDI (empirik, `postgres:18.4`):
    `sbozor_owner` — `NOCREATEDB` va bazaning egasi emas, ya'ni
    `CREATE EXTENSION` unga `permission denied to create extension` beradi.
    Kengaytma `ops/db/init/00-extensions.sql` da, superuser bilan yaratiladi
    (sabab va rad etilgan muqobil o'sha faylda batafsil).

    `name` ATAYIN `_ident()` darvozasidan O'TKAZILMAYDI: u DDL satriga
    qo'shilmaydi, bind parametr sifatida uzatiladi — ya'ni bu yerda
    injection yuzasi umuman yo'q va `_ident()` faqat soxta xotirjamlik
    bergan bo'lardi.
    """
    if op.get_bind().execute(_REQUIRE_EXTENSION, {"name": name}).first() is None:
        raise RuntimeError(
            f"`{name}` kengaytmasi bazada yo'q. Migratsiya roli (`{OWNER_ROLE}`) uni "
            "O'ZI o'rnata olmaydi — `permission denied to create extension`. "
            "`ops/db/init/00-extensions.sql` ni SUPERUSER bilan bajaring "
            "(prod'da bu fayl `docker-entrypoint-initdb.d` orqali avtomatik "
            "ishlaydi; mavjud bazada esa qo'lda: "
            f'psql -U postgres -d <db> -c "CREATE EXTENSION IF NOT EXISTS {name};").'
        )


def create_entity(entity: Any) -> None:
    """`op.create_entity()` ning tipli o'ram'i.

    `alembic-utils` o'z operatsiyalarini import paytida `Operations` ga
    DINAMIK ro'yxatdan o'tkazadi, shuning uchun mypy ularni ko'rmaydi
    (`Module has no attribute "create_entity"`). Ignore'ni har bir
    migratsiyada takrorlash o'rniga u shu yerda BIR MARTA, sababi bilan
    yoziladi — va migratsiyalar `attr-defined` tekshiruvini yo'qotmaydi.
    """
    op.create_entity(entity)  # type: ignore[attr-defined]


def drop_entity(entity: Any) -> None:
    """`op.drop_entity()` ning tipli o'ram'i (`create_entity` jufti)."""
    op.drop_entity(entity)  # type: ignore[attr-defined]


def enable_rls(table: str) -> None:
    """`ENABLE` + `FORCE ROW LEVEL SECURITY` (GRANT'siz).

    `markets` kabi maxsus holatlar uchun: u tenant chegarasining O'ZI,
    shuning uchun policy'si boshqacha va app-rolga faqat `SELECT` beriladi.
    """
    tbl = _ident(table)
    op.execute(f"ALTER TABLE {tbl} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {tbl} FORCE  ROW LEVEL SECURITY")


def enable_tenant_rls(table: str, role: str = APP_ROLE) -> None:
    """Standart tenant jadvali: `ENABLE` + `FORCE` + to'liq DML GRANT.

    GRANT'siz policy ma'nosiz bo'ladi (huquq yo'q -> `permission denied`),
    ENABLE/FORCE'siz esa policy ma'nosiz bo'ladi (hamma narsa ochiq).
    Uchtasi birga yuradi, shuning uchun bitta chaqiruvda.
    """
    enable_rls(table)
    grant_app_dml(table, role=role)


def grant_app_dml(table: str, ops: str = DEFAULT_DML, role: str = APP_ROLE) -> None:
    """Ilova roliga jadval ustida huquq beradi."""
    op.execute(f"GRANT {_dml(ops)} ON TABLE {_ident(table)} TO {_ident(role)}")


def revoke_app_all(table: str, role: str = APP_ROLE) -> None:
    """Ilova rolidan jadval ustidagi BARCHA huquqni olib tashlaydi.

    `users` uchun ishlatiladigan naqsh (Pattern 2): global identifikatsiya
    jadvaliga ORM orqali oddiy `select()` bilan borish IMKONSIZ bo'lishi
    kerak — o'qish faqat tor `SECURITY DEFINER` funksiyalari orqali o'tadi.
    """
    op.execute(f"REVOKE ALL ON TABLE {_ident(table)} FROM {_ident(role)}")


def disable_force_for_backfill(table: str) -> None:
    """Backfill oldidan `NO FORCE` (RESEARCH Pitfall 4 — empirik).

    `sbozor_owner` (superuser EMAS) FORCE ostida ham policy'ga bo'ysunadi,
    ya'ni migratsiyadagi `UPDATE ... SET ...` **jimgina `UPDATE 0`** qaytaradi
    va migratsiya "muvaffaqiyatli" tugaydi. `row_security` sozlamasini
    o'chirish YO'L BERMAYDI — Postgres `query would be affected by
    row-level security policy` xatosini beradi.

    Yagona to'g'ri ketma-ketlik::

        disable_force_for_backfill("stalls")
        result = op.get_bind().execute(sa.text("UPDATE stalls SET ..."))
        assert result.rowcount == kutilgan_son     # jim 0 ni ushlaydi
        restore_force("stalls")

    1-fazada backfill yo'q; yordamchi naqshni hujjatlashtirish uchun bor.
    """
    op.execute(f"ALTER TABLE {_ident(table)} NO FORCE ROW LEVEL SECURITY")


def restore_force(table: str) -> None:
    """Backfill tugagach FORCE'ni qaytaradi (`disable_force_for_backfill` jufti)."""
    op.execute(f"ALTER TABLE {_ident(table)} FORCE  ROW LEVEL SECURITY")


# ===========================================================================
# AUDIT TRIGGERI (D-10)
# ===========================================================================


def audit_trigger_name(table: str) -> str:
    """Jadval uchun audit trigger nomi — testlar ham shu yerdan oladi.

    Nom `sbozor_core.schema_contract.AUDITED_TABLES` reyestri bilan birga
    `tests/tenancy/test_meta.py::test_audited_tables_have_trigger` darvozasini
    hosil qiladi: reyestrda bor, lekin triggeri yo'q jadval CI'da qizaradi.
    """
    return f"trg_audit_{_ident(table)}"


def attach_audit_trigger(table: str) -> None:
    """Jadvalga `fn_audit_row()` triggerini ulaydi (`AFTER ... FOR EACH ROW`).

    `AFTER` — qator allaqachon yozilgan payt: audit "urinish" emas, SODIR
    BO'LGAN o'zgarishni qayd etadi (rad etilgan INSERT audit qatori
    qoldirmaydi).

    Yangi moliyaviy/huquqiy jadval tug'ilganda uch qadam BIRGA bajariladi::

        op.create_table("payments", ...)
        enable_tenant_rls("payments")
        attach_audit_trigger("payments")            # <- bu satr
        # + `AUDITED_TABLES` reyestriga "payments" qo'shiladi

    TALAB: jadvalning birlamchi kaliti `id uuid` bo'lishi shart —
    `fn_audit_row()` `row_id` ni `uuid` ga keltiradi.
    """
    tbl = _ident(table)
    op.execute(
        f"CREATE TRIGGER {audit_trigger_name(tbl)} "
        f"AFTER INSERT OR UPDATE OR DELETE ON {tbl} "
        "FOR EACH ROW EXECUTE FUNCTION fn_audit_row()"
    )


def detach_audit_trigger(table: str) -> None:
    """`attach_audit_trigger()` jufti — `downgrade()` uchun."""
    tbl = _ident(table)
    op.execute(f"DROP TRIGGER IF EXISTS {audit_trigger_name(tbl)} ON {tbl}")


# ===========================================================================
# MOLIYAVIY KONSTRAYT ASBOBLAR TO'PLAMI (ROADMAP mezoni #5, FOUND-05)
# ===========================================================================

MARKET_TZ_LITERAL = "Asia/Tashkent"
"""Biznes-kun chegarasi hisoblanadigan mintaqa.

`sbozor_core.timeutil.MARKET_TZ` bilan bir xil bo'lishi SHART —
`tests/integration/test_business_date.py` DB natijasini kod-qatlami natijasi
bilan uchala chegara holatida solishtiradi.
"""

BUSINESS_DATE_EXPR = f"((created_at AT TIME ZONE '{MARKET_TZ_LITERAL}')::date)"
"""`business_date` generated column ifodasi.

IKKI ARGUMENTLI shakl ATAYIN: `timezone(text, timestamptz)` PostgreSQL'da
`provolatile = 'i'` (IMMUTABLE), shuning uchun generated column'da ruxsat
etiladi. Bitta argumentli `timezone(timestamptz)` esa `TimeZone` GUC'iga
bog'liq va `'s'` (STABLE) — u `ERROR: generation expression is not immutable`
beradi.
"""


def financial_guard_statements(
    table: str,
    *,
    unique_cols: list[str],
    amount_col: str = "amount_soum",
    parent: tuple[str, str] | None = None,
) -> list[str]:
    """`financial_guards()` chiqaradigan DDL operatorlari — SOF funksiya.

    Ajratilishining sababi: `financial_guards()` `alembic.op` ga tayanadi va
    migratsiya konteksti tashqarisida chaqirib bo'lmaydi. Testlar shu ro'yxatni
    oladi va HAQIQIY jadvalda bajaradi, ya'ni ular yordamchining nusxasini
    emas, AYNAN o'zi chiqaradigan DDL'ni isbotlaydi. Nusxa yozilganda test
    yashil qolib, migratsiya boshqa narsa qilishi mumkin edi.
    """
    tbl = _ident(table)
    amount = _ident(amount_col)
    keys = [_ident(col) for col in unique_cols]
    if not keys:
        raise ValueError(f"{table}: `unique_cols` bo'sh — idempotentlik kaliti aniqlanmagan")

    statements = [
        f"ALTER TABLE {tbl} ADD COLUMN business_date date "
        f"GENERATED ALWAYS AS {BUSINESS_DATE_EXPR} STORED",
        f"ALTER TABLE {tbl} ADD CONSTRAINT ck_{tbl}_{amount}_positive CHECK ({amount} > 0)",
        f"ALTER TABLE {tbl} ADD CONSTRAINT uq_{tbl}_business_day "
        f"UNIQUE (market_id, {', '.join(keys)}, business_date)",
    ]

    if parent is not None:
        parent_table, child_col = _ident(parent[0]), _ident(parent[1])
        statements.append(
            f"ALTER TABLE {tbl} ADD CONSTRAINT fk_{tbl}_{parent_table} "
            f"FOREIGN KEY (market_id, {child_col}) "
            f"REFERENCES {parent_table} (market_id, id)"
        )

    return statements


def financial_guards(
    table: str,
    *,
    unique_cols: list[str],
    amount_col: str = "amount_soum",
    parent: tuple[str, str] | None = None,
) -> None:
    """Moliyaviy jadvalga to'rt konstraytni BIRGA o'rnatadi (mezon #5).

    Chiqadigan DDL::

        business_date date GENERATED ALWAYS AS
            ((created_at AT TIME ZONE 'Asia/Tashkent')::date) STORED
        CHECK  (amount_soum > 0)
        UNIQUE (market_id, <unique_cols...>, business_date)
        FOREIGN KEY (market_id, <child_col>) REFERENCES <parent> (market_id, id)

    Har biri boshqa nosozlikni yopadi va ular ALOHIDA unutilishi mumkin:

    * `business_date` — mahalliy yarim tundan keyingi besh soat naive UTC
      sanasida OLDINGI kunga tushadi. Ustun DB tomonda hisoblanadi, ya'ni
      kod-qatlamida ikkinchi haqiqat manbai paydo bo'lmaydi (Pitfall 6).
    * `CHECK (amount_soum > 0)` — pul `bigint` so'm; `float` TAQIQLANGAN
      (yaxlitlanish drifti aynan mahsulot bartaraf etadigan nizoni tug'diradi).
    * `UNIQUE(market_id, ..., business_date)` — kunni qayta yopish ikkinchi
      hisob yaratmaydi (`ON CONFLICT DO NOTHING` bilan birga, BILL-01).
    * composite FK — A bozori qatori B bozorining rastasiga havola qila
      olmaydi; bu RLS emas, SXEMA darajasidagi kafolat.

    BU YORDAMCHI 2- VA 6-FAZALARDA HAR BIR MOLIYAVIY JADVAL UCHUN MAJBURIY.
    `sbozor_core.schema_contract.FINANCIAL_TABLES` reyestri +
    `tests/tenancy/test_meta.py::test_financial_tables_have_guards` uni
    unutishni CI'da bloklaydi: jadval tug'ilgan kuni darvoza yopiladi.

    CHEKLOV — PER-MARKET TIMEZONE: mintaqa ifodada LITERAL yozilgan
    (`'Asia/Tashkent'`). Generated column BOSHQA JADVALGA MUROJAAT QILA
    OLMAYDI, ya'ni `markets.timezone` ustunini bu yerdan o'qib bo'lmaydi.
    Bozorga xos mintaqa kerak bo'lganda yagona yo'l — `timezone` ni qatorning
    O'ZIGA denormalizatsiya qilish va ifodani `(created_at AT TIME ZONE
    timezone)::date` ga o'zgartirish; bu jadvalni qayta yozadigan migratsiya
    bo'ladi. MVP'da barcha bozorlar `Asia/Tashkent` da.
    """
    for statement in financial_guard_statements(
        table,
        unique_cols=unique_cols,
        amount_col=amount_col,
        parent=parent,
    ):
        op.execute(statement)
