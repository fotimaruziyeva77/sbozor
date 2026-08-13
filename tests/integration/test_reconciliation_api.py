"""`/api/v1/reconciliation/*` — RECON-01 va RECON-02 ning HTTP kontrakti.

=============================================================================
⛔⛔ BU FAYLNING ENG QIMMAT DA'VOSI — **DALILNING BAYT EMASLIGI**.

RECON-01 «rasm-dalil **havolalari** bilan» deydi va o'sha so'z ikki xil
o'qilishi mumkin edi: (a) javobda IMZOLANGAN URL, (b) javobda
IDENTIFIKATOR. D-03 / T-06-81 ikkinchisini tanlagan va bu fayl tanlovni
XULQ bilan qulflaydi: javob tanasida `evidence_snapshot_ids` BOR va
`presigned` / `http` / `image` satrlari YO'Q.

⚠ NEGA BU DARVOZA `test_personal_data_coverage.py` DAN AJRALIB TURADI:
  o'sha fayl SXEMANI o'lchaydi (maydon nomlari, javob modeli), bu esa
  HAQIQIY JAVOB TANASINI. Ikkalasi ham kerak — handler `dict` qaytarib
  sxemani chetlab o'tsa birinchisi sezmasdi, model o'zgarsa-yu shu
  stsenariy ochilmasa ikkinchisi sezmasdi (05-14 ning darsi).

=============================================================================
⛔ BU FAYL `test_reconciliation_repo.py` NI TAKRORLAMAYDI.

Case arifmetikasi (ikki sinfning ochilishi, idempotentlik, hit-rate
maxraji, keyset kesishmasligi) o'sha yerda, HAQIQIY bazada, 24 darvoza
bilan o'lchangan. Bu yerda faqat HTTP CHEGARASIDAGI da'volar:

  1. javob TANASI — dalil identifikator, shaxsiy maydon YO'Q;
  2. HUQUQ — kassir/nazoratchi 403; bozor admini o'qiydi, lekin HUKM
     CHIQARMAYDI (`DISPUTE_DECIDE` faqat direktorda);
  3. YOPIQ RO'YXAT HTTP chegarasida ham yopiq (`"other"` -> 422);
  4. IKKI JURNAL — `reconciliation_case_events` VA `audit_log`;
  5. CROSS-TENANT — begona case 404, 403 EMAS;
  6. standart kun KECHA va oraliq chegarasi 422.
=============================================================================
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import pytest
from app.jobs.reconciliation import reconciliation_open
from fixtures.admin_api import session_headers
from fixtures.billing_domain import (
    BillingDomainSeed,
    add_charge_evidence,
    add_daily_charge,
    billing_domain,
)
from fixtures.market_domain import MarketDomainSeed
from fixtures.notification_domain import (
    cleanup_notification_domain,
    seed_case,
    seed_outbox_row,
)
from fixtures.nvr_domain import nvr_rows
from fixtures.occupancy_domain import occupancy_rows
from fixtures.snapshot_domain import snapshot_rows
from fixtures.two_markets import SEED_PASSWORD, TwoMarketSeed
from sbozor_core.enums import AnomalyKind, ReconciliationCaseStatus
from sbozor_core.timeutil import business_today
from sqlalchemy import text

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator
    from datetime import date

    import httpx
    from fixtures import TenantSessionFactory
    from psycopg import Connection
    from psycopg.rows import TupleRow
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

REPORT_URL = "/api/v1/reconciliation/report"
CASES_URL = "/api/v1/reconciliation/cases"
HIT_RATE_URL = "/api/v1/reconciliation/hit-rate"
DELIVERY_URL = "/api/v1/reconciliation/delivery"
"""⛔ FAQAT KURSOR DEKODERI UCHUN — yuzaning O'ZI `test_delivery_surface.py` da.

Ikki dekoder (`_decode_cursor` / `_decode_delivery_cursor`) BIR fayldagi
BIR sinf nuqsonni ko'taradi, ya'ni ularning testlari ham yonma-yon
turishi kerak: bittasini tuzatib ikkinchisini unutish aynan shu yerda
ko'zga tashlanadi.
"""

PERSONAL_FIELDS = frozenset({"vendor_name", "phone", "full_name"})
"""C-10 darvozasining maydonlari — `test_personal_data_coverage.py:59` bilan AYNI.

⚠ NUSXA ONGLI (`test_billing_api.py` da o'rnatilgan qoida): o'sha faylni
  import qilish tenancy paketini integratsiya to'plamiga bog'lardi.
  Nomlar `PERSONAL_ROUTES` darvozasi tomonidan ALLAQACHON mustaqil
  qo'riqlanadi, ya'ni ikki ro'yxat ajralib ketsa o'sha darvoza qizaradi.
"""

FORBIDDEN_EVIDENCE_MARKERS = ("presigned", "http", "image")
"""⛔ JAVOB TANASIDA BO'LMAYDIGAN satrlar — D-03 ning XULQ darajasidagi o'lchovi.

`presigned` — imzolangan havolaning nomi; `http` — har qanday URL ning
boshi; `image` — kadr marshrutining nomi. Uchalasi ham javobda paydo
bo'lishi «dalil-kadr yuzasi kengaydi» degan BIRINCHI belgi bo'lardi va
u aynan «qulaylik uchun» qo'shilgan bitta maydondan boshlanardi
(`CaseEvidence` klass docstringi).
"""

_INSERT_EVIDENCED_ANOMALY = (
    "INSERT INTO billing_anomalies "
    "(id, market_id, kind, stall_id, service_date, occupancy_event_id, snapshot_id) "
    "VALUES (%s, %s, %s, %s, %s, %s, %s)"
)
"""DALILLI anomaliya — case OCHILADIGAN sinf hodisa VA kadrni TALAB QILADI.

`billing_anomalies` da ikki juftlangan `CHECK` bor:

    (kind = 'no_coverage_stall') = (occupancy_event_id IS NULL)
    (occupancy_event_id IS NULL) = (snapshot_id IS NULL)

ya'ni `fixtures/notification_domain.py::seed_no_coverage_anomaly` ATAYIN
faqat DALILSIZ sinfni yozadi va undan case OCHILMAYDI (Pattern 4).

⚠ XOM SQL SHU MODULDA, `fixtures/` DA EMAS: reja bu rejaning
  `files_modified` ini cheklaydi va 07-07 aynan shu qarorni AYNI sabab
  bilan qabul qilgan (07-07 SUMMARY, Rule 3 / 2-band). Umumiy seed'ga
  ko'chirish 07-04 SUMMARY ning 4-ochiq bandidagi ish.
"""

_EVIDENCE_PAIR = (
    "SELECT e.id, e.snapshot_id FROM occupancy_events e "
    "WHERE e.market_id = %s AND e.snapshot_id IS NOT NULL ORDER BY e.id LIMIT 1"
)
"""Hodisa + kadr juftligi — ZANJIR BAZADAN olinadi, qayta QURILMAYDI."""

_COUNT_EVENTS = (
    "SELECT count(*) FROM reconciliation_case_events WHERE market_id = %s AND case_id = %s"
)

_CASE_ROW = (
    "SELECT status, assignee_user_id FROM reconciliation_cases WHERE market_id = %s AND id = %s"
)
"""Case'ning BAZADAGI holati — javobga emas, YOZILGAN qatorga qaraydi.

⛔ FAQAT JAVOBGA QARASH YETMAYDI: marshrut qiymatni javob modeliga
   qo'yib, bazaga yozmagan holat o'shanda YASHIL qolardi (05-14 darsi).
"""

_MEMBER_ROLES = "SELECT roles FROM user_market_roles WHERE market_id = %s AND user_id = %s"
"""A'zolik NAZORATI — «begona bozor xodimi» testining eng muhim qismi.

⛔ USIZ TENANCY DARVOZASI BO'SH-ROST BO'LARDI: tasodifiy UUID bilan
   yozilgan test «mavjud bo'lmagan foydalanuvchi rad etildi» ni
   o'lchardi va `member_roles()` tekshiruvi olib tashlanganda ham
   yashil qolardi.
"""


# ===========================================================================
# Fixture'lar — `test_reconciliation_repo.py::env` naqshi
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
    def market_ids(self) -> tuple[UUID, ...]:
        return self.billing.market_ids


@pytest.fixture
async def env(
    sync_owner_conn: Connection[TupleRow],
    app_sessionmaker: async_sessionmaker[AsyncSession],
    two_markets: TwoMarketSeed,
    market_domain: MarketDomainSeed,
    migrated: None,
) -> AsyncIterator[Env]:
    """`day_close` YUGURGAN seed — ⛔ `stall_slot_occupancy` TO'LGAN.

    =========================================================================
    ⛔ `billing_domain_before_day_close` YETMAYDI VA BU O'LCHANGAN.

    Sinf A ning dalili (`charge_evidence`) `stall_slot_occupancy` ga
    KOMPOZIT FK bilan tayanadi, o'sha jadvalning YAGONA yozuvchisi esa
    `occupancy_repo.materialize()` — ya'ni `day_close`. Slotlarsiz
    `add_charge_evidence()` `None` qaytaradi va bu faylning eng qimmat
    da'vosi (`evidence_snapshot_ids` BO'SH EMAS) o'lchanmasdi.

    ⛔ QO'LDA `INSERT` YOZILMAYDI: u arzonroq bo'lardi va aynan o'sha
       arzonlik C-3 sinfidagi xatoni testdan YASHIRARDI
       (`fixtures/billing_domain.py` modul docstringining birinchi
       bandi).
    =========================================================================

    ⚠ `day_close` `SEED_BUSINESS_DATE` (kelajakdagi qat'iy sana) uchun
      yuguradi, bu faylning case'lari esa KECHAGI kunda. Ular
      TO'QNASHMAYDI: `add_charge_evidence()` bozorning ISTALGAN slot
      qatorini oladi (`ORDER BY s.id LIMIT 1`) va dalil zanjirining
      sana bo'yicha bog'lanishi YO'Q — `test_billing_immutable.py:852`
      da o'rnatilgan qoida.
    """
    with (
        nvr_rows(sync_owner_conn, two_markets) as nvr,
        snapshot_rows(sync_owner_conn, nvr) as snaps,
        occupancy_rows(sync_owner_conn, two_markets, market_domain, snaps) as occupancy,
    ):
        async with billing_domain(
            sync_owner_conn, app_sessionmaker, two_markets, market_domain, occupancy
        ) as billing:
            yield Env(billing, market_domain, two_markets)


@pytest.fixture
def recon(sync_owner_conn: Connection[TupleRow], env: Env) -> Iterator[Env]:
    """`env` USTIGA case jadvallarining tozalanishi.

    ⚠ `env` ARGUMENT sifatida olinadi, faqat «oldin ishlasin» uchun emas:
      pytest fixture'larni TESKARI tartibda yopadi, ya'ni case'lar
      billing qatorlaridan OLDIN o'chadi. Teskari holatda
      `cleanup_billing_domain()` ning `DELETE FROM billing_anomalies` i
      hali havola qilib turgan case tufayli FK buzilishi bilan yiqilardi
      (`fk_reconciliation_cases_anomaly` da `ondelete` YO'Q).
    """
    try:
        yield env
    finally:
        cleanup_notification_domain(sync_owner_conn, market_ids=list(env.market_ids))


@pytest.fixture
async def director_headers(api_client: httpx.AsyncClient, recon: Env) -> dict[str, str]:
    """DIREKTOR sessiyasi — unda `report_view` VA ⛔ `dispute_decide` bor (§5.6)."""
    return await session_headers(api_client, recon.base.market_a.director_phone, SEED_PASSWORD)


@pytest.fixture
async def admin_headers(api_client: httpx.AsyncClient, recon: Env) -> dict[str, str]:
    """BOZOR ADMINI sessiyasi — `report_view` BOR, ⛔ `dispute_decide` YO'Q."""
    market_a = recon.base.market_a
    return await session_headers(api_client, market_a.admin_phone, market_a.admin_password)


@pytest.fixture
async def cashier_headers(api_client: httpx.AsyncClient, recon: Env) -> dict[str, str]:
    """KASSIR sessiyasi — ⛔ unda `report_view` YO'Q (UI-SPEC §5.6)."""
    return await session_headers(api_client, recon.base.market_a.cashier_phone, SEED_PASSWORD)


# ===========================================================================
# Yordamchilar
# ===========================================================================


def _report_day() -> date:
    """Marshrutning STANDART kuni — ⛔ `business_today()` NING AYNAN JUFTI.

    ⛔ `date.today()` YOKI DB `CURRENT_DATE` ISHLATILMAYDI: marshrut kunni
       `sbozor_core.timeutil.business_today()` (Asia/Tashkent) bilan
       hisoblaydi, konteynerlar esa UTC da yuguradi. Ikki manba
       Toshkent yarim tunidan keyingi besh soatda BIR KUN farq qilardi
       va seed marshrut qaraydigan kundan boshqa kunga tushardi — test
       FLAKY bo'lardi va sabab kodda emas, SOATDA bo'lardi.

    ⚠ `daily_charges` ning `service_date <= business_date` `CHECK` i
      baribir bajariladi: Toshkent sanasi UTC sanasidan ko'pi bilan
      BIR KUN oldinda, ya'ni `business_today() - 1` har doim
      `CURRENT_DATE` dan katta emas.
    """
    return business_today() - timedelta(days=1)


def _seed_unpaid_charge(conn: Connection[TupleRow], env: Env, *, day: date) -> tuple[UUID, UUID]:
    """SINF A — «band, lekin to'lovsiz»: hisob YOZILGAN, to'lov YO'Q.

    ⛔ TO'LOV ATAYIN YOZILMAYDI: sinfning butun ma'nosi shunda. Hisobning
       dalili (`charge_evidence`) esa YOZILADI — usiz hisobot qatori
       dalil identifikatorisiz kelardi va faylning eng qimmat da'vosi
       (`evidence_snapshot_ids` bo'sh EMAS) o'lchanmasdi.

    Returns:
        `(charge_id, case_id)`.
    """
    charge_id, _ = add_daily_charge(
        conn,
        market_id=env.market_id,
        stall_id=env.stall_ids[0],
        vendor_id=env.vendor_id,
        tariff_id=env.tariff_id,
        service_date=day,
    )
    evidence_id = add_charge_evidence(conn, market_id=env.market_id, charge_id=charge_id)
    assert evidence_id is not None, (
        "nazorat: bozorda g'olib hodisali slot qatori yo'q — hisobning dalili "
        "yozilmadi va `evidence_snapshot_ids` da'vosi BO'SH-ROST bo'lardi"
    )
    case_id = seed_case(conn, market_id=env.market_id, service_date=day, charge_id=charge_id)
    return charge_id, case_id


def _seed_unregistered_anomaly(
    conn: Connection[TupleRow],
    env: Env,
    *,
    day: date,
    stall_index: int = 1,
    kind: AnomalyKind = AnomalyKind.UNASSIGNED_OCCUPIED,
) -> tuple[UUID, UUID]:
    """SINF B — «ro'yxatga olinmagan savdo»: hisob UMUMAN yozilmagan.

    ⚠ `stall_index` VA `kind` ARGUMENT: `uq_billing_anomalies_market_stall_
      service_date_kind` bitta rastaga bir kunda bitta turdagi anomaliyani
      ruxsat etadi, ya'ni bir nechta case kerak bo'lganda ular BOSHQA
      rasta yoki BOSHQA turdan kelishi shart. Standart qiymatlar bitta
      case yetadigan testlarni qisqa saqlaydi.

    Returns:
        `(anomaly_id, case_id)`.
    """
    anomaly_id = _seed_evidenced_anomaly(conn, env, day=day, stall_index=stall_index, kind=kind)
    case_id = seed_case(conn, market_id=env.market_id, service_date=day, anomaly_id=anomaly_id)
    return anomaly_id, case_id


def _seed_evidenced_anomaly(
    conn: Connection[TupleRow],
    env: Env,
    *,
    day: date,
    stall_index: int = 1,
    kind: AnomalyKind = AnomalyKind.UNASSIGNED_OCCUPIED,
) -> UUID:
    """Anomaliya qatori — ⛔ CASE'SIZ. `recon.open` uni O'ZI ochadi.

    ⛔ `_seed_unregistered_anomaly()` DAN AJRATILDI VA BU ZARURIYAT:
       o'sha yordamchi case'ni QO'LDA (`seed_case`) yozadi, ya'ni case
       MAHSULOT yo'lidan tug'ilmaydi va TUG'ILISH hodisasi ham
       yozilmaydi. «Har case tug'ilganda tarixga qator tushadi» da'vosini
       o'lchash uchun case'ni ⛔ JOB ochishi SHART.
    """
    row = conn.execute(_EVIDENCE_PAIR, (str(env.market_id),)).fetchone()
    assert row is not None, f"nazorat: {env.market_id} da kadrli bandlik hodisasi yo'q"
    event_id, snapshot_id = row

    anomaly_id = uuid4()
    conn.execute(
        _INSERT_EVIDENCED_ANOMALY,
        (
            str(anomaly_id),
            str(env.market_id),
            kind.value,
            str(env.stall_ids[stall_index]),
            day,
            str(event_id),
            str(snapshot_id),
        ),
    )
    return anomaly_id


def _keys_at_every_depth(payload: Any) -> set[str]:
    """Javob JSON'idagi BARCHA kalitlar — ⛔ REKURSIV.

    ⛔ FAQAT YUQORI DARAJAGA QARASH YETMAYDI: shaxsiy maydon deyarli hech
       qachon ildizda turmaydi — u `rows[].vendor_name` bo'lib IKKI qavat
       pastda yashaydi (`test_personal_data_coverage.response_field_names`
       ning aynan sababi va CR-02 ning o'lchangan holati).
    """
    found: set[str] = set()
    if isinstance(payload, dict):
        for key, value in payload.items():
            found.add(str(key))
            found |= _keys_at_every_depth(value)
    elif isinstance(payload, list):
        for item in payload:
            found |= _keys_at_every_depth(item)
    return found


async def _case_audit_count(tenant_session: TenantSessionFactory, market_id: UUID) -> int:
    """`reconciliation_cases` ustidagi audit qatorlari — ⛔ ILOVA roli bilan.

    ⛔ `sync_owner_conn` BILAN O'QILMAYDI: `audit_read` policy'si
       `sbozor_app` ga va TENANT KONTEKSTIGA bog'langan, ega roli esa
       `audit_log` da hech nima ko'rmaydi. Ega bilan yozilgan sanoq HAR
       DOIM 0 berardi va «audit yozildi» da'vosi jimgina BO'SH-ROST
       bo'lib qolardi (07-08 buni bir marta TO'LAGAN).
    """
    async with tenant_session(market_id) as session:
        found = await session.execute(
            text(
                "SELECT count(*) FROM audit_log "
                "WHERE market_id = :market_id AND table_name = :table_name"
            ),
            {"market_id": market_id, "table_name": "reconciliation_cases"},
        )
        return int(found.scalar_one())


# ===========================================================================
# 1. HISOBOT — IKKI SINF, DALIL IDENTIFIKATOR, SHAXSIY MAYDON YO'Q
# ===========================================================================


async def test_report_shows_both_classes(
    api_client: httpx.AsyncClient,
    sync_owner_conn: Connection[TupleRow],
    recon: Env,
    director_headers: dict[str, str],
) -> None:
    """⛔ RECON-01: hisobot IKKALA sinfni ham ko'rsatadi va ularni AJRATADI.

    =======================================================================
    ⛔⛔ IKKI SANOQ HECH QACHON QO'SHILMAYDI (D-05 ning aynan takrori).

    «Band, lekin to'lovsiz» — pul KELMADI. «Ro'yxatga olinmagan savdo» —
    savdo UMUMAN yozilmadi. Ikkisini bitta «nomuvofiqlik soni» ga
    qo'shish direktorga bitta son ko'rsatardi va u ikki BOSHQA harakat
    (to'lovni undirish / rastani biriktirish) o'rniga bittasini
    tanlardi.
    =======================================================================
    """
    day = _report_day()
    _seed_unpaid_charge(sync_owner_conn, recon, day=day)
    _seed_unregistered_anomaly(sync_owner_conn, recon, day=day)

    response = await api_client.get(REPORT_URL, headers=director_headers)

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["day"] == day.isoformat()
    assert payload["unpaid_count"] == 1, payload
    assert payload["unregistered_count"] == 1, payload
    assert {row["subject_kind"] for row in payload["rows"]} == {"occupied_unpaid", "anomaly"}

    unpaid = next(row for row in payload["rows"] if row["subject_kind"] == "occupied_unpaid")
    unregistered = next(row for row in payload["rows"] if row["subject_kind"] == "anomaly")
    assert unpaid["expected_soum"] is not None and unpaid["expected_soum"] > 0
    assert payload["unpaid_expected_soum"] == unpaid["expected_soum"]
    # ⛔ SINF B DA KUTILGAN SUMMA `null` VA BU JAVOB, NOL EMAS: hisob
    #    yozilmagan, ya'ni «qancha kutilishini tizim BILMAYDI». Nol
    #    yozish «bu savdodan hech nima kutilmagan» degan YOLG'ON da'vo
    #    bo'lardi va u yig'indini ham buzardi.
    assert unregistered["expected_soum"] is None, unregistered
    assert unregistered["vendor_id"] is None, unregistered


async def test_report_carries_evidence_ids_but_no_bytes(
    api_client: httpx.AsyncClient,
    sync_owner_conn: Connection[TupleRow],
    recon: Env,
    director_headers: dict[str, str],
) -> None:
    """⛔ RECON-01 NING ENG MUHIM O'LCHOVI — dalil HAVOLA, BAYT emas (D-03).

    Uch da'vo BIRGA: identifikator BOR, u `UUID` shaklida, va javob
    tanasida imzolangan havolaning birorta izi YO'Q. Faqat birinchisi
    bo'lsa «qulaylik uchun» qo'shilgan `image_url` maydoni darvozadan
    o'tib ketardi (T-06-81 ning aynan boshlanish nuqtasi).
    """
    day = _report_day()
    _seed_unpaid_charge(sync_owner_conn, recon, day=day)
    _seed_unregistered_anomaly(sync_owner_conn, recon, day=day)

    response = await api_client.get(REPORT_URL, headers=director_headers)

    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("application/json")

    payload = response.json()
    for row in payload["rows"]:
        assert row["evidence_snapshot_ids"], (
            f"{row['subject_kind']} qatori dalilsiz keldi — seed buzilgan bo'lsa "
            "bu da'vo BO'SH-ROST bo'lardi"
        )
        for snapshot_id in row["evidence_snapshot_ids"]:
            UUID(snapshot_id)

    body = response.text.lower()
    leaked = [marker for marker in FORBIDDEN_EVIDENCE_MARKERS if marker in body]
    assert leaked == [], (
        f"javob tanasida dalil-kadr yuzasining izi bor: {leaked}. Javobda FAQAT "
        "`snapshot_id` bo'ladi; kadr MAVJUD `GET /api/v1/snapshots/{id}/image` "
        "dan olinadi va o'sha marshrut `audit_read` yozadi (D-03, T-06-81)"
    )


async def test_report_has_no_personal_field(
    api_client: httpx.AsyncClient,
    sync_owner_conn: Connection[TupleRow],
    recon: Env,
    director_headers: dict[str, str],
) -> None:
    """⛔ G7-6: javob JSON'ining HECH BIR chuqurligida shaxsiy maydon YO'Q.

    ⚠ REKURSIV SKAN MAJBURIY (`_keys_at_every_depth` docstringi): CR-02
      o'lchagan holatda `vendor_name` ildizda emas, `rows[]` ichida
      yashardi.

    ⚠ NAZORAT ASSERTI: `vendor_id` javobda BOR. Usiz test «javob bo'sh»
      holatida ham yashil bo'lardi — ya'ni u shaxsiy maydonning yo'qligini
      emas, MA'LUMOTNING yo'qligini o'lchardi (05-15 ning S-D darsi).
    """
    day = _report_day()
    _seed_unpaid_charge(sync_owner_conn, recon, day=day)

    response = await api_client.get(REPORT_URL, headers=director_headers)

    assert response.status_code == 200, response.text
    keys = _keys_at_every_depth(response.json())

    assert "vendor_id" in keys, "nazorat: javobda `vendor_id` yo'q — skan bo'sh to'plamda ishladi"
    assert keys & PERSONAL_FIELDS == set(), sorted(keys & PERSONAL_FIELDS)


async def test_report_day_defaults_to_yesterday(
    api_client: httpx.AsyncClient,
    recon: Env,
    director_headers: dict[str, str],
) -> None:
    """⛔ STANDART KUN — KECHA, va u JAVOBDA qaytadi (§11.1).

    ⛔ BUGUN BO'LSA sahifa HAR DOIM bo'sh ochilardi: `recon.open` KECHAGI
       kunni bugun tekshiradi. To'g'ri ishlayotgan tizim «buzuq» bo'lib
       ko'rinardi.

    ⛔ KELAJAK KUNI **422** — bo'sh ro'yxat EMAS: «kelajakda nomuvofiqlik
       yo'q» degan MA'NOSIZ javob «bu kunda nomuvofiqlik topilmadi»
       bilan bir xil ko'rinardi.
    """
    response = await api_client.get(REPORT_URL, headers=director_headers)

    assert response.status_code == 200, response.text
    assert response.json()["day"] == _report_day().isoformat()
    # ⛔ NOL — NATIJA: bo'sh kunda ham UCHALA hisoblagich qaytadi.
    assert response.json()["unpaid_count"] == 0
    assert response.json()["unregistered_count"] == 0
    assert response.json()["unpaid_expected_soum"] == 0

    future = (business_today() + timedelta(days=1)).isoformat()
    rejected = await api_client.get(REPORT_URL, params={"day": future}, headers=director_headers)

    assert rejected.status_code == 422, rejected.text
    assert rejected.json()["detail"] == "day_in_future"


# ===========================================================================
# 2. HUQUQ — MATRITSA TEGILMAGAN, LEKIN U HTTP DA HAM ISHLAYDI
# ===========================================================================


@pytest.mark.parametrize(
    "url", [REPORT_URL, CASES_URL, HIT_RATE_URL], ids=["report", "cases", "hit-rate"]
)
async def test_the_cashier_cannot_read_the_reconciliation_surface(
    api_client: httpx.AsyncClient,
    recon: Env,
    cashier_headers: dict[str, str],
    url: str,
) -> None:
    """⛔ Kassirda `report_view` YO'Q (UI-SPEC §5.6) — hamma yerda 403.

    Kassir pul YIG'ADI, hisobot O'QIMAYDI. Uni nomuvofiqlik navbatiga
    kiritish «kim qarzdor?» ro'yxatini kassa oldida turgan odamga
    ochardi va bu D-02 ning nizо oqimidan butunlay boshqa yuza bo'lardi.
    """
    response = await api_client.get(url, headers=cashier_headers)

    assert response.status_code == 403, f"{url}: {response.status_code} — {response.text}"


async def test_the_market_admin_reads_but_cannot_decide(
    api_client: httpx.AsyncClient,
    sync_owner_conn: Connection[TupleRow],
    recon: Env,
    admin_headers: dict[str, str],
) -> None:
    """⛔ Bozor admini KO'RADI, lekin HUKM CHIQARMAYDI (`DISPUTE_DECIDE`).

    =======================================================================
    ⛔ IKKI DA'VO BITTA TESTDA VA ULAR AJRALMAS: «o'qiy oladi» yolg'iz
       o'zi `REPORT_VIEW` ning kengligini isbotlaydi, «yoza olmaydi»
       yolg'iz o'zi esa 403 ning sababini noaniq qoldirardi (huquq
       yetishmadimi yoki sessiya buzuqmi?). Birga ular AYNAN bitta
       huquqning chegarasini ko'rsatadi.
    =======================================================================
    """
    day = _report_day()
    _, case_id = _seed_unpaid_charge(sync_owner_conn, recon, day=day)

    readable = await api_client.get(REPORT_URL, headers=admin_headers)
    assert readable.status_code == 200, readable.text

    detail = await api_client.get(f"{CASES_URL}/{case_id}", headers=admin_headers)
    assert detail.status_code == 200, detail.text

    denied = await api_client.patch(
        f"{CASES_URL}/{case_id}",
        json={"status": ReconciliationCaseStatus.IN_REVIEW.value},
        headers=admin_headers,
    )

    assert denied.status_code == 403, denied.text


# ===========================================================================
# 3. YOPIQ RO'YXAT VA IKKI JURNAL (D-12, D-14)
# ===========================================================================


async def test_case_status_is_a_closed_set_over_http(
    api_client: httpx.AsyncClient,
    sync_owner_conn: Connection[TupleRow],
    recon: Env,
    director_headers: dict[str, str],
) -> None:
    """⛔ D-12: `"other"` HTTP chegarasida **422** — u holat bo'lib KIRA OLMAYDI.

    Erkin matnli a'zo hisobotda GURUHLANMAYDI va u AMALDA eng katta guruh
    bo'lib qolardi — o'shanda hit-rate maxraji (D-13) ham ma'nosini
    yo'qotardi. Yechim matni esa `resolution_note` da yashaydi va u
    o'lchanmaydi.
    """
    day = _report_day()
    _, case_id = _seed_unpaid_charge(sync_owner_conn, recon, day=day)

    response = await api_client.patch(
        f"{CASES_URL}/{case_id}", json={"status": "other"}, headers=director_headers
    )

    assert response.status_code == 422, response.text

    # NAZORAT: yopiq ro'yxatning A'ZOSI o'sha yo'ldan O'TADI — aks holda
    # test «PATCH umuman ishlamaydi» holatida ham yashil bo'lardi.
    accepted = await api_client.patch(
        f"{CASES_URL}/{case_id}",
        json={"status": ReconciliationCaseStatus.IN_REVIEW.value},
        headers=director_headers,
    )
    assert accepted.status_code == 200, accepted.text


async def test_case_transition_writes_to_both_journals(
    api_client: httpx.AsyncClient,
    sync_owner_conn: Connection[TupleRow],
    tenant_session: TenantSessionFactory,
    recon: Env,
    director_headers: dict[str, str],
) -> None:
    """⛔ D-14 / T-07-61: bitta o'tish IKKALA jurnalga ham **AYNAN +1** qator yozadi.

    =======================================================================
    ⛔⛔ IKKI JURNAL, IKKI MAQSAD — VA BIRORTASI ORTIQCHA EMAS.

      `reconciliation_case_events` — MAHSULOT tarixi, uni DIREKTOR
          o'qiydi va u javobning `events` maydonida KO'RINADI;
      `audit_log` — XAVFSIZLIK jurnali, uni AUDITOR o'qiydi va uning
          qamrovi butun ilova bo'ylab bir xil bo'lishi shart.

    Birinchisida `from_status -> to_status` ketma-ketligi bor,
    ikkinchisida yo'q; ikkinchisi butun tizimni qamraydi, birinchisi
    faqat case domenini. Ya'ni ularni almashtirib bo'lmaydi.

    ⛔⛔ SANOQ `+1`, `>= 1` EMAS — VA BU FARQ BIR MARTA O'LCHANGAN.

    `audit_log` qatorini ⛔ **DB-TRIGGER** yozadi (`0023` migratsiyasi
    `reconciliation_cases` ni `NOTIFICATION_AUDITED_TABLES` ga qo'shgan).
    Marshrutga qo'shimcha `write_app_audit(...)` qo'yilganda sanoq
    **+2** bo'ldi — ya'ni bitta hodisa xavfsizlik jurnalida IKKI MARTA
    ko'rinardi va «bugun nechta case yopildi?» savoli ikki xil javob
    berardi. `>= 1` bilan yozilgan assert bu dublikatni KO'RMASDI.
    =======================================================================
    """
    day = _report_day()
    _, case_id = _seed_unpaid_charge(sync_owner_conn, recon, day=day)
    audit_before = await _case_audit_count(tenant_session, recon.market_id)

    response = await api_client.patch(
        f"{CASES_URL}/{case_id}",
        json={
            "status": ReconciliationCaseStatus.JUSTIFIED.value,
            "resolution_note": "Sotuvchi kechqurun to'lagan — kvitansiya bor.",
        },
        headers=director_headers,
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["status"] == "justified"
    assert payload["resolution_note"] == "Sotuvchi kechqurun to'lagan — kvitansiya bor."
    assert len(payload["events"]) == 1, payload["events"]
    assert payload["events"][0]["from_status"] == "new"
    assert payload["events"][0]["to_status"] == "justified"
    # ⛔ AKTOR — DIREKTORNING IDENTIFIKATORI, ISMI EMAS (C-10): `None`
    #    bo'lsa u «TIZIM» degani bo'lardi va nizoda hukmni kim
    #    chiqarganini KO'RSATMASDI.
    assert payload["events"][0]["actor_user_id"] == str(recon.base.market_a.director_user_id)

    events = sync_owner_conn.execute(_COUNT_EVENTS, (str(recon.market_id), str(case_id))).fetchone()
    assert events is not None and events[0] == 1, events

    assert await _case_audit_count(tenant_session, recon.market_id) == audit_before + 1


async def test_transition_to_the_same_status_is_a_conflict(
    api_client: httpx.AsyncClient,
    sync_owner_conn: Connection[TupleRow],
    recon: Env,
    director_headers: dict[str, str],
) -> None:
    """⛔ NOL O'TISH -> **409**, va tarixga qator YOZILMAYDI (D-14).

    Nol o'tish tarixni shovqin bilan to'ldirardi: «case necha marta
    qo'ldan qo'lga o'tdi?» savoli noto'g'ri javob berardi. Repo
    `ValueError` beradi, marshrut uni KODGA aylantiradi — sxemaning
    `IntegrityError` i «baza buzuq» kabi ko'rinardi.
    """
    day = _report_day()
    _, case_id = _seed_unpaid_charge(sync_owner_conn, recon, day=day)

    response = await api_client.patch(
        f"{CASES_URL}/{case_id}",
        json={"status": ReconciliationCaseStatus.NEW.value},
        headers=director_headers,
    )

    assert response.status_code == 409, response.text
    assert response.json()["detail"] == "status_unchanged"

    events = sync_owner_conn.execute(_COUNT_EVENTS, (str(recon.market_id), str(case_id))).fetchone()
    assert events is not None and events[0] == 0, events


# ===========================================================================
# 3b. MAS'UL — DIREKTOR TANLAYDI, AKTOR EMAS (RECON-02, B-2)
#
# ⛔⛔ MAS'UL VA AKTOR — IKKI BOSHQA SAVOLNING JAVOBI.
#
#   aktor  (`actor_user_id`)     -> «KIM QAROR QILDI?» — tarix qatorining
#                                   egasi, nizoda (D-02) javob beradigan odam;
#   mas'ul (`assignee_user_id`)  -> «KIM ISH QILADI?» — case'ning joriy egasi.
#
# 07-20 gacha marshrut `payload.assignee_user_id` ni JIMGINA tashlab
# yuborardi va SQL har o'tishda case'ni HUKM CHIQARGAN odamga biriktirardi
# (`COALESCE(:actor_user_id, assignee_user_id)`). Ya'ni RECON-02 ning
# «mas'ul... yoziladi» bandi AMALDA yo'q edi, javob esa `200`.
#
# ⛔ BU BO'LIMNING ENG QIMMAT DA'VOSI — TENANCY: `reconciliation_cases.
#    assignee_user_id` da `users` ga FK ⛔ YO'Q (`0023:344-347` tekshiruvni
#    «ilova qatlamida» deb yozgan), ya'ni yagona to'siq ILOVADA. Maydonni
#    tekshiruvsiz «ulab qo'yish» begona bozor xodimini biriktirish yo'lini
#    ochardi — u maydonni tashlab yuborishdan ham YOMONROQ holat.
# ===========================================================================


async def test_the_director_assigns_the_case_to_a_market_member(
    api_client: httpx.AsyncClient,
    sync_owner_conn: Connection[TupleRow],
    recon: Env,
    director_headers: dict[str, str],
) -> None:
    """⛔ RECON-02: direktor TANLAGAN mas'ul bazaga yetadi va u AKTOR EMAS.

    ⛔ IKKI ASSERT ATAYIN JUFT: javobdagi qiymat ham, BAZADAGI qator ham
       o'lchanadi. Faqat javobga qarash marshrut qiymatni javob modeliga
       qo'yib, bazaga yozmagan holatni KO'RMASDI.

    ⛔ «DIREKTORGA TENG EMAS» ALOHIDA ASSERT: bugungi nuqson aynan shu —
       case hukm chiqargan odamga biriktiriladi. Teng bo'lgan kun oddiy
       «assignee bor» asserti darvozani o'tkazib yuborardi.
    """
    day = _report_day()
    _, case_id = _seed_unpaid_charge(sync_owner_conn, recon, day=day)
    assignee = recon.base.market_a.admin_user_id
    director = recon.base.market_a.director_user_id
    assert assignee != director, (
        "nazorat: seed mas'ul bilan aktorni BIR ODAM qilib qo'ygan — bu test "
        "o'shanda hech nimani o'lchamasdi"
    )

    response = await api_client.patch(
        f"{CASES_URL}/{case_id}",
        json={
            "status": ReconciliationCaseStatus.IN_REVIEW.value,
            "assignee_user_id": str(assignee),
        },
        headers=director_headers,
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["assignee_user_id"] == str(assignee), payload
    assert payload["assignee_user_id"] != str(director), (
        "⛔ B-2: javobdagi mas'ul HUKM CHIQARGAN odam — direktor tanlovi JIMGINA tashlab yuborildi"
    )

    row = sync_owner_conn.execute(_CASE_ROW, (str(recon.market_id), str(case_id))).fetchone()
    assert row is not None, "nazorat: case qatori bazada yo'q"
    assert row[0] == ReconciliationCaseStatus.IN_REVIEW.value, row
    assert str(row[1]) == str(assignee), (
        f"⛔ BAZAGA yozilgan mas'ul tanlangan odam emas: {row[1]} != {assignee}"
    )

    # ⛔ AKTOR O'ZGARMAYDI: tarix qatorining egasi HAMON direktor — mas'ul
    #    uni ALMASHTIRMAYDI, chunki ular ikki boshqa savolning javobi.
    assert payload["events"][-1]["actor_user_id"] == str(director), payload["events"]


async def test_an_explicit_null_clears_the_assignment(
    api_client: httpx.AsyncClient,
    sync_owner_conn: Connection[TupleRow],
    recon: Env,
    director_headers: dict[str, str],
) -> None:
    """⛔ «Biriktirilmagan» tanlovi HAQIQATAN biriktirishni bekor qiladi.

    UI-SPEC ning `<option value="">Biriktirilmagan</option>` bandi bugun
    IMKONSIZ amalni va'da qiladi: `COALESCE(:assignee, assignee_user_id)`
    `NULL` ni E'TIBORSIZ qoldiradi va eski mas'ul o'z joyida qolardi —
    direktor tanlovni bosardi, javob `200` bo'lardi, ekranda esa hech
    nima o'zgarmasdi.
    """
    day = _report_day()
    _, case_id = _seed_unpaid_charge(sync_owner_conn, recon, day=day)
    assignee = recon.base.market_a.admin_user_id

    assigned = await api_client.patch(
        f"{CASES_URL}/{case_id}",
        json={
            "status": ReconciliationCaseStatus.IN_REVIEW.value,
            "assignee_user_id": str(assignee),
        },
        headers=director_headers,
    )
    assert assigned.status_code == 200, assigned.text
    assert assigned.json()["assignee_user_id"] == str(assignee), (
        "nazorat: birinchi biriktirish ishlamadi — bekor qilish da'vosi BO'SH-ROST bo'lardi"
    )

    cleared = await api_client.patch(
        f"{CASES_URL}/{case_id}",
        json={
            "status": ReconciliationCaseStatus.JUSTIFIED.value,
            "assignee_user_id": None,
        },
        headers=director_headers,
    )

    assert cleared.status_code == 200, cleared.text
    assert cleared.json()["assignee_user_id"] is None, cleared.json()
    # ⛔ HOLAT BARIBIR O'ZGARADI: bekor qilish o'tishni BLOKLAMAYDI.
    assert cleared.json()["status"] == ReconciliationCaseStatus.JUSTIFIED.value

    row = sync_owner_conn.execute(_CASE_ROW, (str(recon.market_id), str(case_id))).fetchone()
    assert row is not None and row[1] is None, (
        f"⛔ BAZADA mas'ul hamon turibdi: {row} — «Biriktirilmagan» tanlovi "
        "IMKONSIZ amal bo'lib qolgan"
    )


async def test_a_silent_transition_keeps_the_existing_assignee(
    api_client: httpx.AsyncClient,
    sync_owner_conn: Connection[TupleRow],
    recon: Env,
    director_headers: dict[str, str],
) -> None:
    """⛔ B-2: maydon YUBORILMAGAN o'tish mavjud biriktirishni O'G'IRLAMAYDI.

    =======================================================================
    ⛔⛔ IKKI SHOX BIR TESTDA — VA IKKALASI HAM KERAK.

      (a) EGASI BOR case: mijoz JIM -> egasi O'ZGARMAYDI. Bugun
          `COALESCE(:actor_user_id, assignee_user_id)` aktorni tanlaydi,
          ya'ni har holat o'zgarishi biriktirishni jimgina o'g'irlaydi.

      (b) EGASIZ case: mijoz JIM -> uni QO'LGA OLGAN odam egasi bo'ladi.
          Bu BUGUNGI xulq va u ATAYIN saqlanadi
          (`_UPDATE_CASE_STATUS` docstringidagi mavjud qoida).

    ⛔ (b) SIZ (a) NI YOZIB BO'LMAYDI: `COALESCE` ni butunlay olib tashlash
       ham (a) ni yashil qilardi, lekin egasiz case abadiy egasiz qolardi
       va navbatda «bu case kimda?» savoli javobsiz bo'lardi.
    =======================================================================
    """
    day = _report_day()
    _, owned_case = _seed_unpaid_charge(sync_owner_conn, recon, day=day)
    _, orphan_case = _seed_unregistered_anomaly(sync_owner_conn, recon, day=day, stall_index=1)
    assignee = recon.base.market_a.admin_user_id
    director = recon.base.market_a.director_user_id

    assigned = await api_client.patch(
        f"{CASES_URL}/{owned_case}",
        json={
            "status": ReconciliationCaseStatus.IN_REVIEW.value,
            "assignee_user_id": str(assignee),
        },
        headers=director_headers,
    )
    assert assigned.status_code == 200, assigned.text

    # ---- (a) MIJOZ JIM, EGASI BOR -> egasi SAQLANADI.
    silent = await api_client.patch(
        f"{CASES_URL}/{owned_case}",
        json={"status": ReconciliationCaseStatus.JUSTIFIED.value},
        headers=director_headers,
    )
    assert silent.status_code == 200, silent.text
    assert silent.json()["assignee_user_id"] == str(assignee), (
        "⛔ B-2: holat o'zgarishi mavjud biriktirishni JIMGINA o'g'irladi — "
        f"case endi {silent.json()['assignee_user_id']} da"
    )

    # ---- (b) MIJOZ JIM, EGASI YO'Q -> uni QO'LGA OLGAN odam egasi bo'ladi.
    taken = await api_client.patch(
        f"{CASES_URL}/{orphan_case}",
        json={"status": ReconciliationCaseStatus.IN_REVIEW.value},
        headers=director_headers,
    )
    assert taken.status_code == 200, taken.text
    assert taken.json()["assignee_user_id"] == str(director), (
        "egasiz case uni qo'lga olgan odamga tushishi kerak edi — bu BUGUNGI "
        f"xulq va u saqlanadi: {taken.json()['assignee_user_id']}"
    )


async def test_a_foreign_market_member_cannot_be_assigned(
    api_client: httpx.AsyncClient,
    sync_owner_conn: Connection[TupleRow],
    recon: Env,
    director_headers: dict[str, str],
) -> None:
    """⛔⛔ T-07-109: BEGONA BOZOR xodimini biriktirish **422** bilan RAD ETILADI.

    =======================================================================
    ⛔⛔ BU FAYLDAGI ENG QIMMAT DA'VO VA U «YO'Q FOYDALANUVCHI» NI EMAS,
        HAQIQATAN MAVJUD BEGONA XODIMNI o'lchaydi.

    `reconciliation_cases.assignee_user_id` da `users` ga FK ⛔ YO'Q
    (`0023:344-347`), ya'ni baza «bu odam bu bozorda ishlaydimi?»
    savolini UMUMAN bermaydi. Yagona to'siq — ilova qatlami.

    ⛔ NAZORAT (b) MAJBURIY: agar test tasodifiy UUID bilan yozilsa, u
       «mavjud bo'lmagan foydalanuvchi rad etildi» ni o'lchardi va
       TENANCY haqida HECH NIMA isbotlamasdi — darvoza `member_roles()`
       olib tashlanganda ham yashil qolardi.

    ⛔ NAZORAT (a) HAM MAJBURIY: rad etish `rollback` ga TAYANMASLIGI
       kerak. Tekshiruv `transition()` dan KEYIN qilinsa holat allaqachon
       o'zgargan bo'lardi va «case umuman o'zgarmadi» da'vosi tranzaksiya
       xulqiga bog'liq bo'lib qolardi.
    =======================================================================
    """
    day = _report_day()
    _, case_id = _seed_unpaid_charge(sync_owner_conn, recon, day=day)
    foreigner = recon.base.market_b.admin_user_id

    # ---- NAZORAT (b): bu odam HAQIQATAN B bozorining a'zosi.
    membership = sync_owner_conn.execute(
        _MEMBER_ROLES, (str(recon.base.market_b.id), str(foreigner))
    ).fetchone()
    assert membership is not None, (
        "nazorat: tanlangan `user_id` B bozorida A'ZO EMAS — test o'shanda "
        "«yo'q foydalanuvchi» ni o'lchardi va TENANCY haqida hech nima "
        "isbotlamasdi"
    )
    assert (
        sync_owner_conn.execute(_MEMBER_ROLES, (str(recon.market_id), str(foreigner))).fetchone()
        is None
    ), "nazorat: o'sha odam A bozorida ham a'zo — chegara yo'q"

    response = await api_client.patch(
        f"{CASES_URL}/{case_id}",
        json={
            "status": ReconciliationCaseStatus.IN_REVIEW.value,
            "assignee_user_id": str(foreigner),
        },
        headers=director_headers,
    )

    assert response.status_code == 422, response.text
    assert response.json()["detail"] == "assignee_not_in_market", response.json()

    # ---- NAZORAT (a): case qatori UMUMAN o'zgarmagan.
    row = sync_owner_conn.execute(_CASE_ROW, (str(recon.market_id), str(case_id))).fetchone()
    assert row is not None
    assert row[0] == ReconciliationCaseStatus.NEW.value, (
        f"⛔ rad etilgan so'rov HOLATNI o'zgartirib yubordi: {row}"
    )
    assert row[1] is None, f"⛔ rad etilgan so'rov MAS'ULNI yozib yubordi: {row}"

    events = sync_owner_conn.execute(_COUNT_EVENTS, (str(recon.market_id), str(case_id))).fetchone()
    assert events is not None and events[0] == 0, (
        f"⛔ rad etilgan so'rov TARIXGA qator yozdi: {events}"
    )


async def test_an_unknown_user_is_rejected_like_a_foreign_one(
    api_client: httpx.AsyncClient,
    sync_owner_conn: Connection[TupleRow],
    recon: Env,
    director_headers: dict[str, str],
) -> None:
    """⛔ T-07-110: «yo'q odam» va «begona bozor xodimi» — AYNI javob.

    ⛔ 403 YOKI BOSHQA KOD BERILMAYDI: farqning O'ZI «bunday foydalanuvchi
       bor, lekin sizniki emas» degan ma'lumotni oshkor qilardi va
       hujumchi identifikatorlarni javob kodi bo'yicha sanab chiqa olardi
       — `member_roles()` docstringidagi qoidaning aynan takrori.
    """
    day = _report_day()
    _, first_case = _seed_unpaid_charge(sync_owner_conn, recon, day=day)
    _, second_case = _seed_unregistered_anomaly(sync_owner_conn, recon, day=day, stall_index=1)

    unknown = await api_client.patch(
        f"{CASES_URL}/{first_case}",
        json={
            "status": ReconciliationCaseStatus.IN_REVIEW.value,
            "assignee_user_id": str(uuid4()),
        },
        headers=director_headers,
    )
    foreign = await api_client.patch(
        f"{CASES_URL}/{second_case}",
        json={
            "status": ReconciliationCaseStatus.IN_REVIEW.value,
            "assignee_user_id": str(recon.base.market_b.cashier_user_id),
        },
        headers=director_headers,
    )

    assert unknown.status_code == 422, unknown.text
    assert unknown.status_code == foreign.status_code
    assert unknown.content == foreign.content, (
        "javob tanalari farq qiladi — enumeration signali (T-07-110)"
    )


# ===========================================================================
# 4. NAVBAT — KEYSET SAHIFALASH VA KUN KESIMIDAGI HISOBLAGICHLAR
# ===========================================================================


async def test_case_list_pagination_is_keyset(
    api_client: httpx.AsyncClient,
    sync_owner_conn: Connection[TupleRow],
    recon: Env,
    director_headers: dict[str, str],
) -> None:
    """⛔ DQ-4: ikkinchi sahifa birinchisi bilan KESISHMAYDI, hisoblagich BIR XIL.

    =======================================================================
    ⛔ IKKI DA'VO ATAYIN BIRGA:

      (a) KESISHMASLIK — `OFFSET` bilan sahifalaganda nazoratchi bir
          case'ni IKKI MARTA ko'rib, ikkinchisini UMUMAN ko'rmasdi
          (`_CASE_ROWS` docstringi);
      (b) HISOBLAGICHLARNING TENGLIGI — ular SAHIFAGA emas, KUNGA
          tegishli. Sahifadan hisoblansa ikkinchi sahifada «bugun
          nechta case?» savoli boshqa javob berardi.
    =======================================================================
    """
    day = _report_day()
    # ⚠ HAR CASE O'Z NISHONI BILAN: qisman UNIQUE indeks bitta nishonga
    #   ikkinchi case ochishni STRUKTURAVIY ravishda taqiqlaydi, anomaliya
    #   unikaligi esa `(rasta, kun, tur)` bo'yicha — shuning uchun rasta
    #   VA tur ikkalasi ham aylantiriladi.
    seeded = {
        str(
            _seed_unregistered_anomaly(
                sync_owner_conn,
                recon,
                day=day,
                stall_index=index,
                kind=AnomalyKind.UNASSIGNED_OCCUPIED
                if index % 2 == 0
                else AnomalyKind.CLOSED_DAY_OCCUPIED,
            )[1]
        )
        for index in range(4)
    }
    assert len(seeded) == 4, "nazorat: seed to'rtta MUSTAQIL case yozmadi"

    first = await api_client.get(
        CASES_URL, params={"day": day.isoformat(), "limit": 2}, headers=director_headers
    )
    assert first.status_code == 200, first.text
    page_one = first.json()
    assert len(page_one["rows"]) == 2, page_one
    assert page_one["next_cursor"] is not None, (
        "sahifa TO'LDI, lekin kursor kelmadi — usiz keyset sahifalash "
        "IFODALAB BO'LMASDI (`CaseListPage.next_cursor` docstringi)"
    )

    second = await api_client.get(
        CASES_URL,
        params={"day": day.isoformat(), "limit": 2, "cursor": page_one["next_cursor"]},
        headers=director_headers,
    )
    assert second.status_code == 200, second.text
    page_two = second.json()

    ids_one = {row["case_id"] for row in page_one["rows"]}
    ids_two = {row["case_id"] for row in page_two["rows"]}
    assert ids_one & ids_two == set(), sorted(ids_one & ids_two)
    assert ids_one | ids_two == seeded, sorted((ids_one | ids_two) ^ seeded)

    # (b) HISOBLAGICHLAR IKKALA SAHIFADA HAM BIR XIL — ular KUNGA tegishli.
    for key in ("new_count", "in_review_count", "justified_count", "unjustified_count"):
        assert page_one[key] == page_two[key] == (4 if key == "new_count" else 0), (
            f"{key}: {page_one[key]} vs {page_two[key]}"
        )

    # ⛔ BUZILGAN KURSOR JIM TASHLAB YUBORILMAYDI: aks holda nazoratchi
    #    «Yana» tugmasini bosganda BIRINCHI sahifani qayta ko'rardi va
    #    navbat cheksiz aylanardi — u buni sezmasdi ham.
    probe = await api_client.get(
        CASES_URL,
        params={"day": day.isoformat(), "cursor": "buzilgan-kursor"},
        headers=director_headers,
    )
    assert probe.status_code == 422, probe.text


async def test_case_list_counts_ignore_the_status_filter(
    api_client: httpx.AsyncClient,
    sync_owner_conn: Connection[TupleRow],
    recon: Env,
    director_headers: dict[str, str],
) -> None:
    """⛔ To'rt hisoblagich `status` filtridan MUSTAQIL — kun bo'yicha.

    Nazoratchi «yangi» filtrini yoqqanda «bugun nechta case yopildi?»
    savolining javobi o'zgarmasligi kerak. Filtrni hisoblagichlarga ham
    qo'llash tanlangan holatdan boshqa uchtasini NOLGA tushirardi va u
    «bugun hech nima yopilmadi» bilan MEXANIK ravishda bir xil
    ko'rinardi.
    """
    day = _report_day()
    _seed_unpaid_charge(sync_owner_conn, recon, day=day)
    anomaly_id, _ = _seed_unregistered_anomaly(sync_owner_conn, recon, day=day)
    del anomaly_id

    filtered = await api_client.get(
        CASES_URL,
        params={"day": day.isoformat(), "status": ReconciliationCaseStatus.NEW.value},
        headers=director_headers,
    )

    assert filtered.status_code == 200, filtered.text
    payload = filtered.json()
    assert payload["new_count"] == 2, payload
    assert len(payload["rows"]) == 2, payload

    unknown = await api_client.get(
        CASES_URL, params={"day": day.isoformat(), "status": "other"}, headers=director_headers
    )
    assert unknown.status_code == 422, unknown.text


# ===========================================================================
# 5. HIT-RATE — MAXRAJ VA ORALIQ (D-13, T-07-60)
# ===========================================================================


async def test_hit_rate_excludes_open_cases(
    api_client: httpx.AsyncClient,
    sync_owner_conn: Connection[TupleRow],
    recon: Env,
    director_headers: dict[str, str],
) -> None:
    """⛔ D-13: `new` / `in_review` MAXRAJGA KIRMAYDI, lekin YASHIRILMAYDI ham.

    ⛔ NAZORAT ASSERTI (`open_cases > 0`) MAJBURIY: seedda ochiq case
       BO'LMASA maxraj da'vosi BO'SH-ROST bo'lardi — 05-15 ning S-D
       darsi va 07-07 ning sabotaj o'lchovi aynan shu nuqtani ko'rsatgan.
    """
    day = _report_day()
    _, unpaid_case = _seed_unpaid_charge(sync_owner_conn, recon, day=day)
    # ⚠ IKKI ANOMALIYA BOSHQA-BOSHQA RASTADA: unikalik `(rasta, kun, tur)`
    #   bo'yicha (`_seed_unregistered_anomaly` docstringi).
    _, first_anomaly_case = _seed_unregistered_anomaly(
        sync_owner_conn, recon, day=day, stall_index=1
    )
    _, second_anomaly_case = _seed_unregistered_anomaly(
        sync_owner_conn, recon, day=day, stall_index=2
    )

    for case_id, to_status in (
        (first_anomaly_case, ReconciliationCaseStatus.JUSTIFIED),
        (second_anomaly_case, ReconciliationCaseStatus.UNJUSTIFIED),
    ):
        closed = await api_client.patch(
            f"{CASES_URL}/{case_id}", json={"status": to_status.value}, headers=director_headers
        )
        assert closed.status_code == 200, closed.text
    del unpaid_case  # ⚠ ATAYIN `new` holatida qoladi — u maxrajga KIRMAYDI.

    response = await api_client.get(
        HIT_RATE_URL,
        params={"from": day.isoformat(), "to": day.isoformat()},
        headers=director_headers,
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["justified"] == 1, payload
    assert payload["unjustified"] == 1, payload
    assert payload["open_cases"] == 1, payload
    assert payload["hit_rate"] == pytest.approx(0.5), payload


async def test_hit_rate_is_null_when_nothing_was_measured(
    api_client: httpx.AsyncClient,
    recon: Env,
    director_headers: dict[str, str],
) -> None:
    """⛔ O'lchov yo'q bo'lganda javob **`null`**, `0.0` EMAS (D-13).

    «Hali o'lchov yo'q» ≠ «nol aniqlik». Nol yozish direktorning birinchi
    haftadagi qaroriga bevosita ta'sir qilardi — 5-fazaning Wilson
    qarori bilan aynan bir sinfda.
    """
    day = _report_day()

    response = await api_client.get(
        HIT_RATE_URL,
        params={"from": day.isoformat(), "to": day.isoformat()},
        headers=director_headers,
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["hit_rate"] is None, payload
    assert payload["justified"] == 0
    assert payload["unjustified"] == 0


async def test_hit_rate_rejects_an_unbounded_range(
    api_client: httpx.AsyncClient,
    recon: Env,
    director_headers: dict[str, str],
) -> None:
    """⛔ T-07-60: oraliq MAJBURIY va 92 kundan uzun bo'lolmaydi.

    Chegarasiz so'rov `reconciliation_cases` ni butunlay skanerlardi va
    bitta so'rov bilan bozorning butun tarixini tortib olish yo'li ochiq
    qolardi.
    """
    day = _report_day()

    missing = await api_client.get(HIT_RATE_URL, headers=director_headers)
    assert missing.status_code == 422, missing.text

    too_wide = await api_client.get(
        HIT_RATE_URL,
        params={"from": (day - timedelta(days=92)).isoformat(), "to": day.isoformat()},
        headers=director_headers,
    )
    assert too_wide.status_code == 422, too_wide.text
    assert too_wide.json()["detail"] == "range_too_wide"

    # NAZORAT: AYNAN 92 kunlik oraliq O'TADI — chegara bir kunga
    # siljib qolgan bo'lsa bu assert uni ushlaydi.
    exact = await api_client.get(
        HIT_RATE_URL,
        params={"from": (day - timedelta(days=91)).isoformat(), "to": day.isoformat()},
        headers=director_headers,
    )
    assert exact.status_code == 200, exact.text

    inverted = await api_client.get(
        HIT_RATE_URL,
        params={"from": day.isoformat(), "to": (day - timedelta(days=1)).isoformat()},
        headers=director_headers,
    )
    assert inverted.status_code == 422, inverted.text
    assert inverted.json()["detail"] == "range_invalid"


# ===========================================================================
# 5b. CASE TUG'ILISHI VA NAIVE KURSOR (WR-01, WR-05)
#
# ⛔⛔ IKKI ARZON, LEKIN HAQIQIY NUQSON.
#
#   WR-01 — sxema, model va API uchta joyda `from_status IS NULL` ni
#           ALLAQACHON e'lon qiladi (`EVENT_FROM_STATUS_CHECK`,
#           `ReconciliationCaseEvent` docstringi, `CaseEvent.from_status:
#           str | None`), lekin o'sha yo'ldan mahsulotda HECH QACHON
#           qator o'tmasdi: case'ni `recon.open` ochardi va tarix BO'SH
#           qolardi. Ya'ni case tarixi IKKINCHI qadamdan boshlanardi.
#
#   WR-05 — `2026-01-01|<uuid>` shaklidagi kursor `datetime.fromisoformat()`
#           dan MUVAFFAQIYATLI o'tadi (u yaroqli ISO), lekin `tzinfo`
#           siz qoladi. `asyncpg` uni `timestamptz` ga kodlay olmaydi ->
#           `DBAPIError` -> `500 internal_error`. Ya'ni `_decode_cursor()`
#           ning O'Z docstringi («buzilgan qiymat ⛔ 422») bajarilmasdi.
# ===========================================================================


async def test_a_case_is_born_with_a_system_event(
    api_client: httpx.AsyncClient,
    app_sessionmaker: async_sessionmaker[AsyncSession],
    sync_owner_conn: Connection[TupleRow],
    recon: Env,
    director_headers: dict[str, str],
) -> None:
    """⛔ WR-01: `recon.open` ochgan case tarixi TUG'ILISHDAN boshlanadi.

    =======================================================================
    ⛔ CASE ⛔ JOB TOMONIDAN ochiladi, `seed_case()` bilan EMAS: qo'lda
       yozilgan qator mahsulot yo'lini CHETLAB o'tardi va bu test
       o'zi seed qilgan narsani o'lchardi.

    ⛔ UCH DA'VO BIRGA VA HECH BIRI ORTIQCHA EMAS:
       (a) tug'ilish qatori BOR va u TIZIMNIKI (`actor_user_id IS NULL`);
       (b) u direktor ekranida KO'RINADI (`events` bo'sh EMAS);
       (c) takroriy yugurish IKKINCHI qator YOZMAYDI — `ON CONFLICT DO
           NOTHING` tufayli `inserted` bo'sh qoladi.

    ⛔ (c) SIZ (a) NI YOZIB BO'LMAYDI: hodisani case bilan bir
       tranzaksiyada emas, ALOHIDA bayonot bilan yozgan yechim (a) ni
       yashil qilardi va har kechagi qayta yugurish tarixga YANGI
       «tug'ildi» qatorini qo'shardi.
    =======================================================================
    """
    day = _report_day()
    anomaly_id = _seed_evidenced_anomaly(sync_owner_conn, recon, day=day, stall_index=1)

    opened = await reconciliation_open(app_sessionmaker, business_date=day)
    assert opened.errors == [], f"`recon.open` xato berdi: {opened.errors}"
    assert opened.anomaly_cases >= 1, (
        f"job SINF B dan case ochmadi: {opened} — bu testning butun kirishi YO'Q"
    )

    listed = await api_client.get(
        CASES_URL, params={"day": day.isoformat()}, headers=director_headers
    )
    assert listed.status_code == 200, listed.text
    born = [row for row in listed.json()["rows"] if row["anomaly_id"] == str(anomaly_id)]
    assert len(born) == 1, f"job ochgan case navbatda topilmadi: {listed.json()['rows']}"
    case_id = born[0]["case_id"]

    detail = await api_client.get(f"{CASES_URL}/{case_id}", headers=director_headers)
    assert detail.status_code == 200, detail.text
    events = detail.json()["events"]

    # ---- (b) DIREKTOR EKRANIDA KO'RINADI.
    assert events, (
        "⛔ WR-01: yangi case tarixi BO'SH keldi — `from_status IS NULL` yo'li "
        "sxemada e'lon qilingan, lekin mahsulotda HECH QACHON bajarilmaydi"
    )
    # ---- (a) QATOR TIZIMNIKI VA U TUG'ILISH.
    assert len(events) == 1, events
    assert events[0]["from_status"] is None, events[0]
    assert events[0]["actor_user_id"] is None, (
        "tug'ilish qatorining aktori TIZIM (`NULL`) bo'lishi SHART — odam "
        f"identifikatori u yerda «kimdir ochdi» degan YOLG'ON da'vo bo'lardi: {events[0]}"
    )
    assert events[0]["to_status"] == ReconciliationCaseStatus.NEW.value, events[0]

    # ---- (c) TAKRORIY YUGURISH IKKINCHI QATOR YOZMAYDI.
    again = await reconciliation_open(app_sessionmaker, business_date=day)
    assert again.errors == [], f"ikkinchi yugurish xato berdi: {again.errors}"
    assert again.skipped_existing >= 1, (
        f"nazorat: ikkinchi yugurish `skipped_existing` shoxiga TUSHMADI: {again}"
    )
    count = sync_owner_conn.execute(_COUNT_EVENTS, (str(recon.market_id), str(case_id))).fetchone()
    assert count is not None and int(count[0]) == 1, (
        f"⛔ takroriy yugurish IKKINCHI tug'ilish qatorini yozdi: {count} — "
        "har kechagi cron tarixni shovqin bilan to'ldirardi"
    )


async def test_a_naive_cursor_is_a_422_not_a_500(
    api_client: httpx.AsyncClient,
    sync_owner_conn: Connection[TupleRow],
    recon: Env,
    director_headers: dict[str, str],
) -> None:
    """⛔ WR-05: tz-siz kursor **422** — navbat kursorida.

    =======================================================================
    ⛔⛔ O'LCHANGAN XULQ REJADA KUTILGANIDAN ⛔ YOMONROQ CHIQDI.

    Reja `500 internal_error` ni kutgan edi (`asyncpg` `timestamptz` ga
    kodlay olmaydi degan farazda). O'LCHOV boshqasini ko'rsatdi:
    so'rov bazagacha BORADI va **200** qaytadi — `rows` BO'SH, lekin
    `new_count` 2 da turadi.

    Ya'ni nuqson `500` emas, ⛔ **JIM YOLG'ON**: nazoratchi «Yana»
    tugmasini bosganda BO'SH sahifani ko'radi, hisoblagich esa «bu kunda
    2 ta case bor» deb turadi. Aynan shu holatni `_decode_cursor()` ning
    O'Z docstringi taqiqlaydi («buzilgan qiymat ⛔ 422, JIM
    E'TIBORSIZLIK EMAS») — ya'ni funksiya o'z va'dasini bajarmasdi.

    ⛔ ASSERT IKKALASINI HAM QULFLAYDI (`!= 500` VA `== 422`): mexanizm
       kelajakda o'zgarsa ham (masalan `asyncpg` qattiqlashsa) da'vo
       o'sha bo'lib qoladi.
    =======================================================================

    ⛔ `"buzilgan-kursor"` DAN BOSHQA SINF: u `ValueError` beradi va
       ALLAQACHON tutilgan. Bu yerdagi qiymat `datetime.fromisoformat()`
       dan MUVAFFAQIYATLI o'tadi (`2026-01-01` yaroqli ISO), lekin
       `tzinfo` siz qoladi — ya'ni u SERVER qurgan kursor EMAS, qo'lda
       yasalgan qiymat, ya'ni KIRISH xatosi.

    ⛔ NAZORAT: SERVER QURGAN kursor (tz-li) hamon ishlaydi — usiz test
       «kursor umuman ishlamaydi» holatida ham yashil bo'lardi.
    """
    day = _report_day()
    seeded = {
        str(_seed_unregistered_anomaly(sync_owner_conn, recon, day=day, stall_index=index)[1])
        for index in range(2)
    }
    assert len(seeded) == 2, "nazorat: seed ikkita MUSTAQIL case yozmadi"

    naive = await api_client.get(
        CASES_URL,
        params={"day": day.isoformat(), "cursor": f"2026-01-01|{uuid4()}"},
        headers=director_headers,
    )

    assert naive.status_code != 500, (
        "⛔ tz-siz kursor bazagacha borib `DBAPIError` ga aylandi — kirish "
        f"xatosi SERVER nosozligi bo'lib ko'rinyapti: {naive.text}"
    )
    assert naive.status_code == 422, naive.text
    assert naive.json()["detail"] == "cursor_invalid", naive.json()

    # ---- NAZORAT: SERVER QURGAN kursor ikkinchi sahifani BERADI.
    first = await api_client.get(
        CASES_URL, params={"day": day.isoformat(), "limit": 1}, headers=director_headers
    )
    assert first.status_code == 200, first.text
    assert first.json()["next_cursor"] is not None, first.json()

    second = await api_client.get(
        CASES_URL,
        params={"day": day.isoformat(), "limit": 1, "cursor": first.json()["next_cursor"]},
        headers=director_headers,
    )
    assert second.status_code == 200, second.text
    assert {row["case_id"] for row in second.json()["rows"]} & {
        row["case_id"] for row in first.json()["rows"]
    } == set()


async def test_a_naive_delivery_cursor_is_a_422_not_a_500(
    api_client: httpx.AsyncClient,
    sync_owner_conn: Connection[TupleRow],
    recon: Env,
    director_headers: dict[str, str],
) -> None:
    """⛔ WR-05 ning IKKINCHI dekoderi — `GET /delivery` kursori.

    ⛔ IKKI DEKODER ⛔ IKKI TEST: `_decode_cursor()` va
       `_decode_delivery_cursor()` — MUSTAQIL funksiyalar va bittasini
       tuzatib ikkinchisini unutish aynan shu fayl qamramaydigan
       nosozlik bo'lardi.

    ⚠ O'LCHANGAN QIZIL — navbat kursoridagi bilan AYNI SINF: **200**
      qaytardi, `rows` BO'SH, `pending_count` esa 2 da turdi. Ya'ni
      direktor «bugun xabar yuborilmagan» degan YOLG'ON xulosaga
      kelardi, holbuki navbatda ikkita qator bor edi.
    """
    day = business_today()
    seeded = [
        seed_outbox_row(sync_owner_conn, market_id=recon.market_id, vendor_id=recon.vendor_id)
        for _ in range(2)
    ]
    assert len(set(seeded)) == 2, "nazorat: seed ikkita MUSTAQIL navbat qatori yozmadi"

    naive = await api_client.get(
        DELIVERY_URL,
        params={"day": day.isoformat(), "cursor": f"2026-01-01|{uuid4()}"},
        headers=director_headers,
    )

    assert naive.status_code != 500, f"⛔ tz-siz yetkazilganlik kursori `500` berdi: {naive.text}"
    assert naive.status_code == 422, naive.text
    assert naive.json()["detail"] == "cursor_invalid", naive.json()

    # ---- NAZORAT: SERVER QURGAN kursor ikkinchi sahifani BERADI.
    first = await api_client.get(
        DELIVERY_URL, params={"day": day.isoformat(), "limit": 1}, headers=director_headers
    )
    assert first.status_code == 200, first.text
    assert first.json()["next_cursor"] is not None, first.json()

    second = await api_client.get(
        DELIVERY_URL,
        params={"day": day.isoformat(), "limit": 1, "cursor": first.json()["next_cursor"]},
        headers=director_headers,
    )
    assert second.status_code == 200, second.text
    assert {row["outbox_id"] for row in second.json()["rows"]} & {
        row["outbox_id"] for row in first.json()["rows"]
    } == set()


# ===========================================================================
# 6. CROSS-TENANT — 404, VA 403 EMAS (T-07-59)
# ===========================================================================


async def test_cross_tenant_case_is_not_found(
    api_client: httpx.AsyncClient,
    sync_owner_conn: Connection[TupleRow],
    recon: Env,
    director_headers: dict[str, str],
) -> None:
    """⛔ Begona bozorning case'i -> **404**, va u MAVJUD BO'LMAGAN ID bilan AYNI.

    =======================================================================
    ⛔ 403 JAVOBINING O'ZI «bunday case bor, lekin sizniki emas» degan
       ma'lumotni oshkor qilardi va hujumchi identifikatorlarni javob
       KODI bo'yicha sanab chiqa olardi (T-07-59).

    ⛔ IKKI JAVOB BAYT-BAYT SOLISHTIRILADI: bir xil 404 ichida turli
       `detail` matni ham enumeration signali bo'lardi.
    =======================================================================
    """
    day = _report_day()
    market_b = recon.base.market_b
    foreign_case = seed_case(
        sync_owner_conn,
        market_id=market_b.id,
        service_date=day,
        anomaly_id=_seed_foreign_anomaly(sync_owner_conn, recon, day=day),
    )

    foreign = await api_client.get(f"{CASES_URL}/{foreign_case}", headers=director_headers)
    unknown = await api_client.get(f"{CASES_URL}/{uuid4()}", headers=director_headers)

    assert foreign.status_code != 403, (
        "403 case MAVJUDLIGINI tasdiqlaydi — 404 bo'lishi shart (T-07-59)"
    )
    assert foreign.status_code == 404, foreign.text
    assert foreign.status_code == unknown.status_code
    assert foreign.content == unknown.content, "javob tanalari farq qiladi — enumeration signali"

    patched = await api_client.patch(
        f"{CASES_URL}/{foreign_case}",
        json={"status": ReconciliationCaseStatus.IN_REVIEW.value},
        headers=director_headers,
    )
    assert patched.status_code == 404, patched.text


def _seed_foreign_anomaly(conn: Connection[TupleRow], env: Env, *, day: date) -> UUID:
    """B BOZORINING dalilsiz anomaliyasi — cross-tenant nishoni.

    ⛔ `no_coverage_stall` ATAYIN: B bozorida dalil zanjiri (hodisa +
       kadr) seedda YO'Q va uni qurish bu testning savoliga (tenant
       chegarasi) hech nima qo'shmasdi. Case sxema darajasida qonuniy
       — `recon.open` uni ochmaydi, lekin bu test JOBNI emas,
       MARSHRUTNI sinaydi.
    """
    anomaly_id = uuid4()
    conn.execute(
        "INSERT INTO billing_anomalies (id, market_id, kind, stall_id, service_date) "
        "VALUES (%s, %s, %s, %s, %s)",
        (
            str(anomaly_id),
            str(env.base.market_b.id),
            AnomalyKind.NO_COVERAGE_STALL.value,
            str(env.domain.market_b.stall_ids[0]),
            day,
        ),
    )
    return anomaly_id
