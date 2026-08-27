# CamAgent ↔ Server protokoli — v1 (MUZLATILGAN)

> Yagona haqiqat manbai. Agent ham, sbozor `agent_gateway` ham shu hujjatga
> qarab yoziladi. O'zgartirish = yangi `v` qiymati; v1 maydonlari hech qachon
> o'zgarmaydi va olib tashlanmaydi (500 bozorda eski versiyalar qoladi).
>
> Format: faqat JSON (UTF-8). Python'ga xos hech narsa yo'q (pickle taqiqlangan).
> Vaqtlar hamma joyda **UTC, ISO-8601** (`2026-08-25T05:00:00Z`).

---

## 1. Transport

| Kanal | Manzil | Vazifa |
|---|---|---|
| WebSocket (wss) | `/api/v1/agent/ws` | register, heartbeat, buyruqlar, natijalar (JSON matn freymlari) |
| HTTPS POST | `/api/v1/agent/snapshot` | rasm (JPEG body), metama'lumot sarlavhalarda |
| HTTPS POST | `/api/v1/agent/speedtest` | upload tezligini o'lchash (tasodifiy baytlar) |
| HTTPS POST | `/api/v1/agent/activate` | bir martalik aktivatsiya (o'rnatish bosqichi) |

Rasm WS ichidan YUBORILMAYDI (head-of-line blocking). Keyinchalik server
`snapshot` o'rniga presigned S3 URL berishi mumkin — buning uchun v2 emas,
`config.upload_url` maydoni yetarli (hozircha bo'sh).

Har JSON xabarda majburiy maydon: `"v": 1`.

---

## 2. Aktivatsiya (bir martalik, o'rnatish oynasidan)

`POST /api/v1/agent/activate` — token YO'Q, faqat aktivatsiya kodi.

```json
{
  "v": 1,
  "activation_code": "KARMANA-7F3K2",
  "instance_id": "i-9f2c4e8a1b3d",
  "agent_version": "0.4.0",
  "hostname": "DESKTOP-BOZOR1",
  "nvrs": [
    {
      "serial": "DS-7616NI-K2/1620210101CCRR",
      "model": "DS-7616NI-K2",
      "firmware": "V4.30.085",
      "channels": [
        {"id": 1, "name": "Kirish darvoza", "camera_ip": "192.168.1.64", "enabled": true}
      ]
    }
  ]
}
```

Javob `200`:

```json
{"v": 1, "token": "at_...", "agent_id": "a-12", "config": { }}
```

Xatolar: `404` — kod topilmadi; `409` — kod allaqachon ishlatilgan.
`instance_id` agent birinchi ishga tushishida yaratiladi va o'zgarmaydi
(`config` papkasida saqlanadi). Token DPAPI bilan shifrlab saqlanadi.

---

## 3. WebSocket sessiyasi

Ulanish ochilgach agent **birinchi** xabar sifatida `register` yuboradi.
Server 10 soniyada `register` olmasa ulanishni yopadi.

### 3.1 `register` (agent → server)

```json
{
  "v": 1,
  "type": "register",
  "token": "at_...",
  "instance_id": "i-9f2c4e8a1b3d",
  "agent_version": "0.4.0",
  "uptime_s": 12,
  "nvrs": [
    {
      "serial": "DS-7616NI-K2/1620210101CCRR",
      "model": "DS-7616NI-K2",
      "firmware": "V4.30.085",
      "ip": "192.168.1.100",
      "channels": [
        {"id": 1, "name": "Kirish darvoza", "camera_ip": "192.168.1.64", "enabled": true},
        {"id": 2, "name": "Meva rastalari", "camera_ip": "192.168.1.65", "enabled": true}
      ]
    }
  ]
}
```

- `nvrs` — har doim **ro'yxat** (bir agent = bir nechta NVR, v0.1 bittasini yuboradi).
- `firmware` majburiy — panel zaif proshivkalarni flot bo'ylab ko'radi.
- Kanal bilan birga `name` va `camera_ip` majburiy — server rasta↔kamera
  bog'lanish o'zgarganini sezadi.

### 3.2 `registered` (server → agent)

```json
{
  "v": 1,
  "type": "registered",
  "agent_id": "a-12",
  "server_time": "2026-08-25T05:00:00Z",
  "config": { }
}
```

- `server_time` — agent soat farqini shu yerdan o'lchaydi
  (`offset = server_time - agent_utc_now`).
- `config` — **TO'LIQ konfiguratsiya** (desired-state, 5-bo'lim).

Agar token noto'g'ri: `{"v":1,"type":"reject","code":"bad_token"}` va ulanish yopiladi.
Agar shu token ostida **boshqa** `instance_id` allaqachon faol:
`{"v":1,"type":"reject","code":"instance_conflict"}` — ikkinchi nusxa rad
etiladi, panelda ogohlantirish chiqadi.

### 3.3 `heartbeat` (agent → server, har `config.heartbeat_s`)

```json
{
  "v": 1,
  "type": "heartbeat",
  "ts": "2026-08-25T05:01:00Z",
  "status": "ok",
  "queue_len": 0,
  "disk_free_mb": 41200,
  "mem_free_mb": 2100,
  "uptime_s": 72,
  "agent_version": "0.4.0",
  "last_snapshot": "2026-08-25T04:00:11Z",
  "upload_mbps": 12.4,
  "nvr_ok": true
}
```

`status`: `ok` | `nvr_unreachable` | `auth_failed` | `degraded`.
Server javobi (ixtiyoriy, vaqt sinxron uchun):
`{"v":1,"type":"heartbeat_ack","server_time":"..."}`.

### 3.4 `command` (server → agent)

```json
{"v": 1, "type": "command", "id": "c-501", "name": "snapshot_now", "params": {}}
```

Ruxsat etilgan `name` qiymatlari — **faqat** shu ro'yxat:

```
snapshot_now · rescan_nvr · update_config · update_credentials
enable_channel · disable_channel · restart · get_logs
start_stream · stop_stream · update_agent
```

Ro'yxatda yo'q buyruq bajarilmaydi: agent
`command_result{ok:false, code:"unknown_command"}` qaytaradi va jurnalga yozadi.

Parametrlar:

| Buyruq | `params` |
|---|---|
| `snapshot_now` | `{"channels": [1,2]}` — bo'sh bo'lsa hammasi |
| `rescan_nvr` | `{}` |
| `update_config` | `{"config": { }}` — **to'liq** konfiguratsiya (5-bo'lim) |
| `update_credentials` | `{"nvr_serial": "...", "username": "...", "password": "..."}` |
| `enable_channel` / `disable_channel` | `{"nvr_serial": "...", "channel": 3}` |
| `restart` | `{}` |
| `get_logs` | `{"max_kb": 256}` |
| `start_stream` | `{"nvr_serial": "...", "channel": 3, "duration_s": 600, "publish_url": "rtsp://..."}` |
| `stop_stream` | `{"nvr_serial": "...", "channel": 3}` — kanal berilmasa hammasi |
| `update_agent` | `{"version": "0.5.0", "url": "https://...zip", "sha256": "...", "sig": "base64(ed25519)"}` |

### 3.5 `command_result` (agent → server)

```json
{
  "v": 1, "type": "command_result", "id": "c-501",
  "ok": true, "code": "done", "detail": "3 kanaldan rasm olindi",
  "data": {}
}
```

`get_logs` uchun jurnal matni `data.log` ichida (chegara `max_kb`).
`rescan_nvr` uchun `data.nvrs` — `register`dagi bilan bir xil tuzilma.

### 3.6 `error` (agent → server, hodisa bo'lganda)

```json
{"v": 1, "type": "error", "ts": "...", "code": "disk_cap_prune", "message": "Disk limiti oshdi, 12 ta eski rasm o'chirildi"}
```

Kodlar: `disk_cap_prune` · `auth_failed` · `nvr_unreachable` ·
`snapshot_failed` · `update_failed` · `rollback` · `stream_failed` ·
`unknown_command` · `queue_corrupt_rebuilt`.

### 3.7 Qayta ulanish

Eksponensial backoff: 1 s dan boshlab ×2, maksimum 60 s, har safar
±30 % tasodifiy jitter. Ulanish tiklangach navbat FIFO tartibda,
`config.upload_rate_kbps` limiti bilan bo'shatiladi.

---

## 4. Rasm yuborish — `POST /api/v1/agent/snapshot`

Body: xom JPEG baytlari (`Content-Type: image/jpeg`).
Metama'lumot — sarlavhalarda:

| Sarlavha | Misol | Izoh |
|---|---|---|
| `Authorization` | `Bearer at_...` | agent tokeni |
| `X-Idempotency-Key` | `karmana-01:DS.../CCRR:3:2026-08-25T04:00` | 4.1-bo'lim |
| `X-Channel` | `3` | kanal raqami |
| `X-NVR-Serial` | `DS-7616NI-K2/1620210101CCRR` | |
| `X-NVR-Time` | `2026-08-25T04:00:09Z` | NVR o'z vaqti (bo'lmasa bo'sh) |
| `X-Agent-Time` | `2026-08-25T04:00:10Z` | agent UTC |
| `X-Server-Time-Est` | `2026-08-25T04:00:12Z` | agent + o'lchangan offset |
| `X-Late` | `0` yoki `1` | catch-up rasmi (kechikkan) |
| `X-Trigger` | `schedule` yoki `command:c-501` | |
| `X-SHA256` | `9f86d08...` | JPEG baytlari hash'i |

Javoblar:

- `200 {"v":1,"ok":true,"duplicate":false}` — qabul qilindi, agent navbatdan o'chiradi.
- `200 {"v":1,"ok":true,"duplicate":true}` — bu kalit allaqachon bor, ikkinchi
  nusxa YARATILMAYDI, agent navbatdan o'chiradi.
- `401` — token yaroqsiz (agent `error` yozadi, qayta ro'yxatdan o'tishga harakat qiladi).
- `413` / `5xx` — navbatda qoladi, keyinroq qayta yuboriladi.

Server `X-SHA256`ni qayta hisoblab solishtiradi — mos kelmasa `400`,
agent rasmni qayta yuboradi.

### 4.1 Idempotency kaliti (deterministik)

```
{agent_key_prefix}:{nvr_serial}:{kanal}:{slot}
```

- `agent_key_prefix` — server `config`da beradigan **shaffof bo'lmagan** satr
  (agent uning ma'nosini bilmaydi; server uchun bu bozor/agent identifikatori).
- `slot` — jadval sloti, daqiqagacha: `2026-08-25T04:00` (UTC).
- `snapshot_now` uchun slot o'rniga buyruq ID: `...:3:cmd-c-501`.
- Catch-up rasmi ham **o'z slotining** kalitini oladi (shuning uchun ikki marta
  urinilsa dublikat bo'lmaydi).

---

## 5. Konfiguratsiya obyekti (desired-state, TO'LIQ)

`registered.config` va `update_config.params.config` — har doim to'liq shu
tuzilma. Agent olgach eskisini butunlay almashtiradi va diskka saqlaydi
(offlayn ishga tushish uchun).

```json
{
  "v": 1,
  "agent_key_prefix": "karmana-01",
  "schedule": ["04:00", "06:00", "08:00", "16:00", "18:00"],
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
  "stream": {"enabled": true, "max_duration_s": 600, "max_channels": 2}
}
```

- `schedule` — mahalliy vaqt (`timezone` bo'yicha), `HH:MM`.
- `channels_disabled` — `["{nvr_serial}:{ch}"]` formatida.
- `upload_rate_kbps: 0` — cheklovsiz.
- `upload_url` bo'sh — rasm `POST /snapshot`ga boradi; to'ldirilsa (kelajakda
  presigned S3) — o'sha manzilga.
- Agent notanish maydonlarni **e'tiborsiz saqlaydi** (oldinga moslik).

---

## 6. Tezlik o'lchash — `POST /api/v1/agent/speedtest`

Agent `register`dan keyin (va har `speedtest.interval_days` kunda)
`size_kb` hajmdagi tasodifiy baytlarni yuboradi, davomiylikni o'zi o'lchaydi
va natijani keyingi `heartbeat.upload_mbps`da bildiradi.

| O'lchangan upload | Server qo'yadigan profil |
|---|---|
| < 5 Mbit/s | `low` — past sifat, jonli video o'chiq |
| 5–50 Mbit/s | `standard` — 2 kanalgacha video |
| > 50 Mbit/s | `high` — video ochiq |

Profilni **server** tanlaydi va `update_config` bilan yuboradi — agent o'zi
qaror qilmaydi (biznes-mantiq serverda).

---

## 7. Yangilanish paketi

`update_agent` ko'rsatgan `url`dan ZIP yuklanadi. Tekshiruvlar tartibi:

1. `sha256` mos kelishi
2. Ed25519 imzo (`sig`) — ochiq kalit agentga qurilgan
3. ZIP ichida `camagent/VERSION` fayli `version` bilan mos kelishi

Uchtasi ham o'tsa — `versions/<version>/` ga ochiladi, launcher yangi
versiyani ishga tushiradi. Yangi versiya **10 daqiqa ichida muvaffaqiyatli
`register`** qilmasa launcher eskisiga qaytaradi va serverga
`error{code:"rollback"}` yuboriladi. (Tafsilot: CLAUDE.md 9-bo'lim.)

---

## 8. Versiyalash qoidasi

- v1 maydonlari o'zgarmaydi, olib tashlanmaydi.
- Yangi ixtiyoriy maydon qo'shish mumkin — eski agentlar uni e'tiborsiz
  qoldiradi, eski server ham shunday.
- Majburiy o'zgarish kerak bo'lsa — `v: 2`, lekin server v1 ni ham
  cheksiz qo'llab-quvvatlaydi.
