# Phase 8: Hisobotlar, mustahkamlash va ishga tushirish — Pattern Map

**Mapped:** 2026-08-13
**Files analyzed:** 38 (23 yangi · 15 o'zgartiriladigan)
**Analogs found:** 34 / 38 (aniq moslik 21 · rol-moslik 13 · analogsiz 4)

> ⛔ **Bu faza deyarli yangi naqsh tug'dirmaydi.** Har yangi fayl uchun repo'da
> AYNI rol + AYNI ma'lumot oqimidagi analog bor. Rejalarda «shu naqshda
> yozing» emas, **«shu fayl, shu qatorlardan ko'chiring»** deb yozilsin.

---

## File Classification

### Backend — core-api

| Yangi/O'zgaruvchi fayl | Rol | Ma'lumot oqimi | Eng yaqin analog | Moslik |
|---|---|---|---|---|
| `services/core-api/app/api/v1/reports.py` **(YANGI)** | controller | request-response (JSON) | `services/core-api/app/api/v1/billing.py` | exact |
| ⤷ `.xlsx` eksport marshrutlari (o'sha faylda) | controller | streaming / binary | `services/core-api/app/api/v1/imports.py:213-244, 629-643` | exact |
| ⤷ `POST /reports/three-way/ledger` (o'sha faylda) | controller | file-I/O (upload) | `services/core-api/app/api/v1/imports.py:327-461` | exact |
| `services/core-api/app/repositories/report_repo.py` **(YANGI)** | repository | batch / derived aggregation | `services/core-api/app/repositories/billing_repo.py:949-1057` | exact |
| `services/core-api/app/services/xlsx_export.py` **(YANGI)** | service (pure transform) | transform → bytes | `services/core-api/app/services/xlsx_template.py:282-315, 469-484` + `tests/fixtures/karmana_seed.py:679-703` | exact (ikki manbadan birlashtiriladi) |
| `services/core-api/app/services/xlsx_template.py` **(MOD)** | service | transform | o'zi (`TEMPLATE_KINDS:75-83`) | self |
| `services/core-api/app/services/import_validator.py` **(MOD)** | service (validator) | transform | o'zi (`validate_staff_rows` naqshi) | self |
| `services/core-api/app/api/v1/imports.py` **(MOD)** | controller | file-I/O | o'zi (`ImportKind:128`, `_TEMPLATE_PERMISSIONS:136`) | self |
| `services/core-api/app/settings.py` **(MOD)** | config | — | o'zi (`import_max_*:82-100`) | self |
| `services/core-api/app/schemas.py` **(MOD)** | model (DTO) | — | o'zi (`ChargeListResponse`, `OccupancyAccuracyResponse`) | self |
| `services/core-api/app/main.py` **(MOD)** | config (router wiring) | — | o'zi (`main.py:453` — `reconciliation_router`) | self |

### Migratsiyalar va sxema kontrakti

| Yangi/O'zgaruvchi fayl | Rol | Ma'lumot oqimi | Eng yaqin analog | Moslik |
|---|---|---|---|---|
| `migrations/versions/0024_ledger_entries.py` **(YANGI)** | migration | DDL | `migrations/versions/0023_notification_domain.py:330-378, 640-664` | exact |
| `migrations/versions/0025_notification_settings_id.py` **(YANGI)** | migration | DDL (ALTER + PK ko'chirish) | `migrations/versions/0023_notification_domain.py:541-568` (nishon jadval ta'rifi) | role-match |
| `packages/sbozor-core/sbozor_core/schema_contract.py` **(MOD)** | config (registry) | — | o'zi (`AUDITED_TABLES:170`) | self |
| `migrations/entities/__init__.py` **(MOD)** | config (registry) | — | o'zi (`NOTIFICATION_TENANT_TABLES` naqshi) | self |

### Ops / infra

| Yangi/O'zgaruvchi fayl | Rol | Ma'lumot oqimi | Eng yaqin analog | Moslik |
|---|---|---|---|---|
| `ops/backup/Dockerfile` **(YANGI)** | config (image) | — | `services/core-api/Dockerfile:1-14` (`COPY --from=<pinned image>` naqshi) | role-match |
| `ops/backup/run-backup.sh` **(YANGI)** | utility (shell) | batch / file-I/O | `ops/scripts/verify-tunnel.sh:1-87` | role-match |
| `ops/backup/loop.sh` **(YANGI)** | scheduler (daemon loop) | event-driven (poll) | ⛔ **analog yo'q** — `app/jobs/capture.py` idempotentlik qarori kontseptual manba | none |
| `ops/backup/heartbeat.sql` **(YANGI)** | migration-like (raw SQL) | CRUD (upsert) | `services/core-api/app/repositories/binding_repo.py:540-548` (`ON CONFLICT DO UPDATE`) | role-match |
| `ops/backup/README.md` **(YANGI)** | doc | — | `ops/seaweedfs/README.md` (compose'dan havola qilingan) | role-match |
| `ops/docs/go-live.md` **(YANGI)** | doc (runbook) | — | `ops/docs/monitoring.md:1-90` | exact |
| `compose.yaml` **(MOD)** | config | — | o'zi (`storage:` bloki 55-120) | self |
| `.env.example` **(MOD)** | config | — | o'zi (1-40) | self |

### Frontend

| Yangi/O'zgaruvchi fayl | Rol | Ma'lumot oqimi | Eng yaqin analog | Moslik |
|---|---|---|---|---|
| `frontend/src/app/[locale]/(app)/reports/page.tsx` **(YANGI)** | page (route) | request-response | `frontend/src/app/[locale]/(app)/reconciliation/page.tsx:81-171` | exact |
| `frontend/src/app/[locale]/(app)/reports/page.test.tsx` **(YANGI)** | test | — | `frontend/src/components/reconciliation/page.test.tsx` | exact |
| `frontend/src/components/reports/period-picker.tsx` **(YANGI)** | component (control) | URL state (nuqs) | `frontend/src/components/billing/day-picker.tsx:62-170` | role-match (kun → davr) |
| `frontend/src/components/reports/accuracy-view.tsx` **(YANGI)** | component | request-response | `frontend/src/components/reconciliation/hit-rate-card.tsx:66-168` | exact |
| `frontend/src/components/reports/{revenue,receivables,discrepancies}-view.tsx` **(YANGI)** | component (list) | request-response | `frontend/src/components/reconciliation/unpaid-list.tsx` | exact |
| `frontend/src/lib/report-queries.ts` **(YANGI)** | store (server state) | request-response | `frontend/src/lib/occupancy-queries.ts:1-212` | exact |
| `frontend/src/lib/api-types.ts` **(MOD)** | model (zod) | — | o'zi (`accuracyReportSchema`) | self |
| `frontend/src/components/shell/app-shell.tsx` **(MOD)** | component (nav) | — | o'zi (`NavItem` 59-97) | self |
| `frontend/messages/uz-Latn.json` **(MOD)** + `ru.json` + `uz-Cyrl.overrides.json` | config (i18n) | — | o'zi + `frontend/scripts/gen-cyrillic.mjs` | self |

### Testlar

| Yangi/O'zgaruvchi fayl | Rol | Ma'lumot oqimi | Eng yaqin analog | Moslik |
|---|---|---|---|---|
| `tests/integration/test_reports_api.py` **(YANGI)** | test (integration) | request-response | `tests/integration/test_reconciliation_api.py` | exact |
| `tests/integration/test_three_way.py` **(YANGI)** | test (integration) | file-I/O + aggregation | `tests/integration/test_staff_import.py` | exact |
| `tests/integration/test_backup_heartbeat.py` **(YANGI)** | test (integration) | event-driven | `tests/integration/test_alerting.py` | exact |
| `tests/integration/test_restore_drill.py` **(YANGI)** | test (integration, slow) | batch / container | `tests/conftest.py` (testcontainers boot) | role-match |
| `tests/integration/test_phase8_criteria.py` **(YANGI)** | test (criteria) | — | `tests/integration/test_phase7_criteria.py:1-60, 1650-1690` | exact |
| `tests/unit/test_xlsx_export.py` **(YANGI)** | test (unit) | transform | `tests/unit/test_xlsx_template.py` + `tests/unit/test_karmana_seed.py` | exact |
| `tests/unit/test_backup_contract.py` **(YANGI)** | test (unit, static scan) | file scan | `tests/unit/test_compose_sim_env.py:1-60` | exact |
| `tests/tenancy/test_personal_data_coverage.py` **(MOD)** | test (gate) | — | o'zi (115-165, 463-583) | self |
| `tests/unit/test_xlsx_template.py` **(MOD)** | test | — | o'zi (`test_template_kinds_are_exactly_three` ≈843) | self |
| `frontend/src/components/snapshots/alert-list.test.tsx` **(MOD)** | test (component) | — | o'zi | self |

---

## Pattern Assignments

### 1. `app/api/v1/reports.py` (controller · request-response + binary)

**Analog:** `services/core-api/app/api/v1/billing.py` (JSON + huquq imzo) va
`services/core-api/app/api/v1/imports.py` (bayt javob + upload).

**Modul boshi va importlar** (`billing.py:53-92`):

```python
from __future__ import annotations

from datetime import date, timedelta
from typing import Annotated
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sbozor_core.timeutil import business_today

from app.deps import Principal, TenantSessionDep, require_permission
from app.repositories import billing_repo
from app.schemas import (...)
from app.security.rbac import Permission

# ⚠ `date` VA `UUID` ISH VAQTIDA IMPORT QILINADI, `TYPE_CHECKING` OSTIDA
#   EMAS — `from __future__ import annotations` ostida annotatsiyalar SATR
#   bo'lib qoladi va FastAPI ularni Pydantic uchun YECHA olmaydi.

log = structlog.get_logger(__name__)
__all__ = ["router"]
router = APIRouter(tags=["billing"])
```

⛔ `reports.py` shu shaklni AYNAN takrorlaydi (`tags=["reports"]`), va
`date`/`UUID` ish vaqtida import qilinadi — aks holda OpenAPI meta-testi
`PydanticUserError` bilan yiqiladi.

**Huquq imzoda, dekoratorda emas** (`billing.py:109-112`, `occupancy.py:83-84`):

```python
ReportViewerDep = Annotated[Principal, Depends(require_permission(Permission.REPORT_VIEW))]
"""⛔ `BILLING_COLLECT_VIEW` EMAS. Yozilgan hisob, tuzatish va anomaliya —
DIREKTORNING yuzasi; kassir ularni ko'rmaydi (§5.6)."""
```

⛔ R-1: `REPORT_VIEW` **QAYTA ISHLATILADI**, yangi huquq YOZILMAYDI —
`rbac.py` ↔ `rbac.ts` ↔ `role-gate.test.mjs` uchligi o'smaydi.

**Audit e'loni — shaxsiy hisobotlar uchun** (`vendors.py:99-104` naqshi):

```python
VendorViewerDep = Annotated[Principal, Depends(require_permission(Permission.VENDOR_VIEW))]
VendorReadIntentDep = Annotated[
    AuditReadIntent,
    Depends(audit_read(TABLE_VENDORS, reason="vendor_view")),
]
"""D-09: shaxsiy ma'lumotning HAR BIR o'qilishi jurnalga tushadi.
`reason` boshqa o'qish yuzalaridan FARQ QILADI."""
```

⛔ D-07: `reason` yangi va NOMLANGAN (`report_receivables`, `report_three_way`)
— bitta hisobot so'rovi = bitta `audit_read`, sotuvchi boshiga emas.

**Bozor yechish + 403** (`billing.py:137-186` — `detail` **SATR**, lug'at EMAS):

```python
def _reject(code: str, http_status: int) -> HTTPException:
    """`detail` ⛔ **SATR**, lug'at EMAS — va bu klient kontrakti.
    `frontend/src/lib/api-client.ts::detailOf()` `detail` ni AYNAN satr
    deb o'qiydi; lug'at yuborilganda u **bo'sh satr** qaytaradi."""
    return HTTPException(status_code=http_status, detail=code)


def _market_id(principal: Principal) -> UUID:
    market_id = principal.market_id
    if market_id is None:
        raise _reject(_MARKET_NOT_SELECTED, status.HTTP_403_FORBIDDEN)
    return market_id
```

**Davr chegarasi — `_report_day()` ning davr jufti** (`billing.py:189-216`):

```python
def _report_day(day: date | None) -> date:
    today = business_today()
    resolved = today - timedelta(days=1) if day is None else day
    if resolved > today:
        # ⚠ `HTTP_422_UNPROCESSABLE_CONTENT` — RFC 9110 dagi joriy nom
        #   (`audit.py:184-187` da o'rnatilgan qoida). Eski `..._ENTITY`
        #   aliasi Starlette'da DEPRECATED.
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=_DAY_IN_FUTURE
        )
    return resolved
```

⛔ Pitfall 13: `_report_period(from, to)` shu shaklda yoziladi va
`settings.report_max_period_days` dan oshsa `422 report_period_too_long`.
Xato kodlari `ALL_BILLING_ERROR_CODES` reyestriga QO'SHILMAYDI — sabab
`billing.py:124-134` da literal yozilgan (frontend `error-codes.test.mjs`
darvozasi uchala locale matnini talab qilardi).

**Davr parametrlarining alias shakli** (`occupancy.py:162-168` — AYNAN
qayta ishlatiladi):

```python
@router.get("/accuracy", response_model=OccupancyAccuracyResponse)
async def occupancy_accuracy(
    principal: ReportViewerDep,
    session: TenantSessionDep,
    from_date: Annotated[date | None, Query(alias="from")] = None,
    to_date: Annotated[date | None, Query(alias="to")] = None,
) -> OccupancyAccuracyResponse:
```

**Bayt javob (eksport)** (`imports.py:148-149, 629-643`) — ⛔ `GET`, `POST` EMAS (R-3):

```python
XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
XLSX_SUFFIX = ".xlsx"


def _xlsx_response(payload: bytes, filename: str) -> StreamingResponse:
    """`.xlsx` baytlarini yuklab olish javobi qilib o'raydi.

    `Content-Disposition: attachment` — usiz brauzer faylni ko'rsatishga
    urinardi. Fayl nomi ASCII: `filename*=UTF-8''` shakli kerak emas va
    kirill nomli sarlavha eski proksilarni buzardi.
    """
    return StreamingResponse(
        iter([payload]),
        media_type=XLSX_MEDIA_TYPE,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(payload)),
        },
    )
```

⛔ D-06 fayl nomi deterministik: `{market}_{hisobot}_{from}_{to}.xlsx` —
ASCII cheklovi `_xlsx_response()` docstringidan meros.

---

### 2. `app/api/v1/reports.py` → daftar importi (controller · file-I/O)

**Analog:** `services/core-api/app/api/v1/imports.py:327-461` (`import_staff`).

**Modul docstringidagi tranzaksiya qarori** (`imports.py:1-21`) — ⛔ shu matn
ma'nosi `reports.py` ga ham ko'chadi:

```
TRANZAKSIYA BOSHQARUVI BU FAYLDA UMUMAN YO'Q — VA BU ATAYIN.
`TenantSessionDep` sessiyani ALLAQACHON tranzaksiya ichida beradi
(`app/deps.py::get_tenant_session`, 418-449-qatorlar) ...
D-14 (all-or-nothing) SHU SABABLI TEKIN KELADI va bu yerda hech qanday
qo'shimcha blok ochilmaydi.
```

**Uch darvoza — TARTIB MAJBURIY** (`imports.py:37-46`, `373`):

```python
rows = _read(await _read_bounded(file, settings), import_validator.STAFF_COLUMNS, settings)
```

`_read_bounded()` (`imports.py:507-543`) va `_read()` (`imports.py:546-563`)
**qayta ishlatiladi, ko'chirilmaydi**.

**Validatsiya → 422, hech narsa yozilmaydi** (`imports.py:566-603`):

```python
def _reject_if_invalid(issues: list[import_validator.ImportIssue]) -> None:
    if not issues:
        return
    counts: dict[str, int] = {}
    for issue in issues:
        counts[issue.code] = counts.get(issue.code, 0) + 1
    body = ImportErrorResponse(
        detail=_VALIDATION_FAILED,
        errors=[ImportErrorItem(row=i.row, code=i.code, message=i.message) for i in issues],
        error_counts=counts,
    )
    raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=body.model_dump())
```

**BITTA YIG'MA audit yozuvi** (`imports.py:422-441`) — Pattern 6 ning 6-qadami:

```python
# ⚠ YIG'MA YOZUV MAJBURIY. Usiz jurnalda 30 ta alohida `insert` ko'rinardi
# va "bular BITTA ommaviy amaldan" degan fakt yo'qolardi (T-02-180).
# `track_changes=False`: bu yozuvda "nima o'zgardi" savolining ma'nosi yo'q.
await write_app_audit(
    session,
    action=AuditAction.INSERT,
    table_name=TABLE_USERS,
    row_id=None,
    principal=principal,
    new={"import": "staff", "rows": len(rows), "created": len(created), ...},
    track_changes=False,
)
```

**Konstrayt → 409** (`imports.py:157-168, 606-626`) — `_conflict()` va
`_CONFLICT_STATES` o'zgarishsiz qayta ishlatiladi.

**Shablon huquqi** (`imports.py:136-146, 186-207`) — R-11 uchun to'rtinchi a'zo:

```python
_TEMPLATE_PERMISSIONS: dict[str, Permission] = {
    "stalls": Permission.STALL_MANAGE,
    "vendors": Permission.VENDOR_MANAGE,
    "staff": Permission.USER_MANAGE,
}
```

⛔ Uch joy BIRDAN yangilanadi: `xlsx_template.TEMPLATE_KINDS` (75-83),
`imports.ImportKind` (128-134), `_TEMPLATE_PERMISSIONS` (136-146) — va
`test_template_kinds_are_exactly_three` **nomi bilan birga** o'zgaradi
(Pitfall 4 / R-11). Daftar shabloni `REPORT_VIEW` emas, **yozuv** huquqini
oladi (D-20 → `MARKET_ADMIN`, Open Question 5 tavsiyasi).

---

### 3. `app/repositories/report_repo.py` (repository · derived aggregation)

**Analog:** `services/core-api/app/repositories/billing_repo.py:949-1057`.

**Belgili pul ifodalari — ⛔ IMPORT QILINADI, QAYTA YOZILMAYDI**
(`billing_repo.py:153-183`):

```python
_SIGNED_PAYMENT_EXPR: Final[str] = (
    "CASE WHEN p.kind = :reversal THEN -p.amount_soum ELSE p.amount_soum END"
)
"""⛔⛔ BU KONSTANTA IKKI FUNKSIYA TOMONIDAN ISHLATILADI VA IKKINCHI NUSXA
YOZILMAYDI ... G-14 ning butun da'vosi shu satrga tayanadi: ikki hosila
ko'rinish AYNAN bir xil kredit sonidan chiqadi, ya'ni ular **ajralib keta
olmaydi**."""

_SIGNED_ADJUSTMENT_EXPR: Final[str] = (
    "CASE WHEN a.direction = :increase THEN a.amount_soum ELSE -a.amount_soum END"
)
```

**Hosila so'rov — `text()` + `bindparams()` + `# noqa: S608`**
(`billing_repo.py:949-986`):

```python
_VENDOR_OUTSTANDING = text(
    f"""
    WITH parts AS (
        SELECT c.vendor_id AS vendor_id, c.amount_soum AS signed_soum
          FROM daily_charges c
         WHERE c.market_id = :market_id
           AND (:as_of IS NULL OR c.service_date < :as_of)
        UNION ALL
        SELECT c2.vendor_id, {_SIGNED_ADJUSTMENT_EXPR}
          FROM charge_adjustments a
          JOIN daily_charges c2 ON c2.market_id = a.market_id AND c2.id = a.charge_id
         WHERE a.market_id = :market_id
        UNION ALL
        SELECT p.vendor_id, -({_SIGNED_PAYMENT_EXPR})
          FROM payments p
         WHERE p.market_id = :market_id
    )
    SELECT vendor_id, sum(signed_soum)::bigint AS outstanding_soum
      FROM parts
     GROUP BY vendor_id
    """  # noqa: S608
).bindparams(
    bindparam("market_id", type_=_UUID),
    bindparam("as_of", type_=Date()),
    bindparam("vendor_ids", type_=_UUID_ARRAY),
    bindparam("increase", type_=Text()),
    bindparam("reversal", type_=Text()),
)
"""⛔ `S608` SHU SO'ROVDA O'CHIRILGAN VA SABAB TOR: f-string ga tushadigan
YAGONA qiymat — shu moduldagi SOBIT `_SIGNED_*_EXPR` konstantalari. Tashqi
kirish f-string ga umuman kelmaydi; har qiymat `bindparam(...)` orqali
TIPLANGAN parametr."""
```

**Repozitoriy funksiyasi va `int()` konvertatsiyasi** (`billing_repo.py:1023-1057`):

```python
async def vendor_outstanding(session, *, market_id, vendor_ids=None, as_of=None) -> dict[UUID, int]:
    result = await session.execute(_VENDOR_OUTSTANDING, {...})
    return {row["vendor_id"]: int(row["outstanding_soum"]) for row in result.mappings()}
```

⛔ C-6: pul **`int`**, `float` HECH QAYERDA; `::bigint` cast SQL da.
⛔ D-03: `report_repo.py` yangi jadval yaratmaydi — `vendor_outstanding()`,
`daily_charges`, `payments`, `reconciliation_cases`, `billing_anomalies`
ustidan HOSILA so'rov.

**Nol qatorlar `generate_series` bilan** — RESEARCH Pattern 1 ning
`_REVENUE_BY_DAY` bloki (08-RESEARCH.md:561-590) shu naqshning davomi;
`GROUP BY` yolg'iz to'lovsiz kunni tushirib qoldirardi.

---

### 4. `app/services/xlsx_export.py` (service · transform → bytes)

**Analog A — formula qochirish va yagona yozish yo'li:**
`services/core-api/app/services/xlsx_template.py:216-228, 469-484`.

```python
FORMULA_PREFIXES: Final = ("=", "+", "-", "@", "\t", "\r")
"""`\\t` va `\\r` ro'yxatda ATAYIN: ular ko'rinmaydi, lekin Excel ularni
tashlab yuborib KEYINGI belgiga qaraydi — ya'ni `"\\t=cmd|..."` oddiy `=`
tekshiruvidan o'tib ketardi."""


def escape_formula(value: str) -> str:
    if value.startswith(FORMULA_PREFIXES):
        return "'" + value
    return value


def _write_text(worksheet, row: int, column: int, value: str, cell_format=None) -> None:
    """YAGONA matn yozish yo'li — `escape_formula()` shu yerda qo'llanadi.

    `worksheet.write()` boshqa hech qayerda CHAQIRILMAYDI ... `write_string()`
    ATAYIN (`write()` emas): `write()` `"123"` ni songa, `"=1+1"` ni esa
    FORMULAGA aylantirib yuborardi — ya'ni qochirishdan keyin ham hujum
    tiklanardi.
    """
    worksheet.write_string(row, column, escape_formula(value), cell_format)
```

⛔ `escape_formula` va `_write_text` **IMPORT QILINADI** — ikkinchi nusxa
yozilmaydi (Don't Hand-Roll qatori). Qarzdorlik reestrida `vendor_name` bor:
`=HYPERLINK(...)` nomli sotuvchi direktorning mashinasida kod bajartirardi.

**Analog B — bayt determinizmi (⛔ TEST FIKSTURSIDAN MAHSULOTGA KO'CHIRILADI):**
`tests/fixtures/karmana_seed.py:679-703`.

```python
def _freeze_zip(raw: bytes) -> bytes:
    """ZIP a'zolarining sanasini MUZLATADI (determinizm, 2-qatlam).

    `XlsxWriter` `in_memory` rejimida `ZipFile.writestr(nom, ...)` ni
    chaqiradi, `zipfile` esa bunday chaqiruvda a'zo sanasini SOAT'dan
    oladi ... «determinizm» testi GOHIDA yiqilardi (T-02-172).

    Qayta o'rash mazmunga tegmaydi: nom, siqish turi va ochilgan hajm
    o'zgarmaydi, ya'ni `xlsx_reader._check_zip()` darvozalari ham xuddi
    shu qiymatlarni ko'radi.
    """
    buffer = io.BytesIO()
    with (
        zipfile.ZipFile(io.BytesIO(raw)) as source,
        zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as target,
    ):
        for info in source.infolist():
            frozen = zipfile.ZipInfo(info.filename, date_time=_FROZEN_ZIP_TIME)
            frozen.compress_type = info.compress_type
            frozen.external_attr = info.external_attr
            frozen.create_system = info.create_system
            target.writestr(frozen, source.read(info.filename))
    return buffer.getvalue()
```

⛔ Pitfall 3: bu **CONTEXT.md D-05 ning noto'g'ri joyini tuzatadi** —
`_freeze_zip` `xlsx_template.py` da YO'Q. Ko'chirilgach fikstursdagi nusxa
**o'chiriladi va import qilinadi**; ikki nusxa bir kun ajralib ketardi.

**Analog C — varaq qurish tanasi:** `xlsx_template.py:282-315`
(`build_error_report`) — R-5 ning ustun tartibi shu shakldan:

```python
def build_error_report(issues: Sequence[ImportIssue], locale: str) -> bytes:
    texts = _texts(locale)
    buffer = io.BytesIO()
    workbook = xlsxwriter.Workbook(buffer, {"in_memory": True})
    try:
        header_format = workbook.add_format({"bold": True, "bg_color": "#F2F2F2"})
        worksheet = workbook.add_worksheet(texts["errors_sheet"])
        for column, key in enumerate(("error_row", "error_code", "error_message")):
            _write_text(worksheet, 0, column, texts[key], header_format)
        worksheet.set_column(0, 0, 8)
        for offset, issue in enumerate(issues, start=1):
            # `row` — SON, ya'ni `escape_formula()` dan o'tmaydi va o'tishi
            # ham kerak emas: Excelda u bo'yicha SARALASH mumkin bo'lishi
            # kerak (matn sifatida "100" "20" dan oldin turardi).
            worksheet.write_number(offset, 0, issue.row)
            _write_text(worksheet, offset, 1, issue.code)
        worksheet.freeze_panes(1, 0)
        worksheet.autofilter(0, 0, max(len(issues), 1), ERROR_REPORT_COLUMNS - 1)
    finally:
        workbook.close()
    return buffer.getvalue()
```

⛔ Yangi eksportda oxirgi qator `return freeze_zip(buffer.getvalue())` bo'ladi
va `workbook.set_properties({"created": FROZEN_CREATED})` qo'shiladi
(1-qatlam: `docProps/core.xml` soatdan kelardi).
⛔ Pitfall 12/D-10: o'lchanmagan qiymat `sheet.write_blank(...)`, `0` EMAS.

**Analog D — uch tilli matnlar SERVERDA:** `xlsx_template.py:88-167, 318-326`.

```python
_DEFAULT_LOCALE = "uz-Latn"
# Sarlavhalar TARJIMASI — SERVERDA, chunki fayl serverda hosil bo'ladi.
# Bu 1-faza D-16 ("DB kontenti bitta tilda") ga zid EMAS: bular DB kontenti
# emas, hosil qilinadigan hujjatning matni.
_TEXTS: Final[dict[str, dict[str, str]]] = {"uz-Latn": {...}, "uz-Cyrl": {...}, "ru": {...}}


def _texts(locale: str) -> dict[str, str]:
    """Til uchun matnlar; noma'lum til uz-Latn ga tushadi. Istisno
    KO'TARILMAYDI: yangi til qo'shilganda shablonni yuklab olish 500 bilan
    tugashi — usta oqimini butunlay to'sadigan nosozlik bo'lardi."""
    return _TEXTS.get(locale, _TEXTS[_DEFAULT_LOCALE])
```

**Locale manbai** (`imports.py:495-504`) — ⛔ so'rov parametridan EMAS:

```python
async def _locale_of(session: AsyncSession, principal: Principal) -> str:
    """Foydalanuvchi profilidagi til; topilmasa uz-Latn.
    Til `users.locale` dan olinadi, so'rov parametridan EMAS: profil tili —
    bitta HAQIQAT MANBAI."""
    profiles = await user_repo.list_profiles(session, [principal.user_id])
    return profiles[0].locale if profiles else "uz-Latn"
```

---

### 5. `migrations/versions/0024_ledger_entries.py` (migration · DDL)

**Analog:** `migrations/versions/0023_notification_domain.py`.

**Fayl boshi va revision** (`0023:90-149`):

```python
from __future__ import annotations

from collections.abc import Sequence
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

from migrations.entities.policies import owner_bootstrap_policy, tenant_policy
from migrations.helpers import create_entity, enable_tenant_rls, attach_audit_trigger

revision: str = "0023"
down_revision: str | Sequence[str] | None = "0022"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None
```

**Jadval — `market_id` + kompozit FK + UNIQUE** (`0023:330-378`):

```python
op.create_table(
    "reconciliation_cases",
    _market_id(),
    _uuid_pk(),
    sa.Column("service_date", sa.Date(), nullable=False),
    _created_at(),
    _updated_at(),
    sa.PrimaryKeyConstraint("id", name="pk_reconciliation_cases"),
    sa.ForeignKeyConstraint(
        ["market_id"], ["markets.id"], name="fk_reconciliation_cases_market_id_markets"
    ),
    # ⛔ `ondelete` YO'Q (NO ACTION)
    sa.ForeignKeyConstraint(
        ["market_id", "anomaly_id"],
        ["billing_anomalies.market_id", "billing_anomalies.id"],
        name="fk_reconciliation_cases_anomaly",
    ),
    # KOMPOZIT FK NISHONI
    sa.UniqueConstraint("market_id", "id", name="uq_reconciliation_cases_market_id_id"),
    sa.CheckConstraint(CASE_STATUS_CHECK, name="status_allowed"),
)
```

⛔ R-4 uchun: `ledger_entries(market_id, id, business_date, stall_id,
amount_soum BIGINT, imported_by, created_at)` + `UNIQUE(market_id,
business_date, stall_id)` + kompozit FK → `stalls(market_id, id)`.
⛔ `financial_guards()` CHAQIRILMAYDI va `FINANCIAL_TABLES` ga
QO'SHILMAYDI — sabab `0023:77-87` da literal yozilgan (daftar 0 ni ham
yozishi mumkin, `daily_charges` esa `CHECK (amount_soum > 0)` talab qiladi).
Bu farq **jadval docstringida LITERAL** yozilsin (Pattern 6 ogohlantirishi).

**RLS — TARTIB MAJBURIY** (`0023:640-648`, `migrations/helpers.py:155-179`):

```python
# TARTIB MAJBURIY: ENABLE + FORCE + GRANT -> policy (Pitfall 10).
# `alembic-utils` `ENABLE`/`FORCE` ni BILMAYDI — ularsiz policy HECH QANDAY
# ta'sir ko'rsatmaydi va jadval hamma uchun ochiq bo'ladi.
for table in NOTIFICATION_TENANT_TABLES:
    enable_tenant_rls(table)
    create_entity(tenant_policy(table))
    create_entity(owner_bootstrap_policy(table))
```

```python
# migrations/helpers.py:166-175
def enable_tenant_rls(table: str, role: str = APP_ROLE) -> None:
    """GRANT'siz policy ma'nosiz bo'ladi (huquq yo'q -> `permission denied`),
    ENABLE/FORCE'siz esa policy ma'nosiz bo'ladi (hamma narsa ochiq)."""
    enable_rls(table)
    grant_app_dml(table, role=role)
```

**Audit — nom `schema_contract` ga BIR COMMITDA** (`0023:650-664`):

```python
# ⚠ NOM `schema_contract.AUDITED_TABLES` GA SHU MIGRATSIYA BILAN BIR
#   COMMITDA qo'shildi (`06-04` OP-4 naqshi), ya'ni `PENDING_AUDIT_TRIGGERS`
#   BO'SH qoladi va `test_audited_tables_have_trigger` UZLUKSIZ yashil turadi.
for table in NOTIFICATION_AUDITED_TABLES:
    attach_audit_trigger(table)
```

⛔ D-21: yangi `SECURITY DEFINER` funksiya YO'Q — `0023:65-69` bandi
so'zma-so'z takrorlanadi (`DEFINER_SURFACES` BO'SH qoladi, T-06-22).

---

### 6. `migrations/versions/0025_notification_settings_id.py` (migration · ALTER)

**Nishon jadval** (`0023:541-568`) — hozirgi PK `market_id`:

```python
op.create_table(
    "market_notification_settings",
    _market_id(),
    ...
    sa.PrimaryKeyConstraint("market_id", name="pk_market_notification_settings"),
    sa.ForeignKeyConstraint(["market_id"], ["markets.id"], name="fk_..."),
)
```

⛔ Pitfall 16: `id uuid PRIMARY KEY DEFAULT uuidv7()` qo'shilganda
`UNIQUE(market_id)` **SAQLANADI** — `binding_repo._BIND_DIRECTOR_CHAT`
(`binding_repo.py:540-548`) `ON CONFLICT (market_id) DO UPDATE` ishlatadi va
UNIQUE yo'qolsa direktor botga ULANA OLMAYDI.
⛔ Test da'vosi: `bind_director()` ni migratsiyadan keyin IKKI marta chaqirish
(insert + update shoxlari) + `audit_log` da `row_id IS NOT NULL`.
⛔ «`fn_audit_row()` yiqiladi» deb test YOZILMASIN (Open Question 1).

---

### 7. `ops/backup/` (utility · batch + event-driven)

**Shell intizomi analogi:** `ops/scripts/verify-tunnel.sh:1-87`.

```sh
#!/usr/bin/env sh
# =============================================================================
# SBOZOR — SC#5 ning 3-DA'VOSI: marshrut haqiqatan tunneldan ketadi.
#
# ⚠⚠ BU SKRIPT CI'DA ISHLAMAYDI VA ISHLASHI HAM KERAK EMAS.
# ...
# U go-live checklist'ining bandi: VPS'da, deploy'dan KEYIN, bir marta.
# =============================================================================
#
# Ishlatilishi:
#     ops/scripts/verify-tunnel.sh 192.168.1.64
#
# Chiqish kodi: 0 — ...; 1 — ... Nol bo'lmagan kod deploy'ni TO'XTATISHI kerak.

set -eu
```

Ko'chiriladigan intizom:
1. Sarlavha bloki — **nima o'lchanadi, nima O'LCHANMAYDI** (halol chegara);
2. «Ishlatilishi» + **chiqish kodi semantikasi** izohda;
3. `set -eu` (⛔ `run-backup.sh` da `set -euo pipefail`);
4. Har nosozlik shoxida **sabab ro'yxati** `stderr` ga (`verify-tunnel.sh:78-85`);
5. Har tekshiruv ALOHIDA — «ikki xil nosozlik, ikki xil tuzatish»
   (`verify-tunnel.sh:50-53`).

**Image analogi:** `services/core-api/Dockerfile:1-14`.

```dockerfile
# syntax=docker/dockerfile:1

# SBOZOR core-api — multi-stage image.
#
# Baza: python:3.13-slim-trixie (Debian, glibc). musl-asosidagi yengil
# image'lar ISHLATILMAYDI — ... (sabab literal)

FROM python:3.13-slim-trixie AS base

COPY --from=ghcr.io/astral-sh/uv:0.11.33 /uv /bin/uv
```

⛔ `COPY --from=<VERSIYALANGAN TEG>` naqshi allaqachon repo'da (uv 0.11.33).
R-6 uni `restic/restic:0.19.1` uchun takrorlaydi; baza esa
`postgres:18.4-trixie` (Pitfall 7).
⚠ A1 zondi: `docker run --rm <image> restic version` — Wave 0 ning bir
qatorlik bandi; fallback `ADD https://github.com/restic/restic/releases/...`.

**Heartbeat upsert analogi:** `binding_repo.py:540-548` (`ON CONFLICT
(market_id) DO UPDATE`) va `heartbeat.sql` ning maqsad jadvali
`system_heartbeats` — **GLOBAL, RLS'siz** (`alerting.py:665-671`):

```python
# ⚠ TENANT KONTEKSTI YO'Q: `system_heartbeats` — GLOBAL jadval, unda
#   `market_id` ustuni umuman yo'q (`ops.py::SystemHeartbeat`).
```

⛔ Komponent nomi BITTA joyda va u `alerting.BACKUP_COMPONENT` bilan
**matn sifatida bog'lanadi** — `tests/unit/test_backup_contract.py`
ikkisini solishtiradi.

**Compose xizmati analogi:** `compose.yaml:55-120` (`storage:` bloki):

```yaml
  storage:
    # DALIL-KADRLARNING S3-MOS ARXIVI (04-01, CAM-07, W0-4).
    #
    # ⚠ PROFILSIZ — `worker` va `go2rtc` bilan bir xil sabab: bu ISHLAB
    # CHIQARISH komponenti. Profil ortiga yashirilsa kadr olish zanjiri
    # yuklash bosqichida yiqilardi ...
    #
    # OLTINCHI KONTEYNER, UCHINCHI SERVIS EMAS: SeaweedFS — TAYYOR image,
    # biz yozgan kod emas (`db`, `cache`, `go2rtc`, `nginx` bilan bir
    # toifa). CLAUDE.md ning «aynan 3 ta servis» cheklovi BIZNING
    # servislarimizga tegishli va u buzilmaydi.
    image: chrislusf/seaweedfs:4.40
    volumes:
      # ⚠ `:ro` MAJBURIY — `go2rtc.yaml` va `mediamtx.yml` bilan bir xil
      # qoida: server o'z konfiguratsiyasini QAYTA YOZA OLMASLIGI kerak.
      - ./ops/seaweedfs/s3.json:/etc/seaweedfs/s3.json:ro
    environment:
      TZ: ${TZ:-Asia/Tashkent}
    restart: unless-stopped
```

⛔ C-1: `backup` bloki uchun **«SAKKIZINCHI KONTEYNER, TO'RTINCHI SERVIS
EMAS»** izohi shu 63-66-qatorlar shaklida LITERAL yoziladi.
⛔ `seaweed:/seaweed:ro` — `:ro` sababi shu izohdan meros.
⛔ Sirlar `${...}` orqali; `.env.example` ga besh yangi kalit (`.env.example:1-7`
sarlavha bloki: «HAQIQIY SIRLARNI BU YERGA YOZMANG»).

**Analog yo'q:** `loop.sh` ning idempotent poll tsikli — repo'da bash daemon
yo'q. Konseptual manba: 4-faza D-03 (`app/jobs/capture.py` tikining
idempotentligi) va `alerting.py:188-196` ning `HEARTBEAT_STALE_HOURS = 26`
mulohazasi.

---

### 8. `ops/docs/go-live.md` (doc · runbook)

**Analog:** `ops/docs/monitoring.md:1-90`.

```markdown
# Kuzatuv va alertlar — operatsion yo'riqnoma (FOUND-06, D-19..D-22)

> **Bu hujjat darvoza EMAS.** U operatsion tartib: kuzatuv qanday
> ishlashini, uning **halol chegarasini** va odam qo'li bilan
> bajariladigan uch bandni yozadi. Kodning darvozalari
> `tests/integration/test_alerting.py` ... da.

## 0. Bir jumlada
...
### Halol chegara — buni yozib qo'yish shart
⛔ **VPS butunlay o'lsa ichkaridagi HECH BIR kod alert yubora olmaydi.**
Bu kamchilik emas, fizika ...

| Nima | Qayerda |
|------|---------|
```

Ko'chiriladigan struktura:
1. Sarlavhada **talab ID'lari** (`FOUND-07, D-12..D-16, SC#4`);
2. «Bu hujjat darvoza EMAS» + darvozalarning fayl nomlari;
3. `## 0. Bir jumlada`;
4. Har bo'limda **halol chegara** bloki (⛔ nima O'LCHANMAYDI);
5. Jadval shakli: `| Nima | Qayerda |`.

⛔ CONTEXT.md `<specifics>`: har band **«buyruq + kutilgan natija»** —
`verify-tunnel.sh` ning «Chiqish kodi: 0 — …; 1 — …» shakli namuna.
`SC#4 (1)` statik testi (`tests/unit/test_runbook_shape.py`) aynan shu
shaklni skanerlaydi.

---

### 9. `frontend/src/app/[locale]/(app)/reports/page.tsx` (page · request-response)

**Analog:** `frontend/src/app/[locale]/(app)/reconciliation/page.tsx:81-171`.

```tsx
"use client";

import { Suspense } from "react";
import { useTranslations } from "next-intl";

import { useAuthStore } from "@/lib/auth-store";
import { hasPermission } from "@/lib/rbac";

export default function ReconciliationPage() {
  const t = useTranslations();
  const { principal } = useAuthStore();

  if (!hasPermission(principal?.roles ?? [], "report_view")) {
    return (
      <p className="rounded-sm bg-danger/10 px-3 py-2 text-sm text-danger-text" role="alert">
        {t("errors.forbidden")}
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-semibold tracking-tight">{t("recon.title")}</h1>
      <Suspense fallback={<p className="text-sm text-text-muted" role="status">{t("common.loading")}</p>}>
        <ReconciliationWorkspace />
      </Suspense>
    </div>
  );
}
```

⛔ `Suspense` **MAJBURIY** (`page.tsx:72-74`): ish maydoni `?from=`/`?to=` ni
`nuqs` orqali KLIENTDA o'qiydi va chegara bo'lmasa Next 16 butun marshrutni
statik prerender ro'yxatidan chiqarib `build` ni yiqitadi.
⛔ Huquq ko'zgusi so'rovdan OLDIN (`page.tsx:67-70`) — haqiqiy nazorat SERVERDA.
⛔ Bloklar `data-*-block` atributi bilan va **sahifa mazmun atributini
YOZMAYDI** (`page.tsx:48-57`) — atribut ro'yxat komponentining O'ZIDA.

**Davr tanlagichi analogi:** `frontend/src/components/billing/day-picker.tsx:62-113`.

```tsx
export const BILLING_DAY_PARAM = "day";

export function useBillingDay(): BillingDaySelection {
  const [raw, setRaw] = useQueryState(
    BILLING_DAY_PARAM,
    parseAsString.withDefault("").withOptions({ history: "push" }),
  );
  const timeZone = useTimeZone() ?? "Asia/Tashkent";
  const now = useNow();

  const todayIso = businessDayIn(timeZone, now);
  const yesterdayIso = shiftIsoDay(todayIso, -1);
  const day = isValidIsoDay(raw) && raw <= todayIso ? raw : yesterdayIso;

  return {
    day, todayIso, yesterdayIso,
    isToday: day === todayIso,
    setDay: (next: string) => {
      // Standart kun uchun parametr UMUMAN yozilmaydi — toza havola
      // ertasiga ham O'SHA KUNGI standartni ko'rsatadi.
      void setRaw(next === yesterdayIso ? null : next);
    },
  };
}
```

⛔ Sof yordamchilar (`businessDayIn`, `isValidIsoDay`, `shiftIsoDay`)
`components/snapshots/day-picker.tsx` DAN IMPORT QILINADI, nusxa olinmaydi
(`day-picker.tsx:41-48` — ikki nusxa `en-CA`/UTC arifmetikasi bo'yicha
ajralib ketardi).
⛔ Kelajak kuni `max` atributi + `onChange` filtri bilan ikki qatlamda
(`day-picker.tsx:145-160`), jimgina bugunga TUSHIRILMAYDI.

---

### 10. `frontend/src/components/reports/accuracy-view.tsx` (component)

**Analog:** `frontend/src/components/reconciliation/hit-rate-card.tsx:100-164` —
⛔ **D-10 / WR-05 ning aynan naqshi**:

```tsx
if (cases.counts === undefined) {
  /*
   * ⛔ Xatoda ⛔ NOL CHIZILMAYDI: nol O'LCHANGAN qiymat ma'nosini berardi.
   *   Nomlangan sabab qo'shni bloklarda allaqachon bor.
   */
  return (<Card data-recon-content="hitrate">...{t("recon.accuracyNone")}</Card>);
}

...

{resolved === 0 ? (
  /*
   * ⛔ MAXRAJ NOL — FOIZ ELEMENTI UMUMAN CHIZILMAYDI. Bu shox `0 %` ni
   *   «yashiradigan» shart EMAS: foiz shu tarmoqda HISOBLANMAYDI ham.
   */
  <>
    <p className="text-sm">{t("recon.accuracyNone")}</p>
    <p className="text-xs text-text-muted">{t("recon.accuracyNoneHint", { pending })}</p>
  </>
) : (
  <>
    <p aria-describedby={`${denominatorId} ${excludedId}`} className="font-mono ...">
      {format.number(justified / resolved, { style: "percent" })}
    </p>
    {/* ⛔ MAXRAJ JUMLASI — MAJBURIY */}
    <p className="text-sm" id={denominatorId}>{t("recon.accuracyBody", { resolved, justified })}</p>
  </>
)}
```

⛔ Farq: aniqlik hisobotida foiz **SERVERDAN** keladi (`measured`, `correct`,
`false_occupied`, `false_empty` — `occupancy.py:193-213`), klientda
`justified / resolved` kabi hisob QILINMAYDI (05-14).
⛔ `format.number(v, { style: "percent" })` — qo'lda `%` yopishtirilmaydi
(`hit-rate-card.tsx:54-58`).
⛔ `measured === false` → blok umuman chizilmaydi yoki «o'lchov yo'q»
holati; `null ?? 0` refleksi TAQIQ (Pitfall 12).

---

### 11. `frontend/src/lib/report-queries.ts` (store · server state)

**Analog:** `frontend/src/lib/occupancy-queries.ts:1-212`.

```ts
"use client";

import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";
import { accuracyReportSchema } from "@/lib/api-types";
import { useAuthStore } from "@/lib/auth-store";
import { domainKey } from "@/lib/market-queries";

/*
 * ⚠ KALITLAR TUG'ILISHIDANOQ DOIRALANGAN (§5.4, §S-12). `domainKey`
 *   `market-queries.ts` DAN IMPORT QILINADI — ikkinchi nusxa yaratilmaydi.
 *   GLOBAL (marketsiz) KALIT KONSTANTASI BU MODULDA UMUMAN YO'Q.
 * ⛔ MUTATSIYA BU MODULDA YO'Q VA BO'LMAYDI HAM.
 * ⛔ FOIZ BU MODULDA HISOBLANMAYDI.
 */

export const OCCUPANCY_PATH = "/occupancy";

export const accuracyKey = (marketId: string, from: string | null, to: string | null) =>
  domainKey(marketId, "occupancy", "accuracy", from, to);

function useMarketId(): string | null {
  const { principal } = useAuthStore();
  return principal?.marketId ?? null;
}

export function useAccuracyReport(options?: { enabled?: boolean }) {
  const marketId = useMarketId();
  return useQuery({
    queryKey: accuracyKey(marketId ?? "", null, null),
    queryFn: () => apiFetch(`${OCCUPANCY_PATH}/accuracy`, { schema: accuracyReportSchema }),
    // ⚠ `enabled: marketId !== null` — KONTRAKT, qulaylik emas: bozorsiz
    //   sessiyada javob `403 market_not_selected` bo'lardi va u kesh
    //   grafida yashab qolardi.
    enabled: marketId !== null && (options?.enabled ?? true),
    refetchOnWindowFocus: false,
  });
}
```

⛔ 8-faza `accuracyKey` ning `from`/`to` argumentlarini **HAQIQIY qiymat
bilan** to'ldiradi — `occupancy-queries.ts:69-81` docstringi buni aynan
oldindan aytgan («8-fazada tanlagich qo'shilganda kesh yozuvi O'ZI to'g'ri
bo'linadi»). Kalit fabrikasi O'ZGARMAYDI.
⛔ Eksport tugmasi **query emas** — to'g'ridan-to'g'ri `GET` havola
(RESEARCH diagrammasi: «[.xlsx] tugmasi (to'g'ridan GET)»).

---

### 12. `frontend/src/components/shell/app-shell.tsx` (MOD · nav)

**Analog:** o'zi, `app-shell.tsx:59-97` — ⛔ **literal union tipi**:

```tsx
type NavItem = {
  href:
    | "/dashboard"
    | "/map"
    ...
    | "/reconciliation"
    | "/users"
    | "/audit"
    | "/markets/new";
  labelKey: "dashboard" | "map" | ... | "reconciliation" | "users" | "audit" | "newMarket";
  icon: LucideIcon;
  permission: Permission | null;
  group: NavGroup;
};
```

⛔ Pitfall 18: `"/reports"` **ikkala unionga** qo'shiladi, aks holda `tsc`
qizaradi. `NAV_ITEMS` tartibi ma'noli (`app-shell.tsx:98-104`): mobil panel
birinchi TO'RTTASINI oladi — `/reports` `group: "market"` yoki `"system"` ga
tushadi, birinchi to'rtlikni surmaydi.
⛔ `permission: "report_view"` — menyuni YASHIRADI, xavfsizlik chegarasi
serverda (`app-shell.tsx:49-53`).

---

### 13. `tests/tenancy/test_personal_data_coverage.py` (MOD · ⛔ ENG XAVFLI DARVOZA)

**Analog:** o'zi. Ikki reyestr (115-165) va ikki assertion (417-460, 540-583).

```python
BINARY_PERSONAL_ROUTES: dict[str, str] = {
    "/api/v1/snapshots/{snapshot_id}/image": (
        "dalil-kadr BAYTLARI — bozor tashrifchilarining tasviri, ya'ni O'zR "
        "shaxsiy ma'lumotlar qonuni ostidagi ma'lumot. Javob modeli YO'Q, "
        "shuning uchun `PERSONAL_FIELDS` uni HECH QACHON topa olmaydi."
    ),
}
"""⚠ RO'YXAT O'ZI DRIFT MANBAI BO'LMASIN degan shart quyidagi YOPIQLIK
  testida: har bir `response_model` siz `GET` marshruti IKKALA ro'yxatdan
  BIRIDA bo'lishi SHART. Ya'ni yangi bayt-marshrut qo'shgan odam tanlov
  qilishga MAJBUR — «unutish» yo'li yopiq."""
```

```python
EVIDENCE_FRAME_ALLOWED = frozenset({Permission.CAMERA_VIEW, Permission.OCCUPANCY_REVIEW})

def test_binary_personal_routes_declare_read_audit_and_permission() -> None:
    routes = binary_routes(fastapi_app)
    for path in sorted(BINARY_PERSONAL_ROUTES):
        route = routes[path]
        assert audit_resources(route), (...)
        strict = set(required_permissions(route))
        any_gates = required_any_permissions(route)
        granted = strict.union(*any_gates) if any_gates else strict
        assert granted, (...)
        assert granted <= EVIDENCE_FRAME_ALLOWED, (...)   # ⛔ SHU YERDA QIZARADI
```

⛔ **KENGAYTIRISH, BO'SHATISH EMAS** (Pattern 3 / Pitfall 2). To'g'ri shakl —
**per-route ruxsat xaritasi**, kalitlari `BINARY_PERSONAL_ROUTES` bilan
AYNAN teng deb assert qilinadi; `.get()` ISHLATILMAYDI (`KeyError` baland
ovozli nosozlik):

```python
BINARY_PERSONAL_ALLOWED: dict[str, frozenset[Permission]] = {
    "/api/v1/snapshots/{snapshot_id}/image": EVIDENCE_FRAME_ALLOWED,
    "/api/v1/reports/receivables.xlsx": frozenset({Permission.REPORT_VIEW, Permission.VENDOR_VIEW}),
    "/api/v1/reports/three-way.xlsx": frozenset({Permission.REPORT_VIEW, Permission.VENDOR_VIEW}),
}
```

⛔ Uch **XATO** yo'l (Pitfall 2 jadvali) va nima uchun ular xato:
`EVIDENCE_FRAME_ALLOWED` ni kengaytirish (05-15 bekor bo'ladi) · eksportni
`POST` qilish (`get_routes()` faqat `GET` ni yuradi → jimgina chetlab o'tish) ·
shaxsiy eksportni `NON_PERSONAL_BINARY_ROUTES` ga yozish (yolg'on tasnif).

⚠ `MINIMUM_PERSONAL_ROUTES = 4` (103-113) — **QUYI chegara**, o'zgarmaydi;
`/reports/receivables` JSON javobi `vendor_name` bilan hosila to'plamga
qo'shiladi (Pitfall 1) va `audit_read` + `VENDOR_VIEW` e'lon qilishi SHART.

---

### 14. `tests/unit/test_backup_contract.py` (test · static scan)

**Analog:** `tests/unit/test_compose_sim_env.py:1-60`.

```python
"""O'LIK `SIM_*` KONFIGURATSIYASINING DARVOZASI (CAM-09, 03-VERIFICATION GAP-1).
...
SKANERNING IKKI QOIDASI (03-01 da o'rnatilgan naqsh).

1. **QUYI CHEGARA MAJBURIY.** Yo'l noto'g'ri yozilganda yoki `compose.yaml`
   ko'chirilganda skaner BO'SH to'plamda ishlab, hamma assert jimgina o'tib
   ketardi — darvoza mavjudligini yo'qotgan holda yashil bo'lib turaverardi.

2. **SKANER O'Z FAYLINI ISTE'MOLCHILAR TO'PLAMIDAN CHIQARIB TASHLAYDI.**
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
COMPOSE = REPO_ROOT / "compose.yaml"
```

⛔ Ikkala qoida ham `test_backup_contract.py` ga ko'chadi:
(1) skript topilmasa test QIZARADI (bo'sh to'plamda yashil emas);
(2) `heartbeat.sql` dagi komponent nomi `alerting.BACKUP_COMPONENT` dan
**import qilinib** solishtiriladi, literal takrorlanmaydi;
(3) retention qiymatlari (`--keep-daily 14 --keep-weekly 8 --keep-monthly 12`)
LITERAL qulflanadi (C-3);
(4) `pg_dump ... | restic` **quvurining YO'QLIGI** va `--stdin-from-command`
ning MAVJUDLIGI (Pitfall 5), `--compress=0` / `-Z0` (Pitfall 6);
(5) heartbeat chaqiruvi skriptning OXIRGI qadami (Pattern 4 — `finally` da
yoki oldin YOZILMAYDI).

⚠ Nomlar ro'yxatiga tayanmaslik qoidasi: `tests/unit/test_heartbeat_registry.py:38-60`
(«DARVOZA NOMLAR RO'YXATIGA TAYANMAYDI — U HOSILA», AST bilan yig'ish).

---

### 15. `tests/integration/test_phase8_criteria.py` (test · criteria)

**Analog:** `tests/integration/test_phase7_criteria.py:1-60` va
`test_every_criterion_has_its_own_test()` (1650).

```python
"""7-fazaning BESHTA muvaffaqiyat mezoni — ROADMAP matni bilan bog'langan YAGONA fayl.

BU FAYL MAVJUD TESTLARNI TAKRORLAMAYDI — U ULARNI ZANJIR SIFATIDA BOG'LAYDI.
  * `test_reconciliation_api.py` (07-10) — ...
  * `test_notifications.py`      (07-13) — ...

Bu yerdagi savol boshqa va u faqat shu yerda beriladi: **ROADMAP'da
yozilgan jumla bugun rostmi?** Har test docstringi mezon matnini
SO'ZMA-SO'Z olib yuradi.

⛔⛔ SOXTALASHTIRISH TAQIQLANADI — VA BU FAZADA TAQIQNING SHAKLI BOSHQA.
...
Shuning uchun bu modulda TAQIQLANADI:
  1. standart kutubxonaning soxta obyekt vositalari (reyestr: `_FAKE_ROOTS`);
  2. pytest ning tuzatuvchi fixture'i (reyestr: `_FAKE_FIXTURES`);
...
⛔⛔ SC#4 NING CHEGARASI — OCHIQ YOZILADI, YASHIRILMAYDI.
"""
```

⛔ 8-faza uchun taqiqning shakli yana boshqa: eng arzon yolg'on —
`system_heartbeats['backup']` qatorini **QO'LDA** yozib «zaxira ishladi»
deyish, yoki `.xlsx` baytlarini tekshirmasdan `200` ni mezon deb hisoblash.
`_FAKE_ROOTS` naqshi shu ikkisiga moslanadi.
⛔ Nomlangan chegara bloki MAJBURIY: FOUND-07 ning ikkinchi jumlasi
(«tiklash mashqi ... o'tkazilgan») CI'da bajarilmaydi → `08-HUMAN-UAT.md`,
egasi Ops (Pattern 5).

---

## Shared Patterns

### A. Huquq + audit e'loni (barcha yangi controller marshrutlari)

**Manba:** `services/core-api/app/api/v1/vendors.py:99-104`,
`services/core-api/app/security/audit.py:410-426`
**Qo'llanadi:** `reports.py` ning HAR marshruti

```python
ReportViewerDep = Annotated[Principal, Depends(require_permission(Permission.REPORT_VIEW))]
ReportReadIntentDep = Annotated[
    AuditReadIntent,
    Depends(audit_read(TABLE_VENDORS, reason="report_receivables")),
]
```

⛔ `require_any_permission()` ISHLATILMAYDI — `billing.py:4-19` va
`test_personal_data_coverage.py:854-883` («darvoza faqat
`SNAPSHOT_EVIDENCE_FRAME_ROUTES` da») ikkalasi ham buni qulflaydi.
⛔ `reason` HAR yuzada FARQ QILADI (`vendors.py:105-110`) — jurnalni
o'qiyotgan odam ikki xil o'qishni ajrata olishi kerak.

### B. Tranzaksiya — ⛔ QO'LDA OCHILMAYDI

**Manba:** `services/core-api/app/api/v1/imports.py:1-21` (modul docstringi),
`app/deps.py::get_tenant_session:418-449`
**Qo'llanadi:** daftar importi, hisobot marshrutlari

`TenantSessionDep` sessiyani ALLAQACHON tranzaksiya ichida beradi; ichki
blok D-14 ni FAQAT buzardi. ⚠ Bu qoida mexanik darvoza bilan qulflangan —
qabul mezoni faylni tranzaksiya ochish atamalari bo'yicha grep qiladi va
natija NOL bo'lishi shart, shuning uchun o'sha atamalar izohda ham LITERAL
yozilmaydi (02-08 deviatsiya #3).

### C. Xato javobi — `detail` SATR, reyestrga qo'shilmaydi

**Manba:** `services/core-api/app/api/v1/billing.py:115-134, 137-160`
**Qo'llanadi:** `report_period_too_long`, `report_too_large`, `day_in_future`

```python
def _reject(code: str, http_status: int) -> HTTPException:
    return HTTPException(status_code=http_status, detail=code)
```

⛔ `ALL_BILLING_ERROR_CODES` reyestriga QO'SHILMAYDI: frontend darvozasi
(`scripts/error-codes.test.mjs`) uchala locale'dagi `errorCause`/`errorFix`
juftligini talab qilardi, bu holatlar esa klient yo'lida yuz bermaydi
(tanlagich chegarani o'zi to'sadi).
⛔ `HTTP_422_UNPROCESSABLE_CONTENT` (RFC 9110 nomi), `..._ENTITY` DEPRECATED.

### D. Yurak urishi + «yo'qlikka alert»

**Manba:** `services/core-api/app/jobs/alerting.py:177-196, 681-741`;
`services/core-api/app/api/internal/self_check.py:108-133`
**Qo'llanadi:** `ops/backup/*`, `tests/integration/test_backup_heartbeat.py`

```python
BACKUP_COMPONENT: Final[str] = "backup"
"""8-fazada (FOUND-07) quriladigan zaxira jarayonining yurak urishi.
⚠⚠ QATOR HOZIR UMUMAN YO'Q VA BU AYNAN O'LCHANADIGAN HOLAT."""

HEARTBEAT_STALE_HOURS: Final[int] = 26   # ⚠ 24 EMAS, 26

watched = (
    (BACKUP_COMPONENT, "backup_stale"),
    ...
)
for component, key in watched:
    last_seen = seen.get(component)
    # ⚠⚠ `None` HAM ESKIRISH: qator UMUMAN yozilmagan holat alertga
    #    aylanishi SHART — «alert on absence of a success signal».
    if last_seen is None or moment - last_seen >= stale_after:
        signals.append(_Signal(key, None, _detail(stale_hours=...)))
```

⛔ **HAMMASI ALLAQACHON QURILGAN** — `EXPECTED_COMPONENTS` da `backup`
(`self_check.py:112`), `ALERT_META` da `backup_stale` (`alerting.py:313`,
CRITICAL + `never_suppressed` + `platform_scoped`). Bu faza **faqat yurak
urishini YOZADI**; `alerting.py` va `self_check.py` ga TEGILMAYDI.
⛔ D-25 / Pitfall 15: yangi alert kaliti QO'SHILMAYDI —
`ALERT_TITLE_KEY_COUNT = 15` qulfi (`frontend/scripts/snapshot-copy.test.mjs`)
qizarardi.

### E. Yopiq reyestr + parity darvozasi

**Manba:** `tests/tenancy/test_personal_data_coverage.py:417-460`
(yopiqlik testi), `tests/unit/test_compose_sim_env.py:22-38` (skanerning
ikki qoidasi), `tests/unit/test_heartbeat_registry.py:38-60` (hosila reyestr)
**Qo'llanadi:** har yangi marshrut, har yangi komponent nomi, har yangi
alert kaliti

Uch qoida:
1. yangi element **tanlov qilishga MAJBUR** qiladi (ikki ro'yxatdan biri);
2. eskirgan element ro'yxatda **qololmaydi** (`stale` assertioni);
3. reyestr HOSILA bo'lsa — AST/introspeksiya bilan, qo'lda ro'yxat emas.

### F. i18n — uch locale + lug'at

**Manba:** `frontend/messages/uz-Latn.json` → `frontend/scripts/gen-cyrillic.mjs`
→ `uz-Cyrl.json` (+ `uz-Cyrl.overrides.json`); `frontend/scripts/glossary.test.mjs`
**Qo'llanadi:** `/reports` matnlari VA `xlsx_export._TEXTS`

⛔ Pitfall 18: `i18n:gen` yugurtiriladi (uz-Cyrl **hosila**); taqiqlangan
sinonimlar (`yig'im`, `do'kon`) har locale uchun o'z tokenlari bilan
o'lchanadi. Atamalar: «patta» (`yig'im` EMAS), «rasta» (`do'kon` EMAS) —
7-faza D-30 lug'ati.
⛔ D-06: eksport sarlavhalari vebdagi bilan **BIR XIL atama**;
`xlsx_template._TEXTS:97-167` shakli (`_texts()` noma'lum tilda uz-Latn ga
tushadi, istisno KO'TARILMAYDI).

### G. Pul — `int`, `float` HECH QAYERDA

**Manba:** `billing_repo.py:975-977` (`sum(...)::bigint`),
`billing_repo.py:1057` (`int(row[...])`), `xlsx_template.py:307`
(`write_number`)
**Qo'llanadi:** uchala hisobot, solishtiruv, eksport

⛔ Eksportda pul **`write_number(..., money_format)`**, matn EMAS: Excelda
saralash va yig'indi ishlashi kerak. Sana `write_string` + ISO
(`yyyy-mm-dd`) — WR-07 ning (uch faylda uch xil sana) takrorlanishini
oldini oladi.

---

## No Analog Found

Quyidagi fayllar uchun repo'da yaqin moslik yo'q — planner RESEARCH.md ning
kod misollariga tayansin:

| Fayl | Rol | Ma'lumot oqimi | Sabab |
|---|---|---|---|
| `ops/backup/loop.sh` | scheduler (daemon) | event-driven (poll) | Repo'da bash daemon tsikli yo'q; barcha jadval `taskiq` cron'ida. Manba: **08-RESEARCH.md Code Example 5** (1303-1331) + konseptual analog `app/jobs/capture.py` ning idempotentlik qarori (4-faza D-03). |
| `ops/backup/Dockerfile` | config (image) | — | To'rt mavjud Dockerfile ham **bizning kodimizni** quradi; bu esa tayyor image ustidagi ops qatlami. Faqat `COPY --from=<pinned>` naqshi ko'chadi (`services/core-api/Dockerfile:14`). Manba: **08-RESEARCH.md** (379-389). |
| `tests/integration/test_restore_drill.py` | test (slow) | container lifecycle | Repo'da testcontainers **qo'shimcha** konteyner ko'taradigan test yo'q (`tests/conftest.py` yagona sessiyaviy konteynerni boshqaradi). Manba: **08-RESEARCH.md Code Example 7** (1380-1401). ⚠ `@pytest.mark.slow` + D-26 byudjeti (Pitfall 17). |
| `ops/backup/heartbeat.sql` | raw SQL fayl | CRUD (upsert) | Repo'da `.sql` fayli faqat `ops/db/init/` da (rol/parol bootstrap), ular esa `psql` skriptlari. Upsert shakli `binding_repo.py:540-548` dan, `-v` bog'langan o'zgaruvchi va `ON_ERROR_STOP=1` esa **08-RESEARCH.md Code Example 4** (1284-1299) dan. |

---

## Metadata

**Analog search scope:**
`services/core-api/app/{api,repositories,services,jobs,security}` ·
`migrations/{versions,helpers.py,entities}` ·
`packages/sbozor-core/sbozor_core` · `ops/{docs,scripts,seaweedfs}` ·
`frontend/src/{app,components,lib,scripts}` · `frontend/messages` ·
`tests/{integration,unit,tenancy,fixtures}` · `compose.yaml` · `.env.example`

**Files scanned:** 24 (to'liq o'qilgan yoki nishonli qismlari o'qilgan)

**⚠ RESEARCH.md ning CONTEXT.md ni tuzatgan ikki topilmasi shu xaritada
ham amal qiladi:**
1. `_freeze_zip` **`xlsx_template.py` da EMAS** — u `tests/fixtures/karmana_seed.py:679`
   da; mahsulotga KO'CHIRILADI (§4, Pitfall 3);
2. `PERSONAL_ROUTES` **reyestr emas, HOSILA** (`test_personal_data_coverage.py:313-323`)
   — `/reports/receivables` javobiga `vendor_name` qo'shilishi uni AVTOMATIK
   o'stiradi va bu D-07 ga MOS (§13, Pitfall 1).

**Pattern extraction date:** 2026-08-13
