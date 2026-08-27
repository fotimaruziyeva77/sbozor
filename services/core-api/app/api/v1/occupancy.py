"""Bandlik va aniqlik hisoboti — DIREKTORNING yuzasi, nazoratchiniki EMAS (AI-04…AI-06).

=============================================================================
⛔⛔ UCHALA MARSHRUT HAM `REPORT_VIEW` OSTIDA — VA BU XAVFSIZLIK EMAS,
    O'LCHOVNI ASRASH.

`ROLE_PERMISSIONS[INSPECTOR]` — AYNAN `{OCCUPANCY_REVIEW}`, ya'ni
nazoratchi bu sahifani UMUMAN ocha olmaydi (T-05-58). Sabab
maxfiylikda emas: nazoratchi o'z aniqligini ko'rsa u RAQAMNI
YAXSHILASHGA urinardi va o'lchov o'zi o'lchayotgan narsani
o'zgartirardi. «Tez qaror» sanog'i aynan shu urinishning izi bo'lib
qolardi, ya'ni uni ko'rsatish o'sha izni ham yo'q qilardi.

⛔ NAMUNANI QAYTA TORTADIGAN MARSHRUT YOZILMAGAN (D-17.1) — na bu
   faylda, na boshqasida. «Metodning yo'qligi — KELISHUV EMAS,
   STRUKTURA» (`app/services/storage.py:11-22`), va uning yo'qligi
   05-11 ning OpenAPI skani (`test_no_redraw_endpoint`) bilan
   o'lchanadi.

=============================================================================
⛔ SLOTLARARO AGREGATSIYA BU YERDA YO'Q VA JAVOBDA HAM YO'Q.

Kunlik xulosa «kun davomida kamida bir marta band ko'rindi» deydi,
«pattaga tushadi» DEMAYDI. «Kamida 2 slotda band» qoidasi — BILL-01,
6-faza (§D.11). Javobda `amount`, `soum` yoki `patta` ma'nosidagi
birorta maydon YO'Q: bo'lsa direktor bu raqamni kunlik daromad deb
o'qib, 6-faza kelganda IKKI XIL son ko'rardi.

=============================================================================
⚠ O'QISH AUDITI BU ROUTERDA E'LON QILINMAYDI (`reviews.py` bilan bir xil
  qaror): javobda shaxsiy ma'lumot yo'q (rasta raqami, hudud nomi,
  sanoqlar). Dalil KADRINING o'zi `GET /snapshots/{id}/image` proxysidan
  keladi va AYNAN o'sha marshrut `audit_read` yozadi (T-05-47).

⚠ HUQUQ IMZODA (`camera_zones.py` / `reviews.py` shakli), dekoratorda
  EMAS.
=============================================================================
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import TYPE_CHECKING, Annotated, Final
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sbozor_core.timeutil import business_today

from app.deps import (
    Principal,
    TenantSessionDep,
    require_any_permission,
    require_permission,
)
from app.repositories.occupancy_repo import OccupancyRepository
from app.schemas import (
    ConfusionMatrixOut,
    OccupancyAccuracyResponse,
    OccupancyDayResponse,
    OccupancyRoundResponse,
    OccupancyStallItem,
    ProportionIntervalOut,
)
from app.security.rbac import Permission
from app.services.accuracy_report import (
    MIN_SAMPLE_FOR_PERCENT,
    accuracy_report,
    is_fast_decision,
)

if TYPE_CHECKING:
    from app.services.accuracy_report import ProportionInterval

# ⚠ `date` VA `UUID` ISH VAQTIDA IMPORT QILINADI, `TYPE_CHECKING` OSTIDA
#   EMAS — VA BU O'LCHANGAN ZARURIYAT (`reviews.py` da ham aynan shunday).
#   `from __future__ import annotations` ostida annotatsiyalar SATR bo'lib
#   qoladi va FastAPI ularni Pydantic uchun YECHA olmaydi:
#   `PydanticUserError: ... is not fully defined`. Nosozlik marshrutda
#   emas, OpenAPI sxemasini quruvchi meta-testda ko'rinadi.

log = structlog.get_logger(__name__)

__all__ = ["ACCURACY_WINDOW_DAYS", "router"]

router = APIRouter(tags=["occupancy"])

ReportViewerDep = Annotated[Principal, Depends(require_permission(Permission.REPORT_VIEW))]
"""⛔ FAQAT ANIQLIK YUZASI UCHUN (`/accuracy`). Sabab — T-05-58: nazoratchi
O'Z aniqligini ko'rsa raqamni yaxshilashga urinardi va o'lchov o'zi
o'lchayotgan narsani o'zgartirardi."""

OCCUPANCY_VIEW_PERMISSIONS = (Permission.REPORT_VIEW, Permission.OCCUPANCY_REVIEW)
"""Kunlik BANDLIK va namuna holatini ikki xil ish uchun ikki xil odam ko'radi.

=========================================================================
⛔ BU DARVOZA 260827 DA QO'SHILDI VA U YARIM QOLGAN O'ZGARISHNI YOPADI.

260820 da klient qatlami nazoratchiga bu sahifani OCHDI (`app/[locale]/
(app)/occupancy/page.tsx` va `components/shell/app-shell.tsx` —
`permission: ["occupancy_review", "report_view"]`), sabab yozilgan holda:
nazoratchi kun bo'yi kadr ko'rib qaror yozadi, lekin o'z ishining
NATIJASINI ko'ra olmasdi. SERVER esa o'sha kuni yangilanmagan.

O'lchangan oqibat (260827, jonli sinov): menyuda «Bandlik» KO'RINADI,
sahifa OCHILADI, `GET /occupancy` esa **403** qaytaradi va UI uni
«Ma'lumot yuklanmadi» deb ko'rsatadi — ya'ni huquq masalasi tarmoq
nosozligiga o'xshab qoladi va nazoratchi mavjud bo'lmagan muammoni
qidiradi.

⛔ `/accuracy` BU DARVOZAGA KIRMAYDI va bu butun qarorning yuragi:
   T-05-58 ning sababi aynan ANIQLIK raqamiga tegishli, kunlik bandlikka
   emas. Nazoratchi o'z ishining natijasini ko'radi, o'z BAHOSINI —
   yo'q.

⚠ SIZIB CHIQISH YO'Q: bu yuzada pul maydoni umuman yo'q — javob
  `stalls/occupied/empty/no_coverage/human_confirmed` sanoqlaridan iborat.
=========================================================================
"""

OccupancyViewerDep = Annotated[
    Principal, Depends(require_any_permission(*OCCUPANCY_VIEW_PERMISSIONS))
]

ACCURACY_WINDOW_DAYS: Final[int] = 30
"""Aniqlik hisobotining STANDART davri — oxirgi 30 kun (§11.5).

D-13: kuniga 30 band -> oyiga ~900 javob -> +-2–3 f.p. oraliq. Haftalik
davr +-5–7 f.p. berardi, ya'ni raqam «yaxshilandi/yomonlashdi» degan
xulosaga yetarli bo'lmasdi.

⛔ DAVR TANLAGICHI YO'Q (§16.2 — 8-fazaning hisobot yuzasi), lekin
   `from`/`to` parametrlari BOR: ular klientga emas, TESTGA va kelajakdagi
   eksportga kerak. Standart qiymat serverda, ya'ni klient davrni
   qayta hisoblamaydi.
"""


def _market_id(principal: Principal) -> UUID:
    """Sessiyadagi bozor — `reviews.py` dagi jufti bilan bir xil shakl."""
    market_id = principal.market_id
    if market_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail={"error_code": "market_not_selected"}
        )
    return market_id


def _interval(interval: ProportionInterval) -> ProportionIntervalOut:
    return ProportionIntervalOut(point=interval.point, lower=interval.lower, upper=interval.upper)


@router.get("", response_model=OccupancyDayResponse)
async def occupancy_day(
    principal: OccupancyViewerDep,
    session: TenantSessionDep,
    day: Annotated[date | None, Query()] = None,
) -> OccupancyDayResponse:
    """Kunlik bandlik xulosasi va rastalar ro'yxati (`REPORT_VIEW`).

    ⛔ BESHALA HISOBLAGICH HAM HAR DOIM QAYTADI — nol bo'lganda ham.
       «Bugun hech kim ko'rilmadi» bilan «hisoblagich ishlamayapti» bir
       xil ko'rinmasligi kerak (4-fazadagi «yo'qlikka alert» prinsipi).

    ⚠ `day` BERILMASA BUGUNGI KUN. Bugungi kunning materializatsiyasi
      ERTASI kuni 03:40 da bo'ladi (`worker.py::DAY_CLOSE_CRON`), ya'ni
      bugungi javob odatda BO'SH bo'ladi va bu KUTILGAN: bandlik kun
      tugagach hisoblanadi. Klient buni `occupancy.noFutureDays` matni
      bilan aytadi (05-14).
    """
    market_id = _market_id(principal)
    business_date = day if day is not None else business_today()
    repo = OccupancyRepository(session, market_id)

    summary = await repo.day_summary(business_date)
    stalls = await repo.day_stalls(business_date)

    return OccupancyDayResponse(
        day=business_date,
        stalls=summary.stalls,
        occupied=summary.occupied,
        empty=summary.empty,
        default_empty=summary.default_empty,
        no_coverage=summary.no_coverage,
        human_confirmed=summary.human_confirmed,
        items=[
            OccupancyStallItem(
                stall_id=stall.stall_id,
                stall_code=stall.stall_code,
                zone_name=stall.zone_name,
                status=stall.bucket,
                slots=stall.slots,
                occupied_slots=stall.occupied_slots,
                human_confirmed=stall.human_confirmed,
            )
            for stall in stalls
        ],
    )


@router.get("/accuracy", response_model=OccupancyAccuracyResponse)
async def occupancy_accuracy(
    principal: ReportViewerDep,
    session: TenantSessionDep,
    from_date: Annotated[date | None, Query(alias="from")] = None,
    to_date: Annotated[date | None, Query(alias="to")] = None,
) -> OccupancyAccuracyResponse:
    """Chalkashlik matritsasi, uch Wilson oralig'i va bazaviy ulush (`REPORT_VIEW`).

    =======================================================================
    ⛔ FILTRLASH BU YERDA QILINMAYDI — u `accuracy_report()` DA.

    Repozitoriy davr ichidagi BARCHA topshiriqni beradi (javobsizlarini
    ham), ikki filtr (`purpose = 'eval'`, `queue_kind = 'blind_audit'`)
    esa sof funksiyada yashaydi. Ularni bu yerga yoki SQL ga ko'chirish
    kafolatni IKKI joyga bo'lardi va sof funksiyaning testi mahsulot
    yo'lini qo'riqlamay qolardi.
    =======================================================================

    ⚠ DAVRNING OXIRI KIRADI (`<=`): «oxirgi 30 kun» degan gap kunning
      O'ZINI ham qamraydi. `periods.py` ning `[)` konventsiyasi bu yerga
      TEGISHLI EMAS — u sotuvchi biriktirish davri uchun va uning sababi
      (almashinuv kuni) bu yerda mavjud emas.
    """
    market_id = _market_id(principal)
    end = to_date if to_date is not None else business_today()
    start = from_date if from_date is not None else end - timedelta(days=ACCURACY_WINDOW_DAYS - 1)

    repo = OccupancyRepository(session, market_id)
    report = accuracy_report(await repo.accuracy_rows(start, end))

    return OccupancyAccuracyResponse(
        from_date=start,
        to_date=end,
        drawn=report.drawn,
        answered=report.answered,
        unanswered=report.unanswered,
        dont_know=report.dont_know,
        matrix=ConfusionMatrixOut(
            true_occupied=report.matrix.tp,
            false_occupied=report.matrix.fp,
            false_empty=report.matrix.fn,
            true_empty=report.matrix.tn,
        ),
        n=report.n,
        measured=report.measured,
        min_sample=MIN_SAMPLE_FOR_PERCENT,
        base_rate=report.base_rate,
        correct=_interval(report.correct),
        false_occupied=_interval(report.false_occupied),
        false_empty=_interval(report.false_empty),
    )


@router.get("/round", response_model=OccupancyRoundResponse)
async def occupancy_round(
    principal: OccupancyViewerDep,
    session: TenantSessionDep,
    day: Annotated[date | None, Query()] = None,
) -> OccupancyRoundResponse:
    """Kunlik ko'r audit turining holati — O'LCHOVNING O'ZI (`REPORT_VIEW`).

    ⛔ URUG' QAYTARILMAYDI va «qayta tortish» yo'li YO'Q (D-17.1).

    ⛔ JAVOBSIZLAR SONI NOL BO'LGANDA HAM QAYTADI: javobsiz band
       namunadan CHIQMAYDI, u «javobsiz» bo'lib sanaladi (§C.8,
       4-dushman).

    ⚠ «TEZ QAROR» SANOG'I SHU YERDA HISOBLANADI, SQL DA EMAS:
      `is_fast_decision()` chegara (2000 ms) VA `NULL` qoidasini bitta
      joyda ushlab turadi. `decision_ms` `NULL` bo'lganlar sanoqqa
      KIRMAYDI — Valkey uzilishi nazoratchining aybiga aylanmasligi
      kerak (05-10, deviatsiya #8).
    """
    market_id = _market_id(principal)
    business_date = day if day is not None else business_today()

    round_status = await OccupancyRepository(session, market_id).round_status(business_date)

    if round_status is None:
        # ⚠ «TORTILMAGAN» — «HAMMASI BAJARILDI» EMAS. Ikkalasini bir xil
        #   ko'rsatish tortish jobi butunlay o'lgan kunni muvaffaqiyat
        #   bo'lib ko'rsatardi (`review_repo._HAS_ANY_ROUND` qoidasi).
        return OccupancyRoundResponse(
            day=business_date,
            drawn=False,
            round_no=None,
            drawn_at=None,
            frame_size=None,
            sample_size=None,
            answered=None,
            unanswered=None,
            dont_know=None,
            fast_decisions=None,
        )

    return OccupancyRoundResponse(
        day=business_date,
        drawn=True,
        round_no=round_status.round_no,
        drawn_at=round_status.drawn_at,
        frame_size=round_status.frame_size,
        sample_size=round_status.drawn,
        answered=round_status.answered,
        unanswered=round_status.unanswered,
        dont_know=round_status.dont_know,
        fast_decisions=sum(1 for value in round_status.decision_ms if is_fast_decision(value)),
    )
