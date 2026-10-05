"""go2rtc klienti va uning `src` ALLOW-LISTI (D-11, T-03-45).

=============================================================================
⚠⚠ BU FAYLDAGI ALLOW-LIST — RCE GA QARSHI DARVOZA. UNI YUMSHATMANG.

Frigate loyihasidagi xavfsizlik ogohnomasi AYNAN shu naqshga tegishli:

    "Authenticated Admin Can Achieve RCE via go2rtc Stream API —
     `exec:` Filter Not Enforced at API Layer"
    GHSA-wwww-5h25-jf98 · CVSS 9.1 Critical

Ular `PUT /api/go2rtc/streams/{name}` ning `src` parametrini go2rtc'ga
FILTRSIZ uzatgan. go2rtc esa `exec:` protokolini qo'llab-quvvatlaydi —
ya'ni `src` IXTIYORIY TIZIM BUYRUG'INI oqim manbai sifatida ro'yxatga
olishi mumkin. Natija: IKKITA HTTP so'rovi bilan konteyner ichida root
sifatida kod ijrosi.

`exec:` dan tashqari `ffmpeg:`, `echo:` va boshqa protokollar ham bor.
Shuning uchun darvoza QORA RO'YXAT EMAS, ALLOW-LIST: faqat `rtsp://`
bilan boshlanuvchi manba o'tadi va qolganining hammasi rad etiladi.
Qora ro'yxat har yangi protokolda eskirardi.

⚠ Keyingi tahrirlovchiga: bu cheklovni «qulaylik uchun» (masalan HTTP
  snapshot manbai yoki fayl testi uchun) kengaytirish taklifi kelsa —
  javob YO'Q. Manba HECH QACHON foydalanuvchi kiritmasidan qurilmaydi;
  u `app/services/rtsp.py::rtsp_url()` ning CHIQISHI, ya'ni bizning
  o'z kodimiz hosil qilgan satr. Allow-list o'sha faktni MAJBURLAYDI.
=============================================================================

=============================================================================
UCH QATLAM — VA UCHALASI HAM KERAK (T-03-45).

  1. go2rtc ning API porti (1984) XOST PORTIGA PUBLISH QILINMAYDI
     (`compose.yaml`) va konfiguratsiyada ichki interfeysga bog'lanadi;
  2. nginx `/api/streams`, `/api/config`, `/api/restart` yo'llarini
     `return 403` bilan bloklaydi (`ops/nginx/nginx.conf`);
  3. SHU FAYLDAGI allow-list — `core-api` ning O'ZI ham xavfli `src`
     yubora olmaydi.

Uchtasi bir-birini almashtira olmaydi: (1) va (2) TASHQI hujumchini
to'xtatadi, (3) esa ICHKI xatoni — masalan kelajakda kimdir `src` ni
so'rov tanasidan olsa. Qatlamlardan birini «ortiqcha» deb olib tashlash
qolgan ikkitasini bitta xatodan narida qoldiradi.
=============================================================================

DB — YAGONA HAQIQAT MANBAI, go2rtc KONFIGURATSIYASI ESA HOSILA.

`PATCH /api/config` bilan YAML'ga yozish ATAYIN RAD ETILDI (RESEARCH
D.13): u ikkinchi haqiqat manbaini tug'dirardi (baza bilan fayl drift
qiladi) va `exec:` YOZISH yuzasini kengaytirardi. Oqimlar XOTIRAGA,
ish paytida qo'shiladi (`PUT /api/streams`); go2rtc qayta ishga tushsa
ular yo'qoladi va keyingi ko'rish so'rovi ularni QAYTA qo'shadi —
ro'yxatga olish LAZY va shuning uchun startup'da 25 ta so'rov yo'q.
"""

from __future__ import annotations

from types import TracebackType
from typing import Self

import httpx
import structlog
from pydantic import SecretStr

__all__ = [
    "GO2RTC_STREAMS_PATH",
    "LIVE_VIEW_PATH",
    "TRANSPORT_HINT",
    "Go2rtcClient",
    "Go2rtcError",
    "UNSAFE_SOURCE",
    "assert_safe_go2rtc_src",
    "live_view_url",
]

log = structlog.get_logger(__name__)

_ALLOWED_STREAM_SCHEME = "rtsp://"
"""YAGONA ruxsat etilgan manba sxemasi.

Prefiks AYNAN shu holda solishtiriladi — `strip()`, `lstrip()`,
`lower()` yoki `casefold()` QO'LLANMAYDI va bu ataylab:

  * `" rtsp://..."` (bosh bo'shliq bilan) go2rtc tomonida qanday
    talqin qilinishi BIZGA NOMA'LUM — ya'ni normalizatsiya qilib
    o'tkazish «biz bilamiz» degan asossiz da'vo bo'lardi;
  * har qanday normalizatsiya qadami darvoza bilan iste'molchi
    o'rtasida FARQ tug'diradi va aynan shu farqda chetlab o'tish yo'li
    yashaydi (ASVS V5.3 — «kanonizatsiya tekshiruvdan OLDIN, bir
    marta»).

Bizning `src` imiz `rtsp_url()` ning chiqishi, ya'ni u hech qachon
bo'shliq bilan boshlanmaydi. Bo'shliqli qiymat kelishi — KODDA XATO
borligining belgisi va u jimgina tuzatilmasligi kerak.
"""

UNSAFE_SOURCE = "unsafe_go2rtc_source"
"""`ValueError` ning matni — testda ham, jurnalda ham AYNAN shu satr."""

GO2RTC_STREAMS_PATH = "/api/streams"
"""go2rtc ning oqimlar API'si.

⚠ SHU SATR nginx'da `return 403` bilan bloklanadi. Ikkalasi bir xil
  qiymatda qolishi kerak va buni `tests/unit/test_go2rtc_client.py::
  test_nginx_blocks_the_go2rtc_api_paths` konfiguratsiya faylini o'qib
  tekshiradi — konstanta va konfiguratsiya jimgina ajralib ketmasin.
"""

_TIMEOUT_SECONDS = 5.0
"""go2rtc bilan muloqot chegarasi.

⚠ CHEGARA MAJBURIY va u so'rov ICHIDAGI yo'lda: `POST /live-token`
  go2rtc'ga boradi va `uvicorn --workers 1` ostida osilgan chaqiruv
  BUTUN API'ni bloklardi (T-03-42 ning boshqa yo'ldan takrori; 03-06
  navbat yo'lida aynan shu sabab bilan `asyncio.timeout` qo'ygan).
  go2rtc compose tarmog'ida turadi, ya'ni 5 soniya juda saxiy chegara.
"""


class Go2rtcError(RuntimeError):
    """go2rtc javob bermadi yoki xato status qaytardi.

    `httpx` istisnolaridan ALOHIDA sinf: chaqiruvchi (marshrut) uni
    500 emas, TUSHUNARLI xatoga aylantirishi kerak — «jonli ko'rish
    hozir ishlamayapti» admin uchun «ichki xato» dan ancha foydali
    (D-02).

    ⚠ MATNIGA `httpx` ISTISNOSI INTERPOLYATSIYA QILINMAYDI (T-03-87).
      Sabab `_failure()` docstringida.
    """

    def __init__(self, message: str, agent_reason: str | None = None) -> None:
        super().__init__(message)
        self.agent_reason = agent_reason
        """CamAgent yo'lida AGENT aytgan sabab (261005).

        ⛔ NEGA YANGI XATO TURI OCHILMADI: `cameras.py` dagi izoh buni
           ataylab rad etgan — yangi tur UI'da yangi holat talab qilardi,
           operator uchun esa sabab bir xil («jonli ko'rish ishlamayapti»).
           O'sha qaror KUCHDA: bu maydon yangi HOLAT emas, mavjud
           holatning IZOHI. UI uni asosiy xabar OSTIDA ko'rsatadi.

        ⚠ `None` — to'g'ridan-to'g'ri NVR yo'lida har doim, CamAgent
          yo'lida esa gateway hali sabab bilmaganda.
        """


def _failure(method: str, exc: httpx.HTTPError) -> Go2rtcError:
    """`httpx` istisnosini SIRSIZ `Go2rtcError` ga aylantiradi (T-03-87).

    =========================================================================
    ⚠⚠ `{exc}` INTERPOLYATSIYASI — HAQIQIY OQISH YO'LI EDI.

    `httpx.HTTPStatusError` ning matni TO'LIQ so'rov URL'ini o'z ichiga
    oladi::

        Client error '400 Bad Request' for url
        'http://go2rtc:1984/api/streams?name=cam_...&src=rtsp://admin:PAROL@...'

    `PUT /api/streams` ning `src` i esa REKVIZITLI manba. Ya'ni eski
    xabar parolni `Go2rtcError` ga, u yerdan `api/v1/cameras.py` dagi
    `log.warning(..., error=str(exc))` orqali JURNALGA, jurnaldan esa
    Sentry'ga olib chiqardi (D-12 ning bevosita buzilishi).

    Diagnostika uchun UCHTA fakt yetadi va uchalasi ham sirsiz: qaysi
    AMAL, qaysi XATO TURI, qaysi STATUS. «Qaysi oqim» savoliga
    `go2rtc_stream_registered` / chaqiruvchining jurnal qatori javob
    beradi — u `stream_name` ni yozadi, `src` ni emas.
    =========================================================================
    """
    status = exc.response.status_code if isinstance(exc, httpx.HTTPStatusError) else None
    detail = f"status={status}" if status is not None else "javob yo'q"
    return Go2rtcError(
        f"go2rtc `{method} {GO2RTC_STREAMS_PATH}` yiqildi: {type(exc).__name__} ({detail})"
    )


def assert_safe_go2rtc_src(src: str) -> None:
    """`src` FAQAT `rtsp://` bilan boshlanishi mumkin — aks holda `ValueError`.

    Bu funksiya go2rtc'ga boradigan HAR BIR `src` ning yagona darvozasi.
    Sabab va tahdid modeli modul docstringida (GHSA-wwww-5h25-jf98,
    CVSS 9.1): `exec:` va `ffmpeg:` protokollari ixtiyoriy tizim
    buyrug'ini oqim manbai qiladi.

    Args:
        src: go2rtc uchun oqim manbai.

    Raises:
        ValueError: `UNSAFE_SOURCE` matni bilan. Xato TURI ataylab
            oddiy `ValueError`: chaqiruvchi uni 500 ga aylantirishi
            KERAK — bunday qiymat mahsulot yo'lidan hech qachon
            kelmaydi va u kelishi KODDAGI xatoni bildiradi, mijoz
            xatosini emas.
    """
    if not src.startswith(_ALLOWED_STREAM_SCHEME):
        # ⚠ XATO MATNIGA `src` NING O'ZI YOZILMAYDI. Rad etilgan qiymat
        #   ta'rifi bo'yicha ishonchsiz kirish va uni jurnalga yozish
        #   log injection yuzasini ochardi; sxema prefiksi esa
        #   diagnostika uchun yetarli.
        log.error("unsafe_go2rtc_source_rejected", scheme=src.split(":", 1)[0][:16])
        raise ValueError(UNSAFE_SOURCE)


class Go2rtcClient:
    """`httpx.AsyncClient` ustidagi YUPQA qobiq — uchta amal, boshqa hech nima.

    ⚠ `PATCH /api/config` VA `POST /api/restart` UMUMAN YO'Q. Ular
      «kerak bo'lib qolsa» qo'shiladigan qulayliklar emas: birinchisi
      ikkinchi haqiqat manbaini tug'diradi (modul docstringi),
      ikkinchisi esa BOSHQA bozorlarning ko'rishini uzardi. Metodning
      yo'qligi — kelishuv emas, STRUKTURA.

    Klient `app.state` da SAQLANMAYDI: u `async with` bilan qisqa
    muddatga ochiladi. Sabab — go2rtc bilan muloqot juda siyrak (kunlik
    bir necha ko'rish so'rovi), doimiy pul esa uzilgan ulanishlarni
    kuzatishni talab qilardi.
    """

    def __init__(self, base_url: str, *, timeout: float = _TIMEOUT_SECONDS) -> None:
        self._client = httpx.AsyncClient(base_url=base_url, timeout=timeout)

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self._client.aclose()

    async def has_stream(self, stream_name: str) -> bool:
        """Oqim go2rtc'da ALLAQACHON ro'yxatga olinganmi.

        `GET /api/streams` BUTUN ro'yxatni beradi. Bitta oqimni so'rash
        (`?src=<nom>`) ham mumkin, lekin javob shakli go2rtc versiyasiga
        bog'liq va yo'q oqim uchun 404 emas, bo'sh obyekt qaytishi
        mumkin — ro'yxat esa bir xil shaklda qoladi.

        ⚠⚠ JAVOB TANASI JURNALGA YOZILMAYDI VA BU TALAB, KUZATUV EMAS
          (T-03-90). Ro'yxat BARCHA bozorlarning oqimlarini, ya'ni
          ularning REKVIZITLI `src` larini qaytaradi — bitta
          `log.debug(payload=...)` butun o'rnatmaning NVR parollarini
          bitta satrga chiqarardi. Xato yo'lida ham shu qoida amal
          qiladi: `_failure()` javob tanasiga umuman tegmaydi.
        """
        try:
            response = await self._client.get(GO2RTC_STREAMS_PATH)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise _failure("GET", exc) from exc

        payload = response.json()
        return isinstance(payload, dict) and stream_name in payload

    async def ensure_stream(self, stream_name: str, src: SecretStr) -> bool:
        """Oqim yo'q bo'lsa qo'shadi (LAZY ro'yxatga olish, RESEARCH D.13).

        ⚠ `src` — `SecretStr`, ODDIY `str` EMAS. `PUT /api/streams` ning
          `src` i REKVIZITLI manba (`live_source.authenticated_rtsp_source`
          ning chiqishi), ya'ni u sir. Sir tashuvchi tip `repr()` orqali
          sizishni STRUKTURAVIY ravishda yopadi (`03-04` standarti).

        ⚠ ALLOW-LIST OCHILGAN QIYMAT USTIDA ISHLAYDI va u `SecretStr`
          ortiga YASHIRINMAYDI: «bu sir, demak bizniki» degan mulohaza
          bilan tekshiruvni tushirib qoldirish aynan GHSA-wwww-5h25-jf98
          (CVSS 9.1) ning yo'li bo'lardi. Rekvizitli manba ham `rtsp://`
          bilan boshlanadi, ya'ni darvoza buzilmaydi.

        =====================================================================
        ⚠⚠ MUVAFFAQIYAT STATUS KODIDAN EMAS, NATIJADAN O'LCHANADI.

        go2rtc `PUT /api/streams` ni IKKI QADAMDA bajaradi: avval oqimni
        XOTIRAGA qo'shadi, keyin uni `/config/go2rtc.yaml` ga YOZIB
        QO'YMOQCHI bo'ladi. Bizda o'sha fayl `:ro` mount qilingan (D-11 —
        `exec:` ning konfiguratsiyaga muhrlanishiga qarshi qatlam), ya'ni
        ikkinchi qadam HAR DOIM yiqiladi va go2rtc **400** qaytaradi.
        Oqim esa RO'YXATDA BO'LADI.

        O'lchandi (2026-08-03, 03-14): `PUT` -> `400
        "yaml: ... did not find expected key"`, keyin `GET /api/streams`
        -> oqim BOR, `/api/frame.jpeg` -> 99 681 baytli JPEG.

        Ya'ni `raise_for_status()` ga so'zsiz ishonish jonli ko'rishni
        ISHLAB TURGAN holatda 503 qilardi — bu nosozlikni `go2rtc_calls`
        mock'i yashirgan edi va uni birinchi MOCK'SIZ o'lchov (03-14)
        ochdi. Shuning uchun `PUT` yiqilganda ro'yxat QAYTA O'QILADI:
        oqim bor bo'lsa amal bajarilgan, yo'q bo'lsa — HAQIQIY nosozlik.

        Bu allow-listni ham, D-11 ni ham YUMSHATMAYDI: konfiguratsiyaga
        yozish baribir bajarilmaydi va bu ATAYIN — oqimlar xotirada
        yashaydi (modul docstringi).
        =====================================================================

        Returns:
            `True` — oqim SHU chaqiruvda qo'shildi; `False` — allaqachon
            bor edi. Qaytish qiymati testga «`PUT` HAQIQATAN yuborildimi»
            savoliga javob beradi (natijadan o'lchab bo'lmaydi: ikkala
            holatda ham oxirida oqim MAVJUD bo'ladi).

        Raises:
            ValueError: `src` allow-listdan o'tmasa.
            Go2rtcError: go2rtc javob bermasa YOKI `PUT` dan keyin oqim
                ro'yxatda paydo bo'lmasa.
        """
        # `get_secret_value()` SHU YERDA VA BOSHQA HECH QAYERDA (03-04
        # dagi `nvr_cipher()` bilan bir xil qoida): ochiq qiymatga borish
        # ATAYIN ko'rinadigan, grep bilan topiladigan BITTA qadam.
        source = src.get_secret_value()

        # ⚠ DARVOZA ENG BOSHIDA — tarmoqqa chiqishdan OLDIN. Keyin
        #   tekshirilsa xavfli qiymat allaqachon go2rtc'ga yuborilgan
        #   bo'lardi (T-03-37 dagi «chegara qurilmaga borishdan oldin»
        #   bilan aynan bir xil mulohaza).
        assert_safe_go2rtc_src(source)

        if await self.has_stream(stream_name):
            return False

        put_failure: Go2rtcError | None = None
        try:
            response = await self._client.put(
                GO2RTC_STREAMS_PATH,
                params={"name": stream_name, "src": source},
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            # ⚠⚠ ISTISNO SHU YERDA KO'TARILMAYDI — u faqat SIRSIZ shaklga
            #   o'giriladi va blokdan TASHQARIDA hal qilinadi. Sabab
            #   nozik: `except` ichida `await self._registered(...)`
            #   chaqirilsa va u o'z navbatida ko'tarilsa, yangi
            #   istisnoning `__context__` i AYNAN shu `httpx` istisnosi
            #   bo'lardi — uning matni esa `?src=rtsp://admin:PAROL@...`
            #   ni to'liq tashiydi (T-03-87 ning qayta ochilishi).
            put_failure = _failure("PUT", exc)

        if put_failure is not None:
            # ⚠ `from None` — VA U `has_stream` DAN ATAYIN FARQ QILADI.
            #   SHU chaqiruvning URL'ida sir bor, ya'ni `httpx` istisnosi
            #   `__cause__` da qolsa `traceback`, Sentry ning zanjir
            #   yuruvchisi va har qanday `format_exc()` uni chop etardi.
            #   Yo'qotilgan narsa faqat httpx ning O'Z matni; qaysi amal,
            #   qaysi xato TURI va qaysi STATUS `_failure()` da saqlanadi.
            if await self._registered(stream_name) is not True:
                raise put_failure from None
            # Konfiguratsiyaga yozib bo'lmadi (`:ro`, D-11), oqim esa
            # xotirada ro'yxatga OLINDI — bu KUTILGAN holat, nosozlik emas.
            log.info("go2rtc_stream_not_persisted", stream_name=stream_name)

        log.info("go2rtc_stream_registered", stream_name=stream_name)
        return True

    async def _registered(self, stream_name: str) -> bool | None:
        """`has_stream`, LEKIN O'Z xatosini yutadi: `None` = «ayta olmadim».

        Uch holatli javob ATAYIN. Chaqiruvchi `PUT`/`DELETE` ning
        natijasini shu yerdan o'lchaydi va «tekshira olmadim» ni
        «hammasi joyida» deb talqin qilishi MUMKIN EMAS — ikkalasi ham
        FAIL-CLOSED yo'nalishda hal qilinadi.
        """
        try:
            return await self.has_stream(stream_name)
        except Go2rtcError:
            # Sabab yuqoridagi chaqiruvda allaqachon `Go2rtcError` shakliga
            # o'girilgan va u sirsiz; bu yerda uni QAYTA ko'tarish asosiy
            # nosozlik xabarini (`PUT`/`DELETE` yiqildi) yashirardi.
            return None

    async def remove_stream(self, stream_name: str) -> None:
        """Oqimni ro'yxatdan chiqaradi (arxivlangan kamera uchun).

        ⚠ Bu amal go2rtc'ni QAYTA ISHGA TUSHIRMAYDI va boshqa
          oqimlarga tegmaydi.

        ⚠ `ensure_stream` BILAN BIR XIL SABABGA KO'RA natijadan
          o'lchanadi: `DELETE` ham konfiguratsiyani qayta yozmoqchi
          bo'ladi va `:ro` mount ostida **400** oladi
          (`open /config/go2rtc.yaml: read-only file system` — o'lchandi
          2026-08-03), oqim esa ro'yxatdan CHIQADI.

        Raises:
            Go2rtcError: go2rtc javob bermasa YOKI `DELETE` dan keyin oqim
                ro'yxatda QOLGAN bo'lsa.
        """
        delete_failure: Go2rtcError | None = None
        delete_cause: httpx.HTTPError | None = None
        try:
            response = await self._client.delete(
                GO2RTC_STREAMS_PATH,
                params={"src": stream_name},
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            delete_failure = _failure("DELETE", exc)
            delete_cause = exc

        if delete_failure is not None:
            # ⚠ `from delete_cause` — `ensure_stream` DAN FARQLI. Bu
            #   chaqiruvning URL'ida sir YO'Q (`?src=cam_<uuid4>`), ya'ni
            #   sabab zanjirini bostirish diagnostikani sababsiz
            #   yo'qotardi. Farq atayin va u shu izohda yozilgan.
            if await self._registered(stream_name) is not False:
                raise delete_failure from delete_cause
            log.info("go2rtc_removal_not_persisted", stream_name=stream_name)

        log.info("go2rtc_stream_removed", stream_name=stream_name)


LIVE_VIEW_PATH = "/live/api/ws"
"""Brauzer boradigan YAGONA jonli ko'rish yo'li.

go2rtc ning `/api/ws` endpointi WebRTC ham, MSE ham SHU YO'L orqali
signalling qiladi (`video-stream` veb-komponenti transportni O'ZI
tanlaydi: WebRTC -> MSE -> HLS). Ya'ni UI uchun bitta manzil yetadi va
transport tanlovi mijoz tomonda qoladi.

⚠ `/live/` PREFIKSI MAJBURIY: nginx aynan shu prefiks ostidagi
  so'rovlarga `auth_request` qo'yadi (`ops/nginx/nginx.conf`). Prefikssiz
  manzil go2rtc'ga UMUMAN yetib bormaydi (port publish qilinmagan), ya'ni
  xato "avtorizatsiyasiz o'tib ketdi" emas, "umuman ishlamadi" bo'lib
  ko'rinadi — bu to'g'ri fail-closed yo'nalish.
"""

TRANSPORT_HINT = "webrtc"
"""UI ning badge'i uchun BOSHLANG'ICH qiymat (UI-SPEC §8.4).

Bu majburlash EMAS: go2rtc ning komponenti transportni o'zi tanlaydi va
UI badge'ni HAQIQIY transport bilan almashtiradi. Maslahat faqat
birinchi renderda "noma'lum" ko'rsatmaslik uchun.
"""


def live_view_url(stream_name: str, token: str) -> str:
    """Brauzerga beriladigan OPAQUE jonli ko'rish manzili.

    ⚠ `stream_name` URL ICHIDA, JAVOBNING ALOHIDA MAYDONIDA EMAS
      (UI-SPEC §8.7). Farq amaliy: alohida maydon UI'da ko'rsatiladi va
      nusxa olinadi, URL ichidagi qiymat esa `<video src=...>` ga
      to'g'ridan-to'g'ri beriladi va ekranga chiqmaydi.

    ⚠ QUERY QO'LDA YIG'ILADI, `urlencode` BILAN EMAS — va bu ataylab:
      ikkala qiymat ham BIZNING kodimiz hosil qilgan (`cam_<uuid4>` va
      base64url JWT), ya'ni ularda kodlash talab qiladigan belgi YO'Q.
      `urlencode` qo'shilsa u `.` va `-` ni qoldiradi, ya'ni natija bir
      xil bo'lardi — lekin o'quvchida "bu yerda foydalanuvchi kiritmasi
      bor" degan noto'g'ri taassurot qolardi.
    """
    return f"{LIVE_VIEW_PATH}?src={stream_name}&t={token}"
