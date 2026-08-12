"""Login urinishlari sanagichi — Valkey (T-01-39).

=============================================================================
IKKI KESIM, IKKI XIL HUJUM:

* **telefon bo'yicha** (15 daqiqada 10 urinish) — bitta hisobga qarshi
  parol tanlash. Chegara past, chunki haqiqiy foydalanuvchi parolini 10
  martadan ko'p noto'g'ri yozmaydi.
* **IP bo'yicha** (15 daqiqada 50 urinish) — bitta manbadan ko'p hisobga
  qarshi "password spraying" (har hisobga 1-2 urinish, ya'ni telefon
  sanagichi umuman ishga tushmaydi).

Faqat telefon kesimi bo'lganda spraying to'sqinliksiz o'tardi; faqat IP
kesimi bo'lganda esa NAT ortidagi butun bozor bir sanagichga tushardi.
=============================================================================

Argon2id ning o'zi ham himoya qatlami (har tekshiruv ~100 ms), lekin u
faqat NARXNI oshiradi — sanagich esa CHEGARA qo'yadi.

VALKEY YO'Q BO'LSA: rate-limit O'TKAZIB YUBORILADI va `warning` yoziladi.
Bu ataylab: kesh o'chgani uchun BUTUN TIZIMGA kirishni to'sib qo'yish
(fail-closed) mavjud xizmatni yo'q qiladi, parol tekshiruvi esa baribir
ishlaydi. Bloklash holati (D-08) bundan farq qiladi — u kesh o'chganda
DB'ga tushadi, chunki u haqiqiy avtorizatsiya qarori.

=============================================================================
3-FAZA: `POST /nvr-devices/test-connection` — YUQORIDAGI MULOHAZA BU YERDA
TESKARI ISHLAYDI VA BU FARQ QASDDAN YOZILGAN.

Login yo'lida chegara BIZNING tomonimizda: u BIZNING hisobimizni himoya
qiladi va uni bosish faqat bizning javobimizni sekinlashtiradi.

«Ulanishni tekshirish» yo'lida chegara NVR TOMONIDA: har urinish
qurilmaning O'Z qulflash hisoblagichini oshiradi va Hikvision ~5 xato
urinishdan keyin hisobni 30 daqiqaga qulflaydi — undan keyin TO'G'RI
PAROL HAM ISHLAMAYDI (`03-RESEARCH.md` A.3, D-03). Ya'ni bu yerda
sanagich foydalanuvchini O'ZIMIZDAN emas, O'ZIDAN himoya qiladi.

Ikkita oqibat kelib chiqadi:

  1. Chegara Hikvision'ning ~5 idan PAST bo'lishi SHART (aks holda u
     qurilma qulflangandan KEYIN ishga tushardi va foydasiz bo'lardi);
  2. Chegaradan oshgan so'rov NVR ga BORMASLIGI shart — u shunchaki
     sekinlashtirilmaydi, u UMUMAN yuborilmaydi. Bu da'voning yagona
     dalili — SIMULYATSIYA QILINGAN QURILMADAGI URINISHLAR SANOG'I:
     natijadan o'lchab bo'lmaydi, chunki chaqirib-yutgan kod ham aynan
     bir xil javob berardi (T-03-37).

⚠ Sanoq endpointining ANIQ YO'LI bu yerda ATAYIN yozilmagan.
  `tests/unit/test_no_sim_branching.py` `app/` daraxtida simulyatorning
  imzolarini izlaydi va KODNI IZOHDAN AJRATMAYDI — 03-04 (`nvr_host.py`)
  va 03-05 (`parser.py`) da bu darvoza aynan shu sababdan ikki marta
  urilgan. Nom test faylida yashaydi, ya'ni to'g'ri tomonda.
=============================================================================
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog
from redis.exceptions import RedisError

if TYPE_CHECKING:
    from redis.asyncio import Redis

__all__ = [
    "BOT_RESOLVE_LIMIT",
    "BOT_RESOLVE_WINDOW_SECONDS",
    "IP_LIMIT",
    "NVR_TEST_LIMIT",
    "NVR_TEST_WINDOW_SECONDS",
    "PHONE_LIMIT",
    "WINDOW_SECONDS",
    "TooManyAttempts",
    "check_bot_resolve_rate",
    "check_login_rate",
    "check_nvr_test_rate",
    "reset_login_rate",
]

log = structlog.get_logger(__name__)

WINDOW_SECONDS = 15 * 60
"""Sanagich oynasi. Birinchi urinishda TTL qo'yiladi va oyna shundan boshlanadi."""

PHONE_LIMIT = 10
"""Bitta telefon uchun oynadagi urinishlar soni."""

IP_LIMIT = 50
"""Bitta IP uchun oynadagi urinishlar soni (NAT ortidagi bozor uchun bo'sh joy)."""

_PHONE_KEY = "rl:login:phone:"
_IP_KEY = "rl:login:ip:"

NVR_TEST_LIMIT = 3
"""«Ulanishni tekshirish» uchun oynadagi urinishlar soni.

⚠ QIYMAT HIKVISION NING ~5 IDAN PAST BO'LISHI SHART VA BU MULOHAZA
  QIYMATNING O'ZIDAN MUHIMROQ (modul docstringi).

Arifmetika: `httpx.DigestAuth` har urinishda challenge'ni qayta oladi va
qurilmaga IKKI so'rov yuboradi (03-05 da o'lchangan), lekin ulardan faqat
rekvizitlisi qulflash hisoblagichiga tushadi. Ya'ni 3 ta bosish ≈ 3 ta
xato urinish va foydalanuvchida qulflanishgacha yana bir-ikkita zaxira
qoladi — o'shani NVR ning O'Z veb-interfeysi yoki boshqa admin ishlatishi
mumkin.

Chegara 5 ga tenglashtirilsa u qurilma qulflanishi bilan BIR VAQTDA
ishga tushardi, ya'ni hech qanday himoya bermasdi.
"""

NVR_TEST_WINDOW_SECONDS = 15 * 60
"""Oyna — 15 daqiqa.

Hikvision qulfi ~30 daqiqa (`03-RESEARCH.md` A.3), ya'ni bizning oyna
undan QISQA: qurilma o'zini qulfdan chiqargandan keyin admin darhol
qayta urina olishi kerak, aks holda biz qulfni sun'iy ravishda
uzaytirardik.
"""

_NVR_TEST_KEY = "rl:nvr_test:"
"""Kalit shakli — `rl:nvr_test:<market_id>:<host>`.

⚠ KESIM BOZOR VA NISHON QURILMA BO'YICHA, FOYDALANUVCHI BO'YICHA EMAS.
  Chegara qurilmaning qulflash hisoblagichini himoya qiladi, u esa
  BITTA: bir bozorda ikki admin bir NVR ni navbat bilan sinasa hisoblagich
  ikkalasining urinishini QO'SHIB boradi. Foydalanuvchi bo'yicha kesim
  o'sha yig'indini ko'rmasdi va chegara ikki barobar oshib ketardi.

  `market_id` prefiksi ikki bozorning bir xil xususiy IP (`192.168.1.64`
  — eng ko'p uchraydigan qiymat) ishlatishini hisobga oladi: usiz A
  bozorining urinishlari B bozorining adminini qulflardi.
"""


class TooManyAttempts(Exception):
    """Chegara oshdi — endpoint buni `429 too_many_attempts` ga aylantiradi."""

    def __init__(self, scope: str) -> None:
        super().__init__(f"login rate limit exceeded: {scope}")
        self.scope = scope


async def _bump(cache: Redis, key: str, limit: int, window: int = WINDOW_SECONDS) -> bool:
    """Sanagichni oshiradi; chegara oshgan bo'lsa `False` qaytaradi.

    `INCR` + birinchi urinishda `EXPIRE` — ikkalasi bitta pipeline'da,
    ya'ni `INCR` bajarilib `EXPIRE` yiqilgan holatda kalit MANGU qolib
    ketmaydi (o'shanda foydalanuvchi butunlay qulflanardi).

    `window` STANDART QIYMAT bilan keladi (login oynasi), ya'ni mavjud
    ikkita chaqiruv o'zgarmaydi. NVR yo'li o'z oynasini beradi — sabab
    `NVR_TEST_WINDOW_SECONDS` docstringida.
    """
    async with cache.pipeline(transaction=True) as pipe:
        pipe.incr(key)
        pipe.expire(key, window, nx=True)
        results = await pipe.execute()
    return int(results[0]) <= limit


async def check_login_rate(cache: Redis, *, phone: str, ip: str | None) -> None:
    """Login urinishini sanaydi va chegarani tekshiradi.

    Raises:
        TooManyAttempts: telefon yoki IP kesimi bo'yicha chegara oshsa.
    """
    try:
        if not await _bump(cache, _PHONE_KEY + phone, PHONE_LIMIT):
            raise TooManyAttempts("phone")
        if ip and not await _bump(cache, _IP_KEY + ip, IP_LIMIT):
            raise TooManyAttempts("ip")
    except RedisError as exc:
        # Auth'ning o'zi bloklanmaydi — pastdagi izohga qarang (modul
        # docstringi): parol tekshiruvi baribir bajariladi.
        log.warning("login_rate_limit_unavailable", error=str(exc))


async def check_nvr_test_rate(cache: Redis, *, market_id: str, host: str) -> None:
    """«Ulanishni tekshirish» urinishini sanaydi va chegarani tekshiradi (T-03-37).

    ⚠ CHAQIRUV NVR GA BORISHDAN OLDIN BO'LISHI SHART. Keyin chaqirilsa
      chegaradan oshgan so'rov ALLAQACHON qurilmaga yetib borgan bo'lardi
      va sanagich faqat javobni to'sardi — ya'ni himoya yo'q, faqat uning
      ko'rinishi qolardi. Buni test sim'ning urinishlar sanog'i bilan
      o'lchaydi, natijadan emas (03-05 ning «chaqirilmadi da'vosining
      yagona dalili — SO'ROVLAR SANOG'I» qoidasi).

    ⚠ MUVAFFAQIYATLI TEKSHIRUVDAN KEYIN SANAGICH TOZALANMAYDI —
      `reset_login_rate()` bilan farq shu yerda. Login'da muvaffaqiyat
      "parol to'g'ri" degani, ya'ni oldingi xatolar endi ahamiyatsiz.
      Bu yerda esa muvaffaqiyatli tekshiruv ham qurilmaga BORISH edi va
      u NVR ning yukini oshirdi — chegara aynan borishlar sonini
      cheklaydi.

    Raises:
        TooManyAttempts: shu bozor + shu qurilma kesimida chegara oshsa.
    """
    key = f"{_NVR_TEST_KEY}{market_id}:{host}"
    try:
        allowed = await _bump(cache, key, NVR_TEST_LIMIT, NVR_TEST_WINDOW_SECONDS)
    except RedisError as exc:
        # Login yo'lidagi bilan bir xil qaror va bir xil sabab: kesh
        # o'chgani uchun butun onboarding oqimini to'xtatib qo'yish
        # mavjud xizmatni yo'q qiladi. Qoldiq xavf CHEKLANGAN — endpoint
        # `CAMERA_MANAGE` ortida va u faqat autentifikatsiyalangan bozor
        # adminiga ochiq.
        log.warning("nvr_test_rate_limit_unavailable", error=str(exc))
        return
    if not allowed:
        raise TooManyAttempts("nvr_test")


BOT_RESOLVE_LIMIT = 5
"""`POST /internal/bot/resolve` uchun oynadagi urinishlar soni.

⚠ CHEGARA REYESTRNI SANASHNI QIMMAT QILADI, MAHSULOTNI EMAS. Haqiqiy
  sotuvchi kontaktini BIR MARTA yuboradi; ikki-uch urinish (noto'g'ri
  raqam, akkaunt almashtirish) ham normal. Beshdan ko'pi esa endi odam
  xulqi emas.
"""

BOT_RESOLVE_WINDOW_SECONDS = 15 * 60
"""Oyna — login sanagichi bilan bir xil, 15 daqiqa."""

_BOT_RESOLVE_KEY = "rl:bot_resolve:"
"""Kalit shakli — `rl:bot_resolve:<telegram_user_id>`.

⛔ KESIM TELEGRAM AKKAUNTI BO'YICHA, TELEFON BO'YICHA EMAS — va bu farq
   T-07-41 ning bevosita natijasi: telefon raqamini kalitga qo'yish uni
   Valkey'ga (va u yerdan xotira dumpiga) YOZARDI, holbuki bu modulning
   butun ma'nosi mos kelmagan raqamni HECH QAYERGA saqlamaslik.

⚠ Telegram akkaunti hujumchi uchun ARZON emas: yangi `user_id` yangi
  telefon raqamini (SIM) talab qiladi. Ya'ni kesim reyestrni sanash
  narxini akkaunt narxiga bog'laydi.
"""


async def check_bot_resolve_rate(cache: Redis, *, telegram_user_id: int) -> None:
    """Bog'lanish urinishini sanaydi (T-07-40 ning IKKINCHI qatlami).

    ⛔ BIRINCHI QATLAM `binding_repo.resolve()` DA: tsikl HAR DOIM barcha
       faol bozorlarni oxirigacha aylanadi, ya'ni javob vaqti moslikning
       bor-yo'qligini oshkor qilmaydi. Bittasi yolg'iz yetarli emas:
       tayming yopilmasa cheksiz urinish farqni statistik ravishda
       ochardi; rate-limit bo'lmasa esa bozorlar soni o'sganda tsiklning
       O'ZI sezilarli farq berardi.

    ⚠ VALKEY YO'Q BO'LSA URINISH O'TKAZILADI (login yo'li bilan bir xil
      qaror): kesh o'chgani uchun sotuvchilarning ulanishini butunlay
      to'xtatib qo'yish mavjud xizmatni yo'q qiladi. Qoldiq xavf
      CHEKLANGAN — yuza servis tokeni ortida va u tashqi tarmoqdan
      umuman ko'rinmaydi.

    Raises:
        TooManyAttempts: shu Telegram akkaunti kesimida chegara oshsa.
    """
    key = f"{_BOT_RESOLVE_KEY}{telegram_user_id}"
    try:
        allowed = await _bump(cache, key, BOT_RESOLVE_LIMIT, BOT_RESOLVE_WINDOW_SECONDS)
    except RedisError as exc:
        log.warning("bot_resolve_rate_limit_unavailable", error=str(exc))
        return
    if not allowed:
        raise TooManyAttempts("bot_resolve")


async def reset_login_rate(cache: Redis, *, phone: str, ip: str | None) -> None:
    """Muvaffaqiyatli login'dan keyin sanagichlarni tozalaydi.

    Busiz kunduzi parolini bir necha marta noto'g'ri yozgan kassir
    muvaffaqiyatli kirgandan keyin ham oyna tugaguncha chegaraga yaqin
    turardi va navbatdagi bitta xato uni qulflab qo'yardi.
    """
    keys = [_PHONE_KEY + phone]
    if ip:
        keys.append(_IP_KEY + ip)
    try:
        await cache.delete(*keys)
    except RedisError as exc:
        log.warning("login_rate_limit_reset_failed", error=str(exc))
