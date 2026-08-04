"""Snapshot jadvali — mavsumiy profil, «bugun/ertaga» va qoplanish (CAM-04).

=============================================================================
MARSHRUT TARTIBI AHAMIYATLI: `GET /today` `PATCH /{schedule_id}` DAN OLDIN
E'LON QILINGAN.

FastAPI marshrutlarni E'LON TARTIBIDA solishtiradi (`stalls.py:3-11` da
o'rnatilgan qoida). Teskari tartibda `/snapshot-schedules/today` so'rovi
`{schedule_id}` shabloniga tushardi, `"today"` esa UUID emas — natijada
admin jadval sahifasi o'rniga 422 olardi va sabab kodga qarab UMUMAN
ko'rinmasdi (ikkala marshrut ham to'g'ri yozilgan bo'lib turardi).
=============================================================================

=============================================================================
HUQUQ TALABI MARSHRUT DEKORATORIDA (`dependencies=[...]`), IMZO PARAMETRI
SIFATIDA EMAS (`04-PATTERNS.md` §3.9, `stalls.py:28-42`).

FastAPI dekorator darajasidagi bog'liqliklarni imzo parametrlaridan OLDIN
hal qiladi (`fastapi/routing.py` ularni `dependant.dependencies` ning
BOSHIGA qo'yadi), ya'ni 403 olgan so'rov endpoint tanasiga YETIB
BORMAYDI.

⚠ BU FAYLDA QOIDA «ORTIQCHA» KO'RINADI — VA U ATAYIN SHU YERDA HAM AMAL
  QILADI. Jadval yuzasida `audit_read` yo'q (pastga qarang), ya'ni
  imzoga ko'chirilgan huquq bu yerda YOLG'ON DALIL qoldirmasdi. Lekin
  qoida FAYLDAN FAYLGA ko'chib yuradigan naqsh: bir joyda buzilsa, u
  keyingi routerga nusxa bo'lib o'tadi va o'sha yerda `audit_read` bilan
  uchrashadi. `snapshots.py` — aynan o'sha keyingi router.
=============================================================================

-----------------------------------------------------------------------------
⚠ `audit_read` BU FAYLDA ATAYIN YO'Q — NAZORAT HOLATI `stalls.py:348-369`.

Jadval SHAXSIY MA'LUMOT EMAS: unda profil nomi («Qishki»), davr sanalari
va `HH:MM` vaqtlar bor — na sotuvchi, na tashrifchi, na xodim haqida
hech nima. Bu yuzaga o'qish auditini yopishtirish jurnalni HAR jadval
sahifasi ochilishida shovqin bilan to'ldirardi va HAQIQIY o'qish
hodisasini (kadr rasmi — `snapshots.py`) ko'mib yuborardi. Aynan
`security/audit.py:288-297` da rad etilgan «blanket middleware»
mulohazasining o'zi (T-02-148).

Jadvalning O'ZGARISHI esa auditda: `snapshot_schedules` va
`snapshot_schedule_slots` DB triggeri ostida (`0014_snapshot_domain` ->
`SNAPSHOT_AUDITED_TABLES`). Shuning uchun bu fayl `write_app_audit()` ni
ham CHAQIRMAYDI — har `INSERT` uchun IKKITA qator paydo bo'lardi va
jurnalni o'qiyotgan odam «nima ikki marta sodir bo'ldi?» degan savol
bilan qolardi.
-----------------------------------------------------------------------------

RBAC — YANGI `Permission` QO'SHILMAYDI (Wave 0 qarori, `04-UI-SPEC.md`
W0-F6). Jadval — kameralarning bevosita davomi, ya'ni `CAMERA_MANAGE` /
`CAMERA_VIEW` QAYTA ISHLATILADI. Yangi huquq `security/rbac.py` va
`frontend/src/lib/rbac.ts` matritsalarini BIRGA o'zgartirishni talab
qilardi (til chegarasi tufayli avtomatik ko'zgu yo'q).

CROSS-TENANT JAVOB — HAR DOIM 404 (T-04-75), 403 EMAS. Begona bozorning
`schedule_id` si repozitoriydan `None`/`False` bo'lib qaytadi (RLS +
ikkinchi qatlam predikati) va shu yerda 404 ga aylanadi.

`market_id` HECH QACHON SO'ROV TANASIDAN OLINMAYDI (T-02-54):
`ScheduleCreateIn` va `ScheduleSlotsIn` da bunday maydon umuman e'lon
qilinmagan va ikkalasi ham `extra="forbid"` ostida.

-----------------------------------------------------------------------------
XATO XARITASI — repozitoriyning TO'RT sinfi, to'rt HTTP kodi:

    ScheduleStartsTooSoonError  ->  422 schedule_starts_too_soon   (D-05)
    ScheduleSlotsInvalidError   ->  422 schedule_slots_invalid     (§4.6)
    ScheduleNotEditableError    ->  403 schedule_not_editable      (§4.5)
    ScheduleOverlapError        ->  409 schedule_period_overlaps   (23P01)
    ValueError (ends_on <= starts_on) -> 422 invalid_period

`ScheduleNotEditableError` uchun javob **403**, 409 EMAS va bu ataylab:
o'tmishdagi profil o'tmishdagi kadrlarni TUSHUNTIRADI, ya'ni uni
tahrirlash tarixni yolg'onga aylantirardi. Bu HUQUQ masalasi — bir
vaqtning o'zida ikki tomon bir xil resursni o'zgartirmoqchi bo'lgan
KONFLIKT emas. Aynan shu mulohaza `tariff_past_locked` (02-09) va
`category_period_past_locked` (02-08) uchun ham ishlatilgan va
`schedule_repo.ScheduleNotEditableError` docstringi uni KONTRAKT
sifatida yozib qo'ygan.

Kesishuv esa 409: DB `EXCLUDE` konstraytini buzgan davr — HAQIQIY
konflikt va foydalanuvchi uchun yagona ma'noli harakat boshqa davr
tanlash.
-----------------------------------------------------------------------------
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Literal, cast
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sbozor_core.timeutil import business_today

from app.deps import Principal, SettingsDep, TenantSessionDep, require_permission
from app.repositories.schedule_repo import (
    ScheduleNotEditableError,
    ScheduleOverlapError,
    ScheduleProfile,
    ScheduleRepository,
    ScheduleSlotsInvalidError,
    ScheduleStartsTooSoonError,
)
from app.schemas import (
    ScheduleCreateIn,
    ScheduleDayOut,
    ScheduleItemOut,
    ScheduleListResponse,
    ScheduleProfileOut,
    ScheduleSlotsIn,
    ScheduleTodayOut,
)
from app.security.rbac import Permission

if TYPE_CHECKING:
    from datetime import date, time

# `UUID` ish paytida kerak — FastAPI yo'l parametrlarining annotatsiyasini
# `get_type_hints` bilan o'qiydi (`stalls.py` / `tariffs.py` dagi bilan bir
# xil sabab). `date`/`time` esa faqat yordamchi imzolarida uchraydi.
log = structlog.get_logger(__name__)

ScheduleMode = Literal["past", "active", "future"]
"""Profil rejimi — `schedule_repo._PAST`/`_ACTIVE`/`_FUTURE` ning tipi.

Repozitoriy uni oddiy `str` sifatida beradi (dataclass, Pydantic emas),
javob modeli esa `Literal` bilan qulflaydi: OpenAPI'da uchala qiymat
ochiq turadi va frontend ularni union sifatida oladi. Chegarada `cast`
bo'lgani uchun noto'g'ri qiymat Pydantic validatsiyasida yiqiladi —
jimgina o'tib ketmaydi.
"""

router = APIRouter(tags=["schedules"])

ScheduleManagerDep = Annotated[Principal, Depends(require_permission(Permission.CAMERA_MANAGE))]
ScheduleViewerDep = Annotated[Principal, Depends(require_permission(Permission.CAMERA_VIEW))]
"""IMZO aliaslari — `principal` ni olish uchun, DARVOZA aliaslari EMAS.

Darvozaning o'zi har marshrutning dekoratorida ochiq yozilgan
(`cameras.py:39-42` da o'rnatilgan qoida): huquqning NOMI marshrutning
yonida turishi kerak, aks holda kod-ko'rikda «bu marshrut nimani talab
qiladi?» savoli faylning boshiga qarashni talab qilardi.
"""

_NOT_FOUND = "not_found"
_STARTS_TOO_SOON = "schedule_starts_too_soon"
_SLOTS_INVALID = "schedule_slots_invalid"
_NOT_EDITABLE = "schedule_not_editable"
_OVERLAPS = "schedule_period_overlaps"
_INVALID_PERIOD = "invalid_period"


def _market_id(principal: Principal) -> UUID:
    """Tanlangan bozor (`stalls.py:173-180` dagi jufti bilan aynan bir xil)."""
    if principal.market_id is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="market_not_selected",
        )
    return principal.market_id


def _not_found() -> HTTPException:
    """Cross-tenant va mavjud bo'lmagan profil uchun BIR XIL javob (T-04-75)."""
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_NOT_FOUND)


def _rejected(exc: ValueError) -> HTTPException:
    """Repozitoriyning xato sinfini TANILGAN HTTP javobiga o'giradi.

    ⚠ TARTIB AHAMIYATLI: to'rtala sinf ham `ValueError` dan meros oladi,
      ya'ni umumiy shox OXIRIDA turishi shart. Teskari tartibda har bir
      aniq holat `invalid_period` bo'lib chiqardi va admin «davr
      noto'g'ri» degan xabarni jadvalning vaqtlari chegarasidan oshganda
      ham ko'rardi.

    Noma'lum `ValueError` UMUMIY 422 oladi, 500 emas: bu shoxga faqat
    `assignment_period()` ning O'Z darvozasi (`ends_on <= starts_on`)
    tushadi va u foydalanuvchi kiritmasining xatosi.
    """
    if isinstance(exc, ScheduleStartsTooSoonError):
        log.info("schedule_starts_too_soon", error=str(exc))
        return HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=_STARTS_TOO_SOON
        )
    if isinstance(exc, ScheduleSlotsInvalidError):
        log.info("schedule_slots_invalid", error=str(exc))
        return HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=_SLOTS_INVALID
        )
    if isinstance(exc, ScheduleNotEditableError):
        # 403 — fayl boshidagi xato xaritasiga qarang (o'tmish HUQUQ
        # masalasi, konflikt emas).
        log.info("schedule_not_editable", error=str(exc))
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=_NOT_EDITABLE)
    if isinstance(exc, ScheduleOverlapError):
        log.info("schedule_period_overlaps", error=str(exc))
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_OVERLAPS)
    log.info("schedule_invalid_period", error=str(exc))
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=_INVALID_PERIOD)


def _profile_out(profile: ScheduleProfile) -> ScheduleProfileOut:
    """Repozitoriy obyektini javob shakliga o'giradi."""
    return ScheduleProfileOut(
        id=profile.id,
        name=profile.name,
        starts_on=profile.starts_on,
        ends_on=profile.ends_on,
        mode=cast("ScheduleMode", profile.mode),
    )


def _item_out(profile: ScheduleProfile, times: list[time]) -> ScheduleItemOut:
    return ScheduleItemOut(
        id=profile.id,
        name=profile.name,
        starts_on=profile.starts_on,
        ends_on=profile.ends_on,
        mode=cast("ScheduleMode", profile.mode),
        times=times,
    )


# ---------------------------------------------------------------------------
# STATIK SEGMENT — `{schedule_id}` SHABLONIDAN OLDIN (fayl boshidagi izoh)
# ---------------------------------------------------------------------------


@router.get(
    "/today",
    response_model=ScheduleTodayOut,
    dependencies=[Depends(require_permission(Permission.CAMERA_VIEW))],
)
async def schedule_today(
    principal: ScheduleViewerDep,
    session: TenantSessionDep,
    settings: SettingsDep,
) -> ScheduleTodayOut:
    """«Bugun» VA «ertaga» — BITTA so'rovda (`04-UI-SPEC.md` §4.3 `[TALAB]`).

    =======================================================================
    ⛔ BU MARSHRUT IKKIGA BO'LINMAYDI.

    `GET /today` va `GET /tomorrow` juftligi ikki TURLI lahzada javob
    berardi. Yarim tun atrofida birinchisi 23:59:59 da, ikkinchisi
    00:00:01 da bajarilsa ikkalasi ham AYNI kunni ko'rsatardi — va admin
    ekranda «bugun: 7 slot · ertaga: 7 slot» ni ko'rib, jadval
    o'zgarishini boshdan kechirmasdi.

    D-05 ning butun ko'rsatkichi shu ikki qatorning FARQIDA, ya'ni
    atomiklik bu yerda qulaylik emas, MAZMUN. Repozitoriy uni bitta
    `SELECT` bilan qulflaydi: ikkala sana ham AYNI `now()` dan chiqadi.
    =======================================================================

    ⚠ `uncovered_horizon_days` HAM QAYTADI, faqat sanoq emas: «3 kun
      qoplanmagan» jumlasi qaysi oyna ustida aytilganini bilmasa
      ma'nosiz bo'lardi.

    ⚠ `audit_read` YO'Q — sabab modul docstringida (jadval shaxsiy
      ma'lumot emas; nazorat holati `stalls.py:348-369`).
    """
    repo = ScheduleRepository(session, _market_id(principal))
    view = await repo.today_and_tomorrow(horizon_days=settings.schedule_horizon_days)
    return ScheduleTodayOut(
        profile=None if view.profile is None else _profile_out(view.profile),
        today=ScheduleDayOut(date=view.today.date, times=list(view.today.times)),
        tomorrow=ScheduleDayOut(date=view.tomorrow.date, times=list(view.tomorrow.times)),
        differs=view.differs,
        capture_on_closed_days=view.capture_on_closed_days,
        uncovered_days=view.uncovered_days,
        uncovered_horizon_days=view.uncovered_horizon_days,
    )


@router.get(
    "",
    response_model=ScheduleListResponse,
    dependencies=[Depends(require_permission(Permission.CAMERA_VIEW))],
)
async def list_schedules(
    principal: ScheduleViewerDep,
    session: TenantSessionDep,
) -> ScheduleListResponse:
    """Bozorning barcha profillari (DL-2 ro'yxati, `CAMERA_VIEW`).

    `mode` HAR BIR qator uchun BUGUNGA nisbatan hisoblanadi — UI
    «o'chirish» tugmasini aynan `mode == "future"` bo'yicha chizadi
    (DL-4). Sahifalash yo'q, sabab `ScheduleListResponse` docstringida.
    """
    repo = ScheduleRepository(session, _market_id(principal))
    rows = await repo.list_profiles(today=business_today())
    return ScheduleListResponse(items=[_item_out(profile, times) for profile, times in rows])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=ScheduleItemOut,
    dependencies=[Depends(require_permission(Permission.CAMERA_MANAGE))],
)
async def create_schedule(
    payload: ScheduleCreateIn,
    principal: ScheduleManagerDep,
    session: TenantSessionDep,
    settings: SettingsDep,
) -> ScheduleItemOut:
    """Mavsumiy profil — MAVJUD davrni BO'LIB (`CAMERA_MANAGE`, `04-RESEARCH.md` §A.1).

    Repozitoriy uch qadamni BITTA tranzaksiyada bajaradi: qoplaydigan
    profilni qisqartiradi, `ends_on` dan keyin uni NUSXA sifatida
    tiklaydi va yangi profilni yozadi. UI bu mantiqni TAKRORLAMAYDI.

    ⚠ KESISHUV 409 BERADI, 500 EMAS. Davrlar kesishuvi `EXCLUDE`
      konstrayti (`ex_snapshot_schedules_no_overlap`) bilan DB darajasida
      to'siladi va `23P01` xom holda `main.py` ning global handleriga
      borsa admin «ichki xato» ko'rardi — holbuki bu uning kiritmasining
      to'g'irlanadigan xatosi. Repozitoriy uni `ScheduleOverlapError` ga,
      bu marshrut esa tanilgan `detail` kodiga aylantiradi.

    422 `schedule_starts_too_soon` — `starts_on <= bugun` (D-05);
    422 `schedule_slots_invalid` — vaqtlar bo'sh, dublikatli yoki
        `snapshot_max_times_per_day` dan oshiq (SERVER darvozasi);
    422 `invalid_period` — `ends_on <= starts_on`.
    """
    repo = ScheduleRepository(session, _market_id(principal))
    today = business_today()
    try:
        schedule_id = await repo.create_seasonal(
            name=payload.name,
            starts_on=payload.starts_on,
            ends_on=payload.ends_on,
            times=payload.times,
            today=today,
            # ⚠ CHEGARA SOZLAMADAN, DTO'dan EMAS (`04-UI-SPEC.md` §4.6
            #   `[TALAB]`): klientdagi 12 — QULAYLIK va u DevTools bilan
            #   olib tashlanadi. Haqiqiy shift shu argument.
            max_times_per_day=settings.snapshot_max_times_per_day,
        )
    except ValueError as exc:
        raise _rejected(exc) from exc

    return await _item_or_404(repo, schedule_id, today)


# ---------------------------------------------------------------------------
# SHABLONLI SEGMENT — statiklardan KEYIN
# ---------------------------------------------------------------------------


@router.patch(
    "/{schedule_id}",
    response_model=ScheduleItemOut,
    dependencies=[Depends(require_permission(Permission.CAMERA_MANAGE))],
)
async def update_schedule_slots(
    schedule_id: UUID,
    payload: ScheduleSlotsIn,
    principal: ScheduleManagerDep,
    session: TenantSessionDep,
    settings: SettingsDep,
) -> ScheduleItemOut:
    """Profilning VAQTLARINI almashtiradi (`CAMERA_MANAGE`, `04-UI-SPEC.md` §4.5).

    ⚠ O'ZGARISH ERTADAN KUCHGA KIRADI (D-05) va bu kafolat SHU YERDA
      EMAS: bugungi `capture_runs` qatorlari allaqachon materializatsiya
      qilingan va `capture_repo.ensure_plan()` ning SLOT o'lchovidagi
      muzlatishi ularga yangi vaqt qo'shmaydi. Ya'ni kafolat TUZILMAVIY,
      bu marshrutning xushmuomalaligi emas. UI DL-1 da buni doimiy,
      yopib bo'lmaydigan izoh bilan aytadi.

    ⚠ `starts_on`/`ends_on` YUBORILSA SO'ROV RAD ETILADI (422) —
      `ScheduleSlotsIn.model_config` dagi `extra="forbid"`. Sabab o'sha
      modelning docstringida: jim e'tiborsizlik rad etishdan yomonroq.

    403 `schedule_not_editable` — profil O'TMISHDA;
    404 — profil begona bozorniki yoki mavjud emas.
    """
    repo = ScheduleRepository(session, _market_id(principal))
    today = business_today()
    try:
        updated = await repo.update_slots(
            schedule_id,
            payload.times,
            today=today,
            max_times_per_day=settings.snapshot_max_times_per_day,
        )
    except ValueError as exc:
        raise _rejected(exc) from exc

    if not updated:
        raise _not_found()
    return await _item_or_404(repo, schedule_id, today)


@router.delete(
    "/{schedule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    dependencies=[Depends(require_permission(Permission.CAMERA_MANAGE))],
)
async def delete_schedule(
    schedule_id: UUID,
    principal: ScheduleManagerDep,
    session: TenantSessionDep,
) -> Response:
    """HALI BOSHLANMAGAN profilni o'chiradi (`CAMERA_MANAGE`, DL-4).

    ⛔ FAQAT `starts_on > bugun`. Bunday profil birorta `capture_runs`
       qatorini tug'dirmagan, ya'ni o'chiriladigan DALIL yo'q — bu
       fazadagi o'chirishga ruxsat berilgan YAGONA amal va uning sababi
       `schedule_repo` modul docstringida. Boshlangan profilni o'chirish
       o'tmishdagi kadrlarning yagona izohini yo'q qilardi.

    Amalning O'ZI DB triggeri orqali audit jurnaliga tushadi
    (`SNAPSHOT_AUDITED_TABLES`), ya'ni «kim, qachon o'chirdi» savoli
    javobsiz qolmaydi.

    403 `schedule_not_editable` — profil allaqachon boshlangan;
    404 — profil begona bozorniki yoki mavjud emas.
    """
    repo = ScheduleRepository(session, _market_id(principal))
    try:
        removed = await repo.delete_future(schedule_id, today=business_today())
    except ValueError as exc:
        raise _rejected(exc) from exc

    if not removed:
        raise _not_found()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


async def _item_or_404(
    repo: ScheduleRepository,
    schedule_id: UUID,
    today: date,
) -> ScheduleItemOut:
    """Yozuvdan KEYINGI javob — AYNAN o'qish yo'lidan (`tariffs.py:191-202` naqshi).

    Klient `POST`/`PATCH` dan keyin `GET` qilganda boshqa shakl
    ko'rmaydi. `times` ham shu tufayli normallashgan holda (o'sish
    tartibida, dublikatsiz) qaytadi — repozitoriy uni yozishdan oldin
    tartiblaydi va javob o'sha yozilgan qatorlardan quriladi.
    """
    for profile, times in await repo.list_profiles(today=today):
        if profile.id == schedule_id:
            return _item_out(profile, times)
    raise _not_found()  # pragma: no cover - o'sha tranzaksiyada yo'qolishi mumkin emas
