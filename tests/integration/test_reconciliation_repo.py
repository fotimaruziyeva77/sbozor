"""`reconciliation_repo` — case domeni HAQIQIY BAZADA (RECON-02).

=============================================================================
TO'RTTA QOIDA BU FAYLNING SHAKLINI BELGILAYDI.

  1. ⛔ HAQIQIY `postgres:18.4`, soxta qatlam YO'Q. Tekshirilayotgan
     narsaning O'ZI — `ON CONFLICT` semantikasi, IKKI QISMAN UNIQUE
     indeks, kompozit FK va o'zgarmaslik triggeri. Ularni almashtirgan
     test o'z tasavvurini o'lchagan bo'lardi.

  2. ⛔ SESSIYA TENANT KONTEKSTI BILAN (`tenant_session`). Beshala
     bildirishnoma jadvalida RLS `FORCE` bilan yoqilgan va
     `reconciliation_cases` AUDIT triggeri ostida — kontekstsiz yozuv
     umuman o'tmasdi yoki audit qatori egasiz qolardi.

  3. ⛔ SANALAR O'TMISHDA VA ULAR BAZADAN OLINADI (`_days_ago`).
     `daily_charges` / `billing_anomalies` da `service_date <=
     business_date` `CHECK` i bor, `business_date` esa `created_at` DAN
     HOSILA, ya'ni HAR DOIM «bugun». Qadalgan kelajak sanasi
     `CheckViolation` bilan yiqilardi va sabab «seed noto'g'ri» emas,
     «konstrayt buzuq» kabi ko'rinardi (06-05 da o'lchangan).

  4. ⛔ SEED MAHSULOT QARORINI TAKRORLAMAYDI. `no_coverage_stall`
     anomaliyasi ATAYIN yoziladi — mahsulot unga case OCHMAYDI va aynan
     shu YO'QLIK o'lchanadi. Dalilli anomaliya esa HAQIQIY
     `occupancy_events` + `snapshots` juftligidan quriladi: ikkala
     juftlangan `CHECK` (`no_coverage_is_paired`, `evidence_is_paired`)
     boshqa yo'lni umuman rad etardi.
=============================================================================
⚠ TOZALASH TARTIBI MAJBURIY VA U FIXTURE BOG'LANISHI BILAN IFODALANGAN:
  `recon` fixture'i `env` ni ARGUMENT sifatida oladi, ya'ni pytest uni
  BIRINCHI yopadi. `reconciliation_cases` `billing_anomalies` va
  `daily_charges` ga kompozit FK bilan tayanadi va `ondelete` YO'Q
  (NO ACTION) — case'lar avval o'chmasa `cleanup_billing_domain()`
  FK buzilishi bilan yiqilardi.
=============================================================================
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import pytest
from app.jobs.reconciliation import (
    DEFAULT_OVERDUE_DAYS,
    RECON_OPEN_COMPONENT,
    overdue_cutoff,
    reconciliation_open,
)
from app.repositories.reconciliation_repo import (
    CASE_LOOKBACK_DAYS,
    CASE_PAGE_SIZE,
    CASE_WORTHY_ANOMALY_KINDS,
    CaseRow,
    case_evidence,
    hit_rate,
    list_cases,
    open_cases,
    transition,
)
from fixtures.billing_domain import (
    TARIFF_SOUM,
    BillingDomainSeed,
    MarketBillingRows,
    add_daily_charge,
    add_payment,
    billing_domain_before_day_close,
)
from fixtures.market_domain import MarketDomainSeed
from fixtures.notification_domain import (
    cleanup_notification_domain,
    seed_case,
    seed_no_coverage_anomaly,
    seed_notification_settings,
)
from fixtures.nvr_domain import nvr_rows
from fixtures.occupancy_domain import occupancy_rows
from fixtures.snapshot_domain import snapshot_rows
from fixtures.two_markets import TwoMarketSeed
from sbozor_core.enums import (
    AdjustmentDirection,
    AdjustmentReason,
    AnomalyKind,
    ReconciliationCaseStatus,
    ReconciliationSubjectKind,
)

if TYPE_CHECKING:
    from collections.abc import Iterator
    from datetime import date

    from fixtures import TenantSessionFactory
    from psycopg import Connection
    from psycopg.rows import TupleRow
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

pytestmark = pytest.mark.usefixtures("migrated")

_NEW = ReconciliationCaseStatus.NEW.value
_IN_REVIEW = ReconciliationCaseStatus.IN_REVIEW.value
_JUSTIFIED = ReconciliationCaseStatus.JUSTIFIED.value
_UNJUSTIFIED = ReconciliationCaseStatus.UNJUSTIFIED.value

_OVERDUE_DAYS = 3
"""Testlarning kechikish chegarasi — `market_notification_settings` STANDARTI (A3).

⚠ Fixture'dan olinmaydi va bu ATAYIN: bu qiymat `open_cases()` ga
  ARGUMENT bo'lib beriladi, ya'ni test aynan «chegara ISHLAYAPTIMI?»
  savolini o'lchaydi. Sozlamani o'qish `reconciliation_open()` ning ishi
  va u ALOHIDA o'lchanadi.
"""

_INSERT_EVIDENCED_ANOMALY = (
    "INSERT INTO billing_anomalies "
    "(id, market_id, kind, stall_id, service_date, occupancy_event_id, snapshot_id) "
    "VALUES (%s, %s, %s, %s, %s, %s, %s)"
)
"""DALILLI anomaliya — `no_coverage_stall` DAN FARQLI ravishda hodisa TALAB QILADI.

`billing_anomalies` da ikki juftlangan `CHECK` bor:

    (kind = 'no_coverage_stall') = (occupancy_event_id IS NULL)
    (occupancy_event_id IS NULL) = (snapshot_id IS NULL)

Ya'ni case OCHILADIGAN ikkala sinf (`unassigned_occupied` /
`closed_day_occupied`) uchun hodisa VA kadr MAJBURIY. Shuning uchun bu
fayl `occupancy_rows` + `snapshot_rows` zanjirini oladi:
`fixtures/notification_domain.py::seed_no_coverage_anomaly` ATAYIN
ularsiz ishlaydigan YAGONA sinfni yozadi va u bu yerda «case
OCHILMAYDI» tomonini o'lchaydi.

⚠ XOM SQL SHU MODULDA, `fixtures/` DA EMAS: reja bu rejaning
  `files_modified` ini uchta fayl bilan cheklaydi. Umumiy seed'ga
  ko'chirish 07-05/07-06 ning ishi (07-04 SUMMARY ning 4-ochiq bandi
  aynan shu ko'chishni oldindan yozgan).
"""

_EVIDENCE_PAIR = (
    "SELECT e.id, e.snapshot_id FROM occupancy_events e "
    "WHERE e.market_id = %s AND e.snapshot_id IS NOT NULL ORDER BY e.id LIMIT 1"
)
"""Hodisa + kadr juftligi — ZANJIR BAZADAN olinadi, qayta QURILMAYDI.

`fixtures/billing_domain.py::add_charge_evidence` da o'rnatilgan qoida:
juftlikni test o'zi yig'ishga urinsa u tekshirilayotgan mexanizmning
(kompozit FK + juftlangan `CHECK`) NUSXASINI qurgan bo'lardi.
"""

_INSERT_ADJUSTMENT = (
    "INSERT INTO charge_adjustments "
    "(id, market_id, charge_id, direction, reason_code, amount_soum, actor_user_id) "
    "VALUES (%s, %s, %s, %s, %s, %s, %s)"
)
"""Hisob tuzatishi — job darajasidagi NOSOZLIK holatining YAGONA qurilishi.

Hisobning O'ZIDAN katta `decrease` o'sha kunning qoldig'ini MANFIY qiladi
va `allocate_charge_credit()` uni `ValueError` bilan rad etadi. Bu holat
o'sha funksiyaning O'Z docstringida nomlab qo'yilgan («o'ta katta
`decrease` — D-07 ning o'z savoli»), ya'ni u erishib bo'ladigan ma'lumot
holati, soxta nosozlik EMAS.
"""

_SET_MARKET_GUC = "SELECT set_config('app.market_id', %s, false)"
"""Sessiya darajasidagi tenant konteksti — `charge_adjustments` AUDIT ostida.

Jadval `BILLING_AUDITED_TABLES` da va uning DB-triggeri `app.market_id`
GUC'idan o'qiydi. Kontekstsiz `INSERT` audit qatorini EGASIZ qoldirardi.
Blok tugagach kontekst BO'SHATILADI: `sync_owner_conn` autocommit
rejimida ishlaydi va qoldirilgan qiymat keyingi testga sizib o'tardi
(`fixtures/two_markets.py` da o'lchangan sabab).
"""

_HEARTBEAT = "SELECT last_seen_at, detail FROM system_heartbeats WHERE component = %s"

_COUNT_CASES = "SELECT count(*) FROM reconciliation_cases WHERE market_id = %s"
_COUNT_EVENTS = (
    "SELECT count(*) FROM reconciliation_case_events WHERE market_id = %s AND case_id = %s"
)
_CASE_STATUS = "SELECT status, assignee_user_id FROM reconciliation_cases WHERE id = %s"


# ===========================================================================
# Fixture'lar — `test_billing_repo.py::env` naqshi
# ===========================================================================


@dataclass(frozen=True)
class Env:
    """Bir testning butun kirishi — bozor, rastalar, sotuvchi va kassa."""

    billing: BillingDomainSeed
    domain: MarketDomainSeed
    base: TwoMarketSeed

    @property
    def market_id(self) -> UUID:
        return self.billing.market_a.market_id

    @property
    def vendor_id(self) -> UUID:
        return self.billing.market_a.vendor_id

    @property
    def tariff_id(self) -> UUID:
        return self.billing.market_a.tariff_id

    @property
    def stall_ids(self) -> tuple[UUID, ...]:
        return self.domain.market_a.stall_ids

    @property
    def reviewer_id(self) -> UUID:
        """Nazoratchi — `two_markets` NING direktori, yangi foydalanuvchi EMAS.

        `reconciliation_case_events.actor_user_id` `users` ga FK bilan
        tayanadi (`ondelete` YO'Q), ya'ni o'ylab topilgan `uuid4()` qatorni
        FK buzilishi bilan rad etardi.
        """
        return self.base.market_a.director_user_id

    @property
    def market_ids(self) -> tuple[UUID, ...]:
        return self.billing.market_ids


@pytest.fixture
def env(
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    market_domain: MarketDomainSeed,
) -> Iterator[Env]:
    """Slot qatorlarisiz seed — `day_close` CHAQIRILMAYDI.

    Case domeni bandlikka UMUMAN tegmaydi: uning kirishi `billing_anomalies`,
    `daily_charges` va `payments` qatorlari. `day_close` ni chaqirish har
    testga ikki materializatsiya yugurishini qo'shardi va HECH BIR da'voni
    kuchaytirmasdi.

    ⚠ ZANJIR BARIBIR TO'LIQ (`nvr_rows` -> `snapshot_rows` ->
      `occupancy_rows`): DALILLI anomaliya haqiqiy hodisa va kadrni TALAB
      QILADI (`_INSERT_EVIDENCED_ANOMALY` docstringi).
    """
    with (
        nvr_rows(sync_owner_conn, two_markets) as nvr,
        snapshot_rows(sync_owner_conn, nvr) as snaps,
        occupancy_rows(sync_owner_conn, two_markets, market_domain, snaps) as occupancy,
        billing_domain_before_day_close(
            sync_owner_conn, two_markets, market_domain, occupancy
        ) as billing,
    ):
        yield Env(billing, market_domain, two_markets)


@pytest.fixture
def recon(sync_owner_conn: Connection[TupleRow], env: Env) -> Iterator[Env]:
    """`env` USTIGA bildirishnoma jadvallarining tozalanishi.

    ⚠ `env` ARGUMENT sifatida olinadi, faqat «oldin ishlasin» uchun emas:
      pytest fixture'larni TESKARI tartibda yopadi, ya'ni case'lar billing
      qatorlaridan OLDIN o'chadi. Teskari holatda
      `cleanup_billing_domain()` ning `DELETE FROM billing_anomalies` i
      hali havola qilib turgan case tufayli FK buzilishi bilan yiqilardi
      (`fk_reconciliation_cases_anomaly` da `ondelete` YO'Q).
    """
    try:
        yield env
    finally:
        cleanup_notification_domain(sync_owner_conn, market_ids=list(env.market_ids))


# ===========================================================================
# Yordamchilar
# ===========================================================================


def _days_ago(conn: Connection[TupleRow], days: int) -> date:
    """`CURRENT_DATE - days` — ⛔ BAZADAN, `date.today()` DAN EMAS.

    `date.today()` test JARAYONINING mintaqasida hisoblanadi (konteynerda
    `TZ=Asia/Tashkent`), `business_date` esa BAZADA. Yarim tunda ikkalasi
    bir kun farq qilardi va `service_date <= business_date` `CHECK` i
    tasodifan yiqilardi — ya'ni test FLAKY bo'lardi va sabab kodda emas,
    soatda bo'lardi.
    """
    row = conn.execute("SELECT (CURRENT_DATE - %s::int)::date", (days,)).fetchone()
    assert row is not None, "baza sanani qaytarmadi"
    value: date = row[0]
    return value


def _seed_evidenced_anomaly(
    conn: Connection[TupleRow],
    *,
    market_id: UUID,
    stall_id: UUID,
    service_date: date,
    kind: AnomalyKind,
) -> UUID:
    """Case OCHILADIGAN sinfdagi anomaliya — dalil zanjiri bilan."""
    row = conn.execute(_EVIDENCE_PAIR, (str(market_id),)).fetchone()
    assert row is not None, (
        f"{market_id}: kadrga bog'langan `occupancy_events` qatori topilmadi. "
        "Dalilli anomaliyani `evidence_is_paired` `CHECK` i usiz rad etadi, "
        "ya'ni bu holatda test mahsulotni emas, seedni o'lchagan bo'lardi."
    )
    event_id, snapshot_id = row
    anomaly_id = uuid4()
    conn.execute(
        _INSERT_EVIDENCED_ANOMALY,
        (
            str(anomaly_id),
            str(market_id),
            kind.value,
            str(stall_id),
            service_date,
            str(event_id),
            str(snapshot_id),
        ),
    )
    return anomaly_id


def _seed_cases_with_statuses(
    conn: Connection[TupleRow],
    *,
    market_id: UUID,
    stall_ids: tuple[UUID, ...],
    service_date: date,
    statuses: tuple[str, ...],
) -> tuple[UUID, ...]:
    """Har biriga O'Z nishoni bo'lgan case'lar — qisman UNIQUE indeks talabi.

    ⚠ HAR CASE UCHUN ALOHIDA RASTA: `uq_billing_anomalies_market_stall_
      service_date_kind` bir kunda bir rastaga bitta anomaliya beradi va
      `uq_reconciliation_cases_anomaly` bir anomaliyaga bitta case beradi.
      Ya'ni `statuses` uzunligi rastalar sonidan oshsa seed O'ZI yiqiladi
      — va bu to'g'ri: jimgina kamroq case yozish testni BO'SH ROST
      qilardi.
    """
    assert len(statuses) <= len(stall_ids), (
        f"{len(statuses)} ta case so'raldi, lekin bozorda {len(stall_ids)} ta rasta bor. "
        "Har case O'Z anomaliyasini talab qiladi (qisman UNIQUE indekslar)."
    )
    case_ids: list[UUID] = []
    for stall_id, status in zip(stall_ids, statuses, strict=False):
        anomaly_id = seed_no_coverage_anomaly(
            conn, market_id=market_id, stall_id=stall_id, service_date=service_date
        )
        case_ids.append(
            seed_case(
                conn,
                market_id=market_id,
                service_date=service_date,
                anomaly_id=anomaly_id,
                status=status,
            )
        )
    return tuple(case_ids)


def _case_count(conn: Connection[TupleRow], market_id: UUID) -> int:
    row = conn.execute(_COUNT_CASES, (str(market_id),)).fetchone()
    assert row is not None
    return int(row[0])


# ===========================================================================
# 1. IKKI SINF VA IDEMPOTENTLIK
# ===========================================================================


async def test_case_worthy_kinds_are_derived_from_the_enum(recon: Env) -> None:
    """⛔ RO'YXAT LITERAL EMAS — `AnomalyKind` DAN ITERATSIYA.

    Qo'lda yozilgan kortej enum o'zgargan kuni JIMGINA eskirardi: so'rov
    ishlayverardi, faqat natija to'liqsiz bo'lardi. Bu darvoza aynan o'sha
    ajralishni ushlaydi.
    """
    expected = {kind.value for kind in AnomalyKind} - {AnomalyKind.NO_COVERAGE_STALL.value}
    assert set(CASE_WORTHY_ANOMALY_KINDS) == expected, (
        f"case ochiladigan sinflar ro'yxati enumdan ajralib ketdi: "
        f"{sorted(CASE_WORTHY_ANOMALY_KINDS)} != {sorted(expected)}"
    )
    assert AnomalyKind.NO_COVERAGE_STALL.value not in CASE_WORTHY_ANOMALY_KINDS


async def test_open_cases_opens_one_case_per_case_worthy_anomaly(
    sync_owner_conn: Connection[TupleRow],
    tenant_session: TenantSessionFactory,
    recon: Env,
) -> None:
    """SINF B — `billing_anomalies` qatoridan case tug'iladi (Pattern 4)."""
    day = _days_ago(sync_owner_conn, 1)
    _seed_evidenced_anomaly(
        sync_owner_conn,
        market_id=recon.market_id,
        stall_id=recon.stall_ids[0],
        service_date=day,
        kind=AnomalyKind.UNASSIGNED_OCCUPIED,
    )
    _seed_evidenced_anomaly(
        sync_owner_conn,
        market_id=recon.market_id,
        stall_id=recon.stall_ids[1],
        service_date=day,
        kind=AnomalyKind.CLOSED_DAY_OCCUPIED,
    )

    async with tenant_session(recon.market_id) as session:
        result = await open_cases(
            session,
            market_id=recon.market_id,
            business_date=day,
            cutoff=overdue_cutoff(day, _OVERDUE_DAYS),
        )

    assert result.anomaly_cases == 2, f"ikkala sinf ham case ochishi kerak edi: {result}"
    assert result.skipped_existing == 0
    assert _case_count(sync_owner_conn, recon.market_id) == 2


async def test_no_coverage_anomaly_never_opens_a_case(
    sync_owner_conn: Connection[TupleRow],
    tenant_session: TenantSessionFactory,
    recon: Env,
) -> None:
    """⛔ `no_coverage_stall` NAVBATGA TUSHMAYDI (Pattern 4).

    U kamera qamrovi nuqsoni, tushum nomuvofiqligi EMAS. Uni qamrash
    navbatni har kuni KO'R NUQTALAR bilan to'ldirardi va nazoratchining
    diqqati haqiqiy nomuvofiqlikdan chalg'irdi.

    ⚠ NAZORAT: shu kunda anomaliya HAQIQATAN bor — usiz «0 case» da'vosi
      BO'SH ROST bo'lardi (5-fazaning W-2 darsi).
    """
    day = _days_ago(sync_owner_conn, 1)
    seed_no_coverage_anomaly(
        sync_owner_conn,
        market_id=recon.market_id,
        stall_id=recon.stall_ids[0],
        service_date=day,
    )
    seeded = sync_owner_conn.execute(
        "SELECT count(*) FROM billing_anomalies WHERE market_id = %s AND service_date = %s",
        (str(recon.market_id), day),
    ).fetchone()
    assert seeded is not None and int(seeded[0]) == 1, "nazorat: anomaliya seed qilinmadi"

    async with tenant_session(recon.market_id) as session:
        result = await open_cases(
            session,
            market_id=recon.market_id,
            business_date=day,
            cutoff=overdue_cutoff(day, _OVERDUE_DAYS),
        )

    assert result.anomaly_cases == 0, (
        f"`no_coverage_stall` ga case ochildi: {result}. Bu ko'r nuqtadan "
        "tushum da'vosi to'qish bo'lardi (D-05)."
    )
    assert _case_count(sync_owner_conn, recon.market_id) == 0


async def test_open_cases_is_idempotent_across_two_runs(
    sync_owner_conn: Connection[TupleRow],
    tenant_session: TenantSessionFactory,
    recon: Env,
) -> None:
    """⛔ QAYTA YUGURISH IKKINCHI CASE OCHMAYDI (D-21).

    `recon.open` KONVERGENT — o'sha kun uchun qayta-qayta yugurishi NORMAL
    holat. Idempotentlik ILOVA INTIZOMIDA emas, IKKI QISMAN UNIQUE
    indeksda: ikki parallel yugurish ham ikkinchi qatorni STRUKTURAVIY
    yoza olmaydi.

    ⚠ IKKI ALOHIDA TRANZAKSIYA (ikki `tenant_session` bloki): bitta
      tranzaksiya ichidagi ikkinchi chaqiruv birinchisining yozuvini
      O'ZINING snapshot'ida ko'rardi, ya'ni test cron'ning ikki
      yugurishini emas, bitta tranzaksiyani o'lchagan bo'lardi.
    """
    day = _days_ago(sync_owner_conn, 1)
    _seed_evidenced_anomaly(
        sync_owner_conn,
        market_id=recon.market_id,
        stall_id=recon.stall_ids[0],
        service_date=day,
        kind=AnomalyKind.UNASSIGNED_OCCUPIED,
    )

    async with tenant_session(recon.market_id) as session:
        first = await open_cases(
            session,
            market_id=recon.market_id,
            business_date=day,
            cutoff=overdue_cutoff(day, _OVERDUE_DAYS),
        )
    after_first = _case_count(sync_owner_conn, recon.market_id)
    assert first.anomaly_cases == 1
    assert after_first == 1, "nazorat: birinchi yugurish case yozmadi"

    async with tenant_session(recon.market_id) as session:
        second = await open_cases(
            session,
            market_id=recon.market_id,
            business_date=day,
            cutoff=overdue_cutoff(day, _OVERDUE_DAYS),
        )

    assert _case_count(sync_owner_conn, recon.market_id) == after_first, (
        "ikkinchi yugurish qator soni o'zgartirdi — idempotentlik buzildi"
    )
    assert second.anomaly_cases == 0
    assert second.skipped_existing > 0, (
        f"o'tkazib yuborilgan case sanalmadi: {second}. Sanoq nolga tushsa "
        "qayta yugurish «hech nima topilmadi» bilan mexanik ravishda bir "
        "xil ko'rinardi."
    )


# ===========================================================================
# 2. SINF A — KECHIKISH CHEGARASI VA TO'LOV (Pattern 5)
# ===========================================================================


async def test_a_fresh_unpaid_charge_stays_out_of_the_queue(
    sync_owner_conn: Connection[TupleRow],
    tenant_session: TenantSessionFactory,
    recon: Env,
) -> None:
    """⛔ KECHIKISH CHEGARASI — bugungi to'lanmagan hisob case OCHMAYDI.

    To'lov kun davomida keladi. Chegarasiz har ertalab HAR hisob uchun
    case ochilardi va navbat birinchi haftada SHOVQINGA aylanardi —
    `alerting.py` ning D-22 bandi bu nosozlik sinfini raqam bilan yozgan.
    """
    today = _days_ago(sync_owner_conn, 0)
    add_daily_charge(
        sync_owner_conn,
        market_id=recon.market_id,
        stall_id=recon.stall_ids[0],
        vendor_id=recon.vendor_id,
        tariff_id=recon.tariff_id,
        service_date=today,
    )

    async with tenant_session(recon.market_id) as session:
        result = await open_cases(
            session,
            market_id=recon.market_id,
            business_date=today,
            cutoff=overdue_cutoff(today, _OVERDUE_DAYS),
        )

    assert result.unpaid_cases == 0, (
        f"kechikmagan hisob navbatga tushdi: {result}. Chegara "
        "(`overdue_days={_OVERDUE_DAYS}`) ishlamayapti."
    )


async def test_a_charge_older_than_the_window_opens_a_case(
    sync_owner_conn: Connection[TupleRow],
    tenant_session: TenantSessionFactory,
    recon: Env,
) -> None:
    """SINF A — chegaradan o'tgan to'lanmagan hisob case OCHADI.

    ⚠ Bu test oldingisining JUFTI: yolg'iz «case ochilmadi» da'vosi
      funksiya UMUMAN ishlamaganda ham rost bo'lardi.
    """
    today = _days_ago(sync_owner_conn, 0)
    overdue_day = _days_ago(sync_owner_conn, _OVERDUE_DAYS + 1)
    charge_id, _ = add_daily_charge(
        sync_owner_conn,
        market_id=recon.market_id,
        stall_id=recon.stall_ids[0],
        vendor_id=recon.vendor_id,
        tariff_id=recon.tariff_id,
        service_date=overdue_day,
    )

    async with tenant_session(recon.market_id) as session:
        result = await open_cases(
            session,
            market_id=recon.market_id,
            business_date=today,
            cutoff=overdue_cutoff(today, _OVERDUE_DAYS),
        )

    assert result.unpaid_cases == 1, f"kechikkan hisob navbatga tushmadi: {result}"

    row = sync_owner_conn.execute(
        "SELECT subject_kind, charge_id, anomaly_id, service_date "
        "FROM reconciliation_cases WHERE market_id = %s",
        (str(recon.market_id),),
    ).fetchone()
    assert row is not None
    assert row[0] == ReconciliationSubjectKind.OCCUPIED_UNPAID.value
    assert UUID(str(row[1])) == charge_id
    assert row[2] is None, "XOR buzildi: hisob case'ida `anomaly_id` to'ldirilgan"
    assert row[3] == overdue_day, "case sanasi hisobning kunidan ajralib ketdi"


async def test_a_settled_vendor_gets_no_unpaid_case(
    sync_owner_conn: Connection[TupleRow],
    tenant_session: TenantSessionFactory,
    recon: Env,
) -> None:
    """⛔ TO'LOV CASE OCHILISHINI TO'SADI — «to'lanmagan» ta'rifi bitta.

    Predikat `vendor_outstanding()` + `vendor_charge_allocation()` dan
    chiqadi, ya'ni to'liq to'lagan sotuvchi birinchi qadamdayoq ro'yxatdan
    CHIQADI. Yangi SQL yozilganda bu ikki ta'rif bir kun ajralib ketardi.
    """
    today = _days_ago(sync_owner_conn, 0)
    overdue_day = _days_ago(sync_owner_conn, _OVERDUE_DAYS + 1)
    add_daily_charge(
        sync_owner_conn,
        market_id=recon.market_id,
        stall_id=recon.stall_ids[0],
        vendor_id=recon.vendor_id,
        tariff_id=recon.tariff_id,
        service_date=overdue_day,
        amount_soum=TARIFF_SOUM,
    )
    add_payment(
        sync_owner_conn,
        market_id=recon.market_id,
        stall_id=recon.stall_ids[0],
        vendor_id=recon.vendor_id,
        cashier_id=recon.billing.market_a.cashier_id,
        shift_id=recon.billing.market_a.open_shift_id,
        service_date=overdue_day,
        amount_soum=TARIFF_SOUM,
        quote_soum=TARIFF_SOUM,
    )

    async with tenant_session(recon.market_id) as session:
        result = await open_cases(
            session,
            market_id=recon.market_id,
            business_date=today,
            cutoff=overdue_cutoff(today, _OVERDUE_DAYS),
        )

    assert result.unpaid_cases == 0, (
        f"to'liq to'langan hisob uchun case ochildi: {result}. Sotuvchi "
        "pulini bergan holda navbatga tushardi va nizo aynan shu yerdan "
        "boshlanardi (D-02)."
    )
    assert _case_count(sync_owner_conn, recon.market_id) == 0


async def test_a_charge_inside_the_lookback_window_opens_a_case(
    sync_owner_conn: Connection[TupleRow],
    tenant_session: TenantSessionFactory,
    recon: Env,
) -> None:
    """NOMZODLAR OYNASI — oyna ICHIDAGI eski hisob avvalgidek case ochadi.

    ⚠ Bu (b) va (c) ning MAJBURIY nazorati: yolg'iz «oynadan eskisi
      tushmadi» da'vosi oyna BUTUN SINF A ni o'ldirganda ham rost
      bo'lardi (5-fazaning W-2 darsi).
    """
    today = _days_ago(sync_owner_conn, 0)
    inside = _days_ago(sync_owner_conn, CASE_LOOKBACK_DAYS - 1)
    add_daily_charge(
        sync_owner_conn,
        market_id=recon.market_id,
        stall_id=recon.stall_ids[0],
        vendor_id=recon.vendor_id,
        tariff_id=recon.tariff_id,
        service_date=inside,
    )

    async with tenant_session(recon.market_id) as session:
        result = await open_cases(
            session,
            market_id=recon.market_id,
            business_date=today,
            cutoff=overdue_cutoff(today, _OVERDUE_DAYS),
        )

    assert result.unpaid_cases == 1, (
        f"oyna ICHIDAGI ({CASE_LOOKBACK_DAYS - 1} kunlik) to'lanmagan hisob "
        f"navbatga tushmadi: {result}. Oyna SINF A ning o'zini o'chirib qo'ydi."
    )


async def test_a_charge_older_than_the_lookback_window_opens_no_case(
    sync_owner_conn: Connection[TupleRow],
    tenant_session: TenantSessionFactory,
    recon: Env,
) -> None:
    """⛔ WR-09 — OYNADAN ESKI QARZ NAVBATGA TUSHMAYDI, U REESTRDA KO'RINADI.

    Chegarasiz har yugurishda BUTUN tarixning to'lanmagan hisoblari
    nomzod bo'lardi va ular uchun case O'SHA HISOBNING KUNI bilan
    ochilardi. Yagona ro'yxat yuzasi esa KUN kesimida (`?day=`,
    standart kun KECHA), ya'ni bu case'lar ekranda ⛔ HECH QACHON
    ko'rinmasdi — `hit_rate()` ning `pending` sanog'i esa ular bilan
    doimiy shishib, «hali O'LCHOV YO'Q» signalini shovqinga aylantirardi.

    ⚠ MA'LUMOT YO'QOLMAYDI, YUZASI ALMASHADI: oynadan eski to'lanmagan
      hisob QARZDORLIK REESTRIGA (RECON-04) tegishli.
    """
    today = _days_ago(sync_owner_conn, 0)
    ancient = _days_ago(sync_owner_conn, CASE_LOOKBACK_DAYS + 1)
    add_daily_charge(
        sync_owner_conn,
        market_id=recon.market_id,
        stall_id=recon.stall_ids[0],
        vendor_id=recon.vendor_id,
        tariff_id=recon.tariff_id,
        service_date=ancient,
    )

    async with tenant_session(recon.market_id) as session:
        result = await open_cases(
            session,
            market_id=recon.market_id,
            business_date=today,
            cutoff=overdue_cutoff(today, _OVERDUE_DAYS),
        )

    assert result.unpaid_cases == 0, (
        f"oynadan ESKI ({CASE_LOOKBACK_DAYS + 1} kunlik) hisob uchun case "
        f"ochildi: {result}. U kun kesimidagi ekranda ko'rinmasdi va "
        "`hit_rate()` ning `pending` sanog'ini doimiy shishirardi (WR-09)."
    )
    assert _case_count(sync_owner_conn, recon.market_id) == 0


async def test_the_lookback_boundary_day_still_opens_a_case(
    sync_owner_conn: Connection[TupleRow],
    tenant_session: TenantSessionFactory,
    recon: Env,
) -> None:
    """⛔ CHEGARAVIY KUN — `>=`, `>` EMAS. Aynan `business_date - N` KIRADI.

    `>` yozilganda oynaning eng chekkasidagi kun JIMGINA tushib qolardi
    va farq FAQAT o'sha bir kunda ko'rinardi — ya'ni nosozlik oyiga bir
    marta, tasodifiy bozorda chiqardi. `_OVERDUE_CHARGES` ning yuqori
    chegarasi (`<= :cutoff`) bilan AYNAN bir xil qoida va bir xil sabab.
    """
    today = _days_ago(sync_owner_conn, 0)
    boundary = _days_ago(sync_owner_conn, CASE_LOOKBACK_DAYS)
    add_daily_charge(
        sync_owner_conn,
        market_id=recon.market_id,
        stall_id=recon.stall_ids[0],
        vendor_id=recon.vendor_id,
        tariff_id=recon.tariff_id,
        service_date=boundary,
    )

    async with tenant_session(recon.market_id) as session:
        result = await open_cases(
            session,
            market_id=recon.market_id,
            business_date=today,
            cutoff=overdue_cutoff(today, _OVERDUE_DAYS),
        )

    assert result.unpaid_cases == 1, (
        f"chegaraviy kun (`business_date - {CASE_LOOKBACK_DAYS}`) qamralmadi: "
        f"{result}. Quyi chegara `>` bo'lib qolgan — oynaning eng chekkasidagi "
        "kun jimgina tushib qoladi."
    )
    row = sync_owner_conn.execute(
        "SELECT service_date FROM reconciliation_cases WHERE market_id = %s",
        (str(recon.market_id),),
    ).fetchone()
    assert row is not None and row[0] == boundary, (
        "case chegaraviy kun bilan ochilmadi — `service_date` manbasi ajralgan"
    )


async def test_open_cases_refuses_a_non_positive_threshold(
    sync_owner_conn: Connection[TupleRow],
    tenant_session: TenantSessionFactory,
    recon: Env,
) -> None:
    """⛔ CHEGARA NOL BO'LA OLMAYDI — `ValueError`, jim davom etish EMAS.

    Nol chegara HAR hisob uchun case ochardi. Sxema uni allaqachon
    to'sadi, lekin `COALESCE` orqali kelgan KOD standarti sxemani
    chetlab o'tardi.

    ⚠ `overdue_days = 0` ENDI `cutoff == business_date` SHAKLIDA
      beriladi (08-06): chegarani repo emas, JOB hisoblaydi
      (`overdue_cutoff()`), ya'ni rad etish sharti ham shu qiymat
      ustida yoziladi. O'lchanadigan xulq O'ZGARMADI.
    """
    today = _days_ago(sync_owner_conn, 0)
    async with tenant_session(recon.market_id) as session:
        with pytest.raises(ValueError, match="overdue_days"):
            await open_cases(
                session,
                market_id=recon.market_id,
                business_date=today,
                cutoff=overdue_cutoff(today, 0),
            )


# ===========================================================================
# 3. HIT-RATE — HOSILA, MAXRAJ D-13 DA QULFLANGAN
# ===========================================================================


async def test_hit_rate_is_the_ratio_of_closed_cases(
    sync_owner_conn: Connection[TupleRow],
    tenant_session: TenantSessionFactory,
    recon: Env,
) -> None:
    """`justified=3, unjustified=1` -> `0.75`."""
    day = _days_ago(sync_owner_conn, 1)
    _seed_cases_with_statuses(
        sync_owner_conn,
        market_id=recon.market_id,
        stall_ids=recon.stall_ids,
        service_date=day,
        statuses=(_JUSTIFIED, _JUSTIFIED, _JUSTIFIED, _UNJUSTIFIED),
    )

    async with tenant_session(recon.market_id) as session:
        measured = await hit_rate(session, market_id=recon.market_id, date_from=day, date_to=day)

    assert measured.justified == 3
    assert measured.unjustified == 1
    assert measured.rate == 0.75, f"nisbat noto'g'ri: {measured}"


async def test_hit_rate_is_none_when_nothing_was_measured(
    sync_owner_conn: Connection[TupleRow],
    tenant_session: TenantSessionFactory,
    recon: Env,
) -> None:
    """⛔ O'LCHOV YO'Q BO'LGANDA `None`, NOL EMAS (D-13).

    Nol yozish «tizim aniqligi nol» degan YOLG'ON da'vo bo'lardi va u
    direktorning birinchi haftadagi qaroriga bevosita ta'sir qilardi —
    5-fazaning Wilson qarori bilan aynan bir sinf.
    """
    day = _days_ago(sync_owner_conn, 1)
    async with tenant_session(recon.market_id) as session:
        measured = await hit_rate(session, market_id=recon.market_id, date_from=day, date_to=day)

    assert measured.rate is None, f"o'lchanmagan holat nolga aylandi: {measured}"
    assert measured.justified == 0
    assert measured.unjustified == 0


async def test_pending_cases_do_not_move_the_hit_rate(
    sync_owner_conn: Connection[TupleRow],
    tenant_session: TenantSessionFactory,
    recon: Env,
) -> None:
    """⛔ `new` VA `in_review` MAXRAJGA KIRMAYDI (D-13).

    =======================================================================
    ⛔ SABOTAJ SHU TESTDA O'LCHANADI. Maxrajga `new` qo'shilsa nisbat
       `3 / (3 + 1 + 1)` = `0.6` bo'lardi va bu test QIZARADI. Qizarmasa
       seedda `new` qatori yo'q — shuning uchun pastdagi NAZORAT ASSERTI
       majburiy (05-15 ning S-D darsi: darvoza o'lchayotgan holatning
       MAVJUDLIGINI isbotlashi kerak).
    =======================================================================

    Sabab mexanik: hali ko'rilmagan case metrikani PASAYTIRARDI, ya'ni
    navbatni tez ko'rib chiqmaslik ko'rsatkichni yomonlashtirardi va
    ko'rsatkich o'z jarayonini o'lchash o'rniga uning KECHIKISHINI
    o'lchardi.
    """
    day = _days_ago(sync_owner_conn, 1)
    _seed_cases_with_statuses(
        sync_owner_conn,
        market_id=recon.market_id,
        stall_ids=recon.stall_ids,
        service_date=day,
        statuses=(_JUSTIFIED, _JUSTIFIED, _JUSTIFIED, _UNJUSTIFIED, _NEW, _IN_REVIEW),
    )

    async with tenant_session(recon.market_id) as session:
        measured = await hit_rate(session, market_id=recon.market_id, date_from=day, date_to=day)

    assert measured.pending == 2, (
        f"NAZORAT: seedda `new`/`in_review` qatori yo'q ({measured}) — bu "
        "holatda maxraj testi hech nimani o'lchamasdi."
    )
    assert measured.rate == 0.75, (
        f"kutilmagan holatlar maxrajga kirdi: {measured}. `new`/`in_review` "
        "hisobga olinsa nisbat 0.6 bo'lardi."
    )


# ===========================================================================
# 4. HOLAT O'ZGARISHI — IKKI YOZUV, BITTA TRANZAKSIYA (D-14)
# ===========================================================================


async def test_transition_writes_exactly_one_event_row(
    sync_owner_conn: Connection[TupleRow],
    tenant_session: TenantSessionFactory,
    recon: Env,
) -> None:
    """Har o'tish AYNAN BITTA tarix qatorini tug'diradi (D-14)."""
    day = _days_ago(sync_owner_conn, 1)
    (case_id,) = _seed_cases_with_statuses(
        sync_owner_conn,
        market_id=recon.market_id,
        stall_ids=recon.stall_ids,
        service_date=day,
        statuses=(_NEW,),
    )

    async with tenant_session(recon.market_id, recon.reviewer_id) as session:
        first = await transition(
            session,
            market_id=recon.market_id,
            case_id=case_id,
            to_status=_IN_REVIEW,
            actor_user_id=recon.reviewer_id,
            note="nazoratchi qo'lga oldi",
        )
    assert first.from_status == _NEW
    assert first.to_status == _IN_REVIEW

    events = sync_owner_conn.execute(_COUNT_EVENTS, (str(recon.market_id), str(case_id))).fetchone()
    assert events is not None and int(events[0]) == 1, (
        "bitta o'tish bitta qator yozishi kerak edi (D-14)"
    )

    status_row = sync_owner_conn.execute(_CASE_STATUS, (str(case_id),)).fetchone()
    assert status_row is not None
    assert status_row[0] == _IN_REVIEW
    assert UUID(str(status_row[1])) == recon.reviewer_id, "mas'ul biriktirilmadi"

    # ⛔ YOPILGAN HOLATDAN QAYTISH RUXSAT va u ham YANGI QATOR yozadi.
    async with tenant_session(recon.market_id, recon.reviewer_id) as session:
        await transition(
            session,
            market_id=recon.market_id,
            case_id=case_id,
            to_status=_JUSTIFIED,
            actor_user_id=recon.reviewer_id,
            note="nomuvofiqlik tasdiqlandi",
        )
    async with tenant_session(recon.market_id, recon.reviewer_id) as session:
        reopened = await transition(
            session,
            market_id=recon.market_id,
            case_id=case_id,
            to_status=_IN_REVIEW,
            actor_user_id=recon.reviewer_id,
            note="xato yopilgan edi",
        )
    assert reopened.from_status == _JUSTIFIED

    events = sync_owner_conn.execute(_COUNT_EVENTS, (str(recon.market_id), str(case_id))).fetchone()
    assert events is not None and int(events[0]) == 3, (
        "uchta o'tish uchta qator yozishi kerak edi — qaytish TAHRIR emas, YANGI QATOR (D-14)"
    )


async def test_transition_to_the_same_status_is_refused(
    sync_owner_conn: Connection[TupleRow],
    tenant_session: TenantSessionFactory,
    recon: Env,
) -> None:
    """⛔ NOL O'TISH RAD ETILADI — tarix shovqin bilan to'lmaydi (D-14)."""
    day = _days_ago(sync_owner_conn, 1)
    (case_id,) = _seed_cases_with_statuses(
        sync_owner_conn,
        market_id=recon.market_id,
        stall_ids=recon.stall_ids,
        service_date=day,
        statuses=(_NEW,),
    )

    async with tenant_session(recon.market_id, recon.reviewer_id) as session:
        with pytest.raises(ValueError, match=_NEW):
            await transition(
                session,
                market_id=recon.market_id,
                case_id=case_id,
                to_status=_NEW,
                actor_user_id=recon.reviewer_id,
            )

    events = sync_owner_conn.execute(_COUNT_EVENTS, (str(recon.market_id), str(case_id))).fetchone()
    assert events is not None and int(events[0]) == 0, "rad etilgan o'tish qator yozdi"


async def test_transition_on_a_foreign_case_is_a_lookup_error(
    tenant_session: TenantSessionFactory,
    recon: Env,
) -> None:
    """Topilmagan case JIM `return` QILMAYDI — chaqiruvchi «o'zgardi» deb o'ylardi."""
    async with tenant_session(recon.market_id, recon.reviewer_id) as session:
        with pytest.raises(LookupError):
            await transition(
                session,
                market_id=recon.market_id,
                case_id=uuid4(),
                to_status=_IN_REVIEW,
                actor_user_id=recon.reviewer_id,
            )


# ===========================================================================
# 5. NAVBAT RO'YXATI — KEYSET VA HISOBLAGICHLAR (DQ-4)
# ===========================================================================


async def test_list_cases_keyset_never_repeats_a_row(
    sync_owner_conn: Connection[TupleRow],
    tenant_session: TenantSessionFactory,
    recon: Env,
) -> None:
    """⛔ KEYSET — ikkinchi sahifada birinchisining `id` lari TAKRORLANMAYDI.

    `OFFSET` bilan sahifalaganda navbat kun davomida o'sgani uchun
    nazoratchi bir case'ni IKKI MARTA ko'rib, ikkinchisini UMUMAN
    ko'rmasdi — va buni SEZMASDI ham.
    """
    day = _days_ago(sync_owner_conn, 1)
    seeded = _seed_cases_with_statuses(
        sync_owner_conn,
        market_id=recon.market_id,
        stall_ids=recon.stall_ids,
        service_date=day,
        statuses=(_NEW, _NEW, _NEW, _NEW),
    )

    async with tenant_session(recon.market_id) as session:
        first = await list_cases(session, market_id=recon.market_id, day=day, limit=2)
        assert first.next_cursor is not None, "to'lgan sahifa kursorsiz qaytdi"
        second = await list_cases(
            session, market_id=recon.market_id, day=day, limit=2, cursor=first.next_cursor
        )

    first_ids = {row.case_id for row in first.rows}
    second_ids = {row.case_id for row in second.rows}
    assert len(first.rows) == 2
    assert len(second.rows) == 2
    assert not (first_ids & second_ids), (
        f"sahifalar kesishdi: {sorted(map(str, first_ids & second_ids))}"
    )
    assert first_ids | second_ids == set(seeded), "sahifalash qatorni tushirib qoldirdi"

    order: list[CaseRow] = [*first.rows, *second.rows]
    timestamps = [row.created_at for row in order]
    assert timestamps == sorted(timestamps, reverse=True), (
        "tartib `created_at DESC` emas — kursor indeksdan ajralib ketdi"
    )


async def test_list_cases_returns_all_four_counters_even_on_an_empty_day(
    sync_owner_conn: Connection[TupleRow],
    tenant_session: TenantSessionFactory,
    recon: Env,
) -> None:
    """⛔ NOL — NATIJA: to'rtala hisoblagich ham HAR DOIM qaytadi.

    «Bu kunda case yo'q» bilan «hisoblagich ishlamayapti» bir xil ko'rinsa
    direktor tizimni buzuq deb hisoblardi (`ChargeListResponse` qarori).
    """
    day = _days_ago(sync_owner_conn, 1)
    async with tenant_session(recon.market_id) as session:
        empty = await list_cases(session, market_id=recon.market_id, day=day)

    assert empty.day == day
    assert empty.rows == ()
    assert empty.next_cursor is None
    assert (empty.new_count, empty.in_review_count) == (0, 0)
    assert (empty.justified_count, empty.unjustified_count) == (0, 0)

    _seed_cases_with_statuses(
        sync_owner_conn,
        market_id=recon.market_id,
        stall_ids=recon.stall_ids,
        service_date=day,
        statuses=(_NEW, _IN_REVIEW, _JUSTIFIED, _UNJUSTIFIED),
    )
    async with tenant_session(recon.market_id) as session:
        filtered = await list_cases(session, market_id=recon.market_id, day=day, status=_NEW)

    assert [row.status for row in filtered.rows] == [_NEW], "holat filtri ishlamadi"
    assert (filtered.new_count, filtered.in_review_count) == (1, 1)
    assert (filtered.justified_count, filtered.unjustified_count) == (1, 1), (
        f"hisoblagichlar filtrga ergashdi: {filtered}. Ular KUNGA tegishli, "
        "sahifaga emas — aks holda «bugun hech nima yopilmadi» bilan "
        "«filtr yoqilgan» mexanik ravishda bir xil ko'rinardi."
    )
    assert filtered.next_cursor is None, "to'lmagan sahifa kursor berdi"


async def test_list_cases_page_size_is_capped(
    sync_owner_conn: Connection[TupleRow],
    tenant_session: TenantSessionFactory,
    recon: Env,
) -> None:
    """Klient bir so'rov bilan butun navbatni tortib ololmaydi (DQ-4)."""
    day = _days_ago(sync_owner_conn, 1)
    _seed_cases_with_statuses(
        sync_owner_conn,
        market_id=recon.market_id,
        stall_ids=recon.stall_ids,
        service_date=day,
        statuses=(_NEW, _NEW),
    )
    async with tenant_session(recon.market_id) as session:
        page = await list_cases(
            session, market_id=recon.market_id, day=day, limit=CASE_PAGE_SIZE * 10
        )
    assert len(page.rows) == 2


# ===========================================================================
# 6. DALIL — FAQAT IDENTIFIKATOR (D-03, T-06-81)
# ===========================================================================


async def test_case_evidence_returns_identifiers_only(
    sync_owner_conn: Connection[TupleRow],
    tenant_session: TenantSessionFactory,
    recon: Env,
) -> None:
    """⛔ DALIL — `UUID`, bayt ham, imzolangan havola ham EMAS (D-03).

    Kadrda tashrifchilar yuzi bor (O'zR shaxsiy ma'lumotlar qonuni) va
    dalil-kadr yuzasi KENGAYMAYDI: klient identifikatorni MAVJUD, AUTENTI-
    FIKATSIYA ostidagi kadr marshrutiga beradi.
    """
    day = _days_ago(sync_owner_conn, 1)
    _seed_evidenced_anomaly(
        sync_owner_conn,
        market_id=recon.market_id,
        stall_id=recon.stall_ids[0],
        service_date=day,
        kind=AnomalyKind.UNASSIGNED_OCCUPIED,
    )
    async with tenant_session(recon.market_id) as session:
        await open_cases(
            session,
            market_id=recon.market_id,
            business_date=day,
            cutoff=overdue_cutoff(day, _OVERDUE_DAYS),
        )

    row = sync_owner_conn.execute(
        "SELECT id FROM reconciliation_cases WHERE market_id = %s", (str(recon.market_id),)
    ).fetchone()
    assert row is not None, "nazorat: case ochilmadi"
    case_id = UUID(str(row[0]))

    async with tenant_session(recon.market_id) as session:
        evidence = await case_evidence(session, market_id=recon.market_id, case_id=case_id)

    assert evidence.case_id == case_id
    assert evidence.subject_kind == ReconciliationSubjectKind.ANOMALY.value
    assert len(evidence.snapshot_ids) == 1, f"dalil ko'rsatkichi topilmadi: {evidence}"
    assert all(isinstance(item, UUID) for item in evidence.snapshot_ids), (
        f"javobda `UUID` dan boshqa qiymat bor: {evidence.snapshot_ids!r}"
    )


async def test_case_evidence_on_a_missing_case_is_a_lookup_error(
    tenant_session: TenantSessionFactory,
    recon: Env,
) -> None:
    """Topilmagan case bo'sh dalil bilan ADASHTIRILMAYDI."""
    async with tenant_session(recon.market_id) as session:
        with pytest.raises(LookupError):
            await case_evidence(session, market_id=recon.market_id, case_id=uuid4())


# ===========================================================================
# 7. JOB DARAJASI — `active_market_ids()` BO'YLAB, YURAK URISHI BILAN
# ===========================================================================


def _overdue_unpaid_charge(
    conn: Connection[TupleRow],
    *,
    rows: MarketBillingRows,
    stall_id: UUID,
    service_date: date,
    amount_soum: int = TARIFF_SOUM,
) -> UUID:
    """To'lovsiz, chegaradan o'tgan hisob — SINF A ning minimal kirishi."""
    charge_id, _ = add_daily_charge(
        conn,
        market_id=rows.market_id,
        stall_id=stall_id,
        vendor_id=rows.vendor_id,
        tariff_id=rows.tariff_id,
        service_date=service_date,
        amount_soum=amount_soum,
    )
    return charge_id


async def test_job_opens_cases_in_every_active_market(
    sync_owner_conn: Connection[TupleRow],
    app_sessionmaker: async_sessionmaker[AsyncSession],
    recon: Env,
) -> None:
    """⛔ JOB `active_market_ids()` BO'YLAB YURADI — bitta bozor bilan cheklanmaydi.

    Bir bozorli seed bilan yozilgan test bu da'voni HECH QACHON
    o'lchamasdi: tsikl birinchi elementdan keyin `break` qilganda ham
    yashil qolardi (Pitfall 10 ning aynan sinfi).
    """
    today = _days_ago(sync_owner_conn, 0)
    overdue_day = _days_ago(sync_owner_conn, _OVERDUE_DAYS + 1)
    _overdue_unpaid_charge(
        sync_owner_conn,
        rows=recon.billing.market_a,
        stall_id=recon.domain.market_a.stall_ids[0],
        service_date=overdue_day,
    )
    _overdue_unpaid_charge(
        sync_owner_conn,
        rows=recon.billing.market_b,
        stall_id=recon.domain.market_b.stall_ids[0],
        service_date=overdue_day,
    )

    result = await reconciliation_open(app_sessionmaker, business_date=today)

    # ⚠ `>= 2`, `== 2` EMAS — `test_retention.py:657` da o'rnatilgan qoida:
    #   `active_market_ids()` BUTUN bazadagi faol bozorlarni qaytaradi va
    #   qo'shni test fayli (masalan wizard oqimi) o'z bozorini qoldirishi
    #   mumkin. Aniq songa qadalgan da'vo BEGONA faylning tartibiga
    #   bog'lanib qolardi. Haqiqiy da'vo pastda: IKKALA seed bozorida ham
    #   case bor.
    assert result.markets >= 2, f"job ikkala faol bozorni ham ko'rishi kerak edi: {result}"
    assert result.errors == []
    assert result.unpaid_cases == 2, f"ikkala bozorda ham case ochilmadi: {result}"
    for market_id in recon.market_ids:
        assert _case_count(sync_owner_conn, market_id) == 1, (
            f"{market_id}: case ochilmadi — job bu bozorga umuman yetib bormadi"
        )


async def test_one_broken_market_does_not_stop_the_others(
    sync_owner_conn: Connection[TupleRow],
    app_sessionmaker: async_sessionmaker[AsyncSession],
    recon: Env,
) -> None:
    """⛔ BITTA BOZORNING NUQSONI QOLGANLARINI TO'XTATMAYDI (mahsulot qoidasi #5).

    =======================================================================
    ⛔ NOSOZLIK SOXTA EMAS, HAQIQIY MA'LUMOT HOLATI. B bozorining bir
       hisobiga hisobning O'ZIDAN KATTA `decrease` tuzatishi yoziladi,
       ya'ni o'sha kunning qoldig'i MANFIY bo'ladi.
       `allocate_charge_credit()` uni `ValueError` bilan rad etadi va
       uning O'Z docstringi bu holatni «D-07 ning o'z savoli, taqsimlash
       qoidasiniki emas» deb ATAYIN nomlab qo'ygan — ya'ni bu erishib
       bo'ladigan, hujjatlashtirilgan holat.

    ⚠ REJADAGI MISOL («sozlamada `overdue_days` yo'q») BU YERDA
      ISHLATIB BO'LMAYDI va sabab mexanik: sozlama qatorining yo'qligi
      XATO EMAS — `_MARKET_OVERDUE_DAYS` `COALESCE` bilan kod
      standartiga tushadi va job muvaffaqiyatli yakunlanadi. O'sha misol
      bilan yozilgan test `errors == 1` ni HECH QACHON ko'rmasdi.

    ⚠ IKKINCHI HISOB MAJBURIY: yolg'iz manfiy hisob bilan sotuvchining
      umumiy qoldig'i ham manfiy bo'lardi va u qarzdorlar ro'yxatiga
      UMUMAN kirmasdi — ya'ni taqsimlash chaqirilmasdi va nosozlik
      TUG'ILMASDI.
    =======================================================================
    """
    today = _days_ago(sync_owner_conn, 0)
    overdue_day = _days_ago(sync_owner_conn, _OVERDUE_DAYS + 1)

    _overdue_unpaid_charge(
        sync_owner_conn,
        rows=recon.billing.market_a,
        stall_id=recon.domain.market_a.stall_ids[0],
        service_date=overdue_day,
    )

    broken_charge_id = _overdue_unpaid_charge(
        sync_owner_conn,
        rows=recon.billing.market_b,
        stall_id=recon.domain.market_b.stall_ids[0],
        service_date=overdue_day,
    )
    _overdue_unpaid_charge(
        sync_owner_conn,
        rows=recon.billing.market_b,
        stall_id=recon.domain.market_b.stall_ids[1],
        service_date=overdue_day,
    )
    sync_owner_conn.execute(_SET_MARKET_GUC, (str(recon.billing.market_b.market_id),))
    try:
        sync_owner_conn.execute(
            _INSERT_ADJUSTMENT,
            (
                str(uuid4()),
                str(recon.billing.market_b.market_id),
                str(broken_charge_id),
                AdjustmentDirection.DECREASE.value,
                AdjustmentReason.DIRECTOR_WAIVER.value,
                TARIFF_SOUM + 5_000,
                None,
            ),
        )
    finally:
        sync_owner_conn.execute(_SET_MARKET_GUC, ("",))

    result = await reconciliation_open(app_sessionmaker, business_date=today)

    # ⚠ `>= 2` — sabab qo'shni testdagi bilan aynan bir xil. Bu yerdagi
    #   YUKNI KO'TARADIGAN da'vo `errors` ning UZUNLIGI: aynan BITTA bozor
    #   yiqildi va tsikl to'xtamadi.
    assert result.markets >= 2, f"job ikkala bozorni ham ko'rishi kerak edi: {result}"
    assert len(result.errors) == 1, f"aynan bitta bozor xato berishi kerak edi: {result}"
    assert result.errors[0].startswith("reconciliation_open_failed:"), (
        f"xato SANOQQA aylanmadi: {result.errors!r}"
    )
    assert ":ValueError" in result.errors[0], (
        f"xatoning TURI yozilmadi: {result.errors!r} — matn yozilsa u sotuvchi "
        "telefonini yoki ombor manzilini tashishi mumkin edi (T-04-59)."
    )
    assert _case_count(sync_owner_conn, recon.billing.market_a.market_id) == 1, (
        "sog'lom bozorning navbati B bozorining nuqsoni tufayli bo'sh qoldi"
    )
    assert _case_count(sync_owner_conn, recon.billing.market_b.market_id) == 0


async def test_job_writes_its_heartbeat_even_with_errors(
    sync_owner_conn: Connection[TupleRow],
    app_sessionmaker: async_sessionmaker[AsyncSession],
    recon: Env,
) -> None:
    """⛔ YURAK URISHI XATOLAR BO'LGANDA HAM YOZILADI — job ISHLADI.

    Yugurishning YO'QLIGI («cron o'lmadimi?») va yugurishning QISMAN
    muvaffaqiyati IKKI BOSHQA savol. Ularni bitta signalga siqish
    `/internal/self-check` ni bir bozorning nuqsoni tufayli butun cron
    o'lgandek ko'rsatardi.
    """
    before = sync_owner_conn.execute(_HEARTBEAT, (RECON_OPEN_COMPONENT,)).fetchone()
    seen_before = None if before is None else before[0]

    today = _days_ago(sync_owner_conn, 0)
    result = await reconciliation_open(app_sessionmaker, business_date=today)

    row = sync_owner_conn.execute(_HEARTBEAT, (RECON_OPEN_COMPONENT,)).fetchone()
    assert row is not None, "`reconciliation_open` yurak urishini YOZMADI"
    assert row[0] is not None, "`last_seen_at` bo'sh qoldi"
    if seen_before is not None:
        assert row[0] >= seen_before, "`last_seen_at` yangilanmadi"

    detail: dict[str, Any] = row[1]
    assert detail, "yurak urishi BO'SH `detail` bilan yozildi"
    assert all(isinstance(value, int) for value in detail.values()), (
        f"`detail` da sanoq bo'lmagan qiymat bor: {detail}. `market_id`, "
        "sotuvchi yoki rasta kodi GLOBAL jadvalga tushsa u hamma uchun "
        "ko'rinadigan joyda qolardi."
    )
    assert {"anomaly_cases", "unpaid_cases", "errors"} <= set(detail), (
        f"ikkala sinfning sanog'i ham va xato soni ham `detail` da bo'lishi kerak: {sorted(detail)}"
    )
    assert detail["markets"] == result.markets


async def test_job_reads_the_overdue_threshold_from_market_settings(
    sync_owner_conn: Connection[TupleRow],
    app_sessionmaker: async_sessionmaker[AsyncSession],
    recon: Env,
) -> None:
    """⛔ CHEGARA BOZOR SOZLAMASIDAN — global konstanta EMAS (D-19).

    A bozorida chegara KENGAYTIRILADI (`overdue_days = 30`), B bozorida
    sozlama qatori UMUMAN yo'q va u kod standartiga tushadi. Bir xil
    yoshdagi hisob ikki bozorda IKKI XIL javob olishi kerak — aks holda
    «yangi bozor kod yozmasdan ulanadi» va'dasi buzilardi.
    """
    today = _days_ago(sync_owner_conn, 0)
    charge_day = _days_ago(sync_owner_conn, DEFAULT_OVERDUE_DAYS + 1)
    assert DEFAULT_OVERDUE_DAYS < 30, (
        "NAZORAT: kengaytirilgan chegara kod standartidan katta bo'lishi shart — "
        "aks holda ikki bozor bir xil javob berardi va test hech nimani o'lchamasdi."
    )

    seed_notification_settings(
        sync_owner_conn, market_id=recon.billing.market_a.market_id, overdue_days=30
    )
    _overdue_unpaid_charge(
        sync_owner_conn,
        rows=recon.billing.market_a,
        stall_id=recon.domain.market_a.stall_ids[0],
        service_date=charge_day,
    )
    _overdue_unpaid_charge(
        sync_owner_conn,
        rows=recon.billing.market_b,
        stall_id=recon.domain.market_b.stall_ids[0],
        service_date=charge_day,
    )

    result = await reconciliation_open(app_sessionmaker, business_date=today)

    assert result.errors == []
    assert _case_count(sync_owner_conn, recon.billing.market_a.market_id) == 0, (
        "kengaytirilgan chegara (30 kun) hisobni baribir navbatga qo'ydi — "
        "job bozor sozlamasini o'qimayapti"
    )
    assert _case_count(sync_owner_conn, recon.billing.market_b.market_id) == 1, (
        "sozlamasiz bozor kod standartiga tushmadi (`COALESCE` shoxi)"
    )
    assert result.unpaid_cases == 1


async def test_component_name_matches_the_heartbeat_contract() -> None:
    """⛔ KOMPONENT NOMI SATRI — 07-14 uni AYNAN shu qiymat bilan ro'yxatga oladi.

    Nom ayrilsa `/internal/self-check` komponentni MANGU `never_seen` da
    ko'rsatardi: xato yo'q, jurnal yozuvi yo'q, faqat sukunat.
    """
    assert RECON_OPEN_COMPONENT == "reconciliation_open"
