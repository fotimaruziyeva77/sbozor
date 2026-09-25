"""O'TGAN DAVR QARZLARINI YOPISH — ops qadami (260925-kvq).

=============================================================================
⛔⛔ NEGA BU SKRIPT BOR.

Buyurtmachi qarori (2026-09-25): chegara kunidan OLDINGI barcha sotuvchi
qarzlari to'langan deb hisoblansin, o'sha davrdagi hal qilinmagan
nomuvofiqlik ishlari yopilsin (xaritadagi sariq yo'qolsin). Chegara kunidan
boshlab tizim odatdagidek ishlaydi: patta to'lanmasa 3 kundan keyin yana
sariq bo'ladi.

Qoidalar va sabablar — `app/jobs/debt_settlement.py` docstringida. Qisqasi:
  * soxta to'lov YOZILMAYDI — qarz «Direktor kechirdi» tuzatishi bilan
    kamayadi (aktor — bozor direktori, audit bilan);
  * chegara kuni va undan keyingi to'lovlar TEGILMAYDI — ular bugungi
    pattani yopadi; eski davrdan qolgan avans o'zgarmaydi;
  * hal qilinmagan eski ishlar «Asossiz» holatiga izoh bilan o'tadi.

=============================================================================
⛔ STANDART HOLATDA HECH NARSA SAQLANMAYDI (quruq yugurish): amal to'liq
   bajariladi — qulf, yozuvlar, konstrayt va triggerlar, yakuniy tekshiruv —
   va oxirida ROLLBACK. Hisobot aynan yozish natijasining o'zi. Saqlash
   uchun `SETTLE_APPLY=1`.

⛔ `SETTLE_BEFORE` MAJBURIY va standart qiymati YO'Q: skript ertaga
   yugurtirilsa, «bugun» jimgina yana bir kunni kechirib yuborardi.

⚠ Qayta yugurtirish xavfsiz: eski qoldiq allaqachon nol, ya'ni hech narsa
  yozilmaydi.

-----------------------------------------------------------------------------
ISHLATISH (prod serverda, repo ildizidan):

    # 1) quruq yugurish — hech narsa saqlanmaydi:
    docker exec -i -e SETTLE_BEFORE=2026-09-25 sbozor-core-api-1 \\
      python - < ops/scripts/settle_debts.py

    # 2) saqlash (oldin baza zaxirasi!):
    docker exec -i -e SETTLE_BEFORE=2026-09-25 -e SETTLE_APPLY=1 \\
      sbozor-core-api-1 python - < ops/scripts/settle_debts.py

Ixtiyoriy:
    SETTLE_DIRECTOR_PHONE=+998...  — bozorda faol direktor bittadan ko'p (yoki
                                      qaror boshqa direktorniki) bo'lsa;
    SETTLE_MARKET_ID=<uuid>        — faqat bitta bozor.
=============================================================================
"""

from __future__ import annotations

import asyncio
import os
import sys
from collections import Counter
from datetime import date
from typing import TYPE_CHECKING
from uuid import UUID

try:
    import app  # noqa: F401
except ImportError:
    # Repo ildizidan (`migrate` xizmati) — `app` paketi servis katalogida.
    sys.path.insert(0, "services/core-api")

from app.jobs.debt_settlement import (
    SettlementInvariantError,
    SettlementResult,
    market_directors,
    pick_decision_maker,
    settle_market,
)
from app.jobs.retention import active_market_ids
from sbozor_core.enums import ActorKind, ReconciliationSubjectKind
from sbozor_core.phone import InvalidPhoneError
from sbozor_core.tenancy import set_tenant_context
from sbozor_core.timeutil import business_today
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

if TYPE_CHECKING:
    from app.repositories.user_repo import MarketUser

_KIND_LABEL = {
    ReconciliationSubjectKind.OCCUPIED_UNPAID.value: "band, lekin to'lovsiz",
    ReconciliationSubjectKind.ANOMALY.value: "ro'yxatga olinmagan savdo",
}


_COLUMNS = ("Sotuvchi", "eski hisob", "eski to'lov", "kechiriladi", "yangi to'lov")


class _MarketFailure(Exception):
    """Bitta bozorda to'xtash — bozor nomi bilan; bu bozorga hech narsa saqlanmaydi."""


def _num(value: int) -> str:
    return f"{value:,}".replace(",", " ")


def _som(value: int) -> str:
    return _num(value) + " so'm"


def _require_date(name: str) -> date:
    raw = os.environ.get(name, "").strip()
    if not raw:
        raise SystemExit(f"⛔ {name} berilmagan — modul boshidagi misolga qarang.")
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise SystemExit(f"⛔ {name}={raw!r} — YYYY-MM-DD kutilgan.") from exc


def _optional_uuid(name: str) -> UUID | None:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return None
    try:
        return UUID(raw)
    except ValueError as exc:
        raise SystemExit(f"⛔ {name}={raw!r} — UUID kutilgan.") from exc


async def _vendor_names(session: AsyncSession, market_id: UUID) -> dict[UUID, str]:
    rows = await session.execute(
        text("SELECT id, full_name FROM vendors WHERE market_id = :m"), {"m": market_id}
    )
    return {row[0]: str(row[1] or "?") for row in rows}


def _print_report(
    *,
    market_name: str,
    director: MarketUser,
    result: SettlementResult,
    names: dict[UUID, str],
) -> None:
    plan = result.plan
    waived = [vendor for vendor in plan.vendors if vendor.waived_soum > 0]
    advance = [vendor for vendor in plan.vendors if vendor.advance_soum > 0]
    paid_since = [vendor for vendor in plan.vendors if vendor.new_credit_soum != 0]

    print(f"\n=== {market_name} — {plan.before} dan oldingi davr")
    print(f"Qaror egasi: {director.full_name or '?'} ({director.phone})")
    print(
        f"Kechiriladi: {len(waived)} ta sotuvchi, {len(plan.waivers)} ta hisob, "
        f"jami {_som(plan.waived_soum)}"
    )
    print(
        f"Avansda qoladi (o'zgarmaydi): {len(advance)} ta sotuvchi, "
        f"jami {_som(sum(vendor.advance_soum for vendor in advance))}"
    )
    print(
        f"{plan.before} va undan keyingi to'lovlar (tegilmaydi, o'sha kunlar pattasiga): "
        f"{len(paid_since)} ta sotuvchi, "
        f"jami {_som(sum(vendor.new_credit_soum for vendor in paid_since))}"
    )

    kinds = Counter(case.subject_kind for case in plan.cases)
    listed = ", ".join(f"{_KIND_LABEL.get(kind, kind)}: {count}" for kind, count in kinds.items())
    detail = f" ({listed})" if listed else ""
    print(f"Hal qilinmagan eski ishlar -> «Asossiz»: {len(plan.cases)} ta{detail}")
    days = Counter(case.service_date for case in plan.cases)
    if days:
        print("  kunlar: " + ", ".join(f"{day}: {count}" for day, count in sorted(days.items())))
    print(f"Tekshiruv: {plan.before} dan oldingi qarz va hal qilinmagan eski ish QOLMADI.")

    if waived:
        print("\n-- Sotuvchi kesimida (kechiriladigan summa bo'yicha, so'm) --")
        name, due, paid, forgiven, since = _COLUMNS
        print(f"{name:<30} {due:>12} {paid:>12} {forgiven:>12} {since:>12}")
        for vendor in sorted(waived, key=lambda row: row.waived_soum, reverse=True):
            print(
                f"{names.get(vendor.vendor_id, '?')[:30]:<30} "
                f"{_num(vendor.old_due_soum):>12} {_num(vendor.old_credit_soum):>12} "
                f"{_num(vendor.waived_soum):>12} {_num(vendor.new_credit_soum):>12}"
            )


async def _settle_one(
    sessionmaker: async_sessionmaker[AsyncSession],
    *,
    market_id: UUID,
    before: date,
    phone: str | None,
    apply: bool,
) -> SettlementResult:
    request_id = f"settle-debts-{before.isoformat()}"
    async with sessionmaker() as session:
        transaction = await session.begin()
        try:
            await set_tenant_context(
                session,
                market_id=market_id,
                actor_id=None,
                request_id=request_id,
                actor_kind=ActorKind.SYSTEM,
            )
            market_name = str(
                await session.scalar(
                    text("SELECT name FROM markets WHERE id = :m"), {"m": market_id}
                )
                or market_id
            )
            try:
                director = pick_decision_maker(
                    await market_directors(session, market_id=market_id), phone
                )
                # Qaror egasi — audit triggeri aktorni shu GUC'dan o'qiydi.
                await set_tenant_context(
                    session,
                    market_id=market_id,
                    actor_id=director.user_id,
                    request_id=request_id,
                    actor_kind=ActorKind.USER,
                )
                result = await settle_market(
                    session, market_id=market_id, before=before, actor_user_id=director.user_id
                )
            except (LookupError, InvalidPhoneError, SettlementInvariantError) as exc:
                raise _MarketFailure(f"{market_name}: {exc}") from exc
            names = await _vendor_names(session, market_id)
        except BaseException:
            await transaction.rollback()
            raise

        if apply:
            await transaction.commit()
        else:
            await transaction.rollback()

    _print_report(market_name=market_name, director=director, result=result, names=names)
    if apply:
        print(
            f"\n✅ SAQLANDI: {result.adjustments_written} ta tuzatish, "
            f"{result.cases_closed} ta ish yopildi."
        )
    else:
        print("\nQuruq yugurish — hech narsa saqlanmadi (saqlash uchun SETTLE_APPLY=1).")
    return result


async def main() -> None:
    before = _require_date("SETTLE_BEFORE")
    today = business_today()
    if before > today:
        raise SystemExit(f"⛔ SETTLE_BEFORE ({before}) bugundan ({today}) keyin bo'lolmaydi.")
    apply = os.environ.get("SETTLE_APPLY", "").strip() == "1"
    phone = os.environ.get("SETTLE_DIRECTOR_PHONE", "").strip() or None
    only_market = _optional_uuid("SETTLE_MARKET_ID")

    url = (
        os.environ.get("DATABASE_URL", "").strip()
        or os.environ.get("MIGRATION_DATABASE_URL", "").strip()
    )
    if not url:
        raise SystemExit("⛔ DATABASE_URL ham, MIGRATION_DATABASE_URL ham yo'q.")

    engine = create_async_engine(url, echo=False)
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    failed: list[str] = []
    try:
        market_ids = await active_market_ids(sessionmaker)
        if only_market is not None:
            if only_market not in market_ids:
                raise SystemExit(f"⛔ SETTLE_MARKET_ID={only_market} faol bozorlar orasida yo'q.")
            market_ids = [only_market]
        mode = "SAQLASH" if apply else "quruq yugurish"
        print(f"Chegara: {before} (shu kundan OLDINGI davr yopiladi); rejim: {mode}")
        for market_id in market_ids:
            try:
                await _settle_one(
                    sessionmaker, market_id=market_id, before=before, phone=phone, apply=apply
                )
            except _MarketFailure as exc:
                # Bir bozorning muammosi qolganlarini to'xtatmaydi — bu bozor
                # uchun hech narsa saqlanmadi (tranzaksiya orqaga qaytdi).
                failed.append(str(exc))
    finally:
        await engine.dispose()

    if failed:
        print("\n⛔ Quyidagi bozorlarda HECH NARSA saqlanmadi:")
        for line in failed:
            print(f"  {line}")
        print("  (direktorni tanlash: -e SETTLE_DIRECTOR_PHONE=+998...)")
        raise SystemExit(2)


if __name__ == "__main__":
    asyncio.run(main())
