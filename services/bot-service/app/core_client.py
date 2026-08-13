"""`core-api` ning ichki bot yuzasiga YUPQA qobiq (D-08, D-10, D-04).

=============================================================================
⛔⛔ BOTNING YAGONA MA'LUMOT MANBAI SHU FAYL.

`app/settings.py` ochiq yozgan: bu servisda `database_url` YO'Q va bu
unutilgan emas, QAROR. Telegram'dan kelgan oqim autentifikatsiya
QILINMAGAN, ya'ni unga baza ulanishini berish IKKINCHI RLS yuzasini
ochardi (T-07-01). Shuning uchun handlerlar SQL yozmaydi, sxemani
bilmaydi va bozor identifikatorini O'ZLARI tanlamaydi — ular faqat shu
qobiqqa boradi, u esa `Bearer` bilan `core-api` ga.

=============================================================================
⛔⛔ 1-TAQIQ — MAXFIY QIYMATGA OCHIQ HOLDA BORISH AYNAN BITTA JOYDA.

Servis tokeni `SecretStr` ichida yashaydi va undan chiqadigan yagona
joy — quyidagi `_service_token_header()`. U yerdan qiymat to'g'ridan-
to'g'ri `httpx.AsyncClient(headers=...)` ga o'tadi va `self` ga
SAQLANMAYDI: klient obyektining birorta atributi tokenni tashimaydi,
ya'ni `repr(client)` va Sentry'ning lokal o'zgaruvchilar to'plami uni
KO'RA OLMAYDI.

⛔ TOKEN URL GA HECH QACHON TUSHMAYDI. U so'rov SARLAVHASIDA yuboriladi;
   `httpx` istisnolarining matni esa URL ni o'z ichiga oladi. So'rov
   satriga qo'yilgan token birinchi tarmoq xatosidayoq jurnalga chiqardi
   — va o'sha jurnal Sentry'ga ketardi.

=============================================================================
⛔⛔ 2-TAQIQ — ISTISNO MATNI HECH QAYERGA YOZILMAYDI (D-04).

`app/services/alerts.py::_failure()` ning qoidasi BU YERDA TAKRORLANADI,
chunki bu boshqa kod bazasi va u yerdagi darvoza bu fayl ustida
ishlamaydi. Qoida: uch fakt beriladi va uchalasi ham sirsiz — qaysi
AMAL, qaysi XATO TURI, qaysi STATUS.

⛔ `str(exc)`, `repr(exc)` va f-string ichida istisno — TAQIQ. Sabab
   mexanik: `httpx` istisnosining matni so'rov URL ini o'z ichiga oladi
   va kelajakda u yerga qo'yilgan har qanday parametr (masalan telefon
   raqami) jurnalga ko'chib o'tardi. Taqiq
   `tests/unit/test_core_client_secrets.py` da `ast` bilan o'lchanadi —
   u `app/handlers/*.py` ni ham skanerlaydi, ya'ni istisno matni
   FOYDALANUVCHIGA ham ko'rsatilmasligi shu yerda qulflanadi.

=============================================================================
⚠⚠ BU YUZA ISTISNO KO'TARADI — VA BU `AlertSender` DAN ATAYIN FARQ QILADI.

`alerts.py::send_message()` istisno KO'TARMAYDI: u kuzatuv vositasi va
kuzatuv kuzatilayotgan tizimni yiqita olmasligi kerak.

Bu yerda yo'nalish TESKARI. Bu — KIRUVCHI yuza: sotuvchi tugmani bosdi va
javob KUTAYAPTI. Jim yiqilish uni JAVOBSIZ qoldirardi — ekranda hech
narsa o'zgarmasdi va u tugmani yana bosardi. Shuning uchun metod
`CoreApiError` ko'taradi, handler esa uni tutib «keyinroq urinib
ko'ring» matnini ko'rsatadi. Ya'ni nosozlik KO'RINADI, lekin uning
TAFSILOTI ko'rinmaydi.
=============================================================================
"""

from __future__ import annotations

from contextlib import suppress
from datetime import date
from typing import Any, Final
from uuid import UUID

import httpx
import structlog
from pydantic import BaseModel, SecretStr

log = structlog.get_logger(__name__)

RESOLVE_PATH: Final = "/internal/bot/resolve"
DIRECTOR_RESOLVE_PATH: Final = "/internal/bot/director/resolve"
VENDOR_SUMMARY_PATH: Final = "/internal/bot/vendor/summary"
VENDOR_PAYMENTS_PATH: Final = "/internal/bot/vendor/payments"

DEFAULT_TIMEOUT_SECONDS: Final = 5.0
"""⚠ Taym-aut MAJBURIY va u standart `httpx` qiymatiga tashlab qo'yilmaydi.

Sotuvchi tugmani bosgan va javob kutayapti: cheksiz kutish uni «bot
qotdi» holatida qoldirardi, aiogram esa o'sha update uchun handler
korutinasini ushlab turardi.
"""

DEFAULT_PAGE_SIZE: Final = 10
"""«To'lovlarim» ning bir sahifasi — ⛔ oxirgi 10 qator (reja Task 2).

Telegram xabari uzun bo'lsa sotuvchi telefonda uni umuman o'qimaydi;
qolgani «Ko'proq» tugmasi ortida.
"""

BOUND_STATUS: Final = "bound"
"""⛔⛔ RESOLVE JAVOBINING YAGONA NOMLANGAN HOLATI — VA BU D-26(a) NING KODDAGI SHAKLI.

`core-api` uchta holat qaytaradi: `bound`, `no_match`, `multiple_matches`.
Bot ⛔ FAQAT BIRINCHISINI biladi; qolgan ikkitasi uchun bu yerda na
konstanta, na shox bor.

Sabab: agar ikkinchi va uchinchi holat kodda NOMLANSA, ertaga kimdir
ularga har xil matn yozish yo'lini ochardi — va o'sha farq reyestrni
TASHQARIDAN tekshirish oracle'iga aylanardi («raqamim ro'yxatda bormi?»
degan savolga bot javob berardi). Bu yerda ikkalasi ham «`bound` emas»
degan BITTA shoxga tushadi, ya'ni matn tengligi TESTGA emas, STRUKTURAGA
tayanadi.
"""

_NOT_BOUND_STATUS: Final = 404
"""`core-api` ning «bog'lanmagan» javobining STATUSI — ⛔ YOLG'IZ O'ZI YETMAYDI.

⚠ SHART IKKI QISMLI: status VA `_NOT_BOUND_DETAIL`. Sabab pastdagi
  konstantaning docstringida.
"""

_NOT_BOUND_DETAIL: Final = "not_bound"
"""`core-api` ning «bu Telegram akkaunti hech qaysi sotuvchiga bog'lanmagan»
javobidagi NOMLANGAN detal. Bu XATO EMAS, HOLAT.

=============================================================================
⛔⛔ SATR `api/internal/bot.py::_NOT_BOUND` BILAN AYNAN BIR XIL BO'LISHI
   SHART VA U BU YERDA LITERAL TAKRORLANADI.

Sabab mexanik: bu IKKINCHI KOD BAZASI (`bot-service` ning O'Z
`pyproject.toml` va `uv.lock` i bor, D-09), ya'ni `core-api` dan import
qilishning YO'LI YO'Q. To'plam a'zoligi bilan bog'lash ham imkonsiz.
Shuning uchun juftlik LITERAL, va uning sababi shu yerda OCHIQ yozilgan —
`binding_repo::VENDOR_BINDING_CONFLICT_ALERT_KEY` bilan aynan bir xil
holat va aynan bir xil yechim.

=============================================================================
⛔⛔ NEGA STATUS YOLG'IZ O'ZI YETMAYDI — VA BU O'LCHANGAN NUQSON (WR-01).

Ilgari HAR QANDAY `404` `NotBoundError` ga aylanardi. Ya'ni:

  * noto'g'ri sozlangan `CORE_API_URL` (marshrut umuman yo'q -> nginx
    yoki FastAPI ning `{"detail": "Not Found"}` i),
  * `/internal/bot/*` prefiksining o'zgarishi,
  * oradagi proxy ning HTML `404` sahifasi

uchalasi ham sotuvchiga «SIZ BOG'LANMAGANSIZ» degan xulosani berardi va
`/start` uni kontakt tugmasiga qaytarardi. Sotuvchi raqamini QAYTA
yuborardi, natija O'ZGARMASDI — ya'ni infratuzilma nosozligi
FOYDALANUVCHINING nuqsoni bo'lib ko'rinardi. `start.py:97-98` aynan shu
YOLG'ON xulosani ochiq taqiqlaydi.

⚠ Endi faqat NOMLANGAN detal shu shoxga olib boradi; qolgan har qanday
  `404` oddiy `CoreApiError` bo'ladi va handler `bot.error.retry` ni
  ko'rsatadi — ya'ni nosozlik KO'RINADI, lekin u sotuvchining aybi
  bo'lib ko'rinmaydi.
=============================================================================
"""


# ===========================================================================
# XATOLAR — ⛔ MATN EMAS, TUR VA STATUS
# ===========================================================================


class CoreApiError(Exception):
    """`core-api` chaqiruvi yiqildi — ⛔ SIRSIZ uch fakt bilan.

    Attributes:
        operation: qaysi AMAL (`resolve` / `vendor_summary` / ...).
        error_type: qaysi XATO TURI — ⛔ `type(exc).__name__`, hech qachon
            istisnoning MATNI.
        status: qaysi HTTP STATUS (javob umuman kelmagan bo'lsa `None`).

    ⚠ Xabar matni shu uch fakt ustida quriladi va boshqa hech narsa
      ustida qurilmaydi. Handler bu matnni FOYDALANUVCHIGA
      KO'RSATMAYDI — u faqat jurnal va Sentry uchun.
    """

    def __init__(self, *, operation: str, error_type: str, status: int | None) -> None:
        self.operation = operation
        self.error_type = error_type
        self.status = status
        detail = f"status={status}" if status is not None else "javob yo'q"
        super().__init__(f"core-api `{operation}` yiqildi: {error_type} ({detail})")


class NotBoundError(CoreApiError):
    """`404` + NOMLANGAN `not_bound` detali — akkaunt hech kimga bog'lanmagan.

    ⛔ ALOHIDA TUR, `status == 404` TEKSHIRUVI EMAS. Sabab: bu HOLAT
    handlerda «xato» shoxidan BOSHQA javob beradi (foydalanuvchi
    `/start` ga qaytariladi), ya'ni farq handlerlarning har birida
    takrorlanadigan sehrli songa emas, TURGA tayanishi kerak.

    ⛔⛔ SHART IKKI QISMLI VA IKKINCHI QISM 07-21 DA QO'SHILDI (WR-01):
       statusning O'ZI yetmaydi, javob tanasida `detail == "not_bound"`
       ham bo'lishi SHART. Sabab `_NOT_BOUND_DETAIL` docstringida —
       qisqasi, noto'g'ri sozlangan `CORE_API_URL` ham `404` beradi va
       u sotuvchiga «siz bog'lanmagansiz» degan YOLG'ON xulosani
       berardi.
    """


def _is_not_bound(response: httpx.Response) -> bool:
    """Javob AYNAN «bog'lanmagansiz» holatimi — status VA nomlangan detal.

    =========================================================================
    ⛔ TANA FAQAT TENGLIK UCHUN O'QILADI (D-04). Olingan `detail` qiymati
       ⛔ HECH QAYERGA yozilmaydi: na jurnalga, na istisno matniga, na
       qaytish qiymatiga. Funksiya `bool` qaytaradi va aynan shu sababdan:
       satrni qaytarish uni chaqiruvchining ixtiyoriga qo'yardi va ertami
       kechmi u jurnalga chiqardi.

    ⚠ `suppress(ValueError)` — `json.JSONDecodeError` ning ota-turi.
      HTML `404` sahifasi, bo'sh tana va buzuq JSON uchalasi ham shu
      yerda tugaydi va ⛔ `False` beradi, ya'ni ular «bog'lanmagansiz»
      xulosasiga OLIB BORMAYDI (WR-01).

    ⚠ `isinstance(..., dict)` MAJBURIY: `json()` ro'yxat yoki satr
      qaytarishi mumkin va o'shanda `.get()` `AttributeError` berardi —
      ya'ni infratuzilma nosozligi botni YIQITARDI.
    =========================================================================
    """
    if response.status_code != _NOT_BOUND_STATUS:
        return False
    with suppress(ValueError):
        body = response.json()
        if isinstance(body, dict):
            return bool(body.get("detail") == _NOT_BOUND_DETAIL)
    return False


def _failure(
    operation: str, exc: Exception, status: int | None, *, not_bound: bool = False
) -> CoreApiError:
    """`httpx` istisnosini SIRSIZ `CoreApiError` ga aylantiradi (D-04).

    ⛔ Bu funksiyaning tanasida istisnoni TASVIRLAYDIGAN hech narsa
       yozilmaydi: darvoza aynan shu tanani `ast` bilan o'qiydi va
       `str(exc)` / f-string ichidagi istisno uni QIZARTIRADI.

    Args:
        not_bound: ⛔ QAROR CHAQIRUVCHIDA QABUL QILINADI, bu yerda EMAS.
            Ilgari shox `status == 404` bilan tanlanardi va o'sha shakl
            HAR QANDAY `404` ni «bog'lanmagansiz» ga aylantirardi
            (WR-01, `_NOT_BOUND_DETAIL` docstringi). Bayroq shaklida
            javob TANASI ham qarorga kiradi, lekin uning QIYMATI bu
            funksiyaga UMUMAN yetib kelmaydi — ya'ni D-04 darvozasi
            (`ast` bilan shu tanani o'qiydi) yashil qoladi.
    """
    log.warning(
        "core_api_call_failed",
        operation=operation,
        # ⛔ AYNAN SHU SHAKL TALAB QILINADI (darvozaning (c) bandi):
        #    tur NOMI, istisno MATNI emas.
        error_type=type(exc).__name__,
        status=status,
    )
    if not_bound:
        return NotBoundError(operation=operation, error_type=type(exc).__name__, status=status)
    return CoreApiError(operation=operation, error_type=type(exc).__name__, status=status)


def _service_token_header(token: SecretStr) -> dict[str, str]:
    """⛔ MAXFIY QIYMATGA OCHIQ HOLDA BORISH — AYNAN SHU BITTA JOYDA.

    `alerts.py:296-300` naqshi: qiymat o'qiladi va DARHOL yuboriladigan
    tuzilmaga qo'yiladi; oraliq o'zgaruvchi ham, atribut ham
    tug'ilmaydi.

    ⚠ f-string ATAYIN ISHLATILMAGAN: bu modulda f-string ichidagi qiymat
      darvozaning tekshiruv maydoni va sirni o'sha maydondan butunlay
      chiqarib yuborish arzonroq.
    """
    return {"Authorization": "Bearer " + token.get_secret_value()}


# ===========================================================================
# JAVOB MODELLARI — `api/internal/bot.py` NING KO'ZGUSI
# ===========================================================================
#
# ⚠ `extra` ATAYIN QAT'IY EMAS (frontenddagi `z.strictObject` dan farqli).
#   U yerda qat'iylik server yuzasining jimgina kengayishini to'sadi va
#   ikkinchi tomon O'SHA jamoa. Bu yerda esa iste'molchi ISHLAB TURGAN
#   bot: `core-api` javobga maydon qo'shsa, sotuvchining qarzi ko'rinmay
#   qolishi «qat'iylik» narxi sifatida juda qimmat. Yuzaning qat'iyligi
#   server tomonda (`api/internal/bot.py` javob modellari) o'lchanadi.


class VendorRef(BaseModel):
    """⛔ FAQAT IDENTIFIKATORLAR — ism va telefon YO'Q (D-05)."""

    market_id: UUID
    vendor_id: UUID


class ResolveResult(BaseModel):
    """`POST /internal/bot/resolve` javobi."""

    status: str
    vendor: VendorRef | None = None


class DirectorResolveResponse(BaseModel):
    """`POST /internal/bot/director/resolve` javobi — ⛔ ikki maydon, boshqasi YO'Q.

    ⛔ SERVER `market_id` RO'YXATINI QAYTARMAYDI va bot uni SO'RAMAYDI:
       direktor bu fazada OLUVCHI, u botga bitta marta kontakt ulashadi va
       boshqa hech narsa qilmaydi. `market_count` esa «ulandingizmi?»
       degan yagona savolga javob berish uchun yetarli.
    """

    status: str
    market_count: int


class MarketSummary(BaseModel):
    """Bitta bozordagi qoldiq — ⛔ SON BUTUN (`int`), `float` YO'Q (D-07)."""

    market_id: UUID
    vendor_id: UUID
    outstanding_soum: int
    as_of: date
    stall_codes: list[str] = []


class VendorSummary(BaseModel):
    """⚠ RO'YXAT: bir sotuvchi ikki bozorda faol bo'lishi QONUNIY.

    Server birinchisini JIMGINA tanlamaydi (07-08 qarori), ya'ni tanlov
    bu yerda ham qilinmaydi — bot barcha bozorlarni ko'rsatadi.
    """

    markets: list[MarketSummary] = []


class ChargeRow(BaseModel):
    """Bir kunlik hisob va unga tushgan kredit — ⛔ ikkala son ham `int`."""

    service_date: date
    stall_code: str
    due_soum: int
    paid_soum: int
    settled: bool


class PaymentsPage(BaseModel):
    """`GET /internal/bot/vendor/payments` ning bitta sahifasi."""

    market_id: UUID
    vendor_id: UUID
    rule: str
    rows: list[ChargeRow] = []
    next_cursor: str | None = None


# ===========================================================================
# KLIENT
# ===========================================================================


class CoreClient:
    """`core-api` ning `/internal/bot/*` yuzasi ustidagi yupqa qobiq.

    ⛔ QOBIQ «YUPQA» EKANI QAROR: bu yerda keshlash, qayta urinish va
       biznes mantiq YO'Q. Har biri o'z sababi bilan tashqarida —
       keshlash qarz sonini ESKIRTIRARDI (D-02 ning teskarisi), qayta
       urinish esa sotuvchining kutish vaqtini taym-autlar yig'indisiga
       aylantirardi.
    """

    __slots__ = ("_client",)

    def __init__(
        self,
        *,
        base_url: str,
        token: SecretStr,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        """Klientni quradi; ⛔ token `self` ga SAQLANMAYDI.

        Args:
            base_url: `core-api` ning compose tarmog'idagi manzili.
            token: servis-servis tokeni. `SecretStr` — tur darajasidagi
                himoya; qiymat faqat `_service_token_header()` ichida
                ochiladi.
            timeout: FAQAT test uchun almashtiriladi.
            transport: ⚠ FAQAT TEST UCHUN (`alerts.py` dagi `base_url`
                bilan bir xil naqsh). `httpx.MockTransport` bilan
                darvoza soketsiz ishlaydi, ya'ni «token sarlavhada,
                URL da emas» da'vosi HAQIQIY so'rov obyekti ustida
                o'lchanadi.
        """
        self._client = httpx.AsyncClient(
            base_url=base_url,
            timeout=timeout,
            headers=_service_token_header(token),
            transport=transport,
        )

    async def aclose(self) -> None:
        """Ulanish pulini yopadi (`_main()` ning `finally` bloki)."""
        await self._client.aclose()

    async def _request(
        self,
        operation: str,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> Any:
        """Bitta chaqiruv — ⛔ istisno SIRSIZ turga aylantiriladi.

        ⚠ `raise ... from exc` SAQLANADI: zanjir Sentry uchun kerak va u
          sir tashimaydi — token SARLAVHADA, `httpx` xabari esa URL ni
          ko'rsatadi. Sir chiqadigan yagona yo'l istisno MATNINI o'zimiz
          ko'chirishimiz bo'lardi va aynan shu taqiqlangan.
        """
        try:
            response = await self._client.request(method, path, params=params, json=json)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            # ⛔ TANA SHU YERDA O'QILADI, `_failure()` ICHIDA EMAS: qaror
            #   (qaysi istisno turi) chaqiruvchida qabul qilinadi va
            #   `_failure()` faqat BAYROQ oladi — ya'ni javob mazmuni D-04
            #   darvozasi qo'riqlaydigan tanaga umuman kirmaydi.
            raise _failure(
                operation, exc, exc.response.status_code, not_bound=_is_not_bound(exc.response)
            ) from exc
        except httpx.HTTPError as exc:
            raise _failure(operation, exc, None) from exc
        except ValueError as exc:
            # JSON o'qib bo'lmadi — `json.JSONDecodeError` `ValueError` ning
            # avlodi. Bu ham NOSOZLIK va u ham sirsiz turga aylanadi.
            raise _failure(operation, exc, None) from exc

    async def resolve(self, *, telegram_user_id: int, raw_phone: str) -> ResolveResult:
        """BOT-01 — «bu Telegram ID kimning akkaunti?» (D-10, D-26).

        ⛔ RAQAM SO'ROV TANASIDA YUBORILADI, URL DA EMAS. Telefon —
           shaxsiy ma'lumot (O'zR qonuni ostida); URL esa jurnalning,
           proxy'ning va `httpx` istisno matnining ichiga tushadi.

        ⛔ NORMALIZATSIYA BU YERDA QILINMAYDI (D-25): u chegarada va
           AYNAN BIR JOYDA — `core-api` ning `binding_repo._normalize`
           ida. Ikkinchi implementatsiya bir kun boshqa natija berardi
           va bog'lanish JIMGINA buzilardi.
        """
        payload = await self._request(
            "resolve",
            "POST",
            RESOLVE_PATH,
            json={"telegram_user_id": telegram_user_id, "phone": raw_phone},
        )
        return ResolveResult.model_validate(payload)

    async def resolve_director(
        self, *, telegram_user_id: int, raw_phone: str
    ) -> DirectorResolveResponse:
        """RECON-03 — «bu Telegram akkaunti qaysi bozorning direktoriniki?».

        ⛔ IKKINCHI CHAQIRUV, IKKINCHI YUZA EMAS: handler avval
           `resolve()` ni chaqiradi va faqat u mos kelmaganda shu yerga
           tushadi. Ikkalasi ham AYNI kontaktdan, AYNI rate-limit
           sanagichi ostida ishlaydi.

        ⛔ RAQAM SO'ROV TANASIDA, URL DA EMAS (`resolve()` bilan bir xil
           sabab): telefon — shaxsiy ma'lumot, URL esa jurnalning,
           proxy'ning va `httpx` istisno matnining ichiga tushadi.

        ⛔ NORMALIZATSIYA BU YERDA QILINMAYDI (D-25) — u chegarada va
           AYNAN BIR JOYDA.

        Raises:
            CoreApiError: har qanday nosozlik — ⛔ SIRSIZ uch fakt bilan.
                `404` bu yuzada HOLAT emas: «topilmadi» javobi `200` +
                `no_match` bo'lib keladi.
        """
        payload = await self._request(
            "resolve_director",
            "POST",
            DIRECTOR_RESOLVE_PATH,
            json={"telegram_user_id": telegram_user_id, "phone": raw_phone},
        )
        return DirectorResolveResponse.model_validate(payload)

    async def vendor_summary(self, *, telegram_user_id: int) -> VendorSummary:
        """BOT-02 (1/2) — sotuvchining qoldig'i, har bozor uchun alohida.

        Raises:
            NotBoundError: `404` + `detail == "not_bound"` — akkaunt hech
                qaysi sotuvchiga bog'lanmagan (HOLAT, xato emas).
            CoreApiError: qolgan har qanday nosozlik — ⛔ NOMLANMAGAN
                `404` ham SHU YERGA tushadi (WR-01).
        """
        payload = await self._request(
            "vendor_summary",
            "GET",
            VENDOR_SUMMARY_PATH,
            params={"telegram_user_id": telegram_user_id},
        )
        return VendorSummary.model_validate(payload)

    async def vendor_payments(
        self,
        *,
        telegram_user_id: int,
        market_id: UUID,
        cursor: str | None = None,
        limit: int = DEFAULT_PAGE_SIZE,
    ) -> PaymentsPage:
        """BOT-02 (2/2) — «qaysi kunning pattasi to'landi?».

        ⛔ `market_id` MAJBURIY VA BU 07-08 NING QARORI: bir Telegram ID
           ikki bozorda faol bo'lishi mumkin va serverda «birinchisini
           tanlash» sotuvchiga BOSHQA bozorning tarixini ko'rsatardi.
           Qiymat `vendor_summary()` javobidan olinadi — ya'ni tanlov
           ma'lumotdan keladi, taxmindan emas.
        """
        params: dict[str, Any] = {
            "telegram_user_id": telegram_user_id,
            "market_id": str(market_id),
            "limit": limit,
        }
        if cursor is not None:
            params["cursor"] = cursor
        payload = await self._request("vendor_payments", "GET", VENDOR_PAYMENTS_PATH, params=params)
        return PaymentsPage.model_validate(payload)
