"""agent_gateway — FastAPI router: WS, snapshot, aktivatsiya, admin panel.

Protokol: docs/protocol.md (v1). sbozor bu routerni o'z app'iga
include_router() bilan ulaydi; dev rejimda `python -m agent_gateway`.
"""
from __future__ import annotations

import asyncio
import hashlib
import html
import json
import re
import secrets
import time
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, FastAPI, Form, Header, Request, WebSocket, WebSocketDisconnect
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response

from . import video_routes
from .db import GatewayDB
from .media import MediaServer
from .retention import retention_days
from .retention import sweep as retention_sweep
from .storage import DiskStorage, SnapshotStorage

ALLOWED_COMMANDS = {
    "snapshot_now", "rescan_nvr", "update_config", "update_credentials",
    "enable_channel", "disable_channel", "restart", "get_logs",
    "start_stream", "stop_stream", "update_agent",
}

MAX_SCHEDULE_SLOTS = 48
"""Bir kundagi kadr olish vaqtlari chegarasi (yarim soatlik jadval sig'adi).

Bu — xato yozuvdan himoya, texnik chegara emas: 40 kamerali bozorda 48 slot
kuniga 1920 rasm degani va sekin uplink'da navbat ulgurmasdi. Chegaraga
urilgan operator o'ylab ko'rishi kerak."""


def parse_schedule(times: str) -> list[str]:
    """«06:00, 7:00» -> `["06:00", "07:00"]`. Xato bo'lsa `ValueError`.

    ⛔ IKKI FORMA HAM SHU YERGA KELADI (kod yaratish va jadvalni
       o'zgartirish). Ikkinchi nusxa yozilsa ular vaqt o'tib bir-biridan
       ajralardi va operator bir joyda qabul qilingan yozuvni ikkinchisida
       rad etilgan holda ko'rardi.

    Natija TARTIBLANGAN va TAKRORSIZ: agent jadvalni shu ko'rinishda
    saqlaydi, panel esa shuni ko'rsatadi — ikkalasi bir xil bo'lmasa
    operator «saqlanmadi shekilli» deb qayta yuborardi.
    """
    parsed: list[str] = []
    for raw in re.split(r"[,\s;]+", times.strip()):
        if not raw:
            continue
        m = re.fullmatch(r"([01]?\d|2[0-3]):([0-5]\d)", raw)
        if not m:
            raise ValueError(f"vaqt formati noto'g'ri: {raw!r} — HH:MM kutilgan")
        parsed.append(f"{int(m.group(1)):02d}:{m.group(2)}")
    schedule = sorted(set(parsed))
    if not schedule:
        raise ValueError("kamida bitta vaqt kerak — bo'sh jadval rasm olishni "
                         "butunlay to'xtatardi")
    if len(schedule) > MAX_SCHEDULE_SLOTS:
        raise ValueError(f"{MAX_SCHEDULE_SLOTS} tadan ko'p vaqt kiritildi")
    return schedule

DEFAULT_CONFIG = {
    "v": 1,
    "agent_key_prefix": "",  # agent yaratilganda to'ldiriladi
    # Navoiy viloyati bozorlari uchun: ertalab 06:00 dan 10:00 gacha har soatda,
    # kechqurun 17:00 va 18:00 da. Boshqa vaqtda rasm olinmaydi.
    # Bu STANDART qiymat — har obyekt uchun paneldan o'zgartirilishi mumkin.
    "schedule": ["06:00", "07:00", "08:00", "09:00", "10:00", "17:00", "18:00"],
    "timezone": "Asia/Samarkand",
    "quality": {"jpeg_quality": 80, "max_width": 1920, "profile": "standard"},
    "channel_gap_s": 2.5,
    "heartbeat_s": 60,
    "channels_disabled": [],
    "disk_cap_mb": 5000,
    "catchup_window_min": 120,
    "upload_rate_kbps": 0,
    "upload_url": "",
    "speedtest": {"interval_days": 7, "size_kb": 2048},
    # `max_channels` standarti 2 — protokol 5-bo'lim bilan bir xil. Kerakli
    # bozorga paneldan (update_config) 16 gacha ko'tariladi; standartni 16
    # qilish sekin uplink'li obyektda rasm olishni bo'g'ib qo'yardi.
    "stream": {"enabled": True, "max_duration_s": 600, "max_channels": 2,
               "copy_codec": False},
}

HEARTBEAT_RED_S = 600  # 10 daqiqa heartbeat yo'q → qizil holat
MAX_SNAPSHOT_MB = 25   # bitta kadr uchun oqilona chegara (haqiqiylari ~40 KB)
ACTIVATE_MAX_TRIES = 10        # bir IP dan
ACTIVATE_WINDOW_S = 600        # 10 daqiqada

PANEL_MAX_TRIES = 12           # xato kalit bilan, bir IP dan
PANEL_WINDOW_S = 600
"""Panel kaliti uchun tezlik limiti (260828).

Kalit 24 baytlik tasodifiy satr, ya'ni uni TOPIB bo'lmaydi. Limit boshqa
narsa uchun: panel teskari proksi orqali INTERNETGA chiqarilganda xato
kalit bilan kelgan so'rovlar oqimi jurnalni to'ldirardi va haqiqiy
hodisalar orasida yo'qolardi. Chegara xato urinishlarga qo'yiladi —
to'g'ri kalit bilan ishlayotgan operator hech qachon sezmaydi."""


class RateLimiter:
    """Oddiy oyna asosidagi tezlik limiti.

    Aktivatsiya uchun majburiy: kod topilsa agent tokeni qo'lga tushadi.
    12 obyekt uchun xotiradagi hisob yetarli; sbozor'da Redis'ga ko'chadi.
    """

    def __init__(self, max_tries: int, window_s: float):
        self.max_tries = max_tries
        self.window_s = window_s
        self._hits: dict[str, list[float]] = {}

    def allow(self, key: str) -> bool:
        """Shu IP hali urinib ko'rishi mumkinmi.

        DIQQAT: bu yerda HECH NARSA sanalmaydi. Faqat XATO urinish `fail()`
        orqali sanaladi. Ilgari har murojaat sanalardi va bir NAT ortidagi
        (bitta operator, bitta tashqi IP) 12 bozor o'rnatilganda 11-si
        "too_many_attempts" olardi — hujum emas, oddiy o'rnatish kuni.
        Brute-force esa aynan xato urinishlardan iborat, shuning uchun
        himoya kuchi kamaymaydi.
        """
        now = time.time()
        hits = [t for t in self._hits.get(key, []) if now - t < self.window_s]
        self._hits[key] = hits
        return len(hits) < self.max_tries

    def fail(self, key: str) -> None:
        """Kod noto'g'ri chiqdi — shu urinish hisobga olinadi."""
        now = time.time()
        hits = [t for t in self._hits.get(key, []) if now - t < self.window_s]
        hits.append(now)
        self._hits[key] = hits
        if len(self._hits) > 10_000:          # xotira o'smasin
            self._hits = {k: v for k, v in self._hits.items()
                          if v and now - v[-1] < self.window_s}

# Panel uslubi. Ranglar oshkora belgilangan: brauzer qorong'i rejimda
# sahifani o'zicha ag'darib, matnni o'qib bo'lmaydigan qilib qo'ymasin.
_CSS = """
:root{--bg:#f7f7f8;--card:#fff;--fg:#1a1a1a;--muted:#5c5c5c;--line:#d6d6da;
 --head:#ececef;--ok:#1b7f3b;--warn:#b26a00;--bad:#c62828;--link:#0b5fbf}
@media (prefers-color-scheme:dark){
 :root{--bg:#16181c;--card:#1e2126;--fg:#e8e8ea;--muted:#a0a4ad;--line:#343841;
  --head:#272b32;--ok:#5ec27a;--warn:#e0a33a;--bad:#f0736e;--link:#6fb2ff}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
 font:14px/1.5 "Segoe UI",system-ui,sans-serif}
.wrap{max-width:1180px;margin:0 auto;padding:20px 18px 60px}
h1{font-size:22px;margin:0 0 4px}h2{font-size:16px;margin:26px 0 8px}
h3{font-size:14px;margin:20px 0 6px}
a{color:var(--link)}
p.hint{color:var(--muted);margin:4px 0 12px}
.tablewrap{overflow-x:auto;background:var(--card);border:1px solid var(--line);
 border-radius:8px}
table{border-collapse:collapse;width:100%}
th,td{padding:7px 11px;text-align:left;border-bottom:1px solid var(--line);
 white-space:nowrap}
th{background:var(--head);font-weight:600;font-size:12px;
 text-transform:uppercase;letter-spacing:.03em;color:var(--muted)}
tr:last-child td{border-bottom:none}
td.wrapcell{white-space:normal;max-width:420px}
.ok{color:var(--ok);font-weight:600}.warn{color:var(--warn);font-weight:600}
.bad{color:var(--bad);font-weight:600}.muted{color:var(--muted)}
.dot{display:inline-block;width:8px;height:8px;border-radius:50%;
 margin-right:6px;vertical-align:middle}
code{background:var(--head);padding:1px 5px;border-radius:4px;font-size:12px}
form.inline{display:inline}
button{font:inherit;padding:5px 11px;border:1px solid var(--line);border-radius:6px;
 background:var(--card);color:var(--fg);cursor:pointer}
button:hover{background:var(--head)}
input,textarea{font:inherit;padding:5px 8px;border:1px solid var(--line);
 border-radius:6px;background:var(--card);color:var(--fg)}
.panel{background:var(--card);border:1px solid var(--line);border-radius:8px;
 padding:12px 14px;margin:12px 0}
.panel.alert{border-color:var(--bad);border-width:2px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(190px,1fr));gap:12px}
.thumb{background:var(--card);border:1px solid var(--line);border-radius:8px;
 overflow:hidden}
.thumb img{width:100%;display:block;aspect-ratio:16/9;object-fit:cover}
.thumb .cap{padding:6px 8px;font-size:12px;color:var(--muted)}
pre{background:var(--card);border:1px solid var(--line);border-radius:8px;
 padding:10px;overflow-x:auto;font-size:12px}
.empty{padding:14px;color:var(--muted)}
/* Kameralar to'ri — Hik-Connect uslubida. `auto-fill` ekran kengligiga
   moslashadi: keng monitorda 4-5 ustun, noutbukda 2-3 ustun. */
.wall{display:grid;gap:8px;margin-top:10px;
 grid-template-columns:repeat(auto-fill,minmax(300px,1fr))}
.cam{background:var(--card);border:1px solid var(--line);border-radius:8px;
 overflow:hidden}
.camview{position:relative;background:#000;aspect-ratio:16/9}
.camview video{width:100%;height:100%;object-fit:contain;display:block}
.camcap{padding:5px 8px;font-size:12px;white-space:nowrap;overflow:hidden;
 text-overflow:ellipsis}
/* Play tugmasi — video yo'q ekan markazda turadi, jonli bo'lganda
   burchakka kichrayadi va videoni to'smaydi. */
.play{position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);
 width:56px;height:56px;border-radius:50%;font-size:20px;line-height:1;
 background:rgba(255,255,255,.9);color:#111;border:none;cursor:pointer}
.play:hover{background:#fff}
.cam.bor .play{left:auto;top:auto;right:6px;bottom:6px;transform:none;
 width:26px;height:26px;font-size:11px;background:rgba(0,0,0,.55);color:#fff}
.badge{position:absolute;top:6px;right:6px;font-size:11px;padding:1px 6px;
 border-radius:4px;background:rgba(0,0,0,.65);color:#fff}
.badge:empty{display:none}
.badge.jonli{background:var(--bad);font-weight:700}
.badge.kutish{background:var(--warn);color:#000}
.badge.xato{background:#555}
/* Ikki marta bosilganda katta ko'rinish: butun ekranni egallaydi. */
body.kattada .wall{grid-template-columns:1fr}
body.kattada .cam:not(.katta){display:none}
.cam.katta .camview{aspect-ratio:auto;height:calc(100vh - 130px)}
"""


def _esc(value) -> str:
    """Har qanday qiymatni HTML uchun xavfsiz matnga aylantiradi.

    Bu maydonlarning KO'PI agentdan keladi (heartbeat, register). Qochirilmasa
    istalgan agent tokeni bo'lgan odam panelga skript joylashtira oladi va
    operator sahifani ochganda uning nomidan barcha obyektlarga buyruq
    yuboriladi.
    """
    if value is None or value == "":
        return "-"
    return html.escape(str(value))


def _fmt_mbps(value) -> str:
    """Tezlik matn bo'lib kelsa ham panel yiqilmasin."""
    try:
        return f"{float(value):.1f}"
    except (TypeError, ValueError):
        return "-"


def _clock_skew_s(agent_time_iso: str) -> float | None:
    """Agent vaqti bilan server vaqti orasidagi farq (soniya).

    Kompyuter soati adashgan bo'lsa dalil noto'g'ri vaqtga bog'lanadi va
    haqiqiy vaqtdagi bozor umuman suratga olinmaydi. Buni server sezishi
    kerak — agent o'zi sezmasligi mumkin.
    """
    if not agent_time_iso:
        return None
    try:
        t = datetime.fromisoformat(agent_time_iso.replace("Z", "+00:00"))
    except ValueError:
        return None
    return abs((datetime.now(timezone.utc) - t).total_seconds())


def _utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def detect_channel_changes(old_nvrs: list, new_nvrs: list) -> list[str]:
    """Kamera boshqa portga ulab qo'yilganini aniqlaydi.

    Server rasta<->kamera bog'lanishini kanal raqamiga qiladi. Kamera boshqa
    portga ko'chirilsa, rasmlar indamay boshqa rastaga yozila boshlaydi —
    ya'ni noto'g'ri odamga pul yoziladi. Shuning uchun kamera nomi yoki IP'si
    o'zgargan kanal darhol belgilanadi.
    """
    def index(nvrs: list) -> dict[str, dict]:
        out = {}
        for nvr in nvrs or []:
            for ch in nvr.get("channels") or []:
                out[f"{nvr.get('serial')}:{ch.get('id')}"] = ch
        return out

    before, after = index(old_nvrs), index(new_nvrs)
    changed = []
    for key, ch in after.items():
        prev = before.get(key)
        if prev is None:
            continue  # yangi kanal — o'zgarish emas
        old_ip, new_ip = prev.get("camera_ip") or "", ch.get("camera_ip") or ""
        old_name, new_name = prev.get("name") or "", ch.get("name") or ""
        if old_ip and new_ip and old_ip != new_ip:
            changed.append(f"{key}: kamera IP {old_ip} -> {new_ip}")
        elif old_name and new_name and old_name != new_name:
            changed.append(f"{key}: kamera nomi '{old_name}' -> '{new_name}'")
    for key in before:
        if key not in after:
            changed.append(f"{key}: kanal yo'qoldi")
    return changed


class Gateway:
    """Ulanishlar va holat. Bitta jarayon ichida yashaydi."""

    def __init__(self, data_dir: Path, storage: SnapshotStorage | None = None):
        self.data_dir = Path(data_dir)
        self.db = GatewayDB(self.data_dir / "gateway.db")
        self.storage = storage or DiskStorage(self.data_dir / "snapshots")
        self.live: dict[str, WebSocket] = {}          # agent_id -> ws
        self.live_instance: dict[str, str] = {}       # agent_id -> instance_id
        self.configs: dict[str, dict] = {}            # agent_id -> joriy config (keshi)
        # Karantin bazadan tiklanadi — server qayta yuklanganda kamera
        # ko'chirilgani haqidagi belgi yo'qolmasligi kerak.
        self.quarantined: dict[str, set[str]] = self.db.all_quarantine()
        self.activate_limiter = RateLimiter(ACTIVATE_MAX_TRIES, ACTIVATE_WINDOW_S)
        self.panel_limiter = RateLimiter(PANEL_MAX_TRIES, PANEL_WINDOW_S)
        # Jonli video. MediaMTX o'rnatilmagan bo'lsa hech narsa yiqilmaydi —
        # panel "yangilanuvchi rasm" zaxira rejimiga o'tadi.
        self.media = MediaServer(self.data_dir / "media")

    def quarantine_channels(self, agent_id: str, changes: list[str]) -> None:
        """O'zgargan kanallarni tahlildan chiqaradi (operator tasdiqlagunicha).

        Bazaga ham yoziladi: bu belgi noto'g'ri rastaga pul yozilishining
        oldini oladi va server qayta yuklanganda yo'qolib ketmasligi shart.
        """
        keys = {c.split(":", 2)[0] + ":" + c.split(":", 2)[1] for c in changes}
        self.quarantined.setdefault(agent_id, set()).update(keys)
        self.db.add_quarantine(agent_id, sorted(keys), "; ".join(changes)[:300])

    def config_for(self, agent: dict) -> dict:
        """Obyektning joriy konfiguratsiyasi: xotira → baza → standart."""
        agent_id = agent["agent_id"]
        cfg = self.configs.get(agent_id)
        if cfg is None:
            cfg = self.db.load_config(agent_id)      # server qayta yuklangan bo'lsa
        if cfg is None:
            cfg = json.loads(json.dumps(DEFAULT_CONFIG))
            cfg["agent_key_prefix"] = agent["key_prefix"]
        # Prefiks har doim bazadagi qiymatdan olinadi — u obyekt identifikatori.
        cfg["agent_key_prefix"] = agent["key_prefix"]
        self.configs[agent_id] = cfg
        return cfg

    def set_config(self, agent_id: str, config: dict) -> dict:
        """Operator o'zgartirgan sozlamani saqlaydi (xotirada VA bazada)."""
        self.configs[agent_id] = config
        self.db.save_config(agent_id, config)
        return config

    async def push_pending_commands(self, agent_id: str) -> None:
        ws = self.live.get(agent_id)
        if ws is None:
            return
        for cmd in self.db.pending_commands(agent_id):
            msg = {"v": 1, "type": "command", "id": cmd["cmd_id"],
                   "name": cmd["name"], "params": json.loads(cmd["params_json"] or "{}")}
            await ws.send_text(json.dumps(msg, ensure_ascii=False))
            self.db.mark_command_sent(cmd["cmd_id"])
            self.db.log_event(agent_id, "command_sent", f"{cmd['name']} ({cmd['cmd_id']})")


def build_router(data_dir: str | Path, storage: SnapshotStorage | None = None,
                 admin_token: str | None = None) -> APIRouter:
    """`admin_token` — /admin sahifalariga kirish kaliti.

    None bo'lsa tasodifiy yaratiladi va konsolga chiqariladi. Panelni
    ochiq qoldirib bo'lmaydi: undan agentlarga buyruq yuboriladi, ya'ni
    panelga kirgan odam 500 obyektning ichki tarmog'iga buyruq bera oladi.
    """
    gw = Gateway(Path(data_dir), storage)
    gw.admin_token = admin_token or secrets.token_urlsafe(24)
    router = APIRouter()
    router.gateway = gw  # testlar va sbozor uchun qulay havola

    def check_admin(request: Request) -> bool:
        """Panel kalitini tekshiradi va XATO urinishlarni sanaydi.

        ⚠ SANOQ FAQAT XATODA (`activate` bilan bir xil qaror): to'g'ri
          kalit bilan ishlayotgan operator sahifani necha marta yangilasa
          ham chegaraga urilmaydi.
        """
        client_ip = request.client.host if request.client else "?"
        supplied = (request.cookies.get("camagent_admin")
                    or request.query_params.get("token")
                    or request.headers.get("X-Admin-Token", ""))
        if not gw.panel_limiter.allow(client_ip):
            return False
        if secrets.compare_digest(supplied or "", gw.admin_token):
            return True
        gw.panel_limiter.fail(client_ip)
        return False

    def remember_token(request: Request, response: Response) -> Response:
        _secure(response)
        """Kalit manzilda kelgan bo'lsa cookie'ga yozamiz.

        Busiz panel ichidagi formalar ishlamaydi: forma POST qilganda
        manzildagi `?token=` yo'qoladi va server 401 qaytaradi — tugmalar
        jimgina ishlamay qo'yadi.
        """
        if request.query_params.get("token") == gw.admin_token:
            # Secure bayrog'i: HTTPS ulanishda cookie hech qachon
            # shifrlanmagan kanaldan ketmasin (audit topilmasi). sbozor
            # teskari proksi ortida `X-Forwarded-Proto` orqali bilinadi.
            https = (request.url.scheme == "https"
                     or request.headers.get("X-Forwarded-Proto") == "https")
            response.set_cookie("camagent_admin", gw.admin_token,
                                httponly=True, samesite="strict",
                                secure=https, max_age=12 * 3600)
        return response

    def deny() -> HTMLResponse:
        return _secure(HTMLResponse(
            _page("Kirish taqiqlangan",
                  "<h1>Kirish taqiqlangan</h1>"
                  "<p class='hint'>Panelga kirish uchun kalit kerak. Serverni "
                  "ishga tushirganda konsolga chiqarilgan havolani oching:<br>"
                  "<code>/admin?token=...</code></p>"),
            status_code=401))

    # ------------------------------------------------ aktivatsiya

    @router.post("/api/v1/agent/activate")
    async def activate(request: Request):
        client_ip = (request.client.host if request.client else "?")
        if not gw.activate_limiter.allow(client_ip):
            gw.db.log_event(None, "activate_throttled", f"IP {client_ip}")
            return JSONResponse({"v": 1, "error": "too_many_attempts"}, status_code=429)

        body = await request.json()
        code = str(body.get("activation_code", "")).strip()
        instance_id = str(body.get("instance_id", "")).strip()
        if not code or not instance_id:
            gw.activate_limiter.fail(client_ip)
            return JSONResponse({"v": 1, "error": "bad_request"}, status_code=400)
        info = gw.db.use_code(code, instance_id)
        if info is None:
            gw.activate_limiter.fail(client_ip)
            gw.db.log_event(None, "activate_fail", f"kod topilmadi: {code}")
            return JSONResponse({"v": 1, "error": "code_not_found"}, status_code=404)
        if info.get("used"):
            gw.activate_limiter.fail(client_ip)
            gw.db.log_event(None, "activate_fail", f"kod band: {code}")
            return JSONResponse({"v": 1, "error": "code_used"}, status_code=409)
        existing = gw.db.find_agent_for_code_reuse(instance_id, info["key_prefix"])
        if existing:
            agent = existing  # o'sha kompyuter qayta aktivatsiya qilyapti
        else:
            agent = gw.db.create_agent(info["market_name"], info["key_prefix"], instance_id)
        gw.db.log_event(agent["agent_id"], "activated", f"kod={code} instance={instance_id}")
        cfg = gw.config_for(gw.db.agent_by_id(agent["agent_id"]) or agent)
        # Kodga biriktirilgan sozlama (odatda jadval) — AGENT YOZUVI HALI
        # YO'Q bo'lgan paytda kiritilgan qaror. U faqat YANGI agentga
        # qo'llanadi: mavjud agentda paneldan kiritilgan jadval bo'lishi
        # mumkin va kodni qayta ishlatish uni ortga qaytarardi.
        if info.get("config") and not existing:
            cfg = {**cfg, **info["config"]}
            gw.set_config(agent["agent_id"], cfg)
            gw.db.log_event(agent["agent_id"], "config_from_code",
                            ", ".join(sorted(info["config"])))
        return {"v": 1, "token": agent["token"], "agent_id": agent["agent_id"], "config": cfg}

    # ------------------------------------------------ WebSocket

    @router.websocket("/api/v1/agent/ws")
    async def agent_ws(ws: WebSocket):
        await ws.accept()
        agent: dict | None = None
        try:
            raw = await asyncio.wait_for(ws.receive_text(), timeout=10)
            reg = json.loads(raw)
            if reg.get("v") is not None and reg.get("v") != 1:
                await ws.send_text(json.dumps(
                    {"v": 1, "type": "reject", "code": "bad_protocol_version"}))
                await ws.close(code=4002)
                return
            if reg.get("type") != "register":
                await ws.close(code=4000)
                return
            agent = await run_in_threadpool(gw.db.agent_by_token,
                                            str(reg.get("token", "")))
            if not agent:
                await ws.send_text(json.dumps({"v": 1, "type": "reject", "code": "bad_token"}))
                await ws.close(code=4001)
                return
            instance_id = str(reg.get("instance_id", ""))
            aid = agent["agent_id"]
            if aid in gw.live and gw.live_instance.get(aid) != instance_id:
                gw.db.set_warning(aid, f"instance_conflict: {instance_id}")
                gw.db.log_event(aid, "instance_conflict", instance_id)
                await ws.send_text(json.dumps({"v": 1, "type": "reject", "code": "instance_conflict"}))
                await ws.close(code=4009)
                return
            if agent.get("instance_id") and agent["instance_id"] != instance_id:
                # token ko'chirilgan .exe bilan boshqa kompyuterdan kelyapti
                gw.db.set_warning(aid, f"instance_conflict: {instance_id}")
                gw.db.log_event(aid, "instance_conflict", instance_id)
                await ws.send_text(json.dumps({"v": 1, "type": "reject", "code": "instance_conflict"}))
                await ws.close(code=4009)
                return
            new_nvrs = reg.get("nvrs") or []
            old_nvrs = json.loads(agent.get("nvrs_json") or "[]")
            changes = detect_channel_changes(old_nvrs, new_nvrs)
            gw.db.mark_registered(aid, instance_id, str(reg.get("agent_version", "?")),
                                  new_nvrs)
            if changes:
                gw.quarantine_channels(aid, changes)
                gw.db.set_warning(aid, "kanal o'zgardi: " + "; ".join(changes[:3]))
                gw.db.log_event(aid, "channel_changed", "; ".join(changes))
            gw.live[aid] = ws
            gw.live_instance[aid] = instance_id
            cfg = gw.config_for(agent)
            await ws.send_text(json.dumps({
                "v": 1, "type": "registered", "agent_id": aid,
                "server_time": _utcnow(), "config": cfg,
            }, ensure_ascii=False))
            gw.db.log_event(aid, "registered", f"v={reg.get('agent_version')}")
            await gw.push_pending_commands(aid)

            while True:
                raw = await ws.receive_text()
                msg = json.loads(raw)
                mtype = msg.get("type")
                if mtype == "heartbeat":
                    await run_in_threadpool(gw.db.record_heartbeat, aid, msg)
                    await ws.send_text(json.dumps(
                        {"v": 1, "type": "heartbeat_ack", "server_time": _utcnow()}))
                    await gw.push_pending_commands(aid)
                elif mtype == "command_result":
                    await run_in_threadpool(gw.db.record_command_result,
                                            str(msg.get("id")), msg, aid)
                    gw.db.log_event(aid, "command_result",
                                    f"{msg.get('id')} ok={msg.get('ok')} {msg.get('detail', '')}")
                    rescanned = (msg.get("data") or {}).get("nvrs")
                    if rescanned:  # rescan ham kanal o'zgarishini ochib berishi mumkin
                        current = gw.db.agent_by_id(aid) or {}
                        diff = detect_channel_changes(
                            json.loads(current.get("nvrs_json") or "[]"), rescanned)
                        gw.db.mark_registered(aid, instance_id,
                                              str(current.get("agent_version") or "?"), rescanned)
                        if diff:
                            gw.quarantine_channels(aid, diff)
                            gw.db.set_warning(aid, "kanal o'zgardi: " + "; ".join(diff[:3]))
                            gw.db.log_event(aid, "channel_changed", "; ".join(diff))
                elif mtype == "error":
                    gw.db.log_event(aid, "agent_error",
                                    f"{msg.get('code')}: {msg.get('message', '')}")
                else:
                    gw.db.log_event(aid, "unknown_msg", str(mtype))
        except (WebSocketDisconnect, asyncio.TimeoutError, json.JSONDecodeError):
            pass
        finally:
            if agent and gw.live.get(agent["agent_id"]) is ws:
                gw.live.pop(agent["agent_id"], None)
                gw.live_instance.pop(agent["agent_id"], None)

    # ------------------------------------------------ rasm qabul qilish

    @router.post("/api/v1/agent/snapshot")
    async def snapshot(
        request: Request,
        authorization: str = Header(default=""),
        x_idempotency_key: str = Header(default=""),
        x_channel: str = Header(default="0"),
        x_nvr_serial: str = Header(default=""),
        x_nvr_time: str = Header(default=""),
        x_agent_time: str = Header(default=""),
        x_server_time_est: str = Header(default=""),
        x_late: str = Header(default="0"),
        x_trigger: str = Header(default=""),
        x_sha256: str = Header(default=""),
        x_instance_id: str = Header(default=""),
        content_length: str = Header(default=""),
    ):
        # E'lon qilingan hajm chegaradan katta bo'lsa — TANANI O'QIMASDAN rad
        # etamiz (audit topilmasi: `await request.body()` avval butun tanani
        # xotiraga yig'adi, keyin hajmni tekshiradi — ya'ni 1 GB e'lon qilib
        # xotirani to'ldirish mumkin edi).
        if content_length.isdigit() and int(content_length) > MAX_SNAPSHOT_MB * 1_048_576:
            return JSONResponse({"v": 1, "ok": False, "error": "too_large"},
                                status_code=413)
        # DIQQAT: baza so'rovlari va diskka yozish BLOKLOVCHI. Ular to'g'ridan
        # -to'g'ri `async` ichida bajarilsa butun hodisa tsikli to'xtaydi va
        # WebSocket heartbeat'lar ham navbatga tushadi. O'lchangan: 100 agentda
        # kechikish 100 barobar oshardi, o'tkazuvchanlik esa o'zgarmasdi.
        token = authorization.removeprefix("Bearer ").strip()
        agent = await run_in_threadpool(gw.db.agent_by_token, token)
        if not agent:
            return JSONResponse({"v": 1, "ok": False, "error": "bad_token"}, status_code=401)

        # Instance ko'rinishi (audit topilmasi): klon faqat rasm yuklab, WS
        # ochmasa, "instance_conflict" ogohlantirishi chiqmasdi. Endi yuklash
        # yo'lida ham mos kelmagan instance BELGILANADI — operator ko'radi.
        # Rad etilmaydi (dalil yo'qolmasin), lekin ogohlantirish qo'yiladi.
        saqlangan = (agent.get("instance_id") or "").strip()
        if x_instance_id and saqlangan and x_instance_id != saqlangan:
            gw.db.set_warning(agent["agent_id"],
                              f"boshqa instance rasm yuklayapti: {x_instance_id[:40]}")
            gw.db.log_event(agent["agent_id"], "instance_conflict_upload",
                            x_instance_id[:60])
        if not x_idempotency_key:
            return JSONResponse({"v": 1, "ok": False, "error": "no_key"}, status_code=400)

        # Kalit AYNI agentga tegishli bo'lishi shart. Aks holda bir obyekt
        # boshqasining kalitini yuborib, uning dalilini "dublikat" qilib
        # bostirib qo'yishi mumkin — agent esa yagona nusxasini o'chiradi.
        prefix = (agent.get("key_prefix") or "").strip()
        if prefix and not x_idempotency_key.startswith(f"{prefix}:"):
            gw.db.log_event(agent["agent_id"], "key_prefix_mismatch",
                            x_idempotency_key[:120])
            return JSONResponse({"v": 1, "ok": False, "error": "key_prefix_mismatch"},
                                status_code=400)

        # Kanal agentning ro'yxatdan o'tgan kanallari ichida bo'lsin.
        if not x_channel.isdigit():
            return JSONResponse({"v": 1, "ok": False, "error": "bad_channel"},
                                status_code=400)
        channel = int(x_channel)
        known = {int(c.get("id", 0))
                 for nvr in json.loads(agent.get("nvrs_json") or "[]")
                 for c in (nvr.get("channels") or [])}
        if known and channel not in known:
            gw.db.log_event(agent["agent_id"], "unknown_channel", str(channel))
            return JSONResponse({"v": 1, "ok": False, "error": "unknown_channel"},
                                status_code=400)

        body = await request.body()
        if not body:
            return JSONResponse({"v": 1, "ok": False, "error": "empty"}, status_code=400)
        if len(body) > MAX_SNAPSHOT_MB * 1_048_576:
            return JSONResponse({"v": 1, "ok": False, "error": "too_large"},
                                status_code=413)
        if body[:2] != b"\xff\xd8":
            return JSONResponse({"v": 1, "ok": False, "error": "not_jpeg"},
                                status_code=400)

        # SHA-256 MAJBURIY: rasm dalil, butunligi tekshirilmasdan qabul
        # qilinmaydi. Ilgari sarlavha bo'lmasa tekshiruv o'tkazib yuborilardi.
        digest = hashlib.sha256(body).hexdigest()
        if not x_sha256:
            return JSONResponse({"v": 1, "ok": False, "error": "sha256_required"},
                                status_code=400)
        if digest != x_sha256.lower():
            return JSONResponse({"v": 1, "ok": False, "error": "sha256_mismatch"}, status_code=400)
        if gw.db.snapshot_exists(x_idempotency_key):   # indeksli SELECT, ~0.03 ms
            return {"v": 1, "ok": True, "duplicate": True}

        # Soat farqi: agent vaqti bilan server vaqti ko'p farq qilsa, dalil
        # noto'g'ri vaqtga bog'langan bo'ladi. Belgilab qo'yamiz.
        skew = _clock_skew_s(x_agent_time)
        if skew is not None and skew > 300:
            gw.db.set_warning(agent["agent_id"],
                              f"kompyuter soati {int(skew)} soniya farq qilyapti")
            gw.db.log_event(agent["agent_id"], "clock_skew", f"{int(skew)} s")
        meta = {
            "channel": channel, "nvr_serial": x_nvr_serial,
            "nvr_time": x_nvr_time, "agent_time": x_agent_time,
            "server_time_est": x_server_time_est, "late": x_late == "1",
            "trigger": x_trigger, "sha256": digest,
            # Kamera boshqa portga ko'chirilgan bo'lsa rasm saqlanadi, lekin
            # tahlilga kirmaydi — noto'g'ri rastaga yozilib ketmasin.
            "quarantined": f"{x_nvr_serial}:{channel}" in gw.quarantined.get(
                agent["agent_id"], set()),
        }
        def _persist() -> None:
            ref = gw.storage.save_snapshot(x_idempotency_key, body, meta)
            gw.db.record_snapshot(x_idempotency_key, agent["agent_id"], ref,
                                  meta, len(body))

        await run_in_threadpool(_persist)
        return {"v": 1, "ok": True, "duplicate": False}

    # ------------------------------------------------ speedtest

    @router.post("/api/v1/agent/speedtest")
    async def speedtest(request: Request, authorization: str = Header(default="")):
        token = authorization.removeprefix("Bearer ").strip()
        if not gw.db.agent_by_token(token):
            return JSONResponse({"v": 1, "ok": False}, status_code=401)
        body = await request.body()
        if len(body) > MAX_SNAPSHOT_MB * 1_048_576:
            return JSONResponse({"v": 1, "ok": False, "error": "too_large"},
                                status_code=413)
        return {"v": 1, "ok": True, "received_bytes": len(body)}

    # ------------------------------------------------ admin panel (dev)

    def _fmt_ts(ts: float | None) -> str:
        if not ts:
            return "-"
        return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")

    # Ikkinchi himoya qatlami: biror maydon qochirilmay qolsa ham, brauzer
    # skriptni ishga tushirmaydi. `unsafe-inline` faqat uslub uchun.
    SECURITY_HEADERS = {
        "Content-Security-Policy":
            "default-src 'none'; img-src 'self'; style-src 'unsafe-inline'; "
            "form-action 'self'; base-uri 'none'; frame-ancestors 'none'",
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Referrer-Policy": "no-referrer",
        # HSTS: HTTPS ustida brauzer bu domenga faqat shifrlangan kanaldan
        # boradi (downgrade/MITM'ga qarshi). HTTP'da e'tiborsiz — zararsiz.
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    }

    def _secure(response: Response) -> Response:
        for name, value in SECURITY_HEADERS.items():
            response.headers[name] = value
        return response

    def _page(title: str, body: str, refresh_s: int = 0) -> str:
        """Sahifa qobig'i. Ranglar oshkora — brauzerning qorong'i rejimida ham o'qilsin."""
        refresh = f"<meta http-equiv='refresh' content='{refresh_s}'>" if refresh_s else ""
        return f"""<!doctype html><html lang="uz"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">{refresh}
<title>{html.escape(title)}</title><style>{_CSS}</style></head>
<body><div class="wrap">{body}</div></body></html>"""

    @router.get("/admin", response_class=HTMLResponse)
    async def admin_home(request: Request):
        if not check_admin(request):
            return deny()
        rows = []
        now = time.time()
        online_count = 0
        for a in gw.db.list_agents():
            hb = a.get("last_heartbeat")
            online = a["agent_id"] in gw.live
            red = (hb is None) or (now - hb > HEARTBEAT_RED_S)
            online_count += 1 if (online and not red) else 0
            cls = "ok" if (online and not red) else ("bad" if red else "warn")
            label = "onlayn" if online else "oflayn"
            if red and online:
                label = "heartbeat yo'q"
            hbj = json.loads(a.get("last_heartbeat_json") or "{}")
            warn = (f"<br><span class='bad'>{html.escape(a['warning'])}</span>"
                    if a.get("warning") else "")
            mbps = a.get("upload_mbps")
            rows.append(
                f"<tr><td><a href='/admin/agent/{a['agent_id']}'>{a['agent_id']}</a></td>"
                f"<td class='wrapcell'>{html.escape(a['market_name'])}{warn}</td>"
                f"<td class='{cls}'><span class='dot' style='background:currentColor'></span>"
                f"{label}</td>"
                f"<td>{_fmt_ts(hb)}</td><td>{_esc(hbj.get('queue_len'))}</td>"
                f"<td>{_esc(hbj.get('status'))}</td><td>{_esc(a.get('agent_version'))}</td>"
                f"<td>{_fmt_mbps(mbps)}</td></tr>")

        def code_schedule(c: dict) -> str:
            """Kodga biriktirilgan jadval — u KO'RINISHI shart.

            Ko'rinmasa operator kodni «standart jadval bilan» deb o'ylab
            obyektga jo'natardi va farqni faqat birinchi kun rasmlaridan
            bilib olardi."""
            try:
                cfg = json.loads(c.get("config_json") or "null")
            except json.JSONDecodeError:
                return "<span class='bad'>buzuq</span>"
            if not cfg or not cfg.get("schedule"):
                return "<span class='muted'>standart</span>"
            return html.escape(", ".join(cfg["schedule"]))

        codes = "".join(
            f"<tr><td><code>{_esc(c['code'])}</code></td><td>{html.escape(c['market_name'])}</td>"
            f"<td class='wrapcell'>{code_schedule(c)}</td>"
            f"<td class='{'muted' if c['used_by'] else 'ok'}'>"
            f"{'ishlatilgan' if c['used_by'] else 'bo`sh'}</td></tr>"
            for c in gw.db.list_codes())
        events = "".join(
            f"<tr><td>{_fmt_ts(e['ts'])}</td><td>{_esc(e['agent_id'])}</td>"
            f"<td>{_esc(e.get('actor'))}</td>"
            f"<td><code>{_esc(e['kind'])}</code></td>"
            f"<td class='wrapcell'>{html.escape(e['detail'] or '')}</td></tr>"
            for e in gw.db.list_events(30))

        total = len(gw.db.list_agents())

        # Saqlash muddati — OPERATOR KO'RADIGAN YAGONA joy. Busiz «eski
        # kadr qani?» savoliga javob faqat kodda va `.env` da qolardi.
        kun = retention_days()
        eng_eski = gw.db.oldest_snapshot_age_days(time.time())
        if kun <= 0:
            saqlash = "tozalash o'chiq — kadrlar cheksiz saqlanadi"
        elif eng_eski is None:
            saqlash = f"{kun} kun saqlanadi"
        else:
            saqlash = (f"{kun} kun saqlanadi &middot; eng eskisi "
                       f"{eng_eski:.0f} kunlik")

        body = f"""<h1>CamAgent gateway</h1>
<p class="hint">{online_count}/{total} agent onlayn &middot;
{gw.db.snapshot_count()} ta rasm qabul qilindi &middot;
{saqlash} &middot;
<a href="/admin/snapshots">rasmlar</a> &middot;
<a href="/admin/slots">slot to'liqligi</a> &middot;
sahifa 10 soniyada yangilanadi</p>

<h2>Agentlar</h2>
<div class="tablewrap"><table>
<tr><th>ID</th><th>Bozor</th><th>Holat</th><th>Oxirgi heartbeat (UTC)</th>
<th>Navbat</th><th>Status</th><th>Versiya</th><th>Upload Mbit/s</th></tr>
{''.join(rows) or "<tr><td colspan='8' class='empty'>hali agent ulanmagan</td></tr>"}
</table></div>

<h2>Aktivatsiya kodlari</h2>
<div class="tablewrap"><table>
<tr><th>Kod</th><th>Bozor</th><th>Jadval</th><th>Holati</th></tr>
{codes or "<tr><td colspan='4' class='empty'>kod yo`q</td></tr>"}
</table></div>
<div class="panel"><form method="post" action="/admin/codes">
Bozor nomi: <input name="market_name" required placeholder="Karmana bozori">
Prefiks: <input name="key_prefix" required placeholder="karmana-01">
<br>Kadr olish jadvali (ixtiyoriy):
<input name="times" size="52"
 placeholder="{', '.join(DEFAULT_CONFIG['schedule'])}">
<button>Kod yaratish</button>
<p class="hint">Jadval kiritilsa agent BIRINCHI ulanishidayoq shu vaqtlar
bilan ishlaydi — obyektdan qaytib panelga kirish shart emas. Bo'sh
qoldirilsa standart jadval qo'llanadi.</p></form></div>

<h2>Oxirgi hodisalar (audit)</h2>
<div class="tablewrap"><table>
<tr><th>Vaqt (UTC)</th><th>Agent</th><th>Kim</th><th>Turi</th><th>Tafsilot</th></tr>
{events or "<tr><td colspan='5' class='empty'>hodisa yo`q</td></tr>"}
</table></div>"""
        return remember_token(request, HTMLResponse(
            _page("CamAgent gateway", body, refresh_s=10)))

    @router.post("/admin/codes")
    async def admin_create_code(request: Request, market_name: str = Form(...),
                                key_prefix: str = Form(...),
                                times: str = Form(default="")):
        if not check_admin(request):
            return deny()
        config = None
        if times.strip():
            try:
                config = {"schedule": parse_schedule(times)}
            except ValueError as exc:
                return JSONResponse({"error": str(exc)}, status_code=400)
        code = gw.db.create_code(market_name, key_prefix, config=config)
        detail = f"{code} -> {market_name}"
        if config:
            detail += f" (jadval: {', '.join(config['schedule'])})"
        gw.db.log_event(None, "code_created", detail,
                        actor=f"panel@{request.client.host if request.client else '?'}")
        return RedirectResponse("/admin", status_code=303)

    @router.get("/admin/agent/{agent_id}", response_class=HTMLResponse)
    async def admin_agent(agent_id: str, request: Request):
        if not check_admin(request):
            return deny()
        a = gw.db.agent_by_id(agent_id)
        if not a:
            return HTMLResponse("agent topilmadi", status_code=404)
        nvr_list = json.loads(a.get("nvrs_json") or "[]")
        quarantined = sorted(gw.quarantined.get(agent_id, set()))
        quarantine_block = ""
        if quarantined:
            items = "".join(f"<li><code>{html.escape(k)}</code></li>" for k in quarantined)
            quarantine_block = f"""<div class="panel alert">
<b class="bad">Kanal o'zgarishi aniqlandi — bu kanallar tahlildan chiqarildi:</b>
<ul>{items}</ul>
<p>Kamera boshqa portga ulangan bo'lishi mumkin. Rasmlarni ko'zdan kechiring,
to'g'ri bo'lsa tasdiqlang.</p>
<form method="post" action="/admin/agent/{agent_id}/clear_quarantine">
<button>Tekshirdim, tahlilga qaytar</button></form></div>"""

        def command_row(c: dict) -> str:
            # `get_logs` javobi shu ustunda bo'ladi va kesib tashlanadi —
            # shuning uchun to'liq ko'rish uchun havola qo'shiladi.
            full = (f" <a href='/admin/command/{_esc(c['cmd_id'])}'>to`liq</a>"
                    if c["result_json"] else "")
            return (f"<tr><td><code>{_esc(c['cmd_id'])}</code></td>"
                    f"<td>{_esc(c['name'])}</td>"
                    f"<td class='wrapcell'>{html.escape(c['params_json'] or '')}</td>"
                    f"<td class='wrapcell'>"
                    f"{html.escape((c['result_json'] or '')[:200])}{full}</td></tr>")

        cmds = "".join(command_row(c) for c in gw.db.list_commands(agent_id))

        # Jonli ko'rish tarixi. CLAUDE.md 11-bo'lim: "Kim, qachon, qaysi
        # kamerani ochgani jurnalga yoziladi." Umumiy hodisalar ro'yxatida
        # 12 bozor aralashib ketadi — operator BITTA bozorni ochib ko'ra
        # olishi kerak, aks holda audit amalda ishlamaydi.
        def stream_row(v: dict) -> str:
            tugadi = _fmt_ts(v["ended_at"]) if v["ended_at"] else "<b>ochiq</b>"
            davomiylik = int(((v["ended_at"] or v["last_seen_at"])
                              - v["started_at"]) / 60)
            return (f"<tr><td>{_esc(v['channel'])}</td>"
                    f"<td>{_esc(v['actor'])}</td>"
                    f"<td>{_esc(v['mode'])}</td>"
                    f"<td>{_fmt_ts(v['started_at'])}</td>"
                    f"<td>{tugadi}</td><td>{davomiylik} daq</td>"
                    f"<td class='wrapcell'>{_esc(v['end_reason'])}</td></tr>")

        streams = "".join(stream_row(v)
                          for v in gw.db.list_stream_sessions(agent_id, limit=30))
        oylik = gw.db.stream_minutes_this_month(agent_id)
        buttons = "".join(
            f"<form class='inline' method='post' action='/admin/agent/{agent_id}/command'>"
            f"<input type='hidden' name='name' value='{n}'><button>{n}</button></form> "
            for n in sorted(ALLOWED_COMMANDS))
        online = agent_id in gw.live
        hbj = json.loads(a.get("last_heartbeat_json") or "{}")

        nvr_blocks = []
        for nvr in nvr_list:
            serial = str(nvr.get("serial") or "")
            chan_cells = []
            for c in nvr.get("channels") or []:
                flag = "karantin" if f"{serial}:{c.get('id')}" in quarantined else ""
                state = "yoqilgan" if c.get("enabled") else "o`chirilgan"
                # Jonli ko'rish faqat agent onlayn va kanal yoqilgan bo'lsa.
                # Karantindagi kanal ham ko'riladi — aynan uni tekshirish
                # uchun operator kameraga qaraydi.
                korish = ""
                if agent_id in gw.live and c.get("enabled"):
                    korish = (
                        f"<form class='inline' method='post' "
                        f"action='/admin/agent/{_esc(agent_id)}/stream/start'>"
                        f"<input type='hidden' name='channel' value='{_esc(c.get('id'))}'>"
                        f"<input type='hidden' name='nvr_serial' value='{_esc(serial)}'>"
                        f"<button>jonli ko'rish</button></form>")
                chan_cells.append(
                    f"<tr><td>{_esc(c.get('id'))}</td>"
                    f"<td>{html.escape(str(c.get('name') or '-'))}</td>"
                    f"<td><code>{html.escape(str(c.get('camera_ip') or '-'))}</code></td>"
                    f"<td class='{'ok' if c.get('enabled') else 'muted'}'>{state}</td>"
                    f"<td class='bad'>{flag}</td><td>{korish}</td></tr>")
            chan_rows = "".join(chan_cells)
            nvr_blocks.append(f"""<p class="hint">
<b>{html.escape(str(nvr.get('model') or '-'))}</b> &middot;
seriya <code>{html.escape(str(nvr.get('serial') or '-'))}</code> &middot;
proshivka <code>{html.escape(str(nvr.get('firmware') or '-'))}</code> &middot;
IP <code>{html.escape(str(nvr.get('ip') or '-'))}</code></p>
<div class="tablewrap"><table>
<tr><th>Kanal</th><th>Kamera nomi</th><th>Kamera IP</th><th>Holat</th><th></th>
<th>Video</th></tr>
{chan_rows or "<tr><td colspan='6' class='empty'>kanal yo`q</td></tr>"}
</table></div>""")

        # Jadval — eng ko'p o'zgartiriladigan sozlama, shuning uchun unga
        # alohida forma. JSON maydonига `{"config": {"schedule": [...]}}`
        # yozish operatorni sintaksis xatosi bilan yolg'iz qoldirardi va
        # xato jadval RASM OLINMASLIGI bilan tugardi (4-prinsip).
        cur_cfg = gw.config_for(a)
        cur_schedule = ", ".join(cur_cfg.get("schedule") or [])
        schedule_block = f"""<h3>Kadr olish jadvali</h3>
<div class="panel">
<form method="post" action="/admin/agent/{agent_id}/schedule">
<p>Vaqtlar vergul bilan, bozorning mahalliy vaqtida
(<code>{_esc(cur_cfg.get('timezone'))}</code>):</p>
<input name="times" size="70" value="{html.escape(cur_schedule)}">
<br><button>Jadvalni saqlash</button>
<p class="hint">Saqlangach agentga darhol yuboriladi. Agent oflayn bo'lsa —
keyingi ulanishida oladi (desired-state).</p>
</form></div>"""

        body = f"""<h1>{html.escape(a['market_name'])}</h1>
<p class="hint"><a href="/admin">&larr; barcha agentlar</a> &middot;
<code>{agent_id}</code> &middot;
<span class="{'ok' if online else 'bad'}">{'onlayn' if online else 'oflayn'}</span> &middot;
versiya {_esc(a.get('agent_version'))} &middot;
navbat {_esc(hbj.get('queue_len'))} &middot;
disk {_esc(hbj.get('disk_free_mb'))} MB</p>
{quarantine_block}

{schedule_block}

<h3>Buyruq yuborish</h3>
<div class="panel">{buttons}</div>
<div class="panel">
<form method="post" action="/admin/agent/{agent_id}/command">
<p>Parametrli buyruq — nomi va JSON params:</p>
<input name="name" value="update_config" size="24">
<br><textarea name="params" rows="4" cols="70"
 placeholder='{{"config": {{"schedule": ["05:00","17:00"], ...}}}}'></textarea>
<br><button>Yuborish</button></form></div>

<h3>Obyektni o'chirish</h3>
<div class="panel"><form method="post" action="/admin/agent/{agent_id}/delete">
<p>Kompyuter almashtirilgan bo'lsa, eski yozuvni olib tashlash mumkin.
<b>Rasmlar saqlanib qoladi</b> — ular dalil.</p>
<button>Ro'yxatdan olib tashlash</button></form></div>

<h3>Kameralar</h3>
<div class="panel"><p><a href="/admin/agent/{agent_id}/wall">
<b>Barcha kameralarni bir ekranda ko'rish</b></a> — Hik-Connect uslubidagi
to'r. Kerakli kamerani bosganda jonli videoga aylanadi.</p></div>

<h3>NVR'lar</h3>
{"".join(nvr_blocks) or "<p class='empty'>NVR ma`lumoti yo`q</p>"}

<h3>Jonli ko'rish tarixi (audit)</h3>
<p class="hint">Shu oyda: <b>{oylik:.0f}</b> daqiqa.
Kim, qachon, qaysi kamerani ochgani shu yerda qoladi.</p>
<div class="tablewrap"><table>
<tr><th>Kanal</th><th>Kim</th><th>Rejim</th><th>Boshlandi</th><th>Tugadi</th>
<th>Davomiylik</th><th>Sabab</th></tr>
{streams or "<tr><td colspan='7' class='empty'>hali hech kim ko`rmagan</td></tr>"}
</table></div>

<h3>Buyruqlar tarixi (audit)</h3>
<div class="tablewrap"><table>
<tr><th>ID</th><th>Nomi</th><th>Params</th><th>Natija</th></tr>
{cmds or "<tr><td colspan='4' class='empty'>buyruq yuborilmagan</td></tr>"}
</table></div>"""
        return remember_token(request, HTMLResponse(
            _page(f"{a['market_name']} — CamAgent", body, refresh_s=15)))

    @router.post("/admin/agent/{agent_id}/schedule")
    async def admin_set_schedule(agent_id: str, request: Request,
                                 times: str = Form(default="")):
        """Jadvalni ALOHIDA forma bilan o'zgartiradi (`update_config` ustida).

        ⛔ BO'SH JADVAL RAD ETILADI. U sintaktik jihatdan to'g'ri, lekin
           ma'nosi «bu obyektda umuman rasm olinmasin» — ya'ni bitta bo'sh
           maydon butun bozorni jimgina o'chirардi. Ataylab to'xtatish
           kerak bo'lsa agentning o'zi olib tashlanadi.

        ⚠ VAQTLAR TARTIBLANADI VA TAKRORI OLIB TASHLANADI: agent jadvalni
          shu ko'rinishda saqlaydi va panelda ko'rsatilgan matn bilan
          diskdagi qiymat bir xil bo'lishi kerak — aks holda operator
          «saqlanmadi shekilli» deb ikkinchi marta yuborardi.
        """
        if not check_admin(request):
            return deny()
        agent = gw.db.agent_by_id(agent_id)
        if not agent:
            return JSONResponse({"error": "agent topilmadi"}, status_code=404)

        try:
            schedule = parse_schedule(times)
        except ValueError as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

        cfg = gw.config_for(agent)
        cfg["schedule"] = schedule
        gw.set_config(agent_id, cfg)
        cmd_id = gw.db.queue_command(agent_id, "update_config", {"config": cfg})
        gw.db.log_event(agent_id, "schedule_changed", f"{', '.join(schedule)} ({cmd_id})",
                        actor=f"panel@{request.client.host if request.client else '?'}")
        await gw.push_pending_commands(agent_id)
        return RedirectResponse(f"/admin/agent/{agent_id}", status_code=303)

    @router.post("/admin/agent/{agent_id}/command")
    async def admin_command(agent_id: str, request: Request, name: str = Form(...),
                            params: str = Form(default="")):
        if not check_admin(request):
            return deny()
        if name not in ALLOWED_COMMANDS:
            return JSONResponse({"error": "buyruq oq ro'yxatda yo'q"}, status_code=400)
        try:
            p = json.loads(params) if params.strip() else {}
        except json.JSONDecodeError:
            return JSONResponse({"error": "params JSON emas"}, status_code=400)
        # Sozlamani o'zgartiradigan buyruqlar server tomonda ham SAQLANADI.
        # Busiz agent qayta ulanganda server eski sozlamani qaytarib yuboradi
        # va operator kiritgan o'zgarish jimgina yo'qoladi.
        if name == "update_config" and isinstance(p.get("config"), dict):
            gw.set_config(agent_id, p["config"])
        elif name in ("enable_channel", "disable_channel"):
            serial, channel = p.get("nvr_serial"), p.get("channel")
            if serial and str(channel).isdigit():
                agent = gw.db.agent_by_id(agent_id)
                cfg = gw.config_for(agent) if agent else None
                if cfg is not None:
                    disabled = list(cfg.get("channels_disabled") or [])
                    key = f"{serial}:{channel}"
                    if name == "disable_channel" and key not in disabled:
                        disabled.append(key)
                    if name == "enable_channel" and key in disabled:
                        disabled.remove(key)
                    cfg["channels_disabled"] = disabled
                    gw.set_config(agent_id, cfg)

        cmd_id = gw.db.queue_command(agent_id, name, p)
        # CLAUDE.md 6-bo'lim: kim, qachon, qaysi bozor. Dev panelda bitta
        # umumiy kalit bor, shuning uchun IP yoziladi; sbozor'da bu yerga
        # haqiqiy foydalanuvchi nomi tushadi.
        actor = f"panel@{request.client.host if request.client else '?'}"
        gw.db.log_event(agent_id, "command_queued", f"{name} ({cmd_id})", actor=actor)
        await gw.push_pending_commands(agent_id)
        return RedirectResponse(f"/admin/agent/{agent_id}", status_code=303)

    @router.post("/admin/agent/{agent_id}/clear_quarantine")
    async def admin_clear_quarantine(agent_id: str, request: Request):
        if not check_admin(request):
            return deny()
        gw.quarantined.pop(agent_id, None)
        gw.db.clear_quarantine(agent_id)
        gw.db.set_warning(agent_id, None)
        gw.db.log_event(agent_id, "quarantine_cleared", "operator tasdiqladi",
                        actor=f"panel@{request.client.host if request.client else '?'}")
        return RedirectResponse(f"/admin/agent/{agent_id}", status_code=303)

    @router.get("/admin/command/{cmd_id}", response_class=HTMLResponse)
    async def admin_command_result(cmd_id: str, request: Request):
        """Buyruq natijasini TO'LIQ ko'rsatadi.

        Jadvalda 300 belgi bilan kesiladi — `get_logs` javobi esa aynan
        shu yerda bo'ladi, ya'ni masofaviy diagnostika vositasi ishlamas edi.
        """
        if not check_admin(request):
            return deny()
        cmd = gw.db.command_by_id(cmd_id)
        if not cmd:
            return _secure(HTMLResponse(_page("Topilmadi", "<h1>Buyruq topilmadi</h1>"),
                                        status_code=404))
        try:
            result = json.loads(cmd["result_json"] or "{}")
        except json.JSONDecodeError:
            result = {"xom": cmd["result_json"]}
        log_text = (result.get("data") or {}).pop("log", "")
        body = f"""<h1>{_esc(cmd['name'])}</h1>
<p class="hint"><a href="/admin/agent/{_esc(cmd['agent_id'])}">&larr; agentga qaytish</a>
 &middot; <code>{_esc(cmd_id)}</code></p>
<h3>Natija</h3>
<pre>{html.escape(json.dumps(result, ensure_ascii=False, indent=1))}</pre>
{f'<h3>Jurnal</h3><pre>{html.escape(log_text)}</pre>' if log_text else ''}"""
        return remember_token(request, HTMLResponse(_page("Buyruq natijasi", body)))

    @router.post("/admin/agent/{agent_id}/delete")
    async def admin_delete_agent(agent_id: str, request: Request):
        """Obyektni ro'yxatdan olib tashlaydi (kompyuter almashtirilganda).

        Rasmlar saqlanib qoladi — ular dalil.
        """
        if not check_admin(request):
            return deny()
        actor = f"panel@{request.client.host if request.client else '?'}"
        gw.live.pop(agent_id, None)
        gw.configs.pop(agent_id, None)
        gw.quarantined.pop(agent_id, None)
        gw.db.delete_agent(agent_id)
        gw.db.log_event(None, "agent_deleted", agent_id, actor=actor)
        return RedirectResponse("/admin", status_code=303)

    @router.get("/admin/slots", response_class=HTMLResponse)
    async def admin_slots(request: Request):
        """Slot to'liqligi: nechta kadr kutilgan, nechtasi kelgan."""
        if not check_admin(request):
            return deny()
        rows = []
        incomplete = 0
        for r in gw.db.slot_completeness():
            cls = "ok" if r["missing"] == 0 else "bad"
            incomplete += 1 if r["missing"] else 0
            rows.append(
                f"<tr><td>{_esc(r['market_name'])}</td><td>{_esc(r['slot'])}</td>"
                f"<td class='{cls}'>{r['got']} / {r['expected']}</td>"
                f"<td class='bad'>{r['missing'] or ''}</td>"
                f"<td>{_fmt_ts(r['last_at'])}</td></tr>")
        body = f"""<h1>Slot to'liqligi</h1>
<p class="hint"><a href="/admin">&larr; ortga</a> &middot; oxirgi 24 soat &middot;
{incomplete} ta slot to'liq kelmagan</p>
<p class="hint">"Rasm yo'q" va "rasmda rasta bo'sh" — boshqa-boshqa narsa.
Bu jadval yo'qolgan kadrlarni ko'rsatadi.</p>
<div class="tablewrap"><table>
<tr><th>Bozor</th><th>Slot (UTC)</th><th>Kelgan / kutilgan</th><th>Yetmadi</th>
<th>Oxirgi kadr</th></tr>
{''.join(rows) or "<tr><td colspan='5' class='empty'>ma`lumot yo`q</td></tr>"}
</table></div>"""
        return remember_token(request, HTMLResponse(_page("Slot to'liqligi", body,
                                                          refresh_s=30)))

    @router.get("/admin/snapshots", response_class=HTMLResponse)
    async def admin_snapshots(request: Request):
        if not check_admin(request):
            return deny()
        snaps = gw.db.list_snapshots()
        thumbs = "".join(
            f"""<div class="thumb">
<a href="/admin/snapshot_img?ref={s['storage_ref']}" target="_blank">
<img src="/admin/snapshot_img?ref={s['storage_ref']}" alt="kanal {s['channel']}" loading="lazy">
</a><div class="cap">kanal {s['channel']} &middot; {_fmt_ts(s['received_at'])[11:]}
{" &middot; <span class='warn'>kech</span>" if s['late'] else ""}
{" &middot; <span class='bad'>karantin</span>" if s['quarantined'] else ""}
</div></div>""" for s in snaps[:24])

        rows = "".join(
            f"<tr><td>{_fmt_ts(s['received_at'])}</td><td>{s['agent_id']}</td>"
            f"<td>{_esc(s['channel'])}</td>"
            f"<td class='warn'>{'kech' if s['late'] else ''}</td>"
            f"<td class='bad'>{'karantin' if s['quarantined'] else ''}</td>"
            f"<td>{_esc(s['trigger'])}</td><td>{(s['size_bytes'] or 0) // 1024} KB</td>"
            f"<td class='wrapcell'><code>{html.escape(s['idem_key'])}</code></td></tr>"
            for s in snaps)

        body = f"""<h1>Rasmlar</h1>
<p class="hint"><a href="/admin">&larr; ortga</a> &middot; jami {len(snaps)} ta</p>
<p class="hint"><b>kech</b> — jadval vaqtidan keyin olingan kadr; server uni
5 ta ovoz sxemasiga teng huquqli qo'shmasin.
<b>karantin</b> — kanal identligi o'zgargan, tahlildan chiqarilgan.</p>
<div class="grid">{thumbs or "<p class='empty'>rasm yo`q</p>"}</div>
<h2>Ro'yxat</h2>
<div class="tablewrap"><table>
<tr><th>Kelgan vaqt (UTC)</th><th>Agent</th><th>Kanal</th><th>Kech</th><th>Karantin</th>
<th>Trigger</th><th>Hajm</th><th>Idempotency kaliti</th></tr>
{rows or "<tr><td colspan='8' class='empty'>rasm yo`q</td></tr>"}
</table></div>"""
        return remember_token(request, HTMLResponse(
            _page("Rasmlar — CamAgent", body, refresh_s=20)))

    @router.get("/admin/snapshot_img")
    async def admin_snapshot_img(ref: str, request: Request):
        if not check_admin(request):
            return deny()
        try:
            # S3 rejimida bu tarmoq chaqirig'i — event loop'ni bloklamasin
            # (snapshot qabulidagi run_in_threadpool bilan bir xil qoida).
            jpeg = await run_in_threadpool(gw.storage.open_snapshot, ref)
            return _secure(Response(jpeg, media_type="image/jpeg"))
        except Exception:
            return JSONResponse({"error": "topilmadi"}, status_code=404)

    # Jonli video marshrutlari alohida modulda: `app.py` allaqachon katta
    # va sbozor video qismini butunlay o'chirib tashlashi mumkin.
    video_routes.attach(router, gw, check_admin=check_admin, deny=deny,
                        page=_page, secure=_secure, esc=_esc, media=gw.media)
    return router


def build_app(data_dir: str | Path, storage: SnapshotStorage | None = None,
              admin_token: str | None = None) -> FastAPI:
    app = FastAPI(title="CamAgent gateway")
    router = build_router(data_dir, storage, admin_token)
    app.include_router(router)
    app.state.gateway = router.gateway

    # Docker healthcheck nishoni. ATAYIN build_app'da, build_router'da emas:
    # router sbozor kabi tashqi app'ga ulanganda u yerda o'zining /healthz
    # yo'li bo'ladi va ikkita bir xil yo'l chalkashlik tug'dirardi.
    @app.get("/healthz", include_in_schema=False)
    def healthz() -> dict:
        return {"status": "ok"}

    # --- tozalash (retention) ---
    #
    # ⚠ FON VAZIFASI `build_app`DA, `build_router`DA EMAS — `/healthz`
    #   bilan bir xil sabab: router sbozor'ning o'z app'iga ulanganda
    #   tozalashni O'SHA loyiha o'zi rejalashtiradi (uning `taskiq`
    #   ishchisi bor) va ikkita jadval bir vaqtda yugurmasin.
    #
    # ⛔ INTERVAL SOATLARDA, cron'da EMAS: gateway qayta ishga tushishi
    #   mumkin va cron'ga bog'langan tozalash o'sha kuni umuman
    #   o'tkazib yuborilardi. Har 6 soatda bir yugurish partiyani
    #   (500 kadr) kunlik oqimdan tez tozalaydi.
    @app.on_event("startup")
    async def _tozalash_boshlansin() -> None:
        if retention_days() <= 0:
            log.info("tozalash o'chirilgan — fon vazifasi ishga tushirilmadi")
            return
        app.state.retention_task = asyncio.create_task(
            _tozalash_halqasi(router.gateway))

    @app.on_event("shutdown")
    async def _tozalash_toxtasin() -> None:
        task = getattr(app.state, "retention_task", None)
        if task is not None:
            task.cancel()

    return app


RETENTION_INTERVAL_S = 6 * 3600
"""Ikki yugurish orasi. Kunlik oqim (12 bozor ~1400 kadr) partiyaga
(500) sig'maydi, shuning uchun kuniga to'rt marta yuguriladi."""

RETENTION_FIRST_DELAY_S = 120
"""Ishga tushgach birinchi yugurishgacha. Kechikish ATAYIN: gateway
ko'tarilgan zahoti agentlar ulanadi va navbatdagi kadrlarni yuboradi —
tozalash o'sha eng band daqiqada disk bilan raqobatlashmasin."""


async def _tozalash_halqasi(gw: Gateway) -> None:
    """Muddati o'tgan kadrlarni davriy o'chiradi.

    ⛔ HALQA HECH QACHON O'LMAYDI: har xato ushlanadi va keyingi
       intervalda qayta uriniladi. Tozalash to'xtasa disk jimgina
       to'lardi va buni faqat server yiqilgan kuni bilardik.
    """
    await asyncio.sleep(RETENTION_FIRST_DELAY_S)
    while True:
        try:
            natija = await run_in_threadpool(retention_sweep, gw.db, gw.storage)
            if natija.deleted:
                gw.db.log_event(None, "retention_sweep",
                                f"{natija.deleted} kadr, "
                                f"{natija.freed_bytes // 1048576} MB")
        except asyncio.CancelledError:
            raise
        except Exception:                             # noqa: BLE001
            log.exception("tozalash halqasida xato")
        await asyncio.sleep(RETENTION_INTERVAL_S)
