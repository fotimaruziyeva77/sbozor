"""Xodimlar rosteri importi — MARKET-07 ning ENDPOINT darajasidagi isboti.

=============================================================================
BU FAYL `tests/unit/test_staff_import_validator.py` NING O'RNINI BOSMAYDI.

Unit testlar sof funksiyani sinaydi (qator raqamlari, rol darajasi,
E.164). Bu yerdagi savol boshqa: **butun zanjir haqiqiy bazada
ishlaydimi** — validatsiya -> `auth_create_user` -> a'zolik -> audit ->
javob, va xato bo'lganda TRANZAKSIYA butunlay orqaga qaytadimi.

Validator to'g'ri bo'lib, router uni CHAQIRMASA unit testlar YASHIL
qolardi.
=============================================================================

D-14 (ALL-OR-NOTHING) SANOQ BILAN O'LCHANADI, JAVOB BILAN EMAS.

"422 keldi" degan da'vo yetarli emas: endpoint hisoblarni yaratib bo'lib,
so'ng 422 qaytargan holatda ham u to'g'ri bo'lardi. Shuning uchun har
bir rad etish testi importdan OLDIN va KEYIN a'zolar sonini
solishtiradi (02-12 sabotaj #6 darsi).

D-02 (BIR MARTALIK PAROL) LOGIN BILAN O'LCHANADI.

"`credentials` bo'sh emas" degan da'vo ham yetarli emas: javobda tasodifiy
satr bo'lishi mumkin va u hech qanday hisobga mos kelmasligi mumkin edi.
Shuning uchun `test_created_account_can_log_in` aynan o'sha parol bilan
`POST /auth/login` qiladi.
"""

from __future__ import annotations

import io
from typing import TYPE_CHECKING, Any

import pytest
import xlsxwriter
from fixtures.admin_api import (
    AUDIT_URL,
    IMPORT_STAFF_URL,
    IMPORTS_TEMPLATE_URL,
    USERS_URL,
    new_phone,
    platform_admin_headers,
    session_headers,
)
from fixtures.auth_api import login
from fixtures.two_markets import SEED_PASSWORD

if TYPE_CHECKING:
    from uuid import UUID

    import httpx
    from app.settings import Settings
    from fastapi import FastAPI
    from fixtures import MarketScope
    from fixtures.auth_users import AuthSeed
    from fixtures.two_markets import TwoMarketSeed
    from psycopg import Connection
    from psycopg.rows import TupleRow

XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

STAFF_HEADER = ["F.I.Sh.", "telefon", "rol"]

SAMPLE_PHONE = "+998901234567"
"""Shablonning namunaviy telefoni E.164 ga keltirilgandan KEYINGI qiymati.

Shablonda u `+` SIZ turadi (`xlsx_template._SAMPLE_PHONE`) — `+`
formula prefiksi va qochirish uni importga yaroqsiz qilardi.
"""


# ---------------------------------------------------------------------------
# Fayl quruvchilar
# ---------------------------------------------------------------------------


def build_xlsx(rows: list[list[Any]], *, sheet: str = "Xodimlar") -> bytes:
    """`XlsxWriter` bilan haqiqiy `.xlsx` quradi (repoda binar fayl YO'Q)."""
    buffer = io.BytesIO()
    workbook = xlsxwriter.Workbook(buffer, {"in_memory": True})
    worksheet = workbook.add_worksheet(sheet)
    worksheet.write_row(0, 0, STAFF_HEADER)
    for index, row in enumerate(rows, start=1):
        worksheet.write_row(index, 0, row)
    workbook.close()
    return buffer.getvalue()


def upload(payload: bytes, name: str = "xodimlar.xlsx") -> dict[str, tuple[str, bytes, str]]:
    """`multipart/form-data` yuklamasi."""
    return {"file": (name, payload, XLSX_MEDIA_TYPE)}


def staff_rows(count: int = 3, role: str = "cashier") -> list[list[str]]:
    """`count` ta yaroqli qator — HAR chaqiruvda YANGI telefonlar bilan.

    `new_phone()` `+99893…` diapazonini beradi va `cleanup_test_users()`
    aynan shu diapazonni o'chiradi. Qattiq yozilgan raqam ikkinchi
    testda `phone_taken` berardi va sabab test kodida KO'RINMASDI.
    """
    return [[f"Xodim {index}", new_phone(), role] for index in range(1, count + 1)]


# ---------------------------------------------------------------------------
# Sessiyalar va sanoqlar
# ---------------------------------------------------------------------------


@pytest.fixture
async def admin_headers(
    api_client: httpx.AsyncClient,
    two_markets: TwoMarketSeed,
) -> dict[str, str]:
    """A bozori adminining sessiyasi (`USER_MANAGE`)."""
    market_a = two_markets.market_a
    return await session_headers(api_client, market_a.admin_phone, market_a.admin_password)


@pytest.fixture
async def director_headers(
    api_client: httpx.AsyncClient,
    two_markets: TwoMarketSeed,
) -> dict[str, str]:
    """A bozori direktorining sessiyasi — D-07 ning manfiy holati."""
    return await session_headers(api_client, two_markets.market_a.director_phone, SEED_PASSWORD)


@pytest.fixture
async def cashier_headers(
    api_client: httpx.AsyncClient,
    two_markets: TwoMarketSeed,
) -> dict[str, str]:
    """A bozori kassirining sessiyasi — eng tor yuza."""
    return await session_headers(api_client, two_markets.market_a.cashier_phone, SEED_PASSWORD)


def count_members(market_scope: MarketScope, market_id: UUID) -> int:
    """`user_market_roles` sanog'i — ILOVA roli va tenant konteksti bilan.

    Superuser bilan O'QILMAYDI: D-14 da'vosi aynan ilova ko'radigan
    haqiqat ustida bo'lishi kerak.
    """
    with market_scope(market_id) as conn:
        row = conn.execute("SELECT count(*) FROM user_market_roles").fetchone()
    assert row is not None
    return int(row[0])


async def member_phones(client: httpx.AsyncClient, headers: dict[str, str]) -> set[str]:
    response = await client.get(USERS_URL, headers=headers)
    assert response.status_code == 200, response.text
    return {item["phone"] for item in response.json()["items"]}


# ===========================================================================
# Muvaffaqiyat yo'li
# ===========================================================================


async def test_one_file_creates_every_account_with_a_password(
    api_client: httpx.AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    """Bitta fayl -> uchta hisob, uchta vaqtinchalik parol (MARKET-07)."""
    rows = staff_rows(3)

    response = await api_client.post(
        IMPORT_STAFF_URL, headers=admin_headers, files=upload(build_xlsx(rows))
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["inserted"] == 3
    assert body["skipped"] == 0
    assert len(body["credentials"]) == 3

    for index, item in enumerate(body["credentials"]):
        assert item["row"] == index + 2, "EXCEL qator raqami saqlanmagan"
        assert item["phone"] == rows[index][1]
        assert item["roles"] == ["cashier"]
        assert len(item["temporary_password"]) >= 10

    listed = await member_phones(api_client, admin_headers)
    assert {row[1] for row in rows} <= listed


async def test_created_account_can_log_in_and_must_change_password(
    api_client: httpx.AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    """Berilgan parol HAQIQATAN ishlaydi va birinchi kirishda almashtiriladi (D-02).

    ⚠ Bu testsiz "parol berildi" da'vosi tekshirilmagan qolardi: javobda
    istalgan tasodifiy satr turishi mumkin edi va u hech qanday hisobga
    mos kelmasligi ham mumkin edi.
    """
    created = await api_client.post(
        IMPORT_STAFF_URL, headers=admin_headers, files=upload(build_xlsx(staff_rows(1)))
    )
    assert created.status_code == 200, created.text
    item = created.json()["credentials"][0]

    response = await login(api_client, item["phone"], item["temporary_password"])

    assert response.status_code == 200, response.text
    assert response.json()["must_change_password"] is True


async def test_multi_role_cell_creates_one_account_with_both_roles(
    api_client: httpx.AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    """D-05: bir odam ham kassir, ham nazoratchi bo'lishi mumkin."""
    phone = new_phone()

    response = await api_client.post(
        IMPORT_STAFF_URL,
        headers=admin_headers,
        files=upload(build_xlsx([["Ikki Rolli", phone, "cashier; inspector"]])),
    )

    assert response.status_code == 200, response.text
    assert response.json()["credentials"][0]["roles"] == ["cashier", "inspector"]

    listed = await api_client.get(USERS_URL, headers=admin_headers)
    member = next(item for item in listed.json()["items"] if item["phone"] == phone)
    assert sorted(member["roles"]) == ["cashier", "inspector"]


async def test_response_is_not_cacheable(
    api_client: httpx.AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    """Javob ochiq parollarni olib yuradi — u KESHLANMAYDI (T-02-176)."""
    response = await api_client.post(
        IMPORT_STAFF_URL, headers=admin_headers, files=upload(build_xlsx(staff_rows(1)))
    )

    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "no-store"


# ===========================================================================
# D-14 — ALL-OR-NOTHING
# ===========================================================================


async def test_all_or_nothing_with_a_mixed_file(
    api_client: httpx.AsyncClient,
    admin_headers: dict[str, str],
    market_scope: MarketScope,
    two_markets: TwoMarketSeed,
) -> None:
    """Uchta to'g'ri + uchta xato -> 422 va bazada NOL yangi a'zo.

    Fayl ATAYIN ARALASH: faqat xatoli qatorlardan iborat fayl bilan test
    "hech narsa yozilmadi" ni isbotlay olmasdi — yoziladigan narsaning
    O'ZI yo'q edi.
    """
    market_a = two_markets.market_a.id
    before = count_members(market_scope, market_a)

    payload = build_xlsx(
        [
            *staff_rows(3),
            ["Yomon Telefon", "12", "cashier"],
            ["Yomon Rol", new_phone(), "kassr"],
            ["Rolsiz", new_phone(), ""],
        ]
    )
    response = await api_client.post(IMPORT_STAFF_URL, headers=admin_headers, files=upload(payload))

    assert response.status_code == 422, response.text
    body = response.json()["detail"]
    assert body["detail"] == "import_validation_failed"
    assert sorted(body["error_counts"]) == ["invalid_phone", "invalid_role", "row_too_short"]
    assert {item["row"] for item in body["errors"]} == {5, 6, 7}

    assert count_members(market_scope, market_a) == before, "D-14 buzildi: qator yozilgan"


async def test_phone_taken_by_another_market_is_also_all_or_nothing(
    api_client: httpx.AsyncClient,
    admin_headers: dict[str, str],
    market_scope: MarketScope,
    two_markets: TwoMarketSeed,
) -> None:
    """Platformada BAND telefon -> 422 `phone_taken`, va HECH BIR hisob yozilmaydi.

    ⚠ Jimgina o'tkazib yuborish adminni "xodim yaratildi" deb
    ishontirardi. Bu yo'l `auth_create_user` ning `ON CONFLICT DO
    NOTHING` xulqidan keladi: u `NULL` qaytaradi va tranzaksiyani abort
    QILMAYDI, ya'ni to'xtatish ILOVA ning ishi.

    Sanoq assertion'i MAJBURIY: xato qatordan OLDINGI ikkita qator
    allaqachon yozilgan bo'lishi mumkin edi.
    """
    market_a = two_markets.market_a.id
    before = count_members(market_scope, market_a)

    payload = build_xlsx(
        [
            *staff_rows(2),
            ["Boshqa Bozor A'zosi", two_markets.market_b.cashier_phone, "cashier"],
        ]
    )
    response = await api_client.post(IMPORT_STAFF_URL, headers=admin_headers, files=upload(payload))

    assert response.status_code == 422, response.text
    body = response.json()["detail"]
    assert [item["code"] for item in body["errors"]] == ["phone_taken"]
    assert body["errors"][0]["row"] == 4

    assert count_members(market_scope, market_a) == before, "D-14 buzildi: qator yozilgan"


# ===========================================================================
# D-15 — qayta import
# ===========================================================================


async def test_reimport_does_not_reset_passwords(
    api_client: httpx.AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    """AYNI fayl ikkinchi marta: `inserted=0`, `skipped=N`, eski parol ISHLAYDI.

    ⚠ Bu D-15 ning eng muhim da'vosi va u XAVFSIZLIK qarori: muqobil
    (parolni qayta berish) roster faylini OMMAVIY PAROL TIKLASH quroliga
    aylantirardi — eski faylni tasodifan qayta yuklagan admin butun
    jamoani tizimdan chiqarib yuborardi.
    """
    payload = build_xlsx(staff_rows(2))

    first = await api_client.post(IMPORT_STAFF_URL, headers=admin_headers, files=upload(payload))
    assert first.status_code == 200, first.text
    item = first.json()["credentials"][0]

    second = await api_client.post(IMPORT_STAFF_URL, headers=admin_headers, files=upload(payload))

    assert second.status_code == 200, second.text
    assert second.json() == {"inserted": 0, "skipped": 2, "credentials": []}

    # Parol TIKLANMAGAN — birinchi importdagi qiymat hamon ishlaydi.
    replayed = await login(api_client, item["phone"], item["temporary_password"])
    assert replayed.status_code == 200, replayed.text


async def test_reimport_does_not_change_roles(
    api_client: httpx.AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    """Mavjud a'zoning ROLI ham o'zgarmaydi — fayl boshqa rol yozsa ham."""
    phone = new_phone()
    first = await api_client.post(
        IMPORT_STAFF_URL,
        headers=admin_headers,
        files=upload(build_xlsx([["Bir Rolli", phone, "cashier"]])),
    )
    assert first.status_code == 200, first.text

    second = await api_client.post(
        IMPORT_STAFF_URL,
        headers=admin_headers,
        files=upload(build_xlsx([["Bir Rolli", phone, "inspector"]])),
    )
    assert second.status_code == 200, second.text
    assert second.json()["skipped"] == 1

    listed = await api_client.get(USERS_URL, headers=admin_headers)
    member = next(item for item in listed.json()["items"] if item["phone"] == phone)
    assert member["roles"] == ["cashier"], "D-15 buzildi: rol qayta yozilgan"


# ===========================================================================
# D-04 — rol berish darajasi
# ===========================================================================


async def test_market_admin_cannot_assign_market_admin(
    api_client: httpx.AsyncClient,
    admin_headers: dict[str, str],
    market_scope: MarketScope,
    two_markets: TwoMarketSeed,
) -> None:
    """Bozor admini o'ziga TENG rol berolmaydi -> 422 `role_not_allowed`."""
    before = count_members(market_scope, two_markets.market_a.id)

    response = await api_client.post(
        IMPORT_STAFF_URL,
        headers=admin_headers,
        files=upload(build_xlsx([["Yangi Admin", new_phone(), "market_admin"]])),
    )

    assert response.status_code == 422, response.text
    assert [item["code"] for item in response.json()["detail"]["errors"]] == ["role_not_allowed"]
    assert count_members(market_scope, two_markets.market_a.id) == before


async def test_platform_admin_can_assign_market_admin(
    api_client: httpx.AsyncClient,
    auth_seed: AuthSeed,
) -> None:
    """NAZORAT: yuqori daraja AYNI faylni qabul qiladi."""
    headers = await platform_admin_headers(api_client, auth_seed)

    response = await api_client.post(
        IMPORT_STAFF_URL,
        headers=headers,
        files=upload(build_xlsx([["Yangi Admin", new_phone(), "market_admin"]])),
    )

    assert response.status_code == 200, response.text
    assert response.json()["credentials"][0]["roles"] == ["market_admin"]


async def test_platform_admin_role_is_rejected_for_the_market_admin(
    api_client: httpx.AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    """`platform_admin` a'zolik roli sifatida HECH KIM tomonidan berilmaydi (CR-03)."""
    response = await api_client.post(
        IMPORT_STAFF_URL,
        headers=admin_headers,
        files=upload(build_xlsx([["Gibrid", new_phone(), "platform_admin"]])),
    )

    assert response.status_code == 422, response.text
    assert [item["code"] for item in response.json()["detail"]["errors"]] == ["role_not_allowed"]


async def test_platform_admin_role_is_rejected_for_the_platform_admin_too(
    api_client: httpx.AsyncClient,
    auth_seed: AuthSeed,
) -> None:
    """Rad etish PLATFORMA ADMINI uchun ham amal qiladi — gibrid hisob yo'li yopiq."""
    headers = await platform_admin_headers(api_client, auth_seed)

    response = await api_client.post(
        IMPORT_STAFF_URL,
        headers=headers,
        files=upload(build_xlsx([["Gibrid", new_phone(), "platform_admin"]])),
    )

    assert response.status_code == 422, response.text
    assert [item["code"] for item in response.json()["detail"]["errors"]] == ["role_not_allowed"]


# ===========================================================================
# D-07 — huquq darvozasi
# ===========================================================================


async def test_director_cannot_import_staff(
    api_client: httpx.AsyncClient,
    director_headers: dict[str, str],
) -> None:
    """Direktorda `USER_MANAGE` YO'Q — u hisob yarata olmaydi (D-07)."""
    response = await api_client.post(
        IMPORT_STAFF_URL, headers=director_headers, files=upload(build_xlsx(staff_rows(1)))
    )

    assert response.status_code == 403, response.text


async def test_cashier_cannot_import_staff(
    api_client: httpx.AsyncClient,
    cashier_headers: dict[str, str],
) -> None:
    """Kassir — eng tor yuza, u ham 403 oladi."""
    response = await api_client.post(
        IMPORT_STAFF_URL, headers=cashier_headers, files=upload(build_xlsx(staff_rows(1)))
    )

    assert response.status_code == 403, response.text


async def test_director_cannot_download_the_staff_template(
    api_client: httpx.AsyncClient,
    director_headers: dict[str, str],
) -> None:
    """Shablon ham `USER_MANAGE` ortida: u ruxsat etilgan rollarni OSHKOR qiladi."""
    response = await api_client.get(
        IMPORTS_TEMPLATE_URL, params={"kind": "staff"}, headers=director_headers
    )

    assert response.status_code == 403, response.text


async def test_market_admin_downloads_the_staff_template(
    api_client: httpx.AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    """NAZORAT: bozor admini shablonni oladi (aks holda yuqoridagi 403 ma'nosiz)."""
    response = await api_client.get(
        IMPORTS_TEMPLATE_URL, params={"kind": "staff"}, headers=admin_headers
    )

    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == XLSX_MEDIA_TYPE


async def test_downloaded_staff_template_creates_a_real_account(
    api_client: httpx.AsyncClient,
    admin_headers: dict[str, str],
    sync_owner_conn: Connection[TupleRow],
) -> None:
    """UCHIDAN-UCHIGA: yuklab olingan shablon O'ZI import qilinadi.

    Bu — A6 ustunlar tartibining eng kuchli isboti. Namunaviy qator
    HAQIQIY hisob yaratadi, ya'ni ustunlar tartibi shablon bilan parser
    orasida bir kun ajralib ketsa AYNAN shu test qizaradi.

    ⚠ TOZALASH SHU YERDA VA U MAJBURIY: namunaviy telefon
    (`SAMPLE_PHONE`) `cleanup_test_users()` ning `+99893…` naqshiga
    TUSHMAYDI, ya'ni avtomatik tozalashga tayanib bo'lmaydi. Qator
    qolib ketsa keyingi chaqiruv `phone_taken` olardi va sabab test
    kodida umuman ko'rinmasdi.
    """
    template = await api_client.get(
        IMPORTS_TEMPLATE_URL, params={"kind": "staff"}, headers=admin_headers
    )
    assert template.status_code == 200, template.text

    try:
        imported = await api_client.post(
            IMPORT_STAFF_URL, headers=admin_headers, files=upload(template.content, "shablon.xlsx")
        )

        assert imported.status_code == 200, imported.text
        body = imported.json()
        assert body["inserted"] == 1
        assert body["credentials"][0]["phone"] == SAMPLE_PHONE
        assert body["credentials"][0]["roles"] == ["cashier"]
    finally:
        sync_owner_conn.execute("DELETE FROM users WHERE phone_e164 = %s", (SAMPLE_PHONE,))


# ===========================================================================
# FOUND-02 — tenant chegarasi
# ===========================================================================


async def test_import_into_market_a_leaves_market_b_untouched(
    api_client: httpx.AsyncClient,
    auth_seed: AuthSeed,
    market_scope: MarketScope,
    two_markets: TwoMarketSeed,
) -> None:
    """Platforma admini A ni tanlab import qilganda B ning sanog'i O'ZGARMAYDI.

    `market_id` FAYLDAN olinmaydi (T-02-54) va shablonda bunday ustun
    umuman yo'q — bu test o'sha qoidaning ish paytidagi isboti.
    """
    market_a, market_b = two_markets.market_a.id, two_markets.market_b.id
    before_a = count_members(market_scope, market_a)
    before_b = count_members(market_scope, market_b)

    headers = await platform_admin_headers(api_client, auth_seed, market_a)
    response = await api_client.post(
        IMPORT_STAFF_URL, headers=headers, files=upload(build_xlsx(staff_rows(2)))
    )

    assert response.status_code == 200, response.text
    assert count_members(market_scope, market_a) == before_a + 2
    assert count_members(market_scope, market_b) == before_b, "cross-tenant yozuv!"


# ===========================================================================
# FOUND-03 — audit
# ===========================================================================


async def test_audit_records_each_account_and_the_bulk_import(
    api_client: httpx.AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    """Har hisob uchun yozuv VA ommaviy amalning O'ZI uchun bitta yig'ma yozuv.

    ⚠ Yig'ma yozuv MAJBURIY: usiz jurnalda 30 ta alohida `insert`
    ko'rinardi va "bular bitta ommaviy amaldan" degan fakt yo'qolardi —
    nizoda aynan shu savol so'raladi (T-02-180).
    """
    response = await api_client.post(
        IMPORT_STAFF_URL, headers=admin_headers, files=upload(build_xlsx(staff_rows(2)))
    )
    assert response.status_code == 200, response.text
    created = {item["phone"] for item in response.json()["credentials"]}

    audit = await api_client.get(AUDIT_URL, params={"limit": 100}, headers=admin_headers)
    assert audit.status_code == 200, audit.text
    entries = audit.json()["items"]

    users_rows = [
        entry for entry in entries if entry["table_name"] == "users" and entry["action"] == "insert"
    ]
    per_account = {
        entry["new_value"]["phone"]
        for entry in users_rows
        if entry["row_id"] is not None and "phone" in (entry["new_value"] or {})
    }
    assert created <= per_account, "har hisob uchun audit yozuvi yo'q"

    bulk = [
        entry
        for entry in users_rows
        if entry["row_id"] is None and (entry["new_value"] or {}).get("import") == "staff"
    ]
    assert len(bulk) == 1, f"yig'ma yozuv topilmadi yoki takrorlangan: {len(bulk)}"
    assert bulk[0]["new_value"]["created"] == 2
    assert bulk[0]["new_value"]["rows"] == 2


async def test_audit_never_contains_a_temporary_password(
    api_client: httpx.AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    """Jurnalning HECH BIR joyida ochiq parol YO'Q (T-01-52, T-02-176)."""
    response = await api_client.post(
        IMPORT_STAFF_URL, headers=admin_headers, files=upload(build_xlsx(staff_rows(2)))
    )
    assert response.status_code == 200, response.text
    passwords = [item["temporary_password"] for item in response.json()["credentials"]]

    audit = await api_client.get(AUDIT_URL, params={"limit": 100}, headers=admin_headers)
    body = audit.text

    for password in passwords:
        assert password not in body, "vaqtinchalik parol audit javobiga tushgan"


# ===========================================================================
# T-02-181 — roster hajmi chegarasi
# ===========================================================================


async def test_roster_larger_than_the_limit_is_rejected(
    api_client: httpx.AsyncClient,
    api_app: FastAPI,
    admin_headers: dict[str, str],
    test_settings: Settings,
    market_scope: MarketScope,
    two_markets: TwoMarketSeed,
) -> None:
    """Chegaradan bitta ortiq qator -> 422 `staff_roster_too_large`.

    Chegara SOZLAMA orqali toraytiriladi — 201 qatorli fayl qurish
    testni sekinlashtirardi va hech qanday yangi ma'lumot bermasdi
    (`tests/unit/test_xlsx_reader.py` dagi bilan aynan bir xil usul).

    ⚠ Argon2id hash'lash CPU bo'yicha QIMMAT: chegarasiz 5000 qatorli
    fayl butun ishchini bloklagan bo'lardi (T-02-179).
    """
    before = count_members(market_scope, two_markets.market_a.id)
    narrowed = test_settings.model_copy(update={"import_max_staff_rows": 2})
    api_app.state.settings = narrowed
    try:
        response = await api_client.post(
            IMPORT_STAFF_URL, headers=admin_headers, files=upload(build_xlsx(staff_rows(3)))
        )
    finally:
        api_app.state.settings = test_settings

    assert response.status_code == 422, response.text
    assert response.json()["detail"] == "staff_roster_too_large"
    assert count_members(market_scope, two_markets.market_a.id) == before
