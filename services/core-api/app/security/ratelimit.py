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
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog
from redis.exceptions import RedisError

if TYPE_CHECKING:
    from redis.asyncio import Redis

__all__ = [
    "IP_LIMIT",
    "PHONE_LIMIT",
    "WINDOW_SECONDS",
    "TooManyAttempts",
    "check_login_rate",
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


class TooManyAttempts(Exception):
    """Chegara oshdi — endpoint buni `429 too_many_attempts` ga aylantiradi."""

    def __init__(self, scope: str) -> None:
        super().__init__(f"login rate limit exceeded: {scope}")
        self.scope = scope


async def _bump(cache: Redis, key: str, limit: int) -> bool:
    """Sanagichni oshiradi; chegara oshgan bo'lsa `False` qaytaradi.

    `INCR` + birinchi urinishda `EXPIRE` — ikkalasi bitta pipeline'da,
    ya'ni `INCR` bajarilib `EXPIRE` yiqilgan holatda kalit MANGU qolib
    ketmaydi (o'shanda foydalanuvchi butunlay qulflanardi).
    """
    async with cache.pipeline(transaction=True) as pipe:
        pipe.incr(key)
        pipe.expire(key, WINDOW_SECONDS, nx=True)
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
