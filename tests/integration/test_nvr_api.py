"""NVR marshrutlarining API xulqi — CAM-01 va SC#4 ning ENDPOINT darajasidagi isboti.

=============================================================================
BU FAYL 03-04 NING REPOZITORIY TESTLARINI VA 03-05 NING ISAPI TESTLARINI
ALMASHTIRMAYDI — U ULARNING USTIGA QURILADI.

    test_nvr_repo.py       «upsert uch qoidani bajaradimi?»   (kirish QO'LDA)
    test_nvr_errors.py     «o'n ikki kod ajratiladimi?»       (kirish ISAPI'DAN)
    BU FAYL                «foydalanuvchi nima ko'radi?»      (kirish HTTP'DAN)

Uchtasi bir-birini almashtira olmaydi: repozitoriy testi 500 bilan
yiqiladigan endpointda ham YASHIL qolardi, ISAPI testi esa huquq
darvozasini umuman ko'rmaydi.
=============================================================================

⚠ NAVBAT BU YERDA CHAQIRILMAYDI. `POST /{id}/discover` ning javobi
(202 + `run_id`) va uning 409 poygasi — HTTP kontrakti; jobning O'ZI
`test_nvr_discovery_job.py` da o'lchanadi. Ikkalasini bir testga
qo'shish "202 keldi" ni "kashfiyot ishladi" dan ajratib bo'lmas holga
keltirardi.

⚠ `sim` MARKERI FAQAT `test-connection` TESTLARIDA. Qolgan marshrutlar
NVR ga umuman bormaydi, ya'ni ularni simulyator ortiga yashirish
to'plamni sababsiz sekinlashtirardi va `npm run test` da ular jimgina
o'tkazib yuborilardi (`fixtures/nvr_sim.py` ning skip qoidasi).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import uuid4

import pytest
from app.main import app as fastapi_app
from fixtures.admin_api import session_headers
from fixtures.nvr_domain import NVR_PORT, nvr_rows
from fixtures.nvr_sim import sim_attempts
from fixtures.two_markets import SEED_PASSWORD
from sqlalchemy import text
from tenancy.test_cross_tenant import all_routes

if TYPE_CHECKING:
    from collections.abc import Iterator

    import httpx
    from fastapi import FastAPI
    from fixtures import TenantSessionFactory
    from fixtures.nvr_domain import NvrDomainSeed
    from fixtures.two_markets import TwoMarketSeed
    from psycopg import Connection
    from psycopg.rows import TupleRow

pytestmark = pytest.mark.usefixtures("migrated")

NVR_URL = "/api/v1/nvr-devices"

PROBE_PASSWORD = "ParolHechQachonQaytmasin1"  # noqa: S105 - test uskunasi, sir emas
"""Parol darvozasining ZOND SATRI.

Qiymat ATAYIN uzun va o'ziga xos: qisqa satr (`"parol"`) javobning
istalgan joyidagi matnga tasodifan mos kelib YOLG'ON-QIZIL berardi.
"""

NEW_ADDRESS = "192.168.44.10:8080"
"""Seed'da UMUMAN uchramaydigan manzil (`fixtures/nvr_domain.A_HOST` bilan solishtiring)."""

PUBLIC_ADDRESS = "8.8.8.8"
"""Marshrutlanadigan OMMAVIY IP — SSRF darvozasining kirishi (T-03-23)."""

UNREACHABLE_ADDRESS = "127.0.0.1:1"
"""DARHOL rad etiladigan manzil — loopback, yopiq port.

Xususiylik darvozasidan O'TADI (loopback global emas) va TCP darajasida
`ECONNREFUSED` beradi, ya'ni test tarmoqni kutmaydi va simulyatorga
bog'lanmaydi.
"""

MINIMUM_COVERED_ROUTES = 6
"""Parol darvozasi QAMRAY OLADIGAN eng kam marshrut soni.

Ro'yxat qo'lda emas, `app.routes` dan yig'iladi — ya'ni yangi marshrut
qo'shilganda darvoza AVTOMATIK kengayadi. Quyi chegara esa teskari
xavfni yopadi: yurish buzilib bo'shab qolsa darvoza jimgina yashil
bo'lardi (`test_route_coverage.py` dagi bilan aynan bir xil qoida).
"""


# ---------------------------------------------------------------------------
# Sessiyalar va seed
# ---------------------------------------------------------------------------


@pytest.fixture
def nvr_seed(
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
) -> Iterator[NvrDomainSeed]:
    """`two_markets` ustiga NVR qatlami (`fixtures/nvr_domain.py`)."""
    with nvr_rows(sync_owner_conn, two_markets) as seed:
        yield seed


@pytest.fixture
async def manager_headers(
    api_client: httpx.AsyncClient,
    two_markets: TwoMarketSeed,
    nvr_seed: NvrDomainSeed,
) -> dict[str, str]:
    """A bozori adminining sessiyasi (`CAMERA_MANAGE` + `CAMERA_VIEW`).

    `nvr_seed` ATAYIN argument sifatida: qurilma sessiyadan OLDIN
    yozilishi kerak, aks holda birinchi so'rov bo'sh reestrni ko'rardi.
    """
    market_a = two_markets.market_a
    return await session_headers(api_client, market_a.admin_phone, market_a.admin_password)


@pytest.fixture
async def viewer_headers(
    api_client: httpx.AsyncClient,
    two_markets: TwoMarketSeed,
    nvr_seed: NvrDomainSeed,
) -> dict[str, str]:
    """A bozori DIREKTORI — `CAMERA_VIEW` bor, `CAMERA_MANAGE` YO'Q (D-15)."""
    return await session_headers(api_client, two_markets.market_a.director_phone, SEED_PASSWORD)


@pytest.fixture
def enqueued(api_app: FastAPI) -> Iterator[list[dict[str, Any]]]:
    """Navbatga qo'yishni YOZIB OLADI va haqiqiy brokerni chetlab o'tadi.

    ⚠ NEGA ALMASHTIRISH KERAK: modul darajasidagi `enqueue_discovery`
      compose tarmog'idagi `cache` ga qarab turadi, test esa O'Z Valkey
      konteynerida ishlaydi va u yerda hech qanday worker yo'q. Almashtirish
      nuqtasi — `app.state`, ya'ni `sessionmaker`/`cache`/`settings` bilan
      AYNAN bir xil mexanizm (yangi mexanizm kiritilmaydi).

    ⚠ TOZALASH MAJBURIY: `api_app` — modul darajasidagi YAGONA `app`
      obyekti, ya'ni qoldirilgan atribut boshqa test modullariga (masalan
      cross-tenant matritsasiga) sizib o'tardi.
    """
    calls: list[dict[str, Any]] = []

    async def _record(**kwargs: Any) -> None:
        calls.append(kwargs)

    api_app.state.enqueue_discovery = _record
    try:
        yield calls
    finally:
        del api_app.state.enqueue_discovery


def _create_payload(address: str = NEW_ADDRESS, password: str = PROBE_PASSWORD) -> dict[str, str]:
    return {"address": address, "username": "sbozor", "password": password}


# ---------------------------------------------------------------------------
# CAM-01 — qurilmani ro'yxatga olish
# ---------------------------------------------------------------------------


async def test_create_device_returns_the_passport_without_the_password(
    api_client: httpx.AsyncClient,
    manager_headers: dict[str, str],
) -> None:
    """201 + qurilma pasporti; `has_password` bor, `password` maydoni YO'Q (SC#4).

    Ikkita ALOHIDA da'vo va ikkalasi ham kerak: birinchisi "parol
    saqlandi" faktini tasdiqlaydi, ikkinchisi esa javob MODELIDA bunday
    maydon umuman e'lon qilinmaganini (`exclude=True` emas, T-03-39).
    """
    response = await api_client.post(NVR_URL, json=_create_payload(), headers=manager_headers)

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["host"] == "192.168.44.10"
    assert body["port"] == 8080
    assert body["use_tls"] is False
    assert body["has_password"] is True
    assert "password" not in body
    # Kashfiyotgacha pasport BO'SH — admin ularni QO'LDA kiritmaydi (D-01).
    assert body["model"] is None
    assert body["rtsp_port"] is None
    assert body["last_discovery_at"] is None


async def test_duplicate_address_is_a_conflict(
    api_client: httpx.AsyncClient,
    manager_headers: dict[str, str],
    nvr_seed: NvrDomainSeed,
) -> None:
    """Seed'dagi `host:port` ikkinchi marta qo'shilganda **409** `nvr_host_taken`."""
    payload = _create_payload(address=f"{nvr_seed.market_a.host}:{NVR_PORT}")

    response = await api_client.post(NVR_URL, json=payload, headers=manager_headers)

    assert response.status_code == 409, response.text
    assert response.json()["detail"] == "nvr_host_taken"


async def test_public_address_is_blocked(
    api_client: httpx.AsyncClient,
    manager_headers: dict[str, str],
) -> None:
    """Ommaviy IP **422** `nvr_host_public_blocked` (T-03-23).

    Bu KONFIGURATSIYA tekshiruvi emas, SSRF chegarasi: serverning o'zi
    `nvr_devices.host` ga yozilgan manzilga Digest so'rov yuboradi.
    """
    response = await api_client.post(
        NVR_URL, json=_create_payload(address=PUBLIC_ADDRESS), headers=manager_headers
    )

    assert response.status_code == 422, response.text
    assert response.json()["detail"] == "nvr_host_public_blocked"


async def test_unparseable_address_has_its_own_code(
    api_client: httpx.AsyncClient,
    manager_headers: dict[str, str],
) -> None:
    """Yaroqsiz sxema **422** `nvr_address_invalid` — ommaviy IP dan ALOHIDA kod.

    NAZORAT BANDI yuqoridagi test bilan juftlikda: ikkala holat ham 422
    beradi, lekin `detail` FARQ QILADI. Bitta kod bo'lganda admin
    "manzilni tuzating" o'rniga "tunnel ichidagi manzilni toping" degan
    butunlay noto'g'ri maslahat olardi (03-04 ning ochiq talabi).
    """
    response = await api_client.post(
        NVR_URL, json=_create_payload(address="rtsp://192.168.1.64"), headers=manager_headers
    )

    assert response.status_code == 422, response.text
    assert response.json()["detail"] == "nvr_address_invalid"


async def test_camera_viewer_cannot_add_a_device(
    api_client: httpx.AsyncClient,
    viewer_headers: dict[str, str],
) -> None:
    """Direktor (`CAMERA_VIEW` bor, `CAMERA_MANAGE` yo'q) **403** oladi.

    Nazorat bandi keyingi testda: o'sha sessiya `GET` da 200 oladi, ya'ni
    403 sessiyaning umumiy yaroqsizligidan emas, AYNAN huquqdan.
    """
    response = await api_client.post(NVR_URL, json=_create_payload(), headers=viewer_headers)

    assert response.status_code == 403, response.text


async def test_camera_viewer_can_read_the_list(
    api_client: httpx.AsyncClient,
    viewer_headers: dict[str, str],
    nvr_seed: NvrDomainSeed,
) -> None:
    """NAZORAT BANDI: o'sha direktor sessiyasi ro'yxatni KO'RADI."""
    response = await api_client.get(NVR_URL, headers=viewer_headers)

    assert response.status_code == 200, response.text
    items = response.json()["items"]
    assert [item["id"] for item in items] == [str(nvr_seed.market_a.nvr_id)]
    assert items[0]["has_password"] is True


async def test_list_shows_only_this_market(
    api_client: httpx.AsyncClient,
    manager_headers: dict[str, str],
    nvr_seed: NvrDomainSeed,
) -> None:
    """A bozorining ro'yxatida B bozorining qurilmasi YO'Q.

    Pozitiv qism ham majburiy: bo'sh ro'yxat ham "izolyatsiya ishladi"
    kabi ko'rinardi va hech nimani isbotlamasdi.
    """
    response = await api_client.get(NVR_URL, headers=manager_headers)

    assert response.status_code == 200, response.text
    ids = {item["id"] for item in response.json()["items"]}
    assert str(nvr_seed.market_a.nvr_id) in ids
    assert str(nvr_seed.market_b.nvr_id) not in ids


async def test_patch_updates_the_isapi_username(
    api_client: httpx.AsyncClient,
    manager_headers: dict[str, str],
    nvr_seed: NvrDomainSeed,
) -> None:
    """`PATCH` foydalanuvchi nomini yangilaydi va pasportning qolganiga tegmaydi."""
    url = f"{NVR_URL}/{nvr_seed.market_a.nvr_id}"

    response = await api_client.patch(url, json={"username": "yangi"}, headers=manager_headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["username"] == "yangi"
    assert body["host"] == nvr_seed.market_a.host
    assert body["has_password"] is True


async def test_cross_tenant_device_is_not_found(
    api_client: httpx.AsyncClient,
    manager_headers: dict[str, str],
    nvr_seed: NvrDomainSeed,
) -> None:
    """B bozorining `nvr_id` si bilan `PATCH` **404** (403 EMAS, T-03-40)."""
    url = f"{NVR_URL}/{nvr_seed.market_b.nvr_id}"

    response = await api_client.patch(url, json={"username": "yangi"}, headers=manager_headers)

    assert response.status_code != 403, "403 obyekt MAVJUDLIGINI tasdiqlardi"
    assert response.status_code == 404, response.text


# ---------------------------------------------------------------------------
# SC#4 — parol
# ---------------------------------------------------------------------------


async def test_password_update_leaves_a_valueless_audit_row(
    api_client: httpx.AsyncClient,
    manager_headers: dict[str, str],
    nvr_seed: NvrDomainSeed,
    tenant_session: TenantSessionFactory,
) -> None:
    """Parol almashtirish 204 beradi va auditda QIYMATSIZ iz qoldiradi.

    `nvr_credentials` DB triggeridan butunlay chiqarilgan (T-03-13), ya'ni
    yozuvni ILOVA qatlami qoldiradi va u faqat FAKTNI yozadi. Test ikki
    tomonlama: yozuv BOR va unda parol YO'Q.
    """
    rows = nvr_seed.market_a
    url = f"{NVR_URL}/{rows.nvr_id}/password"

    body = {"password": PROBE_PASSWORD}
    response = await api_client.post(url, json=body, headers=manager_headers)

    assert response.status_code == 204, response.text
    assert not response.content

    async with tenant_session(rows.market_id) as session:
        result = await session.execute(
            text(
                "SELECT new_value::text AS payload FROM audit_log "
                "WHERE market_id = :market_id AND table_name = 'nvr_devices' "
                "  AND source = 'app' AND row_id = :nvr_id"
            ),
            {"market_id": rows.market_id, "nvr_id": rows.nvr_id},
        )
        payloads = [row.payload for row in result]

    assert payloads, "parol almashtirish auditda iz qoldirmadi"
    assert any("credentials_updated" in payload for payload in payloads)
    assert all(PROBE_PASSWORD not in payload for payload in payloads)


async def test_password_never_in_any_response(
    api_client: httpx.AsyncClient,
    manager_headers: dict[str, str],
    nvr_seed: NvrDomainSeed,
    enqueued: list[dict[str, Any]],
) -> None:
    """PAROL DARVOZASI: har bir NVR marshrutining XOM javobida zond satri YO'Q.

    =======================================================================
    RO'YXAT QO'LDA EMAS — U `app.routes` DAN YIG'ILADI.

    Qo'lda yozilgan ro'yxatga yangi marshrutni kim qo'shishi kerak edi?
    Hech kim — va u darvozadan TASHQARIDA qolardi, hech qanday test
    qizarmasdan. Avtomatik ro'yxat esa uni o'sha kuniyoq qamrab oladi.

    ⚠ XOM TANA TEKSHIRILADI (`response.text`), parse qilingan JSON emas:
      parol javobga sarlavhada, xato matnida yoki ichma-ich obyektda ham
      tushishi mumkin va JSON kaliti bo'yicha qidiruv ularning HECH
      BIRINI ko'rmasdi.
    =======================================================================
    """
    rows = nvr_seed.market_a
    device_url = f"{NVR_URL}/{rows.nvr_id}"

    # Zond paroli AVVAL bazaga yoziladi: darvoza "javobda uchramadi" ni
    # "hech qayerda saqlanmagan" dan ajrata olishi kerak.
    stored = await api_client.post(NVR_URL, json=_create_payload(), headers=manager_headers)
    assert stored.status_code == 201, stored.text
    new_id = stored.json()["id"]

    discover = await api_client.post(f"{device_url}/discover", headers=manager_headers)
    assert discover.status_code == 202, discover.text
    run_id = discover.json()["run_id"]

    responses: dict[str, httpx.Response] = {
        "POST /api/v1/nvr-devices": stored,
        "GET /api/v1/nvr-devices": await api_client.get(NVR_URL, headers=manager_headers),
        "POST /api/v1/nvr-devices/test-connection": await api_client.post(
            f"{NVR_URL}/test-connection",
            json=_create_payload(address=UNREACHABLE_ADDRESS),
            headers=manager_headers,
        ),
        "PATCH /api/v1/nvr-devices/{nvr_id}": await api_client.patch(
            f"{NVR_URL}/{new_id}", json={"username": "zond"}, headers=manager_headers
        ),
        "POST /api/v1/nvr-devices/{nvr_id}/password": await api_client.post(
            f"{device_url}/password", json={"password": PROBE_PASSWORD}, headers=manager_headers
        ),
        "POST /api/v1/nvr-devices/{nvr_id}/discover": discover,
        "GET /api/v1/nvr-devices/{nvr_id}/discovery-runs/{run_id}": await api_client.get(
            f"{device_url}/discovery-runs/{run_id}", headers=manager_headers
        ),
    }

    declared = {route.path for route in all_routes(fastapi_app) if route.path.startswith(NVR_URL)}
    covered = {name.split(" ", 1)[1] for name in responses}
    assert declared <= covered, (
        f"quyidagi NVR marshrutlari parol darvozasidan TASHQARIDA: {sorted(declared - covered)}"
    )
    assert len(covered) >= MINIMUM_COVERED_ROUTES, (
        f"darvoza atigi {len(covered)} marshrutni qamrab oldi — `app.routes` yurishi buzilgan"
    )

    for name, response in responses.items():
        assert PROBE_PASSWORD not in response.text, f"{name}: parol javob tanasida sizib chiqdi"


# ---------------------------------------------------------------------------
# CAM-08 — kashfiyotning HTTP kontrakti
# ---------------------------------------------------------------------------


async def test_discover_returns_202_and_enqueues_the_four_ids(
    api_client: httpx.AsyncClient,
    manager_headers: dict[str, str],
    nvr_seed: NvrDomainSeed,
    enqueued: list[dict[str, Any]],
) -> None:
    """**202** + `run_id`, va navbatga AYNAN to'rtta identifikator ketadi.

    `market_id` navbat xabarida BO'LISHI SHART: worker'da so'rov yo'q,
    ya'ni u tenant kontekstini boshqa hech qayerdan ololmaydi
    (Pitfall 13).
    """
    rows = nvr_seed.market_a

    response = await api_client.post(f"{NVR_URL}/{rows.nvr_id}/discover", headers=manager_headers)

    assert response.status_code == 202, response.text
    run_id = response.json()["run_id"]

    assert len(enqueued) == 1
    assert enqueued[0]["market_id"] == rows.market_id
    assert enqueued[0]["nvr_id"] == rows.nvr_id
    assert str(enqueued[0]["run_id"]) == run_id
    assert enqueued[0]["actor_id"] is not None


async def test_second_discover_returns_409_with_the_existing_run_id(
    api_client: httpx.AsyncClient,
    manager_headers: dict[str, str],
    nvr_seed: NvrDomainSeed,
    enqueued: list[dict[str, Any]],
) -> None:
    """Ikkinchi kashfiyot **409** va javob tanasida MAVJUD `run_id` (UI-SPEC §5.6 [TALAB]).

    ⚠ `run_id` SIZ 409 UI'ni ikkinchi so'rovga majbur qilardi — poyga
      holatining o'zida yana bitta poyga. Shuning uchun bu yerda ikkita
      alohida da'vo: status 409 VA tanadagi identifikator BIRINCHI
      yugurishnikiga TENG.
    """
    url = f"{NVR_URL}/{nvr_seed.market_a.nvr_id}/discover"

    first = await api_client.post(url, headers=manager_headers)
    second = await api_client.post(url, headers=manager_headers)

    assert first.status_code == 202, first.text
    assert second.status_code == 409, second.text
    body = second.json()["detail"]
    assert body["detail"] == "discovery_already_running"
    assert body["run_id"] == first.json()["run_id"]
    # Ikkinchi so'rov navbatga HECH NIMA qo'ymaydi — aks holda NVR ga
    # ikki barobar borish qaytib kelardi (T-03-16).
    assert len(enqueued) == 1


async def test_discovery_run_poll_reports_the_queued_state(
    api_client: httpx.AsyncClient,
    manager_headers: dict[str, str],
    nvr_seed: NvrDomainSeed,
    enqueued: list[dict[str, Any]],
) -> None:
    """Poll `queued` holatini va `channels_found = None` ni qaytaradi.

    ⚠ `channels_found` NING `None` BO'LISHI — S2a va S2b ni ajratadigan
      YAGONA belgi (UI-SPEC §5.2). Nolga tenglashtirish "0 ta kanal
      topildi" degan YOLG'ON natija berardi.
    """
    rows = nvr_seed.market_a
    started = await api_client.post(f"{NVR_URL}/{rows.nvr_id}/discover", headers=manager_headers)
    run_id = started.json()["run_id"]

    response = await api_client.get(
        f"{NVR_URL}/{rows.nvr_id}/discovery-runs/{run_id}", headers=manager_headers
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "queued"
    assert body["channels_found"] is None
    assert body["finished_at"] is None
    assert body["error_code"] is None


async def test_run_of_another_device_is_not_found(
    api_client: httpx.AsyncClient,
    manager_headers: dict[str, str],
    nvr_seed: NvrDomainSeed,
    enqueued: list[dict[str, Any]],
) -> None:
    """Yugurish BOSHQA qurilmaning yo'li ostida so'ralganda **404**.

    Yo'l qurilma ostida yashaydi, ya'ni `{nvr_id}` shunchaki bezak emas —
    u tekshiriladigan qism. Usiz bitta bozor ichida istalgan yugurishni
    istalgan qurilma yo'li bilan o'qish mumkin bo'lardi.
    """
    rows = nvr_seed.market_a
    started = await api_client.post(f"{NVR_URL}/{rows.nvr_id}/discover", headers=manager_headers)
    run_id = started.json()["run_id"]

    response = await api_client.get(
        f"{NVR_URL}/{uuid4()}/discovery-runs/{run_id}", headers=manager_headers
    )

    assert response.status_code == 404, response.text


async def test_enqueue_failure_leaves_no_active_run_behind(
    api_client: httpx.AsyncClient,
    api_app: FastAPI,
    manager_headers: dict[str, str],
    nvr_seed: NvrDomainSeed,
    tenant_session: TenantSessionFactory,
    enqueued: list[dict[str, Any]],
) -> None:
    """Navbat yiqilsa FAOL yugurish qolmaydi va keyingi urinish ISHLAYDI.

    =======================================================================
    BU EDGE CASE EMAS — U TIZIMNI QULFLAB QO'YADIGAN YAGONA YO'L.

    `0012` dagi QISMAN UNIQUE indeks `status IN ('queued','running')`
    ustida. Navbatga tushmagan `queued` qator shu NVR uchun HAR QANDAY
    keyingi kashfiyotni MANGU bloklardi va foydalanuvchi uni "tugma
    ishlamay qoldi" deb ko'rardi.

    Yechim — KOMPENSATSIYA EMAS, ROLLBACK: istisno `get_tenant_session`
    ning `session.begin()` blokidan chiqib, `create_run` INSERT'ini ham
    olib ketadi. `finish_run(failed)` yozishga urinish o'sha rollback
    bilan birga yo'qolardi va faqat "yozdik" degan yolg'on xotirjamlik
    qolardi (bu AVVAL YOZILGAN va TEST BILAN O'LCHANGAN xato).

    NAZORAT BANDI (ikkinchi yarim) MAJBURIY: faqat "faol qator yo'q"
    da'vosi yozuvning UMUMAN ishlamayotganini ham "muvaffaqiyat" deb
    ko'rsatardi. Shuning uchun keyingi urinish 202 olishi tekshiriladi.
    =======================================================================
    """
    rows = nvr_seed.market_a

    async def _explode(**_: Any) -> None:
        raise ConnectionError("navbat yiqildi")

    # ⚠ YOZUVCHI TIKLANADI, O'CHIRILMAYDI. `del` bilan olib tashlansa
    #   marshrut MODUL darajasidagi `enqueue_discovery` ga tushardi va u
    #   compose tarmog'idagi HAQIQIY Valkey'ga yozardi — test o'zi
    #   o'lchayotgan narsani chetlab o'tib, ustiga yon ta'sir qoldirardi.
    recorder = api_app.state.enqueue_discovery
    api_app.state.enqueue_discovery = _explode
    try:
        response = await api_client.post(
            f"{NVR_URL}/{rows.nvr_id}/discover", headers=manager_headers
        )
    finally:
        api_app.state.enqueue_discovery = recorder

    assert response.status_code == 503, response.text
    assert response.json()["detail"] == "discovery_internal_error"

    async with tenant_session(rows.market_id) as session:
        result = await session.execute(
            text(
                "SELECT count(*) FROM nvr_discovery_runs "
                "WHERE market_id = :market_id AND nvr_id = :nvr_id "
                "  AND status IN ('queued', 'running')"
            ),
            {"market_id": rows.market_id, "nvr_id": rows.nvr_id},
        )
        active = int(result.scalar_one())

    assert active == 0, "yugurish FAOL holatda qoldi — keyingi kashfiyot mangu bloklanardi"

    # NAZORAT BANDI: navbat tiklanganda tugma ISHLAYDI.
    retry = await api_client.post(f"{NVR_URL}/{rows.nvr_id}/discover", headers=manager_headers)
    assert retry.status_code == 202, retry.text
    assert len(enqueued) == 1


# ---------------------------------------------------------------------------
# CAM-01 — «ulanishni tekshirish» (simulyator ustida)
# ---------------------------------------------------------------------------


@pytest.mark.sim
async def test_test_connection_reports_the_device_and_writes_nothing(
    api_client: httpx.AsyncClient,
    manager_headers: dict[str, str],
    nvr_seed: NvrDomainSeed,
    sim: str,
    sim_credentials: tuple[str, str],
    tenant_session: TenantSessionFactory,
) -> None:
    """Muvaffaqiyatli tekshiruv TO'RTTA maydonni beradi va YOZUV YARATMAYDI.

    UI-SPEC §4.5 to'rttasini ham MAJBURIY deb belgilaydi: kanallar soni
    adminning "to'g'ri qurilmaga ulandimmi?" savoliga yagona javobi,
    soat farqi esa 300 s dan kichik bo'lsa ham ko'rsatiladi.

    "Yozuv yaratmaydi" da'vosi SANOQ bilan o'lchanadi, natijadan emas:
    javobning shakli qator yozilgan holatda ham AYNAN bir xil bo'lardi.
    """
    username, password = sim_credentials
    before = await _device_count(tenant_session, nvr_seed.market_a.market_id)

    response = await api_client.post(
        f"{NVR_URL}/test-connection",
        json={"address": sim, "username": username, "password": password},
        headers=manager_headers,
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["ok"] is True
    assert body["model"] == "DS-7616NI-K2"
    assert body["device_type"] == "NVR"
    assert body["channels_preview"] == 6
    assert body["clock_drift_seconds"] is not None
    assert body["auth_locked"] is False

    assert await _device_count(tenant_session, nvr_seed.market_a.market_id) == before


@pytest.mark.sim
async def test_test_connection_names_the_reason_without_an_http_error(
    api_client: httpx.AsyncClient,
    manager_headers: dict[str, str],
    nvr_seed: NvrDomainSeed,
    sim: str,
    sim_credentials: tuple[str, str],
) -> None:
    """Noto'g'ri parol **200** + `ok=false` + kod + `auth_locked` beradi (D-02/§4.4).

    ⚠ HTTP XATOSI EMAS VA BU ATAYIN: TanStack Query 4xx/5xx ni tarmoq
      nosozligi deb QAYTA URINARDI, qayta urinish esa qurilmaning
      qulflash hisoblagichini oshirardi — aynan D-03 taqiqlagan xulq.
    """
    username, _ = sim_credentials

    response = await api_client.post(
        f"{NVR_URL}/test-connection",
        json={"address": sim, "username": username, "password": "notogri-parol"},
        headers=manager_headers,
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["ok"] is False
    assert body["error_code"] == "nvr_bad_credentials"
    assert body["auth_locked"] is True
    assert body["model"] is None


@pytest.mark.sim
async def test_rate_limit_blocks_before_the_request_reaches_the_device(
    api_client: httpx.AsyncClient,
    manager_headers: dict[str, str],
    nvr_seed: NvrDomainSeed,
    sim: str,
    sim_credentials: tuple[str, str],
) -> None:
    """Chegaradan oshgan so'rov **429** oladi va QURILMAGA BORMAYDI (T-03-37).

    =======================================================================
    «BORMADI» DA'VOSINING YAGONA DALILI — URINISHLAR SANOG'I.

    Natijadan o'lchab bo'lmaydi: chaqirib, javobni tashlab yuborgan kod
    ham aynan bir xil 429 berardi. Sanoq esa qurilmaning O'Z hisoblagichi
    va aynan u Hikvision'ni 30 daqiqaga qulflaydi.
    =======================================================================
    """
    username, _ = sim_credentials
    payload = {"address": sim, "username": username, "password": "notogri-parol"}
    url = f"{NVR_URL}/test-connection"

    statuses = [
        (await api_client.post(url, json=payload, headers=manager_headers)).status_code
        for _ in range(3)
    ]
    attempts_before_block = sim_attempts(sim)

    blocked = await api_client.post(url, json=payload, headers=manager_headers)

    assert statuses == [200, 200, 200], statuses
    assert blocked.status_code == 429, blocked.text
    assert blocked.json()["detail"] == "too_many_attempts"
    assert sim_attempts(sim) == attempts_before_block, (
        "chegaradan oshgan so'rov QURILMAGA yetib bordi — sanoq o'sdi"
    )


async def _device_count(tenant_session: TenantSessionFactory, market_id: Any) -> int:
    async with tenant_session(market_id) as session:
        result = await session.execute(
            text("SELECT count(*) FROM nvr_devices WHERE market_id = :market_id"),
            {"market_id": market_id},
        )
        return int(result.scalar_one())
