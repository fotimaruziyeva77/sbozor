"""`CoreClient` ning soxtasi — chaqiruvlarni SANAYDI (BOT-01 darvozasi).

⛔ Sanoq shu yerda tug'iladi va bu tasodifiy emas: `test_binding.py` ning
uchala rad etish testi «`core.resolve` CHAQIRILMADI» degan da'voni
o'lchaydi. Da'vo faqat sanagich bo'lganda o'lchanadi — «javob neytral
edi» tekshiruvi uni ALMASHTIRMAYDI, chunki chaqiruv qilingan va javob
baribir neytral bo'lgan holat ham mavjud (va u aynan taqiqlangan holat:
u `core-api` da rate-limit sanagichini oshirardi).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID

from app.core_client import (
    CoreApiError,
    MarketSummary,
    PaymentsPage,
    ResolveResult,
    VendorSummary,
)

if TYPE_CHECKING:
    from datetime import date

MARKET_ID = UUID("11111111-1111-4111-8111-111111111111")
VENDOR_ID = UUID("22222222-2222-4222-8222-222222222222")


class CoreDouble:
    """Chaqiruvlarni sanaydigan va oldindan berilgan javobni qaytaradigan soxta."""

    def __init__(
        self,
        *,
        resolve_result: ResolveResult | None = None,
        summary: VendorSummary | None = None,
        pages: list[PaymentsPage] | None = None,
        raises: Exception | None = None,
    ) -> None:
        self.resolve_calls: list[dict[str, Any]] = []
        self.summary_calls: list[int] = []
        self.payments_calls: list[dict[str, Any]] = []
        self._resolve_result = resolve_result
        self._summary = summary
        self._pages = list(pages or [])
        self._raises = raises

    async def resolve(self, *, telegram_user_id: int, raw_phone: str) -> ResolveResult:
        self.resolve_calls.append({"telegram_user_id": telegram_user_id, "raw_phone": raw_phone})
        if self._raises is not None:
            raise self._raises
        assert self._resolve_result is not None, (
            "⛔ `core.resolve` CHAQIRILDI, lekin bu soxtaga javob sozlanmagan — "
            "ya'ni test uni CHAQIRILMASLIGI kerak deb qurgan edi. Bu xabar "
            "BOT-01 ning uch darvozasidan biri ochilganda chiqadi."
        )
        return self._resolve_result

    async def vendor_summary(self, *, telegram_user_id: int) -> VendorSummary:
        self.summary_calls.append(telegram_user_id)
        if self._raises is not None:
            raise self._raises
        assert self._summary is not None
        return self._summary

    async def vendor_payments(
        self,
        *,
        telegram_user_id: int,
        market_id: UUID,
        cursor: str | None = None,
        limit: int = 10,
    ) -> PaymentsPage:
        self.payments_calls.append(
            {
                "telegram_user_id": telegram_user_id,
                "market_id": market_id,
                "cursor": cursor,
                "limit": limit,
            }
        )
        if self._raises is not None:
            raise self._raises
        return self._pages.pop(0)


def failing_double(status: int) -> CoreDouble:
    """Har chaqiruvda `CoreApiError` (yoki `404` da uning avlodi) beradi."""
    from app.core_client import NotBoundError

    error_class = NotBoundError if status == 404 else CoreApiError
    return CoreDouble(
        raises=error_class(operation="test", error_type="HTTPStatusError", status=status)
    )


def one_market_summary(
    outstanding: int, *, as_of: date, codes: tuple[str, ...] = ("A-01",)
) -> VendorSummary:
    return VendorSummary(
        markets=[
            MarketSummary(
                market_id=MARKET_ID,
                vendor_id=VENDOR_ID,
                outstanding_soum=outstanding,
                as_of=as_of,
                stall_codes=list(codes),
            )
        ]
    )
