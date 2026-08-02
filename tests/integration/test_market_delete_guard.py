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

from psycopg import Connection
from psycopg.rows import TupleRow

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

# 2026-08-03 holati: `ALL_TENANT_TABLES` ning o'n ikkitasi. Quyi chegara
# `0012` dan keyin ham to'g'ri bo'lib qolaveradi (jadvallar faqat qo'shiladi).
KNOWN_TENANT_TABLE_COUNT = 12

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
