"""Bildirishnoma domenining META-INVARIANTLARI — hammasi `pg_catalog` dan.

=============================================================================
NEGA BU FAYL MODELNI IMPORT QILMAYDI.

`sbozor_core.models.notification` — ISTALGAN holat. Bazadagi sxema esa
HAQIQIY holat. Ikkisi ajralib qolishi mumkin (migratsiya qo'llanmagan,
ustun keyingi migratsiyada `ALTER TABLE` bilan qo'shilgan, kimdir qo'lda
`psql` ochgan) va aynan o'sha holatda modeldan o'qiydigan test JIMGINA
yashil qolardi. `test_market_domain_meta.py` bu qoidani 2-fazada
o'rnatgan, `test_billing_domain_meta.py` uni 6-fazada davom ettirgan; bu
fayl esa 7-fazada.

⚠ ISTISNO — `test_no_new_security_definer_function_was_added()`
`tenancy.test_meta` ni ATAYIN import qiladi: uning butun savoli aynan
«DEFINER reyestri O'SDIMI?» va u ikkala tomonni ko'rmasdan javob bera
olmaydi. Import test funksiyasining ICHIDA
(`test_occupancy_domain_meta.py` dagi jufti bilan bir xil sabab: modul
darajasidagi import butun faylning yig'ilishini yiqitishi mumkin).
=============================================================================

TO'QQIZTA INVARIANT VA HAR BIRI QAYSI DA'VONI QULFLAYDI:

  1. ⛔ G7-2 (D-03) — `notification_outbox` sxemasida kadr / obyekt kaliti /
     manzil / tayyor matn / chat manzili nomli ustun YO'Q. O'lchov
     `information_schema.columns` DAN, grep bilan EMAS: grep migratsiya
     MATNINI ko'radi, SXEMANI emas — keyingi migratsiya ustunni
     `ALTER TABLE ... ADD COLUMN` bilan qo'shsa grep YASHIL qolardi.
  2. Taqiqlangan tokenlar predikati SUN'IY nomlarda HAQIQATAN ushlaydi —
     1-bandning SHARTI. Usiz predikat noto'g'ri yozilganda (`==` bilan)
     darvoza mangu yashil bo'lardi.
  3. ⛔ G7-8 birinchi yarmi — saqlangan QOLDIQ ustuni beshala jadvalda YO'Q.
  4. ⛔ G7-8 ikkinchi yarmi — yangi modullarda suzuvchi arifmetika va
     kasrli tip nomi YO'Q. O'lchov AST bilan, grep bilan EMAS (02-23 /
     03-07 darsi: taqiqni TUSHUNTIRGAN docstring grepni o'z-o'ziga
     qarshi qo'yardi).
  5. Beshala jadvalning TIPLAR TO'PLAMI ruxsat etilganiga TENG.
  6. Beshala jadvalda RLS `ENABLE` + `FORCE` + tenant policy.
  7. Case NISHONINING to'rt cheklovi va ikki QISMAN UNIQUE indeksi mavjud.
  8. Case tarixi HAQIQATAN append-only — XULQIY o'lchov (`UPDATE` rad
     etiladi), shaklga qarash EMAS.
  9. ⛔ G7-7 (T-06-22) — `pg_proc.prosecdef` to'plami 6-fazadagidan
     O'SMAGAN: `0023` birorta yangi `SECURITY DEFINER` funksiya
     qo'shmadi.

Enum <-> `CHECK` tengligi bu yerda TAKRORLANMAYDI: u
`tests/unit/test_reconciliation_enums.py` da va `0023` `CHECK`
ifodalarini MODELDAN import qiladi, ya'ni ikkinchi nusxa umuman
tug'ilmaydi (`test_billing_domain_meta.py::
test_no_migration_hard_codes_a_value_list` ning o'lchangan xulosasi).
"""

from __future__ import annotations

import ast
import re
from datetime import date
from pathlib import Path
from uuid import UUID, uuid4

import psycopg
import pytest
from fixtures.market_domain import MarketDomainSeed
from psycopg import Connection
from psycopg.rows import TupleRow

pytestmark = pytest.mark.tenancy

NOTIFICATION_TABLES: tuple[str, ...] = (
    "reconciliation_cases",
    "reconciliation_case_events",
    "notification_outbox",
    "vendor_telegram_bindings",
    "market_notification_settings",
)
"""`0023` yaratgan BESHALA jadval — tip va RLS darvozalari shular ustidan yuradi."""

FORBIDDEN_OUTBOX_COLUMN_TOKENS: frozenset[str] = frozenset(
    {
        "snapshot_id",
        "snapshot",
        "image",
        "photo",
        "object_key",
        "url",
        "link",
        "text",
        "body",
        "message_text",
        "chat_id",
    }
)
"""⛔⛔ G7-2 NING YURAGI — `notification_outbox` da HECH QACHON bo'lmasligi
kerak bo'lgan ustun nomlarining O'ZAKLARI.

TAQIQNING SABABI UCH QATLAMLI VA HAR BIRI MUSTAQIL:

  (a) KADR — SHAXSIY MA'LUMOT. Kadrda bozor tashrifchilarining yuzlari
      bor va ular O'zR shaxsiy ma'lumotlar qonuni ostida. `snapshot_id` /
      `object_key` / `image_*` ustuni bo'lgan zahoti dalil-kadrni xabarga
      biriktirish yo'li OCHILADI — D-03 esa buni MUZOKARA QILINMAYDIGAN
      taqiq deb belgilaydi.

  (b) TELEGRAM SERVERLARI CHEGARADAN TASHQARIDA. Bir marta yuborilgan
      bayt qaytarib olinmaydi: o'chirilgan xabar ham provayder tomonida
      qolishi mumkin. Dalil xabarga HAVOLA bo'lib boradi (veb yuzasiga,
      autentifikatsiya ostida) — BAYT bo'lib bormaydi.

  (c) TAYYOR MATN USTUNI BAZANI EKSPORT KANALIGA AYLANTIRADI (Pitfall 6).
      `text` / `body` / `message_text` ustuni sotuvchining ismini, rasta
      kodini va summani BAZAGA yozardi, u yerdan `pg_dump` -> restic ->
      TASHQI BUCKET ga chiqardi. Matn `kind` + `payload` dan JO'NATISH
      PAYTIDA quriladi.

  `chat_id` esa boshqa sinf: D-26(c) qayta ulanishda eski bog'lanishni
  BEKOR qiladi va navbatda turgan xabar ESKI chatga ketmasligi kerak —
  manzil jo'natish paytida `JOIN` bilan olinadi.

⚠⚠ `provider_message_id` ATAYIN USHLANMAYDI VA BU YERDA OCHIQ YOZILADI.
Ro'yxatda `message_text` bor, `message` YO'Q; `text` esa
`provider_message_id` ning ichida uchramaydi. Bu TASODIF EMAS: o'sha
ustun Telegram QAYTARGAN identifikator, ya'ni chiquvchi kontent emas,
jo'natish DALILI. Ro'yxatga `message` ni «to'liqroq bo'lsin» deb qo'shish
darvozani YOLG'ON-QIZIL qilardi va yagona «tuzatish» yo'li mavjud,
qonuniy ustunni O'CHIRISH bo'lardi.

⚠ SOLISHTIRUV `in` (ost-satr) BO'YICHA, tenglik bo'yicha EMAS: `url`
tokeni `evidence_url` ni ham, `image_url` ni ham ushlashi SHART. Tenglik
bilan yozilgan predikat prefiks qo'shilgan zahoti chetlab o'tilardi.
"""

BALANCE_SCANNED_TABLES: tuple[str, ...] = NOTIFICATION_TABLES
"""G7-8 ning birinchi yarmi — saqlangan qoldiq qidiriladigan yuza.

BESHALA jadval ro'yxatda va bu ATAYIN: qoldiq ustuni «pul jadvaliga»
emas, EGASIGA yoki eng ko'p o'qiladigan jadvalga yopishadi — bu domenda
esa ikkalasi ham case va outbox qatorlari.

⚠ `vendors` / `stalls` bu ro'yxatda YO'Q va bu takror emas, CHEGARA:
ularni `test_billing_domain_meta.py::BALANCE_SCANNED_TABLES` allaqachon
skanerlaydi. Ikkinchi nusxa ikki ro'yxatni ajralib ketadigan qilardi.
"""

ALLOWED_DATA_TYPES: frozenset[str] = frozenset(
    {
        "uuid",
        "text",
        "bigint",
        "integer",
        "date",
        "jsonb",
        "time without time zone",
        "timestamp with time zone",
    }
)
"""G7-8/D-07 — beshala jadvalda RUXSAT ETILGAN `information_schema` tiplari.

⛔ SOLISHTIRUV TO'PLAM TENGLIGI BILAN, `not in` BILAN EMAS
(`test_billing_domain_meta.py::ALLOWED_DATA_TYPES` da o'rnatilgan qoida).
`assert "double precision" not in types` shakli faqat SANAB O'TILGAN
tiplarni qo'riqlardi: `numeric(12,2)`, `real`, `money` yoki
`double precision[]` uni chetlab o'tardi. Tenglik esa HAR QANDAY yangi
tipni ushlaydi.

⛔ KASRLI TIPLAR RO'YXATDA YO'Q va bu shu domendagi eng arzon qulf: bu
jadvallarda pul ustuni UMUMAN yo'q (summa `payload` da KO'CHIRMA bo'lib
turadi, manba esa `payments` / `daily_charges`), ya'ni kasrli tipning
paydo bo'lishi «summani shu yerda hisoblay boshladik» degan ma'noni
bildirardi — D-06/D-07 aynan shuni taqiqlaydi.

⚠⚠ `boolean` RO'YXATDA YO'Q VA BU O'LCHANGAN FAKT, UNUTISH EMAS.
Beshala jadvalning birortasida ham bayroq ustuni yo'q: holat `text` +
enumdan hosila `CHECK` bilan (`status`, `kind`, `recipient_kind`), faollik
esa `NULL` bilan (`revoked_at IS NULL` — qisman indekslarning predikati)
ifodalanadi. `is_active` / `is_revoked` shaklidagi bayroq IKKINCHI HAQIQAT
MANBAI bo'lardi va u `revoked_at` dan jimgina ajralib ketardi. Ro'yxatga
`boolean` ni «har ehtimolga qarshi» qo'shish o'sha qarorni JIMGINA
bo'shatardi — reja matnida u bor edi, sxemada esa YO'Q, ya'ni tenglik
darvozasi uni birinchi yugurishdayoq rad etardi.

⚠ `time without time zone` MAJBURIY: `market_notification_settings` ning
quiet hours chegaralari — DIVOR SOATI, moment emas. Ularni `timestamptz`
qilish «har kuni 21:00» tushunchasini bitta lahzaga aylantirardi.
"""

FORBIDDEN_ARITHMETIC_CALLS: frozenset[str] = frozenset({"float", "round"})
"""AST da CHAQIRUV sifatida uchramasligi kerak bo'lgan nomlar (G7-8)."""

FORBIDDEN_ARITHMETIC_NAMES: frozenset[str] = frozenset({"Decimal"})
"""AST da NOM sifatida uchramasligi kerak bo'lgan tiplar (G7-8)."""

NOTIFICATION_SOURCES: tuple[Path, ...] = tuple(
    Path(__file__).resolve().parents[2] / part
    for part in (
        "packages/sbozor-core/sbozor_core/models/notification.py",
        "migrations/versions/0023_notification_domain.py",
    )
)
"""7-fazaning IKKI yangi Python fayli — NOMMA-NOM.

⚠ `glob("*.py")` ATAYIN EMAS (`test_billing_domain_meta.py::
_BILLING_MIGRATIONS` da o'rnatilgan qoida): quyi fazalarning fayllarida
suzuvchi arifmetika QONUNIY bo'lishi mumkin (masalan `camera_zones`
poligonining normalizatsiyasi — u pul emas, KOORDINATA) va ularni bu
darvoza ostiga tortish 7-fazaning testini o'zga fazaning qarziga bog'lab
qo'yardi.
"""

TABLE_COLUMNS = """
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = %s
"""
"""⛔ `information_schema` ATAYIN — G7-2 SXEMANI o'qiydi, matnni emas.

Grant filtri xavfi (`information_schema` o'z ko'rinishlarini joriy rolning
huquqlari bo'yicha filtrlaydi) NAZORAT ASSERTI bilan yopiladi: bo'sh
to'plam HAR DOIM yiqiladi, ya'ni «ko'rinmadi» «yo'q» ga aylanmaydi.
"""

CONSTRAINT_DEFS = """
SELECT con.conname, pg_get_constraintdef(con.oid)
FROM pg_constraint con
JOIN pg_class c ON c.oid = con.conrelid
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public'
  AND c.relname = %s
  AND con.contype = ANY(%s)
"""
"""Jadvalning konstraytlari — TA'RIFI bilan.

`pg_constraint` ishlatiladi (`information_schema` emas): oxirgisi o'z
ko'rinishlarini joriy rolning grant'lari bo'yicha filtrlaydi, ya'ni huquqi
tor rol ostida jimgina KAM konstrayt qaytarardi va darvoza sababsiz yashil
bo'lib qolardi (`test_occupancy_domain_meta.py` da o'rnatilgan qoida).
"""

PARTIAL_INDEX = """
SELECT i.indpred IS NOT NULL, ix.indexdef
FROM pg_index i
JOIN pg_class c ON c.oid = i.indexrelid
JOIN pg_namespace n ON n.oid = c.relnamespace
JOIN pg_indexes ix ON ix.schemaname = n.nspname AND ix.indexname = c.relname
WHERE n.nspname = 'public' AND c.relname = %s
"""
"""Indeksning QISMAN ekani — `pg_index.indpred` dan.

⚠ `indexdef` MATNIDA `WHERE` qidirish YETARLI EMAS: `pg_index.indpred`
predikatning PARSLANGAN shakli, ya'ni u indeksning haqiqiy tuzilishidan
keladi. Matn qidiruvi ustun nomida `where` uchraydigan indeksda ham rost
bo'lardi.
"""

RLS_FLAGS = """
SELECT c.relrowsecurity, c.relforcerowsecurity
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public' AND c.relname = %s
"""

POLICY_NAMES = """
SELECT policyname
FROM pg_policies
WHERE schemaname = 'public' AND tablename = %s
ORDER BY policyname
"""

DEFINER_FUNCTIONS = """
SELECT p.proname
FROM pg_proc p
JOIN pg_namespace n ON n.oid = p.pronamespace
WHERE n.nspname = 'public' AND p.prosecdef
ORDER BY p.proname
"""

TENANT_POLICY_NAME = "tenant_isolation"
"""`migrations/entities/policies.py::TENANT_POLICY_SIGNATURE` ning qiymati.

⚠ REYESTRDAN IMPORT QILINMAYDI va bu ATAYIN: `migrations.entities` dan
olingan nom reyestrning O'ZI xato bo'lganda test bilan BIRGA xato
bo'lardi — ya'ni darvoza o'z manbasini tekshirardi.
"""

PHASE_SIX_DEFINER_COUNT = 21
"""`test_meta.py::EXPECTED_DEFINER_FUNCTIONS` ning 6-faza oxiridagi SANOG'I.

⛔ BU SON O'SMASLIGI SHART. Yangi `SECURITY DEFINER` funksiya — RLS'ni
chetlab o'tadigan YANGI YUZA (T-06-22 / C-11): u ega huquqi bilan
ishlaydi, ya'ni tenant predikati unga qo'llanmaydi. 7-faza birorta
shunday funksiya qo'shmaydi — `market_delete_draft(uuid)` ning faqat
TANASI kengaydi, IMZOSI o'zgarmadi.
"""

EXTRA_DEFINER_FUNCTIONS: frozenset[str] = frozenset({"capture_due_markets"})
"""Bazada BOR, lekin `EXPECTED_DEFINER_FUNCTIONS` da YO'Q definer funksiyalar.

`test_meta.py` ning solishtiruvi `found >= EXPECTED_DEFINER_FUNCTIONS`,
ya'ni u ORTIQCHA nomni UMUMAN ko'rmaydi — aynan shu bo'shliqni bu ro'yxat
yopadi. `capture_due_markets()` 4-fazadan keladi va uning tor yuzasi
`test_snapshot_domain_meta.py::test_capture_due_markets_exposes_only_
identifiers` da alohida qulflangan.

⚠ `audit_draw_due_markets()` va `occupancy_day_close_markets()` bu yerda
YO'Q va bu O'LCHANGAN FAKT: `0020` ikkalasini ham DROP qildi
(`test_occupancy_domain_meta.py::DEFINER_SURFACES` bo'shatilishining
sababi). Ularni «har ehtimolga qarshi» qo'shish quyidagi TENGLIK
darvozasini yiqitardi.
"""

_ANOMALY_SERVICE_DATE = date(2026, 1, 15)
"""Case nishoni uchun O'TMISH sanasi.

⚠ «Bugun» ISHLATILMAYDI: `billing_anomalies.business_date` — `created_at`
dan hosila ustun va u konteynerning `Asia/Tashkent` mintaqasida
hisoblanadi. Sobit o'tmish sanasi yarim tundagi chegara xatosini
BUTUNLAY yo'q qiladi.
"""


def _columns(conn: Connection[TupleRow], table: str) -> dict[str, str]:
    rows = conn.execute(TABLE_COLUMNS, (table,)).fetchall()
    columns = {str(row[0]): str(row[1]) for row in rows}
    assert columns, (
        f"`{table}` uchun `information_schema.columns` 0 qator qaytardi. "
        "Jadval yo'q, yoki joriy rolda unga birorta huquq yo'q — ikkala "
        "holatda ham quyidagi da'vo BO'SH ROST bo'lib qolardi."
    )
    return columns


def _constraint_names(conn: Connection[TupleRow], table: str, contypes: str) -> set[str]:
    rows = conn.execute(CONSTRAINT_DEFS, (table, list(contypes))).fetchall()
    return {str(row[0]) for row in rows}


def _forbidden_column_hits(columns: frozenset[str]) -> dict[str, list[str]]:
    """Ustun nomlari ichidan taqiqlangan TOKENLARNI ushlaydigan YAGONA predikat.

    ⛔ TESTLAR BU FUNKSIYANI QAYTA YOZMAYDI, CHAQIRADI — va aynan shu uni
    NAZORAT qilinadigan qiladi: `test_forbidden_tokens_are_actually_
    reachable()` uni SUN'IY nomlar bilan chaqiradi, ya'ni predikat
    noto'g'ri yozilganda (masalan `==` bilan) nazorat testi ham
    qizaradi. Ikki joyda ikki nusxa predikat bo'lganda nazorat o'z
    nusxasini tekshirgan bo'lardi.
    """
    hits: dict[str, list[str]] = {}
    for column in sorted(columns):
        lowered = column.lower()
        matched = sorted(token for token in FORBIDDEN_OUTBOX_COLUMN_TOKENS if token in lowered)
        if matched:
            hits[column] = matched
    return hits


def _forbidden_arithmetic(source: str) -> list[str]:
    """AST bo'yicha taqiqlangan chaqiruv/nomlarni topadi (G7-8).

    =========================================================================
    ⛔ NEGA AST, NEGA GREP EMAS — 02-23 / 03-07 NING O'LCHANGAN DARSI.

    Sodda grep izohni koddan AJRATMAYDI. Bu domenning ikkala fayli ham
    taqiqni TUSHUNTIRADI («kasrli tip ishlatilmaydi», «yaxlitlash
    chaqiruvi yo'q») va o'sha tushuntirish grep darvozasini O'Z-O'ZIGA
    QARSHI qo'yardi: yagona «tuzatish» yo'li darvozaga istisno qo'shish
    yoki sababni yozmaslik bo'lardi — ikkalasi ham himoyani zaiflashtiradi.

    AST esa docstringni `ast.Constant` deb ko'radi va uning ICHIGA
    umuman kirmaydi. Farq `test_notification_modules_use_no_float_
    arithmetic()` ichida IKKI ZOND bilan O'LCHANADI.
    =========================================================================
    """
    tree = ast.parse(source)
    offenders: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id in FORBIDDEN_ARITHMETIC_CALLS:
                offenders.append(f"{func.id}() @ satr {node.lineno}")
            elif isinstance(func, ast.Attribute) and func.attr in FORBIDDEN_ARITHMETIC_CALLS:
                offenders.append(f".{func.attr}() @ satr {node.lineno}")
        elif isinstance(node, ast.Name) and node.id in FORBIDDEN_ARITHMETIC_NAMES:
            offenders.append(f"{node.id} @ satr {node.lineno}")
        elif isinstance(node, ast.Attribute) and node.attr in FORBIDDEN_ARITHMETIC_NAMES:
            offenders.append(f".{node.attr} @ satr {node.lineno}")
    return offenders


def test_outbox_has_no_evidence_or_message_column(
    sync_app_conn: Connection[TupleRow], migrated: None
) -> None:
    """⛔ G7-2 — `notification_outbox` da dalil/manzil/matn ustuni YO'Q (D-03).

    =========================================================================
    ⛔⛔ BU FAZANING IKKINCHI SAVOLIGA FAQAT SHU TEST JAVOB BERADI:
       «chegaradan CHIQMASLIGI kerak bo'lgan narsa chiqmadimi?»

    Va u faqat SXEMADAN o'qib javob bera oladi. Grep migratsiya MATNINI
    ko'radi: keyingi migratsiya `ALTER TABLE notification_outbox ADD
    COLUMN evidence_url text` yozsa grep YASHIL qolardi, chunki `0023`
    ning matni o'zgarmagan bo'lardi. `information_schema` esa jadvalning
    BUGUNGI holatini beradi.

    ⚠ SOLISHTIRUV TO'PLAM TENGLIGI BILAN (`hits == {}`), `len() == 0`
      bilan EMAS: ikkalasi bir xil natija berardi, lekin xato xabari
      QAYSI ustun QAYSI token bilan ushlanganini ko'rsatishi kerak —
      aks holda keyingi ishlovchi sababni topolmay, eng oson yo'l
      sifatida tokenni ro'yxatdan o'chirardi.
    =========================================================================
    """
    columns = frozenset(_columns(sync_app_conn, "notification_outbox"))
    hits = _forbidden_column_hits(columns)

    assert hits == {}, (
        f"`notification_outbox` da TAQIQLANGAN ustun(lar) topildi: {hits}.\n"
        "Bu ustunlarning YO'QLIGI D-03 ning sxema darajasidagi ifodasi:\n"
        "  * kadr identifikatori / obyekt kaliti / manzil -> dalil-kadr "
        "Telegram serverlariga (CHEGARADAN TASHQARIGA) chiqadigan yo'l;\n"
        "  * tayyor matn -> sotuvchi ismi va summa bazaga, u yerdan "
        "`pg_dump` -> restic -> tashqi bucket ga chiqadi;\n"
        "  * chat manzili -> D-26(c) da bekor qilingan bog'lanishga "
        "yuborilgan xabar.\n"
        "Matn `kind` + `payload` dan JO'NATISH PAYTIDA quriladi, manzil "
        "esa `vendor_telegram_bindings` dan `JOIN` bilan olinadi."
    )

    # NAZORAT: jadvalning O'ZI kutilgan ustunlarga ega. Usiz yuqoridagi
    # inkor da'vosi jadval bo'sh bo'lganda ham rost bo'lardi
    # (`_columns()` bo'sh to'plamda yiqiladi, ya'ni nazorat AVTOMATIK),
    # lekin `dedupe_key` ning MAVJUDLIGI alohida ma'noga ega: aynan u
    # D-21 ning kaliti va u yo'qolsa outbox umuman boshqa jadval bo'lardi.
    assert "dedupe_key" in columns, (
        "`notification_outbox.dedupe_key` YO'Q — bu jadval endi D-21 ning "
        "idempotentlik navbati emas, ya'ni yuqoridagi taqiq ham boshqa "
        "narsani o'lchayapti."
    )


def test_forbidden_tokens_are_actually_reachable() -> None:
    """⛔ NAZORAT O'LCHOVI — taqiq predikati SUN'IY nomlarda HAQIQATAN ushlaydi.

    =========================================================================
    YUQORIDAGI TESTNING SHARTI, TAKRORI EMAS.

    `test_outbox_has_no_evidence_or_message_column()` INKOR da'vo qiladi
    («hech nima topilmadi») va inkor da'volar bir sinf nosozlikka
    tug'ma ochiq: predikat noto'g'ri yozilgan bo'lsa u HAM «hech nima
    topilmadi» deydi. Masalan `token == column` shakli `evidence_url` ni
    ham, `snapshot_id` ni ham o'tkazib yuborardi va darvoza MANGU yashil
    qolardi — 5-fazaning W-2/W-3 darsi aynan shu haqda.

    Shuning uchun bu yerda predikat O'LCHANAYOTGAN HOLATNING MAVJUD
    shakllari bilan chaqiriladi va har biri ushlanishi TALAB qilinadi.
    =========================================================================
    """
    reachable = frozenset({"snapshot_id", "evidence_url", "message_text"})
    hits = _forbidden_column_hits(reachable)

    assert set(hits) == reachable, (
        f"predikat sun'iy nomlarning HAMMASINI ushlamadi: {sorted(hits)}.\n"
        f"  ushlanmagani: {sorted(reachable - set(hits))}\n"
        "Shu holatda yuqoridagi G7-2 darvozasi BO'SH ROST bo'lib qolardi — "
        "ya'ni u aynan qo'riqlashi kerak bo'lgan ustunni o'tkazib yuborardi."
    )

    # ⚠ TESKARI YO'NALISH — qonuniy ustunlar USHLANMASLIGI SHART. Usiz
    #   predikatni «hammasini ushlaydigan» qilib yozish (masalan bo'sh
    #   token qo'shish) yuqoridagi da'voni ham qanoatlantirardi, lekin
    #   darvozani YOLG'ON-QIZIL qilardi va yagona "tuzatish" yo'li
    #   mavjud, qonuniy ustunni O'CHIRISH bo'lardi.
    legitimate = frozenset({"provider_message_id", "last_error_type", "next_attempt_at"})
    assert _forbidden_column_hits(legitimate) == {}, (
        "predikat QONUNIY ustunni ushladi: "
        f"{_forbidden_column_hits(legitimate)}. `provider_message_id` — "
        "Telegram QAYTARGAN identifikator (jo'natish DALILI), chiquvchi "
        "kontent EMAS; `last_error_type` esa ATAYIN `_type` bilan tugaydi "
        "(D-04: unga faqat `type(exc).__name__` yoziladi)."
    )


def test_no_stored_balance_column_anywhere(
    sync_app_conn: Connection[TupleRow], migrated: None
) -> None:
    """⛔ G7-8 birinchi yarmi — saqlangan QOLDIQ ustuni beshala jadvalda YO'Q.

    =========================================================================
    QARZ — HAR DOIM HISOBLANADIGAN KO'RINISH (BILL-03, D-06).

    Bildirishnoma domenida bu taqiq YANGI SHAKLDA qaytib keladi: eslatma
    xabari «qancha qarzdorsiz?» degan songa muhtoj va uni case yoki
    outbox qatoriga YOZIB QO'YISH eng tabiiy «optimizatsiya» bo'lardi.
    O'sha son bir yozilgach MUZLAB qolardi: sotuvchi ertasi kuni to'lasa
    ham eslatma eski raqamni takrorlardi va nizoda (D-02) IKKI XIL son
    dalil bo'la olmasdi.

    Xabardagi summa `payload` da KO'CHIRMA bo'lib turadi va u AYNI
    LAHZADAGI hisobning nusxasi — bu boshqa sinf: nusxa xabar bilan
    birga qotadi va aynan shuning uchun u `payload` da, USTUNDA emas.
    =========================================================================
    """
    found: set[str] = set()
    for table in BALANCE_SCANNED_TABLES:
        for column in _columns(sync_app_conn, table):
            lowered = column.lower()
            if lowered.startswith("balance") or lowered.endswith("balance"):
                found.add(f"{table}.{column}")

    assert found == set(), (
        f"saqlangan qoldiq ustuni topildi: {sorted(found)}. Qarz "
        "so'rovda HISOBLANADI (BILL-03); saqlangan ustun ikkinchi haqiqat "
        "manbai bo'ladi va u birinchisidan JIMGINA ajralib ketadi."
    )

    assert len(BALANCE_SCANNED_TABLES) == 5, (
        "skanerlanadigan yuza qisqarib ketgan — jadval ro'yxatdan tushib "
        "qolsa yuqoridagi inkor da'vosi u yerda umuman o'lchamasdi"
    )


def test_notification_modules_use_no_float_arithmetic() -> None:
    """⛔ G7-8 ikkinchi yarmi — yangi modullarda suzuvchi arifmetika YO'Q (D-07).

    =========================================================================
    PUL — `bigint` SO'M ↔ Python `int`. KASRLI TIP HECH QAYERDA.

    Yaxlitlanish drifti aynan mahsulot bartaraf etadigan nizoni
    tug'diradi: kunlik patta agregatida bir tiyin farq oyiga bir necha
    so'mga aylanadi va sotuvchi bilan bozor ma'muriyati IKKI XIL son
    ko'radi. `float` da bu farq HECH QANDAY xato bermaydi — u shunchaki
    yig'iladi.

    ⛔⛔ O'LCHOV AST BILAN VA FARQ SHU YERDA, IKKI ZOND BILAN O'LCHANADI:

        zond 1 (KOD)      -> `round(float(x))`  -> AST USHLAYDI
        zond 2 (DOCSTRING)-> aynan o'sha so'zlar -> AST KO'RMAYDI,
                                                    grep esa KO'RADI

    Ikkinchi zond bu faylning butun mavjudlik sababi: `models/
    notification.py` va `0023` ikkalasi ham taqiqni TUSHUNTIRADI, ya'ni
    grep darvozasi ularni O'Z IZOHLARI uchun jazolardi va yagona
    «tuzatish» yo'li sababni O'CHIRISH bo'lardi (03-07 da bir marta
    haqiqatan sodir bo'lgan).
    =========================================================================
    """
    code_probe = "def f(x):\n    return round(float(x)) + Decimal(1)\n"
    assert _forbidden_arithmetic(code_probe) != [], (
        "AST predikati HAQIQIY chaqiruvni topmadi — quyidagi da'vo bo'sh rost bo'lib qolardi"
    )

    doc_probe = '"""Bu yerda round( va float( va Decimal faqat MATN sifatida."""\n'
    assert _forbidden_arithmetic(doc_probe) == [], (
        "AST predikati DOCSTRINGDAGI so'zni ushladi — u grepdan farq "
        "qilmayapti va taqiqni tushuntirgan izoh darvozani o'z-o'ziga "
        "qarshi qo'yadi (03-07)"
    )
    assert re.search(r"round\(|float\(|Decimal", doc_probe) is not None, (
        "sodda grep naqshi docstringdagi so'zni TOPMADI — ikki zond "
        "orasidagi FARQ o'lchanmay qoldi, ya'ni yuqoridagi da'vo "
        "AST ning grepdan ustunligini isbotlamayapti"
    )

    offenders: dict[str, list[str]] = {}
    for path in NOTIFICATION_SOURCES:
        assert path.is_file(), f"kutilgan manba fayl yo'q: {path}"
        hits = _forbidden_arithmetic(path.read_text(encoding="utf-8"))
        if hits:
            offenders[path.name] = hits

    assert offenders == {}, (
        f"bildirishnoma modullarida suzuvchi arifmetika topildi: {offenders}. "
        "Pul — `bigint` so'm ↔ `int` (D-11): `float`/`round`/`Decimal` "
        "yaxlitlanish driftini olib keladi va u HECH QANDAY xato bermasdan "
        "yig'iladi."
    )


def test_notification_columns_use_only_allowed_types(
    sync_app_conn: Connection[TupleRow], migrated: None
) -> None:
    """Beshala jadval ustunlarining TIPLAR TO'PLAMI ruxsat etilganiga TENG (G7-8).

    ⛔ SOLISHTIRUV TENGLIK BILAN, `not in` BILAN EMAS — sabab
       `ALLOWED_DATA_TYPES` docstringida. Tenglik IKKI YO'NALISHNI ham
       qulflaydi: yangi tip (`numeric`, `double precision`, `money`)
       D-07 ni bekor qiladi, YO'QOLGAN tip esa ustunning jimgina
       o'chirilganini bildiradi.
    """
    found: dict[str, set[str]] = {}
    for table in NOTIFICATION_TABLES:
        for column, data_type in _columns(sync_app_conn, table).items():
            found.setdefault(data_type, set()).add(f"{table}.{column}")

    assert set(found) == ALLOWED_DATA_TYPES, (
        "bildirishnoma jadvallarining tip to'plami kutilganidan farq qiladi.\n"
        f"  ORTIQCHA tiplar: "
        f"{ {t: sorted(found[t]) for t in sorted(set(found) - ALLOWED_DATA_TYPES)} }\n"
        f"  YO'QOLGAN tiplar: {sorted(ALLOWED_DATA_TYPES - set(found))}\n"
        "Har ikkala yo'nalish ham ONGLI qaror talab qiladi."
    )


def test_notification_tables_have_rls_enabled_and_forced(
    sync_app_conn: Connection[TupleRow], migrated: None
) -> None:
    """Beshala jadvalda RLS `ENABLE` + `FORCE` + tenant policy (T-07-20).

    =========================================================================
    UCHALASI HAM KERAK VA UCHALASI HAM ALOHIDA BUZILISHI MUMKIN:

      * `ENABLE` yo'q -> policy TA'SIRSIZ, jadval hamma uchun OCHIQ.
        `alembic-utils` `ENABLE`/`FORCE` ni BILMAYDI, ya'ni `PGPolicy`
        yaratilgan bo'lsa ham jadval qo'riqsiz qolishi mumkin (Pitfall 10);
      * `FORCE` yo'q -> jadval EGASI (migratsiya roli) policy'dan chetda
        qoladi va ega bilan ochilgan har qanday sessiya butun platformani
        ko'radi;
      * tenant policy yo'q -> RLS bor, lekin deny-all: xavfsiz, lekin
        ilova umuman ishlamaydi va nosozlik prodda birinchi so'rovda
        ko'rinardi.

    ⚠ TEKSHIRUV `sbozor_app` ULANISHI BILAN: `pg_policies` ko'rinishi
      rolga bog'liq emas, lekin butun fayl ilova roli ko'radigan haqiqat
      ustidan yuradi (`conftest.py` ning birinchi qoidasi).
    =========================================================================
    """
    problems: list[str] = []
    for table in NOTIFICATION_TABLES:
        row = sync_app_conn.execute(RLS_FLAGS, (table,)).fetchone()
        assert row is not None, f"`{table}` `pg_class` da topilmadi — migratsiya bajarilmagan"
        enabled, forced = bool(row[0]), bool(row[1])
        if not enabled:
            problems.append(f"{table}: `ENABLE ROW LEVEL SECURITY` yo'q")
        if not forced:
            problems.append(f"{table}: `FORCE ROW LEVEL SECURITY` yo'q")

        policies = {str(r[0]) for r in sync_app_conn.execute(POLICY_NAMES, (table,)).fetchall()}
        if TENANT_POLICY_NAME not in policies:
            problems.append(f"{table}: `{TENANT_POLICY_NAME}` policy'si yo'q (mavjud: {policies})")

    assert problems == [], "bildirishnoma jadvallarida RLS to'liq emas:\n  " + "\n  ".join(problems)


def test_case_target_constraints_exist(sync_app_conn: Connection[TupleRow], migrated: None) -> None:
    """Case AYNAN BITTA o'zgarmas qatorga ishora qiladi — TO'RT CHEKLOV (DQ-5).

    =========================================================================
    HAR BIRI BOSHQA NOSOZLIKNI YOPADI VA BIRORTASI YOLG'IZ YETARLI EMAS:

      fk_reconciliation_cases_anomaly / _charge (KOMPOZIT, `market_id` bilan)
          -> begona bozorning dalili STRUKTURAVIY yetib kelmaydi. Yagona
             ustunli FK `market_id` ni tekshirmasdi va A bozorining
             case'i B bozorining anomaliyasiga ishora qila olardi.

      CHECK subject_is_exclusive  (XOR)
          -> IKKI dalil ham, DALILSIZLIK ham imkonsiz. `OR` shakli
             ikkalasi to'ldirilgan holatni O'TKAZARDI.

      CHECK subject_kind_matches_target  (IKKI TOMONLAMA TENGLIK)
          -> diskriminator ustundan ajralib keta olmaydi. Usiz hisobot
             «ro'yxatga olinmagan savdo» deb sanagan qator aslida hisob
             qatoriga ishora qilardi va ikki sinfning nisbati (RECON-01
             ning butun mazmuni) noto'g'ri chiqardi.

    Ikki QISMAN UNIQUE indeks esa D-21: bir anomaliyaga/hisobga BIR case.
    ⚠ QISMANLIK `pg_index.indpred` DAN o'qiladi va u MAJBURIY: to'liq
      UNIQUE indeks `anomaly_id IS NULL` bo'lgan BARCHA hisob case'larini
      bir-biriga to'qnashtirardi.
    =========================================================================
    """
    checks = _constraint_names(sync_app_conn, "reconciliation_cases", "c")
    foreign_keys = _constraint_names(sync_app_conn, "reconciliation_cases", "f")

    expected_checks = {
        "ck_reconciliation_cases_subject_is_exclusive",
        "ck_reconciliation_cases_subject_kind_matches_target",
    }
    assert expected_checks <= checks, (
        f"`reconciliation_cases` da kutilgan `CHECK` yo'q: "
        f"{sorted(expected_checks - checks)}. Mavjudlari: {sorted(checks)}."
    )

    expected_fks = {"fk_reconciliation_cases_anomaly", "fk_reconciliation_cases_charge"}
    assert expected_fks <= foreign_keys, (
        f"`reconciliation_cases` da kutilgan kompozit FK yo'q: "
        f"{sorted(expected_fks - foreign_keys)}. Mavjudlari: {sorted(foreign_keys)}."
    )

    for index in ("uq_reconciliation_cases_anomaly", "uq_reconciliation_cases_charge"):
        row = sync_app_conn.execute(PARTIAL_INDEX, (index,)).fetchone()
        assert row is not None, (
            f"`{index}` indeksi bazada YO'Q — ikkinchi case ochilishini "
            "faqat ilova mantig'i to'xtatardi va u `recon.open` ning ikki "
            "parallel yugurishida ishlamasdi (D-21)."
        )
        assert bool(row[0]), (
            f"`{index}` QISMAN emas: {row[1]!r} — predikatsiz UNIQUE "
            "indeks `NULL` ustundagi barcha qatorlarni keraksiz qamrardi "
            "va niyatni yashirardi."
        )
        assert "UNIQUE" in str(row[1]), f"`{index}` UNIQUE emas: {row[1]!r}"


def test_case_events_are_append_only(
    sync_owner_conn: Connection[TupleRow], market_domain: MarketDomainSeed
) -> None:
    """Case tarixi HAQIQATAN append-only — `UPDATE` RAD ETILADI (D-14, T-07-09).

    =========================================================================
    ⛔ XULQIY O'LCHOV, SHAKL EMAS — VA BU FARQ 07-02 NING OCHIQ BANDI EDI.

    O'sha reja triggerning ULANGANINI tekshira oldi (`trg_case_event_
    immutable` mavjud), lekin `UPDATE` ning HAQIQATAN rad etilishini
    o'lchay olmadi: buning uchun HAQIQIY case qatori kerak, u esa
    `billing_anomalies` seed'ini talab qiladi (kompozit FK). Shakl va
    xulq ALOHIDA buzilishi mumkin: trigger joyida turib, funksiyasi
    `RETURN NEW` bilan qayta yozilgan bo'lishi mumkin — o'shanda
    shakl testi yashil, tarix esa TAHRIRLANADIGAN bo'lardi.

    «Tahrirlanadigan tarix — tarix EMAS»: case tarixi «kim, qachon,
    qaysi holatdan qaysi holatga o'tkazdi» degan savolning YAGONA javobi
    va u nizoda (D-02) dalil bo'ladi.
    =========================================================================

    ⚠ SEED `sbozor_owner` BILAN: `reconciliation_case_events` FORCE RLS
      ostida va yozish `owner_bootstrap` policy'si orqali o'tadi. Rad
      etish esa TRIGGER darajasida, ya'ni u rolga bog'liq emas —
      `sbozor_app` uchun ham aynan shu javob keladi.
    """
    market_id = market_domain.market_a.market_id
    stall_id = market_domain.market_a.stall_ids[0]
    event_id = _seed_case_with_event(sync_owner_conn, market_id=market_id, stall_id=stall_id)

    try:
        with pytest.raises(psycopg.errors.RaiseException) as excinfo:
            sync_owner_conn.execute(
                "UPDATE reconciliation_case_events SET note = %s WHERE id = %s",
                ("tarix qayta yozilmoqda", str(event_id)),
            )
        assert "append-only" in str(excinfo.value), (
            f"qo'riqchi boshqa sababdan yiqildi: {excinfo.value!r} — xato "
            "xabari QAYSI qoida buzilganini aytishi kerak."
        )
    finally:
        _cleanup_case_chain(sync_owner_conn, market_id=market_id)


def test_no_new_security_definer_function_was_added(
    sync_app_conn: Connection[TupleRow], migrated: None
) -> None:
    """⛔ G7-7 — `0023` birorta yangi `SECURITY DEFINER` funksiya qo'shmadi (T-06-22).

    =========================================================================
    YANGI DEFINER FUNKSIYA — RLS'NI CHETLAB O'TADIGAN YANGI YUZA.

    `SECURITY DEFINER` funksiya EGA huquqi bilan ishlaydi, ya'ni tenant
    predikati unga QO'LLANMAYDI. Har bir shunday funksiya — bozorlararo
    o'qishning potensial yo'li va uning yuzasi (nima qaytaradi) alohida
    tekshirilishi kerak. Shuning uchun ularning SONI o'sishi ONGLI qaror
    bo'lishi shart, yon ta'sir emas.

    `0023` bu yuzani KENGAYTIRMAYDI: `market_delete_draft(uuid)` ning
    faqat TANASI kengaydi (endi u 34 jadvaldan `DELETE` qiladi), IMZOSI
    o'zgarmadi va yangi funksiya umuman tug'ilmadi.

    ⛔ SOLISHTIRUV TO'PLAM TENGLIGI BILAN, `>=` BILAN EMAS — VA AYNAN SHU
       YERDA BU TEST `test_meta.py::test_security_definer_functions_pin_
       search_path` DAN FARQ QILADI. U yerdagi da'vo `found >=
       EXPECTED_DEFINER_FUNCTIONS`, ya'ni u ORTIQCHA nomni UMUMAN
       KO'RMAYDI: yangi definer funksiya qo'shilsa o'sha test YASHIL
       qolardi (u faqat yangi funksiyaning `search_path` ini talab
       qilardi). Bo'shliq shu yerda yopiladi.
    =========================================================================
    """
    from tenancy.test_meta import EXPECTED_DEFINER_FUNCTIONS

    assert len(EXPECTED_DEFINER_FUNCTIONS) == PHASE_SIX_DEFINER_COUNT, (
        f"`EXPECTED_DEFINER_FUNCTIONS` sanog'i o'zgargan: "
        f"{len(EXPECTED_DEFINER_FUNCTIONS)} (6-fazada {PHASE_SIX_DEFINER_COUNT} edi). "
        "Reyestrga nom qo'shish RLS'ni chetlab o'tadigan yangi yuza "
        "demakdir va u 7-fazada ATAYIN qo'shilmaydi."
    )

    expected = frozenset(EXPECTED_DEFINER_FUNCTIONS) | EXTRA_DEFINER_FUNCTIONS
    found = {str(row[0]) for row in sync_app_conn.execute(DEFINER_FUNCTIONS).fetchall()}

    assert found == expected, (
        "bazadagi `SECURITY DEFINER` funksiyalar to'plami kutilganidan farq qiladi.\n"
        f"  YANGI (kutilmagan): {sorted(found - expected)}\n"
        f"  YO'QOLGAN: {sorted(expected - found)}\n"
        "Yangi definer funksiya — RLS'ni chetlab o'tadigan YANGI YUZA "
        "(T-06-22): u ega huquqi bilan ishlaydi va tenant predikatiga "
        "bo'ysunmaydi. Yo'qolgani esa login yoki bozor hayot siklining "
        "buzilishini bildiradi."
    )


# ===========================================================================
# XULQIY TEST UCHUN MINIMAL ZANJIR
#
# ⚠ NEGA BU YERDA VA NEGA `fixtures/notification_domain.py` DA EMAS:
#   fixture moduli QUYI OQIM rejalari (07-05…07-13) uchun yozilgan va
#   uning `seed_case()` i nishonni CHAQIRUVCHIDAN oladi. Bu yerdagi test
#   esa nishonni O'ZI yaratishi kerak — `billing_anomalies` qatori
#   bo'lmasa case'ni umuman yozib bo'lmaydi (kompozit FK).
# ===========================================================================

_INSERT_ANOMALY = (
    "INSERT INTO billing_anomalies (id, market_id, kind, stall_id, service_date) "
    "VALUES (%s, %s, %s, %s, %s)"
)
"""⚠ `kind = 'no_coverage_stall'` ATAYIN: AYNAN shu qiymatda ikkala
juftlangan `CHECK` ham (`no_coverage_is_paired`, `evidence_is_paired`)
dalil ustunlarining `NULL` bo'lishini TALAB qiladi, ya'ni bu yagona
anomaliya sinfi bo'lib, u `occupancy_events` va `snapshots` seed'isiz
qonuniy yoziladi. Boshqa `kind` da zanjir butun bandlik qatlamini
talab qilardi."""

_INSERT_CASE = (
    "INSERT INTO reconciliation_cases "
    "(id, market_id, subject_kind, anomaly_id, service_date) VALUES (%s, %s, %s, %s, %s)"
)

_INSERT_CASE_EVENT = (
    "INSERT INTO reconciliation_case_events (id, market_id, case_id, from_status, to_status) "
    "VALUES (%s, %s, %s, NULL, %s)"
)


def _seed_case_with_event(conn: Connection[TupleRow], *, market_id: UUID, stall_id: UUID) -> UUID:
    """`anomaliya -> case -> case hodisasi` zanjirini yozadi va hodisa `id` sini qaytaradi."""
    anomaly_id, case_id, event_id = uuid4(), uuid4(), uuid4()

    conn.execute(
        _INSERT_ANOMALY,
        (
            str(anomaly_id),
            str(market_id),
            "no_coverage_stall",
            str(stall_id),
            _ANOMALY_SERVICE_DATE,
        ),
    )
    conn.execute(
        _INSERT_CASE,
        (str(case_id), str(market_id), "anomaly", str(anomaly_id), _ANOMALY_SERVICE_DATE),
    )
    conn.execute(_INSERT_CASE_EVENT, (str(event_id), str(market_id), str(case_id), "new"))
    return event_id


def _cleanup_case_chain(conn: Connection[TupleRow], *, market_id: UUID) -> None:
    """Zanjirni bolalardan otaga o'chiradi.

    ⚠ AVVAL BOZOR QORALAMAGA QAYTARILADI VA BUSIZ TOZALASH YIQILADI:
      `case_event_immutable()` `DELETE` ni FAQAT bozor nofaol bo'lganda
      o'tkazadi (`market_delete_draft()` ning yo'li). Bayroqni tushirish
      bu yerda semantik jihatdan HALOL — `market_domain` / `two_markets`
      fixture'lari bozorni bir necha satr keyin baribir shu holatda
      o'chiradi (`cleanup_billing_domain()` bilan bir xil naqsh).
    """
    conn.execute("UPDATE markets SET is_active = false WHERE id = %s", (str(market_id),))
    for table in ("reconciliation_case_events", "reconciliation_cases", "billing_anomalies"):
        conn.execute(
            f"DELETE FROM {table} WHERE market_id = %s",  # noqa: S608
            (str(market_id),),
        )
    conn.execute("UPDATE markets SET is_active = true WHERE id = %s", (str(market_id),))
