"""market_notification_settings.id uuid — audit tarixi ochiladi

Revision ID: 0025
Revises: 0024
Create Date: 2026-08-16

07 `deferred-items.md` №4 NING YOPILISHI (D-24). Jadvalning birlamchi
kaliti `market_id` dan `id` ga ko'chadi va jadval `AUDITED_TABLES` ga
qo'shiladi — ya'ni «direktor chatini kim, qachon almashtirdi?» savoli
`audit_log` dan javob oladi.

=============================================================================
⛔⛔ ENG MUHIM BAND — `UNIQUE (market_id)` SAQLANADI (Pitfall 16).

PK `id` ga ko'chgach 1:1 kafolati AVTOMATIK YO'QOLADI. Uni QAYTARMASLIK
mahsulotning butun bir yo'lini sindirardi:

`services/core-api/app/repositories/binding_repo.py::_BIND_DIRECTOR_CHAT`
quyidagini yozadi ->

    INSERT INTO market_notification_settings (market_id, director_chat_id)
         VALUES (:market_id, :chat_id)
    ON CONFLICT (market_id) DO UPDATE ...

`ON CONFLICT (<ustunlar>)` INFERENCE shakli va u AYNAN o'sha ustun(lar)
ustidagi UNIQUE (yoki exclusion) cheklovni QIDIRADI. Cheklov bo'lmasa
Postgres ->

    there is no unique or exclusion constraint matching the
    ON CONFLICT specification

va DIREKTOR BOTGA UMUMAN ULANA OLMAYDI: `resolve_director()` ->
`bind_director()` yiqiladi, `director_chat_id` HECH QACHON yozilmaydi va
dayjest (kunlik tushum, bandlik, TOP-10 qarzdor) HECH KIMGA bormaydi.

⚠ NOSOZLIK MIGRATSIYADA KO'RINMASDI — u faqat direktor botga `contact`
ulashgan LAHZADA chiqardi, ya'ni ishga tushirish kunida.

⛔ SHUNING UCHUN CHEKLOV SABOTAJ BILAN O'LCHANDI (`08-02` / T3): u
vaqtincha olib tashlandi va `test_bind_director_is_idempotent_across_two_
calls` AYNAN yuqoridagi xato bilan QIZARDI.
=============================================================================

⛔ NEGA `id` UMUMAN QO'SHILADI — VA SABAB REPO YOZGANIDAN BOSHQA.

Repo'ning uch joyi «`fn_audit_row()` `id` ustunisiz jadvalda har DML da
YIQILADI» degan edi. Da'vo HECH QACHON o'lchanmagan edi va u YOLG'ON:

    O'lchov (2026-08-16, PostgreSQL 18.4): trigger qo'lda ulanib bitta
    `UPDATE` bajarildi -> DML O'TDI, `audit_log` ga 1 qator yozildi,
    `row_id = NULL`, `action = 'update'`.

MEXANIKA: `jsonb ->> '<yo'q kalit>'` `NULL` beradi, `NULL::uuid` istisno
ko'tarmaydi, `audit_log.row_id` esa `nullable` (`0002_audit.py`).

HAQIQIY NUQSON YOMONROQ EDI: `row_id IS NULL` bo'lgan audit qatori QAYSI
QATORGA tegishli ekanini AYTMAYDI. Yiqilish DARHOL ko'rinardi; `NULL` esa
jimgina yillar davomida yozilib turardi. `id uuid` aynan shuni tuzatadi —
audit funksiyasini o'zgartirish EMAS (D-24 ning ochiq talabi).

=============================================================================
⚠ JADVAL YARATILMAYDI — MAVJUD JADVAL O'ZGARADI. Shuning uchun bu
migratsiya `enable_tenant_rls` / `tenant_policy` / `owner_bootstrap_policy`
ni CHAQIRMAYDI: uchalasi ham `0023` da allaqachon o'rnatilgan va PK
ko'chishi ularga TEGMAYDI (policy predikati `market_id` ustida, PK ustida
emas).

⚠ `ALL_TENANT_TABLES` GA HAM HECH NIMA QO'SHILMAYDI — nom u yerda
7-fazadan beri bor (`NOTIFICATION_TENANT_TABLES` ning beshinchi a'zosi).

⛔ YANGI `SECURITY DEFINER` FUNKSIYA QO'SHILMAYDI (T-06-22 / G7-7) va bu
migratsiya `market_delete_draft()` GA HAM TEGMAYDI: jadval kaskadda
allaqachon bor (`0023` qo'shgan) va uning NOMI o'zgarmadi.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

from migrations.entities import SETTINGS_AUDITED_TABLES
from migrations.helpers import attach_audit_trigger, detach_audit_trigger

# revision identifiers, used by Alembic.
revision: str = "0025"
down_revision: str | Sequence[str] | None = "0024"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE = "market_notification_settings"

PK_NAME = "pk_market_notification_settings"
"""Birlamchi kalitning nomi — `0023` dan beri O'ZGARMAYDI.

⚠ FAQAT USTUNI ko'chadi (`market_id` -> `id`), NOMI emas. Nom
`models/base.py::NAMING_CONVENTION` ning `pk_%(table_name)s` qoidasidan
keladi, ya'ni uni o'zgartirish `test_autogenerate_is_empty` ni darhol
qizartirardi.
"""

MARKET_UNIQUE_NAME = "uq_market_notification_settings_market_id"
"""⛔⛔ `ON CONFLICT (market_id)` NING YAGONA TAYANCHI — fayl boshidagi band.

Nom `NAMING_CONVENTION` ning `uq_%(table_name)s_%(column_0_N_name)s`
qoidasidan keladi va u MODELDA ham AYNAN shu nom bilan e'lon qilingan
(`models/notification.py::MarketNotificationSettings.__table_args__`) —
ikkisi ajralib ketsa `test_autogenerate_is_empty` qizaradi.
"""


def upgrade() -> None:
    """Upgrade schema."""
    # ------------------------------------------------------------------
    # 1. `id uuid` ustuni — MAVJUD QATORLAR HAM TO'LDIRILADI.
    #
    #    ⚠ ALOHIDA `UPDATE` KERAK EMAS va bu Postgres ning o'lchangan
    #    xulqi: `ADD COLUMN ... DEFAULT <volatile>` jadvalni QAYTA YOZADI
    #    va standartni HAR QATOR uchun ALOHIDA hisoblaydi, ya'ni har bir
    #    mavjud qator O'Z `uuidv7()` qiymatini oladi. `uuidv7()` VOLATILE,
    #    ya'ni PG 11 ning "fast default" optimizatsiyasi (bitta qiymatni
    #    hamma qatorga berish) bu yerda QO'LLANMAYDI.
    #
    #    ⛔ AGAR U IMMUTABLE BO'LGANDA hamma qator AYNI qiymatni olardi va
    #    keyingi `PRIMARY KEY` qadami `could not create unique index`
    #    bilan yiqilardi — ya'ni nosozlik shu yerdayoq ko'rinardi,
    #    jimgina o'tib ketmasdi.
    #
    #    ⚠ `disable_force_for_backfill()` CHAQIRILMAYDI: bu DDL, DML emas.
    #    RLS policy'lari `UPDATE`/`INSERT` ga qo'llanadi, `ALTER TABLE`
    #    ning qayta yozishiga EMAS (Pitfall 4 aynan `UPDATE ... SET` haqda
    #    edi va bu yerda unday bayonot yo'q).
    # ------------------------------------------------------------------
    op.add_column(
        TABLE,
        sa.Column(
            "id",
            pg.UUID(as_uuid=True),
            server_default=sa.text("uuidv7()"),
            nullable=False,
        ),
    )

    # ------------------------------------------------------------------
    # 2. PK `market_id` -> `id`.
    #
    #    ⚠ TARTIB MAJBURIY: avval ESKI PK tashlanadi, keyin YANGISI
    #    qo'yiladi. Jadvalda bir vaqtda ikkita birlamchi kalit bo'la
    #    olmaydi (`multiple primary keys for table ... are not allowed`).
    #
    #    ⚠ `fk_market_notification_settings_market_id_markets` BUZILMAYDI:
    #    u SHU jadvaldan `markets` GA yo'nalgan, ya'ni u `markets` ning
    #    kalitiga tayanadi — bu jadvalning O'Z PK siga emas.
    # ------------------------------------------------------------------
    op.drop_constraint(PK_NAME, TABLE, type_="primary")
    op.create_primary_key(PK_NAME, TABLE, ["id"])

    # ------------------------------------------------------------------
    # 3. ⛔⛔ 1:1 KAFOLATI QAYTARILADI — fayl boshidagi ENG MUHIM band.
    #
    #    Bu satr olib tashlansa migratsiya XATOSIZ o'tadi, testlarning
    #    ko'pchiligi YASHIL qoladi va nosozlik faqat direktor botga
    #    `contact` ulashgan lahzada chiqadi. Sabotaj bilan o'lchangan.
    # ------------------------------------------------------------------
    op.create_unique_constraint(MARKET_UNIQUE_NAME, TABLE, ["market_id"])

    # ------------------------------------------------------------------
    # 4. Audit (D-24). Endi `row_id` HAQIQIY qiymat oladi.
    #
    #    ⚠ NOM `schema_contract.AUDITED_TABLES` GA SHU MIGRATSIYA BILAN
    #      BIR COMMITDA qo'shildi (`06-04` OP-4 naqshi), ya'ni
    #      `PENDING_AUDIT_TRIGGERS` BO'SH qoladi va
    #      `test_audited_tables_have_trigger` UZLUKSIZ yashil turadi.
    #
    #    ⚠ TARTIB: trigger `id` ustuni MAVJUD bo'lgandan KEYIN ulanadi.
    #      Teskarisida u ishlar edi, lekin `row_id IS NULL` yozardi —
    #      ya'ni aynan tuzatilayotgan nuqson qaytib kelardi.
    # ------------------------------------------------------------------
    for table in SETTINGS_AUDITED_TABLES:
        attach_audit_trigger(table)


def downgrade() -> None:
    """Downgrade schema."""
    # TARTIB TESKARI: trigger AVVAL yechiladi — `id` ustuni tashlangandan
    # keyin u `row_id IS NULL` yozadigan holatga qaytardi.
    for table in reversed(SETTINGS_AUDITED_TABLES):
        detach_audit_trigger(table)

    op.drop_constraint(MARKET_UNIQUE_NAME, TABLE, type_="unique")

    # PK `id` -> `market_id`. `market_id` da `NOT NULL` allaqachon bor
    # (`0023`), ya'ni birlamchi kalit qo'yish uchun qo'shimcha qadam
    # kerak emas.
    op.drop_constraint(PK_NAME, TABLE, type_="primary")
    op.create_primary_key(PK_NAME, TABLE, ["market_id"])

    op.drop_column(TABLE, "id")
