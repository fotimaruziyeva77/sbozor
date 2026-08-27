"""`nvr-sim` ga HAQIQIY TCP orqali boradigan testlar (CAM-09, SC#7).

=============================================================================
NEGA `ASGITransport` EMAS:

`tests/conftest.py` dagi `api_client` ilovaning O'ZIGA to'g'ridan-to'g'ri
boradi — tarmoq, port va uvicorn yo'q. Bu boshqa maqsad uchun to'g'ri vosita.
Bu yerdagi da'vo esa boshqacha: **kod NVR bilan gaplasha oladi**. Uni
tarmoqsiz isbotlab bo'lmaydi, chunki sim alohida jarayonda, alohida
konteynerda, alohida TCP ulanishi ortida turadi — real qurilma bilan aynan
shu munosabatda.

`respx` ham yaramaydi: u `httpx` transportini almashtiradi, ya'ni Digest
handshake UMUMAN bajarilmaydi (B.6).

CI'DA SKIP YO'Q: `sim_url` fixture'i `CI` muhitida `pytest.fail` beradi
(T-03-10). Aks holda SC#7 ning «CI'da o'lchanadi» da'vosi jimgina yolg'onga
aylanardi — chiqish yashil, sanoq esa nolga tushgan bo'lardi.
=============================================================================
"""

from __future__ import annotations

from datetime import UTC, datetime
from email.utils import parsedate_to_datetime

import httpx
import pytest
from fixtures.nvr_sim import (
    DEFAULT_TIMEOUT,
    sim_attempts,
    sim_mode,
    sim_patch,
    sim_reset,
    sim_state,
)

pytestmark = pytest.mark.sim


def _digest(credentials: tuple[str, str]) -> httpx.DigestAuth:
    username, password = credentials
    return httpx.DigestAuth(username, password)


async def test_sim_is_reachable(sim: str) -> None:
    """Control-plane javob beradi — sim ko'tarilgan va u HAQIQIY TCP ortida.

    ⚠ Bu testning yiqilishi «sim ishlamayapti» degani, «kod buzilgan» degani
    emas. Shuning uchun u eng birinchi turadi: qolgan sim testlarining
    yiqilish sababini bir qarashda ajratib beradi.
    """
    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
        response = await client.get(f"{sim}/__sim__/state")

    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "ok"
    assert body["channel_count"] >= 1, "sim kanalsiz — `SIM_CHANNEL_COUNT` noto'g'ri"


async def test_digest_handshake_succeeds(sim: str, sim_credentials: tuple[str, str]) -> None:
    """`httpx.DigestAuth` sim bilan HAQIQIY RFC 7616 handshake bajaradi.

    Ketma-ketlik (A.3):
      1. rekvizitsiz so'rov -> `401` + `WWW-Authenticate: Digest ... qop="auth"`
      2. klient `response = MD5(HA1:nonce:nc:cnonce:qop:HA2)` ni hisoblaydi
      3. so'rov `Authorization: Digest ...` bilan QAYTA yuboriladi -> `200`

    Ya'ni bu test sim'ning `verify()` si `response` ni HAQIQATAN
    hisoblayotganini talab qiladi — stub bo'lsa 1-qadamdan keyin `200`
    kelardi va handshake umuman sinalmasdan qolardi.
    """
    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as anonymous:
        challenge = await anonymous.get(f"{sim}/ISAPI/System/deviceInfo")

    assert challenge.status_code == 401, "rekvizitsiz so'rov `401` bermadi"
    header = challenge.headers.get("WWW-Authenticate", "")
    assert header.startswith("Digest "), f"Digest challenge yo'q: {header!r}"
    assert 'qop="auth"' in header, f'`qop="auth"` yo\'q: {header!r}'
    assert "nonce=" in header, f"`nonce` yo'q: {header!r}"

    async with httpx.AsyncClient(auth=_digest(sim_credentials), timeout=DEFAULT_TIMEOUT) as client:
        response = await client.get(f"{sim}/ISAPI/System/deviceInfo")

    assert response.status_code == 200, f"Digest handshake yiqildi: {response.text[:200]}"
    assert "<model>DS-7616NI-K2</model>" in response.text
    assert "<deviceType>NVR</deviceType>" in response.text


async def test_wrong_password_never_authenticates(sim: str) -> None:
    """Noto'g'ri parol HECH QACHON o'tmaydi va urinish SANALADI.

    Bu — T-03-09 (Spoofing) ning yagona o'lchovi. `verify()` stub bo'lsa
    (masalan har doim `True`), `nvr_bad_credentials` yo'li hech qachon
    sinalmasdi va D-03 ning butun retry siyosati o'lchanmasdan qolardi.

    Sanoq esa D-03 ning ikkinchi yarmini o'lchaydi: BITTA chaqiruv = BITTA
    rekvizit urinishi. Hikvision ~5 urinishdan keyin hisobni 30 daqiqaga
    qulflaydi, ya'ni `401` da retry qilish ZARARLI.
    """
    before = sim_attempts(sim)

    async with httpx.AsyncClient(
        auth=httpx.DigestAuth("admin", "definitely-not-the-password"),
        timeout=DEFAULT_TIMEOUT,
    ) as client:
        response = await client.get(f"{sim}/ISAPI/System/deviceInfo")

    assert response.status_code == 401, (
        f"noto'g'ri parol bilan {response.status_code} keldi. Digest tekshiruvi "
        "STUB bo'lib qolgan — sim har parolni qabul qilyapti (T-03-09)."
    )

    after = sim_attempts(sim)
    assert after - before == 1, (
        f"rekvizit urinishlari {before} -> {after}. Bitta chaqiruv AYNAN bitta "
        "urinish bo'lishi kerak: `401` dan keyin qayta urinish hisobni qulflaydi (D-03)."
    )


async def test_clock_drift_is_visible_before_authentication(sim: str) -> None:
    """`Date` sarlavhasi `401` javobida ham siljigan — A.3 ning "eng qimmatli hiylasi".

    Noto'g'ri parol, soat farqi va qulflangan hisob — UCHALASI HAM `401`
    beradi, ya'ni status kod farqlamaydi. Yagona ajratuvchi belgi qurilmaning
    `Date` sarlavhasi, va u autentifikatsiya YIQILISHIDAN OLDIN o'qiladi.
    """
    sim_mode(sim, "clock_drift", drift_seconds=420)

    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as anonymous:
        response = await anonymous.get(f"{sim}/ISAPI/System/deviceInfo")

    assert response.status_code == 401, "drift `401` dan OLDIN aniqlanishi kerak edi"
    device_time = parsedate_to_datetime(response.headers["Date"])
    drift = (device_time - datetime.now(UTC)).total_seconds()
    assert 380 < drift < 460, (
        f"o'lchangan siljish {drift:.0f}s, kutilgan ~420s. `Date` sarlavhasi "
        "siljimasa `nvr_clock_drift` yo'lini sinab bo'lmaydi (uvicorn `--no-date-header` ?)."
    )


async def test_rtsp_port_is_discovered_not_assumed(
    sim: str, sim_credentials: tuple[str, str]
) -> None:
    """A.2 / Pitfall 8: RTSP porti `adminAccesses` dan KELADI, 554 deb qotirilmaydi.

    O'rnatuvchilar portni tez-tez o'zgartiradi (masalan 10554). 554 ni
    qotirish JIMGINA ishlamaydigan kamera yozuvlari tug'diradi: kashfiyot
    yashil, kadr olish qora.
    """
    async with httpx.AsyncClient(auth=_digest(sim_credentials), timeout=DEFAULT_TIMEOUT) as client:
        default = await client.get(f"{sim}/ISAPI/Security/adminAccesses")
        assert default.status_code == 200
        assert "<protocol>RTSP</protocol>" in default.text
        assert "<portNo>554</portNo>" in default.text

        sim_mode(sim, "port_moved", rtsp_port=10554)
        moved = await client.get(f"{sim}/ISAPI/Security/adminAccesses")

    assert "<portNo>10554</portNo>" in moved.text, (
        "`port_moved` rejimida ham 554 qaytdi — port sozlanmaydi degani"
    )
    assert "<portNo>80</portNo>" in moved.text, (
        "HTTP porti ham o'zgarib ketdi — faqat RTSP protokoli tegishi kerak"
    )


async def test_stream_limit_reject_shape(sim: str, sim_credentials: tuple[str, str]) -> None:
    """D-05 ning BIRINCHI shakli: qurilma javob beradi va sababni XML'da aytadi."""
    sim_patch(sim, mode="stream_limit", stream_limit=4, stream_limit_mode="reject")

    statuses: list[int] = []
    async with httpx.AsyncClient(auth=_digest(sim_credentials), timeout=DEFAULT_TIMEOUT) as client:
        for channel in range(1, 6):
            response = await client.get(f"{sim}/ISAPI/Streaming/channels/{channel}01")
            statuses.append(response.status_code)
        last = response

    assert statuses[:4] == [200, 200, 200, 200], f"birinchi to'rtta da'vo o'tmadi: {statuses}"
    assert statuses[4] != 200, f"beshinchi da'vo ham o'tdi: {statuses} — chegara AMAL QILMAYAPTI"
    assert "Maximum number of streams" in last.text, (
        f"rad etish sababi javobda yo'q: {last.text[:200]}"
    )
    assert sim_state(sim)["stream_claims"] == 4, "rad etilgan da'vo ham sanalib ketdi"


async def test_stream_limit_silent_shape(sim: str, sim_credentials: tuple[str, str]) -> None:
    """D-05 ning IKKINCHI shakli: javob UMUMAN kelmaydi, ulanish uziladi.

    A.5 chegaraning wire darajasida qanday ko'rinishini **LOW** ishonch bilan
    belgilaydi: ba'zi firmware `453`/`503` beradi, ba'zisi esa jimgina uzadi.
    Bitta shaklni tanlash heuristikani o'z taxminiga moslashtirgan bo'lardi —
    shuning uchun IKKALASI ham modellashtiriladi va IKKALASI ham sinaladi.
    """
    sim_patch(sim, mode="stream_limit", stream_limit=4, stream_limit_mode="silent")

    async with httpx.AsyncClient(auth=_digest(sim_credentials), timeout=DEFAULT_TIMEOUT) as client:
        for channel in range(1, 5):
            response = await client.get(f"{sim}/ISAPI/Streaming/channels/{channel}01")
            assert response.status_code == 200, f"kanal {channel} da'vosi o'tmadi"

        with pytest.raises(httpx.HTTPError) as excinfo:
            await client.get(f"{sim}/ISAPI/Streaming/channels/501")

    # ⚠ Muhimi shundaki, status kodi ham, xato XML'i ham YO'Q — heuristika
    # faqat TRANSPORT darajasidagi alomatga tayanishi mumkin. `TransportError`
    # aynan shuni bildiradi: HTTP javobi UMUMAN kelmadi.
    assert isinstance(excinfo.value, httpx.TransportError), (
        f"kutilgan transport xatosi emas: {type(excinfo.value).__name__}: {excinfo.value}"
    )


async def test_reset_zeroes_the_counters(sim: str, sim_credentials: tuple[str, str]) -> None:
    """`POST /__sim__/reset` sanagichlarni nolga qaytaradi.

    Usiz testlar bir-birining sanog'ini MEROS qilib olardi: `stream_limit=4`
    testi oldingi testdan qolgan da'volar bilan boshlanib, BIRINCHI so'rovdayoq
    rad etilardi — va sabab test mantig'ida emas, tozalanmagan holatda bo'lardi.
    """
    sim_patch(sim, stream_limit=4)
    async with httpx.AsyncClient(auth=_digest(sim_credentials), timeout=DEFAULT_TIMEOUT) as client:
        await client.get(f"{sim}/ISAPI/Streaming/channels/101")
        await client.get(f"{sim}/ISAPI/Streaming/channels/201")

    dirty = sim_state(sim)
    assert dirty["stream_claims"] == 2
    assert dirty["auth_attempts"] > 0

    clean = sim_reset(sim)
    assert clean["stream_claims"] == 0, "`reset` `stream_claims` ni nollamadi"
    assert clean["auth_attempts"] == 0, "`reset` `auth_attempts` ni nollamadi"
    assert clean["mode"] == "ok"
    assert clean["stream_limit"] != 4, "`reset` `stream_limit` ni standartga qaytarmadi"


async def test_channel_list_reflects_offline_and_removed(
    sim: str, sim_credentials: tuple[str, str]
) -> None:
    """SC#2 ning ikki alomati: oflayn kanal RO'YXATDA qoladi, olib tashlangani — yo'q.

    Farq muhim: `offline` kanal uchun kamera yozuvi BARIBIR yaratiladi
    (`status='offline'`), ro'yxatdan chiqib ketgani esa O'CHIRILMAYDI (D-10) —
    ikkalasi ham kashfiyot kodining boshqa-boshqa yo'llari.
    """
    sim_patch(sim, mode="channel_offline", offline_channels=[3])

    async with httpx.AsyncClient(auth=_digest(sim_credentials), timeout=DEFAULT_TIMEOUT) as client:
        status = await client.get(f"{sim}/ISAPI/ContentMgmt/InputProxy/channels/status")
        assert status.status_code == 200
        assert status.text.count("<online>false</online>") == 1
        assert status.text.count("<online>true</online>") == 5

        sim_patch(sim, mode="channel_removed", offline_channels=[], removed_channels=[5])
        channels = await client.get(f"{sim}/ISAPI/ContentMgmt/InputProxy/channels")

    assert channels.status_code == 200
    assert "<id>5</id>" not in channels.text, "olib tashlangan kanal ro'yxatda qoldi"
    assert "<id>4</id>" in channels.text and "<id>6</id>" in channels.text


# =============================================================================
# 4-FAZA (W0-10, CAM-06): `frame_mode` va ISAPI `/picture`.
#
# ⛔ BU BLOKNING MAVJUDLIK SABABI: MediaMTX BUZUQ KADR BERA OLMAYDI.
#
# `nvr-sim-rtsp` yaroqli oqim beradi — bu uning ishi. Ya'ni undan «yarmida
# uzilgan JPEG», «JPEG o'rniga HTML sahifa» yoki «bo'sh tana» ni OLIB
# BO'LMAYDI. Sifat filtri (04-04) esa aynan shularni rad etishi kerak.
# Baytlar sim boshqaruvida bo'lmasa, filtr hech qachon buzuq kadr
# ko'rmasdi va u DARVOZA emas, KONVENTSIYA bo'lib qolardi.
#
# ⚠ Har test `sim` fixture'ini oladi — u testdan OLDIN ham, KEYIN ham
#   `reset` qiladi, ya'ni `frame_mode` keyingi testga SIZIB O'TMAYDI.
# =============================================================================

PICTURE_PATH = "/ISAPI/Streaming/channels/101/picture"
JPEG_SOI = b"\xff\xd8\xff"
JPEG_EOI = b"\xff\xd9"


async def test_frame_mode_rejects_an_unknown_value(sim: str) -> None:
    """Noma'lum QIYMAT rad etiladi — noma'lum KALIT bilan bir xil qat'iylik.

    ⚠ Kalit darvozasi buni USHLAMAYDI: `frame_mode` `PATCHABLE_FIELDS` da
      bor, ya'ni `{"frame_mode": "corrupt"}` undan O'TADI. Qiymat
      tekshiruvisiz sim so'rovni qabul qilib, holatini o'zgartirmasdi va
      test «buzuq kadr so'radim» deb o'ylab, YAROQLI kadr ustida ishlab,
      sifat filtri umuman sinalmagan holda yashil qolardi.
    """
    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
        bad_value = await client.post(f"{sim}/__sim__/state", json={"frame_mode": "corrupt"})
        bad_key = await client.post(f"{sim}/__sim__/state", json={"frame_mod": "ok"})

    assert bad_value.status_code == 400, (
        f"noma'lum `frame_mode` qiymati {bad_value.status_code} bilan QABUL QILINDI: "
        f"{bad_value.text[:200]}"
    )
    assert "frame_mode" in bad_value.text, f"xato sababi ko'rinmayapti: {bad_value.text[:200]}"
    assert bad_key.status_code == 400, "noma'lum kalit qabul qilindi"

    assert sim_state(sim)["frame_mode"] == "ok", "rad etilgan so'rov holatni o'zgartirdi"


async def test_frame_mode_ok_returns_a_complete_jpeg(
    sim: str, sim_credentials: tuple[str, str]
) -> None:
    """Standart holatda `/picture` YAROQLI JPEG beradi — ijobiy nazorat.

    Usiz quyidagi uchala buzuq-holat testi «sim har doim axlat qaytaradi»
    degan holatda ham yashil bo'lardi.
    """
    async with httpx.AsyncClient(auth=_digest(sim_credentials), timeout=DEFAULT_TIMEOUT) as client:
        response = await client.get(f"{sim}{PICTURE_PATH}")

    assert response.status_code == 200, f"`/picture` {response.status_code} berdi"
    assert response.headers["content-type"].startswith("image/jpeg")
    assert response.content.startswith(JPEG_SOI), "SOI markeri yo'q — bu JPEG emas"
    assert response.content.endswith(JPEG_EOI), "EOI markeri yo'q — oqim to'liq emas"
    assert len(response.content) > 1024, (
        f"kadr atigi {len(response.content)} bayt — sifat filtri uchun `mean`/`stddev` "
        "o'lchab bo'lmaydigan darajada kichik"
    )


async def test_frame_mode_truncated_loses_the_end_of_image_marker(
    sim: str, sim_credentials: tuple[str, str]
) -> None:
    """Yarim yetkazilgan javob: sarlavha YAROQLI, oxiri YO'Q.

    ⚠ `Content-Type` HAMON `image/jpeg` — va bu ataylab. Tarmoq uzilishi
      sarlavhani o'zgartirmaydi, ya'ni sarlavhaga qarab qaror qiladigan
      filtr bu kadrni YAROQLI deb qabul qilardi.
    """
    sim_patch(sim, frame_mode="truncated")

    async with httpx.AsyncClient(auth=_digest(sim_credentials), timeout=DEFAULT_TIMEOUT) as client:
        response = await client.get(f"{sim}{PICTURE_PATH}")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/jpeg")
    assert response.content.startswith(JPEG_SOI), "sarlavha ham yo'qolgan — bu kesish emas"
    assert not response.content.endswith(JPEG_EOI), "EOI hamon joyida — oqim kesilmagan"


async def test_frame_mode_html_returns_a_non_jpeg_body_with_status_200(
    sim: str, sim_credentials: tuple[str, str]
) -> None:
    """JPEG o'rniga HTML xato sahifasi — status kodi BARIBIR 200 (T-04-10).

    Bu eng ayyor shakl: HTTP darajasida hammasi joyida, tanada esa kadr
    o'rniga sahifa. `200` ga qarab qaror qiladigan kod bu javobni
    «muvaffaqiyatli kadr olish» deb yozib qo'yardi va yo'qlik yozuvi
    hech qachon tug'ilmasdi.
    """
    sim_patch(sim, frame_mode="html")

    async with httpx.AsyncClient(auth=_digest(sim_credentials), timeout=DEFAULT_TIMEOUT) as client:
        response = await client.get(f"{sim}{PICTURE_PATH}")

    assert response.status_code == 200, "HTML tanasi 200 bilan kelishi SHART (T-04-10)"
    assert response.headers["content-type"].startswith("text/html")
    assert not response.content.startswith(JPEG_SOI), "HTML tanasi JPEG magic bayti bilan boshlandi"
    assert b"<html>" in response.content


async def test_frame_mode_empty_returns_an_empty_body(
    sim: str, sim_credentials: tuple[str, str]
) -> None:
    """Bo'sh tana `image/jpeg` sarlavhasi bilan — sarlavha «kadr» deydi, tana bo'sh."""
    sim_patch(sim, frame_mode="empty")

    async with httpx.AsyncClient(auth=_digest(sim_credentials), timeout=DEFAULT_TIMEOUT) as client:
        response = await client.get(f"{sim}{PICTURE_PATH}")

    assert response.status_code == 200
    assert response.content == b"", f"tana bo'sh emas: {response.content[:80]!r}"


async def test_picture_requires_credentials_and_counts_the_attempt(sim: str) -> None:
    """`bad_password` rejimida `/picture` ham `401` beradi va urinish SANALADI.

    ⚠ Yangi autentifikatsiya kodi YOZILMAGAN: `/picture` mavjud Digest
      darvozasidan o'tadi (`main.py::_authenticate`). Agar u alohida
      yo'ldan borsa, kadr olish autentifikatsiyasiz ishlab ketardi va
      `nvr_bad_credentials` yo'li bu endpoint uchun umuman sinalmasdi.
    """
    sim_mode(sim, "bad_password")
    before = sim_attempts(sim)

    async with httpx.AsyncClient(
        auth=httpx.DigestAuth("admin", "definitely-not-the-password"),
        timeout=DEFAULT_TIMEOUT,
    ) as client:
        response = await client.get(f"{sim}{PICTURE_PATH}")

    assert response.status_code == 401, (
        f"`bad_password` rejimida `/picture` {response.status_code} berdi — "
        "kadr olish yo'li Digest darvozasini CHETLAB o'tyapti"
    )
    assert sim_attempts(sim) - before == 1, "rekvizit urinishi sanalmadi"


async def test_picture_claims_no_rtsp_session(sim: str, sim_credentials: tuple[str, str]) -> None:
    """D-07: ISAPI `/picture` NOL RTSP sessiyasi ochadi.

    Shuning uchun D-06/D-07 uni sessiya bosimi ostida ENG XAVFSIZ usul deb
    belgilaydi. Sim oqim da'vosini sanasa, o'z hujjatining TESKARISINI
    modellagan bo'lardi va 04-04 ning «chegara to'lganda ham `/picture`
    ishlaydi» yo'li sim ustida hech qachon yashil bo'lmasdi.

    ⚠ Nazorat: oqim yo'li (`/picture` siz) BARIBIR sanaydi — ya'ni bu test
      «sanagich umuman ishlamayapti» holatida qizaradi.
    """
    async with httpx.AsyncClient(auth=_digest(sim_credentials), timeout=DEFAULT_TIMEOUT) as client:
        for _ in range(3):
            picture = await client.get(f"{sim}{PICTURE_PATH}")
            assert picture.status_code == 200

        assert sim_state(sim)["stream_claims"] == 0, (
            "`/picture` RTSP sessiyasini da'vo qildi — D-07 ning teskarisi"
        )

        stream = await client.get(f"{sim}/ISAPI/Streaming/channels/101")

    assert stream.status_code == 200
    assert sim_state(sim)["stream_claims"] == 1, "oqim yo'li ham sanamadi — sanagich buzuq"


async def test_picture_rejects_a_malformed_channel_id(
    sim: str, sim_credentials: tuple[str, str]
) -> None:
    """Shakl buzuq -> `400`; shakl to'g'ri, kanal yo'q -> `404`.

    Ikkalasini bir xil kodga yig'ish 04-04 ning xato taksonomiyasini
    ko'rlantirardi: «kod noto'g'ri URL quryapti» (retry bilan HECH QACHON
    tuzalmaydi) va «kamera qurilmadan yo'qolgan» (kashfiyot qayta
    ishga tushishi kerak) — butunlay boshqa remediatsiyalar.
    """
    async with httpx.AsyncClient(auth=_digest(sim_credentials), timeout=DEFAULT_TIMEOUT) as client:
        malformed = await client.get(f"{sim}/ISAPI/Streaming/channels/7/picture")
        wrong_stream = await client.get(f"{sim}/ISAPI/Streaming/channels/103/picture")
        # Shakl to'g'ri (`{kanal}{oqim}`), lekin kanal 99 CI'dagi oltitadan
        # tashqarida — bu MAVJUDLIK savoli, SHAKL savoli emas.
        missing = await client.get(f"{sim}/ISAPI/Streaming/channels/9901/picture")

    assert malformed.status_code == 400, f"`7` shakli {malformed.status_code} berdi"
    assert wrong_stream.status_code == 400, f"`103` (oqim `03`) {wrong_stream.status_code} berdi"
    assert missing.status_code == 404, f"mavjud bo'lmagan kanal {missing.status_code} berdi"


async def test_reset_returns_frame_mode_to_ok(sim: str, sim_credentials: tuple[str, str]) -> None:
    """`POST /__sim__/reset` `frame_mode` ni `"ok"` ga qaytaradi.

    Usiz buzuq kadr rejimi keyingi testga SIZIB O'TARDI va sabab o'sha
    testning mantig'ida emas, tozalanmagan holatda bo'lardi.
    """
    sim_patch(sim, frame_mode="empty")
    assert sim_state(sim)["frame_mode"] == "empty"

    clean = sim_reset(sim)
    assert clean["frame_mode"] == "ok", "`reset` `frame_mode` ni standartga qaytarmadi"

    async with httpx.AsyncClient(auth=_digest(sim_credentials), timeout=DEFAULT_TIMEOUT) as client:
        response = await client.get(f"{sim}{PICTURE_PATH}")

    assert response.content.startswith(JPEG_SOI), "`reset` dan keyin ham buzuq kadr keldi"
