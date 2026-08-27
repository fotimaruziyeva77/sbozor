"""Login, bozor tanlash va parol almashtirish oqimlari (FOUND-01, D-01…D-07).

=============================================================================
BU FAYLNING ENG MUHIM TESTI — `test_login_no_user_enumeration`.

U javob TANASINI ham taqqoslaydi, faqat status kodini emas. Sabab: status
kodini bir xil qilib qo'yish oson va u odatda birinchi urinishdayoq
to'g'ri bo'ladi; javob tanasiga esa vaqt o'tib "foydali" tafsilot
qo'shiladi ("telefon topilmadi", "hisob bloklangan") va o'sha payt
enumeration teshigi jimgina ochiladi. Bayt darajasidagi taqqoslash o'sha
kunni CI'da ushlaydi.
=============================================================================

Testlar HTTP chegarasidan o'tadi (`httpx.ASGITransport`), ya'ni ular
dependency'lar, Pydantic validatsiyasi, RLS va Valkey bilan birga
ISHLAYDIGAN tizimni sinaydi — funksiyalarni alohida emas.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import uuid4

import pytest
from app.security.ratelimit import PHONE_LIMIT
from app.security.tokens import COOKIE_PATH, REFRESH_COOKIE_NAME
from fixtures.auth_api import (
    CHANGE_PASSWORD_URL,
    ME_URL,
    REFRESH_URL,
    SELECT_MARKET_URL,
    audit_rows,
    draft_market,
    global_audit_rows,
    login,
    set_user_active,
)
from sbozor_core.security import decode_token

if TYPE_CHECKING:
    import httpx
    from app.settings import Settings
    from fixtures import TenantSessionFactory
    from fixtures.auth_users import AuthSeed
    from psycopg import Connection
    from psycopg.rows import TupleRow
    from redis.asyncio import Redis
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

EXPECTED_EXPIRES_IN = 900
EXPECTED_MAX_AGE = 2_592_000


async def test_login_returns_access_token_and_roles(
    api_client: httpx.AsyncClient, auth_seed: AuthSeed
) -> None:
    """Bitta a'zolikli foydalanuvchi login'da to'liq sessiya oladi."""
    response = await login(api_client, auth_seed.market_admin.phone, auth_seed.password)

    assert response.status_code == 200
    body = response.json()
    assert body["roles"] == ["market_admin"]
    assert body["market"]["id"] == str(auth_seed.market_a_id)
    assert body["market"]["name"] == auth_seed.market_a_name
    # `is_active` — MAJBURIY maydon (02-03): javob shakli bozor faolligini
    # uzatadi, ya'ni bu yerdagi bayt-bayt taqqoslash uni ham qamraydi.
    assert body["markets"] == [
        {"id": str(auth_seed.market_a_id), "name": auth_seed.market_a_name, "is_active": True}
    ]
    assert body["is_platform_admin"] is False
    assert body["must_change_password"] is False
    assert body["expires_in"] == EXPECTED_EXPIRES_IN
    assert body["token_type"] == "bearer"
    assert body["locale"] == "uz-Latn"


async def test_access_token_claims(
    api_client: httpx.AsyncClient, auth_seed: AuthSeed, test_settings: Settings
) -> None:
    """Token ichida `typ='access'`, `sub` — satr, `roles` — ro'yxat, `mid` — tanlangan bozor."""
    response = await login(api_client, auth_seed.market_admin.phone, auth_seed.password)
    claims = decode_token(
        response.json()["access_token"],
        expected_type="access",
        secret=test_settings.jwt_secret,
        issuer=test_settings.jwt_issuer,
        audience=test_settings.jwt_audience,
    )

    assert claims.token_type == "access"
    assert claims.user_id == auth_seed.market_admin.user_id
    assert claims.market_id == auth_seed.market_a_id
    assert claims.roles == ["market_admin"]
    assert claims.is_platform_admin is False


async def test_refresh_cookie_attributes(
    api_client: httpx.AsyncClient, auth_seed: AuthSeed
) -> None:
    """Cookie atributlari T-01-42/T-01-43 talablariga mos.

    Atribut QIYMATLARI RFC 6265 bo'yicha registrga sezgir emas
    (`SameSite=Lax` va `SameSite=lax` bir xil), shuning uchun taqqoslash
    kichik harfda bajariladi.
    """
    response = await login(api_client, auth_seed.market_admin.phone, auth_seed.password)
    raw = response.headers.get("set-cookie")

    assert raw is not None, "login refresh cookie'sini qo'ymadi"
    lowered = raw.lower()
    assert raw.startswith(f"{REFRESH_COOKIE_NAME}=")
    assert "httponly" in lowered
    assert "samesite=lax" in lowered
    assert f"path={COOKIE_PATH}".lower() in lowered
    assert f"max-age={EXPECTED_MAX_AGE}" in lowered


async def test_refresh_cookie_name_matches_tokens_constant() -> None:
    """`Cookie(alias=...)` literali va `REFRESH_COOKIE_NAME` bir xil.

    FastAPI alias'i OpenAPI sxemasiga tushadi va o'zgaruvchi bo'la
    olmaydi, ya'ni nom ikki joyda yozilgan. Ular ajralib qolsa cookie
    qo'yiladi-yu, endpoint uni O'QIY OLMAYDI va `/refresh` jimgina
    401 bera boshlaydi.
    """
    from app.api.v1 import auth as auth_module

    aliases = [
        item.alias
        for item in auth_module.RefreshCookie.__metadata__  # type: ignore[attr-defined]
        if getattr(item, "alias", None)
    ]
    assert aliases == [REFRESH_COOKIE_NAME]


async def test_login_no_user_enumeration(
    api_client: httpx.AsyncClient, auth_seed: AuthSeed
) -> None:
    """Mavjud bo'lmagan telefon va noto'g'ri parol AYNAN bir xil javob beradi (T-01-40)."""
    unknown = await login(api_client, "+998900000001", auth_seed.password)
    wrong_password = await login(api_client, auth_seed.market_admin.phone, "butunlay-boshqa-parol")

    assert unknown.status_code == wrong_password.status_code == 401
    assert unknown.json() == wrong_password.json()
    assert unknown.content == wrong_password.content


async def test_blocked_user_is_indistinguishable_from_wrong_password(
    api_client: httpx.AsyncClient, auth_seed: AuthSeed
) -> None:
    """Bloklangan foydalanuvchi TO'G'RI parol bilan ham bir xil 401 oladi (D-08 + T-01-40)."""
    blocked = await login(api_client, auth_seed.blocked.phone, auth_seed.password)
    wrong_password = await login(api_client, auth_seed.market_admin.phone, "butunlay-boshqa-parol")

    assert blocked.status_code == 401
    assert blocked.json() == wrong_password.json()
    assert blocked.content == wrong_password.content


async def test_must_change_password_user_gets_flag(
    api_client: httpx.AsyncClient, auth_seed: AuthSeed
) -> None:
    """D-02: vaqtinchalik parol bilan kirish MUVAFFAQIYATLI, lekin bayroq `true`."""
    response = await login(api_client, auth_seed.must_change.phone, auth_seed.password)

    assert response.status_code == 200
    assert response.json()["must_change_password"] is True


@pytest.mark.parametrize("template", ["{national}", "+998{national}", "+998 {spaced}"])
async def test_phone_is_normalized_across_formats(
    api_client: httpx.AsyncClient, auth_seed: AuthSeed, template: str
) -> None:
    """D-01: uch xil yozilish shakli AYNI foydalanuvchini topadi.

    Normalizatsiya chegarada bo'lmasa bir odam ikkita hisob olardi va
    uning qarz tarixi ikkiga bo'linardi.
    """
    national = auth_seed.market_admin.phone.removeprefix("+998")
    spaced = f"{national[:2]} {national[2:5]} {national[5:7]} {national[7:]}"

    response = await login(
        api_client,
        template.format(national=national, spaced=spaced),
        auth_seed.password,
    )

    assert response.status_code == 200
    assert response.json()["market"]["id"] == str(auth_seed.market_a_id)


async def test_unparsable_phone_is_422_not_401(
    api_client: httpx.AsyncClient, auth_seed: AuthSeed
) -> None:
    """Formatni o'qib bo'lmasa 422 — bu enumeration signali EMAS.

    422 "raqam shakli noto'g'ri" deydi, "bunday foydalanuvchi yo'q"
    demaydi. Mavjud bo'lmagan, lekin YAROQLI raqam esa odatdagi 401 oladi
    (yuqoridagi enumeration testi).
    """
    response = await login(api_client, "salom", auth_seed.password)
    assert response.status_code == 422


async def test_login_rate_limit(api_client: httpx.AsyncClient, auth_seed: AuthSeed) -> None:
    """T-01-39: bir telefon uchun chegaradan keyingi urinish 429 beradi."""
    for _ in range(PHONE_LIMIT):
        attempt = await login(api_client, auth_seed.market_admin.phone, "noto-g-ri-parol")
        assert attempt.status_code == 401

    blocked = await login(api_client, auth_seed.market_admin.phone, "noto-g-ri-parol")
    assert blocked.status_code == 429
    assert blocked.json() == {"detail": "too_many_attempts"}


async def test_successful_login_clears_rate_counter(
    api_client: httpx.AsyncClient, auth_seed: AuthSeed, valkey_client: Redis
) -> None:
    """Muvaffaqiyatli login sanagichni tozalaydi.

    Busiz kunduzi parolini bir necha marta noto'g'ri yozgan kassir
    muvaffaqiyatli kirgandan keyin ham chegaraga yaqin turardi.
    """
    phone = auth_seed.market_admin.phone
    for _ in range(3):
        await login(api_client, phone, "noto-g-ri-parol")
    assert await valkey_client.get(f"rl:login:phone:{phone}") is not None

    success = await login(api_client, phone, auth_seed.password)

    assert success.status_code == 200
    assert await valkey_client.get(f"rl:login:phone:{phone}") is None


async def test_login_writes_audit_row(
    api_client: httpx.AsyncClient,
    auth_seed: AuthSeed,
    tenant_session: TenantSessionFactory,
) -> None:
    """D-09: muvaffaqiyatli kirish `action='login'` yozuvini qoldiradi."""
    await login(api_client, auth_seed.market_admin.phone, auth_seed.password)

    rows = await audit_rows(tenant_session, auth_seed.market_a_id, action="login")

    assert len(rows) == 1
    assert rows[0].actor_user_id == auth_seed.market_admin.user_id
    assert rows[0].source == "app"
    assert rows[0].table_name == "users"


async def test_failed_login_writes_login_failed_audit(
    api_client: httpx.AsyncClient,
    auth_seed: AuthSeed,
    sync_superuser_conn: Connection[TupleRow],
) -> None:
    """Muvaffaqiyatsiz urinish ham izsiz qolmaydi (D-09).

    Yozuvda `market_id IS NULL` (rad etilgan urinishda bozor aniqlanmagan),
    shuning uchun u `audit_read` policy'si ostida NA ilova, NA ega roliga
    ko'rinadi — ataylab. Bu test uni klaster superuseri bilan o'qiydi;
    mahsulot yo'li (platforma admini uchun tor `SECURITY DEFINER` funksiya)
    01-07 rejasida quriladi.
    """
    await login(api_client, auth_seed.market_admin.phone, "noto-g-ri-parol")

    rows = global_audit_rows(
        sync_superuser_conn, action="login_failed", phone=auth_seed.market_admin.phone
    )

    assert len(rows) == 1
    assert rows[0][0] == "login_failed"
    assert rows[0][1] == "app"
    assert rows[0][2]["reason"] == "bad_password"


async def test_register_route_does_not_exist() -> None:
    """D-04: o'z-o'zidan ro'yxatdan o'tish endpointi YO'Q va bo'lmaydi."""
    from app.main import app

    paths = set(app.openapi()["paths"])
    assert "/api/v1/auth/register" not in paths
    assert not any(path.endswith("/register") for path in paths)


async def test_platform_admin_gets_market_list_without_selection(
    api_client: httpx.AsyncClient, auth_seed: AuthSeed
) -> None:
    """D-06: platforma admini bozor TANLAB kiradi — login'da `market` `None`."""
    response = await login(api_client, auth_seed.platform_admin.phone, auth_seed.password)

    assert response.status_code == 200
    body = response.json()
    assert body["market"] is None
    assert body["is_platform_admin"] is True
    assert {market["id"] for market in body["markets"]} >= {
        str(auth_seed.market_a_id),
        str(auth_seed.market_b_id),
    }
    # Bozor tanlanmagan sessiya uchun refresh cookie BERILMAYDI —
    # `refresh_tokens.market_id` NOT NULL va bozorsiz sessiyaning ma'nosi yo'q.
    assert response.headers.get("set-cookie") is None


async def test_platform_admin_can_select_each_market(
    api_client: httpx.AsyncClient, auth_seed: AuthSeed
) -> None:
    """A ni tanlab A ni, B ni tanlab B ni ko'radi — RLS ikkalasida ham ishlaydi (D-06)."""
    login_body = (
        await login(api_client, auth_seed.platform_admin.phone, auth_seed.password)
    ).json()
    headers = {"Authorization": f"Bearer {login_body['access_token']}"}

    for market_id, market_name in (
        (auth_seed.market_a_id, auth_seed.market_a_name),
        (auth_seed.market_b_id, auth_seed.market_b_name),
    ):
        selected = await api_client.post(
            SELECT_MARKET_URL, json={"market_id": str(market_id)}, headers=headers
        )
        assert selected.status_code == 200, selected.text
        assert selected.json()["market"] == {
            "id": str(market_id),
            "name": market_name,
            "is_active": True,
        }

        # Tanlangan token bilan `/me` AYNAN o'sha bozorni tenant sessiyasidan o'qiydi.
        me = await api_client.get(
            ME_URL,
            headers={"Authorization": f"Bearer {selected.json()['access_token']}"},
        )
        assert me.status_code == 200, me.text
        assert me.json()["market"] == {
            "id": str(market_id),
            "name": market_name,
            "is_active": True,
        }


async def test_member_cannot_select_foreign_market(
    api_client: httpx.AsyncClient, auth_seed: AuthSeed
) -> None:
    """A'zoligi bo'lmagan bozorni tanlash 403 (D-06)."""
    login_body = (await login(api_client, auth_seed.market_admin.phone, auth_seed.password)).json()

    response = await api_client.post(
        SELECT_MARKET_URL,
        json={"market_id": str(auth_seed.market_b_id)},
        headers={"Authorization": f"Bearer {login_body['access_token']}"},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "market_forbidden"}


async def test_unknown_market_is_also_403(
    api_client: httpx.AsyncClient, auth_seed: AuthSeed
) -> None:
    """Mavjud bo'lmagan bozor ham AYNAN 403 — mavjudlik oshkor qilinmaydi (T-01-47)."""
    login_body = (
        await login(api_client, auth_seed.platform_admin.phone, auth_seed.password)
    ).json()

    response = await api_client.post(
        SELECT_MARKET_URL,
        json={"market_id": str(uuid4())},
        headers={"Authorization": f"Bearer {login_body['access_token']}"},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "market_forbidden"}


async def test_login_reports_draft_market_as_inactive(
    api_client: httpx.AsyncClient,
    auth_seed: AuthSeed,
    sync_owner_conn: Connection[TupleRow],
) -> None:
    """A'zolik tarmog'i qoralama bozorni ro'yxatga chiqaradi VA `is_active: false` deydi.

    IKKI DA'VO, IKKALASI HAM ZARUR (UI-SPEC §12.1.1 X-2):

    1. Bozor RO'YXATDA BOR. A'zolik tarmog'ida hech qachon filtr bo'lmagan,
       ya'ni bu da'vo o'zgarishdan oldin ham bajarilardi — u regressiya
       qulfi sifatida turadi.
    2. Bayroq `false`. Aynan SHU YANGI: ilgari `MarketRef` da bunday maydon
       umuman yo'q edi va UI qoralamani faoldan ajrata olmasdi. Standart
       qiymatli (`= True`) maydon bu testni jimgina yashil qilardi —
       shuning uchun `MarketRef.is_active` da standart qiymat YO'Q.

    Foydalanuvchi ATAYIN `inspector`: uning bitta a'zoligi bor, ya'ni
    ikkinchi (qoralama) a'zolik qo'shilgach bozor AVTOMATIK tanlanmaydi va
    `markets` ro'yxati to'ldiriladi — bozor tanlash ekranidagi holat.
    """
    with draft_market(sync_owner_conn, member_id=auth_seed.inspector.user_id) as market_id:
        body = (await login(api_client, auth_seed.inspector.phone, auth_seed.password)).json()

    listed = {market["id"]: market for market in body["markets"]}
    assert str(market_id) in listed, f"qoralama bozor a'zolik ro'yxatiga chiqmadi: {sorted(listed)}"
    assert listed[str(market_id)]["is_active"] is False, (
        "qoralama bozor 'faol' deb yorliqlandi — UI uni oddiy bozordan ajrata olmaydi"
    )
    # NAZORAT: o'sha javobdagi HAQIQIY faol bozor `true` bo'lib qoladi, ya'ni
    # bayroq har doim `false` deb qattiq yozilmagan.
    assert listed[str(auth_seed.market_a_id)]["is_active"] is True


async def test_platform_admin_sees_draft_market_in_list(
    api_client: httpx.AsyncClient,
    auth_seed: AuthSeed,
    sync_owner_conn: Connection[TupleRow],
) -> None:
    """Platforma admini qoralama bozorni ro'yxatda KO'RADI (avval server kesib tashlardi).

    Bu — o'zgarishning to'g'ridan-to'g'ri qulfi. Ilgari `_visible_markets()`
    platforma admini tarmog'ida bayroq bo'yicha kesardi, ya'ni ustani boshlab
    yarim tashlab ketgan odam O'ZI yaratgan qoralamani qaytib topa olmasdi —
    a'zolik tarmog'idagi bozor admini esa uni ko'raverardi (assimetriya).

    A'zolik ATAYIN berilmaydi: platforma admini tarmog'i (`auth_list_markets()`)
    aynan a'zoliksiz ishlashi kerak.
    """
    with draft_market(sync_owner_conn) as market_id:
        body = (await login(api_client, auth_seed.platform_admin.phone, auth_seed.password)).json()

    listed = {market["id"]: market for market in body["markets"]}
    assert str(market_id) in listed, (
        "qoralama bozor platforma admini ro'yxatida yo'q — server hamon kesyapti"
    )
    assert listed[str(market_id)]["is_active"] is False
    assert listed[str(auth_seed.market_a_id)]["is_active"] is True


async def test_platform_admin_can_select_a_draft_market(
    api_client: httpx.AsyncClient,
    auth_seed: AuthSeed,
    sync_owner_conn: Connection[TupleRow],
) -> None:
    """Ko'ringan qoralama bozor TANLANADI ham — ko'rinadigan, lekin o'lik element qolmaydi.

    Ro'yxatni ochib, tanlashni yopiq qoldirish o'zgarishdan OLDINGI holatdan
    ham yomonroq bo'lardi: foydalanuvchi qoralamani ko'rib, bosib, 403 olardi.
    Bundan tashqari ustaning O'Z oqimi shu yo'lga tayanadi — 2–7-qadamlar
    tenant-scoped jadvallarga yozadi, ya'ni ular `app.market_id` ni aynan
    qoralama bozorga o'rnatishni talab qiladi.

    Javobdagi `is_active: false` — usta relsini chizish uchun kerakli signal
    (UI-SPEC §6.4: bosilganda birinchi tugallanmagan qadamga o'tiladi).
    """
    login_body = (
        await login(api_client, auth_seed.platform_admin.phone, auth_seed.password)
    ).json()
    headers = {"Authorization": f"Bearer {login_body['access_token']}"}

    with draft_market(sync_owner_conn, name="Karmana (qoralama)") as market_id:
        selected = await api_client.post(
            SELECT_MARKET_URL, json={"market_id": str(market_id)}, headers=headers
        )
        assert selected.status_code == 200, selected.text
        assert selected.json()["market"] == {
            "id": str(market_id),
            "name": "Karmana (qoralama)",
            "is_active": False,
        }

        # Tanlangan token bilan tenant konteksti HAQIQATAN o'sha bozorga
        # bog'landi — ya'ni usta qadamlari shu sessiyada yozishi mumkin.
        me = await api_client.get(
            ME_URL, headers={"Authorization": f"Bearer {selected.json()['access_token']}"}
        )
        assert me.status_code == 200, me.text
        assert me.json()["market"]["id"] == str(market_id)
        assert me.json()["market"]["is_active"] is False


async def test_member_cannot_select_a_foreign_draft_market(
    api_client: httpx.AsyncClient,
    auth_seed: AuthSeed,
    sync_owner_conn: Connection[TupleRow],
) -> None:
    """NAZORAT HOLATI: qoralama bozor darvozani HAMMAGA ochib yubormaydi.

    Usiz yuqoridagi test "endi har kim har qanday bozorni tanlay oladi"
    holatida ham yashil ko'rinardi. Bu yerda a'zoligi bo'lmagan oddiy
    bozor admini AYNAN o'sha qoralama bozorni so'raydi va 403
    `market_forbidden` oladi — vakolat hamon `is_platform_admin` bayrog'iga
    bog'liq, bozorning faolligiga emas (T-01-47 bo'yicha javob "bunday
    bozor bor" degan signalni ham bermaydi).
    """
    login_body = (await login(api_client, auth_seed.market_admin.phone, auth_seed.password)).json()
    headers = {"Authorization": f"Bearer {login_body['access_token']}"}

    with draft_market(sync_owner_conn) as market_id:
        response = await api_client.post(
            SELECT_MARKET_URL, json={"market_id": str(market_id)}, headers=headers
        )

    assert response.status_code == 403
    assert response.json() == {"detail": "market_forbidden"}


_DEMOTE = "UPDATE users SET is_platform_admin = %s WHERE id = %s"
"""`sbozor_owner` bilan bajariladi — `users` app-rolga butunlay yopiq.

Mahsulot yo'li (lavozimni olib tashlash endpointi) 1-fazada YO'Q va aynan
shu sababdan WR-03 hali ekspluatatsiya qilinmagan edi. Test o'sha
endpoint tug'ilgandagi holatni oldindan qulflaydi.
"""


async def test_select_market_rereads_platform_admin_flag(
    api_client: httpx.AsyncClient,
    auth_seed: AuthSeed,
    sync_owner_conn: Connection[TupleRow],
    test_settings: Settings,
) -> None:
    """Bayroq DB'da o'chirilgach ESKI token yangi `pa=true` sessiya BERMAYDI (WR-03).

    `select-market` — tokendan token yasaydigan YAGONA yo'l. 1-fazada u
    `is_platform_admin` ni KELGAN da'vodan ko'chirardi, ya'ni zanjir
    `token -> select-market -> yangi token -> select-market -> ...`
    `users` jadvaliga umuman tegmasdan bayroqni CHEKSIZ yangilardi.

    Bu bayroqni QO'LGA KIRITISH yo'li emas edi (`_assert_roles_assignable`
    va `require_platform_admin` uni to'g'ri rad etadi) — bu uni BEKOR
    QILISHDAN keyin SAQLAB QOLISH yo'li edi. `login` va `refresh`
    allaqachon DB'dan o'qiydi; `select-market` yagona istisno edi.

    Da'vo `pa` CLAIM'i bo'yicha tekshiriladi, `roles` bo'yicha EMAS:
    `require_platform_admin` va `markets.list_markets` aynan shu bayroqqa
    qaraydi (CR-03 ning darsi — rol nomi a'zolikdan ham kelishi mumkin, va
    bu seed'da platforma adminining a'zolik roli aynan `platform_admin`).
    """
    login_body = (
        await login(api_client, auth_seed.platform_admin.phone, auth_seed.password)
    ).json()
    assert login_body["is_platform_admin"] is True
    headers = {"Authorization": f"Bearer {login_body['access_token']}"}

    sync_owner_conn.execute(_DEMOTE, (False, str(auth_seed.platform_admin.user_id)))

    selected = await api_client.post(
        SELECT_MARKET_URL, json={"market_id": str(auth_seed.market_a_id)}, headers=headers
    )

    assert selected.status_code == 200, selected.text
    claims = decode_token(
        selected.json()["access_token"],
        expected_type="access",
        secret=test_settings.jwt_secret,
        issuer=test_settings.jwt_issuer,
        audience=test_settings.jwt_audience,
    )
    assert claims.is_platform_admin is False, (
        "`select-market` bayroqni tokendan ko'chirdi — lavozimi olib tashlangan "
        "hisob `pa=true` ni cheksiz yangilay oladi (WR-03)"
    )

    # Ikkinchi yarim: bayroq faqat token ichida emas, QARORDA ham o'chgan.
    # A'zoligi bo'lmagan bozorni tanlash endi platforma admini yo'lidan
    # o'tmaydi (403 — `test_unknown_market_is_also_403` bilan bir xil kod,
    # mavjudlik oshkor qilinmaydi).
    foreign = await api_client.post(
        SELECT_MARKET_URL, json={"market_id": str(uuid4())}, headers=headers
    )
    assert foreign.status_code == 403
    assert foreign.json() == {"detail": "market_forbidden"}


async def test_select_market_keeps_platform_admin_when_still_set(
    api_client: httpx.AsyncClient,
    auth_seed: AuthSeed,
    test_settings: Settings,
) -> None:
    """NAZORAT HOLATI: bayroq DB'da HAMON `true` bo'lsa u saqlanadi.

    Usiz yuqoridagi test "hamma narsa rad etilyapti" holatida ham yashil
    ko'rinardi — masalan `find_login_by_id` har doim `None` qaytarsa yoki
    bayroq har doim `false` ga qattiq yozilsa. Bu test qayta o'qish
    HAQIQIY qiymatni olayotganini isbotlaydi.
    """
    login_body = (
        await login(api_client, auth_seed.platform_admin.phone, auth_seed.password)
    ).json()
    headers = {"Authorization": f"Bearer {login_body['access_token']}"}

    selected = await api_client.post(
        SELECT_MARKET_URL, json={"market_id": str(auth_seed.market_b_id)}, headers=headers
    )

    assert selected.status_code == 200, selected.text
    claims = decode_token(
        selected.json()["access_token"],
        expected_type="access",
        secret=test_settings.jwt_secret,
        issuer=test_settings.jwt_issuer,
        audience=test_settings.jwt_audience,
    )
    assert claims.is_platform_admin is True
    assert "platform_admin" in claims.roles


async def test_select_market_rejects_blocked_user_inside_the_cache_window(
    api_client: httpx.AsyncClient,
    auth_seed: AuthSeed,
    api_sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    """Bloklangan hisob bozor tanlay olmaydi — HATTO kesh hali "faol" desa ham.

    `is_active` ni `get_current_principal` ham tekshiradi, LEKIN u Valkey
    keshidan o'qiydi (`USER_STATE_TTL_SECONDS = 30`). Bloklash mahsulot
    endpointi orqali kelganda kesh darhol bekor qilinadi; boshqa har qanday
    yo'ldan (to'g'ridan-to'g'ri DB, migratsiya, kelajakdagi fon jarayoni)
    kelganda esa 30 soniyalik oyna ochiq qoladi. `select-market` aynan o'sha
    oynada YANGI 30 KUNLIK refresh oila ocha olardi — ya'ni bir necha
    soniyalik nomuvofiqlik bir oylik sessiyaga aylanardi.

    Test ATAYIN keshni AVVAL isitadi (`GET /api/v1/me`), so'ng bayroqni
    keshni bekor qilmasdan o'chiradi. Shu tartibsiz javob 401
    `account_blocked` bo'lardi — ya'ni test bu yerdagi tekshiruvni emas,
    `get_current_principal` ni sinagan bo'lardi (green-for-wrong-reason).

    Javob 401 `invalid_credentials` — MAVJUD kod: "bu hisob bor, lekin
    bloklangan" degan signal berilmaydi (T-01-40 enumeration siyosati).
    """
    login_body = (
        await login(api_client, auth_seed.platform_admin.phone, auth_seed.password)
    ).json()
    headers = {"Authorization": f"Bearer {login_body['access_token']}"}

    # Keshni isitadi: `user:state:{id}` endi "faol, almashtirish shart emas".
    # (Bozor tanlanmagani uchun javob 409, lekin principal qurilgan — kerakli yon ta'sir.)
    warmed = await api_client.get(ME_URL, headers=headers)
    assert warmed.status_code == 409, warmed.text

    await set_user_active(api_sessionmaker, auth_seed.platform_admin.user_id, is_active=False)
    try:
        response = await api_client.post(
            SELECT_MARKET_URL, json={"market_id": str(auth_seed.market_a_id)}, headers=headers
        )
    finally:
        await set_user_active(api_sessionmaker, auth_seed.platform_admin.user_id, is_active=True)

    assert response.status_code == 401
    assert response.json() == {"detail": "invalid_credentials"}


async def test_select_market_audit_carries_platform_admin_label(
    api_client: httpx.AsyncClient,
    auth_seed: AuthSeed,
    tenant_session: TenantSessionFactory,
) -> None:
    """D-06: auditda "platforma admini X bozorida" matni bo'ladi."""
    login_body = (
        await login(api_client, auth_seed.platform_admin.phone, auth_seed.password)
    ).json()
    await api_client.post(
        SELECT_MARKET_URL,
        json={"market_id": str(auth_seed.market_a_id)},
        headers={"Authorization": f"Bearer {login_body['access_token']}"},
    )

    rows = await audit_rows(tenant_session, auth_seed.market_a_id, action="market_selected")

    assert len(rows) == 1
    label = rows[0].actor_label
    assert label is not None
    assert "platforma admini" in label
    assert auth_seed.platform_admin.phone in label
    assert auth_seed.market_a_name in label


async def test_me_requires_selected_market(
    api_client: httpx.AsyncClient, auth_seed: AuthSeed
) -> None:
    """Bozor tanlanmagan token bilan tenant so'rovi 409 beradi, jimgina 0 qator EMAS."""
    login_body = (
        await login(api_client, auth_seed.platform_admin.phone, auth_seed.password)
    ).json()

    response = await api_client.get(
        ME_URL, headers={"Authorization": f"Bearer {login_body['access_token']}"}
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "market_not_selected"}


async def test_me_without_token_is_401(api_client: httpx.AsyncClient) -> None:
    """Tokensiz so'rov 401 — anonim kirish yo'li yo'q."""
    response = await api_client.get(ME_URL)
    assert response.status_code == 401


async def test_change_password_clears_flag_and_revokes_sessions(
    api_client: httpx.AsyncClient, auth_seed: AuthSeed
) -> None:
    """D-02: almashtirishdan keyin bayroq `false` va ESKI sessiya o'ladi."""
    first = await login(api_client, auth_seed.must_change.phone, auth_seed.password)
    assert first.json()["must_change_password"] is True
    old_cookie = api_client.cookies.get(REFRESH_COOKIE_NAME)
    assert old_cookie is not None

    new_password = "yangi-uzun-parol-2026"  # noqa: S105 — test ma'lumoti
    changed = await api_client.post(
        CHANGE_PASSWORD_URL,
        json={"current_password": auth_seed.password, "new_password": new_password},
        headers={"Authorization": f"Bearer {first.json()['access_token']}"},
    )
    assert changed.status_code == 204

    stale = await api_client.post(
        REFRESH_URL, headers={"Cookie": f"{REFRESH_COOKIE_NAME}={old_cookie}"}
    )
    assert stale.status_code == 401

    again = await login(api_client, auth_seed.must_change.phone, new_password)
    assert again.status_code == 200
    assert again.json()["must_change_password"] is False


async def test_change_password_wrong_current_is_401(
    api_client: httpx.AsyncClient, auth_seed: AuthSeed
) -> None:
    """Joriy parol noto'g'ri bo'lsa almashtirish rad etiladi."""
    body = (await login(api_client, auth_seed.market_admin.phone, auth_seed.password)).json()

    response = await api_client.post(
        CHANGE_PASSWORD_URL,
        json={"current_password": "boshqa-parol", "new_password": "yangi-uzun-parol-2026"},
        headers={"Authorization": f"Bearer {body['access_token']}"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "invalid_credentials"}


@pytest.mark.parametrize("candidate", ["qisqa", "             ", "{current}"])
async def test_change_password_rejects_weak_password(
    api_client: httpx.AsyncClient, auth_seed: AuthSeed, candidate: str
) -> None:
    """Qisqa, faqat bo'sh joydan iborat va joriysi bilan bir xil parol — 400."""
    body = (await login(api_client, auth_seed.market_admin.phone, auth_seed.password)).json()
    new_password = candidate.format(current=auth_seed.password)

    response = await api_client.post(
        CHANGE_PASSWORD_URL,
        json={"current_password": auth_seed.password, "new_password": new_password},
        headers={"Authorization": f"Bearer {body['access_token']}"},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "weak_password"}


def test_login_response_has_no_password_field(api_client: httpx.AsyncClient) -> None:
    """OpenAPI sxemasida javob tomonida parol/hash maydoni umuman yo'q."""
    from app.main import app

    schema: dict[str, Any] = app.openapi()["components"]["schemas"]["LoginResponse"]
    leaked = [
        name
        for name in schema["properties"]
        if "password" in name and name != "must_change_password"
    ]
    assert not leaked, f"login javobida parolga oid maydon: {leaked}"
