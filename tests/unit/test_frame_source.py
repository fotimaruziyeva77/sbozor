"""Uchta kadr olish usuli bitta protokol ortida (D-06/D-07, §S-9, §S-10).

=============================================================================
BU FAYLNING MARKAZIY DA'VOSI: MUVAFFAQIYAT **NATIJADAN** O'LCHANADI.

03-14 da o'lchangan sinf: `raise_for_status()` ga so'zsiz ishonish go2rtc
ISHLAB TURGAN holatda 503 berardi. Bu yerda TESKARI xavf o'lchanadi —
`200 OK` + `Content-Type: image/jpeg` + tanada HTML xato sahifasi. Ikkala
holatda ham javob **kodi** yolg'on gapiradi va yagona haqiqat manbai —
javob BAYTLARINING o'zi.

Shuning uchun magic-bayt darvozasi mustaqil test bilan qulflanadi va uning
nazorat holati (`timeout`, `401`) O'SHA darvoza olib tashlanganda YASHIL
qolishi kerak — ya'ni «natijadan o'lchash» alohida qaror ekani isbotlanadi.
=============================================================================

=============================================================================
SIR OQISHI TESTI NAZORAT HOLATI BILAN KELADI (04-06 ning darsi).

Avval XOM `httpx` istisnosi parolni HAQIQATAN tashishini o'lchaymiz, keyin
bizning `FrameSourceError` da uning YO'QLIGINI. Nazoratsiz test oqish
yo'lining O'ZI mavjud bo'lmagan shoxda ham yashil bo'lardi va darvoza «bor»
bo'lib ko'rinardi.
=============================================================================

⚠ `respx` ATAYIN: u transport darajasida ishlaydi, ya'ni `Go2rtcClient` ham,
  `IsapiClient` ham O'Z konstruktori bilan to'liq quriladi va faqat tarmoq
  almashadi. Xususiy `_client` maydoniga tegish testni mahsulot
  konstruktoridan (timeout byudjeti, Digest auth) chetlab o'tkazardi.
"""

from __future__ import annotations

import asyncio
import pathlib
import traceback
from typing import TYPE_CHECKING, Any

import httpx
import pytest
import respx
from app.services import frame_source as frame_source_module
from app.services.capture_errors import (
    CAPTURE_BAD_CREDENTIALS,
    CAPTURE_CAMERA_OFFLINE,
    CAPTURE_INVALID_RESPONSE,
    CAPTURE_SOURCE_UNREACHABLE,
    CAPTURE_STREAM_LIMIT,
    CAPTURE_TIMEOUT,
)
from app.services.frame_source import (
    UNKNOWN_CAPTURE_METHOD,
    CaptureTarget,
    DeviceEndpoint,
    FrameSourceError,
    FrameSourcePool,
    capture_frame,
)
from app.services.isapi.client import IsapiClient
from app.services.isapi.errors import NVR_ERROR_CODES, NvrError
from fixtures.frames import HTML_ERROR_PAGE, frame_bytes, truncate
from pydantic import SecretStr
from sbozor_core.enums import CaptureMethod

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Callable

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
FRAME_SOURCE_PATH = REPO_ROOT / "services" / "core-api" / "app" / "services" / "frame_source.py"

GO2RTC_URL = "http://go2rtc.invalid:1984"
NVR_URL = "http://nvr.invalid:8080"

SECRET = "Sekret123"  # noqa: S105 - test uskunasi
"""Istisno matnida IZLANADIGAN qiymat — u yerda UCHRAMASLIGI kerak."""

STREAM_NAME = "cam_deadbeefdeadbeefdeadbeefdeadbeef"
CHANNEL_NO = 7

RTSP_SOURCE = f"rtsp://admin:{SECRET}@nvr.invalid:554/Streaming/Channels/701"
"""Rekvizitli manba — `live_source.authenticated_rtsp_source()` ning chiqishi."""

TARGET = CaptureTarget(
    stream_name=STREAM_NAME,
    channel_no=CHANNEL_NO,
    stream="main",
    rtsp_source=SecretStr(RTSP_SOURCE),
)

DEVICE = DeviceEndpoint(base_url=NVR_URL, username="admin", password=SECRET)

# 1280x720 — `QUALITY_MIN_BYTES` polidan (4 096) baland kadr, ya'ni bu
# baytlar sifat filtridan ham o'tadi (04-04 ning o'lchovi).
GOOD_JPEG = frame_bytes(mean=140, stddev=45, width=1280, height=720)

PICTURE_PATH = f"/ISAPI/Streaming/channels/{CHANNEL_NO}01/picture"
SUB_PICTURE_PATH = f"/ISAPI/Streaming/channels/{CHANNEL_NO}02/picture"


# ---------------------------------------------------------------------------
# Yordamchilar
# ---------------------------------------------------------------------------


async def _pool() -> FrameSourcePool:
    return FrameSourcePool(go2rtc_url=GO2RTC_URL)


def _register_go2rtc(router: respx.Router, frame: httpx.Response) -> None:
    """`ensure_stream()` ning ikki chaqiruvi + kadr yo'li."""
    router.get(f"{GO2RTC_URL}/api/streams").mock(return_value=httpx.Response(200, json={}))
    router.put(f"{GO2RTC_URL}/api/streams").mock(
        return_value=httpx.Response(200, json={"ok": True})
    )
    router.get(f"{GO2RTC_URL}/api/frame.jpeg").mock(return_value=frame)


def _digest(handler: Callable[[httpx.Request], httpx.Response]) -> Any:
    """`401` + `WWW-Authenticate: Digest` -> ikkinchi so'rovda `Authorization`.

    ⚠ HANDSHAKE HAQIQIY: `httpx.DigestAuth` javobni O'ZI quradi. To'g'ridan-
      to'g'ri `200` qaytarish `Authorization` sarlavhasini umuman
      tug'dirmasdi va «parol query satrida emas, sarlavhada» da'vosi
      o'lchanmagan qolardi.
    """

    def _side_effect(request: httpx.Request) -> httpx.Response:
        if "authorization" not in request.headers:
            return httpx.Response(
                401,
                headers={"WWW-Authenticate": 'Digest realm="ISAPI", nonce="deadbeef", qop="auth"'},
            )
        return handler(request)

    return _side_effect


async def _isapi_sources(device: DeviceEndpoint = DEVICE) -> AsyncIterator[Any]:
    pool = await _pool()
    try:
        async with pool.for_device(device) as sources:
            yield sources
    finally:
        await pool.aclose()


# ---------------------------------------------------------------------------
# go2rtc — D-06 ning standart yo'li
# ---------------------------------------------------------------------------


@respx.mock
async def test_the_go2rtc_path_registers_the_stream_before_asking_for_a_frame() -> None:
    """`ensure_stream()` AVVAL, `/api/frame.jpeg` KEYIN (RESEARCH §B.6).

    3-fazada ro'yxatga olish LAZY: oqim faqat ko'rish so'ralganda
    qo'shiladi. Kadr olish esa jonli ko'rishga BOG'LIQ EMAS — ya'ni
    ro'yxatga olmasdan so'ralgan kadr `404` bilan qaytardi va nosozlik
    «kamera oflayn» bo'lib ko'rinardi.
    """
    router = respx.mock
    _register_go2rtc(router, httpx.Response(200, content=GOOD_JPEG))

    pool = await _pool()
    try:
        async with pool.for_device(DEVICE) as sources:
            frame = await capture_frame(sources, TARGET, method=CaptureMethod.GO2RTC.value)
    finally:
        await pool.aclose()

    assert frame.data == GOOD_JPEG
    assert frame.method == CaptureMethod.GO2RTC.value
    assert frame.elapsed_ms >= 0

    ordered = [(call.request.method, call.request.url.path) for call in router.calls]
    assert ordered.index(("GET", "/api/streams")) < ordered.index(("GET", "/api/frame.jpeg")), (
        f"kadr ro'yxatga olishdan OLDIN so'raldi: {ordered}"
    )


@respx.mock
async def test_the_frame_request_carries_only_the_src_parameter() -> None:
    """So'rov parametrlari ALLOW-LIST bilan quriladi (Pitfall 8, T-04-52).

    ⛔ Keshlangan kadr «bu kadr 06:30 da olingan» da'vosini YOLG'ON qiladi
       va dalil zanjiri jimgina buziladi: hisobotdagi son o'zgaradi, xato
       chiqmaydi, birorta test qizarmaydi.
    """
    router = respx.mock
    _register_go2rtc(router, httpx.Response(200, content=GOOD_JPEG))

    pool = await _pool()
    try:
        async with pool.for_device(DEVICE) as sources:
            await capture_frame(sources, TARGET, method=CaptureMethod.GO2RTC.value)
    finally:
        await pool.aclose()

    frames = [call for call in router.calls if call.request.url.path == "/api/frame.jpeg"]
    assert len(frames) == 1
    assert dict(frames[0].request.url.params) == {"src": STREAM_NAME}, (
        "kadr so'rovida ortiqcha parametr bor — allow-list ishlamayapti"
    )


@respx.mock
async def test_the_frame_source_never_deregisters_the_stream() -> None:
    """D-11 — `DELETE /api/streams` HECH QACHON yuborilmaydi.

    go2rtc yalqov: tomoshabin bo'lmasa RTSP sessiyasini O'ZI yopadi.
    Har kadrdan keyin ro'yxatdan chiqarish keyingi slotda qayta
    ro'yxatga olishni majburlardi — ya'ni har kadr uchun ikkita ortiqcha
    HTTP borish va NVR ga yangi RTSP handshake.
    """
    router = respx.mock
    _register_go2rtc(router, httpx.Response(200, content=GOOD_JPEG))
    deleted = router.delete(f"{GO2RTC_URL}/api/streams").mock(
        return_value=httpx.Response(200, json={})
    )

    pool = await _pool()
    try:
        async with pool.for_device(DEVICE) as sources:
            await capture_frame(sources, TARGET, method=CaptureMethod.GO2RTC.value)
    finally:
        await pool.aclose()

    assert not deleted.called, "kadr olishdan keyin oqim ro'yxatdan chiqarildi (D-11 buzilishi)"


@respx.mock
async def test_an_html_body_is_rejected_even_when_the_content_type_says_jpeg() -> None:
    """⛔ SABOTAJ NISHONI — MUVAFFAQIYAT NATIJADAN O'LCHANADI (§S-10).

    `200 OK` + `Content-Type: image/jpeg` + tanada HTML. Sarlavhaga
    ishonadigan filtr bu sahifani YAROQLI BILLING KADRI sifatida
    saqlardi va 5-faza uni bandlik dalili deb o'qirdi.
    """
    router = respx.mock
    _register_go2rtc(
        router,
        httpx.Response(200, content=HTML_ERROR_PAGE, headers={"Content-Type": "image/jpeg"}),
    )

    pool = await _pool()
    try:
        async with pool.for_device(DEVICE) as sources:
            with pytest.raises(FrameSourceError) as failure:
                await capture_frame(sources, TARGET, method=CaptureMethod.GO2RTC.value)
    finally:
        await pool.aclose()

    assert failure.value.code == CAPTURE_INVALID_RESPONSE


@respx.mock
async def test_a_truncated_body_is_still_accepted_by_the_source_layer() -> None:
    """NAZORAT HOLATI: kesilgan JPEG magic-baytdan O'TADI va bu TO'G'RI.

    `frame_source` faqat «bu umuman kadrmi?» savoliga javob beradi;
    «bu kadr YAROQLIMI?» savoli `quality.analyze()` niki (04-04) va u
    kesilgan tanani `corrupt` deb belgilaydi. Ikkala darvoza ham kerak
    va ular ALOHIDA o'lchanadi — birinchisini ikkinchisining ishini
    qilishga majburlash ikkalasini bir joyga yig'ib, sabab kodini
    (`not_a_jpeg` / `missing_end_of_image`) yo'qotardi.
    """
    router = respx.mock
    _register_go2rtc(router, httpx.Response(200, content=truncate(GOOD_JPEG)))

    pool = await _pool()
    try:
        async with pool.for_device(DEVICE) as sources:
            frame = await capture_frame(sources, TARGET, method=CaptureMethod.GO2RTC.value)
    finally:
        await pool.aclose()

    assert frame.data.startswith(b"\xff\xd8\xff")
    assert frame.data != GOOD_JPEG


@respx.mock
async def test_a_go2rtc_timeout_becomes_capture_timeout() -> None:
    """Manba ulandi, lekin kadr bermadi -> `capture_timeout`."""
    router = respx.mock
    router.get(f"{GO2RTC_URL}/api/streams").mock(return_value=httpx.Response(200, json={}))
    router.put(f"{GO2RTC_URL}/api/streams").mock(return_value=httpx.Response(200, json={}))
    router.get(f"{GO2RTC_URL}/api/frame.jpeg").mock(
        side_effect=httpx.ReadTimeout("kadr kelmadi", request=None)
    )

    pool = await _pool()
    try:
        async with pool.for_device(DEVICE) as sources:
            with pytest.raises(FrameSourceError) as failure:
                await capture_frame(sources, TARGET, method=CaptureMethod.GO2RTC.value)
    finally:
        await pool.aclose()

    assert failure.value.code == CAPTURE_TIMEOUT


@respx.mock
async def test_a_go2rtc_404_means_the_camera_is_offline_not_that_the_source_is_down() -> None:
    """`404` — oqim ro'yxatda BOR, lekin kadr yo'q: kanal oflayn.

    ⚠ `capture_source_unreachable` DAN AJRATISH OPERATSION: birinchisi
      adminni tunnel va tarmoqqa yuboradi, bu esa AYNAN o'sha kameraning
      quvvati va kabeliga.
    """
    router = respx.mock
    router.get(f"{GO2RTC_URL}/api/streams").mock(return_value=httpx.Response(200, json={}))
    router.put(f"{GO2RTC_URL}/api/streams").mock(return_value=httpx.Response(200, json={}))
    router.get(f"{GO2RTC_URL}/api/frame.jpeg").mock(return_value=httpx.Response(404, text="no"))

    pool = await _pool()
    try:
        async with pool.for_device(DEVICE) as sources:
            with pytest.raises(FrameSourceError) as failure:
                await capture_frame(sources, TARGET, method=CaptureMethod.GO2RTC.value)
    finally:
        await pool.aclose()

    assert failure.value.code == CAPTURE_CAMERA_OFFLINE


# ---------------------------------------------------------------------------
# SIR OQISHI — nazorat holati bilan
# ---------------------------------------------------------------------------


@respx.mock
async def test_an_error_carries_neither_the_password_nor_the_rtsp_url() -> None:
    """T-04-49 — parol na xabarda, na `traceback` da, na `__cause__` da.

    =======================================================================
    NAZORAT HOLATI BIRINCHI KELADI VA U MAJBURIY.

    `httpx.HTTPStatusError` ning matni TO'LIQ so'rov URL'ini tashiydi,
    `PUT /api/streams` ning URL'i esa `?src=rtsp://admin:PAROL@...`.
    Oqish yo'lining MAVJUDLIGI avval o'lchanadi — usiz bu test o'z
    farazini o'ziga tasdiqlagan bo'lardi (04-06 ning 3-deviatsiyasi).
    =======================================================================
    """
    leaky_url = httpx.URL(f"{GO2RTC_URL}/api/streams", params={"src": RTSP_SOURCE})
    raw = httpx.HTTPStatusError(
        f"Client error '401 Unauthorized' for url '{leaky_url}'",
        request=httpx.Request("PUT", leaky_url),
        response=httpx.Response(401),
    )
    assert SECRET in str(raw), "nazorat holati ishlamadi — oqish yo'li umuman yo'q"

    router = respx.mock
    router.get(f"{GO2RTC_URL}/api/streams").mock(return_value=httpx.Response(200, json={}))
    router.put(f"{GO2RTC_URL}/api/streams").mock(return_value=httpx.Response(401, text="denied"))

    pool = await _pool()
    try:
        async with pool.for_device(DEVICE) as sources:
            with pytest.raises(FrameSourceError) as failure:
                await capture_frame(sources, TARGET, method=CaptureMethod.GO2RTC.value)
    finally:
        await pool.aclose()

    rendered = "|".join(
        (
            str(failure.value),
            repr(failure.value),
            failure.value.detail,
            "".join(traceback.format_exception(failure.value)),
        )
    )
    assert SECRET not in rendered, "parol istisno matnida qoldi (T-04-49)"
    assert "rtsp://" not in rendered, "RTSP manbai istisno matnida qoldi"
    assert "Authorization" not in rendered
    assert failure.value.__cause__ is None, "sabab zanjiri xom istisnoni olib yuribdi"


# ---------------------------------------------------------------------------
# ISAPI — D-07: NOL RTSP sessiyasi
# ---------------------------------------------------------------------------


@respx.mock
async def test_the_isapi_path_keeps_the_password_out_of_the_query_string() -> None:
    """§S-9 — parol `httpx.DigestAuth` da, so'rov satrida EMAS.

    ISAPI ning `?u=…&p=…` varianti parolni query satriga, u yerdan nginx
    access-log'iga va Sentry breadcrumb'iga olib chiqardi — `sentry-sdk`
    ning httpx integratsiyasi har CHIQUVCHI so'rovni breadcrumb qiladi va
    breadcrumb `data` sida to'liq URL turadi.
    """
    router = respx.mock
    seen: list[httpx.Request] = []

    def _picture(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, content=GOOD_JPEG, headers={"Content-Type": "image/jpeg"})

    router.get(f"{NVR_URL}{PICTURE_PATH}").mock(side_effect=_digest(_picture))

    pool = await _pool()
    try:
        async with pool.for_device(DEVICE) as sources:
            frame = await capture_frame(sources, TARGET, method=CaptureMethod.ISAPI.value)
    finally:
        await pool.aclose()

    assert frame.data == GOOD_JPEG
    assert frame.method == CaptureMethod.ISAPI.value
    assert seen, "Digest handshake umuman bajarilmadi"
    for request in seen:
        assert SECRET not in str(request.url), "parol so'rov satrida"
        assert request.url.params.multi_items() == [], "ISAPI kadr so'rovida parametr bo'lmasligi kerak"
        assert request.headers.get("Authorization", "").startswith("Digest ")


@respx.mock
async def test_the_isapi_path_uses_the_substream_channel_when_asked() -> None:
    """Hikvision `{kanal}{oqim}`: `01` — asosiy, `02` — sub-oqim (D-09)."""
    router = respx.mock
    route = router.get(f"{NVR_URL}{SUB_PICTURE_PATH}").mock(
        side_effect=_digest(
            lambda _request: httpx.Response(
                200, content=GOOD_JPEG, headers={"Content-Type": "image/jpeg"}
            )
        )
    )

    pool = await _pool()
    try:
        async with pool.for_device(DEVICE) as sources:
            await capture_frame(
                sources,
                CaptureTarget(
                    stream_name=STREAM_NAME,
                    channel_no=CHANNEL_NO,
                    stream="sub",
                    rtsp_source=SecretStr(RTSP_SOURCE),
                ),
                method=CaptureMethod.ISAPI.value,
            )
    finally:
        await pool.aclose()

    assert route.called


@respx.mock
async def test_the_isapi_path_rejects_an_html_body_labelled_as_jpeg() -> None:
    """`Content-Type` ga ISHONILMAYDI — magic bayt ikkinchi qatlam (§C.7)."""
    router = respx.mock
    router.get(f"{NVR_URL}{PICTURE_PATH}").mock(
        side_effect=_digest(
            lambda _request: httpx.Response(
                200, content=HTML_ERROR_PAGE, headers={"Content-Type": "image/jpeg"}
            )
        )
    )

    pool = await _pool()
    try:
        async with pool.for_device(DEVICE) as sources:
            with pytest.raises(FrameSourceError) as failure:
                await capture_frame(sources, TARGET, method=CaptureMethod.ISAPI.value)
    finally:
        await pool.aclose()

    assert failure.value.code == CAPTURE_INVALID_RESPONSE


@respx.mock
async def test_the_isapi_path_claims_no_rtsp_session(monkeypatch: pytest.MonkeyPatch) -> None:
    """⛔ D-07 NING KODDAGI O'LCHOVI — `/picture` OQIM DA'VO QILMAYDI.

    `IsapiClient._stream_claims` `nvr_stream_limit` evristikasining
    kirishi (`client.py::_classify`). `/picture` u yerga sanalsa, keyingi
    tarmoq uzilishi «NVR chegarasi to'ldi» deb talqin qilinardi — ya'ni
    sessiya bosimida ENG XAVFSIZ yo'l (D-07) o'zini chegara qurboni deb
    e'lon qilardi va adaptiv pasaytirish noto'g'ri tomonga ishlardi.
    """
    router = respx.mock
    router.get(f"{NVR_URL}{PICTURE_PATH}").mock(
        side_effect=_digest(
            lambda _request: httpx.Response(
                200, content=GOOD_JPEG, headers={"Content-Type": "image/jpeg"}
            )
        )
    )

    async with IsapiClient(NVR_URL, "admin", SECRET) as client:
        await client.fetch_picture(CHANNEL_NO)
        await client.fetch_picture(CHANNEL_NO)
        claims_after_pictures = client.stream_claims

    assert claims_after_pictures == 0, (
        "`/picture` RTSP sessiyasini da'vo qildi — D-07 ning teskarisi"
    )


@respx.mock
async def test_an_isapi_401_becomes_bad_credentials_and_a_404_becomes_camera_offline() -> None:
    """ISAPI taksonomiyasi kadr olish kodlariga XARITALANADI, yo'qolmaydi."""
    router = respx.mock
    router.get(f"{NVR_URL}{PICTURE_PATH}").mock(return_value=httpx.Response(401, text="denied"))

    pool = await _pool()
    try:
        async with pool.for_device(DEVICE) as sources:
            with pytest.raises(FrameSourceError) as unauthorized:
                await capture_frame(sources, TARGET, method=CaptureMethod.ISAPI.value)
    finally:
        await pool.aclose()
    assert unauthorized.value.code == CAPTURE_BAD_CREDENTIALS

    router.reset()
    router.get(f"{NVR_URL}{PICTURE_PATH}").mock(
        side_effect=_digest(lambda _request: httpx.Response(404, text="kanal yo'q"))
    )
    pool = await _pool()
    try:
        async with pool.for_device(DEVICE) as sources:
            with pytest.raises(FrameSourceError) as missing:
                await capture_frame(sources, TARGET, method=CaptureMethod.ISAPI.value)
    finally:
        await pool.aclose()
    assert missing.value.code == CAPTURE_CAMERA_OFFLINE


def test_every_isapi_code_has_a_capture_code() -> None:
    """Xaritalash TO'LIQ — yangi ISAPI kodi jimgina tushib qola olmaydi.

    ⚠ Standart qiymatga tayanish (`.get(code, fallback)`) yangi kodni
      jimgina `capture_source_unreachable` ga aylantirardi va admin
      butunlay boshqa joyni qidirardi. Darvoza IKKI TOMONLAMA: reyestrda
      yo'q kod ham qizartiradi.
    """
    mapped = set(frame_source_module.ISAPI_TO_CAPTURE)
    assert mapped == set(NVR_ERROR_CODES), {
        "faqat xaritada": sorted(mapped - set(NVR_ERROR_CODES)),
        "faqat reyestrda": sorted(set(NVR_ERROR_CODES) - mapped),
    }
    assert frame_source_module.ISAPI_TO_CAPTURE["nvr_stream_limit"] == CAPTURE_STREAM_LIMIT


# ---------------------------------------------------------------------------
# ffmpeg — oxirgi chora
# ---------------------------------------------------------------------------


class _FakeProcess:
    """`asyncio.subprocess.Process` ning testga yetarli yuzasi."""

    def __init__(self, *, stdout: bytes, returncode: int, hang: bool) -> None:
        self._stdout = stdout
        self.returncode: int | None = returncode
        self._hang = hang
        self.killed = False
        self.waited = False

    async def communicate(self) -> tuple[bytes, bytes]:
        if self._hang:
            await asyncio.sleep(3600)
        return self._stdout, b""

    def kill(self) -> None:
        self.killed = True

    async def wait(self) -> int:
        self.waited = True
        return self.returncode or 0


def _fake_exec(
    monkeypatch: pytest.MonkeyPatch, process: _FakeProcess
) -> list[tuple[str, ...]]:
    calls: list[tuple[str, ...]] = []

    async def _exec(*argv: str, **_kwargs: Any) -> _FakeProcess:
        calls.append(argv)
        return process

    monkeypatch.setattr(asyncio, "create_subprocess_exec", _exec)
    return calls


async def test_the_ffmpeg_path_passes_arguments_as_a_list_and_never_through_a_shell(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """T-04-56 — `create_subprocess_exec`, `_shell` EMAS; argumentlar ro'yxat.

    Shell qatlami RTSP manbaidagi har qanday belgini (parolda `;`, `$`,
    backtick bo'lishi mumkin) buyruqqa aylantirardi — parolni ADMIN
    kiritadi, ya'ni u ishonchsiz kirish.
    """
    process = _FakeProcess(stdout=GOOD_JPEG, returncode=0, hang=False)
    calls = _fake_exec(monkeypatch, process)

    pool = await _pool()
    try:
        async with pool.for_device(DEVICE) as sources:
            frame = await capture_frame(sources, TARGET, method=CaptureMethod.FFMPEG.value)
    finally:
        await pool.aclose()

    assert frame.data == GOOD_JPEG
    assert frame.method == CaptureMethod.FFMPEG.value
    assert len(calls) == 1
    assert calls[0][0] == "ffmpeg"
    assert RTSP_SOURCE in calls[0], "rekvizitli manba subprocess argumenti sifatida uzatilmadi"


async def test_the_ffmpeg_path_kills_the_process_on_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """T-04-56 — timeout'da `kill()` VA `wait()`; zombi jarayon qolmaydi.

    `kill()` yolg'iz o'zi yetmaydi: o'ldirilgan bola jarayon `wait()`
    chaqirilmaguncha zombi bo'lib qoladi va worker konteynerida ular
    kunlik 175 slot bo'yicha to'planardi.
    """
    process = _FakeProcess(stdout=b"", returncode=0, hang=True)
    _fake_exec(monkeypatch, process)
    monkeypatch.setattr(frame_source_module, "FFMPEG_TIMEOUT_SECONDS", 0.05)

    pool = await _pool()
    try:
        async with pool.for_device(DEVICE) as sources:
            with pytest.raises(FrameSourceError) as failure:
                await capture_frame(sources, TARGET, method=CaptureMethod.FFMPEG.value)
    finally:
        await pool.aclose()

    assert failure.value.code == CAPTURE_TIMEOUT
    assert process.killed, "timeout'da jarayon o'ldirilmadi"
    assert process.waited, "o'ldirilgan jarayon `wait()` qilinmadi — zombi qoladi"


async def test_the_ffmpeg_path_reports_a_non_zero_exit_without_the_stderr(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`stderr` xato matniga QO'SHILMAYDI — u RTSP URL'ini parol bilan chop etadi."""
    process = _FakeProcess(stdout=b"", returncode=1, hang=False)
    _fake_exec(monkeypatch, process)

    pool = await _pool()
    try:
        async with pool.for_device(DEVICE) as sources:
            with pytest.raises(FrameSourceError) as failure:
                await capture_frame(sources, TARGET, method=CaptureMethod.FFMPEG.value)
    finally:
        await pool.aclose()

    assert failure.value.code == CAPTURE_SOURCE_UNREACHABLE
    assert SECRET not in f"{failure.value}|{failure.value.detail}"


# ---------------------------------------------------------------------------
# Usul tanlovi — bazadan, ikkinchi qatlam bilan
# ---------------------------------------------------------------------------


async def test_an_unknown_method_is_rejected_before_any_network_call() -> None:
    """`nvr_devices.capture_method` CHECK'i BIRINCHI qatlam, bu — IKKINCHI.

    Migratsiya bilan kod ajralib ketishi mumkin (yangi qiymat CHECK'ga
    qo'shilib, bu yerda unutilishi), va o'shanda tanlov jimgina standart
    yo'lga tushib ketardi — dala diagnostikasi «qaysi yo'l ishladi?»
    savoliga noto'g'ri javob berardi.
    """
    pool = await _pool()
    try:
        async with pool.for_device(DEVICE) as sources:
            with pytest.raises(ValueError, match=UNKNOWN_CAPTURE_METHOD):
                await capture_frame(sources, TARGET, method="telepatiya")
    finally:
        await pool.aclose()


async def test_the_pool_offers_exactly_the_three_documented_methods() -> None:
    """D-06: uchta usul, bittasi ham ortiqcha emas va bittasi ham yetishmaydi."""
    pool = await _pool()
    try:
        async with pool.for_device(DEVICE) as sources:
            assert set(sources) == {
                CaptureMethod.GO2RTC.value,
                CaptureMethod.ISAPI.value,
                CaptureMethod.FFMPEG.value,
            }
            for method, source in sources.items():
                assert source.method == method
    finally:
        await pool.aclose()


# ---------------------------------------------------------------------------
# Matn darvozalari — QURILISH SHAKLI, qiymat emas
# ---------------------------------------------------------------------------


def test_the_module_never_names_the_cache_parameter_or_deregisters_a_stream() -> None:
    """Ikki taqiq MATN darajasida qulflanadi (Pitfall 8, D-11).

    Test QIYMATNI o'lchaydi (yuqoridagi ikki test), bu darvoza esa
    QURILISH SHAKLINI: allow-list bugun to'g'ri ishlashi mumkin, lekin
    ertaga kimdir «diagnostika uchun» parametr qo'shib qo'yishi mumkin va
    o'shanda faqat matn darvozasi buni ushlaydi (04-04 ning 6-sabotaji).
    """
    body = FRAME_SOURCE_PATH.read_text(encoding="utf-8")
    assert '"cache"' not in body and "'cache'" not in body
    assert ".remove_stream(" not in body
    assert body.count("get_secret_value()") <= 1, (
        "ochiq qiymatga borish BITTA joyda bo'lishi kerak (§S-9)"
    )
    assert "from None" in body


def test_the_isapi_client_never_puts_credentials_in_the_query_string() -> None:
    """§S-9 ning matn darvozasi — `IsapiClient` da Digest, query satri EMAS."""
    body = (
        REPO_ROOT / "services" / "core-api" / "app" / "services" / "isapi" / "client.py"
    ).read_text(encoding="utf-8")
    assert "DigestAuth" in body
    assert "?u=" not in body
    assert "&p=" not in body


def test_isapi_errors_stay_isapi_errors_at_their_own_layer() -> None:
    """`fetch_picture` `NvrError` beradi — xaritalash `frame_source` da.

    Qatlamlarni aralashtirish `IsapiClient` ni kadr olish taksonomiyasiga
    bog'lab qo'yardi va u kashfiyot yo'lida ham o'sha kodlarni ko'tarib
    yurardi.
    """
    assert issubclass(NvrError, Exception)
    assert not issubclass(NvrError, FrameSourceError)
