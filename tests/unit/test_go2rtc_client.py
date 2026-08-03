"""go2rtc `src` allow-listi — RCE darvozasining testi (D-11, T-03-45).

=============================================================================
HAR RAD ETISH YO'LI ALOHIDA TEST (`test_jwt.py` da o'rnatilgan qoida).

Bitta parametrik test ham «hammasi rad etiladi» deb yashil bo'lardi,
lekin nosozlik xabarida QAYSI protokol o'tib ketgani ko'rinmasdi.
Bu yerda esa har yo'lning O'Z nomi bor va CI ro'yxatida
`test_rejects_exec_source` alohida qator bo'lib turadi —
`03-RESEARCH.md` D.13 aynan shu nomni talab qiladi.
=============================================================================

TAHDID: GHSA-wwww-5h25-jf98 (CVSS 9.1). Frigate `PUT /api/streams` ning
`src` parametrini go2rtc'ga filtrsiz uzatgan; `exec:` protokoli esa
ixtiyoriy tizim buyrug'ini oqim manbai qiladi — natijada ikkita HTTP
so'rovi bilan konteynerda root sifatida kod ijrosi.

⚠ BU FAYL KONFIGURATSIYANI HAM O'QIYDI. Allow-list — himoyaning faqat
BIR qatlami; qolgan ikkitasi `ops/nginx/nginx.conf` va `compose.yaml`
da yashaydi va ular Python testlariga KO'RINMAYDI. Konfiguratsiya
darvozalari `test_rate_limit_proxy.py:446-460` naqshida yozilgan:
fayl o'qiladi va taqiqlangan/majburiy satr izlanadi.
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from typing import TYPE_CHECKING

import httpx
import pytest
from app.services.go2rtc import (
    GO2RTC_STREAMS_PATH,
    LIVE_VIEW_PATH,
    UNSAFE_SOURCE,
    Go2rtcClient,
    Go2rtcError,
    assert_safe_go2rtc_src,
    live_view_url,
)
from pydantic import SecretStr
from structlog.testing import capture_logs

if TYPE_CHECKING:
    from collections.abc import Callable

REPO_ROOT = Path(__file__).resolve().parents[2]
NGINX_CONF = REPO_ROOT / "ops" / "nginx" / "nginx.conf"
COMPOSE = REPO_ROOT / "compose.yaml"
GO2RTC_CONF = REPO_ROOT / "ops" / "go2rtc" / "go2rtc.yaml"

SAFE_SOURCE = "rtsp://192.168.1.64:554/Streaming/Channels/101"
"""Mahsulot yo'lidagi HAQIQIY shakl — `rtsp_url()` ning chiqishi."""

SECRET = "Sekret123"  # noqa: S105 - test uskunasi
"""Istisno matnida IZLANADIGAN qiymat — u yerda UCHRAMASLIGI kerak."""

CREDENTIALED_SOURCE = f"rtsp://admin:{SECRET}@nvr.invalid:554/Streaming/Channels/102"
"""Rekvizitli manba — Task 1 ning chiqishi bilan AYNAN bir shaklda."""

BASE_URL = "http://go2rtc.invalid:1984"
STREAM_NAME = "cam_deadbeefdeadbeefdeadbeefdeadbeef"

BLOCKED_API_PATHS = ("api/streams", "api/config", "api/restart")
"""nginx darajasida `403` oladigan go2rtc yo'llari (D-11)."""


# ---------------------------------------------------------------------------
# Allow-list — HAR RAD ETISH YO'LI ALOHIDA
# ---------------------------------------------------------------------------


def test_accepts_the_rtsp_source() -> None:
    """Mahsulot yo'lidagi `rtsp://` manba O'TADI.

    IJOBIY HOLAT MAJBURIY: usiz darvozani `raise ValueError` bilan
    almashtirib qo'yish mumkin edi va barcha rad etish testlari yashil
    qolardi — jonli ko'rish esa umuman ishlamasdi.
    """
    assert_safe_go2rtc_src(SAFE_SOURCE)


def test_rejects_exec_source() -> None:
    """`exec:` RAD ETILADI — GHSA-wwww-5h25-jf98 ning AYNAN mexanizmi.

    Bu testning NOMI `03-RESEARCH.md` D.13 da nomma-nom talab qilingan:
    CI ro'yxatidagi qator xavfni o'qiydigan odamga to'g'ridan-to'g'ri
    ko'rsatadi.
    """
    with pytest.raises(ValueError, match=UNSAFE_SOURCE):
        assert_safe_go2rtc_src("exec:whoami")


def test_rejects_ffmpeg_source() -> None:
    """`ffmpeg:` RAD ETILADI — u ham tashqi jarayon ishga tushiradi."""
    with pytest.raises(ValueError, match=UNSAFE_SOURCE):
        assert_safe_go2rtc_src("ffmpeg:rtsp://x#video=copy")


def test_rejects_echo_source() -> None:
    """`echo:` RAD ETILADI — manbani BUYRUQ CHIQISHIDAN oladi."""
    with pytest.raises(ValueError, match=UNSAFE_SOURCE):
        assert_safe_go2rtc_src("echo:/bin/sh -c id")


def test_rejects_http_source() -> None:
    """`http://` RAD ETILADI — u o'zi zararsiz, LEKIN allow-list QAT'IY.

    `http://` bilan RCE bo'lmaydi, shuning uchun uni «zararsiz» deb
    o'tkazish vasvasasi bor. Rad etish sababi boshqa: bu YAGONA
    yo'l orqali `core-api` SSRF vositasiga aylanardi (u ichki tarmoqda
    turadi va WireGuard tunneliga ulangan), va allow-listning har
    kengayishi keyingi kengayishni oqlaydi.
    """
    with pytest.raises(ValueError, match=UNSAFE_SOURCE):
        assert_safe_go2rtc_src("http://192.168.1.64/snapshot.jpg")


def test_rejects_empty_source() -> None:
    """Bo'sh satr RAD ETILADI.

    `if not src.startswith(...)` uni allaqachon ushlaydi, LEKIN test
    kerak: kimdir darvozani `if src and not src.startswith(...)` ga
    aylantirsa (masalan «bo'sh qiymatni o'tkazib yuboraylik» degan
    niyat bilan) bo'sh `src` go2rtc'ga borardi.
    """
    with pytest.raises(ValueError, match=UNSAFE_SOURCE):
        assert_safe_go2rtc_src("")


def test_rejects_leading_whitespace_source() -> None:
    """`" rtsp://..."` RAD ETILADI — BOSH BO'SHLIQ CHETLAB O'TISH YO'LI.

    ⚠ BU TEST DARVOZANING CHEGARASINI AYNAN O'LCHAYDI. Agar kimdir
      `assert_safe_go2rtc_src` ni `src.lstrip().startswith(...)` yoki
      `src.strip().startswith(...)` ga aylantirsa, bu holat YASHIL
      bo'lib qolardi — va o'sha normalizatsiya tekshiruv bilan
      iste'molchi (go2rtc) o'rtasida FARQ tug'dirardi. Aynan shu
      farqda chetlab o'tish yashaydi (ASVS V5.3).

      Bizning `src` imiz `rtsp_url()` ning chiqishi, ya'ni bo'shliqli
      qiymat KODDA XATO borligining belgisi va uni jimgina
      «tuzatib» o'tkazib yuborish xatoni ko'rinmas qilardi.
    """
    with pytest.raises(ValueError, match=UNSAFE_SOURCE):
        assert_safe_go2rtc_src(" rtsp://192.168.1.64:554/Streaming/Channels/101")


def test_rejects_uppercase_scheme() -> None:
    """`RTSP://` RAD ETILADI — solishtiruv REGISTRGA SEZGIR.

    `lower()`/`casefold()` qo'shish yuqoridagi bilan bir xil sinf
    xato bo'lardi: u darvoza bilan go2rtc o'rtasida yana bitta
    talqin farqini tug'dirardi.
    """
    with pytest.raises(ValueError, match=UNSAFE_SOURCE):
        assert_safe_go2rtc_src("RTSP://192.168.1.64:554/Streaming/Channels/101")


def test_rejects_scheme_embedded_later_in_the_string() -> None:
    """`exec:...rtsp://...` RAD ETILADI — tekshiruv PREFIKS bo'yicha.

    `"rtsp://" in src` shaklidagi tekshiruv bu qiymatni O'TKAZIB
    YUBORARDI va u `exec:` bilan boshlangani uchun go2rtc uni buyruq
    deb bajarardi. Nazorat holati: darvoza `in` emas, `startswith`.
    """
    with pytest.raises(ValueError, match=UNSAFE_SOURCE):
        assert_safe_go2rtc_src("exec:ffmpeg -i rtsp://192.168.1.64/x -f rtsp {output}")


# ---------------------------------------------------------------------------
# `Go2rtcClient` — SIR `SecretStr` BILAN TASHILADI (T-03-87, T-03-90, T-03-92)
# ---------------------------------------------------------------------------


def _mocked(
    monkeypatch: pytest.MonkeyPatch,
    handler: Callable[[httpx.Request], httpx.Response],
) -> list[httpx.Request]:
    """`httpx.AsyncClient` ni `MockTransport` bilan quradigan fabrika o'rnatadi.

    Yozib olingan so'rovlar ro'yxati qaytariladi — «tarmoqqa HECH NIMA
    chiqmadi» da'vosi aynan shu ro'yxatning bo'shligi bilan o'lchanadi.

    ⚠ `Go2rtcClient._client` GA TO'G'RIDAN-TO'G'RI TEGILMAYDI. Xususiy
      atributni almashtirish yopilmagan klient qoldirardi VA testni
      mahsulot konstruktoridan (`timeout` berilishidan) chetlab
      o'tkazardi. Bu yerda mahsulot konstruktori TO'LIQ ishlaydi, faqat
      transport almashadi.
    """
    seen: list[httpx.Request] = []
    original = httpx.AsyncClient

    def _record(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return handler(request)

    def _factory(*, base_url: str, timeout: float) -> httpx.AsyncClient:
        return original(base_url=base_url, timeout=timeout, transport=httpx.MockTransport(_record))

    monkeypatch.setattr(httpx, "AsyncClient", _factory)
    return seen


def _empty_registry(_request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, json={})


def test_ensure_stream_takes_the_source_as_a_secret() -> None:
    """`src` ning imzosi `SecretStr` — bu KELISHUV emas, TIP (`03-04` standarti).

    ⚠ Oddiy `str` bo'lganda rekvizitli manba `repr()` orqali istisno
      matniga, `pytest` diffiga va Sentry ning lokal o'zgaruvchilar
      suratiga tushardi — ya'ni himoya har chaqiruv joyidagi ehtiyotkorlikka
      tayanardi. `SecretStr` uni STRUKTURAGA aylantiradi.
    """
    annotation = inspect.signature(Go2rtcClient.ensure_stream).parameters["src"].annotation

    assert "SecretStr" in str(annotation), annotation


async def test_ensure_stream_sends_the_credentialed_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ochilgan qiymat `PUT /api/streams` ning `src` parametriga tushadi.

    IJOBIY HOLAT MAJBURIY: usiz «sir go2rtc'ga yetib bormaydi» degan
    regressiya barcha maskalanish testlarini YASHIL qoldirardi — jonli
    ko'rish esa NVR'da `401` olardi.
    """
    seen = _mocked(monkeypatch, _empty_registry)

    async with Go2rtcClient(BASE_URL) as client:
        added = await client.ensure_stream(STREAM_NAME, SecretStr(CREDENTIALED_SOURCE))

    assert added is True
    puts = [request for request in seen if request.method == "PUT"]
    assert len(puts) == 1, [request.method for request in seen]
    assert puts[0].url.params["src"] == CREDENTIALED_SOURCE
    assert puts[0].url.params["name"] == STREAM_NAME


async def test_ensure_stream_skips_the_put_when_the_stream_already_exists(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Oqim bor bo'lsa `PUT` YUBORILMAYDI — LAZY ro'yxatga olish (RESEARCH D.13).

    NAZORAT HOLATI: usiz yuqoridagi test `ensure_stream` HAR safar `PUT`
    yuboradigan holatda ham yashil bo'lardi va rekvizit go2rtc'ning
    jurnaliga har ko'rishda qayta tushardi.
    """
    registry: dict[str, dict[str, list[str]]] = {STREAM_NAME: {"producers": []}}
    seen = _mocked(monkeypatch, lambda _request: httpx.Response(200, json=registry))

    async with Go2rtcClient(BASE_URL) as client:
        added = await client.ensure_stream(STREAM_NAME, SecretStr(CREDENTIALED_SOURCE))

    assert added is False
    assert [request.method for request in seen] == ["GET"]


async def test_unsafe_secret_source_never_reaches_the_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`SecretStr("exec:...")` — `ValueError` VA tarmoqqa HECH NIMA chiqmaydi.

    ⚠ DARVOZA `SecretStr` ORTIGA YASHIRINMAYDI. Sir tashuvchi tip qo'shilishi
      allow-listni chetlab o'tishning eng ehtimolli yo'li edi: «bu sir,
      demak bizniki» degan mulohaza bilan tekshiruv tushib qolardi.
      GHSA-wwww-5h25-jf98 (CVSS 9.1) esa aynan shu joyda yashaydi.
    """
    seen = _mocked(monkeypatch, _empty_registry)

    async with Go2rtcClient(BASE_URL) as client:
        with pytest.raises(ValueError, match=UNSAFE_SOURCE):
            await client.ensure_stream(STREAM_NAME, SecretStr("exec:rm -rf /"))

    assert seen == [], (
        "xavfli manba rad etilgunicha go2rtc'ga so'rov ketdi — darvoza "
        "tarmoqqa chiqishdan KEYIN ishlayapti"
    )


async def test_ensure_stream_failure_carries_neither_the_url_nor_the_password(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """T-03-87 — `Go2rtcError` da so'rov URL'i ham, parol ham YO'Q.

    =======================================================================
    BU FAZADAGI HAQIQIY OQISH YO'LI VA U SHU TEST BILAN QULFLANADI.

    `httpx.HTTPStatusError` ning matni TO'LIQ so'rov URL'ini o'z ichiga
    oladi, so'rov URL'i esa `?name=...&src=rtsp://admin:PAROL@...`. Eski
    kodda u `f"... yiqildi: {exc}"` orqali `Go2rtcError` ga, u yerdan
    `cameras.py` dagi `log.warning(..., error=str(exc))` orqali jurnalga,
    va jurnaldan Sentry'ga ketardi.

    Sabab zanjiri HAM tekshiriladi: `__cause__` bo'sh va kontekst
    bostirilgan, ya'ni `traceback` ham, Sentry ning zanjir yuruvchisi ham
    httpx ning xabariga UMUMAN yetib bormaydi.
    =======================================================================
    """

    def _handler(request: httpx.Request) -> httpx.Response:
        if request.method == "PUT":
            return httpx.Response(400, text="bad request")
        return httpx.Response(200, json={})

    _mocked(monkeypatch, _handler)

    async with Go2rtcClient(BASE_URL) as client:
        with pytest.raises(Go2rtcError) as failure:
            await client.ensure_stream(STREAM_NAME, SecretStr(CREDENTIALED_SOURCE))

    rendered = f"{failure.value!s}|{failure.value!r}"
    assert SECRET not in rendered, "parol istisno matnida qoldi (T-03-87)"
    assert "nvr.invalid" not in rendered, "so'rov URL'i istisno matnida qoldi"
    assert failure.value.__cause__ is None, "sabab zanjiri httpx istisnosini olib yuribdi"
    assert failure.value.__suppress_context__ is True, (
        "kontekst bostirilmagan — `traceback` httpx ning URL'li xabarini chop etardi"
    )
    # Diagnostika SAQLANADI: qaysi amal, qaysi xato turi, qaysi status.
    assert GO2RTC_STREAMS_PATH in str(failure.value)
    assert "HTTPStatusError" in str(failure.value)
    assert "400" in str(failure.value)


async def test_has_stream_failure_carries_no_response_body(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """T-03-90 — `GET /api/streams` javobi istisno matniga TUSHMAYDI.

    Javob BARCHA bozorlarning oqimlarini, ya'ni ularning REKVIZITLI `src`
    larini qaytaradi. Bitta bozorning nosozligi qolgan hammasining
    parolini jurnalga chiqarardi.
    """
    body = json.dumps({"cam_other": {"src": CREDENTIALED_SOURCE}})
    _mocked(monkeypatch, lambda _request: httpx.Response(500, text=body))

    async with Go2rtcClient(BASE_URL) as client:
        with pytest.raises(Go2rtcError) as failure:
            await client.has_stream(STREAM_NAME)

    rendered = f"{failure.value!s}|{failure.value!r}"
    assert SECRET not in rendered
    assert "500" in str(failure.value)


async def test_has_stream_never_logs_the_stream_registry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """MUVAFFAQIYATLI `has_stream` ham javob tanasini JURNALGA yozmaydi.

    ⚠ Bu «bugun ham shunday» emas, TALAB (T-03-90): ro'yxatda boshqa
      bozorlarning rekvizitli manbalari turadi va «diagnostika uchun»
      bitta `log.debug(payload=...)` butun o'rnatmaning NVR parollarini
      bitta satrga chiqarardi.
    """
    registry = {"cam_other": {"src": CREDENTIALED_SOURCE}}
    _mocked(monkeypatch, lambda _request: httpx.Response(200, json=registry))

    with capture_logs() as logs:
        async with Go2rtcClient(BASE_URL) as client:
            assert await client.has_stream(STREAM_NAME) is False

    assert SECRET not in json.dumps(logs, default=str), "javob tanasi jurnalga tushdi"


async def test_remove_stream_failure_carries_no_url(monkeypatch: pytest.MonkeyPatch) -> None:
    """`DELETE` ning xatosi ham faqat sinf nomi + statusni beradi.

    Bu chaqiruvning URL'ida sir YO'Q (`src=<cam_uuid4>`), lekin uchala
    blok bir xil qoidaga bo'ysunishi kerak: ikkitasi tozalanib, uchinchisi
    `{exc}` da qolsa keyingi tahrirlovchi uni «to'g'ri namuna» deb
    nusxalardi.
    """
    _mocked(monkeypatch, lambda _request: httpx.Response(404))

    async with Go2rtcClient(BASE_URL) as client:
        with pytest.raises(Go2rtcError) as failure:
            await client.remove_stream(STREAM_NAME)

    assert "404" in str(failure.value)
    assert BASE_URL not in str(failure.value)


# ---------------------------------------------------------------------------
# Jonli ko'rish manzili
# ---------------------------------------------------------------------------


def test_live_view_url_carries_the_stream_name_inside_the_url() -> None:
    """`stream_name` URL ICHIDA va manzil `/live/` prefiksi ostida (UI-SPEC §8.7)."""
    url = live_view_url("cam_deadbeef", "tok.en.value")

    assert url.startswith(LIVE_VIEW_PATH), url
    assert "src=cam_deadbeef" in url
    assert "t=tok.en.value" in url


def test_live_view_path_is_under_the_authorized_prefix() -> None:
    """Manzil `/live/` ostida — ya'ni nginx unga `auth_request` qo'yadi.

    Prefiks o'zgarsa (masalan `/stream/`) manzil nginx ning
    avtorizatsiya blokidan TASHQARIDA qolardi va so'rov `location /`
    orqali frontendga ketardi: jonli ko'rish ishlamasdi, lekin
    xavfsizlik nuqsoni ham tug'ilmasdi. Bu test o'sha jimgina
    uzilishning oldini oladi.
    """
    assert LIVE_VIEW_PATH.startswith("/live/")
    assert "/live/" in NGINX_CONF.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# KONFIGURATSIYA DARVOZALARI — qolgan ikki qatlam (T-03-45)
# ---------------------------------------------------------------------------


def _go2rtc_service_lines() -> list[str]:
    """`compose.yaml` dagi `go2rtc` xizmatining KOD qatorlari (izohlarsiz).

    ⚠ IZOHLAR OLIB TASHLANADI — VA BU SHU FAZADA UCHINCHI MARTA
      TAKRORLANGAN DARSNING NATIJASI. `test_no_sim_branching` darvozasi
      03-04, 03-05 va 03-06 da uch marta izohdagi matnga urildi, chunki
      grep KODNI IZOHDAN AJRATMAYDI.

      Bu yerda ziddiyat aynan teskari tomonga ishlaydi: `compose.yaml`
      dagi izoh D-11 ni TUSHUNTIRADI va u yerda `1984` soni ATAYIN
      yozilgan (o'qiyotgan odam qaysi port haqida gap ketayotganini
      bilishi kerak). Izohlarni filtrlamasa, darvoza o'z sababini
      tushuntirgani uchun qizarardi — ya'ni u yaxshi hujjatlashni
      JAZOLARDI.
    """
    lines: list[str] = []
    inside = False
    for raw in COMPOSE.read_text(encoding="utf-8").splitlines():
        if raw.startswith("  go2rtc:"):
            inside = True
            continue
        if inside and raw and not raw.startswith("   ") and not raw.lstrip().startswith("#"):
            break
        if inside and not raw.lstrip().startswith("#"):
            lines.append(raw)
    return lines


@pytest.mark.parametrize("blocked", BLOCKED_API_PATHS)
def test_nginx_blocks_the_go2rtc_api_path(blocked: str) -> None:
    """`/api/streams|config|restart` nginx'da `403` oladi (D-11, 2-qatlam).

    Bloklar `return 403` bilan bo'lishi SHART: `deny all` 403 beradi,
    lekin `proxy_pass` bo'lgan blokda ishlamasdi va «bloklandi» degan
    yolg'on ishonch qolardi.
    """
    text = NGINX_CONF.read_text(encoding="utf-8")

    assert blocked in text, f"`{blocked}` `nginx.conf` da umuman uchramaydi"
    blocks = [
        chunk for chunk in text.split("location") if blocked in chunk and "return 403" in chunk
    ]
    assert blocks, f"`{blocked}` uchun `return 403` bo'lgan `location` bloki topilmadi"


def test_nginx_blocks_the_api_path_through_the_live_prefix() -> None:
    """`/live/api/streams` HAM bloklangan — prefiks orqali chetlab o'tish yo'li.

    ⚠ BU IKKINCHI BLOK ALOHIDA KERAK. `/live/` bloki go2rtc'ga so'rovni
      prefiksni OLIB TASHLAB uzatadi, ya'ni `/live/api/streams`
      go2rtc'ning `/api/streams` iga yetib borardi va birinchi blok
      (`^/api/...` ga langar tashlagan) uni UMUMAN ko'rmasdi.
    """
    text = NGINX_CONF.read_text(encoding="utf-8")
    blocks = [
        chunk for chunk in text.split("location") if "/live/api/" in chunk and "return 403" in chunk
    ]

    assert blocks, (
        "`/live/api/(streams|config|restart)` uchun `return 403` bloki yo'q — "
        "go2rtc API'si `/live/` prefiksi orqali ochiq qoladi"
    )


def test_nginx_declares_the_auth_request_target() -> None:
    """`/live/` bloki `auth_request` bilan darvozalangan (SC#6)."""
    text = NGINX_CONF.read_text(encoding="utf-8")

    assert "auth_request /internal/live-authz;" in text, (
        "`/live/` bloki `auth_request` e'lon qilmaydi — jonli oqim avtorizatsiyasiz ochiq qolardi"
    )
    assert "internal;" in text, (
        "`/internal/live-authz` nginx blokida `internal;` yo'q — nishonni "
        "foydalanuvchi to'g'ridan-to'g'ri chaqira olardi"
    )


def test_compose_does_not_publish_the_go2rtc_api_port() -> None:
    """go2rtc xost portiga PUBLISH QILINMAYDI (D-11, 1-qatlam).

    Uchala qatlamdan ENG MUHIMI: nginx bloklari ham, allow-list ham
    port ochiq bo'lganda hech nimani himoya qilmasdi — hujumchi
    to'g'ridan-to'g'ri `1984` ga borardi.
    """
    lines = _go2rtc_service_lines()

    assert lines, "`compose.yaml` da `go2rtc` xizmati topilmadi"
    assert not any(line.strip().startswith("ports:") for line in lines), (
        "`go2rtc` xizmatida `ports:` bandi paydo bo'ldi — bu API'ni "
        "(va u bilan birga RCE yuzasini) xostga ochadi"
    )
    assert not any("1984" in line for line in lines), (
        "go2rtc ning API porti (1984) compose'ning KODIDA ko'rinib qoldi"
    )


def test_production_go2rtc_config_has_no_exec_source() -> None:
    """Prod konfiguratsiyasida `exec:` YO'Q.

    Prod fayl WireGuard tunneliga ulangan xostda ishlaydi — u yerdagi
    ixtiyoriy buyruq ijrosi butun NVR tarmog'iga ochilgan darvoza bo'lardi
    (GHSA-wwww-5h25-jf98).

    ⚠ ASSERT FAQAT PROD FAYLNI O'QIYDI va bu ataylab: test uskunasining
      konfiguratsiyasi `--profile sim` ortida yashaydi, boshqa hayot
      davriga ega va boshqa rejalar tomonidan almashtiriladi. Uni shu
      darvozaga bog'lash test uskunasining har o'zgarishida XAVFSIZLIK
      testini qizartirardi.
    """
    text = GO2RTC_CONF.read_text(encoding="utf-8")
    offending = [
        line for line in text.splitlines() if "exec:" in line and not line.lstrip().startswith("#")
    ]

    assert not offending, f"prod go2rtc konfiguratsiyasida `exec:` bor: {offending}"


def test_go2rtc_streams_path_matches_the_blocked_path() -> None:
    """Kod konstantasi va nginx bloki AYNAN bir yo'lni ko'rsatadi.

    Ikkalasi jimgina ajralib ketsa (masalan go2rtc yo'lni o'zgartirsa va
    faqat kod yangilansa) nginx bloki eskirgan yo'lni himoya qilib,
    yangisini ochiq qoldirardi.
    """
    assert GO2RTC_STREAMS_PATH == "/api/streams"
    assert GO2RTC_STREAMS_PATH.lstrip("/") in BLOCKED_API_PATHS
