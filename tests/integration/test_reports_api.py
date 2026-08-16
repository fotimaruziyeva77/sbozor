"""`/api/v1/reports/*` — RECON-04 ning HTTP kontrakti (uch JSON marshruti).

=============================================================================
⛔⛔ BU FAYL `test_report_repo.py` NI TAKRORLAMAYDI.

Davr arifmetikasi (nol kunlar, storno belgisi, tuzatish netlanishi,
`code_sort` tartibi, ikki sinfning ajralishi) 08-04 da HAQIQIY bazada,
to'qqiz darvoza bilan o'lchangan. Bu yerda faqat HTTP CHEGARASIDAGI
da'volar — ular repo qatlamida UMUMAN ko'rinmaydi:

  1. HUQUQ — kim ochadi, kim 403 oladi (⛔ `platform_admin` HAM 403);
  2. AUDIT — bitta so'rov AYNAN bitta iz qoldiradi, sotuvchi boshiga EMAS;
  3. DAVR CHEGARASI — uchta xato uchta ALOHIDA kod bilan;
  4. CROSS-TENANT — B bozorining direktori A ning qatorlarini ko'rmaydi;
  5. JAVOB TANASI — ism BOR, telefon YO'Q, dalil IDENTIFIKATOR;
  6. SAHIFALASH — yig'indi BUTUN DAVRNIKI, sanoq ekranniki.

=============================================================================
⛔ MARSHRUT NOMLARI: `/revenue`, `/debtors`, `/anomalies`.

08-07 rejasi `/receivables` va `/discrepancies` degan edi, LEKIN 08-03
(TO'LQIN 1) `REPORT_KINDS` ni `{revenue, debtors, anomalies, accuracy}`
deb to'plam TENGLIGI bilan qulflagan (UI-SPEC §12.1, G-43a) va jo'natilgan
klient yo'lni AYNAN o'sha a'zodan quradi. Sabab `app/api/v1/reports.py`
modul docstringining 2-bandida LITERAL yozilgan.

=============================================================================
⚠ SANALAR BAZADAN EMAS, `business_today()` DAN — VA BU FARQ ONGLI.

`test_report_repo.py` sanani `payments.business_date` (generated ustun)
dan o'qiydi, chunki u ARIFMETIKANI o'lchaydi. Bu fayl esa MARSHRUTNING
CHEGARASINI o'lchaydi va chegara aynan `business_today() - 1` bilan
qo'yilgan — ya'ni test marshrut ishlatgan MANBADAN yuradi
(`test_reconciliation_api.py::_report_day()` bilan bir xil qaror).

⚠ FON VAZIFASINI KUTISH MEXANIZMI O'YLAB TOPILMAYDI: `audit_read` yozuvni
  `BackgroundTasks` orqali yuboradi, `httpx.ASGITransport` esa fon
  vazifalarini javob qaytarilishidan OLDIN bajaradi
  (`test_personal_data_audit.py` modul docstringi).
=============================================================================
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import timedelta
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import pytest
from fixtures.admin_api import session_headers
from fixtures.auth_api import audit_rows
from fixtures.billing_domain import (
    TARIFF_SOUM,
    BillingDomainSeed,
    add_daily_charge,
    billing_domain_before_day_close,
)
from fixtures.market_domain import MarketDomainSeed
from fixtures.notification_domain import cleanup_notification_domain, seed_case
from fixtures.nvr_domain import nvr_rows
from fixtures.occupancy_domain import occupancy_rows
from fixtures.snapshot_domain import snapshot_rows
from fixtures.two_markets import SEED_PASSWORD, TwoMarketSeed
from sbozor_core.enums import AuditAction
from sbozor_core.timeutil import business_today

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from datetime import date

    import httpx
    from app.settings import Settings
    from fastapi import FastAPI
    from fixtures import TenantSessionFactory
    from fixtures.auth_users import AuthSeed
    from psycopg import Connection
    from psycopg.rows import TupleRow

    DebtorFactory = Callable[[int], list[UUID]]

REVENUE_URL = "/api/v1/reports/revenue"
DEBTORS_URL = "/api/v1/reports/debtors"
ANOMALIES_URL = "/api/v1/reports/anomalies"

REPORT_URLS = (REVENUE_URL, DEBTORS_URL, ANOMALIES_URL)
REPORT_IDS = ("revenue", "debtors", "anomalies")
"""⛔ UCHALASI HAM HAR ROL TESTIDA ALOHIDA SINALADI.

Bitta marshrutni sinash keyingi ijrochi qo'shadigan to'rtinchisini
qamramasdi va huquq darvozasi marshrut bo'yicha «esdan chiqadigan»
narsaga aylanardi (`test_occupancy_report.py` da o'rnatilgan qoida).
"""

PERSONAL_FIELDS = frozenset({"phone", "full_name", "chat_id", "telegram_user_id"})
"""⛔ JAVOB TANASIDA BO'LMAYDIGAN kalitlar — `vendor_name` bu ro'yxatda YO'Q.

⚠ VA BU FARQ SHU FAZANING O'ZAGI: qarzdorlik reestri HUJJAT va unda ism
  QONUNIY (D-07, §5.5). Taqiq ALOQA ma'lumotiga tegishli — telefon
  eksportga tushib fayl bo'lib tarqalardi, holbuki qarz undirish oqimi
  ALLAQACHON bot eslatmasi (BOT-03, UI-SPEC O-03).

⚠ NUSXA ONGLI (`test_reconciliation_api.py:87-94` da o'rnatilgan qoida):
  `tests/tenancy/` ni import qilish tenancy paketini integratsiya
  to'plamiga bog'lardi.
"""

FORBIDDEN_EVIDENCE_MARKERS = ("presigned", "http", "image")
"""⛔ Dalil — IDENTIFIKATOR, KADR EMAS (07 D-03, T-06-81).

`test_reconciliation_api.py:96-104` dagi ro'yxatning AYNAN nusxasi va
sabab ham aynan o'sha: uchalasi ham javobda paydo bo'lishi «dalil-kadr
yuzasi kengaydi» degan BIRINCHI belgi bo'lardi.
"""

MANY_VENDORS = 200
"""⛔ AUDIT SANOG'INING IKKINCHI HAJMI — VA U «katta son» EMAS, O'LCHOV.

Sanoq da'vosi («bitta so'rov = bitta yozuv») uch sotuvchida ham rost
bo'lardi, agar marshrut sotuvchi boshiga bittadan yozuv yozsa ham —
yo'q, uch sotuvchida u UCH yozuv berardi va farq ko'rinardi. Lekin
FARQNING KATTALIGI muhim: 200 da «har sotuvchi uchun bitta yozuv»
xatosi jurnalni bir so'rovda 200 qator bilan to'ldirardi va HAQIQIY
o'qish hodisasi shovqin ichida ko'milardi (06 №9 da rad etilgan (a)
yo'lining aynan oqibati). Ikki hajm birga o'lchanganda da'vo
«sanoq NATIJAGA BOG'LIQ EMAS» degan ancha kuchli shaklga o'tadi.
"""

_INSERT_VENDOR = (
    "INSERT INTO vendors (id, market_id, full_name, phone_e164) VALUES (%s, %s, %s, %s)"
)
_DRAFT_MARKET = "UPDATE markets SET is_active = false WHERE id = %s"
_DELETE_THEIR_CHARGES = (
    "DELETE FROM daily_charges WHERE market_id = %s AND vendor_id = ANY(%s::uuid[])"
)
_DELETE_VENDORS = "DELETE FROM vendors WHERE id = ANY(%s::uuid[])"
"""Ommaviy sotuvchi qatorlari — ⛔ XOM SQL SHU MODULDA, `fixtures/` DA EMAS.

`test_reconciliation_api.py:121-125` da o'rnatilgan qaror: reja bu
rejaning `files_modified` ini cheklaydi va umumiy seed'ga ko'chirish
boshqa fayllarning darvozalarini bu faylning ehtiyojiga bog'lardi.

=============================================================================
⛔⛔ TOZALASH UCH QADAMLI VA UCHALASI HAM MAJBURIY — O'LCHANGAN.

  1. `UPDATE markets SET is_active = false` — `0020` `daily_charges` ga
     SHARTSIZ (`P0001`) o'zgarmaslik qo'riqchisini qo'ygan va `DELETE`
     uchun YAGONA istisno QORALAMA bozor. Usiz birinchi `DELETE` darhol
     yiqilardi (`cleanup_billing_domain()` ning aynan birinchi qadami);
  2. `daily_charges` ⛔ SOTUVCHIDAN OLDIN: `fk_daily_charges_market_id_
     vendor_id_vendors` da `ondelete` YO'Q va teskari tartib
     `ForeignKeyViolation` beradi (bu ijroda BIR MARTA o'lchandi —
     beshta test AYNAN shu bilan qizardi);
  3. `vendors` — ⛔ VA U `cleanup_billing_domain()` DAN CHIQMAYDI: u
     `vendors` ni `market_id` bo'yicha emas, seed'ning O'Z ro'yxati
     bo'yicha o'chiradi (`cleanup_market_domain()`), ya'ni bu qatorlar
     keyingi testlarga sizib o'tardi va `cleanup_two_markets()` ning
     `DELETE FROM markets` i FK bilan yiqilardi.

⚠ `is_active` QAYTA YOQILMAYDI: `env` teardowni (`cleanup_billing_domain`)
  baribir o'sha bayroqni tushiradi va bozor bir necha satr keyin butunlay
  o'chiriladi (o'sha funksiyaning docstringidagi «semantik jihatdan
  HALOL» qadamining aynan takrori).
=============================================================================
"""


# ===========================================================================
# Fixture'lar — `test_report_repo.py::env` naqshi
# ===========================================================================


@dataclass(frozen=True)
class Env:
    """Bir testning butun kirishi — ikki bozor, rastalar, sotuvchi va tarif."""

    billing: BillingDomainSeed
    domain: MarketDomainSeed
    base: TwoMarketSeed
    auth: AuthSeed

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
def env(
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    auth_seed: AuthSeed,
    market_domain: MarketDomainSeed,
    migrated: None,
) -> Iterator[Env]:
    """⛔ `day_close` YUGURTIRILMAYDI — bu fayl slot qatorlariga TAYANMAYDI.

    `test_reconciliation_api.py::env` `billing_domain` (day_close bilan)
    ni oladi, chunki uning eng qimmat da'vosi `charge_evidence` ga
    tayanadi. Bu yerda dalil zanjiri O'LCHANMAYDI — u 08-04 da repo
    qatlamida o'lchangan, ya'ni qimmatroq seed hech nima qo'shmasdi.

    ⚠ `auth_seed` `market_domain` DAN OLDIN — `test_occupancy_report.py::env`
      qoidasi: pytest fixture'larni teskari tartibda yopadi, ya'ni
      nazoratchi foydalanuvchisi domen qatorlaridan KEYIN o'chiriladi.
    """
    with (
        nvr_rows(sync_owner_conn, two_markets) as nvr,
        snapshot_rows(sync_owner_conn, nvr) as snaps,
        occupancy_rows(sync_owner_conn, two_markets, market_domain, snaps) as occupancy,
        billing_domain_before_day_close(
            sync_owner_conn, two_markets, market_domain, occupancy
        ) as billing,
    ):
        yield Env(billing, market_domain, two_markets, auth_seed)


@pytest.fixture
def reports(sync_owner_conn: Connection[TupleRow], env: Env) -> Iterator[Env]:
    """`env` USTIGA case jadvallarining tozalanishi.

    ⚠ `env` ARGUMENT sifatida olinadi, faqat «oldin ishlasin» uchun emas:
      pytest fixture'larni TESKARI tartibda yopadi, ya'ni case'lar
      billing qatorlaridan OLDIN o'chadi
      (`test_reconciliation_api.py::recon` bilan aynan bir xil sabab).
    """
    try:
        yield env
    finally:
        cleanup_notification_domain(sync_owner_conn, market_ids=list(env.market_ids))


@pytest.fixture
async def director_headers(api_client: httpx.AsyncClient, reports: Env) -> dict[str, str]:
    """DIREKTOR sessiyasi — `report_view` VA `vendor_view` BOR (D-07)."""
    return await session_headers(api_client, reports.base.market_a.director_phone, SEED_PASSWORD)


@pytest.fixture
async def admin_headers(api_client: httpx.AsyncClient, reports: Env) -> dict[str, str]:
    """BOZOR ADMINI sessiyasi — ikkala huquq ham BOR (§5.6)."""
    market_a = reports.base.market_a
    return await session_headers(api_client, market_a.admin_phone, market_a.admin_password)


@pytest.fixture
async def cashier_headers(api_client: httpx.AsyncClient, reports: Env) -> dict[str, str]:
    """KASSIR sessiyasi — ⛔ unda `report_view` YO'Q (UI-SPEC §5.6)."""
    return await session_headers(api_client, reports.base.market_a.cashier_phone, SEED_PASSWORD)


@pytest.fixture
async def inspector_headers(api_client: httpx.AsyncClient, reports: Env) -> dict[str, str]:
    """NAZORATCHI sessiyasi — `ROLE_PERMISSIONS[INSPECTOR]` AYNAN `{OCCUPANCY_REVIEW}`."""
    return await session_headers(api_client, reports.auth.inspector.phone, SEED_PASSWORD)


@pytest.fixture
async def platform_admin_headers(api_client: httpx.AsyncClient, reports: Env) -> dict[str, str]:
    """PLATFORMA ADMINI sessiyasi — ⛔ A bozori TANLANGAN holda.

    ⛔ BOZOR TANLASH MAJBURIY: tanlanmagan sessiyada javob
       `market_not_selected` bo'lardi va test «huquq yo'q» bilan «bozor
       yo'q» ni ajratmasdi — ya'ni 403 YOLG'ON SABABDAN kelardi
       (`fixtures/admin_api.py::session_headers` docstringi).
    """
    return await session_headers(
        api_client,
        reports.base.platform_admin_phone,
        SEED_PASSWORD,
        market_id=reports.market_id,
    )


@pytest.fixture
async def market_b_director_headers(api_client: httpx.AsyncClient, reports: Env) -> dict[str, str]:
    """B BOZORINING direktori — cross-tenant da'vosining sub'ekti."""
    return await session_headers(api_client, reports.base.market_b.director_phone, SEED_PASSWORD)


@pytest.fixture
def tiny_row_limit(api_app: FastAPI, test_settings: Settings) -> Iterator[None]:
    """`report_max_rows = 1` — ⛔ 50 000 QATOR SEED QILINMAYDI.

    =======================================================================
    ⛔ NEGA CHEGARA PASAYTIRILADI, NEGA MA'LUMOT KO'PAYTIRILMAYDI.

    Haqiqiy chegara (50 000) ni seed bilan urish ~50 000 qator yozishni
    talab qilardi va test daqiqalarga cho'zilardi — ya'ni u birinchi
    «sekin testlarni o'chirib qo'yaylik» to'lqinida o'chirilardi.
    O'lchanayotgan narsa esa SON EMAS, SHOX: `row_count > max_rows`
    bo'lganda javob **422** bo'ladimi yoki JIMGINA kesiladimi. Shox
    chegaraning istalgan qiymatida bir xil.

    ⚠ `Settings` `app.state` dan o'qiladi (`deps.py::get_settings_dep`),
      ya'ni bu almashtirish MAHSULOT yo'lini buzmaydi — u aynan
      `lifespan` va test fixture'i ishlatadigan qo'lni ishlatadi.

    ⛔ TIKLASH `finally` DA: `api_app` modul darajasidagi YAGONA `app`
       obyektini qaytaradi, ya'ni tiklanmagan qiymat keyingi testlarga
       SIZIB o'tardi va ular «hisobot juda katta» bilan yiqilardi.
    =======================================================================
    """
    api_app.state.settings = test_settings.model_copy(update={"report_max_rows": 1})
    try:
        yield
    finally:
        api_app.state.settings = test_settings


# ===========================================================================
# Yordamchilar
# ===========================================================================


def _last_closed_day() -> date:
    """Davrning eng yuqori RUXSAT ETILGAN kuni — ⛔ KECHA.

    ⛔ `date.today()` YOKI DB `CURRENT_DATE` ISHLATILMAYDI: marshrut
       chegarani `sbozor_core.timeutil.business_today()` (Asia/Tashkent)
       bilan qo'yadi, konteynerlar esa UTC da yuguradi. Ikki manba
       Toshkent yarim tunidan keyingi besh soatda BIR KUN farq qilardi va
       test FLAKY bo'lardi — sabab kodda emas, SOATDA
       (`test_reconciliation_api.py::_report_day()` ning aynan darsi).
    """
    return business_today() - timedelta(days=1)


def _period(days: int = 7) -> dict[str, str]:
    """`?from=&to=` — oxiri KECHA, uzunligi `days` kun (ikkala uchi ham kiradi)."""
    to_date = _last_closed_day()
    from_date = to_date - timedelta(days=days - 1)
    return {"from": from_date.isoformat(), "to": to_date.isoformat()}


def _seed_unpaid_charge(
    conn: Connection[TupleRow],
    env: Env,
    *,
    day: date,
    stall_index: int = 0,
    vendor_id: UUID | None = None,
) -> UUID:
    """Hisob YOZILGAN, to'lov YO'Q — qarzdorlik reestrining kirish holati.

    ⛔ TO'LOV ATAYIN YOZILMAYDI: `vendor_outstanding()` shundagina noldan
       farqli qoldiq beradi va reestrda qator paydo bo'ladi.

    ⚠ TO'LOV BU FAYLDA UMUMAN YOZILMAYDI VA SABAB SXEMADA:
      `payments.business_date` — `created_at` DAN HOSILA generated ustun,
      ya'ni u HAR DOIM BUGUN. Bugun esa davrning yuqori chegarasidan
      (KECHA) tashqarida, ya'ni seed qilingan to'lov birorta YAROQLI
      hisobot davriga TUSHA OLMAYDI. Tushum arifmetikasi shu sababdan
      `test_report_repo.py` da (repo qatlamida, davr chegarasisiz)
      o'lchanadi va bu yerda TAKRORLANMAYDI.
    """
    charge_id, _ = add_daily_charge(
        conn,
        market_id=env.market_id,
        stall_id=env.stall_ids[stall_index],
        vendor_id=env.vendor_id if vendor_id is None else vendor_id,
        tariff_id=env.tariff_id,
        service_date=day,
    )
    return charge_id


def _seed_many_debtors(conn: Connection[TupleRow], env: Env, count: int) -> list[UUID]:
    """`count` ta sotuvchi + har biriga bittadan to'lanmagan hisob.

    ⛔ HAR HISOB BOSHQA KUNDA: `uq_daily_charges_market_id_stall_id_service_date`
       bitta rastaga bir kunda bitta hisobni ruxsat etadi. Rastalar soni
       seedda oltita, ya'ni 200 qatorni KUN o'qi bo'yicha yoyish yagona
       yo'l — va u davr chegarasiga (`report_max_period_days = 366`)
       sig'adi.

    Returns:
        Yaratilgan sotuvchi identifikatorlari — TOZALASH uchun.
    """
    latest = _last_closed_day()
    vendor_ids: list[UUID] = []
    for index in range(count):
        vendor_id = uuid4()
        conn.execute(
            _INSERT_VENDOR,
            (
                str(vendor_id),
                str(env.market_id),
                f"Qarzdor {index:03d}",
                f"+99870{index:07d}",
            ),
        )
        vendor_ids.append(vendor_id)
        _seed_unpaid_charge(
            conn,
            env,
            day=latest - timedelta(days=index),
            vendor_id=vendor_id,
        )
    return vendor_ids


@pytest.fixture
def debtors(sync_owner_conn: Connection[TupleRow], reports: Env) -> Iterator[DebtorFactory]:
    """Qarzdor sotuvchilarni yaratadi va ⛔ UCH QADAMDA tozalaydi.

    ⛔ TOZALASH FIXTURE'DA, TESTNING `finally` IDA EMAS — va bu farq
       o'lchangan: `finally` bloki har testda TAKRORLANARDI va bittasida
       unutilgan tartib (sotuvchi hisobdan OLDIN) butun to'plamni
       `ForeignKeyViolation` bilan yiqitardi. Fixture tartibni BIR JOYDA
       saqlaydi (`_DELETE_VENDORS` docstringidagi uch qadam).
    """
    created: list[UUID] = []

    def _make(count: int) -> list[UUID]:
        vendor_ids = _seed_many_debtors(sync_owner_conn, reports, count)
        created.extend(vendor_ids)
        return vendor_ids

    try:
        yield _make
    finally:
        if created:
            ids = [str(vendor_id) for vendor_id in created]
            sync_owner_conn.execute(_DRAFT_MARKET, (str(reports.market_id),))
            sync_owner_conn.execute(_DELETE_THEIR_CHARGES, (str(reports.market_id), ids))
            sync_owner_conn.execute(_DELETE_VENDORS, (ids,))


async def _vendor_read_count(
    tenant_session: TenantSessionFactory, market_id: UUID, *, reason: str
) -> int:
    """`action='read'` + `table_name='vendors'` + shu `reason` li yozuvlar soni.

    ⛔ `reason` BO'YICHA FILTRLANADI: sessiya qurilishi (`/auth/login`)
       ham, boshqa yuzalar ham `vendors` ustiga yozuv qoldirishi mumkin.
       Filtrsiz sanoq boshqa hodisani ham sanardi va da'vo YOLG'ON-YASHIL
       bo'lardi.

    ⚠ Superuser bilan O'QILMAYDI: audit ekrani (D-11) AYNAN shu yo'ldan
      ma'lumot oladi (`test_personal_data_audit.py::_stall_reads` qoidasi).
    """
    rows = await audit_rows(tenant_session, market_id, action=str(AuditAction.READ))
    return sum(
        1
        for row in rows
        if row.table_name == "vendors" and (row.new_value or {}).get("reason") == reason
    )


def _keys(payload: Any) -> set[str]:
    """Javob TANASIDAGI barcha kalitlar — ichma-ich.

    ⛔ SXEMA EMAS, TANA: `test_personal_data_coverage.py` javob MODELINI
       o'lchaydi va handler `dict` qaytarib sxemani chetlab o'tsa u
       sezmasdi (`test_reconciliation_api.py:12-16` ning darsi).
    """
    found: set[str] = set()
    if isinstance(payload, dict):
        for key, value in payload.items():
            found.add(key)
            found |= _keys(value)
    elif isinstance(payload, list):
        for item in payload:
            found |= _keys(item)
    return found


# ===========================================================================
# 1. HUQUQ — ⛔ MATRITSA TEGILMAGAN, LEKIN U HTTP DA HAM ISHLAYDI
# ===========================================================================


@pytest.mark.parametrize("url", REPORT_URLS, ids=REPORT_IDS)
async def test_the_director_reads_every_report(
    api_client: httpx.AsyncClient, reports: Env, director_headers: dict[str, str], url: str
) -> None:
    """NAZORAT: 403 huquqdan chiqyaptimi, marshrutning yo'qligidan emas.

    ⚠ USIZ QUYIDAGI UCH RAD ETISH TESTI MARSHRUT UMUMAN QAYD
      ETILMAGAN holatda ham yashil bo'lardi — 404 ham, 403 ham «200
      emas» degan da'voni qanoatlantiradi. Bu holat 05-12 da bir marta
      o'lchangan (`test_occupancy_report.py::
      test_the_director_can_reach_the_report`).
    """
    response = await api_client.get(url, params=_period(), headers=director_headers)

    assert response.status_code == 200, f"{url}: {response.text}"


@pytest.mark.parametrize("url", REPORT_URLS, ids=REPORT_IDS)
async def test_the_market_admin_reads_every_report(
    api_client: httpx.AsyncClient, reports: Env, admin_headers: dict[str, str], url: str
) -> None:
    """Bozor adminida ham `report_view` BOR (§5.6) — yuza IKKI ROLGA ochiq."""
    response = await api_client.get(url, params=_period(), headers=admin_headers)

    assert response.status_code == 200, f"{url}: {response.text}"


@pytest.mark.parametrize("url", REPORT_URLS, ids=REPORT_IDS)
async def test_the_cashier_cannot_read_any_report(
    api_client: httpx.AsyncClient, reports: Env, cashier_headers: dict[str, str], url: str
) -> None:
    """⛔ Kassirda `report_view` YO'Q (D-04, UI-SPEC §5.6) — uchalasida ham 403.

    Kassir pul YIG'ADI, hisobot O'QIMAYDI. Qarzdorlik reestrini kassa
    oldida turgan odamga ochish «kim qarzdor?» ro'yxatini nizo oqimidan
    BUTUNLAY boshqa yuzaga ko'chirardi.
    """
    response = await api_client.get(url, params=_period(), headers=cashier_headers)

    assert response.status_code == 403, f"{url}: {response.status_code} — {response.text}"


@pytest.mark.parametrize("url", REPORT_URLS, ids=REPORT_IDS)
async def test_the_inspector_cannot_read_any_report(
    api_client: httpx.AsyncClient, reports: Env, inspector_headers: dict[str, str], url: str
) -> None:
    """⛔ `ROLE_PERMISSIONS[INSPECTOR]` AYNAN `{OCCUPANCY_REVIEW}` (T-05-58).

    Nazoratchi o'z aniqligini ko'rsa u RAQAMNI YAXSHILASHGA urinardi va
    o'lchov o'zi o'lchayotgan narsani o'zgartirardi — 05-12 da o'rnatilgan
    sabab, hisobot yuzasida ham kuchda.
    """
    response = await api_client.get(url, params=_period(), headers=inspector_headers)

    assert response.status_code == 403, f"{url}: {response.status_code} — {response.text}"


@pytest.mark.parametrize("url", REPORT_URLS, ids=REPORT_IDS)
async def test_the_platform_admin_cannot_read_any_report(
    api_client: httpx.AsyncClient,
    reports: Env,
    platform_admin_headers: dict[str, str],
    url: str,
) -> None:
    """⛔⛔ PLATFORMA ADMINIGA `REPORT_VIEW` BERILMAGAN — VA BU ONGLI QAROR.

    =======================================================================
    ⛔ BU «UNUTILGAN HUQUQ» EMAS (Pitfall 11 varianti A, UI-SPEC O-07).

    Platforma admini BOZORLARARO rol: u HAR BOZORNI ko'ra oladi. Unga
    hisobot yuzasini ochish HAR BOZORNING qarzdorlari ismini BITTA
    akkauntga to'plardi — ya'ni bitta sessiya butun platformaning
    shaxsiy ma'lumot xaritasiga aylanardi. Uning ishi bozorni QURISH
    (wizard) va PLATFORMA auditini o'qish; bozorning PULI va
    QARZDORLARI uning yuzasi emas.

    ⚠ SESSIYADA BOZOR TANLANGAN (`platform_admin_headers`), ya'ni 403
      AYNAN huquqdan keladi — `market_not_selected` dan emas. Bu farq
      test'ning butun ma'nosini ushlab turadi.
    =======================================================================
    """
    response = await api_client.get(url, params=_period(), headers=platform_admin_headers)

    assert response.status_code == 403, f"{url}: {response.status_code} — {response.text}"


# ===========================================================================
# 2. CROSS-TENANT — B NING DIREKTORI A NING QATORLARINI KO'RMAYDI (T-08-27)
# ===========================================================================


async def test_the_other_markets_director_never_sees_market_a_rows(
    api_client: httpx.AsyncClient,
    sync_owner_conn: Connection[TupleRow],
    reports: Env,
    director_headers: dict[str, str],
    market_b_director_headers: dict[str, str],
) -> None:
    """⛔ B bozorining direktori A ning DAVRINI so'raganda A ning izi CHIQMAYDI.

    =======================================================================
    ⛔ BU MATRITSA TESTINING TAKRORI EMAS — U BOSHQA NARSANI O'LCHAYDI.

    `test_cross_tenant.py` matritsasi `/reports/*` ni AVTOMATIK qamraydi,
    LEKIN u `from`/`to` majburiy query parametrlarini TO'LDIRMAYDI, ya'ni
    so'rov validatsiya darvozasida **422** bilan to'xtaydi va marshrut
    mantiqi UMUMAN ishlamaydi. Bu AYNAN `GET /reconciliation/hit-rate`
    ning holati va u ham `QUERY_PARAM_ROUTES` da YO'Q — istisno KERAK
    EMAS, chunki 422 matritsaning birorta da'vosini buzmaydi (tokensiz
    so'rov baribir 401 oladi, javobda B ning izi yo'q).

    ⛔ SHUNING UCHUN TENANT CHEGARASI SHU YERDA, PARAMETRLAR BILAN
       o'lchanadi — aks holda u HECH QAYERDA o'lchanmagan bo'lardi
       (`QUERY_PARAM_ROUTES` docstringidagi «boshqa joyda o'lchanishi
       SHART» talabining bajarilishi).
    =======================================================================

    ⚠ NAZORAT BIRINCHI: A ning direktori O'SHA davrda qatorni KO'RADI.
      Usiz test «hisobot umuman bo'sh» holatida ham yashil bo'lardi.
    """
    day = _last_closed_day()
    _seed_unpaid_charge(sync_owner_conn, reports, day=day)
    params = _period()

    control = await api_client.get(DEBTORS_URL, params=params, headers=director_headers)
    assert control.status_code == 200, control.text
    assert control.json()["rows"], (
        "nazorat: A ning direktori ham qator ko'rmadi — tenant da'vosi BO'SH-ROST bo'lardi"
    )

    foreign = await api_client.get(DEBTORS_URL, params=params, headers=market_b_director_headers)

    assert foreign.status_code == 200, foreign.text
    assert foreign.json()["rows"] == [], foreign.text
    assert foreign.json()["total_outstanding_soum"] == 0

    body = foreign.text
    for marker in (str(reports.vendor_id), str(reports.market_id)):
        assert marker not in body, f"B ning javobida A ning izi bor: {marker}"


# ===========================================================================
# 3. AUDIT — ⛔ BITTA SO'ROV = BITTA YOZUV, SOTUVCHI BOSHIGA EMAS (T-08-28)
# ===========================================================================


@pytest.mark.parametrize("vendor_count", [3, MANY_VENDORS], ids=["uch", "ikki-yuz"])
async def test_one_debtors_request_writes_exactly_one_audit_row(
    api_client: httpx.AsyncClient,
    tenant_session: TenantSessionFactory,
    reports: Env,
    director_headers: dict[str, str],
    debtors: DebtorFactory,
    vendor_count: int,
) -> None:
    """⛔⛔ SANOQ NATIJAGA BOG'LIQ EMAS — 3 QARZDORDA HAM, 200 DA HAM AYNAN 1.

    =======================================================================
    ⛔ NEGA IKKI HAJM O'LCHANADI (`MANY_VENDORS` docstringi).

    «Har sotuvchi uchun bitta yozuv» xatosi uch qarzdorda jurnalga UCH
    qator qo'yardi — sezilarli, lekin zararsiz ko'rinardi. 200 da esa u
    bitta so'rovda jurnalni 200 qator bilan to'ldirib, HAQIQIY o'qish
    hodisasini shovqin ostida ko'mardi (06 №9 da rad etilgan (a) yo'li).
    Ikki hajm birga o'lchanganda da'vo «bitta yozuv» dan «sanoq NATIJAGA
    BOG'LIQ EMAS» ga kuchayadi.
    =======================================================================

    ⚠ FON VAZIFASI KUTILMAYDI: `httpx.ASGITransport` `BackgroundTasks` ni
      javob qaytarilishidan OLDIN bajaradi (modul docstringi).
    """
    debtors(vendor_count)
    before = await _vendor_read_count(
        tenant_session, reports.market_id, reason="report_receivables"
    )

    response = await api_client.get(
        DEBTORS_URL, params=_period(days=vendor_count + 1), headers=director_headers
    )

    assert response.status_code == 200, response.text
    assert len(response.json()["rows"]) == vendor_count, (
        "nazorat: qarzdorlar ro'yxati kutilgan hajmda emas — sanoq BO'SH-ROST bo'lardi"
    )

    after = await _vendor_read_count(tenant_session, reports.market_id, reason="report_receivables")

    assert after - before == 1, (
        f"{vendor_count} qarzdorli so'rov {after - before} ta audit qatori yozdi — "
        "kutilgan AYNAN 1 (bitta so'rov = bitta o'qish hodisasi, D-09)"
    )


@pytest.mark.parametrize("url", [REVENUE_URL, ANOMALIES_URL], ids=["revenue", "anomalies"])
async def test_the_moneyless_reports_leave_no_vendor_read_trace(
    api_client: httpx.AsyncClient,
    tenant_session: TenantSessionFactory,
    reports: Env,
    director_headers: dict[str, str],
    url: str,
) -> None:
    """NAZORAT: audit AYNAN `/debtors` da bor va BOSHQA JOYDA yo'q.

    ⛔ USIZ YUQORIDAGI DA'VO «hamma hisobot yuzasiga audit yopishtirilgan»
       holatda ham yashil bo'lardi — o'shanda jurnal har tushum
       so'rovida qator olardi va D-09 yozuvi nizoni hal qilishga
       yaramay qolardi (`audit.py` da ATAYIN rad etilgan «blanket
       middleware» holatining aynan sinfi).

    Tushum va arxiv javoblarida SHAXSIY MAYDON YO'Q (rasta kodi, sana,
    summa, sinf nomi), ya'ni ularda `audit_read` ham bo'lmasligi kerak.
    """
    before = await _vendor_read_count(
        tenant_session, reports.market_id, reason="report_receivables"
    )

    response = await api_client.get(url, params=_period(), headers=director_headers)
    assert response.status_code == 200, response.text

    after = await _vendor_read_count(tenant_session, reports.market_id, reason="report_receivables")

    assert after == before, f"{url} sotuvchi o'qish auditini yozdi — jurnal shovqinga to'ladi"


# ===========================================================================
# 4. DAVR CHEGARASI — UCH XATO, UCH ALOHIDA KOD (T-08-30, Pitfall 13)
# ===========================================================================


@pytest.mark.parametrize("url", REPORT_URLS, ids=REPORT_IDS)
async def test_today_is_rejected_as_a_future_period(
    api_client: httpx.AsyncClient, reports: Env, director_headers: dict[str, str], url: str
) -> None:
    """⛔⛔ YUQORI CHEGARA **KECHA** — BUGUN 422 `report_period_future`.

    =======================================================================
    ⛔ BUGUN «KELAJAK» DEB ATALADI VA BU MEXANIK HAQIQAT.

    `daily_charges` D+1 04:10 da tug'iladi (`BILLING_CLOSE_CRON`, C-3).
    Bugunni qamragan hisobot bugungi PATTANI ko'rsatmasdi, lekin bugungi
    TO'LOVNI ko'rsatardi — natija KAM KO'RSATILGAN `charged_soum` va
    sun'iy musbat `diff_soum`. Va u EKRANDA QOLMASDI: aynan shu javob
    `.xlsx` bo'lib imzolanadigan varaqqa tushadi (UI-SPEC §1.2 qoida 1).
    =======================================================================

    ⚠ NAZORAT: KECHA o'sha marshrutdan O'TADI — aks holda test «marshrut
      har qanday davrni rad etadi» holatida ham yashil bo'lardi.
    """
    today = business_today().isoformat()
    rejected = await api_client.get(
        url, params={"from": today, "to": today}, headers=director_headers
    )

    assert rejected.status_code == 422, rejected.text
    assert rejected.json()["detail"] == "report_period_future", rejected.text

    yesterday = _last_closed_day().isoformat()
    accepted = await api_client.get(
        url, params={"from": yesterday, "to": yesterday}, headers=director_headers
    )
    assert accepted.status_code == 200, accepted.text


@pytest.mark.parametrize("url", REPORT_URLS, ids=REPORT_IDS)
async def test_a_reversed_period_is_rejected_with_its_own_code(
    api_client: httpx.AsyncClient, reports: Env, director_headers: dict[str, str], url: str
) -> None:
    """`from > to` -> 422 `report_period_invalid` — ⛔ ALOHIDA kod bilan.

    Uchala xatoni bitta kodga yig'ish ekranda YOLG'ON sabab ko'rsatardi
    va foydalanuvchi sanalarni joyini almashtirib ko'rib, xato
    takrorlanganda tizimni buzuq deb xulosa qilardi
    (`frontend/src/lib/report-errors.ts` ning sakkizinchi kod izohi).
    """
    to_date = _last_closed_day()
    response = await api_client.get(
        url,
        params={"from": to_date.isoformat(), "to": (to_date - timedelta(days=3)).isoformat()},
        headers=director_headers,
    )

    assert response.status_code == 422, response.text
    assert response.json()["detail"] == "report_period_invalid", response.text


@pytest.mark.parametrize("url", REPORT_URLS, ids=REPORT_IDS)
async def test_a_period_longer_than_the_limit_is_rejected(
    api_client: httpx.AsyncClient,
    reports: Env,
    director_headers: dict[str, str],
    test_settings: Settings,
    url: str,
) -> None:
    """`report_max_period_days` dan uzun davr -> 422 `report_period_too_long`.

    ⚠ CHEGARA `Settings` DAN O'QILADI, TESTDA TAKRORLANMAYDI: `366`
      qiymatini bu yerga yozish uni IKKI joyda saqlab qolardi va
      chegara o'zgarganda test o'zining eskirganini AYTMASDI.

    ⚠ NAZORAT: AYNAN chegaraga teng davr O'TADI — «>` va `>=` farqi
      shundagina o'lchanadi.
    """
    to_date = _last_closed_day()
    limit = test_settings.report_max_period_days

    too_long = await api_client.get(
        url,
        params={
            "from": (to_date - timedelta(days=limit)).isoformat(),
            "to": to_date.isoformat(),
        },
        headers=director_headers,
    )
    assert too_long.status_code == 422, too_long.text
    assert too_long.json()["detail"] == "report_period_too_long", too_long.text

    exact = await api_client.get(
        url,
        params={
            "from": (to_date - timedelta(days=limit - 1)).isoformat(),
            "to": to_date.isoformat(),
        },
        headers=director_headers,
    )
    assert exact.status_code == 200, exact.text


@pytest.mark.parametrize("url", REPORT_URLS, ids=REPORT_IDS)
async def test_a_period_over_the_row_limit_is_refused_not_truncated(
    api_client: httpx.AsyncClient,
    reports: Env,
    director_headers: dict[str, str],
    tiny_row_limit: None,
    url: str,
) -> None:
    """⛔⛔ CHEGARADAN OSHGAN JAVOB **RAD ETILADI**, JIMGINA KESILMAYDI.

    =======================================================================
    Kesilgan javob ekranda ham, faylda ham TO'LIQ ko'rinardi va direktor
    yetishmayotgan qatorlarni HECH QACHON sezmasdi — bu fazadagi eng
    qimmat nosozlik sinfi (UI-SPEC §1.2, §8.6). Rad javobi esa to'g'ri
    harakatni aytadi: «davrni qisqartiring».
    =======================================================================

    ⚠ Tushum hisobotida qator soni KUNLAR soniga teng (`generate_series`),
      ya'ni yetti kunlik davr chegarasi `1` bo'lgan holatda 7 qator
      berardi. Arxiv va reestr bo'sh bo'lishi mumkin — shuning uchun
      ular uchun ham qator SEED QILINADI emas, davr UZAYTIRILADI: chegara
      `row_count` ga qaraydi va tushumda u har doim noldan katta.
    """
    response = await api_client.get(url, params=_period(days=7), headers=director_headers)

    if url == REVENUE_URL:
        assert response.status_code == 422, response.text
        assert response.json()["detail"] == "report_too_large", response.text
        return

    # ⛔ Reestr va arxiv bo'sh davrni HALOL 200 bilan qaytaradi: `row_count`
    #    = 0 va u chegaradan oshmaydi. «Bo'sh javob ham rad etilsin» degan
    #    yumshatish chegarani NATIJAGA emas, SO'ROVGA bog'lardi.
    assert response.status_code == 200, response.text
    assert response.json()["row_count"] == 0


async def test_the_row_limit_counts_the_whole_period_not_the_page(
    api_client: httpx.AsyncClient,
    reports: Env,
    director_headers: dict[str, str],
    debtors: DebtorFactory,
    tiny_row_limit: None,
) -> None:
    """⛔ CHEGARA `row_count` GA QARAYDI — `limit` BILAN AYLANIB O'TILMAYDI.

    `?limit=1` bilan so'ralgan javobda BIR qator ko'rinardi, lekin
    davrda IKKI qator bor. Chegarani `shown_count` ga bog'lash
    «sahifalab olsam chegara yo'q» yo'lini ochardi va DoS bandi
    (T-08-30) mexanik ravishda bo'shab qolardi.
    """
    latest = _last_closed_day()
    debtors(2)

    response = await api_client.get(
        DEBTORS_URL,
        params={
            "from": (latest - timedelta(days=3)).isoformat(),
            "to": latest.isoformat(),
            "limit": "1",
        },
        headers=director_headers,
    )

    assert response.status_code == 422, response.text
    assert response.json()["detail"] == "report_too_large", response.text


# ===========================================================================
# 5. JAVOB TANASI — ISM BOR, TELEFON YO'Q, DALIL IDENTIFIKATOR (T-08-29)
# ===========================================================================


async def test_the_debtors_row_carries_the_name_and_never_the_phone(
    api_client: httpx.AsyncClient,
    sync_owner_conn: Connection[TupleRow],
    reports: Env,
    director_headers: dict[str, str],
) -> None:
    """⛔ `vendor_name` BOR (D-07), `phone` YO'Q (UI-SPEC O-03).

    =======================================================================
    IKKI DA'VO BITTA TESTDA VA ULAR AJRALMAS: «ism bor» yolg'iz o'zi
    yuzaning shaxsiy-ma'lumot yuzasiga aylanganini isbotlaydi;
    «telefon yo'q» yolg'iz o'zi bo'sh javobda ham rost bo'lardi. Birga
    ular AYNAN chegarani ko'rsatadi — hujjatga ISM tushadi, ALOQA
    ma'lumoti esa tushmaydi.
    =======================================================================

    ⚠ TANA O'LCHANADI, SXEMA EMAS (`_keys()` docstringi).
    """
    _seed_unpaid_charge(sync_owner_conn, reports, day=_last_closed_day())

    response = await api_client.get(DEBTORS_URL, params=_period(), headers=director_headers)

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["rows"], "nazorat: reestr bo'sh — ikkala da'vo ham BO'SH-ROST bo'lardi"
    assert payload["rows"][0]["vendor_name"], payload["rows"][0]

    leaked = _keys(payload) & PERSONAL_FIELDS
    assert leaked == set(), f"qarzdorlik javobida aloqa ma'lumoti bor: {sorted(leaked)}"


async def test_the_anomaly_row_carries_an_identifier_not_a_frame(
    api_client: httpx.AsyncClient,
    sync_owner_conn: Connection[TupleRow],
    reports: Env,
    director_headers: dict[str, str],
) -> None:
    """⛔ Dalil — IDENTIFIKATOR, KADR EMAS (07 D-03, T-06-81).

    Kadrda bozor TASHRIFCHILARINING yuzi bor (O'zR shaxsiy ma'lumotlar
    qonuni), ya'ni imzolangan havola ham, ombor kaliti ham javobga
    CHIQMAYDI. Klient identifikatorni MAVJUD, autentifikatsiya ostidagi
    kadr marshrutiga beradi.
    """
    day = _last_closed_day()
    charge_id = _seed_unpaid_charge(sync_owner_conn, reports, day=day)
    seed_case(sync_owner_conn, market_id=reports.market_id, service_date=day, charge_id=charge_id)

    response = await api_client.get(ANOMALIES_URL, params=_period(), headers=director_headers)

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["rows"], "nazorat: arxiv bo'sh — dalil da'vosi BO'SH-ROST bo'lardi"
    assert payload["unpaid_count"] == 1, payload
    assert payload["unregistered_count"] == 0, payload

    body = json.dumps(payload).lower()
    for marker in FORBIDDEN_EVIDENCE_MARKERS:
        assert marker not in body, f"arxiv javobida taqiqlangan belgi: {marker!r}"


@pytest.mark.parametrize("url", REPORT_URLS, ids=REPORT_IDS)
async def test_the_period_is_echoed_from_the_server(
    api_client: httpx.AsyncClient, reports: Env, director_headers: dict[str, str], url: str
) -> None:
    """⛔ `from_date`/`to_date` JAVOBDA — ekran davrni SERVERDAN chizadi (§8.7, G-39).

    So'ralgan davrni chizish «men oktyabrni so'radim, oktyabr
    ko'rsatildi» degan YOLG'ON tasdiq berardi. Bu ekranda tuzatiladigan,
    FAYLDA esa tarqaladigan xato.
    """
    params = _period()
    response = await api_client.get(url, params=params, headers=director_headers)

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["from_date"] == params["from"], payload
    assert payload["to_date"] == params["to"], payload


async def test_the_revenue_row_carries_the_server_computed_difference(
    api_client: httpx.AsyncClient,
    sync_owner_conn: Connection[TupleRow],
    reports: Env,
    director_headers: dict[str, str],
) -> None:
    """⛔ `diff_soum` SERVERDAN — klient `collected − charged` QILMAYDI (D-03).

    ⚠ BELGI KONVENSIYASI HAM O'LCHANADI: patta yozilgan, to'lov yo'q ->
      farq MANFIY. Belgi teskari bo'lsa ekran «ortiqcha to'lov» deb
      o'qirdi va direktor kam yig'ilgan kunni MUAMMOSIZ deb ko'rardi.
    """
    day = _last_closed_day()
    _seed_unpaid_charge(sync_owner_conn, reports, day=day)

    response = await api_client.get(REVENUE_URL, params=_period(), headers=director_headers)

    assert response.status_code == 200, response.text
    payload = response.json()
    charged_day = next(row for row in payload["rows"] if row["business_date"] == day.isoformat())

    assert charged_day["charged_soum"] == TARIFF_SOUM, charged_day
    assert charged_day["collected_soum"] == 0, charged_day
    assert charged_day["diff_soum"] == -TARIFF_SOUM, charged_day
    assert payload["total_charged_soum"] == TARIFF_SOUM, payload
    assert payload["total_collected_soum"] == 0, payload


# ===========================================================================
# 6. SAHIFALASH — YIG'INDI BUTUN DAVRNIKI, SANOQ EKRANNIKI (UI-SPEC §8.6)
# ===========================================================================


async def test_the_page_shrinks_but_the_period_totals_do_not(
    api_client: httpx.AsyncClient,
    reports: Env,
    director_headers: dict[str, str],
    debtors: DebtorFactory,
) -> None:
    """⛔⛔ `row_count` BUTUN DAVRNIKI, `shown_count` — SAHIFANIKI.

    =======================================================================
    ⛔ VA YIG'INDI SAHIFAGA ERGASHMAYDI.

    Ikki qarzdordan bittasi ko'rsatilganda `total_outstanding_soum`
    IKKALASINING yig'indisi bo'lib qoladi. Aks holda ekranda «Jami
    qarz» yozuvi ostida sahifadagi qatorlarning yig'indisi turardi va
    direktor uni BUTUN DAVR deb o'qirdi — usiz `reports.rowsShown`
    jumlasi ham ma'nosini yo'qotardi (§8.6).
    =======================================================================
    """
    latest = _last_closed_day()
    debtors(2)

    response = await api_client.get(
        DEBTORS_URL,
        params={
            "from": (latest - timedelta(days=3)).isoformat(),
            "to": latest.isoformat(),
            "limit": "1",
        },
        headers=director_headers,
    )

    assert response.status_code == 200, response.text
    payload = response.json()

    assert len(payload["rows"]) == 1, payload
    assert payload["shown_count"] == 1, payload
    assert payload["row_count"] == 2, payload
    assert payload["total_outstanding_soum"] == 2 * TARIFF_SOUM, payload


async def test_the_offset_walks_the_period_without_moving_the_totals(
    api_client: httpx.AsyncClient,
    reports: Env,
    director_headers: dict[str, str],
    debtors: DebtorFactory,
) -> None:
    """`offset` ikkinchi qatorni beradi va yig'indi O'ZGARMAYDI.

    ⚠ NAZORAT: ikki sahifadagi `vendor_id` lar FARQ QILADI — aks holda
      `offset` e'lon qilinib, JIMGINA e'tiborsiz qoldirilgan bo'lardi
      va test baribir yashil qolardi.
    """
    latest = _last_closed_day()
    debtors(2)

    params = {
        "from": (latest - timedelta(days=3)).isoformat(),
        "to": latest.isoformat(),
        "limit": "1",
    }
    first = await api_client.get(DEBTORS_URL, params=params, headers=director_headers)
    second = await api_client.get(
        DEBTORS_URL, params={**params, "offset": "1"}, headers=director_headers
    )

    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert first.json()["rows"][0]["vendor_id"] != second.json()["rows"][0]["vendor_id"]
    assert second.json()["row_count"] == 2
    assert second.json()["total_outstanding_soum"] == 2 * TARIFF_SOUM
