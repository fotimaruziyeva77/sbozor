"""Vaqt primitivlari — Asia/Tashkent biznes-kuni (FOUND-05).

=============================================================================
QAMROV OGOHLANTIRISHI — `business_date()` YOZISH YO'LIDA ISHLATILMAYDI.

DB'da `business_date` — hisoblanadigan ustun:

    business_date date GENERATED ALWAYS AS
      ((created_at AT TIME ZONE 'Asia/Tashkent')::date) STORED

ya'ni u yozuv paytida BIR MARTA hisoblanadi va hech qachon drift qilmaydi.
Bu yerdagi funksiya faqat hisobot filtrlari, kod-qatlamidagi taqqoslash va
testlar uchun. Yozishda uni takrorlash ikkita haqiqat manbai yaratadi —
va ular aynan yarim tun atrofida bir kun farq qiladi (Anti-Pattern 10).
=============================================================================

Konteynerlar UTC soatida ishlaydi. Toshkent — UTC+5, yozgi vaqt YO'Q, lekin
mahalliy 00:00–04:59 oralig'idagi har bir yozuv naive UTC sanasida OLDINGI
kunga tushadi (Pitfall 6). Shuning uchun naive `datetime` bu yerda xato
bilan rad etiladi — jimgina noto'g'ri javob berishdan ko'ra to'xtash yaxshi.
"""

from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

__all__ = ["MARKET_TZ", "business_date", "now_tz"]

# `tzdata` paketi bog'liqlik sifatida o'rnatilgan: slim Debian image'da tizim
# zoneinfo bazasi YO'Q va busiz bu satr `ZoneInfoNotFoundError` beradi.
MARKET_TZ: ZoneInfo = ZoneInfo("Asia/Tashkent")


def now_tz() -> datetime:
    """Hozirgi payt — bozor mintaqasida, HAR DOIM aware.

    `datetime.now()` (naive) ni loyihada ishlatmang: u konteyner soatiga
    (UTC) bog'lanadi va `TZ` muhit o'zgaruvchisiga tayanadi.
    """
    return datetime.now(MARKET_TZ)


def business_date(moment: datetime) -> date:
    """Berilgan paytning qaysi BIZNES-KUNGA tegishli ekanini qaytaradi.

    Kun chegarasi — Toshkent devor-soati bo'yicha yarim tun (MVP'da siljish
    yo'q). Kirish istalgan mintaqada bo'lishi mumkin: u avval Toshkentga
    o'giriladi, keyin sanasi olinadi.

    Raises:
        ValueError: `moment` naive (mintaqasiz) bo'lsa. Naive datetime
            TAQIQLANGAN — u yarim tundan keyingi besh soatni oldingi kunga
            yozib qo'yadi va bu xato faqat nizo paytida ko'rinadi.
    """
    if moment.tzinfo is None or moment.tzinfo.utcoffset(moment) is None:
        raise ValueError(
            "business_date() aware datetime talab qiladi (mintaqasiz qiymat "
            f"berilgan: {moment!r}). Toshkent yarim tunidan keyingi yozuvlar naive "
            "UTC sanasida oldingi kunga tushadi — shuning uchun bu holat xato."
        )
    return moment.astimezone(MARKET_TZ).date()
