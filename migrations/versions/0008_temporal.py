"""temporal: toifa davrlari va tariflar + RLS + audit + o'zgarmaslik triggerlari

Revision ID: 0008
Revises: 0007
Create Date: 2026-07-31

=============================================================================
IKKI JADVAL, BITTA MEXANIZM — VORIS (successor) MODELI.

Yangi qiymat = YANGI QATOR. Eski qator HECH QACHON `UPDATE` qilinmaydi.
Yuqori chegara (`valid_to`) SAQLANMAYDI — u keyingi qatordan hosila va
so'rovda hisoblanadi::

    SELECT valid_from,
           LEAD(valid_from) OVER (PARTITION BY market_id, category_id
                                  ORDER BY valid_from) AS valid_to,
           amount_soum
    FROM tariffs WHERE market_id = :m AND category_id = :c
    ORDER BY valid_from DESC

"D sanadagi amaldagi qiymat" esa `WHERE valid_from <= :d ORDER BY valid_from
DESC LIMIT 1` — UNIQUE konstraytining O'ZI bu so'rov uchun optimal indeks
(o'lchangan: `Index Scan Backward using uq_tariffs_market_id_category_id_
valid_from`), qo'shimcha indeks KERAK EMAS.

NEGA `daterange` + `EXCLUDE` EMAS (bu fazadagi eng muhim model qarori):
D-06 "yangi narx = yangi qator, ESKISI O'ZGARMAYDI" va D-07 "sanasi o'tgan
tarif QULFLANADI" bir-birini quvvatlaydi, `daterange` esa ikkalasini ham
buzadi — yangi narx kiritish eski qatorning yuqori chegarasini YOPISHNI,
ya'ni uni `UPDATE` qilishni talab qilardi va o'sha `UPDATE` aynan D-07
taqiqlagan amal bo'lib chiqardi (Pitfall 9). `stall_assignments` da
`daterange` TO'G'RI va u `0009` da — farq ataylab.

`updated_at` USTUNI IKKALA JADVALDA HAM YO'Q: u "bu qatorni tahrirlash
mumkin" degan yolg'on va'da berardi. Qatorlar faqat QO'SHILADI.
=============================================================================

⚠ `financial_guards("tariffs", ...)` ATAYIN CHAQIRILMAYDI — pastdagi 2-blok
izohiga qarang. Bu "helper ishlatilmagan" emas, ANIQ qaror.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

from migrations.entities import TEMPORAL_TENANT_TABLES
from migrations.entities.policies import owner_bootstrap_policy, tenant_policy
from migrations.entities.triggers import (
    CATEGORY_PERIOD_PAST_IMMUTABLE,
    TARIFF_PAST_IMMUTABLE,
)
from migrations.helpers import (
    BUSINESS_DATE_EXPR,
    attach_audit_trigger,
    attach_immutability_trigger,
    create_entity,
    detach_audit_trigger,
    detach_immutability_trigger,
    drop_entity,
    enable_tenant_rls,
)

# revision identifiers, used by Alembic.
revision: str = "0008"
down_revision: str | Sequence[str] | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

IMMUTABILITY_TRIGGERS: tuple[tuple[str, str, str], ...] = (
    (
        "stall_category_periods",
        "category_period_past_immutable",
        "trg_category_period_past_immutable",
    ),
    ("tariffs", "tariff_past_immutable", "trg_tariff_past_immutable"),
)
"""`(jadval, trigger funksiyasi, trigger nomi)` — `upgrade()` va `downgrade()` uchun."""

IMMUTABILITY_FUNCTIONS = (CATEGORY_PERIOD_PAST_IMMUTABLE, TARIFF_PAST_IMMUTABLE)
"""`IMMUTABILITY_TRIGGERS` bilan bir xil TARTIBDA."""


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


def upgrade() -> None:
    """Upgrade schema."""
    # ------------------------------------------------------------------
    # 1. stall_category_periods — rastaning TOIFA tarixi (D-04).
    #
    #    `stalls.category_id` ustuni ATAYIN YO'Q: toifani o'zgartirish
    #    O'TMISHDAGI hisobni ham qayta yozardi. Joriy toifa shu jadvaldan
    #    `valid_from <= :d` bo'yicha OXIRGI qator sifatida olinadi.
    # ------------------------------------------------------------------
    op.create_table(
        "stall_category_periods",
        _market_id(),
        _uuid_pk(),
        sa.Column("stall_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("category_id", pg.UUID(as_uuid=True), nullable=False),
        # A3: BIRINCHI qatorning `valid_from` i `market_profile.operating_since`
        # dan olinadi — import kuni EMAS, aks holda 6-faza undan oldingi har bir
        # kunni "toifasiz" deb topib butun tarixni anomaliyaga aylantirardi.
        sa.Column("valid_from", sa.Date(), nullable=False),
        _created_at(),
        sa.PrimaryKeyConstraint("id", name="pk_stall_category_periods"),
        sa.ForeignKeyConstraint(
            ["market_id"], ["markets.id"], name="fk_stall_category_periods_market_id_markets"
        ),
        sa.ForeignKeyConstraint(
            ["market_id", "stall_id"],
            ["stalls.market_id", "stalls.id"],
            name="fk_stall_category_periods_market_id_stall_id_stalls",
        ),
        # ⚠ NOMDA `market_id` SEGMENTI YO'Q va bu ATAYIN: to'liq konvensiya
        # nomi (`fk_stall_category_periods_market_id_category_id_stall_
        # categories`) 64 bayt bo'lib Postgres'ning 63 baytlik chegarasidan
        # oshadi va JIMGINA kesiladi — kesilgan nom modeldagi nom bilan mos
        # kelmay autogenerate uni har safar "o'zgargan" deb ko'rsatardi.
        # Konstraytning O'ZI baribir composite (02-04 deviatsiya #6).
        sa.ForeignKeyConstraint(
            ["market_id", "category_id"],
            ["stall_categories.market_id", "stall_categories.id"],
            name="fk_stall_category_periods_category_id_stall_categories",
        ),
        # Bir rastaga bir kunda IKKITA toifa berib bo'lmaydi. Bu ayni paytda
        # "D sanadagi toifa" so'rovining indeksi ham.
        sa.UniqueConstraint(
            "market_id",
            "stall_id",
            "valid_from",
            name="uq_stall_category_periods_market_id_stall_id_valid_from",
        ),
        sa.UniqueConstraint("market_id", "id", name="uq_stall_category_periods_market_id_id"),
    )

    # ------------------------------------------------------------------
    # 2. tariffs — toifa NARXI tarixi (D-05/D-06/D-07).
    #
    #    ⚠ `financial_guards("tariffs", ...)` BU YERDA CHAQIRILMAYDI.
    #
    #    Yordamchi `UNIQUE(market_id, category_id, business_date)` beradi, ya'ni
    #    idempotentlik kalitini QATOR YOZILGAN KUNGA bog'laydi. Tarifda esa
    #    hukmron sana `valid_from` (narx QACHONDAN amal qiladi), `business_date`
    #    emas — va bir kunda ikkita KELAJAK tarifini kiritish ("1-sentabrdan"
    #    va "1-oktabrdan") mutlaqo normal amal. Helper bilan ikkinchisi
    #    `unique_violation` bilan rad etilardi.
    #
    #    Shuning uchun uchala qo'riqchi ham QO'LDA yozilgan va ular
    #    `test_financial_tables_have_guards` darvozasidan aynan shu holida
    #    o'tadi:
    #      * `business_date` STORED generated ustuni  (pastda)
    #      * `CHECK (amount_soum > 0)`                (pastda)
    #      * `market_id` bilan boshlanadigan UNIQUE   (pastda)
    #    Jadval `FINANCIAL_TABLES` da QOLADI — unda haqiqiy pul ustuni bor.
    # ------------------------------------------------------------------
    op.create_table(
        "tariffs",
        _market_id(),
        _uuid_pk(),
        sa.Column("category_id", pg.UUID(as_uuid=True), nullable=False),
        # Pul — `bigint` so'm; `float` TAQIQLANGAN (yaxlitlanish drifti aynan
        # mahsulot bartaraf etadigan nizoni tug'diradi).
        sa.Column("amount_soum", sa.BigInteger(), nullable=False),
        # BIZNES sanasi — narx QACHONDAN amal qiladi.
        sa.Column("valid_from", sa.Date(), nullable=False),
        _created_at(),
        # Qator QAYSI BIZNES-KUNDA kiritilgani (auditga). `valid_from` bilan
        # aralashtirilmaydi — bu ikki xil savol. Ifoda `migrations.helpers`
        # dan IMPORT qilinadi: uchinchi nusxa yozilsa mintaqa arifmetikasi
        # ajralib ketardi. IKKI ARGUMENTLI `AT TIME ZONE` shakli MAJBURIY —
        # u IMMUTABLE, bitta argumentlisi STABLE va generated column'da
        # umuman ruxsat etilmaydi.
        sa.Column(
            "business_date",
            sa.Date(),
            sa.Computed(BUSINESS_DATE_EXPR, persisted=True),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_tariffs"),
        sa.ForeignKeyConstraint(["market_id"], ["markets.id"], name="fk_tariffs_market_id_markets"),
        sa.ForeignKeyConstraint(
            ["market_id", "category_id"],
            ["stall_categories.market_id", "stall_categories.id"],
            name="fk_tariffs_market_id_category_id_stall_categories",
        ),
        # D-06: bir toifaga bir SANADA bitta narx. Takroriy kiritish 409
        # bo'ladi, eski qator esa hech qachon o'zgarmaydi.
        sa.UniqueConstraint(
            "market_id",
            "category_id",
            "valid_from",
            name="uq_tariffs_market_id_category_id_valid_from",
        ),
        sa.UniqueConstraint("market_id", "id", name="uq_tariffs_market_id_id"),
        # Nol yoki manfiy narx "bepul rasta" ni ifodalamaydi — u hisobni
        # JIMGINA yo'qotadi.
        sa.CheckConstraint("amount_soum > 0", name="amount_soum_positive"),
    )

    # ------------------------------------------------------------------
    # 3. RLS. TARTIB MAJBURIY: ENABLE + FORCE + GRANT -> policy (Pitfall 10).
    # ------------------------------------------------------------------
    for table in TEMPORAL_TENANT_TABLES:
        enable_tenant_rls(table)
        create_entity(tenant_policy(table))
        create_entity(owner_bootstrap_policy(table))

    # ------------------------------------------------------------------
    # 4. Audit (D-10). Ikkala jadval ham `AUDITED_TABLES` da: toifa tarif
    #    orqali summani TO'G'RIDAN-TO'G'RI belgilaydi, tarif esa pul
    #    miqdorining o'zi.
    # ------------------------------------------------------------------
    for table in TEMPORAL_TENANT_TABLES:
        attach_audit_trigger(table)

    # ------------------------------------------------------------------
    # 5. O'ZGARMASLIK QO'RIQCHILARI (D-04 / D-07, T-02-31).
    #
    #    Retroaktiv narx o'zgartirish — o'tmishdagi qarzni yashirishning eng
    #    arzon yo'li va u aynan mahsulot fosh qiladigan nosozlik turi. Ilova
    #    qatlami 403 ni ustiga qo'yadi, lekin KAFOLAT shu triggerlarda: xom
    #    SQL yo'li ham, `sbozor_owner` ham qamraladi.
    #
    #    TRIGGER TARTIBI (Postgres qoidasi): bir xil vaqtdagi triggerlar
    #    ALIFBO tartibida, `BEFORE` esa `AFTER` dan OLDIN yuradi. Ya'ni rad
    #    etilgan `UPDATE` audit qatori HOSIL QILMAYDI — bu to'g'ri xulq:
    #    sodir bo'lmagan amal "o'zgardi" deb yozilmasin.
    #
    #    ⚠ Ikkala funksiya ham QORALAMA bozorni (`markets.is_active = false`)
    #    istisno qiladi — usiz `market_delete_draft()` (0010) HAR DOIM `23514`
    #    bilan yiqilardi. Sabab va nega bu xavfsizlikni zaiflashtirmasligi
    #    `migrations/entities/triggers.py::TARIFF_PAST_IMMUTABLE` da.
    # ------------------------------------------------------------------
    for function in IMMUTABILITY_FUNCTIONS:
        create_entity(function)

    for table, function_name, trigger_name in IMMUTABILITY_TRIGGERS:
        attach_immutability_trigger(table, function_name, trigger_name)


def downgrade() -> None:
    """Downgrade schema."""
    # Trigger AVVAL, funksiya KEYIN: bog'langan trigger qolgan holda
    # `DROP FUNCTION` bog'liqlik xatosi bilan yiqiladi (0002 dagi naqsh).
    for table, _function_name, trigger_name in reversed(IMMUTABILITY_TRIGGERS):
        detach_immutability_trigger(table, trigger_name)

    for function in reversed(IMMUTABILITY_FUNCTIONS):
        drop_entity(function)

    for table in reversed(TEMPORAL_TENANT_TABLES):
        detach_audit_trigger(table)

    for table in reversed(TEMPORAL_TENANT_TABLES):
        drop_entity(owner_bootstrap_policy(table))
        drop_entity(tenant_policy(table))

    op.drop_table("tariffs")
    op.drop_table("stall_category_periods")
