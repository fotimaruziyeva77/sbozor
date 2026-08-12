"""Telegram jo'natuvchisi — YUPQA, SIRSIZ va BLOKLAMAYDIGAN (FOUND-06, D-19).

=============================================================================
⛔⛔ 1-TAQIQ — ALERTGA KADR RASMI HECH QACHON BIRIKTIRILMAYDI (D-19).

Rasm biriktiruvchi Telegram metodi bu faylda UMUMAN YOZILMAYDI va u
«hozircha kerak emas» degani EMAS. Sabab ikki qatlamli va ikkalasi ham
huquqiy:

  1. DALIL-KADRLAR — SHAXSIY MA'LUMOT. Kadrda bozor tashrifchilari,
     sotuvchilar va ularning yuzlari bo'ladi. Ular O'zR ning shaxsiy
     ma'lumotlar to'g'risidagi qonuni ostida va loyiha ularni saqlash
     uchun aniq majburiyat olgan.

  2. TELEGRAM SERVERLARI — CHEGARADAN TASHQARIDA. Loyiha zimmasiga olgan
     data-rezidentlik chegarasi O'zbekiston bilan chegaralanadi
     (PROJECT.md: «davlat bosqichidan oldin O'zbekiston hostingiga
     ko'chish»). Telegram'ga yuborilgan har bir bayt o'sha chegaradan
     CHIQADI va uni QAYTARIB BO'LMAYDI — o'chirilgan xabar ham
     serverlarda qolishi mumkin.

Ya'ni kadr biriktirish «xavfsizlik sozlamasi» emas: u bir marta yozilsa,
u yozilgan kundan boshlab qaytarib bo'lmaydigan sizish yo'li bo'lardi.

Shuning uchun himoya KELISHUV emas, STRUKTURA — uslub namunasi
`sbozor_core/security.py:6-11` va `go2rtc.py:193-197` («Metodning
yo'qligi — kelishuv emas, STRUKTURA»). `AlertSender` da AYNAN BITTA metod
bor va u faqat matn yuboradi. Bu faylning butun yuzasini `dir()` bilan
sanab chiqadigan darvoza `tests/integration/test_alerting.py` da turadi va
u `alert_events` jadvalining tegishli ustuni yo'qligi bilan juftlashgan
(`snapshot.py::AlertEvent` — `snapshot_id` ustuni ham ATAYIN yo'q).

⚠ Frontend tomonidagi jufti — `04-UI-SPEC.md` ning G-3 darvozasi: alert
  komponentlarida `<img>` TAQIQLANGAN. Backend va frontend bir xil
  qoidani IKKI mustaqil mexanizm bilan majburlaydi.
=============================================================================

=============================================================================
⛔ 2-TAQIQ — BOT TOKENI URL'NING BIR QISMI, YA'NI ISTISNO MATNI UNI TASHIYDI.

Telegram Bot API ning shakli:

    POST https://api.telegram.org/bot<SIR>/sendMessage
                                  ^^^^^^^ maxfiy qiymat AYNAN shu yerda

`httpx.HTTPStatusError` ning matni TO'LIQ so'rov URL'ini o'z ichiga oladi,
ya'ni `f"... {exc}"` shaklidagi bitta interpolyatsiya sirni `AlertError`
ga, u yerdan jurnalga va jurnaldan Sentry'ga olib chiqardi. Bu 3-fazada
`go2rtc.py:133-160` da HAQIQATAN sodir bo'lgan yo'lning aynan takrori,
faqat boshqa protokolda.

Shuning uchun `_failure()` MAJBURIY va u faqat UCH faktni beradi: qaysi
AMAL, qaysi XATO TURI, qaysi STATUS. Uchalasi ham sirsiz va uchalasi ham
diagnostika uchun yetarli.

⚠ IKKINCHI QATLAM: maxfiy qiymatga ochiq holda borish AYNAN BITTA joyda —
  URL qurilishidan bevosita oldin. Sanoq darvozasi buni matn ustida
  o'lchaydi.

⚠ UCHINCHI QATLAM: `SENSITIVE_KEYS` (`sbozor_core/logging.py`) endi
  `telegram_bot_token` ni ham qamraydi. 04-04 o'lchagan edi: filtr FAQAT
  ANIQ KALIT NOMIGA qaraydi, ya'ni `*_token` shakli avtomatik
  qamralmasdi va `log.info("x", telegram_bot_token=...)` senzuradan
  O'TMASDAN chiqib ketardi. `SecretStr` bu yo'lni YOPMAYDI — u
  `repr(settings)` ni yopadi, structlog kalitini emas.
=============================================================================

=============================================================================
⛔ 3-TAQIQ — ALERT YUBORISH ASOSIY OQIMNI BLOKLAMAYDI.

`send_message()` ISTISNO KO'TARMAYDI. U `bool` qaytaradi va chaqiruvchi
undan «xabar ketdimi?» degan yagona savolga javob oladi.

Sabab bitta jumlada: KUZATUV VOSITASI KUZATILAYOTGAN TIZIMNI YIQITA
OLMASLIGI KERAK. Telegram uzilganda kadr olish DAVOM ETISHI shart — aks
holda bir soatlik Telegram nosozligi bir kunlik patta hisobini yo'q
qilardi, ya'ni alert mexanizmi o'zi ogohlantirishi kerak bo'lgan zarardan
kattaroq zarar keltirardi.

Mexanizmning ikkinchi yarmi chaqiruvchida (`app/jobs/alerting.py`): xabar
yuborish ALOHIDA, QISQA tranzaksiyada va xato u yerda ham YUTILADI
(`discovery.py:529-556` naqshi).
=============================================================================

=============================================================================
BO'SH TOKEN — QONUNIY HOLAT, LEKIN JIMGINA EMAS.

`alerts_enabled` `False` bo'lganda `httpx` klienti UMUMAN OCHILMAYDI va
`send_message()` darhol `False` qaytaradi. Lekin ishga tushishda BIR
MARTA `log.warning("alerts_disabled")` yoziladi.

Ogohlantirishsiz ishlash aynan «ALERT BOR DEB O'YLASH» yolg'onini
tug'diradi va u D-20 ning («alert muvaffaqiyat signalining YO'QLIGIGA
qo'yiladi») bevosita buzilishi bo'lardi: tizim jim, admin xotirjam,
kadr olish esa uch kundan beri to'xtagan.

⚠ `notified_at` ham `NULL` bo'lib qoladi va UI «Telegram xabari
  YUBORILMADI» qatorini YASHIRMAYDI (`04-UI-SPEC.md` §6.7).
=============================================================================

⚠ `aiogram` QO'SHILMAYDI (§E.12). 4-fazada tugma, FSM, webhook va inline —
  hech biri kerak emas; `httpx` (allaqachon prod bog'liqligi) bilan bitta
  `POST` yetadi. `bot-service` 7-fazada (BOT-01…BOT-04) o'z joyida
  tug'iladi va uni bu yerga tortish butun bir servisni uch faza oldinga
  surardi. To'liq outbox ham bu yerda QURILMAYDI (BOT-04).
"""

from __future__ import annotations

from types import TracebackType
from typing import TYPE_CHECKING, Final, Self

import httpx
import structlog
from tenacity import AsyncRetrying, retry_if_exception, stop_after_attempt, wait_exponential

if TYPE_CHECKING:
    from pydantic import SecretStr

__all__ = [
    "ALERTS_DISABLED_REASON",
    "AlertError",
    "AlertSender",
    "TELEGRAM_API_BASE",
    "TELEGRAM_SEND_METHOD",
]

log = structlog.get_logger(__name__)

TELEGRAM_API_BASE: Final[str] = "https://api.telegram.org"
"""Bot API ning bazaviy manzili — sozlama EMAS, konstanta.

Manzilni sozlanadigan qilish uni foydalanuvchi kiritmasidan qurish yo'lini
ochardi va bot tokeni ixtiyoriy xostga yuborilardi. Bu qiymat testda
`respx` bilan tutiladi, almashtirilmaydi.
"""

TELEGRAM_SEND_METHOD: Final[str] = "sendMessage"
"""⛔ YAGONA ISHLATILADIGAN BOT API METODI (D-19).

Ro'yxatning bitta a'zosi borligi — modul docstringining 1-taqig'i. Bu
konstanta darvoza uchun ham manba: `test_alerting.py` `respx` tutgan HAR
BIR so'rovning yo'li AYNAN shu satr bilan tugashini talab qiladi.
"""

_TIMEOUT_SECONDS: Final[float] = 5.0
"""Telegram bilan muloqot chegarasi — CHEKSIZ KUTISH YO'Q.

⚠ CHEGARA MAJBURIY. Alert jo'natuvchisi `alert_sweep` ning ichida, ya'ni
  worker jarayonida ishlaydi va osilgan chaqiruv har 5 daqiqalik supurgini
  bir-biriga taqab, oxir-oqibat butun navbatni to'sardi. Telegram tashqi
  xizmat, ya'ni uning javob bermasligi NORMAL holat.
"""

_RETRY_ATTEMPTS: Final[int] = 2
"""URINISHLAR SONI — IKKITA, uchta emas.

⚠ ARIFMETIKA: 2 urinish x 5 s = 10 s eng yomon holat. Uchta urinish uni
  15 s ga cho'zardi va `alert_sweep` ning 5 daqiqalik oynasida 30 ta
  yiqilgan alert butun oynani yeb qo'yardi.

⚠ VA U FAQAT TARMOQ SINFIGA QO'LLANADI (`_should_retry`). Telegram ning
  `429` iga qayta urinish chegarani QATTIQROQ urardi — bu `isapi/client.py`
  dagi «`401` ga retry qilmaslik» qoidasining aynan bir xil shakli, faqat
  boshqa sabab bilan.
"""

ALERTS_DISABLED_REASON: Final[str] = "alerts_disabled"
"""Jurnal hodisasining nomi VA UI dagi sababning kaliti.

Bitta satr ikki joyda ishlatiladi: bu yerda `log.warning(...)` sifatida va
`04-UI-SPEC.md` §6.7 ning «Telegram sozlanmagan» tushuntirishi sifatida.
"""


class AlertError(RuntimeError):
    """Telegram javob bermadi yoki xato status qaytardi.

    ⚠ MATNIGA `httpx` ISTISNOSI INTERPOLYATSIYA QILINMAYDI (T-04-59).
      Sabab modul docstringining 2-taqig'ida: bot tokeni URL'ning bir
      qismi.

    ⚠ BU SINF `send_message()` DAN TASHQARIGA CHIQMAYDI — u faqat ichki
      diagnostikani bir joyga yig'adi. Metodning kontrakti `bool`
      (3-taqiq).
    """


def _failure(exc: Exception, status: int | None) -> AlertError:
    """`httpx` istisnosini SIRSIZ `AlertError` ga aylantiradi (T-04-59).

    Uch fakt beriladi va uchalasi ham sirsiz: qaysi AMAL, qaysi XATO TURI,
    qaysi STATUS. Sabab modul docstringida — bu funksiyaning O'Z tanasida
    maxfiy qiymatni tasvirlaydigan hech narsa yozilmaydi, chunki darvoza
    aynan shu tanani o'qiydi.
    """
    detail = f"status={status}" if status is not None else "javob yo'q"
    return AlertError(f"telegram `{TELEGRAM_SEND_METHOD}` yiqildi: {type(exc).__name__} ({detail})")


def _should_retry(exc: BaseException) -> bool:
    """Retry predikati — FAQAT tarmoq sinfi.

    `isapi/client.py::_should_retry` ning JUFTI (nusxa emas: u yerda
    `_TransientServerError` bor va u ISAPI ga xos). Qoidaning O'ZI bir
    xil va sabab ham bir xil shaklda:

      * `httpx.HTTPStatusError` BU YERDA ATAYIN YO'Q. Telegram ning
        `429` i («juda tez yuboryapsiz») va `401` i («token noto'g'ri»)
        qayta urinishdan TUZALMAYDI — birinchisi holatni yomonlashtiradi,
        ikkinchisi esa konfiguratsiya nosozligi.
      * TLS xatosi ham qamralmaydi: qo'l siqish o'zidan o'ziga tuzalmaydi.
    """
    return isinstance(exc, httpx.TimeoutException | httpx.NetworkError)


class AlertSender:
    """`httpx.AsyncClient` ustidagi YUPQA qobiq — AYNAN BITTA amal.

    ⛔ RASM BIRIKTIRUVCHI METOD UMUMAN YO'Q va u «keyin qo'shiladigan
       qulaylik» emas — modul docstringining 1-taqig'iga qarang.

    ⛔ HUJJAT, MEDIA GURUH, XABAR TAHRIRLASH VA XABAR O'CHIRISH metodlari
       ham YO'Q. Ular ham «kerak bo'lib qolsa» qo'shiladigan qulayliklar
       emas: har bir yangi metod yangi yuza va yangi qaror talab qiladi
       («bu chaqiruvda shaxsiy ma'lumot bormi?»), javob esa
       `TELEGRAM_SEND_METHOD` ning YAGONA qiymati bilan tugaydi.

       ⚠ TAQIQLANGAN METOD NOMLARI BU YERDA LITERAL YOZILMAYDI — 03-07
         ning o'lchangan darsi (07-02 uni `models/notification.py` da
         qaytadan to'lagan): sodda grep darvozasi IZOHNI KODDAN
         ajratmaydi, ya'ni taqiqni tushuntirish uchun yozilgan literal
         darvozani O'Z-O'ZIGA QARSHI qo'yardi va yagona «tuzatish» yo'li
         darvozaga istisno qo'shish bo'lardi. Da'vo SUSAYMAYDI, u
         O'LCHANADIGAN joyga ko'chadi: `test_alerting.py::
         test_sender_public_surface_did_not_grow` ommaviy nomlar
         TO'PLAMINI literal to'plam bilan TENGLIK bo'yicha solishtiradi,
         ya'ni yangi metod nima deb atalishidan QAT'I NAZAR ushlanadi —
         grep esa faqat oldindan sanab chiqilgan nomlarni ko'rardi.

    Klient `TaskiqState` da SAQLANADI (worker resursi, `worker.py`):
    `alert_sweep` har 5 daqiqada ishlaydi va har safar yangi TLS qo'l
    siqishi narxini to'lash keraksiz. Bu `Go2rtcClient` dan FARQ QILADI va
    farq sababi chastotada.
    """

    __slots__ = ("_chat_id", "_client", "_enabled", "_url")

    def __init__(
        self,
        *,
        token: SecretStr,
        chat_id: str,
        enabled: bool,
        base_url: str = TELEGRAM_API_BASE,
        timeout: float = _TIMEOUT_SECONDS,
    ) -> None:
        """Jo'natuvchini quradi; o'chirilgan holatda KLIENT OCHILMAYDI.

        Args:
            token: bot tokeni. `SecretStr` — tur darajasidagi himoya.
            chat_id: platforma admini yoki ops guruhining STANDART
                manzili. `send_message(..., chat_id=...)` uni bosib
                o'tadi — sabab metodning docstringida.
            enabled: KLIENT OCHILSINMI. ⛔ Bu `Settings.alerts_enabled`
                ning HOSILASI EMAS va 07-06 da AYNAN shu o'zgardi:
                chegarani CHAQIRUVCHI hal qiladi.

                Sabab o'lchangan (07-RESEARCH Pitfall 9):
                `alerts_enabled = bool(token AND chat_id)`, ya'ni ops
                chati sozlanmagan bozorda BUTUN jo'natuvchi o'chib
                qolardi — SOTUVCHIGA ketadigan kvitansiya (CASH-05) ham
                JIMGINA ketmasdi. Kvitansiya uchun esa ops chati KERAK
                EMAS: unga faqat token va sotuvchining O'Z chati kerak.

                ⛔ IKKINCHI BAYROQ QO'SHILMADI. `settings.py` ochiq
                ogohlantirgan «uchinchi holat» (yoqilgan, lekin
                manzilsiz) shu bilan qaytardi. Uning o'rniga worker
                jo'natuvchini `enabled=bool(token)` bilan quradi va
                ALERT SUPURGISINI chaqiruv joyida `alerts_enabled`
                bilan o'raydi — ya'ni «manzilsiz supurgi» ikkala
                yo'lda ham imkonsiz bo'lib qoladi.
            base_url: FAQAT test uchun almashtiriladi.
            timeout: FAQAT test uchun almashtiriladi.
        """
        self._enabled = enabled
        self._chat_id = chat_id
        if not enabled:
            # Ogohlantirish MAJBURIY — modul docstringining «bo'sh token»
            # bo'limi. Jim ishlash «alert bor deb o'ylash» yolg'onidir.
            log.warning(ALERTS_DISABLED_REASON)
            self._client: httpx.AsyncClient | None = None
            self._url = ""
            return
        # ⚠ MAXFIY QIYMATGA OCHIQ HOLDA BORISH — AYNAN SHU BITTA JOYDA VA
        #   AYNAN URL QURILISHIDAN OLDIN. Qiymat hech qayerga
        #   saqlanmaydi: u faqat quyidagi satrning ichida yashaydi va
        #   `self._url` ning o'zi ham `__slots__` ostida, `repr` siz.
        self._url = f"{base_url}/bot{token.get_secret_value()}/{TELEGRAM_SEND_METHOD}"
        self._client = httpx.AsyncClient(timeout=timeout)

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        """Klientni yopadi — o'chirilgan holatda ham xavfsiz (no-op)."""
        if self._client is not None:
            await self._client.aclose()

    @property
    def enabled(self) -> bool:
        """Alertlar sozlanganmi. UI va `alert_sweep` shu qiymatga qaraydi."""
        return self._enabled

    async def send_message(self, text: str, *, chat_id: str | None = None) -> bool:
        """Matnli xabar yuboradi. ISTISNO KO'TARMAYDI (3-taqiq).

        ⛔ FAQAT MATN. Kadr, obyekt kaliti, rasm havolasi va shaxsiy
           ma'lumot bu chaqiruvga TUSHMAYDI — chaqiruvchi (`alerting.py`)
           matnni sonlar va tarjima kalitlaridan quradi.

        =====================================================================
        ⛔ 1. `chat_id` — ARGUMENT, YANGI METOD EMAS (D-23, 07-06).

        Alert supurgisi OPS chatiga yozadi, outbox esa SOTUVCHINING
        shaxsiy chatiga. Ikkinchi jo'natuvchi SINF yozish modul
        docstringining 1- va 2-taqig'ini IKKILANTIRARDI: darvozalar ikki
        joyda bo'lib, biri ertaga eskirardi va sizish yo'li aynan o'sha
        eskirgan yarimdan ochilardi.

        Kalit argument esa metodlar TO'PLAMINI tegilmagan qoldiradi —
        `TELEGRAM_SEND_METHOD` hamon YAGONA Bot API metodi, ya'ni
        1-taqiq strukturaviy jihatdan KUCHSIZLANMAYDI.

        ⛔ 2. `chat_id` JURNALGA YOZILMAYDI.

        U Telegram FOYDALANUVCHI identifikatori, ya'ni shaxsiy ma'lumot
        (D-01). Pastdagi `log.info("alert_delivered", ...)` hamon faqat
        `chars` va `status` beradi — manzil u yerga na to'g'ridan-to'g'ri,
        na `_failure()` orqali tushadi.

        ⛔ 3. METODLAR SONI O'ZGARMADI.

        Rasm, hujjat va media guruh yuboradigan Bot API metodlari bu
        faylda HAMON YO'Q. `tests/integration/test_alerting.py` ning yuza
        darvozasi buni LITERAL TO'PLAM TENGLIGI bilan o'lchaydi (`len()`
        emas: sanoq bir metodni ikkinchisiga almashtirishni ko'rmasdi).
        =====================================================================

        Args:
            text: yuboriladigan matn (HTML `parse_mode`).
            chat_id: manzil. `None` — konstruktordagi STANDART manzil
                (ops chati). Bo'sh standart + argumentsiz chaqiruv
                `False` beradi va bu XATO EMAS: «manzil yo'q» —
                sozlamaning qonuniy holati.

        Returns:
            `True` — Telegram xabarni QABUL QILDI. `False` — alertlar
            o'chiq, MANZIL yo'q, tarmoq yiqildi, chegaraga urildi yoki
            status xato. Chaqiruvchi `False` ni `notified_at IS NULL` ga
            aylantiradi va UI uni ochiq ko'rsatadi.
        """
        client = self._client
        target = chat_id or self._chat_id
        if client is None or not target:
            return False

        try:
            response = await self._post(client, text, target)
        except AlertError as error:
            # ⚠ `str(error)` XAVFSIZ: `_failure()` unga faqat amal, xato
            #   turi va statusni beradi.
            log.warning("alert_not_delivered", error=str(error))
            return False

        log.info("alert_delivered", chars=len(text), status=response)
        return True

    async def _post(self, client: httpx.AsyncClient, text: str, target: str) -> int:
        """Retry qatlami — FAQAT tarmoq sinfi (`_should_retry`).

        ⚠ ISTISNO `except` BLOKIDAN TASHQARIDA KO'TARILADI (04-06 ning
          o'lchovi): blok tugagach Python kontekstni tozalaydi, ya'ni
          `__context__` ham xom istisnoni tashimaydi. `from None` yolg'iz
          o'zi faqat `__cause__` ni yopardi.

        ⚠ `target` ARGUMENT, `self._chat_id` EMAS: manzil chaqiruv
          joyida hal qilinadi (`send_message` docstringining 1-bandi).
          Uni bu yerda qayta o'qish argumentli chaqiruvni JIMGINA ops
          chatiga burardi — ya'ni sotuvchining kvitansiyasi begona chatga
          ketardi.
        """
        payload = {
            "chat_id": target,
            "text": text,
            # HTML — `Markdown` dan xavfsizroq: bozor nomida `_` yoki `*`
            # bo'lsa Markdown parseri butun xabarni rad etardi.
            "parse_mode": "HTML",
            # Xabar matnidagi havolalarning oldi ko'rinishi O'CHIRILADI:
            # u tashqi so'rov tug'diradi va xabarni kengaytiradi.
            "disable_web_page_preview": True,
        }
        retrying: AsyncRetrying = AsyncRetrying(
            stop=stop_after_attempt(_RETRY_ATTEMPTS),
            wait=wait_exponential(multiplier=0.3, max=2.0),
            retry=retry_if_exception(_should_retry),
            reraise=True,
        )

        captured: Exception | None = None
        status: int | None = None
        try:
            response: httpx.Response = await retrying(client.post, self._url, json=payload)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            captured, status = exc, exc.response.status_code
        except httpx.HTTPError as exc:
            captured = exc
        else:
            return int(response.status_code)

        raise _failure(captured, status) from None
