"""O'TGAN KUNLAR UCHUN KUNLIK HISOBLARNI TO'LDIRISH — bir martalik ops qadami.

=============================================================================
⛔⛔ NEGA BU SKRIPT BOR (2026-08-25, buyurtmachi buyrug'i).

Pilot bozor kamerasiz ishladi: `payments` 138 qator, `daily_charges` 0 —
«Hisoblangan 0 so'm», qarz reestri −3 676 000 (jonli serverda o'lchandi).
Kamerasiz avto-rejim (`billing_close._close_market_without_cameras`) shu
kundan boshlab yozadi; O'TGAN kunlarni esa aynan shu skript bir marta
to'ldiradi — buyurtmachi: «o'tgan kunlarni ham to'ldir hisoblarni».

⛔ HISOB TARIXIY TO'G'RI: har kun uchun O'SHA kunning biriktirishi, tarifi
   va rasta holati o'qiladi (`resolve_stall_day_money(as_of=kun)`) —
   bugungi holat o'tmishga ko'chirilmaydi.

⛔ IDEMPOTENT (D-06): mavjud hisob QAYTA yozilmaydi — skriptni ikki marta
   yugurtirish xavfsiz (`skipped_existing` o'sadi, boshqa hech nima).

⛔ KAMERALI BOZORGA TEGMAYDI: avto-rejim sharti har kunda qayta tekshiriladi
   (kamera bor bozorda slot hukmisiz kun «no_slot_rows» bo'lib qolaveradi —
   hisob yozilmaydi, xuddi cron'dagidek).

-----------------------------------------------------------------------------
ISHLATISH (repo ildizida, prod serverda):

    docker compose run --rm \\
      -e BACKFILL_FROM=2026-07-26 \\
      -e BACKFILL_TO=2026-08-24 \\
      migrate python ops/scripts/backfill_charges.py

`migrate` xizmati ATAYIN: uning image'ida `ops/` bor va `MIGRATION_DATABASE_URL`
(egalik roli) o'rnatilgan — RLS `FORCE` bo'lgani uchun ega ham tenant GUC'i
bilan ishlaydi (`bootstrap_admin.py` bilan bir xil yo'l). `DATABASE_URL`
berilsa, u USTUN (ilova roli bilan yugurish).

⚠ `BACKFILL_TO` BUGUNDAN KATTA BO'LOLMAYDI va odatda KECHA bo'lishi kerak:
  bugungi kunni kechqurungi cron o'zi yozadi.
=============================================================================
"""

from __future__ import annotations

import asyncio
import os
import sys
from datetime import date, timedelta

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

# Skript repo ildizidan yuritiladi; `app` paketi servis katalogida.
sys.path.insert(0, "services/core-api")

from app.jobs.billing_close import billing_close  # noqa: E402


def _require_date(name: str) -> date:
    raw = os.environ.get(name, "").strip()
    if not raw:
        raise SystemExit(f"⛔ {name} berilmagan — modul boshidagi misolga qarang.")
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise SystemExit(f"⛔ {name}={raw!r} — YYYY-MM-DD kutilgan.") from exc


async def main() -> None:
    start = _require_date("BACKFILL_FROM")
    end = _require_date("BACKFILL_TO")
    if start > end:
        raise SystemExit(f"⛔ BACKFILL_FROM ({start}) BACKFILL_TO ({end}) dan katta.")
    if end > date.today():
        raise SystemExit(f"⛔ BACKFILL_TO ({end}) kelajakda — bugungi kunni cron yozadi.")

    url = (
        os.environ.get("DATABASE_URL", "").strip()
        or os.environ.get("MIGRATION_DATABASE_URL", "").strip()
    )
    if not url:
        raise SystemExit("⛔ DATABASE_URL ham, MIGRATION_DATABASE_URL ham yo'q.")

    engine = create_async_engine(url, echo=False)
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)

    total_auto = 0
    total_existing = 0
    total_errors: list[str] = []
    day = start
    try:
        while day <= end:
            result = await billing_close(sessionmaker, business_date=day)
            total_auto += result.charged_auto
            total_existing += result.skipped_existing
            total_errors.extend(result.errors)
            print(
                f"{day}: avto={result.charged_auto} kamera={result.charged} "
                f"bor_edi={result.skipped_existing} sotuvchisiz={result.skipped_unassigned_auto} "
                f"holat_skip={result.skipped_inactive + result.skipped_fair} "
                f"xato={len(result.errors)}"
            )
            day += timedelta(days=1)
    finally:
        await engine.dispose()

    print("---")
    print(f"JAMI: yangi avto-hisob {total_auto}, allaqachon bor edi {total_existing}.")
    if total_errors:
        # Takrorlarni yig'ib ko'rsatamiz — har kunda bir xil tarif bo'shlig'i
        # 30 qator bo'lib emas, bir qator × son bo'lib o'qilsin.
        from collections import Counter

        for code, n in Counter(total_errors).most_common():
            print(f"  XATO {code} × {n}")
        raise SystemExit("⛔ Xatolar bor — yuqoridagi ro'yxatni ko'rib chiqing.")


if __name__ == "__main__":
    asyncio.run(main())
