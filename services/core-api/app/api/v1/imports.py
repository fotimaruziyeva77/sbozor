"""Excel import (D-13/D-14/D-15) — Karmananing real ro'yxati kiradigan yo'l.

=============================================================================
TRANZAKSIYA BOSHQARUVI BU FAYLDA UMUMAN YO'Q — VA BU ATAYIN.

`TenantSessionDep` sessiyani ALLAQACHON tranzaksiya ichida beradi
(`app/deps.py::get_tenant_session`, 418–449-qatorlar). Ya'ni:

    endpointdan chiqqan HAR QANDAY istisno  ->  butun import orqaga qaytadi
    endpoint normal qaytdi                  ->  hammasi birgalikda yoziladi

D-14 (all-or-nothing) SHU SABABLI TEKIN KELADI va bu yerda hech qanday
qo'shimcha blok ochilmaydi. Ichki blok ochish uni faqat BUZARDI: ichki
qism muvaffaqiyat bilan yopilgach, undan keyingi xato allaqachon
yozilgan qatorlarni qoldirib ketardi.

(Bu qoida mexanik darvoza bilan qulflangan — qabul mezoni faylni
tranzaksiya ochish atamalari bo'yicha grep qiladi va natija NOL bo'lishi
shart. Shuning uchun o'sha atamalar bu izohda ham LITERAL yozilmagan:
02-08 deviatsiya #3 dagi bilan aynan bir xil sabab.)
=============================================================================

VALIDATSIYA YOZISHDAN OLDIN — DB XATOSIDAN FOYDALANIB BO'LMAYDI.

RLS yoqilgan jadvalda Postgres konstrayt xatosining `DETAIL` qatorini
BUTUNLAY o'chiradi (Pitfall 4, empirik — ega uchun ham). Ya'ni
"88-qator: 12 raqami takrorlangan" xabarini DB'dan OLIB BO'LMAYDI.
Butun tekshiruv `app/services/import_validator.py` da, YOZISHDAN OLDIN
bajariladi; DB konstrayti esa POYGA qo'riqchisi va u ishga tushsa javob
409 `import_conflict` bo'ladi.

409 D-14 NI BUZMAYDI, AKSINCHA UNGA MOS: tranzaksiya butunlay orqaga
qaytadi, ya'ni "hech narsa saqlanmadi" da'vosi o'sha yo'lda ham
to'g'ri qoladi.

-----------------------------------------------------------------------------
UCH DARVOZA, UCH XIL BOSQICH — TARTIB MAJBURIY:

  1. `_read_bounded()`  — bayt oqimi CHEGARADAN oshsa DARHOL to'xtaydi
                          (fayl xotiraga TO'LIQ olinmasdan);
  2. `xlsx_reader`      — ZIP bomba, XML bomba, qator/ustun/varaq;
  3. `import_validator` — mazmun: nom, kod, telefon, sana, takroriylik.

Birinchisi ikkinchisining O'RNINI BOSMAYDI: `read_rows()` `len(raw)` ni
tekshirganda baytlar ALLAQACHON xotirada bo'lardi.
-----------------------------------------------------------------------------

CHEGARALAR `SettingsDep` ORQALI OLINADI, `get_settings()` BILAN EMAS.

`get_settings()` `lru_cache` bilan MUHITDAN o'qiydi, integratsiya testi
esa faqat `app.state.settings` ni almashtiradi (`main.py` modul
docstringi va `deps.get_settings_dep` docstringi). To'g'ridan-to'g'ri
chaqiruv testda `ValidationError` bilan yiqilardi — bu O'LCHANDI:
dastlabki yozuvda AYNAN ikkita matritsa testi `3 validation errors for
Settings` bilan qulagan. Bundan muhimrog'i, u prod'da ham ilova
holatini CHETLAB o'tardi: `lifespan` bergan sozlama bilan endpoint
ko'rgan sozlama ajralib ketishi mumkin edi.

XATO XARITASI (`sqlstate` bo'yicha — `constraint_name` asyncpg o'ramida
`None` va RLS `DETAIL` ni o'chiradi):

    23505 / 23P01 / 23503  ->  409 import_conflict
    ImportRejected         ->  422 file_too_large | file_too_complex
                                   | unsupported_file_type
    issues bo'sh emas      ->  422 import_validation_failed + errors[]
    MarketProfileMissing   ->  409 market_incomplete

Noma'lum SQLSTATE QAYTA KO'TARILADI — global handler uni 500 ga
aylantiradi. "Har ehtimolga qarshi" 409 yangi konstraytni jimgina
noto'g'ri xabar bilan yashirardi (`zones.py`/`stalls.py` dagi qaror).

`market_id` HECH QACHON FAYLDAN OLINMAYDI (T-02-54): u faqat
`_market_id(principal)` dan keladi va shablonda bunday ustun umuman yo'q.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Literal
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from fastapi.responses import StreamingResponse
from sbozor_core.enums import AuditAction
from sbozor_core.security import hash_password
from sqlalchemy.exc import IntegrityError

from app.deps import (
    CurrentPasswordDep,
    Principal,
    SettingsDep,
    TenantSessionDep,
    require_permission,
)
from app.repositories import user_repo
from app.repositories.import_repo import ImportRepository
from app.repositories.stall_repo import MarketProfileMissingError, sqlstate_of
from app.repositories.user_repo import StaffCreateEntry, UserRepository
from app.schemas import (
    ImportErrorItem,
    ImportErrorReportRequest,
    ImportErrorResponse,
    ImportResultResponse,
    StaffCredentialItem,
    StaffImportResponse,
)
from app.security.audit import TABLE_USERS, write_app_audit
from app.security.rbac import Permission
from app.services import import_validator, xlsx_reader, xlsx_template
from app.services.staff_accounts import assignable_roles, temporary_password
from app.services.xlsx_reader import ImportRejected, ReadLimits

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.settings import Settings

# `UUID` ish paytida kerak — FastAPI yo'l va so'rov parametrlarining
# annotatsiyasini `get_type_hints` bilan o'qiydi (`zones.py` dagi sabab).
log = structlog.get_logger(__name__)

router = APIRouter(tags=["imports"])

StallManagerDep = Annotated[Principal, Depends(require_permission(Permission.STALL_MANAGE))]
VendorManagerDep = Annotated[Principal, Depends(require_permission(Permission.VENDOR_MANAGE))]
UserManagerDep = Annotated[Principal, Depends(require_permission(Permission.USER_MANAGE))]

ImportKind = Literal["stalls", "vendors", "staff"]
"""`?kind=` va marshrut nomlari uchun YAGONA tip.

`xlsx_template.TEMPLATE_KINDS` bilan qo'lda sinxron saqlanadi va ajralib
qolgan holatni `test_template_kinds_are_exactly_three` hamda OpenAPI
marshrutlar darvozasi birgalikda ushlaydi.
"""

_TEMPLATE_PERMISSIONS: dict[str, Permission] = {
    "stalls": Permission.STALL_MANAGE,
    "vendors": Permission.VENDOR_MANAGE,
    "staff": Permission.USER_MANAGE,
}
"""Shablon turi -> uni olish uchun kerak bo'ladigan huquq (D-07).

`staff` -> `USER_MANAGE`: shablon chaqiruvchi BERA OLADIGAN rollar
ro'yxatini o'z ichiga oladi, ya'ni u hisob yaratish yuzasining bir
qismi. Direktorda bu huquq YO'Q, ya'ni u shablonni ham ololmaydi.
"""

XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
XLSX_SUFFIX = ".xlsx"

_VALIDATION_FAILED = "import_validation_failed"
_UNSUPPORTED = "unsupported_file_type"
_CONFLICT = "import_conflict"
_MARKET_INCOMPLETE = "market_incomplete"
_ROSTER_TOO_LARGE = "staff_roster_too_large"

UNIQUE_VIOLATION = "23505"
EXCLUSION_VIOLATION = "23P01"
FK_VIOLATION = "23503"
_CONFLICT_STATES = frozenset({UNIQUE_VIOLATION, EXCLUSION_VIOLATION, FK_VIOLATION})
"""Uchala holat ham BITTA javobga (`409 import_conflict`) tushadi.

Ularni ajratish MA'NOSIZ bo'lardi: validatsiya yozishdan OLDIN
bajarilgani uchun bu yerga faqat POYGA holati yetib keladi (ikki admin
bir vaqtda import qildi), va poyga uchun foydalanuvchi bajaradigan
harakat uchalasida ham BIR XIL — "qayta urinib ko'ring". Xato MATNI
javobga chiqmaydi, u to'liq log'ga yoziladi (T-02-95).
"""


def _market_id(principal: Principal) -> UUID:
    """Tanlangan bozor (`zones.py` dagi yordamchining aynan nusxasi).

    `TenantSessionDep` allaqachon 409 qaytargan bo'lardi; bu tekshiruv
    KELAJAK uchun — kimdir endpointni tenant sessiyasisiz qayta yozsa,
    `market_id=None` bilan qator yozilib ketmasin.
    """
    if principal.market_id is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="market_not_selected",
        )
    return principal.market_id


async def require_template_access(
    principal: CurrentPasswordDep,
    kind: Annotated[ImportKind, Query()] = "stalls",
) -> Principal:
    """Shablon turi QAYSI huquqni talab qilishini hal qiladi.

    `?kind=stalls` -> `STALL_MANAGE`, `?kind=vendors` -> `VENDOR_MANAGE`,
    `?kind=staff` -> `USER_MANAGE`. Bitta huquqni hammasiga qo'yish D-07
    ning ajratishini buzardi: hozirgi matritsada uchala huquq HAM bir xil
    rollarda (bozor admini, platforma admini), lekin ular ATAYIN alohida
    tushunchalar va kelajakda ajralishi mumkin. Direktorda uchalasi ham
    YO'Q, ya'ni u birorta shablonni ham ololmaydi.

    `Literal` tipi noma'lum `kind` ni 422 bilan rad etadi. Autentifikatsiya
    BUNDAN OLDIN hal bo'ladi (`principal` — quyi dependency), ya'ni
    tokensiz so'rov baribir 401 oladi.
    """
    needed = _TEMPLATE_PERMISSIONS[kind]
    if needed not in principal.permissions:
        log.info("permission_denied", required=str(needed), roles=sorted(principal.roles))
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
    return principal


TemplateAccessDep = Annotated[Principal, Depends(require_template_access)]


@router.get("/template")
async def download_template(
    principal: TemplateAccessDep,
    session: TenantSessionDep,
    kind: Annotated[ImportKind, Query()] = "stalls",
) -> StreamingResponse:
    """Import shablonini yuklab beradi (`STALL_MANAGE` / `VENDOR_MANAGE`).

    Fayl HAR SAFAR yangidan quriladi — repoda nusxa saqlanmaydi
    (Open Question 5). Shu tufayli zona yoki toifa nomi tahrirlanganda
    keyingi yuklab olish AVTOMATIK yangi ro'yxat bilan keladi.

    Til `users.locale` dan olinadi, so'rov parametridan EMAS: profil
    tili — bitta HAQIQAT MANBAI va u `PATCH /me/locale` bilan
    o'zgaradi. Parametr sifatida qabul qilish ikkinchi manba tug'dirardi
    va admin interfeysi bir tilda, shabloni boshqa tilda kelib qolardi.
    (Bu shablonni BUZMAYDI — parser ustunlarni POZITSIYA bo'yicha
    o'qiydi, O-05 — lekin foydalanuvchini chalg'itardi.)
    """
    repo = ImportRepository(session, _market_id(principal))

    zones = sorted(await repo.zone_ids_by_name())
    categories = sorted(await repo.category_ids_by_name())
    locale = await _locale_of(session, principal)

    # Rol ro'yxati CHAQIRUVCHINING D-04 darajasidan quriladi, `Role`
    # enum'idan EMAS: bozor admini `director` ni tanlab, keyin
    # `role_not_allowed` olishi ustaning eng bema'ni yo'li bo'lardi.
    roles = sorted(str(role) for role in assignable_roles(principal.is_platform_admin))

    payload = xlsx_template.build_template(kind, locale, zones, categories, roles=roles)
    return _xlsx_response(payload, f"sbozor-{kind}-shablon.xlsx")


@router.post("/stalls", response_model=ImportResultResponse)
async def import_stalls(
    principal: StallManagerDep,
    session: TenantSessionDep,
    settings: SettingsDep,
    file: Annotated[UploadFile, File()],
) -> ImportResultResponse:
    """Rastalarni `.xlsx` dan ommaviy yozadi (`STALL_MANAGE`).

    Ustunlar (A6): `kod, zona, toifa, holat, izoh` — POZITSIYA bo'yicha.
    """
    repo = ImportRepository(session, _market_id(principal))
    rows = _read(await _read_bounded(file, settings), import_validator.STALL_COLUMNS, settings)

    zones = await repo.zone_ids_by_name()
    categories = await repo.category_ids_by_name()
    existing = await repo.existing_stall_codes()

    accepted, issues = import_validator.validate_stall_rows(
        rows,
        zones=zones,
        categories=categories,
        existing_codes=existing,
    )
    _reject_if_invalid(issues)

    try:
        operating_since = await repo.operating_since()
        inserted = await repo.insert_stalls(accepted, valid_from=operating_since)
    except MarketProfileMissingError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=_MARKET_INCOMPLETE,
        ) from exc
    except IntegrityError as exc:
        raise _conflict(exc) from exc

    return ImportResultResponse(inserted=inserted, skipped=len(rows) - inserted)


@router.post("/vendors", response_model=ImportResultResponse)
async def import_vendors(
    principal: VendorManagerDep,
    session: TenantSessionDep,
    settings: SettingsDep,
    file: Annotated[UploadFile, File()],
) -> ImportResultResponse:
    """Sotuvchilarni `.xlsx` dan ommaviy yozadi (`VENDOR_MANAGE`).

    Ustunlar (A6): `F.I.Sh., telefon, rasta kodi, boshlanish sanasi`.
    Rasta kodi berilgan qatorlar uchun OCHIQ biriktirish davri ham
    yoziladi; kodi bo'sh sotuvchi reestrga rastasiz tushadi (D-11).
    """
    repo = ImportRepository(session, _market_id(principal))
    rows = _read(await _read_bounded(file, settings), import_validator.VENDOR_COLUMNS, settings)

    try:
        operating_since = await repo.operating_since()
    except MarketProfileMissingError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=_MARKET_INCOMPLETE,
        ) from exc

    accepted, issues = import_validator.validate_vendor_rows(
        rows,
        stalls_by_code=await repo.stall_ids_by_code(),
        existing_phones=await repo.existing_vendor_phones(),
        default_from=operating_since,
    )
    _reject_if_invalid(issues)

    try:
        inserted = await repo.insert_vendors(accepted)
    except IntegrityError as exc:
        raise _conflict(exc) from exc

    return ImportResultResponse(inserted=inserted, skipped=len(rows) - inserted)


@router.post("/staff", response_model=StaffImportResponse)
async def import_staff(
    principal: UserManagerDep,
    session: TenantSessionDep,
    settings: SettingsDep,
    response: Response,
    file: Annotated[UploadFile, File()],
) -> StaffImportResponse:
    """Xodimlar rosterini `.xlsx` dan ommaviy hisobga aylantiradi (`USER_MANAGE`).

    Ustunlar (A6): `F.I.Sh., telefon, rol` — POZITSIYA bo'yicha.

    TARTIB MAJBURIY VA U SHU YERDA LITERAL YOZILGAN:

      1. `_read_bounded()` -> `_read()` — 02-12 ning uch darvozasi;
      2. ROSTER HAJMI (`import_max_staff_rows`) — umumiy qator
         chegarasidan KEYIN va validatsiyadan OLDIN;
      3. chaqiruvchining D-04 darajasi (`assignable_roles`);
      4. joriy bozor a'zolarining telefonlari (D-15 skip lug'ati);
      5. `validate_staff_rows()` -> bitta xato ham bo'lsa 422, HECH NARSA
         yozilmaydi;
      6. har qabul qilingan qator uchun vaqtinchalik parol + Argon2id
         hash — OCHIQ qiymat FAQAT lokal lug'atda qoladi;
      7. `create_members()`; band telefonlar qaytsa ular ham 422 ga
         aylanadi;
      8. har hisob uchun audit yozuvi;
      9. importning O'ZI uchun bitta YIG'MA audit yozuvi;
     10. `Cache-Control: no-store`.

    ⚠ 7-QADAMDAGI 422 D-14 NI BUZMAYDI, GARCHI KOD SHUNDAY KO'RINSA HAM.
    O'sha paytda `create_members()` allaqachon bir nechta `users` qatorini
    yozgan bo'ladi — lekin `HTTPException` endpointdan chiqadi,
    `TenantSessionDep` esa butun ishni orqaga qaytaradi, ya'ni yozilgan
    hisoblar HAM yo'qoladi. Bu fakt kodni o'qigan odam uchun ravshan
    emas, shuning uchun u shu yerda literal yozilgan.

    ⚠ OCHIQ PAROL HECH QANDAY JURNALGA UZATILMAYDI: pastdagi `log.info`
    faqat SANOQLARNI oladi. `censor_secrets` ikkinchi qatlam (kalit
    `SENSITIVE_KEYS` da va senzura rekursiv); birinchi qatlam esa uni
    umuman uzatmaslik.

    ⚠ `market_id` HECH QACHON FAYLDAN OLINMAYDI (T-02-54): u faqat
    `_market_id(principal)` dan keladi va shablonda bunday ustun umuman
    yo'q.
    """
    repo = UserRepository(session, _market_id(principal))
    rows = _read(await _read_bounded(file, settings), import_validator.STAFF_COLUMNS, settings)

    if len(rows) > settings.import_max_staff_rows:
        log.warning("staff_roster_too_large", rows=len(rows), limit=settings.import_max_staff_rows)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=_ROSTER_TOO_LARGE,
        )

    allowed = frozenset(str(role) for role in assignable_roles(principal.is_platform_admin))
    accepted, issues = import_validator.validate_staff_rows(
        rows,
        allowed_roles=allowed,
        existing_member_phones=await repo.existing_member_phones(),
    )
    _reject_if_invalid(issues)

    locale = await _locale_of(session, principal)
    # Ochiq parollar SHU LUG'ATDA va boshqa hech qayerda: repozitoriyga
    # faqat hash ketadi (`user_repo` modul docstringi).
    secrets_by_row = {row.row: temporary_password() for row in accepted}
    entries = [
        StaffCreateEntry(
            row=row.row,
            phone=row.phone,
            password_hash=hash_password(secrets_by_row[row.row]),
            full_name=row.full_name,
            locale=locale,
            roles=list(row.roles),
        )
        for row in accepted
    ]

    created, taken = await repo.create_members(entries)
    _reject_if_invalid(
        [
            import_validator.ImportIssue(
                row=number,
                code="phone_taken",
                message=f"{number}-qator: bu telefon platformada allaqachon band",
            )
            for number in taken
        ]
    )

    for member in created:
        # `users.py::create_user` dagi bilan AYNAN bir xil shakl: a'zolik
        # qatorining O'Z auditi `fn_audit_row()` triggeridan avtomatik
        # keladi, `users` uchun esa trigger YO'Q (`SECURITY DEFINER`).
        await write_app_audit(
            session,
            action=AuditAction.INSERT,
            table_name=TABLE_USERS,
            row_id=member.user_id,
            principal=principal,
            new={"phone": member.phone, "roles": member.roles, "locale": locale},
        )

    # ⚠ YIG'MA YOZUV MAJBURIY. Usiz jurnalda 30 ta alohida `insert`
    # ko'rinardi va "bular BITTA ommaviy amaldan" degan fakt yo'qolardi —
    # nizoda aynan shu savol so'raladi (T-02-180). `track_changes=False`:
    # bu yozuvda "nima o'zgardi" degan savolning ma'nosi yo'q, u amalning
    # O'ZINI tasvirlaydi.
    await write_app_audit(
        session,
        action=AuditAction.INSERT,
        table_name=TABLE_USERS,
        row_id=None,
        principal=principal,
        new={
            "import": "staff",
            "rows": len(rows),
            "created": len(created),
            "skipped": len(rows) - len(created),
            "roles": sorted({role for member in created for role in member.roles}),
        },
        track_changes=False,
    )

    log.info("staff_import_done", created=len(created), skipped=len(rows) - len(created))
    # Javob o'nlab OCHIQ parolni olib yuradi — u hech qayerda
    # keshlanmasligi kerak (T-02-176).
    response.headers["Cache-Control"] = "no-store"

    return StaffImportResponse(
        inserted=len(created),
        skipped=len(rows) - len(created),
        credentials=[
            StaffCredentialItem(
                row=member.row,
                phone=member.phone,
                full_name=member.full_name,
                roles=member.roles,
                temporary_password=secrets_by_row[member.row],
            )
            for member in created
        ],
    )


@router.post("/errors.xlsx")
async def download_error_report(
    payload: ImportErrorReportRequest,
    principal: StallManagerDep,
    session: TenantSessionDep,
) -> StreamingResponse:
    """422 javobidagi xatolarni `.xlsx` qilib qaytaradi (UI-SPEC §8.5).

    Klient 422 javobining `errors` massivini AYNAN qaytarib yuboradi.
    Server uni saqlamaydi: 300 qatorlik xato ro'yxatini bazaga yozish
    hech qanday savolga javob bermaydigan, lekin o'chirilishi kerak
    bo'lgan ma'lumot yaratardi.

    Kirish uzunligi `ImportErrorReportRequest` da CHEGARALANGAN
    (T-02-97): usiz endpoint o'z-o'ziga DoS bo'lardi — 10 million
    elementli massiv serverda 10 million qatorli fayl qurdirardi.

    `TenantSessionDep` bu yerda MA'LUMOT uchun emas, DARVOZA uchun:
    usiz endpoint bozor tanlanmagan sessiya bilan ham ishlab ketardi.
    """
    _market_id(principal)

    issues = [
        import_validator.ImportIssue(row=item.row, code=item.code, message=item.message)
        for item in payload.errors
    ]
    report = xlsx_template.build_error_report(issues, await _locale_of(session, principal))

    return _xlsx_response(report, "sbozor-import-xatolar.xlsx")


async def _locale_of(session: AsyncSession, principal: Principal) -> str:
    """Foydalanuvchi profilidagi til; topilmasa uz-Latn.

    Profil qatori yo'q bo'lishi amalda mumkin emas (token o'sha
    foydalanuvchi uchun chiqarilgan), lekin bu yerda istisno ko'tarish
    shablonni yuklab olishni butunlay to'sardi — sabab esa mutlaqo
    ahamiyatsiz bo'lardi.
    """
    profiles = await user_repo.list_profiles(session, [principal.user_id])
    return profiles[0].locale if profiles else "uz-Latn"


async def _read_bounded(file: UploadFile, settings: Settings) -> bytes:
    """Yuklangan faylni CHEGARALANGAN holda o'qiydi.

    ⚠ BU DARVOZA `xlsx_reader.MAX_UPLOAD_BYTES` NING O'RNINI BOSMAYDI,
    UNDAN OLDIN TURADI. `read_rows()` `len(raw)` ni tekshirganda
    baytlar ALLAQACHON xotirada bo'lardi, ya'ni 4 GB lik yuklama
    chegaraga YETIB BORMASDAN konteynerni o'ldirardi (T-02-89).

    Shuning uchun o'qish bo'lak-bo'lak boradi va chegaradan oshgan
    zahoti to'xtaydi — qolgan baytlar UMUMAN o'qilmaydi.

    Kengaytma ham SHU YERDA tekshiriladi, lekin u faqat QULAYLIK:
    haqiqiy darvoza — ZIP va XML qatlami (`xlsx_reader`), u fayl
    nomiga umuman qaramaydi va `.xlsx` deb nomlangan PDF ni ham rad
    etadi.
    """
    name = (file.filename or "").lower()
    if not name.endswith(XLSX_SUFFIX):
        log.info("import_bad_extension", filename=name)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=_UNSUPPORTED,
        )

    limit = settings.import_max_upload_bytes
    chunks: list[bytes] = []
    total = 0
    while chunk := await file.read(64 * 1024):
        total += len(chunk)
        if total > limit:
            log.warning("import_upload_too_large", read_bytes=total, limit=limit)
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="file_too_large",
            )
        chunks.append(chunk)
    return b"".join(chunks)


def _read(raw: bytes, expected_columns: int, settings: Settings) -> list[xlsx_reader.SheetRow]:
    """`xlsx_reader` ni chaqiradi va `ImportRejected` ni 422 ga aylantiradi.

    Chegaralar `app/settings.py` dan olinadi (A7), modul standartlaridan
    emas: 1000 rastadan kattaroq bozor kelganda ular deploy qayta
    qurilmasdan kengaytiriladi.
    """
    try:
        return xlsx_reader.read_rows(
            raw,
            expected_columns=expected_columns,
            limits=ReadLimits.from_settings(settings),
        )
    except ImportRejected as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=exc.code,
        ) from exc


def _reject_if_invalid(issues: list[import_validator.ImportIssue]) -> None:
    """Bitta xato ham bo'lsa 422 — HECH NARSA yozilmaydi (D-14).

    `errors` massivi TO'LIQ yuboriladi: UI birinchi 50 tasini
    ko'rsatadi va qolganini `.xlsx` qilib yuklab oladi (UI-SPEC §8.5),
    ya'ni kesish SERVERDA emas, KLIENTDA bo'ladi.

    `error_counts` — kod bo'yicha guruhlangan sanoq. Bu ekranning eng
    qimmatli qismi: 300 ta qator o'qib bo'lmaydi, 3 ta jumla o'qiladi
    va harakatga aylanadi.

    Javob `HTTPException(detail=...)` bilan qurilsa `errors` bir daraja
    pastga tushib (`{"detail": {"detail": ..., "errors": [...]}}`)
    `ImportErrorResponse` shartnomasini buzardi — 02-11 dagi
    `blocking[]` bilan AYNAN bir xil holat. Shuning uchun tana
    DTO'dan quriladi va `HTTPException` ning `detail` iga BUTUNLIGICHA
    beriladi.
    """
    if not issues:
        return

    counts: dict[str, int] = {}
    for issue in issues:
        counts[issue.code] = counts.get(issue.code, 0) + 1

    body = ImportErrorResponse(
        detail=_VALIDATION_FAILED,
        errors=[
            ImportErrorItem(row=issue.row, code=issue.code, message=issue.message)
            for issue in issues
        ],
        error_counts=counts,
    )
    log.info("import_validation_failed", errors=len(issues), counts=counts)
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail=body.model_dump(),
    )


def _conflict(exc: IntegrityError) -> HTTPException:
    """Konstrayt buzilishini 409 `import_conflict` ga aylantiradi.

    Bu yerga faqat POYGA holati yetib keladi: mazmun xatolari
    validatorda, YOZISHDAN OLDIN ushlangan. Xom xato matni javobga
    HECH QACHON tushmaydi (T-02-95) — u jadval va konstrayt nomlarini
    oshkor qilardi; sabab to'liq log'ga yoziladi.

    ⚠ 409 D-14 NI BUZMAYDI. Istisno tranzaksiyani butunlay orqaga
    qaytaradi, ya'ni "hech narsa saqlanmadi" da'vosi bu yo'lda ham
    to'g'ri.

    Noma'lum SQLSTATE QAYTA KO'TARILADI — global handler uni 500 ga
    aylantiradi va yangi konstrayt jimgina noto'g'ri xabar bilan
    yashirinmaydi.
    """
    state = sqlstate_of(exc)
    if state in _CONFLICT_STATES:
        log.warning("import_conflict", sqlstate=state, error=str(exc.orig))
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_CONFLICT)
    raise exc


def _xlsx_response(payload: bytes, filename: str) -> StreamingResponse:
    """`.xlsx` baytlarini yuklab olish javobi qilib o'raydi.

    `Content-Disposition: attachment` — usiz brauzer faylni ko'rsatishga
    urinardi. Fayl nomi ASCII: `filename*=UTF-8''` shakli kerak emas va
    kirill nomli sarlavha eski proksilarni buzardi.
    """
    return StreamingResponse(
        iter([payload]),
        media_type=XLSX_MEDIA_TYPE,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(payload)),
        },
    )
