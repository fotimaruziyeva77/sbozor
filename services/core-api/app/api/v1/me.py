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

from fastapi import APIRouter, HTTPException, status
from sbozor_core.enums import AuditAction

from app.deps import AuthSessionDep, CurrentPasswordDep, PrincipalDep
from app.repositories import user_repo
from app.schemas import LocaleResponse, ProfileResponse, UpdateProfileRequest
from app.security.audit import TABLE_USERS, write_app_audit

router = APIRouter(tags=["me"])

_USER_NOT_FOUND = "not_found"


def _not_found() -> HTTPException:
    """Profil topilmadi — token yaroqli, lekin foydalanuvchi o'chirilgan."""
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_USER_NOT_FOUND)


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
