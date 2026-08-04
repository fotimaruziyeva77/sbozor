"""`alert_events` ustidagi O'QISH yuzasi (`04-UI-SPEC.md` §6.7, D-22).

=============================================================================
⛔ BU MODULDA YOZISH METODI YO'Q VA U ATAYIN SHUNDAY.

Ogohlantirishni YARATADIGAN va YOPADIGAN yagona joy — fon jarayoni
(`app/services/alerts.py`, 04-08). Bu yerda faqat o'qish bor va sabab
mahsulot qoidasida:

  * ogohlantirishni QO'LDA yopish tugmasi qurilmaydi — uni faqat
    TIKLANISH yopadi (`resolved_at` ni sweep qo'yadi). Qo'lda yopish
    adminga muammoni KO'RMASDAN yashirish imkonini berardi va aynan shu
    bosqichda «hammasi yaxshi» ko'rinishi mahsulotning butun mazmunini
    yo'q qilardi;
  * yaratish esa DEBOUNCE mantig'iga tayanadi (`uq_alert_events_market_
    id_alert_key_open` qisman indeksi) va uni HTTP yuzasidan chaqirish
    o'sha mantiqning ikkinchi nusxasini tug'dirardi.

Ya'ni «yozish metodi yo'q» — bu qamrov chegarasi emas, DARVOZA. Regex
darvozasi `app/api/v1/snapshots.py` da `PATCH`/`POST`/`DELETE /alerts`
yo'qligini alohida tekshiradi (T-04-73).
=============================================================================

⚠ `detail` XOM HOLDA QAYTADI va allowlist filtri `app/schemas.py::
  AlertEventOut` da. Repozitoriy jadval qatorini beradi, «UI nimani
  ko'radi» qarorini esa DTO qabul qiladi — aks holda filtr ikki joyda
  yashab, ikkinchi chaqiruvchi uni chetlab o'tardi (T-04-74).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sbozor_core.models import AlertEvent
from sbozor_core.tenancy import TenantScopedRepository
from sqlalchemy import select

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = ["AlertRepository"]


class AlertRepository(TenantScopedRepository):
    """`alert_events` — faqat o'qish (modul docstringi)."""

    async def list_events(self, *, closed: bool) -> Sequence[AlertEvent]:
        """Ochiq (`closed=False`) yoki YOPILGAN (`closed=True`) ogohlantirishlar.

        ⚠ IKKI RO'YXAT BIRLASHTIRILMAYDI. UI ochiqlarni DOIMO ko'rsatadi,
          yopilganlarni esa faqat checkbox yoqilganda (`?closed=1`,
          standart o'chiq). Bitta ro'yxatda kelsa admin o'nlab yopilgan
          qator orasidan ochiqlarini qidirishga majbur bo'lardi va D-22
          ning alert charchashi aynan UI tomonda qaytadi.

        Tartib — `last_seen_at` bo'yicha KAMAYISH: eng so'nggi hodisa
        yuqorida. `first_seen_at` bo'yicha saralash eski, lekin hamon
        davom etayotgan muammoni ro'yxatning tubiga tushirardi.
        """
        predicate = (
            AlertEvent.resolved_at.is_not(None) if closed else AlertEvent.resolved_at.is_(None)
        )
        result = await self.session.execute(
            self.scoped(select(AlertEvent))
            .where(predicate)
            .order_by(AlertEvent.last_seen_at.desc(), AlertEvent.id)
        )
        return list(result.scalars().all())
