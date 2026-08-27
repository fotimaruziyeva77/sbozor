"""Audit jurnalini ko'rish (D-11, D-12) — va ko'rishning O'ZINI qayd etish (D-09).

=============================================================================
IKKI ENDPOINT, IKKI TURLI CHEGARA — VA ULAR ARALASHTIRILMAYDI:

| Endpoint                   | Qatorlar            | Darvoza                    |
| -------------------------- | ------------------- | -------------------------- |
| `GET /api/v1/audit`        | `market_id` = tanl. | `AUDIT_VIEW` huquqi + RLS  |
| `GET /api/v1/audit/platform`| `market_id IS NULL`| `is_platform_admin` BAYROG'I|

Ikkinchisi birinchisining "kengaytirilgan" varianti EMAS: ularning
qatorlar to'plami KESISHMAYDI. Platforma endpointi bozor yozuvlarini
hech qachon qaytarmaydi (funksiya sharti LITERAL `market_id IS NULL`),
tenant endpointi esa `market_id IS NULL` qatorlarni hech qachon
ko'rsatmaydi (`audit_read` policy'si `market_id = app.market_id`).

Ya'ni platforma yo'lini qo'shish tenant izolyatsiyasini KENGAYTIRMAYDI —
u faqat hech qaysi bozorga tegishli BO'LMAGAN yozuvlarga o'qish yo'li
ochadi (Gap 5). Quyidagi hamma narsa birinchi endpointga tegishli.
=============================================================================

KIM KO'RADI: `AUDIT_VIEW` huquqi bo'lganlar — platforma admini, direktor
va bozor admini (01-06 matritsasi). Kassir va nazoratchida bu huquq YO'Q
va bu ataylab: jurnal shaxsiy ma'lumot (kim, qachon, qaysi telefon bilan
kirgani) to'plami, ya'ni unga kirish nazorat funksiyasi bilan cheklanadi.

NIMA KO'RADI: FAQAT o'z bozorining yozuvlari. Buni ikki qatlam
majburlaydi — `audit_read` RLS policy'si (01-05) va `AuditRepository`
ning `scoped()` predikati. Platforma admini ham istisno emas: u bozor
TANLAB kiradi va tanlangandan keyin oddiy tenant kontekstida ishlaydi
(D-06).

KO'RGANI YOZILADI: `Depends(audit_read(...))` — bu endpointning
qaytariladigan ma'lumotidan KAM emas darajada muhim qismi. O'zbekiston
shaxsiy ma'lumotlar qonuni o'qishni ham qayd etishni talab qiladi (D-09).
=============================================================================

RAD ETILGAN SO'ROV JURNALDA IZ QOLDIRMAYDI — IKKI MUSTAQIL QATLAM:

    1. E'LON TARTIBI. `require_permission(AUDIT_VIEW)` `audit_read` dan
       OLDIN turadi. FastAPI dependency'larni aynan shu tartibda hal
       qiladi va birinchi `HTTPException` qolganlarini umuman chaqirmaydi,
       ya'ni 403 olgan so'rovda o'qish niyati QURILMAYDI ham.
    2. FON VAZIFASI JAVOBGA BOG'LANADI. Yozuv `BackgroundTasks` orqali
       ketadi, `BackgroundTasks` esa endpoint MUVAFFAQIYATLI qaytargan
       javob obyektiga biriktiriladi. Istisno bilan tugagan so'rov uchun
       FastAPI YANGI javob quradi va unda fon vazifasi yo'q — shu sababli
       422 (query validatsiyasi endpointdan KEYIN xato beradi) ham iz
       qoldirmaydi.

IKKALASI HAM O'LCHANDI: bittasini alohida buzganda testlar YASHIL qoladi
(ikkinchisi ushlaydi), ikkalasi birga buzilganda esa
`test_rejected_request_writes_no_read_row` va
`test_invalid_query_writes_no_read_row` darhol qizaradi. Ya'ni bu
haqiqiy ikki qatlam, bir qarorning ikki ta'rifi emas.

Nima uchun ikkitasi kerak: jurnaldagi YOLG'ON dalil (403 olgan kassir
"o'qidi" deb yozilishi) nizoni hal qilishda aynan shu yozuvga tayanadigan
odamni chalg'itadi — bu jurnalning bo'sh qolishidan ham yomonroq.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.deps import (
    AuthSessionDep,
    Principal,
    TenantSessionDep,
    require_permission,
    require_platform_admin,
)
from app.repositories import audit_repo
from app.repositories.audit_repo import (
    AuditRepository,
    InvalidCursorError,
    mask_sensitive,
)
from app.schemas import AUDIT_PAGE_SIZE_MAX, AuditEntry, AuditListResponse, AuditQuery
from app.security.audit import TABLE_AUDIT_LOG, AuditReadIntent, audit_read
from app.security.rbac import Permission

if TYPE_CHECKING:
    from uuid import UUID

    from sbozor_core.models import AuditLog

    from app.repositories.audit_repo import PlatformAuditRow

router = APIRouter(tags=["audit"])

AuditViewerDep = Annotated[Principal, Depends(require_permission(Permission.AUDIT_VIEW))]
AuditReadIntentDep = Annotated[
    AuditReadIntent,
    Depends(audit_read(TABLE_AUDIT_LOG, reason="audit_view")),
]

PlatformAuditViewerDep = Annotated[Principal, Depends(require_platform_admin)]
PlatformAuditReadIntentDep = Annotated[
    AuditReadIntent,
    Depends(audit_read(TABLE_AUDIT_LOG, reason="platform_audit_view")),
]
"""`reason` TENANT YO'LIDAN FARQ QILADI (`audit_view` emas).

Jurnalni o'qiyotgan odam ikki xil o'qishni ajrata olishi kerak: "bozor
admini o'z bozorining jurnalini ochdi" va "platforma admini
platforma-global hodisalarni ko'rdi". Ikkalasi bir xil `reason` bilan
yozilganda o'sha farq YO'QOLARDI va D-09 yozuvi savolga to'liq javob
bermay qolardi.
"""


def _market_id(principal: Principal) -> UUID:
    """Tanlangan bozor (`TenantSessionDep` allaqachon 409 qaytargan bo'lardi)."""
    if principal.market_id is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="market_not_selected",
        )
    return principal.market_id


def _describe(query: AuditQuery) -> dict[str, Any]:
    """Qo'llangan filtrlarning JSON tavsifi — o'qish yozuvi uchun.

    `mode="json"` sana va UUID qiymatlarini satrga o'giradi (JSONB'ga
    to'g'ridan-to'g'ri tushadi). `cursor` CHIQARIB TASHLANADI: u opaque
    va jurnalni o'qiyotgan odamga hech nima aytmaydi; `limit` esa qoladi,
    chunki "kim butun jurnalni yuklab oldi" savoliga aynan u javob beradi.
    """
    return query.model_dump(mode="json", exclude_none=True, exclude={"cursor"}, by_alias=True)


def _entry(row: AuditLog | PlatformAuditRow) -> AuditEntry:
    """Qatorni javob shakliga o'giradi — MASKALASH shu yerda, BIR JOYDA.

    Ikkala endpoint ham shu funksiyadan o'tadi. Nusxa ko'chirilganda
    xavf aniq: kelajakda `SENSITIVE_AUDIT_KEYS` ga yangi kalit qo'shilsa
    yoki maskalash mantiqi o'zgarsa, ikkinchi nusxa jimgina eski holicha
    qolardi va aynan platforma yo'li (kamroq ko'riladigan) himoyasiz
    bo'lib qolardi (T-01-52).

    Kirish tipi UNION: `AuditLog` (ORM, tenant yo'li) va `PlatformAuditRow`
    (`SECURITY DEFINER` funksiyasi, platforma yo'li) bir xil maydon
    nomlariga ega, chunki funksiyaning `RETURNS TABLE` imzosi ATAYIN
    jadval ustunlaridan nusxa olingan (01-14). Nomlar ajralib ketsa mypy
    darhol qizaradi — ya'ni bu moslik hujjatda emas, tiplarda qulflangan.
    """
    return AuditEntry(
        id=row.id,
        at=row.at,
        business_date=row.business_date,
        actor_user_id=row.actor_user_id,
        actor_label=row.actor_label,
        action=row.action,
        table_name=row.table_name,
        row_id=row.row_id,
        changed_keys=row.changed_keys,
        old_value=mask_sensitive(row.old_value),
        new_value=mask_sensitive(row.new_value),
        request_id=row.request_id,
        source=row.source,
    )


@router.get("", response_model=AuditListResponse)
async def list_audit(
    principal: AuditViewerDep,
    intent: AuditReadIntentDep,
    query: Annotated[AuditQuery, Query()],
    session: TenantSessionDep,
) -> AuditListResponse:
    """Filtrlanadigan audit ro'yxati (D-12).

    Javobdagi `old_value`/`new_value` JSONB'lari MASKALANADI: jurnalga
    tasodifan tushgan sezgir maydon ko'rish ekrani orqali tarqalmasligi
    kerak (T-01-52).
    """
    try:
        page = await AuditRepository(session, _market_id(principal)).list_audit(query)
    except InvalidCursorError as exc:
        # `HTTP_422_UNPROCESSABLE_CONTENT` — RFC 9110 dagi joriy nom;
        # eski `..._ENTITY` taxallusi Starlette'da eskirgan (bir xil 422).
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="invalid_cursor",
        ) from exc

    intent.filters = _describe(query)
    intent.result_count = len(page.rows)

    return AuditListResponse(
        items=[_entry(row) for row in page.rows],
        next_cursor=page.next_cursor,
    )


@router.get("/platform", response_model=AuditListResponse)
async def list_platform_audit(
    principal: PlatformAuditViewerDep,
    intent: PlatformAuditReadIntentDep,
    session: AuthSessionDep,
    limit: Annotated[int, Query(ge=1, le=AUDIT_PAGE_SIZE_MAX)] = 50,
    cursor: Annotated[str | None, Query()] = None,
) -> AuditListResponse:
    """Platforma-global (`market_id IS NULL`) audit yozuvlari — Gap 5 ning yopilishi.

    NIMA KO'RINADI: HECH QAYSI bozorga tegishli bo'lmagan hodisalar —
    birinchi navbatda `login_failed` ("kim tizimga kirishga urinmoqda"
    savoli, FOUND-03). Bunday yozuvda `market_id` ATAYIN `NULL`: rad
    etilgan login urinishida bozor NOMA'LUM va uni taxmin qilish jurnalga
    yolg'on dalil yozish bo'lardi (01-06). Aynan shu sababli ular
    `GET /api/v1/audit` (tenant-scoped) orqali HECH QACHON ko'rinmagan va
    01-06 -> 01-07 -> 01-09 zanjirida uch marta ochiq bo'shliq sifatida
    qayd etilgan edi.

    TENANT QATORLARI BU YERDA YO'Q. Funksiyaning sharti LITERAL
    `market_id IS NULL` (`auth_list_platform_audit`, 0005), ya'ni bu
    endpoint "RLS'siz butun audit jurnalini o'qish" vositasi EMAS va
    unga aylantirib ham bo'lmaydi: bozor qatorlari funksiyadan umuman
    qaytmaydi. Platforma admini bozor yozuvlarini ko'rish uchun baribir
    bozor TANLAB `GET /api/v1/audit` ga boradi (D-06).

    NEGA `AuthSessionDep`, `TenantSessionDep` EMAS: bu yerda o'qiladigan
    qatorlarning tenant konteksti YO'Q va funksiya `SECURITY DEFINER`,
    ya'ni GUC'ga umuman qaramaydi. `TenantSessionDep` bo'lganda bozor
    tanlamagan platforma admini 409 `market_not_selected` olardi — lekin
    u aynan platforma darajasidagi hodisalarni ko'rmoqchi va uni "avval
    biror bozorni tanlang" deb qaytarish ma'nosiz bo'lardi.

    DARVOZA — `require_platform_admin` (`users.is_platform_admin`
    BAYROG'I). Funksiyaning `sbozor_app` ga `GRANT EXECUTE` qilingani
    o'z-o'zidan HUQUQ BERMAYDI: u faqat "ilova chaqira oladi" degani.
    RBAC har doim ilova qatlamida (D-07) va bu yerda u rolga emas,
    bayroqqa tayanadi (CR-03 — sabab `app/deps.py` da).

    KO'RGANI YOZILADI (D-09): `reason='platform_audit_view'`. Yozuv
    `principal.market_id` bilan tushadi — bozor tanlamagan admin uchun u
    ham `market_id IS NULL` bo'ladi va keyingi so'rovda shu endpointning
    O'ZIDA ko'rinadi. Bu KUTILGAN xulq: platforma jurnalini kim ko'rgani
    ham platforma darajasidagi hodisa.
    """
    try:
        page = await audit_repo.list_platform_audit(session, limit=limit, cursor=cursor)
    except InvalidCursorError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="invalid_cursor",
        ) from exc

    # `cursor` filtrlar tavsifiga KIRMAYDI (`_describe` bilan bir xil qoida):
    # u opaque va jurnalni o'qiyotgan odamga hech nima aytmaydi. `limit`
    # esa qoladi — "kim butun jurnalni yuklab oldi" savoliga aynan u javob beradi.
    intent.filters = {"limit": limit}
    intent.result_count = len(page.rows)

    return AuditListResponse(
        items=[_entry(row) for row in page.rows],
        next_cursor=page.next_cursor,
    )
