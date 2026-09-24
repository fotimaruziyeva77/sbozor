"""O'TGAN KUNLAR UCHUN KUNLIK HISOBLARNI TO'LDIRISH — ops qadami.

=============================================================================
⛔⛔ NEGA BU SKRIPT BOR.

2026-08-25: pilot bozor kamerasiz ishladi — `payments` 138 qator,
`daily_charges` 0 («Hisoblangan 0 so'm», qarz reestri −3 676 000). O'tgan
kunlar shu skript bilan bir marta to'ldirildi (246 hisob).

2026-09-24: kamera ulangach bozor butunlay D-04 ga o'tdi, zona esa 53
rastadan 6–9 tasida edi — 28-avgustdan 28 kun davomida 0 ta hisob.
`billing_close` endi gibrid qoida bilan ishlaydi (modul docstringining
6-bandi): zonasiz rasta biriktirish bo'yicha, zonali rasta D-04 bo'yicha.
O'tgan kunlar AYNAN shu mahsulot yo'lidan qayta yopiladi — skript o'zi
hech narsa hisoblamaydi.

=============================================================================
HAR KUN UCHUN: `day_close(kun)` -> `billing_close(kun)`.

`day_close` konvergent (qayta yugurish mo'ljallangan) va u slot qatorlarini
materializatsiya qiladi; usiz kamerali bozorda o'sha kun `no_slot_rows`
bo'lib qolardi va hisob yozilmasdi (Pitfall 2).

⛔ IDEMPOTENT (D-06): mavjud hisob QAYTA yozilmaydi — ikki marta
   yugurtirish xavfsiz (`skipped_existing` o'sadi, boshqa hech nima).

=============================================================================
⛔⛔ BO'SH KUNLAR — SO'RAMASDAN HISOBLANMAYDI.

Kalendar «ochiq» degan, lekin bozorda BIRONTA to'lov yozilmagan kun
(masalan 1–2-sentabr bayrami) — bozor amalda yopiq bo'lgan bo'lishi
mumkin. Uni hisoblash HAR sotuvchiga soxta qarz yozardi: prod'da bitta
shunday kun ~1,25 mln so'm edi. Skript bunday kunlarni ro'yxat qilib
TO'XTAYDI va hech narsa yozmaydi. Ikki yo'l:

  * to'g'ri yo'l — «Ish kunlari» sahifasida o'sha kunni YOPIQ deb belgilash
    (kalendar istisnosi); keyin skript uni o'zi o'tkazib yuboradi;
  * bozor o'sha kuni haqiqatan ishlagan bo'lsa — kunni
    `BACKFILL_ALLOW_EMPTY_DAYS` ga yozish (vergul bilan).

=============================================================================
⚠ HALOL CHEKLOVLAR:

  * Biriktirish, tarif va kalendar O'SHA kunnikidan o'qiladi, lekin rasta
    HOLATI (faol/yopiq/ta'mirda) — BUGUNGI reyestr ustuni: holat tarixi
    saqlanmaydi. Bugun yopiq rasta o'tgan kunlar uchun ham hisoblanmaydi.
  * Zonali rastalar D-04 da: nazoratchi tasdiqlamagan kun «bo'sh» bo'lib
    yopiladi va hisob yozilmaydi. Ular uchun avval ko'rib chiqish navbati.

-----------------------------------------------------------------------------
ISHLATISH (prod serverda):

    # 1) oldindan tekshiruv — HECH NARSA YOZMAYDI:
    docker exec -i -e BACKFILL_FROM=2026-08-28 -e BACKFILL_TO=2026-09-23 \\
      -e BACKFILL_DRY_RUN=1 sbozor-core-api-1 python - < ops/scripts/backfill_charges.py

    # 2) yozish:
    docker exec -i -e BACKFILL_FROM=2026-08-28 -e BACKFILL_TO=2026-09-23 \\
      sbozor-core-api-1 python - < ops/scripts/backfill_charges.py

`core-api` konteyneri ilova roli bilan (`DATABASE_URL`) ishlaydi — kunlik
cron aynan shu rol bilan yozadi. `migrate` xizmatida ham ishlaydi
(`MIGRATION_DATABASE_URL`, repo ildizidan).

⚠ `BACKFILL_TO` BUGUNDAN KICHIK bo'lishi shart: bugungi kun hali tugamagan,
  uni kechasi cron yopadi.
=============================================================================
"""

from __future__ import annotations

import asyncio
import os
import sys
from collections import Counter
from datetime import date, timedelta
from uuid import UUID

try:
    import app  # noqa: F401
except ImportError:
    # Repo ildizidan (`migrate` xizmati) — `app` paketi servis katalogida.
    sys.path.insert(0, "services/core-api")

from app.jobs.billing_close import billing_close
from app.jobs.day_close import day_close
from app.jobs.retention import active_market_ids
from sbozor_core.enums import ActorKind, PaymentKind
from sbozor_core.tenancy import set_tenant_context
from sbozor_core.timeutil import business_today
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


def _require_date(name: str) -> date:
    raw = os.environ.get(name, "").strip()
    if not raw:
        raise SystemExit(f"⛔ {name} berilmagan — modul boshidagi misolga qarang.")
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise SystemExit(f"⛔ {name}={raw!r} — YYYY-MM-DD kutilgan.") from exc


def _allowed_empty_days() -> set[date]:
    raw = os.environ.get("BACKFILL_ALLOW_EMPTY_DAYS", "").strip()
    if not raw:
        return set()
    try:
        return {date.fromisoformat(part.strip()) for part in raw.split(",") if part.strip()}
    except ValueError as exc:
        raise SystemExit(
            f"⛔ BACKFILL_ALLOW_EMPTY_DAYS={raw!r} — vergul bilan YYYY-MM-DD kutilgan."
        ) from exc


async def _empty_days(
    sessionmaker: async_sessionmaker[AsyncSession], days: list[date]
) -> dict[str, list[date]]:
    """Kalendar ochiq, lekin bironta to'lov yo'q kunlar — `{bozor nomi: [kunlar]}`."""
    found: dict[str, list[date]] = {}
    for market_id in await active_market_ids(sessionmaker):
        async with sessionmaker() as session, session.begin():
            await set_tenant_context(
                session,
                market_id=market_id,
                actor_id=None,
                request_id="backfill-preflight",
                actor_kind=ActorKind.SYSTEM,
            )
            name = await _market_name(session, market_id)
            for day in days:
                is_open = await session.scalar(
                    text("SELECT market_is_open(:m, :d)"), {"m": market_id, "d": day}
                )
                paid = await session.scalar(
                    text(
                        "SELECT count(*) FROM payments "
                        "WHERE market_id = :m AND business_date = :d AND kind = :k"
                    ),
                    {"m": market_id, "d": day, "k": PaymentKind.PAYMENT.value},
                )
                if is_open and int(paid or 0) == 0:
                    found.setdefault(name, []).append(day)
    return found


async def _market_name(session: AsyncSession, market_id: UUID) -> str:
    name = await session.scalar(text("SELECT name FROM markets WHERE id = :m"), {"m": market_id})
    return str(name) if name is not None else str(market_id)


async def main() -> None:
    start = _require_date("BACKFILL_FROM")
    end = _require_date("BACKFILL_TO")
    today = business_today()
    if start > end:
        raise SystemExit(f"⛔ BACKFILL_FROM ({start}) BACKFILL_TO ({end}) dan katta.")
    if end >= today:
        raise SystemExit(
            f"⛔ BACKFILL_TO ({end}) bugun yoki kelajakda — bugungi kunni kechasi cron yopadi."
        )
    dry_run = os.environ.get("BACKFILL_DRY_RUN", "").strip() == "1"
    allowed = _allowed_empty_days()

    url = (
        os.environ.get("DATABASE_URL", "").strip()
        or os.environ.get("MIGRATION_DATABASE_URL", "").strip()
    )
    if not url:
        raise SystemExit("⛔ DATABASE_URL ham, MIGRATION_DATABASE_URL ham yo'q.")

    engine = create_async_engine(url, echo=False)
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    days = [start + timedelta(days=offset) for offset in range((end - start).days + 1)]

    try:
        empty = await _empty_days(sessionmaker, days)
        blocking = {
            name: [day for day in market_days if day not in allowed]
            for name, market_days in empty.items()
        }
        blocking = {name: market_days for name, market_days in blocking.items() if market_days}

        print(f"Oraliq: {start} — {end} ({len(days)} kun)")
        for name, market_days in empty.items():
            listed = ", ".join(day.isoformat() for day in market_days)
            print(f"  {name}: kalendar ochiq, to'lov 0 — {listed}")

        if blocking:
            print(
                "\n⛔ Yuqoridagi kunlar hisoblanmaydi va skript HECH NARSA YOZMADI.\n"
                "   Bozor o'sha kunlari yopiq bo'lgan bo'lsa — «Ish kunlari» sahifasida\n"
                "   ularni yopiq deb belgilang. Ishlagan bo'lsa — kunlarni\n"
                "   BACKFILL_ALLOW_EMPTY_DAYS=YYYY-MM-DD,... ga yozing."
            )
            raise SystemExit(2)
        if dry_run:
            print("\nOldindan tekshiruv toza. BACKFILL_DRY_RUN=1 — hech narsa yozilmadi.")
            return

        total_auto = total_camera = total_existing = 0
        unmaterialised: list[date] = []
        errors: list[str] = []
        for day in days:
            await day_close(sessionmaker, business_date=day)
            result = await billing_close(sessionmaker, business_date=day)
            total_auto += result.charged_auto
            total_camera += result.charged
            total_existing += result.skipped_existing
            errors.extend(result.errors)
            if result.no_slot_rows:
                unmaterialised.append(day)
            print(
                f"{day}: biriktirish={result.charged_auto} kamera={result.charged} "
                f"bor_edi={result.skipped_existing} sotuvchisiz={result.skipped_unassigned_auto} "
                f"holat_skip={result.skipped_inactive + result.skipped_fair} "
                f"slotsiz={result.no_slot_rows} xato={len(result.errors)}"
            )
    finally:
        await engine.dispose()

    print("---")
    print(
        f"JAMI: biriktirish bo'yicha {total_auto}, kamera bo'yicha {total_camera}, "
        f"allaqachon bor edi {total_existing}."
    )
    if unmaterialised:
        print(
            "⚠ Slot qatori bo'lmagan rastalar bor kunlar (kadr jadvali qamramagan bo'lishi "
            "mumkin): " + ", ".join(day.isoformat() for day in unmaterialised)
        )
    if errors:
        # Takrorlarni yig'ib ko'rsatamiz — har kunda bir xil tarif bo'shlig'i
        # 30 qator bo'lib emas, bir qator × son bo'lib o'qilsin.
        for code, count in Counter(errors).most_common():
            print(f"  XATO {code} × {count}")
        raise SystemExit("⛔ Xatolar bor — yuqoridagi ro'yxatni ko'rib chiqing.")


if __name__ == "__main__":
    asyncio.run(main())
