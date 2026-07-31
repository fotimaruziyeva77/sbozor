"""Bozor hayot sikli — ro'yxat, yaratish va o'chirish (D-06, D-16, MARKET-01).

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

=============================================================================
BOZOR YARATISH `markets` GA `INSERT` QILMAYDI — U `market_create()` NI
CHAQIRADI, VA BU YAGONA MUMKIN BO'LGAN YO'L.

`sbozor_app` roliga `markets` da faqat `SELECT` berilgan; policy esa
`id = app.market_id`. Ya'ni ORM `insert(Market)` ikki mustaqil to'siqqa
uriladi va HECH QANDAY holatda ishlab ketmaydi. To'liq sabab va to'rtta
`SECURITY DEFINER` funksiyaning taqsimoti — `app/repositories/market_repo.py`
modul docstringida.

⚠ `market_create()` bozor bilan BIRGA `market_profile` qatorini ham
yozadi (PATTERNS §3.6 dagi ochiq savolning javobi). Sabab: profil tenant
jadvali va unga yozish `app.market_id` ni talab qiladi, u esa bu
chaqiruvda hali yo'q; profilsiz bozor esa xato bermasdan HECH QACHON
ishlamaydi (`market_is_open()` fail-closed). Endpoint ikkinchi chaqiruv
QILMAYDI va tranzaksiya chegarasi DB funksiyasining ichida qoladi.

`POST /markets` UCHUN TENANT SESSIYASI ISHLATILMAYDI (`audit.py::
list_platform_audit` bilan AYNAN bir xil sabab): bu chaqiruvda
`app.market_id` bo'sh va tenant sessiyasi 409 `market_not_selected`
qaytarardi — lekin admin aynan hali mavjud bo'lmagan bozorni yaratmoqda
va uni "avval biror bozorni tanlang" deb qaytarish ma'nosiz bo'lardi.

AUDIT MAJBURIY VA U APP QATLAMIDA: `markets` `AUDITED_TABLES` da YO'Q,
ya'ni `fn_audit_row()` triggeri unga o'rnatilmagan. `SECURITY DEFINER`
funksiya ichida ham trigger yo'q. Usiz bozor yaratish, faollashtirish va
o'chirish jurnalda UMUMAN ko'rinmasdi (T-02-83).
=============================================================================
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import JSONResponse
from sbozor_core.enums import AuditAction

from app.deps import (
    AuthSessionDep,
    Principal,
    PrincipalDep,
    TenantSessionDep,
    require_permission,
    require_platform_admin,
)
from app.repositories.market_repo import MarketRepository, SetupStatusRow
from app.schemas import (
    BlockingItem,
    MarketCreateRequest,
    MarketCreateResponse,
    MarketListItem,
    SetupStatusResponse,
)
from app.security.audit import TABLE_MARKETS, write_app_audit
from app.security.rbac import Permission

# `UUID` `if TYPE_CHECKING:` ostiga QO'YILMAYDI: FastAPI yo'l
# parametrlarining annotatsiyasini ISH PAYTIDA o'qiydi (`get_type_hints`),
# ya'ni import faqat tip tekshiruvida bo'lsa marshrut `NameError` bilan
# yiqilardi (`zones.py:44-47` dagi bilan bir xil sabab).

log = structlog.get_logger(__name__)

router = APIRouter(tags=["markets"])

MarketManagerDep = Annotated[Principal, Depends(require_permission(Permission.MARKET_MANAGE))]
MarketDataViewerDep = Annotated[Principal, Depends(require_permission(Permission.MARKET_DATA_VIEW))]
PlatformAdminDep = Annotated[Principal, Depends(require_platform_admin)]

_NOT_FOUND = "not_found"
_MARKET_IS_ACTIVE = "market_is_active"
_MARKET_INCOMPLETE = "market_incomplete"


def _market_id(principal: Principal) -> UUID:
    """Tanlangan bozor.

    `TenantSessionDep` allaqachon 409 qaytargan bo'lardi; bu tekshiruv
    mypy uchun emas, KELAJAK uchun: kimdir endpointni tenant sessiyasisiz
    qayta yozsa, `market_id=None` bilan amal bajarilib ketmasin
    (`zones.py:66-82` dagi bilan bir xil yordamchi).
    """
    if principal.market_id is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="market_not_selected",
        )
    return principal.market_id


def _own_market(market_id: UUID, principal: Principal) -> UUID:
    """Yo'ldagi bozor TANLANGAN bozor bilan bir xilmi; aks holda 404.

    =========================================================================
    QAYTARILADIGAN QIYMAT — `principal` DAN, YO'LDAN EMAS. BU ATAYIN.

    Bu funksiyaning natijasi `MarketRepository` ning `SECURITY DEFINER`
    chaqiruvlariga uzatiladi, ular esa RLS'ga UMUMAN bo'ysunmaydi. Yo'l
    parametrini uzatish darvoza yagona himoya bo'lib qolishini anglatardi:
    solishtirish bir kun olib tashlansa (yoki `!=` `==` ga aylansa)
    `market_activate()` BEGONA bozorni faollashtirib yuborardi va RLS uni
    to'sa olmasdi (T-02-82).

    `principal.market_id` ni uzatish esa darvozani IKKINCHI qatlamga
    aylantiradi: eng yomon holatda ham amal chaqiruvchining O'Z bozoriga
    tegadi. Bu "ortiqcha ehtiyot" emas — `SECURITY DEFINER` funksiya
    bilan ishlaganda ilova qatlami YAGONA tenant chegarasi.
    =========================================================================

    404, 403 EMAS (T-01-76): 403 javobining O'ZI "bunday bozor bor, lekin
    sizniki emas" degan ma'lumotni oshkor qilardi.
    """
    tenant = _market_id(principal)
    if market_id != tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_NOT_FOUND)
    return tenant


def _blocking(status_row: SetupStatusRow) -> list[BlockingItem]:
    """Faollashtirishni to'sib turgan sabablar — QADAM tartibida.

    =========================================================================
    TO'LIQLIK QOIDASI SHU YERDA VA FAQAT SHU YERDA YASHAYDI.

    Uni `GET /setup-status` ham, `POST /activate` ham AYNAN shu funksiyadan
    oladi. Ikki joyda yozilganda ular bir kun ajralib ketardi va natija eng
    yomon shaklda ko'rinardi: panel "hammasi tayyor" deb turib, tugma 409
    berardi (yoki aksincha — tugma ishlab, panel qizil qolardi).

    TARTIB — `step` BO'YICHA O'SISH. Frontend `blocking[0].step` ni
    "birinchi tugallanmagan qadam" deb ishlatadi (UI-SPEC §6.4 va 02-03
    dagi `firstIncompleteStep()`), ya'ni tartib javob SHARTNOMASINING bir
    qismi, ko'rinish qulayligi emas.

    `detail` FAQAT SONLARNI tashiydi (`"0"`, `"498/512"`). Server matn
    yozmaydi: UI uchta tilda ishlaydi va bu yerdan chiqqan har qanday
    jumla i18n chegarasidan tashqarida qolardi. Frontend `code` ni
    tarjimaga, `detail` ni esa o'sha tarjimaning sonli o'rniga qo'yadi.

    SOTUVCHILAR (`vendors`) VA KAMERALAR (`cameras`) BU YERDA UMUMAN
    UCHRAMAYDI — D-11 va D-16. Ular yakuniy panelda ko'rinadi, lekin
    hech qachon to'smaydi.
    =========================================================================
    """
    items: list[BlockingItem] = []

    if status_row.zones == 0:
        items.append(BlockingItem(step=2, code="zones_missing", detail="0"))
    if status_row.categories == 0:
        items.append(BlockingItem(step=3, code="categories_missing", detail="0"))
    if status_row.tariffs_covered < status_row.categories:
        items.append(
            BlockingItem(
                step=4,
                code="tariff_missing_for_category",
                detail=f"{status_row.tariffs_covered}/{status_row.categories}",
            )
        )
    if status_row.stalls == 0:
        items.append(BlockingItem(step=5, code="stalls_missing", detail="0"))
    if status_row.stalls_with_category < status_row.stalls:
        items.append(
            BlockingItem(
                step=5,
                code="stalls_without_category",
                detail=f"{status_row.stalls_with_category}/{status_row.stalls}",
            )
        )
    if not status_row.calendar_configured:
        items.append(BlockingItem(step=7, code="calendar_missing", detail="0"))

    return items


def _setup_status_response(status_row: SetupStatusRow) -> SetupStatusResponse:
    """Sanoqlar + hisoblangan `blocking[]` -> javob DTO'si.

    `cameras` HAR DOIM `0` va bu D-16 ning ILGAGI: maydon javobda
    BUGUNDAN bor, ya'ni 3–5 fazalar haqiqiy sanoqni qo'yganda frontend
    shakli o'zgarmaydi va yakuniy paneldagi neytral qator (UI-SPEC §6.7)
    o'z joyida qoladi. Kamera jadvali hali mavjud emas, shuning uchun
    sanoq DB so'rovida emas — u shu yerda, ko'rinadigan joyda.

    `can_activate` — SERVER qarori va u `blocking` ning bo'shligidan
    hisoblanadi. Klient uni sanoqlardan qayta hisoblamaydi (o'sha holatda
    to'liqlik qoidasi ikkinchi marta, boshqa tilda yozilgan bo'lardi).
    """
    blocking = _blocking(status_row)
    return SetupStatusResponse(
        zones=status_row.zones,
        categories=status_row.categories,
        tariffs_covered=status_row.tariffs_covered,
        categories_total=status_row.categories,
        stalls=status_row.stalls,
        stalls_with_category=status_row.stalls_with_category,
        vendors=status_row.vendors,
        calendar_configured=status_row.calendar_configured,
        cameras=0,
        can_activate=not blocking,
        blocking=blocking,
    )


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
    rows = await MarketRepository(session).list_visible(
        is_platform_admin=principal.is_platform_admin
    )
    return [
        MarketListItem(id=row.id, name=row.name, timezone=row.timezone, is_active=row.is_active)
        for row in rows
    ]


@router.post("", status_code=status.HTTP_201_CREATED, response_model=MarketCreateResponse)
async def create_market(
    payload: MarketCreateRequest,
    principal: PlatformAdminDep,
    _permitted: MarketManagerDep,
    session: AuthSessionDep,
) -> MarketCreateResponse:
    """QORALAMA bozor yaratadi — ustaning 1-qadami (MARKET-01, D-16).

    IKKI DARVOZA, IKKALASI HAM MAJBURIY (T-02-79):

      * `require_platform_admin` — `users.is_platform_admin` BAYROG'I;
      * `require_permission(MARKET_MANAGE)` — huquq matritsasi (D-07).

    Bugun ikkalasi bir xil to'plamni qamraydi (`MARKET_MANAGE` faqat
    `platform_admin` rolida), lekin ular MUSTAQIL: matritsa kengayib
    `MARKET_MANAGE` bozor adminiga berilsa ham bayroq darvozasi joyida
    qoladi. Bitta darvoza qoldirish "bozor ma'lumotini boshqarish" ni
    jimgina "yangi bozor ochish" ga aylantirardi.

    Javobda `is_active` HAR DOIM `false` — lekin u BARIBIR qaytariladi:
    klient uni taxmin qilmasligi va `MarketRef` bilan bir xil shaklda
    o'qishi kerak.
    """
    repo = MarketRepository(session)
    market_id = await repo.create_market(
        name=payload.name,
        timezone=payload.timezone,
        operating_since=payload.operating_since,
        open_weekdays=payload.open_weekdays,
        address=payload.address,
        tin=payload.tin,
        bank_account=payload.bank_account,
        bank_mfo=payload.bank_mfo,
        contact_phone=payload.contact_phone,
    )

    await write_app_audit(
        session,
        action=AuditAction.INSERT,
        table_name=TABLE_MARKETS,
        row_id=market_id,
        # =================================================================
        # `principal=` ATAYIN UZATILMAYDI — MAYDONLAR QO'LDA BERILADI.
        #
        # `write_app_audit` `principal` dan `market_id` ni ham oladi, ya'ni
        # A bozorini tanlab turgan platforma admini C bozorini yaratganda
        # yozuv A NING JURNALIGA tushardi — "A bozorida yangi bozor
        # yaratildi" degan YOLG'ON DALIL. Bozor yaratish hech qaysi
        # bozorga tegishli emas va `audit_log.market_id` ustuni uchun
        # `NULL` aynan shu holat uchun ochiq qoldirilgan
        # (`sbozor_core.models.ops.AuditLog` docstringi: "platforma
        # darajasidagi harakatlar (bozor yaratish, ...)").
        #
        # Yozuv ko'rinmay qolmaydi: `GET /api/v1/audit/platform` AYNAN
        # `market_id IS NULL` qatorlarini qaytaradi va uning darvozasi ham
        # `users.is_platform_admin` bayrog'i.
        # =================================================================
        actor_user_id=principal.user_id,
        actor_label=principal.actor_label,
        request_id=principal.request_id,
        # REKVIZITLAR AUDITGA TUSHMAYDI (T-02-84, ASVS V8): bank hisobi,
        # MFO va STIR — moliyaviy identifikatorlar va ular jurnalni
        # o'qiyotgan HAR KIMGA ochilardi. Maskalash (`***`) ham tanlanmadi:
        # maskalangan qiymat hech qanday savolga javob bermaydi, lekin
        # "bu yerda rekvizit bor" degan signalni qoldiradi. Jurnalning
        # vazifasi — "kim qachon qaysi bozorni yaratdi", rekvizitlarning
        # o'zi esa `market_profile` da va uning O'ZGARISHI DB-trigger
        # auditiga tushadi.
        new={
            "name": payload.name,
            "timezone": payload.timezone,
            "operating_since": payload.operating_since.isoformat(),
        },
    )
    await session.commit()

    log.info("market_created", market_id=str(market_id))
    return MarketCreateResponse(id=market_id, name=payload.name, is_active=False)


@router.get("/{market_id}/setup-status", response_model=SetupStatusResponse)
async def market_setup_status(
    market_id: UUID,
    principal: MarketDataViewerDep,
    session: TenantSessionDep,
) -> SetupStatusResponse:
    """Ustaning to'liqlik holati — HISOBLANADI, HECH QAYERDA SAQLANMAYDI.

    =========================================================================
    `wizard_session` JADVALI YO'Q VA BO'LMAYDI (RESEARCH Pattern 5).

    Qadam holati domen ma'lumotining O'ZIDAN o'qiladi: zona bor —
    2-qadam bajarilgan. Alohida holat jadvali `market_id` hali yo'q
    paytda RLS'siz global jadval talab qilardi va 1000 rastali import
    JSONB ichida yashab qolardi; klient-tomon store esa sahifa
    yangilanishida butun ishni yo'q qilardi.

    Buning bevosita natijasi: usta boshqa qurilmadan davom ettiriladi,
    sahifa yangilash xavfsiz va ikkita parallel oyna bir-birini buzmaydi
    — hech qanday sinxronlash kodisiz.
    =========================================================================

    Yo'ldagi `market_id` TANLANGAN bozor bilan solishtiriladi va mos
    kelmasa **404** (`_own_market`). RLS baribir bo'sh sanoqlar berardi,
    lekin "hammasi nol" javobi begona bozorni "bo'm-bo'sh qoralama" deb
    ko'rsatib, uning MAVJUDLIGINI tasdiqlagan bo'lardi — 02-10 dagi
    "bo'sh ro'yxat tenant teshigini yashiradi" holatining aynan o'zi.

    `MARKET_DATA_VIEW` yetarli (`MARKET_MANAGE` EMAS): direktor bozorning
    to'liqligini KO'RADI, lekin faollashtira olmaydi (D-07).
    """
    tenant_id = _own_market(market_id, principal)
    status_row = await MarketRepository(session).setup_status(tenant_id)
    return _setup_status_response(status_row)


@router.post("/{market_id}/activate", response_model=MarketCreateResponse)
async def activate_market(
    market_id: UUID,
    principal: MarketManagerDep,
    session: TenantSessionDep,
) -> MarketCreateResponse | JSONResponse:
    """Qoralamani JONLI holatga o'tkazadi — ustaning oxirgi qadami.

    =========================================================================
    409 — XATO EMAS, YO'L KO'RSATKICHI (UI-SPEC §6.6).

    Chala bozor uchun javob tanasi `{"detail": "market_incomplete",
    "blocking": [...]}` va `blocking` AYNAN `setup-status` dagi bilan bir
    xil shaklda. Sabab UI qarorida: yakuniy panel 409 ni ALOHIDA xato
    UI'si bilan emas, o'sha ro'yxatni ALMASHTIRISH bilan ko'rsatadi
    (bitta render yo'li, `role="status"`, toast yo'q). Ro'yxatsiz 409
    foydalanuvchini "nima yetishmayapti?" savoli bilan qoldirardi va u
    qadamlarni bittalab qidirib chiqishga majbur bo'lardi.

    Shuning uchun javob `HTTPException` bilan EMAS, `JSONResponse` bilan
    quriladi: `HTTPException` tanani `{"detail": ...}` ichiga o'raydi va
    `blocking` bir daraja pastga tushib ketardi.
    =========================================================================

    TO'LIQLIK TEKSHIRUVI SERVERDA (T-02-81) va `market_activate()` unga
    umuman qaramaydi — DB funksiyasi parametr qabul qilmaydi va faqat
    bayroqni ko'taradi. Ya'ni klientdagi tugmani DevTools bilan yoqib
    yuborish hech nima bermaydi.

    ALLAQACHON FAOL BOZOR -> 409 `market_is_active`, va bu tekshiruv
    to'liqlikdan OLDIN turadi: faollashtirilgandan keyin zonasi
    o'chirilgan bozor uchun javob "chala" emas, "allaqachon jonli"
    bo'lishi kerak.
    """
    tenant_id = _own_market(market_id, principal)
    repo = MarketRepository(session)

    # `old` qiymati TAXMIN QILINMAYDI — u yozuvdan OLDIN o'qiladi
    # (`users.py:368-397` qoidasi). Bu ayni paytda "allaqachon faol"
    # darvozasining ham manbai: ikkita alohida so'rov bo'lganda ular
    # orasida bayroq o'zgarishi mumkin edi.
    current = await repo.current_market()
    if current is None:  # pragma: no cover - RLS bir xil tranzaksiyada 1 qator beradi
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_NOT_FOUND)
    if current.is_active:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_MARKET_IS_ACTIVE)

    status_row = await repo.setup_status(tenant_id)
    blocking = _blocking(status_row)
    if blocking:
        log.info(
            "market_activation_blocked",
            market_id=str(tenant_id),
            codes=[item.code for item in blocking],
        )
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "detail": _MARKET_INCOMPLETE,
                "blocking": [item.model_dump() for item in blocking],
            },
        )

    await repo.activate_market(tenant_id)
    await write_app_audit(
        session,
        action=AuditAction.UPDATE,
        table_name=TABLE_MARKETS,
        row_id=tenant_id,
        principal=principal,
        old={"is_active": current.is_active},
        new={"is_active": True},
    )

    log.info("market_activated", market_id=str(tenant_id))
    return MarketCreateResponse(id=tenant_id, name=current.name, is_active=True)


@router.delete(
    "/{market_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def delete_market(
    market_id: UUID,
    principal: MarketManagerDep,
    session: TenantSessionDep,
) -> Response:
    """Tashlab ketilgan QORALAMANI o'chiradi (A10, Pitfall 7).

    NEGA BU ENDPOINT UMUMAN BOR: usta har `POST /markets` da haqiqiy
    qator tug'diradi, ya'ni yarim yo'lda tashlab ketilgan urinishlar
    bazada TO'PLANADI. Ular bozor tanlash ekranida ham ko'rinadi (02-03
    dan beri qoralama ATAYIN filtrlanmaydi), demak "tozalash yo'li yo'q"
    holati foydalanuvchi ko'radigan chalkashlikka aylanardi.

    JONLI BOZOR HECH QACHON O'CHMAYDI. Qaror `market_delete_draft()`
    ning O'ZIDA: u `is_active` ni tekshiradi va `false` qaytaradi, ya'ni
    xom SQL yo'li ham shu qoidaga bo'ysunadi. `market_deactivate()`
    funksiyasi ham ATAYIN yaratilmagan — aks holda "o'chirish uchun avval
    deaktivatsiya qiling" degan ikki qadamli yo'l ochilardi.

    ⚠ BOZOR TANLANGAN BO'LISHI SHART (`TenantSessionDep`): admin nimani
    o'chirayotganini KO'RIB turgan bo'lishi kerak va yo'ldagi
    identifikator tanlangan bozor bilan solishtiriladi (`_own_market`).
    """
    tenant_id = _own_market(market_id, principal)
    repo = MarketRepository(session)

    # `old` YOZUVDAN OLDIN o'qiladi (users.py:368-397 qoidasi): o'chirilgan
    # qatorni keyin o'qib bo'lmaydi va uni "taxmin qilib" yozish jurnalga
    # yolg'on dalil qo'yardi.
    current = await repo.current_market()
    if current is None:  # pragma: no cover - RLS bir xil tranzaksiyada 1 qator beradi
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_NOT_FOUND)

    if not await repo.delete_draft(tenant_id):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_MARKET_IS_ACTIVE)

    await write_app_audit(
        session,
        action=AuditAction.DELETE,
        table_name=TABLE_MARKETS,
        row_id=tenant_id,
        principal=principal,
        old={"name": current.name, "is_active": current.is_active},
    )
    # Yozuv o'chirilgan bozorning `market_id` si bilan qoladi va bu
    # KUTILGAN: `audit_log.market_id` da FOREIGN KEY ATAYIN yo'q, aynan
    # shuning uchun audit izi u tasvirlagan bozordan uzoq yashaydi
    # (`sbozor_core.models.ops.AuditLog` docstringi).
    log.info("draft_market_deleted", market_id=str(tenant_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
