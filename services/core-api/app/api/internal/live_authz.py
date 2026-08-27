"""nginx `auth_request` nishoni — jonli ko'rishning YAGONA avtorizatsiya nuqtasi.

=============================================================================
NEGA BU MARSHRUT BOR: go2rtc TENANT TUSHUNMAYDI.

go2rtc'da faqat GLOBAL Basic-auth bor — «bozor» tushunchasining o'zi yo'q.
Uni foydalanuvchiga ochish A bozori direktoriga B bozori kamerasini
berardi (T-03-46) va SC#6 ni buzardi. Avtorizatsiya mantiqi go2rtc'da
YO'Q va u yerda BO'LISHI HAM KERAK EMAS: media serveri media uzatadi,
huquq qarorini esa domenni biladigan servis qabul qiladi.

Shuning uchun nginx har `/live/...` so'rovida SHU marshrutga subso'rov
yuboradi va faqat STATUSGA qaraydi:

    204  ->  so'rov go2rtc'ga o'tkaziladi
    403  ->  so'rov rad etiladi

=============================================================================
JAVOB TANASI HAR DOIM BO'SH — VA BU XAVFSIZLIK QARORI.

`auth_request` tanani UMUMAN o'qimaydi, lekin nginx javobni o'z
jurnaliga (`error_log`) yozishi mumkin. Tanadagi har qanday tafsilot —
«kamera topilmadi», «boshqa bozor», «token muddati o'tgan» — o'sha
jurnalga sizib ketardi va u odatda ilova jurnalidan KO'RA kengroq
o'qiladi. Sabab bizning `structlog` yozuvimizda qoladi.
=============================================================================

=============================================================================
⚠ TOKEN VA `src` NING MOSLIGI MAJBURIY — USIZ BUTUN DARVOZA MA'NOSIZ.

URL shakli: `/live/api/ws?src=<oqim-nomi>&t=<chipta>`.

Agar biz faqat chiptani tekshirsak (imzo + muddat + kamera->bozor), A
bozori direktori O'Z kamerasi uchun haqiqiy chipta olib, keyin `src` ni
B bozori kamerasining oqim nomiga ALMASHTIRIB yuborishi mumkin edi —
va tekshiruv baribir 204 berardi, chunki chipta haqiqiy. go2rtc esa
`src` bo'yicha oqimni topib berardi.

Ya'ni chipta OQIM NOMIGA bog'lanishi shart. Tekshiruv: chiptadagi
`camera_id` ga mos qatorning `stream_name` i so'rovdagi `src` bilan
AYNAN teng bo'lishi kerak.

Bu tekshiruv `test_live_view.py::test_token_does_not_work_for_another_
cameras_stream` bilan qulflangan.
=============================================================================

MARSHRUT PREFIKSSIZ VA RBAC DEPENDENCY'SIZ (`main.py::healthz` naqshi):
uni FOYDALANUVCHI emas, nginx chaqiradi va unda `Authorization`
sarlavhasi umuman bo'lmaydi. Himoya ikki qatlamli — nginx tomonda
`internal;`, bu yerda esa chiptaning O'ZI: tokensiz so'rov 403 oladi
va bu `auth_request` nishoni to'g'ridan-to'g'ri chaqirilganda ham
o'z kuchida qoladi.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import parse_qs, urlsplit

import jwt
import structlog
from fastapi import APIRouter, Request, Response, status
from sbozor_core.enums import ActorKind
from sbozor_core.tenancy import set_tenant_context

from app.repositories.nvr_repo import NvrRepository
from app.security.tokens import decode_live_token

if TYPE_CHECKING:
    from sbozor_core.security import LiveClaims

    from app.settings import Settings

log = structlog.get_logger(__name__)

router = APIRouter(include_in_schema=False)

ORIGINAL_URI_HEADER = "X-Original-URI"
"""nginx `auth_request` subso'roviga qo'yadigan asl so'rov yo'li (query bilan).

`auth_request` subso'rovi asl so'rovning query parametrlarini O'ZI bilan
OLIB KELMAYDI — u faqat `auth_request` da ko'rsatilgan yo'lga boradi.
Shuning uchun asl URI aniq sarlavha bilan uzatiladi
(`ops/nginx/nginx.conf` dagi `proxy_set_header X-Original-URI`).

Sarlavha nomi IKKI joyda literal turadi (bu yerda va konfiguratsiyada) —
`REFRESH_COOKIE_NAME` bilan aynan bir xil holat va aynan bir xil yechim:
mosligini test tekshiradi.
"""

TOKEN_PARAM = "t"  # noqa: S105 — so'rov parametrining NOMI, sir emas
STREAM_PARAM = "src"


def _query_of(request: Request) -> dict[str, list[str]]:
    """So'rov parametrlari — avval `X-Original-URI` dan, keyin URL'ning o'zidan.

    IKKI MANBA VA TARTIB AHAMIYATLI. Mahsulot yo'lida qiymatlar
    `X-Original-URI` da keladi (nginx subso'rovi), lekin marshrutning
    O'ZI to'g'ridan-to'g'ri ham chaqirilishi mumkin — testda va nginx
    konfiguratsiyasi buzilgan holatda. Ikkinchi manba usiz marshrut
    «tokensiz» deb hisoblab, HAR DOIM 403 berardi va u holda hech qanday
    test uning MUVAFFAQIYAT yo'lini o'lchay olmasdi.
    """
    original = request.headers.get(ORIGINAL_URI_HEADER)
    if original:
        return parse_qs(urlsplit(original).query, keep_blank_values=True)
    return parse_qs(request.url.query, keep_blank_values=True)


def _single(values: dict[str, list[str]], name: str) -> str | None:
    """Parametrning YAGONA qiymati; takrorlangan bo'lsa — `None`.

    ⚠ TAKROR RAD ETILADI (`?t=yaxshi&t=yomon`): HTTP parametrni ikki
      marta berishga ruxsat beradi va turli qatlamlar turli qiymatni
      tanlaydi (nginx birinchisini, go2rtc oxirgisini). Bu klassik
      parameter-pollution chetlab o'tish yo'li — biz tekshirgan qiymat
      go2rtc ishlatadigan qiymat bo'lmasligi mumkin edi.
    """
    found = values.get(name)
    if not found or len(found) != 1 or not found[0]:
        return None
    return found[0]


def _denied(reason: str) -> Response:
    """403 — TANASIZ (fayl boshidagi izoh). Sabab faqat ilova jurnalida."""
    log.info("live_authz_denied", reason=reason)
    return Response(status_code=status.HTTP_403_FORBIDDEN)


async def _stream_matches(request: Request, claims: LiveClaims, stream: str) -> bool:
    """Chiptadagi kamera HAQIQATAN shu oqimga tegishlimi (fayl boshidagi izoh).

    Tenant konteksti CHIPTADAN o'rnatiladi — `Principal` dan emas, chunki
    bu yo'lda `Principal` umuman yo'q. Bu `jobs/discovery.py::
    _system_transaction` bilan bir xil naqsh, ikki farq bilan:
    `actor_kind` `USER` (harakat odam nomidan bo'lyapti) va sessiya
    hech nima YOZMAYDI — u faqat o'qiydi.

    ⚠ RLS BU YERDA IKKINCHI DARVOZA: `market_id` chiptadan keladi va u
      imzolangan, lekin kontekst baribir o'rnatiladi. Aks holda so'rov
      GUC'siz ketardi va RLS fail-closed 0 qator berib, HAR DOIM 403
      qaytarardi — ya'ni xato «xavfsiz» tomonga ishlardi, lekin mahsulot
      umuman ishlamasdi.
    """
    sessionmaker = request.app.state.sessionmaker
    async with sessionmaker() as session, session.begin():
        await set_tenant_context(
            session,
            market_id=claims.market_id,
            actor_id=claims.user_id,
            request_id=None,
            actor_kind=ActorKind.USER,
        )
        repo = NvrRepository(session, claims.market_id)
        for camera in await repo.list_cameras(include_archived=True):
            if camera.id != claims.camera_id:
                continue
            # ⚠ ARXIVLANGAN KAMERA — 403. Uning oqimi go2rtc'da
            #   ro'yxatga olinmaydi (UI-SPEC §6.6) va chipta arxivlashdan
            #   OLDIN berilgan bo'lishi mumkin: 60 soniyalik oyna arxiv
            #   qarorini chetlab o'tishga yetadi.
            return not camera.is_archived and camera.stream_name == stream
    return False


@router.get("/internal/live-authz")
async def live_authz(request: Request) -> Response:
    """nginx `auth_request` — **204** yoki **403**, tanasiz.

    Rad etish yo'llari (har biri alohida testda):
      * chipta umuman yo'q yoki takrorlangan;
      * `src` yo'q;
      * imzo/algoritm/`iss`/`aud` mos emas (masalan ODDIY access token);
      * muddat tugagan (D-08 ning butun mazmuni);
      * kamera bu bozorga tegishli emas, arxivlangan yoki `src` mos emas.
    """
    values = _query_of(request)
    token = _single(values, TOKEN_PARAM)
    stream = _single(values, STREAM_PARAM)

    if token is None:
        return _denied("missing_token")
    if stream is None:
        return _denied("missing_stream")

    settings: Settings = request.app.state.settings
    try:
        claims = decode_live_token(token, settings=settings)
    except jwt.ExpiredSignatureError:
        return _denied("expired")
    except jwt.InvalidTokenError:
        # ⚠ TUR BO'YICHA AJRATILMAYDI: `InvalidAudienceError`,
        #   `InvalidSignatureError` va `DecodeError` — hammasi bir xil
        #   javob oladi. Ajratish hujumchiga «imzo to'g'ri edi, lekin
        #   auditoriya emas» degan foydali signal berardi.
        return _denied("invalid_token")

    if not await _stream_matches(request, claims, stream):
        return _denied("camera_stream_mismatch")

    log.info("live_authz_granted", camera_id=str(claims.camera_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
