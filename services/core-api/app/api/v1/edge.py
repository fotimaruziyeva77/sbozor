"""Universal agent protokoli v1 — `/api/v1/edge/*` (0036).

Agent (Windows, `sbozor-agent`) serverga O'ZI ulanadi: long-poll, hodisalar,
fayllar, natijalar, yurak urishi. Protokol — agent repozitoriyasidagi
`docs/protocol-http.md`; sxemalar — `app/edge_contract/schemas/`.

=============================================================================
⛔ FOYDALANUVCHI SESSIYASI YO'Q. Autentifikatsiya — `Authorization: Bearer
   <token>` + `X-Instance-Id`. Serverda faqat tokenning SHA-256 xeshi.
   Bozor tokendan `edge_agent_auth()` (SECURITY DEFINER) orqali topiladi,
   keyingi BARCHA so'rovlar `set_tenant_context(..., SYSTEM)` bilan RLS
   ostida. Cross-tenant matritsasidan chiqarilishi
   `tests/tenancy/test_cross_tenant.py::EXEMPT_ROUTES` da sabab bilan,
   qamrovi `tests/integration/test_edge.py` da.
⛔ Agent faqat O'Z obyektini ko'radi: hodisadagi `site_id`/`agent_id`
   tokendagidan farq qilsa — rad etiladi.
=============================================================================
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any, Literal
from uuid import UUID
from zoneinfo import ZoneInfo

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.deps import SettingsDep
from app.edge_contract import ContractError, validate_config, validate_envelope, validate_result
from app.repositories import binding_repo, edge_repo
from app.services import storage
from app.services.edge_config import effective_config
from app.services.storage import StorageError

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

__all__ = ["router", "server_time"]

log = structlog.get_logger(__name__)

router = APIRouter(tags=["edge-agent"])

TASHKENT = ZoneInfo("Asia/Tashkent")
MAX_EVENTS = 200
MAX_FILE_BYTES = 5 * 1024 * 1024
MAX_WAIT_S = 25
POLL_STEP_S = 1.0

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_VERSION_RE = re.compile(r"^\d{1,4}\.\d{1,4}\.\d{1,6}(-[0-9A-Za-z]+(\.[0-9A-Za-z]+)*)?$")
_ALLOWED_FILE_TYPES = frozenset({"image/jpeg", "image/png", "application/octet-stream"})


def server_time() -> str:
    """Joriy vaqt `+05:00` bilan (agent soat farqini shundan o'lchaydi)."""
    return datetime.now(TASHKENT).isoformat(timespec="seconds")


def _sessionmaker(request: Request) -> async_sessionmaker[AsyncSession]:
    return request.app.state.sessionmaker  # type: ignore[no-any-return]


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class AgentContext:
    agent_id: str
    site_id: str
    market_id: UUID


async def agent_context(request: Request) -> AgentContext:
    """Bearer token + `X-Instance-Id` -> agent. 401 / 409."""
    header = request.headers.get("authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="not_authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    async with _sessionmaker(request)() as session:
        auth = await edge_repo.agent_auth(session, _token_hash(token.strip()))
    if auth is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid_token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    instance = request.headers.get("x-instance-id", "")
    if not secrets.compare_digest(instance.encode(), auth.instance_id.encode()):
        log.warning("edge_instance_conflict", agent_id=auth.agent_id)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="instance_conflict")
    return AgentContext(agent_id=auth.agent_id, site_id=auth.site_id, market_id=auth.market_id)


AgentDep = Annotated[AgentContext, Depends(agent_context)]


def _tenant(request: Request, agent: AgentContext, what: str) -> Any:
    return binding_repo.tenant_session(
        _sessionmaker(request),
        market_id=agent.market_id,
        request_id=f"edge:{what}:{agent.agent_id}",
    )


# ---------------------------------------------------------------------------
# POST /activate
# ---------------------------------------------------------------------------


class ActivateRequest(BaseModel):
    code: str = Field(min_length=1, max_length=32)
    instance_id: str = Field(min_length=1, max_length=128)
    hostname: str = Field(default="", max_length=128)
    version: str = Field(default="", max_length=64)
    os: str = Field(default="", max_length=64)


class ActivateResponse(BaseModel):
    agent_id: str
    site_id: str
    token: str


_CODE_INVALID = "code_invalid"


@router.post("/activate", response_model=ActivateResponse)
async def activate(body: ActivateRequest, request: Request) -> ActivateResponse:
    """Bir martalik kod -> token. 404 kod yaroqsiz; 409 obyektda boshqa nusxa jonli."""
    code = body.code.strip().upper()
    async with _sessionmaker(request)() as session:
        found = await edge_repo.activation_find(session, code)
    now = datetime.now(UTC)
    if found is None or found.used_at is not None or found.expires_at <= now:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_CODE_INVALID)

    agent_id = f"agt-{secrets.token_hex(8)}"
    token = secrets.token_urlsafe(32)
    async with binding_repo.tenant_session(
        _sessionmaker(request), market_id=found.market_id, request_id=f"edge:activate:{agent_id}"
    ) as session:
        if await edge_repo.live_conflict(session, found.market_id, found.site_id, body.instance_id):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="instance_conflict")
        if not await edge_repo.claim_code(
            session, found.market_id, found.code_id, agent_id=agent_id
        ):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_CODE_INVALID)
        await edge_repo.create_agent(
            session,
            found.market_id,
            agent_id=agent_id,
            site_id=found.site_id,
            token_sha256=_token_hash(token),
            instance_id=body.instance_id,
            hostname=body.hostname,
            version=body.version,
            os=body.os,
        )
    log.info("edge_agent_activated", agent_id=agent_id, site_id=found.site_id)
    return ActivateResponse(agent_id=agent_id, site_id=found.site_id, token=token)


# ---------------------------------------------------------------------------
# GET /poll
# ---------------------------------------------------------------------------


class PollResponse(BaseModel):
    server_time: str
    config: dict[str, Any] | None
    commands: list[dict[str, Any]]


def _command_out(command: edge_repo.CommandRow) -> dict[str, Any]:
    return {
        "id": str(command.id),
        "type": command.type,
        "v": 1,
        "site_id": command.site_id,
        "issued_at": command.issued_at.isoformat(),
        "expires_at": command.expires_at.isoformat(),
        "issued_by": command.issued_by,
        "data": command.data,
    }


async def _poll_once(
    session: AsyncSession, agent: AgentContext, config_version: int
) -> PollResponse | None:
    site = await edge_repo.get_site(session, agent.market_id, agent.site_id)
    if site is None:  # pragma: no cover — FK kafolati
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found")
    current = await edge_repo.latest_config(session, agent.market_id, agent.site_id)
    newer = current is not None and current.version > config_version
    has_commands = await edge_repo.pending_commands(session, agent.market_id, agent.site_id)
    if not newer and not has_commands:
        return None
    config = None
    if newer and current is not None:
        config = effective_config(
            site_id=site.id,
            kind=site.kind,
            version=current.version,
            doc=current.doc,
            setup=site.setup,
        )
    commands = await edge_repo.deliver_commands(session, agent.market_id, agent.site_id)
    return PollResponse(
        server_time=server_time(), config=config, commands=[_command_out(c) for c in commands]
    )


@router.get("/poll", response_model=PollResponse)
async def poll(
    request: Request,
    agent: AgentDep,
    config_version: Annotated[int, Query(ge=0)] = 0,
    wait: Annotated[int, Query(ge=0)] = MAX_WAIT_S,
) -> PollResponse:
    """Long-poll: yangi sozlama yoki buyruq bo'lsa darhol, aks holda `wait` (≤25 s) gacha."""
    deadline = asyncio.get_running_loop().time() + min(wait, MAX_WAIT_S)
    first = True
    while True:
        async with _tenant(request, agent, "poll") as session:
            if first:
                await edge_repo.touch_agent(session, agent.market_id, agent.agent_id)
                first = False
            result = await _poll_once(session, agent, config_version)
        if result is not None:
            return result
        remaining = deadline - asyncio.get_running_loop().time()
        if remaining <= 0 or await request.is_disconnected():
            return PollResponse(server_time=server_time(), config=None, commands=[])
        await asyncio.sleep(min(POLL_STEP_S, remaining))


# ---------------------------------------------------------------------------
# POST /events
# ---------------------------------------------------------------------------


class EventsRequest(BaseModel):
    events: list[Any] = Field(max_length=MAX_EVENTS)


class Rejected(BaseModel):
    id: str
    reason: str


class EventsResponse(BaseModel):
    accepted: list[str]
    rejected: list[Rejected]


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("z", "Z"))


@router.post("/events", response_model=EventsResponse)
async def post_events(body: EventsRequest, request: Request, agent: AgentDep) -> EventsResponse:
    """Hodisalar paketi (≤200). `id` bo'yicha idempotent; yaroqsizlari `rejected`."""
    accepted: list[str] = []
    rejected: list[Rejected] = []
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for event in body.events:
        event_id = str(event.get("id", "")) if isinstance(event, dict) else ""
        try:
            validate_envelope(event)
        except ContractError as exc:
            rejected.append(Rejected(id=event_id, reason=str(exc)[:500]))
            continue
        if event["site_id"] != agent.site_id:
            rejected.append(Rejected(id=event_id, reason="site_id: boshqa obyekt"))
            continue
        if event["agent_id"] != agent.agent_id:
            rejected.append(Rejected(id=event_id, reason="agent_id: boshqa agent"))
            continue
        accepted.append(event_id)
        if event_id in seen:
            continue
        seen.add(event_id)
        rows.append(
            {
                "id": UUID(event_id),
                "agent_id": agent.agent_id,
                "type": event["type"],
                "v": event["v"],
                "seq": event["seq"],
                "occurred_at": _parse_time(event["occurred_at"]),
                "clock_ok": event["clock_ok"],
                "correlation_id": UUID(event["correlation_id"])
                if event.get("correlation_id")
                else None,
                "data": event["data"],
            }
        )
    if rows:
        async with _tenant(request, agent, "events") as session:
            await edge_repo.insert_events(session, agent.market_id, agent.site_id, rows)
    return EventsResponse(accepted=accepted, rejected=rejected)


# ---------------------------------------------------------------------------
# HEAD / PUT /files/{sha256}
# ---------------------------------------------------------------------------


def _check_sha(sha256: str) -> None:
    if not _SHA256_RE.match(sha256):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="sha256_invalid")


def storage_key(site_id: str, sha256: str) -> str:
    """`edge/{site_id}/{sha256}` — ikkala segment ham server tomonida tekshirilgan."""
    return f"edge/{site_id}/{sha256}"


@router.head("/files/{sha256}", include_in_schema=False)
async def head_file(sha256: str, request: Request, agent: AgentDep) -> Response:
    """`200` fayl bor, `404` yo'q."""
    if not _SHA256_RE.match(sha256):
        return Response(status_code=status.HTTP_404_NOT_FOUND)
    async with _tenant(request, agent, "file-head") as session:
        found = await edge_repo.get_file(session, agent.market_id, agent.site_id, sha256)
    return Response(status_code=status.HTTP_200_OK if found else status.HTTP_404_NOT_FOUND)


class FileStored(BaseModel):
    sha256: str
    size: int


@router.put("/files/{sha256}", response_model=FileStored)
async def put_file(
    sha256: str, request: Request, agent: AgentDep, settings: SettingsDep
) -> FileStored:
    """Kadr (≤5 MB). Xesh mos kelmasa 400; takror yuborish — 200."""
    _check_sha(sha256)
    declared = request.headers.get("content-length")
    if declared is not None and declared.isdigit() and int(declared) > MAX_FILE_BYTES:
        raise HTTPException(status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail="file_too_large")
    data = bytearray()
    async for chunk in request.stream():
        data.extend(chunk)
        if len(data) > MAX_FILE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail="file_too_large"
            )
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="file_empty")
    if hashlib.sha256(data).hexdigest() != sha256:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="hash_mismatch")
    content_type = request.headers.get("content-type", "image/jpeg").split(";")[0].strip().lower()
    if content_type not in _ALLOWED_FILE_TYPES:
        content_type = "application/octet-stream"

    async with _tenant(request, agent, "file-check") as session:
        existing = await edge_repo.get_file(session, agent.market_id, agent.site_id, sha256)
    if existing is not None:
        return FileStored(sha256=sha256, size=existing.size)

    key = storage_key(agent.site_id, sha256)
    try:
        async with storage.open(settings) as client:
            await client.put(key, bytes(data), content_type=content_type)
    except StorageError as exc:
        log.warning("edge_file_storage_unavailable", site_id=agent.site_id, error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="storage_unavailable"
        ) from exc

    async with _tenant(request, agent, "file-put") as session:
        await edge_repo.insert_file(
            session,
            agent.market_id,
            agent.site_id,
            sha256=sha256,
            size=len(data),
            content_type=content_type,
            storage_key=key,
        )
    return FileStored(sha256=sha256, size=len(data))


# ---------------------------------------------------------------------------
# POST /results
# ---------------------------------------------------------------------------


class ResultsRequest(BaseModel):
    results: list[Any] = Field(max_length=MAX_EVENTS)


class ResultsResponse(BaseModel):
    accepted: list[str]
    rejected: list[Rejected]


@router.post("/results", response_model=ResultsResponse)
async def post_results(body: ResultsRequest, request: Request, agent: AgentDep) -> ResultsResponse:
    """Buyruq natijalari — faqat SHU obyektning buyruqlari yangilanadi."""
    valid: list[tuple[UUID, str, str | None]] = []
    rejected: list[Rejected] = []
    for item in body.results:
        item_id = str(item.get("command_id", "")) if isinstance(item, dict) else ""
        errors = validate_result(item)
        if errors:
            rejected.append(Rejected(id=item_id, reason=str(errors[0])[:500]))
            continue
        valid.append((UUID(item["command_id"]), item["status"], item.get("reason")))
    found: set[UUID] = set()
    if valid:
        async with _tenant(request, agent, "results") as session:
            found = await edge_repo.set_results(session, agent.market_id, agent.site_id, valid)
    accepted = [str(command_id) for command_id, _, _ in valid if command_id in found]
    rejected += [
        Rejected(id=str(command_id), reason="command_id: topilmadi")
        for command_id, _, _ in valid
        if command_id not in found
    ]
    return ResultsResponse(accepted=accepted, rejected=rejected)


# ---------------------------------------------------------------------------
# POST /heartbeat
# ---------------------------------------------------------------------------


class HeartbeatResponse(BaseModel):
    server_time: str


_HEARTBEAT_MAX_BYTES = 64 * 1024


@router.post("/heartbeat", response_model=HeartbeatResponse)
async def heartbeat(request: Request, agent: AgentDep) -> HeartbeatResponse:
    """Har 60 s: holat panelda ko'rinadi (`last_seen_at`, `last_heartbeat`)."""
    raw = await request.body()
    if len(raw) > _HEARTBEAT_MAX_BYTES:
        raise HTTPException(status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail="too_large")
    try:
        payload = json.loads(raw or b"{}")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="json_invalid") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="json_invalid")
    async with _tenant(request, agent, "heartbeat") as session:
        await edge_repo.record_heartbeat(session, agent.market_id, agent.agent_id, payload)
    return HeartbeatResponse(server_time=server_time())


# ---------------------------------------------------------------------------
# PUT /site-setup
# ---------------------------------------------------------------------------


class SiteSetup(BaseModel):
    devices: list[dict[str, Any]] = Field(default_factory=list, max_length=500)
    lanes: list[dict[str, Any]] = Field(default_factory=list, max_length=200)


class SetupStored(BaseModel):
    devices: int
    lanes: int


@router.put("/site-setup", response_model=SetupStored)
async def put_site_setup(body: SiteSetup, request: Request, agent: AgentDep) -> SetupStored:
    """Obyekt tuzilmasi (qurilmalar, yo'laklar). Parol YO'Q — sxema `password` ni rad etadi."""
    setup = {"devices": body.devices, "lanes": body.lanes}
    probe = {
        "config_version": 1,
        "site": {"id": agent.site_id, "type": "parking", "timezone": "Asia/Tashkent"},
        "plugins": ["parking"],
        "update": {"channel": "stable", "auto": True},
        **setup,
    }
    errors = [e for e in validate_config(probe) if e.path.startswith(("devices", "lanes"))]
    if errors:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "setup_invalid",
                "errors": [{"path": e.path, "message": e.message} for e in errors],
            },
        )
    async with _tenant(request, agent, "site-setup") as session:
        await edge_repo.set_setup(session, agent.market_id, agent.site_id, setup)
    return SetupStored(devices=len(body.devices), lanes=len(body.lanes))


# ---------------------------------------------------------------------------
# Relizlar
# ---------------------------------------------------------------------------


def _releases_dir(settings: Any) -> Path:
    return Path(settings.edge_releases_dir)


def _binary_path(base: Path, version: str) -> Path | None:
    """Versiya QAT'IY tekshiriladi — yo'l bo'lagi (`/`, `..`) kira olmaydi."""
    if not _VERSION_RE.match(version) or ".." in version:
        return None
    path = base / "bin" / f"sbozor-agent-{version}.exe"
    try:
        if path.resolve().parent != (base / "bin").resolve():
            return None
    except OSError:
        return None
    return path if path.is_file() else None


@router.get("/releases/latest")
async def releases_latest(
    agent: AgentDep,
    settings: SettingsDep,
    channel: Literal["stable", "pilot"] = "stable",
) -> Response:
    """Imzolangan manifest SO'ZMA-SO'Z (imzo baytlarga qo'yilgan). Yo'q bo'lsa 204."""
    del agent
    path = _releases_dir(settings) / channel / "latest.json"
    try:
        content = path.read_bytes()
    except OSError:
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    return Response(content=content, media_type="application/json")


@router.get("/releases/binary/{version}")
async def releases_binary(version: str, agent: AgentDep, settings: SettingsDep) -> Response:
    """Imzolangan relizning `.exe` fayli."""
    del agent
    path = _binary_path(_releases_dir(settings), version)
    if path is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found")
    return FileResponse(path, media_type="application/octet-stream", filename=path.name)


@router.get("/download")
async def download(settings: SettingsDep) -> Response:
    """Tokensiz: eng so'nggi `stable` `.exe` (birinchi o'rnatish uchun)."""
    base = _releases_dir(settings)
    try:
        signed = json.loads((base / "stable" / "latest.json").read_bytes())
        manifest = signed["manifest"]
        if isinstance(manifest, str):
            manifest = json.loads(manifest)
        version = str(manifest["version"])
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found") from exc
    path = _binary_path(base, version)
    if path is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found")
    return FileResponse(path, media_type="application/octet-stream", filename=path.name)
