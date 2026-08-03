"""Kashfiyot orkestratsiyasi — SC#1 va SC#2 ning darvozasi (sim ustida).

=============================================================================
BU FAYL 03-02 NING `test_nvr_sim.py` DAN VA 03-04 NING `test_nvr_repo.py`
DAN ALOHIDA — UCHALASI UCH XIL DA'VONI O'LCHAYDI.

    test_nvr_sim.py        «sim Hikvision kabi javob beradimi?»
    test_nvr_repo.py       «upsert uch qoidani bajaradimi?»  (kirish QO'LDA)
    BU FAYL                «manzil + parol -> kameralar»     (kirish NVR'DAN)

Uchinchisi birinchi ikkitasini almashtira olmaydi va aksincha. `test_nvr_
repo.py` `DiscoveredChannel` ni QO'LDA yasaydi — ya'ni u XML ham,
namespace ham, `deviceType` tarmoqlanishi ham ko'rmaydi. Bu yerda esa
kanallar HAQIQIY ISAPI javobidan, HAQIQIY Digest handshake ortidan
keladi.
=============================================================================

⚠ UCHTA NAZORAT HOLATI MAJBURIY VA ULAR ALOHIDA TESTLAR:

  (a) `channels_added=0` bo'lgan ikkinchi yugurishda kameralarning `id` va
      `first_seen_at` O'ZGARMAGANI. Usiz «idempotent» da'vosi «qayta
      yaratildi va bir xil ko'rinadi» dan FARQLANMASDI.
  (b) `channel_removed` dan keyin qator soni KAMAYMAGANI. Usiz «oflayn
      qilindi» «o'chirildi» dan FARQLANMASDI — ikkala holatda ham
      «status = offline» so'rovi bo'sh natija bermasdi.
  (c) IP-kamera yo'lida `InputProxy` CHAQIRILMAGANI — SO'ROVLAR SANOG'I
      bilan. Usiz `InputProxy` ni chaqirib, `404` ni yutib, keyin to'g'ri
      yo'ldan borgan kod ham AYNAN BIR XIL natija berardi.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import pytest
from app.repositories.nvr_repo import NvrRepository
from app.services.isapi.client import IsapiClient
from app.services.isapi.discovery import run_discovery
from app.services.rtsp import rtsp_url
from fixtures.nvr_domain import A_CAMERA_CHANNELS, nvr_rows
from fixtures.nvr_sim import sim_patch, sim_state
from sbozor_core.enums import CameraStatus
from sqlalchemy import text

if TYPE_CHECKING:
    from uuid import UUID

    from app.services.isapi.discovery import DiscoveryOutcome
    from fixtures import TenantSessionFactory
    from fixtures.two_markets import TwoMarketSeed
    from psycopg import Connection
    from psycopg.rows import TupleRow

pytestmark = [pytest.mark.sim, pytest.mark.usefixtures("migrated")]

SIM_CHANNEL_COUNT = 6
"""D-09: CI'da 6 kanal (`DS-7616NI-K2` fixture'iga mos, tez).

25 kanal ALOHIDA, `slow` markerli test bilan o'lchanadi va standart
zanjirda ishlamaydi.
"""

SEEDED_CHANNELS = len(A_CAMERA_CHANNELS)
"""Seed'da 3 kanal bor — ya'ni birinchi skan 3 tasini QO'SHADI, 3 tasini KO'RADI.

Sonlar farqli bo'lgani ataylab: `channels_found` bilan `channels_added`
teng chiqsa ularning FARQI umuman sinalmasdi.
"""


def _now() -> datetime:
    return datetime.now(tz=UTC)


async def _discover(
    tenant_session: TenantSessionFactory,
    market_id: UUID,
    nvr_id: UUID,
    sim_url: str,
    credentials: tuple[str, str],
    **kwargs: Any,
) -> DiscoveryOutcome:
    """Bitta to'liq kashfiyot: yangi sessiya, yangi klient, yangi vaqt tamg'asi.

    Klient HAR YUGURISHDA yangi — real jobda ham shunday (job boshlanadi,
    ulanadi, tugaydi va yopadi). Bitta klientni testlar orasida saqlash
    Digest nonce'ini ham, oqim sanog'ini ham meros qilib qoldirardi.
    """
    username, password = credentials
    async with tenant_session(market_id) as session:
        repo = NvrRepository(session, market_id)
        async with IsapiClient(sim_url, username, password) as client:
            return await run_discovery(repo, client, nvr_id=nvr_id, run_started_at=_now(), **kwargs)


async def _cameras(
    tenant_session: TenantSessionFactory, market_id: UUID, nvr_id: UUID
) -> dict[int, dict[str, object]]:
    """Kanal raqami -> XOM ustun qiymatlari.

    ORM emas, xom SQL: identity-map keshidan qaytgan obyekt «`first_seen_at`
    o'zgarmadi» da'vosini BAZANI emas, KESHNI o'lchagan holga keltirardi
    (`test_nvr_repo.py` dagi bilan bir xil sabab).

    `source_ip` `host()` orqali — `inet` ustuni qiymatni `/32` prefiksi
    bilan saqlaydi (03-04 ning `threat_flag: value-format` bandi).
    """
    async with tenant_session(market_id) as session:
        result = await session.execute(
            text(
                "SELECT channel_no, id, name, name_overridden, status, is_archived, "
                "       has_substream, first_seen_at, last_seen_at, "
                "       host(source_ip) AS source_ip, source_model "
                "FROM cameras WHERE market_id = :market_id AND nvr_id = :nvr_id"
            ),
            {"market_id": market_id, "nvr_id": nvr_id},
        )
        return {row.channel_no: dict(row._mapping) for row in result}


async def _device_row(
    tenant_session: TenantSessionFactory, market_id: UUID, nvr_id: UUID
) -> dict[str, object]:
    async with tenant_session(market_id) as session:
        result = await session.execute(
            text(
                "SELECT host, model, device_type, serial_number, firmware_version, "
                "       rtsp_port, rtsp_port_assumed, last_discovery_at "
                "FROM nvr_devices WHERE market_id = :market_id AND id = :nvr_id"
            ),
            {"market_id": market_id, "nvr_id": nvr_id},
        )
        return dict(result.one()._mapping)


async def _camera_audit_updates(tenant_session: TenantSessionFactory, market_id: UUID) -> int:
    async with tenant_session(market_id) as session:
        result = await session.execute(
            text(
                "SELECT count(*) FROM audit_log WHERE market_id = :market_id "
                "AND table_name = 'cameras' AND action = 'update'"
            ),
            {"market_id": market_id},
        )
        return int(result.scalar_one())


# ---------------------------------------------------------------------------
# SC#1 — manzil va rekvizitdan kameralargacha
# ---------------------------------------------------------------------------


async def test_discovery_creates_a_camera_for_every_channel(
    sim: str,
    sim_credentials: tuple[str, str],
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    tenant_session: TenantSessionFactory,
) -> None:
    """SC#1: qo'lda birorta RTSP URL yozilmaydi — hammasi NVR javobidan.

    Nom NVR'dan keladi (`tagahoov` — yozib olingan dumpdagi HAQIQIY nom,
    biz o'ylab topgan «Kanal 01» emas), manba kamera IP'si ham.
    """
    with nvr_rows(sync_owner_conn, two_markets) as seed:
        rows = seed.market_a

        outcome = await _discover(tenant_session, rows.market_id, rows.nvr_id, sim, sim_credentials)

        assert outcome.counts.channels_found == SIM_CHANNEL_COUNT
        assert outcome.counts.channels_added == SIM_CHANNEL_COUNT - SEEDED_CHANNELS
        assert outcome.device.model == "DS-7616NI-K2"
        assert outcome.device.device_type == "NVR"

        cameras = await _cameras(tenant_session, rows.market_id, rows.nvr_id)
        assert sorted(cameras) == list(range(1, SIM_CHANNEL_COUNT + 1))
        assert cameras[1]["name"] == "tagahoov", "nom NVR javobidan olinmadi"
        assert cameras[1]["source_ip"] == "1.0.0.208"
        assert cameras[1]["source_model"] == "DS-2CD2387G2-LSU/SL"

        device = await _device_row(tenant_session, rows.market_id, rows.nvr_id)
        assert device["serial_number"] == "DS-7616NI-K20000000000CCRRG00000000WCVU"
        assert device["firmware_version"] == "V4.74.210"
        assert device["last_discovery_at"] is not None


async def test_nvr_path_never_calls_the_video_inputs_endpoint(
    sim: str,
    sim_credentials: tuple[str, str],
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    tenant_session: TenantSessionFactory,
) -> None:
    """D-04, A.1: NVR'da `InputProxy` AVTORITETLI, `Video/inputs/channels` YO'Q.

    ⚠ Da'vo SO'ROVLAR SANOG'I bilan o'lchanadi. Natijadan o'lchab
      bo'lmasdi: `Video/inputs/channels` ni chaqirib, `403` ni yutib,
      keyin `InputProxy` ga o'tgan kod ham AYNAN BIR XIL kameralarni
      yaratardi — lekin real qurilmada bitta ortiqcha borish qilardi va
      bo'sh slotlarni «kanal» deb ko'rish xavfi ochiq qolardi.
    """
    with nvr_rows(sync_owner_conn, two_markets) as seed:
        rows = seed.market_a
        await _discover(tenant_session, rows.market_id, rows.nvr_id, sim, sim_credentials)

        hits: dict[str, int] = sim_state(sim)["endpoint_hits"]

    assert hits.get("ContentMgmt/InputProxy/channels", 0) == 1
    assert hits.get("ContentMgmt/InputProxy/channels/status", 0) == 1
    assert hits.get("System/Video/inputs/channels", 0) == 0, (
        "NVR yo'lida `Video/inputs/channels` chaqirildi — u bo'sh slotlarni ham "
        "sanaydi va A.1 bo'yicha AVTORITETLI EMAS"
    )


async def test_ip_camera_path_never_calls_input_proxy(
    sim: str,
    sim_credentials: tuple[str, str],
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    tenant_session: TenantSessionFactory,
) -> None:
    """D-04 ning IKKINCHI shoxi: standalone kamerada `InputProxy` UMUMAN YO'Q.

    Nazorat holati (c). Sim IP-kamera modelida `InputProxy` ga `404`
    beradi, ya'ni «chaqirdim va yutdim» yo'li ham bitta kamera yaratardi
    — farqni faqat sanoq ko'rsatadi.
    """
    sim_patch(sim, model="DS-2CD2346G2-ISU")

    with nvr_rows(sync_owner_conn, two_markets) as seed:
        rows = seed.market_b  # B bozorida bitta seed kanali bor

        outcome = await _discover(tenant_session, rows.market_id, rows.nvr_id, sim, sim_credentials)
        hits: dict[str, int] = sim_state(sim)["endpoint_hits"]

        assert outcome.device.device_type == "IPCamera"
        assert outcome.counts.channels_found == 1
        cameras = await _cameras(tenant_session, rows.market_id, rows.nvr_id)
        assert sorted(cameras) == [1]
        assert cameras[1]["name"] == "Atelier"

    assert hits.get("ContentMgmt/InputProxy/channels", 0) == 0, (
        "IP-kamerada `InputProxy` chaqirildi — D-04 tarmoqlanishi ishlamayapti"
    )
    assert hits.get("System/Video/inputs/channels", 0) == 1


# ---------------------------------------------------------------------------
# UI-SPEC §5.2 [TALAB] — `channels_found` sub-oqim tekshiruvidan OLDIN
# ---------------------------------------------------------------------------


async def test_channels_found_is_reported_before_substream_probes(
    sim: str,
    sim_credentials: tuple[str, str],
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    tenant_session: TenantSessionFactory,
) -> None:
    """Callback sub-oqim tekshiruvlaridan OLDIN chaqiriladi (UI-SPEC §5.2).

    ⚠ TARTIB SANOQ BILAN O'LCHANADI: callback chaqirilgan payt sim'da
      NECHTA `Streaming/channels/*` so'rovi bo'lganini yozib olamiz. Agar
      callback oxirda chaqirilsa bu son 6 bo'lardi.

    Sabab byudjet hisobida: 25 kanal × borish ~50 soniya oladi va u
    vaqtda admin BIR XIL «yuklanmoqda» ni ko'radi — «osilib qoldi» dan
    farqlanmaydigan holat.
    """
    observed: list[tuple[int, int]] = []

    async def _record(found: int) -> None:
        streaming = sum(
            count
            for path, count in sim_state(sim)["endpoint_hits"].items()
            if path.startswith("Streaming/channels/")
        )
        observed.append((found, streaming))

    with nvr_rows(sync_owner_conn, two_markets) as seed:
        rows = seed.market_a
        outcome = await _discover(
            tenant_session,
            rows.market_id,
            rows.nvr_id,
            sim,
            sim_credentials,
            on_channels_found=_record,
        )

    assert observed == [(SIM_CHANNEL_COUNT, 0)], (
        f"callback {observed} bilan chaqirildi — kutilgani (6, 0): kanallar soni "
        "sub-oqim tekshiruvlaridan OLDIN e'lon qilinishi SHART"
    )
    assert outcome.counts.channels_found == SIM_CHANNEL_COUNT


async def test_channels_found_counts_offline_channels_too(
    sim: str,
    sim_credentials: tuple[str, str],
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    tenant_session: TenantSessionFactory,
) -> None:
    """`channels_found` — SANAB CHIQILGAN kanallar, holatidan QAT'I NAZAR.

    UI-SPEC §6.3 [TALAB]. Aks holda `unchanged = found − added` formulasi
    oflayn kameralar sonicha kam chiqardi va admin uni «kameralar
    yo'qoldi» deb o'qirdi.

    ⚠ Bu yerda 12-KOD (`channel_offline`) o'lchanadi: kamera yozuvi
      BARIBIR yaratiladi va sabab `channel_issues` da qaytadi (UI-SPEC
      §7.3 — u BLOK emas, qator badge'i).
    """
    sim_patch(sim, mode="channel_offline", offline_channels=[3, 7], channel_count=8)

    with nvr_rows(sync_owner_conn, two_markets) as seed:
        rows = seed.market_a
        outcome = await _discover(tenant_session, rows.market_id, rows.nvr_id, sim, sim_credentials)

        assert outcome.counts.channels_found == 8, "oflayn kanallar sanoqdan tushib qoldi"

        cameras = await _cameras(tenant_session, rows.market_id, rows.nvr_id)
        assert sorted(cameras) == list(range(1, 9))
        assert cameras[3]["status"] == CameraStatus.OFFLINE.value
        assert cameras[7]["status"] == CameraStatus.OFFLINE.value
        assert cameras[1]["status"] == CameraStatus.ONLINE.value

    codes = sorted(issue.code for issue in outcome.channel_issues)
    assert codes == ["channel_offline", "channel_offline"], codes
    reported = sorted(int(issue.detail["channel_no"]) for issue in outcome.channel_issues)
    assert reported == [3, 7]
    assert all("channel_name" in issue.detail for issue in outcome.channel_issues)


# ---------------------------------------------------------------------------
# SC#2 — idempotentlik va uch qoida
# ---------------------------------------------------------------------------


async def test_rescan_is_idempotent_and_keeps_identity(
    sim: str,
    sim_credentials: tuple[str, str],
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    tenant_session: TenantSessionFactory,
) -> None:
    """Nazorat holati (a): ikkinchi skan 0 qo'shadi VA `id` ni O'ZGARTIRMAYDI.

    ⚠ FAQAT `channels_added == 0` ni tekshirish YETARLI EMAS: qatorlarni
      o'chirib qayta yaratgan kod ham nolni ko'rsatishi mumkin edi (yangi
      qator uchun `xmax = 0` bo'lardi... lekin sanoq baribir 6 chiqardi).
      Haqiqiy da'vo — IDENTIKLIK: `id` va `first_seen_at` o'zgarmagan.
      Ular 4-fazadagi snapshotlar va 5-fazadagi zonalar uchun barqaror
      bo'lishi SHART.
    """
    with nvr_rows(sync_owner_conn, two_markets) as seed:
        rows = seed.market_a

        await _discover(tenant_session, rows.market_id, rows.nvr_id, sim, sim_credentials)
        before = await _cameras(tenant_session, rows.market_id, rows.nvr_id)

        second = await _discover(tenant_session, rows.market_id, rows.nvr_id, sim, sim_credentials)
        after = await _cameras(tenant_session, rows.market_id, rows.nvr_id)

        assert second.counts.channels_added == 0, "ikkinchi skan yangi kamera qo'shdi"
        assert second.counts.channels_found == SIM_CHANNEL_COUNT
        assert second.counts.channels_marked_offline == 0

        for channel_no, row in before.items():
            assert after[channel_no]["id"] == row["id"], f"kanal {channel_no}: `id` o'zgardi"
            assert after[channel_no]["first_seen_at"] == row["first_seen_at"], (
                f"kanal {channel_no}: `first_seen_at` qayta yozildi"
            )
        assert all(
            after[channel]["last_seen_at"] > before[channel]["last_seen_at"]  # type: ignore[operator]
            for channel in before
        ), "`last_seen_at` yangilanmadi — skan haqiqatan bo'ldimi?"


async def test_new_channel_is_added_and_existing_rows_are_untouched(
    sim: str,
    sim_credentials: tuple[str, str],
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    tenant_session: TenantSessionFactory,
) -> None:
    """SC#2 ning 1-qoidasi: yangi kanal QO'SHILADI, mavjudi TEGILMAYDI."""
    with nvr_rows(sync_owner_conn, two_markets) as seed:
        rows = seed.market_a

        await _discover(tenant_session, rows.market_id, rows.nvr_id, sim, sim_credentials)
        before = await _cameras(tenant_session, rows.market_id, rows.nvr_id)

        sim_patch(sim, mode="channel_added", channel_count=8)
        outcome = await _discover(tenant_session, rows.market_id, rows.nvr_id, sim, sim_credentials)
        after = await _cameras(tenant_session, rows.market_id, rows.nvr_id)

        assert outcome.counts.channels_added == 2, "yangi ikki kanal qo'shilmadi"
        assert outcome.counts.channels_found == 8
        assert sorted(after) == list(range(1, 9))
        for channel_no in before:
            assert after[channel_no]["id"] == before[channel_no]["id"]


async def test_missing_channel_goes_offline_and_is_not_deleted(
    sim: str,
    sim_credentials: tuple[str, str],
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    tenant_session: TenantSessionFactory,
) -> None:
    """Nazorat holati (b): QATOR SONI KAMAYMAYDI (D-10, T-03-27).

    ⚠ Usiz «oflayn qilindi» «o'chirildi» dan FARQLANMASDI. Farq 4- va
      5-fazalarda hal qiluvchi: snapshotlar va zona poligonlari
      `cameras.id` ga tayanadi va qator o'chirilsa tarixiy DALIL yetim
      qolardi.

    ⚠ SABOTAJ CHEGARASI: `mark_missing_offline` chaqiruvini olib tashlash
      AYNAN shu testni qizartiradi, idempotentlik testlari esa yashil
      qoladi — ikki qoida alohida o'lchanayotgani shu bilan isbotlanadi.
    """
    with nvr_rows(sync_owner_conn, two_markets) as seed:
        rows = seed.market_a

        await _discover(tenant_session, rows.market_id, rows.nvr_id, sim, sim_credentials)
        before = await _cameras(tenant_session, rows.market_id, rows.nvr_id)

        sim_patch(sim, mode="channel_removed", removed_channels=[5])
        outcome = await _discover(tenant_session, rows.market_id, rows.nvr_id, sim, sim_credentials)
        after = await _cameras(tenant_session, rows.market_id, rows.nvr_id)

        assert outcome.counts.channels_found == SIM_CHANNEL_COUNT - 1
        assert outcome.counts.channels_marked_offline == 1
        assert len(after) == len(before), "qator soni kamaydi — kamera O'CHIRILDI"
        assert after[5]["status"] == CameraStatus.OFFLINE.value
        assert after[5]["id"] == before[5]["id"], "qator o'chirilib qayta yaratilgan"


async def test_manually_renamed_camera_survives_the_rescan(
    sim: str,
    sim_credentials: tuple[str, str],
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    tenant_session: TenantSessionFactory,
) -> None:
    """SC#2 ning «mavjudi tegilmaydi» qismi — admin qarori NVR'dan USTUN.

    Seed'ning 2-kanali `name_overridden = true` bilan keladi. NVR o'sha
    kanalni `garaazh` deb ataydi; qayta skandan keyin ham admin nomi
    qolishi SHART.

    Arxivlangan kanal (seed'ning 3-kanali) ham TIKLANMAYDI — bu D-10 ning
    ikkinchi yarmi va u ham «admin qarori ustun» qoidasidan chiqadi.
    """
    with nvr_rows(sync_owner_conn, two_markets) as seed:
        rows = seed.market_a

        await _discover(tenant_session, rows.market_id, rows.nvr_id, sim, sim_credentials)
        cameras = await _cameras(tenant_session, rows.market_id, rows.nvr_id)

        assert cameras[2]["name"] == "Sabzavot qatori (admin nomi)", (
            "qayta skan admin qo'ygan nomni bosib ketdi"
        )
        assert cameras[2]["name_overridden"] is True
        assert cameras[3]["is_archived"] is True, "arxivlangan kanal qayta skanda tiklandi"
        # Nazorat bandi: bayroqsiz kanal NVR nomini OLADI.
        assert cameras[1]["name"] == "tagahoov"


async def test_swapped_camera_updates_the_source_and_leaves_an_audit_row(
    sim: str,
    sim_credentials: tuple[str, str],
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    tenant_session: TenantSessionFactory,
) -> None:
    """Fizik almashtirish KUZATILADI (A.4) — 5-faza uchun signal.

    Kanal raqami KALIT, kamera IP'si va modeli esa ATRIBUT. Ular
    o'zgarganda yozuv yangilanadi va `audit_log` ga qator tushadi —
    5-fazada aynan shu signal «zona poligonlari yaroqsiz bo'lishi
    mumkin» degan xulosani beradi.
    """
    with nvr_rows(sync_owner_conn, two_markets) as seed:
        rows = seed.market_a

        await _discover(tenant_session, rows.market_id, rows.nvr_id, sim, sim_credentials)
        before_audit = await _camera_audit_updates(tenant_session, rows.market_id)

        sim_patch(
            sim,
            mode="camera_swapped",
            swapped_channel=3,
            swapped_ip="10.20.30.40",
            swapped_model="DS-2CD-YANGI",
        )
        await _discover(tenant_session, rows.market_id, rows.nvr_id, sim, sim_credentials)

        cameras = await _cameras(tenant_session, rows.market_id, rows.nvr_id)
        after_audit = await _camera_audit_updates(tenant_session, rows.market_id)

        assert cameras[3]["source_ip"] == "10.20.30.40"
        assert cameras[3]["source_model"] == "DS-2CD-YANGI"
        assert after_audit > before_audit, "`cameras` uchun `update` audit qatori yozilmadi"


# ---------------------------------------------------------------------------
# RTSP porti va sub-oqim
# ---------------------------------------------------------------------------


async def test_moved_rtsp_port_reaches_the_generated_url(
    sim: str,
    sim_credentials: tuple[str, str],
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    tenant_session: TenantSessionFactory,
) -> None:
    """Kashf etilgan port BAZAGA yoziladi va URL'ga yetib boradi (Pitfall 8).

    ⚠ SABOTAJ CHEGARASI: `adminAccesses` javobini e'tiborsiz qoldirib
      `rtsp_port` ni 554 deb qotirish AYNAN shu testni qizartiradi.
      Nosozlikning real ko'rinishi esa «kashfiyot yashil, kadr olish
      qora» bo'lardi — ya'ni uni 4-fazada, boshqa quyi tizimda izlashardi.
    """
    sim_patch(sim, mode="port_moved", rtsp_port=10554)

    with nvr_rows(sync_owner_conn, two_markets) as seed:
        rows = seed.market_a
        outcome = await _discover(tenant_session, rows.market_id, rows.nvr_id, sim, sim_credentials)
        device = await _device_row(tenant_session, rows.market_id, rows.nvr_id)

    assert outcome.rtsp_port == 10554
    assert outcome.rtsp_port_assumed is False
    assert device["rtsp_port"] == 10554, "kashf etilgan port bazaga yozilmadi"
    assert device["rtsp_port_assumed"] is False

    url = rtsp_url(str(device["host"]), int(str(device["rtsp_port"])), 3)
    assert url.endswith(":10554/Streaming/Channels/301"), url


async def test_channel_without_a_substream_is_flagged(
    sim: str,
    sim_credentials: tuple[str, str],
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    tenant_session: TenantSessionFactory,
) -> None:
    """`{ch}02` `404` bersa `has_substream = False` (A.2).

    ⚠ Bu 4-fazada hal qiluvchi bo'ladi: go2rtc DOIMIY ravishda faqat
      sub-oqimga ulanadi (A.5 — 25 kanal asosiy oqimda ~100 Mbps,
      sub-oqimda ~12 Mbps). Sub-oqimi yo'q kanalni KASHFIYOT paytida
      bilish kerak, kadr olish paytida emas.
    """
    sim_patch(sim, no_substream_channels=[4])

    with nvr_rows(sync_owner_conn, two_markets) as seed:
        rows = seed.market_a
        await _discover(tenant_session, rows.market_id, rows.nvr_id, sim, sim_credentials)
        cameras = await _cameras(tenant_session, rows.market_id, rows.nvr_id)

    assert cameras[4]["has_substream"] is False
    assert cameras[5]["has_substream"] is True, "nazorat: qolgan kanallarda sub-oqim bor"


async def test_substream_probe_can_be_switched_off(
    sim: str,
    sim_credentials: tuple[str, str],
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    tenant_session: TenantSessionFactory,
) -> None:
    """`probe_substreams=False` byudjetning katta qismini tejaydi (E.16).

    25 kanal × bitta qo'shimcha borish — kashfiyot vaqtining eng katta
    bo'lagi. Qadamning o'chirilishi SOZLAMA bo'lishi kerak, chunki uning
    narxi tunnel kechikishiga to'g'ridan-to'g'ri bog'liq va u bozordan
    bozorga farq qiladi.
    """
    with nvr_rows(sync_owner_conn, two_markets) as seed:
        rows = seed.market_a
        await _discover(
            tenant_session,
            rows.market_id,
            rows.nvr_id,
            sim,
            sim_credentials,
            probe_substreams=False,
        )
        streaming = sum(
            count
            for path, count in sim_state(sim)["endpoint_hits"].items()
            if path.startswith("Streaming/channels/")
        )

    assert streaming == 0, f"sub-oqim tekshiruvi o'chirilgan, lekin {streaming} so'rov ketdi"


# ---------------------------------------------------------------------------
# D-09 — 25 kanal, ALOHIDA sekin test
# ---------------------------------------------------------------------------


@pytest.mark.slow
async def test_discovery_scales_to_25_channels(
    sim: str,
    sim_credentials: tuple[str, str],
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    tenant_session: TenantSessionFactory,
) -> None:
    """Karmana o'lchamidagi NVR (D-09) — `npm run test:sim:slow` bilan.

    ⚠ Bu test standart zanjirda ISHLAMAYDI (`-m "sim and not slow"`).
      Sabab byudjetda: 25 kanal × (kanal + sub-oqim) borishi har `gate` ga
      sezilarli vaqt qo'shardi, kashfiyotning O'ZI esa 6 kanalda ham
      to'liq o'lchanadi. Bu test MIQYOSNI tekshiradi, mantiqni emas.

    Kanal soni ISH PAYTIDA oshiriladi (`SIM_CHANNEL_COUNT` faqat
    boshlang'ich qiymat), ya'ni konteynerni qayta ko'tarish shart emas.
    """
    sim_patch(sim, model="DS-7732NI-M4", channel_count=25)

    with nvr_rows(sync_owner_conn, two_markets) as seed:
        rows = seed.market_a
        outcome = await _discover(tenant_session, rows.market_id, rows.nvr_id, sim, sim_credentials)
        cameras = await _cameras(tenant_session, rows.market_id, rows.nvr_id)

    assert outcome.counts.channels_found == 25
    assert len(cameras) == 25
    assert sorted(cameras) == list(range(1, 26))
