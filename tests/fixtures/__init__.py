"""Test seed'lari va umumiy fixture tiplari.

`tests/conftest.py` bu paketdan import qiladi; seed mantiqi conftest ichida
emas, shu yerda yashaydi — conftest fixture'lar REYESTRI bo'lib qolsin,
ma'lumot fabrikasi emas.
"""

from __future__ import annotations

from contextlib import AbstractAsyncContextManager
from typing import Protocol
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

__all__ = ["TenantSessionFactory"]


class TenantSessionFactory(Protocol):
    """`tenant_session(market_id)` — kontekst o'rnatilgan sessiya beradi.

    Ochilgan sessiya TRANZAKSIYA ICHIDA bo'ladi: `set_config(..., true)`
    tranzaksiya oxirida qiymatni tark etadi, ya'ni kontekst tranzaksiyasiz
    umuman o'rnatilmaydi (`sbozor_core.tenancy` buni `RuntimeError` bilan
    rad etadi).
    """

    def __call__(
        self,
        market_id: UUID | None,
        actor_id: UUID | None = None,
    ) -> AbstractAsyncContextManager[AsyncSession]: ...
