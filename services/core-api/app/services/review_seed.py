"""Urug' rejimi — MODEL YO'Q PAYTDA nazoratchi navbatini to'ldirish.

=============================================================================
⛔⛔ TOVUQ-TUXUM MUAMMOSI VA UNING YECHIMI (260828).

Nazoratchi navbati `review_assignments` dan quriladi, u esa
`occupancy_events` GA BOG'LANGAN (`occupancy_event_id NOT NULL`).
Hodisani cv-service yozadi, cv-service esa MODEL talab qiladi
(`ops/models/rfdetr-large.onnx`).

Model o'qitish uchun DATASET kerak. Dataset nazoratchi javoblaridan
(`zone_reviews`) yig'iladi. Nazoratchi javob berishi uchun navbat kerak.
Navbat uchun hodisa kerak. Hodisa uchun model kerak.

    model -> hodisa -> navbat -> javob -> dataset -> model

Halqa YOPIQ va u O'ZI OCHILMAYDI. Birinchi kunda dataset ham, model ham
yo'q — ya'ni tizim hech qachon boshlanmasdi.

⛔ YECHIM — HODISANI MODELSIZ YOZISH, LEKIN UNI MODEL QARORI DEB
   KO'RSATMASLIK:

     verdict       = 'uncertain'   -> tizim BILMAYDI
     confidence    = 0.0           -> ishonch YO'Q (taxmin ham emas)
     model_version = 'seed-v0'     -> bu MODEL EMAS, urug'

Uchala maydon birga o'qiladi: keyingi ijrochi hisobotdagi `seed-v0`
qatorini ko'rib, uni model bashorati deb o'ylay olmaydi. `uncertain`
esa mavjud navbatga TABIIY tushadi — `ix_occupancy_events_uncertain`
indeksi va `review_assignments.queue_kind='uncertain'` o'zgarmaydi.

=============================================================================
⚠ ANIQLIK HISOBOTIGA TUSHMAYDI. `zone_reviews.shown_ai_verdict=false`
  va `queue_kind='uncertain'` — ya'ni bu javoblar `train` maqsadida
  qoladi. Aniqlik esa FAQAT `blind_audit` + `eval` dan hisoblanadi
  (`accuracy_report.py`). Urug' javoblarini aniqlikka qo'shish
  «model o'zini o'zi baholadi» degan ma'noni berardi — model YO'Q
  bo'lgan holatda bu son umuman ma'nosiz.

⚠ MODEL PAYDO BO'LGACH BU REJIM O'CHIRILADI: `OCCUPANCY_SEED_MODE=0`.
  Ikkalasi birga ishlasa bitta kadr+zona uchun IKKI qaror bo'lardi
  (`uq_occupancy_events_market_id_snapshot_zone_model` `model_version`
  ni ham qamragani uchun baza buni RAD ETMAYDI) va patta hisobi qaysi
  birini olishini bilmasdi.
=============================================================================
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

log = structlog.get_logger(__name__)

SEED_MODEL_VERSION = "seed-v0"
"""`model_version` qiymati — HISOBOTDA KO'RINADI va shu sababdan
«model» ga o'xshamaydigan qilib tanlangan."""

SEED_CONFIDENCE = Decimal("0.0000")
"""Ishonch NOL. `uncertain` oynasining o'rtasi (0.45) EMAS: o'rtacha
qiymat «model taxmin qildi» degan ma'noni berardi, holbuki hech qanday
model ishlamagan."""

SEED_THRESHOLDS_VERSION = 1
"""Chegaralar reyestri versiyasi — urug'da ishlatilmaydi, lekin ustun
`NOT NULL` va `> 0`."""


@dataclass
class SeedResult:
    """Bir kadr uchun natija — NOL ham natija (`DayCloseResult` qoidasi)."""

    events_created: int = 0
    """Yangi yozilgan `occupancy_events` qatorlari."""
    seeded: int = 0
    """NAVBATGA qo'shilgan qatorlar — nazoratchi shuncha kadr ko'radi.

    ⚠ `events_created` DAN FARQ QILISHI MUMKIN va bu xato emas: hodisa
      allaqachon bor, navbat esa yo'q bo'lsa (birinchi urinish yarim
      bajarilgan) — bu yugurish faqat navbatni tiklaydi.
    """


_INSERT_EVENT = text(
    """
    INSERT INTO occupancy_events
        (market_id, snapshot_id, snapshot_is_billable, camera_zone_id,
         business_date, slot_time, verdict, confidence,
         model_version, thresholds_version, zone_version)
    SELECT :market_id, s.id, true, cz.id, s.business_date, s.slot_time,
           'uncertain', :confidence, :model_version, :thresholds, cz.version
      FROM snapshots s
      JOIN camera_zones cz
        ON cz.market_id = s.market_id
       AND cz.camera_id = s.camera_id
       AND cz.is_active
     WHERE s.market_id = :market_id
       AND s.id = :snapshot_id
       AND s.quality_verdict = 'ok'
    ON CONFLICT ON CONSTRAINT uq_occupancy_events_market_id_snapshot_zone_model
    DO NOTHING
    RETURNING id
    """
)
"""Kadr x FAOL ZONA -> `uncertain` hodisa.

⛔ `quality_verdict = 'ok'` SHARTI MAJBURIY: `snapshots.is_billable`
   generatsiya qilingan ustun va `occupancy_events` ning kompozit FK'si
   `(id, true)` juftligini talab qiladi. Yaroqsiz kadr uchun bu juftlik
   jadvalda UMUMAN yo'q — `INSERT` baza darajasida yiqilardi (D-21,
   `capture.py` dagi `enqueue_detect` sharti bilan bir xil sabab).

⚠ `cz.version` HODISAGA YOZILADI: zona keyin qayta chizilsa, eski
  javob qaysi konturga tegishli ekani ma'lum qoladi. Busiz dataset
  «qaysi to'rtburchak edi?» savoliga javob bera olmasdi.
"""

_INSERT_ASSIGNMENT = text(
    """
    INSERT INTO review_assignments (market_id, occupancy_event_id, queue_kind, purpose)
    SELECT oe.market_id, oe.id, 'uncertain', 'train'
      FROM occupancy_events oe
     WHERE oe.market_id = :market_id
       AND oe.snapshot_id = :snapshot_id
       AND oe.model_version = :model_version
    ON CONFLICT ON CONSTRAINT uq_review_assignments_occupancy_event_id
    DO NOTHING
    RETURNING id
    """
)
"""Hodisa -> nazoratchi navbati.

⛔ `purpose='train'` VA `queue_kind='uncertain'` — ikkalasi ham
   ATAYIN. `blind_audit` bo'lsa `audit_round_id` talab qilinardi
   (`ck_review_assignments_blind_audit_needs_round`), `eval` esa
   aniqlik hisobiga tushardi — model yo'q holatda bu son ma'nosiz.

⛔⛔ MANBA — YANGI YOZILGAN QATORLAR EMAS, SHU KADRNING BARCHA URUG'
    HODISALARI. Farq nozik va u 260828 da jonli o'lchandi:

    `INSERT ... RETURNING` faqat YANGI qatorlarni beradi. Hodisa
    allaqachon bor, navbat esa yo'q bo'lsa (birinchi urinish yarim
    bajarilgan, yoki qator qo'lda o'chirilgan) — `RETURNING` bo'sh
    qaytardi va kadr NAVBATSIZ qolardi. Uni keyin topishning yo'li
    yo'q: hech qayerda «bu kadr ko'rilmagan» degan belgi qolmasdi.

    Endi so'rov hodisalardan boshlanadi va navbatga qo'yish o'zining
    `ON CONFLICT` i bilan idempotent. Ya'ni tozalash — HODISA emas,
    NAVBAT darajasida.
"""


async def seed_snapshot(session: AsyncSession, *, market_id: UUID, snapshot_id: UUID) -> SeedResult:
    """Bitta kadr uchun urug' hodisalarini va navbatni yozadi.

    Args:
        session: TENANT sessiyasi — RLS `market_id` ni o'zi qo'llaydi.
        market_id: bozor.
        snapshot_id: yangi yozilgan kadr.

    Returns:
        `SeedResult`. Zona chizilmagan kamera uchun `zones=0` —
        bu XATO EMAS: kameralarning ko'pchiligida zona yo'q va ular
        `/cameras` sahifasida «zonasiz kamera» deb sanaladi.
    """
    hodisalar = (
        await session.execute(
            _INSERT_EVENT,
            {
                "market_id": market_id,
                "snapshot_id": snapshot_id,
                "confidence": SEED_CONFIDENCE,
                "model_version": SEED_MODEL_VERSION,
                "thresholds": SEED_THRESHOLDS_VERSION,
            },
        )
    ).all()

    navbat = (
        await session.execute(
            _INSERT_ASSIGNMENT,
            {
                "market_id": market_id,
                "snapshot_id": snapshot_id,
                "model_version": SEED_MODEL_VERSION,
            },
        )
    ).all()

    natija = SeedResult(events_created=len(hodisalar), seeded=len(navbat))

    if natija.seeded:
        log.info(
            "review_seeded",
            snapshot_id=str(snapshot_id),
            seeded=natija.seeded,
            events_created=natija.events_created,
            model_version=SEED_MODEL_VERSION,
        )
    return natija
