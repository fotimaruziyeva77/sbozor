"""Fazaning BESHTA muvaffaqiyat mezoni — ROADMAP matni bilan bog'langan YAGONA fayl.

=============================================================================
BU FAYL MAVJUD TESTLARNI TAKRORLAMAYDI — U ULARNI MEZON DARAJASIDA BOG'LAYDI.

Har mezonning qismlari allaqachon qamralgan va ular o'z egasida qoladi:

  * `test_wizard_flow.py`      (02-11) — ustaning har bir darvozasi;
  * `test_stall_registry.py`   (02-08) — reestr endpointining xulqi;
  * `test_stall_code_reuse.py` (02-07) — kod reyestri, xom SQL yo'li bilan;
  * `test_tariff_history.py`   (02-07) — tarif tarixining SXEMA isboti;
  * `test_tariffs_api.py`      (02-09) — boshlang'ich narx uchtaligi;
  * `test_market_calendar.py`  (02-07) — `market_is_open()` ning uch qavati;
  * `test_stall_assignments.py`(02-07) — D-09…D-12 davr mexanikasi;
  * `stall-map.test.tsx`       (02-14) — xaritaning KO'RINISH tomoni.

Bu yerdagi savol boshqa va u faqat shu yerda beriladi: **ROADMAP'da yozilgan
jumla bugun rostmi?** Har test docstringi mezon matnini SO'ZMA-SO'Z olib
yuradi, ya'ni ROADMAP tahrirlanganda mos kelmaslik ko'zga tashlanadi.

NEGA BU KERAK: mezon qismlarga bo'linganda har bir qism yashil bo'lib,
BUTUN da'vo baribir yolg'on bo'lishi mumkin. Eng ehtimolli shakl —
qismlar ORASIDAGI uzilish: usta har bir endpointi ishlaydi-yu, zanjirning
o'rtasida 403 chiqadi; tarif API'si to'g'ri yozadi-yu, "D sanadagi narx"
so'rovi boshqa qatorni topadi; xarita katagi `has_vendor: true` deydi-yu,
karta sotuvchisiz ochiladi.
=============================================================================

⚠ SC#5 NING KO'RINISH TOMONI BU YERDA EMAS. Grid render, katakning
bosilishi va kartaning ochilishi `frontend/src/components/stalls/
stall-map.test.tsx` (02-14) da qamralgan; bu fayl AYNAN API SHARTNOMASINI
tekshiradi (nima qaytadi, qanday tartibda, qaysi maydonlar bilan).
Ikkalasi birga mezonni yopadi — birortasi yolg'iz o'zi yopmaydi.

SANALAR `market_today` DAN HISOBLANADI, SOBIT YOZILMAYDI (02-07 dev. #1).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import TYPE_CHECKING, Any
from uuid import UUID

import psycopg
import pytest
from fixtures.admin_api import (
    ACTIVATE_URL,
    ASSIGNMENTS_URL,
    CALENDAR_URL,
    CATEGORIES_URL,
    MARKETS_URL,
    SETUP_STATUS_URL,
    STALLS_URL,
    TARIFFS_URL,
    VENDORS_URL,
    ZONES_URL,
    session_headers,
)
from fixtures.auth_api import SELECT_MARKET_URL
from fixtures.market_domain import A_CATEGORY_NAMES, A_TARIFF_AMOUNTS
from fixtures.two_markets import SEED_PASSWORD

if TYPE_CHECKING:
    from collections.abc import Iterator

    import httpx
    from fixtures import MarketDomainSeed, MarketScope
    from fixtures.two_markets import TwoMarketSeed
    from psycopg import Connection
    from psycopg.rows import TupleRow

# ---------------------------------------------------------------------------
# Kontrakt so'rovlari — 6-fazaga BERILADIGAN shakllarning o'zi
# ---------------------------------------------------------------------------

PRICE_AT = (
    "SELECT amount_soum FROM tariffs "
    "WHERE market_id = %s AND category_id = %s AND valid_from <= %s::date "
    "ORDER BY valid_from DESC LIMIT 1"
)
"""«D sanadagi amaldagi tarif» — 6-fazaning hisob-kitobi AYNAN shu shaklni oladi.

Qator TOPILMASA javob `None` bo'ladi, `0` EMAS (D-08 fail-closed): tarifsiz
kun bepul kun emas, ANOMALIYA.
"""

IS_OPEN = "SELECT market_is_open(%s, %s::date)"
"""6-fazaning kunlik job'i aynan shu shartni `WHERE` bandiga yozadi —
"o'sha kunga patta hisoblanmaydi" da'vosining MEXANIZMI shu."""

AUDIT_FOR_ROW = (
    "SELECT action, changed_keys, old_value, new_value FROM audit_log "
    "WHERE market_id = %s AND table_name = %s AND row_id = %s "
    "ORDER BY id"
)

TAMPER_UPDATE = "UPDATE audit_log SET action = 'tampered'"
TAMPER_DELETE = "DELETE FROM audit_log"

# ---------------------------------------------------------------------------
# SC#1 uchun konstantalar
# ---------------------------------------------------------------------------

SC1_TIMEZONE = "Asia/Tashkent"
SC1_ZONES = ("Mezon markaziy", "Mezon sharqiy")
SC1_CATEGORIES = ("Mezon sabzavot", "Mezon go'sht")
SC1_STALLS = ("7101", "7102", "7103")
SC1_AMOUNTS = (6_000, 14_000)
SC1_WEEKDAYS = (1, 2, 3, 4, 5, 6)
SC1_VENDOR_PHONE = "+998909992001"
"""Seed, matritsa va `test_wizard_flow.py` diapazonlaridan TASHQARIDA.

`market_domain` `+99890111000X`, `two_markets` `+99897…`, matritsa
`+998909990001`, usta oqimi testi `+99890999100X` ni band qilgan.
"""

OPERATING_SINCE_DAYS = 180
"""`operating_since` qancha kun ORQADA — Karmana holatiga mos (bozor yillar
davomida ishlagan). O'tmish bo'lishi SHART: 4-qadamdagi boshlang'ich narx
tarmog'i aks holda umuman bosilmasdi."""

FUTURE_DAYS = 30
"""Yangi tarif kuchga kiradigan kun — `market_today` dan hisoblanadi."""


@dataclass(frozen=True, slots=True)
class Call:
    """Usta oqimidagi bitta chaqiruv — YORLIQ bilan.

    Yorliqsiz "birorta 403 yo'q" da'vosi qizarganda QAYSI qadam
    to'xtaganini aytmasdi, ya'ni xabar "usta ishlamayapti" dan nariga
    o'tmasdi.
    """

    label: str
    status: int


def _assert_no_refusals(calls: list[Call]) -> None:
    """Shu paytgacha bo'lgan chaqiruvlarda 403 YO'QLIGINI tekshiradi.

    ⚠ BU YORDAMCHI HAR BOSQICHDAN KEYIN CHAQIRILADI, FAQAT OXIRIDA EMAS —
    va sabab O'LCHANGAN. Dastlabki yozuvda tekshiruv faqat oxirida turardi;
    `PLATFORM_ADMIN` dan `STALL_MANAGE` olib tashlangan sabotajda test
    ROSTDAN qizardi, lekin xabar `ValueError: zip() argument 2 is longer
    than argument 1` bo'ldi — ya'ni 3-qadam 403 olgani uchun ro'yxat bo'sh
    qolib, KEYINGI bosqich texnik xato bilan qulagan edi.

    Aynan shu Pitfall 6 ning haqiqiy ko'rinishi bo'lgani uchun bu yerdagi
    diagnostika mezonning bir qismi: "usta ishlamayapti" xabari qaysi
    qadamni tuzatish kerakligini AYTMAYDI.
    """
    forbidden = [call.label for call in calls if call.status == 403]
    assert forbidden == [], f"usta oqimida 403 olingan qadamlar: {forbidden}"


# ---------------------------------------------------------------------------
# Fixture'lar
# ---------------------------------------------------------------------------


@pytest.fixture
def built_markets(sync_owner_conn: Connection[TupleRow]) -> Iterator[list[UUID]]:
    """SC#1 yaratgan bozorlarni ro'yxatga oladi va oxirida o'chiradi.

    Tozalash MAHSULOT funksiyasi bilan (`market_delete_draft()`) — u o'n
    uchta jadvalning tartibini biladi va yangi jadval qo'shilganda YAGONA
    yangilanadigan joy bo'lib qoladi.

    ⚠ AVVAL BAYROQ TUSHIRILADI: mezon testi bozorni FAOLLASHTIRADI,
    `market_delete_draft()` esa jonli bozorga ATAYIN tegmaydi — ya'ni
    deaktivatsiyasiz teardown jimgina hech nima o'chirmasdi va keyingi
    testlar o'sib boradigan `GET /markets` ro'yxatini ko'rardi.
    """
    market_ids: list[UUID] = []
    try:
        yield market_ids
    finally:
        for market_id in market_ids:
            sync_owner_conn.execute(
                "UPDATE markets SET is_active = false WHERE id = %s", (str(market_id),)
            )
            sync_owner_conn.execute("SELECT market_delete_draft(%s)", (str(market_id),))


@pytest.fixture
async def admin_headers(
    api_client: httpx.AsyncClient,
    two_markets: TwoMarketSeed,
    market_domain: MarketDomainSeed,
) -> dict[str, str]:
    """A bozori adminining sessiyasi.

    `market_domain` ATAYIN argument sifatida olinadi: domen qatlami
    sessiyadan OLDIN yozilishi kerak, aks holda birinchi so'rov bo'sh
    reestrni ko'rardi va mezon da'volari "hech narsa yo'q" holatida ham
    yashil bo'lardi.
    """
    market_a = two_markets.market_a
    return await session_headers(api_client, market_a.admin_phone, market_a.admin_password)


# ===========================================================================
# SC#1
# ===========================================================================


async def test_sc1_platform_admin_builds_a_market_without_code(
    api_client: httpx.AsyncClient,
    two_markets: TwoMarketSeed,
    built_markets: list[UUID],
    market_today: date,
) -> None:
    """SC#1 — «Platforma admini ustadan o'tib yangi bozor yaratadi (rekvizit →
    zona → rasta → toifa → tarif) va oxirida bozor ishlashga tayyor holatda
    ko'rinadi — kod yozilmaydi».

    IKKI DA'VO VA IKKALASI HAM MEZONNING BIR QISMI:

    1. **"Kod yozilmaydi"** — butun zanjir FAQAT ochiq HTTP endpointlaridan
       o'tadi: birorta xom `INSERT`, birorta `sbozor_owner` ulanishi va
       birorta migratsiya qadami yo'q. Shuning uchun bu test `sync_owner_conn`
       ni faqat TEARDOWN uchun oladi (`built_markets`), oqimning O'ZIDA emas.
    2. **Oqim davomida birorta chaqiruv 403 BERMAYDI.** Bu alohida assert va
       u alohida bo'lishi shart: Pitfall 6 (platforma adminida `STALL_MANAGE`
       yo'qligi) aynan shu shaklda ko'rinadi — har bir endpoint alohida
       to'g'ri, matritsa esa zanjirning o'rtasida JIMGINA rad etadi.

    ⚠ Bu test `test_wizard_flow.py` ni takrorlamaydi: u yerda har bir
    DARVOZA (chala bozor, qayta faollashtirish, o'chirish, audit) alohida
    sinaladi. Bu yerdagi yagona savol — ZANJIR uzilmaydimi.
    """
    operating_since = market_today - timedelta(days=OPERATING_SINCE_DAYS)
    calls: list[Call] = []

    headers = await session_headers(api_client, two_markets.platform_admin_phone, SEED_PASSWORD)

    created = await api_client.post(
        MARKETS_URL,
        json={
            "name": "Mezon bozori",
            "timezone": SC1_TIMEZONE,
            "operating_since": operating_since.isoformat(),
        },
        headers=headers,
    )
    calls.append(Call("1-qadam: POST /markets", created.status_code))
    assert created.status_code == 201, created.text
    market_id = UUID(created.json()["id"])
    built_markets.append(market_id)

    selected = await api_client.post(
        SELECT_MARKET_URL, json={"market_id": str(market_id)}, headers=headers
    )
    calls.append(Call("bozorni tanlash", selected.status_code))
    assert selected.status_code == 200, selected.text
    tenant = {"Authorization": f"Bearer {selected.json()['access_token']}"}

    zone_ids: list[UUID] = []
    for name in SC1_ZONES:
        response = await api_client.post(ZONES_URL, json={"name": name}, headers=tenant)
        calls.append(Call(f"2-qadam: POST /zones ({name})", response.status_code))
        if response.status_code == 201:
            zone_ids.append(UUID(response.json()["id"]))
    _assert_no_refusals(calls)

    category_ids: list[UUID] = []
    for name in SC1_CATEGORIES:
        response = await api_client.post(CATEGORIES_URL, json={"name": name}, headers=tenant)
        calls.append(Call(f"3-qadam: POST /categories ({name})", response.status_code))
        if response.status_code == 201:
            category_ids.append(UUID(response.json()["id"]))
    _assert_no_refusals(calls)

    for category_id, amount in zip(category_ids, SC1_AMOUNTS, strict=True):
        # `valid_from` = `operating_since`, ya'ni O'TMISHDAGI sana. Bu yo'l
        # QORALAMA bozorda ochiq (02-09 boshlang'ich narx istisnosi) va
        # SC#3 testi uni AYNAN teskari tomondan — faol bozorda YOPIQ
        # ekanini — o'lchaydi.
        response = await api_client.post(
            TARIFFS_URL,
            json={
                "category_id": str(category_id),
                "amount_soum": amount,
                "valid_from": operating_since.isoformat(),
            },
            headers=tenant,
        )
        calls.append(Call(f"4-qadam: POST /tariffs ({amount})", response.status_code))
    _assert_no_refusals(calls)

    for index, code in enumerate(SC1_STALLS):
        response = await api_client.post(
            STALLS_URL,
            json={
                "code": code,
                "zone_id": str(zone_ids[index % len(zone_ids)]),
                "category_id": str(category_ids[index % len(category_ids)]),
            },
            headers=tenant,
        )
        calls.append(Call(f"5-qadam: POST /stalls ({code})", response.status_code))
    _assert_no_refusals(calls)

    vendor = await api_client.post(
        VENDORS_URL,
        json={"full_name": "Mezon Sotuvchisi", "phone": SC1_VENDOR_PHONE},
        headers=tenant,
    )
    calls.append(Call("6-qadam: POST /vendors", vendor.status_code))

    weekdays = await api_client.put(
        f"{CALENDAR_URL}/weekdays", json={"open_weekdays": list(SC1_WEEKDAYS)}, headers=tenant
    )
    calls.append(Call("7-qadam: PUT /calendar/weekdays", weekdays.status_code))

    status_response = await api_client.get(
        SETUP_STATUS_URL.format(market_id=market_id), headers=tenant
    )
    calls.append(Call("GET setup-status", status_response.status_code))

    activated = await api_client.post(ACTIVATE_URL.format(market_id=market_id), headers=tenant)
    calls.append(Call("faollashtirish", activated.status_code))

    listed = await api_client.get(MARKETS_URL, headers=tenant)
    calls.append(Call("GET /markets", listed.status_code))

    # --- 1-da'vo: birorta qadam RAD ETILMADI ---
    _assert_no_refusals(calls)
    unexpected = [(call.label, call.status) for call in calls if call.status not in {200, 201}]
    assert unexpected == [], f"kutilmagan javob kodlari: {unexpected}"

    # --- 2-da'vo: bozor OXIRIDA ishlashga tayyor ---
    assert status_response.json()["can_activate"] is True, status_response.text
    assert status_response.json()["blocking"] == []
    assert activated.json()["is_active"] is True
    entry = next(item for item in listed.json() if item["id"] == str(market_id))
    assert entry["is_active"] is True, (
        "bozor faollashtirish javobida `is_active: true`, ro'yxatda esa boshqacha — "
        "yozuv va o'qish yo'llari ajralib ketgan"
    )


# ===========================================================================
# SC#2
# ===========================================================================


async def test_sc2_registry_changes_are_audited(
    api_client: httpx.AsyncClient,
    two_markets: TwoMarketSeed,
    market_domain: MarketDomainSeed,
    market_scope: MarketScope,
    sync_app_conn: Connection[TupleRow],
    admin_headers: dict[str, str],
    market_today: date,
) -> None:
    """SC#2 — «Bozor admini rastalar va sotuvchilar reestrini yuritadi: rasta
    holati (faol/ta'mirda/yopiq), toifasi va sotuvchi biriktirish davri
    o'zgaradi, har o'zgarish auditda ko'rinadi».

    MEZON UCH XIL O'ZGARISHNI SANAYDI VA ULARNING AUDIT SHAKLI HAR XIL —
    aynan shu farq bu testning qiymati:

      * **holat** va **kod** -> `stalls` ustida `update`: `old -> new`
        juftligi bor va `changed_keys` o'zgargan ustunni nomlaydi;
      * **toifa** -> `stall_category_periods` ustida **`insert`** (D-04,
        voris modeli): eski davr TAHRIRLANMAYDI, ya'ni bu yerda `old`
        BO'LMAYDI va uni talab qilish mezonni noto'g'ri o'qish bo'lardi;
      * **biriktirish davri** -> `stall_assignments` ustida `update`,
        `period` maydonining `old -> new` i bilan (D-10: davr chegarasi
        qarz EGALIGINI belgilaydi).

    Oxirgi banddan keyin YOZUVNING O'ZI himoyalanganini ham o'lchaymiz:
    audit jurnali append-only, ya'ni "har o'zgarish auditda ko'rinadi"
    da'vosi kuchini o'zgarishni yozib, keyin izni o'chirish bilan
    yo'qotib bo'lmaydi.
    """
    market_a = two_markets.market_a
    domain_a = market_domain.market_a
    stall_id = domain_a.unassigned_stall_id
    assert stall_id is not None, "seed `unassigned_stall_id` bermadi"

    # --- 1. HOLAT ---
    status_change = await api_client.patch(
        f"{STALLS_URL}/{stall_id}", json={"status": "maintenance"}, headers=admin_headers
    )
    assert status_change.status_code == 200, status_change.text

    # --- 2. KOD (D-02: bo'shagan raqam qayta ishlatilmaydi) ---
    code_change = await api_client.patch(
        f"{STALLS_URL}/{stall_id}", json={"code": "7999"}, headers=admin_headers
    )
    assert code_change.status_code == 200, code_change.text

    # --- 3. TOIFA (kelajakdagi sanadan — o'tmish yopiq, D-04) ---
    new_category = domain_a.category_ids[1]
    assert domain_a.category_by_stall[stall_id] != new_category, (
        "seed shu rastaga ALLAQACHON shu toifani bergan — o'zgarish o'lchanmasdi"
    )
    category_change = await api_client.post(
        f"{STALLS_URL}/{stall_id}/category",
        json={
            "category_id": str(new_category),
            "valid_from": (market_today + timedelta(days=FUTURE_DAYS)).isoformat(),
        },
        headers=admin_headers,
    )
    assert category_change.status_code == 201, category_change.text

    # --- 4. BIRIKTIRISH DAVRI ---
    gap_stall = domain_a.gap_stall_id
    assert gap_stall is not None, "seed `gap_stall_id` bermadi"
    history = await api_client.get(f"{STALLS_URL}/{gap_stall}/assignments", headers=admin_headers)
    assert history.status_code == 200, history.text
    open_period = next(item for item in history.json()["items"] if item["to_date"] is None)
    assignment_id = open_period["id"]
    closed_at = date.fromisoformat(open_period["from_date"]) + timedelta(days=5)

    close = await api_client.patch(
        f"{ASSIGNMENTS_URL}/{assignment_id}",
        json={"to_date": closed_at.isoformat()},
        headers=admin_headers,
    )
    assert close.status_code == 200, close.text
    assert close.json()["to_date"] == closed_at.isoformat()

    # --- AUDIT ---
    with market_scope(market_a.id) as conn:
        stall_rows = conn.execute(
            AUDIT_FOR_ROW, (str(market_a.id), "stalls", str(stall_id))
        ).fetchall()
        period_rows = conn.execute(
            "SELECT action, new_value->>'category_id' FROM audit_log "
            "WHERE market_id = %s AND table_name = 'stall_category_periods' "
            "AND new_value->>'stall_id' = %s ORDER BY id",
            (str(market_a.id), str(stall_id)),
        ).fetchall()
        assignment_rows = conn.execute(
            AUDIT_FOR_ROW, (str(market_a.id), "stall_assignments", assignment_id)
        ).fetchall()

    updates = [row for row in stall_rows if row[0] == "update"]
    assert len(updates) == 2, f"holat va kod uchun ikkita `update` kutilgan edi: {stall_rows}"
    changed = [set(row[1]) for row in updates]
    assert any("status" in keys for keys in changed), changed
    assert any("code" in keys for keys in changed), changed
    for _action, keys, old_value, new_value in updates:
        for key in keys:
            assert old_value[key] != new_value[key], (
                f"`changed_keys` da `{key}` bor, lekin `old` va `new` bir xil — "
                "diff hisoblagichi buzilgan"
            )

    inserted_categories = [row for row in period_rows if row[0] == "insert"]
    assert str(new_category) in {row[1] for row in inserted_categories}, (
        f"toifa o'zgarishi jurnalda yo'q: {period_rows}"
    )

    period_updates = [row for row in assignment_rows if row[0] == "update"]
    assert len(period_updates) == 1, f"biriktirish davri uchun bitta `update`: {assignment_rows}"
    _action, keys, old_value, new_value = period_updates[0]
    assert "period" in set(keys), keys
    assert old_value["period"] != new_value["period"], (
        "davr yopildi, lekin jurnaldagi `period` o'zgarmagan — qarz egaligining "
        "o'zgarishi izsiz qolardi (D-10)"
    )

    # --- YOZUVNING O'ZI HIMOYALANGAN (append-only) ---
    #
    # Usiz mezon "har o'zgarish auditda ko'rinadi" da'vosi kuchsiz bo'lardi:
    # o'zgarishni yozib, keyin izini o'chirish yo'li ochiq qolardi. Ilova
    # roli uchun ish 3-qatlamgacha (trigger) yetib ham bormaydi — huquq
    # umuman berilmagan.
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        sync_app_conn.execute(TAMPER_UPDATE)
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        sync_app_conn.execute(TAMPER_DELETE)


# ===========================================================================
# SC#3
# ===========================================================================


async def test_sc3_past_charges_keep_the_old_price(
    api_client: httpx.AsyncClient,
    two_markets: TwoMarketSeed,
    market_domain: MarketDomainSeed,
    market_scope: MarketScope,
    admin_headers: dict[str, str],
    market_today: date,
) -> None:
    """SC#3 — «Tarif o'zgartirilganda o'tmishdagi sanaga tegishli hisob eski
    narxda qoladi — yangi narx faqat belgilangan sanadan ta'sir qiladi».

    TEST **FAOL** BOZORDA BAJARILADI VA BU MEZONNING SHARTI.

    Qoralama bozorda boshlang'ich narx istisnosi ochiq (02-09) — u yerda
    `valid_from` `operating_since` ga tushishi mumkin va "o'tmish"
    tushunchasi hali ma'noga ega emas. Mezon esa ISHLAYOTGAN bozor haqida:
    u yerda o'tmish QULFLANGAN. Shuning uchun test avval istisnoning
    YOPIQ ekanini o'lchaydi (o'tmishdagi sanaga urinish -> 422), keyin
    qonuniy yo'ldan (kelajakdagi sana) yozadi.

    Uch o'lchov ham kerak:
      1. narx yangi qatordan OLDIN o'qiladi — boshlang'ich holat aniq;
      2. yangi qator API orqali qo'shiladi (D-06: INSERT, UPDATE emas);
      3. AYNI o'tmish sanasi QAYTA o'qiladi va javob O'ZGARMAGAN bo'ladi.

    Ikkinchi o'lchovsiz test hech nimani isbotlamasdi: birinchi javobning
    to'g'riligi yangi qatorning eski javobga TA'SIR QILMASLIGINI
    ko'rsatmaydi.

    ⚠ `test_tariff_history.py` (02-07) ayni da'voni XOM SQL bilan
    isbotlaydi — insider `psql` ochgan holat uchun. Bu yerda esa yozuv
    MAHSULOT yo'lidan (`POST /tariffs`) boradi va "D sanadagi narx"
    so'rovi 6-fazaga beriladigan shaklda o'qiladi.
    """
    market_a = two_markets.market_a
    domain_a = market_domain.market_a
    # UCHINCHI toifa ("Kiyim"). Indeks yozilgan, SUMMA esa seed'dan
    # olinadi: seed narxni o'zgartirsa test o'z-o'zidan moslashadi, lekin
    # qaysi toifa sinalayotgani ko'rinib turadi (02-06 qoidasi).
    category_id = domain_a.category_ids[2]
    seeded_amount = A_TARIFF_AMOUNTS[2]
    # Seed'dagi UCHALA summadan ham FARQLI: aks holda so'rov `category_id`
    # filtrini yo'qotib BOSHQA toifaning tarifini topganda ham test yashil
    # qolardi.
    new_amount = 15_001
    assert new_amount not in A_TARIFF_AMOUNTS

    with market_scope(market_a.id) as conn:
        active = conn.execute(
            "SELECT is_active FROM markets WHERE id = %s", (str(market_a.id),)
        ).fetchone()
    assert active == (True,), (
        "seed bozori faol emas — SC#3 ning butun sharti (o'tmish qulflangan) yo'qoladi"
    )

    effective = market_today + timedelta(days=FUTURE_DAYS)
    past_day = effective - timedelta(days=1)

    with market_scope(market_a.id) as conn:
        before = conn.execute(PRICE_AT, (market_a.id, category_id, past_day)).fetchone()
    assert before == (seeded_amount,), (
        f"boshlang'ich narx {before}, kutilgan {seeded_amount} — seed o'zgargan va test "
        "o'z shartini bajarmayapti"
    )

    # --- Boshlang'ich narx yo'li FAOL bozorda YOPIQ ---
    retro = await api_client.post(
        TARIFFS_URL,
        json={
            "category_id": str(category_id),
            "amount_soum": new_amount,
            "valid_from": domain_a.operating_since.isoformat(),
        },
        headers=admin_headers,
    )
    assert retro.status_code == 422, retro.text
    assert retro.json() == {"detail": "valid_from_must_be_future"}

    # --- Qonuniy yo'l: kelajakdagi sana ---
    created = await api_client.post(
        TARIFFS_URL,
        json={
            "category_id": str(category_id),
            "amount_soum": new_amount,
            "valid_from": effective.isoformat(),
        },
        headers=admin_headers,
    )
    assert created.status_code == 201, created.text

    with market_scope(market_a.id) as conn:
        after_past = conn.execute(PRICE_AT, (market_a.id, category_id, past_day)).fetchone()
        on_effective = conn.execute(PRICE_AT, (market_a.id, category_id, effective)).fetchone()

    assert after_past == (seeded_amount,), (
        f"{past_day} sanasidagi narx {after_past} ga o'zgardi — yangi tarif O'TMISHGA "
        "ta'sir qildi va o'sha kunlarning hisobi retroaktiv qayta yozildi"
    )
    assert on_effective == (new_amount,), (
        f"kuchga kirish kunida ({effective}) narx {on_effective} — chegara EKSKLYUZIV "
        "bo'lib qolgan, ya'ni yangi tarif bir kun kechikadi"
    )

    # Eski qator TEGILMAGAN holda tarixda turibdi va uning `valid_to` si
    # HISOBLANADI (Pitfall 9 — saqlanadigan ustun emas).
    history = await api_client.get(f"{TARIFFS_URL}?category={category_id}", headers=admin_headers)
    assert history.status_code == 200, history.text
    rows = {row["valid_from"]: row for row in history.json()["items"]}
    old_row = rows[domain_a.operating_since.isoformat()]
    assert old_row["amount_soum"] == seeded_amount
    assert old_row["valid_to"] == effective.isoformat(), (
        "eski qatorning amal qilish oxiri yangi qatordan HISOBLANMAYAPTI"
    )


# ===========================================================================
# SC#4
# ===========================================================================


async def test_sc4_closed_day_has_no_charge_basis(
    api_client: httpx.AsyncClient,
    two_markets: TwoMarketSeed,
    market_domain: MarketDomainSeed,
    market_scope: MarketScope,
    admin_headers: dict[str, str],
    market_today: date,
) -> None:
    """SC#4 — «Bozor admini bayram/ishlamaydigan kunni belgilaydi va o'sha
    kunga patta hisoblanmaydi».

    "PATTA HISOBLANMAYDI" NING MEXANIZMI — `market_is_open(market_id, date)`.

    6-fazaning kunlik job'i shu funksiyani `WHERE` bandiga yozadi:

        WHERE market_is_open(:market_id, :business_date)

    ya'ni funksiya `false` bergan kun uchun BIRORTA hisob qatori umuman
    tug'ilmaydi. Shuning uchun mezonning isboti — funksiyaning javobi,
    hisob jadvalining o'zi emas (u 6-fazada paydo bo'ladi).

    O'LCHOV OLDIN VA KEYIN OLINADI. Faqat "keyin" o'lchansa test kunning
    haftalik jadval bo'yicha ALLAQACHON yopiq bo'lgan holatida ham yashil
    bo'lardi — ya'ni istisno qatori hech nimani o'zgartirmagan bo'lsa ham.
    Nazorat kuni (istisno YOZILMAGAN, ayni haftakun) esa "funksiya har
    doim `false` qaytaradi" holatini yopadi.
    """
    market_a = two_markets.market_a
    open_weekdays = set(market_domain.market_a.open_weekdays)

    holiday = _next_weekday_in(market_today + timedelta(days=1), open_weekdays)
    control = _next_weekday_in(holiday + timedelta(days=1), open_weekdays)
    assert holiday != control

    with market_scope(market_a.id) as conn:
        before = conn.execute(IS_OPEN, (market_a.id, holiday)).fetchone()
    assert before == (True,), (
        f"{holiday} haftalik jadval bo'yicha ALLAQACHON yopiq — istisno qatori "
        "hech nimani o'zgartirmasdi va test bo'sh da'vo bo'lib qolardi"
    )

    created = await api_client.post(
        f"{CALENDAR_URL}/exceptions",
        json={"exception_date": holiday.isoformat(), "is_open": False, "note": "Mezon bayrami"},
        headers=admin_headers,
    )
    assert created.status_code == 201, created.text
    assert created.json()["is_open"] is False

    with market_scope(market_a.id) as conn:
        after = conn.execute(IS_OPEN, (market_a.id, holiday)).fetchone()
        control_answer = conn.execute(IS_OPEN, (market_a.id, control)).fetchone()

    assert after == (False,), (
        f"{holiday} bayram deb belgilandi, lekin `market_is_open` hamon `{after}` — "
        "6-fazadagi kunlik job o'sha kunga ham patta yozardi"
    )
    assert control_answer == (True,), (
        f"NAZORAT: {control} kuni uchun istisno YOZILMAGAN, lekin javob `{control_answer}` — "
        "funksiya bir kunning istisnosini butun bozorga tarqatgan"
    )


def _next_weekday_in(start: date, weekdays: set[int]) -> date:
    """`start` dan boshlab jadval bo'yicha OCHIQ birinchi kun.

    Sana HISOBLANADI, sobit yozilmaydi: qotirilgan "bayram" sanasi bir
    necha oydan keyin o'tmishga aylanardi va seed'ning haftalik jadvali
    (`A_OPEN_WEEKDAYS` — dushanba yopiq) bilan tasodifan to'qnashardi.
    """
    for offset in range(8):
        candidate = start + timedelta(days=offset)
        if candidate.isoweekday() in weekdays:
            return candidate
    raise AssertionError(f"bir hafta ichida ochiq kun topilmadi: {sorted(weekdays)}")


# ===========================================================================
# SC#5
# ===========================================================================


async def test_sc5_map_groups_stalls_by_zone_in_code_order(
    api_client: httpx.AsyncClient,
    market_domain: MarketDomainSeed,
    admin_headers: dict[str, str],
) -> None:
    """SC#5 — «Bozor admini sxematik plan-xaritada rastalarni zona bo'yicha
    grid ko'rinishida ko'radi; rasta bosilganda uning kartasi (raqam, toifa,
    tarif, sotuvchi, holat) ochiladi».

    BU FAYL API SHARTNOMASINI TEKSHIRADI, GRID RENDERINI EMAS (fayl
    docstringiga qarang). To'rt da'vo:

    1. **Birorta rasta yo'qolmaydi** — xaritadagi kataklar to'plami
       reestrdagi rastalar to'plami bilan AYNAN teng. Xarita alohida
       agregat so'rov bilan quriladi, ya'ni `JOIN` shartidagi bitta
       xatolik rastalarni JIMGINA tushirib qoldirardi va bozor admini
       yo'q rasta uchun patta talab qilinmayotganini SEZMASDI.
    2. **Katak tartibi inson-raqamli** (`2 < 10 < 100`), matn tartibi
       emas. Da'vo BO'SH BO'LMASLIGI alohida o'lchanadi: kamida bitta
       zonada ikkala tartib FARQ qilishi shart, aks holda "tartib
       to'g'ri" degan xulosa `code_sort` umuman ishlamaganda ham
       chiqardi.
    3. **Katakda AYNAN to'rt maydon** — `id`, `code`, `status`,
       `has_vendor`. To'plam TENGLIGI tekshiriladi, "bor" emas: D-20
       bo'yicha rang serverda hisoblanmaydi va koordinata saqlanmaydi
       (D-19), ya'ni ortiqcha maydon ham shartnoma buzilishi.
    4. **Katak va karta bir xil haqiqatni aytadi** — har bir katakning
       `has_vendor` i kartadagi `vendor_name` bilan mos keladi. Bu
       mezonning "bosilganda kartasi ochiladi" qismining yagona
       mashinaviy shakli: rang manbai bilan karta ajralib ketsa,
       xaritada "sotuvchili" ko'ringan rasta kartada sotuvchisiz
       ochilardi.
    """
    response = await api_client.get(f"{STALLS_URL}/map", headers=admin_headers)
    assert response.status_code == 200, response.text
    zones: list[dict[str, Any]] = response.json()["zones"]
    cells = [cell for zone in zones for cell in zone["cells"]]
    assert cells, "xarita bo'sh — quyidagi da'volarning birortasi ham hech nimani isbotlamasdi"

    # --- 1. Birorta rasta yo'qolmaydi ---
    registry = await api_client.get(f"{STALLS_URL}?limit=100", headers=admin_headers)
    assert registry.status_code == 200, registry.text
    registry_items = registry.json()["items"]
    assert registry.json()["next_cursor"] is None, "reestr bir sahifaga sig'madi"
    assert {cell["id"] for cell in cells} == {item["id"] for item in registry_items}, (
        "xarita va reestr HAR XIL rastalar to'plamini ko'rsatmoqda"
    )

    # --- 2. Inson-raqamli tartib va da'voning BO'SH EMASLIGI ---
    discriminating = 0
    for zone in zones:
        codes = [cell["code"] for cell in zone["cells"]]
        assert codes == sorted(codes, key=int), f"{zone['name']}: {codes}"
        if codes != sorted(codes):
            discriminating += 1
    assert discriminating > 0, (
        "birorta zonada raqamli va matn tartibi FARQ qilmadi — bu holatda tartib "
        "da'vosi `code_sort` umuman ishlamaganda ham yashil bo'lardi"
    )

    # --- 3. Katakning AYNAN olti maydoni ---
    #
    # ⛔⛔ SON TO'RTDAN OLTIGA ONGLI RAVISHDA OSHIRILDI (260820): qo'lda
    #     chizilgan plan `plan_x`/`plan_y` ni qo'shdi. To'plam TENGLIGI
    #     saqlanadi (D-31) — `>=` ga aylantirilmaydi, aks holda javobga
    #     kelajakda sudralib kiradigan har qanday maydon jimgina o'tib
    #     ketardi.
    #
    # ⛔ D-19 BEKOR QILINMADI: sxematik ko'rinish AVVALGIDEK avtomatik
    #    joylashadi va koordinata `NULL` bo'lishi mumkin. Ular IXTIYORIY
    #    ikkinchi qatlam — pastdagi da'vo aynan shuni qulflaydi.
    for cell in cells:
        assert set(cell) == {
            "id",
            "code",
            "status",
            "has_vendor",
            "plan_x",
            "plan_y",
        }, cell

    # Bu seed planni CHIZMAYDI, ya'ni koordinata `NULL` bo'lishi SHART:
    # agar server chizilmagan rastaga `0` bersa, muharrir hamma rastani
    # chap-yuqori burchakka bosib qo'yardi.
    assert {(cell["plan_x"], cell["plan_y"]) for cell in cells} == {(None, None)}

    # --- 4. Katak va karta bir xil haqiqatni aytadi ---
    with_vendor = [cell for cell in cells if cell["has_vendor"]]
    assert with_vendor, (
        "birorta katakda `has_vendor: true` yo'q — kartaning sotuvchi maydoni "
        "sinalmasdi (seed'da biriktirilgan rasta bor)"
    )
    for cell in cells:
        card = await api_client.get(f"{STALLS_URL}/{cell['id']}", headers=admin_headers)
        assert card.status_code == 200, card.text
        body = card.json()
        assert body["code"] == cell["code"]
        assert body["status"] == cell["status"]
        assert (body["vendor_name"] is not None) is cell["has_vendor"], (
            f"{cell['code']}-rasta: xaritada has_vendor={cell['has_vendor']}, "
            f"kartada vendor_name={body['vendor_name']}"
        )

    # Mezon kartadan BESH narsani nomlaydi — ular bittasida ham `None`
    # bo'lmasligi kerak, aks holda da'vo bo'sh maydonlar ustida yashil
    # bo'lardi. Seed har rastaga toifa davri va har toifaga tarif beradi.
    card = await api_client.get(f"{STALLS_URL}/{with_vendor[0]['id']}", headers=admin_headers)
    body = card.json()
    missing = [
        field
        for field in ("code", "category_name", "tariff_soum", "vendor_name", "status")
        if body.get(field) is None
    ]
    assert missing == [], f"karta mezon nomlagan maydonlarsiz keldi: {missing}"
    # Kutilma SEED'DAN olinadi, test faylida qayta yozilmaydi (02-06 qoidasi).
    assert len(market_domain.market_a.category_ids) == len(A_CATEGORY_NAMES)
    assert body["category_name"] in set(A_CATEGORY_NAMES)
