"""market_domain: bozor profili, zonalar, toifalar, rastalar, kod reyestri + RLS + D-02

Revision ID: 0007
Revises: 0006
Create Date: 2026-07-31

=============================================================================
BU MIGRATSIYA UCH NARSANI BIRGA O'RNATADI VA ULAR AJRALMAS:

  1. SXEMA — beshta jadval, composite-FK maqsadli `UNIQUE(market_id, id)`
     konstraytlari va `market_id` bilan boshlanadigan indeks (P9).
  2. TENANT IZOLYATSIYASI — `ENABLE` + `FORCE ROW LEVEL SECURITY` + policy.
     Uchtasidan bittasi tushib qolsa jadval JIMGINA ochiq qoladi.
  3. D-02 KAFOLATI — `stall_code_registry` + `trg_stall_code_claim`: bozorda
     bir marta ishlatilgan rasta raqami boshqa rastaga hech qachon o'tmaydi.

ULARNI ALOHIDA MIGRATSIYAGA BO'LISH — XATO BO'LARDI: oraliqda "jadval bor,
lekin policy yo'q" oynasi ochilardi va o'sha oynada bajarilgan har qanday
seed/import cross-tenant qatorlarni yozib qo'yardi. `alembic upgrade head`
atomik emas (har bir revision o'z tranzaksiyasida), ya'ni oyna nazariy emas.
=============================================================================

AUDIT TRIGGERI ATAYIN FAQAT IKKI JADVALGA ULANADI (`market_profile`,
`stalls`). Qolgan uchtasi uchun sabab — `sbozor_core.schema_contract.
AUDITED_TABLES` docstringida, lekin eng muhimini shu yerda takrorlaymiz,
chunki "unutilgan" deb ko'rinadi:

  * `zones` / `stall_categories` — nomlar LUG'ATI, moliyaviy ham, huquqiy
    ham yozuv emas; ularga havola qiluvchi jadvallar allaqachon auditda.
  * `stall_code_registry` — birlamchi kaliti `(market_id, code)`, ya'ni unda
    `id uuid` USTUNI YO'Q. `fn_audit_row()` esa `row_id` ni `uuid` ga
    keltiradi (`COALESCE((v_new ->> 'id')::uuid, ...)`) va bunday jadvalda
    HAR DML da yiqilardi. Trigger qo'shish = rasta yaratishni butunlay
    ishlamay qo'yish.

⚠ "TO'LIQLIK UCHUN" UCHINCHI TRIGGERNI QO'SHMANG — migratsiya yiqiladi.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

import sqlalchemy as sa
from alembic import op
from sbozor_core.models.market import (
    OPEN_WEEKDAYS_CHECK,
    STALL_CODE_SORT_EXPR,
    STALL_STATUS_CHECK,
)
from sqlalchemy.dialects import postgresql as pg

from migrations.entities import MARKET_DOMAIN_TENANT_TABLES
from migrations.entities.functions import (
    MARKET_CORE_FUNCTIONS,
    MARKET_CORE_GRANT_SIGNATURES,
)
from migrations.entities.policies import owner_bootstrap_policy, tenant_policy
from migrations.entities.triggers import STALL_CODE_CLAIM
from migrations.helpers import (
    APP_ROLE,
    attach_audit_trigger,
    create_entity,
    detach_audit_trigger,
    drop_entity,
    enable_tenant_rls,
)

# revision identifiers, used by Alembic.
revision: str = "0007"
down_revision: str | Sequence[str] | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

AUDITED_TABLES: tuple[str, ...] = ("market_profile", "stalls")
"""Shu migratsiyada `fn_audit_row()` ulanadigan jadvallar (D-10).

`sbozor_core.schema_contract.AUDITED_TABLES` — bu ro'yxatning kod-tomondagi
nusxasi; ikkalasining mosligi `tests/tenancy/test_meta.py::
test_audited_tables_have_trigger` bilan qulflangan.
"""

STALL_CODE_CLAIM_TRIGGER = "trg_stall_code_claim"


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


def _updated_at() -> sa.Column[datetime]:
    return sa.Column(
        "updated_at",
        sa.DateTime(timezone=True),
        server_default=sa.text("now()"),
        nullable=False,
    )


def upgrade() -> None:
    """Upgrade schema."""
    # ------------------------------------------------------------------
    # 1. market_profile — bozorga AYNAN BITTA qator.
    #
    #    `UNIQUE(market_id)` bu yerda tozalik emas, FUNKSIYANING ISHLASH
    #    SHARTI: `market_is_open()` (0010) profilni SKALYAR subquery bilan
    #    o'qiydi va ikkinchi qator paydo bo'lsa "more than one row returned"
    #    bilan yiqilardi. U ayni paytda tenant indeksining o'zi ham
    #    (`market_id` bilan boshlanadi, P9).
    # ------------------------------------------------------------------
    op.create_table(
        "market_profile",
        _market_id(),
        _uuid_pk(),
        # A3: barcha BOSHLANG'ICH `valid_from` (birinchi tarif va birinchi
        # toifa davri) AYNAN shu sanadan olinadi, import kunidan EMAS.
        sa.Column("operating_since", sa.Date(), nullable=False),
        # D-17: ISO kun raqamlari (1=dushanba … 7=yakshanba) — `EXTRACT(ISODOW
        # FROM ...)` bilan bir xil asosda, ya'ni konversiya yozilmaydi.
        sa.Column(
            "open_weekdays",
            pg.ARRAY(sa.SmallInteger()),
            server_default=sa.text("'{1,2,3,4,5,6,7}'"),
            nullable=False,
        ),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("tin", sa.Text(), nullable=True),
        sa.Column("bank_account", sa.Text(), nullable=True),
        sa.Column("bank_mfo", sa.Text(), nullable=True),
        sa.Column("contact_phone", sa.Text(), nullable=True),
        _created_at(),
        _updated_at(),
        sa.PrimaryKeyConstraint("id", name="pk_market_profile"),
        sa.ForeignKeyConstraint(
            ["market_id"], ["markets.id"], name="fk_market_profile_market_id_markets"
        ),
        sa.UniqueConstraint("market_id", name="uq_market_profile_market_id"),
        sa.UniqueConstraint("market_id", "id", name="uq_market_profile_market_id_id"),
        # `ck` konvensiyasi prefiksni O'ZI qo'shadi (`ck_<table>_<name>`).
        sa.CheckConstraint(OPEN_WEEKDAYS_CHECK, name="open_weekdays_valid"),
        # A2 TAXMINI: STIR — 9 raqam. Ifoda `MarketProfile` modelidagi bilan
        # AYNAN bir xil bo'lishi shart; u model tomonda konstantaga
        # chiqarilmagani uchun bu yerda literal (yagona nusxa emas, LEKIN
        # ikkalasi ham bitta qarorni yozadi va farqi code review'da ko'rinadi).
        sa.CheckConstraint("tin IS NULL OR tin ~ '^[0-9]{9}$'", name="tin_format"),
    )

    # ------------------------------------------------------------------
    # 2. zones — YASSI ro'yxat, ierarxiya YO'Q (D-03).
    # ------------------------------------------------------------------
    op.create_table(
        "zones",
        _market_id(),
        _uuid_pk(),
        sa.Column("name", sa.Text(), nullable=False),
        _created_at(),
        _updated_at(),
        sa.PrimaryKeyConstraint("id", name="pk_zones"),
        sa.ForeignKeyConstraint(["market_id"], ["markets.id"], name="fk_zones_market_id_markets"),
        # Import zonaga NOM bo'yicha bog'laydi (D-14), shuning uchun nom ham
        # UNIQUE, ham bo'sh bo'lmasligi kerak: bo'sh nom hech qachon mos
        # kelmaydi va jimgina "fantom" zona yaratardi.
        sa.UniqueConstraint("market_id", "name", name="uq_zones_market_id_name"),
        sa.UniqueConstraint("market_id", "id", name="uq_zones_market_id_id"),
        sa.CheckConstraint("length(btrim(name)) > 0", name="name_not_blank"),
    )

    # ------------------------------------------------------------------
    # 3. stall_categories — tarif kalitining O'ZI (D-05).
    #    Rasta bilan bog'lanish TO'G'RIDAN-TO'G'RI EMAS: `stalls.category_id`
    #    ustuni ATAYIN YO'Q (D-04), tarix `stall_category_periods` da (0008).
    # ------------------------------------------------------------------
    op.create_table(
        "stall_categories",
        _market_id(),
        _uuid_pk(),
        sa.Column("name", sa.Text(), nullable=False),
        _created_at(),
        _updated_at(),
        sa.PrimaryKeyConstraint("id", name="pk_stall_categories"),
        sa.ForeignKeyConstraint(
            ["market_id"], ["markets.id"], name="fk_stall_categories_market_id_markets"
        ),
        sa.UniqueConstraint("market_id", "name", name="uq_stall_categories_market_id_name"),
        sa.UniqueConstraint("market_id", "id", name="uq_stall_categories_market_id_id"),
        sa.CheckConstraint("length(btrim(name)) > 0", name="name_not_blank"),
    )

    # ------------------------------------------------------------------
    # 4. stalls — "band, lekin to'lovsiz" da'vosining tayanch obyekti.
    # ------------------------------------------------------------------
    op.create_table(
        "stalls",
        _market_id(),
        _uuid_pk(),
        sa.Column("zone_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        # INSON-RAQAMLI tartib DB kafolati (2 < 10 < 100). Ifoda MODELDAN
        # olinadi — DDL tomonda qayta yozilsa ikkinchi haqiqat manbai paydo
        # bo'lardi va ro'yxat bilan xarita boshqa-boshqa tartibda chiqardi.
        sa.Column(
            "code_sort",
            sa.Text(),
            sa.Computed(STALL_CODE_SORT_EXPR, persisted=True),
            nullable=False,
        ),
        sa.Column("status", sa.Text(), server_default=sa.text("'active'"), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        _created_at(),
        _updated_at(),
        sa.PrimaryKeyConstraint("id", name="pk_stalls"),
        sa.ForeignKeyConstraint(["market_id"], ["markets.id"], name="fk_stalls_market_id_markets"),
        # D-03: zona MAJBURIY va composite FK orqali — A bozoridagi rasta B
        # bozorining zonasiga havola qila OLMAYDI (T-02-30). Bu RLS emas,
        # SXEMA darajasidagi kafolat.
        sa.ForeignKeyConstraint(
            ["market_id", "zone_id"],
            ["zones.market_id", "zones.id"],
            name="fk_stalls_market_id_zone_id_zones",
        ),
        # D-01: raqam BOZOR bo'yicha yagona (zona bo'yicha emas).
        sa.UniqueConstraint("market_id", "code", name="uq_stalls_market_id_code"),
        sa.UniqueConstraint("market_id", "id", name="uq_stalls_market_id_id"),
        sa.CheckConstraint(STALL_STATUS_CHECK, name="status_allowed"),
        sa.CheckConstraint("length(btrim(code)) > 0", name="code_not_blank"),
    )
    # Keyset kursori `(code_sort, id)` shu indeksdan foydalanadi; tenant
    # invarianti #5 bo'yicha `market_id` bilan BOSHLANADI (P9).
    op.create_index("ix_stalls_market_id_code_sort", "stalls", ["market_id", "code_sort"])

    # ------------------------------------------------------------------
    # 5. stall_code_registry — D-02 ning DB kafolati.
    #
    #    `UNIQUE(market_id, code)` YETARLI EMAS: rasta kodi tahrirlangach
    #    eski kod BO'SHAB QOLADI va boshqa rastaga berilishi mumkin bo'lardi.
    #    U holda hisobotdagi "12-rasta" yillar davomida ikki xil jismoniy
    #    joyni anglatardi va nizoda dalil sifatida ishlamasdi (T-02-32).
    #
    #    `id uuid` ustuni ATAYIN YO'Q — birlamchi kalit `(market_id, code)`
    #    ning O'ZI. Oqibati: audit triggeri bu jadvalga ULANMAYDI (fayl
    #    boshidagi izoh).
    # ------------------------------------------------------------------
    op.create_table(
        "stall_code_registry",
        _market_id(),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("stall_id", pg.UUID(as_uuid=True), nullable=False),
        # ATAYIN `created_at` deb atalmagan: u qatorning emas, KODNING bozorda
        # birinchi ko'rilgan paytini bildiradi.
        sa.Column(
            "first_seen",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("market_id", "code", name="pk_stall_code_registry"),
        sa.ForeignKeyConstraint(
            ["market_id"], ["markets.id"], name="fk_stall_code_registry_market_id_markets"
        ),
        sa.ForeignKeyConstraint(
            ["market_id", "stall_id"],
            ["stalls.market_id", "stalls.id"],
            name="fk_stall_code_registry_market_id_stall_id_stalls",
        ),
    )

    # ------------------------------------------------------------------
    # 6. RLS. TARTIB MAJBURIY: ENABLE + FORCE + GRANT -> policy.
    #    `alembic-utils` `ENABLE`/`FORCE` ni BILMAYDI (Pitfall 10) — ularsiz
    #    policy HECH QANDAY ta'sir ko'rsatmaydi va jadval hamma uchun ochiq
    #    bo'ladi (T-02-29).
    # ------------------------------------------------------------------
    for table in MARKET_DOMAIN_TENANT_TABLES:
        enable_tenant_rls(table)
        create_entity(tenant_policy(table))
        create_entity(owner_bootstrap_policy(table))

    # ------------------------------------------------------------------
    # 7. Audit triggerlari (D-10). Fayl boshidagi izoh — nega faqat ikkitasi.
    # ------------------------------------------------------------------
    for table in AUDITED_TABLES:
        attach_audit_trigger(table)

    # ------------------------------------------------------------------
    # 8. D-02: kod reyestri triggeri.
    #
    #    ⚠ `AFTER`, `BEFORE` EMAS — O'LCHANGAN ZARURAT (02-04). `BEFORE
    #    INSERT` paytida `stalls` qatori HALI YOZILMAGAN, ya'ni reyestrga
    #    `stall_id = NEW.id` bilan yozish `fk_stall_code_registry_market_id_
    #    stall_id_stalls` ni darhol buzardi. Kafolat zaiflashmaydi: `AFTER`
    #    dagi `RAISE` ham butun operatsiyani bekor qiladi.
    #
    #    `UPDATE OF code` — kod TAHRIRLANGANDA ham tekshiriladi, aks holda
    #    reyestr faqat yaratish yo'lini qamrardi va D-02 chetlab o'tilardi.
    # ------------------------------------------------------------------
    create_entity(STALL_CODE_CLAIM)
    op.execute(
        f"CREATE TRIGGER {STALL_CODE_CLAIM_TRIGGER} "
        "AFTER INSERT OR UPDATE OF code ON stalls "
        "FOR EACH ROW EXECUTE FUNCTION stall_code_claim()"
    )

    # ------------------------------------------------------------------
    # 9. Bozor yozish funksiyalari (Pattern 6).
    #
    #    `sbozor_app` ga `markets` da FAQAT `SELECT` grant'i bor (0001) va
    #    policy predikati `id = app.market_id` — ya'ni yangi bozor yaratishga
    #    IKKI mustaqil to'siq bor. Yagona yo'l — shu `SECURITY DEFINER`
    #    funksiyalar (T-02-35).
    #
    #    `market_delete_draft` va `market_is_open` BU YERDA EMAS, `0010` da:
    #    ikkalasi ham hali mavjud bo'lmagan `market_calendar_exceptions` ga
    #    tegadi (sabab `MARKET_CORE_FUNCTIONS` docstringida).
    # ------------------------------------------------------------------
    for function in MARKET_CORE_FUNCTIONS:
        create_entity(function)

    for signature in MARKET_CORE_GRANT_SIGNATURES:
        # PUBLIC dan AVVAL olib tashlanadi: Postgres yangi funksiyaga
        # `EXECUTE TO PUBLIC` ni STANDART beradi, ya'ni REVOKE'siz bozor
        # yaratish yo'li bazadagi HAR QANDAY rol uchun ochiq bo'lib qolardi.
        op.execute(f"REVOKE ALL ON FUNCTION {signature} FROM PUBLIC")
        op.execute(f"GRANT EXECUTE ON FUNCTION {signature} TO {APP_ROLE}")


def downgrade() -> None:
    """Downgrade schema."""
    for function in reversed(MARKET_CORE_FUNCTIONS):
        drop_entity(function)

    # Trigger AVVAL, funksiya KEYIN: bog'langan trigger qolgan holda
    # `DROP FUNCTION` bog'liqlik xatosi bilan yiqiladi (0002 dagi naqsh).
    op.execute(f"DROP TRIGGER IF EXISTS {STALL_CODE_CLAIM_TRIGGER} ON stalls")
    drop_entity(STALL_CODE_CLAIM)

    for table in reversed(AUDITED_TABLES):
        detach_audit_trigger(table)

    for table in reversed(MARKET_DOMAIN_TENANT_TABLES):
        drop_entity(owner_bootstrap_policy(table))
        drop_entity(tenant_policy(table))

    op.drop_table("stall_code_registry")
    op.drop_index("ix_stalls_market_id_code_sort", table_name="stalls")
    op.drop_table("stalls")
    op.drop_table("stall_categories")
    op.drop_table("zones")
    op.drop_table("market_profile")
