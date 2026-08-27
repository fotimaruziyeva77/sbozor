"""Sotuvchi <-> Telegram bog'lanishi — D-26 ning UCH NOMLANGAN SHOXI.

=============================================================================
⛔⛔ RLS NING ENG NOZIK MASALASI SHU YERDA HAL BO'LADI (Pattern 7).

Bot «bu Telegram ID» deydi, lekin **qaysi bozor** ekanini BILMAYDI.
`vendor_telegram_bindings` esa tenant jadvali (RLS `ENABLE` + `FORCE`),
ya'ni kontekstsiz `SELECT` **0 qator** beradi (fail-closed). Uch yo'ldan
ikkitasi YOPIQ:

  * RLS'ni chetlab o'tadigan YANGI funksiya (chaqiruvchi emas, ta'riflovchi
    huquqi bilan bajariladigan tur) -> ⛔ TAQIQ (T-06-22, G7-7: kutilgan
    funksiyalar to'plami TENGLIK bilan solishtiriladi, ya'ni yangi nom
    darvozani darhol qizartiradi);
  * jadvalni RLS'siz global qilish -> ⛔ TAQIQ (har yangi jadval
    `market_id` + RLS `FORCE` oladi);
  * `active_market_ids()` bo'ylab tsikl -> ✅ MAVJUD va YAGONA chetlab
    o'tuvchi yuza. U `app/jobs/retention.py` dan IMPORT QILINADI, nusxa
    OLINMAYDI — o'sha funksiyaning docstringi buni ochiq talab qiladi
    («xavfsizlik yuzasi AYNAN BITTA chaqiruv nuqtasiga ega bo'lishi
    kerak»).

⚠ IKKI TAQIQLANGAN NOM BU FAYLDA LITERAL YOZILMAYDI (yuqoridagi tur nomi
  va chetlab o'tuvchi funksiyaning O'ZINING nomi). Sabab 03-07 / 07-02 da
  ikki marta o'lchangan: sodda grep darvozasi IZOHNI KODDAN AJRATMAYDI va
  yagona «tuzatish» yo'li sababni o'chirish bo'lardi. Darvozaning o'zi
  `tests/integration/test_bot_internal_api.py::
  test_binding_repo_adds_no_rls_bypassing_surface` da.

⛔ ITERATSIYA «SAMARASIZLIK» EMAS, MEXANIZM. `vendors` da
`uq_vendors_market_id_phone_e164` bor, ya'ni BITTA BOZOR ICHIDA telefon
<=1 sotuvchiga mos keladi. Demak D-26(b) («bir nechta moslik») FAQAT
BOZORLAR ARO yuz beradi va uni aniqlashning yagona yo'li — barcha faol
bozorlarni ko'rib chiqish. Bitta tsikl IKKALA vazifani ham bajaradi.

=============================================================================
⛔ ERTA `break` YO'Q — TSIKL DOIMIY, LEKIN ⛔ JAVOB VAQTI BARIBIR FARQ
   QILADI. ENUMERATSIYA HIMOYASI — RATE-LIMIT, TAYMING EMAS (T-07-40,
   08-06/WR-04).

Tsikl HAR DOIM barcha faol bozorlarni oxirigacha aylanadi va bu
SAQLANADI: erta `break` tsiklning O'ZINI «raqam reyestrda bormi?»
savolining o'lchagichiga aylantirardi va u eng arzon, eng barqaror
signal bo'lardi.

⛔ LEKIN BU YOLG'IZ «DOIMIY VAQT» BERMAYDI — VA BU YERDA O'LCHANMAGAN
   DA'VO YOZILMAYDI. Tsikldan KEYINGI ish uch shoxda uch xil narxga
   ega va farq tsiklnikidan KATTA:

     `NO_MATCH`          -> faqat `log.info` — I/O YO'Q
     `BOUND`             -> yangi tenant tranzaksiyasi + `SELECT` +
                            `UPDATE`/`INSERT` + `flush`
     `MULTIPLE_MATCHES`  -> HAR mos bozor uchun tranzaksiya +
                            `alert_events` upsert

Ya'ni tayming bo'yicha «doimiy javob» DA'VOSI kodda BAJARILMAYDI va u
shu sababdan bu fayldan OLIB TASHLANDI — kuchaytirilmadi, chunki
o'lchanmagan da'vo mavjud bo'lmagan himoyaga ishonch berardi.

⚠ SUN'IY DOIMIY KECHIKISH (minimal-kechikish konstantasi + uyqu bilan
  tekislash) ONGLI RAD ETILDI: u botning javob vaqtini HAR chaqiruvda
  oshirardi va test to'plamining yugurish vaqtiga ham tushardi — narx
  REAL, foyda esa quyidagi ikki qatlam borligida NAZARIY.

⛔ ENUMERATSIYANING HAQIQIY IKKI TO'SIG'I:

  1. ⛔ D-24 — STRUKTURAVIY: odam Telegram'da FAQAT O'Z kontaktini
     ulasha oladi, ya'ni «begona raqamni sinab ko'rish» yo'li umuman
     ochilmaydi (`app/api/internal/bot.py` ning o'sha bandi).
  2. ⛔ RATE-LIMIT — `POST /internal/bot/resolve`, `telegram_user_id`
     kesimida (`BOT_RESOLVE_LIMIT = 5`). Statistik tayming hujumi
     MINGLAB o'lchov talab qiladi; besh urinish uni imkonsiz qiladi.

⚠ IKKALASI HAM O'LCHANADI, TAYMING ESA YO'Q — va bu ochiq yozilyapti:
  o'lchanmagan xavfsizlik da'vosi kodda qolsa, keyingi ijrochi mavjud
  bo'lmagan himoyaga tayanib chinakam to'siqni (rate-limit) «ortiqcha»
  deb olib tashlashi mumkin edi.

=============================================================================
⛔ MUVAFFAQIYATSIZ URINISH SAQLANMAYDI (Open Question 1 / A5, T-07-41).

Mos kelmagan telefon HECH QAYERGA yozilmaydi: na jadvalga, na jurnalga.
Urinishlarni saqlash tizimga **sotuvchi bo'lmagan** odamlarning telefon
raqamlarini yozdirardi — D-01 ostida yangi huquqiy yuk (O'zR shaxsiy
ma'lumotlar qonuni) va mahsulot qiymati nolga yaqin.

Shuning uchun «kutilmoqda ro'yxati» — bu BOG'LANMAGAN SOTUVCHILAR
ro'yxati (`vendors LEFT JOIN vendor_telegram_bindings`), muvaffaqiyatsiz
URINISHLAR emas. `pending_vendors()` aynan shu farqni kodda ifodalaydi.

⛔ `ResolveOutcome` DA TELEFON MAYDONI YO'Q. Chaqiruvchi
(`/internal/bot/*`) javobni bot-service ga beradi va u yerdan jurnalga
tushishi mumkin — ya'ni maydon mavjud bo'lsa u ertami-kechmi log'ga
chiqardi. Yo'q maydon sizib chiqa olmaydi.
=============================================================================
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from typing import TYPE_CHECKING, Final
from uuid import UUID

import structlog
from sbozor_core.enums import ActorKind, Role
from sbozor_core.models import Stall, StallAssignment, Vendor, VendorTelegramBinding
from sbozor_core.phone import InvalidPhoneError, normalize_phone
from sbozor_core.tenancy import set_tenant_context
from sqlalchemy import BigInteger, bindparam, func, select, text, update
from sqlalchemy.dialects.postgresql import UUID as PgUuid

from app.jobs.alerting import raise_alert
from app.jobs.retention import active_market_ids
from app.repositories.user_repo import UserRepository

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

__all__ = [
    "VENDOR_BINDING_CONFLICT_ALERT_KEY",
    "BindingRef",
    "DirectorRef",
    "DirectorResolveOutcome",
    "DirectorResolveStatus",
    "PendingVendor",
    "PendingVendorPage",
    "ResolveOutcome",
    "ResolveStatus",
    "VendorRef",
    "active_bindings",
    "bind",
    "bind_director",
    "pending_vendors",
    "resolve",
    "resolve_director",
    "revoke",
    "stall_codes_by_vendor",
    "tenant_session",
]

log = structlog.get_logger(__name__)

VENDOR_BINDING_CONFLICT_ALERT_KEY: Final[str] = "vendor_binding_conflict"
"""D-26(b) anomaliyasining alert kaliti.

⛔⛔ KALIT `app/jobs/alerting.py::ALERT_META` GA RO'YXATGA OLINGAN BO'LISHI
   SHART va u AYNAN SHU REJADA olindi. `_upsert()` `ALERT_META[signal.key]`
   ustida ishlaydi, ya'ni ro'yxatga olinmagan kalit `KeyError` beradi.
   Kalitni keyingi rejaga qoldirish ikki natijadan BIRINI berardi: yiqilgan
   `resolve()` yoki (xato yutilsa) ⛔ JIMGINA YO'QOLGAN ANOMALIYA.
   Ikkinchisi aynan D-26(b) oldini olmoqchi bo'lgan «reyestr nuqsoni jim
   qoladi» nosozligi (T-07-44a).

⚠ SATR IKKI JOYDA LITERAL TURADI (bu yerda va `ALERT_META` da) — import
  yo'nalishi `binding_repo -> alerting` bo'lgani uchun teskari import
  siklga olib kelardi. Mosligi `tests/integration/test_bot_internal_api.py`
  da TO'PLAM a'zoligi bilan o'lchanadi (`ORIGINAL_URI_HEADER` bilan aynan
  bir xil holat va aynan bir xil yechim).
"""

REVOKE_REASON_REBOUND: Final[str] = "rebound"
"""D-26(c) — qayta ulanishda eski qatorning bekor qilinish SABABI.

`revocation_is_paired` CHECK i `revoked_at` va `revoked_reason` ni juftlikda
talab qiladi, ya'ni sabab ixtiyoriy emas.
"""

PENDING_VENDORS_DEFAULT_LIMIT: Final[int] = 50
"""`pending_vendors()` sahifasining standart o'lchami."""


class ResolveStatus(StrEnum):
    """D-26 ning UCH NOMLANGAN SHOXI — yopiq to'plam.

    ⛔ TO'RTINCHI A'ZO QO'SHILMAYDI. «Noaniq», «xato» yoki «keyinroq» kabi
       a'zo shoxni NOMSIZ qoldirardi va chaqiruvchi uni jimgina
       `no_match` bilan bir xil ko'rsatardi — ya'ni reyestr nuqsoni yana
       ko'rinmas bo'lardi.
    """

    BOUND = "bound"
    """Aynan BITTA moslik topildi va bog'lanish YOZILDI."""

    NO_MATCH = "no_match"
    """Moslik yo'q — D-26(a).

    ⛔ Bog'lanish YOZILMAYDI, hech qanday qator yaratilmaydi va telefon
       raqami HECH QAYERGA saqlanmaydi. Sabab modul docstringida.

    ⛔ Format xatosi (`InvalidPhoneError`) HAM shu qiymatni beradi:
       «raqamingiz noto'g'ri formatda» degan javob «raqamingiz reyestrda
       yo'q» dan AJRALIB TURARDI va o'sha farqning o'zi enumeratsiya
       signali bo'lardi.
    """

    MULTIPLE_MATCHES = "multiple_matches"
    """>=2 moslik — D-26(b), FAQAT bozorlar aro (modul docstringi).

    ⛔ Bog'lanish YOZILMAYDI va JIMGINA «birinchisini tanlash» TAQIQLANADI:
       bu REYESTR NUQSONI va uni yashirish noto'g'ri sotuvchiga boshqa
       birovning qarzini ko'rsatardi (T-07-44).
    """


@dataclass(frozen=True, slots=True)
class VendorRef:
    """Sotuvchiga ishora — FAQAT IDENTIFIKATORLAR.

    ⛔ ISM, TELEFON YOKI BOZOR NOMI YO'Q (D-05, T-07-42). Bu obyekt
       `/internal/bot/*` javobining tanasiga aylanadi va u yerdan
       bot-service ning jurnaliga tushishi mumkin.
    """

    market_id: UUID
    vendor_id: UUID


@dataclass(frozen=True, slots=True)
class ResolveOutcome:
    """`resolve()` ning natijasi — holat va (muvaffaqiyatda) ishora.

    ⛔ `phone` MAYDONI YO'Q va bu `dataclasses.fields()` bilan o'lchanadi.
       Sabab modul docstringida: mavjud maydon ertami-kechmi jurnalga
       chiqardi.
    """

    status: ResolveStatus
    vendor: VendorRef | None = None


@dataclass(frozen=True, slots=True)
class BindingRef:
    """Faol bog'lanish — `(market_id, vendor_id)` juftligi.

    ⚠ BIR TELEGRAM ID IKKI BOZORDA FAOL BO'LISHI MUMKIN va bu QONUNIY:
      sotuvchi ikki bozorda savdo qiladi va ikkalasida ham o'z qarzini
      ko'rishi kerak (`BINDING_TELEGRAM_ACTIVE_INDEX` docstringi —
      cheklov `market_id` bilan boshlanadi, ya'ni faqat bozor ICHIDA
      ishlaydi). Shuning uchun `active_bindings()` RO'YXAT qaytaradi va
      chaqiruvchi birinchisini JIMGINA TANLAMAYDI.
    """

    market_id: UUID
    vendor_id: UUID


@dataclass(frozen=True, slots=True)
class PendingVendor:
    """Bog'lanmagan sotuvchi — D-26(a) ning ADMIN ko'rinishi.

    ⛔ `full_name` / `phone_e164` MAYDONLARI YO'Q va bu D-05 ning bevosita
       talabi: `PERSONAL_ROUTES` O'SMASLIGI shart (G7-6). Ism klientda
       AUDIT QILINGAN `GET /api/v1/vendors` bilan joinlanadi — o'sha
       marshrut `audit_read` + `VENDOR_VIEW` ostida va aynan shu tufayli
       «kim sotuvchi ismini ko'rdi?» savoli javobsiz qolmaydi.
    """

    vendor_id: UUID
    stall_codes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PendingVendorPage:
    """Keyset sahifasi — `next_cursor` `None` bo'lsa ro'yxat tugadi."""

    items: tuple[PendingVendor, ...]
    next_cursor: UUID | None


class DirectorResolveStatus(StrEnum):
    """Direktor shoxining IKKI nomlangan holati — yopiq to'plam.

    ⛔ `ResolveStatus` NING UCHINCHI A'ZOSI (`multiple_matches`) BU YERDA
       YO'Q va uning yo'qligi MEXANIK, kelishuv EMAS.

    Sotuvchida noaniqlik REYESTR NUQSONI: `vendors` da telefon global
    noyob emas (`uq_vendors_market_id_phone_e164` faqat BOZOR ICHIDA
    ishlaydi), ya'ni bir telefon ikki sotuvchi qatoriga mos kelishi
    mumkin va u holat tuzatilishi kerak.

    `users.phone_e164` esa GLOBAL NOYOB (`auth_create_user` band telefonda
    `None` qaytaradi), ya'ni bir telefon = BIR ODAM. Bir odamning ikki
    bozorda direktor bo'lishi QONUNIY (`user_market_roles` da ikki qator)
    va har bozorning O'Z sozlama qatori bor. Demak «bir nechta moslik»
    holati bu shoxda UMUMAN TUG'ILMAYDI: mos kelgan HAR BIR bozorning
    qatori yoziladi.
    """

    BOUND = "bound"
    """>=1 bozorda direktor topildi va HAR BIRINING chati YOZILDI."""

    NO_MATCH = "no_match"
    """Moslik yo'q — `ResolveStatus.NO_MATCH` bilan AYNI ma'no va AYNI matn.

    ⛔ Format xatosi, reyestrda yo'q telefon, bloklangan xodim va
       kassir/nazoratchi roli — TO'RTALASI HAM shu qiymat. Ularni ajratish
       reyestrni tashqaridan tekshirish oracle'i bo'lardi.
    """


@dataclass(frozen=True, slots=True)
class DirectorRef:
    """Direktorga ishora — FAQAT IDENTIFIKATORLAR.

    ⛔ TELEFON VA ISM MAYDONI YO'Q (D-05, `VendorRef` bilan aynan bir xil
       sabab): bu tip javob quruvchisiga boradi va u yerdan bot-service
       ning jurnaliga tushishi mumkin. Yo'q maydon sizib chiqa olmaydi.
    """

    market_id: UUID
    user_id: UUID


@dataclass(frozen=True, slots=True)
class DirectorResolveOutcome:
    """`resolve_director()` ning natijasi — holat va mos kelgan bozorlar.

    ⚠ `markets` RO'YXAT: bir odam bir nechta bozorning direktori bo'lishi
      QONUNIY va HAR BIRINING sozlama qatori yoziladi
      (`DirectorResolveStatus` docstringi).
    """

    status: DirectorResolveStatus
    markets: tuple[DirectorRef, ...] = ()


# ===========================================================================
# Tranzaksiya chegarasi
# ===========================================================================


@asynccontextmanager
async def tenant_session(
    sessionmaker: async_sessionmaker[AsyncSession],
    *,
    market_id: UUID,
    request_id: str | None,
) -> AsyncIterator[AsyncSession]:
    """Tenant konteksti O'RNATILGAN qisqa tranzaksiya — BOT YO'LINING YAGONA kirishi.

    ⚠ NUSXA EMAS, JUFT — VA BU FARQ `active_market_ids()` DAN ATAYIN
      AJRATILGAN. `app/jobs/retention.py::active_market_ids` docstringi
      ikkalasini ochiq ajratadi: RLS'ni chetlab o'tuvchi so'rov
      TAKRORLANMAYDI va import qilinadi, kontekst menejeri esa xavfsizlik
      YUZASI emas, STRUKTURAVIY naqsh va u `discovery.py`, `capture.py`,
      `retention.py`, `alerting.py` da ATAYIN takrorlangan (modul hech
      kimga bog'lanmasligi uchun). Bu — beshinchi nusxa.

    ⚠ OMMAVIY (`_` PREFIKSISIZ) va sabab mexanik: `/internal/bot/*`
      marshrutlarida `Principal` YO'Q, ya'ni `deps.py::TenantSessionDep`
      (u bozorni `Principal` dan oladi) UMUMAN ishlamaydi. Bot yo'liga
      o'z kontekst menejeri kerak va u AYNAN BITTA bo'lishi shart —
      marshrut faylida ikkinchi nusxa yozilsa `actor_kind` yoki
      tranzaksiya chegarasi jimgina ajralib ketardi.

    ⚠ `actor_kind = SYSTEM`, `actor_id = None`: bu yo'lda `Principal`
      UMUMAN YO'Q (D-10) va uni «taxmin qilib» yozish audit jurnalida
      yolg'on dalil bo'lardi.
    """
    # SIM117 `retention.py` dagi bilan bir xil sababdan rad etilgan:
    # ichki blok TRANZAKSIYA chegarasi.
    async with sessionmaker() as session:  # noqa: SIM117
        async with session.begin():
            await set_tenant_context(
                session,
                market_id=market_id,
                actor_id=None,
                request_id=request_id,
                actor_kind=ActorKind.SYSTEM,
            )
            yield session


# ===========================================================================
# Normalizatsiya — CHEGARADA va AYNAN BIR JOYDA (D-25)
# ===========================================================================


def _normalize(raw_phone: str) -> str | None:
    """Telegram dan kelgan raqamni E.164 ga keltiradi; xato bo'lsa `None`.

    ⚠ `Contact.phone_number` BA'ZAN `+` SIZ KELADI (klient/platformaga
      qarab — `07-RESEARCH.md` § Pattern 6). `phonenumbers` `+` siz satrni
      MILLIY raqam deb o'qiydi, ya'ni `998901234567` `UZ` mintaqasida
      12 xonali «milliy» raqam bo'lib chiqadi va `is_valid_number()` uni
      RAD ETADI. Shuning uchun `+` yo'q bo'lsa QO'SHILADI.

    ⚠ IKKINCHI URINISH — XOM SATR BILAN. `+` qo'shish `901234567` kabi
      HAQIQIY milliy shaklni buzardi (`+90...` — Turkiya kodi), shuning
      uchun birinchi urinish yiqilsa xom satr `DEFAULT_REGION` bilan
      qayta o'qiladi. Ikkala yo'l ham `normalize_phone()` ga boradi:
      ⛔ YANGI REGEKS YOZILMAYDI (D-25 — normalizatsiya AYNAN BIR JOYDA).

    ⛔ XATO SABABI OSHKOR QILINMAYDI: chaqiruvchi faqat `None` ko'radi va
       uni `NO_MATCH` ga aylantiradi. «Format noto'g'ri» va «reyestrda
       yo'q» javoblarining farqi enumeratsiya signali bo'lardi.
    """
    candidate = raw_phone.strip()
    if not candidate:
        return None

    attempts = (candidate,) if candidate.startswith("+") else (f"+{candidate}", candidate)
    for attempt in attempts:
        try:
            return normalize_phone(attempt)
        except InvalidPhoneError:
            continue
    return None


# ===========================================================================
# D-26 — UCH NOMLANGAN SHOX
# ===========================================================================


async def resolve(
    sessionmaker: async_sessionmaker[AsyncSession],
    *,
    raw_phone: str,
    telegram_user_id: int,
    request_id: str | None = None,
) -> ResolveOutcome:
    """Telefon -> sotuvchi moslashtirish, D-26 ning uch shoxi bilan.

    ⛔ FUNKSIYA `sessionmaker` OLADI, `session` EMAS: u `active_market_ids()`
       bo'ylab BIR NECHA tenant sessiyasi ochadi. Tayyor sessiya berilsa
       uning konteksti BITTA bozorga qadalgan bo'lardi va D-26(b)
       («bozorlar aro moslik») shoxi HECH QACHON bajarilmasdi.

    Bosqichlar:
      1. normalizatsiya (chegarada, `_normalize()`);
      2. HAR faol bozor bo'ylab tsikl — ⛔ erta `break` YO'Q (modul
         docstringi, T-07-40);
      3. natijaga qarab uch shox.

    ⚠ TSIKL DOIMIY, JAVOB VAQTI ESA EMAS: 3-bosqichning narxi uch shoxda
      uch xil (`NO_MATCH` — I/O yo'q; `BOUND` — yozuv tranzaksiyasi;
      `MULTIPLE_MATCHES` — har bozor uchun alert upserti). Enumeratsiya
      himoyasi shuning uchun TAYMINGDA emas — D-24 (odam faqat O'Z
      kontaktini ulashadi) va rate-limitda (`BOT_RESOLVE_LIMIT`). To'liq
      sabab modul docstringining o'sha bandida (WR-04).

    Returns:
        `ResolveOutcome` — ⛔ telefon raqami YO'Q (modul docstringi).
    """
    phone = _normalize(raw_phone)
    if phone is None:
        # ⛔ Raqam JURNALGA HAM yozilmaydi: u shaxsiy ma'lumot va urinish
        #   sotuvchi bo'lmagan odamdan kelgan bo'lishi mumkin.
        log.info("bot_resolve_unparseable_phone", telegram_user_id=telegram_user_id)
        return ResolveOutcome(status=ResolveStatus.NO_MATCH)

    matches: list[VendorRef] = []
    for market_id in await active_market_ids(sessionmaker):
        async with tenant_session(
            sessionmaker, market_id=market_id, request_id=request_id
        ) as session:
            # ⚠ `market_id` PREDIKATI RLS BILAN BIRGA — ikkinchi qatlam.
            #   RLS `FORCE` allaqachon sessiyani shu bozorga qamaydi;
            #   aniq predikat esa kontekst o'rnatilmay qolgan holatda
            #   so'rovni JIMGINA butun jadvalga yoymaydi.
            #
            # ⛔ «FAOL SOTUVCHI» PREDIKATI YO'Q va bu SXEMADAN kelib
            #   chiqadi, unutishdan emas: `vendors` da holat/bayroq ustuni
            #   UMUMAN yo'q (`models/market.py::Vendor` — ikki ustun:
            #   `full_name`, `phone_e164`). Sun'iy `is_active` shartini
            #   o'ylab topish ikkinchi haqiqat manbai bo'lardi.
            result = await session.execute(
                select(Vendor.id).where(
                    Vendor.market_id == market_id,
                    Vendor.phone_e164 == phone,
                )
            )
            matches.extend(
                VendorRef(market_id=market_id, vendor_id=vendor_id)
                for vendor_id in result.scalars().all()
            )

    if not matches:
        # --- D-26(a) --------------------------------------------------
        # ⛔ HECH NIMA YOZILMAYDI: na bog'lanish, na «urinish» qatori.
        log.info("bot_resolve_no_match", telegram_user_id=telegram_user_id)
        return ResolveOutcome(status=ResolveStatus.NO_MATCH)

    if len(matches) > 1:
        # --- D-26(b) --------------------------------------------------
        await _raise_conflict(
            sessionmaker,
            matches=matches,
            telegram_user_id=telegram_user_id,
            request_id=request_id,
        )
        return ResolveOutcome(status=ResolveStatus.MULTIPLE_MATCHES)

    # --- D-26(c)/BOUND ------------------------------------------------
    match = matches[0]
    async with tenant_session(
        sessionmaker, market_id=match.market_id, request_id=request_id
    ) as session:
        await bind(
            session,
            market_id=match.market_id,
            vendor_id=match.vendor_id,
            telegram_user_id=telegram_user_id,
        )
    log.info("bot_resolve_bound", telegram_user_id=telegram_user_id)
    return ResolveOutcome(status=ResolveStatus.BOUND, vendor=match)


async def _raise_conflict(
    sessionmaker: async_sessionmaker[AsyncSession],
    *,
    matches: list[VendorRef],
    telegram_user_id: int,
    request_id: str | None,
) -> None:
    """D-26(b) — HAR TEGISHLI BOZORDA anomaliya alerti ochadi.

    ⛔ QATOR IKKALA BOZORGA HAM YOZILADI va bu `platform_scoped=False`
       qarorining bevosita natijasi: to'qnashuv IKKALA bozorning
       reyestriga tegishli va har bozor direktori O'Z qatorini ko'rishi
       kerak. `True` bo'lsa xabar bozorlar bo'ylab BITTA bo'lib
       birlashardi va ikkinchi bozor ma'muriyati hech nima ko'rmasdi.

    ⛔ `detail` BO'SH: `ALERT_DETAIL_KEYS` allowlisti telefon yoki ism
       uchun kalit BERMAYDI va bermasligi ham kerak — alert matni faqat
       «reyestrda takrorlangan raqam bor» faktini aytadi, tuzatish esa
       veb yuzasida bajariladi (`04-UI-SPEC.md` §11.9).

    ⚠ TAKRORIY URINISH NAVBATNI TO'LDIRMAYDI: `_upsert()` qisman UNIQUE
      indeks (`uq_alert_events_market_id_alert_key_open`) ustida
      `ON CONFLICT DO UPDATE` qiladi, ya'ni ikkinchi chaqiruv YANGI qator
      emas, `occurrences + 1` beradi.
    """
    for market_id in sorted({match.market_id for match in matches}):
        async with tenant_session(
            sessionmaker, market_id=market_id, request_id=request_id
        ) as session:
            await raise_alert(session, market_id=market_id, key=VENDOR_BINDING_CONFLICT_ALERT_KEY)

    log.warning(
        "bot_resolve_multiple_matches",
        telegram_user_id=telegram_user_id,
        market_count=len({match.market_id for match in matches}),
    )


# ===========================================================================
# DIREKTOR SHOXI — DAYJEST MANZILINING YAGONA YOZUV YO'LI (RECON-03)
# ===========================================================================
#
# ⛔⛔ BU BO'LIM 07-18 GACHA MAVJUD EMAS EDI VA UNING YO'QLIGI MEZON #3 NI
#    STRUKTURAVIY RAVISHDA BAJARILMAS QILGAN EDI:
#    `market_notification_settings.director_chat_id` ga butun repo bo'ylab
#    BIRORTA yozuvchi yo'q edi, ya'ni `outbox_repo` ning o'quvchisi
#    (`_RESOLVE_DIRECTOR_CHAT`) produksiyada HAR DOIM `None` qaytarardi va
#    direktor dayjestni HECH QACHON olmasdi.
#
# ⛔ SHAKL — DIREKTOR BOTGA `contact` ULASHADI, admin veb formaga RAQAM
#    KO'CHIRMAYDI. Sabab: `director_chat_id` — Telegram ning ICHKI raqami
#    va uni qo'lda kiritishda BITTA xato dayjestni (kunlik tushum, bandlik,
#    TOP-10 qarzdorning summasi) BEGONA odamning chatiga yuborardi —
#    qiymat sintaktik jihatdan to'g'ri bo'lib qolaverardi va hech bir
#    darvoza buni ushlay olmasdi. `contact` esa Telegram O'ZI kafolatlagan
#    yagona narsa (D-24) va u `contact.user_id == message.from_user.id`
#    bilan MEXANIK tekshiriladi.


_BIND_DIRECTOR_CHAT = text(
    """
    INSERT INTO market_notification_settings (market_id, director_chat_id)
         VALUES (:market_id, :chat_id)
    ON CONFLICT (market_id) DO UPDATE
            SET director_chat_id = EXCLUDED.director_chat_id,
                updated_at = now()
      RETURNING (xmax = 0) AS inserted
    """
).bindparams(
    bindparam("market_id", type_=PgUuid(as_uuid=True)),
    bindparam("chat_id", type_=BigInteger()),
)
"""Direktorning chatini sozlama qatoriga YOZADI (UPSERT).

=============================================================================
⛔⛔ NEGA `UPSERT`, YA'NI NEGA BOZOR YARATILGANDA QATOR TUG'ILMAYDI — QAROR.

`market_create()` KASKADIGA `market_notification_settings` QATORI
QO'SHILMAYDI va bu bo'shliq emas, ONGLI TANLOV. Sabab: jadvalning uchala
ustuni ham qator BO'LMAGANDA to'g'ri qiymat beradi va bu ikki joyda
O'LCHANGAN, taxmin qilinmagan:

  * `outbox_repo._CLAIM_DUE` — `LEFT JOIN market_notification_settings` +
    `COALESCE(s.quiet_hours_start, :quiet_start)`; `JOIN` yozilganda
    sozlamasiz bozorning butun navbati JIMGINA ko'rinmas bo'lardi, shuning
    uchun u ATAYIN `LEFT JOIN`;
  * `jobs/notifications._MARKET_OVERDUE_DAYS` va uning jufti
    `jobs/reconciliation` da — `COALESCE((SELECT s.overdue_days ...),
    :fallback)`, standart esa SXEMADAN hosila
    (`notification_meta.DEFAULT_OVERDUE_DAYS`).

Ya'ni qatorni oldindan yaratish HECH BIR o'quvchining javobini
o'zgartirmaydi, lekin IKKINCHI standart manbaini tug'dirardi: sxemaning
`server_default` i va kaskadning yozgan qiymati bir kun ajralib ketardi
va «standart qaysi?» savoliga ikki joy ikki xil javob berardi. Bundan
tashqari kaskad `markets` ni yaratadigan DB FUNKSIYASIDA (migratsiyada)
yashaydi — unga yangi jadval qo'shish MIGRATSIYA talab qilardi, holbuki
bu yo'l migratsiyasiz qurilgan.

⚠ O'sha funksiyaning bajarilish huquqi turi bu yerda LITERAL
  yozilmaydi — sabab modul docstringining «ikki taqiqlangan nom»
  bandida (darvoza izohni koddan ajratmaydi).

`director_chat_id` esa boshqa toifada: uning standarti YO'Q va u faqat
direktor botga ulanganda ma'lum bo'ladi. Shuning uchun qator AYNAN SHU
yerda, LAZY tarzda tug'iladi — `ON CONFLICT` esa «qator allaqachon bor»
(masalan `overdue_days` veb yuzasidan o'zgartirilgan) shoxini xatosiz
qamraydi.
=============================================================================

⛔ FAQAT IKKI USTUN `SET` QILINADI. `quiet_hours_start`, `quiet_hours_end`
   va `overdue_days` — BOZOR SOZLAMASI (D-19) va ular direktorning
   telefonidan kelmaydi. Ularni `EXCLUDED` bilan ustiga yozish qayta
   ulanishni «sozlamalarni standartga qaytarish» amaliga aylantirardi va
   direktor sabab ko'rmasdi.

⚠ `xmax = 0` — «bu qator YANGI yaratildimi?» faktining Postgres dagi
  yagona arzon manbai: `ON CONFLICT DO UPDATE` shoxida qator versiyasi
  yangilanadi va `xmax` nolga teng bo'lmaydi.
"""


async def bind_director(session: AsyncSession, *, market_id: UUID, chat_id: int) -> bool:
    """Bozorning dayjest manzilini yozadi; `True` = qator YANGI yaratildi.

    ✅ AUDIT QATORI ENDI YOZILADI — DB TRIGGERI BILAN (`0025`, 8-faza).
       `market_notification_settings` `schema_contract.AUDITED_TABLES` ga
       QO'SHILDI va unga `fn_audit_row()` ulandi, ya'ni «direktor chatini
       kim, qachon almashtirdi?» savoli endi `audit_log` dan javob oladi
       (`row_id` = qatorning `id` si). 07 `deferred-items.md` №4 SHU BILAN
       yopildi.

       ⛔ ILOVA DARAJASIDA QO'LDA AUDIT YOZILMAYDI VA BU O'ZGARMADI:
          u `revoke()` da topilgan WR-03 nuqsonining aynan takrori
          bo'lardi (to'qilgan `old` qiymat + reyestr qarori bilan zid
          xulq). Iz DB triggeridan keladi, ilovadan EMAS.
       ⚠ SHU SABABNI YOZUVCHI FUNKSIYA NOMI BU YERDA LITERAL
         KELTIRILMAYDI: `test_bot_internal_api.py` uning SANOG'INI
         qulflaydi (yangi chaqiruv qo'shilmagani shu bilan o'lchanadi) va
         izohning O'ZI sanoqni oshirib, darvozani sababi bilan
         qizartirardi — 03-07 / 07-02 darsining aynan takrori.

    ⛔ ESKI SABAB O'LCHOV BILAN RAD ETILDI, TAKRORLANMASIN. Bu docstring
       avval «`fn_audit_row()` `id` ustunisiz jadvalda har DML da
       YIQILARDI» degan edi. 2026-08-16 da `PostgreSQL 18.4` da
       o'lchandi: trigger YIQILMAYDI — u `row_id IS NULL` bo'lgan qator
       yozadi va o'sha qator QAYSI qatorga tegishli ekanini aytmaydi.
       To'siq TEXNIK emas, MA'NOVIY edi; `0025` unga `id uuid` PK berib
       (va ⛔ `UNIQUE (market_id)` ni SAQLAB) hal qildi.

    ⛔⛔ `ON CONFLICT (market_id)` NING TAYANCHI — `uq_market_notification_
       settings_market_id`. PK `id` ga ko'chgan, ya'ni bu cheklov olib
       tashlansa quyidagi so'rov «there is no unique or exclusion
       constraint matching the ON CONFLICT specification» bilan yiqiladi
       va direktor botga UMUMAN ULANA OLMAYDI. Bu SABOTAJ bilan
       o'lchangan (`08-02` / T3).

    ⛔ FUNKSIYA `session` OLADI, `sessionmaker` EMAS: u chaqiruvchining
       tranzaksiyasida ishlaydi (`outbox_repo` funksiyalarining aynan
       qoidasi). Tenant konteksti chaqiruvchida o'rnatiladi — RLS
       `tenant_policy` `FOR ALL ... WITH CHECK(...)` bo'lgani uchun
       kontekstsiz `INSERT` policy bilan RAD ETILADI.

    ⛔ `chat_id` JURNALGA YOZILMAYDI (loyihaning qattiq cheklovi).

    Returns:
        `True` — sozlama qatori shu chaqiruvda tug'ildi; `False` — mavjud
        qatorning manzili ustiga yozildi (qayta ulanish).
    """
    result = await session.execute(
        _BIND_DIRECTOR_CHAT, {"market_id": market_id, "chat_id": chat_id}
    )
    return bool(result.scalar_one())


async def resolve_director(
    sessionmaker: async_sessionmaker[AsyncSession],
    *,
    raw_phone: str,
    telegram_user_id: int,
    request_id: str | None = None,
) -> DirectorResolveOutcome:
    """Telefon -> direktor moslashtirish va HAR MOS BOZORNING chatini yozish.

    ⛔ FUNKSIYA `sessionmaker` OLADI, `session` EMAS: u
       `active_market_ids()` bo'ylab bir necha tenant sessiyasi ochadi
       (`resolve()` bilan aynan bir xil sabab).

    Bosqichlar:
      1. normalizatsiya (chegarada, `_normalize()`);
      2. HAR faol bozor bo'ylab SKANER — ⛔ erta `break` YO'Q;
      3. mos kelgan HAR BIR bozor uchun ALOHIDA tranzaksiyada `bind_director()`.

    ⛔ NORMALIZATSIYA YIQILGANDA HAM TSIKL TO'LIQ YUGURADI. Erta `return`
       tsiklning O'ZINI «raqam shakli to'g'rimi?» o'lchagichiga
       aylantirardi — `resolve()` ning aynan qoidasi (T-07-40). Moslik
       tekshiruvida `None` hech qanday telefonga teng bo'lmaydi.
       ⚠ BU «DOIMIY JAVOB VAQTI» DEGANI EMAS: mos bozor topilganda
         tsikldan keyin HAR BIRI uchun yozuv tranzaksiyasi ochiladi va
         narx shu yerda ajraladi. Enumeratsiya himoyasi D-24 va
         rate-limitda (modul docstringi, WR-04).

    ⛔ ROL VA HOLAT TEKSHIRUVI HAQIQIY: moslik FAQAT `Role.DIRECTOR` roli
       BOR va `is_active` bo'lgan a'zoda. Kassir/nazoratchi telefoni va
       bloklangan xodim `NO_MATCH` beradi — bloklangan xodim bozorning
       kunlik tushumini olishda davom etardi.

    ⛔ TELEFON HECH QAYERGA YOZILMAYDI: na `log.*` argumentiga, na istisno
       matniga, na natija tipiga (modul docstringi).

    ⛔ YOZUV O'QISHDAN KEYIN VA HAR BOZOR UCHUN ALOHIDA TRANZAKSIYADA:
       bitta bozorning yozuvi yiqilsa qolganlari o'z holicha qoladi.

    Returns:
        `DirectorResolveOutcome` — ⛔ telefon raqami YO'Q.
    """
    phone = _normalize(raw_phone)

    matches: list[DirectorRef] = []
    for market_id in await active_market_ids(sessionmaker):
        async with tenant_session(
            sessionmaker, market_id=market_id, request_id=request_id
        ) as session:
            members = await UserRepository(session, market_id).list_members()
        matches.extend(
            DirectorRef(market_id=market_id, user_id=member.user_id)
            for member in members
            if member.is_active
            and Role.DIRECTOR.value in member.roles
            # ⚠ `phone is None` bo'lganda bu shart HAR DOIM yolg'on —
            #   `_normalize()` ikkala tomonda ham ishlaydi, ya'ni
            #   `None == None` bilan tasodifiy moslik TUG'ILMAYDI.
            and phone is not None
            and _normalize(member.phone) == phone
        )

    if not matches:
        # ⛔ NA TELEFON, NA `telegram_user_id` (u DIREKTOR uchun aynan
        #   `chat_id` ning O'ZI) jurnalga yozilmaydi.
        log.info("director_resolve_no_match")
        return DirectorResolveOutcome(status=DirectorResolveStatus.NO_MATCH)

    rebound = 0
    for match in matches:
        async with tenant_session(
            sessionmaker, market_id=match.market_id, request_id=request_id
        ) as session:
            created = await bind_director(
                session, market_id=match.market_id, chat_id=telegram_user_id
            )
        rebound += 0 if created else 1

    log.info("director_chat_bound", market_count=len(matches), rebound=rebound)
    return DirectorResolveOutcome(status=DirectorResolveStatus.BOUND, markets=tuple(matches))


# ===========================================================================
# Bog'lanishni yozish va bekor qilish (APPEND-ONLY)
# ===========================================================================


async def revoke(
    session: AsyncSession,
    *,
    market_id: UUID,
    binding_id: UUID,
    vendor_id: UUID,
    telegram_user_id: int,
    reason: str,
) -> bool:
    """FAOL bog'lanishni bekor qiladi — ⛔ IDEMPOTENT NO-OP va AUDITSIZ.

    ⛔ ESKI QATOR O'CHIRILMAYDI (append-only, D-20 sinfi). `DELETE` yozish
       «eski bog'lanish qachon, nega bekor qilindi?» savolini javobsiz
       qoldirardi — holbuki aynan shu savol nizoda (D-02) «xabar kimga
       ketgan edi?» degan javobni beradi. Jadvalning O'Z docstringi
       (`models/notification.py::VendorTelegramBinding`) buni TARIX deb
       ta'riflaydi.

    =======================================================================
    ⛔⛔ (1) `revoked_at IS NULL` QO'RIQCHISI — APPEND-ONLY NING IKKINCHI
       YARMI (07-21, WR-03).

    Qo'riqchisiz `UPDATE` ALLAQACHON bekor qilingan qatorning `revoked_at`
    va `revoked_reason` ustunlarini QAYTA YOZARDI. Jadvalning butun
    mazmuni TARIX (D-27), ya'ni qayta yozish ASL bekor qilish paytini va
    ASL sababini YO'Q QILARDI — «o'chirmaymiz» qoidasi saqlanib turib,
    dalil baribir yo'qolardi. `RETURNING` bo'sh bo'lsa funksiya JIM
    qaytadi: hech nima o'zgarmagan, ya'ni jurnalga ham yozadigan fakt
    yo'q.

    =======================================================================
    ⛔⛔ (2) AUDIT QATORI YOZILMAYDI — REYESTR QARORI USTUN (07-21, WR-03).

    `schema_contract.AUDITED_TABLES` docstringi `vendor_telegram_bindings`
    ni ATAYIN chiqargan: jadvalning O'ZI TARIX va audit unga IKKINCHI
    NUSXA yozardi. Ilgari bu funksiya ilova darajasida qo'lda audit
    yozardi, ya'ni ⛔ REYESTR QARORI VA KOD BIR-BIRIGA ZID EDI — «bu
    jadval auditsiz» degan hujjat bilan «audit yozilyapti» degan xulq bir
    vaqtda mavjud edi.

    ⛔ REYESTR TEGILMAYDI, KOD UNGA MOSLASHADI: teskarisi (jadvalni
       reyestrga qo'shish) `fn_audit_row()` ni talab qilardi va u `row_id`
       ni `uuid` ga keltiradi — bu jadvalda esa `id uuid` bor, ya'ni
       texnik to'siq yo'q, LEKIN ikkinchi nusxa muammosi qoladi.

    =======================================================================
    ⛔ (3) `old={"revoked_at": None, ...}` TO'QILGAN QIYMAT EDI: kod
       qatorning HAQIQIY oldingi holatini O'QIMASDAN, uni `None` deb
       FARAZ QILARDI. Qayta bekor qilishda esa faraz YOLG'ON bo'lardi va
       audit jurnali «avval bekor qilinmagan edi» deb YOLG'ON DALIL
       yozardi. U (2) bilan birga yo'qoldi.

    ⚠ TUZILMAVIY JURNAL QOLADI va uning argumentlari O'ZGARMAYDI: telefon
      raqami u yerda YO'Q va qo'shilmaydi.
    =======================================================================

    Returns:
        `True` — qator SHU chaqiruvda bekor qilindi; `False` — u
        allaqachon bekor qilingan edi va hech nima o'zgarmadi.
    """
    revoked = (
        await session.execute(
            update(VendorTelegramBinding)
            .where(
                VendorTelegramBinding.market_id == market_id,
                VendorTelegramBinding.id == binding_id,
                # ⛔ QO'RIQCHI — docstringning (1) bandi.
                VendorTelegramBinding.revoked_at.is_(None),
            )
            .values(revoked_at=func.now(), revoked_reason=reason)
            .returning(VendorTelegramBinding.id)
        )
    ).scalar_one_or_none()

    if revoked is None:
        return False

    log.info(
        "vendor_binding_revoked",
        market_id=str(market_id),
        vendor_id=str(vendor_id),
        telegram_user_id=telegram_user_id,
        reason=reason,
    )
    return True


async def bind(
    session: AsyncSession,
    *,
    market_id: UUID,
    vendor_id: UUID,
    telegram_user_id: int,
) -> UUID:
    """Yangi bog'lanish qatori — D-26(c) qayta ulanish bilan.

    IKKI QISMAN UNIQUE INDEKS, IKKI BEKOR QILISH YO'LI:

      * `uq_vendor_telegram_bindings_vendor_active` — o'sha SOTUVCHIDA
        faol bog'lanish (telefon almashtirildi, akkaunt o'g'irlandi,
        oila a'zosining telefoni edi);
      * `uq_vendor_telegram_bindings_telegram_active` — o'sha TELEGRAM
        AKKAUNTIDA boshqa sotuvchiga faol bog'lanish (bir odam ikki
        sotuvchi qatorini boshqarmoqchi).

    Ikkalasi ham BEKOR QILINADI, keyin YANGI qator qo'shiladi. Bekor
    qilinmasa `INSERT` `UniqueViolation` bilan yiqilardi va sotuvchi
    «bot ishlamayapti» ko'rinishidagi nosozlik olardi.

    Returns:
        Yangi qatorning identifikatori.
    """
    open_rows = (
        await session.execute(
            select(
                VendorTelegramBinding.id,
                VendorTelegramBinding.vendor_id,
                VendorTelegramBinding.telegram_user_id,
            ).where(
                VendorTelegramBinding.market_id == market_id,
                VendorTelegramBinding.revoked_at.is_(None),
                (VendorTelegramBinding.vendor_id == vendor_id)
                | (VendorTelegramBinding.telegram_user_id == telegram_user_id),
            )
        )
    ).all()

    for row in open_rows:
        if row.vendor_id == vendor_id and row.telegram_user_id == telegram_user_id:
            # Ayni bog'lanish ALLAQACHON faol — qayta yozish audit
            # jurnalini bo'sh o'zgarish bilan to'ldirardi.
            return UUID(str(row.id))
        await revoke(
            session,
            market_id=market_id,
            binding_id=UUID(str(row.id)),
            vendor_id=UUID(str(row.vendor_id)),
            telegram_user_id=int(row.telegram_user_id),
            reason=REVOKE_REASON_REBOUND,
        )

    binding = VendorTelegramBinding(
        market_id=market_id,
        vendor_id=vendor_id,
        telegram_user_id=telegram_user_id,
    )
    session.add(binding)
    await session.flush()
    return binding.id


# ===========================================================================
# O'QISH YUZASI
# ===========================================================================


async def active_bindings(
    sessionmaker: async_sessionmaker[AsyncSession],
    *,
    telegram_user_id: int,
    request_id: str | None = None,
) -> tuple[BindingRef, ...]:
    """Telegram ID ning FAOL bog'lanishlari — barcha faol bozorlar bo'ylab.

    ⛔ BOT BOZORNI BILMAYDI, shuning uchun bu yerda ham `active_market_ids()`
       bo'ylab yuriladi (modul docstringi).

    ⚠ RO'YXAT, BITTA QIYMAT EMAS: bir sotuvchi ikki bozorda savdo qilishi
      mumkin (`BindingRef` docstringi). Chaqiruvchi birinchisini JIMGINA
      TANLAMAYDI — u ikkala bozorning javobini ham beradi.
    """
    found: list[BindingRef] = []
    for market_id in await active_market_ids(sessionmaker):
        async with tenant_session(
            sessionmaker, market_id=market_id, request_id=request_id
        ) as session:
            result = await session.execute(
                select(VendorTelegramBinding.vendor_id).where(
                    VendorTelegramBinding.market_id == market_id,
                    VendorTelegramBinding.telegram_user_id == telegram_user_id,
                    VendorTelegramBinding.revoked_at.is_(None),
                )
            )
            found.extend(
                BindingRef(market_id=market_id, vendor_id=vendor_id)
                for vendor_id in result.scalars().all()
            )
    return tuple(found)


async def stall_codes_by_vendor(
    session: AsyncSession,
    *,
    market_id: UUID,
    vendor_ids: list[UUID],
    business_date: date,
) -> dict[UUID, tuple[str, ...]]:
    """Sotuvchining SHU KUNDAGI rasta KODLARI — `pending_vendors` bilan BIR MANBA.

    ⛔ RASTA KODI SHAXSIY MA'LUMOT EMAS va u ATAYIN qaytariladi: sotuvchi
       botda «qaysi rasta uchun?» degan savolga javob ko'rmasa, qarz soni
       nizoda dalil bo'lolmasdi (D-02). Kod `stall_id` EMAS — 06-01 ning
       kontraktida tenglik uzgichi AYNAN kod (`billing_repo.
       _VENDOR_CHARGE_DUES` docstringi).

    ⚠ IKKI CHAQIRUVCHI, BITTA SO'ROV: `pending_vendors()` (admin
      ko'rinishi) va `/internal/bot/vendor/summary`. Ikkinchi nusxa
      «hozir biriktirilgan» ta'rifini ikkiga bo'lardi va bir yuzada
      tugagan biriktirish, ikkinchisida faol bo'lib ko'rinardi.
    """
    if not vendor_ids:
        return {}

    rows = (
        await session.execute(
            select(StallAssignment.vendor_id, Stall.code)
            .join(
                Stall,
                (Stall.market_id == StallAssignment.market_id)
                & (Stall.id == StallAssignment.stall_id),
            )
            .where(
                StallAssignment.market_id == market_id,
                StallAssignment.vendor_id.in_(vendor_ids),
                StallAssignment.period.contains(business_date),
            )
            .order_by(StallAssignment.vendor_id, Stall.code_sort, Stall.id)
        )
    ).all()

    collected: dict[UUID, list[str]] = {vendor_id: [] for vendor_id in vendor_ids}
    for row in rows:
        collected[UUID(str(row.vendor_id))].append(str(row.code))
    return {vendor_id: tuple(codes) for vendor_id, codes in collected.items()}


async def pending_vendors(
    session: AsyncSession,
    *,
    market_id: UUID,
    business_date: date,
    cursor: UUID | None = None,
    limit: int = PENDING_VENDORS_DEFAULT_LIMIT,
) -> PendingVendorPage:
    """D-26(a) NING ADMIN KO'RINISHI — bog'lanmagan sotuvchilar.

    ⛔ RO'YXAT «URINISHLAR» EMAS, SOTUVCHILAR: `vendors LEFT JOIN
       vendor_telegram_bindings ... AND revoked_at IS NULL` va
       `binding.id IS NULL`. Sabab modul docstringida (A5) — mos kelmagan
       urinishlar SAQLANMAYDI, ya'ni ulardan ro'yxat qurib bo'lmaydi va
       qurish ham kerak emas: adminga «kim hali ulanmagan?» kerak, «kim
       noto'g'ri raqam yuborgan?» emas.

    ⛔ JAVOBDA ISM/TELEFON YO'Q (`PendingVendor` docstringi, D-05).

    ⚠ `business_date` CHAQIRUVCHIDAN keladi (`headline_repo` naqshi):
      biznes-kun `Asia/Tashkent` bo'yicha hisoblanadi va uni SQL ichida
      qayta yozish ikkinchi manba tug'dirardi.

    ⚠ HTTP ISTE'MOLCHISI BU FAZADA YO'Q va bu KUTILGAN — «kutilmoqda
      ro'yxati» admin yuzasi keyingi rejaniki. Qoida BUGUN yoziladi,
      yuza keyin qo'shiladi (`billing_repo.vendor_charge_allocation()`
      bilan AYNAN bir xil naqsh va aynan bir xil sabab) — ⛔ ya'ni bu
      «o'lik kod» EMAS va o'chirilmaydi.
    """
    unbound = (
        select(Vendor.id.label("vendor_id"))
        .outerjoin(
            VendorTelegramBinding,
            (VendorTelegramBinding.market_id == Vendor.market_id)
            & (VendorTelegramBinding.vendor_id == Vendor.id)
            & (VendorTelegramBinding.revoked_at.is_(None)),
        )
        .where(Vendor.market_id == market_id, VendorTelegramBinding.id.is_(None))
    )
    if cursor is not None:
        unbound = unbound.where(Vendor.id > cursor)
    # `limit + 1` — keyingi sahifa BORMI degan savolga ikkinchi so'rovsiz
    # javob beradi (`stall_repo` ning keyset naqshi).
    unbound = unbound.order_by(Vendor.id).limit(limit + 1)

    vendor_ids = [UUID(str(row)) for row in (await session.execute(unbound)).scalars().all()]
    has_more = len(vendor_ids) > limit
    page_ids = vendor_ids[:limit]
    if not page_ids:
        return PendingVendorPage(items=(), next_cursor=None)

    by_vendor = await stall_codes_by_vendor(
        session, market_id=market_id, vendor_ids=page_ids, business_date=business_date
    )

    return PendingVendorPage(
        items=tuple(
            PendingVendor(vendor_id=vendor_id, stall_codes=by_vendor[vendor_id])
            for vendor_id in page_ids
        ),
        next_cursor=page_ids[-1] if has_more else None,
    )
