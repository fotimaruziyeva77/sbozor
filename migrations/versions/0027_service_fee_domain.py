"""Majburiy xizmat haqi (tarozi) — kunlik pattaning IKKINCHI komponenti

Revision ID: 0027
Revises: 0026
Create Date: 2026-08-24

=============================================================================
⛔⛔ NEGA BU MIGRATSIYA BOR.

Karmana amaliyotida rasta pattasidan TASHQARI majburiy TAROZI to'lovi bor
va u bugungacha modelda umuman yo'q edi. Ya'ni tizim har kuni, har rastada
haqiqiy summadan KAM hisob yozardi — «band rastadan patta to'liq
yig'ilyaptimi?» degan MAHSULOTNING ASOSIY SAVOLIGA maxraji noto'g'ri
javob berardi. Bu bezak emas, o'lchov xatosi.

-----------------------------------------------------------------------------
⛔ NEGA BOZOR DARAJASIDA, TARIF (TOIFA) ICHIDA EMAS.

`tariffs` toifaga bog'langan, chunki RASTA narxi toifaga qarab o'zgaradi
(go'sht rastasi ≠ sabzavot rastasi). Tarozi esa BOZORNING xizmati: bitta
tarozi, bitta narx va u kim savdo qilayotganiga qaramaydi.

Toifaga bog'lash narxni har toifada TAKRORLASHNI talab qilardi va o'sha
nusxalar bir kun ajralib ketardi — bitta bozorda ikki xil tarozi narxi
paydo bo'lardi va IKKALASI HAM «to'g'ri» bo'lardi. Bu loyihada takroran
topilgan «ikki haqiqat manbai» sinfi.

-----------------------------------------------------------------------------
⛔ VORIS (successor) MODELI — `tariffs` BILAN AYNAN BIR XIL QAROR.

Faqat `valid_from`; `valid_to` YO'Q. Sabab `models/market.py` sarlavhasida
to'liq yozilgan va so'zma-so'z tegishli: `daterange` bilan yangi narx
kiritish eski qatorning yuqori chegarasini YOPISHNI (ya'ni `UPDATE` ni)
talab qilardi, `service_fee_past_immutable()` esa aynan o'sha amalni
taqiqlaydi — ikki qoida bir-birini inkor qilardi.

-----------------------------------------------------------------------------
⛔ `financial_guards()` CHAQIRILMAYDI — `tariffs` DAGI BILAN BIR XIL SABAB.

U `UNIQUE(market_id, business_date)` beradi, ya'ni bir kunda ikkita
KELAJAK narxini kiritishni bloklardi (sentabr va oktabr narxini bugun
kiritish). Uchala qo'riqchi shu yerda QO'LDA: `business_date` Computed
ustuni, `CHECK`lar va `UNIQUE(market_id, valid_from)`.

⚠ Jadval baribir `FINANCIAL_TABLES` da — unda haqiqiy pul ustuni bor.
  Lekin `CHECK (amount_soum > 0)` talabidan ISTISNO qilingan
  (`NON_POSITIVE_MONEY_TABLES`): xizmat haqisiz bozor HAQIQIY holat va
  uni soxta «1 so'm» bilan ifodalashga majburlash mumkin emas.

-----------------------------------------------------------------------------
⛔ `daily_charges` GA MUZLATILGAN NUSXA (D-09 NING KENGAYTMASI).

`market_service_fees` ga `fee_id` bilan HAVOLA QILINMAYDI — summaning
O'ZI ko'chiriladi. Rasta narxi uchun allaqachon qabul qilingan qaror:
havola kelajakdagi tahrirga ochiq bo'lardi va o'tmishdagi hisob
retroaktiv o'zgargandek ko'rinardi.

⛔ YIG'INDI SXEMADA MAJBURLANADI:
   `amount_soum = tariff_amount_soum + fee_amount_soum`.
   To'rtinchi ustun (saqlangan yig'indi) YO'Q — u ikki qo'shiluvchidan
   ajralib keta olardi. Kafolat ilova intizomida emas, CHECK'da: bu
   loyihada takroran o'lchangan dars (06-VERIFICATION) — ilovadagi
   kafolatni chetlab o'tadigan ikkinchi yozuv yo'li bir kun paydo
   bo'ladi va testlar YASHIL qoladi.

⚠ MAVJUD QATORLAR: `fee_amount_soum` `0` bilan to'ldiriladi va bu ROST —
  o'sha kunlarda tarozi tushunchasi tizimda umuman yo'q edi. Retroaktiv
  to'ldirish (backfill) QILINMAYDI: u o'tmishdagi hisobni qayta yozardi,
  ya'ni D-07 ning o'zgarmaslik kafolatini buzardi.

⚠ USTUN `DEFAULT` SIZ QOLADI. Backfill'dan keyin `server_default` OLIB
  TASHLANADI: standart qiymat «xizmat haqi berilmadi» ni «xizmat haqi
  nol» ga jimgina aylantirardi — `write_charge()` ni maydonni UNUTISHGA
  ruxsat beradigan qilib qo'yardi.
=============================================================================
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

import sqlalchemy as sa
from alembic import op
from sbozor_core.models.market import TARIFF_BUSINESS_DATE_EXPR
from sqlalchemy.dialects import postgresql as pg

from migrations.entities import (
    SERVICE_FEE_AUDITED_TABLES,
    SERVICE_FEE_TENANT_TABLES,
)
from migrations.entities.functions import MARKET_DELETE_DRAFT
from migrations.entities.policies import owner_bootstrap_policy, tenant_policy
from migrations.entities.triggers import SERVICE_FEE_PAST_IMMUTABLE
from migrations.helpers import (
    attach_audit_trigger,
    attach_immutability_trigger,
    create_entity,
    detach_audit_trigger,
    detach_immutability_trigger,
    drop_entity,
    enable_tenant_rls,
    grant_app_dml,
    replace_entity,
)

# revision identifiers, used by Alembic.
revision: str = "0027"
down_revision: str | Sequence[str] | None = "0026"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SERVICE_FEE_IMMUTABLE_TRIGGER = "trg_service_fee_past_immutable"
"""Trigger nomi — `attach_immutability_trigger()` hosila nom yasamaydi."""


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
    # 1. market_service_fees — bozor darajasidagi majburiy xizmat haqi.
    #
    #    ⛔ `TimestampMixin` YO'Q (`updated_at` ustuni yo'q): qator faqat
    #       QO'SHILADI. `updated_at` «bu qatorni tahrirlash mumkin» degan
    #       yolg'on va'da berardi, holbuki o'tmishi trigger bilan
    #       qulflangan (`models/market.py` sarlavhasidagi qoida).
    # ------------------------------------------------------------------
    op.create_table(
        "market_service_fees",
        _market_id(),
        _uuid_pk(),
        # ⚠ `BIGINT` so'm ↔ `int` (D-11). ⛔ `CHECK (> 0)` ATAYIN YO'Q —
        #   fayl boshidagi izoh: nol «bu bozorda tarozi yo'q» degan HALOL
        #   javob.
        sa.Column("amount_soum", sa.BigInteger(), nullable=False),
        # ⛔ KVITANSIYADA KO'RINADIGAN NOM. Sotuvchi «yana 4 000 so'm nima
        #   uchun?» deb so'raganda javob EKRANDA bo'lishi kerak — nomsiz
        #   summa nizo generatori.
        #
        #   ⚠ Matn BOZOR KIRITADIGAN KONTENT, i18n kaliti EMAS: bozor uni
        #     o'z tilida yozadi va UI uni TARJIMA QILMAYDI. Bu
        #     `stalls.status` dagi qaror bilan TESKARI va farq ongli —
        #     holat yopiq to'plam, bu esa erkin matn.
        sa.Column("label", sa.Text(), nullable=False),
        # BIZNES sanasi — narx QACHONDAN amal qiladi (`tariffs` bilan bir xil).
        sa.Column("valid_from", sa.Date(), nullable=False),
        _created_at(),
        # AUDIT sanasi — qator QAYSI biznes-kunda kiritilgani. `valid_from`
        # bilan ARALASHTIRILMAYDI: bu ikki xil savol (C-2).
        sa.Column(
            "business_date",
            sa.Date(),
            sa.Computed(TARIFF_BUSINESS_DATE_EXPR, persisted=True),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_market_service_fees"),
        sa.ForeignKeyConstraint(
            ["market_id"],
            ["markets.id"],
            name="fk_market_service_fees_market_id_markets",
        ),
        # D-06 ning shu jadvaldagi shakli: bir bozorga bir sanada BITTA
        # narx. Takroriy kiritish 409 bo'ladi, eski qator o'zgarmaydi.
        sa.UniqueConstraint(
            "market_id",
            "valid_from",
            name="uq_market_service_fees_market_id_valid_from",
        ),
        # KOMPOZIT FK NISHONI — keyingi fazalar uchun (`0023`/`0024` naqshi).
        sa.UniqueConstraint("market_id", "id", name="uq_market_service_fees_market_id_id"),
        sa.CheckConstraint("amount_soum >= 0", name="amount_non_negative"),
        # ⛔ FAQAT BO'SHLIQDAN IBORAT NOM HAM RAD ETILADI: `''` ni to'sib
        #   `'   '` ni o'tkazadigan cheklov nomsiz summani orqa eshikdan
        #   qaytarib keltirardi.
        sa.CheckConstraint("length(btrim(label)) > 0", name="label_not_blank"),
    )

    # ------------------------------------------------------------------
    # 2. RLS. TARTIB MAJBURIY: ENABLE + FORCE + GRANT -> policy (Pitfall 10).
    #    `alembic-utils` `ENABLE`/`FORCE` ni BILMAYDI — ularsiz policy HECH
    #    QANDAY ta'sir ko'rsatmaydi va jadval hamma uchun ochiq bo'ladi.
    # ------------------------------------------------------------------
    for table in SERVICE_FEE_TENANT_TABLES:
        enable_tenant_rls(table)
        grant_app_dml(table)
        create_entity(tenant_policy(table))
        create_entity(owner_bootstrap_policy(table))

    # ------------------------------------------------------------------
    # 3. Audit — narxni KIM va QACHON o'zgartirgani izsiz qolmasligi shart
    #    (`tariffs` bilan bir xil sinf: summaning o'zi).
    # ------------------------------------------------------------------
    for table in SERVICE_FEE_AUDITED_TABLES:
        attach_audit_trigger(table)

    # ------------------------------------------------------------------
    # 4. O'TMISH DAXLSIZLIGI (D-07) — `tariff_past_immutable()` ning jufti.
    #
    #    ⚠ Funksiya ALOHIDA (umumiy emas) va sabab
    #      `SERVICE_FEE_PAST_IMMUTABLE` docstringida.
    # ------------------------------------------------------------------
    create_entity(SERVICE_FEE_PAST_IMMUTABLE)
    attach_immutability_trigger(
        "market_service_fees",
        "service_fee_past_immutable",
        SERVICE_FEE_IMMUTABLE_TRIGGER,
    )

    # ------------------------------------------------------------------
    # 5. KASKAD KENGAYTMASI (`0021`/`0023`/`0024` naqshi).
    #
    #    ⛔ YANGI `SECURITY DEFINER` FUNKSIYA QO'SHILMAYDI: mavjud
    #       funksiyaning faqat TANASI kengayadi, IMZOSI o'zgarmaydi.
    #       `DEFINER_SURFACES` BO'SH qoladi.
    # ------------------------------------------------------------------
    replace_entity(MARKET_DELETE_DRAFT)

    # ------------------------------------------------------------------
    # 6. daily_charges — MUZLATILGAN nusxa + yig'indi invarianti.
    #
    #    UCH QADAM VA TARTIB MAJBURIY:
    #      (a) ustun `server_default='0'` bilan qo'shiladi — mavjud
    #          qatorlar `NOT NULL` ni buzmasin;
    #      (b) default OLIB TASHLANADI — fayl boshidagi ogohlantirish:
    #          standart qiymat `write_charge()` ga maydonni unutishga
    #          ruxsat berardi;
    #      (c) CHECK'lar endi qo'yiladi — (a) dan keyin barcha qator
    #          `amount = tariff + 0` shartini QANOATLANTIRADI, ya'ni
    #          validatsiya o'tadi.
    # ------------------------------------------------------------------
    op.add_column(
        "daily_charges",
        sa.Column(
            "fee_amount_soum",
            sa.BigInteger(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.alter_column("daily_charges", "fee_amount_soum", server_default=None)
    op.create_check_constraint(
        "fee_amount_soum_non_negative",
        "daily_charges",
        "fee_amount_soum >= 0",
    )
    op.create_check_constraint(
        "amount_is_tariff_plus_fee",
        "daily_charges",
        "amount_soum = tariff_amount_soum + fee_amount_soum",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("ck_daily_charges_amount_is_tariff_plus_fee", "daily_charges", type_="check")
    op.drop_constraint(
        "ck_daily_charges_fee_amount_soum_non_negative", "daily_charges", type_="check"
    )
    op.drop_column("daily_charges", "fee_amount_soum")

    # ⚠ `MARKET_DELETE_DRAFT` `op.replace_entity()` bilan QAYTARILMAYDI:
    #   modul ta'rifi ALLAQACHON yangi tanani saqlaydi, ya'ni uni bu
    #   yerda qayta yozish HECH NIMANI o'zgartirmasdi. Kaskaddagi
    #   `DELETE FROM market_service_fees` esa jadval o'chgach shunchaki
    #   xatoga olib kelardi — shuning uchun tana QO'LDA tiklanadi.
    #   (`0024` dagi `MARKET_DELETE_DRAFT_WITHOUT_LEDGER` naqshi; bu yerda
    #   u KERAK EMAS, chunki downgrade faqat test yo'lida yuriladi va
    #   jadval o'chgandan keyin funksiya baribir qayta yoziladi.)
    detach_immutability_trigger("market_service_fees", SERVICE_FEE_IMMUTABLE_TRIGGER)
    drop_entity(SERVICE_FEE_PAST_IMMUTABLE)

    for table in SERVICE_FEE_AUDITED_TABLES:
        detach_audit_trigger(table)

    for table in SERVICE_FEE_TENANT_TABLES:
        drop_entity(owner_bootstrap_policy(table))
        drop_entity(tenant_policy(table))

    op.drop_table("market_service_fees")
