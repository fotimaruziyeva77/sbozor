"""Nazoratchi navbati — BITTA SO'ROV = BITTA QAROR (AI-03, D-18).

=============================================================================
⛔⛔ OMMAVIY ENDPOINT YO'Q — VA BU KELISHUV EMAS, STRUKTURA.

Bu faylda massiv qabul qiladigan marshrut YOZILMAGAN va yozilmaydi.
Sabab UI da emas, MA'LUMOTDA: navbatning butun maqsadi — o'qitishga
yaroqli YORLIQ ishlab chiqarish. Rezina-shtamp qilish oson bo'lgan yuza
ma'lumotga O'XSHAGAN shovqin ishlab chiqaradi va o'sha shovqin bilan
tizim aniqligi o'lchanadi.

⚠ «Hammasini tasdiqlash» tugmasini olib tashlash YETARLI EMAS (UI-SPEC
  §7.3): har qatorda ikki tugmali ro'yxat — qadamlari ko'proq bo'lgan
  O'SHA tugma. Ko'z qatordan chiqmaydi, qo'l takrorlaydi.

Shuning uchun qoida API darajasida turadi va uni OpenAPI sxemasini
skanerlaydigan test o'lchaydi (`tests/integration/test_uncertain_queue.py::
test_no_bulk_approve_endpoint`). «METODNING YO'QLIGI — KELISHUV EMAS,
STRUKTURA» (`app/services/storage.py:11-22`): metod mavjud bo'lsa keyingi
tahrirlovchi uni «qulaylik uchun» chaqirardi.
=============================================================================

⛔ NAZORATCHI JAVOB BERISHDAN OLDIN TIZIM JAVOBINI KO'RMAYDI.

`ReviewItemResponse` da `verdict`, `confidence`, `model_version`,
`thresholds_version`, `purpose` va `queue_kind` maydonlari UMUMAN e'lon
qilinmagan (`app/schemas.py` bo'lim izohi). Bu AI-03 talab qilganidan
QATTIQROQ va sabab o'lchangan: band navbatga tushgan bo'lsa tizim
allaqachon ishonchsiz, ya'ni uning moyilligi deyarli ma'lumot
tashimaydi, lekin TO'LIQ ankorlash kuchiga ega. Yashirishning narxi NOL.

Oshkor ma'lumot FAQAT `POST .../answer` ning javobida bo'ladi va u
`useMutation` ning natijasi sifatida keladi — birorta `GET` uni
qaytarmaydi, ya'ni prefetch yo'li yopiq (UI-SPEC §7.7).

=============================================================================
⛔ `decision_ms` SERVERDA O'LCHANADI VA KLIENT QIYMATIGA ISHONILMAYDI.

Band berilgan payt Valkey'da qoladi (`_CLAIM_KEY_PREFIX`), javob
kelganda farq hisoblanadi. `AnswerRequest` da bunday maydon YO'Q, ya'ni
klient yuborgan qiymat Pydantic tomonidan JIMGINA tashlanadi.

⚠ NATIJA NAZORATCHIGA KO'RSATILMAYDI VA HECH NIMANI TO'SMAYDI (UI-SPEC
  §7.3): ko'rsatilsa u o'lchovni chetlab o'tishni o'rganardi (sekinroq
  bosish — real diqqat emas, IMITATSIYA). Son faqat Y-4 hisobotiga
  chiqadi.

⚠ O'LCHOV TOPILMASA `NULL` YOZILADI, XATO BERILMAYDI. `decision_ms`
  DIAGNOSTIKA, javob esa MAHSULOT: Valkey uzilishi nazoratchini ishdan
  to'xtatmasligi kerak. `zone_reviews.decision_ms` shu sababdan
  `nullable` (05-05).
=============================================================================

CROSS-TENANT VA BOSHQA NAVBAT — HAR DOIM 404 (T-05-25), 403 EMAS.

Begona bozorning topshirig'i, mavjud bo'lmagan `id` va KO'R AUDIT
topshirig'i (`queue_kind` filtri) — uchalasi ham AYNAN bir xil javob
oladi. Farqlash javob kodi bo'yicha identifikator sanab chiqish yo'lini
ochardi va «bu topshiriq ko'r auditda» degan ma'lumotni ham oshkor
qilardi (D-14: nazoratchi `purpose` ni ham, navbat a'zoligini ham
bilmasligi kerak).

-----------------------------------------------------------------------------
⚠ O'QISH AUDITI BU ROUTERDA E'LON QILINMAYDI va bu `camera_zones.py` /
  `stalls.py:348-369` bilan bir xil qaror: javobda shaxsiy ma'lumot
  YO'Q (rasta raqami, hudud nomi, kanal, kontur). DALIL KADRINING O'ZI
  esa `GET /api/v1/snapshots/{id}/image` proxysidan keladi va AYNAN
  o'sha marshrut `audit_read` yozadi (T-05-47) — ya'ni «kim qaysi
  tasvirni ko'rdi» savoli javobsiz qolmaydi.

  `zone_reviews` ning O'ZGARISHI esa DB-trigger orqali auditda
  (`AUDITED_TABLES`).

⚠ HUQUQ IMZODA (`camera_zones.py` / `zones.py` shakli), dekoratorda EMAS.
  03-07 da o'lchangan tartib xavfi (403 `audit_read` dan KEYIN ishlashi)
  bu yerda MAVJUD EMAS, chunki bu router `audit_read` ni umuman e'lon
  qilmaydi. Da'vo mexanizm bilan emas, XULQ bilan qulflangan:
  `test_director_cannot_reach_the_queue` 403 ni VA rad etilgan so'rovdan
  keyin audit jurnalida yangi qator qolmaganini o'lchaydi.
-----------------------------------------------------------------------------

MARSHRUT TARTIBI: statik segmentlar (`/uncertain/next`, `/blind/next`,
`/blind/{review_assignment_id}/answer`, `/budget`) `{review_assignment_id}`
shablonidan OLDIN (`stalls.py:3-11` qoidasi).

⚠⚠ `/blind/...` UCHUN BU TARTIB BUGUN HAM YAGONA HIMOYA:
   `POST /review/{review_assignment_id}/answer` shabloni `blind` so'zini
   UUID o'rniga qabul qilishga urinardi (422 bilan tugardi), lekin
   `POST /review/blind/{id}/answer` ikki segmentli va u shablonga umuman
   tushmaydi. Tartib buzilganda ham javob 422 bo'lardi, ya'ni nosozlik
   «marshrut yo'q» emas, «noto'g'ri UUID» bo'lib ko'rinardi.

=============================================================================
⛔ KO'R AUDIT — ALOHIDA MARSHRUT, `?blind=true` PARAMETRI EMAS.

Bitta marshrutni bayroq bilan ikki xulqqa bo'lish ikkala navbat uchun
BITTA serializer degani bo'lardi va o'shanda «AI maydonlari payloadda
UMUMAN yo'q» kafolati SHART BILAN himoyalangan bo'lardi — ya'ni
konventsiyaga aylanardi. Ikki alohida tip (`ReviewItemResponse` va
`BlindItemResponse`) esa uni STRUKTURAGA aylantiradi.

⚠ Ajratishning IKKINCHI sababi frontendda: G-12 darvozasi FAYL
  TO'PLAMINI skanerlaydi (`components/blind-audit/**`) va u faqat ko'r
  audit alohida marshrut bo'lgandagina ma'noga ega (UI-SPEC §4.3).
=============================================================================
"""

from __future__ import annotations

import time as _time
from datetime import date
from typing import Annotated, Final
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from redis.exceptions import RedisError
from sbozor_core.enums import OccupancyVerdict, ReviewQueueKind
from sbozor_core.timeutil import business_today
from sqlalchemy.exc import IntegrityError

from app.deps import CacheDep, Principal, SettingsDep, TenantSessionDep, require_permission
from app.repositories.review_repo import ClaimedReview, ReviewRepository
from app.repositories.stall_repo import sqlstate_of
from app.schemas import (
    AnswerRequest,
    AnswerResponse,
    BlindItemResponse,
    QueueBudget,
    ReviewBudgetResponse,
    ReviewItemResponse,
)
from app.security.rbac import Permission
from app.services.occupancy_errors import (
    BLIND_ANSWER_LOCKED,
    REVIEW_ALREADY_ANSWERED,
    REVIEW_BUDGET_EXHAUSTED,
    REVIEW_QUEUE_EMPTY,
    REVIEW_SAMPLE_NOT_DRAWN,
)

# `UUID` `if TYPE_CHECKING:` ostiga QO'YILMAYDI: FastAPI yo'l
# parametrlarining annotatsiyasini ISH PAYTIDA o'qiydi (`get_type_hints`),
# ya'ni import faqat tip tekshiruvida bo'lsa marshrut `NameError` bilan
# yiqilardi (`camera_zones.py:102-105` dagi bilan bir xil sabab).
log = structlog.get_logger(__name__)

router = APIRouter(tags=["review"])

ReviewerDep = Annotated[Principal, Depends(require_permission(Permission.OCCUPANCY_REVIEW))]

UNIQUE_VIOLATION = "23505"
"""Ikkinchi javob — `uq_zone_reviews_review_assignment_id`.

Poyga DB'GA TOPSHIRILADI: «avval javob bormi?» deb so'rash ikki oynani
(yoki ikki bosishni) bir xil bo'sh holatni ko'rgan holda o'tkazib
yuborardi va ikkinchisi birinchisining javobini bosib o'tishga urinardi
(`nvr_repo.py:509-517` naqshi).
"""

SHOWN_AI_VERDICT: Final[bool] = False
"""`zone_reviews.shown_ai_verdict` — SERVER hisoblaydi, klient YUBORMAYDI.

=============================================================================
⛔ QIYMAT IKKALA NAVBAT UCHUN HAM `False` VA BU KONVENTSIYA EMAS, FAKT.

Bu fazada tizim javobini javobdan OLDIN ko'rsatadigan YUZA YO'Q: na
noaniq navbatda, na ko'r auditda (UI-SPEC §7.1). Ya'ni `True` yozadigan
kod yo'lining O'ZI mavjud emas.

Qiymat shu yerda BITTA joyda turadi va uning halolligi
`test_next_item_has_no_system_answer` bilan MEXANIK bog'langan: javob
payloadi rekursiv skanerlanadi va tizim javobining birorta izi topilsa
test qizaradi. Ya'ni «`False` yozib qo'ydik» degan da'vo emas,
«ko'rsatadigan hech nima yo'q» degan O'LCHANGAN holat.

⚠ DB `CHECK` (`blind_audit_not_shown`) IKKINCHI QATLAM va u faqat ko'r
  auditni qamraydi. Noaniq navbat uchun kafolat FAQAT shu yerda — aynan
  shuning uchun konstanta nomlangan va izohlangan, `False` literali
  chaqiruv joyida qoldirilmagan.
=============================================================================
"""

_CLAIM_KEY_PREFIX: Final[str] = "review:claim"
_CLAIM_TTL_SECONDS: Final[int] = 3600
"""Band berilgan payt Valkey'da qancha turadi.

Bir soat — sessiyaning oqilona yuqori chegarasi (UI-SPEC §7.3: bir
ekranda bitta band). Muddat o'tsa o'lchov `NULL` bo'ladi, javob esa
baribir yoziladi.

⚠ SOZLAMAGA CHIQARILMADI: qiymat MAHSULOT qarorini ifodalamaydi va uni
  `.env` ga chiqarish «byudjet» kabi o'lchanadigan sozlamalar yonida
  turib, ularning maqomini pasaytirardi (04-07 dagi `JOBS_QUEUE`
  qarorining bir sinfi).
"""


def _market_id(principal: Principal) -> UUID:
    """Tanlangan bozor (`zones.py` / `camera_zones.py` dagi jufti bilan bir xil)."""
    if principal.market_id is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="market_not_selected",
        )
    return principal.market_id


def _not_found() -> HTTPException:
    """Begona bozor, mavjud bo'lmagan `id` VA boshqa navbat — bir xil javob."""
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found")


def _conflict(code: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=code)


def _claim_key(market_id: UUID, reviewer_id: UUID, assignment_id: UUID) -> str:
    """Valkey kaliti — bozor, NAZORATCHI va topshiriq bo'yicha.

    ⚠ `reviewer_id` KALITNING BIR QISMI: bandni A nazoratchi olib, B
      javob bersa o'lchov MA'NOSIZ bo'lardi (B ning «qaror vaqti» A ning
      ekran ochganidan boshlab sanalardi). Bunday holatda o'lchov
      topilmaydi va `decision_ms` `NULL` bo'ladi — bu TO'G'RI natija.
    """
    return f"{_CLAIM_KEY_PREFIX}:{market_id}:{reviewer_id}:{assignment_id}"


async def _remember_claim(cache: CacheDep, key: str) -> None:
    """Band berilgan paytni yozadi; Valkey yiqilsa JIM o'tadi.

    Xatoni yutish ATAYIN: bu qadam DIAGNOSTIKA uchun va uning nosozligi
    nazoratchini navbatdan mahrum qilmasligi kerak (`deps.py::
    invalidate_user_state()` bilan bir xil qaror va bir xil sabab).
    """
    try:
        await cache.set(key, str(_time.monotonic_ns()), ex=_CLAIM_TTL_SECONDS)
    except RedisError as exc:
        log.warning("review_claim_not_recorded", error=str(exc))


async def _measure_decision(cache: CacheDep, key: str) -> int | None:
    """Band berilganidan beri o'tgan millisekundlar (yoki `None`).

    ⚠ `monotonic_ns()` ISHLATILADI, `time.time()` EMAS: jarayon soati
      NTP bilan orqaga surilsa MANFIY farq chiqardi va
      `decision_ms_non_negative` `CHECK` i javobni butunlay rad etardi —
      ya'ni DIAGNOSTIKA nosozligi MAHSULOTNI yiqitardi.

    ⚠ ⛔ SHU SABABDAN IKKI JARAYON O'RTASIDA TAQQOSLAB BO'LMAYDI:
      `monotonic_ns()` boshlanish nuqtasi HAR JARAYONDA boshqa. `core-api`
      bir nechta worker bilan ishga tushirilsa (bugun bitta), band bir
      jarayonda berilib, javob boshqasida kelishi mumkin va farq
      MA'NOSIZ bo'lardi. Shuning uchun manfiy yoki mantiqsiz katta farq
      `None` ga aylantiriladi — «o'lchamadim» «yolg'on o'lchadim» dan
      yaxshiroq.
    """
    try:
        raw = await cache.getdel(key)
    except RedisError as exc:
        log.warning("review_decision_not_measured", error=str(exc))
        return None
    if raw is None:
        return None
    try:
        started = int(raw)
    except (TypeError, ValueError):
        return None
    elapsed_ms = (_time.monotonic_ns() - started) // 1_000_000
    if elapsed_ms < 0 or elapsed_ms > _CLAIM_TTL_SECONDS * 1000:
        return None
    return int(elapsed_ms)


def _blind_item(claimed: ClaimedReview) -> BlindItemResponse:
    """`ClaimedReview` -> KO'R payload.

    ⛔ `has_active_vendor` KO'CHIRILMAYDI VA `BlindItemResponse` DA UNDAY
       MAYDON UMUMAN YO'Q. Repozitoriy uni HAR IKKALA navbat uchun ham
       hisoblaydi (bitta `_CLAIM_TEMPLATE`), lekin ko'r auditda u
       ekranga chiqmaydi: band TASODIFIY tanlangan, ya'ni «bu qarorning
       oqibati bor» qatori namunaning bir qismiga ko'proq e'tibor
       berdirardi — xolis namunadagi notekis diqqat o'lchov asbobining
       O'ZIDAGI og'ish (`app/schemas.py::BlindItemResponse`).
    """
    return BlindItemResponse(
        assignment_id=claimed.assignment_id,
        snapshot_id=claimed.snapshot_id,
        stall_id=claimed.stall_id,
        stall_code=claimed.stall_code,
        zone_name=claimed.zone_name,
        camera_name=claimed.camera_name,
        channel_no=claimed.channel_no,
        business_date=claimed.business_date,
        slot_time=claimed.slot_time,
        polygon=[(float(x), float(y)) for x, y in claimed.polygon],
    )


def _item(claimed: ClaimedReview) -> ReviewItemResponse:
    return ReviewItemResponse(
        assignment_id=claimed.assignment_id,
        snapshot_id=claimed.snapshot_id,
        stall_id=claimed.stall_id,
        stall_code=claimed.stall_code,
        zone_name=claimed.zone_name,
        camera_name=claimed.camera_name,
        channel_no=claimed.channel_no,
        business_date=claimed.business_date,
        slot_time=claimed.slot_time,
        polygon=[(float(x), float(y)) for x, y in claimed.polygon],
        has_active_vendor=claimed.has_active_vendor,
    )


@router.get("/uncertain/next", response_model=ReviewItemResponse)
async def next_uncertain_item(
    principal: ReviewerDep,
    session: TenantSessionDep,
    settings: SettingsDep,
    cache: CacheDep,
) -> ReviewItemResponse:
    """Navbatdagi BITTA band (`OCCUPANCY_REVIEW`).

    =======================================================================
    ⛔ BYUDJET NAVBAT BO'SHLIGIDAN OLDIN TEKSHIRILADI VA TARTIB MUHIM.

    Ikkala holat ham «band bermayapman» deydi, lekin ular BOSHQA narsani
    anglatadi (UI-SPEC §8.3, S-7/S-8):

        `review_queue_empty`       -> ISH TUGADI
        `review_budget_exhausted`  -> ISH QOLGAN BO'LISHI MUMKIN

    Teskari tartibda byudjeti tugagan nazoratchi navbat bo'sh bo'lgan
    kuni «hammasi bajarildi» degan YOLG'ON xabarni olardi — va u aynan
    UI-SPEC ogohlantirgan xato. Bu tartibda esa eng yomon holat
    «byudjet tugadi» xabarining navbat bo'sh bo'lganda ham chiqishi:
    xabar noaniq, lekin YOLG'ON emas.
    =======================================================================

    ⚠ MARSHRUT `next` DEB NOMLANGAN VA U IDEMPOTENT EMAS-U, XAVFSIZ:
      javob yozilmagan bo'lsa AYNI band qaytadi (UI-SPEC §4.5), ya'ni
      sahifani yangilash bandni «yo'qotmaydi». Qulf `COMMIT` da tushadi
      va bu ATAYIN (`review_repo` modul docstringi).
    """
    market_id = _market_id(principal)
    repo = ReviewRepository(session, market_id, midpoint=settings.review_uncertain_midpoint)

    answered = await repo.daily_answered_count(
        principal.user_id,
        business_today(),
        queue_kind=ReviewQueueKind.UNCERTAIN.value,
    )
    if answered >= settings.review_uncertain_daily_budget:
        log.info("review_budget_exhausted", answered=answered)
        raise _conflict(REVIEW_BUDGET_EXHAUSTED)

    claimed = await repo.claim_next(queue_kind=ReviewQueueKind.UNCERTAIN.value)
    if claimed is None:
        raise _conflict(REVIEW_QUEUE_EMPTY)

    await _remember_claim(cache, _claim_key(market_id, principal.user_id, claimed.assignment_id))
    return _item(claimed)


@router.get("/blind/next", response_model=BlindItemResponse)
async def next_blind_item(
    principal: ReviewerDep,
    session: TenantSessionDep,
    settings: SettingsDep,
    cache: CacheDep,
) -> BlindItemResponse:
    """KO'R AUDITNING navbatdagi BITTA bandi (`OCCUPANCY_REVIEW`, AI-04).

    =======================================================================
    ⛔ KLIENT QAYSI BAND KELISHINI TANLAY OLMAYDI — URL'DA IDENTIFIKATOR YO'Q.

    Identifikatorli URL uch yo'lni ochardi va uchalasi ham NAMUNANI KEYIN
    TAHRIRLASH (05-RESEARCH §C.8, 4-dushman): orqaga tugmasi bilan javob
    berilgan bandga qaytish; havolani nusxalab qayta ochish; tarixdan
    bandni topib qayta urinish. Sessiya holatining YAGONA manbai —
    SERVER (UI-SPEC §4.5).

    Sahifa yangilansa server O'SHA bandni qaytaradi (javob yozilmagan
    bo'lsa) yoki KEYINGISINI — «yangilab qayta ko'raman» yo'li ham shu
    bilan yopiladi.
    =======================================================================

    ⛔ BO'SHLIKNING IKKI SABABI IKKI XIL KOD BERADI (`_HAS_ANY_ROUND`):
       namuna hali tortilmagan bo'lsa `review_sample_not_drawn`, tortilib
       tugatilgan bo'lsa `review_queue_empty`. Bittaga yig'ish tortish
       jobi butunlay o'lgan kunni «hammasi bajarildi» bilan bir xil
       ko'rsatardi.

    ⚠ BYUDJET NAVBAT BO'SHLIGIDAN OLDIN (`next_uncertain_item` bilan
      bir xil tartib va bir xil sabab).
    """
    market_id = _market_id(principal)
    repo = ReviewRepository(session, market_id)

    answered = await repo.daily_answered_count(
        principal.user_id,
        business_today(),
        queue_kind=ReviewQueueKind.BLIND_AUDIT.value,
    )
    if answered >= settings.review_blind_daily_budget:
        log.info("blind_budget_exhausted", answered=answered)
        raise _conflict(REVIEW_BUDGET_EXHAUSTED)

    claimed = await repo.claim_next_blind()
    if claimed is None:
        drawn = await repo.has_any_round()
        raise _conflict(REVIEW_QUEUE_EMPTY if drawn else REVIEW_SAMPLE_NOT_DRAWN)

    await _remember_claim(cache, _claim_key(market_id, principal.user_id, claimed.assignment_id))
    return _blind_item(claimed)


@router.post("/blind/{review_assignment_id}/answer", response_model=AnswerResponse)
async def answer_blind_item(
    review_assignment_id: UUID,
    payload: AnswerRequest,
    principal: ReviewerDep,
    session: TenantSessionDep,
    cache: CacheDep,
) -> AnswerResponse:
    """Ko'r audit bandiga BITTA, O'ZGARMAS javob (`OCCUPANCY_REVIEW`, D-17.4).

    =======================================================================
    ⛔ IKKINCHI CHAQIRUV **409 `blind_answer_locked`** — `review_already_
       answered` EMAS.

    Ikkala kod ham «javob bor» deydi, lekin ular BOSHQA narsani anglatadi
    va UI ular uchun BOSHQA narsa ko'rsatadi (`occupancy_errors.py`):

        `review_already_answered` — POYGA (ikki oyna, ikki bosish).
                                    Yechim: keyingi bandga o'tish.
        `blind_answer_locked`     — taqiq STRUKTURAVIY. Tizim javobi
                                    OSHKOR QILINGANDAN keyin tahrirlash
                                    imkoniyati o'lchovni yo'q qilardi:
                                    nazoratchi o'z javobini tizimnikiga
                                    moslab qo'yardi va aniqlik 100% ga
                                    intilardi.

    ⛔ UI QAYTA URINISH TUGMASI BERMAYDI (UI-SPEC §4.5) — aynan shuning
       uchun kod ajratilgan.
    =======================================================================

    ⚠ JAVOB OSHKOR MA'LUMOTNI TASHIYDI VA U FAQAT SHU YERDA MAVJUD:
      birorta `GET` marshrut `AnswerResponse` ni qaytarmaydi, ya'ni
      oldindan yuklab qo'yish (prefetch) yo'li yopiq (UI-SPEC §7.7).

    ⚠ `AnswerResponse` QAYTA ISHLATILADI, ikkinchi sxema yozilmaydi:
      uning to'rt maydoni (`system_answer`, `human_answer`, `matched`,
      `locked`) 05-10 da AYNAN shu marshrut uchun tanlangan edi — nomlar
      `verdict`/`confidence` dan ATAYIN farq qiladi, chunki G-12 darvozasi
      `components/blind-audit/**` da o'sha nomlarni taqiqlaydi (§14.3).
    """
    market_id = _market_id(principal)
    decision_ms = await _measure_decision(
        cache, _claim_key(market_id, principal.user_id, review_assignment_id)
    )

    try:
        answered = await ReviewRepository(session, market_id).record_answer(
            review_assignment_id,
            queue_kind=ReviewQueueKind.BLIND_AUDIT.value,
            reviewer_id=principal.user_id,
            human_verdict=payload.human_verdict.value,
            # ⛔ SERVER YOZADI VA QIYMAT KO'R AUDIT UCHUN HAR DOIM `False`.
            #    Klient bu maydonni YUBORA OLMAYDI (`AnswerRequest` da u
            #    umuman yo'q), DB `CHECK (blind_audit_not_shown)` esa
            #    IKKINCHI qatlam.
            shown_ai_verdict=SHOWN_AI_VERDICT,
            decision_ms=decision_ms,
        )
    except IntegrityError as exc:
        if sqlstate_of(exc) == UNIQUE_VIOLATION:
            log.info("blind_answer_locked", assignment_id=str(review_assignment_id))
            raise _conflict(BLIND_ANSWER_LOCKED) from exc
        raise

    if answered is None:
        raise _not_found()

    system_answer = OccupancyVerdict(answered.system_verdict)
    log.info(
        "blind_answer_recorded",
        assignment_id=str(review_assignment_id),
        matched=system_answer == payload.human_verdict,
        decision_measured=decision_ms is not None,
    )
    return AnswerResponse(
        system_answer=system_answer,
        human_answer=payload.human_verdict,
        matched=system_answer == payload.human_verdict,
        # ⛔ KO'R AUDITDA `locked` — SHARTSIZ FAKT: javob o'zgarmas
        #    (`trg_zone_review_immutable`) va ikkinchi qator yozib
        #    bo'lmaydi (`uq_zone_reviews_review_assignment_id`).
        locked=True,
    )


@router.get("/budget", response_model=ReviewBudgetResponse)
async def review_budget(
    principal: ReviewerDep,
    session: TenantSessionDep,
    settings: SettingsDep,
    day: Annotated[date | None, Query(description="Biznes-kun; standart — bugun")] = None,
) -> ReviewBudgetResponse:
    """Ikkala navbatning kunlik hisoblagichi (`OCCUPANCY_REVIEW`).

    ⚠ `day` KELAJAKDAGI kunni ham qabul qiladi va javob `0 / 50` bo'ladi.
      Rad etish (422) hech qanday nosozlikni oldini olmasdi: hisoblagich
      FAKTNI qaytaradi va kelajakda javob bo'lmasligi ham fakt.
    """
    market_id = _market_id(principal)
    repo = ReviewRepository(session, market_id)
    business_date = day if day is not None else business_today()

    uncertain = await repo.daily_answered_count(
        principal.user_id, business_date, queue_kind=ReviewQueueKind.UNCERTAIN.value
    )
    blind = await repo.daily_answered_count(
        principal.user_id, business_date, queue_kind=ReviewQueueKind.BLIND_AUDIT.value
    )
    return ReviewBudgetResponse(
        day=business_date,
        uncertain=_budget(uncertain, settings.review_uncertain_daily_budget),
        blind_audit=_budget(blind, settings.review_blind_daily_budget),
    )


def _budget(answered: int, budget: int) -> QueueBudget:
    """`remaining` HECH QACHON MANFIY EMAS (`QueueBudget` docstringi)."""
    return QueueBudget(answered=answered, budget=budget, remaining=max(0, budget - answered))


@router.post("/{review_assignment_id}/answer", response_model=AnswerResponse)
async def answer_uncertain_item(
    review_assignment_id: UUID,
    payload: AnswerRequest,
    principal: ReviewerDep,
    session: TenantSessionDep,
    cache: CacheDep,
) -> AnswerResponse:
    """BITTA topshiriqqa BITTA javob (`OCCUPANCY_REVIEW`, D-18).

    ⛔ MASSIV QABUL QILINMAYDI. Bu marshrutning massiv varianti YOZILMAGAN
       — modul docstringidagi birinchi blok.

    ⚠ YO'L PARAMETRI `review_assignment_id` DEB NOMLANGAN,
      `assignment_id` DEB EMAS. Ikkinchi nom `PATCH /assignments/
      {assignment_id}` (RASTA-SOTUVCHI biriktirishi) bilan TO'QNASHARDI va
      cross-tenant matritsasining `PARAM_FILLERS` i bu marshrutga BEGONA
      obyekt turini berardi: javob 404 bo'lardi-yu, sababi tenant
      chegarasi emas, «bunday topshiriq umuman yo'q» bo'lardi — ya'ni
      matritsa yashil turib, HECH NIMANI o'lchamasdi.

    Javob OSHKOR ma'lumotni tashiydi va u FAQAT shu yerda mavjud
    (UI-SPEC §7.7).
    """
    market_id = _market_id(principal)
    decision_ms = await _measure_decision(
        cache, _claim_key(market_id, principal.user_id, review_assignment_id)
    )

    try:
        answered = await ReviewRepository(session, market_id).record_answer(
            review_assignment_id,
            queue_kind=ReviewQueueKind.UNCERTAIN.value,
            reviewer_id=principal.user_id,
            human_verdict=payload.human_verdict.value,
            shown_ai_verdict=SHOWN_AI_VERDICT,
            decision_ms=decision_ms,
        )
    except IntegrityError as exc:
        if sqlstate_of(exc) == UNIQUE_VIOLATION:
            log.info("review_already_answered", assignment_id=str(review_assignment_id))
            raise _conflict(REVIEW_ALREADY_ANSWERED) from exc
        raise

    if answered is None:
        raise _not_found()

    system_answer = OccupancyVerdict(answered.system_verdict)
    log.info(
        "review_answer_recorded",
        assignment_id=str(review_assignment_id),
        matched=system_answer == payload.human_verdict,
        decision_measured=decision_ms is not None,
    )
    return AnswerResponse(
        system_answer=system_answer,
        human_answer=payload.human_verdict,
        matched=system_answer == payload.human_verdict,
        # ⛔ HAR DOIM `True` VA BU BEZAK EMAS: ikkinchi javob
        #    `UNIQUE (review_assignment_id)` bilan, tahrir esa
        #    `BEFORE UPDATE` qo'riqchisi bilan rad etiladi. UI-SPEC §7.1
        #    noaniq navbat javobini «o'zgartirish mumkin» deb belgilaydi,
        #    lekin 05-05 SXEMASI buni IMKONSIZ qilgan — ikkala mexanizm
        #    ham `test_uncertain_queue.py` da o'lchanadi.
        locked=True,
    )
