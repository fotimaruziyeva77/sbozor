"""Ish kunlari kalendari — haftalik jadval va istisno kunlar (MARKET-05, D-17/D-18).

=============================================================================
BU MODUL `market_is_open()` NI CHAQIRMAYDI — U UNGA MA'LUMOT YOZADI.

SC#4 ning butun qarori BITTA DB funksiyasida (`market_is_open(market_id,
date)`) va 6-faza unga BITTA shart sifatida murojaat qiladi. Shu yerda
`open_weekdays` yoki istisnolar ustida ikkinchi "ochiqmi?" mantig'i
yozilsa, u bir kun DB funksiyasidan ajralib ketardi va ikki javob
bir-biriga zid bo'lardi: ekran "ochiq" deb ko'rsatib turgan kunga hisob
yozilmasdi (yoki aksincha).

Shuning uchun bu repozitoriy FAQAT xom faktlarni qaytaradi: haftalik
jadval massivi va istisno qatorlari. Talqin — `market_is_open()` da.
=============================================================================

AUDIT DB-TRIGGERDA: `market_profile` ham, `market_calendar_exceptions` ham
`AUDITED_TABLES` da (02-05/02-06). Ya'ni oddiy `UPDATE`/`INSERT`/`DELETE`
o'zi audit qatorini tug'diradi va app-qatlam yozuvi qo'shilsa jurnalda
IKKITA qator paydo bo'lardi.

TENANT FILTRI IKKI QATLAM (RESEARCH Pattern 1): RLS policy'si himoya to'ri,
`scoped()` esa aniq `market_id` predikati.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import UUID

from sbozor_core.models import MarketCalendarException, MarketProfile
from sbozor_core.tenancy import TenantScopedRepository
from sqlalchemy import delete, insert, select, update

from app.repositories.stall_repo import MarketProfileMissingError

if TYPE_CHECKING:
    from datetime import date

__all__ = [
    "CalendarExceptionRow",
    "CalendarProfileRow",
    "CalendarRepository",
]


@dataclass(frozen=True)
class CalendarProfileRow:
    """Bozor profilining kalendarga tegishli qismi.

    `id` javobda QAYTARILMAYDI — u faqat audit qatorini test qilish va
    kelajakdagi `row_id` havolalari uchun kerak. Profil bozorga BITTA
    (`uq_market_profile_market_id`), ya'ni klient uchun uning
    identifikatori hech qanday ma'no bermaydi.
    """

    id: UUID
    open_weekdays: list[int]
    """Bo'sh ro'yxat = "hali tanlanmagan" (ustunda `NULL`), `profile()` ga qarang."""


@dataclass(frozen=True)
class CalendarExceptionRow:
    """Haftalik jadvaldan chiqadigan bitta kun (D-18).

    `is_open` IKKI TOMONLAMA: `false` — bayram/yopiq kun, `true` —
    jadvalda dam olish bo'lgan, lekin ISHLAYDIGAN kun.
    """

    id: UUID
    exception_date: date
    is_open: bool
    note: str | None


class CalendarRepository(TenantScopedRepository):
    """`market_profile.open_weekdays` + `market_calendar_exceptions`."""

    async def profile(self) -> CalendarProfileRow:
        """Bozorning haftalik jadvali; HALI TANLANMAGAN bo'lsa `[]`.

        ⚠ `open_weekdays` USTUNI `NULL` BO'LISHI MUMKIN (0011,
        `0011_weekday_choice`): `market_create()` endi ish rejimini
        taxmin qilmaydi va usta 1-qadamidan tashqari yo'ldan (seed,
        migratsiya, qo'lda `INSERT`) tug'ilgan bozorda ustun `NULL`
        qoladi. Usiz bu yerdagi `list(...)` `TypeError` bilan yiqilib,
        `GET /calendar` 500 berardi.

        `NULL` -> `[]` XARITASI ENDI NOANIQ EMAS va aynan shu sabab u
        xavfsiz: `'{}'` (bo'sh massiv) `ck_market_profile_open_weekdays_valid`
        bilan TAQIQLANGAN, ya'ni javobdagi bo'sh ro'yxat FAQAT bitta
        ma'noni tashiydi — "jadval hali tanlanmagan". Klient (7-qadamdagi
        `WeekdayPicker`) uni belgisiz katakchalar bilan ko'rsatadi va
        `PUT /calendar/weekdays` bilan tanlovni yozadi.

        Profil QATORINING O'ZI yo'qligi esa boshqa holat va u istisno
        bilan qoladi (pastda).

        Raises:
            MarketProfileMissingError: profil qatori yo'q bo'lsa ->
                router 409 `market_incomplete`. Bu "jadval tanlanmagan"
                dan FARQLI: qator yo'q bo'lsa yoziladigan joy ham yo'q,
                ya'ni `PUT /calendar/weekdays` ham `None` qaytarardi va
                bo'sh ro'yxat foydalanuvchini ishlamaydigan ekranga
                qamab qo'yardi.
        """
        result = await self.session.execute(
            self.scoped(select(MarketProfile.id, MarketProfile.open_weekdays))
        )
        row = result.one_or_none()
        if row is None:
            raise MarketProfileMissingError(f"market_profile topilmadi: {self.market_id}")
        return CalendarProfileRow(id=row.id, open_weekdays=list(row.open_weekdays or ()))

    async def set_weekdays(self, open_weekdays: list[int]) -> UUID | None:
        """Haftalik jadvalni yozadi; profil qatori yo'q bo'lsa `None`.

        `UPDATE ... RETURNING` ikki ishni birga bajaradi: "bor edimi?"
        savoliga javob beradi va yozadi (`ZoneRepository.rename()` naqshi).

        AUDIT QATORINI SHU `UPDATE` NING O'ZI TUG'DIRADI — trigger
        `old`/`new` farqini hisoblaydi va `changed_keys` ga
        `open_weekdays` ni qo'yadi. Ilova tomonidan qo'shimcha yozuv
        KERAK EMAS va u jurnalni ikkilantirardi.
        """
        result = await self.session.execute(
            update(MarketProfile)
            .where(MarketProfile.market_id == self.market_id)
            .values(open_weekdays=open_weekdays)
            .returning(MarketProfile.id)
        )
        return result.scalar_one_or_none()

    async def list_exceptions(self, *, since: date, limit: int) -> list[CalendarExceptionRow]:
        """Istisnolar — sanasi KAMAYISH tartibida, `since` dan boshlab.

        ⚠ `since` YUQORI chegara QO'YMAYDI: kelajakdagi bayramlar (jumladan
        keyingi yilning yanvari — dekabrda belgilanadigan odatiy holat)
        ro'yxatda QOLADI. Kesiladigani faqat OLDINGI yillar, ya'ni ekran
        yildan-yilga o'sib boradigan tarixni ko'tarib yurmaydi.

        `limit` — T-02-68: chegarasiz so'rov butun tarixni bitta JSON'ga
        aylantirardi. Kursor mexanikasi ATAYIN yo'q: bir bozorda yiliga
        o'nlab istisno bo'ladi, ya'ni sahifalash hech qanday muammoni hal
        qilmasdi.
        """
        result = await self.session.execute(
            self.scoped(
                select(
                    MarketCalendarException.id,
                    MarketCalendarException.exception_date,
                    MarketCalendarException.is_open,
                    MarketCalendarException.note,
                )
                .where(MarketCalendarException.exception_date >= since)
                .order_by(MarketCalendarException.exception_date.desc())
                .limit(limit)
            )
        )
        return [
            CalendarExceptionRow(
                id=row.id,
                exception_date=row.exception_date,
                is_open=row.is_open,
                note=row.note,
            )
            for row in result
        ]

    async def add_exception(
        self,
        *,
        exception_date: date,
        is_open: bool,
        note: str | None,
    ) -> UUID:
        """Yangi istisno. Takroriy sana `IntegrityError` (`23505`) ko'taradi.

        `market_id` `self.market_id` DAN — so'rov tanasidan EMAS
        (T-02-54, mass-assignment darvozasi).
        """
        result = await self.session.execute(
            insert(MarketCalendarException)
            .values(
                market_id=self.market_id,
                exception_date=exception_date,
                is_open=is_open,
                note=note,
            )
            .returning(MarketCalendarException.id)
        )
        return result.scalar_one()

    async def delete_exception(self, exception_id: UUID) -> bool:
        """Istisnoni o'chiradi; topilmasa (yoki begona bozorniki bo'lsa) `False`.

        O'CHIRISH IZ QOLDIRADI: `trg_audit_market_calendar_exceptions`
        `DELETE` ni ham qamraydi (T-02-40). Istisnoni qo'yib, kun o'tgach
        uni o'chirib tashlash izni yo'qotishning eng oddiy usuli bo'lardi.
        """
        result = await self.session.execute(
            delete(MarketCalendarException)
            .where(
                MarketCalendarException.market_id == self.market_id,
                MarketCalendarException.id == exception_id,
            )
            .returning(MarketCalendarException.id)
        )
        return result.scalar_one_or_none() is not None
