# Phase 5: Kamera zonalari, CV va nazoratchi tasdig'i — Pattern Map

**Mapped:** 2026-08-08
**Files analyzed:** 61 (yangi yoki o'zgaradigan)
**Analogs found:** 42 / 61 (19 tasi uchun **analog yo'q** — §4 ga qarang)

> **Bu hujjatning maqsadi:** ijrochi naqsh o'ylab topmasin — u aniq `fayl:qator`
> dan nusxa olsin. Kod parchalari **verbatim** (2026-08-08 holatiga).
>
> **4-FAZADAN FARQI — ANALOG IKKIGA BO'LINADI VA CHEGARA O'TKIR.**
> Fazaning **vodoprovodi** (tenant jadvali, RLS, migratsiya, fon-vazifa, ombor,
> navbat, frontend kalitlari, darvozalar) uchun analog **hamma joyda bor va
> yetuk**. Fazaning **yadrosi** (idrok: ONNX, `supervision`, poligon
> geometriyasi, statistika, ko'r audit namunasi) uchun analog **umuman yo'q**
> va u soxta analog bilan to'ldirilmaydi.
>
> **ETTI SHAKLNING ANALOGI YO'Q:** ONNX / ML runtime (§4.1), `supervision` va
> poligon geometriyasi (§4.2), xom tenzor arifmetikasi (§4.3), ikkinchi Python
> servisi va uning `pyproject.toml`/`Dockerfile` i (§4.4), statistik hisobot —
> chalkashlik + Wilson (§4.5), qayta chiqariladigan tasodifiy namuna (§4.6),
> «oltin to'plam» harness'i (§4.7). Yana uchtasi qisman: ko'r serializer
> (§4.8), «o'zgarmas AI + alohida inson qatori» (§4.9), litsenziya-metadata
> darvozasi (§4.10).
>
> **Eng xavfli olti joy:** §S-1 (`zones` nomi BAND → `camera_zones`),
> §S-3 (o'zgarmaslik **SHARTSIZ**, `tariff_past_immutable()` SHAKLI EMAS),
> §S-4 (billing langari — tayyor, faqat ishlatiladi), §S-5 (kun yopilishi
> tenant kontekstini O'ZI o'rnatadi), §S-10 (darvoza sanoq emas, manbadan
> hosila), §S-13 (frontend sof mantiq testi `.test.tsx` bo'lishi SHART).
>
> ⚠ **UCH O'LCHOV REJANI DARHOL O'ZGARTIRADI** — §0.1.

---

## 0. Umumiy majburiy konventsiyalar

`04-PATTERNS.md` §0 jadvali **to'liq, o'zgarishsiz amal qiladi**. Quyida
faqat **shu fazaga xos** yoki **o'lchov bilan tuzatilgan** bandlar.

| Qoida | Manba | Buzilsa nima bo'ladi |
|-------|-------|----------------------|
| Har modul **fayl-darajasidagi docstring** bilan boshlanadi va "nega shunday" ni tushuntiradi | `app/services/storage.py:1-90`, `quality.py:1-56` | Kod review'dan o'tmaydi |
| Izohlar, docstring'lar, xato matnlari — **uz-Latn** | butun 1–4 faza kodi | Uslub ajralib qoladi |
| `from __future__ import annotations`; `__all__` aniq; `if TYPE_CHECKING:` faqat tip importlari | `storage.py:92-120` | ruff/mypy shuni kutadi |
| ruff `["E","F","I","UP","B","SIM","ASYNC","S"]`, `line-length=100`, py313; mypy `strict` | `pyproject.toml` | CI qizaradi |
| `timestamptz` + `ZoneInfo("Asia/Tashkent")`; naive `datetime` **TAQIQ** | `sbozor_core/timeutil.py` | `ValueError` |
| Biznes-kun **DB'da** (`GENERATED … STORED`); **ikki argumentli** `AT TIME ZONE` MAJBURIY | `migrations/helpers.py:324-332` | `generation expression is not immutable` |
| Bu fazada pul ustuni **YO'Q** — `FINANCIAL_TABLES` ga jadval qo'shilmaydi | `schema_contract.py:110-134` | Meta-test soxta `amount_soum` talab qiladi |
| PG `ENUM` tipi **ISHLATILMAYDI** — `text` + enum'dan HOSILA `CHECK` | `models/snapshot.py:31-38` | Ikkinchi konventsiya tug'iladi |
| Chiquvchi chaqiruvda `timeout` HAR DOIM; xato **sirsiz** (amal + istisno turi + status) | `storage.py:37-66` | Endpoint URL Sentry'ga chiqadi |
| Yangi `detail` kodi **uch joyda**: `app/schemas.py` · `lib/api-types.ts` · uchala `messages/*.json` | `frontend/scripts/error-codes.test.mjs:16-34` | `error-codes.test.mjs` qizaradi |
| Frontend: **Next.js 16 hujjatini `node_modules/next/dist/docs/` dan o'qing** yozishdan oldin | `frontend/AGENTS.md` | Eskirgan API ishlatiladi |

### 0.1 — UCH O'LCHOV, UCHALASI HAM REJANI DARHOL O'ZGARTIRADI

| # | O'lchov (2026-08-08) | Manba | Rejaga ta'siri |
|---|---|---|---|
| **M-1** | Bazada **faqat `btree_gist`** o'rnatilgan. **`pgcrypto` YO'Q** | `ops/db/init/00-extensions.sql` (oxirgi satr: `CREATE EXTENSION IF NOT EXISTS btree_gist;`); `.env.example:49` uni boshqa kontekstda «ataylab rad etilgan» deb belgilaydi | RESEARCH §C.8.1 ning `ORDER BY digest(id::text \|\| :seed, 'sha256')` so'rovi **bugun ishlamaydi** — `digest()` `pgcrypto` funksiyasi. Uch yo'l va tanlov — §3.1 |
| **M-2** | `vitest` `include: ["src/**/*.test.tsx"]` — **faqat `.tsx`**. `.ts` test fayli **JIMGINA** yig'ilmaydi | `frontend/vitest.config.ts:34`; ogohlantirish `camera-page-state.test.tsx:16-20` («o'lchangan holat, 03-08») | `zone-geometry` testi **`.test.tsx`** bo'lishi SHART, ichida JSX bo'lmasa ham |
| **M-3** | `node --test` **TypeScript'ni import qila olmaydi**. `frontend/scripts/` dagi 9 testdan faqat `gen-cyrillic.test.mjs:6` manba modulini import qiladi (`.mjs` dan); qolgan 8 tasi fayllarni **MATN** sifatida o'qiydi | `frontend/package.json:14` | RESEARCH ning `frontend/scripts/zone-geometry.test.mjs` + `src/lib/zone-geometry.ts` juftligi **bajarilmaydi** — §S-13 da tanlov |

---

## 1. File Classification

### 1.1 Backend — sxema qatlami

| Yangi/o'zgaradigan fayl | Rol | Data flow | Eng yaqin analog | Moslik |
|---|---|---|---|---|
| `packages/sbozor-core/sbozor_core/models/occupancy.py` | model | CRUD + event-log | `models/snapshot.py` (**to'liq shablon**, 879 q., 5 klass) | **exact** |
| `.../models/__init__.py` (MOD) | model-barrel | — | o'zi | **exact** |
| `.../enums.py` (MOD — `OccupancyVerdict`, `ReviewQueueKind`, `ReviewPurpose`, `ResolutionSource`) | enum | — | o'zi (`SnapshotQuality:217-220`) | **exact** |
| `.../schema_contract.py` (MOD — `AUDITED_TABLES`) | registry | — | o'zi (`AUDITED_TABLES:130+`) | **exact** |
| `migrations/entities/__init__.py` (MOD — `OCCUPANCY_TENANT_TABLES` / `_AUDITED_` / `_DELETE_ORDER`) | registry | — | o'zi (`:191-280`) | **exact** |
| `migrations/versions/0018_occupancy_domain.py` | migration | DDL + RLS + audit | `0014_snapshot_domain.py` (842 q.) | **exact** |
| `migrations/versions/0019_market_delete_occupancy.py` | migration | funksiya almashtirish | `0015_market_delete_snapshots.py` | **exact** |
| `migrations/entities/triggers.py` (MOD — `occupancy_event_immutable()`, `zone_review_immutable()`) | db-trigger fn | — | `AUDIT_IMMUTABLE` (`triggers.py:131-146` — **SHARTSIZ**), **emas** `TARIFF_PAST_IMMUTABLE:233` | **exact** (§S-3) |
| `migrations/entities/functions.py` (MOD — kaskad + kun-yopish bozorlari) | db-function | request-response | o'zi (`CAPTURE_DUE_MARKETS:1424-1455`) | **exact** |

### 1.2 Backend — `cv-service` (loyihaning IKKINCHI Python servisi)

| Fayl | Rol | Data flow | Analog | Moslik |
|---|---|---|---|---|
| `services/cv-service/pyproject.toml` + `uv.lock` | config | — | `services/core-api/pyproject.toml:128-129` (`[tool.uv.sources] sbozor-core = {path=…, editable=true}`) | role-match (§4.4) |
| `services/cv-service/Dockerfile` | config/ops | — | `services/core-api/Dockerfile` (`dev`/`runtime`) | role-match (§4.4) |
| `services/cv-service/app/main.py` (minimal FastAPI) | bootstrap | request-response | `app/api/internal/self_check.py:133-180` | role-match |
| `services/cv-service/app/worker.py` | bootstrap | event-driven | `core-api/app/worker.py:260-300`, `:599-630` | **exact** |
| `services/cv-service/app/settings.py` | config | — | `core-api/app/settings.py` | **exact** |
| `services/cv-service/app/jobs/detect.py` | job | batch + event-driven | `core-api/app/jobs/capture.py` + `discovery.py:170-205` | **exact** (orkestratsiya) |
| `services/cv-service/app/services/storage.py` (FAQAT o'qish) | service | file-I/O | `core-api/app/services/storage.py:159-330` | **exact** |
| `.../app/detector/session.py` (ONNX) | service | transform | — | **analog yo'q** (§4.1) |
| `.../app/detector/postprocess.py` (xom tenzor → `sv.Detections`) | sof funksiya | transform | `app/services/quality.py` (SHAKL) | partial (§4.3) |
| `.../app/detector/zones.py` (`PolygonZone`, 0..1 ↔ piksel) | sof funksiya | transform | `app/services/object_key.py` / `rtsp.py` | partial (§4.2) |
| `.../app/detector/annotate.py` (dalil rasm) | service | transform | — | **analog yo'q** (§4.2) |

### 1.3 Backend — `core-api` qo'shimchalari

| Fayl | Rol | Data flow | Analog | Moslik |
|---|---|---|---|---|
| `app/api/v1/camera_zones.py` | router | CRUD + versiyalash | `app/api/v1/zones.py` (**nomdosh, boshqa domen**) + `tariffs.py` | **exact** |
| `app/api/v1/reviews.py` | router | request-response | `app/api/v1/snapshots.py` + `stalls.py:126-190` | role-match (§4.8) |
| `app/repositories/camera_zone_repo.py` | repository | CRUD | `stall_repo.py::ZoneRepository` + `tariff_repo.py` | **exact** |
| `app/repositories/occupancy_repo.py` | repository | CRUD | `snapshot_repo.py` | **exact** |
| `app/repositories/review_repo.py` | repository | CRUD + qulflash | `capture_repo.py` (`claim_due` — `SKIP LOCKED` 4-fazada TUG'ILGAN) | **exact** |
| `app/jobs/day_close.py` (AI-06 + materializatsiya) | job | batch | `app/jobs/retention.py` + `capture.py` | **exact** |
| `app/jobs/audit_draw.py` | job | batch | `app/jobs/alerting.py` (`alert_sweep`) | role-match (§4.6) |
| `app/services/zone_geometry.py` | sof funksiya | transform | `app/services/live_source.py` | role-match (§4.2) |
| `app/services/accuracy_report.py` | sof funksiya | transform | `sbozor_core/money.py` | partial (§4.5) |
| `packages/sbozor-core/sbozor_core/occupancy.py` (`aggregate_stall_slot()`) | utility | transform | `sbozor_core/periods.py` | **exact** |
| `app/services/occupancy_errors.py` | registry | — | `app/services/capture_errors.py` | **exact** |
| `app/api/internal/self_check.py` (MOD — `EXPECTED_COMPONENTS`) | registry | — | o'zi (`:108-126`) | **exact** |
| `app/worker.py` (MOD — `day_close`, `audit_draw` cron) | bootstrap | event-driven | o'zi (`:682-745`) | **exact** |
| `app/schemas.py` · `app/settings.py` · `app/security/rbac.py` (MOD) | schema/config/matrix | — | o'zi | **exact** |

### 1.4 Infra / ops

| Fayl | Rol | Analog | Moslik |
|---|---|---|---|
| `compose.yaml` (MOD — `cv-service`) | config/ops | `compose.yaml:245-347` (`worker`), `:348-468` (`scheduler`) | role-match — **UCHINCHI SERVIS** (§S-11) |
| `ops/models/README.md` + ONNX artefakt yo'li | doc/ops | `ops/seaweedfs/README.md`, `ops/docs/nvr-onboarding.md` | **exact** |
| `.gitattributes` | config | o'zi — `:31` da **`*.onnx binary` ALLAQACHON bor** | **exact** |
| `.env.example` (MOD) · `package.json` (MOD — D-26) | config | o'zi (`package.json:6-33`) | **exact** |
| `scripts/check-validation-signoff.mjs` (MOD — D-27) | script | o'zi (`:54-61`, `:317`) | **exact** |

### 1.5 Frontend

| Fayl | Rol | Analog | Moslik |
|---|---|---|---|
| `frontend/src/lib/zone-geometry.ts` | sof funksiya | `src/components/cameras/camera-page-state.ts` (**nega ajratilgani o'lchov bilan yozilgan**) | **exact** (SHAKL) / §4.2 (mazmun) |
| `src/components/camera-zones/zone-editor.tsx` | component | `components/stalls/stall-map.tsx:22-37` + `snapshots/capture-grid.tsx:12-58` | role-match |
| `src/components/camera-zones/zone-list.tsx` | component (list) | `components/zones/zone-list.tsx` | **exact** |
| `src/components/review/review-card.tsx` | component | `snapshots/snapshot-dialog.tsx` + `cameras/nvr-error-block.tsx` | role-match |
| `src/lib/zone-queries.ts` · `src/lib/review-queries.ts` | data-access | `src/lib/snapshot-queries.ts:1-95` | **exact** |
| `app/[locale]/(app)/camera-zones/page.tsx` · `.../review/page.tsx` | page (client) | `.../cameras/page.tsx`, `.../snapshots/page.tsx` | **exact** |
| `src/lib/occupancy-errors.ts` | registry | `src/lib/capture-errors.ts` / `nvr-errors.ts` | **exact** |
| `src/lib/api-types.ts` · `src/lib/rbac.ts` · `messages/*` (MOD) | schema/i18n | o'zi | **exact** |

### 1.6 Testlar — darvozalar

| Fayl | Rol | Analog | Moslik |
|---|---|---|---|
| `tests/unit/test_license_fence.py` (D-03) | test (unit) | `tests/unit/test_runtime_deps.py` (**to'liq shablon**) | **exact** (§3.8) / §4.10 |
| `tests/unit/test_rfdetr_postprocess.py` | test (unit) | `tests/unit/test_quality_filter.py` (shakl) | partial (§4.3) |
| `tests/unit/test_aggregate_stall_slot.py` | test (unit) | `tests/unit/test_periods.py` | **exact** |
| `tests/unit/test_zone_geometry.py` | test (unit) | `tests/unit/test_rtsp_url.py` | **exact** |
| `tests/unit/test_accuracy_report.py` | test (unit) | `tests/unit/test_money.py` | role-match (§4.5) |
| `tests/unit/test_runtime_deps.py` (MOD) · `test_sentry_processes.py` (MOD) | test (unit) | o'zi | **exact** (§S-10) |
| `tests/fixtures/detections.py` | fixture | `tests/fixtures/frames.py:1-80` (**nomlash majburiyati**) | partial (§4.2) |
| `tests/fixtures/occupancy_domain.py` | fixture | `tests/fixtures/snapshot_domain.py` | **exact** |
| `tests/fixtures/golden_set/` + `scripts/eval-golden-set.py` | fixture + CLI | `tests/fixtures/karmana_seed.py` (CLI naqshi) | partial (§4.7) |
| `tests/tenancy/test_occupancy_domain_meta.py` | test (meta) | `tests/tenancy/test_snapshot_domain_meta.py` (9 invariant) | **exact** |
| `tests/integration/test_camera_zones_api.py` | integration | `test_tariff_history.py` | **exact** |
| `tests/integration/test_occupancy_immutable.py` | integration | `test_audit_immutable.py` | **exact** |
| `tests/integration/test_occupancy_billing_fence.py` | integration | `tests/tenancy/test_billable_anchor_probe.py` + `test_snapshot_quality.py` | **exact** |
| `tests/integration/test_blind_audit.py` | integration | `test_snapshot_api.py` | partial (§4.6, §4.8) |
| `tests/integration/test_uncertain_queue.py` | integration | `tests/tenancy/test_route_coverage.py` (OpenAPI skani) | role-match |
| `tests/integration/test_day_close.py` | integration | `test_capture_tick.py` | **exact** |
| `tests/integration/test_onnx_session.py` | integration | `test_live_view_e2e.py` (mock'siz o'lchov) | partial (§4.1) |
| `tests/integration/test_phase5_criteria.py` | faza darvozasi | `test_phase4_criteria.py:1377-1420` | **exact** (§S-14) |

### 1.7 Frontend testlari

| Fayl | Analog | Moslik |
|---|---|---|
| `src/lib/zone-geometry.test.tsx` (⚠ `.tsx`, M-2) | `components/cameras/camera-page-state.test.tsx:1-20` | **exact** |
| `src/components/camera-zones/zone-editor.test.tsx` | `components/snapshots/capture-grid.test.tsx` | **exact** |
| `src/lib/zone-queries.test.tsx` | `src/lib/snapshot-queries.test.tsx` | **exact** |
| `scripts/occupancy-copy.test.mjs` | `scripts/snapshot-copy.test.mjs` / `nvr-copy.test.mjs` | **exact** |
| `scripts/error-codes.test.mjs` (MOD) · `scripts/gen-cyrillic.test.mjs` (MOD) | o'zi | **exact** (§S-15) |

---

## 2. Shared Patterns — HAMMA fayl uchun

### S-1. Yangi tenant jadvali — BESH JOY, **va oltinchisi: NOM TO'QNASHUVI**

`03-PATTERNS.md` §S-1 / `04-PATTERNS.md` §S-1 **o'zgarishsiz amal qiladi**.
`0014_snapshot_domain` — eng yangi shablon.

1. `migrations/entities/__init__.py::OCCUPANCY_TENANT_TABLES` + `ALL_TENANT_TABLES`
2. Migratsiya (`op.create_table` + `enable_tenant_rls` + `tenant_policy` + `owner_bootstrap_policy`)
3. `schema_contract.py::AUDITED_TABLES` (**faqat trigger ulanadigan jadval**)
4. `models/__init__.py` barreli
5. `tests/fixtures/occupancy_domain.py` seed'i
6. **`OCCUPANCY_DELETE_ORDER`** + `market_delete_draft()` kaskadi (§S-2)

> 🔴 **`zones` NOMI BAND (D-06).** `packages/sbozor-core/sbozor_core/models/market.py:295-305`:
>
> ```python
> class Zone(Base, TenantMixin, TimestampMixin):
>     """Bozor zonasi — YASSI ro'yxat, ierarxiya YO'Q (D-03).
>
>     Zona kaliti rasta RAQAMIGA kirmaydi (D-01: raqam bozor bo'yicha yagona),
>     ya'ni rastani boshqa zonaga ko'chirish uning raqamini o'zgartirmaydi va
>     tarixni buzmaydi.
>     """
>
>     __tablename__ = "zones"
> ```
>
> Unga `stalls.zone_id` **`NOT NULL`** bilan tayanadi; frontendda
> `components/zones/zone-list.tsx` va `app/api/v1/zones.py` **shu ma'noda**
> ishlatiladi.
>
> **Oqibatlari:** jadval — **`camera_zones`**; router — `app/api/v1/camera_zones.py`
> (`zones.py` ga tegilmaydi); frontend papkasi — `components/camera-zones/`;
> **UI matnlari uchala tilda kvalifikator bilan** («bozor zonasi» /
> «kamera zonasi»). Kvalifikatorsiz «zona» so'zi rejada ham, kodda ham,
> tarjimada ham ishlatilmaydi.

**Reyestr shakli — verbatim:** `migrations/entities/__init__.py:191-207`

```python
SNAPSHOT_TENANT_TABLES: tuple[str, ...] = (
    "snapshot_schedules",
    "snapshot_schedule_slots",
    "capture_runs",
    "snapshots",
    "alert_events",
)
"""`0014_snapshot_domain` yaratadigan tenant jadvallari (CAM-04/05/06/07).

TARTIB — FK bo'yicha OTA-ONADAN bolalarga, `NVR_TENANT_TABLES` bilan aynan
bir xil qoida ...
✅ RO'YXAT `ALL_TENANT_TABLES` GA QO'SHILDI (`04-03` / T2, `0014` bilan bir
commitda).
"""
```

**5-faza jufti (RESEARCH §A.2/§B.5/§C.8/§D.12 sxemalaridan):**

```python
OCCUPANCY_TENANT_TABLES: tuple[str, ...] = (
    "camera_zones",           # -> cameras, stalls
    "occupancy_events",       # -> snapshots (id, is_billable), camera_zones
    "audit_rounds",           # namuna turi — doira MUZLATILADI
    "review_assignments",     # -> occupancy_events; UNIQUE navbatni mutlaq qiladi
    "zone_reviews",           # -> review_assignments
    "stall_slot_occupancy",   # -> stalls, occupancy_events (materializatsiya)
)
OCCUPANCY_AUDITED_TABLES: tuple[str, ...] = ("camera_zones", "zone_reviews")
```

> 🔴 **AUDIT ASSIMETRIYASI.** `occupancy_events` audit triggeridan
> **CHIQARILADI**; sabab `migrations/entities/__init__.py:236-252` shaklida
> yoziladi:
>
> ```python
> """...
> ⚠ UCHTASI ATAYIN CHIQARILGAN ...
>   * `capture_runs`, `snapshots`, `alert_events` — HODISA JURNALLARI: ular
>     faqat QO'SHILADI (odam tomonidan tahrirlanmaydi), ya'ni audit ularning
>     ustiga o'sha ma'lumotning IKKINCHI NUSXASINI yozardi;
>   * HAJM: 175 qator/kun/bozor × har holat o'tishi ...
> """
> ```
>
> Hajm argumenti bu yerda **kuchliroq**: 175 kadr × ~30 zona ≈ **5 000
> qator/kun/bozor**, va **o'zgarmas jadval uchun audit ma'nosiz** (§S-3 uni
> DB darajasida imkonsiz qiladi). `zone_reviews` esa **auditda BO'LADI** —
> insonning moliyaviy oqibatli qarori, `AUDITED_TABLES` dagi `tariffs` /
> `stall_assignments` bilan bir oilada (`schema_contract.py:130-160`).

**Composite FK va `UNIQUE(market_id, id)`** — `models/snapshot.py:657-671`:

```python
    __table_args__ = (
        ForeignKeyConstraint(["market_id"], ["markets.id"], name="fk_snapshots_market_id_markets"),
        ForeignKeyConstraint(
            ["market_id", "capture_run_id"],
            ["capture_runs.market_id", "capture_runs.id"],
            name="fk_snapshots_market_id_capture_run_id_capture_runs",
        ),
        # `camera_id` DENORMALIZATSIYA, lekin kompozit FK baribir qo'yiladi:
        # `capture_runs.nvr_id` bilan bir xil qoida — denormalizatsiya
        # tenant chegarasini bo'shatish uchun bahona emas (T-03-14 sinfi).
        ForeignKeyConstraint(
            ["market_id", "camera_id"],
            ["cameras.market_id", "cameras.id"],
            name="fk_snapshots_market_id_camera_id_cameras",
        ),
```

`camera_zones` **ikkita** kompozit FK oladi (`cameras` VA `stalls`) —
RESEARCH §A.2 ning ikkala satri ham tenant chegarasini sxemada yopadi.

---

### S-2. `market_delete_draft()` kaskadi — **ALOHIDA RO'YXAT, hosila emas**

**Verbatim:** `migrations/entities/__init__.py:258-280`

```python
SNAPSHOT_DELETE_ORDER: tuple[str, ...] = (
    "snapshots",
    "capture_runs",
    "snapshot_schedule_slots",
    "snapshot_schedules",
    "alert_events",
)
"""`market_delete_draft()` kaskadiga qo'shiladigan tartib (W0-6, `0015`).

⚠ IKKI FAKT, IKKALASI HAM MAJBURIY:

**(a) Tartib BOLALARDAN OTA-ONAGA** — ya'ni bu `SNAPSHOT_TENANT_TABLES`
ning oddiy teskarisi EMAS va uni `reversed(...)` bilan hosil qilib
bo'lmaydi: `alert_events` FK zanjirida umuman turmaydi ...

**(b) BUTUN BLOK MAVJUD NVR BLOKIDAN OLDIN TURISHI SHART.**
"""
```

> 🔴 **5-fazada qoida UCHINCHI marta qo'llanadi va blok SNAPSHOT BLOKIDAN
> OLDIN turadi:** `stall_slot_occupancy` → `zone_reviews` →
> `review_assignments` → `audit_rounds` → `occupancy_events` →
> `camera_zones` → *(mavjud snapshot bloki)* → *(NVR bloki)* → *(market
> bloki)*. Kengaytirilmasa `0018` dan keyin qoralama bozorni o'chirish FK
> buzilishi bilan yiqiladi — `0012`→`0013` va `0014`→`0015` juftligining
> **aynan uchinchi takrori**, ya'ni `0019` **rejalashtirilgan ish**.

---

### S-3. O'ZGARMASLIK — **SHARTSIZ**; `tariff_past_immutable()` SHAKLI NOTO'G'RI

| Shakl | Manba | Semantika | 5-fazada |
|---|---|---|---|
| **SHARTSIZ** — har qanday `UPDATE`/`DELETE` rad etiladi | `migrations/entities/triggers.py:131-146` (`AUDIT_IMMUTABLE`) | «Jadval append-only» | ✅ `occupancy_events`, `zone_reviews` |
| **SHARTLI** — faqat *o'tmishdagi* qator, qoralama bozor istisno | `triggers.py:233-283` (`TARIFF_PAST_IMMUTABLE`) | «O'tmishdagi narx qulflanadi» | ❌ **ISHLATILMAYDI** |

**Ko'chiriladigan shakl — verbatim:** `triggers.py:131-146`

```python
AUDIT_IMMUTABLE = PGFunction(
    schema="public",
    signature="audit_immutable()",
    definition="""
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public
AS $$
BEGIN
  RAISE EXCEPTION 'audit_log is append-only (attempted %)', TG_OP;
END $$
""",
)
"""`audit_log` ustidagi 3- va 4-qatlam qo'riqchisi.

Ikkala triggerda ham (`BEFORE UPDATE OR DELETE FOR EACH ROW` va
`BEFORE TRUNCATE FOR EACH STATEMENT`) ishlatiladi. `TG_OP` xabarga
qo'shiladi, chunki uch xil urinish (UPDATE / DELETE / TRUNCATE) uch xil
tahdid modelidan keladi va log'da ular ajralib turishi kerak.
"""
```

**Ulash — verbatim:** `migrations/helpers.py:269-304`

```python
def attach_immutability_trigger(table: str, function: str, name: str) -> None:
    """`BEFORE UPDATE OR DELETE ... FOR EACH ROW` qo'riqchi triggerini ulaydi.

    `attach_audit_trigger()` bilan bir xil shaklda yozilgan, LEKIN uchta
    ataylab qilingan farq bor va har biri boshqa sababga ega:

    * **`BEFORE`, `AFTER` emas** — qo'riqchi o'zgarish SODIR BO'LISHIDAN
      OLDIN to'xtatishi kerak. ...
    * **Trigger funksiyasi PARAMETR** — ... Sabab: xato xabari QAYSI qoida
      buzilganini aytishi kerak, `TG_TABLE_NAME` bo'yicha shoxlanadigan
      umumiy funksiya esa ikkala jadvalni bir-biriga bog'lab qo'yardi.
    * **Trigger nomi ham PARAMETR** ...

    TRIGGER TARTIBI (Postgres qoidasi ...): bir xil vaqtda ishlaydigan
    triggerlar ALIFBO tartibida chaqiriladi, `BEFORE` esa `AFTER` dan oldin
    yuradi. Ya'ni bu qo'riqchi rad etgan `UPDATE` audit qatori QOLDIRMAYDI.
    """
    op.execute(
        f"CREATE TRIGGER {_ident(name)} "
        f"BEFORE UPDATE OR DELETE ON {_ident(table)} "
        f"FOR EACH ROW EXECUTE FUNCTION {_ident(function)}()"
    )
```

**Chaqirish joyi:** `migrations/versions/0008_temporal.py:76-82, 266`

```python
        "category_period_past_immutable",
        "trg_category_period_past_immutable",
    ),
    ("tariffs", "tariff_past_immutable", "trg_tariff_past_immutable"),
...
        attach_immutability_trigger(table, function_name, trigger_name)
```

> 🔴 **IKKI ALOHIDA FUNKSIYA** (`helpers.py:279-283`): `occupancy_event_immutable()`
> va `zone_review_immutable()` — tanalari deyarli bir xil bo'lsa ham.
> 🔴 **`RETURN CASE WHEN TG_OP='DELETE' THEN OLD ELSE NEW END` KERAK EMAS** —
> u **shartli** qo'riqchida (`TARIFF_PAST_IMMUTABLE:255`) kerak; shartsizda
> `RAISE` dan keyin qaytish nuqtasi yo'q (`AUDIT_IMMUTABLE` ham yozmaydi).
> 🔴 **`TimestampMixin` QO'YILMAYDI** — `models/snapshot.py:650-653`:
> «`TimestampMixin` YO'Q: kadr o'zgarmaydi… `updated_at` "bu qatorni
> tahrirlash mumkin" degan yolg'on va'da berardi.»
> ⚠ `zone_reviews` da **ikkala** trigger bo'ladi (audit + o'zgarmaslik) va
> yuqoridagi tartib qoidasi aynan kerakli natijani beradi.

**Nazoratchi qarori — `INSERT`, `UPDATE` emas.** Yakuniy javob
**hisoblanadigan ko'rinish**: `COALESCE(review.human_verdict, event.verdict)`
(RESEARCH §B.5.2) — 2-fazadagi «qoldiq har doim hisoblanadigan ko'rinish»
qoidasining takrori. To'liq juftlik uchun **analog yo'q** — §4.9.

---

### S-4. Billing langari — 4-FAZA UNI QO'YGAN VA O'LCHAGAN; 5-FAZA FAQAT ISHLATADI

**Ilgak — verbatim:** `models/snapshot.py:681-699`

```python
        # ⚠⚠ D-16 NING YAGONA ILGAGI — BU KONSTRAYT BOSHQA FAZA UCHUN BOR.
        #
        #   5-fazada `occupancy_events` shunday quriladi:
        #
        #       snapshot_is_billable boolean NOT NULL DEFAULT true
        #       CHECK  (snapshot_is_billable)
        #       FOREIGN KEY (snapshot_id, snapshot_is_billable)
        #           REFERENCES snapshots (id, is_billable)
        #
        #   Ya'ni `quality_verdict <> 'ok'` bo'lgan kadrga bandlik dalilini
        #   bog'lash uchun kerak bo'lgan `(id, true)` juftligi JADVALDA
        #   UMUMAN MAVJUD BO'LMAYDI va FK rad etadi. «Yaroqsiz kadr
        #   billing'ga ta'sir qilmaydi» da'vosi kelishuv emas, DB xatosi.
        #
        #   ⚠ NOMI KONVENSIYADAN HOSILA EMAS ...: `billable_anchor` nomi
        #     5-faza va meta-test uchun QIDIRILADIGAN belgidir ...
        UniqueConstraint("id", "is_billable", name="uq_snapshots_billable_anchor"),
```

**O'lchov — verbatim:** `models/snapshot.py:639-648`

```python
    `is_billable` — `GENERATED ALWAYS AS (quality_verdict = 'ok') STORED`.
    Shakl W0-1 zondi bilan HAQIQIY `postgres:18.4` da O'LCHANGAN
    (2026-08-04, `tests/fixtures/billable_probe.py`): `GENERATED ... STORED`
    ustun ustidagi `UNIQUE` kompozit FK NISHONI bo'la OLADI
    (`BILLABLE_ANCHOR_SUPPORTED = true`). ... Zond kafolatning IKKALA
    yo'nalishini ham o'lchadi: `'dark'` qatorga havola `ForeignKeyViolation`
    beradi, VA mavjud `'ok'` qatorni `'dark'` ga `UPDATE` qilish ham rad
    etiladi — ya'ni kafolat faqat `INSERT` paytida emas, hukm o'zgarganda
    ham ishlaydi.
```

**Bola-jadvalning AYNAN DDL'i — verbatim:** `tests/fixtures/billable_probe.py:87-104`

```python
# Bola-jadval: 5-fazadagi `occupancy_events` ning minimal shakli.
#
# `CHECK (snapshot_is_billable)` — juftlikning IKKINCHI yarmi va usiz
# butun konstruksiya ma'nosiz bo'lardi: FK yolg'iz o'zi `(id, false)`
# juftligiga havolani ham QABUL QILARDI (u ham mavjud juftlik). CHECK
# `false` ni butunlay taqiqlaydi, ya'ni yagona mumkin bo'lgan havola —
# `is_billable = true` bo'lgan kadrga.
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

> 🔴 **UCH SATR AYNAN KO'CHIRILADI VA `CHECK` UNUTILMAYDI** — usiz butun
> kafolat yo'q.
> 🔴 **KAFOLAT TRANZITIV** (RESEARCH §D.12): `stall_slot_occupancy` →
> `occupancy_events` → `snapshots (id, is_billable)`. `stall_slot_occupancy`
> **yangi mexanizm o'ylab topmaydi** — `winning_occupancy_event_id` orqali
> zanjirni davom ettiradi va
> `CHECK ((verdict='occupied') = (winning_occupancy_event_id IS NOT NULL))`
> qo'yadi. Bu `models/snapshot.py:709-712` ning aynan shakli:
>
> ```python
>         CheckConstraint(
>             "(storage_tier = 'purged') = (object_deleted_at IS NOT NULL)",
>             name="purged_has_deletion_time",
>         ),
> ```
>
> 🔴 **KADR AVVAL FILTRLANADI** (RESEARCH §E.13): `quality_verdict <> 'ok'`
> kadr uchun `detect` **umuman ishga tushmaydi** — «oldindan filtrlash mumkin
> bo'lgan xatoni imkonsiz xatoga aylantirishdan yaxshiroq».

**Meta-test jufti:** `tests/tenancy/test_snapshot_domain_meta.py:172, 217`
(`test_snapshots_have_the_billable_anchor`,
`test_is_billable_is_a_stored_generated_column`). 5-faza jufti —
`test_occupancy_events_reference_the_billable_anchor` va
`test_occupancy_events_check_forbids_false`.

---

### S-5. Fon-vazifa tenant kontekstini O'ZI o'rnatadi; bozorlar `SECURITY DEFINER` dan

`04-PATTERNS.md` §S-3 to'liq amal qiladi. `app/jobs/discovery.py:170-205` —
`_system_transaction()`: `Principal` YO'Q, `actor_kind=ActorKind.SYSTEM`,
`HTTPException` YO'Q, **har chaqiruvda yangi tranzaksiya** (`SET LOCAL`).

**Bozorlar ro'yxati — verbatim:** `migrations/entities/functions.py:1424-1444`

```python
CAPTURE_DUE_MARKETS = PGFunction(
    schema="public",
    signature="capture_due_markets()",
    definition="""
RETURNS TABLE (market_id uuid, due_count integer)
LANGUAGE sql
SECURITY DEFINER
SET search_path = pg_catalog, public
STABLE
AS $$
    SELECT m.id,
           COALESCE(due.total, 0)::integer
      FROM public.markets AS m
      LEFT JOIN LATERAL (
          SELECT count(*)::integer AS total
            FROM public.capture_runs AS r
           WHERE r.market_id = m.id
             AND r.status = 'pending'
             AND r.scheduled_at <= now()
      ) AS due ON true
     WHERE m.is_active
```

> **5-fazada IKKI job shu naqshni oladi:** `day_close` va `audit_draw`.
> Ikkalasi ham **faqat identifikator** qaytaradigan `SECURITY DEFINER`
> funksiyadan bozorlarni oladi, keyin **har bozor uchun alohida
> `_system_transaction()`**. Bitta tranzaksiyada ikki bozor — tenant sizib
> chiqishining eng qisqa yo'li (GUC'lar `SET LOCAL`).
>
> **Ikki darvoza AVTOMATIK yopiladi:** `tests/tenancy/test_meta.py:495`
> (`test_security_definer_functions_pin_search_path`) va
> `test_snapshot_domain_meta.py:573`
> (`test_capture_due_markets_exposes_only_identifiers`). **Yangi funksiya
> uchun ikkinchisining jufti yoziladi:** funksiya bandlik verdikti,
> confidence yoki nazoratchi javobini **qaytarmasligi** shart — aks holda u
> RLS ni chetlab o'tuvchi ma'lumot yo'li bo'lardi. D-17 sharoitida bu
> ikkinchi ma'noga ega: namuna tortadigan funksiya `verdict`/`confidence`
> ni **qaytara olmaydi** — §S-6.2 ning DB tomondagi jufti.

---

### S-6. Ko'r auditning BESH STRUKTURAVIY HIMOYASI

| # | Himoya (D-17) | Mexanizm | Mavjud naqsh |
|---|---|---|---|
| 1 | Hosila urug' — namuna qayta chizilmaydi | `seed = f(market_id, business_date, round_no)`; tartib hash bo'yicha | **analog yo'q** (§4.6). ⚠ M-1: `digest()` yo'q → `sha256(bytea)` |
| 2 | AI maydonlari payloadda **umuman yo'q** (`None` emas — kalitning O'ZI yo'q) | `queue_kind='blind_audit'` da boshqa javob modeli | `self_check.py:100-106` + `go2rtc.py:193-197` («metodning yo'qligi — STRUKTURA») |
| 3 | `CHECK (queue_kind <> 'blind_audit' OR shown_ai_verdict = false)` | DB konstrayti | `models/snapshot.py:709-712` (ikki ustun orasidagi majburiy bog'lanish) |
| 4 | Javob o'zgarmas — oshkor qilingandan keyin tahrirlab bo'lmaydi | Shartsiz o'zgarmaslik triggeri | §S-3 |
| 5 | 70/30 `eval`/`train` — **tortish paytida** belgilanadi | `review_assignments.purpose` `INSERT` da to'ladi | `models/snapshot.py:629-636` |

**5-himoyaning verbatim analogi** — `models/snapshot.py:629-636`:

```python
    **(b) `quality_verdict` YOZISH PAYTIDA QO'YILADI, HISOBLANMAYDI**
    (T-04-23). U oddiy ustun va hech qachon qayta baholanmaydi;
    `quality_thresholds_version` esa QAYSI chegara to'plami bilan
    qo'yilganini yozadi. Aks holda chegarani sozlash ... o'tmishdagi
    kadrlarning billing yaroqliligini RETROAKTIV o'zgartirardi — ya'ni bir
    yil oldin yozilgan hisob bugun o'z-o'zidan bekor bo'lardi.
```

> 🔴 **`thresholds_version` VA `model_version` SHU SABABGA KO'RA QATORDA**
> (D-11, D-12). `UNIQUE (market_id, snapshot_id, camera_zone_id,
> model_version)` — «yangi model bilan qayta ishlash *yangi qator*, eskisini
> o'chirmaydi». Bu §E.15 dagi `timm` ilgagining va «yaxshilanishni o'lchash
> mashinasi» ning butun mexanizmi.

**Ikki navbatning o'zaro istisnosi** — `review_assignments` da
`UNIQUE (occupancy_event_id)`; poyga **DB'ga topshiriladi**. Verbatim manba —
`app/repositories/nvr_repo.py:509-517`:

```python
        """Yangi kashfiyot yugurishini `queued` holatida yozadi.

        ⚠ «Faol yugurish bormi?» TEKSHIRILMAYDI — bu ataylab.
          `0012` dagi QISMAN UNIQUE indeks ... ikkinchi faol yugurishni
          `23505` bilan rad etadi va chaqiruvchi uni 409 ga aylantiradi
          (03-06). Oldindan tekshirish «tekshir-keyin-yoz» poygasini
          tug'dirardi ...
```

⚠ **TARTIB MUHIM** (RESEARCH §C.8.3): **avval ko'r audit namunasi tortiladi,
keyin noaniq navbat quriladi.** Teskari tartibda audit doirasi «noaniq»
lardan tozalangan bo'lardi va aniqlik sun'iy ko'tarilardi.

---

### S-7. Xato taksonomiyasi — KOD reyestri **UCH JOYDA**

**Verbatim:** `frontend/scripts/error-codes.test.mjs:16-34`

```
 * Qamralgan uch ro'yxat:
 *   * `MARKET_ERROR_CODES`      -> `ERROR_CODES` + `marketErrorMessageKey`
 *   * `BlockingItem.code`       -> `wizard.blocking.*`
 *   * `ImportIssue.code`        -> `import.errors.*`
...
 * 3-FAZA (G-1 va G-2) — TO'RTINCHI ro'yxat va u BOSHQA SINFDAN:
 *   * `NVR_ERROR_CODES`  -> `lib/nvr-errors.ts` -> `cameras.errorCause.*`
 *                           VA `cameras.errorFix.*`
 *
 * Farqi shundaki, bu yerda har kod uchun IKKITA matn talab qilinadi.
```

**Backend reyestrini o'qish — verbatim:** `error-codes.test.mjs:92-107`

```js
function readPythonFrozenset(source, name) {
  const start = source.indexOf(`${name}: Final[frozenset[str]] = frozenset(`);
  assert.ok(start !== -1, `${name} backend faylida topilmadi`);

  const rest = source.slice(start);
  const end = rest.indexOf("\n)");
  assert.ok(end !== -1, `${name} bloki yopilmagan`);

  return rest
    .slice(0, end)
    .split("\n")
    .filter((line) => !line.trim().startsWith("#"))
    .map((line) => /^\s*"([a-z_]+)",\s*$/u.exec(line))
    .filter(Boolean)
    .map((match) => match[1]);
}
```

> **5-faza OLTINCHI ro'yxatni qo'shadi:** `OCCUPANCY_ERROR_CODES`
> (`app/services/occupancy_errors.py`) → `frontend/src/lib/occupancy-errors.ts`
> → `messages/*.json`. Fayl yo'llari `error-codes.test.mjs:45-72` dagi
> konstantalar bloki shaklida qo'shiladi (4-faza `CAPTURE_ERRORS` /
> `BACKEND_CAPTURE_ERRORS` juftligini aynan shu yerga qo'shgan).
>
> ⚠ `occupancy_events` da **xato ustuni YO'Q** (u o'zgarmas hodisa jurnali),
> ya'ni kodlar faqat HTTP `detail` bo'ladi va `MARKET_ERROR_CODES` ga
> **`import` qilinadi**, qo'lda takrorlanmaydi (`app/schemas.py:33,490,567`).

---

### S-8. SOF FUNKSIYA MODULI — geometriya, agregatsiya, statistika

**Shakl — verbatim:** `app/services/quality.py:1-6`

```
"""Kadr sifati — bayt oqimidan verdikt va `light_mode` (CAM-06, D-12/D-13/D-14/D-15).

Sof funksiyalar moduli (`rtsp.py`, `live_source.py` bilan bir xil shakl):
tarmoqqa chiqmaydi, bazaga tegmaydi, holat saqlamaydi va `Settings` ni
BILMAYDI — chegaralar unga argument sifatida kiradi.
"""
```

> 🔴 «`Settings` ni BILMAYDI — chegaralar argument sifatida kiradi» — D-11
> ning bevosita talabi: `uncertain` chegaralari `thresholds_version` bilan
> **qatorda** yashaydi, ya'ni ular funksiyaga **kirish**, `import` emas.
> Aks holda «sozlash SQL bilan, migratsiyasiz» va'dasi buzilardi.

**Xato kodi konstantasining shakli — verbatim:** `app/services/live_source.py:100-106`

```python
CREDENTIAL_INJECTION = "rtsp_credential_injection"
"""Rekvizit manzilning avtoritetini yoki yo'lini O'ZGARTIRDI (T-03-88).

Bu holat to'g'ri kodda HECH QACHON yuz bermaydi — u faqat foizli kodlash
buzilganda chiqadi. Ya'ni bu satr ko'rinishi KODDA xato borligining
belgisi va uni jimgina yutish mumkin emas.
"""
```

`zone_geometry.py` jufti: `POLYGON_TOO_FEW_POINTS`, `POLYGON_TOO_MANY_POINTS`,
`POLYGON_OUT_OF_RANGE`, `POLYGON_SELF_INTERSECTING`, `ASPECT_RATIO_MISMATCH` —
**har biri docstring bilan**.

**Domen sof funksiyasi `sbozor_core` da:** `sbozor_core/periods.py:43-45`

```python
__all__ = ["PERIOD_BOUNDS", "assignment_period", "period_contains"]

PERIOD_BOUNDS: Final[Literal["[)"]] = "[)"
```

> **`aggregate_stall_slot()` (AI-05) AYNAN SHU YERGA TUSHADI** —
> `packages/sbozor-core/sbozor_core/occupancy.py` (RESEARCH §D.11: «bazada
> emas, API'da emas»). `core-api` ham, `cv-service` ham import qiladi —
> ikki nusxa tug'ilmaydi.
> ⚠ Ustuvorlik **talabdagidan uzunroq**: `occupied > uncertain > empty >
> no_coverage`. `no_coverage` **«bo'sh» EMAS** (D-22) va bu farq testda
> **to'liq sanab chiqiladi** (3 verdict + yo'qlik, 1–4 kamera).

---

### S-9. Fixture nomlash — FIZIK/GEOMETRIK FAKT, verdikt aks-sadosi EMAS

**Verbatim:** `tests/fixtures/frames.py:3-29`

```
=============================================================================
MAJBURIYAT 1 — NOMLASH QOIDASI: FIZIK XUSUSIYAT, DETEKTOR VERDIKTI EMAS.

    frame_bytes(mean=8, stddev=2)        ✅
    test_mean_8_stddev_2_reads_back...   ✅

    frame_dark() / frame_blank()         ❌
    test_dark_frame_is_rejected()        ❌

⚠ SABABI TO'G'RIDAN-TO'G'RI: chegara bilan nomlangan fixture testni O'Z
  FARAZINING AKS-SADOSIGA aylantiradi. `frame_rejected_by_filter()` degan
  fixture "filtr rad etadigan kadr" ni yasash uchun filtrning CHEGARASINI
  bilishi kerak — ya'ni u chegarani chegaraning O'ZI bilan tekshiradi va
  chegara noto'g'ri qo'yilgan bo'lsa ham YASHIL qoladi. ...

  Bu modul sifat filtrini UMUMAN import qilmaydi va uning chegaralarini
  BILMAYDI.
```

**Determinizm — verbatim:** `frames.py:32-37, 102-103`

```
MAJBURIYAT 2 — DETERMINIZM: BIR XIL ARGUMENT -> BIR XIL BAYTLAR.

Shovqin `random` GLOBAL modulidan OLINMAYDI. Qadalgan urug'li mustaqil
generator (`random.Random(_SEED)`) ishlatiladi va u har chaqiruvda YANGIDAN
quriladi — modul darajasida umumiy holat yo'q ...
```

```python
_SEED: Final = 20260804
"""Qadalgan urug'. Qiymatning O'ZI ahamiyatsiz — QADALGANLIGI ahamiyatli."""
```

> 🔴 **5-FAZADA MAJBURIYAT KUCHLIROQ SHAKLDA QAYTADI** (RESEARCH §Validation):
>
> | ✅ To'g'ri (geometrik fakt) | ❌ Noto'g'ri (verdikt aks-sadosi) |
> |---|---|
> | `detections_at(boxes=[(0.4,0.5,0.5,0.6)])` | `detections_that_make_zone_occupied()` |
> | `polygon_unit_square()` | `polygon_that_catches_the_box()` |
> | `review_pairs(ai=[...], human=[...])` | `reviews_with_94_percent_accuracy()` |
>
> **Kutilgan natijalar QO'LDA hisoblanadi va testda LITERAL yoziladi** —
> tekshirilayotgan funksiya chaqirilib olinmaydi.
> ⚠ `tests/fixtures/detections.py` uchun **analog yo'q** (§4.2): `frames.py`
> **shaklni** beradi (`__all__`, tolerans konstantalari, CLI, alohida
> determinizm testi `test_frame_fixtures.py`), mexanika esa yangi.

---

### S-10. DARVOZA SANOQ EMAS, **MANBADAN HOSILA** — 04-13 ning eng qimmat darsi

**Verbatim:** `tests/unit/test_sentry_processes.py:1-33`

```
"""Sentry darvozasi — SANOQ EMAS, `compose.yaml` DAN HOSILA (04-13, FOUND-06).

=============================================================================
⛔ DARVOZANING O'ZI NOSOZ EDI VA U SHU SABABDAN QAYTA YOZILDI.

04-12 «Sentry ikkala jarayonda ham o'rnatiladi» da'vosini IKKITA **kod
kirish nuqtasi** ro'yxati bilan qulflagan edi ...
Ikkalasi ham UCHINCHI **jarayonni** (`scheduler`) struktura jihatidan
ko'ra olmaydi, shuning uchun ular abadiy yashil edi — `04-VERIFICATION.md`
nosozlikni testdan emas, KONTEYNERDAN o'lchab topdi.

⚠ Ro'yxatga uchinchi nomni qo'shish nosozlikni n+1 da QAYTADAN tug'dirardi.
=============================================================================
DARVOZA UCH BOSQICHDA ISHLAYDI VA HAR UCHALASIDA «TOPILMADI» = YIQILISH:

  (a) JARAYONLARNI TOPISH   — `environment` da `SENTRY_DSN` bo'lgan har servis
  (b) KIRISH NUQTASI        — `command` tokenlari ichidan AYNAN BITTA
                              `modul:atribut` (topilmasa `pytest.fail`)
  (c) O'SHA OBYEKTNING O'Z REYESTRI — obyekt TURIGA qarab mos hodisa
                              reyestrida `init_sentry(` bo'lishi talab
                              qilinadi (noma'lum tur -> `pytest.fail`)

«O'tkazib yuborish» yo'li ATAYIN YO'Q: aynan o'sha yo'l 04-12 ning
darvozasini uchinchi jarayonda jimgina bo'shatgan edi.
```

**Predikat, ro'yxat emas — verbatim:** `test_sentry_processes.py:62-68, 93-95`

```python
SENTRY_ENV_KEY: Final = "SENTRY_DSN"
"""Jarayonni «kuzatuv va'da qilingan» deb belgilaydigan YAGONA belgi.

⚠ Ro'yxat EMAS, PREDIKAT: darvoza servis NOMLARINI bilmaydi va bilishi
  ham kerak emas. `compose.yaml` bu kalitni kimga bersa, o'sha jarayon
  `init_sentry()` ni chaqirishi SHART.
"""
...
⚠ Servis NOMLARI bu faylda ro'yxat sifatida YOZILMAGAN va bu ataylab —
  aynan nomlar ro'yxati 04-12 ning darvozasini eskirtirgan edi.
```

> 🔴 **IKKI OQIBAT:**
> **(a) `cv-service` bu darvozaga AVTOMATIK tushadi.** Unga `SENTRY_DSN`
> berilsa (berilishi kerak), test darhol `init_sentry(` ni talab qiladi.
> Bosqich (c) obyekt TURIGA qarab dispatch qiladi (`FastAPI` /
> `AsyncBroker` / `TaskiqScheduler`) va **noma'lum tur → `pytest.fail`**,
> `skip` emas — jimgina o'tib ketish yo'li yo'q.
> **(b) BU FAZANING HAR YANGI DARVOZASI SHU TEXNIKADA YOZILADI:**
> «Ommaviy tasdiqlash endpointi yo'q» (D-18) — **OpenAPI sxemasini
> skanerlaydi** (analog `tests/tenancy/test_route_coverage.py`);
> «Ko'r audit javobida `verdict`/`confidence` yo'q» — javobni **rekursiv
> skanerlaydi**, ma'lum maydonni tekshirmaydi.
>
> ⚠ **TESKARI HOLAT HAM BOR VA U ZID EMAS** — `self_check.py:114-121`:
>
> ```python
> """Yurak urishi KUTILADIGAN fon komponentlari.
>
> ⚠ RO'YXAT SHU YERDA QATTIQ YOZILGAN va u `system_heartbeats` jadvalidan
>   HOSILA EMAS — bu farq butun darvozaning mazmuni. Jadvaldan o'qilsa
>   «hech qachon yozilmagan komponent» tushunchasining O'ZI yo'qolardi:
>   bo'sh jadval «kutilayotgan hech nima yo'q» degan ma'no berib, endpoint
>   `200 ok` qaytarardi ...
> """
> ```
>
> **«Kim BOR?» savoliga manbadan javob olinadi; «kim BO'LISHI KERAK?»
> savoliga reyestr javob beradi.** `cv-service` komponentlari
> (`cv_detect`) `EXPECTED_COMPONENTS` ga **qo'lda** qo'shiladi.

**Quyi chegara majburiy** — `test_runtime_deps.py:291-302`
(`test_manifest_actually_parsed`) va `test_sentry_processes.py:79-98`
(`MIN_COMPOSE_SERVICES`, `MIN_ENV_KEYS`). **Har yangi «fayl o'qiydigan»
darvoza shu quyi chegarani oladi.**

---

### S-11. `cv-service` — **UCHINCHI SERVIS**, «to'rtinchi konteyner» EMAS

**Mavjud qoida — verbatim:** `compose.yaml:491-503` (`nvr-sim`)

```yaml
    # `core-api` Dockerfile'ining `dev` target'i QAYTA ISHLATILADI (B.9):
    # yangi Dockerfile yo'q, CI'da yangi build qatlami yo'q, yangi paket yo'q.
    # Bu TO'RTINCHI KONTEYNER, uchinchi servis emas — `migrate` va `tests`
    # bilan aynan bir xil naqsh, ya'ni CLAUDE.md ning "aynan 3 ta servis"
    # cheklovi buzilmaydi.
```

> 🔴 **`cv-service` UCHUN BU NAQSH ISHLAMAYDI — SABAB BOG'LIQLIKLARDA.**
> `core-api` `opencv` ni **ataylab rad etadi** va buni test **mexanik
> qulflaydi** — `tests/unit/test_runtime_deps.py:91-94`:
>
> ```python
>     # D-13: sifat filtri uchun `Pillow` yetadi. `opencv` — `cv-service`
>     # ning bog'liqligi (5-faza) va u runtime image'ga ~70 MB qo'shardi.
>     "opencv-python",
>     "opencv-python-headless",
> ```
>
> Ya'ni `cv-service` **o'z `pyproject.toml`, `uv.lock` va `Dockerfile`** i
> bilan keladi. CLAUDE.md **buzilmaydi**: `cv-service` allaqachon uchlikning
> a'zosi (D-23, RESEARCH §E.13).
>
> ⚠ **`sbozor-core` UCHALASIDA BAHAM KO'RILADI** —
> `services/core-api/pyproject.toml:128-129`:
>
> ```toml
> [tool.uv.sources]
> sbozor-core = { path = "../../packages/sbozor-core", editable = true }
> ```
>
> ⚠ **`services/nvr-sim` da `pyproject.toml` HAM, `Dockerfile` HAM YO'Q**
> (o'lchandi) — loyihada **ikkinchi bog'liqlik to'plami hech qachon
> qurilmagan**; bu §4.4 ning mavzusi.

**Compose bloki:** `compose.yaml:245-347` (`worker`) — profilsiz,
`restart: unless-stopped`, `depends_on: cache` + `db`, `--workers 1`,
`SENTRY_DSN`. **`ports:` bloki YO'Q** (`go2rtc` blokidagi ogohlantirish:
«compose `ports:` bandi Docker'ning `iptables` qoidalarini yozadi va u host
firewall'ini CHETLAB O'TADI»). Sirlar `:-` bilan bo'sh standart **olmaydi**
(`NVR_CREDENTIAL_KEY: ${NVR_CREDENTIAL_KEY}` izohi: «worker ko'tarilib, xato
faqat birinchi kashfiyotda chiqardi (T-03-22)»).

> ⚠ **HEALTHCHECK SOXTALASHTIRILMAYDI** (`04-PATTERNS.md` §3.11): jarayon
> tirikligi «ish bajarilyaptimi?» savoliga javob bermaydi. Shuning uchun
> `cv-service` da **minimal FastAPI** bor (D-23) va u yurak urishini yozadi;
> konteyner healthcheck'i `nc -z` bilan (`go2rtc` naqshi).
> ⚠ **ONNX FAYLI `COPY` BILAN KIRADI (D-24).** `.gitattributes:31` da
> `*.onnx binary` **allaqachon yozilgan**. Ish paytida yuklab olish **yo'q**.

---

### S-12. Frontend — kalitlar TUG'ILISHIDANOQ market-scoped

**Verbatim:** `frontend/src/lib/snapshot-queries.ts:30-42`

```
 * ⚠ KALITLAR TUG'ILISHIDANOQ DOIRALANGAN (§5.4). `domainKey`
 *   `market-queries.ts` DAN IMPORT QILINADI — ikkinchi nusxa
 *   yaratilmaydi. GLOBAL (marketsiz) KALIT KONSTANTASI BU MODULDA
 *   UMUMAN YO'Q: har fabrikaning BIRINCHI argumenti `marketId`, ya'ni
 *   doiralashni chetlab o'tish TypeScript xatosisiz mumkin emas.
 *   Bu — CR-01 ning strukturaviy davosi, kod-ko'rikdagi eslatma emas.
 *
 * ⚠ TIP TIZIMI YOLG'IZ YETARLI EMAS va bu o'lchangan (04-02): kalitdan
 *   `marketId` ni TUSHIRIB QOLDIRISH typecheck'ni qizartiradi, lekin
 *   `domainKey("snapshots", ...)` yozish ... TIP JIHATIDAN YAROQLI.
 *   Shuning uchun kalit SHAKLI birlik testi bilan ham qulflanadi
 *   (`snapshot-queries.test.tsx`).
```

**Fabrika shakli:** `snapshot-queries.ts:84-88`

```ts
export const scheduleTodayKey = (marketId: string) =>
  domainKey(marketId, "schedule", "today");

export const schedulesKey = (marketId: string) =>
  domainKey(marketId, "schedules");
```

> **5-faza jufti** — `zone-queries.ts` (`cameraZonesKey(marketId, cameraId)`)
> va `review-queries.ts` (`reviewQueueKey(marketId, kind)`,
> `accuracyReportKey(marketId, from, to)`). Ikkalasi ham `domainKey` ni
> import qiladi va `*-queries.test.tsx` bilan qulflanadi.
> ⚠ **POLL ORALIG'I HAR DOMENDA QAYTA HISOBLANADI** (`snapshot-queries.ts:57-71`:
> 3-fazaning 2000 ms i ko'chirilmagan, chunki oyna 15 daqiqa). Nazoratchi
> navbatiga poll **umuman kerak emas** — qaror va sabab modul izohida.

---

### S-13. Frontend sof mantiq — **`.ts` modul + `.test.tsx` test** (M-2/M-3)

**Nega sof mantiq ajratiladi — verbatim:** `frontend/src/components/cameras/camera-page-state.ts:1-25`

```
/*
 * =============================================================================
 * `/cameras` SAHIFASINING SOF QARORLARI.
 *
 * NEGA ALOHIDA MODUL — O'LCHOV BILAN TOPILDI (03-09 sabotaji S3):
 *
 *   Bu qarorlar dastlab `page.tsx` ning ichida, eksport qilinmagan
 *   funksiyalar edi. Sabotaj `cameraEmptyKind` dan E-1 ning shartini
 *   olib tashladi ... Natija: `typecheck`, `lint`,
 *   `build`, 167 vitest va 86 node testi — HAMMASI YASHIL qoldi.
 *
 *   Ya'ni rejaning O'Z talabi ... hech qanday mexanizm bilan qamralmagan edi.
 *   Marshrut faylining ichidagi funksiyani test qilib bo'lmaydi ...
 * =============================================================================
 */
```

**Fayl kengaytmasi — verbatim:** `camera-page-state.test.tsx:16-20`

```
 * ⚠ FAYL KENGAYTMASI `.tsx` VA BU MAJBURIY: `vitest.config.ts` ning
 *   `include` naqshi `src/**\/*.test.tsx`. `.ts` fayl JIMGINA ishga
 *   tushmasdi va «hammasi yashil» hisoboti yolg'on bo'lardi (03-08 da
 *   o'lchangan holat).
```

> 🔴 **RESEARCH ning `frontend/scripts/zone-geometry.test.mjs` +
> `src/lib/zone-geometry.ts` juftligi BAJARILMAYDI** (M-3). Ikki yaroqli
> yo'l va reja ATAYIN bittasini tanlaydi:
>
> | Yo'l | Modul | Test | Ustunligi | Narxi |
> |---|---|---|---|---|
> | **A (tavsiya)** | `src/lib/zone-geometry.ts` | `src/lib/zone-geometry.test.tsx` (vitest) | Tiplangan; `zone-editor.tsx` to'g'ridan-to'g'ri import qiladi; `camera-page-state` naqshining takrori | `npm run test:unit` (`node --test`) uni ko'rmaydi — u `vitest run` da yuradi |
> | B | `scripts/zone-geometry.mjs` | `scripts/zone-geometry.test.mjs` | `gen-cyrillic.mjs` ning aniq takrori | Tip yo'q; komponent `.mjs` import qiladi; ikkinchi modul tizimi |
>
> **A tanlanadi** — RESEARCH §A.5 ning o'zi: «render qatlami almashtiriladi,
> geometriya emas», ya'ni geometriya komponent bilan **bir xil tip
> tizimida** bo'lishi kerak. Qaror va M-3 sababi `zone-geometry.ts`
> docstringiga yoziladi.

**SVG qarorining o'lchov asosi — verbatim:** `frontend/src/components/stalls/stall-map.tsx:22-37`

```
/*
 * =============================================================================
 * SXEMATIK PLAN-XARITA — CSS Grid + memoizatsiyalangan tugmalar.
 *
 * Canvas kutubxonasi (RESEARCH Pattern 11) O'LCHOV bilan rad etilgan:
 * bu yerda render STATIK (D-19 drag-drop'ni rad etdi, D-20 faqat holat
 * uslubini beradi), ya'ni canvas'ning yagona ustunligi — kadr-bo'yicha
 * qayta chizish — umuman ishlatilmasdi. 1000 elementli React yangilanishi
 * memo bilan ~4 ms; narxi esa haqiqiy bo'lardi: SSR yo'q, a11y yo'q,
 * matn o'lchamlari qo'lda.
 *
 * VIRTUALIZATSIYA KUTUBXONASI HAM QO'SHILMAYDI: `content-visibility: auto`
 * ... — nol bog'liqlik, nol JS.
 * =============================================================================
 */
```

> ⚠ **BU IZOH D-05 NING DALILI, LEKIN TO'LIQ EMAS — FARQ REJADA YOZILSIN.**
> `stall-map.tsx` da render **STATIK** («D-19 drag-drop'ni rad etdi»);
> poligon muharririda render **INTERAKTIV** — tepani sudrash `mousemove`
> chastotasida qayta chizadi. Ya'ni 2-fazaning o'lchovi «1000 element DOM'da
> o'ladi» ni rad etadi, lekin «sudrash 16 ms ichida» ni **isbotlamaydi**.
> D-05 shuni ochiq qoldirgan («50+ poligonda >16 ms bo'lsa → Konva»). Reja
> bu o'lchovni **darvoza qilmasin**, lekin `zone-editor.tsx` docstringida
> ochiq yozsin.

**Klaviatura naqshi — verbatim:** `frontend/src/components/snapshots/capture-grid.tsx:16-42`

```
 * ⛔⛔ MATRITSA ROLI QO'YILMAYDI — SEMANTIKA NATIVE JADVAL.
 *
 *     Vasvasa aniq: naqsh ARIA APG dan olingan va o'sha hujjat aynan shu
 *     nomdagi rolni ko'rsatadi. Bu yerda u ATAYIN QO'YILMAYDI ...
 *
 * ⛔ KLAVIATURA TUZOG'I (T-04-88, WCAG 2.1.2). 25 kamera × 7 vaqt = 175
 *    bosiladigan hujayra. Har biri alohida tab to'xtashi bo'lsa,
 *    klaviatura foydalanuvchisi jurnaldan CHIQIB KETA OLMAYDI. Shuning
 *    uchun butun matritsa uchun BITTA to'xtash: faol hujayra
 *    `tabIndex={0}`, qolganlari `tabIndex={-1}`; ular orasida o'q
 *    tugmalari ko'chiradi.
 *
 *    3-fazada bu kerak emas edi ... — bu kodbazada roving tabindex
 *    BIRINCHI marta ishlatilyapti.
```

> **Poligon muharririda AYNAN SHU MUAMMO qaytadi:** bir kamerada 10–40
> poligon × 4–6 tepa = 40–240 fokuslanadigan `<circle>`. Roving tabindex
> **majburiy**, ARIA roli **qo'yilmaydi** — `<polygon tabIndex>` yetadi
> (RESEARCH §A.5).

---

### S-14. Faza darvozasi — mezon boshiga BITTA test + META-TEST + MOCK'SIZ O'LCHOV

**Verbatim:** `tests/integration/test_phase4_criteria.py:1377-1403`

```python
def test_every_criterion_has_its_own_test() -> None:
    ...
    for number in range(1, 6):
        owned = [name for name in names if name.startswith(f"test_sc{number}_")]
        assert len(owned) == 1, (...)

    criteria = [name for name in names if name.startswith("test_sc")]
    assert len(criteria) == 5, f"mezon testlari soni 5 emas: {criteria}"
```

Ikkinchi darvoza — `test_phase4_criteria.py:1406`
(`test_criteria_module_uses_no_storage_mock`); 3-fazada u go2rtc mock'i edi.

> **5-fazada:** `test_phase5_criteria.py` da **beshta** mezon (`range(1, 6)`,
> `len(criteria) == 5`) — RESEARCH SC#1…SC#5.
> 🔴 **MOCK'SIZ O'LCHOVNING JUFTI — ONNX SESSIYASI.** Bu darvoza yozilmasa,
> birinchi «qulaylik uchun» soxta detektor butun inference yo'lini
> **o'lchanmagan** qoldirardi (03-14 va 04-12 nosozliklarining uchinchi
> takrori). Shakl — `test_phase3_criteria.py:1120-1124`
> (`inspect.signature` bilan mock fixture'ini izlash).
> ⚠ **LEKIN CHOK `sv.Detections` DA (D-02):** undan **keyingi** hamma narsa
> sintetik `Detections` bilan testlanadi va bu **to'g'ri**. Mock taqig'i
> faqat `test_phase5_criteria.py` va `test_onnx_session.py` ga tegishli.

---

### S-15. i18n — Cyrillic allowlist va `ъ` ning IKKI MA'NOSI (O'LCHANGAN)

**Verbatim:** `frontend/scripts/gen-cyrillic.test.mjs:695-741`

```
 * ⛔ QOIDA 6 — `ъ` NING IKKI MA'NOSI [O'LCHANDI: 04-UI-SPEC §11.11, M-9].
 *
 *   TO'G'RI  `ma'lumot` -> `маълумот`, `ta'sir` -> `таъсир`
 *   DEFEKT   `NVR'ga` -> `НВРъга`
 ...
 *     DEFEKT := /[A-Za-z]ъ/         TO'G'RI := /[а-яёқғҳўъ]ъ/i
 *
 *     transliterate("NVR'ga ulanmadi")  ->  "НВРъга уланмади"
 *     kod nuqtalari:  Н=U+41D  В=U+412  Р=U+420  ъ=U+44A
 ...
 *     /[A-Za-z]ъ/          defektni HECH QACHON ushlamaydi (o'lchandi: false)
 *     /[а-яёқғҳўъ]ъ/i      defektni TO'G'RI deb belgilaydi  (o'lchandi: true)
```

**Ishlaydigan diskriminator — verbatim:** `gen-cyrillic.test.mjs:751-758`

```js
  /** Akronim qoldig'i: `ъ` dan oldin ikki yoki undan ko'p BOSH harf. */
  const ACRONYM_DEFECT = /[A-ZА-ЯЁҚҒҲЎ]{2,}ъ/u;

  /** Spetsifikatsiyaning literal sharti — lotin harfidan keyingi `ъ`. */
  const LATIN_DEFECT = /[A-Za-z]ъ/u;

  /** Tutuq belgisi — `ъ` dan oldin kichik kirill harfi. */
  const TUTUQ = /[а-яёқғҳў]ъ/u;
```

> 🔴 **5-FAZA KO'P YANGI AKRONIM OLIB KELADI:** `AI`, `ONNX`, `RF-DETR`,
> `SVG`, `JSON`, `CV`, `Wilson`, `eval`, `train`. `AI'ga` → `АИъга` — ya'ni
> `uz-Cyrl.overrides.json -> words` bilan **juft** yuritish majburiy va
> `gen-cyrillic.test.mjs::allowed` regexi (`:502-516`) kengaytiriladi
> (4-faza `S3`, `SeaweedFS`, `JPEG`, `IR`, `Telegram`, `Sentry`, `UTC` ni
> qo'shgan).
> ⚠ «`ъ` dan oldin UNLI bo'lsa to'g'ri» degan muqobil qoida **NOTO'G'RI**
> (`:739-741`): `санъат` va `қалъа` da `ъ` dan oldin **undosh** turadi.

---

## 3. Pattern Assignments — fayl bo'yicha

### 3.1 `migrations/versions/0018_occupancy_domain.py`

**Analog:** `migrations/versions/0014_snapshot_domain.py` (842 qator) —
**to'liq shablon**. Undan oldingi shablon `0012_nvr_domain.py`.

**Fayl sarlavhasi:** «BU MIGRATSIYADA QOTIB QOLADIGAN QARORLAR» bloki
majburiy — kamida **oltita** band:

1. Jadval nomi **`camera_zones`** — `zones` band (§S-1, D-06)
2. `occupancy_events` **audit triggeridan chiqarilgan** (~5000 qator/kun/bozor + o'zgarmas jadval)
3. `occupancy_events` ga **shartsiz** o'zgarmaslik triggeri (§S-3, D-12)
4. `FOREIGN KEY (snapshot_id, snapshot_is_billable) REFERENCES snapshots (id, is_billable)` + `CHECK (snapshot_is_billable)` (§S-4, D-21)
5. `UNIQUE (market_id, snapshot_id, camera_zone_id, model_version)` — qayta ishlash **yangi qator** (D-12, §E.15 ilgagi)
6. `CHECK (queue_kind <> 'blind_audit' OR shown_ai_verdict = false)` (D-17.3)

**Revision bloki** (`0014` shakli):

```python
revision: str = "0018"
down_revision: str | Sequence[str] | None = "0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None
```

**RLS + audit tsikllari — IKKI ALOHIDA RO'YXAT ustidan** (`0012_nvr_domain.py:454-471`):

```python
    for table in OCCUPANCY_TENANT_TABLES:
        enable_tenant_rls(table)
        create_entity(tenant_policy(table))
        create_entity(owner_bootstrap_policy(table))
    ...
    for table in OCCUPANCY_AUDITED_TABLES:
        attach_audit_trigger(table)
```

**`downgrade()` — teskari tartib** (`0012_nvr_domain.py:474-492`): audit
`detach` → **o'zgarmaslik triggerlarini yechish**
(`detach_immutability_trigger`, `helpers.py:307-309`) → policy `drop` →
indekslar → `op.drop_table` **bolalardan ota-onaga**.

> ⚠ **M-1 — `pgcrypto` MUAMMOSI VA UCH YO'L.** `btree_gist` bu fazada kerak
> **emas** (`EXCLUDE` yo'q). `pgcrypto` esa faqat RESEARCH §C.8.1 ning
> `digest()` variantini tanlagan holda kerak:
>
> | Yo'l | Nima kerak | Narxi |
> |---|---|---|
> | **A (tavsiya)** — yadro `sha256(bytea)` | Hech nima. `ORDER BY sha256((id::text \|\| :seed)::bytea)` | Yo'q |
> | B — `pgcrypto` | `ops/db/init/00-extensions.sql` ga satr + `require_extension("pgcrypto")` + `test_meta.py:297` shaklida meta-test | Yangi kengaytma; `.env.example:49` izohi boshqa kontekstda ekanini tushuntirish |
> | C — tartib Python'da | `hashlib.sha256` + `IN (...)` | Katta doirada N ta ID ni ilovaga tortadi |
>
> **A tanlansa `require_extension` YOZILMAYDI.** Qaror `audit_rounds`
> docstringiga yoziladi.

**Kengaytma darvozasining shakli (B tanlansa) — verbatim:** `migrations/helpers.py:106-126`

```python
def require_extension(name: str) -> None:
    """Kengaytma bazada MAVJUDLIGINI talab qiladi; yo'q bo'lsa `RuntimeError`.

    BU TEKSHIRUV MIGRATSIYANING BIRINCHI SATRI BO'LISHI KERAK. Sabab: kerakli
    kengaytmasiz `op.create_table(...)` o'rtada yiqiladi ... va xabar aslida
    NIMA yetishmayotganini aytmaydi ...

    NEGA MIGRATSIYA KENGAYTMANI O'ZI YARATMAYDI (empirik, `postgres:18.4`):
    `sbozor_owner` — `NOCREATEDB` va bazaning egasi emas, ya'ni
    `CREATE EXTENSION` unga `permission denied to create extension` beradi.
    """
```

---

### 3.2 `packages/sbozor-core/sbozor_core/models/occupancy.py`

**Analog:** `models/snapshot.py` — **to'liq shablon** (879 qator).

**Fayl docstringining shakli — verbatim:** `models/snapshot.py:1-24`

```
"""Snapshot quvuri: mavsumiy jadval, kunlik reja, kadr va ogohlantirish.

=============================================================================
BU FAYLDA UCHTA KAFOLAT YASHAYDI VA UCHALASI HAM KODDA EMAS, SXEMADA.
Ular "qulaylik uchun" buzilishi oson, shuning uchun sabablari shu yerda.

1. `UNIQUE (market_id, camera_id, business_date, slot_time)` — CAM-05 ning
   IDEMPOTENTLIGI. Ilova qatlami bunga TAYANADI, uni TAKRORLAMAYDI ...
2. `EXCLUDE USING gist (market_id WITH =, period WITH &&)` — «bir kunga
   AYNAN bitta profil» ...
3. `UNIQUE (id, is_billable)` — 5-FAZA UCHUN ILGAK (D-16) ...
=============================================================================
```

**Oltala klass va `__table_args__` da MAJBURIYSI:**

| Klass | Mixinlar | Majburiy elementlar |
|---|---|---|
| `CameraZone` | `Base, TenantMixin, TimestampMixin` | kompozit FK→`cameras` **VA** →`stalls`; `UNIQUE(market_id, camera_id, stall_id, version)`; `UNIQUE(market_id, id)`; `CHECK (jsonb_array_length(polygon) >= 3)`; nuqta soniga **yuqori** chegara `CHECK` (RESEARCH Security: DoS) |
| `OccupancyEvent` | `Base, TenantMixin` — **`TimestampMixin` YO'Q** | kompozit FK→`snapshots (id, is_billable)` + `CHECK (snapshot_is_billable)`; kompozit FK→`camera_zones`; `UNIQUE(market_id, snapshot_id, camera_zone_id, model_version)`; `UNIQUE(market_id, id)`; verdict `CHECK` enum'dan; **shartsiz o'zgarmaslik triggeri** |
| `AuditRound` | `Base, TenantMixin` | `UNIQUE(market_id, business_date, round_no)`; `frame_size`, `frame_predicate_hash`, `drawn_at` (doira **muzlatiladi**, D-17.4) |
| `ReviewAssignment` | `Base, TenantMixin` | kompozit FK→`occupancy_events`; **`UNIQUE(occupancy_event_id)`**; `purpose` va `queue_kind` `CHECK` |
| `ZoneReview` | `Base, TenantMixin` — **`TimestampMixin` YO'Q** | kompozit FK→`review_assignments`; `CHECK (queue_kind <> 'blind_audit' OR shown_ai_verdict = false)`; `UNIQUE(market_id, id)`; **shartsiz o'zgarmaslik** + **audit** triggerlari |
| `StallSlotOccupancy` | `Base, TenantMixin` | kompozit FK→`stalls`; kompozit FK→`occupancy_events` (nullable); `UNIQUE(market_id, stall_id, business_date, slot_time)`; `CHECK ((verdict='occupied') = (winning_occupancy_event_id IS NOT NULL))` |

**Indeks nomlari — MODEL VA MIGRATSIYA UCHUN BITTA MANBA**
(`04-PATTERNS.md` §S-2; 4-faza jufti `models/snapshot.py:122-130`):

```python
CAPTURE_RUN_ACTIVE_STATUSES: tuple[str, ...] = (
    CaptureRunStatus.PENDING.value,
    CaptureRunStatus.RUNNING.value,
)
"""Watchdog «osilib qolgan» deb hisoblaydigan holatlar to'plami (FOUND-06).

`0014_snapshot_domain` dagi `ix_capture_runs_overdue` indeksining predikati
AYNAN shu ro'yxatdan hosil qilinadi, qo'lda ko'chirilmaydi — bu
`DISCOVERY_RUN_ACTIVE_STATUSES` (`models/nvr.py:83-93`) bilan bir xil qoida
```

> **Kamida ikki qisman indeks, ikkala predikat ham enum'dan HOSILA:**
> `ix_camera_zones_active` (`WHERE is_active`) va
> `ix_occupancy_events_uncertain` (`WHERE verdict = 'uncertain'`).
> ⚠ **`market_id` bilan boshlanmaydigan indeks bo'lsa** —
> `tests/tenancy/test_meta.py:44` dagi `INDEX_EXCEPTIONS` ga **sabab bilan**
> yoziladi, aks holda `test_tenant_indexes_lead_with_market_id`
> (`test_meta.py:460`) qizaradi.

**Denormalizatsiya izohining shakli — verbatim:** `models/snapshot.py:717-722`

```python
    # DENORMALIZATSIYA: 5/6-faza so'rovlari «shu kameraning shu kundagi
    # kadrlari» ni `capture_runs` ga `JOIN` qilmasdan olishi kerak.
    camera_id: Mapped[UUID] = mapped_column(PgUuid(as_uuid=True), nullable=False)
    # ⚠ `capture_runs.scheduled_at` DAN NUSXALANADI, MUSTAQIL HISOBLANMAYDI.
    #   Ikki mustaqil hisoblash manbai yarim tunda bir kun farq qilardi
    #   (Pitfall 3) — `SNAPSHOT_BUSINESS_DATE_EXPR` docstringiga qarang.
```

> **5-fazada IKKI JOYDA kerak:** `occupancy_events.business_date`/`slot_time`
> va `stall_slot_occupancy.business_date`. **Ikkalasi ham `snapshots` dan
> NUSXALANADI**; generated ustun bo'lsa ifoda `SNAPSHOT_BUSINESS_DATE_EXPR`
> bilan **aynan bir xil** bo'lishi shart va buni
> `test_snapshot_domain_meta.py:396`
> (`test_both_business_date_expressions_are_identical`) shaklidagi meta-test
> qulflaydi.

**Enum e'loni** — `sbozor_core/enums.py:217-220` shakli; keyin `_quoted()`
bilan `CHECK` ifodasi (`models/nvr.py:104-117`).

---

### 3.3 `migrations/entities/triggers.py` (MOD)

**Analog:** `AUDIT_IMMUTABLE` (`triggers.py:131-146`) — to'liq matn §S-3 da.

**Reyestrga qo'shish:** `triggers.py:40-57` (`__all__`) va guruh
konstantalari (`MARKET_DOMAIN_TRIGGER_FUNCTIONS`,
`NVR_DOMAIN_TRIGGER_FUNCTIONS`, `ALL_TRIGGER_FUNCTIONS`) — 5-faza
`OCCUPANCY_TRIGGER_FUNCTIONS` qo'shadi va uni `ALL_TRIGGER_FUNCTIONS` ga
ulaydi.

**`SECURITY DEFINER` YO'QLIGI — ATAYIN** (`triggers.py:24-38`), va u
`tests/tenancy/test_meta.py:694`
(`test_audit_trigger_function_is_not_security_definer`) bilan qulflangan.
Yangi qo'riqchilarda ham `SECURITY DEFINER` **yozilmaydi**;
`SET search_path = pg_catalog, public` esa **majburiy**.

---

### 3.4 `services/cv-service/app/jobs/detect.py`

**Analog:** `core-api/app/jobs/capture.py` (1142 q.) + `discovery.py:170-205`.

| Element | Manba | Nima uchun |
|---|---|---|
| `_system_transaction()` | `discovery.py:170-205` | §S-5 — busiz job jimgina 0 qator ko'radi |
| Deterministik `request_id` | `discovery.py:265-269` | Bitta snapshot uchun barcha zona hodisalari **bir ipda** |
| `_DeviceContext` naqshi (ORM emas, oddiy qiymatlar) | `discovery.py:334-358` | Tranzaksiyadan keyin ORM obyektiga tegish `expire_on_commit` ga bog'lanardi |
| `_Finisher` — `failed` yozuvining YAGONA joyi | `discovery.py:559-622` | Uch xato yo'li uni baham ko'radi |
| «JOB JARAYONI HECH QACHON YIQILMAYDI» | `discovery.py:61-65, 323-331` | Navbat yiqilgan vazifani qayta yetkazishi mumkin |
| `_write_heartbeat()` — ALOHIDA, QISQA tranzaksiya, xato **yutiladi** | `app/jobs/capture.py:542+`, `alerting.py:1102-1124` | Yurak urishi `self_check` ga chiqadi; uning yiqilishi ishni to'xtata olmaydi |

**Xato ushlash zanjiri — verbatim:** `discovery.py:323-331`

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

**`error_detail` chegarasi — verbatim:** `discovery.py:160-171`

```python
_MAX_DETAIL_CHARS: Final[int] = 500
"""Job yozadigan `error_detail["raw"]` ning chegarasi. ..."""


def _raw(message: str) -> dict[str, Any]:
    """`error_detail` ning yagona shakli — `raw` kaliti (UI-SPEC §7.4 allowlist'i)."""
    return {"raw": message[:_MAX_DETAIL_CHARS]}
```

> **Idempotentlik — `ON CONFLICT DO NOTHING`, oldindan tekshirilmaydi**
> (falsafa manbai `nvr_repo.py:509-517`, §S-6 da verbatim).
> 🔴 **KADR OLISH BILAN BIR TRANZAKSIYADA BOG'LANMAYDI** (RESEARCH §E.13):
> `detect` **kadr saqlangandan keyin** navbatga qo'yiladi; enqueue naqshi
> `worker.py:678` (`asyncio.timeout(ENQUEUE_TIMEOUT_SECONDS)`) va u
> **tranzaksiyadan KEYIN** turadi (`04-PATTERNS.md` §3.3, 4-qadam).
> 🔴 **`quality_verdict <> 'ok'` kadr uchun task UMUMAN qo'yilmaydi** (§S-4).

---

### 3.5 `services/cv-service/app/services/storage.py` (FAQAT O'QISH)

**Analog:** `core-api/app/services/storage.py` (530 q.) — **to'liq shablon**,
lekin **yuza qisqaradi**.

**O'lchangan fakt 1–2 — verbatim:** `storage.py:37-62`

```
⛔ 3. XATO SIRSIZ — VA OQISH YO'LI O'LCHANGAN, FARAZ QILINMAGAN.

   O'lchov (2026-08-04, `aiobotocore 3.9.0` + SeaweedFS 4.40, yetib
   bo'lmaydigan manzilga `put_object`):

       EndpointConnectionError:
       Could not connect to the endpoint URL:
       "http://ombor-yoq.invalid:8333/sbozor-snapshots/<market>/<sana>/…jpg"

   Ya'ni `botocore` ning TARMOQ istisnolari to'liq manzilni — sxema, host,
   port, bucket VA obyekt kalitini — matnda tashiydi. ...

   Xuddi shu o'lchov IKKINCHI faktni ham berdi ...:
   `ClientError` ning matni (`SignatureDoesNotMatch`, `InvalidAccessKeyId`,
   `NoSuchKey`) manzilni ham, rekvizitni ham TASHIMAYDI. ...

   Shuning uchun `_failure()` FAQAT uch fakt beradi: amal + istisno turi +
   HTTP status. Va u `raise … from None` bilan ko'tariladi ...
```

**O'lchangan fakt 3 — `head` va `get` BOSHQA kod beradi — verbatim:** `storage.py:159-173`

```python
_ABSENT_ERROR_CODES = frozenset({"404", "NoSuchKey", "NotFound"})
...
    head_object(yo'q kalit)  -> Error.Code = "404"        (HTTP 404)
    get_object(yo'q kalit)   -> Error.Code = "NoSuchKey"  (HTTP 404)
...
olmaydi va uni status kodidan hosil qiladi — shuning uchun `"404"` va
`"NoSuchKey"` ikkalasi ham ro'yxatda. ...
⚠ `NoSuchBucket` BU RO'YXATDA ATAYIN YO'Q. U ham 404 beradi, lekin ma'nosi
```

**O'lchangan fakt 4 — `Quiet` rejimi:** `storage.py:360-365`

```python
    async def delete_many(self, keys: Sequence[str]) -> int:
        ...
        ⚠ `Quiet` REJIMI ISHLATILMAYDI VA BU O'LCHANGAN QAROR. `Quiet=True`
```

> **`cv-service` omboriga NIMA KIRADI:**
>
> | Metod | `cv-service` da | Sabab |
> |---|---|---|
> | `get(key)` | ✅ | RESEARCH §E.13: **S3 kaliti beriladi, baytlar emas** |
> | `put(key, data)` | ✅ **faqat dalil rasmi** | `PolygonZoneAnnotator` chiqishi |
> | `head` / `list_prefix` / `delete_many` | ⛔ **YOZILMAYDI** | `storage.py:11-22`: «metodning yo'qligi — kelishuv emas, STRUKTURA». Retention `core-api` da qoladi |
>
> 🔴 **REKVIZIT HAM TOR** (RESEARCH §E.13: faqat **o'qish** huquqi). Dalil
> rasmi uchun yozish kerak bo'lsa **alohida prefiks** oladi va bu
> `ops/seaweedfs/s3.json.example` da ko'rinadi (`anonymous` yo'qligini
> grep-darvoza allaqachon tekshiradi).
> ⚠ **KLIENT EGALIGI** (`storage.py:75-88`): worker jarayonida
> `WORKER_STARTUP` da bir marta ochiladi, `WORKER_SHUTDOWN` da yopiladi.
> `cv-service` — sof worker, ya'ni **faqat shu variant**.

---

### 3.6 `services/core-api/app/api/v1/camera_zones.py`

**Analog:** `app/api/v1/zones.py` (**nomdosh, boshqa domen** — §S-1) +
`tariffs.py` (versiyalash) + `stalls.py` (skelet).

**Qarorlar bloki — verbatim:** `app/api/v1/zones.py:1-30`

```
"""Zona reestri (D-03) — YASSI ro'yxat, ierarxiya YO'Q.

=============================================================================
O'QISH VA YOZISH HUQUQLARI ATAYIN AJRATILGAN (D-07).

`GET` — `MARKET_DATA_VIEW`, qolgan hammasi — `STALL_MANAGE`. Direktorda
birinchisi BOR, ikkinchisi YO'Q ...

CROSS-TENANT JAVOB — HAR DOIM 404 (T-02-55). Boshqa bozorning `zone_id` si
bilan kelgan har qanday amal RLS ostida 0 qator topadi va "topilmadi"
javobini oladi. 403 QAYTARILMAYDI: javobning O'ZI "bunday zona bor, lekin
sizniki emas" degan ma'lumotni oshkor qilardi ...
=============================================================================

`market_id` HECH QACHON SO'ROV TANASIDAN OLINMAYDI (T-02-54). U faqat
`_market_id(principal)` dan keladi va `ZoneRequest` da bunday maydon
umuman e'lon qilinmagan ...
```

**Alias bloki — verbatim:** `zones.py:50-53`

```python
router = APIRouter(tags=["zones"])

StallManagerDep = Annotated[Principal, Depends(require_permission(Permission.STALL_MANAGE))]
MarketDataViewerDep = Annotated[Principal, Depends(require_permission(Permission.MARKET_DATA_VIEW))]
```

**`UUID` ni `TYPE_CHECKING` ostiga qo'ymaslik — verbatim:** `zones.py:41-45`

```python
# `UUID` `if TYPE_CHECKING:` ostiga QO'YILMAYDI: FastAPI yo'l
# parametrlarining annotatsiyasini ISH PAYTIDA o'qiydi (`get_type_hints`),
# ya'ni import faqat tip tekshiruvida bo'lsa marshrut `NameError` bilan
# yiqilardi (`users.py:48` da ham aynan shu sababdan oddiy import).
```

> ⚠ **RBAC — YANGI `Permission` QO'SHILADIMI?** Standart javob: **yo'q** —
> `camera_zones` kameralarning davomi, ya'ni `CAMERA_MANAGE`/`CAMERA_VIEW`
> qayta ishlatiladi (`rbac.py:117-135`). **Nazoratchi navbati boshqacha**:
> `UserRole.INSPECTOR` (`enums.py:47`) mavjud va D-17 uni «yagona xolis
> o'lchov asbobi» ning egasi qiladi. Yangi `Permission` qo'shilsa,
> `rbac.py:20-27` bo'yicha **frontend ko'zgusi qo'lda** sinxronlanadi va
> `tests/unit/test_rbac_matrix.py` darvozasi ishlaydi.
> ⚠ **VERSIYALASH — `UPDATE` EMAS, YANGI QATOR** (D-07, RESEARCH §A.2):
> `is_active=false` + yangi `version`. Poligon o'zgarishi **o'tmishdagi
> dalilni qayta yozmaydi** — tariflarning tarixiyligi (MARKET-03) naqshi.
> ⚠ **`audit_read` KERAK EMAS** — jadval shaxsiy ma'lumot emas; nazorat
> holati `stalls.py:348-369` (`GET /map` da `audit_read` **ataylab yo'q**,
> sabab kodda). Jadval **o'zgarishi** DB-trigger orqali auditda (§S-1).
> ⚠ **MARSHRUT TARTIBI** (`stalls.py:3-11`): statik segment (`/coverage`,
> `/pending`) `{id}` shablonidan **OLDIN**.

**Serverdagi V5 validatsiyasi** (RESEARCH Security: «frontend tekshiruvi
takror, ishonch emas») — `app/services/zone_geometry.py` sof funksiyasi;
router uni chaqirib xato kodini `detail` ga aylantiradi (§S-8).

---

### 3.7 `services/core-api/app/api/v1/reviews.py`

**Analog:** `app/api/v1/snapshots.py` + `stalls.py:126-190`.
**Ko'r serializer uchun analog yo'q** (§4.8).

**«Metodning yo'qligi — STRUKTURA» (D-18) — verbatim:** `app/services/storage.py:11-22`

```
1. YUPQA QOBIQ, VA METODNING YO'QLIGI — KELISHUV EMAS, STRUKTURA.

   `create_bucket` va `delete_bucket` UMUMAN yozilmagan. ...

   Metod MAVJUD bo'lsa keyingi tahrirlovchi uni "qulaylik uchun" — masalan
   testni soddalashtirish uchun — chaqirardi ... `go2rtc.py:193-197` bilan
   aynan bir xil mulohaza: "metodning yo'qligi — kelishuv emas, STRUKTURA".
```

> 🔴 **D-18 shu tarzda amalga oshiriladi:** «hammasini tasdiqlash» endpointi
> **yozilmaydi**, va bu **API qoidasi, UI qoidasi emas** (RESEARCH §C.9).
> Darvoza — OpenAPI sxemasini skanerlaydigan test (§S-10): `zone_reviews`
> yaratadigan **massiv qabul qiluvchi** endpoint yo'qligi.

**Yashirin yuza — verbatim:** `app/api/internal/self_check.py:100-106`

```python
router = APIRouter(include_in_schema=False)
"""OpenAPI'ga CHIQMAYDI — `live_authz` bilan bir xil qaror va bir xil sabab.

Sxema MIJOZLAR uchun yoziladi, bu yerda esa mijoz yo'q ...
"""
```

> ⚠ **BU NAQSH KO'R AUDIT UCHUN ISHLATILMAYDI.** Ko'r audit endpointi
> **sxemada ko'rinadigan** oddiy endpoint — yashirish himoya emas. Himoya —
> **payloadda maydonning umuman yo'qligi** (§S-6.2) va uni **rekursiv
> skanerlaydigan** test o'lchaydi.

---

### 3.8 `tests/unit/test_license_fence.py` (D-03) — **birinchi migratsiyadan OLDIN**

**Analog:** `tests/unit/test_runtime_deps.py` (302 q.) — **to'liq shablon**.

**Nega manifest O'QILADI, import qilinmaydi — verbatim:** `test_runtime_deps.py:3-23`

```
=============================================================================
NEGA BU TEST BOR VA NEGA U BOSHQA HECH QAYERDA ISHLAMAYDI:

Bu sinfdagi xato **FAQAT DEPLOY PAYTIDA** ko'rinadi. `services/core-api/
Dockerfile` ikkita target quradi:

    dev      -> `uv sync --frozen`             (dev guruhi BILAN)
    runtime  -> `uv sync --frozen --no-dev`    (dev guruhi TUSHMAYDI)

Butun test to'plami `dev` target'da ishlaydi. ...

Shuning uchun darvoza **manifestning o'zini** o'qiydi, import qilib
ko'rmaydi: import bu konteynerda HAR DOIM muvaffaqiyatli bo'ladi va aynan
shu narsa muammoni yashiradi.
=============================================================================
```

**Nom normallashtirish — verbatim:** `test_runtime_deps.py:118-128`

```python
def _requirement_name(spec: str) -> str:
    """`redis[hiredis]==8.0.1` -> `redis`; `XlsxWriter==3.2.9` -> `xlsxwriter`.

    Nom PEP 503 bo'yicha normallashtiriladi (kichik harf, `_`/`.` -> `-`),
    aks holda `taskiq_redis` va `taskiq-redis` ikki xil paket bo'lib
    ko'rinardi va darvoza jimgina o'tkazib yuborardi.
    """
    head = spec.split(";", 1)[0].strip()
    for separator in ("==", ">=", "<=", "~=", "!=", ">", "<", "@"):
        head = head.split(separator, 1)[0]
    return head.split("[", 1)[0].strip().lower().replace("_", "-").replace(".", "-")
```

**Taqiqlangan paket — IKKALA guruhda ham yo'q — verbatim:** `test_runtime_deps.py:225-240`

```python
@pytest.mark.parametrize("package", sorted(FORBIDDEN_PACKAGES))
def test_forbidden_package_is_absent_from_both_groups(
    package: str, runtime_packages: set[str], dev_packages: set[str]
) -> None:
    """Taqiqlangan paket IKKALA guruhda ham yo'q (D-13/D-17, T-04-05).

    `dev` guruhi ham qamraladi va bu ATAYIN: `uv add --dev aioboto3`
    ham `uv.lock` ni qayta hal qiladi ... Guruh farqi bu
    to'qnashuvni umuman yumshatmaydi — lock bitta.
    """
```

**Nazorat holati — verbatim:** `test_runtime_deps.py:291-299`

```python
def test_manifest_actually_parsed(runtime_packages: set[str], dev_packages: set[str]) -> None:
    """Bo'sh to'plamda hamma assert jimgina o'tib ketardi.

    `_parse` yo'li noto'g'ri bo'lsa yoki TOML tuzilishi o'zgarsa,
    yuqoridagi "yo'q" testlari HAMMASI yashil qolardi — chunki bo'sh
    to'plamda hech nima yo'q. Bu quyi chegara shu yolg'on-yashilni yopadi.
    """
    assert len(runtime_packages) >= 20, f"prod bog'liqliklari juda kam: {sorted(runtime_packages)}"
```

> 🔴 **5-FAZA DARVOZASI IKKI QATLAMLI (D-03):**
>
> **(1) MANIFEST QATLAMI** — `test_runtime_deps.py` ning takrori, lekin
> `services/cv-service/pyproject.toml` uchun:
> * `REQUIRED_RUNTIME_PACKAGES = {"onnxruntime", "supervision",
>   "opencv-python-headless", "numpy", "aiobotocore", "taskiq",
>   "taskiq-redis", "fastapi"}`
> * `FORBIDDEN_PACKAGES = {"rfdetr", "rfdetr-plus", "torch", "torchvision",
>   "ultralytics", "aioboto3", "boto3", "minio"}` — **`rfdetr` ning O'ZI ham
>   taqiqlangan** (D-04: `torch` uning **majburiy** bog'liqligi, ~800 MB).
>
> **(2) LOCKFILE / METADATA QATLAMI — YANGI, ANALOGI YO'Q** (§4.10):
> * `services/cv-service/uv.lock` da `rfdetr-plus` **yo'q** (matn sifatida
>   o'qib — `test_sentry_processes.py:34-41` dagi «`PyYAML` bog'liqlik emas,
>   qo'lda parse qilinadi» qoidasiga rioya qilib);
> * **o'rnatilgan har bir distribution** metadata'sida `License-Expression`
>   / `Classifier: License` o'qilib, `LicenseRef-*` (OSI bo'lmagan) yoki
>   AGPL topilsa test **yiqiladi** — §S-10 ning «ro'yxat emas, predikat»
>   qoidasining aynan qo'llanishi (kelajakdagi noma'lum proprietar paketni
>   ham ushlaydi).
>
> ⚠ **QUYI CHEGARA MAJBURIY:** `importlib.metadata.distributions()` bo'sh
> qaytsa hamma assert jimgina o'tib ketardi → `assert len(dists) >= 30`.
> ⚠ **TEST BIRINCHI MIGRATSIYADAN OLDIN YOZILADI** (Wave 0): u
> `pyproject.toml` yozilgunicha qizil turadi va bu **KUTILGAN** —
> `schema_contract.py:140-148` dagi «reyestr migratsiyadan oldin yoziladi»
> qarorining takrori.

---

### 3.9 `frontend/src/lib/zone-geometry.ts` + `zone-geometry.test.tsx`

**Analog (SHAKL):** `src/components/cameras/camera-page-state.ts` +
`camera-page-state.test.tsx` — §S-13 da verbatim.
**Geometriyaning O'ZI uchun analog yo'q** (§4.2).

**Eksport yuzasi (RESEARCH §A.5 dan, to'liq):**

```
addVertex, moveVertex, deleteVertex, closePolygon, undo/redo,
normalize(px, w, h) / denormalize(norm, w, h),
isSelfIntersecting(polygon), polygonArea, centroid,
interpolateRow(first, last, n)     // A.4 dagi qator yordamchisi
```

> 🔴 **`isSelfIntersecting` E'TIBORDAN QOLDIRILMAYDI** (RESEARCH §A.5):
> «o'zi bilan kesishgan poligon `cv2.pointPolygonTest` da aniqlanmagan
> natija beradi. Uni **saqlash paytida rad etish** kerak.» Ya'ni u
> **frontendda ham, serverda ham** bor va **serverdagisi ishonch manbai**.
> ⚠ **AYLANMA YO'QOTISHSIZ:** `denormalize(normalize(p,w,h),w,h) == p` —
> `tests/unit/test_periods.py` va `test_rtsp_url.py` dagi aylanma
> testlarining aynan shakli.
> ⚠ Kutilgan natijalar **QO'LDA hisoblanadi va literal yoziladi** (§S-9).

---

### 3.10 `compose.yaml` (MOD) — `cv-service`

**Analog:** `compose.yaml:245-347` (`worker`). §S-11 ga qarang.

**Fayl boshidagi profil ro'yxati YANGILANADI** (u HUJJAT):

```yaml
#   (yo'q)   -> db, cache, storage, core-api, worker, scheduler, cv-service, go2rtc : `npm run up`
```

**`npm run up` yorlig'i ham yangilanadi** (`package.json:7`):

```json
    "up": "docker compose up -d db cache storage core-api worker scheduler go2rtc --wait",
```

---

### 3.11 Meros bandlar — D-26 va D-27

**D-27 — verbatim:** `scripts/check-validation-signoff.mjs:54-61` va `:317`

```js
const DEFAULT_FILE = path.join(
  import.meta.dirname,
  "..",
  ".planning",
  "phases",
  "02-bozor-domeni-va-yangi-bozor-ustasi",
  "02-VALIDATION.md",
);
...
const file = process.argv[2] ? path.resolve(process.argv[2]) : DEFAULT_FILE;
```

> **Tuzatish yo'nalishi:** `DEFAULT_FILE` fazadan **mustaqil** bo'lsin —
> `.planning/phases/` ni skanerlab **eng katta raqamli** faza papkasidagi
> `*-VALIDATION.md` ni olsin; topilmasa **`process.exit(1)`** (jimgina o'tib
> ketmasin — §S-10 ning «topilmadi = yiqilish» qoidasi). Argument berilgan
> holat o'zgarmaydi.

**D-26 — verbatim:** `package.json:22`

```json
    "gate": "npm run sim:up && npm run lint && npm run test && npm --prefix frontend run i18n:check && npm --prefix frontend test && npm --prefix frontend run typecheck && npm --prefix frontend run lint && npm --prefix frontend run build",
```

> **Byudjet qayta o'lchanadi va o'lchov sharti YOZILADI:** «tinch xostda,
> ikkinchi Docker steki ishlamayotgan holda, uch marta». 4-faza 900 s ni
> hujjatlashtirgan, o'lchov 1009–1174 s bergan — farqning bir qismi xost
> sekinlashuvi bo'lishi mumkin (D-26). Natija yangi raqam **va uning o'lchov
> sharoiti** bilan yoziladi. ⚠ Zanjirga `cv-service` build'i qo'shilishi
> byudjetni yana o'zgartiradi — o'lchov **`cv-service` qo'shilgandan keyin**
> qilinsin.

---

## 4. No Analog Found — **analog yo'q**

> Bu bo'lim ataylab batafsil: soxta analog ko'rsatish **admitted gap dan
> yomonroq**, chunki ijrochi unga ergashadi.

### 4.1 ONNX / har qanday ML runtime — **analog yo'q**

**O'lchov (2026-08-08, `onnx|rfdetr|supervision|torch|numpy|opencv|cv2`,
`-i`, `.md` dan tashqari barcha fayl):** ijro etiladigan koddagi natija —
**NOL**. Topilganlar faqat:

```
.gitattributes:31                       *.onnx    binary
services/core-api/app/services/quality.py:51-53   «`opencv` BU FAZADA YO'Q (D-13)»
services/core-api/pyproject.toml:92-93            «`opencv-python-headless` BU YERGA QO'SHILMAYDI»
tests/unit/test_runtime_deps.py:91-94             FORBIDDEN_PACKAGES ichida
services/core-api/Dockerfile:7                    «musl ostida ular manbadan qurilardi (onnxruntime, asyncpg…)»
```

Ya'ni loyihada **birorta ML runtime yo'q** va bu fazaning **birinchi
inference kodi**.

**Eng yaqin strukturaviy qo'shnilar:**

| Nima | Fayl | Nimasi o'xshash / nimasi boshqa |
|---|---|---|
| Og'ir tashqi resurs va uning umri | `app/worker.py:181-207` (`WORKER_STARTUP`/`WORKER_SHUTDOWN`) | ✅ Sessiya bir marta ochiladi, `shutdown` da yopiladi. ❌ ONNX sessiyasi **jarayon-lokal**, tarmoq resursi emas |
| Sozlamani startup'da tekshirish | `app/settings.py` `field_validator` | ✅ Model fayli yo'q bo'lsa **ishga tushishda** yiqilsin, birinchi kadrda emas |
| «Musl'da g'ildirak yo'q» | `services/core-api/Dockerfile:7` | ✅ Debian-slim baza majburiy — `onnxruntime` manylinux_2_28 |

**Nima o'ylab topiladi:** `onnxruntime.InferenceSession` qurish,
`sess_options.intra_op_num_threads`, `providers=["CPUExecutionProvider"]`
(ATAYIN yoziladi), `session.get_inputs()[0].shape[2:4]` dan rezolyutsiyani
**o'qib olish** (qattiq yozib qo'yish emas — RESEARCH §B.2). Bularning
hammasi RESEARCH §B.2/§B.3 da spetsifikatsiyalangan.

> 🔴 **`.gitattributes:31` DA `*.onnx binary` ALLAQACHON BOR** — artefaktni
> repoda saqlash oldindan ko'zda tutilgan, ya'ni D-24 («build paytida
> `COPY`») repo darajasida qarshilikka uchramaydi.

---

### 4.2 `supervision` / poligon geometriyasi — **analog yo'q**

**O'lchov (2026-08-08, `polygon`, `-i`, `.md` dan tashqari):** **NOL
natija.** Loyihada birorta geometrik hisob yo'q — na frontendda, na
backendda.

**Eng yaqin strukturaviy qo'shnilar:**

| Nima | Fayl | Nimasi ko'chiriladi |
|---|---|---|
| Sof funksiya moduli | `app/services/quality.py:1-6`, `live_source.py:1-5` | Modul shakli, xato kodi konstantalari, `Settings` ni bilmaslik |
| Baytdan o'lchov + verdikt | `app/services/quality.py` (Pillow) | «Dekodla → o'lcha → verdikt» **oqimi**; geometriya emas |
| Frontend sof mantiq | `src/components/cameras/camera-page-state.ts` | Modulni sahifadan ajratish sababi va test kengaytmasi (§S-13) |
| Fixture nomlash | `tests/fixtures/frames.py:1-80` | Fizik/geometrik fakt bilan nomlash (§S-9) |

**Nima o'ylab topiladi:** `sv.PolygonZone(polygon, triggering_anchors=...)`,
`zone.trigger(detections)`, `PolygonZoneAnnotator(...).annotate(scene, label)`,
0..1 ↔ piksel konversiyasi, `isSelfIntersecting`, `interpolateRow`,
`polygonArea`, `centroid`.

> 🔴 **QO'LDA YOZILMAYDIGAN NARSALAR (RESEARCH §B.4):** nuqta-poligon ichida
> testi (`cv2.pointPolygonTest` ustidagi mantiq), zona hisoblagichi,
> annotator. Hammasi `supervision` da bor va MIT.
> 🔴 **RASMIY MISOL `ultralytics` ISHLATADI** (RESEARCH §B.4, Tuzoq 3) —
> **AGPL, TAQIQLANGAN**. Misolni ko'chirib olish AGPL paketni
> `pyproject.toml` ga olib kirardi; §3.8 darvozasi aynan shuni ushlaydi.
> 🔴 **`PolygonZone` PIKSEL KUTADI, biz 0..1 saqlaymiz** (Tuzoq 1) —
> konversiya **sof funksiya** bo'lib ajratiladi va real kadrsiz to'liq
> testlanadi.
> ⚠ **`triggering_anchors` SOZLAMA** (D-09): standart
> `(Position.CENTER, Position.BOTTOM_CENTER)`. Bu 4-fazaning `light_mode`
> bilan bir xil naqsh — mexanizm quriladi va o'lchanadi, QIYMAT keyin
> sozlanadi.

---

### 4.3 Xom tenzor arifmetikasi — **analog yo'q**

Eksport qilingan RF-DETR grafi **xom tenzor** qaytaradi (RESEARCH §B.2,
rasmiy hujjatdan): sigmoid → background ustunini olib tashlash → `cxcywh`
(normalangan) → `xyxy` (piksel) → confidence filtri.

**Eng yaqin qo'shni:** `tests/unit/test_quality_filter.py` — «kirish
sintetik, kutilgan natija literal» shakli. Arifmetikaning O'ZI yangi.

> 🔴 **BACKGROUND USTUNINI NOTO'G'RI OLIB TASHLASH JIMGINA NOTO'G'RI JAVOB
> BERADI** (RESEARCH §B.2): istisno tashlanmaydi, faqat «odam» o'rniga
> «boshqa narsa» chiqadi. Shuning uchun bu **alohida birlik test bilan
> qoplanishi SHART** — kirishi qo'lda yasalgan tenzor, kutilgan chiqishi
> **qo'lda hisoblangan** quti. Bu «model to'g'rimi» emas, «arifmetika
> to'g'rimi» degan savol, ya'ni **real kadrsiz to'liq isbotlanadi**.
> ⚠ `rfdetr` ning o'z post-processing kodi **ishlatilmaydi** — u `torch`
> talab qiladi (D-04).

---

### 4.4 Ikkinchi Python servisi (`pyproject.toml` + `Dockerfile` + `uv.lock`) — **analog yo'q**

**O'lchov (2026-08-08):** `ls services/*/Dockerfile` → **bitta natija**
(`services/core-api/Dockerfile`). `services/nvr-sim/` da `pyproject.toml`
**yo'q** — u `core-api` image'ining `dev` target'ini qayta ishlatadi
(`compose.yaml:491-503`).

**Eng yaqin strukturaviy qo'shni:** `services/core-api/pyproject.toml` —
undan ko'chiriladigan narsa: `[tool.uv.sources]` bandi (`:128-129`),
`[dependency-groups] dev` ajratmasi, ruff/mypy konfiguratsiyasi,
`Dockerfile` ning `dev`/`runtime` ikki target'i.

**Nima o'ylab topiladi:** ikkinchi `uv.lock` ni CI'da tekshirish,
`cv-service` uchun `npm run lint` / `npm run test` zanjiriga qo'shilish
(root `package.json` yorliqlari `--prefix` siz `docker compose … tests`
konteyneriga tayanadi — yangi servis kodini kim lint qiladi degan savol
ochiq va reja unga javob berishi kerak).

> ⚠ **`tests` KONTEYNERI `core-api` IMAGE'IDA ISHLAYDI.** `cv-service`
> kodining testlari qayerda yuradi — reja aniq qaror qilsin. Ikki variant:
> (a) `cv-service` testlari `services/cv-service/tests/` da va o'z
> konteynerida; (b) `cv-service` ning **sof** qismlari (`postprocess`,
> `zones`) `packages/sbozor-core` ga chiqariladi va mavjud `tests/unit` da
> sinaladi. **(b) arzonroq** va §S-8 bilan mos, lekin `supervision` ni
> `sbozor-core` ga olib kirardi — bu `core-api` image'ini ham kattalashtiradi.
> Qaror **Wave 0 da** qilinsin, chunki u `pyproject.toml` larning shaklini
> belgilaydi.

---

### 4.5 Statistik hisobot (chalkashlik matritsasi + Wilson) — **analog yo'q**

Loyihada statistika yo'q. Eng yaqin qo'shni —
`packages/sbozor-core/sbozor_core/money.py` + `tests/unit/test_money.py`:
sof arifmetika, `int` semantikasi, chetki holatlar to'liq sanab chiqilgan.
Undan ko'chiriladigan narsa — **shakl va test uslubi**, formulalar emas.

**Nima o'ylab topiladi:** Wilson score oralig'i, chalkashlik matritsasi,
bazaviy bandlik ulushi. Hammasi RESEARCH §C.8.4 da.

> 🔴 **«ANIQLIK» YOLG'IZ KO'RSATKICH SIFATIDA E'LON QILINMAYDI** (§C.8.4):
> rastalarning 90% i band bo'lsa, «har doim band» deydigan soxta model 90%
> oladi. Hisobot **chalkashlik matritsasi** bo'lishi shart va ikki xato
> **teng emas**: «band deb xato» → **nizo**, «bo'sh deb xato» → **yo'qotish**.
> Ikkalasi alohida, har biri Wilson oralig'i bilan.
> 🔴 **HISOBOT FAQAT `purpose='eval'` QATORLARDAN** (D-14) — `train` qatorlar
> hisobga kirmaydi va bu **alohida test** bilan o'lchanadi.
> ⚠ Kutilgan qiymatlar **qo'lda hisoblanadi va literal yoziladi** (§S-9) —
> `scipy` qo'shilmaydi.

---

### 4.6 Qayta chiqariladigan tasodifiy namuna — **analog yo'q**

**O'lchov:** `setseed|random\(\)|digest\(|sha256` — SQL kontekstida **nol**
natija (`digest` faqat `services/nvr-sim/sim/digest.py` — HTTP Digest
autentifikatsiyasi, butunlay boshqa narsa).

**Eng yaqin strukturaviy qo'shni:** `tests/fixtures/frames.py:102-103`
(`_SEED: Final = 20260804` — «Qiymatning O'ZI ahamiyatsiz — QADALGANLIGI
ahamiyatli») va `tests/fixtures/karmana_seed.py` (determinizm sababi izohda,
generator CLI sifatida ham chaqiriladi).

**Nima o'ylab topiladi:** hosila urug' formulasi, `ORDER BY hash LIMIT n`,
doirani muzlatish (`frame_size`, `frame_predicate_hash`, `drawn_at`),
qayta hisoblash testi.

> 🔴 **`ORDER BY random() LIMIT n` YARAMAYDI** (§C.8.1) — qayta
> chiqarilmaydi. **`setseed()` bilan seed saqlash ham yetarli emas** — seedni
> tanlagan odam uni bir necha marta sinab ko'rishi mumkin.
> 🔴 **M-1: `digest()` MAVJUD EMAS** — §3.1 dagi uch yo'ldan biri tanlanadi.
> ⚠ **DOIRA `uncertain` LARNI HAM O'Z ICHIGA OLADI** (§C.8.3): «Faqat
> ishonchli javoblarni tekshiraylik» degan qisqartma o'lchovni ma'nosiz
> qiladi.

---

### 4.7 «Oltin to'plam» harness'i — **analog yo'q**

Uxlab yotadigan darvoza (`source='karmana'` qatorlar paydo bo'lgan kuni
**kodsiz o'zi uyg'onadi**) — loyihada bunday naqsh yo'q.

**Eng yaqin strukturaviy qo'shnilar:**

| Nima | Fayl | Nimasi o'xshash |
|---|---|---|
| «Jadval mavjud bo'lsa — konstrayt ham shart» | `schema_contract.py:88-94` (`FINANCIAL_TABLES` falsafasi) | ✅ **Aynan shu mexanizm**: reyestr bugun bo'sh, darvoza kelajakda avtomatik yopiladi |
| Manifest + generator CLI | `tests/fixtures/karmana_seed.py` (`npm run karmana:sample`) | ✅ CLI shakli, determinizm izohi |
| `backup` komponenti hozir `never_seen` da | `self_check.py:123-126` | ✅ «Uni ro'yxatdan olib turish "keyin qo'shamiz" qarziga aylanardi» |

**`FINANCIAL_TABLES` falsafasi — verbatim:** `schema_contract.py:88-94`

```
1-fazada bu jadvallarning HECH BIRI hali mavjud emas (ular 2- va 6-fazalarda
tug'iladi). Reyestr shunga qaramay hozir yoziladi, chunki meta-test uni
"jadval mavjud bo'lsa — quyidagi konstraytlar ham bo'lishi shart" shaklida
ishlatadi: shunda 6-fazada `payments` yaratilgan kuni darvoza avtomatik
yopiladi va hech kim `UNIQUE(market_id, idempotency_key)` ni unutib
qo'ymaydi.
```

> **Bu — oltin to'plam darvozasining AYNAN falsafasi** (D-02): mexanizm
> hozir quriladi, `source='karmana'` qatorlar kelgan kuni **kod
> o'zgarmasdan** aktivlashadi.
> 🔴 **SINTETIK YOZUVLAR `true_verdict` NI FAQAT GEOMETRIYADAN OLADI**
> (RESEARCH §Validation): «bu poligon ichida shu koordinatalarda quti bor» —
> **detektorning javobidan emas**, aks holda o'zini-o'zi tasdiqlash tuzog'i
> qaytadi.
> ⚠ **YANGI `golden` MARKERI** kerak (RESEARCH Test Framework) va u
> `pyproject.toml` `markers` ga **oldindan** e'lon qilinadi —
> `--strict-markers` ostida e'lon qilinmagan marker **yig'ilishda** yiqiladi
> (`test_runtime_deps.py:262-283` o'lchagan).

---

### 4.8 Ko'r serializer (maydonning umuman yo'qligi) — **qisman analog**

Loyihada «bu yuza ATAYIN yo'q» qarori bor (`storage.py:11-22`,
`go2rtc.py:193-197`, `self_check.py:100-106`), lekin **bitta modeldan ikki
xil javob shakli** chiqaradigan serializer **yo'q**.

**Nima o'ylab topiladi:** `queue_kind` ga qarab boshqa `response_model`,
va uni o'lchaydigan **rekursiv kalit skani**.

> 🔴 **`None` QILIB YUBORISH YETARLI EMAS** (D-17, §C.8.2): kalitning O'ZI
> bo'lmasligi kerak. Test javobni **rekursiv skanerlab** taqiqlangan
> kalitlar (`verdict`, `confidence`, `model_version`) yo'qligini tasdiqlaydi
> — 4-fazadagi «alertga kadr rasmi biriktirilmaydi» testining aynan shakli.

---

### 4.9 «O'zgarmas AI qiymati + alohida inson qatori» — **qisman analog**

Ikkala komponent alohida mavjud (§S-3: shartsiz trigger; hisoblanadigan
`COALESCE`), lekin **birga hech qachon ishlatilmagan**.

**Eng yaqin strukturaviy qo'shni:** `tariffs` + `stall_category_periods`
juftligi — qiymat **tahrirlanmaydi**, yangi davr **qo'shiladi**, amaldagi
qiymat sanadan **hisoblanadi**. Farqi: u yerda ikkala qator ham bir xil
manbadan (odam), bu yerda esa **AI va odam ikki xil manba** va ular ikki
**alohida jadvalda** yashaydi.

**Nima o'ylab topiladi:** `effective_verdict` ko'rinishi va uning
`resolution_source` i (RESEARCH §C.10):

```
effective_verdict, resolution_source =
    review mavjud       -> (review.human_verdict, 'human')
    verdict='uncertain' -> ('empty',              'default_empty')
    aks holda           -> (event.verdict,        'ai')
```

> 🔴 **AI-06 HISOBLANADI, YOZILMAYDI** (D-19, §C.10): `zone_reviews` ga
> **soxta qator yozilmaydi** — aks holda tizim «nazoratchi buni bo'sh deb
> tasdiqladi» deb yolg'on gapirardi va o'sha yolg'on keyin trening
> datasetiga tushardi.
> 🔴 **XAVF YO'NALISHI:** standart «bo'sh» → **jimgina yo'qotish**, ortiqcha
> hisob emas. Shuning uchun chora — «billing'ga kirib ketmasin» emas,
> **«ko'rinmay qolmasin»**: kunlik hisobotda «N ta zona ko'rilmagani uchun
> bo'sh deb hisoblandi» raqami **nol bo'lsa ham** ko'rsatiladi (4-fazadagi
> «yo'qlikka alert» prinsipining takrori).

---

### 4.10 Litsenziya-metadata darvozasi — **qisman analog**

`test_runtime_deps.py` **manifestni** o'qiydi; **o'rnatilgan
distribution'larning metadata'sini** o'qiydigan test **yo'q**.

**Eng yaqin qo'shnilar:** `test_runtime_deps.py` (manifest o'qish + nom
normallashtirish + quyi chegara) va `test_sentry_processes.py` (predikat
asosidagi kashfiyot + `pytest.fail` on unknown).

**Nima o'ylab topiladi:** `importlib.metadata.distributions()` bo'ylab
yurish, `License-Expression` / `Classifier: License ::` o'qish, `LicenseRef-*`
va AGPL predikatlari, `uv.lock` ni matn sifatida skanerlash.

---

## 5. Wave 0 — birinchi migratsiyadan OLDIN bajariladigan ishlar

| # | Ish | Fayl | Sabab / manba |
|---|---|---|---|
| **W0-1** | `tests/unit/test_license_fence.py` — `rfdetr-plus` / `LicenseRef-*` / AGPL darvozasi | yangi (shablon: `tests/unit/test_runtime_deps.py`) | **D-03.** Litsenziya endi lockfile invarianti. Keyin qo'shilsa `uv add rfdetr` allaqachon `torch` ni tortgan bo'lardi (§3.8, §4.10) |
| **W0-2** | `cv-service` testlari qayerda yuradi — **qaror** | `services/cv-service/pyproject.toml` shakli | §4.4: `tests` konteyneri `core-api` image'ida ishlaydi. Qaror `pyproject.toml` larning shaklini belgilaydi, ya'ni keyin o'zgartirish qimmat |
| **W0-3** | M-1 qarori: `sha256(bytea)` / `pgcrypto` / Python | `0018` sarlavhasi, `audit_rounds` docstringi | RESEARCH §C.8.1 ning SQL'i **bugun ishlamaydi**. Migratsiyadan keyin aniqlash qayta migratsiya demakdir |
| **W0-4** | `OCCUPANCY_TENANT_TABLES` + `_AUDITED_` + `_DELETE_ORDER` reyestrlari | `migrations/entities/__init__.py` | §S-1/§S-2. `schema_contract.py:140-148`: reyestr **migratsiyadan oldin** yoziladi, meta-test vaqtincha qizil turadi — bu KUTILGAN |
| **W0-5** | `AUDITED_TABLES` ga `camera_zones`, `zone_reviews` | `schema_contract.py` | W0-4 bilan bir xil sabab |
| **W0-6** | `market_delete_draft()` kaskadini oltita yangi jadval bilan kengaytirish + `0019` | `migrations/entities/functions.py` | §S-2. `0012`→`0013` va `0014`→`0015` juftligining **uchinchi takrori** |
| **W0-7** | `tests/fixtures/detections.py` — `sv.Detections` konstruktori, **geometrik fakt bo'yicha** nomlangan | yangi | §S-9. Usiz butun zona mantig'i darvoza emas, konventsiya bo'lib qolardi |
| **W0-8** | `frontend/src/lib/zone-geometry.ts` + `zone-geometry.test.tsx` (⚠ `.tsx`) | yangi | §S-13 / M-2. `.ts` test JIMGINA yig'ilmaydi |
| **W0-9** | `tests/fixtures/golden_set/` skeleti + `manifest.jsonl` sxemasi + `scripts/eval-golden-set.py` (uxlab yotadigan darvoza) | yangi | §4.7. Faza mahsuloti — **mashina**, raqam emas (D-01) |
| **W0-10** | `golden` pytest markerini `pyproject.toml` ga e'lon qilish | `pyproject.toml` | `--strict-markers` ostida e'lon qilinmagan marker **yig'ilishda** yiqiladi (`test_runtime_deps.py:262-283`) |
| **W0-11** | `compose.yaml` ga `cv-service` + `self_check.EXPECTED_COMPONENTS` ga `cv_detect` | `compose.yaml`, `app/api/internal/self_check.py:108-126` | §S-10(b) va §S-11. `SENTRY_DSN` berilishi bilan `test_sentry_processes.py` avtomatik talab qo'yadi |
| **W0-12** | ONNX artefaktini image'ga olib kirish yo'li (`COPY`, yuklab olish emas) | `services/cv-service/Dockerfile`, `ops/models/` | **D-24.** `.gitattributes:31` da `*.onnx binary` allaqachon bor |
| **W0-13** | ⚠ `npm run gate` byudjetini **tinch xostda uch marta** o'lchash va 900 s ni qayta belgilash | `package.json`, `05-VALIDATION.md` | **D-26** (`04-VERIFICATION` open_item). O'lchov `cv-service` build'i qo'shilgandan **keyin** |
| **W0-14** | ⚠ `scripts/check-validation-signoff.mjs::DEFAULT_FILE` ni fazadan mustaqil qilish | `scripts/check-validation-signoff.mjs:54-61` | **D-27** (`04-VERIFICATION` open_item). Topilmasa `exit 1` — §S-10 |

---

## Metadata

**Analog qidiruv qamrovi:**
`services/core-api/app/**` · `services/nvr-sim/**` · `packages/sbozor-core/**` ·
`migrations/**` · `tests/**` · `frontend/src/**` · `frontend/scripts/**` ·
`compose.yaml` · `ops/**` · `scripts/**` · `package.json` · `pyproject.toml` ·
`.gitattributes` · `.env.example`

**Skanerlangan fayllar:** ~510 (git tracked); to'liq o'qilgan: 6;
nishonli o'qilgan: 21; grep bilan tekshirilgan: 9 ta o'lchov.

**Empirik o'lchovlar (2026-08-08 — bu hujjatning «analog yo'q» da'volari shulardan keladi):**

| Da'vo | Buyruq / manba | Natija |
|---|---|---|
| ML runtime yo'q | `grep -i "onnx\|rfdetr\|supervision\|torch\|numpy\|opencv\|cv2"` (`.md` dan tashqari) | Ijro etiladigan kodda **0**; faqat `.gitattributes:31` va **taqiq izohlari** |
| Poligon geometriyasi yo'q | `grep -i "polygon"` (`.md` dan tashqari) | **0 natija** |
| `pgcrypto` o'rnatilmagan | `ops/db/init/00-extensions.sql` to'liq o'qildi | Faqat `CREATE EXTENSION IF NOT EXISTS btree_gist;` → **M-1** |
| Ikkinchi Python servisi yo'q | `ls services/*/Dockerfile`; `services/nvr-sim/` tarkibi | **1 ta Dockerfile**; `nvr-sim` da `pyproject.toml` yo'q → §4.4 |
| `vitest` faqat `.tsx` yig'adi | `frontend/vitest.config.ts:34` | `include: ["src/**/*.test.tsx"]` → **M-2** |
| `node --test` TS import qila olmaydi | `frontend/package.json:14`; `frontend/scripts/*.test.mjs` importlari | 9 testdan 1 tasi modul import qiladi (`.mjs`), 8 tasi matn o'qiydi → **M-3** |
| Billing langari mavjud va **o'lchangan** | `models/snapshot.py:639-699`; `tests/fixtures/billable_probe.py` o'qildi | **Tasdiqlandi** — `BILLABLE_ANCHOR_SUPPORTED = true`, ikkala yo'nalish |
| `zones` nomi band | `models/market.py:295-305`; `app/api/v1/zones.py`; `components/zones/` | **Tasdiqlandi** → `camera_zones` (D-06) |
| Shartsiz o'zgarmaslik triggeri mavjud | `migrations/entities/triggers.py:131-146`; `helpers.py:269-309` | **Tasdiqlandi** — `AUDIT_IMMUTABLE` + `attach_immutability_trigger()` |
| `SECURITY DEFINER` bozor ro'yxati naqshi mavjud | `migrations/entities/functions.py:1424-1455`; `test_snapshot_domain_meta.py:573` | **Tasdiqlandi** — `capture_due_markets()` |
| `INSPECTOR` roli mavjud | `packages/sbozor-core/sbozor_core/enums.py:47` | **Tasdiqlandi** — yangi rol kerak emas |

**Pattern extraction date:** 2026-08-08
