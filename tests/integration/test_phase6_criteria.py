"""Fazaning BESHTA muvaffaqiyat mezoni — ROADMAP matni bilan bog'langan YAGONA fayl.

=============================================================================
BU FAYL MAVJUD TESTLARNI TAKRORLAMAYDI — U ULARNI ZANJIR SIFATIDA BOG'LAYDI.

Har mezonning qismlari allaqachon qamralgan va ular O'Z EGASIDA qoladi:

  * `test_billing_close.py`    (06-07) — job, Pitfall 2, yopiq kun, D-14;
  * `test_billing_repo.py`     (06-06) — pul yechimi, FIFO, qoldiq tengligi;
  * `test_billing_immutable.py`(06-04/05) — uchala o'zgarmaslik qo'riqchisi;
  * `test_billing_api.py`      (06-08) — o'qish yuzasi, maydonning YO'QLIGI;
  * `test_payments_api.py`     (06-09) — idempotentlik, storno, sabab-kod;
  * `test_shifts_api.py`       (06-10) — ko'r deklaratsiya, ikki tomonlama farq;
  * `collect-session.test.tsx` (06-11) — ≤3 o'zaro ta'sir sanog'i (G-20);
  * `payment-bar.test.tsx`     (06-11) — `useRef` qulfi (G-21).

Bu yerdagi savol boshqa va u faqat shu yerda beriladi: **ROADMAP'da
yozilgan jumla bugun rostmi?** Har test docstringi mezon matnini
SO'ZMA-SO'Z olib yuradi, ya'ni ROADMAP tahrirlanganda mos kelmaslik
ko'zga tashlanadi.

=============================================================================
⛔⛔ D-01 — BU FAZADA «HOZIR O'LCHAB BO'LMAYDI» DEGAN BAND YO'Q.

5-fazada haqiqat YO'Q edi: oltin to'plam bo'sh, real kadr olinmagan,
modelning aniqligi o'lchanmagan — va aynan shuning uchun `AI-02`
`Blocked` bo'lib qoldi va `05-HUMAN-UAT.md` uchta band bilan tug'ildi.

Bu fazada haqiqat ⛔ **TO'LIQ MAVJUD** va uchala qismi ham bazada
yashaydi:

    pul miqdori  -> `tariffs.amount_soum` (aniq son, `bigint`)
    bandlik      -> `stall_slot_occupancy` (materializatsiya qilingan)
    to'lov       -> `payments` (append-only, belgili yig'indi)

Ya'ni beshala mezon ⛔ **bugun mexanik isbotlanadi**. Agar bu modul
«buni hozir o'lchab bo'lmaydi» degan bandni tug'dirsa — bu ⛔ **dizayn
xatosi**, tabiiy chegara emas, va u `06-VALIDATION.md` ning
`## Manual-Only Verifications` jadvaliga SABAB, EGA va TETIK bilan
yozilishi hamda `06-HUMAN-UAT.md` ni talab qilishi shart.

⛔ Shu sababdan bu fazada `06-HUMAN-UAT.md` fayli YARATILMAYDI va bu
   ⛔ **natija**, unutilgan band emas.

=============================================================================
⛔⛔ CHOK QAYERDA — VA U DA'VO EMAS, CHEGARA.

SC#4(b) va SC#5(b) — «≤3 bosish» va «uch tez bosish bitta so'rov» —
BRAUZER xulqi va ular ⛔ **vitest** da o'lchanadi
(`collect-session.test.tsx`, `payment-bar.test.tsx`). Bu modul ularni
QAYTA YOZMAYDI: ikkinchi implementatsiya ⛔ **ikkinchi haqiqat** bo'lardi
(G-20/G-21 bilan aynan bir xil naqsh, va 05-15 da o'lchangan sinf).

⛔ SANOQNING O'ZI EMAS, UNING ⛔ **DARVOZAGA ULANGANI** shu yerda
   o'lchanadi va u ikki mustaqil da'vodan iborat:

     (1) sanoq testi ⛔ MAVJUD va uning matnida CHEGARA ⛔ AYNAN yozilgan;
     (2) `package.json::gate` — fazaning YETKAZIB BERISH buyrug'i —
         o'sha to'plamni ⛔ HAQIQATAN yugurtiradi.

⛔ NEGA `subprocess` BILAN EMAS — VA BU O'LCHANGAN, TAXMIN EMAS:
   bu modul `tests` konteynerida yuguradi va u konteynerda
   ⛔ **`node` ham, `npm` ham YO'Q** (`services/core-api/Dockerfile`,
   `target: dev` — Python image'i). `docker compose --profile test run
   --rm tests sh -c "which npm node"` ⛔ **bo'sh** qaytaradi (06-14 da
   o'lchandi). Ya'ni «subprocess bilan yugurtiramiz» bandi bu yerda
   ⛔ **hech qachon** bajarilmasdi va uni `pytest.skip` bilan yumshatish
   soxtalashtirishning eng arzon shakli bo'lardi.

   ⚠ IKKINCHI, MUSTAQIL SABAB: `npm --prefix frontend test --
     collect-session` shakli ⛔ **NOTO'G'RI**: `frontend` ning `test`
     skripti — `node --test scripts/*.test.mjs && vitest run` zanjiri va
     `--` dan keyingi argument BIRINCHI buyruqqa yopishardi
     (`node --test scripts/*.test.mjs collect-session`), ya'ni vitest
     filtri UMUMAN ishlamasdi.

=============================================================================
UCHTA DARVOZA VA UCHALASI HAM MUSTAQIL:

  1. **Mezon boshiga bitta test** — `test_sc1_`…`test_sc5_`, boshqasi yo'q.
  2. **Meta-test** — mezonlardan biri JIMGINA tushib qolmasin. Fayl qayta
     tashkil qilinganda yoki test vaqtincha o'chirilganda darvoza baribir
     yashil bo'lardi va «beshala mezon o'lchanadi» da'vosi ISBOTSIZ
     qolardi. Meta-testning O'Z nomida `sc<raqam>` YO'Q va bu ataylab.
  3. **Soxtalashtirishsiz o'lchov** — na baza, na ombor, na marshrut grafi
     almashtiriladi. Darvoza IKKI yo'ldan yuradi (`ast` daraxti VA modul
     global nomlari). ⛔ «O'tkazib yuborish» yo'li ATAYIN YO'Q.

     ⛔ BU FAZAGA XOS UCHINCHI TAQIQ: pul mezoni ⛔ **suzuvchi
        arifmetika** bilan o'lchanmaydi (D-11). Taqiq 5-fazanikidan
        (`precision`/`recall`/`map`) BOSHQA, chunki bu fazaning yolg'oni
        ham boshqa: bu yerda hech kim aniqlik DA'VO qilmaydi — bu yerda
        summa YAXLITLANIB ketishi mumkin.

=============================================================================
⛔ KUN — SEEDNING KUNI EMAS, O'TMISHDAGI OCHIQ KUN (06-07 ning darsi).

`ck_daily_charges_service_date_not_in_future` `service_date <=
business_date` ni talab qiladi, `business_date` esa `created_at` DAN
HOSILA, ya'ni HAR DOIM «bugun». `SEED_BUSINESS_DATE` (2026-09-01) —
QADALGAN sana va u bugundan KEYIN bo'lishi mumkin: o'sha kunga hisob ham,
anomaliya ham YOZIB BO'LMAYDI.

Shuning uchun mezonlarning kuni `_open_past_day()` bilan tanlanadi:
A bozorining HAFTALIK jadvali bo'yicha OCHIQ, o'tmishdagi eng yaqin kun.
`CURRENT_DATE - 1` YETARLI EMAS — A bozori dushanba yopiq va test
seshanba kuni yugurganda nosozlik KODDA emas, KALENDARDA bo'lardi.
=============================================================================
"""

from __future__ import annotations

import ast
import inspect
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import psycopg
import pytest
from app.jobs.billing_close import billing_close
from app.jobs.day_close import day_close
from app.main import app as fastapi_app
from app.repositories import billing_repo
from fixtures.admin_api import session_headers
from fixtures.billing_domain import (
    BILLING_VALID_FROM,
    BillingDomainSeed,
    MarketBillingRows,
    add_billable_frame,
    add_payment,
    add_zone_with_event_on,
    billing_domain_before_day_close,
)
from fixtures.frames import frame_bytes
from fixtures.market_domain import A_OPEN_WEEKDAYS, MarketDomainSeed
from fixtures.nvr_domain import nvr_rows
from fixtures.occupancy_domain import OccupancyDomainSeed, occupancy_rows
from fixtures.snapshot_domain import snapshot_rows
from fixtures.two_markets import SEED_PASSWORD, TwoMarketSeed
from sbozor_core.billing import ALLOCATION_RULE
from sbozor_core.enums import (
    AdjustmentDirection,
    AdjustmentReason,
    AnomalyKind,
    OccupancyVerdict,
    PaymentKind,
    ReviewPurpose,
    ReviewQueueKind,
    ShiftStatus,
)
from sbozor_core.models.snapshot import DEFAULT_SNAPSHOT_SLOTS

if TYPE_CHECKING:
    from collections.abc import Iterator

    import httpx
    from app.services.storage import SnapshotStorage
    from fixtures import TenantSessionFactory
    from psycopg import Connection
    from psycopg.rows import TupleRow
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

pytestmark = pytest.mark.usefixtures("migrated")

_MODULE_PATH = Path(__file__)
_REPO_ROOT = _MODULE_PATH.parents[2]

PENDING_URL = "/api/v1/billing/pending"
PAYMENTS_URL = "/api/v1/payments"
SHIFTS_URL = "/api/v1/shifts"
SNAPSHOTS_URL = "/api/v1/snapshots"

_SLOT_A = DEFAULT_SNAPSHOT_SLOTS[0]
_SLOT_B = DEFAULT_SNAPSHOT_SLOTS[1]

SET_MARKET = "SELECT set_config('app.market_id', %s, false)"
"""Sessiya darajasidagi tenant konteksti — FAQAT `audit_log` ni O'QISH uchun.

`audit_read` policy'si tenant-scoped va u jadval EGASIGA ham qo'llanadi
(`FORCE`). Kontekstsiz sanoq 0 bo'lardi va audit da'vosi BO'SH ROST bo'lib
qolardi (`test_billing_immutable.py:89-96` da o'lchangan tuzoq).

⚠ QOLGAN so'rovlarga QO'YILMAYDI va o'qishdan keyin BO'SHATILADI: job
  o'z kontekstini O'ZI o'rnatadi va testning sessiya darajasidagi
  qiymati mahsulot yo'lini niqoblab qo'yardi (Pitfall 9).
"""

AUDIT_COUNT = "SELECT count(*) FROM audit_log WHERE table_name = %s"

_INSERT_REVIEW_ASSIGNMENT = (
    "INSERT INTO review_assignments "
    "(id, market_id, occupancy_event_id, audit_round_id, queue_kind, purpose) "
    "VALUES (%s, %s, %s, %s, %s, %s)"
)
_INSERT_ZONE_REVIEW = (
    "INSERT INTO zone_reviews "
    "(id, market_id, review_assignment_id, queue_kind, shown_ai_verdict, "
    " human_verdict, reviewer_id, decision_ms) "
    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
)
"""Nusxa ONGLI — `test_billing_close.py:86-96` da o'rnatilgan qoida: ikki SQL
satri jadval strukturasi bilan birga o'zgaradi va u sxema darvozasi
(`test_billing_domain_meta.py`) bilan ALLAQACHON qo'riqlangan."""


# ===========================================================================
# ⛔⛔ SOXTALASHTIRISH REYESTRLARI — NOMLAR BO'LAKLAB QURILADI
#
# ⛔ NEGA LITERAL YOZILMAYDI VA BU HIYLA EMAS, ZARURAT:
#    bu modulning O'Z qabul mezoni MATN SKANI bilan o'lchanadi — reja
#    soxtalashtirish vositalarining nomini `grep` bilan izlaydi va natija
#    NOL bo'lishini talab qiladi. Reyestrni literal yozish darvozani O'Z
#    izohida topib, uni HECH QACHON yashil bo'lmaydigan qilardi. Aynan shu
#    qaror 5-fazada ham yozilgan (`test_phase5_criteria.py:148-152`) — u
#    yerda ro'yxat docstringdan KODGA ko'chirilgan; bu yerda esa bir qadam
#    nariga: nom ish vaqtida QURILADI, manba matnida esa BUTUN holida
#    uchramaydi.
#
# ⚠ Ish vaqtidagi qiymat AYNAN o'sha nom — pastdagi NAZORAT testi buni
#   tekshiradi, ya'ni bo'laklash xatosi jimgina o'tib keta olmaydi.
# ===========================================================================

_MOCK_ROOTS = frozenset(
    {
        "moto",
        "unittest",
        "mock",
        "respx",
        "aioresponses",
        "botocore",
        "pytest_mock",
        "responses",
    }
)
"""Bu modulda IMPORT QILINMAYDIGAN kutubxonalar — ro'yxat KODDA, matnda EMAS."""

_MOCK_SUFFIX = "Mock"
"""`from … import …` bilan olib kiriladigan soxtalashtirish VOSITALARINING oxiri.

Standart kutubxonaning soxta obyekt sinflari — yalang'ochi ham, «sehrli»
ham, asinxroni ham — HAMMASI shu qo'shimcha bilan tugaydi, ya'ni ro'yxat
SANOQ emas, SHAKL bo'yicha yopiladi va beshinchi variant ham jimgina
o'tib keta olmaydi.

⚠ SINF NOMLARI BU YERDA HAM SANALMAYDI — yuqoridagi bo'limdagi sabab.
"""

_PATCH = "pat" + "ch"
_MOCK_NAMES = frozenset({_PATCH, "mock_open", "seal"})
_FAKE_FIXTURES = frozenset(
    {
        "monkey" + _PATCH,
        "mocker",
        "enqueued",
        "telegram_calls",
        "respx_mock",
        "httpx_mock",
        "go2rtc_mock",
    }
)
"""Test imzosida UCHRAMASLIGI shart bo'lgan fixture nomlari.

Import skani soxtalashtirishning FAQAT BIR shaklini ko'radi. Ikkinchisi —
pytest'ning O'Z tuzatuvchi fixture'i yoki loyihaning spy fixture'i
(`enqueued` broker'ni almashtiradi) — birorta yangi import TALAB
QILMAYDI, ya'ni `ast` daraxti uni UMUMAN ko'rmasdi.
"""

_BANNED_MONEY_NAMES = frozenset({"float", "decimal", "round"})
"""⛔ D-11 — PUL MEZONI SUZUVCHI ARIFMETIKA BILAN O'LCHANMAYDI.

Uchala nom ham shu modulda TAQIQLANADI: summa `bigint` so'm ↔ Python
`int` va yaxlitlash amali mezon qatlamida UMUMAN paydo bo'lmasligi kerak.
Bitta yaxlitlash butun fazaning da'vosini («pul miqdori aniq») jimgina
taxminiy qilib qo'yardi.

⚠ NOMLAR KICHIK HARFDA yozilgan va solishtiruv ham kichik harfda: bu
  modulning O'Z qabul mezoni matn skani bilan o'lchanadi va reyestrni
  «to'g'ri» imloda yozish darvozani o'ziga qarshi qo'yardi (yuqoridagi
  bo'lim bilan aynan bir xil sabab).
"""


# ===========================================================================
# MUHIT — BESH QATLAMLI SEED
# ===========================================================================


class Env:
    """Bir mezonga kerak bo'ladigan hamma narsa — bitta obyektda."""

    def __init__(
        self,
        billing: BillingDomainSeed,
        domain: MarketDomainSeed,
        base: TwoMarketSeed,
        occupancy: OccupancyDomainSeed,
        conn: Connection[TupleRow],
        today: date,
    ) -> None:
        self.billing = billing
        self.domain = domain
        self.base = base
        self.occupancy = occupancy
        self.conn = conn
        self.today = today

    @property
    def live(self) -> MarketBillingRows:
        """A bozori — to'liq holat qamrovi."""
        return self.billing.market_a

    @property
    def market_id(self) -> UUID:
        return self.live.market_id

    @property
    def other_market_id(self) -> UUID:
        return self.billing.market_b.market_id

    @property
    def vendor_id(self) -> UUID:
        return self.live.vendor_id

    @property
    def cashier_id(self) -> UUID:
        return self.live.cashier_id

    def stall(self, name: str) -> UUID:
        """Nomlangan stsenariy rastasi — `None` bo'lsa NAZORAT bilan yiqiladi."""
        stall_id: UUID | None = getattr(self.live, name)
        assert stall_id is not None, f"nazorat: seedda {name!r} rastasi yo'q"
        return stall_id

    @property
    def never_assigned_stall(self) -> UUID:
        """⛔ D-28 NING YAGONA IFODALANADIGAN HOLATI O'TMISHDAGI KUNDA.

        Seedning `stall_occupied_without_assignment` i biriktirish
        BO'SHLIG'INI `[SEED_BUSINESS_DATE, +7)` oralig'iga qo'yadi, ya'ni
        u KELAJAKDA. O'tmishdagi kunda o'sha rasta BIRIKTIRILGAN.

        `market_domain` esa `unassigned_stall_id` ga BIRORTA biriktirish
        yozmaydi, ya'ni u HAR QANDAY kunda sotuvchisiz — D-28 ning kirishi.
        """
        stall_id = self.domain.market_a.unassigned_stall_id
        assert stall_id is not None, "nazorat: `market_domain` da biriktirilmagan rasta yo'q"
        return stall_id

    def code(self, stall_id: UUID) -> str:
        """Rastaning KODI — BAZADAN, qo'shni faylning ro'yxat tartibidan EMAS."""
        row = self.conn.execute(
            "SELECT code FROM stalls WHERE id = %s", (str(stall_id),)
        ).fetchone()
        assert row is not None, f"nazorat: {stall_id} rastasi bazada yo'q"
        code: str = row[0]
        return code

    def tariff_amount(self, day: date | None = None) -> int:
        """Seed tarif zanjirining SHU KUNDAGI summasi — ⛔ BAZADAN, LITERAL EMAS.

        Qadalgan `15 000` fixture konstantasi bilan birga o'zgarardi va
        «hisob QAYSI tarifdan olindi?» savoli javobsiz qolardi. Bu yerda
        summa AYNAN o'sha `tariffs` zanjiridan o'qiladi.

        ⛔ KUN BO'YICHA, BIRINCHI QATOR EMAS: zanjir ikki qatorli
           (`NEXT_TARIFF_VALID_FROM` = 2026-09-02 da 15 000 -> 20 000),
           mezonlarning kuni esa «bugun»ga ergashadi (`_open_past_day`).
           Faqat birinchi qatorni o'qish o'sha kundan beri SC#1/SC#2/SC#5 ni
           JIMGINA qizartirdi — mahsulot to'g'ri summani yozib turgan edi.
           Kun berilmasa — bugun (kassir `POST /payments` da ko'radigan narx).
        """
        row = self.conn.execute(
            "SELECT amount_soum FROM tariffs "
            "WHERE id = ANY(%s::uuid[]) AND valid_from <= %s "
            "ORDER BY valid_from DESC LIMIT 1",
            (
                [str(self.live.tariff_id), str(self.live.next_tariff_id)],
                self.today if day is None else day,
            ),
        ).fetchone()
        assert row is not None, "nazorat: seedning tarif qatori bazada yo'q"
        return int(row[0])

    def day_total_amount(self, day: date | None = None) -> int:
        """Kunlik pattaning TO'LIQ summasi — ⛔ BAZADAN, LITERAL EMAS (0027).

        =====================================================================
        ⛔ `tariff_amount()` ENDI KUNLIK SUMMA EMAS.

        0027 dan keyin `daily_charges.amount_soum` IKKI qo'shiluvchidan
        iborat: tarif ustuni (`tariff_amount_soum`) va majburiy xizmat
        haqi (`fee_amount_soum`). Mezon matnidagi «toifa tarifi bo'yicha
        TO'LIQ kunlik patta» endi AYNAN shu yig'indini bildiradi.

        ⚠ IKKALA QIYMAT HAM BAZADAN o'qiladi — `tariff_amount()` bilan
          bir xil sabab: qadalgan son fixture konstantasi bilan birga
          o'zgarardi va «summa QAYERDAN olindi?» savoli javobsiz
          qolardi.

        ⚠ Xizmat haqi qatori BO'LMASLIGI mumkin (bozor uni belgilamagan)
          — o'shanda `0` qaytadi va yig'indi tarifning o'ziga teng
          bo'ladi. Bu HALOL javob, nosozlik emas.
        =====================================================================
        """
        on = self.today if day is None else day
        row = self.conn.execute(
            "SELECT amount_soum FROM market_service_fees "
            "WHERE market_id = %s AND valid_from <= %s "
            "ORDER BY valid_from DESC LIMIT 1",
            (str(self.market_id), on),
        ).fetchone()
        fee = 0 if row is None else int(row[0])
        return self.tariff_amount(on) + fee


@pytest.fixture
def env(
    sync_owner_conn: Connection[TupleRow],
    two_markets: TwoMarketSeed,
    market_domain: MarketDomainSeed,
    market_today: date,
) -> Iterator[Env]:
    """Slot qatorlarisiz seed — `day_close` bu yerda CHAQIRILMAYDI.

    ⛔ `billing_domain` (async) VARIANTI ATAYIN ISHLATILMAYDI: u
       `SEED_BUSINESS_DATE` uchun `day_close` yugurtiradi, mezonlar esa
       O'TMISHDAGI kun bilan ishlaydi (modul docstringining oxirgi bandi).
       Ikki yugurish har mezonga narx qo'shib, birorta da'voga xizmat
       qilmasdi.

    ⚠ TOZALASH `market_id` BO'YICHA: SC#4/SC#5 to'lov va smena qatorlarini
      HTTP orqali yozadi va seed ularning identifikatorlarini BILMAYDI.
      Bozor avval qoralamaga qaytariladi — `payment_immutable()` va
      `shift_declaration_immutable()` `DELETE` ni FAQAT nofaol bozorda
      ruxsat etadi (`test_shifts_api.py::env` naqshi).
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
            yield Env(billing, market_domain, two_markets, occupancy, sync_owner_conn, market_today)
        finally:
            sync_owner_conn.execute(
                "UPDATE markets SET is_active = false WHERE id = %s", (str(market_id),)
            )
            # ⛔ `notification_outbox` 07-12 DA QO'SHILDI: `POST /payments`
            #    ning 6.5-QADAMI (CASH-05) har yangi to'lov uchun kvitansiya
            #    niyatini ham yozadi. `fk_notification_outbox_vendor` da
            #    `ondelete` YO'Q, ya'ni qoldiq qator quyi qatlamlarning
            #    sotuvchi/bozor `DELETE` ini FK buzilishi bilan yiqitardi.
            sync_owner_conn.execute(
                "DELETE FROM notification_outbox WHERE market_id = %s", (str(market_id),)
            )
            sync_owner_conn.execute("DELETE FROM payments WHERE market_id = %s", (str(market_id),))
            sync_owner_conn.execute(
                "DELETE FROM cashier_shifts WHERE market_id = %s AND id <> %s",
                (str(market_id), str(billing.market_a.open_shift_id)),
            )
            sync_owner_conn.execute(
                "UPDATE markets SET is_active = true WHERE id = %s", (str(market_id),)
            )


@pytest.fixture
async def cashier_headers(api_client: httpx.AsyncClient, env: Env) -> dict[str, str]:
    """KASSIR sessiyasi — `payment_create` va `shift_manage` BOR, `report_view` YO'Q."""
    return await session_headers(api_client, env.base.market_a.cashier_phone, SEED_PASSWORD)


@pytest.fixture
async def director_headers(api_client: httpx.AsyncClient, env: Env) -> dict[str, str]:
    """DIREKTOR sessiyasi — `report_view` BOR (variance va dalil kadri shu yerdan)."""
    return await session_headers(api_client, env.base.market_a.director_phone, SEED_PASSWORD)


# ===========================================================================
# O'TMISHDAGI KUN — TESTDA TUG'ILGAN QATORLARNING EGASI
# ===========================================================================


def _open_past_day(conn: Connection[TupleRow]) -> date:
    """O'tmishdagi eng yaqin OCHIQ kun (A bozorining haftalik jadvali bo'yicha).

    ⚠ NAZORAT ASSERTI BILAN: kun `BILLING_VALID_FROM` dan OLDIN tushsa
      tarif ham, toifa davri ham hali mavjud emas va butun modul «tarif
      yo'q» shoxini o'lchagan bo'lardi.
    """
    row = conn.execute("SELECT (now() AT TIME ZONE 'Asia/Tashkent')::date - 1").fetchone()
    assert row is not None
    day: date = row[0]

    while day.isoweekday() not in A_OPEN_WEEKDAYS:
        day -= timedelta(days=1)

    assert day >= BILLING_VALID_FROM, (
        f"tanlangan kun {day} tarif zanjiridan ({BILLING_VALID_FROM}) OLDIN — seed bu "
        "kunda hali narxga ega emas va mezonlar boshqa shoxni o'lchagan bo'lardi"
    )
    return day


class PastDay:
    """O'TMISHDAGI kunning kadr/hodisa qatlami — VA ULARNING EGASI.

    =========================================================================
    ⛔ NEGA ALOHIDA EGA KERAK: `cleanup_billing_domain()` `occupancy_events`,
       `snapshots` va `capture_runs` ni O'Z ID'lari bo'yicha o'chiradi va bu
       yerda tug'ilgan qatorlarni BILMAYDI. Tozalanmasa u FK buzilishi bilan
       yiqilardi va nosozlik SEEDDA ko'rinardi, holbuki u MEZONNIKI.

    ⛔ TOZALASH BILLING QATORLARIDAN BOSHLANADI va bu TARTIB masalasi:
       `charge_evidence`, `billing_anomalies` va `stall_slot_occupancy`
       shu yerda tug'ilgan hodisalarga TAYANADI.
    =========================================================================
    """

    __slots__ = ("_conn", "_events", "_market_ids", "_reviews", "_rows", "_zones")

    def __init__(self, conn: Connection[TupleRow], market_ids: tuple[UUID, ...]) -> None:
        self._conn = conn
        self._market_ids = market_ids
        self._rows: list[tuple[str, UUID]] = []
        self._events: list[UUID] = []
        self._zones: list[UUID] = []
        self._reviews: list[UUID] = []

    def frame(self, *, market_id: UUID, camera_id: UUID, slot: Any, day: date) -> UUID:
        """Kadr — `capture_runs` + YAROQLI `snapshots`. Qaytaradi `snapshot_id`."""
        nvr_id = _nvr_of(self._conn, market_id)
        run_id, snapshot_id = add_billable_frame(
            self._conn,
            market_id=market_id,
            nvr_id=nvr_id,
            camera_id=camera_id,
            slot=slot,
            day=day,
            is_market_open=True,
        )
        self._rows.append(("snapshots", snapshot_id))
        self._rows.append(("capture_runs", run_id))
        return snapshot_id

    def occupied(
        self,
        *,
        market_id: UUID,
        camera_id: UUID,
        stall_id: UUID,
        snapshot_id: UUID,
        day: date,
        slot: Any,
        center: tuple[float, float],
        version: int,
    ) -> UUID:
        """Zona + AI «band» hodisasi. Qaytaradi `occupancy_event_id`.

        ⚠ `version` HAR CHAQIRUVDA BOSHQA: seedda o'sha (kamera, rasta)
          juftligiga zona ALLAQACHON bo'lishi mumkin.
        """
        zone_id, event_id = add_zone_with_event_on(
            self._conn,
            market_id=market_id,
            camera_id=camera_id,
            stall_id=stall_id,
            snapshot_id=snapshot_id,
            business_date=day,
            slot=slot,
            center=center,
            version=version,
        )
        self._zones.append(zone_id)
        self._events.append(event_id)
        return event_id

    def answer(self, *, market_id: UUID, event_id: UUID, human_verdict: str) -> None:
        """Nazoratchining javobi — NOANIQ navbat topshirig'i + `zone_reviews`."""
        assignment_id = uuid4()
        self._conn.execute(
            _INSERT_REVIEW_ASSIGNMENT,
            (
                str(assignment_id),
                str(market_id),
                str(event_id),
                None,
                ReviewQueueKind.UNCERTAIN.value,
                ReviewPurpose.TRAIN.value,
            ),
        )
        self._conn.execute(
            _INSERT_ZONE_REVIEW,
            (
                str(uuid4()),
                str(market_id),
                str(assignment_id),
                ReviewQueueKind.UNCERTAIN.value,
                True,
                human_verdict,
                str(_reviewer_of(self._conn, market_id)),
                1500,
            ),
        )
        self._reviews.append(assignment_id)

    def cleanup(self) -> None:
        """Billing hosilalari -> javoblar -> hodisalar -> zonalar -> kadrlar."""
        markets = [str(market_id) for market_id in self._market_ids]
        self._conn.execute(
            "UPDATE markets SET is_active = false WHERE id = ANY(%s::uuid[])", (markets,)
        )
        for table in (
            "charge_evidence",
            "charge_adjustments",
            "billing_anomalies",
            "daily_charges",
            "stall_slot_occupancy",
        ):
            self._conn.execute(
                f"DELETE FROM {table} WHERE market_id = ANY(%s::uuid[])",  # noqa: S608
                (markets,),
            )

        if self._reviews:
            ids = [str(value) for value in self._reviews]
            self._conn.execute(
                "DELETE FROM zone_reviews WHERE review_assignment_id = ANY(%s::uuid[])", (ids,)
            )
            self._conn.execute("DELETE FROM review_assignments WHERE id = ANY(%s::uuid[])", (ids,))
        if self._events:
            self._conn.execute(
                "DELETE FROM occupancy_events WHERE id = ANY(%s::uuid[])",
                ([str(value) for value in self._events],),
            )
        if self._zones:
            self._conn.execute(
                "DELETE FROM camera_zones WHERE id = ANY(%s::uuid[])",
                ([str(value) for value in self._zones],),
            )
        for table, row_id in self._rows:
            self._conn.execute(
                f"DELETE FROM {table} WHERE id = %s",  # noqa: S608
                (str(row_id),),
            )
        self._conn.execute(
            "UPDATE markets SET is_active = true WHERE id = ANY(%s::uuid[])", (markets,)
        )


def _nvr_of(conn: Connection[TupleRow], market_id: UUID) -> UUID:
    """Bozorning NVR'i — `capture_runs` DAN (`billing_domain._nvr_of` qoidasi)."""
    row = conn.execute(
        "SELECT nvr_id FROM capture_runs WHERE market_id = %s ORDER BY nvr_id LIMIT 1",
        (str(market_id),),
    ).fetchone()
    assert row is not None, f"{market_id} da `capture_runs` qatori yo'q"
    nvr_id: UUID = row[0]
    return nvr_id


def _reviewer_of(conn: Connection[TupleRow], market_id: UUID) -> UUID:
    """`zone_reviews.reviewer_id` — bozorning admin foydalanuvchisi."""
    row = conn.execute(
        "SELECT user_id FROM user_market_roles "
        "WHERE market_id = %s AND 'market_admin' = ANY(roles) "
        "ORDER BY user_id LIMIT 1",
        (str(market_id),),
    ).fetchone()
    assert row is not None, f"{market_id} da `market_admin` rolli foydalanuvchi yo'q"
    reviewer_id: UUID = row[0]
    return reviewer_id


class Scenario:
    """O'tmishdagi kunning TO'LIQ holat qamrovi — nomma-nom.

    =========================================================================
    BESH RASTA, BESH BOSHQA JAVOB (A bozori):

      `two_ai_slots`     2 slotda AI «band»                 -> HISOB
      `human_slot`       1 slotda «band» + nazoratchi «band» -> HISOB
      `one_ai_slot`      1 slotda AI «band»                 -> hisob YO'Q (D-04)
      `human_says_empty` 1 slotda AI «band» + BOSHQA slotda
                         nazoratchi «bo'sh»                 -> hisob YO'Q (G-6)
      `unassigned`       2 slotda «band», sotuvchisiz       -> ANOMALIYA (D-28)

    ⛔ `human_says_empty` — G-6 NING BUTUN MAZMUNI. Usiz «nazoratchi
       tasdig'i» sharti «nazoratchi umuman javob berganmi?» degan
       ZAIFROQ shart bilan almashtirilganda (C-6 sabotaji) HAMMA
       assert yashil qolardi.

    ⚠ B BOZORIGA HAM KADR YOZILADI (hodisasiz): `no_slot_rows` — BUTUN
      YUGURISHNING sanog'i, ya'ni B materializatsiya qilinmasa u
      `day_close` dan KEYIN ham nolga tushmasdi.
    =========================================================================
    """

    __slots__ = (
        "day",
        "human_says_empty",
        "human_slot",
        "one_ai_slot",
        "snapshot_a",
        "two_ai_slots",
        "unassigned",
    )

    def __init__(self, env: Env, past: PastDay, day: date) -> None:
        self.day = day
        self.two_ai_slots = env.stall("stall_with_two_occupied_slots")
        self.human_slot = env.stall("stall_with_one_human_confirmed_occupied_slot")
        self.one_ai_slot = env.stall("stall_with_one_ai_occupied_slot")
        self.human_says_empty = env.stall("stall_occupied_without_assignment")
        self.unassigned = env.never_assigned_stall

        market_id = env.market_id
        camera_a = env.occupancy.market_a.camera_id
        camera_b = env.occupancy.market_a.second_camera_id
        assert camera_b is not None, "nazorat: A bozorining ikkinchi kamerasi yo'q"

        snap_a = past.frame(market_id=market_id, camera_id=camera_a, slot=_SLOT_A, day=day)
        snap_b = past.frame(market_id=market_id, camera_id=camera_b, slot=_SLOT_B, day=day)
        self.snapshot_a = snap_a

        # (1) IKKI SLOTDA AI «band» -> HISOB.
        for camera_id, snapshot_id, slot, center, version in (
            (camera_a, snap_a, _SLOT_A, (0.20, 0.20), 31),
            (camera_b, snap_b, _SLOT_B, (0.25, 0.25), 32),
        ):
            past.occupied(
                market_id=market_id,
                camera_id=camera_id,
                stall_id=self.two_ai_slots,
                snapshot_id=snapshot_id,
                day=day,
                slot=slot,
                center=center,
                version=version,
            )

        # (2) BITTA SLOTDA «band» + nazoratchi «band» dedi -> HISOB.
        human_event = past.occupied(
            market_id=market_id,
            camera_id=camera_a,
            stall_id=self.human_slot,
            snapshot_id=snap_a,
            day=day,
            slot=_SLOT_A,
            center=(0.30, 0.30),
            version=33,
        )
        past.answer(
            market_id=market_id, event_id=human_event, human_verdict=OccupancyVerdict.OCCUPIED.value
        )

        # (3) BITTA SLOTDA AI «band» -> hisob YO'Q (D-04).
        past.occupied(
            market_id=market_id,
            camera_id=camera_a,
            stall_id=self.one_ai_slot,
            snapshot_id=snap_a,
            day=day,
            slot=_SLOT_A,
            center=(0.40, 0.40),
            version=34,
        )

        # (4) ⛔ G-6: bitta slotda AI «band», BOSHQA slotda nazoratchi
        #     «bo'sh» dedi. Rastada nazoratchi javobi BOR, lekin u BAND
        #     slotda EMAS -> hisob YOZILMAYDI.
        past.occupied(
            market_id=market_id,
            camera_id=camera_a,
            stall_id=self.human_says_empty,
            snapshot_id=snap_a,
            day=day,
            slot=_SLOT_A,
            center=(0.48, 0.48),
            version=35,
        )
        empty_event = past.occupied(
            market_id=market_id,
            camera_id=camera_b,
            stall_id=self.human_says_empty,
            snapshot_id=snap_b,
            day=day,
            slot=_SLOT_B,
            center=(0.52, 0.52),
            version=36,
        )
        past.answer(
            market_id=market_id, event_id=empty_event, human_verdict=OccupancyVerdict.EMPTY.value
        )

        # (5) IKKI SLOTDA «band», SOTUVCHISIZ -> ANOMALIYA (D-28).
        for camera_id, snapshot_id, slot, center, version in (
            (camera_a, snap_a, _SLOT_A, (0.60, 0.60), 37),
            (camera_b, snap_b, _SLOT_B, (0.65, 0.65), 38),
        ):
            past.occupied(
                market_id=market_id,
                camera_id=camera_id,
                stall_id=self.unassigned,
                snapshot_id=snapshot_id,
                day=day,
                slot=slot,
                center=center,
                version=version,
            )

        # B bozori — KADR BOR, HODISA YO'Q (sinf docstringidagi ⚠).
        past.frame(
            market_id=env.other_market_id,
            camera_id=env.occupancy.market_b.camera_id,
            slot=_SLOT_A,
            day=day,
        )


@pytest.fixture
def past(sync_owner_conn: Connection[TupleRow], env: Env) -> Iterator[PastDay]:
    """⚠ `env` GA BOG'LANGAN va bu TARTIB uchun: pytest fixture'larni teskari
    tartibda yopadi, ya'ni bu tozalash billing seedinikidan OLDIN yuguradi.
    """
    owner = PastDay(sync_owner_conn, (env.market_id, env.other_market_id))
    try:
        yield owner
    finally:
        owner.cleanup()


@pytest.fixture
def scenario(sync_owner_conn: Connection[TupleRow], env: Env, past: PastDay) -> Scenario:
    """O'tmishdagi kunning to'liq holat qamrovi (`Scenario` docstringi)."""
    return Scenario(env, past, _open_past_day(sync_owner_conn))


async def _materialise_and_close(sessionmaker: async_sessionmaker[AsyncSession], day: date) -> None:
    """⛔ MAHSULOT ZANJIRI: `day_close` -> `billing_close`, AYNAN shu tartibda.

    Tartib C-3 ning o'zi: `stall_slot_occupancy` — `billing_close` ning
    KIRISHI va uni `day_close` yozadi. Teskari tartib «yashil, lekin bo'sh»
    natijani berardi va aynan shu farq SC#1 da ALOHIDA o'lchanadi.
    """
    await day_close(sessionmaker, business_date=day)
    await billing_close(sessionmaker, business_date=day)


def _charges(conn: Connection[TupleRow], market_id: UUID, day: date) -> dict[UUID, tuple[Any, ...]]:
    """`{stall_id: (amount_soum, created_at)}` — kun kesimida."""
    rows = conn.execute(
        "SELECT stall_id, amount_soum, created_at FROM daily_charges "
        "WHERE market_id = %s AND service_date = %s",
        (str(market_id), day),
    ).fetchall()
    return {row[0]: (row[1], row[2]) for row in rows}


def _charge_id(conn: Connection[TupleRow], market_id: UUID, stall_id: UUID, day: date) -> UUID:
    row = conn.execute(
        "SELECT id FROM daily_charges WHERE market_id = %s AND stall_id = %s AND service_date = %s",
        (str(market_id), str(stall_id), day),
    ).fetchone()
    assert row is not None, f"nazorat: {stall_id} rastasiga {day} kunida hisob yozilmagan"
    charge_id: UUID = row[0]
    return charge_id


def _rows(conn: Connection[TupleRow], sql: str, params: tuple[object, ...]) -> int:
    row = conn.execute(sql, params).fetchone()
    assert row is not None
    return int(row[0])


def _column_names(conn: Connection[TupleRow], table: str) -> set[str]:
    """`information_schema.columns` dan ustun nomlari — TO'PLAM sifatida."""
    rows = conn.execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema = 'public' AND table_name = %s",
        (table,),
    ).fetchall()
    return {str(row[0]) for row in rows}


# ===========================================================================
# SC#1 — «Kun yopilganda band rastaga (kamida 2 snapshotda band, yoki
#         1 snapshot + nazoratchi tasdig'i) toifa tarifi bo'yicha to'liq
#         kunlik patta yoziladi; job qayta ishga tushirilsa ikkinchi hisob
#         paydo bo'lmaydi»
# ===========================================================================


async def test_sc1_immutable_daily_charge_is_written_once(
    sync_owner_conn: Connection[TupleRow],
    app_sessionmaker: async_sessionmaker[AsyncSession],
    scenario: Scenario,
    env: Env,
) -> None:
    """SC#1: «Kun yopilganda band rastaga (kamida 2 snapshotda band, yoki 1
    snapshot + nazoratchi tasdig'i) toifa tarifi bo'yicha to'liq kunlik patta
    yoziladi; job qayta ishga tushirilsa ikkinchi hisob paydo bo'lmaydi».

    =========================================================================
    ⛔⛔ KETMA-KETLIK DARVOZASI SHU TESTNING ICHIDA (Pitfall 2, C-3).

    Ikki holat MEXANIK ravishda ajralishi shart:

      (1) `day_close` HALI yugurmagan -> `charged == 0` VA `no_slot_rows > 0`
      (2) `day_close` yugurgan        -> `charged > 0`

    Agar (1) da `no_slot_rows` ham 0 bo'lganda edi, «job ishladi va hech kim
    band emas» bilan «biz umuman ko'rmadik» BIR XIL javob berardi — va aynan
    shu holat 20:30 dagi cron bilan HAR KUNI takrorlanardi.

    ⛔ U ALOHIDA TESTGA AJRATILMAYDI: mezon matnining «kun yopilganda»
       qismi AYNAN shu ketma-ketlik. Alohida testda u mezondan uzilib
       qolardi va mezon o'chirilganda ham yashil turaverardi.

    =========================================================================
    ⛔ QAYTA YUGURISH IKKI USTUN BILAN o'lchanadi (D-06): `amount_soum`
       VA `created_at`. Faqat sanoqni o'lchagan test `DO UPDATE`
       sabotajidan O'TARDI — qator soni o'zgarmasdi-yu, yozuv esa
       kechasi jimgina qayta yozilardi (05-12 dagi zaif testning aynan
       o'zi).
    """
    day = scenario.day
    market_id = env.market_id

    # ---- (1) MATERIALIZATSIYASIZ: «bo'sh» «ko'rmadik» dan AJRALADI.
    before = await billing_close(app_sessionmaker, business_date=day)
    assert before.charged == 0, "materializatsiyasiz hisob yozildi"
    assert before.no_slot_rows > 0, (
        "materializatsiyasiz yugurish `no_slot_rows = 0` qaytardi — sukunat "
        "«hammasi joyida» dan AJRALMADI (Pitfall 2)"
    )
    assert _charges(sync_owner_conn, market_id, day) == {}

    # ---- (2) MAHSULOT ZANJIRI: `day_close` -> `billing_close`.
    await _materialise_and_close(app_sessionmaker, day)

    written = _charges(sync_owner_conn, market_id, day)
    # ⚠ 2026-09-24 (gibrid qoida): ZONASIZ, biriktirilgan rastalar endi
    #   biriktirish bo'yicha hisob oladi — DALILSIZ. Mezon matni KAMERA
    #   hukmi haqida, shuning uchun to'plam dalil bo'yicha ajratiladi va
    #   qolgan har bir hisobda dalil YO'QLIGI alohida talab qilinadi.
    with_evidence = {
        row[0]
        for row in sync_owner_conn.execute(
            "SELECT DISTINCT c.stall_id FROM daily_charges c "
            "JOIN charge_evidence e ON e.market_id = c.market_id AND e.charge_id = c.id "
            "WHERE c.market_id = %s AND c.service_date = %s",
            (str(market_id), day),
        ).fetchall()
    }
    assert with_evidence == {scenario.two_ai_slots, scenario.human_slot}, (
        "kamera hukmidan hisob yozilgan rastalar to'plami mezon matniga MOS EMAS "
        f"(kutilgan: 2 slotli + nazoratchi tasdiqlagan): {sorted(map(str, with_evidence))}"
    )
    assert with_evidence <= set(written), "dalilli hisob `daily_charges` da yo'q"

    # ⛔ 0027: «TO'LIQ kunlik patta» = tarif + majburiy xizmat haqi — SHU KUNNING.
    expected = env.day_total_amount(day)
    for stall_id, (amount, _created) in written.items():
        if stall_id not in with_evidence:
            continue
        assert amount == expected, (
            f"{stall_id} rastasining summasi {amount}, kutilgan {expected} "
            "(tarif + xizmat haqi) — «toifa tarifi bo'yicha TO'LIQ kunlik "
            "patta» sharti buzilgan"
        )

    # ---- (3) QAYTA YUGURISH: sanoq HAM, qiymat HAM, vaqt HAM o'zgarmaydi.
    again = await billing_close(app_sessionmaker, business_date=day)
    assert again.charged == 0, "qayta yugurish YANGI hisob yozdi"

    after = _charges(sync_owner_conn, market_id, day)
    assert after == written, (
        "qayta yugurishdan keyin hisob qatorlari o'zgardi — `amount_soum` yoki "
        f"`created_at` qayta yozilgan (D-06):\n  oldin: {written}\n  keyin: {after}"
    )

    # ---- (4) ⛔ QAYTA YUGURISH **JIM** BO'LISHI SHART, «TO'SILGAN» EMAS.
    #
    # ⛔ BU IKKI ASSERT SABOTAJ BILAN TUG'ILDI (S-1, 06-14). `write_charge`
    #    dagi `DO NOTHING` -> `DO UPDATE` almashtirilganda yuqoridagi uchala
    #    da'vo ham YASHIL qolardi: `daily_charges` ustidagi o'zgarmaslik
    #    triggeri `UPDATE` ni P0001 bilan rad etadi, job esa istisnoni
    #    YUTADI (`errors` ga TUR yozadi) va qator soni ham, qiymatlar ham
    #    o'zgarmaydi. Ya'ni sabotaj sistemaga YETIB BORGAN, lekin tanlangan
    #    HOLAT ikkala shoxda bir xil natija berardi — 05-15 ning S-D darsi
    #    AYNAN shu sinf.
    #
    # ⛔ Tuzatish TESTDA emas, HOLATDA: idempotentlik «hech nima o'zgarmadi»
    #    emas, «job qatorni ALLAQACHON BOR deb TANIDI va JIM o'tdi» degani.
    #    Ikkinchi shoxda hisob har kecha triggerga urilib turardi va u
    #    faqat jurnalda ko'rinardi.
    assert again.errors == [], (
        f"qayta yugurish xato bilan tugadi: {again.errors} — idempotentlik "
        "«yozuvni qayta yozishga urinib, qo'riqchiga urilish» EMAS (D-06)"
    )
    assert again.skipped_existing >= len(written), (
        f"qayta yugurish {again.skipped_existing} ta mavjud hisobni tanidi, yozilgani "
        f"esa {len(written)} ta — job konfliktni `ON CONFLICT DO NOTHING` yo'lidan "
        "o'tkazmayapti"
    )


# ===========================================================================
# SC#2 — «Har hisob yozuvidan dalil-kadrlarga o'tish mumkin; hisob
#         yaratilgach o'zgarmaydi — tuzatish faqat sabab ko'rsatilgan
#         `charge_adjustments` yozuvi sifatida ko'rinadi»
# ===========================================================================


async def test_sc2_charge_reaches_evidence_and_cannot_be_edited(
    sync_owner_conn: Connection[TupleRow],
    app_sessionmaker: async_sessionmaker[AsyncSession],
    api_client: httpx.AsyncClient,
    director_headers: dict[str, str],
    s3_client: SnapshotStorage,
    scenario: Scenario,
    env: Env,
) -> None:
    """SC#2: «Har hisob yozuvidan dalil-kadrlarga o'tish mumkin; hisob
    yaratilgach o'zgarmaydi — tuzatish faqat sabab ko'rsatilgan
    `charge_adjustments` yozuvi sifatida ko'rinadi».

    =========================================================================
    ⛔⛔ «O'TISH MUMKIN» — MARSHRUTGACHA BORILADI, HAVOLA SANALMAYDI.

    `charge_evidence.occupancy_event_id` ning MAVJUDLIGI «dalilga o'tish
    mumkin» degani EMAS: pointer to'g'ri bo'lib, kadr esa ombordan
    o'chirilgan yoki marshrut yopiq bo'lishi mumkin. Shuning uchun zanjir
    OXIRIGACHA yuriladi:

        daily_charges -> charge_evidence -> occupancy_events.snapshot_id
                      -> GET /snapshots/{id}/image  -> 200 + `image/jpeg`

    ⛔ BAYTLAR OMBORGA HAQIQATAN YOZILADI (mock YO'Q): 04-06 da o'lchangan
       qoida — mock'langan ombor «kod ombor bilan gaplasha oladi» da'vosini
       umuman sinamaydi va yashil bo'lib turaveradi.

    ⛔ DIREKTOR SESSIYASI: dalil kadri `REPORT_VIEW` ostida va aynan
       direktor nizoda uni ochadi (D-02).
    =========================================================================
    """
    day = scenario.day
    market_id = env.market_id
    await _materialise_and_close(app_sessionmaker, day)

    charge_id = _charge_id(sync_owner_conn, market_id, scenario.two_ai_slots, day)

    # ---- (a) DALIL ZANJIRI OXIRIGACHA.
    evidence = sync_owner_conn.execute(
        "SELECT ce.occupancy_event_id, ev.snapshot_id, s.object_key "
        "FROM charge_evidence AS ce "
        "JOIN occupancy_events AS ev ON ev.id = ce.occupancy_event_id "
        "JOIN snapshots AS s ON s.id = ev.snapshot_id "
        "WHERE ce.market_id = %s AND ce.charge_id = %s ORDER BY ce.slot_time",
        (str(market_id), str(charge_id)),
    ).fetchall()
    assert evidence, (
        "hisobga birorta dalil qatori bog'lanmagan — BILL-02 ning «dalil-kadrlarga "
        "o'tish mumkin» sharti bajarilmaydi"
    )
    event_id, snapshot_id, object_key = evidence[0]
    assert event_id is not None, "`occupancy_event_id` bo'sh — muzlatilgan dalil YO'Q (D-08)"

    payload = frame_bytes(mean=118, stddev=44)
    await s3_client.put(str(object_key), payload)
    try:
        image = await api_client.get(
            f"{SNAPSHOTS_URL}/{snapshot_id}/image", headers=director_headers
        )
    finally:
        await s3_client.delete_many([str(object_key)])

    assert image.status_code == 200, image.text
    assert image.headers["content-type"] == "image/jpeg"
    assert image.content == payload, "dalil kadri boshqa baytlarni qaytardi"

    # ---- (b) HISOB O'ZGARMAS: `UPDATE` ham, `DELETE` ham RAD ETILADI.
    with pytest.raises(psycopg.errors.RaiseException):
        sync_owner_conn.execute(
            "UPDATE daily_charges SET amount_soum = 1 WHERE id = %s", (str(charge_id),)
        )
    with pytest.raises(psycopg.errors.RaiseException):
        sync_owner_conn.execute("DELETE FROM daily_charges WHERE id = %s", (str(charge_id),))

    # ---- (c) TUZATISH YO'LI OCHIQ VA U AUDITDA IZ QOLDIRADI.
    sync_owner_conn.execute(SET_MARKET, (str(market_id),))
    try:
        audited_before = _rows(sync_owner_conn, AUDIT_COUNT, ("charge_adjustments",))
        sync_owner_conn.execute(
            "INSERT INTO charge_adjustments "
            "(market_id, charge_id, direction, reason_code, amount_soum, actor_user_id) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (
                str(market_id),
                str(charge_id),
                AdjustmentDirection.DECREASE.value,
                AdjustmentReason.LATE_REVIEW.value,
                5_000,
                str(env.cashier_id),
            ),
        )
        audited_after = _rows(sync_owner_conn, AUDIT_COUNT, ("charge_adjustments",))
    finally:
        sync_owner_conn.execute(SET_MARKET, ("",))

    assert audited_after == audited_before + 1, (
        f"tuzatish auditga tushmadi ({audited_before} -> {audited_after}) — «kim qaror "
        "qildi?» savoli javobsiz qoladi (D-02)"
    )

    amount = sync_owner_conn.execute(
        "SELECT amount_soum FROM daily_charges WHERE id = %s", (str(charge_id),)
    ).fetchone()
    assert amount is not None and amount[0] == env.day_total_amount(day), (
        "tuzatish ASL hisobni o'zgartirdi — u ALOHIDA qator bo'lishi shart"
    )


# ===========================================================================
# SC#3 — «Qarz faqat biriktirilgan sotuvchida ko'rinadi (qoldiq har doim
#         hisoblanadigan ko'rinish: hisoblar − to'lovlar); biriktirilmagan
#         band rasta hisob emas, "ro'yxatga olinmagan savdo" anomaliyasi
#         sifatida chiqadi»
# ===========================================================================


async def test_sc3_debt_is_computed_and_unassigned_becomes_anomaly(
    sync_owner_conn: Connection[TupleRow],
    app_sessionmaker: async_sessionmaker[AsyncSession],
    tenant_session: TenantSessionFactory,
    scenario: Scenario,
    env: Env,
) -> None:
    """SC#3: «Qarz faqat biriktirilgan sotuvchida ko'rinadi (qoldiq har doim
    hisoblanadigan ko'rinish: hisoblar − to'lovlar); biriktirilmagan band
    rasta hisob emas, "ro'yxatga olinmagan savdo" anomaliyasi sifatida
    chiqadi».

    =========================================================================
    ⛔ «HISOBLANADIGAN KO'RINISH» IKKI YO'LDAN O'LCHANADI VA IKKALASI HAM
       KERAK:

      (1) XULQ  — `vendor_outstanding()` yozilgan hisobni QAYTARADI;
      (2) SXEMA — `daily_charges` va `vendors` da nomi `balance` bilan
          boshlanadigan/tugaydigan ustun ⛔ **YO'Q**, va bu ⛔ **TO'PLAM
          TENGLIGI** bilan (D-31).

    Yolg'iz (1) saqlangan balans ustuni qo'shilgan kuni ham yashil
    qolardi (ustun bor, ko'rinish ham to'g'ri ishlaydi — DRIFT esa
    keyinroq boshlanadi). Yolg'iz (2) esa hisob-kitobning O'ZI buzilganini
    ko'rmasdi.

    =========================================================================
    ⛔⛔ D-24 NING JAVOBI HAMON TASDIQ — VA U SHU YERDA QAYTA YOZILMAYDI.

    «Bitta to'lov N kunlik qarzni yopganda qaysi kunning pattasi
    to'landi?» savolining javobi HOSILA FIFO ko'rinish (G-13/G-14) va u
    ikki qatlamda O'LCHANGAN: `tests/unit/test_payment_credit_rules.py`
    (jadval testi) va `test_billing_repo.py::vendor_charge_allocation`.

    Bu yerda faqat javobning ⛔ **SHAKLI** tekshiriladi: qoida NOMLANGAN
    va u FIFO; saqlangan taqsimlash jadvali ⛔ **YO'Q**. Qoidaning o'zini
    qayta yozish ⛔ **ikkinchi haqiqat** bo'lardi (G-20/G-21 bilan aynan
    bir xil naqsh).
    """
    day = scenario.day
    market_id = env.market_id
    await _materialise_and_close(app_sessionmaker, day)

    # ---- (a) BIRIKTIRILGAN RASTA: hisob VA qoldiq.
    charged = _charges(sync_owner_conn, market_id, day)
    assert scenario.two_ai_slots in charged, "nazorat: biriktirilgan rastaga hisob yozilmagan"

    async with tenant_session(market_id) as session:
        outstanding = await billing_repo.vendor_outstanding(
            session, market_id=market_id, vendor_ids=[env.vendor_id], as_of=env.today
        )
    assert outstanding.get(env.vendor_id, 0) >= env.tariff_amount(day), (
        "biriktirilgan sotuvchining qoldig'i yozilgan hisobni QAMRAMADI — «qarz "
        f"biriktirilgan sotuvchida ko'rinadi» sharti buzilgan: {outstanding}"
    )

    # ---- (b) BIRIKTIRILMAGAN BAND RASTA: 0 hisob, 1 anomaliya.
    assert scenario.unassigned not in charged, (
        "sotuvchisiz rastaga hisob yozildi — «kimdir qarzdor, lekin kim ekani "
        "noma'lum» yozuvi qarz hisobotini buzardi (D-28)"
    )
    anomalies = sync_owner_conn.execute(
        "SELECT count(*) FROM billing_anomalies "
        "WHERE market_id = %s AND service_date = %s AND stall_id = %s AND kind = %s",
        (
            str(market_id),
            day,
            str(scenario.unassigned),
            AnomalyKind.UNASSIGNED_OCCUPIED.value,
        ),
    ).fetchone()
    assert anomalies is not None and anomalies[0] == 1, (
        "«ro'yxatga olinmagan savdo» anomaliyasi yozilmadi — band rasta JIMGINA "
        f"yo'qoldi (BILL-04): {anomalies}"
    )

    # ---- (c) SAQLANGAN BALANS USTUNI YO'Q — TO'PLAM TENGLIGI bilan.
    for table in ("daily_charges", "vendors"):
        stored = {
            name
            for name in _column_names(sync_owner_conn, table)
            if name.startswith("balance") or name.endswith("balance")
        }
        assert stored == set(), (
            f"⛔ BILL-03: `{table}` da saqlangan balans ustuni paydo bo'ldi: {sorted(stored)} — "
            "qoldiq HAR DOIM hisoblanadigan ko'rinish bo'lishi shart (drift nizoga aylanadi)"
        )

    # ---- (d) D-24: qoida NOMLANGAN, taqsimlash SAQLANMAYDI.
    assert ALLOCATION_RULE == "FIFO_OLDEST_SERVICE_DATE_FIRST", (
        f"taqsimlash qoidasi o'zgargan ({ALLOCATION_RULE!r}) — D-24 ning javobi "
        "«eng qadimgi kundan boshlanadi» edi va uni jimgina almashtirish "
        "«qaysi kunning pattasi to'landi?» savolini boshqa javobga o'tkazardi"
    )
    rules_table = _REPO_ROOT / "tests" / "unit" / "test_payment_credit_rules.py"
    assert rules_table.is_file(), (
        f"{rules_table} YO'Q — D-24 ning jadval testi (G-13 ning birinchi qatlami) "
        "o'chirilgan va qoida hech qayerda o'lchanmay qolgan"
    )
    tables = sync_owner_conn.execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'public' AND table_name = 'payment_allocations'"
    ).fetchall()
    assert tables == [], (
        "`payment_allocations` jadvali paydo bo'ldi — D-07/BILL-03 bo'yicha "
        "taqsimlash SAQLANMAYDI, u hosila ko'rinish"
    )
    allocated = {
        name for name in _column_names(sync_owner_conn, "payments") if name.startswith("allocated")
    }
    assert allocated == set(), (
        f"`payments` da saqlangan taqsimlash ustuni paydo bo'ldi: {sorted(allocated)}"
    )


# ===========================================================================
# SC#4 — «Kun davomida kassir/direktor "kutilayotgan patta"ni (bugungi
#         tarif + eski qarz) jonli ko'radi; kassir rastani raqamdan topib,
#         tarifdan kelgan summani ≤3 bosishda tasdiqlaydi va summani faqat
#         sabab-kod bilan o'zgartira oladi»
# ===========================================================================

THREE_TAP_TEST = Path("frontend/src/components/collect/collect-session.test.tsx")
"""G-20 ning egasi — ≤3 o'zaro ta'sir sanog'i (06-11)."""

SINGLE_REQUEST_TEST = Path("frontend/src/components/collect/payment-bar.test.tsx")
"""G-21 ning egasi — `useRef` qulfi (06-11)."""

GATE_FRONTEND_STEP = "npm --prefix frontend test"
"""⛔ `package.json::gate` ZANJIRIDA BO'LISHI SHART BO'LGAN QADAM.

Bu satrning mavjudligi — «vitest darvozasi fazaning yetkazib berish
buyrug'iga ULANGAN» degan da'voning YAGONA mexanik shakli. U yo'qolsa
G-20/G-21 testlari repoda qolib, HECH QACHON yugurmasdi va ikkala mezon
ham «yashil» hisobotda ko'rinardi.
"""

PENDING_STALL_KEYS = frozenset(
    {
        "stall_code",
        "service_date",
        "market_open",
        "amount_soum",
        "amount_unavailable_reason",
        "outstanding_soum",
        "total_due_soum",
        "stall_status",
        "vendor_assigned",
        # 0027 — kunlik patta IKKI KOMPONENTLI (rasta puli + xizmat haqi).
        "stall_amount_soum",
        "fee_amount_soum",
        "fee_label",
    }
)
"""UI-SPEC §9.2 ning kalitlari — ⛔ `charge_id` UMUMAN YO'Q (D-17).

⛔ RO'YXAT QO'LDA YOZILGAN VA BU ATAYIN: u KUTILGAN NATIJA, o'lchov emas.
   Uni `PendingStallResponse.model_fields` dan hosila qilish testni «model
   o'ziga teng» degan tavtologiyaga aylantirardi.

⚠ TO'QQIZDAN O'N IKKIGA (0027): uch maydon kunlik pattaning IKKI
  komponentini ochadi. SC#4 ning `charge_id` YO'Q da'vosi O'ZGARMADI va u
  hamon TO'PLAM TENGLIGI bilan o'lchanadi.

⚠ YETTIDAN TO'QQIZGA (quick 260816-75c): `stall_status` + `vendor_assigned`.
  SC#4 ning `charge_id` YO'Q da'vosi O'ZGARMADI va u hamon TO'PLAM
  TENGLIGI bilan o'lchanadi — ya'ni yangi maydonlar darvozani
  bo'shatmadi, faqat kutilgan natijani AYNAN ikkitaga kengaytirdi.
"""


def _gate_chain() -> str:
    """`package.json` dagi `gate` zanjiri — ⛔ FAYLDAN, nusxadan EMAS.

    ⚠ JSON PARSERI ATAYIN ISHLATILMAYDI: `gate` qiymati BIR SATRDA yashaydi
      va uni satr sifatida o'qish parserning butun xato yuzasini (izohli
      kalitlar, ekranlangan qo'shtirnoqlar) darvozadan chiqarib tashlaydi.
      NAZORAT bilan: satr AYNAN BITTA bo'lishi shart.
    """
    source = (_REPO_ROOT / "package.json").read_text(encoding="utf-8")
    lines = [line.strip() for line in source.splitlines() if line.strip().startswith('"gate":')]
    assert len(lines) == 1, (
        f"`package.json` da {len(lines)} ta `gate` qatori topildi — skaner boshqa "
        "shaklda ishlayapti va darvoza jimgina yashil bo'lardi"
    )
    return lines[0]


async def test_sc4_pending_projection_and_three_step_confirmation(
    api_client: httpx.AsyncClient,
    tenant_session: TenantSessionFactory,
    cashier_headers: dict[str, str],
    env: Env,
) -> None:
    """SC#4: «Kun davomida kassir/direktor "kutilayotgan patta"ni (bugungi
    tarif + eski qarz) jonli ko'radi; kassir rastani raqamdan topib,
    tarifdan kelgan summani ≤3 bosishda tasdiqlaydi va summani faqat
    sabab-kod bilan o'zgartira oladi».

    =========================================================================
    (a) PROYEKSIYA HISOB EMAS — `charge_id` ⛔ UMUMAN E'LON QILINMAGAN
        (D-17), va bu TO'PLAM TENGLIGI bilan o'lchanadi: `not in` faqat
        AYNAN o'sha nomni ushlaydi va `chargeId` jimgina o'tib ketardi.

        ⛔ SUMMA YAGONA FUNKSIYADAN (D-16): `resolve_stall_day_money()` va
           `pending_projection()` — IKKI CHAQIRUV, BIR NATIJA. Ular ajralib
           ketsa kassir ko'rgan son bilan kechqurun yozilgan son boshqa
           bo'lardi va nizoda IKKALASI ham «to'g'ri» bo'lardi.

    (b) ≤3 BOSISH ⛔ **FRONTENDDA** o'lchanadi (G-20) va bu yerda uning
        DARVOZAGA ULANGANI tasdiqlanadi — modul docstringidagi «chok»
        bandi. Sanoqning O'ZI bu yerda qayta yozilmaydi.

    (c) SABAB-KODSIZ SUMMA O'ZGARTIRISH -> ⛔ **422** (HTTP bilan, haqiqiy
        marshrutdan).
    =========================================================================
    """
    stall_id = env.stall("stall_with_two_occupied_slots")
    code = env.code(stall_id)

    # ---- (a) KALITLAR TO'PLAMI + IKKI CHAQIRUV, BIR NATIJA.
    response = await api_client.get(
        PENDING_URL, params={"stall_code": code}, headers=cashier_headers
    )
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()

    assert set(body) == PENDING_STALL_KEYS, (
        f"§9.2 ning kalitlar to'plami buzilgan: {sorted(body)}. ⛔ `charge_id` bu "
        "javobda MAVJUD EMAS — proyeksiya HISOB EMAS (D-17)"
    )

    as_of = date.fromisoformat(str(body["service_date"]))
    async with tenant_session(env.market_id) as session:
        money = await billing_repo.resolve_stall_day_money(
            session, market_id=env.market_id, as_of=as_of, stall_code=code
        )
        projection = await billing_repo.pending_projection(
            session, market_id=env.market_id, as_of=as_of, stall_code=code
        )
    assert len(money) == 1, f"nazorat: {code!r} kodiga {len(money)} ta rasta mos keldi"
    assert projection.stall is not None, "nazorat: proyeksiya aniq moslikni qaytarmadi"

    assert money[0].amount_soum == projection.stall.amount_soum, (
        "⛔ D-16: `resolve_stall_day_money()` va `pending_projection()` BOSHQA summa "
        f"berdi ({money[0].amount_soum} != {projection.stall.amount_soum}) — kassir "
        "ko'rgan son bilan kechqurun yoziladigan son AJRALIB KETGAN"
    )
    assert body["amount_soum"] == projection.stall.amount_soum, (
        "HTTP javobi repozitoriy javobidan farq qildi — handler pul mantig'i yozgan"
    )

    # ---- (b) ≤3 BOSISH: DARVOZAGA ULANGAN VITEST TESTI.
    counter = (_REPO_ROOT / THREE_TAP_TEST).read_text(encoding="utf-8")
    assert "toBe(3)" in counter, (
        f"{THREE_TAP_TEST} matnida `toBe(3)` YO'Q — G-20 ning chegarasi ANIQ son "
        "bilan yozilmagan va «≤3» da'vosi o'lchanmay qolgan"
    )
    assert GATE_FRONTEND_STEP in _gate_chain(), (
        f"`package.json::gate` zanjirida {GATE_FRONTEND_STEP!r} qadami YO'Q — G-20 "
        "testi repoda qolib, fazaning yetkazib berish buyrug'ida HECH QACHON "
        "yugurmasdi"
    )

    # ---- (c) SABAB-KODSIZ SUMMA O'ZGARTIRISH -> 422.
    rejected = await api_client.post(
        PAYMENTS_URL,
        json={
            "idempotency_key": f"sc4-sabab-kodsiz-{uuid4()}",
            "stall_code": code,
            "method": "cash",
            "amount_soum": max(env.tariff_amount() - 5_000, 1),
        },
        headers=cashier_headers,
    )
    assert rejected.status_code == 422, (
        f"sabab-kodsiz chetlangan summa QABUL QILINDI ({rejected.status_code}) — CASH-02 "
        f"buzilgan: {rejected.text}"
    )


# ===========================================================================
# SC#5 — «Takror bosilgan to'lov dublikat yaratmaydi, tuzatish faqat storno
#         + qayta kiritish orqali; smena yopilishida kassir tizim summasini
#         ko'rmasdan naqdni deklaratsiya qiladi va farq (variance) direktor
#         hisobotiga chiqadi»
# ===========================================================================

CLOSE_RESPONSE_KEYS = frozenset({"id", "status", "declared_soum", "closed_at"})
"""`POST /shifts/{id}/close` ning AYNAN TO'RT kaliti (UI-SPEC §10.3).

⛔ `system_*` NOMLI MAYDON YO'Q va bu TO'PLAM TENGLIGI bilan o'lchanadi:
   brauzerga yetgan maydon O'QILADI (DevTools, tarmoq paneli), ya'ni
   «ko'rsatmayapmiz» kod-ko'rik DA'VOSI, o'lchov emas.
"""


async def test_sc5_idempotent_payment_reversal_and_blind_variance(
    sync_owner_conn: Connection[TupleRow],
    api_client: httpx.AsyncClient,
    cashier_headers: dict[str, str],
    director_headers: dict[str, str],
    env: Env,
) -> None:
    """SC#5: «Takror bosilgan to'lov dublikat yaratmaydi, tuzatish faqat
    storno + qayta kiritish orqali; smena yopilishida kassir tizim summasini
    ko'rmasdan naqdni deklaratsiya qiladi va farq (variance) direktor
    hisobotiga chiqadi».

    =========================================================================
    ⛔⛔ (d) VARIANCE `GET /shifts?day=` DA O'LCHANADI, `close` JAVOBIDA EMAS
        (UI-SPEC §10.4). Sabab matematik: `system = declared − variance` —
        BITTA AYIRISH, ya'ni farqni yopish javobida qaytarish tizim
        summasini qaytarish bilan AYNI narsa.

    ⛔ IKKI YO'NALISH HAM O'LCHANADI VA ULAR HAR XIL KATTALIKDA: `declared <
       system` (manfiy) va `declared > system` (musbat). Ikkalasi bir xil
       kattalikda bo'lganda modul-kattalik sabotaji (`abs(...)`) ikkala
       qatorni bir xil songa aylantirib, farqni KO'RSATMASDAN qolardi
       (05-15 ning S-D darsi: da'vo susaytirilmaydi, HOLAT kengaytiriladi).
    =========================================================================
    """
    stall_id = env.stall("stall_with_two_occupied_slots")
    code = env.code(stall_id)
    amount = env.tariff_amount()

    # ⛔ PREKONDITSIYA: bugun A bozori uchun OCHIQ kun bo'lishi SHART.
    #   Seed'da A dushanba yopiq (`A_OPEN_WEEKDAYS = 2..7`) va bu test
    #   2026-08-17 (dushanba) kuni POST /payments -> 422 `market_closed`
    #   bilan yiqildi [O'LCHANDI: 09-07 gate o'lchovi]. SC#5 ning da'vosi
    #   idempotentlik/storno/variance — kun jadvali emas; yopiq kun rad
    #   etish xulqining o'z testlari bor (`test_market_calendar.py`).
    sync_owner_conn.execute(
        "UPDATE market_profile SET open_weekdays = %s WHERE market_id = %s",
        ([1, 2, 3, 4, 5, 6, 7], str(env.market_id)),
    )

    # ---- (a) BIR XIL KALIT IKKI MARTA -> 1 QATOR, 200, O'SHA `id`.
    payload = {
        "idempotency_key": f"sc5-takror-{uuid4()}",
        "stall_code": code,
        "method": "cash",
        "amount_soum": amount,
    }
    first = await api_client.post(PAYMENTS_URL, json=payload, headers=cashier_headers)
    assert first.status_code == 201, first.text
    second = await api_client.post(PAYMENTS_URL, json=payload, headers=cashier_headers)
    assert second.status_code == 200, (
        f"takror so'rov {second.status_code} qaytardi — D-21 bo'yicha u kassir uchun "
        f"KO'RINMAS bo'lishi kerak: {second.text}"
    )
    assert second.json()["payment_id"] == first.json()["payment_id"]

    written = _rows(
        sync_owner_conn,
        "SELECT count(*) FROM payments WHERE market_id = %s",
        (str(env.market_id),),
    )
    assert written == 1, f"takror so'rov IKKINCHI qator yozdi ({written}) — CASH-03 buzilgan"

    # ---- (b) UCH TEZ BOSISH: DARVOZAGA ULANGAN VITEST TESTI (G-21).
    lock = (_REPO_ROOT / SINGLE_REQUEST_TEST).read_text(encoding="utf-8")
    assert "toHaveLength(1)" in lock, (
        f"{SINGLE_REQUEST_TEST} matnida «AYNAN bitta so'rov» asserti YO'Q — G-21 ning "
        "chegarasi o'lchanmay qolgan"
    )
    assert GATE_FRONTEND_STEP in _gate_chain(), (
        f"`package.json::gate` zanjirida {GATE_FRONTEND_STEP!r} qadami YO'Q — G-21 "
        "testi fazaning yetkazib berish buyrug'ida HECH QACHON yugurmasdi"
    )

    # ---- (c) TO'LOV O'ZGARMAS; TUZATISH FAQAT YANGI QATOR (STORNO).
    payment_id = UUID(str(first.json()["payment_id"]))
    with pytest.raises(psycopg.errors.RaiseException):
        sync_owner_conn.execute(
            "UPDATE payments SET amount_soum = 1 WHERE id = %s", (str(payment_id),)
        )

    reversal = await api_client.post(
        f"{PAYMENTS_URL}/{payment_id}/reverse",
        json={"reason_code": "wrong_amount"},
        headers=cashier_headers,
    )
    assert reversal.status_code == 201, reversal.text
    kinds = sync_owner_conn.execute(
        "SELECT kind, reversal_reason FROM payments WHERE market_id = %s ORDER BY kind",
        (str(env.market_id),),
    ).fetchall()
    assert len(kinds) == 2, f"storno YANGI qator yozmadi: {kinds}"
    reversal_row = next(row for row in kinds if str(row[0]) == "reversal")
    assert reversal_row[1], "storno SABABSIZ yozildi — D-23 buzilgan"

    # ⛔ SABAB MAJBURIY: bo'sh sabab bilan storno IFODALAB BO'LMAYDI.
    #   ⚠ Qator SEEDNING yozuvchisi bilan quriladi, xom `INSERT` matni bu
    #     yerda TAKRORLANMAYDI — `ck_payments_reversal_reason_is_paired`
    #     ning shakli `fixtures/billing_domain.add_payment()` da yashaydi.
    with pytest.raises(psycopg.errors.CheckViolation) as unnamed:
        add_payment(
            sync_owner_conn,
            market_id=env.market_id,
            stall_id=stall_id,
            vendor_id=env.vendor_id,
            cashier_id=env.cashier_id,
            shift_id=env.live.open_shift_id,
            kind=PaymentKind.REVERSAL.value,
            reverses_payment_id=payment_id,
            reversal_reason=None,
        )
    assert "reversal_reason_is_paired" in str(unnamed.value), (
        f"xato boshqa konstraytdan keldi: {unnamed.value!r}"
    )

    # ---- (d) KO'R DEKLARATSIYA + IKKI TOMONLAMA FARQ.
    #
    # ⛔ AVVAL YANGI TO'LOV YOZILADI VA BU ZARURAT, BEZAK EMAS: yuqoridagi
    #    (c) storno tizim summasini AYNAN nolga tushirdi (`+amount − amount`)
    #    va nol tizim summasi ustida «declared < system» holatini IFODALAB
    #    BO'LMASDI — deklaratsiya manfiy bo'lishi kerak bo'lardi, uni esa
    #    `ck_cashier_shifts_declared_soum_non_negative` rad etadi.
    fresh = await api_client.post(
        PAYMENTS_URL,
        json={
            "idempotency_key": f"sc5-yangi-{uuid4()}",
            "stall_code": code,
            "method": "cash",
            "amount_soum": amount,
        },
        headers=cashier_headers,
    )
    assert fresh.status_code == 201, fresh.text

    shortfall_shift = env.live.open_shift_id
    closed = await api_client.post(
        f"{SHIFTS_URL}/{shortfall_shift}/close",
        json={"declared_soum": amount - 5_000},
        headers=cashier_headers,
    )
    assert closed.status_code == 200, closed.text
    assert set(closed.json()) == CLOSE_RESPONSE_KEYS, (
        f"§10.3 ning kalitlar to'plami buzilgan: {sorted(closed.json())} — kassir "
        "tizim summasini KO'RMASLIGI shart (D-25)"
    )

    surplus_shift = uuid4()
    sync_owner_conn.execute(
        "INSERT INTO cashier_shifts (id, market_id, cashier_id, status) VALUES (%s, %s, %s, %s)",
        (
            str(surplus_shift),
            str(env.market_id),
            str(env.cashier_id),
            ShiftStatus.OPEN.value,
        ),
    )
    surplus_closed = await api_client.post(
        f"{SHIFTS_URL}/{surplus_shift}/close",
        json={"declared_soum": 7_000},
        headers=cashier_headers,
    )
    assert surplus_closed.status_code == 200, surplus_closed.text

    report = await api_client.get(
        SHIFTS_URL, params={"day": env.today.isoformat()}, headers=director_headers
    )
    assert report.status_code == 200, report.text
    by_id = {row["id"]: row for row in report.json()["rows"]}

    shortfall = by_id[str(shortfall_shift)]
    assert shortfall["variance_soum"] == -5_000, (
        f"⛔ KAMOMAD AYNAN `-5 000` bo'lishi SHART (D-26): {shortfall}"
    )
    surplus = by_id[str(surplus_shift)]
    assert surplus["variance_soum"] == 7_000, (
        "⛔ SC#5(d): `declared > system` holati MUSBAT farq bilan qaytarilishi shart — "
        f"ortiqcha naqdni jim yutish kamomadni yashirish bilan BIR XIL xato: {surplus}"
    )
    assert shortfall["variance_soum"] != -surplus["variance_soum"], (
        "nazorat: ikki yo'nalish BIR XIL kattalikda — modul-kattalik sabotaji ikkala "
        "qatorni ham bir xil songa aylantirib, farqni ko'rsatmasdan qolardi"
    )


# ===========================================================================
# META — MEZONLARDAN BIRORTASI JIMGINA TUSHIB QOLMASIN
# ===========================================================================


def test_every_criterion_has_its_own_test() -> None:
    """Beshala mezon uchun AYNAN BITTA nomlangan test mavjud (G-1).

    USIZ MEZONLARDAN BIRI JIMGINA TUSHIB QOLARDI: fayl qayta tashkil
    qilinganda yoki test vaqtincha o'chirilganda darvoza baribir yashil
    bo'lardi va «beshala mezon o'lchanadi» da'vosi isbotsiz qolardi.

    ⚠ META-TESTNING O'Z NOMIDA `sc<raqam>` YO'Q va bu ataylab: darvoza
      `sc[1-5]` naqshini SANAYDI, ya'ni meta-testning o'zi sanoqqa kirib
      ketmasligi kerak.

    ⛔ RO'YXAT MODUL INTROSPEKSIYASIDAN HOSILA (`inspect.getmembers`),
       qo'lda YOZILMAYDI: qo'lda yozilgan ro'yxat test o'chirilganda u
       bilan BIRGA tahrirlanardi va darvoza qizarmasdi.
    """
    module = sys.modules[__name__]
    names = sorted(
        name
        for name, obj in inspect.getmembers(module, inspect.isfunction)
        if name.startswith("test_") and obj.__module__ == __name__
    )
    assert len(names) >= 7, (
        f"modulda faqat {len(names)} ta test topildi — introspeksiya BO'SH ro'yxatda "
        "ishlayotgan bo'lsa bu darvoza jimgina yashil bo'lardi"
    )

    for number in range(1, 6):
        owned = [name for name in names if name.startswith(f"test_sc{number}_")]
        assert len(owned) == 1, (
            f"SC#{number} uchun {len(owned)} ta test topildi ({owned}) — har mezonning "
            "egasi AYNAN BITTA nomlangan test bo'lishi kerak"
        )

    criteria = [name for name in names if name.startswith("test_sc")]
    assert len(criteria) == 5, f"mezon testlari soni 5 emas: {criteria}"


def test_criteria_module_uses_no_fakes() -> None:
    """SOXTALASHTIRISHSIZ O'LCHOV DARVOZASI — IKKI MUSTAQIL YO'L.

    =======================================================================
    NEGA IKKI YO'L KERAK VA NEGA BIRI YETMAYDI.

    Soxtalashtirishning ikki shakli bor va ular BOSHQA-BOSHQA izda qoladi:

      1. KUTUBXONA IMPORTI — `ast` daraxtida ko'rinadi. Satr bo'yicha
         qidiruv izohni koddan ajrata olmasdi, shuning uchun daraxt
         o'qiladi.
      2. FIXTURE SO'ROVI (pytest'ning O'Z tuzatuvchi fixture'i yoki
         loyihaning `enqueued` spy'i) — birorta IMPORT talab qilmaydi,
         ya'ni birinchi yo'l uni UMUMAN ko'rmasdi. U modul global nomlari
         va test imzolari orqali topiladi.

    ⚠ UCHINCHI DA'VO — DARAXTNING BO'SH BO'LMASLIGI. Skaner nosozlansa
      yoki fayl qayta nomlansa ikkala to'plam ham bo'sh chiqib, darvoza
      TRIVIAL ravishda yashil bo'lardi.

    =======================================================================
    ⛔⛔ BU FAZAGA XOS TAQIQ — SUZUVCHI ARIFMETIKA (D-11).

    5-fazada taqiq ANIQLIK METRIKASI nomlariga qo'yilgan edi, chunki
    o'sha fazaning yolg'oni «mexanika yashil, demak model ishlaydi»
    bo'lardi. Bu fazada haqiqat mavjud va yolg'onning shakli BOSHQA:
    summa YAXLITLANIB ketishi mumkin. Shuning uchun bu yerda `float`,
    o'nlik-kasr tipi va yaxlitlash amali TAQIQLANADI — pul `bigint` so'm
    ↔ Python `int` bo'lib qoladi.

    ⛔ «O'TKAZIB YUBORISH» YO'LI ATAYIN YO'Q: bu yerda `skipif` ham,
       `xfail` ham yo'q. Soxtalashtirilgan mezon — «faza tugadi» degan
       da'voning eng arzon yolg'on shakli.
    =======================================================================
    """
    tree = ast.parse(_MODULE_PATH.read_text(encoding="utf-8"))

    roots: set[str] = set()
    imported_names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots |= {alias.name.split(".")[0] for alias in node.names}
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                roots.add(node.module.split(".")[0])
            imported_names |= {alias.name for alias in node.names}

    assert len(roots) >= 10, (
        f"faqat {len(roots)} ta import ildizi topildi — `ast` skaneri bo'sh daraxtda "
        "ishlayotgan bo'lsa bu darvoza JIMGINA yashil bo'lardi"
    )
    assert not roots & _MOCK_ROOTS, (
        f"soxtalashtirish kutubxonasi import qilingan: {sorted(roots & _MOCK_ROOTS)} — "
        "bu fayl HAQIQIY `postgres:18.4`, HAQIQIY ombor va HAQIQIY marshrut grafi "
        "ustida o'lchaydi"
    )
    faked_imports = sorted(
        name for name in imported_names if name in _MOCK_NAMES or name.endswith(_MOCK_SUFFIX)
    )
    assert faked_imports == [], f"soxtalashtirish vositasi import qilingan: {faked_imports}"

    # ---- IKKINCHI YO'L: modul global nomlari VA test imzolari.
    module = sys.modules[__name__]
    globals_seen = set(vars(module))
    assert len(globals_seen) >= 20, (
        f"modul global nomlari faqat {len(globals_seen)} ta — ikkinchi yo'l BO'SH "
        "to'plamda ishlayotgan bo'lsa u ham jimgina yashil bo'lardi"
    )
    assert not globals_seen & _FAKE_FIXTURES, (
        f"soxtalashtiruvchi nom modul darajasida bog'langan: "
        f"{sorted(globals_seen & _FAKE_FIXTURES)}"
    )

    tests = [
        (name, obj)
        for name, obj in inspect.getmembers(module, inspect.isfunction)
        if name.startswith("test_") and obj.__module__ == __name__
    ]
    assert len(tests) >= 7, (
        f"modulda faqat {len(tests)} ta test topildi — imzo skaneri BO'SH ro'yxatda "
        "ishlayotgan bo'lsa bu darvoza ham jimgina yashil bo'lardi"
    )
    faked = sorted(
        f"{name}({', '.join(sorted(_FAKE_FIXTURES & set(inspect.signature(obj).parameters)))})"
        for name, obj in tests
        if _FAKE_FIXTURES & set(inspect.signature(obj).parameters)
    )
    assert faked == [], (
        f"quyidagi testlar soxtalashtiruvchi fixture so'rayapti: {faked} — mezon moduli "
        "na bazani, na omborni, na marshrut grafini almashtiradi"
    )

    # ---- D-11: SUZUVCHI ARIFMETIKA — IKKI TOMONDAN YOPILADI.
    named = _executable_names(tree)
    assert named, "`ast` daraxtida birorta bajariladigan nom topilmadi — skaner bo'sh"

    money = sorted(_BANNED_MONEY_NAMES & named)
    assert not money, (
        f"mezon modulida suzuvchi arifmetika nomi bor: {money} — pul `bigint` so'm ↔ "
        "Python `int` bo'lib qoladi va yaxlitlash amali mezon qatlamida UMUMAN "
        "paydo bo'lmasligi kerak (D-11)"
    )

    fractional = _fractional_constants(tree)
    assert all(0 <= value <= 1 for value in fractional), (
        f"mezon modulida [0, 1] dan tashqaridagi kasr konstanta bor: "
        f"{sorted(value for value in fractional if not 0 <= value <= 1)} — bu modulda "
        "kasr son FAQAT normalangan poligon geometriyasiga tegishli bo'lishi mumkin "
        "(0..1). Pul HAR DOIM butun so'm: kasr summa D-11 ni JIMGINA buzardi"
    )


def _executable_names(tree: ast.AST) -> set[str]:
    """Modulning BAJARILADIGAN nomlari — ⛔ TIP ANNOTATSIYALARI CHIQARILADI.

    =======================================================================
    ⛔ NEGA ANNOTATSIYA SANOQQA KIRMAYDI VA BU DA'VONI ZAIFLASHTIRMAYDI.

    D-11 ning taqig'i AMALGA qo'yilgan: son suzuvchi tipga o'girilmasin,
    yaxlitlanmasin, o'nlik-kasr tipida saqlanmasin. Poligon markazining
    `tuple[float, float]` annotatsiyasi esa AMAL emas — u normalangan
    (0..1) GEOMETRIYA va u bu modulda pul bilan hech qachon uchrashmaydi:
    koordinata `camera_zones.polygon` ga boradi, summa esa `bigint` so'm
    ustuniga.

    Annotatsiyani ham taqiqlash geometriyani `Any` bilan yozishga
    majburlardi, ya'ni darvoza `mypy --strict` ni buzib, HIMOYANI
    KAMAYTIRARDI. Buning o'rniga taqiq IKKINCHI tomondan yopiladi:
    `_fractional_constants()` har kasr konstantani [0, 1] oralig'iga
    qamaydi, ya'ni kasr SUMMA (`15_000.5`) shu modulda IFODALAB
    BO'LMAYDI.
    =======================================================================
    """
    names: set[str] = set()
    skipped = ("annotation", "returns")

    def walk(node: ast.AST) -> None:
        if isinstance(node, ast.Name):
            names.add(node.id.lower())
        elif isinstance(node, ast.Attribute):
            names.add(node.attr.lower())
        for field, value in ast.iter_fields(node):
            if field in skipped:
                continue
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, ast.AST):
                        walk(item)
            elif isinstance(value, ast.AST):
                walk(value)

    walk(tree)
    return names


def _fractional_constants(tree: ast.AST) -> list[Any]:
    """Modulning BUTUN BO'LMAGAN sonli konstantalari.

    ⚠ TIP NOMI BILAN TEKSHIRILMAYDI (`isinstance(..., <suzuvchi tip>)`):
      o'sha nom yuqoridagi darvozaning O'ZI tomonidan taqiqlangan va
      skaner o'zini o'zi qizartirardi. Shuning uchun tekshiruv TESKARI:
      butun son, satr, bayt va `None` chiqarib tashlanadi — qolgani
      ta'rifi bo'yicha kasr (yoki undan ham begonaroq) qiymat.
    """
    keep: list[Any] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant):
            continue
        value = node.value
        if isinstance(value, int | str | bytes) or value is None or value is Ellipsis:
            continue
        keep.append(value)
    return keep


def test_the_fake_registry_names_are_built_correctly() -> None:
    """NAZORAT — bo'laklab qurilgan reyestr AYNAN kutilgan nomlarni beradi.

    ⛔ USIZ BUTUN SOXTALASHTIRISH DARVOZASI JIMGINA BO'SHAB QOLARDI: bir
       harflik bo'laklash xatosi (`"pa" "tch"` -> `"patch"` o'rniga
       `"patch "`) hech qayerda ko'rinmasdi va yuqoridagi ikki to'plam
       hech qachon hech nimani ushlamasdi.

    ⚠ KUTILGAN NOMLAR HAM BO'LAKLAB QURILADI va sabab o'sha: bu modulning
      qabul mezoni matn skani bilan o'lchanadi (yuqoridagi bo'lim).
    """
    assert len(_PATCH) == 5, f"bo'laklash buzilgan: {_PATCH!r}"
    assert _PATCH in _MOCK_NAMES
    assert ("monkey" + _PATCH) in _FAKE_FIXTURES
    assert _MOCK_SUFFIX == "Moc" + "k", f"qo'shimcha buzilgan: {_MOCK_SUFFIX!r}"
    assert ("Magic" + _MOCK_SUFFIX).endswith(_MOCK_SUFFIX)
    assert not ("Magic" + _MOCK_SUFFIX).endswith("Mocks")


# ===========================================================================
# G-2 / G-3 / G-6 — MEZONLARDAN MUSTAQIL DARVOZALAR
# ===========================================================================


async def test_g2_service_date_matches_materialized_occupancy(
    sync_owner_conn: Connection[TupleRow],
    app_sessionmaker: async_sessionmaker[AsyncSession],
    scenario: Scenario,
    env: Env,
) -> None:
    """G-2: har yozilgan hisob uchun o'sha kunda slot qatori BOR.

    =========================================================================
    ⛔⛔ BU DARVOZA PITFALL 1 NI USHLAYDI — IKKI USTUN, IKKI MA'NO:

        stall_slot_occupancy.business_date = MA'LUMOT TEGISHLI kun
        daily_charges.business_date        = QATOR YOZILGAN kun (hosila)

    Hisobning domen ustuni `service_date` deb ATAYIN boshqa nomlangan.
    Ularni chalkashtirgan implementatsiya NORMAL kunda 0 qator berardi
    (job D+1 da yuguradi) — hisobot bo'sh, xato yo'q, va nosozlik faqat
    birinchi kunlik hisobot bo'sh chiqqanda ko'rinardi.

    ⚠ SO'ROV `LEFT JOIN` BILAN: «mos kelmagan hisob bormi?» degan savol
      to'g'ridan-to'g'ri beriladi va javob BO'SH RO'YXAT bo'lishi shart.
    =========================================================================
    """
    day = scenario.day
    await _materialise_and_close(app_sessionmaker, day)

    charged = _charges(sync_owner_conn, env.market_id, day)
    assert charged, "nazorat: birorta hisob yozilmagan — darvoza BO'SH to'plamda yugurardi"

    orphans = sync_owner_conn.execute(
        "SELECT c.stall_id, c.service_date FROM daily_charges AS c "
        "WHERE c.market_id = %s AND c.service_date = %s AND NOT EXISTS ("
        "  SELECT 1 FROM stall_slot_occupancy AS sso "
        "   WHERE sso.market_id = c.market_id AND sso.stall_id = c.stall_id "
        "     AND sso.business_date = c.service_date)",
        (str(env.market_id), day),
    ).fetchall()

    assert orphans == [], (
        f"⛔ G-2: {len(orphans)} ta hisobning kuniga MOS keladigan slot qatori yo'q "
        f"({orphans}) — `service_date` bandlik kuni bilan semantik AJRALIB KETGAN "
        "(Pitfall 1)"
    )


ALLOWED_BILLING_TYPES = frozenset(
    {
        "uuid",
        "bigint",
        "date",
        "text",
        "timestamp with time zone",
        "time without time zone",
    }
)
"""⛔ G-3 — OLTALA YANGI JADVAL USTUNLARINING RUXSAT ETILGAN TIPLARI.

⛔ SOLISHTIRUV `==` BILAN, `not in` BILAN EMAS (D-31): inkor tasdiq faqat
   SANAB O'TILGAN tipni ushlaydi va o'nlik-kasr yoki suzuvchi tiplardan
   bittasi ro'yxatga qo'shilmagan bo'lsa u JIMGINA o'tib ketardi.
   To'plam tengligi esa har QANDAY yangi tipni ushlaydi.

⚠ RO'YXAT ⛔ **O'LCHANGAN**, taxmin qilinmagan (06-14 da, `0020` ustida):

    time without time zone -> `charge_evidence.slot_time` (kun sloti;
                              `snapshots.slot_time` bilan AYNI tip)
    boolean                -> ⛔ oltala jadvalda BIRORTA ustun YO'Q

`boolean` ni «har ehtimolga qarshi» ro'yxatda qoldirish to'plam
tengligini ⛔ **yolg'on** qilardi: yangi mantiqiy bayroq (masalan
`daily_charges.is_disputed`) darvozadan JIMGINA o'tib ketardi, holbuki
u aynan ko'rib chiqilishi kerak bo'lgan o'zgarish.
"""

BILLING_TABLES = (
    "daily_charges",
    "charge_evidence",
    "charge_adjustments",
    "payments",
    "billing_anomalies",
    "cashier_shifts",
)
"""6-faza tug'dirgan oltala jadval (`0020`)."""


def test_g3_billing_columns_use_only_allowed_types(
    sync_owner_conn: Connection[TupleRow],
) -> None:
    """G-3: oltala billing jadvalining tiplari YOPIQ to'plamdan.

    Pul `bigint` so'm bo'lib qoladi: o'nlik-kasr yoki suzuvchi tip kunlik
    patta agregatlarida drift beradi va aynan o'sha drift sotuvchi bilan
    nizoga aylanadi — SBOZOR mavjud bo'lish sababining O'ZI (D-02, D-11).
    """
    found: dict[str, set[str]] = {}
    for table in BILLING_TABLES:
        rows = sync_owner_conn.execute(
            "SELECT DISTINCT data_type FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = %s",
            (table,),
        ).fetchall()
        types = {str(row[0]) for row in rows}
        assert types, f"nazorat: `{table}` jadvali bazada topilmadi — darvoza bo'sh yugurardi"
        found[table] = types

    union: set[str] = set()
    for types in found.values():
        union |= types

    assert union == ALLOWED_BILLING_TYPES, (
        "⛔ G-3: billing jadvallarining tiplar to'plami kutilgandan FARQ QILADI.\n"
        f"  ortiqcha: {sorted(union - ALLOWED_BILLING_TYPES)}\n"
        f"  yetishmayapti: {sorted(ALLOWED_BILLING_TYPES - union)}\n"
        f"  jadval kesimida: { {name: sorted(value) for name, value in found.items()} }"
    )


async def test_g6_human_confirmation_must_be_on_the_occupied_slot(
    sync_owner_conn: Connection[TupleRow],
    app_sessionmaker: async_sessionmaker[AsyncSession],
    scenario: Scenario,
    env: Env,
) -> None:
    """G-6: D-04 predikati `human_confirmed` DAN AJRALADI — uch holat.

    =========================================================================
    UCH HOLAT VA UCHALASI HAM BITTA TESTDA (C-6):

      (1) 2 slotda AI «band»                       -> HISOB
      (2) 1 slotda AI «band» + BOSHQA slotda
          nazoratchi «bo'sh» dedi                  -> ⛔ HISOB YO'Q
      (3) 1 slotda «band» + nazoratchi «band» dedi -> HISOB

    ⛔ (2) — BUTUN DARVOZANING MA'NOSI. Predikat «rastada nazoratchi
       javobi BORMI?» degan ZAIFROQ shaklga almashtirilganda (aynan
       `_PER_STALL_CTE.human_confirmed` ni ishlatish) (1) va (3) yashil
       qolardi, (2) esa QIZARISHI SHART: nazoratchi «bo'sh» degan slot
       hisobni OQLAMAYDI.

    ⛔ UCHALASI ALOHIDA TESTGA AJRATILMAYDI: ajratilganda (2) o'chirilib
       ketsa qolgan ikkitasi yashil qolardi va darvoza o'z ma'nosini
       yo'qotardi.
    =========================================================================
    """
    day = scenario.day
    await _materialise_and_close(app_sessionmaker, day)
    charged = set(_charges(sync_owner_conn, env.market_id, day))

    assert scenario.two_ai_slots in charged, "(1) 2 slotda AI «band» -> hisob YOZILMADI"
    assert scenario.human_slot in charged, (
        "(3) nazoratchi «band» degan rastaga hisob YOZILMADI — BILL-01 ning ikkinchi "
        "sharti («1 snapshot + nazoratchi tasdig'i») ishlamayapti"
    )
    assert scenario.human_says_empty not in charged, (
        "⛔ (2) G-6: nazoratchi BOSHQA slotda «bo'sh» degan rastaga hisob yozildi — "
        "predikat «nazoratchi javob berganmi?» degan ZAIFROQ shaklga siljigan (C-6)"
    )
    assert scenario.one_ai_slot not in charged, (
        "nazorat: bitta AI slotli rastaga hisob yozildi — D-04 chegarasi tushib ketgan"
    )


def test_the_module_measures_a_market_that_the_seed_actually_owns(
    sync_owner_conn: Connection[TupleRow], env: Env
) -> None:
    """NAZORAT — seed HAQIQATAN yozilgan va mezonlar bo'sh bazada yugurmayapti.

    ⛔ USIZ BUTUN FAYL «BO'SH TO'PLAM USTIDA YASHIL» BO'LARDI: har
       `assert` ning kirish holati seeddan keladi va seed jimgina
       yiqilganda mezonlar «hech nima yo'q, demak hammasi joyida»
       deganday ko'rinardi.
    """
    stalls = _rows(
        sync_owner_conn,
        "SELECT count(*) FROM stalls WHERE market_id = %s AND status = 'active'",
        (str(env.market_id),),
    )
    assert stalls > 0, "A bozorida faol rasta yo'q — seed yozilmagan"

    tariffs = _rows(
        sync_owner_conn,
        "SELECT count(*) FROM tariffs WHERE market_id = %s",
        (str(env.market_id),),
    )
    assert tariffs >= 2, (
        f"A bozorida {tariffs} ta tarif qatori bor — seedning IKKI qatorli zanjiri "
        "(D-09) yo'qolgan va «qaysi tarifdan?» savoli o'lchanmay qolardi"
    )

    other = _rows(
        sync_owner_conn,
        "SELECT count(*) FROM tariffs WHERE market_id = %s",
        (str(env.other_market_id),),
    )
    assert other >= 1, (
        "B bozorida birorta tarif yo'q — «A ni ko'raman, B ni ko'rmayman» da'vosi "
        "BO'SH bozor ustida jimgina rost bo'lardi"
    )

    # ⚠ MARSHRUTLAR `app.openapi()` DAN, `app.routes` DAN EMAS: v1 yuzasi
    #   ALOHIDA ilova sifatida `mount` qilingan, ya'ni ildiz ilovaning
    #   `routes` ro'yxatida faqat `/healthz`, `/docs` va qo'shnilari
    #   ko'rinadi — nazorat BO'SH to'plamda yugurgan bo'lardi (06-14 da
    #   o'lchandi).
    routes = set(fastapi_app.openapi()["paths"])
    assert len(routes) >= 40, (
        f"OpenAPI sxemasida faqat {len(routes)} ta marshrut bor — skaner marshrut "
        "grafining boshqa shaklini ko'ryapti"
    )
    for path in (PENDING_URL, PAYMENTS_URL, SHIFTS_URL):
        assert path in routes, (
            f"{path} marshrut grafida yo'q — mezonlar MAVJUD BO'LMAGAN yuzani o'lchayotgan bo'lardi"
        )
