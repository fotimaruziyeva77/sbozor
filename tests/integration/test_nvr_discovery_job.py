"""Kashfiyot fon-vazifasi — Pitfall 13 ning O'LCHOVI va SC#1 ning uchidan-uchiga isboti.

=============================================================================
TEST WORKER KONTEYNERINI KUTMAYDI — U JOBNI FUNKSIYA SIFATIDA CHAQIRADI.

`discover_nvr` — sof `async def` (D-06), ya'ni uni chaqirish uchun na
broker, na worker jarayoni kerak. Bu D-06 ning BUTUN MAQSADI va shu
bilan birga eng amaliy foydasi: navbatning tarmoq qismi testdan chiqadi,
o'lchanadigan narsa esa KASHFIYOT MANTIG'I bo'lib qoladi.

Navbatning O'ZI alohida, bitta testda o'lchanadi
(`test_enqueue_puts_the_four_identifiers_on_the_queue`) va u HAQIQIY
Valkey ustida ishlaydi.
=============================================================================

=============================================================================
NEGA SESSIYA FABRIKASI `api_sessionmaker` — VA BU O'LCHANGAN TANLOV.

`app_sessionmaker` `app_engine` ustida quriladi, u esa ATAYIN
`pool_size=1, max_overflow=0` (GUC sizishini ochib berish uchun,
`tests/conftest.py`). Kashfiyot jobi esa AYNI PAYTDA IKKI ulanish
talab qiladi:

    1. uzun tranzaksiya  — ISAPI muloqoti va yakuniy `upsert`
    2. qisqa tranzaksiya — `channels_found` ning oraliq yozuvi

Bitta ulanishli pulda ikkinchisi birinchisini kutib DEADLOCK berardi va
sabab "job osilib qoldi" bo'lib ko'rinardi — tenant konteksti kabi
butunlay boshqa joyda qidirilardi. `api_sessionmaker` standart pul
o'lchamiga ega va u aynan shu sababdan mavjud.
=============================================================================
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import uuid4

import pytest
from app.jobs import discovery as discovery_job
from app.jobs.discovery import discover_nvr
from app.repositories.nvr_repo import NvrRepository
from app.security.secrets import encrypt_nvr_password
from app.worker import DISCOVERY_QUEUE, enqueue_discovery
from fixtures.nvr_domain import nvr_rows
from fixtures.nvr_sim import sim_state
from sbozor_core.enums import ActorKind
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from taskiq_redis import ListQueueBroker

if TYPE_CHECKING:
    from collections.abc import AsyncIterator
    from uuid import UUID

    from fixtures import TenantSessionFactory
    from fixtures.nvr_domain import MarketNvrRows
    from fixtures.two_markets import TwoMarketSeed
    from psycopg import Connection
    from psycopg.rows import TupleRow
    from redis.asyncio import Redis
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

pytestmark = [pytest.mark.sim, pytest.mark.usefixtures("migrated")]

SIM_CHANNEL_COUNT = 6
"""D-09: CI'da 6 kanal (`DS-7616NI-K2` fixture'iga mos)."""

SEEDED_CHANNELS = 3
"""Seed A bozorida 3 kanal yozadi (`fixtures/nvr_domain.A_CAMERA_CHANNELS`).

Ya'ni birinchi skan 6 tasini KO'RADI va 3 tasini QO'SHADI. Sonlar
farqli bo'lgani ataylab: teng bo'lsa `channels_found` bilan
`channels_added` ning FARQI umuman sinalmasdi.
"""


async def _prepare(
    sessionmaker: async_sessionmaker[AsyncSession],
    rows: MarketNvrRows,
    sim: str,
    credentials: tuple[str, str],
) -> None:
    """Seed qatorini SIMULYATORGA qaratadi va HAQIQIY shifrlangan parol yozadi.

    Ikki qadam ham majburiy va ikkalasi ham seed'ning ochiq
    soddalashtirishini tuzatadi:

      * seed `port = 80` yozadi (`nvr_devices.port` ning standarti), sim
        esa boshqa portda tinglaydi — job manzilni FAQAT bazadan quradi,
        ya'ni tuzatish o'sha yerda bo'lishi kerak;
      * seed `password_encrypted` ga ATAYIN Fernet BO'LMAGAN bayt yozadi
        (`NVR_PASSWORD_PLACEHOLDER`) — u faqat ustunning mavjudligini
        sinaydi. Job esa uni haqiqatan deshifrlaydi.

    Manzilning bazadan qurilishi — SC#7 ning ("real qurilmaga o'tish —
    sozlama o'zgarishi, kod o'zgarishi emas") bevosita o'lchovi.
    """
    _, password = credentials
    host, port = _split_sim_url(sim)

    async with sessionmaker() as session, session.begin():
        await _set_tenant(session, rows.market_id)
        repo = NvrRepository(session, rows.market_id)
        await repo.update_device(rows.nvr_id, host=host, port=port, username=credentials[0])
        await repo.put_credential(rows.nvr_id, encrypt_nvr_password(password), 1)


def _split_sim_url(sim: str) -> tuple[str, int]:
    """`http://<host>:<port>` -> `(host, port)`."""
    remainder = sim.split("://", 1)[-1]
    host, _, port = remainder.partition(":")
    return host, int(port or 80)


async def _set_tenant(session: AsyncSession, market_id: UUID) -> None:
    from sbozor_core.tenancy import set_tenant_context

    await set_tenant_context(
        session,
        market_id=market_id,
        actor_id=None,
        request_id="pytest",
        actor_kind=ActorKind.SYSTEM,
    )


async def _create_run(sessionmaker: async_sessionmaker[AsyncSession], rows: MarketNvrRows) -> UUID:
    """API qatlami qiladigan ishni takrorlaydi: `queued` qatorini yozadi."""
    async with sessionmaker() as session, session.begin():
        await _set_tenant(session, rows.market_id)
        return await NvrRepository(session, rows.market_id).create_run(rows.nvr_id)


async def _run_row(
    tenant_session: TenantSessionFactory, market_id: UUID, run_id: UUID
) -> dict[str, Any]:
    async with tenant_session(market_id) as session:
        result = await session.execute(
            text(
                "SELECT status, channels_found, channels_added, channels_marked_offline, "
                "       finished_at, error_code, error_detail::text AS detail "
                "FROM nvr_discovery_runs WHERE market_id = :market_id AND id = :run_id"
            ),
            {"market_id": market_id, "run_id": run_id},
        )
        return dict(result.one()._mapping)


async def _camera_count(tenant_session: TenantSessionFactory, market_id: UUID, nvr_id: UUID) -> int:
    async with tenant_session(market_id) as session:
        result = await session.execute(
            text("SELECT count(*) FROM cameras WHERE market_id = :market_id AND nvr_id = :nvr_id"),
            {"market_id": market_id, "nvr_id": nvr_id},
        )
        return int(result.scalar_one())


@pytest.fixture
async def prepared(
    api_sessionmaker: async_sessionmaker[AsyncSession],
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    sim: str,
    sim_credentials: tuple[str, str],
) -> AsyncIterator[MarketNvrRows]:
    """Sim'ga qaratilgan, haqiqiy parolli A bozori qurilmasi."""
    with nvr_rows(sync_owner_conn, two_markets) as seed:
        await _prepare(api_sessionmaker, seed.market_a, sim, sim_credentials)
        yield seed.market_a


# ---------------------------------------------------------------------------
# SC#1 — manzil va parol -> kameralar
# ---------------------------------------------------------------------------


async def test_discovery_job_walks_queued_to_succeeded(
    api_sessionmaker: async_sessionmaker[AsyncSession],
    tenant_session: TenantSessionFactory,
    prepared: MarketNvrRows,
) -> None:
    """`queued` -> `succeeded`, sonlar to'liq va `finished_at` to'ldirilgan.

    Bu SC#1 ning uchidan-uchiga o'lchovi: kirish — bazadagi manzil va
    shifrlangan parol; chiqish — HAQIQIY kamera qatorlari. Oradagi
    hech nima (XML, Digest, namespace, `deviceType` tarmoqlanishi)
    testda taqlid qilinmaydi.
    """
    run_id = await _create_run(api_sessionmaker, prepared)

    await discover_nvr(
        api_sessionmaker,
        market_id=prepared.market_id,
        nvr_id=prepared.nvr_id,
        run_id=run_id,
        actor_id=None,
    )

    row = await _run_row(tenant_session, prepared.market_id, run_id)
    assert row["status"] == "succeeded", row
    assert row["channels_found"] == SIM_CHANNEL_COUNT
    assert row["channels_added"] == SIM_CHANNEL_COUNT - SEEDED_CHANNELS
    assert row["finished_at"] is not None
    assert row["error_code"] is None

    assert await _camera_count(tenant_session, prepared.market_id, prepared.nvr_id) == (
        SIM_CHANNEL_COUNT
    )


async def test_worker_sets_tenant_context(
    api_sessionmaker: async_sessionmaker[AsyncSession],
    tenant_session: TenantSessionFactory,
    prepared: MarketNvrRows,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """PITFALL 13 NING O'LCHOVI — IKKI TOMONLAMA (T-03-38).

    =======================================================================
    NAZORAT HOLATI MAJBURIY VA U BIRINCHI KELADI.

    Kontekstsiz chaqirilgan job:
      * HECH QANDAY istisno ko'tarmaydi,
      * yugurish qatoriga HECH NIMA yozmaydi (u `queued` bo'lib qoladi),
      * BIRORTA kamera yaratmaydi.

    Ya'ni nosozlik JIMGINA — jurnalda ham, javobda ham, bazada ham "xato"
    degan so'z yo'q. Aynan shuning uchun bu naqsh alohida test bilan
    qulflanadi: uni faqat "kamera soni o'zgarmadi" bilan ushlash mumkin.

    Kontekstni CHETLAB O'TISH usuli — `set_tenant_context` ni bo'sh
    funksiyaga almashtirish. Bu `discover_nvr` ning O'Z chaqiruvini
    o'chiradi va boshqa hech nimaga tegmaydi, ya'ni o'lchanayotgan
    narsa AYNAN o'sha chaqiruv.
    =======================================================================
    """
    before = await _camera_count(tenant_session, prepared.market_id, prepared.nvr_id)
    assert before == SEEDED_CHANNELS, "seed kutilgan holatda emas"

    async def _no_context(*_: Any, **__: Any) -> None:
        """Kontekst O'RNATILMAYDI — RLS fail-closed holatga tushadi."""

    blind_run = await _create_run(api_sessionmaker, prepared)
    monkeypatch.setattr(discovery_job, "set_tenant_context", _no_context)
    await discover_nvr(
        api_sessionmaker,
        market_id=prepared.market_id,
        nvr_id=prepared.nvr_id,
        run_id=blind_run,
        actor_id=None,
    )
    monkeypatch.undo()

    blind = await _run_row(tenant_session, prepared.market_id, blind_run)
    assert blind["channels_added"] is None, (
        "kontekstsiz job yugurish qatoriga yozdi — RLS chetlab o'tilgan"
    )
    assert blind["status"] == "queued", blind
    assert blind["error_code"] is None, (
        "kontekstsiz job XATO ham yozdi — nosozlik JIMGINA bo'lishi kerak edi"
    )
    assert await _camera_count(tenant_session, prepared.market_id, prepared.nvr_id) == before, (
        "kontekstsiz job kamera yaratdi — bu RLS ning buzilgani demak"
    )

    # =====================================================================
    # NOSOZLIKNING IKKINCHI, KUTILMAGAN OQIBATI — VA U SHU YERDA
    # QULFLANADI.
    #
    # Kontekstsiz job yugurishni `running` ga ham o'tkaza olmagani uchun
    # qator MANGU `queued` bo'lib qoladi. `0012` dagi qisman UNIQUE
    # indeks esa `status IN ('queued','running')` ustida — ya'ni shu NVR
    # uchun boshqa HECH QANDAY kashfiyot boshlab bo'lmaydi.
    #
    # Ya'ni Pitfall 13 faqat "hech nima topilmadi" bermaydi: u qurilmani
    # BUTUNLAY QULFLAB QO'YADI va buni yagona tuzatish yo'li — bazaga
    # qo'l bilan kirish. Aynan shuning uchun kontekst chaqiruvi jobning
    # birinchi qadamida turadi.
    # =====================================================================
    with pytest.raises(IntegrityError):
        await _create_run(api_sessionmaker, prepared)

    async with api_sessionmaker() as session, session.begin():
        await _set_tenant(session, prepared.market_id)
        await NvrRepository(session, prepared.market_id).finish_run(blind_run, "failed")

    # --- IKKINCHI YARIM: kontekst bilan AYNI job kameralarni YARATADI ---
    real_run = await _create_run(api_sessionmaker, prepared)
    await discover_nvr(
        api_sessionmaker,
        market_id=prepared.market_id,
        nvr_id=prepared.nvr_id,
        run_id=real_run,
        actor_id=None,
    )

    real = await _run_row(tenant_session, prepared.market_id, real_run)
    assert real["status"] == "succeeded", real
    assert real["channels_added"] > 0, (
        "kontekst bilan ham hech nima qo'shilmadi — o'lchov ma'nosini yo'qotdi"
    )
    assert await _camera_count(tenant_session, prepared.market_id, prepared.nvr_id) > before


async def test_channels_found_is_written_before_the_substream_probes(
    api_sessionmaker: async_sessionmaker[AsyncSession],
    tenant_session: TenantSessionFactory,
    prepared: MarketNvrRows,
    sim: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """UI-SPEC §5.2 [TALAB] — oraliq yozuv sub-oqim tekshiruvlaridan OLDIN.

    =======================================================================
    O'LCHOV VAQT BO'YICHA EMAS, SO'ROVLAR SANOG'I BO'YICHA.

    "Oldin yozildi" da'vosini natijadan ko'rib bo'lmaydi: oxirida yozgan
    kod ham AYNAN bir xil qatorni qoldiradi. Yagona dalil — yozuv
    paytida `Streaming/channels/*` ga NECHA MARTA borilgani. Byudjet
    hisobiga ko'ra vaqtning KATTA QISMI aynan o'sha tsiklga ketadi, ya'ni
    "0" bu yerda "admin ~50 soniyalik qorong'ilik o'rniga ikkita
    o'qiladigan bosqichni ko'radi" degani.
    =======================================================================
    """
    observed: list[tuple[int, int]] = []
    original = NvrRepository.set_channels_found

    async def _spy(self: NvrRepository, run_id: UUID, channels_found: int) -> bool:
        streaming = sum(
            count
            for path, count in sim_state(sim)["endpoint_hits"].items()
            if path.startswith("Streaming/channels/")
        )
        observed.append((channels_found, streaming))
        return await original(self, run_id, channels_found)

    monkeypatch.setattr(NvrRepository, "set_channels_found", _spy)

    run_id = await _create_run(api_sessionmaker, prepared)
    await discover_nvr(
        api_sessionmaker,
        market_id=prepared.market_id,
        nvr_id=prepared.nvr_id,
        run_id=run_id,
        actor_id=None,
    )

    assert observed == [(SIM_CHANNEL_COUNT, 0)], (
        f"`channels_found` sub-oqim tekshiruvlaridan KEYIN yozildi: {observed}"
    )
    row = await _run_row(tenant_session, prepared.market_id, run_id)
    assert row["channels_found"] == SIM_CHANNEL_COUNT


async def test_failure_is_recorded_and_the_job_does_not_raise(
    api_sessionmaker: async_sessionmaker[AsyncSession],
    tenant_session: TenantSessionFactory,
    prepared: MarketNvrRows,
) -> None:
    """Noto'g'ri parol -> `failed` + `nvr_bad_credentials`, ISTISNO YO'Q.

    ⚠ JOB JARAYONI YIQILMASLIGI — XAVFSIZLIK TALABI, TOZALIK EMAS.
      Yiqilgan vazifani navbat qayta yetkazishi mumkin, qayta urinish esa
      NVR ga ikkinchi marta borardi va D-03 ning qulflash arifmetikasini
      ishga tushirardi (~5 urinish -> 30 daqiqa qulf).
    """
    async with api_sessionmaker() as session, session.begin():
        await _set_tenant(session, prepared.market_id)
        await NvrRepository(session, prepared.market_id).put_credential(
            prepared.nvr_id, encrypt_nvr_password("notogri-parol"), 1
        )

    run_id = await _create_run(api_sessionmaker, prepared)

    await discover_nvr(
        api_sessionmaker,
        market_id=prepared.market_id,
        nvr_id=prepared.nvr_id,
        run_id=run_id,
        actor_id=None,
    )

    row = await _run_row(tenant_session, prepared.market_id, run_id)
    assert row["status"] == "failed", row
    assert row["error_code"] == "nvr_bad_credentials"
    assert row["finished_at"] is not None
    assert "notogri-parol" not in (row["detail"] or "")


async def test_unreadable_credential_is_not_reported_as_a_bad_password(
    api_sessionmaker: async_sessionmaker[AsyncSession],
    tenant_session: TenantSessionFactory,
    prepared: MarketNvrRows,
) -> None:
    """Deshifrlab bo'lmaydigan token `nvr_credential_unreadable` beradi (03-04 ning talabi).

    ⚠ FARQ OPERATSION, LEKSIK EMAS. `nvr_bad_credentials` "NVR dagi parol
      noto'g'ri" deydi va admin uni qayta kiritadi; bu kod esa "shifr
      kalitimiz bilan muammo" deydi va yechim butunlay boshqa joyda
      (`NVR_CREDENTIAL_KEYS_RETIRED`). Bitta kod operatorni noto'g'ri
      joyni qidirishga majbur qilardi.

    Seed'ning `NVR_PASSWORD_PLACEHOLDER` i AYNAN shunday token — u Fernet
    formatida EMAS va `nvr_rows` uni ataylab shunday yozadi.
    """
    async with api_sessionmaker() as session, session.begin():
        await _set_tenant(session, prepared.market_id)
        await NvrRepository(session, prepared.market_id).put_credential(
            prepared.nvr_id, b"bu-fernet-tokeni-emas", 1
        )

    run_id = await _create_run(api_sessionmaker, prepared)

    await discover_nvr(
        api_sessionmaker,
        market_id=prepared.market_id,
        nvr_id=prepared.nvr_id,
        run_id=run_id,
        actor_id=None,
    )

    row = await _run_row(tenant_session, prepared.market_id, run_id)
    assert row["status"] == "failed", row
    assert row["error_code"] == "nvr_credential_unreadable"


async def test_a_second_delivery_of_the_same_run_does_nothing(
    api_sessionmaker: async_sessionmaker[AsyncSession],
    tenant_session: TenantSessionFactory,
    prepared: MarketNvrRows,
    sim: str,
) -> None:
    """AYNI `run_id` ikkinchi marta yetkazilsa job NVR ga BORMAYDI.

    Navbatlar "kamida bir marta" kafolatini beradi, ya'ni takroriy
    yetkazish NORMAL hodisa. Darvoza — `start_run()` ning
    `status = 'queued'` sharti, va uning yagona dalili yana SO'ROVLAR
    SANOG'I: natija (`succeeded` qator) ikkinchi skandan keyin ham
    aynan bir xil ko'rinardi.
    """
    run_id = await _create_run(api_sessionmaker, prepared)
    await discover_nvr(
        api_sessionmaker,
        market_id=prepared.market_id,
        nvr_id=prepared.nvr_id,
        run_id=run_id,
        actor_id=None,
    )
    hits_after_first = sum(sim_state(sim)["endpoint_hits"].values())

    await discover_nvr(
        api_sessionmaker,
        market_id=prepared.market_id,
        nvr_id=prepared.nvr_id,
        run_id=run_id,
        actor_id=None,
    )

    assert sum(sim_state(sim)["endpoint_hits"].values()) == hits_after_first, (
        "takroriy yetkazish NVR ga ikkinchi marta bordi — D-03 ning qulflash xavfi"
    )
    row = await _run_row(tenant_session, prepared.market_id, run_id)
    assert row["status"] == "succeeded", row


# ---------------------------------------------------------------------------
# Navbatning O'ZI — HAQIQIY Valkey ustida
# ---------------------------------------------------------------------------


async def test_enqueue_puts_the_four_identifiers_on_the_queue(
    valkey_url: str,
    valkey_client: Redis,
) -> None:
    """`enqueue_discovery` navbatga AYNAN to'rtta identifikatorni qo'yadi.

    =======================================================================
    HAQIQIY VALKEY, MOCK EMAS — VA SABAB `tests/conftest.py::valkey_client`
    DA ALLAQACHON YOZILGAN: qalbaki klient semantikani TAXMIN qiladi va
    farqi faqat prod'da ko'rinadi.

    Bu yerda o'lchanadigan narsa AYNAN o'sha semantika:
      * vazifa `LIST` ga tushadimi (`PubSubBroker` bo'lganda obunachisiz
        xabar YO'QOLARDI);
      * `UUID` lar JSON'ga sig'adimi (`json.dumps(UUID(...))` `TypeError`
        beradi — konversiya qobiqda bo'lishi SHART);
      * `market_id` xabarda BORMI (usiz worker tenant kontekstini hech
        qayerdan ololmaydi — Pitfall 13).

    Broker ALMASHTIRILADI (`target=`): modul darajasidagi broker compose
    tarmog'idagi `cache` ga qarab turadi, test esa o'z konteynerida.
    =======================================================================
    """
    market_id, nvr_id, run_id, actor_id = uuid4(), uuid4(), uuid4(), uuid4()
    target = ListQueueBroker(valkey_url, queue_name=DISCOVERY_QUEUE)
    await target.startup()
    try:
        await enqueue_discovery(
            market_id=market_id,
            nvr_id=nvr_id,
            run_id=run_id,
            actor_id=actor_id,
            target=target,
        )
    finally:
        await target.shutdown()

    raw = await valkey_client.lpop(DISCOVERY_QUEUE)
    assert isinstance(raw, bytes), f"navbatga hech nima tushmadi yoki shakli kutilmagan: {raw!r}"
    payload = raw.decode()

    for name, value in (
        ("market_id", market_id),
        ("nvr_id", nvr_id),
        ("run_id", run_id),
        ("actor_id", actor_id),
    ):
        assert f'"{name}": "{value}"' in payload, f"`{name}` navbat xabarida yo'q: {payload}"
    assert "nvr.discover" in payload
