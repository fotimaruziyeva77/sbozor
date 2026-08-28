"""Gateway registri — SQLite (dev/reference).

sbozor'da bu jadvallar PostgreSQL'ga ko'chadi; interfeys (funksiya imzolari)
o'zgarmaydi. Bitta yozuvchi oqim + qulf — dev yuki uchun yetarli.
"""
from __future__ import annotations

import json
import secrets
import sqlite3
import threading
import time
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS activation_codes(
  code TEXT PRIMARY KEY,
  market_name TEXT NOT NULL,
  key_prefix TEXT NOT NULL,
  used_by TEXT,
  created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS agents(
  agent_id TEXT PRIMARY KEY,
  token TEXT UNIQUE NOT NULL,
  instance_id TEXT,
  market_name TEXT NOT NULL,
  key_prefix TEXT NOT NULL,
  agent_version TEXT,
  nvrs_json TEXT,
  registered_at REAL,
  last_heartbeat REAL,
  last_heartbeat_json TEXT,
  upload_mbps REAL,
  warning TEXT,
  config_json TEXT
);
CREATE TABLE IF NOT EXISTS quarantine(
  agent_id TEXT NOT NULL,
  channel_key TEXT NOT NULL,
  reason TEXT,
  created_at REAL NOT NULL,
  PRIMARY KEY (agent_id, channel_key)
);
CREATE TABLE IF NOT EXISTS stream_sessions(
  session_id TEXT PRIMARY KEY,
  agent_id TEXT NOT NULL,
  channel INTEGER NOT NULL,
  nvr_serial TEXT DEFAULT '',
  actor TEXT,
  started_at REAL NOT NULL,
  last_seen_at REAL NOT NULL,
  ended_at REAL,
  end_reason TEXT,
  mode TEXT,
  bytes_est INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_stream_agent ON stream_sessions(agent_id, started_at);
CREATE INDEX IF NOT EXISTS idx_stream_open ON stream_sessions(ended_at, last_seen_at);
CREATE TABLE IF NOT EXISTS snapshots(
  idem_key TEXT PRIMARY KEY,
  agent_id TEXT NOT NULL,
  channel INTEGER,
  nvr_serial TEXT,
  storage_ref TEXT NOT NULL,
  sha256 TEXT,
  late INTEGER DEFAULT 0,
  quarantined INTEGER DEFAULT 0,
  trigger TEXT,
  nvr_time TEXT,
  agent_time TEXT,
  server_time_est TEXT,
  received_at REAL NOT NULL,
  size_bytes INTEGER
);
CREATE TABLE IF NOT EXISTS commands(
  cmd_id TEXT PRIMARY KEY,
  agent_id TEXT NOT NULL,
  name TEXT NOT NULL,
  params_json TEXT,
  created_at REAL NOT NULL,
  sent_at REAL,
  result_json TEXT
);
CREATE INDEX IF NOT EXISTS idx_snap_received ON snapshots(received_at);
CREATE INDEX IF NOT EXISTS idx_snap_agent ON snapshots(agent_id, received_at);
CREATE INDEX IF NOT EXISTS idx_cmd_agent ON commands(agent_id, created_at);
CREATE TABLE IF NOT EXISTS events(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  agent_id TEXT,
  ts REAL NOT NULL,
  kind TEXT NOT NULL,
  detail TEXT,
  actor TEXT
);
CREATE INDEX IF NOT EXISTS idx_events_agent ON events(agent_id, ts);
"""


class GatewayDB:
    def __init__(self, path: Path | str):
        # Satr ham qabul qilinadi: `docker exec ... GatewayDB('/data/...')`
        # ko'rinishidagi operatsion buyruqlar Path importisiz ishlasin.
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._db = sqlite3.connect(str(path), check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        # WAL: o'qish yozishni bloklamaydi — panel ochiq turganda rasm qabul
        # qilish sekinlashmasin.
        # synchronous=NORMAL: standart FULL har INSERT'da diskni fsync qiladi
        # va bitta rasm yozuvi 15 ms oladi (o'lchangan) — soatiga 480 ta rasm
        # kelganda bu sezilarli. NORMAL'da elektr uchsa oxirgi bir necha
        # tranzaksiya yo'qolishi mumkin, LEKIN baza buzilmaydi va rasm
        # fayllari yonidagi .json sidecar'dan yozuvni tiklab bo'ladi
        # (storage.py). Ya'ni dalil yo'qolmaydi — faqat indeks tiklanadi.
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.execute("PRAGMA synchronous=NORMAL")
        with self._lock:
            self._db.executescript(_SCHEMA)
            self._migrate()
            self._db.commit()

    def _migrate(self) -> None:
        """Mavjud bazaga yangi ustunlarni qo'shadi.

        `CREATE TABLE IF NOT EXISTS` allaqachon mavjud jadvalga ustun
        QO'SHMAYDI. Shuning uchun server yangilanganda eski baza yangi kod
        bilan mos kelmay qoladi va so'rovlar "no such column" bilan yiqiladi.
        Har yangi ustun shu ro'yxatga qo'shilishi shart.
        """
        added = [
            ("agents", "config_json", "TEXT"),
            ("snapshots", "quarantined", "INTEGER DEFAULT 0"),
            ("events", "actor", "TEXT"),
            # Kod bilan birga beriladigan jadval: agent BIRINCHI ulanishidayoq
            # to'g'ri vaqtlar bilan ishlaydi. Busiz obyektga borgan odam
            # standart jadval bilan qaytardi va uni keyin paneldan
            # to'g'rilash ESDAN CHIQARDI — birinchi kunlar rasmi noto'g'ri
            # vaqtda olinardi va buni faqat hisobotda sezardik.
            ("activation_codes", "config_json", "TEXT"),
            # Ijara uzaytirilganda `start_stream` QAYSI NVR'ga tegishli
            # ekanini bilish kerak: ikki NVR'li obyektda serialsiz buyruq
            # birinchi NVR'ga tushib, noto'g'ri kamerani ochardi.
            ("stream_sessions", "nvr_serial", "TEXT DEFAULT ''"),
        ]
        for table, column, decl in added:
            try:
                existing = {r[1] for r in self._db.execute(f"PRAGMA table_info({table})")}
            except sqlite3.DatabaseError:
                continue
            if existing and column not in existing:
                self._db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {decl}")

    def _exec(self, sql: str, args: tuple = ()):
        with self._lock:
            cur = self._db.execute(sql, args)
            self._db.commit()
            return cur

    def _rows(self, sql: str, args: tuple = ()) -> list[sqlite3.Row]:
        with self._lock:
            return self._db.execute(sql, args).fetchall()

    # --- aktivatsiya kodlari ---

    def create_code(self, market_name: str, key_prefix: str, code: str | None = None,
                    config: dict | None = None) -> str:
        """Aktivatsiya kodi; `config` berilsa agent uni BIRINCHI ulanishda oladi.

        `config` — TO'LIQ konfiguratsiya emas, faqat ustiga yoziladigan
        maydonlar (odatda `schedule`). Qolgani `DEFAULT_CONFIG` dan keladi,
        ya'ni bu yerga yozilgan yarim konfiguratsiya agentni nosoz holatga
        tushira olmaydi.
        """
        # 3 bayt = 24 bit edi: prefiks bozor nomi (ochiq), qolgani 16.7 mln
        # variant — tezlik limitisiz bir soatda topib bo'lardi. Endi 128 bit.
        code = code or f"{key_prefix.upper()[:12]}-{secrets.token_urlsafe(16)}"
        self._exec(
            "INSERT INTO activation_codes(code, market_name, key_prefix, created_at,"
            " config_json) VALUES(?,?,?,?,?)",
            (code, market_name, key_prefix, time.time(),
             json.dumps(config, ensure_ascii=False) if config else None),
        )
        return code

    def set_code_config(self, code: str, config: dict | None) -> bool:
        """Ishlatilmagan kodga jadval biriktiradi (yoki olib tashlaydi).

        ⛔ ISHLATILGAN KODGA TEGMAYDI: agent allaqachon yaratilgan bo'lsa
           konfiguratsiya `agents.config_json` da yashaydi va bu yerdagi
           o'zgarish JIMGINA E'TIBORSIZ qolardi — operator esa jadvalni
           o'zgartirdim deb o'ylardi.
        """
        rows = self._rows("SELECT used_by FROM activation_codes WHERE code=?", (code,))
        if not rows or rows[0]["used_by"]:
            return False
        self._exec(
            "UPDATE activation_codes SET config_json=? WHERE code=?",
            (json.dumps(config, ensure_ascii=False) if config else None, code),
        )
        return True

    def use_code(self, code: str, instance_id: str) -> dict | None:
        rows = self._rows("SELECT * FROM activation_codes WHERE code=?", (code,))
        if not rows:
            return None
        row = rows[0]
        if row["used_by"] and row["used_by"] != instance_id:
            return {"used": True}
        self._exec("UPDATE activation_codes SET used_by=? WHERE code=?", (instance_id, code))
        config = None
        raw = row["config_json"] if "config_json" in row.keys() else None
        if raw:
            try:
                config = json.loads(raw)
            except json.JSONDecodeError:
                config = None
        return {"used": False, "market_name": row["market_name"],
                "key_prefix": row["key_prefix"], "config": config}

    def list_codes(self) -> list[dict]:
        return [dict(r) for r in self._rows("SELECT * FROM activation_codes ORDER BY created_at DESC")]

    # --- agentlar ---

    def create_agent(self, market_name: str, key_prefix: str, instance_id: str) -> dict:
        agent_id = "a-" + secrets.token_hex(4)
        token = "at_" + secrets.token_urlsafe(24)
        self._exec(
            "INSERT INTO agents(agent_id, token, instance_id, market_name, key_prefix) VALUES(?,?,?,?,?)",
            (agent_id, token, instance_id, market_name, key_prefix),
        )
        return {"agent_id": agent_id, "token": token, "key_prefix": key_prefix}

    def agent_by_token(self, token: str) -> dict | None:
        rows = self._rows("SELECT * FROM agents WHERE token=?", (token,))
        return dict(rows[0]) if rows else None

    def agent_by_id(self, agent_id: str) -> dict | None:
        rows = self._rows("SELECT * FROM agents WHERE agent_id=?", (agent_id,))
        return dict(rows[0]) if rows else None

    def find_agent_for_code_reuse(self, instance_id: str, key_prefix: str) -> dict | None:
        """Ayni kompyuter ayni obyekt kodi bilan qayta aktivatsiya qilyaptimi.

        `key_prefix` shart: aks holda bir bozorning kodi bilan boshqa
        bozorning agent tokenini olish mumkin edi — `instance_id` esa
        `--status` da chop etiladi va har aktivatsiyada yuboriladi.
        """
        rows = self._rows(
            "SELECT * FROM agents WHERE instance_id=? AND key_prefix=?",
            (instance_id, key_prefix))
        return dict(rows[0]) if rows else None

    def mark_registered(self, agent_id: str, instance_id: str, version: str, nvrs: list) -> None:
        self._exec(
            "UPDATE agents SET instance_id=?, agent_version=?, nvrs_json=?, registered_at=?, warning=NULL WHERE agent_id=?",
            (instance_id, version, json.dumps(nvrs, ensure_ascii=False), time.time(), agent_id),
        )

    def set_warning(self, agent_id: str, warning: str) -> None:
        self._exec("UPDATE agents SET warning=? WHERE agent_id=?", (warning, agent_id))

    def record_heartbeat(self, agent_id: str, hb: dict) -> None:
        self._exec(
            "UPDATE agents SET last_heartbeat=?, last_heartbeat_json=?, upload_mbps=COALESCE(?, upload_mbps) WHERE agent_id=?",
            (time.time(), json.dumps(hb, ensure_ascii=False), hb.get("upload_mbps"), agent_id),
        )

    def list_agents(self) -> list[dict]:
        return [dict(r) for r in self._rows("SELECT * FROM agents ORDER BY market_name")]

    # --- konfiguratsiya (xotirada emas, bazada) ---

    def save_config(self, agent_id: str, config: dict) -> None:
        """Operator o'zgartirgan sozlama saqlanishi SHART.

        Aks holda agent qayta ulanganda server eski sozlamani qaytarib
        yuboradi va o'zgarish jimgina yo'qoladi; server qayta ishga
        tushganda esa barcha obyektlar standart sozlamaga qaytadi.
        """
        self._exec("UPDATE agents SET config_json=? WHERE agent_id=?",
                   (json.dumps(config, ensure_ascii=False), agent_id))

    def load_config(self, agent_id: str) -> dict | None:
        rows = self._rows("SELECT config_json FROM agents WHERE agent_id=?", (agent_id,))
        if not rows or not rows[0]["config_json"]:
            return None
        try:
            return json.loads(rows[0]["config_json"])
        except json.JSONDecodeError:
            return None

    # --- karantin (server qayta yuklanganda yo'qolmasin) ---

    def add_quarantine(self, agent_id: str, channel_keys: list[str], reason: str) -> None:
        for key in channel_keys:
            self._exec(
                "INSERT OR IGNORE INTO quarantine(agent_id, channel_key, reason, created_at)"
                " VALUES(?,?,?,?)", (agent_id, key, reason[:300], time.time()))

    def list_quarantine(self, agent_id: str) -> set[str]:
        return {r["channel_key"] for r in self._rows(
            "SELECT channel_key FROM quarantine WHERE agent_id=?", (agent_id,))}

    def clear_quarantine(self, agent_id: str) -> None:
        self._exec("DELETE FROM quarantine WHERE agent_id=?", (agent_id,))

    def all_quarantine(self) -> dict[str, set[str]]:
        out: dict[str, set[str]] = {}
        for r in self._rows("SELECT agent_id, channel_key FROM quarantine"):
            out.setdefault(r["agent_id"], set()).add(r["channel_key"])
        return out

    # --- rasmlar ---

    def snapshot_exists(self, idem_key: str) -> bool:
        return bool(self._rows("SELECT 1 FROM snapshots WHERE idem_key=?", (idem_key,)))

    def record_snapshot(self, idem_key: str, agent_id: str, storage_ref: str, meta: dict, size: int) -> None:
        self._exec(
            "INSERT OR IGNORE INTO snapshots(idem_key, agent_id, channel, nvr_serial, storage_ref, sha256,"
            " late, quarantined, trigger, nvr_time, agent_time, server_time_est, received_at, size_bytes)"
            " VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                idem_key, agent_id, meta.get("channel"), meta.get("nvr_serial"), storage_ref,
                meta.get("sha256"), 1 if meta.get("late") else 0,
                1 if meta.get("quarantined") else 0, meta.get("trigger"),
                meta.get("nvr_time"), meta.get("agent_time"), meta.get("server_time_est"),
                time.time(), size,
            ),
        )

    def list_snapshots(self, limit: int = 200) -> list[dict]:
        return [dict(r) for r in self._rows(
            "SELECT * FROM snapshots ORDER BY received_at DESC LIMIT ?", (limit,))]

    def snapshot_count(self) -> int:
        return self._rows("SELECT COUNT(*) AS n FROM snapshots")[0]["n"]

    # --- tozalash (retention) ---

    def snapshots_older_than(self, cutoff: float, limit: int) -> list[dict]:
        """Saqlash muddati o'tgan kadrlar — ENG ESKISIDAN boshlab.

        Args:
            cutoff: `received_at` shu qiymatdan KICHIK bo'lganlar.
            limit: bir partiyada nechta. Partiya kerak: 12 bozorda bir
                yillik to'planma o'n minglab qator bo'ladi va ularni
                bitta tranzaksiyada o'chirish bazani bloklab qo'yardi.

        Returns:
            `idem_key` va `storage_ref` — o'chirish uchun yetarli
            minimum. To'liq qator o'qilmaydi: partiya kattaligida bu
            ortiqcha xotira.
        """
        return [dict(r) for r in self._rows(
            "SELECT idem_key, storage_ref, size_bytes FROM snapshots"
            " WHERE received_at < ? ORDER BY received_at LIMIT ?",
            (cutoff, limit))]

    def delete_snapshot_row(self, idem_key: str) -> None:
        """Metadata qatorini o'chiradi.

        ⛔⛔ FAQAT RASM O'CHIRILGANDAN KEYIN CHAQIRILADI. Teskari tartibda
            metadata yo'qolib, rasm S3'da qolardi — uni endi HECH KIM
            topa olmaydi (havola faqat shu qatorda edi) va u abadiy
            chiqindi bo'lib joy egallardi.
        """
        self._exec("DELETE FROM snapshots WHERE idem_key=?", (idem_key,))

    def oldest_snapshot_age_days(self, now: float) -> float | None:
        """Eng eski kadr necha kunlik. Panel shu sondan foydalanadi."""
        rows = self._rows("SELECT MIN(received_at) AS t FROM snapshots")
        eng_eski = rows[0]["t"] if rows else None
        if eng_eski is None:
            return None
        return max(0.0, (now - float(eng_eski)) / 86400.0)

    # --- buyruqlar va hodisalar ---

    def queue_command(self, agent_id: str, name: str, params: dict) -> str:
        cmd_id = "c-" + secrets.token_hex(4)
        self._exec(
            "INSERT INTO commands(cmd_id, agent_id, name, params_json, created_at) VALUES(?,?,?,?,?)",
            (cmd_id, agent_id, name, json.dumps(params, ensure_ascii=False), time.time()),
        )
        return cmd_id

    def pending_commands(self, agent_id: str) -> list[dict]:
        return [dict(r) for r in self._rows(
            "SELECT * FROM commands WHERE agent_id=? AND sent_at IS NULL ORDER BY created_at", (agent_id,))]

    def mark_command_sent(self, cmd_id: str) -> None:
        self._exec("UPDATE commands SET sent_at=? WHERE cmd_id=?", (time.time(), cmd_id))

    def record_command_result(self, cmd_id: str, result: dict, agent_id: str = "") -> None:
        """Natija AYNI agentning buyrug'iga yoziladi.

        `agent_id` sizsiz bir agent boshqasining buyrug'iga soxta natija
        yozib qo'yishi mumkin edi.
        """
        if agent_id:
            self._exec(
                "UPDATE commands SET result_json=? WHERE cmd_id=? AND agent_id=?",
                (json.dumps(result, ensure_ascii=False), cmd_id, agent_id))
        else:
            self._exec("UPDATE commands SET result_json=? WHERE cmd_id=?",
                       (json.dumps(result, ensure_ascii=False), cmd_id))

    def list_commands(self, agent_id: str, limit: int = 50) -> list[dict]:
        return [dict(r) for r in self._rows(
            "SELECT * FROM commands WHERE agent_id=? ORDER BY created_at DESC LIMIT ?", (agent_id, limit))]

    def slot_completeness(self, hours: int = 24) -> list[dict]:
        """Har slot bo'yicha: nechta kadr kutilgan, nechtasi kelgan.

        "Rasm yo'q" va "rasmda rasta bo'sh" — butunlay boshqa narsa. Busiz
        yo'qolgan dalil hech qayerda ko'rinmaydi va hech kim bilmaydi.
        Kutilgan son agentning ro'yxatdan o'tgan kanallari sonidan olinadi.
        """
        since = time.time() - hours * 3600
        rows = self._rows(
            "SELECT s.agent_id, a.market_name, a.nvrs_json,"
            "  substr(s.idem_key, length(s.idem_key) - 15) AS slot,"
            "  COUNT(*) AS got, MAX(s.received_at) AS last_at"
            " FROM snapshots s JOIN agents a ON a.agent_id = s.agent_id"
            " WHERE s.received_at >= ? AND s.trigger = 'schedule'"
            " GROUP BY s.agent_id, slot ORDER BY last_at DESC LIMIT 200",
            (since,))
        out = []
        for r in rows:
            expected = sum(
                1 for nvr in json.loads(r["nvrs_json"] or "[]")
                for c in (nvr.get("channels") or []) if c.get("enabled", True))
            out.append({
                "agent_id": r["agent_id"], "market_name": r["market_name"],
                "slot": r["slot"], "got": r["got"], "expected": expected,
                "missing": max(0, expected - r["got"]), "last_at": r["last_at"],
            })
        return out

    # ------------------------------------------------ jonli video

    def start_stream_session(self, session_id: str, agent_id: str, channel: int,
                             actor: str, mode: str = "webrtc",
                             nvr_serial: str = "") -> None:
        """Jonli ko'rish seansini ochadi.

        CLAUDE.md 11-bo'lim: "Kim, qachon, qaysi kamerani ochgani
        jurnalga yoziladi." Bu shunchaki audit emas — bozor kamerasini
        kim ko'rgani shaxsiy ma'lumot masalasi, va tekshiruvda birinchi
        so'raladigan narsa.

        `nvr_serial` saqlanadi, chunki ijara uzaytirilganda qayta
        yuboriladigan `start_stream` aynan o'sha NVR'ga borishi kerak.
        """
        now = time.time()
        self._exec(
            "INSERT OR REPLACE INTO stream_sessions(session_id, agent_id, channel,"
            " nvr_serial, actor, started_at, last_seen_at, mode)"
            " VALUES(?,?,?,?,?,?,?,?)",
            (session_id, agent_id, int(channel), nvr_serial or "", actor, now, now, mode))

    def touch_stream_session(self, session_id: str) -> bool:
        """Brauzer hali ochiq — ijarani uzaytiradi.

        Sahifa yopilsa bu chaqiruv KELMAY QOLADI va seans muddati tugab,
        oqim o'chadi. Cheklovni UI'ga ishonib topshirib bo'lmaydi:
        brauzer yiqilsa yoki tarmoq uzilsa "yopildi" signali kelmaydi.
        """
        cur = self._exec(
            "UPDATE stream_sessions SET last_seen_at=? "
            "WHERE session_id=? AND ended_at IS NULL", (time.time(), session_id))
        return cur.rowcount > 0

    def end_stream_session(self, session_id: str, reason: str) -> dict | None:
        """Seansni yopadi va YANGILANGAN qatorni qaytaradi.

        Chaqiruvchi undan `agent_id` va `channel` ni olib agentga
        `stop_stream` yuboradi, shuning uchun qator yangilangan holda
        qaytishi kerak — aks holda "nega yopildi" jurnalda bo'sh qoladi.
        """
        if not self._rows("SELECT 1 FROM stream_sessions WHERE session_id=?",
                          (session_id,)):
            return None
        self._exec("UPDATE stream_sessions SET ended_at=?, end_reason=? "
                   "WHERE session_id=? AND ended_at IS NULL",
                   (time.time(), reason, session_id))
        rows = self._rows("SELECT * FROM stream_sessions WHERE session_id=?",
                          (session_id,))
        return dict(rows[0]) if rows else None

    def stream_session(self, session_id: str) -> dict | None:
        rows = self._rows("SELECT * FROM stream_sessions WHERE session_id=?",
                          (session_id,))
        return dict(rows[0]) if rows else None

    def open_stream_sessions(self, agent_id: str = "") -> list[dict]:
        sql = "SELECT * FROM stream_sessions WHERE ended_at IS NULL"
        args: tuple = ()
        if agent_id:
            sql += " AND agent_id=?"
            args = (agent_id,)
        return [dict(r) for r in self._rows(sql + " ORDER BY started_at", args)]

    def stale_stream_sessions(self, older_than_s: float) -> list[dict]:
        """Brauzer aloqasi uzilgan seanslar — ularni yopish kerak."""
        chegara = time.time() - older_than_s
        return [dict(r) for r in self._rows(
            "SELECT * FROM stream_sessions WHERE ended_at IS NULL AND last_seen_at < ?",
            (chegara,))]

    def stream_minutes_this_month(self, agent_id: str) -> float:
        """Shu oyda qancha daqiqa jonli video ko'rilgan.

        Har bozorga oylik limit kerak (SBOZOR-CHECKLIST 2B): TURN orqali
        o'tgan trafik pul turadi va bitta unutilgan sahifa oylik byudjetni
        yeb qo'yishi mumkin. Limit tugasa obyekt avtomatik "yangilanuvchi
        rasm" rejimiga tushadi — video o'chadi, dalil yig'ish esa davom
        etadi (4-prinsip).
        """
        oy_boshi = time.time() - 30 * 86400
        rows = self._rows(
            "SELECT started_at, last_seen_at, ended_at FROM stream_sessions"
            " WHERE agent_id=? AND started_at >= ?", (agent_id, oy_boshi))
        jami = 0.0
        for r in rows:
            tugash = r["ended_at"] or r["last_seen_at"]
            jami += max(0.0, float(tugash) - float(r["started_at"]))
        return jami / 60.0

    def latest_snapshot(self, agent_id: str, channel: int) -> dict | None:
        """Shu kanalning eng oxirgi kadri — zaxira ("yangilanuvchi rasm") rejimi.

        Umumiy `list_snapshots()` dan foydalanib bo'lmaydi: u BARCHA
        obyektlarning kadrlarini vaqt bo'yicha beradi va 12 bozor faol
        bo'lganda kerakli kanal ro'yxatdan tushib qoladi.
        """
        rows = self._rows(
            "SELECT * FROM snapshots WHERE agent_id=? AND channel=?"
            " ORDER BY received_at DESC LIMIT 1", (agent_id, int(channel)))
        return dict(rows[0]) if rows else None

    def list_stream_sessions(self, agent_id: str = "", limit: int = 100) -> list[dict]:
        sql = "SELECT * FROM stream_sessions"
        args: tuple = ()
        if agent_id:
            sql += " WHERE agent_id=?"
            args = (agent_id,)
        return [dict(r) for r in self._rows(
            sql + " ORDER BY started_at DESC LIMIT ?", args + (limit,))]

    def delete_agent(self, agent_id: str) -> None:
        """Obyektni ro'yxatdan olib tashlaydi (kompyuter almashtirilganda).

        Rasmlar QOLADI — ular dalil. Faqat agent yozuvi va uning
        sozlamalari o'chiriladi.
        """
        for sql in ("DELETE FROM agents WHERE agent_id=?",
                    "DELETE FROM quarantine WHERE agent_id=?",
                    "DELETE FROM commands WHERE agent_id=?"):
            self._exec(sql, (agent_id,))

    def command_by_id(self, cmd_id: str) -> dict | None:
        rows = self._rows("SELECT * FROM commands WHERE cmd_id=?", (cmd_id,))
        return dict(rows[0]) if rows else None

    def log_event(self, agent_id: str | None, kind: str, detail: str,
                  actor: str = "") -> None:
        """CLAUDE.md 6-bo'lim: kim, qachon, qaysi bozor."""
        self._exec(
            "INSERT INTO events(agent_id, ts, kind, detail, actor) VALUES(?,?,?,?,?)",
            (agent_id, time.time(), kind, detail, actor or "tizim"))

    def list_events(self, limit: int = 100) -> list[dict]:
        return [dict(r) for r in self._rows("SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,))]
