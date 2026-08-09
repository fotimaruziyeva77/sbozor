"""Bandlik domenining xato taksonomiyasi — o'n besh kod, BITTA iste'molchi.

=============================================================================
⛔ BU REYESTR OLDINGI BESHTASIDAN BITTA NARSA BILAN FARQ QILADI:
   `occupancy_events` DA XATO USTUNI YO'Q.

`nvr_discovery_runs.error_code` (03-06) va `capture_runs.error_code` (04-05)
bor edi, ya'ni o'sha ikki reyestrning IKKITA iste'molchisi bor: baza ustuni
va HTTP javobi. Bu yerda esa `occupancy_events` — O'ZGARMAS HODISA JURNALI
(D-12: tizim javobi saqlanadi va HECH QACHON o'zgartirilmaydi). Muvaffaqiyatsiz
bandlik qarori hodisa YARATMAYDI — u umuman yozilmaydi.

Shuning uchun bu kodlar **faqat HTTP `detail`** bo'ladi:

    HTTPException(detail={"error_code": ...})   -> HTTP javobi (05-06, 05-10…)

⚠ BU FARQ YOZIB QO'YILDI, chunki u ZID YO'NALISHDA o'qilishi mumkin: keyingi
  ijrochi «boshqa reyestrlarda ustun bor edi-ku» deb `occupancy_events` ga
  `error_code` ustuni qo'shishi mumkin. Qo'shmasin — u ustun «bandlik
  aniqlanmadi» degan hodisani DALIL sifatida yozib qo'yardi, holbuki bandlik
  dalili faqat YAROQLI kadrdan tug'iladi (D-21: `snapshots` ning
  `UNIQUE (id, is_billable)` langariga kompozit FK). Xato — hodisa emas.
=============================================================================

D-02: backend **KOD** beradi, matnni frontend uch tilda chizadi. Bu modulda
foydalanuvchi matni YO'Q va bo'lmaydi — u `frontend/messages/*.json` da.

=============================================================================
⛔ NEGA IKKI SIRT REYESTRI (`ZONE_ERROR_CODES` va `REVIEW_ERROR_CODES`),
   BITTA emas.

Reyestr nomi — SIRTNING O'ZI, alohida «surface» xaritasi emas:

    ZONE_ERROR_CODES    -> `cameraZones.errorCause.*` / `cameraZones.errorFix.*`
    REVIEW_ERROR_CODES  -> `review.errorCause.*`      / `review.errorFix.*`

Bu 04-10 dagi `actor` ustunining aynan bir xil sinfi va aynan bir xil
sababdan mexanik: kod qaysi EKRANDA ko'rsatilishi — ikki tomonda MUSTAQIL
yozilgan fakt. Backend kodni zona muharririniki deb, frontend esa
ko'rib chiqish sirtiniki deb hisoblasa, matn kaliti mavjud bo'lmagan
namespace'dan qidirilardi va foydalanuvchi tarjimasiz texnik satrni
ko'rardi — kod nomi esa ikkala tomonda ham BIR XIL bo'lgani uchun hech
qanday darvoza qizarmasdi.

Shuning uchun `scripts/error-codes.test.mjs` (G-17) kodlarni ham, ULAR QAYSI
REYESTRDA turishini ham solishtiradi.

⚠ `OCCUPANCY_ERROR_CODES` — IKKALASINING BIRLASHMASI, uchinchi qo'lda
  yozilgan ro'yxat EMAS (§S-5). Qo'lda yozilgan nusxa bir kun ajralib
  ketardi va `app/schemas.py` allowlist'i reyestrdan kichik bo'lib qolardi:
  router kod bilan `HTTPException` ko'tarardi, allowlist uni tanimasdi.
=============================================================================
"""

from __future__ import annotations

from typing import Final

__all__ = [
    "BLIND_ANSWER_LOCKED",
    "OCCUPANCY_ERROR_CODES",
    "REVIEW_ALREADY_ANSWERED",
    "REVIEW_BUDGET_EXHAUSTED",
    "REVIEW_ERROR_CODES",
    "REVIEW_IMAGE_UNAVAILABLE",
    "REVIEW_QUEUE_EMPTY",
    "REVIEW_SAMPLE_NOT_DRAWN",
    "ZONE_ASPECT_MISMATCH",
    "ZONE_CAMERA_HAS_NO_FRAME",
    "ZONE_ERROR_CODES",
    "ZONE_LIMIT_REACHED",
    "ZONE_POLYGON_DEGENERATE_EDGE",
    "ZONE_POLYGON_OUT_OF_RANGE",
    "ZONE_POLYGON_SELF_INTERSECTING",
    "ZONE_POLYGON_TOO_FEW_POINTS",
    "ZONE_POLYGON_TOO_MANY_POINTS",
    "ZONE_STALL_ALREADY_COVERED",
]


# ---------------------------------------------------------------------------
# 1-SIRT — ZONA MUHARRIRI (AI-01). Matn `cameraZones.*` da.
# ---------------------------------------------------------------------------

ZONE_POLYGON_TOO_FEW_POINTS: Final[str] = "zone_polygon_too_few_points"
"""Zonada uchtadan kam tepa qolgan — bu FIGURA emas, chiziq.

Ikki tepali «zona» ning yuzasi nol, ya'ni u hech qachon birorta rastani
qamramaydi. Uni jimgina qabul qilish rastani QAMROVDA ko'rsatib, aslida
u haqida hech qanday ma'lumot yig'maydigan holat tug'dirardi — ya'ni
`no_coverage` (D-22) YASHIRINARDI va hisobot jimgina noto'g'ri o'qilardi.
"""

ZONE_POLYGON_TOO_MANY_POINTS: Final[str] = "zone_polygon_too_many_points"
"""Tepalar soni bitta zona uchun belgilangan chegaradan oshdi.

Chegara ixtiyoriy emas: har tepa saqlanadi, har kadrda qayta o'qiladi va
`supervision.PolygonZone` ga uzatiladi. Chegarasiz bitta noto'g'ri klient
ming tepali poligon yuborib, kunlik bandlik hisobini sekinlashtirishi
mumkin edi (resurs chegarasi, T-05 sinfi).
"""

ZONE_POLYGON_OUT_OF_RANGE: Final[str] = "zone_polygon_out_of_range"
"""Koordinata 0..1 oralig'idan chiqdi — normalash shartnomasi buzilgan (D-07).

⚠ Koordinatalar ATAYIN normalangan: kamera qayta kashf qilinganda yoki
  ruxsati o'zgarganda poligon omon qoladi. Oraliqdan tashqaridagi qiymat
  bu kafolatni yo'q qiladi va u DENORMALASHDAN KEYIN kadr chetidan
  tashqariga tushadi — ya'ni zona ko'rinmas bo'lib qoladi, lekin baribir
  «qamrovda» deb sanaladi.
"""

ZONE_POLYGON_SELF_INTERSECTING: Final[str] = "zone_polygon_self_intersecting"
"""Poligon chegarasi o'zi bilan kesishgan — YUZASI IKKI MA'NOLI (D-05).

⛔ Bu kodni jimgina yutib bo'lmasligining sababi geometrik: o'zi bilan
   kesishgan figurada «ichkarida» tushunchasi aniqlanmagan va nuqta-ichida
   testi ishlatilgan algoritmga qarab TURLI javob beradi. Ya'ni xato
   poligon geometriyasiga yoziladi va u yerdan bandlik qaroriga, undan
   esa billing chegarasiga o'tadi — jimgina, dalilsiz.
"""

ZONE_POLYGON_DEGENERATE_EDGE: Final[str] = "zone_polygon_degenerate_edge"
"""Ketma-ket ikki tepa AYNAN bir xil — qirraning uzunligi NOL.

⛔ BU `ZONE_POLYGON_SELF_INTERSECTING` NING TAKRORI EMAS va ularni
   birlashtirish JIMGINA noto'g'ri hisob berardi. Farq o'lchangan:
   `frontend/src/lib/zone-geometry.ts::isSelfIntersecting` takrorlangan
   tepani **topa olmaydi** — nol uzunlikdagi kesma uchun orientatsiya
   determinanti har doim nol bo'ladi, ya'ni «nina» sharti ham
   (`dot > EPS`), umumiy kesishuv sharti ham (`o1 !== o2`) bajarilmaydi.
   Ya'ni bu holat klient darvozasidan BEMALOL o'tadi va uni FAQAT server
   ushlaydi.

Oqibati esa kesishgan poligonникi bilan bir sinf: nol uzunlikdagi qirra
`supervision.PolygonZone` ostidagi nuqta-poligon testida aniqlanmagan
natija beradi (takroriy tepa aylanish sonini buzadi), ya'ni bandlik
boshqa maydondan o'lchanadi — xato xabarisiz, bevosita billing chegarasiga.

⚠ Kod REYESTRGA 05-06 da QO'SHILDI: `validate_polygon()` beshta
  mavjud kodning birortasiga ham to'g'ri kelmaydigan HAQIQIY rad etish
  yo'lini topdi. Reyestrga qo'shish — `zone_geometry.py` da yangi literal
  o'ylab topishdan yagona to'g'ri muqobil (§S-5): literal `app/schemas.py`
  allowlist'iga tushmasdi va admin `errors.generic` ni ko'rardi.
"""

ZONE_LIMIT_REACHED: Final[str] = "zone_limit_reached"
"""Bitta kameradagi zonalar soni chegaraga yetdi (O-02).

⚠ Bu NOSOZLIK emas, RESURS chegarasi: admin ishini davom ettira oladi —
  boshqa kamerada. Shuning uchun u `zone_polygon_*` guruhidan alohida
  o'qiladi va frontendda `warning` bo'ladi.
"""

ZONE_STALL_ALREADY_COVERED: Final[str] = "zone_stall_already_covered"
"""Bu rastaning SHU KAMERADAGI zonasi allaqachon bor.

⛔ «Rasta allaqachon qamrovda» DEGANI EMAS va bu farq muhim: bir rasta bir
   necha kamerada bo'lishi NORMAL va u D-20 ning butun asosi («birortasi
   band desa — rasta band»). Taqiq faqat BIR KAMERADA ikkinchi zonaga
   qo'yilgan: u yerda ikki poligon bir rastaga ikki qarama-qarshi verdikt
   berib, qaysi biri hisobga kirishini aniqlab bo'lmas qilardi.
"""

ZONE_CAMERA_HAS_NO_FRAME: Final[str] = "zone_camera_has_no_frame"
"""Kamerada hali yaroqli kadr yo'q — zona chizishning LANGARI yo'q.

Zona kadr ustida chiziladi va uning `source_width`/`source_height` iga
bog'lanadi. Kadrsiz chizilgan poligon nimaga nisbatan normalanganini
BILDIRMASDI, ya'ni birinchi haqiqiy kadr kelganda u boshqa joyni
ko'rsatardi va buni sezish qiyin bo'lardi.
"""

ZONE_ASPECT_MISMATCH: Final[str] = "zone_aspect_mismatch"
"""Kadr nisbati zonalar chizilgandagidan farq qiladi (§6.8).

⛔ AVTOMATIK TO'G'RILASH YO'Q va bu ataylab: nisbat o'zgarishi kameraning
   ruxsati yoki o'rnatilishi o'zgarganini bildiradi, ya'ni poligonlar
   endi BOSHQA joyni ko'rsatishi mumkin. Cho'zib moslashtirish xatoni
   «tuzatilgan» qilib ko'rsatib, uni o'lchanmas holga keltirardi.
   To'g'ri xulq — zonani `needs_review` deb belgilash va ODAMDAN so'rash.
"""


# ---------------------------------------------------------------------------
# 2-SIRT — KO'RIB CHIQISH va KO'RMASDAN TEKSHIRISH (AI-03, AI-04).
# Matn `review.*` da.
# ---------------------------------------------------------------------------

REVIEW_QUEUE_EMPTY: Final[str] = "review_queue_empty"
"""Navbatda ko'riladigan band qolmadi.

⚠ Bu MUVAFFAQIYAT holati va u shu tarzda o'qilishi kerak: tizim bugun
  shubhalangan hamma rasta ko'rib chiqilgan. U reyestrda, chunki
  to'g'ridan-to'g'ri URL bilan kelgan so'rov ham javob olishi kerak —
  aks holda ekran bo'sh qolib, nazoratchi «ish yo'q» bilan «tizim
  ishlamadi» ni ajrata olmasdi.
"""

REVIEW_BUDGET_EXHAUSTED: Final[str] = "review_budget_exhausted"
"""Kunlik ko'rish byudjeti tugadi (D-13).

⛔ Byudjet — KVOTA emas, DIQQAT chegarasi. Uni «yana ko'rish» tugmasi bilan
   ochish charchagan holda berilgan javoblarni ma'lumotga aylantirardi va
   aynan shu ma'lumot bilan tizim aniqligi o'lchanadi. Ya'ni chegarani
   yumshatish o'lchov asbobining o'zini buzardi.
"""

REVIEW_SAMPLE_NOT_DRAWN: Final[str] = "review_sample_not_drawn"
"""Bugungi namuna hali tortilmagan.

⛔ QO'LDA TORTISH YO'LI YO'Q (D-17, 1-himoya): urug' hosila va namuna
   qayta chizilmaydi. «Bu turda xato ko'p chiqdi, qaytadan tortaman»
   degan yo'l aniqlikni yuqoriga siljitardi — ya'ni hisobot o'zi
   o'lchayotgan narsani o'zgartirardi. Shuning uchun bu kod «kuting»
   deydi va HECH QANDAY amal taklif qilmaydi.
"""

REVIEW_IMAGE_UNAVAILABLE: Final[str] = "review_image_unavailable"
"""Dalil kadri ochilmadi — javob berish MUMKIN EMAS (§7.4).

⛔ Rasm bu yerda «bezak» emas, QARORNING DARVOZASI: nazoratchi ko'rmagan
   rasta haqida bergan javobi ma'lumot emas, taxmin. Uni jimgina qabul
   qilish xolis o'lchovga TAXMINNI qo'shardi va aniqlik raqami
   isbotlanmagan holda ko'tarilardi.
"""

BLIND_ANSWER_LOCKED: Final[str] = "blind_answer_locked"
"""Ko'rmasdan tekshirishda bu bandga javob ALLAQACHON yozilgan (D-17, 4-himoya).

⛔ `REVIEW_ALREADY_ANSWERED` DAN AJRATISH MAJBURIY. Ikkalasi ham «javob bor»
   deydi, lekin SABABI va OQIBATI butunlay boshqa:

     bu kod       — javob STRUKTURAVIY o'zgarmas. Tizim javobi oshkor
                    qilingandan keyin tahrirlash imkoniyati o'lchovni
                    yo'q qilardi (nazoratchi o'z javobini tizimnikiga
                    moslab qo'yardi va aniqlik 100% ga intilardi).
     ikkinchisi   — POYGA holati (ikki oyna, ikki bosish).

   Ularni birlashtirish keyingi ijrochiga «bu shunchaki poyga ekan, ustiga
   yozsa bo'ladi» degan xulosa berardi — ya'ni D-17 ni JIMGINA yolg'onga
   aylantirardi.
"""

REVIEW_ALREADY_ANSWERED: Final[str] = "review_already_answered"
"""Noaniq navbatidagi bandga javob allaqachon berilgan — POYGA holati.

Ikki oyna yoki ikki marta bosish. Yechim oddiy: navbat yangilanadi va
keyingi bandga o'tiladi. Yuqoridagi `BLIND_ANSWER_LOCKED` bilan
ADASHTIRMANG — u yerda taqiq strukturaviy, bu yerda esa shunchaki
ikkinchi so'rov kech qolgan.
"""


ZONE_ERROR_CODES: Final[frozenset[str]] = frozenset(
    {
        ZONE_POLYGON_TOO_FEW_POINTS,
        ZONE_POLYGON_TOO_MANY_POINTS,
        ZONE_POLYGON_OUT_OF_RANGE,
        ZONE_POLYGON_SELF_INTERSECTING,
        ZONE_POLYGON_DEGENERATE_EDGE,
        ZONE_LIMIT_REACHED,
        ZONE_STALL_ALREADY_COVERED,
        ZONE_CAMERA_HAS_NO_FRAME,
        ZONE_ASPECT_MISMATCH,
    }
)
"""Zona muharririning kodlari — matni `cameraZones.errorCause.*` / `errorFix.*`.

⚠ REYESTR NOMI — SIRTNING O'ZI. Kodni bu to'plamdan `REVIEW_ERROR_CODES` ga
  ko'chirish uning MATN KALITINI ham ko'chiradi va G-17 buni talab qiladi.
"""

REVIEW_ERROR_CODES: Final[frozenset[str]] = frozenset(
    {
        REVIEW_QUEUE_EMPTY,
        REVIEW_BUDGET_EXHAUSTED,
        REVIEW_SAMPLE_NOT_DRAWN,
        REVIEW_IMAGE_UNAVAILABLE,
        BLIND_ANSWER_LOCKED,
        REVIEW_ALREADY_ANSWERED,
    }
)
"""Ko'rib chiqish sirtining kodlari — matni `review.errorCause.*` / `errorFix.*`."""


OCCUPANCY_ERROR_CODES: Final[frozenset[str]] = ZONE_ERROR_CODES | REVIEW_ERROR_CODES
"""Bandlik domenining BARCHA `detail` kodlari — o'n beshta.

⚠ IKKI SIRT REYESTRIDAN HOSILA, qo'lda uchinchi marta YOZILMAGAN. Qo'lda
  yozilgan nusxa `app/schemas.py` ning allowlist'ini reyestrdan kichik
  qoldirishi mumkin edi va u holda router ko'targan kod HTTP chegarasida
  tanilmasdi (§S-5, `CAPTURE_JOB_ERROR_CODES` bilan aynan bir xil qaror).

`app/schemas.py` bu to'plamni IMPORT qiladi, qayta YOZMAYDI.
"""
