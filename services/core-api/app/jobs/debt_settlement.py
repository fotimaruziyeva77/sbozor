"""O'TGAN DAVR QARZLARINI YOPISH — buyurtmachi qarori bilan bir martalik amal (260925-kvq).

=============================================================================
⛔⛔ NEGA BU MODUL BOR.

2026-09-24: 28 kunlik hisob uzilishi `ops/scripts/backfill_charges.py`
bilan tiklandi (726 hisob). Kassir o'sha kunlarda pattani ko'rmagan edi,
ya'ni «qarz» ma'muriy tiklashning natijasi; `recon.open` esa ular uchun
«band, lekin to'lovsiz» ishlarini ochdi va xarita sarg'aydi. Buyurtmachi
qarori (2026-09-25): chegara kunidan OLDINGI qarzlar to'langan deb
hisoblansin, chegara kunidan boshlab tizim odatdagidek ishlasin.

Chaqiruvchi — `ops/scripts/settle_debts.py`. Cron EMAS va bo'lmaydi.

=============================================================================
UCH QOIDA — HAR BIRI MAVJUD MAHSULOT MEXANIZMIDAN:

  1. ⛔ SOXTA TO'LOV YOZILMAYDI. `payments` — kassaga tushgan pul: smena
     deklaratsiyasi, kassa daftari va kvitansiya undan o'qiydi. Qarz
     `charge_adjustments` orqali kamayadi (`decrease`, `director_waiver` —
     ekranda «Direktor kechirdi»), aktor — bozor direktori. Audit qatorini
     DB-trigger yozadi (`BILLING_AUDITED_TABLES`).

  2. ⛔ KREDIT CHEGARASI — TO'LOVNING O'Z KUNI (`business_date < before`),
     storno esa ASL to'lovning kuniga tegishli
     (`billing_repo._SETTLEMENT_CREDIT`). Chegara kuni va undan keyingi
     to'lovlar TEGILMAYDI — ular o'sha kunlarning pattasini yopadi; eski
     davrdan qolgan avans ham o'zgarmaydi.

  3. ⛔ QAYSI HISOB QANCHA KAMAYADI — `allocate_charge_credit()`
     (`FIFO_OLDEST_SERVICE_DATE_FIRST`). Eski kredit eng eski kunlarni
     yopadi va har hisobning YOPILMAGAN qoldig'i aynan shu summaga
     kamaytiriladi. Qoidaning ikkinchi nusxasi yozilmaydi.

Ishlar: chegara kunidan oldingi HAMMA hal qilinmagan (`new`/`in_review`)
ish `unjustified` («Asossiz») holatiga izoh bilan o'tadi —
`reconciliation_repo.transition()` orqali (tarix qatori + audit). «Asossiz»
— qarorning ma'nosi: «to'lovsiz» da'vosi tasdiqlanmadi, qarz to'langan deb
hisoblandi. Xarita sarig'i ikkala sinfdan ham chiqadi, ya'ni ikkalasi ham
yopiladi. Aniqlik ulushi `service_date` oynasida hisoblanadi — chegara
kunidan keyingi davr ko'rsatkichiga ta'sir yo'q.

=============================================================================
⛔ ATOMAR VA KONVERGENT. `settle_market()` commit QILMAYDI — tranzaksiya
   chaqiruvchida: yozish rejimi commit qiladi, quruq yugurish esa AYNI
   amalni bajarib ROLLBACK qiladi (hisobot — yozish natijasining o'zi,
   konstrayt va triggerlar ham o'lchanadi). Reja `pg_advisory_xact_lock`
   ICHIDA hisoblanadi: ikki parallel yugurish bir hisobni ikki marta
   kamaytira olmaydi (`director_waiver` da UNIQUE indeks yo'q — bir hisobga
   bir necha tuzatish qonuniy). Qayta yugurish hech narsa yozmaydi: qoldiq
   allaqachon nol. Yakuniy invariant buzilsa `SettlementInvariantError` —
   chaqiruvchi rollback qiladi.
=============================================================================
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from sbozor_core.billing import allocate_charge_credit
from sbozor_core.enums import ReconciliationCaseStatus, ReconciliationSubjectKind, Role
from sbozor_core.phone import normalize_phone
from sqlalchemy import Text, bindparam, text

from app.repositories import billing_repo, reconciliation_repo
from app.repositories.user_repo import UserRepository

if TYPE_CHECKING:
    from collections.abc import Sequence
    from datetime import date
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.repositories.billing_repo import SettlementCharge
    from app.repositories.reconciliation_repo import PendingCase
    from app.repositories.user_repo import MarketUser

__all__ = [
    "SETTLEMENT_CASE_STATUS",
    "MarketSettlementPlan",
    "SettlementInvariantError",
    "SettlementResult",
    "VendorSettlement",
    "Waiver",
    "market_directors",
    "pick_decision_maker",
    "plan_market_settlement",
    "settle_market",
    "settlement_note",
]

SETTLEMENT_CASE_STATUS: Final[str] = ReconciliationCaseStatus.UNJUSTIFIED.value
"""Yopilgan ishning holati — modul docstringidagi «Asossiz» bandi."""

_SETTLEMENT_LOCK = text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))").bindparams(
    bindparam("key", type_=Text())
)
"""Bozor boshiga tranzaksiya qulfi — commit/rollback bilan o'zi bo'shaydi."""


class SettlementInvariantError(RuntimeError):
    """Yozishdan keyingi tekshiruv buzildi — chaqiruvchi ROLLBACK qilishi SHART."""


@dataclass(frozen=True, slots=True)
class Waiver:
    """Bitta hisobning kechiriladigan qoldig'i."""

    charge_id: UUID
    vendor_id: UUID
    service_date: date
    stall_code: str
    amount_soum: int


@dataclass(frozen=True, slots=True)
class VendorSettlement:
    """Bitta sotuvchining eski davri — hisobot qatori."""

    vendor_id: UUID
    old_due_soum: int
    """Chegara kunidan oldingi hisoblar (mavjud tuzatishlar bilan netlangan)."""
    old_credit_soum: int
    """Chegara kunidan oldin yozilgan to'lovlar (stornolar ayirilgan)."""
    waived_soum: int
    waived_charges: int
    advance_soum: int
    """Eski krediti eski hisoblardan ortgan qismi — O'ZGARMAYDI, oldinga o'tadi."""
    new_credit_soum: int
    """Chegara kuni va undan keyingi to'lovlar — TEGILMAYDI (faqat ma'lumot)."""


@dataclass(frozen=True, slots=True)
class MarketSettlementPlan:
    """Bir bozor uchun nima yoziladi — hali hech narsa yozilmagan."""

    market_id: UUID
    before: date
    vendors: tuple[VendorSettlement, ...]
    waivers: tuple[Waiver, ...]
    cases: tuple[PendingCase, ...]

    @property
    def waived_soum(self) -> int:
        return sum(waiver.amount_soum for waiver in self.waivers)

    @property
    def is_empty(self) -> bool:
        return not self.waivers and not self.cases


@dataclass(frozen=True, slots=True)
class SettlementResult:
    """`settle_market()` natijasi — reja va HAQIQATAN yozilgan qatorlar soni."""

    plan: MarketSettlementPlan
    adjustments_written: int
    cases_closed: int


def settlement_note(before: date, subject_kind: str) -> str:
    """Yopilgan ishning izohi — tarix qatori va yechim matni (direktor o'qiydi)."""
    day = before.strftime("%d.%m.%Y")
    if subject_kind == ReconciliationSubjectKind.OCCUPIED_UNPAID.value:
        return (
            f"Direktor qarori: {day} dan oldingi kunlarning qarzlari to'langan deb "
            "hisoblandi (to'lanmagan qoldiq «Direktor kechirdi» tuzatishi bilan yopildi)."
        )
    return (
        f"Direktor qarori: {day} dan oldingi nomuvofiqliklar yopildi — hisob shu kundan "
        "qaytadan yuritiladi."
    )


async def plan_market_settlement(
    session: AsyncSession, *, market_id: UUID, before: date
) -> MarketSettlementPlan:
    """Reja — faqat O'QIYDI. Sessiyada tenant konteksti o'rnatilgan bo'lishi shart."""
    charges = await billing_repo.settlement_charge_dues(session, market_id=market_id, before=before)
    credits = await billing_repo.settlement_credit(session, market_id=market_id, before=before)

    by_vendor: dict[UUID, list[SettlementCharge]] = defaultdict(list)
    for charge in charges:
        by_vendor[charge.vendor_id].append(charge)

    vendors: list[VendorSettlement] = []
    waivers: list[Waiver] = []
    for vendor_id in sorted(set(by_vendor) | set(credits), key=str):
        own = by_vendor.get(vendor_id, [])
        credit = credits.get(vendor_id)
        credit_before = credit.before_soum if credit is not None else 0
        credit_since = credit.since_soum if credit is not None else 0

        by_key = {(item.due.service_date, item.due.stall_code): item for item in own}
        if len(by_key) != len(own):
            # `allocate_charge_credit()` natijasi `(kun, rasta kodi)` bilan
            # qaytadi; takror kalit qoldiqni NOTO'G'RI hisobga yozdirardi.
            raise SettlementInvariantError(
                f"sotuvchi {vendor_id}: bir kunda bir xil kodli ikki hisob bor — "
                "kechirish qaysi hisobga yozilishini aniqlab bo'lmaydi"
            )
        broken = [item for item in own if item.due.due_soum < 0]
        if broken:
            # `allocate_charge_credit()` uni `ValueError` bilan rad etardi —
            # sabab ma'lumotda, tuzatishni inson ko'rishi kerak.
            raise SettlementInvariantError(
                f"sotuvchi {vendor_id}: {broken[0].due.service_date} / "
                f"{broken[0].due.stall_code} hisobining nettosi allaqachon manfiy"
            )

        allocation = allocate_charge_credit([item.due for item in own], credit_before)
        own_waivers = [
            Waiver(
                charge_id=by_key[(row.service_date, row.stall_code)].charge_id,
                vendor_id=vendor_id,
                service_date=row.service_date,
                stall_code=row.stall_code,
                amount_soum=row.unpaid_soum,
            )
            for row in allocation.rows
            if row.unpaid_soum > 0
        ]
        waivers.extend(own_waivers)
        vendors.append(
            VendorSettlement(
                vendor_id=vendor_id,
                old_due_soum=sum(item.due.due_soum for item in own),
                old_credit_soum=credit_before,
                waived_soum=sum(waiver.amount_soum for waiver in own_waivers),
                waived_charges=len(own_waivers),
                advance_soum=allocation.advance_soum,
                new_credit_soum=credit_since,
            )
        )

    cases = await reconciliation_repo.pending_cases_before(
        session, market_id=market_id, before=before
    )
    return MarketSettlementPlan(
        market_id=market_id,
        before=before,
        vendors=tuple(vendors),
        waivers=tuple(waivers),
        cases=tuple(cases),
    )


async def settle_market(
    session: AsyncSession, *, market_id: UUID, before: date, actor_user_id: UUID
) -> SettlementResult:
    """Qulf -> reja -> yozish -> tekshiruv. ⛔ COMMIT QILMAYDI (modul docstringi).

    Sessiyada tenant konteksti `actor_id = actor_user_id` bilan o'rnatilgan
    bo'lishi shart — audit triggeri aktorni o'sha GUC'dan o'qiydi.
    """
    await session.execute(_SETTLEMENT_LOCK, {"key": f"debt_settlement:{market_id}"})
    plan = await plan_market_settlement(session, market_id=market_id, before=before)

    for waiver in plan.waivers:
        await billing_repo.write_director_waiver(
            session,
            market_id=market_id,
            charge_id=waiver.charge_id,
            amount_soum=waiver.amount_soum,
            actor_user_id=actor_user_id,
        )
    for case in plan.cases:
        await reconciliation_repo.transition(
            session,
            market_id=market_id,
            case_id=case.case_id,
            to_status=SETTLEMENT_CASE_STATUS,
            actor_user_id=actor_user_id,
            note=settlement_note(before, case.subject_kind),
        )

    await _verify_settled(session, market_id=market_id, before=before)
    return SettlementResult(
        plan=plan, adjustments_written=len(plan.waivers), cases_closed=len(plan.cases)
    )


async def _verify_settled(session: AsyncSession, *, market_id: UUID, before: date) -> None:
    """Yozishdan keyin: eski qarz qolmagan, manfiy hisob yo'q, ochiq eski ish yo'q."""
    negative = [
        charge
        for charge in await billing_repo.settlement_charge_dues(
            session, market_id=market_id, before=before
        )
        if charge.due.due_soum < 0
    ]
    if negative:
        raise SettlementInvariantError(
            f"{len(negative)} ta hisobning nettosi manfiy bo'lib qoldi "
            f"(masalan {negative[0].due.service_date} / {negative[0].due.stall_code}) — "
            "parallel tuzatish yozilgan bo'lishi mumkin"
        )

    outstanding = await billing_repo.vendor_outstanding(session, market_id=market_id, as_of=before)
    debtors = {vendor_id: soum for vendor_id, soum in outstanding.items() if soum > 0}
    if debtors:
        raise SettlementInvariantError(
            f"{len(debtors)} ta sotuvchida {before} dan oldingi qarz qoldi: "
            f"jami {sum(debtors.values())} so'm"
        )

    left = await reconciliation_repo.pending_cases_before(
        session, market_id=market_id, before=before
    )
    if left:
        raise SettlementInvariantError(f"{len(left)} ta eski ish hal qilinmagan holda qoldi")


async def market_directors(session: AsyncSession, *, market_id: UUID) -> list[MarketUser]:
    """Bozorning FAOL direktorlari — kechirish qarorining egasi shular orasidan."""
    members = await UserRepository(session, market_id).list_members()
    return [
        member for member in members if member.is_active and Role.DIRECTOR.value in member.roles
    ]


def pick_decision_maker(directors: Sequence[MarketUser], phone: str | None) -> MarketUser:
    """Qaror egasini tanlaydi — taxmin QILMAYDI.

    Telefon berilsa — aynan o'sha direktor; berilmasa — bozorda yagona faol
    direktor bo'lishi shart. Aks holda `LookupError`: tuzatish qatorida
    noto'g'ri odam «qaror qildi» deb yozilgani nizoda yolg'on dalil bo'lardi.
    """
    if not directors:
        raise LookupError("bozorda faol direktor yo'q — kechirish qarorining egasi topilmadi")
    candidates = ", ".join(f"{d.full_name or '?'} {d.phone}" for d in directors)
    if phone is not None:
        wanted = normalize_phone(phone)
        for director in directors:
            if director.phone == wanted:
                return director
        raise LookupError(f"{wanted} faol direktorlar orasida yo'q (bor: {candidates})")
    if len(directors) == 1:
        return directors[0]
    raise LookupError(
        f"bozorda {len(directors)} ta faol direktor bor ({candidates}) — qaror egasini "
        "telefon raqami bilan ko'rsating"
    )
