"""Universal agent obyektlari — panel yuzasi `/api/v1/edge-sites` (0036).

Tanlangan bozor doirasida (`TenantSessionDep`, RLS): obyektlar va ularning
agentlari, aktivatsiya kodi, biznes sozlamasi (versiyalangan), buyruqlar,
hodisalar, avtoturargoh kunlik xulosasi, davr hisoboti (JSON + `.xlsx`)
va kadr.

HUQUQLAR — mavjud matritsadan, YANGI HUQUQ QO'SHILMADI:
  * o'qish — `CAMERA_VIEW` (platforma admini, bozor admini, direktor);
  * yozish — `CAMERA_MANAGE` (platforma admini, bozor admini).
  Agent kamera/shlagbaum qurilmalarini boshqaradi, ya'ni bu NVR sozlamasi
  bilan bir sinf (`CAMERA_MANAGE` docstringi): direktor ko'radi, o'zgartirmaydi.

Har yozuv `audit_log` ga ilova qatlamida yoziladi; kadr ochilishi —
`audit_read` (dalil-kadr bilan bir xil qoida).
"""

from __future__ import annotations

import re
from datetime import UTC, date, datetime, time, timedelta
from typing import TYPE_CHECKING, Annotated, Any, Literal
from uuid import UUID
from zoneinfo import ZoneInfo

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sbozor_core.enums import AuditAction
from sqlalchemy.exc import IntegrityError

# `_locale_of` va `_xlsx_response` `imports.py` DAN — `reports.py` bilan bir
# xil qaror: profil tili va yuklab olish javobining qoidasi BITTA joyda.
from app.api.v1.imports import _locale_of, _xlsx_response
from app.deps import Principal, SettingsDep, TenantSessionDep, require_permission
from app.edge_contract import COMMAND_TYPES
from app.repositories import edge_repo
from app.security.audit import AuditReadIntent, audit_read, write_app_audit
from app.security.rbac import Permission
from app.services import parking_report, storage
from app.services.edge_config import default_doc, strip_derived, validate_doc
from app.services.storage import StorageError

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

__all__ = ["router"]

log = structlog.get_logger(__name__)

router = APIRouter(tags=["edge-sites"])

TASHKENT = ZoneInfo("Asia/Tashkent")
TABLE_EDGE_SITES = "edge_sites"
TABLE_EDGE_FILES = "edge_files"

ViewerDep = Annotated[Principal, Depends(require_permission(Permission.CAMERA_VIEW))]
ManagerDep = Annotated[Principal, Depends(require_permission(Permission.CAMERA_MANAGE))]
FrameIntentDep = Annotated[
    AuditReadIntent, Depends(audit_read(TABLE_EDGE_FILES, reason="edge_frame_view"))
]

_NOT_FOUND = "not_found"
_GATE_PREFIX = "parking.gate."
_GATE_TTL = timedelta(seconds=60)
_DEFAULT_TTL = timedelta(hours=1)


def _market_id(principal: Principal) -> UUID:
    if principal.market_id is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="market_not_selected")
    return principal.market_id


def _not_found() -> HTTPException:
    """Begona va mavjud bo'lmagan obyekt uchun BIR XIL javob."""
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_NOT_FOUND)


# ---------------------------------------------------------------------------
# Modellar
# ---------------------------------------------------------------------------


class EdgeAgentOut(BaseModel):
    id: str
    hostname: str
    version: str
    os: str
    last_seen_at: datetime | None
    online: bool
    heartbeat: dict[str, Any] | None


class EdgeSetupOut(BaseModel):
    devices: list[dict[str, Any]]
    lanes: list[dict[str, Any]]


class EdgeSiteOut(BaseModel):
    id: str
    kind: str
    name: str
    created_at: datetime
    config_version: int
    setup: EdgeSetupOut
    agent: EdgeAgentOut | None


class EdgeSiteListResponse(BaseModel):
    items: list[EdgeSiteOut]


class EdgeSiteCreate(BaseModel):
    kind: Literal["parking", "market", "livestock"]
    name: str = Field(min_length=1, max_length=100)


class ActivationCodeOut(BaseModel):
    code: str
    expires_at: datetime


class EdgeSiteCreated(BaseModel):
    site: EdgeSiteOut
    activation_code: ActivationCodeOut


class EdgeConfigOut(BaseModel):
    version: int
    doc: dict[str, Any]
    created_at: datetime


class EdgeConfigUpdate(BaseModel):
    doc: Any


class EdgeCommandCreate(BaseModel):
    type: str = Field(min_length=1, max_length=64)
    data: dict[str, Any] = Field(default_factory=dict)


class EdgeCommandOut(BaseModel):
    id: UUID
    type: str
    data: dict[str, Any]
    issued_by: str
    issued_at: datetime
    expires_at: datetime
    delivered_at: datetime | None
    result_status: str | None
    result_reason: str | None
    result_at: datetime | None


class EdgeCommandListResponse(BaseModel):
    items: list[EdgeCommandOut]


class EdgeEventOut(BaseModel):
    id: UUID
    type: str
    v: int
    seq: int
    occurred_at: datetime
    received_at: datetime
    clock_ok: bool
    correlation_id: UUID | None
    data: dict[str, Any]
    file_ids: list[str]


class EdgeEventListResponse(BaseModel):
    items: list[EdgeEventOut]
    has_more: bool


class CashByMethod(BaseModel):
    cash: int
    terminal: int


class PlateOut(BaseModel):
    occurred_at: datetime
    plate: str
    lane_id: str
    direction: str
    file_id: str | None


class ParkingSummaryOut(BaseModel):
    date: date
    entries: int
    exits: int
    open_estimate: int
    cash_total_soum: int
    cash_by_method: CashByMethod
    last_plates: list[PlateOut]


class ParkingReportTotalsOut(BaseModel):
    entries: int
    exits: int
    cash: int
    terminal: int
    total: int
    free_count: int


class ParkingReportDayOut(ParkingReportTotalsOut):
    date: date


class ParkingReportSessionOut(BaseModel):
    """Bitta mashina. `None` — hodisa kelmagan (ochiq seans, raqamsiz kirish)."""

    session_id: str
    plate: str | None
    entered_at: datetime | None
    exited_at: datetime | None
    duration_minutes: int | None
    amount_soum: int
    method: str | None
    reason: str | None
    entry_file_id: str | None
    opened_at_exit: bool


class ParkingReportHourOut(BaseModel):
    hour: int
    entries: int
    exits: int


class ParkingReportStayBucketOut(BaseModel):
    key: str
    count: int


class ParkingReportStayOut(BaseModel):
    measured: int
    median_minutes: int | None
    buckets: list[ParkingReportStayBucketOut]
    unrecorded_entries: int


class ParkingReportExitReasonOut(BaseModel):
    reason: str
    count: int


class ParkingReportRegularOut(BaseModel):
    plate: str
    visits: int
    amount_soum: int
    last_seen_at: datetime


class ParkingReportOut(BaseModel):
    site_id: str
    site_name: str
    from_date: date
    to_date: date
    days: list[ParkingReportDayOut]
    total: ParkingReportTotalsOut
    sessions: list[ParkingReportSessionOut]
    hours: list[ParkingReportHourOut]
    stay: ParkingReportStayOut
    exit_reasons: list[ParkingReportExitReasonOut]
    inside: int
    paid_sessions: int
    average_check_soum: int | None
    regulars: list[ParkingReportRegularOut]


# ---------------------------------------------------------------------------
# Yordamchilar
# ---------------------------------------------------------------------------


def _agent_out(agent: edge_repo.AgentRow | None, now: datetime) -> EdgeAgentOut | None:
    if agent is None:
        return None
    online = agent.last_seen_at is not None and now - agent.last_seen_at <= edge_repo.ONLINE_WINDOW
    return EdgeAgentOut(
        id=agent.id,
        hostname=agent.hostname,
        version=agent.version,
        os=agent.os,
        last_seen_at=agent.last_seen_at,
        online=online,
        heartbeat=agent.last_heartbeat,
    )


def _setup_out(setup: dict[str, Any]) -> EdgeSetupOut:
    devices = setup.get("devices")
    lanes = setup.get("lanes")
    return EdgeSetupOut(
        devices=devices if isinstance(devices, list) else [],
        lanes=lanes if isinstance(lanes, list) else [],
    )


async def _sites_out(
    session: Any, market_id: UUID, sites: list[edge_repo.SiteRow]
) -> list[EdgeSiteOut]:
    ids = [site.id for site in sites]
    agents = await edge_repo.latest_agent(session, market_id, ids)
    versions = await edge_repo.latest_versions(session, market_id, ids)
    now = datetime.now(UTC)
    return [
        EdgeSiteOut(
            id=site.id,
            kind=site.kind,
            name=site.name,
            created_at=site.created_at,
            config_version=versions.get(site.id, 0),
            setup=_setup_out(site.setup),
            agent=_agent_out(agents.get(site.id), now),
        )
        for site in sites
    ]


async def _site_or_404(session: Any, market_id: UUID, site_id: str) -> edge_repo.SiteRow:
    if len(site_id) > 64:
        raise _not_found()
    site = await edge_repo.get_site(session, market_id, site_id)
    if site is None:
        raise _not_found()
    return site


def _command_out(command: edge_repo.CommandRow) -> EdgeCommandOut:
    return EdgeCommandOut(
        id=command.id,
        type=command.type,
        data=command.data,
        issued_by=command.issued_by,
        issued_at=command.issued_at,
        expires_at=command.expires_at,
        delivered_at=command.delivered_at,
        result_status=command.result_status,
        result_reason=command.result_reason,
        result_at=command.result_at,
    )


def _file_ids(data: dict[str, Any]) -> list[str]:
    out: list[str] = []
    single = data.get("file_id")
    if isinstance(single, str):
        out.append(single)
    many = data.get("file_ids")
    if isinstance(many, list):
        out += [item for item in many if isinstance(item, str)]
    stalls = data.get("stalls")
    if isinstance(stalls, list):
        out += [
            s["file_id"]
            for s in stalls
            if isinstance(s, dict) and isinstance(s.get("file_id"), str)
        ]
    return list(dict.fromkeys(out))


# ---------------------------------------------------------------------------
# Obyektlar
# ---------------------------------------------------------------------------


@router.get("", response_model=EdgeSiteListResponse)
async def list_sites(principal: ViewerDep, session: TenantSessionDep) -> EdgeSiteListResponse:
    """Bozordagi obyektlar va ularning agentlari (onlayn = 3 daqiqa ichida ko'ringan)."""
    market_id = _market_id(principal)
    sites = await edge_repo.list_sites(session, market_id)
    return EdgeSiteListResponse(items=await _sites_out(session, market_id, sites))


@router.post("", response_model=EdgeSiteCreated, status_code=status.HTTP_201_CREATED)
async def create_site(
    body: EdgeSiteCreate, principal: ManagerDep, session: TenantSessionDep
) -> EdgeSiteCreated:
    """Yangi obyekt + 1-versiya standart sozlama + aktivatsiya kodi."""
    market_id = _market_id(principal)
    site = await edge_repo.create_site(
        session,
        market_id,
        site_id=edge_repo.new_site_id(body.kind),
        kind=body.kind,
        name=body.name.strip(),
        created_by=principal.user_id,
    )
    await edge_repo.insert_config(
        session, market_id, site.id, doc=default_doc(site.kind), created_by=principal.user_id
    )
    code, expires_at = await edge_repo.create_code(
        session, market_id, site.id, created_by=principal.user_id
    )
    await write_app_audit(
        session,
        action=AuditAction.INSERT,
        table_name=TABLE_EDGE_SITES,
        new={"site_id": site.id, "kind": site.kind, "name": site.name},
        principal=principal,
    )
    (out,) = await _sites_out(session, market_id, [site])
    return EdgeSiteCreated(
        site=out, activation_code=ActivationCodeOut(code=code, expires_at=expires_at)
    )


@router.get("/{site_id}", response_model=EdgeSiteOut)
async def get_site(site_id: str, principal: ViewerDep, session: TenantSessionDep) -> EdgeSiteOut:
    market_id = _market_id(principal)
    site = await _site_or_404(session, market_id, site_id)
    (out,) = await _sites_out(session, market_id, [site])
    return out


@router.post(
    "/{site_id}/activation-codes",
    response_model=ActivationCodeOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_activation_code(
    site_id: str, principal: ManagerDep, session: TenantSessionDep
) -> ActivationCodeOut:
    """Bir martalik kod (7 kun). Faollashtirish obyektdagi oldingi agentni almashtiradi."""
    market_id = _market_id(principal)
    site = await _site_or_404(session, market_id, site_id)
    code, expires_at = await edge_repo.create_code(
        session, market_id, site.id, created_by=principal.user_id
    )
    await write_app_audit(
        session,
        action=AuditAction.INSERT,
        table_name="edge_activation_codes",
        new={"site_id": site.id, "expires_at": expires_at.isoformat()},
        principal=principal,
    )
    return ActivationCodeOut(code=code, expires_at=expires_at)


# ---------------------------------------------------------------------------
# Sozlama
# ---------------------------------------------------------------------------


@router.get("/{site_id}/config", response_model=EdgeConfigOut)
async def get_config(
    site_id: str, principal: ViewerDep, session: TenantSessionDep
) -> EdgeConfigOut:
    market_id = _market_id(principal)
    site = await _site_or_404(session, market_id, site_id)
    current = await edge_repo.latest_config(session, market_id, site.id)
    if current is None:
        raise _not_found()
    return EdgeConfigOut(version=current.version, doc=current.doc, created_at=current.created_at)


@router.put("/{site_id}/config", response_model=EdgeConfigOut)
async def put_config(
    site_id: str, body: EdgeConfigUpdate, principal: ManagerDep, session: TenantSessionDep
) -> EdgeConfigOut:
    """Yangi versiya (append-only). Sxemaga mos kelmasa 422 + o'zbekcha xatolar."""
    market_id = _market_id(principal)
    site = await _site_or_404(session, market_id, site_id)
    if not isinstance(body.doc, dict):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="config_not_object"
        )
    doc = strip_derived(body.doc)
    errors = validate_doc(site_id=site.id, kind=site.kind, doc=doc, setup=site.setup)
    if errors:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "config_invalid",
                "errors": [{"path": e.path, "message": e.message} for e in errors[:50]],
            },
        )
    previous = await edge_repo.latest_config(session, market_id, site.id)
    try:
        row = await edge_repo.insert_config(
            session, market_id, site.id, doc=doc, created_by=principal.user_id
        )
    except IntegrityError as exc:  # parallel saqlash
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="config_conflict") from exc
    await write_app_audit(
        session,
        action=AuditAction.UPDATE,
        table_name="edge_configs",
        old=None
        if previous is None
        else {"site_id": site.id, "version": previous.version, "doc": previous.doc},
        new={"site_id": site.id, "version": row.version, "doc": row.doc},
        principal=principal,
    )
    return EdgeConfigOut(version=row.version, doc=row.doc, created_at=row.created_at)


# ---------------------------------------------------------------------------
# Buyruqlar
# ---------------------------------------------------------------------------


@router.post(
    "/{site_id}/commands", response_model=EdgeCommandOut, status_code=status.HTTP_201_CREATED
)
async def create_command(
    site_id: str, body: EdgeCommandCreate, principal: ManagerDep, session: TenantSessionDep
) -> EdgeCommandOut:
    """Buyruq (oq ro'yxat — `command.schema.json`). Shlagbaum 60 s, qolgani 1 soat amal qiladi."""
    market_id = _market_id(principal)
    site = await _site_or_404(session, market_id, site_id)
    if body.type not in COMMAND_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="command_type_invalid"
        )
    ttl = _GATE_TTL if body.type.startswith(_GATE_PREFIX) else _DEFAULT_TTL
    command = await edge_repo.create_command(
        session,
        market_id,
        site.id,
        type_=body.type,
        data=body.data,
        issued_by=str(principal.user_id),
        expires_in=ttl,
    )
    await write_app_audit(
        session,
        action=AuditAction.INSERT,
        table_name="edge_commands",
        row_id=command.id,
        new={"site_id": site.id, "type": command.type, "data": command.data},
        principal=principal,
    )
    return _command_out(command)


@router.get("/{site_id}/commands", response_model=EdgeCommandListResponse)
async def list_commands(
    site_id: str, principal: ViewerDep, session: TenantSessionDep
) -> EdgeCommandListResponse:
    market_id = _market_id(principal)
    site = await _site_or_404(session, market_id, site_id)
    rows = await edge_repo.list_commands(session, market_id, site.id)
    return EdgeCommandListResponse(items=[_command_out(row) for row in rows])


# ---------------------------------------------------------------------------
# Hodisalar va xulosa
# ---------------------------------------------------------------------------


@router.get("/{site_id}/events", response_model=EdgeEventListResponse)
async def list_events(
    site_id: str,
    principal: ViewerDep,
    session: TenantSessionDep,
    type: Annotated[str | None, Query(max_length=64)] = None,  # noqa: A002 — protokol nomi
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0, le=100_000)] = 0,
) -> EdgeEventListResponse:
    market_id = _market_id(principal)
    site = await _site_or_404(session, market_id, site_id)
    rows = await edge_repo.list_events(
        session, market_id, site.id, event_type=type, limit=limit + 1, offset=offset
    )
    items = [
        EdgeEventOut(
            id=row.id,
            type=row.type,
            v=row.v,
            seq=row.seq,
            occurred_at=row.occurred_at,
            received_at=row.received_at,
            clock_ok=row.clock_ok,
            correlation_id=row.correlation_id,
            data=row.data,
            file_ids=_file_ids(row.data),
        )
        for row in rows[:limit]
    ]
    return EdgeEventListResponse(items=items, has_more=len(rows) > limit)


_SUMMARY_TYPES = (
    "parking.session.opened",
    "parking.session.closed",
    "core.payment.cash",
    "parking.plate.read",
)


@router.get("/{site_id}/parking-summary", response_model=ParkingSummaryOut)
async def parking_summary(
    site_id: str,
    principal: ViewerDep,
    session: TenantSessionDep,
    day: Annotated[date | None, Query(alias="date")] = None,
) -> ParkingSummaryOut:
    """Kun (Asia/Tashkent) bo'yicha: kirish, chiqish, naqd tushum, so'nggi raqamlar."""
    market_id = _market_id(principal)
    site = await _site_or_404(session, market_id, site_id)
    target = day or datetime.now(TASHKENT).date()
    start = datetime.combine(target, time.min, tzinfo=TASHKENT)
    end = start + timedelta(days=1)
    rows = await edge_repo.summary_events(
        session, market_id, site.id, types=_SUMMARY_TYPES, start=start, end=end
    )
    entries = exits = cash = terminal = 0
    plates: list[PlateOut] = []
    for row in rows:
        data = row.data
        if row.type == "parking.session.opened":
            entries += 1
        elif row.type == "parking.session.closed":
            exits += 1
        elif row.type == "core.payment.cash":
            amount = int(data.get("amount_soum", 0))
            if data.get("method") == "terminal":
                terminal += amount
            else:
                cash += amount
        elif row.type == "parking.plate.read":
            plates.append(
                PlateOut(
                    occurred_at=row.occurred_at,
                    plate=str(data.get("plate", "")),
                    lane_id=str(data.get("lane_id", "")),
                    direction=str(data.get("direction", "")),
                    file_id=data.get("file_id") if isinstance(data.get("file_id"), str) else None,
                )
            )
    return ParkingSummaryOut(
        date=target,
        entries=entries,
        exits=exits,
        open_estimate=max(entries - exits, 0),
        cash_total_soum=cash + terminal,
        cash_by_method=CashByMethod(cash=cash, terminal=terminal),
        last_plates=list(reversed(plates))[:20],
    )


# ---------------------------------------------------------------------------
# Avtoturargoh davr hisoboti
# ---------------------------------------------------------------------------

# ⛔ KODLAR `reports.py` NIKI BILAN AYNAN BIR XIL: frontend ularni
#    `report-errors.ts::REPORT_ERROR_CODES` orqali uch tilda sabab + keyingi
#    qadam matniga o'giradi. Yangi kod yozilsa ekranda «noma'lum xato»
#    chiqardi, holbuki sabab oddiy — «davr juda uzun».
_REPORT_PERIOD_FUTURE = "report_period_future"
_REPORT_PERIOD_INVALID = "report_period_invalid"
_REPORT_PERIOD_TOO_LONG = "report_period_too_long"
_REPORT_TOO_LARGE = "report_too_large"

_FILENAME_UNSAFE = re.compile(r"[^A-Za-z0-9_-]+")

ReportFromDep = Annotated[date, Query(alias="from")]
ReportToDep = Annotated[date, Query(alias="to")]


def _check_report_period(from_date: date, to_date: date) -> None:
    """Davr tekshiruvi — ⛔ JIMGINA KESILMAYDI, rad etiladi (`reports.py` qoidasi).

    `reports.py::_report_period` dan FARQI: yuqori chegara BUGUN, kecha
    emas. Avtoturargoh hodisalari real vaqtda keladi (D+1 yopilish yo'q),
    ya'ni bugungi kun ham to'liq ma'noli — direktor «bugun qancha kirdi?»
    deb so'raydi.
    """
    today = datetime.now(TASHKENT).date()
    if to_date > today:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=_REPORT_PERIOD_FUTURE
        )
    if from_date > to_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=_REPORT_PERIOD_INVALID
        )
    if (to_date - from_date).days + 1 > parking_report.MAX_PERIOD_DAYS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=_REPORT_PERIOD_TOO_LONG
        )


async def _parking_report(
    session: Any,
    principal: Principal,
    settings: Any,
    site_id: str,
    from_date: date,
    to_date: date,
) -> tuple[edge_repo.SiteRow, parking_report.ParkingReport]:
    """JSON va `.xlsx` marshrutlarining UMUMIY boshi — bitta hisob, ikki shakl.

    Hisob `parking_report.build_parking_report` da (sof funksiya); bu yerda
    faqat davr tekshiruvi, hodisalarni olish va hajm darvozasi.
    """
    market_id = _market_id(principal)
    site = await _site_or_404(session, market_id, site_id)
    _check_report_period(from_date, to_date)

    start = datetime.combine(from_date, time.min, tzinfo=TASHKENT)
    end = datetime.combine(to_date, time.min, tzinfo=TASHKENT) + timedelta(days=1)
    rows = await edge_repo.summary_events(
        session, market_id, site.id, types=parking_report.EVENT_TYPES, start=start, end=end
    )
    report = parking_report.build_parking_report(rows, from_date=from_date, to_date=to_date)

    # ⛔ Seanslar ro'yxati JIMGINA KESILMAYDI (`reports.py::_guard_row_count`
    #    qoidasi): kesilgan varaq to'liq ko'rinardi va direktor yetishmagan
    #    mashinalarni hech qachon sezmasdi.
    if len(report.sessions) > settings.report_max_rows:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=_REPORT_TOO_LARGE
        )
    return site, report


def _report_out(site: edge_repo.SiteRow, report: parking_report.ParkingReport) -> ParkingReportOut:
    return ParkingReportOut(
        site_id=site.id,
        site_name=site.name,
        from_date=report.from_date,
        to_date=report.to_date,
        days=[
            ParkingReportDayOut(
                date=day.day,
                entries=day.entries,
                exits=day.exits,
                cash=day.cash_soum,
                terminal=day.terminal_soum,
                total=day.total_soum,
                free_count=day.free_count,
            )
            for day in report.days
        ],
        total=ParkingReportTotalsOut(
            entries=report.total.entries,
            exits=report.total.exits,
            cash=report.total.cash_soum,
            terminal=report.total.terminal_soum,
            total=report.total.total_soum,
            free_count=report.total.free_count,
        ),
        sessions=[
            ParkingReportSessionOut(
                session_id=row.session_id,
                plate=row.plate,
                entered_at=row.entered_at,
                exited_at=row.exited_at,
                duration_minutes=row.duration_minutes,
                amount_soum=row.amount_soum,
                method=row.method,
                reason=row.reason,
                entry_file_id=row.entry_file_id,
                opened_at_exit=row.opened_at_exit,
            )
            for row in report.sessions
        ],
        hours=[
            ParkingReportHourOut(hour=row.hour, entries=row.entries, exits=row.exits)
            for row in report.hours
        ],
        stay=ParkingReportStayOut(
            measured=report.stay.measured,
            median_minutes=report.stay.median_minutes,
            buckets=[
                ParkingReportStayBucketOut(key=bucket.key, count=bucket.count)
                for bucket in report.stay.buckets
            ],
            unrecorded_entries=report.stay.unrecorded_entries,
        ),
        exit_reasons=[
            ParkingReportExitReasonOut(reason=item.reason, count=item.count)
            for item in report.exit_reasons
        ],
        inside=report.inside,
        paid_sessions=report.paid_sessions,
        average_check_soum=report.average_check_soum,
        regulars=[
            ParkingReportRegularOut(
                plate=item.plate,
                visits=item.visits,
                amount_soum=item.amount_soum,
                last_seen_at=item.last_seen_at,
            )
            for item in report.regulars
        ],
    )


@router.get("/{site_id}/parking-report", response_model=ParkingReportOut)
async def parking_report_json(
    site_id: str,
    principal: ViewerDep,
    session: TenantSessionDep,
    settings: SettingsDep,
    from_date: ReportFromDep,
    to_date: ReportToDep,
) -> ParkingReportOut:
    """Davr (Toshkent kunlari, `to` kiradi, eng ko'pi 92 kun): kunlar,
    yig'indi va mashinalar ro'yxati.

    Huquq `parking-summary` bilan AYNI (`CAMERA_VIEW`) — direktor va
    ma'muriyat ko'radi, kassir yo'q.
    """
    site, report = await _parking_report(session, principal, settings, site_id, from_date, to_date)
    return _report_out(site, report)


@router.get("/{site_id}/parking-report.xlsx", response_class=StreamingResponse)
async def parking_report_xlsx(
    site_id: str,
    principal: ViewerDep,
    session: TenantSessionDep,
    settings: SettingsDep,
    from_date: ReportFromDep,
    to_date: ReportToDep,
) -> StreamingResponse:
    """Xuddi shu hisobot `.xlsx` bo'lib: «Kunlar» (JAMI qatori bilan) va
    «Mashinalar» varaqlari. Til — so'rovchining profilidan (D-06).

    Fayl nomi `avtoturargoh_{site_id}_{from}_{to}.xlsx` — TO'LIQ ASCII
    (`Content-Disposition` sarlavhasiga tushadi), obyekt identifikatori
    serverniki va ASCII, lekin baribir tozalanadi.
    """
    site, report = await _parking_report(session, principal, settings, site_id, from_date, to_date)
    locale = await _locale_of(session, principal)
    payload = parking_report.build_parking_report_workbook(
        report, locale=locale, site_name=site.name
    )
    filename = (
        f"avtoturargoh_{_FILENAME_UNSAFE.sub('-', site.id)}"
        f"_{from_date.isoformat()}_{to_date.isoformat()}.xlsx"
    )
    return _xlsx_response(payload, filename)


# ---------------------------------------------------------------------------
# Kadr
# ---------------------------------------------------------------------------


@router.get(
    "/{site_id}/files/{file_id}",
    response_class=StreamingResponse,
    dependencies=[Depends(require_permission(Permission.CAMERA_VIEW))],
)
async def site_file(
    site_id: str,
    file_id: str,
    principal: ViewerDep,
    intent: FrameIntentDep,
    session: TenantSessionDep,
    settings: SettingsDep,
) -> StreamingResponse:
    """Agent yuklagan kadr — core-api orqali proksi; ochilishi auditda (`edge_frame_view`).

    ⚠ IMZODAGI TARTIB: `principal` `intent` DAN OLDIN (403 audit yozmaydi).
    Begona/mavjud bo'lmagan obyekt va fayl — BIR XIL 404.
    """
    market_id = _market_id(principal)
    site = await _site_or_404(session, market_id, site_id)
    if len(file_id) != 64 or not all(c in "0123456789abcdef" for c in file_id):
        raise _not_found()
    found = await edge_repo.get_file(session, market_id, site.id, file_id)
    if found is None:
        raise _not_found()
    try:
        async with storage.open(settings) as client:
            payload = await client.get(found.storage_key)
    except StorageError as exc:
        log.warning("edge_file_storage_unavailable", site_id=site.id, error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="storage_unavailable"
        ) from exc
    intent.filters = {"site_id": site.id, "file_id": file_id}
    intent.result_count = 1

    async def _body() -> AsyncIterator[bytes]:
        yield payload

    return StreamingResponse(
        _body(),
        media_type=found.content_type,
        headers={"Cache-Control": "private, no-store", "Content-Length": str(len(payload))},
    )
