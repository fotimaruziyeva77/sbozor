"""Test seed'lari va umumiy fixture tiplari.

`tests/conftest.py` bu paketdan import qiladi; seed mantiqi conftest ichida
emas, shu yerda yashaydi — conftest fixture'lar REYESTRI bo'lib qolsin,
ma'lumot fabrikasi emas.
"""

from __future__ import annotations

from collections.abc import Coroutine
from contextlib import AbstractAsyncContextManager
from typing import Any, Protocol
from uuid import UUID

from sbozor_core.enums import ActorKind
from sqlalchemy.ext.asyncio import AsyncSession

from fixtures.market_domain import (
    MarketDomainRows,
    MarketDomainSeed,
    cleanup_market_domain,
    seed_market_domain,
)

__all__ = [
    "MarketDomainRows",
    "MarketDomainSeed",
    "TenantSessionFactory",
    "TokenFactory",
    "cleanup_market_domain",
    "seed_market_domain",
]


class TenantSessionFactory(Protocol):
    """`tenant_session(market_id)` — kontekst o'rnatilgan sessiya beradi.

    Ochilgan sessiya TRANZAKSIYA ICHIDA bo'ladi: `set_config(..., true)`
    tranzaksiya oxirida qiymatni tark etadi, ya'ni kontekst tranzaksiyasiz
    umuman o'rnatilmaydi (`sbozor_core.tenancy` buni `RuntimeError` bilan
    rad etadi).

    `actor_kind` va `request_id` — audit testlari uchun (01-05): audit
    qatorini `fn_audit_row()` triggeri AYNAN shu GUC'lardan to'ldiradi,
    shuning uchun ular test tomondan boshqarilishi kerak. Ular alohida
    fixture'ga ajratilmagan: kontekst BITTA operatorda o'rnatiladi
    (`SET_TENANT_CONTEXT`) va uni ikkiga bo'lish prod yo'lidan farq qilardi.
    """

    def __call__(
        self,
        market_id: UUID | None,
        actor_id: UUID | None = None,
        *,
        actor_kind: ActorKind = ActorKind.USER,
        request_id: str = "pytest",
    ) -> AbstractAsyncContextManager[AsyncSession]: ...


class TokenFactory(Protocol):
    """`token_for(phone, password, market_id)` — HAQIQIY access token beradi.

    Imzo rejadagi `token_for(user_id, market_id, roles)` dan farq qiladi
    va bu ATAYIN: rollar chaqiruvchidan EMAS, bazadagi a'zolik qatoridan
    keladi. Rollarni argument sifatida qabul qilish "kassir tokeni
    `market_admin` rollari bilan" kabi BAZADA MAVJUD BO'LMAGAN holatni
    yasashga imkon berardi — matritsa esa o'shanda haqiqiy tizimni emas,
    o'zi o'ylab topgan tizimni sinardi.
    """

    def __call__(
        self,
        phone: str,
        password: str,
        market_id: UUID | None = None,
    ) -> Coroutine[Any, Any, str]: ...
