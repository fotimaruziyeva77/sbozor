"""vendors: sotuvchilar va QOPLANMAYDIGAN biriktirish davrlari + RLS + audit

Revision ID: 0009
Revises: 0008
Create Date: 2026-07-31

=============================================================================
NEGA BU YERDA `daterange` TO'G'RI, `0008` DA ESA XATO BO'LARDI.

`0008_temporal.py` ikkala tarix jadvalini VORIS modelida qurdi va uning
docstringi `daterange` ni ATAYIN rad etadi. Bu yerda esa qaror TESKARI, va
farq uch nuqtaga tayanadi — uchalasi ham `tariffs` da mavjud EMAS edi:

  (a) DAVR HAQIQATAN YOPILADI. Sotuvchi rastadan ketadi va o'sha kun
      ma'lum. Tarifda esa "narx tugadi" degan hodisa yo'q — keyingi narx
      boshlanadi, xolos, ya'ni yuqori chegara har doim HOSILA.
  (b) BO'SHLIQ — MA'NOLI HOLAT (D-11). Ikki davr orasidagi kunlarda hech
      kim biriktirilmagan va bu XATO EMAS: aynan shu "sotuvchisiz band
      rasta" anomaliyasini 6-faza fosh qiladi. Tarifda bo'shliq esa
      hisobning to'xtashini anglatardi.
  (c) O'TMISHDAGI DAVRNI YOPISH TAQIQLANMAGAN. D-07 tarifning o'tgan
      qatorini qulflaydi, biriktirishda esa bunday qoida YO'Q — sotuvchi
      kecha ketganini bugun qayd etish normal amal. `daterange` aynan shu
      `UPDATE` ni talab qiladi va u yerda taqiqlangan edi.

Ya'ni ikkala model ham ataylab va ular bir-birining o'rnini bosmaydi.
=============================================================================

⚠ ALEMBIC `ExcludeConstraint` NI KO'RMAYDI — IKKI TOMONLAMA (empirik,
Alembic 1.18.5 + SQLAlchemy 2.0.51, `compare_metadata()`):

  * model va DB bir xil bo'lganda diff **0 element** (soxta drift yo'q);
  * konstrayt modeldan OLIB TASHLANGANDA ham diff **0 element** — ya'ni
    YO'QOLISH SEZILMAYDI.

Shuning uchun konstrayt bu yerda LITERAL yoziladi (autogenerate uni hech
qachon o'zi qo'shmaydi) va uning mavjudligi
`tests/tenancy/test_market_domain_meta.py::
test_stall_assignments_has_exclusion_constraint` bilan alohida qulflanadi.
O'sha test — bu kafolatning YAGONA darvozasi.

⚠ XATO XABARI HAQIDA (Pitfall 4, empirik — HAM app-rol, HAM ega uchun):
RLS yoqilgan jadvalda Postgres `UNIQUE`/`EXCLUDE` buzilishining `DETAIL`
qatorini BUTUNLAY o'chiradi (ko'rinmaydigan qator haqida ma'lumot sizib
chiqmasin). Ya'ni foydalanuvchiga ko'rinadigan xabar DB xatosidan
OLINMAYDI. `exc.orig.constraint_name` ham asyncpg o'ramida `None` bo'lib
qaytadi (o'lchandi), demak yagona ishonchli diskriminator — `sqlstate`::

    23P01 (exclusion_violation) -> "assignment_period_overlaps"  -> 409
    23505 (unique_violation)    -> "vendor_phone_taken"          -> 409
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

from migrations.entities import VENDOR_TENANT_TABLES
from migrations.entities.policies import owner_bootstrap_policy, tenant_policy
from migrations.helpers import (
    attach_audit_trigger,
    create_entity,
    detach_audit_trigger,
    drop_entity,
    enable_tenant_rls,
    require_extension,
)

# revision identifiers, used by Alembic.
revision: str = "0009"
down_revision: str | Sequence[str] | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ASSIGNMENT_VENDOR_INDEX = "ix_stall_assignments_market_id_vendor_id"


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
    # 0. KENGAYTMA DARVOZASI — MIGRATSIYANING BIRINCHI SATRI.
    #
    #    `EXCLUDE USING gist (market_id WITH =, ...)` uchun `uuid` tipining
    #    GiST tenglik operator klassi kerak va u AYNAN `btree_gist` dan
    #    keladi. Darvozasiz `op.create_table()` o'rtada "data type uuid has
    #    no default operator class for access method gist" bilan yiqilardi
    #    va xabar NIMA yetishmayotganini aytmasdi — dasturchi konstraytni
    #    "noto'g'ri yozilgan" deb o'ylab uni olib tashlashi mumkin edi
    #    (aynan yo'qotilishi eng qimmat konstrayt).
    #
    #    ⚠ `op.execute("CREATE EXTENSION ...")` BU YERDA YOZILMAYDI:
    #    `sbozor_owner` — `NOCREATEDB` va bazaning egasi emas, ya'ni unga
    #    `permission denied to create extension` qaytadi (empirik).
    #    Kengaytma `ops/db/init/00-extensions.sql` da SUPERUSER bilan
    #    o'rnatiladi va `require_extension()` ning xato matni o'sha faylni
    #    nomma-nom ko'rsatadi.
    # ------------------------------------------------------------------
    require_extension("btree_gist")

    # ------------------------------------------------------------------
    # 1. vendors — SHAXSIY MA'LUMOT (F.I.Sh. + telefon).
    #
    #    D-12: telefon MAJBURIY va BOZOR ICHIDA unique. Bozorlararo unique
    #    EMAS va bu ATAYIN, "unutilgan" emas: bir odam ikki bozorda savdo
    #    qilishi mumkin va MVP uni ikki alohida sotuvchi qatori sifatida
    #    ko'radi. Global `UNIQUE(phone_e164)` qo'shish bugun "tozaroq"
    #    ko'rinardi, lekin u ikkinchi bozorda ro'yxatdan o'tishni BLOKLAB
    #    qo'yardi — ya'ni mahsulot cheklovini sxemaga muzlatib qo'yish.
    #    Yagona shaxs sifatida birlashtirish — v2 (T-02-44: accept).
    #
    #    Telefon FORMATI DB'da tekshirilmaydi: normalizatsiya chegarada
    #    (`sbozor_core.phone.normalize_phone`) — `users.phone_e164` bilan
    #    AYNAN bir xil qaror. Ikki joyda tekshirish formatni ikki marta
    #    ta'riflardi va ular ajralib ketardi.
    # ------------------------------------------------------------------
    op.create_table(
        "vendors",
        _market_id(),
        _uuid_pk(),
        sa.Column("full_name", sa.Text(), nullable=False),
        sa.Column("phone_e164", sa.Text(), nullable=False),
        _created_at(),
        _updated_at(),
        sa.PrimaryKeyConstraint("id", name="pk_vendors"),
        sa.ForeignKeyConstraint(["market_id"], ["markets.id"], name="fk_vendors_market_id_markets"),
        sa.UniqueConstraint("market_id", "phone_e164", name="uq_vendors_market_id_phone_e164"),
        sa.UniqueConstraint("market_id", "id", name="uq_vendors_market_id_id"),
        # Qarzdorlik reestrida ismsiz qator "kimdan undirish kerak?"
        # savoliga javob bermaydi — mahsulotning asosiy hujjati foydasiz
        # bo'lib qolardi.
        sa.CheckConstraint("length(btrim(full_name)) > 0", name="full_name_not_blank"),
    )

    # ------------------------------------------------------------------
    # 2. stall_assignments — 6-fazadagi QARZ EGALIGINING yagona manbai.
    #
    #    PUL USTUNI YO'Q va BO'LMAYDI (D-10): qarz `daily_charges` da
    #    tug'iladi va rasta almashinganda ESKI sotuvchida qoladi. Aynan shu
    #    sababdan jadval `FINANCIAL_TABLES` reyestridan CHIQARILGAN (02-01):
    #    aks holda `test_financial_tables_have_guards` undan
    #    `CHECK (amount_soum > 0)` talab qilardi va yagona "tuzatish" yo'li
    #    soxta pul ustuni qo'shish bo'lardi.
    #
    #    `updated_at` USTUNI HAM YO'Q: davr yopilishi `period` ning yuqori
    #    chegarasi bilan ifodalanadi. `updated_at` "bu qatorni tahrirlash
    #    mumkin" degan yolg'on va'da berardi va davr semantikasi bilan
    #    raqobatlashardi.
    # ------------------------------------------------------------------
    op.create_table(
        "stall_assignments",
        _market_id(),
        _uuid_pk(),
        sa.Column("stall_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("vendor_id", pg.UUID(as_uuid=True), nullable=False),
        # HAR DOIM `sbozor_core.periods.assignment_period()` bilan quriladi
        # (`[)` chegarasi). Xom `daterange(...)` yozilsa konvensiya ikkinchi
        # manbaga ega bo'lardi va almashinuv KUNIDAGI patta ikki sotuvchiga
        # yozilardi (D-10 ning aynan buziladigan joyi).
        sa.Column("period", pg.DATERANGE(), nullable=False),
        _created_at(),
        sa.PrimaryKeyConstraint("id", name="pk_stall_assignments"),
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
        sa.ForeignKeyConstraint(
            ["market_id", "vendor_id"],
            ["vendors.market_id", "vendors.id"],
            name="fk_stall_assignments_market_id_vendor_id_vendors",
        ),
        sa.UniqueConstraint("market_id", "id", name="uq_stall_assignments_market_id_id"),
        # ⚠ ALEMBIC BU KONSTRAYTNI AVTOGENERATSIYA QILMAYDI VA UNING
        #   YO'QOLGANINI HAM SEZMAYDI (fayl boshidagi o'lchov). Shuning uchun
        #   u shu yerda LITERAL turadi va meta-test bilan qulflanadi.
        #
        #   D-09: bir vaqtda 1 rasta = 1 sotuvchi. Ilova qatlamidagi "avval
        #   tekshir, keyin yoz" naqshi IKKI PARALLEL so'rovda ikkalasini ham
        #   o'tkazib yuborardi (ikkalasi ham bo'sh holatni ko'radi) —
        #   `EXCLUDE` esa atomik va xom SQL yo'lini ham qamraydi.
        #   Buzilganda SQLSTATE `23P01`.
        #
        #   Ustunlar TARTIBI ham ahamiyatli: `market_id` BIRINCHI, ya'ni
        #   konstrayt ostidagi GiST indeksi tenant invarianti #5 dan
        #   (`test_tenant_indexes_lead_with_market_id`) o'tadi.
        pg.ExcludeConstraint(
            ("market_id", "="),
            ("stall_id", "="),
            ("period", "&&"),
            name="ex_stall_assignments_no_overlap",
            using="gist",
        ),
        # Quyi chegarasiz davr "abadiy o'tmishdan beri biriktirilgan" degani
        # bo'lardi va har qanday tarixiy hisobga kirib qolardi. Yuqori
        # chegara esa `NULL` bo'lishi MUMKIN — bu "sotuvchi hali ishlayapti".
        sa.CheckConstraint("lower(period) IS NOT NULL", name="lower_bound_required"),
    )
    # "Shu sotuvchining rastalari" — qarzdorlik reestri va sotuvchi
    # kartochkasining asosiy so'rovi. EXCLUDE indeksi (`market_id`,
    # `stall_id`, `period`) bu savolga javob BERMAYDI — u `vendor_id` ni
    # umuman qamramaydi.
    op.create_index(ASSIGNMENT_VENDOR_INDEX, "stall_assignments", ["market_id", "vendor_id"])

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

    # ------------------------------------------------------------------
    # 4. Audit (D-10, T-02-39). Ikkala jadval ham MAJBURIY:
    #
    #    * `vendors` — shaxsiy ma'lumot; ism/telefon o'zgarishi qarzdorlik
    #      reestrining kimga tegishli ekanini o'zgartiradi.
    #    * `stall_assignments` — `period` ning tahriri qarz EGALIGINI bir
    #      sotuvchidan boshqasiga ko'chiradi. Trigger `old->new` juftligini
    #      yozadi (`changed_keys={period}`), ya'ni davrni orqaga surib
    #      qarzni o'tkazish urinishi izsiz qolmaydi.
    #
    #    Nomlar `tests/tenancy/test_meta.py::PENDING_AUDIT_TRIGGERS` dan
    #    shu vazifada O'CHIRILADI — ro'yxat ikki tomonlama va o'chirilmasa
    #    `test_audited_tables_have_trigger` qizarib sababni o'zi aytadi.
    # ------------------------------------------------------------------
    for table in VENDOR_TENANT_TABLES:
        attach_audit_trigger(table)


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
