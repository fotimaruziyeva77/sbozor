"""`occupancy_events` ga OMMAVIY yozuv — idempotentlik SXEMAGA tayanadi.

=============================================================================
⛔ OLDINDAN TEKSHIRILMAYDI — POYGA BAZAGA TOPSHIRILADI.

Falsafa manbai `core-api/app/repositories/nvr_repo.py:509-517` va §S-6: «bu
qator bormi?» degan `SELECT` dan keyin `INSERT` qilish poyga oynasini
ochadi va u oyna AYNAN takroriy ishga tushirishda — ya'ni bu jadval uchun
eng ehtimolli holatda — yopiladi.

Idempotentlik `0018` dagi

    UNIQUE (market_id, snapshot_id, camera_zone_id, model_version)

ga TAYANADI va uni TAKRORLAMAYDI. `ON CONFLICT DO NOTHING` shu indeksni
nomma-nom ko'rsatadi: `index_elements` siz konflikt HAR QANDAY unikal
konstraytda yutilardi — shu jumladan `uq_occupancy_events_market_id_id`
(ya'ni `id` to'qnashuvi) da ham, va bu KODDAGI xatoni jimgina yashirardi.

=============================================================================
⚠ `business_date` VA `slot_time` `snapshots` DAN NUSXALANADI.

Ular bu yerda MUSTAQIL HISOBLANMAYDI va buning sababi Pitfall 3: ikki
mustaqil hisoblash manbai yarim tunda bir kun farq qilardi — kadr
`snapshots` da 09-01 ga, dalil esa 09-02 ga tushardi va 6-faza uni
«yo'q» deb ko'rardi. Chaqiruvchi (`jobs/detect.py`) qiymatlarni
tranzaksiya ICHIDA o'qib beradi.

=============================================================================
⚠ `snapshot_is_billable` BU YERDA YOZILMAYDI VA BU ATAYIN.

Ustunning `DEFAULT true` i bor (`models/occupancy.py`), `CHECK` esa
boshqa qiymatni rad etadi. Ya'ni D-21 langari «eslab qolinadigan» narsaga
aylanmaydi: yozuvchi uni umuman bilmasa ham kompozit FK
(`snapshot_id, snapshot_is_billable) -> snapshots (id, is_billable)`)
yaroqsiz kadrga havolani RAD ETADI.
=============================================================================
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Final

import structlog
from sbozor_core.models.occupancy import OccupancyEvent
from sbozor_core.tenancy import TenantScopedRepository
from sqlalchemy.dialects.postgresql import insert as pg_insert

if TYPE_CHECKING:
    from collections.abc import Sequence
    from datetime import date, time
    from uuid import UUID

__all__ = ["CONFIDENCE_EXPONENT", "OccupancyWriter", "ZoneEvent"]

log = structlog.get_logger(__name__)

CONFIDENCE_EXPONENT: Final = Decimal("0.0001")
"""`occupancy_events.confidence` — `numeric(5, 4)`, ya'ni AYNAN 4 kasr xona.

⚠ YAXLITLASH `Decimal.quantize` BILAN, `float` ARIFMETIKASI BILAN EMAS.
  `float` dan to'g'ridan-to'g'ri qurilgan `Decimal` (`Decimal(0.1)`)
  ikkilik yaqinlashtirishning butun dumini olib keladi
  (`0.1000000000000000055511151231257827…`) va `asyncpg` uni
  `numeric(5,4)` ga sig'dira olmay YIQILARDI — ya'ni nosozlik ZONA
  VERDIKTIDAN emas, sonli tasvirdan kelardi.

⚠ YAXLITLASH REJIMI — `ROUND_HALF_EVEN` (`Decimal` ning standarti) va u
  05-07 dagi `np.rint` bilan AYNAN BIR XIL. Ikki modul ikki xil
  yaxlitlasa `0.12345` chegara qiymati bir joyda `0.1234`, boshqasida
  `0.1235` bo'lardi va `uncertain` oynasining cheti oldindan aytib
  bo'lmaydigan holga kelardi (05-06 ning darsi: «lossless» va «mijoz
  kabi yaxlitlaydi» — IKKI BOSHQA xususiyat).
"""


@dataclass(frozen=True, slots=True)
class ZoneEvent:
    """Bitta zona uchun bitta modelning javobi — YOZILADIGAN qiymatlar.

    ⚠ ORM OBYEKTI EMAS, ODDIY QIYMATLAR (`discovery.py::_DeviceContext`
      naqshi): qiymatlar tranzaksiya ichida quriladi va undan keyin
      hech qanday DB yo'li qolmaydi.
    """

    camera_zone_id: UUID
    zone_version: int
    verdict: str
    confidence: float


class OccupancyWriter(TenantScopedRepository):
    """`occupancy_events` ga BITTA ommaviy `INSERT` — boshqa metod yo'q.

    ⚠ `UPDATE` VA `DELETE` METODLARI UMUMAN YO'Q va bu yuza qarori
      `services/storage.py` nikining aynan o'zi. `0018` jadvalga
      SHARTSIZ `BEFORE UPDATE OR DELETE` qo'riqchisini ulagan (D-12),
      ya'ni bunday metod yozilsa u DB darajasida yiqilardi — lekin
      YOZILGANIGA qarab keyingi o'quvchi «demak tahrirlash mumkin ekan»
      degan xulosa chiqarardi.
    """

    async def record(
        self,
        events: Sequence[ZoneEvent],
        *,
        snapshot_id: UUID,
        business_date: date,
        slot_time: time,
        model_version: str,
        thresholds_version: int,
    ) -> int:
        """Hodisalarni bitta `INSERT ... ON CONFLICT DO NOTHING` bilan yozadi.

        Args:
            events: zona hodisalari. BO'SH ro'yxat QONUNIY — u «bu kamerada
                faol zona yo'q» degan holatni bildiradi va u XATO EMAS
                (D-22 ning `no_coverage` manbai).
            snapshot_id: dalil qaysi kadrga tegishli.
            business_date: `snapshots` qatoridan NUSXALANGAN.
            slot_time: `snapshots` qatoridan NUSXALANGAN.
            model_version: kalitning bir qismi — raqobatlashuvchi model
                O'Z qatorini yozadi, eskisini o'chirmaydi.
            thresholds_version: qaysi chegara to'plami bilan hukm
                qilingani (D-11).

        Returns:
            HAQIQATAN yozilgan qatorlar soni. Takroriy ishga tushirishda
            u `0` bo'ladi va bu MUVAFFAQIYAT, xato emas.
        """
        if not events:
            return 0

        rows: list[dict[str, Any]] = [
            {
                "market_id": self.market_id,
                "snapshot_id": snapshot_id,
                "camera_zone_id": event.camera_zone_id,
                "business_date": business_date,
                "slot_time": slot_time,
                "verdict": event.verdict,
                "confidence": Decimal(repr(event.confidence)).quantize(CONFIDENCE_EXPONENT),
                "model_version": model_version,
                "thresholds_version": thresholds_version,
                "zone_version": event.zone_version,
            }
            for event in events
        ]

        statement = (
            pg_insert(OccupancyEvent)
            .values(rows)
            .on_conflict_do_nothing(
                # ⚠ INDEKS NOMMA-NOM: `index_elements` siz konflikt HAR
                #   QANDAY unikal konstraytda yutilardi (modul docstringi).
                index_elements=["market_id", "snapshot_id", "camera_zone_id", "model_version"],
            )
            # ⚠ `RETURNING` — `rowcount` EMAS. `ON CONFLICT DO NOTHING`
            #   ostida `RETURNING` AYNAN yozilgan qatorlarni beradi, ya'ni
            #   sanoq drayver xulqiga (va uning `rowcount` talqiniga)
            #   bog'lanmaydi. Takroriy ishga tushirishda u BO'SH bo'ladi.
            .returning(OccupancyEvent.id)
        )
        inserted = (await self.session.execute(statement)).scalars().all()
        return len(inserted)
