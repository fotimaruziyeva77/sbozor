"""Sotuvchi biriktirish davri — `[)` chegara konventsiyasining YAGONA manbai.

=============================================================================
LOYIHADA BITTA KONVENTSIYA BOR: `[)` — quyi chegara KIRADI, yuqori chegara
KIRMAYDI. Xom `Range(...)` yoki SQL `daterange(...)` chaqiruvi yozish yo'lida
BOSHQA HECH QAYERDA yozilmaydi (RESEARCH Pitfall 10).

Nima uchun bu shunchalik qattiq: `daterange` sukut bo'yicha `'[)'` ishlatadi,
lekin `'[]'` ham bir xil darajada yozish mumkin bo'lgan shakl. Ikkalasi bitta
kod bazasida yashasa, almashinuv KUNIDA ikkita sotuvchi bir vaqtda
biriktirilgan bo'lib chiqadi — yoki `ex_stall_assignments_no_overlap`
konstrayti kutilmaganda yiqiladi (chegaraviy kun ikkala davrga tegishli
bo'lgani uchun `&&` rost beradi).

D-10 KONTRAKTI — ALMASHINUV KUNI YANGI SOTUVCHIGA TEGISHLI:

    [2026-08-01, 2026-08-10)   ->  eski sotuvchi:  ... 08-08, 08-09
    [2026-08-10, ∞)            ->  yangi sotuvchi: 08-10, 08-11, ...

Ya'ni 08-10 kunidagi patta YANGI sotuvchiga yoziladi va eski sotuvchining
qarzi o'sha kunga kelib to'xtaydi (D-10: qarz eski sotuvchida QOLADI, lekin
YANGI kunlar unga yozilmaydi).

D-11 BO'SHLIG'I ATAYIN MUMKIN: `[08-01, 08-05)` va `[08-20, ∞)` orasidagi
kunlarda hech kim biriktirilmagan. Bu xato emas — "sotuvchisiz band rasta"
anomaliyasi, 6-faza uni aynan shu bo'shliq orqali topadi. Shuning uchun
davrlar uzluksizligi bu yerda MAJBURLANMAYDI.
=============================================================================

YOZISH YO'LI: `assignment_period()` -> `StallAssignment.period`.
O'QISH YO'LI: DB `@>` operatori (`StallAssignment.period.contains(day)`),
chunki filtrlash GiST indeksidan foydalanishi kerak. `period_contains()` esa
faqat testlar va kod-qatlamidagi hisobot yig'ish uchun.
"""

from __future__ import annotations

from datetime import date
from typing import Final, Literal

from sqlalchemy.dialects.postgresql import Range

__all__ = ["PERIOD_BOUNDS", "assignment_period", "period_contains"]

PERIOD_BOUNDS: Final[Literal["[)"]] = "[)"
"""Loyihadagi YAGONA davr chegarasi shakli.

Konstanta sifatida ochiq turadi, chunki uni migratsiya izohlari, testlar va
6-faza hisob-kitobi bir xil qiymatga tayanib tekshiradi. Uni o'zgartirish
mavjud `stall_assignments` qatorlarining MA'NOSINI o'zgartiradi (chegaraviy
kun boshqa sotuvchiga o'tadi), ya'ni bu migratsiya talab qiladigan qaror.

Tipi `Literal["[)"]` — oddiy `str` EMAS va bu ataylab: `Range.bounds`
`Literal['()', '[)', '(]', '[]']` kutadi, ya'ni konstantaga boshqa qiymat
berish `mypy` da AYNAN shu satrda to'xtaydi. `Final[str]` bo'lganda esa
konvensiyani o'zgartirish tip tekshiruvidan jimgina o'tib ketardi.
"""


def assignment_period(start: date, end: date | None) -> Range[date]:
    """`[start, end)` davrini quradi — `end` KUNI yangi sotuvchiga tegishli (D-10).

    Chiqadigan shakl — `Range(start, end, bounds="[)")`, DB tomonda esa
    `daterange(start, end, '[)')`. Chaqiruvchi bu shaklni O'ZI qurmaydi:
    chegara harfi faqat shu funksiyada va `PERIOD_BOUNDS` da yashaydi.

    Args:
        start: davr boshlanadigan kun — davrga KIRADI.
        end: davr tugaydigan kun — davrga KIRMAYDI. `None` bo'lsa davr
            ochiq oxirli (sotuvchi hali ishlayapti).

    Raises:
        ValueError: `end` `start` dan keyin kelmasa. Postgres `[a, a)` ni
            BO'SH davr deb qabul qiladi va bo'sh davr `&&` bilan hech narsa
            bilan kesishmaydi — ya'ni `ex_stall_assignments_no_overlap`
            konstrayti uni to'xtatmaydi va rastada JIMGINA "sotuvchisi bor,
            lekin hech qaysi kunda emas" qatori paydo bo'ladi. Teskari davr
            (`end < start`) esa DB darajasida `range_bounds_invalid` xatosi
            bo'lib chiqadi, lekin u so'rov bajarilgan paytda — validatsiya
            chegarasidan ancha keyin — ko'rinadi.
    """
    if end is not None and end <= start:
        raise ValueError(
            "assignment_period(): davr oxiri boshidan KEYIN bo'lishi shart "
            f"(start={start.isoformat()}, end={end.isoformat()}). Bir kunlik "
            "biriktirish uchun `end` ni ERTASI kuniga qo'ying — `[)` "
            "konventsiyasida yuqori chegara davrga kirmaydi."
        )
    return Range(start, end, bounds=PERIOD_BOUNDS)


def period_contains(period: Range[date], day: date) -> bool:
    """`day` shu davrga kiradimi — chegara semantikasi bilan.

    Yozish/filtrlash yo'lida ISHLATILMAYDI: u yerda DB `@>` operatori kerak
    (GiST indeksi aynan shuni qamraydi). Bu funksiya testlar va DB'dan
    allaqachon o'qib olingan qatorlar ustidagi hisobot yig'ish uchun.

    Chegara arifmetikasi QO'LDA yozilmaydi — `Range.contains()` ga topshiriladi.
    `day >= lower and (upper is None or day < upper)` shaklidagi qo'lda
    yozilgan variant `bounds` ni UMUMAN o'qimaydi: kimdir bir kun `'[]'` li
    davr qursa, u jimgina noto'g'ri javob berardi va aynan almashinuv kunida
    (ya'ni eng qimmat holatda) xato qilardi.
    """
    return period.contains(day)
