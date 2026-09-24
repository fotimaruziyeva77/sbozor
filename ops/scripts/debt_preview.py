"""SOTUVCHI QARZINING OLDINDAN KO'RINISHI — FAQAT O'QIYDI, HECH NARSA YOZMAYDI.

=============================================================================
⛔⛔ NEGA BU SKRIPT BOR (2026-09-24).

Prod'da 28-avgustdan 28 kun davomida kunlik hisob yozilmadi, to'lovlar esa
yozildi. Tizimdagi qoldiq (`vendor_outstanding`) shu sababli YOLG'ON
edi: sotuvchilar «avansda» ko'rinardi. Buyurtmachi «hozir bularning
qarzi bormi?» deb so'radi — javob uchun yozilmagan kunlar tizimning O'Z
pul funksiyasi (`resolve_stall_day_money`) bilan hisoblanib, haqiqiy
to'lovlar bilan solishtirildi. Tiklashdan (`backfill_charges.py`) OLDIN
natijani ko'rish uchun ham shu skript ishlatiladi.

⛔ FAQAT O'QISH MEXANIK KAFOLATLANGAN: tranzaksiya `SET TRANSACTION READ
   ONLY` bilan ochiladi — tasodifiy yozuv bazaning o'zida rad etiladi.

=============================================================================
QOIDA — «KUTILGAN» NIMA:

  * hisob yozilgan kun — YOZILGAN summa (+ tuzatishlar);
  * hisob yozilmagan kun — BIRIKTIRISH bo'yicha: o'sha kuni kalendar ochiq,
    rasta faol va sotuvchiga biriktirilgan bo'lsa, o'sha kunning tarifi +
    xizmat haqi. Bu kamerasiz bozor qoidasi; zonali rastalar uchun tiklash
    D-04 bo'yicha boradi, ya'ni ularning natijasi bu yerdagidan kam
    bo'lishi mumkin.

«SHUBHALI KUN» — kalendar ochiq, lekin BUTUN bozorda bironta to'lov yo'q
kun (masalan bayram). Bu kunlarning hissasi alohida ko'rsatiladi: bozor
o'sha kuni yopiq bo'lgan bo'lsa, «shubhali kunlarsiz» raqam to'g'ri.

⚠ CHEKLOV: rasta holati — BUGUNGI reyestr ustuni (holat tarixi yo'q). Bugun
  yopiq rasta o'tgan kunlar uchun ham hisoblanmaydi — uning qarzi pastki
  chegara.

-----------------------------------------------------------------------------
ISHLATISH (prod serverda):

    docker exec -i -e DEBT_FROM=2026-08-22 sbozor-core-api-1 \\
      python - < ops/scripts/debt_preview.py

Bugungi kun hisobga KIRMAYDI (to'lovlar ham, patta ham — kecha kechqurungi
holat).
=============================================================================
"""

from __future__ import annotations

import asyncio
import os
import sys
from collections import defaultdict
from datetime import date, timedelta
from typing import Any
from uuid import UUID

try:
    import app  # noqa: F401
except ImportError:
    sys.path.insert(0, "services/core-api")

from app.jobs.retention import active_market_ids
from app.repositories.billing_repo import resolve_stall_day_money
from sbozor_core.enums import ActorKind, PaymentKind
from sbozor_core.tenancy import set_tenant_context
from sbozor_core.timeutil import business_today
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

TOP_DEBTORS = 10


def _som(value: int) -> str:
    return f"{value:,}".replace(",", " ") + " so'm"


def _require_date(name: str) -> date:
    raw = os.environ.get(name, "").strip()
    if not raw:
        raise SystemExit(f"⛔ {name} berilmagan — modul boshidagi misolga qarang.")
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise SystemExit(f"⛔ {name}={raw!r} — YYYY-MM-DD kutilgan.") from exc


async def _rows(session: AsyncSession, sql: str, **params: Any) -> list[Any]:
    return list((await session.execute(text(sql), params)).all())


async def _market_report(
    session: AsyncSession, *, market_id: UUID, start: date, today: date
) -> None:
    params = {"m": market_id, "t": today}
    payment = PaymentKind.PAYMENT.value
    reversal = PaymentKind.REVERSAL.value

    name = await session.scalar(text("SELECT name FROM markets WHERE id = :m"), {"m": market_id})
    billed = {
        row[0]
        for row in await _rows(
            session,
            "SELECT DISTINCT service_date FROM daily_charges "
            "WHERE market_id = :m AND service_date < :t",
            **params,
        )
    }
    pays_per_day = {
        row[0]: int(row[1])
        for row in await _rows(
            session,
            "SELECT business_date, count(*) FROM payments "
            "WHERE market_id = :m AND kind = :k GROUP BY 1",
            m=market_id,
            k=payment,
        )
    }

    expected: dict[UUID, int] = defaultdict(int)
    suspicious_part: dict[UUID, int] = defaultdict(int)
    for vendor_id, amount in await _rows(
        session,
        "SELECT vendor_id, sum(amount_soum) FROM daily_charges "
        "WHERE market_id = :m AND service_date < :t AND vendor_id IS NOT NULL GROUP BY 1",
        **params,
    ):
        expected[vendor_id] += int(amount)
    for vendor_id, amount in await _rows(
        session,
        "SELECT c.vendor_id, sum(CASE WHEN a.direction = 'increase' "
        "THEN a.amount_soum ELSE -a.amount_soum END) "
        "FROM charge_adjustments a JOIN daily_charges c "
        "ON c.market_id = a.market_id AND c.id = a.charge_id "
        "WHERE a.market_id = :m AND c.service_date < :t AND c.vendor_id IS NOT NULL GROUP BY 1",
        **params,
    ):
        expected[vendor_id] += int(amount)

    missing_days: list[date] = []
    suspicious_days: list[date] = []
    day = start
    while day < today:
        if day not in billed:
            charged_any = False
            for money in await resolve_stall_day_money(session, market_id=market_id, as_of=day):
                if money.vendor_id is None or money.amount_soum is None:
                    continue
                charged_any = True
                expected[money.vendor_id] += money.amount_soum
                if pays_per_day.get(day, 0) == 0:
                    suspicious_part[money.vendor_id] += money.amount_soum
            if charged_any:
                missing_days.append(day)
                if pays_per_day.get(day, 0) == 0:
                    suspicious_days.append(day)
        day += timedelta(days=1)

    paid = {
        row[0]: int(row[1])
        for row in await _rows(
            session,
            "SELECT vendor_id, sum(CASE WHEN kind = :r THEN -amount_soum ELSE amount_soum END) "
            "FROM payments WHERE market_id = :m AND business_date < :t "
            "AND vendor_id IS NOT NULL GROUP BY 1",
            m=market_id,
            t=today,
            r=reversal,
        )
    }
    last_paid = {
        row[0]: row[1]
        for row in await _rows(
            session,
            "SELECT vendor_id, max(business_date) FROM payments "
            "WHERE market_id = :m AND kind = :k GROUP BY 1",
            m=market_id,
            k=payment,
        )
    }
    names = {
        row[0]: row[1]
        for row in await _rows(
            session, "SELECT id, full_name FROM vendors WHERE market_id = :m", m=market_id
        )
    }
    open_cases = await _rows(
        session,
        "SELECT s.code, s.status, c.vendor_id, rc.service_date "
        "FROM reconciliation_cases rc JOIN daily_charges c "
        "ON c.market_id = rc.market_id AND c.id = rc.charge_id "
        "JOIN stalls s ON s.market_id = c.market_id AND s.id = c.stall_id "
        "WHERE rc.market_id = :m AND rc.status IN ('new', 'in_review') "
        "ORDER BY length(s.code), s.code",
        m=market_id,
    )

    def debt(vendor_id: UUID) -> tuple[int, int]:
        full = expected.get(vendor_id, 0) - paid.get(vendor_id, 0)
        return full, full - suspicious_part.get(vendor_id, 0)

    print(f"\n=== {name or market_id} — {start} dan {today - timedelta(days=1)} gacha")
    print(f"Hisob yozilmagan, qoida bo'yicha hisoblangan kunlar: {len(missing_days)} ta")
    if suspicious_days:
        print(
            "Kalendar ochiq, lekin bironta to'lov yo'q kunlar (amalda yopiq bo'lishi mumkin): "
            + ", ".join(day.isoformat() for day in suspicious_days)
        )

    if open_cases:
        print("\n-- HAL QILINMAGAN «band, lekin to'lovsiz» ISHLARI (qarz sotuvchi kesimida) --")
        for code, status, vendor_id, case_day in open_cases:
            full, without = debt(vendor_id)
            print(
                f"rasta {code:>4} [{status}] | {names.get(vendor_id, '?')} | "
                f"QARZ {_som(full)} (shubhali kunlarsiz {_som(without)}) | "
                f"oxirgi to'lov {last_paid.get(vendor_id, '-')} | case kuni {case_day}"
            )

    rows = [(debt(vendor_id), vendor_id) for vendor_id in set(expected) | set(paid)]
    rows.sort(key=lambda row: row[0][0], reverse=True)
    debtors = [row for row in rows if row[0][0] > 0]
    print(
        f"\n-- BOZOR: qarzdor {len(debtors)} ta, jami qarz "
        f"{_som(sum(max(0, row[0][0]) for row in rows))} "
        f"(shubhali kunlarsiz {_som(sum(max(0, row[0][1]) for row in rows))}) --"
    )
    for (full, without), vendor_id in debtors[:TOP_DEBTORS]:
        print(
            f"{names.get(vendor_id, '?'):<32} qarz {_som(full)} "
            f"(shubhali kunlarsiz {_som(without)}), oxirgi to'lov {last_paid.get(vendor_id, '-')}"
        )


async def main() -> None:
    start = _require_date("DEBT_FROM")
    today = business_today()
    if start >= today:
        raise SystemExit(f"⛔ DEBT_FROM ({start}) bugundan oldin bo'lishi kerak.")

    url = (
        os.environ.get("DATABASE_URL", "").strip()
        or os.environ.get("MIGRATION_DATABASE_URL", "").strip()
    )
    if not url:
        raise SystemExit("⛔ DATABASE_URL ham, MIGRATION_DATABASE_URL ham yo'q.")

    engine = create_async_engine(url, echo=False)
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    try:
        for market_id in await active_market_ids(sessionmaker):
            async with sessionmaker() as session, session.begin():
                await session.execute(text("SET TRANSACTION READ ONLY"))
                await set_tenant_context(
                    session,
                    market_id=market_id,
                    actor_id=None,
                    request_id="debt-preview",
                    actor_kind=ActorKind.SYSTEM,
                )
                await _market_report(session, market_id=market_id, start=start, today=today)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
