# Phase 3: NVR avtomatik kashfiyoti va tarmoq ulanishi — Pattern Map

**Mapped:** 2026-08-03
**Files analyzed:** 66 (yangi yoki o'zgaradigan)
**Analogs found:** 52 / 66 (14 tasi uchun **analog yo'q** — §4 ga qarang)

> **Bu hujjatning maqsadi:** ijrochi naqsh o'ylab topmasin — u quyidagi aniq `fayl:qator` dan
> nusxa olsin. Kod parchalari **verbatim** (o'zgartirilmagan, 2026-08-03 holatiga); izohlar
> o'zbekcha.
>
> **BU FAZA UCHTA YANGI SHAKLNI OLIB KELADI VA ULARNING ANALOGI YO'Q:**
> chiquvchi HTTP klienti (`httpx` ishlab chiqarish kodida — bugun faqat testlarda),
> maxfiy qiymatni shifrlab saqlash (`cryptography` **hech qayerda import qilinmagan**),
> va fon-vazifa navbati (`taskiq` — bugun faqat `BackgroundTasks` bor).
> Bu uchtasi uchun **soxta analog ko'rsatilmaydi** — §4 da ochiq tan olingan va
> ularning eng yaqin **strukturaviy qo'shnisi** nomma-nom keltirilgan.
>
> **Eng xavfli to'rt joy** (noto'g'ri qilinsa 1- va 2-fazaning kafolatlari buziladi):
> §S-1 (RLS + `market_id`), §S-4 (marshrut darajasidagi permission + `audit_read` tartibi),
> §S-6 (`nvr_credentials` auditdan CHIQARILADI), §S-7 (parol javobga/jurnalga chiqmasligi).

---

## 0. Umumiy majburiy konventsiyalar (hamma fayl uchun)

| Qoida | Manba | Buzilsa nima bo'ladi |
|-------|-------|----------------------|
| Har bir modul **fayl-darajasidagi docstring** bilan boshlanadi va u "nega shunday" ni tushuntiradi | butun 1–2 faza kodi, masalan `stalls.py:1-65` | Kod review'dan o'tmaydi — bu repoda izoh ixtiyoriy emas |
| Izohlar, docstring'lar, xato matnlari — **o'zbek tilida (uz-Latn)** | `rbac.py:1-34`, `logging.py:1-13` | Uslub ajralib qoladi |
| Python: `from __future__ import annotations` birinchi import | har bir `.py` (masalan `rbac.py:36`) | ruff/mypy konfiguratsiyasi shuni kutadi |
| Python: `__all__` aniq e'lon qilinadi | `rbac.py:46`, `logging.py:24-31`, `tokens.py:40-52` | Import yuzasi nazoratsiz kengayadi |
| Python: `if TYPE_CHECKING:` bloki faqat tip importlari uchun | `rbac.py:43-44`, `audit.py:40-44`, `ratelimit.py:34-35` | Runtime import zanjiri og'irlashadi |
| Backend `import` tartibi: stdlib → uchinchi tomon (`sbozor_core` shu yerda) → `app.*` | `stalls.py:87-120` | ruff `I` qoidasi qizaradi |
| ruff `select = ["E","F","I","UP","B","SIM","ASYNC","S"]`, `line-length = 100`, `target py313` | `pyproject.toml:32-38` | CI `npm run lint` da qizaradi |
| mypy `strict = true` | `pyproject.toml:46-48` | Yangi kod tiplanmasa CI qizaradi |
| Frontend: TSX importlar `react` → uchinchi tomon → `@/...` alias | `temp-password-dialog.tsx:1-8` | eslint qizaradi |
| Frontend: `AGENTS.md` majburiyati — **Next.js 16 hujjatini `node_modules/next/dist/docs/` dan o'qing** yozishdan oldin | `frontend/AGENTS.md` | `middleware.ts` kabi eskirgan API ishlatiladi |
| Vaqt: `timestamptz` + `ZoneInfo("Asia/Tashkent")`; naive `datetime` **TAQIQ** | `sbozor_core/timeutil.py` | `ValueError` |
| Pul: bu fazada pul ustuni **YO'Q** — `FINANCIAL_TABLES` ga birorta jadval qo'shilmaydi | `schema_contract.py:76-84` (2-fazadagi Pitfall 3) | Meta-test soxta `amount_soum` talab qilib qoladi |
| Sir **nomlangan kalit** sifatida uzatiladi, `event` matniga qo'shilmaydi | `logging.py:96-109` | `censor_secrets` uni ko'rmaydi va parol Sentry'ga chiqadi |
| Yangi `detail` kodi **uch joyda** e'lon qilinadi | `schemas.py:471+` · `api-types.ts:791+` · uchala `messages/*.json` | `error-codes.test.mjs` qizaradi yoki foydalanuvchi umumiy xato ko'radi |

---

## 1. File Classification

### 1.1 Backend — sxema qatlami

| Yangi/o'zgaradigan fayl | Rol | Data flow | Eng yaqin analog | Moslik |
|-------------------------|-----|-----------|------------------|--------|
| `packages/sbozor-core/sbozor_core/models/nvr.py` | model | CRUD | `packages/sbozor-core/sbozor_core/models/market.py:204-296` | **exact** |
| `packages/sbozor-core/sbozor_core/models/__init__.py` (MOD) | model-barrel | — | o'zi | **exact** |
| `packages/sbozor-core/sbozor_core/enums.py` (MOD) | enum/config | — | o'zi (`Role`, `StallStatus`) | **exact** |
| `packages/sbozor-core/sbozor_core/schema_contract.py` (MOD) | config/registry | — | o'zi (`AUDITED_TABLES:86-115`) | **exact** |
| `migrations/versions/0012_nvr_domain.py` | migration | DDL + RLS + audit | `migrations/versions/0009_vendors.py` | **exact** |
| `migrations/versions/0013_market_delete_guard.py` (D-17/WR-02) | migration | DDL + funksiya almashtirish | `migrations/versions/0011_weekday_choice.py` + `functions.py:1029-1067` | role-match |
| `migrations/entities/__init__.py` (MOD) | registry | — | o'zi (`VENDOR_TENANT_TABLES:112-121`) | **exact** |
| `migrations/entities/functions.py` (MOD — `market_delete_draft`) | db-function | request-response | o'zi (`MARKET_DELETE_DRAFT:1029-1067`) | **exact** |

### 1.2 Backend — xavfsizlik va sirlar

| Yangi/o'zgaradigan fayl | Rol | Data flow | Eng yaqin analog | Moslik |
|-------------------------|-----|-----------|------------------|--------|
| `services/core-api/app/security/secrets.py` (Fernet/MultiFernet) | security utility | transform | — | **analog yo'q** (§4.1) |
| `services/core-api/app/settings.py` (MOD) | config | — | o'zi (`_validate_jwt_secret:84-92`) | **exact** |
| `services/core-api/app/security/rbac.py` (MOD — Wave 0, D-15) | config/matrix | — | o'zi (`rbac.py:117, 130-143`) | **exact** |
| `services/core-api/app/security/tokens.py` (MOD — jonli ko'rish tokeni) | security utility | request-response | o'zi (`issue_access:86-104`, `decode:137-145`) | **exact** |
| `services/core-api/app/security/audit.py` (MOD — `TABLE_NVR_DEVICES`/`TABLE_CAMERAS`) | security utility | — | o'zi (`audit.py:91-101`) | **exact** |
| `services/core-api/app/security/ratelimit.py` (MOD — `test-connection` sanagichi) | security utility | request-response | o'zi (`_bump:69-80`) | **exact** |
| `packages/sbozor-core/sbozor_core/logging.py` — **O'ZGARTIRILMAYDI, TASDIQLANADI** | security utility | — | o'zi (`SENSITIVE_KEYS:36-63`) | **exact** |

### 1.3 Backend — ISAPI klienti va domen servislari

| Yangi/o'zgaradigan fayl | Rol | Data flow | Eng yaqin analog | Moslik |
|-------------------------|-----|-----------|------------------|--------|
| `services/core-api/app/services/isapi/client.py` (`httpx.DigestAuth`) | service (HTTP klient) | request-response | — | **analog yo'q** (§4.2) |
| `services/core-api/app/services/isapi/parser.py` (XML, namespace-agnostik) | service | transform | `app/services/import_validator.py` (sof transform + strukturalangan xato) | partial |
| `services/core-api/app/services/isapi/errors.py` (xato taksonomiyasi) | service/config | — | `app/schemas.py:471-510` (`MARKET_ERROR_CODES`) + `stalls.py:188-225` | role-match |
| `services/core-api/app/services/isapi/discovery.py` (orkestratsiya) | service | batch | `app/services/staff_accounts.py` / `import_repo.py` (ko'p qatorli upsert) | partial |
| `services/core-api/app/services/rtsp.py` (sof URL fabrikasi) | utility | transform | `packages/sbozor-core/sbozor_core/periods.py` (sof funksiya moduli) | role-match |
| `services/core-api/app/services/go2rtc.py` (+ `assert_safe_go2rtc_src`) | service (HTTP klient) | request-response | — | **analog yo'q** (§4.2) |

### 1.4 Backend — navbat (loyihaning birinchi fon-vazifasi)

| Yangi/o'zgaradigan fayl | Rol | Data flow | Eng yaqin analog | Moslik |
|-------------------------|-----|-----------|------------------|--------|
| `services/core-api/app/worker.py` (taskiq broker + yupqa qobiq) | bootstrap | event-driven | `app/main.py:96-117` (`lifespan` resurs egaligi) | partial |
| `services/core-api/app/jobs/discovery.py` (sof `async def discover_nvr`) | job | batch | `app/security/audit.py:272-306` (`_write_read_audit` — **o'z sessiyasini ochadi**) | partial |

### 1.5 Backend — API qatlami

| Yangi/o'zgaradigan fayl | Rol | Data flow | Eng yaqin analog | Moslik |
|-------------------------|-----|-----------|------------------|--------|
| `services/core-api/app/api/v1/nvr.py` | router | CRUD + 202 job | `services/core-api/app/api/v1/stalls.py` | **exact** |
| `services/core-api/app/api/v1/cameras.py` | router | CRUD + o'qish auditi | `services/core-api/app/api/v1/stalls.py:304-345` (dekorator naqshi) | **exact** |
| `services/core-api/app/api/internal/live_authz.py` (nginx `auth_request`) | router | request-response | `app/main.py:200-234` (`/healthz`, `/readyz` — prefikssiz, RBAC'siz) | partial |
| `services/core-api/app/repositories/nvr_repo.py` | repository | CRUD + upsert | `services/core-api/app/repositories/stall_repo.py` + `import_repo.py` | **exact** |
| `services/core-api/app/schemas.py` (MOD) | schema/DTO | — | o'zi (`ZoneItem:629-660`, `MARKET_ERROR_CODES:471`) | **exact** |
| `services/core-api/app/main.py` (MOD) | bootstrap | — | o'zi (`include_router:133-175`) | **exact** |
| `services/core-api/pyproject.toml` (MOD — Wave 0, D-16) | config | — | o'zi (`pyproject.toml:6-56`) | **exact** |

### 1.6 Simulyator (CAM-09)

| Yangi/o'zgaradigan fayl | Rol | Data flow | Eng yaqin analog | Moslik |
|-------------------------|-----|-----------|------------------|--------|
| `services/nvr-sim/sim/main.py` (FastAPI ISAPI mock) | test uskunasi (servis) | request-response | `app/main.py` (FastAPI ilova shakli) | partial |
| `services/nvr-sim/sim/digest.py` (RFC 7616 **server** tomoni) | test uskunasi | transform | — | **analog yo'q** (§4.3) |
| `services/nvr-sim/sim/state.py` (`/__sim__/` control-plane) | test uskunasi | request-response | — | **analog yo'q** (§4.3) |
| `services/nvr-sim/fixtures/*.xml` (real dumplar) | test fixture | file-I/O | `ops/data/karmana/README.md` + `tests/fixtures/karmana_seed.py` (manba qayd etish odati) | partial |

### 1.7 Infra / ops

| Yangi/o'zgaradigan fayl | Rol | Data flow | Eng yaqin analog | Moslik |
|-------------------------|-----|-----------|------------------|--------|
| `compose.yaml` (MOD — `sim` profili, `worker`, `go2rtc`) | config/ops | — | o'zi (`compose.yaml:53-71` migrate, `180-199` tests) | **exact** |
| `compose.override.yml` (MOD, agar dev porti kerak bo'lsa) | config/ops | — | o'zi | **exact** |
| `ops/go2rtc/go2rtc.yaml` + `go2rtc.sim.yaml` | config/ops | — | `ops/nginx/nginx.conf` (mount qilinadigan `:ro` konfiguratsiya) | role-match |
| `ops/nginx/nginx.conf` (MOD — `/live/` + `auth_request`, `/api/streams` bloklash) | config/ops | request-response | o'zi | **exact** |
| `ops/wireguard/` (konfiguratsiya + README) | config/ops | — | — | **analog yo'q** (§4.4) |
| `.env.example` (MOD) | config | — | o'zi | **exact** |
| `package.json` (MOD — `test:sim`) | config | — | o'zi (`package.json:6-26`) | **exact** |
| `pyproject.toml` (MOD — `sim`/`slow` markerlari) | config | — | o'zi (`pyproject.toml:27-30`) | **exact** |

### 1.8 Frontend

| Yangi/o'zgaradigan fayl | Rol | Data flow | Eng yaqin analog | Moslik |
|-------------------------|-----|-----------|------------------|--------|
| `frontend/src/lib/camera-queries.ts` | data-access hook | request-response + polling | `frontend/src/lib/market-queries.ts:100-250` | **exact** |
| `frontend/src/lib/api-types.ts` (MOD) | schema (zod) + xato reyestri | — | o'zi (`ERROR_CODES:791-838`) | **exact** |
| `frontend/src/lib/rbac.ts` (MOD — `camera_manage` ko'zgusi) | config/matrix | — | o'zi | **exact** |
| `frontend/src/app/[locale]/(app)/cameras/page.tsx` | page (client) | request-response | `frontend/src/app/[locale]/(app)/users/page.tsx` | **exact** |
| `frontend/src/components/cameras/nvr-connect-form.tsx` | component (form) | request-response | `frontend/src/components/users/create-user-dialog.tsx` | **exact** |
| `frontend/src/components/cameras/discovery-progress.tsx` (poll + `nuqs`) | component | polling | `frontend/src/components/import/import-panel.tsx` + `audit/page.tsx` (`Suspense`) | partial |
| `frontend/src/components/cameras/camera-list.tsx` | component (list) | request-response | `frontend/src/components/users/user-list.tsx` | **exact** |
| `frontend/src/components/cameras/nvr-error-banner.tsx` (SC#3 matnlari) | component | — | `frontend/src/components/import/import-errors.tsx` + `lib/market-errors.ts` | **exact** |
| `frontend/src/components/cameras/live-view-dialog.tsx` (go2rtc `video-stream`) | component | streaming | — | **analog yo'q** (§4.5) |
| `frontend/messages/{uz-Latn,ru}.json` (MOD) | i18n | — | o'zi | **exact** |
| `frontend/messages/uz-Cyrl.overrides.json` (MOD) | i18n | — | o'zi | **exact** |
| `frontend/scripts/gen-cyrillic.test.mjs` (MOD — allowlist) | test | — | o'zi (`gen-cyrillic.test.mjs:328`) | **exact** |

### 1.9 Testlar

| Yangi/o'zgaradigan fayl | Rol | Data flow | Eng yaqin analog | Moslik |
|-------------------------|-----|-----------|------------------|--------|
| `tests/tenancy/test_nvr_domain_meta.py` | test (meta) | `pg_catalog` o'qish | `tests/tenancy/test_market_domain_meta.py` | **exact** |
| `tests/tenancy/test_camera_route_coverage.py` (yoki mavjudini kengaytirish) | test (meta) | marshrut-grafi | `tests/tenancy/test_personal_data_coverage.py:129-174` | **exact** |
| `tests/fixtures/nvr_domain.py` | test fixture | seed | `tests/fixtures/market_domain.py` | **exact** |
| `tests/unit/test_isapi_parser.py` (respx) | test (unit) | transform | `tests/unit/test_import_validator.py` | role-match |
| `tests/unit/test_rtsp_url.py` | test (unit) | — | `tests/unit/test_periods.py` | **exact** |
| `tests/unit/test_go2rtc_client.py` | test (unit) | — | `tests/unit/test_jwt.py` (rad etish yo'llari) | role-match |
| `tests/unit/test_nvr_secrets.py` | test (unit) | — | `tests/unit/test_password.py` | role-match |
| `tests/unit/test_sim_fixtures.py` | test (unit) | file-I/O | `tests/unit/test_xlsx_reader.py` | role-match |
| `tests/unit/test_no_sim_branching.py` (grep darvozasi) | test (unit) | — | `tests/integration/test_rate_limit_proxy.py:486-496` (`.env.example` grep darvozasi) | role-match |
| `tests/unit/test_rbac_matrix.py` (MOD) | test (unit) | — | o'zi | **exact** |
| `tests/integration/test_nvr_discovery.py` (`-m sim`) | test (integration) | HTTP e2e | `tests/integration/test_wizard_flow.py` | **exact** |
| `tests/integration/test_nvr_credentials.py` (SC#4 darvozasi) | test (integration) | HTTP e2e | `tests/integration/test_personal_data_audit.py` | **exact** |
| `tests/integration/test_live_view_authz.py` (SC#6) | test (integration) | HTTP e2e | `tests/integration/test_password_gate.py` | role-match |
| `tests/integration/test_market_delete_guard.py` (D-17/WR-02) | test (integration) | constraint | `tests/integration/test_stall_code_reuse.py` | role-match |
| `tests/conftest.py` (MOD — `sim_url` fixture) | test fixture | — | o'zi (`api_client:504-513`) | **exact** |

---

## 2. Shared Patterns — HAMMA fayl uchun (avval shu bo'limni o'qing)

### S-1. Tenant jadvali: `market_id` + RLS ENABLE **va** FORCE + policy + composite FK

**Manba 1 — modeldagi shakl:** `packages/sbozor-core/sbozor_core/models/market.py:272-293` (`Zone` — eng sodda tenant jadvali)

```python
class Zone(Base, TenantMixin, TimestampMixin):
    """Bozor zonasi — YASSI ro'yxat, ierarxiya YO'Q (D-03).
    ...
    """

    __tablename__ = "zones"
    __table_args__ = (
        ForeignKeyConstraint(["market_id"], ["markets.id"], name="fk_zones_market_id_markets"),
        UniqueConstraint("market_id", "name", name="uq_zones_market_id_name"),
        UniqueConstraint("market_id", "id", name="uq_zones_market_id_id"),
        # Import rastalarni zonaga NOM bo'yicha bog'laydi (D-14 validatsiyasi).
        # Bo'sh yoki faqat bo'shliqdan iborat nom hech qachon mos kelmaydi va
        # jimgina "fantom" zona yaratardi.
        CheckConstraint("length(btrim(name)) > 0", name="name_not_blank"),
    )

    id: Mapped[UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(Text(), nullable=False)
```

Uchta majburiy element va ularning sababi (`market.py:219-235` dagi `MarketProfile` bilan bir xil):

| Element | Nima uchun | 3-fazada nimaga tegishli |
|---------|-----------|--------------------------|
| `ForeignKeyConstraint(["market_id"], ["markets.id"], ...)` — `market_id` ustunida **inline `ForeignKey` YO'Q** | `models/base.py::market_fk_column()` docstringi: composite FK bir ustunda ikkita FK hosil qilardi | `nvr_devices`, `cameras`, `nvr_credentials`, `nvr_discovery_runs` — to'rttasi ham |
| `UniqueConstraint("market_id", "id", ...)` | **Composite FK nishoni**: bolalar jadvali `(market_id, nvr_id)` ga havola qiladi va cross-tenant bog'lanish **sxema darajasida** yopiladi | `cameras` va `nvr_discovery_runs` → `nvr_devices` ga aynan shunday havola qiladi |
| Domen `UniqueConstraint` **`market_id` bilan boshlanadi** | Tenant invarianti #5 (`test_tenant_indexes_lead_with_market_id`) | `uq_cameras_market_id_nvr_id_channel_no` — **SC#2 ning DB kafolati** |

**Manba 2 — migratsiyadagi shakl:** `migrations/versions/0009_vendors.py:187-243` (composite FK juftligi)

```python
        sa.ForeignKeyConstraint(
            ["market_id"], ["markets.id"], name="fk_stall_assignments_market_id_markets"
        ),
        # A bozoridagi biriktirish B bozorining rastasiga yoki sotuvchisiga
        # havola qila OLMAYDI — bu RLS emas, SXEMA darajasidagi kafolat
        # (T-02-38). RLS chetlab o'tilishi mumkin bo'lgan har qanday yo'lda
        # (migratsiya, `psql`, xato yozilgan `SECURITY DEFINER`) bu ikki FK
        # baribir turadi.
        sa.ForeignKeyConstraint(
            ["market_id", "stall_id"],
            ["stalls.market_id", "stalls.id"],
            name="fk_stall_assignments_market_id_stall_id_stalls",
        ),
```

**Manba 3 — RLS/policy/audit tsikli:** `0009_vendors.py:250-276`

```python
    # ------------------------------------------------------------------
    # 3. RLS. TARTIB MAJBURIY: ENABLE + FORCE + GRANT -> policy.
    #    `alembic-utils` `ENABLE`/`FORCE` ni BILMAYDI (Pitfall 10) — ularsiz
    #    policy HECH QANDAY ta'sir ko'rsatmaydi va jadval hamma uchun ochiq
    #    bo'ladi.
    # ------------------------------------------------------------------
    for table in VENDOR_TENANT_TABLES:
        enable_tenant_rls(table)
        create_entity(tenant_policy(table))
        create_entity(owner_bootstrap_policy(table))
    ...
    for table in VENDOR_TENANT_TABLES:
        attach_audit_trigger(table)
```

**Manba 4 — reyestr:** `migrations/entities/__init__.py:112-132`

```python
VENDOR_TENANT_TABLES: tuple[str, ...] = (
    "vendors",
    "stall_assignments",
)
"""`0009_vendors` — sotuvchilar va biriktirish davrlari (MARKET-04).
...
"""
...
ALL_TENANT_TABLES: tuple[str, ...] = (
    *TENANT_TABLES,
    *MARKET_DOMAIN_TENANT_TABLES,
    *TEMPORAL_TENANT_TABLES,
    *VENDOR_TENANT_TABLES,
    *CALENDAR_TENANT_TABLES,
)
```

> ⚠ `TENANT_TABLES` (`__init__.py:46-60`) va `RLS_TABLES` (`:62-80`) **MUZLATILGAN** — yangi jadval
> u yerga QO'SHILMAYDI. 3-faza `NVR_TENANT_TABLES` nomli **yangi tuple** qo'shadi va uni
> `ALL_TENANT_TABLES` ga kiritadi.

**YANGI TENANT JADVALI QO'SHGANDA BESH JOY (biri unutilsa CI qizaradi):**

1. `migrations/entities/__init__.py::NVR_TENANT_TABLES` + `ALL_TENANT_TABLES`
2. Migratsiya fayli (`op.create_table` + `enable_tenant_rls` + `tenant_policy` + `owner_bootstrap_policy`)
3. `packages/sbozor-core/sbozor_core/schema_contract.py::AUDITED_TABLES` (**faqat trigger ulanadigan jadval**)
4. `packages/sbozor-core/sbozor_core/models/__init__.py` barreli
5. `tests/fixtures/nvr_domain.py` seed'i

**Darvoza:** `tests/tenancy/test_meta.py::test_every_table_is_tenant_scoped` — u reyestrga **umuman
tayanmaydi**, jadvallarni `pg_catalog` dan o'qiydi (`entities/__init__.py:137-141`). Ya'ni reyestrni
unutish testni **aldamaydi**.

---

### S-2. Migratsiya fayli tuzilishi (`0009_vendors.py` — eng yaqin shablon)

**Yuqoridagi lokal yordamchilar HAR MIGRATSIYADA TAKRORLANADI**, umumiy modulga chiqarilmaydi —
`0009_vendors.py:83-113`:

```python
def _uuid_pk() -> sa.Column[UUID]:
    """PG18 native `uuidv7()` — vaqt-tartiblangan, B-tree do'st."""
    return sa.Column(
        "id",
        pg.UUID(as_uuid=True),
        server_default=sa.text("uuidv7()"),
        nullable=False,
    )


def _market_id() -> sa.Column[UUID]:
    """Tenant kaliti — HAR BIR jadvalda birinchi ustun."""
    return sa.Column("market_id", pg.UUID(as_uuid=True), nullable=False)


def _created_at() -> sa.Column[datetime]:
    return sa.Column(
        "created_at",
        sa.DateTime(timezone=True),
        server_default=sa.text("now()"),
        nullable=False,
    )
```

Sarlavha bloki (`0009_vendors.py:74-78`):

```python
# revision identifiers, used by Alembic.
revision: str = "0009"
down_revision: str | Sequence[str] | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None
```

`downgrade()` — **teskari tartib**, `0009_vendors.py:279-290`:

```python
def downgrade() -> None:
    """Downgrade schema."""
    for table in reversed(VENDOR_TENANT_TABLES):
        detach_audit_trigger(table)

    for table in reversed(VENDOR_TENANT_TABLES):
        drop_entity(owner_bootstrap_policy(table))
        drop_entity(tenant_policy(table))

    op.drop_index(ASSIGNMENT_VENDOR_INDEX, table_name="stall_assignments")
    op.drop_table("stall_assignments")
    op.drop_table("vendors")
```

> ⚠ **Yangi kengaytma kerak bo'lsa** `require_extension("...")` migratsiyaning **birinchi satri**
> bo'ladi va `op.execute("CREATE EXTENSION ...")` **YOZILMAYDI** — sabab `0009_vendors.py:118-136`
> da o'lchangan (`sbozor_owner` `NOCREATEDB`). 3-fazada `cidr`/`inet` — **o'rnatilgan tiplar**,
> kengaytma **kerak emas**.

---

### S-3. Tenant sessiyasi va DI — `Annotated[X, Depends(...)]`

**Manba:** `services/core-api/app/deps.py:418-453`

```python
async def get_tenant_session(
    request: Request,
    principal: CurrentPasswordDep,
) -> AsyncIterator[AsyncSession]:
    """Tenant konteksti O'RNATILGAN sessiya (RESEARCH Code Example §1).

    `market_id` tanlanmagan bo'lsa 409: kontekstsiz so'rov RLS tufayli
    jimgina 0 qator qaytarardi va chaqiruvchi buni "ma'lumot yo'q" deb
    talqin qilardi — bu eng yomon xato turi.
    """
    if principal.market_id is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="market_not_selected",
        )
    ...
    async with _sessionmaker(request)() as session:  # noqa: SIM117
        async with session.begin():
            await set_tenant_context(
                session,
                market_id=principal.market_id,
                actor_id=principal.user_id,
                request_id=principal.request_id,
                actor_kind=ActorKind.USER,
            )
            yield session
        # COMMIT -> GUC'lar `''` bo'ladi -> keyingi so'rov fail-closed.


TenantSessionDep = Annotated["AsyncSession", Depends(get_tenant_session)]
```

**Bu 3-fazada O'ZGARTIRILMAYDI.** Har bir yangi tenant endpointi `session: TenantSessionDep` oladi.

**Router faylining tepasidagi alias:** `stalls.py:128-129`

```python
StallManagerDep = Annotated[Principal, Depends(require_permission(Permission.STALL_MANAGE))]
MarketDataViewerDep = Annotated[Principal, Depends(require_permission(Permission.MARKET_DATA_VIEW))]
```

3-faza uchun: `CameraManagerDep` (`Permission.CAMERA_MANAGE`), `CameraViewerDep`
(`Permission.CAMERA_VIEW`) — **aynan shu shaklda**, router faylining tepasida.

> ⚠ **`ActorKind.SYSTEM` — fon vazifasi uchun.** Kashfiyot jobi HTTP so'rov emas, ya'ni
> `get_tenant_session` unga **ishlamaydi**. Job o'z sessiyasini ochib
> `set_tenant_context(market_id=..., actor_kind=ActorKind.SYSTEM)` chaqiradi. Eng yaqin
> strukturaviy analog — `app/security/audit.py:272-306` (`_write_read_audit`), u ham
> `sessionmaker()` dan **yangi** sessiya ochadi va `commit()` ni o'zi qiladi.

---

### S-4. Marshrut darajasidagi permission + `audit_read` — **e'lon tartibi kafolat**

**Bu 3-fazaning eng ko'p ko'chiriladigan naqshi.** `02-19` o'rnatgan shakl (`stalls.py:28-42`):

```
⚠ HUQUQ TALABI MARSHRUT DEKORATORIDA (`dependencies=[...]`), imzo
parametri sifatida EMAS. FastAPI dekorator darajasidagi bog'liqliklarni
imzo parametrlaridan OLDIN hal qiladi (`fastapi/routing.py` ularni
`dependant.dependencies` ning BOSHIGA qo'yadi), ya'ni 403 olgan so'rov
`audit_read` gacha YETIB BORMAYDI va jurnalda "kim nimani ko'rdi"
degan YOLG'ON DALIL qolmaydi.
```

**Amaldagi shakl:** `stalls.py:304-345`

```python
@router.get(
    "",
    response_model=StallListResponse,
    dependencies=[Depends(require_permission(Permission.VENDOR_VIEW))],
)
async def list_stalls(
    principal: MarketDataViewerDep,
    intent: StallReadIntentDep,
    session: TenantSessionDep,
    query: Annotated[StallQuery, Query()],
) -> StallListResponse:
    """Filtrlangan keyset sahifa (`MARKET_DATA_VIEW` + `VENDOR_VIEW` + o'qish auditi).
    ...
    """
    ...
    intent.filters = _describe(query)
    intent.result_count = len(page.rows)
```

**Intent alias:** `stalls.py:131-134`

```python
StallReadIntentDep = Annotated[
    AuditReadIntent,
    Depends(audit_read(TABLE_STALLS, reason="stall_view")),
]
```

**`reason` HAR YUZADA BOSHQACHA** (`stalls.py:137-140`): jurnalni o'qiyotgan odam
"kim kamera ro'yxatini ko'rdi" va "kim jonli tasvirni ochdi" ni ajratishi kerak.
3-faza uchun: `reason="camera_view"` (ro'yxat) va `reason="live_view"` (jonli, RESEARCH E.15).

> ⚠ **NAZORAT HOLATI MAJBURIY.** `stalls.py:348-369` (`GET /map`) da `audit_read` **ataylab yo'q**
> va sabab kodda yozilgan: javobda shaxsiy ma'lumot yo'q, auditni u yerga yopishtirish jurnalni
> shovqin bilan to'ldirardi. 3-fazada bunday nazorat holati — `GET /nvr-devices` (unda faqat
> `host`/`model`/`has_password` bor). **Jonli ko'rish esa auditda** (RESEARCH E.15: "nizo paytida
> kim ko'rdi").

**`audit_read` fabrikasi (o'zgartirilmaydi):** `app/security/audit.py:309-357` — u
`BackgroundTasks` ga yozadi, ya'ni **422/404 bilan tugagan so'rov iz qoldirmaydi**
(`audit.py:329-338`).

---

### S-5. Xato javoblari — 404 / 403 / 409 / 422 va **uch joyli** kod reyestri

| Holat | Kod | Manba |
|-------|-----|-------|
| Cross-tenant yoki mavjud bo'lmagan resurs | **404** `not_found` | `stalls.py:183-185` |
| Huquq yetmasa | **403** `forbidden` | `deps.py:471-479` |
| Bozor tanlanmagan | **409** `market_not_selected` | `deps.py:428-432` |
| Konflikt (host band, kashfiyot allaqachon ketyapti) | **409** `<code>` | `stalls.py:196-201` |
| Buzuq kursor / shakl | **422** | `stalls.py:330-337` |
| RLS `WITH CHECK` buzilishi | **404** (global handler) | `main.py:178-197` |

`IntegrityError` → aniq `detail`, **faqat `sqlstate` bo'yicha** (`stalls.py:188-207`):

```python
def _stall_conflict(exc: IntegrityError) -> HTTPException:
    """`stalls` yo'lidagi `IntegrityError` -> aniq `detail` kodi.

    Noma'lum SQLSTATE QAYTA KO'TARILADI (`main.py` global handleri uni
    500 ga aylantiradi): "har ehtimolga qarshi" 409 yangi konstraytni
    jimgina noto'g'ri xabar bilan yashirardi.
    """
    state = sqlstate_of(exc)
    if state == UNIQUE_VIOLATION:
        ...
    if state == FK_VIOLATION:
        # Begona bozorning `zone_id`/`category_id` si — javob **404**, 403
        # EMAS: 403 o'sha zona MAVJUDLIGINI tasdiqlardi (T-02-56).
        log.info("stall_reference_not_found", sqlstate=state)
        return _not_found()
    raise exc
```

**Yangi xato kodi UCH JOYDA e'lon qilinadi** (biri unutilsa foydalanuvchi umumiy matn ko'radi):

1. `services/core-api/app/schemas.py:471+` — `MARKET_ERROR_CODES` reyestri
2. `frontend/src/lib/api-types.ts:791-838` — `ERROR_CODES` massivi
3. `frontend/messages/{uz-Latn,ru}.json` + `uz-Cyrl.overrides.json` — matnlar

Drift darvozasi: `frontend/scripts/error-codes.test.mjs` (backend ro'yxatini o'qib frontendni tekshiradi).

> ⚠ **SC#3 shu naqshni KENGAYTIRADI.** `nvr_*` kodlari `MARKET_ERROR_CODES` ga tushadi, LEKIN ular
> `HTTPException(detail=...)` bilan bir qatorda **`nvr_discovery_runs.error_code` ustunida** ham
> yashaydi (RESEARCH E.15: "kod, matn emas"). Ya'ni bitta reyestr **ikki iste'molchiga** xizmat
> qiladi va uni ikkiga bo'lish ikki manba hosil qilardi.

---

### S-6. Audit — uch xil yo'l, aralashtirilmaydi

**Qaysi jadval qaysi yo'ldan boradi (3-faza):**

| Jadval / hodisa | Yo'l | Nima kerak |
|-----------------|------|------------|
| `nvr_devices`, `cameras` | **DB-trigger** | `attach_audit_trigger("<jadval>")` migratsiyada + `AUDITED_TABLES` ga qo'shish |
| **`nvr_credentials`** | **HECH QANDAY TRIGGER** | `AUDITED_TABLES` ga **QO'SHILMAYDI** — pastdagi ogohlantirishga qarang |
| Parol o'zgardi (fakti) | **App-qatlam** | `write_app_audit(action=UPDATE, table_name=TABLE_NVR_DEVICES, new={"credentials_updated": True})` — **qiymatsiz** |
| Kashfiyot ishga tushdi/tugadi | **App-qatlam** | `write_app_audit(...)` + `nvr_discovery_runs` qatori |
| Kamera ro'yxati / jonli ko'rish O'QILDI | **App-qatlam** | `Depends(audit_read(TABLE_CAMERAS, reason="live_view"))` |

> 🔴 **`nvr_credentials` AUDIT TRIGGERIDAN CHIQARILADI — bu qat'iy.**
> Sabab `03-RESEARCH.md` C.10 da o'lchangan: `fn_audit_row()` `to_jsonb(NEW)` yozadi, ya'ni
> **shifrlangan bayt** `audit_log.new_value` ga tushardi. Bu ochiq matn emas, lekin kalit
> buzilganda **tarixiy parollarni** beradi. Yechim — sirni alohida jadvalga ajratib, uni
> triggerdan butunlay chiqarish.
>
> **Bu istisno KO'RINADIGAN bo'lishi shart.** `schema_contract.py:132-140` da allaqachon
> shunday odat bor — istisnolar sababi bilan docstringda sanaladi:
>
> ```python
> RO'YXATGA KIRMAYDIGANLAR va sababi:
>   * `zones`, `stall_categories` — nomlar lug'ati. Ular moliyaviy ham,
>     huquqiy ham yozuv emas; ularga havola qiluvchi jadvallar
>     (`stalls`, `stall_category_periods`) allaqachon auditda.
>   * `stall_code_registry` — birlamchi kaliti `(market_id, code)`, ya'ni
>     unda `id uuid` ustuni YO'Q. `fn_audit_row()` esa `row_id` ni `uuid` ga
>     keltiradi va bunday jadvalda ishga tushirilsa har DML da yiqilardi
> ```
>
> `nvr_credentials` uchun **shu ro'yxatga to'rtinchi band** yoziladi.

**App-qatlam yozuvi (verbatim shakl):** `app/security/audit.py:152-214` (`write_app_audit`).
E'tibor bering — `track_changes=False` o'qish yozuvlari uchun (`audit.py:170-175`).

**Trigger ulash:** `migrations/helpers.py::attach_audit_trigger` — **TALAB**: jadvalning birlamchi
kaliti `id uuid` bo'lishi shart (`schema_contract.py:136-139` dagi izohda sanab o'tilgan sabab).
Ya'ni `nvr_credentials` PK `nvr_id` bo'lsa u baribir triggerga yaramaydi — **ikki mustaqil sabab
bir xil qarorga olib keladi**.

---

### S-7. Sir bilan ishlash — uch qatlamli va **birinchi qatlam allaqachon bor**

**Qatlam 1 — jurnal (MAVJUD, faqat TASDIQLANADI, D-12):** `packages/sbozor-core/sbozor_core/logging.py:36-63`

```python
SENSITIVE_KEYS = frozenset(
    {
        # Parol yo'li
        "password",
        ...
        # HTTP sarlavhalari (middleware ularni butun bir dict sifatida yozishi mumkin)
        "authorization",
        "cookie",
        "set-cookie",
        # NVR rekvizitlari (spec §5 — RTSP parollari shifrlangan saqlanadi)
        "rtsp_password",
        "nvr_password",
    }
)
"""Log'ga HECH QACHON tushmasligi kerak bo'lgan kalitlar (kichik harfda)."""
```

✅ **TASDIQLANDI (kod o'qildi, 2026-08-03):** `rtsp_password` va `nvr_password` `logging.py:60-61`
da **allaqachon bor**, izoh bilan. Filtr **rekursiv** (`logging.py:72-88`) — ichma-ich lug'at va
ro'yxatlarni ham maskalaydi. D-12 ning "tasdiqlash kerak, taxmin qilmaslik" bandi **bajarildi**.

⚠ **Ammo shart bor** (`logging.py:96-101`): filtr faqat **KALIT nomiga** qaraydi. Ya'ni parol
`log.info("nvr_probe", nvr_password=pwd)` shaklida uzatilishi kerak,
`log.info(f"probe {pwd}")` shaklida **emas**. `error_detail` jsonb ham shu qoidaga bo'ysunadi —
undagi xom ISAPI javobi `mask_sensitive` dan o'tadi.

**Qatlam 2 — javob modeli (STRUKTURAVIY):** javob sxemasida parol maydoni **UMUMAN BO'LMAYDI**
(`exclude=True` emas). Manba naqsh — `schemas.py:629-640` (`ZoneItem` — faqat kerakli maydonlar):

```python
class ZoneItem(BaseModel):
    """`GET /zones` qatori va `POST`/`PATCH` javobi.
    ...
    """

    id: UUID
    name: str
    stall_count: int
```

3-faza jufti: `NvrDeviceRead` — `id`, `host`, `port`, `username`, `model`, `has_password: bool`.
**`password` maydoni yo'q.**

**Qatlam 3 — shifr (YANGI, analog yo'q):** §4.1 ga qarang.

**Bir martalik sir UI'da:** `frontend/src/components/users/temp-password-dialog.tsx:10-28`

```tsx
/*
 * =============================================================================
 * VAQTINCHALIK PAROL — BIR MARTA KO'RSATILADI (D-02, T-01-68).
 *
 * Parol butun umri davomida faqat ikki joyda bo'ladi: HTTP javobining
 * tanasida va shu komponentning `props` ida. Dialog yopilganda ota-komponent
 * uni `null` ga o'rnatadi va qiymat React holatidan butunlay chiqib ketadi.
 *
 * ATAYIN QILINMAYDI:
 *   - diagnostika chiqishiga yozish (grep darvozasi bilan qulflangan);
 *   - URL yoki so'rov parametriga qo'yish — u brauzer tarixida va server
 *     kirish jurnalida qolib ketardi;
 *   - brauzer omboriga saqlash (T-01-60 bilan bir xil sabab);
 *   - React Query keshiga tushirish (shuning uchun `useMutation`).
 * =============================================================================
 */
```

> ⚠ **3-fazada bu naqsh TESKARI YO'NALISHDA ishlatiladi.** NVR paroli hech qachon
> **ko'rsatilmaydi** — u faqat **kiritiladi**. Ya'ni `nvr-connect-form.tsx` da parol maydoni
> `useMutation` orqali ketadi (kesh yo'q — `temp-password-dialog.tsx:23` dagi bilan bir xil
> sabab) va formadan keyin `reset()` bilan tozalanadi.

---

### S-8. RBAC matritsasi — ikki nusxa **qo'lda** sinxron (Wave 0 blokeri)

**Backend:** `services/core-api/app/security/rbac.py:112-117`

```python
    # --- Operatsiya (5- va 6-fazalar) ---
    PAYMENT_CREATE = "payment_create"
    REPORT_VIEW = "report_view"
    OCCUPANCY_REVIEW = "occupancy_review"
    DISPUTE_DECIDE = "dispute_decide"
    CAMERA_VIEW = "camera_view"
```

**Amaldagi holat (kod o'qildi, 2026-08-03) — D-15 tasdiqlandi:**

| Rol | `CAMERA_VIEW` | `CAMERA_MANAGE` | Manba |
|-----|---------------|-----------------|-------|
| `PLATFORM_ADMIN` | ❌ **YO'Q** | ❌ mavjud emas | `rbac.py:130-143` |
| `DIRECTOR` | ✅ bor | ❌ mavjud emas | `rbac.py:155` |
| `MARKET_ADMIN` | ✅ bor | ❌ mavjud emas | `rbac.py:175` |
| `CASHIER` / `INSPECTOR` | ❌ | ❌ | `rbac.py:181-184` |

`PLATFORM_ADMIN` qatorining izohi (`rbac.py:124-129`) 2-fazadagi **aynan shu xatoni** hujjatlashtiradi:

```python
    # `STALL_MANAGE`/`TARIFF_MANAGE`/`VENDOR_MANAGE` — 2-fazada QO'SHILDI va
    # ular MARKET-01 uchun MAJBURIY: "platforma admini yangi bozor ustasi
    # orqali bozorni kod yozmasdan kiritadi" talabi ustaning rasta, tarif va
    # sotuvchi qadamlarini o'z ichiga oladi. Ularsiz usta 3-qadamda 403 bilan
    # to'xtardi va sabab endpoint kodida KO'RINMASDI — kod to'g'ri ko'rinib,
    # matritsa jimgina rad etardi (Pitfall 6).
```

**3-fazada aynan shu izoh `CAMERA_VIEW`/`CAMERA_MANAGE` uchun takrorlanadi** — self-service
qoidasi bo'yicha NVR'ni **platforma admini** ulaydi.

**Frontend ko'zgusi:** `frontend/src/lib/rbac.ts` — `PERMISSIONS` massivi va `ROLE_PERMISSIONS`
obyektida **aynan bir xil o'zgarish**. Sinxronlash **qo'lda** (`rbac.py:20-27` dagi majburiyat).

**Darvoza:** `tests/unit/test_rbac_matrix.py::test_every_role_has_entry`.

---

### S-9. Introspektsiya teglari va marshrut-grafi darvozalari

**`require_permission` teg qoldiradi** — `deps.py:481-501`:

```python
    # INTROSPEKTSIYA TEGI — ISH PAYTIDA HECH KIM O'QIMAYDI.
    #
    # Bu atribut xulqqa MUTLAQO ta'sir qilmaydi: darvoza yuqoridagi
    # `if perm not in ...` shartida va faqat o'sha yerda. Teg BITTA
    # iste'molchi uchun bor — `tests/tenancy/test_personal_data_coverage.py`
    # marshrutning bog'liqlik grafini yurib "bu yerda qaysi huquq talab
    # qilingan?" savoliga javob olishi kerak.
    #
    # MUQOBILI MANBA MATNINI REGEX BILAN TIRNASH EDI va u yomonroq:
    # dekorator shakli o'zgarganda ... regex hech nima
    # topmasdi va darvoza JIMGINA yashil bo'lib qolardi — ya'ni unutish
    # xavfsiz tomonga emas, XAVFLI tomonga ishlardi.
    _require.required_permission = perm  # type: ignore[attr-defined]
    return _require
```

`audit_read` ning jufti — `audit.py:359-371` (`_dependency.audit_resource = resource_type`).

**Grafni yurish texnikasi (yangi darvoza shu shakldan nusxa oladi):**
`tests/tenancy/test_personal_data_coverage.py:129-174`

```python
def _walk(routes: Any, *, prefix: str) -> Iterator[tuple[str, Any]]:
    """`app.routes` daraxtini yurib `(to'liq yo'l, marshrut)` juftlarini beradi."""
    for route in routes:
        included = getattr(route, "original_router", None)
        if included is not None:
            context = getattr(route, "include_context", None)
            nested = str(getattr(context, "prefix", "") or "")
            yield from _walk(included.routes, prefix=prefix + nested)
            continue
        path = getattr(route, "path", None)
        if path is None:
            continue
        yield prefix + str(path), route
```

```python
def get_routes(app: FastAPI) -> dict[str, APIRoute]:
    """Yo'l -> `GET` marshruti.

    `APIRoute` FILTRI MAJBURIY: `app.routes` da Starlette avtomatik
    qo'shadigan hujjat marshrutlari ham bor ...
    """
    return {
        path: route
        for path, route in _walk(app.routes, prefix="")
        if isinstance(route, APIRoute) and "GET" in _methods(route)
    }
```

**Uch element majburiy** (`test_personal_data_coverage.py:78-121`):
`EXEMPT_ROUTES` (har istisno **sababi bilan**), `MINIMUM_*_ROUTES` (darvoza bo'shab qolmasin) va
**NAZORAT MARSHRUTI** (`MAP_ROUTE:115-121`) — usiz darvoza o'z qarama-qarshisini himoya qilardi.

> 3-fazada bu texnika ikki darvoza uchun kerak:
> **(a)** har `cameras`/`nvr` `GET` marshrutida `CAMERA_VIEW` e'lon qilinganmi;
> **(b)** javobida hech qanday parol maydoni **YO'Qmi** (`response_field_names()`
> rekursiyasi — `test_personal_data_coverage.py:177-191` — `password`/`password_encrypted`
> nomlarini izlaydi). (b) — SC#4 ning **strukturaviy** darvozasi.

---

### S-10. Frontend — server holati **market-scoped** kalitlar bilan

**Manba:** `frontend/src/lib/market-queries.ts:100-138`

```ts
/**
 * HAR BIR domen kaliti shu yerdan quriladi — `["m", marketId, ...]`.
 *
 * ⚠ GLOBAL KALIT KONSTANTALARI (`ZONES_KEY`, `STALLS_KEY`, ...) ATAYIN
 * O'CHIRILGAN va qaytarilmaydi. Ular qolsa keyingi kod ularni "qulay" deb
 * qayta ishlatardi va bo'shliq jimgina qaytardi — CR-01 ning o'zi aynan shu
 * sinfdagi xato edi. Endi doiralashni chetlab o'tish TS xatosisiz mumkin
 * emas: kalit fabrikasining birinchi argumenti `marketId`.
 * ...
 */
export const domainKey = (marketId: string, ...rest: readonly unknown[]) =>
  ["m", marketId, ...rest] as const;

export const zonesKey = (marketId: string) => domainKey(marketId, "zones");
```

**`useMarketId()` — YAGONA manba:** `market-queries.ts:140-150`

```ts
/**
 * Joriy bozor — kalit qurish uchun YAGONA manba.
 *
 * `useAuthStore()` ni har hookda takrorlash o'rniga bitta joyda o'qiladi:
 * takrorlangan `principal?.marketId ?? null` qatorlari orasidan bittasi
 * tushib qolsa, o'sha hook jimgina global kalitga qaytardi.
 */
function useMarketId(): string | null {
  const { principal } = useAuthStore();
  return principal?.marketId ?? null;
}
```

**Query hook (`enabled` kontrakti):** `market-queries.ts:185-200`

```ts
/**
 * ⚠ `enabled` shartidagi `marketId !== null` QULAYLIK EMAS, kontrakt.
 *
 * Bozorsiz sessiyada domen so'rovi serverda `409 market_not_selected` oladi
 * (`deps.py:408-412`) va o'sha xato kesh grafida yashab qolardi. Aynan shu
 * sababli `marketId` `null` bo'lganda kalitdagi bo'sh satr ham xavfsiz:
 * o'sha kalit ostida hech qachon ma'lumot yozilmaydi.
 */
export function useZonesQuery(options?: { enabled?: boolean }) {
  const marketId = useMarketId();
  return useQuery({
    queryKey: zonesKey(marketId ?? ""),
    queryFn: () => apiFetch(ZONES_PATH, { schema: zoneListResponseSchema }),
    enabled: marketId !== null && (options?.enabled ?? true),
  });
}
```

**Mutatsiya + invalidatsiya:** `market-queries.ts:202-236` (`useCreateZone`, `useUpdateZone`) —
`invalidate(client, [...])` yordamchisi (`:167-171`) **funksiya**, konstanta emas.

**Ikkinchi qatlam — sessiya reset:** `frontend/src/lib/query-provider.tsx:54-73`

```tsx
  /*
   * Sessiya identifikatori o'zgardi -> butun kesh bo'shaydi (CR-01).
   *
   * ⚠ AYNAN `clear()`, TanStack'ning yumshoqroq `reset*` / `remove*`
   * oilasidagi `*Queries` metodlari EMAS: `reset*` variantlari kalitlarni
   * SAQLAB, faol so'rovlarni QAYTA YUKLAYDI ...
   *
   * ⚠ IKKALA CHORA HAM KERAK va biri ikkinchisining o'rnini BOSMAYDI ...
   */
  useEffect(() => subscribeSessionReset(() => client.clear()), [client]);
```

> **3-faza qoidasi:** `camera-queries.ts` **tug'ilishidanoq doiralangan** bo'ladi.
> `camerasKey(marketId)`, `nvrDevicesKey(marketId)`, `discoveryRunKey(marketId, runId)` —
> global konstanta **umuman yaratilmaydi**. `query-provider.tsx` **o'zgartirilmaydi** —
> u yangi kalitlarni avtomatik qamraydi.

---

### S-11. Frontend — sahifa / ro'yxat / dialog uchligi

Bu naqsh 2-fazada to'liq yozilgan: `02-PATTERNS.md` §S-10 va §S-11 **hamon amal qiladi** va
3-fazada o'zgartirilmaydi. Qisqa eslatma:

| Element | Manba |
|---------|-------|
| Sahifa (client, huquq tekshiruvi **so'rovdan oldin**) | `frontend/src/app/[locale]/(app)/users/page.tsx:31-85` |
| URL parametri o'qiydigan sahifa → **`Suspense` MAJBURIY** | `frontend/src/app/[locale]/(app)/audit/page.tsx:25-26, 49-58` |
| Ro'yxat: `isPending` / `isError` / bo'sh / natija **to'rtligi** | `frontend/src/components/users/user-list.tsx:80-133` |
| Forma: `react-hook-form` + zod, `useWatch` (`watch()` **emas**) | `frontend/src/components/users/create-user-dialog.tsx:77-142` |
| DB kontenti **tarjima qilinmaydi** (izoh majburiy) | `user-list.tsx:157-161` |
| Xato → i18n kaliti | `frontend/src/lib/market-errors.ts` (`adminErrorMessageKey`) |

> **3-fazada `discovery-progress.tsx` bir yangi element qo'shadi — poll.**
> `useQuery({ refetchInterval })` bilan `run_id` ni kuzatadi va `nuqs` bilan URL'da saqlaydi
> (RESEARCH E.16: "sahifa yangilanganda poll davom etadi"). `nuqs` + `Suspense` juftligi
> `markets/setup?step=N` da allaqachon ishlaydi — **aynan o'sha shakl**.

---

### S-12. i18n — uch katalog + Cyrillic darvozasi **allowlist**

Uchta katalog: `frontend/messages/uz-Latn.json` (manba), `ru.json` (qo'lda),
`uz-Cyrl.json` (**hosila** — `gen-cyrillic.mjs` yozadi) + `uz-Cyrl.overrides.json` (qo'l tuzatishlari).

**Darvoza va uning allowlist'i:** `frontend/scripts/gen-cyrillic.test.mjs:320-341`

```js
    // Lug'at ATAYIN lotin holida qoldiradigan so'zlar.
    //
    // ⚠ `csv` 02-24 da qo'shildi va sababi `xlsx` bilan AYNAN bir xil:
    // fayl formatining nomi harfma-harf o'girilganda (`цсв`) tanib
    // bo'lmas holga kelardi. Ro'yxat `uz-Cyrl.overrides.json` -> `words`
    // bilan JUFT yuritiladi — biri yangilanib, ikkinchisi unutilsa
    // AYNAN shu test qizaradi.
    const allowed = /SBOZOR|Excel|xlsx|CSV|csv|https?:\/\/\S+|[\w.%+-]+@[\w.-]+/gu;
```

> 🔴 **3-faza bu regexni ALBATTA o'zgartiradi.** Kutiladigan yangi lotin atamalar:
> `NVR`, `RTSP`, `ISAPI`, `IP`, `WireGuard`, `Hikvision`, `go2rtc`, `WebRTC`, `HLS`, `NTP`,
> `DS-7616NI-K2` kabi model kodlari. **Ikki joy juft yuritiladi** (izohda aytilganidek):
> `gen-cyrillic.test.mjs::allowed` **va** `uz-Cyrl.overrides.json -> words`. Biri unutilsa
> shu test qizaradi — bu kutilgan xulq, uni "chetlab o'tish" emas, ikkinchi joyni to'ldirish kerak.

Ikkinchi darvoza (`gen-cyrillic.test.mjs:307-317`): `uz-Cyrl.json` da buzuq shakl
(`Эхcэл`, `хлсх`, ...) bo'lmasligi. Yangi atamalar uchun bu ro'yxatga ham nomzod qo'shiladi
(masalan `РТСП`, `НВР` — ular buzuq shakl).

---

### S-13. Testlar — testcontainers + marker + `api_client`

**Ilova fixture'i (prod kod ishga tushadi, nusxa emas):** `tests/conftest.py:484-513`

```python
    """HAQIQIY `app.main.app`, faqat `app.state` test resurslari bilan to'ldirilgan.

    `lifespan` ishga tushirilmaydi (`ASGITransport` uni chaqirmaydi) —
    aynan shu sababdan ilova resurslari `app.state` da yashaydi va
    dependency'lar ularni modul darajasidagi globaldan emas,
    `request.app.state` dan oladi.
    """
    from app.main import app

    app.state.settings = test_settings
    app.state.engine = api_engine
    app.state.sessionmaker = api_sessionmaker
    app.state.cache = valkey_client
    return app


@pytest.fixture
async def api_client(api_app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    """ASGI transport orqali to'g'ridan-to'g'ri ilovaga so'rov yuboradi.

    Tarmoq, port va uvicorn YO'Q — lekin middleware'lar, dependency'lar,
    Pydantic validatsiyasi va cookie mexanikasi to'liq ishlaydi.
    """
    transport = httpx.ASGITransport(app=api_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
```

> ⚠ **Bu naqsh `nvr-sim` ga MOS KELMAYDI.** `ASGITransport` **tarmoqni chetlab o'tadi**, ya'ni
> `httpx.DigestAuth` handshake'i bajarilmaydi. Sim testi **haqiqiy TCP** orqali `nvr-sim:8080`
> ga boradi — `NVR_SIM_BASE_URL` muhitidan (RESEARCH B.9). Ikkalasi ham kerak va ular
> **turli qatlamlar**.

**Marker reyestri:** `pyproject.toml:27-30`

```toml
addopts = "-q --strict-markers"
markers = [
    "tenancy: tenant izolyatsiyasi (RLS) invariantlari — faza darvozasi, majburiy yashil",
]
```

`--strict-markers` tufayli `-m sim` markeri **avval shu ro'yxatga qo'shilishi shart**, aks holda
test yig'ilish paytida yiqiladi. Modul ichida — `pytestmark = pytest.mark.tenancy`
(`test_personal_data_coverage.py:57`) shaklida.

**`pythonpath`** (`pyproject.toml:15-26`) — `[".", "tests", "services/core-api"]`. `nvr-sim`
kodini testdan import qilish kerak bo'lsa u yerga **to'rtinchi yo'l** qo'shiladi; RESEARCH B.9
esa sim'ga **faqat HTTP orqali** borishni tavsiya qiladi (kod import qilinmaydi) — bu holda
o'zgarish kerak emas.

---

### S-14. Compose profillari — "to'rtinchi konteyner, uchinchi servis emas"

**Profil ro'yxati (fayl boshidagi izoh):** `compose.yaml:1-9`

```yaml
# SBOZOR — yagona orkestratsiya nuqtasi.
# Xost mashinasida `make` YO'Q (Windows) — barcha yorliqlar root `package.json` da.
#
# Profillar:
#   (yo'q)   -> db, cache, core-api    : `npm run up`
#   migrate  -> Alembic one-shot job   : `npm run migrate`
#   web      -> frontend (01-02 rejasi Dockerfile'ni yaratadi)
#   proxy    -> nginx
#   test     -> pytest + testcontainers: `npm run test`
```

**Bir xil kod bazasi, boshqa entrypoint (`migrate` naqshi):** `compose.yaml:53-71`

```yaml
  migrate:
    # One-shot job. Alembic ILOVA STARTUP'ida ishga tushmaydi.
    profiles: ["migrate"]
    build:
      context: .
      dockerfile: services/core-api/Dockerfile
      target: dev
    command: ["alembic", "upgrade", "head"]
    environment:
      # DDL egasi roli — ilova roli EMAS.
      MIGRATION_DATABASE_URL: ${MIGRATION_DATABASE_URL}
      TZ: ${TZ:-Asia/Tashkent}
    working_dir: /app
    volumes:
      - .:/app
    depends_on:
      db:
        condition: service_healthy
```

> **Bu naqsh 3-fazada IKKI MARTA ishlatiladi:**
> **(a)** `worker` — `taskiq worker app.worker:broker`, `target: runtime` (prod konteyneri);
> **(b)** `nvr-sim` — `uvicorn sim.main:app`, `target: dev`, `profiles: ["sim"]`.
> Ikkalasi ham `services/core-api/Dockerfile` ni qayta ishlatadi, ya'ni CLAUDE.md ning
> "aynan 3 ta servis" cheklovi **buzilmaydi** (RESEARCH E.16 va B.9 ikkalasi ham buni
> aniq aytadi).

**Xost portiga publish QILINMAYDI** (`compose.yaml:36-37`, T-01-04). Dev uchun
`compose.override.yml` uni `127.0.0.1` ga bog'laydi. `nvr-sim` va `go2rtc-sim` **hech qachon**
publish qilinmaydi.

**Healthcheck shakli:** `compose.yaml:146-155` (core-api) — `python -c "import urllib.request;..."`.
`nvr-sim` uchun aynan shu shakl (`/__sim__/state` ga).

**npm yorliqlari:** `package.json:6-26`. Yangi yorliq `test:sim` shu ro'yxatga qo'shiladi va
`gate` (`package.json:16`) zanjiriga kiritiladi (aks holda SC#7 "CI'da o'lchanadi" da'vosi
**bajarilmaydi**).

---

## 3. Pattern Assignments — fayl bo'yicha

### 3.1 `packages/sbozor-core/sbozor_core/models/nvr.py` (model, CRUD)

**Analog:** `packages/sbozor-core/sbozor_core/models/market.py:272-293` (`Zone`) va
`:556-577` (`StallAssignment` — composite FK)

**To'rtta klass va ularning shakli:**

| Klass | Mixinlar | `__table_args__` da MAJBURIY |
|-------|----------|------------------------------|
| `NvrDevice` | `Base, TenantMixin, TimestampMixin` | FK→`markets`, `UNIQUE(market_id, id)`, `UNIQUE(market_id, host, port)`, `CHECK` `tunnel_subnet` |
| `NvrCredential` | `Base, TenantMixin` (`TimestampMixin` ixtiyoriy — faqat `updated_at`) | composite FK→`(nvr_devices.market_id, nvr_devices.id)`, PK `nvr_id` |
| `Camera` | `Base, TenantMixin, TimestampMixin` | composite FK→`nvr_devices`, **`UNIQUE(market_id, nvr_id, channel_no)`**, `UNIQUE(market_id, id)`, `UNIQUE(stream_name)` |
| `NvrDiscoveryRun` | `Base, TenantMixin` | composite FK→`nvr_devices`, `UNIQUE(market_id, id)`, **qisman UNIQUE** `WHERE status IN ('queued','running')` |

**Ustun yordamchilari (`models/base.py` dan, o'zgartirilmaydi):**
`uuid_pk()`, `market_fk_column()` (`TenantMixin` orqali), `TimestampMixin`.

> ⚠ **`rtsp_url` ustuni YO'Q** (RESEARCH A.2 / E.15). URL — **hosila**, sof funksiyada
> hisoblanadi. Bu qaror model faylining docstringida **yozilishi shart**, aks holda keyingi
> tahrirlovchi "qulaylik uchun" ustun qo'shadi. Shu uslubning namunasi —
> `market.py:318-362` (`Stall` da `category_id` ustuni **ataylab yo'q** va sabab yozilgan).

> ⚠ **`NvrCredential` da `TenantMixin` BOR, lekin audit trigger YO'Q** (§S-6). Bu ikki
> qaror mustaqil: RLS **kerak** (boshqa bozor shifrmatnni ham ko'rmasin), audit **kerak emas**.

**Barrel:** `packages/sbozor-core/sbozor_core/models/__init__.py` — mavjud shaklga
to'rt yangi nom qo'shiladi (`__all__` va import).

---

### 3.2 `migrations/versions/0012_nvr_domain.py` (migration, DDL + RLS + audit)

**Analog:** `migrations/versions/0009_vendors.py` — **to'liq shablon**, satrma-satr.

**Fayl skeleti (0009 dan verbatim ko'chiriladi, nomlar almashadi):**

```python
"""nvr: qurilma, rekvizit, kamera va kashfiyot yugurishlari + RLS + audit

Revision ID: 0012
Revises: 0011
Create Date: 2026-08-XX

=============================================================================
<NEGA shunday — bu fazaning qat'iy qarorlari shu yerda yoziladi:>
  * `nvr_credentials` ALOHIDA jadval va u AUDIT TRIGGERIDAN chiqarilgan
  * `cameras` da `rtsp_url` ustuni YO'Q — URL hosila
  * `UNIQUE (market_id, nvr_id, channel_no)` — SC#2 ning DB kafolati
=============================================================================
"""
from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

from migrations.entities import NVR_TENANT_TABLES
from migrations.entities.policies import owner_bootstrap_policy, tenant_policy
from migrations.helpers import (
    attach_audit_trigger,
    create_entity,
    detach_audit_trigger,
    drop_entity,
    enable_tenant_rls,
)

revision: str = "0012"
down_revision: str | Sequence[str] | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None
```

**Lokal yordamchilar** — `0009_vendors.py:83-113` dan **verbatim** (`_uuid_pk`, `_market_id`,
`_created_at`, `_updated_at`).

**Jadval yaratish** — `0009_vendors.py:154-170` (`vendors`) shaklida; ustun tartibi
`_market_id()` **birinchi**, keyin `_uuid_pk()`.

**RLS + audit tsikli** — `0009_vendors.py:250-276` dan, LEKIN **ikki alohida ro'yxat bilan**:

```python
    for table in NVR_TENANT_TABLES:            # to'rttasi ham
        enable_tenant_rls(table)
        create_entity(tenant_policy(table))
        create_entity(owner_bootstrap_policy(table))

    for table in NVR_AUDITED_TABLES:           # `nvr_credentials` BU YERDA YO'Q
        attach_audit_trigger(table)
```

**`downgrade()`** — `0009_vendors.py:279-290` shaklida, teskari tartibda.

**Qisman UNIQUE indeks** (bir vaqtda ikki skanni bloklash — RESEARCH E.16):
Alembic buni `op.create_index(..., postgresql_where=...)` bilan quradi. `0009_vendors.py:248`
dagi oddiy indeks chaqiruvi bilan bir xil joyda turadi.

> ⚠ **`ExcludeConstraint` bu fazada KERAK EMAS** — `0009_vendors.py:29-40` dagi ogohlantirish
> (Alembic uni ko'rmaydi) 3-fazaga **tegishli emas**, chunki bu yerda davr (range) tipi yo'q.

---

### 3.3 `migrations/versions/0013_market_delete_guard.py` (D-17 / WR-02 — YUQORI ustuvorlik)

**Analog:** `migrations/entities/functions.py:1029-1067` (`MARKET_DELETE_DRAFT`) +
`migrations/versions/0011_weekday_choice.py` (mavjud funksiyani almashtiruvchi migratsiya).

**Bugungi holat (verbatim, `functions.py:1029-1067`):**

```python
MARKET_DELETE_DRAFT = PGFunction(
    schema="public",
    signature="market_delete_draft(p_market_id uuid)",
    definition="""
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
VOLATILE
AS $$
DECLARE
  v_is_active boolean;
BEGIN
  SELECT m.is_active INTO v_is_active
  FROM public.markets AS m
  WHERE m.id = p_market_id;

  IF v_is_active IS DISTINCT FROM false THEN
    RETURN false;
  END IF;

  DELETE FROM public.stall_assignments          WHERE market_id = p_market_id;
  ...
  DELETE FROM public.markets                    WHERE id = p_market_id;

  RETURN true;
END $$
""",
)
```

**D-17 ikkita mustaqil ishni talab qiladi:**

1. **Kaskadga to'rtta yangi jadval qo'shish** — aks holda `market_delete_draft()` FK buzilishi
   bilan yiqiladi (`nvr_devices` → `markets` FK bor). Tartib muhim: `cameras` va
   `nvr_discovery_runs` va `nvr_credentials` **`nvr_devices` dan oldin** o'chiriladi.
2. **DB darajasidagi cheklov** — hozir "faol bozor o'chirilmaydi" kafolati **faqat funksiya
   tanasidagi `IF`** da. Migratsiya uni sxemaga tushiradi.

**Nima uchun bu shoshilinch (`functions.py:1076-1080` izohi):**

```
`ON DELETE CASCADE` ATAYIN ISHLATILMADI. Kaskad hozir qulay ko'rinardi,
...
```

**Isbot testi:** `tests/integration/test_market_delete_guard.py` — jonli bozorni o'chirishga
urinish **DB darajasida** rad etilishi. Analog: `tests/integration/test_stall_code_reuse.py`
(trigger kafolatini ilova qatlamisiz o'lchaydi).

> ⚠ **`MARKET_DEACTIVATE` funksiyasi YARATILMAYDI.** `functions.py:995-1002` buni ochiq
> taqiqlaydi — teskari yo'lning yo'qligi ikki kafolatning asosi.

---

### 3.4 `services/core-api/app/api/v1/nvr.py` va `cameras.py` (router)

**Analog:** `services/core-api/app/api/v1/stalls.py` — **to'liq shablon**.

**Fayl tepasidagi alias bloki** (`stalls.py:126-145` shaklida):

```python
router = APIRouter(tags=["nvr"])

NvrManagerDep = Annotated[Principal, Depends(require_permission(Permission.CAMERA_MANAGE))]
CameraViewerDep = Annotated[Principal, Depends(require_permission(Permission.CAMERA_VIEW))]

CameraReadIntentDep = Annotated[
    AuditReadIntent,
    Depends(audit_read(TABLE_CAMERAS, reason="camera_view")),
]
LiveViewIntentDep = Annotated[
    AuditReadIntent,
    Depends(audit_read(TABLE_CAMERAS, reason="live_view")),
]
```

**`_market_id` / `_not_found` yordamchilari** — `stalls.py:173-185` dan **verbatim**:

```python
def _market_id(principal: Principal) -> UUID:
    """Tanlangan bozor (`zones.py` / `users.py` dagi jufti bilan aynan bir xil)."""
    if principal.market_id is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="market_not_selected",
        )
    return principal.market_id


def _not_found() -> HTTPException:
    """Cross-tenant va mavjud bo'lmagan rasta uchun BIR XIL javob (T-02-55)."""
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_NOT_FOUND)
```

**Marshrutlar va ularning naqshi:**

| Marshrut | Naqsh manbai | Diqqat |
|----------|--------------|--------|
| `POST /nvr-devices` | `stalls.py:430-464` (`create_stall`) | 409 `nvr_host_taken` (`UNIQUE(market_id, host, port)`) |
| `PATCH /nvr-devices/{id}` | `stalls.py:467-492` (`update_stall`) | **`exclude_unset=True` MAJBURIY** (`stalls.py:476-478`) |
| `POST /nvr-devices/test-connection` | `app/api/v1/auth.py` (rate-limit ostidagi endpoint) | **yozuv YARATMAYDI**, rate-limit ostida (§S-5, RESEARCH E.16) |
| `POST /nvr-devices/{id}/discover` | — | **202 Accepted** + `{"run_id": ...}`; 409 agar faol skan bor |
| `GET /nvr-devices/{id}/discovery-runs/{run_id}` | `stalls.py:392-427` (`get_stall`) | Poll nishoni; `audit_read` **yo'q** (shaxsiy ma'lumot emas) |
| `GET /cameras` | `stalls.py:304-345` | `CAMERA_VIEW` + `audit_read(reason="camera_view")` |
| `POST /cameras/{id}/live-token` | — | `CAMERA_VIEW` **dekoratorda** + `audit_read(reason="live_view")` |
| `DELETE /cameras/{id}` → **soft-delete** | — | D-10: `is_archived = true`; **`DELETE` hech qachon** |

> ⚠ **MARSHRUT TARTIBI** (`stalls.py:3-11`): statik segmentli yo'l (`/test-connection`)
> `{id}` shablonidan **OLDIN** e'lon qilinadi. Teskari tartibda `"test-connection"` UUID
> emas deb 422 berilardi va **ikkala marshrut ham to'g'ri yozilgan bo'lib turardi**.

> ⚠ **`market_id` HECH QACHON SO'ROV TANASIDAN OLINMAYDI** (`stalls.py:47-49`) —
> `NvrDeviceCreateRequest` da bunday maydon **umuman e'lon qilinmaydi**.

**Router ulash:** `app/main.py:133-175` shaklida, **2-faza bloki izohi bilan birga**
(`main.py:138-147`) — yangi marshrut `tests/tenancy/test_cross_tenant.py` matritsasiga
**avtomatik** tushadi, LEKIN ikki qo'lda qadam bor: `PARAM_FILLERS` (yo'l parametri) va
`BODY_FILLERS` (tana). Bu 3-fazada ham **aynan shunday**.

---

### 3.5 `services/core-api/app/repositories/nvr_repo.py` (repository)

**Analog:** `services/core-api/app/repositories/stall_repo.py` (tenant-scoped repozitoriy)
+ `app/repositories/import_repo.py` (ko'p qatorli upsert va `inserted`/`skipped` hisoblagichlari).

**Baza klass** (`packages/sbozor-core/sbozor_core/tenancy.py:117-166`):

```python
class TenantScopedRepository:
    """Repozitoriylar uchun baza — IKKINCHI qatlam filtri.

    RLS himoya to'ri bo'lsa ham, so'rovga `market_id` predikatini qo'shish
    majburiy (P9). ...
    """

    def __init__(self, session: AsyncSession, market_id: UUID) -> None:
        self.session = session
        self.market_id = market_id
```

**Upsert (SC#2 ning yuragi)** — RESEARCH A.4 dagi SQL. Xom `text()` yozilganda bind
parametrlari **tiplanadi** (`audit_repo.py:238-256` naqshi, `02-PATTERNS.md` §S-7 da keltirilgan):

```python
_PLATFORM_AUDIT = text(
    "SELECT id, at, business_date, ... FROM auth_list_platform_audit(:limit, :before_at, :before_id)"
).bindparams(
    bindparam("limit", type_=Integer()),
    bindparam("before_at", type_=DateTime(timezone=True)),
    bindparam("before_id", type_=BigInteger()),
)
```

3-fazada bu **majburiy**: `cidr`/`inet`/`jsonb` qiymatlari `text()` da tipsiz uzatilsa
asyncpg'ga xom `str`/`dict` bo'lib borardi.

**Sirni yozish/o'qish** repozitoriyda emas, **servis qatlamida** (`app/security/secrets.py`)
shifrlanadi va repozitoriy faqat `bytes` ni ko'radi — `user_repo.py` parolni hash bo'lgan holda
qabul qilgani bilan bir xil chegara.

---

### 3.6 `services/core-api/app/services/isapi/*` (ISAPI klienti)

**Analog:** yo'q (§4.2). Quyidagilar — **strukturaviy qo'shnilar** va ular qaysi jihatdan
ko'chiriladi:

| Jihat | Qaysi mavjud fayldan | Nima ko'chiriladi |
|-------|----------------------|-------------------|
| Sof transform + strukturalangan xato | `app/services/import_validator.py:58-70, 160` | Xato **kodi** mashina uchun barqaror, matni foydalanuvchi uchun; ikkisi ajratilgan |
| Xato taksonomiyasi reyestr sifatida | `app/schemas.py:471-510` (`MARKET_ERROR_CODES`) | Kodlar **bir joyda**, sabablari izohda guruh-guruh |
| Rad etish yo'llarining testi | `tests/unit/test_jwt.py` | Har rad etish yo'li **alohida test** |
| Klient resursi `app.state` da | `app/main.py:105-111` | `httpx.AsyncClient` **lifespan'da** ochiladi va `app.state` ga qo'yiladi (`Redis` bilan bir xil) |
| Klient yopilishi | `app/main.py:112-116` | `finally: await client.aclose()` |

**Kutubxona qarori (RESEARCH A.3, muzokara qilinmaydi):**

```python
auth = httpx.DigestAuth(username, password)
async with httpx.AsyncClient(auth=auth, timeout=httpx.Timeout(10.0, connect=5.0)) as client:
    ...
```

`timeout=None` **HECH QACHON** — job osilib qoladi. `follow_redirects=False`.
Bitta klient butun kashfiyot davomida qayta ishlatiladi (25 kanal × 2 borish tejaladi).

**Retry siyosati TESKARI (D-03, RESEARCH A.3):**

| Xato sinfi | Retry |
|-----------|-------|
| Tarmoq (timeout, connection reset, 5xx) | ✅ `tenacity`, eksponensial, ≤3 urinish |
| `401` / autentifikatsiya | ❌ **HECH QACHON** — hisobni qulflaydi |

Bu qoida `app/security/ratelimit.py:1-25` dagi mulohaza bilan bir oilada: "chegara qo'yish"
va "narxni oshirish" turli qatlamlar. Ammo bu yerda **teskari** — chegara **bizning
tomonimizda emas, NVR tomonida** va uni bosish **foydalanuvchini qulflaydi**.

**XML namespace (RESEARCH Pitfall 2 — VERIFIED):** parser namespace-agnostik bo'ladi
(yorliqdan `{...}` prefiksi olib tashlanadi). Aks holda `find("deviceType")` **`None`
qaytaradi va parser jimgina bo'sh natija beradi** — bu eng ko'p uchraydigan integratsiya xatosi.

---

### 3.7 `services/core-api/app/services/go2rtc.py` (go2rtc klienti)

**Analog:** yo'q (§4.2). **Lekin bitta funksiya to'liq spetsifikatsiyalangan** (RESEARCH D.13):

```python
_ALLOWED_STREAM_SCHEME = "rtsp://"

def assert_safe_go2rtc_src(src: str) -> None:
    """go2rtc `src` — FAQAT rtsp://. `exec:`/`ffmpeg:` = RCE (GHSA-wwww-5h25-jf98)."""
    if not src.startswith(_ALLOWED_STREAM_SCHEME):
        raise ValueError("unsafe_go2rtc_source")
```

**Darvoza testi:** `tests/unit/test_go2rtc_client.py::test_rejects_exec_source` —
`exec:`, `ffmpeg:`, `echo:` bilan boshlanuvchi `src` rad etilishi.

Bu darvozaning uslubiy analogi — `packages/sbozor-core/sbozor_core/security.py:6-11` dagi
"nima ATAYIN ishlatilmaydi" bloki: **taqiq sababi bilan kodda yoziladi**, chunki keyingi
tahrirlovchi "qulaylik uchun" cheklovni olib tashlashi mumkin.

---

### 3.8 `services/core-api/app/worker.py` + `app/jobs/discovery.py` (navbat)

**Analog:** yo'q (§4.3). Ikki mavjud shakl birlashtiriladi:

**(a) Resurs egaligi — `app/main.py:96-117`:**

```python
@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    """Ulanish pullarini ilova hayoti davomida bir marta ochadi va yopadi."""
    settings: Settings = get_settings()
    configure_logging(settings.log_level)
    ...
    engine: AsyncEngine = make_engine(settings.database_url)
    cache: Redis = Redis.from_url(settings.valkey_url)

    application.state.settings = settings
    application.state.engine = engine
    application.state.sessionmaker = make_sessionmaker(engine)
    application.state.cache = cache
    try:
        yield
    finally:
        await cache.aclose()
        await engine.dispose()
```

Worker jarayonida `app.state` **yo'q** — u taskiq broker'ning startup/shutdown ilgaklarida
o'z `engine`/`sessionmaker` ini quradi. Manbadan ko'chiriladigan narsa — **egalik shakli**:
resurs bir marta ochiladi, `finally` da yopiladi.

**(b) O'z sessiyasini ochadigan kod — `app/security/audit.py:272-306`:**

```python
async def _write_read_audit(
    sessionmaker: async_sessionmaker[AsyncSession],
    principal: Principal,
    intent: AuditReadIntent,
) -> None:
    """O'qish yozuvini YANGI sessiyada va alohida tranzaksiyada yozadi.

    Xato YUTILADI (log'ga yozib): bu kod javob mijozga JO'NATILGANDAN
    KEYIN ishlaydi ...
    """
    try:
        async with sessionmaker() as session:
            await write_app_audit(...)
            await session.commit()
    except SQLAlchemyError as exc:
        log.error("audit_read_write_failed", ...)
```

Bu **loyihadagi yagona** "so'rov konteksti tashqarisidagi DB yozuvi" naqshi va kashfiyot jobi
undan ikki narsani oladi: `sessionmaker()` dan yangi sessiya + `commit()` ni o'zi qilish.

**FARQ (job'da MAJBURIY, `_write_read_audit` da yo'q):** job `set_tenant_context(...)` ni
**o'zi chaqiradi** — `deps.py:442-448` dagi chaqiruv bilan bir xil, lekin
`actor_kind=ActorKind.SYSTEM` bilan. Busiz RLS 0 qator beradi va job jimgina "hech nima
topmadi" deb tugaydi.

**D-06 ning qat'iy sharti:** job **sof `async def discover_nvr(nvr_id, run_id, market_id) -> None`**
funksiya bo'ladi, taskiq dekoratori esa `app/worker.py` da **yupqa qobiq**. Ya'ni
`app/jobs/discovery.py` da `taskiq` **import qilinmaydi**. Ko'chirish narxi ~10 qator.

---

### 3.9 `services/core-api/app/security/secrets.py` (Fernet)

**Analog:** yo'q (§4.1). Uslubiy qo'shni — `packages/sbozor-core/sbozor_core/security.py:44-63`:

```python
# ---------------------------------------------------------------------------
# Parol
# ---------------------------------------------------------------------------

# Modul darajasidagi BITTA instans: `PasswordHash.recommended()` Argon2id ni
# OWASP tavsiya qilgan parametrlar bilan quradi. Har chaqiruvda qayta qurish
# keraksiz ish va parametrlar drift qilishiga yo'l ochadi.
_hasher = PasswordHash.recommended()
```

va sozlama validatori — `app/settings.py:84-92`:

```python
    @field_validator("jwt_secret")
    @classmethod
    def _validate_jwt_secret(cls, value: str) -> str:
        if len(value.encode("utf-8")) < MIN_JWT_SECRET_BYTES:
            raise ValueError(
                f"JWT_SECRET kamida {MIN_JWT_SECRET_BYTES} bayt bo'lishi kerak. "
                'Hosil qilish: python -c "import secrets;print(secrets.token_urlsafe(48))"'
            )
        return value
```

**Ko'chiriladigan uch qoida:**

1. **Instans modul darajasida bir marta** (`_hasher` naqshi) — `MultiFernet` har chaqiruvda
   qayta qurilmaydi.
2. **Kalit formati startup'da tekshiriladi** (`_validate_jwt_secret` naqshi) — noto'g'ri
   `NVR_CREDENTIAL_KEY` **ishga tushishda** yiqilsin, birinchi kamera qo'shilganda emas.
   Xato matnida **hosil qilish buyrug'i** beriladi (yuqoridagi satr shaklida).
3. **Kalit `JWT_SECRET` dan ALOHIDA** — ikki xil xavf modeli (`settings.py:3-5` dagi
   "sirlar hech qachon kodda emas" qoidasi ikkalasiga ham qo'llanadi).

**`Settings` ga qo'shiladigan maydonlar** (`settings.py:36-43` bloki shaklida):

```python
    # --- NVR rekvizitlari (03-XX, SC#4) ---
    nvr_credential_key: str
    nvr_credential_keys_retired: str = ""     # vergul bilan ajratilgan, ixtiyoriy
```

---

### 3.10 `services/nvr-sim/` (simulyator)

**Analog:** yo'q (§4.3). Faqat **shakl** `app/main.py` dan olinadi (FastAPI ilovasi, `lifespan`,
`healthz` ga o'xshash `/__sim__/state`).

**Uchta qat'iy chegara:**

| Chegara | Manba | Darvoza |
|---------|-------|---------|
| Sim **prodga chiqmaydi** | `compose.yaml` `profiles: ["sim"]` (`compose.yaml:161` — `frontend` da bir xil shakl) | `docker compose up` profilsiz uni ishga tushirmaydi |
| Ilova kodida **sim tarmoqlanishi yo'q** | RESEARCH B.9 | `tests/unit/test_no_sim_branching.py` — `services/core-api/app/` ichida `nvr-sim`, `__sim__`, `SIM_` satrlari **umuman uchramaydi** |
| Fixture'lar **haqiqiy dumpdan** | RESEARCH B.7 | `tests/unit/test_sim_fixtures.py` — har fixture XML sifatida parse bo'lishi, Hikvision namespace'iga va **manba izohiga** ega bo'lishi |

**Grep-darvoza naqshi mavjud:** `tests/integration/test_rate_limit_proxy.py:486-496`

```python
    """`.env.example` ham `*` tarqatmaydi — u har bir dev'ning `.env` iga ko'chadi."""
        assert value != "*", "`.env.example` `*` tarqatmasligi shart"
```

`test_no_sim_branching.py` **aynan shu sinfdagi** test: konfiguratsiya/kod matnini o'qib
taqiqlangan satrni izlaydi.

**Fixture manbasini qayd etish odati** — `ops/data/karmana/README.md` va
`tests/fixtures/karmana_seed.py:43` (determinizm sababi izohda). Har `*.xml` fayl boshida
**XML izohi** bilan manba, sana va qurilma modeli yoziladi.

---

### 3.11 `compose.yaml` (MOD) — `sim` profili + `worker` + `go2rtc`

**Analog:** `compose.yaml:53-71` (`migrate`) va `:180-199` (`tests`).

**Fayl boshidagi profil ro'yxati YANGILANADI** (`compose.yaml:1-9`) — u hujjat, uni eskirtirish
keyingi o'quvchini adashtiradi:

```yaml
#   sim      -> nvr-sim + go2rtc-sim (CAM-09)  : `npm run test:sim`
```

**`tests` konteyneriga yangi muhit** (`compose.yaml:187-193` bloki):

```yaml
      NVR_SIM_BASE_URL: "http://nvr-sim:8080"
```

**Healthcheck** — `compose.yaml:146-155` shaklida (`python -c "import urllib.request;..."`).

**Xost portiga publish YO'Q** (`compose.yaml:36-37` qoidasi) — `nvr-sim`, `go2rtc-sim` va
prod `go2rtc` **hech qachon** publish qilinmaydi. go2rtc'ning WebRTC UDP 8555 i **firewall
darajasida** ochiladi, compose `ports:` bilan emas.

**`worker` konteyneri** `target: runtime` bilan (`compose.yaml:72-76` shaklida) — u prod
konteyneri, `migrate`/`tests` esa `dev`.

---

### 3.12 `ops/nginx/nginx.conf` (MOD) — `auth_request` + go2rtc API bloklash

**Analog:** o'zi (mavjud fayl). Ikkita yangi blok:

1. `/live/` → `auth_request /internal/live-authz` → `proxy_pass http://go2rtc:1984`
2. `/api/streams`, `/api/config`, `/api/restart` → **`return 403`** (RESEARCH D.13, 1-qoida)

> ⚠ **`X-Forwarded-For` mexanikasi bu faylda ALLAQACHON nozik** (`compose.yaml:79-116` da
> to'liq o'lchangan): nginx `$remote_addr` bilan **ustiga yozadi** va uvicorn
> `--forwarded-allow-ips` ni **aniq oralik** bilan oladi. Yangi `location` bloki bu
> sozlamalarga **tegmasligi** shart — aks holda `audit_log.ip` soxta qiymat yozadi va
> rate-limit chetlab o'tiladi (01-13 regressiyasi).

---

### 3.13 `frontend/src/lib/camera-queries.ts`

**Analog:** `frontend/src/lib/market-queries.ts:100-250` — **to'liq shablon** (§S-10).

**Tug'ilishidanoq doiralangan kalitlar:**

```ts
export const nvrDevicesKey = (marketId: string) => domainKey(marketId, "nvr-devices");
export const camerasKey = (marketId: string, nvrId: string | null) =>
  domainKey(marketId, "cameras", nvrId);
export const discoveryRunKey = (marketId: string, runId: string) =>
  domainKey(marketId, "discovery-run", runId);
```

`domainKey` **`market-queries.ts` dan import qilinadi** — ikkinchi nusxa yaratilmaydi
(`market-queries.ts:104-108` dagi ogohlantirish aynan shu sinfdagi xato haqida).

**Poll hooki (yangi element):**

```ts
export function useDiscoveryRunQuery(runId: string | null) {
  const marketId = useMarketId();
  return useQuery({
    queryKey: discoveryRunKey(marketId ?? "", runId ?? ""),
    queryFn: () => apiFetch(`${NVR_PATH}/discovery-runs/${runId}`, { schema: discoveryRunSchema }),
    enabled: marketId !== null && runId !== null,
    refetchInterval: (query) =>
      query.state.data?.status === "running" || query.state.data?.status === "queued" ? 2000 : false,
  });
}
```

`enabled` shartining sababi — `market-queries.ts:186-192` dagi izoh (409 keshda yashab qolardi).

**Parol yuboradigan mutatsiya `useMutation` bo'ladi**, `useQuery` **emas** —
`temp-password-dialog.tsx:23` dagi bilan bir xil sabab ("React Query keshiga tushirish" taqiqi).

---

### 3.14 Testlar — `tests/tenancy/test_nvr_domain_meta.py`

**Analog:** `tests/tenancy/test_market_domain_meta.py` (1065 qator) — u `pg_catalog` dan
o'qiydi va **modelga tayanmaydi**.

Bu faza uchun kamida to'rt yangi invariant:

| Invariant | Nima uchun |
|-----------|-----------|
| `cameras` da `UNIQUE (market_id, nvr_id, channel_no)` mavjud | SC#2 ning **yagona** DB kafolati |
| `nvr_credentials` da audit trigger **YO'Q** | §S-6 — shifrmatn auditga tushmasin |
| `cameras` da `rtsp_url` nomli ustun **YO'Q** | RESEARCH A.2 — URL hosila; ustun qo'shilsa ikki manba paydo bo'ladi |
| `nvr_discovery_runs` da qisman UNIQUE (`queued`/`running`) mavjud | Bir vaqtda ikki skan bloklanadi |

Umumiy invariantlar (`market_id`, RLS ENABLE+FORCE, policy, indeks birinchi ustuni) —
`tests/tenancy/test_meta.py` **avtomatik** qamraydi, chunki u jadvallarni `pg_catalog` dan
oladi (`entities/__init__.py:137-141`).

---

## 4. No Analog Found — **analog yo'q**

> Bu bo'lim ataylab batafsil: soxta analog ko'rsatish **admitted gap dan yomonroq**, chunki
> ijrochi unga ergashadi.

### 4.1 Shifrlash (`app/security/secrets.py`) — **analog yo'q**

**O'lchov (2026-08-03, `grep -rn "from cryptography" --include=*.py .`): NOL natija.**
`cryptography==49.0.0` `services/core-api/pyproject.toml:17` da e'lon qilingan, lekin
**hech qayerda import qilinmagan**. Ya'ni bu loyihada **birinchi marta** maxfiy qiymat
shifrlanadi.

**Eng yaqin strukturaviy qo'shni:**

| Nima | Fayl | Nimasi o'xshash / nimasi boshqa |
|------|------|--------------------------------|
| Parol hashlash | `packages/sbozor-core/sbozor_core/security.py:44-63` | ✅ Modul darajasidagi bitta instans, ✅ "nima ATAYIN ishlatilmaydi" bloki. ❌ **Bir tomonlama** — teskari o'girish yo'q, ya'ni kalit rotatsiyasi muammosi umuman yo'q |
| Sir formatini startup'da tekshirish | `app/settings.py:84-92` | ✅ To'liq ko'chiriladi (`field_validator` shakli, xato matnida hosil qilish buyrug'i) |
| Sirni jurnaldan olib tashlash | `packages/sbozor-core/sbozor_core/logging.py:36-113` | ✅ Allaqachon `nvr_password` ni biladi (§S-7) |

**Nima o'ylab topiladi (analog yo'q):** `MultiFernet` qurish, kalit rotatsiyasi
(`NVR_CREDENTIAL_KEYS_RETIRED`), `bytea` ustuniga yozish/o'qish chegarasi.
`cryptography` bu API'ni **o'zi beradi** — hand-roll qilinmaydi (RESEARCH C.10).

### 4.2 Chiquvchi HTTP klienti (ISAPI, go2rtc) — **analog yo'q**

**O'lchov (2026-08-03): `httpx` `services/` va `packages/` ichida NOL marta import qilingan.**
24 ta fayl uni ishlatadi va **hammasi `tests/` ichida** (`tests/conftest.py:505-513`,
`tests/fixtures/auth_api.py`, integratsiya testlari). `pyproject.toml:53` — u
**`[dependency-groups] dev` da**.

> 🔴 **D-16 / Wave 0:** ISAPI klienti **ishlab chiqarish kodi**. `httpx` `[project] dependencies`
> ga ko'chirilmasa — **hamma testlar yashil bo'lgani holda deploy'da `ModuleNotFoundError`**.
> Bu birinchi migratsiyadan **oldin** bajariladi.

**Eng yaqin strukturaviy qo'shni:** `redis.asyncio.Redis` — u ham tashqi tarmoq klienti va
u ham `lifespan` da ochilib `app.state` ga qo'yiladi (`app/main.py:106, 111, 115`). Undan
ko'chiriladigan narsa — **egalik va yopilish**, so'rov mexanikasi emas.

**Nima o'ylab topiladi:** Digest handshake mexanikasi, timeout byudjeti, retry siyosati,
XML parse, xato taksonomiyasi. Bularning **hammasi** `03-RESEARCH.md` §A da spetsifikatsiyalangan —
ijrochi o'ylab topmaydi, tadqiqotdan oladi.

### 4.3 Fon-vazifa navbati (`taskiq`) va simulyator — **analog yo'q**

**O'lchov:** loyihada `arq`, `taskiq`, `celery`, `scheduler` — **nol**. Yagona fon mexanizmi —
FastAPI ning `BackgroundTasks` i (`app/security/audit.py:31, 341-357` va
`app/api/v1/users.py:273, 313, 333`), u esa **so'rov ichida yashaydi** va jarayon o'lsa yo'qoladi.

`compose.yaml` da hech qanday worker konteyneri yo'q — bugungi konteynerlar: `db`, `cache`,
`migrate`, `core-api`, `frontend`, `nginx`, `tests`.

**Eng yaqin strukturaviy qo'shni:** §3.8 dagi ikkilik (`main.py::lifespan` egaligi +
`audit.py::_write_read_audit` ning "o'z sessiyasi").

**Simulyator uchun:** `services/nvr-sim/` — repoda **birinchi** to'rtinchi Python paketi
(`core-api`, `sbozor-core`, `migrations` dan keyin). RFC 7616 **server tomoni** loyihada
umuman yo'q (`PyJWT` bor, `pwdlib` bor — ikkalasi ham boshqa protokol).

### 4.4 WireGuard (`ops/wireguard/`) — **analog yo'q**

Repoda tarmoq darajasidagi izolyatsiya **umuman yo'q**: `ops/` ichida faqat `db/init/`,
`nginx/`, `data/karmana/`. `network_mode: host`, `cap_add: NET_ADMIN`, `/lib/modules` mount —
`compose.yaml` da bunday konstruksiya **hech qachon ishlatilmagan**.

**Eng yaqin qo'shni:** `compose.yaml:36-37` va `compose.override.yml:1-9` — "xost portiga
publish qilmaslik" qarori. Falsafa bir xil (tarmoq yuzasini toraytirish), mexanizm butunlay boshqa.

**SC#5 ning isbot testi ham analogsiz.** RESEARCH C.11 buni **konteyner tarmoq qoidasi** bilan
isbotlashni tavsiya qiladi (tunnelni o'chirib emas) — bu test infratuzilma darajasida va
`tests/` dagi birorta mavjud test unga o'xshamaydi.

### 4.5 Jonli oqim UI (`live-view-dialog.tsx`) — **analog yo'q**

Frontendda video, `<video>` elementi, WebRTC yoki media komponenti **yo'q**. Eng yaqin
qo'shni — `frontend/src/components/ui/dialog.tsx` (Radix qobig'i) va
`create-user-dialog.tsx:145-154` (dialog razmetkasi). Ya'ni **dialog qobig'i** ko'chiriladi,
**ichidagi oqim komponenti** — go2rtc'ning `video-stream` veb-komponenti — yangi shakl.

---

## 5. Wave 0 — birinchi migratsiyadan OLDIN bajariladigan tuzatishlar

> Uchalasi ham 2- va 3-faza tadqiqotlarida **kod o'qib** topilgan va uchalasi ham keyin
> topilsa qimmatroq bo'ladi.

| # | Ish | Fayl | Sabab / manba |
|---|-----|------|---------------|
| **W0-1** | `httpx` ni `[dependency-groups] dev` dan `[project] dependencies` ga ko'chirish | `services/core-api/pyproject.toml:6-56` | **D-16.** Bugun `:53` da dev guruhida. ISAPI klienti — prod kodi. Ko'chirilmasa hamma test yashil, deploy import xatosi |
| **W0-2** | `Permission.CAMERA_MANAGE` qo'shish + `PLATFORM_ADMIN` ga `CAMERA_VIEW` **va** `CAMERA_MANAGE` berish | `app/security/rbac.py:112-117, 130-143` | **D-15.** O'lchandi: `PLATFORM_ADMIN` da `CAMERA_VIEW` yo'q, `CAMERA_MANAGE` umuman mavjud emas. Self-service qoidasi bo'yicha NVR'ni **aynan platforma admini** ulaydi — 2-fazadagi Pitfall 6 ning ayni takrori |
| **W0-3** | `frontend/src/lib/rbac.ts` ko'zgusini **qo'lda** sinxronlash | `frontend/src/lib/rbac.ts` | `rbac.py:20-27` majburiyati. Unutish ma'lumot ochmaydi, lekin tugma ko'rinib turib 403 beradigan UI hosil qiladi |
| **W0-4** | `MARKET_ADMIN` ga `CAMERA_MANAGE` berish qarori | `app/security/rbac.py:164-177` | Bozor admini o'z bozorining hammasini boshqaradi; `DIRECTOR` **olmaydi** (D-07: faqat ko'rish) |
| **W0-5** | `pyproject.toml` ga `sim` va `slow` markerlarini qo'shish | `pyproject.toml:27-30` | `--strict-markers` tufayli marker e'lon qilinmasa `-m sim` yig'ilishda yiqiladi |
| **W0-6** | `SENSITIVE_KEYS` ni **tasdiqlash** (o'zgartirmaslik) | `packages/sbozor-core/sbozor_core/logging.py:59-61` | **D-12.** ✅ Tasdiqlandi 2026-08-03: `rtsp_password` va `nvr_password` allaqachon bor. Bu band **kod o'zgarishini talab qilmaydi** — u faqat "taxmin qilmaslik" majburiyatini yopadi |
| **W0-7** | `market_delete_draft()` kaskadini to'rtta yangi jadval bilan kengaytirish | `migrations/entities/functions.py:1050-1062` | **D-17/WR-02.** Kengaytirilmasa `0012` dan keyin bozor o'chirish FK buzilishi bilan yiqiladi. DB darajasidagi cheklov — `0013` |

---

## Metadata

**Analog qidiruv qamrovi:**
`services/core-api/app/**` · `packages/sbozor-core/**` · `migrations/**` · `tests/**` ·
`frontend/src/**` · `frontend/scripts/**` · `compose.yaml` · `compose.override.yml` ·
`ops/**` · `package.json` · `pyproject.toml`

**Skanerlangan fayllar:** ~340 (git tracked); to'liq o'qilgan: 18; nishonli o'qilgan: 11;
grep bilan tekshirilgan: 6 ta o'lchov (httpx / cryptography / taskiq-arq / BackgroundTasks /
Fernet / sim-branching nomzodlari)

**Empirik o'lchovlar (2026-08-03, bu hujjatning da'volari shulardan keladi):**

| Da'vo | Buyruq | Natija |
|-------|--------|--------|
| `cryptography` hech qayerda import qilinmagan | `grep -rn "from cryptography" --include=*.py .` | **0 natija** |
| `httpx` prod kodida yo'q | `grep -rn "import httpx" --include=*.py services/ packages/` | **0 natija** |
| `httpx` faqat testlarda | `grep -l "httpx" --include=*.py` | **24 fayl, hammasi `tests/`** |
| Navbat/worker yo'q | `grep -in "arq\|taskiq\|celery\|scheduler"` | Faqat `BackgroundTasks` (`audit.py`, `users.py`) |
| `PLATFORM_ADMIN` da `CAMERA_VIEW` yo'q | `rbac.py:130-143` o'qildi | **Tasdiqlandi (D-15)** |
| `CAMERA_MANAGE` mavjud emas | `rbac.py:49-117` o'qildi | **Tasdiqlandi (D-15)** |
| `nvr_password`/`rtsp_password` `SENSITIVE_KEYS` da | `logging.py:59-61` o'qildi | **Tasdiqlandi (D-12) — mavjud** |
| `httpx` dev guruhida | `pyproject.toml:53` o'qildi | **Tasdiqlandi (D-16)** |

**Pattern extraction date:** 2026-08-03
