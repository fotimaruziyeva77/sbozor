"""«Direktor tasvirni KO'RADI» — MAHSULOT YO'LIDAN o'tadigan, MOCK'SIZ o'lchov.

=============================================================================
BU FAYL NIMANI YOPADI.

`03-VERIFICATION.md` fazani **5/8** ga tushirgan ikkita bo'shliq qoldirdi:

  * **GAP-1** — SC#6 ning ikkinchi yarmi («tasvirni ko'radi») na o'lchangan,
    na ULANGAN edi;
  * **GAP-2** — SC#7 zanjirining OXIRGI bo'g'ini mock bilan kesilardi
    (`Go2rtcClient` almashtirilardi), ya'ni media hech qachon oqmasdi.

Shu fayl zanjirni oxirigacha, BIRORTA MOCK'SIZ kesib o'tadi:

    admin formasi -> saqlash -> kashfiyot jobi -> poll -> kameralar reestri
    -> DIREKTOR jonli ko'rish chiptasi -> go2rtc'da oqim (REKVIZIT bilan)
    -> `/api/frame.jpeg` -> HAQIQIY JPEG kadr

=============================================================================
⚠⚠ NEGA NOMLAR KASHFIYOTDAN OLINADI, TESTDAN EMAS.

`03-VALIDATION.md` ning `open_items` da boshqa yopilish yo'li taklif
qilingan edi: «sim'dan bitta kadr olib JPEG ekanini tekshirish».
`03-VERIFICATION.md` uni ATAYIN RAD ETDI va sabab aniq — u mahsulot
yo'lini CHETLAB O'TARDI. Kashfiyot `cam_<uuid4>` oqim nomini va
`<sxema>://<nvr_devices.host>:<kashf-etilgan-port>/...` manbasini O'ZI
hosil qiladi; o'z nomini o'ylab topgan test esa mahsulot haqida HECH
NIMA isbotlamasdi — bu aynan Pitfall 4 (simulyatorning o'zini o'zi
tasdiqlashi) bo'lardi.

Shuning uchun bu yerda:
  * oqim nomi CHIPTA JAVOBIDAN, uning `url` idagi `src=` dan olinadi
    (javobda alohida maydon sifatida ATAYIN yo'q — UI-SPEC §8.7);
  * manba `_ensure_stream()` tomonidan quriladi va rekvizit oyog'i
    (`decrypt_nvr_password` -> `authenticated_rtsp_source`) MAHSULOT
    KODIDA bajariladi;
  * `Go2rtcClient` ALMASHTIRILMAYDI — `PUT /api/streams` haqiqiy go2rtc
    konteyneriga ketadi va u haqiqiy `nvr-sim:554` ga ulanadi.

=============================================================================
⚠⚠ SIR CI JURNALIGA CHIQMAYDI (T-03-94).

`GET /api/streams` javobi BARCHA bozorlarning REKVIZITLI `src` larini
o'z ichiga oladi (T-03-90), kadr esa binar. Shuning uchun bu faylda:

  * javob TANASI hech qayerda chop etilmaydi va assert xabariga
    qo'yilmaydi — faqat kalitlar (`cam_<uuid4>`) va SANOQLAR;
  * chipta javobining tanasi ham xabarga qo'yilmaydi (`t=` — 60 soniyalik
    jonli chipta, D-08);
  * yiqilish xabarida ruxsat etilgani: oqim nomi, o'tgan soniyalar,
    urinishlar soni, oxirgi HTTP status kodi va tananing UZUNLIGI.

=============================================================================
⚠ NEGA AYNAN `/api/frame.jpeg`.

Bu 4-fazaning STANDART kadr olish yo'li (`CLAUDE.md` § «Snapshot capture»,
`03-RESEARCH.md` D.14): go2rtc RTSP sessiyasini ochiq ushlab turadi va
snapshot oddiy HTTP `GET` ga aylanadi. Ya'ni bu test bugungi bo'shliqni
yopishdan tashqari keyingi fazaning OLDINGI SHARTINI ham o'lchaydi —
`03-VERIFICATION.md` uni aynan shunday nomlagan.
=============================================================================
"""

from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING, NamedTuple
from urllib.parse import parse_qs, urlsplit
from uuid import UUID

import httpx
import pytest
from app.services.go2rtc import GO2RTC_STREAMS_PATH, Go2rtcClient
from fixtures.admin_api import session_headers
from fixtures.nvr_flow import CAMERAS_URL, create_device, list_cameras, run_discovery
from fixtures.two_markets import SEED_PASSWORD

if TYPE_CHECKING:
    from typing import Any

    from app.settings import Settings
    from fixtures.two_markets import TwoMarketSeed
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

pytestmark = [pytest.mark.sim, pytest.mark.usefixtures("migrated")]

FRAME_PATH = "/api/frame.jpeg"
"""go2rtc ning kadr olish yo'li — 4-fazaning standart mexanizmi."""

JPEG_SOI = b"\xff\xd8\xff"
"""JPEG ning boshlanish markeri (SOI + birinchi marker bayti).

Status kodi va uzunlik YETMAYDI: go2rtc xato holatida ham 200 bilan
matnli tana qaytarishi mumkin, uzunlik esa o'sha matn uchun ham
noldan katta bo'lardi.
"""

MIN_FRAME_BYTES = 1024
"""Eng kichik ishonarli kadr.

`nvr-sim` ning ISAPI `/picture` yo'li 160 baytli `TINY_JPEG` beradi
(protokol modeli, piksel emas). Bu yerdagi kadr esa HAQIQIY media
quvuridan keladi (`testsrc2` 1280x720 -> H.264 -> go2rtc -> JPEG), ya'ni
u kilobaytlarda o'lchanadi. Chegara ikkalasini ajratadi.
"""

FRAME_DEADLINE_SECONDS = 45.0
"""Kadr kutishning QATTIQ chegarasi.

`runOnDemand` ffmpeg birinchi tomoshabin kelganda ishga tushadi va
keyframe (`-g 24`) kutiladi — o'lchangan qiymat ~2 s. 45 s ~20 barobar
zaxira, LEKIN u cheksiz emas: osilgan test butun to'plamni bloklardi
(`fixtures/nvr_sim.py` ning A.3 qoidasi).
"""

FRAME_POLL_INTERVAL_SECONDS = 1.0
FRAME_TIMEOUT = httpx.Timeout(10.0, connect=5.0)

STREAMS_TIMEOUT = httpx.Timeout(5.0, connect=5.0)


class FrameProbe(NamedTuple):
    """Kadr kutishning NATIJASI — sirsiz maydonlar (T-03-94).

    Tananing O'ZI bu yerda YO'Q va bu ataylab: `NamedTuple` ning `repr()`
    i pytest diffida to'liq chiqadi, ya'ni binar kadr (yoki xato matni)
    CI jurnaliga tushardi.
    """

    arrived: bool
    elapsed: float
    attempts: int
    status: int | None
    length: int
    transport_error: str | None


@pytest.fixture
async def admin_headers(
    api_client: httpx.AsyncClient,
    two_markets: TwoMarketSeed,
) -> dict[str, str]:
    """A bozori adminining sessiyasi (`CAMERA_MANAGE` + `CAMERA_VIEW`)."""
    market_a = two_markets.market_a
    return await session_headers(api_client, market_a.admin_phone, market_a.admin_password)


@pytest.fixture
async def director_headers(
    api_client: httpx.AsyncClient,
    two_markets: TwoMarketSeed,
) -> dict[str, str]:
    """A bozori DIREKTORI — mezon aynan uni nomlaydi (`CAMERA_VIEW`, D-07)."""
    return await session_headers(api_client, two_markets.market_a.director_phone, SEED_PASSWORD)


def _stream_name_from(live_url: str) -> str:
    """Oqim nomini OPAQUE chipta manzilidan ajratadi.

    ⚠ Javobda alohida `stream_name` maydoni ATAYIN YO'Q (UI-SPEC §8.7) va
      bu qoida o'zgarmaydi: alohida maydon UI'da ko'rsatilardi va nusxa
      olinardi. Test uni shu sababdan URL'dan oladi — ya'ni u mahsulot
      shartnomasini kengaytirishni TALAB QILMAYDI.

    ⚠ `t=` (jonli chipta) bu yerdan CHIQMAYDI va hech qayerga yozilmaydi.
    """
    params = parse_qs(urlsplit(live_url).query)
    names = params.get("src", [])
    assert len(names) == 1, (
        f"jonli ko'rish manzilida `src` {len(names)} marta uchradi — chipta "
        "manzilining shakli o'zgargan"
    )
    name = names[0]
    assert name, "jonli ko'rish manzilidagi `src` bo'sh"
    return name


async def _stream_names(go2rtc_url: str) -> frozenset[str]:
    """go2rtc'dagi oqim NOMLARI — javob TANASI hech qayerga chiqmaydi.

    ⚠ FAQAT KALITLAR. Qiymatlar rekvizitli `src` larni tashiydi (T-03-90),
      ya'ni bitta `assert ..., payload` butun o'rnatmaning NVR parollarini
      CI jurnaliga chiqarardi.
    """
    async with httpx.AsyncClient(base_url=go2rtc_url, timeout=STREAMS_TIMEOUT) as client:
        response = await client.get(GO2RTC_STREAMS_PATH)
        response.raise_for_status()
        payload: Any = response.json()

    assert isinstance(payload, dict), "go2rtc `/api/streams` javobi obyekt emas"
    return frozenset(payload)


async def _await_first_frame(go2rtc_url: str, stream_name: str) -> FrameProbe:
    """Kadr kelgunicha CHEGARALANGAN tsiklda so'raydi.

    Birinchi so'rov odatda kadr bermaydi va bu NORMAL: go2rtc RTSP
    sessiyasini shu chaqiruvda ochadi, `nvr-sim-rtsp` esa `runOnDemand`
    ffmpeg'ini shundan keyin ishga tushiradi va keyframe kutiladi.
    """
    started = time.monotonic()
    deadline = started + FRAME_DEADLINE_SECONDS
    attempts = 0
    status: int | None = None
    length = 0
    transport_error: str | None = None

    async with httpx.AsyncClient(base_url=go2rtc_url, timeout=FRAME_TIMEOUT) as client:
        while True:
            attempts += 1
            try:
                response = await client.get(FRAME_PATH, params={"src": stream_name})
            except httpx.HTTPError as exc:
                # ⚠ FAQAT SINF NOMI: `httpx` istisnosining matni to'liq
                #   so'rov URL'ini tashiydi (T-03-87 dagi bilan bir xil
                #   sabab). Bu yerda URL'da sir yo'q, lekin qoida bir
                #   xil qolishi kerak — keyingi tahrirlovchi buni
                #   «to'g'ri namuna» deb nusxalaydi.
                status, length, transport_error = None, 0, type(exc).__name__
            else:
                body = response.content
                status, length, transport_error = response.status_code, len(body), None
                if status == 200 and body[:3] == JPEG_SOI and length >= MIN_FRAME_BYTES:
                    return FrameProbe(
                        arrived=True,
                        elapsed=time.monotonic() - started,
                        attempts=attempts,
                        status=status,
                        length=length,
                        transport_error=None,
                    )

            if time.monotonic() >= deadline:
                return FrameProbe(
                    arrived=False,
                    elapsed=time.monotonic() - started,
                    attempts=attempts,
                    status=status,
                    length=length,
                    transport_error=transport_error,
                )
            await asyncio.sleep(FRAME_POLL_INTERVAL_SECONDS)


async def test_a_frame_arrives_through_the_discovered_stream(
    sim: str,
    sim_credentials: tuple[str, str],
    api_client: httpx.AsyncClient,
    admin_headers: dict[str, str],
    director_headers: dict[str, str],
    enqueued: list[dict[str, Any]],
    api_sessionmaker: async_sessionmaker[AsyncSession],
    test_settings: Settings,
    nvr_cleanup: None,
) -> None:
    """Zanjir KADR bilan tugaydi — SC#6 ning ikkinchi yarmi va SC#7 ning oxirgi bo'g'ini.

    BEShTA BO'G'IN, HAMMASI BIR SESSIYADA VA BIRORTA MOCK'SIZ:

      1. admin uch maydonli formani yuboradi (`create_device`);
      2. kashfiyot jobi kanallarni sanaydi va kameralarni YARATADI;
      3. **direktor** chipta so'raydi — bu chaqiruv MAHSULOT
         `Go2rtcClient` ini ishlatadi, ya'ni haqiqiy `PUT /api/streams`
         REKVIZITLI manba bilan ketadi (03-13);
      4. oqim nomi chipta manzilining `src=` idan olinadi — kashfiyot
         hosil qilgan `cam_<uuid4>`, test o'ylab topgan nom EMAS;
      5. `/api/frame.jpeg` HAQIQIY JPEG qaytaradi.

    ⚠ 5-BO'G'IN 3-BO'G'INSIZ ISHLAMAYDI VA BU O'LCHOVNING BUTUN MA'NOSI:
      `ops/mediamtx/mediamtx.yml` anonim o'qishni RAD ETADI (03-12,
      `authInternalUsers`), ya'ni rekvizit oyog'i olib tashlansa chipta
      baribir 200 keladi (oqim ro'yxatga olinadi), kadr esa KELMAYDI.
      Sabotaj S1 aynan shu shaklni tasdiqladi.

    ⚠ `finally` DAGI `remove_stream` — `Go2rtcClient.remove_stream` ning
      ILOVADAGI birinchi haqiqiy bajarilishi (`03-11` uni «chaqirilmaydi»
      deb qayd etgan edi). Usiz har yugurishda go2rtc xotirasida ochiq
      oqim va uning ortidagi RTSP sessiyasi to'planib borardi (T-03-95).
    """
    created = await create_device(api_client, admin_headers, sim, sim_credentials)
    nvr_id = UUID(created["id"])

    run = await run_discovery(api_client, admin_headers, nvr_id, enqueued, api_sessionmaker)
    assert run["status"] == "succeeded", run["status"]

    cameras = await list_cameras(api_client, admin_headers, nvr_id)
    assert cameras, "kashfiyot birorta kamera yaratmadi — zanjir 2-bo'g'inda uzildi"

    issued = await api_client.post(
        f"{CAMERAS_URL}/{cameras[0]['id']}/live-token", headers=director_headers
    )
    # ⚠ JAVOB TANASI XABARGA QO'YILMAYDI — u 60 soniyalik jonli chiptani
    #   tashiydi (D-08). Status kodi diagnostika uchun yetadi.
    assert issued.status_code == 200, (
        f"direktor chipta ololmadi: HTTP {issued.status_code} (503 bo'lsa — go2rtc "
        "yoki rekvizit oyog'i; 404 bo'lsa — kamera topilmadi)"
    )
    body = issued.json()
    assert body["url"].startswith("/live/"), body["url"]

    stream_name = _stream_name_from(body["url"])

    try:
        probe = await _await_first_frame(test_settings.go2rtc_url, stream_name)

        assert probe.arrived, (
            f"`{stream_name}` uchun {FRAME_DEADLINE_SECONDS:.0f} s ichida JPEG kadr "
            f"KELMADI: {probe.attempts} urinish, {probe.elapsed:.1f} s, oxirgi status "
            f"{probe.status}, tana uzunligi {probe.length} bayt, transport xatosi "
            f"{probe.transport_error}. Eng ehtimolli sabab — go2rtc manbaga ULANA "
            "OLMAYAPTI: rekvizit oyog'i uzilgan (manba anonim so'raydi va sim `401` "
            "beradi) yoki manba yo'li sim'ning yo'l naqshiga MOS KELMAYAPTI."
        )
    finally:
        # ⚠ ISTISNONI YUTMAYDI: `remove_stream` ning O'ZI yiqilsa buni
        #   ko'rish kerak. pytest asosiy assertni `__context__` da
        #   ko'rsatadi, ya'ni sabab yashirinmaydi.
        async with Go2rtcClient(test_settings.go2rtc_url) as client:
            await client.remove_stream(stream_name)


async def test_an_archived_camera_never_reaches_the_real_go2rtc(
    sim: str,
    sim_credentials: tuple[str, str],
    api_client: httpx.AsyncClient,
    admin_headers: dict[str, str],
    director_headers: dict[str, str],
    enqueued: list[dict[str, Any]],
    api_sessionmaker: async_sessionmaker[AsyncSession],
    test_settings: Settings,
    nvr_cleanup: None,
) -> None:
    """Arxivlangan kamera: chipta **404** VA go2rtc'da yangi oqim PAYDO BO'LMAYDI.

    `test_live_view.py::test_archived_camera_has_no_live_token` shu
    da'voning birinchi yarmini SEED qatori va MOCK ustida o'lchaydi. Bu
    yerda u HAQIQIY go2rtc ustida va kashfiyot yaratgan kamera ustida
    takrorlanadi — ya'ni «oqim ro'yxatga OLINMAYDI» (UI-SPEC §6.6) endi
    kod o'qishdan emas, media serverining O'Z ro'yxatidan o'lchanadi.

    ⚠ SOLISHTIRISH FAQAT KALITLAR BO'YICHA: qiymatlar rekvizitli `src`
      larni tashiydi va ular hech qayerga chiqmaydi (T-03-94).
    """
    created = await create_device(api_client, admin_headers, sim, sim_credentials)
    nvr_id = UUID(created["id"])

    run = await run_discovery(api_client, admin_headers, nvr_id, enqueued, api_sessionmaker)
    assert run["status"] == "succeeded", run["status"]

    cameras = await list_cameras(api_client, admin_headers, nvr_id)
    assert cameras, "kashfiyot birorta kamera yaratmadi"
    camera_id = cameras[0]["id"]

    archived = await api_client.post(f"{CAMERAS_URL}/{camera_id}/archive", headers=admin_headers)
    assert archived.status_code == 200, archived.status_code
    assert archived.json()["is_archived"] is True, "kamera arxivlanmadi"

    before = await _stream_names(test_settings.go2rtc_url)

    denied = await api_client.post(
        f"{CAMERAS_URL}/{camera_id}/live-token", headers=director_headers
    )
    assert denied.status_code == 404, (
        f"arxivlangan kamera uchun chipta {denied.status_code} bilan tugadi — 404 "
        "kutilgan edi (UI-SPEC §8.5)"
    )

    after = await _stream_names(test_settings.go2rtc_url)
    assert after == before, (
        f"go2rtc ro'yxati {len(before)} -> {len(after)} ga o'zgardi — arxivlangan "
        "kamera uchun oqim RO'YXATGA OLINDI"
    )
