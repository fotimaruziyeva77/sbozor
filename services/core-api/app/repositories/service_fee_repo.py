"""Majburiy xizmat haqi (tarozi) — bozor darajasidagi narx tarixi (0027).

=============================================================================
⛔⛔ BU MODULDA `UPDATE` YO'Q VA BO'LMAYDI — `tariff_repo` BILAN AYNI QOIDA.

Yangi narx = YANGI QATOR (D-06); mavjud qatorga tegilmaydi. Yagona
istisno — KELAJAKDAGI qatorni o'chirish (`delete_future`), chunki hali
kuchga kirmagan narx hech qanday hisobga ta'sir qilmagan.

O'tmish `service_fee_past_immutable()` triggeri bilan qulflangan va u
ilova qatlamidan MUSTAQIL: xom SQL yo'li ham qamraladi.

=============================================================================
⛔ `min_valid_from` BU YERDA QAYTA HISOBLANMAYDI.

Ruxsat etilgan eng erta sana `market_profile.operating_since` va bozorning
qoralama holatidan chiqadi — ya'ni u TOIFAGA umuman bog'liq emas va
`TariffRepository.tariff_window()` da ALLAQACHON yechilgan.

Ikkinchi nusxa yozish ikki ekranda ikki xil «eng erta sana» ko'rsatardi va
IKKALASI HAM «to'g'ri» bo'lardi — bu loyihada takroran topilgan «ikki
haqiqat manbai» sinfi. Shuning uchun bu repozitoriy o'sha funksiyani
CHAQIRADI, takrorlamaydi.
=============================================================================
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast
from uuid import UUID

from sbozor_core.models import MarketServiceFee
from sbozor_core.tenancy import TenantScopedRepository
from sqlalchemy import Date, bindparam, delete, insert, text
from sqlalchemy.dialects.postgresql import UUID as _UUID

from app.repositories.tariff_repo import TariffRepository, TariffWindow

if TYPE_CHECKING:
    from datetime import date

    from sqlalchemy import CursorResult
    from sqlalchemy.ext.asyncio import AsyncSession

__all__ = ["ServiceFeeRepository", "ServiceFeeRow"]


@dataclass(frozen=True, slots=True)
class ServiceFeeRow:
    """Xizmat haqi tarixining bitta qatori — `valid_to` HISOBLANGAN holda.

    `valid_to` `None` — OXIRGI qator, ya'ni narx hozircha muddatsiz. DB'da
    bunday ustun YO'Q (voris modeli — `models/market.py` sarlavhasi).
    """

    id: UUID
    amount_soum: int
    label: str
    valid_from: date
    valid_to: date | None


_FEE_ROWS = text(
    """
    SELECT rows.id,
           rows.amount_soum,
           rows.label,
           rows.valid_from,
           rows.valid_to
    FROM (
      SELECT f.id,
             f.amount_soum,
             f.label,
             f.valid_from,
             lead(f.valid_from) OVER (
               PARTITION BY f.market_id
               ORDER BY f.valid_from
             ) AS valid_to
      FROM market_service_fees f
      WHERE f.market_id = :market_id
    ) rows
    WHERE (:fee_id IS NULL OR rows.id = :fee_id)
    ORDER BY rows.valid_from DESC
    """
).bindparams(
    bindparam("market_id", type_=_UUID),
    bindparam("fee_id", type_=_UUID),
)
"""`tariff_repo._TARIFF_ROWS` ning JUFTI — bitta ATAYIN farq bilan.

`PARTITION BY` da `category_id` YO'Q: xizmat haqi BOZORNING narxi, ya'ni
butun bozor uchun bitta uzluksiz tarix. Toifa bo'yicha bo'lish uni
`tariffs` ga aylantirib qo'yardi va `market_service_fees` ning butun
mavjud bo'lish sababini yo'q qilardi (`0027` sarlavhasi).
"""


_CURRENT_FEE = text(
    """
    SELECT f.amount_soum, f.label
      FROM market_service_fees f
     WHERE f.market_id = :market_id
       AND f.valid_from <= :as_of
     ORDER BY f.valid_from DESC
     LIMIT 1
    """
).bindparams(
    bindparam("market_id", type_=_UUID),
    bindparam("as_of", type_=Date()),
)
"""Berilgan kunda AMALDAGI xizmat haqi.

⚠ `billing_repo._STALL_DAY_MONEY` ichidagi `fee` CTE'si bilan AYNI
  mantiq. Ikki nusxa bo'lgani ONGLI va u `occupancy.py` dagi qoidaga ZID
  EMAS: o'sha yerdagi taqiq PUL QARORI (qaysi summa olinadi) uchun, bu
  esa KO'RSATISH so'rovi (tarif ekranidagi «hozirgi qiymat»). Pul qarori
  hamon YAGONA joyda — `resolve_stall_day_money()`.

  ⛔ AGAR bu funksiya bir kun pul yo'liga ulansa, u O'CHIRILISHI va
     chaqiruvchi `resolve_stall_day_money()` ga o'tishi SHART.
"""


class ServiceFeeRepository(TenantScopedRepository):
    """Bozorning majburiy xizmat haqi reyestri (0027)."""

    def __init__(self, session: AsyncSession, market_id: UUID) -> None:
        super().__init__(session, market_id)
        # ⛔ KOMPOZITSIYA, VORISLIK EMAS: bu repozitoriy tarif emas va
        #   `TariffRepository` ning yozuv yuzasini MEROS QILIB OLMAYDI —
        #   undan faqat `tariff_window()` (bozor darajasidagi sana
        #   oynasi) kerak.
        self._tariffs = TariffRepository(session, market_id)

    async def window(self, today: date) -> TariffWindow:
        """Ruxsat etilgan eng erta `valid_from` — `tariff_repo` dan (modul izohi)."""
        return await self._tariffs.tariff_window(today)

    def is_valid_from_allowed(self, valid_from: date, window: TariffWindow, today: date) -> bool:
        """`TariffRepository` dagi qoidaning AYNAN o'zi — takrorlanmaydi."""
        return self._tariffs.is_valid_from_allowed(valid_from, window, today)

    async def list_rows(self) -> list[ServiceFeeRow]:
        """Butun tarix — yangisidan eskisiga."""
        result = await self.session.execute(
            _FEE_ROWS, {"market_id": self.market_id, "fee_id": None}
        )
        return [
            ServiceFeeRow(
                id=row.id,
                amount_soum=row.amount_soum,
                label=row.label,
                valid_from=row.valid_from,
                valid_to=row.valid_to,
            )
            for row in result
        ]

    async def get(self, fee_id: UUID) -> ServiceFeeRow | None:
        """Bitta qator — `valid_to` BUTUN tarix ustida hisoblanadi."""
        result = await self.session.execute(
            _FEE_ROWS, {"market_id": self.market_id, "fee_id": fee_id}
        )
        row = result.first()
        if row is None:
            return None
        return ServiceFeeRow(
            id=row.id,
            amount_soum=row.amount_soum,
            label=row.label,
            valid_from=row.valid_from,
            valid_to=row.valid_to,
        )

    async def current(self, as_of: date) -> tuple[int, str] | None:
        """Berilgan kunda amaldagi (summa, nom) yoki `None` — belgilanmagan."""
        result = await self.session.execute(
            _CURRENT_FEE, {"market_id": self.market_id, "as_of": as_of}
        )
        row = result.first()
        return None if row is None else (int(row.amount_soum), str(row.label))

    async def add(
        self,
        *,
        amount_soum: int,
        label: str,
        valid_from: date,
    ) -> UUID:
        """YANGI qator (D-06 — hech qanday mavjud qator o'zgarmaydi).

        ⛔ Chaqiruvchi `valid_from` ni `window()` bilan ALLAQACHON
           tekshirgan bo'lishi shart — bu yerda takroriy tekshiruv YO'Q
           (`tariff_repo.add_tariff()` dan FARQ: u oynani o'zi oladi).
           Sabab: marshrut oynani javobda ham qaytaradi, ya'ni uni ikki
           marta so'rash bitta HTTP so'rovida ikkita bir xil `SELECT`
           bo'lardi.
        """
        result = await self.session.execute(
            insert(MarketServiceFee)
            .values(
                # ⛔ `market_id` `self.market_id` DAN — so'rov tanasidan
                #   EMAS (T-02-54 mass-assignment darvozasi).
                market_id=self.market_id,
                amount_soum=amount_soum,
                label=label,
                valid_from=valid_from,
            )
            .returning(MarketServiceFee.id)
        )
        return result.scalar_one()

    async def delete_future(self, fee_id: UUID) -> bool:
        """KELAJAKDAGI qatorni o'chiradi; topilmasa `False` (-> 404).

        ⛔ «Kelajak» sharti BU YERDA TEKSHIRILMAYDI — `service_fee_past_
           immutable()` triggeri uni `23514` bilan rad etadi va marshrut
           o'sha SQLSTATE ni 403 ga o'giradi. Ilova qatlamida takroriy
           shart yozish ikki manba yaratardi va ular biri ikkinchisidan
           bir kun ilgarilab ketardi (`tariff_repo.delete_future()`
           bilan AYNI qaror).
        """
        result = await self.session.execute(
            delete(MarketServiceFee).where(
                MarketServiceFee.market_id == self.market_id,
                MarketServiceFee.id == fee_id,
            )
        )
        # ⚠ `rowcount` `CursorResult` da yashaydi; `session.execute()` ning
        #   e'lon qilingan qaytish tipi esa `Result` — DML uchun u ish
        #   vaqtida HAR DOIM `CursorResult` bo'ladi, lekin mypy buni
        #   bilmaydi. `cast` — SQLAlchemy 2.0 da bu holatning odatiy
        #   yechimi (`stall_repo.plan_write()` da ham aynan shunday).
        return bool(cast("CursorResult[Any]", result).rowcount)
