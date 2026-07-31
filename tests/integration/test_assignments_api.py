"""Biriktirish API'sining xulqi — D-09/D-10/D-11 ning ENDPOINT darajasidagi isboti.

=============================================================================
BU FAYL 02-07 DAGI `test_stall_assignments.py` NING O'RNINI BOSMAYDI.

U SXEMA darajasida isbotlaydi: `ex_stall_assignments_no_overlap` qoplanuvchi
davrni `23P01` bilan rad etadi, `[)` chegarasi almashinuv kunini yangi
sotuvchiga beradi va bo'shliq kunida `period @> :d` 0 qator qaytaradi. Bu
yerdagi savol boshqa: **ilova qatlami o'sha kafolatlarni foydalanuvchiga
QANDAY ko'rsatadi** — qaysi HTTP kodi, qaysi `detail`, javobda qaysi
maydonlar va almashinuv oqimi API orqali qanday bajariladi.

Ikkisi bir-birini almashtira olmaydi: sxema testi 500 bilan yiqiladigan
endpointda ham YASHIL qolardi, API testi esa konstrayt butunlay olib
tashlanganda "409 kelmadi" deb qizarardi-yu, sababni ko'rsata olmasdi.
=============================================================================

SANALAR `market_today` FIXTURE'IDAN HISOBLANADI (02-07 deviatsiya #1).
Seed'ning sobit biriktirish sanalari (`HANDOVER_DAY`, `GAP_*`) bu faylda
ATAYIN ishlatilmaydi: ular kalendar bilan birga "o'tmish" tomonga suriladi
va "bugun kim biriktirilgan" javobi bir necha kundan keyin butunlay
o'zgarardi — ya'ni testlar sababsiz qizarardi. Har bir davr shu yerda,
bugundan hisoblab yoziladi.

ALMASHINUV OQIMI IKKI CHAQIRUV: yopish (`PATCH`) + ochish (`POST`).
Qulaylik endpointi ATAYIN yo'q (T-02-72), shuning uchun testlar ham uni
ikki qadamda bajaradi — bu oqimning O'ZI mahsulot kontrakti.
"""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING
from uuid import UUID

import pytest
from fixtures.admin_api import ASSIGNMENTS_URL, STALLS_URL, VENDORS_URL, session_headers
from fixtures.two_markets import SEED_PASSWORD

if TYPE_CHECKING:
    from datetime import date

    import httpx
    from fixtures import MarketDomainSeed, MarketScope
    from fixtures.market_domain import MarketDomainRows
    from fixtures.two_markets import TwoMarketSeed

SPAN_DAYS = 10
"""Davr uzunligi — sanalar `market_today` dan shu qadam bilan hisoblanadi."""

PAST_DAYS = 10
"""Bugundan ORQAGA qadam: almashinuv va bo'shliq stsenariylari o'tmishdan boshlanadi.

`POST /assignments` da `from_date` uchun O'TMISH DARVOZASI YO'Q va bu
ataylab: bozor yillar davomida ishlab kelgan, ya'ni mavjud sotuvchini
tizimga kiritish uning haqiqiy boshlanish sanasi bilan yozilishi kerak
(A3). Tarifdan farqi shu — narx o'tmishdagi HISOBNI qayta baholardi,
biriktirish esa mavjud haqiqatni qayd etadi.
"""

NEW_VENDOR_PHONE = "+998909990202"
"""Testlar YARATADIGAN sotuvchining telefoni — seed diapazonlaridan TASHQARIDA.

`A_VENDOR_PHONES` `+99890111...` ni, `two_markets._next_phone()` esa
`+99897...` ni ishlatadi; `test_vendors_api.NEW_PHONE` esa `...0101`.
To'rtinchi diapazon ularning birortasiga ham tegmaydi.
"""


# ---------------------------------------------------------------------------
# Sessiyalar va yordamchilar
# ---------------------------------------------------------------------------


@pytest.fixture
async def admin_headers(
    api_client: httpx.AsyncClient,
    two_markets: TwoMarketSeed,
    market_domain: MarketDomainSeed,
) -> dict[str, str]:
    """A bozori adminining sessiyasi (`VENDOR_MANAGE` + `MARKET_DATA_VIEW`)."""
    market_a = two_markets.market_a
    return await session_headers(api_client, market_a.admin_phone, market_a.admin_password)


@pytest.fixture
async def director_headers(
    api_client: httpx.AsyncClient,
    two_markets: TwoMarketSeed,
    market_domain: MarketDomainSeed,
) -> dict[str, str]:
    """A bozori direktorining sessiyasi — ko'radi, lekin biriktirmaydi (D-07)."""
    market_a = two_markets.market_a
    return await session_headers(api_client, market_a.director_phone, SEED_PASSWORD)


def _free_stalls(rows: MarketDomainRows) -> tuple[UUID, ...]:
    """Seed'da BIRORTA biriktirish davri yo'q rastalar.

    Indeks bo'yicha tanlanmaydi (`stall_ids[2]` kabi): seed tartibi
    o'zgarganda bunday tanlov jimgina BAND rastaga tushib, testni
    409 `assignment_period_overlaps` bilan yiqitardi — va sabab
    qoplanish mantiqiga o'xshab ko'rinardi, holbuki xato tanlovda edi.
    """
    busy = {rows.handover_stall_id, rows.gap_stall_id}
    return tuple(stall_id for stall_id in rows.stall_ids if stall_id not in busy)


async def _assign(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    *,
    stall_id: UUID,
    vendor_id: UUID,
    from_date: date,
    to_date: date | None = None,
) -> httpx.Response:
    body: dict[str, str] = {
        "stall_id": str(stall_id),
        "vendor_id": str(vendor_id),
        "from_date": from_date.isoformat(),
    }
    if to_date is not None:
        body["to_date"] = to_date.isoformat()
    return await client.post(ASSIGNMENTS_URL, json=body, headers=headers)


async def _close(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    assignment_id: str,
    to_date: date,
) -> httpx.Response:
    return await client.patch(
        f"{ASSIGNMENTS_URL}/{assignment_id}",
        json={"to_date": to_date.isoformat()},
        headers=headers,
    )


async def _history(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    stall_id: UUID,
) -> httpx.Response:
    return await client.get(f"{STALLS_URL}/{stall_id}/assignments", headers=headers)


async def _new_vendor(client: httpx.AsyncClient, headers: dict[str, str]) -> UUID:
    """BIRORTA seed biriktirishi bo'lmagan TOZA sotuvchi.

    ⚠ SEED SOTUVCHISI "bugungi rastalar soni" testlariga YARAMAYDI va bu
    o'lchangan: `A_VENDOR_PHONES[0]` egasi `HANDOVER_START` dan boshlanadigan
    davrga ega va o'sha davr KALENDAR BO'YICHA bugunni qamrashi ham,
    qamramasligi ham mumkin (`HANDOVER_DAY` kelgach u yangi sotuvchiga
    o'tadi). Ya'ni `stall_count` kutilmasi seed sotuvchisi bilan yozilsa
    test bir necha kunda sababsiz qizarardi — dastlabki yozuvda u aynan
    shunday `3 != 2` bilan yiqildi.
    """
    response = await client.post(
        VENDORS_URL,
        json={"full_name": "Toza Sotuvchi", "phone": NEW_VENDOR_PHONE},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return UUID(response.json()["id"])


# ---------------------------------------------------------------------------
# D-09 — bir vaqtda 1 rasta = 1 sotuvchi (NAZORAT HOLATI birinchi turadi)
# ---------------------------------------------------------------------------


async def test_adjacent_assignment_is_accepted(
    api_client: httpx.AsyncClient,
    market_domain: MarketDomainSeed,
    market_today: date,
    admin_headers: dict[str, str],
) -> None:
    """NAZORAT HOLATI: QO'SHNI davrlar ikkalasi ham qabul qilinadi.

    Usiz keyingi test (`test_overlapping_assignment_returns_409`) endpoint
    HAR QANDAY ikkinchi davrni rad etadigan holatda ham yashil bo'lardi —
    409 baribir kelardi va "qoplanish bloklandi" degan xulosa yolg'on
    bo'lardi.

    `[)` chegarasi tufayli `[D, D+10)` va `[D+10, D+20)` KESISHMAYDI:
    `D+10` kuni faqat ikkinchi davrga tegishli (D-10).
    """
    rows = market_domain.market_a
    stall_id = _free_stalls(rows)[0]
    vendor_id = rows.vendor_ids[0]
    start = market_today
    middle = start + timedelta(days=SPAN_DAYS)
    end = middle + timedelta(days=SPAN_DAYS)

    first = await _assign(
        api_client,
        admin_headers,
        stall_id=stall_id,
        vendor_id=vendor_id,
        from_date=start,
        to_date=middle,
    )
    second = await _assign(
        api_client,
        admin_headers,
        stall_id=stall_id,
        vendor_id=rows.vendor_ids[1],
        from_date=middle,
        to_date=end,
    )

    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text

    history = await _history(api_client, admin_headers, stall_id)
    assert history.status_code == 200, history.text
    assert len(history.json()["items"]) == 2


async def test_overlapping_assignment_returns_409(
    api_client: httpx.AsyncClient,
    market_domain: MarketDomainSeed,
    market_today: date,
    admin_headers: dict[str, str],
) -> None:
    """Qoplanuvchi davr -> **409** `assignment_period_overlaps` (D-09, T-02-73).

    Qo'riqchi DB'da (`EXCLUDE USING gist`), bu yerda esa uning
    foydalanuvchi tushunadigan tarjimasi sinaladi. Javobda QAYSI davr
    bilan kesishgani YO'Q va bo'lishi ham mumkin emas: RLS ostida
    Postgres konstrayt xatosining `DETAIL` qatorini butunlay o'chiradi
    (Pitfall 4, T-02-75).
    """
    rows = market_domain.market_a
    stall_id = _free_stalls(rows)[0]
    start = market_today
    end = start + timedelta(days=SPAN_DAYS)

    first = await _assign(
        api_client,
        admin_headers,
        stall_id=stall_id,
        vendor_id=rows.vendor_ids[0],
        from_date=start,
        to_date=end,
    )
    assert first.status_code == 201, first.text

    response = await _assign(
        api_client,
        admin_headers,
        stall_id=stall_id,
        vendor_id=rows.vendor_ids[1],
        from_date=start + timedelta(days=SPAN_DAYS // 2),
        to_date=end + timedelta(days=SPAN_DAYS),
    )

    assert response.status_code == 409, response.text
    assert response.json()["detail"] == "assignment_period_overlaps"
    assert "duplicate key" not in response.text, "DB xatosining xom matni javobga sizdi"


async def test_two_stalls_can_share_one_vendor(
    api_client: httpx.AsyncClient,
    market_domain: MarketDomainSeed,
    market_today: date,
    admin_headers: dict[str, str],
) -> None:
    """D-09 ning IKKINCHI yarmi: 1 sotuvchi = KO'P rasta, bir vaqtda.

    `EXCLUDE` konstrayti `(market_id, stall_id, period)` bo'yicha, ya'ni
    u faqat BIR RASTADAGI qoplanishni bloklaydi. Agar u `vendor_id`
    bo'yicha ham yozilganda edi, bitta sotuvchining ikkinchi rastasi
    409 olardi va Karmanadagi eng ODATIY holat (bir savdogar ikki-uch
    rasta) API orqali umuman ifodalanmasdi.

    Sotuvchi TOZA yaratiladi — sabab `_new_vendor()` docstringida
    (seed sotuvchisining bugungi sanog'i kalendarga bog'liq).
    """
    rows = market_domain.market_a
    stalls = _free_stalls(rows)[:2]
    assert len(stalls) == 2, "seed kamida ikkita bo'sh rasta berishi kerak"
    vendor_id = await _new_vendor(api_client, admin_headers)

    for stall_id in stalls:
        response = await _assign(
            api_client,
            admin_headers,
            stall_id=stall_id,
            vendor_id=vendor_id,
            from_date=market_today,
        )
        assert response.status_code == 201, response.text

    vendor = await api_client.get(f"{VENDORS_URL}/{vendor_id}", headers=admin_headers)
    assert vendor.status_code == 200, vendor.text
    assert vendor.json()["stall_count"] == len(stalls)


# ---------------------------------------------------------------------------
# D-10 — almashinuv: davrni yopish va yangisini ochish
# ---------------------------------------------------------------------------


async def test_closing_an_open_period_fills_the_to_date(
    api_client: httpx.AsyncClient,
    market_domain: MarketDomainSeed,
    market_today: date,
    admin_headers: dict[str, str],
) -> None:
    """OCHIQ davrni yopish -> **200**, va `to_date` o'qish yo'lida ham to'ladi.

    Javob AYNAN o'qish yo'lidan quriladi, lekin bu ALOHIDA tekshiriladi:
    yozuv javobi bilan `GET` javobi jimgina ajralib ketsa, klient
    "yopildi" deb ko'rsatib turgan davr ro'yxatda ochiq bo'lib qolardi.
    """
    rows = market_domain.market_a
    stall_id = _free_stalls(rows)[0]
    start = market_today
    end = start + timedelta(days=SPAN_DAYS)

    created = await _assign(
        api_client,
        admin_headers,
        stall_id=stall_id,
        vendor_id=rows.vendor_ids[0],
        from_date=start,
    )
    assert created.status_code == 201, created.text
    assert created.json()["to_date"] is None, "`to_date` berilmadi — davr OCHIQ bo'lishi kerak"

    response = await _close(api_client, admin_headers, created.json()["id"], end)

    assert response.status_code == 200, response.text
    assert response.json()["to_date"] == end.isoformat()

    history = await _history(api_client, admin_headers, stall_id)
    assert history.status_code == 200, history.text
    assert history.json()["items"][0]["to_date"] == end.isoformat()


async def test_closing_a_closed_period_returns_409(
    api_client: httpx.AsyncClient,
    market_domain: MarketDomainSeed,
    market_today: date,
    admin_headers: dict[str, str],
) -> None:
    """YOPILGAN davrni qayta yopish -> **409** `assignment_not_open`.

    Yopilgan davr — o'tmish: uning kunlariga 6-faza allaqachon patta
    yozgan bo'lishi mumkin. Yuqori chegarani surish o'sha kunlarni
    JIMGINA boshqa sotuvchiga o'tkazardi (T-02-72), shuning uchun qayta
    ochish yo'li umuman yo'q.

    404 EMAS (`status != 404` alohida): davr MAVJUD va foydalanuvchi
    "topilmadi" xabarini ko'rsa uni qidirishga tushardi.
    """
    rows = market_domain.market_a
    stall_id = _free_stalls(rows)[0]
    start = market_today
    end = start + timedelta(days=SPAN_DAYS)

    created = await _assign(
        api_client,
        admin_headers,
        stall_id=stall_id,
        vendor_id=rows.vendor_ids[0],
        from_date=start,
        to_date=end,
    )
    assert created.status_code == 201, created.text

    response = await _close(
        api_client, admin_headers, created.json()["id"], end + timedelta(days=SPAN_DAYS)
    )

    assert response.status_code != 404, "davr MAVJUD — 404 foydalanuvchini chalg'itardi"
    assert response.status_code == 409, response.text
    assert response.json()["detail"] == "assignment_not_open"


async def test_handover_flow_moves_the_day_to_the_new_vendor(
    api_client: httpx.AsyncClient,
    two_markets: TwoMarketSeed,
    market_domain: MarketDomainSeed,
    market_scope: MarketScope,
    market_today: date,
    admin_headers: dict[str, str],
) -> None:
    """Almashinuv KUNI YANGI sotuvchiga tegishli (D-10) — ikki chaqiruvli oqim.

    Almashinuv kuni ATAYIN BUGUNGI kun qilib tanlangan: shundagina da'vo
    `GET /stalls/{id}` javobi orqali — ya'ni foydalanuvchi HAQIQATAN
    ko'radigan yuzada — o'lchanadi. Kelajakdagi sana bilan yozilsa
    `vendor_id` bugun hali eski sotuvchini ko'rsatib turardi va test
    hech nimani isbotlamasdi.

    UCHTA MUSTAQIL DA'VO tekshiriladi:
      1. rasta kartochkasi bugun YANGI sotuvchini ko'rsatadi;
      2. eski davr yopilgan va uning `to_date` i AYNAN almashinuv kuni;
      3. DB darajasida `period @> :almashinuv_kuni` AYNAN BITTA qator
         beradi va u yangi sotuvchiniki.

    Uchinchisi ikkinchisidan mustaqil: `[]` chegarasi ishlatilganda kun
    IKKALA davrga ham tushardi, ro'yxat esa baribir to'g'ri ko'rinardi va
    faqat 6-fazadagi patta ikki marta yozilganda ko'rinardi.
    """
    market_id = two_markets.market_a.id
    rows = market_domain.market_a
    stall_id = _free_stalls(rows)[0]
    old_vendor = rows.vendor_ids[0]
    new_vendor = rows.vendor_ids[1]
    handover_day = market_today

    opened = await _assign(
        api_client,
        admin_headers,
        stall_id=stall_id,
        vendor_id=old_vendor,
        from_date=handover_day - timedelta(days=PAST_DAYS),
    )
    assert opened.status_code == 201, opened.text

    closed = await _close(api_client, admin_headers, opened.json()["id"], handover_day)
    assert closed.status_code == 200, closed.text

    reopened = await _assign(
        api_client,
        admin_headers,
        stall_id=stall_id,
        vendor_id=new_vendor,
        from_date=handover_day,
    )
    assert reopened.status_code == 201, reopened.text

    card = await api_client.get(f"{STALLS_URL}/{stall_id}", headers=admin_headers)
    assert card.status_code == 200, card.text
    assert card.json()["vendor_id"] == str(new_vendor), (
        "almashinuv kuni ESKI sotuvchida qoldi — `[)` chegarasi buzilgan (D-10)"
    )

    history = await _history(api_client, admin_headers, stall_id)
    assert history.status_code == 200, history.text
    items = history.json()["items"]
    assert len(items) == 2
    assert items[0]["vendor_id"] == str(new_vendor), "eng yangi davr birinchi kelishi kerak"
    assert items[0]["to_date"] is None
    assert items[1]["vendor_id"] == str(old_vendor)
    assert items[1]["to_date"] == handover_day.isoformat()

    with market_scope(market_id) as conn:
        db_rows = conn.execute(
            "SELECT vendor_id FROM stall_assignments "
            "WHERE market_id = %s AND stall_id = %s AND period @> %s::date",
            (str(market_id), str(stall_id), handover_day),
        ).fetchall()

    assert len(db_rows) == 1, f"almashinuv kunida AYNAN bitta davr kutilgan edi: {db_rows}"
    assert db_rows[0][0] == new_vendor


async def test_assignment_change_is_audited(
    api_client: httpx.AsyncClient,
    two_markets: TwoMarketSeed,
    market_domain: MarketDomainSeed,
    market_scope: MarketScope,
    market_today: date,
    admin_headers: dict[str, str],
) -> None:
    """Davrni yopish `audit_log` da `old -> new` farqi bilan ko'rinadi (T-02-72).

    YOZUVNI DB TRIGGERI QILADI (`stall_assignments` — `AUDITED_TABLES` da),
    ya'ni router `write_app_audit()` chaqirmaydi. Bu test ayni paytda
    o'sha qarorni ham tekshiradi: ilova ham yozganda AYNAN o'sha `row_id`
    uchun IKKITA `update` qatori paydo bo'lardi.

    `changed_keys` da `period` bo'lishi MAJBURIY: aynan shu kalit "qarz
    egaligi surildi" savoliga javob beradi.
    """
    market_id = two_markets.market_a.id
    rows = market_domain.market_a
    stall_id = _free_stalls(rows)[0]

    created = await _assign(
        api_client,
        admin_headers,
        stall_id=stall_id,
        vendor_id=rows.vendor_ids[0],
        from_date=market_today,
    )
    assert created.status_code == 201, created.text
    assignment_id = created.json()["id"]

    closed = await _close(
        api_client, admin_headers, assignment_id, market_today + timedelta(days=SPAN_DAYS)
    )
    assert closed.status_code == 200, closed.text

    with market_scope(market_id) as conn:
        audit = conn.execute(
            "SELECT action, source, changed_keys, old_value->>'period', new_value->>'period' "
            "FROM audit_log WHERE market_id = %s AND table_name = 'stall_assignments' "
            "AND row_id = %s AND action = 'update' ORDER BY id",
            (str(market_id), assignment_id),
        ).fetchall()

    assert len(audit) == 1, f"aynan bitta `update` qatori kutilgan edi (ikki marta yozuv?): {audit}"
    assert audit[0][1] == "db_trigger", "yozuvni ilova emas, DB triggeri qilishi kerak"
    assert "period" in audit[0][2]
    assert audit[0][3] != audit[0][4], "`old` va `new` bir xil — farq yozilmagan"


# ---------------------------------------------------------------------------
# D-11 — sotuvchisiz rasta XATO EMAS
# ---------------------------------------------------------------------------


async def test_stall_without_assignments_returns_an_empty_list(
    api_client: httpx.AsyncClient,
    market_domain: MarketDomainSeed,
    admin_headers: dict[str, str],
) -> None:
    """Hech qachon biriktirilmagan rasta -> **200** va bo'sh `items` (D-11).

    404 EMAS: rasta MAVJUD, faqat sotuvchisi yo'q. 404 qaytarilsa UI
    "bunday rasta yo'q" deb ko'rsatardi va "noma'lum sotuvchi" texnik
    hisobini yaratish vasvasasi tug'ilardi — D-11 aynan shuni taqiqlaydi.
    """
    stall_id = market_domain.market_a.unassigned_stall_id
    assert stall_id is not None, "seed `unassigned_stall_id` ni to'ldirmagan"

    response = await _history(api_client, admin_headers, stall_id)

    assert response.status_code == 200, response.text
    assert response.json()["items"] == []


async def test_vacancy_gap_returns_no_vendor(
    api_client: httpx.AsyncClient,
    market_domain: MarketDomainSeed,
    market_today: date,
    admin_headers: dict[str, str],
) -> None:
    """Davrlar orasidagi BO'SHLIQ kunida rasta sotuvchisiz (D-11).

    Bu "tarix yo'q" holatidan FARQ QILADI va farq alohida tekshiriladi:
    biriktirish TARIXI bo'sh emas (bitta yopilgan davr bor), lekin BUGUN
    hech kim biriktirilmagan. 6-faza aynan shu holatni "band, lekin
    sotuvchisiz" anomaliyasi sifatida topadi — ya'ni `vendor_id: null`
    bu yerda xato emas, MAHSULOT SIGNALI.
    """
    rows = market_domain.market_a
    stall_id = _free_stalls(rows)[0]

    closed = await _assign(
        api_client,
        admin_headers,
        stall_id=stall_id,
        vendor_id=rows.vendor_ids[0],
        from_date=market_today - timedelta(days=PAST_DAYS),
        to_date=market_today - timedelta(days=PAST_DAYS // 2),
    )
    assert closed.status_code == 201, closed.text

    card = await api_client.get(f"{STALLS_URL}/{stall_id}", headers=admin_headers)
    history = await _history(api_client, admin_headers, stall_id)

    assert card.status_code == 200, card.text
    assert card.json()["vendor_id"] is None, "bo'shliq kunida sotuvchi ko'rinmasligi kerak"
    assert history.status_code == 200, history.text
    assert len(history.json()["items"]) == 1, "tarix esa BO'SH EMAS — bu ikki xil holat"


# ---------------------------------------------------------------------------
# Shakl, tenant izolyatsiyasi va huquqlar
# ---------------------------------------------------------------------------


async def test_invalid_period_returns_422(
    api_client: httpx.AsyncClient,
    market_domain: MarketDomainSeed,
    market_today: date,
    admin_headers: dict[str, str],
) -> None:
    """`to_date <= from_date` — IKKALA yo'lda ham **422** `invalid_period`.

    `[a, a)` Postgres uchun BO'SH davr va bo'sh davr `&&` bilan hech nima
    bilan kesishmaydi — ya'ni `EXCLUDE` konstrayti uni TO'XTATMAYDI va
    rastada jimgina "sotuvchisi bor, lekin hech qaysi kunda emas" qatori
    paydo bo'lardi (`sbozor_core.periods.assignment_period()` docstringi).

    Yopish yo'li ALOHIDA tekshiriladi: u sanani so'rov tanasidan emas,
    MAVJUD davrning quyi chegarasidan oladi, ya'ni bu boshqa kod yo'li.
    """
    rows = market_domain.market_a
    stall_id = _free_stalls(rows)[0]
    vendor_id = rows.vendor_ids[0]

    empty = await _assign(
        api_client,
        admin_headers,
        stall_id=stall_id,
        vendor_id=vendor_id,
        from_date=market_today,
        to_date=market_today,
    )
    assert empty.status_code == 422, empty.text
    assert empty.json()["detail"] == "invalid_period"

    created = await _assign(
        api_client,
        admin_headers,
        stall_id=stall_id,
        vendor_id=vendor_id,
        from_date=market_today,
    )
    assert created.status_code == 201, created.text

    backwards = await _close(
        api_client, admin_headers, created.json()["id"], market_today - timedelta(days=1)
    )

    assert backwards.status_code == 422, backwards.text
    assert backwards.json()["detail"] == "invalid_period"


async def test_cross_tenant_stall_or_vendor_returns_404(
    api_client: httpx.AsyncClient,
    market_domain: MarketDomainSeed,
    market_today: date,
    admin_headers: dict[str, str],
) -> None:
    """Begona bozorning rastasi yoki sotuvchisi -> **404**, va aynan 403 EMAS.

    UCHALA yo'l ham tekshiriladi (yozuvda ikkita havola, o'qishda yo'l
    parametri), chunki ular UCH XIL mexanizmga tayanadi: composite FK
    (`23503`), yana o'sha FK va `stall_exists()` ilova darvozasi.
    Faqat bittasini sinash qolgan ikkitasini ochiq qoldirardi —
    ayniqsa o'qish yo'lini, u RLS tufayli bo'sh 200 qaytarardi va
    strukturaviy jihatdan to'g'ri ko'rinardi.

    `status != 403` ALOHIDA assert qilinadi: 403 obyekt MAVJUDLIGINI
    tasdiqlardi (T-02-74).
    """
    a_rows = market_domain.market_a
    b_rows = market_domain.market_b
    own_stall = _free_stalls(a_rows)[0]

    foreign_stall = await _assign(
        api_client,
        admin_headers,
        stall_id=b_rows.stall_ids[0],
        vendor_id=a_rows.vendor_ids[0],
        from_date=market_today,
    )
    foreign_vendor = await _assign(
        api_client,
        admin_headers,
        stall_id=own_stall,
        vendor_id=b_rows.vendor_ids[0],
        from_date=market_today,
    )
    foreign_history = await _history(api_client, admin_headers, b_rows.stall_ids[0])

    for label, response in (
        ("begona rasta", foreign_stall),
        ("begona sotuvchi", foreign_vendor),
        ("begona rasta tarixi", foreign_history),
    ):
        assert response.status_code != 403, f"{label}: 403 obyekt MAVJUDLIGINI tasdiqlaydi"
        assert response.status_code == 404, f"{label}: {response.text}"
        assert response.json()["detail"] == "not_found", label


async def test_director_cannot_manage_assignments(
    api_client: httpx.AsyncClient,
    market_domain: MarketDomainSeed,
    market_today: date,
    director_headers: dict[str, str],
) -> None:
    """Direktor biriktirishni KO'RADI, lekin o'zgartira OLMAYDI (D-07, T-02-76).

    NAZORAT HOLATI (`GET` -> 200) MAJBURIY: usiz test direktorning
    sessiyasi umuman ishlamayotgan holatda ham yashil bo'lardi va D-07
    ning aynan mazmuni — "faqat yozish taqiqlangan" — sinovsiz qolardi.

    Biriktirishni surish 6-fazadagi qarz egaligini boshqa odamga
    o'tkazadi, ya'ni bu huquq nizoni HAL QILADIGAN roldan ATAYIN
    olib tashlangan.
    """
    rows = market_domain.market_a
    stall_id = _free_stalls(rows)[0]

    allowed = await _history(api_client, director_headers, stall_id)
    assert allowed.status_code == 200, allowed.text

    forbidden = await _assign(
        api_client,
        director_headers,
        stall_id=stall_id,
        vendor_id=rows.vendor_ids[0],
        from_date=market_today,
    )

    assert forbidden.status_code == 403, forbidden.text
    assert forbidden.json()["detail"] == "forbidden"
