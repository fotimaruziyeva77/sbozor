# Phase 4: Snapshot pipeline — Pattern Map

**Mapped:** 2026-08-04
**Files analyzed:** 58 (yangi yoki o'zgaradigan)
**Analogs found:** 47 / 58 (11 tasi uchun **analog yo'q** — §4 ga qarang)

> **Bu hujjatning maqsadi:** ijrochi naqsh o'ylab topmasin — u quyidagi aniq `fayl:qator`
> dan nusxa olsin. Kod parchalari **verbatim** (o'zgartirilmagan, 2026-08-04 holatiga);
> izohlar o'zbekcha.
>
> **3-FAZADAN FARQI — BU FAZADA ANALOG DEYARLI HAMMA NARSAGA BOR.**
> 3-faza chiquvchi HTTP klientini, fon-vazifa navbatini va sirni shifrlashni **birinchi
> marta** olib kelgan edi; uchalasi ham endi mavjud va o'lchangan. Shuning uchun bu
> hujjat "qayerdan nusxa olish" dan ko'ra **"analog qayerda tugaydi"** ni aniqroq
> ko'rsatadi.
>
> **BESH SHAKLNING ANALOGI YO'Q VA ULAR SOXTA ANALOG BILAN TO'LDIRILMAYDI:**
> `SELECT … FOR UPDATE SKIP LOCKED` + lease (§4.1), obyekt-ombor / S3 (§4.2),
> tasvir bilan ishlash — `Pillow` (§4.3), `taskiq` **planeri** (broker bor, planer
> yo'q — §4.4), Telegram jo'natuvchisi (§4.5).
>
> **Eng xavfli to'rt joy** (noto'g'ri qilinsa 1–3 fazalarning kafolatlari buziladi):
> §S-1 (tenant jadvali besh joyda), §S-3 (tick tenant kontekstini O'ZI o'rnatadi —
> Pitfall 13 ning takrori), §S-6 (`is_billable` ilgagi — kelishuv emas, tuzilma),
> §S-9 (sir bilan ishlashning to'rt yopiq yuzasi meros olinadi).

---

## 0. Umumiy majburiy konventsiyalar (hamma fayl uchun)

| Qoida | Manba | Buzilsa nima bo'ladi |
|-------|-------|----------------------|
| Har bir modul **fayl-darajasidagi docstring** bilan boshlanadi va u "nega shunday" ni tushuntiradi | `app/jobs/discovery.py:1-66`, `app/worker.py:1-51` | Kod review'dan o'tmaydi — bu repoda izoh ixtiyoriy emas |
| Izohlar, docstring'lar, xato matnlari — **o'zbek tilida (uz-Latn)** | butun 1–3 faza kodi | Uslub ajralib qoladi |
| Python: `from __future__ import annotations` birinchi import | har bir `.py` (`discovery.py:68`) | ruff/mypy konfiguratsiyasi shuni kutadi |
| Python: `__all__` aniq e'lon qilinadi | `discovery.py:94-101`, `worker.py:74`, `live_source.py:63-69` | Import yuzasi nazoratsiz kengayadi |
| Python: `if TYPE_CHECKING:` bloki faqat tip importlari uchun | `discovery.py:86-90`, `worker.py:69-70` | Runtime import zanjiri og'irlashadi |
| Backend `import` tartibi: stdlib → uchinchi tomon (`sbozor_core` shu yerda) → `app.*` | `discovery.py:68-90` | ruff `I` qoidasi qizaradi |
| ruff `select = ["E","F","I","UP","B","SIM","ASYNC","S"]`, `line-length = 100`, `target py313` | `pyproject.toml` | CI `npm run lint` da qizaradi |
| mypy `strict = true` | `pyproject.toml` | Yangi kod tiplanmasa CI qizaradi |
| Vaqt: `timestamptz` + `ZoneInfo("Asia/Tashkent")`; naive `datetime` **TAQIQ** | `sbozor_core/timeutil.py:44-62` | `ValueError` |
| Biznes-kun **DB'da hisoblanadi** (`GENERATED … STORED`), ilovada takrorlanmaydi | `timeutil.py:1-21` (qamrov ogohlantirishi) | Yarim tun atrofida ikki manba bir kun farq qiladi |
| Pul: bu fazada pul ustuni **YO'Q** — `FINANCIAL_TABLES` ga birorta jadval qo'shilmaydi | `schema_contract.py:85-91` (3-fazada aynan shu band yozilgan) | Meta-test soxta `amount_soum` talab qilib qoladi |
| Sir **nomlangan kalit** sifatida uzatiladi, `event` matniga qo'shilmaydi | `sbozor_core/logging.py:96-109` | `censor_secrets` uni ko'rmaydi va parol Sentry'ga chiqadi |
| Sir tashuvchi tip — **`SecretStr`**, oddiy `str` emas | `live_source.py:51-54`, `go2rtc.py:246-249` | `repr()` istisno matnida, pytest diffida, Sentry lokal o'zgaruvchilarida chiqadi |
| Yangi `detail` kodi **uch joyda** e'lon qilinadi | `app/schemas.py:490+` · `frontend/src/lib/api-types.ts:1019+` · uchala `messages/*.json` | `error-codes.test.mjs` qizaradi yoki foydalanuvchi umumiy xato ko'radi |
| Chiquvchi HTTP chaqiruvida `timeout` **HAR DOIM** beriladi | `go2rtc.py:109-117`, `isapi/client.py` timeout byudjeti | Job osilib qoladi, `--workers 1` ostida butun jarayon bloklanadi |
| Frontend: `AGENTS.md` majburiyati — **Next.js 16 hujjatini `node_modules/next/dist/docs/` dan o'qing** yozishdan oldin | `frontend/AGENTS.md` | `middleware.ts` kabi eskirgan API ishlatiladi |

---

## 1. File Classification

### 1.1 Backend — sxema qatlami

| Yangi/o'zgaradigan fayl | Rol | Data flow | Eng yaqin analog | Moslik |
|-------------------------|-----|-----------|------------------|--------|
| `packages/sbozor-core/sbozor_core/models/snapshot.py` | model | CRUD + event-log | `packages/sbozor-core/sbozor_core/models/nvr.py` (to'liq shablon) | **exact** |
| `packages/sbozor-core/sbozor_core/models/__init__.py` (MOD) | model-barrel | — | o'zi | **exact** |
| `packages/sbozor-core/sbozor_core/enums.py` (MOD — `CaptureRunStatus`, `SnapshotQuality`, `SnapshotLightMode`, `SnapshotTier`) | enum/config | — | o'zi (`CameraStatus:87`, `DiscoveryRunStatus:116`) | **exact** |
| `packages/sbozor-core/sbozor_core/schema_contract.py` (MOD — `AUDITED_TABLES`) | config/registry | — | o'zi (`AUDITED_TABLES:93-167`) | **exact** |
| `migrations/entities/__init__.py` (MOD — `SNAPSHOT_TENANT_TABLES` + `SNAPSHOT_AUDITED_TABLES`) | registry | — | o'zi (`NVR_TENANT_TABLES:133-181`) | **exact** |
| `migrations/versions/0014_snapshot_domain.py` | migration | DDL + RLS + audit | `migrations/versions/0012_nvr_domain.py` | **exact** |
| `migrations/versions/0015_market_delete_snapshots.py` (W0-6) | migration | funksiya almashtirish | `migrations/versions/0013_market_delete_guard.py` | **exact** |
| `migrations/entities/functions.py` (MOD — `MARKET_DELETE_DRAFT` kaskadi + `capture_due_markets()`) | db-function | request-response | o'zi (`MARKET_DELETE_DRAFT:1029-1067`) + `market_repo.py:111-121` | role-match |
| **Wave 0 zondi:** `GENERATED STORED` ustunning `UNIQUE`/FK nishoni bo'lishi (D-23) | test fixture (DDL zondi) | — | `tests/fixtures/financial.py:59-145` | **exact** — §3.1 |

### 1.2 Backend — orkestratsiya (fazaning yuragi)

| Yangi/o'zgaradigan fayl | Rol | Data flow | Eng yaqin analog | Moslik |
|-------------------------|-----|-----------|------------------|--------|
| `services/core-api/app/jobs/capture.py` (`capture_tick`, `capture_batch`) | job | batch + event-driven | `app/jobs/discovery.py` (**to'liq shablon** — §3.3) | **exact** |
| `services/core-api/app/jobs/retention.py` | job | batch + file-I/O | `app/jobs/discovery.py` (tranzaksiya/xato shakli) | role-match |
| `services/core-api/app/jobs/alerting.py` (watchdog / `alert_sweep`) | job | batch | `app/jobs/discovery.py` | role-match |
| `services/core-api/app/worker.py` (MOD — `scheduler` + yangi vazifalar) | bootstrap | event-driven | o'zi (`worker.py:129-281`) | **exact** (planer qismi — §4.4) |
| `services/core-api/app/repositories/capture_repo.py` (`ensure_plan` / `claim_due` / `release_expired` / `mark_missed`) | repository | CRUD + qulflash | `app/repositories/nvr_repo.py:506-565` (shartli holat o'tishi) | partial — `SKIP LOCKED` uchun **analog yo'q** (§4.1) |
| `services/core-api/app/repositories/schedule_repo.py` | repository | CRUD | `app/repositories/tariff_repo.py` + `stall_repo.py` (davr bo'lish naqshi) | **exact** |
| `services/core-api/app/repositories/snapshot_repo.py` | repository | CRUD | `app/repositories/nvr_repo.py:294-403` (`upsert` + hisoblagichlar) | **exact** |

### 1.3 Backend — kadr olish, sifat, ombor, alert

| Yangi/o'zgaradigan fayl | Rol | Data flow | Eng yaqin analog | Moslik |
|-------------------------|-----|-----------|------------------|--------|
| `services/core-api/app/services/frame_source.py` (go2rtc → ISAPI → ffmpeg, bitta protokol) | service (HTTP klient) | request-response | `app/services/go2rtc.py` + `app/services/isapi/client.py` | **exact** |
| `services/core-api/app/services/quality.py` (`Pillow` sof funksiyasi) | service (sof funksiya) | transform | `app/services/live_source.py` / `app/services/rtsp.py` (sof modul shakli) | role-match — `Pillow` uchun **analog yo'q** (§4.3) |
| `services/core-api/app/services/object_key.py` (deterministik kalit) | utility | transform | `app/services/rtsp.py` (sof URL fabrikasi) | **exact** |
| `services/core-api/app/services/storage.py` (`aiobotocore` S3 klienti) | service (tashqi klient) | file-I/O | — | **analog yo'q** (§4.2) |
| `services/core-api/app/services/alerts.py` (Telegram `sendMessage`, `httpx`) | service (HTTP klient) | request-response | `app/services/go2rtc.py` (yupqa qobiq + sirsiz xato) | role-match — jo'natuvchi uchun **analog yo'q** (§4.5) |
| `services/core-api/app/services/capture_errors.py` | service/config | — | `app/services/isapi/errors.py` (12 kodli taksonomiya) | **exact** |

### 1.4 Backend — API va konfiguratsiya

| Yangi/o'zgaradigan fayl | Rol | Data flow | Eng yaqin analog | Moslik |
|-------------------------|-----|-----------|------------------|--------|
| `services/core-api/app/api/v1/schedules.py` | router | CRUD | `services/core-api/app/api/v1/tariffs.py` (davrli domen) + `stalls.py` | **exact** |
| `services/core-api/app/api/v1/snapshots.py` (yugurishlar va kadrlar ro'yxati) | router | request-response + o'qish auditi | `app/api/v1/cameras.py` / `stalls.py:304-345` | **exact** |
| `services/core-api/app/schemas.py` (MOD) | schema/DTO | — | o'zi (`MARKET_ERROR_CODES:490`, `:567` job kodlarini **import qiladi**) | **exact** |
| `services/core-api/app/settings.py` (MOD — S3, retention, grace, chegaralar, Telegram) | config | — | o'zi (`settings.py:81-128`) | **exact** |
| `services/core-api/app/security/rbac.py` (MOD — Wave 0) | config/matrix | — | o'zi (`rbac.py:112-117, 130-184`) | **exact** |
| `services/core-api/app/security/audit.py` (MOD — `TABLE_SNAPSHOT_SCHEDULES` va h.k.) | security utility | — | o'zi (`audit.py:91-101`) | **exact** |
| `services/core-api/app/main.py` (MOD — router ulash) | bootstrap | — | o'zi (`main.py:133-175`) | **exact** |
| `services/core-api/pyproject.toml` (MOD — `aiobotocore`, `Pillow`) | config | — | o'zi (3-fazadagi W0-1 `httpx` ko'chirishi) | **exact** |

### 1.5 Simulyator va sifat-ssenariylari

| Yangi/o'zgaradigan fayl | Rol | Data flow | Eng yaqin analog | Moslik |
|-------------------------|-----|-----------|------------------|--------|
| `services/nvr-sim/sim/state.py` (MOD — `frame_mode`) | test uskunasi | request-response | o'zi (`state.py:55-85`, `168-255`) | **exact** |
| `services/nvr-sim/sim/isapi.py` (MOD — `/Streaming/channels/{ch}/picture`) | test uskunasi | file-I/O | o'zi (mavjud `/ISAPI/*` marshrutlashi) | **exact** |
| `ops/mediamtx/mediamtx.yml` (MOD — qorong'i/kulrang/past-kontrast yo'llari) | config/ops | streaming | o'zi (`paths:` + `runOnDemand` naqshi) | **exact** |
| `tests/fixtures/frames.py` (sintetik JPEG generatori) | test fixture | transform | `tests/fixtures/karmana_seed.py` (determinizm + manba izohi) | partial |

### 1.6 Infra / ops

| Yangi/o'zgaradigan fayl | Rol | Data flow | Eng yaqin analog | Moslik |
|-------------------------|-----|-----------|------------------|--------|
| `compose.yaml` (MOD — `storage`, `scheduler`) | config/ops | — | o'zi (`compose.yaml:165-232` worker, `:234-280` go2rtc) | **exact** |
| `ops/seaweedfs/s3.json.example` | config/ops | — | `ops/wireguard/wg0.conf.example` (sirli fayl → `.example`) | **exact** |
| `ops/docs/monitoring.md` (D-21) | doc/ops | — | `ops/docs/nvr-onboarding.md` | **exact** |
| `.env.example` (MOD) | config | — | o'zi | **exact** |
| `package.json` (MOD — yangi yorliqlar + `gate` zanjiri) | config | — | o'zi (`package.json:6-33`) | **exact** |

### 1.7 Frontend

| Yangi/o'zgaradigan fayl | Rol | Data flow | Eng yaqin analog | Moslik |
|-------------------------|-----|-----------|------------------|--------|
| `frontend/src/lib/schedule-queries.ts` | data-access hook | request-response | `frontend/src/lib/camera-queries.ts` (3-fazada `market-queries.ts` dan qurilgan) | **exact** |
| `frontend/src/app/[locale]/(app)/schedule/page.tsx` | page (client) | request-response | `frontend/src/app/[locale]/(app)/cameras/page.tsx` | **exact** |
| `frontend/src/components/schedule/schedule-list.tsx` | component (list) | request-response | `frontend/src/components/tariffs/tariff-list.tsx` | **exact** |
| `frontend/src/components/schedule/slot-editor.tsx` (oraliq generatori → tekis ro'yxat) | component (form) | transform | `frontend/src/components/calendar/weekday-picker.tsx` | role-match |
| `frontend/src/components/schedule/coverage-warning.tsx` («N kun qoplanmagan») | component | — | `frontend/src/components/cameras/nvr-error-block.tsx` | role-match |
| `frontend/src/lib/api-types.ts` (MOD) | schema (zod) + xato reyestri | — | o'zi (`ERROR_CODES:1019-1092`) | **exact** |
| `frontend/src/lib/rbac.ts` (MOD) | config/matrix | — | o'zi | **exact** |
| `frontend/messages/{uz-Latn,ru}.json` + `uz-Cyrl.overrides.json` (MOD) | i18n | — | o'zi | **exact** |
| `frontend/scripts/gen-cyrillic.test.mjs` (MOD — allowlist) | test | — | o'zi (`allowed` regexi) | **exact** |

### 1.8 Testlar

| Yangi/o'zgaradigan fayl | Rol | Data flow | Eng yaqin analog | Moslik |
|-------------------------|-----|-----------|------------------|--------|
| `tests/tenancy/test_snapshot_domain_meta.py` | test (meta) | `pg_catalog` o'qish | `tests/tenancy/test_nvr_domain_meta.py` | **exact** |
| `tests/tenancy/test_meta.py` (MOD — `markets.timezone` invarianti) | test (meta) | — | o'zi (`test_meta.py:397-428` naqshi) | **exact** |
| `tests/fixtures/snapshot_domain.py` (seed) | test fixture | seed | `tests/fixtures/nvr_domain.py` | **exact** |
| `tests/fixtures/frames.py` | test fixture | transform | — | **analog yo'q** (§4.3) |
| `tests/unit/test_quality_filter.py` | test (unit) | transform | `tests/unit/test_live_source.py` (rad etish yo'llari alohida) | role-match |
| `tests/unit/test_object_key.py` | test (unit) | — | `tests/unit/test_rtsp_url.py` | **exact** |
| `tests/unit/test_runtime_deps.py` (MOD — `aiobotocore`/`Pillow`) | test (unit) | — | o'zi | **exact** |
| `tests/integration/test_capture_schedule.py` (CAM-04) | test (integration) | HTTP e2e | `tests/integration/test_tariff_history.py` | **exact** |
| `tests/integration/test_capture_tick.py` (CAM-05) | test (integration) | job e2e | `tests/integration/test_nvr_discovery_job.py` | **exact** |
| `tests/integration/test_snapshot_quality.py` (CAM-06 DB kafolati) | test (integration) | constraint | `tests/integration/test_money_constraints.py` + `test_stall_code_reuse.py` | **exact** |
| `tests/integration/test_storage_layout.py` (`sim`) | test (integration) | file-I/O | `tests/integration/test_live_view_e2e.py` (mock'siz o'lchov) | role-match |
| `tests/integration/test_retention.py` (`sim`) | test (integration) | file-I/O | — | partial (§4.2) |
| `tests/integration/test_alerting.py` (`respx`) | test (integration) | HTTP kontrakti | `tests/integration/test_nvr_errors.py` | role-match |
| `tests/integration/test_phase4_criteria.py` | test (faza darvozasi) | e2e + meta | `tests/integration/test_phase3_criteria.py:1040-1124` | **exact** |
| `tests/unit/test_compose_sim_env.py` (MOD) | test (unit) | — | o'zi | **exact** |
| `tests/conftest.py` / `tests/integration/conftest.py` (MOD — `s3_client` fixture) | test fixture | — | o'zi (`api_client`, `sim_url`) | **exact** |

---

## 2. Shared Patterns — HAMMA fayl uchun (avval shu bo'limni o'qing)

### S-1. Yangi tenant jadvali — BESH JOY, biri unutilsa CI qizaradi

3-fazada bu qoida `03-PATTERNS.md` §S-1 da yozilgan va **o'zgarishsiz amal qiladi**.
`0012_nvr_domain` uni bajargan holda — eng yangi shablon.

1. `migrations/entities/__init__.py::SNAPSHOT_TENANT_TABLES` + `ALL_TENANT_TABLES`
2. Migratsiya fayli (`op.create_table` + `enable_tenant_rls` + `tenant_policy` + `owner_bootstrap_policy`)
3. `packages/sbozor-core/sbozor_core/schema_contract.py::AUDITED_TABLES` (**faqat trigger ulanadigan jadval**)
4. `packages/sbozor-core/sbozor_core/models/__init__.py` barreli
5. `tests/fixtures/snapshot_domain.py` seed'i

**Reyestr shakli — verbatim:** `migrations/entities/__init__.py:133-181`

```python
NVR_TENANT_TABLES: tuple[str, ...] = (
    "nvr_devices",
    "nvr_credentials",
    "cameras",
    "nvr_discovery_runs",
)
"""`0012_nvr_domain` yaratadigan tenant jadvallari (CAM-01/CAM-08).

TARTIB — FK bo'yicha OTA-ONADAN bolalarga: `nvr_devices` birinchi, chunki
qolgan uchtasi unga composite FK `(market_id, nvr_id)` bilan tayanadi.
...
BU RO'YXAT AUDIT UCHUN EMAS. Trigger faqat `NVR_AUDITED_TABLES` ga ulanadi
(pastda) va farq ATAYIN ...
"""

NVR_AUDITED_TABLES: tuple[str, ...] = ("nvr_devices", "cameras")
```

**4-faza jufti (tartib FK bo'yicha):**

```python
SNAPSHOT_TENANT_TABLES: tuple[str, ...] = (
    "snapshot_schedules",
    "snapshot_schedule_slots",
    "capture_runs",
    "snapshots",
    "alert_events",
)
SNAPSHOT_AUDITED_TABLES: tuple[str, ...] = ("snapshot_schedules", "snapshot_schedule_slots")
```

> 🔴 **`capture_runs`, `snapshots`, `alert_events` AUDIT TRIGGERIDAN CHIQARILADI** va
> sabab `migrations/entities/__init__.py:171-175` da allaqachon yozilgan shakl bilan
> **bir xil**:
>
> ```python
> """...
> `nvr_discovery_runs` ham ro'yxatda YO'Q, lekin BOSHQA sababdan: u
> hodisa jurnali va faqat QO'SHILADI (tahrirlanmaydi) — uning ustiga audit
> qo'yish `audit_log` ga o'sha ma'lumotning ikkinchi nusxasini yozardi.
> """
> ```
>
> `capture_runs` uchun bunga **hajm** argumenti qo'shiladi: 175 qator/kun/bozor × har
> holat o'zgarishi (`pending`→`running`→`succeeded`) ≈ kuniga 525 audit qatori bitta
> bozordan. `nvr_credentials` istisnosi **sir** sababli, bu esa **hajm va foydasizlik**
> sababli — ikkalasi ham `schema_contract.py:149-167` dagi «RO'YXATGA KIRMAYDIGANLAR va
> sababi» ro'yxatiga **sabab bilan** yoziladi. Iz yo'qolmaydi: jadval o'zgarishi
> (`snapshot_schedules`) auditda, kunlik yugurishlar esa `capture_runs` ning O'ZIDA
> tarixga ega.

**Composite FK va `UNIQUE(market_id, id)`** — `models/nvr.py:159-198` (`NvrDevice`):

```python
    __table_args__ = (
        ForeignKeyConstraint(
            ["market_id"], ["markets.id"], name="fk_nvr_devices_market_id_markets"
        ),
        # Composite FK NISHONI: `cameras`, `nvr_credentials` va
        # `nvr_discovery_runs` `(market_id, nvr_id)` ga havola qiladi, ya'ni
        # cross-tenant bog'lanish SXEMA darajasida yopiladi (T-03-14). RLS
        # chetlab o'tilishi mumkin bo'lgan har qanday yo'lda (migratsiya,
        # `psql`, xato yozilgan `SECURITY DEFINER`) bu FK baribir turadi.
        UniqueConstraint("market_id", "id", name="uq_nvr_devices_market_id_id"),
```

4-fazada bu **beshala jadvalga** kerak: `capture_runs` → `cameras`/`nvr_devices`,
`snapshots` → `capture_runs`, `snapshot_schedule_slots` → `snapshot_schedules`.

---

### S-2. Indeks nomlari — MODEL VA MIGRATSIYA UCHUN BITTA MANBA (03-03 o'lchovi)

**Manba (verbatim):** `packages/sbozor-core/sbozor_core/models/nvr.py:119-137`

```python
# ===========================================================================
# QISMAN / GLOBAL INDEKS NOMLARI — MODEL VA MIGRATSIYA UCHUN YAGONA MANBA
# ===========================================================================
#
# ⚠ NEGA INDEKSLAR MODELDA HAM E'LON QILINADI (o'lchangan, 03-03):
# `op.create_index(...)` yolg'iz o'zi yetarli EMAS. Alembic autogenerate
# model metadata'sini baza bilan solishtiradi va modelda e'lon qilinmagan
# indeksni "o'chirilgan" deb hisoblaydi — `test_autogenerate_is_empty`
# uchta `remove_index` bilan QIZARDI (birinchi o'lchov). Ya'ni migratsiyada
# indeks yaratish uni sxemaga qo'shadi, LEKIN keyingi `alembic revision
# --autogenerate` uni O'CHIRISHNI taklif qilardi va kimdir buni "tozalash"
# deb qabul qilishi mumkin edi.
#
# Nomlar va predikatlar shu yerda, ikkala tomon (model `Index(...)` va
# `0012_nvr_domain`) SHU KONSTANTALARDAN oladi — literal takrorlanmaydi.

DISCOVERY_ACTIVE_RUN_INDEX = "uq_nvr_discovery_runs_market_id_nvr_id_active"
TUNNEL_SUBNET_INDEX = "uq_nvr_devices_tunnel_subnet_global"
CAMERA_NVR_INDEX = "ix_cameras_market_id_nvr_id"
```

**Iste'mol tomoni — migratsiyadagi import:** `0012_nvr_domain.py:64-72`

```python
from sbozor_core.models.nvr import (
    CAMERA_NVR_INDEX,
    CAMERA_STATUS_CHECK,
    DISCOVERY_ACTIVE_RUN_INDEX,
    DISCOVERY_RUN_ACTIVE_PREDICATE,
    DISCOVERY_RUN_STATUS_CHECK,
    TUNNEL_SUBNET_INDEX,
    TUNNEL_SUBNET_PREDICATE,
)
```

**Qisman indeks yaratish:** `0012_nvr_domain.py:409-415`

```python
    op.create_index(
        DISCOVERY_ACTIVE_RUN_INDEX,
        "nvr_discovery_runs",
        ["market_id", "nvr_id"],
        unique=True,
        postgresql_where=sa.text(DISCOVERY_RUN_ACTIVE_PREDICATE),
    )
```

**Predikat enum'dan HOSILA:** `models/nvr.py:104-117`

```python
    return ", ".join(f"'{value}'" for value in values)


CAMERA_STATUS_CHECK = f"status IN ({_quoted(CAMERA_STATUS_VALUES)})"
"""`cameras.status` faqat ma'lum holatlardan biri (ifoda enum'dan HOSILA)."""
...
DISCOVERY_RUN_ACTIVE_PREDICATE = f"status IN ({_quoted(DISCOVERY_RUN_ACTIVE_STATUSES)})"
"""Qisman UNIQUE indeksning predikati — `DISCOVERY_RUN_ACTIVE_STATUSES` dan HOSILA."""
```

> **4-fazada bu naqsh KAMIDA IKKI MARTA kerak** (RESEARCH §A.2 sxemasi):
> `ix_capture_runs_due` (`WHERE status = 'pending'`) va `ix_capture_runs_overdue`
> (`WHERE status IN ('pending','running')`). Ikkala predikat ham `CaptureRunStatus`
> enum'idan **hosila** bo'lishi shart.
>
> ⚠ `ix_capture_runs_overdue` **`market_id` bilan boshlanmaydi** (watchdog barcha
> bozorlar ustidan yuradi). Bu `TUNNEL_SUBNET_INDEX` bilan bir xil holat va u
> `tests/tenancy/test_meta.py:44` dagi `INDEX_EXCEPTIONS` ga **sabab bilan**
> qo'shiladi — aks holda `test_tenant_indexes_lead_with_market_id`
> (`test_meta.py:397-428`) qizaradi. Istisnoning yozilish uslubi —
> `0012_nvr_domain.py:417-436` (`TUNNEL_SUBNET_INDEX` izohi).

---

### S-3. Fon-vazifa tenant kontekstini O'ZI o'rnatadi — 4-fazaning ENG XAVFLI joyi

**Manba (verbatim):** `services/core-api/app/jobs/discovery.py:170-205`

```python
@asynccontextmanager
async def _system_transaction(
    sessionmaker: async_sessionmaker[AsyncSession],
    *,
    market_id: UUID,
    actor_id: UUID | None,
    request_id: str,
) -> AsyncIterator[AsyncSession]:
    """Tenant konteksti O'RNATILGAN sessiya — `deps.py:418-449` ning worker jufti.

    Uch farq bor va uchalasi ham ataylab:

      1. `Principal` YO'Q — `market_id` va `actor_id` argument sifatida
         keladi (ularni navbat xabari olib keladi);
      2. `actor_kind=ActorKind.SYSTEM` — `audit_log` da "buni odam emas,
         fon jarayoni yozdi" deb ko'rinsin;
      3. `HTTPException` YO'Q — worker'da javob beriladigan mijoz yo'q.

    ⚠ HAR CHAQIRUVDA YANGI TRANZAKSIYA VA YANGI KONTEKST. GUC'lar
      `SET LOCAL` bilan qo'yiladi, ya'ni `COMMIT` da tozalanadi. "Bir marta
      o'rnatib, keyin qayta ishlataman" yo'li fail-closed holatga tushardi
      va u JIMGINA 0 qator berardi (modul docstringi).
    """
    # SIM117 (ikki `async with` ni birlashtirish) `deps.py:434-439` dagi
    # bilan AYNAN bir xil sababdan rad etilgan: ichki blok TRANZAKSIYA
    # chegarasi va u shu yerdagi butun xavfsizlik da'vosini ushlab turadi.
    async with sessionmaker() as session:  # noqa: SIM117
        async with session.begin():
            await set_tenant_context(
                session,
                market_id=market_id,
                actor_id=actor_id,
                request_id=request_id,
                actor_kind=ActorKind.SYSTEM,
            )
            yield session
```

**Nima uchun bu majburiy (verbatim, `discovery.py:14-30`):**

```
PITFALL 13 — JOB TENANT KONTEKSTINI O'ZI O'RNATADI, VA BUSIZ U JIMGINA YOLG'ON
GAPIRADI.
...
Bo'sh GUC ostida RLS FAIL-CLOSED ishlaydi, lekin "fail" so'zi bu yerda
aldamchi:

    SELECT / UPDATE  ->  0 qator, ISTISNO YO'Q
    INSERT           ->  `WITH CHECK` buzilishi (bu esa KO'RINADI)
```

> 🔴 **4-FAZA BU NAQSHNI KENGAYTIRADI VA KENGAYTMA YANGI XAVF TUG'DIRADI.**
> Kashfiyot jobi **bitta** `market_id` bilan chaqirilgan — u navbat xabaridan kelgan.
> Tick esa **hamma** bozorlar ustida ishlashi kerak, `sbozor_app` roli esa kontekstsiz
> **birorta** bozorni ko'rmaydi (`markets` policy'si `id = app.market_id`).
>
> **Loyihada bu muammoning yechimi ALLAQACHON bor** — `market_repo.py:111-121`:
>
> ```python
> _ALL_MARKETS = text(
>     "SELECT market_id, market_name, market_timezone, is_active FROM auth_list_markets_full()"
> )
> """...
> `SECURITY DEFINER` funksiya faqat bozor KONFIGURATSIYASINI ochadi — tenant
> ...
> """
> ```
>
> Tick uchun jufti — `capture_due_markets()`: **faqat `market_id`** (va ixtiyoriy
> `due_count`) qaytaradigan yangi `SECURITY DEFINER` funksiya. Keyin **har bozor uchun
> alohida `_system_transaction()`**. Bitta tranzaksiyada ikki bozorni aralashtirish —
> tenant sizib chiqishining eng qisqa yo'li (GUC'lar `SET LOCAL`).
>
> Yangi `SECURITY DEFINER` funksiya `migrations/entities/functions.py` ga qo'shiladi va
> u **avtomatik** ravishda `tests/tenancy/test_meta.py:432`
> (`test_security_definer_functions_pin_search_path`) darvozasiga tushadi —
> `SET search_path = pg_catalog, public` majburiy.
>
> **Darvoza:** `test_capture_tick_sets_tenant_context` — kontekstsiz chaqiruvda
> materializatsiya **0 qator** yozishini ANIQ ko'rsatadi. Analogi mavjud:
> `tests/integration/test_nvr_discovery_job.py::test_worker_sets_tenant_context`
> (`discovery.py:37-39` da nomi bilan keltirilgan).

---

### S-4. Job — sof `async def`, navbat kutubxonasi FAQAT `worker.py` da (D-06)

**Manba (verbatim):** `services/core-api/app/jobs/discovery.py:1-12`

```
"""NVR kashfiyotining fon-vazifasi — loyihaning BIRINCHI so'rov-tashqari kodi.

=============================================================================
BU FAYLDA NAVBAT KUTUBXONASI IMPORT QILINMAYDI (D-06).

`discover_nvr` — SOF `async def` funksiya. Uni navbatga bog'laydigan yupqa
qobiq `app/worker.py` da va kutubxona nomi FAQAT o'sha faylda uchraydi.
4-faza boshqa mexanizmni tanlasa ko'chirish narxi ~10 qator bo'lishi kerak;
ikki mexanizm bir vaqtda saqlanmaydi.

⚠ Buni `grep -cE "^\\s*(import|from)\\s+taskiq"` mexanik tekshiradi.
=============================================================================
```

> ✅ **4-FAZA MEXANIZMNI SAQLAB QOLDI** (D-02): `taskiq` qoladi, lekin unga **planer**
> qo'shiladi. Ya'ni yuqoridagi majburiyat **kuchida qoladi va kengayadi** —
> `app/jobs/capture.py`, `app/jobs/retention.py`, `app/jobs/alerting.py` uchalasida ham
> `taskiq` import qilinmaydi. Planer ta'rifi (`ScheduledTask`, `LabelScheduleSource`,
> `TaskiqScheduler`) **faqat `app/worker.py`** da.

**Yupqa qobiq (verbatim):** `app/worker.py:210-232`

```python
@broker.task(task_name="nvr.discover")
async def discover_nvr_task(
    context: Annotated[Context, TaskiqDepends()],
    *,
    market_id: str,
    nvr_id: str,
    run_id: str,
    actor_id: str | None = None,
) -> None:
    """YUPQA QOBIQ — boshqa hech nima qilmaydi (D-06).

    Ikki ish bajaradi va ikkalasi ham CHEGARA ishi:

      1. `str` -> `UUID`. Navbat xabari JSON, ya'ni `UUID` u yerdan
         MATN bo'lib qaytadi. Konversiya shu yerda, jobda EMAS ...
      2. `sessionmaker` ni `TaskiqState` dan olib beradi — job resursni
         O'ZI QURMAYDI (`app/jobs/discovery.py` argument sifatida oladi).

    Mantiq shu funksiyada YO'Q va bo'lmasligi kerak: mexanizm
    almashtirilganda ko'chiriladigan yagona qism aynan shu.
    """
```

**Navbatga qo'yish — so'rov ichidagi yo'l uchun `asyncio.timeout`:** `worker.py:274-281`

```python
    # Chegara SHU YERDA, pulda emas — sabab `ENQUEUE_TIMEOUT_SECONDS`
    # docstringida. `TimeoutError` chaqiruvchiga KO'TARILADI: API qatlami
    # navbatga tushmagan yugurishni `failed` deb yopishi SHART, aks holda
    # qator MANGU `queued` bo'lib qolardi ...
    async with asyncio.timeout(ENQUEUE_TIMEOUT_SECONDS):
        await kicker.kiq(**payload)
```

---

### S-5. Broker sozlamalari — `socket_timeout=None` (O'LCHANGAN, 03-06)

**Manba (verbatim):** `app/worker.py:129-159`

```python
broker: AsyncBroker = ListQueueBroker(
    _broker_url(),
    queue_name=DISCOVERY_QUEUE,
    # ==================================================================
    # ⚠⚠ `socket_timeout=None` MAJBURIY VA U "QULAYLIK" EMAS — USIZ
    #    WORKER HAR 5 SONIYADA YIQILADI. Bu O'LCHANGAN fakt:
    #
    #      redis-py 8.0.1 -> Connection.socket_timeout = 5 (STANDART)
    #      ListQueueBroker.listen() -> `BRPOP <queue>` CHEKSIZ bloklanadi
    #      -> 5 s dan keyin `redis.exceptions.TimeoutError`
    #      -> `listen()` faqat `ConnectionError` ni tutadi
    #      -> prefetcher yiqiladi -> "worker-0 is dead. Scheduling reload."
    #
    #    Bo'sh navbatda bu CHEKSIZ QAYTA ISHGA TUSHISH SIKLI: konteyner
    #    "Up" bo'lib turadi, `docker compose ps` sog'lom ko'rsatadi va
    #    birorta vazifa hech qachon bajarilmaydi.
    #
    #    `socket_timeout` — javob KUTISH chegarasi; bloklanuvchi navbat
    #    o'quvchisi uchun uning ta'rifi bo'yicha chegara bo'lishi mumkin
    #    emas. Uning o'rnini `socket_connect_timeout` (ulanish) va
    #    `socket_keepalive` (o'lik peer'ni OS darajasida aniqlash) egallaydi.
    # ==================================================================
    socket_timeout=None,
    socket_connect_timeout=CONNECT_TIMEOUT_SECONDS,
    socket_keepalive=True,
).with_result_backend(
    # ⚠ NATIJA BACKEND'I `socket_timeout` NI SAQLAB QOLADI (standart 5 s):
    #   u oddiy `SET`/`GET` qiladi va ular hech qachon bloklanmaydi, ya'ni
    #   u yerda chegara TO'G'RI va foydali.
    RedisAsyncResultBackend(_broker_url(), result_ex_time=RESULT_TTL_SECONDS),
)
```

**Modul darajasida `Settings` chaqirilmaydi** — `worker.py:26-41`:

```
BROKER QURILISHI `Settings` NI CHAQIRMAYDI — VA BU ATAYIN.

`broker` MODUL DARAJASIDA quriladi (taskiq CLI `app.worker:broker` ni
import qiladi, ya'ni boshqa yo'l yo'q). Agar u `get_settings()` dan
o'qisa, `app.worker` ni IMPORT QILISHNING O'ZI to'liq muhitni talab
qilardi — va `app/main.py` uni import qiladi, ya'ni butun test to'plami
`NVR_CREDENTIAL_KEY` siz yiqilardi.
```

> ⚠ **`scheduler` obyekti ham AYNAN SHU qoidaga bo'ysunadi.** `taskiq scheduler
> app.worker:scheduler` uni **import** qiladi, ya'ni `TaskiqScheduler(...)` qurilishi
> `get_settings()` ga bog'lanmasligi shart. Cron satri (`"* * * * *"`) — literal
> konstanta, sozlama emas.
>
> ⚠ `RedisStreamBroker` **hamon rad etilgan** (`worker.py:172-177`), lekin sabab
> 4-fazada **teskari** ishlaydi: u yerda «qaytgan vazifa NVR ga ikkinchi marta borardi»
> deyilgan. Kadr olishda qayta yetkazish foydali bo'lardi — **lekin uni lease allaqachon
> bajaradi** va ikki mexanizmni birga saqlash D-06 ni buzadi. `ListQueueBroker` qoladi.

**Resurs egaligi:** `worker.py:181-207` (`WORKER_STARTUP` / `WORKER_SHUTDOWN`) —
`engine` bir marta ochiladi, `state.sessionmaker` ga qo'yiladi, `shutdown` da
`dispose()`. Yangi resurs (S3 sessiyasi) **shu yerga** qo'shiladi va shu yerda yopiladi.

---

### S-6. `is_billable` ilgagi — KELISHUV EMAS, TUZILMA (D-16, CAM-06)

**Naqshning manbai — `FINANCIAL_TABLES` falsafasi:** `schema_contract.py:61-75`

```python
"""Mezon #5 konstraytlari majburiy bo'lgan jadvallar.
...
1-fazada bu jadvallarning HECH BIRI hali mavjud emas (ular 2- va 6-fazalarda
tug'iladi). Reyestr shunga qaramay hozir yoziladi, chunki meta-test uni
"jadval mavjud bo'lsa — quyidagi konstraytlar ham bo'lishi shart" shaklida
ishlatadi: shunda 6-fazada `payments` yaratilgan kuni darvoza avtomatik
yopiladi va hech kim `UNIQUE(market_id, idempotency_key)` ni unutib
qo'ymaydi.
"""
```

**4-faza ILGAKNI qo'yadi, 5-faza uni topib OSADI:**

```sql
-- 4-FAZA (shu faza):
ALTER TABLE snapshots ADD CONSTRAINT uq_snapshots_billable_anchor UNIQUE (id, is_billable);

-- 5-FAZA:
FOREIGN KEY (snapshot_id, snapshot_is_billable) REFERENCES snapshots (id, is_billable)
```

**Composite FK'ning DB-darajasidagi kafolat sifatidagi mavjud namunasi** —
`0009_vendors.py:204-213`:

```python
        # A bozoridagi biriktirish B bozorining rastasiga yoki sotuvchisiga
        # havola qila OLMAYDI — bu RLS emas, SXEMA darajasidagi kafolat
        # (T-02-38). RLS chetlab o'tilishi mumkin bo'lgan har qanday yo'lda
        # (migratsiya, `psql`, xato yozilgan `SECURITY DEFINER`) bu ikki FK
        # baribir turadi.
```

> 🔴 **D-23 / OQ-4 — `GENERATED STORED` ustun `UNIQUE` ga kira oladimi?**
> **QISMAN O'LCHANGAN — javobning yarmi shu repoda bor va u ijobiy.**
> `migrations/helpers.py:356-362` aynan shu DDL'ni chiqaradi:
>
> ```python
>     statements = [
>         f"ALTER TABLE {tbl} ADD COLUMN business_date date "
>         f"GENERATED ALWAYS AS {BUSINESS_DATE_EXPR} STORED",
>         f"ALTER TABLE {tbl} ADD CONSTRAINT ck_{tbl}_{amount}_positive CHECK ({amount} > 0)",
>         f"ALTER TABLE {tbl} ADD CONSTRAINT uq_{tbl}_business_day "
>         f"UNIQUE (market_id, {', '.join(keys)}, business_date)",
>     ]
> ```
>
> va `tests/fixtures/financial.py:127-138` uni **haqiqiy `postgres:18.4` jadvalida**
> bajaradi:
>
> ```python
> def create_financial_probe(conn: Connection[TupleRow]) -> FinancialProbe:
>     """Probe jadvallarini quradi va `financial_guards()` DDL'ini qo'llaydi."""
>     drop_financial_probe(conn)
>
>     conn.execute(_CREATE_PARENT)
>     conn.execute(_CREATE_CHILD)
>     for statement in financial_guard_statements(
>         CHILD_TABLE,
>         unique_cols=["stall_id"],
>         parent=(PARENT_TABLE, "stall_id"),
>     ):
>         conn.execute(statement)
> ```
>
> Ya'ni **«GENERATED STORED ustun UNIQUE ga kiradi»** — repoda yashil test bilan
> qulflangan fakt, taxmin emas.
>
> ⚠ **LEKIN D-23 NING IKKINCHI YARMI HAMON O'LCHANMAGAN:** o'sha `UNIQUE` ning
> **kompozit FK NISHONI** bo'lishi. `financial_guard_statements` FK'ni
> `(market_id, id)` ga qo'yadi — ikkala ustun ham **oddiy**. `(id, is_billable)` da
> ikkinchi ustun generated. **Wave 0 zondi aynan shuni bajarishi kerak** (§3.1) va
> uning shabloni `tests/fixtures/financial.py:59-145`.
>
> **Zaxira (D-23, yiqilsa):** `is_billable` — oddiy `boolean NOT NULL`,
> `BEFORE INSERT/UPDATE` triggeri uni `quality_verdict` dan hisoblaydi.
> Trigger fabrikasining mavjud namunasi — `migrations/entities/triggers.py`.

---

### S-7. Xato taksonomiyasi — KOD reyestri, matn emas; u IKKI iste'molchiga xizmat qiladi

**Manba:** `app/schemas.py:33, 490, 567` — job kodlari **import qilinadi**, qayta
yozilmaydi:

```python
from app.jobs.discovery import DISCOVERY_JOB_ERROR_CODES
...
MARKET_ERROR_CODES: Final[frozenset[str]] = frozenset(
    ...
        *DISCOVERY_JOB_ERROR_CODES,
```

**Nima uchun (verbatim, `discovery.py:141-150`):**

```python
DISCOVERY_JOB_ERROR_CODES: Final[frozenset[str]] = frozenset(
    {NVR_NOT_FOUND, NVR_CREDENTIAL_UNREADABLE, JOB_INTERNAL_ERROR}
)
"""Job YOZADIGAN, lekin ISAPI taksonomiyasiga TUSHMAYDIGAN kodlar.

`app/schemas.py::MARKET_ERROR_CODES` bu to'plamni IMPORT qiladi — qo'lda
takrorlamaydi. Ikki nusxa bo'lganda job bazaga kod yozib, API uni
tanimasdi va frontend `errors.generic` ko'rsatib sababni yo'qotardi
(§S-5 ning aynan o'zi).
"""
```

**Kod bir vaqtning o'zida `detail` VA ustun qiymati:** `discovery.py:104-110`

```python
NVR_NOT_FOUND: Final[str] = "nvr_not_found"
"""Qurilma qatori topilmadi (o'chirilgan yoki begona bozorniki).

API qatlamida bu 404 ning `detail` i, job qatlamida esa
`nvr_discovery_runs.error_code`. IKKALASIDA HAM BIR XIL SATR — aks holda
admin bir xil holat uchun ikki xil xabar ko'rardi.
"""
```

**Ikkinchi reyestr — ATAYIN alohida:** `frontend/src/lib/nvr-errors.ts:32-63`
(`NVR_ERROR_CODES` `api-types.ts::ERROR_CODES` ga **qo'shilmaydi**). 4-fazada kadr
olish kodlari ham shu ikkilikka bo'linadi: `capture_runs.error_code` — **domen
reyestri**, HTTP `detail` kodlari — `MARKET_ERROR_CODES`.

**`AUTH_LOCKING_CODES` MEROS OLINADI** — `frontend/src/lib/nvr-errors.ts:139`:

```ts
  NVR_ERROR_CODES.filter((code) => NVR_ERROR_META[code].authLocking);
```

> 🔴 Bu ro'yxat 4-fazada **yangi ma'noga ega bo'ladi**: `nvr_bad_credentials`,
> `nvr_account_locked`, `nvr_user_no_permission` kodlarida **tickning ham qayta
> urinishi taqiqlanadi** — qator darhol `failed`, `attempts = max_attempts`. Aks holda
> tick har daqiqada NVR'ga borib butun bozorning hisobini qulflardi
> (25 kamera × 10 tick = 250 muvaffaqiyatsiz autentifikatsiya urinishi).
> Ikkinchi maxsus kod — `nvr_stream_limit`: retry emas, **kechiktirish** (`locked_until`
> qayta ishlatiladi).

---

### S-8. Retry — TESKARI siyosat, meros olinadi va QAYTA IXTIRO QILINMAYDI

**Manba (verbatim):** `app/services/isapi/client.py:12-19`

```
Arifmetika shafqatsiz: `tenacity` ning odatiy 3 urinishi × foydalanuvchining
...
    tarmoq xatosi (timeout, connect reset, 5xx)  ->  retry, <=3 urinish
```

**Amaldagi shakl:** `isapi/client.py:425-432`

```python
        """Retry qatlami — FAQAT tarmoq sinfi (`_should_retry`)."""
        retrying: AsyncRetrying = AsyncRetrying(
            stop=stop_after_attempt(self._retry_attempts),
            wait=wait_exponential(multiplier=0.3, max=2.0),
            retry=retry_if_exception(_should_retry),
        )
        return await retrying(self._attempt, path, auth=auth)
```

**IKKI QATLAM ARALASHTIRILMAYDI:**

| Qatlam | Vosita | Nimani qoplaydi | Chegara |
|--------|--------|------------------|---------|
| Urinish **ICHIDA** | `tenacity` (`AsyncRetrying`, yuqoridagi shakl) | Bir martalik tarmoq uzilishi | `MAX_RETRY_ATTEMPTS = 3` (`isapi/client.py:109`) |
| Urinishlar **ORASIDA** | Tick + lease (`capture_runs.attempts`) | Worker o'ldi, konteyner qayta ko'tarildi | `max_attempts` **VA** `grace` — qaysi biri oldin tugasa |

---

### S-9. Sir bilan ishlash — TO'RT YOPIQ YUZA MEROS OLINADI

Kadr olish yo'li NVR parolini ushlaydi (go2rtc `src` va ISAPI Digest). 3-fazada
to'rtta oqish yuzasi yopilgan va **to'rttasi ham 4-fazada amal qiladi**.

**(1) `httpx` istisno matnidagi URL** — `go2rtc.py:133-160`:

```python
def _failure(method: str, exc: httpx.HTTPError) -> Go2rtcError:
    """`httpx` istisnosini SIRSIZ `Go2rtcError` ga aylantiradi (T-03-87).

    =========================================================================
    ⚠⚠ `{exc}` INTERPOLYATSIYASI — HAQIQIY OQISH YO'LI EDI.

    `httpx.HTTPStatusError` ning matni TO'LIQ so'rov URL'ini o'z ichiga
    oladi::

        Client error '400 Bad Request' for url
        'http://go2rtc:1984/api/streams?name=cam_...&src=rtsp://admin:PAROL@...'
    ...
    """
    status = exc.response.status_code if isinstance(exc, httpx.HTTPStatusError) else None
    detail = f"status={status}" if status is not None else "javob yo'q"
    return Go2rtcError(
        f"go2rtc `{method} {GO2RTC_STREAMS_PATH}` yiqildi: {type(exc).__name__} ({detail})"
    )
```

**(2) `from None` — istisno zanjiri uziladi** — `go2rtc.py:324-330`:

```python
        if put_failure is not None:
            # ⚠ `from None` — VA U `has_stream` DAN ATAYIN FARQ QILADI.
            #   SHU chaqiruvning URL'ida sir bor, ya'ni `httpx` istisnosi
            #   `__cause__` da qolsa `traceback`, Sentry ning zanjir
            #   yuruvchisi va har qanday `format_exc()` uni chop etardi.
```

**(3) Sentry `before_send` + `before_breadcrumb` — IKKALASI HAM** —
`app/main.py:209-217`:

```python
        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            before_send=_scrub_event,
            # ⚠ IKKALASI HAM MAJBURIY (T-03-89): `before_send` hodisani,
            ...
            before_breadcrumb=_scrub_breadcrumb,
```

`_scrub_breadcrumb` sababi — `main.py:172-186`:

```
⚠⚠ BU ALOHIDA ILMOQ KERAK — `before_send` YETMAYDI.

`sentry-sdk[fastapi]` ning httpx integratsiyasi har CHIQUVCHI so'rovni
breadcrumb sifatida yozadi va breadcrumb `data` sida TO'LIQ URL, query
satri bilan turadi. ... ya'ni parol hodisa YUZ BERMASDAN OLDIN, oddiy
muvaffaqiyatli chaqiruvda ham navbatga tushardi va keyingi ISTALGAN
xato bilan Sentry'ga ketardi.
```

`_scrub_event` freym lokallarini ham qamraydi — `main.py:145-149`:

```
03-13 dan boshlab BU YERDA IKKINCHI VAZIFA HAM BOR: jonli ko'rish yo'li
go2rtc'ga REKVIZITLI RTSP manbaini yuboradi (`?src=rtsp://admin:PAROL@...`),
ya'ni sir istisno matniga, so'rov query satriga va freym lokallariga
tushishi mumkin. `_mask_deep()` uchalasini ham matn darajasida yopadi.
```

**(4) Foizli kodlash darvozasi + `SecretStr`** — `live_source.py:161-178`:

```python
    # ⚠ `safe=""` — MODUL DOCSTRINGIDAGI 1-QADAM. Standart `safe="/"`
    #   sleshni qoldiradi va parolda slesh bo'lsa yo'l chegarasi siljiydi.
    userinfo = f"{quote(username, safe='')}:{quote(password, safe='')}"
    candidate = urlunsplit(...)

    # ⚠ 2-QADAM — DARVOZA. Kodlash to'g'ri ishlaganini NATIJADAN o'lchaydi.
    if _authority(candidate) != expected:
        raise ValueError(CREDENTIAL_INJECTION)

    return SecretStr(candidate)
```

**Ochiq qiymatga borish BITTA joyda:** `go2rtc.py:293-296`

```python
        # `get_secret_value()` SHU YERDA VA BOSHQA HECH QAYERDA (03-04
        # dagi `nvr_cipher()` bilan bir xil qoida): ochiq qiymatga borish
        # ATAYIN ko'rinadigan, grep bilan topiladigan BITTA qadam.
        source = src.get_secret_value()
```

**Parolni ochish va uning xato yo'li** — `discovery.py:428-444`:

```python
    try:
        password = decrypt_nvr_password(token)
    except InvalidToken:
        # ⚠ JURNALGA NA TOKEN, NA UNING BO'LAGI TUSHADI. Xabar operatorga
        #   QAYERGA qarashni aytadi (shifr kaliti), qiymatni emas.
        log.error(
            "nvr_credential_decrypt_failed",
            market_id=str(market_id),
            nvr_id=str(nvr_id),
        )
```

> 🔴 **4-FAZADA YANGI OQISH YUZASI: ISAPI `/picture` NING URL'i.**
> D-07 ISAPI'ni **eng xavfsiz** usul deb belgiladi (nol RTSP sessiyasi), lekin uning
> chaqiruvi `httpx.DigestAuth` bilan boradi — ya'ni parol `auth` obyektida, URL'da
> emas. **`?u=…&p=…` shaklidagi ISAPI varianti ISHLATILMAYDI** — u parolni query
> satriga, u yerdan Sentry breadcrumb'iga va nginx access-log'iga olib chiqardi.
> Bu qoida `frame_source.py` docstringida yozilishi shart.
>
> 🔴 **IKKINCHI YANGI YUZA: S3 rekvizitlari.** `aiobotocore` xatolari
> (`ClientError`) endpoint URL'ini va ba'zan imzo bo'laklarini matnda tashiydi.
> `storage.py` `_failure()` ning aynan `go2rtc.py:133-160` shaklidagi jufti bilan
> boshlanishi kerak: **amal + istisno turi + status**, boshqa hech nima.

---

### S-10. go2rtc bilan har qanday muloqot — NATIJADAN o'lchanadi (03-14)

**Manba (verbatim):** `go2rtc.py:257-280`

```
=====================================================================
⚠⚠ MUVAFFAQIYAT STATUS KODIDAN EMAS, NATIJADAN O'LCHANADI.

go2rtc `PUT /api/streams` ni IKKI QADAMDA bajaradi: avval oqimni
XOTIRAGA qo'shadi, keyin uni `/config/go2rtc.yaml` ga YOZIB
QO'YMOQCHI bo'ladi. Bizda o'sha fayl `:ro` mount qilingan (D-11 —
`exec:` ning konfiguratsiyaga muhrlanishiga qarshi qatlam), ya'ni
ikkinchi qadam HAR DOIM yiqiladi va go2rtc **400** qaytaradi.
Oqim esa RO'YXATDA BO'LADI.

O'lchandi (2026-08-03, 03-14): `PUT` -> `400
"yaml: ... did not find expected key"`, keyin `GET /api/streams`
-> oqim BOR, `/api/frame.jpeg` -> 99 681 baytli JPEG.

Ya'ni `raise_for_status()` ga so'zsiz ishonish jonli ko'rishni
ISHLAB TURGAN holatda 503 qilardi — bu nosozlikni `go2rtc_calls`
mock'i yashirgan edi va uni birinchi MOCK'SIZ o'lchov (03-14)
ochdi. Shuning uchun `PUT` yiqilganda ro'yxat QAYTA O'QILADI:
oqim bor bo'lsa amal bajarilgan, yo'q bo'lsa — HAQIQIY nosozlik.
=====================================================================
```

**Uch holatli tekshiruv:** `go2rtc.py:340-347`

```python
    async def _registered(self, stream_name: str) -> bool | None:
        """`has_stream`, LEKIN O'Z xatosini yutadi: `None` = «ayta olmadim».

        Uch holatli javob ATAYIN. Chaqiruvchi `PUT`/`DELETE` ning
        natijasini shu yerdan o'lchaydi va «tekshira olmadim» ni
        «hammasi joyida» deb talqin qilishi MUMKIN EMAS — ikkalasi ham
        FAIL-CLOSED yo'nalishda hal qilinadi.
        """
```

> **4-fazada bu ikki qoida to'g'ridan-to'g'ri qo'llanadi:**
> **(a)** `frame_source.py` `ensure_stream()` ni chaqiradi; **D-11 bo'yicha
> `remove_stream()` chaqirilmaydi** — go2rtc yalqov, tomoshabin bo'lmasa RTSP
> sessiyasini o'zi yopadi. `remove_stream()` faqat kamera arxivlanganda (3-fazadagi
> mavjud yo'l).
> **(b)** `/api/frame.jpeg` ning muvaffaqiyati ham **natijadan** o'lchanadi — javob
> **baytlarining o'zi** JPEG magic-baytidan boshlanishi shart. `Content-Type` sarlavhasi
> yetarli emas; RESEARCH §C.7 ning 1–2-qadamlari (dekodsiz magic/EOI darvozasi) aynan
> shuni to'sadi va ular NVR yoki go2rtc qaytargan **HTML xato sahifasini** ham tutadi.
>
> ⚠ **`/api/frame.jpeg?cache=` ISHLATILMAYDI** (RESEARCH Pitfall 8) — u eski kadrni
> qaytarishi mumkin va o'shanda «06:00 da rasta band edimi?» savoliga **boshqa vaqtdagi
> kadr** javob berardi.

---

### S-11. Compose — «yangi konteyner, uchinchi servis emas»

**Manba:** `compose.yaml:1-10` (profil ro'yxati — u HUJJAT, eskirtirilmaydi)

```yaml
# Profillar:
#   (yo'q)   -> db, cache, core-api, worker, go2rtc : `npm run up`
#   migrate  -> Alembic one-shot job   : `npm run migrate`
#   web      -> frontend (01-02 rejasi Dockerfile'ni yaratadi)
#   proxy    -> nginx
#   test     -> pytest + testcontainers: `npm run test`
#   sim      -> nvr-sim + nvr-sim-rtsp (CAM-09): `npm run test:sim`
```

**Bir xil kod bazasi, boshqa entrypoint:** `compose.yaml:165-190` (`worker`)

```yaml
  worker:
    # NVR KASHFIYOTINING FON ISHCHISI (03-06, D-06).
    #
    # ⚠ PROFILSIZ — VA BU ATAYIN. `nvr-sim` va `migrate` dan farqli o'laroq
    # bu ISHLAB CHIQARISH komponenti: `npm run up` uni ham ko'taradi.
    ...
    # TO'RTINCHI KONTEYNER, UCHINCHI SERVIS EMAS: `core-api` kod bazasining
    # boshqa entrypoint'i — `migrate` va `tests` bilan aynan bir xil naqsh,
    # ya'ni CLAUDE.md ning "aynan 3 ta servis" cheklovi buzilmaydi
    ...
    build:
      context: .
      dockerfile: services/core-api/Dockerfile
      target: runtime
    # `--workers 1` — `core-api` dagi bilan bir xil sabab: ikkinchi jarayon
    # 4-fazada qo'shiladigan cron vazifalarini IKKI MARTA ishga tushirardi.
    command: ["taskiq", "worker", "app.worker:broker", "--workers", "1"]
```

> **`scheduler` konteyneri AYNAN shu blokdan nusxa olinadi** —
> `command: ["taskiq", "scheduler", "app.worker:scheduler"]`, **profilsiz**,
> `target: runtime`, `restart: unless-stopped`, `depends_on: cache`.
> D-03 tufayli «aynan bitta planer» talabi **yo'q**, lekin `worker.py:187-189` dagi
> izoh (`--workers 1` sababi) endi ikkinchi mazmunga ega bo'ladi va u yangilanadi.
>
> **`storage` (SeaweedFS) esa `go2rtc` blokidan nusxa olinadi** (`compose.yaml:234-280`):
> tayyor image, **`ports:` bloki YO'Q**, `:ro` mount qilingan konfiguratsiya,
> `nc -z` healthcheck. `compose.yaml:256-266` dagi ogohlantirish so'zma-so'z tegishli:
> «compose `ports:` bandi Docker'ning `iptables` qoidalarini yozadi va u host
> firewall'ini CHETLAB O'TADI — ya'ni "UFW da yopiq" degan ishonch yolg'on bo'lib
> qolardi».

**`.env` va sirlar** — `worker` bloki (`compose.yaml:213-221`):

```yaml
      # ⚠ SHIFR KALITI SHU YERDA MAJBURIY (03-04 ning ochiq bandi).
      ...
      # `:-` bilan bo'sh standart berish esa undan YOMONROQ
      # bo'lardi: worker ko'tarilib, xato faqat birinchi kashfiyotda
      # chiqardi (T-03-22).
      NVR_CREDENTIAL_KEY: ${NVR_CREDENTIAL_KEY}
```

> **`S3_ACCESS_KEY` / `S3_SECRET_KEY` uchun aynan shu qaror:** `:-` bilan bo'sh
> standart **berilmaydi**. `TELEGRAM_BOT_TOKEN` esa **teskari** —
> `${TELEGRAM_BOT_TOKEN:-}` bo'ladi va bo'sh token «alertlar o'chiq + `log.warning`»
> degani (RESEARCH Environment Availability: token yo'qligi fazani **bloklamaydi**).
> Ikkala qaror ham sabab bilan `compose.yaml` izohida yoziladi.

---

### S-12. Simulyator — `/__sim__` control-plane KENGAYTIRILADI, ikkinchi mexanizm QURILMAYDI

**Manba:** `services/nvr-sim/sim/state.py:55-83`

```python
SIM_MODES: frozenset[str] = frozenset(
    {
        "ok",
        "bad_password",
        ...
        "unreachable",
    }
)
"""`03-RESEARCH.md` B.8 jadvalidagi barcha rejimlar (`ok` + o'n oltita xato rejimi).

⚠ `unreachable` — YAGONA rejim, u `/__sim__/state` bilan O'RNATILMAYDI: uni
qayta tug'dirishning yagona haqiqiy yo'li konteynerni to'xtatish ...
"""
```

**Qisman yangilash va NOMA'LUM KALIT rad etilishi:** `state.py:191-206`

```python
def apply_patch(state: SimState, patch: dict[str, Any]) -> SimState:
    """`POST /__sim__/state` — **QISMAN** yangilash: berilmagan maydon tegilmaydi.

    Noma'lum kalit **jimgina tashlab yuborilmaydi**: test "men rejimni
    o'rnatdim" deb o'ylab, aslida hech nima o'zgarmagan holatda ishlashi —
    aynan shu fazada eng qimmat turdagi yolg'on-yashil bo'lardi.
    """
    read_only = set(patch) & READ_ONLY_FIELDS
    if read_only:
        raise SimStateError(...)
    unknown = set(patch) - PATCHABLE_FIELDS
    if unknown:
        raise SimStateError(f"noma'lum maydon(lar): {sorted(unknown)}")
```

**Sanagichlar tashqaridan o'rnatilmaydi:** `state.py:173-178`

```python
READ_ONLY_FIELDS: frozenset[str] = frozenset({"stream_claims", "auth_attempts", "endpoint_hits"})
"""SANAGICHLAR — tashqaridan o'rnatilmaydi.

Aks holda test o'zi o'lchayotgan qiymatni o'zi yozib qo'yardi. Ularni nolga
qaytarishning yagona yo'li — `POST /__sim__/reset`.
"""
```

**Control-plane marshrutlari:** `sim/main.py:76, 246-291`
(`/__sim__/state` GET+POST, `/__sim__/reset`, `/__sim__/attempts`, keyin
`@app.api_route(...)` bilan `/ISAPI/{path}`).

**Test tomonidagi jufti:** `tests/fixtures/nvr_sim.py:101-155` — `sim_patch`, `sim_mode`,
`sim_reset`, `sim` fixture'i (har testdan **oldin ham, keyin ham** `reset`).

> **4-faza qo'shadigan uchta narsa va ular MAVJUD mexanizmga ulanadi:**
>
> | Ehtiyoj | Qayerga | Naqsh manbai |
> |---------|---------|--------------|
> | Buzuq / kesilgan JPEG | `SimState.frame_mode` (`"ok"` / `"truncated"` / `"html"` / `"empty"`) + `PATCHABLE_FIELDS` ga qo'shish | `state.py:98-134`, `:168-184` |
> | ISAPI `/picture` endpointi | `services/nvr-sim/sim/isapi.py` — mavjud `/ISAPI/*` marshrutlashi ichida | `sim/main.py:287-291` |
> | Qorong'i / bo'sh / past-kontrast **oqim** | `ops/mediamtx/mediamtx.yml` `paths:` — kanal raqami bo'yicha (`color=c=black`, `color=c=gray`) | `mediamtx.yml` `runOnDemand` + `pathDefaults` |
>
> 🔴 **«Simulyator o'zini o'zi tasdiqlaydi» antinaqshi (3-fazadan meros).**
> Sim kadrni **fizik xususiyat** bilan yasashi kerak («o'rtacha yorug'ligi 8 bo'lgan
> kadr»), **detektorning chegarasi bilan emas**. Fixture nomlari:
> `frame_mean_8_stddev_2` ✅, `frame_rejected_by_filter` ❌.
>
> ⚠ **MediaMTX RTSP oyog'i `network_mode: service:nvr-sim` bilan ulangan**
> (`compose.yaml:384-433`) — real qurilmada ISAPI ham, RTSP ham **bitta manzilda**
> yashaydi. Yangi sifat-yo'llari **o'sha netns ichida** qoladi; ikkinchi konteyner
> qo'shilmaydi.
>
> ⚠ **`mediamtx.yml` dagi parol `compose.yaml` dagi `SIM_PASSWORD` bilan bir xil
> bo'lishi SHART** va buni `tests/unit/test_compose_sim_env.py` mexanik to'sadi
> (`mediamtx.yml` ning `authInternalUsers` izohida yozilgan). Yangi yo'llar
> qo'shilganda o'sha test kengaytiriladi.
>
> ⚠ **Ilova kodida sim tarmoqlanishi YO'Q** — `tests/unit/test_no_sim_branching.py`
> `services/core-api/app/` ichida `nvr-sim`, `__sim__`, `SIM_` satrlarini izlaydi.
> Yangi `frame_mode` **faqat sim tomonda** yashaydi.

---

### S-13. Faza darvozasi — mezon boshiga BITTA test + META-TEST

**Manba (verbatim):** `tests/integration/test_phase3_criteria.py:1040-1066`

```python
def test_every_criterion_has_its_own_test() -> None:
    """Sakkizala mezon uchun AYNAN BITTA nomlangan test mavjud.

    USIZ MEZONLARDAN BIRI JIMGINA TUSHIB QOLARDI: fayl qayta tashkil
    qilinganda yoki test vaqtincha o'chirilganda darvoza baribir yashil
    bo'lardi va «sakkizala mezon o'lchanadi» da'vosi isbotsiz qolardi.

    ⚠ META-TESTNING O'Z NOMIDA `sc<raqam>` YO'Q va bu ataylab: qabul
      mezoni `--collect-only` chiqishida `sc[1-8]` naqshini SANAYDI, ya'ni
      meta-testning o'zi sanoqqa kirib ketmasligi kerak.
    """
    module = sys.modules[__name__]
    names = sorted(
        name
        for name, obj in inspect.getmembers(module, inspect.isfunction)
        if name.startswith("test_") and obj.__module__ == __name__
    )

    for number in range(1, 9):
        owned = [name for name in names if name.startswith(f"test_sc{number}_")]
        assert len(owned) == 1, (...)

    criteria = [name for name in names if name.startswith("test_sc")]
    assert len(criteria) == 8, f"mezon testlari soni 8 emas: {criteria}"
```

**Ikkinchi darvoza — MOCK'SIZ o'lchov SAQLANADI:** `test_phase3_criteria.py:1120-1124`

```python
    mocked = [name for name, obj in tests if MOCK_FIXTURE in inspect.signature(obj).parameters]
    assert mocked == [], (
        f"`{E2E_MODULE}` dagi {mocked} testi go2rtc mock'ini so'rayapti — mock'siz "
        "o'lchov aynan shu bilan yo'q qilinadi va GAP-2 qayta ochilardi"
    )
```

> **4-fazada:** `test_phase4_criteria.py` da **beshta** mezon (`range(1, 6)`,
> `len(criteria) == 5`). Mock'siz o'lchovning jufti — `test_storage_layout.py`:
> u **haqiqiy SeaweedFS konteyneriga** boradi, S3 mock'iga emas. Aynan shu darvoza
> yozilmasa, birinchi «qulaylik uchun» `moto` mock'i S3 imzolash yo'lini butunlay
> o'lchanmagan qoldirardi — 03-14 nosozligining aynan takrori.

---

### S-14. Frontend — kalitlar TUG'ILISHIDANOQ market-scoped

`03-PATTERNS.md` §S-10 va §3.13 **o'zgarishsiz amal qiladi**. Qisqacha:

```ts
// frontend/src/lib/schedule-queries.ts
import { domainKey } from "./market-queries";   // ikkinchi nusxa YARATILMAYDI

export const schedulesKey = (marketId: string) => domainKey(marketId, "schedules");
export const captureRunsKey = (marketId: string, day: string) =>
  domainKey(marketId, "capture-runs", day);
```

`enabled: marketId !== null` — **kontrakt, qulaylik emas** (`market-queries.ts:185-192`
dagi izoh: bozorsiz sessiyada `409 market_not_selected` kesh grafida yashab qolardi).

**i18n Cyrillic allowlist** — `frontend/scripts/gen-cyrillic.test.mjs::allowed` regexi
va `uz-Cyrl.overrides.json -> words` **juft** yuritiladi. 4-faza kutiladigan yangi
lotin atamalari: `S3`, `SeaweedFS`, `JPEG`, `IR`, `Telegram`, `Sentry`, `UTC`.

---

## 3. Pattern Assignments — fayl bo'yicha

### 3.1 `migrations/versions/0014_snapshot_domain.py` + Wave 0 D-23 zondi

**Analog:** `migrations/versions/0012_nvr_domain.py` — **to'liq shablon**, satrma-satr.

**Fayl sarlavhasi (shakl `0012_nvr_domain.py:1-54` dan):** «BU MIGRATSIYADA QOTIB
QOLADIGAN QARORLAR» bloki majburiy. 4-faza uchun kamida beshta band:

1. `capture_runs` **audit triggeridan chiqarilgan** (hajm + hodisa jurnali — §S-1)
2. `business_date` **`scheduled_at` dan**, `created_at` dan EMAS (RESEARCH §A.1)
3. `UNIQUE (market_id, camera_id, business_date, slot_time)` — CAM-05 ning DB kafolati
4. `UNIQUE (id, is_billable)` — 5-faza uchun ILGAK (§S-6)
5. `EXCLUDE USING gist (market_id WITH =, period WITH &&)` — «bir kunga bitta profil»

**Revision bloki:** `0012_nvr_domain.py:85-89`

```python
revision: str = "0012"
down_revision: str | Sequence[str] | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None
```

**RLS + audit tsikllari — IKKI ALOHIDA RO'YXAT ustidan:** `0012_nvr_domain.py:454-471`

```python
    for table in NVR_TENANT_TABLES:
        enable_tenant_rls(table)
        create_entity(tenant_policy(table))
        create_entity(owner_bootstrap_policy(table))
    ...
    for table in NVR_AUDITED_TABLES:
        attach_audit_trigger(table)
```

**`downgrade()` — teskari tartib:** `0012_nvr_domain.py:474-492`

```python
def downgrade() -> None:
    """Downgrade schema."""
    for table in reversed(NVR_AUDITED_TABLES):
        detach_audit_trigger(table)

    for table in reversed(NVR_TENANT_TABLES):
        drop_entity(owner_bootstrap_policy(table))
        drop_entity(tenant_policy(table))

    op.drop_index(TUNNEL_SUBNET_INDEX, table_name="nvr_devices")
    ...
    # TARTIB — FK bo'yicha BOLALARDAN ota-onaga: uchala bolasi ham
    # `nvr_devices` ga composite FK bilan tayanadi.
    op.drop_table("nvr_discovery_runs")
```

> ⚠ **`require_extension("btree_gist")` BU FAZADA QAYTA KERAK BO'LADI.**
> `0012_nvr_domain.py:46-53` da «kengaytma kerak emas» deb yozilgan, lekin sabab
> **`ExcludeConstraint` yo'qligida** edi. 4-fazada `snapshot_schedules` da
> `EXCLUDE USING gist (market_id WITH =, period WITH &&)` bor, ya'ni
> `0009_vendors.py:136` shakli qaytadi:
>
> ```python
>     require_extension("btree_gist")
> ```
>
> **U migratsiyaning birinchi satri bo'ladi** va `op.execute("CREATE EXTENSION ...")`
> **YOZILMAYDI** (`sbozor_owner` `NOCREATEDB` — `0009_vendors.py:118-136` da
> o'lchangan). Kengaytma `ops/db/init/00-extensions.sql` da o'rnatiladi va
> `tests/tenancy/test_meta.py:234::test_btree_gist_extension_is_installed`
> uni allaqachon qulflagan.
>
> ⚠ **ALEMBIC `ExcludeConstraint` NI KO'RMAYDI** — `0009_vendors.py:29-40` dagi
> ogohlantirish bu faylga **TEGISHLI**: konstraytni **ikki tomonda** ham yozing
> (modelda `ExcludeConstraint(...)` — `models/market.py:596`, migratsiyada
> `pg.ExcludeConstraint(...)` — `0009_vendors.py:232`).

**`daterange` chegara konventsiyasi** — `sbozor_core/periods.py:43-45`:

```python
__all__ = ["PERIOD_BOUNDS", "assignment_period", "period_contains"]

PERIOD_BOUNDS: Final[Literal["[)"]] = "[)"
```

Xom `Range(...)` **yozilmaydi** — `assignment_period()` (`periods.py:60-89`) ishlatiladi
yoki uning jufti yoziladi.

**Generated `business_date` ifodasi** — nusxa **ATAYIN**, sababi
`models/market.py:186-201`:

```python
TARIFF_BUSINESS_DATE_EXPR = "((created_at AT TIME ZONE 'Asia/Tashkent')::date)"
"""`tariffs.business_date` generated column ifodasi.

`migrations/helpers.py::BUSINESS_DATE_EXPR` bilan AYNAN bir xil bo'lishi
SHART. Nusxa bo'lishining sababi bog'liqlik yo'nalishi: `migrations.helpers`
`alembic.op` ni import qiladi, `sbozor_core` esa migratsiya vositalariga
bog'lanmaydi (u uchala servisda ishlaydi).
...
IKKI ARGUMENTLI `AT TIME ZONE` shakli MAJBURIY: u IMMUTABLE, bitta
argumentli varianti esa STABLE va generated column'da umuman ruxsat
etilmaydi.
"""
```

4-faza jufti — `CAPTURE_BUSINESS_DATE_EXPR = "((scheduled_at AT TIME ZONE 'Asia/Tashkent')::date)"`,
va **farqning sababi docstringga yoziladi** (reja qatori tegishli kunidan **oldin**
yaratiladi, ya'ni `created_at` 00:00–00:05 oynasida qatorni oldingi kunga yozardi).

**Model tomonidagi shakl** — `models/market.py:519-523`:

```python
    business_date: Mapped[date] = mapped_column(
        Date(),
        Computed(TARIFF_BUSINESS_DATE_EXPR, persisted=True),
        nullable=False,
    )
```

---

**WAVE 0 ZONDI (D-23) — analog `tests/fixtures/financial.py`**

Zond **birinchi migratsiyadan OLDIN** yoziladi va `financial.py` ning shaklini
takrorlaydi: probe jadvallari, DDL alohida qo'llanadi, natija o'lchanadi.

```python
# `financial.py:70-90` shaklidagi ikki probe jadvali:
_CREATE_PARENT = """
CREATE TABLE probe_snapshots (
    id              uuid PRIMARY KEY DEFAULT uuidv7(),
    quality_verdict text NOT NULL,
    is_billable     boolean GENERATED ALWAYS AS (quality_verdict = 'ok') STORED,
    CONSTRAINT uq_probe_snapshots_billable_anchor UNIQUE (id, is_billable)
)
"""
_CREATE_CHILD = """
CREATE TABLE probe_occupancy (
    id                   uuid PRIMARY KEY DEFAULT uuidv7(),
    snapshot_id          uuid NOT NULL,
    snapshot_is_billable boolean NOT NULL DEFAULT true,
    CONSTRAINT ck_probe_occupancy_billable CHECK (snapshot_is_billable),
    CONSTRAINT fk_probe_occupancy_snapshot
        FOREIGN KEY (snapshot_id, snapshot_is_billable)
        REFERENCES probe_snapshots (id, is_billable)
)
"""
```

**Ikki mustaqil da'vo o'lchanadi va ular ALOHIDA testlar:**

1. `UNIQUE (id, is_billable)` yaratiladimi (generated ustun `UNIQUE` da) — **bu
   allaqachon isbotlangan sinf** (`financial.py`), lekin zond uni bu shaklda ham
   tasdiqlaydi;
2. O'sha `UNIQUE` **kompozit FK nishoni** bo'la oladimi — **BU O'LCHANMAGAN**.

Yiqilgan holda zaxira (`0014` ga) — `is_billable` oddiy `boolean NOT NULL` +
`BEFORE INSERT/UPDATE` trigger. Kafolat saqlanadi, narxi ~15 qator.

---

### 3.2 `packages/sbozor-core/sbozor_core/models/snapshot.py`

**Analog:** `packages/sbozor-core/sbozor_core/models/nvr.py` — **to'liq shablon**
(525 qator, to'rt klass, indeks konstantalari, enum-hosila `CHECK` ifodalari).

**Beshta klass va ularning `__table_args__` da MAJBURIYSI:**

| Klass | Mixinlar | Majburiy elementlar |
|-------|----------|---------------------|
| `SnapshotSchedule` | `Base, TenantMixin, TimestampMixin` | FK→`markets`, `UNIQUE(market_id, id)`, `ExcludeConstraint(market_id =, period &&)`, `CHECK (NOT isempty(period))` |
| `SnapshotScheduleSlot` | `Base, TenantMixin` | composite FK→`(snapshot_schedules.market_id, .id)` `ON DELETE CASCADE`, `UNIQUE(market_id, schedule_id, slot_time)` |
| `CaptureRun` | `Base, TenantMixin` | composite FK→`cameras`, `UNIQUE(market_id, camera_id, business_date, slot_time)`, `UNIQUE(market_id, id)`, `business_date` `Computed(..., persisted=True)`, status `CHECK` enum'dan |
| `Snapshot` | `Base, TenantMixin` | composite FK→`capture_runs`, `UNIQUE(market_id, capture_run_id)`, `UNIQUE(market_id, object_key)`, **`UNIQUE(id, is_billable)`**, `is_billable` `Computed` |
| `AlertEvent` | `Base, TenantMixin` | `UNIQUE(market_id, id)`, qisman UNIQUE (ochiq alert bo'yicha debounce) |

**Ustun yordamchilari (`models/base.py` dan, o'zgartirilmaydi):** `uuid_pk()`,
`market_fk_column()` (`TenantMixin` orqali), `TimestampMixin`.

> ⚠ **`scheduled_at` USTUNI `capture_runs` DA HAM, `snapshots` DA HAM BOR va bu
> denormalizatsiya ATAYIN.** Sababni docstringda yozing — 5/6-faza so'rovlari
> `snapshots` dan `capture_runs` ga `JOIN` qilmasdan biznes-kunni olishi kerak.
> Uslub namunasi — `models/nvr.py:209-218` (`rtsp_port` / `rtsp_port_assumed` juftligi:
> «Ularni bitta ustunga birlashtirib bo'lmaydi … DIAGNOSTIKADA butunlay boshqa holat»).
>
> ⚠ **`capture_runs.nvr_id` — DENORMALIZATSIYA, IDENTIFIKATSIYA EMAS** (RESEARCH §B.4:
> «Kalitda `nvr_id` YO'Q»). Kamera boshqa NVR'ga ko'chirilsa tarixdagi slotlar
> identifikatori o'zgarmasligi kerak. Bu qaror ham docstringda — namuna
> `models/nvr.py:222-226` (`serial_number` «Kalit sifatida ISHLATILMAYDI»).
>
> ⚠ **`snapshots` da kadr BAYTLARI YO'Q** — faqat `object_key`, `size_bytes`, `etag`.
> Bu `cameras` da `rtsp_url` ustuni yo'qligining aynan bir oilasidagi qaror
> (`0012_nvr_domain.py:26-31`) va u ham docstringda yoziladi, aks holda keyingi
> tahrirlovchi «qulaylik uchun» `bytea` ustuni qo'shadi.

**Enum e'loni** — `sbozor_core/enums.py:87-138` (`CameraStatus`, `DiscoveryRunStatus`)
shakli; keyin `models/snapshot.py` da `_quoted()` bilan `CHECK` ifodasi hosil qilinadi
(`models/nvr.py:104-117`).

**Barrel:** `packages/sbozor-core/sbozor_core/models/__init__.py` — beshta yangi nom
(`__all__` va import).

---

### 3.3 `services/core-api/app/jobs/capture.py`

**Analog:** `services/core-api/app/jobs/discovery.py` — **to'liq shablon** (623 qator).

**Ko'chiriladigan beshta element:**

| Element | Manba | Nima uchun |
|---------|-------|------------|
| `_system_transaction()` | `discovery.py:170-205` | §S-3 — busiz tick jimgina 0 qator ko'radi |
| Deterministik `request_id` | `discovery.py:265-269` | «Tasodifiy qiymat har tranzaksiyada boshqa bo'lardi va bitta skanning audit qatorlarini bir ipga bog'lash imkonsiz bo'lardi» → tick uchun `f"job-capture-{business_date}-{slot}"` |
| `_DeviceContext` naqshi (ORM emas, oddiy qiymatlar) | `discovery.py:334-358` | Tranzaksiya yopilgandan keyin ORM obyektiga tegish `expire_on_commit` ga bog'lanib qolardi |
| `_Finisher` — `failed` yozuvining YAGONA joyi | `discovery.py:559-622` | Uch xato yo'li uni baham ko'radi; `done` bayrog'i «na muvaffaqiyat, na nosozlik yozilgan» holatini imkonsiz qiladi |
| «JOB JARAYONI HECH QACHON YIQILMAYDI» | `discovery.py:61-65, 329-331` | Navbat yiqilgan vazifani qayta yetkazishi mumkin |

**Xato ushlash zanjiri (verbatim):** `discovery.py:323-331`

```python
    except NvrError as error:
        # TANILGAN sabab — kod va tafsilot ALLAQACHON allowlist'dan
        # o'tgan (`NvrError` konstruktori), ya'ni ular to'g'ridan-to'g'ri
        # yoziladi.
        log.info("nvr_discovery_failed", error_code=error.code, **context)
        await finish.failed(error.code, error.detail)
    except Exception as exc:  # noqa: BLE001 - job jarayoni yiqilmasligi SHART
        log.exception("nvr_discovery_crashed", **context)
        await finish.failed(JOB_INTERNAL_ERROR, _raw(type(exc).__name__))
```

**`error_detail` chegarasi (verbatim):** `discovery.py:160-166, 219-221`

```python
_MAX_DETAIL_CHARS: Final[int] = 500
"""Job yozadigan `error_detail["raw"]` ning chegarasi.
...
Chegarasiz istisno matni (masalan uzun SQL) `jsonb` ustuniga cheksiz
o'sardi (T-03-30 bilan bir xil mulohaza, boshqa yo'lda).
"""


def _raw(message: str) -> dict[str, Any]:
    """`error_detail` ning yagona shakli — `raw` kaliti (UI-SPEC §7.4 allowlist'i)."""
    return {"raw": message[:_MAX_DETAIL_CHARS]}
```

**Alohida qisqa tranzaksiya — progress uchun:** `discovery.py:529-556`
(`_publish_channels_found`) — **xato yutiladi**, chunki bu progress ko'rsatkichi:

```python
    """`channels_found` ni ALOHIDA, QISQA tranzaksiyada yozadi (UI-SPEC §5.2 [TALAB]).

    ⚠ XATO YUTILADI (jurnalga yozib). Bu yozuv PROGRESS ko'rsatkichi, skan
      natijasi emas: uning yiqilishi butun kashfiyotni to'xtatishi mumkin
      emas. Aynan shu mulohaza `audit.py::_write_read_audit` da ham bor va
      u yerda ham xato yutiladi.
    """
```

> **4-fazada bu shakl Telegram alertiga qo'llanadi:** alert jo'natish **kadr olishni
> bloklay olmaydi** (RESEARCH talab→test xaritasi:
> `test_telegram_failure_does_not_block_capture`). Ya'ni `alerts.py` chaqiruvi
> `_publish_channels_found` bilan **aynan bir xil** shaklda — o'z tranzaksiyasi,
> yutilgan xato, `log.warning`.

**`capture_tick` ning to'rt qadami (RESEARCH §A.2 diagrammasi) va ularning tranzaksiya
chegaralari:**

```
0. release_expired()      — lease tugagan `running` -> `pending`   [1-tranzaksiya, bozorsiz*]
1. ensure_plan(business_date=bugun)  ON CONFLICT DO NOTHING        [bozor bo'yicha]
2. mark_overdue_as_missed()          grace oynasidan tashqari      [bozor bo'yicha]
3. claim_due()  SELECT … FOR UPDATE SKIP LOCKED LIMIT n            [bozor bo'yicha]
4. NVR bo'yicha guruhlab `capture_batch` larni navbatga qo'yish     [tranzaksiyadan KEYIN]
```

`*` 0-qadam `SECURITY DEFINER` funksiya orqali yoki har bozor kontekstida — §S-3.

> 🔴 **4-qadam TRANZAKSIYADAN KEYIN.** `discovery.py:479-490` da `IsapiClient` ning
> `async with` bloki tranzaksiya **ichida** turadi va bu sabab bilan yozilgan
> (`discovery.py:42-59`: uzun tranzaksiya ataylab). Tick esa **teskari**: navbatga
> qo'yish tranzaksiya ichida bo'lsa, `COMMIT` yiqilganda vazifa allaqachon
> yuborilgan bo'lardi va worker mavjud bo'lmagan `running` qatorni izlardi.

---

### 3.4 `services/core-api/app/repositories/capture_repo.py`

**Analog:** `app/repositories/nvr_repo.py` — **shartli holat o'tishi** uchun; lekin
`SELECT … FOR UPDATE SKIP LOCKED` uchun **analog yo'q** (§4.1).

**Shartli o'tishning verbatim shakli:** `nvr_repo.py:534-565`

```python
    async def start_run(self, run_id: UUID) -> bool:
        """`queued` -> `running`. Boshqa holatdan o'tkazmaydi (03-06).

        ⚠ `status == 'queued'` SHARTI DARVOZA, TOZALIK EMAS. Navbatlar
          vazifani "KAMIDA BIR MARTA" yetkazadi, ya'ni bir xil `run_id`
          bilan ikkinchi chaqiruv MUMKIN. Shartsiz `UPDATE` ikkinchi jobni
          ham ishga tushirardi ...
        Returns:
            Qator `queued` holatda topilgan va `running` ga o'tgan bo'lsa
            `True`. `False` — qator yo'q, boshqa holatda yoki (tenant
            konteksti o'rnatilmagan bo'lsa) RLS uni ko'rsatmadi.
        """
        result = await self.session.execute(
            update(NvrDiscoveryRun)
            .where(
                NvrDiscoveryRun.market_id == self.market_id,
                NvrDiscoveryRun.id == run_id,
                NvrDiscoveryRun.status == DiscoveryRunStatus.QUEUED.value,
            )
            .values(status=DiscoveryRunStatus.RUNNING.value)
            .returning(NvrDiscoveryRun.id)
        )
        return result.scalar_one_or_none() is not None
```

**«Tekshir-keyin-yoz» ATAYIN QILINMAYDI:** `nvr_repo.py:509-517`

```python
        """Yangi kashfiyot yugurishini `queued` holatida yozadi.

        ⚠ «Faol yugurish bormi?» TEKSHIRILMAYDI — bu ataylab.
          `0012` dagi QISMAN UNIQUE indeks ... ikkinchi faol yugurishni
          `23505` bilan rad etadi va chaqiruvchi uni 409 ga aylantiradi
          (03-06). Oldindan tekshirish «tekshir-keyin-yoz» poygasini
          tug'dirardi ...
```

> **`ensure_plan()` aynan shu falsafada quriladi:** `INSERT … ON CONFLICT DO NOTHING`,
> hech qanday «bugungi reja bormi?» tekshiruvisiz. `UNIQUE (market_id, camera_id,
> business_date, slot_time)` poygani DB darajasida hal qiladi.

**Baza klass — IKKINCHI qatlam filtri:** `packages/sbozor-core/sbozor_core/tenancy.py`
(`TenantScopedRepository`) — RLS himoya to'ri bo'lsa ham, so'rovga `market_id`
predikatini qo'shish **majburiy**. Yuqoridagi `.where(... .market_id == self.market_id ...)`
aynan shu.

**Xom `text()` ishlatilganda bind parametrlari TIPLANADI** — `nvr_repo.py:29-41`
(modul docstringi) va `market_repo.py:152-163`:

```python
_ACTIVATE_MARKET = text("SELECT market_activate(:market_id)").bindparams(
```

> 🔴 `claim_due()` ning CTE + `UPDATE … FROM … RETURNING` so'rovi SQLAlchemy ORM'da
> ifodalanmaydi — u **xom `text()`** bo'ladi. Ya'ni `:grace_seconds`, `:lease_seconds`,
> `:batch`, `:worker_id` **hammasi `bindparam(..., type_=...)` bilan tiplanadi**, aks
> holda asyncpg'ga xom `str` borardi (`nvr_repo.py:29-41` da o'lchangan sinf).

---

### 3.5 `services/core-api/app/services/frame_source.py`

**Analog:** `app/services/go2rtc.py` (yupqa qobiq, sirsiz xato, natijadan o'lchash) +
`app/services/isapi/client.py` (Digest, timeout byudjeti, teskari retry).

**Klient qobig'ining shakli:** `go2rtc.py:190-217`

```python
class Go2rtcClient:
    """`httpx.AsyncClient` ustidagi YUPQA qobiq — uchta amal, boshqa hech nima.

    ⚠ `PATCH /api/config` VA `POST /api/restart` UMUMAN YO'Q. Ular
      «kerak bo'lib qolsa» qo'shiladigan qulayliklar emas ... Metodning
      yo'qligi — kelishuv emas, STRUKTURA.

    Klient `app.state` da SAQLANMAYDI: u `async with` bilan qisqa
    muddatga ochiladi. ...
    """

    def __init__(self, base_url: str, *, timeout: float = _TIMEOUT_SECONDS) -> None:
        self._client = httpx.AsyncClient(base_url=base_url, timeout=timeout)
```

> **4-fazada klient egaligi TESKARI:** kadr olish **siyrak emas** — 175 chaqiruv/kun/bozor
> va cho'qqida bitta daqiqada 25 ta. Ya'ni `frame_source` klienti worker jarayonining
> `TaskiqState` ida yashaydi (`worker.py:181-199` shakli), har chaqiruvda qayta
> ochilmaydi. `go2rtc.py:199-203` dagi «siyrak muloqot» dalili bu yerda **amal
> qilmaydi** va farqni docstringda yozish shart.

**Uchta usul bitta protokol ortida (D-06) va tanlov BAZADAN keladi** —
`discovery.py:208-216` naqshi:

```python
def _base_url(host: str, port: int, *, use_tls: bool) -> str:
    """`nvr_devices` qatoridan ISAPI bazaviy manzili.

    Manzil BAZADAN quriladi va boshqa hech qayerdan: "real qurilmaga
    o'tish — SOZLAMA o'zgarishi, kod o'zgarishi emas" (SC#7) da'vosining
    butun mazmuni shunda.
    """
```

**Allow-list darvozasi ENG BOSHIDA:** `go2rtc.py:298-302`

```python
        # ⚠ DARVOZA ENG BOSHIDA — tarmoqqa chiqishdan OLDIN. Keyin
        #   tekshirilsa xavfli qiymat allaqachon go2rtc'ga yuborilgan
        #   bo'lardi (T-03-37 dagi «chegara qurilmaga borishdan oldin»
        #   bilan aynan bir xil mulohaza).
        assert_safe_go2rtc_src(source)
```

**Xato taksonomiyasi:** `app/services/isapi/errors.py` — reyestr shakli va
`tests/unit/test_isapi_errors.py::test_registry_has_exactly_twelve_unique_codes`
darvozasi (`discovery.py:123-127` da nomi bilan keltirilgan). 4-faza kodlari
(`capture_no_frame`, `capture_not_jpeg`, `capture_timeout`, `capture_stream_limit`, …)
aynan shu shaklda va **o'z sanoq darvozasi** bilan.

---

### 3.6 `services/core-api/app/services/quality.py` va `object_key.py`

**Analog (shakl):** `app/services/live_source.py` va `app/services/rtsp.py` — sof
funksiya modullari (tarmoqqa chiqmaydi, bazaga tegmaydi, holat saqlamaydi).
**`Pillow` chaqiruvlarining o'zi uchun analog yo'q** (§4.3).

**Sof modul docstringining shakli:** `live_source.py:1-5`

```
"""RTSP manbaiga rekvizit qo'shadigan YAGONA joy (D-12, T-03-88, RESEARCH D.13).

Sof funksiyalar moduli (`rtsp.py` bilan bir xil shakl): tarmoqqa
chiqmaydi, bazaga tegmaydi, holat saqlamaydi.
"""
```

**Xato kodlari — modul darajasidagi konstanta + docstring:** `live_source.py:80-106`

```python
NOT_AN_RTSP_SOURCE = "rtsp_source_not_rtsp"
"""Sxema `rtsp` emas yoki avtoritet o'qib bo'lmaydigan shaklda."""
...
CREDENTIAL_INJECTION = "rtsp_credential_injection"
"""Rekvizit manzilning avtoritetini yoki yo'lini O'ZGARTIRDI (T-03-88).

Bu holat to'g'ri kodda HECH QACHON yuz bermaydi — u faqat foizli kodlash
buzilganda chiqadi. Ya'ni bu satr ko'rinishi KODDA xato borligining
belgisi va uni jimgina yutish mumkin emas.
"""
```

4-faza jufti: `MIN_BYTES`, `MAX_BYTES`, `BLANK_STDDEV`, `DARK_MEAN`, `DARK_STDDEV`,
`IR_SATURATION`, `NIGHT_MEAN`, `QUALITY_THRESHOLDS_VERSION` — **har biri docstring
bilan**, va **ular `Settings` dan sozlanadi** (D-15: chegaralar LOW confidence).

> 🔴 **`dark` IKKI SHARTLI bo'lishi SHART** (D-14):
> `dark := mean < DARK_MEAN VA stddev < DARK_STDDEV`. Yagona shartli qoida qonuniy
> qish-tong kadrlarini oylab jimgina tashlab yuborardi. Bu **kod izohida** yoziladi —
> `live_source.py:100-106` dagi «bu satr ko'rinishi KODDA xato borligining belgisi»
> uslubida.
>
> 🔴 **`ImageFile.LOAD_TRUNCATED_IMAGES` `False` bo'lib qolishi SHART.**
> Darvoza: `tests/unit/test_quality_filter.py::test_truncated_images_flag_is_false`.
> Uslubiy analog — `tests/unit/test_no_sim_branching.py` va
> `tests/integration/test_rate_limit_proxy.py:486-496`: **global holatni o'qib,
> taqiqlangan qiymatni rad etadigan darvoza**.
>
> 🔴 **VERDIKT HISOBLANADIGAN EMAS, YOZISH PAYTIDA QO'YILADI** (RESEARCH §C.7).
> `quality_thresholds_version` u qaysi chegara to'plami bilan qo'yilganini yozadi.
> Aks holda chegarani o'zgartirish o'tmishdagi kadrlarning billing yaroqliligini
> **retroaktiv** o'zgartirardi. Bu `models/market.py:472-475` dagi «`valid_to` USTUNI
> YO'Q (Pitfall 9)» qarori bilan bir oiladagi o'zgarmaslik mulohazasi.

**`object_key.py` — sof URL/kalit fabrikasi**, analog `app/services/rtsp.py`.
Kalit shakli (RESEARCH §D.9): `{market_id}/{business_date}/{camera_id}/{HHMM}.jpg`.
Test analogi — `tests/unit/test_rtsp_url.py` (`tests/unit/test_periods.py` shaklida).

---

### 3.7 `services/core-api/app/services/storage.py`

**Analog:** yo'q (§4.2). Quyidagilar — **strukturaviy qo'shnilar** va ular qaysi
jihatdan ko'chiriladi:

| Jihat | Qaysi mavjud fayldan | Nima ko'chiriladi |
|-------|----------------------|-------------------|
| Yupqa qobiq, metod yo'qligi = struktura | `go2rtc.py:190-203` | `create_bucket`/`delete_bucket` **umuman yozilmaydi** (RESEARCH §D.9: `Admin` amali berilmaydi) |
| Sirsiz xato sinfi | `go2rtc.py:120-160` | `StorageError` + `_failure()`: **amal + istisno turi + status**, endpoint URL'siz |
| Resurs egaligi | `worker.py:181-207` | S3 sessiyasi `WORKER_STARTUP` da ochiladi, `WORKER_SHUTDOWN` da yopiladi |
| Sozlamani startup'da tekshirish | `app/settings.py:84-92` (`field_validator`) | `S3_ACCESS_KEY` bo'sh bo'lsa **ishga tushishda** yiqilsin, birinchi kadrda emas |
| «Bu yo'l ATAYIN yo'q» izohi | `sbozor_core/security.py:6-11` | «S3 hech qachon so'rov mexanizmi emas» qoidasi (RESEARCH §D.9) |

**Nima o'ylab topiladi (analog yo'q):** `aiobotocore` sessiya/klient hayot sikli,
`put_object` / `head_object` / `list_objects_v2` / `delete_objects` chaqiruvlari,
`ETag` taqqoslash. Bularning **hammasi** `04-RESEARCH.md` §D.9–D.11 da
spetsifikatsiyalangan.

> 🔴 **TARTIB MUZOKARA QILINMAYDI** (RESEARCH §B.4): avval S3 `PUT`, **keyin** baza
> qatori. «Baza qatori omborda obyekt BORLIGINI TASDIQLAYDI» — teskari tartib 6-fazaga
> **mavjud bo'lmagan dalilga havola** berardi.
>
> 🔴 **`s3.json` NING RASMIY MISOLI XAVFLI** (RESEARCH §D.9): `{"name": "anonymous",
> "actions": ["Read"]}` butun arxivni autentifikatsiyasiz o'qishga ochadi.
> `anonymous` yozuvi **BO'LMASLIGI SHART**. Repoda `ops/seaweedfs/s3.json.example`
> turadi (`ops/wireguard/wg0.conf.example` naqshi) va uning `anonymous` siz ekanini
> **grep-darvoza** tekshiradi — uslub namunasi
> `tests/integration/test_rate_limit_proxy.py:486-496`:
>
> ```python
>     """`.env.example` ham `*` tarqatmaydi — u har bir dev'ning `.env` iga ko'chadi."""
>         assert value != "*", "`.env.example` `*` tarqatmasligi shart"
> ```

---

### 3.8 `services/core-api/app/services/alerts.py` va `app/jobs/alerting.py`

**Analog:** yo'q (§4.5). Ko'chiriladigan uch jihat:

1. **Yupqa HTTP qobig'i + timeout** — `go2rtc.py:190-217`
2. **Sirsiz xato** — `go2rtc.py:133-160` (bot tokeni URL'da: `https://api.telegram.org/bot<TOKEN>/sendMessage`
   — ya'ni `httpx` istisno matni tokenni tashiydi; `_failure()` majburiy)
3. **Xato yutiladi, asosiy oqim to'xtamaydi** — `discovery.py:538-556`

**Alert holati XOTIRADA emas, `alert_events` jadvalida** (RESEARCH «Don't Hand-Roll»):
naqsh — `nvr_discovery_runs` dagi **qisman UNIQUE** (`0012_nvr_domain.py:409-415`):
ochiq alert uchun `UNIQUE (market_id, alert_kind, subject_id) WHERE resolved_at IS NULL`.

> 🔴 **D-19 — ALERTGA KADR RASMI HECH QACHON BIRIKTIRILMAYDI.** Bu qaror
> `alerts.py` docstringida **taqiq sababi bilan** yoziladi; uslub namunasi —
> `sbozor_core/security.py:6-11` va `go2rtc.py:193-197` («Metodning yo'qligi —
> kelishuv emas, STRUKTURA»). Ya'ni `sendPhoto` funksiyasi **umuman yozilmaydi**.
>
> 🔴 **D-22 — ba'zi alertlar HECH QACHON bo'g'ilmaydi** (backup xatosi, uzluksiz
> kamera offline). Bostirish ro'yxati **allowlist** emas, **denylist** bo'ladi va
> uning shakli `frontend/src/lib/nvr-errors.ts:139` (`AUTH_LOCKING_CODES`) bilan bir
> xil — metadan hosila, qo'lda takrorlanmaydi.

---

### 3.9 `services/core-api/app/api/v1/schedules.py`

**Analog:** `services/core-api/app/api/v1/tariffs.py` (davrli domen: davr qo'shish =
mavjud davrni **bo'lish**) + `stalls.py` (router skeleti).

**Fayl tepasidagi alias bloki** (`stalls.py:126-145` shakli):

```python
router = APIRouter(tags=["schedules"])

ScheduleManagerDep = Annotated[Principal, Depends(require_permission(Permission.CAMERA_MANAGE))]
ScheduleViewerDep = Annotated[Principal, Depends(require_permission(Permission.CAMERA_VIEW))]
```

**Huquq talabi MARSHRUT DEKORATORIDA** (`03-PATTERNS.md` §S-4, `stalls.py:28-42`):

```
⚠ HUQUQ TALABI MARSHRUT DEKORATORIDA (`dependencies=[...]`), imzo
parametri sifatida EMAS. FastAPI dekorator darajasidagi bog'liqliklarni
imzo parametrlaridan OLDIN hal qiladi ..., ya'ni 403 olgan so'rov
`audit_read` gacha YETIB BORMAYDI va jurnalda "kim nimani ko'rdi"
degan YOLG'ON DALIL qolmaydi.
```

**`_market_id` / `_not_found` yordamchilari** — `stalls.py:173-190` dan **verbatim**.

**MARSHRUT TARTIBI** (`stalls.py:3-11`): statik segmentli yo'l (`/today`, `/coverage`)
`{id}` shablonidan **OLDIN**.

> ⚠ **`audit_read` bu yerda KERAK EMAS** — jadval shaxsiy ma'lumot emas.
> Nazorat holati mavjud: `stalls.py:348-369` (`GET /map`) da `audit_read` **ataylab
> yo'q** va sabab kodda yozilgan. Jadval **o'zgarishi** esa DB-trigger orqali auditda
> (§S-1).
>
> ⚠ **RBAC — Wave 0 qarori.** 4-faza yangi `Permission` **qo'shmaydi**: jadval
> kameralarning bevosita davomi, ya'ni `CAMERA_MANAGE` / `CAMERA_VIEW` qayta
> ishlatiladi. Agar planer boshqacha qaror qilsa, `rbac.py:20-27` majburiyati bo'yicha
> **frontend ko'zgusi ham qo'lda** sinxronlanadi va `tests/unit/test_rbac_matrix.py`
> darvozasi ishlaydi.

---

### 3.10 `services/core-api/app/worker.py` (MOD)

**Analog:** o'zi. Uchta o'zgarish:

1. **Planer obyekti** (`scheduler`) — §4.4, analog yo'q; `broker` bilan bir xil
   «modul darajasida, `Settings` siz» qoidasiga bo'ysunadi.
2. **To'rt yangi yupqa qobiq**: `capture_tick`, `capture_batch`, `retention_daily`,
   `alert_sweep` — hammasi `discover_nvr_task` (`worker.py:210-239`) shaklida.
3. **Navbat nomlari** — `DISCOVERY_QUEUE` (`worker.py:81-88`) izohidagi qoida:

```python
DISCOVERY_QUEUE: Final[str] = "sbozor:discovery"
"""Navbat ro'yxatining nomi.

`taskiq` ning standart nomi (`taskiq`) ATAYIN ishlatilmaydi: bitta Valkey
nusxasi rate-limit sanagichlari va sessiya keshini ham saqlaydi (`db 0`),
ya'ni kalitlar prefiksi kimga tegishli ekanini AYTISHI kerak. `rl:login:*`
bilan bir xil qoida.
"""
```

> ⚠ **CAPTURE UCHUN ALOHIDA NAVBAT KERAKMI?** `ListQueueBroker` `queue_name` ni
> **broker qurilishida** oladi, ya'ni ikkinchi navbat **ikkinchi broker** demakdir va
> u D-06 ning «ikki mexanizm bir vaqtda saqlanmaydi» bandiga tegmaydi (bir mexanizm,
> ikki navbat) — lekin **ikkinchi worker konteynerini** talab qilardi. Standart tanlov:
> **bitta navbat** (`sbozor:jobs` ga qayta nomlash yoki `sbozor:discovery` ni saqlab
> qolish) — kunlik 175 vazifa uchun ajratish keraksiz. Qaror va sabab
> `worker.py` izohida yozilsin.

---

### 3.11 `compose.yaml` (MOD) — `storage` + `scheduler`

**Analog:** `compose.yaml:165-232` (`worker`) va `:234-280` (`go2rtc`). §S-11 ga qarang.

**Fayl boshidagi profil ro'yxati YANGILANADI** (`compose.yaml:4-10`) — u hujjat:

```yaml
#   (yo'q)   -> db, cache, storage, core-api, worker, scheduler, go2rtc : `npm run up`
```

**`npm run up` yorlig'i ham yangilanadi** (`package.json:7`):

```json
    "up": "docker compose up -d db cache core-api worker go2rtc --wait",
```

**Healthcheck shakli** — `go2rtc` (`compose.yaml:270-279`) `nc -z` bilan:

```yaml
    healthcheck:
      # `/api/streams` EMAS: healthcheck aynan biz bloklayotgan yuzani
      # so'rab turardi ... `nc` port ochiqligini tekshiradi — bu
      # «jarayon tirikmi?» savoliga to'liq javob (`nvr-sim-rtsp` bilan
      # bir xil qaror).
      test: ["CMD", "nc", "-z", "127.0.0.1", "8554"]
```

> ⚠ **`scheduler` uchun `healthcheck` QIYIN va uni SOXTALASHTIRMANG.**
> `taskiq scheduler` HTTP yuzasi bermaydi va jarayon tirikligi «tik ketyaptimi?»
> savoliga javob **bermaydi** — `worker.py:136-144` da o'lchangan nosozlik aynan
> shunday edi («konteyner "Up" bo'lib turadi, `docker compose ps` sog'lom ko'rsatadi
> va birorta vazifa hech qachon bajarilmaydi»). Yagona ishonchli signal —
> **bazadagi ish natijasi** (RESEARCH Pitfall 14: heartbeat'ni konteyner
> `healthcheck` iga **ulamang**).

---

### 3.12 Frontend — `schedule-queries.ts` va sahifa

**Analog:** `frontend/src/lib/camera-queries.ts` (3-fazada `market-queries.ts:100-250`
dan qurilgan) — **to'liq shablon**. §S-14 ga qarang.

**Sahifa/ro'yxat/dialog uchligi** — `02-PATTERNS.md` §S-10/§S-11 hamon amal qiladi:

| Element | Manba |
|---------|-------|
| Sahifa (client, huquq tekshiruvi **so'rovdan oldin**) | `frontend/src/app/[locale]/(app)/cameras/page.tsx` |
| URL parametri o'qiydigan sahifa → **`Suspense` MAJBURIY** | `frontend/src/app/[locale]/(app)/audit/page.tsx` |
| Ro'yxat: `isPending` / `isError` / bo'sh / natija **to'rtligi** | `frontend/src/components/users/user-list.tsx` |
| Forma: `react-hook-form` + zod, `useWatch` (`watch()` **emas**) | `frontend/src/components/cameras/nvr-form.tsx` |
| Xato → i18n kaliti | `frontend/src/lib/market-errors.ts` / `nvr-errors.ts` |

> **Yangi element — SLOT GENERATORI.** «06:00–08:00 har 30 daqiqada» **oraliq sifatida
> saqlanmaydi** (RESEARCH §A.1): UI uni **kengaytiradi**, baza faqat tekis ro'yxatni
> ko'radi. Bu 2-fazadagi «usta holati — domen ma'lumotining o'zi» qarorining takrori.
> Eng yaqin qo'shni — `frontend/src/components/calendar/weekday-picker.tsx`.
>
> **Ikkinchi yangi element — QOPLANMAGAN KUN OGOHLANTIRISHI.** Ikki profil orasidagi
> bo'shliq **xato emas**, lekin u UI'da **ko'rinishi SHART** (aks holda jim ma'lumot
> yo'qotish). Shakl — `frontend/src/components/cameras/nvr-error-block.tsx`
> (sabab + tuzatish yo'li).

---

### 3.13 Testlar — `tests/tenancy/test_snapshot_domain_meta.py`

**Analog:** `tests/tenancy/test_nvr_domain_meta.py` — u `pg_catalog` dan o'qiydi va
**modelga tayanmaydi**.

Bu faza uchun kamida olti yangi invariant:

| Invariant | Nima uchun |
|-----------|-----------|
| `snapshots` da `UNIQUE (id, is_billable)` mavjud | D-16 — 5-faza FK'sining **yagona** ilgagi |
| `snapshots.is_billable` `attgenerated = 's'` (STORED) | Oddiy ustunga aylantirilsa kafolat jimgina yo'qoladi |
| `capture_runs` da audit trigger **YO'Q** | §S-1 — hajm va ikkinchi nusxa |
| `capture_runs.business_date` ifodasi `scheduled_at` ga tayanadi | `created_at` ga o'tkazish 00:00–00:05 oynasini buzardi |
| `snapshot_schedules` da `EXCLUDE` konstrayti mavjud | «Bir kunga bitta profil» — DB invarianti |
| `markets` da `timezone <> 'Asia/Tashkent'` bo'lgan qator **yo'q** | `business_date` literalga qadalgan (RESEARCH §A.3) |

Umumiy invariantlar (`market_id`, RLS ENABLE+FORCE, policy, indeks birinchi ustuni) —
`tests/tenancy/test_meta.py` **avtomatik** qamraydi, chunki u jadvallarni `pg_catalog`
dan oladi.

**Mavjud darvozalar bilan aloqasi:**

| Darvoza | Fayl | 4-fazada nima bo'ladi |
|---------|------|------------------------|
| `test_audited_tables_have_trigger` | `test_meta.py:794` | `AUDITED_TABLES` ga ikkita nom qo'shilgunicha **qizil turadi** — bu KUTILGAN (`schema_contract.py:140-148`) |
| `test_tenant_indexes_lead_with_market_id` | `test_meta.py:397-428` | `ix_capture_runs_overdue` `INDEX_EXCEPTIONS` ga sabab bilan qo'shiladi |
| `test_security_definer_functions_pin_search_path` | `test_meta.py:432` | `capture_due_markets()` avtomatik qamraladi |
| `test_financial_tables_have_guards` | `test_meta.py:841-883` | **HECH NIMA O'ZGARMAYDI** — `FINANCIAL_TABLES` ga jadval qo'shilmaydi (§0) |
| `test_market_delete_guard` | `tests/integration/` | `0015` kaskadni kengaytirmaguncha **qizil** — 3-fazadagi `0012`→`0013` juftligining aynan takrori |

---

## 4. No Analog Found — **analog yo'q**

> Bu bo'lim ataylab batafsil: soxta analog ko'rsatish **admitted gap dan yomonroq**,
> chunki ijrochi unga ergashadi.

### 4.1 `SELECT … FOR UPDATE SKIP LOCKED` + lease — **analog yo'q**

**O'lchov (2026-08-04, `grep -rn "SKIP LOCKED\|FOR UPDATE\|with_for_update" --include=*.py .`):**
**ikkita natija va ikkalasi ham IZOH** —

```
./services/core-api/app/jobs/__init__.py:11:Postgres `SKIP LOCKED`) ochiq savol deb belgilagan. Mexanizm o'zgarsa
./services/core-api/app/worker.py:12:deb belgilagan (`taskiq` vs Postgres `SELECT ... FOR UPDATE SKIP LOCKED`).
```

Ya'ni loyihada **birorta qulflovchi so'rov yo'q**. Bu fazaning markaziy orkestratsiya
primitivi va uning **precedenti yo'q**.

**Eng yaqin strukturaviy qo'shnilar:**

| Nima | Fayl | Nimasi o'xshash / nimasi boshqa |
|------|------|--------------------------------|
| Shartli holat o'tishi | `nvr_repo.py:534-565` (`start_run`) | ✅ «Ikkinchi chaqiruv `False` oladi» falsafasi; ✅ `RETURNING` bilan natijani o'lchash. ❌ **Qulf yo'q** — u bitta qatorga, `WHERE status = 'queued'` bilan ishlaydi |
| Poygani DB'ga topshirish | `nvr_repo.py:509-517` + qisman UNIQUE (`0012:409-415`) | ✅ «Tekshir-keyin-yoz» rad etilgan; ❌ konstrayt **rad etadi**, `SKIP LOCKED` esa **o'tkazib yuboradi** — butunlay boshqa semantika |
| Xom `text()` + tiplangan bind | `market_repo.py:111-165`, `nvr_repo.py:29-41` | ✅ To'liq ko'chiriladi (CTE + `UPDATE … FROM` ORM'da ifodalanmaydi) |

**Nima o'ylab topiladi:** `claim_due()` ning CTE shakli, `locked_until` lease
mexanikasi, `release_expired()`. Bularning **hammasi** `04-RESEARCH.md` §A.2 da
to'liq SQL bilan spetsifikatsiyalangan — ijrochi o'ylab topmaydi, tadqiqotdan oladi.

> ⚠ **IKKALASI HAM KERAK VA BIRI IKKINCHISINING O'RNINI BOSMAYDI** (RESEARCH §A.2):
> `SKIP LOCKED` — «bir vaqtda ikki worker tanlab olmasin» (faqat tranzaksiya
> davomida); lease — «worker o'rtada o'lsa ish qaytsin». Bitta mexanizmni
> «soddalashtirish» uchun tashlab yuborish ikkinchisining qoplagan muddatini ochiq
> qoldiradi.

---

### 4.2 Obyekt-ombor / S3 (`storage.py`) — **analog yo'q**

**O'lchov (2026-08-04, `grep -rni "aiobotocore|boto3|botocore|minio|seaweed|s3_"` —
`.planning/` dan tashqari barcha `.py`/`.toml`/`.yaml`):** **NOL natija.**

Loyihada obyekt-ombor **umuman yo'q**: fayl yuklash yagona yo'li — Excel import
(`app/services/xlsx_reader.py`), u ham xotirada ishlaydi va hech qayerga saqlanmaydi.

**Eng yaqin strukturaviy qo'shni:** `redis.asyncio.Redis` — tashqi tarmoq klienti,
`lifespan`/`WORKER_STARTUP` da ochilib holatga qo'yiladi (`worker.py:194-199`).
Undan ko'chiriladigan narsa — **egalik va yopilish**, so'rov mexanikasi emas.

**Nima o'ylab topiladi:** `aiobotocore` sessiya/klient hayot sikli, `put_object`,
`head_object`, `list_objects_v2` sahifalash, `delete_objects` to'plami, `ETag`.

> 🔴 **`aioboto3` O'RNATIB BO'LMAYDI** (D-17, RESEARCH §D.9.2 — empirik tasdiqlangan,
> `arq` epizodining ikkinchi nusxasi). CLAUDE.md **2026-08-04 da tuzatilgan**.
> `services/core-api/pyproject.toml` ga **`aiobotocore==3.9.0`** yoziladi va
> `tests/unit/test_runtime_deps.py` uni prod bog'liqligi sifatida qulflaydi
> (3-fazadagi W0-1 `httpx` epizodining oldini olish).

---

### 4.3 Tasvir bilan ishlash (`Pillow`) — **analog yo'q**

**O'lchov (2026-08-04, `grep -rni "from PIL|import PIL|pillow"`):** **NOL natija.**
`Pillow` `pyproject.toml` da ham **yo'q** — u yangi bog'liqlik.

Loyihada tasvir bilan ishlash umuman yo'q. Eng yaqin **fayl-baytlari bilan ishlash**
qo'shnisi — `app/services/xlsx_reader.py` (yuklangan faylni xotirada tekshirish,
`import_max_upload_bytes` / `import_max_uncompressed_bytes` chegaralari,
`settings.py:46-79`). Undan ko'chiriladigan narsa — **chegaralar `Settings` da,
kodda emas** va **arzon tekshiruv qimmatidan oldin**.

**Nima o'ylab topiladi:** `Image.open(BytesIO(...))`, `im.draft("L", (320, 180))`,
`im.load()`, `ImageStat.Stat(...).mean/.stddev`, HSV to'yinganligi, `MAX_IMAGE_PIXELS`,
`LOAD_TRUNCATED_IMAGES`. Bularning hammasi `04-RESEARCH.md` §C.7 da **mahalliy
tekshirilgan** holda berilgan.

**`tests/fixtures/frames.py` ham analogsiz.** Eng yaqin qo'shni —
`tests/fixtures/karmana_seed.py` (determinizm sababi izohda yozilgan, generator
skript sifatida ham chaqiriladi: `npm run karmana:sample`).

---

### 4.4 `taskiq` **planeri** — **analog yo'q** (broker bor, planer yo'q)

**O'lchov:** `grep -rn "scheduler\|Scheduler" services/` — `worker.py:12` dagi **izoh**
dan boshqa hech nima. `compose.yaml` da planer konteyneri yo'q; `taskiq` paketi esa
`taskiq scheduler` CLI'sini **allaqachon beradi** (RESEARCH: yangi paket kerak emas).

**Eng yaqin strukturaviy qo'shni:** `worker.py:129-207` — broker qurilishi + startup
ilgaklari. Undan ko'chiriladigan narsa: **modul darajasida qurish**, `Settings` ga
bog'lanmaslik, `compose.yaml` da `target: runtime` bilan alohida `command`.

**Nima o'ylab topiladi:** `TaskiqScheduler(broker=..., sources=[LabelScheduleSource(broker)])`,
`@broker.task(schedule=[{"cron": "* * * * *"}])` yorlig'i, planer va worker'ning
bitta `broker` obyektini baham ko'rishi.

> 🔴 **PLANERGA HOLAT ISHONILMAYDI** (D-02, RESEARCH Pitfall 1 — manba o'qilgan):
> `SchedulerLoop.cron_tasks_last_run` — oddiy `dict`, jarayon xotirasida.
> `RedisScheduleSource` esa **yaroqsiz**: loyihaning Valkey'i
> `--save "" --appendonly no` bilan ishlaydi (`compose.yaml:44`), ya'ni kesh qayta
> ko'tarilganda hamma bozorning jadvali jimgina yo'q bo'lardi.
> Planerning **yagona** vazifasi — `capture.tick` ni navbatga qo'yish.

---

### 4.5 Telegram jo'natuvchisi (`alerts.py`) — **analog yo'q**

**O'lchov (2026-08-04, `grep -rni "telegram|aiogram"` — `.py`/`.toml`/`.yaml`):**
faqat **izohlar va rejalar**. `bot-service` **hali qurilmagan** — `services/` ostida
`core-api` va `nvr-sim` bor, uchinchisi yo'q. `aiogram` hech qayerda o'rnatilmagan.

Eng aniq dalil — `packages/sbozor-core/sbozor_core/enums.py:32`: `vendor` roli
«Telegram-bot identifikatori bo'lib, 7-fazadagi …» deb ta'riflangan.

**Eng yaqin strukturaviy qo'shni:** `app/services/go2rtc.py` — chiquvchi HTTP klienti,
yupqa qobiq, sirsiz xato, timeout. Undan **butun shakl** ko'chiriladi, faqat protokol
boshqa.

**Nima o'ylab topiladi:** `sendMessage` chaqiruvi, `chat_id` sozlamasi, xabar
guruhlash/debounce mantig'i, `parse_mode`.

> ⚠ **`aiogram` QO'SHILMAYDI** (RESEARCH Standard Stack): `httpx` bilan bitta
> `sendMessage` yetadi; `aiogram` ni tortish 7-fazani oldinga surardi.
> To'liq outbox ham **bu yerda qurilmaydi** (RESEARCH «Don't Hand-Roll»: BOT-04).
>
> ⚠ **TOKEN YO'Q — FAZA BLOKLANMAYDI.** Bo'sh `TELEGRAM_BOT_TOKEN` = «alertlar
> o'chiq + `log.warning`». Testlar `respx` bilan HTTP kontraktini o'lchaydi
> (`tests/integration/test_nvr_errors.py` da `respx` allaqachon ishlatiladi).

---

## 5. Wave 0 — birinchi migratsiyadan OLDIN bajariladigan ishlar

> Ro'yxat `04-RESEARCH.md` ning «Wave 0 Gaps» bandidan va shu hujjatning
> o'lchovlaridan quriladi. Ular keyin topilsa qimmatroq bo'ladi.

| # | Ish | Fayl | Sabab / manba |
|---|-----|------|---------------|
| **W0-1** | ⚠ **`GENERATED STORED` ustun kompozit FK NISHONI bo'la oladimi — O'LCHASH** | yangi `tests/fixtures/billable_probe.py` (shablon: `tests/fixtures/financial.py:59-145`) | **D-23 / OQ-4.** `UNIQUE` tomoni allaqachon isbotlangan (`helpers.py:356-362` + `financial.py`), FK-nishon tomoni **emas**. Yiqilsa `0014` boshqa shaklda yoziladi (trigger varianti) — migratsiyadan keyin aniqlash qayta migratsiya demakdir |
| **W0-2** | `aiobotocore==3.9.0` va `Pillow==12.3.0` ni `[project] dependencies` ga qo'shish | `services/core-api/pyproject.toml` | 3-fazadagi W0-1 ning takrori: `dev` guruhida qolsa **hamma test yashil, deploy'da `ModuleNotFoundError`**. `tests/unit/test_runtime_deps.py` ni ham kengaytiring |
| **W0-3** | `taskiq scheduler` ni `compose.yaml` ga qo'shish + `npm run up` yorlig'ini yangilash | `compose.yaml`, `package.json:7` | `worker` profilsiz bo'lgani bilan bir xil sabab (`compose.yaml:168-172`): planer profil ortida qolsa slotlar **hech qachon** materializatsiya bo'lmasdi va hech qanday xato chiqmasdi |
| **W0-4** | `storage` (SeaweedFS) xizmati + `ops/seaweedfs/s3.json.example` | `compose.yaml`, `ops/seaweedfs/` | `anonymous` yozuvi **bo'lmasligi** grep-darvoza bilan qulflanadi (`test_rate_limit_proxy.py:486-496` uslubi) |
| **W0-5** | `AUDITED_TABLES` ga `snapshot_schedules`, `snapshot_schedule_slots` | `schema_contract.py:93-167` | `schema_contract.py:140-148`: reyestr **migratsiyadan oldin** yoziladi, `test_audited_tables_have_trigger` esa vaqtincha qizil turadi — bu KUTILGAN |
| **W0-6** | `market_delete_draft()` kaskadini beshta yangi jadval bilan kengaytirish + `0015` migratsiyasi | `migrations/entities/functions.py:1029-1067` | 3-fazadagi `0012`→`0013` juftligining aynan takrori: kengaytirilmasa `0014` dan keyin bozor o'chirish FK buzilishi bilan yiqiladi. Tartib: `snapshots` → `capture_runs` → `snapshot_schedule_slots` → `snapshot_schedules` |
| **W0-7** | `tests/tenancy/test_meta.py` ga `markets.timezone = 'Asia/Tashkent'` invarianti | `tests/tenancy/test_meta.py` | RESEARCH §A.3: `scheduled_at` `markets.timezone` dan, `business_date` esa **literal**dan hisoblanadi. Ikkinchi mintaqa qo'shilgan kuni test qizarsin, biznes-kun **jimgina siljimasin** |
| **W0-8** | `ix_capture_runs_overdue` uchun `INDEX_EXCEPTIONS` ga **sabab bilan** yozuv | `tests/tenancy/test_meta.py:44` | Watchdog barcha bozorlar ustidan yuradi; indeks `market_id` bilan boshlanmaydi. `TUNNEL_SUBNET_INDEX` bilan bir xil holat |
| **W0-9** | `tests/fixtures/frames.py` — sintetik JPEG generatori (`mean`/`stddev`/to'yinganlik bo'yicha) | yangi | Usiz sifat filtri darvoza emas, **konventsiya** bo'lib qoladi. Fixture nomlari fizik xususiyat bilan (`frame_mean_8_stddev_2`), detektor chegarasi bilan **emas** |
| **W0-10** | `nvr-sim` ga `frame_mode` + `/Streaming/channels/{ch}/picture`; `mediamtx.yml` ga sifat-yo'llari | `sim/state.py`, `sim/isapi.py`, `ops/mediamtx/mediamtx.yml` | Buzuq kadrni MediaMTX bera olmaydi (u yaroqli oqim beradi) — baytlarni sim boshqarishi shart |
| **W0-11** | `pytest` markerlari — **yangi marker KERAK EMAS** (`tenancy`, `sim`, `hardware`, `slow` yetadi) | `pyproject.toml` | `--strict-markers` tufayli e'lon qilinmagan marker yig'ilishda yiqiladi; RESEARCH yangi marker talab qilmaydi — bu bandni **tasdiqlash** kifoya |

---

## Metadata

**Analog qidiruv qamrovi:**
`services/core-api/app/**` · `services/nvr-sim/**` · `packages/sbozor-core/**` ·
`migrations/**` · `tests/**` · `frontend/src/**` · `frontend/scripts/**` ·
`compose.yaml` · `ops/**` · `package.json` · `pyproject.toml`

**Skanerlangan fayllar:** ~490 (git tracked); to'liq o'qilgan: 9; nishonli o'qilgan: 14;
grep bilan tekshirilgan: 8 ta o'lchov.

**Empirik o'lchovlar (2026-08-04 — bu hujjatning «analog yo'q» da'volari shulardan keladi):**

| Da'vo | Buyruq | Natija |
|-------|--------|--------|
| `SKIP LOCKED` / qulflovchi so'rov yo'q | `grep -rn "SKIP LOCKED\|FOR UPDATE\|with_for_update" --include=*.py .` | **2 natija, ikkalasi ham IZOH** (`jobs/__init__.py:11`, `worker.py:12`) |
| S3 / obyekt-ombor yo'q | `grep -rni "aiobotocore\|boto3\|botocore\|minio\|seaweed\|s3_" --include=*.py --include=*.toml --include=*.yaml` | **0 natija** (`.planning/` dan tashqari) |
| `Pillow` yo'q | `grep -rni "from PIL\|import PIL\|pillow" --include=*.py --include=*.toml` | **0 natija** |
| Telegram jo'natuvchisi yo'q | `grep -rni "telegram\|aiogram" --include=*.py --include=*.toml --include=*.yaml` | Faqat **izohlar va rejalar**; `services/bot-service/` **mavjud emas** |
| `taskiq` planeri yo'q | `grep -n "scheduler" services/core-api/app/worker.py` | Faqat `:12` dagi izoh |
| `GENERATED STORED` + `UNIQUE` **ishlaydi** | `migrations/helpers.py:356-362` + `tests/fixtures/financial.py:127-138` o'qildi | **Tasdiqlandi** — haqiqiy `postgres:18.4` jadvalida bajariladi |
| `GENERATED STORED` **kompozit FK nishoni** | — | **O'LCHANMAGAN** → W0-1 |
| `business_date` generated ustuni mavjud naqsh | `models/market.py:519-523`, `models/ops.py:106-110`, `0008_temporal.py:204` | **Uch joyda mavjud** — 4-faza to'rtinchisini `scheduled_at` bilan qo'shadi |
| Fon-vazifa + tenant konteksti naqshi mavjud | `app/jobs/discovery.py:170-205` o'qildi | **Tasdiqlandi** — `_system_transaction()` |
| `btree_gist` o'rnatilgan | `tests/tenancy/test_meta.py:234` | **Tasdiqlandi** (`test_btree_gist_extension_is_installed`) |

**Pattern extraction date:** 2026-08-04
