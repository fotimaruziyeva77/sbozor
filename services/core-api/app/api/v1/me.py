"""Profil va til tanlovi (D-13, FOUND-04).

=============================================================================
TIL — DB'DA, COOKIE'DA EMAS. Bitta haqiqat manbai (D-13).

Cookie ham bor, lekin uning vazifasi boshqa: u frontend'ga birinchi
so'rovdayoq to'g'ri prefiksni tanlash imkonini beradi (`localeDetection:
false` bilan `next-intl` brauzer sarlavhasiga qaramaydi). Cookie —
KESH, profil esa MANBA. Ziddiyat chiqqanda profil g'olib: foydalanuvchi
boshqa qurilmadan kirsa ham o'z tilini oladi.

Shuning uchun bu endpoint cookie QO'YMAYDI — uni frontend javob asosida
o'zi qo'yadi. Server cookie qo'yganda ikkita joyda til holati paydo
bo'lardi va ular jimgina ajralib ketardi.
=============================================================================

`GET /api/v1/me` va `GET /api/v1/auth/me` — IKKI XIL narsa:

| Endpoint        | Nima qaytaradi                | Bozor konteksti     |
| --------------- | ----------------------------- | ------------------- |
| `/auth/me`      | SESSIYA: bozor nomi, huquqlar | MAJBURIY (409 aks)  |
| `/me`           | PROFIL: telefon, ism, til     | ixtiyoriy (`null`)  |

Platforma admini bozor tanlashdan oldin ham o'z profilini ko'rishi kerak,
aks holda til almashtirgich bozor tanlangunicha ishlamas edi.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

import structlog
from fastapi import APIRouter, HTTPException, status
from sbozor_core.enums import AuditAction
from sbozor_core.timeutil import business_today

from app.deps import AuthSessionDep, CurrentPasswordDep, PrincipalDep, TenantSessionDep
from app.repositories import headline_repo, user_repo
from app.schemas import HeadlineResponse, LocaleResponse, ProfileResponse, UpdateProfileRequest
from app.security.audit import TABLE_USERS, write_app_audit
from app.security.rbac import Permission

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.deps import Principal

log = structlog.get_logger(__name__)

router = APIRouter(tags=["me"])

_USER_NOT_FOUND = "not_found"
_HEADLINE_UNAVAILABLE = "headline_unavailable"
_MARKET_NOT_SELECTED = "market_not_selected"

HEADLINE_ORDER: Final[tuple[tuple[Permission, str], ...]] = (
    (Permission.REPORT_VIEW, "headline.revenue_today"),
    (Permission.OCCUPANCY_REVIEW, "headline.review_queue"),
    (Permission.PAYMENT_CREATE, "headline.receipts_written"),
)
"""⛔ TARTIB DETERMINLASHGAN VA U ROL NOMIGA TAYANMAYDI (D-28).

=============================================================================
⛔⛔ «ROL -> KO'RSATKICH» XARITASI ATAYIN YOZILMAGAN.

Foydalanuvchi bir necha rolga ega bo'lishi MUMKIN va bu Karmanada
istisno emas, ODATIY hol (D-05: kichik bozorda bir odam ham bozor
admini, ham kassir). Rol nomiga tayangan xarita bunday foydalanuvchida
IKKI javob berardi va ulardan qaysi biri qaytishi `frozenset` ning
iteratsiya tartibiga — ya'ni TASODIFGA — bog'liq bo'lardi. Foydalanuvchi
sahifani yangilaganda boshqa raqam ko'rishi mumkin edi va u buni
tizimning xatosi deb o'qirdi.

Shuning uchun tanlov HUQUQ bo'yicha va BIRINCHI MOS yozuv g'olib.
Tartib SHU YERDA, bitta joyda yozilgan — uni o'zgartirish ONGLI qaror
bo'ladi va u kod ko'rigidan o'tadi.

⚠ `market_admin` `REPORT_VIEW` ORQALI DIREKTORNIKIGA TUSHADI va bu ONGLI
  qaror (A6), unutish EMAS: unda o'sha huquq bor va bozor tushumi u
  uchun ham TO'G'RI bosh ko'rsatkich.

⛔ `platform_admin` ESA **403** OLADI — VA BU O'LCHANGAN FAKT, TAXMIN
   EMAS. 07-03 rejasining A6 bandi uni `market_admin` bilan bir qatorga
   qo'ygan edi; D-07 matritsasi esa boshqa narsani aytadi (o'lchandi
   2026-08-12): `ROLE_PERMISSIONS[Role.PLATFORM_ADMIN]` da `REPORT_VIEW`
   ham, `OCCUPANCY_REVIEW` ham, `PAYMENT_CREATE` ham ⛔ **YO'Q**.

   Xulq TO'G'RI va matritsa TEGILMAYDI: platforma admini bozorni
   SOZLAYDI (usta, NVR, foydalanuvchilar), uni KUNDALIK BOSHQARMAYDI —
   ya'ni «bugungi tushum» uning ekranining javobi emas. UI bunday
   javobda kartani UMUMAN chizmaydi (UI-SPEC §10.2), ya'ni u bo'sh joy
   ko'radi, xato emas. Unga son kerak bo'lsa — bu kortejga yozuv
   qo'shiladi (masalan `MARKET_VIEW_ALL` -> bozorlar soni) va o'sha payt
   tartib savoli qaytadan beriladi.

⚠ NAZORATCHI KASSIRDAN OLDIN TURADI, chunki ikkala huquq bir odamda
  UCHRAMAYDI (D-07 matritsasi) — ya'ni ular orasidagi tartib bugun
  ahamiyatsiz. U baribir QAT'IY yozilgan: matritsa kengaysa javob
  jimgina o'zgarmasligi kerak.
=============================================================================
"""


def _not_found() -> HTTPException:
    """Profil topilmadi — token yaroqli, lekin foydalanuvchi o'chirilgan."""
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_USER_NOT_FOUND)


def _market_id(principal: Principal) -> UUID:
    """Tanlangan bozor (`reviews.py` / `zones.py` dagi jufti bilan bir xil).

    `TenantSessionDep` bu shartni ALLAQACHON tekshiradi va 409 beradi;
    bu yerdagi tekshiruv TIP uchun (`UUID | None` -> `UUID`) va u
    ikkinchi darvoza sifatida ham zarar qilmaydi.
    """
    if principal.market_id is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=_MARKET_NOT_SELECTED,
        )
    return principal.market_id


@router.get("", response_model=ProfileResponse)
async def read_profile(principal: PrincipalDep, session: AuthSessionDep) -> ProfileResponse:
    """Joriy foydalanuvchi profili.

    `roles` va `market_id` TOKENDAN olinadi (ular sessiya konteksti),
    qolgan maydonlar esa DB'dan (`auth_list_users`) — ya'ni til
    o'zgartirilgandan keyin javob DARHOL yangi qiymatni ko'rsatadi va
    15 daqiqalik access token muddatini kutmaydi.
    """
    profiles = await user_repo.list_profiles(session, [principal.user_id])
    if not profiles:
        raise _not_found()
    profile = profiles[0]

    return ProfileResponse(
        id=profile.user_id,
        phone=profile.phone,
        full_name=profile.full_name,
        locale=profile.locale,
        roles=sorted(principal.roles),
        market_id=principal.market_id,
        is_platform_admin=profile.is_platform_admin,
        must_change_password=profile.must_change_password,
    )


@router.patch("", response_model=LocaleResponse)
async def update_profile(
    payload: UpdateProfileRequest,
    principal: CurrentPasswordDep,
    session: AuthSessionDep,
) -> LocaleResponse:
    """Til tanlovini profilda saqlaydi (D-13).

    `CurrentPasswordDep`, `PrincipalDep` EMAS (1-faza ko'rigi, WR-02): bu
    endpoint YOZADI (`users.locale`) va qurbon nomidan `update` audit
    qatorini chiqaradi. `read_profile` (yuqorida) darvozadan ATAYIN
    tashqarida qoladi — parol almashtirish ekrani foydalanuvchining tilini
    bilishi kerak, aks holda u o'zi tushunmaydigan tilda qulflanib qolardi.

    UI buzilmaydi: `locale-switcher.tsx` interfeys tilini DARHOL o'zgartiradi
    va yozuv xatosini jimgina yutadi (u yerda hujjatlashtirilgan) — ya'ni
    vaqtinchalik parolli foydalanuvchi ham tilni almashtira oladi, tanlov
    faqat parol almashtirilgandan keyin profilga saqlanadi.

    Yozuv `auth_set_locale` `SECURITY DEFINER` funksiyasi orqali ketadi
    (`app/repositories/user_repo.py`): `users` jadvali app-rolga butunlay
    yopiq, ya'ni oddiy `UPDATE users SET locale = ...` `permission denied`
    bilan yiqilardi.

    Audit yozuvi ESKI qiymatni ham oladi: "kim tilni o'zgartirdi" emas,
    "nimadan nimaga" savoliga javob beradigan yozuv kerak — D-12 ning
    ko'rish UI'si aynan shu juftlikni ko'rsatadi.

    Eski qiymat yozuvdan OLDIN o'qiladi: keyin o'qilsa u yangi qiymat
    bo'lib qolardi va jurnal "ru -> ru" degan ma'nosiz qator olardi.
    """
    profiles = await user_repo.list_profiles(session, [principal.user_id])
    if not profiles:
        raise _not_found()
    previous = profiles[0].locale
    updated = str(payload.locale)

    if not await user_repo.set_locale(session, principal.user_id, updated):
        raise _not_found()

    await write_app_audit(
        session,
        action=AuditAction.UPDATE,
        table_name=TABLE_USERS,
        row_id=principal.user_id,
        principal=principal,
        old={"locale": previous},
        new={"locale": updated},
    )
    await session.commit()

    return LocaleResponse(locale=updated)


@router.get("/headline", response_model=HeadlineResponse)
async def read_headline(
    principal: PrincipalDep,
    session: TenantSessionDep,
) -> HeadlineResponse:
    """Bosh ekranning YAGONA asosiy raqami (RECON-06, D-28/D-29).

    =======================================================================
    ⛔⛔ UCH ROL UCHUN UCH MARSHRUT YO'Q — VA BU QARORNING O'ZAGI.

    `/me/headline/director`, `/me/headline/cashier` shakli klientni
    «men kim ekanman?» degan savolga javob berishga majburlardi, ya'ni
    rol mantig'i SERVERDA ham, KLIENTDA ham yashardi. Ikki nusxa
    ajralganda ekranda kassirning soni direktorning yorlig'i bilan
    chizilardi va HECH BIR test buni ko'rmasdi — ikkalasi ham «to'g'ri»
    javob berardi.

    Bitta marshrut + serverdagi tanlov: klient `metric` kalitini oladi va
    uni tarjima qiladi. Boshqa hech nima bilmaydi.
    =======================================================================

    ⛔ **O'QISH AUDITI TALAB QILINMAYDI — VA BU UNUTISH EMAS, QAROR.**
       D-09 shaxsiy ma'lumot O'QILISHINI auditga majburlaydi; bu javobda
       esa shaxsiy maydon (`vendor_name` / `phone` / `full_name`) UMUMAN
       yo'q — faqat bitta son va bitta kalit. Ya'ni `PERSONAL_ROUTES`
       o'smaydi (D-05/G7-6) va jurnalga har bosh sahifa ochilishida qator
       yozish uni SHOVQIN bilan to'ldirardi (`GET /stalls/map` uchun
       aynan shu sabab bilan qabul qilingan qaror —
       `test_personal_data_coverage.py::MAP_ROUTE`).

    ⛔ **BIRORTA HUQUQ MOS KELMASA — 403, «bo'sh javob» EMAS.** 204 yoki
       `value: 0` qaytarish yo'li ATAYIN rad etildi: nol klientda
       O'LCHANGAN QIYMAT bo'lib ko'rinardi («bugun tushum yo'q»),
       holbuki haqiqat boshqa — «bu foydalanuvchi uchun ko'rsatkich
       YO'Q». Bu 05-14 ning «o'lchanmagan sonning o'rniga NOL
       yozilmaydi» darsi va D-20 ning aynan mantig'i: asbobning
       YO'QLIGI nol natija bilan bir xil ko'rinmasligi kerak.
       Klient 403 da kartani UMUMAN chizmaydi (UI-SPEC §10.2).

    ⛔ **`require_permission(...)` DARVOZASI YO'Q va bu ATAYIN.** Bu
       marshrut BITTA huquq talab qilmaydi — u huquqlar TO'PLAMIGA
       qarab TANLAYDI. Dekoratorga darvoza qo'yish uchala ko'rsatkichdan
       birini «asosiy» qilib belgilashni talab qilardi va qolgan ikki
       rol 403 olardi.

    ⛔ **KUN SERVERDA (`business_today()`), SO'ROVDAN EMAS.** `?day=`
       parametri qabul qilinmaydi: u bo'lganda kassir boshqa kunni
       so'rab, o'z ko'rsatkichini tarixiy ma'lumotga aylantirardi va
       (muhimrog'i) direktorning kunlik tushumi klient tanlagan oynaga
       bo'ysunardi. FastAPI e'lon qilinmagan query parametrini JIMGINA
       e'tiborsiz qoldiradi, ya'ni `?day=2026-01-01` parametrsiz chaqiruv
       bilan AYNAN bir xil javob beradi — testda shu o'lchanadi.

    Raises:
        HTTPException: 409 — bozor tanlanmagan (`TenantSessionDep`);
            403 — foydalanuvchida uchala huquqdan birortasi ham yo'q.
    """
    market_id = _market_id(principal)
    # `principal.permissions` — `permissions_for(principal.roles)` ning
    # O'ZI (`deps.Principal.permissions`), ya'ni ROLLAR BIRLASHMASI (D-05).
    granted = principal.permissions

    for permission, metric in HEADLINE_ORDER:
        if permission not in granted:
            continue
        value = await _headline_value(session, permission, market_id=market_id, principal=principal)
        return HeadlineResponse(metric=metric, value=value)

    log.info("headline_unavailable", roles=sorted(principal.roles))
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=_HEADLINE_UNAVAILABLE)


async def _headline_value(
    session: AsyncSession,
    permission: Permission,
    *,
    market_id: UUID,
    principal: Principal,
) -> int:
    """Tanlangan ko'rsatkich uchun `headline_repo` ning BITTA funksiyasi.

    =======================================================================
    ⛔⛔ TARMOQLANISH `Permission` BO'YICHA, i18n KALITI BO'YICHA EMAS —
        VA BU FARQ JIDDIY.

    Kalit satri bo'yicha tarmoqlanish IKKINCHI HAQIQAT MANBAI yaratardi:
    `HEADLINE_ORDER` dagi kalit qayta nomlanganda (masalan
    `headline.revenue_today` -> `headline.today_revenue`) bu yerdagi
    solishtiruv mos kelmay qolardi va boshqaruv OXIRGI shoxga —
    kassirnikiga — tushib ketardi. Natijada direktor `cashier_id` si
    O'ZINIKI bo'lgan KVITANSIYA SANOG'INI olardi va javob 200 bo'lardi:
    xato JIMGINA, faqat noto'g'ri raqam sifatida ko'rinardi.

    `Permission` — enum a'zosi, ya'ni uni qayta nomlash butun kod
    bo'ylab kompilyatsiya darajasida ko'rinadi.

    ⛔ OXIRGI SHOX — `raise`, «standart qiymat» EMAS. `HEADLINE_ORDER` ga
       to'rtinchi yozuv qo'shilib bu funksiya yangilanmasa, marshrut
       BALAND ovozda yiqiladi (500), jimgina noto'g'ri son qaytarmaydi.
       Bu holat CI'ga umuman yetib bormaydi:
       `test_every_headline_order_entry_has_a_resolver` yopiqlikni
       o'lchaydi.
    =======================================================================

    ⚠ Xarita (`dict[Permission, Callable]`) EMAS: uchala funksiyaning
      imzosi HAR XIL (`cashier_id` faqat bittasida, `business_date`
      ikkitasida) va ularni bitta `Callable` tipiga keltirish sun'iy
      `**kwargs` qobig'ini talab qilardi. Qobiq esa aynan shu farqni —
      kassirning so'rovi O'Z identifikatoriga qadalganini — yashirardi.

    ⛔ `cashier_id=principal.user_id`: kassir FAQAT o'z kunini ko'radi.
    """
    if permission is Permission.REPORT_VIEW:
        return await headline_repo.revenue_today_soum(
            session, market_id=market_id, business_date=business_today()
        )
    if permission is Permission.OCCUPANCY_REVIEW:
        return await headline_repo.review_queue_count(session, market_id=market_id)
    if permission is Permission.PAYMENT_CREATE:
        return await headline_repo.receipts_written_count(
            session,
            market_id=market_id,
            business_date=business_today(),
            cashier_id=principal.user_id,
        )
    raise RuntimeError(
        f"`HEADLINE_ORDER` da {permission!r} bor, lekin `_headline_value()` uni "
        "hal qilmaydi — yangi yozuvga MOS KELUVCHI shox qo'shilmagan"
    )
