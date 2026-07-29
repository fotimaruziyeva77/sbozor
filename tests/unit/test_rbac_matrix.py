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
