"""Rol-huquq matritsasi invariantlari (D-07, D-05, D-11, FOUND-01).

=============================================================================
NEGA BU TESTLAR BAZASIZ VA NEGA ULAR SHUNCHALIK QAT'IY:

Matritsa KODDA QAT'IY (D-07 — sozlanadigan permission tizimi Deferred
Ideas'da). Ya'ni uning yagona himoyasi — shu fayl. Bozor ma'muriyati
"direktorga tarif o'zgartirishni ham beraylik" deb so'raganda, kimdir
`ROLE_PERMISSIONS` ga bir satr qo'shishi mumkin va boshqa hech qanday test
buni ko'rmaydi: barcha endpointlar baribir ishlayveradi, faqat direktor
endi tarif o'zgartira oladi.

Shuning uchun bu yerdagi da'volar POZITIV emas, NEGATIV: "bu rolda BU
HUQUQ YO'Q". Negativ da'vo matritsani kengaytirish yo'lini yopadi.
=============================================================================
"""

from __future__ import annotations

import pytest
from app.security.rbac import ROLE_PERMISSIONS, Permission, permissions_for
from sbozor_core.enums import Role


def test_director_cannot_manage() -> None:
    """D-07: direktor — FAQAT ko'rish + nizo qarori.

    Rasta, tarif, sotuvchi va xodim boshqaruvi undan ATAYIN olib tashlangan.
    """
    director = ROLE_PERMISSIONS[Role.DIRECTOR]

    forbidden = {
        Permission.USER_MANAGE,
        Permission.STALL_MANAGE,
        Permission.TARIFF_MANAGE,
        Permission.VENDOR_MANAGE,
    }
    leaked = forbidden & director
    assert not leaked, (
        f"D-07 buzildi: direktorga boshqaruv huquqlari berilgan ({sorted(leaked)}). "
        "Direktor faqat ko'radi va nizo qarorini qabul qiladi."
    )

    # Nazorat holati: matritsa umuman bo'sh bo'lib qolgani uchun o'tmasin.
    assert Permission.REPORT_VIEW in director
    assert Permission.DISPUTE_DECIDE in director


def test_platform_admin_can_run_the_wizard() -> None:
    """MARKET-01: usta qadamlarining HAMMASI platforma admini uchun ochiq (Pitfall 6).

    Bu da'vo boshqa hech qayerda tekshirilmaydi va uning buzilishi JIMGINA
    sodir bo'ladi: endpoint kodi to'g'ri ko'rinadi, matritsa esa rad etadi.
    2-fazadan oldin `PLATFORM_ADMIN` da `STALL_MANAGE`/`TARIFF_MANAGE`/
    `VENDOR_MANAGE` YO'Q edi, ya'ni "bozorni kod yozmasdan kiritish" talabini
    bajaradigan odam ustaning 3-qadamida 403 bilan to'xtardi.

    `permissions_for()` orqali tekshiriladi, `ROLE_PERMISSIONS` dan
    to'g'ridan-to'g'ri emas: endpoint aynan shu funksiyaning natijasini
    ko'radi, ya'ni test rad etish YO'LINI sinaydi, lug'at ichidagi qiymatni
    emas.
    """
    granted = permissions_for(["platform_admin"])

    required = {
        Permission.MARKET_MANAGE,  # 1-qadam: rekvizitlar
        Permission.STALL_MANAGE,  # 3-qadam: zonalar va rastalar
        Permission.TARIFF_MANAGE,  # 4-qadam: toifalar va tariflar
        Permission.VENDOR_MANAGE,  # sotuvchi biriktirish
        Permission.MARKET_DATA_VIEW,  # har qadamda kiritilganini qayta ko'rish
    }
    missing = required - granted
    assert not missing, (
        f"MARKET-01 bajarilmaydi: platforma adminida {sorted(missing)} yo'q — "
        "usta shu qadamda 403 bilan to'xtaydi va sabab endpoint kodida ko'rinmaydi"
    )


def test_market_manage_is_platform_admin_only() -> None:
    """`MARKET_MANAGE` — FAQAT platforma adminida (D-06, T-02-79).

    =========================================================================
    BU DA'VO 02-11 DAN BOSHLAB YUK KO'TARADI — VA UNING BUZILISHI JIMGINA
    SODIR BO'LADI.

    Uchta endpoint aynan shu huquq ostida: `POST /markets`,
    `POST /markets/{id}/activate` va `DELETE /markets/{id}`. Ya'ni huquq
    bozor adminiga berilsa, u:

      * platformada YANGI BOZOR ocha oladi (`POST /markets` da ikkinchi
        darvoza — `require_platform_admin` — hamon ushlab turadi, lekin
        qolgan ikkitasida ikkinchi darvoza YO'Q);
      * o'z bozorini FAOLLASHTIRA oladi, ya'ni platforma nazoratisiz
        jonli holatga o'tkazadi;
      * qoralamani O'CHIRA oladi.

    Hech biri endpoint kodida ko'rinmasdi: `require_permission` satri
    o'zgarmagan bo'lardi. Yagona o'zgarish `ROLE_PERMISSIONS` dagi bitta
    satrda bo'lardi.

    Bundan tashqari bu da'vo `tests/tenancy/test_cross_tenant.py::
    PLATFORM_ADMIN_ROUTES` ning MAVJUD BO'LISH SABABI: o'sha marshrutlar
    matritsada kuchaytirilgan sessiya bilan chaqiriladi, chunki bozor
    adminining 403 i tenant darvozasini butunlay yashirardi. Huquq
    kengaysa, o'sha ro'yxat ham keraksiz bo'lib qoladi va
    `test_platform_admin_routes_really_need_the_elevated_session`
    darhol qizaradi.
    =========================================================================
    """
    holders = {
        role for role, granted in ROLE_PERMISSIONS.items() if Permission.MARKET_MANAGE in granted
    }

    assert holders == {Role.PLATFORM_ADMIN}, (
        f"`MARKET_MANAGE` quyidagi rollarda: {sorted(str(role) for role in holders)}. "
        "U FAQAT platforma adminida bo'lishi kerak — bozor yaratish, faollashtirish va "
        "qoralamani o'chirish bozorlararo amallar (D-06, T-02-79)."
    )


def test_director_is_read_only_on_market_data() -> None:
    """D-07: direktorga bozor ma'lumoti O'QISH uchun ochiq, YOZISH uchun yopiq.

    Matritsa 2-fazada kengaydi (`MARKET_DATA_VIEW`, `VENDOR_VIEW`) — aynan
    shunday kengayish paytida `*_MANAGE` ham "qo'shib yuborilishi" oson
    bo'ladi ("direktor baribir ko'ryapti-ku"). Bu test kengaytmaning
    CHEGARASINI qulflaydi: ikki tomon ham bir testda, ya'ni faqat pozitiv
    yarmini nusxalab qo'yish mumkin emas.
    """
    director = permissions_for(["director"])

    assert Permission.MARKET_DATA_VIEW in director, (
        "direktor rasta/tarif reestrini ko'ra olmaydi — hisobotlari ma'nosiz bo'ladi"
    )
    assert Permission.VENDOR_VIEW in director, "direktor sotuvchi reestrini ko'ra olmaydi"

    forbidden = {
        Permission.STALL_MANAGE,
        Permission.TARIFF_MANAGE,
        Permission.VENDOR_MANAGE,
    }
    leaked = forbidden & director
    assert not leaked, (
        f"D-07 buzildi: bozor ma'lumotini O'QISH huquqi bilan birga {sorted(leaked)} "
        "ham berilgan — direktor endi tarif/rasta o'zgartira oladi"
    )


def test_cashier_and_inspector_have_no_market_data_view() -> None:
    """A8: 2-fazada kassir ham, nazoratchi ham rasta/sotuvchi reestrini KO'RMAYDI.

    Ikkalasining yuzasi ataylab tor (`test_cashier_scope_minimal` va
    `test_inspector_scope_minimal` uni aynan qulflaydi), lekin bu test
    boshqa savolga javob beradi: matritsa kengayganda yangi O'QISH huquqi
    "hammaga zarari yo'q" degan mulohaza bilan pastga sirg'alib tushmasin.

    Bu chegara 5- va 6-fazalarda ATAYIN qayta ko'riladi (kassir rasta
    qidiradi, nazoratchi zona ko'radi) — o'shanda bu test qizaradi va
    o'zgarish ataylab qilingan harakat bo'ladi, jimgina sizib o'tish emas.
    """
    for role in ("cashier", "inspector"):
        granted = permissions_for([role])
        leaked = {Permission.MARKET_DATA_VIEW, Permission.VENDOR_VIEW} & granted
        assert not leaked, (
            f"A8 buzildi: `{role}` roliga {sorted(leaked)} berilgan — 2-fazada "
            "unga bozor reestri ochilmasligi kerak edi"
        )


def test_cashier_scope_minimal() -> None:
    """Kassirning huquqlari AYNAN bitta: to'lov qayd etish.

    Kassir — korrupsiya xavfi eng yuqori nuqta (spec §4.7: erkin summa
    kiritish taqiqlangan). Uning yuzasi kengaysa, u kengayganini shu test
    ko'rsatadi.
    """
    assert ROLE_PERMISSIONS[Role.CASHIER] == frozenset({Permission.PAYMENT_CREATE})


def test_inspector_scope_minimal() -> None:
    """Nazoratchi FAQAT bandlik tasdiqlash navbati bilan ishlaydi (HITL)."""
    assert ROLE_PERMISSIONS[Role.INSPECTOR] == frozenset({Permission.OCCUPANCY_REVIEW})


def test_only_platform_admin_sees_all_markets() -> None:
    """`MARKET_VIEW_ALL` — bozorlararo yagona huquq, faqat platforma adminida (D-06).

    Bu huquq RLS bypass BERMAYDI: u faqat bozor tanlash ekranini ochadi
    (`auth_list_markets()`), tanlangandan keyin `app.market_id` odatdagidek
    o'rnatiladi.
    """
    holders = {
        role for role, perms in ROLE_PERMISSIONS.items() if Permission.MARKET_VIEW_ALL in perms
    }
    assert holders == {Role.PLATFORM_ADMIN}


def test_audit_view_matches_d11() -> None:
    """D-11: audit jurnalini AYNAN uch rol ko'radi — har biri o'z bozorida."""
    holders = {role for role, perms in ROLE_PERMISSIONS.items() if Permission.AUDIT_VIEW in perms}
    assert holders == {Role.PLATFORM_ADMIN, Role.DIRECTOR, Role.MARKET_ADMIN}

    # Negativ tomoni alohida aytiladi: kassir va nazoratchi jurnalni KO'RMAYDI.
    assert Permission.AUDIT_VIEW not in ROLE_PERMISSIONS[Role.CASHIER]
    assert Permission.AUDIT_VIEW not in ROLE_PERMISSIONS[Role.INSPECTOR]


def test_role_union() -> None:
    """D-05: bir odam bir necha rolga ega bo'lsa huquqlar BIRLASHADI.

    Karmana kabi kichik bozorda bozor admini ayni paytda kassir ham bo'ladi —
    unda ikkala to'plam ham bo'lishi kerak, kesishmasi emas.
    """
    combined = permissions_for([Role.MARKET_ADMIN, Role.CASHIER])

    assert combined == ROLE_PERMISSIONS[Role.MARKET_ADMIN] | ROLE_PERMISSIONS[Role.CASHIER]
    assert Permission.PAYMENT_CREATE in combined
    assert Permission.TARIFF_MANAGE in combined
    # Birlashma ham chegarani buzmaydi: ikkalasida ham yo'q huquq paydo bo'lmaydi.
    assert Permission.MARKET_VIEW_ALL not in combined


def test_every_role_has_entry() -> None:
    """`Role` enum'ining HAR BIR a'zosi matritsada bor.

    Yangi rol qo'shilib matritsa unutilsa, `permissions_for()` uni jimgina
    "huquqsiz" deb hisoblardi — endpointlar 403 qaytarib, sabab esa
    ko'rinmas bo'lardi. Bu test o'sha unutishni CI'da ushlaydi.
    """
    assert set(ROLE_PERMISSIONS) == set(Role)


def test_permissions_are_immutable() -> None:
    """Matritsa qiymatlari `frozenset` — ish vaqtida kengaytirib bo'lmaydi.

    Oddiy `set` bo'lganda `ROLE_PERMISSIONS[Role.DIRECTOR].add(...)` ishlagan
    bo'lardi va huquq oshirish bitta satrga tushardi.
    """
    for role, perms in ROLE_PERMISSIONS.items():
        assert isinstance(perms, frozenset), f"{role}: qiymat `frozenset` emas"
        with pytest.raises(AttributeError):
            perms.add(Permission.USER_MANAGE)  # type: ignore[attr-defined]


def test_unknown_role_contributes_nothing() -> None:
    """Noma'lum rol nomi (eski tokendan kelgan) huquq bermaydi va yiqilmaydi.

    Access token 15 daqiqa amal qiladi, ya'ni rol o'chirilgandan keyin ham
    eski token bir muddat kelib turadi. To'g'ri xulq — o'sha rolni jimgina
    e'tiborsiz qoldirish, `KeyError` bilan 500 qaytarish emas.
    """
    assert permissions_for(["hech_qanday_rol"]) == frozenset()
    assert permissions_for(["cashier", "hech_qanday_rol"]) == frozenset({Permission.PAYMENT_CREATE})
