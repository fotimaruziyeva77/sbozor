"""Bozorlar ro'yxati (D-06).

=============================================================================
BU YERDA RLS'NI CHETLAB O'TISH YO'LI YO'Q — VA BO'LMAYDI.

Ikki yo'l bor va ikkalasi ham AYNAN BIR XIL `sbozor_app` ulanishi bilan
ishlaydi (ilova boshqa ulanishni umuman bilmaydi):

| Kim                  | Manba                      | Nima cheklaydi          |
| -------------------- | -------------------------- | ----------------------- |
| `is_platform_admin`  | `auth_list_markets_full()` | funksiyaning O'ZI: u    |
| (BAYROQ, rol emas)   | `SECURITY DEFINER`         | faqat bozor KONFIG'ini  |
|                      |                            | ochadi, tenant ma'lumot |
|                      |                            | ini emas                |
| qolganlar            | `SELECT ... FROM markets`  | `markets` policy'si:    |
|                      | (RLS ostida)               | `id = app.market_id`    |

Qator himoyasini chetlab o'tish atributiga ega rol klasterda UMUMAN
YARATILMAGAN va `tests/tenancy/test_meta.py` dagi rol invariantlari
darvozasi buni butun klaster bo'yicha qulflaydi. Ya'ni platforma
adminining "hamma bozorni ko'rish" huquqi bozor KONFIGURATSIYASI bilan
cheklangan: bozor tanlangandan keyin u ham oddiy tenant policy'siga
bo'ysunadi (bu 01-06 da `/auth/me` orqali uchdan-uchiga isbotlangan).
=============================================================================

BRANCH MANBAI — `is_platform_admin` BAYROG'I, `MARKET_VIEW_ALL` HUQUQI EMAS
(CR-03 tuzatishi; ilgari teskarisi yozilgan edi).

Sabab: huquq ROLDAN hisoblanadi (`permissions_for()`), rol esa a'zolik
qatoridan ham kelishi mumkin. Ya'ni `user_market_roles.roles` ga
`'platform_admin'` yozilgan har qanday hisob — bayroqsiz bo'lsa ham —
`MARKET_VIEW_ALL` ni olardi va bu yerdan platformadagi BARCHA bozorlar
ro'yxatini ko'rardi. Bayroq esa `users` jadvalidagi yagona autoritativ
manba: uni faqat platforma darajasidagi tayinlash o'zgartiradi va u
hech qanday rol/a'zolik yo'li bilan qo'lga kiritilmaydi.

Ikkinchi qulf `users.py::_assert_roles_assignable` da: `platform_admin`
a'zolik roli sifatida umuman berilmaydi. Ikkalasi mustaqil — biri
"gibrid hisob yaratib bo'lmaydi", ikkinchisi "gibrid hisob baribir
ko'rmaydi" deydi.
=============================================================================

Bozor TANLASH endpointi bu yerda EMAS — u `POST /api/v1/auth/select-market`
(01-06): tanlash sessiya operatsiyasi (yangi access token + refresh cookie),
ro'yxat esa oddiy o'qish. Ularni bitta modulga qo'shish sessiya mantiqini
ikki joyga bo'lardi.
"""

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import text

from app.deps import PrincipalDep, TenantSessionDep
from app.schemas import MarketListItem

router = APIRouter(tags=["markets"])

_ALL_MARKETS = text(
    "SELECT market_id, market_name, market_timezone, is_active FROM auth_list_markets_full()"
)

_CURRENT_MARKET = text("SELECT id, name, timezone, is_active FROM markets")
"""ATAYIN FILTRSIZ.

`markets` policy'si `id = NULLIF(current_setting('app.market_id', true), '')
::uuid`, ya'ni bu so'rov AYNAN BITTA qator qaytaradi. Filtr yozilganda
noto'g'ri o'rnatilgan tenant konteksti ko'rinmay qolardi; filtrsiz shaklda
u 0 qator bo'lib DARHOL ko'rinadi (01-06 dagi `/auth/me` bilan bir xil
qoida).
"""


@router.get("", response_model=list[MarketListItem])
async def list_markets(
    principal: PrincipalDep,
    session: TenantSessionDep,
) -> list[MarketListItem]:
    """Ko'rinadigan bozorlar (D-06).

    HAQIQIY platforma admini (`users.is_platform_admin = true`) barcha
    bozorlarni ko'radi, qolganlar — faqat tanlangan bozorni. Tekshiruv
    BAYROQ bo'yicha, `MARKET_VIEW_ALL` huquqi bo'yicha EMAS (CR-03):
    huquq roldan hisoblanadi, rol esa a'zolik qatoridan ham kelishi
    mumkin, ya'ni u bozor darajasida "qo'lga kiritiladigan" qiymat.
    Bayroq esa bozor darajasidan yuqorida turadi va faqat platforma
    tayinlashi bilan o'zgaradi.

    Matritsa (D-07) hamon yagona haqiqat manbai — LEKIN "nima qila oladi"
    savoli uchun. "Qaysi TENANT chegarasida" savoliga u javob bermaydi va
    aynan shu chalkashlik CR-03 ni tug'digan edi.

    Bozor tanlanmagan sessiya `TenantSessionDep` da 409 oladi. Bu ataylab:
    bozor tanlash ekranining manbai `POST /auth/login` javobidagi
    `markets` ro'yxati (01-06), bu endpoint esa boshqaruv panelining
    ichki ro'yxati.
    """
    statement = _ALL_MARKETS if principal.is_platform_admin else _CURRENT_MARKET
    result = await session.execute(statement)
    return [
        MarketListItem(id=row[0], name=row[1], timezone=row[2], is_active=row[3]) for row in result
    ]
