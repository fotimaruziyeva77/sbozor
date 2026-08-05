<!-- GSD:project-start source:PROJECT.md -->

## Project

**SBOZOR**

SBOZOR — O'zbekiston an'anaviy bozorlarini raqamlashtiruvchi universal SaaS platforma. Bozor ma'muriyati uchun: mavjud NVR kameralaridan olingan snapshotlarni AI tahlil qilib, band rastalarni aniqlaydi, kunlik patta hisobini yuritadi va to'lovlar bilan solishtirib nomuvofiqlikni fosh qiladi. MVP — Karmana tumani bozori (Navoiy viloyati, ~300–1000 rasta) pilotida "har bir band rastadan patta to'liq yig'ilyaptimi?" savoliga raqamlar va rasm-dalil bilan javob berish.

**Core Value:** Bozor ma'muriyati har bir band rastadan patta to'liq yig'ilayotganini raqamlar va rasm-dalil bilan ko'radi — "band, lekin to'lovsiz" rastalar kunlik hisobotda avtomatik fosh bo'ladi.

### Constraints

- **Muddat**: 12 hafta (2026-07-28 → ~2026-10-18 Karmanada jonli) — davlat dasturi oynasi va raqobat tezligi
- **Stek**: FastAPI (core-api, cv-service) + aiogram (bot-service) + Next.js/Tailwind (frontend) + PostgreSQL/Valkey/SeaweedFS + Docker Compose — jamoa ko'nikmasi, MVP topshirig'ida qat'iylashtirilgan (tadqiqot 2026-07-29: MinIO arxivlangan → SeaweedFS; Redis → Valkey)
- **Servislar soni**: aynan 3 ta (core-api, cv-service, bot-service) — ortiqcha mikroservis bo'linmaydi
- **Litsenziya**: CV modellar faqat Apache-2.0/MIT — tanlov: RF-DETR (Nano→Large; XLarge/2XLarge PML 1.0 — TAQIQ); AGPL (Ultralytics) taqiqlangan — tijoriy SaaS
- **Infra**: Contabo VPS (8–16 GB RAM, 4–6 vCPU, 400+ GB disk), GPU'siz inference (CPU yetadi); fine-tuning uchun vaqtinchalik ijara GPU
- **Data-rezidentlik**: shaxsiy ma'lumotlar O'zR qonuni ostida — davlat bosqichidan oldin O'zbekiston hostingiga ko'chish rejalashtirilgan (compose ko'chishni osonlashtiradi)
- **Multi-tenant**: hamma jadvalda `market_id` — bitta kod bazasi, cheksiz bozor; yangi bozor kod yozmasdan wizard orqali ulanadi
- **UI**: Apple-uslub minimal dizayn; kassir oqimi ≤3 bosish; 3 til majburiy
- **Xavfsizlik**: NVR faqat VPN (WireGuard) orqali; RTSP parollari shifrlangan; audit jurnali majburiy

<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->

## Technology Stack

## Executive verdict — read this first

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **Python** | **3.13.x** (3.13.14) | Runtime for all 3 services | Only version where *every* required wheel exists today: onnxruntime 1.28 ships cp311–cp314, numpy 2.5.1 needs ≥3.12, torch 2.13 ships cp310–cp314, aiogram caps at `<3.15`. 3.13 has been stable 21 months (EOL 2029-10). **3.12** works but you lose free-threading/JIT groundwork; **3.14** is 9 months old and C-extension wheel coverage still lags on niche deps. Spec's "3.12+" is satisfied. |
| **FastAPI** | **0.140.13** (2026-07-28) | core-api + cv-service HTTP | Fixed by constraint. Extremely active — released yesterday. Use `lifespan=` (not `@on_event`), `Annotated[X, Depends(...)]` DI style. |
| **Pydantic** | **2.13.4** | Validation / settings / DTOs | v2 (Rust core). **Hard cap: aiogram 3.30 requires `pydantic<2.14`** — see Version Compatibility. |
| **SQLAlchemy** | **2.0.51** (2026-06-15) | ORM + Core, async | 2.0 declarative + `Mapped[]`/`mapped_column()` typing style. `AsyncSession` + `async_sessionmaker`. No credible alternative — SQLModel adds a leaky Pydantic/SA hybrid you will fight during multi-tenant RLS work; Tortoise/Piccolo have thinner Postgres feature coverage. |
| **Alembic** | **1.18.5** | Schema migrations | Same maintainer as SQLAlchemy; autogenerate against async engine via a sync wrapper (`connection.run_sync`). See gotcha under alembic-utils. |
| **asyncpg** | **0.31.0** | Postgres driver | Fastest async PG driver; SQLAlchemy URL `postgresql+asyncpg://`. Alembic runs sync — give it a separate `postgresql+psycopg://` URL or `run_sync`. |
| **PostgreSQL** | **18.4** (`postgres:18.4-trixie`) | Primary DB, multi-tenant | PG 18 GA, supported to 2030-11. **Do not use 19** (still `19beta2`). Native `uuidv7()`, async I/O, improved `EXPLAIN`. |
| **Valkey** | **9.1.1** (`valkey/valkey:9.1.1-alpine`) | Queue broker + cache + FSM store | Drop-in Redis replacement, **BSD-3-Clause**, Linux Foundation governed. Redis 8.x is AGPLv3/RSALv2/SSPL tri-licensed — legally fine as an unmodified separate service, but Valkey removes the conversation entirely, which matches this project's stated license posture. `redis-py` client works unchanged. |
| **SeaweedFS** | **4.40** (`chrislusf/seaweedfs:4.40`) | S3-compatible snapshot archive | **Replaces MinIO.** Apache-2.0, 33.7k stars, released 2026-07-20, active. Single-node: `weed server -s3 -dir=/data` in one container. Purpose-built for many small files (exactly: 175 JPEGs/day × N markets). |
| **go2rtc** | **v1.9.14** | RTSP→WebRTC/HLS live view **and** snapshot capture | Fixed by constraint for live view; **also becomes the snapshot source** via `/api/frame.jpeg`. Single Go binary, holds persistent RTSP sessions so a snapshot is an HTTP GET. **⚠ SECURITY (GHSA-wwww-5h25-jf98, CVSS 9.1): `PUT /api/streams?src=exec:…` executes arbitrary commands.** Therefore: go2rtc's HTTP API is NEVER proxied to users or exposed beyond the compose network, and any `src` value core-api forwards MUST be allow-listed to the `rtsp://` scheme. Treat go2rtc as a trusted-network-only internal service. |
| **ONNX Runtime** | **1.28.0** (2026-07-25) | CPU inference for the detector | See "Why ONNX Runtime, not OpenVINO / not torch" below. ~15 MB wheel vs torch's ~800 MB — keeps the cv-service production image small. |
| **RF-DETR** (`rfdetr`) | **1.9.1** (2026-08-04) | Object detector (person + goods in zones) | **Apache-2.0**, verified 2026-08-05 against PyPI metadata, the GitHub API, the raw `LICENSE` and the README. **The licence risk changed shape in 1.9.x and is now mechanically enforceable:** the PML component moved into a **separate distribution**, `rfdetr-plus` 1.0.2 (`license_expression = LicenseRef-PML-1.0`), pulled **only** by the `[plus]` extra. So "never use XLarge/2XLarge" stops being discipline and becomes a **lockfile invariant** — a test asserting `rfdetr-plus` is absent (and no `LicenseRef-*`/AGPL distribution is installed) catches it, and the same gate also catches `ultralytics`. **⚠ `torch` is a mandatory dependency of `rfdetr`, not an extra** — the production image must therefore never install `rfdetr` at all: ship `onnxruntime` plus a prebuilt `.onnx`. |
| **supervision** | **0.30.0** | Polygon-zone occupancy logic + HITL annotation images | MIT, 48k stars, pushed 2026-07-28. `sv.PolygonZone` / `sv.PolygonZoneAnnotator` is *literally* your `camera_zones` → `occupancy_events` step. Roboflow publishes an "Occupancy Analytics" cookbook for this exact pattern. Do **not** hand-roll point-in-polygon. |
| **aiogram** | **3.30.0** (2026-07-17) | bot-service (vendor + director bots) | Fixed by constraint. MIT. asyncio-native, FSM built in. Install `aiogram[fast,redis,i18n]`. |
| **Next.js** | **16.2.12** | Admin panel + cashier mobile + wizard | Fixed by constraint. App Router. **Breaking change vs every tutorial online: `middleware.ts` is now `proxy.ts`, Node runtime only, no Edge.** |
| **React** | **19.2.8** | UI | Required exactly by react-konva 19.2.5 (`peer: react ^19.2.0`). |
| **TypeScript** | **5.9.3** — **not 7.0.2** | Typing | TS 7.0 (Go-native) went GA 2026-07-08, but Next.js only supports it in **16.3-preview behind `experimental.useTypeScriptCli`**, and TS 7.0 ships **no stable programmatic API until 7.1**, breaking parts of the tooling ecosystem. A 12-week MVP is not where you absorb that. Revisit after launch. |
| **Tailwind CSS** | **4.3.3** | Styling | Fixed by constraint. v4 = CSS-first config (`@theme` in CSS, no `tailwind.config.js`), Oxide engine. Wire via `@tailwindcss/postcss@4.3.3`. |
| **next-intl** | **4.13.4** | 3 locales (uz-Latn / uz-Cyrl / ru) | `peerDependencies.next` includes `^16.0.0` — verified compatible. Server-Component-native, ICU message syntax (needed for Uzbek/Russian plural rules). Spec §7 mandates i18n scaffolding from week 1 — this is the right call, retrofitting is brutal. |
| **react-konva** | **19.2.5** + **konva 10.3.0** | Camera-zone polygon editor **and** market plan-map | MIT. React-reconciler bindings to Konva canvas — you get declarative `<Line closed points={...} draggable>` synced to React state, which is exactly a polygon editor. Handles 1000 stalls with pan/zoom where SVG/DOM dies. Same component serves both spec §4.1 layers. |
| **Docker Compose** | v2 (`docker compose`) | Orchestration | Fixed by constraint. One `compose.yaml`, per-service `.env`. Enables the planned Uzbekistan-hosting migration at low cost. |
| **Nginx** | **1.30.4** (`nginx:1.30.4-alpine`) | Reverse proxy + TLS | Fixed by constraint. 1.30 is the current *stable* branch (no EOL date); 1.31 is mainline. Pair with certbot. See Caddy alternative. |
| **uv** | **0.11.33** | Python deps + lockfile + venv | Astral. 10–100× faster than pip, deterministic `uv.lock`, `uv sync --frozen` in Dockerfiles. **Per-service `pyproject.toml`** — this is how you resolve the aiogram pin conflicts below. |

### Supporting Libraries

#### Backend — core-api

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pydantic-settings` | 2.14.2 | Typed env config | Every service. One `Settings` class, `.env` per service. |
| `PyJWT` | **2.13.0** (2026-05-21) | JWT access/refresh tokens | Access token 15 min + refresh token in httpOnly cookie. **Not python-jose** (last release 2025-05-28, effectively unmaintained) and **not Authlib** (an OAuth framework; overkill when you own both ends). |
| `pwdlib[argon2]` | **0.3.0** | Password hashing | **Not passlib.** passlib 1.7.4 is from **2020-10-08**, is unmaintained, and imports the `crypt` stdlib module removed in Python 3.13 — it will not import on your runtime. pwdlib+Argon2id is what fastapi-users v13+ switched to. |
| `argon2-cffi` | 25.1.0 | pwdlib Argon2 backend | Transitive via `pwdlib[argon2]`. |
| `cryptography` | 49.0.0 | Fernet encryption of RTSP/NVR credentials | Spec §5 requires encrypted RTSP passwords at rest. Key from env/secret, never in DB. |
| `alembic-utils` | 0.8.8 | Autogenerate RLS policies, views, functions | **Needed.** Alembic does *not* autogenerate `CREATE POLICY`. Without this, your RLS drifts from your models silently. `PGPolicy`, `PGView`, `PGFunction`. |
| `XlsxWriter` | **3.2.9** | All `.xlsx` report exports | Write-only, constant memory, richer formatting than openpyxl (freeze panes, autofilter, number formats, conditional formats) — which is what a "qarzdorlik reestri" needs. Stream to `io.BytesIO` → FastAPI `StreamingResponse`. **Not openpyxl** — it materialises the whole workbook in memory and you never need to *read* xlsx. |
| `python-multipart` | 0.0.32 | Multipart form parsing | Required by FastAPI for plan-image upload in the wizard. |
| `email-validator` | 2.3.0 | Pydantic `EmailStr` | Transitive via `pydantic[email]`. |
| `phonenumbers` | 9.0.35 | Uzbek phone normalisation (+998…) | Vendor registration via Telegram uses phone as identity — normalise to E.164 at the boundary or you will get duplicate vendors. |
| `structlog` | 26.1.0 | Structured JSON logging | Bind `market_id`, `user_id`, `request_id` into every log line. Essential for a multi-tenant audit story. |
| `asgi-correlation-id` | 5.0.1 | Request ID propagation | Correlates core-api → cv-service → bot-service logs. |
| `sentry-sdk[fastapi]` | 2.66.1 | Error tracking | Spec §5 explicitly requires Sentry. |
| `tenacity` | 9.1.4 | In-request retry (HTTP to go2rtc / ISAPI) | Apache-2.0. Different layer from arq's job retries — use both. |
| `httpx` | 0.28.1 | Async HTTP client | Talking to go2rtc, Hikvision ISAPI (`httpx.DigestAuth`), Telegram. **⚠ As of 2026-08-02 `httpx` sits in core-api's `[dependency-groups] dev`, not `[project] dependencies`.** That is correct only while it is test-only. Phase 3's ISAPI client is production code — it MUST be promoted to `[project] dependencies` in that phase, or the service will import-fail at deploy while every test passes. |
| `aiobotocore` | **3.9.0** (2026-08-01) | Async S3 access to SeaweedFS | **Replaces `aioboto3` (2026-08-04).** `aioboto3 15.5.0` hard-pins `aiobotocore[boto3]==2.25.1`, which drags `boto3` down from 1.43.62 to 1.40.61 — so the `aioboto3 15.5.0` + `boto3 1.43.57` pairing this table previously listed **cannot be installed**. Verified against PyPI metadata and reproduced with a real install. `aioboto3`'s last release was 2025-10-30. Use `aiobotocore` directly; `aiohttp` is already present transitively via `taskiq`, so no new HTTP stack. **Still the S3 API, never `minio-py`** — that is what keeps the storage backend a config change (SeaweedFS → Garage → AWS S3 → Uzbek cloud) instead of a refactor. |
| `tzdata` | 2026.3 | Asia/Tashkent in slim images | Python 3.13 on `python:3.13-slim` has **no** tzdata — `ZoneInfo("Asia/Tashkent")` raises without this. Bites you the first time a report boundary is wrong. |
| `prometheus-fastapi-instrumentator` | 8.1.0 | Metrics | Optional for MVP. Add if you want snapshot-success-rate dashboards beyond Telegram alerts. |

#### Backend — cv-service

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `taskiq` + `taskiq-redis` | **0.12.4** + **1.2.3** | Job queue **and** cron for the snapshot pipeline | **Replaces arq (2026-08-02).** `arq 0.28.0` declares `redis[hiredis]<6,>=4.2.0`, but core-api pins `redis[hiredis]==8.0.1` — installing arq downgrades redis and breaks core-api. Verified against PyPI metadata and reproduced with `pip install arq`. `taskiq-redis 1.2.3` requires `redis<9,>=8.0.0`, which matches the existing pin exactly. See "Scheduling decision" below. |
| `onnxruntime` | 1.28.0 | Detector inference (CPU EP) | Production inference. No torch in this image. |
| `supervision` | 0.30.0 | `PolygonZone` occupancy, NMS, annotation | Zone logic + generating the marked-up evidence images the nazoratchi reviews. |
| `opencv-python-headless` | **4.14.0.94** (2026-07-28) | Image decode/resize/crop, reference-frame differencing | **`-headless`** = no GTK/X11 in the container (≈70 MB smaller, no missing-`libGL` crash). **Not 5.0.0.93** — OpenCV 5.0 shipped 2026-07-02 with API breaks; 4.14 was released 3 weeks *later*, so 4.x is still the actively maintained line. |
| `numpy` | 2.5.1 | Array math | Transitive. Requires Python ≥3.12 — another reason for 3.13. |
| `Pillow` | 12.3.0 | JPEG re-encode for the 90-day → 1-year compression policy (spec §5) | Cheaper than OpenCV for pure re-encode; controls quality/subsampling precisely. |
| `aiobotocore` | **3.9.0** | Async S3 puts of snapshots | Non-blocking upload inside the taskiq worker. **Not `aioboto3`** — see the core-api table: its `aiobotocore[boto3]==2.25.1` pin is incompatible with the project's `boto3`, and it has been unreleased since 2025-10-30. |

#### Backend — CV training (separate image, rented GPU, month 2)

| Library | Version | Purpose |
|---------|---------|---------|
| `rfdetr[train,onnx]` | 1.9.1 | Fine-tune on Karmana HITL-labelled data, then export ONNX |
| `torch` / `torchvision` | 2.13.0 / 0.28.0 | Training backend (**never in the production image**) |
| `transformers` | 5.14.1 | Backbone weights loader (rfdetr requires `>=5.1,<6`) |
| `albumentations` | via `rfdetr[train]` | Augmentation — critical for 06:00 low-light / IR-mode robustness (spec §10 risk #1) |
| `timm` | 1.0.28 (Apache-2.0) | **v2 accuracy lever:** per-zone-crop binary classifier (occupied/empty). Often beats detection for "is this table covered in goods" and trains on far less data. Keep in your back pocket for the ≥95% month-2 target. |

#### Backend — bot-service

| Library | Version | Purpose | Notes |
|---------|---------|---------|-------|
| `aiogram[fast,redis,i18n]` | 3.30.0 | Both bots | `fast` → aiodns + uvloop; `redis` → FSM storage; `i18n` → Babel |
| `redis[hiredis]` | **7.4.1 — NOT 8.x** | aiogram RedisStorage | aiogram 3.30 pins `redis[hiredis]<8,>=6.2.0`. Verified. |
| `Babel` | 2.18.0 | Bot-side translations | CLDR has `uz`, `uz_Cyrl`, `uz_Latn`, `ru`. Bot strings must match the web locales — keep one glossary. |

#### Frontend

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `next-intl` | 4.13.4 | i18n routing, ICU messages, date/number formats | Node 24 ships full ICU → `uz-Latn-UZ` / `uz-Cyrl-UZ` / `ru-UZ` formatting works natively. |
| `react-konva` + `konva` | 19.2.5 + 10.3.0 | Polygon zone editor, plan-map | Camera-zone drawing (wizard step 6), market map with colour-coded stalls (spec §7) |
| `@tanstack/react-query` | 5.101.4 | Server state, caching, optimistic updates | The cashier's ≤3-tap flow needs optimistic payment writes. |
| `zod` | 4.4.3 | Runtime schema validation | Share shapes with FastAPI's OpenAPI output. |
| `react-hook-form` + `@hookform/resolvers` | 7.83.0 + 5.5.7 | The 7-step wizard, tariff forms | Uncontrolled inputs → no re-render storms in long forms. |
| `tailwind-merge` / `clsx` / `class-variance-authority` | 3.6.0 / 2.1.1 / 0.7.1 | Component variants (shadcn/ui pattern) | Build the design system once (spec §7). |
| `@radix-ui/*` | 1.1.x | Accessible unstyled primitives | Dialog, Popover, Select, Tabs — Apple-minimal styling on top. |
| `lucide-react` | 1.27.0 (ISC) | Icons | Consistent line-icon set, tree-shakeable. |
| `recharts` | 3.10.1 | Revenue / occupancy charts | Director dashboard. |
| `sonner` | 2.0.7 | Toasts | Cashier confirmation feedback. |
| `date-fns` | 4.4.0 | Date math with tz support | v4 has first-class time-zone support. Format via `next-intl` for display. |
| `nuqs` | 2.9.2 | URL-synced filter state | Report date-range/market filters become shareable links. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| **uv 0.11.33** | Python deps, lock, venv, Docker layer caching | `uv sync --frozen --no-dev` in the runtime stage. One `pyproject.toml` **per service** — mandatory here (see compat table). |
| **ruff 0.16.0** | Lint + format (replaces black, isort, flake8, pyupgrade) | One tool, one config in `pyproject.toml`. Enable `E,F,I,UP,B,SIM,ASYNC,S`. |
| **mypy 2.3.0** | Static typing | `strict = true` on new code. SQLAlchemy 2.0's `Mapped[]` gives real ORM typing. |
| **pytest 9.1.1** + `pytest-asyncio 1.4.0` + `pytest-cov 7.1.0` | Tests | `asyncio_mode = "auto"`. |
| **testcontainers 4.15.0** | Real Postgres + Valkey in CI | **Do not test multi-tenant RLS against SQLite** — RLS only exists in Postgres, so SQLite tests give false green on your most dangerous code path. |
| **restic 0.19.1** | Encrypted, deduplicated offsite backups | BSD-2. `pg_dump -Fc` + snapshot archive → offsite bucket. Built-in `restic check --read-data-subset` for the mandatory restore drill (spec §5). |
| **rclone** (latest) | Bulk S3↔S3 archive sync | For the SeaweedFS → offsite mirror and for the eventual Uzbekistan migration. |
| **wg-easy 15.3.0** | WireGuard config UI | Optional; plain `wg-quick` is fine if nobody needs a GUI. |
| **Certbot** | Let's Encrypt | `--webroot` via the nginx container, renew via a cron/systemd timer on the host. |

## Installation

# ---------- core-api (uv, Python 3.13) ----------

# ---------- cv-service (Python 3.13, NO torch) ----------

# ---------- bot-service (NOTE the pins) ----------

# ---------- cv-train (separate image, GPU box only) ----------

# ---------- frontend ----------

## Key decisions explained

### Object storage: MinIO → SeaweedFS

| Option | License | Verdict |
|---|---|---|
| **SeaweedFS 4.40** | Apache-2.0 | **Recommended.** Single container `weed server -s3 -dir=/data -master.volumeSizeLimitMB=1024`. 33.7k stars, released 9 days ago. Optimised for exactly your access pattern (many small objects). Version-tagged Docker images. |
| Garage v2.3.0 | AGPL-3.0 | Good alternative — simplest config of the three, purpose-built for small self-hosted S3. Two frictions: AGPL reintroduces the license conversation you're trying to avoid, and Docker Hub tags are commit hashes (awkward to pin). |
| RustFS 1.0.0-beta.11 | Apache-2.0 | **Do not use.** Still pre-release as of 2026-07-23; maintainers say "do NOT use in production"; distributed mode untested. Revisit post-GA — it can read a MinIO data directory in place. |
| MinIO pinned `RELEASE.2025-10-15` | AGPL-3.0 | Emergency bridge only. No patches. Set a hard removal date. |
| Plain filesystem + FastAPI serving | n/a | Genuinely viable at 175 files/day, but you lose the S3 abstraction that makes the Uzbekistan-hosting migration cheap. Not worth it. |

### Snapshot capture: go2rtc first, ISAPI second, ffmpeg third

| Method | How | When |
|---|---|---|
| **1. go2rtc `/api/frame.jpeg`** | `GET http://go2rtc:1984/api/frame.jpeg?src=cam_07` | **Default.** go2rtc holds the RTSP session open, so this is an HTTP GET with no handshake/keyframe wait. Supports `w`/`h` resize and `cache=` server-side. Zero subprocess management. Same component already required for live view. |
| **2. Hikvision ISAPI** | `GET http://<nvr>/ISAPI/Streaming/channels/<ch>01/picture` with `httpx.DigestAuth` | Fallback and cross-check. Full-resolution JPEG straight off the NVR, no decode at all. **Gotchas:** Digest auth fails if NVR clock drift >5 min — NTP the NVR during onboarding; some firmware needs Web-auth set to `digest/basic`, not `digest` only. Channel numbering is `<camera>01` = main stream, `<camera>02` = sub-stream. |
| **3. ffmpeg one-shot** | `ffmpeg -rtsp_transport tcp -i rtsp://… -frames:v 1 -q:v 2 out.jpg` | Last resort / diagnostics. Costs a full RTSP handshake + I-frame wait (3–10 s) per snapshot and needs subprocess timeout hygiene. |
| ~~ONVIF `GetSnapshotUri`~~ | `onvif-zeep-async` 4.2.1 | **Not for snapshots.** Adds a SOAP round-trip to discover a URI that Hikvision exposes directly via ISAPI. `onvif-zeep` (0.2.12) is stale; the async fork is Home-Assistant-maintained. Use ONVIF only if you later need auto-discovery of unknown-brand cameras. |

### Scheduling: taskiq, not arq (uninstallable), not APScheduler, not Celery

| Option | Verdict |
|---|---|
| **taskiq 0.12.4 + taskiq-redis 1.2.3** | **Recommended (changed 2026-08-02).** Requires `redis<9,>=8.0.0` — matches core-api's `redis[hiredis]==8.0.1` pin exactly. Actively developed (pushed 2026-07-24). Bigger abstraction surface than arq (brokers, middlewares, result backends, separate scheduler process) — accept that cost; it is the only asyncio-native queue that installs in this dependency set. |
| ~~arq 0.28.0~~ | **UNINSTALLABLE — do not attempt.** Declares `redis[hiredis]<6,>=4.2.0`; core-api pins `redis[hiredis]==8.0.1`. `pip install arq` silently uninstalls redis 8.x and installs 5.3.1, breaking core-api. Confirmed against PyPI metadata 2026-08-02. Its design was the better fit (~2k LOC, `max_tries` + `Retry(defer=…)`, built-in `cron()`), but that is irrelevant if it cannot coexist with the pinned client. |
| APScheduler **3.11.3** | It is a *scheduler*, not a queue: no durable retry, no job-result history, a job missed during a restart is simply gone. **4.0 — which fixes this — is still `4.0.0a6` from April 2025 and the maintainer explicitly says not for production.** Acceptable only if you want to cut a dependency and accept application-level retry via `tenacity`. |
| Celery 5.6.3 + beat | Three processes (worker + beat + broker) and a sync-first design that fights FastAPI/httpx async code. Massive overkill for 175 jobs/day. **Reject.** |
| taskiq 0.12.4 (+ taskiq-redis 1.2.3) | Closest competitor, more actively developed than arq (pushed 2026-07-24). Bigger abstraction surface (brokers, middlewares, result backends, separate scheduler process). **Switch to this if arq goes quiet.** |

### CV: RF-DETR + ONNX Runtime

| Model | License (code / weights) | Activity | Verdict |
|---|---|---|---|
| **RF-DETR** (`roboflow/rf-detr`) | Apache-2.0 / **Apache-2.0 (Nano→Large)** | pushed 2026-08-04 | **Recommended.** Maintained pip package (`rfdetr` **1.9.1**), first-class `model.export(format="onnx")`, same vendor as `supervision`. **XLarge/2XLarge are PML 1.0** — but since 1.9.x they live in the separate `rfdetr-plus` distribution behind the `[plus]` extra, so the ban is enforceable by a lockfile test rather than by remembering. |
| D-FINE (`Peterande/D-FINE`) | Apache-2.0 / Apache-2.0 | 3.3k★, pushed 2026-07-09 | Excellent accuracy, genuinely license-clean. But it is a research repo — fine-tuning ergonomics are config-file archaeology, not a 2-person-team-friendly API. Good **fallback** if RF-DETR underperforms on your data. |
| RT-DETR (`lyuwenyu/RT-DETR`) | Apache-2.0 / Apache-2.0 | 5.4k★, pushed 2026-06-15 | The ancestor. Superseded by both of the above. No reason to pick it in 2026. |
| YOLOX | Apache-2.0 / Apache-2.0 | 10.6k★, **last push 2025-06-08** | Effectively frozen for 14 months; older architecture, lower mAP. Only if you need its specific ONNX/ncnn/OpenVINO export zoo. |
| **Ultralytics YOLO (any version)** | **AGPL-3.0** | — | **FORBIDDEN.** Per PROJECT.md constraint. AGPL over a network service means source disclosure or a paid commercial licence. Note: `supervision` is MIT and safe — just never import `ultralytics` alongside it, and never `pip install ultralytics` "just to test". |

- **Not OpenVINO** (2026.2.1): its advantage is Intel-specific (VNNI/AMX kernel paths). **Contabo VPS runs AMD EPYC.** On AMD you get little or none of that benefit while adding a large dependency. If you ever move to an Intel host and CPU time becomes a bottleneck, re-benchmark then.
- **Not torch CPU in production**: torch 2.13 is an ~800 MB install vs onnxruntime's ~15 MB. Keeping torch out of the cv-service image shrinks build time, image size, attack surface, and Contabo disk usage. torch belongs only in the training image.
- ONNX Runtime 1.28.0 CPU EP (MLAS) is vendor-neutral and RF-DETR exports to a single `.onnx`. Set `sess_options.intra_op_num_threads` to ≈vCPU count and use `providers=["CPUExecutionProvider"]` explicitly.

### Multi-tenancy: Postgres RLS, not `.where(market_id == …)` discipline

### WireGuard: split-tunnel only

- VPS runs the WireGuard "server" peer (`wg-easy 15.3.0` if you want a UI, otherwise plain `wg-quick`).
- Market side: a small always-on device (mini-PC or OpenWrt router) with `PersistentKeepalive = 25`.
- **`AllowedIPs` on the VPS peer must be only the NVR subnet** (e.g. `192.168.1.0/24`), never `0.0.0.0/0`. A full tunnel routes *all* VPS egress through the market's DSL — Telegram, Let's Encrypt, and your users' traffic all die together.
- Containers that need NVR reach: `go2rtc` (and `cv-service` only if you use the ISAPI fallback). Everything else stays off the VPN.
- Docker: WireGuard in a `network_mode: host` sidecar with `NET_ADMIN` + `/lib/modules` mounted so it uses the host kernel module rather than userspace.
- NVR is never port-forwarded to the internet (spec §5). RTSP credentials Fernet-encrypted in Postgres.

### Backups

- **Nightly** `pg_dump -Fc` → **restic 0.19.1** repo on an *offsite* bucket (Backblaze B2 or a second Contabo region — must be a different failure domain than the VPS).
- Snapshot archive: `restic backup` or `rclone sync` of the SeaweedFS volume to the same offsite bucket.
- Retention: `restic forget --keep-daily 14 --keep-weekly 8 --keep-monthly 12 --prune`.
- **Restore drill is a deliverable, not a nice-to-have** (spec §5 says so). `restic check --read-data-subset=5%` weekly + one full documented restore before go-live.
- Backup failure → Telegram alert (spec §5 monitoring). Alert on *absence* of a success signal, not just on error exit codes.
- Add PG WAL archiving (or graduate to pgBackRest) only if you later need RPO < 24 h.

### i18n practicalities for uz-Latn / uz-Cyrl / ru

- Node 24 ships full ICU, so `Intl.DateTimeFormat('uz-Cyrl-UZ')` and `uz-Latn-UZ` work without `full-icu`. Python-side, Babel 2.18 carries CLDR `uz`, `uz_Cyrl`, `uz_Latn`.
- **Uzbek Latin↔Cyrillic is very nearly a deterministic transliteration.** Write a build-time script that generates `uz-Cyrl.json` from `uz-Latn.json` and hand-corrects the small ambiguity set (е/э, ь, borrowed words). This cuts your translation surface by a third and keeps the two Uzbek locales from drifting.
- URL locale segments: keep them short (`/uz`, `/uz-cyrl`, `/ru`) and map them to full ICU tags in `defineRouting` — don't put `uz-Latn-UZ` in URLs.

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| SeaweedFS 4.40 | Garage v2.3.0 | You want the simplest possible config and AGPL is genuinely a non-issue for you (it is a separate unmodified network service — the same posture as Postgres). |
| SeaweedFS 4.40 | RustFS | After it reaches 1.0 GA. Its in-place MinIO-data-directory read makes it a compelling later migration. |
| Valkey 9.1.1 | Redis 8.8.1 | You need a Redis-8-only feature or want the official Redis image. Legally fine (AGPLv3 as a separate unmodified service); Valkey just avoids the discussion. |
| arq 0.28.0 | taskiq 0.12.4 + taskiq-redis | arq's release cadence stalls, or you want richer middleware/result-backend abstractions. |
| arq 0.28.0 | APScheduler 3.11.3 + tenacity | You want one fewer moving part and accept losing durable retry + job history. Revisit if APScheduler 4.0 ever ships stable. |
| ONNX Runtime CPU | OpenVINO 2026.2.1 | You move to an **Intel** host *and* CPU time actually becomes a constraint. Re-benchmark before adding it — do not add it speculatively. |
| RF-DETR-Small | RF-DETR-Large | Accuracy testing on Karmana data favours it. You have ~40× the CPU headroom needed. |
| RF-DETR | D-FINE | RF-DETR underperforms after fine-tuning on your data. Equally license-clean, harder tooling. |
| PyJWT 2.13.0 | Authlib 1.7.2 / joserfc 1.7.4 | You add third-party OAuth/OIDC login, or need asymmetric JWKS rotation across services. |
| XlsxWriter 3.2.9 | openpyxl 3.1.5 | You need to *read* or edit existing `.xlsx` (e.g. importing the administration's legacy revenue spreadsheets during the 2-week baseline measurement — this may actually happen). Then use both. |
| Nginx 1.30.4 + certbot | Caddy 2.11.4 | You want automatic HTTPS with zero certbot cron/renewal ops. Saves real days of setup. The only reason to keep Nginx is team familiarity and the fixed constraint — if neither binds, Caddy is objectively less work here. |
| react-konva | Plain SVG | Only for the *schematic* early version of the plan-map (spec §10 explicitly allows this). Migrate to Konva before real stall counts. |
| TypeScript 5.9.3 | TypeScript 7.0.2 | After Next.js ships stable (non-experimental) TS 7 support and TS 7.1 lands the programmatic API. Post-launch. |
| Uvicorn 0.51.0 | Granian 2.7.9 | Measured throughput problems under load. Unlikely at this scale. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| **Ultralytics YOLO** (all versions, incl. YOLO11/YOLO26) | **AGPL-3.0** — network-service source disclosure or a paid commercial licence. Hard project constraint. | RF-DETR 1.8.3 (Apache-2.0 code + weights) |
| **RF-DETR XLarge / 2XLarge** | **PML 1.0**, not Apache-2.0, gated behind `rfdetr[plus]`. Easy to grab by accident. | RF-DETR Nano/Small/Medium/**Large** only |
| **MinIO** (server) | Repo **archived 2026-04-25**, read-only, no further security patches. Storing personal data on an abandoned daemon. | SeaweedFS 4.40 |
| **`minio-py` SDK** | Couples you to one vendor's client and to a dead server. | `aiobotocore` against the S3 API |
| **`aioboto3`** (any version) | 15.5.0 hard-pins `aiobotocore[boto3]==2.25.1`, which downgrades `boto3` below this project's pin — the combination is uninstallable. Unreleased since 2025-10-30. Confirmed against PyPI 2026-08-04. | `aiobotocore` 3.9.0 |
| **passlib** | Last release **2020-10-08**; unmaintained; imports the `crypt` stdlib module **removed in Python 3.13** — it will not import on your runtime. Still recommended by stale FastAPI tutorials. | `pwdlib[argon2]` 0.3.0 |
| **python-jose** | Last release 2025-05-28; effectively unmaintained; has a history of unpatched CVEs. Also common in old tutorials. | `PyJWT` 2.13.0 |
| **APScheduler 4.x** | Still `4.0.0a6` (April 2025). Maintainer: "should NOT be used in production", may break without a migration path. | arq 0.28.0 (or APScheduler 3.11.3) |
| **Celery + beat** | Sync-first, three processes, poor asyncio interop with FastAPI, ~800 open issues. Wildly oversized for 175 jobs/day. | arq 0.28.0 |
| **OpenCV 5.0.0.93** | Released 2026-07-02 with API breaks; the 4.x line got a *newer* release (4.14.0.94, 2026-07-28), i.e. 4.x is still the maintained line. | `opencv-python-headless==4.14.0.94` |
| **`opencv-python`** (non-headless) | Pulls GTK/X11/libGL into the container; +70 MB and the classic `ImportError: libGL.so.1` in slim images. | `opencv-python-headless` |
| **torch in the cv-service production image** | ~800 MB for inference that ONNX Runtime does in 15 MB. Bloats builds and Contabo disk. | `onnxruntime` in prod; torch only in the training image |
| **react-leaflet 5.0.0** | Licensed **Hippocratic-2.1** — *not* OSI-approved, imposes ethical-use conditions. A real problem for a commercial SaaS that may go government-facing. | react-konva (MIT) for plan-map; MapLibre GL JS (BSD-3) if you ever need real geo maps |
| **TypeScript 7.0.2** (for this MVP) | Next.js 16 support is preview-only behind `experimental.useTypeScriptCli`; no stable programmatic API until 7.1. | TypeScript 5.9.3 |
| **`middleware.ts`** in Next 16 | Renamed to **`proxy.ts`** (Node runtime only, no Edge). Every online next-intl tutorial is now wrong; this silently breaks locale routing. | `proxy.ts` exporting `export default async function proxy(request)` |
| **PostgreSQL 19** | Still `19beta2`. | `postgres:18.4-trixie` |
| **SQLite for tests** | RLS does not exist in SQLite — your multi-tenant isolation tests would pass while the real behaviour is untested. | testcontainers + real `postgres:18.4` |
| **`float` for money** | Rounding drift in daily patta aggregates → disputes with vendors, which is the exact failure mode this product exists to prevent. | `BIGINT` so'm ↔ Python `int` (per spec §6) |
| **Naive datetimes** | UTC↔Asia/Tashkent (+5, no DST) boundary bugs put a snapshot on the wrong billing day. | `TIMESTAMPTZ` in PG, `datetime` with `ZoneInfo`, `tzdata` installed |

## Stack Patterns by Variant

- `nginx:1.30.4-alpine` + certbot `--webroot`, renewal timer on the host
- go2rtc WebRTC needs **UDP 8555** open directly (it does not traverse an HTTP proxy). Proxy only go2rtc's HTTP API/HLS through Nginx; expose 8555/udp at the firewall, or fall back to HLS/MSE which does proxy cleanly.
- Swap to `caddy:2.11.4` — automatic ACME issuance and renewal, ~10 lines of Caddyfile, no cron. The only cost is unfamiliarity.
- Move go2rtc + a tiny capture agent onto the market-side mini-PC; push JPEGs *up* to the VPS instead of pulling RTSP *down*. Same go2rtc, inverted direction, far more tolerant of jitter. The arq job then becomes "verify a snapshot arrived", and a missing one raises the existing alert.
- No code change (RLS + `market_id`), but give each market its own go2rtc instance and its own WireGuard peer. Keep one cv-service worker pool — 175 frames/day/market means one VPS carries dozens of markets.
- Add the `timm` per-zone-crop binary classifier as a second stage behind RF-DETR. Trains on the HITL dataset you are already collecting, needs far less data than detection fine-tuning, and runs in milliseconds on the small crops.

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| `arq 0.28.0` | `redis[hiredis] >=4.2.0,<6` | **HARD CONFLICT — arq is unusable in this project.** core-api pins `redis[hiredis]==8.0.1`; installing arq downgrades it to 5.3.1 and breaks core-api. Verified against PyPI metadata 2026-08-02 and reproduced with a real install. Use `taskiq` + `taskiq-redis 1.2.3` (requires `redis<9,>=8.0.0` — matches exactly). |
| `aiogram 3.30.0` | `pydantic >=2.4.1,<2.14` | **Hard cap.** Pydantic 2.13.4 is fine today; when 2.14 ships, core-api can move but bot-service cannot. **Isolate service dependency sets** — one `pyproject.toml` + `uv.lock` per service. Verified from aiogram 3.30.0 metadata. |
| `aiogram[redis] 3.30.0` | `redis[hiredis] >=6.2.0,<8` | **Conflicts with redis-py 8.0.1.** Pin `redis>=7.4,<8` in bot-service; use 8.0.1 in core-api/cv-service. Verified from aiogram 3.30.0 metadata. |
| `aiogram 3.30.0` | Python `>=3.10,<3.15` | Python 3.13 is inside the window. |
| `react-konva 19.2.5` | `react ^19.2.0`, `react-dom ^19.2.0`, `konva ^10.0.0` | Exact-ish peer. React 19.2.8 ✓. A future React 20 will require a react-konva major. |
| `next-intl 4.13.4` | `next ^12 \|\| ^13 \|\| ^14 \|\| ^15 \|\| ^16` | Next 16 supported. Requires `proxy.ts` (not `middleware.ts`). |
| `numpy 2.5.1` | Python `>=3.12` | Blocks Python 3.11 for cv-service. |
| `onnxruntime 1.28.0` | Python 3.11–3.14 (manylinux_2_28 x86_64) | cp313 wheel verified present. Needs glibc ≥ 2.28 — `python:3.13-slim-trixie` is fine; **Alpine/musl has no wheel** (would build from source). Use Debian-slim base images. |
| `rfdetr 1.9.1` | `torch` (**mandatory, not an extra**), `transformers >=5.1,<6`, `supervision`, `pydantic >=2,<3` | **Training image only — and that is now a hard rule, not a preference.** Because `torch` is a required dependency, installing `rfdetr` anywhere drags ~800 MB of torch in. The production `cv-service` image ships `onnxruntime` + a prebuilt `.onnx` and never installs `rfdetr` at all. Licence: the PML variants live in the separate `rfdetr-plus` distribution behind the `[plus]` extra, so a lockfile assertion enforces the ban. |
| `supervision 0.30.0` | numpy 2.x, Python >=3.9 | MIT. Safe next to onnxruntime; do **not** install `ultralytics` for its optional adapters. |
| `SQLAlchemy 2.0.51` | `asyncpg 0.31.0`, `psycopg 3.3.4`, `alembic 1.18.5`, `greenlet 3.5.4` | `sqlalchemy[asyncio]` pulls greenlet. Alembic needs a sync path — either a `psycopg` URL or `connection.run_sync`. |
| `alembic-utils 0.8.8` | `alembic 1.18.x`, `SQLAlchemy 2.0.x` | Lower star-count/maintenance than core Alembic — if it lags, write RLS policies as raw `op.execute()` in migrations. Low switching cost. |
| `Tailwind 4.3.3` | `next 16.2.x` via `@tailwindcss/postcss@4.3.3` | v4 is CSS-first: `@import "tailwindcss"` + `@theme {}`; there is no `tailwind.config.js`. |
| `Node 24.18.0 LTS` | `next 16.2.12` | Node 26 becomes LTS 2026-10-28 — *after* your 2026-10-18 go-live. Stay on 24 (LTS until 2028-04). Full ICU included → `uz-Cyrl-UZ` formatting works. |
| `postgres:18.4` | `asyncpg 0.31.0`, `psycopg 3.3.4` | Both support PG 18 protocol/features. |
| `Valkey 9.1.1` | `redis-py 8.0.1` / `7.4.1` | RESP-compatible; the Python client needs no change. |

## Sources

- PyPI JSON API — exact versions, release dates, `requires_python`, `requires_dist`, license classifiers, and wheel filename/ABI tags for every Python package named above
- npm registry API — versions, licenses, and `peerDependencies` for every JS package named above
- GitHub REST API — `archived`, `pushed_at`, `license.spdx_id`, stars, and latest release tags for: `minio/minio` (**archived: true**), `roboflow/rf-detr`, `Peterande/D-FINE`, `lyuwenyu/RT-DETR`, `Megvii-BaseDetection/YOLOX`, `roboflow/supervision`, `seaweedfs/seaweedfs`, `deuxfleurs-org/garage`, `rustfs/rustfs`, `AlexxIT/go2rtc`, `python-arq/arq`, `taskiq-python/taskiq`, `agronholm/apscheduler`, `wg-easy/wg-easy`, `caddyserver/caddy`, `astral-sh/uv`, `restic/restic`
- Docker Hub API — available/pinnable tags for postgres, redis, valkey, nginx, seaweedfs, garage
- endoflife.date API — Python, PostgreSQL, Redis, Node.js, Nginx support windows
- https://rfdetr.roboflow.com/latest/ — model variant table, resolutions, COCO mAP, and the verbatim license split ("Core models (Nano through Large) and all code are released under the Apache 2.0 license; XL and 2XLarge detection models require `rfdetr[plus]` and are provided under PML 1.0"), ONNX export
- https://go2rtc.org/internal/mjpeg/ and `AlexxIT/go2rtc` `internal/mjpeg/README.md` — `/api/frame.jpeg?src=` parameters (`w`, `h`, `rotate`, `hw`, `cache`)
- https://nextjs.org/docs/messages/middleware-to-proxy and https://nextjs.org/docs/app/guides/upgrading/version-16 — middleware→proxy rename, Node-only runtime
- https://devblogs.microsoft.com/typescript/announcing-typescript-7-0-rc/ + `vercel/next.js` Discussion #95633 — TS 7.0 GA 2026-07-08; Next.js support preview-only behind `experimental.useTypeScriptCli`
- https://apscheduler.readthedocs.io/en/master/migration.html + `agronholm/apscheduler` #465 — 4.0 pre-release status and the "not for production" statement
- https://supervision.roboflow.com/detection/tools/polygon_zone/ and .../notebooks/occupancy_analytics/ — PolygonZone API and the occupancy pattern
- Context7 `/websites/next-intl_dev` — Next 16 `proxy.ts` integration, `defineRouting`, matcher config
- https://fastapi-users.github.io/fastapi-users/ v13 release notes — passlib → pwdlib/Argon2 migration
- MinIO community-edition timeline (May 2025 console strip → Dec 2025 maintenance mode → Apr 2026 archive) — corroborated across itsfoss, elest.io, bizety, stormdevelopments **and confirmed directly** by the GitHub API `archived: true` flag
- RustFS production-readiness ("do NOT use in production", GA target July 2026) — corroborated by sealos.io, elest.io, lowcloud + confirmed by PyPI/GitHub showing only `1.0.0-beta.11` prereleases
- Hikvision ISAPI `/ISAPI/Streaming/channels/<ch>01/picture` behaviour, Digest-auth clock-drift sensitivity (>5 min), digest/basic setting — IPCamTalk, Visiotech support, Hikvision Europe integration PDF, `uchkunr/hikvision-best-practices`
- RF-DETR CPU ONNX latency (~74 ms @384² on Intel Core Ultra 9; ~180 ms for Nano @320² elsewhere) — `K4HVH/rf-detr-ort` benchmarks + community reports. Treat as order-of-magnitude, **not** as a Contabo/EPYC number. **Benchmark on the actual VPS in the CV phase.**
- Contabo VPS = AMD EPYC (incl. Turin/Zen 5 on newer plans) — Contabo blog + VPSBenchmarks CPU listings
- Postgres RLS multi-tenant pattern (`SET LOCAL` + `FORCE ROW LEVEL SECURITY`) — Crunchy Data, plus several 2026 practitioner writeups
- Exact RF-DETR-Small vs -Large latency and accuracy **on Karmana imagery** — must be measured, not assumed
- Whether the Karmana Hikvision NVR firmware exposes ISAPI `/picture` on all 20–25 channels and accepts sub-stream snapshots — verify during week 1–2 NVR access (spec §8)
- Whether go2rtc can hold 25 concurrent persistent RTSP sessions against this NVR without hitting its per-client connection limit — Hikvision NVRs cap simultaneous streams (often 6–16 for remote clients). **This is a real week-5–6 risk**: if capped, use sub-streams for go2rtc and ISAPI-pull for snapshots, or stagger connections.
- `alembic-utils` long-term maintenance — low switching cost (raw `op.execute()`), but worth a glance before committing

<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->

## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->

## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->

## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, `.github/skills/`, or `.codex/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->

## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:

- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->

## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
