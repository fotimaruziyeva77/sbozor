"""NVR domenining META-INVARIANTLARI — to'rtta, hammasi `pg_catalog` dan.

=============================================================================
NEGA BU FAYL MODELNI IMPORT QILMAYDI.

`sbozor_core.models.nvr` — ISTALGAN holat. Bazadagi sxema esa HAQIQIY holat.
Ikkisi ajralib qolishi mumkin (migratsiya qo'llanmagan, `op.create_index(...)`
unutilgan, kimdir qo'lda `ALTER TABLE` qilgan) va aynan o'sha holatda
modeldan o'qiydigan test JIMGINA yashil qolardi — ya'ni u eng kerakli paytda
ishlamasdi. `tests/tenancy/test_market_domain_meta.py` shu qoidani 2-fazada
o'rnatgan, bu fayl uni davom ettiradi.

TO'RTTA INVARIANT VA HAR BIRI QAYSI DA'VONI QULFLAYDI:

  1. `UNIQUE (market_id, nvr_id, channel_no)` — SC#2 ning YAGONA DB kafolati.
  2. `nvr_credentials` da audit trigger YO'Q — SC#4 (shifrmatn `audit_log` ga
     tushmaydi).
  3. `cameras` da `rtsp_url` ustuni YO'Q — URL hosila, ikkinchi haqiqat
     manbai tug'ilmaydi.
  4. `nvr_discovery_runs` da qisman UNIQUE — bir vaqtda ikki skan bloklanadi.

Uchtasi INKOR/MAVJUDLIK da'vosi va ular avtomatik invariantlar
(`test_meta.py` ning beshtasi) bilan QOPLANMAYDI: o'sha yerdagi testlar
`market_id` + RLS + policy + indeks tartibini tekshiradi, bu yerdagilar esa
domenning O'Z qarorlarini.
=============================================================================
"""

from __future__ import annotations

import psycopg
import pytest
from fixtures.nvr_domain import nvr_rows
from fixtures.two_markets import TwoMarketSeed
from psycopg import Connection
from psycopg.rows import TupleRow

pytestmark = pytest.mark.tenancy

CHANNEL_UNIQUE_COLUMNS = ["market_id", "nvr_id", "channel_no"]

UNIQUE_CONSTRAINT_COLUMNS = """
SELECT con.conname,
       array_agg(att.attname ORDER BY key.ord)
FROM pg_constraint con
JOIN pg_class c ON c.oid = con.conrelid
JOIN pg_namespace n ON n.oid = c.relnamespace
JOIN LATERAL unnest(con.conkey) WITH ORDINALITY AS key(attnum, ord) ON true
JOIN pg_attribute att ON att.attrelid = c.oid AND att.attnum = key.attnum
WHERE n.nspname = 'public'
  AND c.relname = %s
  AND con.contype = 'u'
GROUP BY con.conname
"""
"""Jadvalning UNIQUE konstraytlari — ustunlar E'LON TARTIBIDA.

Tartib saqlanadi (`WITH ORDINALITY`), chunki da'voning o'zi tartibga
bog'liq: `market_id` BIRINCHI bo'lishi tenant invarianti #5 ning sharti.
`(nvr_id, market_id, channel_no)` bir xil to'plam bo'lardi-yu, indeks
`market_id` bilan boshlanmasdi.
"""

NON_INTERNAL_TRIGGERS = """
SELECT tg.tgname
FROM pg_trigger tg
JOIN pg_class c ON c.oid = tg.tgrelid
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public'
  AND c.relname = %s
  AND NOT tg.tgisinternal
ORDER BY tg.tgname
"""
"""Jadvalga ULANGAN triggerlar (FK uchun yaratilgan ichkilaridan tashqari).

`tgisinternal` filtri MAJBURIY: composite FK har bir jadvalga ichki
trigger qo'yadi va usiz "trigger yo'q" da'vosi HECH QACHON rost
bo'lmasdi — ya'ni test doim qizil bo'lardi va sabab noto'g'ri joyda
qidirilardi.
"""

TABLE_COLUMNS = """
SELECT column_name
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = %s
ORDER BY column_name
"""

PARTIAL_UNIQUE_INDEXES = """
SELECT i.relname,
       pg_get_expr(x.indpred, x.indrelid),
       array_agg(att.attname ORDER BY key.ord)
FROM pg_index x
JOIN pg_class t ON t.oid = x.indrelid
JOIN pg_class i ON i.oid = x.indexrelid
JOIN pg_namespace n ON n.oid = t.relnamespace
JOIN LATERAL unnest(x.indkey) WITH ORDINALITY AS key(attnum, ord) ON true
JOIN pg_attribute att ON att.attrelid = t.oid AND att.attnum = key.attnum
WHERE n.nspname = 'public'
  AND t.relname = %s
  AND x.indisunique
  AND x.indpred IS NOT NULL
GROUP BY i.relname, pg_get_expr(x.indpred, x.indrelid)
"""
"""QISMAN UNIQUE indekslar — predikati bilan birga.

`indpred IS NOT NULL` — aynan "qisman" ning ta'rifi. To'liq UNIQUE bu
yerga tushmaydi va bu MUHIM: `nvr_discovery_runs` da to'liq
`UNIQUE(market_id, nvr_id)` bo'lsa u BITTA kashfiyot tarixini ham
bloklardi (har NVR ga umrbod bitta yugurish) — ya'ni noto'g'ri konstrayt
bu testdan o'tolmaydi.
"""


def _unique_constraints(conn: Connection[TupleRow], table: str) -> dict[str, list[str]]:
    return {
        str(row[0]): [str(col) for col in row[1]]
        for row in conn.execute(UNIQUE_CONSTRAINT_COLUMNS, (table,)).fetchall()
    }


def _triggers(conn: Connection[TupleRow], table: str) -> list[str]:
    return [str(row[0]) for row in conn.execute(NON_INTERNAL_TRIGGERS, (table,)).fetchall()]


def _columns(conn: Connection[TupleRow], table: str) -> list[str]:
    return [str(row[0]) for row in conn.execute(TABLE_COLUMNS, (table,)).fetchall()]


def test_cameras_channel_is_unique_per_nvr(
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    migrated: None,
) -> None:
    """SC#2 ning DB kafolati — KATALOGDA bor VA xom `INSERT` da `23505` beradi.

    =========================================================================
    NEGA IKKI TOMONLAMA O'LCHANADI.

    Faqat katalogni tekshirish "konstrayt e'lon qilingan" ni isbotlardi,
    "u ishlaydi" ni emas: noto'g'ri ustunlar to'plami ham `contype='u'`
    bo'lib turaveradi. Faqat `INSERT` ni tekshirish esa konstraytning
    QAYSI biri ishlaganini ajratmasdi (`uq_cameras_stream_name` ham `23505`
    beradi) — shuning uchun dublikat qatorga ATAYIN BOSHQA `stream_name`
    beriladi va yagona qolgan sabab kanal noyobligi bo'ladi.

    NEGA BU ILOVA QATLAMIDA YETARLI EMAS: ikki parallel skan «avval
    tekshir, keyin yoz» naqshida IKKALASI ham bo'sh holatni ko'radi va
    ikkalasi ham yozadi. Natijada bitta kanalga ikkita qator tug'ilardi va
    5-fazada zona qaysi biriga bog'langani TASODIFGA bog'liq bo'lib
    qolardi (T-03-15). 2-fazadagi `stall_code_registry` falsafasi bilan
    aynan bir xil: qoida ILOVADA emas, DB'da.
    =========================================================================
    """
    constraints = _unique_constraints(sync_owner_conn, "cameras")
    matching = [name for name, cols in constraints.items() if cols == CHANNEL_UNIQUE_COLUMNS]

    assert matching, (
        f"`cameras` da {CHANNEL_UNIQUE_COLUMNS} ustidagi UNIQUE konstrayt YO'Q. "
        f"Mavjudlari: {constraints}. Busiz parallel skanlar bitta kanal uchun "
        "ikkita qator yaratadi (SC#2 buziladi)."
    )

    with nvr_rows(sync_owner_conn, two_markets) as seed:
        a = seed.market_a
        with pytest.raises(psycopg.errors.UniqueViolation) as excinfo:
            sync_owner_conn.execute(
                "INSERT INTO cameras (market_id, nvr_id, channel_no, stream_name, name) "
                "VALUES (%s, %s, %s, %s, %s)",
                (
                    str(a.market_id),
                    str(a.nvr_id),
                    # AYNAN mavjud kanal.
                    a.camera_channels[0],
                    # BOSHQA `stream_name` — aks holda `uq_cameras_stream_name`
                    # ham `23505` berardi va qaysi konstrayt ishlagani
                    # noaniq qolardi.
                    "cam_probe_duplicate_channel",
                    "Dublikat kanal probe'i",
                ),
            )

        assert excinfo.value.sqlstate == "23505", (
            f"kutilgan `23505` (unique_violation), olindi {excinfo.value.sqlstate}"
        )


def test_nvr_credentials_has_no_audit_trigger(
    sync_owner_conn: Connection[TupleRow], migrated: None
) -> None:
    """`nvr_credentials` da BIRORTA trigger yo'q — SC#4 (T-03-13).

    =========================================================================
    `fn_audit_row()` `to_jsonb(NEW)` YOZADI. Trigger bu jadvalga ulansa
    Fernet SHIFRMATNI `audit_log.new_value` ga tushardi. Bu ochiq matn
    emas, LEKIN kalit buzilganda u TARIXIY parollarni ham beradi — ya'ni
    `audit_log` (append-only, o'chirib BO'LMAYDIGAN jadval) eng uzoq
    yashaydigan sir omboriga aylanardi.

    Test AYNAN `nvr_devices` ni NAZORAT sifatida oladi: agar so'rov
    noto'g'ri yozilgan bo'lsa (sxema nomi xato, `tgisinternal` filtri
    teskari) u HAR IKKALA jadval uchun ham bo'sh qaytarardi va yuqoridagi
    inkor da'vosi JIMGINA rost bo'lib qolardi. Nazorat bandi shu yo'lni
    yopadi: `nvr_devices` da trigger BO'LISHI shart.
    =========================================================================
    """
    secret_triggers = _triggers(sync_owner_conn, "nvr_credentials")

    assert secret_triggers == [], (
        f"`nvr_credentials` da trigger(lar) topildi: {secret_triggers}. "
        "Bu jadvalga HECH QANDAY trigger ulanmasligi kerak — `fn_audit_row()` "
        "`to_jsonb(NEW)` yozadi va Fernet shifrmatni `audit_log` ga tushardi "
        "(kalit buzilganda TARIXIY parollar ochilardi)."
    )

    # NAZORAT: so'rov haqiqatan trigger topa oladimi?
    device_triggers = _triggers(sync_owner_conn, "nvr_devices")
    assert "trg_audit_nvr_devices" in device_triggers, (
        f"`nvr_devices` da audit triggeri topilmadi ({device_triggers}) — "
        "so'rov buzilgan bo'lishi mumkin, bunday holatda yuqoridagi inkor "
        "da'vosi hech nimani o'lchamasdi"
    )


def test_cameras_has_no_rtsp_url_column(
    sync_owner_conn: Connection[TupleRow], migrated: None
) -> None:
    """`cameras` da `rtsp_url` ustuni YO'Q — URL HOSILA (`03-RESEARCH.md` A.2).

    =========================================================================
    Ustun qo'shilsa IKKITA haqiqat manbai paydo bo'lardi va ikkalasi ham
    noto'g'ri tomonga ketardi:

      * NVR ning IP'si yoki RTSP porti o'zgarganda BITTA qator emas, 25 ta
        kamera URL'i yangilanishi kerak bo'lardi — bittasi unutilsa jonli
        ko'rish JIMGINA eski manzilga urinardi;
      * `rtsp://user:pass@host/...` shakli sirni `cameras` jadvaliga, ya'ni
        AUDIT TRIGGERI ULANGAN jadvalga olib kirardi — yuqoridagi
        `nvr_credentials` ajratishining butun ma'nosi bekor bo'lardi.

    Bu test aynan «qulaylik uchun» qo'shilgan ustunni ushlaydi: u kod
    ko'rikda ko'rinmasligi mumkin, chunki bitta `sa.Column(...)` satri
    zararsiz ko'rinadi.

    NAZORAT BANDI: `channel_no` va `stream_name` MAVJUD bo'lishi
    tekshiriladi — so'rov noto'g'ri jadval nomiga borsa (yoki sxema
    filtri xato bo'lsa) u bo'sh ro'yxat qaytarib, inkor da'vosini
    ma'nosiz qilardi.
    =========================================================================
    """
    columns = _columns(sync_owner_conn, "cameras")

    assert columns, "`cameras` jadvalining ustunlari topilmadi — so'rov buzilgan"
    assert "rtsp_url" not in columns, (
        "`cameras` da `rtsp_url` ustuni paydo bo'lgan. URL `nvr_devices.host` + "
        "`rtsp_port` + `channel_no` dan SOF FUNKSIYADA hosil qilinadi; ustun "
        "ikkinchi haqiqat manbai tug'diradi va sirni audit ostidagi jadvalga "
        "olib kiradi."
    )
    for expected in ("channel_no", "stream_name"):
        assert expected in columns, (
            f"kutilgan ustun `{expected}` topilmadi ({columns}) — so'rov buzilgan "
            "bo'lishi mumkin va inkor da'vosi hech nimani o'lchamasdi"
        )


def test_discovery_runs_block_a_second_active_scan(
    sync_owner_conn: Connection[TupleRow], migrated: None
) -> None:
    """`nvr_discovery_runs` da QISMAN UNIQUE indeks bor va u FAOL holatlarni qamraydi.

    =========================================================================
    Ikki skan bir vaqtda ishlasa NVR ga ikki barobar yuk va ikki barobar
    `401` urinishi tushadi — Hikvision hisobi QULFLANISHI mumkin va
    o'shanda butun bozor kamerasiz qoladi (T-03-16).

    INDEKS QISMAN BO'LISHI SHART, to'liq emas. To'liq
    `UNIQUE(market_id, nvr_id)` bir NVR ga umrbod BITTA yugurish qatorini
    ruxsat etardi, ya'ni kashfiyot TARIXI umuman yozilmasdi. Shuning
    uchun so'rov `indpred IS NOT NULL` bilan filtrlanadi va predikat
    ichida `queued` HAM, `running` HAM borligi tekshiriladi: faqat
    bittasi qolsa ikkinchi holat qulfsiz o'tib ketardi.
    =========================================================================
    """
    rows = sync_owner_conn.execute(PARTIAL_UNIQUE_INDEXES, ("nvr_discovery_runs",)).fetchall()

    assert rows, (
        "`nvr_discovery_runs` da QISMAN UNIQUE indeks topilmadi — bir NVR "
        "uchun ikkita faol kashfiyot bir vaqtda ishga tushishi mumkin."
    )

    matching = [
        (str(name), str(predicate), [str(col) for col in columns])
        for name, predicate, columns in rows
        if [str(col) for col in columns] == ["market_id", "nvr_id"]
    ]
    assert matching, (
        f"qisman UNIQUE indeks `(market_id, nvr_id)` ustida EMAS: {rows}. "
        "Boshqa ustunlar to'plami bir NVR uchun ikkinchi skanni bloklamaydi."
    )

    name, predicate, _ = matching[0]
    for status in ("queued", "running"):
        assert status in predicate, (
            f"`{name}` indeksining predikati (`{predicate}`) `{status}` holatini "
            "QAMRAMAYDI — o'sha holatdagi ikkinchi yugurish qulfsiz o'tib ketadi."
        )
    for finished in ("succeeded", "failed"):
        assert finished not in predicate, (
            f"`{name}` indeksining predikati yakunlangan `{finished}` holatini ham "
            "qamrayapti — bu kashfiyot TARIXINI bloklaydi (har NVR ga umrbod "
            "bitta yugurish)."
        )
