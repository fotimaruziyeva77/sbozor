"""notification_domain: case, case tarixi, outbox, bog'lanish va sozlama

Revision ID: 0023
Revises: 0022
Create Date: 2026-08-12

7-FAZANING BIRINCHI MIGRATSIYASI. Beshta yangi tenant jadvalini olib keladi
VA kaskadni AYNI MIGRATSIYADA kengaytiradi — ya'ni `0012`->`0013`,
`0014`->`0015`, `0018`->`0019` va `0020`->`0021` juftliklari bu yerda
TAKRORLANMAYDI.

⚠ NEGA JUFTLIK EMAS, NEGA BITTA MIGRATSIYA: to'rt marta takrorlangan
naqshda ikkinchi migratsiya faqat `market_delete_draft()` tanasini
almashtirardi va oradagi holatda `test_cascade_covers_every_table_
referencing_markets` ATAYIN QIZIL turardi. Bu reja ikkala qadamni ham
o'z oynasida bajaradi, ya'ni darvoza HECH QACHON qizil bo'lmaydi —
`06-04` / T2 ning splice qarori (OP-3) bilan bir xil mulohaza.

=============================================================================
BU MIGRATSIYADA QOTIB QOLADIGAN OLTI QAROR:

1. CASE — ALOHIDA JADVAL (D-11). `billing_anomalies` ga ham,
   `daily_charges` ga ham ustun QO'SHILMAYDI. Anomaliya/hisob — HODISA
   (o'zgarmas dalil), case — JARAYON (mas'ul, holat, yechim o'zgaradi).
   Ikkisini bitta qatorga qo'shish o'zgarmas dalil qatorini O'ZGARUVCHAN
   qilardi.

2. CASE AYNAN BITTA O'ZGARMAS QATORGA ISHORA QILADI (DQ-5) va buni UCHTA
   MUSTAQIL cheklov birga kafolatlaydi:

       fk_reconciliation_cases_anomaly  (market_id, anomaly_id)
           -> billing_anomalies (market_id, id)
       fk_reconciliation_cases_charge   (market_id, charge_id)
           -> daily_charges     (market_id, id)
       CHECK subject_is_exclusive       (anomaly_id IS NULL) <> (charge_id IS NULL)
       CHECK subject_kind_matches_target (subject_kind='anomaly') = (anomaly_id IS NOT NULL)

   ⛔ IKKALA NISHON UNIQUE CHEKLOVI ALLAQACHON MAVJUD va bu migratsiya
   ularni YARATMAYDI: `uq_billing_anomalies_market_id_id`
   (`0020_billing_domain.py:662`) va `uq_daily_charges_market_id_id`
   (`0020_billing_domain.py:414`). Ya'ni `0020` ning `stall_slot_occupancy`
   holati (OP-11, `InvalidForeignKeyError`) bu yerda TAKRORLANMAYDI.

3. IKKI IDEMPOTENTLIK CHEKLOVI — ILOVA INTIZOMI EMAS (D-21):
     * `UNIQUE (market_id, dedupe_key)` — bir to'lov, bir kvitansiya
       (6-fazaning T-06-49 bilan AYNAN bir sinf);
     * ikki QISMAN UNIQUE indeks — bir anomaliya/hisob, bir case.
   `recon.open` cron KONVERGENT (o'sha kun uchun qayta-qayta yuguradi),
   ya'ni ilova qatlamidagi «avval tekshir, keyin yoz» ikki parallel
   yugurishda ikkita case yozardi.

4. ⛔ HAR `CHECK` ENUMDAN HOSILA (`0020` naqshi,
   `test_every_check_is_derived_from_enum`): qiymat ro'yxati bu faylga
   LITERAL yozilmaydi, u `sbozor_core.models.notification` dan import
   qilinadi va u yerda `sbozor_core.enums` dan f-string bilan quriladi.
   Ikkinchi nusxa tug'ilmagani uchun «enumga a'zo qo'shilib migratsiya
   yozilmadi» holati YANGI bazada IFODALAB BO'LMAYDI.

5. BITTA O'ZGARMASLIK QO'RIQCHISI (`case_event_immutable()`, D-14/D-20):
   `reconciliation_case_events` SHARTSIZ o'zgarmas. Qolgan to'rtta jadval
   ATAYIN o'zgaradi va ularga qo'riqchi QO'YILMAYDI — case jarayon
   qatori, outbox holat mashinasi, bog'lanish bekor qilinadi, sozlama
   tahrirlanadi.

6. ⛔ YANGI `SECURITY DEFINER` FUNKSIYA QO'SHILMAYDI (T-06-22 / G7-7). Bu
   migratsiya DEFINER yuzasini KENGAYTIRMAYDI: `market_delete_draft(uuid)`
   ning faqat TANASI kengayadi, IMZOSI o'zgarmaydi va yangi funksiya
   umuman tug'ilmaydi. `tests/tenancy/test_occupancy_domain_meta.py::
   DEFINER_SURFACES` BO'SH qolishi SHART.
=============================================================================

⚠ `CHECK` NOMLARI QISQA YOZILADI (`ck_` prefiksisiz) — `0018` da
o'rnatilgan qoida. SQLAlchemy ning `ck` kaliti
(`ck_%(table_name)s_%(constraint_name)s`) ichida `%(constraint_name)s`
TOKENI bor, ya'ni to'liq nom yozilsa natija IKKI KARRA prefiks bo'lardi.

⚠ `financial_guards()` CHAQIRILMAYDI va bu ATAYIN: beshala jadvalda pul
ustuni YO'Q (`schema_contract.FINANCIAL_TABLES` ga ham qo'shilmagan).
Yordamchi `business_date` generated ustunini va `CHECK (amount_soum > 0)`
ni talab qilardi — yagona «tuzatish» yo'li SOXTA PUL USTUNI qo'shish
bo'lardi (2-fazaning Pitfall 3 tuzog'i).

⚠ `business_date` USTUNI HAM YO'Q va bu ham ATAYIN. U `FINANCIAL_TABLES`
ning talabi (`0020` ning C-2 bandi) va bu jadvallar u ro'yxatda emas.
Case'ning DOMEN sanasi `service_date` — u nomuvofiqlik QAYSI KUN uchun
aniqlanganini yozadi va `daily_charges` / `billing_anomalies` dagi bilan
AYNAN bir xil ma'noga ega.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

import sqlalchemy as sa
from alembic import op
from alembic_utils.pg_function import PGFunction
from sbozor_core.models.notification import (
    BINDING_ACTIVE_PREDICATE,
    BINDING_TELEGRAM_ACTIVE_INDEX,
    BINDING_VENDOR_ACTIVE_INDEX,
    CASE_KEYSET_INDEX,
    CASE_STATUS_CHECK,
    CASE_SUBJECT_ANOMALY_INDEX,
    CASE_SUBJECT_ANOMALY_PREDICATE,
    CASE_SUBJECT_CHARGE_INDEX,
    CASE_SUBJECT_CHARGE_PREDICATE,
    CASE_WORKLIST_INDEX,
    EVENT_FROM_STATUS_CHECK,
    EVENT_STATUS_TRANSITION_CHECK,
    EVENT_TO_STATUS_CHECK,
    OUTBOX_DUE_INDEX,
    OUTBOX_DUE_PREDICATE,
    OUTBOX_KIND_CHECK,
    OUTBOX_RECIPIENT_KIND_CHECK,
    OUTBOX_STATUS_CHECK,
    RECIPIENT_MATCHES_VENDOR_CHECK,
    RESOLUTION_NOTE_LENGTH_CHECK,
    SUBJECT_IS_EXCLUSIVE_CHECK,
    SUBJECT_KIND_CHECK,
    SUBJECT_KIND_MATCHES_TARGET_CHECK,
)
from sqlalchemy.dialects import postgresql as pg

from migrations.entities import (
    NOTIFICATION_AUDITED_TABLES,
    NOTIFICATION_DELETE_ORDER,
    NOTIFICATION_TENANT_TABLES,
)
from migrations.entities.functions import MARKET_DELETE_DRAFT
from migrations.entities.policies import owner_bootstrap_policy, tenant_policy
from migrations.entities.triggers import CASE_EVENT_IMMUTABLE
from migrations.helpers import (
    APP_ROLE,
    attach_audit_trigger,
    attach_immutability_trigger,
    create_entity,
    detach_audit_trigger,
    detach_immutability_trigger,
    drop_entity,
    enable_tenant_rls,
)

# revision identifiers, used by Alembic.
revision: str = "0023"
down_revision: str | Sequence[str] | None = "0022"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# ⚠ INDEKS NOMLARI, PREDIKATLARI VA `CHECK` IFODALARI SHU YERDA E'LON
#   QILINMAYDI — ular `sbozor_core.models.notification` dan IMPORT qilinadi
#   (yuqoriga qarang).
#
#   Sabab O'LCHANGAN (03-03, birinchi urinish): `op.create_index(...)`
#   yolg'iz o'zi yetarli emas. Autogenerate model metadata'sini baza bilan
#   solishtiradi, ya'ni modelda e'lon qilinmagan indeks "o'chirilgan" deb
#   ko'rinadi va `test_autogenerate_is_empty` `remove_index` bilan qizaradi
#   (OP-10). Indeks IKKALA tomonda ham bo'lishi shart, nom va predikat esa
#   BITTA manbadan kelishi shart.

MARKET_DELETE_DRAFT_SIGNATURE = "market_delete_draft(uuid)"

IMMUTABILITY_TRIGGERS: tuple[tuple[str, str, str], ...] = (
    ("reconciliation_case_events", "case_event_immutable", "trg_case_event_immutable"),
)
"""`(jadval, funksiya, trigger)` uchliklari — `0018`/`0020` naqshi.

Ro'yxat shu yerda, chunki `upgrade()` ham, `downgrade()` ham uning ustidan
tsikl qiladi va nomlar IKKI joyda yozilsa ular ajralib ketishi mumkin
bo'lardi: `downgrade()` boshqa nomni `DROP TRIGGER IF EXISTS` bilan
qidirardi va qo'riqchi JIMGINA joyida qolardi.

⚠ BITTA UCHLIK, lekin shakl `0020` dagi kabi TUPLE bo'lib qoladi: keyingi
faza ikkinchi qo'riqchi qo'shganda tsikl allaqachon tayyor turadi va
o'sha paytda «bitta element uchun tsikl kerakmi?» degan savol qayta
tug'ilmaydi.
"""


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
    """`updated_at` — FAQAT o'zgaradigan jadvallarda.

    ⚠ U «bu qatorni tahrirlash mumkin» degan VA'DA beradi va bu faqat
    uchta jadvalda ROST: `reconciliation_cases` (jarayon),
    `notification_outbox` (holat mashinasi) va
    `market_notification_settings` (sozlama). `models/billing.py` ning
    oltala jadvalida u ATAYIN yo'q edi — o'sha yerda qatorlar o'zgarmas.
    """
    return sa.Column(
        "updated_at",
        sa.DateTime(timezone=True),
        server_default=sa.text("now()"),
        nullable=False,
    )


def _regrant(signature: str) -> None:
    """`REVOKE PUBLIC` + `GRANT sbozor_app` — `0013`/`0015`/`0019`/`0021` naqshi.

    `DROP FUNCTION` grant'ni ham olib tashlaydi va `CREATE FUNCTION` dan
    keyin Postgres yangi funksiyaga `EXECUTE TO PUBLIC` ni STANDART beradi.
    Usiz funksiyaning «tor yuza» qarori jimgina bekor bo'lardi: u
    `SECURITY DEFINER` va endi O'TTIZ TO'RTTA jadvaldan `DELETE` qiladi.
    """
    op.execute(f"REVOKE ALL ON FUNCTION {signature} FROM PUBLIC")
    op.execute(f"GRANT EXECUTE ON FUNCTION {signature} TO {APP_ROLE}")


MARKET_DELETE_DRAFT_WITHOUT_NOTIFICATIONS = PGFunction(
    schema="public",
    signature=MARKET_DELETE_DRAFT.signature,
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

  DELETE FROM public.charge_evidence            WHERE market_id = p_market_id;
  DELETE FROM public.charge_adjustments         WHERE market_id = p_market_id;
  DELETE FROM public.payments                   WHERE market_id = p_market_id;
  DELETE FROM public.billing_anomalies          WHERE market_id = p_market_id;
  DELETE FROM public.daily_charges              WHERE market_id = p_market_id;
  DELETE FROM public.cashier_shifts             WHERE market_id = p_market_id;

  DELETE FROM public.stall_slot_occupancy      WHERE market_id = p_market_id;
  DELETE FROM public.zone_reviews              WHERE market_id = p_market_id;
  DELETE FROM public.review_assignments        WHERE market_id = p_market_id;
  DELETE FROM public.audit_rounds              WHERE market_id = p_market_id;
  DELETE FROM public.occupancy_events          WHERE market_id = p_market_id;
  DELETE FROM public.camera_zones              WHERE market_id = p_market_id;

  DELETE FROM public.snapshots                  WHERE market_id = p_market_id;
  DELETE FROM public.capture_runs               WHERE market_id = p_market_id;
  DELETE FROM public.snapshot_schedule_slots    WHERE market_id = p_market_id;
  DELETE FROM public.snapshot_schedules         WHERE market_id = p_market_id;
  DELETE FROM public.alert_events               WHERE market_id = p_market_id;

  DELETE FROM public.cameras                    WHERE market_id = p_market_id;
  DELETE FROM public.nvr_discovery_runs         WHERE market_id = p_market_id;
  DELETE FROM public.nvr_credentials            WHERE market_id = p_market_id;
  DELETE FROM public.nvr_devices                WHERE market_id = p_market_id;

  DELETE FROM public.stall_assignments          WHERE market_id = p_market_id;
  DELETE FROM public.stall_category_periods     WHERE market_id = p_market_id;
  DELETE FROM public.tariffs                    WHERE market_id = p_market_id;
  DELETE FROM public.stall_code_registry        WHERE market_id = p_market_id;
  DELETE FROM public.stalls                     WHERE market_id = p_market_id;
  DELETE FROM public.vendors                    WHERE market_id = p_market_id;
  DELETE FROM public.zones                      WHERE market_id = p_market_id;
  DELETE FROM public.stall_categories           WHERE market_id = p_market_id;
  DELETE FROM public.market_calendar_exceptions WHERE market_id = p_market_id;
  DELETE FROM public.market_profile             WHERE market_id = p_market_id;
  DELETE FROM public.user_market_roles          WHERE market_id = p_market_id;
  DELETE FROM public.refresh_tokens             WHERE market_id = p_market_id;
  DELETE FROM public.markets                    WHERE id = p_market_id;

  RETURN true;
END $$
""",
)
"""`0021`–`0023` davridagi `market_delete_draft()` — bildirishnoma jadvallarisiz.

BU YERDA, MIGRATSIYANING O'ZIDA MUZLATILGANI ATAYIN va sabab
`0021_market_delete_billing.py::MARKET_DELETE_DRAFT_WITHOUT_BILLING` bilan
AYNAN BIR XIL: `alembic_utils` `PGFunction` ni MODUL ta'rifidan oladi va
`migrations/entities/functions.py` endi YANGI (bildirishnoma jadvallari
bilan) tanani saqlaydi. `drop_entity()` faqat imzo bilan ishlaydi,
`create_entity()` esa TANANI yozadi — ya'ni bu nusxa bo'lmasa
`downgrade()` YANGI tanani qaytarardi va «`0022` ga qaytdim» degan da'vo
YOLG'ON bo'lardi.

Bundan tashqari bu yerda u ZARURAT: downgrade'dan keyin bildirishnoma
jadvallari shu migratsiyaning `downgrade()` i bilan o'chiriladi, ya'ni
ularga o'chirish qatori yozgan funksiya CHAQIRILGANDA `relation
"public.reconciliation_cases" does not exist` bilan yiqilardi (`plpgsql`
tanasi CREATE paytida tekshirilmaydi — xato faqat CHAQIRUVDA, ya'ni eng
yomon paytda chiqadi).
"""


def upgrade() -> None:
    """Upgrade schema."""
    # ------------------------------------------------------------------
    # 1. reconciliation_cases — nomuvofiqlik case'i (RECON-02, D-11/D-12).
    #
    #    BIRINCHI, chunki `reconciliation_case_events` unga kompozit FK
    #    bilan tayanadi (`NOTIFICATION_TENANT_TABLES` tartibi).
    #
    #    ⛔ IKKI MUSTAQIL, O'ZARO ISTISNO QILUVCHI KOMPOZIT FK (DQ-5) —
    #    fayl boshidagi 2-band. Nishon UNIQUE cheklovlari 6-fazadan
    #    ALLAQACHON MAVJUD, ya'ni bu yerda ular YARATILMAYDI.
    # ------------------------------------------------------------------
    op.create_table(
        "reconciliation_cases",
        _market_id(),
        _uuid_pk(),
        # YOPIQ diskriminator (`ReconciliationSubjectKind`) — `NULL`
        # tekshirish orqali sinfni aniqlash `GROUP BY` ni «qaysi ustun
        # bo'sh?» mantig'iga bog'lardi.
        sa.Column("subject_kind", sa.Text(), nullable=False),
        # ⛔ XOR: ikkalasidan AYNAN BITTASI to'ldiriladi.
        sa.Column("anomaly_id", pg.UUID(as_uuid=True), nullable=True),
        sa.Column("charge_id", pg.UUID(as_uuid=True), nullable=True),
        # DOMEN sanasi — nomuvofiqlik QAYSI KUN uchun aniqlandi.
        sa.Column("service_date", sa.Date(), nullable=False),
        sa.Column("status", sa.Text(), server_default=sa.text("'new'"), nullable=False),
        # ⛔ `users` GA FK YO'Q: `users` GLOBAL jadval va unga kompozit FK
        #   yozib bo'lmaydi; yagona ustunli FK esa begona bozor xodimini
        #   biriktirishni to'xtata olmasdi. Tekshiruv ilova qatlamida.
        sa.Column("assignee_user_id", pg.UUID(as_uuid=True), nullable=True),
        sa.Column("resolution_note", sa.Text(), nullable=True),
        _created_at(),
        _updated_at(),
        sa.PrimaryKeyConstraint("id", name="pk_reconciliation_cases"),
        sa.ForeignKeyConstraint(
            ["market_id"], ["markets.id"], name="fk_reconciliation_cases_market_id_markets"
        ),
        # ⛔ `ondelete` YO'Q (NO ACTION): case'i bor dalil qatorini
        #   o'chirish RAD ETILADI.
        sa.ForeignKeyConstraint(
            ["market_id", "anomaly_id"],
            ["billing_anomalies.market_id", "billing_anomalies.id"],
            name="fk_reconciliation_cases_anomaly",
        ),
        sa.ForeignKeyConstraint(
            ["market_id", "charge_id"],
            ["daily_charges.market_id", "daily_charges.id"],
            name="fk_reconciliation_cases_charge",
        ),
        # KOMPOZIT FK NISHONI: `reconciliation_case_events` `(market_id,
        # case_id)` ga havola qiladi.
        sa.UniqueConstraint("market_id", "id", name="uq_reconciliation_cases_market_id_id"),
        sa.CheckConstraint(CASE_STATUS_CHECK, name="status_allowed"),
        sa.CheckConstraint(SUBJECT_KIND_CHECK, name="subject_kind_allowed"),
        # ⚠⚠ DQ-5 NING IKKI STRUKTURA SHARTI.
        sa.CheckConstraint(SUBJECT_IS_EXCLUSIVE_CHECK, name="subject_is_exclusive"),
        sa.CheckConstraint(SUBJECT_KIND_MATCHES_TARGET_CHECK, name="subject_kind_matches_target"),
        # V5 kirish validatsiyasi — cheklanmagan `text` bitta so'rov bilan
        # megabaytlab matn qabul qilardi.
        sa.CheckConstraint(RESOLUTION_NOTE_LENGTH_CHECK, name="resolution_note_length"),
    )

    # ------------------------------------------------------------------
    # 2. reconciliation_case_events — holat o'zgarishi TARIXI (D-14).
    #
    #    O'zgarish YANGI QATOR, mavjud qator TAHRIRLANMAYDI
    #    (`charge_adjustments` naqshi). Jadval SHARTSIZ o'zgarmas —
    #    qo'riqchi pastda ulanadi.
    # ------------------------------------------------------------------
    op.create_table(
        "reconciliation_case_events",
        _market_id(),
        _uuid_pk(),
        sa.Column("case_id", pg.UUID(as_uuid=True), nullable=False),
        # `NULL` = case TUG'ILDI (oldingi holat yo'q).
        sa.Column("from_status", sa.Text(), nullable=True),
        sa.Column("to_status", sa.Text(), nullable=False),
        # ⛔ `NULL` = TIZIM (`0022` qarori bilan bir xil), «noma'lum» EMAS:
        #   case'ni `recon.open` cron tug'diradi va o'sha qatorga birorta
        #   odamning `user_id` sini yozish YOLG'ON bo'lardi.
        sa.Column("actor_user_id", pg.UUID(as_uuid=True), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        _created_at(),
        sa.PrimaryKeyConstraint("id", name="pk_reconciliation_case_events"),
        sa.ForeignKeyConstraint(
            ["market_id"],
            ["markets.id"],
            name="fk_reconciliation_case_events_market_id_markets",
        ),
        sa.ForeignKeyConstraint(
            ["market_id", "case_id"],
            ["reconciliation_cases.market_id", "reconciliation_cases.id"],
            name="fk_reconciliation_case_events_case",
        ),
        # ⛔ `ondelete` YO'Q — hodisasi bor foydalanuvchini o'chirish RAD
        #   ETILADI (`charge_adjustments.actor_user_id` bilan bir xil).
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["users.id"],
            name="fk_reconciliation_case_events_actor_user_id_users",
        ),
        sa.UniqueConstraint("market_id", "id", name="uq_reconciliation_case_events_market_id_id"),
        # ⚠ `from_status` NULLABLE, ya'ni `CHECK` uni MAJBURLAMAYDI:
        #   `NULL IN (...)` `NULL` beradi va `CHECK` `NULL` ni O'TKAZADI.
        #   Ochiq `IS NULL OR` shakli NIYATNI ko'rsatadi.
        sa.CheckConstraint(EVENT_FROM_STATUS_CHECK, name="from_status_allowed"),
        sa.CheckConstraint(EVENT_TO_STATUS_CHECK, name="to_status_allowed"),
        sa.CheckConstraint(EVENT_STATUS_TRANSITION_CHECK, name="status_actually_changed"),
    )

    # ------------------------------------------------------------------
    # 3. notification_outbox — chiquvchi xabar navbati (BOT-04, D-20/D-21).
    #
    #    ⛔⛔ KADR / OBYEKT KALITI / MANZIL / TAYYOR MATN / `chat_id`
    #    USTUNLARI UMUMAN YO'Q (G7-2, D-03/D-26c). Sabablar
    #    `models/notification.py::NotificationOutbox` docstringida
    #    NOMMA-NOM. Yo'qlik `07-04` da `information_schema` TO'PLAM
    #    TENGLIGI bilan o'lchanadi.
    # ------------------------------------------------------------------
    op.create_table(
        "notification_outbox",
        _market_id(),
        _uuid_pk(),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("recipient_kind", sa.Text(), nullable=False),
        # `NULL` = direktor xabari (`recipient_matches_vendor` MAJBURLAYDI).
        sa.Column("vendor_id", pg.UUID(as_uuid=True), nullable=True),
        # ⛔ D-21 NING KALITI — shakli `"<kind>:<manba-id>"`.
        sa.Column("dedupe_key", sa.Text(), nullable=False),
        # ⛔ ALLOWLIST bilan cheklangan kalitlar; tayyor MATN bu yerda EMAS.
        sa.Column("payload", pg.JSONB(), nullable=False),
        sa.Column("status", sa.Text(), server_default=sa.text("'pending'"), nullable=False),
        sa.Column("attempt_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column(
            "next_attempt_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        # IJARA (`FOR UPDATE SKIP LOCKED` bilan birga): tik ikki nusxada
        # yugurganda bir xabar IKKI MARTA jo'natilmasin.
        sa.Column("lease_until", sa.DateTime(timezone=True), nullable=True),
        # ⚠ `BIGINT` — Telegram ID lari 32-bitdan ALLAQACHON oshib ketgan.
        sa.Column("provider_message_id", sa.BigInteger(), nullable=True),
        # ⛔ FAQAT `type(exc).__name__` (D-04): Telegram URL'i bot tokenini
        #   TASHIYDI, ya'ni `str(exc)` uni bazaga va zaxiraga chiqarardi.
        sa.Column("last_error_type", sa.Text(), nullable=True),
        sa.Column("last_status_code", sa.Integer(), nullable=True),
        _created_at(),
        _updated_at(),
        sa.PrimaryKeyConstraint("id", name="pk_notification_outbox"),
        sa.ForeignKeyConstraint(
            ["market_id"], ["markets.id"], name="fk_notification_outbox_market_id_markets"
        ),
        sa.ForeignKeyConstraint(
            ["market_id", "vendor_id"],
            ["vendors.market_id", "vendors.id"],
            name="fk_notification_outbox_vendor",
        ),
        # ⚠⚠ D-21 NING BUTUN MEXANIZMI — bir niyat, bir qator.
        sa.UniqueConstraint(
            "market_id", "dedupe_key", name="uq_notification_outbox_market_id_dedupe_key"
        ),
        sa.UniqueConstraint("market_id", "id", name="uq_notification_outbox_market_id_id"),
        sa.CheckConstraint(OUTBOX_KIND_CHECK, name="kind_allowed"),
        sa.CheckConstraint(OUTBOX_RECIPIENT_KIND_CHECK, name="recipient_kind_allowed"),
        sa.CheckConstraint(OUTBOX_STATUS_CHECK, name="status_allowed"),
        sa.CheckConstraint(RECIPIENT_MATCHES_VENDOR_CHECK, name="recipient_matches_vendor"),
        sa.CheckConstraint("attempt_count >= 0", name="attempt_count_non_negative"),
        sa.CheckConstraint("jsonb_typeof(payload) = 'object'", name="payload_is_object"),
    )

    # ------------------------------------------------------------------
    # 4. vendor_telegram_bindings — sotuvchi <-> Telegram TARIXI (D-27).
    #
    #    ⚠ BOZORLAR ARO bir `telegram_user_id` bir necha bog'lanishga ega
    #    bo'lishi RUXSAT: sotuvchi ikki bozorda savdo qilishi mumkin va u
    #    ikkalasida ham o'z qarzini ko'rishi kerak. Ikkala qisman UNIQUE
    #    indeks ham `market_id` bilan BOSHLANADI, ya'ni to'qnashuv faqat
    #    bozor ICHIDA tekshiriladi.
    # ------------------------------------------------------------------
    op.create_table(
        "vendor_telegram_bindings",
        _market_id(),
        _uuid_pk(),
        sa.Column("vendor_id", pg.UUID(as_uuid=True), nullable=False),
        # ⚠ `BIGINT`, `INTEGER` EMAS.
        sa.Column("telegram_user_id", sa.BigInteger(), nullable=False),
        # `NULL` = bog'lanish FAOL (qisman indekslarning predikati).
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_reason", sa.Text(), nullable=True),
        _created_at(),
        sa.PrimaryKeyConstraint("id", name="pk_vendor_telegram_bindings"),
        sa.ForeignKeyConstraint(
            ["market_id"],
            ["markets.id"],
            name="fk_vendor_telegram_bindings_market_id_markets",
        ),
        sa.ForeignKeyConstraint(
            ["market_id", "vendor_id"],
            ["vendors.market_id", "vendors.id"],
            name="fk_vendor_telegram_bindings_vendor",
        ),
        sa.UniqueConstraint("market_id", "id", name="uq_vendor_telegram_bindings_market_id_id"),
        sa.CheckConstraint(
            "(revoked_at IS NOT NULL) = (revoked_reason IS NOT NULL)",
            name="revocation_is_paired",
        ),
    )

    # ------------------------------------------------------------------
    # 5. market_notification_settings — BOZOR KESIMIDAGI sozlama (D-19).
    #
    #    ⚠ `market_id` BIRLAMCHI KALIT (1:1), ya'ni `id uuid` ustuni YO'Q
    #    (`nvr_credentials` / `stall_code_registry` naqshi). Aynan shu
    #    sababdan jadval `NOTIFICATION_AUDITED_TABLES` ga QO'SHILMAYDI:
    #    `fn_audit_row()` `row_id` ni `uuid` ga keltiradi va bunday
    #    jadvalda har DML da yiqilardi.
    #
    #    ⚠ QATOR MAJBURIY EMAS: yo'q bo'lsa o'quvchilar `COALESCE` bilan
    #    kod standartlariga tushadi. Standartlar `server_default` da ham
    #    yoziladi, ya'ni qator YARATILGANDA ular O'ZI qo'llanadi.
    # ------------------------------------------------------------------
    op.create_table(
        "market_notification_settings",
        _market_id(),
        # [ASSUMED] A2 — sotuvchilar ERTA boshlaydi (birinchi slot 06:00),
        # ya'ni eslatma savdo boshlanishidan OLDIN kelmasligi kerak.
        sa.Column(
            "quiet_hours_start", sa.Time(), server_default=sa.text("'21:00'"), nullable=False
        ),
        sa.Column("quiet_hours_end", sa.Time(), server_default=sa.text("'08:00'"), nullable=False),
        # [ASSUMED] A3 — kichikroq qiymat case navbatini SHOVQINGA
        # aylantirardi. ⛔ BOT-03 va `recon.open` uchun AYNAN BIR knob.
        sa.Column("overdue_days", sa.Integer(), server_default=sa.text("3"), nullable=False),
        # ⚠ `BIGINT`; `NULL` = direktor hali botga ulanmagan.
        sa.Column("director_chat_id", sa.BigInteger(), nullable=True),
        _created_at(),
        _updated_at(),
        sa.PrimaryKeyConstraint("market_id", name="pk_market_notification_settings"),
        sa.ForeignKeyConstraint(
            ["market_id"],
            ["markets.id"],
            name="fk_market_notification_settings_market_id_markets",
        ),
        sa.CheckConstraint("overdue_days > 0", name="overdue_days_positive"),
        # Yuqori chegara ham MA'NOLI: undan kattasi eslatmani AMALDA
        # o'chirardi va «sozladim» degan direktor nazoratni jimgina
        # yo'qotardi.
        sa.CheckConstraint("overdue_days <= 90", name="overdue_days_bounded"),
    )

    # ------------------------------------------------------------------
    # 6. INDEKSLAR — nomlar va predikatlar MODELDAN import qilinadi (fayl
    #    boshidagi ogohlantirish, OP-10).
    #
    #    QISMAN indeks `op.create_table` GA SIG'MAYDI (`postgresql_where`
    #    faqat `create_index` da bor).
    #
    #    HAMMASI `market_id` BILAN BOSHLANADI -> `INDEX_EXCEPTIONS` ga
    #    hech nima qo'shilmaydi.
    # ------------------------------------------------------------------
    #
    # ⚠⚠ D-21 NAQSHI — BIR ANOMALIYAGA/HISOBGA BITTA CASE. Poyga DB'GA
    #   topshiriladi: `recon.open` KONVERGENT va ilova qatlamidagi «avval
    #   tekshir, keyin yoz» ikki parallel yugurishda ikkita case yozardi.
    op.create_index(
        CASE_SUBJECT_ANOMALY_INDEX,
        "reconciliation_cases",
        ["market_id", "anomaly_id"],
        unique=True,
        postgresql_where=sa.text(CASE_SUBJECT_ANOMALY_PREDICATE),
    )
    op.create_index(
        CASE_SUBJECT_CHARGE_INDEX,
        "reconciliation_cases",
        ["market_id", "charge_id"],
        unique=True,
        postgresql_where=sa.text(CASE_SUBJECT_CHARGE_PREDICATE),
    )
    op.create_index(
        CASE_WORKLIST_INDEX, "reconciliation_cases", ["market_id", "status", "service_date"]
    )
    # Keyset sahifalash (DQ-4): `offset` ISHLATILMAYDI — case ro'yxati kun
    # davomida o'sadi va offset takroriy/tushib qolgan qatorlar berardi.
    op.create_index(
        CASE_KEYSET_INDEX,
        "reconciliation_cases",
        ["market_id", sa.text("created_at DESC"), sa.text("id DESC")],
    )
    op.create_index(
        "ix_reconciliation_case_events_market_case",
        "reconciliation_case_events",
        ["market_id", "case_id"],
    )
    # Jo'natuvchi tikning YAGONA so'rov yo'li. QISMAN — `delivered`
    # qatorlar hech qachon o'chirilmaydi (D-20) va bir yildan keyin ular
    # jadvalning ~99 % ini tashkil qiladi.
    op.create_index(
        OUTBOX_DUE_INDEX,
        "notification_outbox",
        ["market_id", "next_attempt_at"],
        postgresql_where=sa.text(OUTBOX_DUE_PREDICATE),
    )
    # ⚠⚠ D-26c — BIR SOTUVCHIDA/AKKAUNTDA BIR FAOL BOG'LANISH. QISMAN
    #   bo'lishi MAJBURIY: to'liq UNIQUE qayta ulanishni BUTUNLAY imkonsiz
    #   qilardi va sotuvchi telefonini yangi akkauntga ko'chira olmasdi.
    op.create_index(
        BINDING_VENDOR_ACTIVE_INDEX,
        "vendor_telegram_bindings",
        ["market_id", "vendor_id"],
        unique=True,
        postgresql_where=sa.text(BINDING_ACTIVE_PREDICATE),
    )
    op.create_index(
        BINDING_TELEGRAM_ACTIVE_INDEX,
        "vendor_telegram_bindings",
        ["market_id", "telegram_user_id"],
        unique=True,
        postgresql_where=sa.text(BINDING_ACTIVE_PREDICATE),
    )

    # ------------------------------------------------------------------
    # 7. RLS. TARTIB MAJBURIY: ENABLE + FORCE + GRANT -> policy (Pitfall 10).
    #    `alembic-utils` `ENABLE`/`FORCE` ni BILMAYDI — ularsiz policy HECH
    #    QANDAY ta'sir ko'rsatmaydi va jadval hamma uchun ochiq bo'ladi.
    # ------------------------------------------------------------------
    for table in NOTIFICATION_TENANT_TABLES:
        enable_tenant_rls(table)
        create_entity(tenant_policy(table))
        create_entity(owner_bootstrap_policy(table))

    # ------------------------------------------------------------------
    # 8. Audit — ATAYIN BOSHQA RO'YXAT USTIDAN.
    #
    #    `NOTIFICATION_AUDITED_TABLES` = (`reconciliation_cases`,).
    #    Qolgan to'rttasi o'zgarmas jadval, tarix jadvali, texnik navbat
    #    yoki `id` ustunisiz sozlama — sabablar
    #    `schema_contract.AUDITED_TABLES` docstringida NOMMA-NOM.
    #
    #    ⚠ NOM `schema_contract.AUDITED_TABLES` GA SHU MIGRATSIYA BILAN
    #      BIR COMMITDA qo'shildi (`06-04` OP-4 naqshi), ya'ni
    #      `PENDING_AUDIT_TRIGGERS` BO'SH qoladi va
    #      `test_audited_tables_have_trigger` UZLUKSIZ yashil turadi.
    # ------------------------------------------------------------------
    for table in NOTIFICATION_AUDITED_TABLES:
        attach_audit_trigger(table)

    # ------------------------------------------------------------------
    # 9. O'ZGARMASLIK QO'RIQCHISI (D-14/D-20, T-07-09).
    #
    #    ⚠ TARTIB: funksiya AVVAL yaratiladi, trigger KEYIN ulanadi —
    #    `CREATE TRIGGER ... EXECUTE FUNCTION` mavjud funksiyani talab
    #    qiladi.
    # ------------------------------------------------------------------
    create_entity(CASE_EVENT_IMMUTABLE)
    for table, function_name, trigger_name in IMMUTABILITY_TRIGGERS:
        attach_immutability_trigger(table, function_name, trigger_name)

    # ------------------------------------------------------------------
    # 10. KASKAD KENGAYTMASI (`0021` naqshi).
    #
    #     ⛔ YANGI `SECURITY DEFINER` FUNKSIYA QO'SHILMAYDI (T-06-22/G7-7):
    #     mavjud funksiyaning faqat TANASI kengayadi, IMZOSI o'zgarmaydi.
    #     `DEFINER_SURFACES` BO'SH qoladi.
    #
    #     ⚠ BLOK BILLING BLOKIDAN OLDIN TURADI va bu O'LCHANGAN
    #     (`NOTIFICATION_DELETE_ORDER` docstringi): `reconciliation_cases`
    #     `billing_anomalies` va `daily_charges` ga tayanadi.
    # ------------------------------------------------------------------
    drop_entity(MARKET_DELETE_DRAFT_WITHOUT_NOTIFICATIONS)
    create_entity(MARKET_DELETE_DRAFT)
    _regrant(MARKET_DELETE_DRAFT_SIGNATURE)


def downgrade() -> None:
    """Downgrade schema."""
    # KASKAD AVVAL QAYTARILADI: jadvallar o'chirilgandan keyin funksiya
    # tanasi mavjud bo'lmagan jadvalga havola qilib qolardi va CHAQIRUVDA
    # yiqilardi (`plpgsql` tanasi CREATE paytida tekshirilmaydi).
    drop_entity(MARKET_DELETE_DRAFT)
    create_entity(MARKET_DELETE_DRAFT_WITHOUT_NOTIFICATIONS)
    _regrant(MARKET_DELETE_DRAFT_SIGNATURE)

    # TARTIB TESKARI: trigger AVVAL yechiladi, funksiya KEYIN o'chiriladi —
    # `DROP FUNCTION` unga tayanuvchi trigger mavjud bo'lganda yiqiladi.
    for table, _function_name, trigger_name in reversed(IMMUTABILITY_TRIGGERS):
        detach_immutability_trigger(table, trigger_name)
    drop_entity(CASE_EVENT_IMMUTABLE)

    for table in reversed(NOTIFICATION_AUDITED_TABLES):
        detach_audit_trigger(table)

    for table in reversed(NOTIFICATION_TENANT_TABLES):
        drop_entity(owner_bootstrap_policy(table))
        drop_entity(tenant_policy(table))

    op.drop_index(BINDING_TELEGRAM_ACTIVE_INDEX, table_name="vendor_telegram_bindings")
    op.drop_index(BINDING_VENDOR_ACTIVE_INDEX, table_name="vendor_telegram_bindings")
    op.drop_index(OUTBOX_DUE_INDEX, table_name="notification_outbox")
    op.drop_index(
        "ix_reconciliation_case_events_market_case", table_name="reconciliation_case_events"
    )
    op.drop_index(CASE_KEYSET_INDEX, table_name="reconciliation_cases")
    op.drop_index(CASE_WORKLIST_INDEX, table_name="reconciliation_cases")
    op.drop_index(CASE_SUBJECT_CHARGE_INDEX, table_name="reconciliation_cases")
    op.drop_index(CASE_SUBJECT_ANOMALY_INDEX, table_name="reconciliation_cases")

    # TARTIB — `NOTIFICATION_DELETE_ORDER` bo'yicha, ya'ni FK zanjirida
    # BOLALARDAN ota-onaga. Ro'yxat `reversed(NOTIFICATION_TENANT_TABLES)`
    # dan HOSIL QILINMAYDI va sabab reyestrning o'z docstringida.
    for table in NOTIFICATION_DELETE_ORDER:
        op.drop_table(table)
