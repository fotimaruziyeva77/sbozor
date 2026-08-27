"""snapshot_domain: mavsumiy jadval, kunlik reja, kadr, ogohlantirish + yurak urishi

Revision ID: 0014
Revises: 0013
Create Date: 2026-08-04

4-FAZANING BIRINCHI MIGRATSIYASI. Beshta yangi tenant jadvalini olib keladi
va shu bilan `tests/integration/test_market_delete_guard.py` ni ATAYIN
QIZARTIRADI — kaskadni kengaytirish `0015_market_delete_snapshots` da, AYNAN
SHU REJANING oynasida bajariladi (`0012` -> `0013` juftligining takrori,
W0-6/D-17).

=============================================================================
BU MIGRATSIYADA QOTIB QOLADIGAN OLTI QAROR:

1. `capture_runs`, `snapshots`, `alert_events` — AUDIT TRIGGERIDAN
   CHIQARILGAN. Ikki mustaqil sabab:
     (a) uchalasi ham HODISA JURNALI va faqat qo'shiladi (odam
         tahrirlamaydi) — audit ularning ustiga o'sha ma'lumotning IKKINCHI
         NUSXASINI yozardi (`nvr_discovery_runs` bilan bir xil sinf);
     (b) HAJM: 175 qator/kun/bozor x har holat o'tishi
         (`pending`->`running`->`succeeded`) ~ kuniga 525 audit qatori BITTA
         bozordan; o'nta bozorda yiliga ~1.9 mln qator. `audit_log`
         append-only, ya'ni u hech qachon kichraymaydi.
   IZ YO'QOLMAYDI: JADVAL o'zgarishi (kim slotni o'chirdi) auditda, KUNLIK
   YUGURISHLAR esa `capture_runs` ning O'ZIDA tarixga ega. Shuning uchun
   audit tsikli `SNAPSHOT_AUDITED_TABLES` ustidan yuradi,
   `SNAPSHOT_TENANT_TABLES` ustidan EMAS.

2. `business_date` `scheduled_at` DAN, `created_at` DAN EMAS. Reja qatori
   o'zi tegishli bo'lgan kundan OLDIN yaratiladi (kunning birinchi tikida,
   00:00-00:05 oynasida). `created_at` ga tayanish o'sha oynada yozilgan
   qatorni OLDINGI kunga tushirardi va 06:00 sloti kechagi hisobotga tushib
   qolardi. Bu 1-fazadagi moliyaviy shakldan (`helpers.BUSINESS_DATE_EXPR`)
   ATAYIN farq qiladi: u yerda qator hodisadan KEYIN, bu yerda esa hodisadan
   OLDIN yoziladi.

3. `UNIQUE (market_id, camera_id, business_date, slot_time)` — CAM-05 NING
   DB KAFOLATI (T-04-18). Ilova mantig'i bunga TAYANADI, uni
   TAKRORLAMAYDI: tick `ON CONFLICT DO NOTHING` bilan yozadi va poygani
   DB'ga topshiradi. Ikki parallel tik («planer qayta ko'tarildi va tickni
   takrorladi» — taskiq'ning hujjatlashtirilgan yiqilish rejimi) «avval
   tekshir, keyin yoz» naqshida ikkalasi ham bo'sh holatni ko'rardi va
   bitta slot uchun IKKITA qator tug'ilardi; 6-fazada bu bitta kunni ikki
   marta hisoblash degani.

4. `UNIQUE (id, is_billable)` — 5-FAZA UCHUN ILGAK (D-16).
   ⚠ SHAKL O'LCHANGAN, TAXMIN QILINMAGAN. `04-01` (2026-08-04) W0-1 zondi
   HAQIQIY `postgres:18.4` da `BILLABLE_ANCHOR_SUPPORTED = true` ni o'lchadi:
   `GENERATED ALWAYS AS (quality_verdict = 'ok') STORED` ustun ustidagi
   `UNIQUE` kompozit FK NISHONI bo'la OLADI. Shuning uchun bu yerda
   TUZILMAVIY shakl yozildi va `BEFORE INSERT/UPDATE` trigger varianti
   (~15 qator) KERAK BO'LMADI. Zond kafolatning ikkala yo'nalishini ham
   o'lchadi: `'dark'` qatorga havola `ForeignKeyViolation` beradi, VA
   mavjud `'ok'` qatorni `'dark'` ga `UPDATE` qilish ham rad etiladi.

5. `EXCLUDE USING gist (market_id WITH =, period WITH &&)` — «bir kunga
   AYNAN bitta profil» DB invarianti (T-04-19). Ilova qatlamidagi tekshiruv
   ikki parallel so'rovda ikkalasini ham o'tkazib yuborardi va bir kunga
   ikki xil slot to'plami paydo bo'lardi — «ertasi kuni AYNAN o'sha
   slotlarda» (SC#1) da'vosi tekshirib bo'lmaydigan holga kelardi.

6. PG `ENUM` TIPI ISHLATILMAYDI. Ustunlar `text` + enum'dan HOSILA `CHECK`
   ifodasi. Sabab ikkita: (a) PG enum tipiga qiymat qo'shish tranzaksiya
   ichida bajarilmaydi va har safar alohida migratsiya nayrangini talab
   qiladi; (b) loyihada `cameras.status`, `nvr_discovery_runs.status` va
   `stalls.status` uchalasi ham allaqachon `text`+`CHECK` — yangi shakl
   IKKINCHI konventsiya yaratardi.
=============================================================================

⚠ `btree_gist` KENGAYTMASI QAYTA KERAK BO'LDI.
`0012_nvr_domain.py:46-53` «kengaytma kerak emas» deb yozgan, LEKIN sabab
`ExcludeConstraint` YO'QLIGIDA edi. Bu yerda `snapshot_schedules` da u BOR,
ya'ni `0009_vendors.py:136` shakli qaytadi va `require_extension(...)`
migratsiyaning BIRINCHI satri bo'ladi. `op.execute` bilan kengaytma
YARATILMAYDI: migratsiya roli `NOCREATEDB` va bazaning egasi emas
(`0009_vendors.py:118-136` da o'lchangan).

⚠ ALEMBIC `ExcludeConstraint` NI KO'RMAYDI — IKKI TOMONLAMA
(`0009_vendors.py:29-40`): model va DB bir xil bo'lganda diff bo'sh, LEKIN
konstrayt modeldan OLIB TASHLANGANDA HAM diff bo'sh. Shuning uchun u shu
yerda LITERAL yoziladi va mavjudligi
`tests/tenancy/test_snapshot_domain_meta.py` bilan alohida qulflanadi.

⚠ `system_heartbeats` — TENANT JADVALI EMAS. U RLS tsikliga KIRMAYDI
(`market_id` ustuni yo'q, tenant predikati yozib bo'lmaydi) va
`GLOBAL_TABLES` da. Lekin `grant_app_dml()` MAJBURIY: worker yurak urishini
YOZISHI, `core-api` esa `/internal/self-check` uchun O'QISHI kerak — grantsiz
ikkalasi ham `permission denied` bilan yiqilardi.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

import sqlalchemy as sa
from alembic import op
from sbozor_core.models.nvr import CAPTURE_STREAM_CHECK
from sbozor_core.models.snapshot import (
    ALERT_OPEN_EXPR,
    ALERT_OPEN_INDEX,
    ALERT_OPEN_PREDICATE,
    ALERT_SEVERITY_CHECK,
    CAPTURE_BUSINESS_DATE_EXPR,
    CAPTURE_DUE_INDEX,
    CAPTURE_DUE_PREDICATE,
    CAPTURE_METHOD_CHECK,
    CAPTURE_OVERDUE_INDEX,
    CAPTURE_OVERDUE_PREDICATE,
    CAPTURE_RUN_STATUS_CHECK,
    SNAPSHOT_BUSINESS_DATE_EXPR,
    SNAPSHOT_LIGHT_MODE_CHECK,
    SNAPSHOT_QUALITY_CHECK,
    SNAPSHOT_TIER_CHECK,
)
from sqlalchemy.dialects import postgresql as pg

from migrations.entities import (
    SNAPSHOT_AUDITED_TABLES,
    SNAPSHOT_DELETE_ORDER,
    SNAPSHOT_TENANT_TABLES,
)
from migrations.entities.policies import owner_bootstrap_policy, tenant_policy
from migrations.helpers import (
    attach_audit_trigger,
    create_entity,
    detach_audit_trigger,
    drop_entity,
    enable_tenant_rls,
    grant_app_dml,
    require_extension,
)

# revision identifiers, used by Alembic.
revision: str = "0014"
down_revision: str | Sequence[str] | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# ⚠ INDEKS NOMLARI, PREDIKATLARI VA `CHECK` IFODALARI SHU YERDA E'LON
#   QILINMAYDI — ular `sbozor_core.models.snapshot` dan IMPORT qilinadi
#   (yuqoriga qarang).
#
#   Sabab O'LCHANGAN (03-03, birinchi urinish): `op.create_index(...)`
#   yolg'iz o'zi yetarli emas. Autogenerate model metadata'sini baza bilan
#   solishtiradi, ya'ni modelda e'lon qilinmagan indeks "o'chirilgan" deb
#   ko'rinadi va `test_autogenerate_is_empty` `remove_index` bilan qizaradi.
#   Indeks IKKALA tomonda ham bo'lishi shart, nom va predikat esa BITTA
#   manbadan kelishi shart — aks holda ular jimgina ajralib ketardi.

MARKET_TZ = "Asia/Tashkent"
"""Bu migratsiya YOZADIGAN yagona mintaqa literali — `helpers.MARKET_TZ_LITERAL` jufti.

Faqat `capture_on_closed_days` ustunining izohida ishlatiladi, DDL'ga
tushmaydi: `business_date` ifodalari MODELDAN import qilinadi
(`CAPTURE_BUSINESS_DATE_EXPR` / `SNAPSHOT_BUSINESS_DATE_EXPR`), ya'ni bu
faylda mintaqa literali ikkinchi manba sifatida yashamaydi.
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
    # ------------------------------------------------------------------
    require_extension("btree_gist")

    # ------------------------------------------------------------------
    # 1. snapshot_schedules — MAVSUMIY profil (CAM-04).
    #
    #    `EXCLUDE` bu jadvalning butun mazmuni: «bir kunga AYNAN bitta
    #    profil». Mavsumiylik amalda 2-fazadagi tarif qo'shish bilan bir
    #    xil amal — mavjud ochiq oxirli profil BO'LINADI. Bo'shliq
    #    (qoplanmagan kun) ATAYIN mumkin va u UI'da ko'rinishi shart.
    # ------------------------------------------------------------------
    op.create_table(
        "snapshot_schedules",
        _market_id(),
        _uuid_pk(),
        # Admin yozadi: «Standart», «Yozgi», «Qishki». Standart profilning
        # nomi `market_activate()` da qadalgan (`0015`).
        sa.Column("name", sa.Text(), nullable=False),
        # HAR DOIM `[)` (`sbozor_core.periods.PERIOD_BOUNDS`) — loyihadagi
        # YAGONA chegara konventsiyasi. Xom `daterange(...)` yozilsa
        # konvensiya ikkinchi manbaga ega bo'lardi.
        sa.Column("period", pg.DATERANGE(), nullable=False),
        _created_at(),
        _updated_at(),
        sa.PrimaryKeyConstraint("id", name="pk_snapshot_schedules"),
        sa.ForeignKeyConstraint(
            ["market_id"], ["markets.id"], name="fk_snapshot_schedules_market_id_markets"
        ),
        # COMPOSITE FK NISHONI: `snapshot_schedule_slots` `(market_id,
        # schedule_id)` ga havola qiladi, ya'ni A bozorining sloti B
        # bozorining profiliga bog'lana OLMAYDI — bu RLS emas, SXEMA
        # darajasidagi kafolat.
        sa.UniqueConstraint("market_id", "id", name="uq_snapshot_schedules_market_id_id"),
        # ⚠ ALEMBIC BU KONSTRAYTNI AVTOGENERATSIYA QILMAYDI VA UNING
        #   YO'QOLGANINI HAM SEZMAYDI (fayl boshidagi ogohlantirish).
        #   Shuning uchun u shu yerda LITERAL turadi va meta-test bilan
        #   qulflanadi. Ustunlar TARTIBI ham ahamiyatli: `market_id`
        #   BIRINCHI, ya'ni konstrayt ostidagi GiST indeksi tenant
        #   invarianti #5 dan o'tadi. Buzilganda SQLSTATE `23P01`.
        pg.ExcludeConstraint(
            ("market_id", "="),
            ("period", "&&"),
            name="ex_snapshot_schedules_no_overlap",
            using="gist",
        ),
        # BO'SH davr (`[a, a)`) `&&` bilan HECH NIMA bilan kesishmaydi,
        # ya'ni `EXCLUDE` uni to'xtatmaydi va jadvalda «mavjud, lekin hech
        # qaysi kunda amal qilmaydigan» fantom profil paydo bo'lardi.
        sa.CheckConstraint("NOT isempty(period)", name="ck_snapshot_schedules_period_not_empty"),
        sa.CheckConstraint("length(btrim(name)) > 0", name="ck_snapshot_schedules_name_not_blank"),
    )

    # ------------------------------------------------------------------
    # 2. snapshot_schedule_slots — profilning aniq vaqtlari.
    #
    #    `time`, `timetz` EMAS: slot MAHALLIY DEVOR-SOATI va
    #    materializatsiya uni `((:business_date + slot_time) AT TIME ZONE
    #    m.timezone)` bilan `timestamptz` ga aylantiradi. `timetz` vaqtga
    #    QADALGAN ofset biriktiradi — PostgreSQL hujjatining o'zi bu tipni
    #    «kamdan-kam foydali» deb belgilagan.
    #
    #    `ON DELETE CASCADE` FAQAT SHU YERDA: profil o'chirilsa slotlari
    #    ketadi. ⚠ `capture_runs` ga kaskad YO'Q — o'tmishdagi dalil jadval
    #    o'zgarishidan OMON QOLISHI shart.
    # ------------------------------------------------------------------
    op.create_table(
        "snapshot_schedule_slots",
        _market_id(),
        _uuid_pk(),
        sa.Column("schedule_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("slot_time", sa.Time(timezone=False), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_snapshot_schedule_slots"),
        sa.ForeignKeyConstraint(
            ["market_id"], ["markets.id"], name="fk_snapshot_schedule_slots_market_id_markets"
        ),
        # ⚠ NOM QO'LDA BERILGAN, konvensiyadan HOSILA EMAS: konvensiya 67
        #   belgilik nom berardi, PostgreSQL esa identifikatorni 63 baytga
        #   JIMGINA kesadi — natijada model metadata'sidagi nom va bazadagi
        #   nom farq qilib, `alembic check` har safar soxta diff berardi.
        sa.ForeignKeyConstraint(
            ["market_id", "schedule_id"],
            ["snapshot_schedules.market_id", "snapshot_schedules.id"],
            name="fk_snapshot_schedule_slots_schedule",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("market_id", "id", name="uq_snapshot_schedule_slots_market_id_id"),
        # Bir profilda bir vaqt IKKI MARTA bo'lolmaydi: dublikat slot o'sha
        # kamera uchun ikkita `capture_runs` qatorini talab qilardi va
        # `uq_capture_runs_...` ni buzardi — materializatsiya butun bozor
        # uchun yiqilardi. `market_id` bilan BOSHLANADI.
        sa.UniqueConstraint(
            "market_id",
            "schedule_id",
            "slot_time",
            name="uq_snapshot_schedule_slots_market_id_schedule_id_slot_time",
        ),
    )

    # ------------------------------------------------------------------
    # 3. capture_runs — KUNLIK REJA, ya'ni «yo'qlik» ni ko'rinadigan
    #    qiladigan qator (D-20).
    #
    #    Yo'qlik HODISA QOLDIRMAYDI. «Umuman ishlamadi» FAQAT kutilgan
    #    qator OLDINDAN yozilgan bo'lsa aniqlanadi — shuning uchun kun
    #    boshida 25 kamera x 7 slot = 175 qator `pending` holatida
    #    YOZILADI. Bu «alert-on-absence» ni «alert-on-state» ga
    #    aylantiradigan YAGONA qadam.
    #
    #    `nvr_id` — DENORMALIZATSIYA, IDENTIFIKATSIYA EMAS: u
    #    idempotentlik kalitida ATAYIN YO'Q. Kamera boshqa NVR'ga
    #    ko'chirilsa tarixdagi slotlarning identifikatori O'ZGARMASLIGI
    #    kerak, aks holda o'sha kun uchun IKKINCHI qator tug'ilib, bitta
    #    slot ikki marta hisoblanardi. Ustunning vazifasi boshqa: fan-out
    #    `nvr_id` bo'yicha GURUHLANADI (konkurentlik chegarasi NVR ga
    #    tegishli — D-04/D-08).
    #
    #    `snapshot_id` da FK ATAYIN YO'Q: `snapshots` bu jadvalga kompozit
    #    FK bilan tayanadi va teskari FK TSIKL yaratardi.
    # ------------------------------------------------------------------
    op.create_table(
        "capture_runs",
        _market_id(),
        _uuid_pk(),
        sa.Column("camera_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("nvr_id", pg.UUID(as_uuid=True), nullable=False),
        # Profil slotidan NUSXALANADI. Jadval keyinroq tahrirlansa BUGUNGI
        # reja o'zgarmaydi (D-05) — ya'ni rejaning MUZLATILGAN nusxasi.
        sa.Column("slot_time", sa.Time(timezone=False), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        # ⚠ IFODA MODELDAN IMPORT QILINADI — fayl boshidagi 2-band.
        sa.Column(
            "business_date",
            sa.Date(),
            sa.Computed(CAPTURE_BUSINESS_DATE_EXPR, persisted=True),
            nullable=False,
        ),
        # Boshlang'ich `pending` — qator REJADAN tug'iladi, hodisadan emas.
        sa.Column("status", sa.Text(), server_default=sa.text("'pending'"), nullable=False),
        sa.Column("attempts", sa.SmallInteger(), server_default=sa.text("0"), nullable=False),
        # IJARA (lease): `SELECT ... FOR UPDATE SKIP LOCKED` bilan olinadi
        # va `locked_until` o'tgach qator qaytariladi — yiqilgan worker'ning
        # ishi mangu qulflanib qolmaydi.
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        # FAQAT diagnostika: qulflash qarori `locked_until` ga tayanadi.
        sa.Column("locked_by", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        # KOD, MATN EMAS: frontend uni uch tilga tarjima qiladi (CLAUDE.md
        # «3 til majburiy»). Matn saqlansa u bitta tilda muzlab qolardi.
        sa.Column("error_code", sa.Text(), nullable=True),
        # ⚠ YOZISHDAN OLDIN `mask_sensitive` DAN O'TADI (`03-PATTERNS.md`
        #   §S-7): filtr faqat KALIT nomiga qaraydi.
        sa.Column("error_detail", pg.JSONB(), nullable=True),
        # QAYSI yo'l HAQIQATAN ishladi (`nvr_devices.capture_method` —
        # SOZLAMA). `NULL` = hali urinilmagan.
        sa.Column("capture_method", sa.Text(), nullable=True),
        # `market_is_open()` dan (D-10). Bayroq qator yozilgan PAYTDAGI
        # holatni muzlatadi: kalendar keyinroq tahrirlansa o'tmishdagi dalil
        # qayta talqin qilinmaydi.
        sa.Column("is_market_open", sa.Boolean(), nullable=False),
        sa.Column("snapshot_id", pg.UUID(as_uuid=True), nullable=True),
        _created_at(),
        sa.PrimaryKeyConstraint("id", name="pk_capture_runs"),
        sa.ForeignKeyConstraint(
            ["market_id"], ["markets.id"], name="fk_capture_runs_market_id_markets"
        ),
        sa.ForeignKeyConstraint(
            ["market_id", "camera_id"],
            ["cameras.market_id", "cameras.id"],
            name="fk_capture_runs_market_id_camera_id_cameras",
        ),
        sa.ForeignKeyConstraint(
            ["market_id", "nvr_id"],
            ["nvr_devices.market_id", "nvr_devices.id"],
            name="fk_capture_runs_market_id_nvr_id_nvr_devices",
        ),
        # ⚠ CAM-05 NING YAGONA DB KAFOLATI (fayl boshidagi 3-band).
        #   `business_date` KALITGA KIRADI, `scheduled_at` esa KIRMAYDI:
        #   ikkinchisi `timestamptz` va u yarim tun atrofida bir xil
        #   biznes-kunning ikki xil qiymati bo'lishi mumkin edi.
        #   `market_id` BIRINCHI. Buzilganda SQLSTATE `23505`.
        sa.UniqueConstraint(
            "market_id",
            "camera_id",
            "business_date",
            "slot_time",
            name="uq_capture_runs_market_id_camera_id_business_date_slot_time",
        ),
        # COMPOSITE FK NISHONI: `snapshots` `(market_id, capture_run_id)` ga.
        sa.UniqueConstraint("market_id", "id", name="uq_capture_runs_market_id_id"),
        sa.CheckConstraint(CAPTURE_RUN_STATUS_CHECK, name="ck_capture_runs_status_allowed"),
        sa.CheckConstraint(CAPTURE_METHOD_CHECK, name="ck_capture_runs_capture_method_allowed"),
        sa.CheckConstraint("attempts >= 0", name="ck_capture_runs_attempts_non_negative"),
        sa.CheckConstraint(
            "finished_at IS NULL OR started_at IS NULL OR finished_at >= started_at",
            name="ck_capture_runs_finished_after_started",
        ),
    )

    # ------------------------------------------------------------------
    # 4. snapshots — kadrning METAMA'LUMOTI (CAM-06).
    #
    #    ⚠ KADR BAYTLARI BU JADVALDA YO'Q — faqat `object_key`,
    #    `size_bytes`, `etag`. `bytea` ustuni «qulaylik uchun»
    #    QO'SHILMAYDI: JPEG'lar Postgres TOAST'iga tushib `pg_dump` ni
    #    ~175 MB/kun/bozorga o'stirardi va backup/restore mashqi (spec §5)
    #    bajarib bo'lmas holga kelardi. Bu `cameras` da `rtsp_url` ustuni
    #    yo'qligining aynan bir oilasidagi qaror (`0012:26-31`).
    #
    #    ⚠ `quality_verdict` YOZISH PAYTIDA qo'yiladi, HISOBLANMAYDI
    #    (T-04-23): `quality_thresholds_version` qaysi chegara to'plami
    #    bilan qo'yilganini yozadi. Aks holda chegarani sozlash o'tmishdagi
    #    kadrlarning billing yaroqliligini RETROAKTIV o'zgartirardi.
    # ------------------------------------------------------------------
    op.create_table(
        "snapshots",
        _market_id(),
        _uuid_pk(),
        sa.Column("capture_run_id", pg.UUID(as_uuid=True), nullable=False),
        # DENORMALIZATSIYA: 5/6-faza so'rovlari «shu kameraning shu
        # kundagi kadrlari» ni `capture_runs` ga JOIN qilmasdan olishi kerak.
        sa.Column("camera_id", pg.UUID(as_uuid=True), nullable=False),
        # ⚠ `capture_runs.scheduled_at` DAN NUSXALANADI, MUSTAQIL
        #   HISOBLANMAYDI: ikki mustaqil hisoblash manbai yarim tunda bir
        #   kun farq qilardi (Pitfall 3).
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        # FORENZIKA uchun: kadr HAQIQATAN qachon olindi. `business_date` bu
        # ustundan HISOBLANMAYDI — 06:00 sloti 06:09 da olingan bo'lsa ham u
        # 06:00 slotining dalili bo'lib qolishi kerak.
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("slot_time", sa.Time(timezone=False), nullable=False),
        # ⚠ `capture_runs.business_date` BILAN AYNAN BIR XIL IFODA — ikkalasi
        #   ham modeldan import qilinadi va u yerda ALIAS (nusxa emas).
        sa.Column(
            "business_date",
            sa.Date(),
            sa.Computed(SNAPSHOT_BUSINESS_DATE_EXPR, persisted=True),
            nullable=False,
        ),
        # DETERMINISTIK kalit (04-04). Siqilgan versiya AYNAN shu kalitni
        # ustiga yozadi — 6-fazadagi dalil havolalari buzilmaydi.
        sa.Column("object_key", sa.Text(), nullable=False),
        sa.Column("storage_tier", sa.Text(), server_default=sa.text("'full'"), nullable=False),
        # 455 kundan keyin obyekt o'chiriladi, QATOR QOLADI (D-18).
        sa.Column("object_deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        # S3 javobidan — yuklashning HAQIQATAN yakunlanganini tasdiqlaydi
        # (03-14: natijadan o'lchanadi, status kodidan emas).
        sa.Column("etag", sa.Text(), nullable=True),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("quality_verdict", sa.Text(), nullable=False),
        # ⚠ O'LCHOVLARNING O'ZI SAQLANADI, FAQAT HUKM EMAS (D-15): Phase 0
        #   ning real Karmana kadrlari chegaralarni SQL bilan sozlaydi,
        #   qayta kadr olish bilan emas.
        sa.Column("quality_mean", sa.Numeric(6, 2), nullable=False),
        sa.Column("quality_stddev", sa.Numeric(6, 2), nullable=False),
        # IR aniqlash uchun; `NULL` = o'lchanmadi.
        sa.Column("quality_saturation", sa.Numeric(6, 2), nullable=True),
        sa.Column("quality_thresholds_version", sa.SmallInteger(), nullable=False),
        # `quality_verdict` ning DUBLIKATI EMAS (D-12: superset).
        sa.Column("light_mode", sa.Text(), nullable=False),
        sa.Column("capture_method", sa.Text(), nullable=False),
        _created_at(),
        # ⚠ HOSILA USTUN — fayl boshidagi 4-band (shakl O'LCHANGAN).
        sa.Column(
            "is_billable",
            sa.Boolean(),
            sa.Computed("quality_verdict = 'ok'", persisted=True),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_snapshots"),
        sa.ForeignKeyConstraint(
            ["market_id"], ["markets.id"], name="fk_snapshots_market_id_markets"
        ),
        sa.ForeignKeyConstraint(
            ["market_id", "capture_run_id"],
            ["capture_runs.market_id", "capture_runs.id"],
            name="fk_snapshots_market_id_capture_run_id_capture_runs",
        ),
        # `camera_id` DENORMALIZATSIYA, lekin kompozit FK baribir qo'yiladi:
        # denormalizatsiya tenant chegarasini bo'shatish uchun bahona emas.
        sa.ForeignKeyConstraint(
            ["market_id", "camera_id"],
            ["cameras.market_id", "cameras.id"],
            name="fk_snapshots_market_id_camera_id_cameras",
        ),
        sa.UniqueConstraint(
            "market_id", "capture_run_id", name="uq_snapshots_market_id_capture_run_id"
        ),
        sa.UniqueConstraint("market_id", "object_key", name="uq_snapshots_market_id_object_key"),
        # ⚠⚠ D-16 NING YAGONA ILGAGI — BU KONSTRAYT BOSHQA FAZA UCHUN BOR.
        #
        #   5-fazada `occupancy_events` shunday quriladi:
        #       snapshot_is_billable boolean NOT NULL DEFAULT true
        #       CHECK  (snapshot_is_billable)
        #       FOREIGN KEY (snapshot_id, snapshot_is_billable)
        #           REFERENCES snapshots (id, is_billable)
        #
        #   Ya'ni `quality_verdict <> 'ok'` bo'lgan kadrga bandlik dalilini
        #   bog'lash uchun kerak bo'lgan `(id, true)` juftligi JADVALDA
        #   UMUMAN MAVJUD BO'LMAYDI va FK rad etadi.
        #
        #   ⚠ NOMI KONVENSIYADAN HOSILA EMAS: `billable_anchor` — 5-faza va
        #     meta-test uchun QIDIRILADIGAN belgidir.
        sa.UniqueConstraint("id", "is_billable", name="uq_snapshots_billable_anchor"),
        sa.CheckConstraint(SNAPSHOT_QUALITY_CHECK, name="ck_snapshots_quality_verdict_allowed"),
        sa.CheckConstraint(SNAPSHOT_LIGHT_MODE_CHECK, name="ck_snapshots_light_mode_allowed"),
        sa.CheckConstraint(SNAPSHOT_TIER_CHECK, name="ck_snapshots_storage_tier_allowed"),
        sa.CheckConstraint(CAPTURE_METHOD_CHECK, name="ck_snapshots_capture_method_allowed"),
        sa.CheckConstraint("size_bytes > 0", name="ck_snapshots_size_bytes_positive"),
        sa.CheckConstraint(
            "length(btrim(object_key)) > 0", name="ck_snapshots_object_key_not_blank"
        ),
        # `purged` qator obyekt QACHON o'chirilganini aytishi SHART, aks
        # holda «kadr mavjud edi, arxivdan chiqarildi» da'vosi sanasiz
        # qolardi va operator uni «yo'qolgan kadr» dan ajrata olmasdi.
        sa.CheckConstraint(
            "(storage_tier = 'purged') = (object_deleted_at IS NOT NULL)",
            name="ck_snapshots_purged_has_deletion_time",
        ),
    )

    # ------------------------------------------------------------------
    # 5. alert_events — ochiq ogohlantirishning HOLAT yozuvi (D-22).
    #
    #    TENANT jadvali: ogohlantirish HAR DOIM aniq bir bozorning
    #    kamerasiga tegishli va UI uni BOZOR sahifasida ko'rsatadi.
    #    (`04-RESEARCH.md` §E.13 uni «global» deb atagan, lekin o'sha
    #    yerdayoq unga `market_id` bergan — ikkisi bir vaqtda to'g'ri
    #    bo'la olmaydi.)
    #
    #    ⚠ `snapshot_id` USTUNI YO'Q va bo'lmasligi ham kerak (D-19):
    #    alertga kadr rasmi HECH QACHON biriktirilmaydi. Dalil-kadrlar
    #    bozor tashrifchilarining shaxsiy ma'lumoti, Telegram serverlari
    #    esa O'zR data-rezidentlik chegarasidan tashqarida.
    # ------------------------------------------------------------------
    op.create_table(
        "alert_events",
        _market_id(),
        _uuid_pk(),
        # i18n KALITI, matn emas (`capture_runs.error_code` bilan bir xil).
        sa.Column("alert_key", sa.Text(), nullable=False),
        # Muammo davom etsa CHASTOTA emas, DARAJA oshadi — eskalatsiya.
        sa.Column("severity", sa.Text(), nullable=False),
        # Kamera yoki NVR. FK ATAYIN YO'Q: subyekt IKKI XIL jadvaldan
        # bo'lishi mumkin (polimorf havola). `NULL` = butun bozor.
        sa.Column("subject_id", pg.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "first_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        # Bo'g'ilgan takrorlar shu yerda sanaladi va keyingi xabarda
        # «(so'nggi soatda yana 47 marta)» bo'lib chiqadi — bo'g'ish
        # ma'lumot yo'qotmaydi.
        sa.Column("occurrences", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("notified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        # FAQAT matn va sonlar (D-19).
        sa.Column("detail", pg.JSONB(), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_alert_events"),
        sa.ForeignKeyConstraint(
            ["market_id"], ["markets.id"], name="fk_alert_events_market_id_markets"
        ),
        sa.UniqueConstraint("market_id", "id", name="uq_alert_events_market_id_id"),
        sa.CheckConstraint(ALERT_SEVERITY_CHECK, name="ck_alert_events_severity_allowed"),
        sa.CheckConstraint("occurrences > 0", name="ck_alert_events_occurrences_positive"),
        sa.CheckConstraint(
            "length(btrim(alert_key)) > 0", name="ck_alert_events_alert_key_not_blank"
        ),
        sa.CheckConstraint(
            "last_seen_at >= first_seen_at", name="ck_alert_events_last_seen_after_first"
        ),
    )

    # ------------------------------------------------------------------
    # 6. system_heartbeats — GLOBAL jadval (FOUND-06).
    #
    #    ⚠ RLS TSIKLIGA KIRMAYDI va `SNAPSHOT_TENANT_TABLES` da YO'Q: unda
    #    `market_id` ustuni YO'Q, ya'ni tenant predikatini yozib bo'lmaydi.
    #    Komponent (`capture_tick`, `retention`, `backup`) BOZORGA TEGISHLI
    #    EMAS — tik butun platforma uchun bitta jarayonda ishlaydi.
    #
    #    Uni tenant-scoped qilish MANTIQIY XATO bo'lardi: tik umuman
    #    ishlamayotgan bo'lsa, uning yo'qligini bozor kontekstida qidirish
    #    0 qator berardi va sukunat «hammasi joyida» bilan bir xil
    #    ko'rinardi (D-20 aynan shuni taqiqlaydi).
    #
    #    `component` — BIRLAMCHI KALITNING O'ZI: har komponentga aynan
    #    bitta qator va yozuv `ON CONFLICT (component) DO UPDATE` bilan
    #    ketadi. Surrogat `id` ikkinchi `capture_tick` qatoriga yo'l ochardi.
    # ------------------------------------------------------------------
    op.create_table(
        "system_heartbeats",
        sa.Column("component", sa.Text(), nullable=False),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("detail", pg.JSONB(), nullable=True),
        sa.PrimaryKeyConstraint("component", name="pk_system_heartbeats"),
    )
    # ⚠ GRANT MAJBURIY VA U `enable_tenant_rls()` ORQALI KELMAYDI (jadval
    #   tenant emas). Worker yurak urishini YOZADI, `core-api` esa
    #   `/internal/self-check` uchun O'QIYDI — grantsiz ikkalasi ham
    #   `permission denied` bilan yiqilardi va FOUND-06 ning eng pastki
    #   qatlami jimgina ishlamay qolardi.
    grant_app_dml("system_heartbeats")

    # ------------------------------------------------------------------
    # 7. MAVJUD JADVALLARGA USTUNLAR — kadr olish sozlamalari.
    #
    #    `server_default` HAR BIRIDA MAJBURIY: jadvallarda allaqachon
    #    qatorlar bor va `NOT NULL` ustunni standartsiz qo'shish
    #    migratsiyani darhol yiqitardi.
    # ------------------------------------------------------------------
    # D-06/D-07: uchala yo'l bitta protokol ortida, tanlov MA'LUMOT.
    op.add_column(
        "nvr_devices",
        sa.Column("capture_method", sa.Text(), server_default=sa.text("'go2rtc'"), nullable=False),
    )
    # D-08: STANDART 1, ya'ni KETMA-KET. Arifmetika xavfni yo'q qiladi:
    # sovuq kadr ~4 s, 25 kamera ketma-ket = 100 s, grace = 600 s — ya'ni
    # NVR ning O'LCHANMAGAN sessiya chegarasi fazani HECH QACHON bloklay
    # olmaydi. Research'dagi 4 taklifi shu sababdan rad etilgan.
    op.add_column(
        "nvr_devices",
        sa.Column(
            "max_concurrent_captures",
            sa.SmallInteger(),
            server_default=sa.text("1"),
            nullable=False,
        ),
    )
    op.add_column(
        "nvr_devices",
        sa.Column(
            "capture_stagger_ms", sa.Integer(), server_default=sa.text("500"), nullable=False
        ),
    )
    # ADAPTIV PASAYTIRISH uchun. ⚠ AVTOMATIK OSHIRISH YO'Q (tebranish xavfi).
    op.add_column(
        "nvr_devices", sa.Column("observed_stream_limit", sa.SmallInteger(), nullable=True)
    )
    op.create_check_constraint(
        "capture_method_allowed", "nvr_devices", sa.text(CAPTURE_METHOD_CHECK)
    )
    op.create_check_constraint(
        "max_concurrent_captures_positive", "nvr_devices", "max_concurrent_captures > 0"
    )
    op.create_check_constraint(
        "capture_stagger_ms_non_negative", "nvr_devices", "capture_stagger_ms >= 0"
    )
    op.create_check_constraint(
        "observed_stream_limit_positive",
        "nvr_devices",
        "observed_stream_limit IS NULL OR observed_stream_limit > 0",
    )

    # D-09: `'main'` standart. `'sub'` omborni ~12x kamaytiradi VA
    # 5-fazaning aniqlik shiftini pasaytiradi — qaror REAL KADRDA
    # o'lchanadi (Phase 0/pilot), taxmin bilan emas.
    op.add_column(
        "cameras",
        sa.Column("capture_stream", sa.Text(), server_default=sa.text("'main'"), nullable=False),
    )
    op.create_check_constraint("capture_stream_allowed", "cameras", sa.text(CAPTURE_STREAM_CHECK))

    # D-10: yopiq kunlarda ham kadr olinadi. Yopiq deb e'lon qilingan kunda
    # ko'ringan BAND RASTA — aynan mahsulot izlaydigan anomaliya
    # («ro'yxatga olinmagan savdo»). Bayroq kadr OLISHNI boshqaradi,
    # BILLINGNI emas: yopiq kunning qatorlari `is_market_open = false`
    # bilan tug'iladi va 6-faza ularni HISOBDAN chiqaradi, HISOBOTDAN esa
    # chiqarmaydi. Mintaqa chegarasi baribir `MARKET_TZ` bo'yicha.
    op.add_column(
        "market_profile",
        sa.Column(
            "capture_on_closed_days", sa.Boolean(), server_default=sa.text("true"), nullable=False
        ),
    )

    # ------------------------------------------------------------------
    # 8. QISMAN INDEKSLAR — UCHALASI HAM `op.create_table` GA SIG'MAYDI
    #    (`postgresql_where` faqat `create_index` da bor).
    # ------------------------------------------------------------------
    #
    # (a) TICK NING ISSIQ YO'LI. `market_id` bilan BOSHLANADI, chunki tick
    #     HAR BOZOR uchun ALOHIDA tranzaksiyada, tenant konteksti ostida
    #     ishlaydi — so'rovda `market_id = ...` predikati HAR DOIM bor.
    #     Qisman: yakunlangan qatorlar (kunlarning katta qismi) indeksga
    #     umuman tushmaydi.
    op.create_index(
        CAPTURE_DUE_INDEX,
        "capture_runs",
        ["market_id", "scheduled_at"],
        postgresql_where=sa.text(CAPTURE_DUE_PREDICATE),
    )
    #
    # (b) WATCHDOG NING ISSIQ YO'LI — YO'QLIK DETEKTORI (FOUND-06).
    #
    #     ⚠ BU INDEKS `market_id` BILAN BOSHLANMAYDI VA BU ATAYIN.
    #     Watchdog BARCHA BOZORLAR ustidan yuradi: savol «qaysi bozorda?»
    #     emas, «umuman nimadir osilib qoldimi?». `market_id` bilan
    #     boshlash uni o'sha so'rov uchun BUTUNLAY foydasiz qilardi
    #     (rejalashtiruvchi birinchi ustunsiz undan foydalana olmaydi) va
    #     watchdog bozorlar soni o'sgani sari to'liq skanga o'tardi.
    #
    #     Shuning uchun indeks nomi `tests/tenancy/test_meta.py::
    #     INDEX_EXCEPTIONS` ga `04-01` da SABAB bilan qo'shilgan. Bu
    #     `TUNNEL_SUBNET_INDEX` bilan BIR XIL SINF, lekin farqi bor:
    #     tunnel subneti — TENANT IZOLYATSIYASINING chegarasi, bu esa ISH
    #     REJASINING chegarasi. Istisno xavfsizlik da'vosini SUSAYTIRMAYDI:
    #     watchdog faqat identifikatorlarni oladi va har qanday keyingi
    #     o'qish odatdagidek RLS ostidan o'tadi.
    #
    #     Predikat `CaptureRunStatus` dan HOSILA
    #     (`CAPTURE_RUN_ACTIVE_STATUSES`): ikki nusxa ajralib ketganda
    #     indeks jimgina KAM holatni qamrar va ko'rinmagan `running` qator
    #     MANGU `running` bo'lib qolardi — na kadr, na alert, na hisobot.
    op.create_index(
        CAPTURE_OVERDUE_INDEX,
        "capture_runs",
        ["scheduled_at"],
        postgresql_where=sa.text(CAPTURE_OVERDUE_PREDICATE),
    )
    #
    # (c) DEBOUNCE NING YAGONA DB KAFOLATI (D-22): bitta `(bozor, kalit,
    #     subyekt)` uchun AYNAN BITTA ochiq alert. Qisman
    #     (`resolved_at IS NULL`), ya'ni yopilgan alertlar tarixi cheksiz
    #     to'planaveradi va faqat OCHIQ qator qulflanadi —
    #     `nvr_discovery_runs` ning «bir vaqtda ikki skan yo'q» indeksi
    #     bilan aynan bir xil naqsh.
    #
    #     ⚠ UCHINCHI KALIT — IFODA (`COALESCE`), va u MAJBURIY: UNIQUE
    #     indeksda `NULL` O'ZIGA TENG EMAS. `subject_id` butun bozorga
    #     tegishli alertlar uchun `NULL` bo'ladi va `COALESCE` siz bir xil
    #     `(market_id, alert_key)` juftligi uchun ISTALGANCHA ochiq qator
    #     yashab ketardi — debounce JIMGINA ishlamasdi va operator har
    #     daqiqada bir xil xabarni olardi.
    op.create_index(
        ALERT_OPEN_INDEX,
        "alert_events",
        ["market_id", "alert_key", sa.text(ALERT_OPEN_EXPR)],
        unique=True,
        postgresql_where=sa.text(ALERT_OPEN_PREDICATE),
    )

    # ------------------------------------------------------------------
    # 9. RLS. TARTIB MAJBURIY: ENABLE + FORCE + GRANT -> policy (Pitfall 10).
    #    `alembic-utils` `ENABLE`/`FORCE` ni BILMAYDI — ularsiz policy HECH
    #    QANDAY ta'sir ko'rsatmaydi va jadval hamma uchun ochiq bo'ladi.
    #
    #    TSIKL `SNAPSHOT_TENANT_TABLES` USTIDAN — BESHALA jadval.
    #    `system_heartbeats` bu yerda YO'Q (6-bandga qarang).
    # ------------------------------------------------------------------
    for table in SNAPSHOT_TENANT_TABLES:
        enable_tenant_rls(table)
        create_entity(tenant_policy(table))
        create_entity(owner_bootstrap_policy(table))

    # ------------------------------------------------------------------
    # 10. Audit — ATAYIN BOSHQA RO'YXAT USTIDAN (fayl boshidagi 1-band).
    #
    #     `SNAPSHOT_AUDITED_TABLES` = (`snapshot_schedules`,
    #     `snapshot_schedule_slots`). Qolgan uchtasi HODISA JURNALI va
    #     ularning hajmi audit jurnalini yiliga ~1.9 mln qatorga o'stirardi.
    #
    #     ⚠ IKKALA NOM `tests/tenancy/test_meta.py::PENDING_AUDIT_TRIGGERS`
    #       DAN SHU MIGRATSIYA BILAN BIR COMMITDA O'CHIRILDI. `04-01` ularni
    #       o'sha ro'yxatga qo'ygan edi (qarz ochiq); trigger endi ULANDI,
    #       ya'ni qarz YOPILDI va ro'yxat yana BO'SH. Buni unutish testni
    #       TESKARI yo'nalishdan qizartirardi (`closed` asserti).
    # ------------------------------------------------------------------
    for table in SNAPSHOT_AUDITED_TABLES:
        attach_audit_trigger(table)


def downgrade() -> None:
    """Downgrade schema."""
    for table in reversed(SNAPSHOT_AUDITED_TABLES):
        detach_audit_trigger(table)

    for table in reversed(SNAPSHOT_TENANT_TABLES):
        drop_entity(owner_bootstrap_policy(table))
        drop_entity(tenant_policy(table))

    op.drop_index(ALERT_OPEN_INDEX, table_name="alert_events")
    op.drop_index(CAPTURE_OVERDUE_INDEX, table_name="capture_runs")
    op.drop_index(CAPTURE_DUE_INDEX, table_name="capture_runs")

    # ⚠ KONSTRAYT O'CHIRISH XOM SQL BILAN, `op.drop_constraint(...)` BILAN
    #   EMAS — `0011_weekday_choice.py::_replace_check()` da o'rnatilgan
    #   qoida. Sabab: `op.create_check_constraint(...)` nom konvensiyasini
    #   (`ck_<table>_<name>`) QO'LLAYDI, ya'ni `upgrade()` da qisqa nom
    #   berilib to'liq nom hosil bo'ladi. `drop_constraint` ga to'liq nom
    #   berilganda konvensiya ikkinchi marta qo'llanish xavfi bor va nom
    #   ikki joyda hosil qilinardi. Xom SQL da nom AYNAN bitta joyda.
    for table, constraint in (
        ("cameras", "ck_cameras_capture_stream_allowed"),
        ("nvr_devices", "ck_nvr_devices_observed_stream_limit_positive"),
        ("nvr_devices", "ck_nvr_devices_capture_stagger_ms_non_negative"),
        ("nvr_devices", "ck_nvr_devices_max_concurrent_captures_positive"),
        ("nvr_devices", "ck_nvr_devices_capture_method_allowed"),
    ):
        op.execute(f"ALTER TABLE public.{table} DROP CONSTRAINT {constraint}")

    op.drop_column("market_profile", "capture_on_closed_days")
    op.drop_column("cameras", "capture_stream")
    for column in (
        "observed_stream_limit",
        "capture_stagger_ms",
        "max_concurrent_captures",
        "capture_method",
    ):
        op.drop_column("nvr_devices", column)

    op.drop_table("system_heartbeats")

    # TARTIB — `SNAPSHOT_DELETE_ORDER` bo'yicha, ya'ni FK zanjirida
    # BOLALARDAN ota-onaga. Ro'yxat `reversed(SNAPSHOT_TENANT_TABLES)` dan
    # hosil qilinmaydi va sabab reyestrning o'z docstringida: `alert_events`
    # FK zanjirida umuman turmaydi, ya'ni oddiy teskarilash noto'g'ri
    # natija berardi.
    for table in SNAPSHOT_DELETE_ORDER:
        op.drop_table(table)
