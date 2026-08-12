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
⛔ ERTA `break` YO'Q — VA BU XAVFSIZLIK QARORI, OPTIMIZATSIYA EMAS
   (T-07-40).

D-26(a) javobi neytral, lekin JAVOB VAQTI bo'yicha ajratish mumkin
bo'lardi: moslik topilganda tsikl erta tugasa, «raqam reyestrda bormi?»
savoliga TAYMING javob berardi va cheksiz `contact` yuborish reyestrni
tashqaridan sanash yo'lini ochardi. Shuning uchun tsikl HAR DOIM barcha
faol bozorlarni oxirigacha aylanadi.

⚠ Ikkinchi qatlam — `POST /internal/bot/resolve` dagi rate-limit
  (`telegram_user_id` kesimida). Bittasi ham yolg'iz yetarli emas: tayming
  yopilmasa cheksiz urinish tayming farqini statistik ravishda ochardi,
  rate-limit bo'lmasa esa tsiklning O'ZI (bozorlar soni o'sganda)
  sekinlashib, farq yana ko'rinardi.

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
from sbozor_core.enums import ActorKind, AuditAction
from sbozor_core.models import Stall, StallAssignment, Vendor, VendorTelegramBinding
from sbozor_core.phone import InvalidPhoneError, normalize_phone
from sbozor_core.tenancy import set_tenant_context
from sqlalchemy import func, select, update

from app.jobs.alerting import raise_alert
from app.jobs.retention import active_market_ids
from app.security.audit import write_app_audit

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

__all__ = [
    "VENDOR_BINDING_CONFLICT_ALERT_KEY",
    "BindingRef",
    "PendingVendor",
    "PendingVendorPage",
    "ResolveOutcome",
    "ResolveStatus",
    "VendorRef",
    "active_bindings",
    "bind",
    "pending_vendors",
    "resolve",
    "revoke",
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


# ===========================================================================
# Tranzaksiya chegarasi
# ===========================================================================


@asynccontextmanager
async def _tenant_session(
    sessionmaker: async_sessionmaker[AsyncSession],
    *,
    market_id: UUID,
    request_id: str | None,
) -> AsyncIterator[AsyncSession]:
    """Tenant konteksti O'RNATILGAN qisqa tranzaksiya.

    ⚠ NUSXA EMAS, JUFT — VA BU FARQ `active_market_ids()` DAN ATAYIN
      AJRATILGAN. `app/jobs/retention.py::active_market_ids` docstringi
      ikkalasini ochiq ajratadi: chetlab o'tuvchi so'rov (`SECURITY
      DEFINER`) TAKRORLANMAYDI va import qilinadi, `_tenant_session` esa
      xavfsizlik YUZASI emas, STRUKTURAVIY naqsh va u `discovery.py`,
      `capture.py`, `retention.py`, `alerting.py` da ATAYIN takrorlangan
      (modul hech kimga bog'lanmasligi uchun). Bu — beshinchi nusxa.

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
        async with _tenant_session(
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
    async with _tenant_session(
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
        async with _tenant_session(
            sessionmaker, market_id=market_id, request_id=request_id
        ) as session:
            await raise_alert(session, market_id=market_id, key=VENDOR_BINDING_CONFLICT_ALERT_KEY)

    log.warning(
        "bot_resolve_multiple_matches",
        telegram_user_id=telegram_user_id,
        market_count=len({match.market_id for match in matches}),
    )


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
) -> None:
    """Faol bog'lanishni BEKOR QILADI va audit qatorini yozadi.

    ⛔ ESKI QATOR O'CHIRILMAYDI (append-only, D-20 sinfi). `DELETE` yozish
       «eski bog'lanish qachon, nega bekor qilindi?» savolini javobsiz
       qoldirardi — holbuki aynan shu savol nizoda (D-02) «xabar kimga
       ketgan edi?» degan javobni beradi. Jadvalning O'Z docstringi
       (`models/notification.py::VendorTelegramBinding`) buni TARIX deb
       ta'riflaydi.
    """
    await session.execute(
        update(VendorTelegramBinding)
        .where(
            VendorTelegramBinding.market_id == market_id,
            VendorTelegramBinding.id == binding_id,
        )
        .values(revoked_at=func.now(), revoked_reason=reason)
    )
    await write_app_audit(
        session,
        action=AuditAction.UPDATE,
        table_name=VendorTelegramBinding.__tablename__,
        row_id=binding_id,
        old={"revoked_at": None, "revoked_reason": None},
        new={"revoked_at": "now()", "revoked_reason": reason},
        market_id=market_id,
        actor_kind=ActorKind.SYSTEM,
        actor_label="bot",
    )
    log.info(
        "vendor_binding_revoked",
        market_id=str(market_id),
        vendor_id=str(vendor_id),
        telegram_user_id=telegram_user_id,
        reason=reason,
    )


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
        async with _tenant_session(
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

    codes = (
        await session.execute(
            select(StallAssignment.vendor_id, Stall.code)
            .join(
                Stall,
                (Stall.market_id == StallAssignment.market_id)
                & (Stall.id == StallAssignment.stall_id),
            )
            .where(
                StallAssignment.market_id == market_id,
                StallAssignment.vendor_id.in_(page_ids),
                StallAssignment.period.contains(business_date),
            )
            .order_by(StallAssignment.vendor_id, Stall.code_sort, Stall.id)
        )
    ).all()

    by_vendor: dict[UUID, list[str]] = {vendor_id: [] for vendor_id in page_ids}
    for row in codes:
        by_vendor[UUID(str(row.vendor_id))].append(str(row.code))

    return PendingVendorPage(
        items=tuple(
            PendingVendor(vendor_id=vendor_id, stall_codes=tuple(by_vendor[vendor_id]))
            for vendor_id in page_ids
        ),
        next_cursor=page_ids[-1] if has_more else None,
    )
