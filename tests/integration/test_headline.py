"""`GET /me/headline` va uning repozitoriysi — BITTA SON, BITTA KALIT (RECON-06).

=============================================================================
⛔⛔ BU FAYLNING ENG QIMMAT DA'VOSI PUL HAQIDA VA U XULQIY O'LCHANADI.

Pitfall 1: RECON-06 kassirga «bugungi yig'im» ni va'da qiladi, CASH-04 esa
kassir tizim summasini BILMASLIGIGA tayanadi. Ikkalasi bir vaqtda rost
bo'la olmaydi va 6-faza ikkinchisini UCH MUSTAQIL QATLAMDA qurgan
(T-06-53, T-06-59, `shifts.py:126`).

Shuning uchun darvoza «maydon nomi `_soum` bilan tugamasin» degan MATN
tekshiruvi EMAS. U kassir sessiyasi bilan chaqirib, qaytgan `value` ni
o'sha kunning HAQIQIY summasi bilan solishtiradi va ularning TENG
EMASLIGINI talab qiladi. Seed ataylab `soni != summasi` bo'ladigan qilib
qurilgan — teng bo'lsa da'vo hech nimani isbotlamasdi.
=============================================================================

⛔ IKKINCHI DA'VO — JAVOB YUZASINING TO'PLAM TENGLIGI (D-29).
   `set(response.json()) == {"metric", "value"}` — `len()` EMAS va
   `"x" not in ...` EMAS. Inkor tasdiq faqat SANAB O'TILGAN nomni
   ushlaydi; uchinchi maydon boshqa nom bilan jimgina qo'shilardi
   (T-06-75 da o'rnatilgan qoida).

⚠ TEST NOMLARIDAGI `repo` BO'LAGI — TANLAGICH. 07-03 rejasining 1-vazifasi
  `pytest -k repo` bilan yugurtiriladi, ya'ni repozitoriy qatlamining
  testlari HTTP qatlamidan nom bo'yicha ajraladi. Shu sababdan HTTP
  testlarining nomlarida `report` so'zi ISHLATILMAYDI — u `repo` ni o'z
  ichiga oladi va tanlagichni jimgina buzardi.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from app.repositories import headline_repo
from app.repositories.review_repo import ReviewRepository
from fixtures.billing_domain import (
    BillingDomainSeed,
    add_payment,
    billing_domain_before_day_close,
)
from fixtures.market_domain import MarketDomainSeed
from fixtures.nvr_domain import nvr_rows
from fixtures.occupancy_domain import OccupancyDomainSeed, occupancy_rows
from fixtures.snapshot_domain import snapshot_rows
from fixtures.two_markets import TwoMarketSeed
from sbozor_core.enums import PaymentKind, ReversalReason, ReviewQueueKind

if TYPE_CHECKING:
    from collections.abc import Iterator
    from datetime import date
    from uuid import UUID

    from fixtures import TenantSessionFactory
    from fixtures.auth_users import AuthSeed
    from psycopg import Connection
    from psycopg.rows import TupleRow

PUBLIC_REPO_FUNCTIONS = frozenset(
    {"receipts_written_count", "review_queue_count", "revenue_today_soum"}
)
"""`headline_repo` ning OMMAVIY yuzasi — ⛔ RO'YXAT QO'LDA YOZILGAN.

Uni moduldan hosila qilish («modul o'ziga teng») testni tavtologiyaga
aylantirardi. Bu yerda u KUTILGAN NATIJA: modulga qo'shilgan to'rtinchi
ommaviy nom — ongli qaror va u shu qatorni tahrirlashni talab qiladi.
"""

RECEIPT_AMOUNTS = (7_000, 11_000, 13_000)
"""Uch to'lovning summalari — ⛔ SONI (3) BILAN TENG BO'LMAGAN yig'indi.

Bu tanlov emas, Pitfall 1 darvozasining SHARTI: agar seed `1 so'm × 3`
bo'lganda yig'indi ham, sanoq ham `3` chiqardi va «kassir summani
ko'rmaydi» da'vosi TRIVIAL ravishda o'tib ketardi. Uch qiymat ham
har xil — bittasi storno bilan bekor qilinganda qolgan ikkitasining
yig'indisi ham sanoqqa teng kelmaydi.
"""

REVERSED_INDEX = 0
"""Qaysi to'lov storno qilinadi — birinchisi (`RECEIPT_AMOUNTS[0]`)."""


class Env:
    """Billing + bandlik qatlamlari va ularning kaliti — bitta obyektda."""

    def __init__(
        self,
        base: TwoMarketSeed,
        billing: BillingDomainSeed,
        occupancy: OccupancyDomainSeed,
        auth: AuthSeed,
        conn: Connection[TupleRow],
        today: date,
    ) -> None:
        self.base = base
        self.billing = billing
        self.occupancy = occupancy
        self.auth = auth
        self.conn = conn
        self.today = today

    @property
    def market_id(self) -> UUID:
        return self.billing.market_a.market_id

    @property
    def cashier_id(self) -> UUID:
        return self.billing.market_a.cashier_id

    @property
    def director_id(self) -> UUID:
        return self.base.market_a.director_user_id

    @property
    def vendor_id(self) -> UUID:
        return self.billing.market_a.vendor_id

    @property
    def shift_id(self) -> UUID:
        return self.billing.market_a.open_shift_id

    @property
    def stall_id(self) -> UUID:
        """To'lov osiladigan rasta — `None` bo'lsa NAZORAT bilan yiqiladi."""
        stall_id = self.billing.market_a.stall_with_two_occupied_slots
        assert stall_id is not None, "nazorat: seedda `stall_with_two_occupied_slots` yo'q"
        return stall_id

    @property
    def seed_assignment(self) -> UUID:
        """Seed'dagi JAVOBSIZ noaniq navbat yozuvi."""
        assignment_id = self.occupancy.market_a.uncertain_assignment_id
        assert assignment_id is not None, "seed'da javobsiz noaniq yozuv yo'q"
        return assignment_id

    # ------------------------------------------------------------------
    # Yozuvchi yordamchilar
    # ------------------------------------------------------------------

    def add_receipt(self, amount_soum: int, *, cashier_id: UUID | None = None) -> UUID:
        """BUGUNGI kun uchun bitta to'lov qatori."""
        return add_payment(
            self.conn,
            market_id=self.market_id,
            stall_id=self.stall_id,
            vendor_id=self.vendor_id,
            cashier_id=cashier_id if cashier_id is not None else self.cashier_id,
            shift_id=self.shift_id if cashier_id is None else None,
            service_date=self.today,
            amount_soum=amount_soum,
            quote_soum=amount_soum,
        )

    def reverse(self, payment_id: UUID, amount_soum: int) -> UUID:
        """Storno qatori — ⛔ asl qator TAHRIRLANMAYDI (D-23)."""
        return add_payment(
            self.conn,
            market_id=self.market_id,
            stall_id=self.stall_id,
            vendor_id=self.vendor_id,
            cashier_id=self.cashier_id,
            shift_id=self.shift_id,
            service_date=self.today,
            amount_soum=amount_soum,
            quote_soum=amount_soum,
            kind=PaymentKind.REVERSAL.value,
            reverses_payment_id=payment_id,
            reversal_reason=ReversalReason.WRONG_AMOUNT.value,
        )

    def seed_day(self) -> tuple[int, int]:
        """Uch to'lov + bitta storno. Qaytadi: `(kutilgan_summa, kutilgan_sanoq)`.

        ⚠ NAZORAT ASSERTI BILAN BOSHLANADI: kun BO'SH bo'lishi shart. Seed
          allaqachon to'lov yozgan bo'lsa kutilgan sonlar noto'g'ri
          bo'lardi va test o'z arifmetikasini emas, seedning qoldig'ini
          o'lchagan bo'lardi.
        """
        assert self.day_total() == 0, (
            "nazorat: kun bo'sh emas — billing seed'i to'lov yozib qo'ygan va "
            "bu faylning kutilgan sonlari noto'g'ri bo'lardi"
        )

        payment_ids = [self.add_receipt(amount) for amount in RECEIPT_AMOUNTS]
        self.reverse(payment_ids[REVERSED_INDEX], RECEIPT_AMOUNTS[REVERSED_INDEX])

        expected_total = sum(RECEIPT_AMOUNTS) - RECEIPT_AMOUNTS[REVERSED_INDEX]
        expected_count = len(RECEIPT_AMOUNTS)
        return expected_total, expected_count

    def day_total(self) -> int:
        """Kunning HAQIQIY summasi — ⛔ TESTNING O'Z SQL'i, mahsulotniki EMAS.

        ⚠ Bu ATAYIN `headline_repo.revenue_today_soum()` ni chaqirmaydi:
          Pitfall 1 darvozasi kassirning sonini HAQIQIY summa bilan
          solishtiradi va ikkalasini bitta funksiyadan olish «funksiya
          o'ziga teng» degan tavtologiya bo'lardi.
        """
        row = self.conn.execute(
            "SELECT COALESCE(sum(CASE WHEN kind = 'reversal' THEN -amount_soum "
            "ELSE amount_soum END), 0) FROM payments "
            "WHERE market_id = %s AND service_date = %s",
            (str(self.market_id), self.today),
        ).fetchone()
        assert row is not None
        return int(row[0])

    def answer(self, assignment_id: UUID, *, queue_kind: str) -> None:
        """Topshiriqqa javob yozadi — ⛔ navbatdan CHIQARISHNING mahsulot yo'li.

        `review_assignments` dan `DELETE` qilish YO'LI ISHLATILMAYDI: u
        navbat a'zoligini boshqa mexanizm bilan o'zgartirardi va
        `NOT EXISTS (zone_reviews)` predikati umuman sinalmasdi.
        """
        self.conn.execute(
            "INSERT INTO zone_reviews (market_id, review_assignment_id, queue_kind, "
            "shown_ai_verdict, human_verdict, reviewer_id) "
            "VALUES (%s, %s, %s, false, 'occupied', %s)",
            (
                str(self.market_id),
                str(assignment_id),
                queue_kind,
                str(self.base.market_a.admin_user_id),
            ),
        )

    def drop_review(self, assignment_id: UUID) -> None:
        """Seed'dagi javobni olib tashlaydi — ⛔ QORALAMA BOZOR istisnosi orqali.

        `zone_reviews` SHARTSIZ o'zgarmas (`trg_zone_review_immutable`):
        oddiy `DELETE` `P0001` bilan rad etiladi va bu TO'G'RI — insonning
        moliyaviy oqibatli qarori o'chirilmasligi kerak. Yagona yo'l —
        bozorni qoralamaga tushirish; `cleanup_occupancy_domain()` va
        `test_uncertain_queue.py::_delete_review` AYNAN shu mexanizmni
        ishlatadi. Bayroq DARHOL qaytariladi.
        """
        market = str(self.market_id)
        self.conn.execute("UPDATE markets SET is_active = false WHERE id = %s", (market,))
        self.conn.execute(
            "DELETE FROM zone_reviews WHERE market_id = %s AND review_assignment_id = %s",
            (market, str(assignment_id)),
        )
        self.conn.execute("UPDATE markets SET is_active = true WHERE id = %s", (market,))

    def pending_assignments(self, *, queue_kind: str) -> list[UUID]:
        """Javobsiz topshiriqlar — NAZORAT ro'yxati (mahsulot so'rovidan MUSTAQIL)."""
        rows = self.conn.execute(
            "SELECT ra.id FROM review_assignments ra "
            "WHERE ra.market_id = %s AND ra.queue_kind = %s "
            "  AND NOT EXISTS (SELECT 1 FROM zone_reviews zr "
            "                   WHERE zr.review_assignment_id = ra.id)",
            (str(self.market_id), queue_kind),
        ).fetchall()
        return [row[0] for row in rows]


@pytest.fixture
def env(
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    auth_seed: AuthSeed,
    market_domain: MarketDomainSeed,
    market_today: date,
    migrated: None,
) -> Iterator[Env]:
    """To'rt qatlamli seed; to'lovlar TESTDAN KEYIN `market_id` bo'yicha o'chadi.

    ⚠ `auth_seed` `market_domain` DAN OLDIN so'raladi va bu ATAYIN
      (`test_uncertain_queue.py::env` da o'rnatilgan qoida): pytest
      fixture'larni teskari tartibda yopadi, ya'ni nazoratchi
      foydalanuvchisi `zone_reviews` qatorlaridan KEYIN o'chiriladi.
      Teskari tartibda `fk_zone_reviews_reviewer_id_users` (`ondelete`
      YO'Q) tozalashni yiqitardi.

    ⚠ TO'LOVLARNI SEED O'CHIRA OLMAYDI: ular test ichida yoziladi va
      seed ularning identifikatorlarini BILMAYDI. Tozalash `market_id`
      bo'yicha va u `cleanup_billing_domain()` DAN OLDIN bajariladi
      (`test_payments_api.py::env` naqshi).
    """
    with (
        nvr_rows(sync_owner_conn, two_markets) as nvr,
        snapshot_rows(sync_owner_conn, nvr) as snaps,
        occupancy_rows(sync_owner_conn, two_markets, market_domain, snaps) as occupancy,
        billing_domain_before_day_close(
            sync_owner_conn, two_markets, market_domain, occupancy
        ) as billing,
    ):
        market_id = billing.market_a.market_id
        try:
            yield Env(two_markets, billing, occupancy, auth_seed, sync_owner_conn, market_today)
        finally:
            sync_owner_conn.execute(
                "UPDATE markets SET is_active = false WHERE id = %s", (str(market_id),)
            )
            sync_owner_conn.execute("DELETE FROM payments WHERE market_id = %s", (str(market_id),))
            sync_owner_conn.execute(
                "UPDATE markets SET is_active = true WHERE id = %s", (str(market_id),)
            )


# ===========================================================================
# 1. MODULNING OMMAVIY YUZASI — struktura, xulq emas
# ===========================================================================


def test_repo_module_exposes_exactly_three_public_functions() -> None:
    """⛔ `headline_repo` da AYNAN uchta ommaviy nom bor — TO'PLAM TENGLIGI.

    =======================================================================
    ⛔⛔ BU KOSMETIKA EMAS — U PUL YO'LINI STRUKTURAVIY YOPADI.

    Bu modul kassir sessiyasiga xizmat qiladigan yagona o'qish manbai.
    Unga `from app.repositories.payment_repo import shift_system_total`
    qatorini qo'shish YETARLI bo'lardi: o'shanda marshrut
    `headline_repo.shift_system_total(...)` ni chaqira olardi va
    6-fazaning uch qatlamli ko'rligi BITTA import bilan chetlab o'tilardi.

    Shuning uchun moduldagi HAR BIR import pastki chiziq bilan
    aliaslangan va bu test o'sha intizomni qulflaydi. `from __future__
    import annotations` ham shu sababdan yo'q — u modulga `annotations`
    nomini bog'lab qo'yadi (o'lchandi).

    ⚠ TENGLIK, «kamida uchtasi» EMAS: kamayish ham qizartiradi, ya'ni
      funksiyani jimgina olib tashlab bo'lmaydi.
    =======================================================================
    """
    public = {name for name in dir(headline_repo) if not name.startswith("_")}

    assert public == PUBLIC_REPO_FUNCTIONS, (
        "`headline_repo` ning ommaviy yuzasi o'zgardi.\n"
        f"  topildi:  {sorted(public)}\n"
        f"  kutilgan: {sorted(PUBLIC_REPO_FUNCTIONS)}\n"
        "Yangi import qo'shilgan bo'lsa uni `_` bilan aliaslang — aks holda "
        "modul orqali begona funksiyaga yo'l ochiladi (Pitfall 1)."
    )


# ===========================================================================
# 2. PUL — belgili yig'indi (`REPORT_VIEW` ko'rsatkichi)
# ===========================================================================


async def test_repo_revenue_today_is_the_signed_sum_of_the_day(
    env: Env, tenant_session: TenantSessionFactory
) -> None:
    """Kunlik tushum — storno MANFIY hisoblanadi (C-5).

    NAZORAT JUFTI ICHKARIDA: kutilgan qiymat `sum(RECEIPT_AMOUNTS)` DAN
    KICHIK bo'lishi ham tasdiqlanadi. Usiz `kind` filtri butunlay
    yo'qolgan holatda ham test yashil qolardi.
    """
    expected_total, _ = env.seed_day()

    async with tenant_session(env.market_id) as session:
        actual = await headline_repo.revenue_today_soum(
            session, market_id=env.market_id, business_date=env.today
        )

    assert actual == expected_total
    assert actual < sum(RECEIPT_AMOUNTS), (
        "storno yig'indidan AYIRILMADI — `kind = 'reversal'` shoxi ishlamayapti"
    )


async def test_repo_revenue_today_is_zero_on_a_day_without_payments(
    env: Env, tenant_session: TenantSessionFactory
) -> None:
    """To'lovsiz kun — ⛔ `0`, `None` EMAS (`COALESCE`).

    `None` klientda «ko'rsatkich yo'q» bo'lib chiqardi, holbuki «bugun hali
    to'lov yo'q» — O'LCHANGAN javob. Ikkisini aralashtirish D-20 ning
    aynan mantiqi: o'lchov asbobining YO'QLIGI nol natija bilan bir xil
    ko'rinardi.
    """
    async with tenant_session(env.market_id) as session:
        actual = await headline_repo.revenue_today_soum(
            session, market_id=env.market_id, business_date=env.today
        )

    assert actual == 0


# ===========================================================================
# 3. KASSIR — SANOQ, SUMMA EMAS (Pitfall 1)
# ===========================================================================


async def test_repo_receipts_written_counts_rows_and_skips_reversals(
    env: Env, tenant_session: TenantSessionFactory
) -> None:
    """Uch to'lov + bitta storno -> **3**.

    ⛔ Storno SANOQQA KIRMAYDI va sabab arifmetik emas, MA'NOVIY: bekor
       qilingan kvitansiya «yozilgan ish» emas. Belgili yig'indi qoidasi
       (`reversal` -> manfiy) bu yerda ISHLAMAYDI — u pul uchun.
    """
    _, expected_count = env.seed_day()

    async with tenant_session(env.market_id) as session:
        actual = await headline_repo.receipts_written_count(
            session,
            market_id=env.market_id,
            business_date=env.today,
            cashier_id=env.cashier_id,
        )

    assert actual == expected_count


async def test_repo_receipts_written_is_never_the_money_total(
    env: Env, tenant_session: TenantSessionFactory
) -> None:
    """⛔⛔ PITFALL 1 NING REPOZITORIY DARAJASIDAGI DARVOZASI.

    =======================================================================
    Da'vo: kassirga qaytadigan son o'sha kunning HAQIQIY summasiga TENG
    EMAS. Solishtiruv `env.day_total()` bilan — ya'ni testning O'Z SQL'i
    bilan, mahsulot funksiyasi bilan emas (`day_total()` docstringi).

    Sabotaj: `count(*)` ni `sum(amount_soum)` ga almashtirish bu testni
    DARHOL qizartiradi. `RECEIPT_AMOUNTS` ataylab shunday tanlangan —
    seed `1 so'm × 3` bo'lganda ikkala son ham `3` chiqardi va da'vo
    trivial ravishda o'tib ketardi.
    =======================================================================
    """
    expected_total, expected_count = env.seed_day()
    assert expected_total != expected_count, (
        "nazorat: seed summa va sanoqni TENG qilib qo'ygan — bu holatda "
        "pastdagi da'vo hech nimani isbotlamaydi"
    )

    async with tenant_session(env.market_id) as session:
        value = await headline_repo.receipts_written_count(
            session,
            market_id=env.market_id,
            business_date=env.today,
            cashier_id=env.cashier_id,
        )

    assert value != env.day_total(), (
        "kassirning ko'rsatkichi kun SUMMASIGA teng chiqdi — u smena yopishda "
        "aynan shu sonni deklaratsiya qilardi va variance HAR DOIM nol bo'lardi "
        "(CASH-04 / Pitfall 1)"
    )
    assert value == expected_count


async def test_repo_receipts_written_only_counts_the_asking_cashier(
    env: Env, tenant_session: TenantSessionFactory
) -> None:
    """Boshqa odam yozgan to'lov SANOQQA KIRMAYDI.

    Direktor smenasiz to'lov kiritishi MUMKIN (OQ-6/A5) va o'sha qator
    kassirning kunini shishirmasligi kerak: ko'rsatkich «men bugun
    nechta patta yozdim» degan savolga javob beradi, «bozorda nechta
    patta yozildi» degan savolga emas.
    """
    _, expected_count = env.seed_day()
    env.add_receipt(19_000, cashier_id=env.director_id)

    async with tenant_session(env.market_id) as session:
        mine = await headline_repo.receipts_written_count(
            session,
            market_id=env.market_id,
            business_date=env.today,
            cashier_id=env.cashier_id,
        )
        theirs = await headline_repo.receipts_written_count(
            session,
            market_id=env.market_id,
            business_date=env.today,
            cashier_id=env.director_id,
        )

    assert mine == expected_count
    assert theirs == 1


async def test_repo_receipts_written_is_scoped_to_the_given_day(
    env: Env, tenant_session: TenantSessionFactory
) -> None:
    """KECHAGI to'lov bugungi sanoqqa kirmaydi — NAZORAT jufti bilan."""
    _, expected_count = env.seed_day()
    yesterday_payment = add_payment(
        env.conn,
        market_id=env.market_id,
        stall_id=env.stall_id,
        vendor_id=env.vendor_id,
        cashier_id=env.cashier_id,
        shift_id=env.shift_id,
        amount_soum=23_000,
        quote_soum=23_000,
    )
    assert yesterday_payment is not None

    async with tenant_session(env.market_id) as session:
        actual = await headline_repo.receipts_written_count(
            session,
            market_id=env.market_id,
            business_date=env.today,
            cashier_id=env.cashier_id,
        )

    assert actual == expected_count


# ===========================================================================
# 4. NAZORATCHI NAVBATI — predikat `review_repo` NIKI BILAN BIR XIL
# ===========================================================================


async def test_repo_review_queue_count_matches_the_claim_predicate(
    env: Env, tenant_session: TenantSessionFactory
) -> None:
    """⛔ SANOQ NOLGA TUSHGAN PAYT `claim_next()` NING `None` PAYTI BILAN BIR XIL.

    =======================================================================
    ⛔⛔ BU IKKI SQL MATNINI SOLISHTIRMAYDI — U ULARNI CHEGARADA
        UCHRASHTIRADI.

    Matn solishtiruvi (`assert "NOT EXISTS" in ...`) predikat MA'NOSI
    o'zgarganda ham yashil qolardi. Bu yerdagi da'vo esa xulqiy: navbatda
    ish bor ekan sanoq musbat VA `claim_next()` band qaytaradi; oxirgi
    javob yozilgach sanoq nol VA `claim_next()` `None`.

    Ajralib ketishning narxi shu bilan o'lchanadi: bosh ekranda «12»
    ko'rinib, navbatda 7 ta ish chiqishi — nazoratchi sanoqqa boshqa
    ishonmasdi.
    =======================================================================
    """
    pending = env.pending_assignments(queue_kind=ReviewQueueKind.UNCERTAIN.value)
    assert pending, "nazorat: seedda javobsiz noaniq topshiriq yo'q — da'vo bo'sh bo'lardi"

    async with tenant_session(env.market_id) as session:
        before = await headline_repo.review_queue_count(session, market_id=env.market_id)
        claimed = await ReviewRepository(session, env.market_id).claim_next()

    assert before == len(pending)
    assert claimed is not None, "sanoq musbat, lekin navbat band bermadi — predikatlar ajralgan"

    for assignment_id in pending:
        env.answer(assignment_id, queue_kind=ReviewQueueKind.UNCERTAIN.value)

    async with tenant_session(env.market_id) as session:
        after = await headline_repo.review_queue_count(session, market_id=env.market_id)
        drained = await ReviewRepository(session, env.market_id).claim_next()

    assert after == 0
    assert drained is None, "sanoq nol, lekin navbat hamon band beryapti — predikatlar ajralgan"


async def test_repo_review_queue_ignores_the_blind_audit_queue(
    env: Env, tenant_session: TenantSessionFactory
) -> None:
    """⛔ Ko'r audit navbati bosh ekranda KO'RINMAYDI [QAROR].

    Namunaning HAJMI nazoratchiga oshkor qilinmaydi: «bugun 30 ta band
    bor» degan son ko'r auditni ko'r bo'lmagan qilardi (05-RESEARCH §C.8 —
    javob ankorlanishi). Nazoratchining bosh ekrandagi soni — uning
    ASOSIY ishi, ya'ni noaniq navbat.

    NAZORAT: `blind_audit` topshirig'i HAQIQATAN javobsiz qoldiriladi va
    shundan keyin ham sanoq o'zgarmasligi tekshiriladi. Usiz test
    «navbatda umuman ko'r audit yo'q» holatida ham yashil bo'lardi.
    """
    blind_assignment = env.occupancy.market_a.blind_assignment_id
    env.drop_review(blind_assignment)
    blind_pending = env.pending_assignments(queue_kind=ReviewQueueKind.BLIND_AUDIT.value)
    assert blind_assignment in blind_pending, (
        "nazorat: ko'r audit topshirig'i javobsiz holatga o'tmadi — da'vo bo'sh bo'lardi"
    )

    uncertain_pending = env.pending_assignments(queue_kind=ReviewQueueKind.UNCERTAIN.value)

    async with tenant_session(env.market_id) as session:
        actual = await headline_repo.review_queue_count(session, market_id=env.market_id)

    assert actual == len(uncertain_pending)
    assert actual != len(uncertain_pending) + len(blind_pending), (
        "sanoq ikkala navbatni ham qo'shib yubordi — ko'r auditning hajmi oshkor bo'lardi"
    )
