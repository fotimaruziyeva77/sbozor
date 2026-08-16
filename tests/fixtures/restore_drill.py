"""Tiklash mashqining MEXANIKASI — toza `postgres` konteyneri (08-08, D-16a).

=============================================================================
⛔ NEGA BU MODUL BOR, NEGA `tests/integration/conftest.py` DA EMAS.

`conftest.py` ning O'Z docstringi qoidani yozib qo'ygan: u fixture'lar
REYESTRI bo'lib qolishi kerak, mashina esa `tests/fixtures/` da yashaydi
(01-04 da o'rnatilgan naqsh — `fixtures/financial.py`, `fixtures/
two_markets.py`, ...).

⚠ VA BU YERDA QOIDA MEXANIK ZARURIYATGA AYLANADI, uslub emas: `pytest`
  `pythonpath` iga `tests` KATALOGI kiradi, ya'ni `import conftest`
  ILDIZDAGI `tests/conftest.py` ni topadi — `tests/integration/
  conftest.py` ni EMAS. Ya'ni `RestoreTarget` ni integratsiya
  conftest'ida qoldirib, uni test faylida tiplash MUMKIN EMAS edi:
  `from conftest import RestoreTarget` boshqa modulga borardi va
  `mypy` da yiqilardi (aynan shu o'lchandi).

⛔ SHU SABABDAN TIP SHU YERDA. Test fayli uni `fixtures.restore_drill`
   dan oladi, conftest esa faqat fixture sifatida E'LON qiladi.
=============================================================================

⚠⚠ BU MODUL `restic` NI UMUMAN BILMAYDI va bilishi ham kerak emas —
   halol chegara `test_restore_drill.py` ning modul docstringida
   LITERAL yozilgan.
"""

from __future__ import annotations

import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import quote_plus

import psycopg
from sqlalchemy.engine import make_url
from testcontainers.core.container import DockerContainer

if TYPE_CHECKING:
    from collections.abc import Iterator

__all__ = [
    "RESTORE_TARGET_IMAGE",
    "ROLES_SQL_PATH",
    "RestoreTarget",
    "libpq_dsn",
    "start_restore_target",
]

RESTORE_TARGET_IMAGE = "postgres:18.4-trixie"
"""⛔ MANBA BILAN BIR XIL MAJOR — VA U TAXMIN EMAS, O'LCHANADI.

`tests/conftest.py::POSTGRES_IMAGE` ni bu yerga import qilib bo'lmaydi:
`conftest` moduli `pytest` tomonidan alohida yuklanadi va uni oddiy
paket sifatida ham import qilish o'sha modulni IKKI MARTA yuklardi
(`tests/integration/conftest.py` ning modul docstringidagi ogohlantirish).

Ikkinchi nusxa esa JIMGINA eskirmaydi: `test_restore_drill.py` manba
serverning `server_version_num` ini tiklanganiki bilan SOLISHTIRADI.
`POSTGRES_IMAGE` bir kun 19 ga ko'chsa mashq ANIQ xabar bilan yiqiladi —
`pg_restore` ning «unsupported version» sirli xatosidan OLDIN.
"""

RESTORE_TARGET_DB = "sbozor_restored"
RESTORE_TARGET_SUPERUSER = "postgres"
RESTORE_TARGET_PASSWORD = "restore-drill-only-never-real"  # noqa: S105
"""Efemer konteynerning paroli — SIR EMAS, USKUNA (`conftest.APP_PASSWORD` qarori)."""

RESTORE_TARGET_READY_TIMEOUT = 120.0
"""Toza serverning ko'tarilishini kutish chegarasi (sekund).

⚠ LOG SATRIGA QARALMAYDI, ULANISH SINALADI. `postgres` entrypointi
  «database system is ready to accept connections» ni IKKI MARTA yozadi
  (initdb bosqichi + haqiqiy ishga tushish), ya'ni log kutuvchisi
  birinchisida qaytib, hali tayyor bo'lmagan serverga ulanardi.
"""

ROLES_SQL_PATH = Path(__file__).resolve().parents[2] / "ops" / "db" / "init" / "01-roles.sql"
"""Prod bilan AYNAN bir xil rol DDL'i — `tests/conftest.py::_bootstrap_roles` naqshi.

⛔ TOZA SERVERDA ROLLAR ZAXIRADAN OLDIN YARATILADI. Dump `CREATE POLICY
   ... TO sbozor_app` ni o'z ichiga oladi (RLS siyosatlari ROLGA ishora
   qiladi), ya'ni rolsiz serverda `pg_restore` o'sha operatorlarda
   yiqilardi va «tiklandi» da'vosi YARIM qurilgan sxema ustida turardi.
   Bu HAQIQIY tiklash tartibining o'zi: rollar -> dump.

⚠ `00-extensions.sql` ATAYIN YO'Q: `pg_dump` kengaytmani o'zi
  (`CREATE EXTENSION IF NOT EXISTS`) olib keladi va uni oldindan
  yaratish aynan «dump O'ZI yetarlimi?» degan savolni o'lchovdan
  chiqarib tashlardi.
"""


@dataclass(frozen=True)
class RestoreTarget:
    """Zaxira tiklanadigan TOZA `postgres` konteyneri."""

    dsn: str
    """Test JARAYONIDAN ulanish (`host.docker.internal` orqali)."""

    internal_dsn: str
    """Konteyner ICHIDAN ulanish — `pg_restore` shuni ishlatadi."""

    container: DockerContainer

    def run(self, *command: str) -> str:
        """Buyruqni KONTEYNER ICHIDA bajaradi va chiqish kodini TEKSHIRADI.

        ⛔ CHIQISH KODI YUTILMAYDI — bu `run-backup.sh` dagi «quvur yo'q»
           qarorining (08-05, Pitfall 5) shu yerdagi jufti: e'tiborsiz
           qoldirilgan kod yiqilgan `pg_dump` ni «muvaffaqiyat» qilib
           ko'rsatardi va mashq BO'SH dump ustida yashil bo'lardi.
        """
        result = self.container.exec(list(command))
        output = result.output.decode("utf-8", errors="replace")
        assert result.exit_code == 0, (
            f"`{command[0]}` toza serverda {result.exit_code} kodi bilan tugadi:\n{output}"
        )
        return output


def libpq_dsn(sqlalchemy_url: str) -> str:
    """SQLAlchemy URL'ini `pg_dump` tushunadigan libpq shakliga o'tkazadi.

    ⚠ Pitfall 8b ning aynan o'zi (`run-backup.sh` ning `BACKUP_DATABASE_URL`
      bandi): `postgresql+asyncpg://` ni `pg_dump` `invalid URI scheme`
      bilan RAD ETADI.
    """
    url = make_url(sqlalchemy_url)
    user = quote_plus(url.username or "")
    password = quote_plus(url.password or "")
    return f"postgresql://{user}:{password}@{url.host}:{url.port}/{url.database}"


@contextmanager
def start_restore_target() -> Iterator[RestoreTarget]:
    """TOZA `postgres` konteyneri: rollar bor, sxema YO'Q.

    ⚠⚠ KONTEYNER `finally` DA ALBATTA TO'XTAYDI (kontekst menejeri).
       Xost diski 08-08 paytida 93 % to'la edi va qolib ketgan konteyner
       yugurishlar bo'ylab to'planardi — T-08-33 ning aynan o'zi.
    """
    container = (
        DockerContainer(RESTORE_TARGET_IMAGE)
        .with_env("POSTGRES_PASSWORD", RESTORE_TARGET_PASSWORD)
        .with_env("POSTGRES_DB", RESTORE_TARGET_DB)
        .with_exposed_ports(5432)
        # ⚠ `pg_dump` MANBAGA konteyner ICHIDAN boradi, ya'ni unga ham
        #   `tests` xizmatidagi bilan AYNAN bir xil xost xaritasi kerak
        #   (`compose.yaml`: `host.docker.internal:host-gateway`).
        .with_kwargs(extra_hosts={"host.docker.internal": "host-gateway"})
    )
    with container:
        dsn = _wait_for_postgres(container)
        with psycopg.connect(dsn, autocommit=True) as conn:
            # Parametrsiz `execute` — `DO $$...$$` bloklari bitta oddiy
            # so'rov bo'lib ketadi (`tests/conftest.py::_bootstrap_roles`).
            conn.execute(ROLES_SQL_PATH.read_text(encoding="utf-8"))
        yield RestoreTarget(
            dsn=dsn,
            internal_dsn=(
                f"postgresql://{RESTORE_TARGET_SUPERUSER}:{quote_plus(RESTORE_TARGET_PASSWORD)}"
                f"@127.0.0.1:5432/{RESTORE_TARGET_DB}"
            ),
            container=container,
        )


def _wait_for_postgres(container: DockerContainer) -> str:
    """Ulanish MUVAFFAQIYATLI bo'lguncha kutadi va DSN qaytaradi."""
    host = container.get_container_host_ip()
    port = container.get_exposed_port(5432)
    dsn = (
        f"postgresql://{RESTORE_TARGET_SUPERUSER}:{quote_plus(RESTORE_TARGET_PASSWORD)}"
        f"@{host}:{port}/{RESTORE_TARGET_DB}"
    )

    deadline = time.monotonic() + RESTORE_TARGET_READY_TIMEOUT
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            with psycopg.connect(dsn, connect_timeout=3):
                return dsn
        except psycopg.Error as exc:
            last_error = exc
            time.sleep(1.0)
    raise AssertionError(
        f"toza `{RESTORE_TARGET_IMAGE}` {RESTORE_TARGET_READY_TIMEOUT:.0f} s ichida "
        f"ulanishga tayyor bo'lmadi: {last_error}"
    )
