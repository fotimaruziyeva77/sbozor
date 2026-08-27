"""SC#3 ning darvozasi — o'n bir xato yo'li, HAQIQIY Digest handshake ustida.

=============================================================================
NEGA BU FAYL `test_nvr_sim.py` DAN ALOHIDA.

03-02 ning fayli SIMULYATORNI o'lchaydi («sim `401` beradimi?»), bu fayl
esa KLIENTNI («klient `401` ni to'g'ri sababga aylantiradimi?»). Ikkalasi
bir faylda bo'lganda sim yiqilganda klient testi ham qizarardi va sabab
qaysi tomonda ekani ko'rinmasdi.
=============================================================================

=============================================================================
IKKI RAQAM — BUTUN D-03 SIYOSATINING YAGONA TO'G'RIDAN-TO'G'RI ISBOTI.

    test_clock_drift_detected_before_auth  ->  urinishlar AYNAN 0
    test_auth_failure_is_not_retried       ->  urinishlar AYNAN 1

Ular kod EMAS, XULQ o'lchaydi va shuning uchun parametrizatsiyadan
tashqarida, nomlangan testlar sifatida turadi. Birinchisi «drift `401`
dan OLDIN ushlanadi» degan da'voni, ikkinchisi «`401` hech qachon qayta
urinilmaydi» degan da'voni raqam bilan qulflaydi. Ikkalasi ham
`GET /__sim__/attempts` sanog'idan o'qiladi va bu sanoq TEST TOMONIDAN
YOZILA OLMAYDI (03-02: sanagichlar faqat o'qishga).
=============================================================================

`pytestmark = pytest.mark.sim` — `npm run test:sim` zanjirida ishlaydi.
"""

from __future__ import annotations

import ssl
import time

import httpx
import pytest
import respx
from app.services.isapi.client import (
    DEFAULT_TIMEOUT,
    RTSP_FALLBACK_PORT,
    IsapiClient,
    resolve_rtsp_port,
)
from app.services.isapi.errors import ERROR_DETAIL_KEYS, NvrError
from fixtures.nvr_sim import sim_attempts, sim_mode, sim_patch

pytestmark = pytest.mark.sim


def _client(base_url: str, credentials: tuple[str, str], **kwargs: object) -> IsapiClient:
    username, password = credentials
    return IsapiClient(base_url, username, password, **kwargs)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Muvaffaqiyatli yo'l — UI-SPEC §4.5 majburiy qiladigan hamma narsa
# ---------------------------------------------------------------------------


async def test_probe_reports_model_channels_and_clock_drift(
    sim: str, sim_credentials: tuple[str, str]
) -> None:
    """UI-SPEC §4.5: model, tur, KANALLAR SONI va SOAT FARQI — hammasi majburiy.

    Kanallar soni adminning «to'g'ri qurilmaga ulandimmi?» savoliga yagona
    javobi; soat farqi esa 300 s dan kichik bo'lganda ham ko'rsatiladi,
    chunki 250 soniyalik farq bugun ishlaydi va ertaga sinadi.
    """
    async with _client(sim, sim_credentials) as client:
        result = await client.probe()

    assert result.ok, f"{result.error_code}: {result.error_detail}"
    assert result.device is not None
    assert result.device.model == "DS-7616NI-K2"
    assert result.device.device_type == "NVR"
    assert result.channels_preview == 6, "kanallar soni javobda yo'q yoki noto'g'ri"
    assert result.rtsp_port == 554
    assert result.rtsp_port_assumed is False, "554 KASHF ETILDI, taxmin qilinmadi"
    assert result.clock_drift_seconds is not None, "soat farqi o'lchanmadi"
    assert abs(result.clock_drift_seconds) < 5


# ---------------------------------------------------------------------------
# Xato rejimlari — HAR REJIM UCHUN BITTA HOLAT (SC#3)
# ---------------------------------------------------------------------------

ERROR_MODES: tuple[tuple[str, dict[str, object], str], ...] = (
    ("bad_password", {}, "nvr_bad_credentials"),
    ("account_locked", {}, "nvr_account_locked"),
    ("clock_drift", {"drift_seconds": 420}, "nvr_clock_drift"),
    ("digest_stale", {}, "nvr_digest_stale"),
    ("basic_only", {}, "nvr_auth_mode_basic_only"),
    ("no_permission", {}, "nvr_user_no_permission"),
    ("isapi_404", {}, "nvr_isapi_unavailable"),
    ("not_hikvision", {}, "device_not_supported"),
)
"""B.8 ning sim rejimlari -> A.3 ning sabab kodlari.

⚠ SAKKIZALASI HAM `401` YOKI UNGA O'XSHASH javob beradi va ularni
STATUS KODI AJRATMAYDI — bu jadval aynan shu sababdan mavjud.
"""


@pytest.mark.parametrize(("mode", "fields", "expected_code"), ERROR_MODES)
async def test_each_failure_mode_produces_its_own_reason_code(
    sim: str,
    sim_credentials: tuple[str, str],
    mode: str,
    fields: dict[str, object],
    expected_code: str,
) -> None:
    """«Ulanmadi» QABUL QILINMAYDI — har yo'lning O'Z kodi bor (SC#3, D-02)."""
    sim_mode(sim, mode, **fields)

    async with _client(sim, sim_credentials) as client:
        result = await client.probe()

    assert result.ok is False
    assert result.error_code == expected_code, (
        f"rejim {mode!r} -> {result.error_code!r}, kutilgani {expected_code!r}; "
        f"detail={result.error_detail}"
    )


@pytest.mark.parametrize(("mode", "fields", "expected_code"), ERROR_MODES)
async def test_error_detail_keys_are_allowlisted(
    sim: str,
    sim_credentials: tuple[str, str],
    mode: str,
    fields: dict[str, object],
    expected_code: str,
) -> None:
    """UI-SPEC §7.4 [TALAB]: `detail` da faqat allowlist'dagi kalitlar.

    Usiz «noma'lum kalit render qilinmaydi» qoidasi JIMGINA MA'LUMOT
    YO'QOTISHGA aylanardi: backend kalit yozadi, xato qilinmagandek
    ko'rinadi, foydalanuvchi esa uni hech qachon ko'rmaydi.
    """
    del expected_code
    sim_mode(sim, mode, **fields)

    async with _client(sim, sim_credentials) as client:
        result = await client.probe()

    unknown = set(result.error_detail) - ERROR_DETAIL_KEYS
    assert not unknown, f"rejim {mode!r} ruxsatsiz kalit yozdi: {sorted(unknown)}"


async def test_device_not_supported_names_the_device(
    sim: str, sim_credentials: tuple[str, str]
) -> None:
    """Foydalanuvchiga QAYSI qurilma ekani aytiladi (T-03-33, A.3)."""
    sim_mode(sim, "not_hikvision")

    async with _client(sim, sim_credentials) as client:
        result = await client.probe()

    assert result.error_code == "device_not_supported"
    assert result.error_detail.get("model") == "AVS-9000", result.error_detail


async def test_account_locked_carries_the_unlock_timer(
    sim: str, sim_credentials: tuple[str, str]
) -> None:
    """`unlock_at` — UI-SPEC §4.4 dagi taymerning yagona manbai.

    Usiz «qulflangan» xabari «kuting» dan boshqa hech nima aytmasdi va
    admin qachongacha kutishini bilmasdi.
    """
    sim_mode(sim, "account_locked")

    async with _client(sim, sim_credentials) as client:
        result = await client.probe()

    assert result.error_code == "nvr_account_locked"
    assert "unlock_at" in result.error_detail, result.error_detail


# ---------------------------------------------------------------------------
# D-03 NING IKKI RAQAMI
# ---------------------------------------------------------------------------


async def test_clock_drift_detected_before_auth(sim: str, sim_credentials: tuple[str, str]) -> None:
    """Soat farqi `401` DAN OLDIN — urinishlar sanog'i AYNAN 0.

    Bu A.3 ning «eng qimmatli hiylasi» ning raqamli isboti: qurilmaning
    `Date` sarlavhasi REKVIZITSIZ javobda ham keladi, ya'ni tashxis
    qurilmaning qulflash hisoblagichini UMUMAN QO'ZG'ATMASDAN chiqadi.

    Sanoq 0 dan katta bo'lsa — drift `401` dan KEYIN aniqlangan, ya'ni
    admin har tekshiruvda qulflanishga bir qadam yaqinlashardi.
    """
    sim_mode(sim, "clock_drift", drift_seconds=420)
    before = sim_attempts(sim)

    async with _client(sim, sim_credentials) as client:
        result = await client.probe()

    assert result.error_code == "nvr_clock_drift"
    assert result.error_detail["drift_seconds"] > 380
    assert "device_time" in result.error_detail
    assert "server_time" in result.error_detail

    after = sim_attempts(sim)
    assert after - before == 0, (
        f"rekvizit urinishlari {before} -> {after}. Soat farqi autentifikatsiyadan "
        "OLDIN aniqlanishi kerak: aks holda tashxisning O'ZI qulflash hisoblagichini "
        "oshirardi (D-03)."
    )


async def test_auth_failure_is_not_retried(sim: str, sim_credentials: tuple[str, str]) -> None:
    """`401` HECH QACHON qayta urinilmaydi — sanoq AYNAN 1 (D-03, T-03-29).

    Hikvision ~5 urinishdan keyin hisobni 30 daqiqaga qulflaydi. `tenacity`
    ning odatiy 3 urinishi × foydalanuvchining 2 bosishi = 6 urinish, ya'ni
    bitta odam ikki marta bosgani uchun hisob qulflanardi va undan keyin
    TO'G'RI PAROL HAM ISHLAMASDI.

    ⚠ SABOTAJ CHEGARASI: `_should_retry` ga `httpx.HTTPStatusError`
    qo'shilsa bu test AYNAN qizaradi (sanoq 1 dan katta bo'ladi), qolgan
    xato testlari esa yashil qoladi — ya'ni siyosat haqiqatan shu yerda
    o'lchanadi.
    """
    sim_mode(sim, "bad_password")
    before = sim_attempts(sim)

    async with _client(sim, sim_credentials) as client:
        result = await client.probe()

    assert result.error_code == "nvr_bad_credentials"

    after = sim_attempts(sim)
    assert after - before == 1, (
        f"rekvizit urinishlari {before} -> {after}. `401` dan keyin QAYTA URINISH "
        "bajarilgan — bu Hikvision hisobini 30 daqiqaga qulflaydi (D-03)."
    )


# ---------------------------------------------------------------------------
# D-05 — chegara IKKALA shaklda (A.5 ning LOW ishonchi)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("limit_mode", ["reject", "silent"])
async def test_stream_limit_produces_actionable_error(
    sim: str, sim_credentials: tuple[str, str], limit_mode: str
) -> None:
    """Chegara IKKALA shaklda ham `nvr_stream_limit` beradi (D-05, A.5).

    `reject` — qurilma javob beradi va sababni XML'da aytadi (`503` +
    «Maximum number of streams»);
    `silent` — javob UMUMAN kelmaydi, ulanish uziladi; STATUS KODI HAM,
    XATO XML'I HAM YO'Q.

    ⚠ Ikkinchi shaklda heuristika KODGA emas, XULQQA tayanadi: shu
    klientda kamida bitta oqim da'vosi o'tgan va endi keyingisi uzilyapti
    (A.5 ning aynan o'zi). Bitta shaklni tanlash heuristikani o'z
    taxminiga moslashtirgan bo'lardi.

    ⚠ Va bu HEURISTIKA, KAFOLAT EMAS — shuning uchun xom javob
    `detail.raw` da saqlanadi va texnik yordam uni tekshira oladi.
    """
    sim_patch(sim, mode="stream_limit", stream_limit=4, stream_limit_mode=limit_mode)

    async with _client(sim, sim_credentials) as client:
        for channel in range(1, 5):
            await client.get_xml(f"Streaming/channels/{channel}01")

        with pytest.raises(NvrError) as excinfo:
            await client.get_xml("Streaming/channels/501")

    error = excinfo.value
    assert error.code == "nvr_stream_limit", f"{limit_mode}: {error!r}"
    assert error.detail.get("raw"), (
        f"{limit_mode}: xom javob saqlanmadi — heuristikani tekshirib bo'lmaydi"
    )
    assert set(error.detail) <= ERROR_DETAIL_KEYS


# ---------------------------------------------------------------------------
# Transport darajasidagi ikki yo'l
# ---------------------------------------------------------------------------


async def test_tls_untrusted_is_diagnosed() -> None:
    """TLS xatosi `nvr_tls_untrusted` ga xaritalanadi — SIM REJIMI EMAS.

    ⚠ BU FAYLDAGI YAGONA TEST BO'LIB, U SIM'NI ISHLATMAYDI VA BU TANLOV
      OCHIQ YOZILADI (yashirin qisqartma qabul qilinmaydi):

      Sim oddiy HTTP orqali xizmat qiladi. Unga TLS qatlamini qo'shish
      ikkinchi port, sertifikat generatsiyasi va konteynerga yangi bog'liqlik
      olib kelardi — ya'ni O'LCHANADIGAN NARSANI O'ZGARTIRMASDAN
      infratuzilmani og'irlashtirardi. Biz egalik qiladigan narsa —
      XARITALASH, TLS qo'l siqishining o'zi emas (u `httpx` ning ishi).

    ⚠ VA E'TIBOR BERING: o'z-o'zini imzolagan sertifikat bu kodni ISHGA
      TUSHIRMAYDI. Tunnel ichida u `verify=False` bilan ATAYLAB qabul
      qilinadi (A.3), ya'ni bu kod sertifikat ISHONCHSIZLIGI uchun emas,
      TLS ning ISHLAMASLIGI uchun.
    """
    ssl_failure = httpx.ConnectError("[SSL: WRONG_VERSION_NUMBER] wrong version number")
    ssl_failure.__cause__ = ssl.SSLError("[SSL: WRONG_VERSION_NUMBER] wrong version number")

    async with respx.mock(assert_all_called=False) as router:
        router.get(url__regex=r".*/ISAPI/.*").mock(side_effect=ssl_failure)
        async with IsapiClient("https://10.10.0.5", "sbozor", "parol") as client:
            result = await client.probe()

    assert result.error_code == "nvr_tls_untrusted", result.error_detail
    assert set(result.error_detail) <= ERROR_DETAIL_KEYS


async def test_unreachable_address_is_diagnosed() -> None:
    """TCP yetib bormasa -> `nvr_unreachable` («WireGuard tunneli faolmi?»).

    Manzil ATAYIN discard porti (`9`): u har doim rad etiladi va test
    tashqi tarmoqqa bog'liq bo'lib qolmaydi.
    """
    async with IsapiClient("http://127.0.0.1:9", "sbozor", "parol") as client:
        result = await client.probe()

    assert result.error_code == "nvr_unreachable", result.error_detail


async def test_slow_device_times_out_instead_of_hanging(
    sim: str, sim_credentials: tuple[str, str]
) -> None:
    """Sekin NVR job'ni CHEKSIZ ushlab tura olmaydi (T-03-31).

    ⚠ Klient timeout'i bu testda ATAYIN qisqartirilgan (2 s). Sabab
      byudjetda: `03-RESEARCH.md` B.8 `delay_ms=15000` ni taklif qiladi va
      standart 10 soniyalik timeout × 3 urinish har `npm run gate` ga ~45
      soniya qo'shardi. Qisqa timeout AYNAN SHU xulqni o'lchaydi
      («urinish uziladi, klient qaytadi»), faqat arzonroq.
    """
    sim_mode(sim, "slow", delay_ms=15000)
    started = time.monotonic()

    async with _client(sim, sim_credentials, timeout=httpx.Timeout(2.0, connect=2.0)) as client:
        result = await client.probe()

    elapsed = time.monotonic() - started
    assert result.error_code == "nvr_unreachable", result.error_detail
    assert elapsed < 30, f"klient {elapsed:.1f}s osilib qoldi — timeout byudjeti ishlamayapti"


# ---------------------------------------------------------------------------
# RTSP porti — kashf etiladi, taxmin qilinmaydi (A.2, Pitfall 8)
# ---------------------------------------------------------------------------


async def test_moved_rtsp_port_is_discovered(sim: str, sim_credentials: tuple[str, str]) -> None:
    """O'rnatuvchi portni o'zgartirsa kashfiyot uni TOPADI, 554 ni QOTIRMAYDI."""
    sim_mode(sim, "port_moved", rtsp_port=10554)

    async with _client(sim, sim_credentials) as client:
        result = await client.probe()

    assert result.ok, result.error_detail
    assert result.rtsp_port == 10554
    assert result.rtsp_port_assumed is False


def test_missing_rtsp_entry_falls_back_to_554_and_is_flagged() -> None:
    """RTSP yozuvi bo'lmasa 554 ishlatiladi, LEKIN `assumed` belgisi qoladi.

    ⚠ Bu holat sim rejimi bilan qayta tug'dirilmaydi: sim `adminAccesses`
      da RTSP yozuvini HAR DOIM beradi va uni olib tashlash uchun yangi
      control-plane maydoni kerak bo'lardi — o'lchanadigan narsa esa SOF
      FUNKSIYADA yashaydi. Shuning uchun u to'g'ridan-to'g'ri chaqiriladi.

    Belgi shu yerda tug'iladi va `nvr_devices.rtsp_port_assumed` ustuniga
    boradi. Usiz nosozlik «kashfiyot yashil, kadr olish qora» ko'rinishida
    chiqardi va sababi hech qayerda yozilmasdi (Pitfall 8).
    """
    discovered, assumed = resolve_rtsp_port({"HTTP": 80, "RTSP": 10554})
    assert (discovered, assumed) == (10554, False)

    fallback, flagged = resolve_rtsp_port({"HTTP": 80, "HTTPS": 443})
    assert fallback == RTSP_FALLBACK_PORT
    assert flagged is True, "554 taxmin qilindi, lekin bayroq qo'yilmadi"


def test_default_timeout_is_bounded() -> None:
    """`timeout=None` (cheksiz) HECH QACHON — chegara konstantada qulflangan."""
    assert DEFAULT_TIMEOUT.read is not None
    assert DEFAULT_TIMEOUT.connect is not None
