"""nvr_domain: NVR qurilmasi, uning siri, kameralar va kashfiyot yugurishlari

Revision ID: 0012
Revises: 0011
Create Date: 2026-08-03

3-FAZANING BIRINCHI MIGRATSIYASI. To'rtta tenant jadvali olib keladi va
shu bilan `tests/integration/test_market_delete_guard.py` ni ATAYIN
QIZARTIRADI — kaskadni kengaytirish `0013_market_delete_guard` da, AYNAN
SHU REJANING oynasida bajariladi (W0-7 ning ikkinchi yarmi, D-17/WR-02).

=============================================================================
BU MIGRATSIYADA QOTIB QOLADIGAN TO'RT QAROR:

1. `nvr_credentials` — ALOHIDA JADVAL VA AUDIT TRIGGERIDAN CHIQARILGAN.
   Ikki MUSTAQIL sabab (`03-PATTERNS.md` §S-6, SC#4):
     (a) `fn_audit_row()` `to_jsonb(NEW)` yozadi — Fernet SHIFRMATNI
         `audit_log.new_value` ga tushardi. Bu ochiq matn emas, lekin kalit
         buzilganda TARIXIY parollarni beradi va `audit_log` (append-only,
         o'chirib bo'lmaydigan) eng uzoq yashaydigan sir omboriga aylanardi.
     (b) `attach_audit_trigger()` `id uuid` PK talab qiladi; bu 1:1 jadvalda
         PK — `nvr_id`, ya'ni trigger texnik jihatdan ham ishlamaydi.
   Shuning uchun audit tsikli `NVR_AUDITED_TABLES` ustidan yuradi,
   `NVR_TENANT_TABLES` ustidan EMAS. Ikki ro'yxat — ikki xil savolga javob.

2. `cameras` DA `rtsp_url` USTUNI YO'Q (`03-RESEARCH.md` A.2). URL
   `host` + `rtsp_port` + `{channel_no}01/02` dan SOF FUNKSIYADA hosil
   bo'ladi. Ustun qo'shilsa NVR ning IP'si o'zgarganda 25 ta qator
   yangilanishi kerak bo'lardi (bittasi unutilsa jonli ko'rish jimgina eski
   manzilga urinardi), va `rtsp://user:pass@host/...` shakli sirni AUDIT
   TRIGGERI ULANGAN jadvalga olib kirardi.

3. `UNIQUE (market_id, nvr_id, channel_no)` — SC#2 NING DB KAFOLATI
   (T-03-15). Ilova qatlamidagi «avval tekshir, keyin yoz» IKKI PARALLEL
   skanda ikkalasini ham o'tkazib yuborardi (ikkalasi ham bo'sh holatni
   ko'radi) va kanal uchun ikkita qator tug'ilardi. 2-fazadagi
   `stall_code_registry` falsafasi bilan aynan bir xil: qoida ILOVADA emas,
   DB'da.

4. `nvr_discovery_runs` DAGI QISMAN UNIQUE bir vaqtda IKKINCHI skanni
   bloklaydi (T-03-16). Bu tozalik emas: ikki skan NVR ga ikki barobar yuk
   va ikki barobar `401` urinishi beradi — Hikvision hisobi QULFLANISHI
   mumkin va o'shanda butun bozor kamerasiz qoladi.
=============================================================================

⚠ KENGAYTMA KERAK EMAS VA `require_extension(...)` YOZILMAYDI.
`cidr` / `inet` / `jsonb` — PostgreSQL ning O'RNATILGAN tiplari. `0009` dagi
darvoza `btree_gist` uchun kerak edi (`EXCLUDE USING gist` `uuid` uchun
operator klassini o'sha kengaytmadan oladi). Bu yerda `ExcludeConstraint`
ham YO'Q — davr (range) tipi yo'q, ya'ni `0009_vendors.py:29-40` dagi
«Alembic uni ko'rmaydi» ogohlantirishi bu faylga TEGISHLI EMAS.
`op.execute("CREATE EXTENSION ...")` ham yozilmaydi (`sbozor_owner`
`NOCREATEDB` — `0009_vendors.py:118-136` da o'lchangan).
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

import sqlalchemy as sa
from alembic import op
from sbozor_core.models.nvr import (
    CAMERA_NVR_INDEX,
    CAMERA_STATUS_CHECK,
    DISCOVERY_ACTIVE_RUN_INDEX,
    DISCOVERY_RUN_ACTIVE_PREDICATE,
    DISCOVERY_RUN_STATUS_CHECK,
    TUNNEL_SUBNET_INDEX,
    TUNNEL_SUBNET_PREDICATE,
)
from sqlalchemy.dialects import postgresql as pg

from migrations.entities import NVR_AUDITED_TABLES, NVR_TENANT_TABLES
from migrations.entities.policies import owner_bootstrap_policy, tenant_policy
from migrations.helpers import (
    attach_audit_trigger,
    create_entity,
    detach_audit_trigger,
    drop_entity,
    enable_tenant_rls,
)

# revision identifiers, used by Alembic.
revision: str = "0012"
down_revision: str | Sequence[str] | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# ⚠ INDEKS NOMLARI VA PREDIKATLARI SHU YERDA E'LON QILINMAYDI — ular
#   `sbozor_core.models.nvr` dan IMPORT qilinadi (yuqoriga qarang).
#
#   Sabab O'LCHANGAN (03-03, birinchi urinish): `op.create_index(...)`
#   yolg'iz o'zi yetarli emas. Autogenerate model metadata'sini baza bilan
#   solishtiradi, ya'ni modelda e'lon qilinmagan indeks "o'chirilgan" deb
#   ko'rinadi va `test_autogenerate_is_empty` uchta `remove_index` bilan
#   qizaradi. Indeks IKKALA tomonda ham bo'lishi shart, nom va predikat esa
#   BITTA manbadan kelishi shart — aks holda ular jimgina ajralib ketardi
#   va `alembic check` har safar soxta diff berardi.


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
    # 1. nvr_devices — bozorning kameralarga YAGONA kirish nuqtasi.
    #
    #    PAROL BU YERDA YO'Q (2-band). `username` esa shu yerda va u sir
    #    EMAS: onboarding ekranida «qaysi hisob bilan ulanyapmiz?» savoliga
    #    javob berish kerak.
    #
    #    `rtsp_port` + `rtsp_port_assumed` — JUFTLIK va ularni bitta ustunga
    #    birlashtirib bo'lmaydi (`03-RESEARCH.md` A.2): «kashf etilgan 554»
    #    va «taxmin qilingan 554» bir xil raqam, lekin diagnostikada
    #    butunlay boshqa holat — ikkinchisi jonli ko'rish yiqilganda
    #    birinchi tekshiriladigan gumondor.
    #
    #    `host` da CHECK bilan «ommaviy IP» tekshiruvi ATAYIN YO'Q (C.11):
    #    u chegarada bajariladi. Xususiy diapazon ta'rifini DB'ga muzlatib
    #    qo'yish WireGuard topologiyasi o'zgarganda migratsiya talab qilardi.
    # ------------------------------------------------------------------
    op.create_table(
        "nvr_devices",
        _market_id(),
        _uuid_pk(),
        sa.Column("host", sa.Text(), nullable=False),
        sa.Column("port", sa.Integer(), server_default=sa.text("80"), nullable=False),
        sa.Column("use_tls", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("rtsp_port", sa.Integer(), nullable=True),
        sa.Column(
            "rtsp_port_assumed", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column("username", sa.Text(), nullable=False),
        sa.Column("model", sa.Text(), nullable=True),
        sa.Column("serial_number", sa.Text(), nullable=True),
        sa.Column("firmware_version", sa.Text(), nullable=True),
        sa.Column("device_type", sa.Text(), nullable=True),
        sa.Column("tunnel_subnet", pg.CIDR(), nullable=True),
        sa.Column("last_discovery_at", sa.DateTime(timezone=True), nullable=True),
        _created_at(),
        _updated_at(),
        sa.PrimaryKeyConstraint("id", name="pk_nvr_devices"),
        sa.ForeignKeyConstraint(
            ["market_id"], ["markets.id"], name="fk_nvr_devices_market_id_markets"
        ),
        # COMPOSITE FK NISHONI. Qolgan uchala jadval `(market_id, nvr_id)`
        # ga havola qiladi, ya'ni A bozorining kamerasi B bozorining NVR'iga
        # bog'lana OLMAYDI — bu RLS emas, SXEMA darajasidagi kafolat
        # (T-03-14). RLS chetlab o'tilishi mumkin bo'lgan har qanday yo'lda
        # (migratsiya, `psql`, xato yozilgan `SECURITY DEFINER`) FK turadi.
        sa.UniqueConstraint("market_id", "id", name="uq_nvr_devices_market_id_id"),
        sa.UniqueConstraint("market_id", "host", "port", name="uq_nvr_devices_market_id_host_port"),
        sa.CheckConstraint("port BETWEEN 1 AND 65535", name="ck_nvr_devices_port_range"),
        sa.CheckConstraint(
            "rtsp_port IS NULL OR rtsp_port BETWEEN 1 AND 65535",
            name="ck_nvr_devices_rtsp_port_range",
        ),
        sa.CheckConstraint("length(btrim(host)) > 0", name="ck_nvr_devices_host_not_blank"),
        sa.CheckConstraint("length(btrim(username)) > 0", name="ck_nvr_devices_username_not_blank"),
    )

    # ------------------------------------------------------------------
    # 2. nvr_credentials — SIR. AUDIT TRIGGERI BU JADVALGA ULANMAYDI.
    #
    #    Sabab fayl boshidagi 1-bandda (ikki mustaqil sabab). Bu yerda
    #    faqat oqibati qayd etiladi: pastdagi audit tsikli
    #    `NVR_AUDITED_TABLES` ustidan yuradi va bu jadval u yerda YO'Q.
    #
    #    `id uuid` USTUNI YO'Q va bu ataylab — birlamchi kalit `nvr_id`
    #    ning o'zi, ya'ni 1:1 munosabat SXEMADA (ilova qatlamida emas).
    #    Ikkinchi qator paydo bo'lsa «qaysi parol amaldagisi?» savoli
    #    javobsiz qolardi va ulanish tasodifiy natija berardi.
    #    `stall_code_registry` bilan aynan bir xil shakl va bir xil oqibat.
    #
    #    `created_at` YO'Q: qator NVR bilan birga tug'iladi va uning
    #    yaratilish vaqti `nvr_devices` da. `updated_at` esa YAGONA vaqt
    #    belgisi — rotatsiya qachon bo'lganini aynan shu ustun aytadi.
    # ------------------------------------------------------------------
    op.create_table(
        "nvr_credentials",
        _market_id(),
        sa.Column("nvr_id", pg.UUID(as_uuid=True), nullable=False),
        # Fernet TOKENI. Kalit env/secret dan keladi va DB'da HECH QACHON
        # saqlanmaydi (CLAUDE.md spec §5).
        sa.Column("password_encrypted", sa.LargeBinary(), nullable=False),
        sa.Column("key_version", sa.SmallInteger(), server_default=sa.text("1"), nullable=False),
        _updated_at(),
        sa.PrimaryKeyConstraint("nvr_id", name="pk_nvr_credentials"),
        sa.ForeignKeyConstraint(
            ["market_id"], ["markets.id"], name="fk_nvr_credentials_market_id_markets"
        ),
        sa.ForeignKeyConstraint(
            ["market_id", "nvr_id"],
            ["nvr_devices.market_id", "nvr_devices.id"],
            name="fk_nvr_credentials_market_id_nvr_id_nvr_devices",
        ),
        # Bo'sh `bytea` — «parol bor» degan YOLG'ON da'vo bo'lardi va
        # ulanish `401` bilan yiqilib, sabab noma'lum qolardi.
        sa.CheckConstraint(
            "octet_length(password_encrypted) > 0", name="ck_nvr_credentials_password_not_empty"
        ),
        sa.CheckConstraint("key_version > 0", name="ck_nvr_credentials_key_version_positive"),
    )

    # ------------------------------------------------------------------
    # 3. cameras — 4-fazadagi snapshot va 5-fazadagi zonaning tayanchi.
    #
    #    QATOR HECH QACHON O'CHIRILMAYDI (D-10): `is_archived` bayrog'i
    #    ishlatiladi. Yagona istisno — `market_delete_draft()` kaskadi
    #    (`0013`), ya'ni qoralama bozor (unda hech qanday tarix yo'q).
    #
    #    `name_overridden` va `is_archived` — BIR XIL SEMANTIKA: ikkalasi
    #    ham «admin qaroriga tegilmaydi» bayrog'i va qayta skan ikkalasini
    #    ham hurmat qiladi. Aks holda har kechagi skan adminning ishini
    #    bekor qilardi va u buni faqat ertasi kuni sezardi.
    # ------------------------------------------------------------------
    op.create_table(
        "cameras",
        _market_id(),
        _uuid_pk(),
        sa.Column("nvr_id", pg.UUID(as_uuid=True), nullable=False),
        # IDENTIFIKATSIYA KALITI (A.4) — NVR dagi jismoniy uya. Seriya
        # raqami/MAC/IP kalit EMAS: ular kamera almashtirilganda o'zgaradi.
        sa.Column("channel_no", sa.Integer(), nullable=False),
        sa.Column("stream_name", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("name_overridden", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        # Boshlang'ich qiymat `unknown` va bu ATAYIN: `offline` ni standart
        # qilish «kamera buzuq» degan YOLG'ON dalilni birinchi o'lchovdan
        # OLDIN yozardi.
        sa.Column("status", sa.Text(), server_default=sa.text("'unknown'"), nullable=False),
        sa.Column("is_archived", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("has_substream", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        # KUZATILADIGAN atributlar — kalit emas. O'zgarishi audit triggeri
        # orqali yoziladi va 5-fazada «zona nega yaroqsiz bo'lib qoldi?»
        # savoliga javob beradi.
        sa.Column("source_ip", pg.INET(), nullable=True),
        sa.Column("source_model", sa.Text(), nullable=True),
        # HECH QACHON yangilanmaydi / HAR SKANDA yangilanadi — juftlik
        # «kanal qachon paydo bo'ldi» va «oxirgi marta qachon ko'rindi»
        # savollarini AJRATADI.
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
        _created_at(),
        _updated_at(),
        sa.PrimaryKeyConstraint("id", name="pk_cameras"),
        sa.ForeignKeyConstraint(["market_id"], ["markets.id"], name="fk_cameras_market_id_markets"),
        sa.ForeignKeyConstraint(
            ["market_id", "nvr_id"],
            ["nvr_devices.market_id", "nvr_devices.id"],
            name="fk_cameras_market_id_nvr_id_nvr_devices",
        ),
        sa.UniqueConstraint("market_id", "id", name="uq_cameras_market_id_id"),
        # ⚠ SC#2 NING YAGONA DB KAFOLATI (fayl boshidagi 3-band, T-03-15).
        #   Ustunlar TARTIBI ham ahamiyatli: `market_id` BIRINCHI, ya'ni
        #   konstrayt ostidagi indeks tenant invarianti #5 dan
        #   (`test_tenant_indexes_lead_with_market_id`) o'tadi.
        #   Buzilganda SQLSTATE `23505`; 03-05 dagi upsert aynan shu
        #   konstraytga `ON CONFLICT` qiladi.
        sa.UniqueConstraint(
            "market_id", "nvr_id", "channel_no", name="uq_cameras_market_id_nvr_id_channel_no"
        ),
        # go2rtc'dagi oqim nomi — GLOBAL noyob (D.13). Sabab va tenant
        # invariantidan istisno qilinishi `TUNNEL_SUBNET_INDEX` bilan bir
        # joyda, pastdagi 5-bandda tushuntirilgan.
        sa.UniqueConstraint("stream_name", name="uq_cameras_stream_name"),
        sa.CheckConstraint("channel_no > 0", name="ck_cameras_channel_no_positive"),
        sa.CheckConstraint(CAMERA_STATUS_CHECK, name="ck_cameras_status_allowed"),
        sa.CheckConstraint("length(btrim(name)) > 0", name="ck_cameras_name_not_blank"),
        sa.CheckConstraint(
            "length(btrim(stream_name)) > 0", name="ck_cameras_stream_name_not_blank"
        ),
    )
    # «Shu NVR ning kameralari» — kashfiyot upsert'i va kamera ro'yxatining
    # asosiy so'rovi. `uq_cameras_market_id_nvr_id_channel_no` bu savolga
    # javob BERADI (prefiks mos keladi), lekin u UNIQUE va kelajakda
    # o'zgarishi mumkin; ro'yxat so'rovi esa alohida, barqaror indeksga
    # tayanadi. `market_id` bilan BOSHLANADI (tenant invarianti #5).
    op.create_index(CAMERA_NVR_INDEX, "cameras", ["market_id", "nvr_id"])

    # ------------------------------------------------------------------
    # 4. nvr_discovery_runs — SC#2 ni KUZATILADIGAN qiladigan yozuv.
    #
    #    Kashfiyot HTTP so'rovi ICHIDA ishlamaydi (`03-RESEARCH.md` E.16:
    #    ~29 ISAPI so'rovi ≈ 17–60 s, `uvicorn --workers 1` esa butun
    #    API'ni bloklardi) — u JOB da ishlaydi va frontend `id` bo'yicha
    #    poll qiladi.
    #
    #    `channels_*` sanoqlari NULLABLE: yugurish HALI tugamagan bo'lishi
    #    mumkin. Nolga tenglashtirish «0 ta kanal topildi» degan YOLG'ON
    #    natija berardi va `queued` holat muvaffaqiyatsiz skandan farq
    #    qilmasdi.
    #
    #    `error_code` — KOD, MATN EMAS (A.3 taksonomiyasi): frontend uni
    #    uch tilga tarjima qiladi (CLAUDE.md «3 til majburiy»). Matn
    #    saqlansa u bitta tilda muzlab qolardi.
    # ------------------------------------------------------------------
    op.create_table(
        "nvr_discovery_runs",
        _market_id(),
        _uuid_pk(),
        sa.Column("nvr_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("channels_found", sa.Integer(), nullable=True),
        sa.Column("channels_added", sa.Integer(), nullable=True),
        sa.Column("channels_marked_offline", sa.Integer(), nullable=True),
        sa.Column("error_code", sa.Text(), nullable=True),
        # ⚠ Xom diagnostika YOZISHDAN OLDIN `mask_sensitive` DAN O'TADI
        #   (`03-PATTERNS.md` §S-7): filtr faqat KALIT nomiga qaraydi, ya'ni
        #   parol bu yerga NOMLANGAN kalit sifatida tushishi shart,
        #   formatlangan matn ichida hech qachon.
        sa.Column("error_detail", pg.JSONB(), nullable=True),
        # `users.id` ga FK ATAYIN YO'Q: `users` — GLOBAL jadval, unda
        # `market_id` yo'q va composite FK qurib bo'lmaydi; oddiy FK esa
        # foydalanuvchi o'chirilganda kashfiyot tarixini ham olib ketardi.
        # `NULL` = fon/tizim yugurishi (`ActorKind.SYSTEM`).
        sa.Column("triggered_by", pg.UUID(as_uuid=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_nvr_discovery_runs"),
        sa.ForeignKeyConstraint(
            ["market_id"], ["markets.id"], name="fk_nvr_discovery_runs_market_id_markets"
        ),
        sa.ForeignKeyConstraint(
            ["market_id", "nvr_id"],
            ["nvr_devices.market_id", "nvr_devices.id"],
            name="fk_nvr_discovery_runs_market_id_nvr_id_nvr_devices",
        ),
        sa.UniqueConstraint("market_id", "id", name="uq_nvr_discovery_runs_market_id_id"),
        sa.CheckConstraint(DISCOVERY_RUN_STATUS_CHECK, name="ck_nvr_discovery_runs_status_allowed"),
        sa.CheckConstraint(
            "finished_at IS NULL OR finished_at >= started_at",
            name="ck_nvr_discovery_runs_finished_after_started",
        ),
        sa.CheckConstraint(
            "channels_found IS NULL OR channels_found >= 0",
            name="ck_nvr_discovery_runs_channels_found_non_negative",
        ),
        sa.CheckConstraint(
            "channels_added IS NULL OR channels_added >= 0",
            name="ck_nvr_discovery_runs_channels_added_non_negative",
        ),
        sa.CheckConstraint(
            "channels_marked_offline IS NULL OR channels_marked_offline >= 0",
            name="ck_nvr_discovery_runs_channels_marked_offline_non_negative",
        ),
    )

    # ------------------------------------------------------------------
    # 5. QISMAN UNIQUE INDEKSLAR — IKKALASI HAM `op.create_table` GA
    #    SIG'MAYDI (`postgresql_where` faqat `create_index` da bor).
    # ------------------------------------------------------------------
    #
    # (a) BIR VAQTDA IKKI KASHFIYOT BO'LOLMAYDI (T-03-16).
    #     Predikat `DiscoveryRunStatus` dan HOSILA (`_ACTIVE_RUN_PREDICATE`).
    #     Yakunlangan yugurishlar (`succeeded`/`failed`) indeksga TUSHMAYDI,
    #     ya'ni tarix cheksiz to'planaveradi va faqat FAOL qator qulflanadi.
    #     API qatlami 409 ni AYNAN shu konstrayt buzilishidan hosil qiladi
    #     (03-06) — «tekshir-keyin-yoz» poygasi yo'q.
    #     `market_id` bilan BOSHLANADI (tenant invarianti #5).
    op.create_index(
        DISCOVERY_ACTIVE_RUN_INDEX,
        "nvr_discovery_runs",
        ["market_id", "nvr_id"],
        unique=True,
        postgresql_where=sa.text(DISCOVERY_RUN_ACTIVE_PREDICATE),
    )
    #
    # (b) `tunnel_subnet` — BOZORLAR ARO (GLOBAL) NOYOB (D-07, T-03-19).
    #
    #     ⚠ BU INDEKS `market_id` BILAN BOSHLANMAYDI VA BU ATAYIN — u shu
    #     migratsiyadagi YAGONA tenant chegarasidan tashqaridagi cheklov.
    #     Sabab mahsulot darajasida: ko'p tarmoq `192.168.1.0/24` ishlatadi.
    #     Ikkita bozor bir xil subnet e'lon qilsa VPS ning marshrut jadvali
    #     chalkashadi va A bozorining trafigi B ga ketishi mumkin — ya'ni
    #     tenant izolyatsiyasi TARMOQ darajasida buzilardi. Noyoblikni
    #     `(market_id, tunnel_subnet)` ga tushirish bu himoyani BUTUNLAY
    #     yo'q qilardi (har bozor o'z ichida noyob bo'lardi, to'qnashuv esa
    #     aynan bozorlar ORASIDA yuz beradi).
    #
    #     Shuning uchun indeks nomi `tests/tenancy/test_meta.py::
    #     INDEX_EXCEPTIONS` ga sabab bilan qo'shilgan.
    #
    #     `1:1 NAT` yechimi ATAYIN implement qilinmaydi (D-07): to'qnashuvda
    #     onboarding aniq xato beradi va ma'mur boshqa subnet tanlaydi.
    #     Qisman (`IS NOT NULL`), chunki subnet HALI e'lon qilinmagan
    #     qurilmalar ko'p bo'lishi normal va ular bir-biriga xalaqit
    #     bermasligi kerak.
    op.create_index(
        TUNNEL_SUBNET_INDEX,
        "nvr_devices",
        ["tunnel_subnet"],
        unique=True,
        postgresql_where=sa.text(TUNNEL_SUBNET_PREDICATE),
    )

    # ------------------------------------------------------------------
    # 6. RLS. TARTIB MAJBURIY: ENABLE + FORCE + GRANT -> policy (Pitfall 10).
    #    `alembic-utils` `ENABLE`/`FORCE` ni BILMAYDI — ularsiz policy HECH
    #    QANDAY ta'sir ko'rsatmaydi va jadval hamma uchun ochiq bo'ladi.
    #
    #    TSIKL `NVR_TENANT_TABLES` USTIDAN — TO'RTALA jadval, `nvr_credentials`
    #    ham. Sir jadvali RLS ostida bo'lishi SHART: audit istisnosi
    #    (7-band) uni tenant izolyatsiyasidan CHIQARMAYDI.
    # ------------------------------------------------------------------
    for table in NVR_TENANT_TABLES:
        enable_tenant_rls(table)
        create_entity(tenant_policy(table))
        create_entity(owner_bootstrap_policy(table))

    # ------------------------------------------------------------------
    # 7. Audit — ATAYIN BOSHQA RO'YXAT USTIDAN (fayl boshidagi 1-band).
    #
    #    `NVR_AUDITED_TABLES` = (`nvr_devices`, `cameras`).
    #    `nvr_credentials` YO'Q — shifrmatn `audit_log` ga tushmasligi uchun
    #    (SC#4) VA `id uuid` PK bo'lmagani uchun.
    #    `nvr_discovery_runs` ham YO'Q, lekin BOSHQA sababdan: u hodisa
    #    jurnali va faqat qo'shiladi — audit uning ikkinchi nusxasini
    #    yozardi. Kashfiyotning ishga tushishi ILOVA qatlamida auditga
    #    tushadi (`03-PATTERNS.md` §S-6).
    # ------------------------------------------------------------------
    for table in NVR_AUDITED_TABLES:
        attach_audit_trigger(table)


def downgrade() -> None:
    """Downgrade schema."""
    for table in reversed(NVR_AUDITED_TABLES):
        detach_audit_trigger(table)

    for table in reversed(NVR_TENANT_TABLES):
        drop_entity(owner_bootstrap_policy(table))
        drop_entity(tenant_policy(table))

    op.drop_index(TUNNEL_SUBNET_INDEX, table_name="nvr_devices")
    op.drop_index(DISCOVERY_ACTIVE_RUN_INDEX, table_name="nvr_discovery_runs")
    op.drop_index(CAMERA_NVR_INDEX, table_name="cameras")

    # TARTIB — FK bo'yicha BOLALARDAN ota-onaga: uchala bolasi ham
    # `nvr_devices` ga composite FK bilan tayanadi.
    op.drop_table("nvr_discovery_runs")
    op.drop_table("cameras")
    op.drop_table("nvr_credentials")
    op.drop_table("nvr_devices")
