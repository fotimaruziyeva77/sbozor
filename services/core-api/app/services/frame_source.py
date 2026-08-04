"""Uchta kadr olish usuli — BITTA protokol ortida (D-06/D-07, §S-9, §S-10).

=============================================================================
1-MAJBURIYAT: UCHTA USUL, BITTA PROTOKOL — VA TANLOV **BAZADAN**.

`nvr_devices.capture_method` uchta qiymatdan birini oladi (`go2rtc` /
`isapi` / `ffmpeg`) va bu modul o'sha satrni bajariladigan yo'lga
aylantiradi. `discovery.py:208-216` ning mulohazasi bu yerda ham
so'zma-so'z amal qiladi:

    «Manzil BAZADAN quriladi va boshqa hech qayerdan: real qurilmaga
     o'tish — SOZLAMA o'zgarishi, kod o'zgarishi emas.»

⚠ `isapi` — «ZAXIRA» EMAS (D-07). ISAPI `/picture` NVR da **birorta RTSP
  sessiyasini ochmaydi**, go2rtc esa sessiyani ochiq ushlab turadi. Ya'ni
  NVR ning o'lchanmagan sessiya chegarasiga yaqinlashganda `isapi` ENG
  XAVFSIZ yo'l bo'lib qoladi. Standart `go2rtc` bo'lishining sababi
  boshqa: u jonli ko'rish uchun baribir ishlab turadi, ya'ni kadr olish
  qo'shimcha ulanish ochmaydi.
=============================================================================

=============================================================================
2-MAJBURIYAT: KLIENT EGALIGI BU YERDA **TESKARI** (`go2rtc.py:199-203` DAN
FARQ) — VA FARQ ANIQ YOZILADI.

`Go2rtcClient` ning docstringi «klient `app.state` da SAQLANMAYDI: u
`async with` bilan qisqa muddatga ochiladi» deydi va sababini «go2rtc
bilan muloqot juda siyrak (kunlik bir necha ko'rish so'rovi)» deb
asoslaydi.

**Bu dalil 4-fazada AMAL QILMAYDI.** Kadr olish siyrak emas: bitta
bozorda kuniga ~175 chaqiruv va cho'qqida AYNI BIR daqiqada 25 ta. Har
chaqiruvda yangi `httpx.AsyncClient` ochish har kadrga yangi TCP ulanishi
(va ISAPI yo'lida yangi Digest handshake — ya'ni har kadr uchun ORTIQCHA
`401` borish) narxini qo'shardi.

Shuning uchun klientlar `FrameSourcePool` ichida, worker jarayonining
holatida (`TaskiqState`) yashaydi va `WORKER_SHUTDOWN` da yopiladi.
Farq shu yerda yozilgan, chunki aks holda keyingi tahrirlovchi
`go2rtc.py` ning qarama-qarshi izohini ko'rib chalkashardi.

⚠ ISAPI klienti BATCH davomida bitta: `for_device()` uni bir marta ochadi
  va o'sha NVR ning barcha kameralari uchun qayta ishlatadi
  (`isapi/client.py` ning «BITTA klient butun kashfiyot davomida qayta
  ishlatiladi» qoidasi bilan aynan bir xil sabab).
=============================================================================

=============================================================================
3-MAJBURIYAT: ⛔ KESHLANGAN KADR SO'RALMAYDI (Pitfall 8, T-04-52).

go2rtc ning `/api/frame.jpeg` yo'li keshlangan kadrni qaytaradigan
parametrni qo'llab-quvvatlaydi. **U bu yerda ishlatilmaydi va uni
qo'shish yo'li strukturaviy ravishda yopilgan:** so'rov parametrlari
ALLOW-LIST (`_ALLOWED_FRAME_PARAMS`) bilan quriladi va boshqa har qanday
kalit `ValueError` beradi.

Sabab dalil zanjirida: keshlangan kadr «bu kadr 06:30 da olingan»
da'vosini YOLG'ON qiladi. Nosozlik JIM bo'lardi — hisobotdagi son
o'zgaradi, xato chiqmaydi, birorta test qizarmaydi va 6-faza noto'g'ri
kadrni dalil deb hisoblardi.
=============================================================================

=============================================================================
4-MAJBURIYAT: ⛔ OQIM RO'YXATDAN CHIQARILMAYDI (D-11).

Kadr olingandan keyin `remove_stream()` CHAQIRILMAYDI. go2rtc yalqov:
tomoshabin qolmasa RTSP sessiyasini O'ZI yopadi. Har kadrdan keyin
ro'yxatdan chiqarish keyingi slotda qayta ro'yxatga olishni majburlardi —
ya'ni har kadr uchun ikkita ortiqcha HTTP borish VA NVR ga yangi RTSP
handshake, aynan sessiya bosimi eng yuqori bo'lgan daqiqada.

Ro'yxatdan chiqarish faqat kamera ARXIVLANGANDA bo'ladi va u 3-fazadagi
mavjud yo'lda (`api/v1/cameras.py`) qoladi.
=============================================================================

=============================================================================
5-MAJBURIYAT: MUVAFFAQIYAT **NATIJADAN** O'LCHANADI (§S-10, 03-14).

03-14 mock'siz o'lchovi `raise_for_status()` ga so'zsiz ishonish jonli
ko'rishni ISHLAB TURGAN holatda 503 qilishini ko'rsatdi. Bu yerda
TESKARI xavf ham bor va u battar: `200 OK` + `Content-Type: image/jpeg`
+ tanada HTML xato sahifasi. Sarlavhaga ishonadigan filtr o'sha sahifani
YAROQLI BILLING KADRI sifatida saqlardi.

Shuning uchun `capture_frame()` javob BAYTLARINI tekshiradi: ular JPEG
magic-baytidan boshlanmasa `capture_invalid_response` beriladi — status
kodi va `Content-Type` nima deganidan QAT'I NAZAR. Bu §C.7 zanjirining
BIRINCHI qatlami; ikkinchisi ISAPI protokoli chegarasida
(`IsapiClient.fetch_picture`), uchinchisi `quality.analyze()` da.
=============================================================================

⚠ SIR: parol UCH yo'lda ham ushlanadi (go2rtc `src`, ISAPI Digest, ffmpeg
  RTSP URL) va UCHALASIDA HAM u istisno matniga chiqmaydi. Qoidalar §S-9
  dan: istisno matni interpolyatsiya QILINMAYDI (faqat TURI), zanjir
  `from None` bilan uziladi va istisno `except` blokidan TASHQARIDA
  ko'tariladi (`storage.py::_call` bilan bir xil nozik sabab —
  `__context__` ham bo'sh qolsin). Ochiq qiymatga borish AYNAN BITTA
  joyda va u subprocess argumentiga uzatilishidan bevosita oldin turadi —
  buni matn darvozasi SANAB tekshiradi, ya'ni bu izohda o'sha chaqiruvning
  literal shakli ATAYIN yozilmagan.
"""

from __future__ import annotations

import asyncio
import time
from contextlib import AsyncExitStack, asynccontextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final, Protocol

import httpx
import structlog
from sbozor_core.enums import CaptureMethod
from sbozor_core.models.snapshot import CAPTURE_METHOD_VALUES

from app.services.capture_errors import (
    CAPTURE_BAD_CREDENTIALS,
    CAPTURE_CAMERA_OFFLINE,
    CAPTURE_INVALID_RESPONSE,
    CAPTURE_SOURCE_UNREACHABLE,
    CAPTURE_STREAM_LIMIT,
    CAPTURE_TIMEOUT,
    CaptureError,
)
from app.services.go2rtc import Go2rtcClient, Go2rtcError
from app.services.isapi.client import IsapiClient
from app.services.isapi.errors import NvrError

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Mapping

    from pydantic import SecretStr

log = structlog.get_logger(__name__)

__all__ = [
    "FFMPEG_TIMEOUT_SECONDS",
    "FRAME_PATH",
    "ISAPI_TO_CAPTURE",
    "JPEG_MAGIC",
    "UNKNOWN_CAPTURE_METHOD",
    "UNSAFE_FRAME_PARAM",
    "CaptureTarget",
    "CapturedFrame",
    "DeviceEndpoint",
    "FrameSource",
    "FrameSourceError",
    "FrameSourcePool",
    "capture_frame",
]


FRAME_PATH: Final[str] = "/api/frame.jpeg"
"""go2rtc ning kadr yo'li — `03-14` da mock'siz o'lchangan endpoint."""

JPEG_MAGIC: Final[bytes] = b"\xff\xd8\xff"
"""JPEG boshlanishi (SOI + birinchi marker bayti).

`quality.py::_SOI` bilan BIR XIL qiymat, lekin undan IMPORT QILINMAYDI va
bu ataylab: bu modul `Pillow` ga ham, sifat chegaralariga ham
bog'lanmaydi. Uch bayt — protokol fakti, loyihaning qarori emas.
"""

_SRC_PARAM: Final[str] = "src"
_ALLOWED_FRAME_PARAMS: Final[frozenset[str]] = frozenset({_SRC_PARAM})
"""Kadr so'rovida ruxsat etilgan YAGONA parametr (modul docstringi, 3-band)."""

UNSAFE_FRAME_PARAM: Final[str] = "unsafe_frame_parameter"
"""Allow-listdan tashqari parametr — `ValueError` ning matni."""

UNKNOWN_CAPTURE_METHOD: Final[str] = "unknown_capture_method"
"""Noma'lum yoki mavjud bo'lmagan kadr olish usuli — `ValueError` ning matni."""

FRAME_TIMEOUT_SECONDS: float = 15.0
"""go2rtc dan kadr kutishning yuqori chegarasi.

⚠ CHEKSIZ HECH QACHON: osilib qolgan chaqiruv batch semaforini ushlab
  turardi va bitta nosoz kamera butun NVR ning slotini yeb qo'yardi
  (`isapi/client.py::DEFAULT_TIMEOUT` bilan bir xil mulohaza).

Qiymat sovuq kadr byudjetidan (~4 s) uch barobar saxiy: go2rtc oqimni
endi ro'yxatga olgan bo'lsa birinchi keyframe kutiladi.
"""

FFMPEG_TIMEOUT_SECONDS: float = 25.0
"""`ffmpeg` bir martalik kadrining chegarasi — go2rtc dan KATTAROQ.

Sabab RESEARCH §B.6 jadvalida o'lchangan: bu yo'l TO'LIQ RTSP handshake
va keyframe kutishini o'z ichiga oladi (3–10 s), ya'ni u ta'rifi bo'yicha
sekinroq. `FRAME_TIMEOUT_SECONDS` bilan bir xil qilish `ffmpeg` ni
«oxirgi chora» sifatida foydasiz qilardi — u aynan boshqa ikkalasi
ishlamaganda chaqiriladi.

⚠ MODUL DARAJASIDA VA `Final` EMAS: test uni almashtirib, timeout yo'lini
  soniyalar kutmasdan o'lchaydi (`test_frame_source.py`).
"""


class FrameSourceError(CaptureError):
    """Kadr olishning rad etilishi — `CaptureError` ning kadr-manba shoxi.

    ⚠ ALOHIDA SINF, LEKIN YANGI TAKSONOMIYA EMAS: `code` baribir
      `CAPTURE_ERROR_CODES` reyestridan keladi (`CaptureError.__init__`
      allowlist'ni tekshiradi). Sinf faqat «bu nosozlik kadr OLISH
      bosqichida bo'ldi» degan chegarani belgilaydi — `capture_batch`
      uni `StorageError` dan shu bilan ajratadi.

    ⚠ MATNIGA XOM ISTISNO INTERPOLYATSIYA QILINMAYDI (T-04-49). Sabab
      `_failure()` docstringida.
    """


def _failure(code: str, reason: str) -> FrameSourceError:
    """Xato kodini SIRSIZ `FrameSourceError` ga aylantiradi (T-04-49).

    =========================================================================
    ⚠⚠ XOM ISTISNONING MATNI — HAQIQIY OQISH YO'LI.

    `httpx.HTTPStatusError` ning matni TO'LIQ so'rov URL'ini o'z ichiga
    oladi, go2rtc ning `PUT /api/streams` URL'i esa REKVIZITLI manbani
    (`?src=rtsp://admin:PAROL@...`). `ffmpeg` ning `stderr` i ham aynan
    o'sha URL'ni chop etadi. Ya'ni `f"... : {exc}"` shaklidagi bitta qator
    parolni istisnoga, u yerdan jurnalga va Sentry'ga olib chiqardi.

    Diagnostika uchun IKKI fakt yetadi va ikkalasi ham sirsiz: QAYSI
    kod va QAYSI xato turi (yoki status). «Qaysi kamera» savoliga
    chaqiruvchining jurnal qatori javob beradi — u `camera_id` ni O'ZI
    biladi.
    =========================================================================
    """
    return FrameSourceError(code, reason)


def _reason(exc: BaseException) -> str:
    """Istisnodan olinadigan YAGONA narsa — uning TURI.

    `str(exc)` HECH QACHON: u URL'ni, u esa parolni tashiydi.
    """
    return type(exc).__name__


def _frame_params(**params: str) -> dict[str, str]:
    """So'rov parametrlarini ALLOW-LIST ostida quradi (modul docstringi, 3-band).

    Raises:
        ValueError: `UNSAFE_FRAME_PARAM` matni bilan. Tip ataylab oddiy
            `ValueError` — bunday chaqiruv mahsulot yo'lidan HECH QACHON
            kelmaydi va u kelishi KODDAGI xatoni bildiradi
            (`assert_safe_go2rtc_src` bilan bir xil qaror).
    """
    extra = sorted(set(params) - _ALLOWED_FRAME_PARAMS)
    if extra:
        raise ValueError(f"{UNSAFE_FRAME_PARAM}: {extra}")
    return params


ISAPI_TO_CAPTURE: Final[dict[str, str]] = {
    # --- Autentifikatsiya: uchalasi ham NVR hisobini qulflaydigan yo'l ---
    "nvr_bad_credentials": CAPTURE_BAD_CREDENTIALS,
    "nvr_account_locked": CAPTURE_BAD_CREDENTIALS,
    "nvr_user_no_permission": CAPTURE_BAD_CREDENTIALS,
    # --- Sozlama: qurilma javob beradi, lekin muloqot qurilmaydi ---
    "nvr_clock_drift": CAPTURE_SOURCE_UNREACHABLE,
    "nvr_digest_stale": CAPTURE_BAD_CREDENTIALS,
    "nvr_auth_mode_basic_only": CAPTURE_BAD_CREDENTIALS,
    # --- Tarmoq va qurilma ---
    "nvr_unreachable": CAPTURE_SOURCE_UNREACHABLE,
    "nvr_tls_untrusted": CAPTURE_SOURCE_UNREACHABLE,
    "device_not_supported": CAPTURE_SOURCE_UNREACHABLE,
    "nvr_stream_limit": CAPTURE_STREAM_LIMIT,
    "channel_offline": CAPTURE_CAMERA_OFFLINE,
    # --- Javob keldi, lekin ichida TASVIR YO'Q ---
    "nvr_isapi_unavailable": CAPTURE_INVALID_RESPONSE,
}
"""ISAPI taksonomiyasi -> kadr olish taksonomiyasi. TO'LIQ xarita.

⚠ STANDART QIYMAT (`.get(code, fallback)`) ATAYIN YO'Q. U yangi ISAPI
  kodini jimgina `capture_source_unreachable` ga aylantirardi va admin
  butunlay boshqa joyni qidirardi (§S-5 ning aynan o'zi). To'liqlik IKKI
  TOMONLAMA darvoza bilan qulflangan (`test_frame_source.py::
  test_every_isapi_code_has_a_capture_code`).

⚠ `nvr_isapi_unavailable` -> `capture_invalid_response` — bu xarita
  ichidagi eng nozik qator. `/picture` yo'lida bu kod IKKI holatda
  chiqadi va ikkalasi ham «javob keldi, lekin ichida tasvir yo'q»:
  `5xx` (NVR o'zini yomon his qilyapti) va JPEG bo'lmagan tana. Kanal
  YO'QLIGI esa alohida kod oladi (`channel_offline`), ya'ni «kamera
  oflayn» bilan «javob buzuq» aralashmaydi.
"""


@dataclass(frozen=True, slots=True)
class CaptureTarget:
    """Bitta kadr olish uchun yetarli minimum — hammasi BAZADAN.

    ORM obyekti EMAS, oddiy qiymatlar (`discovery.py::_DeviceContext`
    bilan aynan bir xil qaror): kadr olish tranzaksiyadan TASHQARIDA
    bajariladi va detached obyektning har bir atributi
    `DetachedInstanceError` xavfini olib yurardi.
    """

    stream_name: str
    """go2rtc dagi oqim nomi (`cameras.stream_name`, `cam_<uuid4>`)."""

    channel_no: int
    """NVR dagi jismoniy uya (`cameras.channel_no`) — ISAPI yo'li uchun."""

    stream: str
    """`cameras.capture_stream`: `"main"` yoki `"sub"` (D-09)."""

    rtsp_source: SecretStr
    """`live_source.authenticated_rtsp_source()` ning chiqishi — REKVIZITLI."""


@dataclass(frozen=True, slots=True)
class DeviceEndpoint:
    """Bitta NVR bilan gaplashish uchun yetarli minimum (ISAPI yo'li uchun).

    `password` — OCHIQ MATN (`decrypt_nvr_password()` ning chiqishi), ya'ni
    bu obyekt jurnalga, `repr()` ga yoki istisno matniga HECH QACHON
    tushmasligi kerak. `discovery.py::_DeviceContext` bilan aynan bir xil
    shakl va bir xil ehtiyot.
    """

    base_url: str
    username: str
    password: str


@dataclass(frozen=True, slots=True)
class CapturedFrame:
    """Bitta muvaffaqiyatli kadr — baytlar, USUL va sarflangan vaqt.

    `method` — DALIL, sozlama emas: u `capture_runs.capture_method` va
    `snapshots.capture_method` ustunlariga tushadi va «qaysi yo'l HAQIQATAN
    ishladi?» savoliga javob beradi (`nvr_devices.capture_method` esa
    «qaysi yo'l so'ralgan edi»). Fallback ishga tushganda ikkalasi FARQ
    qiladi va aynan shu farq dala diagnostikasining birinchi savoli.

    ⚠ `elapsed_ms` KADR OLISHNING narxi, butun slotning emas: sifat
      tahlili va S3 yuklash bu songa KIRMAYDI. Aralashtirilsa «NVR sekin»
      bilan «ombor sekin» bir xil ko'rinardi.
    """

    data: bytes
    method: str
    elapsed_ms: int


class FrameSource(Protocol):
    """Bitta kadr olish usuli — protokolning butun yuzasi IKKI a'zo.

    Yuza ATAYIN tor: har qanday uchinchi a'zo (masalan «oqimni ro'yxatdan
    chiqar» yoki «keshni tozala») usullar orasidagi FARQNI chaqiruvchiga
    olib chiqardi va D-06 ning «tanlov MA'LUMOT, kod emas» da'vosi
    yo'qolardi.
    """

    @property
    def method(self) -> str:
        """`CaptureMethod` a'zosining qiymati — natijaga DALIL bo'lib tushadi."""
        ...

    async def fetch(self, target: CaptureTarget) -> bytes:
        """Kadr baytlarini oladi yoki `FrameSourceError` ko'taradi."""
        ...


class Go2rtcFrameSource:
    """D-06 ning STANDART yo'li: `ensure_stream()` -> `/api/frame.jpeg`.

    ⚠ RO'YXATGA OLISH BIRINCHI. 3-fazada oqim go2rtc'ga LAZY qo'shiladi
      (faqat ko'rish so'ralganda), kadr olish esa jonli ko'rishga bog'liq
      emas — ya'ni ro'yxatga olinmagan oqim uchun `/api/frame.jpeg` `404`
      qaytarardi va nosozlik «kamera oflayn» bo'lib ko'rinardi.

    ⚠ `ensure_stream()` IDEMPOTENT va u allaqachon mavjud oqim uchun
      `PUT` yubormaydi (bitta `GET` narxida). Shuning uchun uni har
      kadrda chaqirish qimmat emas va u D-11 bilan ziddiyatga kirmaydi.
    """

    method = CaptureMethod.GO2RTC.value

    def __init__(self, client: Go2rtcClient, http: httpx.AsyncClient) -> None:
        self._client = client
        self._http = http

    async def fetch(self, target: CaptureTarget) -> bytes:
        await self._register(target)

        try:
            response = await self._http.get(
                FRAME_PATH,
                params=_frame_params(src=target.stream_name),
            )
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            failure = _failure(CAPTURE_TIMEOUT, _reason(exc))
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            failure = _failure(_status_to_code(status), f"status={status}")
        except httpx.HTTPError as exc:
            failure = _failure(CAPTURE_SOURCE_UNREACHABLE, _reason(exc))
        else:
            return response.content

        # ⚠ ISTISNO `except` BLOKIDAN TASHQARIDA (`storage.py::_call` bilan
        #   bir xil nozik qaror): blok tugagach Python istisno kontekstini
        #   tozalaydi, ya'ni `__context__` ham xom istisnoni tashimaydi.
        #   `from None` yolg'iz o'zi faqat `__cause__` ni yopardi.
        raise failure from None

    async def _register(self, target: CaptureTarget) -> None:
        """Oqimni go2rtc'da ro'yxatga oladi — `remove_stream()` juftisiz (D-11)."""
        try:
            await self._client.ensure_stream(target.stream_name, target.rtsp_source)
        except Go2rtcError as exc:
            failure = _failure(CAPTURE_SOURCE_UNREACHABLE, _reason(exc))
        else:
            return
        raise failure from None


def _status_to_code(status: int) -> str:
    """go2rtc ning HTTP statusini kadr olish kodiga aylantiradi.

    ⚠ `404` -> `capture_camera_offline` VA BU FARQ OPERATSION:
      `capture_source_unreachable` adminni tunnel va tarmoqqa yuboradi,
      `capture_camera_offline` esa AYNAN o'sha kameraning quvvati va
      kabeliga. Oqim allaqachon ro'yxatga olingan bo'lgani uchun `404`
      «go2rtc yo'q» degani emas — «bu oqimdan kadr chiqmadi» degani.
    """
    if status == httpx.codes.NOT_FOUND:
        return CAPTURE_CAMERA_OFFLINE
    if status in {httpx.codes.UNAUTHORIZED, httpx.codes.FORBIDDEN}:
        return CAPTURE_BAD_CREDENTIALS
    return CAPTURE_SOURCE_UNREACHABLE


class IsapiFrameSource:
    """D-07 ning yo'li: NVR'dan JPEG to'g'ridan-to'g'ri, NOL RTSP sessiyasi.

    ⚠ KLIENT SHU OBYEKTGA BOG'LANGAN va u BATCH davomida bitta: rekvizit
      NVR ga tegishli, ya'ni klientni kamera bo'yicha qayta ochish har
      kadr uchun yangi Digest handshake (ortiqcha `401`) berardi.
    """

    method = CaptureMethod.ISAPI.value

    def __init__(self, client: IsapiClient) -> None:
        self._client = client

    async def fetch(self, target: CaptureTarget) -> bytes:
        try:
            return await self._client.fetch_picture(target.channel_no, target.stream)
        except NvrError as error:
            # ⚠ `error.detail` UZATILMAYDI: u ISAPI ning XOM javobini
            #   (`_snippet`) tashiydi va u yerda rekvizit qoldig'i
            #   bo'lishi mumkin. Kod va uning ISAPI dagi manbai yetadi.
            failure = _failure(ISAPI_TO_CAPTURE[error.code], f"isapi={error.code}")
        raise failure from None


class FfmpegFrameSource:
    """D-06 ning OXIRGI CHORASI: bir martalik RTSP handshake.

    ⚠ SHELL ISHLATILMAYDI va argumentlar RO'YXAT sifatida uzatiladi
      (T-04-56). Parolni ADMIN kiritadi, ya'ni u ishonchsiz kirish:
      shell qatlami undagi `;`, `$` yoki backtick belgilarini buyruqqa
      aylantirardi.

    ⚠ `stderr` UMUMAN O'QILMAYDI (`DEVNULL`). `ffmpeg` birinchi qatorda
      to'liq kirish URL'ini — ya'ni parolni — chop etadi. Uni «faqat
      diagnostika uchun» ushlash o'sha satrni istisno matniga, jurnalga
      va Sentry'ga olib chiqardi. Sirni USHLAMASLIK uni maskalashdan
      ishonchliroq.
    """

    method = CaptureMethod.FFMPEG.value

    async def fetch(self, target: CaptureTarget) -> bytes:
        argv = (
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            # TCP: UDP ustidagi RTSP tunnel ortida paket yo'qotadi va
            # yarim kadr `corrupt` bo'lib yozilardi.
            "-rtsp_transport",
            "tcp",
            "-i",
            # OCHIQ QIYMATGA BORISH SHU YERDA VA BOSHQA HECH QAYERDA
            # (`go2rtc.py:293-296` va `storage.py:417-421` bilan bir xil
            # qoida): u ATAYIN ko'rinadigan, grep bilan topiladigan BITTA
            # qadam va argumentga uzatilishidan BEVOSITA oldin turadi.
            # ⚠ Sanoq darvozasi shu fayldagi chaqiruvlarni SANAYDI, ya'ni
            #   izohda uning literal shaklini takrorlash darvozani
            #   yolg'on-qizil qilardi.
            target.rtsp_source.get_secret_value(),
            "-frames:v",
            "1",
            "-q:v",
            "2",
            "-f",
            "image2",
            "pipe:1",
        )

        try:
            process = await asyncio.create_subprocess_exec(
                *argv,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
        except OSError as exc:
            # `ffmpeg` image'da yo'q yoki ijro etilmaydi. Bu PLATFORMA
            # nosozligi, lekin taksonomiyada unga alohida kod yo'q va
            # yangi kod qo'shish reyestrni bu reja doirasidan tashqarida
            # o'zgartirardi — sabab `detail` da nomlanadi.
            failure = _failure(CAPTURE_SOURCE_UNREACHABLE, f"ffmpeg:{_reason(exc)}")
            raise failure from None

        # ⚠ `FFMPEG_TIMEOUT_SECONDS` MODUL GLOBALIDAN CHAQIRUV PAYTIDA
        #   o'qiladi (konstruktorda ushlanmaydi): aks holda uni test ham,
        #   kelajakdagi sozlama ham almashtira olmasdi.
        try:
            stdout, _ = await asyncio.wait_for(
                process.communicate(), timeout=FFMPEG_TIMEOUT_SECONDS
            )
        except TimeoutError:
            _kill(process)
            # ⚠ `wait()` MAJBURIY: `kill()` dan keyin `wait()` chaqirilmasa
            #   bola jarayon ZOMBI bo'lib qoladi va ular worker
            #   konteynerida kunlik 175 slot bo'yicha to'planardi.
            await process.wait()
            failure = _failure(CAPTURE_TIMEOUT, f"ffmpeg:{FFMPEG_TIMEOUT_SECONDS}s")
        else:
            if process.returncode == 0:
                return stdout
            failure = _failure(CAPTURE_SOURCE_UNREACHABLE, f"ffmpeg:exit={process.returncode}")

        raise failure from None


def _kill(process: asyncio.subprocess.Process) -> None:
    """Jarayonni o'ldiradi; u allaqachon tugagan bo'lsa JIM qoladi.

    `ProcessLookupError` bu yerda XATO EMAS: `wait_for` ning timeout'i va
    jarayonning o'z tugashi bir vaqtda yuz berishi mumkin, va o'shanda
    `kill()` bo'sh PID ga borardi.
    """
    try:
        process.kill()
    except ProcessLookupError:  # pragma: no cover - poyga oynasi
        log.debug("ffmpeg_already_exited")


class FrameSourcePool:
    """Worker jarayonining kadr olish resurslari — BIR MARTA ochiladi.

    Egalik shakli `worker.py:181-207` (`engine`) bilan bir xil: obyekt
    `WORKER_STARTUP` da quriladi, `TaskiqState` da yashaydi va
    `WORKER_SHUTDOWN` da yopiladi. Modul docstringining 2-majburiyati bu
    tanlovning sababini `go2rtc.py` ning qarama-qarshi izohi bilan
    solishtirib yozadi.

    ⚠ `Settings` BU YERDA O'QILMAYDI — manzil ARGUMENT sifatida keladi
      (`worker.py:26-41` ning qoidasi: modul darajasidagi qurilish to'liq
      muhitni talab qilmasligi kerak).
    """

    def __init__(self, *, go2rtc_url: str, frame_timeout: float | None = None) -> None:
        self._exit = AsyncExitStack()

        self._go2rtc_client = Go2rtcClient(go2rtc_url)
        self._exit.push_async_exit(self._go2rtc_client)

        self._http = httpx.AsyncClient(
            base_url=go2rtc_url,
            timeout=FRAME_TIMEOUT_SECONDS if frame_timeout is None else frame_timeout,
        )
        self._exit.push_async_callback(self._http.aclose)

        self._go2rtc = Go2rtcFrameSource(self._go2rtc_client, self._http)
        self._ffmpeg = FfmpegFrameSource()

    @asynccontextmanager
    async def for_device(self, device: DeviceEndpoint) -> AsyncIterator[Mapping[str, FrameSource]]:
        """Bitta NVR uchun uchala usulni beradi; ISAPI klienti blok oxirida yopiladi.

        ⚠ ISAPI KLIENTI BLOK BO'YICHA, JARAYON BO'YICHA EMAS: uning
          rekviziti NVR ga tegishli va u bazadan har batchda qayta
          o'qiladi (parol o'zgarganda eski klient uni jimgina ishlatib
          yurardi). go2rtc va ffmpeg manbalari esa jarayon bo'yicha —
          ularda NVR ga bog'liq holat yo'q.
        """
        async with IsapiClient(device.base_url, device.username, device.password) as isapi:
            yield {
                CaptureMethod.GO2RTC.value: self._go2rtc,
                CaptureMethod.ISAPI.value: IsapiFrameSource(isapi),
                CaptureMethod.FFMPEG.value: self._ffmpeg,
            }

    async def aclose(self) -> None:
        """Barcha resurslarni teskari tartibda yopadi (`lifespan` ning `finally` jufti)."""
        await self._exit.aclose()


async def capture_frame(
    sources: Mapping[str, FrameSource],
    target: CaptureTarget,
    *,
    method: str,
) -> CapturedFrame:
    """Tanlangan usul bilan BITTA kadr oladi va natijani NATIJADAN o'lchaydi.

    Args:
        sources: `FrameSourcePool.for_device()` bergan uchta manba.
        target: kamera qatoridan olingan qiymatlar.
        method: `nvr_devices.capture_method` — BAZADAN kelgan satr.

    Returns:
        `CapturedFrame` — baytlar HAQIQATAN JPEG ekani tekshirilgan.

    Raises:
        ValueError: `UNKNOWN_CAPTURE_METHOD` matni bilan. Bazadagi `CHECK`
            konstraytining IKKINCHI qatlami: migratsiya bilan kod ajralib
            ketishi mumkin (yangi qiymat CHECK'ga qo'shilib, bu yerda
            unutilishi) va o'shanda tanlov JIMGINA standart yo'lga tushib
            ketardi — dala diagnostikasi «qaysi yo'l ishladi?» savoliga
            noto'g'ri javob berardi.
        FrameSourceError: tanilgan har qanday rad etish sababi bilan.
    """
    if method not in CAPTURE_METHOD_VALUES:
        raise ValueError(
            f"{UNKNOWN_CAPTURE_METHOD}: {method!r}. Ruxsat etilganlar: "
            f"{list(CAPTURE_METHOD_VALUES)} (`sbozor_core.enums.CaptureMethod`)."
        )
    source = sources.get(method)
    if source is None:
        raise ValueError(
            f"{UNKNOWN_CAPTURE_METHOD}: {method!r} manbalar to'plamida yo'q "
            f"({sorted(sources)}). `FrameSourcePool.for_device()` uchalasini beradi."
        )

    started = time.monotonic()
    data = await source.fetch(target)
    elapsed_ms = int((time.monotonic() - started) * 1000)

    # =====================================================================
    # ⚠⚠ MUVAFFAQIYAT NATIJADAN O'LCHANADI — MODUL DOCSTRINGINING
    #    5-MAJBURIYATI VA U UCHALA USUL UCHUN AYNAN SHU YERDA.
    #
    # `Content-Type` sarlavhasi ham, HTTP statusi ham yolg'on gapirishi
    # mumkin: NVR yoki go2rtc xato holatida HTML sahifa qaytaradi, ba'zi
    # proxy va firmware esa sarlavhani `image/jpeg` qoldirib yuboradi
    # (T-04-25/T-04-53). Sarlavhaga ishonadigan filtr o'sha sahifani
    # YAROQLI BILLING KADRI sifatida saqlardi.
    # =====================================================================
    if not data.startswith(JPEG_MAGIC):
        raise _failure(
            CAPTURE_INVALID_RESPONSE,
            f"{method}: javob JPEG emas ({len(data)} bayt)",
        ) from None

    return CapturedFrame(data=data, method=method, elapsed_ms=elapsed_ms)
