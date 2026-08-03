"""`NvrRepository` — SC#2 ning idempotent upserti va tenant chegarasi.

=============================================================================
BU FAYL 03-03 NING SXEMA TESTLARINING O'RNINI BOSMAYDI — ULARNING USTIGA
QURILADI.

`tests/tenancy/test_nvr_domain_meta.py` (03-03) SXEMA darajasida
isbotlaydi: `UNIQUE (market_id, nvr_id, channel_no)` mavjud va xom
`INSERT` `23505` beradi. Bu yerdagi savol boshqa: **ILOVA o'sha
konstraytdan qanday foydalanadi** — `ON CONFLICT` qaysi ustunlarni
yangilaydi, qaysilariga TEGMAYDI va sonlar to'g'ri chiqadimi.

Ikkisi bir-birini almashtira olmaydi. Sxema testi `SET` ifodasidan
`CASE WHEN name_overridden` olib tashlanganda ham YASHIL qolardi
(konstrayt joyida!); bu yerdagi test esa konstrayt butunlay olib
tashlanganda «ikkinchi upsert 6 ta qo'shdi» deb qizarardi, lekin
SABABNI ko'rsata olmasdi.
=============================================================================

TESTLAR `nvr_rows()` KONTEKST MENEJERIDAN FOYDALANADI (03-03 seed'i).
Seed'ning asimmetriyasi ATAYIN va u bu yerda ishlaydi: A bozorida uch
kanal (biri `name_overridden`, biri `is_archived`), B da bitta. Sonlar
farqli bo'lgani uchun «noto'g'ri bozorning qatorlari qaytdi» holati
sanoqda darhol ko'rinadi.

⚠ IKKI NAZORAT HOLATI MAJBURIY VA ULAR ALOHIDA TEST:
  (a) cross-tenant `nvr_id` bilan HECH NARSA yaratilmasligi;
  (b) `mark_missing_offline()` dan keyin qator sonining KAMAYMAGANI.
  (b) siz «oflayn qilindi» da'vosi «o'chirildi» dan farqlanmasdi — ikkala
  holatda ham status so'rovi bo'sh natija berardi.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from app.repositories.nvr_repo import DiscoveredChannel, NvrRepository, UpsertCounts
from fixtures.nvr_domain import (
    A_CAMERA_CHANNELS,
    A_HOST,
    nvr_rows,
)
from sbozor_core.enums import CameraStatus, DiscoveryRunStatus
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

if TYPE_CHECKING:
    from uuid import UUID

    from fixtures import TenantSessionFactory
    from fixtures.two_markets import TwoMarketSeed
    from psycopg import Connection
    from psycopg.rows import TupleRow

pytestmark = pytest.mark.usefixtures("migrated")


SCAN_CHANNELS = (1, 2, 3, 4, 5, 6)
"""Skan topadigan olti kanal — seed'dagi UCHTASIDAN ko'p.

Ataylab: birinchi upsert «uchtasi mavjud, uchtasi yangi» holatini
o'lchaydi, ya'ni `channels_added` ni `channels_found` dan AJRATADI. Olti
kanalning hammasi yangi bo'lsa ikkala son teng chiqib, farq sinalmasdi.
"""


def _channels(
    numbers: tuple[int, ...] = SCAN_CHANNELS,
    *,
    name_prefix: str = "Kanal",
    source_ip: str | None = "192.168.1.10",
    source_model: str | None = "DS-2CD2043G2",
) -> list[DiscoveredChannel]:
    """Kashfiyot chiqishini yasaydi (ISAPI klienti o'rnida)."""
    return [
        DiscoveredChannel(
            channel_no=number,
            name=f"{name_prefix} {number:02d}",
            source_ip=source_ip,
            source_model=source_model,
        )
        for number in numbers
    ]


def _now() -> datetime:
    return datetime.now(tz=UTC)


async def _camera_rows(
    tenant_session: TenantSessionFactory, market_id: UUID, nvr_id: UUID
) -> dict[int, dict[str, object]]:
    """Kanal raqami -> xom ustun qiymatlari.

    ⚠ ORM obyekti EMAS, XOM SQL. Sabab identity-map da: bir sessiyada
      o'qilgan `Camera` obyekti keyingi o'qishda KESHDAN qaytishi mumkin
      va «`first_seen_at` o'zgarmadi» da'vosi bazani emas, keshni
      o'lchagan bo'lardi.

    ⚠ `source_ip` `host()` ORQALI o'qiladi — xom `::text` emas. Sabab
      `test_source_ip_is_stored_as_a_host_prefixed_inet` da o'lchangan va
      hujjatlashtirilgan: `inet` ustuni qiymatni `/32` prefiksi bilan
      saqlaydi. `host()` semantik qiymatni beradi, ya'ni bu testlar
      manzilning O'ZINI tekshiradi, uning `inet` ko'rinishini emas.
    """
    async with tenant_session(market_id) as session:
        result = await session.execute(
            text(
                "SELECT channel_no, id, name, name_overridden, status, is_archived, "
                "       stream_name, first_seen_at, last_seen_at, "
                "       host(source_ip) AS source_ip, source_model "
                "FROM cameras WHERE market_id = :market_id AND nvr_id = :nvr_id"
            ),
            {"market_id": market_id, "nvr_id": nvr_id},
        )
        return {row.channel_no: dict(row._mapping) for row in result}


async def _camera_count(tenant_session: TenantSessionFactory, market_id: UUID, nvr_id: UUID) -> int:
    async with tenant_session(market_id) as session:
        result = await session.execute(
            text("SELECT count(*) FROM cameras WHERE market_id = :market_id AND nvr_id = :nvr_id"),
            {"market_id": market_id, "nvr_id": nvr_id},
        )
        return int(result.scalar_one())


# ---------------------------------------------------------------------------
# Upsert — SC#2
# ---------------------------------------------------------------------------


async def test_first_upsert_adds_only_the_unknown_channels(
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    tenant_session: TenantSessionFactory,
) -> None:
    """Olti kanal topildi, uchtasi seed'da bor edi -> uchtasi QO'SHILDI."""
    with nvr_rows(sync_owner_conn, two_markets) as seed:
        rows = seed.market_a
        started = _now()

        async with tenant_session(rows.market_id) as session:
            counts = await NvrRepository(session, rows.market_id).upsert_cameras(
                rows.nvr_id, started, _channels()
            )

        assert counts.channels_found == len(SCAN_CHANNELS)
        assert counts.channels_added == len(SCAN_CHANNELS) - len(A_CAMERA_CHANNELS)

        cameras = await _camera_rows(tenant_session, rows.market_id, rows.nvr_id)
        assert set(cameras) == set(SCAN_CHANNELS)
        # `stream_name` GLOBAL UNIQUE — hammasi farqli bo'lishi shart.
        stream_names = {camera["stream_name"] for camera in cameras.values()}
        assert len(stream_names) == len(SCAN_CHANNELS)


async def test_second_upsert_adds_nothing_and_keeps_identity(
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    tenant_session: TenantSessionFactory,
) -> None:
    """Ikkinchi skan: `channels_added = 0`, `id` va `first_seen_at` O'ZGARMAYDI.

    Bu SC#2 ning «takroriy kamera yozuvi yaratilmaydi» bandining to'g'ridan-
    to'g'ri o'lchovi. `last_seen_at` esa YANGILANADI — usiz
    `mark_missing_offline()` ning butun mantiqi ishlamasdi.
    """
    with nvr_rows(sync_owner_conn, two_markets) as seed:
        rows = seed.market_a
        first_run = _now()

        async with tenant_session(rows.market_id) as session:
            await NvrRepository(session, rows.market_id).upsert_cameras(
                rows.nvr_id, first_run, _channels()
            )
        before = await _camera_rows(tenant_session, rows.market_id, rows.nvr_id)

        second_run = first_run + timedelta(minutes=5)
        async with tenant_session(rows.market_id) as session:
            counts = await NvrRepository(session, rows.market_id).upsert_cameras(
                rows.nvr_id, second_run, _channels()
            )
        after = await _camera_rows(tenant_session, rows.market_id, rows.nvr_id)

        assert counts.channels_added == 0
        assert counts.channels_found == len(SCAN_CHANNELS)
        for channel_no in SCAN_CHANNELS:
            assert after[channel_no]["id"] == before[channel_no]["id"]
            assert after[channel_no]["first_seen_at"] == before[channel_no]["first_seen_at"]
            assert after[channel_no]["stream_name"] == before[channel_no]["stream_name"]
            assert after[channel_no]["last_seen_at"] == second_run


async def test_manually_renamed_camera_keeps_its_name(
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    tenant_session: TenantSessionFactory,
) -> None:
    """⚠ SC#2 NING YURAGI: admin qo'ygan nom qayta skanda SAQLANADI.

    Seed'da 2-kanalda `name_overridden = true` va nomi «Sabzavot qatori».
    NVR esa «Kanal 02» deydi. `CASE WHEN cameras.name_overridden` olib
    tashlansa AYNAN shu test qizaradi (sabotaj o'lchovi).
    """
    with nvr_rows(sync_owner_conn, two_markets) as seed:
        rows = seed.market_a
        before = await _camera_rows(tenant_session, rows.market_id, rows.nvr_id)
        overridden_channel = next(
            channel_no
            for channel_no, camera in before.items()
            if camera["id"] == rows.overridden_camera_id
        )
        admin_name = before[overridden_channel]["name"]

        async with tenant_session(rows.market_id) as session:
            await NvrRepository(session, rows.market_id).upsert_cameras(
                rows.nvr_id, _now(), _channels(name_prefix="NVR nomi")
            )

        after = await _camera_rows(tenant_session, rows.market_id, rows.nvr_id)
        assert after[overridden_channel]["name"] == admin_name
        assert after[overridden_channel]["name_overridden"] is True


async def test_untouched_camera_takes_the_new_nvr_name(
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    tenant_session: TenantSessionFactory,
) -> None:
    """NAZORAT BANDI: `name_overridden = false` bo'lgan kamera nomni OLADI.

    Usiz yuqoridagi test «nom hech qachon yangilanmaydi» degan xato
    implementatsiyada ham yashil qolardi.
    """
    with nvr_rows(sync_owner_conn, two_markets) as seed:
        rows = seed.market_a

        async with tenant_session(rows.market_id) as session:
            await NvrRepository(session, rows.market_id).upsert_cameras(
                rows.nvr_id, _now(), _channels(name_prefix="NVR nomi")
            )

        after = await _camera_rows(tenant_session, rows.market_id, rows.nvr_id)
        plain = [
            camera for camera in after.values() if camera["id"] not in {rows.overridden_camera_id}
        ]
        assert plain, "nazorat holati uchun kamida bitta oddiy kamera kerak"
        assert all(str(camera["name"]).startswith("NVR nomi") for camera in plain)


async def test_archived_camera_is_not_resurrected_by_a_rescan(
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    tenant_session: TenantSessionFactory,
) -> None:
    """D-10: arxivlangan kanal qayta skanda TIKLANMAYDI.

    `is_archived` `SET` ro'yxatidan butunlay tashqarida — `name_overridden`
    bilan bir xil semantika: kashfiyot NVR ni haqiqat manbai deb biladi,
    lekin ADMIN QARORI undan ustun.
    """
    with nvr_rows(sync_owner_conn, two_markets) as seed:
        rows = seed.market_a

        async with tenant_session(rows.market_id) as session:
            await NvrRepository(session, rows.market_id).upsert_cameras(
                rows.nvr_id, _now(), _channels()
            )

        after = await _camera_rows(tenant_session, rows.market_id, rows.nvr_id)
        archived = [camera for camera in after.values() if camera["id"] == rows.archived_camera_id]
        assert len(archived) == 1
        assert archived[0]["is_archived"] is True


async def test_changed_source_attributes_are_updated_and_audited(
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    tenant_session: TenantSessionFactory,
) -> None:
    """`source_ip`/`source_model` KUZATILADI va o'zgarishi auditga tushadi.

    5-fazada bu signal muhim: kamera almashtirilsa zona poligonlari
    yaroqsiz bo'lishi mumkin va «nega?» savoliga javob aynan shu
    `audit_log` qatoridan keladi (`03-RESEARCH.md` A.4).
    """
    with nvr_rows(sync_owner_conn, two_markets) as seed:
        rows = seed.market_a

        async with tenant_session(rows.market_id) as session:
            await NvrRepository(session, rows.market_id).upsert_cameras(
                rows.nvr_id, _now(), _channels(source_ip="192.168.1.10")
            )

        before_audit = await _camera_audit_count(tenant_session, rows.market_id)

        async with tenant_session(rows.market_id) as session:
            await NvrRepository(session, rows.market_id).upsert_cameras(
                rows.nvr_id,
                _now() + timedelta(minutes=1),
                _channels(source_ip="192.168.1.77", source_model="DS-2CD2085G1"),
            )

        after = await _camera_rows(tenant_session, rows.market_id, rows.nvr_id)
        assert all(camera["source_ip"] == "192.168.1.77" for camera in after.values())
        assert all(camera["source_model"] == "DS-2CD2085G1" for camera in after.values())
        assert await _camera_audit_count(tenant_session, rows.market_id) > before_audit


async def test_source_ip_is_stored_as_a_host_prefixed_inet(
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    tenant_session: TenantSessionFactory,
) -> None:
    """⚠ O'LCHANGAN ARTEFAKT — `inet` qiymati `/32` PREFIKSI BILAN saqlanadi.

    Bu test hech nimani «to'g'irlamaydi» — u FAKTNI qulflaydi, chunki fakt
    keyingi rejalarga sizib o'tadi:

      * **03-07 (API):** `source_ip` ni JSON'ga to'g'ridan-to'g'ri berish
        UI'da `192.168.1.10/32` ni ko'rsatardi. Serializatsiyada `host()`
        yoki unga teng normalizatsiya KERAK.
      * **5-faza:** «kamera almashtirildimi?» solishtiruvi ikkala tomonda
        ham bir xil shaklda bo'lgani uchun TO'G'RI ishlaydi — ya'ni bu
        artefakt u yerda muammo emas.

    Qiymat `nvr_devices.tunnel_subnet` (`cidr`) bilan ADASHTIRILMASIN: u
    yerda prefiks ma'noli, bu yerda esa manzil har doim bitta xost.
    """
    with nvr_rows(sync_owner_conn, two_markets) as seed:
        rows = seed.market_a

        async with tenant_session(rows.market_id) as session:
            await NvrRepository(session, rows.market_id).upsert_cameras(
                rows.nvr_id, _now(), _channels((1,), source_ip="192.168.1.10")
            )

        async with tenant_session(rows.market_id) as session:
            result = await session.execute(
                text(
                    "SELECT source_ip::text AS raw, host(source_ip) AS semantic "
                    "FROM cameras WHERE market_id = :market_id AND channel_no = 1"
                ),
                {"market_id": rows.market_id},
            )
            row = result.one()

        assert row.raw == "192.168.1.10/32"
        assert row.semantic == "192.168.1.10"


async def _camera_audit_count(tenant_session: TenantSessionFactory, market_id: UUID) -> int:
    async with tenant_session(market_id) as session:
        result = await session.execute(
            text(
                "SELECT count(*) FROM audit_log "
                "WHERE market_id = :market_id AND table_name = 'cameras' AND action = 'update'"
            ),
            {"market_id": market_id},
        )
        return int(result.scalar_one())


# ---------------------------------------------------------------------------
# Yo'qolgan kanal — OFLAYN, o'chirilmaydi (Pitfall 11)
# ---------------------------------------------------------------------------


async def test_missing_channel_goes_offline_and_the_row_survives(
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    tenant_session: TenantSessionFactory,
) -> None:
    """⚠ NAZORAT BANDI BILAN: qator soni KAMAYMAYDI.

    Ikkinchi assert siz «oflayn qilindi» da'vosi «o'chirildi» dan
    farqlanmasdi: ikkala holatda ham `status='online'` so'rovi bo'sh
    natija berardi.
    """
    with nvr_rows(sync_owner_conn, two_markets) as seed:
        rows = seed.market_a
        first_run = _now()

        async with tenant_session(rows.market_id) as session:
            await NvrRepository(session, rows.market_id).upsert_cameras(
                rows.nvr_id, first_run, _channels()
            )
        count_before = await _camera_count(tenant_session, rows.market_id, rows.nvr_id)

        # Ikkinchi skanda 5 va 6 kanallar KO'RINMADI.
        second_run = first_run + timedelta(minutes=10)
        async with tenant_session(rows.market_id) as session:
            repo = NvrRepository(session, rows.market_id)
            await repo.upsert_cameras(rows.nvr_id, second_run, _channels((1, 2, 3, 4)))
            marked = await repo.mark_missing_offline(rows.nvr_id, second_run)

        assert marked == 2

        after = await _camera_rows(tenant_session, rows.market_id, rows.nvr_id)
        assert after[5]["status"] == CameraStatus.OFFLINE.value
        assert after[6]["status"] == CameraStatus.OFFLINE.value
        assert after[1]["status"] == CameraStatus.ONLINE.value
        # ⚠ NAZORAT: qator soni O'ZGARMADI — hech nima o'chirilmadi.
        assert await _camera_count(tenant_session, rows.market_id, rows.nvr_id) == count_before


async def test_mark_missing_offline_is_idempotent(
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    tenant_session: TenantSessionFactory,
) -> None:
    """Ikkinchi chaqiruv `0` qaytaradi — allaqachon oflayn qator qayta yozilmaydi.

    Usiz har skan barcha oflayn kanallarni qayta yozardi va `audit_log`
    hech nima aytmaydigan qatorlar bilan to'lardi.
    """
    with nvr_rows(sync_owner_conn, two_markets) as seed:
        rows = seed.market_a
        first_run = _now()

        async with tenant_session(rows.market_id) as session:
            await NvrRepository(session, rows.market_id).upsert_cameras(
                rows.nvr_id, first_run, _channels()
            )

        second_run = first_run + timedelta(minutes=10)
        async with tenant_session(rows.market_id) as session:
            repo = NvrRepository(session, rows.market_id)
            await repo.upsert_cameras(rows.nvr_id, second_run, _channels((1, 2)))
            first_result = await repo.mark_missing_offline(rows.nvr_id, second_run)

        async with tenant_session(rows.market_id) as session:
            second_result = await NvrRepository(session, rows.market_id).mark_missing_offline(
                rows.nvr_id, second_run
            )

        assert first_result == 4
        assert second_result == 0


# ---------------------------------------------------------------------------
# Tenant chegarasi
# ---------------------------------------------------------------------------


async def test_upsert_with_a_foreign_nvr_id_creates_nothing(
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    tenant_session: TenantSessionFactory,
) -> None:
    """⚠ NAZORAT HOLATI: B bozorining `nvr_id` si bilan A da yozib bo'lmaydi.

    Composite FK `(market_id, nvr_id)` buni SXEMA darajasida to'sadi:
    `market_id` repozitoriydan (A) keladi, `nvr_id` esa B ga tegishli —
    bunday juftlik `nvr_devices` da YO'Q.

    Test IKKI bozorli seed'ga tayanadi va bu majburiy: B da qator
    bo'lmasa «hech nima yaratilmadi» da'vosi izolyatsiyani emas,
    jadvalning bo'shligini o'lchagan bo'lardi.
    """
    with nvr_rows(sync_owner_conn, two_markets) as seed:
        market_a = seed.market_a
        market_b = seed.market_b

        with pytest.raises(IntegrityError):
            async with tenant_session(market_a.market_id) as session:
                await NvrRepository(session, market_a.market_id).upsert_cameras(
                    market_b.nvr_id, _now(), _channels((11, 12))
                )

        # B ning kameralari TEGILMAGAN.
        assert await _camera_count(tenant_session, market_b.market_id, market_b.nvr_id) == len(
            market_b.camera_channels
        )


async def test_repository_never_sees_the_other_market_rows(
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    tenant_session: TenantSessionFactory,
) -> None:
    """`list_devices()` / `list_cameras()` faqat O'Z bozorini qaytaradi."""
    with nvr_rows(sync_owner_conn, two_markets) as seed:
        market_a = seed.market_a
        market_b = seed.market_b

        async with tenant_session(market_a.market_id) as session:
            repo = NvrRepository(session, market_a.market_id)
            devices = await repo.list_devices()
            cameras = await repo.list_cameras()

        assert [device.id for device in devices] == [market_a.nvr_id]
        assert all(camera.market_id == market_a.market_id for camera in cameras)
        # Arxivlangani ro'yxatda YO'Q (D-10).
        assert market_a.archived_camera_id not in {camera.id for camera in cameras}
        assert len(cameras) == len(market_a.active_camera_ids)
        assert market_b.nvr_id not in {device.id for device in devices}


# ---------------------------------------------------------------------------
# Rekvizit chegarasi — FAQAT `bytes`
# ---------------------------------------------------------------------------


async def test_credential_round_trips_as_opaque_bytes(
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    tenant_session: TenantSessionFactory,
) -> None:
    """Repozitoriy shifrlashni BILMAYDI — u faqat baytni saqlaydi va qaytaradi."""
    token = b"gAAAAA-bu-fernet-tokeni-o'rnida-turgan-bayt"

    with nvr_rows(sync_owner_conn, two_markets) as seed:
        rows = seed.market_a

        async with tenant_session(rows.market_id) as session:
            repo = NvrRepository(session, rows.market_id)
            await repo.put_credential(rows.nvr_id, token, key_version=1)

        async with tenant_session(rows.market_id) as session:
            stored = await NvrRepository(session, rows.market_id).get_credential(rows.nvr_id)

        assert stored == token


async def test_credential_write_leaves_no_audit_row(
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    tenant_session: TenantSessionFactory,
) -> None:
    """⚠ SC#4: `nvr_credentials` auditga UMUMAN tushmaydi.

    03-03 buni `pg_trigger` bo'yicha (trigger MAVJUD EMAS) isbotladi; bu
    yerda esa ILOVA YO'LIDAN o'lchanadi — parol haqiqatan yozilgandan
    keyin ham jadval nomi `audit_log` da paydo bo'lmaydi.

    NAZORAT BANDI: o'sha tranzaksiyada `cameras` uchun audit qatori
    PAYDO BO'LADI, ya'ni so'rov haqiqatan qator topa oladi va inkor
    da'vosi bo'sh natijadan kelib chiqmagan.
    """
    with nvr_rows(sync_owner_conn, two_markets) as seed:
        rows = seed.market_a

        async with tenant_session(rows.market_id) as session:
            repo = NvrRepository(session, rows.market_id)
            await repo.put_credential(rows.nvr_id, b"yangi-token", key_version=1)
            await repo.upsert_cameras(rows.nvr_id, _now(), _channels((1,), name_prefix="X"))

        async with tenant_session(rows.market_id) as session:
            result = await session.execute(
                text(
                    "SELECT table_name, count(*) AS n FROM audit_log "
                    "WHERE market_id = :market_id GROUP BY table_name"
                ),
                {"market_id": rows.market_id},
            )
            by_table = {row.table_name: row.n for row in result}

        assert "nvr_credentials" not in by_table
        assert by_table.get("cameras", 0) > 0


# ---------------------------------------------------------------------------
# Kashfiyot yugurishlari
# ---------------------------------------------------------------------------


async def test_active_run_id_is_none_until_a_run_is_queued(
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    tenant_session: TenantSessionFactory,
) -> None:
    """Seed'dagi yugurish `succeeded` — ya'ni FAOL emas."""
    with nvr_rows(sync_owner_conn, two_markets) as seed:
        rows = seed.market_a

        async with tenant_session(rows.market_id) as session:
            assert await NvrRepository(session, rows.market_id).active_run_id(rows.nvr_id) is None

        async with tenant_session(rows.market_id) as session:
            run_id = await NvrRepository(session, rows.market_id).create_run(rows.nvr_id)

        async with tenant_session(rows.market_id) as session:
            assert await NvrRepository(session, rows.market_id).active_run_id(rows.nvr_id) == run_id


async def test_second_active_run_is_blocked_by_the_partial_unique_index(
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    tenant_session: TenantSessionFactory,
) -> None:
    """Ikkinchi FAOL yugurish `23505` beradi (T-03-16).

    Repozitoriy oldindan TEKSHIRMAYDI — «tekshir-keyin-yoz» ikki parallel
    so'rovda ikkalasini ham o'tkazib yuborardi. Yagona ishonchli chegara —
    DB konstraytining o'zi.
    """
    with nvr_rows(sync_owner_conn, two_markets) as seed:
        rows = seed.market_a

        async with tenant_session(rows.market_id) as session:
            await NvrRepository(session, rows.market_id).create_run(rows.nvr_id)

        with pytest.raises(IntegrityError) as excinfo:
            async with tenant_session(rows.market_id) as session:
                await NvrRepository(session, rows.market_id).create_run(rows.nvr_id)

        assert excinfo.value.orig is not None
        assert getattr(excinfo.value.orig, "sqlstate", None) == "23505"


async def test_finish_run_masks_the_error_detail(
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    tenant_session: TenantSessionFactory,
) -> None:
    """⚠ T-03-28: xom ISAPI javobidagi rekvizit `error_detail` ga TUSHMAYDI.

    Bu jsonb'ga diagnostika uchun xom javob yoziladi va unda parol
    NOMLANGAN kalit sifatida bo'lishi mumkin. Filtr ichma-ich obyektni
    ham qamraydi — faqat yuqori daraja tekshirilsa `{"request":
    {"nvr_password": ...}}` ochiq qolardi.
    """
    with nvr_rows(sync_owner_conn, two_markets) as seed:
        rows = seed.market_a

        async with tenant_session(rows.market_id) as session:
            repo = NvrRepository(session, rows.market_id)
            run_id = await repo.create_run(rows.nvr_id)
            await repo.finish_run(
                run_id,
                DiscoveryRunStatus.FAILED.value,
                counts=UpsertCounts(channels_found=0, channels_added=0),
                error_code="nvr_auth_failed",
                error_detail={
                    "status": 401,
                    "request": {"nvr_password": "Sim12345", "username": "sbozor"},
                },
            )

        async with tenant_session(rows.market_id) as session:
            run = await NvrRepository(session, rows.market_id).get_run(run_id)

        assert run is not None
        assert run.error_detail is not None
        assert run.error_detail["request"]["nvr_password"] != "Sim12345"
        # Nazorat: sezgir BO'LMAGAN maydonlar joyida qoladi.
        assert run.error_detail["request"]["username"] == "sbozor"
        assert run.error_detail["status"] == 401


async def test_finish_run_writes_the_three_counts(
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    tenant_session: TenantSessionFactory,
) -> None:
    """`UpsertCounts` maydonlari jadval ustunlariga AYNAN nomma-nom tushadi."""
    with nvr_rows(sync_owner_conn, two_markets) as seed:
        rows = seed.market_a
        started = _now()

        async with tenant_session(rows.market_id) as session:
            repo = NvrRepository(session, rows.market_id)
            run_id = await repo.create_run(rows.nvr_id)
            counts = await repo.upsert_cameras(rows.nvr_id, started, _channels())
            marked = await repo.mark_missing_offline(rows.nvr_id, started)
            await repo.finish_run(
                run_id,
                DiscoveryRunStatus.SUCCEEDED.value,
                counts=counts.with_marked_offline(marked),
            )

        async with tenant_session(rows.market_id) as session:
            run = await NvrRepository(session, rows.market_id).get_run(run_id)

        assert run is not None
        assert run.status == DiscoveryRunStatus.SUCCEEDED.value
        assert run.channels_found == len(SCAN_CHANNELS)
        assert run.channels_added == len(SCAN_CHANNELS) - len(A_CAMERA_CHANNELS)
        assert run.channels_marked_offline == marked
        assert run.finished_at is not None


# ---------------------------------------------------------------------------
# Qurilma va nom amallari
# ---------------------------------------------------------------------------


async def test_rename_sets_the_override_flag_in_one_statement(
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    tenant_session: TenantSessionFactory,
) -> None:
    """`rename_camera()` nom va bayroqni BIRGA qo'yadi; `reset` bayroqni tushiradi."""
    with nvr_rows(sync_owner_conn, two_markets) as seed:
        rows = seed.market_a
        target = rows.camera_ids[0]

        async with tenant_session(rows.market_id) as session:
            assert await NvrRepository(session, rows.market_id).rename_camera(
                target, "Go'sht rastasi"
            )

        cameras = await _camera_rows(tenant_session, rows.market_id, rows.nvr_id)
        renamed = next(camera for camera in cameras.values() if camera["id"] == target)
        assert renamed["name"] == "Go'sht rastasi"
        assert renamed["name_overridden"] is True

        # Qayta skan unga TEGMAYDI.
        async with tenant_session(rows.market_id) as session:
            await NvrRepository(session, rows.market_id).upsert_cameras(
                rows.nvr_id, _now(), _channels(name_prefix="NVR")
            )
        cameras = await _camera_rows(tenant_session, rows.market_id, rows.nvr_id)
        assert next(c for c in cameras.values() if c["id"] == target)["name"] == "Go'sht rastasi"

        # Bayroq tushirilgandan keyin esa keyingi skan nomni QAYTARADI.
        async with tenant_session(rows.market_id) as session:
            assert await NvrRepository(session, rows.market_id).reset_camera_name(target)
        async with tenant_session(rows.market_id) as session:
            await NvrRepository(session, rows.market_id).upsert_cameras(
                rows.nvr_id, _now(), _channels(name_prefix="NVR")
            )
        cameras = await _camera_rows(tenant_session, rows.market_id, rows.nvr_id)
        assert str(next(c for c in cameras.values() if c["id"] == target)["name"]).startswith("NVR")


async def test_archive_and_restore_never_remove_the_row(
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    tenant_session: TenantSessionFactory,
) -> None:
    """D-10: arxivlash — bayroq, o'chirish EMAS."""
    with nvr_rows(sync_owner_conn, two_markets) as seed:
        rows = seed.market_a
        target = rows.camera_ids[0]
        count_before = await _camera_count(tenant_session, rows.market_id, rows.nvr_id)

        async with tenant_session(rows.market_id) as session:
            assert await NvrRepository(session, rows.market_id).archive_camera(target)
        assert await _camera_count(tenant_session, rows.market_id, rows.nvr_id) == count_before

        async with tenant_session(rows.market_id) as session:
            active = await NvrRepository(session, rows.market_id).list_cameras()
        assert target not in {camera.id for camera in active}

        async with tenant_session(rows.market_id) as session:
            assert await NvrRepository(session, rows.market_id).restore_camera(target)
        async with tenant_session(rows.market_id) as session:
            active = await NvrRepository(session, rows.market_id).list_cameras()
        assert target in {camera.id for camera in active}


async def test_create_device_writes_under_the_repository_market(
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    tenant_session: TenantSessionFactory,
) -> None:
    """`market_id` REPOZITORIYDAN keladi — argumentdan emas (mass-assignment).

    ⚠ Xost seed'dagidan FARQLI: `uq_nvr_devices_market_id_host_port` (03-03)
      bir bozorda bir xil `host:port` ni ikki marta yozishga yo'l qo'ymaydi.
      Seed'ning xosti (`A_HOST`) ishlatilsa test `23505` bilan yiqilardi va
      sabab «yaratish ishlamayapti» bo'lib ko'rinardi.
    """
    with nvr_rows(sync_owner_conn, two_markets) as seed:
        rows = seed.market_a
        assert rows.host == A_HOST

        async with tenant_session(rows.market_id) as session:
            nvr_id = await NvrRepository(session, rows.market_id).create_device(
                host="192.168.9.9", port=8080, username="sbozor"
            )

        async with tenant_session(rows.market_id) as session:
            device = await NvrRepository(session, rows.market_id).get_device(nvr_id)

        assert device is not None
        assert device.market_id == rows.market_id
        assert device.rtsp_port is None
        assert device.rtsp_port_assumed is False


async def test_update_device_records_the_discovered_rtsp_port(
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    tenant_session: TenantSessionFactory,
) -> None:
    """Kashf etilgan RTSP porti va «taxmin qilindi» bayrog'i yoziladi (A.2)."""
    with nvr_rows(sync_owner_conn, two_markets) as seed:
        rows = seed.market_a

        async with tenant_session(rows.market_id) as session:
            assert await NvrRepository(session, rows.market_id).update_device(
                rows.nvr_id, rtsp_port=10554, rtsp_port_assumed=False
            )

        async with tenant_session(rows.market_id) as session:
            device = await NvrRepository(session, rows.market_id).get_device(rows.nvr_id)

        assert device is not None
        assert device.rtsp_port == 10554


async def test_unknown_ids_return_falsey_rather_than_raising(
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    tenant_session: TenantSessionFactory,
) -> None:
    """Noma'lum `id` — `None`/`False`, istisno EMAS.

    Chaqiruvchi (03-07) 404 ni shu javobdan hosil qiladi; istisno bo'lsa
    u 500 ga aylanardi va sabab «server xatosi» bo'lib ko'rinardi.
    """
    with nvr_rows(sync_owner_conn, two_markets) as seed:
        rows = seed.market_a
        ghost = uuid4()

        async with tenant_session(rows.market_id) as session:
            repo = NvrRepository(session, rows.market_id)
            assert await repo.get_device(ghost) is None
            assert await repo.get_run(ghost) is None
            assert await repo.get_credential(ghost) is None
            assert await repo.rename_camera(ghost, "yo'q") is False
            assert await repo.archive_camera(ghost) is False
            assert await repo.update_device(ghost, model="X") is False


async def test_upsert_with_no_channels_is_a_no_op(
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    tenant_session: TenantSessionFactory,
) -> None:
    """Bo'sh ro'yxat — nol sonlar, hech qanday yozuv yo'q.

    NVR javob berib, birorta kanal qaytarmasligi HAQIQIY holat (barcha
    kanallar o'chirilgan qurilma). Bo'sh `INSERT ... VALUES ()` esa SQL
    xatosi berardi.
    """
    with nvr_rows(sync_owner_conn, two_markets) as seed:
        rows = seed.market_a
        count_before = await _camera_count(tenant_session, rows.market_id, rows.nvr_id)

        async with tenant_session(rows.market_id) as session:
            counts = await NvrRepository(session, rows.market_id).upsert_cameras(
                rows.nvr_id, _now(), []
            )

        assert counts == UpsertCounts(channels_found=0, channels_added=0)
        assert await _camera_count(tenant_session, rows.market_id, rows.nvr_id) == count_before


def test_module_has_no_hard_delete(request: pytest.FixtureRequest) -> None:
    """⚠ MEXANIK DARVOZA: modulda qattiq o'chirish operatori YO'Q (Pitfall 11).

    Testning o'zi ham `delete(` / `DELETE FROM` literallarini YOZMAYDI —
    ular naqsh bo'lib qidirilayotgani uchun matnda paydo bo'lsa darvoza
    o'z-o'ziga qarshi ishlardi. Shuning uchun naqsh bo'laklardan
    yig'iladi.
    """
    from pathlib import Path

    source = (
        Path(request.config.rootpath) / "services/core-api/app/repositories/nvr_repo.py"
    ).read_text(encoding="utf-8")

    forbidden = ("dele" + "te(Camera)", "DELE" + "TE FROM cameras", "sess" + "ion.delete")
    found = [pattern for pattern in forbidden if pattern in source]
    assert not found, f"nvr_repo.py da qattiq o'chirish topildi: {found}"
