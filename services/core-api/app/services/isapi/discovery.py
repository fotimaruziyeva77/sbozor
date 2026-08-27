"""Kashfiyot orkestratsiyasi — SC#1 va SC#2 ning bajarilish joyi.

=============================================================================
BU FAYL NAVBAT KUTUBXONASINI IMPORT QILMAYDI (D-06).

`run_discovery` — SOF `async def` funksiya. Navbat kutubxonasi faqat
`app/worker.py` da, YUPQA QOBIQ sifatida ko'rinadi:

    @broker.task
    async def discover(nvr_id: str) -> None:
        async with ... as (repo, client):
            await run_discovery(repo, client, nvr_id=..., run_started_at=...)

Sabab: 4-faza boshqa mexanizmni tanlashi mumkin (`arq` bu loyihada
o'rnatilmaydi — u `redis<6` talab qiladi, `core-api` esa `8.0.1` da) va
ko'chirish narxi ~10 QATOR bo'lishi kerak, butun kashfiyot mantig'ini
qayta yozish emas. Ikki mexanizm bir vaqtda saqlanmaydi.

⚠ Buni `grep -cE "^\\s*(import|from)\\s+taskiq"` mexanik tekshiradi.
=============================================================================

=============================================================================
XATO BU YERDA YUTILMAYDI — U YUQORIGA KO'TARILADI.

`NvrError` `run_discovery` dan CHIQIB KETADI. `nvr_discovery_runs` ga
`error_code`/`error_detail` yozish — JOB QATLAMINING ishi (03-06), chunki
aynan o'sha qatlam `create_run`/`finish_run` juftligiga egalik qiladi.

Agar bu fayl xatoni yutib, `DiscoveryOutcome(error_code=...)` qaytarsa,
chaqiruvchi «muvaffaqiyatli natija» ni «xato natija» dan FAQAT maydonni
tekshirib ajratardi va uni unutish JIMGINA «succeeded» holatini yozardi.
Istisno esa unutib bo'lmaydigan mexanizm.

`DiscoveryOutcome` da `error_code` maydoni BOR, lekin uni bu modul
TO'LDIRMAYDI: u 03-06 ga tegishli shakl va shu yerda e'lon qilinishi
ikkala tomonning bitta shaklga qarashini ta'minlaydi.
=============================================================================
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import structlog
from sbozor_core.enums import CameraStatus

from app.repositories.nvr_repo import DiscoveredChannel, UpsertCounts
from app.services.isapi.client import (
    NVR_DEVICE_TYPES,
    assert_supported_device,
    resolve_rtsp_port,
)
from app.services.isapi.errors import NvrError
from app.services.isapi.parser import parse_admin_accesses, parse_channel_status, parse_device_info
from app.services.rtsp import stream_id

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from datetime import datetime
    from uuid import UUID

    from app.repositories.nvr_repo import NvrRepository
    from app.services.isapi.client import IsapiClient
    from app.services.isapi.parser import ChannelRow, DeviceInfo

log = structlog.get_logger(__name__)

__all__ = ["DiscoveryOutcome", "run_discovery"]

# ⚠ QO'LLAB-QUVVATLASH TEKSHIRUVI `client.py::assert_supported_device` DA,
#   BU YERDA EMAS — va bu ataylab. U `probe()` («ulanishni tekshirish»
#   tugmasi) va `run_discovery` (fon jobi) tomonidan BIR XIL bajarilishi
#   shart: ikki nusxa bo'lganda tugma «qurilma qo'llab-quvvatlanmaydi»
#   deb, job esa yarim to'ldirilgan kameralarni yaratib qo'yardi.
#   Tekshiruvning O'ZI kashfiyotning BOSHIDA turadi.


@dataclass(frozen=True, slots=True)
class DiscoveryOutcome:
    """Bitta kashfiyot yugurishining natijasi.

    ⚠ `counts.channels_found` NING TA'RIFI (UI-SPEC §6.3 [TALAB]):
      **shu yugurishda SANAB CHIQILGAN kanallar soni — onlayn/oflayn
      holatidan QAT'I NAZAR.**

      Ta'rif aniq bo'lishi shart, chunki UI uchinchi hisoblagichni undan
      HOSILA qilib chiqaradi:

          unchanged = channels_found − channels_added

      Agar `channels_found` faqat ONLAYN kanallarni sanaganda, ikkita
      kamera oflayn bo'lgan bozorda «o'zgarishsiz» soni ikkitaga kam
      chiqardi va admin uni «ikkita kamera yo'qoldi» deb o'qirdi —
      hech narsa yo'qolmagan holda.
    """

    counts: UpsertCounts
    device: DeviceInfo
    rtsp_port: int
    rtsp_port_assumed: bool
    channel_issues: tuple[NvrError, ...] = ()
    """Kashfiyotni TO'XTATMAGAN, lekin foydalanuvchiga aytiladigan sabablar.

    Hozircha bitta manba: `channel_offline`. U BLOK EMAS (UI-SPEC §7.3 —
    «qator badge'i»), ya'ni kamera yozuvi BARIBIR yaratiladi va skan
    `succeeded` bo'lib qoladi (UI-SPEC §6.4: «bu eng ko'p uchraydigan
    real holat va u xato EMAS»).

    ⚠ NEGA `NvrError` QIYMAT SIFATIDA: unda `code` ham, `detail` ham bor
      va konstruktor `ERROR_DETAIL_KEYS` allowlist'ini MAJBURLAYDI. Yangi
      dataclass yasash o'sha tekshiruvni ikkinchi marta yozishni talab
      qilardi — yoki (ehtimolroq) uni umuman yozmaslikni. `channel_no` va
      `channel_name` kalitlari allowlist'da AYNAN shu holat uchun bor.
    """

    error_code: str | None = None
    error_detail: dict[str, Any] = field(default_factory=dict)
    """03-06 ning job qatlami to'ldiradi — bu modul EMAS (modul docstringi)."""


async def run_discovery(
    repo: NvrRepository,
    client: IsapiClient,
    *,
    nvr_id: UUID,
    run_started_at: datetime,
    on_channels_found: Callable[[int], Awaitable[None]] | None = None,
    probe_substreams: bool = True,
) -> DiscoveryOutcome:
    """Manzil va rekvizitdan kameralargacha — SC#1 ning butun yo'li.

    Ketma-ketlik `03-RESEARCH.md` A.1 dan:

        1. `System/deviceInfo`       -> model, seriya, `deviceType`
        2. `Security/adminAccesses`  -> RTSP porti (554 TAXMIN QILINMAYDI)
        3. `deviceType` bo'yicha     -> kanal ro'yxati (D-04)
        4. `channels_found` -> `on_channels_found` CALLBACK
        5. har kanal uchun sub-oqim tekshiruvi (sozlanadigan)
        6. `upsert_cameras` -> `mark_missing_offline`

    Args:
        repo: tenant doirasidagi repozitoriy.
        client: ochilgan `IsapiClient` (egaligi CHAQIRUVCHIDA).
        nvr_id: qurilma.
        run_started_at: shu skanning YAGONA vaqt tamg'asi. `now()` emas —
            `upsert_cameras` va `mark_missing_offline` uni taqqoslaydi va
            ikki xil vaqt chegarada noaniqlik berardi (03-04).
        on_channels_found: kanallar ro'yxati parse qilinishi bilanoq
            chaqiriladi.
        probe_substreams: `False` bo'lsa har kanal uchun bitta HTTP
            borish tejaladi.

    Raises:
        NvrError: har qanday ISAPI muammosi. Bu yerda YUTILMAYDI.
    """
    device = parse_device_info(await client.get_xml("System/deviceInfo"))
    assert_supported_device(device)

    protocols = parse_admin_accesses(await client.get_xml("Security/adminAccesses"))
    rtsp_port, rtsp_port_assumed = resolve_rtsp_port(protocols)

    rows = await client.list_channels(device)

    # ------------------------------------------------------------------
    # 4-QADAM — UI-SPEC §5.2 [TALAB] VA U SHU YERDA, AYNAN SHU JOYDA.
    #
    # `channels_found` sub-oqim tekshiruvlaridan OLDIN e'lon qilinadi.
    # Sabab byudjet hisobida: vaqtning KATTA QISMI (25 kanal × borish)
    # aynan quyidagi tsiklga ketadi. Callback keyinga surilsa admin ~50
    # soniya davomida BIR XIL «yuklanmoqda» ni ko'rardi va u «osilib
    # qoldi» dan farqlanmasdi. Bitta qo'shimcha yangilanish o'sha
    # qorong'ilikni ikkita o'qiladigan bosqichga ajratadi.
    #
    # Callback `None` bo'lsa hech narsa bo'lmaydi: talab UI'ni ham,
    # testni ham BLOKLAMAYDI.
    # ------------------------------------------------------------------
    channels_found = len(rows)
    if on_channels_found is not None:
        await on_channels_found(channels_found)

    statuses = await _channel_statuses(client, device)
    issues: list[NvrError] = []
    channels: list[DiscoveredChannel] = []

    for row in rows:
        online = statuses.get(row.channel_no, True)
        if not online:
            # Kamera yozuvi BARIBIR yaratiladi (SC#2) — faqat `status`
            # boshqacha. Sabab foydalanuvchiga qator badge'ida aytiladi.
            issues.append(
                NvrError(
                    "channel_offline", {"channel_no": row.channel_no, "channel_name": row.name}
                )
            )
        channels.append(
            DiscoveredChannel(
                channel_no=row.channel_no,
                name=row.name,
                status=CameraStatus.ONLINE.value if online else CameraStatus.OFFLINE.value,
                source_ip=row.source_ip,
                source_model=row.source_model,
                has_substream=await _has_substream(client, row, enabled=probe_substreams),
            )
        )

    counts = await repo.upsert_cameras(nvr_id, run_started_at, channels)
    marked_offline = await repo.mark_missing_offline(nvr_id, run_started_at)
    counts = counts.with_marked_offline(marked_offline)

    await repo.update_device(
        nvr_id,
        model=device.model,
        device_type=device.device_type,
        serial_number=device.serial_number,
        firmware_version=device.firmware_version,
        rtsp_port=rtsp_port,
        rtsp_port_assumed=rtsp_port_assumed,
        last_discovery_at=run_started_at,
    )

    log.info(
        "nvr_discovery_finished",
        channels_found=counts.channels_found,
        channels_added=counts.channels_added,
        channels_marked_offline=counts.channels_marked_offline,
        rtsp_port=rtsp_port,
        rtsp_port_assumed=rtsp_port_assumed,
    )

    return DiscoveryOutcome(
        counts=UpsertCounts(
            # ⚠ `channels_found` ROSTLANADI: `upsert_cameras` uni O'ZI
            #   ko'rgan qatorlardan sanaydi, ta'rif esa «shu yugurishda
            #   SANAB CHIQILGAN» deydi. Bo'sh ro'yxatda ular farq qiladi
            #   (repozitoriy `0` beradi va yozmaydi) va o'sha yagona
            #   holatda UI formulasi noto'g'ri chiqardi.
            channels_found=channels_found,
            channels_added=counts.channels_added,
            channels_marked_offline=counts.channels_marked_offline,
        ),
        device=device,
        rtsp_port=rtsp_port,
        rtsp_port_assumed=rtsp_port_assumed,
        channel_issues=tuple(issues),
    )


async def _channel_statuses(client: IsapiClient, device: DeviceInfo) -> dict[int, bool]:
    """`.../channels/status` — FAQAT NVR yo'lida (D-04).

    Standalone IP-kamerada bunday endpoint YO'Q: qurilmaning o'zi kanal,
    va u so'rovga javob berayotgan bo'lsa u allaqachon onlayn.
    """
    if device.device_type.upper() not in NVR_DEVICE_TYPES:
        return {}
    return parse_channel_status(await client.get_xml("ContentMgmt/InputProxy/channels/status"))


async def _has_substream(client: IsapiClient, row: ChannelRow, *, enabled: bool) -> bool:
    """`{ch}02` mavjudmi (A.2). Tekshiruv o'chirilgan bo'lsa `True` deb hisoblanadi.

    ⚠ SUB-OQIM MAVJUDLIGI KAFOLATLANMAGAN va bu 4-fazada muhim bo'ladi:
      go2rtc DOIMIY ravishda faqat sub-oqimga ulanadi (A.5 — 25 kanal
      asosiy oqimda ~100 Mbps, sub-oqimda ~12 Mbps). Sub-oqimi yo'q kanal
      alohida muomalani talab qiladi va uni KASHFIYOT paytida bilish
      kerak, kadr olish paytida emas.

    ⚠ `nvr_isapi_unavailable` bu yerda «sub-oqim yo'q» deb o'qiladi va
      bu OCHIQ QISQARTMA: `404` ham, ISAPI ning butunlay yo'qolishi ham
      shu kodni beradi. Farqi shundaki, bu nuqtaga yetish uchun
      `deviceInfo` va `adminAccesses` allaqachon MUVAFFAQIYATLI o'tgan —
      ya'ni ISAPI ishlayapti va `404` kanalga tegishli.

    Qolgan barcha kodlar (`nvr_stream_limit`, `nvr_unreachable`, …)
    YUQORIGA KO'TARILADI: chegaraga urilgan skanni «sub-oqimi yo'q»
    deb yozib qo'yish ma'lumotni jimgina buzardi.
    """
    if not enabled:
        return True
    try:
        await client.get_xml(f"Streaming/channels/{stream_id(row.channel_no, substream=True)}")
    except NvrError as error:
        if error.code == "nvr_isapi_unavailable":
            return False
        raise
    return True
