"""A1 ZONDI — parallel `get-or-create` oynasining O'LCHOV USKUNASI (G-12, D-21).

=============================================================================
ZONDNING YAGONA SAVOLI:

    `INSERT ... ON CONFLICT (market_id, idempotency_key) DO NOTHING
    RETURNING id` konfliktda HECH NIMA qaytaradi (Gotcha 5). Ya'ni
    get-or-create uchun IKKINCHI bayonot majburiy. Savol shu:

        READ COMMITTED ostida, PARALLEL sessiya yutgan qatorni
        yutqazgan sessiyaning O'SHA TRANZAKSIYASIDAGI alohida
        `SELECT` i KO'RADIMI (`postgres:18.4`)?

Javob `services/core-api/app/repositories/payment_repo.py` NING SHAKLINI
belgilaydi (D-21 / 06-09):

  * HA  -> `payment_repo` da ikki bayonotli get-or-create: `ON CONFLICT
           DO NOTHING ... RETURNING`, natija `None` bo'lsa AYNI
           tranzaksiyada `SELECT ... WHERE (market_id, idempotency_key)`.
           D-21 («takror so'rov o'sha to'lovni 200 bilan qaytaradi»)
           to'g'ridan-to'g'ri shu shakl bilan bajariladi.
  * YO'Q -> `IntegrityError` + `SAVEPOINT` yo'li majburiy
           (`nvr_repo.py:506-532` naqshi + `03-06` ning `begin_nested`
           darsi), chunki `None` javobini 500 ga aylantirish D-21 ni
           buzardi (Pitfall 3).

⚠ NEGA JADVAL EMAS, ZOND. `payments` hali mavjud emas (`0020` uni shu
  o'lchovdan KEYIN yaratadi) va aynan shu sabab o'lchovni migratsiyadan
  OLDIN qilishga majbur qiladi: natijani keyin bilib olish REPOZITORIYNI
  QAYTA YOZISH demakdir. Shabloni — `tests/fixtures/billable_probe.py`
  (u ham mavjud bo'lmagan jadvalning DDL yo'lini oldindan isbotlagan).

⛔ JADVAL `ALL_TENANT_TABLES` GA QO'SHILMAYDI VA RLS YOQILMAYDI.
  U zond, mahsulot jadvali EMAS. Reyestrga qo'shilishi
  `test_meta.py::test_every_table_is_tenant_scoped` ni HAM,
  `test_autogenerate_is_empty` ni HAM qizartirardi (birinchisi
  `pg_catalog` dan yuradi, ikkinchisi esa mavjud bo'lmagan jadvalga
  policy yaratib ko'radi — `migrations/entities/__init__.py:433-447` da
  o'lchangan `UndefinedTable`). Fixture jadvalni har testdan keyin
  `DROP TABLE` qiladi, ya'ni u `pg_catalog` da ham qolmaydi.

⚠ RLS YO'QLIGI O'LCHOVNI SOXTALASHTIRMAYDI: bu zond POYGA OYNASINI
  o'lchaydi, izolyatsiyani emas. RLS `USING` predikati snapshot
  semantikasiga ta'sir qilmaydi — u qaysi qatorlar KO'RINISHINI
  cheklaydi, qachon ko'rinishini emas.
=============================================================================

DDL `sbozor_owner` bilan bajariladi (`sbozor_app` `public` sxemada obyekt
yarata olmaydi — T-01-06), DML esa `sbozor_app` bilan: aynan ilova roli
ko'radigan xulq o'lchanadi. Shuning uchun `GRANT` MAJBURIY —
`ops/db/init/01-roles.sql` hech qanday standart huquq bermaydi va u
`migrations/helpers.py::grant_app_dml()` ning zonddagi qo'lda yozilgan
ekvivalenti.
"""

from __future__ import annotations

from dataclasses import dataclass

from psycopg import Connection
from psycopg.rows import TupleRow

__all__ = [
    "COUNT_BY_KEY",
    "CTE_UNION_ALL",
    "INSERT_ON_CONFLICT",
    "PROBE_TABLE",
    "SELECT_BACKEND_PID",
    "SELECT_BY_KEY",
    "SELECT_WAIT_EVENT_TYPE",
    "SHOW_ISOLATION",
    "IdempotencyProbe",
    "create_idempotency_probe",
    "drop_idempotency_probe",
]

# Jadval nomi SQL matnlarida LITERAL yozilgan (`billable_probe.py:59-61` da
# o'rnatilgan qoida): dinamiklikka ehtiyoj yo'q, literal shakl SQL'ni
# o'qishni osonlashtiradi va ruff `S608` yolg'on-musbatini bermaydi.
PROBE_TABLE = "probe_idempotent_writes"

# `payments` ning MINIMAL shakli — o'lchov uchun kerak bo'lgan aynan to'rt
# ustun. `kind`, `shift_id`, `service_date` va boshqalar bu savolga hech
# nima qo'shmaydi, `UNIQUE (market_id, idempotency_key)` esa D-21 ning
# BUTUN mexanizmi (`06-CONTEXT.md` D-21) va shu sabab bu yerda bor.
_CREATE_PROBE = """
CREATE TABLE probe_idempotent_writes (
    id              uuid PRIMARY KEY DEFAULT uuidv7(),
    market_id       uuid NOT NULL,
    idempotency_key text NOT NULL,
    amount_soum     bigint NOT NULL,
    CONSTRAINT uq_probe_idempotent_writes_market_key
        UNIQUE (market_id, idempotency_key)
)
"""

# `sbozor_app` ga DML — `grant_app_dml()` ning qo'lda yozilgan ekvivalenti.
# Usiz async sessiyalar `permission denied for table` bilan yiqilardi va
# sabab O'LCHOV NATIJASI kabi ko'rinardi.
_GRANT_PROBE = "GRANT SELECT, INSERT ON TABLE probe_idempotent_writes TO sbozor_app"

_DROP_PROBE = "DROP TABLE IF EXISTS probe_idempotent_writes"

_SERVER_VERSION = "SELECT version()"


# ===========================================================================
# DML — `sbozor_app` bilan, ASYNC sessiyalardan bajariladi
# ===========================================================================

INSERT_ON_CONFLICT = """
INSERT INTO probe_idempotent_writes (market_id, idempotency_key, amount_soum)
VALUES (:market_id, :idempotency_key, :amount_soum)
ON CONFLICT (market_id, idempotency_key) DO NOTHING
RETURNING id
"""
"""Get-or-create ning BIRINCHI bayonoti — konfliktda `None` beradi (Gotcha 5)."""

SELECT_BY_KEY = """
SELECT id FROM probe_idempotent_writes
 WHERE market_id = :market_id AND idempotency_key = :idempotency_key
"""
"""Get-or-create ning IKKINCHI bayonoti — zondning butun savoli shu yerda.

⛔ AYNI TRANZAKSIYADA bajariladi: `payment_repo` HTTP so'rovini bitta
tranzaksiya ichida yopadi, ya'ni «commit qilib, keyin o'qiymiz» shakli
mahsulotda YO'Q va u bu yerda ham o'lchanmaydi.
"""

COUNT_BY_KEY = """
SELECT count(*) FROM probe_idempotent_writes
 WHERE market_id = :market_id AND idempotency_key = :idempotency_key
"""

CTE_UNION_ALL = """
WITH ins AS (
    INSERT INTO probe_idempotent_writes (market_id, idempotency_key, amount_soum)
    VALUES (:market_id, :idempotency_key, :amount_soum)
    ON CONFLICT (market_id, idempotency_key) DO NOTHING
    RETURNING id
)
SELECT id FROM ins
UNION ALL
SELECT id FROM probe_idempotent_writes
 WHERE market_id = :market_id AND idempotency_key = :idempotency_key
"""
"""NAZORAT SHAKLI — «ikki bayonot ortiqcha emasmi?» savolining o'lchovi.

BIR BAYONOTLI get-or-create vasvasasi aniq: `INSERT ... RETURNING` ni CTE
ga solib, `UNION ALL` bilan mavjud qatorni ham qo'shib olish. Shakl
sintaktik jihatdan to'g'ri va KETMA-KET holatda ishlaydi — aynan shuning
uchun u xavfli. `SELECT` qismi BAYONOT snapshotini ko'radi, snapshot esa
bayonot BOSHLANGANDA olinadi; konflikt qatorining egasi shundan KEYIN
commit qilsa, `SELECT` uni TOPMAYDI va natija BO'SH bo'ladi.
"""

SHOW_ISOLATION = "SHOW transaction_isolation"
"""⛔ IZOLYATSIYA DARAJASI OCHIQ O'LCHANADI.

Bu zondning javobi READ COMMITTED ning har-bayonot-snapshot semantikasiga
tayanadi. Kelajakda `REPEATABLE READ` ga o'tilsa naqsh JIMGINA buzilardi:
yutqazgan sessiyaning `SELECT` i o'z tranzaksiyasi boshidagi snapshotni
ko'rar va qatorni TOPMASDI. Assert o'sha o'tishni ushlaydi.
"""

SELECT_BACKEND_PID = "SELECT pg_backend_pid()"
"""Sessiyaning backend PID'i — bloklanish holatini ANIQ kuzatish uchun."""

SELECT_WAIT_EVENT_TYPE = """
SELECT wait_event_type FROM pg_stat_activity WHERE pid = :pid
"""
"""Berilgan backend `Lock` kutayotganini o'lchaydi — `sleep()` NAVBATIDA EMAS.

Uchala sessiya ham `sbozor_app` roli bilan ulanadi, ya'ni `pg_stat_activity`
ustunlari ko'rinadi (Postgres boshqa ROLNING backendlari uchun ularni
niqoblaydi). Bu detal muhim: `sync_owner_conn` bilan poll qilinsa ustun
`NULL` bo'lib qolardi va poll hech qachon tugamasdi.
"""


@dataclass(frozen=True)
class IdempotencyProbe:
    """Zond jadvalining koordinatalari — o'lchov natijasi EMAS.

    `billable_probe.BillableProbe` dan farqi ATAYIN: u yerda DDL ning
    o'zi savol edi (`fk_supported`), bu yerda esa DDL oddiy va savol
    XULQDA — shuning uchun natija testlarda o'lchanadi va shu yerga
    yozilmaydi.

    `server_version` SUMMARY uchun: o'lchov AYNAN qaysi serverda
    olingani yozilmasa, natija keyinroq «qayerda o'lchangan?» degan
    javobsiz savolga aylanardi.
    """

    conn: Connection[TupleRow]
    server_version: str


def create_idempotency_probe(conn: Connection[TupleRow]) -> IdempotencyProbe:
    """Zond jadvalini quradi va `sbozor_app` ga DML huquqini beradi.

    Yiqilish KUTILMAGAN holat va u ATAYIN yuqoriga ko'tariladi:
    `uuidv7()` + `UNIQUE` allaqachon isbotlangan sinf, ya'ni u yerdagi
    xato zondning savoliga emas, muhitga tegishli (noto'g'ri PG
    versiyasi, yetishmayotgan huquq) va uni o'lchov natijasiga
    aylantirish javobni SOXTALASHTIRARDI.
    """
    drop_idempotency_probe(conn)

    row = conn.execute(_SERVER_VERSION).fetchone()
    assert row is not None, "`SELECT version()` javob bermadi"

    conn.execute(_CREATE_PROBE)
    conn.execute(_GRANT_PROBE)

    return IdempotencyProbe(conn=conn, server_version=str(row[0]))


def drop_idempotency_probe(conn: Connection[TupleRow]) -> None:
    """Zond jadvalini o'chiradi.

    Tozalash MAJBURIY: `DROP` qilinmasa keyingi yugurish `DuplicateTable`
    bilan yiqilardi va sabab o'lchov natijasi kabi ko'rinardi.
    """
    conn.execute(_DROP_PROBE)
