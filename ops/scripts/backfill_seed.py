"""Eski kadrlarni nazoratchi navbatiga urug'lantirish — bir martalik ops qadami.

⛔ IDEMPOTENT: `seed_snapshot` ikkala INSERT'ni ham `ON CONFLICT DO NOTHING`
   bilan yozadi, ya'ni skriptni ikki marta yugurtirish xavfsiz — ikkinchi
   yugurish nol yangi qator beradi.

⛔ FAQAT `ok` KADR VA FAQAT ZONALI KAMERA: yaroqsiz kadr uchun
   `occupancy_events` ning kompozit FK'si `(id, true)` juftligini topa
   olmaydi (D-21), zonasiz kamera uchun esa yozadigan narsa yo'q.

⚠ PARTIYALAB: har 50 kadr alohida tranzaksiyada yopiladi. Bitta ulkan
  tranzaksiya uzilsa hammasi qaytardi va jarayon qayerda to'xtagani
  ko'rinmasdi; partiya bilan esa uzilish eng ko'pi 50 kadrni qaytaradi va
  qayta yugurish qolganini davom ettiradi (idempotentlik shuni beradi).
"""

import asyncio
import uuid

from app.services.review_seed import seed_snapshot
from app.settings import get_settings
from sbozor_core.enums import ActorKind
from sbozor_core.tenancy import set_tenant_context
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

MID = uuid.UUID("01a01f40-69e4-7c73-9096-c3b93c053403")
PARTIYA = 50


async def kontekst(ses: AsyncSession) -> None:
    await set_tenant_context(
        ses,
        market_id=MID,
        actor_id=None,
        actor_kind=ActorKind.SYSTEM,
        request_id="backfill-seed",
    )


async def sanoq(mk: async_sessionmaker[AsyncSession]) -> tuple[int, int]:
    async with mk() as ses, ses.begin():
        await kontekst(ses)
        h = (await ses.execute(text("select count(*) from occupancy_events"))).scalar_one()
        n = (await ses.execute(text("select count(*) from review_assignments"))).scalar_one()
    return h, n


async def main() -> None:
    eng = create_async_engine(get_settings().database_url)
    mk = async_sessionmaker(eng, expire_on_commit=False)

    h0, n0 = await sanoq(mk)
    print(f"OLDIN : occupancy_events={h0}  review_assignments={n0}")

    async with mk() as ses, ses.begin():
        await kontekst(ses)
        idlar = [
            r[0]
            for r in (
                await ses.execute(
                    text("""
                select distinct s.id, s.business_date, s.slot_time
                  from snapshots s
                  join camera_zones z
                    on z.camera_id = s.camera_id and z.is_active
                 where s.quality_verdict = 'ok'
                 order by s.business_date, s.slot_time
            """)
                )
            ).all()
        ]
    print(f"ishlov beriladigan kadr: {len(idlar)}")

    hodisa = navbat = 0
    for boshi in range(0, len(idlar), PARTIYA):
        bolak = idlar[boshi : boshi + PARTIYA]
        async with mk() as ses, ses.begin():
            await kontekst(ses)
            for sid in bolak:
                r = await seed_snapshot(ses, market_id=MID, snapshot_id=sid)
                hodisa += r.events_created
                navbat += r.seeded
        print(
            f"  {min(boshi + PARTIYA, len(idlar)):>4}/{len(idlar)}  hodisa={hodisa} navbat={navbat}"
        )

    h1, n1 = await sanoq(mk)
    print(f"KEYIN : occupancy_events={h1}  review_assignments={n1}")
    print(f"QO'SHILDI: hodisa +{h1 - h0}  navbat +{n1 - n0}")
    await eng.dispose()


if __name__ == "__main__":
    asyncio.run(main())
