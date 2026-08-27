"""billing_domain: kunlik hisob, tuzatish, dalil, to'lov, smena va anomaliya

Revision ID: 0020
Revises: 0019
Create Date: 2026-08-10

6-FAZANING BIRINCHI MIGRATSIYASI. Oltita yangi tenant jadvalini olib keladi
va shu bilan `tests/integration/test_market_delete_guard.py::
test_cascade_covers_every_table_referencing_markets` ni ATAYIN QIZARTIRADI —
kaskadni kengaytirish `0021_market_delete_billing` da, AYNAN SHU REJANING
oynasida bajariladi (`0012`->`0013`, `0014`->`0015` va `0018`->`0019`
juftliklarining TO'RTINCHI takrori, OP-1).

=============================================================================
BU MIGRATSIYADA QOTIB QOLADIGAN SAKKIZ QAROR:

1. NOM `daily_charges`, `charges` EMAS (C-1). Nom 1-fazadan QULFLANGAN:
   `sbozor_core.schema_contract.FINANCIAL_TABLES` uni AYNAN shu nom bilan
   kutadi va `tests/tenancy/test_meta.py::test_financial_tables_have_guards`
   bazada shu nomni izlaydi. `charges` deb nomlash darvozani «jadval yo'q»
   holatida JIMGINA yashil qoldirardi — ya'ni uchala moliyaviy qo'riqchi
   ham hech qachon tekshirilmasdi. D-06 va D-07 ning MA'NOSI o'zgarmaydi.

2. `service_date` VA `business_date` — IKKI XIL SAVOL (C-2), VA
   `financial_guards()` SHUNING UCHUN CHAQIRILMAYDI.

       service_date  — hisob QAYSI KUN uchun yozildi (DOMEN sanasi)
       business_date — qator QAYSI KUNDA yozildi   (AUDIT fakti)

   Yordamchi `UNIQUE (market_id, <kalit>, business_date)` beradi, ya'ni
   idempotentlik kalitini QATOR YOZILGAN KUNGA bog'laydi. Kun esa ERTASI
   KUNI 04:10 da yopiladi (C-3), ya'ni kalit `business_date` ustida
   bo'lsa kunni QAYTA yopish IKKINCHI hisob yaratardi. Uchala qo'riqchi
   QO'LDA yoziladi — `0008_temporal.py:164-182` ning AYNAN presedenti
   (`tariffs` bu muammoni 2-fazada shunday hal qilgan).

   ⚠ 06-01 ning A2 zondi Variant B ni (`business_date GENERATED ALWAYS AS
   (service_date) STORED`) HAQIQIY `postgres:18.4` da o'lchagan: u
   ISHLAYDI (`GENERATED_FROM_COLUMN_SUPPORTED = True`). Baribir VARIANT A
   tanlandi — Variant B «qator qachon yozilgan» AUDIT FAKTINI butunlay
   yo'qotardi (backfill bilan normal `billing_close` ni farqlab
   bo'lmasdi) va D-02 ning nizo modeli aynan shunga tayanadi.

3. `payments.charge_id` YO'Q (C-4/D-24). To'lov — SOTUVCHI darajasidagi
   KREDIT. Sabab MEXANIK: kassir kun davomida yig'adi, hisob esa ertasi
   kuni tug'iladi — to'lov paytida `charge_id` MAVJUD EMAS; ustiga bitta
   to'lov bir necha kunlik qarzni yopishi mumkin (§9.6), ya'ni bog'lanish
   1:1 emas. Kun kesimi HOSILA qoida bilan olinadi
   (`sbozor_core.billing.allocate_charge_credit()`,
   `FIFO_OLDEST_SERVICE_DATE_FIRST`, 06-01) va u SAQLANMAYDI:
   ⛔ `payment_allocations` jadvali ham, `allocated_*` ustuni ham
   YARATILMAYDI (D-07 va BILL-03 buni taqiqlaydi).

4. MANFIY SUMMA YOZILMAYDI (C-5). Har joyda MUSBAT KATTALIK +
   `kind`/`direction`. `test_meta.py:1341-1347` har moliyaviy jadvaldan
   `CHECK (amount_soum > 0)` talab qiladi va `money.py:78-79` manfiyni
   rad etadi. D-23 ning «belgili summalar yig'indisi» iborasi —
   HISOBLASH USULI, ustun tipi emas.

5. MUZLATILGAN DALIL — `charge_evidence.occupancy_event_id` (C-7).
   `stall_slot_occupancy` MUTABLE (`_MATERIALIZE_SLOT` `DO UPDATE`
   ishlatadi), ya'ni uning `id` si dalil EMAS: kun qayta hisoblanganda
   o'sha qator boshqa hukmni ko'rsatishi mumkin. `occupancy_events` esa
   `0018` bilan SHARTSIZ o'zgarmas. `stall_slot_occupancy_id` FAQAT
   audit havolasi.

6. `quote_soum` + JUFTLANGAN `CHECK` D-19 NI STRUKTURAVIY QILADI
   (T-06-18). D-19 ni ilova qatlamida («422 `reason_required`»)
   qoldirish `CHECK` bilan qulflashdan KUCHSIZ — xom SQL yo'li ilova
   validatsiyasini BUTUNLAY chetlab o'tadi
   (`migrations/entities/triggers.py:4-20` da o'lchangan sinf).
   `CHECK ((amount_soum = quote_soum) = (override_reason IS NULL))`
   ikki tomonlama: SABABSIZ o'zgartirish ham, O'ZGARISHSIZ sabab ham
   IFODALAB BO'LMAYDI.
   ⚠ Qisman to'lov (OQ-4) BU BILAN TAQIQLANMAYDI: kichik summa
   `override_reason` bilan keladi, ya'ni sabab YOZILADI.

7. IKKI ORFAN `SECURITY DEFINER` FUNKSIYA DROP QILINADI (C-11/G-10).
   `audit_draw_due_markets()` va `occupancy_day_close_markets()`
   CHAQIRUVCHISIZ qoldi va argumentli job modeli (D-12) ularni
   PRINSIPIAL ravishda ishlata olmaydi: ikkalasining tanasi ham `now()`
   ga qadalgan, job esa kunni ARGUMENT sifatida oladi. Chaqiruvchisiz
   `SECURITY DEFINER` — RLS'ni chetlab o'tadigan ISHLATILMAYOTGAN yuza,
   ya'ni u faqat xavf qo'shadi (T-06-22). `PGFunction` ta'riflari
   `functions.py` da JOYIDA QOLADI (`downgrade()` ularni qaytaradi),
   reyestrlar esa BO'SHATILDI — aks holda `test_autogenerate_is_empty`
   ularni «qayta yaratish kerak» deb ko'rsatardi (OP-2).

8. `stall_slot_occupancy` GA `UNIQUE (market_id, id)` BIRINCHI QADAMDA
   QO'SHILADI (OP-11). Usiz `charge_evidence` ning kompozit FK'si
   `asyncpg.exceptions.InvalidForeignKeyError` beradi va MIGRATSIYANING
   O'ZI yiqiladi — `0018:266-287` dagi `uq_snapshots_market_id_id`
   holatining AYNAN takrori.
=============================================================================

⚠ `CHECK` NOMLARI QISQA YOZILADI (`ck_` prefiksisiz) — `0018` da
o'rnatilgan qoida. SQLAlchemy ning `ck` kaliti
(`ck_%(table_name)s_%(constraint_name)s`) ichida `%(constraint_name)s`
TOKENI bor, ya'ni konvensiya ALLAQACHON NOMLANGAN `CHECK` ga ham
qo'llanadi va to'liq nom yozilsa natija IKKI KARRA prefiks bo'lardi.
Qolgan uch kalitda (`uq`, `fk`, `ix`) bu token YO'Q — ular to'liq
yoziladi.

⚠ `cashier_shifts` DA IKKALA TRIGGER HAM BO'LADI (audit + o'zgarmaslik).
Postgres ning tartib qoidasi aynan kerakli natijani beradi: `BEFORE`
`AFTER` dan OLDIN yuradi, ya'ni qo'riqchi rad etgan `UPDATE` `audit_log`
ga qator QOLDIRMAYDI — rad etilgan urinish "o'zgardi" deb yozilmasin.

⚠ YANGI `SECURITY DEFINER` FUNKSIYA QO'SHILMAYDI (T-06-22). Bu faza
DEFINER yuzasini faqat KAMAYTIRADI (7-band).
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime
from uuid import UUID

import sqlalchemy as sa
from alembic import op
from sbozor_core.models.billing import (
    ADJUSTMENT_DIRECTION_CHECK,
    ADJUSTMENT_REASON_CHECK,
    ANOMALY_EVIDENCE_IS_PAIRED_CHECK,
    ANOMALY_KIND_CHECK,
    BILLING_ANOMALY_INDEX,
    CHARGE_ADJUSTMENT_INDEX,
    CHARGE_EVIDENCE_INDEX,
    DAILY_CHARGE_DAY_INDEX,
    DAILY_CHARGE_VENDOR_INDEX,
    NO_COVERAGE_ANOMALY_IS_PAIRED_CHECK,
    OVERRIDE_IS_PAIRED_CHECK,
    OVERRIDE_REASON_CHECK,
    PAYMENT_KIND_CHECK,
    PAYMENT_METHOD_CHECK,
    PAYMENT_STALL_INDEX,
    PAYMENT_VENDOR_INDEX,
    REVERSAL_HAS_NO_OVERRIDE_CHECK,
    REVERSAL_IS_PAIRED_CHECK,
    REVERSAL_REASON_CHECK,
    REVERSAL_REASON_IS_PAIRED_CHECK,
    SERVICE_DATE_NOT_IN_FUTURE_CHECK,
    SHIFT_CLOSED_HAS_DECLARATION_CHECK,
    SHIFT_CLOSED_HAS_SYSTEM_TOTAL_CHECK,
    SHIFT_CLOSED_IS_PAIRED_CHECK,
    SHIFT_OPEN_INDEX,
    SHIFT_OPEN_PREDICATE,
    SHIFT_STATUS_CHECK,
)
from sqlalchemy.dialects import postgresql as pg

from migrations.entities import BILLING_AUDITED_TABLES, BILLING_DELETE_ORDER, BILLING_TENANT_TABLES
from migrations.entities.functions import AUDIT_DRAW_DUE_MARKETS, OCCUPANCY_DAY_CLOSE_MARKETS
from migrations.entities.policies import owner_bootstrap_policy, tenant_policy
from migrations.entities.triggers import (
    CHARGE_IMMUTABLE,
    PAYMENT_IMMUTABLE,
    SHIFT_DECLARATION_IMMUTABLE,
)
from migrations.helpers import (
    APP_ROLE,
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
revision: str = "0020"
down_revision: str | Sequence[str] | None = "0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# ⚠ INDEKS NOMLARI, PREDIKATLARI VA `CHECK` IFODALARI SHU YERDA E'LON
#   QILINMAYDI — ular `sbozor_core.models.billing` dan IMPORT qilinadi
#   (yuqoriga qarang), `business_date` ifodasi esa
#   `migrations.helpers.BUSINESS_DATE_EXPR` dan.
#
#   Sabab O'LCHANGAN (03-03, birinchi urinish): `op.create_index(...)`
#   yolg'iz o'zi yetarli emas. Autogenerate model metadata'sini baza bilan
#   solishtiradi, ya'ni modelda e'lon qilinmagan indeks "o'chirilgan" deb
#   ko'rinadi va `test_autogenerate_is_empty` `remove_index` bilan qizaradi
#   (OP-10). Indeks IKKALA tomonda ham bo'lishi shart, nom va predikat esa
#   BITTA manbadan kelishi shart.

IMMUTABILITY_TRIGGERS: tuple[tuple[str, str, str], ...] = (
    ("daily_charges", "charge_immutable", "trg_charge_immutable"),
    ("payments", "payment_immutable", "trg_payment_immutable"),
    ("cashier_shifts", "shift_declaration_immutable", "trg_shift_declaration_immutable"),
)
"""`(jadval, funksiya, trigger)` uchliklari — `0018:196-199` naqshi.

Ro'yxat shu yerda, chunki `upgrade()` ham, `downgrade()` ham uning ustidan
tsikl qiladi va nomlar IKKI joyda yozilsa ular ajralib ketishi mumkin
bo'lardi: `downgrade()` boshqa nomni `DROP TRIGGER IF EXISTS` bilan
qidirardi va qo'riqchi JIMGINA joyida qolardi.

⚠ UCHTA JADVAL, UCHTA ALOHIDA FUNKSIYA (`helpers.py:278-282` qoidasi) va
ular IKKI XIL SHAKLDA: birinchi ikkitasi SHARTSIZ (D-07/D-23), uchinchisi
SHARTLI (D-25 — smena `open` -> `closed` o'tishi ruxsat etilishi SHART).
Tanlovning sababi `migrations/entities/triggers.py` ning 0020 blokida.
"""

_ORPHAN_DEFINER_FUNCTIONS = (AUDIT_DRAW_DUE_MARKETS, OCCUPANCY_DAY_CLOSE_MARKETS)
"""Chaqiruvchisiz qolgan ikki `SECURITY DEFINER` yuzasi (C-11/G-10).

`upgrade()` ularni DROP qiladi, `downgrade()` esa QAYTARADI. Ta'riflar
`migrations/entities/functions.py` da JOYIDA QOLADI — reyestrlar
(`OCCUPANCY_FUNCTIONS`, `OCCUPANCY_GRANT_SIGNATURES`) esa AYNI COMMITDA
bo'shatildi (OP-2).
"""

_ORPHAN_DEFINER_SIGNATURES = ("audit_draw_due_markets()", "occupancy_day_close_markets()")
"""`_ORPHAN_DEFINER_FUNCTIONS` bilan bir xil TARTIBDA — `downgrade()` ning `_regrant` i."""


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


def _business_date() -> sa.Column[date]:
    """`business_date` — `created_at` DAN HOSILA, STORED (C-2 / Variant A).

    Ifoda `migrations.helpers` dan IMPORT qilinadi: uchinchi nusxa yozilsa
    mintaqa arifmetikasi ajralib ketardi (`0008_temporal.py:196-206`
    naqshi). IKKI ARGUMENTLI `AT TIME ZONE` shakli MAJBURIY — u IMMUTABLE,
    bitta argumentlisi STABLE va generated ustunda umuman ruxsat
    etilmaydi.
    """
    return sa.Column(
        "business_date",
        sa.Date(),
        sa.Computed(BUSINESS_DATE_EXPR, persisted=True),
        nullable=False,
    )


def _regrant(signature: str) -> None:
    """`REVOKE PUBLIC` + `GRANT sbozor_app` — `0018:242-251` naqshi.

    FAQAT `downgrade()` da ishlatiladi: bu migratsiya YANGI funksiya
    YARATMAYDI, u faqat ikkitasini DROP qiladi. `downgrade()` esa ularni
    qaytaradi va `CREATE FUNCTION` dan keyin Postgres `EXECUTE TO PUBLIC`
    ni STANDART beradi — usiz «tor yuza» qarori jimgina bekor bo'lardi.
    """
    op.execute(f"REVOKE ALL ON FUNCTION {signature} FROM PUBLIC")
    op.execute(f"GRANT EXECUTE ON FUNCTION {signature} TO {APP_ROLE}")


def upgrade() -> None:
    """Upgrade schema."""
    # ------------------------------------------------------------------
    # 0b. `stall_slot_occupancy (market_id, id)` — YETISHMAYOTGAN KOMPOZIT
    #     FK NISHONI (fayl boshidagi 8-band, OP-11).
    #
    #     ⛔ TARTIB MAJBURIY: bu qator `charge_evidence` DAN OLDIN turishi
    #     SHART. O'LCHANGAN naqsh (`0018:266-287`): usiz migratsiyaning
    #     O'ZI `asyncpg.exceptions.InvalidForeignKeyError: there is no
    #     unique constraint matching given keys for referenced table
    #     "stall_slot_occupancy"` bilan yiqiladi.
    #
    #     SABAB: 5-fazada `stall_slot_occupancy` ZANJIRNING OXIRI edi —
    #     unga hech kim tayanmasdi, ya'ni `(market_id, id)` juftligi kerak
    #     emasdi. 6-fazada `charge_evidence` unga AUDIT havolasi bilan
    #     tayanadi.
    #
    #     Konstrayt `market_id` bilan BOSHLANADI, ya'ni `INDEX_EXCEPTIONS`
    #     ga qo'shish TALAB QILINMAYDI.
    # ------------------------------------------------------------------
    op.create_unique_constraint(
        "uq_stall_slot_occupancy_market_id_id", "stall_slot_occupancy", ["market_id", "id"]
    )

    # ------------------------------------------------------------------
    # 1. cashier_shifts — kassir smenasi (CASH-03/CASH-04, D-25/D-27).
    #
    #    BIRINCHI, chunki `payments.shift_id` unga kompozit FK bilan
    #    tayanadi (`BILLING_TENANT_TABLES` tartibi).
    #
    #    IKKI VAQT USTUNI: `opened_at` — DOMEN fakti (smena qachon
    #    ochildi), `created_at` — AUDIT fakti (qator qachon yozildi).
    #    C-2 ning aynan takrori va bir xil sababdan: `business_date`
    #    `created_at` DAN hosila bo'lishi shart, aks holda mintaqa
    #    ifodasining ikkinchi nusxasi paydo bo'lardi.
    # ------------------------------------------------------------------
    op.create_table(
        "cashier_shifts",
        _market_id(),
        _uuid_pk(),
        sa.Column("cashier_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.Text(), server_default=sa.text("'open'"), nullable=False),
        sa.Column(
            "opened_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        # KO'R DEKLARATSIYA (CASH-04): kassir kassadagi naqd summani tizim
        # summasini KO'RMASDAN kiritadi.
        sa.Column("declared_soum", sa.BigInteger(), nullable=True),
        sa.Column("system_soum", sa.BigInteger(), nullable=True),
        _created_at(),
        _business_date(),
        sa.PrimaryKeyConstraint("id", name="pk_cashier_shifts"),
        sa.ForeignKeyConstraint(
            ["market_id"], ["markets.id"], name="fk_cashier_shifts_market_id_markets"
        ),
        # ⛔ `ondelete` YO'Q (NO ACTION): smenasi bor kassirni o'chirish RAD
        #   ETILADI. `CASCADE` bo'lganda bitta `DELETE FROM users` butun
        #   kassa tarixini o'chirib yuborardi (`zone_reviews.reviewer_id`
        #   bilan aynan bir xil qaror).
        sa.ForeignKeyConstraint(
            ["cashier_id"], ["users.id"], name="fk_cashier_shifts_cashier_id_users"
        ),
        # KOMPOZIT FK NISHONI: `payments` `(market_id, shift_id)` ga havola.
        sa.UniqueConstraint("market_id", "id", name="uq_cashier_shifts_market_id_id"),
        sa.CheckConstraint(SHIFT_STATUS_CHECK, name="status_allowed"),
        sa.CheckConstraint(SHIFT_CLOSED_IS_PAIRED_CHECK, name="closed_is_paired"),
        sa.CheckConstraint(SHIFT_CLOSED_HAS_DECLARATION_CHECK, name="closed_has_declaration"),
        sa.CheckConstraint(SHIFT_CLOSED_HAS_SYSTEM_TOTAL_CHECK, name="closed_has_system_total"),
        # ⚠ `>= 0`, `> 0` EMAS: butun smena terminal orqali o'tgan kun REAL
        #   holat (UI-SPEC §10.2) va `> 0` kassirni soxta naqd summa
        #   yozishga majburlardi.
        sa.CheckConstraint(
            "declared_soum IS NULL OR declared_soum >= 0", name="declared_soum_non_negative"
        ),
        sa.CheckConstraint(
            "system_soum IS NULL OR system_soum >= 0", name="system_soum_non_negative"
        ),
    )

    # ------------------------------------------------------------------
    # 2. daily_charges — kunlik patta hisobi (BILL-01, D-06/D-07/D-09/D-28).
    #
    #    ⛔ `financial_guards("daily_charges", ...)` CHAQIRILMAYDI —
    #    fayl boshidagi 2-band. Uchala qo'riqchi QO'LDA:
    #      * `business_date` STORED generated ustuni   (`_business_date()`)
    #      * `CHECK (amount_soum > 0)`                 (pastda)
    #      * `market_id` bilan boshlanadigan UNIQUE    (pastda, ikkita)
    #
    #    `vendor_id` `NOT NULL` (D-28): sotuvchisiz rastaga hisob
    #    YOZILMAYDI — u `billing_anomalies.unassigned_occupied` bo'ladi.
    #    `NULL` bilan yozish «kimdir qarzdor, lekin kim ekani noma'lum»
    #    yozuvini tug'dirardi va qarz hisoboti uni hech kimga biriktira
    #    olmasdi.
    #
    #    `tariff_id` HAM, `tariff_amount_soum` HAM saqlanadi (D-09): tarif
    #    keyin tahrirlansa o'tmishdagi hisob RETROAKTIV o'zgarardi.
    # ------------------------------------------------------------------
    op.create_table(
        "daily_charges",
        _market_id(),
        _uuid_pk(),
        sa.Column("stall_id", pg.UUID(as_uuid=True), nullable=False),
        # MUZLATILGAN NUSXA (D-28).
        sa.Column("vendor_id", pg.UUID(as_uuid=True), nullable=False),
        # DOMEN sanasi — hisob QAYSI KUN uchun (C-2).
        sa.Column("service_date", sa.Date(), nullable=False),
        sa.Column("tariff_id", pg.UUID(as_uuid=True), nullable=False),
        # Pul — `bigint` so'm; kasrli tip TAQIQLANGAN (D-11).
        sa.Column("tariff_amount_soum", sa.BigInteger(), nullable=False),
        sa.Column("amount_soum", sa.BigInteger(), nullable=False),
        _created_at(),
        _business_date(),
        sa.PrimaryKeyConstraint("id", name="pk_daily_charges"),
        sa.ForeignKeyConstraint(
            ["market_id"], ["markets.id"], name="fk_daily_charges_market_id_markets"
        ),
        sa.ForeignKeyConstraint(
            ["market_id", "stall_id"],
            ["stalls.market_id", "stalls.id"],
            name="fk_daily_charges_market_id_stall_id_stalls",
        ),
        sa.ForeignKeyConstraint(
            ["market_id", "vendor_id"],
            ["vendors.market_id", "vendors.id"],
            name="fk_daily_charges_market_id_vendor_id_vendors",
        ),
        sa.ForeignKeyConstraint(
            ["market_id", "tariff_id"],
            ["tariffs.market_id", "tariffs.id"],
            name="fk_daily_charges_market_id_tariff_id_tariffs",
        ),
        # ⚠⚠ D-06 NING IDEMPOTENTLIK KALITI — `service_date` USTIDA.
        #   Kunni QAYTA yopish (yoki backfill) ikkinchi hisob YARATMAYDI.
        sa.UniqueConstraint(
            "market_id",
            "stall_id",
            "service_date",
            name="uq_daily_charges_market_id_stall_id_service_date",
        ),
        sa.UniqueConstraint("market_id", "id", name="uq_daily_charges_market_id_id"),
        # ⛔ USTUN NOMI AYNAN `amount_soum` — `test_meta.py:1341-1347`
        #   regeksi (`amount_soum\\s*>\\s*0`) SHU nomni izlaydi.
        sa.CheckConstraint("amount_soum > 0", name="amount_soum_positive"),
        sa.CheckConstraint("tariff_amount_soum > 0", name="tariff_amount_soum_positive"),
        sa.CheckConstraint(SERVICE_DATE_NOT_IN_FUTURE_CHECK, name="service_date_not_in_future"),
    )

    # ------------------------------------------------------------------
    # 3. charge_adjustments — hisob tuzatishi (D-19, C-5).
    #
    #    ALOHIDA QATOR, `daily_charges` ning TAHRIRI EMAS (D-07): asl
    #    summa nizoda ko'rinib qolishi shart. Yakuniy summa —
    #    HISOBLANADIGAN KO'RINISH.
    # ------------------------------------------------------------------
    op.create_table(
        "charge_adjustments",
        _market_id(),
        _uuid_pk(),
        sa.Column("charge_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("direction", sa.Text(), nullable=False),
        sa.Column("reason_code", sa.Text(), nullable=False),
        # MUSBAT KATTALIK (C-5) — yo'nalish `direction` da.
        sa.Column("amount_soum", sa.BigInteger(), nullable=False),
        sa.Column("actor_user_id", pg.UUID(as_uuid=True), nullable=False),
        _created_at(),
        _business_date(),
        sa.PrimaryKeyConstraint("id", name="pk_charge_adjustments"),
        sa.ForeignKeyConstraint(
            ["market_id"], ["markets.id"], name="fk_charge_adjustments_market_id_markets"
        ),
        sa.ForeignKeyConstraint(
            ["market_id", "charge_id"],
            ["daily_charges.market_id", "daily_charges.id"],
            name="fk_charge_adjustments_charge",
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"], ["users.id"], name="fk_charge_adjustments_actor_user_id_users"
        ),
        # ⚠ `test_financial_tables_have_guards` ning uchinchi sharti
        #   (`conkey[1] = market_id`) AYNAN shu konstrayt bilan bajariladi:
        #   bu jadvalda tabiiy idempotentlik kaliti YO'Q — bir hisobga bir
        #   necha tuzatish yozilishi MUTLAQO qonuniy.
        sa.UniqueConstraint("market_id", "id", name="uq_charge_adjustments_market_id_id"),
        sa.CheckConstraint(ADJUSTMENT_DIRECTION_CHECK, name="direction_allowed"),
        sa.CheckConstraint(ADJUSTMENT_REASON_CHECK, name="reason_code_allowed"),
        sa.CheckConstraint("amount_soum > 0", name="amount_soum_positive"),
    )

    # ------------------------------------------------------------------
    # 4. charge_evidence — hisobning RASM-DALILI (BILL-02, C-7).
    #
    #    ⛔ `business_date` USTUNI ATAYIN YO'Q: dalil qatori KUNNI
    #    `daily_charges` dan MEROS qiladi (`charge_id`). Ikkinchi hosila
    #    sana yarim tunda bir kun farq qilishi mumkin bo'lardi (Pitfall 3)
    #    va o'shanda o'sha hisobning dalili hisobotda «yo'q» bo'lib
    #    qolardi.
    # ------------------------------------------------------------------
    op.create_table(
        "charge_evidence",
        _market_id(),
        _uuid_pk(),
        sa.Column("charge_id", pg.UUID(as_uuid=True), nullable=False),
        # AUDIT HAVOLASI — dalil EMAS (jadval MUTABLE, C-7).
        sa.Column("stall_slot_occupancy_id", pg.UUID(as_uuid=True), nullable=False),
        # ⚠⚠ MUZLATILGAN DALIL: `occupancy_events` SHARTSIZ o'zgarmas.
        sa.Column("occupancy_event_id", pg.UUID(as_uuid=True), nullable=False),
        # KADRGA YO'L — rasm-dalilni ko'rsatishning yagona manzili.
        sa.Column("snapshot_id", pg.UUID(as_uuid=True), nullable=False),
        # `stall_slot_occupancy` DAN NUSXALANADI, qayta hisoblanmaydi.
        sa.Column("slot_time", sa.Time(timezone=False), nullable=False),
        _created_at(),
        sa.PrimaryKeyConstraint("id", name="pk_charge_evidence"),
        sa.ForeignKeyConstraint(
            ["market_id"], ["markets.id"], name="fk_charge_evidence_market_id_markets"
        ),
        sa.ForeignKeyConstraint(
            ["market_id", "charge_id"],
            ["daily_charges.market_id", "daily_charges.id"],
            name="fk_charge_evidence_charge",
        ),
        # ⚠ NOM QISQARTIRILGAN va bu O'LCHANGAN zaruriyat: konvensiya nomi
        #   73 baytdan oshardi, PostgreSQL esa identifikatorni 63 baytga
        #   JIMGINA kesadi (`models/occupancy.py:997-1002` holati).
        #   ⛔ NISHON 0b BOSQICHIDA TUG'ILADI (OP-11).
        sa.ForeignKeyConstraint(
            ["market_id", "stall_slot_occupancy_id"],
            ["stall_slot_occupancy.market_id", "stall_slot_occupancy.id"],
            name="fk_charge_evidence_stall_slot_occupancy",
        ),
        sa.ForeignKeyConstraint(
            ["market_id", "occupancy_event_id"],
            ["occupancy_events.market_id", "occupancy_events.id"],
            name="fk_charge_evidence_occupancy_event",
        ),
        sa.ForeignKeyConstraint(
            ["market_id", "snapshot_id"],
            ["snapshots.market_id", "snapshots.id"],
            name="fk_charge_evidence_snapshot",
        ),
        # BIR HISOBGA BIR SLOTDAN BITTA DALIL: dublikat qator hisobotda
        # bitta kadrni ikki marta ko'rsatardi.
        sa.UniqueConstraint(
            "market_id",
            "charge_id",
            "stall_slot_occupancy_id",
            name="uq_charge_evidence_market_charge_slot",
        ),
        sa.UniqueConstraint("market_id", "id", name="uq_charge_evidence_market_id_id"),
    )

    # ------------------------------------------------------------------
    # 5. payments — kassir yozgan to'lov (CASH-01/CASH-02, D-20/D-21/D-23).
    #
    #    ⛔ `charge_id` YO'Q — fayl boshidagi 3-band (C-4/D-24).
    #    ⛔ `payment_allocations` jadvali ham YARATILMAYDI: taqsimlash
    #    HOSILA qoida (`FIFO_OLDEST_SERVICE_DATE_FIRST`) va u
    #    SAQLANMAYDI.
    #
    #    O'ZIGA HAVOLA (`reverses_payment_id`) AYNI `CREATE TABLE` da:
    #    PostgreSQL konstraytlarni tartib bilan qo'shadi — `UNIQUE`
    #    (`AT_PASS_ADD_INDEX`) FK dan (`AT_PASS_ADD_CONSTR`) OLDIN
    #    bajariladi, ya'ni o'ziga havola qiluvchi kompozit FK ishlaydi.
    # ------------------------------------------------------------------
    op.create_table(
        "payments",
        _market_id(),
        _uuid_pk(),
        sa.Column("stall_id", pg.UUID(as_uuid=True), nullable=False),
        # MUZLATILGAN NUSXA — `daily_charges.vendor_id` bilan bir xil qaror.
        sa.Column("vendor_id", pg.UUID(as_uuid=True), nullable=False),
        # ⚠ «TO'LOV QAYSI KUN UCHUN KIRITILDI», «qaysi kunning pattasi
        #   YOPILDI» EMAS — ikkinchisi FIFO qoidasidan chiqadi va
        #   SAQLANMAYDI (D-24).
        sa.Column("service_date", sa.Date(), nullable=False),
        sa.Column("amount_soum", sa.BigInteger(), nullable=False),
        # SERVER BERGAN summa (D-20) — fayl boshidagi 6-band.
        sa.Column("quote_soum", sa.BigInteger(), nullable=False),
        sa.Column("kind", sa.Text(), server_default=sa.text("'payment'"), nullable=False),
        sa.Column("method", sa.Text(), nullable=False),
        sa.Column("reverses_payment_id", pg.UUID(as_uuid=True), nullable=True),
        sa.Column("reversal_reason", sa.Text(), nullable=True),
        sa.Column("override_reason", sa.Text(), nullable=True),
        sa.Column("idempotency_key", sa.Text(), nullable=False),
        # SO'ROV TANASINING BARMOQ IZI — Pitfall 4: bir xil kalit BOSHQA
        # summa bilan kelsa 409 (06-09).
        sa.Column("request_fingerprint", sa.Text(), nullable=False),
        # ⚠ `NULL` RUXSAT (OQ-6/A5): direktor smenasiz to'lov kiritishi
        #   mumkin. `NOT NULL` o'sha holatda soxta smena ochishga
        #   majburlardi va variance hisoboti hech qachon yopilmaydigan
        #   qator bilan ifloslanardi.
        sa.Column("shift_id", pg.UUID(as_uuid=True), nullable=True),
        sa.Column("cashier_id", pg.UUID(as_uuid=True), nullable=False),
        _created_at(),
        _business_date(),
        sa.PrimaryKeyConstraint("id", name="pk_payments"),
        sa.ForeignKeyConstraint(
            ["market_id"], ["markets.id"], name="fk_payments_market_id_markets"
        ),
        sa.ForeignKeyConstraint(
            ["market_id", "stall_id"],
            ["stalls.market_id", "stalls.id"],
            name="fk_payments_market_id_stall_id_stalls",
        ),
        sa.ForeignKeyConstraint(
            ["market_id", "vendor_id"],
            ["vendors.market_id", "vendors.id"],
            name="fk_payments_market_id_vendor_id_vendors",
        ),
        sa.ForeignKeyConstraint(
            ["market_id", "reverses_payment_id"],
            ["payments.market_id", "payments.id"],
            name="fk_payments_reverses_payment",
        ),
        sa.ForeignKeyConstraint(
            ["market_id", "shift_id"],
            ["cashier_shifts.market_id", "cashier_shifts.id"],
            name="fk_payments_cashier_shift",
        ),
        sa.ForeignKeyConstraint(["cashier_id"], ["users.id"], name="fk_payments_cashier_id_users"),
        # ⚠⚠ D-21 NING IDEMPOTENTLIK KALITI. Shakl 06-01 ning A1 zondi
        #   bilan HAQIQIY `postgres:18.4` da o'lchangan
        #   (`IDEMPOTENT_GET_OR_CREATE_SUPPORTED = True`).
        sa.UniqueConstraint(
            "market_id", "idempotency_key", name="uq_payments_market_id_idempotency_key"
        ),
        sa.UniqueConstraint("market_id", "id", name="uq_payments_market_id_id"),
        sa.CheckConstraint(PAYMENT_KIND_CHECK, name="kind_allowed"),
        sa.CheckConstraint(PAYMENT_METHOD_CHECK, name="method_allowed"),
        sa.CheckConstraint(REVERSAL_REASON_CHECK, name="reversal_reason_allowed"),
        sa.CheckConstraint(OVERRIDE_REASON_CHECK, name="override_reason_allowed"),
        sa.CheckConstraint("amount_soum > 0", name="amount_soum_positive"),
        sa.CheckConstraint("quote_soum > 0", name="quote_soum_positive"),
        sa.CheckConstraint(REVERSAL_IS_PAIRED_CHECK, name="reversal_is_paired"),
        sa.CheckConstraint(REVERSAL_REASON_IS_PAIRED_CHECK, name="reversal_reason_is_paired"),
        # ⚠⚠ D-19 SXEMADA (fayl boshidagi 6-band).
        sa.CheckConstraint(OVERRIDE_IS_PAIRED_CHECK, name="override_is_paired"),
        sa.CheckConstraint(REVERSAL_HAS_NO_OVERRIDE_CHECK, name="reversal_has_no_override"),
    )

    # ------------------------------------------------------------------
    # 6. billing_anomalies — hisob YOZILMAGAN, lekin e'tibor talab
    #    qiladigan holat (C-12, D-05/D-10/D-28).
    #
    #    ⛔ JUFTLANGAN `CHECK` (`no_coverage_is_paired`) uchinchi `kind` ni
    #    birinchi ikkitasidan STRUKTURAVIY ajratadi: «ko'ra olmadik» ≠
    #    «band». Ikkovini bir joyga qo'shish KO'R NUQTADAN tushum da'vosi
    #    to'qish bo'lardi.
    # ------------------------------------------------------------------
    op.create_table(
        "billing_anomalies",
        _market_id(),
        _uuid_pk(),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("stall_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("service_date", sa.Date(), nullable=False),
        sa.Column("occupancy_event_id", pg.UUID(as_uuid=True), nullable=True),
        sa.Column("snapshot_id", pg.UUID(as_uuid=True), nullable=True),
        _created_at(),
        _business_date(),
        sa.PrimaryKeyConstraint("id", name="pk_billing_anomalies"),
        sa.ForeignKeyConstraint(
            ["market_id"], ["markets.id"], name="fk_billing_anomalies_market_id_markets"
        ),
        sa.ForeignKeyConstraint(
            ["market_id", "stall_id"],
            ["stalls.market_id", "stalls.id"],
            name="fk_billing_anomalies_market_id_stall_id_stalls",
        ),
        sa.ForeignKeyConstraint(
            ["market_id", "occupancy_event_id"],
            ["occupancy_events.market_id", "occupancy_events.id"],
            name="fk_billing_anomalies_occupancy_event",
        ),
        sa.ForeignKeyConstraint(
            ["market_id", "snapshot_id"],
            ["snapshots.market_id", "snapshots.id"],
            name="fk_billing_anomalies_snapshot",
        ),
        # JOB QAYTA YUGURISHI UCHUN IDEMPOTENTLIK: `billing_close` kun
        # davomida bir necha marta ishga tushishi mumkin.
        sa.UniqueConstraint(
            "market_id",
            "stall_id",
            "service_date",
            "kind",
            name="uq_billing_anomalies_market_stall_service_date_kind",
        ),
        sa.UniqueConstraint("market_id", "id", name="uq_billing_anomalies_market_id_id"),
        sa.CheckConstraint(ANOMALY_KIND_CHECK, name="kind_allowed"),
        sa.CheckConstraint(NO_COVERAGE_ANOMALY_IS_PAIRED_CHECK, name="no_coverage_is_paired"),
        sa.CheckConstraint(ANOMALY_EVIDENCE_IS_PAIRED_CHECK, name="evidence_is_paired"),
    )

    # ------------------------------------------------------------------
    # 7. INDEKSLAR — nomlar va predikat MODELDAN import qilinadi (fayl
    #    boshidagi ogohlantirish, OP-10).
    #
    #    QISMAN UNIQUE indeks `op.create_table` GA SIG'MAYDI
    #    (`postgresql_where` faqat `create_index` da bor).
    #
    #    HAMMASI `market_id` BILAN BOSHLANADI -> `INDEX_EXCEPTIONS` ga
    #    hech nima qo'shilmaydi.
    # ------------------------------------------------------------------
    op.create_index(
        DAILY_CHARGE_VENDOR_INDEX, "daily_charges", ["market_id", "vendor_id", "service_date"]
    )
    op.create_index(
        DAILY_CHARGE_DAY_INDEX, "daily_charges", ["market_id", "service_date", "stall_id"]
    )
    op.create_index(CHARGE_ADJUSTMENT_INDEX, "charge_adjustments", ["market_id", "charge_id"])
    op.create_index(CHARGE_EVIDENCE_INDEX, "charge_evidence", ["market_id", "charge_id"])
    op.create_index(PAYMENT_VENDOR_INDEX, "payments", ["market_id", "vendor_id", "service_date"])
    op.create_index(PAYMENT_STALL_INDEX, "payments", ["market_id", "stall_id", "service_date"])
    op.create_index(
        BILLING_ANOMALY_INDEX, "billing_anomalies", ["market_id", "service_date", "kind"]
    )
    # ⚠⚠ D-27 — BIR KASSIRDA BIR OCHIQ SMENA. Poyga DB'GA topshiriladi:
    #   ikki oynadan bir vaqtda ochilgan smena ilova qatlamining «avval
    #   tekshir, keyin yoz» shakli bilan TO'XTATILMASDI va to'lovlar ikki
    #   smenaga bo'linib, variance HAR IKKALASIDA ham kichik ko'rinardi.
    op.create_index(
        SHIFT_OPEN_INDEX,
        "cashier_shifts",
        ["market_id", "cashier_id"],
        unique=True,
        postgresql_where=sa.text(SHIFT_OPEN_PREDICATE),
    )

    # ------------------------------------------------------------------
    # 8. RLS. TARTIB MAJBURIY: ENABLE + FORCE + GRANT -> policy (Pitfall 10).
    #    `alembic-utils` `ENABLE`/`FORCE` ni BILMAYDI — ularsiz policy HECH
    #    QANDAY ta'sir ko'rsatmaydi va jadval hamma uchun ochiq bo'ladi.
    # ------------------------------------------------------------------
    for table in BILLING_TENANT_TABLES:
        enable_tenant_rls(table)
        create_entity(tenant_policy(table))
        create_entity(owner_bootstrap_policy(table))

    # ------------------------------------------------------------------
    # 9. Audit — ATAYIN BOSHQA RO'YXAT USTIDAN.
    #
    #    `BILLING_AUDITED_TABLES` = (`charge_adjustments`, `cashier_shifts`).
    #    Qolgan to'rttasi o'zgarmas jadval yoki hodisa jurnali — sabablar
    #    `schema_contract.AUDITED_TABLES` docstringida NOMMA-NOM.
    #
    #    ⚠ IKKALA NOM `tests/tenancy/test_meta.py::PENDING_AUDIT_TRIGGERS`
    #      DAN SHU MIGRATSIYA BILAN BIR COMMITDA O'CHIRILDI (OP-4). T1
    #      ularni o'sha ro'yxatga qo'ygan edi (qarz ochiq); trigger endi
    #      ULANDI, ya'ni qarz YOPILDI va ro'yxat yana BO'SH. Buni unutish
    #      testni TESKARI yo'nalishdan qizartirardi (`closed` asserti) —
    #      reyestr IKKI TOMONLAMA.
    # ------------------------------------------------------------------
    for table in BILLING_AUDITED_TABLES:
        attach_audit_trigger(table)

    # ------------------------------------------------------------------
    # 10. O'ZGARMASLIK QO'RIQCHILARI (D-07 / D-23 / D-25).
    #
    #     UCH ALOHIDA FUNKSIYA, IKKI XIL SHAKLDA — tanlov va sabab
    #     `migrations/entities/triggers.py` ning 0020 blokida.
    #
    #     ⚠ TARTIB: funksiya AVVAL yaratiladi, trigger KEYIN ulanadi —
    #     `CREATE TRIGGER ... EXECUTE FUNCTION` mavjud funksiyani talab
    #     qiladi.
    # ------------------------------------------------------------------
    create_entity(CHARGE_IMMUTABLE)
    create_entity(PAYMENT_IMMUTABLE)
    create_entity(SHIFT_DECLARATION_IMMUTABLE)
    for table, function_name, trigger_name in IMMUTABILITY_TRIGGERS:
        attach_immutability_trigger(table, function_name, trigger_name)

    # ------------------------------------------------------------------
    # 11. ORFAN `SECURITY DEFINER` YUZASINI YOPISH (fayl boshidagi 7-band).
    #
    #     ⛔ BU MIGRATSIYA YANGI DEFINER FUNKSIYA QO'SHMAYDI — u ikkitasini
    #     OLIB TASHLAYDI. `tests/tenancy/test_occupancy_domain_meta.py::
    #     DEFINER_SURFACES` AYNI COMMITDA bo'shatildi (OP-2): u yerdagi
    #     test funksiyaning MAVJUDLIGINI talab qiladi (`assert row is not
    #     None, "bazada topilmadi"`), ya'ni DROP dan keyin reyestr bo'sh
    #     bo'lishi SHART.
    #
    #     ⚠ `test_meta.py::EXPECTED_DEFINER_FUNCTIONS` TEGILMAYDI — u
    #       ikkala funksiyani umuman sanamaydi va sharti `found >=
    #       EXPECTED` (quyi chegara).
    # ------------------------------------------------------------------
    for function in _ORPHAN_DEFINER_FUNCTIONS:
        drop_entity(function)


def downgrade() -> None:
    """Downgrade schema."""
    # TARTIB TESKARI: trigger AVVAL yechiladi, funksiya KEYIN o'chiriladi —
    # `DROP FUNCTION` unga tayanuvchi trigger mavjud bo'lganda yiqiladi.
    for table, _function_name, trigger_name in reversed(IMMUTABILITY_TRIGGERS):
        detach_immutability_trigger(table, trigger_name)
    drop_entity(SHIFT_DECLARATION_IMMUTABLE)
    drop_entity(PAYMENT_IMMUTABLE)
    drop_entity(CHARGE_IMMUTABLE)

    for table in reversed(BILLING_AUDITED_TABLES):
        detach_audit_trigger(table)

    for table in reversed(BILLING_TENANT_TABLES):
        drop_entity(owner_bootstrap_policy(table))
        drop_entity(tenant_policy(table))

    op.drop_index(SHIFT_OPEN_INDEX, table_name="cashier_shifts")
    op.drop_index(BILLING_ANOMALY_INDEX, table_name="billing_anomalies")
    op.drop_index(PAYMENT_STALL_INDEX, table_name="payments")
    op.drop_index(PAYMENT_VENDOR_INDEX, table_name="payments")
    op.drop_index(CHARGE_EVIDENCE_INDEX, table_name="charge_evidence")
    op.drop_index(CHARGE_ADJUSTMENT_INDEX, table_name="charge_adjustments")
    op.drop_index(DAILY_CHARGE_DAY_INDEX, table_name="daily_charges")
    op.drop_index(DAILY_CHARGE_VENDOR_INDEX, table_name="daily_charges")

    # TARTIB — `BILLING_DELETE_ORDER` bo'yicha, ya'ni FK zanjirida
    # BOLALARDAN ota-onaga. Ro'yxat `reversed(BILLING_TENANT_TABLES)` dan
    # HOSIL QILINMAYDI va sabab reyestrning o'z docstringida: bu domenda
    # IKKI MUSTAQIL zanjir bor va hosila qiymat `payments` ni
    # `charge_evidence` dan oldin qo'yardi.
    for table in BILLING_DELETE_ORDER:
        op.drop_table(table)

    # ⚠ KONSTRAYT O'CHIRISH XOM SQL BILAN (`0018:791-796` da o'rnatilgan
    #   qoida): `op.create_unique_constraint(...)` ga to'liq nom berilgan,
    #   ya'ni `uq` konvensiyasi (`%(constraint_name)s` tokeni YO'Q) uni
    #   o'zgartirmaydi va nom bazada AYNAN shunday turadi.
    op.execute(
        "ALTER TABLE public.stall_slot_occupancy "
        "DROP CONSTRAINT uq_stall_slot_occupancy_market_id_id"
    )

    # IKKI ORFAN FUNKSIYA QAYTARILADI (`0018:242-251` naqshi). `_regrant()`
    # MAJBURIY: `CREATE FUNCTION` dan keyin Postgres `EXECUTE TO PUBLIC` ni
    # STANDART beradi, ya'ni bazadagi HAR QANDAY rol RLS'ni chetlab
    # o'tadigan funksiyani chaqira olardi.
    for function in _ORPHAN_DEFINER_FUNCTIONS:
        create_entity(function)
    for signature in _ORPHAN_DEFINER_SIGNATURES:
        _regrant(signature)
