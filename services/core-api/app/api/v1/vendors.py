"""Sotuvchilar reestri (MARKET-04) — 1-fazadagi `audit_read` mexanizmining BIRINCHI iste'molchisi.

=============================================================================
E'LON TARTIBI MAJBURIY VA U BEZAK EMAS:

    principal: VendorViewerDep        # 1) HUQUQ
    intent:    VendorReadIntentDep    # 2) O'QISH NIYATI
    session:   TenantSessionDep       # 3) MA'LUMOT

FastAPI dependency'larni AYNAN shu tartibda hal qiladi va birinchi
`HTTPException` qolganlarini umuman chaqirmaydi. Ya'ni 403 olgan so'rov
`audit_read` gacha YETIB KELMAYDI va jurnalga yozuv ham qurilmaydi.

Teskari tartibda (`intent` birinchi) jurnalda "kassir sotuvchilar
ro'yxatini o'qidi" degan YOLG'ON DALIL paydo bo'lardi — hech narsa
o'qilmagan bo'lsa ham. Nizoni hal qilishda aynan shu yozuvga tayanadigan
odam chalg'itilardi va bu jurnalning BO'SH qolishidan ham yomonroq
(`app/api/v1/audit.py` modul docstringi, 38–59-qatorlar; T-02-71).

Qoida `test_forbidden_read_is_not_audited` bilan qulflangan: tartibning
O'ZI hech nima demaydi, sabab esa aynan shu izohda va o'sha testda.
=============================================================================

`audit_read` FAQAT `GET` ENDPOINTLARIDA. `POST`/`PATCH` yozuv yo'llari
`fn_audit_row()` DB-triggeri bilan allaqachon qamralgan (`vendors` —
`AUDITED_TABLES` da, 02-05) va "o'qish niyati" yozuv endpointida ma'nosiz:
u "kim nimani KO'RDI" savoliga javob beradi, "kim nimani O'ZGARTIRDI"
savoliga esa trigger yozuvi javob beradi. Ikkalasini birga qo'yish har
`POST` uchun ikkita yozuv qoldirardi.

O'QISH VA YOZISH HUQUQLARI AJRATILGAN (D-07): `GET` uchun `VENDOR_VIEW`,
yozuv uchun `VENDOR_MANAGE`. Direktorda ikkinchisi YO'Q — u qarzdorlik
reestrini KO'RADI (hisobotlari shunsiz ma'nosiz), lekin sotuvchi qatorini
o'zgartira olmaydi. `VENDOR_VIEW` `MARKET_DATA_VIEW` dan ham ATAYIN
ajratilgan (`security/rbac.py`): shaxsiy ma'lumotga kirish huquqi zona
yoki toifa ro'yxatini ko'rish bilan bir xil og'irlikda emas.

TELEFON MASKALANMAYDI (UI-SPEC §8.6 [QAROR], T-02-77). Server raqamni
allaqachon yubordi — klientda yulduzcha chizish xavfsizlik teatri bo'lardi
va DevTools bilan bir bosishda ochilardi. Telefon esa OPERATSION
zaruriyat: admin sotuvchiga qo'ng'iroq qiladi. Haqiqiy himoya uch qavatli
va u boshqa joyda: RLS + `VENDOR_VIEW` huquqi + SHU YERDAGI o'qish
auditi.

CROSS-TENANT JAVOB — HAR DOIM 404 (T-02-67), 403 EMAS.

`market_id` HECH QACHON SO'ROV TANASIDAN OLINMAYDI (T-02-54):
`VendorRequest` va `VendorUpdateRequest` da bunday maydon umuman e'lon
qilinmagan.

-----------------------------------------------------------------------------
XATO XARITASI — FAQAT `sqlstate` BO'YICHA (`constraint_name` asyncpg
o'ramida `None`, RLS esa `DETAIL` ni o'chiradi — Pitfall 4):

    23505  ->  409 vendor_phone_taken   (`uq_vendors_market_id_phone_e164`)

Boshqa SQLSTATE QAYTA KO'TARILADI va global handler uni 500 ga aylantiradi:
"har ehtimolga qarshi" 409 yangi konstraytni jimgina noto'g'ri xabar bilan
yashirardi (`zones.py` / `stalls.py` / `tariffs.py` bilan bir xil qaror).

Telefon FORMATI bu yerda tekshirilmaydi — u chegarada (Pydantic
validatori) E.164 ga keltiriladi va o'qib bo'lmasa 422 beradi. DB'da
telefon formati uchun konstrayt ATAYIN yo'q (`sbozor_core.models.market.
Vendor` docstringi).
-----------------------------------------------------------------------------
"""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sbozor_core.timeutil import business_today
from sqlalchemy.exc import IntegrityError

from app.deps import Principal, TenantSessionDep, require_permission
from app.repositories.audit_repo import InvalidCursorError
from app.repositories.stall_repo import sqlstate_of
from app.repositories.vendor_repo import VendorRepository, VendorRow
from app.schemas import (
    VENDOR_STALL_CODES_MAX,
    VendorListItem,
    VendorListResponse,
    VendorQuery,
    VendorRequest,
    VendorUpdateRequest,
)
from app.security.audit import TABLE_VENDORS, AuditReadIntent, audit_read
from app.security.rbac import Permission

# `UUID` ish paytida kerak — FastAPI yo'l parametrlarining annotatsiyasini
# `get_type_hints` bilan o'qiydi (`zones.py` dagi bilan bir xil sabab).
log = structlog.get_logger(__name__)

router = APIRouter(tags=["vendors"])

VendorManagerDep = Annotated[Principal, Depends(require_permission(Permission.VENDOR_MANAGE))]
VendorViewerDep = Annotated[Principal, Depends(require_permission(Permission.VENDOR_VIEW))]
VendorReadIntentDep = Annotated[
    AuditReadIntent,
    Depends(audit_read(TABLE_VENDORS, reason="vendor_view")),
]
"""D-09: shaxsiy ma'lumotning HAR BIR o'qilishi jurnalga tushadi.

`reason` boshqa o'qish yuzalaridan FARQ QILADI (`audit_view`,
`platform_audit_view`): jurnalni o'qiyotgan odam "kim sotuvchilar
reestrini varaqladi" va "kim audit jurnalini ochdi" ni ajrata olishi
kerak. Bir xil `reason` bilan o'sha farq yo'qolardi va D-09 yozuvi
savolga to'liq javob bermay qolardi (`api/v1/audit.py` dagi bilan bir xil
qaror).
"""

_NOT_FOUND = "not_found"
_PHONE_TAKEN = "vendor_phone_taken"

UNIQUE_VIOLATION = "23505"
"""Bozor ICHIDA takroriy telefon — `uq_vendors_market_id_phone_e164` (D-12).

Unikalik GLOBAL EMAS va bu ataylab: bir odam ikki bozorda savdo qilishi
mumkin (T-02-44). Ya'ni bu kod "bu raqam allaqachon band" degani faqat
JORIY bozor doirasida.
"""


def _market_id(principal: Principal) -> UUID:
    """Tanlangan bozor (`zones.py` / `tariffs.py` dagi jufti bilan aynan bir xil)."""
    if principal.market_id is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="market_not_selected",
        )
    return principal.market_id


def _not_found() -> HTTPException:
    """Cross-tenant va mavjud bo'lmagan sotuvchi uchun BIR XIL javob (T-02-67)."""
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_NOT_FOUND)


def _write_conflict(exc: IntegrityError) -> HTTPException:
    """`vendors` yo'lidagi `IntegrityError` -> aniq `detail` kodi."""
    state = sqlstate_of(exc)
    if state == UNIQUE_VIOLATION:
        log.info("vendor_phone_taken", sqlstate=state)
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_PHONE_TAKEN)
    raise exc


def _describe(query: VendorQuery) -> dict[str, Any]:
    """Qo'llangan filtrlarning JSON tavsifi — o'qish yozuvi uchun.

    `cursor` CHIQARIB TASHLANADI: u opaque va jurnalni o'qiyotgan odamga
    hech nima aytmaydi. `limit` esa QOLADI — "kim butun reestrni yuklab
    oldi" savoliga aynan u javob beradi va shaxsiy ma'lumot uchun bu
    savol aynan muhimi (`api/v1/audit.py::_describe()` bilan bir xil
    qoida va bir xil sabab).
    """
    return query.model_dump(mode="json", exclude_none=True, exclude={"cursor"})


def _item(row: VendorRow) -> VendorListItem:
    """Repozitoriy qatorini javob elementiga o'giradi.

    Telefon MASKALANMAYDI — sabab modul docstringida (UI-SPEC §8.6).
    """
    return VendorListItem(
        id=row.id,
        full_name=row.full_name,
        phone=row.phone,
        stall_count=row.stall_count,
        stall_codes=list(row.stall_codes),
        created_at=row.created_at,
    )


async def _row_or_404(repo: VendorRepository, vendor_id: UUID) -> VendorListItem:
    """Yozuvdan KEYINGI javob — bitta joyda.

    Javob AYNAN o'qish yo'lidan quriladi, ya'ni klient `POST`/`PATCH` dan
    keyin `GET` qilganda boshqa shakl ko'rmaydi. `stall_count` /
    `stall_codes` ham shu tufayli to'g'ri chiqadi — ular yozuv paytida
    ma'lum emas, chunki biriktirish ALOHIDA endpoint orqali keladi.
    """
    row = await repo.get_vendor(vendor_id, business_today(), codes_limit=VENDOR_STALL_CODES_MAX)
    if row is None:  # pragma: no cover - o'sha tranzaksiyada yo'qolishi mumkin emas
        raise _not_found()
    return _item(row)


@router.get("", response_model=VendorListResponse)
async def list_vendors(
    principal: VendorViewerDep,
    intent: VendorReadIntentDep,
    query: Annotated[VendorQuery, Query()],
    session: TenantSessionDep,
) -> VendorListResponse:
    """Sotuvchilar reestri — keyset sahifa (`VENDOR_VIEW` + o'qish auditi).

    ⚠ ARGUMENTLAR TARTIBI XULQNING BIR QISMI — sabab modul docstringida.

    `q` — F.I.Sh. prefiksi yoki telefonning istalgan qismi. `stall_codes`
    BUGUN biriktirilgan rastalarning kodlari (`code_sort` tartibida, eng
    ko'pi `VENDOR_STALL_CODES_MAX` ta); to'liq son `stall_count` da.
    """
    repo = VendorRepository(session, _market_id(principal))
    try:
        page = await repo.list_vendors(query, business_today(), codes_limit=VENDOR_STALL_CODES_MAX)
    except InvalidCursorError as exc:
        # `audit.py` / `stalls.py` bilan AYNAN bir xil javob: buzuq kursor
        # 422, jimgina birinchi sahifaga qaytish EMAS (u sahifalashni
        # cheksiz siklga aylantirardi).
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="invalid_cursor",
        ) from exc

    intent.filters = _describe(query)
    intent.result_count = len(page.rows)

    return VendorListResponse(
        items=[_item(row) for row in page.rows],
        next_cursor=page.next_cursor,
    )


@router.get("/{vendor_id}", response_model=VendorListItem)
async def get_vendor(
    vendor_id: UUID,
    principal: VendorViewerDep,
    intent: VendorReadIntentDep,
    session: TenantSessionDep,
) -> VendorListItem:
    """Bitta sotuvchi (`VENDOR_VIEW` + o'qish auditi).

    RO'YXAT BILAN BIR XIL SHAKL qaytariladi (`VendorListItem`): sotuvchi
    kartochkasi ro'yxat qatoridan ortiq hech nima ko'rsatmaydi — telefon
    ikkalasida ham bor va biriktirish TARIXI alohida endpointdan keladi
    (`GET /stalls/{id}/assignments`).

    404 — sotuvchi mavjud emas YOKI begona bozorniki. Ikkala holat uchun
    javob BAYT-BAYT bir xil (T-02-67).

    Topilmagan holatda o'qish yozuvi QOLDIRILMAYDI: `HTTPException`
    ko'tarilganda FastAPI yangi javob quradi va unda fon vazifasi yo'q
    (`security/audit.py::audit_read` docstringidagi ikkinchi qatlam).
    """
    repo = VendorRepository(session, _market_id(principal))
    row = await repo.get_vendor(vendor_id, business_today(), codes_limit=VENDOR_STALL_CODES_MAX)
    if row is None:
        raise _not_found()

    # Yakka obyekt o'qishida "filtr" tushunchasi yo'q, lekin RESURS bor —
    # jurnalni o'qiyotgan odam "butun reestr varaqlandimi yoki bitta
    # sotuvchi ochildimi?" savoliga javob olishi kerak.
    intent.filters = {"vendor_id": str(vendor_id)}
    intent.result_count = 1

    return _item(row)


@router.post("", status_code=status.HTTP_201_CREATED, response_model=VendorListItem)
async def create_vendor(
    payload: VendorRequest,
    principal: VendorManagerDep,
    session: TenantSessionDep,
) -> VendorListItem:
    """Yangi sotuvchi (`VENDOR_MANAGE`, D-12).

    `audit_read` bu yerda YO'Q — sabab modul docstringida (yozuv yo'li
    DB-triggeri bilan qamralgan).

    409 `vendor_phone_taken` — shu BOZORDA bu raqam band; boshqa bozorda
    ayni raqam bemalol qabul qilinadi (D-12 nazorat holati).
    422 — telefonni E.164 ga keltirib bo'lmadi (chegara validatori).
    """
    repo = VendorRepository(session, _market_id(principal))
    try:
        vendor_id = await repo.create_vendor(full_name=payload.full_name, phone=payload.phone)
    except IntegrityError as exc:
        raise _write_conflict(exc) from exc

    return await _row_or_404(repo, vendor_id)


@router.patch("/{vendor_id}", response_model=VendorListItem)
async def update_vendor(
    vendor_id: UUID,
    payload: VendorUpdateRequest,
    principal: VendorManagerDep,
    session: TenantSessionDep,
) -> VendorListItem:
    """Sotuvchining ismi yoki telefonini tahrirlaydi (`VENDOR_MANAGE`).

    `exclude_unset=True` MAJBURIY: usiz har `PATCH` berilmagan maydonni
    ham `null` bilan qayta yozardi va ikkala ustun ham `NOT NULL` bo'lgani
    uchun so'rov 500 bilan tugardi.

    409 `vendor_phone_taken` — yangi raqam shu bozorda allaqachon band;
    404 — sotuvchi mavjud emas yoki begona bozorniki.
    """
    repo = VendorRepository(session, _market_id(principal))
    changes: dict[str, Any] = payload.model_dump(exclude_unset=True)
    try:
        updated = await repo.update_vendor(vendor_id, changes)
    except IntegrityError as exc:
        raise _write_conflict(exc) from exc

    if updated is None:
        raise _not_found()
    return await _row_or_404(repo, vendor_id)
