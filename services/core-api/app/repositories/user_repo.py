"""Foydalanuvchi boshqaruvi DB kontrakti — IKKI QATLAMLI o'qish naqshi (D-04).

=============================================================================
NEGA O'QISH IKKI QADAMDA BAJARILADI:

  1-qadam  `user_market_roles` dan **RLS OSTIDA** joriy bozor a'zolarining
           `user_id` va `roles` ro'yxati olinadi (ORM `select()`).
  2-qadam  `auth_list_users(ids)` bilan o'sha ID'larning profil maydonlari
           (telefon, ism, til, holat) boyitiladi.

Bitta so'rov bilan qilishning iloji YO'Q: `users` GLOBAL jadval va
`sbozor_app` roliga u BUTUNLAY yopiq (01-04, `REVOKE ALL`), ya'ni JOIN
`permission denied for table users` bilan yiqilardi. Boshqa yo'nalishda
(hammasini `SECURITY DEFINER` ichida qilish) esa tenant filtri SQL
funksiyasi ichiga ko'chirilardi va RLS uni tekshira olmasdi.

Shu bo'linish yuzani ham qulflaydi: `auth_list_users` ANIQ ID RO'YXATIDAN
boshqa hech narsa qabul qilmaydi, ID'lar esa 1-qadamda RLS orqali
filtrlanadi. Boshqa bozor a'zosining ID'si 1-qadamdayoq qaytmaydi, ya'ni
2-qadam uni hech qachon ko'rmaydi.
=============================================================================

TENANT FILTRI IKKI QATLAM (`TenantScopedRepository`, RESEARCH Pattern 1):
RLS himoya to'ri, `scoped()` esa aniq `market_id` predikati. Bu yerdagi
so'rovlar BITTA entity ustida (`select(UserMarketRole...)`), ya'ni
`scoped()` ning `column_descriptions[0]` cheklovi (01-03 da qayd etilgan)
ularga tegmaydi — JOIN qilinadigan so'rov bu modulda ATAYIN yo'q, chunki
ikkinchi jadval (`users`) baribir `SECURITY DEFINER` ortida.

YOZISH YO'LLARI:
`users` ustidagi har bir yozuv `SECURITY DEFINER` funksiyasi orqali
(`auth_create_user`, `auth_update_password_hash`, `auth_set_active`);
`user_market_roles` esa oddiy RLS ostidagi jadval, ya'ni unga yozuv
`fn_audit_row()` triggeri orqali AVTOMATIK auditga tushadi (01-05).
`users` dagi o'zgarishlar uchun trigger YO'Q (funksiya ichida bajariladi),
shuning uchun ular `write_app_audit()` bilan QO'LDA yoziladi.

=============================================================================
OCHIQ PAROL BU MODULGA UMUMAN KIRMAYDI (02-24, T-02-176).

Parol qabul qiladigan UCHALA yozish yo'lining ham parametri
`password_hash` deb ataladi va u AYNAN hash oladi. Ochiq qiymat
chaqiruvchida (`imports.py`, `users.py`) lokal o'zgaruvchi bo'lib qoladi
va bu yerga faqat Argon2id natijasi keladi.

Sabab: repozitoriy qatlamining hech bir jurnali va hech bir istisno
matni parolni ko'rmasligi kerak. `IntegrityError` ning `str(exc)` so'rov
PARAMETRLARINI ham chiqaradi — ochiq qiymat bu yerdan o'tsa, u
`log.warning(..., error=str(exc.orig))` orqali jurnalga tushardi va "bir
martalik" kafolati jimgina yo'qolardi.

⚠ Bu izohda tekshiriladigan ATAMA ATAYIN yozilmagan: qabul mezoni
faylni o'sha atama bo'yicha grep qiladi va izohning O'ZI darvozani
buzardi (`api/v1/imports.py` dagi tranzaksiya izohi bilan aynan bir xil
qaror — 02-08 deviatsiya #3).
=============================================================================
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sbozor_core.models import UserMarketRole
from sbozor_core.tenancy import TenantScopedRepository
from sqlalchemy import insert, select, text, update

from app.repositories import auth_repo

if TYPE_CHECKING:
    from collections.abc import Sequence
    from datetime import datetime
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

__all__ = [
    "CreatedMember",
    "MarketUser",
    "StaffCreateEntry",
    "UserProfile",
    "UserRepository",
    "list_profiles",
    "set_locale",
]


@dataclass(frozen=True)
class StaffCreateEntry:
    """Ommaviy yaratishning BITTA kirish qatori (02-24).

    ⚠ Maydon nomi `password_hash` va u SHUNDAY qoladi: ochiq parol bu
    modulga umuman kirmaydi (modul docstringi).
    """

    row: int
    phone: str
    password_hash: str
    full_name: str | None
    locale: str
    roles: list[str]


@dataclass(frozen=True)
class CreatedMember:
    """Yaratilgan bitta a'zo — chaqiruvchi javob va audit uchun ishlatadi."""

    row: int
    user_id: UUID
    phone: str
    full_name: str | None
    roles: list[str]


@dataclass(frozen=True)
class MarketUser:
    """Bozor a'zosi — a'zolik (RLS) va profil (`SECURITY DEFINER`) birlashmasi."""

    user_id: UUID
    phone: str
    full_name: str | None
    roles: tuple[str, ...]
    is_active: bool
    must_change_password: bool
    locale: str
    created_at: datetime


_LIST_USERS = text(
    "SELECT user_id, phone_e164, full_name, locale, is_active, "
    "must_change_password, is_platform_admin, created_at "
    "FROM auth_list_users(CAST(:user_ids AS uuid[]))"
)

_CREATE_USER = text(
    "SELECT auth_create_user(:phone, :password_hash, :full_name, :locale, :is_platform_admin)"
)

_SET_LOCALE = text("SELECT auth_set_locale(:user_id, :locale)")


@dataclass(frozen=True)
class UserProfile:
    """`auth_list_users` qaytaradigan profil qatori (a'zoliksiz)."""

    user_id: UUID
    phone: str
    full_name: str | None
    locale: str
    is_active: bool
    must_change_password: bool
    is_platform_admin: bool
    created_at: datetime


async def list_profiles(session: AsyncSession, user_ids: list[UUID]) -> list[UserProfile]:
    """`auth_list_users` — a'zolikdan QAT'I NAZAR profil qatorlari.

    Modul funksiyasi (repozitoriy metodi emas): `GET /me` da bozor konteksti
    umuman bo'lmasligi mumkin (platforma admini bozor tanlamasdan turib
    o'z profilini ko'radi), ya'ni `market_id` talab qiladigan repozitoriyga
    bog'lab qo'yish noto'g'ri bo'lardi.
    """
    if not user_ids:
        return []
    result = await session.execute(_LIST_USERS, {"user_ids": [str(uid) for uid in user_ids]})
    return [
        UserProfile(
            user_id=row.user_id,
            phone=row.phone_e164,
            full_name=row.full_name,
            locale=row.locale,
            is_active=row.is_active,
            must_change_password=row.must_change_password,
            is_platform_admin=row.is_platform_admin,
            created_at=row.created_at,
        )
        for row in result
    ]


async def set_locale(session: AsyncSession, user_id: UUID, locale: str) -> bool:
    """Profil tilini yozadi (D-13); qator topilmasa `False`."""
    result = await session.execute(_SET_LOCALE, {"user_id": str(user_id), "locale": locale})
    return bool(result.scalar_one())


class UserRepository(TenantScopedRepository):
    """Joriy bozor a'zolari ustidagi o'qish va yozish (D-04, D-02, D-08)."""

    async def member_roles(self, user_id: UUID) -> tuple[str, ...] | None:
        """Foydalanuvchining JORIY BOZORDAGI rollari; a'zo bo'lmasa `None`.

        Bu — cross-tenant himoyasining ilova tomonidagi darvozasi (T-01-51).
        Boshqa bozorning `user_id` si uchun RLS 0 qator beradi va chaqiruvchi
        **404** qaytaradi. 403 QAYTARILMAYDI: u "bunday foydalanuvchi bor,
        lekin sizniki emas" degan ma'lumotni oshkor qilardi.
        """
        stmt = self.scoped(select(UserMarketRole.roles).where(UserMarketRole.user_id == user_id))
        result = await self.session.execute(stmt)
        row = result.one_or_none()
        return None if row is None else tuple(row.roles or ())

    async def list_members(self) -> list[MarketUser]:
        """Joriy bozor a'zolari — a'zolik (RLS) + profil (`SECURITY DEFINER`)."""
        stmt = self.scoped(select(UserMarketRole.user_id, UserMarketRole.roles))
        result = await self.session.execute(stmt)
        roles_by_user = {row.user_id: tuple(row.roles or ()) for row in result}

        profiles = await list_profiles(self.session, list(roles_by_user))
        return [
            MarketUser(
                user_id=profile.user_id,
                phone=profile.phone,
                full_name=profile.full_name,
                roles=roles_by_user[profile.user_id],
                is_active=profile.is_active,
                must_change_password=profile.must_change_password,
                locale=profile.locale,
                created_at=profile.created_at,
            )
            for profile in profiles
        ]

    async def create_user(
        self,
        *,
        phone: str,
        password_hash: str,
        full_name: str | None,
        locale: str,
    ) -> UUID | None:
        """Global `users` qatorini yaratadi; telefon BAND bo'lsa `None`.

        `is_platform_admin` ATAYIN uzatilmaydi (har doim `false`): platforma
        adminini bozor boshqaruv ekrani orqali yaratish D-04 ning ikki
        bosqichli modelidan tashqarida — u platforma darajasidagi qaror va
        1-fazada UI'si yo'q.
        """
        result = await self.session.execute(
            _CREATE_USER,
            {
                "phone": phone,
                "password_hash": password_hash,
                "full_name": full_name,
                "locale": locale,
                "is_platform_admin": False,
            },
        )
        return result.scalar_one_or_none()

    async def existing_member_phones(self) -> set[str]:
        """Joriy bozor a'zolarining telefonlari (D-15 skip lug'ati).

        YANGI SO'ROV YOZILMAYDI: `list_members()` allaqachon ikki
        qatlamli naqshni bajaradi (RLS ostidagi a'zolik -> `SECURITY
        DEFINER` profillar), ya'ni boshqa bozor a'zosining telefoni bu
        to'plamga TUSHA OLMAYDI. Alohida `SELECT phone_e164 FROM users`
        yozish esa aynan o'sha chegarani chetlab o'tardi — `users`
        GLOBAL jadval.
        """
        return {member.phone for member in await self.list_members()}

    async def create_members(
        self,
        entries: Sequence[StaffCreateEntry],
    ) -> tuple[list[CreatedMember], list[int]]:
        """Rosterni ommaviy yozadi; `(yaratilganlar, band telefonli QATORLAR)`.

        Har `entry` uchun `create_user()` chaqiriladi. U `None` qaytarsa
        telefon PLATFORMADA band — qator raqami ikkinchi ro'yxatga
        tushadi va a'zolik qatori YOZILMAYDI (aks holda begona hisob bu
        bozorga a'zo bo'lib qolardi).

        ⚠ SIKL BIRINCHI BAND TELEFONDA TO'XTAMAYDI. `auth_create_user`
        `ON CONFLICT (phone_e164) DO NOTHING` bilan ishlaydi, ya'ni u
        tranzaksiyani ABORT QILMAYDI va davom etish xavfsiz. Admin band
        telefonlarning HAMMASINI bir marta ko'rishi kerak
        (`validate_staff_rows` dagi "har qator uchun barcha tekshiruvlar"
        qoidasi bilan aynan bir xil sabab): to'xtash uni "tuzat -> yukla
        -> yangi xato" siklga tushirardi.

        Chaqiruvchi ikkinchi ro'yxat BO'SH BO'LMASA butun importni rad
        etadi (D-14) — istisno tranzaksiyani orqaga qaytaradi va bu
        yerda yozilgan qatorlar ham yo'qoladi.
        """
        created: list[CreatedMember] = []
        taken: list[int] = []

        for entry in entries:
            user_id = await self.create_user(
                phone=entry.phone,
                password_hash=entry.password_hash,
                full_name=entry.full_name,
                locale=entry.locale,
            )
            if user_id is None:
                taken.append(entry.row)
                continue

            await self.add_membership(user_id, entry.roles)
            created.append(
                CreatedMember(
                    row=entry.row,
                    user_id=user_id,
                    phone=entry.phone,
                    full_name=entry.full_name,
                    roles=entry.roles,
                )
            )

        return created, taken

    async def add_membership(self, user_id: UUID, roles: list[str]) -> None:
        """A'zolik qatorini JORIY BOZORDA yaratadi (RLS `WITH CHECK` ostida).

        `RETURNING` ATAYIN so'ralmaydi: qator identifikatori chaqiruvchiga
        kerak emas va `INSERT ... RETURNING` policy tekshiruvining ikkinchi
        yo'lini ochadi (01-06 da `audit_log` da aynan shu narsa login
        endpointini yiqitgan edi).

        Audit yozuvi bu yerda YOZILMAYDI — `user_market_roles` da
        `fn_audit_row()` triggeri bor va u xom SQL yo'lini ham qamraydi.
        """
        await self.session.execute(
            insert(UserMarketRole).values(
                market_id=self.market_id,
                user_id=user_id,
                roles=roles,
            )
        )

    async def set_roles(self, user_id: UUID, roles: list[str]) -> bool:
        """A'zolik qatorining rollarini ALMASHTIRADI; qator topilmasa `False`.

        `scoped()` ISHLATILMAYDI va bu majburiy: u AYNAN `Select` ustida
        ishlaydi (`sbozor_core.tenancy`), ya'ni `UPDATE` uchun predikat
        SHU YERDA yoziladi — `nvr_repo.py::update_device` bilan aynan bir
        xil naqsh. Ikki qatlam saqlanadi: RLS himoya to'ri, `market_id`
        predikati esa aniq filtr.

        Audit yozuvi bu yerda YOZILMAYDI — `add_membership` dagi bilan
        AYNI sabab: `user_market_roles` da `fn_audit_row()` triggeri bor
        va u `old`/`new` ni `changed_keys` bilan birga o'zi qo'yadi.
        Ilova darajasidagi ikkinchi yozuv DUBLIKAT bo'lardi.
        """
        result = await self.session.execute(
            update(UserMarketRole)
            .where(
                UserMarketRole.market_id == self.market_id,
                UserMarketRole.user_id == user_id,
            )
            .values(roles=roles)
            .returning(UserMarketRole.id)
        )
        return result.scalar_one_or_none() is not None

    async def set_active(self, user_id: UUID, *, is_active: bool) -> None:
        """Bloklaydi/tiklaydi (D-08).

        Chaqiruvchi COMMIT dan KEYIN `invalidate_user_state()` ni ishga
        tushirishi SHART, aks holda bloklash 30 soniyagacha kechikadi.
        """
        await auth_repo.set_active(self.session, user_id, is_active=is_active)

    async def set_temporary_password(self, user_id: UUID, password_hash: str) -> None:
        """Vaqtinchalik parol o'rnatadi va majburiy almashtirishni yoqadi (D-02)."""
        await auth_repo.update_password_hash(
            self.session,
            user_id,
            password_hash,
            must_change=True,
        )
