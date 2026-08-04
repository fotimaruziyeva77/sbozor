"""Kun jurnali, kadr detali, RASM PROXYSI va ogohlantirishlar (CAM-06, Y-1…Y-4).

=============================================================================
=============================================================================
⛔⛔ QOIDA 1 — RASM FAQAT PROXY ORQALI; PRESIGNED URL BERILMAYDI (§14.3).

Kadr baytlari YAGONA yo'ldan chiqadi: `GET /snapshots/{id}/image`. Ombor
(SeaweedFS / S3) endpointi brauzerga HECH QACHON ochilmaydi — na
to'g'ridan-to'g'ri, na qayta yo'naltirish bilan, na javob sarlavhasida.

Imzolangan (presigned) havola «arzonroq» ko'rinadi — core-api baytlarni
o'zi uzatmasdi. U TO'RT SABABDAN rad etilgan va to'rttasi ham mustaqil:

  (a) AUDITNI BUZADI. Havola bir marta berilgach, u muddati tugagunicha
      AUDIT YOZUVISIZ ishlaydi. Kadr — bozor tashrifchilarining shaxsiy
      ma'lumoti va uning har o'qilishi `audit_log` ga tushishi kerak
      (2-faza D-09). Nizo paytida «kim bu kadrni ko'rdi?» savoliga javob
      YO'Q bo'lardi — holbuki mahsulotning butun mazmuni dalil.

  (b) RLS'NI CHETLAB O'TADI. Havola sessiyadan MUSTAQIL bo'lib qoladi:
      foydalanuvchining roli o'zgarsa, hisobi bloklansa yoki u boshqa
      bozorga o'tsa ham havola ishlayveradi. Ya'ni bekor qilingan kirish
      huquqi havolaning muddati tugagunicha AMALDA qolardi.

  (c) OMBOR MANZILINI OSHKOR QILADI. To'liq URL brauzer tarixida,
      `Referer` sarlavhasida va nusxalangan havolada paydo bo'lardi —
      ichki xizmat manzili, bucket nomi va imzo parametrlari bilan
      birga. Bu 3-fazadagi go2rtc HTTP yuzasi qoidasining aynan takrori.

  (d) DATA-REZIDENTLIK. Ombor manzili tashqariga chiqmasa, uni
      O'zbekiston hostingiga ko'chirish SOZLAMA o'zgarishi bo'lib
      qoladi (CLAUDE.md ning aniq talabi). Havola brauzerga chiqqan
      zahoti o'sha ko'chish REFAKTORINGGA aylanardi.

Mexanik darvoza: bu faylda `boto3` ning IMZOLANGAN-HAVOLA yasaydigan
ikkala metod nomi ham UCHRAMAYDI; frontend tomonda esa G-4 (`presign` /
`X-Amz` / `seaweed` / `:8333`).

⛔ SHU IZOHDA HAM, QUYIDAGI KODDA HAM O'SHA IKKI METOD NOMINI LITERAL
   SHAKLDA YOZMANG. Darvoza faylni MATN sifatida o'qiydi va izohlarni
   FILTRLAMAYDI — bu ataylab: nomlar API identifikatorlari, taqiqni esa
   so'z bilan ham to'liq tushuntirib bo'ladi (mana shu xatboshi buning
   isboti). Filtrsiz darvoza «nom umuman yozilmagan» degan ancha
   kuchliroq da'voni beradi.
=============================================================================

⛔ QOIDA 2 — `object_key` JAVOBDA UMUMAN YO'Q.

DTO darajasida ham (`SnapshotDetailOut.model_fields` da bunday maydon
yo'q), sarlavhada ham. Bu Qoida 1 ning ikkinchi yuzi: proxy qurilgani
bilan, kalit boshqa marshrutdan chiqib ketsa (c) va (d) sabablari
qaytadi.

=============================================================================
⛔ QOIDA 3 — RASM MARSHRUTIDA `audit_read` MAJBURIY.

`stalls.py:304-345` naqshi. Kadr — bozor tashrifchilarining tasviri,
ya'ni O'zR shaxsiy ma'lumotlar qonuni ostidagi ma'lumot. PostgreSQL'da
`SELECT` uchun trigger YO'Q, ya'ni bu izni FAQAT ilova qatlami qoldira
oladi.

⚠ HUQUQ TALABI MARSHRUT DEKORATORIDA (`dependencies=[...]`), IMZO
  PARAMETRI SIFATIDA EMAS. FastAPI dekorator darajasidagi
  bog'liqliklarni imzo parametrlaridan OLDIN hal qiladi
  (`fastapi/routing.py` ularni `dependant.dependencies` ning BOSHIGA
  qo'yadi), ya'ni 403 olgan so'rov `audit_read` GACHA YETIB BORMAYDI va
  jurnalda «kim nimani ko'rdi» degan YOLG'ON DALIL qolmaydi.

  ⚠⚠ IMZODAGI TARTIB HAM YUK KO'TARADI: `principal` (huquq) `intent`
     (audit) DAN OLDIN turadi. Ularni almashtirish 403 ni audit
     yozuvidan KEYINGA surardi — va o'shanda ko'rmagan odam jurnalda
     ko'rgan bo'lib turardi. Bu `test_snapshot_api.py` ning sabotaj
     o'lchovida aynan shu shaklda tekshirilgan.

⚠ Kun jurnali (`GET /capture-runs`) va kadr DETALI (`GET /snapshots/{id}`)
  auditga TUSHMAYDI va bu ATAYIN — nazorat holati `stalls.py:348-369`.
  Ularning javobida kamera nomi, holat va o'lchovlar bor; TASVIRNING
  O'ZI esa yo'q. Auditni ularga ham yopishtirish jurnalni har jadval
  ochilishida 175 qator bilan to'ldirardi va HAQIQIY hodisani — rasmning
  ochilishini — ko'mib yuborardi (T-02-148).
=============================================================================

⛔ OGOHLANTIRISHNI QO'LDA YOPISH MARSHRUTI QURILMAYDI (§6.7, T-04-73).

`GET /alerts` bor, `PATCH`/`POST`/`DELETE /alerts` YO'Q. Ogohlantirishni
faqat TIKLANISH yopadi (`resolved_at` ni fon sweep'i qo'yadi). Qo'lda
yopish tugmasi adminga muammoni KO'RMASDAN yashirish imkonini berardi —
va aynan «kadr olish to'xtadi» ogohlantirishini yopish mahsulotning
o'zini ko'r qilardi.

-----------------------------------------------------------------------------
CROSS-TENANT JAVOB — HAR DOIM 404 (T-04-75), 403 EMAS. Begona bozorning
`snapshot_id` si repozitoriydan `None` bo'lib qaytadi (RLS + ikkinchi
qatlam predikati) va mavjud bo'lmagan ID bilan AYNAN bir xil javob
oladi — aks holda javobning O'ZI enumeration signali bo'lardi.

XATO XARITASI:

    storage_tier = 'purged'  ->  410 snapshot_object_purged   (D-18)
    StorageError             ->  503 snapshot_storage_unavailable
    topilmadi / begona bozor ->  404 not_found
    kelajakdagi kun          ->  422 (reja hali materializatsiya qilinmagan)

410 (404 EMAS) — `purged` qator MAVJUD va u «kadr bor edi, 455 kun
o'tdi» deydi. 404 esa «bunday kadr bo'lmagan» deb operatorni yo'qolgan
dalilni qidirishga yuborardi.
-----------------------------------------------------------------------------
"""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Annotated
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sbozor_core.enums import SnapshotTier
from sbozor_core.timeutil import business_today

from app.deps import Principal, SettingsDep, TenantSessionDep, require_permission
from app.repositories.alert_repo import AlertRepository
from app.repositories.capture_repo import CaptureRepository
from app.repositories.snapshot_repo import SnapshotRepository
from app.schemas import (
    AlertEventOut,
    AlertListResponse,
    CaptureDayOut,
    CaptureRunOut,
    DaySummaryOut,
    SnapshotDetailOut,
)
from app.security.audit import TABLE_SNAPSHOTS, AuditReadIntent, audit_read
from app.security.rbac import Permission
from app.services import storage
from app.services.storage import StorageError

if TYPE_CHECKING:
    from collections.abc import AsyncIterator
    from decimal import Decimal

    from sbozor_core.models import AlertEvent, Snapshot

    from app.repositories.capture_repo import DaySummary, RunRow

# ⚠ `UUID` VA `date` ISH PAYTIDA KERAK — IKKALASI HAM `if TYPE_CHECKING:`
#   OSTIGA QO'YILMAYDI. FastAPI marshrut annotatsiyalarini ISH PAYTIDA
#   `get_type_hints` bilan o'qiydi va `Annotated[date | None, Query()]`
#   ni Pydantic `TypeAdapter` ga beradi. `date` faqat tip-tekshiruv
#   paytida mavjud bo'lsa u yerda `PydanticUserError: not fully defined`
#   chiqadi — VA U IMPORT PAYTIDA EMAS, birinchi SO'ROVDA chiqadi, ya'ni
#   mypy ham, `import app.main` ham buni ko'rmasdi (o'lchandi: xato
#   faqat `GET /capture-runs` chaqirilganda ko'rindi).
log = structlog.get_logger(__name__)

capture_runs_router = APIRouter(tags=["snapshots"])
router = APIRouter(tags=["snapshots"])
alerts_router = APIRouter(tags=["snapshots"])
"""UCHTA ROUTER, BITTA FAYL — uch RESURS, bitta MAHSULOT ekrani.

`capture-runs`, `snapshots` va `alerts` `04-UI-SPEC.md` §6 dagi bitta
sahifaning uch zonasi, ya'ni ular birga o'qiladi va birga o'zgaradi.
Lekin ular UCH XIL resurs va har biri o'z yo'lida turishi kerak: umumiy
prefiks (`/snapshots/capture-runs`) kun jurnalini kadrning BOLASI qilib
ko'rsatardi — holbuki jurnalning yarmida kadr UMUMAN YO'Q (`missed`,
`failed`, `pending`).
"""

SnapshotViewerDep = Annotated[Principal, Depends(require_permission(Permission.CAMERA_VIEW))]
"""IMZO aliasi — DARVOZA aliasi EMAS (`cameras.py:39-42` qoidasi).

Darvozaning o'zi har marshrutning dekoratorida ochiq yozilgan.
"""

SnapshotImageIntentDep = Annotated[
    AuditReadIntent,
    Depends(audit_read(TABLE_SNAPSHOTS, reason="snapshot_image_view")),
]
"""DALIL-KADRNING OCHILISHI — nizo paytidagi «kim ko'rdi» dalili (D-09).

`reason` `cameras.py` dagi `live_view` DAN FARQ QILADI va bu farq
jurnalni o'qiyotgan odam uchun: «kim jonli tasvirni ochdi» (hozirgi
lahza) va «kim SAQLANGAN dalil-kadrni ochdi» (o'tmishdagi hodisa
haqidagi nizo) ikki xil savol. Bir xil qiymat bilan ular jurnalda
umuman ajralmasdi.

`resource_type` — `TABLE_SNAPSHOTS`: o'qilgan RESURS kadr, kamera emas.
"""

_NOT_FOUND = "not_found"
_PURGED = "snapshot_object_purged"
_STORAGE_UNAVAILABLE = "snapshot_storage_unavailable"

_IMAGE_MEDIA_TYPE = "image/jpeg"
_IMAGE_CACHE_CONTROL = "private, no-store"
"""⛔ `no-store` — KESH DISKKA TUSHMAYDI.

`private` yolg'iz o'zi «proxy keshlamasin» deydi, lekin BRAUZERGA
keshlashga ruxsat berardi: kadr diskda qolib, sessiya tugagandan keyin
ham (umumiy kompyuterda — boshqa foydalanuvchi uchun) ochilardi. Kadr
shaxsiy ma'lumot, ya'ni uning umri sessiyadan uzun bo'lmasligi kerak.
"""


def _market_id(principal: Principal) -> UUID:
    """Tanlangan bozor (`stalls.py:173-180` dagi jufti bilan aynan bir xil)."""
    if principal.market_id is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="market_not_selected",
        )
    return principal.market_id


def _not_found() -> HTTPException:
    """Begona va mavjud bo'lmagan kadr uchun BIR XIL javob (T-04-75)."""
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_NOT_FOUND)


def _as_float(value: Decimal | None) -> float | None:
    """`Numeric` ustunini JSON soniga o'giradi.

    `Decimal` Pydantic'da SATR bo'lib seriyalanardi va frontend uni
    `parseFloat` bilan qayta o'qishga majbur bo'lardi. O'lchov aniqligi
    ikki kasr xonasi (`Numeric(6, 2)`), ya'ni `float` ga o'tkazish
    ma'lumot yo'qotmaydi.
    """
    return None if value is None else float(value)


def _run_out(row: RunRow) -> CaptureRunOut:
    return CaptureRunOut(
        run_id=row.run_id,
        camera_id=row.camera_id,
        channel_no=row.channel_no,
        camera_name=row.camera_name,
        slot_time=row.slot_time,
        scheduled_at=row.scheduled_at,
        status=row.status,
        attempts=row.attempts,
        error_code=row.error_code,
        quality_verdict=row.quality_verdict,
        snapshot_id=row.snapshot_id,
    )


def _summary_out(summary: DaySummary) -> DaySummaryOut:
    return DaySummaryOut(
        planned=summary.planned,
        done=summary.done,
        ok=summary.ok,
        dark=summary.dark,
        blank=summary.blank,
        corrupt=summary.corrupt,
        failed=summary.failed,
        missed=summary.missed,
    )


def _detail_out(row: Snapshot) -> SnapshotDetailOut:
    """Kadr qatorini javob shakliga o'giradi.

    ⛔ `object_key` KO'CHIRILMAYDI — modul docstringidagi Qoida 2. Qator
       obyektida u BOR (retention unga tayanadi), javob modelida esa
       bunday maydon UMUMAN e'lon qilinmagan, ya'ni uni bu yerda
       «unutish» mumkin emas: Pydantic noma'lum argumentni rad etadi.
    """
    return SnapshotDetailOut(
        id=row.id,
        camera_id=row.camera_id,
        business_date=row.business_date,
        slot_time=row.slot_time,
        scheduled_at=row.scheduled_at,
        captured_at=row.captured_at,
        size_bytes=row.size_bytes,
        width=row.width,
        height=row.height,
        quality_verdict=row.quality_verdict,
        light_mode=row.light_mode,
        capture_method=row.capture_method,
        storage_tier=row.storage_tier,
        is_billable=row.is_billable,
        quality_mean=_as_float(row.quality_mean),
        quality_stddev=_as_float(row.quality_stddev),
        quality_saturation=_as_float(row.quality_saturation),
        quality_thresholds_version=row.quality_thresholds_version,
    )


def _alert_out(row: AlertEvent) -> AlertEventOut:
    """⚠ `detail` XOM HOLDA beriladi — allowlist filtri `AlertEventOut` ichida.

    Filtrni bu yerda qilish uni MARSHRUTGA bog'lardi va ikkinchi
    chaqiruvchi (kelajakdagi dayjest) uni chetlab o'tardi (T-04-74).
    """
    return AlertEventOut(
        id=row.id,
        alert_key=row.alert_key,
        severity=row.severity,
        subject_id=row.subject_id,
        first_seen_at=row.first_seen_at,
        last_seen_at=row.last_seen_at,
        occurrences=row.occurrences,
        notified_at=row.notified_at,
        resolved_at=row.resolved_at,
        detail=row.detail,  # type: ignore[arg-type]
    )


# ---------------------------------------------------------------------------
# Y-1/Y-2: KUN JURNALI
# ---------------------------------------------------------------------------


@capture_runs_router.get(
    "",
    response_model=CaptureDayOut,
    dependencies=[Depends(require_permission(Permission.CAMERA_VIEW))],
)
async def capture_day(
    principal: SnapshotViewerDep,
    session: TenantSessionDep,
    day: Annotated[date | None, Query()] = None,
) -> CaptureDayOut:
    """Kunning xulosasi va matritsa qatorlari (`CAMERA_VIEW`, §6.3/§6.4).

    ⛔ KELAJAKDAGI KUN 422 BERADI. Ertangi reja hali MATERIALIZATSIYA
       QILINMAGAN (u kunning birinchi tikida tug'iladi), ya'ni javob
       bo'sh jurnal bo'lardi — va bo'sh jurnal admin uchun «bugun hech
       narsa olinmadi» degan YOLG'ON SIGNAL bilan bir xil ko'rinardi.
       UI ham `<input type="date">` ga `max = bugun` qo'yadi, lekin u
       QULAYLIK: haqiqiy darvoza shu yerda.

    ⛔ ARXIVLANGAN KAMERA JAVOBDA YO'Q, LEKIN UNING MAVJUDLIGI AYTILADI.
       Repozitoriy `list_day()` arxivlangan kameraning O'TMISHDAGI
       qatorlarini ham qaytaradi (dalil hech qachon yashirilmaydi), bu
       yerda esa ular filtrlanadi va `archived_present` bayrog'i
       qo'yiladi. Bayroqsiz admin «kecha 25 kamera bor edi, bugun 24»
       farqini nosozlik deb o'ylardi.

       ⚠ Xulosa `day_summary()` dan keladi va U HAM arxivlangan
         kamerani sanamaydi (04-05 qarori), ya'ni xulosa va matritsa
         AYNAN bir xil to'plamni ko'radi. Aks holda «175 rejalashtirildi»
         yozuvi ostida 168 hujayra chizilardi.

    ⚠ `audit_read` YO'Q va bu ATAYIN — modul docstringidagi Qoida 3 ning
      oxirgi bandi: bu javobda TASVIR yo'q, faqat holat va o'lchov.
    """
    business_date = business_today() if day is None else day
    if business_date > business_today():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="day_in_the_future",
        )

    repo = CaptureRepository(session, _market_id(principal))
    summary = await repo.day_summary(business_date)
    rows = await repo.list_day(business_date)
    visible = [row for row in rows if not row.is_archived]
    return CaptureDayOut(
        day=business_date,
        summary=_summary_out(summary),
        rows=[_run_out(row) for row in visible],
        archived_present=len(visible) != len(rows),
    )


# ---------------------------------------------------------------------------
# Y-3: KADR DETALI VA RASM PROXYSI
# ---------------------------------------------------------------------------


@router.get(
    "/{snapshot_id}",
    response_model=SnapshotDetailOut,
    dependencies=[Depends(require_permission(Permission.CAMERA_VIEW))],
)
async def snapshot_detail(
    snapshot_id: UUID,
    principal: SnapshotViewerDep,
    session: TenantSessionDep,
) -> SnapshotDetailOut:
    """Kadrning metama'lumoti — RASMSIZ (`CAMERA_VIEW`, DL-3).

    ⛔ `object_key` JAVOBDA YO'Q (Qoida 2). O'lchovlar (`quality_*`) esa
       BOR: UI ularni «Texnik tafsilot» blokida ko'rsatadi va D-15
       chegaralarni sozlashda aynan shu sonlarga tayanadi.

    ⚠ `audit_read` BU YERDA YO'Q, RASM marshrutida esa BOR. Farq
      TASVIRDA: bu javobda kadrning O'ZI yo'q, ya'ni tashrifchining
      qiyofasi ochilmaydi. Chegara shu yerda o'tadi va u modul
      docstringining Qoida 3 ida yozilgan.

    `purged` kadr ham QAYTADI (D-18): «kadr bor edi, arxivdan
    chiqarildi» javobi «bunday kadr yo'q» dan butunlay boshqa ma'no.
    Bunday qatorda `storage_tier='purged'` turadi va UI rasm o'rniga
    sababni chizadi.
    """
    repo = SnapshotRepository(session, _market_id(principal))
    row = await repo.get(snapshot_id)
    if row is None:
        raise _not_found()
    return _detail_out(row)


@router.get(
    "/{snapshot_id}/image",
    response_class=StreamingResponse,
    dependencies=[Depends(require_permission(Permission.CAMERA_VIEW))],
)
async def snapshot_image(
    snapshot_id: UUID,
    principal: SnapshotViewerDep,
    intent: SnapshotImageIntentDep,
    session: TenantSessionDep,
    settings: SettingsDep,
) -> StreamingResponse:
    """DALIL-KADRNING O'ZI — core-api orqali PROXY qilinadi (§6.6 `[TALAB]`).

    =======================================================================
    ⛔ BU FAZANING XAVFSIZLIK JIHATIDAN ENG MUHIM MARSHRUTI.

    Uch kafolat BIRGA ishlaydi va ularning har biri ALOHIDA o'lchanadi:

      1. Baytlar OMBORDAN core-api orqali keladi — imzolangan havola
         BERILMAYDI (modul docstringidagi to'rt sabab);
      2. So'rov `CAMERA_VIEW` darvozasidan o'tadi va darvoza
         DEKORATORDA, ya'ni 403 quyidagi audit yozuviga YETIB BORMAYDI;
      3. MUVAFFAQIYATLI o'qish `audit_log` ga `source='app'`,
         `action='read'`, `table_name='snapshots'` qatorini qoldiradi.

    ⚠ IMZODAGI TARTIB YUK KO'TARADI: `principal` `intent` DAN OLDIN.
      FastAPI imzo parametrlarini e'lon tartibida hal qiladi, ya'ni
      almashtirilsa `audit_read` avval ishlab, fon vazifasini
      ro'yxatdan o'tkazardi — va 403 bilan tugagan so'rov ham jurnalda
      «ko'rildi» bo'lib qolishi mumkin edi.
    =======================================================================

    ⚠ OMBOR KLIENTI SO'ROV DAVOMIDA OCHILADI (`async with`), worker'dagidan
      FARQLI. Worker uzoq yashaydigan jarayon va u klientni bir marta
      ochib ushlab turadi (yuzlab yuklash); rasm ko'rish esa SIYRAK
      hodisa — admin kuniga bir necha marta DL-3 ni ochadi. Doimiy pul
      ushlab turish bu tezlikda foyda bermasdi, `aiohttp` ulanishlari
      esa ilova hayoti davomida ochiq qolardi.

    410 `snapshot_object_purged` — obyekt 455 kundan keyin o'chirilgan;
    503 `snapshot_storage_unavailable` — ombor javob bermadi;
    404 — kadr begona bozorniki yoki mavjud emas.
    """
    repo = SnapshotRepository(session, _market_id(principal))
    row = await repo.get(snapshot_id)
    if row is None:
        raise _not_found()
    if row.storage_tier == SnapshotTier.PURGED.value:
        # 410 (404 EMAS): qator MAVJUD va u sana bilan «bor edi» deydi.
        log.info("snapshot_object_purged", snapshot_id=str(snapshot_id))
        raise HTTPException(status_code=status.HTTP_410_GONE, detail=_PURGED)

    try:
        async with storage.open(settings) as client:
            payload = await client.get(row.object_key)
    except StorageError as exc:
        # ⚠ ISTISNO MATNI JAVOBGA CHIQMAYDI (T-04-40 bilan bir xil
        #   yo'nalish): u ombor amali va status kodini tashiydi, ya'ni
        #   ichki topologiya haqida signal berardi. Sabab jurnalda.
        log.warning("snapshot_storage_unavailable", snapshot_id=str(snapshot_id), error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=_STORAGE_UNAVAILABLE,
        ) from exc

    intent.filters = {"snapshot_id": str(snapshot_id)}
    intent.result_count = 1

    async def _body() -> AsyncIterator[bytes]:
        yield payload

    return StreamingResponse(
        _body(),
        media_type=_IMAGE_MEDIA_TYPE,
        headers={
            "Cache-Control": _IMAGE_CACHE_CONTROL,
            "Content-Length": str(len(payload)),
        },
    )


# ---------------------------------------------------------------------------
# Y-4: OGOHLANTIRISHLAR — FAQAT O'QISH
# ---------------------------------------------------------------------------


@alerts_router.get(
    "",
    response_model=AlertListResponse,
    dependencies=[Depends(require_permission(Permission.CAMERA_VIEW))],
)
async def list_alerts(
    principal: SnapshotViewerDep,
    session: TenantSessionDep,
    closed: Annotated[bool, Query()] = False,
) -> AlertListResponse:
    """Ochiq (`closed=0`, standart) yoki yopilgan ogohlantirishlar (§6.7).

    ⛔ YOPISH/BOSTIRISH MARSHRUTI SHU FAYLDA UMUMAN YO'Q (T-04-73):
       ogohlantirishni faqat TIKLANISH yopadi. Regex darvozasi
       `PATCH`/`POST`/`DELETE /alerts` yo'qligini tekshiradi.

    ⚠ `detail` ALLOWLIST bilan filtrlanadi va filtr `AlertEventOut` ning
      O'ZIDA (T-04-74) — `jsonb` ustuniga kelajakdagi har qanday alert
      yozuvchisi istalgan kalit yozishi mumkin va denylist birinchi
      e'tiborsizlikda buzilardi.

    ⚠ Javobda `snapshot_id` ham, rasm havolasi ham YO'Q (D-19) —
      jadvalda bunday ustunning O'ZI yo'q.
    """
    repo = AlertRepository(session, _market_id(principal))
    rows = await repo.list_events(closed=closed)
    return AlertListResponse(items=[_alert_out(row) for row in rows])
