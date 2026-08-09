"""occupancy_domain: kamera zonalari, AI hodisalari, ko'r audit, nazoratchi javobi

Revision ID: 0018
Revises: 0017
Create Date: 2026-08-09

5-FAZANING BIRINCHI MIGRATSIYASI. Oltita yangi tenant jadvalini olib keladi
va shu bilan `tests/integration/test_market_delete_guard.py::
test_cascade_covers_every_table_referencing_markets` ni ATAYIN QIZARTIRADI —
kaskadni kengaytirish `0019_market_delete_occupancy` da, AYNAN SHU REJANING
oynasida bajariladi (`0012`->`0013` va `0014`->`0015` juftliklarining
UCHINCHI takrori, W0-6).

=============================================================================
BU MIGRATSIYADA QOTIB QOLADIGAN YETTI QAROR:

1. NOM `camera_zones`, `zones` EMAS (D-06). `zones` 2-fazada bozor
   HUDUDLARI uchun band (`models/market.py::Zone`) va unga
   `stalls.zone_id NOT NULL` tayanadi. `zones` deb nomlash bu migratsiyani
   "jadval allaqachon mavjud" bilan yiqitardi — yoki, bundan ham yomoni,
   mavjud jadvalga IKKINCHI tenant policy'sini qo'yardi. Router ham
   `camera_zones.py`, frontend papkasi ham `camera-zones/`.

2. `occupancy_events` AUDIT TRIGGERIDAN CHIQARILGAN. Ikki mustaqil sabab
   va ikkalasi ham 4-fazadagidan KUCHLIROQ:
     (a) HAJM: 175 kadr/kun/bozor x ~30 zona ~ 5 000 qator/kun/bozor —
         4-fazadagi ~525 audit qatorining O'N BAROBARI. `audit_log`
         append-only, ya'ni u hech qachon kichraymaydi;
     (b) jadval 3-band bo'yicha o'zgarmas — audit faqat `INSERT` ni
         ko'rardi va bu o'sha ma'lumotning IKKINCHI NUSXASI bo'lardi.
   `audit_rounds` va `review_assignments` ham chiqarilgan (hodisa
   jurnallari). `camera_zones` va `zone_reviews` esa AUDITDA: birinchisida
   poligonni jimgina siljitish dalilni yo'q qiladi, ikkinchisi esa
   INSONNING moliyaviy oqibatli qarori (`tariffs` bilan bir oilada).

3. O'ZGARMASLIK — VAQT SHARTISIZ (D-12/D-17.4). `occupancy_events` va
   `zone_reviews` ga `BEFORE UPDATE OR DELETE` qo'riqchilari ulanadi va
   ular `tariff_past_immutable()` ning `valid_from <= bugun` SHARTINI
   OLMAYDI: o'sha shart «bugungi» javobni ochiq qoldirardi, holbuki aynan
   bugungi javob o'lchov natijasini belgilaydi.
   ⚠ QORALAMA-BOZOR ISTISNOSI FAQAT `DELETE` GA saqlanadi va u O'LCHANGAN
   ZARURAT: usiz `0019` ning kaskadi har qoralama uchun `RAISE EXCEPTION`
   bilan yiqilardi. `UPDATE` esa HAR DOIM rad etiladi — ya'ni istisno
   yuzasi `tariffs` nikidan IKKI BAROBAR TOR. Rad etilgan uch muqobil
   (`session_replication_role`, `DISABLE TRIGGER`, `current_user` sharti)
   `migrations/entities/triggers.py` ning 0018 blokida sanab chiqilgan.

4. BILLING LANGARI (D-21) — UCH SATR 4-FAZADAN AYNAN KO'CHIRILDI:

       snapshot_is_billable boolean NOT NULL DEFAULT true
       CHECK  (snapshot_is_billable)
       FOREIGN KEY (snapshot_id, snapshot_is_billable)
           REFERENCES snapshots (id, is_billable)

   Nishon — `uq_snapshots_billable_anchor` (`0014`, D-16). `snapshots.
   is_billable` `GENERATED ALWAYS AS (quality_verdict = 'ok') STORED`,
   ya'ni yaroqsiz kadr uchun kerak bo'lgan `(id, true)` juftligi JADVALDA
   UMUMAN MAVJUD BO'LMAYDI. `CHECK` juftlikning IKKINCHI YARMI: usiz FK
   `(id, false)` juftligiga havolani ham qabul qilardi. Langar 4-fazada
   HAQIQIY `postgres:18.4` da o'lchangan
   (`tests/fixtures/billable_probe.py`, `BILLABLE_ANCHOR_SUPPORTED = true`)
   va 5-faza uni FAQAT ISHLATADI, qayta o'lchamaydi.

5. QAYTA ISHLASH — YANGI QATOR:
   `UNIQUE (market_id, snapshot_id, camera_zone_id, model_version)`.
   Ikkinchi model (§E.15 dagi `timm` krop-klassifikatori) o'sha kadr va
   o'sha zona uchun RAQOBATLASHUVCHI verdikt yozadi, eskisini
   O'CHIRMAYDI — «yaxshilanishni o'lchash mashinasi» ning butun mexanizmi
   shu. `model_version` kalitga KIRADI, aynan shuning uchun.

6. KO'R AUDIT `CHECK` (D-17.3):
   `CHECK (queue_kind <> 'blind_audit' OR shown_ai_verdict = false)`.
   U «ko'r audit, lekin AI javobi ko'rsatilgan» qatorini IFODALAB
   BO'LMAYDIGAN qiladi. `zone_reviews.queue_kind` DENORMALIZATSIYA
   (`CHECK` boshqa jadvalni o'qiy olmaydi), shuning uchun u
   `review_assignments (id, queue_kind)` langariga KOMPOZIT FK bilan
   qadalgan — 4-banddagi langar naqshining aynan takrori. Usiz nusxani
   yolg'on yozib (`'uncertain'`) `CHECK` ni chetlab o'tish mumkin bo'lardi.

7. YANGI KENGAYTMA TALAB QILINMAYDI — VA BU O'LCHANGAN, TAXMIN EMAS.
   `05-01` ning W0-3 zondi HAQIQIY bazada to'rt faktni o'lchadi:
   `AUDIT_SEED_SHA256_SUPPORTED = true` (yadro `sha256(bytea)` kengaytmasiz
   ishlaydi) va `PGCRYPTO_ABSENT = true` (`pgcrypto` bazada YO'Q; faqat
   `plpgsql` va `btree_gist` o'rnatilgan). Ya'ni ko'r audit namunasining
   tartibi `digest()` SIZ hosil qilinadi va bu migratsiyada kengaytma
   darvozasi (`0014:209` dagi shakl) CHAQIRILMAYDI. O'lchov
   `tests/fixtures/audit_seed_probe.py` va
   `tests/tenancy/test_audit_seed_probe.py` da; `ops/db/init/00-extensions.sql`
   ATAYIN o'zgarmadi.
=============================================================================

⚠ IKKI YANGI `SECURITY DEFINER` FUNKSIYA (`audit_draw_due_markets()` va
`occupancy_day_close_markets()`) SHU MIGRATSIYADA yaratiladi. Ikkalasi ham
`LANGUAGE sql` va bu XAVFSIZ, chunki tanalari SHU MIGRATSIYA yaratgan
jadvallarga havola qiladi va funksiyalar jadvallardan KEYIN yaratiladi.
`LANGUAGE sql` tanasi `CREATE FUNCTION` PAYTIDA parse qilinadi
(`check_function_bodies` standart `on`) — kelajakdagi jadvalga havola
qilingan `sql` tanasi butun zanjirni yiqitardi (04-03/T3 da O'LCHANGAN).

⚠ `_regrant()` IKKALASI UCHUN HAM MAJBURIY: `CREATE FUNCTION` dan keyin
Postgres yangi funksiyaga `EXECUTE TO PUBLIC` ni STANDART beradi, ya'ni
RLS'ni chetlab o'tadigan funksiyani bazadagi HAR QANDAY rol chaqira olardi
(`0010`/`0011`/`0013`/`0015` dagi bilan aynan bir xil naqsh).

⚠ `CHECK` NOMLARI QISQA YOZILADI (`ck_` prefiksisiz) VA BU `0014` DAN
ATAYIN FARQ QILADI. Sabab SQLAlchemy ning nom konvensiyasida va u
O'LCHANDI: `ck` kaliti (`ck_%(table_name)s_%(constraint_name)s`) ichida
`%(constraint_name)s` TOKENI bor, ya'ni konvensiya ALLAQACHON NOMLANGAN
`CHECK` ga ham qo'llanadi. `0014` uslubida to'liq nom yozilsa natija
IKKI KARRA prefiks bo'lardi va uzunlari xesh bilan KESILARDI:

    ck_occupancy_events_ck_occupancy_events_confidence_in_u_f713

Qolgan uch kalit (`uq`, `fk`, `ix`) da bu token YO'Q, ya'ni ularning
to'liq nomlari o'zgarishsiz o'tadi — shuning uchun ular BU FAYLDA ham
to'liq yoziladi. Natijada bazadagi `CHECK` nomlari MODELDAGI nomlar bilan
AYNAN mos keladi va meta-testlar ularni bitta manbadan qidiradi.

⚠ `zone_reviews` DA IKKALA TRIGGER HAM BO'LADI (audit + o'zgarmaslik) va
Postgres ning tartib qoidasi aynan kerakli natijani beradi: bir vaqtda
ishlaydigan triggerlar ALIFBO tartibida chaqiriladi, `BEFORE` esa `AFTER`
dan OLDIN yuradi. Ya'ni qo'riqchi rad etgan `UPDATE` `audit_log` ga qator
QOLDIRMAYDI — rad etilgan urinish "o'zgardi" deb yozilmasin.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

import sqlalchemy as sa
from alembic import op
from sbozor_core.models.occupancy import (
    BLIND_AUDIT_NEEDS_ROUND_CHECK,
    BLIND_AUDIT_NOT_SHOWN_CHECK,
    CAMERA_ZONE_ACTIVE_INDEX,
    CAMERA_ZONE_ACTIVE_PREDICATE,
    EVAL_NEEDS_BLIND_AUDIT_CHECK,
    HUMAN_VERDICT_CHECK,
    NO_COVERAGE_IS_PAIRED_CHECK,
    OCCUPANCY_UNCERTAIN_INDEX,
    OCCUPANCY_UNCERTAIN_PREDICATE,
    OCCUPANCY_VERDICT_CHECK,
    POLYGON_IS_ARRAY_CHECK,
    POLYGON_MAX_VERTICES_CHECK,
    POLYGON_MIN_VERTICES_CHECK,
    RESOLUTION_SOURCE_CHECK,
    REVIEW_PURPOSE_CHECK,
    REVIEW_QUEUE_KIND_CHECK,
    SLOT_OCCUPIED_HAS_WINNER_CHECK,
    SLOT_VERDICT_CHECK,
)
from sqlalchemy.dialects import postgresql as pg

from migrations.entities import (
    OCCUPANCY_AUDITED_TABLES,
    OCCUPANCY_DELETE_ORDER,
    OCCUPANCY_TENANT_TABLES,
)
from migrations.entities.functions import (
    AUDIT_DRAW_DUE_MARKETS,
    OCCUPANCY_DAY_CLOSE_MARKETS,
    OCCUPANCY_GRANT_SIGNATURES,
)
from migrations.entities.policies import owner_bootstrap_policy, tenant_policy
from migrations.entities.triggers import OCCUPANCY_EVENT_IMMUTABLE, ZONE_REVIEW_IMMUTABLE
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
revision: str = "0018"
down_revision: str | Sequence[str] | None = "0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# ⚠ INDEKS NOMLARI, PREDIKATLARI VA `CHECK` IFODALARI SHU YERDA E'LON
#   QILINMAYDI — ular `sbozor_core.models.occupancy` dan IMPORT qilinadi
#   (yuqoriga qarang).
#
#   Sabab O'LCHANGAN (03-03, birinchi urinish): `op.create_index(...)`
#   yolg'iz o'zi yetarli emas. Autogenerate model metadata'sini baza bilan
#   solishtiradi, ya'ni modelda e'lon qilinmagan indeks "o'chirilgan" deb
#   ko'rinadi va `test_autogenerate_is_empty` `remove_index` bilan qizaradi.
#   Indeks IKKALA tomonda ham bo'lishi shart, nom va predikat esa BITTA
#   manbadan kelishi shart — aks holda ular jimgina ajralib ketardi.

IMMUTABILITY_TRIGGERS: tuple[tuple[str, str, str], ...] = (
    ("occupancy_events", "occupancy_event_immutable", "trg_occupancy_event_immutable"),
    ("zone_reviews", "zone_review_immutable", "trg_zone_review_immutable"),
)
"""`(jadval, funksiya, trigger)` uchliklari — `0008_temporal.py:76-82` naqshi.

Ro'yxat shu yerda, chunki `upgrade()` ham, `downgrade()` ham uning ustidan
tsikl qiladi va nomlar IKKI joyda yozilsa ular ajralib ketishi mumkin
bo'lardi: `downgrade()` boshqa nomni `DROP TRIGGER IF EXISTS` bilan
qidirardi va qo'riqchi JIMGINA joyida qolardi.
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
    return sa.Column(
        "updated_at",
        sa.DateTime(timezone=True),
        server_default=sa.text("now()"),
        nullable=False,
    )


def _regrant(signature: str) -> None:
    """`REVOKE PUBLIC` + `GRANT sbozor_app` — `0015` dagi naqsh.

    `CREATE FUNCTION` dan keyin Postgres yangi funksiyaga `EXECUTE TO
    PUBLIC` ni STANDART beradi. Usiz ikkala funksiyaning ham «tor yuza»
    qarori jimgina bekor bo'lardi: ikkalasi ham `SECURITY DEFINER` va
    RLS'ni chetlab o'tadi.
    """
    op.execute(f"REVOKE ALL ON FUNCTION {signature} FROM PUBLIC")
    op.execute(f"GRANT EXECUTE ON FUNCTION {signature} TO {APP_ROLE}")


def upgrade() -> None:
    """Upgrade schema."""
    # ------------------------------------------------------------------
    # 0. KENGAYTMA DARVOZASI ATAYIN YO'Q — fayl boshidagi 7-band.
    #
    #    `0014` `btree_gist` ni talab qilgan edi (`ExcludeConstraint`
    #    uchun), bu domenda esa `EXCLUDE` konstrayti YO'Q va ko'r audit
    #    namunasi yadro `sha256(bytea)` bilan tartiblanadi. `05-01` ning
    #    W0-3 zondi buni HAQIQIY bazada o'lchadi va `pgcrypto` ning
    #    YO'QLIGINI ham tasdiqladi.
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # 0b. `snapshots (market_id, id)` — YETISHMAYOTGAN KOMPOZIT FK NISHONI.
    #
    #     O'LCHANGAN, TAXMIN EMAS: usiz shu migratsiyaning o'zi
    #     `asyncpg.exceptions.InvalidForeignKeyError: there is no unique
    #     constraint matching given keys for referenced table "snapshots"`
    #     bilan yiqiladi.
    #
    #     SABAB: 4-fazada `snapshots` ZANJIRNING OXIRI edi — unga hech kim
    #     tayanmasdi, ya'ni `(market_id, id)` juftligi kerak emasdi.
    #     5-fazada `occupancy_events` unga IKKI XIL FK bilan tayanadi va
    #     ular IKKI XIL savolga javob beradi: tenant chegarasi
    #     (`(market_id, snapshot_id)`) va billing chegarasi
    #     (`(snapshot_id, snapshot_is_billable)`). Birinchisi ikkinchisidan
    #     KELIB CHIQMAYDI — billing langari `market_id` ni umuman ko'rmaydi
    #     va ko'rsa u FK NISHONI sifatida yaroqsiz bo'lardi (`test_meta.py::
    #     INDEX_EXCEPTIONS` dagi `uq_snapshots_billable_anchor` bandi).
    #
    #     Konstrayt `market_id` bilan BOSHLANADI, ya'ni `INDEX_EXCEPTIONS`
    #     ga qo'shish TALAB QILINMAYDI.
    # ------------------------------------------------------------------
    op.create_unique_constraint("uq_snapshots_market_id_id", "snapshots", ["market_id", "id"])

    # ------------------------------------------------------------------
    # 1. camera_zones — kamera kadridagi rasta konturi (AI-01, D-06/D-07).
    #
    #    IKKITA KOMPOZIT FK (`cameras` VA `stalls`): A bozorining kamerasi
    #    B bozorining rastasiga bog'lana OLMAYDI va bu RLS emas, SXEMA
    #    darajasidagi kafolat (T-05-20).
    #
    #    VERSIYALANGAN: tahrir `UPDATE` emas, YANGI QATOR. Eskisi
    #    `is_active = false` bo'ladi va JOYIDA QOLADI —
    #    `occupancy_events.zone_version` o'sha paytdagi konturga ishora
    #    qiladi. Poligonni joyida tahrirlash butun tarixni RETROAKTIV
    #    qayta talqin qilardi (T-05-26, `tariffs` bilan bir xil sinf).
    # ------------------------------------------------------------------
    op.create_table(
        "camera_zones",
        _market_id(),
        _uuid_pk(),
        sa.Column("camera_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("stall_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        # `[[x, y], ...]`, har biri 0..1. Diapazon va o'z-o'zi bilan
        # kesishish SERVERDA tekshiriladi (`validate_polygon`, 05-06) —
        # frontend tekshiruvi TAKROR, ishonch emas (T-05-27).
        sa.Column("polygon", pg.JSONB(), nullable=False),
        # Poligon QAYSI kadr o'lchamida chizilgani: kamera ruxsati
        # o'zgarsa nisbat farqi shu yerdan aniqlanadi.
        sa.Column("source_width", sa.Integer(), nullable=False),
        sa.Column("source_height", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        _created_at(),
        _updated_at(),
        sa.PrimaryKeyConstraint("id", name="pk_camera_zones"),
        sa.ForeignKeyConstraint(
            ["market_id"], ["markets.id"], name="fk_camera_zones_market_id_markets"
        ),
        sa.ForeignKeyConstraint(
            ["market_id", "camera_id"],
            ["cameras.market_id", "cameras.id"],
            name="fk_camera_zones_market_id_camera_id_cameras",
        ),
        sa.ForeignKeyConstraint(
            ["market_id", "stall_id"],
            ["stalls.market_id", "stalls.id"],
            name="fk_camera_zones_market_id_stall_id_stalls",
        ),
        sa.UniqueConstraint(
            "market_id",
            "camera_id",
            "stall_id",
            "version",
            name="uq_camera_zones_market_id_camera_id_stall_id_version",
        ),
        # KOMPOZIT FK NISHONI: `occupancy_events` `(market_id,
        # camera_zone_id)` ga havola qiladi.
        sa.UniqueConstraint("market_id", "id", name="uq_camera_zones_market_id_id"),
        # ⚠ UCHTA KONSTRAYT, VA TARTIB O'RNIGA `CASE` ISHLATILADI.
        #   PostgreSQL `CHECK` larni ANIQLANMAGAN tartibda baholaydi, ya'ni
        #   `{"a": 1}` yozilganda uzunlik ifodasi `polygon_is_array` dan
        #   OLDIN baholanishi va `22023 cannot get array length of a
        #   non-array` bilan yiqilishi mumkin edi — rad etish `23514` emas,
        #   boshqa sinf xato bo'lardi. Ifodalar modeldan import qilinadi va
        #   u yerda `CASE` bilan himoyalangan.
        sa.CheckConstraint(POLYGON_IS_ARRAY_CHECK, name="polygon_is_array"),
        sa.CheckConstraint(POLYGON_MIN_VERTICES_CHECK, name="polygon_min_vertices"),
        sa.CheckConstraint(POLYGON_MAX_VERTICES_CHECK, name="polygon_max_vertices"),
        sa.CheckConstraint("source_width > 0", name="source_width_positive"),
        sa.CheckConstraint("source_height > 0", name="source_height_positive"),
        sa.CheckConstraint("version > 0", name="version_positive"),
    )

    # ------------------------------------------------------------------
    # 2. occupancy_events — AI ning BITTA zona uchun javobi (AI-02).
    #
    #    ⚠⚠ FAYL BOSHIDAGI 4-BAND SHU YERDA MODDIYLASHADI. Uch satr
    #    4-fazadan aynan ko'chirilgan va ularning UCHALASI HAM kerak:
    #    ustun (`DEFAULT true`), `CHECK` va kompozit FK. `CHECK` unutilsa
    #    FK yolg'iz o'zi `(id, false)` juftligiga havolani ham QABUL
    #    QILARDI — u ham mavjud juftlik.
    #
    #    ⚠ `business_date` va `slot_time` `snapshots` DAN NUSXALANADI va
    #    `GENERATED` EMAS: ikki mustaqil hisoblash manbai yarim tunda bir
    #    kun farq qilardi (Pitfall 3) va dalil 6-fazada "yo'q" bo'lib
    #    qolardi. `snapshots.business_date` ning O'ZI generated — haqiqat
    #    manbai BITTA va u yuqoriroq qatlamda.
    # ------------------------------------------------------------------
    op.create_table(
        "occupancy_events",
        _market_id(),
        _uuid_pk(),
        sa.Column("snapshot_id", pg.UUID(as_uuid=True), nullable=False),
        # ⚠ LANGARNING IKKINCHI USTUNI. Qiymat HAR DOIM `true` (`CHECK`
        #   boshqasini rad etadi); `DEFAULT true` chaqiruvchini uni
        #   yozishdan ozod qiladi, ya'ni kafolat "eslab qolinadigan"
        #   narsaga aylanmaydi.
        sa.Column(
            "snapshot_is_billable",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column("camera_zone_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("business_date", sa.Date(), nullable=False),
        sa.Column("slot_time", sa.Time(timezone=False), nullable=False),
        sa.Column("verdict", sa.Text(), nullable=False),
        # O'LCHOVNING O'ZI SAQLANADI, faqat hukm emas: real kadrlar
        # kelganda chegaralar SQL bilan sozlanadi, qayta aniqlash bilan
        # emas.
        sa.Column("confidence", sa.Numeric(5, 4), nullable=False),
        sa.Column("model_version", sa.Text(), nullable=False),
        # ⚠ CHEGARALAR QATORDA (D-11) — `quality_thresholds_version`
        #   naqshi. Sozlash SQL bilan, migratsiya bilan EMAS.
        sa.Column("thresholds_version", sa.SmallInteger(), nullable=False),
        sa.Column("zone_version", sa.Integer(), nullable=False),
        _created_at(),
        sa.PrimaryKeyConstraint("id", name="pk_occupancy_events"),
        sa.ForeignKeyConstraint(
            ["market_id"], ["markets.id"], name="fk_occupancy_events_market_id_markets"
        ),
        sa.ForeignKeyConstraint(
            ["market_id", "snapshot_id"],
            ["snapshots.market_id", "snapshots.id"],
            name="fk_occupancy_events_market_id_snapshot_id_snapshots",
        ),
        # ⚠⚠ D-21 NING BUTUN KAFOLATI:
        #       FOREIGN KEY (snapshot_id, snapshot_is_billable)
        #           REFERENCES snapshots (id, is_billable)
        #   Nishon — `uq_snapshots_billable_anchor` (`0014`). NOM QO'LDA
        #   berilgan: konvensiya 63 baytdan uzun nom berardi va PostgreSQL
        #   uni JIMGINA kesib, `alembic check` ni har safar soxta diff
        #   bilan qizartirardi.
        sa.ForeignKeyConstraint(
            ["snapshot_id", "snapshot_is_billable"],
            ["snapshots.id", "snapshots.is_billable"],
            name="fk_occupancy_events_snapshot_billable",
        ),
        sa.ForeignKeyConstraint(
            ["market_id", "camera_zone_id"],
            ["camera_zones.market_id", "camera_zones.id"],
            name="fk_occupancy_events_market_id_camera_zone_id_camera_zones",
        ),
        # ⚠ FAYL BOSHIDAGI 5-BAND: `model_version` KALITGA KIRADI.
        sa.UniqueConstraint(
            "market_id",
            "snapshot_id",
            "camera_zone_id",
            "model_version",
            name="uq_occupancy_events_market_id_snapshot_zone_model",
        ),
        # KOMPOZIT FK NISHONI: `review_assignments` va
        # `stall_slot_occupancy` `(market_id, id)` ga havola qiladi.
        sa.UniqueConstraint("market_id", "id", name="uq_occupancy_events_market_id_id"),
        # ⚠⚠ JUFTLIKNING IKKINCHI YARMI — USIZ FK MA'NOSIZ.
        sa.CheckConstraint("snapshot_is_billable", name="snapshot_is_billable"),
        sa.CheckConstraint(OCCUPANCY_VERDICT_CHECK, name="verdict_allowed"),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="confidence_in_unit_range",
        ),
        sa.CheckConstraint("zone_version > 0", name="zone_version_positive"),
        sa.CheckConstraint("thresholds_version > 0", name="thresholds_version_positive"),
        sa.CheckConstraint("length(btrim(model_version)) > 0", name="model_version_not_blank"),
    )

    # ------------------------------------------------------------------
    # 3. audit_rounds — ko'r auditning BITTA tortish doirasi (D-13/D-17.1).
    #
    #    Uch fakt MUZLATILADI va ularsiz «xolis namuna» da'vosini keyin
    #    tekshirib bo'lmasdi: `frame_size` (tortish paytida nechta nomzod
    #    bor edi), `frame_predicate_hash` (nomzodlar QAYSI shart bilan
    #    tanlandi) va `drawn_at`.
    #
    #    ⚠ URUG' USTUN SIFATIDA SAQLANMAYDI — u
    #    `f(market_id, business_date, round_no)` dan HOSILA. Saqlangan
    #    urug' o'zgartirilishi mumkin bo'lardi; hosila urug'ni «qayta
    #    chizish» uchun kunni yoki bozorni o'zgartirish kerak bo'lardi.
    #    SQL yo'li kengaytmasiz ishlaydi (fayl boshidagi 7-band).
    # ------------------------------------------------------------------
    op.create_table(
        "audit_rounds",
        _market_id(),
        _uuid_pk(),
        sa.Column("business_date", sa.Date(), nullable=False),
        sa.Column("round_no", sa.SmallInteger(), server_default=sa.text("1"), nullable=False),
        sa.Column("frame_size", sa.Integer(), nullable=False),
        sa.Column("frame_predicate_hash", sa.Text(), nullable=False),
        sa.Column(
            "drawn_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_audit_rounds"),
        sa.ForeignKeyConstraint(
            ["market_id"], ["markets.id"], name="fk_audit_rounds_market_id_markets"
        ),
        sa.UniqueConstraint(
            "market_id",
            "business_date",
            "round_no",
            name="uq_audit_rounds_market_id_business_date_round_no",
        ),
        # KOMPOZIT FK NISHONI: `review_assignments` `(market_id,
        # audit_round_id)` ga havola qiladi.
        sa.UniqueConstraint("market_id", "id", name="uq_audit_rounds_market_id_id"),
        sa.CheckConstraint("round_no > 0", name="round_no_positive"),
        sa.CheckConstraint("frame_size >= 0", name="frame_size_non_negative"),
        sa.CheckConstraint(
            "length(btrim(frame_predicate_hash)) > 0",
            name="frame_predicate_hash_not_blank",
        ),
    )

    # ------------------------------------------------------------------
    # 4. review_assignments — nazoratchi navbatidagi BITTA yozuv.
    #
    #    ⚠ `UNIQUE (occupancy_event_id)` — «BITTA HODISA IKKI NAVBATDA
    #    BO'LA OLMAYDI» va poyga DB'GA TOPSHIRILADI (`nvr_repo.py:509-517`
    #    naqshi): ko'r audit tortish va noaniq navbat qurish IKKI ALOHIDA
    #    job va ular bir vaqtda ishlashi mumkin. «Tekshir-keyin-yoz»
    #    ikkalasiga ham bo'sh holatni ko'rsatardi.
    #
    #    ⚠ KONSTRAYT `market_id` BILAN BOSHLANMAYDI va bu ATAYIN — nomi
    #    `tests/tenancy/test_meta.py::INDEX_EXCEPTIONS` ga SABAB bilan
    #    qo'shilgan.
    # ------------------------------------------------------------------
    op.create_table(
        "review_assignments",
        _market_id(),
        _uuid_pk(),
        sa.Column("occupancy_event_id", pg.UUID(as_uuid=True), nullable=False),
        # `NULL` = noaniq navbat; ko'r audit uchun MAJBURIY.
        sa.Column("audit_round_id", pg.UUID(as_uuid=True), nullable=True),
        sa.Column("queue_kind", sa.Text(), nullable=False),
        # ⚠ TORTISH PAYTIDA to'ladi (D-14, 70/30). Standart `train`:
        #   noaniq navbat uchun to'g'ri javob va u xolis o'lchovga
        #   TASODIFAN kirib qolmaydi — `eval` ATAYIN qo'yiladi.
        sa.Column("purpose", sa.Text(), server_default=sa.text("'train'"), nullable=False),
        _created_at(),
        sa.PrimaryKeyConstraint("id", name="pk_review_assignments"),
        sa.ForeignKeyConstraint(
            ["market_id"], ["markets.id"], name="fk_review_assignments_market_id_markets"
        ),
        sa.ForeignKeyConstraint(
            ["market_id", "occupancy_event_id"],
            ["occupancy_events.market_id", "occupancy_events.id"],
            name="fk_review_assignments_occupancy_event",
        ),
        sa.ForeignKeyConstraint(
            ["market_id", "audit_round_id"],
            ["audit_rounds.market_id", "audit_rounds.id"],
            name="fk_review_assignments_audit_round",
        ),
        sa.UniqueConstraint("occupancy_event_id", name="uq_review_assignments_occupancy_event_id"),
        sa.UniqueConstraint("market_id", "id", name="uq_review_assignments_market_id_id"),
        # ⚠⚠ FAYL BOSHIDAGI 6-BANDNING IKKINCHI YARMI: `zone_reviews` ning
        #   `queue_kind` NUSXASI SHU LANGARGA qadaladi. Usiz D-17.3 ning
        #   `CHECK` i o'z nusxasiga ishonardi va nusxani yolg'on yozish uni
        #   chetlab o'tardi.
        sa.UniqueConstraint("id", "queue_kind", name="uq_review_assignments_queue_anchor"),
        sa.CheckConstraint(REVIEW_QUEUE_KIND_CHECK, name="queue_kind_allowed"),
        sa.CheckConstraint(REVIEW_PURPOSE_CHECK, name="purpose_allowed"),
        sa.CheckConstraint(BLIND_AUDIT_NEEDS_ROUND_CHECK, name="blind_audit_needs_round"),
        # D-14: XOLIS namuna FAQAT ko'r auditdan kelishi mumkin. Noaniq
        # navbat TANLANGAN (biased) namuna va uni aniqlik hisobotiga
        # qo'shish raqamni MODELNING UMUMIY ANIQLIGI bo'lmagan narsaga
        # aylantirardi.
        sa.CheckConstraint(EVAL_NEEDS_BLIND_AUDIT_CHECK, name="eval_needs_blind_audit"),
    )

    # ------------------------------------------------------------------
    # 5. zone_reviews — nazoratchining javobi (AI-03/AI-04, D-12/D-17.3).
    #
    #    ⚠⚠ FAYL BOSHIDAGI 6-BAND: `queue_kind` DENORMALIZATSIYA, LEKIN
    #    QADALGAN. `CHECK` boshqa jadvalni o'qiy olmaydi, shuning uchun
    #    ko'r audit sharti shu yerdagi nusxaga tayanadi — va nusxa
    #    `(review_assignment_id, queue_kind)` kompozit FK bilan
    #    `review_assignments (id, queue_kind)` ga qadalgan.
    #
    #    ⚠ `users` GA FK: mavjud bo'lmagan foydalanuvchiga ishora qiladigan
    #    javob DALIL EMAS. `ondelete` YO'Q (NO ACTION) — `CASCADE` bo'lganda
    #    bitta `DELETE FROM users` nazoratchining butun tarixini o'chirib
    #    yuborardi.
    # ------------------------------------------------------------------
    op.create_table(
        "zone_reviews",
        _market_id(),
        _uuid_pk(),
        sa.Column("review_assignment_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("queue_kind", sa.Text(), nullable=False),
        # ⚠ SERVER HISOBLAYDI, KLIENT YUBORMAYDI (05-10: `AnswerRequest` da
        #   bu maydon UMUMAN e'lon qilinmagan). DB `CHECK` — IKKINCHI
        #   qatlam (T-05-44).
        sa.Column("shown_ai_verdict", sa.Boolean(), nullable=False),
        sa.Column("human_verdict", sa.Text(), nullable=False),
        sa.Column("reviewer_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "decided_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        # FAQAT DIAGNOSTIKA (D-16 ishonchlilik o'lchovining kirishi).
        # `NULL` = klient o'lchamadi; kafolat unga TAYANMAYDI.
        sa.Column("decision_ms", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_zone_reviews"),
        sa.ForeignKeyConstraint(
            ["market_id"], ["markets.id"], name="fk_zone_reviews_market_id_markets"
        ),
        sa.ForeignKeyConstraint(
            ["market_id", "review_assignment_id"],
            ["review_assignments.market_id", "review_assignments.id"],
            name="fk_zone_reviews_review_assignment",
        ),
        sa.ForeignKeyConstraint(
            ["review_assignment_id", "queue_kind"],
            ["review_assignments.id", "review_assignments.queue_kind"],
            name="fk_zone_reviews_queue_kind_anchor",
        ),
        sa.ForeignKeyConstraint(
            ["reviewer_id"], ["users.id"], name="fk_zone_reviews_reviewer_id_users"
        ),
        # Bitta topshiriqqa BITTA javob. Ikkinchi javob o'zgarmaslik
        # triggerini `INSERT` orqali chetlab o'tish yo'li bo'lardi:
        # tahrirlash o'rniga ikkinchi qator yoziladi.
        sa.UniqueConstraint("review_assignment_id", name="uq_zone_reviews_review_assignment_id"),
        # ⚠⚠ D-17.3 — «KO'R, LEKIN KO'RSATILGAN» IFODALAB BO'LMAYDI.
        sa.CheckConstraint(BLIND_AUDIT_NOT_SHOWN_CHECK, name="blind_audit_not_shown"),
        sa.CheckConstraint(REVIEW_QUEUE_KIND_CHECK, name="queue_kind_allowed"),
        sa.CheckConstraint(HUMAN_VERDICT_CHECK, name="human_verdict_allowed"),
        sa.CheckConstraint(
            "decision_ms IS NULL OR decision_ms >= 0",
            name="decision_ms_non_negative",
        ),
    )

    # ------------------------------------------------------------------
    # 6. stall_slot_occupancy — RASTA darajasidagi hukm (AI-05/AI-06).
    #
    #    ⚠ KAFOLAT TRANZITIV VA YANGI MEXANIZM O'YLAB TOPILMAYDI:
    #        stall_slot_occupancy -> occupancy_events -> snapshots (id, is_billable)
    #    `CHECK ((verdict = 'occupied') = (winning_occupancy_event_id IS NOT
    #    NULL))` uni majburlaydi: «band» hukmi HAR DOIM aniq bir YAROQLI
    #    kadrga ishora qiladi.
    #
    #    ⚠ `no_coverage` — «BO'SH» EMAS (D-22) va farq IKKALA ustunda
    #    birdan yashaydi (`no_coverage_is_paired`). Uni `empty` ga
    #    aylantirish o'lchovning YO'QLIGINI yaxshi natijaga aylantirardi.
    # ------------------------------------------------------------------
    op.create_table(
        "stall_slot_occupancy",
        _market_id(),
        _uuid_pk(),
        sa.Column("stall_id", pg.UUID(as_uuid=True), nullable=False),
        # ⚠ `occupancy_events` DAN (u esa `snapshots` dan) NUSXALANADI.
        sa.Column("business_date", sa.Date(), nullable=False),
        sa.Column("slot_time", sa.Time(timezone=False), nullable=False),
        sa.Column("verdict", sa.Text(), nullable=False),
        sa.Column("resolution_source", sa.Text(), nullable=False),
        sa.Column("winning_occupancy_event_id", pg.UUID(as_uuid=True), nullable=True),
        _created_at(),
        sa.PrimaryKeyConstraint("id", name="pk_stall_slot_occupancy"),
        sa.ForeignKeyConstraint(
            ["market_id"], ["markets.id"], name="fk_stall_slot_occupancy_market_id_markets"
        ),
        sa.ForeignKeyConstraint(
            ["market_id", "stall_id"],
            ["stalls.market_id", "stalls.id"],
            name="fk_stall_slot_occupancy_stall",
        ),
        sa.ForeignKeyConstraint(
            ["market_id", "winning_occupancy_event_id"],
            ["occupancy_events.market_id", "occupancy_events.id"],
            name="fk_stall_slot_occupancy_winning_event",
        ),
        # IDEMPOTENTLIK KALITI: kunlik job `ON CONFLICT DO UPDATE` bilan
        # yozadi va o'tgan kunni qayta hisoblash natijani O'ZGARTIRMAYDI.
        sa.UniqueConstraint(
            "market_id",
            "stall_id",
            "business_date",
            "slot_time",
            # ⚠ NOM QISQARTIRILGAN: to'liq ustun ro'yxati 66 belgi berardi
            #   va PostgreSQL identifikatorni 63 baytga kesardi.
            name="uq_stall_slot_occupancy_market_stall_day_slot",
        ),
        sa.CheckConstraint(SLOT_VERDICT_CHECK, name="verdict_allowed"),
        sa.CheckConstraint(RESOLUTION_SOURCE_CHECK, name="resolution_source_allowed"),
        sa.CheckConstraint(
            SLOT_OCCUPIED_HAS_WINNER_CHECK,
            name="occupied_has_winning_event",
        ),
        sa.CheckConstraint(NO_COVERAGE_IS_PAIRED_CHECK, name="no_coverage_is_paired"),
    )

    # ------------------------------------------------------------------
    # 7. QISMAN INDEKSLAR — `op.create_table` GA SIG'MAYDI
    #    (`postgresql_where` faqat `create_index` da bor).
    #
    #    IKKALASI HAM `market_id` BILAN BOSHLANADI: ikkala so'rov ham HAR
    #    DOIM tenant konteksti ostida, bitta bozor uchun bajariladi.
    #    Predikatlar modeldan import qilinadi (fayl boshidagi ogohlantirish).
    # ------------------------------------------------------------------
    op.create_index(
        CAMERA_ZONE_ACTIVE_INDEX,
        "camera_zones",
        ["market_id", "camera_id"],
        postgresql_where=sa.text(CAMERA_ZONE_ACTIVE_PREDICATE),
    )
    op.create_index(
        OCCUPANCY_UNCERTAIN_INDEX,
        "occupancy_events",
        ["market_id", "business_date"],
        postgresql_where=sa.text(OCCUPANCY_UNCERTAIN_PREDICATE),
    )

    # ------------------------------------------------------------------
    # 8. RLS. TARTIB MAJBURIY: ENABLE + FORCE + GRANT -> policy (Pitfall 10).
    #    `alembic-utils` `ENABLE`/`FORCE` ni BILMAYDI — ularsiz policy HECH
    #    QANDAY ta'sir ko'rsatmaydi va jadval hamma uchun ochiq bo'ladi.
    #
    #    TSIKL `OCCUPANCY_TENANT_TABLES` USTIDAN — OLTALA jadval.
    # ------------------------------------------------------------------
    for table in OCCUPANCY_TENANT_TABLES:
        enable_tenant_rls(table)
        create_entity(tenant_policy(table))
        create_entity(owner_bootstrap_policy(table))

    # ------------------------------------------------------------------
    # 9. Audit — ATAYIN BOSHQA RO'YXAT USTIDAN (fayl boshidagi 2-band).
    #
    #    `OCCUPANCY_AUDITED_TABLES` = (`camera_zones`, `zone_reviews`).
    #    Qolgan to'rttasi hodisa jurnali yoki o'zgarmas jadval.
    #
    #    ⚠ IKKALA NOM `tests/tenancy/test_meta.py::PENDING_AUDIT_TRIGGERS`
    #      DAN SHU MIGRATSIYA BILAN BIR COMMITDA O'CHIRILDI. `05-01` ularni
    #      o'sha ro'yxatga qo'ygan edi (qarz ochiq); trigger endi ULANDI,
    #      ya'ni qarz YOPILDI va ro'yxat yana BO'SH. Buni unutish testni
    #      TESKARI yo'nalishdan qizartirardi (`closed` asserti) — reyestr
    #      IKKI TOMONLAMA.
    # ------------------------------------------------------------------
    for table in OCCUPANCY_AUDITED_TABLES:
        attach_audit_trigger(table)

    # ------------------------------------------------------------------
    # 10. O'ZGARMASLIK QO'RIQCHILARI (fayl boshidagi 3-band).
    #
    #     IKKI ALOHIDA FUNKSIYA, tanalari deyarli bir xil bo'lsa ham:
    #     xato xabari QAYSI qoida buzilganini aytishi kerak
    #     (`helpers.py::attach_immutability_trigger` docstringi).
    #
    #     ⚠ TARTIB: funksiya AVVAL yaratiladi, trigger KEYIN ulanadi —
    #     `CREATE TRIGGER ... EXECUTE FUNCTION` mavjud funksiyani talab
    #     qiladi.
    # ------------------------------------------------------------------
    create_entity(OCCUPANCY_EVENT_IMMUTABLE)
    create_entity(ZONE_REVIEW_IMMUTABLE)
    for table, function_name, trigger_name in IMMUTABILITY_TRIGGERS:
        attach_immutability_trigger(table, function_name, trigger_name)

    # ------------------------------------------------------------------
    # 11. IKKI TIK YUZASI — `SECURITY DEFINER`, FAQAT IDENTIFIKATOR VA
    #     SANOQ (§S-5, T-05-19).
    #
    #     YANGI funksiyalar, ya'ni `drop_entity()` KERAK EMAS. `_regrant()`
    #     esa MAJBURIY — ikkalasi ham RLS'ni chetlab o'tadi.
    # ------------------------------------------------------------------
    create_entity(AUDIT_DRAW_DUE_MARKETS)
    create_entity(OCCUPANCY_DAY_CLOSE_MARKETS)
    for signature in OCCUPANCY_GRANT_SIGNATURES:
        _regrant(signature)


def downgrade() -> None:
    """Downgrade schema."""
    drop_entity(OCCUPANCY_DAY_CLOSE_MARKETS)
    drop_entity(AUDIT_DRAW_DUE_MARKETS)

    # TARTIB TESKARI: trigger AVVAL yechiladi, funksiya KEYIN o'chiriladi —
    # `DROP FUNCTION` unga tayanuvchi trigger mavjud bo'lganda yiqiladi.
    for table, _function_name, trigger_name in reversed(IMMUTABILITY_TRIGGERS):
        detach_immutability_trigger(table, trigger_name)
    drop_entity(ZONE_REVIEW_IMMUTABLE)
    drop_entity(OCCUPANCY_EVENT_IMMUTABLE)

    for table in reversed(OCCUPANCY_AUDITED_TABLES):
        detach_audit_trigger(table)

    for table in reversed(OCCUPANCY_TENANT_TABLES):
        drop_entity(owner_bootstrap_policy(table))
        drop_entity(tenant_policy(table))

    op.drop_index(OCCUPANCY_UNCERTAIN_INDEX, table_name="occupancy_events")
    op.drop_index(CAMERA_ZONE_ACTIVE_INDEX, table_name="camera_zones")

    # TARTIB — `OCCUPANCY_DELETE_ORDER` bo'yicha, ya'ni FK zanjirida
    # BOLALARDAN ota-onaga. Ro'yxat `reversed(OCCUPANCY_TENANT_TABLES)` dan
    # HOSIL QILINMAYDI va sabab reyestrning o'z docstringida: bugungi
    # ustma-ustlik TASODIF, ikki ro'yxat esa ikki xil savolga javob beradi
    # va MUSTAQIL o'zgaradi.
    for table in OCCUPANCY_DELETE_ORDER:
        op.drop_table(table)

    # ⚠ KONSTRAYT O'CHIRISH XOM SQL BILAN (`0014` downgrade'ida o'rnatilgan
    #   qoida): `op.create_unique_constraint(...)` ga to'liq nom berilgan,
    #   ya'ni `uq` konvensiyasi (`%(constraint_name)s` tokeni YO'Q) uni
    #   o'zgartirmaydi va nom bazada AYNAN shunday turadi. Xom SQL da nom
    #   AYNAN bitta joyda hosil qilinadi.
    op.execute("ALTER TABLE public.snapshots DROP CONSTRAINT uq_snapshots_market_id_id")
