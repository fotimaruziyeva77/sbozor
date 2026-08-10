"""`alembic-utils` entity reyestri — `env.py` shu ro'yxatni ro'yxatga oladi.

`register_entities(ALL_ENTITIES)` autogenerate'ga bu obyektlarni kuzatishni
buyuradi: fabrikaning matni o'zgarsa, keyingi `alembic revision
--autogenerate` `op.replace_entity(...)` ni o'zi taklif qiladi va policy
ta'rifi bazadan ajralib qolmaydi.

DIQQAT: `alembic-utils` `ENABLE`/`FORCE ROW LEVEL SECURITY` ni BILMAYDI —
u faqat `CREATE POLICY` ni boshqaradi. Bayroqlar `migrations/helpers.py`
dagi `enable_tenant_rls()` orqali qo'yiladi (Pitfall 10).
"""

from __future__ import annotations

from typing import Any, Final

from migrations.entities.functions import (
    ALL_FUNCTIONS,
    AUTH_SUPPORT_FUNCTIONS,
    MARKET_DOMAIN_FUNCTIONS,
    OCCUPANCY_FUNCTIONS,
    PLATFORM_AUDIT_FUNCTIONS,
    SNAPSHOT_FUNCTIONS,
    USER_ADMIN_FUNCTIONS,
)
from migrations.entities.policies import (
    audit_append_policy,
    audit_read_platform_policy,
    audit_read_policy,
    markets_policy,
    owner_bootstrap_policy,
    tenant_policy,
)
from migrations.entities.triggers import ALL_TRIGGER_FUNCTIONS

__all__ = [
    "ALL_ENTITIES",
    "ALL_RLS_TABLES",
    "ALL_TENANT_TABLES",
    "CALENDAR_TENANT_TABLES",
    "IDEMPOTENT_GET_OR_CREATE_MEASURED_AT",
    "IDEMPOTENT_GET_OR_CREATE_SUPPORTED",
    "MARKET_DOMAIN_TENANT_TABLES",
    "NVR_AUDITED_TABLES",
    "NVR_TENANT_TABLES",
    "OCCUPANCY_AUDITED_TABLES",
    "OCCUPANCY_DELETE_ORDER",
    "OCCUPANCY_TENANT_TABLES",
    "RLS_TABLES",
    "SNAPSHOT_AUDITED_TABLES",
    "SNAPSHOT_DELETE_ORDER",
    "SNAPSHOT_TENANT_TABLES",
    "TEMPORAL_TENANT_TABLES",
    "TENANT_TABLES",
    "VENDOR_TENANT_TABLES",
]

TENANT_TABLES: tuple[str, ...] = ("user_market_roles", "refresh_tokens")
"""`0001_identity` YARATGAN tenant jadvallari — BU RO'YXAT MUZLATILGAN.

⚠ YANGI JADVAL BU YERGA QO'SHILMAYDI. `migrations/versions/0001_identity.py`
shu tuple ustidan TSIKL qiladi (`enable_tenant_rls(table)`,
`create_entity(tenant_policy(table))`), ya'ni qiymatni kengaytirish nol
holatdan qilingan migratsiyani `relation "stalls" does not exist` bilan
yiqitardi — 0001 hali mavjud bo'lmagan jadvalga RLS qo'ymoqchi bo'lardi.

Yangi jadvallar quyidagi MIGRATSIYA-SCOPE'li tuple'larga qo'shiladi
(`MARKET_DOMAIN_TENANT_TABLES`, `TEMPORAL_TENANT_TABLES`,
`VENDOR_TENANT_TABLES`, `CALENDAR_TENANT_TABLES`), ularning yig'indisi esa
`ALL_TENANT_TABLES` — autogenerate va policy reyestri aynan shundan
quriladi.
"""

RLS_TABLES: tuple[str, ...] = ("markets", *TENANT_TABLES)
"""`0001_identity` da RLS yoqilgan jadvallar — BU RO'YXAT HAM MUZLATILGAN.

Kengaytirish o'rniga `ALL_RLS_TABLES` ishlatiladi (pastda).

`markets` maxsus policy bilan.

`audit_log` bu ro'yxatda ATAYIN YO'Q: unga `owner_bootstrap` policy'si
BERILMASLIGI shart. O'sha policy `FOR ALL ... USING (true)` bo'lgani uchun
egaga `UPDATE`/`DELETE` da qatorlarni ko'rsatib qo'yardi va o'zgarmaslikning
2-qatlamini bir zarbada yo'q qilardi (`migrations/versions/0002_audit.py`).

DIQQAT — `audit_read_platform` (0005) BUNGA ZID EMAS. U ham EGAGA
mo'ljallangan (`TO sbozor_owner`), lekin `FOR SELECT`: `UPDATE`/`DELETE`
uchun baribir birorta policy paydo bo'lmaydi, ya'ni 2-qatlam o'zgarishsiz
qoladi. Butun farq komanda bandida — uni kelajakda `FOR ALL` ga
"soddalashtirish" o'zgarmaslikni JIMGINA yo'q qilardi, shuning uchun
`test_audit_read_platform_is_owner_only` komandani `SELECT` ga qulflaydi.
"""


# ===========================================================================
# 2-FAZA — MIGRATSIYA-SCOPE'LI TENANT JADVALLARI
# ===========================================================================
#
# Reyestr MIGRATSIYA bo'yicha bo'lingan, chunki har bir tuple ustidan AYNAN
# uni yaratgan migratsiya tsikl qiladi. Bitta katta ro'yxat bo'lganda
# 0001 hali mavjud bo'lmagan jadvalga RLS qo'ymoqchi bo'lardi (yuqoriga
# qarang), yoki har bir migratsiya "mening ulushim qaysi" degan savolni
# qo'lda hal qilardi.

MARKET_DOMAIN_TENANT_TABLES: tuple[str, ...] = (
    "market_profile",
    "zones",
    "stall_categories",
    "stalls",
    "stall_code_registry",
)
"""`0007_market_domain` yaratadigan tenant jadvallari (MARKET-01/02)."""

TEMPORAL_TENANT_TABLES: tuple[str, ...] = (
    "stall_category_periods",
    "tariffs",
)
"""`0008_temporal` — VORIS modelidagi ikkita tarix jadvali (D-04/D-06, MARKET-03).

Alohida migratsiyada, chunki ular `stalls` va `stall_categories` ga composite
FK bilan tayanadi va o'zgarmaslik triggerlarini ham olib keladi.
"""

VENDOR_TENANT_TABLES: tuple[str, ...] = (
    "vendors",
    "stall_assignments",
)
"""`0009_vendors` — sotuvchilar va biriktirish davrlari (MARKET-04).

Alohida migratsiyada, chunki `stall_assignments` `btree_gist` kengaytmasini
talab qiladi va migratsiya `require_extension("btree_gist")` bilan
boshlanadi (Pitfall 1).
"""

CALENDAR_TENANT_TABLES: tuple[str, ...] = ("market_calendar_exceptions",)
"""`0010_calendar` — yopiq kun istisnolari (MARKET-05, D-18)."""


# ===========================================================================
# 3-FAZA — NVR DOMENI
# ===========================================================================

NVR_TENANT_TABLES: tuple[str, ...] = (
    "nvr_devices",
    "nvr_credentials",
    "cameras",
    "nvr_discovery_runs",
)
"""`0012_nvr_domain` yaratadigan tenant jadvallari (CAM-01/CAM-08).

TARTIB — FK bo'yicha OTA-ONADAN bolalarga: `nvr_devices` birinchi, chunki
qolgan uchtasi unga composite FK `(market_id, nvr_id)` bilan tayanadi.
`0012` shu ro'yxat ustidan `enable_tenant_rls` + `tenant_policy` +
`owner_bootstrap_policy` tsiklini bajaradi, `downgrade()` esa
`reversed(...)` bilan yuradi.

BU RO'YXAT AUDIT UCHUN EMAS. Trigger faqat `NVR_AUDITED_TABLES` ga ulanadi
(pastda) va farq ATAYIN — `nvr_credentials` RLS ostida bo'lishi SHART, audit
triggeri ostida esa BO'LMASLIGI shart.

QARORLAR (`03-CONTEXT.md`):
  * D-07 — `nvr_devices.tunnel_subnet` bozorlar ARO noyob. Bu shu domendagi
    YAGONA tenant chegarasidan tashqaridagi cheklov va u `0012` da qisman
    UNIQUE indeks sifatida, sababi bilan yoziladi.
  * D-10 — kamera SOFT-DELETE (`cameras.is_archived`). Qattiq `DELETE`
    faqat `market_delete_draft()` kaskadida (qoralama bozor).
"""

NVR_AUDITED_TABLES: tuple[str, ...] = ("nvr_devices", "cameras")
"""`0012_nvr_domain` da `attach_audit_trigger()` ULANADIGAN jadvallar.

⚠ `nvr_credentials` BU RO'YXATDA ATAYIN YO'Q — ikki mustaqil sabab
(`sbozor_core.schema_contract.AUDITED_TABLES` docstringining to'rtinchi
bandi va `sbozor_core.models.nvr.NvrCredential` docstringi):

  (a) `fn_audit_row()` `to_jsonb(NEW)` yozadi -> Fernet shifrmatni
      `audit_log` ga tushardi va kalit buzilganda TARIXIY parollarni berardi;
  (b) `attach_audit_trigger()` `id uuid` PK talab qiladi, bu 1:1 jadvalda
      esa PK — `nvr_id`.

`nvr_discovery_runs` ham ro'yxatda YO'Q, lekin BOSHQA sababdan: u
hodisa jurnali va faqat QO'SHILADI (tahrirlanmaydi) — uning ustiga audit
qo'yish `audit_log` ga o'sha ma'lumotning ikkinchi nusxasini yozardi.
Kashfiyotning ishga tushishi va yakuni ILOVA qatlamida auditga tushadi
(`03-PATTERNS.md` §S-6).

Ro'yxat ALOHIDA, chunki `0012` ikki xil tsikl qiladi: RLS `NVR_TENANT_TABLES`
bo'yicha, audit esa shu yerdan. Bitta ro'yxat bo'lganda istisnoni
migratsiyaning ichida `if table != "nvr_credentials"` shaklida yozishga
to'g'ri kelardi — ya'ni qaror kodning ichiga yashiringan bo'lardi.
"""

# ===========================================================================
# 4-FAZA — SNAPSHOT QUVURI
# ===========================================================================

SNAPSHOT_TENANT_TABLES: tuple[str, ...] = (
    "snapshot_schedules",
    "snapshot_schedule_slots",
    "capture_runs",
    "snapshots",
    "alert_events",
)
"""`0014_snapshot_domain` yaratadigan tenant jadvallari (CAM-04/05/06/07).

TARTIB — FK bo'yicha OTA-ONADAN bolalarga, `NVR_TENANT_TABLES` bilan aynan
bir xil qoida:
  * `snapshot_schedule_slots` -> `snapshot_schedules` ga `(market_id, schedule_id)`;
  * `capture_runs`            -> `cameras` ga `(market_id, camera_id)` (3-fazadan);
  * `snapshots`               -> `capture_runs` ga `(market_id, capture_run_id)`.
`0014` shu ro'yxat ustidan `enable_tenant_rls` + `tenant_policy` +
`owner_bootstrap_policy` tsiklini bajaradi, `downgrade()` esa
`reversed(...)` bilan yuradi.

✅ RO'YXAT `ALL_TENANT_TABLES` GA QO'SHILDI (`04-03` / T2, `0014` bilan bir
commitda). U `04-01` da ATAYIN qoldirilgan edi — sabab o'sha konstantaning
yonidagi izohda (o'lchangan `UndefinedTable`) — va qarzni
`test_snapshot_registries_are_self_consistent` mexanik ushlab turdi.

BU RO'YXAT AUDIT UCHUN EMAS. Trigger faqat `SNAPSHOT_AUDITED_TABLES` ga
ulanadi (pastda) va farq ATAYIN — beshala jadval RLS ostida bo'lishi SHART,
audit triggeri ostida esa faqat ikkitasi.

`alert_events` — TENANT jadvali (`market_id NOT NULL`), `04-PATTERNS.md`
§S-1. `04-RESEARCH.md` §E.13 uni `GLOBAL_TABLES` deb atagan, lekin
`GLOBAL_TABLES` ning ta'rifi — «`market_id` ustuni BO'LMASLIGI kutilgan
jadvallar», research esa unga `market_id` beradi: ikkisi bir vaqtda to'g'ri
bo'la olmaydi. Tenant varianti tanlandi, chunki UI ogohlantirishlarni BOZOR
sahifasida ko'rsatadi. `GLOBAL_TABLES` ga faqat `system_heartbeats` qo'shildi
(unda `market_id` ustuni yo'q).

QARORLAR (`04-CONTEXT.md`):
  * D-16 — `snapshots` da `UNIQUE (id, is_billable)` langari; `is_billable`
    `GENERATED ALWAYS AS (quality_verdict = 'ok') STORED`. Bu shakl W0-1
    zondi bilan HAQIQIY `postgres:18.4` da O'LCHANGAN
    (`tests/fixtures/billable_probe.py`, natija: qo'llab-quvvatlanadi).
  * D-05 — jadval kun o'rtasida o'zgartirilsa BUGUNGI rejaga ta'sir
    qilmaydi: reja kunning birinchi tikida materializatsiya qilinadi.
"""

SNAPSHOT_AUDITED_TABLES: tuple[str, ...] = ("snapshot_schedules", "snapshot_schedule_slots")
"""`0014_snapshot_domain` da `attach_audit_trigger()` ULANADIGAN jadvallar.

⚠ UCHTASI ATAYIN CHIQARILGAN va sabab `nvr_discovery_runs` niki bilan bir
xil sinfda, lekin unga IKKINCHI (mustaqil) argument qo'shiladi:

  * `capture_runs`, `snapshots`, `alert_events` — HODISA JURNALLARI: ular
    faqat QO'SHILADI (odam tomonidan tahrirlanmaydi), ya'ni audit ularning
    ustiga o'sha ma'lumotning IKKINCHI NUSXASINI yozardi;
  * HAJM: 175 qator/kun/bozor × har holat o'tishi
    (`pending`->`running`->`succeeded`) ≈ kuniga 525 audit qatori BITTA
    bozordan. O'nta bozorda bu yiliga ~1.9 mln qator — `audit_log`
    append-only, ya'ni u hech qachon kichraymaydi.

IZ YO'QOLMAYDI va bu shu qarorning sharti: JADVAL o'zgarishi
(`snapshot_schedules` — kim jadvalni o'zgartirdi) auditda, KUNLIK
YUGURISHLAR esa `capture_runs` ning O'ZIDA tarixga ega (`status`,
`attempt_count`, `error_code`, vaqt tamg'alari).

Ro'yxat ALOHIDA, chunki `0014` ikki xil tsikl qiladi: RLS
`SNAPSHOT_TENANT_TABLES` bo'yicha, audit esa shu yerdan.
"""

SNAPSHOT_DELETE_ORDER: tuple[str, ...] = (
    "snapshots",
    "capture_runs",
    "snapshot_schedule_slots",
    "snapshot_schedules",
    "alert_events",
)
"""`market_delete_draft()` kaskadiga qo'shiladigan tartib (W0-6, `0015`).

⚠ IKKI FAKT, IKKALASI HAM MAJBURIY:

**(a) Tartib BOLALARDAN OTA-ONAGA** — ya'ni bu `SNAPSHOT_TENANT_TABLES`
ning oddiy teskarisi EMAS va uni `reversed(...)` bilan hosil qilib
bo'lmaydi: `alert_events` FK zanjirida umuman turmaydi (u hech kimga
tayanmaydi va unga hech kim tayanmaydi), shuning uchun uning o'rni
ixtiyoriy va oxirida turadi. Ro'yxat ALOHIDA e'lon qilinishining butun
sababi shu — hosila qiymat noto'g'ri natija berardi.

**(b) BUTUN BLOK MAVJUD NVR BLOKIDAN OLDIN TURISHI SHART.** `capture_runs`
`cameras` ga kompozit FK `(market_id, camera_id)` bilan tayanadi,
`cameras` esa `MARKET_DELETE_DRAFT` ning BIRINCHI `DELETE` i
(`migrations/entities/functions.py`). Blok NVR blokidan keyin qo'yilsa
kaskad o'z chet el kalitiga urilib yiqilardi — va bu faqat qoralama
bozorni o'chirmoqchi bo'lgan admin ekranida ko'rinardi.

`0015` va `MARKET_DELETE_DRAFT` kengaytmasi qiymatni SHUNDAN oladi
(`04-03` / T3), reyestr esa ATAYIN `0014` dan OLDIN yoziladi: shunda
`test_cascade_covers_every_table_referencing_markets` qizargan zahoti
tuzatish ro'yxati tayyor turadi.
"""

# ===========================================================================
# 5-FAZA — BANDLIK DOMENI (KAMERA ZONALARI, CV VA NAZORATCHI TASDIG'I)
# ===========================================================================

OCCUPANCY_TENANT_TABLES: tuple[str, ...] = (
    "camera_zones",
    "occupancy_events",
    "audit_rounds",
    "review_assignments",
    "zone_reviews",
    "stall_slot_occupancy",
)
"""`0018_occupancy_domain` yaratadigan tenant jadvallari (AI-01…AI-06).

TARTIB — FK bo'yicha OTA-ONADAN bolalarga, `SNAPSHOT_TENANT_TABLES` bilan
aynan bir xil qoida:
  * `camera_zones`         -> `cameras` VA `stalls` ga (IKKITA kompozit FK);
  * `occupancy_events`     -> `snapshots (id, is_billable)` va `camera_zones` ga;
  * `review_assignments`   -> `occupancy_events` va `audit_rounds` ga;
  * `zone_reviews`         -> `review_assignments` ga;
  * `stall_slot_occupancy` -> `stalls` va `occupancy_events` ga.
`0018` shu ro'yxat ustidan `enable_tenant_rls` + `tenant_policy` +
`owner_bootstrap_policy` tsiklini bajaradi, `downgrade()` esa
`reversed(...)` bilan yuradi.

⚠ RO'YXAT `ALL_TENANT_TABLES` GA HALI QO'SHILMAGAN va bu ATAYIN — sabab
o'sha konstantaning yonidagi izohda (`04-01` da O'LCHANGAN `UndefinedTable`).
Qo'shish `0018` BILAN BIR COMMITDA bajariladi (`05-05` / T2), qarzni esa
`test_meta.py::test_occupancy_registries_are_self_consistent` mexanik ushlab
turadi: shart BAZAGA bog'langan, ya'ni jadval tug'ilgan zahoti darvoza O'ZI
QUROLLANADI.

BU RO'YXAT AUDIT UCHUN EMAS. Trigger faqat `OCCUPANCY_AUDITED_TABLES` ga
ulanadi (pastda) va farq ATAYIN — oltala jadval RLS ostida bo'lishi SHART,
audit triggeri ostida esa faqat ikkitasi.

QARORLAR (`05-CONTEXT.md`):
  * D-06 — NOM TO'QNASHUVI: jadval `camera_zones`, `zones` EMAS. `zones`
    2-fazada bozor hududlari uchun BAND (`models/market.py::Zone`) va unga
    `stalls.zone_id NOT NULL` tayanadi, ya'ni `zones` deb nomlash
    migratsiyani to'qnashtirardi. Router ham `camera_zones.py`
    (`zones.py` ga TEGILMAYDI), frontend papkasi ham `camera-zones/`.
  * D-21 — BILLING LANGARI: `occupancy_events` 4-fazaning strukturaviy
    langariga osiladi — `FOREIGN KEY (snapshot_id, snapshot_is_billable)
    REFERENCES snapshots (id, is_billable)` + `CHECK (snapshot_is_billable)`.
    Shunda yaroqsiz kadr (`quality_verdict <> 'ok'`) bandlik dalilini
    UMUMAN yarata olmaydi — DB rad etadi, intizom emas. Langarning O'ZI
    4-fazada HAQIQIY `postgres:18.4` da o'lchangan
    (`tests/fixtures/billable_probe.py`, `BILLABLE_ANCHOR_SUPPORTED = true`)
    va `uq_snapshots_billable_anchor` `INDEX_EXCEPTIONS` da shu sabab bilan
    turadi. 5-faza langarni FAQAT ISHLATADI, qayta o'lchamaydi (§S-4).
  * D-12 — `occupancy_events` O'ZGARMAS: AI natijasi hech qachon
    tahrirlanmaydi, qayta ishlash YANGI qator yozadi
    (`UNIQUE (market_id, snapshot_id, camera_zone_id, model_version)`).
"""

OCCUPANCY_AUDITED_TABLES: tuple[str, ...] = ("camera_zones", "zone_reviews")
"""`0018_occupancy_domain` da `attach_audit_trigger()` ULANADIGAN jadvallar.

⚠ AUDIT ASSIMETRIYASI — TO'RTTASI ATAYIN CHIQARILGAN.

`occupancy_events` CHIQARILADI va sabab `SNAPSHOT_AUDITED_TABLES` niki bilan
bir sinfda, lekin bu yerda IKKALA argument ham KUCHLIROQ:

  * HAJM: 175 kadr/kun/bozor × ~30 zona ≈ **5 000 qator/kun/bozor** — bu
    4-fazadagi ~525 audit qatorining o'n barobari. `audit_log` append-only,
    ya'ni u hech qachon kichraymaydi;
  * O'ZGARMASLIK: jadval D-12 bo'yicha SHARTSIZ o'zgarmas (`0018` unga
    o'zgarmaslik triggerini qo'yadi). **O'zgarmas jadval uchun audit
    ma'nosiz** — u faqat INSERT ni ko'rardi va bu o'sha ma'lumotning
    IKKINCHI NUSXASI bo'lardi. 4-fazada bu argument «odam tahrirlamaydi»
    shaklida edi; bu yerda u konventsiya emas, DB darajasidagi FAKT.

`audit_rounds`, `review_assignments` ham chiqarilgan: birinchisi tortish
FAKTINI (`frame_size`, `frame_predicate_hash`, `drawn_at`) o'z ichida
MUZLATIB saqlaydi, ikkinchisi esa navbat yozuvi — ikkalasi ham hodisa
jurnali sinfida.

`zone_reviews` esa AUDITDA BO'LADI va bu ro'yxatning butun mazmuni:
u INSONNING moliyaviy oqibatli qarori (nazoratchining verdikti kunlik
patta hisobini o'zgartiradi), ya'ni `schema_contract.AUDITED_TABLES` dagi
`tariffs` / `stall_assignments` bilan BIR OILADA. `camera_zones` ham
auditda: poligon jimgina siljitilsa o'sha rastaning «band, lekin
to'lovsiz» dalili YO'QOLADI — `cameras.is_archived` bilan aynan bir xil
nazoratni jimgina o'chirish yo'li.

Ro'yxat ALOHIDA, chunki `0018` ikki xil tsikl qiladi: RLS
`OCCUPANCY_TENANT_TABLES` bo'yicha, audit esa shu yerdan.
"""

OCCUPANCY_DELETE_ORDER: tuple[str, ...] = (
    "stall_slot_occupancy",
    "zone_reviews",
    "review_assignments",
    "audit_rounds",
    "occupancy_events",
    "camera_zones",
)
"""`market_delete_draft()` kaskadiga qo'shiladigan tartib (W0-6, `0019`).

⚠ IKKI FAKT, IKKALASI HAM MAJBURIY:

**(a) RO'YXAT LITERAL — HOSILA EMAS.** Bugun u tasodifan
`tuple(reversed(OCCUPANCY_TENANT_TABLES))` bilan USTMA-UST TUSHADI, chunki
bu domenda FK zanjiridan chetda turgan jadval YO'Q (4-fazada `alert_events`
aynan shunday edi va aynan shu sabab ikki ro'yxatni AJRATGAN edi).

⛔ USTMA-USTLIK QIYMATNI HOSILA QILISH UCHUN SABAB EMAS —
`OCCUPANCY_DELETE_ORDER = tuple(reversed(OCCUPANCY_TENANT_TABLES))` deb
yozish §S-2 ning butun qoidasini buzardi: RLS tartibi (ota-onadan bolalarga)
va o'chirish tartibi (bolalardan ota-onaga) IKKI XIL SAVOLGA javob beradi
va ular BIR-BIRIDAN MUSTAQIL o'zgaradi. Zanjirdan tashqaridagi bitta jadval
qo'shilgan kuni hosila qiymat JIMGINA noto'g'ri bo'lardi — kaskad o'z chet
el kalitiga urilib yiqilardi va buni faqat qoralama bozorni o'chirmoqchi
bo'lgan admin ekranida ko'rardi. Taqiq mexanik qulflangan:
`test_meta.py::test_occupancy_delete_order_is_declared_not_derived` MANBA
MATNINI o'qiydi va `reversed(OCCUPANCY_TENANT_TABLES)` iborasini topsa
qizaradi (§S-10 — darvoza sanoq emas, manbadan hosila).

**(b) BUTUN BLOK MAVJUD SNAPSHOT BLOKIDAN OLDIN TURISHI SHART.**
`occupancy_events` `snapshots (id, is_billable)` ga kompozit FK bilan
tayanadi, `snapshots` esa `SNAPSHOT_DELETE_ORDER` ning BIRINCHI `DELETE` i.
Blok snapshot blokidan keyin qo'yilsa kaskad o'z chet el kalitiga urilib
yiqilardi — `0012`→`0013` va `0014`→`0015` juftligining AYNAN UCHINCHI
takrori.

`0019` va `MARKET_DELETE_DRAFT` kengaytmasi qiymatni SHUNDAN oladi
(`05-05` / T3). `market_delete_draft()` ning O'ZI bu rejada
O'ZGARTIRILMAYDI: reyestr ATAYIN `0018` dan OLDIN yoziladi, shunda
`test_cascade_covers_every_table_referencing_markets` qizargan zahoti
tuzatish ro'yxati tayyor turadi.
"""

ALL_TENANT_TABLES: tuple[str, ...] = (
    *TENANT_TABLES,
    *MARKET_DOMAIN_TENANT_TABLES,
    *TEMPORAL_TENANT_TABLES,
    *VENDOR_TENANT_TABLES,
    *CALENDAR_TENANT_TABLES,
    *NVR_TENANT_TABLES,
    # ✅ QARZ YOPILDI (`04-03` / T2, 2026-08-04) — `0014_snapshot_domain`
    # BILAN BIR COMMITDA. `04-01` bu qatorni ATAYIN qoldirmagan edi va
    # sabab O'LCHANGAN, taxmin emas:
    #
    #   sqlalchemy.exc.ProgrammingError: (psycopg.errors.UndefinedTable)
    #   relation "public.snapshot_schedules" does not exist
    #   [SQL: CREATE POLICY tenant_isolation on public.snapshot_schedules ...]
    #
    # `ALL_ENTITIES` aynan shu ro'yxatdan quriladi, `alembic_utils` ning
    # "schema" komparatori esa solishtirish uchun har bir entity'ni
    # HAQIQATAN yaratib ko'radi (`simulate_entity`). Ya'ni hali mavjud
    # bo'lmagan jadvalga policy ro'yxatga olinishi
    # `tests/tenancy/test_market_domain_meta.py::test_autogenerate_is_empty`
    # ni DARHOL qizartirardi. `0014` jadvallarni endi yaratadi, ya'ni
    # splice AYNAN shu commitda va faqat shu commitda to'g'ri bo'ladi.
    #
    # 3-fazada bu qarz PLAN ICHIDA yopilgan (03-03 reyestrni va `0012` ni
    # ketma-ket bergan) — bu yerda ham xuddi shunday, faqat qarz ikki REJA
    # (`04-01` -> `04-03`) orasida turdi va uni `test_meta.py::
    # test_snapshot_registries_are_self_consistent` mexanik ushlab turdi:
    # shart BAZAGA bog'langan, ya'ni jadval tug'ilgan zahoti darvoza O'ZI
    # QUROLLANADI.
    *SNAPSHOT_TENANT_TABLES,
    # ✅ QARZ YOPILDI (`05-05` / T2, 2026-08-09) — `0018_occupancy_domain`
    # BILAN BIR COMMITDA, `04-03` ning `0014` bilan qilgani bilan AYNAN bir
    # xil qadam va uchinchi marta qo'llanishi.
    #
    # `05-01` bu qatorni ATAYIN qoldirmagan edi va sabab yuqoridagi ✅ bandda
    # O'LCHANGAN (`UndefinedTable`, 2026-08-04): `ALL_ENTITIES` shu ro'yxatdan
    # quriladi, `alembic_utils` komparatori esa har bir entity'ni HAQIQATAN
    # yaratib ko'radi (`simulate_entity`), ya'ni hali mavjud bo'lmagan
    # `camera_zones` ga policy ro'yxatga olinishi
    # `test_market_domain_meta.py::test_autogenerate_is_empty` ni DARHOL
    # yiqitardi. `0018` jadvallarni endi yaratadi, ya'ni splice AYNAN shu
    # commitda va faqat shu commitda to'g'ri bo'ladi.
    #
    # Qarz ko'rinmas emas edi: `test_meta.py::
    # test_occupancy_registries_are_self_consistent` shartni BAZAGA bog'lagan —
    # jadval tug'ilgan zahoti darvoza O'ZI QUROLLANDI.
    *OCCUPANCY_TENANT_TABLES,
)
"""BARCHA tenant jadvallari — policy reyestrining yagona manbai.

`ALL_ENTITIES` aynan shundan quriladi, ya'ni autogenerate har bir jadvalning
`tenant_isolation` policy'sini kuzatadi. Bu reyestr UNUTILISHI mumkin bo'lgan
yagona joy, shuning uchun u YOLG'IZ darvoza EMAS:
`tests/tenancy/test_meta.py::test_every_table_is_tenant_scoped` jadvallarni
`pg_catalog` dan o'qiydi va reyestrga UMUMAN tayanmaydi — reyestrga
qo'shilmagan jadval baribir topiladi (T-02-28).
"""

ALL_RLS_TABLES: tuple[str, ...] = ("markets", *ALL_TENANT_TABLES)
"""RLS yoqilgan barcha jadvallar — `owner_bootstrap` policy'si shu ro'yxatga.

`market_create()` va `market_delete_draft()` `SECURITY DEFINER` bo'lib EGA
huquqi bilan ishlaydi, `FORCE ROW LEVEL SECURITY` esa EGANI HAM policy'ga
bo'ysundiradi. Ya'ni `owner_bootstrap` policy'siz o'sha funksiyalar
`market_profile` ga yoza olmasdi va usta 1-qadamda jimgina 0 qator bilan
tugardi.
"""

ALL_ENTITIES: list[Any] = [
    # `markets` — tenant chegarasining o'zi: predikat `id` bo'yicha.
    markets_policy(),
    *(tenant_policy(table) for table in ALL_TENANT_TABLES),
    # Ega uchun bootstrap: `SECURITY DEFINER` login funksiyalari va bozor
    # yaratish yo'li FORCE ostida bloklanib qolmasligi uchun.
    *(owner_bootstrap_policy(table) for table in ALL_RLS_TABLES),
    # `audit_log` — yozish predikatsiz, o'qish tenant-scoped, UPDATE/DELETE
    # uchun policy YO'Q (o'zgarmaslikning 2-qatlami).
    audit_append_policy(),
    audit_read_policy(),
    # Platforma-global (`market_id IS NULL`) qatorlar uchun EGAGA ochiladigan
    # tor `FOR SELECT` yo'li — `auth_list_platform_audit()` ning jufti (Gap 5).
    audit_read_platform_policy(),
    # Login bootstrap — global o'qish yuzasining BUTUN ro'yxati (Pattern 2).
    *ALL_FUNCTIONS,
    # Sessiya va parol YOZISH yo'li (0003): `refresh_tokens` ustidagi
    # operatsiyalar ham tenant kontekstisiz bajarilishi kerak, chunki
    # refresh cookie kelganda bozor hali noma'lum.
    *AUTH_SUPPORT_FUNCTIONS,
    # Foydalanuvchi boshqaruvi va profil (0004): `users` app-rolga yopiq,
    # ya'ni yaratish/profil o'qish/til saqlash ham shu yuzadan o'tadi.
    *USER_ADMIN_FUNCTIONS,
    # Platforma-global audit o'qish (0005): yuqoridagi `audit_read_platform`
    # policy'si bilan JUFTLIKDA ishlaydi — biri ikkinchisisiz 0 qator beradi.
    *PLATFORM_AUDIT_FUNCTIONS,
    # Bozor hayot sikli (0007): yaratish/faollashtirish/nomlash/o'chirish
    # `SECURITY DEFINER`, `market_is_open()` esa ATAYIN INVOKER.
    *MARKET_DOMAIN_FUNCTIONS,
    # Snapshot quvurining tik yuzasi (0015): `capture_due_markets()` —
    # tenant kontekstisiz FAQAT identifikator qaytaradigan tor `SECURITY
    # DEFINER` funksiya (§S-3). Reyestrga tushishi MAJBURIY: usiz tananing
    # keyingi o'zgarishi autogenerate'da ko'rinmasdi va bazadagi ta'rif
    # koddagisidan jimgina ajralib ketardi.
    *SNAPSHOT_FUNCTIONS,
    # Bandlik domenining ikki tik yuzasi (0018): `audit_draw_due_markets()`
    # va `occupancy_day_close_markets()` — ikkalasi ham tenant kontekstisiz
    # FAQAT identifikator va sanoq qaytaradigan tor `SECURITY DEFINER`
    # funksiyalar (§S-5, T-05-19). Reyestrga tushishi MAJBURIY: usiz
    # tananing keyingi o'zgarishi autogenerate'da ko'rinmasdi va bazadagi
    # ta'rif koddagisidan jimgina ajralib ketardi.
    *OCCUPANCY_FUNCTIONS,
    # Audit yozuvchisi + append-only qo'riqchisi (D-10) + 2-faza domen
    # qoidalari (kod reyestri, tarif/toifa daxlsizligi) + 5-faza bandlik
    # domenining ikki o'zgarmaslik qo'riqchisi (D-12/D-17.4).
    *ALL_TRIGGER_FUNCTIONS,
]


# ===========================================================================
# 6-FAZA — WAVE 0 O'LCHOV MARKERLARI (BILLING VA KASSIR)
# ===========================================================================
#
# ⛔ BU BLOKDAGI KONSTANTALAR ENTITY EMAS va `ALL_ENTITIES` ga KIRMAYDI.
#    Ular HAQIQIY `postgres:18.4` da olingan O'LCHOV natijalari va ular
#    shu yerda yashaydi, chunki ularning ISTE'MOLCHISI migratsiya qatlami:
#    `0020` ning shakli va `payment_repo` ning shakli aynan shu javoblardan
#    chiqadi. `04-01` ning `BILLABLE_ANCHOR_SUPPORTED` i (bu faylda `:344`
#    izohida havola qilingan) o'rnatgan naqsh — o'lchov SUMMARY'da qolib
#    ketmaydi, u KODDA qulflanadi.

IDEMPOTENT_GET_OR_CREATE_SUPPORTED: Final[bool] = True
"""A1 O'LCHOVI — ikki bayonotli get-or-create parallel yozuvda ISHLAYDIMI.

**O'lchov:** 2026-08-10, `PostgreSQL 18.4 (Debian trixie)`, testcontainer.
**O'lchaydigan test:** `tests/tenancy/test_idempotency_concurrency.py::
test_second_statement_sees_the_winner` — ikki MUSTAQIL `AsyncSession`
`asyncio.Barrier` bilan bir vaqtda bir xil `(market_id, idempotency_key)`
juftligini yozadi.

**Nima o'lchandi (uchala da'vo birga):** jadvalda AYNAN 1 qator · ikkala
korutina ham BIR XIL `id` oldi · birorta korutina istisno ko'tarmadi.
Yutqazgan sessiya AYNI tranzaksiyasida alohida `SELECT` bajardi va yutgan
qatorni KO'RDI (READ COMMITTED har BAYONOT uchun yangi snapshot oladi).

⛔ **QIYMAT QO'LDA YOZILMAYDI.** Test uni O'QIB o'lchov natijasi bilan
solishtiradi (`assert IDEMPOTENT_GET_OR_CREATE_SUPPORTED is measured`),
ya'ni marker o'lchovdan ajralib keta olmaydi. `True` deb qo'yib xulqni
buzish IMKONSIZ — test darhol qizaradi.

⛔ **AGAR QIYMAT `False` BO'LSA — 06-09 NING KIRISH SHARTI O'ZGARADI:**
`payment_repo` ikki bayonotli get-or-create o'rniga `IntegrityError` +
`SAVEPOINT` (`session.begin_nested()`) yo'lidan yuradi —
`services/core-api/app/repositories/nvr_repo.py:506-532` naqshi va `03-06`
ning o'lchangan darsi (abort holatidagi tranzaksiya 409+`run_id` ni 500 ga
aylantirardi). Bu shox TAXMIN emas, MAJBURIYAT: D-21 («takror so'rov o'sha
to'lovni 200 bilan qaytaradi») ikkala holatda ham bajarilishi shart.

⚠ **QIYMAT IZOLYATSIYA DARAJASIGA BOG'LIQ.** `REPEATABLE READ` ga
o'tilganda ikkinchi bayonot o'z tranzaksiyasi boshidagi snapshotni ko'rar
va qatorni TOPMASDI. Test `SHOW transaction_isolation` ni OCHIQ
solishtiradi (`read committed`), ya'ni engine sozlamasining jimgina
o'zgarishi shu yerda ushlanadi.
"""

IDEMPOTENT_GET_OR_CREATE_MEASURED_AT: Final[str] = "2026-08-10 · PostgreSQL 18.4"
"""A1 o'lchovining sanasi va serveri.

Yozilmasa natija keyinroq «qayerda va qachon o'lchangan?» degan javobsiz
savolga aylanardi (`billable_probe.BillableProbe.server_version` bilan
aynan bir xil sabab). PG major versiyasi ko'tarilganda zond QAYTA
yugurtiriladi va bu satr yangilanadi.
"""
