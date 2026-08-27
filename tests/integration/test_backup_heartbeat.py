"""Zaxira yurak urishi -> `/internal/self-check` -> `backup_stale` (FOUND-07, D-15).

=============================================================================
⛔ TEST SQL NI QO'LDA YOZMAYDI — U `ops/backup/heartbeat.sql` FAYLINI O'QIYDI.

Bu qoida qulaylik emas, DARVOZANING O'ZI. Qo'lda yozilgan `INSERT ...
ON CONFLICT` mahsulot skriptidan bir kun JIMGINA ajralib ketardi va
o'shanda bu fayl «zaxira ishladi» degan YOLG'ONNI o'lchardi: test yashil
bo'lib turardi, mahsulot esa boshqa komponent nomi (yoki boshqa jadval,
yoki boshqa `ON CONFLICT` maqsadi) bilan yozardi va
`/internal/self-check` `backup` ni MANGU `never_seen` da ko'rsatardi.

Aynan shu nosozlik shakli `self_check.py` ning O'Z ogohlantirishida
nomma-nom yozilgan (`EXPECTED_COMPONENTS` ustidagi ⛔ blok) va u shu
faylning majburiy sabotaji bilan o'lchanadi.

⚠ YAGONA MOSLASHTIRISH — `:'day'` -> `%s::text`, VA U TOR HAM, E'LON
  QILINGAN HAM (sabab `DBAPI_DAY_BINDING` docstringida, o'lchangan xato
  bilan). `psql -v day=...` mijoz tomonida qochiradi, DB-API esa server
  tomonida bog'laydi; IKKALASI HAM bog'langan o'zgaruvchi, ya'ni T-08-22
  ning («SQL satr birlashtirish yo'q») ma'nosi saqlanadi. Almashtirish
  SONI tekshiriladi: mexanizm o'zgarsa test SHU YERDA yiqiladi, jimgina
  noto'g'ri SQL bajarmaydi.

⛔ SQL NING QOLGAN HAMMASI — jadval nomi, `'backup'` komponenti,
  `ON CONFLICT (component)` maqsadi va `detail` ning shakli — FAYLDAN
  VERBATIM keladi.
=============================================================================

=============================================================================
ZANJIRNING IKKI UCHI VA ULARNING IKKI XIL O'LCHOVI.

  yurak urishi -> `/internal/self-check`   -> `never_seen` dan CHIQISH
  yurak urishi -> `alert_sweep`            -> `backup_stale` (CRITICAL)

Ikkalasi ham kerak va ular BOSHQA-BOSHQA jarayonlarni ifodalaydi
(`self_check.py` ning 2-qoidasi): endpoint `core-api` da, supurgi
`worker` da. Faqat bittasini o'lchash ikkinchisining nomi ajralib
ketganini ko'rmasdi.
=============================================================================

⚠ VAQT SILJITILMAYDI — U ARGUMENT (`alert_sweep(..., now=...)`), aynan
  `test_alerting.py` dagi qaror. Yurak urishining YOSHI esa `last_seen_at`
  ni ORQAGA surish bilan quriladi: `HEARTBEAT_STALE_HOURS` (26) ning ikki
  tomoni (27 soat -> alert, 2 soat -> alert YO'Q) shu bilan o'lchanadi.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from app.jobs.alerting import (
    BACKUP_COMPONENT,
    HEARTBEAT_STALE_HOURS,
    NEVER_SUPPRESSED_ALERT_KEYS,
    alert_sweep,
)
from app.services.alerts import AlertSender
from pydantic import SecretStr
from sbozor_core.enums import AlertSeverity
from sbozor_core.timeutil import MARKET_TZ

if TYPE_CHECKING:
    from collections.abc import Iterator
    from datetime import date

    import httpx
    from fixtures.two_markets import TwoMarketSeed
    from psycopg import Connection
    from psycopg.rows import TupleRow
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

pytestmark = pytest.mark.usefixtures("migrated")

REPO_ROOT = Path(__file__).resolve().parents[2]
HEARTBEAT_SQL_PATH = REPO_ROOT / "ops" / "backup" / "heartbeat.sql"
"""MAHSULOT skripti — `run-backup.sh` ning ENG OXIRGI qadami shuni bajaradi."""

PSQL_DAY_VARIABLE = ":'day'"
"""`psql -v day=YYYY-MM-DD` bog'langan o'zgaruvchisining fayldagi shakli."""

DBAPI_DAY_BINDING = "%s::text"
"""`:'day'` ning DB-API jufti — ⛔ `::text` MAJBURIY VA U O'LCHANDI.

=============================================================================
`psql` ning `:'day'` i QOCHIRILGAN SATR LITERALINI qo'yadi (`'2026-08-16'`),
ya'ni Postgres uni `unknown` sifatida ko'rib `text` ga hal qiladi. DB-API
esa TIPSIZ parametr yuboradi va `jsonb_build_object(..., "any")` uning
tipini ANIQLAY OLMAYDI:

    psycopg.errors.IndeterminateDatatype: could not determine data type
    of parameter $1

`::text` — yangi xulq EMAS, `psql` ning qochirishi bergan tipni AYNAN
tiklash. Ikkala yo'lda ham qiymat BOG'LANGAN parametr bo'lib qoladi va
T-08-22 ning «SQL satr birlashtirish yo'q» qoidasi buzilmaydi.
=============================================================================
"""

SELF_CHECK_URL = "/internal/self-check"

_DROP_HEARTBEAT = "DELETE FROM system_heartbeats WHERE component = %s"
_READ_HEARTBEAT = "SELECT last_seen_at, detail FROM system_heartbeats WHERE component = %s"
_AGE_HEARTBEAT = (
    "UPDATE system_heartbeats SET last_seen_at = now() - make_interval(hours => %s) "
    "WHERE component = %s"
)
"""Yurak urishini ORQAGA suradi — ⚠ INTERVAL BAZANING SOATIDA.

`self_check.py::_threshold()` bilan aynan bir xil sabab: yozuvchi ham,
o'quvchi ham `now()` ga tayanadi, ya'ni konteyner soatining drifti
chegarani jimgina siljitmaydi.
"""

_OPEN_ALERTS = (
    "SELECT alert_key, severity FROM alert_events "
    "WHERE market_id = ANY(%s::uuid[]) AND resolved_at IS NULL"
)
_DROP_ALERTS = "DELETE FROM alert_events WHERE market_id = ANY(%s::uuid[])"


def _sql_body(sql_text: str) -> str:
    """To'liq qatorli `--` izohlarini OLIB TASHLAYDI.

    =====================================================================
    ⛔ BUSIZ BOG'LASH O'LCHOVI YOLG'ON BERARDI — VA BU O'LCHANDI, taxmin
       qilinmadi: `heartbeat.sql` da `:'day'` UCH marta uchraydi, ikkitasi
       T-08-22 ni tushuntiruvchi IZOHDA (fayl o'z mexanizmini o'zi
       hujjatlaydi) va faqat bittasi BAJARILADIGAN SQL da.

    Ya'ni «aynan bitta bog'langan o'zgaruvchi» da'vosi izoh matnini SQL
    bilan aralashtirib, hech qachon rost bo'lmasdi — yoki (izohlar
    o'zgarsa) tasodifan rost bo'lib, keyingi tahrirda jimgina buzilardi.

    ⚠ FAQAT TO'LIQ QATORLI izohlar olinadi. Qator ICHIDAGI `--` ni kesish
      satr literali ichidagi ikki tirega tegib, SQL ni buzardi;
      `heartbeat.sql` esa (va `ops/backup/` ning butun uslubi) izohni
      HAR DOIM alohida qatorga yozadi.
    =====================================================================
    """
    return "\n".join(line for line in sql_text.splitlines() if not line.lstrip().startswith("--"))


def _heartbeat_statement() -> str:
    """`heartbeat.sql` ni o'qiydi va `:'day'` ni DB-API placeholder'iga bog'laydi.

    ⛔ NAZORAT ASSERTI MAJBURIY. `count == 1` bo'lmasa almashtirish
       jimgina noto'g'ri SQL yasardi (yoki umuman ta'sir qilmasdi) va
       test o'z tasavvurini bajargan bo'lardi. Fayl mexanizmi o'zgarsa
       (masalan `:day` yoki `$1` ga o'tsa) nosozlik SHU YERDA, aniq
       xabar bilan chiqadi.
    """
    body = _sql_body(HEARTBEAT_SQL_PATH.read_text(encoding="utf-8"))
    found = body.count(PSQL_DAY_VARIABLE)
    assert found == 1, (
        f"`{HEARTBEAT_SQL_PATH.name}` ning BAJARILADIGAN qismida {PSQL_DAY_VARIABLE} "
        f"{found} marta uchradi (kutilgan: 1) — bog'lash mexanizmi o'zgargan, "
        "test uni jimgina noto'g'ri bajarmasligi kerak"
    )
    return body.replace(PSQL_DAY_VARIABLE, DBAPI_DAY_BINDING)


def _write_heartbeat(conn: Connection[TupleRow], day: date) -> None:
    """MAHSULOT SQL'ini bajaradi — `run-backup.sh` ning 5-qadami bilan bir xil."""
    conn.execute(_heartbeat_statement(), (day.isoformat(),))


def _market_day() -> date:
    """`run-backup.sh` dagi `TZ=Asia/Tashkent date +%F` ning aynan jufti."""
    return datetime.now(tz=MARKET_TZ).date()


@pytest.fixture(autouse=True)
def _production_sql_is_present() -> None:
    """QUYI CHEGARA — ALOHIDA TEST EMAS, HAR O'LCHOVDAN OLDINGI FIXTURE.

    =====================================================================
    ⛔ NEGA FIXTURE, NEGA BESHINCHI TEST EMAS (08-05 da o'rnatilgan naqsh).

    Alohida test bo'lganda u YOLG'IZ qizarib, qolgan to'rt da'vo BO'SH-ROST
    holida yashil bo'lib turardi: fayl yo'qolgan bo'lsa `_heartbeat_
    statement()` `FileNotFoundError` beradi va sabab «test buzuq» kabi
    ko'rinardi. `autouse` shaklida chegara TO'RTALA o'lchovning HAR
    BIRIDAN oldin bajariladi va nosozlik ANIQ xabar bilan chiqadi.
    =====================================================================
    """
    assert HEARTBEAT_SQL_PATH.is_file(), (
        f"mahsulot skripti topilmadi: {HEARTBEAT_SQL_PATH} — "
        "`ops/backup/heartbeat.sql` ko'chirilgan bo'lsa shu fayl ham yangilanishi SHART"
    )
    assert "system_heartbeats" in _heartbeat_statement(), (
        "`heartbeat.sql` `system_heartbeats` ga yozmayapti — zanjirning manbai o'zgargan"
    )


@pytest.fixture
def no_backup_heartbeat(sync_owner_conn: Connection[TupleRow]) -> Iterator[None]:
    """`system_heartbeats['backup']` YO'Q holatidan boshlaydi va shunday tugatadi.

    ⚠ IKKALA TOMONDA HAM tozalanadi: qator sessiya davomida yashaydi
      (`system_heartbeats` GLOBAL jadval, tenant tozalashiga tushmaydi),
      ya'ni tozalanmagan test keyingisining boshlang'ich holatini jimgina
      buzardi va sabab «flaky» bo'lib ko'rinardi.
    """
    sync_owner_conn.execute(_DROP_HEARTBEAT, (BACKUP_COMPONENT,))
    try:
        yield
    finally:
        sync_owner_conn.execute(_DROP_HEARTBEAT, (BACKUP_COMPONENT,))


@pytest.fixture
def quiet_alerts(
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
) -> Iterator[list[str]]:
    """Ikki bozorning `alert_events` i — o'lchovdan oldin ham, keyin ham TOZA."""
    market_ids = [str(market.id) for market in two_markets.markets]
    sync_owner_conn.execute(_DROP_ALERTS, (market_ids,))
    try:
        yield market_ids
    finally:
        sync_owner_conn.execute(_DROP_ALERTS, (market_ids,))


async def _sweep_open_alerts(
    sessionmaker: async_sessionmaker[AsyncSession],
    conn: Connection[TupleRow],
    market_ids: list[str],
) -> list[tuple[str, str]]:
    """Supurgini TARMOQSIZ yugurtiradi va OCHIQ alertlarni qaytaradi.

    ⚠ JO'NATUVCHI O'CHIQ (`enabled=False`), MOCK EMAS. Mahsulot obyekti
      saqlanadi (`test_alerting.py` ning qarori), lekin bu fayl Telegram
      KONTRAKTINI o'lchamaydi — u `alert_events` QATORINI o'lchaydi.
      `respx` qo'shish o'lchovga hech nima bermasdi va ikkinchi
      bog'liqlik kiritardi.
    """
    silent = AlertSender(token=SecretStr(""), chat_id="", enabled=False)
    try:
        await alert_sweep(sessionmaker, silent, now=datetime.now(tz=MARKET_TZ))
    finally:
        await silent.aclose()
    return [(row[0], row[1]) for row in conn.execute(_OPEN_ALERTS, (market_ids,)).fetchall()]


def _self_check_payload(response: httpx.Response) -> dict[str, Any]:
    """Javob tanasi — `200` da ham, `503` da ham MAVJUD (`self_check.py`)."""
    assert response.status_code in {200, 503}, (
        f"`{SELF_CHECK_URL}` kutilmagan holat kodi berdi: {response.status_code}"
    )
    payload: dict[str, Any] = response.json()
    return payload


# ===========================================================================
# (a) BOSHLANG'ICH HOLAT — QATOR UMUMAN YO'Q
# ===========================================================================


async def test_backup_is_never_seen_while_no_heartbeat_row_exists(
    api_client: httpx.AsyncClient,
    sync_owner_conn: Connection[TupleRow],
    no_backup_heartbeat: None,
) -> None:
    """Yurak urishi YOZILMAGANDA `backup` `never_seen` da turadi.

    =====================================================================
    ⛔ «QATOR YO'Q» — O'LCHANADIGAN HOLAT, TEXNIK TAFSILOT EMAS.

    `self_check.py` `stale` va `never_seen` ni ATAYIN ajratadi: birinchisi
    `ok` ni `false` qiladi, ikkinchisi esa YO'Q. Agar bu farq bo'lmasa
    endpoint zaxira qurilgunga qadar HAR KUNI `503` qaytarardi va tashqi
    kuzatuvchi doimiy qizil signalni ko'rib uni O'CHIRIB qo'yardi — ya'ni
    darvoza mavjud bo'lib turib, hech nimani kuzatmasdi.

    Shuning uchun bu yerda IKKI da'vo birga o'lchanadi: qator BAZADA yo'q
    VA endpoint uni `never_seen` da OCHIQ ko'rsatadi. Faqat ikkinchisini
    o'lchash qator boshqa nom bilan mavjud bo'lgan holatni ham «to'g'ri»
    deb ko'rsatardi.
    =====================================================================
    """
    stored = sync_owner_conn.execute(_READ_HEARTBEAT, (BACKUP_COMPONENT,)).fetchone()
    assert stored is None, (
        f"nazorat: `system_heartbeats['{BACKUP_COMPONENT}']` qatori mavjud — "
        "boshlang'ich holat qurilmadi va (a) hech nimani o'lchamasdi"
    )

    payload = _self_check_payload(await api_client.get(SELF_CHECK_URL))

    assert BACKUP_COMPONENT in payload["never_seen"], (
        f"`{BACKUP_COMPONENT}` `never_seen` da yo'q, holbuki yurak urishi YOZILMAGAN: {payload}"
    )
    assert BACKUP_COMPONENT not in payload["stale"], (
        "YOZILMAGAN komponent `stale` ga tushdi — `ok` jimgina `false` bo'lardi"
    )


# ===========================================================================
# (b) MAHSULOT SQL'I — `never_seen` DAN CHIQISH
# ===========================================================================


async def test_the_production_heartbeat_sql_clears_never_seen(
    api_client: httpx.AsyncClient,
    sync_owner_conn: Connection[TupleRow],
    no_backup_heartbeat: None,
) -> None:
    """`heartbeat.sql` bajarilgach `backup` `never_seen` dan CHIQADI.

    ⛔ SHU FAYLDAGI ENG MUHIM DA'VO. U `ops/backup/heartbeat.sql` dagi
       komponent nomini `self_check.py::EXPECTED_COMPONENTS` bilan XULQ
       orqali bog'laydi: nomlar ajralsa zaxira ISHLAB TURGAN holatda ham
       endpoint uni MANGU `never_seen` da ko'rsatardi va `alert_sweep`
       har kuni CRITICAL alert yozardi — to'g'ri ishlayotgan tizim o'zini
       o'zi buzuq deb e'lon qilardi.

    ⚠ `detail.business_date` HAM o'lchanadi: `run-backup.sh` sanani
      `-v day=` bilan uzatadi va uning YO'QOLISHI («qaysi kunning
      zaxirasi?») runbook uchun javobsiz savol bo'lardi.
    """
    day = _market_day()

    _write_heartbeat(sync_owner_conn, day)

    stored = sync_owner_conn.execute(_READ_HEARTBEAT, (BACKUP_COMPONENT,)).fetchone()
    assert stored is not None, (
        f"`{HEARTBEAT_SQL_PATH.name}` bajarildi, lekin `system_heartbeats` da "
        f"`{BACKUP_COMPONENT}` qatori paydo bo'lmadi — komponent nomi "
        "`alerting.BACKUP_COMPONENT` dan AJRALGAN"
    )
    assert stored[1] == {"business_date": day.isoformat()}, (
        f"`detail` kutilgan shaklda emas: {stored[1]!r}"
    )

    payload = _self_check_payload(await api_client.get(SELF_CHECK_URL))

    assert BACKUP_COMPONENT not in payload["never_seen"], (
        f"yurak urishi yozilgan, lekin `{BACKUP_COMPONENT}` HAMON `never_seen` da: {payload}"
    )
    assert BACKUP_COMPONENT not in payload["stale"], (
        f"YANGI yozilgan yurak urishi `stale` deb belgilandi: {payload}"
    )


# ===========================================================================
# (c) VA (d) — `HEARTBEAT_STALE_HOURS` NING IKKI TOMONI
# ===========================================================================


async def test_an_aged_heartbeat_raises_a_critical_backup_stale_alert(
    api_sessionmaker: async_sessionmaker[AsyncSession],
    sync_owner_conn: Connection[TupleRow],
    no_backup_heartbeat: None,
    quiet_alerts: list[str],
) -> None:
    """27 soatlik yurak urishi `backup_stale` (CRITICAL) ni OCHADI.

    ⚠ 27 — `HEARTBEAT_STALE_HOURS` (26) DAN HOSILA, qattiq yozilgan son
      EMAS. Chegara bir kun o'zgarsa bu test u bilan birga siljiydi;
      qadalgan `27` esa chegarani jimgina «26 dan kattaroq nimadir» ga
      aylantirardi.

    ⛔ QATOR MAHSULOT SQL'I BILAN YOZILADI, keyin ORQAGA suriladi. Qo'lda
       yozilgan qator bu testni (b) dan mustaqil qilardi — ya'ni komponent
       nomi ajralganda (b) qizarib, (c) yashil qolardi va zanjirning
       yarmi o'lchanmagan bo'lib qolardi.
    """
    _write_heartbeat(sync_owner_conn, _market_day())
    sync_owner_conn.execute(_AGE_HEARTBEAT, (HEARTBEAT_STALE_HOURS + 1, BACKUP_COMPONENT))

    opened = await _sweep_open_alerts(api_sessionmaker, sync_owner_conn, quiet_alerts)

    severities = {severity for key, severity in opened if key == "backup_stale"}
    assert severities, f"eskirgan yurak urishi `backup_stale` bermadi; ochilgan alertlar: {opened}"
    assert severities == {AlertSeverity.CRITICAL.value}, (
        f"`backup_stale` CRITICAL emas: {severities} — zaxira yo'qolishi `warning` sinfiga tushdi"
    )
    assert "backup_stale" in NEVER_SUPPRESSED_ALERT_KEYS, (
        "`backup_stale` bo'g'iladigan bo'lib qoldi — admin tizim ishlayapti deb "
        "o'ylab turardi, holbuki zaxira uch kundan beri yozilmayapti (D-22)"
    )


async def test_a_fresh_heartbeat_raises_no_backup_alert(
    api_sessionmaker: async_sessionmaker[AsyncSession],
    sync_owner_conn: Connection[TupleRow],
    no_backup_heartbeat: None,
    quiet_alerts: list[str],
) -> None:
    """2 soatlik yurak urishi HECH QANDAY `backup_stale` bermaydi.

    ⛔ NAZORAT HOLATI — VA USIZ (c) BO'SH-ROST BO'LARDI. Har doim alert
       ko'taradigan supurgi (c) ni ham yashil qilardi; bu test aynan
       o'sha shoxni yopadi.

    ⚠ QOLGAN PLATFORMA ALERTLARI (`retention_stale`, `outbox_stale`, ...)
      BU YERDA KUTILADI va ular tekshirilmaydi: ularning joblari bu
      seedda hech qachon yugurmaydi, ya'ni ularning yurak urishi YO'Q va
      `None` HAM ESKIRISH. Da'vo AYNAN `backup_stale` ga qaratilgan.
    """
    _write_heartbeat(sync_owner_conn, _market_day())
    sync_owner_conn.execute(_AGE_HEARTBEAT, (2, BACKUP_COMPONENT))

    opened = await _sweep_open_alerts(api_sessionmaker, sync_owner_conn, quiet_alerts)

    assert "backup_stale" not in {key for key, _severity in opened}, (
        f"YANGI yurak urishi ustida `backup_stale` ochildi: {opened} — "
        f"chegara ({HEARTBEAT_STALE_HOURS} soat) jimgina siljigan"
    )
    assert opened, (
        "nazorat: supurgi BIRORTA alert ochmadi — ya'ni u umuman ishlamagan bo'lishi "
        "mumkin va (c) ning teskarisi hech nimani o'lchamasdi"
    )
