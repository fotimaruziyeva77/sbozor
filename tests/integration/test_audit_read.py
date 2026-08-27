"""Audit ko'rish API'si va O'QISH auditi (D-09, D-11, D-12).

=============================================================================
IKKI ALOHIDA DA'VO — VA ULARNI ARALASHTIRIB BO'LMAYDI:

1. **KIM KO'RADI** (D-11): platforma admini, direktor va bozor admini —
   har biri O'Z bozori doirasida. Kassir va nazoratchi umuman ko'rmaydi.
2. **KO'RISHNING O'ZI YOZILADI** (D-09): `GET /audit` chaqirilgach
   jurnalda yangi `action='read'` qatori paydo bo'ladi. O'zbekiston
   shaxsiy ma'lumotlar qonuni shaxsiy ma'lumot O'QISHINI ham qayd
   etishni talab qiladi, PostgreSQL'da esa `SELECT` uchun trigger YO'Q —
   ya'ni bu yozuvni faqat ilova qatlami qo'ya oladi.

Ikkinchi da'voning eng nozik qismi — RAD ETILGAN so'rov yozuv
QOLDIRMASLIGI: 403 olgan kassir hech narsani o'qimagan, ya'ni "o'qidi"
degan yozuv YOLG'ON dalil bo'lardi va jurnalning qiymatini tushirardi.
=============================================================================
"""

from __future__ import annotations

import json
from datetime import timedelta
from typing import TYPE_CHECKING, Any

from fixtures.admin_api import (
    AUDIT_URL,
    PROFILE_URL,
    USERS_URL,
    insert_audit_probe,
    new_phone,
    platform_admin_headers,
    session_headers,
)
from fixtures.auth_api import CHANGE_PASSWORD_URL, audit_rows
from sbozor_core.enums import AuditAction
from sbozor_core.timeutil import now_tz

if TYPE_CHECKING:
    import httpx
    from fixtures import TenantSessionFactory
    from fixtures.auth_users import AuthSeed
    from psycopg import Connection
    from psycopg.rows import TupleRow

TABLE_AUDIT_LOG = "audit_log"

DIRECTOR_PASSWORD = "direktor-uzun-parol-2026"  # noqa: S105 — test ma'lumoti
"""API orqali yaratilgan direktorning ONBOARDING dan keyingi doimiy paroli."""


async def _market_admin(api_client: httpx.AsyncClient, auth_seed: AuthSeed) -> dict[str, str]:
    return await session_headers(api_client, auth_seed.market_admin.phone, auth_seed.password)


async def _director(api_client: httpx.AsyncClient, auth_seed: AuthSeed) -> dict[str, str]:
    """Direktor D-04 ning birinchi bosqichi orqali yaratiladi va ONBOARD qilinadi.

    ONBOARDING QISMI MAJBURIY (01-11, CR-01). Vaqtinchalik parol bilan
    yaratilgan foydalanuvchida `must_change_password = true` bo'ladi va
    `require_password_current` uni HAR QANDAY tenant endpointida 403
    `password_change_required` bilan rad etadi — ya'ni parol
    almashtirilmasa `GET /audit` javobi 403 bo'lardi va
    `test_director_can_view_the_audit_log` "direktorda `AUDIT_VIEW` bor"
    degan da'voni umuman sinamay qo'yardi.

    Shuning uchun bu yordamchi D-02 ning HAQIQIY oqimini bajaradi:
    vaqtinchalik parol -> majburiy almashtirish -> yangi parol bilan
    sessiya. Natijada test yana AYNAN huquq matritsasini sinaydi.
    """
    platform = await platform_admin_headers(api_client, auth_seed)
    phone = new_phone()
    created = await api_client.post(
        USERS_URL,
        json={"phone": phone, "full_name": "Direktor", "roles": ["director"], "locale": "uz-Latn"},
        headers=platform,
    )
    assert created.status_code == 201, created.text
    temporary = created.json()["temporary_password"]

    temporary_headers = await session_headers(api_client, phone, temporary)
    changed = await api_client.post(
        CHANGE_PASSWORD_URL,
        json={"current_password": temporary, "new_password": DIRECTOR_PASSWORD},
        headers=temporary_headers,
    )
    assert changed.status_code == 204, changed.text

    return await session_headers(api_client, phone, DIRECTOR_PASSWORD)


async def _read_audit_rows(tenant_session: TenantSessionFactory, auth_seed: AuthSeed) -> list[Any]:
    """`action='read'` yozuvlari — mahsulot yo'li bilan (ilova roli + RLS)."""
    return await audit_rows(tenant_session, auth_seed.market_a_id, action=str(AuditAction.READ))


# ---------------------------------------------------------------------------
# D-11 — kim ko'radi
# ---------------------------------------------------------------------------


async def test_market_admin_sees_the_current_market_log(
    api_client: httpx.AsyncClient, auth_seed: AuthSeed
) -> None:
    """Bozor admini o'z bozorining jurnalini ko'radi, eng yangisi birinchi."""
    headers = await _market_admin(api_client, auth_seed)

    response = await api_client.get(AUDIT_URL, headers=headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["items"], "jurnal bo'sh — login yozuvi ham ko'rinmayapti"
    timestamps = [item["at"] for item in body["items"]]
    assert timestamps == sorted(timestamps, reverse=True)
    first = body["items"][0]
    assert set(first) == {
        "id",
        "at",
        "business_date",
        "actor_user_id",
        "actor_label",
        "action",
        "table_name",
        "row_id",
        "changed_keys",
        "old_value",
        "new_value",
        "request_id",
        "source",
    }


async def test_director_can_view_the_audit_log(
    api_client: httpx.AsyncClient, auth_seed: AuthSeed
) -> None:
    """D-11: direktorda `AUDIT_VIEW` bor (u nazorat rolida).

    Direktor `_director()` da ONBOARD qilinadi (D-02: vaqtinchalik parol
    almashtiriladi) — busiz parol darvozasi 403 qaytarardi va bu test
    huquqni emas, darvozani sinagan bo'lardi.
    """
    headers = await _director(api_client, auth_seed)

    response = await api_client.get(AUDIT_URL, headers=headers)

    assert response.status_code == 200, response.text


async def test_platform_admin_sees_only_the_selected_market(
    api_client: httpx.AsyncClient, auth_seed: AuthSeed
) -> None:
    """Platforma admini ham TANLANGAN bozor doirasida ko'radi — bypass yo'q (D-06).

    A bozorida ATAYIN iz qoldiriladi (A admini login qiladi), so'ng
    platforma admini B ni tanlab jurnalni so'raydi. Usiz test A'da
    umuman yozuv bo'lmagan holatda ham yashil bo'lardi.
    """
    await _market_admin(api_client, auth_seed)
    from_b = await platform_admin_headers(api_client, auth_seed, auth_seed.market_b_id)

    response = await api_client.get(AUDIT_URL, headers=from_b)

    assert response.status_code == 200, response.text
    items = response.json()["items"]
    actors = {item["actor_user_id"] for item in items}
    assert str(auth_seed.market_admin.user_id) not in actors
    assert str(auth_seed.platform_admin.user_id) in actors


async def test_cashier_cannot_view_the_audit_log(
    api_client: httpx.AsyncClient, auth_seed: AuthSeed
) -> None:
    """Kassirda `AUDIT_VIEW` YO'Q — u aynan `{PAYMENT_CREATE}` (D-07, D-11)."""
    headers = await session_headers(api_client, auth_seed.cashier.phone, auth_seed.password)

    response = await api_client.get(AUDIT_URL, headers=headers)

    assert response.status_code == 403
    assert response.json() == {"detail": "forbidden"}


async def test_inspector_cannot_view_the_audit_log(
    api_client: httpx.AsyncClient, auth_seed: AuthSeed
) -> None:
    """Nazoratchida ham `AUDIT_VIEW` yo'q — uning ishi faqat HITL navbati.

    MANBA ATAYIN `auth_seed.inspector`, `auth_seed.must_change` EMAS
    (01-11, CR-01 test-yaxlitligi). Ikkalasi ham nazoratchi, farqi faqat
    D-02 bayrog'ida — lekin `must_change` bilan javob
    `password_change_required` bo'lardi va test 403 ni ko'rib YASHIL
    qolardi-yu, `AUDIT_VIEW` yo'qligini umuman sinamasdi.

    Shu sababli `detail` ham tekshiriladi: kelajakda darvoza yana bu
    testning yo'liga tushib qolsa, u jimgina yashil emas, QIZIL bo'ladi.
    """
    headers = await session_headers(api_client, auth_seed.inspector.phone, auth_seed.password)

    response = await api_client.get(AUDIT_URL, headers=headers)

    assert response.status_code == 403
    assert response.json() == {"detail": "forbidden"}


async def test_cross_tenant_rows_are_invisible_under_every_filter(
    api_client: httpx.AsyncClient, auth_seed: AuthSeed
) -> None:
    """A bozori admini B ning yozuvlarini HECH QANDAY filtr bilan ko'rmaydi.

    B da aniq iz qoldiriladi (`PATCH /me` -> `update` yozuvi), so'ng A dan
    o'sha izni turli filtr kombinatsiyalari bilan qidiriladi. Filtrsiz
    tekshiruv yetarli emas: filtr predikati RLS predikatidan KEYIN
    qo'llanishi kerak, aks holda "topilmadi" javobi tasodifiy bo'lardi.
    """
    b_headers = await session_headers(
        api_client, auth_seed.other_market_admin.phone, auth_seed.password
    )
    patched = await api_client.patch(PROFILE_URL, json={"locale": "ru"}, headers=b_headers)
    assert patched.status_code == 200, patched.text

    a_headers = await _market_admin(api_client, auth_seed)
    outsider = str(auth_seed.other_market_admin.user_id)

    for params in (
        {"actor_user_id": outsider},
        {"table_name": "users", "action": str(AuditAction.UPDATE)},
        {"limit": 200},
    ):
        response = await api_client.get(AUDIT_URL, params=params, headers=a_headers)
        assert response.status_code == 200, response.text
        actors = {item["actor_user_id"] for item in response.json()["items"]}
        assert outsider not in actors, f"{params}: begona bozor yozuvi ko'rindi"


# ---------------------------------------------------------------------------
# D-12 — filtrlar va sahifalash
# ---------------------------------------------------------------------------


async def test_action_filter_narrows_the_result(
    api_client: httpx.AsyncClient, auth_seed: AuthSeed
) -> None:
    """`?action=login` faqat login yozuvlarini qaytaradi."""
    headers = await _market_admin(api_client, auth_seed)

    response = await api_client.get(
        AUDIT_URL, params={"action": str(AuditAction.LOGIN)}, headers=headers
    )

    assert response.status_code == 200, response.text
    items = response.json()["items"]
    assert items
    assert {item["action"] for item in items} == {str(AuditAction.LOGIN)}


async def test_actor_and_table_filters(api_client: httpx.AsyncClient, auth_seed: AuthSeed) -> None:
    """`?actor_user_id=` va `?table_name=` filtrlari birga ishlaydi."""
    headers = await _market_admin(api_client, auth_seed)

    response = await api_client.get(
        AUDIT_URL,
        params={"actor_user_id": str(auth_seed.market_admin.user_id), "table_name": "users"},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    items = response.json()["items"]
    assert items
    assert {item["actor_user_id"] for item in items} == {str(auth_seed.market_admin.user_id)}
    assert {item["table_name"] for item in items} == {"users"}


async def test_business_date_range_filter(
    api_client: httpx.AsyncClient, auth_seed: AuthSeed
) -> None:
    """`from`/`to` — `business_date` USTUNI bo'yicha (Asia/Tashkent biznes-kuni).

    Ertangi kun uchun so'rov BO'SH qaytadi: bu nazorat holati, usiz
    filtr umuman qo'llanmagan holatda ham test yashil bo'lardi.
    """
    headers = await _market_admin(api_client, auth_seed)
    today = now_tz().date()
    tomorrow = today + timedelta(days=1)

    inside = await api_client.get(
        AUDIT_URL, params={"from": today.isoformat(), "to": today.isoformat()}, headers=headers
    )
    outside = await api_client.get(
        AUDIT_URL,
        params={"from": tomorrow.isoformat(), "to": tomorrow.isoformat()},
        headers=headers,
    )

    assert inside.status_code == outside.status_code == 200
    assert inside.json()["items"]
    assert {item["business_date"] for item in inside.json()["items"]} == {today.isoformat()}
    assert outside.json()["items"] == []
    assert outside.json()["next_cursor"] is None


async def test_keyset_pagination_continues_without_gaps_or_repeats(
    api_client: httpx.AsyncClient, auth_seed: AuthSeed
) -> None:
    """`limit=1` + `cursor`: keyingi sahifa TAKRORLAMAYDI va o'tkazib yubormaydi.

    Kursor OPAQUE: test uning ichini o'qimaydi, faqat javobdan olib
    keyingi so'rovga qaytaradi — kodlash shakli ichki qaror bo'lib qoladi.

    DIQQAT: har `GET /audit` jurnalga YANGI `read` qatori qo'shadi (D-09),
    ya'ni "birinchi sahifa" har safar boshqacha bo'ladi. Shuning uchun
    tekshiruv MUTLAQ ro'yxat bilan emas, kursorning DAVOMIYLIGI bilan
    olib boriladi: kursor qat'iy yuqori chegara bo'lgani uchun undan
    keyin qo'shilgan (yangiroq) qatorlar natijaga umuman tushmaydi.
    """
    headers = await _market_admin(api_client, auth_seed)

    first = await api_client.get(AUDIT_URL, params={"limit": 1}, headers=headers)
    assert first.status_code == 200, first.text
    assert len(first.json()["items"]) == 1
    cursor = first.json()["next_cursor"]
    assert cursor, "keyingi sahifa bor, lekin kursor berilmadi"

    second = await api_client.get(AUDIT_URL, params={"limit": 1, "cursor": cursor}, headers=headers)
    tail = await api_client.get(AUDIT_URL, params={"limit": 200, "cursor": cursor}, headers=headers)

    assert second.status_code == tail.status_code == 200
    second_ids = [item["id"] for item in second.json()["items"]]
    tail_ids = [item["id"] for item in tail.json()["items"]]

    assert second_ids == tail_ids[:1], "sahifalash tartibni buzdi"
    assert first.json()["items"][0]["id"] not in tail_ids, "kursor qatorni TAKRORLADI"
    assert tail_ids == sorted(tail_ids, reverse=True)


async def test_last_page_has_no_cursor(api_client: httpx.AsyncClient, auth_seed: AuthSeed) -> None:
    """Barcha yozuvlar bitta sahifaga sig'sa `next_cursor` — `null`."""
    headers = await _market_admin(api_client, auth_seed)

    response = await api_client.get(AUDIT_URL, params={"limit": 200}, headers=headers)

    assert response.status_code == 200, response.text
    assert response.json()["next_cursor"] is None


async def test_limit_above_the_maximum_is_rejected(
    api_client: httpx.AsyncClient, auth_seed: AuthSeed
) -> None:
    """`limit=500` -> 422 (T-01-57: chegarasiz so'rov o'z-o'ziga DoS)."""
    headers = await _market_admin(api_client, auth_seed)

    response = await api_client.get(AUDIT_URL, params={"limit": 500}, headers=headers)

    assert response.status_code == 422


async def test_malformed_cursor_is_rejected(
    api_client: httpx.AsyncClient, auth_seed: AuthSeed
) -> None:
    """Buzuq kursor 422 beradi — jimgina birinchi sahifaga QAYTMAYDI.

    Jimgina qaytish sahifalashni cheksiz siklga aylantirardi va uning
    sababi mijoz tomonda umuman ko'rinmasdi.
    """
    headers = await _market_admin(api_client, auth_seed)

    response = await api_client.get(AUDIT_URL, params={"cursor": "not-a-cursor"}, headers=headers)

    assert response.status_code == 422


async def test_sensitive_values_are_masked_in_the_response(
    api_client: httpx.AsyncClient,
    auth_seed: AuthSeed,
    sync_owner_conn: Connection[TupleRow],
) -> None:
    """Jurnaldagi sezgir kalitlar javobda `"***"` bo'lib chiqadi (T-01-52).

    Ichma-ich joylashgan obyekt ham qamraladi: maskalash faqat yuqori
    darajada ishlaganda `{"credentials": {"password": ...}}` shaklidagi
    yozuv ochiq qolardi.
    """
    insert_audit_probe(
        sync_owner_conn,
        auth_seed.market_a_id,
        table_name="probe_table",
        new_value=json.dumps(
            {
                "password_hash": "$argon2id$v=19$m=65536,t=3,p=4$SIR",
                "credentials": {"password": "ochiq-parol", "note": "ko'rinishi kerak"},
            }
        ),
    )
    headers = await _market_admin(api_client, auth_seed)

    response = await api_client.get(
        AUDIT_URL, params={"table_name": "probe_table"}, headers=headers
    )

    assert response.status_code == 200, response.text
    items = response.json()["items"]
    assert len(items) == 1
    value = items[0]["new_value"]
    assert value["password_hash"] == "***"
    assert value["credentials"]["password"] == "***"
    assert value["credentials"]["note"] == "ko'rinishi kerak"
    assert "argon2" not in json.dumps(value)


# ---------------------------------------------------------------------------
# D-09 — o'qishning o'zi auditga tushadi
# ---------------------------------------------------------------------------


async def test_viewing_the_audit_log_writes_a_read_row(
    api_client: httpx.AsyncClient,
    auth_seed: AuthSeed,
    tenant_session: TenantSessionFactory,
) -> None:
    """`GET /audit` -> jurnalda `action='read'`, `table_name='audit_log'` qatori."""
    headers = await _market_admin(api_client, auth_seed)
    before = await _read_audit_rows(tenant_session, auth_seed)

    response = await api_client.get(
        AUDIT_URL, params={"action": str(AuditAction.LOGIN), "limit": 10}, headers=headers
    )
    assert response.status_code == 200, response.text

    after = await _read_audit_rows(tenant_session, auth_seed)
    assert len(after) == len(before) + 1
    row = after[-1]
    assert row.table_name == TABLE_AUDIT_LOG
    assert row.source == "app"
    assert row.actor_user_id == auth_seed.market_admin.user_id


async def test_read_row_records_reason_filters_and_result_count(
    api_client: httpx.AsyncClient,
    auth_seed: AuthSeed,
    tenant_session: TenantSessionFactory,
) -> None:
    """O'qish yozuvi NIMA o'qilganini tasvirlaydi, "o'qildi" demaydi.

    `filters` va `result_count` bo'lmasa jurnal savolga javob bermaydi:
    "kim butun jurnalni yuklab oldi" va "kim bitta yozuvni ochdi" bir
    xil ko'rinardi.
    """
    headers = await _market_admin(api_client, auth_seed)

    response = await api_client.get(
        AUDIT_URL, params={"action": str(AuditAction.LOGIN), "limit": 5}, headers=headers
    )
    assert response.status_code == 200, response.text
    returned = len(response.json()["items"])

    rows = await _read_audit_rows(tenant_session, auth_seed)
    value = rows[-1].new_value
    assert value["reason"] == "audit_view"
    assert value["result_count"] == returned
    assert value["filters"]["action"] == str(AuditAction.LOGIN)
    assert value["filters"]["limit"] == 5


async def test_reading_does_not_recurse(
    api_client: httpx.AsyncClient,
    auth_seed: AuthSeed,
    tenant_session: TenantSessionFactory,
) -> None:
    """BITTA so'rov — AYNAN BITTA `read` yozuvi (rekursiya yo'q).

    O'qish auditi endpointdan tashqarida, alohida sessiyada yoziladi;
    agar u o'z navbatida `GET /audit` yo'lidan o'tganda edi, har so'rov
    cheksiz zanjir hosil qilardi.
    """
    headers = await _market_admin(api_client, auth_seed)
    before = len(await _read_audit_rows(tenant_session, auth_seed))

    await api_client.get(AUDIT_URL, headers=headers)

    assert len(await _read_audit_rows(tenant_session, auth_seed)) == before + 1


async def test_rejected_request_writes_no_read_row(
    api_client: httpx.AsyncClient,
    auth_seed: AuthSeed,
    tenant_session: TenantSessionFactory,
) -> None:
    """403 olgan kassir hech narsani o'qimagan — yozuv ham bo'lmasligi kerak.

    Aks holda jurnalda "kassir audit jurnalini o'qidi" degan YOLG'ON dalil
    paydo bo'lardi va nizoni hal qilishda aynan shu yozuv ishlatilardi.
    """
    cashier = await session_headers(api_client, auth_seed.cashier.phone, auth_seed.password)
    before = len(await _read_audit_rows(tenant_session, auth_seed))

    rejected = await api_client.get(AUDIT_URL, headers=cashier)

    assert rejected.status_code == 403
    assert len(await _read_audit_rows(tenant_session, auth_seed)) == before


async def test_invalid_query_writes_no_read_row(
    api_client: httpx.AsyncClient,
    auth_seed: AuthSeed,
    tenant_session: TenantSessionFactory,
) -> None:
    """422 bilan rad etilgan so'rov ham o'qish yozuvi qoldirmaydi."""
    headers = await _market_admin(api_client, auth_seed)
    before = len(await _read_audit_rows(tenant_session, auth_seed))

    rejected = await api_client.get(AUDIT_URL, params={"limit": 500}, headers=headers)

    assert rejected.status_code == 422
    assert len(await _read_audit_rows(tenant_session, auth_seed)) == before
