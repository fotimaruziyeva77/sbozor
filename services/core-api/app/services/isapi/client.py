"""Hikvision ISAPI klienti — Digest, timeout byudjeti va TESKARI retry siyosati.

=============================================================================
                    ⚠⚠  `401` NI QAYTA URINISH TAQIQLANADI  ⚠⚠
                              (D-03, T-03-29)

Hikvision hisobni **~5 ta xato urinishdan keyin 30 daqiqaga qulflaydi** va
undan keyin **TO'G'RI PAROL HAM ISHLAMAYDI**. Admin buni ko'rmaydi: u
parolni tuzatadi, tizim baribir «parol noto'g'ri» deydi, va sabab
tizimning O'ZIDA bo'ladi.

Arifmetika shafqatsiz: `tenacity` ning odatiy 3 urinishi × foydalanuvchining
2 bosishi = **6 urinish** — ya'ni bitta odam ikki marta bosgani uchun hisob
qulflanadi. Shuning uchun siyosat odatdagiga TESKARI:

    tarmoq xatosi (timeout, connect reset, 5xx)  ->  retry, <=3 urinish
    `401` / `403`  (autentifikatsiya)            ->  HECH QACHON

Bu qoida `_should_retry()` predikatida yashaydi va `httpx.HTTPStatusError`
u yerda ATAYIN YO'Q. Raqamli isbot — `tests/integration/test_nvr_errors.py::
test_auth_failure_is_not_retried`: simulyatordagi urinishlar sanog'i
`401` dan keyin AYNAN 1 bo'lishi kerak.
=============================================================================

=============================================================================
SOAT FARQINI `401` DAN OLDIN USHLASH — BU MODULNING ENG QIMMATLI HIYLASI.

Markaziy muammo (A.3): noto'g'ri parol ham, soat farqi ham, qulflangan
hisob ham, `digest`-only firmware ham — **hammasi `401` beradi**. Javob
kodi FARQLAMAYDI.

Yagona erta ajratuvchi belgi — qurilmaning `Date` sarlavhasi. U
**muvaffaqiyatsiz** birinchi javobda ham keladi, ya'ni:

    rekvizitsiz `GET` -> `401` + `Date` -> farqni o'lchaymiz -> xulosa

Bu yo'lda qurilmaning qulflash hisoblagichi UMUMAN QO'ZG'ALMAYDI (biz
rekvizit yubormaymiz). Shuning uchun `probe()` bu tekshiruvni BIRINCHI
qiladi.

⚠ `Date` sarlavhasi umuman bo'lmasa tekshiruv O'TKAZIB YUBORILADI (xato
  EMAS): sarlavhaning yo'qligi soat farqi haqida hech nima aytmaydi va
  undan xato yasash butun ulanishni sababsiz bloklardi.
=============================================================================

Resurs egaligi `app/main.py:96-117` (`Redis`) naqshi bilan bir xil:
klient async context manager, yopilish `finally` da. BITTA klient butun
kashfiyot davomida qayta ishlatiladi — har yangi `httpx.DigestAuth`
birinchi so'rovni `401` bilan boshlaydi va 25 kanal uchun bu 25 ta
ORTIQCHA borish demakdir (A.3).
"""

from __future__ import annotations

import ssl
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from typing import TYPE_CHECKING, Any, Final, Self

import httpx
import structlog
from defusedxml.ElementTree import fromstring as xml_fromstring
from sbozor_core.models.nvr import CAPTURE_STREAM_VALUES
from tenacity import AsyncRetrying, retry_if_exception, stop_after_attempt, wait_exponential

from app.services.isapi.errors import NvrError
from app.services.isapi.parser import (
    ChannelRow,
    DeviceInfo,
    local_name,
    parse_admin_accesses,
    parse_device_info,
    parse_input_proxy_channels,
    parse_video_input_channels,
)
from app.services.rtsp import stream_id

if TYPE_CHECKING:
    from types import TracebackType

log = structlog.get_logger(__name__)

__all__ = [
    "CLOCK_DRIFT_TOLERANCE_SECONDS",
    "DEFAULT_TIMEOUT",
    "ISAPI_PREFIX",
    "MAX_RETRY_ATTEMPTS",
    "NVR_DEVICE_TYPES",
    "RTSP_FALLBACK_PORT",
    "SUPPORTED_MANUFACTURER",
    "IsapiClient",
    "ProbeResult",
    "assert_supported_device",
    "resolve_rtsp_port",
]


ISAPI_PREFIX: Final[str] = "/ISAPI"

DEFAULT_TIMEOUT: Final[httpx.Timeout] = httpx.Timeout(10.0, connect=5.0)
"""⚠ `timeout=None` (CHEKSIZ) HECH QACHON.

Sekin yoki javob bermay qolgan NVR job'ni CHEKSIZ ushlab turardi va
worker'ni bloklardi (T-03-31): bitta nosoz qurilma butun navbatni
to'xtatib qo'yadi. Tunnel ortidagi qurilma sekinroq, shuning uchun
`connect=5, read=10` — `httpx` ning 5 s standartidan kattaroq, lekin
CHEKLANGAN.
"""

MAX_RETRY_ATTEMPTS: Final[int] = 3
"""Tarmoq sinfidagi xatolar uchun. `401` bu songa UMUMAN aloqasi yo'q (D-03)."""

CLOCK_DRIFT_TOLERANCE_SECONDS: Final[float] = 300.0
"""Digest nonce'ining vaqt tolerantligi — standart 5 daqiqa.

⚠ BU SOZLAMA, QOTIB QOLGAN SON EMAS. `03-RESEARCH.md` A2 taxminiga ko'ra
«5 daqiqa» BITTA manbaga tayanadi (`uchkunr/hikvision-best-practices`) va
firmware bo'yicha o'zgarishi mumkin — ishonch darajasi MEDIUM. Qattiq son
yozilsa taxminni keyin, real qurilmada, TUZATIB BO'LMASDI: konstruktor
parametri esa uni bitta chaqiruv joyida o'zgartirish imkonini beradi.
"""

RTSP_FALLBACK_PORT: Final[int] = 554
"""`adminAccesses` da RTSP yozuvi topilmaganda ishlatiladigan taxmin (A.2).

⚠ FAQAT FALLBACK. Ishlatilganda yozuvda `rtsp_port_assumed` belgisi
qoladi — aks holda «kashfiyot yashil, kadr olish qora» nosozligi sababsiz
qolardi (Pitfall 8).
"""

NVR_DEVICE_TYPES: Final[frozenset[str]] = frozenset({"NVR", "DVR", "HDVR"})
"""D-04 ning tarmoqlanish nuqtasi — `InputProxy` yo'liga tushadigan turlar.

Qolganlari (`IPCamera`, `IPDome`, …) standalone yo'lidan boradi: ularda
`InputProxy` UMUMAN YO'Q va u `404` beradi (A.1, 2-qadam-B).
"""

SUPPORTED_MANUFACTURER: Final[str] = "hikvision"
"""MVP'da faqat Hikvision ISAPI (T-03-33, A.3 ning oxirgi qatori)."""


def assert_supported_device(device: DeviceInfo) -> None:
    """Qurilma qo'llab-quvvatlanadimi — YAGONA joyda (T-03-33).

    ⚠⚠ RAD ETISH SHARTI «`manufacturer != "hikvision"`» EMAS, «`manufacturer`
       BOR VA U Hikvision EMAS». Farq O'LCHANGAN faktdan chiqadi:

           DS-7616NI-K2 dumpi  ->  <manufacturer>hikvision</manufacturer>
           DS-7732NI-M4 dumpi  ->  maydon UMUMAN YO'Q          (!)

       Ikkalasi ham HAQIQIY Hikvision NVR va ikkalasi ham yozib olingan
       dumpdan. Ya'ni «maydon yo'q» = «boshqa ishlab chiqaruvchi» degan
       tenglama 32 kanalli NVR ni — Karmananing 25 kanaliga eng yaqin
       modelni — rad etardi. Nosozlik CI'da ko'rinmasdi: 6 kanalli
       standart stsenariy `DS-7616NI-K2` fixture'ini ishlatadi va unda
       maydon BOR.

    Qoldiq xavf ATAYIN qabul qilinadi va u kichik: `manufacturer` ni
    e'lon qilmaydigan, LEKIN `DeviceInfo`, `InputProxy` va `adminAccesses`
    ni Hikvision shaklida qaytaradigan qurilma bilan kashfiyot BARIBIR
    ishlaydi — u qaysi yorliq bilan sotilgani ahamiyatsiz. Soxta qurilma
    esa (sim'ning `not_hikvision` rejimi) o'zini BOSHQA ishlab chiqaruvchi
    deb ATAYIN e'lon qiladi va u rad etiladi.

    Raises:
        NvrError: `device_not_supported`, `detail.model` bilan — admin
            QAYSI qurilma rad etilganini bilishi kerak.
    """
    manufacturer = device.manufacturer.strip().lower()
    if manufacturer and SUPPORTED_MANUFACTURER not in manufacturer:
        raise NvrError("device_not_supported", {"model": device.model})


_STREAM_PATH_PREFIX: Final[str] = "Streaming/channels/"

_PICTURE_SUFFIX: Final[str] = "/picture"
"""Kadr olish yo'lining oxiri — `Streaming/channels/<id>/picture`."""

_MAIN_STREAM_NAME, _SUB_STREAM_NAME = CAPTURE_STREAM_VALUES
"""`cameras.capture_stream` ning ikkala qiymati — RO'YXATDAN OCHIB OLINADI.

Qo'lda `"main"` deb yozish bugungi qiymatda to'g'ri ishlardi, lekin
ro'yxatga uchinchi a'zo qo'shilgan kunda bu satr JIMGINA eskirardi:
`stream != "main"` shartida yangi qiymat sub-oqim deb talqin qilinardi.
Ochib olish esa o'sha kunda IMPORT paytida yiqiladi — ya'ni nosozlik
kadr olishda emas, ishga tushishda ko'rinadi.
"""

_JPEG_MAGIC: Final[bytes] = b"\xff\xd8\xff"
"""JPEG boshlanishi (SOI + birinchi marker bayti) — `quality.py` bilan bir xil qiymat.

Bu yerdagi nusxa `quality.py` ni IMPORT QILMAYDI va bu ataylab: ISAPI
klienti sifat filtriga bog'lanmasligi kerak (u kashfiyot yo'lida ham
ishlaydi va u yerda sifat qoidalari umuman yo'q). Uch bayt — protokol
fakti, loyihaning qarori emas.
"""


def _claims_rtsp_session(path: str) -> bool:
    """Bu yo'l NVR da RTSP SESSIYASINI da'vo qiladimi (D-07).

    ⚠⚠ `/picture` YO'Q VA BU FARQ D-07 NING BUTUN MAZMUNI. ISAPI ning
       kadr olish yo'li NVR'dan JPEG ni HTTP orqali oladi va **birorta
       RTSP sessiyasini ochmaydi** — shuning uchun sessiya bosimi ostida
       u zaxira emas, ENG XAVFSIZ usul.

    Sanagich `_classify()` ning `nvr_stream_limit` evristikasiga kiradi
    («shu klientda kamida bitta oqim da'vosi o'tgan edi»). `/picture` u
    yerga sanalsa, keyingi tarmoq uzilishi «NVR chegarasi to'ldi» deb
    talqin qilinardi — ya'ni adaptiv pasaytirish (04-07) chegarani
    tunnel uzilishi tufayli tushirib yuborardi va eng xavfsiz usul o'zini
    chegara qurboni deb e'lon qilardi.

    Simulyator ham AYNAN shu shaklda tuzatilgan (04-02): 3-fazadagi kod
    `/picture` yo'lida ham oqim da'vosini sanardi va u D-07 ning
    TESKARISINI modellardi.
    """
    return path.startswith(_STREAM_PATH_PREFIX) and not path.endswith(_PICTURE_SUFFIX)


_STREAM_LIMIT_MARKERS: Final[tuple[str, ...]] = (
    "maximum number of streams",
    "devicebusy",
)
"""A.5: chegaraning `reject` shaklidagi alomatlari — javob TANASIDAN.

⚠ HEURISTIKA, KAFOLAT EMAS. `03-RESEARCH.md` A.5 chegaraning wire
darajasida qanday ko'rinishini **LOW** ishonch bilan belgilaydi:
ba'zi firmware `453`/`503` beradi, ba'zisi ulanishni JIMGINA uzadi va
xato kodi UMUMAN bo'lmaydi. Shuning uchun:
  * backend faqat KOD beradi va xom javobni `detail.raw` da saqlaydi;
  * taxminiylik foydalanuvchi MATNIDA ifodalanadi (UI-SPEC §7.5), ya'ni
    bu faylda emas.
"""

_LOCKED_MARKER: Final[str] = "locked"


class _TransientServerError(Exception):
    """5xx — qayta urinish MA'NOLI bo'lgan yagona status sinfi.

    ⚠ Bu ATAYIN `httpx.HTTPStatusError` EMAS. Ikkalasi bir sinf bo'lganda
      retry predikati `401` ni tarmoq xatosidan ajrata olmasdi va D-03
      predikatning ICHIDA, ko'rinmas holda buzilardi.
    """

    def __init__(self, response: httpx.Response) -> None:
        self.response = response
        super().__init__(f"HTTP {response.status_code}")


@dataclass(frozen=True, slots=True)
class ProbeResult:
    """«Ulanishni tekshirish» tugmasining natijasi (UI-SPEC §4.5).

    Muvaffaqiyatli yo'lda `channels_preview` va `clock_drift_seconds`
    MAJBURIY:
      * kanallar soni — adminning «to'g'ri qurilmaga ulandimmi?» savoliga
        yagona javobi;
      * soat farqi — 300 s dan KICHIK bo'lsa ham ko'rsatiladi, chunki 250
        soniyalik farq bugun ishlaydi va ertaga sinadi.
    """

    ok: bool
    device: DeviceInfo | None = None
    clock_drift_seconds: float | None = None
    channels_preview: int | None = None
    rtsp_port: int | None = None
    rtsp_port_assumed: bool = False
    error_code: str | None = None
    error_detail: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class _Greeting:
    """Rekvizitsiz BIRINCHI javobdan olinadigan hamma narsa.

    Ikkala diagnostika ham BITTA borishdan chiqadi va bu ataylab: har
    qo'shimcha borish tunnel ortida qimmat, va ikkinchi so'rov qurilmaning
    holatini o'zgartirib qo'yishi mumkin edi.
    """

    drift_seconds: float | None
    device_time: datetime | None
    challenge: str


def _is_tls_error(exc: BaseException) -> bool:
    """TLS qo'l siqishining muvaffaqiyatsizligimi — sertifikat ishonchsizligi EMAS.

    ⚠ FARQ MUHIM (A.3): tunnel ichidagi O'Z-O'ZINI IMZOLAGAN sertifikat bu
      kodni ISHGA TUSHIRMAYDI — u `verify=False` bilan ATAYLAB qabul
      qilinadi, chunki WireGuard allaqachon transport ishonchini beradi.
      `nvr_tls_untrusted` sertifikat *ishonchsizligi* uchun emas, TLS ning
      *ishlamasligi* uchun: mos shifr to'plami yo'q, protokol versiyasi rad
      etildi yoki javob umuman TLS emas.
    """
    cause: BaseException | None = exc
    seen = 0
    while cause is not None and seen < 5:
        if isinstance(cause, ssl.SSLError):
            return True
        cause = cause.__cause__ or cause.__context__
        seen += 1
    return "ssl" in str(exc).lower()


def _should_retry(exc: BaseException) -> bool:
    """Retry predikati — D-03 ning YAGONA joyi.

    ⚠⚠ `httpx.HTTPStatusError` BU YERDA ATAYIN YO'Q VA QO'SHILMAYDI.
       Uni qo'shish `401` ni qayta urinishga aylantiradi va Hikvision
       hisobini 30 daqiqaga qulflaydi (T-03-29). Bu qatorni «umumiylashtirish»
       vasvasasi paydo bo'lsa: `tests/integration/test_nvr_errors.py::
       test_auth_failure_is_not_retried` aynan shuni o'lchaydi.

    ⚠ TLS xatosi ham QAYTA URINILMAYDI: qo'l siqish o'zidan o'ziga
      tuzalmaydi, uch marta urinish faqat kechikish qo'shadi.

    ⚠ `httpx.RemoteProtocolError` (`ProtocolError` -> `TransportError`,
      `NetworkError` EMAS) ham qamralmaydi: u D-05 ning «javobsiz uzilish»
      alomati va uni qayta urinish chegaraga yana urilardi.
    """
    if isinstance(exc, httpx.ConnectError):
        return not _is_tls_error(exc)
    if isinstance(exc, httpx.TimeoutException | httpx.NetworkError):
        return True
    return isinstance(exc, _TransientServerError)


def _looks_like_stream_limit(response: httpx.Response) -> bool:
    """Javob TANASIDA chegara alomati bormi (A.5 ning `reject` shakli)."""
    body = response.text.lower()
    return any(marker in body for marker in _STREAM_LIMIT_MARKERS)


def _diagnostic_text(body: bytes, tag: str) -> str | None:
    """Xato TANASIDAN bitta qiymatni namespace'dan qat'i nazar oladi.

    ⚠ Bu TASHXIS uchun va u HECH QACHON ISTISNO KO'TARMAYDI: biz allaqachon
      xato yo'lidamiz va tashxis parseri yiqilsa asosiy sabab (`401`)
      yo'qolib, o'rniga «XML parse bo'lmadi» chiqardi.

    `iter()` ATAYIN (`_children` emas): `<lockStatus>` `<userCheck>` ning
    ICHIDA yotadi va chuqurligi firmware bo'yicha o'zgarishi mumkin.
    """
    try:
        root = xml_fromstring(body)
    except (ValueError, SyntaxError):
        return None
    for element in root.iter():
        if local_name(element.tag) == tag:
            value = (element.text or "").strip()
            return value or None
    return None


def _snippet(response: httpx.Response) -> str:
    """Xom javob — `NvrError` konstruktori uni yana bir bor kesadi."""
    return f"HTTP {response.status_code} {response.text}".strip()


def resolve_rtsp_port(protocols: dict[str, int]) -> tuple[int, bool]:
    """`adminAccesses` xaritasidan RTSP portini oladi (A.2, Pitfall 8).

    Returns:
        `(port, assumed)`. `assumed=True` — javobda RTSP yozuvi topilmadi
        va 554 TAXMIN qilindi.

    ⚠ NEGA STANDART QIYMAT `rtsp_url()` DA EMAS, SHU YERDA: `app/services/
      rtsp.py` port argumentini MAJBURIY qiladi va o'z izohida sababini
      aytadi — standart qiymat u yerga qo'yilsa «taxmin qilindi» FAKTI
      yo'qolardi. Bayroq shu funksiyada tug'iladi va shu yerdan
      `nvr_devices.rtsp_port_assumed` ustuniga boradi.
    """
    port = protocols.get("RTSP")
    if port is None:
        return RTSP_FALLBACK_PORT, True
    return port, False


class IsapiClient:
    """Bitta NVR bilan HTTP muloqoti. Async context manager.

    ⚠ SIMULYATOR HAQIDA BIRORTA TARMOQLANISH YO'Q va bo'lmaydi. Bu klient
      uchun har qanday qurilma — bu `host`, `port` va rekvizit; ular esa
      bazadagi qatordan keladi. «Real qurilmaga o'tish — SOZLAMA
      o'zgarishi, kod o'zgarishi emas» (SC#7) da'vosining butun mazmuni
      shunda.
    """

    def __init__(
        self,
        base_url: str,
        username: str,
        password: str,
        *,
        timeout: httpx.Timeout | None = None,
        verify: bool = False,
        clock_drift_tolerance: float = CLOCK_DRIFT_TOLERANCE_SECONDS,
        retry_attempts: int = MAX_RETRY_ATTEMPTS,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._username = username
        self._auth = httpx.DigestAuth(username, password)
        self._basic = httpx.BasicAuth(username, password)
        self._clock_drift_tolerance = clock_drift_tolerance
        self._retry_attempts = retry_attempts
        self._stream_claims = 0
        self._basic_probe_used = False

        self._client = httpx.AsyncClient(
            timeout=timeout or DEFAULT_TIMEOUT,
            # ISAPI redirect QILMAYDI; qilsa bu shubhali va uni ko'r-ko'rona
            # kuzatish so'rovni (rekvizit bilan birga) boshqa xostga olib
            # borardi.
            follow_redirects=False,
            # ⚠ `verify=False` ATAYIN VA U SERTIFIKAT TEKSHIRUVINI EMAS,
            #   ISHONCH MANBAINI ko'chiradi: ISAPI chaqiruvi FAQAT WireGuard
            #   tunneli ichidan boradi (SC#5) va transport ishonchini tunnel
            #   beradi. Bozorlardagi NVR'lar o'z-o'zini imzolagan sertifikat
            #   bilan keladi va ularni almashtirish self-service qoidasini
            #   (D-01) buzardi — admin sertifikat o'rnata olmaydi.
            #   Standart yo'l umuman `http://` (A.3 jadvali).
            verify=verify,  # noqa: S501
        )

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        """`app/main.py:112-116` naqshi: resurs egasi uni O'ZI yopadi."""
        await self._client.aclose()

    # ------------------------------------------------------------------
    # Transport
    # ------------------------------------------------------------------

    def _url(self, path: str) -> str:
        return f"{self._base_url}{ISAPI_PREFIX}/{path.lstrip('/')}"

    async def _attempt(self, path: str, *, auth: httpx.Auth | None) -> httpx.Response:
        """BITTA urinish. 5xx `_TransientServerError`, 4xx `HTTPStatusError`.

        Tartib ahamiyatli: chegara alomati (`stream_limit`) 5xx ni retry
        qatlamiga BERMAYDI — qayta urinish chegaraga yana urilardi va
        qurilmani battar bosardi.
        """
        response = await self._client.get(self._url(path), auth=auth)

        if response.status_code >= 500 and not _looks_like_stream_limit(response):
            raise _TransientServerError(response)

        # 4xx (va chegara alomatidagi 5xx) -> `httpx.HTTPStatusError`.
        # ⚠ U retry predikatidan TASHQARIDA qoladi (D-03).
        response.raise_for_status()

        if _claims_rtsp_session(path):
            self._stream_claims += 1
        return response

    async def _send(self, path: str, *, auth: httpx.Auth | None) -> httpx.Response:
        """Retry qatlami — FAQAT tarmoq sinfi (`_should_retry`)."""
        retrying: AsyncRetrying = AsyncRetrying(
            stop=stop_after_attempt(self._retry_attempts),
            wait=wait_exponential(multiplier=0.3, max=2.0),
            retry=retry_if_exception(_should_retry),
            reraise=True,
        )
        return await retrying(self._attempt, path, auth=auth)

    # ------------------------------------------------------------------
    # Xatoga xaritalash — `03-RESEARCH.md` A.3 jadvali, satrma-satr
    # ------------------------------------------------------------------

    def _classify(self, exc: BaseException, path: str) -> NvrError:
        if isinstance(exc, _TransientServerError):
            return NvrError("nvr_isapi_unavailable", {"raw": _snippet(exc.response)})

        if isinstance(exc, httpx.HTTPStatusError):
            return self._classify_status(exc.response)

        if isinstance(exc, httpx.ConnectError) and _is_tls_error(exc):
            return NvrError("nvr_tls_untrusted", {"raw": f"{type(exc).__name__}: {exc}"})

        if isinstance(exc, httpx.TransportError):
            # D-05 ning IKKINCHI shakli: javob UMUMAN kelmadi. Buni
            # chegaradan ajratadigan yagona narsa — XULQ (A.5): shu
            # klientda kamida bitta oqim da'vosi O'TGAN va endi keyingisi
            # uzilyapti.
            if _claims_rtsp_session(path) and self._stream_claims >= 1:
                return NvrError(
                    "nvr_stream_limit",
                    {
                        "raw": (
                            f"{type(exc).__name__}: {exc} "
                            f"(oldin {self._stream_claims} oqim da'vosi o'tgan edi)"
                        )
                    },
                )
            return NvrError("nvr_unreachable", {"raw": f"{type(exc).__name__}: {exc}"})

        return NvrError("nvr_unreachable", {"raw": f"{type(exc).__name__}: {exc}"})

    def _classify_status(self, response: httpx.Response) -> NvrError:
        """A.3 jadvalining status-kodli qatorlari."""
        status = response.status_code
        raw = _snippet(response)

        if status == httpx.codes.UNAUTHORIZED:
            return self._classify_unauthorized(response, raw)

        if status == httpx.codes.FORBIDDEN:
            return NvrError("nvr_user_no_permission", {"raw": raw})

        if status == httpx.codes.NOT_FOUND:
            return NvrError("nvr_isapi_unavailable", {"raw": raw})

        if status >= 500 and _looks_like_stream_limit(response):
            return NvrError("nvr_stream_limit", {"raw": raw})

        return NvrError("nvr_isapi_unavailable", {"raw": raw})

    def _classify_unauthorized(self, response: httpx.Response, raw: str) -> NvrError:
        """`401` NING UCHTA MA'NOSI — status kod ularni AJRATMAYDI.

        Tartib ahamiyatli: qulf HAMMASIDAN oldin (u boshqa hamma
        tashxisni ma'nosiz qiladi), keyin `stale`, oxirida rekvizit.
        """
        body = _diagnostic_text(response.content, "lockStatus")
        if body is not None and _LOCKED_MARKER in body.lower():
            detail: dict[str, Any] = {"raw": raw}
            unlock_seconds = _diagnostic_text(response.content, "unlockTime")
            if unlock_seconds is not None and unlock_seconds.isdigit():
                unlock_at = datetime.now(tz=UTC) + timedelta(seconds=int(unlock_seconds))
                detail["unlock_at"] = unlock_at.isoformat()
            return NvrError("nvr_account_locked", detail)

        challenge = response.headers.get("WWW-Authenticate", "")
        if "stale=true" in challenge.lower().replace('"', "").replace(" ", ""):
            # A.3: `stale` ning takrorlanishi deyarli har doim SOAT FARQI
            # alomati — nonce vaqtga bog'langan va qurilma uni «eskirgan»
            # deb hisoblaydi.
            return NvrError("nvr_digest_stale", {"raw": raw})

        if _advertises_basic_only(challenge):
            return NvrError("nvr_auth_mode_basic_only", {"raw": raw})

        return NvrError("nvr_bad_credentials", {"raw": raw})

    # ------------------------------------------------------------------
    # Ommaviy yuza
    # ------------------------------------------------------------------

    @property
    def stream_claims(self) -> int:
        """Shu klient NVR da nechta RTSP sessiyasini da'vo qilgani (D-07).

        Ommaviy — chunki bu son `_classify()` ning `nvr_stream_limit`
        evristikasining kirishi va uning `/picture` yo'lida NOL bo'lishi
        alohida o'lchanadigan da'vo (`test_frame_source.py::
        test_the_isapi_path_claims_no_rtsp_session`). Xususiy maydonga
        test orqali tegish o'lchovni mahsulot yuzasidan uzib qo'yardi.
        """
        return self._stream_claims

    async def get_xml(self, path: str) -> bytes:
        """`GET /ISAPI/{path}` — xom baytlar yoki `NvrError`.

        Parse QILMAYDI: parser sof qatlam bo'lib qoladi va uni tarmoqsiz
        sinash mumkin (`tests/unit/test_isapi_parser.py`).
        """
        try:
            response = await self._send(path, auth=self._auth)
        except (httpx.HTTPError, _TransientServerError) as exc:
            raise self._classify(exc, path) from exc
        return response.content

    async def fetch_picture(self, channel_no: int, stream: str = "main") -> bytes:
        """`GET /ISAPI/Streaming/channels/{kanal}{oqim}/picture` — XOM JPEG baytlari.

        Hikvision oqim identifikatorini `{kanal}{oqim}` shaklida quradi:
        `01` — asosiy oqim, `02` — sub-oqim (`rtsp.py::stream_id` bilan
        AYNAN bir xil qoida va aynan o'sha funksiyadan olinadi — ikkinchi
        nusxa bir kun ajralib ketardi).

        ⚠⚠ BU METOD XML PARSERIDAN O'TMAYDI. `get_xml()` javobni XML deb
           kutadi va uni `defusedxml` ga beradi; bu yerda esa javob —
           `image/jpeg`, ya'ni baytlar O'ZGARTIRILMASDAN qaytariladi.

        ⛔ LOGIN VA PAROLNI SO'ROV PARAMETRIDA YUBORADIGAN ISAPI VARIANTI
           ISHLATILMAYDI (§S-9). Hikvision firmware'i bunday shaklni ham
           qabul qiladi va u «bir chaqiruvga arzon» ko'rinadi — lekin
           parolni so'rov satriga, u yerdan nginx access-log'iga va
           `sentry-sdk` ning httpx breadcrumb'iga (`data` da to'liq URL
           turadi) olib chiqardi. Yagona ruxsat etilgan yo'l —
           `httpx.DigestAuth`, ya'ni parol SARLAVHADA va u hech qayerga
           yozilmaydi.

        ⚠ D-07: bu yo'l NVR da **birorta RTSP sessiyasini ochmaydi**
          (`_claims_rtsp_session` docstringi).

        ⚠ RETRY SIYOSATI QAYTA YOZILMAYDI: `_send()` ning mavjud
          `AsyncRetrying` qatlami (`_should_retry` — `401` HECH QACHON
          qayta urinilmaydi) shu yerda ham amal qiladi. Ikkinchi retry
          qatlami urinishlar sonini ko'paytirib, D-03 ning qulflash
          arifmetikasini ishga tushirardi.

        Args:
            channel_no: NVR dagi kanal raqami (1 dan boshlanadi).
            stream: `"main"` yoki `"sub"` (`cameras.capture_stream`).

        Returns:
            JPEG baytlari — HECH QANDAY o'zgartirishsiz.

        Raises:
            NvrError: `channel_offline` (kanal yo'q — `404`),
                `nvr_isapi_unavailable` (javob keldi, lekin ichida TASVIR
                YO'Q) yoki `_classify()` ning qolgan kodlari.
        """
        if stream not in CAPTURE_STREAM_VALUES:
            raise ValueError(
                f"noma'lum capture_stream={stream!r}. Ruxsat etilganlar: "
                f"{list(CAPTURE_STREAM_VALUES)} (`cameras.capture_stream` CHECK'i)."
            )
        path = (
            f"{_STREAM_PATH_PREFIX}"
            f"{stream_id(channel_no, substream=stream == _SUB_STREAM_NAME)}"
            f"{_PICTURE_SUFFIX}"
        )
        try:
            response = await self._send(path, auth=self._auth)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == httpx.codes.NOT_FOUND:
                # ⚠ `nvr_isapi_unavailable` DAN AJRATILADI: `/picture`
                #   yo'lida `404` «endpoint yo'q» emas, «bu KANAL yo'q»
                #   degani (sim buni ATAYIN 400 dan ajratadi — shakl
                #   buzuq bo'lsa 400, kanal yo'q bo'lsa 404). Admin uchun
                #   ikkalasi butunlay boshqa ish: birinchisi bizning
                #   kodimiz, ikkinchisi uning kamerasi.
                raise NvrError("channel_offline", {"raw": _snippet(exc.response)}) from exc
            raise self._classify(exc, path) from exc
        except (httpx.HTTPError, _TransientServerError) as exc:
            raise self._classify(exc, path) from exc

        body = response.content
        # ⚠ `Content-Type` O'QILADI, LEKIN UNGA ISHONILMAYDI. Ba'zi
        #   firmware va proxy xato sahifasini `image/jpeg` sarlavhasi
        #   bilan qaytaradi (T-04-25). Sarlavhaga ishonadigan tekshiruv
        #   HTML sahifani yaroqli kadr deb qabul qilardi, ya'ni yagona
        #   ishonchli darvoza — BAYTLARNING O'ZI. Bu §C.7 ning magic-bayt
        #   zanjirining IKKINCHI qatlami (birinchisi `frame_source`,
        #   uchinchisi `quality.analyze`).
        if not body.startswith(_JPEG_MAGIC):
            content_type = response.headers.get("Content-Type", "?")
            raise NvrError(
                "nvr_isapi_unavailable",
                {
                    "raw": (
                        f"`{_PICTURE_SUFFIX.lstrip('/')}` javobi JPEG emas "
                        f"(Content-Type={content_type}, {len(body)} bayt)"
                    )
                },
            )
        return body

    async def greet(self) -> _Greeting:
        """REKVIZITSIZ birinchi so'rov — soat farqi va auth rejimi BIR borishda.

        ⚠ Bu so'rovda `Authorization` sarlavhasi YO'Q, ya'ni qurilmaning
          qulflash hisoblagichi QO'ZG'ALMAYDI. Butun erta-tashxis
          strategiyasi shunga tayanadi.
        """
        try:
            response = await self._send("System/deviceInfo", auth=None)
        except httpx.HTTPStatusError as exc:
            # `401` bu yerda KUTILGAN natija — u xato emas, SALOMLASHUV.
            response = exc.response
        except (httpx.HTTPError, _TransientServerError) as exc:
            raise self._classify(exc, "System/deviceInfo") from exc

        raw_date = response.headers.get("Date")
        if raw_date is None:
            # Sarlavha yo'qligi soat farqi haqida HECH NIMA aytmaydi —
            # tekshiruv o'tkazib yuboriladi, xato ko'tarilmaydi.
            return _Greeting(None, None, response.headers.get("WWW-Authenticate", ""))

        try:
            device_time = parsedate_to_datetime(raw_date)
        except (TypeError, ValueError):
            return _Greeting(None, None, response.headers.get("WWW-Authenticate", ""))

        drift = (device_time - datetime.now(tz=UTC)).total_seconds()
        return _Greeting(drift, device_time, response.headers.get("WWW-Authenticate", ""))

    async def clock_drift_seconds(self) -> float | None:
        """Qurilma soatining server soatidan farqi (soniya) yoki `None`.

        Musbat qiymat — qurilma soati OLDINDA. `None` — qurilma `Date`
        sarlavhasini bermadi va tekshiruv o'tkazib yuborildi.
        """
        return (await self.greet()).drift_seconds

    async def list_channels(self, device: DeviceInfo) -> list[ChannelRow]:
        """D-04 TARMOQLANISHINING YAGONA MANBAI.

        `NVR`/`DVR`/`HDVR` -> `ContentMgmt/InputProxy/channels` (A.1 da
        AVTORITETLI deb belgilangan: u faqat HAQIQATAN ulangan kameralarni
        beradi);
        qolganlari -> `System/Video/inputs/channels` (standalone kamera).

        ⚠ NVR'da `System/Video/inputs/channels` ATAYIN CHAQIRILMAYDI: u
          qurilmaning video-kirish SLOTLARINI sanaydi va bo'sh slot ham
          «kanal» bo'lib chiqardi. 03-02 yozib olingan IKKALA NVR dumpida
          ham bu endpoint uchun `403` qayd etilgan — ya'ni bu xulosa
          taxmin emas, O'LCHOV.
        """
        skipped: list[str] = []
        if device.device_type.upper() in NVR_DEVICE_TYPES:
            rows = parse_input_proxy_channels(
                await self.get_xml("ContentMgmt/InputProxy/channels"), skipped=skipped
            )
        else:
            rows = parse_video_input_channels(await self.get_xml("System/Video/inputs/channels"))

        if skipped:
            # Kanal O'TKAZIB YUBORILDI, lekin JIM qolmadi. `error_detail`
            # ga tushmaydi: UI-SPEC §7.4 allowlist'ida ro'yxat uchun kalit
            # yo'q va allowlist zaiflashtirilmaydi.
            log.warning("isapi_channel_skipped", username=self._username, skipped=skipped)
        return rows

    async def probe(self) -> ProbeResult:
        """«Ulanishni tekshirish» — xato KO'TARMAYDI, uni NATIJAGA aylantiradi.

        Ketma-ketlik `03-RESEARCH.md` A.1 dan va TARTIB AHAMIYATLI:
          1. rekvizitsiz salomlashuv -> soat farqi va auth rejimi;
          2. `System/deviceInfo`     -> model va `deviceType`;
          3. `Security/adminAccesses`-> RTSP porti (554 TAXMIN QILINMAYDI);
          4. kanallar ro'yxati       -> `channels_preview`.
        """
        try:
            greeting = await self.greet()
            self._assert_clock_is_close(greeting)
            await self._assert_digest_is_offered(greeting)

            device = parse_device_info(await self.get_xml("System/deviceInfo"))
            assert_supported_device(device)

            ports = parse_admin_accesses(await self.get_xml("Security/adminAccesses"))
            rtsp_port, assumed = resolve_rtsp_port(ports)
            channels = await self.list_channels(device)
        except NvrError as error:
            log.info(
                "nvr_probe_failed",
                username=self._username,
                base_url=self._base_url,
                error_code=error.code,
            )
            return ProbeResult(ok=False, error_code=error.code, error_detail=error.detail)

        return ProbeResult(
            ok=True,
            device=device,
            clock_drift_seconds=greeting.drift_seconds,
            channels_preview=len(channels),
            rtsp_port=rtsp_port,
            rtsp_port_assumed=assumed,
        )

    def _assert_clock_is_close(self, greeting: _Greeting) -> None:
        """Soat farqi `401` DAN OLDIN — bu yo'lda rekvizit yuborilmagan."""
        drift = greeting.drift_seconds
        if drift is None or abs(drift) <= self._clock_drift_tolerance:
            return
        raise NvrError(
            "nvr_clock_drift",
            {
                "drift_seconds": round(drift, 1),
                "device_time": (greeting.device_time.isoformat() if greeting.device_time else None),
                "server_time": datetime.now(tz=UTC).isoformat(),
            },
        )

    async def _assert_digest_is_offered(self, greeting: _Greeting) -> None:
        """Qurilma Digest TAKLIF QILMASA — bu `digest/basic` firmware alomati.

        ⚠ BASIC SINOVI FAQAT DIAGNOSTIKA UCHUN VA FAQAT BIR MARTA: u ham
          rekvizit urinishi va u ham qulflash hisoblagichiga tushadi.

        ⚠ VA U FAQAT SHU YO'LDA BAJARILADI. Reja uni «`nvr_bad_credentials`
          xulosasidan OLDIN» qo'yishni aytadi, lekin o'sha joyda u
          `test_auth_failure_is_not_retried` ning «urinishlar AYNAN 1»
          da'vosini buzardi: noto'g'ri parol yo'lida sanoq 2 bo'lib
          qolardi. Ajratuvchi belgi challenge SXEMASIDA: `basic`
          rejimidagi firmware `WWW-Authenticate: Basic ...` yuboradi va
          Digest'ni UMUMAN taklif qilmaydi, ya'ni noto'g'ri parol yo'li
          bu tarmoqqa hech qachon tushmaydi. Bu real qurilma xulqiga ham
          MOSROQ — biz Digest'ni «sinab ko'rmaymiz», qurilma uni taklif
          qilmaganini O'QIYMIZ.

        Basic **avtomatik zaxira YO'L EMAS** (T-03-36): natija —
        `nvr_auth_mode_basic_only` TAVSIYASI, parolni base64 bilan
        tarmoqqa chiqaradigan doimiy rejim emas.
        """
        if not _advertises_basic_only(greeting.challenge) or self._basic_probe_used:
            return
        self._basic_probe_used = True

        try:
            await self._send("System/deviceInfo", auth=self._basic)
        except httpx.HTTPStatusError:
            # Basic ham o'tmadi -> rejim emas, rekvizit muammosi.
            # Digest yo'li o'z xulosasini o'zi chiqaradi.
            return
        except (httpx.HTTPError, _TransientServerError) as exc:
            raise self._classify(exc, "System/deviceInfo") from exc

        raise NvrError(
            "nvr_auth_mode_basic_only",
            {"raw": f"WWW-Authenticate: {greeting.challenge}"},
        )


def _advertises_basic_only(challenge: str) -> bool:
    """`WWW-Authenticate` faqat `Basic` taklif qilyaptimi (Digest'siz)."""
    lowered = challenge.lower()
    return "basic" in lowered and "digest" not in lowered
