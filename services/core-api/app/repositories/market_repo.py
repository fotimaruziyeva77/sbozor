"""Bozor hayot sikli — `markets` ga yozishning YAGONA ilova yo'li (MARKET-01).

=============================================================================
BU SINF `TenantScopedRepository` DAN MEROS OLMAYDI — VA OLA OLMAYDI HAM.

`TenantScopedRepository` konstruktorda `market_id` talab qiladi va har
so'rovga `market_id = :market_id` predikatini qo'shadi. Bozor YARATISH
yo'lida esa o'sha qiymat hali MAVJUD EMAS: `POST /markets` chaqirilganda
`app.market_id` bo'sh va yangi bozorning identifikatori aynan shu
chaqiruv NATIJASIDA tug'iladi. Ya'ni meros olish uchun avval yaratiladigan
narsaning identifikatorini bilish kerak bo'lardi.

Ikkinchi sabab strukturaviy: `markets` da `market_id` USTUNI YO'Q — tenant
kaliti `id` ning O'ZI (`migrations/entities/policies.py::MARKETS_PREDICATE`).
`scoped()` esa aynan `market_id` ustuniga tayanadi.
=============================================================================

`markets` GA YOZISHNING TO'RTTA YO'LI BOR VA HAMMASI `SECURITY DEFINER`:

| Funksiya               | Nima qiladi                      | Qaysi endpoint        |
| ---------------------- | -------------------------------- | --------------------- |
| `market_create()`      | qoralama bozor + PROFIL qatori   | `POST /markets`       |
| `market_activate()`    | `is_active = true`               | `POST /{id}/activate` |
| `market_rename()`      | nom                              | (hali yo'q — pastda)  |
| `market_delete_draft()`| qoralamani BUTUNLAY o'chiradi    | `DELETE /{id}`        |

Sabab `migrations/entities/functions.py` da: `sbozor_app` roliga `markets`
da faqat `SELECT` grant'i berilgan va policy `id = app.market_id` bo'lgani
uchun `INSERT` ikki mustaqil to'siqqa uriladi (GRANT yo'q; yangi bozorning
`id` si hali GUC'ga teng emas). Ya'ni bu yerda ORM `insert(Market)` yozish
mumkin emas — u xato bilan yiqiladi, "ishlab ketib" tenant chegarasini
buzmaydi.

⚠ `market_create()` PROFIL QATORINI HAM O'ZI YOZADI va bu QARORNING
sababi shu yerda takrorlanadi (PATTERNS §3.6 dagi ochiq savolning javobi):
`market_profile` — tenant jadvali, ya'ni unga yozish uchun `app.market_id`
kerak, u esa `POST /markets` chaqiruvida hali yo'q. Profil keyinroq
(`select-market` dan keyin) alohida chaqiruvda yozilsa, ikkalasi orasida
PROFILSIZ BOZOR oynasi ochilardi — va aynan o'sha oynada `market_is_open()`
fail-closed `false` beradi, ya'ni bozor xato bermasdan HECH QACHON
ishlamaydigan holatga tushardi. Bitta DB funksiyasi ikkala qatorni bitta
tranzaksiyada yozadi va endpoint ikkinchi chaqiruv qilmaydi.

TIPLANGAN BIND PARAMETRLARI MAJBURIY, STIL EMAS (`audit_repo._PLATFORM_AUDIT`
bilan bir xil sabab): usta rekvizit maydonlarining ko'pchiligini bo'sh
qoldiradi, ya'ni `NULL` uzatiladi. `text()` da SQLAlchemy tipni ustundan
chiqara olmaydi va tipsiz `NULL` asyncpg'ga noma'lum tip bilan ketardi.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import Date, SmallInteger, Text, bindparam, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import UUID as PgUuid

if TYPE_CHECKING:
    from datetime import date
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

__all__ = [
    "MarketRepository",
    "MarketRow",
    "SetupStatusRow",
]


@dataclass(frozen=True)
class MarketRow:
    """Bozor konfiguratsiyasining bitta qatori.

    `is_active` — QORALAMA/JONLI farqi (D-16). U javob shakllarida hech
    qachon literal `True` bilan to'ldirilmaydi: manba har doim DB
    (02-03 da o'rnatilgan qoida).
    """

    id: UUID
    name: str
    timezone: str
    is_active: bool


@dataclass(frozen=True)
class SetupStatusRow:
    """Ustaning to'liqlik sanoqlari — BITTA so'rovning natijasi.

    ⛔⛔ `cameras` ENDI BU YERDA VA U HAQIQIY SANOQ (260820).

    Ilgari bu maydon yo'q edi va router `cameras=0` deb qotirib
    qo'yardi; izohda «kamera jadvali 3–5 fazalarda tug'iladi, ya'ni
    sanaladigan narsaning O'ZI mavjud emas» deyilgan edi. U izoh
    ESKIRGAN — jadval bor va Karmana test bozorida 6 ta kamera onlayn.

    Oqibati ekranda ko'rindi: admin paneli «Kamera ulanmagan · 0» deb
    QIZIL ogohlantirish chizardi, kameralar esa ishlab turardi. Bu
    mahsulotning o'z qoidasini buzardi — «o'lchanmagan qiymat o'rniga
    nol yozilmaydi» (T-05-04).

    ⚠ Arxivlanganlar sanalmaydi: arxivlangan kamera bandlikni
      o'lchamaydi.

    `categories_total` ham yo'q: u `categories` ning O'ZI. Bitta sonni
    ikki nom bilan o'qish ikkinchi haqiqat manbaini tug'dirardi —
    javobda ikkala maydon ham bo'lishi (UI "6 toifadan 6 tasi" deb
    ko'rsatadi) shakl talabi, sanoq talabi emas.
    """

    cameras: int
    zones: int
    categories: int
    stalls: int
    vendors: int
    tariffs_covered: int
    stalls_with_category: int
    calendar_configured: bool


_ALL_MARKETS = text(
    "SELECT market_id, market_name, market_timezone, is_active FROM auth_list_markets_full()"
)
"""HAQIQIY platforma admini uchun barcha bozorlar (D-06).

`SECURITY DEFINER` funksiya faqat bozor KONFIGURATSIYASINI ochadi — tenant
ma'lumotini emas. Sabab va uning chegarasi `app/api/v1/markets.py` modul
docstringida.
"""

_CURRENT_MARKET = text("SELECT id, name, timezone, is_active FROM markets")
"""ATAYIN FILTRSIZ.

`markets` policy'si `id = NULLIF(current_setting('app.market_id', true), '')
::uuid`, ya'ni bu so'rov AYNAN BITTA qator qaytaradi. Filtr yozilganda
noto'g'ri o'rnatilgan tenant konteksti ko'rinmay qolardi; filtrsiz shaklda
u 0 qator bo'lib DARHOL ko'rinadi (01-06 dagi `/auth/me` bilan bir xil
qoida).
"""

_CREATE_MARKET = text(
    "SELECT market_create(:name, :timezone, :operating_since, :open_weekdays, "
    ":address, :tin, :bank_account, :bank_mfo, :contact_phone)"
).bindparams(
    bindparam("name", type_=Text()),
    bindparam("timezone", type_=Text()),
    bindparam("operating_since", type_=Date()),
    bindparam("open_weekdays", type_=ARRAY(SmallInteger)),
    bindparam("address", type_=Text()),
    bindparam("tin", type_=Text()),
    bindparam("bank_account", type_=Text()),
    bindparam("bank_mfo", type_=Text()),
    bindparam("contact_phone", type_=Text()),
)
"""Qoralama bozor + profil qatori — BITTA tranzaksiyada (modul docstringi).

`is_active` uchun parametr YO'Q: funksiya uni LITERAL `false` qiladi.
Parametr bo'lganda chaqiruvchi uni bir kun `true` bilan berib
faollashtirishning butun to'liqlik tekshiruvini chetlab o'tardi.
"""

_ACTIVATE_MARKET = text("SELECT market_activate(:market_id)").bindparams(
    bindparam("market_id", type_=PgUuid(as_uuid=True))
)

_RENAME_MARKET = text("SELECT market_rename(:market_id, :name)").bindparams(
    bindparam("market_id", type_=PgUuid(as_uuid=True)),
    bindparam("name", type_=Text()),
)

_DELETE_DRAFT = text("SELECT market_delete_draft(:market_id)").bindparams(
    bindparam("market_id", type_=PgUuid(as_uuid=True))
)

_SETUP_STATUS = text(
    """
    WITH profile AS (
        SELECT p.operating_since, p.open_weekdays
          FROM market_profile p
         WHERE p.market_id = :market_id
    )
    SELECT
        (SELECT count(*) FROM zones z
          WHERE z.market_id = :market_id)                        AS zones,
        (SELECT count(*) FROM stall_categories c
          WHERE c.market_id = :market_id)                        AS categories,
        (SELECT count(*) FROM stalls s
          WHERE s.market_id = :market_id)                        AS stalls,
        (SELECT count(*) FROM vendors v
          WHERE v.market_id = :market_id)                        AS vendors,
        /*
         * ⛔⛔ KAMERA SANOG'I — QOTIRILGAN NOL O'RNIGA (260820).
         *
         *     Router qatlamida `cameras=0` yozilgan edi va uning izohi
         *     «kamera jadvali 3–5 fazalarda tug'iladi, sanaladigan
         *     narsaning O'ZI yo'q» derdi. U izoh ESKIRGAN: jadval
         *     allaqachon bor va Karmana test bozorida 6 ta kamera
         *     ONLAYN turibdi.
         *
         *     Oqibati ekranda ko'rindi: admin paneli «Kamera ulanmagan
         *     · 0» deb qizil ogohlantirish chizardi, holbuki kameralar
         *     ishlayotgan edi. Bu mahsulotning o'z qoidasini buzardi —
         *     «o'lchanmagan qiymat o'rniga nol yozilmaydi».
         *
         * ⛔ ARXIVLANGANLAR SANALMAYDI: arxivlangan kamera bandlikni
         *    o'lchamaydi, ya'ni «ulangan kamera» sanog'iga kirmasligi
         *    kerak.
         */
        (SELECT count(*) FROM cameras cam
          WHERE cam.market_id = :market_id
            AND NOT cam.is_archived)                              AS cameras,
        (SELECT count(*) FROM stall_categories c
          WHERE c.market_id = :market_id
            AND EXISTS (
                SELECT 1 FROM tariffs t
                 WHERE t.market_id = c.market_id
                   AND t.category_id = c.id
                   AND t.valid_from <= (SELECT operating_since FROM profile)
            ))                                                   AS tariffs_covered,
        (SELECT count(*) FROM stalls s
          WHERE s.market_id = :market_id
            AND EXISTS (
                SELECT 1 FROM stall_category_periods cp
                 WHERE cp.market_id = s.market_id
                   AND cp.stall_id = s.id
                   AND cp.valid_from <= (SELECT operating_since FROM profile)
            ))                                                   AS stalls_with_category,
        COALESCE(
            (SELECT array_length(open_weekdays, 1) FROM profile), 0
        ) > 0                                                    AS calendar_configured
    """
).bindparams(bindparam("market_id", type_=PgUuid(as_uuid=True)))
"""Ustaning BARCHA sanoqlari — bitta so'rov, oltita skalyar subquery.

=============================================================================
PROFIL QATORI YO'Q BO'LSA SO'ROV YIQILMAYDI — U FAIL-CLOSED JAVOB BERADI.

`profile` CTE'si 0 qator bergan holatda `(SELECT operating_since FROM
profile)` `NULL` bo'ladi, `t.valid_from <= NULL` esa `NULL` — ya'ni
`EXISTS` `false` va ikkala qamrov sanog'i ham `0` chiqadi;
`array_length(...)` ham `NULL` bo'lib `calendar_configured` `false` bo'ladi.

Bu `MarketProfileMissingError` (409 `market_incomplete`) dan ATAYIN
farqli va farq mahsulot qarori: `setup-status` ning butun vazifasi —
"nima yetishmayapti" savoliga RO'YXAT bilan javob berish (UI-SPEC §6.6:
"409 xato emas, yo'l ko'rsatkichi"). Profilsiz bozor uchun 409 qaytarish
foydalanuvchini AYNAN o'sha yo'l ko'rsatkichisiz qoldirardi. Fail-closed
javob esa `calendar_missing` bandini beradi va faollashtirishni baribir
to'sadi — ya'ni qamrov torayemaydi, tushuntirish qo'shiladi.

`market_create()` orqali tug'ilgan bozorda bu holat UCHRAMAYDI (profil
o'sha tranzaksiyada yoziladi). U faqat `markets` ga xom `INSERT` bilan
yozilgan qatorlarda (migratsiya, seed, `fixtures/auth_api.draft_market()`)
yuzaga keladi.
=============================================================================

`vendors` va `cameras` sanoqlari faollashtirishni HECH QACHON to'smaydi
(D-11 va D-16) — lekin `vendors` baribir SANALADI: yakuniy panel (UI-SPEC
§6.6) "bozor nimadan iborat" ro'yxatini ko'rsatadi va sotuvchilar soni
o'sha ro'yxatning bandi.

TENANT FILTRI IKKI QATLAM: RLS policy'si himoya to'ri, `:market_id`
predikati esa aniq, ko'rinadigan shart (`stall_repo.py` naqshi).
"""


class MarketRepository:
    """`markets` va uning to'liqlik holati.

    IKKI XIL SESSIYA BILAN ISHLAYDI va bu ataylab:

      * `create_market()` — `AuthSessionDep` (tenant konteksti YO'Q, chunki
        yaratilayotgan bozorning identifikatori hali mavjud emas);
      * qolgan hammasi — `TenantSessionDep` (RLS ostidagi o'qish va
        tanlangan bozor ustidagi amallar).

    Sinf sessiya turini o'zi TEKSHIRMAYDI: `SECURITY DEFINER` funksiyalar
    GUC'ga umuman qaramaydi, RLS'ga tayanadigan ikkita o'qish
    (`current_market`, `list_visible`) esa kontekstsiz sessiyada 0 qator
    beradi — ya'ni noto'g'ri ishlatish jimgina emas, DARHOL ko'rinadi.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_visible(self, *, is_platform_admin: bool) -> list[MarketRow]:
        """Ko'rinadigan bozorlar (D-06).

        Tarmoq manbai — `is_platform_admin` BAYROG'I, `MARKET_VIEW_ALL`
        huquqi EMAS (CR-03). To'liq sabab `app/api/v1/markets.py` modul
        docstringida; bu yerda faqat so'rov tanlanadi.
        """
        statement = _ALL_MARKETS if is_platform_admin else _CURRENT_MARKET
        result = await self.session.execute(statement)
        return [
            MarketRow(id=row[0], name=row[1], timezone=row[2], is_active=row[3]) for row in result
        ]

    async def current_market(self) -> MarketRow | None:
        """TANLANGAN bozor — RLS predikati bo'yicha (so'rov filtrsiz).

        `None` — tenant konteksti o'rnatilmagan yoki bozor o'chirilgan.
        Chaqiruvchi buni 404 ga aylantiradi: bozor tanlangan bo'lsa ham
        qator topilmasligi "sizniki emas" degani, "server xatosi" emas.
        """
        result = await self.session.execute(_CURRENT_MARKET)
        row = result.one_or_none()
        return (
            None
            if row is None
            else MarketRow(id=row[0], name=row[1], timezone=row[2], is_active=row[3])
        )

    async def create_market(
        self,
        *,
        name: str,
        timezone: str,
        operating_since: date,
        open_weekdays: list[int] | None,
        address: str | None,
        tin: str | None,
        bank_account: str | None,
        bank_mfo: str | None,
        contact_phone: str | None,
    ) -> UUID:
        """QORALAMA bozor + uning profilini yaratadi va `id` ni qaytaradi.

        `is_active` argumenti YO'Q (modul docstringi): yangi bozor HAR
        DOIM qoralama va faollashtirish alohida darvoza ostida.
        """
        result = await self.session.execute(
            _CREATE_MARKET,
            {
                "name": name,
                "timezone": timezone,
                "operating_since": operating_since,
                "open_weekdays": open_weekdays,
                "address": address,
                "tin": tin,
                "bank_account": bank_account,
                "bank_mfo": bank_mfo,
                "contact_phone": contact_phone,
            },
        )
        market_id: UUID = result.scalar_one()
        return market_id

    async def activate_market(self, market_id: UUID) -> None:
        """Qoralamani jonli holatga o'tkazadi (usta oxirgi qadami).

        TO'LIQLIK TEKSHIRUVI BU YERDA EMAS va DB funksiyasida ham yo'q —
        u chaqiruvchida (`app/api/v1/markets.py::_blocking`), chunki javob
        "yo'q" emas, YETISHMAYOTGAN QADAMLAR RO'YXATI bo'lishi kerak
        (UI-SPEC §6.6). Repozitoriy metodi qaror qabul qilmaydi.
        """
        await self.session.execute(_ACTIVATE_MARKET, {"market_id": market_id})

    async def rename_market(self, market_id: UUID, name: str) -> None:
        """Bozor nomini o'zgartiradi.

        ⚠ HTTP ISTE'MOLCHISI HALI YO'Q. Metod baribir shu yerda, chunki u
        `markets` ga yozishning to'rtta yo'lidan biri va uchalasi bir
        joyda turgani uchun `GRANT` reyestri (`MARKET_CORE_GRANT_
        SIGNATURES`) bilan bir ko'rinishda solishtiriladi. Usta 1-qadamiga
        qaytib rekvizitlarni tahrirlash ekrani 02-16 da quriladi va o'sha
        reja `PATCH /markets/{id}` ni shu metod ustiga qo'yadi.

        Alohida funksiya bo'lishining sababi `migrations/entities/
        functions.py::MARKET_RENAME` da: nom o'zgartirish va faollashtirish
        bitta `market_update()` ostida birlashtirilganda ular bitta
        `GRANT` bilan kelardi.
        """
        await self.session.execute(_RENAME_MARKET, {"market_id": market_id, "name": name})

    async def delete_draft(self, market_id: UUID) -> bool:
        """Tashlab ketilgan QORALAMANI butunlay o'chiradi; `False` = o'chirilmadi.

        `False` ikki holatda qaytadi va ular ATAYIN ajratilmagan
        (`market_delete_draft()` ning `IS DISTINCT FROM false` shakli):
        bozor JONLI yoki bozor UMUMAN YO'Q. Chaqiruvchi ikkalasini ham
        409 `market_is_active` ga aylantiradi — "yo'q" holati esa unga
        yetib bormaydi, chunki yo'l parametri allaqachon tanlangan bozor
        bilan solishtirilgan (404).

        JONLI BOZORNI O'CHIRISH YO'LI ILOVA QATLAMIDA HAM, DB'DA HAM
        YARATILMAGAN: qaror funksiyaning O'ZIDA, ya'ni xom SQL yo'li ham
        shu qoidaga bo'ysunadi.
        """
        result = await self.session.execute(_DELETE_DRAFT, {"market_id": market_id})
        return bool(result.scalar_one())

    async def setup_status(self, market_id: UUID) -> SetupStatusRow:
        """Ustaning to'liqlik sanoqlari — HISOBLANADI, SAQLANMAYDI.

        Hech qanday `wizard_session` jadvali yo'q va bo'lmaydi (RESEARCH
        Pattern 5): qadam holati domen ma'lumotining O'ZIDAN o'qiladi,
        ya'ni sahifa yangilash, boshqa qurilmadan davom ettirish va
        parallel tahrirlash hech qanday sinxronlash talab qilmaydi.
        """
        result = await self.session.execute(_SETUP_STATUS, {"market_id": market_id})
        row = result.one()
        return SetupStatusRow(
            zones=row.zones,
            categories=row.categories,
            stalls=row.stalls,
            vendors=row.vendors,
            tariffs_covered=row.tariffs_covered,
            stalls_with_category=row.stalls_with_category,
            calendar_configured=bool(row.calendar_configured),
            cameras=row.cameras,
        )
