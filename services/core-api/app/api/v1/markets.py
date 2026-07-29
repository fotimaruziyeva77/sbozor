"""Bozorlar ro'yxati (D-06).

=============================================================================
BU YERDA RLS'NI CHETLAB O'TISH YO'LI YO'Q — VA BO'LMAYDI.

Ikki yo'l bor va ikkalasi ham AYNAN BIR XIL `sbozor_app` ulanishi bilan
ishlaydi (ilova boshqa ulanishni umuman bilmaydi):

| Kim                  | Manba                      | Nima cheklaydi          |
| -------------------- | -------------------------- | ----------------------- |
| `MARKET_VIEW_ALL`    | `auth_list_markets_full()` | funksiyaning O'ZI: u    |
| (platforma admini)   | `SECURITY DEFINER`         | faqat bozor KONFIG'ini  |
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
from app.security.rbac import Permission

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

    `MARKET_VIEW_ALL` huquqi bo'lsa barcha bozorlar, aks holda faqat
    tanlangan bozor. Tekshiruv HUQUQ bo'yicha, `is_platform_admin`
    bayrog'i bo'yicha EMAS: matritsa (D-07) yagona haqiqat manbai bo'lib
    qolishi kerak, aks holda bir kun matritsa o'zgaradi-yu, bu yerdagi
    shart eskirib qoladi.

    Bozor tanlanmagan sessiya `TenantSessionDep` da 409 oladi. Bu ataylab:
    bozor tanlash ekranining manbai `POST /auth/login` javobidagi
    `markets` ro'yxati (01-06), bu endpoint esa boshqaruv panelining
    ichki ro'yxati.
    """
    statement = (
        _ALL_MARKETS if Permission.MARKET_VIEW_ALL in principal.permissions else _CURRENT_MARKET
    )
    result = await session.execute(statement)
    return [
        MarketListItem(id=row[0], name=row[1], timezone=row[2], is_active=row[3]) for row in result
    ]
