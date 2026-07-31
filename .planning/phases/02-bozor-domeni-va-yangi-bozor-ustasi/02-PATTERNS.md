# Phase 2: Bozor domeni va "Yangi bozor" ustasi — Pattern Map

**Mapped:** 2026-07-31
**Files analyzed:** 62 (yangi yoki o'zgaradigan)
**Analogs found:** 58 / 62 (4 tasi uchun aniq analog yo'q — pastdagi "No Analog Found")

> **Bu hujjatning maqsadi:** 2-fazadagi deyarli har bir fayl uchun 1-fazada **haqiqatan ishlaydigan** analog mavjud.
> Ijrochi naqsh o'ylab topmaydi — u quyidagi aniq fayl:qatordan nusxa oladi.
> Kod parchalari **verbatim** (o'zgartirilmagan) keltirilgan; izohlar o'zbekcha.
>
> **Eng xavfli uch joy** (noto'g'ri qilinsa 1-fazaning tenant-izolyatsiya kafolati buziladi):
> §S-1 (RLS + `market_id`), §S-2 (tenant sessiyasi / DI), §S-3 (audit yozuvi).

---

## 0. Umumiy majburiy konventsiyalar (hamma fayl uchun)

| Qoida | Manba | Buzilsa nima bo'ladi |
|-------|-------|----------------------|
| Har bir modul **fayl-darajasidagi docstring/izoh** bilan boshlanadi va u "nega shunday" ni tushuntiradi | butun 1-faza kodi | Kod review'dan o'tmaydi — bu repoda izoh ixtiyoriy emas |
| Izohlar, docstring'lar, xato matnlari — **o'zbek tilida (uz-Latn)** | `deps.py:1-40`, `policies.py:1-31` | Uslub ajralib qoladi |
| Python: `from __future__ import annotations` birinchi import | har bir `.py` | ruff/mypy konfiguratsiyasi shuni kutadi |
| Python: `__all__` aniq e'lon qilinadi | `helpers.py:35-54`, `tenancy.py:40-49` | Import yuzasi nazoratsiz kengayadi |
| Python: `if TYPE_CHECKING:` bloki faqat tip importlari uchun | `users.py:74-77`, `audit_repo.py:51-54` | Runtime import zanjiri og'irlashadi |
| Backend `import` tartibi: stdlib → uchinchi tomon (`sbozor_core` shu yerda) → `app.*` | `users.py:44-72` | ruff `I` qoidasi qizaradi |
| Frontend: TSX importlar `react` → uchinchi tomon → `@/...` alias | `user-list.tsx:1-22` | eslint qizaradi |
| Frontend: `AGENTS.md` majburiyati — **Next.js 16 hujjatini `node_modules/next/dist/docs/` dan o'qing** yozishdan oldin | `frontend/AGENTS.md` | `middleware.ts` kabi eskirgan API ishlatiladi |
| Pul: `bigint` so'm ↔ Python `int`; `float`/`Decimal` **TAQIQ** | `sbozor_core/money.py:43-63` | `TypeError` — kutubxona o'zi rad etadi |
| Vaqt: `timestamptz` + `ZoneInfo("Asia/Tashkent")`; naive `datetime` **TAQIQ** | `sbozor_core/timeutil.py:44-62` | `ValueError` |
| Telefon: chegarada `normalize_phone()` (Pydantic `field_validator`) | `schemas.py:190-197` | Bir odam ikki hisob oladi (D-12 buziladi) |

---

## 1. File Classification

### 1.1 Backend — sxema qatlami

| Yangi/o'zgaradigan fayl | Rol | Data flow | Eng yaqin analog | Moslik |
|-------------------------|-----|-----------|------------------|--------|
| `packages/sbozor-core/sbozor_core/models/market.py` | model | CRUD | `packages/sbozor-core/sbozor_core/models/identity.py` | **exact** |
| `packages/sbozor-core/sbozor_core/models/__init__.py` | model-barrel | — | o'zi (1-faza holati) | **exact** |
| `packages/sbozor-core/sbozor_core/enums.py` | enum/config | — | o'zi (`Role`, `Locale`) | **exact** |
| `packages/sbozor-core/sbozor_core/schema_contract.py` | config/registry | — | o'zi | **exact** |
| `migrations/versions/0006_market_domain.py` | migration | DDL | `migrations/versions/0001_identity.py` | **exact** |
| `migrations/versions/0007_temporal.py` | migration | DDL + trigger | `migrations/versions/0002_audit.py` | **exact** |
| `migrations/versions/0008_vendors.py` | migration | DDL + EXCLUDE | `migrations/versions/0001_identity.py` + RESEARCH Code Example 1 | role-match |
| `migrations/versions/0009_calendar.py` | migration | DDL + funksiya | `migrations/versions/0004_user_admin.py` | **exact** |
| `migrations/entities/__init__.py` | registry | — | o'zi | **exact** |
| `migrations/entities/functions.py` | db-function | request-response | o'zi (`AUTH_FIND_LOGIN`) | **exact** |
| `migrations/entities/triggers.py` | db-trigger | event-driven | o'zi (`FN_AUDIT_ROW`, `AUDIT_IMMUTABLE`) | **exact** |
| `migrations/helpers.py` | utility | DDL | o'zi (`financial_guard_statements`) | **exact** |
| `ops/db/init/00-extensions.sql` | config/ops | — | `ops/db/init/01-roles.sql` | role-match |

### 1.2 Backend — API qatlami

| Yangi/o'zgaradigan fayl | Rol | Data flow | Eng yaqin analog | Moslik |
|-------------------------|-----|-----------|------------------|--------|
| `services/core-api/app/api/v1/stalls.py` | router | CRUD + keyset | `services/core-api/app/api/v1/users.py` | **exact** |
| `services/core-api/app/api/v1/vendors.py` | router | CRUD + o'qish-auditi | `services/core-api/app/api/v1/audit.py` (`audit_read`) + `users.py` | **exact** |
| `services/core-api/app/api/v1/tariffs.py` | router | append-only CRUD | `services/core-api/app/api/v1/users.py` | role-match |
| `services/core-api/app/api/v1/zones.py` | router | CRUD | `services/core-api/app/api/v1/users.py` | **exact** |
| `services/core-api/app/api/v1/categories.py` | router | CRUD | `services/core-api/app/api/v1/users.py` | **exact** |
| `services/core-api/app/api/v1/calendar.py` | router | CRUD | `services/core-api/app/api/v1/users.py` | **exact** |
| `services/core-api/app/api/v1/markets.py` (MOD) | router | request-response | o'zi + `users.py::create_user` | **exact** |
| `services/core-api/app/api/v1/imports.py` | router | file-I/O (batch) | `services/core-api/app/api/v1/users.py` (403/409/422 naqshi) | partial |
| `services/core-api/app/repositories/stall_repo.py` | repository | CRUD | `services/core-api/app/repositories/user_repo.py` | **exact** |
| `services/core-api/app/repositories/vendor_repo.py` | repository | CRUD + keyset | `user_repo.py` + `audit_repo.py::AuditRepository` | **exact** |
| `services/core-api/app/repositories/tariff_repo.py` | repository | temporal read | `services/core-api/app/repositories/audit_repo.py` | role-match |
| `services/core-api/app/repositories/market_repo.py` | repository | SECURITY DEFINER chaqiruvi | `services/core-api/app/repositories/user_repo.py` (`_CREATE_USER`) | **exact** |
| `services/core-api/app/services/xlsx_reader.py` | service | file-I/O | — | **no analog** |
| `services/core-api/app/services/xlsx_template.py` | service | file-I/O (stream) | — | **no analog** |
| `services/core-api/app/services/import_validator.py` | service | transform | — | **no analog** |
| `services/core-api/app/schemas.py` (MOD) | schema/DTO | — | o'zi | **exact** |
| `services/core-api/app/security/rbac.py` (MOD) | config/matrix | — | o'zi | **exact** |
| `services/core-api/app/security/audit.py` (MOD) | security utility | — | o'zi (`TABLE_USERS`) | **exact** |
| `services/core-api/app/main.py` (MOD) | bootstrap | — | o'zi (`include_router`) | **exact** |
| `services/core-api/app/api/v1/auth.py` (MOD — WR-02/WR-03) | router | request-response | o'zi | **exact** |
| `services/core-api/app/repositories/auth_repo.py` (MOD — `Membership.is_active`) | repository | — | o'zi | **exact** |
| `services/core-api/pyproject.toml` (MOD) | config | — | o'zi | **exact** |

### 1.3 Testlar

| Yangi/o'zgaradigan fayl | Rol | Data flow | Eng yaqin analog | Moslik |
|-------------------------|-----|-----------|------------------|--------|
| `tests/fixtures/market_domain.py` | test fixture | seed | `tests/fixtures/two_markets.py` | **exact** |
| `tests/tenancy/test_market_domain_meta.py` | test (meta) | pg_catalog o'qish | `tests/tenancy/test_meta.py` | **exact** |
| `tests/integration/test_tariff_history.py` | test (integration) | temporal | `tests/integration/test_business_date.py` | **exact** |
| `tests/integration/test_stall_assignments.py` | test (integration) | constraint | `tests/tenancy/test_composite_fk.py` | **exact** |
| `tests/integration/test_stall_code_reuse.py` | test (integration) | constraint | `tests/tenancy/test_composite_fk.py` | **exact** |
| `tests/integration/test_market_calendar.py` | test (integration) | funksiya chaqiruvi | `tests/integration/test_business_date.py` | role-match |
| `tests/integration/test_stall_import.py` | test (integration) | file-I/O | `tests/integration/test_users_api.py` | role-match |
| `tests/integration/test_wizard_flow.py` | test (integration) | HTTP e2e | `tests/integration/test_users_api.py` | **exact** |
| `tests/unit/test_rbac_matrix.py` (MOD) | test (unit) | — | o'zi | **exact** |

### 1.4 Frontend

| Yangi/o'zgaradigan fayl | Rol | Data flow | Eng yaqin analog | Moslik |
|-------------------------|-----|-----------|------------------|--------|
| `frontend/src/app/globals.css` (MOD — Wave 0) | config/tokens | — | o'zi | **exact** |
| `frontend/src/components/ui/dialog.tsx` | ui primitive | — | `frontend/src/components/users/create-user-dialog.tsx:145-158` (inline) | **exact** |
| `frontend/src/components/ui/field.tsx` | ui primitive | — | `frontend/src/components/audit/audit-filters.tsx:173-190` | **exact** |
| `frontend/src/components/ui/select.tsx` | ui primitive | — | `frontend/src/components/audit/audit-filters.tsx:192-213` | **exact** |
| `frontend/src/components/ui/badge.tsx` | ui primitive | — | `frontend/src/components/users/user-list.tsx:345-364` | **exact** |
| `frontend/src/components/ui/skeleton.tsx` | ui primitive | — | `app/[locale]/(app)/layout.tsx:95-96` | **exact** |
| `frontend/src/components/ui/empty-state.tsx` | ui primitive | — | `user-list.tsx:98-100` | partial |
| `frontend/src/components/ui/confirm-dialog.tsx` | ui primitive | — | `frontend/src/components/users/user-list.tsx:260-343` | **exact** |
| `frontend/src/app/[locale]/(app)/stalls/page.tsx` | page (client) | request-response | `frontend/src/app/[locale]/(app)/users/page.tsx` | **exact** |
| `frontend/src/app/[locale]/(app)/vendors/page.tsx` | page (client) | request-response | `frontend/src/app/[locale]/(app)/users/page.tsx` | **exact** |
| `frontend/src/app/[locale]/(app)/tariffs/page.tsx` | page (client) | request-response | `frontend/src/app/[locale]/(app)/users/page.tsx` | **exact** |
| `frontend/src/app/[locale]/(app)/calendar/page.tsx` | page (client) | request-response | `frontend/src/app/[locale]/(app)/users/page.tsx` | **exact** |
| `frontend/src/app/[locale]/(app)/map/page.tsx` | page (client) | request-response | `frontend/src/app/[locale]/(app)/audit/page.tsx` (`Suspense`!) | **exact** |
| `frontend/src/app/[locale]/(app)/markets/new/page.tsx` | page (client) | request-response | `frontend/src/app/[locale]/(app)/users/page.tsx` | role-match |
| `frontend/src/app/[locale]/(app)/markets/setup/page.tsx` | page (client) | request-response | `frontend/src/app/[locale]/(app)/audit/page.tsx` (nuqs + `Suspense`) | **exact** |
| `frontend/src/components/stalls/stall-list.tsx` | component (list) | request-response | `frontend/src/components/users/user-list.tsx` | **exact** |
| `frontend/src/components/stalls/stall-dialog.tsx` | component (form) | request-response | `frontend/src/components/users/create-user-dialog.tsx` | **exact** |
| `frontend/src/components/stalls/stall-filters.tsx` | component (filter) | URL state | `frontend/src/components/audit/audit-filters.tsx` | **exact** |
| `frontend/src/components/stalls/{stall-map,stall-cell,stall-tone,stall-map-legend}.tsx` | component (render) | derived state | — | **no analog** |
| `frontend/src/components/stalls/stall-card-dialog.tsx` | component (dialog) | — | `frontend/src/components/users/user-list.tsx:260-343` | **exact** |
| `frontend/src/components/vendors/{vendor-list,vendor-dialog,assignment-dialog}.tsx` | component | CRUD | `users/{user-list,create-user-dialog}.tsx` | **exact** |
| `frontend/src/components/tariffs/{tariff-list,tariff-dialog}.tsx` | component | CRUD | `users/{user-list,create-user-dialog}.tsx` | **exact** |
| `frontend/src/components/calendar/{weekday-picker,exception-list,exception-dialog}.tsx` | component | CRUD | `create-user-dialog.tsx:262-289` (`RoleCheckbox` — ko'p tanlov) | **exact** |
| `frontend/src/components/zones/zone-list.tsx`, `categories/category-list.tsx` | component | CRUD | `frontend/src/components/users/user-list.tsx` | **exact** |
| `frontend/src/components/wizard/{wizard-shell,wizard-stepper,activation-panel}.tsx` | component | request-response | `frontend/src/components/shell/app-shell.tsx` (nav+filtr) | partial |
| `frontend/src/components/import/{import-panel,import-errors}.tsx` | component | file-I/O | — | **no analog** |
| `frontend/src/lib/api-types.ts` (MOD) | schema (zod) | — | o'zi | **exact** |
| `frontend/src/lib/queries.ts` (MOD) yoki `lib/queries/*.ts` | data-access hook | request-response | o'zi | **exact** |
| `frontend/src/lib/rbac.ts` (MOD) | config/matrix | — | o'zi | **exact** |
| `frontend/src/components/shell/app-shell.tsx` (MOD) | layout | — | o'zi | **exact** |
| `frontend/src/components/auth/market-picker.tsx` (MOD — W0-12) | component | — | o'zi | **exact** |
| `frontend/messages/{uz-Latn,ru}.json` (MOD) | i18n | — | o'zi | **exact** |
| `frontend/messages/uz-Cyrl.overrides.json` (MOD) | i18n | — | o'zi | **exact** |
| `frontend/scripts/gen-cyrillic.test.mjs` (MOD) | test | — | o'zi | **exact** |
| `frontend/src/components/stalls/stall-map.test.tsx` | test (component) | — | `frontend/src/components/auth/market-picker.test.tsx` | **exact** |

---

## 2. Shared Patterns — HAMMA fayl uchun (avval shu bo'limni o'qing)

### S-1. Tenant jadvali: `market_id` + RLS ENABLE **va** FORCE + policy

**Manba 1 — modeldagi shakl:** `packages/sbozor-core/sbozor_core/models/base.py:37-97`

```python
NAMING_CONVENTION: dict[str, str] = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_N_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Barcha SBOZOR modellari uchun deklarativ baza."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def uuid_pk() -> MappedColumn[UUID]:
    """Vaqt-tartiblangan birlamchi kalit (`uuidv7()`, PG18 native)."""
    return mapped_column(
        PgUuid(as_uuid=True),
        primary_key=True,
        server_default=text("uuidv7()"),
    )


def market_fk_column() -> MappedColumn[UUID]:
    """`market_id` ustuni — tenant kaliti.

    FK `markets(id)` ga ATAYIN shu yerda emas, konkret modelning
    `__table_args__` ida e'lon qilinadi: keyingi fazalarda ba'zi jadvallar
    `(market_id, <parent_id>)` COMPOSITE FK ishlatadi va bitta ustunda
    ikkita FK bo'lishi keraksiz indeks/konstraytga olib keladi.
    """
    return mapped_column(PgUuid(as_uuid=True), nullable=False)


class TimestampMixin:
    """`created_at` / `updated_at` — ikkalasi ham `timestamptz`."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class TenantMixin:
    """Tenant-scoped jadval uchun `market_id`."""

    market_id: Mapped[UUID] = market_fk_column()
```

> ⚠ `market_fk_column()` docstringi **aynan 2-fazani** nazarda tutgan: `stalls`, `tariffs`,
> `stall_assignments` composite FK ishlatadi, ya'ni `market_id` ustunida `ForeignKey` **inline
> yozilmaydi** — u `__table_args__` da e'lon qilinadi.

**Manba 2 — migratsiyadagi shakl:** `migrations/versions/0001_identity.py:143-170`

```python
    op.create_table(
        "user_market_roles",
        sa.Column("market_id", pg.UUID(as_uuid=True), nullable=False),
        _uuid_pk(),
        sa.Column("user_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("roles", pg.ARRAY(sa.Text()), nullable=False),
        _created_at(),
        _updated_at(),
        sa.PrimaryKeyConstraint("id", name="pk_user_market_roles"),
        sa.ForeignKeyConstraint(
            ["market_id"], ["markets.id"], name="fk_user_market_roles_market_id_markets"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_user_market_roles_user_id_users",
            ondelete="CASCADE",
        ),
        # Bu konstrayt AYNI PAYTDA `(market_id, user_id)` indeksining o'zi —
        # alohida `CREATE INDEX` keraksiz dublikat bo'lardi.
        sa.UniqueConstraint("market_id", "user_id", name="uq_user_market_roles_market_id_user_id"),
        # Composite FK maqsadi (T-01-26): keyingi fazalar `(market_id, id)`
        # ga havola qilib cross-tenant bog'lanishni strukturaviy yopadi.
        sa.UniqueConstraint("market_id", "id", name="uq_user_market_roles_market_id_id"),
        sa.CheckConstraint(ROLES_SUBSET_CHECK, name="roles_allowed"),
        sa.CheckConstraint("cardinality(roles) > 0", name="roles_not_empty"),
    )
    enable_tenant_rls("user_market_roles")
```

Migratsiya faylining lokal yordamchilari (`0001_identity.py:55-81`) — **har yangi migratsiyada
takrorlanadi**, umumiy modulga chiqarilmagan:

```python
def _uuid_pk() -> sa.Column[UUID]:
    """PG18 native `uuidv7()` — vaqt-tartiblangan, B-tree do'st."""
    return sa.Column(
        "id",
        pg.UUID(as_uuid=True),
        server_default=sa.text("uuidv7()"),
        nullable=False,
    )


def _created_at() -> sa.Column[datetime]:
    return sa.Column(
        "created_at",
        sa.DateTime(timezone=True),
        server_default=sa.text("now()"),
        nullable=False,
    )
```

**Manba 3 — policy tartibi:** `migrations/versions/0001_identity.py:210-218`

```python
    # ------------------------------------------------------------------
    # 5. Policy'lar. TARTIB MUHIM: ENABLE/FORCE (yuqorida) -> policy.
    #    `alembic-utils` bayroqlarni BILMAYDI (Pitfall 10), ularsiz policy
    #    hech qanday ta'sir ko'rsatmaydi.
    # ------------------------------------------------------------------
    create_entity(markets_policy())
    for table in TENANT_TABLES:
        create_entity(tenant_policy(table))
    for table in RLS_TABLES:
        create_entity(owner_bootstrap_policy(table))
```

**Manba 4 — yordamchi:** `migrations/helpers.py:123-136`

```python
def enable_tenant_rls(table: str, role: str = APP_ROLE) -> None:
    """Standart tenant jadvali: `ENABLE` + `FORCE` + to'liq DML GRANT.

    GRANT'siz policy ma'nosiz bo'ladi (huquq yo'q -> `permission denied`),
    ENABLE/FORCE'siz esa policy ma'nosiz bo'ladi (hamma narsa ochiq).
    Uchtasi birga yuradi, shuning uchun bitta chaqiruvda.
    """
    enable_rls(table)
    grant_app_dml(table, role=role)
```

**Manba 5 — predikat (`NULLIF` MAJBURIY):** `migrations/entities/policies.py:65-103`

```python
TENANT_PREDICATE = "market_id = NULLIF(current_setting('app.market_id', true), '')::uuid"
"""Standart tenant jadvallari uchun predikat (`market_id` ustuni bo'yicha)."""


def tenant_policy(table: str) -> PGPolicy:
    """Berilgan tenant jadvali uchun `sbozor_app` policy'si.

    `WITH CHECK` `USING` bilan bir xil: boshqa bozorga YOZISH ham
    (INSERT/UPDATE) strukturaviy rad etiladi, faqat o'qish emas.
    """
    return PGPolicy(
        schema="public",
        signature=TENANT_POLICY_SIGNATURE,
        on_entity=f"public.{table}",
        definition=f"""
            AS PERMISSIVE
            FOR ALL
            TO {APP_ROLE}
            USING      ({TENANT_PREDICATE})
            WITH CHECK ({TENANT_PREDICATE})
        """,
    )
```

**Manba 6 — reyestrga qo'shish (unutilsa CI qizaradi):** `migrations/entities/__init__.py:35-41`

```python
TENANT_TABLES: tuple[str, ...] = ("user_market_roles", "refresh_tokens")
"""`market_id` ustuni + standart tenant policy'si bo'lgan jadvallar.

Yangi tenant jadvali qo'shilganda BU RO'YXATGA ham bir satr qo'shiladi.
Unutilsa `tests/tenancy/test_meta.py::test_every_table_is_tenant_scoped`
jadvalni policy'siz topib darvozani yopadi.
"""
```

**YANGI JADVAL QO'SHGANDA TO'RT JOY (biri unutilsa CI qizaradi):**

1. `migrations/entities/__init__.py::TENANT_TABLES`
2. migratsiya fayli (`op.create_table` + `enable_tenant_rls` + `tenant_policy` + `owner_bootstrap_policy`)
3. `packages/sbozor-core/sbozor_core/schema_contract.py::AUDITED_TABLES` (agar audit trigger ulansa)
4. `tests/fixtures/market_domain.py` seed'i

**Darvoza (bu testni O'QING, uni aldashga urinmang):** `tests/tenancy/test_meta.py:228-261`

```python
def test_every_table_is_tenant_scoped(sync_app_conn: Connection[TupleRow], migrated: None) -> None:
    """Har bir jadval: `market_id` + RLS ENABLE + FORCE + policy.

    Uchtasi ham kerak va uchtasi ham ALOHIDA buzilishi mumkin:
      * `market_id` yo'q -> jadval umuman tenant'ga bog'lanmagan;
      * ENABLE yo'q      -> policy TA'SIRSIZ, hamma narsa ochiq (Pitfall 10);
      * FORCE yo'q       -> ega (migratsiya roli) policy'dan chetda qoladi;
      * policy yo'q      -> RLS bor, lekin deny-all (fail-closed, lekin ilova ishlamaydi).
    """
```

Ikkinchi darvoza — **indeks birinchi ustuni** (`test_meta.py:299-329`): tenant jadvalidagi
har bir indeks (PK'dan tashqari) `market_id` bilan boshlanishi shart. RESEARCH empirik
tekshirdi: `EXCLUDE USING gist (market_id WITH =, ...)` bu darvozadan **o'tadi**.

---

### S-2. Tenant sessiyasi va DI — `Annotated[X, Depends(...)]`

**Manba:** `services/core-api/app/deps.py:398-433`

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

    # SIM117 (ikki `async with` ni birlashtirish) ATAYIN rad etilgan: ichki
    # blok TRANZAKSIYA chegarasi va u shu yerdagi butun xavfsizlik da'vosini
    # ushlab turadi. ...
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

**Bu 2-fazada O'ZGARTIRILMAYDI.** Har bir yangi tenant endpointi shunchaki
`session: TenantSessionDep` oladi. `require_password_current` avtomatik ishlaydi.

**Endpoint-darajasidagi alias (har router faylining tepasida):** `services/core-api/app/api/v1/users.py:104-105`

```python
UserManagerDep = Annotated[Principal, Depends(require_permission(Permission.USER_MANAGE))]
UserViewerDep = Annotated[Principal, Depends(require_permission(Permission.USER_VIEW))]
```

2-faza uchun: `StallManagerDep`, `MarketDataViewerDep`, `TariffManagerDep`, `VendorManagerDep`,
`VendorViewerDep` — aynan shu shaklda, router faylining tepasida.

**Repozitoriy — ikkinchi qatlam filtri:** `packages/sbozor-core/sbozor_core/tenancy.py:117-166`

```python
class TenantScopedRepository:
    """Repozitoriylar uchun baza — IKKINCHI qatlam filtri.

    RLS himoya to'ri bo'lsa ham, so'rovga `market_id` predikatini qo'shish
    majburiy (P9). Ikki sabab:

    * RLS bir kun noto'g'ri migratsiya bilan o'chib qolsa, ilova baribir
      to'g'ri ishlaydi;
    * predikat rejalashtiruvchiga indeks ishlatish imkonini beradi — RLS
      ifodasi yolg'iz o'zi har doim ham indeksga tushmaydi.

    Voris klasslar `self.session` va `self.market_id` dan foydalanadi va har
    bir `select()` ni `self.scoped(...)` orqali o'tkazadi.
    """

    def __init__(self, session: AsyncSession, market_id: UUID) -> None:
        self.session = session
        self.market_id = market_id
```

> ⚠ `scoped()` **bitta entity** ustidagi `select()` ni kutadi (`column_descriptions[0]`).
> RESEARCH Pattern 3 dagi `LEFT JOIN LATERAL` so'rovi bu cheklovga tushadi —
> uni `text()` bilan yozing va `market_id` ni bind parametr sifatida bering
> (`audit_repo.py:238-246` naqshi), yoki `select(Stall)` dan boshlab lateral'ni
> `.join(..., isouter=True)` bilan qo'shing.

---

### S-3. Audit yozuvi — ikki xil, aralashtirilmaydi

**Qaysi jadval qaysi yo'ldan boradi:**

| Jadval | Yo'l | Nima kerak |
|--------|------|------------|
| `stalls`, `stall_category_periods`, `tariffs`, `vendors`, `stall_assignments`, `market_calendar_exceptions` | **DB-trigger** | `attach_audit_trigger("<jadval>")` migratsiyada + `AUDITED_TABLES` ga qo'shish |
| `markets` (yaratish/faollashtirish/nomlash) | **App-qatlam** | `write_app_audit(...)` — `SECURITY DEFINER` funksiya ichida trigger yo'q |
| `vendors` O'QISH (shaxsiy ma'lumot, D-09) | **App-qatlam** | `Depends(audit_read("vendors", reason="vendor_view"))` |

**Trigger ulash:** `migrations/helpers.py:190-212`

```python
def attach_audit_trigger(table: str) -> None:
    """Jadvalga `fn_audit_row()` triggerini ulaydi (`AFTER ... FOR EACH ROW`).

    Yangi moliyaviy/huquqiy jadval tug'ilganda uch qadam BIRGA bajariladi::

        op.create_table("payments", ...)
        enable_tenant_rls("payments")
        attach_audit_trigger("payments")            # <- bu satr
        # + `AUDITED_TABLES` reyestriga "payments" qo'shiladi

    TALAB: jadvalning birlamchi kaliti `id uuid` bo'lishi shart —
    `fn_audit_row()` `row_id` ni `uuid` ga keltiradi.
    """
    tbl = _ident(table)
    op.execute(
        f"CREATE TRIGGER {audit_trigger_name(tbl)} "
        f"AFTER INSERT OR UPDATE OR DELETE ON {tbl} "
        "FOR EACH ROW EXECUTE FUNCTION fn_audit_row()"
    )
```

Migratsiyadagi chaqiruv (`0002_audit.py:171`) va uning jufti (`0002_audit.py:176`):

```python
    attach_audit_trigger(AUDITED_TABLE)
...
def downgrade() -> None:
    """Downgrade schema."""
    detach_audit_trigger(AUDITED_TABLE)
```

**App-qatlam yozuvi:** `services/core-api/app/api/v1/users.py:240-248`

```python
    await repo.add_membership(user_id, roles)
    await write_app_audit(
        session,
        action=AuditAction.INSERT,
        table_name=TABLE_USERS,
        row_id=user_id,
        principal=principal,
        new={"phone": payload.phone, "roles": roles, "locale": locale},
    )
```

**`old` qiymati TAXMIN QILINMAYDI** — `users.py:368-397`:

```python
async def _set_member_active(...) -> None:
    """`block`/`unblock` ning umumiy qismi: a'zolik tekshiruvi + yozuv + audit.

    `old` qiymati TAXMIN QILINMAYDI — u yozuvdan oldin `auth_user_state()`
    bilan o'qiladi. "Bloklash so'ralgan, demak avval faol edi" degan
    taxmin allaqachon bloklangan foydalanuvchi uchun jurnalga YOLG'ON
    eski qiymat yozardi, jurnal esa aynan nizoni hal qilish uchun bor.
    """
```

**O'qish auditi (D-09 — `vendors` uchun MAJBURIY):** `services/core-api/app/api/v1/audit.py:94-104` + `168-197`

```python
AuditViewerDep = Annotated[Principal, Depends(require_permission(Permission.AUDIT_VIEW))]
AuditReadIntentDep = Annotated[
    AuditReadIntent,
    Depends(audit_read(TABLE_AUDIT_LOG, reason="audit_view")),
]
```

```python
@router.get("", response_model=AuditListResponse)
async def list_audit(
    principal: AuditViewerDep,
    intent: AuditReadIntentDep,
    query: Annotated[AuditQuery, Query()],
    session: TenantSessionDep,
) -> AuditListResponse:
    ...
    intent.filters = _describe(query)
    intent.result_count = len(page.rows)
```

> **E'LON TARTIBI MAJBURIY:** `require_permission` **`audit_read` dan OLDIN**.
> Sabab `audit.py:38-59` docstringida ikki qatlam sifatida hujjatlashtirilgan:
> 403 olgan so'rov jurnalga **yolg'on dalil** yozmasligi kerak.
> `TABLE_VENDORS = "vendors"` konstantasi `app/security/audit.py:59-69` yoniga qo'shiladi.

---

### S-4. Xato javoblari — 404 / 403 / 409 / 422 qoidasi

| Holat | Kod | Manba |
|-------|-----|-------|
| Cross-tenant yoki mavjud bo'lmagan resurs | **404** `not_found` | `users.py:173-175` |
| Huquq yetmasa | **403** `forbidden` | `deps.py:451-459` |
| Bozor tanlanmagan | **409** `market_not_selected` | `deps.py:408-412` |
| Konflikt (kod band, tarif sanasi band) | **409** `<code>` | `users.py:238` |
| Buzuq kursor / shakl | **422** | `audit.py:181-189` |
| RLS `WITH CHECK` buzilishi | **404** (global handler) | `main.py:131-150` |

```python
def _not_found() -> HTTPException:
    """Cross-tenant va mavjud bo'lmagan foydalanuvchi uchun BIR XIL javob."""
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_USER_NOT_FOUND)
```

Global RLS handler allaqachon o'rnatilgan (`main.py:131-150`) — yangi router **hech nima
qo'shmaydi**, RLS buzilishi avtomatik 404 bo'ladi.

Yangi `detail` kodlari **ikkala tomonda** e'lon qilinadi: backend (`HTTPException(detail=...)`) va
frontend `api-types.ts::ERROR_CODES` (`api-types.ts:318-333`).

---

### S-5. Keyset paginatsiya (OFFSET **hech qachon**)

**Repozitoriy tomoni:** `services/core-api/app/repositories/audit_repo.py:160-210`

```python
class AuditRepository(TenantScopedRepository):
    async def list_audit(self, query: AuditQuery) -> AuditPage:
        """Filtrlangan sahifa. `query.limit` — QAYTARILADIGAN qatorlar soni."""
        stmt = self.scoped(select(AuditLog))
        ...
        if query.cursor is not None:
            at, row_id = decode_cursor(query.cursor)
            # Qiymatlar `literal(..., type_)` bilan ATAYIN tiplangan ...
            boundary = tuple_(
                literal(at, DateTime(timezone=True)),
                literal(row_id, BigInteger()),
            )
            stmt = stmt.where(tuple_(AuditLog.at, AuditLog.id) < boundary)

        # BITTA ORTIQCHA qator so'raladi: "yana bormi?" savoliga javob
        # beradigan yagona arzon usul.
        stmt = stmt.order_by(AuditLog.at.desc(), AuditLog.id.desc()).limit(query.limit + 1)

        result = await self.session.execute(stmt)
        rows = list(result.scalars().all())

        if len(rows) > query.limit:
            rows = rows[: query.limit]
            last = rows[-1]
            return AuditPage(rows=rows, next_cursor=encode_cursor(last.at, last.id))
        return AuditPage(rows=rows, next_cursor=None)
```

Kursor kodlash/dekodlash (`audit_repo.py:124-149`) — `stalls`/`vendors` uchun `(code, id)` yoki
`(created_at, id)` juftligi bilan **aynan shu shaklda** takrorlanadi:

```python
def encode_cursor(at: datetime, row_id: int) -> str:
    """`(at, id)` juftligini opaque satrga o'raydi.

    Base64 — SIR EMAS, u faqat "bu qiymatning ichini o'qimang" degan
    signal. Mijoz uni o'zi qurishga urinsa (masalan `at` ni surib), eng
    yomoni boshqa sahifani oladi: kursor RLS predikatidan KEYIN
    qo'llanadi, ya'ni u bilan begona bozorga o'tib bo'lmaydi.
    """
    raw = f"{at.isoformat()}|{row_id}".encode()
    return base64.urlsafe_b64encode(raw).decode()
```

**Query modeli:** `services/core-api/app/schemas.py:296-323`

```python
AUDIT_PAGE_SIZE_MAX = 200

class AuditQuery(BaseModel):
    date_from: date | None = Field(default=None, alias="from")
    date_to: date | None = Field(default=None, alias="to")
    actor_user_id: UUID | None = None
    action: str | None = None
    table_name: str | None = None
    limit: Annotated[int, Field(ge=1, le=AUDIT_PAGE_SIZE_MAX)] = 50
    cursor: str | None = None
```

**Javob shakli:** `schemas.py:349-353`

```python
class AuditListResponse(BaseModel):
    """`GET /audit` — sahifa + keyingi kursor (`null` bo'lsa oxirgi sahifa)."""

    items: list[AuditEntry]
    next_cursor: str | None
```

---

### S-6. Pul va vaqt

**Pul (`tariffs.amount_soum`):** `packages/sbozor-core/sbozor_core/money.py:14-27, 65-84`

```python
type Soum = int
"""Pul miqdori — butun so'm. Semantik nom, alohida tip emas."""

MAX_SAFE_SOUM: int = 9_007_199_254_740_991


def assert_safe_soum(value: int) -> Soum:
    """Pul miqdorini tekshiradi va O'ZINI qaytaradi (chegarada ishlatiladi)."""
```

DB tomonda: `bigint` + `CHECK (amount_soum > 0)`. Zod tomonda: `soumSchema`
(`api-types.ts:45`) — `z.number().int().max(Number.MAX_SAFE_INTEGER)`.

**Biznes-kun ifodasi:** `migrations/helpers.py:225-241`

```python
MARKET_TZ_LITERAL = "Asia/Tashkent"

BUSINESS_DATE_EXPR = f"((created_at AT TIME ZONE '{MARKET_TZ_LITERAL}')::date)"
"""`business_date` generated column ifodasi.

IKKI ARGUMENTLI shakl ATAYIN: `timezone(text, timestamptz)` PostgreSQL'da
`provolatile = 'i'` (IMMUTABLE), shuning uchun generated column'da ruxsat
etiladi. Bitta argumentli `timezone(timestamptz)` esa `TimeZone` GUC'iga
bog'liq va `'s'` (STABLE) — u `ERROR: generation expression is not immutable`
beradi.
"""
```

Modeldagi jufti (`models/ops.py:46-53, 108-112`):

```python
AUDIT_BUSINESS_DATE_EXPR = "((at AT TIME ZONE 'Asia/Tashkent')::date)"
...
    business_date: Mapped[date] = mapped_column(
        Date(),
        Computed(AUDIT_BUSINESS_DATE_EXPR, persisted=True),
        nullable=False,
    )
```

> ⚠ **`tariffs` uchun `financial_guards()` NI CHAQIRMANG** (RESEARCH Anti-Pattern):
> u `UNIQUE(market_id, category_id, business_date)` beradi va bir kunda ikkita
> kelajak tarifini kiritishni bloklaydi. `tariffs` da uchta qo'riqchi **qo'lda** yoziladi:
> `business_date` Computed ustuni (yuqoridagi shaklda), `CHECK (amount_soum > 0)`,
> `UNIQUE(market_id, category_id, valid_from)`.
>
> ⚠ **`stall_assignments` ni `FINANCIAL_TABLES` dan OLIB TASHLANG**
> (`schema_contract.py:49-57`) — meta-test `CHECK (amount_soum > 0)` talab qiladi,
> jadvalda esa pul ustuni yo'q. Bu Wave 0 ishi, birinchi migratsiyadan **oldin**.

**Kod-qatlamidagi vaqt:** `sbozor_core/timeutil.py:44-62` — `business_date(moment)` naive
`datetime` ni `ValueError` bilan rad etadi. Yozish yo'lida **ishlatilmaydi** (DB hisoblaydi).

---

### S-7. `SECURITY DEFINER` funksiyasi (`markets` ga yozish, `market_is_open`)

**Manba:** `migrations/entities/functions.py:77-112`

```python
AUTH_FIND_LOGIN = PGFunction(
    schema="public",
    signature="auth_find_login(p_phone text)",
    definition="""
RETURNS TABLE (
    user_id uuid,
    password_hash text,
    is_active boolean,
    ...
)
LANGUAGE sql
SECURITY DEFINER
SET search_path = pg_catalog, public
STABLE
AS $$
    SELECT u.id,
           u.password_hash,
           ...
    FROM public.users AS u
    WHERE u.phone_e164 = p_phone
$$
""",
)
```

**Fayl docstringidan majburiy qoidalar** (`functions.py:27-42`):

- `SET search_path = pg_catalog, public` — **har bir funksiyada LITERAL yoziladi**,
  umumiy konstantaga chiqarilmaydi. `test_security_definer_functions_pin_search_path`
  butun `public` sxemani skanerlaydi.
- Funksiya tanasidagi har bir ustun havolasi **jadval aliasi** bilan (`u.locale`, `r.market_id`) —
  aliassiz `column reference ... is ambiguous`.
- Yangi funksiya `tests/tenancy/test_meta.py::EXPECTED_DEFINER_FUNCTIONS` ga ham qo'shiladi.

**GRANT naqshi:** `migrations/versions/0004_user_admin.py:51-63`

```python
def upgrade() -> None:
    """Upgrade schema."""
    for function in USER_ADMIN_FUNCTIONS:
        create_entity(function)

    for signature in USER_ADMIN_GRANT_SIGNATURES:
        # PUBLIC dan AVVAL olib tashlanadi: Postgres yangi funksiyaga
        # `EXECUTE TO PUBLIC` ni STANDART beradi, ya'ni REVOKE'siz
        # foydalanuvchi yaratish yo'li bazadagi har qanday rol uchun
        # ochiq bo'lib qolardi.
        op.execute(f"REVOKE ALL ON FUNCTION {signature} FROM PUBLIC")
        op.execute(f"GRANT EXECUTE ON FUNCTION {signature} TO {APP_ROLE}")
```

> `market_is_open()` — **`SECURITY DEFINER` EMAS** (RESEARCH Pattern 7):
> u chaqiruvchi huquqi bilan ishlaydi, ya'ni RLS unga qo'llanadi va boshqa bozor
> so'ralganda fail-closed `false` beradi. `STABLE` + `SET search_path` baribir yoziladi.

**Ilova tomonidan chaqirish:** `services/core-api/app/repositories/user_repo.py:79-83, 184-194`

```python
_CREATE_USER = text(
    "SELECT auth_create_user(:phone, :password_hash, :full_name, :locale, :is_platform_admin)"
)
```

```python
        result = await self.session.execute(
            _CREATE_USER,
            {
                "phone": phone,
                "password_hash": password_hash,
                "full_name": full_name,
                "locale": locale,
                "is_platform_admin": False,
            },
        )
        return result.scalar_one_or_none()
```

Tiplangan bind parametrlari kerak bo'lganda (`NULL` uzatiladigan joyda **MAJBURIY**) —
`audit_repo.py:238-256`:

```python
_PLATFORM_AUDIT = text(
    "SELECT id, at, business_date, ... FROM auth_list_platform_audit(:limit, :before_at, :before_id)"
).bindparams(
    bindparam("limit", type_=Integer()),
    bindparam("before_at", type_=DateTime(timezone=True)),
    bindparam("before_id", type_=BigInteger()),
)
```

---

### S-8. DB trigger funksiyasi (`tariff_past_immutable`, `stall_code_claim`)

**Manba:** `migrations/entities/triggers.py:44-91` (`FN_AUDIT_ROW`) va `118-130`:

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
```

**Fayl docstringidagi qulflangan qaror** (`triggers.py:22-35`): trigger funksiyalari
**`SECURITY DEFINER` EMAS** — `tests/tenancy/test_meta.py` buni `pg_proc.prosecdef`
bo'yicha qulflaydi. `SET search_path = pg_catalog, public` esa shunda ham majburiy.

Trigger'ning O'ZI (funksiya emas) xom `op.execute()` bilan yaratiladi — `0002_audit.py:156-163`:

```python
    op.execute(
        "CREATE TRIGGER audit_no_mutate BEFORE UPDATE OR DELETE ON audit_log "
        "FOR EACH ROW EXECUTE FUNCTION audit_immutable()"
    )
```

Ro'yxatga qo'shish (`triggers.py:139-142`) va migratsiyada tsikl (`0002_audit.py:72-73`):

```python
ALL_TRIGGER_FUNCTIONS: list[PGFunction] = [
    FN_AUDIT_ROW,
    AUDIT_IMMUTABLE,
]
```

```python
    for function in ALL_TRIGGER_FUNCTIONS:
        create_entity(function)
```

---

### S-9. RBAC matritsasi — ikki nusxa qo'lda sinxron

**Backend:** `services/core-api/app/security/rbac.py:40-112`

```python
class Permission(StrEnum):
    """Tekshiriladigan huquqlar. Endpoint `require_permission(...)` bilan qo'riqlanadi."""

    # --- Bozor ichidagi ma'lumot (2-faza) ---
    STALL_MANAGE = "stall_manage"
    TARIFF_MANAGE = "tariff_manage"
    VENDOR_MANAGE = "vendor_manage"
```

```python
ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.PLATFORM_ADMIN: frozenset(
        {
            Permission.MARKET_VIEW_ALL,
            Permission.MARKET_MANAGE,
            Permission.USER_MANAGE,
            Permission.USER_VIEW,
            Permission.AUDIT_VIEW,
        }
    ),
```

> ⚠ **Pitfall 6 (Wave 0):** `Role.PLATFORM_ADMIN` da `STALL_MANAGE`/`TARIFF_MANAGE`/`VENDOR_MANAGE`
> **yo'q** — ya'ni MARKET-01 ni bajaradigan odam o'zi qurayotgan bozorga rasta kirita olmaydi.
> RESEARCH Code Example 6 aniq to'plamni beradi. `MARKET_DATA_VIEW` va `VENDOR_VIEW`
> ikkita **yangi** Permission.

**Frontend ko'zgusi:** `frontend/src/lib/rbac.ts:28-76` — `PERMISSIONS` massivi va
`ROLE_PERMISSIONS` obyektida **aynan bir xil o'zgarish**. Fayl tepasidagi ogohlantirish
(`rbac.ts:1-17`) saqlanadi: bu fayl xavfsizlik chegarasi emas.

**Darvoza:** `tests/unit/test_rbac_matrix.py::test_every_role_has_entry`.

---

### S-10. Frontend — sahifa / ro'yxat / dialog uchligi

**Sahifa (client component, huquq tekshiruvi so'rovdan OLDIN):** `frontend/src/app/[locale]/(app)/users/page.tsx:31-85`

```tsx
export default function UsersPage() {
  const t = useTranslations();
  const { principal } = useAuthStore();
  const [createOpen, setCreateOpen] = useState(false);

  const roles = principal?.roles ?? [];
  const canView = hasPermission(roles, "user_view");
  const canManage = hasPermission(roles, "user_manage");

  if (!canView) {
    return (
      <p
        className="rounded-sm bg-danger/10 px-3 py-2 text-sm text-danger"
        role="alert"
      >
        {t("errors.forbidden")}
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold tracking-tight">
          {t("users.title")}
        </h1>

        {canManage ? (
          <Button onClick={() => setCreateOpen(true)}>
            <UserPlus aria-hidden="true" />
            {t("users.create")}
          </Button>
        ) : null}
      </div>
      ...
```

> **URL parametrini o'qiydigan sahifa `Suspense` ichida bo'lishi SHART** —
> `audit/page.tsx:49-58` va uning sababi `audit/page.tsx:25-26`:
> *"`Suspense` MAJBURIY: filtrlar URL qidiruv parametrlarini o'qiydi... Chegara bo'lmasa
> Next.js butun sahifani statik prerender ro'yxatidan chiqarardi."*
> Bu `markets/setup?step=N` va `stalls?zone=...` uchun **to'g'ridan-to'g'ri qo'llanadi**.

**Ro'yxat komponenti — yuklanish / xato / bo'sh / natija to'rtligi:** `user-list.tsx:80-133`

```tsx
  if (usersQuery.isPending) {
    return (
      <p className="text-sm text-text-muted" role="status">
        {t("common.loading")}
      </p>
    );
  }

  if (usersQuery.isError) {
    return (
      <p className="rounded-sm bg-danger/10 px-3 py-2 text-sm text-danger" role="alert">
        {t(adminErrorMessageKey(usersQuery.error))}
      </p>
    );
  }

  const items = usersQuery.data.items;

  if (items.length === 0) {
    return <p className="text-sm text-text-muted">{t("users.emptyState")}</p>;
  }

  return (
    <>
      <ul aria-label={t("users.title")} className="flex flex-col gap-3">
        {items.map((user) => (
          <li key={user.id}>
            <UserCard ... user={user} />
          </li>
        ))}
      </ul>
```

**DB kontenti tarjima QILINMAYDI** (1-faza D-16) — har bunday joyda izoh majburiy
(`user-list.tsx:157-161`):

```tsx
          {/* D-16: ism va telefon DB kontenti — tarjima qilinmaydi. */}
          <p className="truncate text-base font-medium">
            {user.full_name ?? user.phone}
          </p>
```

**Forma dialogi (react-hook-form + zod, tarjimali xato matni):** `create-user-dialog.tsx:77-142`

```tsx
  const schema = useMemo(
    () =>
      z.object({
        phone: z
          .string()
          .min(1, { error: t("errors.required") })
          .refine(looksLikeUzbekPhone, { error: t("auth.invalidPhone") }),
        fullName: z.string(),
        roles: z.array(z.string()).min(1, { error: t("users.rolesRequired") }),
        locale: localeSchema,
      }),
    [t],
  );

  const {
    control,
    formState: { errors, isSubmitting },
    handleSubmit,
    register,
    reset,
    setValue,
  } = useForm<CreateUserValues>({
    resolver: zodResolver(schema),
    defaultValues: EMPTY_VALUES,
  });

  /*
   * `useWatch`, `watch()` EMAS: `watch` — `useForm()` qaytaradigan oddiy
   * funksiya va React Compiler uni memoizatsiya qila olmaydi (eskirgan UI
   * xavfi). `useWatch` esa hook bo'lib, obunani to'g'ri e'lon qiladi.
   */
  const selectedRoles = useWatch({ control, name: "roles" });
```

```tsx
  async function onSubmit(values: CreateUserValues) {
    setFormError(null);
    try {
      const created = await createUser.mutateAsync({...});
      handleOpenChange(false);
      onCreated(created.temporary_password);
    } catch (error) {
      setFormError(t(adminErrorMessageKey(error)));
    }
  }
```

Maydon + xato razmetkasi (`create-user-dialog.tsx:161-177`) — `ui/field.tsx` shundan ajratiladi:

```tsx
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium" htmlFor="create-phone">
                {t("users.phoneLabel")}
              </label>
              <Input
                aria-invalid={errors.phone ? true : undefined}
                autoComplete="off"
                id="create-phone"
                inputMode="tel"
                placeholder={t("auth.phoneHint")}
                type="tel"
                {...register("phone")}
              />
              {errors.phone ? (
                <p className="text-sm text-danger">{errors.phone.message}</p>
              ) : null}
            </div>
```

**Radix Dialog qobig'i (`ui/dialog.tsx` shundan chiqariladi):** `create-user-dialog.tsx:145-154`

```tsx
    <Dialog.Root onOpenChange={handleOpenChange} open={open}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-black/40" />
        <Dialog.Content className="fixed top-1/2 left-1/2 z-50 flex max-h-[calc(100vh-2rem)] w-[min(30rem,calc(100vw-2rem))] -translate-x-1/2 -translate-y-1/2 flex-col gap-4 overflow-y-auto rounded-lg border border-border bg-surface p-6 shadow-raised">
          <Dialog.Title className="text-lg font-semibold">
            {t("users.createTitle")}
          </Dialog.Title>
          <Dialog.Description className="sr-only">
            {t("users.createHint")}
          </Dialog.Description>
```

**Badge (`ui/badge.tsx` shundan):** `user-list.tsx:345-364`

```tsx
function Badge({
  children,
  tone,
}: {
  children: React.ReactNode;
  tone: "success" | "warning" | "danger";
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium",
        tone === "success" && "bg-success/12 text-success",
        tone === "warning" && "bg-warning/20 text-text",
        tone === "danger" && "bg-danger/12 text-danger",
      )}
    >
      {children}
    </span>
  );
}
```

> UI-SPEC §4.2/§12.1 bo'yicha `ui/badge.tsx` ga ko'chirilganda tone'lar
> `text-success-text` / `text-danger-text` / `text-warning-text` ga o'tadi va
> `px-2.5 py-0.5` → `px-2 py-1` (4-panjara).

**Primitiv komponent shakli (`ui/*.tsx`):** `ui/card.tsx:1-34` va `ui/button.tsx:42-59`

```tsx
export type CardProps = ComponentPropsWithRef<"div">;

export function Card({ className, ...props }: CardProps) {
  return (
    <div
      className={cn(
        "rounded-lg border border-border bg-surface shadow-card",
        className,
      )}
      {...props}
    />
  );
}
```

```tsx
export type ButtonProps = ComponentPropsWithRef<"button"> &
  VariantProps<typeof buttonVariants>;

export function Button({
  className,
  variant,
  size,
  type = "button",
  ...props
}: ButtonProps) {
```

> **Qat'iy qoida** (`ui/button.tsx:6-9`, `ui/card.tsx:5-8`, `ui/input.tsx:5-11`):
> *"bu faylda foydalanuvchiga ko'rinadigan hech qanday matn yo'q"* — barcha matn
> `next-intl` orqali `children`/prop bo'lib keladi. Yangi `ui/*` primitivlari shu qoidaga bo'ysunadi.

---

### S-11. Frontend — server holati (TanStack Query)

**Manba:** `frontend/src/lib/queries.ts:21-31, 53-141`

```ts
/*
 * =============================================================================
 * Ma'muriy ekranlarning server holati (01-07 kontrakti).
 *
 * Har bir endpoint FAQAT shu yerda chaqiriladi: komponent `apiFetch` ni
 * to'g'ridan-to'g'ri ishlatmaydi. Sabab — invalidatsiya. ...
 * =============================================================================
 */

export const USERS_PATH = "/users";
export const USERS_QUERY_KEY = ["users"] as const;

export function useUsersQuery(options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: USERS_QUERY_KEY,
    queryFn: () => apiFetch(USERS_PATH, { schema: userListResponseSchema }),
    enabled: options?.enabled ?? true,
  });
}

export function useCreateUser() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: CreateUserInput) =>
      apiFetch(USERS_PATH, {
        method: "POST",
        body: {
          phone: input.phone,
          full_name: input.fullName,
          roles: input.roles,
          locale: input.locale,
        },
        schema: createUserResponseSchema,
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: USERS_QUERY_KEY });
    },
  });
}
```

**Keyset (infinite) so'rov:** `queries.ts:175-210`

```ts
function buildAuditPath(filters: AuditFilters, cursor: string | null): string {
  const params = new URLSearchParams();
  // Backend nomlari `AuditQuery` dan: `from`/`to` alias, qolgani snake_case.
  if (filters.from) params.set("from", filters.from);
  ...
  params.set("limit", String(AUDIT_PAGE_SIZE));
  if (cursor) params.set("cursor", cursor);
  return `${AUDIT_PATH}?${params.toString()}`;
}

export function useAuditQuery(filters: AuditFilters) {
  return useInfiniteQuery({
    queryKey: ["audit", filters],
    queryFn: ({ pageParam }) =>
      apiFetch(buildAuditPath(filters, pageParam), {
        schema: auditListResponseSchema,
      }),
    initialPageParam: null as string | null,
    getNextPageParam: (lastPage) => lastPage.next_cursor,
  });
}
```

**"Ko'proq yuklash" UI:** `audit-list.tsx:100-112`

```tsx
      {auditQuery.hasNextPage ? (
        <div>
          <Button
            disabled={auditQuery.isFetchingNextPage}
            onClick={() => void auditQuery.fetchNextPage()}
            variant="secondary"
          >
            {auditQuery.isFetchingNextPage
              ? t("common.loading")
              : t("audit.loadMore")}
          </Button>
        </div>
      ) : null}
```

**Xato kodi → tarjima kaliti:** `queries.ts:216-251`

```ts
export type AdminErrorMessageKey =
  | "users.phoneTaken"
  | "users.roleNotAllowed"
  | "users.cannotBlockSelf";

export function adminErrorMessageKey(
  error: unknown,
): ErrorMessageKey | AdminErrorMessageKey {
  if (error instanceof ApiError) {
    switch (error.detail) {
      case "phone_taken":
        return "users.phoneTaken";
      ...
      default:
        break;
    }
  }
  return errorMessageKey(error);
}
```

> 2-faza uchun: `stall_code_taken`, `stall_code_retired`, `assignment_overlaps`,
> `tariff_already_set_for_date`, `tariff_past_locked`, `market_incomplete`,
> `import_validation_failed` kabi kodlar **aynan shu switch'ga** qo'shiladi
> (yoki modul bo'yicha bo'lingan `marketErrorMessageKey()` funksiyasiga).
> Ular `api-types.ts::ERROR_CODES` ga ham qo'shiladi.

**URL holati (nuqs):** `audit-filters.tsx:34-73`

```ts
/** Filtrlarning URL nomlari — havolada shu ko'rinishda turadi. */
const auditFilterParsers = {
  from: parseAsString.withDefault(""),
  to: parseAsString.withDefault(""),
  actor: parseAsString.withDefault(""),
  action: parseAsString.withDefault(""),
  table: parseAsString.withDefault(""),
};

export function useAuditFilters(): {
  filters: AuditFilters;
  isEmpty: boolean;
} {
  const [urlFilters] = useQueryStates(auditFilterParsers);

  return {
    filters: {
      from: urlFilters.from,
      ...
    },
    isEmpty: Object.values(urlFilters).every((value) => value === ""),
  };
}
```

> **Bu naqsh usta qadamiga (`?step=N`) to'g'ridan-to'g'ri qo'llanadi:**
> panel va ro'yxat **bir xil hookdan** o'qiydi, holat prop bo'lib uzatilmaydi
> (`audit-filters.tsx:51-56` dagi sabab).

---

### S-12. Zod kontrakti (`api-types.ts`)

**Manba:** `frontend/src/lib/api-types.ts:1-13, 183-215`

```ts
/**
 * core-api HTTP kontraktining runtime sxemalari (01-06 / 01-07).
 *
 * NEGA `zod`, `interface` EMAS: TypeScript tipi kompilyatsiyadan keyin
 * yo'qoladi va noto'g'ri javob shakli faqat komponent ichida `undefined`
 * bo'lib chiqadi. `schema.parse()` esa chegarada, aniq xato bilan yiqiladi ...
 */
```

```ts
export const userListItemSchema = z.object({
  id: z.uuid(),
  phone: z.string(),
  full_name: z.string().nullable(),
  roles: z.array(z.string()),
  is_active: z.boolean(),
  must_change_password: z.boolean(),
  locale: z.string(),
  created_at: z.string(),
});
export type UserListItem = z.infer<typeof userListItemSchema>;

export const userListResponseSchema = z.object({
  items: z.array(userListItemSchema),
});
```

Konventsiyalar: **maydon nomlari backend'dagidek `snake_case`**, sana/vaqt `z.string()`,
UUID `z.uuid()`, pul `soumSchema`, enum ro'yxati `as const` massiv + `isX()` type-guard
(`api-types.ts:230-271` — `AUDIT_ACTIONS`/`isAuditAction`). `StallStatus` uchun aynan shu shakl.

---

### S-13. Testlar — testcontainers + `sbozor_app` roli

**Fixture zanjiri:** `tests/conftest.py:273-322`

```python
@pytest.fixture
def two_markets(sync_owner_conn: Connection[TupleRow], migrated: None) -> Iterator[TwoMarketSeed]:
    """Ikki bozor + beshta foydalanuvchi + oltita a'zolik qatori."""
    seed = seed_two_markets(sync_owner_conn)
    try:
        yield seed
    finally:
        cleanup_two_markets(sync_owner_conn, seed)


@pytest.fixture
def tenant_session(app_sessionmaker: async_sessionmaker[AsyncSession]) -> TenantSessionFactory:
    """Tenant konteksti o'rnatilgan sessiya beruvchi fabrika."""

    @asynccontextmanager
    async def _tenant_session(
        market_id: UUID | None,
        actor_id: UUID | None = None,
        *,
        actor_kind: ActorKind = ActorKind.USER,
        request_id: str = "pytest",
    ) -> AsyncIterator[AsyncSession]:
        async with app_sessionmaker() as session, session.begin():
            await set_tenant_context(...)
            yield session

    return _tenant_session
```

**Yangi seed fayli `tests/fixtures/market_domain.py` `two_markets.py` naqshini takrorlaydi:**
`tests/fixtures/two_markets.py:64-107, 197-296`

```python
@dataclass(frozen=True)
class MarketSeed:
    """Bitta bozor va uning foydalanuvchilari."""

    id: UUID
    name: str
    ...
```

```python
def seed_two_markets(conn: Connection[TupleRow]) -> TwoMarketSeed:
    """Ikki bozor, beshta foydalanuvchi va oltita a'zolik qatorini yozadi.

    `conn` `sbozor_owner` bilan ochilgan va autocommit rejimida bo'lishi
    kerak — ma'lumot boshqa ulanishdagi (`sbozor_app`) testlarga darhol
    ko'rinishi shart.
    """
```

```python
def cleanup_two_markets(conn: Connection[TupleRow], seed: TwoMarketSeed) -> None:
    """Seed'ni to'liq o'chiradi (FK tartibida)."""
    market_ids = [str(market.id) for market in seed.markets]
    ...
    conn.execute("DELETE FROM refresh_tokens WHERE market_id = ANY(%s::uuid[])", (market_ids,))
```

> **Ikki bozor MAJBURIY** (`two_markets.py:1-6`): *"Bitta bozorli seed bilan tenant
> izolyatsiyasini isbotlab bo'lmaydi: '0 qator qaytdi' javobi izolyatsiya ishlaganini ham,
> jadval bo'shligini ham bildirishi mumkin."*
> `market_domain.py` da A bozorida 3 zona / 3 toifa / 6 rasta, B bozorida 1 zona / 2 rasta.

**Konstrayt testi (nazorat holati + rad etish jufti):** `tests/tenancy/test_composite_fk.py:79-107`

```python
def test_same_tenant_reference_is_accepted(
    child_table: Connection[TupleRow], two_markets: TwoMarketSeed
) -> None:
    """NAZORAT HOLATI: to'g'ri juftlik qabul qilinadi.

    Bu test busiz keyingi test yolg'on-yashil bo'lardi — FK hamma narsani
    rad etayotgan bo'lsa ham "cross-tenant bloklandi" deb ko'rinardi.
    """
```

```python
def test_cross_tenant_reference_is_rejected(
    child_table: Connection[TupleRow], two_markets: TwoMarketSeed
) -> None:
    """B bozori qatori A bozorining a'zoligiga havola qila OLMAYDI."""
    with pytest.raises(psycopg.errors.ForeignKeyViolation) as excinfo:
        ...
    assert "fk_probe_membership" in str(excinfo.value)
```

> `stall_assignments` EXCLUDE testi aynan shu juftlik shaklida:
> `psycopg.errors.ExclusionViolation` (SQLSTATE **23P01**) + nazorat holati (kesishmaydigan davr qabul qilinadi).
> `stall_code_registry` testi: `psycopg.errors.UniqueViolation` + nazorat (o'z kodini qaytarib olish ruxsat).

**Chegara jadvali bilan test (tarif tarixi uchun namuna):** `tests/integration/test_business_date.py:41-52`

```python
# RESEARCH Pattern 7 dagi o'lchangan chegara jadvali.
EVENING_UTC = datetime(2026, 11, 5, 18, 30, tzinfo=UTC)
AFTER_MIDNIGHT_UTC = datetime(2026, 11, 5, 19, 30, tzinfo=UTC)
EARLY_MORNING_UTC = datetime(2026, 11, 5, 1, 0, tzinfo=UTC)

EXPECTED = {
    EVENING_UTC: date(2026, 11, 5),
    AFTER_MIDNIGHT_UTC: date(2026, 11, 6),
    EARLY_MORNING_UTC: date(2026, 11, 5),
}
```

**HTTP integratsiya testi:** `tests/fixtures/admin_api.py:44-48` (URL konstantalari) +
`tests/integration/test_users_api.py` (`api_client`, `auth_seed`, `session_headers`).
Yangi URL'lar `admin_api.py::__all__` ga qo'shiladi:

```python
USERS_URL = "/api/v1/users"
PROFILE_URL = "/api/v1/me"
MARKETS_URL = "/api/v1/markets"
AUDIT_URL = "/api/v1/audit"
```

**React komponent testi:** `frontend/src/components/auth/market-picker.test.tsx:21-52, 65-82`

```tsx
const routerMock = vi.hoisted(() => ({ replace: vi.fn() }));

vi.mock("@/i18n/navigation", () => ({
  useRouter: () => routerMock,
}));

const apiClientMock = vi.hoisted(() => ({ apiFetch: vi.fn() }));

vi.mock("@/lib/api-client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api-client")>();
  return { ...actual, apiFetch: apiClientMock.apiFetch };
});
```

```tsx
function renderPicker(): ReturnType<typeof render> {
  // `retry: false` — xato holatida test 3 marta qayta urinishni kutmasligi uchun.
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });

  const tree: ReactElement = (
    <NextIntlClientProvider locale="uz-Latn" messages={messages}>
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <MarketPicker />
        </AuthProvider>
      </QueryClientProvider>
    </NextIntlClientProvider>
  );

  return render(tree);
}
```

> `fireEvent` ishlatiladi, `@testing-library/user-event` **EMAS** (`market-picker.test.tsx:17-19`) —
> u tasdiqlangan paket ro'yxatiga kirmaydi.

---

### S-14. i18n kalitlari

**Mavjud namespace'lar** (`frontend/messages/uz-Latn.json`): `common` (10), `shell` (3),
`roles` (5), `nav` (4), `auth` (21), `users` (30), `audit` (26), `errors` (5).

Konventsiya (UI-SPEC §1.1): **ikki daraja** — `namespace.camelCaseKey`; uchinchi daraja
**faqat enum xaritalari uchun** (`audit.actions.insert`, `audit.tables.markets`).

2-faza qo'shadigan namespace'lar: `stalls`, `vendors`, `zones`, `categories`, `tariffs`,
`calendar`, `map`, `wizard`, `import` + `stalls.status.*`, `import.errors.*` enum xaritalari.

Qo'lda tahrirlanadigan fayllar: `uz-Latn.json` (manba), `ru.json`, `uz-Cyrl.overrides.json`.
`uz-Cyrl.json` — **avtomatik** (`npm run i18n:gen`), qo'l tegizilmaydi.
Darvoza: `npm run i18n:check` (kalit-parity + ICU-argument parity).

---

## 3. Pattern Assignments — fayl bo'yicha

### 3.1 `packages/sbozor-core/sbozor_core/models/market.py` (model, CRUD)

**Analog:** `packages/sbozor-core/sbozor_core/models/identity.py`

**Fayl boshi va docstring shakli** (`identity.py:1-20`) — 2-faza modeli ham shunday
"asosiy arxitektura qarori" bloki bilan boshlanadi (voris modeli vs `daterange` farqi).

**Model shakli** (`identity.py:125-153`) — **har bir yangi jadval uchun to'g'ridan-to'g'ri qolip**:

```python
class UserMarketRole(Base, TenantMixin, TimestampMixin):
    """Bozordagi a'zolik + rollar to'plami (D-05)."""

    __tablename__ = "user_market_roles"
    __table_args__ = (
        ForeignKeyConstraint(
            ["market_id"], ["markets.id"], name="fk_user_market_roles_market_id_markets"
        ),
        ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_user_market_roles_user_id_users",
            ondelete="CASCADE",
        ),
        # Bitta bozorda bitta foydalanuvchi — bitta a'zolik qatori.
        # Bu ayni paytda `(market_id, user_id)` indeksining o'zi ham.
        UniqueConstraint("market_id", "user_id", name="uq_user_market_roles_market_id_user_id"),
        # COMPOSITE FK MAQSADI UCHUN: keyingi fazalardagi jadvallar
        # `(market_id, id)` ga havola qiladi va shu bilan cross-tenant
        # bog'lanish STRUKTURAVIY imkonsiz bo'ladi (T-01-26).
        UniqueConstraint("market_id", "id", name="uq_user_market_roles_market_id_id"),
        # Qisqa mantiqiy nomlar — `ck` konvensiyasi prefiksni o'zi qo'shadi.
        CheckConstraint(ROLES_SUBSET_CHECK, name="roles_allowed"),
        CheckConstraint("cardinality(roles) > 0", name="roles_not_empty"),
    )

    id: Mapped[UUID] = uuid_pk()
    user_id: Mapped[UUID] = mapped_column(PgUuid(as_uuid=True), nullable=False)
    roles: Mapped[list[str]] = mapped_column(ARRAY(Text()), nullable=False)
```

**`CheckConstraint` nomi — QISQA mantiqiy nom** (`identity.py:99-106`):

```python
        # DIQQAT: `ck` konvensiyasi `ck_%(table_name)s_%(constraint_name)s`,
        # ya'ni bu yerga QISQA mantiqiy nom beriladi va yakuniy nom
        # `ck_users_locale_allowed` bo'ladi. To'liq nom yozilsa u ikki marta
        # prefikslanadi (`ck_users_ck_users_...`).
        CheckConstraint(LOCALE_CHECK, name="locale_allowed"),
```

**Enum'dan hosil qilinadigan CHECK** (`identity.py:56-75`) — `StallStatus` uchun aynan shu:

```python
ROLE_VALUES: tuple[str, ...] = tuple(role.value for role in Role)
LOCALE_VALUES: tuple[str, ...] = tuple(locale.value for locale in Locale)


def _quoted(values: Iterable[str]) -> str:
    """SQL literal ro'yxati. Qiymatlar `StrEnum` a'zolari — tashqi kirish emas."""
    return ", ".join(f"'{value}'" for value in values)


ROLES_SUBSET_CHECK = f"roles <@ ARRAY[{_quoted(ROLE_VALUES)}]::text[]"
"""...
Ifoda `sbozor_core.enums.Role` dan HOSIL QILINADI, qo'lda ko'chirilmaydi.
Enum o'zgarib migratsiya unutilsa, `tests/tenancy/test_meta.py::
test_role_check_constraint_matches_enum` bazadagi amaldagi konstraytni
enum bilan solishtirib darvozani yopadi.
"""

LOCALE_CHECK = f"locale IN ({_quoted(LOCALE_VALUES)})"
```

→ `STALL_STATUS_CHECK = f"status IN ({_quoted(STALL_STATUS_VALUES)})"` va migratsiyada
`sa.CheckConstraint(STALL_STATUS_CHECK, name="status_allowed")`.

**Generated column** (`models/ops.py:108-112`) — `tariffs.business_date` uchun (yuqorida §S-6).

**`updated_at` YO'Q bo'lgan model** (`identity.py:156-163`) — `stall_assignments`,
`tariffs`, `stall_category_periods` uchun aynan shu sabab (o'zgarmas hodisa yozuvi):

```python
class RefreshToken(Base, TenantMixin):
    """...

    `updated_at` ATAYIN YO'Q: token qatori o'zgarmas hodisa yozuvi —
    u faqat bekor qilinadi (`revoked_at`) va almashtiriladi
    (`replaced_by_jti`), tahrir qilinmaydi.
    """
```

**Barrel'ga qo'shish MAJBURIY:** `models/__init__.py:1-7`

```python
"""SBOZOR ORM modellari.

`Base.metadata` — Alembic `target_metadata` sining yagona manbai. Har bir
model moduli SHU YERDA import qilinishi shart: import qilinmagan modul
metadata'ga tushmaydi va autogenerate uni "o'chirilgan jadval" deb hisoblab
`op.drop_table()` taklif qiladi.
"""
```

---

### 3.2 `migrations/versions/0006_market_domain.py` … `0009_calendar.py`

**Analog:** `migrations/versions/0001_identity.py` (jadval + RLS), `0002_audit.py` (trigger),
`0004_user_admin.py` (faqat funksiya).

**Migratsiya fayl boshi** (`0001_identity.py:1-53`):

```python
"""identity: markets, users, user_market_roles, refresh_tokens + RLS + login funksiyalari

Revision ID: 0001
Revises:
Create Date: 2026-07-29

Bu migratsiya uch narsani BIRGA o'rnatadi va ular ajralmas:
  ...
"""

from __future__ import annotations

from collections.abc import Sequence
...

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None
```

→ `0006`: `revision = "0006"`, `down_revision = "0005"`. Zanjir uzilmasin.

**`downgrade()` HAR DOIM yoziladi va teskari tartibda** (`0001_identity.py:237-252`,
`0002_audit.py:174-192`):

```python
def downgrade() -> None:
    """Downgrade schema."""
    for function in reversed(ALL_FUNCTIONS):
        drop_entity(function)

    for table in reversed(RLS_TABLES):
        drop_entity(owner_bootstrap_policy(table))
    for table in reversed(TENANT_TABLES):
        drop_entity(tenant_policy(table))
    ...
    op.drop_index("ix_refresh_tokens_market_id_user_id_expires_at", table_name="refresh_tokens")
    op.drop_table("refresh_tokens")
```

**Xavfsizlik uchun kritik DDL — ATAYIN literal** (`0001_identity.py:133-138`, `0002_audit.py:128-135`):

```python
    # Bu satr ATAYIN literal yozilgan (yordamchi `revoke_app_all()` mavjud
    # bo'lsa ham): xavfsizlik uchun eng kritik DDL o'qiganda ham, `grep`
    # qilganda ham ko'rinib turishi shart.
    op.execute("REVOKE ALL ON TABLE users FROM sbozor_app")
```

**Kengaytma tekshiruvi (`0008_vendors.py`)** — RESEARCH Code Example 1 dagi
`raise RuntimeError(...)` bloki; `btree_gist` ni `sbozor_owner` **o'rnata olmaydi**
(empirik). `ops/db/init/00-extensions.sql` ning analogi — `ops/db/init/01-roles.sql`,
u `tests/conftest.py:138-156` da **verbatim o'qib bajariladi**:

```python
@pytest.fixture(scope="session", autouse=True)
def _bootstrap_roles(pg_container: PgEndpoint) -> None:
    """`ops/db/init/01-roles.sql` ni VERBATIM bajaradi, so'ng parol beradi.

    Rol atributlari (NOSUPERUSER / NOBYPASSRLS) bu yerda QAYTA YOZILMAYDI —
    ular faqat SQL faylida yashaydi. Shu sababli meta-test prod DDL'ini
    tekshiradi, testga xos nusxani emas.
    """
    roles_sql = ROLES_SQL_PATH.read_text(encoding="utf-8")
```

→ `00-extensions.sql` ham shu tarzda `conftest.py` da superuser ulanishi bilan bajarilishi kerak
(`sync_superuser_conn` mavjud, `conftest.py:212-231`), aks holda `0008` testda yiqiladi.

---

### 3.3 `services/core-api/app/api/v1/stalls.py` (va zones / categories / calendar / tariffs)

**Analog:** `services/core-api/app/api/v1/users.py`

**Router e'loni va modul strukturasi** (`users.py:79-105`):

```python
log = structlog.get_logger(__name__)

router = APIRouter(tags=["users"])
```

**GET (ro'yxat) + POST (yaratish) juftligi** (`users.py:178-250`):

```python
@router.get("", response_model=UserListResponse)
async def list_users(principal: UserViewerDep, session: TenantSessionDep) -> UserListResponse:
    """Joriy bozor a'zolari (`USER_VIEW`)."""
    repo = UserRepository(session, _market_id(principal))
    members = await repo.list_members()
    return UserListResponse(
        items=[
            UserListItem(
                id=member.user_id,
                ...
            )
            for member in members
        ]
    )


@router.post("", status_code=status.HTTP_201_CREATED, response_model=CreateUserResponse)
async def create_user(
    payload: CreateUserRequest,
    principal: UserManagerDep,
    session: TenantSessionDep,
) -> CreateUserResponse:
    """..."""
    _assert_roles_assignable(principal, payload.roles)
    ...
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="phone_taken")
```

**`market_id` ni olish yordamchisi — har router faylida takrorlanadi** (`users.py:113-125`,
`audit.py:115-122` da ham aynan bir xil):

```python
def _market_id(principal: Principal) -> UUID:
    """Tanlangan bozor.

    `TenantSessionDep` allaqachon 409 qaytargan bo'lardi; bu tekshiruv
    mypy uchun emas, KELAJAK uchun: kimdir endpointni tenant sessiyasisiz
    qayta yozsa, `market_id=None` bilan a'zolik qatori yozilib ketmasin.
    """
    if principal.market_id is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="market_not_selected",
        )
    return principal.market_id
```

**204 javob (yozuvsiz amal)** (`users.py:253-290`):

```python
@router.post(
    "/{user_id}/block",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def block_user(...) -> Response:
    ...
    return Response(status_code=status.HTTP_204_NO_CONTENT)
```

**Ro'yxatga qo'shish:** `services/core-api/app/main.py:43-47, 124-128`

```python
from app.api.v1.audit import router as audit_router
from app.api.v1.auth import router as auth_router
from app.api.v1.markets import router as markets_router
...
app.include_router(auth_router, prefix=f"{API_V1_PREFIX}/auth")
app.include_router(users_router, prefix=f"{API_V1_PREFIX}/users")
app.include_router(me_router, prefix=f"{API_V1_PREFIX}/me")
app.include_router(markets_router, prefix=f"{API_V1_PREFIX}/markets")
app.include_router(audit_router, prefix=f"{API_V1_PREFIX}/audit")
```

> `tests/tenancy/test_route_coverage.py` mavjud — yangi marshrutlar u yerda ham qamrovga tushadi.

---

### 3.4 `services/core-api/app/api/v1/vendors.py` (router, CRUD + o'qish auditi)

**Analog:** `services/core-api/app/api/v1/audit.py` (dependency e'lon tartibi) + `users.py` (CRUD).

RESEARCH Pattern 10 aynan bu faylni ko'rsatadi. Dependency zanjiri (`audit.py:94-104` naqshi):

```python
VendorViewerDep = Annotated[Principal, Depends(require_permission(Permission.VENDOR_VIEW))]
VendorReadIntentDep = Annotated[
    AuditReadIntent, Depends(audit_read(TABLE_VENDORS, reason="vendor_view")),
]
```

Endpoint signaturasida tartib **majburiy**: `principal` (huquq) → `intent` (o'qish niyati) →
`session`. Endpoint oxirida `intent.filters` va `intent.result_count` to'ldiriladi
(`audit.py:191-192`):

```python
    intent.filters = _describe(query)
    intent.result_count = len(page.rows)
```

`_describe()` (`audit.py:125-133`) — `cursor` chiqarib tashlanadi, `limit` qoladi:

```python
def _describe(query: AuditQuery) -> dict[str, Any]:
    """Qo'llangan filtrlarning JSON tavsifi — o'qish yozuvi uchun."""
    return query.model_dump(mode="json", exclude_none=True, exclude={"cursor"}, by_alias=True)
```

`TABLE_VENDORS` konstantasi `app/security/audit.py:59-69` yoniga:

```python
TABLE_USERS = "users"
"""`login`, `login_failed`, `password_changed` — hodisa foydalanuvchiga tegishli."""
```

---

### 3.5 `services/core-api/app/repositories/*_repo.py`

**Analog:** `services/core-api/app/repositories/user_repo.py`

**Sinf + `scoped()` ishlatilishi** (`user_repo.py:132-167`):

```python
class UserRepository(TenantScopedRepository):
    """Joriy bozor a'zolari ustidagi o'qish va yozish (D-04, D-02, D-08)."""

    async def member_roles(self, user_id: UUID) -> tuple[str, ...] | None:
        """Foydalanuvchining JORIY BOZORDAGI rollari; a'zo bo'lmasa `None`.

        Bu — cross-tenant himoyasining ilova tomonidagi darvozasi (T-01-51).
        Boshqa bozorning `user_id` si uchun RLS 0 qator beradi va chaqiruvchi
        **404** qaytaradi.
        """
        stmt = self.scoped(select(UserMarketRole.roles).where(UserMarketRole.user_id == user_id))
        result = await self.session.execute(stmt)
        row = result.one_or_none()
        return None if row is None else tuple(row.roles or ())
```

**INSERT — `RETURNING` so'ralmaydi** (`user_repo.py:196-213`):

```python
    async def add_membership(self, user_id: UUID, roles: list[str]) -> None:
        """A'zolik qatorini JORIY BOZORDA yaratadi (RLS `WITH CHECK` ostida).

        `RETURNING` ATAYIN so'ralmaydi: qator identifikatori chaqiruvchiga
        kerak emas va `INSERT ... RETURNING` policy tekshiruvining ikkinchi
        yo'lini ochadi (01-06 da `audit_log` da aynan shu narsa login
        endpointini yiqitgan edi).

        Audit yozuvi bu yerda YOZILMAYDI — `user_market_roles` da
        `fn_audit_row()` triggeri bor va u xom SQL yo'lini ham qamraydi.
        """
        await self.session.execute(
            insert(UserMarketRole).values(
                market_id=self.market_id,
                user_id=user_id,
                roles=roles,
            )
        )
```

> ⚠ `stalls`/`vendors` yaratishda `id` kerak bo'lsa `RETURNING` ishlatiladi — lekin
> **`SELECT` policy'si o'sha qatorga qo'llanadi**. Tenant jadvallarida bu ishlaydi
> (`tenant_policy` `FOR ALL` — `USING` ham bor), `audit_log` da esa yo'q edi.
> Import yo'lida `pg_insert(...).on_conflict_do_nothing(...).returning(Stall.id)` xavfsiz.

**Frozen dataclass qaytarish shakli** (`user_repo.py:59-71`):

```python
@dataclass(frozen=True)
class MarketUser:
    """Bozor a'zosi — a'zolik (RLS) va profil (`SECURITY DEFINER`) birlashmasi."""

    user_id: UUID
    phone: str
    ...
```

---

### 3.6 `services/core-api/app/api/v1/markets.py` (MOD — usta 1- va 9-qadamlari)

**Analog:** o'zi + `users.py::create_user`.

Mavjud fayl docstringi (`markets.py:1-47`) **saqlanadi va kengaytiriladi** — u
"bu yerda RLS'ni chetlab o'tish yo'li yo'q" da'vosini ushlab turadi.

`POST /markets` `users.py::create_user` naqshini takrorlaydi:
1. Huquq darvozasi (`require_permission(MARKET_MANAGE)`) — DB'ga tegilmasdan;
2. `market_create()` `SECURITY DEFINER` (repo orqali, `_CREATE_USER` naqshi);
3. `market_profile` qatori **shu tranzaksiyada**;
4. `write_app_audit(action=INSERT, table_name=TABLE_MARKETS, ...)` — funksiya ichida trigger yo'q.

> ⚠ 1-qadamda tenant konteksti hali **yo'q** (`app.market_id` bo'sh). Ya'ni bu endpoint
> `TenantSessionDep` **emas**, `AuthSessionDep` oladi (`deps.py:210-236`) — `audit.py:200-207`
> dagi `list_platform_audit` bilan aynan bir xil sabab. `market_profile` qatori esa
> tenant kontekstini talab qiladi → 2-qadam (`select-market`) dan keyin yoziladi
> **yoki** `market_create()` funksiyasi ikkalasini birga yaratadi. Rejalashtiruvchi bu ikkitadan
> birini tanlab, sababini plan'da yozsin.

`GET /markets/{id}/setup-status` — sof o'qish, hisoblanadi, saqlanmaydi (RESEARCH Pattern 5).
`_CURRENT_MARKET` naqshi (`markets.py:63-71`) — **filtrsiz so'rov**, RLS o'zi cheklaydi:

```python
_CURRENT_MARKET = text("SELECT id, name, timezone, is_active FROM markets")
"""ATAYIN FILTRSIZ.

`markets` policy'si `id = NULLIF(current_setting('app.market_id', true), '')
::uuid`, ya'ni bu so'rov AYNAN BITTA qator qaytaradi. Filtr yozilganda
noto'g'ri o'rnatilgan tenant konteksti ko'rinmay qolardi; filtrsiz shaklda
u 0 qator bo'lib DARHOL ko'rinadi.
"""
```

---

### 3.7 `services/core-api/app/schemas.py` (MOD) — Pydantic v2 shakllari

**Analog:** o'zi.

Fayl docstringi (`schemas.py:1-10`) chegara qoidasini o'rnatadi:

```python
"""HTTP kontrakt shakllari (Pydantic 2.13).

Chegara qoidalari shu yerda qulflanadi:

* **Telefon CHEGARADA normallashtiriladi** (D-01). ...
* **Parol siyosati BITTA joyda** — `validate_password_strength()`.
"""
```

**Telefon validatori — `vendors` uchun AYNAN takrorlanadi** (`schemas.py:190-197`):

```python
    @field_validator("phone")
    @classmethod
    def _normalize(cls, value: str) -> str:
        """E.164 ga keltiradi (D-01: telefon — yagona identifikator)."""
        try:
            return normalize_phone(value)
        except InvalidPhoneError as exc:
            raise ValueError(str(exc)) from exc
```

**Enum ustidagi maydon** (`schemas.py:175-188`) — `StallStatus` uchun aynan shu:

```python
class CreateUserRequest(BaseModel):
    """`POST /users` — ikki bosqichli yaratishning so'rov shakli (D-04).

    `roles` `Role` enum ustida: noma'lum rol nomi 422 beradi va u hech
    qachon `user_market_roles.roles` ga yetib bormaydi. KIM qaysi rolni
    bera olishi (rol berish DARAJASI) esa bu yerda EMAS — u endpoint
    mantiqida, chunki javob 403 bo'lishi kerak, 422 emas.
    """

    phone: str
    full_name: str | None = None
    roles: Annotated[list[Role], Field(min_length=1)]
    locale: Locale = Locale.UZ_LATN
```

`__all__` alifbo tartibida saqlanadi (`schemas.py:22-46`). Fayl allaqachon 353 qator —
rejalashtiruvchi domen sxemalarini `app/schemas.py` ga qo'shish yoki
`app/schemas/market.py` ga bo'lish qarorini plan'da hujjatlashtirsin (bo'linsa,
mavjud `from app.schemas import ...` importlari buzilmasligi uchun `app/schemas/__init__.py`
re-export beradi).

---

### 3.8 `services/core-api/app/api/v1/imports.py` + `app/services/xlsx_*.py`

**Analoglar:** yo'q (pastdagi "No Analog Found"). Lekin **chegara naqshlari mavjud**:

- Xato javobi shakli — `users.py:238` (409) va `audit.py:181-189` (422);
- 422 tanasi qator-raqamli ro'yxat bo'ladi → yangi Pydantic model
  (`AuditListResponse` shakli, `schemas.py:349-353` naqshi);
- Bitta tranzaksiya — `get_tenant_session` allaqachon `session.begin()` ichida
  (`deps.py:420-429`), ya'ni endpoint **hech nima qo'shmaydi**: istisno → rollback (D-14 avtomatik);
- `StreamingResponse` bilan shablon berish — loyihada birinchi marta;
  `python-multipart` allaqachon bog'liqlikda (CLAUDE.md).

---

### 3.9 Frontend — `stall-map.tsx` va `stall-cell.tsx`

**Analog:** yo'q. **Kontrakt** RESEARCH Pattern 11 + UI-SPEC §7.1-7.2 da to'liq berilgan
(katak — haqiqiy `<button>`, `React.memo`, tanlangan ID katak propiga tushmaydi,
`key={stall.id}`, CSS Grid `repeat(auto-fill, minmax(3rem, 1fr))`).

**Qayta ishlatiladigan qismlar:**
- `cn()` (`frontend/src/lib/cn.ts`) — variant class'lari uchun;
- `cva` naqshi (`ui/button.tsx:10-40`) — `TONE_STYLES` uchun to'g'ridan-to'g'ri qolip;
- Dialog (`user-list.tsx:293-342`) — rasta kartasi;
- `useFormatter()` (`user-list.tsx:146`, `audit-list.tsx:127`) — sana/son formatlash.

---

## 4. No Analog Found

Bu fayllar uchun kodbazada yaqin analog yo'q — planner RESEARCH/UI-SPEC naqshlariga tayanadi.

| Fayl | Rol | Data flow | Sabab | Nimaga tayaniladi |
|------|-----|-----------|-------|--------------------|
| `services/core-api/app/services/xlsx_reader.py` | service | file-I/O | Loyihada birorta fayl o'qish yo'li yo'q; `openpyxl` yangi bog'liqlik | RESEARCH Pitfall 5 (zip-bomba darvozasi, `defusedxml`), Arxitektura diagrammasidagi 6 bosqich |
| `services/core-api/app/services/xlsx_template.py` | service | file-I/O (stream) | `XlsxWriter` hali ishlatilmagan; `StreamingResponse` loyihada yo'q | CLAUDE.md (`io.BytesIO` → `StreamingResponse`) |
| `services/core-api/app/services/import_validator.py` | service | transform | Ko'p-xatoli validatsiya naqshi yo'q (mavjud kod bitta xato bilan yiqiladi) | RESEARCH Code Example 3 (`ImportError_` dataclass, qator+kod+xabar) |
| `frontend/src/components/import/{import-panel,import-errors}.tsx` | component | file-I/O | Fayl yuklash UI'si yo'q | UI-SPEC §8.5 (4 holatli oqim) |
| `frontend/src/components/stalls/{stall-map,stall-cell,stall-tone,stall-map-legend}.tsx` | component | derived state | Grid/canvas render naqshi yo'q | RESEARCH Pattern 11 + UI-SPEC §7 |
| `frontend/src/components/wizard/*` | component | request-response | Ko'p qadamli oqim naqshi yo'q (eng yaqini `app-shell.tsx` navigatsiyasi) | UI-SPEC §6 + RESEARCH Pattern 5 |

> Diqqat: bu fayllarda ham **§0 umumiy konventsiyalar** va **§S-10/§S-11** (holat to'rtligi,
> TanStack Query, xato→tarjima xaritasi) baribir qo'llanadi — analog yo'qligi
> "yangi uslub" degani emas.

---

## 5. Wave 0 — birinchi migratsiyadan OLDIN bajariladigan tuzatishlar

Bular yangi kod emas, **mavjud fayllarni tuzatish**. Ularsiz birinchi migratsiya yoki
birinchi ekran yiqiladi.

| # | Fayl | O'zgarish | Sabab (manba) |
|---|------|-----------|----------------|
| W0-A | `packages/sbozor-core/sbozor_core/schema_contract.py:49-57` | `stall_assignments` ni `FINANCIAL_TABLES` dan olib tashlash | `test_financial_tables_have_guards` `CHECK (amount_soum > 0)` talab qiladi; jadvalda pul ustuni yo'q (RESEARCH Pitfall 3) |
| W0-B | `services/core-api/app/security/rbac.py:71-79` + `frontend/src/lib/rbac.ts:48-54` | `PLATFORM_ADMIN` ga `STALL_MANAGE`/`TARIFF_MANAGE`/`VENDOR_MANAGE` + yangi `MARKET_DATA_VIEW`/`VENDOR_VIEW` | Aks holda MARKET-01 ni bajaradigan odam rasta kirita olmaydi (RESEARCH Pitfall 6, Code Example 6) |
| W0-C | `ops/db/init/00-extensions.sql` (yangi) + `tests/conftest.py` | `CREATE EXTENSION btree_gist` superuser bilan | `sbozor_owner` uni o'rnata olmaydi — empirik (RESEARCH Pitfall 1) |
| W0-D | `services/core-api/app/api/v1/auth.py` (WR-02, WR-03) | `select-market` ni `require_password_current` ostiga olish + `is_platform_admin` ni DB'dan qayta o'qish | 1-faza `01-REVIEW-GAPS.md:307-311`: *"the moment one is added (market wizard...) this becomes a live authorization bypass"* — bu faza aynan o'sha usta |
| W0-E | 6 fayl zanjiri (UI-SPEC §12.1.1) | `MarketRef` ga `is_active` qo'shish: `auth_memberships()` SQL → `auth_repo.Membership` → `schemas.MarketRef` → `auth.py::_visible_markets` (8 joy) → `api-types.marketRefSchema` → `market-picker.tsx` | Qoralama bozor bozor tanlash ekraniga yetib bormaydi (o'lchandi). **Tartib majburiy: 1→2→3→4→5→6** |
| W0-F | `frontend/src/app/globals.css` | 6 token tuzatish + 4 yangi token + `@media (pointer: coarse)` | UI-SPEC §4.2 — o'lchangan WCAG AA buzilishlari |
| W0-G | `frontend/src/components/ui/{dialog,field,select,badge,skeleton,empty-state,confirm-dialog}.tsx` | Mavjud inline nusxalardan ajratish | UI-SPEC §1.2 — 2-faza +9 ekran qo'shadi, nusxa 9 taga chiqmasin |
| W0-H | `frontend/messages/uz-Cyrl.overrides.json` + `frontend/scripts/gen-cyrillic.test.mjs` | 5 so'z + T-01…T-04 assertion | UI-SPEC §5.2 — transliterator "Excel" ni buzadi |

---

## Metadata

**Analog search scope:**
`migrations/` (helpers, entities, versions 0001-0005) ·
`packages/sbozor-core/sbozor_core/` (models, tenancy, money, timeutil, phone, enums, schema_contract) ·
`services/core-api/app/` (deps, main, schemas, api/v1, repositories, security) ·
`tests/` (conftest, fixtures, tenancy, integration) ·
`frontend/src/` (app, components, lib, i18n) · `frontend/messages/`

**Files scanned:** 158 tracked (planning tashqarisida) · **fully read:** 42 · **targeted read:** 6

**Pattern extraction date:** 2026-07-31

**Upstream:** `02-CONTEXT.md` (D-01…D-20) · `02-RESEARCH.md` (Pattern 1-11, Pitfall 1-10, Code Example 1-6) · `02-UI-SPEC.md` (§1, §6, §7, §8, §12)
