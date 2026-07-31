"""Rol-huquq matritsasi — KODDA QAT'IY (D-07).

=============================================================================
BU MATRITSA DB'GA KO'CHIRILMAYDI. Sozlanadigan permission tizimi (huquqlarni
bozor kesimida o'zgartirish) — Deferred Ideas'dagi v2 nomzodi. MVP'da u
ataylab kodda: matritsa o'zgarishi kod review'dan va `tests/unit/
test_rbac_matrix.py` darvozasidan o'tadi, ya'ni "direktorga tarif
o'zgartirishni ham beraylik" so'rovi jimgina UI sozlamasi bo'lib o'tib
ketmaydi.

`USER_MANAGE` — "foydalanuvchi boshqarish" huquqi, "ISTALGAN ROLNI BERISH"
huquqi EMAS. D-04 bo'yicha kim qaysi rolni yarata olishi (rol berish
DARAJASI: platforma admini -> bozor admini/direktor, bozor admini ->
kassir/nazoratchi) `POST /users` endpointining SERVIS MANTIQIDA
tekshiriladi (01-07 Task 1) — matritsaga yangi permission qo'shilmaydi.
Aks holda har bir rol-juftligi uchun alohida huquq kerak bo'lardi va
matritsa o'qib bo'lmas holga kelardi.
=============================================================================

JUFTINI YANGILASHNI UNUTMANG: bu matritsaning UI ko'zgusi
`frontend/src/lib/rbac.ts` da yashaydi va u QO'LDA sinxron saqlanadi (til
chegarasi tufayli avtomatik tekshiruv yo'q). Bu yerga yangi `Permission`
qo'shsangiz yoki rol qatorini o'zgartirsangiz — o'sha faylda AYNAN bir xil
o'zgarishni bajaring. Ko'zgu xavfsizlik chegarasi EMAS (haqiqiy qaror
`require_permission(...)` da), ya'ni uni unutish ma'lumot ochmaydi — lekin
tugma ko'rinib turib 403 beradigan (yoki huquq bor bo'la turib menyu
yo'qoladigan) chalkash UI hosil qiladi.

Qamrov: bu yerdagi ba'zi huquqlar hali hech qayerda tekshirilmaydi
(`PAYMENT_CREATE`, `OCCUPANCY_REVIEW`, `DISPUTE_DECIDE` — 5- va 6-fazalar).
Ular ATAYIN hozirdan bor: D-07 ning mazmuni — "direktor NIMA QILA
OLMAYDI" — aynan shu huquqlarning yo'qligi bilan ifodalanadi. Ularsiz D-07
ni test bilan qulflab bo'lmasdi.
"""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING

from sbozor_core.enums import Role

if TYPE_CHECKING:
    from collections.abc import Iterable

__all__ = ["ROLE_PERMISSIONS", "Permission", "permissions_for"]


class Permission(StrEnum):
    """Tekshiriladigan huquqlar. Endpoint `require_permission(...)` bilan qo'riqlanadi.

    `StrEnum` — qiymatlar log va audit yozuvlariga to'g'ridan-to'g'ri tushadi.
    """

    # --- Foydalanuvchilar va jurnal ---
    USER_MANAGE = "user_manage"
    USER_VIEW = "user_view"
    AUDIT_VIEW = "audit_view"

    # --- Bozor darajasi ---
    MARKET_VIEW_ALL = "market_view_all"
    MARKET_MANAGE = "market_manage"

    # --- Bozor ichidagi ma'lumot (2-faza) ---
    STALL_MANAGE = "stall_manage"
    TARIFF_MANAGE = "tariff_manage"
    VENDOR_MANAGE = "vendor_manage"
    # O'QISH huquqlari YOZISHdan ALOHIDA: D-07 ning butun mazmuni —
    # direktor reestrni KO'RADI, lekin o'zgartira olmaydi. Bitta
    # `*_MANAGE` huquqi ikkalasini ham qamrasa, "ko'rsin" so'rovi
    # "o'zgartirsin" ga aylanib ketardi.
    MARKET_DATA_VIEW = "market_data_view"
    """Zona / toifa / rasta / tarif / kalendar O'QISH.

    Shaxsiy ma'lumotni QAMRAMAYDI — sotuvchi uchun alohida `VENDOR_VIEW`.
    """
    VENDOR_VIEW = "vendor_view"
    """Sotuvchi (F.I.Sh., telefon — SHAXSIY MA'LUMOT) O'QISH.

    `MARKET_DATA_VIEW` dan ATAYIN ajratilgan: 1-faza D-09 bo'yicha shaxsiy
    ma'lumotning O'QILISHI ham auditda qayd etiladi, ya'ni bu huquq berilishi
    boshqa reestrlarni ko'rish bilan bir xil og'irlikda emas.
    """

    # --- Operatsiya (5- va 6-fazalar) ---
    PAYMENT_CREATE = "payment_create"
    REPORT_VIEW = "report_view"
    OCCUPANCY_REVIEW = "occupancy_review"
    DISPUTE_DECIDE = "dispute_decide"
    CAMERA_VIEW = "camera_view"


ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    # Platforma admini: bozorlararo yagona rol (D-06). `MARKET_VIEW_ALL` unga
    # RLS bypass BERMAYDI — u faqat bozor tanlash ekranini ochadi.
    #
    # `STALL_MANAGE`/`TARIFF_MANAGE`/`VENDOR_MANAGE` — 2-fazada QO'SHILDI va
    # ular MARKET-01 uchun MAJBURIY: "platforma admini yangi bozor ustasi
    # orqali bozorni kod yozmasdan kiritadi" talabi ustaning rasta, tarif va
    # sotuvchi qadamlarini o'z ichiga oladi. Ularsiz usta 3-qadamda 403 bilan
    # to'xtardi va sabab endpoint kodida KO'RINMASDI — kod to'g'ri ko'rinib,
    # matritsa jimgina rad etardi (Pitfall 6).
    Role.PLATFORM_ADMIN: frozenset(
        {
            Permission.MARKET_VIEW_ALL,
            Permission.MARKET_MANAGE,
            Permission.USER_MANAGE,
            Permission.USER_VIEW,
            Permission.AUDIT_VIEW,
            Permission.STALL_MANAGE,
            Permission.TARIFF_MANAGE,
            Permission.VENDOR_MANAGE,
            Permission.MARKET_DATA_VIEW,
            Permission.VENDOR_VIEW,
        }
    ),
    # D-07: FAQAT ko'rish + nizo qarori. `*_MANAGE` huquqlarining yo'qligi —
    # bu qatorning ASOSIY mazmuni, qo'shimchasi emas.
    #
    # 2-fazada qo'shilgan ikkita huquq ham FAQAT O'QISH: direktor rasta va
    # tarif reestrini ko'radi (hisobotlari shunsiz ma'nosiz), lekin birorta
    # `*_MANAGE` OLMAYDI. `test_director_is_read_only_on_market_data` shu
    # chegarani qulflaydi — matritsa kengayishi D-07 ni buzmasin.
    Role.DIRECTOR: frozenset(
        {
            Permission.REPORT_VIEW,
            Permission.AUDIT_VIEW,
            Permission.CAMERA_VIEW,
            Permission.DISPUTE_DECIDE,
            Permission.USER_VIEW,
            Permission.MARKET_DATA_VIEW,
            Permission.VENDOR_VIEW,
        }
    ),
    # Bozor admini o'z bozorining hamma narsasini boshqaradi, LEKIN boshqa
    # bozorlarni umuman ko'rmaydi (`MARKET_VIEW_ALL` yo'q).
    Role.MARKET_ADMIN: frozenset(
        {
            Permission.USER_MANAGE,
            Permission.USER_VIEW,
            Permission.AUDIT_VIEW,
            Permission.STALL_MANAGE,
            Permission.TARIFF_MANAGE,
            Permission.VENDOR_MANAGE,
            Permission.MARKET_DATA_VIEW,
            Permission.VENDOR_VIEW,
            Permission.REPORT_VIEW,
            Permission.CAMERA_VIEW,
        }
    ),
    # Kassir — eng tor yuza: u faqat to'lov qayd etadi. Summani tarif
    # belgilaydi (spec §4.7), ya'ni bu huquq "pul kiritish" emas,
    # "to'lovni qayd etish".
    Role.CASHIER: frozenset({Permission.PAYMENT_CREATE}),
    # Nazoratchi — HITL navbati. U to'lov ham kirita olmaydi, jurnal ham
    # ko'rmaydi: uning ishi faqat "band/bo'sh" qarorini tasdiqlash.
    Role.INSPECTOR: frozenset({Permission.OCCUPANCY_REVIEW}),
}
"""Rol -> huquqlar. HAR BIR `Role` a'zosi shu yerda bo'lishi SHART.

Unutish `tests/unit/test_rbac_matrix.py::test_every_role_has_entry` bilan
bloklanadi: aks holda yangi rol jimgina "huquqsiz" bo'lib qolardi va sabab
403 javobida ko'rinmasdi.
"""


def permissions_for(roles: Iterable[str]) -> frozenset[Permission]:
    """Rollar to'plamining huquqlar BIRLASHMASI (D-05).

    Karmana kabi kichik bozorda bir odam ham bozor admini, ham kassir
    bo'ladi — unda ikkala to'plam ham amal qiladi.

    Noma'lum rol nomi JIMGINA e'tiborsiz qoldiriladi (`KeyError` emas):
    access token 15 daqiqa amal qiladi, ya'ni rol o'zgartirilgandan keyin
    ham eski token bir muddat kelib turadi. To'g'ri xulq — o'sha roldan
    huquq bermaslik, butun so'rovni 500 bilan yiqitish emas.
    """
    granted: set[Permission] = set()
    for raw in roles:
        try:
            role = Role(raw)
        except ValueError:
            continue
        granted |= ROLE_PERMISSIONS.get(role, frozenset())
    return frozenset(granted)
