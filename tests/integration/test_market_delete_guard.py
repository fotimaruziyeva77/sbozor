"""`market_delete_draft()` kaskadining TO'LIQLIK darvozasi (W0-7 / D-17, T-03-05).

=============================================================================
BU FAYLNING YAGONA VAZIFASI — MUDDATNI MAJBURLASH.

`market_delete_draft()` o'n ikki jadval bo'ylab kaskad o'chiradi va uning
yagona chegarasi bugun — FUNKSIYA TANASIDAGI QO'LDA YOZILGAN RO'YXAT.
`ON DELETE CASCADE` ATAYIN ishlatilmagan (sabab `migrations/entities/
functions.py::MARKET_DELETE_DRAFT` docstringida: kaskad 6-fazada
`payments`/`daily_charges` ga JIMGINA tarqalib, haqiqiy moliyaviy tarixni
o'chirib yuborardi).

Qo'lda yozilgan ro'yxatning narxi shu: yangi tenant jadvali qo'shgan odam
bu funksiyani ham yangilashi SHART. Unutsa — `DELETE FROM public.markets`
chet el kaliti buzilishi bilan yiqiladi va bu FAQAT ISH PAYTIDA, qoralama
bozorni o'chirmoqchi bo'lgan admin ekranida ko'rinadi.

`0012_nvr_domain` (03-03) AYNAN shunday to'rtta jadval olib keladi
(`nvr_devices`, `cameras`, `nvr_credentials`, `nvr_discovery_runs`).
Bu test o'sha kunni ISH PAYTIDAN CI'GA ko'chiradi.
=============================================================================

NEGA FUNKSIYA TANASI BAZADAN O'QILADI, PYTHON MANBASIDAN EMAS:
`migrations/entities/functions.py` — bu ISTALGAN holat. Bazadagi funksiya
esa HAQIQIY holat. Ikkisi ajralib qolishi mumkin (migratsiya
qo'llanmagan, `op.replace_entity(...)` unutilgan, qo'lda `CREATE OR
REPLACE` qilingan) va aynan o'sha holatda manba faylini o'qiydigan test
JIMGINA yashil qolardi — ya'ni u eng kerakli paytda ishlamasdi.

NEGA "market_id USTUNI BOR" EMAS, "markets GA FK BOR":
O'lchandi (2026-08-03): `audit_log` da `market_id` ustuni BOR, lekin
`markets` ga chet el kaliti YO'Q. Ya'ni ustun bo'yicha izlaydigan so'rov
13 jadval topardi va `audit_log` ni kaskaddan "yetishmayotgan" deb
ko'rsatib, darvozani BUGUNOQ YOLG'ON-QIZIL qilardi. Bundan ham yomoni —
"tuzatish" yo'li audit jurnalini kaskadga qo'shish bo'lardi, ya'ni bozor
o'chirilganda uning butun DALIL IZI ham yo'q bo'lardi.

Chegara aynan FK: `DELETE FROM markets` ni yiqitadigan narsa — chet el
kaliti, ustun nomi emas. Ya'ni so'rov "nima buzilishi mumkin" degan
savolni o'lchaydi, "nima o'xshab turibdi" ni emas.
"""

from __future__ import annotations

import re
from uuid import UUID

import psycopg
import pytest
from fixtures.nvr_domain import add_discovery_run, nvr_rows
from fixtures.snapshot_domain import snapshot_rows
from fixtures.two_markets import TwoMarketSeed
from psycopg import Connection
from psycopg.rows import TupleRow

NVR_TABLES: tuple[str, ...] = ("cameras", "nvr_discovery_runs", "nvr_credentials", "nvr_devices")
"""03-03 qo'shgan to'rt jadval — kaskad TO'LIQ qamrashi kerak bo'lganlari."""

SNAPSHOT_TABLES: tuple[str, ...] = (
    "snapshots",
    "capture_runs",
    "snapshot_schedule_slots",
    "snapshot_schedules",
    "alert_events",
)
"""04-03 qo'shgan besh jadval — `0015` kaskadga qo'shishi kerak bo'lganlari.

TARTIB `migrations.entities.SNAPSHOT_DELETE_ORDER` bilan bir xil, lekin bu
yerda u faqat O'QISH uchun: test qatorlarni SANAYDI, o'chirmaydi. Ro'yxat
reyestrdan IMPORT QILINMAYDI — `tests/integration/` `migrations` paketiga
bog'lanmaydi va, muhimrog'i, reyestrdan olingan ro'yxat reyestrning O'ZI
xato bo'lganda test bilan BIRGA xato bo'lardi.
"""

TABLES_REFERENCING_MARKETS = """
SELECT DISTINCT c.relname
FROM pg_constraint con
JOIN pg_class c ON c.oid = con.conrelid
JOIN pg_namespace n ON n.oid = c.relnamespace
JOIN pg_class ref ON ref.oid = con.confrelid
JOIN pg_namespace refn ON refn.oid = ref.relnamespace
WHERE con.contype = 'f'
  AND n.nspname = 'public'
  AND refn.nspname = 'public'
  AND ref.relname = 'markets'
  AND c.relkind = 'r'
ORDER BY c.relname
"""
"""`public.markets` ga chet el kaliti bilan bog'langan jadvallar.

`pg_constraint` ishlatiladi (`information_schema` emas): oxirgisi
o'zining ko'rinishlarini joriy rolning grant'lari bo'yicha filtrlaydi,
ya'ni huquqi tor rol ostida jimgina KAM jadval qaytarardi va darvoza
sababsiz yashil bo'lib qolardi.
"""

FUNCTION_BODY = "SELECT pg_get_functiondef('public.market_delete_draft(uuid)'::regprocedure)"

# 2026-08-04 holati: `ALL_TENANT_TABLES` ning o'n yettitasi (12 + `0014` ning
# beshtasi). Quyi chegara jadvallar faqat QO'SHILGANI uchun to'g'ri bo'lib
# qolaveradi; uni ko'tarish esa MAJBURIY, aks holda `0014` ning beshta
# jadvali tushib qolgan taqdirda ham quyi chegara qanoatlanardi va
# `test_reference_query_actually_finds_the_tenant_tables` darvozasi o'z
# vazifasini bajarmasdi.
KNOWN_TENANT_TABLE_COUNT = 17

# Tuzatish yo'riqnomasi ALOHIDA konstantada, f-satr ICHIDA emas: ruff'ning
# `S608` qoidasi SQL kalit so'zi bo'lgan formatlangan satrni "so'rov
# qurilishi" deb hisoblaydi va bu yerda YOLG'ON-MUSBAT berardi (bu — xato
# XABARI, so'rov emas). Matnni oddiy satrga ko'chirish qoidani chetlab
# o'tmaydi, uni QO'LLANILMAYDIGAN qiladi.
CASCADE_FIX_HINT = (
    "Tuzatish: `migrations/entities/functions.py::MARKET_DELETE_DRAFT` tanasiga "
    "`DELETE FROM public.<jadval> WHERE market_id = p_market_id;` qatorini qo'shing "
    "(FK bo'yicha BOLALARDAN ota-onaga tartibida) va migratsiyada "
    "`op.replace_entity(...)` bilan qo'llang."
)


def _tables_referencing_markets(conn: Connection[TupleRow]) -> list[str]:
    return [row[0] for row in conn.execute(TABLES_REFERENCING_MARKETS).fetchall()]


def _function_body(conn: Connection[TupleRow]) -> str:
    row = conn.execute(FUNCTION_BODY).fetchone()
    assert row is not None, (
        "`market_delete_draft(uuid)` bazada topilmadi — migratsiya qo'llanmagan "
        "yoki funksiya imzosi o'zgargan"
    )
    body: str = row[0]
    return body


def _deleted_tables_in_order(body: str) -> list[str]:
    """Funksiya tanasidagi `DELETE FROM public.<jadval>` lar — YOZILGAN TARTIBDA.

    Tartib saqlanadi, chunki kaskadning to'g'riligi unga bog'liq: FK
    bo'yicha bolalardan ota-onaga borilmasa, funksiya o'z-o'zini yiqitardi.
    """
    return re.findall(r"DELETE\s+FROM\s+public\.(\w+)", body)


def test_cascade_covers_every_table_referencing_markets(
    sync_app_conn: Connection[TupleRow], migrated: None
) -> None:
    """HAR BIR bog'langan jadval kaskadda bor — yetishmagani NOMMA-NOM aytiladi.

    Bu darvozaning butun mazmuni. U bugun YASHIL (o'n ikki jadval, hammasi
    ro'yxatda) va `0012_nvr_domain` yangi tenant jadvalini olib kelgan
    zahoti QIZARADI — ya'ni kaskadni kengaytirish qarzi 03-03 ning
    oynasidan tashqariga chiqa olmaydi.
    """
    referencing = _tables_referencing_markets(sync_app_conn)
    body = _function_body(sync_app_conn)

    missing = [
        table
        for table in referencing
        if not re.search(rf"DELETE\s+FROM\s+public\.{re.escape(table)}\b", body)
    ]

    assert not missing, (
        f"`market_delete_draft()` kaskadida {sorted(missing)} YO'Q. "
        "Bu jadval(lar) `markets` ga chet el kaliti bilan bog'langan, ya'ni "
        "qoralama bozorni o'chirish chet el kaliti buzilishi bilan yiqiladi "
        "va sabab faqat ish paytida ko'rinadi.\n" + CASCADE_FIX_HINT
    )


def test_reference_query_actually_finds_the_tenant_tables(
    sync_app_conn: Connection[TupleRow], migrated: None
) -> None:
    """QUYI CHEGARA: so'rov bo'sh to'plam qaytarsa darvoza ma'nosini yo'qotadi.

    Usiz `pg_constraint` so'rovi noto'g'ri yozilganda (sxema nomi xato,
    `contype` boshqa harf, `confrelid` o'rniga `conrelid`) yuqoridagi test
    HECH NIMANI tekshirmasdan yashil qolardi — "0 ta yetishmayotgan
    jadval" har doim rost.
    """
    referencing = _tables_referencing_markets(sync_app_conn)

    assert len(referencing) >= KNOWN_TENANT_TABLE_COUNT, (
        f"`markets` ga bog'langan atigi {len(referencing)} jadval topildi "
        f"({sorted(referencing)}), kutilgani kamida {KNOWN_TENANT_TABLE_COUNT}. "
        "So'rov buzilgan bo'lishi mumkin — bunday holatda to'liqlik testi "
        "JIMGINA yashil qoladi."
    )
    # Nazorat qiymatlari: 2-fazadan beri mavjud va nomlari o'zgarmagan.
    for table in ("stalls", "vendors", "stall_assignments"):
        assert table in referencing, f"kutilgan tenant jadvali `{table}` topilmadi"


def test_markets_is_the_tenant_itself_and_is_deleted_last(
    sync_app_conn: Connection[TupleRow], migrated: None
) -> None:
    """NAZORAT HOLATI: `markets` ro'yxatga KIRMAYDI va OXIRGI o'chiriladi.

    Ikki alohida da'vo, ikkalasi ham kerak:

    1. `markets` — tenant jadvali EMAS, tenantning O'ZI (unda `market_id`
       ustuni yo'q, `id` bor). U yuqoridagi to'plamga tushib qolsa, darvoza
       o'z shartini SOXTA kengaytirgan bo'lardi va "markets kaskadda bormi"
       degan ma'nosiz savolni tekshirardi.
    2. U funksiyaning OXIRGI `DELETE` i. Ota-ona bolalardan oldin
       o'chirilsa, funksiya har safar o'z FK'siga urilib yiqilardi.
    """
    referencing = _tables_referencing_markets(sync_app_conn)
    assert "markets" not in referencing, (
        "`markets` o'ziga o'zi havola qiladigan bo'lib qolgan — u tenantning "
        "O'ZI, tenant jadvali emas"
    )

    deleted = _deleted_tables_in_order(_function_body(sync_app_conn))

    assert deleted, "funksiya tanasida birorta `DELETE FROM public.*` topilmadi"
    assert deleted[-1] == "markets", (
        f"kaskadning oxirgi `DELETE` i `{deleted[-1]}`, `markets` emas — "
        "ota-ona qatori bolalaridan oldin o'chirilsa funksiya FK buzilishi "
        "bilan yiqiladi"
    )
    assert deleted.count("markets") == 1, "`markets` bir marta o'chirilishi kerak"


def test_audit_log_deliberately_survives_market_deletion(
    sync_app_conn: Connection[TupleRow], migrated: None
) -> None:
    """`audit_log` kaskadda ATAYIN YO'Q — va bu o'lchangan fakt (D-10, 1-faza).

    =========================================================================
    Bu test darvozaning shartini TESKARI yo'nalishda qulflaydi.

    `audit_log` da `market_id` ustuni BOR, lekin `markets` ga chet el
    kaliti YO'Q — aynan shuning uchun bozor o'chirilganda uning dalil izi
    saqlanib qoladi va `DELETE FROM markets` baribir yiqilmaydi.

    Agar kimdir kelajakda `audit_log.market_id` ga FK qo'shsa, yuqoridagi
    to'liqlik testi qizaradi va "tuzatish" ning eng oson yo'li uni
    kaskadga qo'shish bo'lardi — ya'ni jurnal o'chirilishi mumkin bo'lgan
    yagona yo'l aynan shu tarzda, XATONI TUZATISH niqobi ostida
    ochilardi. Bu test o'sha yo'lni yopadi: FK qo'shilsa BU test ham
    qizaradi va qaror ataylab qilingan bo'lishi kerak bo'ladi.
    =========================================================================
    """
    referencing = _tables_referencing_markets(sync_app_conn)
    deleted = _deleted_tables_in_order(_function_body(sync_app_conn))

    assert "audit_log" not in referencing, (
        "`audit_log` endi `markets` ga FK bilan bog'langan — bu o'zgarish "
        "audit yozuvlarini kaskadga tortadi va jurnalning o'chmasligi "
        "kafolatini buzadi (1-faza D-10)"
    )
    assert "audit_log" not in deleted, (
        "`market_delete_draft()` audit jurnalini o'chiryapti — bozor "
        "o'chirilganda uning butun DALIL IZI yo'qoladi"
    )


# ===========================================================================
# 03-03 — WR-02 NING IKKINCHI YARMI: KAFOLAT ENDI O'LCHANADI, SANALMAYDI
# ===========================================================================
#
# Yuqoridagi to'rt test funksiyaning TANASINI o'qiydi, ya'ni ular
# "ro'yxat to'liqmi?" degan savolga javob beradi. Quyidagi uchtasi esa
# funksiyani HAQIQATAN CHAQIRADI va natijani qatorlar bo'yicha o'lchaydi —
# ikki xil savol va ikkalasi ham kerak: to'liq ro'yxat noto'g'ri TARTIBDA
# bo'lsa yuqoridagilar yashil qolardi-yu, chaqiruv FK buzilishi bilan
# yiqilardi.


def _rows_for_market(conn: Connection[TupleRow], table: str, market_id: UUID) -> int:
    row = conn.execute(
        f"SELECT count(*) FROM {table} WHERE market_id = %s",  # noqa: S608
        (str(market_id),),
    ).fetchone()
    assert row is not None
    return int(row[0])


def _delete_draft(conn: Connection[TupleRow], market_id: UUID) -> bool:
    row = conn.execute("SELECT market_delete_draft(%s)", (str(market_id),)).fetchone()
    assert row is not None
    return bool(row[0])


def test_draft_market_deletion_covers_the_nvr_domain(
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    migrated: None,
) -> None:
    """Qoralama bozor to'rtala NVR jadvali bilan birga o'chadi; B bozori TEGILMAYDI.

    Bu `0013` ning ASOSIY da'vosi va u yuqoridagi statik darvozadan
    MUSTAQIL: u yerda funksiya MATNI o'qiladi, bu yerda esa funksiya
    CHAQIRILADI. Tartib noto'g'ri bo'lsa (masalan `nvr_devices` bolalaridan
    OLDIN o'chirilsa) matn baribir to'liq ko'rinardi, chaqiruv esa FK
    buzilishi bilan yiqilardi.

    ⚠ IKKINCHI BOZOR NAZORAT SIFATIDA: A o'chirilgandan keyin B ning
    qatorlari JOYIDA qolishi tekshiriladi. Usiz `WHERE market_id = ...`
    predikati butunlay yo'qolgan taqdirda ham (ya'ni kaskad HAMMA bozorni
    tozalab yuborganda) test yashil bo'lardi.
    """
    with nvr_rows(sync_owner_conn, two_markets) as seed:
        a, b = seed.market_a, seed.market_b
        # Seed B bozoriga ATAYIN yugurish yozmaydi («bo'sh ro'yxat»
        # stsenariysi uchun). Pastdagi cross-tenant nazorati esa B da
        # HAR TO'RT jadvalda ham qator bo'lishini talab qiladi — aks holda
        # `nvr_discovery_runs` bo'yicha predikat yo'qolgan taqdirda ham
        # test yashil qolardi.
        add_discovery_run(sync_owner_conn, b)

        for table in NVR_TABLES:
            assert _rows_for_market(sync_owner_conn, table, a.market_id) > 0, (
                f"seed `{table}` ga A bozori uchun qator yozmagan — test "
                "o'chirishni emas, bo'sh jadvalni o'lchagan bo'lardi"
            )

        # Bozor QORALAMAGA qaytariladi: `market_delete_draft()` faol bozorga
        # ATAYIN tegmaydi (keyingi test aynan shuni o'lchaydi).
        sync_owner_conn.execute(
            "UPDATE markets SET is_active = false WHERE id = %s", (str(a.market_id),)
        )

        assert _delete_draft(sync_owner_conn, a.market_id) is True, (
            "`market_delete_draft()` qoralama bozor uchun `false` qaytardi"
        )

        for table in NVR_TABLES:
            remaining = _rows_for_market(sync_owner_conn, table, a.market_id)
            assert remaining == 0, f"`{table}` da A bozorining {remaining} ta YETIM qatori qoldi"

        row = sync_owner_conn.execute(
            "SELECT count(*) FROM markets WHERE id = %s", (str(a.market_id),)
        ).fetchone()
        assert row is not None and int(row[0]) == 0, "qoralama bozor qatori o'chmadi"

        # NAZORAT: B bozori butunlay tegilmagan.
        for table in NVR_TABLES:
            assert _rows_for_market(sync_owner_conn, table, b.market_id) > 0, (
                f"`{table}` da B bozorining qatorlari ham o'chib ketdi — kaskad "
                "`WHERE market_id = ...` predikatini yo'qotgan bo'lishi mumkin"
            )


def test_draft_market_deletion_covers_the_snapshot_domain(
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    migrated: None,
) -> None:
    """Qoralama bozor BESHALA snapshot jadvali bilan birga o'chadi; B TEGILMAYDI.

    Bu `0015` ning ASOSIY da'vosi va u yuqoridagi statik darvozadan
    MUSTAQIL: u yerda funksiya MATNI o'qiladi, bu yerda esa funksiya
    CHAQIRILADI.

    ⚠ TARTIB AYNAN SHU YERDA O'LCHANADI. `capture_runs` `cameras` ga
    kompozit FK bilan tayanadi, `cameras` esa kaskadning BIRINCHI `DELETE`
    i (3-fazadan). Ya'ni snapshot bloki NVR blokidan KEYIN qo'yilsa matn
    baribir TO'LIQ ko'rinardi (statik darvoza yashil), chaqiruv esa chet el
    kaliti buzilishi bilan yiqilardi — va bu faqat qoralama bozorni
    o'chirmoqchi bo'lgan admin ekranida ko'rinardi.

    ⚠ IKKINCHI BOZOR NAZORAT SIFATIDA: A o'chirilgandan keyin B ning
    qatorlari JOYIDA qolishi tekshiriladi. Usiz `WHERE market_id = ...`
    predikati butunlay yo'qolgan taqdirda ham (ya'ni kaskad HAMMA bozorni
    tozalab yuborganda) test yashil bo'lardi.
    """
    # ⚠ TARTIB MUHIM VA U `with` NING CHIQISH TARTIBIDA QULFLANGAN: snapshot
    #   seed'i NVR seed'ining ICHIDA ochiladi, ya'ni tozalash TESKARI ketadi
    #   (avval `capture_runs`, keyin `cameras`). Teskari joylashuv
    #   `nvr_domain` ning tozalashini `cameras` ga hali `capture_runs` tayanib
    #   turgan paytda ishga tushirardi va FK buzilishi bilan yiqilardi.
    with (
        nvr_rows(sync_owner_conn, two_markets) as nvr,
        snapshot_rows(sync_owner_conn, nvr) as seed,
    ):
        a, b = seed.market_a, seed.market_b

        for table in SNAPSHOT_TABLES:
            assert _rows_for_market(sync_owner_conn, table, a.market_id) > 0, (
                f"seed `{table}` ga A bozori uchun qator yozmagan — test "
                "o'chirishni emas, bo'sh jadvalni o'lchagan bo'lardi"
            )

        # Bozor QORALAMAGA qaytariladi: `market_delete_draft()` faol bozorga
        # ATAYIN tegmaydi (quyidagi test aynan shuni o'lchaydi).
        sync_owner_conn.execute(
            "UPDATE markets SET is_active = false WHERE id = %s", (str(a.market_id),)
        )

        assert _delete_draft(sync_owner_conn, a.market_id) is True, (
            "`market_delete_draft()` qoralama bozor uchun `false` qaytardi — "
            "beshta yangi jadval kaskadga qo'shilmagan bo'lishi mumkin"
        )

        for table in SNAPSHOT_TABLES:
            remaining = _rows_for_market(sync_owner_conn, table, a.market_id)
            assert remaining == 0, (
                f"`{table}` da A bozorining {remaining} ta YETIM qatori qoldi — "
                "kadr metama'lumoti bozor tashrifchilarining shaxsiy "
                "ma'lumotiga havola qiladi (T-04-20)"
            )
        # NVR domeni ham o'chgan bo'lishi shart: snapshot bloki uni
        # BLOKLAMASLIGI kerak (tartib to'g'ri bo'lsa ikkalasi ham ketadi).
        for table in NVR_TABLES:
            assert _rows_for_market(sync_owner_conn, table, a.market_id) == 0, (
                f"`{table}` da A bozorining qatorlari qoldi — snapshot bloki "
                "NVR blokini bloklab qo'ygan bo'lishi mumkin"
            )

        row = sync_owner_conn.execute(
            "SELECT count(*) FROM markets WHERE id = %s", (str(a.market_id),)
        ).fetchone()
        assert row is not None and int(row[0]) == 0, "qoralama bozor qatori o'chmadi"

        # NAZORAT: B bozori butunlay tegilmagan.
        for table in SNAPSHOT_TABLES:
            assert _rows_for_market(sync_owner_conn, table, b.market_id) > 0, (
                f"`{table}` da B bozorining qatorlari ham o'chib ketdi — kaskad "
                "`WHERE market_id = ...` predikatini yo'qotgan bo'lishi mumkin"
            )


def test_active_market_survives_market_delete_draft(
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    migrated: None,
) -> None:
    """FAOL bozorda `market_delete_draft()` `false` qaytaradi VA hech nima o'chmaydi.

    Ikki da'vo, ikkalasi ham kerak: `false` qaytarib, lekin baribir bir
    nechta jadvalni tozalab yuborgan funksiya eng yomon holat bo'lardi —
    chaqiruvchi "o'chmadi" deb hisoblardi, ma'lumot esa yo'qolgan bo'lardi.
    """
    with nvr_rows(sync_owner_conn, two_markets) as seed:
        b = seed.market_b
        # Seed B ga yugurish yozmaydi — to'rtala jadvalni ham o'lchash uchun
        # qator shu yerda qo'shiladi (`add_discovery_run()` docstringi).
        add_discovery_run(sync_owner_conn, b)

        before = {
            table: _rows_for_market(sync_owner_conn, table, b.market_id) for table in NVR_TABLES
        }
        assert all(count > 0 for count in before.values()), before

        assert _delete_draft(sync_owner_conn, b.market_id) is False, (
            "`market_delete_draft()` FAOL bozor uchun `true` qaytardi — "
            "jonli bozorni o'chirish yo'li ochilib qolgan"
        )

        after = {
            table: _rows_for_market(sync_owner_conn, table, b.market_id) for table in NVR_TABLES
        }
        assert after == before, f"faol bozorda qatorlar o'zgardi: {before} -> {after}"

        row = sync_owner_conn.execute(
            "SELECT count(*) FROM markets WHERE id = %s", (str(b.market_id),)
        ).fetchone()
        assert row is not None and int(row[0]) == 1, "faol bozor qatori o'chib ketdi"


def test_active_market_cannot_be_deleted_by_raw_sql(
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    migrated: None,
) -> None:
    """SC#8 / WR-02 NING YAGONA TO'G'RIDAN-TO'G'RI ISBOTI (T-03-17).

    =========================================================================
    Bu test ilova qatlamini BUTUNLAY chetlab o'tadi: u `market_delete_draft()`
    ni chaqirmaydi, HTTP so'rov yubormaydi — u to'g'ridan-to'g'ri
    `DELETE FROM markets` yozadi, aynan `psql` dan yozilganidek.

    `0013` gacha bu urinish MUVAFFAQIYATLI bo'lardi: "faol bozorni o'chirib
    bo'lmaydi" kafolati faqat `market_delete_draft()` tanasidagi `IF` da
    yashardi va o'sha `IF` ni chetlab o'tish uchun funksiyani chaqirmaslik
    kifoya edi. Ya'ni kafolat ilova qatlamining odob-axloqiga tayanardi,
    SXEMAGA emas. Xato yozilgan kelajakdagi `SECURITY DEFINER` funksiya
    ham xuddi shu teshikdan o'tardi.

    ⚠ ULANISH ROLI AHAMIYATLI: test `sbozor_owner` bilan yozadi — ya'ni
    MIGRATSIYA huquqiga ega rol bilan. Trigger `SECURITY DEFINER` emas va
    hech qanday rolga istisno bermaydi, shuning uchun ega ham undan
    o'tolmaydi. `sbozor_app` bilan sinash zaifroq bo'lardi: unga `markets`
    ustida `DELETE` grant'i umuman berilmagan, ya'ni urinish TRIGGERGA
    yetib bormasdan `permission denied` bilan tugardi va biz butunlay
    boshqa mexanizmni o'lchagan bo'lardik.
    =========================================================================
    """
    with nvr_rows(sync_owner_conn, two_markets) as seed:
        b = seed.market_b

        # `CheckViolation` = SQLSTATE `23514` — `markets_delete_guard()` ning
        # `USING ERRCODE` i. Kod `tariff_past_immutable()` /
        # `category_period_past_immutable()` bilan AYNAN bir xil va bu
        # ataylab: uchalasi ham "domen qoidasi buzildi" sinfida va
        # chaqiruvchi ularni bitta yo'lda 409 ga aylantiradi.
        with pytest.raises(psycopg.errors.CheckViolation) as exc:
            sync_owner_conn.execute("DELETE FROM markets WHERE id = %s", (str(b.market_id),))

        assert exc.value.sqlstate == "23514", (
            f"kutilgan `23514` (check_violation), olindi {exc.value.sqlstate}"
        )
        message = str(exc.value)
        assert str(b.market_id) in message, (
            f"xato xabari qaysi bozor rad etilganini aytmayapti: {message!r}"
        )

        row = sync_owner_conn.execute(
            "SELECT count(*) FROM markets WHERE id = %s", (str(b.market_id),)
        ).fetchone()
        assert row is not None and int(row[0]) == 1, (
            "istisno ko'tarildi, lekin bozor baribir o'chib ketdi — trigger "
            "`BEFORE` emas, `AFTER` bo'lib qolgan bo'lishi mumkin"
        )
